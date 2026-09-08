"""P7 – vai trò có quyền nhưng chưa ai giữ, và cách quét quyền mà không cần tài khoản.

Chủ tịch duyệt phương án "tài khoản robot để thử là đủ". Bản này KHÔNG tạo tám tài khoản đăng nhập
được, và lý do phải viết ra để sau này không ai tưởng là quên:

Tạo tài khoản cho đủ bảng thì bảng trông đẹp còn khoảng trống quản lý vẫn nguyên – vai trò vẫn không
có ai làm việc. Đổi lại, hệ thống của một công ty đại chúng có thêm tám lối vào mà không ai dùng, tức
là không ai để ý khi có người dùng chúng.

Mà mục đích thật – "robot giữ vị trí từng phòng ban để thử quyền trên hệ thống thật" – không cần tài
khoản: cả hai lớp chặn đều là hàm thuần của chuỗi vai trò, nên dựng một User trong bộ nhớ rồi gọi
thẳng hàng rào là biết vai trò đó đi được tới đâu. Không lối vào mới, không mật khẩu phải cất giữ.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_p7.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p7.db", "test_p7.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, ROLES
from app.services import ks_robot as KS


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


def test_bao_ra_dung_nhung_vai_tro_chua_co_nguoi():
    """Đúng những vai trò CỦA NGƯỜI chưa có người – không kể ba vai trò máy.

    Từ 08/9/2026 (P8) có ba vai trò robot. Hỏi "vai trò này đã có ai chưa" với một vai trò máy là hỏi
    sai câu, và nếu để chúng trong danh sách này thì bộ dò kêu suốt đời về ba dòng không bao giờ xử lý
    được – cách nhanh nhất dạy người đọc bỏ qua cả danh sách. Việc của vai trò máy được hỏi bằng câu
    khác, ở _vai_tro_may_chua_co_tai_khoan."""
    from app.services import access as AC
    db = db_()
    co = {u.role for u in db.execute(select(User).where(User.active == True)).scalars()}   # noqa: E712
    thay = {x["vai_tro"] for x in KS._vai_tro_khong_co_nguoi(db)}
    assert thay == set(ROLES) - co - set(AC.VAI_TRO_MAY)
    assert not (thay & set(AC.VAI_TRO_MAY)), "vai trò máy lọt vào danh sách vai trò thiếu người"
    db.close()


def test_vai_tro_may_thieu_tai_khoan_thi_hoi_bang_cau_khac():
    """Vai trò người thiếu người là việc bố trí nhân sự. Vai trò máy thiếu tài khoản nghĩa là robot vẫn
    chạy dưới tên một con người, và nhật ký vẫn chưa phân biệt được ai làm gì – đúng vấn đề P8 giải."""
    from app.services import access as AC
    db = db_()
    ra = KS._vai_tro_may_chua_co_tai_khoan(db)
    thay = {x["vai_tro"] for x in ra}
    co_may = {u.role for u in db.execute(select(User).where(User.active == True)).scalars()   # noqa: E712
              if AC.la_vai_tro_may(u.role)}
    assert thay == set(AC.VAI_TRO_MAY) - co_may
    assert all(x["muc"] == "vang" for x in ra)
    assert all("nhật ký" in x["tom_tat"] or "không truy được" in x["tom_tat"] for x in ra)
    db.close()


def test_muc_vang_chu_khong_do():
    """Đây là việc bố trí người, không phải lỗ hổng bảo mật. Báo đỏ cho việc nhân sự thì lần sau không
    ai phân biệt được đâu là việc gấp."""
    db = db_()
    assert all(x["muc"] == "vang" for x in KS._vai_tro_khong_co_nguoi(db))
    db.close()


def test_quet_quyen_khong_tao_tai_khoan_nao():
    """Quét quyền từng vai trò mà không thêm một tài khoản nào vào hệ thống."""
    db = db_()
    truoc = len(db.execute(select(User)).scalars().all())
    KS._quyen_tung_vai_tro(db)
    assert len(db.execute(select(User)).scalars().all()) == truoc
    db.close()


def test_khong_vai_tro_nao_bi_chan_o_moi_duong_dan():
    """Vai trò bị hàng rào chặn ở mọi đường dẫn là vai trò đăng nhập vào và nhìn thấy hệ thống trống."""
    db = db_()
    assert KS._quyen_tung_vai_tro(db) == []
    db.close()


def test_bo_kiem_co_hai_bo_moi():
    ten = [f.__name__ for f in KS.BO_KIEM]
    assert "_vai_tro_khong_co_nguoi" in ten and "_quyen_tung_vai_tro" in ten
