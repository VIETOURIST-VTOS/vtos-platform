# -*- coding: utf-8 -*-
"""Đếm tour theo trạng thái — MỘT chỗ duy nhất định nghĩa "đang bán" và "chờ quyết toán".

VÌ SAO TÁCH RA THÀNH MỘT TỆP RIÊNG
══════════════════════════════════════════════════════════════════════════════════════════════
Hai con số này xuất hiện ở ba nơi trên cùng một màn hình: thẻ chỉ tiêu ở đầu trang, biểu đồ xu
hướng ở khu 2, và bản lưu cuối kỳ. Nếu mỗi nơi tự viết `status == "da_duyet"` thì đến lúc quy
trình đổi tên một trạng thái, ba nơi sẽ đổi vào ba thời điểm khác nhau — và trong khoảng giữa,
màn hình hiện ba con số khác nhau cho cùng một câu hỏi mà không chỗ nào báo lỗi.

MÓN NỢ CÒN LẠI, ghi ra để nó không thành món nợ vô hình
══════════════════════════════════════════════════════════════════════════════════════════════
`api/v1/routes.py` vẫn tự gom nhóm `select(Tour.status, func.count()).group_by(Tour.status)` để
dựng `counts` cho bảng điều khiển. Đó là CÙNG một phép đếm với hàm dưới đây. Vòng này chưa sửa
tệp ấy vì nó là tệp trung tâm của toàn bộ API và bản checkout ở đây không đủ để chạy thử nó;
lần nào chạm vào routes.py tiếp theo thì đổi chỗ ấy sang gọi `theo_trang_thai()`.

ĐÂY LÀ SỐ TẠI MỘT THỜI ĐIỂM, KHÔNG PHẢI SỐ TRONG KỲ
══════════════════════════════════════════════════════════════════════════════════════════════
`Tour.status` chỉ giữ trạng thái HIỆN TẠI — không có lịch sử. Nên "cuối tháng 8 có bao nhiêu tour
đang bán" là câu hỏi mà hôm nay KHÔNG tính lại được: tour đã quyết toán xong rồi thì không còn dấu
vết nó từng nằm chờ. Đó là lý do phải chụp bản lưu đúng lúc, và là lý do `xu_huong` từ chối những
bản lưu chụp muộn thay vì im lặng dùng chúng.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Tour

# Trạng thái nào là "đang bán", trạng thái nào là "chờ quyết toán" — khai một lần, ở đây.
#
# "Chờ quyết toán" gồm HAI trạng thái chứ không phải một: `ket_thuc` là chuyến đã đi xong mà chưa
# đóng sổ, `da_dong_so` là đã đóng sổ mà Kế toán chưa xác nhận. Cả hai đều là tiền chưa chốt được,
# nên Chủ tịch đọc chúng như một việc. Tách đôi ở màn hình thì hai con số nhỏ thay cho một con số
# thật, và không ai cộng nhẩm trong đầu khi đọc bảng điều hành.
DANG_BAN = ("da_duyet",)
CHO_QUYET_TOAN = ("ket_thuc", "da_dong_so")


def theo_trang_thai(db: Session) -> dict[str, int]:
    """{trạng thái: số tour}. Trạng thái không có tour nào thì KHÔNG có mặt trong kết quả."""
    return {st: n for st, n in db.execute(
        select(Tour.status, func.count()).group_by(Tour.status)).all()}


def _cong(dem: dict[str, int], cac_trang_thai) -> int:
    return sum(dem.get(st, 0) for st in cac_trang_thai)


def dang_ban(db: Session, dem: dict[str, int] | None = None) -> int:
    return _cong(dem if dem is not None else theo_trang_thai(db), DANG_BAN)


def cho_quyet_toan(db: Session, dem: dict[str, int] | None = None) -> int:
    return _cong(dem if dem is not None else theo_trang_thai(db), CHO_QUYET_TOAN)
