"""HD-BH1 — BÀN LÀM VIỆC CỦA PHÒNG HƯỚNG DẪN.

Đo được trên main eeca2da trước vòng này: `BAN` khai đúng HAI bàn, `dieu_hanh` và `doi_xe`.
Trưởng phòng Hướng dẫn gọi `/bao-cao/ban-lam-viec?phong=huong_dan` KHÔNG bị chặn — ông vào được —
nhưng nhận đúng câu *Phòng này chưa khai bàn làm việc*. Lớp quyền đã đúng; thứ thiếu là cái bàn.

  A. Bàn tồn tại, đúng người mở được, và không ô nào khai mà không có hàm dựng.
  B. Mỗi ô đếm đúng, và đếm CÙNG MỘT con số với màn hình nguồn.
  C. Ba luật của bàn làm việc vẫn còn: số 0 khác lỗi, một ô hỏng không kéo sập bàn, thiếu ô thì
     KHÔNG có tổng.
  D. Hàng rào cấu trúc: không ô nào tự viết lại phép lọc, và một mốc ngày chỉ khai một chỗ.

CÁCH ĐẾM CỦA BỘ NÀY: mọi ca đo BẰNG HIỆU SỐ — đọc ô trước khi dựng cảnh, dựng cảnh, đọc lại, so
phần chênh. Dữ liệu mẫu có sẵn bao nhiêu hồ sơ không ảnh hưởng, và ngày mai ai sửa `seed.py` cũng
không làm bộ này đỏ vì một lý do chẳng liên quan.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_bh1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_bh1.db"):
    os.remove("test_bh1.db")

from datetime import date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import ban_lam_viec as BLV  # noqa: E402

client = TestClient(app)
MK = "Vtos@Demo#2026"
TP = "tp_hd_bh1"
GD = "gd_doi_xe_bh1"


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import User
        with SessionLocal() as db:
            # Tên tài khoản mang mã đợt. Bài học Đợt HD-DG2: đặt tên chung thì bộ nào chạy sau
            # trong cùng một lượt sẽ sập ở bước dựng cảnh vì trùng tên, rồi đỏ hàng loạt vì một
            # lý do chẳng liên quan gì tới điều nó canh.
            for ten, vai in ((TP, "tp_hd"), (GD, "gd_doi_xe")):
                if db.execute(select(User).where(User.username == ten)).scalars().first() is None:
                    db.add(User(username=ten, full_name="Thử " + ten, role=vai,
                                department="Thử", password_hash=hash_password(MK)))
            db.commit()
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _h(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _so(khoa: str) -> int:
    """Số lượng của một ô trên bàn Hướng dẫn, đọc qua đúng hàm dựng bàn."""
    with _db() as db:
        for o in BLV.ban(db, "huong_dan")["o"]:
            if o["khoa"] == khoa:
                assert o["trang_thai"] == BLV.SAN_SANG, f"{khoa} đang {o['trang_thai']}: {o['ly_do']}"
                return o["so_luong"]
    raise AssertionError(f"Bàn Hướng dẫn không có ô {khoa}")


def _nv(db, ma, ten, het_han=date(2030, 1, 1), the="quoc_te", active=True):
    from app.models.hr import Employee
    e = Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                 start_date=date(2024, 1, 1), card_no=ma, card_type=the,
                 card_expiry=het_han, member_org=True, contract_type="ctv",
                 ctv_contract=True, active=active)
    db.add(e); db.commit()
    return e


def _tour(db, ma, loai="le_noi_dia", bat_dau=None):
    from sqlalchemy import select

    from app.models.core import Tour, User
    op = db.execute(select(User)).scalars().first()
    d = bat_dau or (date.today() + timedelta(days=20))
    t = Tour(code=ma, name="Chuyến " + ma, tour_type=loai, operator_id=op.id,
             start_date=d, end_date=d + timedelta(days=3))
    db.add(t); db.commit()
    return t


def _pc(db, tour, e, status="cho_xac_nhan", gio=True, han=None):
    from app.models.hr import GuideAssignment
    d = datetime.combine(tour.start_date, datetime.min.time()) + timedelta(hours=6)
    a = GuideAssignment(tour_id=tour.id, guide_id=e.id, days=3, rate_per_day=800_000,
                        status=status,
                        bat_dau=d if gio else None,
                        ket_thuc=(d + timedelta(days=3)) if gio else None,
                        han_tra_loi=han)
    db.add(a); db.commit()
    return a


# ═════════════════ A · bàn tồn tại và đúng người mở được ═════════════════

def test_a1_phong_huong_dan_DA_CO_ban_lam_viec():
    assert "huong_dan" in BLV.BAN, "Phòng Hướng dẫn vẫn chưa khai bàn làm việc"
    with _db() as db:
        kq = BLV.ban(db, "huong_dan")
    assert kq["co_ban"] is True
    assert kq["ten"]
    assert len(kq["o"]) == len(BLV.BAN["huong_dan"]["o"])


def test_a2_dung_nguoi_mo_duoc_va_nguoi_khac_bi_chan():
    """Phạm vi theo phòng đã chạy sẵn trong `bao_cao_phong.PHONG`; ca này canh để nó không bị
    nới ra nhân một đợt nào đó. Trưởng phòng Hướng dẫn KHÔNG được thấy bàn Đội xe và ngược lại."""
    h_tp, h_gd = _h(TP), _h(GD)
    r = client.get("/api/v1/bao-cao/ban-lam-viec?phong=huong_dan", headers=h_tp)
    assert r.status_code == 200 and r.json()["co_ban"] is True, r.text
    assert client.get("/api/v1/bao-cao/ban-lam-viec?phong=doi_xe",
                      headers=h_tp).status_code == 403
    assert client.get("/api/v1/bao-cao/ban-lam-viec?phong=huong_dan",
                      headers=h_gd).status_code == 403
    assert client.get("/api/v1/bao-cao/ban-lam-viec?phong=doi_xe",
                      headers=h_gd).status_code == 200


def test_a3_moi_o_khai_trong_BAN_deu_co_ham_dung():
    """Khai một ô mà quên viết hàm thì vòng lặp dựng bàn BỎ QUA nó — bàn thiếu một ô mà không ai
    báo, và tổng vẫn hiện ra như đủ."""
    thieu = [k for k in BLV.BAN["huong_dan"]["o"] if k not in BLV.O_HAM]
    assert not thieu, f"Ô khai mà không có hàm dựng, sẽ biến mất lặng lẽ: {thieu}"


# ═════════════════ B · mỗi ô đếm đúng ═════════════════

def test_b1_loi_chao_qua_han_dem_dung_cai_qua_han():
    truoc = _so("hdv_chao_qua_han")
    with _db() as db:
        e = _nv(db, "BH1-B1", "Người được chào")
        t1, t2 = _tour(db, "BH1-B1-T1"), _tour(db, "BH1-B1-T2")
        _pc(db, t1, e, han=datetime.now() - timedelta(days=5))     # quá hạn
        _pc(db, t2, e, han=datetime.now() + timedelta(days=5))     # còn hạn
    assert _so("hdv_chao_qua_han") == truoc + 1


def test_b2_chuyen_chua_co_nguoi_dem_GIONG_HET_man_hinh_nguon():
    """Hàng rào quan trọng nhất của nhóm này: ô trên bàn và cửa API phải ra CÙNG một con số.

    Lệch nhau là đúng cái luật đầu tệp `ban_lam_viec.py` cấm — hai chỗ cùng đếm một thứ thì người
    dùng tin con số dễ đọc chứ không tin con số đúng. Ca này gọi CẢ HAI rồi so, nên nó đỏ ngay
    ngày ai sửa một bên mà quên bên kia.
    """
    with _db() as db:
        e = _nv(db, "BH1-B2", "Người nhận")
        _tour(db, "BH1-B2-T0")                                     # chưa ai nhận
        t_huy = _tour(db, "BH1-B2-T1")
        _pc(db, t_huy, e, status="huy")                            # huỷ: VẪN tính là chưa có
        t_tu_choi = _tour(db, "BH1-B2-T2")
        _pc(db, t_tu_choi, e, status="tu_choi")                    # từ chối: tính là ĐÃ có
    tren_ban = _so("hdv_chuyen_chua_co_nguoi")
    r = client.get("/api/v1/huong-dan/chuyen-can-hdv?so_ngay=30", headers=_h(TP))
    assert r.status_code == 200, r.text
    assert tren_ban == len(r.json()), (
        f"Bàn đếm {tren_ban}, màn hình nguồn đếm {len(r.json())} — hai chỗ đang đếm hai kiểu")
    ma = {x["code"] for x in r.json()}
    assert "BH1-B2-T0" in ma and "BH1-B2-T1" in ma, "Chuyến bị huỷ lượt chào phải vẫn là chưa có người"
    assert "BH1-B2-T2" not in ma, "Chuyến đã có lượt chào bị từ chối KHÔNG đổi hành vi cũ"


def test_b3_the_het_han_va_sap_het_han_dem_ca_hai_nguoi_da_nghi_thi_khong():
    truoc = _so("hdv_the_sap_het_han")
    hom_nay = date.today()
    with _db() as db:
        _nv(db, "BH1-B3a", "Đã hết hạn", het_han=hom_nay - timedelta(days=10))
        _nv(db, "BH1-B3b", "Sắp hết hạn", het_han=hom_nay + timedelta(days=30))
        _nv(db, "BH1-B3c", "Còn lâu", het_han=hom_nay + timedelta(days=400))
        _nv(db, "BH1-B3d", "Đã nghỉ việc", het_han=hom_nay - timedelta(days=10), active=False)
    assert _so("hdv_the_sap_het_han") == truoc + 2, \
        "Phải đếm người ĐÃ hết hạn và người SẮP hết hạn, không đếm người còn lâu và người đã nghỉ"


def test_b4_phan_cong_thieu_gio_dem_dung():
    truoc = _so("hdv_phan_cong_thieu_gio")
    with _db() as db:
        e = _nv(db, "BH1-B4", "Người thiếu giờ")
        t1, t2, t3 = (_tour(db, "BH1-B4-T1"), _tour(db, "BH1-B4-T2"), _tour(db, "BH1-B4-T3"))
        _pc(db, t1, e, gio=False)                                  # thiếu giờ, còn chiếm lịch
        _pc(db, t2, e, gio=True)                                   # đủ giờ
        _pc(db, t3, e, gio=False, status="huy")                    # thiếu giờ nhưng đã huỷ
    assert _so("hdv_phan_cong_thieu_gio") == truoc + 1


def test_b5_pham_vi_lech_CHI_dem_nhom_khong_dat():
    """Hồ sơ chưa khai loại thẻ là việc phải NHẬP của HCNS, không phải việc phải XỬ của người
    điều phối. Đưa nó lên bàn là biến một ô còn trống thành một lời buộc tội — đúng điều Đợt
    HD-PV1 dựng ra để tránh."""
    truoc = _so("hdv_pham_vi_lech")
    with _db() as db:
        nd = _nv(db, "BH1-B5a", "Thẻ nội địa", the="noi_dia")
        trong = _nv(db, "BH1-B5b", "Chưa khai thẻ", the="")
        t1 = _tour(db, "BH1-B5-T1", loai="doan_nuoc_ngoai")
        t2 = _tour(db, "BH1-B5-T2", loai="doan_nuoc_ngoai")
        _pc(db, t1, nd)                                            # KHÔNG ĐẠT
        _pc(db, t2, trong)                                         # chưa kết luận được
    assert _so("hdv_pham_vi_lech") == truoc + 1, \
        "Ô này chỉ được đếm nhóm «không đạt», không gộp nhóm «chưa kết luận được»"
    # Cửa API thì vẫn trả đủ ba nhóm — hai chỗ, hai câu hỏi, và cả hai phải còn.
    r = client.get("/api/v1/huong-dan/pham-vi-the/lech", headers=_h(TP))
    assert r.status_code == 200
    assert r.json()["so_chua_ket_luan_duoc"] >= 1


# ═════════════════ C · ba luật của bàn làm việc ═════════════════

def test_c1_so_0_KHONG_bi_lan_voi_loi(monkeypatch):
    """Một ô đọc hỏng mà hiện «0 việc» là nói với trưởng phòng rằng hôm nay không có gì phải làm.

    BẢN ĐẦU CỦA CA NÀY KHÔNG CẮN, và đó là bài học đáng ghi hơn cả chính nó. Nó chỉ duyệt các ô
    trong trạng thái bình thường rồi viết `if trang_thai != SAN_SANG: ...` — mà ở lượt chạy bình
    thường không ô nào hỏng, nên nhánh ấy KHÔNG BAO GIỜ chạy. Phép đột biến đổi ô hỏng từ `None`
    sang `0` vẫn XANH. Một ca mang tên «số 0 không lẫn với lỗi» mà không hề nhìn thấy một ô lỗi
    nào. Nay nó TỰ LÀM HỎNG một ô rồi mới hỏi.
    """
    def no(db, cfg):
        raise RuntimeError("ô này cố tình hỏng để đo")
    monkeypatch.setitem(BLV.O_HAM, "hdv_the_sap_het_han", no)
    with _db() as db:
        o_het = [o for o in BLV.ban(db, "huong_dan")["o"]
                 if o["khoa"] == "hdv_the_sap_het_han"][0]
    assert o_het["trang_thai"] == BLV.LOI
    assert o_het["so_luong"] is None, \
        "Ô đọc hỏng phải ĐỂ TRỐNG. In 0 là nói hôm nay không có việc gì."
    # Và ở lượt bình thường, ô nào bằng 0 thì phải là 0 THẬT, không phải lỗi đội lốt.
    with _db() as db:
        for o in BLV.ban(db, "huong_dan")["o"]:
            if o["so_luong"] == 0:
                assert o["trang_thai"] == BLV.SAN_SANG


def test_c2_mot_o_hong_KHONG_keo_sap_ca_ban_va_thi_KHONG_co_tong(monkeypatch):
    def no(db):
        raise RuntimeError("ô này cố tình hỏng")
    monkeypatch.setitem(BLV.O_HAM, "hdv_chao_qua_han", lambda db, cfg: no(db))
    with _db() as db:
        kq = BLV.ban(db, "huong_dan")
    assert len(kq["o"]) == len(BLV.BAN["huong_dan"]["o"]), "Bàn mất ô khi một ô hỏng"
    hong = [o for o in kq["o"] if o["trang_thai"] == BLV.LOI]
    assert len(hong) == 1 and "cố tình hỏng" in hong[0]["ly_do"]
    assert kq["tong_dang_cho"] is None, "Thiếu một ô mà vẫn in tổng là in một con số thiếu"


def test_c3_mau_so_KHONG_cong_vao_tong():
    with _db() as db:
        kq = BLV.ban(db, "huong_dan")
    assert kq["tong_dang_cho"] is not None
    viec = sum(o["so_luong"] for o in kq["o"] if o["khoa"] not in BLV.MAU_SO)
    assert kq["tong_dang_cho"] == viec
    mau = [o for o in kq["o"] if o["khoa"] in BLV.MAU_SO]
    assert mau, "Bàn Hướng dẫn không có mẫu số nào – bốn con số trên không có gì để đọc cùng"
    assert all(o["so_luong"] is not None for o in mau)


# ═════════════════ D · hàng rào cấu trúc ═════════════════

def test_d1_moi_o_phai_noi_duoc_no_lay_so_tu_dau():
    """`nguon` là chỗ người đọc dò ngược con số. Một ô không nói nguồn là một con số không ai
    kiểm lại được, và con số không kiểm được thì vài tuần nữa không ai tin."""
    with _db() as db:
        for o in BLV.ban(db, "huong_dan")["o"]:
            assert o["nguon"].strip(), f"Ô {o['khoa']} không nói nguồn"
            assert o["den"].strip(), f"Ô {o['khoa']} không dẫn sang màn hình nào"
            assert o["nhan_muc"].strip(), f"Ô {o['khoa']} không có lời đọc kèm con số"


def test_d2_khong_o_nao_TU_VIET_LAI_phep_loc():
    """Canh bằng cây cú pháp. Mỗi hàm dựng ô của bàn Hướng dẫn phải GỌI một phép lọc đã công bố ở
    lớp dịch vụ. Tự viết lọc trong `ban_lam_viec.py` là dựng chỗ thứ hai, và hai chỗ rồi sẽ lệch."""
    import ast
    import inspect
    from pathlib import Path

    PHEP_LOC = {"loi_chao_qua_han", "chuyen_chua_co_nguoi", "the_sap_het_han",
                "phan_cong_thieu_gio", "pham_vi_lech", "guide_eligible"}
    cay = ast.parse(Path(inspect.getsourcefile(BLV)).read_text(encoding="utf-8"))
    ham = {n.name: n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name.startswith("_hdv_")}
    assert len(ham) == len(BLV.BAN["huong_dan"]["o"]), f"Tìm thấy {len(ham)} hàm ô"
    for ten, n in ham.items():
        goi = {getattr(g.func, "id", "") or getattr(g.func, "attr", "")
               for g in ast.walk(n) if isinstance(g, ast.Call)}
        assert goi & PHEP_LOC, f"{ten} không gọi phép lọc nào của lớp dịch vụ – nó tự lọc lấy"


def test_d3_moc_bao_truoc_han_the_chi_khai_MOT_cho():
    """Màn hình nguồn báo trước 60 ngày, bàn làm việc cũng phải 60. Hai hằng số rời nhau thì một
    ngày ai sửa một chỗ là hai màn hình nói hai điều khác nhau về cùng một người."""
    from app.api.v1 import huong_dan as API
    from app.services import hdv as HDV
    assert API.SAP_HET_HAN is HDV.SAP_HET_HAN_NGAY or API.SAP_HET_HAN == HDV.SAP_HET_HAN_NGAY
    import ast
    import inspect
    from pathlib import Path
    cay = ast.parse(Path(inspect.getsourcefile(API)).read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", "") == "SAP_HET_HAN" for t in n.targets):
            assert not isinstance(n.value, ast.Constant), \
                "SAP_HET_HAN lại được viết cứng một con số thay vì đọc từ services/hdv.py"
