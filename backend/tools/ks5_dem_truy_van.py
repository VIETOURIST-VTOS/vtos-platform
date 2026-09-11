"""KS-5 · Đếm SỐ LƯỢT TRUY VẤN của một thao tác, không đo thời gian.

Vì sao đếm lượt chứ không bấm giờ: thời gian phụ thuộc máy, phụ thuộc lúc đo, phụ thuộc cả việc máy
chủ có đang bận hay không — nên nó không nói được đúng/sai, chỉ nói nhanh/chậm hôm nay. Số lượt truy
vấn thì nói được đúng/sai: một thao tác đọc danh sách mà số lượt tăng theo số bản ghi thì trong đó
CÓ truy vấn nằm trong vòng lặp, và điều đó đúng ở mọi máy, mọi lúc.

Ngày 10/9/2026 màn hình Khoản treo mất 55 giây mới mở. Nguyên nhân là đệm tham số tra lại theo từng
dòng. Bấm giờ chỉ nói "chậm"; đếm lượt nói thẳng "số lượt tăng theo số dòng" và chỉ đúng chỗ.

Hai quy tắc KS-5 canh:

  (1) Số lượt truy vấn của một thao tác KHÔNG được tăng theo số bản ghi.
  (2) Mọi phép đọc danh sách phải có TRẦN, và chạm trần thì PHẢI NÓI RA.

Quy tắc (2) quan trọng ngang (1) và hay bị quên hơn. Một danh sách âm thầm cắt ở 300 dòng còn nguy
hiểm hơn một danh sách chậm: người đọc tin rằng mình đang nhìn toàn bộ, và ra quyết định trên phần
bị cắt mà không biết. Cắt thì được, im lặng thì không.
"""
from __future__ import annotations

import contextlib


@contextlib.contextmanager
def dem_truy_van(engine=None):
    """Đếm số câu lệnh SQL chạy trong khối lệnh. Dùng: `with dem_truy_van() as d: ...` rồi đọc d["n"].

    Bắt ở tầng engine của SQLAlchemy nên đếm được cả truy vấn do quan hệ lười (lazy) sinh ra — đó
    chính là loại truy vấn nằm trong vòng lặp mà đọc mã không thấy.
    """
    from sqlalchemy import event

    if engine is None:
        from app.db.session import engine as e_mac_dinh
        engine = e_mac_dinh

    so = {"n": 0, "cau": []}

    def _ghi(conn, cursor, statement, parameters, context, executemany):
        so["n"] += 1
        if len(so["cau"]) < 400:
            so["cau"].append(" ".join(str(statement).split())[:160])

    event.listen(engine, "before_cursor_execute", _ghi)
    try:
        yield so
    finally:
        event.remove(engine, "before_cursor_execute", _ghi)


def nhom_cau(so: dict) -> dict[str, int]:
    """{câu lệnh: số lần} — câu nào lặp nhiều lần gần như luôn là câu nằm trong vòng lặp."""
    d: dict[str, int] = {}
    for c in so["cau"]:
        d[c] = d.get(c, 0) + 1
    return dict(sorted(d.items(), key=lambda x: -x[1]))


# --------------------------------------------------------------------------- trần đọc danh sách

# Đường dẫn đọc danh sách và TRẦN đã khai. None nghĩa là CHƯA CÓ TRẦN — đó là việc còn nợ, không
# phải lựa chọn thiết kế. Khi thêm trần thì phải kèm cách nói ra lúc chạm trần (xem KHOA_NOI_RA).
TRAN_DANH_SACH: dict[str, int | None] = {
    "GET /api/v1/alerts": 200,
    "GET /api/v1/tours": 300,
}

# Khoá mà phản hồi phải mang khi bị cắt, để giao diện nói cho người đọc biết họ đang nhìn phần cắt.
KHOA_NOI_RA = ("cham_tran", "con_nua", "tong")

LY_DO_CHUA_CO_TRAN: dict[str, str] = {}

# Trần đã thêm — giữ lại lời khai cũ để còn truy được vì sao từng thiếu và cái gì đã bù. Bảng này
# KHÔNG được bộ kiểm đọc: một cửa chỉ rời LY_DO_CHUA_CO_TRAN khi TRAN_DANH_SACH có số thật, và số ấy
# chính bộ kiểm T4/T5 đo lại trên phản hồi chứ không tin lời khai.
DA_CO_TRAN: dict[str, str] = {
    "GET /api/v1/alerts": (
        "Mở 10/9/2026 bởi KS-5: đọc TOÀN BỘ bảng alerts – 1.703 dòng đang mở – rồi mới lọc theo vai "
        "trò bằng Python; không trần, không phân trang. "
        "ĐÓNG 11/9/2026: trần 200 dòng một trang (trần cứng 500), có offset, và phản hồi mang `tong` "
        "nên giao diện biết mình đang nhìn phần cắt. Trần đặt SAU bộ lọc vai trò, không phải trước – "
        "cắt trước khi lọc thì người chỉ thấy cảnh báo của mình có thể nhận một trang rỗng trong khi "
        "việc của họ nằm ở dòng thứ 400. Lọc trang_thai/nguon/cua_toi đẩy xuống câu truy vấn (KS-4)."),
}

# Số lượt truy vấn tối đa cho một lần gọi đọc danh sách. Vượt trần gần như luôn là truy vấn trong
# vòng lặp. Để rộng rãi có chủ đích: mục đích là bắt N+1, không phải ép tối ưu từng câu.
TRAN_LUOT_DOC_DANH_SACH = 40
