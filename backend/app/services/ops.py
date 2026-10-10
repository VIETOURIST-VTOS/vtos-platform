"""Vận hành: báo cáo ngày (Điều 12), ca trực page (cổng 11), đề nghị chi – lệnh chi NCC (robot R3, cổng 14/15).

R3 chỉ tính toán, gắn cảnh báo và xếp cấp duyệt; quyết định duyệt là người. Không robot nào chuyển tiền.
"""
from datetime import date, datetime, timedelta, time
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User, Alert
from app.models.hr import Employee
from app.models.ops import DailyReport, PageShift, PaymentRequest
from app.models.payments import Receipt
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
             "hint": "Không có phát sinh thì ghi 'không'."},
}
PART_TITLES = {1: "VIỆC ĐÃ LÀM HÔM NAY", 2: "SỐ LIỆU TRONG NGÀY", 3: "VIỆC NGÀY MAI", 4: "VƯỚNG MẮC – ĐỀ XUẤT"}


def dept_of_user(db: Session, u: User) -> str:
    """Phòng dùng cho mẫu báo cáo: theo hồ sơ nhân sự, rồi theo vai trò."""
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e and e.department in DEPT_FORMS: return e.department
    if u.department in DEPT_FORMS: return u.department
    return {"nv_kd": "kd_le", "tn_kd": "kd_le", "tp_kd": "kd_le", "gd_kd": "kd_le", "ptgd_doan": "kd_doan", "nv_dh": "dieu_hanh", "tp_dh": "dieu_hanh", "nv_mkt": "marketing", "ptgd_mkt": "marketing",
            "cntt": "cntt", "ketoan": "ketoan", "hcns": "hcns"}.get(u.role, "kd_le")


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
    for k in DEPT_FORMS.get(dept, {}).get("fields", []) or list(p2.keys()):
        lines.append(f"{k}: {str(p2.get(k, '')).strip() or 'không'}")
    lines += ["", f"PHẦN 3 — {PART_TITLES[3]}", p3.strip() or "(trống)", "", f"PHẦN 4 — {PART_TITLES[4]}", p4.strip() or "không", "",
              f"— {u.full_name}" + (f" · Mã NV {staff_code}" if staff_code else "") + f" · {name}"]
    return subject, "\n".join(lines)

CATEGORY_ACCOUNT = {"chi_tour": "154", "marketing": "641", "hanh_chinh": "642"}   # tam_ung: ghi 141 khi chi, hoàn ứng vào 154 khi Kế toán xác nhận quyết toán
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
                      "sua_chua_xe": ("gd_doi_xe",), "tam_ung_tai_xe": ("gd_doi_xe",)}

# Loại chi tài xế được TỰ LẬP. Đúng một loại, và cố ý.
#
# `sua_chua_xe` KHÔNG có trong danh sách này: lúc tài xế phát hiện xe hỏng thì CHƯA CÓ số tiền và
# CHƯA CÓ garage — hai thứ `create_request` bắt buộc phải có. Bắt tài xế lập đề nghị chi lúc ấy là
# bắt họ bịa ra một con số, đúng thứ ranh giới 09/9/2026 cấm. Đề nghị sửa chữa do Giám đốc đội xe
# lập SAU KHI có báo giá. Việc "báo hư hỏng" là một việc khác, chưa có cửa, và nó chưa có cửa là
# một việc CÒN THIẾU chứ không phải một việc đã xong.
LOAI_CHI_TAI_XE_TU_LAP = ("tam_ung_tai_xe",)

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
    """Điểm nháp 0–10: Phần 1 ≥ 20 ký tự = 3; Phần 2 điền ≥ 2/3 số trường = 2 (điền hết = 3); Phần 3 ≥ 20 ký tự = 2; nộp trước 20h = 2."""
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
    if not r.on_time: notes.append("nộp sau 20:00")
    return float(min(score, 10)), "; ".join(notes) or "Đủ 4 phần, đúng giờ"


def submit_report(db: Session, u: User, d: date, p1: str, p2: str, p3: str, p4: str) -> DailyReport:
    if d > date.today():
        raise ValueError("Không nộp báo cáo cho ngày tương lai")
    r = db.execute(select(DailyReport).where(DailyReport.user_id == u.id, DailyReport.report_date == d)).scalars().first()
    if r and r.reviewed_by:
        raise ValueError("Báo cáo đã được trưởng phòng chấm – không sửa")
    now = datetime.now()
    if r is None:
        r = DailyReport(user_id=u.id, report_date=d); db.add(r)
    r.part1_done, r.part2_numbers, r.part3_issues, r.part4_plan = p1, p2, p3, p4
    r.submitted_at = now
    r.on_time = d == now.date() and now.time() <= REPORT_DEADLINE   # nộp bù ngày trước = trễ
    r.robot_score, r.robot_note = robot_score(r)
    db.flush()
    R.audit(db, u.username, u.role, "nop_bao_cao_ngay", f"report:{u.username}:{d}", after={"diem_robot": r.robot_score, "dung_gio": r.on_time})
    db.commit(); db.refresh(r)
    return r


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
    """Robot: thiếu 1 ngày → nhắc nhở; 2 ngày liên tiếp → chuyển HCNS (cảnh báo đỏ). Chạy sau 20h hoặc sáng hôm sau."""
    today = date.today()
    now = datetime.now()
    last = today if now.time() > REPORT_DEADLINE else today - timedelta(days=1)
    days = [d for d in (last - timedelta(days=1), last) if d.weekday() != 6]
    created = 0
    emps = db.execute(select(Employee).where(Employee.active == True, Employee.department.in_(NO_TIMESHEET_DEPTS), Employee.user_id != None)).scalars().all()
    for e in emps:
        missing = [d for d in days if not db.execute(select(DailyReport).where(DailyReport.user_id == e.user_id, DailyReport.report_date == d)).scalars().first()]
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


def create_request(db: Session, u: User, data: dict) -> PaymentRequest:
    cat = data["category"]
    if cat not in CATEGORY_CONFIRMER: raise ValueError("Loại chi không hợp lệ")
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
    r.so_tien_ngoai_te, r.ty_gia, r.ngay_ty_gia = nt["so_tien_ngoai_te"], nt["ty_gia"], nt["ngay_ty_gia"]
    # R3: xếp cấp duyệt
    if cat == "marketing":
        # ═══════════════════════════════════════════════════════════════════════════════════════
        # MARKETING ĐI MỘT CHỮ KÝ — CHỦ TỊCH CHỐT 23/9/2026, xác nhận lại 24/9/2026
        # ═══════════════════════════════════════════════════════════════════════════════════════
        #
        # Luật: MỌI đề xuất chi Marketing do P.TGĐ Marketing duyệt là xong. Không có mốc tiền, không
        # có nhánh. Dữ liệu vẫn đẩy lên TGĐ và Chủ tịch — nhưng để XEM, không phải để bấm.
        #
        # ĐÂY LÀ MỘT BƯỚC NỚI, KHÔNG PHẢI MỘT BƯỚC SIẾT. Trước hôm nay Marketing có HAI phanh, và
        # quyết định này gỡ cả hai:
        #   · `han_muc_mkt` = 5.000.000đ — từ mức ấy trở lên phải thêm chữ ký Chủ tịch
        #   · vượt phần còn lại của hạng mục ngân sách — cũng bật hai chữ ký
        # Chủ tịch đã được nêu rõ cả hai phanh này cùng hệ quả (một hồ sơ 500 triệu, hoặc một hồ sơ
        # vượt dự toán, nay cũng chỉ cần một chữ ký) và vẫn chốt bỏ. Ghi ra đây để người sửa sau
        # biết đây là quyết định có chủ đích, không phải một chỗ sót.
        #
        # NHỮNG THỨ KHÔNG BỊ GỠ, và đừng ai gỡ tiếp vì tưởng là cùng một mạch:
        #   · Kế toán vẫn kiểm chứng từ và mã số thuế trước khi chi — đó là kiểm soát tài chính và
        #     điều kiện trừ thuế, không phải một cấp duyệt.
        #   · Phép kiểm hai ô hạng mục/chiến dịch ngay dưới đây (TC-80, 24/9) — giữ nguyên.
        #   · Cờ `over_budget` vẫn được tính và vẫn ghi vào mô tả. Nó thôi CHẶN, nhưng không thôi
        #     NÓI: người duyệt và hai màn hình lãnh đạo vẫn thấy khoản nào đang vượt dự toán.
        #   · Người lập không tự duyệt, và P.TGĐ Marketing không lập hồ sơ (chặn ngay dưới đây).
        if u.role == "ptgd_mkt":
            raise ValueError(
                "P.TGĐ Marketing không lập hồ sơ đề xuất chi, chỉ duyệt (Chủ tịch chốt 23/9/2026). "
                "Vì mọi hồ sơ Marketing dừng ở một chữ ký của P.TGĐ, nếu chính người ấy lập thì hồ "
                "sơ không còn ai ký được ngoài chính mình. Giao cho một nhân viên Marketing lập.")
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
        # Bỏ luôn bước "bộ phận xác nhận": người xác nhận bộ phận của Marketing CHÍNH LÀ P.TGĐ MKT
        # (xem CATEGORY_CONFIRMER), mà nay ông ấy là người DUYỆT ở cuối. Giữ cả hai bước là bắt cùng
        # một người bấm hai lần cho cùng một hồ sơ — thủ tục chứ không phải kiểm soát.
        r.status = "cho_kt"
    if t and cat in ("chi_tour", "tam_ung"):
        cf = tour_cashflow(db, t)
        if (cf["paid"] or 0) + cf["committed"] + cf["pending"] + (r.amount or 0) > (cf["budget"] or 0) + 1:
            r.over_budget, r.two_signatures = True, True
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


def step(db: Session, u: User, r: PaymentRequest, action: str, reason: str = "") -> str:
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
    if action == "reject":
        if r.status in ("da_chi", "tu_choi"): raise ValueError("Không từ chối được")
        if not reason.strip(): raise ValueError("Từ chối phải có lý do")
        r.status, r.reject_reason = "tu_choi", reason
        msg = f"Đã từ chối {r.code}: {reason}"
    elif action == "confirm":
        if r.status != "cho_tp": raise ValueError("Không ở bước xác nhận bộ phận")
        if u.role not in CATEGORY_CONFIRMER[r.category] and u.role not in ("tgd",) and not toan_quyen(u): raise ValueError("Không đúng người phụ trách bộ phận")
        r.status, r.tp_by = "cho_kt", u.username
        msg = f"{r.code}: bộ phận đã xác nhận, chuyển Kế toán kiểm tra"
    elif action == "check":
        if r.status != "cho_kt": raise ValueError("Không ở bước Kế toán kiểm tra")
        if u.role not in VAI_KIEM_CHUNG_TU and not toan_quyen_ke_ca_tach_bach(u, db): raise ValueError("Chỉ Kế toán kiểm tra")
        if not r.has_document: raise ValueError("Thiếu chứng từ đính kèm (hợp đồng/hóa đơn/báo giá) – không chuyển duyệt")
        if r.category not in ("hoan_tien", "tam_ung") and not r.supplier_tax_code: raise ValueError("NCC chưa có MST – phải xác nhận trước khi thanh toán")
        r.status, r.kt_by = "cho_duyet", u.username
        msg = f"{r.code}: Kế toán đã kiểm tra, trình {'Chủ tịch + TGĐ' if r.two_signatures else 'TGĐ'} duyệt"
    elif action == "approve":
        if r.status != "cho_duyet": raise ValueError("Không ở bước duyệt")
        if r.category == "marketing":
            # Một chữ ký, và là chữ ký của P.TGĐ Marketing (Chủ tịch chốt 23/9/2026).
            # Chủ tịch toàn quyền vẫn ký được — đó là luật 13/9, không phải ngoại lệ mở riêng ở đây.
            if not (u.role == "ptgd_mkt" or toan_quyen(u)):
                raise ValueError("Chi Marketing chỉ P.TGĐ Marketing duyệt (Chủ tịch chốt 23/9/2026)")
            # Người lập không tự duyệt. Cửa lập đã chặn P.TGĐ MKT, nhưng Chủ tịch toàn quyền thì lập
            # được — nên ranh giới này phải đứng ở ĐÂY mới kín, không chỉ ở cửa lập.
            if (r.created_by or "") == u.username:
                raise ValueError("Người lập không tự duyệt hồ sơ của chính mình")
            r.status, r.approved_by, r.approved_at = "cho_chi", u.username, datetime.now()
            _post_liability(db, r)
            _KTN.ghi_buoc(db, _pv, "duyet_lenh_chi", u)
            R.audit(db, u.username, u.role, "de_nghi_chi_approve", f"dc:{r.code}",
                    after={"trang_thai": r.status, "mot_chu_ky_mkt": True, "ngoai_du_toan": r.over_budget})
            db.commit()
            return (f"{r.code} đã duyệt – lập lệnh chi chờ Kế toán thực hiện"
                    + (" (khoản này NGOÀI DỰ TOÁN)" if r.over_budget else ""))
        if u.role == "tgd": r.signed_tgd = True
        elif u.role == "chutich" and r.two_signatures: r.signed_chutich = True
        else: raise ValueError("Chỉ TGĐ (và Chủ tịch khi cần 2 chữ ký) duyệt chi")
        done = r.signed_tgd and (r.signed_chutich or not r.two_signatures)
        if done:
            r.status, r.approved_by, r.approved_at = "cho_chi", u.username, datetime.now()
            _post_liability(db, r)
            msg = f"{r.code} đã duyệt – lập lệnh chi chờ Kế toán thực hiện trên ngân hàng"
        else:
            msg = f"{r.code}: đã ký {'TGĐ' if r.signed_tgd else 'Chủ tịch'}, chờ chữ ký còn lại"
    elif action == "pay":
        if r.status != "cho_chi": raise ValueError("Chưa có lệnh chi được duyệt")
        if u.role not in VAI_GHI_DA_CHI and not toan_quyen_ke_ca_tach_bach(u, db): raise ValueError("Chỉ Kế toán ghi nhận đã chi")
        r.status, r.paid_at, r.paid_ref = "da_chi", datetime.now(), reason
        r.paid_method = "tien_mat" if reason.lower().startswith("tm") else "chuyen_khoan"
        _post_payment(db, r)
        if r.category == "hoan_tien":
            from app.services import bookings as BK
            BK.on_refund_paid(db, r)
        msg = f"{r.code} đã chi ({r.paid_ref or 'không có mã GD'})"
    else:
        raise ValueError("Hành động không hợp lệ")
    if _b:
        _KTN.ghi_buoc(db, _pv, _b, u)   # bước đã xong, để lại dấu chân
    R.audit(db, u.username, u.role, f"de_nghi_chi_{action}", f"dc:{r.code}", after={"trang_thai": r.status, "ly_do": reason})
    db.commit()
    return msg


def _post_liability(db: Session, r: PaymentRequest):
    """Duyệt đề nghị chi có hóa đơn/hợp đồng NCC → ghi nhận công nợ: Nợ 154/641/642 – Có 331 (hoàn tiền khách: không ghi tại bước này)."""
    acc = CATEGORY_ACCOUNT.get(r.category)
    if not acc: return
    t = db.get(Tour, r.tour_id) if r.tour_id else None
    try:
        e = ACC.post_entry(db, "robot", "robot", date.today(), f"Đề nghị chi {r.code} – {r.supplier_name}: {r.description[:80]}",
                           [{"account": acc, "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id, "note": "" if r.has_invoice else "Không hóa đơn – không được trừ TNDN"},
                            {"account": "331", "credit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}], "de_nghi_chi", f"dc:{r.code}", r.tour_id)
        r.entry_ids = list(r.entry_ids or []) + [e.id]
    except ValueError as ex:
        R.audit(db, "robot", "robot", "ghi_so_that_bai", f"dc:{r.code}", after={"ly_do": str(ex)})


def _post_payment(db: Session, r: PaymentRequest):
    cash = "111" if r.paid_method == "tien_mat" else "112"
    if r.category == "hoan_tien":
        lines = [{"account": "131", "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": r.amount, "partner": r.supplier_name}]
    elif r.category == "tam_ung":   # tạm ứng HDV/NCC trước tour: Nợ 141 – Có 111/112; hoàn ứng khi Kế toán xác nhận quyết toán
        lines = [{"account": "141", "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": r.amount, "partner": r.supplier_name}]
    else:
        lines = [{"account": "331", "debit": r.amount, "partner": r.supplier_name, "tour_id": r.tour_id}, {"account": cash, "credit": r.amount, "partner": r.supplier_name}]
    try:
        e = ACC.post_entry(db, "robot", "robot", date.today(), f"Chi {r.code} – {r.supplier_name}" + (f" (GD {r.paid_ref})" if r.paid_ref else ""), lines, "lenh_chi", f"dc:{r.code}", r.tour_id)
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
