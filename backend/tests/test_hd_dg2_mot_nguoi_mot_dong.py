"""HD-DG2 — MỘT NGƯỜI MỘT DÒNG: bảng điểm thôi tách một hướng dẫn viên làm hai.

Đo được trên main 54c88dd trước vòng này. Một hướng dẫn viên, bốn lượt chấm 5 · 4 · 2 · 1, hai
lượt qua cửa khách tự chấm và hai lượt qua cửa nhân viên ghi hộ. Sự thật: 4 lượt, trung bình 3,0,
hai lượt thấp. Bảng điểm in ra HAI dòng cùng một id, một dòng 3,5 một dòng 2,5, và CẢ HAI cùng
ghi "2 lượt, trong đó 2 lượt thấp".

  A. Tên hiện lên quyết định ở MỘT chỗ, và hai cửa ghi đều đi qua chỗ ấy.
  B. Một người một dòng — kể cả khi đổi tên, kể cả với những lượt chấm CŨ ghi nhãn chung.
  C. Ba con số của một dòng đếm theo CÙNG một khoá và CÙNG một bộ lọc.
  D. Loại KHÔNG có khoá vẫn phải tách ra, không bị dồn vào một dòng.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd_dg2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd_dg2.db"):
    os.remove("test_hd_dg2.db")

from datetime import date, datetime  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models.danh_gia import DG_CO_KHOA, DG_DOI_TUONG  # noqa: E402
from app.services import danh_gia as DG  # noqa: E402

client = TestClient(app)
ID: dict[str, int] = {}
TU, DEN = date(2026, 1, 1), date(2027, 12, 31)


def _nv(db, ma, ten):
    from app.models.hr import Employee
    e = Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                 start_date=date(2024, 1, 1), card_no=ma, card_type="quoc_te",
                 card_expiry=date(2030, 1, 1), member_org=True,
                 contract_type="ctv", ctv_contract=True)
    db.add(e); db.commit()
    return e


def _chuyen(db, op, ma, ten, khach):
    """Một chuyến + một booking + một phiếu chăm sóc. Mỗi lượt chấm cần đủ bộ ba này."""
    from app.models.core import Booking, Tour
    from app.models.cskh import CareTicket
    t = Tour(code=ma, name=ten, tour_type="le_noi_dia", operator_id=op.id,
             start_date=date(2026, 11, 1), end_date=date(2026, 11, 4))
    db.add(t); db.commit()
    b = Booking(code="B-" + ma, tour_id=t.id, customer_name=khach, customer_phone="0900000000",
                pax=2, sales_id=op.id, created_by=op.id, request_id=0, source="thu")
    db.add(b); db.commit()
    c = CareTicket(booking_id=b.id, tour_id=t.id, customer_name=khach,
                   customer_phone="0900000000", han_lien_he=date(2026, 11, 6))
    db.add(c); db.commit()
    return t, c


def _khach_cham(db, care, dong):
    """Khách TỰ chấm — đi qua mã khảo sát, đúng đường đời thật đi."""
    m = DG.sinh_ma(db, care); db.commit()
    DG.ghi_danh_gia(db, m.ma, {"diem": dong, "nhu_cau_tiep": "co",
                               "dong_y_dung_danh_gia": "co"})
    db.commit()


def _ghi_ho(db, op, care, dong):
    DG.ghi_ho(db, op, care, {"diem": dong}); db.commit()


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _op(db):
    from sqlalchemy import select

    from app.models.core import User
    return db.execute(select(User)).scalars().first()


def _dong(bd, did):
    return [r for r in bd["rows"] if r["id"] == did]


# ═════════════════ A · tên quyết định ở MỘT chỗ ═════════════════

def test_a1_loai_co_khoa_lay_ten_tu_ho_so_va_BO_QUA_ten_nguoi_goi_dua_vao():
    """Tên do màn hình gửi lên là thứ sửa được ở phía trình duyệt. Một bảng điểm nhận tên từ bên
    ngoài là một bảng điểm ai cũng gắn điểm cho ai được."""
    with _db() as db:
        e = _nv(db, "DG2-A", "Nguyễn Văn Thật")
        assert DG.ten_doi_tuong(db, "hdv", e.id, "Tên Bịa Đặt") == "Nguyễn Văn Thật"
        assert DG.ten_doi_tuong(db, "hdv", e.id, "") == "Nguyễn Văn Thật"


def test_a2_loai_khong_khoa_lay_ten_goi_y_roi_moi_den_nhan_chung():
    with _db() as db:
        assert DG.ten_doi_tuong(db, "tour", None, "Phú Quốc 4 ngày") == "Phú Quốc 4 ngày"
        assert DG.ten_doi_tuong(db, "tour", None, "") == DG_DOI_TUONG["tour"]
        assert DG.ten_doi_tuong(db, "khach_san", None, "   ") == DG_DOI_TUONG["khach_san"]


def test_a3_ho_so_khong_con_thi_LUI_ve_ten_da_ghi_chu_khong_bo_trong():
    """Cột `doi_tuong_ten` chép tên lúc chấm là CỐ Ý — chú thích ở `models/danh_gia.py` ghi rõ:
    hướng dẫn viên nghỉ việc và hồ sơ bị xoá thì điểm cũ vẫn phải đọc được là chấm cho ai (bài học
    bia mộ tài khoản, TC-83). Vòng này KHÔNG bỏ cột ấy, chỉ thôi dùng nó làm khoá gộp."""
    with _db() as db:
        assert DG.ten_doi_tuong(db, "hdv", 999_999, "Người Đã Nghỉ") == "Người Đã Nghỉ"
        assert DG.ten_doi_tuong(db, "hdv", 999_999, "") == DG_DOI_TUONG["hdv"]


def test_a4_hai_cua_ghi_DEU_di_qua_mot_cho_va_khong_cua_nao_tu_tra_ten():
    """Canh bằng cây cú pháp, không tìm chuỗi: chú thích trong tệp cũng nhắc đúng mấy chữ ấy.

    Hai điều kiện, và cả hai đều cần. Một: cả `ghi_danh_gia` lẫn `ghi_ho` phải GỌI
    `ten_doi_tuong`. Hai: không hàm nào trong hai hàm ấy được tự gọi `db.get(Employee, ...)` để
    lấy tên — thêm một chỗ tra tên là dựng lại đúng cái bản sao thứ hai vừa gỡ đi.
    """
    import ast
    import inspect
    from pathlib import Path

    cay = ast.parse(Path(inspect.getsourcefile(DG)).read_text(encoding="utf-8"))
    for ten_ham in ("ghi_danh_gia", "ghi_ho"):
        than = next((n for n in ast.walk(cay)
                     if isinstance(n, ast.FunctionDef) and n.name == ten_ham), None)
        assert than is not None, f"Không còn hàm {ten_ham}"
        goi = [g for g in ast.walk(than) if isinstance(g, ast.Call)]
        ten_goi = {getattr(g.func, "id", "") or getattr(g.func, "attr", "") for g in goi}
        assert "ten_doi_tuong" in ten_goi, f"{ten_ham} không gọi ten_doi_tuong"
        for g in goi:
            if getattr(g.func, "attr", "") != "get":
                continue
            doi = [a for a in g.args if getattr(a, "id", "") == "Employee"]
            assert not doi, f"{ten_ham} còn tự tra hồ sơ nhân sự thay vì hỏi ten_doi_tuong"


# ═════════════════ B · một người một dòng ═════════════════

def test_b1_hai_cua_ghi_cung_mot_nguoi_thi_bang_diem_ra_DUNG_MOT_dong():
    """Ca chính của vòng. Trước đợt này ra hai dòng, 3,5 và 2,5 — không dòng nào là 3,0."""
    with _db() as db:
        op = _op(db)
        e = _nv(db, "DG2-B1", "Trần Một Dòng")
        for i, (sao, qua_khach) in enumerate([(5, False), (4, True), (2, False), (1, True)]):
            _t, care = _chuyen(db, op, f"DG2-B1-T{i}", f"Chuyến {i}", f"Khách {i}")
            d = [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": sao}]
            if qua_khach:
                _khach_cham(db, care, d)
            else:
                _ghi_ho(db, op, care, d)
        bd = DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False)
        r = _dong(bd, e.id)
        assert len(r) == 1, f"Một người mà ra {len(r)} dòng: {r}"
        assert r[0]["so_luot"] == 4 and r[0]["diem_tb"] == 3.0 and r[0]["so_luot_thap"] == 2
        assert r[0]["ten"] == "Trần Một Dòng"
        ID["b1"] = e.id


def test_b2_doi_ten_trong_ho_so_KHONG_tach_nguoi_ay_lam_hai_dong():
    """Tên là ảnh chụp lúc ghi. Gộp theo tên thì một lần đổi tên là một người thành hai dòng, và
    chuyện đổi tên trong hồ sơ nhân sự xảy ra thật: sửa chính tả, thêm dấu, đổi họ sau kết hôn."""
    with _db() as db:
        from app.models.hr import Employee
        e = db.get(Employee, ID["b1"])
        e.full_name = "Trần Một Dòng (đã đổi tên)"
        db.commit()
        op = _op(db)
        _t, care = _chuyen(db, op, "DG2-B2-T", "Chuyến sau khi đổi tên", "Khách mới")
        _khach_cham(db, care, [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 5}])
        r = _dong(DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False), e.id)
        assert len(r) == 1, f"Đổi tên xong ra {len(r)} dòng: {r}"
        assert r[0]["so_luot"] == 5
        assert r[0]["ten"] == "Trần Một Dòng (đã đổi tên)", "Tên phải lấy lúc ĐỌC, từ hồ sơ"


def test_b3_luot_cham_CU_ghi_nhan_chung_tu_hien_dung_ten_khong_can_va_du_lieu():
    """Những dòng đã lỡ ghi "Hướng dẫn viên" nằm sẵn trong kho. Nếu phải chạy một lệnh vá dữ liệu
    mới đọc đúng thì cái vá ấy là một việc người phải nhớ làm, trên mọi máy chủ, đúng một lần."""
    with _db() as db:
        from app.models.danh_gia import DanhGiaSauTour
        op = _op(db)
        e = _nv(db, "DG2-B3", "Lê Dòng Cũ")
        _t, care = _chuyen(db, op, "DG2-B3-T", "Chuyến cũ", "Khách cũ")
        # Ghi THẲNG vào kho đúng hình dạng dữ liệu cũ: có id, nhưng tên là nhãn chung.
        db.add(DanhGiaSauTour(care_id=care.id, booking_id=care.booking_id, tour_id=care.tour_id,
                              doi_tuong="hdv", doi_tuong_id=e.id,
                              doi_tuong_ten=DG_DOI_TUONG["hdv"], diem=4, nguon="khach",
                              tao_luc=datetime(2026, 11, 5, 9, 0)))
        db.commit()
        r = _dong(DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False), e.id)
        assert len(r) == 1 and r[0]["ten"] == "Lê Dòng Cũ", f"Dòng cũ vẫn mang nhãn chung: {r}"


# ═════════════════ C · ba con số, một khoá, một bộ lọc ═════════════════

def test_c1_so_luot_thap_KHONG_BAO_GIO_lon_hon_so_luot():
    """Bất biến đọc được bằng mắt thường trên màn hình. Trước đợt này nó bị phá: hai cột đếm theo
    hai khoá, nên một dòng nói "2 lượt, trong đó 2 lượt thấp" khi nó chỉ có một lượt thấp."""
    with _db() as db:
        for dt in DG_DOI_TUONG:
            for ck in (True, False):
                for r in DG.bang_diem(db, dt, TU, DEN, chi_khach=ck)["rows"]:
                    assert r["so_luot_thap"] <= r["so_luot"], f"{dt} chi_khach={ck}: {r}"


def test_c2_chi_khach_loc_CA_BA_con_so_chu_khong_chi_loc_hai():
    """Bẫy cũ nằm đúng ở đây: câu truy vấn chính có lọc `nguon`, câu đếm lượt thấp cũng có — nhưng
    chúng là HAI câu, nên người sau sửa một chỗ là xong lệch. Nay là một câu, không lệch được."""
    with _db() as db:
        op = _op(db)
        e = _nv(db, "DG2-C2", "Phạm Lọc Nguồn")
        _t1, c1 = _chuyen(db, op, "DG2-C2-T1", "Khách chấm thấp", "K1")
        _khach_cham(db, c1, [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 2}])
        _t2, c2 = _chuyen(db, op, "DG2-C2-T2", "Nhân viên ghi hộ thấp", "K2")
        _ghi_ho(db, op, c2, [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 1}])

        chi = _dong(DG.bang_diem(db, "hdv", TU, DEN, chi_khach=True), e.id)[0]
        assert (chi["so_luot"], chi["diem_tb"], chi["so_luot_thap"]) == (1, 2.0, 1), chi
        ca = _dong(DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False), e.id)[0]
        assert (ca["so_luot"], ca["diem_tb"], ca["so_luot_thap"]) == (2, 1.5, 2), ca


def test_c3_khoang_ngay_cung_loc_ca_ba_con_so():
    with _db() as db:
        op = _op(db)
        e = _nv(db, "DG2-C3", "Hoàng Ngoài Kỳ")
        _t, care = _chuyen(db, op, "DG2-C3-T", "Chuyến ngoài kỳ", "K")
        _khach_cham(db, care, [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": 1}])
        trong = _dong(DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False), e.id)
        assert trong and trong[0]["so_luot_thap"] == 1
        ngoai = _dong(DG.bang_diem(db, "hdv", date(2020, 1, 1), date(2020, 12, 31),
                                   chi_khach=False), e.id)
        assert not ngoai, f"Lượt chấm ngoài khoảng ngày vẫn lọt vào bảng: {ngoai}"


def test_c4_ba_con_so_phai_sinh_ra_tu_MOT_cau_truy_van():
    """Canh bằng cây cú pháp. Đây là hàng rào giữ cho cái sai cũ không mọc lại dưới hình dạng khác:
    chừng nào `so_luot_thap` còn đến từ một câu đếm RIÊNG trong thân hàm, nó còn có thể lọc khác
    câu chính — và hai cột lại nói hai chuyện."""
    import ast
    import inspect
    from pathlib import Path

    cay = ast.parse(Path(inspect.getsourcefile(DG)).read_text(encoding="utf-8"))
    than = next((n for n in ast.walk(cay)
                 if isinstance(n, ast.FunctionDef) and n.name == "bang_diem"), None)
    assert than is not None, "Không còn hàm bang_diem"
    dem_rieng = 0
    for n in ast.walk(than):
        if not (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "select"):
            continue
        for a in n.args:
            if isinstance(a, ast.Call) and getattr(getattr(a.func, "value", None), "id", "") == "func" \
                    and getattr(a.func, "attr", "") == "count":
                dem_rieng += 1
    assert dem_rieng <= 1, (
        f"Thân bang_diem có {dem_rieng} câu `select(func.count(...))` — số lượt và số lượt thấp "
        "phải ra từ cùng một phép gộp, nếu không hai cột sẽ lọc khác nhau")


# ═════════════════ D · loại KHÔNG có khoá vẫn phải tách ═════════════════

def test_d1_cac_chuyen_khac_nhau_KHONG_bi_don_vao_mot_dong():
    """Gộp theo người là đúng cho hướng dẫn viên và tài xế. `tour`, `khach_san`, `an_uong` không
    có khoá — `doi_tuong_id` luôn rỗng — nên gộp chúng theo id sẽ dồn MỌI chuyến vào một dòng."""
    with _db() as db:
        op = _op(db)
        ten = []
        for i in range(3):
            t, care = _chuyen(db, op, f"DG2-D1-T{i}", f"Chuyến riêng {i}", f"K{i}")
            ten.append(t.name)
            _khach_cham(db, care, [{"doi_tuong": "tour", "diem": 3 + i,
                                    "doi_tuong_ten": t.name}])
        bd = DG.bang_diem(db, "tour", TU, DEN, chi_khach=False)
        co = {r["ten"] for r in bd["rows"]}
        for x in ten:
            assert x in co, f"Chuyến «{x}» biến mất khỏi bảng — các chuyến bị dồn: {bd['rows']}"
        assert all(r["id"] is None for r in bd["rows"])


def test_d2_loai_co_khoa_va_khong_khoa_khai_dung_nhu_bang_khai():
    """Nếu một ngày có người thêm loại mới vào `DG_CO_KHOA` thì bảng điểm đổi cách gộp theo. Ca
    này không canh mã, nó canh cho hai bảng khai không lệch nhau."""
    assert set(DG_CO_KHOA) <= set(DG_DOI_TUONG), "DG_CO_KHOA khai loại không có trong DG_DOI_TUONG"
    assert "hdv" in DG_CO_KHOA and "tour" not in DG_CO_KHOA


# ═════════ E · BA CA CHỦ TỊCH NÊU KHI RÀ SOÁT BẢN ĐẦU, 15/10/2026 ═════════

def test_e1_hai_huong_dan_vien_TRUNG_TEN_van_la_hai_nguoi_va_phan_biet_duoc():
    """Gộp theo mã người thì hai người trùng tên không bị nhập làm một — bản đầu đã đúng chỗ ấy.
    Nhưng hai dòng in ra CHỮ Y HỆT NHAU, nên bảng đúng mà người đọc vẫn không biết dòng nào là
    ai. Mã nhân viên đứng cạnh tên là thứ phân biệt được; `id` không phải, vì màn hình không in
    khoá kỹ thuật ra cho người dùng đọc."""
    with _db() as db:
        op = _op(db)
        a = _nv(db, "DG2-E1A", "Nguyễn Văn Trùng")
        b = _nv(db, "DG2-E1B", "Nguyễn Văn Trùng")
        for e, sao in ((a, 5), (b, 1)):
            _t, care = _chuyen(db, op, f"DG2-E1-{e.code}", "Chuyến trùng tên", "Khách")
            _ghi_ho(db, op, care, [{"doi_tuong": "hdv", "doi_tuong_id": e.id, "diem": sao}])
        ra = DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False)["rows"]
        da = _dong({"rows": ra}, a.id)
        db_ = _dong({"rows": ra}, b.id)
        assert len(da) == 1 and len(db_) == 1, "Hai người trùng tên bị gộp làm một"
        assert da[0]["diem_tb"] == 5.0 and db_[0]["diem_tb"] == 1.0
        assert da[0]["ten"] == db_[0]["ten"] == "Nguyễn Văn Trùng"
        assert da[0]["ma_nv"] == "DG2-E1A" and db_[0]["ma_nv"] == "DG2-E1B", \
            "Hai dòng trùng tên không có gì phân biệt trên màn hình"


def test_e2_LUAT_bat_buoc_co_khoa_nam_mot_cho_va_CA_HAI_cua_ghi_deu_qua():
    """Đo được trên bản đầu: cửa khách tự chấm CHẶN một lượt chấm «hướng dẫn viên» không nói là
    ai, còn cửa ghi hộ thì GHI ĐƯỢC. Hai cửa một luật lại lệch — đúng cái bệnh vòng này chữa."""
    from fastapi import HTTPException
    with _db() as db:
        op = _op(db)
        _t, c1 = _chuyen(db, op, "DG2-E2-A", "Ghi hộ thiếu khoá", "Khách")
        with pytest.raises(HTTPException) as kh:
            DG.ghi_ho(db, op, c1, {"diem": [{"doi_tuong": "hdv", "diem": 2}]})
        assert "cụ thể" in str(kh.value.detail)
        db.rollback()
        _t2, c2 = _chuyen(db, op, "DG2-E2-B", "Khách chấm thiếu khoá", "Khách")
        m = DG.sinh_ma(db, c2); db.commit()
        with pytest.raises(HTTPException):
            DG.ghi_danh_gia(db, m.ma, {"diem": [{"doi_tuong": "hdv", "diem": 2}],
                                       "nhu_cau_tiep": "co", "dong_y_dung_danh_gia": "co"})
        db.rollback()
        # Loại KHÔNG có khoá vẫn phải ghi được bình thường — luật này chỉ dành cho loại có khoá.
        _t3, c3 = _chuyen(db, op, "DG2-E2-C", "Chấm cả chuyến", "Khách")
        DG.ghi_ho(db, op, c3, {"diem": [{"doi_tuong": "tour", "diem": 4}]}); db.commit()


def test_e3_dong_CU_thieu_khoa_khong_bi_doan_nguoi_va_khong_doi_nhan_loai():
    """Hai điều kiện, và cả hai đều cần. Không ĐOÁN: dòng ấy phải ra `id` rỗng, không được gán
    bừa cho ai. Không ĐỘI NHÃN LOẠI: tên "Hướng dẫn viên" đứng lẫn giữa những người thật trông y
    hệt một người tên vậy, mang một điểm trung bình của không ai cả."""
    with _db() as db:
        from app.models.danh_gia import DanhGiaSauTour
        op = _op(db)
        _t, care = _chuyen(db, op, "DG2-E3", "Chuyến cũ thiếu khoá", "Khách")
        # Ghi THẲNG vào kho đúng hình dạng dữ liệu cũ mà cửa ghi hộ từng tạo ra được.
        db.add(DanhGiaSauTour(care_id=care.id, booking_id=care.booking_id, tour_id=care.tour_id,
                              doi_tuong="hdv", doi_tuong_id=None,
                              doi_tuong_ten=DG_DOI_TUONG["hdv"], diem=2, nguon="nhan_vien",
                              tao_luc=datetime(2026, 11, 5, 9, 0)))
        db.commit()
        mo_coi = [r for r in DG.bang_diem(db, "hdv", TU, DEN, chi_khach=False)["rows"]
                  if r["id"] is None]
        assert len(mo_coi) == 1, f"Nhóm không khoá: {mo_coi}"
        assert mo_coi[0]["ten"] != DG_DOI_TUONG["hdv"], \
            "Nhóm không khoá đang đội nhãn loại, trông như một người tên vậy"
        assert mo_coi[0]["ten"] == DG.CHUA_RO_NGUOI
        assert mo_coi[0]["ma_nv"] == ""


def test_e4_moi_luot_cham_duoc_tinh_DUNG_MOT_LAN():
    """Bất biến, không phải một con số. Hôm nay câu truy vấn không nối bảng nào nên nó đúng; hàng
    rào này đứng đó cho ngày ai thêm một phép nối sai điều kiện — lúc ấy mọi con số phình lên
    cùng một lúc và không dòng nào báo, vì bảng vẫn đẹp."""
    from sqlalchemy import func, select

    from app.models.danh_gia import DanhGiaSauTour
    with _db() as db:
        for dt in DG_DOI_TUONG:
            for ck in (True, False):
                loc = [DanhGiaSauTour.doi_tuong == dt, DanhGiaSauTour.diem.is_not(None),
                       func.date(DanhGiaSauTour.tao_luc) >= TU,
                       func.date(DanhGiaSauTour.tao_luc) <= DEN]
                if ck:
                    loc.append(DanhGiaSauTour.nguon == "khach")
                that = db.execute(select(func.count()).select_from(
                    DanhGiaSauTour).where(*loc)).scalar() or 0
                bang = sum(r["so_luot"] for r in DG.bang_diem(db, dt, TU, DEN, chi_khach=ck)["rows"])
                assert that == bang, (
                    f"{dt} chi_khach={ck}: sổ có {that} lượt, bảng cộng lại {bang} — "
                    "một lượt chấm đang được tính nhiều hơn một lần")


def test_e5_hai_cua_ghi_deu_goi_ham_doi_chieu_khoa_chu_khong_chep_lai_luat():
    """Canh bằng cây cú pháp. Cùng một lẽ với ca A4: hai bản sao của một luật thì bản nào rồi
    cũng lệch, và lần này đã lệch thật trước khi Chủ tịch chỉ ra."""
    import ast
    import inspect
    from pathlib import Path

    cay = ast.parse(Path(inspect.getsourcefile(DG)).read_text(encoding="utf-8"))
    for ten_ham in ("ghi_danh_gia", "ghi_ho"):
        than = next((n for n in ast.walk(cay)
                     if isinstance(n, ast.FunctionDef) and n.name == ten_ham), None)
        assert than is not None, f"Không còn hàm {ten_ham}"
        goi = {getattr(g.func, "id", "") or getattr(g.func, "attr", "")
               for g in ast.walk(than) if isinstance(g, ast.Call)}
        assert "doi_chieu_khoa" in goi, f"{ten_ham} không gọi doi_chieu_khoa"
