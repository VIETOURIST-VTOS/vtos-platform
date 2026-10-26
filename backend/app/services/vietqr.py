"""KH-2 · Mã QR chuyển khoản theo chuẩn VietQR (EMVCo, Napas 247) — sinh TẠI MÁY, không gọi dịch vụ ngoài.

Nội dung chuyển khoản luôn là MÃ BOOKING (BKxxxx-xxxx): robot SePay hiện có (`payments.match_transaction`)
đã khớp «mã BK + đúng số tiền còn phải thu» thành phiếu thu tự động. Trả cọc thì số tiền không bằng
phần còn lại → robot chuyển Kế toán xác nhận, đúng như Chủ tịch duyệt.
"""
import unicodedata

# Mã BIN Napas của các ngân hàng phổ biến. Tra theo TÊN ngân hàng trong danh mục TK của Kế toán.
BIN = {
    "vietcombank": "970436", "vcb": "970436", "vietinbank": "970415", "bidv": "970418", "agribank": "970405",
    "techcombank": "970407", "mbbank": "970422", "mb": "970422", "quandoi": "970422", "acb": "970416", "achau": "970416",
    "vpbank": "970432", "tpbank": "970423", "tienphong": "970423", "sacombank": "970403", "hdbank": "970437",
    "vib": "970441", "quocte": "970441", "shb": "970443", "eximbank": "970431", "msb": "970426", "hanghai": "970426",
    "ocb": "970448", "phuongdong": "970448", "seabank": "970440", "lpbank": "970449", "lienviet": "970449",
    "namabank": "970428", "baca": "970409", "abbank": "970425", "vietabank": "970427", "pvcombank": "970412",
    "baoviet": "970438", "kienlong": "970452", "vietbank": "970433", "ncb": "970419", "quocdan": "970419",
    "saigonbank": "970400", "scb": "970429", "dongabank": "970406", "gpbank": "970408", "oceanbank": "970414",
    "cake": "546034", "ubank": "546035", "timo": "963388",
}


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def bin_cua(ten_ngan_hang: str) -> str | None:
    k = "".join(ch for ch in _khong_dau(ten_ngan_hang) if ch.isalnum())
    # Khoá dài trước để «vietabank» không bị «vietbank» bắt nhầm, «mbbank» trước «mb».
    for key in sorted(BIN, key=len, reverse=True):
        if key in k:
            return BIN[key]
    return None


def _tlv(tag: str, v: str) -> str:
    return f"{tag}{len(v):02d}{v}"


def crc16(s: str) -> str:
    crc = 0xFFFF
    for b in s.encode("utf-8"):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def noi_dung_sach(s: str) -> str:
    """Ngân hàng chỉ giữ chữ không dấu, số, khoảng trắng; tối đa 25 ký tự cho chắc."""
    return "".join(ch for ch in _khong_dau(s).upper() if ch.isalnum() or ch in " -")[:25]


def payload(bin_: str, so_tk: str, so_tien: int, noi_dung: str) -> str:
    tk = "".join(ch for ch in so_tk if ch.isalnum())
    if not bin_ or not tk:
        raise ValueError("Thiếu mã ngân hàng hoặc số tài khoản")
    if so_tien <= 0:
        raise ValueError("Số tiền phải lớn hơn 0")
    nguoi_nhan = _tlv("00", bin_) + _tlv("01", tk)
    m38 = _tlv("00", "A000000727") + _tlv("01", nguoi_nhan) + _tlv("02", "QRIBFTTA")
    s = (_tlv("00", "01") + _tlv("01", "12") + _tlv("38", m38) + _tlv("53", "704") + _tlv("54", str(int(so_tien)))
         + _tlv("58", "VN") + _tlv("62", _tlv("08", noi_dung_sach(noi_dung))) + "6304")
    return s + crc16(s)
