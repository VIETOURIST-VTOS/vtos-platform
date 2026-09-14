# -*- coding: utf-8 -*-
"""DT-3 · Dựng bảng dòng tiền bốn mốc từ sổ nghĩa vụ.

Phép thử chạy trên SỔ THẬT trong cơ sở dữ liệu sqlite, dùng đúng bốn hàm đọc của VPM-11 đã trích
nguyên văn. Không giả lập phép cộng: một bảng dòng tiền mà phép thử tự bịa số thì nó chỉ chứng
minh rằng hàm bịa số chạy được.

Tệp này canh năm chuyện, cả năm đều cho ra một con số TRÔNG NHƯ ĐÚNG khi hỏng:

  1. Luỹ kế dựng bằng cách cộng cột trước vào cột sau — sai số làm tròn nhân lên, và một khoản xếp
     nhầm cột thì sai ở mọi cột từ đó về sau.
  2. Khoản PHẢI THU quá hạn tự chảy vào các cột — bảng có thêm tiền mà công ty không có.
  3. Một lần đọc sổ quên truyền vai trò — bảng của Tổng giám đốc vẫn đủ dòng, chỉ là mỗi dòng mang
     số của toàn tập đoàn.
  4. Ô không có số trả về số 0 — "chưa có cửa nhập" biến thành "công ty không nợ đồng nào".
  5. Chỉ tiêu B dùng làm số đầu kỳ — lỗi trừ hai lần quay lại.
"""
from datetime import date, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import core as _core  # noqa: F401  – nạp bảng companies/tours mà khoá ngoại trỏ tới
from app.models.nghia_vu import NghiaVuThanhToan
from app.services import dong_tien_bang as B
from app.services import dong_tien_ky as KY
from app.services import dong_tien_pham_vi as PV

HOM_NAY = date(2026, 9, 13)


@pytest.fixture()
def db():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    with Session(m) as s:
        yield s


_dem = [0]


def them(db, nhom, tien, *, ngay=None, huong=None, da_tra=0.0, trang_thai="du_kien",
         ghi_nho=False, company_id=None):
    from app.models.nghia_vu import NHOM
    _dem[0] += 1
    i = _dem[0]
    db.add(NghiaVuThanhToan(
        ma_goc=f"NV-T{i:04d}", huong=huong or NHOM[nhom][0], nhom=nhom, ghi_nho=ghi_nho,
        company_id=company_id, tong_nghia_vu=tien, da_tra=da_tra,
        ngay_cam_ket=ngay, ngay_du_kien_tra=ngay, trang_thai=trang_thai,
        nguon_bang="test", nguon_id=9000 + i, loai_tien="VND"))
    db.commit()


def o(bang, ma_dong, ma_moc):
    return [d for d in bang["dong"] if d["ma"] == ma_dong][0]["o"][ma_moc]


# =============================================================================================
# 1. Luỹ kế đến từ KHOẢNG NGÀY, không từ phép cộng các cột
# =============================================================================================

def test_cot_sau_chua_tron_ven_cot_truoc(db):
    """Ba khoản rơi vào ba mốc khác nhau. Cột 2 tháng phải chứa cả ba."""
    them(db, "tra_ncc", 10_000_000, ngay=HOM_NAY + timedelta(days=3))    # trong 1 tuần
    them(db, "tra_ncc", 20_000_000, ngay=HOM_NAY + timedelta(days=10))   # trong 2 tuần
    them(db, "tra_ncc", 40_000_000, ngay=HOM_NAY + timedelta(days=40))   # trong 2 tháng
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tra_ncc", "7n")["so_da_tron"] == 10_000_000
    assert o(b, "tra_ncc", "14n")["so_da_tron"] == 30_000_000
    assert o(b, "tra_ncc", "1t")["so_da_tron"] == 30_000_000
    assert o(b, "tra_ncc", "2t")["so_da_tron"] == 70_000_000


def test_moi_cot_doc_lai_so_tu_dau_chu_khong_cong_don_cot_truoc(db):
    """Một khoản NGAY BIÊN giữa hai cột. Nếu cột sau dựng bằng cách cộng cột trước với phần đuôi
    thì khoản này bị đếm hai lần hoặc rơi mất, tuỳ cách viết phần đuôi."""
    them(db, "tra_ncc", 7_000_000, ngay=HOM_NAY + timedelta(days=6))     # ngày cuối của cột 1 tuần
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    for c in KY.MA_MOC:
        assert o(b, "tra_ncc", c)["so_da_tron"] == 7_000_000, c


def test_khoan_den_han_DUNG_HOM_NAY_nam_trong_cot_dau(db):
    """Nó là khoản gấp nhất trong bảng – rơi ra ngoài là mất đúng khoản đáng lo nhất."""
    them(db, "tra_ncc", 5_000_000, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tra_ncc", "7n")["so_da_tron"] == 5_000_000


def test_khoan_xa_hon_hai_thang_KHONG_vao_bang_nhung_KHONG_mat(db):
    them(db, "tra_ncc", 9_000_000, ngay=HOM_NAY + timedelta(days=200))
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tra_ncc", "2t")["so_da_tron"] == 0
    assert b["ba_ro"]["ngoai_tam_nhin"]["tong"] == 9_000_000, "khoản ngoài tầm nhìn bị bỏ im lặng"


# =============================================================================================
# 2. Quá hạn: CHI vào mọi cột, THU không vào cột nào
# =============================================================================================

def test_CHI_qua_han_cong_vao_MOI_cot(db):
    them(db, "tra_ncc", 3_000_000, ngay=HOM_NAY - timedelta(days=30))
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    for c in KY.MA_MOC:
        assert o(b, "tra_ncc", c)["so_da_tron"] == 3_000_000, c
    assert b["qua_han_theo_nhom"]["tra_ncc"]["so_da_tron"] == 3_000_000


def test_THU_qua_han_KHONG_cong_vao_cot_nao(db):
    """Chỗ bản đầu của làn này sai: xử thu và chi đối xứng nhau.

    Tiền ra thì mình quyết, tiền vào thì không. Mặc định rằng một khoản phải thu quá hạn sẽ thu
    được ngay là cách làm bảng dòng tiền đẹp hơn sự thật – và nó đẹp đúng ở dòng đáy.
    """
    them(db, "thu_khach", 50_000_000, ngay=HOM_NAY - timedelta(days=20))
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    for c in KY.MA_MOC:
        assert o(b, "thu_khach", c)["so_da_tron"] == 0, c
    assert b["qua_han_theo_nhom"]["thu_khach"]["so_da_tron"] == 50_000_000, \
        "khoản phải thu quá hạn bị giấu hẳn – phải hiện riêng, chỉ là không tự cộng"


def test_qua_han_hien_RIENG_chu_khong_chi_lan_vao_cot(db):
    """Hiện riêng để người đọc phân biệt 'phải trả tuần này' với 'lẽ ra phải trả từ tháng trước'."""
    them(db, "tra_ncc", 2_000_000, ngay=HOM_NAY - timedelta(days=5))
    them(db, "tra_ncc", 8_000_000, ngay=HOM_NAY + timedelta(days=5))
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert b["qua_han_theo_nhom"]["tra_ncc"]["so_da_tron"] == 2_000_000
    assert o(b, "tra_ncc", "7n")["so_da_tron"] == 10_000_000
    assert b["ba_ro"]["qua_han"]["tong"] == 2_000_000


def test_luat_qua_han_KHONG_chep_lai_trong_tep_dung_bang():
    """Luật THU/CHI nằm ở dong_tien_ky.luy_ke(). Chép lại là hẹn trước một lần lệch."""
    import inspect
    nguon = inspect.getsource(B)
    assert "KY.luy_ke(" in nguon
    assert nguon.count("luy_ke") >= 1


# =============================================================================================
# 3. Mọi lần đọc sổ đều phải truyền vai trò
# =============================================================================================

def test_khong_co_lan_doc_so_nao_quen_vai_tro():
    """`_loc()` của VPM-11: vai_tro rỗng thì KHÔNG lọc theo nhóm. Quên một chỗ là chỗ ấy trả cả sổ,
    và bảng của TGĐ vẫn đủ dòng – chỉ là mỗi dòng mang số của toàn tập đoàn."""
    assert B.kiem_khong_doc_so_khi_thieu_vai_tro() == []


def test_ham_canh_vai_tro_CO_KEU_khi_dang_keu():
    """Một hàm canh bị làm cho câm vẫn trả danh sách rỗng, và phép thử trên vẫn xanh y như khi mọi
    thứ đều đúng. Nên phải thử cả chiều ngược lại: đưa cho nó một đoạn mã sai và bắt nó kêu."""
    xau = "x = NV.cong(db, a, b, company_id=1)\ny = NV.ba_ro(db, c, vai_tro=v)\n"
    keu = B.kiem_khong_doc_so_khi_thieu_vai_tro(xau)
    assert len(keu) == 1 and "NV.cong()" in keu[0]
    assert B.kiem_khong_doc_so_khi_thieu_vai_tro("z = NV.cong(db, a, b, vai_tro=v)\n") == []


def test_TGD_khong_thay_tien_cua_nhom_ngoai_tam(db):
    them(db, "tra_goc_vay", 900_000_000, ngay=HOM_NAY + timedelta(days=5))
    them(db, "tra_ncc", 4_000_000, ngay=HOM_NAY + timedelta(days=5))
    tgd = B.bang(db, "tgd", hom_nay=HOM_NAY)
    assert "tra_goc_vay" not in {d["ma"] for d in tgd["dong"]}
    assert o(tgd, "tong_chi", "7n")["so_da_tron"] == 4_000_000, \
        "dòng TỔNG của TGĐ đang mang cả khoản trả gốc vay"
    ct = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(ct, "tong_chi", "7n")["so_da_tron"] == 904_000_000


def test_dong_luong_CO_SO_tren_bang_TGD_theo_chot_13_9(db):
    them(db, "luong_bh", 600_000_000, ngay=HOM_NAY + timedelta(days=10))
    tgd = B.bang(db, "tgd", hom_nay=HOM_NAY)
    assert o(tgd, "luong_bhxh", "14n")["so_da_tron"] == 600_000_000
    assert o(tgd, "tong_chi", "14n")["so_da_tron"] == 600_000_000


def test_vai_tro_khong_mo_duoc_khoi_thi_khong_co_bang(db):
    them(db, "tra_ncc", 1_000_000, ngay=HOM_NAY)
    b = B.bang(db, "ptgd_kd", hom_nay=HOM_NAY)
    assert b["xem_duoc"] is False
    assert "dong" not in b and "ba_ro" not in b


def test_loc_theo_phap_nhan_di_thang_xuong_so(db):
    them(db, "tra_ncc", 11_000_000, ngay=HOM_NAY, company_id=1)
    them(db, "tra_ncc", 22_000_000, ngay=HOM_NAY, company_id=2)
    b1 = B.bang(db, "chutich", hom_nay=HOM_NAY, company_id=1)
    assert o(b1, "tra_ncc", "7n")["so_da_tron"] == 11_000_000


# =============================================================================================
# 4. Ô không có số thì KHÔNG trả số 0
# =============================================================================================

def test_o_khong_co_so_khong_co_khoa_so(db):
    """Trả 0 thì bên nhận cộng nó vào như một con số thật. Trả {"so": None} thì họ viết
    `o["so"] or 0`. Nên KHÔNG có khoá "so" nào cả – muốn cộng phải đọc cờ trước."""
    them(db, "tra_ncc", 1_000_000, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    ghi = o(b, "ghi_nho_thu_ho", "7n")
    assert ghi["co_so"] is False
    assert "so" not in ghi and "so_da_tron" not in ghi
    assert "Chưa có cửa nhập" in ghi["hien"]


def test_dong_ghi_nho_KHONG_BAO_GIO_vao_phep_cong(db):
    """Tiền thu hộ nằm trong tài khoản nhưng KHÔNG phải của công ty."""
    them(db, "thu_ho_khach", 700_000_000, ngay=HOM_NAY, ghi_nho=True)
    them(db, "thu_khach", 100_000_000, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tong_thu", "7n")["so_da_tron"] == 100_000_000
    assert o(b, "ghi_nho_thu_ho", "7n")["co_so"] is False


def test_ba_dong_so_du_khong_co_tren_bang_TGD(db):
    them(db, "tra_ncc", 1_000_000, ngay=HOM_NAY)
    tgd = B.bang(db, "tgd", hom_nay=HOM_NAY)
    assert not (set(PV.CHI_TOAN_CANH) & {d["ma"] for d in tgd["dong"]})
    assert "số dư" not in tgd["ten_dong_day"].lower()


def test_thieu_so_dau_ky_thi_KHONG_suy_ra_so_du_tu_chenh_lech_thu_chi(db):
    """Một bảng ghi 'số dư cuối khoảng 1,2 tỷ' mà thực ra chỉ là 'thu trừ chi trong khoảng' là một
    câu nói dối đúng đến từng chữ số."""
    them(db, "thu_khach", 5_000_000_000, ngay=HOM_NAY)
    them(db, "tra_ncc", 1_000_000_000, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)                 # không truyền dau_ky
    x = o(b, "so_du_du_kien_cuoi_khoang", "7n")
    assert x["co_so"] is False and "so" not in x
    assert "Chưa chốt tiền được phép sử dụng" in x["hien"]


def test_co_so_dau_ky_thi_so_du_bang_dau_ky_cong_thu_tru_chi(db):
    them(db, "thu_khach", 5_000_000_000, ngay=HOM_NAY)
    them(db, "tra_ncc", 1_000_000_000, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY, dau_ky=2_000_000_000)
    assert o(b, "tien_kha_dung_dau_ky", "7n")["so_da_tron"] == 2_000_000_000
    assert o(b, "so_du_du_kien_cuoi_khoang", "7n")["so_da_tron"] == 6_000_000_000


# =============================================================================================
# 5. Chỉ tiêu B KHÔNG được dùng làm số đầu kỳ
# =============================================================================================

def test_truyen_chi_tieu_B_lam_dau_ky_thi_NEM_LOI(db):
    """Lỗi trừ hai lần ngày 13/9: A đã trừ lệnh chi, rồi bảng dự báo đọc lại chính các lệnh chi ấy
    từ sổ và trừ thêm lần nữa. Cờ dung_lam_dau_ky là hàng rào cuối cùng, và đây là chỗ nó chặn."""
    b_chi_tieu = KY.tien_con_bo_tri_moi({"so": 100_000_000}, 20_000_000)
    assert b_chi_tieu["dung_lam_dau_ky"] is False
    with pytest.raises(ValueError, match="trừ lệnh chi hai lần"):
        B.bang(db, "chutich", hom_nay=HOM_NAY, dau_ky=b_chi_tieu)


def test_chi_tieu_A_chua_tinh_duoc_thi_khong_ra_so_du(db):
    """A thiếu một thành phần thì không có khoá "so" – bảng phải im lặng đúng chỗ, không đoán."""
    a = KY.tien_duoc_phep_su_dung({"so_du_ngan_hang": 1_000_000_000})   # thiếu tiền mặt kiểm kê
    assert "so" not in a
    b = B.bang(db, "chutich", hom_nay=HOM_NAY, dau_ky=a)
    assert o(b, "so_du_du_kien_cuoi_khoang", "7n")["co_so"] is False


# =============================================================================================
# 6. Hai cơ sở ngày, hai tên gọi – chỗ dịch tay phải nổ khi sai
# =============================================================================================

def test_co_so_ngay_la_thi_NEM_LOI_chu_khong_roi_em_vao_nhanh_du_kien(db):
    """`NV.cong()` viết `if co_so_ngay == "cam_ket" ... else ngày dự kiến`, nên MỌI chuỗi lạ – kể
    cả một lỗi gõ – rơi êm vào nhánh ngày dự kiến và chạy đúng một nửa thời gian."""
    for xau in ("du_kien", "thuc_hien_", "", "CAM_KET"):
        with pytest.raises(ValueError, match="Cơ sở ngày"):
            B.bang(db, "chutich", hom_nay=HOM_NAY, co_so=xau)


def test_hai_co_so_ngay_cho_hai_con_so_va_hai_NHAN_khac_nhau(db):
    them(db, "tra_ncc", 6_000_000, ngay=HOM_NAY + timedelta(days=3))
    a = B.bang(db, "chutich", hom_nay=HOM_NAY, co_so=KY.CAM_KET)
    c = B.bang(db, "chutich", hom_nay=HOM_NAY, co_so=KY.THUC_HIEN)
    assert a["nhan_so_du"] != c["nhan_so_du"], \
        "hai con số khác nhau mà cùng một nhãn thì người đọc kết luận số liệu chạy lung tung"
    assert a["nhan_co_so"] == "Nghĩa vụ đến hạn"
    assert c["nhan_co_so"] == "Kế hoạch thực thu – chi"


# =============================================================================================
# 7. Các luật của sổ mà bảng này thừa hưởng – canh để biết khi chúng đổi
# =============================================================================================

def test_tra_mot_phan_thi_du_bao_PHAN_CON_LAI(db):
    them(db, "tra_ncc", 10_000_000, da_tra=7_000_000, ngay=HOM_NAY + timedelta(days=2))
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tra_ncc", "7n")["so_da_tron"] == 3_000_000


def test_khoan_da_tat_toan_va_da_huy_khong_con_la_nhu_cau_tien(db):
    them(db, "tra_ncc", 8_000_000, ngay=HOM_NAY, trang_thai="da_tra")
    them(db, "tra_ncc", 9_000_000, ngay=HOM_NAY, trang_thai="huy")
    them(db, "tra_ncc", 1_000_000, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tra_ncc", "7n")["so_da_tron"] == 1_000_000


def test_khoan_KHONG_CO_NGAY_vao_ro_chua_du_du_lieu_chu_khong_bien_mat(db):
    them(db, "tra_ncc", 12_000_000, ngay=None)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "tra_ncc", "2t")["so_da_tron"] == 0
    assert b["ba_ro"]["chua_du_du_lieu"]["tong"] == 12_000_000
    assert b["ba_ro"]["chua_du_du_lieu"]["so_khoan"] == 1


def test_dong_TONG_la_tong_cua_cac_dong_DA_LAM_TRON(db):
    """Ràng buộc của Chủ tịch: màn hình và Excel dùng chung một hàm, và dòng tổng cộng các dòng ĐÃ
    làm tròn. Viết lam_tron(sum(...)) thì nhanh hơn một chữ và sai theo cách không ai nhìn ra."""
    them(db, "tra_ncc", 1_000_000.4, ngay=HOM_NAY)
    them(db, "hoan_khach", 2_000_000.4, ngay=HOM_NAY)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    tong = o(b, "tong_chi", "7n")
    assert tong["so_da_tron"] == (o(b, "tra_ncc", "7n")["so_da_tron"]
                                  + o(b, "hoan_tra_khach", "7n")["so_da_tron"])
    assert tong["hien"] == tong["hien"].strip() and tong["hien"]


def test_so_tu_so_nghia_vu_VE_DA_LA_SO_NGUYEN(db):
    """Ghi lại chỗ tệp này ĐANG DỰA VÀO, để biết ngay khi nó đổi.

    `NV.cong()` của VPM-11 làm tròn một lần ở đầu ra (`round(v)` theo từng nhóm). Vì số về đây đã
    nguyên, "cộng rồi làm tròn" và "cộng các số đã tròn" cho ra cùng một kết quả — tức thứ tự làm
    tròn ở tệp này HÔM NAY không quan sát được từ ngoài.

    Nó chỉ không quan sát được CHỪNG NÀO họ còn làm tròn. Ngày nào `cong()` trả số lẻ, thứ tự ấy
    bắt đầu đổi kết quả và đổi ÂM THẦM. Phép thử này đỏ đúng ngày đó, và người đọc dòng đỏ sẽ được
    dẫn tới đây thay vì đi tìm một khoản lệch vài đồng trong bảng kiểm toán.
    """
    them(db, "tra_ncc", 1_000_000.4, ngay=HOM_NAY)
    them(db, "hoan_khach", 2_000_000.6, ngay=HOM_NAY)
    from app.services import nghia_vu as NV
    tho = NV.cong(db, HOM_NAY, HOM_NAY, co_so_ngay="cam_ket", vai_tro="chutich")
    assert tho, "không đọc được gì – phép thử mất tác dụng"
    for nhom, v in tho.items():
        assert float(v).is_integer(), (
            f"nhóm {nhom} về {v} – sổ nghĩa vụ đã thôi làm tròn ở đầu ra. "
            "Đọc lại thứ tự làm tròn ở dong_tien_bang._o_mot_dong().")


def test_dong_cach_thu_tu_khong_co_so_va_khong_vao_TONG(db, monkeypatch):
    """Dòng đi theo cách thứ tư: có mặt, không có số, không vào phép cộng.

    GHI RÕ ĐIỀU ĐO ĐƯỢC, vì nó khác điều bản nháp của phép thử này tưởng: số của dòng ấy KHÔNG hề
    về tới tầng dựng bảng. `nhom_duoc_xem()` đã loại nó ngay tại câu truy vấn, nên `theo_moc` không
    có khoá của nó và phép cộng lấy ra 0.

    Tức HAI TẦNG LỌC ĐANG CHỒNG NHAU: tầng dưới (câu truy vấn) chặn tiền, tầng trên (`dong_de_cong`
    của khung) chặn mã. Hôm nay tháo tầng trên ra thì bảng KHÔNG đổi một đồng nào – phép thử đột
    biến N11 đã chứng minh đúng như vậy.

    Giữ tầng trên, và giữ câu này: một hàng rào thừa thì rẻ, còn ngày nào tầng dưới nới ra – ví dụ
    ai đó cho dòng ngoài tầm về tới đây kèm số để vẽ ô "chưa xác định" – thì tầng trên là thứ duy
    nhất còn chặn tiền lại. Đừng dọn nó đi vì thấy phép thử vẫn xanh khi không có nó.
    """
    monkeypatch.setitem(PV.CHUA_TACH_DUOC, "thue_nghia_vu", "Lý do dựng tại chỗ cho phép thử.")
    them(db, "thue", 800_000_000, ngay=HOM_NAY)
    them(db, "tra_ncc", 5_000_000, ngay=HOM_NAY)
    b = B.bang(db, "tgd", hom_nay=HOM_NAY)
    assert o(b, "thue_nghia_vu", "7n")["co_so"] is False, "dòng cách thứ tư đang hiện số"
    assert o(b, "tong_chi", "7n")["so_da_tron"] == 5_000_000

    # Chứng minh thẳng điều nói ở trên, thay vì tin vào nó: số không về tới tầng này.
    from app.services import nghia_vu as NV
    tho = NV.cong(db, HOM_NAY, HOM_NAY, co_so_ngay="cam_ket", vai_tro="tgd")
    assert "thue" not in tho, (
        "sổ nay TRẢ VỀ cả nhóm ngoài tầm – tầng lọc trên (dong_de_cong) từ nay là hàng rào THẬT, "
        "không còn thừa. Đọc lại _o_mot_dong() trước khi sửa gì.")


def test_bang_mang_theo_bon_cot_co_ngay_dau_ngay_cuoi_viet_san(db):
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert [c["ma"] for c in b["cot"]] == KY.MA_MOC
    for c in b["cot"]:
        assert c["tu_hien"] and c["den_hien"] and c["so_ngay"] > 0


def test_bang_mang_theo_co_bao_cao_chua_day_du(db):
    b = B.bang(db, "chutich", hom_nay=HOM_NAY, nhom_chua_phan_loai=["tam_ung_du_an"])
    assert b["day_du"]["day_du"] is False
    assert "tam_ung_du_an" in b["day_du"]["cau"]


# =============================================================================================
# 8. Lỗ "chưa rõ pháp nhân" — đo được 13/9, không vá được ở đây nhưng KHÔNG để im lặng
# =============================================================================================

def test_nghia_vu_chua_ro_phap_nhan_ROI_RA_NGOAI_bang_tung_phap_nhan(db):
    """`cash_plan_items` không có cột company_id, nên bộ nạp ghi pháp nhân RỖNG, và `_loc()` lọc
    `company_id == <id>` loại hết. Bảng ấy lại là NGUỒN DUY NHẤT của lương, thuế và thu công nợ
    khác — ba dòng biến thành 0, và 0 đọc là 'kỳ này không phải trả lương'."""
    them(db, "luong_bh", 900_000_000, ngay=HOM_NAY + timedelta(days=5), company_id=None)
    them(db, "tra_ncc", 4_000_000, ngay=HOM_NAY + timedelta(days=5), company_id=7)

    b7 = B.bang(db, "chutich", hom_nay=HOM_NAY, company_id=7)
    assert o(b7, "luong_bhxh", "7n")["so_da_tron"] == 0, "tiền đề đổi – đọc lại _loc() của VPM-11"
    c = b7["canh_bao_pham_vi"]
    assert c["co_khoan_roi_ra_ngoai"] is True
    assert c["tong"] == 900_000_000
    assert "Lương, bảo hiểm và liên quan" in c["cau"] and "ĐANG THIẾU" in c["cau"]


def test_bang_toan_tap_doan_khong_loc_nen_khong_mat_gi(db):
    them(db, "luong_bh", 900_000_000, ngay=HOM_NAY + timedelta(days=5), company_id=None)
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)                 # không truyền company_id
    assert o(b, "luong_bhxh", "7n")["so_da_tron"] == 900_000_000
    assert b["canh_bao_pham_vi"]["co_khoan_roi_ra_ngoai"] is False


def test_khong_co_khoan_nao_roi_ra_thi_khong_keu(db):
    """Một cảnh báo kêu cả lúc không có gì là một cảnh báo sắp bị tắt đi."""
    them(db, "tra_ncc", 4_000_000, ngay=HOM_NAY + timedelta(days=5), company_id=7)
    c = B.bang(db, "chutich", hom_nay=HOM_NAY, company_id=7)["canh_bao_pham_vi"]
    assert c["co_khoan_roi_ra_ngoai"] is False and c["cau"] == ""


def test_khoan_ghi_nho_va_khoan_da_dong_khong_tinh_vao_phan_roi_ra(db):
    them(db, "thu_ho_khach", 500_000_000, ngay=HOM_NAY, ghi_nho=True, company_id=None)
    them(db, "tra_ncc", 300_000_000, ngay=HOM_NAY, trang_thai="da_tra", company_id=None)
    c = B.bang(db, "chutich", hom_nay=HOM_NAY, company_id=7)["canh_bao_pham_vi"]
    assert c["co_khoan_roi_ra_ngoai"] is False, "đang đếm cả khoản ghi nhớ hoặc khoản đã tất toán"


# =============================================================================================
# 6. Cầu SỔ → BẢNG: dịch tên, và KHÔNG được vứt tên nào
# =============================================================================================
# Sổ nghĩa vụ gọi một dòng là `hoan_khach`; bảng trình bày v1.1 gọi nó là `hoan_tra_khach`. Bảy
# dòng lệch như thế, nên `doc_mot_moc()` phải DỊCH trước khi trả về. Hai chỗ hỏng, cả hai đều im:
#
#   · quên dịch        → bảy dòng chi đọc `.get(ma, 0.0)` ra 0, bảng nhẹ hơn sự thật
#   · dịch mà vứt bớt  → một nhóm mới của sổ biến mất TRƯỚC khi ai kịp thấy nó
#
# Chuyện thứ nhất đã xảy ra thật ngày 14/9/2026. Chuyện thứ hai chưa, và hai phép thử này dựng lên
# để nó đừng xảy ra lần đầu trên bảng của Chủ tịch.

def test_so_cua_dong_lech_ten_van_ve_dung_dong_cua_no(db):
    """`luong_bh` của sổ phải hiện ở dòng `luong_bhxh` của bảng – không phải ở đâu khác, và không
    phải bằng 0."""
    them(db, "luong_bh", 123_000_000, ngay=HOM_NAY + timedelta(days=3))
    b = B.bang(db, "chutich", hom_nay=HOM_NAY)
    assert o(b, "luong_bhxh", "7n")["so_da_tron"] == 123_000_000
    assert PV.NHOM_SANG_MA["luong_bh"] == "luong_bhxh"
    assert [d["ma"] for d in b["dong"]].count("luong_bh") == 0, (
        "bảng đang hiện MÃ CỦA SỔ – cầu sang khung_dong_tien tra theo mã của BẢNG, "
        "nên dòng này sẽ trống trên màn hình 01")


def test_nhom_MOI_cua_so_chua_co_dong_nao_nhan_thi_KHONG_bi_vut_im_lang(db, monkeypatch):
    """Trục NHÓM mở mặc định: nhóm mới thêm vào sổ mà chưa lên bảng vẫn phải CÒN SỐ khi đi qua cầu.

    Vứt nó đi ở bước dịch là bỏ sót tiền, và bỏ sót không kêu: `day_du()` không còn gì để đếm, nên
    bảng tự nhận là ĐẦY ĐỦ trong khi vừa đánh rơi một khoản thật. Đúng kiểu sai mà cả tệp này sinh
    ra để chặn – "một con số trông như đúng".
    """
    from app.models.nghia_vu import NHOM
    monkeypatch.setitem(NHOM, "nhom_moi_chua_len_bang", ("chi", "Nhóm mới của sổ"))
    them(db, "nhom_moi_chua_len_bang", 77_000_000, ngay=HOM_NAY + timedelta(days=2))

    theo_moc = B.doc_mot_moc(db, "chutich", "7n", hom_nay=HOM_NAY)
    assert theo_moc.get("nhom_moi_chua_len_bang") == 77_000_000, (
        "bước dịch SỔ→BẢNG đang VỨT nhóm chưa có dòng. Giữ nguyên tên nó, đừng bỏ: "
        "xem _sang_ma_dong() trong dong_tien_bang.py")
