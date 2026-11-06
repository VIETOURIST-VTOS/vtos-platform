# -*- coding: utf-8 -*-
"""KS-20e · Email + PDF sau thanh toán đặt phòng VTD (Chủ tịch duyệt bản xem thử 07/11/2026, theo mẫu Agoda).

  · Phiếu xác nhận đặt phòng (Booking Confirmation) — song ngữ, A4, xuất trình khi nhận phòng.
  · Hóa đơn đặt phòng khách sạn (Hotel Booking Invoice) — song ngữ, A4, đã thanh toán bao nhiêu, gồm VAT.
  · Email xác nhận song ngữ, đính kèm cả hai PDF. Khách tải lại hai PDF trong «Đơn của tôi».

Tên, MST, địa chỉ, hotline người phát hành lấy từ hồ sơ pháp nhân công ty mẹ trong VTOS (màn «Pháp nhân»), thiếu thì
ghi «chưa khai» — máy không tự điền. Không in chữ ký giả: ô «Xác nhận điện tử» kèm mã tra cứu.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.don_ks_vtd import TT_DA_TRA_KS, DonKsVtd, ThanhToanKsVtd
from app.models.khach_san_vtd import KhachSanVtd

LOGO = Path(__file__).resolve().parents[1] / "static" / "logo" / "khoachu-holdings-ngang.svg"
NAVY, HONG, XAM, NEN = (20, 83, 141), (252, 77, 122), (77, 91, 106), (233, 237, 242)
PHONG_CHU = [  # (thường, đậm) — phông có đủ dấu tiếng Việt; Dockerfile cài fonts-dejavu-core
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
]
KENH = {"qr": "QR chuyển khoản", "onepay": "Thẻ (OnePay)", "sepay": "Thẻ (cổng SePay)"}
THU = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
THANG = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class LoiPhieu(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def phong_chu() -> tuple[str, str] | None:
    return next(((a, b) for a, b in PHONG_CHU if os.path.exists(a) and os.path.exists(b)), None)


def _vnd(x) -> str:
    return f"{int(round(float(x or 0))):,}".replace(",", ".") + " ₫"


def _dmy(d: date | str | None) -> str:
    if not d:
        return ""
    d = date.fromisoformat(str(d)[:10]) if not isinstance(d, date) else d
    return f"{d:%d/%m/%Y}"


def _en(d: date) -> str:
    return f"{THU[d.weekday()]}, {d.day:02d} {THANG[d.month - 1]} {d.year}"


def nguoi_phat_hanh(db: Session) -> dict:
    """Tên / MST / địa chỉ / hotline của công ty mẹ — từ màn «Pháp nhân» trong VTOS; thiếu thì ghi chưa khai."""
    from app.core.config import settings
    from app.models.core import Company
    c = db.execute(select(Company).where(Company.kind == "me", Company.active.is_(True)).order_by(Company.id)).scalars().first()
    return {"ten": (c.name if c else "") or settings.COMPANY_NAME,
            "mst": (c.tax_code if c else "") or settings.COMPANY_TAX_CODE or "chưa khai",
            "dia_chi": (getattr(c, "address", "") if c else "") or "chưa khai",
            "hotline": (getattr(c, "phone", "") if c else "") or "chưa khai"}


def don_vi(d: DonKsVtd) -> list[dict]:
    """Các phòng theo thứ tự P1, P2…; đơn không khai từng phòng → mỗi dòng gói một mục."""
    ra = []
    for x in d.dong or []:
        ks = x.get("khach") or []
        if ks:
            for kh in ks:
                ra.append({"x": x, "kh": kh, "n": int(kh["phong"])})
        else:
            ra.append({"x": x, "kh": None, "n": 99})
    return sorted(ra, key=lambda v: v["n"])


def _nhan_dv(v: dict) -> str:
    return f"P{v['kh']['phong']}" if v["kh"] else f"{v['x']['so']} ×"


def _khach(kh: dict | None, x: dict) -> str:
    if not kh:
        return ""
    t = f"{kh['nl']} NL"
    if kh.get("te"):
        t += f" + {kh['te']} trẻ ({', '.join(str(a) for a in kh.get('tuoi') or [])})"
    return t


def _huy(x: dict) -> str:
    if not x.get("huy_han"):
        return "Không hoàn tiền"
    gio = f" {x['huy_gio_chot']}" if x.get("huy_gio_chot") else ""
    return f"Miễn phí đến {_dmy(x['huy_han'])}{gio}"


def thanh_toan(db: Session, d: DonKsVtd) -> tuple[datetime | None, str]:
    t = db.execute(select(ThanhToanKsVtd).where(ThanhToanKsVtd.don_id == d.id, ThanhToanKsVtd.trang_thai.in_(TT_DA_TRA_KS))
                   .order_by(ThanhToanKsVtd.luc.desc())).scalars().first()
    return (d.tra_luc or (t.luc if t else None)), (KENH.get(t.kenh, t.kenh) if t else "")


def _che_sdt(s: str) -> str:
    so = "".join(ch for ch in (s or "") if ch.isdigit())
    return f"{so[:2]}•• ••• {so[-3:]}" if len(so) >= 7 else ""


def _ks(db: Session, d: DonKsVtd) -> KhachSanVtd | None:
    return db.get(KhachSanVtd, d.khach_san_id)


def kiem(d: DonKsVtd, loai: str) -> None:
    from app.services import don_ks_vtd as KV
    if loai == "phieu" and d.trang_thai != "da_xac_nhan":
        raise LoiPhieu("Phiếu xác nhận có khi đơn đã được xác nhận", 409)
    if loai == "hoa_don" and d.trang_thai not in ("da_tra", "da_xac_nhan"):
        raise LoiPhieu("Hóa đơn có khi đơn đã thanh toán", 409)
    if loai not in ("phieu", "hoa_don"):
        raise LoiPhieu("Loại giấy tờ không hợp lệ", 404)
    _ = KV


# ───────────────────────────────────────────────────────────────────────────────────── PDF
def _pdf():
    from fpdf import FPDF
    pc = phong_chu()
    if pc is None:
        raise LoiPhieu("Máy chủ thiếu phông chữ tiếng Việt để in PDF — báo CNTT cài fonts-dejavu-core", 503)
    p = FPDF(format="A4", unit="mm")
    p.set_auto_page_break(True, 14)
    p.add_font("VN", "", pc[0])
    p.add_font("VN", "B", pc[1])
    p.set_margins(14, 12, 14)
    p.add_page()
    return p


def _o(p, w, h, nhan, phu, gia, dam=True, khung=False, nen=False):
    """Một ô hai tầng: nhãn tiếng Anh + nhãn tiếng Việt nhỏ, rồi giá trị."""
    x, y = p.get_x(), p.get_y()
    if nen:
        p.set_fill_color(*NEN)
        p.rect(x, y, w, h, "F")
    if khung:
        p.set_draw_color(196, 205, 214)
        p.rect(x, y, w, h)
    p.set_xy(x + 2, y + 1.5)
    p.set_font("VN", "", 8)
    p.set_text_color(20, 38, 59)
    p.cell(w - 4, 3.6, nhan)
    p.set_xy(x + 2, y + 5)
    p.set_font("VN", "", 6.5)
    p.set_text_color(*XAM)
    p.cell(w - 4, 3, phu)
    p.set_xy(x + 2, y + 8.6)
    p.set_font("VN", "B" if dam else "", 9.5)
    p.set_text_color(20, 38, 59)
    p.multi_cell(w - 4, 4.4, gia, align="L")
    p.set_xy(x + w, y)


def pdf_phieu(db: Session, d: DonKsVtd) -> bytes:
    """Phiếu xác nhận đặt phòng (Booking Confirmation) A4 — như phiếu Agoda."""
    kiem(d, "phieu")
    k, ph = _ks(db, d), nguoi_phat_hanh(db)
    tra_luc, kenh = thanh_toan(db, d)
    p = _pdf()
    if LOGO.exists():
        p.image(str(LOGO), x=14, y=11, h=13)
    p.set_xy(100, 11)
    p.set_font("VN", "B", 18)
    p.set_text_color(20, 38, 59)
    p.cell(56, 8, "Booking", align="R")
    p.set_text_color(*HONG)
    p.cell(40, 8, " Confirmation")
    p.set_xy(90, 19)
    p.set_font("VN", "", 7.5)
    p.set_text_color(*XAM)
    p.cell(106, 4, "Phiếu xác nhận đặt phòng — xuất trình bản điện tử hoặc bản in khi nhận phòng", align="R")
    p.set_draw_color(*NAVY)
    p.set_line_width(0.8)
    p.line(14, 26, 196, 26)
    p.set_line_width(0.2)
    y = 29
    trai = [("Booking ID", "Mã đặt phòng VTD", d.ma), ("Hotel confirmation no.", "Mã xác nhận khách sạn", d.ma_xac_nhan_ks or "Vietourist gửi khi có"),
            ("Lead guest", "Khách chính", d.ho_ten), ("Property", "Khách sạn", f"{k.ten if k else ''}{' ' + '★' * k.sao if k and k.sao else ''}"),
            ("Address", "Địa chỉ", (k.dia_chi if k else "") or ", ".join(filter(None, [k.khu_vuc if k else "", k.tinh_thanh if k else ""])))]
    for nhan, phu, gia in trai:
        p.set_xy(14, y)
        _o(p, 100, 15, nhan, phu, gia, khung=True)
        y += 16
    te_tuoi = [str(t) for v in don_vi(d) if v["kh"] for t in (v["kh"].get("tuoi") or [])]
    phai = [("Number of rooms", "Số phòng", str(d.so_phong)), ("Adults", "Người lớn", str(d.nguoi_lon)),
            ("Children (ages)", "Trẻ em (tuổi)", f"{d.tre_em}" + (f" ({', '.join(te_tuoi)})" if te_tuoi else "")),
            ("Nights", "Số đêm", str((d.ra - d.vao).days)), ("Arrival time", "Giờ đến dự kiến", d.gio_den or "Chưa rõ")]
    y2 = 29
    for nhan, phu, gia in phai:
        p.set_xy(118, y2)
        _o(p, 78, 15, nhan, phu, gia, nen=True)
        y2 += 16
    y = max(y, y2) + 2
    gio_nhan, gio_tra = (k.gio_nhan if k else "14:00"), (k.gio_tra if k else "12:00")
    p.set_xy(14, y)
    _o(p, 89, 15, "Arrival", "Ngày đến", f"{_en(d.vao)} — from {gio_nhan}", khung=True)
    p.set_xy(107, y)
    _o(p, 89, 15, "Departure", "Ngày đi", f"{_en(d.ra)} — before {gio_tra}", khung=True)
    y += 19
    # danh sách phòng
    p.set_xy(14, y)
    p.set_font("VN", "B", 10)
    p.cell(0, 5, "Rooming list · Danh sách phòng")
    y += 6
    cot = [(14, "Room"), (46, "Room type · Loại phòng"), (42, "Rate · Gói"), (34, "Guests · Khách"), (46, "Cancellation · Hủy")]
    p.set_fill_color(*NEN)
    p.set_xy(14, y)
    p.set_font("VN", "B", 7.5)
    for w, t in cot:
        p.cell(w, 6, t, border=1, fill=True)
    y += 6
    p.set_font("VN", "", 8)
    for v in don_vi(d):
        x = v["x"]
        p.set_xy(14, y)
        goi = x.get("goi", "") + (" · bữa sáng" if x.get("bua_sang") and "sáng" not in x.get("goi", "").lower() else "")
        hang = [_nhan_dv(v), x.get("loai_phong", ""), goi, _khach(v["kh"], x), _huy(x)]
        for (w, _t), t in zip(cot, hang):
            p.cell(w, 6, t[:34], border=1)
        y += 6
    y += 3
    yc = [t for t in (d.yeu_cau or "").split("\n") if t.strip() and not t.startswith("Phòng ")]
    p.set_xy(14, y)
    p.set_fill_color(*NEN)
    p.set_font("VN", "", 8)
    p.multi_cell(182, 4.4, "Bao gồm · Inclusions: " + ("; ".join(sorted({f"{_nhan_dv(v)} bữa sáng" for v in don_vi(d) if v["x"].get("bua_sang")})) or "chỉ phòng")
                 + f". Giá đã gồm VAT 8%. Yêu cầu đặc biệt (tùy khả năng của khách sạn): {'; '.join(yc) or 'không'}.", fill=True, align="L")
    y = p.get_y() + 3
    p.set_xy(14, y)
    p.set_draw_color(196, 205, 214)
    p.rect(14, y, 182, 34)
    p.set_xy(16, y + 2)
    p.set_font("VN", "", 8.5)
    p.multi_cell(128, 4.6, f"Thanh toán · Payment: Đã thanh toán đủ {_vnd(d.tong)}" + (f" · {kenh}" if kenh else "")
                 + (f" · {tra_luc:%d/%m/%Y}" if tra_luc else ""), align="L")
    p.set_x(16)
    p.multi_cell(128, 4.6, "Đặt phòng và chi trả bởi · Booked and payable by:", align="L")
    p.set_x(16)
    p.set_font("VN", "B", 8.5)
    p.multi_cell(128, 4.6, ph["ten"], align="L")
    p.set_x(16)
    p.set_font("VN", "", 8)
    p.multi_cell(128, 4.4, f"MST: {ph['mst']} · {ph['dia_chi']} · Hotline: {ph['hotline']}", align="L")
    p.set_draw_color(154, 166, 178)
    p.set_dash_pattern(1, 1)
    p.rect(150, y + 3, 44, 28)
    p.set_dash_pattern()
    p.set_xy(150, y + 10)
    p.set_font("VN", "B", 8)
    p.multi_cell(44, 4.4, "Xác nhận điện tử\nkhông cần chữ ký", align="C")
    p.set_x(150)
    p.set_font("VN", "", 7.5)
    p.multi_cell(44, 4, f"Mã tra cứu: {d.ma}", align="C")
    y += 38
    p.set_xy(14, y)
    p.set_font("VN", "B", 8.5)
    p.cell(0, 5, "Ghi chú · Notes")
    p.ln(5)
    p.set_font("VN", "", 7.8)
    for t in ("• QUAN TRỌNG: khi nhận phòng, khách chính xuất trình giấy tờ tùy thân có ảnh, đúng tên trên phiếu.",
              "• Các phòng được giữ suốt ngày nhận phòng. Không đến nhận phòng được tính như hủy sau hạn theo chính sách từng phòng.",
              "• Giá không gồm minibar, giặt ủi, điện thoại… khách sạn thu trực tiếp. Không thu thêm tiền phòng tại khách sạn.",
              f"• Phiếu do VTOS lập tự động. Đổi / hủy đơn: «Đơn của tôi» trên cổng Vietourist hoặc hotline {ph['hotline']}."):
        p.set_x(14)
        p.multi_cell(182, 4.2, t, align="L")
    return bytes(p.output())


def pdf_hoa_don(db: Session, d: DonKsVtd) -> bytes:
    """Hóa đơn đặt phòng khách sạn (Hotel Booking Invoice) A4 — như biên lai Agoda."""
    from app.services import khach_san_vtd as S
    kiem(d, "hoa_don")
    k, ph = _ks(db, d), nguoi_phat_hanh(db)
    tra_luc, kenh = thanh_toan(db, d)
    p = _pdf()
    p.set_text_color(20, 38, 59)
    p.set_font("VN", "", 8.5)
    p.set_xy(14, 14)
    p.multi_cell(110, 4.6, f"Địa chỉ · Address:\n{ph['ten']}\nMST: {ph['mst']}\n{ph['dia_chi']}\nHotline: {ph['hotline']}", align="L")
    if LOGO.exists():
        p.image(str(LOGO), x=138, y=12, h=14)
    y = 42
    for a, b, c in (("Mã số đặt phòng", "Booking ID", d.ma), ("Ngày trả tiền", "Payment date", f"{tra_luc:%d/%m/%Y}" if tra_luc else ""),
                    ("Số chứng từ", "Document no.", f"HD-{d.ma}")):
        p.set_xy(14, y)
        p.set_font("VN", "", 8.5)
        p.cell(42, 4.5, a)
        p.set_font("VN", "B", 9)
        p.cell(60, 4.5, c)
        p.set_xy(14, y + 4.2)
        p.set_font("VN", "", 6.8)
        p.set_text_color(*XAM)
        p.cell(42, 3.5, b)
        p.set_text_color(20, 38, 59)
        y += 10
    p.set_xy(14, y + 2)
    p.set_font("VN", "B", 14)
    p.cell(182, 7, "Hóa đơn đặt phòng khách sạn", align="C")
    p.set_xy(14, y + 9)
    p.set_font("VN", "", 8.5)
    p.set_text_color(*XAM)
    p.cell(182, 4.5, "Hotel Booking Invoice", align="C")
    p.set_text_color(20, 38, 59)
    y += 17
    # khách hàng
    p.set_draw_color(138, 151, 165)
    p.set_fill_color(*NEN)
    p.set_xy(14, y)
    p.set_font("VN", "B", 8.5)
    p.cell(182, 6, "Họ tên & địa chỉ khách hàng · Customer", border=1, align="C", fill=True)
    y += 6
    hang = [("Họ tên người mua hàng", (d.ho_ten or "").upper()), ("Địa chỉ email", d.email or "—"), ("Số điện thoại", _che_sdt(d.lien_he) or "—")]
    p.rect(14, y, 182, 6 * len(hang) + 2)
    for a, b in hang:
        p.set_xy(18, y + 1)
        p.set_font("VN", "", 8.5)
        p.cell(55, 6, a)
        p.set_font("VN", "B", 8.5)
        p.cell(120, 6, b)
        y += 6
    y += 6
    # chi tiết
    p.set_xy(14, y)
    p.set_font("VN", "B", 8.5)
    p.cell(132, 6, "Thông tin chi tiết · Details", border=1, align="C", fill=True)
    p.cell(50, 6, "Thành tiền · Amount", border=1, align="C", fill=True)
    y += 6
    dong = [("Tên khách sạn", f"{k.ten if k else ''}{', ' + k.tinh_thanh if k and k.tinh_thanh else ''}", ""),
            ("Thời gian", f"{_dmy(d.vao)} – {_dmy(d.ra)} ({(d.ra - d.vao).days} đêm)", ""),
            ("Số lượng phòng", str(d.so_phong), "")]
    phu_thu = 0
    for x in sorted(d.dong or [], key=lambda x: min([kh["phong"] for kh in x.get("khach") or []] or [99])):
        nhan = ", ".join(f"P{kh['phong']}" for kh in sorted(x.get("khach") or [], key=lambda a: a["phong"])) or f"{x['so']} ×"
        pt = int(x.get("phu_thu") or 0)
        phu_thu += pt
        dong.append((f"{nhan} · {x.get('loai_phong', '')}"[:34], f"{x.get('goi', '')} · {x['so']} phòng", _vnd(int(x.get("tien") or 0) - pt)))
    if phu_thu:
        ct = "; ".join(c["nhan"] for x in d.dong or [] for c in (x.get("phu_thu_ct") or []) if c.get("tien"))
        dong.append(("Phụ thu trẻ em / giường phụ", ct[:60] or "theo chính sách khách sạn", _vnd(phu_thu)))
    y0 = y
    for a, b, c in dong:
        p.set_xy(16, y + 1)
        p.set_font("VN", "", 8.3)
        p.cell(52, 5.6, a)
        p.cell(78, 5.6, b)
        p.set_xy(146, y + 1)
        p.cell(48, 5.6, c, align="R")
        y += 5.8
    y += 2
    p.rect(14, y0, 132, y - y0)
    p.rect(146, y0, 50, y - y0)
    tong = [("Tổng tiền phòng · Room total", _vnd(d.tien_phong), False), ("Giảm giá / voucher", "− " + _vnd(d.giam_voucher) if d.giam_voucher else _vnd(0), False),
            ("TỔNG CỘNG TIỀN THANH TOÁN · TOTAL PAID", _vnd(d.tong), True),
            (f"Trong đó thuế GTGT {S.VAT_PT}% · incl. VAT {S.VAT_PT}%", _vnd(S.vat_trong(int(d.tong or 0))), False),
            ("Phương thức · Method", kenh or "—", False)]
    for a, b, dam in tong:
        p.set_xy(14, y)
        p.set_font("VN", "B" if dam else "", 8.5)
        p.cell(132, 6.5, a + "  ", border=1, align="R")
        p.cell(50, 6.5, b + "  ", border=1, align="R")
        y += 6.5
    y += 8
    p.set_xy(14, y)
    p.set_font("VN", "", 7.8)
    p.set_text_color(*XAM)
    p.multi_cell(120, 4.2, "Hóa đơn này được hệ thống VTOS chiết xuất tự động dành cho khách hàng.\nVietourist thu hộ tiền phòng cho khách sạn. "
                 "Chứng từ này không thay thế hóa đơn GTGT; cần hóa đơn GTGT, vui lòng gửi thông tin xuất hóa đơn qua «Đơn của tôi».", align="L")
    p.set_text_color(20, 38, 59)
    p.set_draw_color(154, 166, 178)
    p.set_dash_pattern(1, 1)
    p.rect(148, y, 48, 22)
    p.set_dash_pattern()
    p.set_xy(148, y + 5)
    p.set_font("VN", "B", 8)
    p.multi_cell(48, 4.4, "Xác nhận điện tử", align="C")
    p.set_x(148)
    p.set_font("VN", "", 7.5)
    p.multi_cell(48, 4, f"Mã tra cứu: {d.ma}", align="C")
    return bytes(p.output())


# ───────────────────────────────────────────────────────────────────────────────────── email
def email_html(db: Session, d: DonKsVtd) -> tuple[str, str, str]:
    """(tiêu đề, chữ thường, html) của email xác nhận song ngữ."""
    from app.services import khach_san_vtd as S
    k, ph = _ks(db, d), nguoi_phat_hanh(db)
    tra_luc, kenh = thanh_toan(db, d)
    ten_ks = k.ten if k else ""
    dv = don_vi(d)
    tieu_de = f"Xác nhận đặt phòng với Vietourist – Mã đặt phòng: {d.ma}"
    hang = "".join(f"<tr><td style='padding:8px;border-top:1px solid #edf1f5'><b>{_nhan_dv(v)}</b></td>"
                   f"<td style='padding:8px;border-top:1px solid #edf1f5'>{v['x'].get('loai_phong', '')} · {v['x'].get('goi', '')}</td>"
                   f"<td style='padding:8px;border-top:1px solid #edf1f5'>{_khach(v['kh'], v['x'])}</td></tr>" for v in dv)
    tien = "".join(f"<tr><td style='padding:3px 0'>{', '.join(f'P{kh['phong']}' for kh in sorted(x.get('khach') or [], key=lambda a: a['phong'])) or str(x['so']) + ' ×'} · "
                   f"{x.get('loai_phong', '')}</td><td style='padding:3px 0;text-align:right'>{_vnd(x.get('tien'))}</td></tr>"
                   for x in sorted(d.dong or [], key=lambda x: min([kh["phong"] for kh in x.get("khach") or []] or [99])))
    huy = "".join(f"<li><b>{_nhan_dv(v)}</b> — {_huy(v['x'])}</li>" for v in dv)
    o = "style='border-top:8px solid #f3f5f8;padding:18px 22px'"
    html = f"""<div style="background:#eef1f5;padding:16px;font-family:Arial,Helvetica,sans-serif;color:#14263b">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden">
<div style="background:#14538D;color:#fff;padding:14px 22px;font-weight:bold;font-size:20px;letter-spacing:.04em">VIETOURIST <span style="font-size:11px;font-weight:normal;letter-spacing:.2em">HOLDINGS</span></div>
<div style="padding:22px">
<h1 style="margin:0;font-size:21px">Đơn đặt phòng của quý khách đã được xác nhận!</h1>
<p style="margin:2px 0 12px;color:#4d5b6a;font-size:13px">Your booking is confirmed</p>
<p>Thân gửi <b>{d.ho_ten}</b>,</p>
<p>Mã đặt phòng của quý khách là <b>{d.ma}</b>. Vietourist đã nhận đủ <b>{_vnd(d.tong)}</b> và đã báo khách sạn. Phiếu xác nhận và hóa đơn đặt phòng (PDF) được đính kèm thư này; quý khách tải lại được trong «Đơn của tôi».</p>
</div>
<div {o}><b style="font-size:17px">{ten_ks}</b><br><span style="color:#4d5b6a">{(k.dia_chi if k else '') or (k.tinh_thanh if k else '')}</span></div>
<div {o}><table width="100%" style="font-size:14px"><tr>
<td style="background:#f5f9ff;padding:10px;border-radius:8px"><span style="color:#4d5b6a;font-size:12px">Nhận phòng · Check-in</span><br><b>{_dmy(d.vao)}</b> từ {k.gio_nhan if k else '14:00'}{' · đến ' + d.gio_den if d.gio_den else ''}</td>
<td width="10"></td>
<td style="background:#f5f9ff;padding:10px;border-radius:8px"><span style="color:#4d5b6a;font-size:12px">Trả phòng · Check-out</span><br><b>{_dmy(d.ra)}</b> trước {k.gio_tra if k else '12:00'}</td></tr></table></div>
<div {o}><b style="font-size:16px">Thông tin đơn đặt phòng · Booking details</b>
<p style="margin:8px 0">Đặt phòng: <b>{d.so_phong} phòng, {(d.ra - d.vao).days} đêm</b> · Khách chính: <b>{d.ho_ten}</b> · Số người ở: <b>{d.nguoi_lon} người lớn{f', {d.tre_em} trẻ em' if d.tre_em else ''}</b></p>
<table width="100%" style="font-size:13px;border:1px solid #dce3ea;border-collapse:collapse"><tr style="background:#f3f5f8;color:#4d5b6a"><td style="padding:8px">Phòng</td><td style="padding:8px">Loại phòng · Gói</td><td style="padding:8px">Khách</td></tr>{hang}</table>
<p style="color:#1d7a4a;font-weight:bold">✓ Đã xác nhận và thanh toán đơn đặt phòng</p></div>
<div {o}><b style="font-size:16px">Chi tiết thanh toán · Payment details</b>
<table width="100%" style="font-size:14px;margin-top:6px">{tien}
<tr><td style="border-top:1px solid #dce3ea;padding-top:8px"><b>Tổng tiền · Total</b></td><td style="border-top:1px solid #dce3ea;padding-top:8px;text-align:right"><b>{_vnd(d.tong)}</b></td></tr></table>
<p style="font-size:12px;color:#4d5b6a">Đã gồm {S.VAT_PT}% VAT ({_vnd(S.vat_trong(int(d.tong or 0)))}). Không thu thêm tại khách sạn, trừ dịch vụ quý khách tự dùng.<br>
Đã thanh toán{f' ngày {tra_luc:%d/%m/%Y}' if tra_luc else ''}{f' · {kenh}' if kenh else ''}.</p></div>
<div {o}><b style="font-size:16px">Chính sách hủy · Cancellation policy</b><ul style="padding-left:18px">{huy}</ul>
<p style="font-size:12px;color:#4d5b6a">Không đến nhận phòng được tính như hủy sau hạn. Tiền hoàn về tài khoản / thẻ đã dùng trong 3–7 ngày làm việc. Hủy hoặc xem số được hoàn: «Đơn của tôi» trên cổng Vietourist.</p></div>
<div {o} ><b>Lưu ý quan trọng</b><p style="font-size:12.5px;color:#4d5b6a;line-height:1.55">• Khi nhận phòng, xuất trình giấy tờ tùy thân có ảnh, đúng tên khách chính, và phiếu xác nhận.<br>
• Giá không gồm minibar, giặt ủi, điện thoại… khách sạn thu trực tiếp.<br>
• Vietourist không bao giờ gọi điện yêu cầu chuyển tiền ngoài trang đặt phòng. Gặp cuộc gọi lạ, báo hotline Vietourist {ph['hotline']}.</p></div>
<div style="background:#f3f5f8;padding:14px 22px;font-size:12px;color:#4d5b6a">Đây là thư tự động, vui lòng không trả lời. Vietourist đã báo {ten_ks} về đơn của quý khách.<br>
Gửi bởi: <b>{ph['ten']}</b> · MST {ph['mst']} · {ph['dia_chi']} · Hotline {ph['hotline']}</div>
</div></div>"""
    chu = (f"Thân gửi {d.ho_ten},\n\nĐơn đặt phòng {d.ma} tại {ten_ks} đã được xác nhận (Your booking is confirmed).\n"
           f"Nhận phòng {_dmy(d.vao)} · trả phòng {_dmy(d.ra)} · {d.so_phong} phòng\n"
           + "".join(f"{_nhan_dv(v)} · {v['x'].get('loai_phong', '')} · {v['x'].get('goi', '')} · {_khach(v['kh'], v['x'])} · {_huy(v['x'])}\n" for v in dv)
           + f"Đã thanh toán: {_vnd(d.tong)} (đã gồm {S.VAT_PT}% VAT)\n"
           + (f"Mã xác nhận của khách sạn: {d.ma_xac_nhan_ks}\n" if d.ma_xac_nhan_ks else "")
           + "Phiếu xác nhận và hóa đơn đặt phòng đính kèm thư này; tải lại trong «Đơn của tôi».\n\n"
           + f"{ph['ten']} · Hotline {ph['hotline']}")
    return tieu_de, chu, html


def dinh_kem(db: Session, d: DonKsVtd) -> list[tuple[str, bytes]]:
    """Hai PDF đính kèm email — thiếu phông chữ thì gửi email không đính kèm (khách vẫn tải trong «Đơn của tôi»)."""
    ra = []
    for ten, f in ((f"Phieu-xac-nhan-{d.ma}.pdf", pdf_phieu), (f"Hoa-don-{d.ma}.pdf", pdf_hoa_don)):
        try:
            ra.append((ten, f(db, d)))
        except LoiPhieu:
            continue
    return ra
