"""TR-1d · Link thanh toán tour đoàn riêng (Chủ tịch duyệt bản xem thử 02/11/2026). Xem models/thanh_toan_doan.py.

ĐƯỜNG ĐI
  1. Sale Admin phòng Đoàn bấm «Tạo link thanh toán» trên một ĐỢT của lịch thanh toán hợp đồng khách.
     Máy kiểm: công tắc thanh toán chung đang bật · hợp đồng còn hiệu lực, đã nối booking · báo giá của hợp đồng
     đã ở «khách chốt» · đợt đã có số tiền và hạn chưa qua · đợt còn thiếu tiền · đợt chưa có link đang mở ·
     tài khoản nhận QR đã ký. Số tiền = phần còn thiếu của đợt LÚC TẠO (phép rải của lich_thanh_toan.bang).
  2. Khách mở kh.vietourist.vn/thanh-toan/TD000123 — không cần đăng nhập — thấy số tiền, QR chuyển khoản và
     thông tin chuyển tay. KHÔNG có thẻ (Chủ tịch 02/11: tour đoàn không áp dụng Visa / Master).
  3. Tiền về có «TD000123» + đúng số → robot lập phiếu thu (chờ Kế toán xác nhận), link «đã trả», email kèm
     hóa đơn PDF. Lệch số → «chờ Kế toán», không email; Kế toán gán tay xong mà đợt đã đủ → link «đã trả» + email.
"""
import re
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ban_hang import BaoGia, HopDongKhach, LichThanhToanHD
from app.models.core import Booking, Tour, User
from app.models.thanh_toan_doan import TRANG_THAI_LINK, LinkThanhToanDoan
from app.services import rules as R

QUYEN_TAO = ("sales_admin",)                     # Chủ tịch chốt 02/11/2026: CHỈ Sale Admin tạo / hủy link
GOC_LINK = "https://kh.vietourist.vn/thanh-toan/"
MA_RE = re.compile(r"TD(\d{6})")
SAI_SO = 0.5


class LoiTTD(Exception):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def _vnd(x) -> str:
    return f"{int(round(float(x or 0))):,}".replace(",", ".")


def _kiem_quyen(u: User) -> None:
    if u.role not in QUYEN_TAO:
        raise LoiTTD("Chỉ Sale Admin phòng Đoàn được tạo / hủy link thanh toán", 403)


def trang_thai(l: LinkThanhToanDoan, hom_nay: date | None = None) -> str:
    """mo / da_tra / huy / het_han — «hết hạn» là phép tính, không lưu."""
    if l.trang_thai == "mo" and l.han < (hom_nay or date.today()):
        return "het_han"
    return l.trang_thai


def _dot_con_thieu(db: Session, hd: HopDongKhach, lich: LichThanhToanHD) -> float:
    from app.services import lich_thanh_toan as LTT
    for d in LTT.bang(db, hd)["dot"]:
        if d["id"] == lich.id:
            return float(d["con_thieu"])
    return 0.0


def _ra(db: Session, l: LinkThanhToanDoan, hom_nay: date | None = None) -> dict:
    tt = trang_thai(l, hom_nay)
    return {"ma": l.ma, "link": GOC_LINK + l.ma, "lich_id": l.lich_id, "hop_dong_id": l.hop_dong_id,
            "so_tien": float(l.so_tien), "han": l.han.isoformat(), "trang_thai": tt,
            "trang_thai_ten": "Hết hạn" if tt == "het_han" else TRANG_THAI_LINK.get(tt, tt),
            "email": l.email, "dien_thoai": l.dien_thoai, "tao_boi": l.tao_boi,
            "tao_luc": l.tao_luc.isoformat() if l.tao_luc else None, "tra_luc": l.tra_luc.isoformat() if l.tra_luc else None,
            "huy_boi": l.huy_boi, "ly_do_huy": l.ly_do_huy,
            "email_link_luc": l.email_link_luc.isoformat() if l.email_link_luc else None,
            "email_hd_luc": l.email_hd_luc.isoformat() if l.email_hd_luc else None, "email_loi": l.email_loi}


def ds_theo_hop_dong(db: Session, hid: int, hom_nay: date | None = None) -> dict:
    from app.services import tour_online as TRO
    ds = db.execute(select(LinkThanhToanDoan).where(LinkThanhToanDoan.hop_dong_id == hid)
                    .order_by(LinkThanhToanDoan.id.desc())).scalars()
    return {"tt_chung": TRO.tt_chung(db), "link": [_ra(db, l, hom_nay) for l in ds]}


def tao(db: Session, u: User, lich_id: int, email: str = "", dien_thoai: str = "", gui_email: bool = True,
        now: datetime | None = None) -> dict:
    from app.services import cong_khach as K
    from app.services import tour_online as TRO
    now = now or datetime.now()
    _kiem_quyen(u)
    if not TRO.tt_chung(db):
        raise LoiTTD("Công tắc thanh toán chung đang tắt — chưa tạo được link", 409)
    lich = db.get(LichThanhToanHD, lich_id)
    if lich is None:
        raise LoiTTD("Không có đợt thanh toán này", 404)
    hd = db.get(HopDongKhach, lich.hop_dong_id)
    if hd is None or hd.trang_thai in ("huy", "thanh_ly"):
        raise LoiTTD("Hợp đồng đã hủy hoặc đã thanh lý — không tạo link", 409)
    bg = db.get(BaoGia, hd.bao_gia_id) if hd.bao_gia_id else None
    if bg is None or bg.trang_thai != "khach_chot":
        raise LoiTTD("Hợp đồng chưa đi từ báo giá khách đã chốt — số tiền chưa có căn cứ", 409)
    if not hd.booking_id:
        raise LoiTTD("Hợp đồng chưa nối booking — nối booking trước rồi tạo link", 409)
    b = db.get(Booking, hd.booking_id)
    if b is None or b.cancelled:
        raise LoiTTD("Booking của hợp đồng đã hủy", 409)
    if lich.so_tien is None:
        raise LoiTTD(f"Đợt {lich.dot} chưa có số tiền — đặt lịch thanh toán trước", 409)
    if lich.han is None or lich.han < now.date():
        raise LoiTTD(f"Đợt {lich.dot} chưa có hạn hoặc hạn đã qua — dời hạn đợt rồi tạo link", 409)
    con = round(_dot_con_thieu(db, hd, lich))
    if con <= SAI_SO:
        raise LoiTTD(f"Đợt {lich.dot} đã thu đủ — không cần link", 409)
    for l in db.execute(select(LinkThanhToanDoan).where(LinkThanhToanDoan.lich_id == lich.id,
                                                        LinkThanhToanDoan.trang_thai == "mo")).scalars():
        if trang_thai(l, now.date()) == "mo":
            raise LoiTTD(f"Đợt {lich.dot} đang có link {l.ma} — hủy link cũ trước", 409)
    ba = K.tai_khoan_qr(db)
    if ba is None or not ba.account_number:
        raise LoiTTD("Tài khoản nhận chuyển khoản (cong_qr_tai_khoan) chưa ký — chưa tạo được link", 409)
    email = (email or bg.khach_email or b.customer_email or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise LoiTTD("Email nhận link không hợp lệ")
    l = LinkThanhToanDoan(ma=f"tam-{uuid.uuid4().hex[:12]}", hop_dong_id=hd.id, lich_id=lich.id, booking_id=b.id,
                          so_tien=float(con), han=lich.han, trang_thai="mo", email=email,
                          dien_thoai=(dien_thoai or bg.khach_dien_thoai or b.customer_phone or "").strip()[:30],
                          tao_boi=u.username, tao_luc=now)
    db.add(l); db.flush()
    l.ma = f"TD{l.id:06d}"
    R.audit(db, u.username, u.role, "tao_link_thanh_toan_doan", f"link:{l.ma}",
            after={"hop_dong": hd.so_hop_dong, "dot": lich.dot, "so_tien": con, "han": lich.han.isoformat()})
    if gui_email and email:
        gui_email_link(db, l, now)
    db.commit()
    return _ra(db, l, now.date())


def _link(db: Session, ma: str) -> LinkThanhToanDoan:
    l = db.execute(select(LinkThanhToanDoan).where(LinkThanhToanDoan.ma == (ma or "").strip().upper())).scalars().first()
    if l is None:
        raise LoiTTD("Không có link thanh toán này", 404)
    return l


def huy(db: Session, u: User, ma: str, ly_do: str, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    _kiem_quyen(u)
    l = _link(db, ma)
    if l.trang_thai != "mo":
        raise LoiTTD(f"Link đang «{TRANG_THAI_LINK.get(l.trang_thai, l.trang_thai)}» — không hủy được", 409)
    if len((ly_do or "").strip()) < 5:
        raise LoiTTD("Ghi lý do hủy link")
    l.trang_thai, l.huy_boi, l.huy_luc, l.ly_do_huy = "huy", u.username, now, ly_do.strip()[:300]
    R.audit(db, u.username, u.role, "huy_link_thanh_toan_doan", f"link:{l.ma}", after={"ly_do": l.ly_do_huy})
    db.commit()
    return _ra(db, l, now.date())


def gui_lai(db: Session, u: User, ma: str, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    _kiem_quyen(u)
    l = _link(db, ma)
    tt = trang_thai(l, now.date())
    if tt == "mo":
        ok = gui_email_link(db, l, now)
    elif tt == "da_tra":
        ok = gui_email_hoa_don(db, l, now)
    else:
        raise LoiTTD("Link đã hủy hoặc hết hạn — tạo link mới", 409)
    db.commit()
    if not ok:
        raise LoiTTD(f"Chưa gửi được email: {l.email_loi or 'thiếu địa chỉ email'}", 502)
    return _ra(db, l, now.date())


# ══ KHÁCH XEM (không đăng nhập) ══════════════════════════════════════════════════════════════════════════════════

def _tom_tat(db: Session, l: LinkThanhToanDoan) -> dict:
    from app.services import lich_thanh_toan as LTT
    hd = db.get(HopDongKhach, l.hop_dong_id)
    lich = db.get(LichThanhToanHD, l.lich_id)
    b = db.get(Booking, l.booking_id)
    t = db.get(Tour, b.tour_id) if b and b.tour_id else None
    bang = LTT.bang(db, hd)
    return {"hd": hd, "lich": lich, "b": b, "t": t, "bang": bang,
            "so_dot": len(bang["dot"]), "tong_hd": float(hd.gia_tri or 0), "da_thu": float(bang["da_thu"])}


def xem_cong(db: Session, ma: str, hom_nay: date | None = None) -> dict:
    from app.services import cong_khach as K
    from app.services import vietqr as Q
    l = _link(db, ma)
    x = _tom_tat(db, l)
    hd, lich, b, t = x["hd"], x["lich"], x["b"], x["t"]
    tt = trang_thai(l, hom_nay)
    ra = {"ma": l.ma, "trang_thai": tt, "trang_thai_ten": "Hết hạn" if tt == "het_han" else TRANG_THAI_LINK.get(tt, tt),
          "khach": hd.khach_ten, "so_hop_dong": hd.so_hop_dong,
          "tour": (t.name if t else ""), "khoi_hanh": t.start_date.isoformat() if t and t.start_date else None,
          "so_khach": int(b.pax or 0) if b else 0,
          "dot": lich.dot if lich else None, "ten_dot": lich.ten if lich else "", "so_dot": x["so_dot"],
          "so_tien": float(l.so_tien), "han": l.han.isoformat(), "tong_hd": x["tong_hd"], "da_thu": x["da_thu"],
          "tra_luc": l.tra_luc.isoformat() if l.tra_luc else None, "chuyen_khoan": None,
          "ghi_chu": "Tour đoàn chỉ nhận chuyển khoản. Số tiền cố định theo hợp đồng — cần đổi, liên hệ Sales phụ trách."}
    if tt == "mo":
        ba = K.tai_khoan_qr(db)
        bin_ = Q.bin_cua(ba.bank_name) if ba is not None and ba.account_number else None
        if bin_:
            so = int(round(float(l.so_tien or 0)))
            ra["chuyen_khoan"] = {"ngan_hang": ba.bank_name, "so_tk": ba.account_number, "chu_tk": ba.account_name,
                                  "so_tien": so, "noi_dung": Q.noi_dung_sach(l.ma), "payload": Q.payload(bin_, ba.account_number, so, l.ma)}
    return ra


def tai_hoa_don(db: Session, ma: str) -> bytes:
    l = _link(db, ma)
    if l.trang_thai != "da_tra":
        raise LoiTTD("Link chưa được thanh toán — chưa có hóa đơn", 409)
    return hoa_don_pdf(db, l)


# ══ TIỀN VỀ ══════════════════════════════════════════════════════════════════════════════════════════════════════

def _da_tra(db: Session, l: LinkThanhToanDoan, receipt_id: int | None, now: datetime) -> None:
    l.trang_thai, l.receipt_id, l.tra_luc = "da_tra", receipt_id, now
    R.audit(db, "he_thong", "he_thong", "link_thanh_toan_doan_da_tra", f"link:{l.ma}", after={"so_tien": float(l.so_tien)})
    gui_email_hoa_don(db, l, now)


def tu_khop(db: Session, txn, now: datetime | None = None) -> bool:
    """Gọi từ khớp giao dịch ngân hàng, TRƯỚC đường booking chung. Nội dung có «TD……» của một link:
    đúng số và link đang mở → phiếu thu tự động (chờ Kế toán xác nhận) + link «đã trả» + email hóa đơn.
    Lệch số / link không mở → «chờ Kế toán» gắn sẵn booking, không email. Trả True khi đã xử lý."""
    from app.services import payments as P
    now = now or datetime.now()
    m = MA_RE.search((txn.content or "").upper().replace(" ", "").replace("-", ""))
    if not m:
        return False
    l = db.execute(select(LinkThanhToanDoan).where(LinkThanhToanDoan.ma == "TD" + m.group(1))).scalars().first()
    if l is None:
        return False
    b = db.get(Booking, l.booking_id)
    so = float(txn.amount or 0)
    # KS-19o (06/11/2026): «hết hạn» xét theo NGÀY TIỀN VỀ (ngày giao dịch ngân hàng), không theo lúc robot chạy —
    # khách chuyển trong hạn mà robot / SePay đồng bộ trễ một ngày thì vẫn là trả đúng hạn.
    luc_ve = getattr(txn, "transaction_date", None) or now
    tt = trang_thai(l, (luc_ve.date() if hasattr(luc_ve, "date") else luc_ve))
    if b is None or b.cancelled or tt != "mo" or abs(so - float(l.so_tien or 0)) >= 1:
        ly_do = (f"link {l.ma} đang «{tt}»" if tt != "mo" else
                 f"số {_vnd(so)} ≠ {_vnd(l.so_tien)} của link {l.ma}") if b is not None else f"link {l.ma} mất booking"
        txn.match_status, txn.booking_id = "cho_ke_toan", (b.id if b is not None else None)
        txn.match_note = f"Tour đoàn: {ly_do} – Kế toán quyết định"
        return True
    r = P._make_receipt(db, b, txn, so, "robot", "tu_dong", note=f"Link thanh toán đoàn {l.ma} — khớp mã + đúng số")
    txn.match_status, txn.booking_id, txn.match_note = "da_khop", b.id, f"Tự động (link đoàn {l.ma}): {r.code}"
    R.audit(db, "robot", "robot", "link_doan_tu_khop", f"receipt:{r.code}", after={"booking": b.code, "so_tien": so, "link": l.ma})
    db.flush()
    _da_tra(db, l, r.id, now)
    return True


def sau_phieu_thu(db: Session, booking_id: int, receipt_id: int | None = None, now: datetime | None = None) -> int:
    """Kế toán gán tay / thu tiền mặt vào booking của một hợp đồng đoàn: link đang mở mà đợt của nó nay đã đủ
    → «đã trả» + email hóa đơn. Trả số link vừa chuyển."""
    now = now or datetime.now()
    n = 0
    for l in db.execute(select(LinkThanhToanDoan).where(LinkThanhToanDoan.booking_id == booking_id,
                                                        LinkThanhToanDoan.trang_thai == "mo")).scalars().all():
        hd, lich = db.get(HopDongKhach, l.hop_dong_id), db.get(LichThanhToanHD, l.lich_id)
        if hd is not None and lich is not None and _dot_con_thieu(db, hd, lich) <= SAI_SO:
            _da_tra(db, l, receipt_id, now)
            n += 1
    return n


# ══ EMAIL + HÓA ĐƠN PDF ══════════════════════════════════════════════════════════════════════════════════════════

def gui_email_link(db: Session, l: LinkThanhToanDoan, now: datetime | None = None) -> bool:
    from app.services import tour_online as TRO
    now = now or datetime.now()
    if not l.email:
        return False
    x = _tom_tat(db, l)
    try:
        noi = (f"Kính gửi {x['hd'].khach_ten},\n\nVietourist gửi link thanh toán đợt {x['lich'].dot}/{x['so_dot']}"
               f" ({x['lich'].ten}) của hợp đồng {x['hd'].so_hop_dong}"
               + (f" — {x['t'].name}, khởi hành {x['t'].start_date:%d/%m/%Y}" if x["t"] and x["t"].start_date else "") + ".\n"
               f"Số tiền: {_vnd(l.so_tien or 0)} đ · hạn {l.han:%d/%m/%Y}.\n\n{GOC_LINK}{l.ma}\n\n"
               f"Thanh toán bằng chuyển khoản (QR hoặc chuyển tay), nội dung ghi đúng mã {l.ma}.\n\nVietourist")
        TRO.GUI_EMAIL(l.email, f"Link thanh toán đợt {x['lich'].dot} · {x['hd'].so_hop_dong}", noi, [])
        l.email_link_luc, l.email_loi = now, ""
        return True
    except Exception as ex:   # noqa: BLE001
        l.email_loi = f"{now:%d/%m %H:%M} {ex}"[:300]
        return False


def gui_email_hoa_don(db: Session, l: LinkThanhToanDoan, now: datetime | None = None) -> bool:
    """Lỗi gửi chỉ GHI LẠI, không làm hỏng việc nhận tiền."""
    from app.services import tour_online as TRO
    now = now or datetime.now()
    if not l.email:
        return False
    x = _tom_tat(db, l)
    try:
        pdf = hoa_don_pdf(db, l, now)
        con = max(0.0, x["tong_hd"] - x["da_thu"])
        noi = (f"Kính gửi {x['hd'].khach_ten},\n\nVietourist đã nhận {_vnd(l.so_tien)} đ (chuyển khoản, nội dung {l.ma}) "
               f"cho đợt {x['lich'].dot}/{x['so_dot']} của hợp đồng {x['hd'].so_hop_dong}"
               + (f" — {x['t'].name}, khởi hành {x['t'].start_date:%d/%m/%Y}" if x["t"] and x["t"].start_date else "") + ".\n"
               + (f"Hợp đồng đã thanh toán đủ {_vnd(x['tong_hd'])} đ." if con <= SAI_SO else
                  f"Đã thanh toán {_vnd(x['da_thu'])} / {_vnd(x['tong_hd'])} đ · còn lại {_vnd(con)} đ.")
               + "\nHóa đơn đính kèm.\n\nVietourist")
        TRO.GUI_EMAIL(l.email, f"Xác nhận thanh toán đợt {x['lich'].dot} · {x['hd'].so_hop_dong}", noi,
                      [(f"HoaDon-{x['hd'].so_hop_dong}-dot{x['lich'].dot}.pdf", pdf, "application/pdf")])
        l.email_hd_luc, l.email_loi = now, ""
        R.audit(db, "he_thong", "he_thong", "link_doan_email_hoa_don", f"link:{l.ma}", after={"email": l.email})
        return True
    except Exception as ex:   # noqa: BLE001
        l.email_loi = f"{now:%d/%m %H:%M} {ex}"[:300]
        return False


def hoa_don_pdf(db: Session, l: LinkThanhToanDoan, now: datetime | None = None) -> bytes:
    """Chứng từ xác nhận thanh toán (KHÔNG phải hóa đơn GTGT điện tử — Kế toán xuất riêng). Cùng mẫu TR-1."""
    import io
    from PIL import Image, ImageDraw
    from app.core.config import settings
    from app.models.payments import Receipt
    from app.services import tour_online as TRO
    now = now or datetime.now()
    x = _tom_tat(db, l)
    hd, lich, b, t = x["hd"], x["lich"], x["b"], x["t"]
    W, H, L = 1240, 1754, 90
    im = Image.new("RGB", (W, H), "white")
    g = ImageDraw.Draw(im)
    if not TRO.co_phong_viet():
        _ve = g.text
        g.text = lambda xy, chu, **k: _ve(xy, TRO._bo_dau(str(chu)), **k)      # type: ignore[method-assign]
    f_to, f_dam, f_th, f_nho = TRO._phong(40, True), TRO._phong(24, True), TRO._phong(24), TRO._phong(20)
    y = 80
    g.text((L, y), settings.COMPANY_NAME, font=f_dam, fill="#0f2f6b"); y += 40
    g.text((L, y), "Vietourist · www.vietourist.com.vn · kh.vietourist.vn", font=f_nho, fill="#555"); y += 70
    g.text((L, y), "XÁC NHẬN THANH TOÁN · TOUR ĐOÀN", font=f_to, fill="#111"); y += 70
    for k, v in (("Hợp đồng", hd.so_hop_dong), ("Ngày lập", f"{now:%d/%m/%Y %H:%M}"), ("Khách hàng", hd.khach_ten),
                 ("Mã số thuế", hd.khach_ma_so_thue or "—"), ("Tour", t.name if t else "—"),
                 ("Khởi hành · số khách", (f"{t.start_date:%d/%m/%Y}" if t and t.start_date else "—") + f" · {int(b.pax or 0) if b else 0} khách"),
                 ("Đợt thanh toán", f"{lich.dot}/{x['so_dot']} · {lich.ten}"), ("Mã thanh toán", l.ma)):
        g.text((L, y), k, font=f_nho, fill="#666"); g.text((L + 330, y), str(v)[:70], font=f_th, fill="#111"); y += 42
    y += 20
    g.line((L, y, W - L, y), fill="#999", width=2); y += 20
    con = max(0.0, x["tong_hd"] - x["da_thu"])
    for k, v, dam in (("Số tiền đợt này", float(l.so_tien), True), ("Giá trị hợp đồng", x["tong_hd"], False),
                      ("Đã thanh toán", x["da_thu"], True), ("Còn lại", con, False)):
        g.text((L, y), k, font=f_dam if dam else f_th, fill="#111"); g.text((W - L - 300, y), f"{_vnd(v)} đ", font=f_dam if dam else f_th, fill="#111"); y += 44
    y += 20
    g.text((L, y), "Các lần thanh toán", font=f_dam, fill="#111"); y += 40
    for r in db.execute(select(Receipt).where(Receipt.booking_id == b.id, Receipt.status != "huy").order_by(Receipt.id)).scalars():
        cach = "Tiền mặt" if r.method == "tien_mat" else "Chuyển khoản"
        g.text((L, y), f"{r.code} · {r.created_at:%d/%m/%Y %H:%M} · {cach}", font=f_nho, fill="#333")
        g.text((W - L - 300, y), f"{_vnd(r.amount or 0)} đ", font=f_nho, fill="#333"); y += 34
    g.text((L, H - 120), "Chứng từ xác nhận thanh toán do hệ thống Vietourist lập tự động — không thay hóa đơn GTGT.", font=f_nho, fill="#777")
    buf = io.BytesIO()
    im.save(buf, "PDF", resolution=150.0)
    return buf.getvalue()
