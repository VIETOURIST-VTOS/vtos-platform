"""HS-1 — hồ sơ nhân viên: ai thấy trường nào, và bảng tài khoản xếp theo thứ tự nào.

Phép thử canh hai thứ dễ sai mà NHÌN KHÔNG RA:
  · cắt sai quyền thì màn hình vẫn vẽ đẹp, chỉ là có người đọc được thứ không phải của họ;
  · xếp sai thứ tự thì 121 dòng vẫn hiện đủ, chỉ là không ai tìm thấy ai.
Cả hai kiểu hỏng đều im lặng, nên chúng phải có phép thử chứ không trông vào mắt người.
"""
import pytest

from app.services.ho_so_nhan_vien import (
    CAP_BAC, CAP_CHUA_KHAI, NHOM_TRUONG, PHONG_TRONG, THU_TU_PHONG, VAI_DUNG_DAU,
    cap_cua_vai, cat_ho_so_theo_vai, che_gia_tri, quyen_nhom, xep_bang_tai_khoan,
)

HO_SO_DAY_DU = {
    "staff_code": "62", "full_name": "Nguyen Van A", "department": "visa",
    "title": "CV Visa 2", "start_date": "2024-01-02", "active": True,
    "end_kind": "thoi_viec", "end_reason": "ly do rieng tu",
    "email": "a@vietourist.com.vn", "phone": "0901234567",
    "username": "nguyenvana", "role": "nv_visa", "so_quyen": 9,
    "dob": "1994-03-14", "id_number": "079094001234",
    "permanent_address": "So 1 duong X phuong Y",
    "tax_code": "8123456712", "social_insurance_no": "7912345456",
    "base_salary": 18000000.0, "bhxh_base": 9000000.0, "bank_account": "19001234567841",
    "so_tour": 14, "so_booking": 63,
    "ngay_cong_ky_nay": 11, "duoc_xac_nhan_cong": True, "ly_do_nghi": "kham benh",
    "advance_limit": 5000000.0, "fuel_card_last4": "7841",
    "diem_danh_gia": 8.5, "nhat_ky": ["sua department"], "nhat_ky_gia_tri": ["x -> y"],
}

NHAY_CAM = ("id_number", "bank_account", "base_salary", "bhxh_base",
            "tax_code", "social_insurance_no", "permanent_address")


def test_hs1_1_chu_tich_thay_toan_dien():
    """Chủ tịch chốt 15/10/2026: quyền toàn diện — CO ở cả 17 nhóm, không nhóm nào che."""
    for n in NHOM_TRUONG:
        assert quyen_nhom(n["ma"], "chutich") == "co", (
            f"Nhóm {n['ma']} ({n['ten']}) không phải 'co' với Chủ tịch. "
            "Quyền của Chủ tịch là toàn diện — nếu đổi luật ấy thì sửa ở quyết định, "
            "không sửa lẻ một nhóm.")

    ra = cat_ho_so_theo_vai(HO_SO_DAY_DU, "chutich")
    assert ra == HO_SO_DAY_DU, "Chủ tịch phải nhận đúng hồ sơ đầy đủ, không thiếu không che."


def test_hs1_2_cntt_khong_doc_duoc_luong_va_cccd():
    """CNTT quản trị tài khoản, KHÔNG mặc nhiên đọc hồ sơ nhân sự (Chủ tịch 15/10/2026)."""
    ra = cat_ho_so_theo_vai(HO_SO_DAY_DU, "cntt")
    for t in NHAY_CAM:
        assert t not in ra, (
            f"CNTT đọc được '{t}'. Đây là lỗ kiểm soát sẽ bị hỏi trong kỳ soát xét: "
            "CNTT là vai kỹ thuật, không phải vai nhân sự.")
    assert ra.get("username") == "nguyenvana", "CNTT vẫn phải quản trị được tài khoản."
    assert "nhat_ky" in ra and "nhat_ky_gia_tri" not in ra, (
        "CNTT được thấy TÊN TRƯỜNG đã đổi, không được thấy giá trị trước/sau.")


def test_hs1_3_hcns_thay_nhung_la_ban_da_che():
    """HCNS thấy nhóm 4 và 5, nhưng cửa trả về bản ĐÃ CHE — giá trị thật không rời máy chủ."""
    ra = cat_ho_so_theo_vai(HO_SO_DAY_DU, "hcns")
    for t in ("id_number", "bank_account", "base_salary"):
        assert t in ra, f"HCNS phải thấy '{t}' (ở dạng che) để còn làm việc được."
        assert str(ra[t]) != str(HO_SO_DAY_DU[t]), (
            f"'{t}' trả về nguyên giá trị thật cho HCNS. Che phải làm ở MÁY CHỦ: "
            "trả thật rồi để màn hình giấu nghĩa là ai mở tab Network cũng đọc được.")


def test_hs1_4_vai_dung_dau_chi_thay_trong_pham_vi():
    """Phạm vi là một hàng rào THẬT, không phải một nhãn: ngoài phạm vi thì không có khoá."""
    trong = cat_ho_so_theo_vai(HO_SO_DAY_DU, "tp_kd", trong_pham_vi=True)
    ngoai = cat_ho_so_theo_vai(HO_SO_DAY_DU, "tp_kd", trong_pham_vi=False)

    assert trong.get("full_name") and trong.get("so_tour") == 14
    assert "username" not in trong, "Trưởng phòng không xem tài khoản và quyền (nhóm 3)."
    assert "id_number" not in trong and "base_salary" not in trong
    assert "phone" not in trong, "Điện thoại cá nhân (2b) cần quyền riêng."
    assert "ly_do_nghi" not in trong, "Lý do nghỉ liên quan sức khoẻ không mở cho vai đứng đầu."
    assert ngoai == {}, (
        "Ngoài phạm vi mà vẫn trả về trường nào là hàng rào hỏng — đổi mã nhân viên "
        "trên đường dẫn là xem được người phòng khác.")


def test_hs1_5_vai_la_khong_thay_gi():
    """Mặc định là TỪ CHỐI: thêm vai mới mà quên khai thì thấy rỗng, không phải thấy hết."""
    assert cat_ho_so_theo_vai(HO_SO_DAY_DU, "vai_vua_them_hom_nay") == {}
    assert cat_ho_so_theo_vai(HO_SO_DAY_DU, "") == {}
    assert quyen_nhom("4", "tai_xe") == "khong"


def test_hs1_6_truong_bi_cat_thi_bo_han_chu_khong_dat_none():
    """None đọc giống 'có trường này nhưng rỗng'. Không có quyền thì không có khoá."""
    ra = cat_ho_so_theo_vai(HO_SO_DAY_DU, "cntt")
    assert "base_salary" not in ra.keys(), "Phải BỎ khoá, không đặt None."


def test_hs1_7_che_khong_de_lot_gia_tri_that():
    assert che_gia_tri(18000000.0, "tien") == "•••", "Số tiền che hẳn — bốn số cuối vẫn nói ra bậc lương."
    cccd = che_gia_tri("079094001234", "ho_so")
    assert "094001" not in cccd and cccd.endswith("234") and cccd.startswith("0790")
    assert che_gia_tri("", "ho_so") == "" and che_gia_tri(None, "tien") is None, (
        "Rỗng vẫn là rỗng — che một ô trống thành '•••' là bịa ra rằng có dữ liệu.")


def test_hs1_8_moi_vai_trong_roles_deu_co_cap_bac():
    """Vai mới trong ROLES mà quên khai cấp thì bảng 121 dòng xếp sai trong im lặng.

    Mã chạy vẫn sống (CAP_CHUA_KHAI xếp cuối nhóm nhân viên) — hỏng theo chiều an toàn.
    Phép thử này là chỗ nói cho người viết biết phải khai, chứ không phải chỗ chặn chạy.
    """
    from app.models.core import ROLES
    thieu = sorted(set(ROLES) - set(CAP_BAC))
    assert not thieu, (
        f"Vai chưa khai cấp bậc: {thieu}. Thêm vào CAP_BAC trong "
        "backend/app/services/ho_so_nhan_vien.py — một chỗ duy nhất.")
    assert cap_cua_vai("vai_khong_co_that") == CAP_CHUA_KHAI
    assert CAP_CHUA_KHAI > CAP_BAC["tn_kd"], (
        "Vai chưa khai phải xếp SAU trưởng nhóm. Xếp đầu thì một vai lạ trông như lãnh đạo.")


def test_hs1_9_gom_theo_phong_dung_thu_tu_chu_tich_chot():
    rows = [
        {"department": "ketoan", "role": "ketoan", "full_name": "K"},
        {"department": "kinh_doanh", "role": "nv_kd", "full_name": "B"},
        {"department": "marketing", "role": "nv_mkt", "full_name": "M"},
        {"department": "visa", "role": "nv_visa", "full_name": "V"},
    ]
    ten = [g["phong"] for g in xep_bang_tai_khoan(rows)["nhom"]]
    assert ten == ["marketing", "kinh_doanh", "visa", "ketoan"], (
        f"Thứ tự phòng sai: {ten}. Chủ tịch chốt 15/10/2026 — Marketing TRƯỚC Kinh doanh.")
    assert THU_TU_PHONG.index("marketing") < THU_TU_PHONG.index("kinh_doanh")


def test_hs1_10_trong_phong_xep_theo_cap_roi_den_ten():
    rows = [
        {"department": "kinh_doanh", "role": "nv_kd", "full_name": "Be"},
        {"department": "kinh_doanh", "role": "gd_kd", "full_name": "Zung"},
        {"department": "kinh_doanh", "role": "nv_kd", "full_name": "An"},
        {"department": "kinh_doanh", "role": "tp_kd", "full_name": "Minh"},
    ]
    nguoi = xep_bang_tai_khoan(rows)["nhom"][0]["nguoi"]
    assert [n["full_name"] for n in nguoi] == ["Zung", "Minh", "An", "Be"], (
        "Phải xếp giám đốc → trưởng phòng → nhân viên, cùng cấp mới xếp theo tên. "
        "Xếp theo tên trước thì giám đốc tên Z nằm cuối phòng.")
    assert [n["cap_bac"] for n in nguoi] == [4, 5, 7, 7]


def test_hs1_11_phong_la_va_phong_trong_khong_bien_mat():
    rows = [
        {"department": "", "role": "bks", "full_name": "Ban Kiem soat"},
        {"department": "phong_moi_chua_khai", "role": "nv_kd", "full_name": "X"},
        {"department": "marketing", "role": "nv_mkt", "full_name": "M"},
    ]
    ra = xep_bang_tai_khoan(rows)
    ten = [g["phong"] for g in ra["nhom"]]
    assert ten == ["marketing", "phong_moi_chua_khai", PHONG_TRONG], (
        f"Sai thứ tự: {ten}. Phòng lạ xếp sau phòng đã khai, trước nhóm chưa gán phòng.")
    assert ra["phong_chua_xep"] == ["phong_moi_chua_khai"], (
        "Phòng lạ phải được KHAI RA. Gộp im lặng vào 'chưa gán phòng' thì một phòng thật "
        "biến mất khỏi chỗ nó phải đứng mà không ai thấy.")
    assert sum(g["so"] for g in ra["nhom"]) == 3, "Không được rơi mất một dòng nào."


def test_hs1_12_ba_vai_ke_toan_khong_nam_trong_bang_quyen():
    """Dựng lại phần canh mà `test_le2b::f1` mất đi khi tệp này được khai vào danh sách của nó.

    f1 ghi MỘT dòng cho mỗi cặp (tệp, vai), nên sau khi khai `ho_so_nhan_vien.py` ở đó, một lần
    MỞ QUYỀN thật cho ba vai kế toán trong chính tệp này sẽ không làm f1 đỏ nữa. Phép thử này
    canh đúng chỗ ấy, và hẹp hơn: ba vai được phép có mặt trong CAP_BAC (xếp thứ bậc) nhưng
    KHÔNG được có mặt trong bảng `quyen` của bất kỳ nhóm trường nào.

    Mở quyền đọc hồ sơ nhân sự cho Kế toán trưởng, Kế toán thanh toán hay Thủ quỹ là một quyết
    định của Chủ tịch, không phải một dòng thêm vào lúc nửa đêm. Chủ tịch 15/10/2026 đã chốt
    kế toán thanh toán nhận số tài khoản qua DANH SÁCH CHI LƯƠNG ĐÃ DUYỆT — quyền trên hồ sơ
    thanh toán, không phải quyền đọc hồ sơ nhân sự.
    """
    BA_VAI = ("ketoan_truong", "ketoan_tt", "thu_quy")
    thua = [f"nhóm {n['ma']}: {v}" for n in NHOM_TRUONG for v in BA_VAI if v in n["quyen"]]
    assert not thua, (
        "Ba vai kế toán xuất hiện trong bảng quyền của hồ sơ nhân sự: " + ", ".join(thua)
        + ". Đây là một lần MỞ QUYỀN, phải có chữ ký Chủ tịch — không phải một dòng thêm vào.")
    for v in BA_VAI:
        assert v in CAP_BAC, f"'{v}' phải vẫn có trong CAP_BAC — xếp thứ bậc là việc khác."


def test_hs1_13_moi_khoa_trong_bang_quyen_phai_la_mot_vai_co_that():
    """Hàng rào bắt đúng lỗi làn này đã mắc ngày 15/10/2026.

    Bản đầu của bảng quyền khai một khoá `"truong_phong"`. Không có vai nào tên như thế trong
    `ROLES` — các vai đứng đầu thật là `tp_dh`, `tp_kd`, `tp_hd`, `gd_kd`, `gd_doi_xe`. Dòng ấy
    KHÔNG BAO GIỜ khớp một `User.role`, nên nó không mở nhầm cho ai; nhưng nó cũng không đóng
    cho ai, và người đọc bảng sau này sẽ tin rằng trưởng phòng đã được xử lý.

    Một dòng quyền không bao giờ chạy là tệ hơn một dòng thiếu: dòng thiếu thì thấy ngay, dòng
    chết thì trông như đã xong.
    """
    from app.models.core import ROLES
    gia = sorted({v for n in NHOM_TRUONG for v in n["quyen"] if v not in ROLES})
    assert not gia, (
        f"Bảng quyền khai vai không có trong ROLES: {gia}. "
        "Vai viết sai tên thì không mở nhầm cho ai, nhưng cũng không đóng cho ai — "
        "và bảng sẽ nói dối về chính nó.")


def test_hs1_14_vai_dung_dau_la_vai_that_va_ke_toan_truong_khong_nam_trong_do():
    from app.models.core import ROLES
    thieu = [v for v in VAI_DUNG_DAU if v not in ROLES]
    assert not thieu, f"VAI_DUNG_DAU có vai không tồn tại: {thieu}"
    assert "ketoan_truong" not in VAI_DUNG_DAU, (
        "Kế toán trưởng đứng đầu phòng Kế toán, nhưng cho vai ấy mở hồ sơ nhân sự là một lần "
        "MỞ QUYỀN mới. Chủ tịch 15/10/2026 chốt nhóm 4 và 5 chỉ Chủ tịch và HCNS. "
        "Mở thì mở bằng một quyết định, không bằng một dòng suy ra.")
    # Năm phòng dưới đây KHÔNG có vai đứng đầu nào trong ROLES, nên câu hỏi "trưởng phòng thấy
    # gì" chưa đặt ra được ở đó. Phép thử ghim sự thật ấy: ngày nào có vai mới thì nó đỏ, và
    # người thêm vai sẽ phải quyết luôn phạm vi của vai đó thay vì để trống.
    for phong in ("visa", "marketing", "hcns", "cntt", "phap_che"):
        assert not [v for v in ROLES if v.startswith(("tp_", "gd_")) and phong in v], (
            f"Phòng {phong} nay đã có vai đứng đầu — phải quyết phạm vi của vai ấy, "
            "và thêm vào VAI_DUNG_DAU nếu Chủ tịch đồng ý.")
