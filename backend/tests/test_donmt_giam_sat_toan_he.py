# -*- coding: utf-8 -*-
"""ĐỢT DỌN-MT — `/nhan-vien-phong-toi` mở cho bốn vai nền, ở ĐÚNG MỨC NHÓM 1.

VÌ SAO CÓ ĐỢT NÀY

Main đỏ ba phép thử `test_ma_tran_quyen` sau khi Đợt CUA-1 gộp. CUA-1 khai màn
`/nhan-vien-phong-toi` đúng bằng `VAI_DUNG_DAU`, và lý do nó đưa ra là ĐÚNG: cửa
`GET /employees/phong-toi` chỉ mở cho năm vai ấy, nên một mục menu cho người khác là một mục
dẫn tới 403 — đúng món nợ `test_lg4` cấm.

Nhưng một luật khác đã ký đòi Chủ tịch · TGĐ · Ban Kiểm soát · robot Kiểm soát xem được MỌI
màn hình. HAI LUẬT ẤY CHỈ NGƯỢC NHAU KHI THIẾU MỘT CỬA — có cửa thì cả hai cùng đúng. Đây là
lần thứ hai trong hai ngày cùng một va chạm (lần trước: `/hoa-don-thieu`, Đợt R4b-2c), và cùng
một cách gỡ: cho nó một cửa, đừng bỏ vai ra khỏi menu.

CHỦ TỊCH KÝ 24/10/2026, VÀ KÝ CÓ GIỚI HẠN

Mở NHÓM 1 (mã nhân viên, họ tên, phòng, chức danh, ngày vào, thâm niên…) cho ba vai giám sát
toàn hệ, trên toàn công ty. KHÔNG mở nhóm nào khác:

  · nhóm 1b (lý do nghỉ việc chi tiết)  — vẫn chỉ Chủ tịch và HCNS
  · nhóm 2b (điện thoại cá nhân)        — vẫn chỉ Chủ tịch và HCNS
  · nhóm 3  (tài khoản và quyền)        — vẫn chỉ Chủ tịch, HCNS, CNTT
  · nhóm 4 và 5 (hồ sơ cá nhân, lương)  — vẫn chỉ Chủ tịch và HCNS

Quyết định 15/10/2026 — "nhóm 4 và 5 chỉ Chủ tịch và HCNS" — KHÔNG bị đụng tới. Phép thử
`test_donmt_3` dưới đây là chỗ giữ câu ấy: nó đi hết 17 nhóm và đòi ba vai mới KHÔNG có mặt ở
nhóm nào ngoài nhóm 1.

BA CỬA PHẢI MỞ CÙNG LÚC, VÀ ĐÓ LÀ BÀI HỌC CỦA ĐỢT NÀY

Mở ma trận trường mà quên `trong_pham_vi` thì cửa vẫn trả 403 — màn hình mở ra, bấm vào thì
lỗi, tức là vừa dựng lại đúng món nợ `test_lg4` mà đợt này đi trả. Ba chỗ: ma trận trường ·
phép tính phạm vi · hàng rào vai ở chính cửa API.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services import access as AC                                  # noqa: E402
from app.services.ho_so_nhan_vien import (NHOM_TRUONG,                 # noqa: E402
                                          VAI_DUNG_DAU,
                                          VAI_GIAM_SAT_TOAN_HE,
                                          cat_ho_so_theo_vai,
                                          quyen_nhom, trong_pham_vi)

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUONG = "/nhan-vien-phong-toi"
BA_VAI = ("tgd", "bks", "robot_ks")

# Một hồ sơ đầy đủ, cùng hình với test_hs1: đủ trường của cả bốn nhóm nhạy cảm để phép cắt có
# cái mà cắt. Thiếu một trường nào ở đây thì phép thử "không lọt" xanh vì không có gì để lọt.
HO_SO = {
    "staff_code": "NV-001", "full_name": "Nguyễn Văn A", "department": "Điều hành",
    "title": "Chuyên viên", "position": "nv", "start_date": "2024-01-02", "active": True,
    "end_kind": "tu_nguyen", "end_reason": "chuyển chỗ ở",
    "phone": "0900000000", "email": "a@vietourist.com.vn",
    "username": "nguyenvana", "role": "nv_dh",
    "id_number": "079200000001", "base_salary": 15_000_000,
}


class _Nguoi:
    def __init__(self, vai, phong="", _id=1):
        self.role, self.department, self.id = vai, phong, _id


def test_donmt_1_bon_vai_nen_xem_duoc_man_hinh():
    """Luật đã ký: Chủ tịch · TGĐ · Ban Kiểm soát · robot Kiểm soát xem được MỌI màn hình."""
    vai = AC.MENU_ROLES[DUONG]
    thieu = [r for r in AC.BASE_VIEW if r not in vai]
    assert not thieu, f"{DUONG} không mở cho {thieu}"
    # Và KHÔNG được lấy mất của năm vai đứng đầu — đợt này THÊM, không đổi chỗ.
    mat = [r for r in VAI_DUNG_DAU if r not in vai]
    assert not mat, f"{DUONG} đã đánh rơi {mat} — đợt này chỉ thêm, không thay"


def test_donmt_2_mot_nguon_cho_bon_vai_nen():
    """`VAI_GIAM_SAT_TOAN_HE` phải TRÙNG KHỚP `access.BASE_VIEW`, không phải một bản chép tay.

    Hai bảng khai cùng một danh sách thì sớm muộn lệch, và lúc lệch thì một vai xem được màn
    hình mà cửa API từ chối — đúng món nợ `test_lg4`. Không nhập thẳng `access` vào
    `ho_so_nhan_vien` được vì vòng nhập mô-đun, nên chỗ nối hai bảng là phép thử này.
    """
    assert tuple(VAI_GIAM_SAT_TOAN_HE) == tuple(AC.BASE_VIEW), (
        f"VAI_GIAM_SAT_TOAN_HE={VAI_GIAM_SAT_TOAN_HE} lệch BASE_VIEW={AC.BASE_VIEW}")


def test_donmt_3_ba_vai_moi_chi_nam_o_NHOM_1():
    """CHỖ GIỮ QUYẾT ĐỊNH 15/10/2026. Nhóm 4 và 5 vẫn chỉ Chủ tịch và HCNS.

    Đi hết 17 nhóm chứ không kiểm vài nhóm đã biết: nhóm thứ 18 thêm vào tháng sau sẽ không có
    ai rà lại, và nó sẽ lặng lẽ mở cho ba vai này nếu ai đó chép dòng `quyen` của nhóm 1.
    """
    thua = [f"nhóm {n['ma']} ({n['ten']}): {v}"
            for n in NHOM_TRUONG if n["ma"] != "1"
            for v in BA_VAI if v in n["quyen"]]
    assert not thua, ("Ba vai giám sát chỉ được mở ở NHÓM 1. Đang có thêm: "
                      + "; ".join(thua)
                      + ". Nhóm 4 và 5 là quyết định của Chủ tịch ngày 15/10/2026.")
    for v in BA_VAI:
        assert quyen_nhom("1", v) == "co", f"{v} phải thấy nhóm 1"
        for nhom in ("1b", "2b", "3", "4", "5"):
            assert quyen_nhom(nhom, v) == "khong", f"{v} KHÔNG được thấy nhóm {nhom}"


def test_donmt_4_cat_ho_so_chi_tra_ve_truong_cua_nhom_1():
    """Đo trên phép CẮT THẬT, không đọc bảng khai: bảng đúng mà phép cắt sai thì vẫn lọt."""
    nhom1 = set(next(n for n in NHOM_TRUONG if n["ma"] == "1")["truong"])
    for v in BA_VAI:
        ra = cat_ho_so_theo_vai(dict(HO_SO), v, trong_pham_vi=True)
        assert ra, f"{v} không thấy gì — cửa mở rồi mà phép cắt vẫn trả rỗng"
        lot = sorted(set(ra) - nhom1)
        assert not lot, f"{v} thấy trường ngoài nhóm 1: {lot}"
        for cam in ("phone", "id_number", "base_salary", "username", "end_reason"):
            assert cam not in ra, f"{v} thấy `{cam}` — đây là trường của nhóm đã khoá"


def test_donmt_5_pham_vi_mo_toan_he_cho_ba_vai_va_khong_doi_cua_ai():
    """Mở ma trận trường mà quên chỗ này thì cửa vẫn trả 403: màn hình mở ra, bấm vào thì lỗi."""
    muc_tieu = _Nguoi("nv_dh", "Kinh doanh", 99)
    for v in AC.BASE_VIEW:
        duoc, luat = trong_pham_vi(None, _Nguoi(v, ""), muc_tieu)
        assert duoc, f"{v} vẫn bị chặn ở trong_pham_vi — màn hình sẽ dẫn tới 403"
        assert luat == "giam_sat_toan_he", f"{v} đi nhầm nhánh luật: {luat}"
    # KHÔNG đổi luật của năm vai đứng đầu: khác phòng thì vẫn không xem được.
    duoc, luat = trong_pham_vi(None, _Nguoi("tp_dh", "Điều hành", 7), muc_tieu)
    assert not duoc, f"Trưởng phòng Điều hành xem được người phòng Kinh doanh — luật đã đổi ({luat})"
    # Và vai lạ vẫn không có gì: mặc định là TỪ CHỐI.
    duoc, _ = trong_pham_vi(None, _Nguoi("vai_vua_them_hom_nay", "Kinh doanh"), muc_tieu)
    assert not duoc


def test_donmt_6_hang_rao_vai_o_chinh_cua_API_cung_mo():
    """Chỗ thứ ba. Ba chỗ phải mở cùng lúc — xem ghi chú đầu tệp."""
    with open(os.path.join(GOC, "app", "api", "v1", "hrm.py"), encoding="utf-8") as f:
        ma = f.read()
    i = ma.index("def nhan_vien_phong_toi(")
    dau = ma[i - 200:i + 300]
    assert "_HSNV_VAI_GIAM_SAT" in dau, (
        "Cửa GET /employees/phong-toi chưa mở cho bốn vai nền — ma trận trường và phạm vi mở "
        "rồi mà hàng rào vai ở cửa còn đóng thì màn hình vẫn trả 403.")
    assert "_HSNV_VAI_QUAN_LY" in dau, "Đợt này KHÔNG được lấy cửa khỏi năm vai đứng đầu"


def test_donmt_7_man_hinh_co_cua_that_chu_khong_chi_co_menu():
    """Món nợ `test_lg4` nói ngược lại: thấy menu mà không gọi được cửa nào. Đợt này trả nó."""
    cua = AC.MAN_HINH_API.get(DUONG)
    assert cua, f"{DUONG} không khai cửa API nào trong MAN_HINH_API"
