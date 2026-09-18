# -*- coding: utf-8 -*-
"""PR-1 · Sổ hoạt động PR — người phát ngôn, và đồng hồ hai giờ của khủng hoảng truyền thông.

Chủ tịch chốt 18/9/2026 hai điều, và cả hai đều hỏng LẶNG nếu làm sai:

  1. NGƯỜI PHÁT NGÔN LÀ P.TGĐ MARKETING. Làm sai kiểu rẻ nhất là thêm một ô gõ tên: sổ vẫn đầy
     đủ, mọi dòng đều có tên, và đúng vào hôm cần tra "ai đã nói câu đó" thì cái tên ấy không nối
     được với tài khoản nào.
  2. KHỦNG HOẢNG TRUYỀN THÔNG: 2 GIỜ kể từ lúc việc được GHI VÀO SỔ. Làm sai kiểu rẻ nhất là cho
     người nhập gõ mốc bắt đầu — ai sắp quá hạn chỉ cần lùi mốc lại, và con số "quá hạn" trên màn
     hình vẫn xanh, vẫn đẹp, vẫn vô nghĩa.

Cộng hai chỗ nối dễ tuột: LUẬT VIẾT HAI LẦN (Python và SQL) phải ra cùng một tập, và phép ĐẾM
phải đếm trên CẢ SỔ chứ không trên trang đang xem — đúng lỗi đã mắc và đã sửa ở sổ lead cùng ngày.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_pr1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_pr1.db", "test_pr1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import inspect  # noqa: E402
import re  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.marketing import PR_LOAI, PrHoatDong  # noqa: E402
from app.services import intake_pr as IN  # noqa: E402
from app.services import pr_hoat_dong as PR  # noqa: E402

Base.metadata.create_all(engine)
GIO = 2.0
BAY_GIO = datetime(2026, 9, 18, 12, 0, 0)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(PrHoatDong).delete()
    s.commit()
    yield s
    s.close()


def dong(**kw):
    return {"loai": "bai_bao", "tieu_de": "Vietourist mở tuyến charter Phú Quốc",
            "noi_dang": "Báo Thanh Niên", **kw}


def vu(db, truoc_bao_lau_gio: float, **kw):
    """Một việc đã vào sổ cách đây N giờ."""
    h, _ = IN.nap(db, dong(**kw), "nv_mkt")
    h.ghi_nhan_luc = BAY_GIO - timedelta(hours=truoc_bao_lau_gio)
    db.flush()
    return h


# =============================================================================================
# 1. ĐỒNG HỒ HAI GIỜ — và nó chỉ chạy cho vụ khủng hoảng
# =============================================================================================

def test_HAN_doc_tu_THAM_SO_co_nguoi_ky_chu_khong_viet_cung_so_2(db):
    """Một con số không có người ký là một con số không ai bảo vệ được khi có người muốn đổi."""
    from app.services import rules as R

    assert PR.gio_han(db) == 2.0
    d = next((t for t in R.DEFAULT_PARAMS if t[0] == PR.THAM_SO_GIO), None)
    assert d, f"thiếu tham số {PR.THAM_SO_GIO}"
    assert d[3] == "giờ" and d[4], "tham số phải ghi đơn vị và ai chốt"
    ma = inspect.getsource(PR)
    assert not re.search(r"timedelta\(hours=2\b", ma), "số 2 đang viết cứng trong mã"


def test_viec_KHONG_phai_khung_hoang_thi_KHONG_co_han(db):
    """Gán hạn hai giờ cho một bài đăng mạng xã hội là làm hỏng chính con số cần nhìn: bảng quá
    hạn đầy những dòng không ai coi là gấp thì không ai nhìn bảng ấy nữa."""
    h = vu(db, 10)
    db.commit()
    assert h.la_khung_hoang is False
    assert PR.han_phan_hoi(h, GIO) is None
    assert PR.qua_han(h, GIO, BAY_GIO) is False


def test_vu_khung_hoang_qua_2_gio_chua_phan_hoi_la_QUA_HAN(db):
    h = vu(db, 3, la_khung_hoang=True, muc_do="vua")
    db.commit()
    assert PR.han_phan_hoi(h, GIO) == h.ghi_nhan_luc + timedelta(hours=2)
    assert PR.qua_han(h, GIO, BAY_GIO) is True


def test_chua_toi_2_gio_thi_CHUA_qua_han(db):
    h = vu(db, 1.5, la_khung_hoang=True)
    db.commit()
    assert PR.qua_han(h, GIO, BAY_GIO) is False


def test_DA_PHAN_HOI_thi_khong_con_qua_han_du_da_lau(db):
    """Vụ xử lý xong mà vẫn nằm ở bảng quá hạn thì bảng ấy mất hết ý nghĩa."""
    h = vu(db, 30, la_khung_hoang=True)
    h.phan_hoi_luc = h.ghi_nhan_luc + timedelta(hours=1)
    db.commit()
    assert PR.qua_han(h, GIO, BAY_GIO) is False


def test_MOC_DEM_la_luc_VAO_SO_chu_khong_phai_luc_viec_xay_ra(db):
    """Lấy lúc xảy ra thì một vụ phát hiện muộn ba ngày đã quá hạn ngay khi vừa ghi, và con số
    quá hạn thành vô nghĩa. Lấy lúc vào sổ thì nó đo đúng cái đo được: từ khi công ty BIẾT, bao
    lâu thì công ty TRẢ LỜI."""
    truoc = datetime.now()
    h, _ = IN.nap(db, dong(la_khung_hoang=True), "nv_mkt")
    db.commit()
    assert truoc <= h.ghi_nhan_luc <= datetime.now()
    # Và cửa nhập KHÔNG có ô để gõ mốc ấy.
    keys = {c["key"] for c in IN.bo_nap(__import__("app.services.intake", fromlist=["_c"])._c)
            ["hoat_dong_pr"]["cot"]}
    assert "ghi_nhan_luc" not in keys
    assert IN.kiem(db, dong(ghi_nhan_luc="2026-09-01 08:00"))[0], \
        "gõ mốc bắt đầu vào cửa nhập phải là LỖI – ai sắp quá hạn chỉ cần lùi mốc lại"


# =============================================================================================
# 2. HAI BẢN CỦA MỘT LUẬT, VÀ PHÉP ĐẾM ĐẾM TRÊN CẢ SỔ
# =============================================================================================

def test_HAI_BAN_CUA_MOT_LUAT_python_va_SQL_phai_ra_cung_mot_tap(db):
    """Sổ dựng ra cố ý có đủ năm dạng, kể cả ba dạng dễ quên: không phải khủng hoảng nhưng đã lâu;
    khủng hoảng đã phản hồi; và khủng hoảng vừa đúng bên trong hạn."""
    vu(db, 10)                                             # không phải khủng hoảng
    vu(db, 3, la_khung_hoang=True)                         # quá hạn
    vu(db, 9, la_khung_hoang=True)                         # quá hạn
    vu(db, 1.5, la_khung_hoang=True)                       # còn trong hạn
    d = vu(db, 20, la_khung_hoang=True)
    d.phan_hoi_luc = d.ghi_nhan_luc + timedelta(minutes=30)  # đã phản hồi
    db.commit()

    theo_python = {h.id for h in db.execute(select(PrHoatDong)).scalars()
                   if PR.qua_han(h, GIO, BAY_GIO)}
    theo_sql = {h.id for h in db.execute(
        PR.loc_qua_han(select(PrHoatDong), GIO, BAY_GIO)).scalars()}
    assert theo_python == theo_sql, "bộ lọc SQL và phép tính Python đang nói hai điều khác nhau"
    assert len(theo_python) == 2


def test_DEM_QUA_HAN_dem_tren_CA_SO_khong_dem_tren_trang_dang_xem(db):
    """Đếm trên một câu truy vấn đã cắt trang thì con số nhỏ hơn sự thật, và nhỏ một cách IM LẶNG
    – đúng lỗi đã mắc và đã sửa ở sổ lead ngày 18/9/2026."""
    for _ in range(5):
        vu(db, 4, la_khung_hoang=True)
    db.commit()
    assert PR.dem_qua_han(db, GIO, BAY_GIO) == 5
    ma = inspect.getsource(PR.dem_qua_han)
    assert "select(PrHoatDong)" in ma, "phép đếm phải tự dựng câu truy vấn của nó, không nhận từ ngoài"


def test_THE_QUA_HAN_tren_man_hinh_doc_tu_phep_dem_ca_so(db):
    """Người đọc thẻ này hỏi "công ty đang nợ mấy câu trả lời", không hỏi "trang này có mấy dòng đỏ"."""
    for _ in range(3):
        vu(db, 4, la_khung_hoang=True)
    # Dòng thứ tư phải CÒN TRONG HẠN so với ĐỒNG HỒ THẬT, vì `bang()` đếm theo `datetime.now()`
    # chứ không nhận mốc giả – nó là bản trả về cho màn hình. Đặt mốc theo BAY_GIO ở đây là dựng
    # một dòng đã quá hạn từ lâu, và phép thử đi bắt nhầm người (đã mắc đúng lỗi ấy lúc viết).
    moi, _ = IN.nap(db, dong(la_khung_hoang=True), "nv_mkt")
    moi.ghi_nhan_luc = datetime.now()
    db.commit()
    b = PR.bang(db, loai="mang_xa_hoi")                 # lọc ra một tập RỖNG
    assert b["rows"] == []
    assert b["dem"]["qua_han"] == 3, "thẻ quá hạn phải đếm trên cả sổ, không theo bộ lọc đang xem"


# =============================================================================================
# 3. NGƯỜI PHÁT NGÔN
# =============================================================================================

def test_NGUOI_PHAT_NGON_khong_phai_o_go_ten_tu_do(db):
    keys = {c["key"] for c in IN.bo_nap(__import__("app.services.intake", fromlist=["_c"])._c)
            ["hoat_dong_pr"]["cot"]}
    assert "nguoi_phat_ngon" not in keys
    assert IN.kiem(db, dong(nguoi_phat_ngon="Anh Tuấn"))[0], \
        "gõ tên người phát ngôn vào cửa nhập phải là LỖI"


def test_HANG_RAO_phat_ngon_khai_o_cho_MAY_DOC_DUOC_va_dung_mot_vai(db):
    """Một câu `if` trong thân hàm thì bảng phân quyền toàn hệ không đếm được nó, mà cái gì không
    đếm được thì không rà soát được. Bài học trả giá cùng ngày ở sổ tài sản thương hiệu."""
    from app.api.v1 import marketing as API
    from app.services import rules as R

    ma = inspect.getsource(API.pr_phat)
    trong_rao = set(re.findall(r"require_roles\(([^)]*)\)", ma)[0].replace('"', "").replace(" ", "").split(","))
    assert trong_rao == {"ptgd_mkt"}, "chỉ P.TGĐ Marketing bấm được nút phát"
    d = next((t for t in R.DEFAULT_PARAMS if t[0] == PR.THAM_SO_VAI_PHAT_NGON), None)
    assert d and d[1] == "ptgd_mkt", "tham số và hàng rào đang khai hai vai khác nhau"
    assert d[4], "tham số không ghi ai chốt"


def test_PHAT_ghi_ten_NGUOI_BAM_chu_khong_ghi_ten_VAI(db):
    """Sáu tháng sau câu hỏi là "ai đã nói", không phải "vai nào đã nói"."""
    h = vu(db, 1)
    kq = PR.phat(db, h, "ptgd.mkt")
    db.commit()
    assert h.nguoi_phat_ngon == "ptgd.mkt" and h.trang_thai == "da_phat"
    assert h.phat_luc is not None and "ptgd.mkt" in kq["message"]


def test_PHAT_mot_vu_khung_hoang_CHINH_LA_phan_hoi(db):
    """Bắt bấm thêm một nút "đã phản hồi" nữa là dựng ra một ô sẽ bị quên, và bảng quá hạn sẽ đầy
    những dòng đã xử lý xong."""
    h = vu(db, 1, la_khung_hoang=True)
    PR.phat(db, h, "ptgd.mkt")
    db.commit()
    assert h.phan_hoi_luc == h.phat_luc and h.phan_hoi_boi == "ptgd.mkt"
    assert PR.qua_han(h, GIO, BAY_GIO + timedelta(hours=99)) is False


def test_PHAT_HAI_LAN_bi_tu_choi(db):
    h = vu(db, 1)
    PR.phat(db, h, "ptgd.mkt")
    db.commit()
    with pytest.raises(ValueError):
        PR.phat(db, h, "ptgd.mkt")


def test_cua_nhap_KHONG_dat_thang_trang_thai_da_phat(db):
    assert IN.kiem(db, dong(trang_thai="da_phat"))[0]
    assert IN.kiem(db, dong(trang_thai="nhap"))[0] == []


# =============================================================================================
# 4. GHI PHẢN HỒI BẰNG ĐƯỜNG KHÁC
# =============================================================================================

def test_ghi_phan_hoi_cho_vu_xu_ly_bang_dien_thoai(db):
    """Không vụ nào cũng kết thúc bằng một bài đăng. Không có cửa này thì những vụ ấy nằm mãi ở
    bảng quá hạn."""
    h = vu(db, 1, la_khung_hoang=True)
    kq = PR.ghi_phan_hoi(db, h, "nv_mkt")
    db.commit()
    assert h.phan_hoi_luc is not None and h.phan_hoi_boi == "nv_mkt"
    assert kq["sau_bao_lau_gio"] >= 0
    assert PR.qua_han(h, GIO, BAY_GIO + timedelta(hours=99)) is False


def test_ghi_phan_hoi_cho_viec_KHONG_phai_khung_hoang_bi_tu_choi(db):
    h = vu(db, 1)
    with pytest.raises(ValueError):
        PR.ghi_phan_hoi(db, h, "nv_mkt")


def test_ghi_phan_hoi_HAI_LAN_bi_tu_choi(db):
    h = vu(db, 1, la_khung_hoang=True)
    PR.ghi_phan_hoi(db, h, "nv_mkt")
    db.commit()
    with pytest.raises(ValueError):
        PR.ghi_phan_hoi(db, h, "nv_mkt")


# =============================================================================================
# 5. CỬA NHẬP
# =============================================================================================

def test_bang_nay_CO_mot_cua_nhap(db):
    """Ranh giới 09/9: bảng không có cửa là VIỆC CÒN THIẾU."""
    from app.services import ks_cua_nhap as K
    from app.services.intake import BO_NAP

    assert BO_NAP["hoat_dong_pr"]["bang_dich"] == "mkt_pr_hoat_dong"
    assert "mkt_pr_hoat_dong" not in K.bang()["khong_cua"]


def test_thieu_tieu_de_hoac_loai_la_LOI(db):
    assert any("tiêu đề" in x.lower() for x in IN.kiem(db, dong(tieu_de=""))[0])
    assert any("loại" in x.lower() for x in IN.kiem(db, dong(loai=""))[0])
    assert any("danh mục" in x for x in IN.kiem(db, dong(loai="podcast"))[0])
    assert set(PR_LOAI) >= {"bai_bao", "thong_cao", "su_kien", "phat_ngon", "khung_hoang"}


def test_khung_hoang_chua_biet_muc_do_chi_la_CANH_BAO(db):
    """Lúc một vụ vừa nổ ra, người ghi chưa chắc đã biết nó to đến đâu. Chặn ở đây là buộc người
    ta đoán một mức độ, hoặc không ghi gì cả – mà không ghi thì đồng hồ không bao giờ bắt đầu."""
    loi, cb, _ = IN.kiem(db, dong(la_khung_hoang=True))
    assert loi == []
    assert any("mức độ" in x for x in cb)


def test_KHONG_co_khoa_chong_trung_va_do_la_chu_y(db):
    """Hai bài báo cùng tiêu đề trên hai tờ báo là hai việc thật. Gộp chúng là xoá mất một việc."""
    IN.nap(db, dong(noi_dang="Báo Thanh Niên"), "nv_mkt")
    IN.nap(db, dong(noi_dang="Báo Tuổi Trẻ"), "nv_mkt")
    db.commit()
    assert db.query(PrHoatDong).count() == 2
    assert len({h.ma for h in db.query(PrHoatDong)}) == 2, "mã phải khác nhau"


def test_SO_NAY_CAT_THEO_PHAM_VI_PHAP_NHAN_va_cho_noi_nam_o_bang():
    """`PrHoatDong` khai trong `pham_vi_phap_nhan.PHAI_LOC`. Khai mà không nối là một lời hứa
    không giữ — kho này đã có 22 mô hình khai và chỉ 5 chỗ gọi `PV.loc`, nên chỗ nối của sổ này
    phải có thật chứ không để lại thành món nợ thứ 18."""
    from app.services import pham_vi_phap_nhan as PV

    assert "PrHoatDong" in PV.PHAI_LOC
    assert "PrHoatDong" not in PV.CO_Y_KHONG_LOC, "không được khai ở cả hai danh sách"
    assert "PV.loc(q, PrHoatDong" in inspect.getsource(PR.bang), \
        "đã khai PHẢI LỌC nhưng chưa nối phép lọc vào chỗ đọc sổ"
