"""Đầu nhận webhook tổng đài – nghe trước, hiểu sau.

P.A Việt Nam có bốn API tổng đài nhưng không công bố đặc tả, nên VTOS mở một đầu nhận ghi NGUYÊN VĂN
thay vì đoán tên trường. Một đầu nhận công khai (không đăng nhập) thì mỗi tính chất dưới đây là một chỗ
có thể hỏng thầm, nên chốt hết bằng phép thử:

  TD1  chưa khai chuỗi bí mật thì đầu nhận ĐÓNG – không mở sẵn một cửa không khoá để chờ cấu hình
  TD2  sai chuỗi thì 404, không phải 403 – không xác nhận đường dẫn có tồn tại
  TD3  đúng chuỗi thì ghi nguyên văn cả chuỗi truy vấn lẫn thân, không diễn giải
  TD4  cookie và chuỗi uỷ quyền của bên gọi KHÔNG được lưu
  TD5  thân quá dài bị cắt, không nuốt trọn
  TD6  ghi hỏng vẫn trả 200 – nhà cung cấp tắt webhook khi nhận mã lỗi
  TD7  bảng đọc gom được tên trường đã gặp (đặc tả dựng lại từ quan sát) và đòi đúng vai trò
  TD8  quá trần thì dọn dòng cũ, không để đầy đĩa
"""
import os, sys, json
os.environ["DATABASE_URL"] = "sqlite:///./test_tongdai.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
os.environ["TONG_DAI_WEBHOOK_MA"] = "ma-thu-nghiem-123456"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tongdai.db", "test_tongdai.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

MA = "ma-thu-nghiem-123456"
client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        yield


def test_td1_chua_khai_chuoi_bi_mat_thi_dau_nhan_dong():
    """Mở sẵn một cửa không khoá để chờ cấu hình là cách chắc chắn nhất để quên mất nó đang mở."""
    from app.services import tong_dai as TD
    cu = os.environ.pop("TONG_DAI_WEBHOOK_MA", None)
    try:
        assert TD.kiem_ma("") is False
        assert TD.kiem_ma("bat-ky-chuoi-nao") is False, \
            "chưa khai chuỗi bí mật thì KHÔNG chuỗi nào được đi qua"
        assert TD.duong_dan_webhook() == "", \
            "chưa mở thì không đưa ra địa chỉ, để màn hình nói 'chưa mở' thay vì đưa địa chỉ chết"
        assert client.post(f"/api/v1/tong-dai/cuoc-goi/{MA}").status_code == 404
    finally:
        if cu is not None: os.environ["TONG_DAI_WEBHOOK_MA"] = cu


def test_td2_sai_chuoi_tra_404_khong_phai_403():
    """403 nói 'có đường dẫn này, bạn chỉ thiếu quyền'. 404 không nói gì cả."""
    r = client.post("/api/v1/tong-dai/cuoc-goi/chuoi-sai-hoan-toan")
    assert r.status_code == 404, f"đang trả {r.status_code}"


def test_td3_dung_chuoi_thi_ghi_nguyen_van_khong_dien_giai():
    """Ghi nguyên văn là toàn bộ mục đích: khi P.A trỏ webhook vào, mình phải ĐỌC ĐƯỢC giao thức thật."""
    than = json.dumps({"caller": "0987133383", "did": "02822317777", "uniqueid": "abc-123"})
    r = client.post(f"/api/v1/tong-dai/cuoc-goi/{MA}?event=incoming&extension=101",
                    content=than, headers={"Content-Type": "application/json"})
    assert r.status_code == 200 and r.json()["ok"] is True

    from app.db.session import SessionLocal
    from app.models.crm import TongDaiSuKien
    from sqlalchemy import select
    db = SessionLocal()
    sk = db.execute(select(TongDaiSuKien).order_by(TongDaiSuKien.id.desc())).scalars().first()
    assert sk is not None
    assert "event=incoming" in sk.chuoi_truy_van and "extension=101" in sk.chuoi_truy_van
    assert sk.than == than, "thân phải giữ NGUYÊN VĂN, không phân tích, không chuẩn hoá"
    assert sk.phuong_thuc == "POST"
    db.close()


def test_td4_khong_luu_cookie_va_chuoi_uy_quyen_cua_ben_goi():
    """Giữ lại đầu mục xác thực của bên gọi là tự tạo một kho bí mật của người khác trong CSDL của mình."""
    client.post(f"/api/v1/tong-dai/cuoc-goi/{MA}", content="x=1",
                headers={"Cookie": "phien=BIMAT_KHONG_DUOC_LUU",
                         "Authorization": "Bearer TOKEN_KHONG_DUOC_LUU",
                         "User-Agent": "PA-Tongdai/1.0"})
    from app.db.session import SessionLocal
    from app.models.crm import TongDaiSuKien
    from sqlalchemy import select
    db = SessionLocal()
    sk = db.execute(select(TongDaiSuKien).order_by(TongDaiSuKien.id.desc())).scalars().first()
    kho = json.dumps(sk.dau_muc).lower()
    assert "bimat_khong_duoc_luu" not in kho and "token_khong_duoc_luu" not in kho, \
        "cookie / chuỗi uỷ quyền của bên gọi không được lưu"
    assert "cookie" not in sk.dau_muc and "authorization" not in sk.dau_muc
    assert "user-agent" in sk.dau_muc, "đầu mục nói về nguồn gọi thì giữ – đó là thứ để nhận ra ai gọi"
    db.close()


def test_td5_than_qua_dai_bi_cat():
    from app.services import tong_dai as TD
    client.post(f"/api/v1/tong-dai/cuoc-goi/{MA}", content="A" * (TD.THAN_TOI_DA + 5_000))
    from app.db.session import SessionLocal
    from app.models.crm import TongDaiSuKien
    from sqlalchemy import select
    db = SessionLocal()
    sk = db.execute(select(TongDaiSuKien).order_by(TongDaiSuKien.id.desc())).scalars().first()
    assert len(sk.than) == TD.THAN_TOI_DA, f"phải cắt ở {TD.THAN_TOI_DA}, đang giữ {len(sk.than)}"
    db.close()


def test_td6_ghi_hong_van_tra_200():
    """Nhà cung cấp thường TẮT webhook sau vài lần nhận mã lỗi. Mất webhook là mất luôn cơ hội nhìn thấy
    giao thức – nên lỗi phía mình không được lộ ra thành mã lỗi phía họ."""
    from app.services import tong_dai as TD
    goc = TD.ghi
    TD.ghi = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ổ đĩa đầy"))
    try:
        r = client.post(f"/api/v1/tong-dai/cuoc-goi/{MA}", content="y=2")
        assert r.status_code == 200, f"ghi hỏng vẫn phải trả 200, đang trả {r.status_code}"
    finally:
        TD.ghi = goc


def test_td7_bang_doc_gom_ten_truong_va_doi_dung_vai_tro():
    """`khoa_thay` chính là đặc tả mà nhà cung cấp không đưa, dựng lại từ những gì đã nhận."""
    assert client.get("/api/v1/tong-dai/su-kien").status_code in (401, 403)
    assert client.get("/api/v1/tong-dai/su-kien", headers=login("kd.hoa")).status_code == 403, \
        "nhật ký kỹ thuật không phải chỗ của sale"
    j = client.get("/api/v1/tong-dai/su-kien", headers=login("cntt")).json()
    assert j["da_mo"] is True and j["duong_dan_webhook"].endswith(MA)
    khoa = dict(j["khoa_thay"])
    for k in ("event", "extension", "caller", "uniqueid"):
        assert k in khoa, f"tên trường '{k}' đã nhận được thì phải hiện ra trong bảng đặc tả quan sát"


def test_td8_qua_tran_thi_don_dong_cu():
    """Một đầu nhận công khai là một đầu nhận có thể bị dội. Đĩa đầy thì cả hệ thống dừng."""
    from app.services import tong_dai as TD
    from app.db.session import SessionLocal
    from app.models.crm import TongDaiSuKien
    from sqlalchemy import select, func
    db = SessionLocal()
    cu = TD.TRAN_DONG
    TD.TRAN_DONG = 5
    try:
        for i in range(12):
            TD.ghi(db, nguon="thu", phuong_thuc="POST", duong_dan="/x", chuoi_truy_van=f"i={i}",
                   than="", dau_muc={}, ip="127.0.0.1")
        db.commit()
        n = int(db.execute(select(func.count()).select_from(TongDaiSuKien.__table__)).scalar())
        assert n <= TD.TRAN_DONG + 1, f"phải dọn về quanh {TD.TRAN_DONG} dòng, đang giữ {n}"
        # dòng còn lại phải là dòng MỚI nhất, không phải dòng cũ nhất
        cuoi = db.execute(select(TongDaiSuKien).order_by(TongDaiSuKien.id.desc())).scalars().first()
        assert "i=11" in cuoi.chuoi_truy_van
    finally:
        TD.TRAN_DONG = cu
        db.close()
