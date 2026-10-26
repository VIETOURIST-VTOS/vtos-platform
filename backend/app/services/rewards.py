"""KH-3 · VTD Rewards — Chủ tịch chốt ĐÚNG số dự thảo đặc tả v3.0 và duyệt bản xem thử 26/10/2026.

  Hạng (chi tiêu xét hạng 12 tháng cuốn chiếu): Member < 30 tr ×1,00 · Plus 30–<100 tr ×1,25 · Premium ≥ 100 tr ×1,50.
  Cộng điểm: P = floor(B / 10.000 × hệ số hạng LÚC CHUYẾN ĐỦ ĐIỀU KIỆN, không tính chính chuyến ấy).
  1 điểm = 100 đ ưu đãi; một booking dùng voucher tối đa 5% giá trị; điểm hết hạn 12 tháng từ lần cộng.
  Giữ hạng 30 ngày khi chi tiêu tụt dưới ngưỡng.

  B = giá trị booking sau giảm giá (gồm cả voucher đã áp). Đủ điều kiện = booking TRỰC TIẾP (không qua đại lý /
  CTV), không hủy, tour đã kết thúc VÀ đã thu đủ — cùng phép đo với D06 (`hoa_hong_d06.tinh_trang_booking`).
  Chỉ cộng cho chuyến đủ điều kiện TỪ ngày hiệu lực Chủ tịch ký (`rewards_hieu_luc_tu`), không hồi tố.
  Hạng thì xét trên mọi chuyến 12 tháng — khách thấy đúng chi tiêu thật của mình.

  Sổ chỉ ghi thêm và TỰ ĐỐI CHIẾU: mỗi lần tính, điểm đích của từng booking so với điểm đã ghi → ghi phần chênh.
  Hủy / hoàn / giảm giá sau khi đã cộng → dòng DAO. Chạy lại không ghi gì nếu không có gì đổi.
"""
import math
import secrets
from datetime import date, datetime, timedelta
from fractions import Fraction
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Booking, Tour, User
from app.models.rewards import SoDiem, VoucherRewards, YeuThich, LOAI_DONG, TRANG_THAI_VOUCHER
from app.services.zalo import norm_phone

KHOA_HIEU_LUC = "rewards_hieu_luc_tu"
HANG = (("Member", 0, Fraction(1)), ("Plus", 30_000_000, Fraction(5, 4)), ("Premium", 100_000_000, Fraction(3, 2)))
DONG_MOI_DIEM = 10_000
GIA_TRI_DIEM = 100
TRAN_VOUCHER = Fraction(5, 100)
HAN_DIEM_NGAY = 365
GIU_HANG_NGAY = 30
HAN_VOUCHER_NGAY = 30
DIEM_DOI_TOI_THIEU = 100
GIA_HAN_KHI_TRA = 30

TOAN_QUYEN = ("chutich", "tgd")
VAI_AP = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "sales_admin") + TOAN_QUYEN
VAI_XEM = tuple(dict.fromkeys(VAI_AP + ("bks", "robot_ks", "ketoan", "nv_mkt", "ptgd_mkt")))


class LoiDiem(ValueError):
    pass


def _hom_nay() -> date:
    return date.today()


def hieu_luc_tu(db: Session) -> date | None:
    from app.services import moi_truong_du_lieu as MT
    from app.services import rules as R
    try:
        return MT.doc_ngay(str(R.get_param_chu(db, KHOA_HIEU_LUC)).strip())
    except (KeyError, ValueError):
        return None


# ── chủ điểm ────────────────────────────────────────────────────────────────────────────────────

def chu_cua_booking(b: Booking) -> str | None:
    sdt = norm_phone(b.customer_phone or "")
    if len(sdt) == 10 and sdt.startswith("0"):
        return f"sdt:{sdt}"
    em = (b.customer_email or "").strip().lower()
    return f"email:{em}" if "@" in em else None


def chu_tu_lien_he(q: str) -> str | None:
    q = (q or "").strip()
    if "@" in q:
        return f"email:{q.lower()}"
    sdt = norm_phone(q)
    return f"sdt:{sdt}" if len(sdt) == 10 and sdt.startswith("0") else None


def chu_cua_tai_khoan(tk) -> list[str]:
    ra = []
    if tk.dien_thoai:
        ra.append(f"sdt:{tk.dien_thoai}")
    if tk.email:
        ra.append(f"email:{tk.email.lower()}")
    return ra


def _bookings(db: Session, chu: str) -> list[Booking]:
    """Booking TRỰC TIẾP của chủ điểm (kể cả đã hủy — cần để trừ điểm)."""
    kieu, gt = chu.split(":", 1)
    cau = select(Booking).where(Booking.doi_tac_id.is_(None))
    if kieu == "sdt":
        cau = cau.where(Booking.customer_phone.like("%" + "%".join(gt[-9:])))
    else:
        cau = cau.where(func.lower(Booking.customer_email) == gt)
    return [b for b in db.execute(cau.order_by(Booking.id)).scalars() if chu_cua_booking(b) == chu]


def _du_dk(db: Session, chu: str, hom_nay: date) -> list[tuple[Booking, date, int]]:
    """[(booking, ngày đủ điều kiện, B)] — booking trực tiếp, không hủy, tour xong, đã thu đủ."""
    from app.services.hoa_hong_d06 import tinh_trang_booking
    ra = []
    for b in _bookings(db, chu):
        if b.cancelled:
            continue
        tt = tinh_trang_booking(db, b, db.get(Tour, b.tour_id) if b.tour_id else None, hom_nay)
        if tt["du"] and tt["net"] > 0:
            ra.append((b, tt["ngay"], tt["net"]))
    return ra


# ── hạng ────────────────────────────────────────────────────────────────────────────────────────

def hang_theo_chi_tieu(chi: int) -> tuple[str, Fraction, int]:
    ten, he, nguong = HANG[0][0], HANG[0][2], HANG[0][1]
    for t, n, h in HANG:
        if chi >= n:
            ten, he, nguong = t, h, n
    return ten, he, nguong


def _chi_tieu(ds: list[tuple[Booking, date, int]], ngay: date, tru_booking: int | None = None) -> int:
    return sum(net for b, d, net in ds if ngay - timedelta(days=HAN_DIEM_NGAY) < d <= ngay and b.id != tru_booking)


def _bac(ten: str) -> int:
    return [h[0] for h in HANG].index(ten)


def hang(db: Session, chu: str, hom_nay: date | None = None, ds=None) -> dict:
    hn = hom_nay or _hom_nay()
    ds = ds if ds is not None else _du_dk(db, chu, hn)
    chi = _chi_tieu(ds, hn)
    ten_tinh, _, _ = hang_theo_chi_tieu(chi)
    # Giữ hạng 30 ngày: hạng hiệu lực = hạng cao nhất đạt được trong 30 ngày qua.
    giu, ngay_dat = ten_tinh, hn
    for k in range(1, GIU_HANG_NGAY + 1):
        d = hn - timedelta(days=k)
        t, _, _ = hang_theo_chi_tieu(_chi_tieu(ds, d))
        if _bac(t) > _bac(giu):
            giu, ngay_dat = t, d
    he = next(h for t, n, h in HANG if t == giu)
    i = _bac(ten_tinh)
    sau = HANG[i + 1] if i + 1 < len(HANG) else None
    return {"hang": giu, "he_so": float(he), "chi_tieu_12_thang": chi, "hang_theo_chi_tieu": ten_tinh,
            "giu_den": (ngay_dat + timedelta(days=GIU_HANG_NGAY)).isoformat() if giu != ten_tinh else None,
            "hang_sau": sau[0] if sau else None, "con_thieu": (sau[1] - chi) if sau else 0,
            "bang_hang": [{"hang": t, "tu": n, "he_so": float(h)} for t, n, h in HANG]}


# ── sổ điểm ─────────────────────────────────────────────────────────────────────────────────────

def _ghi(db: Session, chu: str, loai: str, so: int, now: datetime, **kw) -> SoDiem:
    r = SoDiem(chu=chu, loai=loai, so_diem=int(so), luc=now, **kw)
    db.add(r); db.flush()
    return r


def _dong(db: Session, chu: str) -> list[SoDiem]:
    return db.execute(select(SoDiem).where(SoDiem.chu == chu).order_by(SoDiem.luc, SoDiem.id)).scalars().all()


def phan_bo(dong: list[SoDiem]) -> tuple[list[list], int]:
    """FIFO theo hạn: mỗi dòng trừ ăn vào lô cộng còn hạn sớm nhất có TRƯỚC nó. Trả (lô [dòng, còn lại], phần âm)."""
    lo, am = [], 0
    for r in dong:
        if r.so_diem > 0:
            lo.append([r, r.so_diem])
            continue
        can = -r.so_diem
        for l_ in sorted((x for x in lo if x[1] > 0), key=lambda x: (x[0].het_han or date.max, x[0].id)):
            lay = min(can, l_[1]); l_[1] -= lay; can -= lay
            if not can:
                break
        am += can
    return lo, am


def tinh(db: Session, chu: str, hom_nay: date | None = None, now: datetime | None = None) -> dict:
    """Đối chiếu sổ của một chủ điểm với dữ liệu booking. Chỉ ghi khi chương trình đã bật."""
    hn = hom_nay or _hom_nay()
    now = now or datetime.combine(hn, datetime.now().time())
    h = hieu_luc_tu(db)
    ghi = 0
    if h is None or hn < h:
        return {"dang_bat": False, "ghi": 0}
    ds = _du_dk(db, chu, hn)
    du = {b.id: (d, net) for b, d, net in ds}
    da = {}
    for r in db.execute(select(SoDiem).where(SoDiem.chu == chu, SoDiem.loai.in_(("CONG", "DAO")))).scalars():
        x = da.setdefault(r.booking_id, {"diem": 0, "he_so": ""})
        x["diem"] += r.so_diem
        if r.loai == "CONG" and r.he_so and not x["he_so"]:
            x["he_so"] = r.he_so
    for b in _bookings(db, chu):
        x = da.get(b.id, {"diem": 0, "he_so": ""})
        if b.id in du and du[b.id][0] >= h:
            ngay_du, net = du[b.id]
            if x["he_so"]:
                he = Fraction(x["he_so"])
                ten = next(t for t, n, hh in HANG if hh == he)
            else:
                ten, he, _ = hang_theo_chi_tieu(_chi_tieu(ds, ngay_du, tru_booking=b.id))
            dich = math.floor(Fraction(net, DONG_MOI_DIEM) * he)
        else:
            ngay_du, net, dich, he, ten = None, 0, 0, None, ""
        chenh = dich - x["diem"]
        if chenh > 0:
            _ghi(db, chu, "CONG", chenh, now, booking_id=b.id, het_han=hn + timedelta(days=HAN_DIEM_NGAY), co_so=net,
                 he_so=str(he), hang=ten, ghi_chu=f"{b.code} · {net:,} đ × {float(he):g}".replace(",", "."))
            ghi += 1
        elif chenh < 0:
            _ghi(db, chu, "DAO", chenh, now, booking_id=b.id, co_so=net,
                 ghi_chu=f"{b.code} · " + ("đã hủy" if b.cancelled else f"giá trị đủ điều kiện còn {net:,} đ".replace(",", ".")))
            ghi += 1
    # voucher hết hạn chưa dùng → trả điểm; voucher đã dùng mà booking bị hủy → hoàn điểm
    for v in db.execute(select(VoucherRewards).where(VoucherRewards.chu == chu, VoucherRewards.trang_thai.in_(("cho_dung", "da_dung")))).scalars():
        tra = None
        if v.trang_thai == "cho_dung" and v.han_dung < hn:
            tra, v.trang_thai = "Voucher hết hạn chưa dùng", "het_han"
        elif v.trang_thai == "da_dung" and v.booking_id and getattr(db.get(Booking, v.booking_id), "cancelled", True):
            tra, v.trang_thai = "Booking dùng voucher đã hủy", "da_hoan"
        if tra:
            han = max(v.han_diem_goc or hn, hn + timedelta(days=GIA_HAN_KHI_TRA))
            _ghi(db, chu, "TRA_GIU", v.so_diem, now, voucher_id=v.id, het_han=han, ghi_chu=f"{tra} · {v.ma}")
            ghi += 1
    # lô quá hạn còn dư → ghi hết hạn
    lo, _ = phan_bo(_dong(db, chu))
    for r, con in lo:
        if con > 0 and r.het_han and r.het_han < hn:
            _ghi(db, chu, "HET_HAN", -con, now, ghi_chu=f"Hết hạn lô cộng {r.luc:%d/%m/%Y}")
            ghi += 1
    db.commit()
    return {"dang_bat": True, "ghi": ghi}


def so_du(db: Session, chu: str, hom_nay: date | None = None) -> dict:
    hn = hom_nay or _hom_nay()
    dong = _dong(db, chu)
    tong = sum(r.so_diem for r in dong)
    lo, am = phan_bo(dong)
    sap = [(r.het_han, con) for r, con in lo if con > 0 and r.het_han and hn <= r.het_han <= hn + timedelta(days=30)]
    giu = db.execute(select(func.coalesce(func.sum(VoucherRewards.so_diem), 0)).where(
        VoucherRewards.chu == chu, VoucherRewards.trang_thai == "cho_dung")).scalar_one()
    return {"kha_dung": max(tong, 0), "am": min(tong, 0), "dang_giu": int(giu),
            "sap_het_han": sum(c for _, c in sap), "sap_het_han_ngay": min((d for d, _ in sap), default=None)}


# ── voucher ─────────────────────────────────────────────────────────────────────────────────────

_CHU_MA = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _ma_voucher(db: Session) -> str:
    while True:
        m = "VTD-" + "".join(secrets.choice(_CHU_MA) for _ in range(6))
        if not db.execute(select(VoucherRewards.id).where(VoucherRewards.ma == m)).first():
            return m


def doi_voucher(db: Session, chu: str, so_diem: int, hom_nay: date | None = None, now: datetime | None = None) -> VoucherRewards:
    hn = hom_nay or _hom_nay()
    now = now or datetime.combine(hn, datetime.now().time())
    h = hieu_luc_tu(db)
    if h is None or hn < h:
        raise LoiDiem("VTD Rewards chưa bắt đầu — chưa đổi được điểm")
    so_diem = int(so_diem or 0)
    if so_diem < DIEM_DOI_TOI_THIEU:
        raise LoiDiem(f"Đổi tối thiểu {DIEM_DOI_TOI_THIEU} điểm")
    tinh(db, chu, hn, now)
    sd = so_du(db, chu, hn)
    if so_diem > sd["kha_dung"]:
        raise LoiDiem(f"Bạn chỉ có {sd['kha_dung']:,} điểm khả dụng".replace(",", "."))
    lo, _ = phan_bo(_dong(db, chu))
    han_goc = min((r.het_han for r, con in lo if con > 0 and r.het_han), default=None)
    v = VoucherRewards(ma=_ma_voucher(db), chu=chu, so_diem=so_diem, gia_tri=so_diem * GIA_TRI_DIEM,
                       han_dung=hn + timedelta(days=HAN_VOUCHER_NGAY), han_diem_goc=han_goc, tao_luc=now)
    db.add(v); db.flush()
    _ghi(db, chu, "GIU", -so_diem, now, voucher_id=v.id, ghi_chu=f"Đổi voucher {v.ma}")
    db.commit(); db.refresh(v)
    return v


def ap_voucher(db: Session, u: User, ma_voucher: str, ma_booking: str, hom_nay: date | None = None, now: datetime | None = None) -> dict:
    from app.services.vai_ke_thua import vai_va_cha
    from app.services import rules as R
    if not set(vai_va_cha(u.role)) & set(VAI_AP):
        raise LoiDiem("Chỉ Kinh doanh / Sale Admin áp voucher")
    hn = hom_nay or _hom_nay()
    now = now or datetime.now()
    v = db.execute(select(VoucherRewards).where(VoucherRewards.ma == (ma_voucher or "").strip().upper())).scalars().first()
    if v is None:
        raise LoiDiem("Không có voucher này")
    if v.trang_thai != "cho_dung":
        raise LoiDiem(f"Voucher {TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai).lower()}")
    if v.han_dung < hn:
        raise LoiDiem("Voucher đã quá hạn dùng")
    b = db.execute(select(Booking).where(Booking.code == (ma_booking or "").strip())).scalars().first()
    if b is None:
        raise LoiDiem("Không có booking này")
    if b.cancelled or b.locked:
        raise LoiDiem("Booking đã hủy hoặc đã khoá — không áp được")
    if b.doi_tac_id:
        raise LoiDiem("Booking qua đại lý / CTV không dùng voucher cá nhân")
    if chu_cua_booking(b) != v.chu:
        raise LoiDiem("Booking không cùng SĐT / email với chủ voucher")
    net = int(round(float(b.amount or 0) - float(b.discount or 0)))
    tran = math.floor(net * TRAN_VOUCHER)
    if v.gia_tri > tran:
        raise LoiDiem(f"Voucher {v.gia_tri:,} đ vượt trần 5% booking ({tran:,} đ)".replace(",", "."))
    truoc = float(b.discount or 0)
    b.discount = truoc + v.gia_tri
    v.trang_thai, v.booking_id, v.ap_boi, v.ap_luc = "da_dung", b.id, u.username, now
    R.audit(db, u.username, u.role, "ap_voucher_rewards", f"booking:{b.code}",
            before={"discount": truoc}, after={"discount": b.discount, "voucher": v.ma, "gia_tri": v.gia_tri})
    db.commit()
    return {"message": f"Đã áp {v.ma} ({v.gia_tri:,} đ) vào {b.code}".replace(",", "."), "giam_gia_moi": int(b.discount)}


def xem_voucher(db: Session, ma: str) -> dict:
    v = db.execute(select(VoucherRewards).where(VoucherRewards.ma == (ma or "").strip().upper())).scalars().first()
    if v is None:
        raise LoiDiem("Không có voucher này")
    from app.services.cong_ngoai import che
    return {"ma": v.ma, "chu": che(v.chu.split(":", 1)[1]), "gia_tri": v.gia_tri, "han_dung": v.han_dung.isoformat(),
            "trang_thai": TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai)}


# ── xem ─────────────────────────────────────────────────────────────────────────────────────────

def _lich_su(db: Session, chu: str) -> list[dict]:
    return [{"luc": r.luc.isoformat(timespec="minutes"), "loai": LOAI_DONG.get(r.loai, r.loai), "so_diem": r.so_diem,
             "het_han": r.het_han.isoformat() if r.het_han and r.so_diem > 0 else None, "noi_dung": r.ghi_chu}
            for r in reversed(_dong(db, chu))][:100]


def _voucher(db: Session, chu: str) -> list[dict]:
    ra = []
    for v in db.execute(select(VoucherRewards).where(VoucherRewards.chu == chu).order_by(VoucherRewards.tao_luc.desc())).scalars():
        b = db.get(Booking, v.booking_id) if v.booking_id else None
        ra.append({"ma": v.ma, "gia_tri": v.gia_tri, "so_diem": v.so_diem, "han_dung": v.han_dung.isoformat(),
                   "trang_thai": v.trang_thai, "trang_thai_ten": TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai),
                   "booking": b.code if b else None})
    return ra


def tong_quan(db: Session, chu_ds: list[str], hom_nay: date | None = None) -> dict:
    hn = hom_nay or _hom_nay()
    h = hieu_luc_tu(db)
    dang_bat = h is not None and hn >= h
    ra = {"dang_bat": dang_bat, "hieu_luc_tu": h.isoformat() if h else None, "kha_dung": 0, "dang_giu": 0, "am": 0,
          "sap_het_han": 0, "sap_het_han_ngay": None, "lich_su": [], "voucher": [], "chu": chu_ds[0] if chu_ds else None,
          "quy_doi": GIA_TRI_DIEM, "doi_toi_thieu": DIEM_DOI_TOI_THIEU}
    best = None
    for chu in chu_ds:
        if dang_bat:
            tinh(db, chu, hn)
        sd = so_du(db, chu, hn)
        for k in ("kha_dung", "dang_giu", "am", "sap_het_han"):
            ra[k] += sd[k]
        if sd["sap_het_han_ngay"] and (not ra["sap_het_han_ngay"] or sd["sap_het_han_ngay"].isoformat() < ra["sap_het_han_ngay"]):
            ra["sap_het_han_ngay"] = sd["sap_het_han_ngay"].isoformat()
        ra["lich_su"] += _lich_su(db, chu)
        ra["voucher"] += _voucher(db, chu)
        hg = hang(db, chu, hn)
        if best is None or hg["chi_tieu_12_thang"] > best["chi_tieu_12_thang"]:
            best = hg
    ra["hang"] = best or hang_rong()
    return ra


def hang_rong() -> dict:
    return {"hang": "Member", "he_so": 1.0, "chi_tieu_12_thang": 0, "hang_theo_chi_tieu": "Member", "giu_den": None,
            "hang_sau": "Plus", "con_thieu": HANG[1][1], "bang_hang": [{"hang": t, "tu": n, "he_so": float(h)} for t, n, h in HANG]}


def tra_cuu(db: Session, q: str) -> dict:
    chu = chu_tu_lien_he(q)
    if chu is None:
        raise LoiDiem("Ghi SĐT 10 số hoặc email")
    from app.services.cong_ngoai import che
    t = tong_quan(db, [chu])
    return {"lien_he": che(chu.split(":", 1)[1]), "hang": t["hang"]["hang"], "chi_tieu_12_thang": t["hang"]["chi_tieu_12_thang"],
            "kha_dung": t["kha_dung"], "dang_giu": t["dang_giu"], "dang_bat": t["dang_bat"],
            "voucher": [v for v in t["voucher"] if v["trang_thai"] == "cho_dung"]}


# ── yêu thích ───────────────────────────────────────────────────────────────────────────────────

def luu_yeu_thich(db: Session, tk, tour_id: int, luu: bool) -> None:
    r = db.execute(select(YeuThich).where(YeuThich.tai_khoan_id == tk.id, YeuThich.tour_id == tour_id)).scalars().first()
    if not luu:
        if r:
            db.delete(r); db.commit()
        return
    if r:
        return
    from app.services import cong_khach as K
    try:
        o = K.tour(db, tour_id)
    except K.LoiKhach as ex:
        raise LoiDiem(str(ex))
    if db.execute(select(func.count(YeuThich.id)).where(YeuThich.tai_khoan_id == tk.id)).scalar_one() >= 100:
        raise LoiDiem("Đã lưu tối đa 100 tour")
    db.add(YeuThich(tai_khoan_id=tk.id, tour_id=tour_id, gia_luc_luu=o["gia"])); db.commit()


def ds_yeu_thich(db: Session, tk) -> list[dict]:
    from app.services import cong_khach as K
    ra = []
    for r in db.execute(select(YeuThich).where(YeuThich.tai_khoan_id == tk.id).order_by(YeuThich.luc.desc())).scalars():
        t = db.get(Tour, r.tour_id)
        try:
            o = K.tour(db, r.tour_id); gia, con = o["gia"], True
        except K.LoiKhach:
            o, gia, con = None, None, False
        giam = (r.gia_luc_luu - gia) if con and gia is not None and gia < r.gia_luc_luu else 0
        ra.append({"tour_id": r.tour_id, "ten": t.name if t else "", "khoi_hanh": t.start_date.isoformat() if t else None,
                   "gia_luc_luu": r.gia_luc_luu, "gia_hien_tai": gia, "con_ban": con, "giam": giam, "tour": o})
    return ra


def id_yeu_thich(db: Session, tk) -> list[int]:
    return [x for x in db.execute(select(YeuThich.tour_id).where(YeuThich.tai_khoan_id == tk.id)).scalars()]

