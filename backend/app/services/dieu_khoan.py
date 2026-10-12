"""Đợt E4a – ĐIỀU KHOẢN THANH TOÁN và ĐỢT THANH TOÁN.

════════════════════════════════════════════════════════════════════════════════════════════════
VẤN ĐỀ
════════════════════════════════════════════════════════════════════════════════════════════════

`nghia_vu_thanh_toan` cho tới nay là MỘT dòng mang MỘT `tong_nghia_vu`, MỘT `da_tra`, và MỘT
`ngay_cam_ket` nhập tay. Hệ quả đo được:

  · Hợp đồng "50% cọc – 50% trước khởi hành 7 ngày" chỉ có MỘT hạn. Bảng dòng tiền dồn cả 189
    triệu vào một tháng, trong khi thực tế tiền ra làm hai lần cách nhau ba tuần.
  · `ngay_cam_ket` gõ tay, nên không đối chiếu được với hợp đồng và không ai dò ngược được vì sao
    hạn là ngày ấy.

Đợt này giải cả hai, và KHÔNG phá nguyên tắc gốc của VPM-11: nghĩa vụ vẫn MỘT dòng, MỘT mã gốc,
vẫn là nơi giữ câu trả lời "còn phải trả bao nhiêu". Các đợt là dòng CON.

════════════════════════════════════════════════════════════════════════════════════════════════
MỘT ĐIỀU KHOẢN NÓI BA CÂU
════════════════════════════════════════════════════════════════════════════════════════════════

    đếm ngày TỪ MỐC NÀO  ·  chia MẤY ĐỢT  ·  mỗi đợt BAO NHIÊU % và LỆCH MỐC MẤY NGÀY

Số ngày âm là TRƯỚC mốc, dương là SAU. "50% ở −30, 50% ở −7" tính từ ngày khởi hành là đúng cách
phòng Điều hành vẫn nói.

KHAI TRONG CSDL, KHÔNG PHẢI TRONG MÃ – khác với `chung_tu_loai` của Đợt E3, và khác có lý do:
loại chứng từ là một danh mục của chế độ kế toán, mấy năm mới đổi; điều khoản thanh toán là một
thoả thuận thương mại, mỗi nhà cung cấp một kiểu, và Kế toán phải thêm được mà không chờ ai sửa
phần mềm. Đổi lại, nó phải CÓ CHỮ KÝ: Chủ tịch chốt 12/10/2026 rằng điều khoản do Chủ tịch ký,
y như bảng tham số chính sách.

════════════════════════════════════════════════════════════════════════════════════════════════
LÀM TRÒN: ĐỢT CUỐI GÁNH PHẦN LẺ
════════════════════════════════════════════════════════════════════════════════════════════════

Chia 100.000.000 đ làm ba đợt 33/33/34 thì ba lần làm tròn có thể ra tổng lệch vài đồng. Vài đồng
ấy KHÔNG vô hại: sổ nghĩa vụ lấy `tong_nghia_vu` làm chuẩn, nên "tổng các đợt ≠ tổng nghĩa vụ"
là một cảnh báo đỏ trên màn hình, và một cảnh báo đỏ sai vì làm tròn sẽ dạy người dùng bỏ qua nó.

Nên: mọi đợt trừ đợt cuối làm tròn tới đồng, ĐỢT CUỐI = tổng trừ đi tất cả các đợt trước. Tổng
luôn khớp đến đồng, không có ngoại lệ. `test_e4_4` dựng đúng cảnh chia ba phần bằng nhau.
"""
from __future__ import annotations

from datetime import date, timedelta

# ════════════════════════════════════════════════════════════════════════════════════════════════
# MỐC ĐẾM NGÀY
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Năm mốc, và mỗi mốc kèm TÊN TRƯỜNG mà phép suy đi tìm. Khai cả hai ở một chỗ để không có cảnh
# bảng này có một mốc mà mã không biết lấy ngày ở đâu.
MOC: dict[str, tuple[str, str]] = {
    # mã                 (tên hiển thị,                         lấy ngày ở đâu)
    "ky_hop_dong":   ("Ngày ký hợp đồng",                   "ngay_ky_hop_dong"),
    "khoi_hanh":     ("Ngày khởi hành tour",                "ngay_khoi_hanh"),
    "nhan_hoa_don":  ("Ngày nhận hóa đơn",                  "ngay_hoa_don"),
    "nghiem_thu":    ("Ngày nghiệm thu / kết thúc tour",    "ngay_ket_thuc"),
    "ngay_co_dinh":  ("Ngày cố định trong tháng",           ""),
}

# Loại chữ ký của điều khoản – ĐỌC TỪ `chu_ky.VAI_KY_CAN`, không khai lại ở đây. Một bảng luật,
# nhiều nơi đọc: bài học Đợt LG1, LG2 và LG3.
LOAI_CHU_KY = "dieu_khoan_thanh_toan"


class SaiDieuKhoan(ValueError):
    """Điều khoản khai không hợp lệ – nói rõ sai ở đâu, không trả âm thầm."""


def ten_moc(ma: str) -> str:
    return MOC[ma][0] if ma in MOC else ma


# ════════════════════════════════════════════════════════════════════════════════════════════════
# KIỂM MỘT ĐIỀU KHOẢN
# ════════════════════════════════════════════════════════════════════════════════════════════════
def kiem_dot(dot: list[dict]) -> None:
    """Ném lỗi nếu danh sách đợt không dùng được. Gọi TRƯỚC khi lưu, không phải lúc đọc ra.

    Một điều khoản thiếu phần trăm là một khoản tiền không có hạn – nó không hỏng ngay, nó hỏng
    lúc bảng dòng tiền thiếu đúng phần ấy mà không ai biết."""
    if not dot:
        raise SaiDieuKhoan("Điều khoản phải có ít nhất một đợt.")
    if len(dot) > 12:
        raise SaiDieuKhoan(f"Tối đa 12 đợt, điều khoản này khai {len(dot)}.")
    tong = 0.0
    for i, d in enumerate(dot, start=1):
        try:
            ty_le = float(d.get("ty_le"))
        except (TypeError, ValueError):
            raise SaiDieuKhoan(f"Đợt {i} chưa có tỷ lệ phần trăm.")
        if ty_le <= 0:
            raise SaiDieuKhoan(f"Đợt {i} có tỷ lệ {ty_le}% – tỷ lệ phải lớn hơn 0.")
        try:
            int(d.get("lech_ngay"))
        except (TypeError, ValueError):
            raise SaiDieuKhoan(f"Đợt {i} chưa có số ngày lệch mốc (số âm = trước mốc).")
        tong += ty_le
    # So tới 0,01% chứ không so bằng nhau tuyệt đối: 1/3 + 1/3 + 1/3 trong số thực không ra đúng 100.
    if abs(tong - 100.0) > 0.01:
        raise SaiDieuKhoan(
            f"Tổng tỷ lệ các đợt là {tong:g}%, phải đúng 100%. "
            f"Thiếu phần trăm nghĩa là có một phần tiền không đợt nào gánh, và phần ấy sẽ không "
            f"hiện ở tháng nào trên bảng dòng tiền.")


def kiem_moc(ma: str) -> str:
    if ma not in MOC:
        raise SaiDieuKhoan(f"Mốc đếm ngày `{ma}` không có trong bảng. Chọn một trong: "
                           + ", ".join(MOC))
    return ma


# ════════════════════════════════════════════════════════════════════════════════════════════════
# SUY HẠN VÀ CHIA TIỀN
# ════════════════════════════════════════════════════════════════════════════════════════════════
def suy_han(ngay_moc: date | None, lech_ngay: int) -> date | None:
    """Hạn của một đợt. Mốc rỗng thì hạn rỗng – KHÔNG lấy hôm nay thay thế.

    Lấy hôm nay làm mốc thay cho một ngày chưa biết là bịa ra một hạn, và một hạn bịa trông y hệt
    một hạn thật trên màn hình. Rỗng thì đi vào rổ "chưa đủ dữ liệu dự báo" của sổ nghĩa vụ."""
    if ngay_moc is None:
        return None
    return ngay_moc + timedelta(days=int(lech_ngay))


def can_cu_han(moc: str, lech_ngay: int) -> str:
    """Câu giải thích đi kèm hạn, hiện ngay cạnh ngày trên màn hình: `khởi hành −7`.

    Có câu này thì người đọc dò ngược được về điều khoản; không có thì một ngày trên màn hình là
    một con số không ai kiểm được."""
    n = int(lech_ngay)
    dau = "−" if n < 0 else "+"
    return f"{ten_moc(moc)} {dau}{abs(n)} ngày"


def chia_tien(tong: float | None, dot: list[dict]) -> list[float]:
    """Chia tổng nghĩa vụ ra từng đợt. TỔNG CÁC ĐỢT LUÔN BẰNG TỔNG, đến từng đồng.

    Đợt cuối = tổng trừ các đợt trước, chứ không phải tổng × tỷ lệ cuối. Xem ghi chú đầu tệp."""
    kiem_dot(dot)
    if tong is None:
        return [0.0] * len(dot)
    tong = float(tong)
    ra: list[float] = []
    for d in dot[:-1]:
        ra.append(round(tong * float(d["ty_le"]) / 100.0))
    ra.append(round(tong - sum(ra)))
    return ra


def dung_dot(tong: float | None, dot: list[dict], moc: str, ngay_moc: date | None) -> list[dict]:
    """Dựng danh sách đợt đã tính đủ tiền, hạn và căn cứ – sẵn sàng ghi xuống bảng."""
    kiem_moc(moc)
    tien = chia_tien(tong, dot)
    ra = []
    for i, (d, t) in enumerate(zip(dot, tien), start=1):
        ra.append({
            "so_thu_tu": i,
            "dien_giai": str(d.get("dien_giai") or f"Đợt {i}/{len(dot)}")[:200],
            "so_tien": t,
            "ngay_han": suy_han(ngay_moc, d["lech_ngay"]),
            "can_cu_han": can_cu_han(moc, d["lech_ngay"]),
        })
    return ra


# ════════════════════════════════════════════════════════════════════════════════════════════════
# SỬA MỘT ĐIỀU KHOẢN ĐANG DÙNG – ĐỢT NÀO ĐƯỢC ĐỘNG VÀO
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Chủ tịch chốt 12/10/2026: sửa điều khoản thì tính lại hạn cho CẢ những hợp đồng đang gắn.
#
# Nhưng câu ấy đụng một luật đã có chữ ký từ 11/9/2026, ghi ngay đầu `models/nghia_vu.py`:
# "Thay lịch trả không tự xoá quá hạn theo cam kết". Nên phạm vi tính lại hẹp đúng hai bước:
#
#   · ĐỢT ĐÃ TRẢ      – giữ nguyên. Dời hạn một khoản đã xong là viết lại lịch sử.
#   · ĐỢT ĐANG QUÁ HẠN – giữ nguyên. Dời sang tương lai là nhãn đỏ biến mất trong khi tiền vẫn
#                        chưa trả. Đây đúng là thứ luật trên cấm.
#   · ĐỢT CHƯA TRẢ, CÒN Ở TƯƠNG LAI – nhận hạn mới.
#
# `test_e4_8` và `test_e4_9` dựng đúng hai cảnh bị loại.
def duoc_tinh_lai(ngay_han: date | None, so_tien: float | None, da_tra: float | None,
                  hom_nay: date) -> bool:
    if (da_tra or 0) > 0:
        return False
    if ngay_han is not None and ngay_han < hom_nay:
        return False
    return True


def vi_sao_khong_tinh_lai(ngay_han: date | None, so_tien: float | None, da_tra: float | None,
                          hom_nay: date) -> str:
    """Lý do bị loại, viết cho người đọc. Rỗng nghĩa là đợt ấy ĐƯỢC tính lại."""
    if (da_tra or 0) > 0:
        return "đã trả – dời hạn của một khoản đã xong là viết lại lịch sử"
    if ngay_han is not None and ngay_han < hom_nay:
        return ("đang quá hạn – dời sang tương lai là nhãn đỏ biến mất trong khi tiền vẫn chưa "
                "trả (luật sổ nghĩa vụ 11/9/2026)")
    return ""
