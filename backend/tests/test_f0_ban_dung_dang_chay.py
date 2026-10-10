"""Đợt F0 — `/health` phải nói ra bản dựng đang chạy, và nói THẬT khi không biết.

Ngày 09/10/2026 một câu phải rút lại vì không ai biết bản trên Render là commit nào. Tệp này
canh để chuyện ấy không lặp lại trong im lặng.
"""
import importlib
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_f0.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_f0.db", "test_f0.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

from app.api.v1 import routes as R        # noqa: E402


def test_a_cua_health_tra_ve_khoa_commit():
    d = R.health()
    assert "commit" in d, (
        "`/health` phai co khoa `commit`. Thieu no thi khong ai chung minh duoc ban dang chay "
        "la commit nao, va moi cau ve he thong dang chay deu la suy doan.")
    assert "status" in d and "time" in d, "Hai khoa cu phai con nguyen"


def test_b_rong_khi_khong_co_bien_chu_khong_bia():
    """RONG la mot cau tra loi that: khong biet. Bia mot gia tri con te hon de trong."""
    for b in ("RENDER_GIT_COMMIT", "GIT_COMMIT", "SOURCE_VERSION"):
        os.environ.pop(b, None)
    importlib.reload(R)
    assert R.BAN_DUNG_DANG_CHAY == "", (
        f"Khong co bien moi truong thi phai RONG, dang la {R.BAN_DUNG_DANG_CHAY!r}")


def test_c_doc_duoc_bien_cua_render():
    os.environ["RENDER_GIT_COMMIT"] = "0779e79abc"
    importlib.reload(R)
    try:
        assert R.BAN_DUNG_DANG_CHAY == "0779e79abc"
        assert R.health()["commit"] == "0779e79abc"
    finally:
        os.environ.pop("RENDER_GIT_COMMIT", None)
        importlib.reload(R)


def test_d_cua_health_khong_nhan_db():
    """Luat cu cua cua nay phai con nguyen: khong cham co so du lieu.

    Doc mot bien moi truong luc nap mo-dun khong pha luat ay - va phep thu nay la cho ghi lai
    rang no khong duoc pha.
    """
    import inspect
    assert list(inspect.signature(R.health).parameters) == [], (
        "`/health` khong duoc nhan tham so nao - nhat la `db`. Doc ly do trong chu thich ham.")
