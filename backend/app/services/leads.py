"""CRM lead: nhập lead (Excel/CSV/tay), thống kê kênh × tháng, đối chiếu lead ↔ booking theo SĐT (tỷ lệ chốt, khách mới / quay lại,
doanh thu lũy kế – đúng mẫu 'Báo cáo Lead & Chuyển đổi' của Marketing), phân công sale, nhắn Zalo cho lead."""
from datetime import datetime, date, timedelta
from io import BytesIO
import sqlalchemy as sa
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Tour, Booking
from app.models.crm import Lead, LeadChannelStat, ZaloMessage, LEAD_CHANNELS, LEAD_STATUS
from app.services import rules as R
from app.services.zalo import norm_phone

# Tên bản quy tắc tính TỶ LỆ CHỐT mà báo cáo đang dùng. Chủ tịch chốt 14/9/2026: lấy cách của tệp
# OVERVIEW của phòng Marketing — nhóm theo KỲ PHÁT SINH LEAD, tử số gồm CẢ phần chốt ở các kỳ SAU.
# Đổi quy tắc là đổi BIÊN BẢN rồi mới đổi tên ở đây, không phải sửa thầm phép tính: mọi báo cáo in
# ra kèm tên thước đã dùng, để hai bản báo cáo khác thước không bị đem so với nhau.
QUY_TAC_TY_LE_CHOT = "overview-v1"

CANON = {c.lower().replace(" ", ""): c for c in LEAD_CHANNELS}
CANON.update({"hotline": "Hotline 1", "web": "Đặt tour web", "website": "Đặt tour web", "dattourweb": "Đặt tour web", "tiktok": "Tiktok Ads", "tiktokads": "Tiktok Ads", "zalo": "Zalo OA", "fb": "Facebook", "khachcu": "Khách cũ"})


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# HẠN XỬ LÝ MỘT LEAD — P.TGĐ Phan Ngọc Tuấn chốt 24 giờ ngày 18/9/2026
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# CON SỐ KHÔNG NẰM Ở ĐÂY. Nó nằm ở tham số `lead_han_xu_ly_gio` trong rules.DEFAULT_PARAMS, chỗ duy
# nhất của kho ghi một con số luật kèm người ký và ngày ký, và là chỗ đã có cửa nhập sẵn (màn hình
# Tham số). Viết cứng 24 vào đây là lấy mất cả hai thứ ấy trong một dòng.
#
# HẠN LÀ SỐ SUY RA, KHÔNG PHẢI CỘT TRONG BẢNG. `hạn = received_at + N giờ` — không thêm cột vào
# bảng leads, nên không có migration. Cột chỉ cần khi giá trị KHÔNG suy được từ dữ liệu đã có; ở đây
# nó suy được, và một cột thừa thì đến ngày đổi hạn là cả bảng cũ mang hạn cũ mà không ai nhớ.
#
# THẾ NÀO LÀ ĐÃ XỬ LÝ — hai dấu, lấy HỢP, không lấy giao:
#     · `last_contact_at` có giá trị  → đã có người liên hệ
#     · `status` khác "moi"           → đã có người động vào hồ sơ (chăm sóc / chốt / mất)
# Chỉ soi một dấu là đếm nhầm: sale đổi trạng thái mà quên ghi giờ liên hệ vẫn là đã xử lý, và
# ngược lại. Lấy hợp thì một lead chỉ còn "quá hạn" khi THẬT SỰ không ai chạm vào.
#
# KHÔNG CÓ `received_at` THÌ KHÔNG CÓ HẠN, VÀ KHÔNG CÓ HẠN THÌ KHÔNG KẾT LUẬN QUÁ HẠN. Trả None chứ
# không mặc định là quá hạn — cùng một lẽ với "chưa đối chiếu thì chưa xác định, không phải 0%".


def han_theo_quy_tac(l: Lead, gio: float) -> datetime | None:
    """Hạn SUY RA từ quy tắc: lúc lead vào sổ cộng N giờ. None khi không biết lead vào sổ lúc nào.

    ĐỔI TÊN 18/9/2026. Bản đầu tên là `han_xu_ly`, nhưng gói bàn giao R3 mang theo một CỘT cũng tên
    `han_xu_ly` trên bảng `leads` — hạn mà NGƯỜI NHẬP hẹn cho riêng lead ấy, có cửa nhập hẳn hoi
    trong `intake_marketing.py`. Hai thứ khác nhau mà cùng một tên là cách chắc chắn nhất để sau
    này không ai biết con số trên màn hình là lời hẹn hay là luật.
        · CỘT  `Lead.han_xu_ly`   – hạn ĐÃ HẸN, người nhập ghi
        · HÀM  `han_theo_quy_tac` – hạn THEO LUẬT, suy từ tham số P.TGĐ ký
    `han_hieu_luc()` ngay dưới chọn giữa hai cái, và nói ra đã chọn cái nào.
    """
    if not l.received_at:
        return None
    return l.received_at + timedelta(hours=gio)


def han_hieu_luc(l: Lead, gio: float) -> tuple[datetime | None, str]:
    """Hạn ĐANG CÓ HIỆU LỰC cho một lead, kèm nguồn của nó.

    LỜI HẸN THẮNG LUẬT. Luật 24 giờ là mức mặc định cho lead không ai hẹn riêng; khi Sales đã hẹn
    một ngày cụ thể với khách thì đó mới là lời hứa có thật, và chấm người ta theo luật chung trong
    khi họ đã hẹn khác là chấm sai.

    Trả về ("nguồn") theo đúng lối `nguon_mau_so` của báo cáo chuyển đổi: con số nào cũng phải nói
    được nó ra từ đâu, nếu không thì không ai kiểm được.
    """
    hen = getattr(l, "han_xu_ly", None)
    if hen is not None:
        # Cột là KIỂU NGÀY. Hẹn "ngày 20" nghĩa là hết ngày 20 mới trễ, không phải 0 giờ sáng 20.
        return datetime(hen.year, hen.month, hen.day, 23, 59, 59), "da_hen"
    return han_theo_quy_tac(l, gio), "theo_quy_tac"


def da_xu_ly(l: Lead) -> bool:
    """Đã có người chạm vào lead này chưa. Xem ghi chú "HAI DẤU, LẤY HỢP" ở trên."""
    return bool(l.last_contact_at) or l.status != "moi"


def qua_han(l: Lead, gio: float, bay_gio: datetime | None = None) -> bool:
    han, _ = han_hieu_luc(l, gio)
    if han is None or da_xu_ly(l):
        return False
    return (bay_gio or datetime.now()) > han


def loc_qua_han(qs, gio: float, bay_gio: datetime | None = None):
    """Thêm điều kiện QUÁ HẠN vào một câu truy vấn Lead đã lọc sẵn.

    Có hàm này để chỗ ĐẾM và chỗ ĐÁNH DẤU TỪNG DÒNG dùng CHUNG một định nghĩa. Đếm bằng SQL còn
    đánh dấu bằng Python là hai đầu, và hai đầu thì sớm muộn lệch nhau — đúng kiểu hỏng mà bản sửa
    tỷ lệ chốt ngày 18/9 vừa dọn xong ở chỗ khác.
    """
    now = bay_gio or datetime.now()
    moc = now - timedelta(hours=gio)
    # HAI NHÁNH, ĐÚNG NHƯ `han_hieu_luc()` bên Python — và phép thử đối chiếu hai đầu canh cho
    # chúng không lệch nhau. Lead có hạn đã hẹn thì so với hạn ấy (hết ngày mới trễ); không có thì
    # so với lúc vào sổ cộng N giờ.
    het_ngay_hen = Lead.han_xu_ly < now.date()
    qua_theo_luat = Lead.received_at < moc
    return qs.where(
        Lead.last_contact_at.is_(None),
        Lead.status == "moi",
        sa.case((Lead.han_xu_ly.is_not(None), het_ngay_hen), else_=qua_theo_luat),
    )


def gio_han(db: Session) -> float:
    """Đọc hạn đã ký. Một chỗ đọc, để không ai gõ lại tên tham số ở chỗ thứ hai."""
    return float(R.get_param(db, "lead_han_xu_ly_gio"))


def dem_qua_han(db: Session, qs, gio: float | None = None, bay_gio: datetime | None = None) -> int:
    """Đếm lead quá hạn trong ĐÚNG bộ lọc đang xem — không đếm trên trang đã cắt.

    Danh sách lead cắt ở 300 dòng; đếm trên trang ấy thì con số quá hạn nhỏ hơn sự thật và nhỏ một
    cách im lặng. Nên đếm chạy trên câu truy vấn TRƯỚC khi cắt.
    """
    g = gio if gio is not None else gio_han(db)
    # GỠ limit/offset/order_by NGAY TẠI ĐÂY, không trông vào việc người gọi nhớ truyền câu chưa cắt.
    # Phép thử ngày 18/9 bắt đúng chỗ này: truyền vào câu đã .limit(2) thì hàm đếm ra 2 trong khi sổ
    # có 5 — và nó SAI THEO HƯỚNG NHỎ ĐI, kiểu sai không ai nhận ra. Một lời hứa mà phải nhờ người
    # gọi giữ hộ thì sớm muộn có người quên; gỡ ở đây là hứa bằng chính cấu trúc.
    q = loc_qua_han(qs.order_by(None).limit(None).offset(None), g, bay_gio)
    return int(db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0)


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
    chi tiết SĐT chốt: tour, ngày KH, khách mới / quay lại, số lần đi, tổng khách, doanh thu lũy kế.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    HAI TỶ LỆ, HAI TÊN – sửa 18/9/2026
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Báo cáo này trả về HAI con số tỷ lệ, và chúng KHÔNG bằng nhau. Trước bản sửa này chỉ có một
    khoá `rate`, nên hai người đọc hai nghĩa khác nhau mà không ai biết:

      `rate`                  – tỷ lệ của CHÍNH BÁO CÁO NÀY: lead kỳ X chốt tour KHỞI HÀNH TRONG
                                tháng T. Đây là một bảng chéo (kỳ lead × tháng khởi hành), có ích
                                riêng, nhưng KHÔNG phải tỷ lệ chốt của phòng Marketing.
      `ty_le_chot_overview`   – QUY TẮC CHỦ TỊCH KÝ 14/9/2026 (`overview-v1`): nhóm theo KỲ PHÁT
                                SINH LEAD, tử số gồm CẢ phần chốt ở các kỳ SAU.

    Hệ quả bắt buộc phải hiện lên màn hình: tỷ lệ theo overview-v1 CÒN TĂNG sau khi kỳ đã đóng –
    lead tháng 7 có thể chốt vào tháng 9. Nên mọi chỗ in con số ấy phải kèm `tinh_den_ngay`. In nó
    như một con số cuối cùng là hứa một điều không đúng, và tháng sau cùng một kỳ ra số khác thì
    người đọc tưởng có ai sửa sổ.

    CHƯA ĐỐI CHIẾU THÌ KHÔNG XÁC ĐỊNH, KHÔNG PHẢI 0%. `ty_le_chot_overview` đọc dấu `booking_id`
    do `match_conversions()` gắn. Chưa ai chạy đối chiếu thì trả None kèm một câu cảnh báo – 0%
    đọc là "chạy mà không ra khách", còn chưa xác định đọc là "chưa ai so sổ". Hai câu khác hẳn.

    BA ĐƠN VỊ ĐẾM, KHÔNG GỘP: `so_dong` (số dòng) · `so_sdt` (số điện thoại chuẩn hoá khác nhau,
    đơn vị "một người" theo chốt 14/9) · `so_khai_bao` (số Marketing tự khai trong LeadChannelStat).
    `nguon_mau_so` ghi rõ mẫu số đã lấy từ đâu; `lech_khai_bao` phơi ra phần chênh thay vì san phẳng.
    """
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
    # ĐẾM RIÊNG HAI ĐƠN VỊ, KHÔNG GỘP. Sửa 18/9/2026 – xem chú thích QUY_TAC_TY_LE_CHOT ở cuối hàm.
    #   so_dong = số DÒNG lead (một người liên hệ hai lần là hai dòng)
    #   so_sdt  = số SỐ ĐIỆN THOẠI ĐÃ CHUẨN HOÁ khác nhau — đơn vị "một người" theo chốt 14/9/2026
    # Nhãn màn hình phải gọi đúng tên "số điện thoại khác nhau", KHÔNG viết "số khách": hai người
    # chung một số đếm thành một, một người đổi số đếm thành hai.
    sdt_theo_key: dict[tuple, set] = {}
    for l in leads: sdt_theo_key.setdefault((l.lead_month, l.channel), set()).add(l.phone)
    # Tử số của overview-v1: SĐT của kỳ ấy đã chốt Ở BẤT KỲ LÚC NÀO (kể cả các kỳ SAU), lấy theo
    # dấu `booking_id` do match_conversions() gắn – không phụ thuộc target_month.
    chot_moi_luc: dict[tuple, set] = {}
    for l in leads:
        if l.booking_id: chot_moi_luc.setdefault((l.lead_month, l.channel), set()).add(l.phone)
    da_tung_doi_chieu = any(l.converted_at for l in leads)

    detail = []; seen = set(); agg: dict[tuple, dict] = {}
    for l in sorted(leads, key=lambda x: (x.lead_month, x.channel)):
        key = (l.lead_month, l.channel); a = agg.setdefault(key, {"lead_month": l.lead_month, "channel": l.channel, "leads": 0, "converted": 0, "new": 0, "returning": 0, "revenue": 0.0, "doanh_thu_booking_chot": 0.0})
        bs = bp.get(l.phone, []); hit = [b for b in bs if b.id in tours_in]
        if not hit or (l.phone, l.lead_month) in seen: continue
        seen.add((l.phone, l.lead_month)); b = min(hit, key=lambda x: x.tour.start_date)
        prior = [x for x in bs if x.tour and x.tour.start_date < b.tour.start_date]
        returning = len(prior) > 0; trips = len({x.tour_id for x in bs if x.tour and x.tour.start_date < d2}); pax = sum(x.pax for x in bs if x.tour and x.tour.start_date < d2)
        # `rev` là chi tiêu TRỌN ĐỜI của số điện thoại ấy (mọi booking khởi hành trước d2) – KHÔNG
        # phải doanh thu của kênh này kỳ này. Khoá `revenue` giữ NGUYÊN nghĩa cũ để không bạn đọc
        # nào lặng lẽ đổi ý nghĩa; số của riêng booking đã chốt nằm ở `doanh_thu_booking_chot`.
        rev = sum((x.amount or 0) - (x.discount or 0) for x in bs if x.tour and x.tour.start_date < d2)
        rev_chot = (b.amount or 0) - (b.discount or 0)
        a["converted"] += 1; a["new"] += 0 if returning else 1; a["returning"] += 1 if returning else 0
        a["revenue"] += rev; a["doanh_thu_booking_chot"] += rev_chot
        detail.append({"channel": l.channel, "lead_month": l.lead_month, "phone": l.phone, "name": l.name or b.customer_name, "tour": b.tour.name if b.tour else "", "tour_code": b.tour.code if b.tour else "", "start_date": b.tour.start_date if b.tour else None,
                       "kind": "Khách quay lại" if returning else "Khách mới", "trips": trips, "pax": pax, "revenue": rev, "revenue_tron_doi": rev, "doanh_thu_booking_chot": rev_chot,
                       "sales": b.sales.full_name if b.sales else "", "booking": b.code})
    rows = []
    for key in sorted(set(list(stats.keys()) + list(agg.keys()))):
        a = agg.get(key, {"lead_month": key[0], "channel": key[1], "leads": 0, "converted": 0, "new": 0, "returning": 0, "revenue": 0.0, "doanh_thu_booking_chot": 0.0})
        a["so_dong"] = lead_counts.get(key, 0); a["so_sdt"] = len(sdt_theo_key.get(key, ()))
        a["so_khai_bao"] = stats[key].leads if key in stats else None
        # BỎ max(khai_báo, đếm_được) – sửa 18/9/2026. max() chọn con số LỚN HƠN mà không nói đã
        # chọn cái nào, nên mẫu số không truy được về nguồn và tỷ lệ luôn nghiêng về phía thấp.
        # Nay: có khai báo thì dùng khai báo, không có thì dùng số đếm được, và GHI RA đã dùng cái nào.
        a["nguon_mau_so"] = "khai_bao" if a["so_khai_bao"] is not None else "dem_duoc"
        a["leads"] = a["so_khai_bao"] if a["so_khai_bao"] is not None else a["so_sdt"]
        # Chênh lệch giữa lời khai và số đếm được: HIỆN RA, không san phẳng. Lệch lớn nghĩa là tệp
        # nguồn chỉ có phần chi tiết của một số kênh – đó là việc còn thiếu, không phải số để dùng.
        a["lech_khai_bao"] = None if a["so_khai_bao"] is None else a["so_khai_bao"] - a["so_sdt"]
        a["cost"] = stats[key].cost if key in stats else 0
        a["rate"] = a["converted"] / a["leads"] if a["leads"] else 0
        # Tỷ lệ CÙNG MỘT ĐƠN VỊ: tử số và mẫu số đều là số điện thoại đếm được. `rate` ở trên chia
        # số điện thoại cho một con số khai báo – hai đơn vị khác nhau, nên nó không tự đứng được.
        a["ty_le_tren_sdt_dem_duoc"] = (a["converted"] / a["so_sdt"]) if a["so_sdt"] else None
        a["chot_moi_luc"] = len(chot_moi_luc.get(key, ()))
        a["ty_le_chot_overview"] = (a["chot_moi_luc"] / a["so_sdt"]) if (a["so_sdt"] and da_tung_doi_chieu) else None
        a["cost_per_lead"] = (a["cost"] or 0) / a["leads"] if a["leads"] and (a["cost"] or 0) else 0; rows.append(a)
    # SỐ NGƯỜI THEO THÁNG KHÔNG PHẢI TỔNG SỐ NGƯỜI TỪNG KÊNH. Một người liên hệ qua hai kênh trong
    # cùng tháng là MỘT số điện thoại, nhưng cộng hai dòng kênh lại thì thành hai. Nên mức tháng
    # phải đếm lại trên TẬP HỢP, không cộng dồn — cùng một lý do đã bắt `so_sdt` ra đời.
    sdt_thang: dict[str, set] = {}
    chot_thang: dict[str, set] = {}
    for l in leads:
        sdt_thang.setdefault(l.lead_month, set()).add(l.phone)
        if l.booking_id: chot_thang.setdefault(l.lead_month, set()).add(l.phone)
    by_month = {}
    for a in rows:
        mm = by_month.setdefault(a["lead_month"], {"lead_month": a["lead_month"], "leads": 0, "converted": 0, "new": 0, "returning": 0, "revenue": 0.0,
                                                   "doanh_thu_booking_chot": 0.0, "so_dong": 0})
        for k in ("leads", "converted", "new", "returning", "revenue", "doanh_thu_booking_chot", "so_dong"): mm[k] += a[k]
    for ky, mm in by_month.items():
        mm["so_sdt"] = len(sdt_thang.get(ky, ()))
        mm["chot_moi_luc"] = len(chot_thang.get(ky, ()))
    for mm in by_month.values():
        mm["rate"] = mm["converted"] / mm["leads"] if mm["leads"] else 0
        mm["ty_le_tren_sdt_dem_duoc"] = (mm["converted"] / mm["so_sdt"]) if mm["so_sdt"] else None
        mm["ty_le_chot_overview"] = (mm["chot_moi_luc"] / mm["so_sdt"]) if (mm["so_sdt"] and da_tung_doi_chieu) else None
    cur = [a for a in rows if a["lead_month"] == target_month]
    tot = {"leads": sum(a["leads"] for a in cur), "converted": sum(a["converted"] for a in cur),
           "so_sdt": len(sdt_thang.get(target_month, ())), "chot_moi_luc": len(chot_thang.get(target_month, ()))}
    tot["rate"] = tot["converted"] / tot["leads"] if tot["leads"] else 0
    tot["ty_le_tren_sdt_dem_duoc"] = (tot["converted"] / tot["so_sdt"]) if tot["so_sdt"] else None
    tot["ty_le_chot_overview"] = (tot["chot_moi_luc"] / tot["so_sdt"]) if (tot["so_sdt"] and da_tung_doi_chieu) else None
    return {"target_month": target_month, "lead_months": lead_months, "by_channel_current": cur, "total_current": tot, "by_month": sorted(by_month.values(), key=lambda x: x["lead_month"]),
            "by_channel_month": rows, "detail": sorted(detail, key=lambda x: (x["channel"], x["lead_month"], -(x["revenue"] or 0))), "as_of": datetime.now(),
            "quy_tac_ty_le_chot": QUY_TAC_TY_LE_CHOT, "tinh_den_ngay": datetime.now(),
            "da_doi_chieu": da_tung_doi_chieu,
            "canh_bao": [] if da_tung_doi_chieu else ["Chưa chạy đối chiếu lead ↔ booking, nên tỷ lệ chốt theo quy tắc đã ký CHƯA XÁC ĐỊNH (không phải 0%)."]}


def to_xlsx(rep: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = f"Tong hop {rep['target_month']}"
    def head(ws, cols): ws.append(cols); [setattr(c, "font", Font(bold=True)) or setattr(c, "fill", PatternFill("solid", fgColor="D9E2F3")) for c in ws[ws.max_row]]
    ws.append([f"BÁO CÁO LEAD & CHUYỂN ĐỔI THÁNG {rep['target_month']} (VTOS, {rep['as_of']:%d/%m/%Y %H:%M})"]); ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Quy tắc tỷ lệ chốt: {rep.get('quy_tac_ty_le_chot','')} — nhóm theo kỳ phát sinh lead, tử số gồm cả phần chốt ở các kỳ sau. "
               f"Tính đến {rep['as_of']:%d/%m/%Y %H:%M}; con số này CÒN TĂNG khi lead kỳ cũ chốt ở kỳ sau."])
    for c in rep.get("canh_bao", []): ws.append([f"CẢNH BÁO: {c}"])
    ws.append([])
    # Cột "Tỷ lệ chốt" của bảng này là tỷ lệ CHÉO (lead kỳ X → tour khởi hành tháng T), KHÔNG phải
    # tỷ lệ chốt theo quy tắc đã ký. Hai cột cuối mới là con số theo `overview-v1`, và chúng có tên
    # riêng để không ai đem hai thước so với nhau. Rỗng = chưa đối chiếu, không phải 0%.
    ws.append([f"1. Lead tháng {rep['target_month']} → tour khởi hành tháng {rep['target_month']} theo kênh"])
    head(ws, ["Kênh", "Số leads", "Nguồn mẫu số", "SĐT khác nhau đếm được", "Lệch so với khai báo", "SĐT chốt tour (khởi hành trong tháng)", "Tỷ lệ chéo (khởi hành trong tháng)",
              f"SĐT đã chốt mọi lúc ({rep.get('quy_tac_ty_le_chot','')})", f"TỶ LỆ CHỐT ({rep.get('quy_tac_ty_le_chot','')})", "Khách mới", "Khách quay lại", "Doanh thu lũy kế (đ)", "Doanh thu booking đã chốt (đ)", "Chi phí/lead"])
    for a in rep["by_channel_current"]:
        ws.append([a["channel"], a["leads"], a.get("nguon_mau_so", ""), a.get("so_sdt"), a.get("lech_khai_bao"), a["converted"], round(a["rate"], 4),
                   a.get("chot_moi_luc"), (round(a["ty_le_chot_overview"], 4) if a.get("ty_le_chot_overview") is not None else ""),
                   a["new"], a["returning"], round((a["revenue"] or 0)), round((a.get("doanh_thu_booking_chot") or 0)), round(a["cost_per_lead"])])
    t = rep["total_current"]; ws.append(["TỔNG", t["leads"], t["converted"], round(t["rate"], 4)]); ws.append([])
    ws.append([f"2. Đối chiếu lead các tháng → tour tháng {rep['target_month']}"]); head(ws, ["Tháng lead", "Tổng leads", "SĐT có tour", "Tỷ lệ chốt", "Khách mới", "Khách quay lại", "Doanh thu lũy kế (đ)"])
    for mm in rep["by_month"]: ws.append([mm["lead_month"], mm["leads"], mm["converted"], round(mm["rate"], 4), mm["new"], mm["returning"], round((mm["revenue"] or 0))])
    ws.append([]); ws.append(["3. Chi tiết kênh × tháng lead"]); head(ws, ["Kênh", "Tháng lead", "Tổng leads", "SĐT có tour", "Tỷ lệ chốt", "Khách mới", "Khách quay lại", "Doanh thu lũy kế (đ)"])
    for a in rep["by_channel_month"]: ws.append([a["channel"], a["lead_month"], a["leads"], a["converted"], round(a["rate"], 4), a["new"], a["returning"], round((a["revenue"] or 0))])
    ws2 = wb.create_sheet(f"Chi tiet SDT da chot"); head(ws2, ["STT", "Kênh", "Tháng lead", "SĐT", "Tên khách hàng", "Tour", "Mã tour", "Ngày khởi hành", "Phân loại", "Số lần đi (lũy kế)", "Tổng khách (lũy kế)", "Doanh thu lũy kế (đ)", "Sale", "Booking"])
    for i, d in enumerate(rep["detail"], 1): ws2.append([i, d["channel"], d["lead_month"], d["phone"], d["name"], d["tour"], d["tour_code"], d["start_date"].strftime("%d/%m/%Y") if d["start_date"] else "", d["kind"], d["trips"], d["pax"], round((d["revenue"] or 0)), d["sales"], d["booking"]])
    for w in (ws, ws2):
        for col in w.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8); w.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 48)
    bio = BytesIO(); wb.save(bio); return bio.getvalue()


def _han_ra(l: Lead, db: Session) -> dict:
    """Đọc hạn đã ký MỘT lần cho mỗi dòng, rồi tính cả hai khoá từ đúng con số ấy.

    Bản đầu gọi gio_han(db) hai lần trong cùng một dòng. Bộ đệm tham số làm nó rẻ, nhưng hai lần đọc
    thì có hai cơ hội đọc ra hai giá trị khác nhau nếu ai đó duyệt tham số đúng lúc — và một dòng có
    hạn của luật cũ kèm cờ quá hạn của luật mới thì không giải thích được cho ai.
    """
    g = gio_han(db)
    han, nguon = han_hieu_luc(l, g)
    return {"han_xu_ly": han, "nguon_han": nguon, "qua_han": qua_han(l, g)}


def lead_out(l: Lead, db: Session | None = None) -> dict:
    s = db.get(User, l.sales_id) if (db and l.sales_id) else None
    b = db.get(Booking, l.booking_id) if (db and l.booking_id) else None
    return {"id": l.id, "phone": l.phone, "name": l.name, "channel": l.channel, "lead_month": l.lead_month, "received_at": l.received_at, "campaign": l.campaign, "interest": l.interest, "sales_id": l.sales_id,
            "sales_name": s.full_name if s else "", "status": l.status, "status_name": LEAD_STATUS.get(l.status, l.status), "note": l.note, "zalo_uid": l.zalo_uid, "zalo_follow": l.zalo_follow,
            "last_contact_at": l.last_contact_at, "booking_id": l.booking_id, "booking_code": b.code if b else "", "booking_tour": b.tour.code if b and b.tour else "", "converted_at": l.converted_at, "created_at": l.created_at,
            # HẠN XỬ LÝ (P.TGĐ Phan Ngọc Tuấn chốt 18/9/2026). Cần `db` để đọc tham số đã ký; gọi
            # lead_out() không kèm db thì hai khoá này là None — KHÔNG đoán bằng một số viết cứng.
            **(_han_ra(l, db) if db else {"han_xu_ly": None, "nguon_han": None, "qua_han": None})}
