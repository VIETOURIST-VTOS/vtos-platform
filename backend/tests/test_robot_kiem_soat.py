"""Robot Kiểm soát – vị trí Kiểm soát do AI giữ (chỉ đạo 07/9/2026).

Ba phép thử quan trọng nhất:
  - test_robot_khong_sua_duoc_so_cua_phong_ban: quyền ghi mở đúng ba cửa, không mở nguyên tắc.
  - test_khong_du_du_lieu_thi_khong_cham_0: chấm 0 cho phòng chưa có số là vu oan bằng số học.
  - test_chi_bao_cao_khi_co_viec_nghiem_trong: không có bản định kỳ, đúng chỉ đạo.
"""
import os, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:///./test_robot_kiem_soat.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_robot_kiem_soat.db", "test_robot_kiem_soat.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, AuditLog
from app.models.kiem_soat import KsPhatHien, KsDiem, KsBaoCao
from app.services import ks_robot as KS

client = TestClient(app)
MK = "robot123456"


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for vai in ("bks", "chutich", "cntt", "nv_kd", "ketoan"):
            un = f"ks_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


def login(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"ks_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


# ------------------------------------------------------------------ nguyên tắc
def test_robot_khong_sua_duoc_so_cua_phong_ban():
    """Ban Kiểm soát nay ghi được, nhưng ghi được ĐÚNG BA CỬA. Đây là phép thử giữ cho việc nới quyền
    hôm nay không lặng lẽ nở ra thành quyền sửa dữ liệu nghiệp vụ."""
    from app.services.access import WRITE_ALLOWED_FOR_READ_ONLY as W
    assert "/api/v1/kiem-soat/quet" in W and "/api/v1/kiem-soat/cham-diem" in W
    assert "/api/v1/ngoai-le/ghi" in W
    # Mở việc ra được, ĐÓNG lại thì không – đóng là quyền của người.
    assert "/api/v1/ngoai-le/dong" not in W
    for cam in ("/api/v1/tours", "/api/v1/bookings", "/api/v1/expenses", "/api/v1/payroll",
                "/api/v1/params", "/api/v1/access", "/api/v1/accounting"):
        assert not any(w.startswith(cam) for w in W), f"robot Kiểm soát không được ghi vào {cam}"


def test_bks_bi_chan_moi_thao_tac_ghi_nghiep_vu():
    h = login("bks")
    for path, body in (("/api/v1/tours", {}), ("/api/v1/ngoai-le/dong", {"ma": "x#1"}),
                       ("/api/v1/kiem-soat/hau-kiem-diem", {"diem_id": 1, "chap_nhan": True})):
        assert client.post(path, headers=h, json=body).status_code == 403, f"bks ghi được {path}"


def test_bks_chay_duoc_quet_va_cham_diem():
    h = login("bks")
    assert client.post("/api/v1/kiem-soat/quet", headers=h).status_code == 200
    assert client.post("/api/v1/kiem-soat/cham-diem", headers=h).status_code == 200


def test_phan_quyen_man_hinh_kiem_soat():
    for vai in ("chutich", "bks", "cntt"):
        assert client.get("/api/v1/kiem-soat", headers=login(vai)).status_code == 200
    for vai in ("nv_kd", "ketoan"):
        assert client.get("/api/v1/kiem-soat", headers=login(vai)).status_code == 403


# ------------------------------------------------------------------ quét
def test_quet_khong_de_ra_ban_trung_khi_chay_lai():
    db = db_()
    KS.quet(db); n1 = len(db.execute(select(KsPhatHien)).scalars().all())
    KS.quet(db); n2 = len(db.execute(select(KsPhatHien)).scalars().all())
    db.close()
    assert n1 == n2, "chạy lại vòng quét không được đẻ ra bản ghi trùng"


def test_quet_de_lai_vet_o_nhat_ky_bat_bien():
    db = db_(); KS.quet(db)
    hd = {a for a in db.execute(select(AuditLog.action)).scalars()}; db.close()
    assert "robot_ks_quet" in hd


def test_mot_bo_kiem_hong_khong_lam_trang_ca_vong_quet():
    """Robot mà im lặng khi hỏng thì tệ hơn robot báo sai: nó tạo cảm giác mọi thứ đều ổn."""
    db = db_()
    goc = KS.BO_KIEM
    def _no(_db=None): raise RuntimeError("bộ kiểm hỏng thử")
    try:
        KS.BO_KIEM = goc + (_no,)
        kq = KS.quet(db)
    finally:
        KS.BO_KIEM = goc
    db.close()
    assert kq["loi_bo_kiem"], "bộ kiểm hỏng phải được nêu trong kết quả, không được nuốt"


# ------------------------------------------------------------------ chấm điểm
def test_khong_du_du_lieu_thi_khong_cham_0():
    db = db_()
    kq = KS.cham_diem(db); db.close()
    thieu = [r for r in kq["rows"] if not r["du_co_so"]]
    assert thieu, "dữ liệu mẫu phải có ít nhất một phòng chưa đủ cơ sở chấm"
    for r in thieu:
        assert r["diem"] is None, "phòng chưa đủ số liệu phải để RỖNG, không phải chấm 0 như làm kém"
        assert "chưa đủ cơ sở" in r["nhan_xet"].lower()


def test_diem_may_cham_luon_o_trang_thai_cho_hau_kiem():
    db = db_(); KS.cham_diem(db)
    for d in db.execute(select(KsDiem)).scalars():
        assert d.trang_thai == "cho_hau_kiem"
    db.close()


def test_cham_diem_de_lai_vet_o_nhat_ky_ai_muc_3():
    """Chấm điểm con người là ô rủi ro cao nhất trong bảng quyền AI – phải có vết và phải chờ hậu kiểm."""
    from app.models.core import AiRun
    db = db_(); KS.cham_diem(db)
    r = db.execute(select(AiRun).where(AiRun.tac_vu == "cham_diem")).scalars().all(); db.close()
    assert r, "chấm điểm không để lại vết ở nhật ký AI"
    assert r[-1].muc == 3 and r[-1].trang_thai == "cho_hau_kiem"


def test_chu_tich_hau_kiem_duoc_diem():
    db = db_(); KS.cham_diem(db)
    d = db.execute(select(KsDiem)).scalars().first(); did = d.id; db.close()
    h = login("chutich")
    r = client.post("/api/v1/kiem-soat/hau-kiem-diem", headers=h,
                    json={"diem_id": did, "chap_nhan": False, "ghi_chu": "Chưa phản ánh đúng khối lượng việc"})
    assert r.status_code == 200, r.text
    db = db_(); d = db.get(KsDiem, did); tt, gc = d.trang_thai, d.hau_kiem_ghi_chu; db.close()
    assert tt == "bac" and gc


# ------------------------------------------------------------------ báo cáo
def test_chi_bao_cao_khi_co_viec_nghiem_trong():
    """Anh Tuấn chốt: không báo cáo định kỳ. Quét mà không có việc đỏ MỚI thì không sinh báo cáo."""
    db = db_()
    KS.quet(db)                                    # lần đầu: có thể sinh báo cáo
    truoc = len(db.execute(select(KsBaoCao)).scalars().all())
    KS.quet(db); KS.quet(db)                       # hai lần nữa, không có việc đỏ MỚI
    sau = len(db.execute(select(KsBaoCao)).scalars().all())
    db.close()
    assert sau == truoc, "quét lại mà không có việc nghiêm trọng mới thì không được sinh thêm báo cáo"


def test_bao_cao_moi_sinh_ra_khi_co_viec_do_moi():
    db = db_()
    truoc = len(db.execute(select(KsBaoCao)).scalars().all())
    db.add(KsPhatHien(ma="thu#do_moi", loai="may_chu_loi", muc="do", phong_ban="Kiểm thử",
                      tom_tat="Việc đỏ dựng ra để thử đường báo cáo", con=True, da_bao_cao=False))
    db.commit()
    KS._bao_cao_neu_nghiem_trong(db, "robot_ks")
    sau = db.execute(select(KsBaoCao)).scalars().all()
    db.close()
    assert len(sau) == truoc + 1
    assert "Việc đỏ dựng ra để thử" in sau[-1].noi_dung


# ------------------------------------------------------------------ nối vào Ngoại lệ
def test_phat_hien_cua_robot_hien_o_man_hinh_ngoai_le():
    """Robot mở việc ra ở ĐÚNG cửa phòng ban đã dùng, không dựng hàng đợi thứ hai."""
    from app.services import ngoai_le as NL
    db = db_()
    db.add(KsPhatHien(ma="thu#hien_o_ngoai_le", loai="quyen_lech", muc="do", phong_ban="Kiểm thử",
                      tom_tat="Việc thử phải hiện ở màn hình Ngoại lệ", con=True))
    db.commit()
    ds = NL.danh_sach(db, cat_moi_loai=0)["rows"]; db.close()
    r = [x for x in ds if x["loai"] == "ks_phat_hien" and "hiện ở màn hình Ngoại lệ" in x["tom_tat"]]
    assert r, "phát hiện của robot không hiện ở màn hình Ngoại lệ"
    assert r[0]["nguoi_quyet"] == "" and r[0]["thieu_chu_ky"] is True


# ------------------------------------------------------------------ quyền AI
def test_vi_tri_kiem_soat_khai_dung_bang_quyen_ai():
    from app.services import ai_quyen as AQ
    db = db_(); AQ.nap_mac_dinh(db); db.commit()
    for tac_vu in ("hoi_dap", "vb_noi_bo", "cham_diem"):
        muc = AQ.muc_cua(db, "bks", tac_vu)
        assert muc == 3, f"bks/{tac_vu} phải ở mức 3, đang {muc}"
        from app.models.core import AiPosition
        pos = db.execute(select(AiPosition).where(AiPosition.vai_tro == "bks",
                                                  AiPosition.tac_vu == tac_vu)).scalars().first()
        assert not AQ.thieu_han_muc(pos.muc, pos.han_muc), f"bks/{tac_vu} mức 3 mà thiếu hạn mức"
    # Người đi giám sát không nói chuyện với khách hàng.
    assert AQ.muc_cua(db, "bks", "tin_khach") == 0
    from app.models.core import AiPosition
    p = db.execute(select(AiPosition).where(AiPosition.vai_tro == "bks",
                                            AiPosition.tac_vu == "cham_diem")).scalars().first()
    db.close()
    assert p.han_muc.get("nguoi_hau_kiem") == "chutich", "điểm phòng ban phải do Chủ tịch hậu kiểm"


def test_menu_kiem_soat_theo_dung_ma_tran():
    from app.services.access import MENU_ROLES
    assert "/kiem-soat" in MENU_ROLES
    for vai in ("chutich", "tgd", "bks", "cntt"): assert vai in MENU_ROLES["/kiem-soat"]
    for vai in ("nv_kd", "ketoan", "hcns", "tp_dh"): assert vai not in MENU_ROLES["/kiem-soat"]
