"""Hồ sơ nhân viên — AI THẤY TRƯỜNG NÀO, và thứ tự của bảng tài khoản.

Chủ tịch chốt 15/10/2026. Hai việc tách bạch nằm chung một tệp vì chúng dùng chung
một bảng cấp bậc:

  1. XẾP BẢNG TÀI KHOẢN — gom theo phòng, trong phòng xếp theo cấp bậc từ cao xuống.
  2. CẮT HỒ SƠ THEO VAI — trường nào vai nào được thấy, và trường nào trả về bản đã che.

VÌ SAO CHE LÀ VIỆC CỦA MÁY CHỦ, không phải của màn hình. Nếu cửa trả về giá trị thật
rồi màn hình tự giấu đi, thì giá trị thật ĐÃ RỜI máy chủ: nó nằm trong phản hồi mạng,
trong bộ nhớ trình duyệt, trong công cụ dành cho người phát triển. Người không đủ quyền
mở tab Network là đọc được. Che ở đây nghĩa là giá trị thật KHÔNG BAO GIỜ đi ra.

MẶC ĐỊNH LÀ TỪ CHỐI. Vai không có tên trong bảng thì không thấy gì — thêm một vai mới
vào ROLES mà quên khai ở đây thì người ấy thấy một hồ sơ rỗng, chứ không phải thấy hết.
Hỏng theo chiều an toàn.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- cấp bậc
#
# ROLES trong models/core.py là một danh sách phẳng, KHÔNG mang thứ bậc nào. Bảng dưới
# đây là thứ phải dựng mới. Chủ tịch duyệt 15/10/2026.
#
# Hai chỗ đã nêu rõ với Chủ tịch khi duyệt, ghi lại để lần sau khỏi tra lại:
#   · ketoan_truong đặt cấp 4 (ngang giám đốc), không phải cấp 5 ngang trưởng phòng.
#   · cntt / hcns / ir_phapche đặt cấp 7 cùng chuyên viên. Nếu các vai ấy là trưởng
#     bộ phận thật thì sửa thành 5 — sửa ở ĐÚNG MỘT chỗ này, không rải ra nơi khác.
CAP_BAC: dict[str, int] = {
    "chutich": 1,
    "tgd": 2,
    "ptgd_doan": 3, "ptgd_mkt": 3,
    "gd_kd": 4, "gd_doi_xe": 4, "ketoan_truong": 4,
    "tp_dh": 5, "tp_kd": 5, "tp_hd": 5,
    "tn_kd": 6,
    "nv_dh": 7, "nv_kd": 7, "nv_mkt": 7, "nv_visa": 7, "sales_admin": 7,
    "ketoan": 7, "ketoan_tt": 7, "thu_quy": 7, "hcns": 7, "hanh_chinh": 7,
    "cntt": 7, "ir_phapche": 7, "tai_xe": 7, "hdv": 7,
    "bks": 8,
    "robot_pq": 9, "robot_ks": 9, "robot_vpm": 9,
}

# Vai chưa khai cấp xếp CUỐI nhóm nhân viên, không xếp đầu. Một vai mới xuất hiện ở
# đầu danh sách trông y hệt một vai lãnh đạo, và không ai nghi ngờ thứ tự.
CAP_CHUA_KHAI = 7.5

def cap_cua_vai(vai: str) -> float:
    return CAP_BAC.get((vai or "").strip(), CAP_CHUA_KHAI)

# --------------------------------------------------------------------------- phòng
#
# Thứ tự theo sơ đồ tổ chức, Chủ tịch chốt 15/10/2026 — KHÔNG theo bảng chữ cái.
# Marketing đứng trước Kinh doanh: đúng chiều việc chạy, có nguồn khách rồi mới bán.
THU_TU_PHONG: list[str] = [
    "ban_lanh_dao", "marketing", "kinh_doanh", "dieu_hanh", "visa",
    "huong_dan", "doi_xe", "ketoan", "hcns", "cntt", "phap_che", "bks", "robot",
]

# Phòng có mặt trong cơ sở dữ liệu mà KHÔNG có trong danh sách trên thì xếp sau mọi
# phòng đã khai, theo bảng chữ cái, và trước nhóm chưa gán phòng.
#
# CỐ Ý KHÔNG NÉM LỖI, và cũng cố ý không im lặng gộp chúng vào "chưa gán phòng":
# ném lỗi thì một chữ viết hoa lệch trong ô `department` làm đỏ cả màn hình 121 dòng;
# gộp im lặng thì một phòng thật biến mất khỏi chỗ nó phải đứng mà không ai thấy.
# Hàm xếp trả kèm `phong_chua_xep` để màn hình nói ra.
PHONG_TRONG = "(chưa gán phòng)"

def _khoa_phong(ma_phong: str) -> tuple[int, str]:
    p = (ma_phong or "").strip().lower()
    if not p:
        return (len(THU_TU_PHONG) + 1, "")        # chưa gán phòng — xếp cuối cùng
    if p in THU_TU_PHONG:
        return (THU_TU_PHONG.index(p), p)
    return (len(THU_TU_PHONG), p)                 # phòng lạ — sau phòng đã khai

def xep_bang_tai_khoan(rows: list[dict]) -> dict:
    """Gom theo phòng rồi xếp trong phòng theo cấp bậc; cùng cấp thì theo họ tên.

    `rows` là các từ điển có ít nhất `department`, `role`, `full_name`.
    Trả về {"nhom": [{"phong", "so", "nguoi": [...]}], "phong_chua_xep": [...]}.
    """
    nhom: dict[str, list[dict]] = {}
    for r in rows:
        nhom.setdefault((r.get("department") or "").strip().lower(), []).append(r)

    chua_xep = sorted(p for p in nhom if p and p not in THU_TU_PHONG)

    ra = []
    for p in sorted(nhom, key=_khoa_phong):
        nguoi = sorted(
            nhom[p],
            key=lambda r: (cap_cua_vai(r.get("role", "")), (r.get("full_name") or "").lower()),
        )
        for r in nguoi:
            r["cap_bac"] = cap_cua_vai(r.get("role", ""))
        ra.append({"phong": p or PHONG_TRONG, "so": len(nguoi), "nguoi": nguoi})
    return {"nhom": ra, "phong_chua_xep": chua_xep}

# --------------------------------------------------------------------------- quyền
#
# Năm giá trị, và chúng KHÔNG thay thế được cho nhau:
#   co        thấy giá trị thật
#   che       thấy bản đã che; muốn thấy thật phải gọi cửa hiện-trường, cửa ấy ghi nhật ký
#   khong     cửa không trả trường ấy về — không phải trả rỗng, là không có khoá
#   pham_vi   như `co`, nhưng chỉ với nhân viên thuộc phạm vi quản lý của người gọi
#   cap_rieng phải có một quyền cấp riêng; chưa có hệ cấp quyền cho nó thì coi như `khong`
CO, CHE, KHONG, PHAM_VI, CAP_RIENG = "co", "che", "khong", "pham_vi", "cap_rieng"

HCNS_VA_TREN = ("chutich", "hcns")
QUAN_TRI_TK = ("chutich", "hcns", "cntt")

# VAI ĐỨNG ĐẦU MỘT BỘ PHẬN — đo từ `ROLES` ngày 15/10/2026, và KHÔNG có vai nào tên là
# `truong_phong`. Bản đầu của tệp này khai một khoá mang tên ấy; nó không bao giờ khớp một
# `User.role` thật. Luật mặc-định-từ-chối làm nó vô hại, nhưng một dòng trong bảng quyền mà
# không bao giờ chạy là một dòng NÓI SAI về chính hệ thống, và người đọc sau sẽ tin nó.
#
# NĂM PHÒNG KHÔNG CÓ VAI ĐỨNG ĐẦU: Visa, Marketing, HCNS, CNTT, Pháp chế. Với các phòng ấy
# câu hỏi "trưởng phòng thấy gì" chưa đặt ra được — không có ai mang vai ấy để mà hỏi.
#
# `ketoan_truong` CỐ Ý KHÔNG nằm ở đây. Kế toán trưởng đứng đầu phòng Kế toán, nhưng cho vai
# ấy mở hồ sơ nhân sự là một lần MỞ QUYỀN mới — Chủ tịch 15/10/2026 chốt nhóm 4 và 5 chỉ Chủ
# tịch và HCNS. Muốn mở thì mở bằng một quyết định, không bằng một dòng suy ra.
VAI_DUNG_DAU = ("tp_dh", "tp_kd", "tp_hd", "gd_kd", "gd_doi_xe")

# 17 nhóm. Chủ tịch `co` ở CẢ 17 — "quyền của Chủ tịch là toàn diện" (15/10/2026).
NHOM_TRUONG: list[dict] = [
    {"ma": "1",  "ten": "Nhận dạng công việc",
     "truong": ["staff_code", "full_name", "department", "title", "position",
                "sales_group", "office", "company_id", "contract_type",
                "start_date", "tham_nien", "active", "ended_on"],
     "quyen": {"chutich": CO, "hcns": CO, "cntt": CO, **{v: PHAM_VI for v in VAI_DUNG_DAU}}},
    {"ma": "1b", "ten": "Lý do nghỉ việc chi tiết", "che_kieu": None,
     "truong": ["end_kind", "end_reason"],
     "quyen": {"chutich": CO, "hcns": CO}},
    {"ma": "2",  "ten": "Liên hệ công việc",
     "truong": ["email", "zalo_noi"],
     "quyen": {"chutich": CO, "hcns": CO, "cntt": CO, **{v: PHAM_VI for v in VAI_DUNG_DAU}}},
    {"ma": "2b", "ten": "Điện thoại cá nhân", "che_kieu": "dien_thoai",
     "truong": ["phone"],
     "quyen": {"chutich": CO, "hcns": CO}},
    {"ma": "3",  "ten": "Tài khoản và quyền",
     "truong": ["username", "role", "last_login_at", "must_change_password",
                "ngoai_bien_che", "so_quyen"],
     "quyen": {"chutich": CO, "hcns": CO, "cntt": CO}},
    {"ma": "4",  "ten": "Hồ sơ cá nhân", "che_kieu": "ho_so",
     "truong": ["dob", "gender", "id_number", "id_issued_on", "id_issued_by",
                "permanent_address", "current_address", "tax_code",
                "social_insurance_no"],
     "quyen": {"chutich": CO, "hcns": CHE}},
    {"ma": "5",  "ten": "Hợp đồng và lương", "che_kieu": "tien",
     "truong": ["contract_type_hd", "contract_end", "base_salary", "bhxh_base",
                "probation", "so_nguoi_phu_thuoc", "bank_account"],
     "quyen": {"chutich": CO, "hcns": CHE}},
    {"ma": "6",  "ten": "Việc đang gánh",
     "truong": ["so_tour", "so_booking", "so_lenh_xe", "so_visa", "so_phan_cong_kd"],
     "quyen": {"chutich": CO, "hcns": CO, "cntt": CO, **{v: PHAM_VI for v in VAI_DUNG_DAU}}},
    {"ma": "7a", "ten": "Xem ngày công",
     "truong": ["ngay_cong_ky_nay"],
     "quyen": {"chutich": CO, "hcns": CO, **{v: PHAM_VI for v in VAI_DUNG_DAU}}},
    {"ma": "7b", "ten": "Xác nhận công",
     "truong": ["duoc_xac_nhan_cong"],
     "quyen": {"chutich": CO, "hcns": CO, **{v: CAP_RIENG for v in VAI_DUNG_DAU}}},
    {"ma": "7c", "ten": "Duyệt đơn nghỉ",
     "truong": ["duoc_duyet_nghi", "so_don_cho_duyet"],
     "quyen": {"chutich": CO, "hcns": CO, **{v: CAP_RIENG for v in VAI_DUNG_DAU}}},
    {"ma": "7d", "ten": "Lý do nghỉ liên quan sức khoẻ", "che_kieu": None,
     "truong": ["ly_do_nghi"],
     "quyen": {"chutich": CO, "hcns": CO}},
    {"ma": "8a", "ten": "Vận hành theo vai",
     "truong": ["card_no", "card_type", "card_expiry", "xe_dang_gan"],
     "quyen": {"chutich": CO, "hcns": CO, "cntt": CO, **{v: PHAM_VI for v in VAI_DUNG_DAU}}},
    {"ma": "8b", "ten": "Tạm ứng, thẻ nhiên liệu, hợp đồng CTV, chi tiết sự cố",
     "che_kieu": "tien",
     "truong": ["advance_limit", "fuel_card_last4", "ctv_contract", "su_co"],
     "quyen": {"chutich": CO, "hcns": CO}},
    {"ma": "9",  "ten": "Đánh giá và tài sản",
     "truong": ["danh_gia_gan_nhat", "diem_danh_gia", "tai_san_da_cap"],
     "quyen": {"chutich": CO, "hcns": CO}},
    {"ma": "10", "ten": "Nhật ký hồ sơ — tên trường đã đổi",
     "truong": ["nhat_ky"],
     "quyen": {"chutich": CO, "hcns": CO, "cntt": CO}},
    {"ma": "10b", "ten": "Giá trị trước/sau của trường nhạy cảm",
     "truong": ["nhat_ky_gia_tri"],
     "quyen": {"chutich": CO, "hcns": CO}},
]

NHOM_THEO_MA = {n["ma"]: n for n in NHOM_TRUONG}

def quyen_nhom(ma_nhom: str, vai: str, trong_pham_vi: bool = False,
               cap_rieng: frozenset[str] = frozenset()) -> str:
    """Trả về CO / CHE / KHONG cho một nhóm với một vai. PHAM_VI và CAP_RIENG đã giải."""
    n = NHOM_THEO_MA.get(ma_nhom)
    if n is None:
        return KHONG
    q = n["quyen"].get((vai or "").strip(), KHONG)     # mặc định là từ chối
    if q == PHAM_VI:
        return CO if trong_pham_vi else KHONG
    if q == CAP_RIENG:
        return CO if (trong_pham_vi and ma_nhom in cap_rieng) else KHONG
    return q

# --------------------------------------------------------------------------- che
#
# Che giữ lại ĐỦ để người có quyền đối chiếu, và không đủ để ai chép lại.
# Số tiền che hẳn: bốn số cuối của một khoản lương vẫn nói ra bậc lương.
def che_gia_tri(gia_tri, kieu: str | None):
    if gia_tri in (None, ""):
        return gia_tri
    if kieu == "tien":
        return "•••"
    s = str(gia_tri)
    if kieu == "dien_thoai":
        return ("•" * max(0, len(s) - 3)) + s[-3:] if len(s) > 3 else "•••"
    if len(s) <= 7:
        return "•" * len(s)
    return s[:4] + "•" * (len(s) - 7) + s[-3:]

def cat_ho_so_theo_vai(ho_so: dict, vai: str, trong_pham_vi: bool = False,
                       cap_rieng: frozenset[str] = frozenset()) -> dict:
    """Cắt hồ sơ đầy đủ xuống đúng phần một vai được thấy.

    Trường thuộc nhóm KHONG bị BỎ HẲN khỏi từ điển trả về — không đặt None, vì None
    đọc giống "có trường này nhưng rỗng", và màn hình sẽ in ô trống thay vì không in gì.
    """
    ra: dict = {}
    for n in NHOM_TRUONG:
        q = quyen_nhom(n["ma"], vai, trong_pham_vi, cap_rieng)
        if q == KHONG:
            continue
        for t in n["truong"]:
            if t not in ho_so:
                continue
            ra[t] = ho_so[t] if q == CO else che_gia_tri(ho_so[t], n.get("che_kieu"))
    return ra
