"""KS-4 · YÊU CẦU VÒNG ĐỜI CHO CẢNH BÁO — bản khai của Kiểm soát, phần dựng bảng là của VPM.

Đo được ngày 10/9/2026: 1.703 cảnh báo đang mở, 1.310 trong đó là ĐỎ. Hai nhóm lớn nhất:
851 chuyến quá hạn quyết toán (`qua_han_qt`) và 251 booking quá deadline thu (`qua_deadline_thu`).

Một nghìn bảy trăm việc đỏ không có ai đứng tên thì không phải một nghìn bảy trăm việc — nó là một
màn hình không ai mở. Bảng `alerts` hiện có đúng bảy cột: kind, level, ref, message, to_roles,
created_at, resolved. `to_roles` là một chuỗi vai trò, không phải một người; `resolved` là một ô
đúng/sai, không nói ai đóng, đóng lúc nào, dựa vào đâu. Không có hạn xử lý nên không đo được cái gì
đang trễ. Không có trạng thái đang-xử-lý nên hai người cùng làm một việc mà không ai biết.

Tệp này KHAI yêu cầu chứ không dựng bảng — dựng bảng là việc của lane Viết phần mềm. Phép thử
`test_ks4_vong_doi_canh_bao.py` đọc bản khai này và sẽ ĐỎ cho tới khi bảng có đủ. Đỏ ở đây là đúng:
nó là việc còn nợ đang được đếm, không phải phép thử hỏng.

Vì sao 851 chuyến quá hạn quyết toán không phải 851 vi phạm: phần lớn là chuyến LỊCH SỬ đổ từ
Vietrip sang, đã đóng từ trước khi VTOS chạy thật. `run_robots` quét mọi chuyến `ket_thuc` không giới
hạn mốc thời gian nào, nên mỗi chuyến cũ thành một dòng đỏ. Phân hệ Chăm sóc đã gặp đúng chuyện này
và đã có lời giải: tham số `cham_soc_lui_ngay` chặn việc mở phiếu cho toàn bộ lịch sử. Cảnh báo cần
một mốc tương tự, và cần một cột nói rõ dòng này sinh ra từ dữ liệu lịch sử hay từ vi phạm phát sinh
sau ngày vận hành thật — vì hai thứ ấy đi tới hai người khác nhau: một bên là việc dọn dữ liệu, một
bên là việc kỷ luật.
"""
from __future__ import annotations

# --------------------------------------------------------------- cột bảng alerts phải có thêm

COT_VONG_DOI: dict[str, str] = {
    "nguoi_nhan_id": (
        "Người CỤ THỂ chịu trách nhiệm dòng này, không phải danh sách vai trò. `to_roles` trả lời "
        "'ai được xem', không trả lời 'ai phải làm'. Việc gửi cho năm vai trò là việc không của ai."),
    "han_xu_ly": (
        "Mốc thời gian phải xong. Không có cột này thì câu 'cảnh báo đang trễ' không đo được, và cả "
        "1.310 dòng đỏ đứng ngang nhau dù có dòng mở từ tháng trước."),
    "trang_thai": (
        "Vòng đời thật: mới → đang xử lý → đã xử lý → đóng, kèm nhánh bỏ qua. Cột `resolved` đúng/sai "
        "gộp ba trạng thái khác nhau vào một ô nên hai người cùng làm một việc mà không ai biết."),
    "nhan_luc": "Lúc có người nhận. Chênh lệch với created_at là thời gian một việc đỏ nằm không.",
    "dong_luc": "Lúc đóng. Không có thì không đo được một việc mất bao lâu.",
    "dong_boi_id": "Ai đóng. `resolved=True` không nói ai bấm, nên không ai chịu trách nhiệm việc đóng ẩu.",
    "bang_chung": (
        "Bằng chứng đóng: số chứng từ, mã bản ghi, hoặc lý do viết ra. Đóng mà không cần nói dựa vào "
        "đâu thì nút đóng là nút giấu việc."),
    "nguon": (
        "'lich_su' hay 'phat_sinh'. Dữ liệu cũ đổ sang sinh cảnh báo là việc DỌN DỮ LIỆU; vi phạm sau "
        "ngày vận hành thật là việc KỶ LUẬT. Trộn hai thứ vào một danh sách là cách chắc chắn nhất để "
        "không xử lý được thứ nào."),
    "gom_khoa": (
        "Khoá gom trùng. Cùng một vấn đề sinh lại mỗi lượt quét thì phải cộng dồn vào một dòng, không "
        "đẻ dòng mới. Hiện mỗi nơi tự dò trùng theo (kind, ref) bằng tay, nơi nào quên là nơi ấy ngập."),
}

TRANG_THAI: dict[str, str] = {
    "moi": "vừa sinh, chưa ai nhận",
    "dang_xu_ly": "đã có người nhận",
    "da_xu_ly": "người nhận báo xong, chờ xác nhận",
    "dong": "đã xác nhận xong",
    "bo_qua": "quyết định không xử lý — phải có lý do, đây là nhánh cho dữ liệu lịch sử",
}

# Chuyển trạng thái hợp lệ. Không cho nhảy thẳng mới → đóng: đóng mà chưa ai nhận là đóng để cho
# sạch màn hình, đúng cái đang làm 1.703 dòng trở nên vô nghĩa.
CHUYEN: dict[str, tuple[str, ...]] = {
    "moi": ("dang_xu_ly", "bo_qua"),
    "dang_xu_ly": ("da_xu_ly", "bo_qua"),
    "da_xu_ly": ("dong", "dang_xu_ly"),
    "dong": (),
    "bo_qua": ("dang_xu_ly",),
}

# --------------------------------------------------------------- tham số Ban TGĐ phải chốt

THAM_SO_CAN: list[tuple[str, str, str]] = [
    ("ngay_van_hanh_that",
     "Ngày VTOS bắt đầu là sổ thật. Vi phạm trước ngày này là dữ liệu lịch sử, sinh cảnh báo thì "
     "phải gắn nguon='lich_su' và không tính vào chấm điểm ai cả.",
     "ngày (yyyy-mm-dd)"),
    ("canh_bao_lui_ngay",
     "Chỉ sinh cảnh báo cho sự kiện trong khoảng lùi này. Cùng cách đã dùng cho 'cham_soc_lui_ngay'. "
     "Không có mốc này thì mỗi lượt quét là một lượt quét lại toàn bộ lịch sử.",
     "ngày"),
    ("canh_bao_han_mac_dinh_gio",
     "Hạn xử lý mặc định cho loại cảnh báo chưa khai hạn riêng. Không có hạn thì không có gì trễ.",
     "giờ"),
]

# --------------------------------------------------------------- trần chống ngập

# Một lượt quét sinh quá số này dòng CÙNG MỘT LOẠI là dấu hiệu quét không có mốc thời gian, không
# phải dấu hiệu công ty vừa sai 851 lần trong một đêm.
TRAN_MOT_LOAI_MOT_LUOT = 50

# Loại được phép quét toàn lịch sử, kèm lý do. Giữ danh sách này NGẮN: mỗi dòng ở đây là một chỗ
# 1.703 dòng đỏ được phép quay lại. Lý do phải viết đủ dài để người duyệt phải nghĩ (≥ 60 ký tự).
QUET_TOAN_LICH_SU_DUOC_PHEP: dict[str, str] = {}

# --------------------------------------------------------------- chống trùng

# Nơi dựng Alert phải có cửa dò trùng trong cùng hàm. Khai ngoại lệ ở đây kèm lý do nếu một nơi cố ý
# sinh dòng mới mỗi lần (ví dụ nhật ký sự kiện một lần, không phải việc cần xử lý).
#
# Khoá là "đường/dẫn/tệp.py::tên_hàm", KHÔNG phải cả tệp: miễn trừ cả tệp thì hàm quét định kỳ nằm
# cùng tệp cũng được miễn theo, mà đó mới đúng là chỗ đẻ ra dòng hàng loạt.
KHONG_CAN_DO_TRUNG: dict[str, str] = {
    "app/services/zalo.py::_bao_hong": (
        "Token Zalo hỏng là sự kiện một lần cho một OA duy nhất (ref cố định 'zalo_oa'), không nhân "
        "theo số bản ghi nên không có đường ngập."),
    "app/services/su_co_tour.py::tao": (
        "Sinh đúng một cảnh báo cho đúng một sự cố vừa được người dùng khai, ref là mã sự cố nên "
        "không trùng được; đây là cửa NGƯỜI bấm chứ không phải lượt quét, không nhân theo số bản "
        "ghi. Hàm robot_su_co() trong cùng tệp vẫn dò trùng bình thường."),
}

MIN_LY_DO = 60
