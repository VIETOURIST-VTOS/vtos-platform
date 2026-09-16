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
from datetime import date

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


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# TC-46 · "ĐANG BÁN" VÀ "ĐANG CHẠY" LÀ HAI CÂU HỎI KHÁC NHAU — anh Tuấn chốt 16/9/2026
# ═══════════════════════════════════════════════════════════════════════════════════════════════
# Bản vẽ v3.0 thêm thẻ "Tour đang chạy". Dựng nó làm lộ ra một điều mà chín vòng trước không ai
# phải đối mặt: HỆ THỐNG KHÔNG CÓ TRẠNG THÁI "ĐANG CHẠY". Một chuyến được duyệt xong mang trạng
# thái `da_duyet` và giữ nguyên trạng thái ấy suốt từ lúc mở bán, qua cả hành trình, tới khi Điều
# hành bấm kết thúc. Nên "đang bán" của bản cũ thật ra là "đã duyệt", gồm cả những đoàn đang trên
# đường.
#
# Anh Tuấn chọn TÁCH HẲN, và chấp nhận hệ quả: con số "Tour đang bán" trên màn hình sẽ NHỎ ĐI so
# với hôm qua. Ghi ra đây để vòng sau đọc bản lưu cũ không tưởng là mất số.
#
#   · đang bán   = đã duyệt, CHƯA tới ngày khởi hành
#   · đang chạy  = đã duyệt, đã khởi hành và chưa qua ngày về
#   · đã về chưa đóng sổ = đã duyệt, ĐÃ QUA ngày về mà trạng thái vẫn là đã duyệt
#
# NHÓM THỨ BA KHÔNG PHẢI PHẦN DƯ CHO ĐỦ PHÉP CỘNG. Nó là một việc tồn: chuyến đã về mà Điều hành
# chưa bấm kết thúc thì tiền của chuyến ấy chưa vào hàng đợi quyết toán, và không màn hình nào
# hiện nó ra. Bỏ nó đi thì hai con số đầu cộng lại không bằng tổng đã duyệt, và chỗ chênh ấy biến
# mất lặng lẽ — đúng kiểu sai mà không ai kiểm được. Nên nó có tên, có chỗ hiện, có bộ phận.
#
# LẤY NGÀY THEO VÉ, KHÔNG THEO TRẠNG THÁI, nên hàm này cần `hom_nay` truyền vào chứ không tự đọc
# đồng hồ: cùng một luật với `lich_chup` và `ket_qua_kinh_doanh` — mọi phép tính theo ngày đều phải
# thử được ở một ngày bất kỳ.

GIAI_DOAN = ("dang_ban", "dang_chay", "da_ve_chua_dong_so")


def theo_giai_doan(db: Session, hom_nay: date) -> dict[str, int]:
    """Chia các chuyến ĐÃ DUYỆT theo vị trí của chúng so với hôm nay.

    Ba nhóm không trùng nhau và phủ kín, nên cộng cả ba ra đúng `dang_ban()` của bản cũ.
    """
    q = select(Tour.start_date, Tour.end_date).where(Tour.status.in_(DANG_BAN))
    ra = {k: 0 for k in GIAI_DOAN}
    for bat_dau, ket_thuc in db.execute(q).all():
        if bat_dau is not None and bat_dau > hom_nay:
            ra["dang_ban"] += 1
        elif ket_thuc is not None and ket_thuc < hom_nay:
            ra["da_ve_chua_dong_so"] += 1
        else:
            # Gồm cả chuyến thiếu ngày: một chuyến đã duyệt mà không có ngày đi hay ngày về thì
            # không thể nói nó chưa khởi hành hay đã về. Xếp vào "đang chạy" là chỗ ít sai nhất —
            # nó vẫn nằm trong tổng, vẫn có người phải nhìn, và không bị dán nhãn "đã về".
            ra["dang_chay"] += 1
    return ra
