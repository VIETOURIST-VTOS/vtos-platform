# -*- coding: utf-8 -*-
"""KY-3 · Chênh lệch tỷ giá: ĐO TRƯỚC, GHI SỔ SAU (Chủ tịch quyết 09/10/2026).

Vòng này KHÔNG sửa một con số tiền nào. Lý do nằm ở đầu `services/chenh_lech_ty_gia.py`: tách chênh
lệch ra 635/515 sẽ đổi lãi lỗ của những chuyến đã chốt, nên phải quyết với con số thật trong tay.

HAI ĐIỀU TỆP NÀY GIỮ, VÀ ĐIỀU THỨ HAI QUAN TRỌNG HƠN:

  1. Bộ đếm ra đúng số — ca UK (hai tỷ giá GBP trong một chuyến) phải hiện ra.
  2. Bộ đếm KHÔNG ĐẾM THIẾU. Một bộ đếm thiếu còn tệ hơn không có: nó in ra một con số, người đọc
     tin, và cái thiếu biến mất khỏi tầm mắt. Nên có hàng rào bắt `BANG_NGOAI_TE` phủ HẾT các bảng
     mang ngoại tệ — thêm một bảng mới mà quên khai thì đỏ ngay.

VÀ MỘT HÀNG RÀO GIỮ CHỖ TRỐNG: TK 413 phải TIẾP TỤC không có đường ghi. Đó là kết luận của vòng
này, không phải việc còn dở — 413 dùng để đánh giá lại số dư ngoại tệ, mà sổ cái VTOS không có số
dư ngoại tệ nào. Ai đó "sửa cho đủ" bằng một đường ghi vào 413 thì phép thử đỏ và phải nói ra họ
đang đánh giá lại CÁI GÌ.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ky3.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB):
        os.remove(_DB)
except OSError:
    pass

import re                                            # noqa: E402
from pathlib import Path                             # noqa: E402

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402

GOC = Path(__file__).resolve().parents[2]
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


@pytest.fixture()
def tour(db):
    from app.models.core import Tour
    return db.execute(select(Tour)).scalars().first()


def _pt(db, tour_id, tien_te, ty_gia, ngay, goc=100.0, sl=1.0):
    """Một dòng phương tiện mang ngoại tệ – bảng này khai rõ cột nguyên tệ nên ước tính được tiền."""
    from app.models.lop3_tour import TourPhuongTien
    r = TourPhuongTien(tour_id=tour_id, loai="xe", tien_te=tien_te, ty_gia=ty_gia,
                       ngay_ty_gia=ngay, so_tien_goc=goc, so_luong=sl)
    db.add(r); db.flush()
    return r


# ------------------------------------------------- bộ đếm không được đếm thiếu

def test_khai_du_moi_bang_mang_ngoai_te():
    """Hàng rào đắt nhất tệp. Nó không kiểm một con số nào — nó kiểm BỘ ĐẾM CÓ NHÌN HẾT KHÔNG.

    Thêm một bảng mang cặp cột `tien_te` + `ty_gia` mà quên khai trong `BANG_NGOAI_TE` thì chênh
    lệch của bảng ấy không ai đếm. Và vì bộ đếm vẫn in ra số, không ai biết nó đang đếm thiếu —
    đúng loại im lặng tệ nhất: một con số trông đầy đủ.
    """
    from app.services import chenh_lech_ty_gia as CL
    from app.models import lop3_tour as L
    import inspect
    co_ngoai_te = set()
    for ten, obj in vars(L).items():
        if not inspect.isclass(obj) or not hasattr(obj, "__tablename__"):
            continue
        cot = {c.key for c in getattr(obj, "__table__").columns}
        if {"tien_te", "ty_gia"} <= cot:
            co_ngoai_te.add(obj.__tablename__)
    khai = set(CL.BANG_NGOAI_TE)
    assert co_ngoai_te - khai == set(), (
        f"bảng mang ngoại tệ mà BANG_NGOAI_TE chưa khai: {sorted(co_ngoai_te - khai)} — "
        "chênh lệch của bảng ấy sẽ không ai đếm, mà bộ đếm vẫn in ra số")
    assert khai - co_ngoai_te == set(), f"khai thừa bảng không có ngoại tệ: {sorted(khai - co_ngoai_te)}"


def test_bang_nao_uoc_tinh_duoc_tien_thi_khai_that_thay_vi_doan():
    """Ba bảng không có cột `so_tien_goc`. Khai thẳng là không ước tính được, đừng đoán một cột.

    Đoán bừa `thanh_tien` hay `so_tien` là nguyên tệ rồi nhân tỷ giá thì ra một con số sai mà trông
    rất thật — và không ai kiểm được, vì chính mô hình cũng không nói cột ấy ở đồng nào.
    """
    from app.services import chenh_lech_ty_gia as CL
    assert CL.goc_ro_rang("tour_phuong_tien") is True
    assert CL.goc_ro_rang("tour_ve_khach") is False
    assert CL.goc_ro_rang("tour_ve_thanh_toan") is False


# ------------------------------------------------- ca UK

def test_hai_ty_gia_cung_mot_ngay_la_cho_dang_ngo_nhat(db, tour):
    """Ca UK dựng lại: cùng chuyến, cùng GBP, cùng NGÀY, hai tỷ giá 36.000 và 35.944."""
    from app.services import chenh_lech_ty_gia as CL
    ng = date(2026, 3, 10)
    _pt(db, tour.id, "GBP", 36000, ng, goc=692.34, sl=43)
    _pt(db, tour.id, "GBP", 35944, ng, goc=692.34, sl=43)
    db.flush()
    ra = CL.hai_ty_gia_mot_chuyen(db, tour.id)
    gbp = [x for x in ra if x["tien_te"] == "GBP"]
    assert gbp, "hai tỷ giá GBP trong một chuyến mà không dòng nào báo"
    x = gbp[0]
    assert x["so_ty_gia"] == 2 and x["chenh_ty_gia"] == 56
    assert x["cung_ngay_khac_gia"] == ["2026-03-10"], \
        "hai tỷ giá khác nhau cho CÙNG MỘT NGÀY phải được nêu riêng – đó là chỗ không giải thích được"
    assert x["tien_uoc_tinh"] > 0 and x["uoc_tinh_thieu"] is False


def test_khac_ngay_thi_khac_gia_la_binh_thuong_va_phai_phan_biet(db, tour):
    """Khác ngày nên khác tỷ giá KHÔNG phải lỗi. Gộp chung với ca trên là báo động giả hàng loạt.

    Vẫn liệt kê (để người đọc thấy chuyến này dùng nhiều tỷ giá), nhưng `cung_ngay_khac_gia` rỗng —
    và màn hình xếp những dòng ấy xuống dưới.
    """
    from app.services import chenh_lech_ty_gia as CL
    _pt(db, tour.id, "AUD", 18500, date(2026, 4, 1))
    _pt(db, tour.id, "AUD", 18620, date(2026, 5, 1))
    db.flush()
    aud = [x for x in CL.hai_ty_gia_mot_chuyen(db, tour.id) if x["tien_te"] == "AUD"][0]
    assert aud["so_ty_gia"] == 2
    assert aud["cung_ngay_khac_gia"] == [], "khác ngày mà bị xếp vào rổ cùng-ngày-khác-giá"


def test_mot_ty_gia_thi_khong_bao(db, tour):
    from app.services import chenh_lech_ty_gia as CL
    _pt(db, tour.id, "SGD", 19000, date(2026, 4, 2))
    _pt(db, tour.id, "SGD", 19000, date(2026, 4, 3))
    db.flush()
    assert not [x for x in CL.hai_ty_gia_mot_chuyen(db, tour.id) if x["tien_te"] == "SGD"]


def test_dong_vnd_khong_bi_coi_la_ngoai_te(db, tour):
    """VND và ô trống đều KHÔNG phải ngoại tệ. Đếm nhầm chúng là ngập bộ đếm bằng tiếng ồn.

    BẢN ĐẦU CỦA PHÉP THỬ NÀY LÀ TRANG TRÍ, bẻ ngược mới lộ: nó tạo MỘT dòng VND và MỘT dòng trống,
    rồi hỏi "VND có bị báo không". Nhưng rổ `hai_ty_gia_mot_chuyen` chỉ nhận nhóm có TỪ HAI tỷ giá
    khác nhau — một dòng thì chẳng bao giờ vào rổ, kể cả khi bộ lọc ngoại tệ bị gỡ sạch. Nó khẳng
    định "VND không bị báo" trong đúng tình huống không gì bị báo được.

    Bản này cho mỗi loại HAI dòng hai tỷ giá khác nhau — tức là nếu bộ lọc hỏng thì chúng CHẮC CHẮN
    vào rổ, và lúc ấy câu hỏi mới có nghĩa.
    """
    from app.services import chenh_lech_ty_gia as CL
    _pt(db, tour.id, "VND", 1, date(2026, 4, 4))
    _pt(db, tour.id, "VND", 2, date(2026, 4, 4))
    _pt(db, tour.id, "", 1, date(2026, 4, 5))
    _pt(db, tour.id, "", 2, date(2026, 4, 5))
    db.flush()
    ten = {x["tien_te"] for x in CL.hai_ty_gia_mot_chuyen(db, tour.id)}
    assert "VND" not in ten, "dòng VND bị đếm như ngoại tệ – bộ đếm sẽ ngập tiếng ồn"
    assert "" not in ten, "dòng bỏ trống đồng tiền bị đếm như ngoại tệ"


# ------------------------------------------------- đối chiếu sổ tỷ giá

def _so(db, tien_te, ngay, ty_gia, nguon="Vietcombank"):
    from app.models.ty_gia import TyGia
    r = TyGia(tien_te=tien_te, ngay=ngay, ty_gia=ty_gia, nguon=nguon, nguoi_nhap="test")
    db.add(r); db.flush()
    return r


def test_ba_ro_khac_nhau_cho_ba_viec_khac_nhau(db, tour):
    """Khớp sổ / lệch sổ / sổ chưa có / không có ngày – bốn tình huống, không gộp làm một."""
    from app.services import chenh_lech_ty_gia as CL
    from app.models.lop3_tour import TourVeThanhToan
    ng = date(2026, 6, 10)
    _so(db, "CAD", ng, 19000)
    _pt(db, tour.id, "CAD", 19000, ng)            # khớp sổ
    _pt(db, tour.id, "CAD", 19250, ng)            # lệch sổ
    _pt(db, tour.id, "TWD", 800, date(2026, 6, 11))   # sổ chưa có ngày ấy
    db.add(TourVeThanhToan(tour_id=tour.id, tien_te="JPY", ty_gia=170, so_tien=1000))  # không có cột ngày
    db.flush()

    dc = CL.doi_chieu_so_ty_gia(db, tour.id)
    lech = [x for x in dc["lech_voi_so"] if x["tien_te"] == "CAD"]
    assert len(lech) == 1 and lech[0]["ty_gia"] == 19250, "dòng lệch sổ không được nêu đúng một lần"
    assert lech[0]["ty_gia_trong_so"] == [19000.0] and lech[0]["chenh_gan_nhat"] == 250
    assert not any(x["ty_gia"] == 19000 for x in dc["lech_voi_so"]), "dòng KHỚP sổ bị báo nhầm là lệch"

    thieu = [x for x in dc["so_chua_co"] if x["tien_te"] == "TWD"]
    assert thieu and thieu[0]["ngay"] == "2026-06-11" and thieu[0]["ty_gia_dang_dung"] == [800.0], \
        "ngày sổ chưa có phải nêu kèm tỷ giá đang dùng – đó là cái người nhập cần để đối chiếu"

    jpy = [x for x in dc["thieu_ngay_ty_gia"] if x["tien_te"] == "JPY"]
    assert jpy and "không có cột ngày" in jpy[0]["ly_do"], \
        "dòng không có ngày phải vào rổ riêng, không được đoán một ngày rồi đối chiếu"


def test_hai_nguon_cung_ngay_thi_khop_voi_bat_ky_nguon_nao(db, tour):
    """Sổ cho phép hai nguồn khác nhau cùng ngày, và đó là thiết kế có chủ ý của sổ tỷ giá.

    Nên dòng dùng tỷ giá của NGUỒN NÀO trong sổ cũng là khớp. Đòi khớp đúng một nguồn là tự đặt ra
    luật "nguồn nào mới đúng" — luật ấy sổ tỷ giá cố ý không có, vì máy không chọn hộ.
    """
    from app.services import chenh_lech_ty_gia as CL
    ng = date(2026, 7, 1)
    _so(db, "EUR", ng, 27000, nguon="Vietcombank")
    _so(db, "EUR", ng, 27180, nguon="thực tế chuyển khoản")
    _pt(db, tour.id, "EUR", 27180, ng)
    db.flush()
    assert not [x for x in CL.doi_chieu_so_ty_gia(db, tour.id)["lech_voi_so"] if x["tien_te"] == "EUR"]


# ------------------------------------------------- 413 phải TIẾP TỤC trống

def test_413_van_khong_co_duong_ghi_va_do_la_ket_luan(db):
    """Giữ một chỗ trống CÓ LÝ DO, và bắt người sửa sau phải nói ra lý do mới.

    413 đánh giá lại số dư ngoại tệ cuối kỳ. `JournalLine` không có cột ngoại tệ nào – sổ cái toàn
    VND – nên không có số dư ngoại tệ để đánh giá lại. Ai thêm một đường ghi vào 413 thì phép thử
    này đỏ, và họ phải trả lời: đánh giá lại CÁI GÌ.
    """
    from app.models.accounting import JournalLine
    cot = {c.key for c in JournalLine.__table__.columns}
    assert "tien_te" not in cot and "ty_gia" not in cot, (
        "JournalLine nay mang ngoại tệ – nếu đúng thì sổ cái ĐÃ có số dư ngoại tệ và 413 phải có "
        "đường ghi; sửa phép thử này kèm ngày và người quyết")
    ma = (GOC / "backend" / "app").rglob("*.py")
    pham = []
    for f in ma:
        if f.name == "accounting.py" and f.parent.name == "services":
            continue                       # danh mục tài khoản được phép nhắc tên 413
        if f.name == "chenh_lech_ty_gia.py":
            continue                       # tệp này nhắc 413 để GIẢI THÍCH vì sao nó trống
        t = f.read_text(encoding="utf-8")
        if re.search(r'"account"\s*:\s*"413', t) or re.search(r'account\s*=\s*"413"', t):
            pham.append(str(f.relative_to(GOC)))
    assert not pham, f"có đường ghi sổ vào TK 413 ở: {pham} – xem docstring phép thử này"


# ------------------------------------------------- cửa và lời

def test_cua_tra_loi_va_noi_ra_minh_chi_la_ban_do(db):
    r = client.post("/api/v1/auth/login", data={"username": "ketoan", "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    kq = client.get("/api/v1/ty-gia/chenh-lech", headers=h)
    assert kq.status_code == 200, kq.text
    d = kq.json()
    for k in ("hai_ty_gia_mot_chuyen", "lech_voi_so", "so_chua_co", "thieu_ngay_ty_gia",
              "bang_duoc_quet", "ghi_chu"):
        assert k in d, f"cửa thiếu khóa {k}"
    assert "ĐO" in d["ghi_chu"] and "635" in d["ghi_chu"] and "413" in d["ghi_chu"], \
        "cửa phải nói rõ đây là bản đo, chênh lệch sẽ đi đâu nếu được ký, và vì sao 413 trống"
    assert d["tai_khoan"] == {"danh_gia_lai": "413", "lo": "635", "lai": "515"}


def test_cua_khong_doi_ma_tran_quyen():
    """Đặt dưới `/api/v1/ty-gia` là có chủ ý: màn hình Tỷ giá đã khai tiền tố ấy, nên 0 dòng đổi."""
    from app.services import access as AC
    assert "/api/v1/ty-gia" in AC.MAN_HINH_API["/ty-gia"]
    nguon = (GOC / "backend" / "app" / "api" / "v1" / "ty_gia.py").read_text(encoding="utf-8")
    assert '@router.get("/chenh-lech")' in nguon

def test_man_hinh_ty_gia_goi_dung_cua_va_in_ra_cai_nguoi_doc_lam_duoc():
    """Bộ đếm mà không ai thấy thì bằng không có. Và so ĐƯỜNG ĐẦY ĐỦ, không so khúc đầu.

    Bài học kiểm ngược của NS-2: `"/chenh-lech" in nguon` vẫn xanh khi ai đó đổi tên đường thành
    `/chenh-lech-tam`, vì chuỗi cũ là khúc đầu của chuỗi mới.
    """
    mh = (GOC / "web" / "app" / "ty-gia" / "page.tsx").read_text(encoding="utf-8")
    assert re.search(r'"/ty-gia/chenh-lech"', mh), "màn hình Tỷ giá chưa gọi đúng cửa chênh lệch"
    assert "cl.ghi_chu" in mh, "khung phải IN RA câu máy chủ nói, không tự đặt lời"
    # Hai con số này là hai VIỆC của hai người: Điều hành sửa chỗ hai tỷ giá, nhân viên nhập chỗ sổ
    # còn thiếu. In gộp thành một số "có vấn đề" thì không ai biết phần nào là việc của mình.
    assert "cl.so_chuyen_cung_ngay_khac_gia" in mh, "khung chưa nêu chỗ đáng ngờ nhất"
    assert "cl.so_cap_so_chua_co" in mh, "khung chưa nói sổ còn thiếu bao nhiêu ngày – đó là cửa nhập"
