"""Kho tệp & hình ảnh dùng chung: chứng từ ảnh của mọi phòng ban.

Năm cách một kho chứng từ trở nên vô dụng, và bộ test này chặn cả năm:

  1. Nhận tệp chạy được – kho chứng từ biến thành kho phát tán.
  2. Nhận tệp nặng tùy ý – một ảnh 40 MB tải lên giữa giờ cao điểm là đủ làm chậm cả hệ thống 512 MB.
  3. Cùng một ảnh tạo hai bản ghi – người đọc hồ sơ phải đoán hai bản giống nhau khác nhau chỗ nào.
  4. Xóa cứng – chứng từ biến mất không dấu vết, kiểm toán bế tắc.
  5. Trả về nội dung không khớp mã băm – hồ sơ "gần đúng" tệ hơn hồ sơ báo lỗi.
"""
import os, sys, io
os.environ["DATABASE_URL"] = "sqlite:///./test_tep.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
os.environ["VISA_DOC_DIR"] = "./test_tep_kho"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_tep.db"): os.remove("test_tep.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
# PNG 1×1 thật, không phải chuỗi giả – để phần đoán loại nội dung chạy đúng như lúc người dùng tải ảnh lên.
ANH = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a4944415478"
                    "9c63000100000500010d0a2db40000000049454e44ae426082")


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def tai(who, ten, data, doi_tuong="chuyen_xe", dtid="1", loai="chung_tu", kieu="image/png", **kw):
    return client.post("/api/v1/tep", headers=login(who),
                       files={"tep": (ten, io.BytesIO(data), kieu)},
                       data={"doi_tuong": doi_tuong, "doi_tuong_id": dtid, "loai": loai, **kw})


# ---------------------------------------------------------------- Cấu hình
def test_cau_hinh_du_de_mot_tac_vu_ai_biet_gioi_han_truoc_khi_gui(_startup):
    d = client.get("/api/v1/tep/cau-hinh", headers=login("ketoan")).json()
    assert d["gioi_han_mb"] > 0 and "pdf" in d["duoi_nhan"] and "exe" in d["duoi_tu_choi"]
    assert {x["ma"] for x in d["doi_tuong"]} >= {"chuyen_xe", "booking", "nhan_su", "hoa_don"}
    assert all(x["phong_ban"] for x in d["doi_tuong"])
    assert "kho_luu" in d and "durable" in d["kho_luu"]


# ---------------------------------------------------------------- Nhận tệp
def test_gan_anh_vao_chung_tu_va_doc_lai_dung_noi_dung(_startup):
    r = tai("ketoan", "hoa_don_dau.png", ANH)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["moi"] and d["la_anh"] and d["kich_thuoc"] == len(ANH)
    assert d["ten_tep"] == "hoa_don_dau.png"
    ve = client.get(f"/api/v1/tep/{d['id']}/tai", headers=login("ketoan"))
    assert ve.status_code == 200 and ve.content == ANH


def test_ten_tep_khong_phai_la_cho_luu(_startup):
    """Lấy tên người dùng đặt làm đường dẫn là mở cửa cho tên tệp lạ ghi đè tệp của hồ sơ khác."""
    from app.db.session import SessionLocal
    from app.models.attachments import Attachment
    from sqlalchemy import select
    with SessionLocal() as db:
        a = db.execute(select(Attachment).order_by(Attachment.id.desc())).scalars().first()
        assert "hoa_don_dau.png" not in a.khoa_luu
        assert a.checksum[:12] in a.khoa_luu


def test_duong_dan_dung_cau_truc_kho_ho_so(_startup):
    """Mô hình quản trị số hóa mục 7.2: Pháp nhân / Năm / Nhóm hồ sơ / Tháng-hoặc-Mã đối tượng / Tệp.

    Cấu trúc giống nhau ở mọi pháp nhân là điều kiện để kiểm toán viên mở kho của một pháp nhân họ chưa
    từng làm việc cùng mà vẫn tìm ra hồ sơ, không phải hỏi ai."""
    from app.db.session import SessionLocal
    from app.models.attachments import Attachment
    from sqlalchemy import select
    with SessionLocal() as db:
        a = db.execute(select(Attachment).order_by(Attachment.id.desc())).scalars().first()
        phan = a.khoa_luu.split("/")
        assert len(phan) == 5, a.khoa_luu
        assert phan[0] == "CHUA_XAC_DINH", "chưa khai pháp nhân thì nói rõ, không mặc định về công ty mẹ"
        assert phan[1].isdigit() and len(phan[1]) == 4
        assert phan[2] == "05_Tour"          # chuyến xe thuộc nhóm hồ sơ tour
        assert phan[3] == a.doi_tuong_id     # tour/nhân sự lưu theo mã đối tượng, không theo tháng
        assert a.nhom_ho_so == "05_Tour" and a.nhay_cam is False


def test_ho_so_nhan_su_luu_theo_ma_nv_va_danh_dau_nhay_cam(_startup):
    """Nghị định 13/2023 và mục 7.3: hồ sơ nhân sự là dữ liệu cá nhân, phân quyền riêng."""
    r = tai("hcns", "hop_dong_lao_dong.pdf", b"%PDF-1.4 hop dong", doi_tuong="nhan_su", dtid="NS0016",
            loai="hop_dong", kieu="application/pdf")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["nhom_ho_so"] == "06_Nhan_su" and d["nhay_cam"] is True
    assert d["thoi_han_luu"].startswith("Thời gian làm việc")
    from app.db.session import SessionLocal
    from app.models.attachments import Attachment
    with SessionLocal() as db:
        a = db.get(Attachment, d["id"])
        assert a.khoa_luu.split("/")[2:4] == ["06_Nhan_su", "NS0016"]


def test_ho_so_nhan_su_khong_lo_ra_cho_vai_tro_khac(_startup):
    """Xem được màn hình nhân sự KHÔNG đồng nghĩa với xem được hợp đồng lao động của từng người."""
    ds = client.get("/api/v1/tep?doi_tuong=nhan_su&doi_tuong_id=NS0016", headers=login("hcns")).json()
    assert len(ds) == 1
    aid = ds[0]["id"]
    for ai in ("ketoan", "kd.hoa", "cntt"):
        assert client.get(f"/api/v1/tep?doi_tuong=nhan_su&doi_tuong_id=NS0016",
                          headers=login(ai)).json() == [], f"{ai} không được thấy hồ sơ nhân sự"
        assert client.get(f"/api/v1/tep/{aid}/tai", headers=login(ai)).status_code == 403, ai
    assert client.get(f"/api/v1/tep/{aid}/tai", headers=login("hcns")).status_code == 200


def test_vai_tro_khac_khong_gan_duoc_tep_vao_ho_so_nhan_su(_startup):
    r = tai("ketoan", "gi_do.pdf", b"%PDF-1.4 x", doi_tuong="nhan_su", dtid="NS0002",
            loai="hop_dong", kieu="application/pdf")
    assert r.status_code == 403 and "Nghị định 13/2023" in r.json()["detail"]


def test_cau_hinh_cong_bo_du_nhom_ho_so_va_thoi_han_luu(_startup):
    """Chín nhóm theo Mô hình quản trị số hóa, cộng nhóm thứ mười thêm 09/9/2026.

    Nhóm "10_Marketing" (lưu 5 năm) sinh ra cùng đợt mở cửa tải tệp cho nội dung marketing: ảnh sắp
    đăng không phải hồ sơ pháp lý cũng không phải chứng từ ghi sổ, nhét vào một nhóm sẵn có cho tiện
    là làm hỏng thời hạn lưu của cả nhóm ấy.

    Phép thử này đọc số nhóm THẲNG TỪ khai báo chứ không viết cứng một con số nữa. Viết cứng thì mỗi
    lần thêm nhóm lại đỏ một lần và người sửa chỉ việc tăng số – tức là phép thử không canh gì cả.
    Điều đáng canh là: nhóm nào cũng phải có thời hạn lưu, và cấu trúc kho không đổi.
    """
    from app.models.attachments import NHOM_HO_SO
    d = client.get("/api/v1/tep/cau-hinh", headers=login("ketoan")).json()
    assert len(d["nhom_ho_so"]) == len(NHOM_HO_SO) >= 9
    assert all(n["thoi_han_luu"] for n in d["nhom_ho_so"])
    assert "Pháp nhân / Năm / Nhóm hồ sơ" in d["cau_truc_kho"]


def test_cung_mot_anh_gan_hai_lan_khong_tao_ban_thu_hai(_startup):
    r = tai("ketoan", "ten_khac_hoan_toan.png", ANH)
    assert r.status_code == 201 and r.json()["moi"] is False
    assert "đã có trong hồ sơ" in r.json()["message"]
    ds = client.get("/api/v1/tep?doi_tuong=chuyen_xe&doi_tuong_id=1", headers=login("ketoan")).json()
    assert len(ds) == 1


def test_cung_anh_nhung_khac_ho_so_thi_van_la_hai_ban(_startup):
    """Cùng tấm ảnh gắn cho hai chứng từ khác nhau là hai lần đính kèm thật – không gộp."""
    r = tai("ketoan", "hoa_don_dau.png", ANH, dtid="2")
    assert r.status_code == 201 and r.json()["moi"] is True


def test_tu_choi_tep_chay_duoc(_startup):
    r = tai("ketoan", "chay_di.exe", b"MZ" + b"\0" * 100, kieu="application/octet-stream")
    assert r.status_code == 422 and "không chứa tệp chạy được" in r.json()["detail"]


def test_tu_choi_tep_qua_nang_va_noi_ro_bao_nhieu(_startup):
    from app.services import attachments as AT
    r = tai("ketoan", "to_qua.png", b"\0" * ((AT.GIOI_HAN_MB + 1) * 1024 * 1024))
    assert r.status_code == 422 and "vượt mức cho phép" in r.json()["detail"]


def test_tu_choi_duoi_la(_startup):
    r = tai("ketoan", "du_lieu.sqlite", b"x" * 10, kieu="application/octet-stream")
    assert r.status_code == 422 and "Nhận: ảnh" in r.json()["detail"]


def test_khong_gan_vao_doi_tuong_khong_khai_bao(_startup):
    r = tai("ketoan", "a.png", ANH, doi_tuong="linh_tinh")
    assert r.status_code == 422 and "đối tượng hợp lệ" in r.json()["detail"]


def test_thieu_ma_ban_ghi_thi_tu_choi(_startup):
    r = tai("ketoan", "a.png", ANH, dtid="  ")
    assert r.status_code == 422


# ---------------------------------------------------------------- Thu hồi
def test_go_tep_phai_ghi_ly_do_va_khong_xoa_cung(_startup):
    r = tai("ketoan", "nham.png", ANH + b"khac", dtid="9")
    aid = r.json()["id"]
    assert client.post(f"/api/v1/tep/{aid}/thu-hoi", headers=login("ketoan"),
                       json={"ly_do": ""}).status_code == 422
    r2 = client.post(f"/api/v1/tep/{aid}/thu-hoi", headers=login("ketoan"),
                     json={"ly_do": "Gắn nhầm sang chuyến khác"})
    assert r2.status_code == 200 and r2.json()["thu_hoi"] is True
    con = client.get("/api/v1/tep?doi_tuong=chuyen_xe&doi_tuong_id=9", headers=login("ketoan")).json()
    assert con == []
    ke_ca = client.get("/api/v1/tep?doi_tuong=chuyen_xe&doi_tuong_id=9&ke_ca_thu_hoi=true",
                       headers=login("ketoan")).json()
    assert len(ke_ca) == 1 and ke_ca[0]["ly_do_thu_hoi"] == "Gắn nhầm sang chuyến khác"
    assert client.get(f"/api/v1/tep/{aid}/tai", headers=login("ketoan")).status_code == 200, \
        "bản ghi thu hồi vẫn phải đọc lại được để đối chiếu"


def test_gan_lai_tep_da_thu_hoi_thi_giu_dau_vet(_startup):
    """Gắn lại không được xóa lịch sử: người đọc hồ sơ phải thấy tệp này từng bị gỡ và vì sao."""
    r = tai("ketoan", "nham.png", ANH + b"khac", dtid="9")
    assert r.status_code == 201 and r.json()["thu_hoi"] is False
    assert "trước đó thu hồi vì" in r.json()["mo_ta"]


def test_go_hai_lan_thi_bao_ra(_startup):
    ds = client.get("/api/v1/tep?doi_tuong=chuyen_xe&doi_tuong_id=2", headers=login("ketoan")).json()
    aid = ds[0]["id"]
    assert client.post(f"/api/v1/tep/{aid}/thu-hoi", headers=login("ketoan"),
                       json={"ly_do": "x"}).status_code == 200
    assert client.post(f"/api/v1/tep/{aid}/thu-hoi", headers=login("ketoan"),
                       json={"ly_do": "x"}).status_code == 422


# ---------------------------------------------------------------- Toàn vẹn
def test_noi_dung_bi_doi_thi_bao_loi_chu_khong_tra_ve(_startup):
    """Trả về nội dung "gần đúng" cho một hồ sơ pháp lý tệ hơn hẳn việc báo lỗi rõ ràng."""
    from app.db.session import SessionLocal
    from app.models.attachments import Attachment
    from app.services.storage import storage
    from sqlalchemy import select
    with SessionLocal() as db:
        a = db.execute(select(Attachment).where(Attachment.doi_tuong_id == "1")).scalars().first()
        storage().put(a.khoa_luu, b"noi dung da bi thay the", "image/png")
        aid = a.id
    r = client.get(f"/api/v1/tep/{aid}/tai", headers=login("ketoan"))
    assert r.status_code == 503 and "không khớp mã kiểm tra" in r.json()["detail"]


# ---------------------------------------------------------------- Phân quyền
def test_go_tep_hep_hon_gan_tep(_startup):
    """Ai cũng gắn được chứng từ vào hồ sơ mình xử lý; gỡ chứng từ ra thì không."""
    r = tai("kd.hoa", "bien_lai.png", ANH + b"kd", doi_tuong="booking", dtid="1")
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert client.post(f"/api/v1/tep/{aid}/thu-hoi", headers=login("kd.hoa"),
                       json={"ly_do": "thử gỡ"}).status_code == 403


# ------------------------------------------- Khế ước vay (rà soát cửa 09/9)
def test_khe_uoc_vay_gan_duoc_ban_goc():
    """Bộ nạp Excel chỉ mang được các CON SỐ của khế ước.

    Lúc đối chiếu dư nợ với ngân hàng, thứ phải mở ra là bản gốc có chữ ký và dấu – không phải một dòng
    số. Trước 09/9 không có đối tượng nào để gắn nó vào, nên bản gốc nằm ở máy của kế toán.
    """
    r = tai("ketoan", "khe_uoc_2026.pdf", b"%PDF-1.4 khe uoc thu", doi_tuong="khe_uoc_vay",
            dtid="HD-VAY-001", loai="hop_dong", kieu="application/pdf")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["moi"] is True
    ds = client.get("/api/v1/tep?doi_tuong=khe_uoc_vay&doi_tuong_id=HD-VAY-001",
                    headers=login("ketoan")).json()
    assert len(ds) == 1 and ds[0]["ten_tep"] == "khe_uoc_2026.pdf"


def test_khe_uoc_vay_xep_vao_nhom_ngan_hang_va_luu_theo_ma_khe_uoc():
    """Xếp theo THÁNG KÝ thì phụ lục gia hạn năm sau nằm ở thư mục khác với khế ước gốc – một khế ước
    sống nhiều năm, hồ sơ của nó phải nằm cùng một chỗ."""
    d = client.get("/api/v1/tep/cau-hinh", headers=login("ketoan")).json()
    kv = [x for x in d["doi_tuong"] if x["ma"] == "khe_uoc_vay"]
    assert kv, "chưa khai đối tượng khe_uoc_vay"
    assert kv[0]["nhom_ho_so"] == "04_Ngan_hang_Vay"
    assert kv[0]["luu_theo"] == "đối tượng"
    assert kv[0]["nhay_cam"] is False, "khế ước vay không phải dữ liệu cá nhân – không gắn nhãn nhạy cảm"
