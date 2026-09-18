# -*- coding: utf-8 -*-
"""MKT-2 · Cửa nhập của phòng Marketing.

Cửa nhập là chỗ duy nhất số liệu vào được hệ thống, nên nó cũng là chỗ duy nhất chặn được số sai.
Tệp này canh bốn chuyện:

  1. RANH GIỚI LỖI / CẢNH BÁO. Bắt lỗi quá tay thì nhân viên không nhập được và quay về Excel;
     cảnh báo quá tay thì không ai đọc nữa. Quy ước: chỉ báo LỖI khi dòng ấy sẽ làm SAI một con
     số; thiếu thông tin thì cảnh báo.
  2. HAI Ô KÊNH, VÀ KHÔNG ĐOÁN Ô CÒN LẠI. Đoán một lần là con số mang phép đoán ấy mãi mãi.
  3. KHOÁ CHỐNG TRÙNG giữ được hai lượt liên hệ thật, và gộp được hai lần gọi cùng một nơi.
  4. BA THỨ CỦA VIỆC GIAO SALES đi với nhau – thiếu một thì "quá hạn" không tính được.
"""
from datetime import date, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import marketing as _mkt  # noqa: F401  – bảng campaigns mà leads.campaign_id trỏ tới
from app.models.core import Booking, Tour  # noqa: F401
from app.models.crm import Lead, LeadChannelStat
from app.services import intake_marketing as I
from app.services.intake import _c

HOM_NAY = date.today()
BO = I.bo_nap(_c)


@pytest.fixture()
def db():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    with Session(m) as s:
        yield s


def dong(**kw):
    """Một dòng hợp lệ tối thiểu; phép thử chỉ đổi đúng thứ nó đang canh.

    Bản 2 thêm `phat_sinh_luc`: sau góp ý 13/9, dòng chỉ có kỳ mà không có giờ là dòng CHƯA ĐỦ
    cho phép tính theo mốc 30/60/90 ngày, nên nó phải kêu. "Dòng đủ thông tin" từ nay có giờ.
    """
    return {"sdt": "0901234567", "thang": "2026-09", "diem_tiep_nhan": "hotline_1",
            "nguon_thu_hut": "facebook", "mang": "le",
            "phat_sinh_luc": "2026-09-13 09:20", **kw}


def loi(db, **kw):
    return I.kiem_lead(db, dong(**kw))[0]


def canh_bao(db, **kw):
    return I.kiem_lead(db, dong(**kw))[1]


# =============================================================================================
# 1. Ranh giới lỗi / cảnh báo
# =============================================================================================

def test_dong_du_thong_tin_thi_khong_loi_khong_canh_bao(db):
    e, cb, khoa = I.kiem_lead(db, dong())
    assert e == [] and cb == []
    # Khoá là MÃ LEAD, và dòng chưa có mã thì khoá rỗng – mã do hệ thống cấp lúc nạp, không phải
    # lúc kiểm. Bản 1 ghép khoá từ sdt|kỳ|điểm tiếp nhận; khoá ấy sai theo cả hai chiều cùng lúc.
    assert khoa is None
    assert I.kiem_lead(db, dong(ma_lead="L2026-09-0007"))[2] == "L2026-09-0007"


def test_THIEU_SO_DIEN_THOAI_la_LOI(db):
    """Số điện thoại là thứ duy nhất nối lead với booking. Không có nó thì dòng ấy không bao giờ
    đếm được vào tỷ lệ chốt – nhận vào là tự làm hỏng mẫu số."""
    assert any("Thiếu số điện thoại" in x for x in loi(db, sdt=""))


def test_THIEU_DIEM_TIEP_NHAN_la_LOI(db):
    """Phải biết cuộc liên hệ rơi vào đâu – đây là khoá chống trùng, thiếu thì không chống được."""
    assert any("Thiếu điểm tiếp nhận" in x for x in loi(db, diem_tiep_nhan=""))


def test_THIEU_NGUON_chi_la_CANH_BAO(db):
    """Khách không nhớ biết tới mình từ đâu là chuyện thường ngày. Bắt lỗi ở đây thì nhân viên
    hoặc bịa một nguồn, hoặc bỏ không nhập – cả hai đều tệ hơn một ô trống thành thật."""
    assert loi(db, nguon_thu_hut="") == []
    assert any("Chưa biết nguồn thu hút" in x for x in canh_bao(db, nguon_thu_hut=""))


def test_canh_bao_thieu_nguon_noi_ro_DONG_VAN_DUOC_DEM(db):
    """Người nhập phải biết dòng của mình không bị vứt đi, nếu không họ sẽ bịa cho đủ ô."""
    cb = " ".join(canh_bao(db, nguon_thu_hut=""))
    assert "vẫn được nhận" in cb and "vẫn đếm vào tổng" in cb


def test_THIEU_NHOM_KHACH_chi_la_CANH_BAO(db):
    assert loi(db, mang="") == []
    assert any("lẻ hay đoàn" in x for x in canh_bao(db, mang=""))


def test_gia_tri_ngoai_danh_muc_la_LOI(db):
    """Ô chọn mà nhận giá trị lạ thì ba tháng sau không tổng hợp được gì."""
    assert any("không có trong danh mục" in x for x in loi(db, nguon_thu_hut="tiktok_shop"))
    assert any("không có trong danh mục" in x for x in loi(db, diem_tiep_nhan="messenger"))
    assert any("không hợp lệ" in x for x in loi(db, mang="doan"))
    assert any("không hợp lệ" in x for x in loi(db, trang_thai="dang_cho"))


def test_so_dien_thoai_thieu_so_van_NHAN_nhung_noi_ra(db):
    """Số cũ nhập thiếu là dữ liệu có thật. Vứt đi thì mất một lần liên hệ; nhận im lặng thì sau
    này không ai hiểu vì sao nó không khớp booking nào."""
    assert loi(db, sdt="090123456") == []
    assert any("không đối chiếu được với booking" in x for x in canh_bao(db, sdt="090123456"))


# =============================================================================================
# 2. Hai ô kênh, và không đoán ô còn lại
# =============================================================================================

def test_hai_o_kenh_la_HAI_COT_RIENG_trong_khai_bao():
    cot = {c["key"]: c for c in BO["khach_tiem_nang"]["cot"]}
    assert "nguon_thu_hut" in cot and "diem_tiep_nhan" in cot
    assert cot["diem_tiep_nhan"]["bat_buoc"] is True
    assert cot["nguon_thu_hut"]["bat_buoc"] is False, \
        "bắt buộc nguồn thu hút thì nhân viên sẽ bịa cho đủ ô"


def test_hai_danh_muc_KHONG_TRUNG_gia_tri_nao():
    """Trùng một mã giữa hai danh mục là mở đường cho chính cái lỗi đang sửa: một giá trị đứng
    được ở cả hai trục thì lại không biết nó là trục nào."""
    assert not (set(I.NGUON_THU_HUT) - {"khac"}) & (set(I.DIEM_TIEP_NHAN) - {"khac"})


def test_cua_nhap_KHONG_suy_nguon_tu_diem_tiep_nhan(db):
    """Khách gọi hotline có thể đến từ Facebook, từ biển quảng cáo, từ bạn giới thiệu."""
    e, cb, _ = I.kiem_lead(db, dong(nguon_thu_hut=""))
    assert e == []
    I.nap_lead(db, dong(nguon_thu_hut=""), "nv_mkt")
    db.commit()
    x = db.query(Lead).first()
    assert x.nguon_thu_hut is None, "cửa nhập đang đoán hộ nguồn thu hút"
    assert x.diem_tiep_nhan == "hotline_1"


def test_khach_cu_QUAY_LAI_tach_khoi_khach_cu_GIOI_THIEU():
    """Một bên là khách tự đi tiếp, một bên là khách mang người mới tới. Gộp hai thứ ấy thì không
    đo được sức giới thiệu của tệp khách cũ."""
    assert "khach_cu" in I.NGUON_THU_HUT and "gioi_thieu" in I.NGUON_THU_HUT
    assert I.NGUON_THU_HUT["khach_cu"] != I.NGUON_THU_HUT["gioi_thieu"]


# =============================================================================================
# 3. Khoá chống trùng
# =============================================================================================

def test_hai_noi_nhan_khac_nhau_thi_la_HAI_LEAD(db):
    """Gọi hotline rồi nhắn Zalo là hai lượt liên hệ THẬT. Gộp là xoá mất một lần có thật."""
    I.nap_lead(db, dong(diem_tiep_nhan="hotline_1"), "nv")
    I.nap_lead(db, dong(diem_tiep_nhan="zalo_oa"), "nv")
    db.commit()
    assert db.query(Lead).count() == 2
    assert len({x.ma_lead for x in db.query(Lead)}) == 2


def test_nhap_lai_CUNG_MOT_TEP_khong_nhan_doi_lead(db):
    """Điều kiện nghiệm thu 1 của góp ý: nhập lại cùng file không nhân đôi lead."""
    _, tt1 = I.nap_lead(db, dong(ten="A"), "nv")
    db.commit()
    _, tt2 = I.nap_lead(db, dong(ten="A"), "nv")
    db.commit()
    assert tt1 == "moi" and tt2 == I.TRUNG_CHO_XU_LY
    assert db.query(Lead).count() == 1


def test_dong_trung_khit_KHONG_TU_GHI_DE_len_dong_cu(db):
    """Điều kiện nghiệm thu 4: dòng trùng khít đưa xử lý, KHÔNG tự coi là giao dịch mới.

    Và cũng không được lặng lẽ ghi đè. Bản 1 ghi đè – nghĩa là nếu tệp nhập lại có một ô bị gõ
    sai, ô sai ấy thay thế dữ liệu đúng đang có mà không ai biết. Phép thử này canh cả hai chiều:
    không thêm dòng, và cũng không đổi dòng đang có.
    """
    I.nap_lead(db, dong(ten="A"), "nv")
    db.commit()
    doi, tt = I.nap_lead(db, dong(ten="TÊN GÕ SAI"), "nv")
    db.commit()
    assert tt == I.TRUNG_CHO_XU_LY
    assert db.query(Lead).count() == 1
    assert db.query(Lead).first().name == "A"
    assert doi is db.query(Lead).first()   # trả về dòng ĐANG CÓ để người đối chiếu


def test_nguoi_XAC_NHAN_la_lan_lien_he_khac_thi_moi_ghi_them(db):
    """Hàng đợi phải có lối ra. Chặn mà không cho người quyết thì lần liên hệ thật thứ hai mất."""
    I.nap_lead(db, dong(), "nv")
    db.commit()
    _, tt = I.nap_lead(db, dong(), "nv", nguoi_da_xac_nhan_la_lan_khac=True)
    db.commit()
    assert tt == "moi"
    assert db.query(Lead).count() == 2


def test_ma_lead_do_HE_THONG_cap_va_KHONG_trung_nhau(db):
    I.nap_lead(db, dong(phat_sinh_luc="2026-09-13 09:20"), "nv")
    I.nap_lead(db, dong(phat_sinh_luc="2026-09-14 10:00"), "nv")
    db.commit()
    ma = [x.ma_lead for x in db.query(Lead)]
    assert all(m and m.startswith("L2026-09-") for m in ma)
    assert len(set(ma)) == len(ma)


def test_HE_THONG_KHONG_cap_ma_khach(db):
    """Chốt của Chủ tịch 14/9/2026: không có mã khách, người nhập chỉ nhập MÃ TOUR.

    Phép thử này canh một điều KHÔNG được làm. Bản trước có `ma_khach` do hệ thống tự sinh từ số
    điện thoại; cái mã ấy trông như một danh tính đã xác minh trong khi nó chỉ là số điện thoại
    đội lốt, và một khi đã có mã thì báo cáo sẽ gọi nó là "số khách" chứ không ai còn nhớ nó từ
    đâu ra.

    Canh ở HAI chỗ, vì bản đầu của phép thử này canh sai chỗ: nó đọc `hasattr()` trên một đối
    tượng vừa lấy ra sau `commit()`, và phép đột biến "gán thêm ld.ma_khach" vẫn THOÁT. Đo lại
    mới thấy: `hasattr` trên một thuộc tính KHÔNG phải cột thì không nói được gì chắc chắn sau
    khi phiên làm mới đối tượng. Hợp đồng thật nằm ở BẢNG và ở MÃ NGUỒN, nên canh đúng hai chỗ ấy.
    """
    import ast
    import inspect

    # 1. Bảng không có cột mã khách
    assert "ma_khach" not in Lead.__table__.columns, \
        "cột mã khách đã quay lại – hệ thống không được tự cấp danh tính cho người"
    assert "ma_tour" in Lead.__table__.columns

    # 2. Cửa nhập không gán mã khách ở bất kỳ đâu
    cay = ast.parse(inspect.getsource(I))
    gan = {n.attr for n in ast.walk(cay)
           if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store)}
    assert "ma_khach" not in gan, "cửa nhập đang gán mã khách cho lead"


def test_MA_TOUR_la_o_nguoi_nhap_chon_chu_khong_suy_tu_chu_tu_do(db):
    """Phép đếm "bao nhiêu chuyến" dùng mã tour. Chữ tự do thì cùng một tour thành nhiều tour."""
    I.nap_lead(db, dong(ma_tour="DLPT", quan_tam="Đà Lạt Phan Thiết"), "nv")
    db.commit()
    assert db.query(Lead).first().ma_tour == "DLPT"
    cot = {c["key"]: c for c in BO["khach_tiem_nang"]["cot"]}
    assert "ma_tour" in cot
    assert cot["ma_tour"]["bat_buoc"] is False, \
        "bắt buộc mã tour thì lead mới hỏi chưa rõ tour sẽ không nhập được"


def test_so_dien_thoai_chuan_hoa_truoc_khi_lam_dau_van_tay(db):
    """'84901234567' và '0901234567' là cùng một người. Không chuẩn hoá thì thành hai khách."""
    a = I.dau_van_tay(dong(sdt="84901234567"), thang="2026-09")
    b = I.dau_van_tay(dong(sdt="0901234567"), thang="2026-09")
    c = I.dau_van_tay(dong(sdt="090 123 4567"), thang="2026-09")
    assert a == b == c


# =============================================================================================
# 4. Ba thứ của việc giao Sales đi với nhau
# =============================================================================================

def test_da_giao_ma_khong_co_nguoi_nhan_la_LOI(db):
    assert any("không ghi người nhận" in x for x in loi(db, trang_thai="da_giao"))


def test_co_nguoi_nhan_ma_thieu_moc_thoi_gian_la_CANH_BAO(db):
    """Không chặn – giao việc miệng rồi ghi sổ sau là chuyện thường. Nhưng phải nói ra, vì thiếu
    mốc thì thẻ 'Lead quá hạn' không tính được dòng này."""
    cb = " ".join(canh_bao(db, nguoi_nhan="NV0021"))
    assert loi(db, nguoi_nhan="NV0021") == []
    assert "chưa ghi thời điểm giao" in cb and "chưa ghi hạn xử lý" in cb


def test_han_xu_ly_TRUOC_thoi_diem_giao_la_LOI(db):
    """Hạn trước lúc giao thì lead ấy quá hạn ngay khi vừa được giao – một con số vô nghĩa chảy
    thẳng vào thẻ cảnh báo."""
    e = loi(db, nguoi_nhan="NV01", giao_luc="2026-09-10", han_xu_ly="2026-09-08")
    assert any("trước thời điểm giao" in x for x in e)


def test_thoi_diem_giao_o_TUONG_LAI_la_LOI(db):
    mai = HOM_NAY + timedelta(days=3)
    assert any("tương lai" in x for x in loi(db, nguoi_nhan="NV01",
                                             giao_luc=mai.strftime("%Y-%m-%d")))


def test_cua_nhap_KHONG_tu_dat_han_xu_ly(db):
    """'Quá hạn' là một lời buộc tội với người được giao. Buộc tội theo một con số hệ thống tự
    đặt thì người bị buộc có quyền không nhận."""
    I.nap_lead(db, dong(nguoi_nhan="NV01", giao_luc="2026-09-10"), "nv_mkt")
    db.commit()
    assert db.query(Lead).first().han_xu_ly is None
    cot = {c["key"]: c for c in BO["khach_tiem_nang"]["cot"]}
    assert "KHÔNG tự đặt hộ" in cot["han_xu_ly"]["ghi_chu"]


def test_lead_MAT_phai_co_ly_do(db):
    assert any("phải chọn lý do" in x for x in loi(db, trang_thai="mat"))
    assert loi(db, trang_thai="mat", ly_do_mat="gia") == []


def test_ly_do_mat_la_DANH_SACH_DONG():
    """Ô chữ tự do thì ba tháng sau mỗi người viết một kiểu cho cùng một lý do, và không tổng hợp
    được 'vì sao mình mất khách'."""
    cot = {c["key"]: c for c in BO["khach_tiem_nang"]["cot"]}
    assert cot["ly_do_mat"]["kieu"] == "chon"
    assert set(cot["ly_do_mat"]["chon"]) == set(I.LY_DO_MAT)


def test_co_ly_do_mat_ma_trang_thai_khac_thi_CANH_BAO(db):
    assert any("kiểm lại" in x for x in canh_bao(db, ly_do_mat="gia", trang_thai="dang_cham_soc"))


# =============================================================================================
# 5. Cửa số kênh theo tháng – nguồn THỨ HAI, tách khỏi cửa lead
# =============================================================================================

def test_hai_cua_RIENG_chu_khong_gop(db):
    """Số khai tay và số đếm được là hai nguồn khác nhau, và việc đối chiếu chúng chính là nhóm
    'Đối soát dữ liệu'. Gộp hai cửa là xoá mất chính việc ấy."""
    assert BO["khach_tiem_nang"]["bang_dich"] == "leads"
    assert BO["so_kenh_marketing"]["bang_dich"] == "lead_channel_stats"


def test_khai_0_lead_thi_CANH_BAO(db):
    """0 và 'không chạy kênh ấy' là hai chuyện khác nhau trên báo cáo."""
    e, cb, _ = I.kiem_so_kenh(db, {"thang": "2026-09", "kenh": "facebook", "so_lead": 0})
    assert e == []
    assert any("không chạy kênh ấy" in x for x in cb)


def test_thieu_chi_phi_thi_CANH_BAO_chu_khong_coi_la_0(db):
    e, cb, _ = I.kiem_so_kenh(db, {"thang": "2026-09", "kenh": "facebook", "so_lead": 147})
    assert e == []
    assert any("Chưa có chi phí kênh" in x for x in cb)
    I.nap_so_kenh(db, {"thang": "2026-09", "kenh": "facebook", "so_lead": 147}, "nv_mkt")
    db.commit()
    assert db.query(LeadChannelStat).first().cost is None, "chi phí rỗng bị ghi thành 0"


def test_so_am_la_LOI(db):
    for k, v in (("so_lead", -1), ("chi_phi", -5)):
        e = I.kiem_so_kenh(db, {"thang": "2026-09", "kenh": "facebook", "so_lead": 1, k: v})[0]
        assert any("không âm được" in x for x in e), k


def test_kenh_ngoai_CA_HAI_danh_muc_la_LOI(db):
    e = I.kiem_so_kenh(db, {"thang": "2026-09", "kenh": "bao_chi", "so_lead": 5})[0]
    assert any("không có trong hai danh mục" in x for x in e)


def test_khoa_chong_trung_cua_so_kenh_la_ky_cong_kenh(db):
    a = I.kiem_so_kenh(db, {"thang": "2026-09", "kenh": "facebook", "so_lead": 1})[2]
    b = I.kiem_so_kenh(db, {"thang": "2026-09", "kenh": "facebook", "so_lead": 999})[2]
    c = I.kiem_so_kenh(db, {"thang": "2026-10", "kenh": "facebook", "so_lead": 1})[2]
    assert a == b and a != c


# =============================================================================================
# 6. Khai báo cửa đúng khuôn mà intake.py gom
# =============================================================================================

def test_khai_bao_du_cac_phan_intake_doi():
    for ma, bo in BO.items():
        for khoa in ("bang_dich", "phong_ban", "ten", "mo_ta", "khoa_chong_trung", "cot",
                     "kiem", "nap"):
            assert khoa in bo, f"{ma} thiếu '{khoa}'"
        assert bo["phong_ban"] == "marketing"
        assert callable(bo["kiem"]) and callable(bo["nap"])
        assert len(bo["mo_ta"]) >= 80, f"{ma}: mô tả quá ngắn để người nhập hiểu phải làm gì"


def test_moi_cot_deu_co_vi_du_hoac_ghi_chu():
    """Ô trống không có ví dụ là ô người ta đoán cách điền, và mỗi người đoán một kiểu."""
    for ma, bo in BO.items():
        for c in bo["cot"]:
            assert c["vi_du"] or c["ghi_chu"], f"{ma}.{c['key']}: không ví dụ, không ghi chú"


def test_cua_lead_KHONG_co_o_doanh_thu():
    """Tiền của khách nằm ở booking. Gõ tay vào đây là mở đường cho hai con số cùng nói về một
    khoản – đúng thứ đang phải sửa ở báo cáo chuyển đổi."""
    keys = {c["key"] for c in BO["khach_tiem_nang"]["cot"]}
    assert not (keys & {"doanh_thu", "gia_tri", "so_tien", "revenue"})


# =============================================================================================
# 7. HAI CỬA MARKETING ĐƯỢC THÊM VÀO, KHÔNG PHẢI THAY CHO CỬA CỦA LÀN KHÁC
# =============================================================================================
#
# VÌ SAO CÓ MỤC NÀY – một lỗi suýt xảy ra ngày 18/9/2026, và nó sẽ hỏng LẶNG.
#
# `intake.py` là tệp DÙNG CHUNG: mỗi làn thêm một cửa vào đúng một chỗ trong tệp ấy. Gói Marketing
# này soạn trên bản `intake.py` chụp ngày 14/9. Ngày 16/9 một làn khác thêm CỬA THỨ BẢY (bảng
# tháng dịch vụ lẻ – 49 tệp, 10,29 tỷ) vào cùng tệp. Đẩy thẳng bản 14/9 lên là GỠ cửa ấy ra khỏi
# hệ, mà không một phép thử nào của Marketing đỏ lên: hai cửa Marketing vẫn chạy đúng, và 10,29 tỷ
# lặng lẽ không còn đường vào.
#
# Cách chặn không phải là "nhớ kiểm tra" mà là một phép thử ĐẾM ĐỦ CẢ TÁM CỬA. Ai thêm cửa thứ
# chín thì sửa danh sách này – và việc phải sửa nó chính là lúc người ấy nhìn thấy danh sách.

def test_THEM_CUA_MARKETING_KHONG_DUOC_GO_CUA_CUA_LAN_KHAC():
    """Tám cửa, đủ tám. Thiếu một cửa là một phòng ban mất đường nạp – và mất im lặng."""
    from app.services import intake as IT

    phai_co = {
        # sáu cửa có trước gói Marketing
        "nha_cung_cap", "don_dich_vu", "chuyen_xe", "nhan_su", "cham_cong", "khach_hang",
        "booking", "sao_ke_ngan_hang", "huong_dan_vien", "quyet_toan_tour",
        # cửa thứ bảy (16/9/2026) – làn khác, KHÔNG được biến mất vì gói này
        "bang_thang_dich_vu_le",
        # cửa thứ tám (14/9/2026, đẩy 18/9) – gói này
        "khach_tiem_nang", "so_kenh_marketing",
    }
    thieu = sorted(phai_co - set(IT.BO_NAP))
    assert not thieu, (
        f"những cửa này biến mất khỏi intake.BO_NAP: {thieu}. Nếu là do gộp nhánh thì bản "
        f"intake.py đang đẩy được soạn trên một bản CŨ của main – nối lại vào main trước khi đẩy.")


def test_MOI_CUA_DEU_PHAI_KHAI_QUYEN_AI_BAM_DUOC():
    """Cửa có trong BO_NAP mà không có trong VAI_TRO là cửa không ai bấm được – hoặc tệ hơn, là
    cửa mà bộ kiểm quyền đọc ra rỗng rồi cho qua. Hai bảng phải đi đôi."""
    from app.services import intake as IT

    thieu = sorted(set(IT.BO_NAP) - set(IT.VAI_TRO))
    assert not thieu, f"cửa không khai quyền: {thieu}"
