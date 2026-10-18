# -*- coding: utf-8 -*-
"""BĐ-1 · Báo động khủng hoảng: phút 0 báo Chủ tịch, phút 15 đánh thức thêm người.

Ba điều vòng này phải giữ, và phép thử ở đây canh đúng ba điều ấy:

  1. HAI NGƯỠNG. Trên ngưỡng thường thì chỉ vào hàng chờ người đọc. Trên ngưỡng ĐỎ, hoặc gặp DỐC,
     thì reo chuông ngay — vì ngoài giờ không có người trực Marketing để đọc hàng đợi.

  2. LEO THANG MỘT LẦN. Phút 15 chưa ai bấm nhận thì báo thêm TGĐ và P.TGĐ Marketing, rồi THÔI.
     Một cửa báo động gửi lại mỗi phút là một cửa bị tắt vào sáng hôm sau.

  3. SỔ GHI CẢ THẤT BẠI. Người chưa nối Zalo phải thành một hàng `thanh_cong=False` có lý do, chứ
     không được bỏ qua im lặng — nếu không, bảng điều khiển sẽ hiện "đã gửi 3/3" trong khi thực ra
     không máy nào kêu.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_bd1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_bd1.db", "test_bd1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import inspect  # noqa: E402
import pathlib  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.bao_dong import CanhBaoGui  # noqa: E402
from app.models.core import Alert, User  # noqa: E402
from app.models.zalo_noi import ZaloNoiTaiKhoan  # noqa: E402
from app.services import bao_dong_khung_hoang as BD  # noqa: E402

Base.metadata.create_all(engine)

BANG = (CanhBaoGui, ZaloNoiTaiKhoan, Alert, User)


@pytest.fixture()
def db():
    s = SessionLocal()
    for M in BANG:
        s.query(M).delete()
    s.commit()
    yield s
    for M in BANG:
        s.query(M).delete()
    s.commit()
    s.close()


def nguoi(db, ten, vai, uid=""):
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x")
    db.add(u)
    db.flush()
    if uid:
        db.add(ZaloNoiTaiKhoan(user_id=u.id, zalo_uid=uid, gan_boi=ten))
        db.flush()
    return u


def ba_lanh_dao(db, noi_zalo=()):
    return [nguoi(db, t, v, f"uid-{t}" if v in noi_zalo else "")
            for t, v in (("tuan", "chutich"), ("tgd1", "tgd"), ("mkt1", "ptgd_mkt"))]


def canh_bao(db, luc=None, message="[VTOS] thu"):
    a = Alert(kind=BD.KIND, level="red", ref="tin:1", message=message,
              to_roles="chutich,tgd,ptgd_mkt", gom_khoa="khung_hoang:tin:1",
              created_at=luc or datetime.now(), trang_thai="moi")
    db.add(a)
    db.flush()
    return a


# =============================================================================================
# A. HAI NGƯỠNG
# =============================================================================================
def test_A1_duoi_nguong_do_thi_khong_reo_chuong():
    """Trên ngưỡng thường mà dưới ngưỡng ĐỎ thì chỉ vào hàng chờ — không đánh thức ai."""
    assert BD.dang_do({"diem": 3, "ly_do": ["Từ đỏ: kien"]}, 4) is False


def test_A2_tu_nguong_do_tro_len_thi_reo():
    assert BD.dang_do({"diem": 4, "ly_do": []}, 4) is True
    assert BD.dang_do({"diem": 9, "ly_do": []}, 4) is True


def test_A3_doc_reo_chuong_du_diem_chua_toi_nguong():
    """Mười người cùng viết một câu nhẹ dưới một bài trong một giờ là một làn sóng; mười câu ấy
    chấm riêng lẻ thì câu nào cũng hiền. Nên DỐC reo dù điểm thấp."""
    assert BD.dang_do({"diem": 1, "ly_do": ["Dốc: 7 tin trong 60 phút"]}, 4) is True


def test_A4_ly_do_khac_khong_lam_reo_nham():
    assert BD.dang_do({"diem": 1, "ly_do": ["Từ đỏ: to", "Quá hạn trả lời"]}, 4) is False


# =============================================================================================
# B. GỬI — VÀ SỔ PHẢI GHI CẢ LẦN KHÔNG GỬI ĐƯỢC
# =============================================================================================
def test_B1_nguoi_chua_noi_zalo_van_co_hang_trong_so(db, monkeypatch):
    """Đây là phép thử quan trọng nhất của tệp này.

    Bỏ qua im lặng người chưa nối máy thì hệ sẽ báo "đã gửi cho 3/3 lãnh đạo" trong khi chỉ 2 máy
    kêu, và không ai biết người thứ ba chưa bao giờ nhận được gì.
    """
    ba_lanh_dao(db, noi_zalo=("chutich",))
    monkeypatch.setattr(BD, "kenh", lambda _db: ["zalo_oa"])
    monkeypatch.setattr(BD.ZL, "send_oa_text", lambda _db, _uid, _t: {"error": 0, "data": {"message_id": "m1"}})
    a = canh_bao(db)

    BD.gui_vong(db, a, ("chutich", "tgd", "ptgd_mkt"), 0)
    hang = list(db.execute(select(CanhBaoGui).where(CanhBaoGui.alert_id == a.id)).scalars())

    assert len(hang) == 3, "phải có đúng một hàng cho MỖI người phải báo, kể cả người chưa nối"
    hong = [g for g in hang if not g.thanh_cong]
    assert len(hong) == 2
    assert all(g.ly_do == "chua_noi_zalo" for g in hong), "thất bại phải có LÝ DO, không để trống"


def test_B2_mot_kenh_hong_khong_lam_chet_ca_luot_gui(db, monkeypatch):
    """Ba người × nhiều kênh: một lỗi mạng ở người đầu mà dừng cả vòng thì hai người sau không
    nhận được gì, và sổ cũng không ghi được vì sao."""
    ba_lanh_dao(db, noi_zalo=("chutich", "tgd", "ptgd_mkt"))
    monkeypatch.setattr(BD, "kenh", lambda _db: ["zalo_oa"])

    def gui(_db, uid, _t):
        if uid == "uid-tuan":
            raise RuntimeError("mang hong")
        return {"error": 0, "data": {"message_id": "m"}}

    monkeypatch.setattr(BD.ZL, "send_oa_text", gui)
    a = canh_bao(db)
    hang = BD.gui_vong(db, a, ("chutich", "tgd", "ptgd_mkt"), 0)

    assert len(hang) == 3
    assert sum(1 for g in hang if g.thanh_cong) == 2
    hong = [g for g in hang if not g.thanh_cong][0]
    assert hong.ly_do.startswith("loi_gui_zalo"), hong.ly_do


def test_B3_zalo_tra_ve_loi_thi_khong_duoc_tinh_la_thanh_cong(db, monkeypatch):
    """Zalo trả HTTP 200 kèm `error != 0` vẫn là KHÔNG gửi được. Đọc mã trả về chứ không đọc việc
    lời gọi có ném ngoại lệ hay không."""
    ba_lanh_dao(db, noi_zalo=("chutich",))
    monkeypatch.setattr(BD, "kenh", lambda _db: ["zalo_oa"])
    monkeypatch.setattr(BD.ZL, "send_oa_text", lambda _db, _u, _t: {"error": -213, "message": "User not follow OA"})
    a = canh_bao(db)
    g = [x for x in BD.gui_vong(db, a, ("chutich",), 0)][0]
    assert g.thanh_cong is False
    assert "zalo_tu_choi" in g.ly_do and "not follow" in g.ly_do


def test_B4_zns_va_email_bao_dung_ly_do_chua_dung_duoc(db, monkeypatch):
    """Hai kênh này chưa có ô nhập số điện thoại / email. Trạng thái ĐÚNG là thất bại CÓ LÝ DO —
    im lặng không gửi rồi để bảng hiện 100% thành công mới là cái sai."""
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["zns", "email"])
    monkeypatch.setattr(BD.ZL, "configured", lambda _db: {"zns_templates": {}})
    a = canh_bao(db)
    hang = BD.gui_vong(db, a, ("chutich",), 0)
    ly = sorted(g.ly_do for g in hang)
    # EM-1 (18/10/2026): email nay đọc `users.email_cong_viec`; người chưa có địa chỉ báo đúng thế.
    assert ly == ["chua_cau_hinh_mau_zns", "thieu_email_cong_viec"]
    assert all(not g.thanh_cong for g in hang)


def test_B5_loi_nhan_khong_mang_ten_hay_so_dien_thoai_khach(db):
    """Tin này đi RA NGOÀI VTOS. Nó chỉ cần nặng cỡ nào, ở đâu, và một đoạn trích."""
    d = {"diem": 7, "nguon": "tin", "nguon_id": 3, "kenh": "Zalo OA", "luc": "2026-09-19 22:00:00",
         "khach": "Nguyễn Văn A", "trich": "toi se kien cong ty"}
    t = BD.loi_nhan(d)
    assert "Nguyễn Văn A" not in t
    assert "toi se kien" in t and "7 điểm" in t


# =============================================================================================
# C. LEO THANG
# =============================================================================================
def test_C1_chua_qua_han_thi_khong_leo_thang(db, monkeypatch):
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong"])
    monkeypatch.setattr(BD, "phut_leo", lambda _db: 15)
    canh_bao(db, luc=datetime.now() - timedelta(minutes=5))
    assert BD.leo_thang(db)["leo_thang"] == 0


def test_C2_qua_han_chua_ai_nhan_thi_bao_them_hai_nguoi(db, monkeypatch):
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong"])
    monkeypatch.setattr(BD, "phut_leo", lambda _db: 15)
    a = canh_bao(db, luc=datetime.now() - timedelta(minutes=20))

    assert BD.leo_thang(db)["leo_thang"] == 1
    them = list(db.execute(select(CanhBaoGui).where(CanhBaoGui.alert_id == a.id,
                                                    CanhBaoGui.vong == 15)).scalars())
    vai = sorted(db.get(User, g.user_id).role for g in them)
    assert vai == ["ptgd_mkt", "tgd"], "vòng leo thang báo TGĐ và P.TGĐ Marketing, KHÔNG báo lại Chủ tịch"


def test_C3_leo_thang_chi_mot_lan_du_goi_bao_nhieu_lan(db, monkeypatch):
    """Không ai bấm nhận suốt đêm thì vẫn chỉ hai vòng. Gửi lại mỗi phút là cách chắc chắn nhất
    để sáng hôm sau người ta tắt chuông."""
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong"])
    monkeypatch.setattr(BD, "phut_leo", lambda _db: 15)
    a = canh_bao(db, luc=datetime.now() - timedelta(minutes=90))

    for _ in range(5):
        BD.leo_thang(db)
    n = len(list(db.execute(select(CanhBaoGui).where(CanhBaoGui.alert_id == a.id,
                                                     CanhBaoGui.vong == 15)).scalars()))
    assert n == 2, f"phải đúng 2 hàng (TGĐ + P.TGĐ MKT), thấy {n}"


def test_C4_da_co_nguoi_nhan_thi_khong_danh_thuc_them_ai(db, monkeypatch):
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong"])
    monkeypatch.setattr(BD, "phut_leo", lambda _db: 15)
    a = canh_bao(db, luc=datetime.now() - timedelta(minutes=40))
    u = db.execute(select(User).where(User.role == "chutich")).scalars().first()
    BD.nhan(db, a.id, u)

    assert BD.leo_thang(db)["leo_thang"] == 0


# =============================================================================================
# D. BẤM "ĐÃ NHẬN"
# =============================================================================================
def test_D1_nguoi_bam_thu_hai_khong_ghi_de_nguoi_thu_nhat(db):
    """Câu hỏi phép đo cần trả lời là 'bao lâu thì có NGƯỜI ĐẦU TIÊN nhận'. Ghi đè làm con số ấy
    biến mất."""
    tuan, tgd, mkt = ba_lanh_dao(db)
    a = canh_bao(db)
    r1 = BD.nhan(db, a.id, tuan)
    r2 = BD.nhan(db, a.id, tgd)

    assert r1["ok"] is True
    assert r2["ok"] is False and r2["ly_do"] == "da_co_nguoi_nhan"
    assert db.get(Alert, a.id).nguoi_nhan_id == tuan.id


def test_D2_nhan_xong_thi_trang_thai_doi_sang_dang_xu_ly(db):
    tuan, _t, _m = ba_lanh_dao(db)
    a = canh_bao(db)
    BD.nhan(db, a.id, tuan)
    assert db.get(Alert, a.id).trang_thai == "dang_xu_ly"


def test_D3_khong_nhan_duoc_canh_bao_loai_khac(db):
    """Nút này chỉ dành cho cảnh báo khủng hoảng — bấm nhầm sang cảnh báo dòng tiền là sửa sổ của
    người khác."""
    tuan, _t, _m = ba_lanh_dao(db)
    a = Alert(kind="d7", level="red", ref="X", message="khac", to_roles="chutich")
    db.add(a)
    db.flush()
    assert BD.nhan(db, a.id, tuan)["ly_do"] == "khong_thay_canh_bao"


# =============================================================================================
# E. PHÉP ĐO CHÍNH CỬA BÁO ĐỘNG
# =============================================================================================
def test_E1_dem_dung_so_vu_khong_ai_bam_nhan(db, monkeypatch):
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong"])
    a1 = canh_bao(db)
    a2 = Alert(kind=BD.KIND, level="red", ref="tin:2", message="x", to_roles="chutich",
               gom_khoa="khung_hoang:tin:2", created_at=datetime.now(), trang_thai="moi")
    db.add(a2)
    db.flush()
    u = db.execute(select(User).where(User.role == "chutich")).scalars().first()
    BD.nhan(db, a1.id, u)

    do = BD.do_bao_dong(db)
    assert do["tong_vu"] == 2
    assert do["khong_ai_bam_nhan"] == 1


def test_E2_phut_trung_binh_toi_luc_nhan(db):
    ba_lanh_dao(db)
    gio = datetime.now()
    a = canh_bao(db, luc=gio - timedelta(minutes=8))
    u = db.execute(select(User).where(User.role == "chutich")).scalars().first()
    BD.nhan(db, a.id, u, bay_gio=gio)

    assert 7.5 <= BD.do_bao_dong(db)["phut_trung_binh_toi_luc_nhan"] <= 8.5


def test_E3_chuong_khong_duoc_tinh_la_toi_duoc_dien_thoai(db, monkeypatch):
    """CHỖ NÀY LÀ CHỖ DỄ TỰ LỪA NHẤT.

    Chuông trong VTOS luôn "gửi thành công" vì gửi chuông chỉ là ghi một dòng. 2 giờ sáng không ai
    mở máy tính, nên nếu đếm chung thì mọi vụ sẽ hiện 100% thành công trong khi không ai được đánh
    thức.
    """
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong"])
    a = canh_bao(db)
    BD.gui_vong(db, a, ("chutich",), 0)

    do = BD.do_bao_dong(db)
    assert do["theo_kenh"]["chuong"]["thanh_cong"] == 1, "chuông vẫn ghi là gửi được"
    assert do["khong_kenh_nao_toi_may"] == 1, "nhưng KHÔNG được tính là tới điện thoại ai cả"


def test_E4_neu_zalo_toi_duoc_thi_vu_ay_khong_con_bi_dem_la_mu(db, monkeypatch):
    ba_lanh_dao(db, noi_zalo=("chutich",))
    monkeypatch.setattr(BD, "kenh", lambda _db: ["chuong", "zalo_oa"])
    monkeypatch.setattr(BD.ZL, "send_oa_text", lambda _db, _u, _t: {"error": 0, "data": {"message_id": "m"}})
    a = canh_bao(db)
    BD.gui_vong(db, a, ("chutich",), 0)
    assert BD.do_bao_dong(db)["khong_kenh_nao_toi_may"] == 0


def test_E5_goi_ten_nguoi_chua_toi_duoc_chu_khong_chi_dem_so(db, monkeypatch):
    """Biết 'còn một người' mà không biết ai thì không sửa được."""
    ba_lanh_dao(db, noi_zalo=("chutich",))
    monkeypatch.setattr(BD, "kenh", lambda _db: ["zalo_oa"])
    monkeypatch.setattr(BD.ZL, "send_oa_text", lambda _db, _u, _t: {"error": 0, "data": {"message_id": "m"}})
    a = canh_bao(db)
    BD.gui_vong(db, a, ("chutich", "tgd", "ptgd_mkt"), 0)

    mu = BD.do_bao_dong(db)["nguoi_chua_toi_duoc"]
    assert sorted(x["username"] for x in mu) == ["mkt1", "tgd1"]
    assert all(x["da_noi_zalo"] is False for x in mu)


def test_E6_ly_do_that_bai_duoc_gom_lai_de_nhin(db, monkeypatch):
    """Cuối tháng phải đọc được 'kênh này hỏng vì cùng MỘT lý do', không phải lật từng hàng."""
    ba_lanh_dao(db)
    monkeypatch.setattr(BD, "kenh", lambda _db: ["zalo_oa"])
    a = canh_bao(db)
    BD.gui_vong(db, a, ("chutich", "tgd", "ptgd_mkt"), 0)
    assert BD.do_bao_dong(db)["theo_kenh"]["zalo_oa"]["ly_do"] == {"chua_noi_zalo": 3}


# =============================================================================================
# F. HÀNG RÀO ĐỌC MÃ NGUỒN
# =============================================================================================
def test_F1_khong_ket_luan_ho_la_khung_hoang(db):
    """Cửa này ĐÁNH THỨC người, nó KHÔNG tự đánh dấu 'là khủng hoảng' vào sổ PR — người quyết."""
    ma = pathlib.Path(inspect.getsourcefile(BD)).read_text(encoding="utf-8")
    assert "la_khung_hoang" not in ma, (
        "cửa báo động không được tự ghi kết luận vào sổ PR; nó chỉ đánh thức người để NGƯỜI quyết")


def test_F2_moi_kenh_that_bai_deu_phai_kem_ly_do(db):
    """Đọc mã: mọi nhánh trả False phải trả kèm một chuỗi lý do khác rỗng."""
    ma = pathlib.Path(inspect.getsourcefile(BD)).read_text(encoding="utf-8")
    assert 'return False, ""' not in ma, "có nhánh trả thất bại mà không nói vì sao"
