"""KS-13 · Danh mục khách sạn hợp tác VTD — phía VTOS (nhập, duyệt, bật hiện) và phía cổng khách (tìm, xem, chọn phòng).

Xem đầu app/models/khach_san_vtd.py cho ai làm gì. Ở bước 12a khách «Gửi yêu cầu giữ phòng»: yêu cầu vào hàng chờ
KS-11 của Điều hành (dat_phong_ota.gui_yeu_cau), mang phòng khách chọn và GIÁ DO MÁY TÍNH LẠI — không tin số
trình duyệt gửi lên.
"""
import math
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.khach_san_vtd import (AnhKhachSanVtd, GoiGiaVtd, KhachSanVtd, LoaiPhongVtd, MuaGiaVtd, LOAI_CHO_O,
                                      NHOM_ANH_KS, TIEN_ICH, TRANG_THAI_ANH_KS, TRANG_THAI_GOI)
from app.services.nha_hang import THANH_PHO, MIEN, _co, _khong_dau

TOAN_QUYEN = ("chutich", "tgd")
VAI_NHAP = ("tp_dh", "nv_dh") + TOAN_QUYEN
VAI_DUYET = ("tp_dh",) + TOAN_QUYEN
VAI_XEM = tuple(dict.fromkeys(VAI_NHAP + ("bks", "robot_ks", "gd_kd", "tp_kd", "nv_mkt", "ptgd_mkt")))
VAI_XEM = tuple(dict.fromkeys(VAI_XEM + ("ketoan", "tn_kd", "nv_kd", "sales_admin")))   # KS-14: Kế toán, Sales đọc danh mục để xử lý đơn
ANH_TOI_DA = 80
DEM_TOI_DA = 30
NGAY_CUOI_TUAN = (4, 5)       # đêm thứ Sáu, thứ Bảy


class LoiKhachSan(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _audit(db: Session, u: User, viec: str, ma: str, truoc=None, sau=None) -> None:
    from app.services import rules as R
    R.audit(db, u.username, u.role, viec, f"khach_san_vtd:{ma}", before=truoc, after=sau)


def _ks(db: Session, kid: int) -> KhachSanVtd:
    k = db.get(KhachSanVtd, kid)
    if k is None:
        raise LoiKhachSan("Không có khách sạn này", 404)
    return k


def _quyen(u: User, vai: tuple, viec: str) -> None:
    if not _co(u, vai):
        raise LoiKhachSan(viec, 403)


def _ma_moi(db: Session) -> str:
    n = len(db.execute(select(KhachSanVtd.id)).all()) + 1
    while db.execute(select(KhachSanVtd.id).where(KhachSanVtd.ma == f"KS-{n:03d}")).first():
        n += 1
    return f"KS-{n:03d}"


# ══ GIÁ ═══════════════════════════════════════════════════════════════════════════════════════════════
def cac_dem(vao: date, ra: date) -> list[date]:
    return [vao + timedelta(days=i) for i in range((ra - vao).days)]


def gia_luu(goi: GoiGiaVtd, mua: list[MuaGiaVtd], vao: date, ra: date) -> dict | None:
    """Tiền MỘT phòng cho cả kỳ ở (chưa thuế phí). Đêm nào không có mùa giá phủ → None (gói không bán được kỳ này)."""
    tien, niem, co_niem = 0.0, 0.0, True
    for d in cac_dem(vao, ra):
        m = next((x for x in mua if x.tu_ngay <= d <= x.den_ngay), None)
        if m is None:
            return None
        g = float(m.gia_cuoi_tuan) if (d.weekday() in NGAY_CUOI_TUAN and m.gia_cuoi_tuan) else float(m.gia_thuong)
        tien += g
        if m.gia_niem_yet:
            niem += float(m.gia_niem_yet)
        else:
            co_niem = False
    so = (ra - vao).days
    return {"tong": round(tien), "gia_dem": round(tien / so), "niem_yet_dem": round(niem / so) if co_niem and niem > tien else None}


def han_huy(goi: GoiGiaVtd, vao: date) -> date | None:
    return vao - timedelta(days=goi.huy_truoc_ngay) if goi.huy_truoc_ngay is not None else None


def _kiem_ky(vao, ra, hom_nay: date | None = None) -> tuple[date, date]:
    hom_nay = hom_nay or date.today()
    try:
        vao = vao if isinstance(vao, date) else date.fromisoformat(str(vao)[:10])
        ra = ra if isinstance(ra, date) else date.fromisoformat(str(ra)[:10])
    except ValueError:
        raise LoiKhachSan("Ngày nhận / trả phòng không hợp lệ")
    if vao < hom_nay:
        raise LoiKhachSan("Ngày nhận phòng đã qua")
    if ra <= vao:
        raise LoiKhachSan("Ngày trả phòng phải sau ngày nhận phòng")
    if (ra - vao).days > DEM_TOI_DA:
        raise LoiKhachSan(f"Đặt tối đa {DEM_TOI_DA} đêm một lần")
    return vao, ra


# ══ VTOS · HỒ SƠ KHÁCH SẠN ════════════════════════════════════════════════════════════════════════
TRUONG_KS = ("ten", "tinh_thanh", "khu_vuc", "dia_chi", "sao", "loai", "km_trung_tam", "gan", "noi_bat", "mo_ta",
             "tien_ich", "gio_nhan", "gio_tra", "cs_tre_em", "cs_giuong_phu", "cs_vat_nuoi", "cs_khac", "thue_phi_pt",
             "lien_he_noi_bo", "ghi_chu_noi_bo")


def _kiem_ks(d: dict) -> dict:
    o = {}
    o["ten"] = str(d.get("ten") or "").strip()[:160]
    if len(o["ten"]) < 3:
        raise LoiKhachSan("Ghi tên khách sạn")
    o["tinh_thanh"] = str(d.get("tinh_thanh") or "").strip()
    if o["tinh_thanh"] not in THANH_PHO:
        raise LoiKhachSan("Chọn thành phố trong danh sách")
    try:
        o["sao"] = int(d.get("sao") or 0)
    except (TypeError, ValueError):
        raise LoiKhachSan("Hạng sao không hợp lệ")
    if not 0 <= o["sao"] <= 5:
        raise LoiKhachSan("Hạng sao từ 1 đến 5 (0 = chưa xếp hạng)")
    o["loai"] = str(d.get("loai") or "khach_san")
    if o["loai"] not in LOAI_CHO_O:
        raise LoiKhachSan("Loại chỗ ở không hợp lệ")
    km = d.get("km_trung_tam")
    o["km_trung_tam"] = None if km in (None, "") else round(float(km), 1)
    if o["km_trung_tam"] is not None and not 0 <= o["km_trung_tam"] <= 200:
        raise LoiKhachSan("Khoảng cách tới trung tâm 0–200 km")
    ti = d.get("tien_ich") or []
    if any(x not in TIEN_ICH for x in ti):
        raise LoiKhachSan("Tiện ích không hợp lệ")
    o["tien_ich"] = list(dict.fromkeys(ti))
    for k in ("gio_nhan", "gio_tra"):
        v = str(d.get(k) or "").strip() or ("14:00" if k == "gio_nhan" else "12:00")
        if len(v) != 5 or v[2] != ":" or not (v[:2] + v[3:]).isdigit() or int(v[:2]) > 23 or int(v[3:]) > 59:
            raise LoiKhachSan("Giờ nhận / trả phòng dạng HH:MM")
        o[k] = v
    t = d.get("thue_phi_pt")
    o["thue_phi_pt"] = 0.0 if t in (None, "") else float(t)
    if not 0 <= o["thue_phi_pt"] <= 30:
        raise LoiKhachSan("Thuế phí 0–30%")
    for k, n in (("khu_vuc", 120), ("dia_chi", 300), ("gan", 300), ("noi_bat", 300), ("cs_tre_em", 300),
                 ("cs_giuong_phu", 300), ("cs_vat_nuoi", 300), ("lien_he_noi_bo", 300)):
        o[k] = str(d.get(k) or "").strip()[:n]
    for k in ("mo_ta", "cs_khac", "ghi_chu_noi_bo"):
        o[k] = str(d.get(k) or "").strip()[:6000]
    return o


def luu_ks(db: Session, u: User, d: dict, kid: int | None = None, now: datetime | None = None) -> KhachSanVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành nhập và sửa khách sạn")
    o = _kiem_ks(d)
    now = now or datetime.now()
    if kid is None:
        k = KhachSanVtd(ma=_ma_moi(db), tao_boi=u.username, tao_luc=now, **o)
        db.add(k)
        db.flush()
        _audit(db, u, "ks_vtd_tao", k.ma, None, {"ten": k.ten})
    else:
        k = _ks(db, kid)
        truoc = {x: getattr(k, x) for x in TRUONG_KS}
        for x, v in o.items():
            setattr(k, x, v)
        _audit(db, u, "ks_vtd_sua", k.ma, truoc, o)
    k.sua_boi, k.sua_luc = u.username, now
    db.commit()
    db.refresh(k)
    return k


def dieu_kien_hien(db: Session, k: KhachSanVtd) -> list[dict]:
    lps = _lp_cua(db, k.id)
    return [{"ma": "ho_so", "ten": "Đủ tên, thành phố, hạng sao", "ok": bool(k.ten and k.tinh_thanh in THANH_PHO and k.sao)},
            {"ma": "anh", "ten": "Có ảnh đã duyệt", "ok": bool(_anh_duyet(db, [k.id]).get(k.id))},
            {"ma": "phong", "ten": "Có loại phòng đang bán", "ok": any(x.dang_ban for x in lps)},
            {"ma": "mo_ta", "ten": "Có giới thiệu cho khách", "ok": len(k.mo_ta or "") >= 40}]


def bat_hien(db: Session, u: User, kid: int, bat: bool, now: datetime | None = None) -> KhachSanVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành bật / tắt hiện khách sạn trên cổng")
    k = _ks(db, kid)
    now = now or datetime.now()
    if bat:
        if k.ngung:
            raise LoiKhachSan("Khách sạn đã ngừng hợp tác")
        thieu = [c["ten"] for c in dieu_kien_hien(db, k) if not c["ok"]]
        if thieu:
            raise LoiKhachSan("Chưa bật được — còn thiếu: " + "; ".join(thieu))
        if k.sua_boi == u.username and not _co(u, TOAN_QUYEN):
            raise LoiKhachSan("Người vừa sửa hồ sơ không tự bật — cần TP Điều hành khác hoặc Chủ tịch / TGĐ")
    k.hien_cong, k.hien_boi, k.hien_luc = bool(bat), u.username, now
    k.tat_ly_do = "" if bat else f"Tắt bởi {u.username}"
    _audit(db, u, "ks_vtd_bat" if bat else "ks_vtd_tat", k.ma)
    db.commit()
    return k


def ngung(db: Session, u: User, kid: int, ngung_: bool) -> KhachSanVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành đổi trạng thái hợp tác")
    k = _ks(db, kid)
    k.ngung = bool(ngung_)
    if ngung_:
        k.hien_cong, k.tat_ly_do = False, "Ngừng hợp tác"
    _audit(db, u, "ks_vtd_ngung" if ngung_ else "ks_vtd_hop_tac_lai", k.ma)
    db.commit()
    return k


# ══ VTOS · LOẠI PHÒNG, GÓI GIÁ, MÙA GIÁ ═══════════════════════════════════════════════════════════
def _lp_cua(db: Session, kid: int) -> list[LoaiPhongVtd]:
    return db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.khach_san_id == kid)
                      .order_by(LoaiPhongVtd.thu_tu, LoaiPhongVtd.id)).scalars().all()


def luu_loai_phong(db: Session, u: User, kid: int, d: dict, lid: int | None = None, now: datetime | None = None) -> LoaiPhongVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành nhập loại phòng")
    k = _ks(db, kid)
    ten = str(d.get("ten") or "").strip()[:120]
    if len(ten) < 2:
        raise LoiKhachSan("Ghi tên loại phòng")
    try:
        o = {"ten": ten, "dien_tich": int(d.get("dien_tich") or 0), "giuong": str(d.get("giuong") or "").strip()[:120],
             "mo_ta": str(d.get("mo_ta") or "").strip()[:300], "toi_da_nguoi_lon": int(d.get("toi_da_nguoi_lon") or 2),
             "toi_da_tre_em": int(d.get("toi_da_tre_em") or 0), "so_phong": int(d.get("so_phong") or 1),
             "thu_tu": int(d.get("thu_tu") or 0), "dang_ban": bool(d.get("dang_ban", True))}
    except (TypeError, ValueError):
        raise LoiKhachSan("Số liệu loại phòng không hợp lệ")
    if not 1 <= o["toi_da_nguoi_lon"] <= 20 or not 0 <= o["toi_da_tre_em"] <= 10:
        raise LoiKhachSan("Sức chứa: người lớn 1–20, trẻ em 0–10")
    if not 0 <= o["so_phong"] <= 500 or not 0 <= o["dien_tich"] <= 2000:
        raise LoiKhachSan("Số phòng 0–500, diện tích 0–2000 m²")
    if lid is None:
        lp = LoaiPhongVtd(khach_san_id=k.id, **o)
        db.add(lp)
    else:
        lp = db.get(LoaiPhongVtd, lid)
        if lp is None or lp.khach_san_id != k.id:
            raise LoiKhachSan("Không có loại phòng này", 404)
        for x, v in o.items():
            setattr(lp, x, v)
    lp.sua_boi, lp.sua_luc = u.username, now or datetime.now()
    db.flush()
    _audit(db, u, "ks_vtd_loai_phong", k.ma, None, {"id": lp.id, **o})
    db.commit()
    db.refresh(lp)
    return lp


def _mua_cua(db: Session, gids: list[int]) -> dict[int, list[MuaGiaVtd]]:
    ra: dict[int, list] = {}
    if gids:
        for m in db.execute(select(MuaGiaVtd).where(MuaGiaVtd.goi_id.in_(gids)).order_by(MuaGiaVtd.tu_ngay)).scalars():
            ra.setdefault(m.goi_id, []).append(m)
    return ra


def _kiem_mua(ds: list) -> list[dict]:
    ra = []
    for i, m in enumerate(ds or [], start=1):
        try:
            tu, den = date.fromisoformat(str(m.get("tu_ngay"))[:10]), date.fromisoformat(str(m.get("den_ngay"))[:10])
            gt = float(m.get("gia_thuong") or 0)
            gc = float(m["gia_cuoi_tuan"]) if m.get("gia_cuoi_tuan") not in (None, "", 0) else None
            gn = float(m["gia_niem_yet"]) if m.get("gia_niem_yet") not in (None, "", 0) else None
        except (TypeError, ValueError):
            raise LoiKhachSan(f"Mùa giá dòng {i}: ngày hoặc giá không hợp lệ")
        if den < tu:
            raise LoiKhachSan(f"Mùa giá dòng {i}: «đến ngày» trước «từ ngày»")
        if gt < 10000 or (gc is not None and gc < 10000):
            raise LoiKhachSan(f"Mùa giá dòng {i}: giá bán mỗi đêm từ 10.000 đ")
        if max(gt, gc or 0) > 500_000_000:
            raise LoiKhachSan(f"Mùa giá dòng {i}: giá quá lớn — kiểm tra lại số 0")
        ra.append({"tu_ngay": tu, "den_ngay": den, "gia_thuong": gt, "gia_cuoi_tuan": gc, "gia_niem_yet": gn,
                   "ghi_chu": str(m.get("ghi_chu") or "").strip()[:200]})
    ra.sort(key=lambda x: x["tu_ngay"])
    for a, b in zip(ra, ra[1:]):
        if b["tu_ngay"] <= a["den_ngay"]:
            raise LoiKhachSan(f"Hai mùa giá chồng ngày nhau ({a['tu_ngay']:%d/%m} – {a['den_ngay']:%d/%m} và từ {b['tu_ngay']:%d/%m})")
    return ra


def luu_goi(db: Session, u: User, lid: int, d: dict, gid: int | None = None, now: datetime | None = None) -> GoiGiaVtd:
    """Lưu gói + toàn bộ mùa giá (thay hết). Gói về «Nháp» — phải gửi duyệt lại; gói đang duyệt thôi hiện."""
    _quyen(u, VAI_NHAP, "Chỉ Điều hành nhập gói giá")
    lp = db.get(LoaiPhongVtd, lid)
    if lp is None:
        raise LoiKhachSan("Không có loại phòng này", 404)
    ten = str(d.get("ten") or "").strip()[:80]
    if len(ten) < 2:
        raise LoiKhachSan("Ghi tên gói (vd: Chỉ phòng, Có bữa sáng)")
    h = d.get("huy_truoc_ngay")
    h = None if h in (None, "", "khong") else int(h)
    if h is not None and not 0 <= h <= 60:
        raise LoiKhachSan("Miễn phí hủy trước 0–60 ngày, hoặc «không hoàn tiền»")
    mua = _kiem_mua(d.get("mua") or [])
    if not mua:
        raise LoiKhachSan("Nhập ít nhất một mùa giá")
    now = now or datetime.now()
    if gid is None:
        g = GoiGiaVtd(loai_phong_id=lid)
        db.add(g)
    else:
        g = db.get(GoiGiaVtd, gid)
        if g is None or g.loai_phong_id != lid:
            raise LoiKhachSan("Không có gói này", 404)
        for m in db.execute(select(MuaGiaVtd).where(MuaGiaVtd.goi_id == g.id)).scalars():
            db.delete(m)
    truoc = g.trang_thai if gid else None
    g.ten, g.bua_sang, g.huy_truoc_ngay, g.dang_ban = ten, bool(d.get("bua_sang")), h, bool(d.get("dang_ban", True))
    g.trang_thai, g.ly_do_tra_lai, g.duyet_boi, g.duyet_luc = "nhap", "", "", None
    g.sua_boi, g.sua_luc = u.username, now
    db.flush()
    for m in mua:
        db.add(MuaGiaVtd(goi_id=g.id, **m))
    k = db.get(KhachSanVtd, lp.khach_san_id)
    _audit(db, u, "ks_vtd_goi_luu", k.ma, {"trang_thai": truoc}, {"goi": g.id, "ten": ten, "so_mua": len(mua)})
    db.commit()
    db.refresh(g)
    return g


def gui_duyet_goi(db: Session, u: User, gid: int) -> GoiGiaVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành gửi duyệt giá")
    g = db.get(GoiGiaVtd, gid)
    if g is None:
        raise LoiKhachSan("Không có gói này", 404)
    if g.trang_thai not in ("nhap", "tra_lai"):
        raise LoiKhachSan("Gói này không ở trạng thái nháp")
    g.trang_thai, g.gui_boi = "cho_duyet", u.username
    db.commit()
    return g


def duyet_goi(db: Session, u: User, gid: int, dong_y: bool, ly_do: str = "", now: datetime | None = None) -> GoiGiaVtd:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành duyệt giá")
    g = db.get(GoiGiaVtd, gid)
    if g is None:
        raise LoiKhachSan("Không có gói này", 404)
    if g.trang_thai != "cho_duyet":
        raise LoiKhachSan("Gói này không chờ duyệt")
    if g.sua_boi == u.username and not _co(u, TOAN_QUYEN):
        raise LoiKhachSan("Người nhập giá không tự duyệt — cần TP Điều hành khác hoặc Chủ tịch / TGĐ")
    if not dong_y and len((ly_do or "").strip()) < 5:
        raise LoiKhachSan("Trả lại phải ghi lý do")
    g.trang_thai = "da_duyet" if dong_y else "tra_lai"
    g.ly_do_tra_lai = "" if dong_y else ly_do.strip()[:300]
    g.duyet_boi, g.duyet_luc = u.username, now or datetime.now()
    lp = db.get(LoaiPhongVtd, g.loai_phong_id)
    k = db.get(KhachSanVtd, lp.khach_san_id)
    _audit(db, u, "ks_vtd_goi_duyet" if dong_y else "ks_vtd_goi_tra_lai", k.ma, None, {"goi": g.id, "ly_do": g.ly_do_tra_lai})
    db.commit()
    return g


# ══ VTOS · ẢNH ═════════════════════════════════════════════════════════════════════════════════════
def _anh_cua(db: Session, kid: int) -> list[AnhKhachSanVtd]:
    return db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id == kid)
                      .order_by(AnhKhachSanVtd.la_bia.desc(), AnhKhachSanVtd.thu_tu, AnhKhachSanVtd.id)).scalars().all()


def _anh_duyet(db: Session, kids: list[int]) -> dict[int, list[AnhKhachSanVtd]]:
    ra: dict[int, list] = {}
    if kids:
        q = (select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id.in_(kids), AnhKhachSanVtd.trang_thai == "da_duyet")
             .order_by(AnhKhachSanVtd.la_bia.desc(), AnhKhachSanVtd.thu_tu, AnhKhachSanVtd.id))
        for a in db.execute(q).scalars():
            ra.setdefault(a.khach_san_id, []).append(a)
    return ra


def tai_anh(db: Session, u: User, kid: int, ten_tep: str, data: bytes, d: dict, now: datetime | None = None) -> tuple[AnhKhachSanVtd, bool]:
    from app.services import attachments as AT
    from app.services.nha_hang import KIEU_ANH, LoiNhaHang, _co_pil, _kiem_tep_anh, _lam_nhe
    _quyen(u, VAI_NHAP, "Chỉ Điều hành tải ảnh khách sạn")
    k = _ks(db, kid)
    try:
        duoi = _kiem_tep_anh(ten_tep, data)
    except LoiNhaHang as ex:
        raise LoiKhachSan(str(ex))
    nhom = str(d.get("nhom") or "").strip()
    if nhom not in NHOM_ANH_KS:
        raise LoiKhachSan("Chọn nhóm ảnh")
    lid = d.get("loai_phong_id")
    lid = int(lid) if lid not in (None, "", 0, "0") else None
    if lid is not None:
        lp = db.get(LoaiPhongVtd, lid)
        if lp is None or lp.khach_san_id != k.id:
            raise LoiKhachSan("Loại phòng không thuộc khách sạn này")
    ds = _anh_cua(db, kid)
    cs = AT._sha(data)
    from app.models.attachments import Attachment
    for x in ds:
        a = db.get(Attachment, x.attachment_id)
        if a is not None and a.checksum == cs:
            return x, False
    if len(ds) >= ANH_TOI_DA:
        raise LoiKhachSan(f"Album đã đủ {ANH_TOI_DA} ảnh — ẩn ảnh cũ trước khi tải thêm")
    hien, nho, rong, cao = _lam_nhe(data)
    if hien is None and _co_pil():
        raise LoiKhachSan("Tệp không mở được như một ảnh — kiểm tra lại tệp")
    ma = f"ks{k.id}"
    try:
        a, _ = AT.dinh_kem(db, "khach_san_vtd", ma, ten_tep, data, kieu=KIEU_ANH[duoi], loai="hinh_anh",
                           mo_ta=f"Album {k.ma}", boi=u.username)
        ah = AT.dinh_kem(db, "khach_san_vtd", ma, f"{ten_tep}.hien.webp", hien, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Bản hiển thị · {k.ma}", boi=u.username, nguon="he_thong")[0] if hien else a
        an = AT.dinh_kem(db, "khach_san_vtd", ma, f"{ten_tep}.nho.webp", nho, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Ảnh nhỏ · {k.ma}", boi=u.username, nguon="he_thong")[0] if nho else ah
    except ValueError as ex:
        raise LoiKhachSan(str(ex))
    x = AnhKhachSanVtd(khach_san_id=k.id, loai_phong_id=lid, attachment_id=a.id, hien_id=ah.id, nho_id=an.id,
                       rong=rong, cao=cao, nhom=nhom, chu_thich=str(d.get("chu_thich") or "").strip()[:200],
                       nguon=str(d.get("nguon") or "").strip()[:200], thu_tu=max([y.thu_tu for y in ds], default=0) + 1,
                       la_bia=False, trang_thai="nhap", tai_boi=u.username, tai_luc=now or datetime.now())
    db.add(x)
    db.commit()
    db.refresh(x)
    return x, True


def _lay_anh(db: Session, pid: int) -> AnhKhachSanVtd:
    x = db.get(AnhKhachSanVtd, pid)
    if x is None:
        raise LoiKhachSan("Không có ảnh này", 404)
    return x


def sua_anh(db: Session, u: User, pid: int, d: dict) -> AnhKhachSanVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành sửa ảnh khách sạn")
    x = _lay_anh(db, pid)
    if "nhom" in d:
        if d["nhom"] not in NHOM_ANH_KS:
            raise LoiKhachSan("Nhóm ảnh không hợp lệ")
        x.nhom = d["nhom"]
    if "loai_phong_id" in d:
        lid = d["loai_phong_id"]
        lid = int(lid) if lid not in (None, "", 0, "0") else None
        if lid is not None:
            lp = db.get(LoaiPhongVtd, lid)
            if lp is None or lp.khach_san_id != x.khach_san_id:
                raise LoiKhachSan("Loại phòng không thuộc khách sạn này")
        x.loai_phong_id = lid
    if "chu_thich" in d:
        moi = str(d["chu_thich"] or "").strip()[:200]
        if moi != x.chu_thich and x.trang_thai == "da_duyet":
            x.trang_thai, x.duyet_boi, x.duyet_luc = "cho_duyet", "", None   # chữ ra trước khách: duyệt lại
        x.chu_thich = moi
    if "thu_tu" in d:
        x.thu_tu = int(d["thu_tu"] or 0)
    if d.get("la_bia"):
        for y in _anh_cua(db, x.khach_san_id):
            y.la_bia = y.id == x.id
    db.commit()
    return x


def gui_duyet_anh(db: Session, u: User, ids: list[int]) -> int:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành gửi duyệt ảnh")
    n = 0
    for pid in ids[:200]:
        x = db.get(AnhKhachSanVtd, int(pid))
        if x is not None and x.trang_thai in ("nhap", "tra_lai"):
            x.trang_thai, n = "cho_duyet", n + 1
    db.commit()
    return n


def duyet_anh(db: Session, u: User, ids: list[int], dong_y: bool, ly_do: str = "", now: datetime | None = None) -> dict:
    _quyen(u, VAI_DUYET, "Chỉ TP Điều hành duyệt ảnh")
    if not dong_y and len((ly_do or "").strip()) < 5:
        raise LoiKhachSan("Trả lại phải ghi lý do")
    now = now or datetime.now()
    doi, bo = 0, []
    for pid in ids[:200]:
        x = db.get(AnhKhachSanVtd, int(pid))
        if x is None or x.trang_thai != "cho_duyet":
            continue
        if x.tai_boi == u.username and not _co(u, TOAN_QUYEN):
            bo.append({"id": x.id, "ly_do": "Người tải không tự duyệt"})
            continue
        x.trang_thai = "da_duyet" if dong_y else "tra_lai"
        x.ly_do_tra_lai = "" if dong_y else ly_do.strip()[:300]
        x.duyet_boi, x.duyet_luc = u.username, now
        doi += 1
    db.commit()
    return {"da_doi": doi, "bo_qua": bo}


def an_anh(db: Session, u: User, pid: int, an: bool) -> AnhKhachSanVtd:
    _quyen(u, VAI_NHAP, "Chỉ Điều hành ẩn ảnh")
    x = _lay_anh(db, pid)
    x.trang_thai = "an" if an else "nhap"
    if an:
        x.la_bia = False
    db.commit()
    return x


def tep_anh(db: Session, u: User | None, pid: int, co: str):
    """co: goc (chỉ VTOS) | hien | nho. Cổng (u=None): chỉ ảnh ĐÃ DUYỆT của khách sạn ĐANG HIỆN, không bao giờ bản gốc."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    x = _lay_anh(db, pid)
    if co not in ("goc", "hien", "nho"):
        raise LoiKhachSan("Không có cỡ ảnh này", 404)
    if u is None:
        k = db.get(KhachSanVtd, x.khach_san_id)
        if co == "goc" or x.trang_thai != "da_duyet" or k is None or not k.hien_cong or k.ngung:
            raise LoiKhachSan("Không có ảnh này", 404)
    else:
        _quyen(u, VAI_XEM, "Không có quyền")
    a = db.get(Attachment, {"goc": x.attachment_id, "hien": x.hien_id, "nho": x.nho_id}[co])
    return AT.doc(db, a), a


def _anh_out(x: AnhKhachSanVtd, cong: bool = False) -> dict:
    goc = "/api/v1/ks-vtd-anh" if cong else "/api/v1/khach-san-vtd/anh"
    o = {"id": x.id, "nhom": x.nhom, "nhom_ten": NHOM_ANH_KS.get(x.nhom, x.nhom), "chu_thich": x.chu_thich,
         "loai_phong_id": x.loai_phong_id, "la_bia": x.la_bia,
         "hien": f"{goc}/{x.id}/hien", "nho": f"{goc}/{x.id}/nho"}
    if not cong:
        o.update({"trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_ANH_KS.get(x.trang_thai, x.trang_thai),
                  "ly_do_tra_lai": x.ly_do_tra_lai, "nguon": x.nguon, "tai_boi": x.tai_boi, "duyet_boi": x.duyet_boi,
                  "thu_tu": x.thu_tu, "goc": f"{goc}/{x.id}/goc"})
    return o


# ══ VTOS · ĐỌC ═════════════════════════════════════════════════════════════════════════════════════
def _ks_noi_bo(k: KhachSanVtd) -> dict:
    return {**{x: getattr(k, x) for x in TRUONG_KS}, "id": k.id, "ma": k.ma, "hien_cong": k.hien_cong, "hien_boi": k.hien_boi,
            "tat_ly_do": k.tat_ly_do, "ngung": k.ngung, "sua_boi": k.sua_boi, "tao_boi": k.tao_boi,
            "sua_luc": k.sua_luc.isoformat(timespec="minutes") if k.sua_luc else None}


def _goi_out(g: GoiGiaVtd, mua: list[MuaGiaVtd]) -> dict:
    return {"id": g.id, "loai_phong_id": g.loai_phong_id, "ten": g.ten, "bua_sang": g.bua_sang, "huy_truoc_ngay": g.huy_truoc_ngay,
            "dang_ban": g.dang_ban, "trang_thai": g.trang_thai, "trang_thai_ten": TRANG_THAI_GOI.get(g.trang_thai, g.trang_thai),
            "ly_do_tra_lai": g.ly_do_tra_lai, "sua_boi": g.sua_boi, "duyet_boi": g.duyet_boi,
            "mua": [{"id": m.id, "tu_ngay": m.tu_ngay.isoformat(), "den_ngay": m.den_ngay.isoformat(), "gia_thuong": float(m.gia_thuong),
                     "gia_cuoi_tuan": float(m.gia_cuoi_tuan) if m.gia_cuoi_tuan else None,
                     "gia_niem_yet": float(m.gia_niem_yet) if m.gia_niem_yet else None, "ghi_chu": m.ghi_chu} for m in mua]}


def _goi_cua(db: Session, lids: list[int]) -> dict[int, list[GoiGiaVtd]]:
    ra: dict[int, list] = {}
    if lids:
        for g in db.execute(select(GoiGiaVtd).where(GoiGiaVtd.loai_phong_id.in_(lids)).order_by(GoiGiaVtd.id)).scalars():
            ra.setdefault(g.loai_phong_id, []).append(g)
    return ra


def ds_vtos(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM, "Không có quyền")
    ks = db.execute(select(KhachSanVtd).order_by(KhachSanVtd.tinh_thanh, KhachSanVtd.ten)).scalars().all()
    ids = [k.id for k in ks]
    anh = {}
    lp = {}
    if ids:
        for a in db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.khach_san_id.in_(ids))).scalars():
            anh.setdefault(a.khach_san_id, []).append(a)
        for x in db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.khach_san_id.in_(ids))).scalars():
            lp.setdefault(x.khach_san_id, []).append(x)
    goi = _goi_cua(db, [x.id for v in lp.values() for x in v])
    dong = []
    for k in ks:
        gs = [g for x in lp.get(k.id, []) for g in goi.get(x.id, [])]
        a = anh.get(k.id, [])
        bia = next((x for x in a if x.la_bia and x.trang_thai == "da_duyet"), None) or next((x for x in a if x.trang_thai == "da_duyet"), None)
        dong.append({**_ks_noi_bo(k), "so_anh": len(a), "anh_duyet": sum(x.trang_thai == "da_duyet" for x in a),
                     "anh_cho": sum(x.trang_thai == "cho_duyet" for x in a), "so_loai_phong": len(lp.get(k.id, [])),
                     "goi_duyet": sum(g.trang_thai == "da_duyet" for g in gs), "goi_cho": sum(g.trang_thai == "cho_duyet" for g in gs),
                     "bia": _anh_out(bia)["nho"] if bia else None})
    return {"khach_san": dong, "thanh_pho": [{"ten": t, "mien": MIEN[m]} for t, (m, _k) in THANH_PHO.items()],
            "loai": LOAI_CHO_O, "tien_ich": TIEN_ICH, "nhom_anh": NHOM_ANH_KS,
            "duoc_nhap": _co(u, VAI_NHAP), "duoc_duyet": _co(u, VAI_DUYET), "toi": u.username,
            "toan_quyen": _co(u, TOAN_QUYEN),
            "cho_duyet": {"anh": sum(d["anh_cho"] for d in dong), "goi": sum(d["goi_cho"] for d in dong)}}


def mot_vtos(db: Session, u: User, kid: int) -> dict:
    _quyen(u, VAI_XEM, "Không có quyền")
    k = _ks(db, kid)
    lps = _lp_cua(db, kid)
    goi = _goi_cua(db, [x.id for x in lps])
    mua = _mua_cua(db, [g.id for v in goi.values() for g in v])
    return {"khach_san": _ks_noi_bo(k), "dieu_kien": dieu_kien_hien(db, k),
            "anh": [_anh_out(x) for x in _anh_cua(db, kid)],
            "loai_phong": [{"id": x.id, "ten": x.ten, "dien_tich": x.dien_tich, "giuong": x.giuong, "mo_ta": x.mo_ta,
                            "toi_da_nguoi_lon": x.toi_da_nguoi_lon, "toi_da_tre_em": x.toi_da_tre_em, "so_phong": x.so_phong,
                            "thu_tu": x.thu_tu, "dang_ban": x.dang_ban,
                            "goi": [_goi_out(g, mua.get(g.id, [])) for g in goi.get(x.id, [])]} for x in lps]}


def cho_duyet(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM, "Không có quyền")
    anh = db.execute(select(AnhKhachSanVtd).where(AnhKhachSanVtd.trang_thai == "cho_duyet").order_by(AnhKhachSanVtd.id)).scalars().all()
    goi = db.execute(select(GoiGiaVtd).where(GoiGiaVtd.trang_thai == "cho_duyet").order_by(GoiGiaVtd.id)).scalars().all()
    lp = {x.id: x for x in db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.id.in_([g.loai_phong_id for g in goi] or [0]))).scalars()}
    kids = {a.khach_san_id for a in anh} | {x.khach_san_id for x in lp.values()}
    ks = {k.id: k for k in db.execute(select(KhachSanVtd).where(KhachSanVtd.id.in_(list(kids) or [0]))).scalars()}
    mua = _mua_cua(db, [g.id for g in goi])
    return {"anh": [{**_anh_out(a), "khach_san": ks[a.khach_san_id].ten} for a in anh],
            "goi": [{**_goi_out(g, mua.get(g.id, [])), "loai_phong": lp[g.loai_phong_id].ten,
                     "khach_san": ks[lp[g.loai_phong_id].khach_san_id].ten} for g in goi],
            "duoc_duyet": _co(u, VAI_DUYET), "toi": u.username, "toan_quyen": _co(u, TOAN_QUYEN)}


# ══ CỔNG KHÁCH ═════════════════════════════════════════════════════════════════════════════════════
def _hien(db: Session, tinh: str = "") -> list[KhachSanVtd]:
    q = select(KhachSanVtd).where(KhachSanVtd.hien_cong.is_(True), KhachSanVtd.ngung.is_(False))
    if tinh:
        q = q.where(KhachSanVtd.tinh_thanh == tinh)
    return db.execute(q.order_by(KhachSanVtd.ten)).scalars().all()


def _phong_ban_duoc(db: Session, kids: list[int], vao: date, ra: date, nl: int, te: int, so_phong: int) -> dict[int, list[dict]]:
    """{khách sạn: [loại phòng + các gói BÁN ĐƯỢC cho kỳ ở]} — chỉ gói đã duyệt, đang bán, phủ đủ mọi đêm."""
    if not kids:
        return {}
    lps = db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.khach_san_id.in_(kids), LoaiPhongVtd.dang_ban.is_(True))
                     .order_by(LoaiPhongVtd.thu_tu, LoaiPhongVtd.id)).scalars().all()
    goi = _goi_cua(db, [x.id for x in lps])
    mua = _mua_cua(db, [g.id for v in goi.values() for g in v])
    from app.services import don_ks_vtd as KV   # KS-14: số phòng còn bán cho cả kỳ ở
    con = KV.con_phong(db, lps, vao, ra)
    can_nl, can_te = math.ceil(nl / max(1, so_phong)), math.ceil(te / max(1, so_phong))
    ra_: dict[int, list] = {}
    for x in lps:
        gs = []
        for g in goi.get(x.id, []):
            if g.trang_thai != "da_duyet" or not g.dang_ban:
                continue
            p = gia_luu(g, mua.get(g.id, []), vao, ra)
            if p is None:
                continue
            hh = han_huy(g, vao)
            gs.append({"id": g.id, "ten": g.ten, "bua_sang": g.bua_sang, "huy_truoc_ngay": g.huy_truoc_ngay,
                       "huy_han": hh.isoformat() if hh else None, "mien_phi_huy": g.huy_truoc_ngay is not None,
                       **p, "con": con.get(x.id, 0)})
        gs.sort(key=lambda o: o["tong"])
        ra_.setdefault(x.khach_san_id, []).append({
            "id": x.id, "ten": x.ten, "dien_tich": x.dien_tich, "giuong": x.giuong, "mo_ta": x.mo_ta,
            "toi_da_nguoi_lon": x.toi_da_nguoi_lon, "toi_da_tre_em": x.toi_da_tre_em, "so_phong": x.so_phong,
            "vua": can_nl <= x.toi_da_nguoi_lon and can_te <= x.toi_da_tre_em, "goi": gs, "con": con.get(x.id, 0)})
    return ra_


def _the_cong(k: KhachSanVtd, anh: list[AnhKhachSanVtd], phong: list[dict]) -> dict:
    co_gia = [g for p in phong if p["vua"] for g in p["goi"]]
    goi = [g for p in phong if p["vua"] and p.get("con", 1) > 0 for g in p["goi"]]   # KS-14: bỏ loại phòng đã hết
    re_nhat = min(goi, key=lambda g: g["gia_dem"]) if goi else None
    return {"id": k.id, "ten": k.ten, "sao": k.sao, "loai": k.loai, "loai_ten": LOAI_CHO_O.get(k.loai, k.loai),
            "tinh_thanh": k.tinh_thanh, "khu_vuc": k.khu_vuc, "km_trung_tam": k.km_trung_tam, "gan": k.gan,
            "noi_bat": k.noi_bat, "tien_ich": [TIEN_ICH[t] for t in (k.tien_ich or []) if t in TIEN_ICH],
            "mien": THANH_PHO.get(k.tinh_thanh, ("",))[0],
            "anh": [_anh_out(a, True) for a in anh[:8]], "so_anh": len(anh),
            "gia_tu": ({"gia_dem": re_nhat["gia_dem"], "niem_yet_dem": re_nhat["niem_yet_dem"], "bua_sang": re_nhat["bua_sang"],
                        "mien_phi_huy": re_nhat["mien_phi_huy"]} if re_nhat else None),
            "co_mien_phi_huy": any(g["mien_phi_huy"] for g in goi), "co_bua_sang": any(g["bua_sang"] for g in goi),
            "thue_phi_pt": k.thue_phi_pt,
            "het_phong": bool(co_gia) and not goi,
            # KS-14: điểm đánh giá của khách đã ở. Chưa có đơn đặt nên chưa có bài nào.
            "danh_gia": {"so_bai": 0, "diem_tb": None}}


def tim(db: Session, tinh: str, vao, ra, nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
        hom_nay: date | None = None) -> dict:
    vao, ra = _kiem_ky(vao, ra, hom_nay)
    nl, te, sp = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0)), max(1, int(so_phong or 1))
    if sp > 9 or nl > 30 or te > 20:
        raise LoiKhachSan("Tối đa 9 phòng, 30 người lớn, 20 trẻ em một lần đặt")
    tat_ca = _hien(db)
    dem_tp: dict[str, int] = {}
    for k in tat_ca:
        dem_tp[k.tinh_thanh] = dem_tp.get(k.tinh_thanh, 0) + 1
    ks = [k for k in tat_ca if not tinh or k.tinh_thanh == tinh]
    anh = _anh_duyet(db, [k.id for k in ks])
    phong = _phong_ban_duoc(db, [k.id for k in ks], vao, ra, nl, te, sp)
    the = [_the_cong(k, anh.get(k.id, []), phong.get(k.id, [])) for k in ks]
    the.sort(key=lambda o: (o["gia_tu"] is None, o["ten"]))
    return {"khach_san": the, "tong": len(the), "dem": (ra - vao).days, "vao": vao.isoformat(), "ra": ra.isoformat(),
            "nguoi_lon": nl, "tre_em": te, "so_phong": sp,
            "thanh_pho": [{"ten": t, "so": dem_tp[t]} for t in sorted(dem_tp, key=lambda t: -dem_tp[t])],
            "loai": LOAI_CHO_O}


def chi_tiet_cong(db: Session, kid: int, vao, ra, nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
                  hom_nay: date | None = None) -> dict:
    vao, ra = _kiem_ky(vao, ra, hom_nay)
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiKhachSan("Khách sạn này không còn hiện trên VTD", 404)
    nl, te, sp = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0)), max(1, int(so_phong or 1))
    anh = _anh_duyet(db, [k.id]).get(k.id, [])
    phong = _phong_ban_duoc(db, [k.id], vao, ra, nl, te, sp).get(k.id, [])
    for p in phong:
        p["anh"] = [_anh_out(a, True) for a in anh if a.loai_phong_id == p["id"]][:6]
    the = _the_cong(k, anh, phong)
    return {**the, "dia_chi": k.dia_chi, "mo_ta": k.mo_ta, "gio_nhan": k.gio_nhan, "gio_tra": k.gio_tra,
            "chinh_sach": {"tre_em": k.cs_tre_em, "giuong_phu": k.cs_giuong_phu, "vat_nuoi": k.cs_vat_nuoi, "khac": k.cs_khac},
            "anh": [_anh_out(a, True) for a in anh], "nhom_anh": NHOM_ANH_KS,
            "phong": phong, "dem": (ra - vao).days, "vao": vao.isoformat(), "ra": ra.isoformat(),
            "nguoi_lon": nl, "tre_em": te, "so_phong": sp, "the_bat": _the_bat()}


def _the_bat() -> bool:
    from app.services import sepay_pg as SP   # SP-1: nút trả thẻ chỉ hiện khi có cổng thẻ
    return SP.cong_the_bat()


def tinh_lua_chon(db: Session, kid: int, vao, ra, chon: list[dict], hom_nay: date | None = None) -> dict:
    """Máy TÍNH LẠI phòng khách chọn từ giá đã duyệt. chon = [{goi_id, so}] — không nhận số tiền nào từ trình duyệt."""
    vao, ra = _kiem_ky(vao, ra, hom_nay)
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiKhachSan("Khách sạn này không còn hiện trên VTD", 404)
    dong, tien, so = [], 0, 0
    for c in chon or []:
        n = int(c.get("so") or 0)
        if n <= 0:
            continue
        g = db.get(GoiGiaVtd, int(c.get("goi_id") or 0))
        lp = db.get(LoaiPhongVtd, g.loai_phong_id) if g else None
        if g is None or lp is None or lp.khach_san_id != k.id or g.trang_thai != "da_duyet" or not g.dang_ban or not lp.dang_ban:
            raise LoiKhachSan("Gói giá đã thay đổi — tải lại trang để xem giá mới", 409)
        if n > lp.so_phong:
            raise LoiKhachSan(f"«{lp.ten}» chỉ còn tối đa {lp.so_phong} phòng")
        p = gia_luu(g, _mua_cua(db, [g.id]).get(g.id, []), vao, ra)
        if p is None:
            raise LoiKhachSan(f"«{lp.ten} · {g.ten}» chưa có giá cho các ngày này", 409)
        dong.append({"loai_phong": lp.ten, "goi": g.ten, "so": n, "tong": p["tong"] * n, "bua_sang": g.bua_sang,
                     "huy_han": (han_huy(g, vao).isoformat() if g.huy_truoc_ngay is not None else None)})
        tien += p["tong"] * n
        so += n
    thue = round(tien * (k.thue_phi_pt or 0) / 100)
    return {"dong": dong, "so_phong": so, "tien_phong": tien, "thue_phi": thue, "tong": tien + thue, "dem": (ra - vao).days}


def gui_yeu_cau_giu(db: Session, tk, kid: int, d: dict, hom_nay: date | None = None):
    """Khách gửi yêu cầu giữ phòng — đi vào hàng chờ KS-11 của Điều hành (Điều hành báo giá / giữ phòng với khách sạn)."""
    from app.services import dat_phong_ota as DP
    vao, ra = _kiem_ky(d.get("ngay_nhan"), d.get("ngay_tra"), hom_nay)
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiKhachSan("Khách sạn này không còn hiện trên VTD", 404)
    lc = tinh_lua_chon(db, kid, vao, ra, d.get("chon") or [], hom_nay) if d.get("chon") else None
    dong = [f"Khách sạn hợp tác VTD: {k.ma} · {k.ten} ({k.tinh_thanh})"]
    if lc and lc["dong"]:
        for x in lc["dong"]:
            dong.append(f"- {x['so']} × {x['loai_phong']} · {x['goi']}: {x['tong']:,.0f} đ / {lc['dem']} đêm".replace(",", "."))
        dong.append(f"Giá VTD lúc gửi: phòng {lc['tien_phong']:,.0f} đ + thuế phí {lc['thue_phi']:,.0f} đ = {lc['tong']:,.0f} đ".replace(",", "."))
    elif d.get("loai_phong"):
        dong.append(f"Loại phòng quan tâm: {str(d['loai_phong'])[:120]}")
    if str(d.get("yeu_cau_them") or "").strip():
        dong.append("Ghi chú của khách: " + str(d["yeu_cau_them"]).strip()[:1200])
    so_phong = (lc["so_phong"] if lc and lc["so_phong"] else int(d.get("so_phong") or 1))
    gui = {"noi_den": f"{k.ten} · {k.tinh_thanh}"[:160], "ngay_nhan": vao, "ngay_tra": ra, "so_phong": so_phong,
           "nguoi_lon": int(d.get("nguoi_lon") or 1), "tre_em": int(d.get("tre_em") or 0),
           "nguoi_nhan_phong": d.get("nguoi_nhan_phong") or "", "lien_he": d.get("lien_he") or "",
           "yeu_cau_them": "\n".join(dong)}
    try:
        don = DP.gui_yeu_cau(db, tk, gui)
    except DP.LoiOta as ex:
        raise LoiKhachSan(str(ex), getattr(ex, "status", 400))
    return DP.tom_tat_khach(don)


def tim_ten(ds: list[dict], q: str) -> list[dict]:
    k = _khong_dau(q.strip())
    return [o for o in ds if k in _khong_dau(" ".join((o["ten"], o["khu_vuc"], o["gan"])))] if k else ds
