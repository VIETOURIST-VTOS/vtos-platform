"""KH-1 · Cổng khách hàng VTD — trang chủ, tour, gửi yêu cầu, đơn của tôi, hồ sơ.

Chủ tịch duyệt 26/10/2026 (bộ giao diện v3.2, màn KH01–KH04, KH16, KH23):
  · Tour hiện cho khách = tour ĐÃ DUYỆT, CÒN CHỖ, CHƯA KHỞI HÀNH. Chỉ đưa ra giá bán / khách và
    thông tin lịch — KHÔNG BAO GIỜ đưa giá vốn, chi phí, biên lãi, người điều hành.
  · «Gửi yêu cầu» = một lead kênh «Đặt tour web» cho Sales liên hệ. KHÔNG giữ chỗ, KHÔNG thu tiền,
    KHÔNG hứa giá cuối.
  · «Đơn của tôi» = booking có SĐT hoặc email TRÙNG với liên hệ khách vừa xác thực bằng mã một lần.
    Chỉ liên hệ đã xác thực mới dùng để ghép — không ghép theo thông tin khách tự gõ thêm.
  · Thanh toán hiển thị TÁCH khỏi trạng thái phục vụ, và chỉ phiếu thu KẾ TOÁN ĐÃ XÁC NHẬN mới là
    «đã thu»; phiếu robot vừa khớp là «đang xác nhận tiền».
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.core import Tour, Booking
from app.models.payments import Receipt
from app.models.crm import Lead
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.cong_khach import YeuCauKhach, LOAI_YEU_CAU
from app.services.zalo import norm_phone

KENH_LEAD = "Đặt tour web"
TOUR_DONG = {"ket_thuc", "da_dong_so", "kt_xac_nhan", "khoa"}
KHONG_BAN = ("non_package", "thue_xe")
GIO_CHOT_NGAY = 7
YEU_CAU_TOI_DA_NGAY = 10
SO_THICH = ("Biển & nghỉ dưỡng", "Văn hóa & di sản", "Thiên nhiên & khám phá", "Ẩm thực", "Gia đình & trẻ em")
TRANG_THAI_LEAD = {"moi": "Đã gửi – chờ Sales liên hệ", "dang_cham_soc": "Sales đang tư vấn",
                   "chot": "Đã chốt – xem trong đơn", "mat": "Đã đóng yêu cầu"}


class LoiKhach(ValueError):
    pass


def _hom_nay() -> date:
    return date.today()


def la_khach(tk: TaiKhoanNgoai) -> None:
    if tk.loai != "khach_hang":
        raise LoiKhach("Chức năng này dành cho tài khoản khách hàng")
    if tk.trang_thai == "khoa":
        raise LoiKhach("Tài khoản đã bị khoá")


def la_khach_hoac_co_dong(tk: TaiKhoanNgoai) -> None:
    """CD-2 (Chủ tịch duyệt 28/10/2026): ưu đãi cổ đông — cổ đông ĐÃ XÁC MINH xem tour, nhà hàng và gửi yêu cầu
    theo đúng luồng của khách hàng. Đơn, điểm, hạng thành viên… vẫn chỉ của khách hàng."""
    if tk.loai == "co_dong":
        if tk.trang_thai != "hoat_dong":
            raise LoiKhach("Tài khoản cổ đông chưa được IR xác minh")
        return
    la_khach(tk)


def _so_dem(t: Tour) -> tuple[int, int]:
    n = t.days or ((t.end_date - t.start_date).days + 1 if t.start_date and t.end_date else 1)
    return n, max(n - 1, 0)


def _da_ban(db: Session, tour_ids: list[int]) -> dict[int, int]:
    if not tour_ids:
        return {}
    q = (select(Booking.tour_id, func.coalesce(func.sum(Booking.pax), 0))
         .where(Booking.tour_id.in_(tour_ids), Booking.cancelled.is_(False)).group_by(Booking.tour_id))
    return {tid: int(n) for tid, n in db.execute(q).all()}


def _con_cho(t: Tour, da_ban: int) -> int:
    suc_chua = t.seats_open or t.planned_pax or 0
    return max(suc_chua - da_ban, 0)


def _tour_out(t: Tour, con: int, hom_nay: date) -> dict:
    """CHỈ thông tin bán. Danh sách trường đóng — thêm trường mới phải sửa ở đây, có chủ ý."""
    ngay, dem = _so_dem(t)
    gia = int(t.price_per_pax or 0)
    km = int(t.price_promo or 0)
    co_km = 0 < km < gia
    gio_chot = (t.start_date - hom_nay).days <= GIO_CHOT_NGAY
    return {
        "id": t.id, "ma": t.code, "ten": t.name, "khoi_hanh": t.start_date.isoformat(), "ket_thuc": t.end_date.isoformat(),
        "ngay": ngay, "dem": dem, "thoi_gian": f"{ngay} ngày {dem} đêm" if dem else f"{ngay} ngày",
        "noi_khoi_hanh": t.departure_point or "", "phuong_tien": t.transport or "",
        "nuoc_ngoai": t.tour_type in ("le_nuoc_ngoai", "doan_nuoc_ngoai") or bool(t.country and t.country.lower() not in ("vn", "việt nam", "viet nam")),
        "gia": km if co_km else gia, "gia_goc": gia if co_km else None, "gia_tre_em": int(t.price_chd) if t.price_chd else None,
        "nhan": "Tour khuyến mại" if co_km else ("Tour giờ chót" if gio_chot else "Tour du lịch"),
        "nhom": "promo" if co_km else ("last" if gio_chot else "tour"),
        "con_cho": con > 0, "it_cho": 0 < con <= 5,
    }


def tours(db: Session, q: str = "", tu_ngay: date | None = None, noi: str = "", ngan_sach: int = 0,
          nhom: str = "", gioi_han: int = 60) -> list[dict]:
    hom_nay = _hom_nay()
    cau = (select(Tour).where(Tour.status == "da_duyet", Tour.start_date > hom_nay,
                              Tour.price_per_pax.is_not(None), Tour.price_per_pax > 0,
                              Tour.tour_type.not_in(KHONG_BAN)).order_by(Tour.start_date, Tour.id))
    if tu_ngay:
        cau = cau.where(Tour.start_date >= tu_ngay)
    if q.strip():
        k = f"%{q.strip()}%"
        cau = cau.where(or_(Tour.name.ilike(k), Tour.code.ilike(k), Tour.country.ilike(k)))
    if noi.strip():
        cau = cau.where(Tour.departure_point == noi.strip())
    ds = db.execute(cau).scalars().all()
    ban = _da_ban(db, [t.id for t in ds])
    ra = []
    for t in ds:
        con = _con_cho(t, ban.get(t.id, 0))
        if con <= 0:
            continue
        o = _tour_out(t, con, hom_nay)
        if ngan_sach and o["gia"] > ngan_sach:
            continue
        if nhom in ("promo", "last") and o["nhom"] != nhom:
            continue
        ra.append(o)
        if len(ra) >= gioi_han:
            break
    return ra


def noi_khoi_hanh(db: Session) -> list[str]:
    hom_nay = _hom_nay()
    ds = db.execute(select(Tour.departure_point).where(Tour.status == "da_duyet", Tour.start_date > hom_nay,
                                                       Tour.departure_point != "").distinct()).scalars().all()
    return sorted(x for x in ds if x)


def tour(db: Session, tour_id: int) -> dict:
    t = db.get(Tour, tour_id)
    hom_nay = _hom_nay()
    if t is None or t.status != "da_duyet" or t.start_date <= hom_nay or not t.price_per_pax or t.tour_type in KHONG_BAN:
        raise LoiKhach("Tour này không còn mở bán trên cổng")
    con = _con_cho(t, _da_ban(db, [t.id]).get(t.id, 0))
    if con <= 0:
        raise LoiKhach("Tour này đã hết chỗ — gửi yêu cầu tour đoàn để Sales tìm lịch khác")
    return _tour_out(t, con, hom_nay)


# ── yêu cầu ─────────────────────────────────────────────────────────────────────────────────────

def gui_yeu_cau(db: Session, tk: TaiKhoanNgoai, loai: str, tour_id: int | None, so_khach: int, dien_thoai: str,
                ngay_mong_muon: date | None, ghi_chu: str, dong_y: bool, now: datetime | None = None,
                nha_hang: dict | None = None) -> YeuCauKhach:
    la_khach_hoac_co_dong(tk)
    now = now or datetime.now()
    if loai not in LOAI_YEU_CAU:
        raise LoiKhach("Loại yêu cầu không hợp lệ")
    if not dong_y:
        raise LoiKhach("Đánh dấu ô xác nhận: gửi yêu cầu chưa giữ chỗ và chưa thu tiền")
    nh = nha_hang or {}
    if loai == "nha_hang":   # KH-2: số khách = người lớn + trẻ em, máy tự cộng
        so_khach = int(nh.get("nguoi_lon") or 0) + int(nh.get("tre_em") or 0)
    if not 1 <= int(so_khach or 0) <= 500:
        raise LoiKhach("Số khách từ 1 đến 500")
    sdt = norm_phone(dien_thoai or tk.dien_thoai)
    if len(sdt) != 10 or not sdt.startswith("0"):
        raise LoiKhach("Ghi số điện thoại để Sales gọi lại (10 số)")
    trong_ngay = db.execute(select(func.count(YeuCauKhach.id)).where(
        YeuCauKhach.tai_khoan_id == tk.id, YeuCauKhach.tao_luc >= now - timedelta(days=1))).scalar_one()
    if trong_ngay >= YEU_CAU_TOI_DA_NGAY:
        raise LoiKhach("Bạn đã gửi nhiều yêu cầu trong 24 giờ — Sales sẽ liên hệ, vui lòng chờ")
    ten_tour = ""
    them = {}
    if loai == "nha_hang":
        from app.services import nha_hang as NH
        try:
            o, td, tam = NH.kiem_dat_ban(db, int(nh.get("nha_hang_id") or 0), int(nh.get("thuc_don_id") or 0), ngay_mong_muon,
                                         str(nh.get("gio") or ""), int(nh.get("nguoi_lon") or 0), int(nh.get("tre_em") or 0), now.date())
        except NH.LoiNhaHang as ex:
            raise LoiKhach(str(ex))
        ten_tour = f"{o['ten']} · {td['ten']} · {ngay_mong_muon:%d/%m/%Y} {nh['gio']} · {nh.get('nguoi_lon')} NL + {nh.get('tre_em') or 0} TE"
        them = {"nha_hang_id": o["id"], "thuc_don_id": td["id"], "gio_den": nh["gio"], "tre_em": int(nh.get("tre_em") or 0), "tam_tinh": tam}
    elif loai == "tour":
        o = tour(db, int(tour_id or 0))
        ten_tour = f"{o['ma']} · {o['ten']} · {date.fromisoformat(o['khoi_hanh']):%d/%m/%Y}"
    else:
        if ngay_mong_muon is not None and ngay_mong_muon <= now.date():
            raise LoiKhach("Ngày mong muốn phải sau hôm nay")
        ten_tour = "Tour đoàn theo yêu cầu"
    ghi = (ghi_chu or "").strip()[:1000]
    # Lead đi đúng cửa sẵn có của Kinh doanh (gộp theo SĐT × tháng × kênh) — ghi chú NỐI THÊM,
    # không đè lần khách gửi trước trong tháng.
    from app.services.leads import upsert_lead
    lead, _moi = upsert_lead(db, "cong_khach", {"phone": sdt, "name": tk.ho_ten or "", "channel": KENH_LEAD,
                                                "received_at": now.isoformat(), "interest": ten_tour[:200]})
    nguon = "Cổng cổ đông" if tk.loai == "co_dong" else "Cổng khách hàng"
    dong = (f"[{nguon} {now:%d/%m %H:%M}] {LOAI_YEU_CAU[loai]}: {ten_tour} · {so_khach} khách"
            + (f" · ngày mong muốn {ngay_mong_muon:%d/%m/%Y}" if ngay_mong_muon and loai != "nha_hang" else "")
            + (f" · tạm tính {them['tam_tinh']:,} đ".replace(",", ".") if them else "") + (f" · {ghi}" if ghi else ""))
    cu = (lead.note or "").strip()
    lead.note = ((cu + "\n") if cu else "") + dong
    lead.note = lead.note[-2000:]
    ten_tour = ten_tour[:200]
    yc = YeuCauKhach(tai_khoan_id=tk.id, loai=loai, tour_id=tour_id if loai == "tour" else None, ten_tour=ten_tour,
                     so_khach=int(so_khach), ngay_mong_muon=ngay_mong_muon, dien_thoai=sdt, ghi_chu=ghi,
                     lead_id=lead.id, tao_luc=now, **them)
    db.add(yc)
    db.commit(); db.refresh(yc)
    return yc


def yeu_cau_cua(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    ds = db.execute(select(YeuCauKhach).where(YeuCauKhach.tai_khoan_id == tk.id)
                    .order_by(YeuCauKhach.tao_luc.desc()).limit(50)).scalars().all()
    leads = {l.id: l for l in db.execute(select(Lead).where(Lead.id.in_([y.lead_id for y in ds if y.lead_id]))).scalars()} if ds else {}
    ra = []
    for y in ds:
        l = leads.get(y.lead_id)
        tt = l.status if l else "moi"
        ra.append({"id": y.id, "loai": LOAI_YEU_CAU.get(y.loai, y.loai), "noi_dung": y.ten_tour, "so_khach": y.so_khach,
                   "gui_luc": y.tao_luc.isoformat(timespec="minutes"), "trang_thai": TRANG_THAI_LEAD.get(tt, "Đã gửi")})
    return ra


# ── đơn của tôi ─────────────────────────────────────────────────────────────────────────────────

def _booking_cua(db: Session, tk: TaiKhoanNgoai) -> list[Booking]:
    dk = []
    if tk.dien_thoai:
        # Chín số cuối, cho phép dấu cách / chấm / gạch xen giữa («+84 901 234 567»).
        dk.append(Booking.customer_phone.like("%" + "%".join(tk.dien_thoai[-9:])))
    if tk.email:
        dk.append(func.lower(Booking.customer_email) == tk.email.lower())
    if not dk:
        return []
    ds = db.execute(select(Booking).where(or_(*dk)).order_by(Booking.created_at.desc())).scalars().all()
    # Lọc lần hai bằng số đã chuẩn hoá: LIKE theo đuôi chỉ để thu hẹp, không phải để quyết định.
    return [b for b in ds if (tk.dien_thoai and norm_phone(b.customer_phone) == tk.dien_thoai)
            or (tk.email and (b.customer_email or "").strip().lower() == tk.email.lower())]


def _phuc_vu(b: Booking, t: Tour | None, hom_nay: date) -> tuple[str, str]:
    if b.cancelled:
        return "Đã hủy", "bad"
    if t is None:
        return "Đang xác nhận", "neutral"
    if t.status == "huy":
        return "Lịch thay đổi – Sales sẽ liên hệ", "warn"
    if t.status in TOUR_DONG or (t.end_date and t.end_date < hom_nay):
        return "Đã hoàn tất", "good"
    if t.start_date and t.start_date <= hom_nay <= t.end_date:
        return "Đang đi", "good"
    if t.status == "da_duyet":
        return "Đã xác nhận", "neutral"
    return "Đang xác nhận", "neutral"


def _tien(db: Session, b: Booking) -> dict:
    gia_tri = int(round(float(b.amount or 0) - float(b.discount or 0)))
    rows = db.execute(select(Receipt.status, func.coalesce(func.sum(Receipt.amount), 0)).where(
        Receipt.booking_id == b.id, Receipt.status != "huy").group_by(Receipt.status)).all()
    da_thu = int(round(sum(float(v) for s, v in rows if s == "ke_toan_xac_nhan")))
    dang_xn = int(round(sum(float(v) for s, v in rows if s != "ke_toan_xac_nhan")))
    if gia_tri > 0 and da_thu >= gia_tri:
        nhan = "Đã thu đủ"
    elif da_thu > 0:
        nhan = "Đã thu một phần"
    elif dang_xn > 0:
        nhan = "Đang xác nhận tiền"
    else:
        nhan = "Chưa thanh toán"
    return {"gia_tri": gia_tri, "da_thu": da_thu, "dang_xac_nhan": dang_xn, "con_lai": max(gia_tri - da_thu, 0), "thanh_toan": nhan}


def don_cua_toi(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    la_khach(tk)
    hom_nay = _hom_nay()
    ra = []
    for b in _booking_cua(db, tk):
        t = db.get(Tour, b.tour_id) if b.tour_id else None
        pv, muc = _phuc_vu(b, t, hom_nay)
        ra.append({"ma": b.code, "ten": t.name if t else (b.services_note or "Dịch vụ"),
                   "khoi_hanh": t.start_date.isoformat() if t else (b.service_date.isoformat() if b.service_date else None),
                   "ket_thuc": t.end_date.isoformat() if t else None, "so_khach": b.pax,
                   "phuc_vu": pv, "muc": muc, "sap_di": bool(t and not b.cancelled and t.start_date > hom_nay and t.status != "huy"),
                   **_tien(db, b)})
    return ra


def don(db: Session, tk: TaiKhoanNgoai, ma: str) -> dict:
    d = next((x for x in don_cua_toi(db, tk) if x["ma"] == ma), None)
    if d is None:
        # Cùng một câu cho «không có» và «không phải của bạn» — cổng không thành máy dò mã booking.
        raise LoiKhach("Không tìm thấy đơn này trong tài khoản của bạn")
    return d


def trang_chu(db: Session, tk: TaiKhoanNgoai) -> dict:
    la_khach(tk)
    ds = don_cua_toi(db, tk)
    sap = sorted([d for d in ds if d["sap_di"]], key=lambda d: d["khoi_hanh"] or "")
    return {"sap_di": len(sap), "chuyen_toi": sap[0] if sap else None, "tour": tours(db, gioi_han=3),
            "yeu_cau_dang_cho": sum(1 for y in yeu_cau_cua(db, tk) if y["trang_thai"].startswith("Đã gửi"))}


def cap_nhat_ho_so(db: Session, tk: TaiKhoanNgoai, ho_ten: str | None, so_thich: str | None, nhan_tin: bool | None) -> TaiKhoanNgoai:
    la_khach(tk)
    if ho_ten is not None:
        tk.ho_ten = ho_ten.strip()[:160]
    if so_thich is not None:
        if so_thich and so_thich not in SO_THICH:
            raise LoiKhach("Sở thích không hợp lệ")
        tk.so_thich = so_thich
    if nhan_tin is not None:
        tk.nhan_tin_quang_cao = bool(nhan_tin)
    db.commit(); db.refresh(tk)
    return tk


# ── KH-2 · thanh toán QR ────────────────────────────────────────────────────────────────────────

def _so(s: str) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def tai_khoan_qr(db: Session):
    """TK nhận tiền QR: tham số `cong_qr_tai_khoan` (số TK) khớp một TK ĐANG DÙNG trong danh mục ngân hàng.
    Không khớp thì trả None — đóng QR, không đoán tài khoản."""
    from app.models.banks import BankAccount
    from app.services import rules as R
    so = _so(R.get_param_text(db, "cong_qr_tai_khoan"))
    if not so:
        return None
    for ba in db.execute(select(BankAccount).where(BankAccount.active.is_(True))).scalars():
        if _so(ba.account_number) == so:
            return ba
    return None


def qr_don(db: Session, tk: TaiKhoanNgoai, ma: str, muc: str = "") -> dict:
    """Mã QR chuyển khoản cho một đơn CỦA KHÁCH. `muc`: «coc» (đủ % cọc) hoặc «du» (toàn bộ còn lại).

    Số tiền do MÁY tính từ booking và phiếu thu (cùng phép cộng robot dùng để khớp) — không nhận số
    tiền từ trình duyệt. Tài khoản nhận là tham số `cong_qr_tai_khoan` Chủ tịch đã ký; chưa ký thì đóng.
    """
    import math
    from app.services.payments import paid_amount
    from app.services import vietqr as Q
    la_khach(tk)
    b = next((x for x in _booking_cua(db, tk) if x.code == ma), None)
    if b is None:
        raise LoiKhach("Không tìm thấy đơn này trong tài khoản của bạn")
    if b.cancelled:
        raise LoiKhach("Đơn đã hủy — không thanh toán")
    gia_tri = int(round(float(b.amount or 0) - float(b.discount or 0)))
    da_nop = int(round(float(paid_amount(db, b.id))))
    con = gia_tri - da_nop
    if gia_tri <= 0 or con <= 0:
        raise LoiKhach("Đơn đã thanh toán đủ hoặc chưa có giá trị — không cần chuyển thêm")
    coc = int(math.ceil(gia_tri * float(b.deposit_pct or 0) / 100)) - da_nop
    coc = coc if 0 < coc < con else 0
    muc = muc if muc in ("coc", "du") else ("coc" if coc else "du")
    if muc == "coc" and not coc:
        raise LoiKhach("Đơn đã đủ tiền cọc — chọn thanh toán toàn bộ phần còn lại")
    so_tien = coc if muc == "coc" else con
    ba = tai_khoan_qr(db)
    if ba is None or not ba.account_number:
        raise LoiKhach("Thanh toán QR chưa mở — vui lòng liên hệ Sales phụ trách để nhận thông tin chuyển khoản")
    bin_ = Q.bin_cua(ba.bank_name)
    if bin_ is None:
        raise LoiKhach("Thanh toán QR chưa mở cho ngân hàng này — vui lòng liên hệ Sales phụ trách")
    return {"ma": b.code, "muc": muc, "so_tien": so_tien, "coc": coc, "con_lai": con, "da_nop": da_nop,
            "payload": Q.payload(bin_, ba.account_number, so_tien, b.code), "noi_dung": Q.noi_dung_sach(b.code),
            "ngan_hang": ba.bank_name, "so_tk": ba.account_number, "chu_tk": ba.account_name,
            "tu_khop": muc == "du"}
