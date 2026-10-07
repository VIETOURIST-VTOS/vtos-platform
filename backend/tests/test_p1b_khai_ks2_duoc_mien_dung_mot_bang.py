"""P1b – P1 đọc bảng khai KS-2, và CHỈ đọc đúng một bảng trong sáu.

VIỆC NÀY SINH RA TỪ MỘT LẦN main ĐỎ. Đo 07/10/2026 trên `git archive origin/main` ra một cây sạch:
`test_p1_mot_kieu_khai_quyen.py::test_khong_endpoint_nao_con_phai_doc_ma_nguon` đỏ với đúng một cửa —
`POST /api/v1/guide-assignments/de-xuat/{did}/quyet`. Cửa ấy KHÔNG hở: nó chặn theo DỮ LIỆU (bước
đang chờ cần vai nào) và đã khai đàng hoàng vào bảng KS-2 theo đúng lệnh Chủ tịch ngày 07/10. Hai
hàng rào cùng canh một việc mà đọc hai nguồn khác nhau: KS-2 đọc bảng khai, P1 thì chưa biết bảng
ấy có tồn tại. Hậu quả không nằm ở một dòng đỏ: main đỏ thì MỌI làn đỏ theo và không gì gộp được.

CHỖ DỄ SỬA SAI NHẤT, và vì sao bản này không sửa theo lối ấy: lý do P1 nhặt được cửa này là vì
THÂN HÀM có chuỗi `require_roles` — trong một câu GIẢI THÍCH ở docstring, không phải trong mã chạy.
Nên lối sửa rẻ nhất là bảo `_doc_ma_nguon` bỏ qua docstring. Lối ấy SAI: cửa ấy thật sự có gọi
`HDV.kiem_nguoi_quyet` trong thân hàm, tức đúng loại việc P1 sinh ra để nhìn thấy. Bỏ qua docstring
chỉ làm P1 thôi nhìn thấy nó — im lặng chứ không phải đúng. Bản này cho P1 miễn cửa ấy vì nó ĐÃ
KHAI, và lời khai ấy có người kiểm lại (Q2 của KS-2 mở đúng hàm dịch vụ được nêu tên ra đọc).

Bốn phép thử dưới đây khoá lại chỗ dễ trôi nhất của cách sửa này: cái miễn trừ phình ra.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_p1b_khai.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_p1b_khai.db", "test_p1b_khai.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

from fastapi import APIRouter, Depends, FastAPI  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.deps import current_user, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.core import User  # noqa: E402
from app.services import ks_robot as KS  # noqa: E402
from tools import ks2_khai_quyen as K  # noqa: E402

CUA = "POST /api/v1/guide-assignments/de-xuat/{did}/quyet"


def _require(u: User) -> None:
    """Chặn vai trò trong thân hàm – chỉ dùng cho cửa giả của phép thử p1b3, không nằm trong kho."""
    if u.role not in ("chutich",):
        raise RuntimeError("403")


def test_p1b1_cua_da_khai_o_bang_khong_con_bi_bao_va_danh_sach_rong():
    """Trạng thái phải có: P1 xanh trên chính kho này, và xanh VÌ cửa kia đã khai — không phải vì
    lời báo bị tắt đi. Hai điều kiểm cùng lúc nên không thể xanh nhầm."""
    assert CUA in K.CHAN_TANG_DICH_VU, (
        "Cửa quyết định của bước duyệt HDV phải có tên trong bảng CHAN_TANG_DICH_VU — Chủ tịch "
        "quyết 07/10/2026. Gỡ dòng khai ấy ra thì phải dựng chặn ở chữ ký, không phải để trống.")
    assert KS.endpoint_phai_doc_ma_nguon(app) == []


def test_p1b2_go_dong_khai_di_thi_P1_do_lai_ngay():
    """Phép thử QUAN TRỌNG NHẤT của tệp này. Miễn trừ phải đến TỪ LỜI KHAI, không phải từ việc P1
    đã thôi nhìn. Gỡ đúng một dòng khai ra khỏi bảng thì cửa ấy phải hiện lại trong danh sách đỏ.

    Không có phép thử này thì một bản sửa làm P1 mù hẳn cũng xanh y như bản sửa đúng.
    """
    goc = dict(K.CHAN_TANG_DICH_VU)
    try:
        K.CHAN_TANG_DICH_VU.pop(CUA)
        con = KS.endpoint_phai_doc_ma_nguon(app)
        assert any("guide-assignments/de-xuat" in c and "quyet" in c for c in con), (
            f"Gỡ dòng khai mà P1 vẫn xanh — nghĩa là P1 đang mù, không phải đang đọc bảng. {con}")
    finally:
        K.CHAN_TANG_DICH_VU.clear()
        K.CHAN_TANG_DICH_VU.update(goc)
    assert KS.endpoint_phai_doc_ma_nguon(app) == []


def test_p1b3_khai_o_bang_KHAC_thi_khong_duoc_mien():
    """Năm bảng kia KHÔNG miễn, và `CHAN_TAI_CHO` là bảng phải canh kỹ nhất: chính nó nói rằng chặn
    nằm NGAY TRONG THÂN HÀM — tức đúng cái P1 sinh ra để nhìn thấy. Mở cả sáu bảng là tắt P1 bằng
    một dòng mà vẫn xanh.

    Dựng một ứng dụng con riêng chứ không đụng vào `app` thật: thêm một cửa hở vào kho chỉ để chạy
    phép thử là để lại một cửa hở thật nếu có ngày ai quên xoá.
    """
    phu = FastAPI()
    r = APIRouter(prefix="/api/v1")

    @r.post("/thu-nghiem-p1b/chan-tai-cho")
    def _chan_tai_cho(u: User = Depends(current_user), db: Session = Depends(get_db)):
        # `_require(` là một trong những dấu hiệu mà `ks_robot.CHAN_TRONG_THAN` nhận ra: chặn nằm
        # trong THÂN HÀM chứ không ở chữ ký — đúng loại cửa P1 sinh ra để nhìn thấy.
        _require(u)
        return {"ok": True}

    phu.include_router(r)
    khoa = "POST /api/v1/thu-nghiem-p1b/chan-tai-cho"
    assert any("thu-nghiem-p1b" in c for c in KS.endpoint_phai_doc_ma_nguon(phu)), (
        "Cửa chặn trong thân hàm mà chưa khai gì thì phải bị bắt — đây là mốc so sánh của phép thử.")

    goc = dict(K.CHAN_TAI_CHO)
    try:
        K.CHAN_TAI_CHO[khoa] = "thu_nghiem:chan_tai_cho"
        con = KS.endpoint_phai_doc_ma_nguon(phu)
        assert any("thu-nghiem-p1b" in c for c in con), (
            "Khai ở CHAN_TAI_CHO mà được miễn — miễn trừ đã phình sang bảng không ai kiểm lại lời "
            f"khai. Chỉ CHAN_TANG_DICH_VU được miễn. {con}")
    finally:
        K.CHAN_TAI_CHO.clear()
        K.CHAN_TAI_CHO.update(goc)


def test_p1b4_doc_bang_hong_thi_nghiem_hon_chu_khong_long_hon():
    """Nhánh hỏng phải nghiêng về phía BÁO THỪA. Một hàng rào mà lúc hỏng thì im lặng mở cửa là
    hàng rào tệ hơn không có, vì nó còn làm người ta yên tâm."""
    import builtins
    that = builtins.__import__

    def gay(ten, *a, **k):
        if ten.startswith("tools.ks2_khai_quyen") or ten == "tools":
            raise ImportError("thử: không đọc được bảng khai")
        return that(ten, *a, **k)

    builtins.__import__ = gay
    try:
        assert KS._khai_chan_tang_dich_vu() == set(), (
            "Đọc bảng hỏng mà vẫn trả về một tập miễn trừ — nghĩa là có một nguồn thứ hai nào đó "
            "đang lặng lẽ mở cửa.")
        con = KS.endpoint_phai_doc_ma_nguon(app)
        assert any("guide-assignments/de-xuat" in c and "quyet" in c for c in con)
    finally:
        builtins.__import__ = that
    assert KS.endpoint_phai_doc_ma_nguon(app) == []
