"""KS-64 · 09/11/2026 — bốn điều máy chủ HỨA với hai cửa nhập bốn bước của bản v3.3.

Giao diện bốn bước thì ai cũng thấy; bốn điều dưới đây thì không ai thấy, và cả bốn đều là loại
sai LẶNG — không có thông báo đỏ ở đâu hết khi nó hỏng. Nên chúng có phép thử riêng:

  1. SÁU TRƯỜNG MỚI PHẢI VÀO SỔ. pydantic bỏ lặng lẽ trường lạ: nếu `can_cu_so_tien` hay
     `ma_khoan_goc` chưa khai ở `DeXuatChiIn` thì người gõ thấy mình đã khai, mà sổ trống trơn.
     Phép thử đọc lại dòng giao dịch và đòi thấy đúng chữ mình vừa gửi.

  2. Ô NGÂN HÀNG KHÔNG THUỘC VAI GĐ ĐỘI XE — và chặn ở MÁY CHỦ. v3.3 §2/§7. Ẩn ô trên màn hình
     là một lời đề nghị; ai cũng gọi thẳng cửa này bằng một dòng fetch. Phép thử gọi thẳng.

  3. VAI KẾ TOÁN VẪN GHI ĐƯỢC tài khoản và ngân hàng. Một hàng rào dựng sai chỗ thì nó chặn
     đúng người đang làm việc — vế này quan trọng ngang vế trên.

  4. GỬI HAI LẦN THÌ CHỈ MỘT PHIẾU. Ở bước 4 người ta bấm Gửi, trang chưa kịp trả lời, họ bấm
     lại. Trước bản này mỗi lần bấm sinh một mã mới nên hệ thống KHÔNG thấy gì trùng.

Và một điều máy chủ CỐ Ý KHÔNG hứa: ô "hẹn bổ sung chứng từ" ở bước 2 KHÔNG mở ngưỡng chứng từ
bắt buộc (chặn cứng B6). §11 xếp "trường hợp được gửi thiếu chứng từ" vào năm cấu hình phải có
người chốt; một dòng lý do gõ tay không phải một người chốt. Phép thử cuối giữ đúng chỗ ấy —
nếu ngày nào có người nới nó ra, phải là nới có chủ ý, không phải nới nhân một đợt sửa giao diện.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_ks64.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ks64.db"): os.remove("test_ks64.db")
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
HOM_NAY = date.today()
GD = "gd.doixe.ks64"


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.models.core import User
        from app.core.security import hash_password
        db = SessionLocal()
        db.add(User(username=GD, full_name="GĐ đội xe KS-64", role="gd_doi_xe", department="doi_xe",
                    staff_code="KS64", password_hash=hash_password("Vtos@Demo#2026"), active=True))
        db.commit(); db.close()
        yield


def dong(ma: str) -> dict:
    """Đọc lại dòng giao dịch vừa ghi, bằng chính cửa mà màn Đối soát đang dùng."""
    d = client.get("/api/v1/fleet/giao-dich?source=de_xuat_vietrip", headers=login("ketoan")).json()
    return next(t for t in d["rows"] if t["ma_gd"] == ma)


# ───────────────────────── 1 · sáu trường mới phải VÀO SỔ ─────────────────────────

def test_sau_truong_moi_cua_bon_buoc_khong_bi_bo_lang_le():
    h = login("ketoan")
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=h,
                    json={"ngay": str(HOM_NAY), "so_tien": 3_300_000, "noi_dung": "Thay loc dau xe Carnival",
                          "nhom": "Sửa chữa – bảo dưỡng", "nguoi_thu_huong": "Garage Tan Binh",
                          "chung_tu": "HD-KS64-001",
                          "pham_vi": "xe", "loai": "tam_ung",
                          "can_cu_so_tien": "Đã gồm thuế / phí theo chứng từ",
                          "ma_khoan_goc": "2026-11-93408-0911-1",
                          "ghi_chu_kiem_tra": "Xe dang chay tour, can xu ly trong ngay"})
    assert r.status_code == 201, r.text
    t = dong(r.json()["ma_gd"])
    kho = f"{t.get('mo_ta') or ''} {t.get('ghi_chu') or ''}"
    # Căn cứ số tiền và mã khoản gốc là hai thứ dùng để KHÔNG cộng một khoản hai lần. Chúng phải
    # đọc được từ chính dòng giao dịch, không chỉ nằm trong nhật ký audit: người đi đối soát mở
    # danh sách giao dịch, không mở audit log.
    assert "Đã gồm thuế" in kho, kho
    assert "2026-11-93408-0911-1" in kho, kho
    assert "Tạm ứng" in kho, kho
    assert "can xu ly trong ngay" in kho, kho


def test_hen_bo_sung_chung_tu_nam_lai_trong_so():
    """Khoản DƯỚI ngưỡng, chưa có chứng từ, có lời hẹn. Lời hẹn phải vào sổ để sau còn tra được
    khoản nào đang nợ giấy – và nợ từ bao giờ."""
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"),
                    json={"ngay": str(HOM_NAY), "so_tien": 450_000, "noi_dung": "Rua xe truoc tour",
                          "nhom": "Chi phí riêng của xe", "nguoi_thu_huong": "Tiem rua xe Bay",
                          "hen_bo_sung": "phieu thu tra ngay 15/11"})
    assert r.status_code == 201, r.text
    t = dong(r.json()["ma_gd"])
    kho = f"{t.get('mo_ta') or ''} {t.get('ghi_chu') or ''}"
    assert "CHƯA CÓ CHỨNG TỪ" in kho and "15/11" in kho, kho


# ──────────────── 2 + 3 · ô ngân hàng: chặn vai GĐ, KHÔNG chặn kế toán ────────────────

@pytest.mark.parametrize("o", ["so_tai_khoan", "ngan_hang"])
def test_gd_doi_xe_khong_ghi_duoc_o_ngan_hang(o):
    """v3.3 §2, §7. Gọi THẲNG cửa máy chủ, không qua màn hình: ẩn ô là lời đề nghị, không phải
    hàng rào."""
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login(GD),
                    json={"ngay": str(HOM_NAY), "so_tien": 1_200_000, "noi_dung": "Va lop doc duong",
                          "nhom": "Chi phí riêng của xe", "nguoi_thu_huong": "Lop Hung",
                          o: "0601234567890" if o == "so_tai_khoan" else "Vietcombank"})
    assert r.status_code == 422, r.text
    assert "Kế toán kiểm soát" in r.json()["detail"]


def test_gd_doi_xe_van_ghi_duoc_ben_nhan_va_lap_duoc_phieu():
    """Vế thứ hai: cái bị lấy khỏi tay GĐ là SỐ TÀI KHOẢN và NGÂN HÀNG, không phải cả cái phiếu."""
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login(GD),
                    json={"ngay": str(HOM_NAY), "so_tien": 1_200_000, "noi_dung": "Va lop doc duong",
                          "nhom": "Chi phí riêng của xe", "nguoi_thu_huong": "Lop Hung",
                          "pham_vi": "xe", "loai": "thanh_toan",
                          "can_cu_so_tien": "Không phát sinh thuế / phí"})
    assert r.status_code == 201, r.text
    assert "Lop Hung" in (dong(r.json()["ma_gd"]).get("mo_ta") or "")


def test_ke_toan_van_ghi_duoc_tai_khoan_va_ngan_hang():
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"),
                    json={"ngay": str(HOM_NAY), "so_tien": 7_700_000, "noi_dung": "Thanh toan bao hiem xe",
                          "nhom": "Chi phí riêng của xe", "nguoi_thu_huong": "CTY Bao hiem PTI",
                          "so_tai_khoan": "060058950621", "ngan_hang": "Sacombank",
                          "chung_tu": "HD-KS64-BH"})
    assert r.status_code == 201, r.text


# ───────────────────────── 4 · gửi hai lần thì chỉ một phiếu ─────────────────────────

def test_gui_hai_lan_cung_chung_tu_thi_bi_chan():
    j = {"ngay": str(HOM_NAY), "so_tien": 5_500_000, "noi_dung": "Thay bo thang",
         "nhom": "Sửa chữa – bảo dưỡng", "nguoi_thu_huong": "Garage Phu Nhuan",
         "chung_tu": "HD-KS64-TRUNG"}
    a = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"), json=j)
    assert a.status_code == 201, a.text
    b = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"), json=j)
    assert b.status_code == 422, b.text
    # Thông báo phải GỌI TÊN phiếu cũ: "đã trùng" mà không nói trùng với cái nào thì người gõ
    # không biết nên xem lại phiếu nào.
    assert a.json()["ma_gd"] in b.json()["detail"], b.json()["detail"]


def test_van_gui_duoc_khi_nguoi_lap_da_xem_va_xac_nhan_la_khoan_khac():
    j = {"ngay": str(HOM_NAY), "so_tien": 5_500_000, "noi_dung": "Thay bo thang xe thu hai",
         "nhom": "Sửa chữa – bảo dưỡng", "nguoi_thu_huong": "Garage Phu Nhuan",
         "chung_tu": "HD-KS64-TRUNG", "cho_phep_trung": True}
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"), json=j)
    assert r.status_code == 201, r.text


def test_khac_so_tien_thi_khong_coi_la_trung():
    """Hàng rào chống trùng phải hẹp. Chặn rộng quá thì người ta học cách tích «vẫn gửi» mọi lần,
    và lúc ấy hàng rào không còn tác dụng gì nữa."""
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"),
                    json={"ngay": str(HOM_NAY), "so_tien": 5_500_001, "noi_dung": "Thay bo thang",
                          "nhom": "Sửa chữa – bảo dưỡng", "nguoi_thu_huong": "Garage Phu Nhuan",
                          "chung_tu": "HD-KS64-TRUNG"})
    assert r.status_code == 201, r.text


# ──────────── điều CỐ Ý KHÔNG hứa: lời hẹn KHÔNG mở ngưỡng chứng từ ────────────

def test_hen_bo_sung_KHONG_mo_nguong_chung_tu_bat_buoc():
    """Chặn cứng B6 giữ nguyên là chặn cứng. Ai được miễn và miễn tới mức nào là việc §11 ghi rõ
    phải có người chốt – không phải việc một ô lý do gõ tay mở ra."""
    r = client.post("/api/v1/fleet/de-xuat-chi", headers=login("ketoan"),
                    json={"ngay": str(HOM_NAY), "so_tien": 50_000_000, "noi_dung": "Dai tu hop so",
                          "nhom": "Sửa chữa – bảo dưỡng", "nguoi_thu_huong": "Garage Truong Chinh",
                          "hen_bo_sung": "hoa don ve tuan sau"})
    assert r.status_code == 422, r.text
    assert "chứng từ gốc" in r.json()["detail"]


# ──────────── ngưỡng phải ĐỌC ĐƯỢC từ máy chủ, không gõ lại trong mã web ────────────

def test_man_hinh_doc_duoc_nguong_chung_tu_tu_may_chu():
    """Bước 2 của cả hai cửa báo trước bằng đúng con số đang áp. Gõ lại số trong mã web thì ngày
    nào đó ai sửa tham số trên màn Chính sách & định mức, màn hình vẫn báo con số cũ."""
    d = client.get("/api/v1/fleet/danh-muc-dot3", headers=login(GD)).json()
    assert "nguong_chung_tu" in d, list(d)
    assert float(d["nguong_chung_tu"]) > 0
