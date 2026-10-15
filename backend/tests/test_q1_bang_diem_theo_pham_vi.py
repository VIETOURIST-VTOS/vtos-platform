"""HD-Q1 — BẢNG ĐIỂM THEO PHẠM VI QUẢN LÝ.

Đo được trên main c2e124d trước vòng này, đăng nhập thật bằng từng vai: nhân viên Marketing và
nhân viên Điều hành đọc được bảng điểm hướng dẫn viên LẪN bảng điểm tài xế, còn Trưởng phòng
Hướng dẫn và Giám đốc Đội xe — trưởng bộ phận của chính những người bị chấm — bị chặn 403 ở mọi
cửa của nhóm đánh giá.

  A. Vai trò → loại đối tượng. Không có loại hợp lệ thì TỪ CHỐI, không lùi về xem tất cả.
  B. Phạm vi phòng ban, và lọc TRƯỚC khi cộng chứ không giấu sau khi cộng.
  C. Quyền XEM không kéo theo quyền GHI.
  D. Màn hình và API mở cùng lúc, và bảng khai phạm vi không lệch với bảng phòng ban đã có.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_q1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_q1.db"):
    os.remove("test_q1.db")

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1 import danh_gia as API  # noqa: E402
from app.main import app  # noqa: E402
from app.services import danh_gia as DG  # noqa: E402

client = TestClient(app)
MK = "Vtos@Demo#2026"
TU, DEN = "2026-01-01", "2027-12-31"
D1, D2 = date(2026, 1, 1), date(2027, 12, 31)
ID: dict[str, int] = {}
# Tên tài khoản mang mã đợt — bài học HD-DG2: tên chung thì hai bộ chạy cùng lượt sập ở bước dựng.
AI = {"tp_hd": "tp_hd_q1", "gd_doi_xe": "gd_doi_xe_q1", "chutich": "chutich_q1"}


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import Booking, Tour, User
        from app.models.cskh import CareTicket
        from app.models.hr import Employee
        with SessionLocal() as db:
            for vai, ten in AI.items():
                if db.execute(select(User).where(User.username == ten)).scalars().first() is None:
                    db.add(User(username=ten, full_name="Thử " + ten, role=vai,
                                department="Thử", password_hash=hash_password(MK)))
            db.commit()
            op = db.execute(select(User)).scalars().first()

            def nv(ma, ten, phong, vi_tri):
                e = Employee(code=ma, full_name=ten, department=phong, position=vi_tri,
                             start_date=date(2024, 1, 1), card_no=ma, card_type="quoc_te",
                             card_expiry=date(2030, 1, 1), member_org=True,
                             contract_type="ctv", ctv_contract=True)
                db.add(e); db.commit()
                return e.id

            # Hai hướng dẫn viên THUỘC phòng Hướng dẫn, một người ở phòng KHÁC nhưng vẫn được
            # chấm loại «hdv» — ca này là chỗ phạm vi phải cắn.
            ID["trong_a"] = nv("Q1-A", "Trong phạm vi A", "huong_dan", "hdv")
            ID["trong_b"] = nv("Q1-B", "Trong phạm vi B", "huong_dan", "hdv")
            ID["ngoai"] = nv("Q1-X", "Ngoài phạm vi", "dieu_hanh", "hdv")
            ID["tx"] = nv("Q1-TX", "Tài xế trong đội", "doi_xe", "tai_xe")

            t = Tour(code="Q1-T", name="Chuyến thử", tour_type="le_noi_dia", operator_id=op.id,
                     start_date=date(2026, 11, 1), end_date=date(2026, 11, 3))
            db.add(t); db.commit()
            b = Booking(code="Q1-B", tour_id=t.id, customer_name="Khách", customer_phone="09",
                        pax=1, sales_id=op.id, created_by=op.id, request_id=0, source="thu")
            db.add(b); db.commit()
            care = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="Khách",
                              customer_phone="09", han_lien_he=date(2026, 11, 5))
            db.add(care); db.commit()
            ID["care"] = care.id

            from app.models.danh_gia import DanhGiaSauTour
            for khoa, diem, dt in (("trong_a", 5, "hdv"), ("trong_b", 1, "hdv"),
                                   ("ngoai", 5, "hdv"), ("tx", 4, "tai_xe")):
                db.add(DanhGiaSauTour(care_id=care.id, booking_id=b.id, tour_id=t.id,
                                      doi_tuong=dt, doi_tuong_id=ID[khoa], diem=diem,
                                      doi_tuong_ten="x", nguon="khach"))
            # Một lượt chấm loại «hdv» KHÔNG có khoá người — không quy được về phòng nào.
            db.add(DanhGiaSauTour(care_id=care.id, booking_id=b.id, tour_id=t.id,
                                  doi_tuong="hdv", doi_tuong_id=None, diem=2,
                                  doi_tuong_ten="Hướng dẫn viên", nguon="khach"))
            db.commit()
        yield


def _h(vai):
    r = client.post("/api/v1/auth/login", data={"username": AI[vai], "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _bd(vai, dt):
    return client.get(f"/api/v1/danh-gia/bang-diem/{dt}?tu={TU}&den={DEN}&chi_khach=false",
                      headers=_h(vai))


# ═════════ A · vai trò → loại đối tượng ═════════

def test_a1_tp_hd_xem_duoc_HDV_va_bi_chan_o_loai_khac():
    assert _bd("tp_hd", "hdv").status_code == 200
    for dt in ("tai_xe", "tour", "khach_san", "an_uong"):
        r = _bd("tp_hd", dt)
        assert r.status_code == 403, f"{dt}: {r.status_code}"
        assert "PHAM_VI_BANG_DIEM" in r.text


def test_a2_gd_doi_xe_xem_duoc_TAI_XE_va_bi_chan_o_loai_khac():
    assert _bd("gd_doi_xe", "tai_xe").status_code == 200
    for dt in ("hdv", "tour"):
        assert _bd("gd_doi_xe", dt).status_code == 403


def test_a3_loai_doi_tuong_khong_hop_le_thi_BAO_LOI_chu_khong_xem_tat_ca():
    """Một cổng mà lúc không khớp thì mở toang là một cổng chỉ tồn tại khi mọi thứ đã đúng."""
    for vai in ("tp_hd", "gd_doi_xe", "chutich"):
        r = _bd(vai, "khong_co_loai_nay")
        assert r.status_code in (403, 422), f"{vai}: {r.status_code} — {r.text[:120]}"
        assert "rows" not in r.text or r.json().get("rows") is None


def test_a4_vai_toan_cong_ty_KHONG_bi_bo_theo_phong():
    for dt in ("hdv", "tai_xe", "tour"):
        r = _bd("chutich", dt)
        assert r.status_code == 200, f"{dt}: {r.text[:120]}"
    assert _bd("chutich", "hdv").json()["chi_phong"] is None


# ═════════ B · phạm vi phòng ban ═════════

def test_b1_truong_phong_CHI_thay_nguoi_cua_phong_minh():
    ids = {r["id"] for r in _bd("tp_hd", "hdv").json()["rows"]}
    assert ID["trong_a"] in ids and ID["trong_b"] in ids
    assert ID["ngoai"] not in ids, "Người phòng khác lọt vào bảng của Trưởng phòng Hướng dẫn"


def test_b2_nhom_KHONG_CO_KHOA_nguoi_khong_lot_vao_bang_cua_truong_phong():
    """Không quy được về ai thì cũng không quy được về phòng nào."""
    d = _bd("tp_hd", "hdv").json()
    assert all(r["id"] is not None for r in d["rows"])
    # Nhưng người xem toàn công ty thì VẪN phải thấy nó, nếu không nó biến mất khỏi mọi màn hình.
    assert any(r["id"] is None for r in _bd("chutich", "hdv").json()["rows"])


def test_b3_bang_cua_truong_phong_bao_ro_no_dang_bi_bo_theo_phong_nao():
    assert _bd("tp_hd", "hdv").json()["chi_phong"] == "huong_dan"
    assert _bd("gd_doi_xe", "tai_xe").json()["chi_phong"] == "doi_xe"


def test_b4_loc_TRUOC_khi_cong_chu_khong_giau_sau_khi_cong():
    """Lọc sau khi cộng là vẫn cộng điểm người ngoài phạm vi rồi mới giấu dòng đi — lúc ấy số
    dòng thì đúng mà mọi con số tổng đều đã trộn người ngoài vào."""
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        trong = DG.bang_diem(db, "hdv", D1, D2, chi_khach=False, chi_phong="huong_dan")
        ca = DG.bang_diem(db, "hdv", D1, D2, chi_khach=False)
    assert sum(r["so_luot"] for r in trong["rows"]) == 2
    assert sum(r["so_luot"] for r in ca["rows"]) >= 4
    assert {r["id"] for r in trong["rows"]} == {ID["trong_a"], ID["trong_b"]}


def test_b5_loai_KHONG_thuoc_phong_nao_thi_bang_rong_va_NOI_RO_VI_SAO():
    """BẢN ĐẦU CỦA CA NÀY KHÔNG CẮN — ghi lại vì nó là lỗi «xanh vì may».

    Nó chỉ đòi bảng rỗng. Gỡ hẳn nhánh chặn sớm đi thì bảng VẪN rỗng, nhưng vì một lý do khác:
    loại không có khoá thì mọi dòng gộp theo TÊN, mã người là rỗng, và phép lọc theo phòng ở dưới
    loại sạch tất cả. Hai đường khác hẳn nhau, cùng ra một kết quả, nên phép đo không phân biệt
    được — đúng cái bẫy sổ Đợt QT-1 đã ghi.

    Thứ nhánh chặn sớm làm được mà đường kia KHÔNG: nó NÓI RA vì sao bảng rỗng. Một bảng trống
    không lời giải thích là «số 0 lẫn với lỗi» ở cấp màn hình — trưởng phòng mở ra, thấy trắng
    trơn, và không biết là chưa có ai chấm hay là mình không được xem.
    """
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        d = DG.bang_diem(db, "tour", D1, D2, chi_khach=False, chi_phong="huong_dan")
    assert d["rows"] == [], "Im lặng bỏ qua phạm vi là cách một cổng mở toang"
    assert "huong_dan" in d["luu_y"] and "phòng" in d["luu_y"].lower(), \
        f"Bảng rỗng mà không nói vì sao rỗng: {d['luu_y']!r}"


# ═════════ C · xem không kéo theo ghi ═════════

def test_c1_hai_vai_moi_xem_duoc_nhung_KHONG_ghi_duoc():
    for vai in ("tp_hd", "gd_doi_xe"):
        r = client.post(f"/api/v1/danh-gia/ghi-ho/{ID['care']}", headers=_h(vai),
                        json={"diem": [{"doi_tuong": "tour", "diem": 4}]})
        assert r.status_code == 403, f"{vai} ghi hộ được: {r.status_code}"


def test_c2_danh_sach_GHI_HO_khong_he_nhan_them_vai_nao():
    assert not (set(API.PV_THEO_PHONG) & set(API.GHI_HO)), \
        "Vai được mở quyền XEM đã lọt sang danh sách GHI HỘ"


def test_c3_hai_cua_du_lieu_khach_KHONG_mo_cho_hai_vai_moi():
    """`/chua-tra-loi` trả TÊN KHÁCH và tên người bán; `/chi-so` là việc gửi tin của chăm sóc
    khách hàng. Chủ tịch dặn không mở danh tính khách một cách mặc nhiên."""
    for vai in ("tp_hd", "gd_doi_xe"):
        for duong in ("chua-tra-loi", "chi-so"):
            r = client.get(f"/api/v1/danh-gia/{duong}?tu={TU}&den={DEN}", headers=_h(vai))
            assert r.status_code == 403, f"{vai} vào được /{duong}"


# ═════════ D · màn hình và API cùng mở, bảng khai không lệch ═════════

def test_d1_man_hinh_va_API_mo_CUNG_LUC():
    """Mở quyền API mà không mở menu thì trưởng phòng vẫn không thấy gì."""
    from app.services import access as AC
    for vai in API.PV_THEO_PHONG:
        assert vai in AC.MENU_ROLES["/danh-gia"], f"{vai} có quyền API mà không có màn hình"
        assert vai in API.XEM_BANG_DIEM


def test_d2_bang_khai_pham_vi_KHONG_lech_voi_bang_phong_ban_da_co():
    """Phạm vi không phải khái niệm mới: nó mượn đúng bảng phòng ban của báo cáo phòng. Hai bảng
    lệch nhau thì một trưởng phòng đọc được bảng điểm của phòng mà ông không có báo cáo, hoặc
    ngược lại — và không ai biết cho tới khi có người hỏi."""
    from app.services import bao_cao_phong as BP
    for vai, d in API.PV_THEO_PHONG.items():
        assert d["phong"] in BP.PHONG, f"{vai} khai phòng «{d['phong']}» không có trong PHONG"
        assert vai in BP.PHONG[d["phong"]]["xem"], \
            f"{vai} xem bảng điểm phòng «{d['phong']}» mà không phải người xem báo cáo phòng ấy"


def test_d3_moi_loai_doi_tuong_khai_trong_pham_vi_deu_la_loai_CO_THAT():
    from app.models.danh_gia import DG_CO_KHOA, DG_DOI_TUONG
    for vai, d in API.PV_THEO_PHONG.items():
        for dt in d["doi_tuong"]:
            assert dt in DG_DOI_TUONG, f"{vai} khai loại «{dt}» không có thật"
            assert dt in DG_CO_KHOA, \
                f"{vai} khai loại «{dt}» không có khoá người, nên không lọc theo phòng được"
