# -*- coding: utf-8 -*-
"""Bộ nạp phòng ban – tệp thứ ba: quyết toán tour CHI TIẾT theo tệp một chuyến.

Vì sao lại một tệp nữa chứ không viết nối vào intake_phong_ban.py hay _2.py: ba robot đang sửa cùng
một kho mã trong cùng một ngày. Tệp _2 đã 81.000 byte, và một tệp lớn do nhiều bên cùng sửa là một
lần gộp hỏng chờ sẵn. Cùng lý do đã tách _2 ra khỏi tệp đầu.

VÀ VÌ SAO ĐÂY LÀ BỘ NẠP RIÊNG, KHÔNG PHẢI MỞ RỘNG CỦA 'quyet_toan_tour'

Hai tệp khác hẳn nhau về hình dạng, không phải khác về mức chi tiết:

    quyet_toan_tour           một tệp = CẢ THÁNG. Mỗi điều hành viên một sheet, mỗi dòng một chuyến,
                              chỉ có tổng doanh thu và tổng giá vốn.
    quyet_toan_tour_chi_tiet  một tệp = MỘT chuyến. Bốn sheet (QT, CTT, HDV CHI, DT), mỗi sheet một
                              mặt của chuyến ấy.

Nhét cả hai vào một bộ nạp thì bộ đọc phải đoán tệp đang cầm là loại nào, và đoán sai một lần là nạp
tổng tháng vào chỗ dành cho một chuyến. Hai cửa riêng thì người nạp chọn đúng cửa, và chọn sai thì bộ
kiểm nói ngay chứ không nạp nhầm.
"""
from app.services import quyet_toan_chi_tiet as QTCT

# Bộ nạp chạm thẳng vào tiền -> cửa tải tệp hẹp hơn cửa nhập tay đúng một bậc (quy tắc P4).
CHAM_TIEN = ("quyet_toan_tour_chi_tiet",)

PHONG_BAN = {"quyet_toan_tour_chi_tiet": "dieu_hanh"}


def bo_nap(_c) -> dict:
    return {
        "quyet_toan_tour_chi_tiet": {
            "bang_dich": "tour_settlement_lines",
            "phong_ban": "dieu_hanh",
            "lo": True,          # một tệp = một chuyến, kiểm và nạp cả tệp một lần
            "ten": "Quyết toán tour – chi tiết một chuyến (4 sheet)",
            "mo_ta": (
                "Tệp quyết toán của Điều hành cho MỘT chuyến, đúng bố cục đang dùng: sheet QT (từng "
                "khách), CTT (chiết tính, có đối tác – số hoá đơn – MST), HDV CHI (tiền ứng và chi "
                "trên tour), DT (doanh thu theo booking). Hệ thống đọc cả bốn sheet và ĐỐI CHIẾU "
                "chéo; chỗ nào các sheet nói khác nhau thì nói ra kèm số của từng nguồn, không tự "
                "chọn bên nào đúng."),
            "khoa_chong_trung": "Mã tour",
            # Bảng cột này để MÀN HÌNH hiển thị cho người nạp biết tệp cần có gì. Bộ đọc thật không
            # dùng nó – nó dò theo nhãn trong tệp, vì bố cục bốn sheet không phẳng thành cột được.
            "cot": [
                _c("ma_tour", "Mã tour", True, vi_du="NT001.03100726",
                   ghi_chu="ô 'Mã tour' ở đầu sheet QT – sáu số cuối cũng là ngày khởi hành"),
                _c("ten_chuong_trinh", "Tên tour", vi_du="NHA TRANG"),
                _c("ngay_di", "Ngày đi", kieu="ngay", vi_du="10/07/2026",
                   ghi_chu="đối chiếu với sáu số cuối của mã tour và với ô KHỞI HÀNH ở sheet CTT"),
                _c("ngay_ve", "Ngày về", kieu="ngay", vi_du="12/07/2026"),
                _c("so_khach", "Số khách", kieu="so", vi_du="42",
                   ghi_chu="đối chiếu với số dòng khách và với sheet CTT, DT"),
                _c("hdv", "Hướng dẫn viên", vi_du="MINH CHIẾN"),
                _c("bien_so_xe", "Biển số xe", vi_du="50H 938.27"),
                _c("doanh_thu", "Doanh thu", kieu="tien",
                   ghi_chu="máy tự cộng từ cột TỔNG THU của sheet QT – không gõ tay"),
            ],
            "kiem": QTCT.kiem_lo, "nap": QTCT.nap_lo,     # không dùng ở chế độ lô, khai cho đủ
            "kiem_lo": QTCT.kiem_lo, "nap_lo": QTCT.nap_lo, "doc_tep": QTCT.doc_tep_lo,
        },
    }


def vai_tro(QUAN_TRI: tuple) -> dict:
    """Ai nạp được. Đúng bằng bộ nạp quyết toán tháng – cùng một phòng sở hữu cùng một con số.

    Kế toán có trong danh sách vì họ là người đối chiếu tệp này với tờ khai thuế: sheet CTT mang số
    hoá đơn và MST nhà cung cấp, và đó là dữ liệu của Kế toán chứ không phải của Điều hành.
    """
    return {"quyet_toan_tour_chi_tiet": QUAN_TRI + ("tp_dh", "nv_dh", "ketoan", "ptgd_doan")}
