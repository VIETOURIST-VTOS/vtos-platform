"""ĐỢT R7-MCT 01/11/2026 — Ô CHỌN MÃ CÔNG TRÌNH: NĂM LUẬT CANH.

Màn hình Sổ kế toán (Đợt R7-SO) để ô "Mã công trình" là một Ô GÕ TAY. Gõ tay thì người dùng tự
nghĩ ra một mã không tồn tại, nhận về một sổ rỗng, và không biết vì sao — màn hình nói sai mà
không ai thấy nó nói sai.

Chủ tịch chốt 01/11/2026: ô ấy đọc DANH SÁCH TOUR THẬT do Điều hành và Sales Admin tạo, mã nào
chưa có trong danh mục công trình thì VẪN HIỆN nhưng ghi rõ.

Năm luật dưới đây canh đúng năm chỗ dễ tuột: cửa biến mất, cửa nuốt cả bảng, cờ `co_trong_so`
bị bỏ, ô tìm không tìm được, và quyền bị nới.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_r7mct.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_r7mct.db"): os.remove("test_r7mct.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
CUA = "/api/v1/books/ma-cong-trinh"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


@pytest.fixture(scope="module")
def tat_ca():
    h = login("ketoan")
    r = client.get(CUA, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_r7mct_1_cua_tra_du_khoa(tat_ca):
    """Cửa trả đủ khoá, và PHẢI có tour thật để trả.

    Nếu kho gieo không có tour nào thì luật này đỏ — đúng như thế: một ô chọn không bao giờ có
    gì để chọn là một ô chọn hỏng, không phải một ô chọn rỗng.
    """
    assert set(tat_ca) >= {"q", "rows", "total_rows", "shown_rows", "truncated", "limit"}
    assert tat_ca["total_rows"] > 0, "kho gieo khong co tour nao — o chon se luon rong"
    for r in tat_ca["rows"]:
        assert set(r) == {"code", "ten", "tu_ngay", "den_ngay", "co_trong_so"}
        assert isinstance(r["co_trong_so"], bool)
        assert r["code"]


def test_r7mct_2_co_tran_va_noi_ra(tat_ca):
    """Cửa KHÔNG BAO GIỜ trả cả bảng: có trần, và nói ra khi đã cắt.

    `GET /api/v1/tours` đo được 16–30 giây trên hệ thật vì nó trả cả bảng. Cửa này sinh ra để
    KHÔNG lặp lại điều đó, nên trần là phần việc của nó chứ không phải tuỳ chọn của người gọi.
    """
    assert tat_ca["limit"] <= 50
    assert tat_ca["shown_rows"] == len(tat_ca["rows"]) <= tat_ca["limit"]
    assert tat_ca["truncated"] == (tat_ca["total_rows"] > tat_ca["shown_rows"])
    h = login("ketoan")
    xin_nhieu = client.get(f"{CUA}?limit=99999", headers=h).json()
    assert xin_nhieu["limit"] <= 50, "nguoi goi xin 99999 ma cua van phai giu tran cua no"


def test_r7mct_3_tim_duoc_theo_ma_va_theo_ten(tat_ca):
    """Ô tìm phải tìm được bằng CẢ mã lẫn tên — người làm sổ nhớ tên đoàn, không nhớ mã."""
    h = login("ketoan")
    mau = tat_ca["rows"][0]
    theo_ma = client.get(f"{CUA}?q={mau['code']}", headers=h).json()
    assert any(r["code"] == mau["code"] for r in theo_ma["rows"]), "tim theo ma khong ra chinh no"
    if mau["ten"]:
        chu = mau["ten"].split()[0]
        theo_ten = client.get(f"{CUA}?q={chu}", headers=h).json()
        assert theo_ten["rows"], f"tim theo ten '{chu}' khong ra dong nao"
    khong_co = client.get(f"{CUA}?q=ZZZ-KHONG-BAO-GIO-CO-MA-NAY", headers=h).json()
    assert khong_co["rows"] == [] and khong_co["total_rows"] == 0


def test_r7mct_4_co_trong_so_noi_that():
    """`co_trong_so` phải trả lời ĐÚNG câu "chọn mã này có ra số không".

    Sổ kế toán gom theo `project_code`. Một mã tour chưa có công trình thì chọn nó cũng không ra
    số. Giấu điều đó đi thì kế toán thấy sổ rỗng và tưởng đoàn ấy không phát sinh gì.

    Đo THẲNG ở cơ sở dữ liệu, không tin lời cửa: lấy một tour, tự hỏi danh mục công trình, rồi
    so với cờ cửa trả về. Hai đường nối đều tính — `tour_id` và mã trùng.
    """
    from sqlalchemy import or_, select
    from app.db.session import SessionLocal
    from app.models.accounting import Project
    from app.models.core import Tour

    h = login("ketoan")
    db = SessionLocal()
    try:
        for t in db.execute(select(Tour.id, Tour.code).limit(5)).all():
            that = db.execute(select(Project.id).where(
                or_(Project.tour_id == t.id, Project.code == t.code)).limit(1)).first() is not None
            cua = client.get(f"{CUA}?q={t.code}", headers=h).json()
            dong = [r for r in cua["rows"] if r["code"] == t.code]
            assert dong, f"tour {t.code} co that ma cua khong tra ve"
            assert dong[0]["co_trong_so"] is that, f"tour {t.code}: cua noi {dong[0]['co_trong_so']}, so noi {that}"
    finally:
        db.close()


def test_r7mct_5_quyen_khong_bi_noi():
    """Cửa này dùng ĐÚNG nhóm `READ` của sổ — không khai một danh sách vai riêng.

    `tp_dh` vào được màn hình `/accounting` nhưng `books.READ` chặn vai ấy đọc sổ. Mở cửa này
    cho nó là nới một quyền chưa ai ký, qua một cửa phụ — đúng cái Lỗi 3 bản rà soát v1.0 đã bắt.

    ĐO BẢN KHAI, KHÔNG ĐO LẠI KHUNG. `require_roles` đã có `test_ma_tran_quyen` và
    `test_le2b_ba_vai_ke_toan` canh. Việc của luật này là canh CHÍNH DÒNG KHAI của cửa mới: ai
    viết `require_roles("ketoan", "tp_dh")` vào đây thì đỏ ngay, dù kho gieo có người dùng của
    vai ấy hay không.

    Bản đầu của luật này đăng nhập bằng `ketoan_truong` và ĐỎ ngày 01/11/2026 — không phải vì mã
    sai mà vì kho gieo KHÔNG CÓ người dùng tên ấy. Một phép thử phụ thuộc vào dữ liệu gieo thì nó
    đo dữ liệu gieo, không đo luật.
    """
    from app.api.v1 import books as API

    nguon = open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "app", "api", "v1", "books.py"), encoding="utf-8").read()
    khoi = nguon.split('@router.get("/ma-cong-trinh")', 1)[1].split("@router.", 1)[0]
    assert "require_roles(*READ)" in khoi, "cua moi khai mot danh sach vai rieng thay vi dung nhom READ"

    assert "tp_dh" not in API.READ
    assert "ketoan_truong" in API.READ
    assert "ketoan" in API.READ
    assert client.get(CUA, headers=login("ketoan")).status_code == 200
