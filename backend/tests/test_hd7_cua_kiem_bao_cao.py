"""HD-7 — CỬA KIỂM BÁO CÁO SAU TOUR: phép "không tự kiểm báo cáo của chính mình" phải CHẠY.

Chủ tịch chốt 13/10/2026, phương án (a):

  TP Hướng dẫn (`tp_hd`)   bắt buộc nối đúng hồ sơ nhân sự/HDV; thiếu hoặc liên kết không rõ ràng
                           thì chặn, hướng dẫn bổ sung.
  HCNS / CNTT              kiểm thay được, nhưng KHÔNG được miễn định danh.
  Và:                      "TP Hướng dẫn đi tour không được tự duyệt báo cáo của mình. Nếu tài
                           khoản kiêm nhiều vai, chuyển sang vai HCNS/CNTT cũng không được vượt
                           chặn này."

CHUYỆN ĐÃ XẢY RA. Dòng cũ ở `bc_kiem`:

    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e is not None and e.id == a.guide_id:
        raise HTTPException(403, "Không tự kiểm báo cáo của chính mình")

Tài khoản người kiểm chưa nối hồ sơ thì vế đầu sai, và cả phép kiểm biến mất — không lỗi, không
dòng nhật ký, chỉ là một hàng rào không chạy. Cách đó 129 dòng, `_phan_cong_cua_toi` làm ngược lại
là từ chối. Hai mặc định ngược nhau trong cùng một tệp, và cái sai là cái im lặng.

MỘT NỬA CÒN NỢ, bộ này nói thẳng ra chứ không che. Vai kiểm thay chưa nối hồ sơ vẫn ĐI QUA, nhưng
để lại dấu `dinh_danh: "khong_tra_duoc"` trong nhật ký — khai luật, đếm vi phạm, chưa chặn ai, đúng
lời giải `tach_nhiem.py` đã dùng cho `tach_nhiem_bat_buoc_ma_nv_tu`. Bắt buộc ngay hôm nay là khóa
cả HCNS lẫn CNTT ra khỏi cửa kiểm, và phòng Hướng dẫn mất người xác nhận lúc Trưởng phòng vắng.

  A. `tp_hd` — bắt buộc định danh, và không tự kiểm của chính mình.
  B. Vai kiểm thay — đổi vai KHÔNG vượt được chặn; chưa nối hồ sơ thì đi qua nhưng BỊ ĐẾM.
  C. Hàng rào cú pháp: trong cửa kiểm không được có lại nhánh "tra không ra thì bỏ qua".
  D. Chứng minh các ca trên CẮN: dựng lại đúng dòng cũ, đòi chúng đỏ.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd7.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd7.db"):
    os.remove("test_hd7.db")

import ast
import inspect
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
MK = "Vtos@Demo#2026"
ID: dict[str, int] = {}
D = datetime(2026, 11, 20, 6, 0)


def _cap_quyen_kiem_thay(db, *ten_tai_khoan):
    """Cấp năng lực `kiem_bao_cao_tour` cho vai kiểm thay — Đợt HD-10, 13/10/2026.

    Từ HD-10, `hcns` và `cntt` không mặc nhiên xác nhận được báo cáo sau tour (Chủ tịch: *quyền
    quản trị kỹ thuật không tự sinh quyền duyệt*). Cảnh dựng ở đây đi qua ĐÚNG bảng ngoại lệ mà
    đời thật đi qua, kèm lý do và hạn, chứ không nhét một cờ vào mã — cảnh giả thì phép thử xanh
    mà hệ thống thật vẫn chặn.
    """
    from datetime import date as _d
    from datetime import timedelta as _td

    from sqlalchemy import select as _sel

    from app.models.core import User as _U
    from app.models.core import UserGrant as _G
    for un in ten_tai_khoan:
        t = db.execute(_sel(_U).where(_U.username == un)).scalars().first()
        assert t is not None, f"không có tài khoản {un} để cấp quyền"
        db.add(_G(user_id=t.id, kind="capability", value="kiem_bao_cao_tour",
                  from_date=_d.today(), to_date=_d.today() + _td(days=90),
                  reason="Phép thử: vai kiểm thay cần năng lực cấp riêng từ Đợt HD-10.",
                  granted_by="chutich", approved_by="chutich"))
    db.commit()


def login(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _hdv(ma, ten):
    from app.models.hr import Employee
    return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                    start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                    member_org=True, contract_type="ctv", ctv_contract=True)


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    """Bốn phân công GIỐNG HỆT NHAU trên cùng một chuyến, mỗi cái cho một ca kiểm — để mỗi ca có
    một bản báo cáo riêng và không ca nào ăn mất bản của ca kia."""
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment

        db = SessionLocal()
        op = db.execute(select(User)).scalars().first().id

        # Hồ sơ của Trưởng phòng Hướng dẫn — người này VỪA quản lý VỪA đi dẫn tour. Có thật.
        tp = _hdv("H7TP1", "Phạm Văn Trưởng")
        hdv1 = _hdv("H7001", "Trần Văn A")
        t = Tour(code="H7-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([tp, hdv1, t])
        db.commit()

        u_tp = User(username="h7.tp_hd", full_name="Phạm Văn Trưởng", role="tp_hd",
                    department="Hướng dẫn", password_hash=hash_password(MK))
        u_tp_roi = User(username="h7.tp_hd.chua_noi", full_name="TP chưa nối hồ sơ", role="tp_hd",
                        department="Hướng dẫn", password_hash=hash_password(MK))
        u_cntt = User(username="h7.cntt.chua_noi", full_name="CNTT chưa nối", role="cntt",
                      department="", password_hash=hash_password(MK))
        # Tài khoản thứ hai CỦA CHÍNH Trưởng phòng, mang vai kiểm thay — ca "đổi vai để lách".
        u_tp_vai2 = User(username="h7.tp_doi_vai", full_name="Phạm Văn Trưởng", role="hcns",
                         department="", staff_code="H7TP1", password_hash=hash_password(MK))
        u_hdv1 = User(username="h7.hdv.mot", full_name="Trần Văn A", role="hdv",
                      department="Hướng dẫn", password_hash=hash_password(MK))
        db.add_all([u_tp, u_tp_roi, u_cntt, u_tp_vai2, u_hdv1])
        db.commit()
        tp.user_id, hdv1.user_id = u_tp.id, u_hdv1.id
        db.commit()

        def _pc(gid):
            a = GuideAssignment(tour_id=t.id, guide_id=gid, days=4, rate_per_day=800_000,
                                bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
            db.add(a); db.commit()
            return a.id

        # Ba phân công của HDV thường (ca A1, B1, B2) và một của chính Trưởng phòng (ca A2).
        for k in ("a1", "b1", "b2"):
            ID[k] = _pc(hdv1.id)
        ID["cua_tp"] = _pc(tp.id)
        ID["tp_emp"] = tp.id
        _cap_quyen_kiem_thay(db, "h7.cntt.chua_noi", "h7.tp_doi_vai")
        db.close()
        yield


def _nop_va_gui(aid, ai="h7.hdv.mot"):
    """Dựng một bản báo cáo ĐANG CHỜ KIỂM trên phân công này."""
    h = login("h7.cntt.chua_noi")        # cửa lập mở cho nhóm HR_READ + cntt
    r = client.post(f"/api/v1/guide-assignments/{aid}/bao-cao",
                    json={"chuong_trinh_thuc_hien": "đã đi đủ chương trình", "so_khach_thuc_te": 20},
                    headers=h)
    assert r.status_code in (200, 201), r.text
    r = client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/gui", json={}, headers=h)
    assert r.status_code in (200, 201), r.text


def _kiem(aid, ten):
    return client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/kiem",
                       json={"xac_nhan": True}, headers=login(ten))


# ───────────────────────── A · tp_hd bắt buộc định danh ─────────────────────────

def test_a1_tp_hd_co_ho_so_va_khong_phai_HDV_cua_chuyen_thi_kiem_duoc():
    _nop_va_gui(ID["a1"])
    r = _kiem(ID["a1"], "h7.tp_hd")
    assert r.status_code == 200, r.text


def test_a2_tp_hd_DI_TOUR_khong_tu_duyet_bao_cao_cua_chinh_minh():
    """Ca Chủ tịch nêu đích danh. Trưởng phòng Hướng dẫn vừa quản lý vừa dẫn tour — có thật ở
    Vietourist."""
    _nop_va_gui(ID["cua_tp"])
    r = _kiem(ID["cua_tp"], "h7.tp_hd")
    assert r.status_code == 403, r.text
    assert "chính mình" in r.text


def test_a3_tp_hd_CHUA_NOI_ho_so_thi_BI_CHAN_chu_khong_di_qua():
    """Đây đúng chỗ dòng cũ tự tắt: không tra ra người thì phép so biến mất và cửa mở."""
    r = _kiem(ID["cua_tp"], "h7.tp_hd.chua_noi")
    assert r.status_code == 404, r.text
    assert "hồ sơ nhân sự" in r.text


# ───────────────────────── B · vai kiểm thay ─────────────────────────

def test_b1_doi_sang_vai_kiem_thay_KHONG_vuot_duoc_chan():
    """Tài khoản thứ hai của CHÍNH Trưởng phòng, mang vai `hcns`, nối hồ sơ bằng mã nhân viên.
    Chủ tịch: "Nếu tài khoản kiêm nhiều vai, chuyển sang vai HCNS/CNTT cũng không được vượt chặn
    này." Phép so đi theo HỒ SƠ, không theo vai — nên đổi vai không đổi được gì."""
    r = _kiem(ID["cua_tp"], "h7.tp_doi_vai")
    assert r.status_code == 403, r.text


def test_b2_vai_kiem_thay_chua_noi_ho_so_thi_di_qua_NHUNG_bi_dem():
    """Nửa còn nợ, nói thẳng ra chứ không che: chưa chặn, nhưng mỗi lần đi qua để lại một dấu đếm
    được. Cho qua mà có người đếm thì được; cho qua trong im lặng thì không."""
    _nop_va_gui(ID["b1"])
    assert _kiem(ID["b1"], "h7.cntt.chua_noi").status_code == 200

    from sqlalchemy import desc, select

    from app.db.session import SessionLocal
    from app.models.core import AuditLog
    with SessionLocal() as db:
        d = db.execute(select(AuditLog).where(AuditLog.action == "kiem_bao_cao_tour")
                       .order_by(desc(AuditLog.id))).scalars().first()
        assert d is not None, "không có dòng nhật ký nào cho việc kiểm báo cáo"
        # `after` là một TỪ ĐIỂN, không phải chuỗi. Bản nháp đầu của phép thử này viết
        # `"khong_tra_duoc" in d.after` — trên từ điển, phép ấy hỏi KHOÁ chứ không hỏi GIÁ TRỊ, nên
        # nó đỏ trong khi mã hoàn toàn đúng. Đọc đúng ô thì không còn chỗ cho kiểu nhầm ấy.
        assert d.after.get("dinh_danh") == "khong_tra_duoc", \
            f"nhật ký không ghi lại rằng người kiểm chưa định danh được: {d.after!r}"


def test_b3_nhat_ky_ghi_MA_HO_SO_khi_dinh_danh_duoc():
    """Ngược lại của B2: định danh được thì nhật ký phải nói ra người nào, không để trống."""
    _nop_va_gui(ID["b2"])
    assert _kiem(ID["b2"], "h7.tp_hd").status_code == 200

    from sqlalchemy import desc, select

    from app.db.session import SessionLocal
    from app.models.core import AuditLog
    with SessionLocal() as db:
        d = db.execute(select(AuditLog).where(AuditLog.action == "kiem_bao_cao_tour")
                       .order_by(desc(AuditLog.id))).scalars().first()
        assert d.after.get("dinh_danh") == "H7TP1", \
            f"nhật ký không ghi mã hồ sơ người kiểm: {d.after!r}"


# ───────────────────────── C · hàng rào cú pháp ─────────────────────────

def _than(ten_ham: str) -> ast.FunctionDef:
    from app.api.v1 import hr as HR
    cay = ast.parse(Path(inspect.getsourcefile(HR)).read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if isinstance(nut, ast.FunctionDef) and nut.name == ten_ham:
            return nut
    raise AssertionError(f"không tìm thấy hàm {ten_ham}")


def test_c1_cua_kiem_khong_duoc_co_lai_nhanh_tra_khong_ra_thi_bo_qua():
    """Canh bằng CÂY CÚ PHÁP, không tìm chuỗi: khối chú thích ngay trên hàm có chép lại nguyên văn
    dòng cũ để người sau đọc hiểu, nên tìm chuỗi sẽ bắt trúng chính lời giải thích rồi kết luận
    ngược — đúng lỗi của hàng rào BL-2 ngày 12/10."""
    for ten in ("bc_kiem", "_khong_tu_kiem"):
        for nut in ast.walk(_than(ten)):
            if isinstance(nut, ast.BoolOp) and isinstance(nut.op, ast.And):
                for ve in nut.values:
                    if (isinstance(ve, ast.Compare) and len(ve.ops) == 1
                            and isinstance(ve.ops[0], ast.IsNot)
                            and isinstance(ve.comparators[0], ast.Constant)
                            and ve.comparators[0].value is None):
                        raise AssertionError(
                            f"{ten} có nhánh 'is not None and …': tra không ra người thì phép so "
                            "biến mất")


def test_c2_tp_hd_nam_trong_nhom_bat_buoc_dinh_danh():
    from app.api.v1.hr import KIEM_PHAI_DINH_DANH
    assert "tp_hd" in KIEM_PHAI_DINH_DANH


# ───────────────────────── D · chứng minh các ca trên CẮN ─────────────────────────

def test_d1_dung_lai_dong_cu_thi_ca_A3_phai_do():
    """Dòng cũ, chép nguyên văn. Ca A3 phải phân biệt được nó với bản mới; không phân biệt được thì
    A3 chẳng đo gì."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import User
    from app.models.hr import Employee, GuideAssignment

    def cong_cu(u, a) -> bool:
        """True = ĐI QUA."""
        with SessionLocal() as db:
            e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
            return not (e is not None and e.id == a.guide_id)

    with SessionLocal() as db:
        a = db.get(GuideAssignment, ID["cua_tp"])
        u = db.execute(select(User).where(User.username == "h7.tp_hd.chua_noi")).scalars().first()
        # bản CŨ: tài khoản chưa nối hồ sơ đi lọt, không một tiếng động
        assert cong_cu(u, a) is True
    # bản MỚI: chặn
    assert _kiem(ID["cua_tp"], "h7.tp_hd.chua_noi").status_code == 404


def test_d2_dong_cu_cung_de_lot_ca_B1_vi_no_chi_tra_theo_tai_khoan():
    """Ca B1 là LỖ THỨ HAI, không phải lỗ A3 nói lại.

    Dòng cũ tra người CHỈ bằng `Employee.user_id == u.id`. Tài khoản thứ hai của Trưởng phòng nối
    với hồ sơ bằng MÃ NHÂN VIÊN chứ không bằng `user_id` — nên dòng cũ không thấy người, và lối
    "mở tài khoản thứ hai mang vai kiểm thay" đi lọt. Bản mới bắt được nhờ đường lùi theo mã.

    Đây là lý do bảng ở vòng HD-5 liệt kê BỐN dạng tra người chứ không gộp làm một: mỗi dạng để lọt
    một ca khác nhau, và chỉ nhìn một dạng thì không thấy ca của dạng kia."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import User
    from app.models.hr import Employee, GuideAssignment
    with SessionLocal() as db:
        a = db.get(GuideAssignment, ID["cua_tp"])
        u = db.execute(select(User).where(User.username == "h7.tp_doi_vai")).scalars().first()
        # dòng cũ tra theo `user_id` và tài khoản này nối bằng MÃ, nên nó KHÔNG thấy người —
        # tức là dòng cũ cũng để lọt ca này. Bản mới bắt được nhờ đường lùi theo mã nhân viên.
        e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        assert e is None, "dựng sai cảnh: tài khoản này đáng lẽ nối bằng mã, không bằng user_id"
    assert _kiem(ID["cua_tp"], "h7.tp_doi_vai").status_code == 403
