# -*- coding: utf-8 -*-
"""NHÀ CUNG CẤP TỪ CHỐI KHÔNG PHẢI LÀ VTOS HỎNG.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

`GET /api/v1/tong-dai/khoi-luong` trả **502** trên hệ thật, đo lại ngày 05/10/2026:

    {"detail": "Không đọc được lịch sử cuộc gọi: Tham số không hợp lệ"}

502 là mã 5xx, nên cửa này nằm trong bộ đếm lỗi máy chủ và đi thẳng lên bàn giám sát của Chủ tịch
dưới nhãn "Màn hình làm máy chủ lỗi". Câu ấy KHÔNG đúng. Phép chẩn đoán `/tong-dai/chan-doan` — thứ
chính làn này viết ra để khỏi phải đoán — trả lời dứt khoát:

    khoá bịa ("0"×32) trả về  : "Tham số không hợp lệ"   ← ĐÚNG mã mà khoá thật nhận
    cả bốn dạng tham số       : "Tham số không hợp lệ"   ← kể cả dạng đã xác minh là đúng

Nên mã 1003 ở đây không nói gì về tham số. Nó nghĩa là **P.A từ chối**, và việc phải làm nằm ở
trang quản trị của P.A chứ không nằm trong một dòng mã nào của VTOS.

"VTOS hỏng" và "khoá tổng đài hết hiệu lực" dẫn tới hai người khác nhau đi làm hai việc khác nhau.
Một bàn giám sát nói sai câu này thì người đọc đi tìm lỗi ở chỗ không có lỗi, và chỗ có lỗi thì
không ai đến.

Trớ trêu là chính cửa ấy ĐÃ làm đúng ở nhánh bên cạnh: chưa khai khoá thì nó trả 200 kèm hướng dẫn.
Cùng một tình huống con người — ai đó phải đi sửa cấu hình — mà hai câu trả lời máy khác hẳn nhau.

BA CHUYỆN trước nay bị trộn làm một, nay tách:
  · nhà cung cấp từ chối / không với tới  → 200, nói rõ phải làm gì, KHÔNG vào bộ đếm 5xx
  · không có cuộc gọi nào trong khoảng    → 200, số 0 — xem phép thử về mã 1005 dưới đây
  · mã của CHÍNH VTOS hỏng                 → vẫn 500, và PHẢI vẫn là 500

Chỗ thứ ba là chỗ dễ làm hỏng nhất khi sửa chỗ thứ nhất: nuốt mọi ngoại lệ thành 200 là bịt mắt bộ
đếm lỗi — sai ngược lại, và sai nặng hơn.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_td9.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_td9.db", "test_td9.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest                                                   # noqa: E402
from fastapi.testclient import TestClient                       # noqa: E402

from app.main import app                                        # noqa: E402
from app.services import pa_tong_dai as PA                      # noqa: E402

KHOA_THU = "khoa-that-khong-duoc-lo-0987654321abcdef"
client = TestClient(app)
TOK: dict = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture(autouse=True)
def _khoa():
    cu = os.environ.get("PA_TONG_DAI_API_KEY")
    os.environ["PA_TONG_DAI_API_KEY"] = KHOA_THU
    goi_cu = PA._goi
    yield
    PA._goi = goi_cu
    if cu is None:
        os.environ.pop("PA_TONG_DAI_API_KEY", None)
    else:
        os.environ["PA_TONG_DAI_API_KEY"] = cu


def _pa_tra(ma: str, thong_bao: str = "Successful", data=None):
    """Thay tầng gọi mạng bằng đúng gói tin P.A trả. Không phép thử nào gọi ra internet thật."""
    import json as _json
    import urllib.request

    class _Gia:
        def __init__(self, noi_dung): self._n = noi_dung
        def read(self): return self._n.encode("utf-8")
        def __enter__(self): return self
        def __exit__(self, *a): return False

    goi = _json.dumps({"code": ma, "message": thong_bao, "data": data if data is not None else []})
    urllib.request.urlopen = lambda req, timeout=None: _Gia(goi)   # noqa


# ============================== 1. KHÔNG CÓ CUỘC NÀO ≠ LỖI ==============================
def test_td9_mot_thang_khong_ai_goi_la_so_khong_chu_khong_phai_loi():
    """Mã 1005 "không tìm thấy bản ghi nào" là một CÂU TRẢ LỜI, không phải một sự cố.

    Trước 05/10/2026 nó bị ném thành ngoại lệ rồi thành 502: một tháng yên ắng đọc ra y hệt một máy
    chủ hỏng. Và đây là kiểu sai tệ nhất cho một phép ĐO, vì nó xảy ra đúng lúc con số đáng tin
    nhất — lúc không có gì để đếm.
    """
    _pa_tra("1005", "No record found")
    d = PA.do_khoi_luong("2026-09-01", "2026-09-30")
    assert d["so_cuoc"] == 0 and d["tong_phut"] == 0


# ============================== 2. TỪ CHỐI LÀ TỪ CHỐI, CÓ MÃ ==============================
@pytest.mark.parametrize("ma", ["1003", "1004", "1001", "1006", "1007"])
def test_td9_pa_tu_choi_thi_nem_dung_kieu_rieng_kem_ma(ma):
    _pa_tra(ma)
    with pytest.raises(PA.TongDaiTuChoi) as e:
        PA.do_khoi_luong("2026-09-01", "2026-09-30")
    assert e.value.ma == ma, "Mất mã lỗi thì người vận hành không tra được bảng của P.A"


def test_td9_khong_voi_toi_tong_dai_cung_la_chuyen_cua_nha_cung_cap():
    import urllib.request
    urllib.request.urlopen = lambda req, timeout=None: (_ for _ in ()).throw(OSError("timed out"))  # noqa
    with pytest.raises(PA.TongDaiTuChoi) as e:
        PA.do_khoi_luong("2026-09-01", "2026-09-30")
    assert e.value.ma == "mang"


def test_td9_tra_ve_khong_phai_json_cung_vay():
    import urllib.request

    class _Gia:
        def read(self): return b"<html>502 Bad Gateway</html>"
        def __enter__(self): return self
        def __exit__(self, *a): return False
    urllib.request.urlopen = lambda req, timeout=None: _Gia()      # noqa
    with pytest.raises(PA.TongDaiTuChoi) as e:
        PA.do_khoi_luong("2026-09-01", "2026-09-30")
    assert e.value.ma == "khong_json"


def test_td9_loi_1003_phai_noi_ro_no_KHONG_co_nghia_la_sai_tham_so():
    """Giữ lại kết luận đã phải đo mới có.

    Người sửa tiếp theo đọc chữ "Tham số không hợp lệ" sẽ đi sửa tham số — và mất một buổi, vì cả
    bốn dạng tham số đều nhận đúng mã ấy, kể cả dạng đã xác minh là đúng. Câu này phải nằm trong
    thứ người dùng ĐỌC ĐƯỢC, không chỉ trong chú thích mã nguồn.
    """
    v = PA.viec_phai_lam("1003")
    assert "cấp lại khoá" in v.lower(), f"Việc phải làm là cấp lại khoá, câu hiện tại: {v[:80]}"
    assert not v.lower().lstrip().startswith("sai tham số"), (
        "Câu hướng dẫn đang bảo người ta đi sửa tham số — đúng cái bẫy đã tốn một buổi để gỡ.")
    assert "khoá bịa" in v.lower(), "Phải nêu bằng chứng: khoá bịa cũng nhận đúng mã ấy"
    assert "pavietnam" in v.lower(), "Phải nói rõ đi đâu mà cấp lại khoá"


# ============================== 3. CỬA: 200 KÈM VIỆC PHẢI LÀM, KHÔNG PHẢI 502 ==============
def test_td9_cua_do_khoi_luong_khong_con_tra_5xx_khi_pa_tu_choi():
    """PHÉP THỬ BẮT ĐÚNG LỖI GỐC: 5xx là thứ đẩy cửa này lên bàn giám sát của Chủ tịch."""
    _pa_tra("1003")
    r = client.get("/api/v1/tong-dai/khoi-luong", headers=login("cntt"))
    assert r.status_code < 500, (
        f"Vẫn trả {r.status_code}. Mã 5xx nghĩa là VTOS hỏng, mà thứ hỏng là khoá của nhà cung cấp.")
    j = r.json()
    assert j["doc_duoc"] is False and j["da_khai_khoa"] is True
    assert j["ma"] == "1003"
    assert j["viec"], "Nói là đọc không được mà không nói phải làm gì thì người đọc vẫn đứng yên"


def test_td9_khoa_khong_bao_gio_lot_ra_cau_tra_loi():
    """Khoá nào đã đi qua trình duyệt thì coi như đã lộ — luật số 1 của chính tệp pa_tong_dai."""
    _pa_tra("1004")
    r = client.get("/api/v1/tong-dai/khoi-luong", headers=login("cntt"))
    assert KHOA_THU not in r.text
    r2 = client.get("/api/v1/tong-dai/chan-doan", headers=login("cntt"))
    assert KHOA_THU not in r2.text


def test_td9_loi_cua_CHINH_VTOS_van_phai_la_500():
    """CHỖ DỄ SỬA HỎNG NHẤT khi dọn 502: nuốt mọi ngoại lệ thành 200.

    Bịt cả lỗi của chính mình thì bộ đếm lỗi mù hẳn — sai ngược lại, và nặng hơn cái đang sửa. Ở
    đây dựng một lỗi THẬT của VTOS (không phải P.A từ chối) và đòi nó vẫn nổ ra 5xx.
    """
    class LoiCuaVtos(Exception):
        """CỐ Ý mang đủ `ma` và `thong_bao`.

        Nếu để nó là một KeyError trần thì nhánh `except Exception` (cách sửa hỏng) vẫn nổ ra 500 —
        nhưng nổ vì `ex.ma` không tồn tại, chứ không phải vì mã lỗi được để lọt lên. Phép thử khi ấy
        xanh với CẢ hai cách viết và không chứng minh được gì; đã đo đúng như vậy khi phá mã.
        Mang đủ hai thuộc tính thì chỉ cách viết ĐÚNG mới để nó bay lên.
        """
        ma, thong_bao = "1003", "giả vờ là từ chối"

    def no(tu, den, tran_trang=None):
        raise LoiCuaVtos()
    cu = PA.do_khoi_luong
    PA.do_khoi_luong = no
    try:
        with pytest.raises(Exception):
            client.get("/api/v1/tong-dai/khoi-luong", headers=login("cntt"))
    finally:
        PA.do_khoi_luong = cu


def test_td9_chua_khai_khoa_va_bi_tu_choi_tra_ve_CUNG_MOT_HINH():
    """Hai nhánh, một tình huống con người: ai đó phải đi sửa cấu hình.

    Trước vòng này một nhánh trả 200 kèm `huong_dan`, nhánh kia ném 502 — nên màn hình nào đọc cửa
    này cũng phải viết hai lối xử lý cho cùng một việc, và lối thứ hai thì không ai viết.
    """
    cu = os.environ.pop("PA_TONG_DAI_API_KEY", None)
    try:
        a = client.get("/api/v1/tong-dai/khoi-luong", headers=login("cntt")).json()
    finally:
        if cu is not None:
            os.environ["PA_TONG_DAI_API_KEY"] = cu
    _pa_tra("1004")
    b = client.get("/api/v1/tong-dai/khoi-luong", headers=login("cntt")).json()
    for k in ("doc_duoc", "ly_do", "viec"):
        assert k in a and k in b, f"Hai nhánh phải cùng hình, thiếu “{k}”"
    assert a["doc_duoc"] is False and b["doc_duoc"] is False
