# -*- coding: utf-8 -*-
"""SEC-02 + CF-07 · Quyền xem từng dòng khối Dòng tiền, và cửa nhập cho từng dòng.

Cái tệp này canh không phải là "lọc đúng chưa". Nó canh ba chuyện khó thấy hơn:

  1. Một bảng ĐÃ BỊ LỌC mà dòng đáy vẫn đề chữ "số dư". Khi ấy không dòng nào trên màn hình sai,
     chỉ cái tên của dòng đáy nói dối – và người đọc là người số hai của tập đoàn, đang cầm bút
     duyệt chi.

  2. Dòng TỔNG cộng từ toàn cảnh rồi mới che bớt. Con số tổng khi ấy vẫn mang phần đã bị che, nên
     bảng của TGĐ tự mâu thuẫn: cộng mắt các dòng ra một số, dòng tổng in ra một số khác.

  3. Một dòng trên bảng mà không ai chịu trách nhiệm nhập. Đến ngày vận hành thật nó hiện "Chưa có"
     mãi mãi, và không ai biết phải đi hỏi ai.
"""
import pytest

from app.services import dong_tien_pham_vi as SEC


# =============================================================================================
# 1. Tên dòng phải khớp NGUYÊN VĂN tài liệu v1.1
# =============================================================================================

def test_ten_dong_lay_nguyen_van_bang_muc_III_cua_v11():
    """Một dòng đổi tên giữa tài liệu và màn hình là một lần hai bên họp về hai thứ khác nhau mà
    tưởng là một. Bản đầu của tệp này đặt lại tên cho gọn và sai ba dòng."""
    assert SEC.DONG["thu_cong_no_khac"].ten == "Thu công nợ khác"
    assert SEC.DONG["giai_ngan_vay"].ten == "Giải ngân vay đã ký khế ước"
    assert SEC.DONG["tra_goc_vay"].ten == "Trả gốc vay ngân hàng"
    assert SEC.DONG["luong_bhxh"].ten == "Lương, bảo hiểm và liên quan"
    assert SEC.DONG["van_hanh"].ten == "Vận hành và phải trả khác"
    assert SEC.DONG["ghi_nho_thu_ho"].ten.endswith("(KHÔNG thuộc tiền khả dụng)")
    assert SEC.DONG["ghi_nho_ky_quy"].ten.endswith("(KHÔNG thuộc tiền khả dụng)")


def test_thu_tu_dong_giu_dung_bang_cua_tai_lieu():
    """Thứ tự cũng là nội dung: dòng TỔNG đứng TRƯỚC các dòng thành phần của nó, y như tài liệu."""
    ma = [d.ma for d in SEC.CAC_DONG]
    assert ma.index("tong_thu") < ma.index("thu_khach") < ma.index("giai_ngan_vay")
    assert ma.index("tong_chi") < ma.index("tra_ncc") < ma.index("van_hanh")
    assert ma[0] == "tien_kha_dung_dau_ky"
    assert ma[-2:] == ["ghi_nho_thu_ho", "ghi_nho_ky_quy"]


# =============================================================================================
# 2. Hai mức xem theo chỉ đạo Chủ tịch
# =============================================================================================

def test_chu_tich_xem_tat_ca_cac_dong():
    assert len(SEC.cac_dong_cho("chutich")) == len(SEC.CAC_DONG)


def test_tgd_chi_xem_tour_va_xe():
    ma = {d.ma for d in SEC.cac_dong_cho("tgd")}
    assert {"thu_khach", "thu_cong_no_khac", "tra_ncc", "hoan_tra_khach", "hoa_hong",
            "luong_bhxh", "van_hanh", "ghi_nho_thu_ho", "tong_thu", "tong_chi"} <= ma
    assert not ({"giai_ngan_vay", "tra_goc_vay", "lai_phi_ngan_hang", "thue_nghia_vu",
                 "ghi_nho_ky_quy"} & ma), "TGĐ đang thấy dòng tài chính"


def test_cach_A_bang_cua_tgd_khong_co_ba_dong_so_du():
    """Chủ tịch chốt Cách A: không 'Tiền khả dụng đầu kỳ', không 'SỐ DƯ DỰ KIẾN CUỐI KHOẢNG',
    không 'THIẾU SO VỚI MỨC DỰ PHÒNG'."""
    ma = {d.ma for d in SEC.cac_dong_cho("tgd")}
    assert not ({"tien_kha_dung_dau_ky", "so_du_du_kien_cuoi_khoang",
                 "thieu_so_voi_muc_du_phong"} & ma)
    assert not any(d.phia == SEC.SO_DU for d in SEC.cac_dong_cho("tgd"))


def test_dong_day_cua_tgd_KHONG_BAO_GIO_mang_chu_so_du():
    """Phép thử quan trọng nhất tệp này.

    Một bảng lọc mất dòng vay, thuế và lãi mà dòng đáy đề 'số dư' thì con số ấy trông như đúng.
    Người đọc thấy 'số dư cuối tháng 4 tỷ', duyệt một khoản chi, trong khi phần bị giấu có kỳ trả
    gốc 6 tỷ. Không dòng nào sai – chỉ cái tên nói dối.
    """
    t = SEC.ten_dong_day("tgd")
    assert t == "Dòng tiền thuần từ hoạt động tour và xe"
    assert "số dư" not in t.lower() and "so du" not in t.lower()
    assert SEC.ten_dong_day("chutich") == "SỐ DƯ DỰ KIẾN CUỐI KHOẢNG"


def test_pham_vi_va_ten_dong_day_khong_bao_gio_lech_nhau():
    """Hai thứ ấy do cùng một hàm quyết định. Nếu một hôm nào đó tách ra hai chỗ, phép thử này đỏ."""
    for vai in SEC.BANG_QUYEN:
        khung = SEC.khung_bang(vai)
        co_so_du = any(d["ma"] == "so_du_du_kien_cuoi_khoang" for d in khung["dong"])
        assert co_so_du == ("SỐ DƯ" in khung["ten_dong_day"]), (
            f"{vai}: bảng {'có' if co_so_du else 'không có'} dòng số dư nhưng dòng đáy đề "
            f"'{khung['ten_dong_day']}'")


# =============================================================================================
# 3. Dòng TỔNG cộng từ tập dòng CỦA CHÍNH VAI ĐÓ
# =============================================================================================

def test_dong_tong_cua_tgd_khong_cong_dong_tai_chinh():
    """Cộng toàn cảnh rồi mới che bớt thì con số tổng vẫn mang phần đã bị che – bảng tự mâu thuẫn:
    cộng mắt các dòng ra một số, dòng tổng in ra một số khác."""
    thu = set(SEC.dong_de_cong("tgd", SEC.VAO))
    chi = set(SEC.dong_de_cong("tgd", SEC.RA))
    assert thu == {"thu_khach", "thu_cong_no_khac"}
    assert "giai_ngan_vay" not in thu
    assert chi == {"tra_ncc", "hoan_tra_khach", "hoa_hong", "luong_bhxh", "van_hanh"}
    assert not ({"tra_goc_vay", "lai_phi_ngan_hang", "thue_nghia_vu"} & chi)


def test_dong_tong_cua_chu_tich_cong_du_moi_dong():
    assert len(SEC.dong_de_cong("chutich", SEC.VAO)) == 3
    assert len(SEC.dong_de_cong("chutich", SEC.RA)) == 8


def test_ghi_nho_va_so_du_khong_bao_gio_lot_vao_phep_cong():
    """Ghi nhớ thu hộ là tiền trong tài khoản nhưng KHÔNG phải của công ty – cộng nó vào là tự cho
    mình thêm tiền."""
    for vai in SEC.BANG_QUYEN:
        gom = set(SEC.dong_de_cong(vai, SEC.VAO)) | set(SEC.dong_de_cong(vai, SEC.RA))
        assert not ({"ghi_nho_thu_ho", "ghi_nho_ky_quy", "tien_kha_dung_dau_ky",
                     "so_du_du_kien_cuoi_khoang", "tong_thu", "tong_chi"} & gom), vai


# =============================================================================================
# 4. Đóng mặc định
# =============================================================================================

def test_vai_tro_chua_khai_thi_KHONG_thay_gi():
    """Mở mặc định rồi liệt kê người bị cấm là kiểu khai mà mỗi vai trò mới là một lần rò rỉ."""
    for vai in ("ptgd_kd", "ptgd_mkt", "nv_kd", "nv_dh", "hdv", "", "chutich_moi"):
        assert SEC.muc_xem(vai) is None, vai
        assert SEC.cac_dong_cho(vai) == []
        assert SEC.cac_canh_bao_cho(vai) == []
        assert SEC.khung_bang(vai)["xem_duoc"] is False


def test_hai_pho_tong_giam_doc_khong_thay_khoi_nay():
    for vai in ("ptgd_kd", "ptgd_mkt"):
        assert vai not in SEC.BANG_QUYEN


def test_ke_toan_va_ban_kiem_soat_giu_toan_canh():
    """Kiểm soát mà chỉ xem được một phần thì không kiểm soát gì."""
    for vai in ("ketoan", "bks"):
        assert SEC.muc_xem(vai) == SEC.TOAN_CANH


def test_ma_dong_la_khong_lot_qua():
    assert SEC.xem_duoc("chutich", "dong_khong_co_that") is False


# =============================================================================================
# 5. Bốn ô cảnh báo
# =============================================================================================

def test_hai_o_canh_bao_toan_canh_chi_chu_tich_doc_duoc():
    """'Ngày đầu tiên thiếu tiền' tính trên một phần sẽ ra một ngày MUỘN HƠN sự thật – báo yên khi
    không yên. Sai theo chiều nguy hiểm, nên không đưa xuống bảng đã lọc."""
    tgd = {c["ma"] for c in SEC.cac_canh_bao_cho("tgd")}
    ct = {c["ma"] for c in SEC.cac_canh_bao_cho("chutich")}
    assert {"phai_tra_qua_han", "phai_tra_7_ngay"} <= tgd
    assert not ({"ngay_dau_thieu_tien", "muc_thieu_lon_nhat"} & tgd)
    assert len(ct) == 4


# =============================================================================================
# 6. Bản khai phải đầy đủ và nói được vì sao
# =============================================================================================

def test_moi_dong_deu_khai_mang_hop_le_va_kem_ly_do():
    """Một dòng khai mang='tai_chinh' mà không nói được vì sao thì rất có thể chỉ đang bị xếp nhầm."""
    for d in SEC.CAC_DONG:
        assert d.mang in (SEC.TOUR_XE, SEC.TAI_CHINH, SEC.CA_HAI, SEC.MOI_VAI), d.ma
        assert d.phia in (SEC.VAO, SEC.RA, SEC.GHI_NHO, SEC.SO_DU, SEC.TONG), d.ma
        assert len(d.ly_do) >= 40, f"{d.ma}: khai mà không nói vì sao"
        assert d.ten.lower() not in d.ly_do.lower(), f"{d.ma}: lý do chỉ chép lại tên dòng"


def test_khong_co_ma_dong_trung():
    ma = [d.ma for d in SEC.CAC_DONG]
    assert len(ma) == len(set(ma))


def test_ba_dong_so_du_deu_thuoc_mang_tai_chinh():
    """Nếu một dòng số dư lỡ khai là tour_xe thì Cách A gãy ngay mà không phép thử nào khác thấy."""
    for d in SEC.CAC_DONG:
        if d.phia == SEC.SO_DU:
            assert d.mang == SEC.TAI_CHINH, d.ma


def test_cau_pham_vi_noi_thang_bang_da_bi_loc():
    """Người dùng phải đọc được rằng mình đang xem một phần, không phải tự đoán ra."""
    c = SEC.khung_bang("tgd")["cau_pham_vi"]
    assert "CHỈ" in c and "không có dòng số dư" in c
    assert "vay" in c and "thuế" in c


@pytest.mark.parametrize("vai", ["chutich", "tgd", "ketoan", "bks"])
def test_khung_bang_du_cac_phan_cho_moi_vai_tro_co_quyen(vai):
    k = SEC.khung_bang(vai)
    assert k["xem_duoc"] is True
    assert k["dong"] and k["ten_dong_day"] and k["canh_bao"] and k["cau_pham_vi"]
    assert k["cong_thu"] and k["cong_chi"]


# =============================================================================================
# 7. CF-07 · mỗi dòng phải có một cửa nhập và một bộ phận chịu trách nhiệm
# =============================================================================================

def test_moi_dong_khong_tu_tinh_deu_co_cua_nhap():
    """Danh sách này PHẢI RỖNG. Một dòng trên bảng mà không ai chịu trách nhiệm nhập thì đến ngày
    vận hành thật nó hiện 'Chưa có' mãi mãi, và không ai biết phải đi hỏi ai."""
    assert SEC.dong_thieu_cua() == []


def test_dong_tu_tinh_KHONG_duoc_co_cua_nhap():
    """Cho gõ đè lên một kết quả tính được là chỗ số liệu bắt đầu nói khác sổ."""
    for d in SEC.CAC_DONG:
        if d.tu_tinh:
            assert d.ma not in SEC.CUA_NHAP, f"{d.ma}: dòng tự tính mà lại mở cửa nhập"


def test_tien_kha_dung_dau_ky_CO_cua_nhap_du_no_o_phia_so_du():
    """Nó là số người ta chốt và xác nhận trên màn hình đối soát ngân hàng, không phải số cộng ra."""
    assert SEC.DONG["tien_kha_dung_dau_ky"].tu_tinh is False
    assert SEC.CUA_NHAP["tien_kha_dung_dau_ky"].bo_phan == "Kế toán"


def test_moi_cua_deu_ghi_ro_cua_nao_va_bo_phan_nao():
    for ma, c in SEC.CUA_NHAP.items():
        assert len(c.cua) >= 20, f"{ma}: chưa nói rõ phải dựng cửa gì"
        assert c.bo_phan.strip(), f"{ma}: không có bộ phận chịu trách nhiệm nhập"
        assert c.nguon.strip(), ma


def test_danh_sach_dong_chua_co_nguon_la_danh_sach_VIEC_chu_khong_phai_loi():
    """Nó cạn dần khi các cửa nhập được dựng xong. Đo ngày 11/9/2026: TÁM dòng chưa có nguồn – tám
    màn hình còn phải dựng, không phải tám chỗ hỏng."""
    thieu = set(SEC.dong_chua_co_nguon())
    assert thieu <= set(SEC.CUA_NHAP)
    # v1.1 ghi thẳng "Chưa có" cho năm dòng này
    assert {"thu_cong_no_khac", "hoan_tra_khach", "hoa_hong", "thue_nghia_vu",
            "van_hanh"} <= thieu
    # và bốn dòng này thì v1.1 nói đã có nguồn
    assert not ({"tien_kha_dung_dau_ky", "thu_khach", "giai_ngan_vay", "tra_goc_vay"} & thieu)


def test_luong_bhxh_ghi_ro_ly_do_chua_co_nguon():
    """'Chưa có' trống không thì người đọc tưởng chỉ là chưa nối; ở đây là chưa có hợp đồng lao
    động nào trong hệ thống – một việc lớn hơn nhiều."""
    assert "hợp đồng lao động" in SEC.CUA_NHAP["luong_bhxh"].nguon


def test_hai_dong_ghi_nho_duoc_danh_dau_la_DE_XUAT_chu_khong_phai_da_chot():
    """Bảng III.4 của v1.1 có 12 dòng, nhưng bảng dòng tiền có thêm hai dòng ghi nhớ không được
    khai cửa. Làn Phân quyền đề xuất cửa cho chúng và đánh dấu rõ là đề xuất – trình bày một đề
    xuất như một quyết định đã chốt là cách nhanh nhất để nó không bao giờ được ai duyệt."""
    for ma in ("ghi_nho_thu_ho", "ghi_nho_ky_quy"):
        assert SEC.CUA_NHAP[ma].tu_de_xuat is True
    da_chot = [ma for ma, c in SEC.CUA_NHAP.items() if not c.tu_de_xuat]
    assert len(da_chot) == 12, "bảng III.4 của v1.1 có đúng 12 dòng đã chốt"
