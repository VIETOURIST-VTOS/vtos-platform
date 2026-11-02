"""KH-3 · VTD Rewards — Chủ tịch chốt ĐÚNG số dự thảo đặc tả v3.0 và duyệt bản xem thử 26/10/2026.

  Hạng (chi tiêu xét hạng 12 tháng cuốn chiếu): Member < 30 tr ×1,00 · Plus 30–<100 tr ×1,25 · Premium ≥ 100 tr ×1,50.
  Cộng điểm: P = floor(B / 10.000 × hệ số hạng LÚC CHUYẾN ĐỦ ĐIỀU KIỆN, không tính chính chuyến ấy).
  1 điểm = 100 đ ưu đãi; một booking dùng voucher tối đa 5% giá trị; điểm hết hạn 12 tháng từ lần cộng.
  Giữ hạng 30 ngày khi chi tiêu tụt dưới ngưỡng.

  B = giá trị booking sau giảm giá (gồm cả voucher đã áp). Đủ điều kiện = booking TRỰC TIẾP (không qua đại lý /
  CTV), không hủy, tour đã kết thúc VÀ đã thu đủ — cùng phép đo với D06 (`hoa_hong_d06.tinh_trang_booking`).
  Chỉ cộng cho chuyến đủ điều kiện TỪ ngày hiệu lực Chủ tịch ký (`rewards_hieu_luc_tu`), không hồi tố.
  Hạng thì xét trên mọi chuyến 12 tháng — khách thấy đúng chi tiêu thật của mình.

  AT-1c (Chủ tịch 28/10/2026): đơn ĐẶT BÀN nhà hàng tích điểm như tour — đơn khách / cổ đông tự đặt trên cổng (không
  qua đại lý / CTV), nhà hàng báo đã dùng VÀ Kế toán đã chốt; B = tiền đã trả qua Vietourist (cọc hoặc trả đủ) trừ
  phần đã hoàn. Chi tiêu đặt bàn cũng vào chi tiêu 12 tháng xét hạng.

  KS-16 (Chủ tịch duyệt 30/10/2026): đơn KHÁCH SẠN VTD tích điểm như tour — khách / cổ đông tự đặt trên cổng,
  đã ở (đơn đã xác nhận, qua ngày trả phòng) VÀ Kế toán đã chốt; B = tiền khách thực trả − đã hoàn. Không có giá thành
  viên. Khách tự nhập voucher lúc đặt (tối đa 5% đơn, VTD chịu); đơn hủy có hoàn tiền / hết giờ giữ chưa trả → trả điểm.
  Một đơn cổng thuộc MỘT chủ điểm: chủ chính của tài khoản (SĐT, không có thì email) — tài khoản có cả SĐT lẫn email
  không được cộng hai lần.

  Sổ chỉ ghi thêm và TỰ ĐỐI CHIẾU: mỗi lần tính, điểm đích của từng booking so với điểm đã ghi → ghi phần chênh.
  Hủy / hoàn / giảm giá sau khi đã cộng → dòng DAO. Chạy lại không ghi gì nếu không có gì đổi.

  KS-16g (Chủ tịch duyệt đề xuất v3, 31/10/2026) — bật bằng tham số `rewards_v3_tu`; khoản đủ điều kiện TRƯỚC ngày ấy
  giữ cách tính cũ (không hồi tố):
    1. Plus từ 40 tr chi tiêu tour 12 tháng; điểm cộng mới hết hạn sau 18 tháng.
    2. Hạng có KỲ 12 tháng từ ngày lên hạng: chi tiêu 12 tháng chạm 40 / 100 tr là lên ngay; hết kỳ xét gia hạn —
       Plus cần 20 tr trong kỳ (không thì về Member), Premium cần 70 tr (không thì xuống Plus thêm 12 tháng).
       Hệ số của một khoản = hạng ĐANG HIỆU LỰC TRƯỚC ngày khoản ấy đủ điều kiện. Thay cho «giữ hạng 30 ngày».
    3. Đơn khách sạn / đặt bàn (VTD thu hộ): điểm = 20% hoa hồng VTD thực nhận ÷ 100 đ × hệ số; không vào chi tiêu xét hạng.
    4. Quà mới: chào mừng 50.000 đ (tour đầu tiên ≥ 5 tr, 30 ngày) · sinh nhật 100.000 đ (một lần mỗi năm, 30 ngày) ·
       trưởng đoàn > 15 khách: điểm trên phần của mình + 2.000 điểm · giới thiệu khách 1.000 điểm (tham số
       `rewards_gioi_thieu_bat`, mặc định đóng chờ pháp chế).
    5. Trần ưu đãi MỚI của một booking tour: C ≤ min(40%·G, G − 5%·B), G = lãi gộp dự toán phân bổ cho booking. Tour
       chưa có dự toán → không phát ưu đãi mới. Không bao giờ cắt hoa hồng D06 hay ưu đãi đã xác nhận.
"""
import math
import secrets
from datetime import date, datetime, timedelta
from fractions import Fraction
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Booking, Tour, User
from app.models.rewards import SoDiem, VoucherRewards, YeuThich, GioiThieuRewards, LOAI_DONG, TRANG_THAI_VOUCHER, LOAI_VOUCHER
from app.services.zalo import norm_phone

KHOA_HIEU_LUC = "rewards_hieu_luc_tu"
KHOA_V3 = "rewards_v3_tu"
KHOA_GIOI_THIEU = "rewards_gioi_thieu_bat"
HANG = (("Member", 0, Fraction(1)), ("Plus", 40_000_000, Fraction(5, 4)), ("Premium", 100_000_000, Fraction(3, 2)))
HANG_CU = (("Member", 0, Fraction(1)), ("Plus", 30_000_000, Fraction(5, 4)), ("Premium", 100_000_000, Fraction(3, 2)))
GIA_HAN_HANG = {"Plus": 20_000_000, "Premium": 70_000_000}
KY_HANG_THANG = 12
HAN_DIEM_THANG = 18
CUA_SO_NGAY = 365                      # chi tiêu xét hạng: 12 tháng cuốn chiếu
DONG_MOI_DIEM = 10_000
GIA_TRI_DIEM = 100
TY_LE_TICH_TOUR = Fraction(1, 100)     # tour: 1% B thành giá trị điểm (= B / 10.000 điểm)
TY_LE_HOA_HONG = Fraction(20, 100)     # v3: KS / nhà hàng 20% hoa hồng VTD
TRAN_VOUCHER = Fraction(5, 100)
HAN_DIEM_NGAY = 365                    # luật cũ
GIU_HANG_NGAY = 30                     # luật cũ
DOAN_TREN = 15                         # đoàn > 15 khách: trưởng đoàn
THUONG_TRUONG_DOAN = 2_000
THUONG_GIOI_THIEU = 1_000
DON_TOI_THIEU_MOI = 5_000_000          # chào mừng / giới thiệu: tour ≥ 5 tr
VOUCHER_CHAO_MUNG = 50_000
VOUCHER_SINH_NHAT = 100_000
TRAN_G = Fraction(40, 100)
SAN_B = Fraction(5, 100)
HAN_VOUCHER_NGAY = 30
DIEM_DOI_TOI_THIEU = 100
GIA_HAN_KHI_TRA = 30
DAU_V3 = " · v3"                       # đuôi ghi chú dòng cộng tính theo luật v3 — khoản cộng trước đó giữ luật cũ

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


def v3_tu(db: Session) -> date | None:
    from app.services import moi_truong_du_lieu as MT
    from app.services import rules as R
    try:
        return MT.doc_ngay(str(R.get_param_chu(db, KHOA_V3)).strip())
    except (KeyError, ValueError):
        return None


def gioi_thieu_mo(db: Session) -> bool:
    from app.services import rules as R
    try:
        return float(R.get_param(db, KHOA_GIOI_THIEU)) >= 1
    except (KeyError, ValueError):
        return False


def _v3(moc: date | None, ngay: date | None) -> bool:
    return moc is not None and ngay is not None and ngay >= moc


def cong_thang(d: date, n: int) -> date:
    t = d.month - 1 + n
    y, m = d.year + t // 12, t % 12 + 1
    import calendar
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


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


def chu_chinh(tk) -> str | None:
    """Chủ điểm DUY NHẤT của một tài khoản cổng — đơn cổng chỉ cộng cho chủ này."""
    ds = chu_cua_tai_khoan(tk)
    return ds[0] if ds else None


def _bookings(db: Session, chu: str) -> list[Booking]:
    """Booking TRỰC TIẾP của chủ điểm (kể cả đã hủy — cần để trừ điểm)."""
    kieu, gt = chu.split(":", 1)
    cau = select(Booking).where(Booking.doi_tac_id.is_(None))
    if kieu == "sdt":
        cau = cau.where(Booking.customer_phone.like("%" + "%".join(gt[-9:])))
    else:
        cau = cau.where(func.lower(Booking.customer_email) == gt)
    return [b for b in db.execute(cau.order_by(Booking.id)).scalars() if chu_cua_booking(b) == chu]


def _bookings_ctv(db: Session, chu: str) -> list[Booking]:
    """KS-16i (Chủ tịch 01/11/2026, theo v3): booking nguồn CTV của chủ điểm — cũng tích điểm (từ ngày áp v3,
    trong trần chi phí ưu đãi của booking). Booking qua ĐẠI LÝ vẫn không tích."""
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    kieu, gt = chu.split(":", 1)
    cau = select(Booking).join(DoiTacBanHang, DoiTacBanHang.id == Booking.doi_tac_id).where(DoiTacBanHang.loai == "ctv_ban_hang")
    if kieu == "sdt":
        cau = cau.where(Booking.customer_phone.like("%" + "%".join(gt[-9:])))
    else:
        cau = cau.where(func.lower(Booking.customer_email) == gt)
    return [b for b in db.execute(cau.order_by(Booking.id)).scalars() if chu_cua_booking(b) == chu]


class _Muc:
    """Một khoản tích điểm: booking tour hoặc đơn đặt bàn. `khoa` phân biệt hai loại trong sổ."""
    def __init__(self, khoa: tuple, ma: str, huy: bool):
        self.khoa, self.code, self.cancelled = khoa, ma, huy

    @property
    def id(self):
        return self.khoa


def _don_dat_ban(db: Session, chu: str) -> list:
    """Đơn đặt bàn TRỰC TIẾP của chủ điểm: người đặt là khách / cổ đông trên cổng, không qua đối tác."""
    from app.models.dat_ban import DonDatBan
    from app.models.cong_ngoai import TaiKhoanNgoai
    kieu, gt = chu.split(":", 1)
    cau = select(DonDatBan).join(TaiKhoanNgoai, TaiKhoanNgoai.id == DonDatBan.tai_khoan_id).where(
        DonDatBan.doi_tac_id.is_(None), TaiKhoanNgoai.loai.in_(("khach_hang", "co_dong")))
    cau = cau.where(TaiKhoanNgoai.dien_thoai == gt) if kieu == "sdt" else cau.where(func.lower(TaiKhoanNgoai.email) == gt)
    return [d for d in db.execute(cau.order_by(DonDatBan.id)).scalars().all()
            if chu_chinh(db.get(TaiKhoanNgoai, d.tai_khoan_id)) == chu]


def _don_ks(db: Session, chu: str) -> list:
    """KS-16: đơn khách sạn VTD do khách / cổ đông tự đặt trên cổng, thuộc chủ chính của tài khoản."""
    from app.models.don_ks_vtd import DonKsVtd
    from app.models.cong_ngoai import TaiKhoanNgoai
    kieu, gt = chu.split(":", 1)
    cau = select(DonKsVtd).join(TaiKhoanNgoai, TaiKhoanNgoai.id == DonKsVtd.tai_khoan_ngoai_id).where(
        DonKsVtd.cong.in_(("khach_hang", "co_dong")))
    cau = cau.where(TaiKhoanNgoai.dien_thoai == gt) if kieu == "sdt" else cau.where(func.lower(TaiKhoanNgoai.email) == gt)
    return [d for d in db.execute(cau.order_by(DonKsVtd.id)).scalars().all()
            if chu_chinh(db.get(TaiKhoanNgoai, d.tai_khoan_ngoai_id)) == chu]


def _b_ks(db: Session, d) -> int:
    from app.services.don_ks_vtd import da_tra
    return max(0, da_tra(db, d) - int(round(float(d.da_hoan_tien or 0))))


def _b_dat_ban(db: Session, d) -> int:
    from app.services.dat_ban import da_tra
    return max(0, da_tra(db, d) - int(round(float(d.da_hoan_tien or 0))))


def _muc(db: Session, chu: str) -> list:
    ra = [_Muc(("b", b.id), b.code, bool(b.cancelled)) for b in _bookings(db, chu) + _bookings_ctv(db, chu)]
    ra += [_Muc(("d", d.id), d.ma, d.trang_thai in ("huy", "khong_den", "tu_choi", "het_han")) for d in _don_dat_ban(db, chu)]
    ra += [_Muc(("k", d.id), d.ma, d.trang_thai in ("da_huy", "het_han")) for d in _don_ks(db, chu)]
    return ra


class _Du:
    """Một khoản đủ điều kiện. `net` = B hiển thị · `uu_dai` = giá trị (đồng) thành điểm trước hệ số ·
    `chi` = phần vào chi tiêu xét hạng · `doan` = trưởng đoàn (v3, > 15 khách)."""
    __slots__ = ("muc", "ngay", "net", "uu_dai", "chi", "doan", "v3", "uu_dai_cu", "ctv")

    def __init__(self, muc, ngay, net, uu_dai, chi, doan=False, v3=False):
        self.muc, self.ngay, self.net, self.uu_dai, self.chi, self.doan, self.v3 = muc, ngay, net, uu_dai, chi, doan, v3
        self.uu_dai_cu = net * TY_LE_TICH_TOUR      # cách tính cũ — giữ cho khoản đã cộng trước ngày áp v3
        self.ctv = False                            # KS-16i: booking nguồn CTV — điểm trong trần chi phí


def _du_dk(db: Session, chu: str, hom_nay: date) -> list[_Du]:
    """Khoản đủ điều kiện — booking tour trực tiếp (không hủy, tour xong, đã thu đủ), đơn đặt bàn trực tiếp (đã dùng,
    Kế toán đã chốt, ngày = muộn hơn giữa ngày ăn và ngày chốt), đơn khách sạn (đã ở, Kế toán đã chốt)."""
    from app.services.hoa_hong_d06 import tinh_trang_booking
    moc = v3_tu(db)
    ra = []
    for b in _bookings(db, chu) + _bookings_ctv(db, chu):
        if b.cancelled:
            continue
        tt = tinh_trang_booking(db, b, db.get(Tour, b.tour_id) if b.tour_id else None, hom_nay)
        if tt["du"] and tt["net"] > 0:
            net, v3 = tt["net"], _v3(moc, tt["ngay"])
            if b.doi_tac_id and not v3:         # đơn CTV chỉ tích từ ngày áp v3
                continue
            n0 = len(ra)
            pax = int(b.pax or 1)
            if v3 and pax > DOAN_TREN:          # trưởng đoàn: chỉ phần của mình
                phan = Fraction(net, pax)
                ra.append(_Du(_Muc(("b", b.id), b.code, False), tt["ngay"], net, phan * TY_LE_TICH_TOUR, phan, True, True))
            else:
                ra.append(_Du(_Muc(("b", b.id), b.code, False), tt["ngay"], net, net * TY_LE_TICH_TOUR, Fraction(net), False, v3))
            if b.doi_tac_id:
                for x in ra[n0:]:
                    x.ctv = True
    for d in _don_dat_ban(db, chu):
        if d.trang_thai != "da_dung" or d.chot_luc is None:
            continue
        ngay = max(d.ngay, d.chot_luc.date())
        net = _b_dat_ban(db, d)
        if ngay <= hom_nay and net > 0:
            ra.append(_thu_ho(("d", d.id), d.ma, ngay, net, d.hoa_hong, moc))
    for d in _don_ks(db, chu):
        if d.trang_thai != "da_xac_nhan" or d.chot_luc is None:
            continue
        ngay = max(d.ra, d.chot_luc.date())
        net = _b_ks(db, d)
        if ngay <= hom_nay and net > 0:
            ra.append(_thu_ho(("k", d.id), d.ma, ngay, net, d.hoa_hong, moc))
    return ra


def _thu_ho(khoa, ma, ngay, net, hoa_hong, moc) -> _Du:
    """KS / nhà hàng: luật cũ tích như tour; v3 = 20% hoa hồng VTD (Kế toán chốt, sau hoàn), không vào chi tiêu hạng."""
    if _v3(moc, ngay):
        hh = max(0, int(round(float(hoa_hong or 0))))
        return _Du(_Muc(khoa, ma, False), ngay, net, hh * TY_LE_HOA_HONG, Fraction(0), False, True)
    return _Du(_Muc(khoa, ma, False), ngay, net, net * TY_LE_TICH_TOUR, Fraction(net))


# ── hạng ────────────────────────────────────────────────────────────────────────────────────────

def hang_theo_chi_tieu(chi, bang=HANG) -> tuple[str, Fraction, int]:
    ten, he, nguong = bang[0][0], bang[0][2], bang[0][1]
    for t, n, h in bang:
        if chi >= n:
            ten, he, nguong = t, h, n
    return ten, he, nguong


def he_so_hang(ten: str) -> Fraction:
    return next(h for t, n, h in HANG if t == ten)


def _chi_tieu(ds: list, ngay: date, tru_booking=None) -> int:
    """Luật cũ: chi tiêu 12 tháng cuốn chiếu (mọi khoản, theo B)."""
    return sum(x.net for x in ds if ngay - timedelta(days=HAN_DIEM_NGAY) < x.ngay <= ngay and x.muc.id != tru_booking)


def _bac(ten: str) -> int:
    return [h[0] for h in HANG].index(ten)


def _hang_cu(ds: list, hn: date) -> dict:
    chi = _chi_tieu(ds, hn)
    ten_tinh, _, _ = hang_theo_chi_tieu(chi, HANG_CU)
    # Giữ hạng 30 ngày: hạng hiệu lực = hạng cao nhất đạt được trong 30 ngày qua.
    giu, ngay_dat = ten_tinh, hn
    for k in range(1, GIU_HANG_NGAY + 1):
        d = hn - timedelta(days=k)
        t, _, _ = hang_theo_chi_tieu(_chi_tieu(ds, d), HANG_CU)
        if _bac(t) > _bac(giu):
            giu, ngay_dat = t, d
    i = _bac(ten_tinh)
    sau = HANG_CU[i + 1] if i + 1 < len(HANG_CU) else None
    return {"hang": giu, "he_so": float(he_so_hang(giu)), "chi_tieu_12_thang": chi, "hang_theo_chi_tieu": ten_tinh,
            "giu_den": (ngay_dat + timedelta(days=GIU_HANG_NGAY)).isoformat() if giu != ten_tinh else None,
            "hang_sau": sau[0] if sau else None, "con_thieu": (sau[1] - chi) if sau else 0,
            "bang_hang": [{"hang": t, "tu": n, "he_so": float(h)} for t, n, h in HANG_CU], "luat": "cu",
            "han_hang": None, "gia_han_can": None, "chi_trong_ky": None, "gia_han_con_thieu": None, "het_ky_ve": None}


def _su_kien(ds: list) -> list[tuple[date, Fraction]]:
    return sorted(((x.ngay, x.chi) for x in ds if x.chi > 0), key=lambda e: e[0])


def _tong(ev, tu: date, den: date) -> int:
    """Chi tiêu các khoản có ngày trong [tu, den]."""
    return int(sum(c for d, c in ev if tu <= d <= den))


def dong_hang(ev: list, den: date, moc: date | None, truoc: bool = False) -> tuple:
    """v3: chạy dòng thời gian hạng tới ngày `den` → (hạng, ngày bắt đầu kỳ, ngày hết kỳ, ngày bắt đầu tính gia hạn). `truoc` = không tính khoản
    của chính ngày `den` (hạng trước giao dịch). Khoản trước `moc` lên hạng theo ngưỡng cũ (30 tr)."""
    ten, tu, het, i = "Member", None, None, 0
    dem = None          # chi tiêu gia hạn tính từ ngày này: kỳ lên hạng không tính chính khoản làm lên hạng
    while True:
        nd = ev[i][0] if i < len(ev) else None
        if het is not None and het <= den and (nd is None or het <= nd):
            trong_ky = _tong(ev, dem, het - timedelta(days=1))
            if trong_ky >= GIA_HAN_HANG[ten]:
                tu, dem, het = het, het, cong_thang(het, KY_HANG_THANG)
            elif ten == "Premium":
                ten, tu, dem, het = "Plus", het, het, cong_thang(het, KY_HANG_THANG)
            else:
                ten, tu, dem, het = "Member", None, None, None
            continue
        if nd is None or nd > den or (truoc and nd == den):
            break
        while i < len(ev) and ev[i][0] == nd:
            i += 1
        chi = _tong(ev, nd - timedelta(days=CUA_SO_NGAY - 1), nd)
        t = hang_theo_chi_tieu(chi, HANG if _v3(moc, nd) else HANG_CU)[0]
        if _bac(t) > _bac(ten):
            ten, tu, dem, het = t, nd, nd + timedelta(days=1), cong_thang(nd, KY_HANG_THANG)
    return ten, tu, het, dem


def hang(db: Session, chu: str, hom_nay: date | None = None, ds=None) -> dict:
    hn = hom_nay or _hom_nay()
    ds = ds if ds is not None else _du_dk(db, chu, hn)
    moc = v3_tu(db)
    if not _v3(moc, hn):
        return _hang_cu(ds, hn)
    ev = _su_kien(ds)
    ten, tu, het, dem = dong_hang(ev, hn, moc)
    chi = _tong(ev, hn - timedelta(days=CUA_SO_NGAY - 1), hn)
    i = _bac(ten)
    sau = HANG[i + 1] if i + 1 < len(HANG) else None
    can = GIA_HAN_HANG.get(ten)
    trong_ky = _tong(ev, dem, hn) if dem else None
    return {"hang": ten, "he_so": float(he_so_hang(ten)), "chi_tieu_12_thang": chi, "hang_theo_chi_tieu": hang_theo_chi_tieu(chi)[0],
            "giu_den": None, "hang_sau": sau[0] if sau else None, "con_thieu": max(0, sau[1] - chi) if sau else 0,
            "bang_hang": [{"hang": t, "tu": n, "he_so": float(h), "gia_han": GIA_HAN_HANG.get(t)} for t, n, h in HANG],
            "luat": "v3", "han_hang": het.isoformat() if het else None, "gia_han_can": can, "chi_trong_ky": trong_ky,
            "gia_han_con_thieu": max(0, can - trong_ky) if can else None,
            "het_ky_ve": ("Plus" if ten == "Premium" else "Member") if can else None}


def he_so_luc(db: Session, ds: list, ngay: date, tru=None) -> tuple[str, Fraction]:
    """Hạng + hệ số áp cho một khoản đủ điều kiện ngày `ngay`."""
    moc = v3_tu(db)
    if _v3(moc, ngay):
        ten = dong_hang(_su_kien(ds), ngay, moc, truoc=True)[0]
        return ten, he_so_hang(ten)
    ten, he, _ = hang_theo_chi_tieu(_chi_tieu(ds, ngay, tru_booking=tru), HANG_CU)
    return ten, he


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
    so_ghi = 0
    if h is None or hn < h:
        return {"dang_bat": False, "ghi": 0}
    ds = _du_dk(db, chu, hn)
    du = {x.muc.id: x for x in ds}
    moc = v3_tu(db)
    han_moi = cong_thang(hn, HAN_DIEM_THANG) if _v3(moc, hn) else hn + timedelta(days=HAN_DIEM_NGAY)
    da = {}
    for r in db.execute(select(SoDiem).where(SoDiem.chu == chu, SoDiem.loai.in_(("CONG", "DAO")))).scalars():
        k = ("d", r.dat_ban_id) if r.dat_ban_id else (("k", r.don_ks_id) if r.don_ks_id else ("b", r.booking_id))
        x = da.setdefault(k, {"diem": 0, "he_so": "", "dau": None})
        x["diem"] += r.so_diem
        if r.loai == "CONG" and r.he_so and not x["he_so"]:
            x["he_so"] = r.he_so
        if r.loai == "CONG":
            x["dau"] = True
            x["v3"] = x.get("v3") or r.ghi_chu.endswith(DAU_V3)
    for b in _muc(db, chu):
        x = da.get(b.id, {"diem": 0, "he_so": "", "dau": None})
        noi = {{"b": "booking_id", "d": "dat_ban_id", "k": "don_ks_id"}[b.id[0]]: b.id[1]}
        k = du.get(b.id)
        if k is not None and k.ngay >= h:
            net = k.net
            if x["he_so"]:
                he = Fraction(x["he_so"])
                ten = next(t for t, n, hh in HANG if hh == he)
            else:
                ten, he = he_so_luc(db, ds, k.ngay, tru=b.id)
            # Không hồi tố: khoản đã cộng theo luật cũ giữ luật cũ (kể cả khi ngày áp v3 ký lùi về trước).
            if k.v3 and x["dau"] and not x.get("v3"):
                k.v3, k.doan, k.uu_dai = False, False, k.uu_dai_cu
            dich = math.floor(k.uu_dai / GIA_TRI_DIEM * he)
            if k.ctv:
                # KS-16i: đơn CTV — không vượt trần chi phí ưu đãi của booking (đã tính hoa hồng nguồn); đã cộng thì
                # không tăng thêm, chỉ giảm khi giá trị đủ điều kiện giảm. Tour chưa có dự toán → không cộng.
                if x["diem"] > 0:
                    dich = min(dich, x["diem"])
                else:
                    p = phong_uu_dai_tour(db, db.get(Booking, b.id[1]), chu=chu, bo_diem=True)
                    dich = min(dich, max(0, p["con"]) // GIA_TRI_DIEM) if p else 0
        else:
            k, net, dich, he, ten = None, 0, 0, None, ""
        chenh = dich - x["diem"]
        if chenh > 0:
            if k.v3 and b.id[0] != "b":
                ghi = f"{b.code} · 20% hoa hồng {int(k.uu_dai / TY_LE_HOA_HONG):,} đ × {float(he):g}"
            elif k.doan:
                ghi = f"{b.code} · trưởng đoàn, phần của mình {int(k.chi):,} đ × {float(he):g}"
            else:
                ghi = f"{b.code} · {net:,} đ × {float(he):g}"
            if k.ctv:
                ghi += " · đơn CTV (trong trần chi phí)"
            _ghi(db, chu, "CONG", chenh, now, **noi, het_han=han_moi, co_so=net,
                 he_so=str(he), hang=ten, ghi_chu=ghi.replace(",", ".") + (DAU_V3 if k.v3 else ""))
            so_ghi += 1
        elif chenh < 0:
            _ghi(db, chu, "DAO", chenh, now, **noi, co_so=net,
                 ghi_chu=f"{b.code} · " + ("đã hủy" if b.cancelled else f"giá trị đủ điều kiện còn {net:,} đ".replace(",", ".")))
            so_ghi += 1
    so_ghi += _thuong(db, chu, ds, h, hn, now, han_moi)
    # voucher hết hạn chưa dùng → trả điểm; voucher đã dùng mà booking bị hủy → hoàn điểm (voucher quà: mở lại)
    for v in db.execute(select(VoucherRewards).where(VoucherRewards.chu == chu, VoucherRewards.trang_thai.in_(("cho_dung", "da_dung")))).scalars():
        tra = None
        if v.trang_thai == "cho_dung" and v.han_dung < hn:
            if v.so_diem <= 0:
                v.trang_thai = "het_han"
                continue
            tra, v.trang_thai = "Voucher hết hạn chưa dùng", "het_han"
        elif v.trang_thai == "da_dung" and v.booking_id and voucher_tour_tra_lai(db, v):
            tra = "Booking dùng voucher đã hủy"
        elif v.trang_thai == "da_dung" and v.don_ks_id and voucher_ks_tra_lai(db, v):
            tra = "Đơn khách sạn dùng voucher đã hủy / hết giờ giữ"
        elif v.trang_thai == "da_dung" and v.dat_ban_id and voucher_db_tra_lai(db, v):
            tra = "Đơn đặt bàn dùng voucher đã hủy / hết hạn"
        if tra:
            _tra_voucher(db, v, now, tra, "het_han" if v.trang_thai == "het_han" else "da_hoan")
            so_ghi += 1
    # lô quá hạn còn dư → ghi hết hạn
    lo, _ = phan_bo(_dong(db, chu))
    for r, con in lo:
        if con > 0 and r.het_han and r.het_han < hn:
            _ghi(db, chu, "HET_HAN", -con, now, ghi_chu=f"Hết hạn lô cộng {r.luc:%d/%m/%Y}")
            so_ghi += 1
    db.commit()
    return {"dang_bat": True, "ghi": so_ghi}


def _tra_voucher(db: Session, v: VoucherRewards, now: datetime, ly_do: str, trang_thai: str = "da_hoan") -> None:
    """Đơn dùng voucher bị hủy / hết giờ giữ: voucher đổi điểm → trả điểm (gia hạn tối thiểu 30 ngày);
    voucher quà (chào mừng / sinh nhật) → mở lại nếu còn hạn, không thì hết hạn. Không sinh điểm từ voucher quà."""
    hn = now.date()
    if v.so_diem <= 0:
        v.trang_thai = "cho_dung" if v.han_dung >= hn else "het_han"
        v.booking_id = v.don_ks_id = v.dat_ban_id = None
        v.ap_boi, v.ap_luc = "", None
        return
    v.trang_thai = trang_thai
    han = max(v.han_diem_goc or hn, hn + timedelta(days=GIA_HAN_KHI_TRA))
    _ghi(db, v.chu, "TRA_GIU", v.so_diem, now, voucher_id=v.id, het_han=han, ghi_chu=f"{ly_do} · {v.ma}")


# ── KS-16g · thưởng trưởng đoàn / giới thiệu · trần ưu đãi mới ─────────────────────────────────────

def _thuong_da_ghi(db: Session, chu: str | None, booking_id: int) -> int:
    cau = select(func.coalesce(func.sum(SoDiem.so_diem), 0)).where(SoDiem.loai == "THUONG", SoDiem.booking_id == booking_id)
    if chu is not None:
        cau = cau.where(SoDiem.chu == chu)
    return int(db.execute(cau).scalar_one())


def _thuong(db: Session, chu: str, ds: list, h: date, hn: date, now: datetime, han: date) -> int:
    """Thưởng trưởng đoàn (booking của chính chủ) + thưởng giới thiệu (chủ là người giới thiệu). Thưởng đã ghi chỉ
    bị thu lại khi booking ấy bị hủy — không bao giờ cắt vì trần."""
    so = 0
    for x in ds:
        if not x.doan or x.ngay < h or _thuong_da_ghi(db, chu, x.muc.id[1]):
            continue
        b = db.get(Booking, x.muc.id[1])
        p = phong_uu_dai_tour(db, b, chu=chu)
        diem = min(THUONG_TRUONG_DOAN, max(0, p["con"]) // GIA_TRI_DIEM) if p else 0
        if diem > 0:
            _ghi(db, chu, "THUONG", diem, now, booking_id=b.id, het_han=han,
                 ghi_chu=f"{b.code} · thưởng trưởng đoàn {b.pax} khách" + ("" if diem == THUONG_TRUONG_DOAN else " (theo trần ưu đãi)"))
            so += 1
    so += _thuong_gioi_thieu(db, chu, h, hn, now, han)
    # thưởng đã ghi mà booking bị hủy → thu lại
    for bid, tong in db.execute(select(SoDiem.booking_id, func.sum(SoDiem.so_diem)).where(
            SoDiem.chu == chu, SoDiem.loai == "THUONG").group_by(SoDiem.booking_id)).all():
        b = db.get(Booking, bid) if bid else None
        if tong and tong > 0 and (b is None or b.cancelled):
            _ghi(db, chu, "THUONG", -int(tong), now, booking_id=bid, ghi_chu=f"{b.code if b else bid} · đã hủy — thu lại thưởng")
            so += 1
    return so


def _thuong_gioi_thieu(db: Session, chu: str, h: date, hn: date, now: datetime, han: date) -> int:
    from app.services.hoa_hong_d06 import tinh_trang_booking
    moc = v3_tu(db)
    so = 0
    for g in db.execute(select(GioiThieuRewards).where(GioiThieuRewards.chu_gioi_thieu == chu,
                                                       GioiThieuRewards.trang_thai == "cho")).scalars().all():
        ds = [b for b in _bookings(db, g.chu_duoc) if not b.cancelled]
        if not ds:
            continue
        b = ds[0]
        if b.created_at and b.created_at < g.luc:
            g.trang_thai, g.booking_id, g.ghi_chu = "khong_du", b.id, "Tour đầu tiên đặt trước khi ghi mã giới thiệu"
            continue
        tt = tinh_trang_booking(db, b, db.get(Tour, b.tour_id) if b.tour_id else None, hn)
        if not tt["du"]:
            continue
        g.booking_id = b.id
        if int(round(float(b.amount or 0))) < DON_TOI_THIEU_MOI:
            g.trang_thai, g.ghi_chu = "khong_du", "Tour đầu tiên dưới 5 triệu"
            continue
        if tt["ngay"] < h or not _v3(moc, tt["ngay"]):
            g.trang_thai, g.ghi_chu = "khong_du", "Tour đầu tiên hoàn tất trước khi chương trình áp dụng"
            continue
        p = phong_uu_dai_tour(db, b)
        diem = min(THUONG_GIOI_THIEU, max(0, p["con"]) // GIA_TRI_DIEM) if p else 0
        if diem <= 0:
            g.trang_thai, g.ghi_chu = "khong_du", "Tour chưa có dự toán / hết trần ưu đãi"
            continue
        _ghi(db, chu, "THUONG", diem, now, booking_id=b.id, het_han=han,
             ghi_chu=f"Giới thiệu khách · tour {b.code}" + ("" if diem == THUONG_GIOI_THIEU else " (theo trần ưu đãi)"))
        g.trang_thai, g.ghi_chu = "da_thuong", f"+{diem:,} điểm".replace(",", ".")
        so += 1
    return so


def co_du_toan(t: Tour | None) -> bool:
    if t is None or not (t.price_per_pax or 0) or float(t.price_per_pax or 0) <= 0:
        return False
    return t.fixed_cost is not None or t.var_cost_per_pax is not None


def _ty_le_nguon_cao_nhat(db: Session, b: Booking) -> Fraction:
    """Hoa hồng nguồn tính theo bậc D06 CAO NHẤT của loại đối tác (chỉ để kiểm trần, không đổi hoa hồng D06)."""
    if not b.doi_tac_id:
        return Fraction(0)
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    from app.services.hoa_hong_d06 import BAC
    dt_ = db.get(DoiTacBanHang, b.doi_tac_id)
    ct = "ctv_d06" if dt_ is not None and dt_.loai == "ctv" else "dai_ly_d06"
    return Fraction(max(x[2] for x in BAC[ct]["bac"]), 10_000)


def phong_uu_dai_tour(db: Session, b: Booking, them: int = 0, chu: str | None = None, bo_diem: bool = False) -> dict | None:
    """Trần ưu đãi mới của một booking tour: C ≤ min(40%·G, G − 5%·B). G = (doanh thu dự kiến − dự toán chi) của tour,
    phân bổ theo tỷ trọng B của booking. C = điểm (đã cộng, hoặc ước theo hạng hiện tại) + voucher đã áp + thưởng đã ghi
    + hoa hồng nguồn (bậc D06 cao nhất) + `them`. Tour chưa có dự toán → None (không phát ưu đãi mới)."""
    from app.services import ops, rules as R
    t = db.get(Tour, b.tour_id) if b.tour_id else None
    if not co_du_toan(t):
        return None
    pax = max(int(t.planned_pax or 0), R.booked_pax(t))
    dt_ = Fraction(int(round(float(t.price_per_pax or 0)))) * pax
    B = int(round(float(b.amount or 0)))
    if dt_ <= 0 or B <= 0:
        return None
    G = (dt_ - Fraction(int(round(ops.tour_budget(db, t))))) * B / dt_
    tran = min(G * TRAN_G, G - B * SAN_B)
    chu = chu or chu_cua_booking(b)
    da_cong = int(db.execute(select(func.coalesce(func.sum(SoDiem.so_diem), 0)).where(
        SoDiem.booking_id == b.id, SoDiem.loai.in_(("CONG", "DAO")))).scalar_one())
    if bo_diem:
        diem = 0
    elif da_cong:
        diem = da_cong * GIA_TRI_DIEM
    else:
        he = he_so_hang(hang(db, chu)["hang"]) if chu else Fraction(1)
        net = int(round(float(b.amount or 0) - float(b.discount or 0)))
        pax_b = int(b.pax or 1)
        phan = Fraction(net, pax_b) if pax_b > DOAN_TREN else Fraction(net)
        diem = math.floor(phan * TY_LE_TICH_TOUR / GIA_TRI_DIEM * he) * GIA_TRI_DIEM
    voucher = int(db.execute(select(func.coalesce(func.sum(VoucherRewards.gia_tri), 0)).where(
        VoucherRewards.booking_id == b.id, VoucherRewards.trang_thai == "da_dung")).scalar_one())
    thuong = _thuong_da_ghi(db, None, b.id) * GIA_TRI_DIEM
    nguon = B * _ty_le_nguon_cao_nhat(db, b)
    C = diem + voucher + thuong + nguon + them
    return {"G": int(G), "tran": max(0, math.floor(tran)), "da_dung": math.ceil(C - them),
            "con": math.floor(tran - C)}


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
    if (v.gia_tri or 0) > tran:
        raise LoiDiem(f"Voucher {v.gia_tri:,} đ vượt trần 5% booking ({tran:,} đ)".replace(",", "."))
    _kiem_voucher_qua_tour(db, v, b, net)
    truoc = float(b.discount or 0)
    b.discount = truoc + (v.gia_tri or 0)
    v.trang_thai, v.booking_id, v.ap_boi, v.ap_luc = "da_dung", b.id, u.username, now
    R.audit(db, u.username, u.role, "ap_voucher_rewards", f"booking:{b.code}",
            before={"discount": truoc}, after={"discount": b.discount, "voucher": v.ma, "gia_tri": v.gia_tri})
    db.commit()
    return {"message": f"Đã áp {v.ma} ({v.gia_tri:,} đ) vào {b.code}".replace(",", "."), "giam_gia_moi": int(b.discount)}


def _kiem_voucher_qua_tour(db: Session, v: VoucherRewards, b: Booking, net: int) -> None:
    """KS-16g: voucher quà không cộng dồn với voucher khác; chào mừng chỉ cho tour ĐẦU TIÊN ≥ 5 tr; mọi voucher quà
    phải nằm trong trần ưu đãi của booking (tour chưa có dự toán → không áp)."""
    khac = db.execute(select(VoucherRewards).where(VoucherRewards.booking_id == b.id, VoucherRewards.trang_thai == "da_dung")).scalars().all()
    if khac and (v.loai != "doi_diem" or any(x.loai != "doi_diem" for x in khac)):
        raise LoiDiem("Voucher quà (chào mừng / sinh nhật) không dùng chung với voucher khác trên cùng booking")
    if v.loai == "doi_diem":
        return
    if net < int(v.don_toi_thieu or 0):
        raise LoiDiem(f"Voucher này cần booking từ {int(v.don_toi_thieu):,} đ".replace(",", "."))
    if v.loai == "chao_mung":
        dau = next((x for x in _bookings(db, v.chu) if not x.cancelled), None)
        if dau is None or dau.id != b.id:
            raise LoiDiem("Voucher chào mừng chỉ dùng cho tour đầu tiên")
    p = phong_uu_dai_tour(db, b, chu=v.chu)
    if p is None:
        raise LoiDiem("Tour chưa có dự toán (giá bán / chi phí) — chưa áp được ưu đãi mới")
    if (v.gia_tri or 0) > p["con"]:
        raise LoiDiem(f"Vượt trần ưu đãi của booking: còn {max(0, p['con']):,} đ (trần {p['tran']:,} đ, đã dùng {p['da_dung']:,} đ)".replace(",", "."))


def xem_voucher(db: Session, ma: str) -> dict:
    v = db.execute(select(VoucherRewards).where(VoucherRewards.ma == (ma or "").strip().upper())).scalars().first()
    if v is None:
        raise LoiDiem("Không có voucher này")
    from app.services.cong_ngoai import che
    return {"ma": v.ma, "chu": che(v.chu.split(":", 1)[1]), "gia_tri": v.gia_tri, "han_dung": v.han_dung.isoformat(),
            "trang_thai": TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai)}


# ── KS-16: khách tự nhập voucher khi đặt khách sạn ─────────────────────────────────────────────────

def voucher_tour_tra_lai(db: Session, v: VoucherRewards) -> bool:
    """KS-16h: booking tour dùng voucher bị hủy → trả khi KHÔNG có phí hủy (VTD / nhà cung cấp hủy, hoặc khách hủy
    miễn phí). Có phí hủy → voucher đã dùng."""
    b = db.get(Booking, v.booking_id)
    if b is None:
        return True
    return bool(b.cancelled) and float(b.cancel_charge or 0) <= 0


def doi_chieu_voucher_tour(db: Session, b: Booking, now: datetime | None = None) -> int:
    """Gọi ngay lúc hủy booking tour: voucher đủ điều kiện → trả điểm / mở lại luôn. Trả số voucher vừa xử lý."""
    n = 0
    for v in db.execute(select(VoucherRewards).where(VoucherRewards.booking_id == b.id, VoucherRewards.trang_thai == "da_dung")).scalars().all():
        if voucher_tour_tra_lai(db, v):
            _tra_voucher(db, v, now or datetime.now(), f"Booking {b.code} hủy, hoàn đủ")
            n += 1
    return n


def voucher_ks_tra_lai(db: Session, v: VoucherRewards) -> bool:
    """Voucher đã gắn đơn khách sạn được TRẢ ĐIỂM khi: đơn hủy có hoàn tiền (khoản hoàn đã trừ phần voucher), hoặc
    đơn hết giờ giữ phòng mà chưa nhận đồng nào. Đơn hủy không hoàn (gói không hoàn tiền) → voucher đã dùng hẳn."""
    from app.models.don_ks_vtd import DonKsVtd
    from app.services.don_ks_vtd import da_tra
    d = db.get(DonKsVtd, v.don_ks_id)
    if d is None or d.voucher_id != v.id:
        return True
    tra = da_tra(db, d)
    if d.trang_thai == "da_huy":
        # KS-16h (Chủ tịch 31/10/2026): chỉ trả khi HOÀN ĐỦ — VTD / khách sạn hủy, hoặc khách hủy trong điều kiện
        # miễn phí. Hủy mất phí (hoàn một phần) → voucher tính là đã dùng.
        return tra <= 0 or int(d.so_hoan or 0) >= tra
    return d.trang_thai == "het_han" and tra <= 0


def doi_chieu_voucher_ks(db: Session, d, now: datetime | None = None) -> bool:
    """Gọi ngay khi đơn khách sạn đổi trạng thái (hủy / hết giờ giữ): voucher đủ điều kiện trả → trả điểm luôn,
    để khách dùng lại không phải chờ. Trả True nếu vừa trả."""
    if not d.voucher_id:
        return False
    v = db.get(VoucherRewards, d.voucher_id)
    if v is None or v.trang_thai != "da_dung" or not voucher_ks_tra_lai(db, v):
        return False
    _tra_voucher(db, v, now or datetime.now(), f"Đơn khách sạn {d.ma} hủy / hết giờ giữ")
    return True


def kiem_voucher_ks(db: Session, tk, ma: str, tong_goc: int, hom_nay: date | None = None) -> VoucherRewards:
    """Kiểm voucher khách gõ ở bước thanh toán: đúng chủ, chưa dùng, còn hạn, không quá 5% đơn."""
    return _kiem_voucher(db, tk, ma, math.floor(int(tong_goc) * TRAN_VOUCHER), "tối đa 5% đơn", hom_nay)


def _kiem_voucher(db: Session, tk, ma: str, tran: int, ten_tran: str, hom_nay: date | None = None) -> VoucherRewards:
    hn = hom_nay or _hom_nay()
    if tk.loai not in ("khach_hang", "co_dong"):
        raise LoiDiem("Tài khoản đối tác không dùng voucher cá nhân")
    v = db.execute(select(VoucherRewards).where(VoucherRewards.ma == (ma or "").strip().upper())).scalars().first()
    if v is None or v.chu not in chu_cua_tai_khoan(tk):
        raise LoiDiem("Không có voucher này trong tài khoản của bạn")
    if v.trang_thai != "cho_dung":
        raise LoiDiem(f"Voucher {TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai).lower()}")
    if v.han_dung < hn:
        raise LoiDiem("Voucher đã quá hạn dùng")
    if v.pham_vi == "tour":
        raise LoiDiem(f"Voucher {LOAI_VOUCHER.get(v.loai, v.loai).lower()} chỉ dùng cho tour")
    if (v.gia_tri or 0) > tran:
        raise LoiDiem(f"Voucher {v.gia_tri:,} đ vượt mức {ten_tran} ({tran:,} đ)".replace(",", "."))
    return v


# ── KS-16b: voucher khi trả trước đặt bàn nhà hàng ─────────────────────────────────────────────────

def tran_dat_ban(d) -> int:
    """Trần voucher của một đơn đặt bàn: 5% tạm tính, không quá số phải trả trước (trước khi trừ voucher)."""
    return min(math.floor(int(d.tam_tinh) * TRAN_VOUCHER), int(d.phai_tra_truoc) + int(d.giam_voucher or 0))


def kiem_voucher_db(db: Session, tk, ma: str, d, hom_nay: date | None = None) -> VoucherRewards:
    return _kiem_voucher(db, tk, ma, tran_dat_ban(d), "tối đa 5% tạm tính và không quá số trả trước", hom_nay)


def voucher_db_tra_lai(db: Session, v: VoucherRewards) -> bool:
    """Như khách sạn: đơn đặt bàn hủy / không đến / nhà hàng từ chối / hết hạn mà có hoàn tiền, hoặc chưa trả đồng
    nào → trả điểm. Không hoàn đồng nào (phạt hết) → voucher đã dùng hẳn."""
    from app.models.dat_ban import DonDatBan
    from app.services.dat_ban import da_tra
    d = db.get(DonDatBan, v.dat_ban_id)
    if d is None or d.voucher_id != v.id:
        return True
    if d.trang_thai not in ("huy", "khong_den", "tu_choi", "het_han"):
        return False
    tra = da_tra(db, d)
    return tra <= 0 or int(d.so_hoan or 0) >= tra      # KS-16h: chỉ trả khi hoàn đủ


def doi_chieu_voucher_db(db: Session, d, now: datetime | None = None) -> bool:
    if not d.voucher_id:
        return False
    v = db.get(VoucherRewards, d.voucher_id)
    if v is None or v.trang_thai != "da_dung" or not voucher_db_tra_lai(db, v):
        return False
    _tra_voucher(db, v, now or datetime.now(), f"Đơn đặt bàn {d.ma} hủy / hết hạn")
    return True


def ap_voucher_ks(db: Session, tk, v: VoucherRewards, don, now: datetime) -> None:
    v.trang_thai, v.don_ks_id, v.ap_boi, v.ap_luc = "da_dung", don.id, f"cong:{tk.id}", now
    from app.services import rules as R
    R.audit(db, f"cong:{tk.id}", tk.loai, "ap_voucher_rewards", f"don_ks_vtd:{don.ma}",
            after={"voucher": v.ma, "gia_tri": v.gia_tri})


def he_so_cua(db: Session, tk, hom_nay: date | None = None) -> dict:
    """Hạng + hệ số của tài khoản cổng — cổng khách sạn hiện «điểm dự kiến». Đối tác / chưa bật: không có điểm."""
    hn = hom_nay or _hom_nay()
    h = hieu_luc_tu(db)
    chu = chu_chinh(tk)
    if tk.loai not in ("khach_hang", "co_dong") or chu is None or h is None or hn < h:
        return {"dang_bat": False, "hang": None, "he_so": 0, "dong_moi_diem": DONG_MOI_DIEM}
    hg = hang(db, chu, hn)
    v3 = _v3(v3_tu(db), hn)
    # v3: điểm khách sạn / nhà hàng tính trên 20% hoa hồng VTD — Kế toán chốt sau khi khách trả phòng, nên cổng
    # không ước được trước; `cach_tinh` cho giao diện đổi lời.
    return {"dang_bat": True, "hang": hg["hang"], "he_so": hg["he_so"], "dong_moi_diem": DONG_MOI_DIEM,
            "cach_tinh": "hoa_hong" if v3 else "gia_tri"}


def quyen_loi_don(db: Session, tk, b: Booking, hom_nay: date | None = None) -> dict | None:
    """KS-16h · «Biết rõ quyền lợi trước khi đặt» (v3 mục 11): điểm dự kiến của booking tour + voucher của khách
    áp được cho booking này (Sales áp khi khách đọc mã). Chỉ booking trực tiếp, chưa hủy, chưa thu đủ."""
    hn = hom_nay or _hom_nay()
    h = he_so_cua(db, tk, hn)
    if not h["dang_bat"] or b.cancelled:
        return None
    ctv = False
    if b.doi_tac_id:                       # KS-16i: đơn CTV tích điểm từ ngày áp v3 (trong trần), không dùng voucher
        from app.models.doi_tac_ban_hang import DoiTacBanHang
        dt_ = db.get(DoiTacBanHang, b.doi_tac_id)
        if dt_ is None or dt_.loai != "ctv_ban_hang" or not _v3(v3_tu(db), hn):
            return None
        ctv = True
    net = int(round(float(b.amount or 0) - float(b.discount or 0)))
    if net <= 0:
        return None
    pax = int(b.pax or 1)
    v3 = _v3(v3_tu(db), hn)
    doan = v3 and pax > DOAN_TREN
    co_so = Fraction(net, pax) if doan else Fraction(net)
    he = Fraction(str(h["he_so"]))
    diem = math.floor(co_so * TY_LE_TICH_TOUR / GIA_TRI_DIEM * he) + (THUONG_TRUONG_DOAN if doan else 0)
    tran = 0 if ctv else math.floor(net * TRAN_VOUCHER)
    dung = []
    for v in ([] if ctv else db.execute(select(VoucherRewards).where(VoucherRewards.chu.in_(chu_cua_tai_khoan(tk)), VoucherRewards.trang_thai == "cho_dung",
                                                     VoucherRewards.han_dung >= hn).order_by(VoucherRewards.han_dung)).scalars()):
        if (v.gia_tri or 0) > tran or net < int(v.don_toi_thieu or 0):
            continue
        if v.loai == "chao_mung":
            dau = next((x for x in _bookings(db, v.chu) if not x.cancelled), None)
            if dau is None or dau.id != b.id:
                continue
        dung.append({"ma": v.ma, "gia_tri": v.gia_tri, "loai_ten": LOAI_VOUCHER.get(v.loai, v.loai), "han_dung": v.han_dung.isoformat()})
    return {"diem_du_kien": diem, "hang": h["hang"], "he_so": h["he_so"], "co_so": int(co_so), "truong_doan": doan,
            "thuong_doan": THUONG_TRUONG_DOAN if doan else 0, "tran_voucher": tran, "voucher_dung_duoc": dung, "ctv": ctv}


def _cho_cong_ks(db: Session, chu: str, hom_nay: date) -> list[dict]:
    """Đơn khách sạn đã ở nhưng Kế toán chưa chốt — khách thấy «chờ chốt, dự kiến +N điểm»."""
    ra = []
    for d in _don_ks(db, chu):
        if d.trang_thai == "da_xac_nhan" and d.chot_luc is None and d.ra <= hom_nay:
            ra.append({"ma": d.ma, "co_so": _b_ks(db, d)})
    return ra


# ── KS-16g · quà chào mừng / sinh nhật · ngày sinh · giới thiệu ─────────────────────────────────────

def v3_dang_bat(db: Session, hn: date) -> bool:
    h = hieu_luc_tu(db)
    return h is not None and hn >= h and _v3(v3_tu(db), hn)


def _phat(db: Session, chu: str, loai: str, gia_tri: int, hn: date, now: datetime, pham_vi: str, toi_thieu: int) -> VoucherRewards:
    v = VoucherRewards(ma=_ma_voucher(db), chu=chu, so_diem=0, gia_tri=gia_tri, han_dung=hn + timedelta(days=HAN_VOUCHER_NGAY),
                       loai=loai, pham_vi=pham_vi, don_toi_thieu=toi_thieu, tao_luc=now)
    db.add(v); db.flush()
    return v


def phat_qua(db: Session, tk, hom_nay: date | None = None, now: datetime | None = None) -> list[str]:
    """Gọi khi khách mở «Điểm thưởng» trên cổng: phát voucher chào mừng (tài khoản chưa có tour nào, một lần mỗi người)
    và sinh nhật (tháng sinh, một lần mỗi năm; ngày sinh phải khai TRƯỚC tháng ấy). Trả danh sách mã vừa phát."""
    hn = hom_nay or _hom_nay()
    now = now or datetime.combine(hn, datetime.now().time())
    chu = chu_chinh(tk)
    if tk.loai not in ("khach_hang", "co_dong") or chu is None or not v3_dang_bat(db, hn):
        return []
    cac_chu = chu_cua_tai_khoan(tk)
    co = lambda loai: db.execute(select(VoucherRewards).where(VoucherRewards.chu.in_(cac_chu), VoucherRewards.loai == loai)  # noqa: E731
                                 .order_by(VoucherRewards.tao_luc.desc())).scalars().first()
    ra = []
    if co("chao_mung") is None and not any(not b.cancelled for c in cac_chu for b in _bookings(db, c)):
        ra.append(_phat(db, chu, "chao_mung", VOUCHER_CHAO_MUNG, hn, now, "tour", DON_TOI_THIEU_MOI).ma)
    ns = tk.ngay_sinh
    if ns and ns.month == hn.month and tk.ngay_sinh_luc and tk.ngay_sinh_luc.date() < hn.replace(day=1):
        sn = co("sinh_nhat")
        if sn is None or sn.tao_luc.year != hn.year:
            ra.append(_phat(db, chu, "sinh_nhat", VOUCHER_SINH_NHAT, hn, now, "tat_ca", 0).ma)
    if ra:
        db.commit()
    return ra


def khai_ngay_sinh(db: Session, tk, ngay: date, now: datetime | None = None) -> None:
    if tk.loai not in ("khach_hang", "co_dong"):
        raise LoiDiem("Chỉ tài khoản khách hàng / cổ đông")
    if tk.ngay_sinh is not None:
        raise LoiDiem("Ngày sinh đã khai — muốn sửa, liên hệ CSKH")
    now = now or datetime.now()
    if not (date(1900, 1, 1) <= ngay <= now.date()):
        raise LoiDiem("Ngày sinh không hợp lệ")
    tk.ngay_sinh, tk.ngay_sinh_luc = ngay, now
    db.commit()


def ma_gioi_thieu(db: Session, tk) -> str | None:
    if tk.loai not in ("khach_hang", "co_dong") or chu_chinh(tk) is None:
        return None
    if not tk.ma_gioi_thieu:
        from app.models.cong_ngoai import TaiKhoanNgoai
        while True:
            m = "GT" + "".join(secrets.choice(_CHU_MA) for _ in range(6))
            if not db.execute(select(TaiKhoanNgoai.id).where(TaiKhoanNgoai.ma_gioi_thieu == m)).first():
                break
        tk.ma_gioi_thieu = m
        db.commit()
    return tk.ma_gioi_thieu


def nhap_ma_gioi_thieu(db: Session, tk, ma: str, now: datetime | None = None) -> GioiThieuRewards:
    """Người được giới thiệu tự ghi mã TRƯỚC khi đặt tour đầu tiên. Không tự giới thiệu, mỗi tài khoản một lần."""
    from app.models.cong_ngoai import TaiKhoanNgoai
    now = now or datetime.now()
    if not gioi_thieu_mo(db) or not v3_dang_bat(db, now.date()):
        raise LoiDiem("Chương trình giới thiệu chưa mở")
    if tk.loai not in ("khach_hang", "co_dong") or chu_chinh(tk) is None:
        raise LoiDiem("Chỉ tài khoản khách hàng / cổ đông đã xác thực liên hệ")
    if db.execute(select(GioiThieuRewards.id).where(GioiThieuRewards.tai_khoan_id == tk.id)).first():
        raise LoiDiem("Tài khoản đã ghi mã giới thiệu")
    nguoi = db.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.ma_gioi_thieu == (ma or "").strip().upper())).scalars().first()
    if nguoi is None or nguoi.loai not in ("khach_hang", "co_dong") or chu_chinh(nguoi) is None:
        raise LoiDiem("Mã giới thiệu không đúng")
    cua_toi = set(chu_cua_tai_khoan(tk))
    if nguoi.id == tk.id or cua_toi & set(chu_cua_tai_khoan(nguoi)):
        raise LoiDiem("Không tự giới thiệu chính mình")
    if any(not b.cancelled for c in cua_toi for b in _bookings(db, c)):
        raise LoiDiem("Mã giới thiệu phải ghi trước khi đặt tour đầu tiên")
    g = GioiThieuRewards(chu_gioi_thieu=chu_chinh(nguoi), tai_khoan_gioi_thieu_id=nguoi.id, tai_khoan_id=tk.id,
                         chu_duoc=chu_chinh(tk), ma=nguoi.ma_gioi_thieu, luc=now)
    db.add(g); db.commit()
    return g


def ho_so_qua(db: Session, tk) -> dict:
    """Phần quà v3 của trang Điểm thưởng: ngày sinh, mã giới thiệu của mình, người mình đã giới thiệu."""
    from app.models.cong_ngoai import TaiKhoanNgoai
    mo = gioi_thieu_mo(db)
    da_ghi = db.execute(select(GioiThieuRewards).where(GioiThieuRewards.tai_khoan_id == tk.id)).scalars().first()
    ds = []
    for g in db.execute(select(GioiThieuRewards).where(GioiThieuRewards.tai_khoan_gioi_thieu_id == tk.id)
                        .order_by(GioiThieuRewards.luc.desc())).scalars():
        t = db.get(TaiKhoanNgoai, g.tai_khoan_id)
        from app.services.cong_ngoai import che
        ds.append({"nguoi": che(t.dien_thoai or t.email) if t else "", "trang_thai": g.trang_thai, "ghi_chu": g.ghi_chu,
                   "luc": g.luc.date().isoformat()})
    return {"ngay_sinh": tk.ngay_sinh.isoformat() if tk.ngay_sinh else None,
            "gioi_thieu_mo": mo, "ma_gioi_thieu": ma_gioi_thieu(db, tk) if mo else None,
            "da_ghi_ma": da_ghi.ma if da_ghi else None, "da_gioi_thieu": ds,
            "thuong_gioi_thieu": THUONG_GIOI_THIEU, "thuong_truong_doan": THUONG_TRUONG_DOAN}


# ── xem ─────────────────────────────────────────────────────────────────────────────────────────

def _nguon(r: SoDiem) -> str:
    if r.loai == "THUONG":
        return "thuong"
    if r.voucher_id:
        return "voucher"
    return "khach_san" if r.don_ks_id else ("dat_ban" if r.dat_ban_id else ("tour" if r.booking_id else ""))


def _lich_su(db: Session, chu: str) -> list[dict]:
    return [{"luc": r.luc.isoformat(timespec="minutes"), "loai": LOAI_DONG.get(r.loai, r.loai), "so_diem": r.so_diem,
             "het_han": r.het_han.isoformat() if r.het_han and r.so_diem > 0 else None, "noi_dung": r.ghi_chu,
             "nguon": _nguon(r)}
            for r in reversed(_dong(db, chu))][:100]


def _voucher(db: Session, chu: str) -> list[dict]:
    ra = []
    for v in db.execute(select(VoucherRewards).where(VoucherRewards.chu == chu).order_by(VoucherRewards.tao_luc.desc())).scalars():
        b = db.get(Booking, v.booking_id) if v.booking_id else None
        if b is None and v.dat_ban_id:
            from app.models.dat_ban import DonDatBan
            dd = db.get(DonDatBan, v.dat_ban_id)
            ma_don = dd.ma if dd else None
        elif b is None and v.don_ks_id:
            from app.models.don_ks_vtd import DonKsVtd
            dk = db.get(DonKsVtd, v.don_ks_id)
            ma_don = dk.ma if dk else None
        else:
            ma_don = b.code if b else None
        tt = TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai)
        if v.so_diem <= 0 and v.trang_thai == "het_han":
            tt = "Hết hạn"
        ra.append({"ma": v.ma, "gia_tri": v.gia_tri, "so_diem": v.so_diem, "han_dung": v.han_dung.isoformat(),
                   "trang_thai": v.trang_thai, "trang_thai_ten": tt, "booking": ma_don,
                   "loai": v.loai, "loai_ten": LOAI_VOUCHER.get(v.loai, v.loai), "pham_vi": v.pham_vi,
                   "don_toi_thieu": int(v.don_toi_thieu or 0)})
    return ra


def tong_quan(db: Session, chu_ds: list[str], hom_nay: date | None = None) -> dict:
    hn = hom_nay or _hom_nay()
    h = hieu_luc_tu(db)
    dang_bat = h is not None and hn >= h
    ra = {"dang_bat": dang_bat, "hieu_luc_tu": h.isoformat() if h else None, "kha_dung": 0, "dang_giu": 0, "am": 0,
          "sap_het_han": 0, "sap_het_han_ngay": None, "lich_su": [], "voucher": [], "chu": chu_ds[0] if chu_ds else None,
          "quy_doi": GIA_TRI_DIEM, "doi_toi_thieu": DIEM_DOI_TOI_THIEU, "cho_cong": []}
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
        ra["cho_cong"] += _cho_cong_ks(db, chu, hn)
        hg = hang(db, chu, hn)
        if best is None or hg["chi_tieu_12_thang"] > best["chi_tieu_12_thang"]:
            best = hg
    ra["hang"] = best or hang_rong()
    he = Fraction(ra["hang"]["he_so"]).limit_denominator(100)
    v3 = _v3(v3_tu(db), hn)
    for x in ra["cho_cong"]:
        # v3: điểm KS theo hoa hồng Kế toán chốt — chưa chốt thì chưa có số
        x["du_kien"] = None if v3 else math.floor(Fraction(x["co_so"], DONG_MOI_DIEM) * he)
    ra["luat"] = "v3" if v3 else "cu"
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
            "voucher": [v for v in t["voucher"] if v["trang_thai"] == "cho_dung"], "khoan": khoan(db, chu)}


def khoan(db: Session, chu: str, hom_nay: date | None = None) -> list[dict]:
    """KS-16: từng khoản tích điểm của một chủ (tour · đặt bàn · khách sạn) và điểm đã cộng — Sales / Kế toán tra."""
    hn = hom_nay or _hom_nay()
    du = {x.muc.id: x.net for x in _du_dk(db, chu, hn)}
    diem: dict = {}
    for r in db.execute(select(SoDiem).where(SoDiem.chu == chu, SoDiem.loai.in_(("CONG", "DAO", "THUONG")), SoDiem.voucher_id.is_(None))).scalars():
        k = ("d", r.dat_ban_id) if r.dat_ban_id else (("k", r.don_ks_id) if r.don_ks_id else ("b", r.booking_id))
        diem[k] = diem.get(k, 0) + r.so_diem
    ten = {"b": "Tour", "d": "Đặt bàn", "k": "Khách sạn"}
    ra = []
    for m in _muc(db, chu):
        ra.append({"ma": m.code, "loai": ten[m.id[0]], "huy": m.cancelled, "du_dieu_kien": m.id in du,
                   "co_so": du.get(m.id, 0), "diem": diem.get(m.id, 0)})
    return ra[-50:][::-1]


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

