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
from app.services import nap_mau_quyet_toan as NMQT

# Bộ nạp chạm thẳng vào tiền -> cửa tải tệp hẹp hơn cửa nhập tay đúng một bậc (quy tắc P4).
CHAM_TIEN = ("quyet_toan_tour_chi_tiet", "mau_quyet_toan_tour")

PHONG_BAN = {"quyet_toan_tour_chi_tiet": "dieu_hanh", "mau_quyet_toan_tour": "dieu_hanh"}


def bo_nap(_c) -> dict:
    return {
        "quyet_toan_tour_chi_tiet": {
            "bang_dich": "tour_settlement_lines",
            # Một tệp quyết toán đổ vào NĂM bảng, không phải một. bang_dich giữ bảng chính (để màn
            # hình và nhật ký nạp gọi tên được), bang_phu liệt kê phần còn lại.
            #
            # Khai đủ ở đây không phải để cho đẹp: phép kiểm "mọi bảng phải có một cửa" (ks_cua_nhap)
            # đọc sống từ chỗ này. Thiếu khai thì bốn bảng kia bị báo là KHÔNG CÓ CỬA NHẬP, trong khi
            # chúng có – và người đọc báo cáo sẽ đi dựng một cửa thứ hai cho thứ đã có cửa.
            "bang_phu": ("tour_settlement_costs", "tour_settlement_cost_lines",
                         "tour_guide_advances", "tour_settlement_bookings"),
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
        # ---------------------------------------------------------------------------------------
        "mau_quyet_toan_tour": {
            "bang_dich": "tour_cost_lines",
            # Một tệp mẫu đổ vào SÁU bảng. bang_dich giữ bảng chính; bang_phu liệt kê phần còn lại,
            # để phép kiểm "mọi bảng phải có một cửa" (ks_cua_nhap) đọc sống từ chỗ này.
            "bang_phu": ("booking_khach", "khach_chi_phi", "tour_doanh_thu_dong",
                         "tour_phuong_tien", "tour_hdv_chi"),
            "phong_ban": "dieu_hanh",
            "lo": True,          # một tệp = một chuyến, kiểm và nạp cả tệp một lần
            "ten": "Quyết toán tour – MẪU CHUẨN VTOS (trong nước / nước ngoài)",
            "mo_ta": (
                "Tệp do CHÍNH VTOS phát ra: MAU_QT_TOUR_TRONG_NUOC.xlsx hoặc "
                "MAU_QT_TOUR_NUOC_NGOAI.xlsx, đã điền xong. Nhân viên Điều hành tải mẫu trống, điền "
                "vào ô nền vàng, rồi tải lên đây.\n\n"
                "Hệ thống KHÔNG đọc ô tổng của tệp – nó cộng lại từ các dòng. Trên tệp mẫu thật của "
                "Điều hành, ô tổng một nhóm chi ghi 3.990.000 trong khi năm dòng của chính nhóm ấy "
                "cộng lại được 4.200.000; con số sai ấy đi thẳng vào giá vốn mà mọi tầng vẫn cân.\n\n"
                "Chín phép kiểm trong tệp là để người lập tờ tự sửa trước khi gửi. Hệ thống chạy lại "
                "toàn bộ ở máy chủ, vì một tệp đã gửi đi là tệp đã ra khỏi tầm kiểm soát: ô công "
                "thức xoá được, sheet ĐỐI CHIẾU xoá được.\n\n"
                "NẠP LẠI LÀ THAY, KHÔNG CỘNG THÊM: nạp cùng một chuyến lần thứ hai thì phần cũ bị "
                "thay, không sinh ra hai lần giá vốn."),
            "khoa_chong_trung": "Mã tour (ở sheet THÔNG TIN)",
            # MẪU TRỐNG DO PHẦN MỀM PHÁT, KHÔNG PHẢI TỆP CHUYỀN TAY QUA ZALO
            #
            # Sheet KHOẢN MỤC trong mẫu là bản sao danh mục của hệ thống, và ô chọn mã ở mọi dòng chi
            # trỏ vào sheet ấy. Một tệp tải về từ tháng trước lệch danh mục một bước là người điền
            # chọn đúng ô mẫu đưa cho rồi bị bộ nạp từ chối vì "mã không có trong danh mục".
            #
            # Khai ở đây để màn hình Nạp dữ liệu dựng đúng hai nút này thay cho nút "tải CSV mẫu"
            # chung – CSV phẳng tám cột không phải hình dạng của tệp này.
            "mau_rieng": (
                {"ten": "Mẫu tour TRONG NƯỚC",
                 "duong_dan": "/api/v1/quyet-toan-lop3/mau-trong?hinh_thuc=trong_nuoc"},
                {"ten": "Mẫu tour NƯỚC NGOÀI",
                 "duong_dan": "/api/v1/quyet-toan-lop3/mau-trong?hinh_thuc=nuoc_ngoai"},
            ),
            # Bảng cột này để MÀN HÌNH hiển thị cho người nạp biết tệp cần có gì, và nó khai bằng
            # _c() như mọi bộ nạp khác chứ không phải một hình dạng dict riêng: khung nhập đọc sống
            # từ chỗ này (kiểu cột, cột bắt buộc, ví dụ), và một bộ nạp khai lệch hình thì màn hình
            # dựng thiếu, còn phép kiểm khung (khai_bao_du) không bắt được vì nó tra đúng những khoá
            # mà bản khai lệch ấy không có.
            #
            # Bộ đọc THẬT không dùng bảng này – nó dò theo nhãn trong tệp, vì bố cục mười sheet không
            # phẳng thành cột được. Cùng lý do đã ghi ở bộ nạp quyết toán chi tiết phía trên.
            "cot": [
                _c("ma_tour", "Mã tour", True, vi_du="NT001.03100726",
                   ghi_chu="Ở sheet THÔNG TIN. Chuyến phải ĐÃ CÓ trong hệ thống."),
                _c("ten_tour", "Tên tour", vi_du="NHA TRANG 3N2Đ"),
                _c("hinh_thuc", "Hình thức", kieu="chon",
                   chon={"trong_nuoc": "Tour trong nước", "nuoc_ngoai": "Tour nước ngoài"},
                   vi_du="trong_nuoc",
                   ghi_chu="Phải khớp với chuyến trong hệ thống – và quyết định dùng mẫu nào."),
                _c("so_khach", "Số dòng khách", kieu="so", vi_du="42",
                   ghi_chu="máy đếm từ sheet KHÁCH – không gõ tay"),
                _c("ngay_kh", "Ngày khởi hành", kieu="ngay", vi_du="10/07/2026"),
                _c("ngay_kt", "Ngày kết thúc", kieu="ngay", vi_du="12/07/2026"),
                _c("dieu_hanh", "Điều hành", vi_du="MINH CHIẾN"),
                _c("doanh_thu", "Tổng thu (máy cộng lại)", kieu="tien", vi_du="285.600.000",
                   ghi_chu="máy cộng từ sheet THU – không đọc ô tổng của tệp"),
            ],
            # Chế độ LÔ chỉ gọi kiem_lo / nap_lo / doc_tep. Vẫn khai kiem/nap cho đủ khung ba cửa:
            # khai_bao_du() tra đúng hai khoá này, và thiếu chúng thì bộ nạp bị báo là khai thiếu.
            "kiem": NMQT.kiem_lo, "nap": NMQT.nap_lo,
            "kiem_lo": NMQT.kiem_lo, "nap_lo": NMQT.nap_lo, "doc_tep": NMQT.doc_tep_lo,
        },
    }


def vai_tro(QUAN_TRI: tuple) -> dict:
    """Ai nạp được. Đúng bằng bộ nạp quyết toán tháng – cùng một phòng sở hữu cùng một con số.

    Kế toán có trong danh sách vì họ là người đối chiếu tệp này với tờ khai thuế: sheet CTT mang số
    hoá đơn và MST nhà cung cấp, và đó là dữ liệu của Kế toán chứ không phải của Điều hành.
    """
    ai = QUAN_TRI + ("tp_dh", "nv_dh", "ketoan", "ptgd_doan")
    # Khai cho CẢ HAI bộ nạp. Không khai thì khung rơi về mặc định QUAN_TRI, tức là chính nhân viên
    # Điều hành – người lập tờ quyết toán – lại không nạp được tờ của mình, và họ sẽ gửi tệp cho
    # người có quyền nạp hộ. Nhật ký khi ấy ghi sai tên người chịu trách nhiệm về con số.
    #
    # CHAM_TIEN ở đầu tệp vẫn hẹp cửa TẢI TỆP thêm một bậc so với cửa nhập tay (quy tắc P4): nv_dh
    # gõ tay được, nhưng tải nguyên một tệp đổ vào sáu bảng thì phải là trưởng phòng trở lên.
    return {"quyet_toan_tour_chi_tiet": ai, "mau_quyet_toan_tour": ai}
