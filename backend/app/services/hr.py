"""Robot R6 – Nhân sự & Lương: tính thang lương f, hoa hồng, quỹ thưởng, quỹ visa, thù lao HDV, công tác phí tài xế
theo mục 6.4 Thiết kế v1.7 từ số liệu quyết toán Kế toán đã xác nhận (tháng quyết toán). Robot chỉ lập NHÁP.
Luồng: nháp → Kế toán xác nhận cơ sở → HCNS lập bảng lương → TGĐ ký lô → bút toán lương.
"""
import math
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User
from app.models.hr import Employee, VisaFile, GuideAssignment, Vehicle, DispatchOrder, Incident, PayrollRun
from app.services import rules as R
from app.services import accounting as ACC
from app.services import luong as L

# ---- Thang f bậc sàn KD Lẻ – Bảng B.1 chính thức (tham số thang_f_bang: "ngưỡng%:hệ số%", f1…f19 + trần) ----
def parse_f_table(text: str) -> list[tuple[float, float]]:
    """'65:0,70:0,…,1000:5' → [(0.65, 0.0), (0.70, 0.0), …, (10.0, 0.05)] – ngưỡng dưới của f1…f19 và trần."""
    out = []
    for part in text.split(","):
        if ":" not in part: continue
        a, b = part.split(":"); out.append((float(a) / 100, float(b) / 100))
    return sorted(out)


def f_rate(rev: float, moc: float, table: list[tuple[float, float]]) -> tuple[int, float]:
    """(bậc, hệ số) theo doanh thu tính chỉ tiêu / mốc; bậc sàn, không nội suy; dưới ngưỡng f1 → f0 = 0."""
    if moc <= 0: return 0, 0.0
    ratio = rev / moc; k, rate = 0, 0.0
    for i, (thr, r) in enumerate(table):
        if ratio >= thr: k, rate = i + 1, r
        else: break
    return k, rate


# Thang lương NV kinh doanh đoàn theo bình quân LN 3 tháng / mốc 30 triệu: f9…f0
DOAN_F = [(1.0, 1.0), (0.9, 0.95), (0.8, 0.88), (0.7, 0.80), (0.6, 0.71), (0.5, 0.61), (0.4, 0.50), (0.3, 0.38), (0.2, 0.26), (0.1, 0.13), (0.0, 0.0)]


def add_working_days(d: date, n: int) -> date:
    """Cộng n ngày làm việc (bỏ Chủ nhật; Thứ Bảy vẫn là ngày làm việc theo lịch Công ty)."""
    from datetime import timedelta
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() != 6: n -= 1
    return d


def moc_of(e: Employee, moc_hcm: float, moc_tinh: float) -> float:
    """Mốc chỉ tiêu theo văn phòng: HCM và Bình Dương (khách lẻ) 200 triệu; Cần Thơ và văn phòng tỉnh 120 triệu (B.2 = 60% HCM)."""
    return moc_hcm if e.office in ("hcm", "binhduong") else moc_tinh


def base_salary_le(emp: Employee, rev: float, moc: float, step_amt: float, cut: float) -> float:
    """Thang giảm lương Phụ lục C: dưới mốc mỗi bậc (20 triệu HCM / 12 triệu Cần Thơ) trừ 700.000 (NV), 800.000 (TL), 1.000.000 (TP), tới 0."""
    if rev >= moc:
        return emp.base_salary
    steps = math.ceil((moc - rev) / step_amt)
    return max(0.0, (emp.base_salary or 0) - steps * cut)


def month_tours(db: Session, y: int, m: int) -> list[Tour]:
    return [t for t in db.execute(select(Tour).where(Tour.status.in_(["kt_xac_nhan", "khoa"]))).scalars()
            if t.kt_confirmed_at and t.kt_confirmed_at.year == y and t.kt_confirmed_at.month == m]


def incidents_of(db: Session, emp_id: int, y: int, m: int, min_level: int = 2) -> int:
    """Số sự vụ ĐÃ CÓ HIỆU LỰC (HCNS xác nhận + cấp có thẩm quyền duyệt, hết thời gian khiếu nại/khiếu nại bị bác), mức ≥ min_level, trong tháng."""
    return sum(1 for i in db.execute(select(Incident).where(Incident.employee_id == emp_id, Incident.level >= min_level, Incident.status == "hieu_luc")).scalars()
               if i.occurred_on.year == y and i.occurred_on.month == m)


def level3_tours(db: Session, y: int, m: int) -> set[tuple[int, int]]:
    """(employee_id, tour_id) có sự vụ mức 3 hiệu lực → không phát sinh hoa hồng của chính booking/đoàn đó."""
    return {(i.employee_id, i.tour_id) for i in db.execute(select(Incident).where(Incident.level >= 3, Incident.status == "hieu_luc", Incident.tour_id != None)).scalars()}


def compute_draft(db: Session, period: str, inputs: dict | None = None) -> tuple[list[dict], dict]:
    """Bản nháp thu nhập tháng theo từng người. Mỗi dòng: {ma, ten, phong, khoan[], luong_cb, bien_doi, tncn, thuc_nhan, ghi_chu}."""
    y, m = map(int, period.split("-"))
    tours = month_tours(db, y, m)
    emps = {e.id: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    by_user = {e.user_id: e for e in emps.values() if e.user_id}
    rows: dict[int, dict] = {}

    def row(e: Employee) -> dict:
        cd = L.che_do_cong(e)
        return rows.setdefault(e.id, {"ma": e.code, "ten": e.full_name, "phong": e.department, "chuc_vu": e.position, "hop_dong": e.contract_type,
                                      "che_do_cong": cd, "che_do_cong_ten": L.CHE_DO_LABEL[cd], "xac_dinh_luong": None,
                                      "luong_cb": 0.0, "khoan": [], "bien_doi": 0.0, "tncn": 0.0,
                                      "bhxh": 0.0, "bhxh_base": 0.0, "doan_phi": 0.0, "tru_su_vu": 0.0,
                                      "thu_nhap": 0.0, "khoan_tru": 0.0, "thuc_nhan": 0.0, "ghi_chu": []})

    def add(e: Employee, ten: str, tien: float, note: str = ""):
        r = row(e); r["khoan"].append({"ten": ten, "tien": round(tien), "ghi_chu": note}); r["bien_doi"] += round(tien)

    moc_hcm = R.get_param(db, "moc_chi_tieu_hcm"); moc_ct = R.get_param(db, "moc_chi_tieu_cantho")
    thr = R.get_param(db, "nguong_bien")
    phat_su_vu = R.get_param(db, "phat_su_vu")
    f_table = parse_f_table(R.get_param_text(db, "thang_f_bang"))
    l3 = level3_tours(db, y, m); emp_by_user = {e.user_id: e.id for e in emps.values()}
    from app.services.ops import shift_penalties_for_month
    shift_pen = shift_penalties_for_month(db, y, m)

    # ---------- BƯỚC 1: xác định mức lương cơ bản CỦA KỲ (Phụ lục đối chiếu 27/8/2026, mục 2.1) ----------
    # Thứ tự bắt buộc: xác định mức lương của kỳ → tính thu nhập → tính khoản trừ → đối soát.
    # Mức ghi trong hợp đồng là mức đầy đủ khi đạt chỉ tiêu, không phải mức chi cố định hằng tháng.
    inputs = inputs or {}
    try: mac_dinh_cong = R.get_param(db, "cong_chuan")
    except KeyError: mac_dinh_cong = 26          # công chuẩn chưa cài tham số – dùng 26, HCNS chốt lại
    cong_chuan = float(inputs.get("cong_chuan") or mac_dinh_cong)
    cong_thuc_te = inputs.get("cong_thuc_te") or {}
    for e in emps.values():
        if e.contract_type != "hdld":
            continue
        r = row(e); cd = L.che_do_cong(e)
        if cd == L.CHAM_CONG:
            ct = cong_thuc_te.get(e.code)
            xd = L.xac_dinh_theo_cong(e, cong_chuan, float(ct) if ct not in (None, "") else None)
            if xd.get("thieu_du_lieu"): r["ghi_chu"].append(xd["giai_thich"])
        else:
            xd = L.xac_dinh_co_dinh(e)
        r["xac_dinh_luong"] = xd
        r["luong_cb"] = round(xd["muc_ky"] * (0.85 if e.probation else 1.0))

    # ---------- Kinh doanh Lẻ: doanh thu tính chỉ tiêu theo tháng quyết toán ----------
    rev_by_sales: dict[int, float] = {}; share_by_sales: dict[int, float] = {}
    doan_profit_by_sales: dict[int, float] = {}; doan_profit_total = 0.0
    for t in tours:
        s = R.settlement_summary(db, t)
        for b in t.bookings:
            if R.is_doan(t):
                share = s["profit"] * ((b.amount or 0) / s["revenue"] if s["revenue"] else 0)
                doan_profit_by_sales[b.sales_id] = doan_profit_by_sales.get(b.sales_id, 0) + share
                continue
            if not b.counts_for_target:
                continue                         # thiếu 4 trường → không chỉ tiêu, không hoa hồng
            if (emp_by_user.get(b.sales_id), t.id) in l3:
                continue                         # sự vụ mức 3 trên chính booking/đoàn này → không hoa hồng
            net = (b.amount or 0) - (b.discount or 0)           # mã KM: tính theo doanh thu đã giảm
            if t.below_margin and not t.strategic and s["margin"] < thr:
                share_by_sales[b.sales_id] = share_by_sales.get(b.sales_id, 0) + max(0.0, s["profit"] * ((b.amount or 0) / s["revenue"] if s["revenue"] else 0)) * 0.10
            else:
                rev_by_sales[b.sales_id] = rev_by_sales.get(b.sales_id, 0) + net
        if R.is_doan(t) and s["profit"] > 0:
            doan_profit_total += s["profit"]

    # Chuyến đã kết thúc nhưng CHƯA chốt quyết toán, theo người bán: doanh thu tính chỉ tiêu chưa gồm những
    # chuyến này, nên "0 đồng" của người còn chuyến treo là CHƯA BIẾT chứ không phải bán được 0.
    chua_qt: dict[int, int] = {}
    hom_nay = date.today()
    for t in db.execute(select(Tour).where(Tour.end_date <= hom_nay)).scalars():
        if t.status in ("kt_xac_nhan", "khoa"): continue
        for sid in {b.sales_id for b in t.bookings}:
            chua_qt[sid] = chua_qt.get(sid, 0) + 1

    for e in emps.values():
        if e.department != "kd_le" or e.contract_type != "hdld":
            continue
        rev = rev_by_sales.get(e.user_id, 0.0)
        if e.position in ("nv", "tl", "tp"):
            moc = moc_of(e, moc_hcm, moc_ct)
            cut = {"nv": 700_000, "tl": 800_000, "tp": 1_000_000}[e.position]
            xd = L.xac_dinh_thang_doanh_thu(e, rev, moc, cut, chua_qt.get(e.user_id, 0))
            row(e)["xac_dinh_luong"] = xd
            row(e)["luong_cb"] = round(xd["muc_ky"] * (0.85 if e.probation else 1.0))
            if xd["cap"] or xd.get("chua_du_co_so"):
                row(e)["ghi_chu"].append(xd["giai_thich"])
            k, rate = f_rate(rev, moc, f_table)
            comm = rate * max(0.0, rev - moc)
            if comm > 0:
                add(e, f"Hoa hồng thang f{k} ({rate*100:.1f}%) × (DT {rev:,.0f} − mốc)", comm)
            if share_by_sales.get(e.user_id):
                add(e, "10% lợi nhuận booking chuyến duyệt chạy dưới biên", share_by_sales[e.user_id])
            if e.office == "cantho" and doan_profit_by_sales.get(e.user_id):
                add(e, "10% lợi nhuận đoàn tự chốt (Cần Thơ)", doan_profit_by_sales[e.user_id] * 0.10)
            n_inc = incidents_of(db, e.id, y, m)
            if n_inc:
                pen = min(max(row(e)["bien_doi"], 0), n_inc * phat_su_vu)
                if pen: add(e, f"Chế tài sự vụ ≥ mức 2 ({n_inc} vụ) – chỉ trừ hoa hồng", -pen)
                if pen < n_inc * phat_su_vu: row(e)["ghi_chu"].append(f"Sự vụ ≥ mức 2: {n_inc} vụ, chế tài {n_inc * phat_su_vu:,.0f} nhưng hoa hồng chỉ {pen:,.0f} – không trừ lương cơ bản (Điều 127.2 BLLĐ)")
            if e.id in shift_pen:
                p_amt, n_miss, kicked = shift_pen[e.id]
                pen = min(max(row(e)["bien_doi"], 0), p_amt)
                if pen: add(e, f"Chế tài ca trực page: {n_miss} lượt sót – chỉ trừ hoa hồng", -pen)
                if kicked: row(e)["ghi_chu"].append("≥ 6 lượt sót: loại khỏi ca trực tháng sau, điều chỉnh chỉ tiêu")
        elif e.position == "gd_kd":
            staff = [x for x in emps.values() if x.department == "kd_le" and x.position in ("nv", "tl", "tp") and x.contract_type == "hdld"]
            hit = sum(1 for x in staff if rev_by_sales.get(x.user_id, 0) >= moc_of(x, moc_hcm, moc_ct))
            pct = hit / len(staff) if staff else 0
            if pct >= 0.85: add(e, f"Thưởng GĐ KD: {pct*100:.0f}% NV đạt chỉ tiêu (≥85%)", R.get_param(db, "gd_kd_thuong_85"), "+1% LN Công ty theo BCKQKD tháng – nhập tay khi TGĐ duyệt")
            elif pct >= 0.5: add(e, f"Thưởng GĐ KD: {pct*100:.0f}% NV đạt chỉ tiêu (50–85%)", R.get_param(db, "gd_kd_thuong_50"), "+0,5% LN Công ty – nhập tay khi TGĐ duyệt")
            else: row(e)["ghi_chu"].append(f"{pct*100:.0f}% NV đạt chỉ tiêu (<50%) – chỉ lương")

    # ---------- Kinh doanh Đoàn ----------
    moc_hh = R.get_param(db, "hh_doan_moc"); rate_hh = R.get_param(db, "hh_doan_ty_le"); moc_luong_doan = R.get_param(db, "moc_luong_doan")
    for e in emps.values():
        if e.department != "kd_doan":
            continue
        if e.position == "nv":
            pr = doan_profit_by_sales.get(e.user_id, 0.0)
            # bình quân LN quyết toán 3 tháng (người < 3 tháng: bình quân số tháng thực có)
            hist = []
            for k in range(2, -1, -1):
                mm, yy = m - k, y
                while mm <= 0: mm += 12; yy -= 1
                if e.start_date and date(yy, mm, 1) < date(e.start_date.year, e.start_date.month, 1):
                    continue                      # chưa vào làm: KHÔNG dựng thêm kỳ 0 đồng rồi chia cho ba
                tot = 0.0
                for t in month_tours(db, yy, mm):
                    if R.is_doan(t):
                        s = R.settlement_summary(db, t)
                        tot += sum(s["profit"] * ((b.amount or 0) / s["revenue"] if s["revenue"] else 0) for b in t.bookings if b.sales_id == e.user_id)
                hist.append({"ky": f"{yy:04d}-{mm:02d}", "loi_nhuan": round(tot)})
            xd = L.xac_dinh_thang_loi_nhuan(e, hist, moc_luong_doan, sorted(DOAN_F))
            row(e)["xac_dinh_luong"] = xd
            row(e)["luong_cb"] = round(xd["muc_ky"] * (0.85 if e.probation else 1.0))
            if xd["ty_le"] < 1: row(e)["ghi_chu"].append(xd["giai_thich"])
            if pr > moc_hh:
                add(e, f"Hoa hồng đoàn {rate_hh*100:.0f}% × (LN {pr:,.0f} − {moc_hh:,.0f})", (pr - moc_hh) * rate_hh)
        elif e.position == "ptgd_doan" and doan_profit_total > 0:
            n_inc = incidents_of(db, e.id, y, m)
            rate = R.get_param(db, "ptgd_doan_ty_le") - 0.005 * n_inc
            add(e, f"PTGĐ tour đoàn {rate*100:.1f}% LN các đoàn có lãi", doan_profit_total * max(rate, 0))
        elif e.position == "sale_admin" and doan_profit_total > 0:
            add(e, "Sale Admin 2% LN các đoàn có lãi", doan_profit_total * R.get_param(db, "sale_admin_ty_le"))

    # ---------- Điều hành: quỹ 2%/1%/1% chia 70/30 ----------
    fund_by_op: dict[int, float] = {}; fund_tp = 0.0
    for t in tours:
        s = R.settlement_summary(db, t)
        fund_by_op[t.operator_id] = fund_by_op.get(t.operator_id, 0) + s["fund_nv"]; fund_tp += s["fund_tp"]
    for e in emps.values():
        if e.department == "dieu_hanh" and e.position == "nv" and fund_by_op.get(e.user_id):
            add(e, "Thưởng chuyến Điều hành (70% quỹ)", fund_by_op[e.user_id])
        if e.department == "dieu_hanh" and e.position == "tp" and fund_tp:
            add(e, "Trưởng phòng ĐH – 30% quỹ toàn phòng", fund_tp)

    # ---------- Ban Visa: quỹ theo tháng hoàn thành ----------
    gia_tu = R.get_param(db, "visa_tu_xu_ly"); gia_dt = R.get_param(db, "visa_gui_doi_tac"); gia_lm = R.get_param(db, "visa_lien_minh")
    files = [f for f in db.execute(select(VisaFile).where(VisaFile.status == "hoan_thanh")).scalars() if f.completed_at and f.completed_at.year == y and f.completed_at.month == m]
    hcm_pool = 0.0; hn: dict[int, float] = {}
    for f in files:
        v = (gia_tu if f.method == "tu_xu_ly" else gia_dt) + (gia_lm if f.alliance else 0)
        if f.office == "hanoi": hn[f.handler_id] = hn.get(f.handler_id, 0) + v
        else: hcm_pool += v
    hcm_staff = [e for e in emps.values() if e.department == "visa" and e.office == "hcm" and e.position != "tp"]
    for e in hcm_staff:
        if hcm_pool: add(e, f"Quỹ visa HCM chia đều {len(hcm_staff)} người ({len([f for f in files if f.office != 'hanoi'])} hồ sơ)", hcm_pool / len(hcm_staff))
    for eid, v in hn.items():
        if eid in emps: add(emps[eid], "Quỹ visa Hà Nội (hưởng riêng)", v)

    # ---------- HDV cộng tác viên: thù lao theo chuyến quyết toán trong tháng, TNCN 10% ----------
    tncn = R.get_param(db, "hdv_tncn")
    tour_ids = {t.id for t in tours}
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.status == "da_xac_nhan")).scalars():
        if a.tour_id not in tour_ids or a.guide_id not in emps:
            continue
        e = emps[a.guide_id]; t = db.get(Tour, a.tour_id)
        gross = a.rate_per_day * a.days * (2 if a.holiday else 1)
        if not a.report_submitted or not a.advance_settled:
            row(e)["ghi_chu"].append(f"TREO thù lao {t.code}: thiếu báo cáo tour / chưa hoàn ứng"); continue
        add(e, f"Thù lao dẫn {t.code}: {a.days} ngày × {a.rate_per_day:,.0f}{' ×2 lễ' if a.holiday else ''}", gross)
        r = row(e); r["tncn"] += round(gross * tncn)
    # ---------- Tài xế: công tác phí theo lệnh điều xe ----------
    ctp = R.get_param(db, "tai_xe_cong_tac_phi")
    days_by_driver: dict[int, int] = {}
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.status.in_(["da_xac_nhan", "hoan_thanh"]))).scalars():
        v = db.get(Vehicle, d.vehicle_id)
        if v and v.kind == "hop_tac":
            continue                                  # xe hợp tác: tài xế đối tác, không tính công tác phí
        if d.date_to.year == y and d.date_to.month == m:
            days_by_driver[d.driver_id] = days_by_driver.get(d.driver_id, 0) + (d.date_to - d.date_from).days + 1
    for eid, n in days_by_driver.items():
        if eid in emps: add(emps[eid], f"Công tác phí tài xế {n} ngày tour × {ctp:,.0f}", n * ctp, "Phụ cấp lễ/đêm theo luật do HCNS tính thêm")

    # ---------- BƯỚC 3: khoản trừ của người lao động (Bộ tính lương từ 01/9/2026) ----------
    # Khác hẳn với bước xác định mức lương ở trên: đây mới là khoản TRỪ thật – bảo hiểm xã hội phần người
    # lao động và đoàn phí công đoàn. BHXH tính trên MỨC LƯƠNG HỢP ĐỒNG, không trên mức lương của kỳ.
    # Căn cứ tính là TIỀN LƯƠNG LÀM CĂN CỨ ĐÓNG BHXH BẮT BUỘC, không phải lương hợp đồng: danh sách đóng
    # BHXH tháng 08/2026 ghi mức tham gia 5.310.000 trong khi lương hợp đồng nhiều người 15–25 triệu. Lấy
    # lương hợp đồng làm căn cứ là trừ của người lao động gấp nhiều lần số phải trừ. Đoàn phí công đoàn cũng
    # tính trên chính mức này theo thỏa thuận khấu trừ đã ký.
    # Chưa có mức đóng thì KHÔNG trừ và ghi rõ – thiếu dữ liệu không phải là dữ liệu bằng 0, nhưng ở đây
    # đoán thừa còn tệ hơn đoán thiếu: trừ nhầm là lấy tiền của người ta.
    ty_bhxh = R.get_param(db, "bhxh_nld"); ty_doan_phi = R.get_param(db, "doan_phi_ty_le")
    for e in emps.values():
        if e.id not in rows: continue
        r = rows[e.id]
        if e.contract_type != "hdld":
            continue          # cộng tác viên (HDV) không thuộc diện đóng BHXH bắt buộc – chỉ khấu trừ TNCN 10%
        if e.bhxh_base and e.bhxh_base > 0:
            r["bhxh"] = round((e.bhxh_base or 0) * ty_bhxh)
            r["bhxh_base"] = e.bhxh_base
            if e.member_org: r["doan_phi"] = round((e.bhxh_base or 0) * ty_doan_phi)
        else:
            r["thieu_muc_bhxh"] = True
            r["ghi_chu"].append("CHƯA CÓ MỨC ĐÓNG BHXH – chưa trừ bảo hiểm và đoàn phí; HCNS nạp danh sách "
                                "đóng BHXH của kỳ trước khi trình ký")

    out = []
    vi_pham = []
    for r in rows.values():
        vi_pham += L.kiem_tra_khong_phai_khoan_tru(r)
        r["tru_su_vu"] = round(-sum(k["tien"] for k in r["khoan"] if k["tien"] < 0))
        r["thu_nhap"] = round(r["luong_cb"] + sum(k["tien"] for k in r["khoan"] if k["tien"] > 0))
        r["khoan_tru"] = round(r["tru_su_vu"] + r["bhxh"] + r["doan_phi"] + r["tncn"])
        r["thuc_nhan"] = round(r["thu_nhap"] - r["khoan_tru"])
        r["ghi_chu"] = "; ".join(r["ghi_chu"])
        out.append(r)
    out.sort(key=lambda r: (r["phong"], r["ma"]))
    if vi_pham:
        # Ràng buộc pháp lý, kiểm ở tầng dữ liệu chứ không phải tầng giao diện (Điều 127.2 BLLĐ 2019).
        raise ValueError("Bảng lương có dòng trừ bắt nguồn từ xếp bậc theo doanh thu / lợi nhuận: " + "; ".join(vi_pham))
    totals = {"luong_cb": sum(r["luong_cb"] for r in out), "bien_doi": sum(r["bien_doi"] for r in out), "tncn": sum(r["tncn"] for r in out),
              "bhxh": sum(r["bhxh"] for r in out), "doan_phi": sum(r["doan_phi"] for r in out),
              "tru_su_vu": sum(r["tru_su_vu"] for r in out), "thu_nhap": sum(r["thu_nhap"] for r in out),
              "khoan_tru": sum(r["khoan_tru"] for r in out),
              "thuc_nhan": sum(r["thuc_nhan"] for r in out), "so_nguoi": len(out), "so_chuyen": len(tours),
              "cong_chuan": cong_chuan, "thieu_cong": [r["ma"] for r in out if (r.get("xac_dinh_luong") or {}).get("thieu_du_lieu")],
              "chua_du_co_so": [r["ma"] for r in out if (r.get("xac_dinh_luong") or {}).get("chua_du_co_so")],
              "thieu_muc_bhxh": [r["ma"] for r in out if r.get("thieu_muc_bhxh")]}
    return out, totals


def get_or_draft(db: Session, period: str, refresh: bool = False) -> PayrollRun:
    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    if run and run.status != "nhap" and refresh:
        raise ValueError("Bảng lương đã qua bước xác nhận – không tính lại")
    if run is None or refresh or run.status == "nhap":
        xung_dot = L.xung_dot_ho_so(db)
        if xung_dot:
            # Một mã dùng cho hai người nghĩa là hệ thống không biết trả tiền cho ai. Dừng và nói ra,
            # không tự chọn hồ sơ đầu tiên (Phần IV Phụ lục – xung đột mã 294).
            raise ValueError("Chưa chạy được kỳ lương, còn xung đột hồ sơ nhân sự: " +
                             "; ".join(x["thong_diep"] for x in xung_dot[:5]))
        rows, totals = compute_draft(db, period, (run.inputs if run else None) or {})
        if run is None:
            run = PayrollRun(period=period, rows=rows, totals=totals); db.add(run)
        else:
            run.rows, run.totals = rows, totals
        db.commit(); db.refresh(run)
    return run


def advance(db: Session, u: User, run: PayrollRun) -> str:
    """Bước tiếp theo theo vai trò: ketoan (nhap→kt_xac_nhan), hcns (kt_xac_nhan→hcns_lap), tgd (hcns_lap→tgd_ky + ghi sổ)."""
    now = datetime.now()
    if run.status == "nhap" and u.role == "ketoan":
        run.status, run.kt_confirmed_by, run.kt_confirmed_at = "kt_xac_nhan", u.username, now
        msg = "Kế toán đã xác nhận cơ sở tính lương"
    elif run.status == "kt_xac_nhan" and u.role == "hcns":
        run.status, run.hcns_by, run.hcns_at = "hcns_lap", u.username, now
        msg = "HCNS đã lập bảng lương – chờ TGĐ ký lô"
    elif run.status == "hcns_lap" and u.role == "tgd":
        run.status, run.tgd_by, run.tgd_at = "tgd_ky", u.username, now
        ids = post_payroll_entries(db, run)
        run.entry_ids = ids
        msg = f"TGĐ đã ký lô bảng lương {run.period}" + (f" – đã ghi sổ {len(ids)} chứng từ" if ids else "")
    else:
        raise ValueError(f"Vai trò {u.role} không thực hiện được bước này ở trạng thái {run.status}")
    R.audit(db, u.username, u.role, f"bang_luong_{run.status}", f"payroll:{run.period}", after={"tong_thuc_nhan": run.totals.get("thuc_nhan")})
    db.commit()
    return msg


def post_payroll_entries(db: Session, run: PayrollRun) -> list[int]:
    """Bút toán lương, LẬP RIÊNG CHO TỪNG PHÁP NHÂN TRẢ LƯƠNG.

    Nợ 642 – Có 334 (HĐLĐ); Nợ 632 – Có 338 thù lao CTV/HDV; Nợ 338 – Có 3335 TNCN khấu trừ 10%;
    Nợ 334 – Có 3383 phần bảo hiểm xã hội người lao động; Nợ 334 – Có 3382 đoàn phí công đoàn.

    Từ 01/9/2026 Đội xe và Giám đốc Điều hành xe nhận lương tại Công ty Vận tải Vietrip, phần còn lại tại
    Vietourist Holdings. Gộp một bút toán chung là sai cả sổ lẫn thuế: hai pháp nhân là hai túi tiền, mỗi
    bên có nghĩa vụ thuế và bảo hiểm riêng. Nên chia theo pháp nhân chủ quản của hồ sơ nhân sự, và người
    chưa xác định pháp nhân thì ghi vào một chứng từ riêng có ghi rõ – không lặng lẽ dồn vào công ty mẹ.
    """
    from app.models.core import Company
    d = date.today()
    emps = {e.code: e for e in db.execute(select(Employee)).scalars()}
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    nhom: dict[int | None, list[dict]] = {}
    for r in run.rows:
        e = emps.get(r["ma"])
        nhom.setdefault(e.company_id if e else None, []).append(r)

    ids = []
    for cid, rows_ in sorted(nhom.items(), key=lambda x: (x[0] is None, x[0] or 0)):
        c = cos.get(cid)
        ten = c.code if c else "CHƯA XÁC ĐỊNH PHÁP NHÂN"
        hdld = sum(r["luong_cb"] + r["bien_doi"] for r in rows_ if r["hop_dong"] == "hdld")
        ctv = sum(r["bien_doi"] for r in rows_ if r["hop_dong"] != "hdld")
        tncn = sum(r.get("tncn", 0) for r in rows_)
        bhxh = sum(r.get("bhxh", 0) for r in rows_)
        doan_phi = sum(r.get("doan_phi", 0) for r in rows_)
        try:
            if hdld > 0:
                ids.append(ACC.post_entry(db, "robot", "robot", d, f"Lương tháng {run.period} – {ten}",
                                          [{"account": "642", "debit": hdld}, {"account": "334", "credit": hdld}],
                                          "luong", f"payroll:{run.period}:{ten}").id)
            if ctv > 0:
                ids.append(ACC.post_entry(db, "robot", "robot", d, f"Thù lao HDV/CTV tháng {run.period} – {ten}",
                                          [{"account": "632", "debit": ctv}, {"account": "338", "credit": ctv}],
                                          "luong", f"payroll:{run.period}:{ten}").id)
            if tncn > 0:
                ids.append(ACC.post_entry(db, "robot", "robot", d, f"Khấu trừ TNCN 10% thù lao CTV tháng {run.period} – {ten}",
                                          [{"account": "338", "debit": tncn}, {"account": "3335", "credit": tncn}],
                                          "luong", f"payroll:{run.period}:{ten}").id)
            if bhxh > 0:
                ids.append(ACC.post_entry(db, "robot", "robot", d, f"BHXH phần người lao động tháng {run.period} – {ten}",
                                          [{"account": "334", "debit": bhxh}, {"account": "3383", "credit": bhxh}],
                                          "luong", f"payroll:{run.period}:{ten}").id)
            if doan_phi > 0:
                ids.append(ACC.post_entry(db, "robot", "robot", d, f"Đoàn phí công đoàn tháng {run.period} – {ten}",
                                          [{"account": "334", "debit": doan_phi}, {"account": "3382", "credit": doan_phi}],
                                          "luong", f"payroll:{run.period}:{ten}").id)
        except ValueError as ex:
            R.audit(db, "robot", "robot", "ghi_so_that_bai", f"payroll:{run.period}:{ten}", after={"ly_do": str(ex)})
    return ids


def but_toan_theo_phap_nhan(db: Session, run: PayrollRun) -> list[dict]:
    """Xem trước bảng lương chia theo pháp nhân trả lương, để đối chiếu trước khi TGĐ ký lô."""
    from app.models.core import Company
    emps = {e.code: e for e in db.execute(select(Employee)).scalars()}
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    nhom: dict[int | None, dict] = {}
    for r in run.rows:
        e = emps.get(r["ma"]); cid = e.company_id if e else None
        c = cos.get(cid)
        g = nhom.setdefault(cid, {"company_id": cid, "company": c.name if c else "", "code": c.code if c else "",
                                  "chua_xac_dinh": c is None, "so_nguoi": 0, "thu_nhap": 0.0, "khoan_tru": 0.0,
                                  "bhxh": 0.0, "doan_phi": 0.0, "tncn": 0.0, "thuc_nhan": 0.0})
        g["so_nguoi"] += 1
        for k in ("thu_nhap", "khoan_tru", "bhxh", "doan_phi", "tncn", "thuc_nhan"):
            g[k] += r.get(k, 0)
    return sorted(nhom.values(), key=lambda g: (g["chua_xac_dinh"], g["code"]))


# ---------- Cổng 13: điều kiện hành nghề HDV ----------
def guide_eligible(e: Employee, on: date) -> tuple[bool, str]:
    if e.department != "huong_dan": return False, "Không phải HDV"
    if not e.card_no or not e.card_expiry or e.card_expiry < on: return False, "Thẻ HDV hết hạn hoặc chưa có"
    if not e.member_org: return False, "Chưa là hội viên tổ chức xã hội – nghề nghiệp"
    if e.contract_type == "ctv" and not e.ctv_contract: return False, "Chưa ký hợp đồng cộng tác"
    return True, ""


def next_code(db: Session, model, prefix: str, width: int = 4) -> str:
    n = db.execute(select(func.count()).select_from(model)).scalar() + 1
    return f"{prefix}{n:0{width}d}"
