"""Tính khấu hao TSCĐ & phân bổ chi phí trả trước – theo cách làm của MISA.

Quy trình mỗi kỳ (giống phân hệ TSCĐ / CCDC của MISA):
  1. Kế toán mở "Bảng tính khấu hao" của kỳ → hệ thống tính mức trích từng thẻ tài sản (đường thẳng, tròn tháng).
  2. Xem lại bảng, rồi bấm "Ghi sổ" → sinh MỘT chứng từ tổng hợp Nợ chi phí / Có hao mòn, gộp dòng theo
     (TK chi phí, TK hao mòn, công trình, bộ phận) đúng như MISA gộp theo bộ phận sử dụng.
  3. Bảng đã ghi sổ là bất biến: muốn sửa thì đảo chứng từ rồi tính lại.

Nguyên tắc số học (bám TT45 và cách MISA tính mặc định):
  - Mức trích tháng = (nguyên giá − giá trị thu hồi ước tính) / số tháng sử dụng, làm tròn về đồng.
  - Trích tròn tháng kể từ tháng đưa vào sử dụng; kỳ cuối lấy đúng phần giá trị còn lại (không trích vượt).
  - Tài sản nạp từ số dư ban đầu: "opening_accumulated" là hao mòn lũy kế tới hết "opening_period",
    các kỳ sau đó mới trích tiếp trên VTOS – tránh trích trùng phần MISA đã trích.
  - Không "trích bù" kỳ bị bỏ sót: mỗi kỳ đúng một mức trích tháng, lịch khấu hao dịch về sau. Kế toán nhìn
    cột "Còn lại" và "Số kỳ còn" để biết ngay nếu có kỳ chưa chạy.
"""
from datetime import date, datetime
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.assets import (FixedAsset, AssetDepreciation, PrepaidExpense, PrepaidAllocation,
                               ASSET_KINDS, ASSET_STATUS, PREPAID_KINDS, PREPAID_STATUS)
from app.models.core import User
from app.models.accounting import Account
from app.services import accounting as ACC
from app.services import rules as R


def _period_of(d: date) -> str:
    return f"{d:%Y-%m}"


def _months_between(start: str, period: str) -> int:
    """Số thứ tự của kỳ 'period' trong lịch bắt đầu từ kỳ 'start' (kỳ đầu tiên = 1)."""
    y0, m0 = int(start[:4]), int(start[5:7])
    y1, m1 = int(period[:4]), int(period[5:7])
    return (y1 - y0) * 12 + (m1 - m0) + 1


def _straight_line(monthly: float, remaining: float, idx: int, total_months: int) -> float:
    """Mức trích/phân bổ một kỳ: bình thường là mức tháng, KỲ CUỐI theo lịch lấy trọn phần còn lại
    để phần lẻ do làm tròn không đẻ thêm một kỳ 1 đồng (MISA cũng dồn số lẻ vào kỳ cuối)."""
    if remaining <= 0:
        return 0.0
    if idx >= total_months:
        return round(remaining, 0)
    return max(min(monthly, remaining), 0.0)


def period_last_day(period: str) -> date:
    """Ngày cuối cùng của kỳ (ngày hạch toán của bút toán khấu hao/phân bổ – giống MISA)."""
    from datetime import timedelta
    y, m = int(period[:4]), int(period[5:7])
    first_next = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return first_next - timedelta(days=1)


def _next_code(db: Session, model, prefix: str) -> str:
    # Số lấy theo SỐ LỚN NHẤT đã cấp cho đúng tiền tố này, không phải số dòng cả bảng —
    # xem `services/ma_tu_sinh.py` cho ba chỗ hỏng của lối đếm cũ.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, model, prefix, 4)


# ---------- Khấu hao TSCĐ ----------

def monthly_depreciation(a: FixedAsset) -> float:
    """Mức trích khấu hao một tháng (đường thẳng)."""
    if a.depr_months <= 0:
        return 0.0
    return round(max((a.cost or 0) - (a.salvage or 0), 0.0) / a.depr_months, 0)


def asset_prior_accumulated(db: Session, a: FixedAsset, period: str) -> float:
    """Hao mòn lũy kế trước kỳ 'period': số dư ban đầu + các kỳ đã tính trên VTOS."""
    got = db.execute(select(func.coalesce(func.sum(AssetDepreciation.amount), 0.0))
                     .where(AssetDepreciation.asset_id == a.id, AssetDepreciation.period < period)).scalar() or 0.0
    return round((a.opening_accumulated or 0.0) + got, 0)


def asset_depreciation_amount(db: Session, a: FixedAsset, period: str) -> float:
    """Mức trích của thẻ tài sản trong kỳ – 0 nếu chưa tới kỳ bắt đầu, đã ngừng trích, đã thanh lý, hoặc hết giá trị."""
    if a.depr_months <= 0 or (a.cost or 0) <= 0 or a.status == "ngung_kh":
        return 0.0
    if period < _period_of(a.start_date):
        return 0.0
    if a.opening_period and period <= a.opening_period:
        return 0.0                                        # phần này MISA đã trích, không trích lại
    if a.status == "thanh_ly" and a.disposed_date and _period_of(a.disposed_date) <= period:
        return 0.0                                        # thôi trích từ tháng thanh lý
    depreciable = max((a.cost or 0) - (a.salvage or 0), 0.0)
    remaining = round(depreciable - asset_prior_accumulated(db, a, period), 0)
    idx = _months_between(_period_of(a.start_date), period)
    return _straight_line(monthly_depreciation(a), remaining, idx, a.depr_months)


def depreciation_table(db: Session, period: str) -> dict:
    """Bảng tính khấu hao TSCĐ của kỳ (MISA: Tài sản cố định ▸ Tính khấu hao). Chưa ghi sổ thì tính lại mỗi lần gọi."""
    posted = {r.asset_id: r for r in db.execute(select(AssetDepreciation).where(AssetDepreciation.period == period)).scalars()}
    rows, total = [], 0.0
    # HÀNG RÀO SỔ THƯƠNG HIỆU (18/9/2026). Thẻ nhận diện nội bộ tự tạo (nguyên giá rỗng) KHÔNG vào
    # bảng tính khấu hao. Về số thì nó vô hại – nguyên giá rỗng nên không có gì để trích – nhưng
    # bảng tính khấu hao là thứ Kế toán in ra và ký, và một bảng ký tên có mấy chục dòng logo là
    # một bảng sai. Luật nằm ở services/tai_san_thuong_hieu, KHÔNG viết lại điều kiện ở đây.
    from app.services.tai_san_thuong_hieu import loc_so_ke_toan
    for a in db.execute(loc_so_ke_toan(select(FixedAsset)).order_by(FixedAsset.code)).scalars():
        p = posted.get(a.id)
        prior = asset_prior_accumulated(db, a, period)
        amount = (p.amount if p else asset_depreciation_amount(db, a, period)) or 0
        acc = round(prior + amount, 0)
        depreciable = max((a.cost or 0) - (a.salvage or 0), 0.0)
        monthly = monthly_depreciation(a)
        if not p and amount <= 0 and acc <= 0 and a.status != "dang_dung":
            continue                                       # thẻ chưa/không còn liên quan kỳ này
        rows.append({
            "asset_id": a.id, "code": a.code, "name": a.name, "kind": a.kind, "kind_name": ASSET_KINDS.get(a.kind, {}).get("ten", a.kind),
            "group": a.group, "department": a.department, "project_code": a.project_code,
            "start_date": a.start_date, "cost": a.cost, "salvage": a.salvage, "depr_months": a.depr_months,
            "monthly": monthly, "prior_accumulated": prior, "amount": amount, "accumulated": acc,
            "remaining": round((a.cost or 0) - acc, 0),
            "months_left": (int(round((depreciable - acc) / monthly)) if monthly > 0 else 0),
            "asset_account": a.asset_account, "depr_account": a.depr_account, "expense_account": a.expense_account,
            "status": a.status, "status_name": ASSET_STATUS.get(a.status, a.status),
            "posted": bool(p and p.entry_id), "entry_id": p.entry_id if p else None,
        })
        total += amount
    return {"period": period, "rows": rows, "total": round(total, 0),
            "posted": any(r["posted"] for r in rows),
            "locked": ACC.is_locked(db, period)}


def post_depreciation(db: Session, u: User, period: str) -> dict:
    """Ghi sổ bảng khấu hao của kỳ: một chứng từ Nợ TK chi phí / Có TK hao mòn, gộp dòng theo TK + công trình + bộ phận."""
    if ACC.is_locked(db, period):
        raise ValueError(f"Kỳ {period} đã khóa – không ghi sổ được")
    done = db.execute(select(AssetDepreciation).where(AssetDepreciation.period == period, AssetDepreciation.entry_id.isnot(None))).first()
    if done:
        raise ValueError(f"Kỳ {period} đã ghi sổ khấu hao – muốn tính lại phải đảo chứng từ cũ")
    tab = depreciation_table(db, period)
    rows = [r for r in tab["rows"] if (r["amount"] or 0) > 0]
    if not rows:
        raise ValueError(f"Kỳ {period} không có tài sản nào phải trích khấu hao")
    groups: dict[tuple, float] = {}
    for r in rows:
        k = (r["expense_account"], r["depr_account"], r["project_code"], r["department"])
        groups[k] = groups.get(k, 0.0) + (r["amount"] or 0)
    lines = []
    for (exp, depr, proj, dept), amt in sorted(groups.items()):
        amt = round(amt, 0)
        lines.append({"account": exp, "debit": amt, "credit": 0, "project_code": proj, "bo_phan": dept, "note": f"Khấu hao TSCĐ kỳ {period}"})
        lines.append({"account": depr, "debit": 0, "credit": amt, "project_code": proj, "bo_phan": dept, "note": f"Khấu hao TSCĐ kỳ {period}"})
    e = ACC.post_entry(db, u.username, u.role, period_last_day(period), f"Trích khấu hao TSCĐ kỳ {period}", lines,
                       source_type="khau_hao", source_ref=f"kh:{period}", nghiep_vu="khau_hao_tscd")
    for r in rows:
        db.add(AssetDepreciation(asset_id=r["asset_id"], period=period, amount=r["amount"],
                                 accumulated=r["accumulated"], remaining=r["remaining"], entry_id=e.id))
    R.audit(db, u.username, u.role, "ghi_so_khau_hao", f"kh:{period}", after={"so_the": len(rows), "so_tien": tab["total"]})
    db.commit()
    return {"period": period, "entry_id": e.id, "entry_code": e.code, "assets": len(rows), "total": tab["total"]}


# ---------- Phân bổ chi phí trả trước / CCDC ----------

# ĐÍCH PHÂN BỔ 242 — LẤY NGUYÊN DANH SÁCH CỦA MISA, không tự mở rộng.
# MISA ghi bút toán phân bổ là `Nợ 154, 622, 623, 627, 635, 641, 642, 241 / Có 242`.
# ĐO ĐƯỢC KHI VIẾT LUẬT NÀY: bản đầu em để `("62", "64", "241")` và dựng cảnh bằng `6323`
# (giá vốn dịch vụ cho thuê xe) — SAI, vì 632x KHÔNG nằm trong danh sách của MISA. Chi phí
# đội xe ở VTOS đi vào `627`, rồi bước 0 của kết sổ đẩy 627 → 154 → 632. Cho chọn thẳng 632x
# là đi tắt qua bước ấy, và chi phí đội xe sẽ bị tính hai lần.
TK_PHAN_BO_NHOM = ("154", "622", "623", "627", "635", "641", "642", "241")


def tk_chi_phi_nhan_phan_bo(db: Session) -> list[dict]:
    """Danh mục TK chi phí có thể nhận phân bổ 242 — ĐỌC THẲNG DANH MỤC, không gõ cứng.

    Hai điều kiện, và cả hai đều có lý do đo được:

      · CHỈ TÀI KHOẢN CHI TIẾT (không có con). Đo trên main 07/11/2026: `642` và `641` đều LÀ
        tài khoản cha. Cho chọn tài khoản cha là mời người dùng tạo ra đúng thứ Chủ tịch đã chốt
        07/11/2026 là phải chặn.
      · CHỈ CÁC NHÓM MISA LIỆT KÊ làm đích phân bổ — xem `TK_PHAN_BO_NHOM` ngay trên.

    Gõ cứng một danh sách ngắn trong mã thì danh mục đổi là danh sách lệch, mà không ai biết.
    """
    cac = {a.code: a for a in db.execute(select(Account)).scalars()}
    lam_cha = {a.parent for a in cac.values() if a.parent}
    return [{"ma": a.code, "ten": a.name}
            for a in sorted(cac.values(), key=lambda x: x.code)
            if a.code.startswith(TK_PHAN_BO_NHOM) and a.code not in lam_cha]


def monthly_allocation(p: PrepaidExpense) -> float:
    if p.months <= 0:
        return 0.0
    return round(max((p.amount or 0), 0.0) / p.months, 0)


def prepaid_prior_allocated(db: Session, p: PrepaidExpense, period: str) -> float:
    got = db.execute(select(func.coalesce(func.sum(PrepaidAllocation.amount), 0.0))
                     .where(PrepaidAllocation.prepaid_id == p.id, PrepaidAllocation.period < period)).scalar() or 0.0
    return round((p.opening_allocated or 0.0) + got, 0)


def prepaid_allocation_amount(db: Session, p: PrepaidExpense, period: str) -> float:
    if p.months <= 0 or (p.amount or 0) <= 0 or p.status in ("ngung_pb", "ghi_giam"):
        return 0.0
    if period < _period_of(p.start_date):
        return 0.0
    if p.opening_period and period <= p.opening_period:
        return 0.0
    remaining = round((p.amount or 0) - prepaid_prior_allocated(db, p, period), 0)
    idx = _months_between(_period_of(p.start_date), period)
    return _straight_line(monthly_allocation(p), remaining, idx, p.months)


def allocation_table(db: Session, period: str) -> dict:
    """Bảng phân bổ chi phí trả trước / CCDC của kỳ (MISA: Công cụ dụng cụ ▸ Phân bổ chi phí)."""
    posted = {r.prepaid_id: r for r in db.execute(select(PrepaidAllocation).where(PrepaidAllocation.period == period)).scalars()}
    rows, total = [], 0.0
    for p in db.execute(select(PrepaidExpense).order_by(PrepaidExpense.code)).scalars():
        rec = posted.get(p.id)
        prior = prepaid_prior_allocated(db, p, period)
        amount = (rec.amount if rec else prepaid_allocation_amount(db, p, period)) or 0
        alloc = round(prior + amount, 0)
        monthly = monthly_allocation(p)
        if not rec and amount <= 0 and p.status != "dang_pb":
            continue
        rows.append({
            "prepaid_id": p.id, "code": p.code, "name": p.name, "kind": p.kind, "kind_name": PREPAID_KINDS.get(p.kind, {}).get("ten", p.kind),
            "department": p.department, "project_code": p.project_code, "start_date": p.start_date,
            "amount_total": p.amount, "months": p.months, "monthly": monthly,
            "prior_allocated": prior, "amount": amount, "allocated": alloc, "remaining": round((p.amount or 0) - alloc, 0),
            "months_left": (int(round(((p.amount or 0) - alloc) / monthly)) if monthly > 0 else 0),
            "asset_account": p.asset_account, "expense_account": p.expense_account,
            "status": p.status, "status_name": PREPAID_STATUS.get(p.status, p.status),
            "posted": bool(rec and rec.entry_id), "entry_id": rec.entry_id if rec else None,
        })
        total += amount
    return {"period": period, "rows": rows, "total": round(total, 0),
            "posted": any(r["posted"] for r in rows), "locked": ACC.is_locked(db, period)}


def post_allocation(db: Session, u: User, period: str) -> dict:
    """Ghi sổ bảng phân bổ: Nợ TK chi phí / Có 242, gộp theo TK + công trình + bộ phận."""
    if ACC.is_locked(db, period):
        raise ValueError(f"Kỳ {period} đã khóa – không ghi sổ được")
    if db.execute(select(PrepaidAllocation).where(PrepaidAllocation.period == period, PrepaidAllocation.entry_id.isnot(None))).first():
        raise ValueError(f"Kỳ {period} đã ghi sổ phân bổ – muốn tính lại phải đảo chứng từ cũ")
    tab = allocation_table(db, period)
    rows = [r for r in tab["rows"] if (r["amount"] or 0) > 0]
    if not rows:
        raise ValueError(f"Kỳ {period} không có khoản nào phải phân bổ")
    groups: dict[tuple, float] = {}
    for r in rows:
        k = (r["expense_account"], r["asset_account"], r["project_code"], r["department"])
        groups[k] = groups.get(k, 0.0) + (r["amount"] or 0)
    lines = []
    for (exp, src, proj, dept), amt in sorted(groups.items()):
        amt = round(amt, 0)
        lines.append({"account": exp, "debit": amt, "credit": 0, "project_code": proj, "bo_phan": dept, "note": f"Phân bổ CP trả trước kỳ {period}"})
        lines.append({"account": src, "debit": 0, "credit": amt, "project_code": proj, "bo_phan": dept, "note": f"Phân bổ CP trả trước kỳ {period}"})
    e = ACC.post_entry(db, u.username, u.role, period_last_day(period), f"Phân bổ chi phí trả trước / CCDC kỳ {period}", lines,
                       source_type="phan_bo", source_ref=f"pb:{period}", nghiep_vu="phan_bo_tra_truoc")
    for r in rows:
        db.add(PrepaidAllocation(prepaid_id=r["prepaid_id"], period=period, amount=r["amount"],
                                 allocated=r["allocated"], remaining=r["remaining"], entry_id=e.id))
        if (r["remaining"] or 0) <= 0:
            p = db.get(PrepaidExpense, r["prepaid_id"])
            if p:
                p.status = "het"
    R.audit(db, u.username, u.role, "ghi_so_phan_bo", f"pb:{period}", after={"so_khoan": len(rows), "so_tien": tab["total"]})
    db.commit()
    return {"period": period, "entry_id": e.id, "entry_code": e.code, "items": len(rows), "total": tab["total"]}


# ---------- Xuất Excel (bố cục như bảng của MISA) ----------

def depreciation_xlsx(tab: dict) -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = "BANG TINH KHAU HAO"
    bold = Font(bold=True, name="Times New Roman")
    for h in ["CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS", "BẢNG TÍNH KHẤU HAO TÀI SẢN CỐ ĐỊNH",
              f"Kỳ {tab['period']} – Đơn vị tính: VND"]:
        ws.append([h])
    head = ["STT", "Mã TSCĐ", "Tên tài sản", "Loại", "Bộ phận", "Công trình", "Ngày bắt đầu KH", "Nguyên giá",
            "Số tháng KH", "Mức KH tháng", "HM lũy kế đầu kỳ", "KH trong kỳ", "HM lũy kế cuối kỳ", "Giá trị còn lại", "Số kỳ còn", "Trạng thái"]
    ws.append(head)
    for c in ws[ws.max_row]:
        c.font = bold
    for i, r in enumerate(tab["rows"], 1):
        ws.append([i, r["code"], r["name"], r["kind_name"], r["department"], r["project_code"],
                   r["start_date"], r["cost"], r["depr_months"], r["monthly"], r["prior_accumulated"],
                   r["amount"], r["accumulated"], r["remaining"], r["months_left"], r["status_name"]])
    ws.append(["", "", "TỔNG CỘNG", "", "", "", "", sum((r["cost"] or 0) for r in tab["rows"]), "", "", "",
               (tab["total"] or 0), "", sum((r["remaining"] or 0) for r in tab["rows"]), "", ""])
    for c in ws[ws.max_row]:
        c.font = bold
    for col, w in zip("ABCDEFGHIJKLMNOP", [5, 14, 38, 18, 12, 14, 14, 16, 10, 14, 18, 16, 18, 16, 10, 18]):
        ws.column_dimensions[col].width = w
    buf = BytesIO(); wb.save(buf); return buf.getvalue()


def allocation_xlsx(tab: dict) -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = "BANG PHAN BO CP TRA TRUOC"
    bold = Font(bold=True, name="Times New Roman")
    for h in ["CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS", "BẢNG PHÂN BỔ CHI PHÍ TRẢ TRƯỚC / CÔNG CỤ DỤNG CỤ",
              f"Kỳ {tab['period']} – Đơn vị tính: VND"]:
        ws.append([h])
    ws.append(["STT", "Mã", "Tên khoản mục", "Loại", "Bộ phận", "Công trình", "Ngày bắt đầu", "Giá trị phân bổ",
               "Số kỳ", "Mức PB tháng", "Đã PB đầu kỳ", "PB trong kỳ", "Lũy kế cuối kỳ", "Còn lại", "Số kỳ còn", "Trạng thái"])
    for c in ws[ws.max_row]:
        c.font = bold
    for i, r in enumerate(tab["rows"], 1):
        ws.append([i, r["code"], r["name"], r["kind_name"], r["department"], r["project_code"], r["start_date"],
                   r["amount_total"], r["months"], r["monthly"], r["prior_allocated"], r["amount"],
                   r["allocated"], r["remaining"], r["months_left"], r["status_name"]])
    ws.append(["", "", "TỔNG CỘNG", "", "", "", "", sum(r["amount_total"] for r in tab["rows"]), "", "", "",
               (tab["total"] or 0), "", sum((r["remaining"] or 0) for r in tab["rows"]), "", ""])
    for c in ws[ws.max_row]:
        c.font = bold
    for col, w in zip("ABCDEFGHIJKLMNOP", [5, 14, 38, 18, 12, 14, 14, 16, 8, 14, 16, 16, 18, 16, 10, 18]):
        ws.column_dimensions[col].width = w
    buf = BytesIO(); wb.save(buf); return buf.getvalue()


# ---------- Tạo / sửa thẻ ----------

def create_asset(db: Session, u: User, data: dict) -> FixedAsset:
    kind = data.get("kind") or "huu_hinh"
    default = ASSET_KINDS.get(kind, ASSET_KINDS["huu_hinh"])
    a = FixedAsset(
        code=(data.get("code") or _next_code(db, FixedAsset, "TS")).strip()[:30],
        name=(data.get("name") or "").strip()[:200], kind=kind, group=(data.get("group") or "")[:60],
        asset_account=data.get("asset_account") or default["tk_nguyen_gia"],
        depr_account=data.get("depr_account") or default["tk_hao_mon"],
        expense_account=data.get("expense_account") or "6424",
        partner_code=(data.get("partner_code") or "")[:60], project_code=(data.get("project_code") or "")[:40],
        department=(data.get("department") or "")[:20],
        purchase_date=data.get("purchase_date"), start_date=data["start_date"],
        cost=float(data.get("cost") or 0), depr_months=int(data.get("depr_months") or 0),
        salvage=float(data.get("salvage") or 0), opening_accumulated=float(data.get("opening_accumulated") or 0),
        opening_period=(data.get("opening_period") or "")[:7], quantity=int(data.get("quantity") or 1),
        note=(data.get("note") or "")[:300], source=data.get("source") or "vtos", created_by=u.username)
    if not a.name:
        raise ValueError("Thiếu tên tài sản")
    if (a.cost or 0) <= 0:
        raise ValueError("Nguyên giá phải lớn hơn 0")
    if db.execute(select(FixedAsset).where(FixedAsset.code == a.code)).scalar_one_or_none():
        raise ValueError(f"Mã tài sản {a.code} đã tồn tại")
    for code in (a.asset_account, a.depr_account, a.expense_account):
        if not db.get(Account, code):
            raise ValueError(f"Tài khoản {code} không có trong danh mục")
    db.add(a); db.flush()
    R.audit(db, u.username, u.role, "them_tscd", f"tscd:{a.code}", after={"ten": a.name, "nguyen_gia": a.cost, "so_thang": a.depr_months})
    db.commit()
    return a


def dispose_asset(db: Session, u: User, a: FixedAsset, on: date, reason: str) -> FixedAsset:
    """Ghi giảm / thanh lý TSCĐ: thôi trích từ tháng thanh lý. Bút toán ghi giảm do Kế toán lập riêng."""
    if a.status == "thanh_ly":
        raise ValueError("Tài sản đã thanh lý")
    a.status, a.disposed_date = "thanh_ly", on
    a.note = (a.note + f" | Thanh lý {on:%d/%m/%Y}: {reason}")[:300]
    R.audit(db, u.username, u.role, "thanh_ly_tscd", f"tscd:{a.code}", after={"ngay": str(on), "ly_do": reason})
    db.commit()
    return a


def create_prepaid(db: Session, u: User, data: dict) -> PrepaidExpense:
    p = PrepaidExpense(
        code=(data.get("code") or _next_code(db, PrepaidExpense, "CC")).strip()[:30],
        name=(data.get("name") or "").strip()[:200], kind=data.get("kind") or "ccdc",
        asset_account=data.get("asset_account") or "242",
        expense_account=(data.get("expense_account") or "").strip(),
        partner_code=(data.get("partner_code") or "")[:60], project_code=(data.get("project_code") or "")[:40],
        department=(data.get("department") or "")[:20], start_date=data["start_date"],
        amount=float(data.get("amount") or 0), months=int(data.get("months") or 1),
        opening_allocated=float(data.get("opening_allocated") or 0), opening_period=(data.get("opening_period") or "")[:7],
        quantity=int(data.get("quantity") or 1), note=(data.get("note") or "")[:300],
        source=data.get("source") or "vtos", created_by=u.username)
    if not p.name:
        raise ValueError("Thiếu tên khoản mục")
    if (p.amount or 0) <= 0:
        raise ValueError("Giá trị phân bổ phải lớn hơn 0")
    if p.months <= 0:
        raise ValueError("Số kỳ phân bổ phải lớn hơn 0")
    # ĐỢT CPTT-1 07/11/2026 — TK CHI PHÍ LÀ Ô BẮT BUỘC, MẶC ĐỊNH `6423` ĐÃ BỎ.
    #
    # Trước đợt này ô ấy mặc định `"6423"` (Chi phí đồ dùng văn phòng) và màn hình KHÔNG có chỗ
    # chọn, nên mọi khoản nhập qua màn hình đều phân bổ vào 6423: bảo hiểm xe lẽ ra vào 6323,
    # thuê văn phòng lẽ ra vào 6427. Sổ vẫn cân, báo cáo vẫn ra số, chỉ cơ cấu chi phí là sai —
    # và người nhập không có cách nào biết. Để mặc định là để máy trả lời hộ một câu chưa ai hỏi.
    #
    # VÀ CHỈ NHẬN TÀI KHOẢN CHI TIẾT: `642` và `641` đều LÀ tài khoản cha trên danh mục. Nhận
    # chúng ở đây là tự tay dựng thêm chỗ phải nắn lại ở đợt chặn tài khoản cha (Chủ tịch chốt
    # 07/11/2026).
    _tk = (p.expense_account or "").strip()
    if not _tk:
        raise ValueError("Chưa chọn TK chi phí nhận phân bổ — mỗi khoản phân bổ vào một tài "
                         "khoản chi phí khác nhau, máy không đoán thay được")
    _cac = {a.code: a for a in db.execute(select(Account)).scalars()}
    if _tk not in _cac:
        raise ValueError(f"TK chi phí {_tk} không có trong danh mục tài khoản")
    if _tk in {a.parent for a in _cac.values() if a.parent}:
        raise ValueError(f"TK chi phí {_tk} là tài khoản tổng hợp (có tài khoản con) — chọn tài "
                         "khoản chi tiết nhất")
    if db.execute(select(PrepaidExpense).where(PrepaidExpense.code == p.code)).scalar_one_or_none():
        raise ValueError(f"Mã {p.code} đã tồn tại")
    db.add(p); db.flush()
    R.audit(db, u.username, u.role, "them_ccdc", f"ccdc:{p.code}", after={"ten": p.name, "gia_tri": p.amount, "so_ky": p.months})
    db.commit()
    return p
