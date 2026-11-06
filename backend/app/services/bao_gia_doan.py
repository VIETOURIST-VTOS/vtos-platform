"""TK-2 · Báo giá chính thức tour đoàn khách tự thiết kế — giai đoạn 2 (Chủ tịch 04/11/2026, duyệt bản xem thử;
hạn 24 giờ; trẻ em 75% giá người lớn với tour đi xe, 80% khi có chặng bay; khách đồng ý → hợp đồng nháp).

Vòng đời một báo giá (đầu ở bảng chung bao_gia, phần riêng ở bao_gia_thiet_ke — KS-19k 06/11/2026):
  nhap ─(Điều hành gửi duyệt)→ cho_duyet ─(duyệt)→ da_gui (khóa, hiện cho khách 24 giờ) ─(khách đồng ý)→ khach_chot
                                         └(trả lại)→ tra_lai ─(sửa, gửi lại)→ cho_duyet
  da_gui quá hạn → het_han · khách gửi phiên bản thiết kế mới → mọi báo giá chưa đồng ý của mã ấy → thay_the.

TIỀN — máy tính lại mỗi lần lưu, không nhận số tiền nào từ trình duyệt ngoài GIÁ VỐN từng dòng do Điều hành nhập:
  giá bán dòng = vốn ÷ (1 − biên), làm tròn lên nghìn · tổng bán dòng = Σ
  giá người lớn = tổng bán dòng ÷ (NL + hệ số TE × TE), làm tròn lên nghìn · giá trẻ em = hệ số × giá NL (lên nghìn)
  tổng khách trả = giá NL × NL + giá TE × TE (em bé không tính) · biên thực = (tổng khách trả − tổng vốn) ÷ tổng khách trả
Cấp duyệt theo biên thực: ≥ 10% → TP Điều hành (người duyệt khác người lập); < 10% → Chủ tịch / TGĐ, bắt buộc lý do.
Sales thấy giá bán, không thấy giá vốn / biên.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ban_hang import BaoGia
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.models.thiet_ke_doan import TRANG_THAI_BG, BaoGiaDoan, ThietKeDoan
from app.services import rules as R
from app.services import thiet_ke_doan as T

HAN_GIO = 24                       # Chủ tịch 04/11/2026: báo giá hiệu lực 24 giờ kể từ khi duyệt
HE_SO_TE_XE, HE_SO_TE_BAY = 0.75, 0.80
NGUONG = T.NGUONG_DUYET            # 10%
VAI_LAP = T.TOAN_QUYEN + ("tp_dh", "nv_dh")
VAI_DUYET_TP = T.TOAN_QUYEN + ("tp_dh",)
CON_SUA = ("nhap", "tra_lai")


class LoiBaoGia(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _quyen(u: User, vai: tuple, msg: str) -> None:
    if u.role not in vai:
        raise LoiBaoGia(msg, 403)


def _len_nghin(x: float) -> int:
    return int(math.ceil(float(x) / 1000.0) * 1000) if x > 0 else 0


def he_so_te(tk: dict) -> float:
    return HE_SO_TE_BAY if any(c.get("pt") == "bay" for c in tk.get("chang", [])) else HE_SO_TE_XE


def tinh(bg: BaoGiaDoan) -> None:
    """Tính lại mọi con số tiền của báo giá từ giá vốn từng dòng + biên + số khách."""
    b = float(bg.bien_pt or 0) / 100
    if not 0 <= b < 0.9:
        raise LoiBaoGia("Biên phải từ 0% đến dưới 90%")
    dong, von, ban = [], 0.0, 0
    for x in bg.dong or []:
        v = x.get("von")
        y = {**x, "ban": None if v is None else _len_nghin(float(v) / (1 - b)) if float(v) > 0 else 0}
        if v is not None:
            von += float(v)
            ban += y["ban"]
        dong.append(y)
    bg.dong = dong
    nl, te = int(bg.so_nl or 0), int(bg.so_te or 0)
    k = float(bg.he_so_te or HE_SO_TE_XE)
    if ban and nl:
        gnl = _len_nghin(ban / (nl + k * te))
        gte = _len_nghin(gnl * k)
        bg.gia_nl, bg.gia_te, bg.tong_ban = gnl, gte, gnl * nl + gte * te
    else:
        bg.gia_nl = bg.gia_te = bg.tong_ban = None
    bg.tong_von = round(von) if dong else None


def bien_thuc(bg: BaoGiaDoan) -> float | None:
    if bg.tong_ban is None or not bg.tong_ban:      # K2: rỗng = chưa có giá bán → chưa có biên
        return None
    return (float(bg.tong_ban) - float(bg.tong_von or 0)) / float(bg.tong_ban)


def _thieu(bg: BaoGiaDoan) -> list[str]:
    return [x["ten"] for x in (bg.dong or []) if x.get("von") is None]


def _het_han_neu_qua(bg: BaoGiaDoan, now: datetime) -> None:
    if bg.trang_thai == "da_gui" and bg.han_luc and now > bg.han_luc:
        bg.trang_thai = "het_han"


def _bam(bg: BaoGiaDoan) -> str:
    goc = {"ma": bg.ma, "dong": [{k: x.get(k) for k in ("ten", "chi_tiet", "ban")} for x in bg.dong or []],
           "gia_nl": bg.gia_nl, "gia_te": bg.gia_te, "tong_ban": bg.tong_ban, "han": bg.han_luc.isoformat() if bg.han_luc else ""}
    return hashlib.sha256(json.dumps(goc, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def ra(bg: BaoGiaDoan, von: bool) -> dict:
    b = bien_thuc(bg)
    o = {"id": bg.id, "ma": bg.ma, "thiet_ke_id": bg.thiet_ke_id, "thiet_ke_ma": bg.thiet_ke_ma,
         "trang_thai": bg.trang_thai, "trang_thai_ten": TRANG_THAI_BG.get(bg.trang_thai, bg.trang_thai),
         "dong": [{k: v for k, v in x.items() if von or k != "von"} for x in bg.dong or []],
         "so_nl": bg.so_nl, "so_te": bg.so_te, "so_eb": bg.so_eb, "he_so_te": float(bg.he_so_te or 0),
         "gia_nl": bg.gia_nl, "gia_te": bg.gia_te, "tong_ban": bg.tong_ban, "bao_gom": bg.bao_gom or [],
         "khong_bao_gom": bg.khong_bao_gom or [], "ghi_chu": bg.ghi_chu, "thieu_gia": _thieu(bg),
         "tao_boi": bg.tao_boi, "tao_luc": bg.tao_luc.isoformat(timespec="minutes") if bg.tao_luc else None,
         "duyet_boi": bg.duyet_boi, "duyet_luc": bg.duyet_luc.isoformat(timespec="minutes") if bg.duyet_luc else None,
         "han_luc": bg.han_luc.isoformat(timespec="minutes") if bg.han_luc else None, "ly_do_tra": bg.ly_do_tra,
         "hop_dong_id": bg.hop_dong_id, "khach_dong_y_luc": bg.khach_dong_y_luc.isoformat(timespec="minutes") if bg.khach_dong_y_luc else None}
    if von:
        o.update({"tong_von": bg.tong_von, "bien_pt":  # k2-doc-an-toan: tong_von chỉ chuyển nguyên giá trị ra (rỗng = chưa đủ giá vốn), không tính
                   float(bg.bien_pt or 0), "bien_thuc": round(b, 4) if b is not None else None,
                  "cap_duyet": bg.cap_duyet or ("tp_dh" if b is not None and b >= NGUONG - 1e-9 else "ct_tgd"),
                  "ly_do_bien": bg.ly_do_bien})
    return o


# ══ VTOS ════════════════════════════════════════════════════════════════════════════════════════════
def lap(db: Session, u: User, thiet_ke_id: int, now: datetime | None = None) -> dict:
    """Lập báo giá từ một phiên bản thiết kế đang hiệu lực. Đã có bản đang soạn / chờ duyệt thì trả bản ấy."""
    _quyen(u, VAI_LAP, "Chỉ Điều hành lập báo giá")
    now = now or datetime.now()
    tk = db.get(ThietKeDoan, thiet_ke_id)
    if tk is None:
        raise LoiBaoGia("Không có thiết kế này", 404)
    if tk.trang_thai != "da_gui":
        raise LoiBaoGia("Thiết kế này đã có phiên bản mới hơn — lập báo giá từ phiên bản mới nhất", 409)
    cu = db.execute(select(BaoGiaDoan).join(BaoGia, BaoGia.id == BaoGiaDoan.id)
                    .where(BaoGiaDoan.thiet_ke_id == tk.id, BaoGia.trang_thai.in_(["nhap", "tra_lai", "cho_duyet"]))).scalars().first()
    if cu is not None:
        return ra(cu, True)
    d, t = tk.du_toan or {}, tk.thiet_ke or {}
    dong = [{"nhom": x["nhom"], "ten": x["ten"], "chi_tiet": x.get("chi_tiet", ""), "von": x.get("von"), "nguon": "tạm tính"}
            for x in d.get("dong", [])]
    dong += [{"nhom": x["nhom"], "ten": x["ten"], "chi_tiet": x.get("ly_do", ""), "von": None, "nguon": "thiếu giá"}
             for x in d.get("thieu_gia", [])]
    k = t.get("khach") or {}
    so = db.execute(select(func.count()).select_from(BaoGiaDoan)).scalar() or 0
    while True:                                              # mã BGD-… giữ như trước KS-19k, không trùng
        so += 1
        if db.execute(select(BaoGia.id).where(BaoGia.ma == f"BGD-{so:06d}")).first() is None:
            break
    kh = db.get(TaiKhoanNgoai, tk.tai_khoan_id)
    so_nl, so_te, so_eb = int(k.get("nl") or 0), int(k.get("te") or 0), int(k.get("eb") or 0)
    dau = BaoGia(ma=f"BGD-{so:06d}", mang="kd_doan", nguon="thiet_ke",
                 khach_ten=(((kh.ho_ten or kh.dien_thoai) if kh else "") or f"Khách cổng #{tk.tai_khoan_id}")[:200],
                 khach_dien_thoai=(kh.dien_thoai if kh else "")[:30], khach_email=(kh.email if kh else "")[:120],
                 ngay_khoi_hanh=tk.ngay_di, so_khach=so_nl + so_te + so_eb, trang_thai="nhap", tao_boi=u.username,
                 tao_luc=now)
    db.add(dau)
    db.flush()
    bg = BaoGiaDoan(id=dau.id, dau=dau, thiet_ke_id=tk.id, thiet_ke_ma=tk.ma, tai_khoan_id=tk.tai_khoan_id, dong=dong,
                    bien_pt=T.BIEN_TAM_TINH * 100, he_so_te=he_so_te(t), so_nl=so_nl, so_te=so_te, so_eb=so_eb,
                    bao_gom=list(d.get("bao_gom", [])), khong_bao_gom=list(d.get("khong_bao_gom", [])))
    tinh(bg)
    db.add(bg)
    db.flush()
    R.audit(db, u.username, u.role, "bao_gia_doan_lap", f"bao_gia_doan:{bg.ma}", after={"thiet_ke": f"{tk.ma}#{tk.phien_ban}"})
    db.commit()
    return ra(bg, True)


def _lay(db: Session, bid: int) -> BaoGiaDoan:
    bg = db.get(BaoGiaDoan, bid)
    if bg is None:
        raise LoiBaoGia("Không có báo giá này", 404)
    return bg


def xem(db: Session, u: User, bid: int, now: datetime | None = None) -> dict:
    T._quyen(u, T.VAI_XEM)
    bg = _lay(db, bid)
    _het_han_neu_qua(bg, now or datetime.now())
    db.commit()
    return ra(bg, T._co(u, T.VAI_GIA_VON))


def luu(db: Session, u: User, bid: int, d: dict) -> dict:
    """Điều hành sửa: giá vốn từng dòng (rỗng = còn thiếu), thêm / bớt dòng, biên %, bao gồm / không bao gồm, ghi chú."""
    _quyen(u, VAI_LAP, "Chỉ Điều hành sửa báo giá")
    bg = _lay(db, bid)
    if bg.trang_thai not in CON_SUA:
        raise LoiBaoGia("Báo giá đã gửi duyệt hoặc đã duyệt — không sửa được", 409)
    if "dong" in d:
        dong = []
        for x in (d.get("dong") or [])[:80]:
            ten = T._sach(x.get("ten"), 200)
            if not ten:
                continue
            v = x.get("von")
            v = None if v in (None, "") else T._tien(v, f"giá vốn «{ten}»")
            dong.append({"nhom": T._sach(x.get("nhom"), 40) or "Khác", "ten": ten, "chi_tiet": T._sach(x.get("chi_tiet"), 200),
                         "von": v, "nguon": T._sach(x.get("nguon"), 40) or "Điều hành nhập"})
        if not dong:
            raise LoiBaoGia("Báo giá cần ít nhất một dòng")
        bg.dong = dong
    if "bien_pt" in d and d["bien_pt"] not in (None, ""):
        bg.bien_pt = float(d["bien_pt"])
    for k in ("bao_gom", "khong_bao_gom"):
        if k in d:
            setattr(bg, k, [T._sach(x, 200) for x in (d.get(k) or []) if T._sach(x, 200)][:30])
    if "ghi_chu" in d:
        bg.ghi_chu = T._sach(d.get("ghi_chu"), 1000)
    tinh(bg)
    R.audit(db, u.username, u.role, "bao_gia_doan_luu", f"bao_gia_doan:{bg.ma}",
            after={"tong_von": bg.tong_von, "tong_ban": bg.tong_ban, "bien_pt": float(bg.bien_pt or 0)})
    db.commit()
    return ra(bg, True)


def gui_duyet(db: Session, u: User, bid: int, ly_do: str = "", now: datetime | None = None) -> dict:
    _quyen(u, VAI_LAP, "Chỉ Điều hành gửi duyệt báo giá")
    bg = _lay(db, bid)
    if bg.trang_thai not in CON_SUA:
        raise LoiBaoGia("Báo giá không ở trạng thái soạn", 409)
    tinh(bg)
    th = _thieu(bg)
    if th:
        raise LoiBaoGia(f"Còn {len(th)} dòng chưa có giá vốn: {', '.join(th[:3])}")
    if not bg.tong_ban:
        raise LoiBaoGia("Báo giá chưa có tiền")
    b = bien_thuc(bg)
    bg.cap_duyet = "tp_dh" if b >= NGUONG - 1e-9 else "ct_tgd"
    if bg.cap_duyet == "ct_tgd":
        if not T._sach(ly_do):
            raise LoiBaoGia(f"Biên {b * 100:.1f}% dưới {NGUONG * 100:.0f}% — ghi lý do để Chủ tịch / TGĐ duyệt")
        bg.ly_do_bien = T._sach(ly_do, 300)
    bg.trang_thai, bg.gui_duyet_luc, bg.ly_do_tra = "cho_duyet", now or datetime.now(), ""
    bg.dau.duoi_bien, bg.dau.giai_trinh = bg.cap_duyet == "ct_tgd", bg.ly_do_bien if bg.cap_duyet == "ct_tgd" else ""
    R.audit(db, u.username, u.role, "bao_gia_doan_gui_duyet", f"bao_gia_doan:{bg.ma}",
            after={"bien_thuc": round(b, 4), "cap_duyet": bg.cap_duyet})
    db.commit()
    return ra(bg, True)


def duyet(db: Session, u: User, bid: int, dong_y: bool, ly_do: str = "", now: datetime | None = None) -> dict:
    now = now or datetime.now()
    bg = _lay(db, bid)
    if bg.trang_thai != "cho_duyet":
        raise LoiBaoGia("Báo giá không ở trạng thái chờ duyệt", 409)
    if bg.cap_duyet == "ct_tgd":
        _quyen(u, T.TOAN_QUYEN, "Biên dưới 10% — chỉ Chủ tịch / TGĐ duyệt")
    else:
        _quyen(u, VAI_DUYET_TP, "Chỉ TP Điều hành, Chủ tịch, TGĐ duyệt báo giá")
        if u.username == bg.tao_boi and u.role not in T.TOAN_QUYEN:
            raise LoiBaoGia("Người lập không tự duyệt báo giá của mình", 403)
    tk = db.get(ThietKeDoan, bg.thiet_ke_id)
    if tk is None or tk.trang_thai != "da_gui":
        bg.trang_thai = "thay_the"
        db.commit()
        raise LoiBaoGia("Khách đã gửi phiên bản thiết kế mới — báo giá này không còn hiệu lực", 409)
    if not dong_y:
        if not T._sach(ly_do):
            raise LoiBaoGia("Ghi lý do trả lại")
        bg.trang_thai, bg.ly_do_tra = "tra_lai", T._sach(ly_do, 300)
        bg.dau.ly_do_tu_choi = bg.ly_do_tra
    else:
        bg.trang_thai, bg.duyet_boi, bg.duyet_luc = "da_gui", u.username, now
        bg.han_luc = now + timedelta(hours=HAN_GIO)
        bg.dau.han_hieu_luc, bg.dau.bien_luc_gui, bg.dau.nguong_luc_gui = bg.han_luc.date(), bien_thuc(bg), NGUONG
        bg.ma_bam = _bam(bg)
        gia = f"{int(bg.tong_ban):,} đ" if bg.tong_ban is not None else "chưa có giá"   # K2: rỗng không thành «0 đ»
        _ghi_lead(db, tk, f"Báo giá {bg.ma} đã gửi khách: {gia}, hiệu lực đến {bg.han_luc:%d/%m %H:%M}".replace(",", "."))
    R.audit(db, u.username, u.role, "bao_gia_doan_duyet", f"bao_gia_doan:{bg.ma}",
            after={"trang_thai": bg.trang_thai, "ly_do": bg.ly_do_tra})
    db.commit()
    return ra(bg, True)


def _ghi_lead(db: Session, tk: ThietKeDoan, dong: str) -> None:
    """Nối một dòng vào ghi chú lead của yêu cầu — Sales theo dõi ở hộp lead như mọi yêu cầu khách."""
    from app.models.cong_khach import YeuCauKhach
    from app.models.crm import Lead
    yc = db.get(YeuCauKhach, tk.yeu_cau_id) if tk.yeu_cau_id else None
    lead = db.get(Lead, yc.lead_id) if yc is not None and yc.lead_id else None
    if lead is not None:
        lead.note = (((lead.note or "").strip() + "\n") if (lead.note or "").strip() else "") + f"[{datetime.now():%d/%m %H:%M}] {dong}"
        lead.note = lead.note[-2000:]


def theo_thiet_ke(db: Session, u: User, thiet_ke_ma: str, now: datetime | None = None) -> list[dict]:
    T._quyen(u, T.VAI_XEM)
    ds = db.execute(select(BaoGiaDoan).where(BaoGiaDoan.thiet_ke_ma == thiet_ke_ma).order_by(BaoGiaDoan.id.desc())).scalars().unique().all()
    for bg in ds:
        _het_han_neu_qua(bg, now or datetime.now())
    db.commit()
    return [ra(bg, T._co(u, T.VAI_GIA_VON)) for bg in ds]


def thay_the_khi_sua(db: Session, thiet_ke_ma: str) -> int:
    """Khách gửi phiên bản thiết kế mới → báo giá chưa được khách đồng ý của mã ấy hết hiệu lực."""
    n = 0
    for bg in db.execute(select(BaoGiaDoan).join(BaoGia, BaoGia.id == BaoGiaDoan.id)
                         .where(BaoGiaDoan.thiet_ke_ma == thiet_ke_ma,
                                BaoGia.trang_thai.in_(["nhap", "tra_lai", "cho_duyet", "da_gui"]))).scalars().unique():
        bg.trang_thai = "thay_the"
        n += 1
    return n


# ══ CỔNG KHÁCH ══════════════════════════════════════════════════════════════════════════════════════
def cho_khach(db: Session, tk_: TaiKhoanNgoai, thiet_ke_ma: str, now: datetime | None = None) -> dict | None:
    """Báo giá mới nhất khách được thấy của một mã thiết kế (đã duyệt / hết hạn / đã đồng ý)."""
    bg = db.execute(select(BaoGiaDoan).join(BaoGia, BaoGia.id == BaoGiaDoan.id)
                    .where(BaoGiaDoan.thiet_ke_ma == thiet_ke_ma, BaoGiaDoan.tai_khoan_id == tk_.id,
                           BaoGia.trang_thai.in_(["da_gui", "het_han", "khach_chot"]))
                    .order_by(BaoGiaDoan.id.desc())).scalars().first()
    if bg is None:
        return None
    _het_han_neu_qua(bg, now or datetime.now())
    o = ra(bg, False)
    o["ma_bam"] = bg.ma_bam
    return o


def khach_dong_y(db: Session, tk_: TaiKhoanNgoai, bid: int, ma_bam: str, dong_y: bool, now: datetime | None = None) -> dict:
    """Khách bấm «Đồng ý báo giá» → khach_dong_y + hợp đồng khách NHÁP (Sale Admin hoàn thiện). Chưa thu tiền."""
    from app.models.ban_hang import HopDongKhach
    from app.services.ban_hang import sinh_ma
    T._khach(tk_)
    now = now or datetime.now()
    bg = db.get(BaoGiaDoan, bid)
    if bg is None or bg.tai_khoan_id != tk_.id:
        raise LoiBaoGia("Không tìm thấy báo giá", 404)
    if not dong_y:
        raise LoiBaoGia("Đánh dấu ô đồng ý báo giá")
    _het_han_neu_qua(bg, now)
    if bg.trang_thai == "khach_chot":
        return {**ra(bg, False), "message": "Bạn đã đồng ý báo giá này"}
    if bg.trang_thai == "het_han":
        db.commit()
        raise LoiBaoGia("Báo giá đã hết hạn — gửi lại thiết kế hoặc liên hệ Sales để nhận báo giá mới", 410)
    if bg.trang_thai != "da_gui":
        raise LoiBaoGia("Báo giá không còn hiệu lực", 409)
    if not ma_bam or ma_bam != bg.ma_bam or _bam(bg) != bg.ma_bam:
        raise LoiBaoGia("Báo giá đã thay đổi — tải lại trang để xem bản mới", 409)
    tk = db.get(ThietKeDoan, bg.thiet_ke_id)
    if tk is None or tk.trang_thai != "da_gui":
        bg.trang_thai = "thay_the"
        db.commit()
        raise LoiBaoGia("Bạn đã gửi phiên bản thiết kế mới — báo giá này không còn hiệu lực", 409)
    t = tk.thiet_ke or {}
    hd = HopDongKhach(bao_gia_id=bg.id, so_hop_dong=sinh_ma(db, HopDongKhach, HopDongKhach.so_hop_dong, "HD"),
                      khach_ten=(tk_.ho_ten or tk_.dien_thoai or f"Khách cổng #{tk_.id}")[:200], gia_tri=float(bg.tong_ban or 0),
                      trang_thai="nhap", tao_boi="cong_khach", tao_luc=now,
                      ghi_chu=(f"Tự tạo khi khách đồng ý báo giá {bg.ma} (tour đoàn khách tự thiết kế {tk.ma} phiên bản "
                               f"{tk.phien_ban}): {bg.so_nl} NL × {int(bg.gia_nl or 0):,} đ + {bg.so_te} TE × {int(bg.gia_te or 0):,} đ"
                               f"{f' + {bg.so_eb} em bé' if bg.so_eb else ''}, khởi hành {t.get('ngay_di', '')}. "
                               "Sale Admin hoàn thiện thông tin khách, số đợt thanh toán rồi ký.").replace(",", "."))
    db.add(hd)
    db.flush()
    bg.trang_thai, bg.khach_dong_y_luc, bg.hop_dong_id = "khach_chot", now, hd.id
    _ghi_lead(db, tk, f"Khách ĐỒNG Ý báo giá {bg.ma} — hợp đồng nháp {hd.so_hop_dong}")
    R.audit(db, f"cong:{tk_.id}", "khach", "bao_gia_doan_khach_dong_y", f"bao_gia_doan:{bg.ma}",
            after={"hop_dong": hd.so_hop_dong, "tong_ban": bg.tong_ban, "ma_bam": bg.ma_bam})
    db.commit()
    return {**ra(bg, False), "hop_dong": hd.so_hop_dong,
            "message": f"Cảm ơn bạn đã đồng ý báo giá {bg.ma}. Sales Vietourist sẽ liên hệ ký hợp đồng {hd.so_hop_dong}."}
