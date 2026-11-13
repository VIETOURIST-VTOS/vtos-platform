"""R5-16 · Chính sách bán của Phòng Kinh doanh Lẻ — Chủ tịch duyệt bản xem trước 14/11/2026.

Ba phần MỚI do GĐ KD / TP ban hành (lưu ở `chinh_sach_ban.noi_dung`, JSON):
    chiet_khau  {"nv_kd": %, "tn_kd": %, "tp_kd": %}           chiết khấu tối đa người bán tự cho (% giá bán)
    tre_em      {"tre_em_pct": %, "em_be_pct": %, "phu_thu_phong_don": đ}
    khuyen_mai  [{"ma", "ten", "kieu": "pct"|"tien", "gia_tri", "ap_dung", "tu", "den"}]
Ô để rỗng = «chưa ban hành» (None), KHÔNG phải 0 — Claude không đặt số; GĐ KD nhập.

Hai phần ĐÃ CÓ, chỉ ĐỌC THẲNG (Chủ tịch 14/11/2026: «đối tác, đại lý và CTV … khách hàng thì áp điểm
reward và hoa hồng … đã có sẵn»): hoa hồng đối tác D06 (`hoa_hong_d06.BAC`, tham số `d06_hieu_luc_tu`) và
VTD Rewards (`rewards.HANG`, tham số `rewards_hieu_luc_tu`). Sửa ở hai màn ấy, không nhập lần hai ở đây.
"""
import json
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ban_hang import ChinhSachBan
from app.models.core import User
from app.models.doi_tac_ban_hang import NHAN_LOAI, DoiTacBanHang

VAI_BAN_HANH = ("gd_kd", "tp_kd", "chutich", "tgd")
VAI_XEM = VAI_BAN_HANH + ("tn_kd", "nv_kd", "sales_admin", "ketoan", "bks", "robot_ks", "cntt")
VAI_CK = ("nv_kd", "tn_kd", "tp_kd")


def _pct(v, ten: str):
    if v in (None, ""):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise HTTPException(422, f"{ten}: phải là số phần trăm")
    if not 0 <= x <= 100:
        raise HTTPException(422, f"{ten}: phải trong 0–100%")
    return x


def _tien(v, ten: str):
    if v in (None, ""):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise HTTPException(422, f"{ten}: phải là số tiền")
    if x < 0:
        raise HTTPException(422, f"{ten}: không được âm")
    return x


def chuan_hoa(d: dict) -> dict:
    ck = d.get("chiet_khau") or {}
    te = d.get("tre_em") or {}
    km = []
    for i, k in enumerate(d.get("khuyen_mai") or []):
        ten = (k.get("ten") or "").strip()
        if not ten:
            continue
        kieu = k.get("kieu") if k.get("kieu") in ("pct", "tien") else "pct"
        gt = _pct(k.get("gia_tri"), f"Khuyến mãi {i + 1}") if kieu == "pct" else _tien(k.get("gia_tri"), f"Khuyến mãi {i + 1}")
        km.append({"ma": (k.get("ma") or "").strip()[:20].upper(), "ten": ten[:160], "kieu": kieu, "gia_tri": gt,
                   "ap_dung": (k.get("ap_dung") or "").strip()[:120], "tu": k.get("tu") or None, "den": k.get("den") or None})
    return {"chiet_khau": {v: _pct(ck.get(v), f"Chiết khấu {v}") for v in VAI_CK},
            "tre_em": {"tre_em_pct": _pct(te.get("tre_em_pct"), "Giá trẻ em"), "em_be_pct": _pct(te.get("em_be_pct"), "Giá em bé"),
                       "phu_thu_phong_don": _tien(te.get("phu_thu_phong_don"), "Phụ thu phòng đơn")},
            "khuyen_mai": km}


def _dong(c: ChinhSachBan) -> dict:
    return {"id": c.id, "ma": c.ma, "mang": c.mang, "hieu_luc_tu": c.hieu_luc_tu, "hieu_luc_den": c.hieu_luc_den,
            "noi_dung": json.loads(c.noi_dung or "{}"), "ghi_chu": c.ghi_chu, "tao_boi": c.tao_boi, "tao_luc": c.tao_luc}


def hien_hanh(db: Session, ngay: date | None = None, mang: str = "kd_le") -> ChinhSachBan | None:
    d = ngay or date.today()
    ds = db.execute(select(ChinhSachBan).where(ChinhSachBan.mang == mang, ChinhSachBan.hieu_luc_tu <= d)
                    .order_by(ChinhSachBan.hieu_luc_tu.desc(), ChinhSachBan.id.desc())).scalars().all()
    return next((c for c in ds if c.hieu_luc_den is None or c.hieu_luc_den >= d), None)


def _lien_ket(db: Session) -> dict:
    """Hai chính sách đã có — đọc thẳng, không lưu lại."""
    from app.services import hoa_hong_d06 as D6
    from app.services import rewards as RW
    d6_tu = D6.hieu_luc_tu(db)
    bac = {k: {"bac": [{"tu": a, "den": b, "ty_le": bps / 100} for a, b, bps in v["bac"]]} for k, v in D6.BAC.items()}
    dem = {}
    for dt in db.execute(select(DoiTacBanHang)).scalars():
        if dt.hieu_luc_den is None or dt.hieu_luc_den >= date.today():
            dem[dt.loai] = dem.get(dt.loai, 0) + 1
    rw_tu = RW.hieu_luc_tu(db)
    v3 = RW.v3_tu(db)
    bang = RW.HANG if (v3 and v3 <= date.today()) else RW.HANG_CU
    return {
        "d06": {"bat": bool(d6_tu and d6_tu <= date.today()), "hieu_luc_tu": d6_tu, "bac": bac,
                "doi_tac": [{"loai": k, "ten": NHAN_LOAI.get(k, k), "so": dem.get(k, 0)} for k in NHAN_LOAI]},
        "rewards": {"bat": bool(rw_tu and rw_tu <= date.today()), "hieu_luc_tu": rw_tu,
                    "hang": [{"ten": t, "tu": m, "he_so": float(h)} for t, m, h in bang],
                    "dong_moi_diem": RW.DONG_MOI_DIEM, "gia_tri_diem": RW.GIA_TRI_DIEM,
                    "tran_voucher_pct": float(RW.TRAN_VOUCHER) * 100, "gioi_thieu_mo": RW.gioi_thieu_mo(db)},
    }


def tong_hop(db: Session, u: User, mang: str = "kd_le") -> dict:
    hh = hien_hanh(db, mang=mang)
    cu = db.execute(select(ChinhSachBan).where(ChinhSachBan.mang == mang)
                    .order_by(ChinhSachBan.hieu_luc_tu.desc(), ChinhSachBan.id.desc())).scalars().all()
    return {"hien_hanh": _dong(hh) if hh else None, "cac_ban": [_dong(c) for c in cu if not hh or c.id != hh.id],
            "lien_ket": _lien_ket(db), "duoc_ban_hanh": u.role in VAI_BAN_HANH}


def ban_hanh(db: Session, u: User, d: dict, mang: str = "kd_le") -> dict:
    if u.role not in VAI_BAN_HANH:
        raise HTTPException(403, "Chỉ GĐ KD / Trưởng phòng KD ban hành chính sách bán")
    try:
        tu = date.fromisoformat(str(d.get("hieu_luc_tu")))
    except ValueError:
        raise HTTPException(422, "Thiếu ngày hiệu lực")
    den = date.fromisoformat(d["hieu_luc_den"]) if d.get("hieu_luc_den") else None
    if den and den < tu:
        raise HTTPException(422, "Ngày hết hiệu lực trước ngày bắt đầu")
    nd = chuan_hoa(d.get("noi_dung") or {})
    cu = hien_hanh(db, tu, mang)
    if cu and cu.hieu_luc_tu < tu:
        cu.hieu_luc_den = tu - timedelta(days=1)                # khép bản cũ, không xoá
    elif cu:
        raise HTTPException(422, f"Đã có bản {cu.ma} bắt đầu cùng ngày — chọn ngày hiệu lực khác")
    n = len(db.execute(select(ChinhSachBan.id).where(ChinhSachBan.mang == mang)).all()) + 1
    c = ChinhSachBan(ma=f"CS-{tu:%Y-%m}-{n}", mang=mang, hieu_luc_tu=tu, hieu_luc_den=den,
                     noi_dung=json.dumps(nd, ensure_ascii=False), ghi_chu=(d.get("ghi_chu") or "")[:2000],
                     tao_boi=u.username, tao_luc=datetime.now())
    db.add(c)
    db.commit(); db.refresh(c)
    return _dong(c)
