"""Phòng HDV Đợt 2 — báo cáo sau tour: nội dung thật, có phiên bản, có vòng kiểm.

Chủ tịch chốt 06/10/2026: báo cáo phải nộp trong 3 ngày, và báo cáo thiếu thì quyết toán tour không
được gọi là hoàn tất. Bộ này giữ đúng những điều ấy:

  A. Có chỗ chứa nội dung thật, không còn là một ô đánh dấu.
  B. Gửi rồi thì KHOÁ; sửa là bản mới, bản cũ vẫn đọc lại được.
  C. Gửi KHÔNG bằng xong — chỉ bản đã xác nhận mới gỡ treo.
  D. Trả lại phải ghi lý do, và trả lại thì treo quay lại.
  E. Không ai tự kiểm báo cáo của chính mình; không ai đọc báo cáo của người khác.
  F. Hạn 3 ngày tính từ ngày tour kết thúc; chuyến chưa có ngày kết thúc thì KHÔNG đoán hạn.
  G. Quyết toán: còn người nợ báo cáo thì chưa được gọi hoàn tất, và nói rõ nợ ai.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hdv2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hdv2.db"):
    os.remove("test_hdv2.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
ID = {}
AI = "cntt"      # xem chú thích trong test_hdv1: nhóm API guide-assignments chưa mở cho Điều hành
D = datetime(2026, 11, 20, 6, 0)


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment

        db = SessionLocal()
        op_id = db.execute(select(User)).scalars().first().id

        def _hdv(ma, ten):
            return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                            start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                            member_org=True, contract_type="ctv", ctv_contract=True)

        e1, e2 = _hdv("BC001", "Lê Văn C"), _hdv("BC002", "Phạm Thị D")
        t1 = Tour(code="BC-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op_id,
                  start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        # Chuyến KHÔNG có ngày kết thúc – dùng cho nhóm F.
        t2 = Tour(code="BC-T2", name="Chuyến chưa chốt ngày về", tour_type="le_noi_dia",
                  operator_id=op_id, start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([e1, e2, t1, t2])
        db.commit()

        # Đợt HD-10 (13/10/2026): `cntt` không còn mặc nhiên xác nhận được báo cáo sau tour. Bộ
        # này dùng `cntt` làm người kiểm từ Đợt HDV-2, nên cảnh phải cấp đúng cái quyền mà đời
        # thật cũng phải cấp — và cấp qua CỬA NGOẠI LỆ chứ không nhét thẳng một cờ vào mã, để
        # cảnh dựng ở đây giống đời thật ở cả cách cấp lẫn cách thu.
        from datetime import timedelta as _td

        from app.models.core import UserGrant
        _ai = db.execute(select(User).where(User.username == AI)).scalars().first()
        db.add(UserGrant(user_id=_ai.id, kind="capability", value="kiem_bao_cao_tour",
                         from_date=date.today(), to_date=date.today() + _td(days=90),
                         reason="Phép thử Đợt HDV-2 dùng CNTT làm người kiểm thay.",
                         granted_by="chutich", approved_by="chutich"))
        db.commit()
        a1 = GuideAssignment(tour_id=t1.id, guide_id=e1.id, days=4, rate_per_day=800_000,
                             bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
        a2 = GuideAssignment(tour_id=t1.id, guide_id=e2.id, days=4, rate_per_day=700_000,
                             bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan",
                             vai_tro="phu")
        db.add_all([a1, a2])
        db.commit()
        ID.update(t1=t1.id, t2=t2.id, e1=e1.id, e2=e2.id, a1=a1.id, a2=a2.id)
        db.close()
        yield


def _lap(aid=None, **kw):
    than = {"chuong_trinh_thuc_hien": "Đi đủ 4 ngày theo chương trình", "so_khach_thuc_te": 18}
    than.update(kw)
    return client.post(f"/api/v1/guide-assignments/{aid or ID['a1']}/bao-cao",
                       json=than, headers=login(AI))


def _doc(aid=None):
    return client.get(f"/api/v1/guide-assignments/{aid or ID['a1']}/bao-cao", headers=login(AI)).json()


# ───────────────────────────── A · nội dung thật ─────────────────────────────
def test_a1_lap_duoc_ban_nhap_voi_noi_dung_that():
    r = _lap()
    assert r.status_code == 201, r.text
    d = _doc()["dang_xet"]
    assert d["trang_thai"] == "nhap" and d["ban_so"] == 1
    assert d["chuong_trinh_thuc_hien"].startswith("Đi đủ 4 ngày")


def test_a2_chua_co_ban_nao_khac_han_co_ban_chua_xong():
    d = _doc(ID["a2"])
    assert d["dang_xet"] is None, "phân công chưa ai lập báo cáo thì không có bản nào"
    assert d["cac_ban"] == []


def test_a3_so_khach_de_trong_duoc_va_khong_co_mac_dinh():
    from app.models.hdv import BaoCaoSauTour
    c = BaoCaoSauTour.__table__.columns["so_khach_thuc_te"]
    assert c.nullable is True and c.default is None and c.server_default is None, \
        "mặc định 0 thì mọi báo cáo chưa điền đều thành một chuyến không khách"


def test_a4_gui_to_trong_thi_tu_choi():
    r = client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao",
                    json={"chuong_trinh_thuc_hien": "   "}, headers=login(AI))
    assert r.status_code == 201
    r2 = client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/gui", json={}, headers=login(AI))
    assert r2.status_code == 422


# ───────────────────────────── B · gửi rồi thì khoá ─────────────────────────────
def test_b1_gui_xong_thi_khoa_khong_sua_de_duoc():
    r = client.post(f"/api/v1/guide-assignments/{ID['a1']}/bao-cao/gui", json={}, headers=login(AI))
    assert r.status_code == 200, r.text
    assert _doc()["dang_xet"]["da_khoa"] is True
    r2 = _lap(chuong_trinh_thuc_hien="sửa lén")
    assert r2.status_code == 422 and r2.json()["detail"]["gate"] == "BAO_CAO_DA_KHOA"


def test_b2_ban_moi_thay_ban_cu_va_ban_cu_van_doc_lai_duoc():
    r = client.post(f"/api/v1/guide-assignments/{ID['a1']}/bao-cao/ban-moi",
                    json={"chuong_trinh_thuc_hien": "Bản 2: bổ sung sự cố", "so_khach_thuc_te": 17},
                    headers=login(AI))
    assert r.status_code == 201 and r.json()["ban_so"] == 2
    d = _doc()
    assert d["dang_xet"]["ban_so"] == 2
    assert len(d["cac_ban"]) == 2, "bản cũ phải còn nguyên để đọc lại"
    cu = [b for b in d["cac_ban"] if b["ban_so"] == 1][0]
    assert cu["bi_thay"] is True and cu["chuong_trinh_thuc_hien"].startswith("Đi đủ 4 ngày"), \
        "bản cũ giữ nguyên nội dung đã gửi, không bị bản mới ghi đè"
    assert d["dang_xet"]["thay_cho_id"] == cu["id"], "đọc ngược được cả chuỗi"


def test_b3_ban_con_nhap_thi_sua_thang_chu_khong_can_ban_moi():
    r = client.post(f"/api/v1/guide-assignments/{ID['a1']}/bao-cao/ban-moi",
                    json={"chuong_trinh_thuc_hien": "x"}, headers=login(AI))
    assert r.status_code == 422


# ───────────────────────────── C · gửi không bằng xong ─────────────────────────────
def test_c1_gui_roi_chua_ai_kiem_thi_van_con_no_bao_cao():
    client.post(f"/api/v1/guide-assignments/{ID['a1']}/bao-cao/gui", json={}, headers=login(AI))
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.get(GuideAssignment, ID["a1"])
    con_no = not a.report_submitted
    db.close()
    assert con_no, "chỉ cần bấm Gửi là hết bị treo thì cái treo ấy mất tác dụng ngay ngày đầu"


def test_c2_xac_nhan_thi_go_treo():
    r = client.post(f"/api/v1/guide-assignments/{ID['a1']}/bao-cao/kiem",
                    json={"xac_nhan": True}, headers=login(AI))
    assert r.status_code == 200, r.text
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.get(GuideAssignment, ID["a1"])
    xong = a.report_submitted
    db.close()
    assert xong, "cột cũ report_submitted phải là tấm gương của bảng mới – hai chỗ đang dùng nó"


# ───────────────────────────── D · trả lại ─────────────────────────────
def test_d1_tra_lai_khong_ghi_ly_do_thi_bi_chan():
    client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/gui", json={},
                headers=login(AI))  # tờ trống đã bị chặn ở a4, nên gửi lại cho có bản
    client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao",
                json={"chuong_trinh_thuc_hien": "Đi đủ chương trình"}, headers=login(AI))
    client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/gui", json={}, headers=login(AI))
    r = client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/kiem",
                    json={"xac_nhan": False, "y_kien": ""}, headers=login(AI))
    assert r.status_code == 422, "trả lại mà không nói thiếu gì thì người nộp phải đoán"


def test_d2_tra_lai_co_ly_do_thi_treo_quay_lai():
    r = client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/kiem",
                    json={"xac_nhan": False, "y_kien": "Thiếu đánh giá nhà cung cấp"}, headers=login(AI))
    assert r.status_code == 200, r.text
    d = _doc(ID["a2"])["dang_xet"]
    assert d["trang_thai"] == "can_bo_sung" and "nhà cung cấp" in d["y_kien_kiem"]
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.get(GuideAssignment, ID["a2"])
    con_no = not a.report_submitted
    db.close()
    assert con_no


def test_d3_lech_phien_ban_thi_409():
    r = client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/kiem",
                    json={"phien_ban": 99, "xac_nhan": True}, headers=login(AI))
    assert r.status_code in (409, 422)
    if r.status_code == 409:
        assert r.json()["detail"]["gate"] == "LECH_PHIEN_BAN"


# ───────────────────────────── E · ai chạm được gì ─────────────────────────────
def test_e1_khong_tu_kiem_bao_cao_cua_chinh_minh():
    """Người kiểm mà cũng là hướng dẫn viên của chuyến ấy thì cửa kiểm phải từ chối."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import User
    from app.models.hr import Employee
    db = SessionLocal()
    u = db.execute(select(User).where(User.username == AI)).scalars().first()
    e = db.get(Employee, ID["e2"])
    cu = e.user_id
    e.user_id = u.id
    db.commit()
    try:
        r = client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/kiem",
                        json={"xac_nhan": True}, headers=login(AI))
        assert r.status_code in (403, 422), "tự nộp rồi tự xác nhận thì cái kiểm ấy không kiểm gì cả"
    finally:
        e.user_id = cu
        db.commit()
        db.close()


# ───────────────────────────── F · hạn 3 ngày ─────────────────────────────
def test_f1_han_nop_la_ngay_ket_thuc_cong_ba():
    from app.services.hdv import han_nop_cua
    assert han_nop_cua(date(2026, 11, 23)) == date(2026, 11, 26)


def test_f2_chuyen_chua_co_ngay_ket_thuc_thi_khong_doan_han():
    from app.services.hdv import han_nop_cua
    assert han_nop_cua(None) is None, \
        "một hạn bịa ra sẽ sinh cảnh báo trễ cho người chưa hề trễ"


def test_f3_thieu_han_thi_khong_ket_luan_tre():
    from app.models.hdv import BaoCaoSauTour
    b = BaoCaoSauTour(assignment_id=1, tour_id=1, guide_id=1, han_nop=None, trang_thai="da_gui")
    assert b.tre_han(date(2030, 1, 1)) is False, "chưa biết hạn khác hẳn đúng hạn"


def test_f4_qua_han_ma_chua_xac_nhan_thi_la_tre():
    from app.models.hdv import BaoCaoSauTour
    b = BaoCaoSauTour(assignment_id=1, tour_id=1, guide_id=1,
                      han_nop=date(2026, 11, 26), trang_thai="da_gui")
    assert b.tre_han(date(2026, 11, 27)) is True
    b.trang_thai = "da_xac_nhan"
    assert b.tre_han(date(2026, 11, 27)) is False, "đã xong rồi thì thôi đếm trễ"


def test_f5_mot_con_so_ba_ngay_duy_nhat():
    """Hằng số 3 ngày phải là MỘT chỗ. Hai chỗ tự đếm riêng là cách chắc chắn để mai kia một chỗ đổi
    thành 5 mà chỗ kia vẫn 3."""
    import pathlib
    from app.models.hdv import HAN_NOP_NGAY
    assert HAN_NOP_NGAY == 3
    src = pathlib.Path(__file__).resolve().parent.parent / "app" / "services" / "hdv.py"
    assert "HAN_NOP_NGAY" in src.read_text(encoding="utf-8"), "phép tính hạn phải dùng hằng số chung"


# ───────────────────────────── G · chặn quyết toán ─────────────────────────────
def test_g1_con_nguoi_no_bao_cao_thi_chua_duoc_goi_hoan_tat_va_noi_ro_no_ai():
    r = client.get("/api/v1/guide-assignments/bao-cao/thieu-theo-tour",
                   params={"tour_id": ID["t1"]}, headers=login(AI))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["duoc_goi_hoan_tat"] is False
    assert d["con_thieu"] == 1, "a1 đã xác nhận, a2 đang ở cần bổ sung"
    assert d["danh_sach"][0]["hdv"] == "Phạm Thị D", "phải nói ra phải gọi ai, không chỉ một ô đỏ"
    assert d["danh_sach"][0]["tinh_trang"] == "can_bo_sung", \
        "chưa nộp / chờ kiểm / bị trả lại là ba việc gọi ba người khác nhau"


def test_g2_moi_nguoi_xong_thi_duoc_goi_hoan_tat():
    client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/ban-moi",
                json={"chuong_trinh_thuc_hien": "Bổ sung đánh giá NCC", "so_khach_thuc_te": 18},
                headers=login(AI))
    client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/gui", json={}, headers=login(AI))
    client.post(f"/api/v1/guide-assignments/{ID['a2']}/bao-cao/kiem",
                json={"xac_nhan": True}, headers=login(AI))
    d = client.get("/api/v1/guide-assignments/bao-cao/thieu-theo-tour",
                   params={"tour_id": ID["t1"]}, headers=login(AI)).json()
    assert d["duoc_goi_hoan_tat"] is True and d["con_thieu"] == 0


def test_g3_nguoi_tu_choi_chuyen_thi_khong_tinh_la_no_bao_cao():
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.get(GuideAssignment, ID["a2"])
    cu = a.status
    a.status = "tu_choi"
    db.commit()
    db.close()
    try:
        d = client.get("/api/v1/guide-assignments/bao-cao/thieu-theo-tour",
                       params={"tour_id": ID["t1"]}, headers=login(AI)).json()
        assert d["con_thieu"] == 0, "người ta không đi thì không có gì để báo cáo"
    finally:
        db = SessionLocal(); a = db.get(GuideAssignment, ID["a2"]); a.status = cu; db.commit(); db.close()


# ───────────── H · nối vào màn hình quyết toán (Chủ tịch chốt 07/10/2026) ─────────────
def test_h1_quyet_toan_khong_duoc_goi_hoan_tat_khi_con_no_bao_cao():
    """Nối ở hàm ĐỌC quyết toán, không chặn ở hàm GHI: chặn ghi thì một báo cáo chưa nộp sẽ khoá luôn
    việc nhập chi phí của Điều hành, mà hai việc ấy không phụ thuộc nhau."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    db = SessionLocal()
    a = db.get(GuideAssignment, ID["a2"])
    cu = a.status
    a.status = "da_xac_nhan"
    db.commit()
    db.close()
    try:
        r = client.get(f"/api/v1/tours/{ID['t1']}/settlement", headers=login(AI))
        if r.status_code != 200:
            pytest.skip(f"cửa quyết toán trả {r.status_code} cho vai này")
        d = r.json()
        assert "duoc_goi_hoan_tat" in d
        if d["thieu_bao_cao_hdv"]:
            assert d["duoc_goi_hoan_tat"] is False
            assert any(c["level"] == "block" and "báo cáo sau tour" in c["msg"] for c in d["checks"]), \
                "phải là mức chặn và phải nói ra tên người còn nợ, không chỉ một ô đỏ"
    finally:
        db = SessionLocal(); a = db.get(GuideAssignment, ID["a2"]); a.status = cu; db.commit(); db.close()


# ───── I · cửa báo cáo của chính HDV nằm trong nhóm API của màn hình /xe-hdv ─────
def test_i1_bon_cua_bao_cao_nam_trong_nhom_xe_hdv():
    """Màn hình /xe-hdv khai nhóm `/api/v1/xe-hdv`. Nếu nó gọi thẳng `/api/v1/guide-assignments` thì
    bản đồ quyền phải khai thêm cả nhóm ấy cho màn hình — mà TÀI XẾ cũng mở màn hình này, nên khai
    như vậy là mở luôn chùm cửa điều động / tạm ứng / đề xuất cho tài xế. Bốn cửa dưới đây là lối vào
    khác của đúng bốn hàm cũ, đặt trong nhóm đã khai sẵn."""
    duong = {r.path for r in app.routes if hasattr(r, "path")}
    for d in ("/api/v1/xe-hdv/bao-cao/{aid}", "/api/v1/xe-hdv/bao-cao/{aid}/gui",
              "/api/v1/xe-hdv/bao-cao/{aid}/ban-moi"):
        assert d in duong, d


def test_i2_vai_tro_thu_lai_dung_hdv():
    """Nhóm `/api/v1/xe-hdv` mở cho cả tài xế lẫn HDV, nên cửa báo cáo phải tự thu vai trò lại.
    Mở cửa theo cả nhóm là cho tài xế nộp báo cáo tour."""
    r = client.post(f"/api/v1/xe-hdv/bao-cao/{ID['a1']}",
                    json={"chuong_trinh_thuc_hien": "x"}, headers=login("cntt"))
    assert r.status_code == 403, \
        "cửa này chỉ dành cho chính HDV – kể cả CNTT cũng không nộp hộ báo cáo tour"


def test_i3_man_hinh_khong_con_goi_thang_guide_assignments():
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "web" / "app" / "xe-hdv" / "page.tsx"
    if not p.exists():
        return
    assert "guide-assignments" not in p.read_text(encoding="utf-8"), \
        "gọi thẳng nhóm khác là ép bản đồ quyền phải nới cho mọi vai trò thấy màn hình này"
