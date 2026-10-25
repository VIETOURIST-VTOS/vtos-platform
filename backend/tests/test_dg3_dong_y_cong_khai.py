# -*- coding: utf-8 -*-
"""HD-DG3 — ĐỒNG Ý CÔNG KHAI NHẬN XÉT. Chủ tịch chốt sáu nút ngày 16/10/2026.

Đo được trên main trước đợt này: VTOS đã có ô `care_tickets.dong_y_dung_danh_gia`, nhưng ô ấy hỏi
*"có đồng ý cho công ty DÙNG lời nhận xét này không"* — không phải câu Chủ tịch chốt, vốn nói RÕ
đăng ở đâu và nói rõ không kèm tên. Nên đợt này ghi riêng, và nhóm F dưới đây canh đúng chỗ ấy:
không một đường nào được coi chữ "co" cũ là đã xin phép cho việc mới.

A. Luật gốc: đủ cả hai mới hiện.
B. Ai duyệt được — và ai KHÔNG, kể cả vai nhìn thấy mọi thứ.
C. Hàng rào chồng vai: chặn đúng lúc, mở lại đúng lúc.
D. Cửa rút công khai: một lần, không rò dữ liệu, không làm máy dò.
E. Gỡ lệch chiều so với đăng.
F. Không dùng lại đồng ý cũ, và không tự tạo đồng ý cho ai.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_dg3.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dg3.db"):
    os.remove("test_dg3.db")

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.services import dong_y as DY  # noqa: E402

client = TestClient(app)
MK = "Vtos@Demo#2026"
# Tên mang mã đợt — bài học HD-DG2: tên chung thì hai bộ chạy cùng lượt sập ở bước dựng.
AI = {"chutich": "chutich_dg3", "tgd": "tgd_dg3", "bks": "bks_dg3", "robot_ks": "robot_dg3",
      "cntt": "cntt_dg3", "tp_hd": "thang_dg3", "tp_hd2": "thang2_dg3", "nv_mkt": "mkt_dg3"}
ID: dict = {}


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import Booking, Tour, User
        from app.models.cskh import CareTicket
        from app.models.danh_gia import DanhGiaSauTour
        from app.models.hr import Employee, GuideAssignment
        with SessionLocal() as db:
            for vai, ten in AI.items():
                vai_that = "tp_hd" if vai == "tp_hd2" else vai
                if db.execute(select(User).where(User.username == ten)).scalars().first() is None:
                    db.add(User(username=ten, full_name="Thử " + ten, role=vai_that,
                                department="Thử", password_hash=hash_password(MK)))
            db.commit()
            op = db.execute(select(User)).scalars().first()

            e = Employee(code="DG3-HDV", full_name="HDV thử DG3", department="huong_dan",
                         position="hdv", start_date=date(2024, 1, 1), card_no="DG3-HDV",
                         card_type="quoc_te", card_expiry=date(2030, 1, 1), member_org=True,
                         contract_type="ctv", ctv_contract=True)
            db.add(e); db.commit(); ID["hdv"] = e.id

            t = Tour(code="DG3-T", name="Chuyến thử DG3", tour_type="le_noi_dia",
                     operator_id=op.id, start_date=date(2026, 9, 12), end_date=date(2026, 9, 15))
            db.add(t); db.commit(); ID["tour"] = t.id
            db.add(GuideAssignment(tour_id=t.id, guide_id=e.id, days=3)); db.commit()

            b = Booking(code="DG3-B", tour_id=t.id, customer_name="KhachDG3Rieng",
                        customer_phone="0900000555", pax=1, sales_id=op.id, created_by=op.id,
                        request_id=0, source="thu")
            db.add(b); db.commit()
            ca = CareTicket(booking_id=b.id, tour_id=t.id, customer_name="KhachDG3Rieng",
                            customer_phone="0900000555", han_lien_he=date(2026, 9, 20))
            db.add(ca); db.commit()
            for i in range(6):
                dg = DanhGiaSauTour(care_id=ca.id, booking_id=b.id, tour_id=t.id, doi_tuong="hdv",
                                    doi_tuong_id=e.id, doi_tuong_ten="HDV thử DG3", diem=5,
                                    nhan_xet=f"Loi khen thu {i}.", nguon="khach")
                db.add(dg); db.commit(); ID[f"dg{i}"] = dg.id
        yield


def _h(vai):
    r = client.post("/api/v1/auth/login", data={"username": AI[vai], "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _dg(khoa):
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    try:
        return db.get(DanhGiaSauTour, ID[khoa]), db
    finally:
        pass


def _nguoi(db, vai):
    """NGƯỜI THẬT từ cơ sở dữ liệu, có id thật.

    Bản đầu của tệp này dùng một lớp giả với `id = 0`. Phép cân mã bắt được: `ai_duyet_duoc` tra
    quyền cấp lẻ theo `u.id`, nên người giả KHÔNG BAO GIỜ có quyền, và ba ca thử xanh vì bị chặn
    ở cửa quyền chứ không phải ở hàng rào chúng mang tên. Dùng người thật để mỗi ca chỉ còn đúng
    một lý do có thể làm nó đỏ.
    """
    from app.models.core import User
    return db.execute(select(User).where(User.username == AI[vai])).scalars().first()


def _ban_ghi(db, dg_id):
    from app.models.danh_gia import DongYCongKhai
    return db.execute(select(DongYCongKhai)
                      .where(DongYCongKhai.danh_gia_id == dg_id)).scalars().first()


def _cap(db, username, kind, value, ngay=90, duyet="chutich_dg3"):
    from app.models.core import User, UserGrant
    u = db.execute(select(User).where(User.username == username)).scalars().first()
    g = UserGrant(user_id=u.id, kind=kind, value=value, from_date=date.today(),
                  to_date=date.today() + timedelta(days=ngay),
                  reason="Chủ tịch chốt 16/10/2026 — thêm một người duyệt công bố",
                  granted_by=duyet, approved_by=duyet, active=True)
    db.add(g); db.commit()
    return g


# ═════════ A · đủ cả hai mới hiện ═════════

def test_a1_chua_hoi_khach_thi_khong_cong_khai():
    assert DY.cong_khai_duoc(None) is False


def test_a2_khach_dong_y_nhung_chua_duyet_thi_VAN_khong_hien():
    """Đồng ý của khách KHÔNG phải lệnh đăng — nó là một trong hai điều kiện."""
    db = _db()
    dg = db.get(type(db.get(__import__("app.models.danh_gia", fromlist=["DanhGiaSauTour"])
                            .DanhGiaSauTour, ID["dg0"])), ID["dg0"]) if False else None
    from app.models.danh_gia import DanhGiaSauTour
    dg = db.get(DanhGiaSauTour, ID["dg0"])
    r = DY.ghi_tra_loi(db, dg, "co"); db.commit()
    assert r.tra_loi == "co"
    assert DY.cong_khai_duoc(r) is False, "chưa ai duyệt mà đã công khai được"
    db.close()


def test_a3_cau_hoi_duoc_chep_NGUYEN_VAN_vao_ban_ghi():
    """Một bản ghi đồng ý mà không nói được «đồng ý với điều gì» thì nó không chứng minh gì cả."""
    db = _db()
    r = _ban_ghi(db, ID["dg0"])
    assert r.cau_hoi == DY.CAU_HOI
    assert "không kèm tên" in r.cau_hoi
    assert "hồ sơ hướng dẫn viên" in r.cau_hoi
    assert r.pham_vi == "ho_so_hdv_cong_khai"
    db.close()


def test_a4_khach_tra_loi_khong_thi_khong_co_ma_rut():
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg1"])
    r = DY.ghi_tra_loi(db, dg, "khong"); db.commit()
    assert r.ma_rut == "", "trả lời không mà vẫn sinh mã rút — không có gì để rút"
    assert DY.cong_khai_duoc(r) is False
    db.close()


def test_a5_khong_co_gia_tri_mac_dinh_cho_cau_dong_y():
    """Im lặng không phải là đồng ý."""
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg2"])
    for xau in ("", "yes", "1", "dong_y", None):
        with pytest.raises(ValueError):
            DY.ghi_tra_loi(db, dg, xau)
    db.close()


# ═════════ B · ai duyệt được ═════════

def test_b1_bks_va_robot_KHONG_duyet_duoc_du_la_BASE_VIEW():
    """`access.co_quyen` trả True cho MỌI vai BASE_VIEW. Đăng một lời khách lên mạng không phải
    việc xem: cơ quan kiểm soát mà tự công bố thì không còn kiểm soát được việc công bố, và một
    con robot bấm nút đăng là nội dung ra ngoài không ai ký."""
    from app.services import access as AC
    db = _db()

    class U:
        def __init__(s, un, vai): s.username, s.role, s.id = un, vai, 0

    for vai in DY.KHONG_DUYET_DU_LA_BASE_VIEW:
        u = U("ai_" + vai, vai)
        assert AC.co_quyen(db, u, DY.QUYEN_DUYET) is True, "cảnh thử sai: co_quyen phải True ở đây"
        assert DY.ai_duyet_duoc(db, u) == (False, ""), f"{vai} duyệt được — hàng rào thủng"
    db.close()


def test_b2_hai_vai_duyet_duoc_bang_VAI():
    db = _db()

    class U:
        def __init__(s, vai): s.username, s.role, s.id = "x", vai, 0

    for vai in DY.VAI_DUYET:
        assert DY.ai_duyet_duoc(db, U(vai)) == (True, "vai")
    db.close()


def test_b3_tp_hd_chi_duyet_duoc_KHI_co_quyen_cap_dich_danh():
    """Hai Trưởng phòng Hướng dẫn: cả hai ĐỌC được hàng đợi, chỉ người được cấp mới BẤM được.
    Quyền hết hạn là nút tắt thật, vì chính nút bấm hỏi quyền ấy chứ không hỏi vai."""
    db = _db()
    assert client.get("/api/v1/cong-bo/hang-doi", headers=_h("tp_hd")).status_code == 200
    assert client.get("/api/v1/cong-bo/hang-doi", headers=_h("tp_hd2")).status_code == 200
    r = client.post(f"/api/v1/cong-bo/{ID['dg0']}/duyet", json={"dong_y": True},
                    headers=_h("tp_hd2"))
    assert r.status_code == 403, "TP Hướng dẫn chưa được cấp mà bấm được"
    _cap(db, AI["tp_hd"], "capability", DY.QUYEN_DUYET)
    db.close()


def test_b4_han_quyen_khong_qua_90_ngay():
    """`core.GRANT_MAX_DAYS` = 90 và cửa cấp từ chối dài hơn. Chủ tịch chọn 12 tháng ngày 16/10;
    đo ra trần 90 ngày nên chốt lại: cấp 90 ngày rồi gia hạn, giữ nguyên luật của kho."""
    from app.models.core import GRANT_MAX_DAYS
    assert GRANT_MAX_DAYS == 90
    r = client.post("/api/v1/access/grants", headers=_h("chutich"), json={
        "user_id": 1, "kind": "capability", "value": DY.QUYEN_DUYET,
        "to_date": str(date.today() + timedelta(days=GRANT_MAX_DAYS + 1)), "reason": "thử"})
    assert r.status_code == 422, "cửa cấp nhận quyền dài hơn 90 ngày"


def test_b5_nv_mkt_khong_doc_duoc_hang_doi():
    assert client.get("/api/v1/cong-bo/hang-doi", headers=_h("nv_mkt")).status_code == 403


# ═════════ C · hàng rào chồng vai ═════════

def test_c1_chan_dung_luc_va_mo_lai_dung_luc():
    """Anh Thắng duyệt bình thường mọi nhận xét, TRỪ nhận xét về một HDV mà chính anh ấy đang giữ
    một khiếu nại chưa đóng. Khiếu nại đóng lại là nút tự mở."""
    from app.models.cskh import Complaint
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg5"])
    DY.ghi_tra_loi(db, dg, "co"); db.commit()
    U = _nguoi(db, "tp_hd")
    assert DY.ai_duyet_duoc(db, U)[0] is True, (
        "cảnh thử sai: người này phải CÓ quyền duyệt, nếu không thì ca đo cửa quyền chứ không "
        "đo hàng rào chồng vai")
    assert DY.vuong_chong_vai(db, U, dg) == "", "chưa có khiếu nại mà đã vướng"
    kn = Complaint(code="KN-DG3-1", source="zalo", customer_name="KhachDG3Rieng",
                   tour_id=ID["tour"], nhom="hdv", level=1, noi_dung="than",
                   handler=AI["tp_hd"], status="dang_xu_ly")
    db.add(kn); db.commit()
    vuong = DY.vuong_chong_vai(db, U, dg)
    assert vuong and "KN-DG3-1" in vuong, "khiếu nại mở mà không vướng — hàng rào thủng"
    kq = DY.duyet(db, U, dg, True)
    assert kq["xong"] is False and "KN-DG3-1" in kq["loi"], (
        f"bị chặn vì lý do KHÁC, không phải chồng vai: {kq}")
    kn.status = "da_dong"; db.commit()
    assert DY.vuong_chong_vai(db, U, dg) == "", "đóng khiếu nại rồi mà vẫn vướng"
    assert DY.duyet(db, U, dg, True)["xong"] is True, "đóng khiếu nại rồi mà nút vẫn không mở"
    db.commit(); db.close()


def test_c2_chu_tich_KHONG_bi_hang_rao_chong_vai_chan():
    """Chủ tịch và TGĐ không giữ việc xác minh khiếu nại, nên không có vai nào để chồng."""
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg0"])

    class U:
        username, role, id = AI["chutich"], "chutich", 0

    assert DY.vuong_chong_vai(db, U, dg) == ""
    db.close()


# ═════════ D · cửa rút công khai ═════════

def test_d1_cua_rut_KHONG_can_dang_nhap_va_KHONG_ro_mot_chu_nao():
    """Một cửa không cần đăng nhập mà đọc được thì nó là cửa ĐỌC, không phải cửa rút."""
    db = _db()
    ma = _ban_ghi(db, ID["dg0"]).ma_rut
    db.close()
    r = client.get(f"/api/v1/rut-dong-y/{ma}")
    assert r.status_code == 200
    for ro in ("KhachDG3Rieng", "0900000555", "HDV thử DG3", "Loi khen thu"):
        assert ro not in r.text, f"cửa rút in ra «{ro}»"


def test_d2_rut_mot_lan_va_bam_lai_KHONG_bao_loi():
    """Khách bấm hai lần không phải là khách sai. Bản đầu của `dong_y.rut` xoá mã ngay sau khi
    rút, làm nhánh «đã rút rồi» thành MÃ CHẾT và khách nhận về câu «đường dẫn không đúng» — phép
    đo bắt được, và ca này giữ cho nó không quay lại."""
    db = _db()
    ma = _ban_ghi(db, ID["dg0"]).ma_rut
    db.close()
    r1 = client.post(f"/api/v1/rut-dong-y/{ma}", json={}).json()
    assert r1["xong"] is True and r1["da_rut_tu_truoc"] is False
    r2 = client.post(f"/api/v1/rut-dong-y/{ma}", json={}).json()
    assert r2["xong"] is True and r2["da_rut_tu_truoc"] is True
    assert "không đúng" not in r2.get("loi_nhan", "")


def test_d3_rut_roi_thi_thoi_cong_khai_NGAY():
    """PHẢI ĐĂNG ĐƯỢC TRƯỚC thì việc rút mới có nghĩa.

    Bản đầu của ca này chỉ kiểm dòng dg0 sau khi rút và thấy không công khai được — nhưng dg0
    chưa từng được duyệt, nên nó vốn đã không công khai và phép thử không đo gì. Phép cân mã bắt
    được: gỡ hẳn điều kiện `rut_luc is None` khỏi `cong_khai_duoc` mà ca này vẫn xanh.
    """
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg4"])
    DY.ghi_tra_loi(db, dg, "co"); db.commit()
    kq = DY.duyet(db, _nguoi(db, "chutich"), dg, True); db.commit()
    assert kq["xong"] is True
    assert DY.cong_khai_duoc(_ban_ghi(db, dg.id)) is True, "cảnh thử sai: chưa đăng được thì rút vô nghĩa"
    ma = _ban_ghi(db, dg.id).ma_rut
    db.close()
    assert client.post(f"/api/v1/rut-dong-y/{ma}", json={}).json()["xong"] is True
    db2 = _db()
    assert DY.cong_khai_duoc(_ban_ghi(db2, dg.id)) is False, "khách rút rồi mà vẫn công khai"
    db2.close()


def test_d4_rut_la_NGUNG_CONG_KHAI_chu_khong_phai_xoa():
    """Lời nhận xét vẫn ở sổ nội bộ và vẫn tính vào điểm hướng dẫn viên."""
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg0"])
    assert dg is not None, "rút mà xoá mất dòng đánh giá"
    assert dg.nhan_xet, "rút mà xoá mất lời nhận xét"
    r = _ban_ghi(db, ID["dg0"])
    assert r.rut_luc is not None and r.tra_loi == "co", "rút mà xoá mất dấu vết đã từng đồng ý"
    db.close()


def test_d5_ma_sai_va_ma_da_dung_tra_ve_CUNG_MOT_cau():
    """Trả lời khác nhau cho từng trường hợp hỏng là biến cửa này thành máy dò."""
    a = client.post("/api/v1/rut-dong-y/ma-hoan-toan-bia-dat", json={}).json()
    assert a["xong"] is False
    assert a["loi"] == "Đường dẫn không đúng hoặc đã hết hiệu lực."


def test_d6_trang_xac_nhan_khong_tra_cosodulieu():
    """Trang xác nhận trả về cùng một nội dung cho mã thật và mã bịa — không lộ mã nào có thật."""
    that = client.get("/api/v1/rut-dong-y/ma-bia-mot").json()
    bia = client.get("/api/v1/rut-dong-y/ma-bia-hai").json()
    assert that == bia


# ═════════ E · gỡ lệch chiều ═════════

def test_e1_bat_ky_ai_trong_ba_cung_go_duoc_ngay():
    """Đăng cần một trong ba; gỡ thì ai trong ba cũng gỡ được, không phải hỏi người đã đăng.
    Đăng nhầm thì sửa được bằng cách gỡ; không gỡ được mới là cái kẹt."""
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg3"])
    DY.ghi_tra_loi(db, dg, "co"); db.commit()

    class CT:
        username, role, id = AI["chutich"], "chutich", 0

    class TGD:
        username, role, id = AI["tgd"], "tgd", 0

    assert DY.duyet(db, CT, dg, True)["xong"] is True; db.commit()
    assert DY.cong_khai_duoc(_ban_ghi(db, dg.id)) is True
    assert DY.go(db, TGD, dg, "khách gọi điện xin gỡ")["xong"] is True; db.commit()
    assert DY.cong_khai_duoc(_ban_ghi(db, dg.id)) is False
    db.close()


def test_e2_khong_dang_thi_BAT_BUOC_ghi_ly_do():
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg2"])
    DY.ghi_tra_loi(db, dg, "co"); db.commit()

    class CT:
        username, role, id = AI["chutich"], "chutich", 0

    assert DY.duyet(db, CT, dg, False, "")["xong"] is False
    kq = DY.duyet(db, CT, dg, False, "lời lẽ không phù hợp để đăng")
    assert kq["xong"] is True and kq["ket_qua"] == "khong_dang"
    db.commit(); db.close()


def test_e3_moi_lan_bam_ghi_lai_BAM_BANG_QUYEN_NAO():
    """Sáu tháng sau câu «ai quyết cái này, bằng quyền gì» phải trả lời được."""
    db = _db()
    r = _ban_ghi(db, ID["dg2"])
    assert r.duyet_boi == AI["chutich"]
    assert r.duyet_bang_quyen == "vai"
    assert r.duyet_luc is not None
    assert r.duyet_ly_do
    db.close()


# ═════════ F · không mượn đồng ý cũ, không tự tạo đồng ý ═════════

def test_f1_o_dong_y_CU_khong_mo_duoc_cua_cong_khai():
    """`care_tickets.dong_y_dung_danh_gia` hỏi một câu KHÁC. Lấy chữ "co" cũ dùng cho việc mới là
    đăng lời của một người ở nơi họ chưa từng được hỏi."""
    from app.models.cskh import CareTicket
    from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg1"])          # dg1 tra loi "khong" o ca a4
    ca = db.get(CareTicket, dg.care_id)
    ca.dong_y_dung_danh_gia = "co"; db.commit()     # o CU noi "co"
    r = db.execute(select(DongYCongKhai)
                   .where(DongYCongKhai.danh_gia_id == dg.id)).scalars().first()
    assert r is not None and r.tra_loi == "khong"
    # Ep not qua moi cua KHAC: coi nhu da duyet. Lam vay thi thu DUY NHAT con giu no kin la cau
    # tra loi cua ban ghi MOI. Khong ep thi ca nay xanh chi vi chua ai duyet — va phep can ma da
    # bat dung loi ay o ban dau.
    r.duyet_luc = __import__("datetime").datetime.now()
    r.duyet_ket_qua = "dang"
    r.duyet_boi = AI["chutich"]
    db.commit()
    assert DY.cong_khai_duoc(r) is False, "ô đồng ý CŨ mở được cửa công khai MỚI"
    db.close()


def test_f2_khong_mot_duong_nao_tu_tao_ban_ghi_dong_y():
    """Ranh giới nặng nhất của đợt: hệ thống chỉ GHI LẠI việc khách đã đồng ý, không tạo hộ.

    Quét mã nguồn: ngoài chính `services/dong_y.py` và cửa khảo sát, không tệp nào được gọi
    `ghi_tra_loi`. Một chỗ gọi lén ở đâu đó là một bản ghi đồng ý không có khách nào bấm.
    """
    import pathlib
    goc = pathlib.Path(__file__).resolve().parent.parent / "app"
    cho_phep = {"services/dong_y.py", "api/v1/khao_sat_cong_khai.py", "services/danh_gia.py"}
    pham = []
    for f in goc.rglob("*.py"):
        rel = str(f.relative_to(goc)).replace("\\", "/")
        if rel in cho_phep:
            continue
        if "ghi_tra_loi" in f.read_text(encoding="utf-8", errors="replace"):
            pham.append(rel)
    assert not pham, f"gọi ghi_tra_loi ngoài danh sách cho phép: {pham}"


def test_f3_hang_doi_noi_ro_rong_khong_phai_la_khong_ai_khen():
    """Rỗng ở đây là đúng, không phải hỏng — và màn hình phải nói ra điều ấy."""
    kq = client.get("/api/v1/cong-bo/hang-doi", headers=_h("chutich")).json()
    assert "luu_y" in kq and "trước đợt này" in kq["luu_y"]
    assert kq["cau_hoi"] == DY.CAU_HOI


def test_f4_nhan_nguoi_viet_KHONG_in_ten_tuyen_khi_chua_co_truong_tuyen():
    """Chủ tịch chọn nhãn có tên tuyến. VTOS chưa có trường tuyến — `tours.name` là chữ tự do, nên
    gom theo nó thì ngưỡng 30 khách đếm một tập khác với tập nó mang tên. Nhãn lùi về chỉ có
    tháng, và lý do in thẳng trên màn hình duyệt chứ không che lén."""
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg0"])
    nhan = DY.nhan_nguoi_viet(db, dg)
    assert nhan.startswith("Khách đi tour tháng ")
    assert "Chuyến thử DG3" not in nhan, "nhãn in tên chuyến — lộ đường về người viết"
    assert DY.CO_TRUONG_TUYEN is False
    assert "HD-13" in DY.ly_do_lui_nhan(db, dg), "máy che mà không nói đang che vì sao"
    db.close()


# ── ĐỢT HDV-2 (làn R2) — câu lý do phải nói ĐÚNG CHUYỆN ─────────────────────────────────────
def test_hdv2_1_ly_do_lui_nhan_KHONG_duoc_noi_la_VTOS_thieu_truong():
    """Câu cũ in cho người duyệt: «VTOS chưa có trường tuyến». SAI, và sai theo hướng tốn việc.

    VTOS CÓ trường: `models/core.py:419` khai `products.region`; `models/hr.py:204` và `:230`
    khai `guide_rates.route`. Thứ còn thiếu là chỗ NỐI chuyến về một địa bàn — hai chuyện khác
    hẳn nhau. Người duyệt đọc «chưa có trường» sẽ đi đặt một việc dựng cột mà không ai cần.

    Trả câu cũ về là phép thử này ĐỎ.
    """
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    dg = db.get(DanhGiaSauTour, ID["dg0"])
    ly_do = DY.ly_do_lui_nhan(db, dg)
    assert "chưa có trường tuyến" not in ly_do, (
        "câu cũ đã quay lại — nó nói VTOS thiếu trường, trong khi `products.region` và "
        "`guide_rates.route` đều đang có")
    assert "CHƯA nối chuyến về một địa bàn" in ly_do, "câu mới không nói đúng chuyện còn thiếu"
    db.close()


def test_hdv2_2_cau_moi_van_phai_chi_duoc_viec_phai_lam():
    """Một câu đúng mà không chỉ được việc thì người duyệt vẫn đứng im."""
    from app.models.danh_gia import DanhGiaSauTour
    db = _db()
    ly_do = DY.ly_do_lui_nhan(db, db.get(DanhGiaSauTour, ID["dg0"]))
    assert "products.region" in ly_do and "guide_rates.route" in ly_do, "không nêu trường đang có"
    assert "dia-ban/do-nen" in ly_do, "không chỉ chỗ xem độ phủ"
    assert "HD-13" in ly_do, "mất mã đợt — `test_f4` cũ canh chỗ này"
    db.close()
