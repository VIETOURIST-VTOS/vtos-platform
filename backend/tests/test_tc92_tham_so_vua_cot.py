"""TC-92 · THAM SỐ MẶC ĐỊNH PHẢI VỪA CỘT THẬT — 28/9/2026, sau một lần máy chủ chết câm.

CHUYỆN ĐÃ XẢY RA, ghi lại vì nó là loại lỗi bộ thử xanh không nói gì được:

`khao_sat_mau_tin` thêm ở TC-90 dài 210 ký tự, cột `Param.value` là String(200). Trên SQLite —
nơi mọi phép thử chạy — độ dài VARCHAR chỉ là LỜI KHAI, không ép. Trên PostgreSQL ở Render nó ép
thật. Kết quả: `seed_params` ném StringDataRightTruncation NGAY TRONG lifespan, uvicorn thoát với
mã 3, và Render giữ bản cũ chạy tiếp.

Nên HAI vòng liên tiếp (TC-86→90 và TC-91) hiện "Deployed" mà thật ra chưa bao giờ khởi động nổi.
Không màn hình nào đỏ, không cảnh báo nào kêu — máy chủ cũ vẫn trả 200 cho mọi cửa cũ. Thứ duy
nhất nhìn thấy được là một cửa MỚI trả 404, mà phải biết trước là nó phải có thì mới nghĩ tới việc
gọi thử.

PHÉP THỬ NÀY ĐỌC ĐỘ DÀI CỘT TỪ CHÍNH MÔ HÌNH, không viết cứng số 200. Nới cột thì trần tự nới
theo; thêm cột mới cũng tự được canh. Viết cứng 200 là dựng một bản sao thứ hai của một sự thật
đã có chỗ ở.
"""
import pytest
from sqlalchemy import String

from app.models.core import Param
from app.services.rules import DEFAULT_PARAMS


def _tran(ten_cot: str) -> int:
    """Độ dài tối đa của một cột, đọc thẳng từ mô hình."""
    kieu = Param.__table__.columns[ten_cot].type
    assert isinstance(kieu, String) and kieu.length, f"cột {ten_cot} không có trần độ dài"
    return kieu.length


@pytest.mark.parametrize("cot,vi_tri", [("value", 1), ("label", 2), ("unit", 3), ("source", 4)])
def test_tham_so_khong_vuot_do_dai_cot(cot, vi_tri):
    tran = _tran(cot)
    qua = [(r[0], len(str(r[vi_tri])))
           for r in DEFAULT_PARAMS if vi_tri < len(r) and len(str(r[vi_tri])) > tran]
    assert not qua, (
        f"{len(qua)} tham số có `{cot}` dài quá trần {tran} của cột — PostgreSQL sẽ từ chối và "
        f"máy chủ chết ngay lúc khởi động, trong khi SQLite của bộ thử im lặng cho qua: {qua}")


def test_khoa_tham_so_khong_vuot_cot_key():
    tran = _tran("key")
    qua = [(r[0], len(r[0])) for r in DEFAULT_PARAMS if len(r[0]) > tran]
    assert not qua, f"khóa dài quá trần {tran}: {qua}"


def test_phep_thu_nay_that_su_no():
    """Tự kiểm: nhét một giá trị quá dài vào và đòi luật ở trên bắt được.

    Một hàng rào không bao giờ đỏ thì không phải hàng rào. Phép thử ở trên chỉ đọc danh sách tĩnh,
    nên rất dễ thành ra luôn xanh nếu ai đó lỡ sửa `_tran` trả về một số khổng lồ.
    """
    tran = _tran("value")
    gia = [("x", "a" * (tran + 1), "nhãn", "đơn vị", "nguồn")]
    qua = [(r[0], len(str(r[1]))) for r in gia if len(str(r[1])) > tran]
    assert qua, "luật độ dài không bắt được cả một giá trị dài hơn trần — hàng rào hỏng"
