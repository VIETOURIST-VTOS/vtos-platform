"""Vận hành: báo cáo ngày (Điều 12), ca trực page (cổng 11), đề nghị chi – lệnh chi NCC (robot R3, cổng 14/15).

R3 chỉ tính toán, gắn cảnh báo và xếp cấp duyệt; quyết định duyệt là người. Không robot nào chuyển tiền.
"""
import re
from datetime import date, datetime, timedelta, time
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User, Alert
from app.services import chu_ky as _CK   # bang chu ky, Dot LG2 - nhap o DAU TEP vi require_roles doc no luc nap mo-dun
from app.models.hr import Employee
from app.models.ops import DailyReport, PageShift, PaymentRequest, DailyReportVersion, ReportExtraForm
from app.models.payments import Receipt
# DOT R4c-3 02/11/2026 — nhap o DAU TEP: `models.hach_toan` la mot bang khai, khong nhap
# `services.ops`, nen khong co vong tron. Va hai bang nay la NGUON DUY NHAT cua luat
# "hinh thuc nao chay tren tai khoan ngan hang" — doc chu khong khai lai.
from app.models.hach_toan import HINH_THUC_TT, HTTT_QUA_TIEN_MAT
from app.services import ngoai_te_chi as NT
from app.services import rules as R
from app.services import accounting as ACC
from app.api.deps import toan_quyen, toan_quyen_ke_ca_tach_bach   # Chủ tịch toàn quyền – MỘT luật, xem deps.toan_quyen

REPORT_DEADLINE = time(20, 0)
NO_TIMESHEET_DEPTS = ("kd_le", "kd_doan", "dieu_hanh", "marketing", "cntt")   # khối bỏ chấm công → báo cáo ngày bắt buộc
REPORT_DEPTS = ("kd_le", "kd_doan", "dieu_hanh", "marketing", "cntt", "ketoan", "hcns")   # 7 phòng có mẫu báo cáo (như form Google)

# Mẫu "Phần 2 – Số liệu trong ngày" theo phòng (đúng nhãn của form Google "Báo cáo công việc hằng ngày · Vietourist")
DEPT_FORMS = {
    "kd_le": {"name": "Kinh doanh Lẻ", "fields": ["Lead nhận trong ngày", "Lead đã liên hệ", "Booking chốt trong ngày", "Doanh thu chốt trong ngày", "Doanh thu luỹ kế tháng", "Ca trực page hôm nay", "Khách sắp khởi hành cần đôn đốc thanh toán"],
              "hint": "Việc gắn với khách, booking hoặc đoàn thì ghi kèm mã để đối chiếu được trên Vietrip/VTOS."},
    "kd_doan": {"name": "Kinh doanh Đoàn", "fields": ["Khách đang tiếp cận, báo giá gửi đi trong ngày", "Đoàn chốt trong ngày", "Đoàn đang chạy", "Đoàn đã kết thúc chờ quyết toán", "Công nợ cần đôn đốc", "Lợi nhuận quyết toán luỹ kế tháng"],
                "hint": "Mỗi đoàn ghi tên khách hàng, số khách, ngày dự kiến, giá trị."},
    "dieu_hanh": {"name": "Điều hành", "fields": ["Dự toán đã lập", "Dịch vụ đã đặt", "Chuyến đang chạy cần theo dõi", "Quyết toán đã đóng trong ngày", "Quyết toán còn treo quá hạn", "Hồ sơ visa trong ngày", "Sự vụ phát sinh"],
                  "hint": "Ghi mã tour cho dự toán, dịch vụ, quyết toán."},
    "marketing": {"name": "Marketing", "fields": ["Chi phí quảng cáo trong ngày", "Số lead thu được trong ngày", "Số lead đã chuyển về Vietrip", "Chiến dịch bật, tắt hoặc chỉnh ngân sách", "Nội dung và mạng xã hội", "Thiết kế", "Web và tối ưu công cụ tìm kiếm"],
                  "hint": "Chi phí và lead ghi theo kênh (Facebook, Google, TikTok, Zalo…)."},
    "cntt": {"name": "Công nghệ thông tin", "fields": ["Yêu cầu tiếp nhận trong ngày", "Yêu cầu đã xử lý xong", "Yêu cầu đang xử lý", "Sự cố hệ thống", "Thay đổi phân quyền đã thực hiện", "Cổng chặn đang lập trình", "Sao lưu hôm nay"],
             "hint": "Ghi rõ hệ thống (Vietrip, VTOS, SePay, website) và người yêu cầu."},
    "ketoan": {"name": "Kế toán", "fields": ["Phiếu thu đã xác nhận trong ngày", "Lệnh chi / thanh toán NCC đã thực hiện", "Quyết toán tour đã xác nhận", "Hóa đơn đã xuất trong ngày", "Công nợ khách hàng và NCC cần đôn đốc", "Thuế, BHXH, ngân hàng", "Tồn quỹ tiền mặt cuối ngày"],
               "hint": "Ghi mã booking / mã tour / số hóa đơn để đối chiếu."},
    "hcns": {"name": "Nhân sự Hành chính", "fields": ["Tuyển dụng", "Hồ sơ lao động đã xử lý", "Chấm công, phép và bảng lương", "Bảo hiểm xã hội và việc với cơ quan nhà nước", "Hành chính, văn thư và con dấu", "Sự vụ nhân sự cần báo cáo", "Thu chi tiền mặt và tồn quỹ cuối ngày"],
             "hint": "Không có phát sinh thì bấm «Không phát sinh» — ô bỏ trống là chưa nhập."},
    # BC-1 (Chủ tịch 26/10/2026): sáu mẫu thêm. Ba mẫu đầu theo PHÒNG; ba mẫu sau là PHẦN VIỆC —
    # không phòng nào tên «Ngân hàng» hay «CSKH», người làm việc ấy được Chủ tịch giao kiêm nhiệm.
    "visa": {"name": "Ban Visa", "fields": ["Hồ sơ nhận trong ngày", "Hồ sơ đã nộp đại sứ quán / lãnh sự", "Hồ sơ có kết quả", "Đậu", "Rớt", "Hồ sơ thiếu giấy tờ cần khách bổ sung", "Lịch hẹn sinh trắc / phỏng vấn sắp tới"],
             "hint": "Ghi mã hồ sơ visa và nước cho từng việc."},
    "huong_dan": {"name": "Hướng dẫn (Trưởng phòng)", "fields": ["Đoàn đang có HDV", "Đoàn chưa phân HDV", "HDV đang đi tour", "Nhận xét / khiếu nại về HDV", "Hồ sơ HDV cần bổ sung"],
                  "hint": "Ghi mã tour và tên HDV."},
    "doi_xe": {"name": "Đội xe (quản lý)", "fields": ["Xe đang đi", "Xe nằm bãi", "Lệnh điều xe đã lập", "Chuyến đã nhập quyết toán", "Bảo dưỡng / sửa chữa", "Giấy tờ xe sắp hết hạn", "Sự cố"],
               "hint": "Ghi biển số xe cho từng việc."},
    "ngan_hang": {"name": "Ngân hàng", "fields": [], "dong": "tai_khoan",
                  "hint": "Số dư theo từng tài khoản và đồng tiền, cùng một mốc chốt. Không cộng tiền khác đồng tiền."},
    "cskh": {"name": "Chăm sóc khách hàng", "fields": ["Khách đã chăm sóc", "Đánh giá hợp lệ nhận được", "Khiếu nại mới", "Khiếu nại đã xử lý xong", "Cuộc gọi hotline", "Khách giới thiệu"],
             "hint": "Không ghi số điện thoại khách vào báo cáo."},
    "ir_phap_che": {"name": "IR – Pháp chế", "fields": ["Lịch công bố thông tin sắp đến hạn", "Hợp đồng / văn bản đã rà soát", "Vụ việc pháp lý đang theo dõi", "Ý kiến rà soát đã gửi"],
                    "hint": "Tài liệu hạn chế không chép vào báo cáo — chỉ ghi mã hồ sơ."},
}
PART_TITLES = {1: "VIỆC ĐÃ LÀM HÔM NAY", 2: "SỐ LIỆU TRONG NGÀY", 3: "VIỆC NGÀY MAI", 4: "VƯỚNG MẮC – ĐỀ XUẤT", 5: "ĐÍNH KÈM"}
# Mẫu chỉ mở bằng KIÊM NHIỆM (không phòng nào mang tên ấy).
MAU_KIEM_NHIEM = ("ngan_hang", "cskh", "ir_phap_che")
# Giá trị ô số «Không phát sinh»: khác ô trống (CHƯA NHẬP). Ô trống không bao giờ được đọc thành 0.
KHONG_PHAT_SINH = "Không phát sinh"

# ── BC-1 · AI PHẢI NỘP (Chủ tịch 26/10/2026) ────────────────────────────────────────────────────
# «Tất cả văn phòng trừ HDV và tài xế; TP Hướng dẫn và quản lý xe vẫn phải báo cáo; Ban TGĐ không
# nộp.» Loại theo VỊ TRÍ chứ không theo phòng: phòng Hướng dẫn có trưởng phòng phải nộp và HDV
# không nộp — loại cả phòng là bỏ sót người phải nộp.
KHONG_NOP_VI_TRI = ("hdv", "tai_xe")
KHONG_NOP_PHONG = ("ban_tgd",)
# Nghỉ CẢ NGÀY đã duyệt thì không có nghĩa vụ. Công tác và tăng ca KHÔNG miễn (tài liệu bàn giao IT).
NGHI_MIEN_BAO_CAO = ("phep_nam", "khong_luong", "om_dau", "thai_san")

# ── BC-1 · HẠN NỘP ─────────────────────────────────────────────────────────────────────────────
# Trước 0 giờ ngày kế tiếp, giờ Việt Nam; đúng 00:00 là muộn cho ngày trước. Áp từ ngày ghi ở tham
# số — ngày cũ giữ hạn 20 giờ, không tính lại (Chủ tịch: «ngay khi lên hệ», không hồi tố).
KHOA_HAN_0H = "bao_cao_ngay_han_0h_tu"


def dept_of_user(db: Session, u: User) -> str:
    """Phòng dùng cho mẫu báo cáo: theo hồ sơ nhân sự, rồi theo vai trò."""
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e and e.department in DEPT_FORMS: return e.department
    if u.department in DEPT_FORMS: return u.department
    return {"nv_kd": "kd_le", "tn_kd": "kd_le", "tp_kd": "kd_le", "gd_kd": "kd_le", "ptgd_doan": "kd_doan", "nv_dh": "dieu_hanh", "tp_dh": "dieu_hanh", "nv_mkt": "marketing", "ptgd_mkt": "marketing",
            "cntt": "cntt", "ketoan": "ketoan", "hcns": "hcns", "gd_doi_xe": "doi_xe", "visa": "visa"}.get(u.role, "kd_le")


def gio_vn() -> datetime:
    """Giờ Việt Nam, KHÔNG phụ thuộc múi giờ máy chủ (KS-18: máy chủ từng chạy sai múi giờ)."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)


def moc_han_0h(db: Session) -> date:
    from app.services import moi_truong_du_lieu as MT
    try:
        d = MT.doc_ngay(str(R.get_param_chu(db, KHOA_HAN_0H)).strip())
    except KeyError:
        d = None
    return d or date(2026, 10, 26)


def han_nop(db: Session, d: date) -> datetime:
    """Thời điểm HẾT HẠN của báo cáo ngày d (giờ VN, naive). Nộp LÚC hoặc SAU mốc này là muộn."""
    if d >= moc_han_0h(db):
        return datetime.combine(d + timedelta(days=1), time(0, 0))
    return datetime.combine(d, REPORT_DEADLINE) + timedelta(minutes=1)   # luật cũ: tới hết 20:00


def han_chu(db: Session, d: date) -> str:
    return "0:00 ngày kế tiếp" if d >= moc_han_0h(db) else "20:00"


def phai_nop(e: Employee) -> bool:
    return bool(e.active and e.user_id and e.department not in KHONG_NOP_PHONG
                and (e.position or "") not in KHONG_NOP_VI_TRI)


def nhan_vien_phai_nop(db: Session) -> list[Employee]:
    return [e for e in db.execute(select(Employee).where(Employee.active == True,   # noqa: E712
                                                         Employee.user_id != None)).scalars()  # noqa: E711
            if phai_nop(e)]


def nghi_ca_ngay_nhieu(db: Session, employee_ids, d: date) -> dict[int, str]:
    """KS-BC · `nghi_ca_ngay` cho NHIỀU người trong MỘT câu hỏi — cùng điều kiện, cùng luật nửa ngày
    không miễn, cùng tên loại nghỉ. Người không nghỉ thì không có khoá."""
    from app.models.hrm import LeaveRequest, LEAVE_KINDS
    ids = list(employee_ids)
    ra: dict[int, str] = {}
    if not ids:
        return ra
    for lr in db.execute(select(LeaveRequest).where(
            LeaveRequest.employee_id.in_(ids), LeaveRequest.status == "duyet",
            LeaveRequest.kind.in_(NGHI_MIEN_BAO_CAO),
            LeaveRequest.date_from <= d, LeaveRequest.date_to >= d).order_by(LeaveRequest.id)).scalars():
        if lr.employee_id in ra:
            continue
        if (lr.date_to - lr.date_from).days + 1 <= (lr.days or 0) + 1e-9:
            ra[lr.employee_id] = LEAVE_KINDS.get(lr.kind, {}).get("ten", lr.kind)
    return ra


def nghi_ca_ngay(db: Session, employee_id: int, d: date) -> str | None:
    """Tên loại nghỉ nếu ngày d là ngày nghỉ CẢ NGÀY đã duyệt; nửa ngày không miễn."""
    from app.models.hrm import LeaveRequest, LEAVE_KINDS
    for lr in db.execute(select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id, LeaveRequest.status == "duyet",
            LeaveRequest.kind.in_(NGHI_MIEN_BAO_CAO),
            LeaveRequest.date_from <= d, LeaveRequest.date_to >= d)).scalars():
        if (lr.date_to - lr.date_from).days + 1 <= (lr.days or 0) + 1e-9:
            return LEAVE_KINDS.get(lr.kind, {}).get("ten", lr.kind)
    return None


def mau_cua(db: Session, u: User) -> list[str]:
    """Mẫu của người nộp: mẫu chính theo phòng, rồi các phần việc kiêm nhiệm Chủ tịch đã giao."""
    chinh = dept_of_user(db, u)
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    them = [] if e is None else [x.mau for x in db.execute(select(ReportExtraForm).where(
        ReportExtraForm.employee_id == e.id, ReportExtraForm.active == True)).scalars()   # noqa: E712
        if x.mau in DEPT_FORMS and x.mau != chinh]
    return [chinh] + sorted(set(them), key=list(DEPT_FORMS).index)


def truong_cua(db: Session, mau: str) -> list[str]:
    """Các ô số của một mẫu. Ngân hàng đọc DANH MỤC TÀI KHOẢN đang dùng — không viết cứng số tài khoản."""
    f = DEPT_FORMS.get(mau, {})
    if f.get("dong") == "tai_khoan":
        from app.models.banks import BankAccount
        tk = [f"{a.code} · {a.bank_name} ({a.currency}) · số dư cuối ngày"
              for a in db.execute(select(BankAccount).where(BankAccount.active == True)   # noqa: E712
                                  .order_by(BankAccount.code)).scalars()]
        return tk + ["Giao dịch chưa rõ nội dung", "Mốc chốt sao kê"]
    return list(f.get("fields", []))


def khoa_o(mau: str, chinh: str, ten: str) -> str:
    """Khoá lưu của một ô Phần 2: mẫu chính giữ nhãn trơn (như dữ liệu cũ), mẫu kiêm nhiệm có tiền tố."""
    return ten if mau == chinh else f"{DEPT_FORMS[mau]['name']} · {ten}"


def parse_part2(raw: str) -> dict:
    """part2_numbers lưu JSON {nhãn: giá trị}; dữ liệu cũ dạng văn bản → {'Số liệu': text}."""
    import json
    if not raw: return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {"Số liệu": str(v)}
    except ValueError:
        return {"Số liệu": raw}


def mail_text(u: User, dept: str, d: date, p1: str, p2: dict, p3: str, p4: str, staff_code: str = "") -> tuple[str, str]:
    """Tiêu đề + nội dung thư đúng bố cục form Google (để gửi email baocao@ và lưu kèm)."""
    name = DEPT_FORMS.get(dept, {}).get("name", dept)
    subject = f"Báo cáo ngày · {u.full_name} · {name} · {d:%d/%m/%Y}"
    lines = [f"PHẦN 1 — {PART_TITLES[1]}", p1.strip() or "(trống)", "", f"PHẦN 2 — {PART_TITLES[2]}"]
    # BC-1: in ĐÚNG các khoá đã lưu (gồm cả mục kiêm nhiệm và tài khoản ngân hàng đọc từ danh mục);
    # ô trống in «chưa nhập» — không in «không», vì «không» đọc ra là đã xác nhận không phát sinh.
    for k in (list(p2.keys()) or DEPT_FORMS.get(dept, {}).get("fields", [])):
        lines.append(f"{k}: {str(p2.get(k, '')).strip() or 'chưa nhập'}")
    lines += ["", f"PHẦN 3 — {PART_TITLES[3]}", p3.strip() or "(trống)", "", f"PHẦN 4 — {PART_TITLES[4]}", p4.strip() or "không", "",
              f"— {u.full_name}" + (f" · Mã NV {staff_code}" if staff_code else "") + f" · {name}"]
    return subject, "\n".join(lines)

# ĐỢT TKC-3 07/11/2026 — BẢNG NÀY CHỈ CÒN NÓI «LOẠI CHI NÀO GHI CÔNG NỢ», KHÔNG NÓI TÀI KHOẢN.
#
# Bản cũ gõ thẳng `154` / `641` / `642` — cả ba là tài khoản TỔNG HỢP trong danh mục thật, và
# `post_entry` nhận bút toán vào tài khoản cha mà không chặn, nên việc này im lặng suốt. Đo trên
# sổ thật 07/11/2026 (thẻ «Bút toán ghi vào tài khoản cha», bảng «Theo đường ghi»): đường
# `de_nghi_chi` đã ghi 27 dòng / 27 chứng từ vào `154`.
#
# Và lỗ thứ hai, nặng hơn: `misa.CATEGORY_ACCOUNT` khai CÙNG các loại chi ấy ở CẤP CON (1541,
# 6417, 6428) theo đúng các quyết định 08/10, 26/10 và 31/10/2026. Hai bảng cùng nói một luật,
# và chúng ĐÃ LỆCH — cùng một khoản chi nằm ở `154` trong sổ VTOS và `1541` trong bảng kê xuất
# sang MISA. Nay bảng này chỉ giữ KHÓA, số hiệu tài khoản lấy ở `services/tk_chi_tiet.py`, và
# `test_tkc3_3` canh hai bảng khớp nhau.
#
# Các loại chi KHÔNG có ở đây thì KHÔNG ghi công nợ lúc duyệt, và đó là cố ý: `hoan_tien` ghi ở
# bước khác, `tam_ung` ghi 141 khi chi rồi hoàn ứng vào chi phí tour khi Kế toán xác nhận quyết
# toán. Thêm một loại vào đây là mở một đường ghi sổ mới — không phải một dòng cấu hình.
CATEGORY_TK_KHOA = {"chi_tour": "dn_chi_chi_tour", "marketing": "dn_chi_marketing",
                    "hanh_chinh": "dn_chi_hanh_chinh", "hoa_hong": "dn_chi_hoa_hong",
                    "tra_ncc_thu_ho": "dn_chi_tra_ncc_thu_ho"}
# ĐỘI XE — Chủ tịch quyết 05/10/2026: "liên quan đến sửa chữa, hư hỏng, tiền bạc là do TGĐ / CT
# duyệt và thấy". Hai loại `sua_chua_xe` và `tam_ung_tai_xe` KHÔNG đổi người ký: cửa duyệt vẫn là
# TGĐ (và Chủ tịch khi cần hai chữ ký), y như mọi loại chi khác. Thứ chúng đổi là người XÁC NHẬN
# NGHIỆP VỤ ở bước đầu — Giám đốc đội xe, người duy nhất biết đúng xe ấy có hỏng thật không và giá
# garage báo có hợp lý không.
#
# Vì sao không dùng lại `tam_ung` sẵn có cho tạm ứng tài xế: `tam_ung` bắt buộc gắn mã tour và do
# Trưởng phòng Điều hành xác nhận. Tiền đi đường của tài xế gắn với CHUYẾN XE, và người xác nhận là
# Giám đốc đội xe. Nhét vào loại cũ thì hồ sơ chạy sang bàn người không quản tài xế, và lần nào
# cũng phải bịa ra một mã tour.
#
# GIỮ BẢNG NÀY GỌN TRONG MỘT KHỐI LIỀN: hàng rào `test_luong_viec` đọc 400 ký tự sau tên biến để so
# bảng luồng công việc với mã đang chạy. Chú thích chen vào giữa các dòng khai là đẩy dòng cuối ra
# ngoài tầm đọc ấy, và hàng rào mù đi mà không báo gì.
CATEGORY_CONFIRMER = {"chi_tour": ("tp_dh",), "marketing": ("ptgd_mkt",), "hanh_chinh": ("hcns",),
                      "hoan_tien": ("gd_kd", "tp_kd", "tp_dh"), "tam_ung": ("tp_dh",),
                      "sua_chua_xe": ("gd_doi_xe",), "tam_ung_tai_xe": ("gd_doi_xe",), "chi_doi_xe": ("gd_doi_xe",), "hoa_hong": ("gd_kd",),
                      "tra_ncc_thu_ho": ("robot",)}   # KS-16d: robot kế toán xác nhận + kiểm (Chủ tịch 31/10/2026)

# Loại chi tài xế được TỰ LẬP. Đúng một loại, và cố ý.
#
# `sua_chua_xe` KHÔNG có trong danh sách này: lúc tài xế phát hiện xe hỏng thì CHƯA CÓ số tiền và
# CHƯA CÓ garage — hai thứ `create_request` bắt buộc phải có. Bắt tài xế lập đề nghị chi lúc ấy là
# bắt họ bịa ra một con số, đúng thứ ranh giới 09/9/2026 cấm. Đề nghị sửa chữa do Giám đốc đội xe
# lập SAU KHI có báo giá. Việc "báo hư hỏng" là một việc khác, chưa có cửa, và nó chưa có cửa là
# một việc CÒN THIẾU chứ không phải một việc đã xong.
LOAI_CHI_TAI_XE_TU_LAP = ("tam_ung_tai_xe",)

# ══════════════════════════════════════════════════════════════════════════════════════════
# ĐỘI XE v3.3 — `chi_doi_xe`. Chủ tịch chốt 10/11/2026, bốn ý:
#   1. Đề xuất chi của GĐ đội xe đi VÀO đề nghị chi này, không dựng luồng duyệt thứ hai (tài liệu v3.3
#      mục 3). Mốc duyệt là mốc chung `nguong_chu_tich_duyet_chi`, không có mốc riêng của đội xe.
#   2. GĐ đội xe là trưởng bộ phận, nên phiếu GĐ gửi coi như BỘ PHẬN ĐÃ XÁC NHẬN: bắt đầu ở `cho_kt`.
#      Vẫn đủ hai người khác người lập: Kế toán kiểm, TGĐ / Chủ tịch ký (người lập không tự ký — `step`).
#   3. Vào SỔ VTD (pháp nhân mẹ): Vietrip chỉ là đơn vị vận hành.
#   4. Tài khoản theo nhóm khoản, khóa lúc lập: chi phí → 627 (như sửa xe, tháng nào tính tháng đó),
#      tạm ứng / nạp quỹ → 141, quyết toán chủ xe → 331.
#
# «Điều chuyển tiền nội bộ» KHÔNG đi đường này: nó không phải một khoản chi, và sổ VTOS chưa có tài
# khoản nội bộ (136 / 336) để ghi. Chặn ở cửa lập, nói ra để Kế toán làm bút toán điều chuyển.
NHOM_DOI_XE = {"Chi phí riêng của xe": "627", "Chi phí chung phân bổ": "627", "Sửa chữa – bảo dưỡng": "627",
               "Tài xế (công tác phí, lương)": "627", "Quyết toán chủ xe / đối tác": "331",
               "Nạp quỹ / tạm ứng (không phải chi phí)": "141"}
NHOM_DOI_XE_CHAN = "Điều chuyển tiền nội bộ (không phải chi phí)"
LOAI_DOI_XE = {"thanh_toan": "Thanh toán", "tam_ung": "Tạm ứng", "hoan_ung": "Hoàn ứng / hoàn chi"}
# Khoản trả cho người của mình (tài xế), tạm ứng, nạp quỹ: không có mã số thuế bên nhận để Kế toán đòi.
NHOM_DOI_XE_KHONG_MST = ("Tài xế (công tác phí, lương)", "Nạp quỹ / tạm ứng (không phải chi phí)")


def tk_doi_xe(nhom: str, loai: str) -> str:
    """Tài khoản của một phiếu đội xe. Tạm ứng luôn 141, bất kể nhóm: tiền giao người của công ty."""
    return "141" if loai == "tam_ung" else NHOM_DOI_XE[nhom]


def _chuan_doi_xe(db: Session, u: User, data: dict) -> dict:
    from app.models.hr import Vehicle
    if u.role == "gd_doi_xe" and (data.get("supplier_bank") or "").strip():
        raise ValueError("Số tài khoản và ngân hàng của bên nhận do Kế toán kiểm soát, không nhập ở màn Giám "
                         "đốc đội xe (v3.3 §2, §7). Ghi tên bên nhận; Kế toán đối chiếu theo danh mục.")
    x = dict(data.get("doi_xe") or {})
    nhom, loai, pv = (x.get("nhom") or "").strip(), (x.get("loai") or "thanh_toan").strip(), x.get("pham_vi") or "xe"
    if nhom == NHOM_DOI_XE_CHAN:
        raise ValueError("Điều chuyển tiền nội bộ không phải một đề nghị chi — Kế toán lập bút toán điều chuyển "
                         "giữa VTD và Vietrip. Sổ VTOS chưa có tài khoản nội bộ để ghi khoản này.")
    if nhom not in NHOM_DOI_XE:
        raise ValueError("Chọn nhóm khoản chi — không phân loại lúc lập thì cuối tháng phải đọc lại từng phiếu để đoán")
    if loai not in LOAI_DOI_XE:
        raise ValueError("Loại đề nghị không hợp lệ")
    if pv not in ("xe", "doi"):
        raise ValueError("Phạm vi là một xe hoặc toàn đội")
    v = None
    if pv == "xe":
        if x.get("xe_id"):
            v = db.get(Vehicle, int(x["xe_id"]))
        elif (x.get("bien_so") or "").strip():
            v = db.execute(select(Vehicle).where(Vehicle.plate == x["bien_so"].strip())).scalars().first()
        if v is None:
            raise ValueError("Chọn xe, hoặc đổi phạm vi sang «chi phí toàn đội»")
    if not (x.get("can_cu") or "").strip():
        raise ValueError("Chọn căn cứ số tiền — VTOS không tự cộng VAT")
    kg_ma = (x.get("ma_khoan_goc") or "").strip()
    if kg_ma:
        kg = khoan_goc(db, kg_ma)
        if kg is None:
            raise ValueError("Khoản gốc phải chọn trong danh sách khoản đã ghi của xe (phiếu chuyến / phiếu bảo "
                             "dưỡng) — mã gõ tay thì máy không đối chiếu được, và chống ghi hai lần không chạy")
        if v is not None and kg["vehicle_id"] != v.id:
            raise ValueError(f"Khoản gốc {kg['ten']} thuộc xe khác — chọn khoản của chính xe {v.plate}")
        cu = de_nghi_theo_khoan_goc(db).get(kg_ma)
        if cu:
            raise ValueError(f"Khoản gốc {kg['ten']} đã có đề nghị chi {cu} — một khoản gốc chỉ một đề nghị chi. "
                             f"Cần chi thêm thì Kế toán chi tiếp phần còn lại của {cu}.")
    return {"pham_vi": pv, "xe_id": v.id if v else None, "bien_so": v.plate if v else "", "loai": loai, "nhom": nhom,
            "tk": tk_doi_xe(nhom, loai), "can_cu": x["can_cu"].strip()[:80],
            "ma_khoan_goc": kg_ma[:60], "hen_bo_sung": (x.get("hen_bo_sung") or "").strip()[:200],
            "ghi_chu_kiem_tra": (x.get("ghi_chu_kiem_tra") or "").strip()[:500]}


# ══════════════════════════════════════════════════════════════════════════════════════════
# CHỐNG GHI CHI PHÍ HAI LẦN — Chủ tịch duyệt bản xem trước 10/11/2026 (phần D).
#
# «Mã khoản gốc» trước đây là ô chữ tự do: gõ gì cũng nhận, nên không máy nào đối chiếu được. Nay là
# một mã CHỌN từ sổ thật: `tc:<id>` một dòng chi phí chuyến, `bd:<id>` một phiếu bảo dưỡng / sửa chữa.
# Một khoản gốc chỉ một đề nghị chi — khoản đã ghi ở phiếu chuyến mà lại đề nghị chi thêm lần nữa là
# tiền ra hai lần cho một việc.
# ══════════════════════════════════════════════════════════════════════════════════════════
def khoan_goc(db: Session, ma: str) -> dict | None:
    from app.models.fleet import Maintenance, Trip, TripCost
    m = re.fullmatch(r"(tc|bd):(\d+)", (ma or "").strip())
    if not m:
        return None
    if m.group(1) == "tc":
        c = db.get(TripCost, int(m.group(2)))
        t = db.get(Trip, c.trip_id) if c else None
        if not c or not t:
            return None
        return {"ma": ma, "loai": "tc", "id": c.id, "vehicle_id": t.vehicle_id, "so_tien": c.amount,
                "ngay": t.ngay_di, "ten": f"Chuyến {t.ma_phieu or t.id} · {c.kind}", "chung_tu": c.chung_tu or ""}
    b = db.get(Maintenance, int(m.group(2)))
    if not b:
        return None
    return {"ma": ma, "loai": "bd", "id": b.id, "vehicle_id": b.vehicle_id, "so_tien": b.so_tien, "ngay": b.ngay,
            "ten": f"Phiếu bảo dưỡng #{b.id} · {b.noi_dung[:60]}", "chung_tu": b.chung_tu or ""}


def de_nghi_theo_khoan_goc(db: Session) -> dict[str, str]:
    """{mã khoản gốc: mã DC} của mọi đề nghị chi đội xe còn hiệu lực (không tính hồ sơ đã từ chối)."""
    ra: dict[str, str] = {}
    for r in db.execute(select(PaymentRequest).where(PaymentRequest.category == "chi_doi_xe",
                                                     PaymentRequest.status != "tu_choi")).scalars():
        k = ((r.doi_xe or {}).get("ma_khoan_goc") or "").strip()
        if k:
            ra.setdefault(k, r.code)
    return ra


def chung_tu_trung(db: Session, so_ct: str, bo_id: int | None = None) -> list[str]:
    """Mã các đề nghị chi KHÁC (mọi loại) đang dùng cùng số chứng từ — để CẢNH BÁO, không chặn: một hóa đơn
    trả hai đợt là chuyện có thật, nhưng người duyệt phải thấy."""
    ct = (so_ct or "").strip()
    if not ct:
        return []
    q = select(PaymentRequest.code).where(PaymentRequest.document_ref == ct, PaymentRequest.status != "tu_choi")
    if bo_id:
        q = q.where(PaymentRequest.id != bo_id)
    return [c for (c,) in db.execute(q).all()]


def _trung_doi_xe(db: Session, data: dict, amount: float) -> PaymentRequest | None:
    """Bấm Gửi hai lần / tải lại khi mạng chậm: cùng chứng từ, cùng số tiền, cùng bên nhận là MỘT phiếu.
    Không có số chứng từ thì không đoán (giữ đúng luật KS-64 B2)."""
    ct = (data.get("document_ref") or "").strip()
    if not ct or data.get("cho_phep_trung"):
        return None
    return db.execute(select(PaymentRequest).where(
        PaymentRequest.category == "chi_doi_xe", PaymentRequest.status != "tu_choi",
        PaymentRequest.document_ref == ct, PaymentRequest.amount == amount,
        PaymentRequest.supplier_name == data["supplier_name"])).scalars().first()


def _kiem_chung_tu_mst(db: Session, r: PaymentRequest) -> None:
    """Chứng từ + mã số thuế bên nhận — Kế toán kiểm. Đề nghị chi thường: ở bước `check`. Đề xuất chi đội
    xe (không có bước `check`, Chủ tịch 10/11/2026): ở bước CHI, trước khi tiền ra."""
    _dx = r.doi_xe if r.category == "chi_doi_xe" else None
    if not r.has_document and not (_dx is not None and co_tep_doi_xe(db, r)):
        raise ValueError("Thiếu chứng từ đính kèm (hợp đồng/hóa đơn/báo giá) – không chuyển duyệt"
                         if _dx is None else "Thiếu chứng từ của đề xuất chi đội xe — chưa chi được")
    _khong_mst = r.category in ("hoan_tien", "tam_ung") or (_dx is not None and (
        _dx.get("loai") != "thanh_toan" or _dx.get("nhom") in NHOM_DOI_XE_KHONG_MST))
    if not _khong_mst and not r.supplier_tax_code: raise ValueError("NCC chưa có MST – phải xác nhận trước khi thanh toán")


def co_tep_doi_xe(db: Session, r: PaymentRequest) -> bool:
    """Chứng từ đội xe gắn ở kho «de_xuat_chi_xe» theo MÃ PHIẾU — có tệp còn hiệu lực là có chứng từ."""
    from app.models.attachments import Attachment
    return db.execute(select(Attachment.id).where(Attachment.doi_tuong == "de_xuat_chi_xe",
                                                  Attachment.doi_tuong_id == r.code,
                                                  Attachment.thu_hoi.is_(False))).first() is not None


# Vai DUY NHẤT duyệt được chi Marketing, kể từ chỉ đạo 23/9/2026.
VAI_DUYET_MKT = "ptgd_mkt"


def ai_duyet_duoc_mkt(db: Session) -> list[str]:
    """Danh sách tài khoản ĐANG HOẠT ĐỘNG giữ vai P.TGĐ Marketing.

    Vì sao cần hàm này: từ 23/9/2026 mọi hồ sơ chi Marketing dừng ở MỘT chữ ký của vai này. Một vai
    rỗng thì mọi hồ sơ nằm chờ vĩnh viễn — và nằm chờ thì trông y hệt "đang xử lý" trên màn hình.
    Không ai báo lỗi, không ai thấy đỏ, tiền chỉ đơn giản là không được duyệt. Đó là kiểu hỏng tệ
    nhất: im lặng.

    Hàm trả về DANH SÁCH chứ không trả về True/False, để chỗ gọi nói được ra TÊN người duyệt khi có,
    và nói được "chưa ai" khi rỗng.
    """
    return sorted(
        u for (u,) in db.execute(
            select(User.username).where(User.role == VAI_DUYET_MKT, User.active.is_(True))).all())


# ====================== BÁO CÁO NGÀY ======================
def robot_score(r: DailyReport) -> tuple[float, str]:
    """Điểm nháp 0–10: Phần 1 ≥ 20 ký tự = 3; Phần 2 điền ≥ 2/3 số trường = 2 (điền hết = 3); Phần 3 ≥ 20 ký tự = 2; nộp đúng hạn = 2.

    «Không phát sinh» là ô ĐÃ ĐIỀN (người nộp xác nhận không có), khác ô trống."""
    p2 = parse_part2(r.part2_numbers)
    filled2 = sum(1 for v in p2.values() if str(v or "").strip())
    n2 = max(len(p2), 1)
    s1 = 3 if len((r.part1_done or "").strip()) >= 20 else 0
    s2 = 3 if filled2 >= n2 else 2 if filled2 * 3 >= n2 * 2 else 1 if filled2 else 0
    s3 = 2 if len((r.part4_plan or "").strip()) >= 20 else 0   # part4_plan = việc ngày mai (Phần 3 của form)
    score = s1 + s2 + s3 + (2 if r.on_time else 0)
    notes = []
    if not s1: notes.append("Phần 1 quá ngắn")
    if s2 < 3: notes.append(f"Phần 2 điền {filled2}/{n2} mục")
    if not s3: notes.append("Việc ngày mai quá ngắn")
    if not r.on_time: notes.append("nộp muộn")
    return float(min(score, 10)), "; ".join(notes) or "Đủ các phần, đúng hạn"


def submit_report(db: Session, u: User, d: date, p1: str, p2: str, p3: str, p4: str,
                  vuong_mac_cho: str = "", vuong_mac_han: date | None = None,
                  now: datetime | None = None) -> DailyReport:
    """Nộp hoặc nộp lại. BC-1: giờ là GIỜ VIỆT NAM; đúng hạn tính theo LẦN NỘP ĐẦU; mỗi lần nộp một
    bản chụp trong `daily_report_versions`. `now` chỉ để phép thử đặt đồng hồ — chỗ gọi thật bỏ trống."""
    import json
    now = now or gio_vn()
    if d > now.date():
        raise ValueError("Không nộp báo cáo cho ngày tương lai")
    r = db.execute(select(DailyReport).where(DailyReport.user_id == u.id, DailyReport.report_date == d)).scalars().first()
    if r and r.reviewed_by:
        raise ValueError("Báo cáo đã được trưởng phòng chấm – không sửa")
    if vuong_mac_cho and vuong_mac_cho not in DEPT_FORMS:
        raise ValueError("Phòng nhận vướng mắc không hợp lệ")
    if r is None:
        r = DailyReport(user_id=u.id, report_date=d, so_lan_nop=0); db.add(r)
    lan_dau = r.first_submitted_at is None and not r.id
    r.part1_done, r.part2_numbers, r.part3_issues, r.part4_plan = p1, p2, p3, p4
    r.vuong_mac_cho, r.vuong_mac_han = vuong_mac_cho or "", vuong_mac_han
    r.submitted_at = now
    if lan_dau:
        r.first_submitted_at = now
        r.on_time = now < han_nop(db, d)
    # Báo cáo CŨ (trước BC-1) không có lần nộp đầu: giữ nguyên cờ `on_time` đã ghi, không tính lại.
    r.so_lan_nop = (r.so_lan_nop or 0) + 1
    r.robot_score, r.robot_note = robot_score(r)
    db.flush()
    from app.services import bao_cao_ngay_xem as _XEM   # BC-2: nộp lại sau «cần bổ sung» về chờ xem; vướng mắc có phòng nhận thành việc theo dõi
    _XEM.sau_khi_nop(db, u, r, dept_of_user(db, u))
    db.add(DailyReportVersion(report_id=r.id, lan=r.so_lan_nop, luc=now, du_lieu=json.dumps(
        {"p1": p1, "p2": parse_part2(p2), "p3": p4, "p4": p3, "vuong_mac_cho": r.vuong_mac_cho,
         "vuong_mac_han": vuong_mac_han.isoformat() if vuong_mac_han else None}, ensure_ascii=False)))
    R.audit(db, u.username, u.role, "nop_bao_cao_ngay", f"report:{u.username}:{d}",
            after={"diem_robot": r.robot_score, "dung_gio": r.on_time, "lan": r.so_lan_nop})
    db.commit(); db.refresh(r)
    return r


_CHUA = object()


def trang_thai_ngay(db: Session, e: Employee | None, user_id: int, d: date, now: datetime | None = None,
                    *, nghi_san: dict | None = None, bc_san: dict | None = None, han_san=_CHUA) -> dict:
    """Một ngày của một người: không có nghĩa vụ / chưa đến hạn / quá hạn chưa nộp / đúng hạn / muộn.

    KS-BC · 08/11/2026 — `nghi_san` / `bc_san` / `han_san` là ba thứ chỗ gọi đã NẠP SẴN cho cả danh
    sách cùng ngày `d` (bảng tổng hợp báo cáo ngày gọi hàm này cho từng nhân viên: trước đây mỗi
    người ba câu hỏi riêng). Không truyền thì tự hỏi như cũ — cùng luật, cùng kết quả."""
    now = now or gio_vn()
    if d.weekday() == 6:
        return {"ngay": d.isoformat(), "ma": "khong_nghia_vu", "ten": "Chủ nhật"}
    if e is not None:
        nghi = nghi_san.get(e.id) if nghi_san is not None else nghi_ca_ngay(db, e.id, d)
        if nghi:
            return {"ngay": d.isoformat(), "ma": "khong_nghia_vu", "ten": f"{nghi} đã duyệt"}
    if bc_san is not None:
        r = bc_san.get(user_id)
    else:
        r = db.execute(select(DailyReport).where(DailyReport.user_id == user_id, DailyReport.report_date == d)).scalars().first()
    if r is None:
        qua = now >= (han_nop(db, d) if han_san is _CHUA else han_san)
        return {"ngay": d.isoformat(), "ma": "qua_han" if qua else "chua_den_han",
                "ten": "Quá hạn chưa nộp" if qua else "Chưa nộp · chưa đến hạn"}
    dau = r.first_submitted_at or r.submitted_at
    return {"ngay": d.isoformat(), "ma": "dung_han" if r.on_time else "muon",
            "ten": "Đúng hạn" if r.on_time else f"Muộn · {dau:%H:%M}", "lan": r.so_lan_nop or 1}


def review_report(db: Session, u: User, r: DailyReport, score: float, note: str) -> DailyReport:
    if not 0 <= score <= 10: raise ValueError("Điểm 0–10")
    r.manager_score, r.manager_note, r.reviewed_by, r.reviewed_at = score, note, u.username, datetime.now()
    R.audit(db, u.username, u.role, "tp_cham_bao_cao_ngay", f"report:{r.user_id}:{r.report_date}", after={"diem": score, "ghi_chu": note})
    db.commit()
    return r


def monthly_grade(reports: list[DailyReport], work_days: int) -> tuple[str, float]:
    """Xếp loại A/B/C/D: điểm bình quân (điểm TP nếu có, không thì điểm robot) × tỷ lệ ngày nộp."""
    if not work_days: return "-", 0.0
    pts = [(r.manager_score if r.manager_score is not None else r.robot_score) for r in reports]
    avg = (sum(pts) / work_days) if pts else 0.0
    grade = "A" if avg >= 8.5 else "B" if avg >= 7 else "C" if avg >= 5 else "D"
    return grade, round(avg, 2)


def work_days_in(y: int, m: int, until: date | None = None) -> list[date]:
    """Thứ Hai – Thứ Bảy (Chủ nhật nghỉ)."""
    d = date(y, m, 1); out = []
    while d.month == m and (until is None or d <= until):
        if d.weekday() != 6: out.append(d)
        d += timedelta(days=1)
    return out


def check_missing_reports(db: Session) -> int:
    """Robot: thiếu 1 ngày → nhắc nhở; 2 ngày liên tiếp → chuyển HCNS (cảnh báo đỏ). Chạy sau hạn nộp."""
    # BC-1: ngày được xét là ngày ĐÃ HẾT HẠN (hạn 0 giờ ngày kế tiếp từ mốc tham số), giờ Việt Nam;
    # người phải nộp là mọi nhân viên văn phòng theo `phai_nop`; nghỉ cả ngày đã duyệt không tính thiếu.
    now = gio_vn()
    today = now.date()
    het_han = [d for d in (today - timedelta(days=3), today - timedelta(days=2), today - timedelta(days=1), today)
               if d.weekday() != 6 and han_nop(db, d) <= now]
    days = het_han[-2:]
    last = days[-1] if days else today
    created = 0
    emps = nhan_vien_phai_nop(db)
    for e in emps:
        missing = [d for d in days if not nghi_ca_ngay(db, e.id, d) and not db.execute(select(DailyReport).where(DailyReport.user_id == e.user_id, DailyReport.report_date == d)).scalars().first()]
        if not missing: continue
        kind, level, roles, msg = ("bc_ngay_2", "red", "hcns,tgd", f"{e.full_name} thiếu báo cáo ngày 2 ngày liên tiếp ({', '.join(f'{d:%d/%m}' for d in missing)}) – chuyển HCNS") \
            if len(missing) >= 2 else ("bc_ngay_1", "warn", "tp_dh,gd_kd,ptgd_doan,ptgd_mkt,hcns", f"{e.full_name} chưa nộp báo cáo ngày {missing[0]:%d/%m} – nhắc nhở")
        ref = f"{e.code}:{last}"
        if not db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref)).scalars().first():
            db.add(Alert(kind=kind, level=level, ref=ref, message=msg, to_roles=roles)); created += 1
    db.commit()
    return created


# ====================== CA TRỰC PAGE (cổng 11) ======================
def shift_penalty(missed: int) -> tuple[float, bool]:
    """1–3 lượt: −100.000/lượt; 4–5: −200.000/lượt; ≥ 6: loại khỏi ca tháng sau (và −200.000/lượt). Chỉ trừ hoa hồng."""
    if missed <= 0: return 0.0, False
    if missed <= 3: return missed * 100_000, False
    if missed <= 5: return missed * 200_000, False
    return missed * 200_000, True


def shift_penalties_for_month(db: Session, y: int, m: int) -> dict[int, tuple[float, int, bool]]:
    """{employee_id: (tiền phạt, tổng lượt sót, bị loại ca)} theo tháng."""
    out: dict[int, tuple[float, int, bool]] = {}
    for s in db.execute(select(PageShift)).scalars():
        if s.shift_date.year == y and s.shift_date.month == m and s.missed:
            pen, out_flag = shift_penalty(s.missed)
            p, n, f = out.get(s.employee_id, (0.0, 0, False))
            out[s.employee_id] = (p + pen, n + s.missed, f or out_flag)
    return out


# ====================== ĐỀ NGHỊ CHI – LỆNH CHI (R3) ======================
def tour_budget(db: Session, t: Tour) -> float:
    pax = max(t.planned_pax, R.booked_pax(t))
    return (t.fixed_cost or 0) + (t.var_cost_per_pax or 0) * pax


def tour_cashflow(db: Session, t: Tour) -> dict:
    """Bảng dòng tiền tour: đã thu, đã chi, còn phải chi, tiền còn lại, lợi nhuận dự kiến; cảnh báo đỏ khi chi vượt thu."""
    revenue = sum((b.amount or 0) - (b.discount or 0) for b in t.bookings)
    collected = sum((r.amount or 0) for r in db.execute(select(Receipt).join(Booking).where(Booking.tour_id == t.id, Receipt.status != "huy")).scalars())
    reqs = db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.status != "tu_choi")).scalars().all()
    paid = sum((r.amount or 0) for r in reqs if r.status == "da_chi")
    committed = sum((r.amount or 0) for r in reqs if r.status in ("cho_chi",))
    pending = sum((r.amount or 0) for r in reqs if r.status in ("cho_tp", "cho_kt", "cho_duyet"))
    budget = tour_budget(db, t)
    total_cost = paid + committed + pending
    return {"tour_id": t.id, "code": t.code, "name": t.name, "status": t.status, "revenue": revenue, "collected": collected, "paid": paid, "committed": committed,
            "pending": pending, "cash_left": collected - paid - committed, "budget": budget, "over_budget": total_cost > budget + 1,
            "expected_profit": revenue - total_cost, "red": paid + committed > collected, "requests": len(reqs)}


def _next_code(db: Session) -> str:
    # Số lấy theo SỐ LỚN NHẤT đã cấp cho đúng tiền tố này, không phải số dòng cả bảng —
    # xem `services/ma_tu_sinh.py` cho ba chỗ hỏng của lối đếm cũ.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, PaymentRequest, f"DC{date.today():%y%m}-", 4)


# ══════════════════════════════════════════════════════════════════════════════════════════
# NGƯỠNG DUYỆT CHI — "dưới mốc TGĐ, từ mốc trở lên CHỦ TỊCH" (Đợt F1)
# ══════════════════════════════════════════════════════════════════════════════════════════
NGUONG_CHU_TICH_KEY = "nguong_chu_tich_duyet_chi"

CHUA_CHOT_NGUONG = (
    "CHƯA CHỐT NGƯỠNG DUYỆT CHI. Mức tiền mà từ đó trở lên lệnh chi do Chủ tịch duyệt nằm ở tham "
    f"số `{NGUONG_CHU_TICH_KEY}` trên màn hình Tham số, và nó mở bằng HAI CHỮ KÝ. Chưa có người ký "
    "mức ấy thì không duyệt được khoản nào: rỗng nghĩa là CHƯA AI CHỐT, không phải là không có mốc."
)


def nguong_chu_tich_dang_hieu_luc(db: Session) -> float | None:
    """Mốc tiền đang hiệu lực. `None` = CHƯA CHỐT.

    ĐỌC BẰNG `get_param_text`, KHÔNG `get_param`. Giá trị mặc định của khóa này là RỖNG, và
    `get_param` làm `float("")` — nổ `ValueError` ngay ở chỗ không ai bắt, trên một endpoint mà mọi
    vai trò đều gọi. Cùng khuôn với `thue_tncn.ky_bat_dau()`, vì cùng một loại công tắc: phép tính
    viết được bằng mã, còn MỐC thì phải có người ký.
    """
    try:
        v = (R.get_param_text(db, NGUONG_CHU_TICH_KEY) or "").strip()
    except KeyError:
        return None
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        # Giá trị có mà không đọc ra số: đóng về phía CHẶN. Cửa `POST /params` đã ép `float()` nên
        # chỉ một lần sửa thẳng cơ sở dữ liệu mới vào được đây — và lúc ấy chặn là đúng.
        return None


LOAI_CHI_MOT_TRONG_HAI = ("tra_ncc_thu_ho",)
# KS-16d — loại MÁY TỰ LẬP khi Kế toán chốt đơn khách sạn / đặt bàn. Người không lập tay được; bước xác nhận bộ phận
# và bước Kế toán kiểm do ROBOT kế toán làm (`don_ks_vtd.robot_kiem_de_nghi`), không ai bấm thay.
LOAI_CHI_MAY_LAP = ("tra_ncc_thu_ho",)


def cap_duyet(db: Session, r: PaymentRequest) -> dict:
    """MỘT chỗ duy nhất trả lời câu "khoản này ai duyệt".

    BỐN NƠI ĐỌC: `step` (ai bấm được), `pr_out` (dòng "ai bấm tiếp"), nhãn trên cửa lập, và hàng
    đợi chờ duyệt ở `dashboard`.

    VÌ SAO PHẢI LÀ MỘT HÀM. Lỗi 13/9/2026 và lại 10/10/2026 cùng một hình: hai chỗ tự suy ra cùng
    một câu trả lời theo hai cách rồi lệch nhau — cửa mở mà biển đề đóng. Trước bản này hàng đợi
    của Chủ tịch lọc `two_signatures == True` còn `step` hỏi một câu khác hẳn; hai câu khác nhau về
    cùng một hồ sơ là chỗ hỏng, không phải một tiện lợi. Hàm có tên thì bộ kiểm đọc được và phép
    thử canh được.

    MARKETING CŨNG ĐI QUA ĐÂY từ Đợt F1b. Trước đó nó có nhánh riêng — một chữ ký P.TGĐ Marketing
    ở mọi mức tiền — và hàm này cố ý không áp cho nó. Nay chữ ký của P.TGĐ là bước `confirm` (duyệt
    nội dung), còn bước `approve` là LỆNH CHI và đi đúng mốc chung như mọi loại chi.
    """
    # KS-16d — Chủ tịch chốt 31/10/2026: trả khách sạn / nhà hàng tiền thu hộ (số đã khóa lúc Kế toán chốt)
    # KHÔNG theo mốc tiền. TGĐ và Chủ tịch ĐỀU có nút, MỘT TRONG HAI bấm là xong; người kia chỉ còn thấy.
    # Mọi mức tiền, kể cả khi chưa chốt mốc.
    # Đội xe v3.3 (Chủ tịch 10/11/2026): mọi đề xuất chi đội xe do CHỦ TỊCH duyệt, mọi mức tiền, không theo mốc.
    if getattr(r, "category", "") == "chi_doi_xe":
        return {"nguong": None, "nguon": "chu_tich_doi_xe", "chua_chot": False, "tren_moc": None,
                "mot_trong_hai": False, "can_tgd": False, "can_chutich": True, "ai": "Chủ tịch", "ly_do": ""}
    if getattr(r, "category", "") in LOAI_CHI_MOT_TRONG_HAI:
        return {"nguong": None, "nguon": "loai_chi", "chua_chot": False, "tren_moc": None, "mot_trong_hai": True,
                "can_tgd": True, "can_chutich": True, "ai": "TGĐ hoặc Chủ tịch", "ly_do": ""}
    nguong, nguon = r.nguong_duyet_ap_dung, "ho_so"
    if nguong is None:
        # Hồ sơ lập TRƯỚC bản nâng cấp này không có ô ấy. Lấy mốc đang hiệu lực — sự thật tốt nhất
        # đọc được — và `step` ghi nó xuống hồ sơ đúng lúc duyệt, nên lần đọc sau không đổi nữa.
        nguong, nguon = nguong_chu_tich_dang_hieu_luc(db), "tham_so"
    if nguong is None:
        return {"nguong": None, "nguon": "chua_chot", "chua_chot": True, "tren_moc": None,
                "can_tgd": False, "can_chutich": False, "ai": "", "ly_do": CHUA_CHOT_NGUONG}
    nguong = float(nguong)
    tren_moc = float(r.amount or 0) >= nguong
    # `two_signatures` = NGOÀI DỰ TOÁN (cổng 15). Lý do KHÁC với mốc tiền.
    #
    # ĐỔI Ở ĐỢT LG2, Chủ tịch chốt 11/10/2026: chi ngoài dự toán cần chữ ký TRƯỞNG PHÒNG và TGĐ,
    # và chữ ký trưởng phòng CHÍNH LÀ bước xác nhận bộ phận đã có (`cho_tp`, ghi vào ô `tp_by`) —
    # không bắt ai bấm thêm lần nữa. Nên cờ này KHÔNG còn cộng thêm chữ ký Chủ tịch; nó chỉ còn
    # giữ TGĐ ở lại kể cả khi khoản nằm trên mốc.
    #
    # BẢNG SỰ THẬT SAU ĐỢT NÀY — Chủ tịch đã xem đúng bảng này trước khi chốt:
    #
    #     trong dự toán, dưới mốc : TGĐ
    #     trong dự toán, từ mốc   : Chủ tịch
    #     NGOÀI dự toán, dưới mốc : trưởng phòng (bước `cho_tp`) + TGĐ
    #     NGOÀI dự toán, TỪ MỐC   : trưởng phòng + TGĐ + CHỦ TỊCH      ← ba chữ ký
    #
    # DÒNG CUỐI LÀ CHỖ CHỦ TỊCH CHỌN SIẾT, KHÔNG NỚI. Câu hỏi đặt ra là "khoản 300 triệu ngoài dự
    # toán ai ký", ba lựa chọn là (theo mốc → Chủ tịch) / (luôn là TGĐ) / (cả hai), và Chủ tịch
    # chọn CẢ HAI. Thiếu dòng ấy thì một khoản ngoài dự toán 300 triệu lại NHẸ HƠN cùng khoản ấy
    # trong dự toán — ngoại lệ dễ hơn lệ thường là chỗ người ta sẽ đi vòng qua.
    can_tgd = bool(r.two_signatures) or not tren_moc
    can_chutich = tren_moc
    ai = " + ".join(t for t in (("Chủ tịch" if can_chutich else ""), ("TGĐ" if can_tgd else "")) if t)
    return {"nguong": nguong, "nguon": nguon, "chua_chot": False, "tren_moc": tren_moc,
            "can_tgd": can_tgd, "can_chutich": can_chutich, "ai": ai, "ly_do": ""}


def vai_ky_duoc(db: Session, r: PaymentRequest) -> list[str]:
    """Vai nào ĐANG Ở CẤP DUYỆT của hồ sơ này — tức vai nào màn hình được vẽ nút bấm cho.

    VÌ SAO HÀM NÀY PHẢI CÓ. `web/app/expenses/page.tsx` tự suy ra cùng câu trả lời bằng tay:
        role === "tgd" || (role === "chutich" && r.two_signatures)
    Đó là ĐÚNG cái cờ sai mà đợt này sửa ở máy chủ, nên nếu để nguyên thì sau F1 màn hình sai cả
    hai đầu: TGĐ thấy nút trên khoản từ mốc trở lên rồi bấm vào nhận 422, còn Chủ tịch KHÔNG có
    nút trên khoản ông phải ký. Cửa mở biển đề đóng, lần thứ tư, và lần này là biển.
    Nên máy chủ TRẢ RA danh sách vai, màn hình chỉ đọc. Một chỗ suy, nhiều chỗ đọc.

    CHỦ TỊCH TOÀN QUYỀN KHÔNG NẰM TRONG DANH SÁCH NÀY khi khoản ở dưới mốc. Toàn quyền
    (06/9/2026) là một ĐƯỜNG VƯỢT, không phải đường mặc định: máy chủ vẫn nhận chữ ký của ông,
    nhưng màn hình không mời ông bấm — đúng điều Chủ tịch chốt 10/10/2026, "dưới 100 triệu TGĐ
    duyệt nhưng Chủ tịch vẫn phải thấy". Thấy, không phải bấm.

    RỖNG nghĩa là KHÔNG AI bấm được lúc này: khoản Marketing chưa ai giữ vai `ptgd_mkt`, hoặc
    chưa chốt mốc. Màn hình phải nói ra chứ không vẽ một danh sách rỗng trong im lặng.
    """
    if r.status != "cho_duyet":
        return []
    # Marketing KHÔNG còn nhánh riêng ở đây (Đợt F1b): bước duyệt của nó nay là LỆNH CHI, theo
    # mốc chung. Chữ ký nội dung của P.TGĐ Marketing nằm ở bước `confirm`, không ở đây.
    c = cap_duyet(db, r)
    return ([] if c["chua_chot"]
            else [v for v, co in (("chutich", c["can_chutich"]), ("tgd", c["can_tgd"])) if co])


def create_request(db: Session, u: User, data: dict) -> PaymentRequest:
    cat = data["category"]
    if cat not in CATEGORY_CONFIRMER: raise ValueError("Loại chi không hợp lệ")
    if cat in LOAI_CHI_MAY_LAP and not data.get("_may_lap"):
        raise ValueError("Đề nghị trả NCC tiền thu hộ do máy tự lập khi Kế toán chốt đơn — không lập tay")
    # Tài xế mở được đúng MỘT loại, và chỉ cho chính mình. Chặn ở đây chứ không chỉ ở cửa API: cửa
    # API nói ai gõ được, chỗ này nói gõ được CÁI GÌ — và chỗ thứ hai là chỗ còn đúng khi mai kia có
    # thêm một cửa khác gọi vào cùng hàm này.
    if u.role == "tai_xe" and cat not in LOAI_CHI_TAI_XE_TU_LAP:
        raise ValueError("Tài xế chỉ lập được đề nghị tạm ứng của chính mình. Đề nghị sửa chữa do "
                         "Giám đốc đội xe lập sau khi có báo giá – báo hư hỏng cho đội xe trước.")
    t = db.get(Tour, data.get("tour_id")) if data.get("tour_id") else None
    if cat in ("chi_tour", "hoan_tien", "tam_ung") and not t:
        raise ValueError("Chi phí tour / hoàn tiền / tạm ứng bắt buộc gắn mã tour (cổng 14)")
    # Hai loại của đội xe CỐ Ý không bắt mã tour. Một xe hỏng giữa đường thì hỏng của chiếc xe, không
    # phải của một chuyến; và tiền đi đường của tài xế có thể rơi vào ngày không chạy tour nào. Bắt mã
    # tour ở đây là bắt người lập chọn đại một mã, và một mã chọn đại thì mọi báo cáo lãi lỗ theo tour
    # sau đó đều sai mà không ai biết.
    if cat == "tam_ung" and t and t.status in ("da_dong_so", "kt_xac_nhan", "khoa"):
        raise ValueError("Tour đã đóng số quyết toán – không tạm ứng thêm")
    # BỐN Ô NGOẠI TỆ – Chủ tịch chốt 27/9/2026. Khoản ngoại tệ thì MÁY NHÂN ra `amount`; khoản đồng
    # Việt Nam đi đúng đường cũ. Kiểm đủ ô và phép nhân nằm ở `services/ngoai_te_chi.py` – một chỗ,
    # để cửa này và mọi cửa sau dùng cùng một luật.
    nt = NT.chuan_hoa(data)
    if (nt["amount"] or 0) <= 0: raise ValueError("Số tiền phải > 0")
    # Tạm ứng tài xế: người thụ hưởng LÀ người lập. Máy điền, không hỏi. Hỏi một ô mà câu trả lời
    # luôn giống nhau là cách chắc chắn nhất để người ta gõ bừa – và một ô "người thụ hưởng" gõ bừa
    # trên một đề nghị chi tiền mặt thì sau này không truy được tiền đã vào tay ai.
    if cat == "tam_ung_tai_xe" and not data.get("supplier_name"):
        data = {**data, "supplier_name": u.full_name or u.username}
    if not data.get("supplier_name"): raise ValueError("Thiếu nhà cung cấp / người thụ hưởng")
    dx = _chuan_doi_xe(db, u, data) if cat == "chi_doi_xe" else None
    if dx is not None:
        cu = _trung_doi_xe(db, data, nt["amount"])
        if cu is not None:
            raise ValueError(f"Đã có phiếu {cu.code} cùng chứng từ {cu.document_ref}, cùng số tiền và cùng bên nhận. "
                             "Nếu là lần bấm thứ hai thì phiếu cũ đã vào sổ; nếu là khoản khác thì gửi lại với ô «vẫn gửi dù trùng».")
    r = PaymentRequest(code=_next_code(db), category=cat, tour_id=t.id if t else None, supplier_name=data["supplier_name"], supplier_tax_code=data.get("supplier_tax_code", ""),
                       supplier_bank=data.get("supplier_bank", ""), amount=nt["amount"], description=data["description"], has_document=bool(data.get("has_document")),
                       document_ref=data.get("document_ref", ""), has_invoice=bool(data.get("has_invoice")), created_by=u.username,
                       company_id=t.company_id if t else None)
    # VPM-17 – ngày đến hạn, nếu người lập đã hẹn được với nhà cung cấp. Rỗng thì để rỗng: khoản này
    # sẽ hiện ở danh sách "đề nghị chi chưa có ngày đến hạn" để người lập quay lại gõ, chứ không bị
    # gán một ngày đoán.
    if data.get("ngay_den_han"):
        r.ngay_den_han = data["ngay_den_han"]
        r.ngay_den_han_boi, r.ngay_den_han_luc = u.username, datetime.now()
    # Bốn ô ngoại tệ đã qua kiểm. `tien_te` rỗng nghĩa là khoản đồng Việt Nam – ba ô còn lại để None.
    r.tien_te = nt["tien_te"]
    if dx is not None:
        from app.services.ket_qua_that import cong_ty_me
        r.doi_xe, r.company_id = dx, cong_ty_me(db)          # sổ VTD — Chủ tịch 10/11/2026
        # Chủ tịch chốt lại 10/11/2026: «GĐ đội xe đề xuất lên thẳng Chủ tịch duyệt, sau đó Kế toán chi».
        # GĐ gửi = bộ phận đã xác nhận; bỏ bước Kế toán kiểm trước duyệt — Kế toán kiểm chứng từ lúc CHI.
        r.status, r.tp_by = "cho_duyet", u.username
    r.so_tien_ngoai_te, r.ty_gia, r.ngay_ty_gia = nt["so_tien_ngoai_te"], nt["ty_gia"], nt["ngay_ty_gia"]
    # R3: xếp cấp duyệt
    if cat == "marketing":
        # ═══════════════════════════════════════════════════════════════════════════════════════
        # MARKETING ĐI HAI BƯỚC — CHỦ TỊCH CHỐT 10/10/2026 (Đợt F1b)
        # ═══════════════════════════════════════════════════════════════════════════════════════
        #
        # Bước 1: P.TGĐ Marketing duyệt NỘI DUNG / KẾ HOẠCH / NGÂN SÁCH — ở bước `confirm`, đúng ô
        #         `CATEGORY_CONFIRMER["marketing"]` vốn đã có.
        # Bước 2: LỆNH CHI — ở bước `approve`, theo mốc `nguong_chu_tich_duyet_chi` của Đợt F1:
        #         dưới mốc TGĐ ký, từ mốc trở lên Chủ tịch ký.
        #
        # ĐÂY LÀ MỘT BƯỚC SIẾT, ĐẢO LẠI MỘT BƯỚC NỚI CỦA CHÍNH CHỦ TỊCH NGÀY 23/9/2026. Luật cũ cho
        # mọi hồ sơ Marketing dừng ở một chữ ký P.TGĐ, không mốc tiền. Để làm được thế, chỗ này CẮT
        # BỎ bước bộ phận (`r.status = "cho_kt"` ngay lúc lập), lý do ghi rõ khi ấy: người xác nhận
        # bộ phận của Marketing CHÍNH LÀ P.TGĐ, mà ông đang ký ở cuối, nên giữ cả hai bước là bắt
        # một người bấm hai lần cho cùng một hồ sơ.
        #
        # NAY LÝ DO ẤY KHÔNG CÒN ĐÚNG: hai bước do HAI NGƯỜI khác nhau bấm. Nên việc phải làm không
        # phải thêm một trạng thái mới, mà là GỠ phần ngoại lệ ấy để Marketing đi chung đúng một
        # đường với mọi loại chi. Dòng `r.status = "cho_kt"` ở cuối khối này đã được gỡ.
        #
        # NHỮNG THỨ KHÔNG ĐỔI, và đừng ai gỡ tiếp vì tưởng cùng một mạch:
        #   · Kế toán vẫn kiểm chứng từ và mã số thuế trước khi chi — kiểm soát tài chính và điều
        #     kiện trừ thuế, không phải một cấp duyệt.
        #   · Phép kiểm hai ô hạng mục/chiến dịch ngay dưới đây (TC-80, 24/9) — giữ nguyên.
        #   · Cờ `over_budget` vẫn tính và vẫn ghi vào mô tả, và vẫn chỉ NÓI chứ không CHẶN. Bản
        #     đầu của đợt này viết rằng nó "lại có răng" vì Marketing đi qua nhánh chung — SAI, và
        #     phép thử bắt được trước khi đẩy: `two_signatures` là một cờ riêng, chỉ bật ở đúng một
        #     chỗ (`chi_tour`/`tam_ung` vượt dự toán TOUR), và F1b không đụng tới chỗ bật cờ ấy.
        #     CÒN LẠI CHO CHỦ TỊCH QUYẾT: có nối lại cổng 15 cho Marketing không. Hệ quả phải cân
        #     trước khi nối: `over_budget` của Marketing còn bật cả khi CHƯA GẮN HẠNG MỤC.
        #   · `han_muc_mkt` = 5.000.000đ vẫn là một tham số CHẾT, không nối lại. Mốc tiền của
        #     Marketing từ nay là mốc chung `nguong_chu_tich_duyet_chi`, không phải một mốc riêng.
        if u.role == "ptgd_mkt":
            raise ValueError(
                "P.TGĐ Marketing không lập hồ sơ đề xuất chi (Chủ tịch chốt 23/9/2026, giữ nguyên "
                "10/10/2026). Lý do nay là: chính P.TGĐ xác nhận nội dung ở bước một, nên nếu ông "
                "lập hồ sơ thì một người bấm hai lần cho cùng một hồ sơ. Giao cho một nhân viên "
                "Marketing lập.")
        # KIỂM HAI Ô, 24/9/2026. Trước đây hai ô này không màn hình nào gửi nên chưa ai gõ sai
        # được; nay phiếu chi có ô chọn thật, và một mã hạng mục gõ sai thì cổng ngân sách đối
        # chiếu với một hạn mức không tồn tại rồi im lặng cho qua. Rỗng vẫn hợp lệ – rỗng nghĩa là
        # CHƯA GẮN, và phần dưới đã xử riêng trường hợp ấy.
        from app.models.marketing import Campaign as _CD, HANG_MUC as _HM
        muc = (data.get("marketing_muc") or "").strip()
        if muc and muc not in _HM:
            raise ValueError(f"Hạng mục marketing không hợp lệ: {muc}")
        cd_id = data.get("campaign_id")
        if cd_id and db.get(_CD, int(cd_id)) is None:
            raise ValueError(f"Không có chiến dịch id {cd_id}.")
        r.marketing_muc = muc
        r.campaign_id = int(cd_id) if cd_id else None
        # Vượt phần còn lại của HẠNG MỤC thì vẫn ghi cờ và vẫn ghi vào mô tả — chỉ không còn bật hai
        # chữ ký. Chưa gán hạng mục cũng tính là ngoài dự toán: không đối chiếu được với hạn mức nào,
        # và chưa lập ngân sách không phải là ngân sách vô hạn.
        if r.marketing_muc:
            from app.services import marketing as MK
            con, vi_sao = MK.con_lai_hang_muc(db, r.marketing_muc, r.company_id)
            if (r.amount or 0) > con:
                r.over_budget = True
                r.description = (r.description + f" [ngoài dự toán: còn {con:,.0f}đ theo {vi_sao}]")[:300]
        else:
            r.over_budget = True
        # KHÔNG đặt trạng thái ở đây nữa. Hồ sơ Marketing bắt đầu ở `cho_tp` như mọi loại chi
        # khác, và bước `cho_tp` CHÍNH LÀ bước một của Chủ tịch: P.TGĐ Marketing duyệt nội dung.
        # Dòng `r.status = "cho_kt"` cũ nằm ở đây là phần ngoại lệ 23/9 mà Đợt F1b gỡ.
    if t and cat in ("chi_tour", "tam_ung"):
        cf = tour_cashflow(db, t)
        if (cf["paid"] or 0) + cf["committed"] + cf["pending"] + (r.amount or 0) > (cf["budget"] or 0) + 1:
            r.over_budget, r.two_signatures = True, True
    # NGƯỠNG DUYỆT CHI — CHỐT Ở LÚC LẬP và ghi xuống hồ sơ (Đợt F1). Xem `models/ops.py` tại cột
    # `nguong_duyet_ap_dung` để biết vì sao không đọc tham số lúc duyệt.
    #
    # RỖNG Ở ĐÂY NGHĨA LÀ CHƯA CHỐT MỐC, và `step` sẽ CHẶN chứ không cho qua. Lập VẪN ĐƯỢC: chặn ở
    # cửa lập là bắt người lập chịu một việc chưa ký của cấp trên, và hồ sơ không lập được thì
    # không có gì đếm ra để ai đó đi ký. Nhãn trả về từ cửa lập nói rõ hồ sơ sẽ nằm chờ.
    #
    # MARKETING CŨNG GHI Ô NÀY từ Đợt F1b: lệnh chi Marketing nay đi qua đúng mốc chung. Trước
    # F1b ô này cố ý để rỗng cho Marketing vì mốc tiền không áp vào nó — câu ấy không còn đúng.
    r.nguong_duyet_ap_dung = nguong_chu_tich_dang_hieu_luc(db)
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "lap_de_nghi_chi", f"dc:{r.code}", after={"loai": cat, "tour": t.code if t else "", "ncc": r.supplier_name, "so_tien": r.amount,
                                                                              "ngoai_du_toan": r.over_budget, "hai_chu_ky": r.two_signatures})
    db.commit(); db.refresh(r)
    return r


# ══════════════════════════════════════════════════════════════════════════════════════════
# HAI CỬA TIỀN — ai kiểm chứng từ, ai bấm ĐÃ CHI. Chủ tịch chốt 09/10/2026 (NL-2).
#
# Trước bản này cả hai viết cứng `u.role != "ketoan"` ngay trong thân hàm, nên chúng KHÔNG đi
# qua `require_roles` và bộ kiểm quyền không đọc được. Khai thành hai hằng số có tên là để
# máy đọc được và phép thử canh được — cùng lý do `toan_quyen()` phải là một HÀM chứ không
# phải một hằng số nhập tay (xem deps.py, bài học 13/9/2026).
#
# HAI DANH SÁCH RỜI NHAU VÀ PHẢI RỜI NHAU. Giao của chúng là `ketoan` — vai nền, còn ở lại vì
# hôm nay chỉ có họ làm cả hai việc. Khi đã có người cho từng vai mới thì `ketoan` ra khỏi
# một trong hai, và lúc ấy lớp chống gian lận mới đứng được bằng chính bảng phân quyền. Cho
# tới lúc ấy, thứ giữ nó là `ks_tach_nhiem` so theo NGƯỜI (Đợt E2a), không phải bảng này.
VAI_KIEM_CHUNG_TU = ("ketoan", "ketoan_tt", "ketoan_truong")
VAI_GHI_DA_CHI = ("ketoan", "thu_quy")


def step(db: Session, u: User, r: PaymentRequest, action: str, reason: str = "",
         hinh_thuc_tt: str = "", so_tien: float | None = None) -> str:
    """confirm (người phụ trách bộ phận) → check (Kế toán) → approve (TGĐ; +Chủ tịch nếu 2 chữ ký) → pay (Kế toán) | reject."""
    # ── Đợt E2a: tách bạch trách nhiệm THEO NGƯỜI ──────────────────────────────────────
    # Lớp cũ ở ngay dưới (`u.role != "ketoan"`) so hai VAI. Đo 19/9/2026: 6 người giữ từ hai
    # tài khoản trở lên, nên so vai là chưa đủ. Kiểm TRƯỚC khi làm, ghi dấu chân SAU khi làm
    # xong — ghi trước là tạo dấu chân cho một bước chưa xảy ra.
    from app.services import ks_tach_nhiem as _KTN
    _pv = f"dc:{r.id}"
    _BUOC_CUA_DE_NGHI_CHI = {"confirm": "xac_nhan_bo_phan", "check": "ke_toan_kiem",
                             "approve": "duyet_lenh_chi", "pay": "da_chi"}
    _b = _BUOC_CUA_DE_NGHI_CHI.get(action, "")
    if _b:
        _kq = _KTN.kiem(db, _pv, _b, u)
        if _kq["chan"]:
            raise ValueError(_kq["vi_pham"][0]["thong_diep"] if _kq["vi_pham"]
                             else _kq["thong_diep_thieu_ma"])
    if action == "tra_bo_sung":
        _tra_bo_sung(db, u, r, reason)
        msg = f"Đã trả {r.code} về người lập để bổ sung: {reason.strip()}"
    elif action == "reject":
        if r.status in ("da_chi", "tu_choi"): raise ValueError("Không từ chối được")
        if (r.da_chi_tien or 0) > 0:
            raise ValueError(f"{r.code} đã chi {float(r.da_chi_tien):,.0f}đ – không từ chối được phần đã ra")
        if not reason.strip(): raise ValueError("Từ chối phải có lý do")
        r.status, r.reject_reason = "tu_choi", reason
        msg = f"Đã từ chối {r.code}: {reason}"
    elif action in ("confirm", "check") and r.category in LOAI_CHI_MAY_LAP:
        raise ValueError("Bước này do robot kế toán làm. Robot dừng vì thiếu thông tin NCC thì bổ sung NCC rồi bấm "
                         "«Robot kiểm lại».")
    elif action == "confirm":
        if r.status != "cho_tp": raise ValueError("Không ở bước xác nhận bộ phận")
        if u.role not in CATEGORY_CONFIRMER[r.category] and u.role not in ("tgd",) and not toan_quyen(u): raise ValueError("Không đúng người phụ trách bộ phận")
        r.status, r.tp_by = "cho_kt", u.username
        msg = f"{r.code}: bộ phận đã xác nhận, chuyển Kế toán kiểm tra"
    elif action == "check":
        if r.status != "cho_kt": raise ValueError("Không ở bước Kế toán kiểm tra")
        if u.role not in VAI_KIEM_CHUNG_TU and not toan_quyen_ke_ca_tach_bach(u, db): raise ValueError("Chỉ Kế toán kiểm tra")
        _kiem_chung_tu_mst(db, r)
        r.status, r.kt_by = "cho_duyet", u.username
        # Câu này là thứ Kế toán đọc rồi đi gõ đúng người, nên nó phải hỏi CHÍNH hàm mà bước duyệt
        # hỏi. Bản trước suy từ `two_signatures`, tức luôn viết "TGĐ" cho mọi khoản trong dự toán —
        # kể cả khoản 300 triệu mà TGĐ không ký được.
        _c = cap_duyet(db, r)
        _ai = _c["ai"] or "KHÔNG AI — chưa chốt ngưỡng duyệt chi"
        msg = f"{r.code}: Kế toán đã kiểm tra, trình {_ai} duyệt lệnh chi"
    elif action == "approve":
        if r.status != "cho_duyet": raise ValueError("Không ở bước duyệt")
        # NHÁNH RIÊNG CỦA MARKETING ĐÃ GỠ — Đợt F1b. Từ 23/9/2026 tới 10/10/2026 chỗ này cho
        # P.TGĐ Marketing ký một mình ở mọi mức tiền rồi `return` sớm. Nay Marketing đi chung đúng
        # đường này: P.TGĐ đã duyệt nội dung ở bước `confirm`, còn LỆNH CHI theo mốc chung.
        #
        # `return` sớm ấy là lý do nhánh cũ phải tự gọi `_KTN.ghi_buoc` — nó nhảy qua đoạn cuối
        # hàm, nơi MỌI hành động đều để lại dấu chân qua `_b`. Gỡ nhánh đi thì dấu chân vẫn còn,
        # và còn đúng một lần thay vì hai.
        # ═══════════════════════════════════════════════════════════════════════════════════
        # AI ĐƯỢC BẤM — Đợt F1. Ba dòng cũ nằm ở đây đã nói NGƯỢC luật:
        #     if u.role == "tgd": ...
        #     elif u.role == "chutich" and r.two_signatures: ...
        #     else: raise ValueError("Chỉ TGĐ (và Chủ tịch khi cần 2 chữ ký) duyệt chi")
        # Một khoản 300 triệu TRONG dự toán có `two_signatures = False`, nên Chủ tịch rơi vào `else`
        # và BỊ TỪ CHỐI, còn TGĐ lại ký được. Đúng ngược hai đầu.
        # ═══════════════════════════════════════════════════════════════════════════════════
        cd = cap_duyet(db, r)
        if cd["chua_chot"]:
            raise ValueError(cd["ly_do"])
        # NGƯỜI LẬP KHÔNG TỰ KÝ LỆNH CHI CỦA CHÍNH MÌNH — Đợt F1b.
        # Phép chặn này trước đây CHỈ nằm trong nhánh riêng của Marketing. Gỡ nhánh ấy mà không bù
        # vào là mở một lỗ; và đo kỹ thì nhánh chung vốn đã hở sẵn cho SÁU loại chi còn lại. Cửa
        # lập không khai `tgd`/`chutich`, nhưng Chủ tịch toàn quyền đi qua được, nên hôm nay ông
        # lập một đề nghị rồi tự ký là đi lọt. Đây là tách bạch trách nhiệm, không phải phân quyền:
        # toàn quyền 06/9/2026 KHÔNG nới chỗ này, cùng lẽ với `ks_toan_quyen.py`.
        if (r.created_by or "") == u.username:
            raise ValueError("Người lập không tự ký lệnh chi của chính mình. Hồ sơ này do "
                             f"`{r.created_by}` lập — phải người khác ở cấp duyệt bấm.")
        # MỘT NGƯỜI KHÔNG KÝ THAY CẢ HAI VAI — Đợt LG2, Chủ tịch chốt 11/10/2026.
        #
        # Khoản NGOÀI DỰ TOÁN từ mốc trở lên cần cả TGĐ và Chủ tịch. Trước bản này không chỗ nào
        # kiểm hai chữ ký ấy có phải hai NGƯỜI: hồ sơ chỉ ghi cờ đã-ký, không ghi tên. Đo
        # 19/9/2026: 220 tài khoản, SÁU người giữ từ hai tài khoản trở lên — nên một người đăng
        # nhập lần lượt hai tài khoản là ký đủ. Hàng rào `test_lg2_8` của chính đợt này tìm ra
        # chỗ hở, sau khi em đã trình Chủ tịch một danh sách SÁU cửa còn thiếu nó.
        #
        # Chủ tịch chọn BỊT, với lý do nêu nguyên văn: đây là tiền ra thật.
        #
        # Gọi `kiem_tra_mot_nguoi_hai_vai` chứ không gọi `kiem_tra_nguoi_ky`: hàm sau kiểm CẢ vai,
        # mà vai được ký ở cửa này tính theo từng hồ sơ (`cap_duyet`) và Chủ tịch đi qua bằng
        # toàn quyền để ký thay cấp TGĐ — lúc ấy vai ông không nằm trong danh sách mà vẫn đúng
        # luật, nên gọi hàm kia là chặn nhầm ông.
        _da_ky = _CK.doc_nguoi_da_ky(r.nguoi_da_ky)
        _CK.kiem_tra_mot_nguoi_hai_vai(u, _da_ky)
        # NGƯỜI XÁC NHẬN BỘ PHẬN KHÔNG DUYỆT — Đợt LG3, Chủ tịch chốt 11/10/2026, cho MỌI hồ sơ.
        #
        # Bước `cho_tp` là CHỮ KÝ THỨ NHẤT của hồ sơ ngoài dự toán (Chủ tịch chốt cùng ngày:
        # chữ ký trưởng phòng chính là bước xác nhận bộ phận đã có). Mà bước ấy TGĐ cũng bấm
        # được, và phép chặn cũ chỉ so với NGƯỜI LẬP — nên TGĐ xác nhận rồi tự duyệt là một mình
        # ký cả hai vế, và hồ sơ trông vẫn đủ chữ ký.
        #
        # Áp cho mọi hồ sơ chứ không riêng hồ sơ ngoài dự toán: một người vừa xác nhận bộ phận
        # vừa duyệt thì bước xác nhận không còn là một lớp nào cả, dù hồ sơ to hay nhỏ.
        if (r.tp_by or "") == u.username:
            raise ValueError(
                f"`{u.username}` đã xác nhận bộ phận cho hồ sơ này – người xác nhận bộ phận "
                "không duyệt lệnh chi của chính hồ sơ ấy. Hai bước phải là hai người.")
        if r.nguong_duyet_ap_dung is None:
            # Hồ sơ cũ: ghi mốc đang áp xuống hồ sơ NGAY LÚC DUYỆT, để lần đọc sau không đổi nữa.
            r.nguong_duyet_ap_dung = cd["nguong"]
        _vai_ky = ""
        if u.role == "tgd" and cd["can_tgd"]:
            _vai_ky = "tgd"
            r.signed_tgd = True
        elif toan_quyen(u):
            # Chủ tịch. Trên mốc thì đây LÀ cấp duyệt của khoản; dưới mốc thì ông ký thay cấp TGĐ
            # theo luật toàn quyền 06/9/2026 — ghi vào ô TGĐ vì đó là cấp duyệt của khoản này, còn
            # AI BẤM thì nhật ký kiểm toán ghi tên, nên vẫn truy được trách nhiệm.
            if cd["can_chutich"]:
                _vai_ky = "chutich"
                r.signed_chutich = True
            else:
                _vai_ky = "tgd"
                r.signed_tgd = True
        elif cd["nguon"] == "loai_chi":
            raise ValueError("Khoản trả NCC tiền thu hộ do TGĐ hoặc Chủ tịch duyệt (mọi mức tiền).")
        elif cd["nguon"] == "chu_tich_doi_xe":
            raise ValueError("Đề xuất chi đội xe do Chủ tịch duyệt (Chủ tịch chốt 10/11/2026).")
        else:
            raise ValueError(
                f"Khoản {float(r.amount or 0):,.0f}đ "
                + ("TỪ MỐC" if cd["tren_moc"] else "dưới mốc")
                + f" {cd['nguong']:,.0f}đ → {cd['ai']} duyệt."
                + (" Khoản NGOÀI DỰ TOÁN cần cả hai chữ ký (cổng 15)." if r.two_signatures else "")
                + " Vai của anh/chị không ở cấp duyệt của khoản này.")
        # Ghi TÊN người vừa ký vào ô `nguoi_da_ky`. Ghi sau khi đặt cờ, và ghi theo vai mà chữ
        # ký vừa rơi vào — chứ không theo `u.role`: Chủ tịch ký thay cấp TGĐ thì chữ ký nằm ở ô
        # TGĐ (tiền lệ Đợt F1), và ô này phải nói đúng ô nào đã có tên ai.
        if _vai_ky:
            _da_ky[_vai_ky] = u.username
            r.nguoi_da_ky = _CK.ghi_nguoi_da_ky(_da_ky)
        if cd.get("mot_trong_hai"):
            done = bool(r.signed_tgd or r.signed_chutich)
        else:
            done = (r.signed_tgd or not cd["can_tgd"]) and (r.signed_chutich or not cd["can_chutich"])
        if done:
            r.status, r.approved_by, r.approved_at = "cho_chi", u.username, datetime.now()
            _post_liability(db, r)
            msg = f"{r.code} đã duyệt – lập lệnh chi chờ Kế toán thực hiện trên ngân hàng"
        else:
            msg = f"{r.code}: đã ký {'TGĐ' if r.signed_tgd else 'Chủ tịch'}, chờ chữ ký còn lại"
    elif action == "pay":
        if r.status != "cho_chi": raise ValueError("Chưa có lệnh chi được duyệt")
        if u.role not in VAI_GHI_DA_CHI and not toan_quyen_ke_ca_tach_bach(u, db): raise ValueError("Chỉ Kế toán ghi nhận đã chi")
        # KS-16d — Chủ tịch chốt 31/10/2026: MỌI loại chi phải có UNC / phiếu chi tải lên trước khi bấm «Đã chi».
        if r.category == "chi_doi_xe":
            _kiem_chung_tu_mst(db, r)         # đội xe: Kế toán kiểm chứng từ lúc chi (Chủ tịch 10/11/2026)
        if not co_unc(db, r):
            raise ValueError(f"Tải ủy nhiệm chi (UNC) / phiếu chi của {r.code} lên trước rồi mới bấm «Đã chi»")
        # ĐỢT R4c-3 02/11/2026 — HÌNH THỨC THANH TOÁN LÀ MỘT Ô, KHÔNG PHẢI MỘT PHÉP ĐOÁN.
        #
        # Dòng cũ ở đây: `paid_method = "tien_mat" if reason.lower().startswith("tm")`. `reason` là
        # ô "mã giao dịch / lý do" Kế toán gõ TAY, nên vế tiền của bút toán chi được quyết bằng HAI
        # CHỮ CÁI ĐẦU của một ô văn bản tự do:
        #
        #     "TM-0231"        -> tiền mặt
        #     "Tien mat 0231"  -> CHUYỂN KHOẢN   (tiền ra khỏi quỹ, sổ ghi giảm tiền gửi)
        #     "Chi TM cho NCC" -> CHUYỂN KHOẢN
        #     "tmp ghi chu"    -> TIỀN MẶT
        #
        # Không gì kêu lên ở cả bốn trường hợp.
        #
        # VÀ KHÔNG CÓ MẶC ĐỊNH. Ô trống là CHƯA CÓ SỐ — quy ước 4 ngày 09/9/2026. Một mặc định
        # `chuyen_khoan` ở đây y hệt phép đoán cũ, chỉ im lặng hơn: nó cũng điền một con số không
        # ai nói, và lần này còn không có hai chữ cái nào để lần ra vì sao.
        _ht = (hinh_thuc_tt or "").strip()
        if not _ht:
            raise ValueError(
                "Thiếu hình thức thanh toán. Vế tiền của bút toán chi phụ thuộc hẳn vào nó "
                "(tiền mặt ghi 1111, qua ngân hàng ghi 1121), nên không có ô này thì không đoán "
                "được và cũng không được đoán. Chọn hình thức rồi bấm lại.")
        if _ht not in HINH_THUC_TT or _ht == "chua_tt":
            raise ValueError(
                f"Hình thức thanh toán không hợp lệ: {_ht!r}. "
                + ("Một khoản đang ghi nhận ĐÃ CHI thì không thể là chưa thanh toán."
                   if _ht == "chua_tt"
                   else "Chọn một trong: " + ", ".join(k for k in HINH_THUC_TT if k and k != "chua_tt")))
        # CHI MỘT PHẦN — Chủ tịch duyệt 10/11/2026, mọi đề nghị chi. Rỗng = chi hết phần còn lại (như cũ).
        _con = round(float(r.amount or 0) - float(r.da_chi_tien or 0), 2)
        _lan = _con if so_tien is None else round(float(so_tien), 2)
        if _lan <= 0:
            raise ValueError("Số tiền chi lần này phải lớn hơn 0")
        if _lan > _con + 0.5:
            raise ValueError(f"Chi lần này {_lan:,.0f}đ vượt phần còn phải chi {_con:,.0f}đ "
                             f"(được duyệt {float(r.amount or 0):,.0f}đ, đã chi {float(r.da_chi_tien or 0):,.0f}đ)")
        _lan = min(_lan, _con)
        # Mỗi lần chi một UNC / phiếu chi: lần thứ hai mà vẫn chỉ có tệp của lần đầu thì chặn.
        if so_unc(db, r) <= len(r.lan_chi or []):
            raise ValueError(f"Lần chi thứ {len(r.lan_chi or []) + 1} của {r.code} cần UNC / phiếu chi riêng – "
                             "tải lên trước rồi mới bấm «Đã chi»")
        _bo_but = list(r.entry_ids or [])
        r.paid_method = _ht
        _post_payment(db, r, _lan, reason)
        _moi = [e for e in (r.entry_ids or []) if e not in _bo_but]
        r.lan_chi = list(r.lan_chi or []) + [{"so_tien": _lan, "luc": datetime.now().isoformat(timespec="seconds"),
                                              "ma_gd": reason[:120], "hinh_thuc": _ht, "boi": u.username,
                                              "entry_id": _moi[0] if _moi else None}]
        r.da_chi_tien = round(float(r.da_chi_tien or 0) + _lan, 2)
        r.paid_ref = reason
        if (r.da_chi_tien or 0) < float(r.amount or 0) - 0.5:
            con_lai = float(r.amount or 0) - (r.da_chi_tien or 0)
            msg = (f"{r.code}: đã chi một phần {_lan:,.0f}đ (lần {len(r.lan_chi)}), "
                   f"còn {con_lai:,.0f}đ chờ chi")
            if _b:
                _KTN.ghi_buoc(db, _pv, _b, u)
            R.audit(db, u.username, u.role, "de_nghi_chi_pay_mot_phan", f"dc:{r.code}",
                    after={"lan": len(r.lan_chi), "so_tien": _lan, "da_chi": r.da_chi_tien, "ma_gd": reason})
            db.commit()
            return msg
        r.status, r.paid_at = "da_chi", datetime.now()
        if r.category in LOAI_CHI_MAY_LAP:
            # KS-16e (Chủ tịch 31/10/2026): đã chi trả khách sạn / nhà hàng → ghi doanh thu hoa hồng của đơn gốc.
            from app.services import don_ks_vtd as _KS
            _KS.sau_khi_chi_tra_ncc(db, u, r)
        if r.category == "hoan_tien":
            from app.services import bookings as BK
            BK.on_refund_paid(db, r)
        msg = (f"{r.code} đã chi ({r.paid_ref or 'không có mã GD'})" if len(r.lan_chi or []) <= 1
               else f"{r.code} đã chi đủ sau {len(r.lan_chi)} lần ({float(r.da_chi_tien):,.0f}đ)")
    else:
        raise ValueError("Hành động không hợp lệ")
    if _b:
        _KTN.ghi_buoc(db, _pv, _b, u)   # bước đã xong, để lại dấu chân
    R.audit(db, u.username, u.role, f"de_nghi_chi_{action}", f"dc:{r.code}", after={"trang_thai": r.status, "ly_do": reason})
    db.commit()
    return msg


# ══════════════════════════════════════════════════════════════════════════════════════════
# TRẢ BỔ SUNG — Chủ tịch duyệt bản xem trước 10/11/2026, áp cho MỌI đề nghị chi 05-TT.
#
# Khác «Từ chối»: từ chối là hết đường, người lập phải lập hồ sơ mới (mã mới, mất dấu hồ sơ cũ).
# Trả bổ sung là hồ sơ VỀ NGƯỜI LẬP, giữ nguyên mã, người lập sửa rồi gửi lại. Chữ ký cũ XOÁ — một
# chữ ký đặt trên bản trước không phải chữ ký cho bản đã sửa — nhưng bản trước và ai đã ký vẫn nằm
# trong `lan_tra`, nên đọc lại được hồ sơ đã đổi gì giữa hai lần ký.
# ══════════════════════════════════════════════════════════════════════════════════════════
O_SUA_DUOC = ("supplier_name", "supplier_tax_code", "supplier_bank", "amount", "description",
              "has_document", "document_ref", "has_invoice", "ngay_den_han")


def _ai_tra_duoc(db: Session, u: User, r: PaymentRequest) -> bool:
    """Ai đang giữ bước hiện tại thì trả được — đúng người sẽ bấm bước ấy."""
    if r.status == "cho_tp":
        return u.role in CATEGORY_CONFIRMER.get(r.category, ()) or u.role == "tgd" or toan_quyen(u)
    if r.status == "cho_kt":
        return u.role in VAI_KIEM_CHUNG_TU or toan_quyen_ke_ca_tach_bach(u, db)
    if r.status == "cho_duyet":
        return u.role in vai_ky_duoc(db, r) or u.role == "tgd" or toan_quyen(u)
    if r.status == "cho_chi":
        return u.role in VAI_GHI_DA_CHI + VAI_KIEM_CHUNG_TU or toan_quyen_ke_ca_tach_bach(u, db)
    return False


def _tra_bo_sung(db: Session, u: User, r: PaymentRequest, ly_do: str) -> None:
    if not (ly_do or "").strip():
        raise ValueError("Trả bổ sung phải ghi lý do – người lập cần biết bổ sung cái gì")
    if r.status not in ("cho_tp", "cho_kt", "cho_duyet", "cho_chi"):
        raise ValueError(f"{r.code} đang ở bước không trả bổ sung được")
    if r.category in LOAI_CHI_MAY_LAP:
        raise ValueError("Hồ sơ do máy tự lập không có người lập để trả về – bổ sung NCC rồi bấm «Robot kiểm lại»")
    if (r.da_chi_tien or 0) > 0:
        raise ValueError(f"{r.code} đã chi {float(r.da_chi_tien):,.0f}đ – phần còn lại chi tiếp, không trả về được")
    if r.entry_ids:
        raise ValueError(f"{r.code} đã ghi công nợ lúc duyệt – trả về thì sổ còn treo bút toán cũ. "
                         "Dùng «Từ chối» rồi lập hồ sơ mới.")
    if not _ai_tra_duoc(db, u, r):
        raise ValueError("Chỉ người đang giữ bước hiện tại của hồ sơ mới trả bổ sung được")
    ban_truoc = {k: (getattr(r, k).isoformat() if hasattr(getattr(r, k), "isoformat") else getattr(r, k))
                 for k in O_SUA_DUOC}
    ban_truoc["chu_ky"] = {"tp_by": r.tp_by, "kt_by": r.kt_by, "nguoi_da_ky": r.nguoi_da_ky,
                           "signed_tgd": r.signed_tgd, "signed_chutich": r.signed_chutich}
    if r.doi_xe:
        ban_truoc["doi_xe"] = dict(r.doi_xe)
    r.lan_tra = list(r.lan_tra or []) + [{"luc": datetime.now().isoformat(timespec="seconds"), "boi": u.username,
                                          "vai": u.role, "ly_do": ly_do.strip()[:300], "buoc": r.status,
                                          "ban_truoc": ban_truoc}]
    r.status = "tra_bo_sung"
    r.tp_by = r.kt_by = r.approved_by = ""
    r.signed_tgd = r.signed_chutich = False
    r.nguoi_da_ky, r.approved_at = "", None
    r.reject_reason = ly_do.strip()[:300]


def gui_lai(db: Session, u: User, r: PaymentRequest, data: dict) -> str:
    """Người lập sửa hồ sơ bị trả rồi gửi lại — đi lại tuyến duyệt từ đầu, giữ nguyên mã."""
    if r.status != "tra_bo_sung":
        raise ValueError(f"{r.code} không ở trạng thái trả bổ sung")
    if (r.created_by or "") != u.username and not toan_quyen(u):
        raise ValueError(f"Chỉ người lập (`{r.created_by}`) gửi lại hồ sơ của mình")
    doi = {}
    for k in O_SUA_DUOC:
        if k not in data or data[k] is None:
            continue
        v = data[k]
        if k == "amount":
            if r.tien_te:
                raise ValueError("Khoản ngoại tệ: số tiền do máy nhân từ ngoại tệ × tỷ giá – từ chối rồi lập lại")
            v = round(float(v), 2)
            if v <= 0:
                raise ValueError("Số tiền phải lớn hơn 0")
        elif isinstance(getattr(r, k), str):
            v = str(v).strip()[:300 if k == "description" else 160]
        if getattr(r, k) != v:
            doi[k] = v
            setattr(r, k, v)
    if not r.supplier_name.strip() or not r.description.strip():
        raise ValueError("Thiếu tên người nhận hoặc nội dung")
    if r.category == "chi_doi_xe" and isinstance(data.get("doi_xe"), dict):
        dx = dict(r.doi_xe or {})
        for k in ("can_cu", "hen_bo_sung", "ghi_chu_kiem_tra"):
            if k in data["doi_xe"]:
                dx[k] = str(data["doi_xe"][k] or "").strip()[:200]
        r.doi_xe = dx
    if "amount" in doi:
        # Số tiền đổi thì xét lại «ngoài dự toán» như lúc lập — một khoản tăng tiền phải đi qua đúng cổng ấy.
        t = db.get(Tour, r.tour_id) if r.tour_id else None
        if t and r.category in ("chi_tour", "tam_ung"):
            cf = tour_cashflow(db, t)
            r.over_budget = r.two_signatures = (
                (cf["paid"] or 0) + cf["committed"] + cf["pending"] + (r.amount or 0) > (cf["budget"] or 0) + 1)
    if r.category == "chi_doi_xe":
        r.status, r.tp_by = "cho_duyet", u.username      # GĐ gửi → Chủ tịch duyệt (10/11/2026)
    else:
        r.status = "cho_tp"
    r.reject_reason = ""
    if r.lan_tra:
        r.lan_tra = list(r.lan_tra[:-1]) + [{**r.lan_tra[-1], "gui_lai_luc": datetime.now().isoformat(timespec="seconds"),
                                             "da_sua": sorted(doi)}]
    R.audit(db, u.username, u.role, "de_nghi_chi_gui_lai", f"dc:{r.code}", after={"da_sua": doi, "lan": len(r.lan_tra or [])})
    db.commit()
    return f"Đã gửi lại {r.code}" + (f" (sửa: {', '.join(sorted(doi))})" if doi else " (không đổi ô nào)")


def so_unc(db: Session, r: PaymentRequest) -> int:
    """Số tệp UNC / phiếu chi còn hiệu lực — chi nhiều lần thì mỗi lần một tệp."""
    from app.models.attachments import Attachment
    return len(db.execute(select(Attachment.id).where(Attachment.doi_tuong == "de_nghi_chi",
                                                      Attachment.doi_tuong_id.in_((r.code, str(r.id))),
                                                      Attachment.loai == "unc", Attachment.thu_hoi.is_(False))).all())


def co_unc(db: Session, r: PaymentRequest) -> bool:
    """Có tệp loại «unc» còn hiệu lực gắn với đề nghị chi (đối tượng de_nghi_chi, theo mã)."""
    from app.models.attachments import Attachment
    return db.execute(select(Attachment.id).where(Attachment.doi_tuong == "de_nghi_chi",
                                                  Attachment.doi_tuong_id.in_((r.code, str(r.id))),
                                                  Attachment.loai == "unc", Attachment.thu_hoi.is_(False))).first() is not None


def _post_liability(db: Session, r: PaymentRequest):
    """Duyệt đề nghị chi có hóa đơn/hợp đồng NCC → ghi nhận công nợ: Nợ (TK chi phí chi tiết theo
    bảng khai `services/tk_chi_tiet.py`) – Có 331. Hoàn tiền khách: không ghi tại bước này."""
    from app.services import tk_chi_tiet as TKCT
    khoa = CATEGORY_TK_KHOA.get(r.category)
    if not khoa: return
    t = db.get(Tour, r.tour_id) if r.tour_id else None
    try:
        # `chon` nằm TRONG `try` cùng với `post_entry`, không đứng trước nó: một tham số tài khoản
        # bị ký sai phải rơi vào đúng đường «ghi sổ thất bại» đã có (ghi nhật ký, Kế toán thấy và
        # sửa tham số), chứ không được làm hỏng cả bước DUYỆT đề nghị chi của người đang ký.
        acc = TKCT.chon(db, khoa)
        e = ACC.post_entry(db, "robot", "robot", date.today(), f"Đề nghị chi {r.code} – {r.supplier_name}: {r.description[:80]}",
                           [{"account": acc, "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id, "note": "" if r.has_invoice else "Không hóa đơn – không được trừ TNDN"},
                            {"account": "331", "credit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}], "de_nghi_chi", f"dc:{r.code}", r.tour_id, nghiep_vu="de_nghi_chi")
        r.entry_ids = list(r.entry_ids or []) + [e.id]
    except ValueError as ex:
        R.audit(db, "robot", "robot", "ghi_so_that_bai", f"dc:{r.code}", after={"ly_do": str(ex)})


def _post_payment(db: Session, r: PaymentRequest, so_tien: float | None = None, ma_gd: str | None = None):
    # ĐỢT R4c-3 02/11/2026 — VẾ TIỀN GHI Ở CẤP CHI TIẾT, KHÔNG Ở CẤP CHA.
    #
    # Dòng cũ ghi `"111"` / `"112"`. Đo được: cả hai là tài khoản CHA (`111` "Tiền mặt",
    # `112` "Tiền gửi không kỳ hạn"); `1111` / `1121` mới là tài khoản chi tiết. Và `post_entry`
    # NHẬN bút toán vào tài khoản cha, không chặn — nên việc này im lặng suốt.
    #
    # Hậu quả đo được, chạy thật `cap_dinh_khoan.ngoai_luat` với đúng hai bút toán chỉ khác vế tiền:
    #
    #     331 / 112   -> NGOÀI LUẬT      vì quy tắc TRA_NCC khai vế Có là 1121, và phép đối chiếu
    #                                    so bằng tiền tố: "112".startswith("1121") là SAI
    #     331 / 1121  -> trong luật
    #
    # Tức là MỌI khoản đã chi đều rơi vào rổ "định khoản ngoài luật" — cái rổ Kế toán trưởng mở ra
    # để tìm bút toán sai. Một rổ mà mọi khoản chi đều rơi vào thì nó không còn chỉ ra chỗ phải
    # nhìn nữa. Thêm nữa: sổ chi tiết tiền gửi và số dư đầu kỳ đều làm việc ở cấp `1121`, nên tiền
    # ghi ở cấp `112` không hiện ra ở đó.
    #
    # ĐỌC `HTTT_QUA_TIEN_MAT` CHỨ KHÔNG SO `== "tien_mat"`: séc tiền mặt vẫn rút trên tài khoản
    # ngân hàng nên nó thuộc bên 112x, và luật ấy đã khai MỘT LẦN ở `models/hach_toan.py`. So chuỗi
    # ở đây là khai lại nó lần thứ hai, và lần này sai.
    cash = "1111" if r.paid_method in HTTT_QUA_TIEN_MAT else "1121"
    # Chi một phần (10/11/2026): mỗi lần chi ghi đúng số của lần ấy. Rỗng = cả khoản (đường cũ).
    tien = float(r.amount or 0) if so_tien is None else float(so_tien)
    gd = r.paid_ref if ma_gd is None else ma_gd
    if r.category == "hoan_tien":
        lines = [{"account": "131", "debit": tien, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": tien, "partner": r.supplier_name}]
    elif r.category == "tam_ung":   # tạm ứng HDV/NCC trước tour: Nợ 141 – Có 111/112; hoàn ứng khi Kế toán xác nhận quyết toán
        lines = [{"account": "141", "debit": tien, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": tien, "partner": r.supplier_name}]
    elif r.category == "chi_doi_xe" and r.doi_xe:
        # Đội xe v3.3: không ghi công nợ lúc duyệt, nên lúc chi ghi THẲNG tài khoản đã khóa trên phiếu —
        # 627 chi phí tháng phát sinh, 141 tạm ứng, 331 trả chủ xe. Ghi Nợ 331 cho khoản chưa từng ghi Có 331
        # là để một số dư treo ở 331 mà không ai nợ ai.
        lines = [{"account": r.doi_xe.get("tk") or "627", "debit": tien, "partner": r.supplier_name},
                 {"account": cash, "credit": tien, "partner": r.supplier_name}]
    else:
        lines = [{"account": "331", "debit": tien, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": tien, "partner": r.supplier_name}]
    try:
        e = ACC.post_entry(db, "robot", "robot", date.today(), f"Chi {r.code} – {r.supplier_name}" + (f" (GD {gd})" if gd else "")
                           + (f" – lần {len(r.lan_chi or []) + 1}" if so_tien is not None and (r.lan_chi or tien < float(r.amount or 0) - 0.5) else ""), lines, "lenh_chi", (f"dc:{r.code}" if not r.lan_chi else f"dc:{r.code}/lan{len(r.lan_chi) + 1}"), r.tour_id, nghiep_vu="chi_tien")
        r.entry_ids = list(r.entry_ids or []) + [e.id]
    except ValueError as ex:
        R.audit(db, "robot", "robot", "ghi_so_that_bai", f"dc:{r.code}", after={"ly_do": str(ex)})


def posted_tour_cost(db: Session, tour_id: int) -> float:
    """Chi phí tour đã ghi 154 qua đề nghị chi đã duyệt (để quyết toán chỉ ghi phần chênh lệch vào 335)."""
    return sum((r.amount or 0) for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == tour_id, PaymentRequest.category.in_(["chi_tour", "tam_ung"]),
                                                                          PaymentRequest.status.in_(["cho_chi", "da_chi"]))).scalars())


def match_outgoing(db: Session, content: str, amount: float) -> PaymentRequest | None:
    """R1/R2: giao dịch tiền ra có mã DCyymm-nnnn và đúng số tiền → tự ghi 'đã chi' cho lệnh chi đang chờ."""
    import re
    m = re.search(r"DC\s?(\d{4})-?(\d{4})", content.replace(" ", ""), re.IGNORECASE)
    if not m: return None
    code = f"DC{m.group(1)}-{m.group(2)}"
    r = db.execute(select(PaymentRequest).where(PaymentRequest.code == code, PaymentRequest.status == "cho_chi")).scalars().first()
    if r and abs((r.amount or 0) - amount) < 1:
        return r
    return None
