"""K11 – bộ kiểm độ dài dữ liệu và toàn vẹn của dữ liệu nạp mặc định.

Lý do có tệp này: phép thử chạy SQLite, máy chủ chạy PostgreSQL. SQLite nhận 300 ký tự vào cột khai
String(120) và không bật ràng buộc khoá ngoại – nên một hàm nạp mặc định sai vẫn xanh ở đây rồi làm
container không khởi động được trên máy chủ. Bộ kiểm này lấp đúng khoảng trống đó.

  KD1 dữ liệu nạp mặc định không có chuỗi nào vượt giới hạn cột
  KD2 giới hạn ĐỌC TỪ MÔ HÌNH, không chép số vào phép thử
  KD3 gài một chuỗi quá dài vào dữ liệu nạp thì bộ kiểm bắt được – và giới hạn nó báo đúng bằng mô hình
  KD4 khoá ngoại trỏ tới dòng không tồn tại thì bắt được
  KD5 khoá ngoại tự trỏ về chính bảng mình KHÔNG được báo nhầm
  KD6 cột bắt buộc mà để chuỗi trống thì bắt được
  KD7 bộ kiểm đã nối vào vòng quét của robot, không nằm chờ ai gọi tay
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_kd.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_kd.db"): os.remove("test_kd.db")
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _loai(thay, loai):
    return [t for t in thay if t["loai"] == loai]


def test_kd1_du_lieu_nap_mac_dinh_khong_co_chuoi_vuot_gioi_han():
    """Đây là phép thử chính. Nó đỏ nghĩa là bản nạp mặc định sẽ làm máy chủ thật không lên được."""
    from app.services import ks_do_dai as KD
    db = _db(); thay = KD.quet(db); db.close()
    xau = _loai(thay, "chuoi_qua_dai")
    assert not xau, "dữ liệu nạp mặc định có chuỗi dài quá cột: " + "; ".join(t["tom_tat"] for t in xau)
    assert not _loai(thay, "khoa_ngoai_treo"), \
        "; ".join(t["tom_tat"] for t in _loai(thay, "khoa_ngoai_treo"))
    assert not _loai(thay, "bat_buoc_de_trong"), \
        "; ".join(t["tom_tat"] for t in _loai(thay, "bat_buoc_de_trong"))


def test_kd2_gioi_han_doc_tu_mo_hinh_khong_chep_so_vao_phep_thu():
    """Con số giới hạn phải lấy từ chính mô hình. Chép số vào phép thử thì đổi mô hình phép thử vẫn xanh."""
    from app.services import ks_do_dai as KD
    from app.models.cskh import CareTicket
    from app.models.core import Company
    gh = KD.gioi_han()
    assert gh["care_tickets"]["customer_name"] == CareTicket.__table__.c.customer_name.type.length
    assert gh["companies"]["code"] == Company.__table__.c.code.type.length
    # đo đủ rộng: nếu chỉ nhìn thấy vài bảng thì nó đang báo "không sai" vì chưa nhìn thấy gì
    assert len(gh) > 50 and sum(len(v) for v in gh.values()) > 300


def test_kd3_gai_chuoi_qua_dai_thi_bo_kiem_bat_duoc():
    """Thử ngược để chắc nó canh thật – gài vào đúng một dòng do hàm nạp mặc định sinh ra."""
    from sqlalchemy import select
    from app.services import ks_do_dai as KD
    from app.models.core import Company
    db = _db()
    n = Company.__table__.c.name.type.length
    c = db.execute(select(Company).where(Company.code == "VTD")).scalars().first()
    goc = c.name
    c.name = "X" * (n + 7); db.commit()
    try:
        thay = _loai(KD.quet(db), "chuoi_qua_dai")
        assert len(thay) == 1 and thay[0]["doi_tuong"] == "companies.name"
        assert thay[0]["chi_tiet"]["gioi_han"] == n, "giới hạn báo ra phải đúng bằng mô hình"
        assert thay[0]["chi_tiet"]["dai_nhat"] == n + 7
    finally:
        c.name = goc; db.commit()
    assert not _loai(KD.quet(db), "chuoi_qua_dai")
    db.close()


def test_kd4_khoa_ngoai_tro_toi_dong_khong_ton_tai_thi_bat_duoc():
    """SQLite không bật ràng buộc khoá ngoại; PostgreSQL bật. Không có phép thử này thì lỗi chỉ lộ khi đẩy lên."""
    from sqlalchemy import select
    from app.services import ks_do_dai as KD
    from app.models.core import Company
    db = _db()
    c = db.execute(select(Company).where(Company.code == "VTRIP-VT")).scalars().first()
    goc = c.parent_id
    c.parent_id = 987654; db.commit()
    try:
        thay = _loai(KD.quet(db), "khoa_ngoai_treo")
        assert any(t["doi_tuong"] == "companies.parent_id" for t in thay), thay
    finally:
        c.parent_id = goc; db.commit()
    assert not _loai(KD.quet(db), "khoa_ngoai_treo")
    db.close()


def test_kd5_khoa_ngoai_tu_tro_ve_chinh_bang_minh_khong_duoc_bao_nham():
    """companies.parent_id → companies.id. Không đặt bí danh cho bảng cha thì câu con thành
    "id = parent_id" trên cùng một dòng: luôn sai, và bộ kiểm báo treo cả bảng dữ liệu đúng.
    Đây là lỗi bộ kiểm mắc ở lần chạy đầu tiên – giữ phép thử để nó không quay lại."""
    from sqlalchemy import select, func
    from app.services import ks_do_dai as KD
    from app.models.core import Company
    db = _db()
    co_cha = db.execute(select(func.count()).select_from(Company).where(
        Company.parent_id.isnot(None))).scalar()
    assert co_cha >= 5, "phải có sẵn công ty con trỏ về công ty mẹ thì phép thử này mới kiểm được gì"
    assert not _loai(KD.quet(db), "khoa_ngoai_treo")
    db.close()


def test_kd6_cot_bat_buoc_de_chuoi_trong_thi_bat_duoc():
    """Cột không cho rỗng và không khai mặc định = mô hình đang nói "phải có người điền"."""
    from sqlalchemy import select
    from app.services import ks_do_dai as KD
    from app.models.core import Company
    db = _db()
    assert "code" in KD.cot_bat_buoc()["companies"]
    c = db.execute(select(Company).where(Company.code == "LAVENDER")).scalars().first()
    goc = c.code
    c.code = "   "; db.commit()
    try:
        thay = _loai(KD.quet(db), "bat_buoc_de_trong")
        assert any(t["doi_tuong"] == "companies.code" for t in thay), thay
    finally:
        c.code = goc; db.commit()
    assert not _loai(KD.quet(db), "bat_buoc_de_trong")
    db.close()


def test_kd7_da_noi_vao_vong_quet_cua_robot():
    """Bộ kiểm không nằm chờ ai gọi tay. Không nối vào BO_KIEM thì nó chỉ là mã chết."""
    from app.services import ks_robot as KS
    from app.services.ks_do_dai import _do_dai_du_lieu
    assert _do_dai_du_lieu in KS.BO_KIEM
    from app.models.kiem_soat import LOAI_PHAT_HIEN
    for l in ("chuoi_qua_dai", "khoa_ngoai_treo", "bat_buoc_de_trong"):
        assert l in LOAI_PHAT_HIEN, f"loại {l} chưa khai tên tiếng Việt – màn hình sẽ hiện mã trần"
