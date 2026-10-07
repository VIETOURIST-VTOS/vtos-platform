"""Đợt 4 – Tài chính, báo cáo và chuyển dữ liệu cho phân hệ Visa.

Nguyên tắc số một (mục 11.2 của đặc tả): **KHÔNG xây sổ thu–chi riêng cho Visa.** Tiền bạc đọc từ phân hệ
Tài chính & Kế toán qua booking mà hồ sơ trỏ tới. Phân hệ này không giữ một đồng nào của riêng nó.

Chỗ dễ sai nhất là phân bổ phí gia đình. Cả nhà nộp một khoản trên MỘT booking; muốn xem lãi lỗ theo từng
đương đơn thì phải chia ra. Nhưng số chia ra là số QUẢN TRỊ, không phải chứng từ – và tổng các phần chia
phải bằng đúng số trên booking, không lệch một đồng (tiêu chí nghiệm thu 14). Phép chia số nguyên đồng luôn
để lại phần dư, nên phần dư được dồn vào một hồ sơ đã xác định trước chứ không để mỗi nơi làm tròn một kiểu.
"""
import csv
import io
from collections import Counter
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Booking, Tour
from app.models.payments import Receipt, Retention
from app.models.ops import PaymentRequest
from app.models.visa import VisaCase, VisaResult, VisaTask, STAGES
from app.services import rules as R
from app.services import so_lo_nap as SLN
from app.services.visa import VisaError, get_case, ensure_see, scope, _audit, resolve_company

# Vai trò được xem cơ cấu tiền: theo ma trận sẵn có của VTOS, Kinh doanh KHÔNG xem giá vốn.
MONEY_ROLES = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "ketoan", "cntt", "bks", "tp_dh")
REPORT_LIMIT = 20000        # số hồ sơ tối đa một lần báo cáo gom vào bộ nhớ


# ---------- Phân bổ phí theo từng đương đơn ----------

def _siblings(db: Session, c: VisaCase) -> list[VisaCase]:
    """Các hồ sơ cùng chia một booking. Hồ sơ đã hủy KHÔNG gánh phí."""
    if not c.booking_id:
        return [c]
    rows = list(db.execute(select(VisaCase).where(VisaCase.booking_id == c.booking_id,
                                                  VisaCase.lifecycle_status != "CANCELLED")
                           .order_by(VisaCase.id)).scalars())
    return rows or [c]


def split_amount(total: float, cases: list[VisaCase]) -> dict[int, int]:
    """Chia `total` cho các hồ sơ theo trọng số, làm tròn tới ĐỒNG, tổng luôn khớp tuyệt đối.

    Phần dư do làm tròn dồn hết vào hồ sơ có id nhỏ nhất (hồ sơ mở đầu tiên) – chọn một quy tắc cố định để
    hai lần chạy cho ra cùng kết quả, và để không ai phải đoán vì sao tổng lệch mấy đồng.
    """
    if not cases:
        return {}
    w = {c.id: float(c.fee_weight) if c.fee_weight and c.fee_weight > 0 else 1.0 for c in cases}
    tw = sum(w.values())
    total_dong = int(round(total))
    out, used = {}, 0
    order = sorted(cases, key=lambda c: c.id)
    for c in order[1:]:
        v = int(round(total_dong * w[c.id] / tw))
        out[c.id] = v
        used += v
    out[order[0].id] = total_dong - used          # hồ sơ đầu gánh phần dư ⇒ tổng khớp tuyệt đối
    return out


def finance_for_case(db: Session, u: User, c: VisaCase) -> dict:
    """Thu – chi liên quan tới một hồ sơ, đọc từ phân hệ tài chính. Không có số nào sinh ra ở đây."""
    if u.role not in MONEY_ROLES:
        raise VisaError("Vai trò của bạn không được xem số liệu thu – chi")
    if not c.booking_id:
        return {"co_booking": False,
                "ghi_chu": "Hồ sơ chưa gắn booking nên chưa đọc được thu – chi. Visa lẻ phải tạo booking "
                           "dịch vụ lẻ (service_type=VISA) rồi gắn vào hồ sơ."}
    b = db.get(Booking, c.booking_id)
    if not b:
        raise VisaError("Booking gắn với hồ sơ không còn tồn tại")

    receipts = list(db.execute(select(Receipt).where(Receipt.booking_id == b.id)).scalars())
    da_thu = sum((r.amount or 0) for r in receipts if r.status != "huy")
    da_xac_nhan = sum((r.amount or 0) for r in receipts if r.status == "ke_toan_xac_nhan")
    retentions = list(db.execute(select(Retention).where(Retention.booking_id == b.id)).scalars())
    # Chi: đề nghị chi gắn theo TOUR chứ không theo booking, nên chỉ lấy được với visa theo tour và phải nói rõ
    # đó là chi của cả tour, không phải của riêng hồ sơ này.
    chi_tour = []
    if c.tour_id:
        chi_tour = list(db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == c.tour_id,
                                                                PaymentRequest.status == "da_chi")).scalars())

    kin = _siblings(db, c)
    doanh_thu = float(b.amount or 0) - float(b.discount or 0)
    gia_von = float(b.cost_amount or 0)
    chia_dt, chia_gv, chia_thu = split_amount(doanh_thu, kin), split_amount(gia_von, kin), split_amount(da_thu, kin)
    return {
        "co_booking": True,
        "booking": {"code": b.code, "khach": b.customer_name, "loai_dich_vu": b.service_type,
                    "trang_thai_thanh_toan": b.pmt_status, "so_khach": b.pax},
        "cua_booking": {"doanh_thu": doanh_thu, "gia_von_ncc": gia_von, "da_thu": da_thu,
                        "da_thu_ke_toan_xac_nhan": da_xac_nhan, "con_phai_thu": doanh_thu - da_thu,
                        "bao_luu": sum((r.remaining or 0) for r in retentions if r.status == "hieu_luc")},
        "phan_bo_cho_ho_so_nay": {
            "so_ho_so_chia_chung": len(kin), "trong_so": c.fee_weight or 1.0,
            "doanh_thu": chia_dt.get(c.id, 0), "gia_von_ncc": chia_gv.get(c.id, 0), "da_thu": chia_thu.get(c.id, 0),
            "lai_lo_du_kien": chia_dt.get(c.id, 0) - chia_gv.get(c.id, 0)},
        "phieu_thu": [{"code": r.code, "so_tien": r.amount, "hinh_thuc": r.method, "nguoi_nop": r.payer,
                       "trang_thai": r.status, "luc": r.created_at} for r in receipts],
        "chi_theo_tour": [{"code": p.code, "ncc": p.supplier_name, "so_tien": p.amount,
                           "noi_dung": p.description, "luc": p.paid_at} for p in chi_tour],
        "luu_y": ("Phần phân bổ là số QUẢN TRỊ để xem lãi lỗ từng người, không phải chứng từ – chứng từ vẫn là "
                  "phiếu thu của booking. Tổng phân bổ của tất cả hồ sơ cùng booking luôn bằng đúng số của "
                  "booking. Mục «chi theo tour» là chi của CẢ TOUR, không phải riêng hồ sơ này."),
    }


def set_fee_weight(db: Session, u: User, c: VisaCase, weight: float | None) -> VisaCase:
    """Đặt trọng số phân bổ phí. Để trống là chia đều."""
    if u.role not in MONEY_ROLES:
        raise VisaError("Vai trò của bạn không được đặt trọng số phân bổ phí")
    if weight is not None and weight <= 0:
        raise VisaError("Trọng số phải lớn hơn 0")
    before = c.fee_weight
    c.fee_weight = weight
    c.row_version += 1
    _audit(db, u, "visa_dat_trong_so_phi", c, before={"trong_so": before}, after={"trong_so": weight})
    return c


def check_allocation(db: Session, booking_id: int) -> dict:
    """Đối chiếu (nghiệm thu 14): tổng phân bổ của mọi hồ sơ cùng booking phải bằng đúng số của booking."""
    b = db.get(Booking, booking_id)
    if not b:
        raise VisaError("Không có booking này")
    cases = list(db.execute(select(VisaCase).where(VisaCase.booking_id == booking_id,
                                                   VisaCase.lifecycle_status != "CANCELLED")).scalars())
    if not cases:
        return {"booking": b.code, "so_ho_so": 0, "khop": True, "ghi_chu": "Booking chưa có hồ sơ Visa nào"}
    dt = int(round(float(b.amount or 0) - float(b.discount or 0)))
    chia = split_amount(dt, cases)
    tong = sum(chia.values())
    return {"booking": b.code, "so_ho_so": len(cases), "doanh_thu_booking": dt, "tong_phan_bo": tong,
            "lech": tong - dt, "khop": tong == dt,
            "chi_tiet": [{"case_id": k, "phan_bo": v} for k, v in sorted(chia.items())]}


# ---------- Báo cáo Visa ----------

def _days(a: datetime | None, b: datetime | None) -> float | None:
    if not a or not b:
        return None
    return round((b - a).total_seconds() / 86400, 1)


def report(db: Session, u: User, f: dict) -> dict:
    """Báo cáo Visa theo kỳ: khối lượng, kết quả, thời gian xử lý, và tiền (chỉ với vai trò được xem tiền).

    Đếm theo HỒ SƠ, không gộp nhóm gia đình thành một dòng – một nhà bốn người là bốn hồ sơ, bốn kết quả."""
    q = select(VisaCase)
    if f.get("since"):
        q = q.where(VisaCase.created_at >= datetime.combine(f["since"], datetime.min.time()))
    if f.get("upto"):
        q = q.where(VisaCase.created_at <= datetime.combine(f["upto"], datetime.max.time()))
    if f.get("market_code"):
        q = q.where(VisaCase.market_code == f["market_code"].upper())
    if f.get("company_id"):
        q = q.where(VisaCase.company_id == int(f["company_id"]))
    if not f.get("include_test"):
        q = q.where(VisaCase.is_test == False)
    # Giới hạn cứng: báo cáo là để nhìn tổng thể, không phải để kéo cả cơ sở dữ liệu vào bộ nhớ. Vượt ngưỡng
    # thì phải thu hẹp kỳ hoặc thị trường – nói thẳng còn hơn âm thầm làm sập máy chủ.
    n = int(db.execute(select(func.count()).select_from(scope(u, q).subquery())).scalar() or 0)
    if n > REPORT_LIMIT:
        raise VisaError(f"Kỳ này có {n:,} hồ sơ, vượt mức {REPORT_LIMIT:,} cho một lần báo cáo. "
                        f"Thu hẹp khoảng ngày hoặc lọc theo thị trường rồi xem lại.".replace(",", "."))
    cases = list(db.execute(scope(u, q)).scalars())
    ids = [c.id for c in cases]
    results = {r.case_id: r for r in db.execute(
        select(VisaResult).where(VisaResult.case_id.in_(ids or [0]))).scalars()} if ids else {}
    names = {x.id: x.full_name for x in db.execute(select(User)).scalars()}

    def bucket(key_fn):
        out: dict = {}
        for c in cases:
            k = key_fn(c)
            d = out.setdefault(k, {"tong": 0, "duoc_cap": 0, "tu_choi": 0, "dang_xu_ly": 0, "huy": 0,
                                   "ngay_xu_ly": []})
            d["tong"] += 1
            if c.lifecycle_status == "CANCELLED":
                d["huy"] += 1
            elif c.result_status == "GRANTED":
                d["duoc_cap"] += 1
            elif c.result_status == "REFUSED":
                d["tu_choi"] += 1
            else:
                d["dang_xu_ly"] += 1
            r = results.get(c.id)
            if r:
                n = _days(c.created_at, datetime.combine(r.received_on, datetime.min.time()))
                if n is not None and n >= 0:
                    d["ngay_xu_ly"].append(n)
        for d in out.values():
            xs = d.pop("ngay_xu_ly")
            d["ngay_xu_ly_tb"] = round(sum(xs) / len(xs), 1) if xs else None
            xong = d["duoc_cap"] + d["tu_choi"]
            # Tỉ lệ đậu tính trên số hồ sơ ĐÃ CÓ KẾT QUẢ, không tính hồ sơ đang xử lý – nếu không thì tháng
            # nào nhận nhiều hồ sơ mới cũng tự nhiên "tỉ lệ đậu thấp".
            d["ty_le_duoc_cap"] = round(100 * d["duoc_cap"] / xong, 1) if xong else None
        return out

    out = {
        "ky": {"tu": f.get("since"), "den": f.get("upto")},
        "tong_ho_so": len(cases),
        "theo_thi_truong": bucket(lambda c: c.market_code),
        "theo_chuyen_vien": bucket(lambda c: names.get(c.visa_owner_user_id, "(chưa phân công)")),
        "theo_giai_doan": dict(Counter(STAGES.get(c.current_stage, c.current_stage) for c in cases
                                       if c.lifecycle_status == "ACTIVE")),
        "ghi_chu": "Đếm theo hồ sơ từng đương đơn. Tỉ lệ được cấp tính trên số hồ sơ đã có kết quả. "
                   "Hồ sơ thử nghiệm không tính (trừ khi chọn hiện).",
    }
    if u.role in MONEY_ROLES:
        # Cộng tiền bằng HAI câu lệnh tổng hợp, không lặp từng booking. Bản đầu gọi db.get(Booking) trong vòng
        # lặp: với vài nghìn hồ sơ là vài nghìn lượt truy vấn cộng vài nghìn đối tượng nằm trong bộ nhớ – đúng
        # kiểu đã làm sập máy chủ 512 MB một lần với bộ sổ kế toán. Máy chủ nhỏ thì phải để cơ sở dữ liệu cộng.
        bids = list({c.booking_id for c in cases if c.booking_id})
        dt = gv = thu = 0.0
        if bids:
            row = db.execute(select(func.coalesce(func.sum(Booking.amount), 0),
                                    func.coalesce(func.sum(Booking.discount), 0),
                                    func.coalesce(func.sum(Booking.cost_amount), 0))
                             .where(Booking.id.in_(bids))).one()
            dt, gv = float(row[0]) - float(row[1]), float(row[2])
            thu = float(db.execute(select(func.coalesce(func.sum(Receipt.amount), 0))
                                   .where(Receipt.booking_id.in_(bids), Receipt.status != "huy")).scalar() or 0)
        out["tien"] = {"doanh_thu": dt, "gia_von_ncc": gv, "lai_go_du_kien": dt - gv, "da_thu": thu,
                       "con_phai_thu": dt - thu, "so_booking": len(bids),
                       "ghi_chu": "Cộng theo BOOKING liên quan, mỗi booking chỉ tính một lần dù có nhiều hồ sơ."}
    return out


# ---------- Chuyển dữ liệu từ Visa Portal ----------

COLS = {"ma_ho_so": ("ma_ho_so", "case_code", "ma", "id"),
        "ten": ("ten", "ho_ten", "applicant", "applicant_name", "khach"),
        "ngay_sinh": ("ngay_sinh", "dob", "birthday"),
        "thi_truong": ("thi_truong", "market", "market_code", "quoc_gia"),
        "loai_visa": ("loai_visa", "visa_type"),
        "ngay_di": ("ngay_di", "departure", "departure_date"),
        "booking": ("booking", "booking_id", "booking_code", "ma_booking"),
        "ket_qua": ("ket_qua", "result", "outcome"),
        "ghi_chu": ("ghi_chu", "note", "notes"),
        "la_thu_nghiem": ("test", "is_test", "thu_nghiem")}


def _norm(h: str) -> str:
    return (h or "").strip().lower().replace(" ", "_").replace("-", "_")


def _rows(data: bytes, filename: str) -> list[dict]:
    if data[:2] == b"PK" or filename.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        it = ws.iter_rows(values_only=True)
        head = [_norm(str(x)) for x in next(it, [])]
        return [dict(zip(head, r)) for r in it]
    text = data.decode("utf-8-sig", errors="replace")
    rd = csv.DictReader(io.StringIO(text))
    return [{_norm(k): v for k, v in r.items()} for r in rd]


def _pick(row: dict, key: str):
    for alias in COLS[key]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return None


def _as_date(v):
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def import_portal(db: Session, u: User, data: bytes, filename: str, apply: bool = False) -> dict:
    """Nạp hồ sơ từ Visa Portal. Mặc định chỉ XEM TRƯỚC; muốn ghi thật phải gọi lại với apply=True.

    Nguyên tắc theo mục 14: giữ mã nguồn cũ để truy vết, hồ sơ nghi trùng đưa vào đối chiếu chứ KHÔNG tự xóa,
    và dữ liệu ghi "test" phải được xác nhận chứ không tự suy ra cả lô là thử nghiệm."""
    from app.services.visa import create_case, find_possible_duplicates
    rows = _rows(data, filename)
    if not rows:
        raise VisaError("Tệp không có dòng dữ liệu nào")
    have = {c.source_record_id: c for c in db.execute(
        select(VisaCase).where(VisaCase.source_system == "visa_portal")).scalars() if c.source_record_id}

    tao_moi, da_co, loi, nghi_trung, danh_dau_test = [], [], [], [], []
    for i, row in enumerate(rows, start=2):
        src = str(_pick(row, "ma_ho_so") or "").strip()
        ten = str(_pick(row, "ten") or "").strip()
        tt = str(_pick(row, "thi_truong") or "").strip().upper()
        if not ten or not tt:
            loi.append({"dong": i, "ly_do": "thiếu tên đương đơn hoặc thị trường", "ma_nguon": src})
            continue
        if src and src in have:
            da_co.append({"dong": i, "ma_nguon": src, "case_code": have[src].case_code})
            continue
        dep = _as_date(_pick(row, "ngay_di"))
        is_test = str(_pick(row, "la_thu_nghiem") or "").strip().lower() in ("1", "true", "x", "co", "có", "yes")
        if is_test:
            danh_dau_test.append({"dong": i, "ten": ten})
        dups = find_possible_duplicates(db, ten, tt, dep, None, resolve_company(db))
        if dups:
            nghi_trung.append({"dong": i, "ten": ten, "trung_voi": [d.case_code for d in dups]})
        payload = {"applicant_name": ten, "market_code": tt, "applicant_dob": _as_date(_pick(row, "ngay_sinh")),
                   "visa_type": str(_pick(row, "loai_visa") or ""), "departure_date": dep,
                   "service_mode": "STANDALONE", "source_system": "visa_portal", "source_record_id": src,
                   "is_test": is_test, "note": str(_pick(row, "ghi_chu") or "")}
        if not apply:
            tao_moi.append({"dong": i, "ten": ten, "thi_truong": tt, "ngay_di": str(dep or "")})
            continue
        try:
            # "independent" vì đây là chuyển dữ liệu lịch sử: nghi trùng đã liệt kê để người dùng đối chiếu,
            # gộp nhầm hai người trùng tên còn tai hại hơn là để hai hồ sơ rồi rà tay.
            c = create_case(db, u, payload, on_duplicate="independent")
            tao_moi.append({"dong": i, "case_code": c.case_code, "ten": ten})
        except VisaError as ex:
            loi.append({"dong": i, "ly_do": str(ex), "ma_nguon": src})

    kq = {"tep": filename, "so_dong": len(rows), "che_do": "thuc_hien" if apply else "xem_truoc",
          "tao_moi": len(tao_moi), "da_co_tu_truoc": len(da_co), "loi": len(loi),
          "nghi_trung": len(nghi_trung), "danh_dau_thu_nghiem": len(danh_dau_test),
          "chi_tiet": {"tao_moi": tao_moi[:50], "da_co": da_co[:50], "loi": loi[:50],
                       "nghi_trung": nghi_trung[:50], "thu_nghiem": danh_dau_test[:50]},
          "luu_y": ("Hồ sơ nghi trùng VẪN được tạo và liệt kê ở đây để đối chiếu tay – hệ thống không tự gộp, "
                    "cũng không tự xóa. Dòng ghi test chỉ được đánh dấu thử nghiệm khi CHÍNH cột đó ghi, "
                    "không suy ra cả lô.")}
    if apply:
        # K5 – NHẬT KÝ LÔ, CHỈ ở chế độ làm thật. Lượt xem trước không ghi gì vào bảng nghiệp vụ nên
        # nó cũng không được để lại một dòng sổ nói rằng đã nạp; người dùng thường bấm xem trước vài
        # lần trước khi bấm thật, và mỗi lượt một dòng sổ thì bộ đối chiếu đếm lô gấp mấy lần.
        #
        # Hồ sơ visa KHÔNG mang tiền ở cửa này (tiền đi đường khác), nên bốn ô tiền để TRỐNG.
        SLN.ghi_lo(db, loai="visa_portal", so_dong=len(rows), da_nap=len(tao_moi),
                   bo_qua_da_co=len(da_co), dong_loi=len(loi), ten_tep=filename,
                   boi=u.username, nguon="nap_tep", dau_vao=rows,
                   ket_qua={"nghi_trung": len(nghi_trung), "danh_dau_thu_nghiem": len(danh_dau_test),
                            "loi": loi[:30]})
        R.audit(db, u.username, u.role, "visa_nap_du_lieu_portal", f"visa_portal:{filename}",
                after={k: kq[k] for k in ("so_dong", "tao_moi", "da_co_tu_truoc", "loi", "nghi_trung")})
    return kq


def reconcile_portal(db: Session) -> dict:
    """Báo cáo đối chiếu sau chuyển đổi (mục 14): còn hồ sơ nào chưa ánh xạ, còn gì phải xử lý tay."""
    tong = int(db.execute(select(func.count(VisaCase.id))).scalar() or 0)
    tu_portal = list(db.execute(select(VisaCase).where(VisaCase.source_system == "visa_portal")).scalars())
    thieu_ma = [c.case_code for c in tu_portal if not c.source_record_id]
    chua_booking = [c.case_code for c in tu_portal if not c.booking_id]
    chua_phan_cong = [c.case_code for c in tu_portal if not c.visa_owner_user_id
                      and c.lifecycle_status == "ACTIVE"]
    trung_ten = [t for t, n in Counter((c.applicant_name or "").strip().lower()
                                       for c in tu_portal).items() if n > 1 and t]
    return {"tong_ho_so_trong_he_thong": tong, "tu_visa_portal": len(tu_portal),
            "thieu_ma_nguon": thieu_ma[:50], "chua_gan_booking": chua_booking[:50],
            "chua_phan_cong": chua_phan_cong[:50], "ten_xuat_hien_nhieu_lan": trung_ten[:50],
            "ghi_chu": "Danh sách này để rà tay, không phải lỗi. Hồ sơ chưa gắn booking thì chưa đọc được "
                       "thu – chi; hồ sơ trùng tên có thể là hai người khác nhau."}
