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
     # Hai khoá đầu là thứ MÁY ĐẾM ĐƯỢC HÔM NAY, đọc từ siêu dữ liệu SQLAlchemy nên cột khoá
     # ngoại ai thêm tuần sau cũng tự vào. Năm khoá sau là năm con số Chủ tịch muốn thấy tách
     # ra theo loại việc; chưa có nguồn nào sinh ra chúng, nên cửa đọc KHÔNG trả về và NÓI RA
     # trong `thieu_nguon`. Một khoá khai mà không bao giờ có giá trị là một lời nói sai về hệ
     # thống — bài học `truong_phong`, 15/10/2026 — nên nó phải tự tố cáo ở mỗi lần gọi.
     "truong": ["so_dong_tro_toi", "viec_dang_ganh",
                "so_tour", "so_booking", "so_lenh_xe", "so_visa", "so_phan_cong_kd"],
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


# =============================================================================================
# HS-2 · ĐỌC HỒ SƠ TỪ CƠ SỞ DỮ LIỆU
#
# Phần trên thuần phép tính: đưa vào một từ điển, trả ra từ điển đã cắt. Phần dưới đi hỏi cơ sở
# dữ liệu. Tách hai phần ở một đường kẻ rõ vì phần trên là chỗ phép thử canh được không cần máy
# chủ, và một phép thử chạy được trong 0,01 giây là phép thử người ta chịu chạy.
#
# BA ĐIỀU PHẦN NÀY PHẢI GIỮ:
#   1. Trường nào KHÔNG CÓ NGUỒN thì không đặt khoá, và tên nó đi vào `thieu_nguon`. Trả rỗng
#      là nói "người này không có số liệu"; nói thiếu nguồn là nói "hệ thống chưa có cửa nhập".
#      Hai câu khác hẳn nhau, và chỉ câu thứ hai dẫn tới một việc phải làm.
#   2. Giá trị thật của nhóm CHE KHÔNG BAO GIỜ rời khỏi hàm này — `cat_ho_so_theo_vai` che
#      trước khi trả, cửa HTTP không cầm bản chưa che một lúc nào.
#   3. Phạm vi quản lý giải ở MÁY CHỦ. Hai luật, và luật yếu phải nói ra là nó yếu.
# =============================================================================================

# Nhóm chạm vào đời tư hoặc tiền. Mỗi lần ĐỌC THẬT một nhóm ở đây đều để lại vết, kể cả khi
# người đọc là Chủ tịch. Quyền và vết là hai thứ khác nhau: vết không giới hạn quyền của ai, nó
# bảo vệ chính người có quyền — hồ sơ nhân sự rò ra ngoài thì nhật ký cho thấy ai đã mở.
NHOM_NHAY_CAM = ("1b", "2b", "4", "5", "7d", "8b", "9", "10b")

# HAI LUẬT PHẠM VI, và chúng KHÔNG mạnh ngang nhau.
#
#   · THEO CÂY: Kinh doanh có sơ đồ tổ chức thật (`don_vi_kd` + `phan_cong_kd`), có ngày hiệu
#     lực, có cha con. Hỏi "người này có thuộc nhánh của tôi vào hôm nay không" là một câu trả
#     lời được chính xác.
#   · THEO PHÒNG: Điều hành, Hướng dẫn, Đội xe KHÔNG có cây nào. Chỗ duy nhất nói hai người
#     cùng một phòng là chuỗi chữ `User.department`. Nó không có ngày hiệu lực (đổi phòng hôm
#     nay thì lịch sử tự viết lại), không có cấp trên cấp dưới, và một chữ viết hoa lệch là hai
#     người khác phòng. ĐÂY LÀ LUẬT YẾU HƠN, và cửa đọc trả về tên luật đã dùng để người đọc
#     biết mình đang dựa vào cái gì. Giấu chỗ yếu đi thì ngày nó hỏng không ai ngờ tới.
PHAM_VI_THEO_CAY = ("gd_kd", "tp_kd")
PHAM_VI_THEO_PHONG = ("tp_dh", "tp_hd", "gd_doi_xe")


def trong_pham_vi(db, nguoi_xem, muc_tieu, ngay=None) -> tuple[bool, str]:
    """Người xem có quản lý mục tiêu không. Trả (có/không, TÊN LUẬT đã dùng)."""
    vai = (getattr(nguoi_xem, "role", "") or "").strip()
    if vai not in VAI_DUNG_DAU:
        return False, "khong_phai_vai_dung_dau"
    if nguoi_xem.id == muc_tieu.id:
        return True, "chinh_minh"

    if vai in PHAM_VI_THEO_CAY:
        from app.services import to_chuc_kd as TCKD
        for mang in ("le", "doan"):
            ds = TCKD.pham_vi_xem(db, nguoi_xem, ngay, mang)
            if ds is None:                      # RỖNG KHÁC None — xem chú thích ở pham_vi_xem
                return True, f"cay_{mang}_toan_bo"
            if ds and any(x["user_id"] == muc_tieu.id
                          for x in TCKD.nguoi_trong(db, ds, ngay)):
                return True, f"cay_{mang}"
        return False, "ngoai_cay"

    p_xem = (getattr(nguoi_xem, "department", "") or "").strip().lower()
    p_dich = (getattr(muc_tieu, "department", "") or "").strip().lower()
    if p_xem and p_xem == p_dich:
        return True, "cung_phong_luat_yeu"
    return False, "khac_phong"


def thu_thap(db, t) -> tuple[dict, list[str]]:
    """Gom hồ sơ ĐẦY ĐỦ của một tài khoản. Chưa cắt, chưa che — hàm gọi phải cắt ngay sau đó.

    Trả (ho_so, thieu_nguon). `thieu_nguon` là tên những trường đã khai trong NHOM_TRUONG mà
    hôm nay chưa có bảng nào sinh ra — danh sách việc còn thiếu, không phải lỗi.
    """
    from datetime import date
    from sqlalchemy import func, select
    from app.models.core import AuditLog
    from app.models.hr import Employee
    from app.models.hrm import (AttendanceDay, Dependent, EmployeeProfile, LaborContract,
                                LeaveRequest)
    from app.models.nhan_su_danh_gia import CapPhatTaiSan, DanhGiaNhanSu
    from app.models.su_co_tour import SuCoTour
    from app.models.zalo_noi import ZaloNoiTaiKhoan
    from app.services import sua_xoa_tai_khoan as SX

    hs: dict = {}
    # ---- nhóm 3: tài khoản (luôn có, vì chính tài khoản là điểm xuất phát)
    hs["username"] = t.username
    hs["role"] = t.role
    hs["last_login_at"] = t.last_login.isoformat() if t.last_login else None
    hs["must_change_password"] = bool(t.must_change_password)
    hs["ngoai_bien_che"] = bool(t.ngoai_bien_che)
    hs["active"] = bool(t.active)
    hs["full_name"] = t.full_name
    hs["staff_code"] = t.staff_code or ""
    hs["department"] = t.department or ""
    hs["sales_group"] = t.sales_group or ""
    hs["company_id"] = t.company_id

    e = db.execute(select(Employee).where(Employee.user_id == t.id)).scalars().first()
    if e is None and (t.staff_code or "").strip():
        e = db.execute(select(Employee).where(Employee.code == t.staff_code.strip())).scalars().first()

    if e is not None:
        hs["title"] = e.title or ""
        hs["position"] = e.position or ""
        hs["office"] = e.office or ""
        hs["contract_type"] = e.contract_type or ""
        hs["start_date"] = e.start_date.isoformat() if e.start_date else None
        if e.start_date:
            n = (date.today() - e.start_date).days
            hs["tham_nien"] = f"{n // 365} năm {(n % 365) // 30} tháng"
        hs["ended_on"] = e.ended_on.isoformat() if e.ended_on else None
        hs["end_kind"] = e.end_kind or ""
        hs["end_reason"] = e.end_reason or ""
        hs["phone"] = e.phone or ""
        hs["probation"] = bool(e.probation)
        hs["bhxh_base"] = e.bhxh_base
        hs["base_salary"] = e.base_salary
        hs["card_no"] = e.card_no or ""
        hs["card_type"] = e.card_type or ""
        hs["card_expiry"] = e.card_expiry.isoformat() if e.card_expiry else None
        hs["ctv_contract"] = bool(e.ctv_contract)
        hs["advance_limit"] = e.advance_limit
        hs["fuel_card_last4"] = e.fuel_card_last4 or ""

        pf = db.execute(select(EmployeeProfile)
                        .where(EmployeeProfile.employee_id == e.id)).scalars().first()
        if pf is not None:
            hs["dob"] = pf.dob.isoformat() if pf.dob else None
            hs["gender"] = pf.gender or ""
            hs["id_number"] = pf.id_number or ""
            hs["id_issued_on"] = pf.id_issued_on.isoformat() if pf.id_issued_on else None
            hs["id_issued_by"] = pf.id_issued_by or ""
            hs["permanent_address"] = pf.permanent_address or ""
            hs["current_address"] = pf.current_address or ""
            hs["tax_code"] = pf.tax_code or ""
            hs["social_insurance_no"] = pf.social_insurance_no or ""
            hs["bank_account"] = pf.bank_account or ""
            if pf.email:
                hs["email"] = pf.email
            if pf.phone:
                hs["phone"] = pf.phone

        hd = db.execute(select(LaborContract)
                        .where(LaborContract.employee_id == e.id)
                        .order_by(LaborContract.effective_from.desc())).scalars().first()
        if hd is not None:
            hs["contract_type_hd"] = hd.kind or ""
            hs["contract_end"] = hd.effective_to.isoformat() if hd.effective_to else None

        hs["so_nguoi_phu_thuoc"] = db.execute(
            select(func.count()).select_from(Dependent)
            .where(Dependent.employee_id == e.id, Dependent.active == True)).scalar_one()  # noqa: E712

        dau_thang = date.today().replace(day=1)
        hs["ngay_cong_ky_nay"] = db.execute(
            select(func.coalesce(func.sum(AttendanceDay.work), 0))
            .where(AttendanceDay.employee_id == e.id,
                   AttendanceDay.day >= dau_thang)).scalar_one()
        hs["so_don_cho_duyet"] = db.execute(
            select(func.count()).select_from(LeaveRequest)
            .where(LeaveRequest.employee_id == e.id,
                   LeaveRequest.status == "cho_duyet")).scalar_one()

        dg = db.execute(select(DanhGiaNhanSu)
                        .where(DanhGiaNhanSu.employee_id == e.id)
                        .order_by(DanhGiaNhanSu.ky.desc())).scalars().first()
        if dg is not None:
            hs["danh_gia_gan_nhat"] = f"{dg.ky_loai} {dg.ky}"
            hs["diem_danh_gia"] = dg.diem_tong
        hs["tai_san_da_cap"] = db.execute(
            select(func.count()).select_from(CapPhatTaiSan)
            .where(CapPhatTaiSan.employee_id == e.id,
                   CapPhatTaiSan.trang_thai == "dang_giu")).scalar_one()
        hs["su_co"] = db.execute(
            select(func.count()).select_from(SuCoTour)
            .where(SuCoTour.nguoi_bao_id == e.id)).scalar_one()

    z = db.execute(select(ZaloNoiTaiKhoan)
                   .where(ZaloNoiTaiKhoan.user_id == t.id)).scalars().first()
    hs["zalo_noi"] = "đã nối" if z is not None else "chưa nối"

    # ---- nhóm 6: đọc từ siêu dữ liệu, cùng bộ đếm với phép gộp và phép xoá
    dong = SX.dem_dong_tro_toi(db, t.id)
    hs["viec_dang_ganh"] = dong
    hs["so_dong_tro_toi"] = sum(x["so_dong"] for x in dong)

    # ---- nhóm 10 / 10b: nhật ký. 10 chỉ TÊN TRƯỜNG, 10b mới có giá trị trước/sau.
    nk = list(db.execute(select(AuditLog)
                         .where(AuditLog.entity == f"user:{t.username}")
                         .order_by(AuditLog.id.desc()).limit(40)).scalars())
    hs["nhat_ky"] = [
        {"luc": r.ts.isoformat(), "ai": r.actor, "viec": r.action,
         "truong": sorted(set((r.before or {}).keys()) | set((r.after or {}).keys()))}
        for r in nk]
    hs["nhat_ky_gia_tri"] = [
        {"luc": r.ts.isoformat(), "ai": r.actor, "viec": r.action,
         "truoc": r.before, "sau": r.after} for r in nk]

    da_khai = [c for n in NHOM_TRUONG for c in n["truong"]]
    thieu = [c for c in da_khai if c not in hs]
    return hs, thieu


def doc_ho_so(db, nguoi_xem, muc_tieu) -> dict:
    """Cửa đọc hoàn chỉnh: gom, giải phạm vi, cắt theo vai, và nói ra mình đã làm gì.

    KHÔNG ném 403 ở đây. Hàm này chỉ tính; cửa HTTP quyết định mã trả về — tách ra để phép thử
    gọi thẳng hàm mà không cần dựng máy chủ.
    """
    trong, luat = trong_pham_vi(db, nguoi_xem, muc_tieu)
    day_du, thieu = thu_thap(db, muc_tieu)
    vai = (getattr(nguoi_xem, "role", "") or "").strip()
    cat = cat_ho_so_theo_vai(day_du, vai, trong_pham_vi=trong)

    nhom_thay, nhay_da_doc = [], []
    for n in NHOM_TRUONG:
        q = quyen_nhom(n["ma"], vai, trong)
        if q == KHONG:
            continue
        nhom_thay.append({"ma": n["ma"], "ten": n["ten"], "quyen": q})
        if q == CO and n["ma"] in NHOM_NHAY_CAM and any(c in cat for c in n["truong"]):
            nhay_da_doc.append(n["ma"])

    return {
        "user_id": muc_tieu.id,
        "ho_ten": muc_tieu.full_name,
        "vai_nguoi_xem": vai,
        "trong_pham_vi": trong,
        "luat_pham_vi": luat,
        "ho_so": cat,
        "nhom_thay": nhom_thay,
        "nhom_nhay_cam_da_doc": nhay_da_doc,
        "thieu_nguon": thieu,
    }
