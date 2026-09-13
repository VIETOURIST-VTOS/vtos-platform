# -*- coding: utf-8 -*-
"""SEC-02 + CF-07 · Quyền xem từng dòng khối Dòng tiền, và cửa nhập cho từng dòng.

Tệp này canh không phải là "lọc đúng chưa". Nó canh năm chuyện khó thấy hơn:

  1. Một bảng ĐÃ BỊ LỌC mà dòng đáy vẫn đề chữ "số dư". Khi ấy không dòng nào trên màn hình sai,
     chỉ cái tên của dòng đáy nói dối – và người đọc là người số hai của tập đoàn, đang cầm bút
     duyệt chi.

  2. Dòng TỔNG cộng từ toàn cảnh rồi mới che bớt. Con số tổng khi ấy vẫn mang phần đã bị che, nên
     bảng của TGĐ tự mâu thuẫn: cộng mắt các dòng ra một số, dòng tổng in ra một số khác.

  3. Một dòng trên bảng mà không ai chịu trách nhiệm nhập. Đến ngày vận hành thật nó hiện "Chưa có"
     mãi mãi, và không ai biết phải đi hỏi ai.

  4. HAI DANH MỤC DÒNG (sửa 13/9). Trước đây tệp trình bày tự khai 13 mã, sổ nghĩa vụ khai 13 mã
     khác, 7 mã lệch tên. Nay chỉ còn một danh mục; các phép thử ở mục 1 là hàng rào giữ nó một.

  5. QUYỀN ĐÃ MỞ NHƯNG VIỆC CÒN THIẾU THÌ BIẾN MẤT. Chủ tịch chốt 13/9 đưa lương vào tầm Tổng
     giám đốc, nên dòng ấy nay CÓ SỐ. Nhưng con số vẫn gồm cả khối văn phòng tập đoàn – nó rộng
     hơn cái tên "tour và xe" trên đầu bảng. Mở quyền rồi bỏ luôn câu ghi chú là cách êm nhất để
     một con số rộng hơn sự thật trông như một con số đúng.
"""
import pytest

from app.models.nghia_vu import NHOM, nhom_duoc_xem
from app.services import dong_tien_pham_vi as SEC

# Mã nằm ngoài tầm nhóm của vai trò xem một phần – ĐỌC TỪ SỔ, không chép tay. Chép tay danh sách
# này vào đây là dựng lại đúng cái lệch mà bản 13/9 vừa dẹp.
NGOAI_TAM_TGD = set(NHOM) - nhom_duoc_xem("tgd")


# =============================================================================================
# 1. MỘT danh mục dòng, không hai – hàng rào chống lệch với sổ nghĩa vụ
# =============================================================================================

def test_moi_nhom_cua_so_nghia_vu_deu_co_mat_tren_bang():
    """Thêm nhóm vào sổ mà quên thêm dòng vào bảng thì bảng lãnh đạo thiếu một khoản tiền thật, và
    thiếu IM LẶNG – tổng vẫn ra một con số trông như đủ."""
    assert SEC.kiem_khop_voi_so_nghia_vu() == []


def test_ten_dong_lay_THANG_tu_so_nghia_vu_chu_khong_chep_lai():
    """Chép tên sang một tệp khác là hẹn trước một lần lệch. Phép thử này đọc cả hai bên và so."""
    for ma, (_, ten) in NHOM.items():
        assert SEC.DONG[ma].ten == ten, f"{ma}: tên trên bảng khác tên trong sổ"


def test_dong_lay_so_tu_so_nghia_vu_deu_mang_co_tu_so_nghia_vu():
    """Cờ này quyết định dòng nào đi qua trục quyền NHÓM. Khai sót một dòng là mở nó cho mọi vai."""
    for d in SEC.CAC_DONG:
        assert d.tu_so_nghia_vu == (d.ma in NHOM), d.ma


def test_hai_dong_ghi_nho_khop_voi_co_ghi_nho_cua_so():
    """Ghi nhớ là tiền có thật mà KHÔNG được cộng vào tiền khả dụng. Hai bên khai lệch nhau thì một
    khoản hoặc bị cộng hai lần, hoặc biến mất."""
    assert SEC.ghi_nho_khop_voi_so() is True


def test_thu_tu_dong_giu_dung_bang_muc_III_cua_tai_lieu():
    """Thứ tự cũng là nội dung: dòng TỔNG đứng TRƯỚC các dòng thành phần của nó, y như tài liệu."""
    ma = [d.ma for d in SEC.CAC_DONG]
    assert ma.index("tong_thu") < ma.index("thu_khach") < ma.index("giai_ngan_vay")
    assert ma.index("tong_chi") < ma.index("tra_ncc") < ma.index("van_hanh_khac")
    assert ma[0] == "tien_kha_dung_dau_ky"
    assert ma[-2:] == ["thu_ho_khach", "ky_quy_lu_hanh"]


def test_khong_co_ma_dong_trung():
    ma = [d.ma for d in SEC.CAC_DONG]
    assert len(ma) == len(set(ma))


def test_bang_gom_13_nhom_cua_so_cong_5_dong_rieng_cua_bang():
    """Năm dòng riêng là dòng của BẢNG, không phải nghĩa vụ – sổ nghĩa vụ không được có chúng."""
    rieng = {d.ma for d in SEC.CAC_DONG if not d.tu_so_nghia_vu}
    assert rieng == {"tien_kha_dung_dau_ky", "tong_thu", "tong_chi",
                     "so_du_du_kien_cuoi_khoang", "thieu_so_voi_muc_du_phong"}
    assert len(SEC.CAC_DONG) == len(NHOM) + 5


# =============================================================================================
# 2. Hai mức xem theo chỉ đạo Chủ tịch
# =============================================================================================

def test_chu_tich_xem_tat_ca_cac_dong():
    assert len(SEC.cac_dong_cho("chutich")) == len(SEC.CAC_DONG)


def test_tgd_chi_xem_tour_va_xe():
    ma = {d.ma for d in SEC.cac_dong_cho("tgd")}
    assert {"thu_khach", "thu_cong_no_khac", "tra_ncc", "hoan_khach", "hoa_hong",
            "luong_bh", "van_hanh_khac", "thu_ho_khach", "tong_thu", "tong_chi"} <= ma
    assert not ({"giai_ngan_vay", "tra_goc_vay", "lai_phi_vay", "thue",
                 "ky_quy_lu_hanh"} & ma), "TGĐ đang thấy dòng tài chính"


def test_ranh_gioi_ngoai_tam_ve_theo_MANG_tai_chinh_ke_toan():
    """Chủ tịch chốt 13/9: "Lương nằm trong tầm TGĐ; chỉ mảng TÀI CHÍNH KẾ TOÁN là không."

    Nên danh sách ngoài tầm phải đúng NĂM nhóm, và cả năm đều là tài chính – kế toán. Thêm một
    nhóm nghiệp vụ vào đó là vẽ lại ranh giới mà Chủ tịch đã vẽ, nên phải đỏ để có người hỏi.
    """
    assert NGOAI_TAM_TGD == {"giai_ngan_vay", "tra_goc_vay", "lai_phi_vay", "thue",
                             "ky_quy_lu_hanh"}
    assert "luong_bh" not in NGOAI_TAM_TGD, "lương bị đẩy lại ra ngoài tầm Tổng giám đốc"


def test_cach_A_bang_cua_tgd_khong_co_ba_dong_so_du():
    """Chủ tịch chốt Cách A: không 'Tiền khả dụng đầu kỳ', không 'SỐ DƯ DỰ KIẾN CUỐI KHOẢNG',
    không 'THIẾU SO VỚI MỨC DỰ PHÒNG'."""
    ma = {d.ma for d in SEC.cac_dong_cho("tgd")}
    assert not (set(SEC.CHI_TOAN_CANH) & ma)
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
# 3. Hai trục quyền – vai trò ĐÓNG mặc định, nhóm MỞ mặc định
# =============================================================================================

def test_truc_VAI_TRO_dong_mac_dinh_vai_tro_chua_khai_thi_KHONG_thay_gi():
    """Mở mặc định rồi liệt kê người bị cấm là kiểu khai mà mỗi vai trò mới là một lần rò rỉ."""
    for vai in ("ptgd_kd", "ptgd_mkt", "nv_kd", "nv_dh", "hdv", "", "chutich_moi"):
        assert SEC.muc_xem(vai) is None, vai
        assert SEC.cac_dong_cho(vai) == []
        assert SEC.cac_canh_bao_cho(vai) == []
        assert SEC.khung_bang(vai)["xem_duoc"] is False


def test_truc_NHOM_mo_mac_dinh_nhom_moi_them_vao_so_van_HIEN_va_van_duoc_CONG(monkeypatch):
    """Đi ngược trục vai trò, và cố ý.

    Lộ một nhóm mới thì có người kêu; giấu một nhóm mới thì không ai biết, và bảng nhu cầu tiền
    nhẹ hơn sự thật. Phép thử này thêm một nhóm vào sổ NGAY TRONG LÚC CHẠY để chắc rằng hành vi ấy
    là của hàm, không phải của một danh sách chép tay.
    """
    monkeypatch.setitem(NHOM, "ncc_moi", ("chi", "Nhóm mới chưa ai khai quyền"))
    dong_moi = SEC.Dong("ncc_moi", NHOM["ncc_moi"][1], SEC.RA, tu_so_nghia_vu=True)
    monkeypatch.setitem(SEC.DONG, "ncc_moi", dong_moi)
    monkeypatch.setattr(SEC, "CAC_DONG", SEC.CAC_DONG + [dong_moi])
    assert SEC.xem_duoc("tgd", "ncc_moi") is True
    assert "ncc_moi" in SEC.dong_de_cong("tgd", SEC.RA)
    assert SEC.an_gia_tri("tgd", "ncc_moi") is False


def test_hai_pho_tong_giam_doc_khong_thay_khoi_nay():
    for vai in ("ptgd_kd", "ptgd_mkt"):
        assert vai not in SEC.BANG_QUYEN


def test_ke_toan_va_ban_kiem_soat_giu_toan_canh():
    """Kiểm soát mà chỉ xem được một phần thì không kiểm soát gì."""
    for vai in ("ketoan", "bks"):
        assert SEC.muc_xem(vai) == SEC.TOAN_CANH


def test_ma_dong_la_khong_lot_qua():
    assert SEC.xem_duoc("chutich", "dong_khong_co_that") is False
    assert SEC.an_gia_tri("tgd", "dong_khong_co_that") is False


# =============================================================================================
# 4. Dòng TỔNG cộng từ tập dòng CỦA CHÍNH VAI ĐÓ
# =============================================================================================

def test_dong_tong_cua_tgd_khong_cong_dong_tai_chinh():
    """Cộng toàn cảnh rồi mới che bớt thì con số tổng vẫn mang phần đã bị che – bảng tự mâu thuẫn:
    cộng mắt các dòng ra một số, dòng tổng in ra một số khác."""
    thu = set(SEC.dong_de_cong("tgd", SEC.VAO))
    chi = set(SEC.dong_de_cong("tgd", SEC.RA))
    assert thu == {"thu_khach", "thu_cong_no_khac"}
    assert chi == {"tra_ncc", "hoan_khach", "hoa_hong", "luong_bh", "van_hanh_khac"}
    assert not (NGOAI_TAM_TGD & (thu | chi))


def test_dong_tong_cua_chu_tich_cong_du_moi_dong():
    assert len(SEC.dong_de_cong("chutich", SEC.VAO)) == 3
    assert len(SEC.dong_de_cong("chutich", SEC.RA)) == 8


def test_ghi_nho_va_so_du_khong_bao_gio_lot_vao_phep_cong():
    """Ghi nhớ thu hộ là tiền trong tài khoản nhưng KHÔNG phải của công ty – cộng nó vào là tự cho
    mình thêm tiền."""
    for vai in SEC.BANG_QUYEN:
        gom = set(SEC.dong_de_cong(vai, SEC.VAO)) | set(SEC.dong_de_cong(vai, SEC.RA))
        assert not ({"thu_ho_khach", "ky_quy_lu_hanh", "tien_kha_dung_dau_ky",
                     "so_du_du_kien_cuoi_khoang", "thieu_so_voi_muc_du_phong",
                     "tong_thu", "tong_chi"} & gom), vai


def test_khong_vai_tro_nao_cong_mot_dong_minh_khong_thay():
    """Hàng rào tổng quát cho cả hai phép thử trên: phép cộng không được đi ra ngoài tập dòng
    đã lọc, với BẤT KỲ vai trò nào, kể cả vai trò thêm sau này."""
    for vai in SEC.BANG_QUYEN:
        thay = {d.ma for d in SEC.cac_dong_cho(vai)}
        for phia in (SEC.VAO, SEC.RA):
            assert set(SEC.dong_de_cong(vai, phia)) <= thay, vai


# =============================================================================================
# 5. Quyền đã mở, việc còn thiếu vẫn phải nói ra
# =============================================================================================

def test_dong_luong_HIEN_VA_CO_SO_tren_bang_cua_TGD():
    """Chốt 13/9 của Chủ tịch: lương nằm trong tầm Tổng giám đốc.

    Bản 11/9 đẩy lương ra ngoài tầm vì CHƯA TÁCH ĐƯỢC theo bộ phận, và tự ghi rằng đó là "việc
    còn thiếu, không phải quyết định về quyền". Nay phần thẩm quyền đã có người quyết.
    """
    assert SEC.xem_duoc("tgd", "luong_bh") is True
    assert SEC.an_gia_tri("tgd", "luong_bh") is False
    assert "luong_bh" in SEC.dong_de_cong("tgd", SEC.RA)


def test_hai_dong_rong_hon_pham_vi_deu_mang_GHI_CHU():
    """Mở quyền rồi bỏ luôn câu ghi chú là cách êm nhất để một con số rộng hơn sự thật trông như
    một con số đúng. Lương gồm cả khối văn phòng; vận hành gồm cả chi phí chung trụ sở."""
    c = SEC.ghi_chu_lan_sang("tgd")
    assert "RỘNG HƠN" in c
    assert "TOÀN CÔNG TY" in c and "cột bộ phận" in c      # dòng lương
    assert "trụ sở" in c                                    # dòng vận hành
    for ma in ("luong_bh", "van_hanh_khac"):
        o = [d for d in SEC.khung_bang("tgd")["dong"] if d["ma"] == ma][0]
        assert o["ghi_chu"], ma
        assert o["an_gia_tri"] is False, ma


def test_ghi_chu_chi_dan_cho_vai_tro_xem_MOT_PHAN():
    """Với người xem toàn cảnh thì dòng ấy vốn là cả dòng – không có gì "rộng hơn" cả."""
    for vai in ("chutich", "ketoan", "bks", "cntt", "robot_ks"):
        assert SEC.ghi_chu_lan_sang(vai) == "", vai
        assert all(not d["ghi_chu"] for d in SEC.khung_bang(vai)["dong"]), vai


# --- cách thứ tư: đang RỖNG, nhưng hàng rào phải còn sống ------------------------------------
# Bộ máy này không còn dòng nào dùng sau chốt 13/9. Giữ lại vì nó là đường DUY NHẤT để một dòng
# ngoài tầm được phép có mặt trên bảng, và các phép thử dưới đây canh rằng dòng đi đường ấy không
# bao giờ kèm số. Không canh thì bộ máy mục đi trong im lặng, và lần sau ai cần lại dựng lại bằng
# một câu `if` theo tên dòng – đúng chỗ đã hỏng.

def test_cach_thu_tu_dang_RONG_va_dung_la_dang_rong():
    """Ghi lại tình trạng hôm nay thành một câu máy đọc được, để ai thêm dòng vào đó phải sửa cả
    phép thử này – tức phải nghĩ một lần nữa."""
    assert SEC.CHUA_TACH_DUOC == {}
    assert not any(SEC.an_gia_tri("tgd", d.ma) for d in SEC.CAC_DONG)
    assert SEC.canh_bao_dong_day("tgd") == ""


def test_dong_NGOAI_TAM_ma_duoc_cho_hien_thi_BAT_BUOC_khong_co_so(monkeypatch):
    """Ràng buộc, không phải danh sách.

    Dựng tại chỗ đúng tình huống của bản 11/9 – một dòng ngoài tầm được cho hiện – rồi kiểm rằng
    phép ẩn TỰ chặn số, dù `CHUA_TACH_DUOC` chỉ giữ câu giải thích chứ không quyết định gì.
    """
    monkeypatch.setitem(SEC.CHUA_TACH_DUOC, "thue", "Lý do dựng tại chỗ cho phép thử.")
    assert SEC.xem_duoc("tgd", "thue") is True
    assert SEC.an_gia_tri("tgd", "thue") is True
    assert "thue" not in SEC.dong_de_cong("tgd", SEC.RA)
    o = [d for d in SEC.khung_bang("tgd")["dong"] if d["ma"] == "thue"][0]
    assert o["hien"] == SEC.CAU_CHUA_TACH and o["ly_do_an"]
    c = SEC.canh_bao_dong_day("tgd")
    assert "Thuế và nghĩa vụ khác" in c and "đứng ngoài phép cộng" in c


def test_khai_CHUA_TACH_DUOC_mot_dong_DANG_TRONG_TAM_thi_do(monkeypatch):
    """Khai một dòng đang trong tầm vào đó thì khai xong mà KHÔNG CÓ TÁC DỤNG – và người khai
    tưởng đã giấu được con số. Hàm canh phải gọi tên đúng dòng ấy."""
    assert SEC.kiem_chua_tach_duoc() == []
    monkeypatch.setitem(SEC.CHUA_TACH_DUOC, "tra_ncc", "Khai nhầm – tra_ncc đang trong tầm.")
    assert SEC.kiem_chua_tach_duoc() == ["tra_ncc"]
    assert SEC.an_gia_tri("tgd", "tra_ncc") is False, "khai nhầm mà lại giấu được số"


def test_mot_ma_khong_duoc_nam_ca_o_hai_bang_nhan(monkeypatch):
    """'Dòng này vẫn có số, số hơi rộng' và 'dòng này không có số' là hai câu ngược nhau."""
    assert SEC.kiem_ghi_chu_lan_sang() == []
    assert not (set(SEC.CHUA_TACH_DUOC) & set(SEC.GHI_CHU_LAN_SANG))
    monkeypatch.setitem(SEC.GHI_CHU_LAN_SANG, "thue", "Câu mâu thuẫn dựng tại chỗ.")
    monkeypatch.setitem(SEC.CHUA_TACH_DUOC, "thue", "Lý do dựng tại chỗ.")
    assert SEC.kiem_ghi_chu_lan_sang() == ["thue"]


def test_hai_cau_nhan_dung_RIENG_khong_gop(monkeypatch):
    """Gộp lại thì người đọc không phân biệt được 'thiếu khoản này' với 'khoản này đang tính rộng
    hơn' – hai lỗi lệch về hai phía ngược nhau."""
    monkeypatch.setitem(SEC.CHUA_TACH_DUOC, "thue", "Lý do dựng tại chỗ cho phép thử.")
    k = SEC.khung_bang("tgd")
    assert k["canh_bao_dong_day"] and k["ghi_chu_lan_sang"]
    assert k["canh_bao_dong_day"] != k["ghi_chu_lan_sang"]
    assert "CHƯA gồm" in k["canh_bao_dong_day"]
    assert "RỘNG HƠN" in k["ghi_chu_lan_sang"]
    assert "Thuế" in k["canh_bao_dong_day"] and "Thuế" not in k["ghi_chu_lan_sang"]


def test_chu_tich_khong_can_nhan_vi_ong_xem_toan_canh(monkeypatch):
    monkeypatch.setitem(SEC.CHUA_TACH_DUOC, "thue", "Lý do dựng tại chỗ cho phép thử.")
    for vai in ("chutich", "ketoan", "bks", "cntt", "robot_ks"):
        assert SEC.canh_bao_dong_day(vai) == "", vai
        assert SEC.ghi_chu_lan_sang(vai) == "", vai
        assert not any(SEC.an_gia_tri(vai, d.ma) for d in SEC.CAC_DONG), vai


# =============================================================================================
# 6. Trục thứ ba – số tổng hợp khác chi tiết từng người
# =============================================================================================

def test_xem_so_tong_hop_khong_dong_nghia_duoc_xem_luong_tung_nguoi():
    """Trục hẹp hơn hẳn hai trục kia, và cố ý tách ra: một người được xem tổng quỹ lương không
    đương nhiên được xem lương từng người."""
    for vai in ("chutich", "ketoan", "bks"):
        assert SEC.xem_chi_tiet_nhan_vien(vai) is True, vai
    for vai in ("tgd", "cntt", "robot_ks", "ptgd_kd", ""):
        assert SEC.xem_chi_tiet_nhan_vien(vai) is False, vai


def test_cntt_va_robot_xem_duoc_bang_nhung_khong_xem_luong_tung_nguoi():
    """Hai vai trò kỹ thuật cần đối chiếu con số, không cần biết ai lĩnh bao nhiêu."""
    for vai in ("cntt", "robot_ks"):
        assert SEC.muc_xem(vai) == SEC.TOAN_CANH
        assert SEC.xem_chi_tiet_nhan_vien(vai) is False


# =============================================================================================
# 7. PHÉP TÍNH khác QUYỀN XEM – báo cáo tự nói ra là mình chưa đầy đủ
# =============================================================================================

def test_bao_cao_khong_co_nhom_la_thi_bao_day_du():
    assert SEC.day_du()["day_du"] is True
    assert SEC.day_du([])["cau"] == ""


def test_nhom_chua_phan_loai_van_duoc_CONG_nhung_bang_phai_TU_DANH_DAU():
    """Đo được 13/9: hạng mục lạ của `cash_plan_items` rơi thầm vào 'Vận hành và phải trả khác' mà
    không có cờ nào. Bỏ sót và đoán đều sai; ở đây cộng vào NHƯNG nói ra."""
    d = SEC.day_du(["tam_ung_du_an", "phi_kiem_toan"])
    assert d["day_du"] is False
    assert d["chua_phan_loai"] == ["tam_ung_du_an", "phi_kiem_toan"]
    assert "CHƯA ĐẦY ĐỦ" in d["cau"] and "vẫn được cộng" in d["cau"]
    assert "tam_ung_du_an" in d["cau"]


def test_khung_bang_mang_theo_co_day_du():
    assert SEC.khung_bang("chutich", ["la_hoac"])["day_du"]["day_du"] is False
    assert SEC.khung_bang("chutich")["day_du"]["day_du"] is True


# =============================================================================================
# 8. Bốn ô cảnh báo
# =============================================================================================

def test_hai_o_canh_bao_toan_canh_chi_nguoi_xem_toan_canh_doc_duoc():
    """'Ngày đầu tiên thiếu tiền' tính trên một phần sẽ ra một ngày MUỘN HƠN sự thật – báo yên khi
    không yên. Sai theo chiều nguy hiểm, nên không đưa xuống bảng đã lọc."""
    tgd = {c["ma"] for c in SEC.cac_canh_bao_cho("tgd")}
    ct = {c["ma"] for c in SEC.cac_canh_bao_cho("chutich")}
    assert {"phai_tra_qua_han", "phai_tra_7_ngay"} <= tgd
    assert not ({"ngay_dau_thieu_tien", "muc_thieu_lon_nhat"} & tgd)
    assert len(ct) == 4


# =============================================================================================
# 9. Bản khai phải đầy đủ và nói được vì sao
# =============================================================================================

def test_moi_dong_deu_khai_phia_hop_le():
    for d in SEC.CAC_DONG:
        assert d.phia in (SEC.VAO, SEC.RA, SEC.GHI_NHO, SEC.SO_DU, SEC.TONG), d.ma


def test_phia_cua_dong_nghia_vu_khop_voi_huong_trong_so():
    """Một dòng thu khai nhầm sang phía chi thì nó bị TRỪ thay vì CỘNG – và bảng vẫn ra một con số
    trông như đúng, chỉ nhỏ đi gấp đôi khoản ấy."""
    for d in SEC.CAC_DONG:
        if not d.tu_so_nghia_vu or d.phia == SEC.GHI_NHO:
            continue
        huong = NHOM[d.ma][0]
        assert d.phia == (SEC.VAO if huong == "thu" else SEC.RA), d.ma


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
# 10. CF-07 · mỗi dòng phải có một cửa nhập và một bộ phận chịu trách nhiệm
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
    """Nó cạn dần khi các cửa nhập được dựng xong.

    ĐO LẠI ngày 13/9 trên kho mã, không đọc từ tài liệu: sau khi VPM-11 nối sổ nghĩa vụ vào sáu
    bảng nguồn, chỉ còn BA dòng chưa có nguồn. Con số 'tám dòng' ghi ngày 11/9 là đọc từ bảng III.4
    của tài liệu chứ không phải đo từ mã – và nó đã sai.
    """
    thieu = set(SEC.dong_chua_co_nguon())
    assert thieu <= set(SEC.CUA_NHAP)
    assert thieu == {"hoa_hong", "thu_ho_khach", "ky_quy_lu_hanh"}


def test_ba_dong_chi_nhap_tay_van_duoc_ghi_ro_la_nhap_tay():
    """Có nguồn KHÔNG có nghĩa là tự động. Ba dòng này chỉ chảy vào sổ khi kế toán gõ vào
    `cash_plan_items` – hỏng một tháng không gõ thì bảng vẫn xanh và vẫn thiếu tiền thật."""
    for ma in ("thu_cong_no_khac", "luong_bh", "thue"):
        assert "nhập tay" in SEC.CUA_NHAP[ma].nguon, ma


def test_cua_nhap_luong_giu_lai_HAI_viec_con_thieu():
    """Hai việc khác nhau, và bỏ quên việc nào cũng để lại một con số trông như đúng.

    (1) CỘT BỘ PHẬN – thiếu nó thì con số lương rộng hơn phạm vi tour–xe (xem GHI_CHU_LAN_SANG).
    (2) NỐI PayrollRun VÀO SỔ NGHĨA VỤ – đo 13/9: bảng lương đã có số thật, có chữ ký TGĐ, đã ghi
        sổ kế toán khi ký; nhưng sổ nghĩa vụ chỉ nhận lương qua cash_plan_items gõ tay. Hai con số
        cho cùng một khoản tiền, không gì buộc chúng bằng nhau, lệch thì không ai kêu.
    """
    c = SEC.CUA_NHAP["luong_bh"]
    assert "CỘT BỘ PHẬN" in c.cua
    assert "PayrollRun" in c.cua and "sổ nghĩa vụ" in c.cua
    assert "CHƯA nối vào sổ nghĩa vụ" in c.nguon, "mất dấu việc còn thiếu ở cột nguồn"


def test_hai_dong_ghi_nho_van_ghi_ro_la_NAM_NGOAI_bang_III4():
    """Chủ tịch đã chốt cửa cho hai dòng ghi nhớ ngày 11/9/2026, nhưng bảng III.4 của v1.1 vẫn chỉ
    có 12 dòng. Giữ dấu ấy lại để lần sau ai đối chiếu mã với tài liệu thấy ngay vì sao lệch hai
    dòng, thay vì tưởng có người tự thêm bừa."""
    for ma in ("thu_ho_khach", "ky_quy_lu_hanh"):
        assert SEC.CUA_NHAP[ma].ngoai_bang_III4 is True
    trong_tai_lieu = [ma for ma, c in SEC.CUA_NHAP.items() if not c.ngoai_bang_III4]
    assert len(trong_tai_lieu) == 12, "bảng III.4 của v1.1 có đúng 12 dòng"
