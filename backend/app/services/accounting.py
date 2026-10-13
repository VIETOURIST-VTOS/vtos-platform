"""Robot R2 – Kế toán tự động theo TT99/2025.

Nguyên tắc: mọi bút toán sinh từ nghiệp vụ đã được Kế toán xác nhận (phiếu thu, hóa đơn phát hành, quyết toán tour);
chứng từ đã ghi sổ là bất biến – sai thì lập chứng từ đảo. Kỳ đã khóa không ghi sổ.
"""
import json
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User
from app.models.payments import Receipt
from app.models.accounting import Account, JournalEntry, JournalLine, Invoice, PeriodLock
from app.services import rules as R
from app.services import chung_tu_loai as CTL   # Đợt E3 – loại chứng từ, loại nghiệp vụ, khoá sự kiện

# Hệ thống tài khoản rút gọn cho công ty lữ hành (TT 99/2025/TT-BTC, Phụ lục I) – bổ sung dần.
#
# DÒNG CHÚ THÍCH TRÊN TỪNG KHAI SAI, và sửa nó là một phần của vòng KY-2 (08/10/2026). Nó nói danh
# mục này theo TT 99, trong khi ba tên vẫn là chữ của TT 200: 112 "Tiền gửi ngân hàng", 242 "Chi phí
# trả trước", 244 "Cầm cố, thế chấp, ký quỹ, ký cược". Tệp `data/misa_tai_khoan.json` thì khai thật
# hơn — nó ghi rõ "+ TT200". Một chú thích nói sai về chính đoạn mã bên dưới là thứ người đọc sau tin
# mà không kiểm, nên nay cả hai nơi đều mang tên của Phụ lục I TT 99 (hiệu lực 01/01/2026, áp dụng
# cho năm tài chính bắt đầu từ 01/01/2026).
#
# ĐỔI TÊN LÀ ĐỔI NHÃN, KHÔNG ĐỔI SỐ: `seed_accounts` ghi đè `a.name` mỗi lần chạy nên bàn đang chạy
# đổi tên ngay lúc khởi động, còn số dư và bút toán không đụng tới. Khác hẳn với mức giảm trừ ở vòng
# KY-1 — cái đó là TIỀN nên phải chờ hai chữ ký.
CHART = [
    ("111", "Tiền mặt", "TS", ""), ("112", "Tiền gửi không kỳ hạn", "TS", ""),
    ("131", "Phải thu của khách hàng", "TS", ""), ("133", "Thuế GTGT được khấu trừ", "TS", ""),
    ("138", "Phải thu khác", "TS", ""), ("141", "Tạm ứng", "TS", ""),
    ("154", "Chi phí SXKD dở dang (chi phí tour)", "TS", ""), ("211", "Tài sản cố định hữu hình", "TS", ""),
    ("214", "Hao mòn TSCĐ", "TS", ""), ("242", "Chi phí chờ phân bổ", "TS", ""),
    ("331", "Phải trả người bán (NCC dịch vụ)", "NV", ""), ("333", "Thuế và các khoản phải nộp", "NV", ""),
    ("3331", "Thuế GTGT phải nộp", "NV", "333"), ("3334", "Thuế TNDN", "NV", "333"), ("3335", "Thuế TNCN", "NV", "333"),
    ("334", "Phải trả người lao động", "NV", ""), ("335", "Chi phí phải trả (NCC chưa có hóa đơn)", "NV", ""),
    ("338", "Phải trả, phải nộp khác", "NV", ""), ("3387", "Doanh thu chưa thực hiện / đặt cọc", "NV", "338"),
    ("341", "Vay và nợ thuê tài chính", "NV", ""), ("411", "Vốn đầu tư của chủ sở hữu", "NV", ""),
    ("421", "Lợi nhuận sau thuế chưa phân phối", "NV", ""),
    ("511", "Doanh thu bán hàng và cung cấp dịch vụ", "DT", ""), ("515", "Doanh thu hoạt động tài chính", "DT", ""),
    # 627 THÊM 08/10/2026 (Chủ tịch quyết): chi phí vận hành đội xe – sửa chữa xe vào thẳng 627 của
    # THÁNG PHÁT SINH, không treo 242 chờ phân bổ. Cuối kỳ kết chuyển 627 -> 154 (bước 0 của
    # `services/ket_so.py`). Trước bản này danh mục KHÔNG có 627 nên `misa.CATEGORY_ACCOUNT` để trống
    # ô `sua_chua_xe` và tiền chi được mà không lên bảng kê.
    ("627", "Chi phí sản xuất chung", "CP", ""),
    ("632", "Giá vốn hàng bán (giá vốn tour)", "CP", ""), ("635", "Chi phí tài chính", "CP", ""),
    ("641", "Chi phí bán hàng", "CP", ""), ("642", "Chi phí quản lý doanh nghiệp", "CP", ""),
    ("128", "Đầu tư nắm giữ đến ngày đáo hạn / cho vay", "TS", ""), ("222", "Đầu tư vào công ty liên kết, liên doanh", "TS", ""),
    ("244", "Ký quỹ, ký cược", "TS", ""), ("413", "Chênh lệch tỷ giá hối đoái", "NV", ""),
    ("711", "Thu nhập khác", "DT", ""), ("811", "Chi phí khác", "CP", ""),
    ("821", "Chi phí thuế TNDN", "CP", ""), ("911", "Xác định kết quả kinh doanh", "XD", ""),
]


MISA_CHART = Path(__file__).resolve().parent.parent / "data" / "misa_tai_khoan.json"
# Tài khoản bắt buộc có đối tượng / công trình (định hướng 06/9/2026 – 4 chiều đối tượng)
NEED_PARTNER = ("131", "331", "1388", "141", "3388", "341", "1281", "1283", "136", "222", "221", "244")
NEED_PROJECT = ("154", "5113", "632")


def seed_accounts(db: Session):
    """Nạp danh mục tài khoản theo cấu trúc MISA (124 TK, phân cấp, ánh xạ TT99) + bổ sung TK rút gọn cũ. Chạy được nhiều lần."""
    have = {a.code: a for a in db.execute(select(Account)).scalars()}
    rows = json.loads(MISA_CHART.read_text(encoding="utf-8"))["tai_khoan"]
    parents = {r["parent"] for r in rows if r["parent"]}
    for r in rows:
        a = have.get(r["code"])
        if a is None:
            a = Account(code=r["code"], name=r["name"], kind=r["kind"], parent=r["parent"]); db.add(a); have[r["code"]] = a
        a.name, a.kind, a.parent, a.level = r["name"], r["kind"], r["parent"], r["level"]
        a.bs_debit, a.bs_credit, a.pl_code = r.get("bs_debit") or "", r.get("bs_credit") or "", r.get("pl_code") or ""
        a.is_detail, a.misa = r["code"] not in parents, True
    for c, n, k, p in CHART:
        if c not in have:
            db.add(Account(code=c, name=n, kind=k, parent=p, level=len(c) - 2, is_detail=True))
    db.commit()


def account_rule_check(db: Session, account: str, l: dict, source_type: str) -> None:
    """Kiểm tra chiều đối tượng: công nợ phải có đối tượng; chi phí tour / doanh thu / giá vốn phải có công trình (tour)."""
    if source_type in ("misa", "so_du_dau_ky", "kiem_toan", "dao", "luong", "ket_chuyen"):
        return
    if account.startswith(NEED_PARTNER) and not (l.get("partner_code") or l.get("partner") or l.get("booking_id")):
        raise ValueError(f"Tài khoản {account} phải ghi mã đối tượng (khách / NCC / nhân viên / ngân hàng)")
    if account.startswith(NEED_PROJECT) and not (l.get("project_code") or l.get("tour_id")):
        raise ValueError(f"Tài khoản {account} phải ghi mã công trình (mã tour)")


def period_of(d: date) -> str:
    return f"{d:%Y-%m}"


def is_locked(db: Session, period: str) -> bool:
    return db.get(PeriodLock, period) is not None


def _company_of_tour(db: Session, tour_id):
    """Chứng từ của một tour thuộc pháp nhân của tour đó. Tour chưa xác định pháp nhân thì chứng từ
    cũng để trống – không đoán, không mặc định về công ty mẹ."""
    if not tour_id: return None
    from app.models.core import Tour
    t = db.get(Tour, tour_id)
    return t.company_id if t else None


def _next_code(db: Session, prefix: str, d: date) -> str:
    # Số lấy theo SỐ LỚN NHẤT đã cấp cho đúng tiền tố này, không phải số dòng cả bảng —
    # xem `services/ma_tu_sinh.py` cho ba chỗ hỏng của lối đếm cũ.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, JournalEntry, f"{prefix}{d:%y%m}-", 4)


def cho_ve_huu(db: Session, e, hau_to: str = ":old") -> None:
    """Cho một chứng từ VỀ HƯU: đổi mã nguồn, và THU HỒI luôn khoá sự kiện của nó.

    Đợt DỌN-1, 13/10/2026 — vá một chỗ hỏng của Đợt E3.

    `khoa_su_kien` là một cột GHI MỘT LẦN lúc lập chứng từ, không phải một phép tính đọc lại từ
    `source_ref`. Nên khi một nơi đổi tên mã nguồn để cho chứng từ cũ về hưu — `misa.py` làm đúng
    thế ở hai chỗ, khi nạp lại dữ liệu và khi nạp lại mốc kiểm toán — thì cột khoá KHÔNG đổi
    theo. Chứng từ đã về hưu vẫn giữ chỗ khoá, và lần ghi mới đâm vào chính nó: `replace=true`
    của cửa chốt sổ kiểm toán trả về 422 kể từ Đợt E3 (12/10/2026).

    Khoá của một chứng từ đã về hưu phải là RỖNG chứ không phải một giá trị khác: NULL không va
    nhau trong chỉ mục duy nhất, còn một chuỗi `...:old` thì vẫn chiếm chỗ và sẽ va với lần về
    hưu thứ hai của cùng sự kiện ấy.

    Gom BA việc vào MỘT hàm có tên, vì rời ra thì nơi thứ ba sẽ quên một vế — y như hai nơi hiện
    có đã quên vế thứ hai. Việc thứ ba là `flush`: phiên làm việc của hệ thống đặt
    `autoflush=False`, nên một thay đổi chưa đẩy xuống thì câu truy vấn ngay sau đó KHÔNG THẤY.
    Thiếu đúng dòng ấy, `import_opening_balance` vẫn trả 422 dù khoá đã được thu hồi trong bộ nhớ
    — đo được 13/10/2026, và `import_audited_checkpoint` thoát nạn chỉ vì tình cờ có sẵn một
    `db.flush()` ở dòng sau. Một hàm đúng nhờ tình cờ là một hàm sẽ sai ở nơi gọi thứ ba.
    """
    e.source_ref = f"{e.source_ref}{hau_to}"
    e.khoa_su_kien = None
    db.flush()


def post_entry(db: Session, actor: str, role: str, entry_date: date, description: str, lines: list[dict],
               source_type: str = "thu_cong", source_ref: str = "", tour_id: int | None = None, post: bool = True,
               nghiep_vu: str = "but_toan_tay", ngay_chung_tu: date | None = None) -> JournalEntry:
    """lines: [{account, debit, credit, partner?, booking_id?, tour_id?, note?}]. Kiểm tra cân đối và kỳ khóa.

    ĐỢT E3 12/10/2026 – hai tham số mới:

    · `nghiep_vu` – VIỆC GÌ đã xảy ra, lấy trong `chung_tu_loai.NGHIEP_VU`. Loại chứng từ suy ra
      từ đó, nên người gọi khai MỘT thứ chứ không khai hai thứ có thể lệch nhau. Mặc định
      `but_toan_tay` CHỈ đúng cho cửa lập tay; `test_e3_1` đọc cây cú pháp của mọi chỗ gọi và đỏ
      nếu một chỗ nào đó không khai rõ.

    · `ngay_chung_tu` – ngày trên tờ chứng từ. Bỏ trống thì bằng `entry_date`, đúng như mọi chứng
      từ đang có trước đợt này.

    CHẶN GHI SỔ HAI LẦN: khoá sự kiện ghép từ nguồn, mã nguồn và nghiệp vụ. Trùng thì NÉM LỖI và
    nói ra mã chứng từ đã ghi – một trong bốn luật cứng Chủ tịch chốt (nguồn trùng thật luôn
    chặn), nên nó KHÔNG đi qua bảng mức độ chặn."""
    period = period_of(entry_date)
    if is_locked(db, period):
        raise ValueError(f"Kỳ {period} đã khóa – không ghi sổ được")
    td = round(sum(float(l.get("debit") or 0) for l in lines), 0)
    tc = round(sum(float(l.get("credit") or 0) for l in lines), 0)
    if td <= 0 or abs(td - tc) >= 1:
        raise ValueError(f"Bút toán không cân: Nợ {td:,.0f} ≠ Có {tc:,.0f}")
    tcode = ""
    if tour_id:
        t = db.get(Tour, tour_id); tcode = t.code if t else ""
    for l in lines:
        if not l.get("project_code") and (l.get("tour_id") or tour_id):
            tt = db.get(Tour, l["tour_id"]) if l.get("tour_id") and l.get("tour_id") != tour_id else None
            l["project_code"] = tt.code if tt else tcode
        acc = db.get(Account, str(l["account"]))
        if not acc:
            raise ValueError(f"Tài khoản {l['account']} không có trong danh mục")
        account_rule_check(db, acc.code, l, source_type)
    khoa = CTL.khoa(source_type, source_ref, nghiep_vu)
    if khoa is not None:
        cu = db.execute(select(JournalEntry).where(JournalEntry.khoa_su_kien == khoa)).scalars().first()
        if cu is not None:
            raise ValueError(
                f"Sự kiện này đã ghi sổ ở chứng từ {cu.code} ngày {cu.entry_date:%d/%m/%Y} – "
                f"{CTL.ten_nghiep_vu(nghiep_vu)}, nguồn {source_type}, mã nguồn {source_ref}. "
                f"Ghi lần nữa là nhân đôi số tiền mà sổ vẫn cân, nên không ai thấy. "
                f"Muốn sửa thì lập bút toán đảo cho {cu.code}, đừng ghi thêm một tờ nữa.")
    e = JournalEntry(code=_next_code(db, "CT", entry_date), entry_date=entry_date, period=period, description=description[:300],
                     ngay_chung_tu=ngay_chung_tu or entry_date,
                     loai_nghiep_vu=CTL.nghiep_vu_hop_le(nghiep_vu), loai_chung_tu=CTL.chung_tu_cua(nghiep_vu),
                     khoa_su_kien=khoa,
                     source_type=source_type, source_ref=source_ref, tour_id=tour_id, created_by=actor,
                     status="da_ghi_so" if post else "nhap", posted_by=actor if post else "", posted_at=datetime.now() if post else None,
                     company_id=_company_of_tour(db, tour_id))
    for l in lines:
        e.lines.append(JournalLine(account_code=str(l["account"]), debit=float(l.get("debit") or 0), credit=float(l.get("credit") or 0),
                                   partner=(l.get("partner") or "")[:160], partner_code=(l.get("partner_code") or "")[:60], project_code=(l.get("project_code") or "")[:40],
                                   item_code=(l.get("item_code") or "")[:40], doc_no=(l.get("doc_no") or "")[:40],
                                   booking_id=l.get("booking_id"), tour_id=l.get("tour_id") or tour_id, note=(l.get("note") or "")[:200]))
    db.add(e); db.flush()
    R.audit(db, actor, role, "ghi_so" if post else "lap_chung_tu", f"entry:{e.code}",
            after={"nguon": source_type, "ref": source_ref, "so_tien": td, "dong": [(l["account"], l.get("debit") or 0, l.get("credit") or 0) for l in lines]})
    return e


def post_draft(db: Session, u: User, e: JournalEntry) -> JournalEntry:
    if e.status != "nhap":
        raise ValueError("Chứng từ không ở trạng thái nháp")
    if is_locked(db, e.period):
        raise ValueError(f"Kỳ {e.period} đã khóa")
    e.status, e.posted_by, e.posted_at = "da_ghi_so", u.username, datetime.now()
    R.audit(db, u.username, u.role, "ghi_so", f"entry:{e.code}", after={"so_tien": sum((l.debit or 0) for l in e.lines)})
    db.commit()
    return e


def reverse_entry(db: Session, u: User, e: JournalEntry, reason: str) -> JournalEntry:
    """Bút toán đảo: ghi ngược Nợ/Có cùng số tiền vào ngày hôm nay (chứng từ gốc giữ nguyên)."""
    if e.status != "da_ghi_so":
        raise ValueError("Chỉ đảo chứng từ đã ghi sổ")
    if e.reversed_by_id:
        raise ValueError("Chứng từ đã được đảo")
    lines = [{"account": l.account_code, "debit": l.credit, "credit": l.debit, "partner": l.partner, "partner_code": l.partner_code, "project_code": l.project_code,
              "item_code": l.item_code, "doc_no": l.doc_no, "booking_id": l.booking_id, "tour_id": l.tour_id, "note": f"Đảo {e.code}"} for l in e.lines]
    r = post_entry(db, u.username, u.role, date.today(), f"Đảo {e.code}: {reason}", lines, "dao", f"entry:{e.code}", e.tour_id, nghiep_vu="but_toan_dao")
    e.reversed_by_id = r.id
    db.commit()
    return r


# ---------- Bút toán tự động từ nghiệp vụ ----------
def on_receipt_confirmed(db: Session, r: Receipt, actor: str, role: str) -> JournalEntry | None:
    """Phiếu thu được Kế toán xác nhận → Nợ 111/112 – Có 131 (khách, booking)."""
    if db.execute(select(JournalEntry).where(JournalEntry.source_ref == f"receipt:{r.code}")).scalars().first():
        return None
    b = db.get(Booking, r.booking_id)
    cash = "111" if r.method == "tien_mat" else "112"
    d = (r.confirmed_at or r.created_at or datetime.now()).date()
    try:
        pc = b.tour.code if b and b.tour else ""
        return post_entry(db, "robot", "robot", d, f"Thu tiền {b.code if b else ''} – {r.payer}",
                          [{"account": cash, "debit": r.amount, "partner": r.payer, "booking_id": r.booking_id, "project_code": pc},
                           {"account": "131", "credit": r.amount, "partner": b.customer_name if b else r.payer, "partner_code": (b.customer_phone if b and getattr(b, "customer_phone", "") else ""), "booking_id": r.booking_id, "project_code": pc}],
                          "thu_tien", f"receipt:{r.code}", b.tour_id if b else None, nghiep_vu="thu_tien_khach")
    except ValueError as ex:  # kỳ khóa → cảnh báo, không chặn nghiệp vụ thu tiền
        R.audit(db, actor, role, "ghi_so_that_bai", f"receipt:{r.code}", after={"ly_do": str(ex)})
        return None


def on_invoice_issued(db: Session, inv: Invoice) -> JournalEntry:
    """Phát hành hóa đơn → Nợ 131 – Có 511 (doanh thu chưa thuế), Có 3331 (thuế GTGT)."""
    lines = [{"account": "131", "debit": inv.total, "partner": inv.customer_name, "booking_id": inv.booking_id},
             {"account": "511", "credit": inv.pre_tax, "partner": inv.customer_name, "booking_id": inv.booking_id}]
    if (inv.vat or 0) > 0:
        lines.append({"account": "3331", "credit": inv.vat, "partner": inv.customer_name})
    return post_entry(db, "robot", "robot", inv.issue_date, f"Hóa đơn {inv.series}-{inv.number:07d} – {inv.customer_name}", lines,
                      "hoa_don", f"invoice:{inv.series}-{inv.number}", inv.tour_id, nghiep_vu="phat_hanh_hoa_don")


def on_settlement_confirmed(db: Session, t: Tour, actor: str, role: str) -> list[JournalEntry]:
    """Kế toán xác nhận quyết toán tour:
       - phần chi phí quyết toán chưa ghi qua đề nghị chi (NCC chưa có hóa đơn) → Nợ 154 – Có 335 (trích trước);
       - kết chuyển giá vốn: Nợ 632 – Có 154 theo toàn bộ chi phí quyết toán.
       Mã KM là dòng giá vốn quản trị nội bộ, không ghi sổ."""
    if db.execute(select(JournalEntry).where(JournalEntry.source_ref == f"tour:{t.code}", JournalEntry.source_type == "quyet_toan")).scalars().first():
        return []
    from app.services.ops import posted_tour_cost
    d = (t.kt_confirmed_at or datetime.now()).date()
    out = []
    if (t.actual_cost or 0) > 0:
        try:
            from app.models.ops import PaymentRequest
            adv = sum((r.amount or 0) for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.category == "tam_ung", PaymentRequest.status == "da_chi")).scalars())
            if adv > 0:   # hoàn ứng: tạm ứng đã chi trở thành chi phí tour
                out.append(post_entry(db, "robot", "robot", d, f"Hoàn ứng tour {t.code} theo quyết toán",
                                      [{"account": "154", "debit": adv, "tour_id": t.id}, {"account": "141", "credit": adv, "partner": "Tạm ứng tour", "tour_id": t.id}], "quyet_toan", f"tour:{t.code}", t.id, nghiep_vu="quyet_toan_hoan_ung"))
            diff = (t.actual_cost or 0) - posted_tour_cost(db, t.id)
            if diff > 0:
                out.append(post_entry(db, "robot", "robot", d, f"Chi phí tour {t.code} chưa có hóa đơn NCC theo quyết toán (trích trước)",
                                      [{"account": "154", "debit": diff, "tour_id": t.id}, {"account": "335", "credit": diff, "partner": "NCC dịch vụ tour", "tour_id": t.id}],
                                      "quyet_toan", f"tour:{t.code}", t.id, nghiep_vu="quyet_toan_trich_truoc"))
            elif diff < 0:
                R.audit(db, actor, role, "canh_bao_quyet_toan", f"tour:{t.code}", after={"ly_do": f"Chi phí quyết toán {(t.actual_cost or 0):,.0f} nhỏ hơn đề nghị chi đã duyệt {(t.actual_cost or 0) - diff:,.0f} – Kế toán rà soát"})
            out.append(post_entry(db, "robot", "robot", d, f"Kết chuyển giá vốn tour {t.code}",
                                  [{"account": "632", "debit": t.actual_cost, "tour_id": t.id}, {"account": "154", "credit": t.actual_cost, "tour_id": t.id}],
                                  "quyet_toan", f"tour:{t.code}", t.id, nghiep_vu="quyet_toan_gia_von"))
        except ValueError as ex:
            R.audit(db, actor, role, "ghi_so_that_bai", f"tour:{t.code}", after={"ly_do": str(ex)})
    return out


# ---------- Hóa đơn điện tử ----------
class LocalInvoiceProvider:
    """Adapter mặc định: cấp số nội bộ. Khi ký hợp đồng HĐĐT (Viettel/VNPT/MISA meInvoice…) thay bằng adapter gọi API nhà cung cấp."""
    name = "noi_bo"

    def issue(self, db: Session, inv: Invoice) -> tuple[int, str]:
        last = db.execute(select(func.max(Invoice.number)).where(Invoice.series == inv.series)).scalar() or 0
        n = last + 1
        return n, f"LOCAL-{inv.series}-{n:07d}"


PROVIDER = LocalInvoiceProvider()


def create_invoice(db: Session, u: User, b: Booking, vat_rate: float | None, tax_code: str, address: str, description: str) -> Invoice:
    if db.execute(select(Invoice).where(Invoice.booking_id == b.id, Invoice.status != "huy")).scalars().first():
        raise ValueError(f"Booking {b.code} đã có hóa đơn")
    rate = R.get_param(db, "thue_gtgt") if vat_rate is None else float(vat_rate)
    total = (b.amount or 0) - (b.discount or 0)                      # giá bán đã gồm thuế
    pre = round(total / (1 + rate)) if rate > 0 else total
    inv = Invoice(booking_id=b.id, tour_id=b.tour_id, customer_name=b.customer_name, customer_tax_code=tax_code, customer_address=address,
                  description=description or f"Dịch vụ du lịch – {b.tour.name if b.tour else ''} ({b.pax} khách)",
                  pre_tax=pre, vat_rate=rate, vat=total - pre, total=total, created_by=u.username)
    db.add(inv); db.flush()
    R.audit(db, u.username, u.role, "lap_hoa_don_nhap", f"invoice_draft:{inv.id}", after={"booking": b.code, "tong": total, "thue": rate})
    db.commit(); db.refresh(inv)
    return inv


def issue_invoice(db: Session, u: User, inv: Invoice) -> Invoice:
    if inv.status != "nhap":
        raise ValueError("Hóa đơn không ở trạng thái nháp")
    if is_locked(db, period_of(date.today())):
        raise ValueError("Kỳ hiện tại đã khóa")
    inv.number, inv.provider_ref = PROVIDER.issue(db, inv)
    inv.provider, inv.issue_date, inv.status = PROVIDER.name, date.today(), "da_phat_hanh"
    inv.issued_by, inv.issued_at = u.username, datetime.now()
    db.flush()
    e = on_invoice_issued(db, inv)
    inv.entry_id = e.id
    R.audit(db, u.username, u.role, "phat_hanh_hoa_don", f"invoice:{inv.series}-{inv.number}", after={"tong": (inv.total or 0), "ma_tra_cuu": inv.provider_ref, "chung_tu": e.code})
    db.commit(); db.refresh(inv)
    return inv


def cancel_invoice(db: Session, u: User, inv: Invoice, reason: str) -> Invoice:
    if inv.status == "huy":
        raise ValueError("Hóa đơn đã hủy")
    if inv.status == "da_phat_hanh" and inv.entry_id:
        e = db.get(JournalEntry, inv.entry_id)
        if e and not e.reversed_by_id:
            reverse_entry(db, u, e, f"Hủy hóa đơn {inv.series}-{inv.number}: {reason}")
    inv.status = "huy"
    R.audit(db, u.username, u.role, "huy_hoa_don", f"invoice:{inv.series}-{inv.number or inv.id}", after={"ly_do": reason})
    db.commit()
    return inv


# ---------- Sổ sách & khóa kỳ ----------
def ledger(db: Session, account: str, period: str | None) -> dict:
    """Sổ cái tài khoản (S03b): số dư đầu kỳ, phát sinh, số dư cuối."""
    acc = db.get(Account, account)
    if not acc:
        raise ValueError("Không có tài khoản")
    q = select(JournalLine, JournalEntry).join(JournalEntry).where(JournalLine.account_code == account, JournalEntry.status == "da_ghi_so").order_by(JournalEntry.entry_date, JournalEntry.id)
    rows = db.execute(q).all()
    debit_side = acc.kind in ("TS", "CP")
    opening = sum(((l.debit or 0) - (l.credit or 0)) for l, e in rows if period and e.period < period)
    bal = opening
    out = []
    for l, e in rows:
        if period and e.period != period:
            continue
        bal += (l.debit or 0) - (l.credit or 0)
        out.append({"date": e.entry_date, "code": e.code, "description": e.description, "partner": l.partner, "debit": l.debit, "credit": l.credit,
                    "balance": bal if debit_side else -bal, "entry_id": e.id})
    return {"account": account, "name": acc.name, "kind": acc.kind, "opening": opening if debit_side else -opening,
            "total_debit": sum((r["debit"] or 0) for r in out), "total_credit": sum((r["credit"] or 0) for r in out), "closing": bal if debit_side else -bal, "rows": out}


def trial_balance(db: Session, period: str) -> list[dict]:
    """Bảng cân đối số phát sinh (S06) theo kỳ."""
    res = {}
    for acc in db.execute(select(Account).order_by(Account.code)).scalars():
        res[acc.code] = {"account": acc.code, "name": acc.name, "kind": acc.kind, "open_debit": 0.0, "open_credit": 0.0, "debit": 0.0, "credit": 0.0}
    for l, e in db.execute(select(JournalLine, JournalEntry).join(JournalEntry).where(JournalEntry.status == "da_ghi_so")).all():
        r = res.get(l.account_code)
        if not r: continue
        if e.period < period:
            r["open_debit"] += (l.debit or 0); r["open_credit"] += (l.credit or 0)
        elif e.period == period:
            r["debit"] += (l.debit or 0); r["credit"] += (l.credit or 0)
    out = []
    for r in res.values():
        net_open = r["open_debit"] - r["open_credit"]
        r["open_debit"], r["open_credit"] = (net_open, 0.0) if net_open >= 0 else (0.0, -net_open)
        net_close = net_open + (r["debit"] or 0) - (r["credit"] or 0)
        r["close_debit"], r["close_credit"] = (net_close, 0.0) if net_close >= 0 else (0.0, -net_close)
        if any(abs(r[k]) > 0 for k in ("open_debit", "open_credit", "debit", "credit")):
            out.append(r)
    return out


def lock_period(db: Session, u: User, period: str, note: str) -> PeriodLock:
    if is_locked(db, period):
        raise ValueError(f"Kỳ {period} đã khóa")
    drafts = db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.period == period, JournalEntry.status == "nhap")).scalar()
    if drafts:
        raise ValueError(f"Còn {drafts} chứng từ nháp trong kỳ {period} – ghi sổ hoặc hủy trước khi khóa")
    pl = PeriodLock(period=period, locked_by=u.username, note=note)
    db.add(pl)
    R.audit(db, u.username, u.role, "khoa_ky_ke_toan", f"period:{period}", after={"ghi_chu": note})
    db.commit()
    return pl
