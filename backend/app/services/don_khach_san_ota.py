# -*- coding: utf-8 -*-
"""Luật của đơn khách sạn — các hàng rào mà tài liệu Agoda nói ra bằng chữ.

Tệp này KHÔNG gọi mạng. Nó chỉ trả lời: đơn này đã đủ điều kiện để sang bước sau chưa.

Mỗi hàng rào dưới đây đến từ một câu trong tài liệu, và mỗi câu ấy mô tả một cách hỏng đã xảy ra
với một đối tác nào đó trước mình. Chép lại thành mã là cách duy nhất để không phải học lại.
"""
from datetime import date, datetime, timedelta

from app.models.don_khach_san_ota import (BUOC_DON, DON_DONG, KIEU_THANH_TOAN, LY_DO_HUY,
                                          NGUON_CHET, NGUON_SONG, NGUON_THU, TRANG_THAI_DON,
                                          TRANG_THAI_NGUON)
from app.services.khach_san_ota import LoiOta, co_quyen

# «The searchId is only valid for 1 hr» — và quá hạn thì Agoda trả lỗi 912, lúc khách đã điền
# xong tên và đang chờ. Chặn trước ở đây rẻ hơn.
HAN_MA_TIM_GIAY = 3600
# waitTime khuyến nghị của Book API.
HAN_DAT_GIAY = 120
# «Cancellations are allowed up to 1 day before check-in.»
NGAY_CHOT_HUY = 1

# Chín điều kiện phải giống hệt nhau ở cả ba bước Search → Precheck → Book. Lệch một cái thì
# Agoda từ chối, hoặc tệ hơn: nhận, rồi đặt một phòng khác với phòng khách đã xem giá.
PHAI_KHOP = ("ngay_nhan", "ngay_tra", "nuoc_khach", "tien_te", "ngon_ngu",
             "so_phong", "nguoi_lon", "tre_em", "tuoi_tre_em")


def _gio(a, b) -> float:
    return abs((a - b).total_seconds())


def con_han_ma_tim(don, now=None) -> bool:
    """`searchId` sống đúng một giờ kể từ lúc hỏi giá."""
    if not don.ma_tim or don.tim_luc is None:
        return False
    return _gio(now or datetime.utcnow(), don.tim_luc) < HAN_MA_TIM_GIAY


def lech_ba_buoc(don, gui: dict) -> list[str]:
    """Những ô mà lần gọi này khai khác với lúc hỏi giá."""
    l = []
    for k in PHAI_KHOP:
        if k not in gui:
            continue
        cu, moi = getattr(don, k, None), gui[k]
        if isinstance(cu, (date, datetime)) and isinstance(moi, str):
            moi = date.fromisoformat(moi)
        if str(cu) != str(moi):
            l.append(f"{k}: đã hỏi giá «{cu}», nay gửi «{moi}»")
    return l


def thieu_de_dat(don, ota, now=None) -> list[str]:
    """Chưa đủ cái gì thì chưa được gọi Book."""
    t = []
    if not co_quyen(ota, "BOOK"):
        t.append("chưa ghi nhận nguồn cấp quyền BOOK")
    if getattr(ota, "moi_truong", "tat") == "tat":
        t.append("môi trường đang Tắt")
    # Thẻ tham chiếu là cách duy nhất tra lại một lần gọi quá hạn. Thiếu nó thì một lần mạng
    # chập là một lần không ai biết khách đã bị tính tiền hay chưa.
    if not (don.the_tham_chieu or "").strip():
        t.append("chưa có thẻ tham chiếu — quá hạn sẽ không tra lại được")
    if not don.ma_khoi:
        t.append("chưa có mã khối phòng")
    if not con_han_ma_tim(don, now):
        t.append("mã tìm đã quá một giờ — phải hỏi giá lại")
    if float(don.gia_gom_thue or 0) <= 0:
        t.append("chưa có giá đã gồm thuế")
    if don.trang_thai in DON_DONG:
        t.append("đơn đã đóng")
    if don.ma_don_nguon:
        t.append("đơn này đã đặt rồi")
    return t


def dat_lai_duoc(don) -> bool:
    """Quá hạn Book thì KHÔNG được gửi lại ngay.

    Tài liệu: «should not immediately resend the same booking request». Phải tra Booking List
    bằng thẻ tham chiếu trước — vì rất có thể Agoda đã nhận, chỉ là trả lời về muộn.
    """
    return don.trang_thai != "cho_tra_cuu"


def ghi_qua_han_dat(don) -> None:
    don.trang_thai = "cho_tra_cuu"


def ghi_dat_xong(don, tra_loi: dict, now=None) -> None:
    """Chép kết quả Book vào đơn. `processing` true nghĩa là CHƯA xong, phải tra tiếp."""
    ma = int(tra_loi.get("id") or 0)
    if ma <= 0:
        raise LoiOta("Nguồn không trả mã đơn")
    don.ma_don_nguon = ma
    don.ma_hanh_trinh = int(tra_loi.get("itineraryId") or 0)
    don.dang_xu_ly = bool(tra_loi.get("processing"))
    don.dat_luc = now or datetime.utcnow()
    don.trang_thai = "da_dat"
    don.trang_thai_nguon = "BookingReceived"


def nhan_trang_thai_nguon(don, trang_thai: str) -> None:
    if trang_thai not in TRANG_THAI_NGUON:
        raise LoiOta("Trạng thái nguồn lạ: " + str(trang_thai)[:40])
    don.trang_thai_nguon = trang_thai
    if trang_thai in NGUON_CHET:
        don.trang_thai = "da_huy" if "Cancel" in trang_thai else "that_bai"
    elif trang_thai in NGUON_SONG:
        don.trang_thai = "da_dat"
        don.dang_xu_ly = False


def so_de_doi_chieu(don) -> str:
    """Số đưa cho khách và cho khách sạn, theo đúng thứ tự tài liệu dặn."""
    return (don.so_xac_nhan_ks or "").strip() or (don.tham_chieu_nguon or "").strip() \
        or (str(don.ma_don_nguon) if don.ma_don_nguon else "")


def thieu_de_huy(don, ota, hom_nay=None) -> list[str]:
    t = []
    if not co_quyen(ota, "CANCEL"):
        t.append("chưa ghi nhận nguồn cấp quyền CANCEL")
    if not don.ma_don_nguon:
        t.append("đơn chưa có mã bên nguồn")
    if don.trang_thai == "da_huy" or don.trang_thai_nguon in NGUON_CHET:
        t.append("đơn đã huỷ rồi")
    if don.ngay_nhan:
        n = hom_nay or date.today()
        if n >= don.ngay_nhan - timedelta(days=NGAY_CHOT_HUY):
            # Không phải «không huỷ được» — mà là không huỷ qua API được. Phải có người thật.
            t.append("quá hạn huỷ qua API — phải báo nguồn bằng người")
    return t


def lech_xac_nhan_huy(don, xem: dict, gui: dict) -> list[str]:
    """Ba con số phải khớp y nguyên bản xem trước, lệch là lỗi 914.

    «BookingID, Reference, and RefundRateInclusive must match to proceed.»
    """
    l = []
    if int(gui.get("bookingId") or 0) != int(xem.get("bookingId") or -1):
        l.append("mã đơn lệch")
    if int(gui.get("reference") or 0) != int(xem.get("reference") or -1):
        l.append("số tham chiếu lệch")
    a = round(float(gui.get("refundInclusive") or 0), 2)
    b = round(float(xem.get("refundInclusive") or -1), 2)
    if a != b:
        l.append(f"số tiền hoàn lệch: xem trước {b}, gửi {a}")
    ly = gui.get("cancelReason")
    if ly is None or int(ly) not in LY_DO_HUY:
        l.append("lý do huỷ không có trong bảng mã của nguồn")
    return l


def vao_bao_cao_tien(don) -> bool:
    """Đơn nào được tính vào tiền.

    Hai thứ bị loại, và cả hai đều là tiền ảo nếu lọt: đơn dựng trong Sandbox, và đơn Agoda
    đánh dấu `BookingTest`.
    """
    if don.moi_truong != "that":
        return False
    if don.trang_thai_nguon in NGUON_THU:
        return False
    return don.trang_thai == "da_dat" and don.trang_thai_nguon in NGUON_SONG


def tom_tat(don) -> dict:
    return {
        "id": don.id,
        "the_tham_chieu": don.the_tham_chieu,
        "trang_thai": don.trang_thai,
        "trang_thai_ten": TRANG_THAI_DON.get(don.trang_thai, don.trang_thai),
        "trang_thai_nguon": don.trang_thai_nguon,
        "ma_don_nguon": don.ma_don_nguon or None,
        "so_doi_chieu": so_de_doi_chieu(don),
        "moi_truong": don.moi_truong,
        "ngay_nhan": don.ngay_nhan.isoformat() if don.ngay_nhan else None,
        "ngay_tra": don.ngay_tra.isoformat() if don.ngay_tra else None,
        "tien_te": don.tien_te,
        "gia_gom_thue": float(don.gia_gom_thue or 0),
        "kieu_thanh_toan": KIEU_THANH_TOAN.get(don.kieu_thanh_toan, don.kieu_thanh_toan),
        "dang_xu_ly": bool(don.dang_xu_ly),
        "vao_bao_cao_tien": vao_bao_cao_tien(don),
        "buoc": BUOC_DON,
        # ── KS-12 · những ô KHÁCH khai ────────────────────────────────────────────────
        # `tom_tat` là thứ DUY NHẤT màn Điều hành đọc. KS-11 thêm bảy cột vào bảng mà không
        # thêm vào đây, nên đơn khách gửi lên hiện ra trống — không lỗi, không đỏ, chỉ trống.
        # Dùng getattr có mặc định: hàm này còn được gọi với vật giả trong phép thử KS-6.
        "la_yeu_cau_khach": bool(getattr(don, "tai_khoan_ngoai_id", None)),
        "cong": getattr(don, "cong", "") or "",
        "noi_den": getattr(don, "noi_den", "") or "",
        "nguoi_nhan_phong": getattr(don, "nguoi_nhan_phong", "") or "",
        "lien_he": getattr(don, "lien_he", "") or "",
        "yeu_cau_them": getattr(don, "yeu_cau_them", "") or "",
        "gui_luc": (getattr(don, "gui_luc", None).isoformat()
                    if getattr(don, "gui_luc", None) else None),
        "so_phong": getattr(don, "so_phong", 1),
        "nguoi_lon": getattr(don, "nguoi_lon", 1),
        "tre_em": getattr(don, "tre_em", 0),
    }
