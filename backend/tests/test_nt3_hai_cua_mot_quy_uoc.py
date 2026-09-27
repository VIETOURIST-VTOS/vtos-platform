"""NT-3 · Hai cửa ghi, MỘT quy ước ngoại tệ — Chủ tịch quyết 27/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHUYỆN NÀY ĐÃ XẢY RA, VÀ SỐ TIỀN ĐO ĐƯỢC
═══════════════════════════════════════════════════════════════════════════════════════════════
Bảng `tour_cost_lines` có HAI cửa ghi. Tới 27/9/2026 chúng hiểu ô `so_tien_goc` ngược nhau:

    settlement.py::_ngoai_te        so_tien_goc = ĐƠN GIÁ → actual = goc × tg × số lượng × hệ số
    quyet_toan_lop3.py::/{tid}/chi  so_tien_goc = TỔNG    → actual = goc × tg  (nhân biến mất)

Land 692,34 GBP × 43 khách × 36.000 — con số của tệp UK thật, chép từ chú thích trong
`models/vietrip.py`:

    cửa Điều hành : 1.071.742.320 đ
    cửa lớp 3     :    24.924.240 đ
    lệch          : 1.046.818.080 đ TRÊN MỘT DÒNG

Chủ tịch chốt: số tiền gốc là ĐƠN GIÁ MỘT ĐƠN VỊ. Quy đổi TRƯỚC, nhân SAU.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CỬA HỎNG, KHÔNG PHẢI MỘT
═══════════════════════════════════════════════════════════════════════════════════════════════
`/chi`, `/phuong-tien`, `/hdv-chi` mất số lượng. `/doanh-thu` nặng hơn cả: nó ghi đè `thành tiền`
nhưng để `thành tiền trước thuế` và `tiền thuế` nguyên ở ĐỒNG GỐC — ba cột của một dòng ở hai
loại tiền, và `tiền thuế` là cột đi vào tờ khai thuế GTGT.

`/khach-chi-phi` KHÔNG hỏng: cửa ấy không có phép nhân nào, một khách một khoản, nên hai cách
hiểu trùng nhau. Vẫn có phép thử, để lần sửa sau không kéo nó lệch theo.
"""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import quyet_toan_lop3 as L3
from app.main import app
from app.services.settlement import calc_actual, validate

client = TestClient(app)

GBP, PAX, TY_GIA = 692.34, 43, 36000.0
HOM_NAY = dt.date.today().isoformat()


# ═══════════════ 1. HAI CỬA PHẢI RA CÙNG MỘT SỐ ═══════════════

def test_nt3_hai_cua_ra_CUNG_MOT_SO_tren_cung_mot_dong():
    """Phép thử quan trọng nhất của tệp. Hai cửa ghi chung một bảng thì phải cùng một phép tính."""
    dg = L3.don_gia_vnd("GBP", GBP, TY_GIA, HOM_NAY, None)
    lop3 = round(dg * PAX * 1, 2)

    v = validate({"description": "Land", "supplier_name": "NCC UK", "cost_kind": "theo_khach",
                  "tien_te": "GBP", "so_tien_goc": GBP, "ty_gia": TY_GIA, "ngay_ty_gia": HOM_NAY,
                  "qty": PAX, "coef": 1})

    assert lop3 == v["actual"] == 1_071_742_320
    assert dg == v["unit_price"] == 24_924_240, "unit_price phải cùng một nghĩa ở hai cửa"


def test_nt3_don_gia_vnd_tra_ve_MOT_DON_VI_khong_phai_ca_dong():
    """Đây là chỗ đổi nghĩa. Trả về cả dòng là quay lại đúng lỗi cũ."""
    assert L3.don_gia_vnd("GBP", GBP, TY_GIA, HOM_NAY, None) == round(GBP * TY_GIA, 2)


def test_nt3_khoan_VND_tra_lai_dung_don_gia_da_go():
    assert L3.don_gia_vnd("", None, None, None, 1500.0) == 1500.0
    assert L3.don_gia_vnd("VND", None, None, None, 1500.0) == 1500.0


def test_nt3_ten_ham_da_DOI_de_cho_quen_thanh_loi_ngay():
    """Giữ tên cũ thì một nơi gọi bị quên sẽ lặng lẽ chạy tiếp với nghĩa cũ — và nghĩa cũ là chỗ
    lệch hơn một tỷ đồng. Đổi tên thì chỗ quên là một lỗi ngay lúc nạp mã."""
    assert not hasattr(L3, "quy_doi"), "tên cũ còn sống — một nơi gọi bị quên sẽ không ai thấy"
    assert callable(L3.don_gia_vnd)


# ═══════════════ 2. BA PHÉP KIỂM NGOẠI TỆ KHÔNG ĐƯỢC MẤT ═══════════════

@pytest.mark.parametrize("thieu,tim", [
    ({"ty_gia": None}, "tỷ giá"),
    ({"ngay_ty_gia": None}, "tỷ giá"),
    ({"so_tien_goc": None}, "đồng tiền gốc"),
])
def test_nt3_khai_ngoai_te_thieu_o_thi_van_CHAN(thieu, tim):
    d = {"tien_te": "GBP", "so_tien_goc": GBP, "ty_gia": TY_GIA, "ngay_ty_gia": HOM_NAY}
    d.update(thieu)
    with pytest.raises(Exception) as e:
        L3.don_gia_vnd(d["tien_te"], d["so_tien_goc"], d["ty_gia"], d["ngay_ty_gia"], None)
    assert tim in str(getattr(e.value, "detail", e.value))


# ═══════════════ 3. NĂM NƠI GỌI ĐỀU QUY ĐỔI TRƯỚC, NHÂN SAU ═══════════════

def _than(ten_ham: str) -> str:
    import inspect
    import re
    s = inspect.getsource(L3)
    i = s.find(f"def {ten_ham}(")
    assert i >= 0, ten_ham
    j = s.find("\n@router", i)
    than = s[i: j if j > 0 else len(s)]
    than = re.sub(r'"""(?:.|\n)*?"""', " ", than)
    return "\n".join(l for l in than.split("\n") if not l.strip().startswith("#"))


@pytest.mark.parametrize("ham", ["them_doanh_thu", "them_dong_chi", "them_phuong_tien",
                                 "them_hdv_chi"])
def test_nt3_moi_cua_quy_doi_DON_GIA_roi_moi_nhan(ham):
    """Hàng rào đọc MÃ, vì đây là lỗi về THỨ TỰ hai dòng — chạy thử một ca không bắt được mọi ca.

    Hình sai: tính tích rồi GHI ĐÈ bằng số đã quy đổi. Hình đúng: quy đổi đơn giá vào một biến,
    rồi nhân biến ấy.
    """
    than = _than(ham)
    assert "don_gia_vnd(" in than, f"{ham} không quy đổi ngoại tệ nữa"
    i_qd = than.find("don_gia_vnd(")
    i_nhan = max(than.rfind("* v.so_luong"), than.rfind("_thanh_tien(dg"))
    assert i_nhan > i_qd, f"{ham}: còn nhân TRƯỚC khi quy đổi — số lượng sẽ bị ghi đè"
    assert "dg" in than, f"{ham}: không giữ đơn giá đã quy đổi vào biến riêng"


def test_nt3_khach_chi_phi_khong_co_phep_nhan_nen_khong_doi():
    """Cửa này một khách một khoản. Không có gì để mất, và cũng không được tự thêm phép nhân."""
    than = _than("them_khach_chi_phi")
    assert "don_gia_vnd(" in than
    assert "* v.so_luong" not in than


# ═══════════════ 4. cost_kind PHẢI KHỚP PHÉP NHÂN CỬA THẬT SỰ LÀM ═══════════════

def test_nt3_cua_chi_KHAI_cost_kind_thay_vi_de_roi_ve_mac_dinh():
    """Lỗi bắt được 27/9/2026, trong chính bộ soát ngoại tệ.

    Cửa `/chi` nhân `đơn giá × số lượng × hệ số` nhưng KHÔNG đặt `cost_kind`, nên dòng nó ghi
    mang mặc định `"co_dinh"` — cột nói *"đừng nhân với số khách"* trong khi cửa vừa nhân. Mọi bộ
    đọc sau này dựng lại sai phép nhân của dòng, kể cả bộ soát sinh ra để bắt đúng chuyện ấy.
    """
    than = _than("them_dong_chi")
    assert "cost_kind=" in than, "cửa /chi vẫn để cost_kind rơi về mặc định của cột"
    assert "theo_khach" in than


def test_nt3_cost_kind_da_khai_thi_calc_actual_dung_lai_duoc_so():
    """Khai đúng `cost_kind` thì phép nhân của cửa lớp 3 và `calc_actual` cho ra cùng một số —
    đó mới là ý nghĩa của việc khai nó."""
    dg = L3.don_gia_vnd("GBP", GBP, TY_GIA, HOM_NAY, None)
    assert round(dg * PAX * 1, 2) == calc_actual("theo_khach", dg, PAX, 1)


# ═══════════════ 5. /doanh-thu: BA CỘT MỘT LOẠI TIỀN ═══════════════

def test_nt3_doanh_thu_ba_cot_cung_MOT_loai_tien():
    """Bản cũ ghi đè `thành tiền` nhưng để `trước thuế` và `tiền thuế` ở đồng gốc. `tiền thuế` là
    cột đi vào tờ khai GTGT — một dòng hai loại tiền ở đó là một tờ khai sai."""
    dg = L3.don_gia_vnd("GBP", GBP, TY_GIA, HOM_NAY, None)
    truoc, thue, tong = L3._thanh_tien(dg, PAX, 0.08)
    assert truoc == round(dg * PAX, 2)
    assert thue == round(truoc * 0.08, 2)
    assert tong == round(truoc + thue, 2)
    # Cả ba đều là VND: tiền thuế phải cùng bậc độ lớn với thành tiền, không phải bậc đồng gốc.
    assert thue > GBP * PAX, "tiền thuế đang ở đồng gốc trong khi thành tiền đã là VND"


def test_nt3_doanh_thu_luu_don_gia_bang_VND():
    than = _than("them_doanh_thu")
    assert "don_gia_truoc_thue=dg" in than, "cột đơn giá còn lưu đồng gốc, lệch với settlement"
