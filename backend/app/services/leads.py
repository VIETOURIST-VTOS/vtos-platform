"""CRM lead: nhập lead (Excel/CSV/tay), thống kê kênh × tháng, đối chiếu lead ↔ booking theo SĐT (tỷ lệ chốt, khách mới / quay lại,
doanh thu lũy kế – đúng mẫu 'Báo cáo Lead & Chuyển đổi' của Marketing), phân công sale, nhắn Zalo cho lead."""
from datetime import datetime, date, timedelta
from io import BytesIO
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Tour, Booking
from app.models.crm import Lead, LeadChannelStat, ZaloMessage, LEAD_CHANNELS, LEAD_STATUS
from app.services import rules as R
from app.services.zalo import norm_phone

CANON = {c.lower().replace(" ", ""): c for c in LEAD_CHANNELS}
CANON.update({"hotline": "Hotline 1", "web": "Đặt tour web", "website": "Đặt tour web", "dattourweb": "Đặt tour web", "tiktok": "Tiktok Ads", "tiktokads": "Tiktok Ads", "zalo": "Zalo OA", "fb": "Facebook", "khachcu": "Khách cũ"})


def canon_channel(s: str) -> str:
    k = (s or "").strip().lower().replace(" ", "")
    return CANON.get(k, (s or "Khác").strip()[:40] or "Khác")


def month_of(v) -> str:
    """'Tháng 8' → tháng đó của năm hiện tại; '2026-08' / '08/2026' / datetime → YYYY-MM."""
    if isinstance(v, (datetime, date)): return f"{v:%Y-%m}"
    s = str(v or "").strip().lower()
    import re
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if m: return f"{int(m.group(1))}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{1,2})/(\d{4})$", s)
    if m: return f"{int(m.group(2))}-{int(m.group(1)):02d}"
    m = re.search(r"th[aá]ng\s*(\d{1,2})(?:\D+(\d{4}))?", s)
    if m: return f"{int(m.group(2)) if m.group(2) else date.today().year}-{int(m.group(1)):02d}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return f"{int(m.group(3))}-{int(m.group(2)):02d}"
    return f"{date.today():%Y-%m}"


def upsert_lead(db: Session, actor: str, d: dict) -> tuple[Lead, bool]:
    ph = norm_phone(d.get("phone") or "")
    if len(ph) < 7: raise ValueError(f"SĐT không hợp lệ: {d.get('phone')}")
    if len(ph) < 10: d = {**d, "note": ((d.get("note") or "") + f" [SĐT nguồn thiếu số: {d.get('phone')}]").strip()}
    ch = canon_channel(d.get("channel") or ""); mo = month_of(d.get("lead_month") or d.get("received_at") or "")
    l = db.execute(select(Lead).where(Lead.phone == ph, Lead.lead_month == mo, Lead.channel == ch)).scalars().first()
    new = l is None
    if new: l = Lead(phone=ph, channel=ch, lead_month=mo, created_by=actor); db.add(l)
    if d.get("name"): l.name = str(d["name"]).strip()[:120]
    for k in ("campaign", "interest", "note"):
        if d.get(k): setattr(l, k, str(d[k]).strip()[: (200 if k != "note" else 2000)])
    if d.get("received_at"):
        try: l.received_at = datetime.fromisoformat(str(d["received_at"])[:19])
        except ValueError: pass
    if d.get("sales_id"): l.sales_id = int(d["sales_id"])
    if d.get("status") in LEAD_STATUS: l.status = d["status"]
    db.flush(); return l, new


def import_rows(db: Session, actor: str, rows: list[dict]) -> dict:
    n_new = n_upd = 0; errs = []
    for i, r in enumerate(rows):
        try:
            _, new = upsert_lead(db, actor, r); n_new += new; n_upd += (not new)
        except ValueError as ex: errs.append(f"dòng {i + 1}: {ex}")
    db.commit(); return {"new": n_new, "updated": n_upd, "errors": errs[:20], "n_errors": len(errs)}


def import_xlsx(db: Session, actor: str, data: bytes, default_month: str = "") -> dict:
    """Đọc mọi sheet có cột SĐT: nhận dạng cột theo tiêu đề (SĐT/Điện thoại, Tên, Kênh, Tháng lead/Ngày, Tour, Ghi chú).
    Sheet tổng hợp có cột 'Kênh' + 'Tháng lead' + 'Tổng leads' → nạp thống kê kênh × tháng."""
    from openpyxl import load_workbook
    wb = load_workbook(BytesIO(data), data_only=True); rows = []; stats = 0
    def find(h, *keys): return next((i for i, x in enumerate(h) if x and any(k in str(x).lower() for k in keys)), None)
    for ws in wb.worksheets:
        vals = list(ws.iter_rows(values_only=True))
        for hi, h in enumerate(vals[:60]):
            hl = [str(x).lower() if x else "" for x in h]
            ip = next((i for i, x in enumerate(hl) if x.strip() in ("sđt", "sdt", "số điện thoại", "điện thoại", "phone", "sđt khách", "sđt khách hàng", "so dien thoai")), None)
            ik = find(hl, "kênh", "kenh", "channel"); im = find(hl, "tháng lead", "thang lead"); it = find(hl, "tổng leads", "tong leads", "số leads")
            if ik is not None and im is not None and it is not None and ip is None:   # bảng thống kê kênh × tháng
                for r in vals[hi + 1:]:
                    if r[ik] is None or r[it] is None or str(r[ik]).strip().lower() in ("tổng", "kênh", ""):
                        if r[ik] is None and r[it] is None: break
                        continue
                    try: n = int(float(r[it]))
                    except (TypeError, ValueError): continue
                    set_stat(db, actor, month_of(r[im]), canon_channel(str(r[ik])), n); stats += 1
                continue
            if ip is None: continue
            iname = find(hl, "tên khách", "ten khach", "khách hàng", "họ tên", "name"); idate = find(hl, "ngày lead", "ngày tạo", "ngày nhận", "date")
            iint = find(hl, "tour", "quan tâm"); inote = find(hl, "ghi chú", "note"); icamp = find(hl, "chiến dịch", "campaign")
            for r in vals[hi + 1:]:
                if ip >= len(r) or r[ip] is None or not str(r[ip]).strip(): continue
                rows.append({"phone": r[ip], "name": r[iname] if iname is not None else "", "channel": r[ik] if ik is not None else "Khác",
                             "lead_month": r[im] if im is not None else (r[idate] if idate is not None else default_month), "received_at": r[idate] if idate is not None and isinstance(r[idate], datetime) else None,
                             "interest": r[iint] if iint is not None else "", "note": r[inote] if inote is not None else "", "campaign": r[icamp] if icamp is not None else ""})
            break
    out = import_rows(db, actor, rows); out["stats"] = stats; out["rows"] = len(rows)
    R.audit(db, actor, "user", "nhap_lead_excel", "crm", after={"moi": out["new"], "cap_nhat": out["updated"], "thong_ke": stats, "loi": out["n_errors"]}); db.commit()
    return out


def set_stat(db: Session, actor: str, month: str, channel: str, leads: int, cost: float | None = None) -> LeadChannelStat:
    s = db.execute(select(LeadChannelStat).where(LeadChannelStat.lead_month == month, LeadChannelStat.channel == channel)).scalars().first()
    if not s: s = LeadChannelStat(lead_month=month, channel=channel); db.add(s)
    s.leads = int(leads); s.updated_by = actor
    if cost is not None: s.cost = float(cost)
    db.flush(); return s


# ---------- đối chiếu lead ↔ booking ----------
def _bookings_by_phone(db: Session) -> dict[str, list[Booking]]:
    out: dict[str, list[Booking]] = {}
    for b in db.execute(select(Booking).where(Booking.cancelled == False)).scalars():
        out.setdefault(norm_phone(b.customer_phone), []).append(b)
    return out


def match_conversions(db: Session, months: list[str] | None = None) -> dict:
    """Gắn booking cho lead (SĐT trùng, booking tạo sau lead); lead chốt → status 'chot'. Trả số lượng."""
    q = select(Lead)
    if months: q = q.where(Lead.lead_month.in_(months))
    leads = list(db.execute(q).scalars()); bp = _bookings_by_phone(db); n = 0
    for l in leads:
        bs = [b for b in bp.get(l.phone, []) if f"{b.created_at:%Y-%m}" >= l.lead_month]
        if bs:
            b = min(bs, key=lambda x: x.created_at)
            if l.booking_id != b.id: l.booking_id, l.converted_at, n = b.id, b.created_at, n + 1
            if l.status != "chot": l.status = "chot"
    db.commit(); return {"matched": n, "leads": len(leads)}


def conversion_report(db: Session, target_month: str, lead_months: list[str] | None = None) -> dict:
    """Đúng cấu trúc file Marketing: (1) lead tháng T → tour khởi hành tháng T theo kênh; (2) lead T-2, T-1, T → tour tháng T; (3) kênh × tháng lead;
    chi tiết SĐT chốt: tour, ngày KH, khách mới / quay lại, số lần đi, tổng khách, doanh thu lũy kế."""
    y, m = map(int, target_month.split("-")); d1 = date(y, m, 1); d2 = date(y + (m == 12), m % 12 + 1, 1)
    if not lead_months:
        lead_months = [f"{(d1 - timedelta(days=1)).replace(day=1) - timedelta(days=0):%Y-%m}"]
        p1 = (d1 - timedelta(days=1)).replace(day=1); p2 = (p1 - timedelta(days=1)).replace(day=1)
        lead_months = [f"{p2:%Y-%m}", f"{p1:%Y-%m}", target_month]
    bp = _bookings_by_phone(db)
    tours_in = {b.id for b in db.execute(select(Booking).join(Tour, Tour.id == Booking.tour_id).where(Booking.cancelled == False, Tour.start_date >= d1, Tour.start_date < d2)).scalars()}
    stats = {(s.lead_month, s.channel): s for s in db.execute(select(LeadChannelStat).where(LeadChannelStat.lead_month.in_(lead_months))).scalars()}
    leads = list(db.execute(select(Lead).where(Lead.lead_month.in_(lead_months))).scalars())
    lead_counts: dict[tuple, int] = {}
    for l in leads: lead_counts[(l.lead_month, l.channel)] = lead_counts.get((l.lead_month, l.channel), 0) + 1
    detail = []; seen = set(); agg: dict[tuple, dict] = {}
    for l in sorted(leads, key=lambda x: (x.lead_month, x.channel)):
        key = (l.lead_month, l.channel); a = agg.setdefault(key, {"lead_month": l.lead_month, "channel": l.channel, "leads": 0, "converted": 0, "new": 0, "returning": 0, "revenue": 0.0})
        bs = bp.get(l.phone, []); hit = [b for b in bs if b.id in tours_in]
        if not hit or (l.phone, l.lead_month) in seen: continue
        seen.add((l.phone, l.lead_month)); b = min(hit, key=lambda x: x.tour.start_date)
        prior = [x for x in bs if x.tour and x.tour.start_date < b.tour.start_date]
        returning = len(prior) > 0; trips = len({x.tour_id for x in bs if x.tour and x.tour.start_date < d2}); pax = sum(x.pax for x in bs if x.tour and x.tour.start_date < d2)
        rev = sum(x.amount - x.discount for x in bs if x.tour and x.tour.start_date < d2)
        a["converted"] += 1; a["new"] += 0 if returning else 1; a["returning"] += 1 if returning else 0; a["revenue"] += rev
        detail.append({"channel": l.channel, "lead_month": l.lead_month, "phone": l.phone, "name": l.name or b.customer_name, "tour": b.tour.name if b.tour else "", "tour_code": b.tour.code if b.tour else "", "start_date": b.tour.start_date if b.tour else None,
                       "kind": "Khách quay lại" if returning else "Khách mới", "trips": trips, "pax": pax, "revenue": rev, "sales": b.sales.full_name if b.sales else "", "booking": b.code})
    rows = []
    for key in sorted(set(list(stats.keys()) + list(agg.keys()))):
        a = agg.get(key, {"lead_month": key[0], "channel": key[1], "leads": 0, "converted": 0, "new": 0, "returning": 0, "revenue": 0.0})
        a["leads"] = max(stats[key].leads if key in stats else 0, lead_counts.get(key, 0)); a["cost"] = stats[key].cost if key in stats else 0
        a["rate"] = a["converted"] / a["leads"] if a["leads"] else 0; a["cost_per_lead"] = a["cost"] / a["leads"] if a["leads"] and a["cost"] else 0; rows.append(a)
    by_month = {}
    for a in rows:
        mm = by_month.setdefault(a["lead_month"], {"lead_month": a["lead_month"], "leads": 0, "converted": 0, "new": 0, "returning": 0, "revenue": 0.0})
        for k in ("leads", "converted", "new", "returning", "revenue"): mm[k] += a[k]
    for mm in by_month.values(): mm["rate"] = mm["converted"] / mm["leads"] if mm["leads"] else 0
    cur = [a for a in rows if a["lead_month"] == target_month]
    tot = {"leads": sum(a["leads"] for a in cur), "converted": sum(a["converted"] for a in cur)}; tot["rate"] = tot["converted"] / tot["leads"] if tot["leads"] else 0
    return {"target_month": target_month, "lead_months": lead_months, "by_channel_current": cur, "total_current": tot, "by_month": sorted(by_month.values(), key=lambda x: x["lead_month"]),
            "by_channel_month": rows, "detail": sorted(detail, key=lambda x: (x["channel"], x["lead_month"], -x["revenue"])), "as_of": datetime.now()}


def to_xlsx(rep: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = f"Tong hop {rep['target_month']}"
    def head(ws, cols): ws.append(cols); [setattr(c, "font", Font(bold=True)) or setattr(c, "fill", PatternFill("solid", fgColor="D9E2F3")) for c in ws[ws.max_row]]
    ws.append([f"BÁO CÁO LEAD & CHUYỂN ĐỔI THÁNG {rep['target_month']} (VTOS, {rep['as_of']:%d/%m/%Y %H:%M})"]); ws["A1"].font = Font(bold=True, size=13); ws.append([])
    ws.append([f"1. Lead tháng {rep['target_month']} → tour khởi hành tháng {rep['target_month']} theo kênh"]); head(ws, ["Kênh", "Số leads", "SĐT chốt tour", "Tỷ lệ chốt", "Khách mới", "Khách quay lại", "Doanh thu lũy kế (đ)", "Chi phí/lead"])
    for a in rep["by_channel_current"]: ws.append([a["channel"], a["leads"], a["converted"], round(a["rate"], 4), a["new"], a["returning"], round(a["revenue"]), round(a["cost_per_lead"])])
    t = rep["total_current"]; ws.append(["TỔNG", t["leads"], t["converted"], round(t["rate"], 4)]); ws.append([])
    ws.append([f"2. Đối chiếu lead các tháng → tour tháng {rep['target_month']}"]); head(ws, ["Tháng lead", "Tổng leads", "SĐT có tour", "Tỷ lệ chốt", "Khách mới", "Khách quay lại", "Doanh thu lũy kế (đ)"])
    for mm in rep["by_month"]: ws.append([mm["lead_month"], mm["leads"], mm["converted"], round(mm["rate"], 4), mm["new"], mm["returning"], round(mm["revenue"])])
    ws.append([]); ws.append(["3. Chi tiết kênh × tháng lead"]); head(ws, ["Kênh", "Tháng lead", "Tổng leads", "SĐT có tour", "Tỷ lệ chốt", "Khách mới", "Khách quay lại", "Doanh thu lũy kế (đ)"])
    for a in rep["by_channel_month"]: ws.append([a["channel"], a["lead_month"], a["leads"], a["converted"], round(a["rate"], 4), a["new"], a["returning"], round(a["revenue"])])
    ws2 = wb.create_sheet(f"Chi tiet SDT da chot"); head(ws2, ["STT", "Kênh", "Tháng lead", "SĐT", "Tên khách hàng", "Tour", "Mã tour", "Ngày khởi hành", "Phân loại", "Số lần đi (lũy kế)", "Tổng khách (lũy kế)", "Doanh thu lũy kế (đ)", "Sale", "Booking"])
    for i, d in enumerate(rep["detail"], 1): ws2.append([i, d["channel"], d["lead_month"], d["phone"], d["name"], d["tour"], d["tour_code"], d["start_date"].strftime("%d/%m/%Y") if d["start_date"] else "", d["kind"], d["trips"], d["pax"], round(d["revenue"]), d["sales"], d["booking"]])
    for w in (ws, ws2):
        for col in w.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8); w.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 48)
    bio = BytesIO(); wb.save(bio); return bio.getvalue()


def lead_out(l: Lead, db: Session | None = None) -> dict:
    s = db.get(User, l.sales_id) if (db and l.sales_id) else None
    b = db.get(Booking, l.booking_id) if (db and l.booking_id) else None
    return {"id": l.id, "phone": l.phone, "name": l.name, "channel": l.channel, "lead_month": l.lead_month, "received_at": l.received_at, "campaign": l.campaign, "interest": l.interest, "sales_id": l.sales_id,
            "sales_name": s.full_name if s else "", "status": l.status, "status_name": LEAD_STATUS.get(l.status, l.status), "note": l.note, "zalo_uid": l.zalo_uid, "zalo_follow": l.zalo_follow,
            "last_contact_at": l.last_contact_at, "booking_id": l.booking_id, "booking_code": b.code if b else "", "booking_tour": b.tour.code if b and b.tour else "", "converted_at": l.converted_at, "created_at": l.created_at}
