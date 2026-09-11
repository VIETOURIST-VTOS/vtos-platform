# -*- coding: utf-8 -*-
"""PQ-10 · Phạm vi ĐƯỢC PHÉP tách khỏi phạm vi ĐANG XEM, và làm tròn tiền một hàm duy nhất.

Hai chuyện tệp này canh, và cả hai đều là chuyện "xanh vì không nhìn thấy gì" rất dễ xảy ra:

  1. Lựa chọn của người dùng KHÔNG BAO GIỜ nới rộng được phạm vi được phép. Một đột biến bỏ dòng
     kiểm quyền đi vẫn làm mọi phép thử "chọn đúng thì xem được" xanh như cũ – nên ở đây có phép
     thử đi từ chiều ngược lại: chọn một đơn vị NGOÀI phạm vi và đòi phải rỗng, không phải đòi
     "không lỗi".

  2. Dòng tổng bằng TỔNG CÁC DÒNG ĐÃ LÀM TRÒN. Viết lam_tron(sum(...)) chỉ lệch vài đồng, nên phép
     thử phải dựng đúng bộ số làm hai cách ấy khác nhau – bộ số tròn trịa sẽ cho cả hai cách cùng
     kết quả và phép thử thành vô dụng.
"""
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
from app.models.core import Company, User
from app.services import pham_vi_dang_xem as DX
from app.services import lam_tron_tien as LT


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    # check_same_thread=False + StaticPool: phép thử vòng parent_id phải gọi hàm trong một luồng
    # riêng để còn đặt được hạn giờ; mặc định của sqlite cấm dùng chung nối kết giữa hai luồng.
    eng = sa.create_engine("sqlite+pysqlite:///:memory:", poolclass=sa.pool.StaticPool,
                           connect_args={"check_same_thread": False})
    md.create_all(eng)
    with Session(eng) as s:
        yield s


@pytest.fixture()
def nhom(db):
    """Một nhóm thật ba tầng, để phép thử không chỉ đúng cho cây phẳng.

        1 Vietourist Holdings (me)
          ├─ 3 Chi nhánh Cần Thơ (chi_nhanh)
          │    └─ 5 Tổ Cần Thơ 2 (chi_nhanh, ĐÃ NGỪNG)
          └─ 4 VPĐD Hà Nội (chi_nhanh)
        2 Vận tải Vietrip (con) – KHÔNG thuộc cây của 1
    """
    db.add_all([
        Company(id=1, code="VTD", name="Vietourist Holdings", kind="me", active=True),
        Company(id=2, code="VTRIP", name="Vận tải Vietrip", kind="con", active=True),
        Company(id=3, code="CT", name="Chi nhánh Cần Thơ", kind="chi_nhanh", parent_id=1, active=True),
        Company(id=4, code="HN", name="VPĐD Hà Nội", kind="chi_nhanh", parent_id=1, active=True),
        Company(id=5, code="CT2", name="Tổ Cần Thơ 2", kind="chi_nhanh", parent_id=3, active=False),
    ])
    db.flush()
    return db


def _nguoi(vai_tro="nv_dh", company_id=None):
    return User(id=1, username="x", full_name="X", role=vai_tro, company_id=company_id)


# =============================================================================================
# 1. Phạm vi ĐƯỢC PHÉP – đi xuống theo parent_id
# =============================================================================================

def test_toan_cong_ty_gom_ca_don_vi_truc_thuoc(nhom):
    """Đây là chỗ hôm nay CHƯA có: loc() cũ so sánh company_id == cid nên dừng ở tầng một."""
    assert DX.duoc_phep(nhom, _nguoi("nv_dh", 1)) == {1, 3, 4, 5}
    assert DX.duoc_phep(nhom, _nguoi("nv_dh", 3)) == {3, 5}
    assert DX.duoc_phep(nhom, _nguoi("nv_dh", 5)) == {5}


def test_cay_anh_em_khong_lot_vao(nhom):
    """Vận tải Vietrip không nằm dưới Holdings, nên người của Holdings không được kéo nó vào."""
    assert 2 not in DX.duoc_phep(nhom, _nguoi("nv_dh", 1))


def test_vai_tro_toan_tap_doan_khong_bi_gioi_han(nhom):
    from app.services import pham_vi_phap_nhan as PV
    for vai in PV.TOAN_TAP_DOAN:
        assert DX.duoc_phep(nhom, _nguoi(vai, None)) is None, vai


def test_vong_parent_id_khong_treo_may_chu(nhom):
    """parent_id do người nhập. Một ô nhập nhầm không được phép treo máy chủ.

    Không có khóa chống vòng thì phép thử này KHÔNG đỏ – nó chạy mãi, và cả bộ kiểm đứng lại. Đó
    là lý do nó kèm hạn giờ thay vì chỉ assert.
    """
    nhom.execute(sa.update(Company).where(Company.id == 1).values(parent_id=5))
    nhom.flush()
    import threading
    ra = {}
    t = threading.Thread(target=lambda: ra.update(x=DX.hau_due(nhom, 1)), daemon=True)
    t.start()
    t.join(timeout=5)
    assert not t.is_alive(), "hau_due() chạy quá 5 giây – vòng parent_id chưa bị chặn"
    assert ra["x"] == {1, 3, 4, 5}


# =============================================================================================
# 2. Cây đơn vị để vẽ nút chọn
# =============================================================================================

def test_cay_long_dung_tang_va_dem_du(nhom):
    c = DX.cay(nhom, _nguoi("nv_dh", 1))
    assert [n["company_id"] for n in c] == [1]
    assert c[0]["cap"] == 0
    con = {n["company_id"]: n for n in c[0]["con"]}
    assert set(con) == {3, 4} and con[3]["cap"] == 1
    assert [n["company_id"] for n in con[3]["con"]] == [5] and con[3]["con"][0]["cap"] == 2
    assert DX.so_don_vi(c) == 4


def test_don_vi_da_ngung_van_hien_va_van_chon_duoc(nhom):
    """Chi nhánh đóng cửa tháng 6 vẫn còn số liệu sáu tháng đầu năm."""
    c = DX.cay(nhom, _nguoi("nv_dh", 3))
    to = c[0]["con"][0]
    assert to["company_id"] == 5 and to["hoat_dong"] is False
    assert DX.kiem_chon(nhom, _nguoi("nv_dh", 3), DX.DON_VI, 5)["ok"] is True


def test_cha_ngoai_pham_vi_thi_khong_bi_keo_vao_cay(nhom):
    """Kéo cha vào cho đủ hình là để lộ đúng thứ phạm vi đang chặn."""
    c = DX.cay(nhom, _nguoi("nv_dh", 3))
    assert [n["company_id"] for n in c] == [3], "công ty mẹ số 1 lọt vào cây của người chỉ được xem 3"


def test_mot_don_vi_duy_nhat_thi_khong_dang_hien_nut_chon(nhom):
    assert DX.co_the_thu_hep(nhom, _nguoi("nv_dh", 5)) is False
    assert DX.co_the_thu_hep(nhom, _nguoi("nv_dh", 1)) is True


# =============================================================================================
# 3. Lựa chọn không nới rộng được phạm vi
# =============================================================================================

def test_chon_don_vi_ngoai_pham_vi_bi_tu_choi_403_kem_ly_do_tieng_viet(nhom):
    kq = DX.kiem_chon(nhom, _nguoi("nv_dh", 3), DX.DON_VI, 2)
    assert kq["ok"] is False and kq["ma"] == 403
    assert "Vận tải Vietrip" in kq["ly_do"], "lý do phải gọi tên đơn vị, không phải một mã số"
    assert len(kq["ly_do"]) >= 40, "câu lỗi quá ngắn thì màn hình sẽ tự nghĩ ra một câu khác"


def test_chon_don_vi_khong_co_trong_danh_muc_la_422_chu_khong_phai_403(nhom):
    """Hai lỗi khác nhau: 'không có đơn vị ấy' và 'có nhưng anh không được xem'. Trộn làm một thì
    người dùng không biết nên đi hỏi quản trị hay đi báo nhập thiếu danh mục."""
    assert DX.kiem_chon(nhom, _nguoi("nv_dh", 1), DX.DON_VI, 99)["ma"] == 422
    assert DX.kiem_chon(nhom, _nguoi("nv_dh", 1), "cua_rieng_toi")["ma"] == 422


def test_dat_chon_truot_thi_KHONG_ghi(nhom):
    kq = DX.dat_chon(nhom, _nguoi("nv_dh", 3), DX.DON_VI, 2)
    assert kq["ok"] is False and "company_id" not in kq


def test_chua_co_kho_luu_thi_noi_thang_chua_luu_duoc(nhom):
    """Một nút bấm nói 'đã lưu' mà không lưu là thứ người dùng chỉ phát hiện ra vào hôm sau."""
    assert DX.KHO_LUU is None
    assert DX.dat_chon(nhom, _nguoi("nv_dh", 1), DX.DON_VI, 3)["luu_tru"] == "chua_co"
    assert DX.doc_chon(nhom, _nguoi("nv_dh", 1))["luu_tru"] == "chua_co"


# =============================================================================================
# 4. Lọc theo lựa chọn
# =============================================================================================

def _cau(q):
    return str(q.compile(compile_kwargs={"literal_binds": True}))


def test_chon_don_vi_thi_loc_ca_cay_con(nhom):
    from app.models.core import Tour
    q = DX.loc_dang_xem(sa.select(Tour), Tour, _nguoi("nv_dh", 1), nhom,
                        {"kieu": DX.DON_VI, "company_id": 3})
    s = _cau(q)
    assert "IN (3, 5)" in s.replace(" ,", ",")


def test_chon_ngoai_pham_vi_thi_RONG_chu_khong_am_tham_mo_rong(nhom):
    """Đột biến bỏ dòng kiểm quyền đi sẽ làm câu này trả về toàn bộ – và phép thử 'chọn đúng thì
    xem được' vẫn xanh. Đây là phép thử duy nhất bắt được nó."""
    from app.models.core import Tour
    q = DX.loc_dang_xem(sa.select(Tour), Tour, _nguoi("nv_dh", 3), nhom,
                        {"kieu": DX.DON_VI, "company_id": 2})
    s = _cau(q).lower()
    assert "false" in s
    assert " in (2" not in s, "vẫn lọc theo đơn vị bị cấm – tức là đã tin lựa chọn của trình duyệt"


def test_toan_pham_vi_giu_dong_chua_gan_dung_nhu_loc_cu(nhom):
    """Quy tắc 2 của PQ-6: không giấu. Ở kiểu mặc định, hành vi phải trùng khít loc() cũ."""
    from app.models.core import Tour
    q = DX.loc_dang_xem(sa.select(Tour), Tour, _nguoi("nv_dh", 1), nhom,
                        {"kieu": DX.TOAN_PHAM_VI})
    s = _cau(q).upper()
    assert "IS NULL" in s, "dòng chưa gán pháp nhân bị loại khỏi danh sách mặc định"


def test_chua_xac_dinh_la_muc_rieng_khong_gop_vao_cong_ty_me(nhom):
    from app.models.core import Tour
    s = _cau(DX.loc_dang_xem(sa.select(Tour), Tour, _nguoi("nv_dh", 1), nhom,
                             {"kieu": DX.CHUA_XAC_DINH})).upper()
    assert "IS NULL" in s and " IN (" not in s


def test_bang_khong_co_cot_phap_nhan_thi_khong_dong_gi(nhom):
    """Ép mọi bảng phải có pháp nhân sẽ làm hỏng danh mục dùng chung (ngân hàng, tài khoản kế toán)."""
    from app.models.core import Param
    a = _cau(sa.select(Param))
    b = _cau(DX.loc_dang_xem(sa.select(Param), Param, _nguoi("nv_dh", 3), nhom,
                             {"kieu": DX.DON_VI, "company_id": 3}))
    assert a == b


def test_cau_hien_thi_noi_ro_dang_xem_bao_nhieu_don_vi(nhom):
    m = DX.mo_ta(nhom, _nguoi("nv_dh", 1), {"kieu": DX.DON_VI, "company_id": 3})
    assert "Chi nhánh Cần Thơ" in m["cau_hien_thi"] and "1 đơn vị trực thuộc" in m["cau_hien_thi"]
    m2 = DX.mo_ta(nhom, _nguoi("nv_dh", 1), {"kieu": DX.CHUA_XAC_DINH})
    assert "CHƯA gán pháp nhân" in m2["cau_hien_thi"]


# =============================================================================================
# 5. Làm tròn tiền – chỉ đạo Chủ tịch 11/9/2026
# =============================================================================================

def test_tong_bang_tong_cac_dong_DA_lam_tron(nhom):
    """Bộ số cố ý chọn để hai cách làm tròn ra hai kết quả KHÁC nhau.

    0,6 × 3 = 1,8 → làm tròn tổng ra 2. Làm tròn từng dòng rồi cộng ra 3. Chủ tịch chốt cách thứ
    hai, vì người đọc bảng cộng mắt các dòng trên màn hình chứ không cộng số gốc.
    """
    so = [0.6, 0.6, 0.6]
    b = LT.bang_tien(so)
    assert [d["so_da_tron"] for d in b["dong"]] == [1, 1, 1]
    assert b["tong"]["so"] == 3
    assert LT.lam_tron(sum(so)) == 2, "bộ số này không còn phân biệt được hai cách – đổi bộ số khác"


def test_hien_cua_dong_tong_bang_tong_cac_hien_o_tren():
    so = [1343030.4567, 250000.5, 99999.5]
    b = LT.bang_tien(so)
    tu_man_hinh = sum(int(d["hien"].replace(".", "")) for d in b["dong"])
    assert b["tong"]["hien"] == f"{tu_man_hinh:,}".replace(",", ".")


def test_nua_dong_luon_len_tren_khong_phai_ve_so_chan():
    """round() của Python làm tròn về số chẵn: round(0.5)=0, round(1.5)=2. Trên tiền thì đó là một
    quy tắc không ai đọc hóa đơn mà đoán ra được."""
    assert LT.lam_tron(0.5) == 1 and LT.lam_tron(1.5) == 2 and LT.lam_tron(2.5) == 3
    assert LT.lam_tron(-0.5) == -1, "số âm phải đối xứng, nếu không thu và chi bằng nhau còn dư một đồng"


def test_o_rong_khong_bien_thanh_so_khong():
    """Ô chưa ai điền hiện ra '0' là nói với người đọc rằng đã đếm xong và kết quả bằng không."""
    assert LT.lam_tron(None) is None and LT.hien(None) == ""
    t = LT.cong([100.4, None, 200.6])
    assert t["so"] == 301 and t["so_dong_rong"] == 1 and t["so_dong_co_so"] == 2


def test_dau_cham_phan_cach_nghin_theo_loi_viet_nam():
    assert LT.hien(1343030.4567) == "1.343.030"
    assert LT.hien(0) == "0"


def test_chi_co_mot_ham_lam_tron_cho_ca_man_hinh_va_excel():
    """Chủ tịch chốt: màn hình và Excel dùng CHUNG một hàm, không phải hai hàm cho kết quả giống
    nhau. Hai hàm giống nhau hôm nay là hai hàm khác nhau sau lần sửa đầu tiên."""
    assert LT.HAM_DUY_NHAT == "app.services.lam_tron_tien.lam_tron"
    mo_dun, ten = LT.HAM_DUY_NHAT.rsplit(".", 1)
    import importlib
    assert getattr(importlib.import_module(mo_dun), ten) is LT.lam_tron
