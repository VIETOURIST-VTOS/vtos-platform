"""KS-16h · Nguồn đơn CTV — Chủ tịch duyệt bản xem thử 31/10/2026 (đề xuất v3 mục 7, «máy tự gắn», «máy tự xử»).

LUẬT
  · Giữ nguồn 30 ngày theo SĐT khách:
      – CTV gửi «Giới thiệu khách» (khách đã đồng ý chuyển liên hệ) → nguồn ĐƯỢC BẢO VỆ;
      – khách mở link kh.vietourist.vn/CTV-xxxx rồi đăng nhập / gửi yêu cầu trên cổng khách → nguồn LINK
        (last-click): chỉ ghi khi khách chưa có nguồn được bảo vệ; link mới hơn của CTV khác THAY link cũ.
  · Trùng nguồn, máy tự xử theo luật:
      – đang có nguồn được bảo vệ của CTV khác → CTV đến sau «không giữ được»;
      – Sales đã liên hệ khách (Lead có người phụ trách, `last_contact_at`) trong 7 ngày TRƯỚC lúc CTV gửi →
        Sales được ưu tiên, CTV «không giữ được»;
      – SĐT khách trùng SĐT của CTV → không tự giới thiệu.
  · Booking tạo trong thời hạn giữ của khách (cùng SĐT) mà chưa gắn đối tác → máy gắn đối tác + `nguon_don_id`
    lúc tạo. Sales chỉ xem, không sửa; đổi nguồn chỉ qua vụ việc (khiếu nại) do Trưởng KD / Kế toán xử.
  · Mọi dòng giữ lại kèm trạng thái và lý do — không xóa.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models.core import Booking, User
from app.models.crm import Lead
from app.models.doi_tac_ban_hang import DoiTacBanHang
from app.models.nguon_doi_soat import NguonDon, VuViecDoiTac, LOAI_NGUON, TRANG_THAI_NGUON, TRANG_THAI_VV
from app.services.zalo import norm_phone

GIU_NGAY = 30
SALES_UU_TIEN_NGAY = 7
VV_NGAY_LAM_VIEC = 5
VAI_XU_LY = ("gd_kd", "ketoan", "chutich", "tgd")          # Trưởng Kinh doanh (GĐ KD) · Kế toán · toàn quyền


class LoiNguon(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def ma_ctv(dt: DoiTacBanHang) -> str:
    return f"CTV-{dt.id:04d}"


def doi_tac_tu_ma(db: Session, ma: str) -> DoiTacBanHang | None:
    m = (ma or "").strip().upper()
    if not m.startswith("CTV-") or not m[4:].isdigit():
        return None
    dt = db.get(DoiTacBanHang, int(m[4:]))
    return dt if dt is not None and dt.loai == "ctv_ban_hang" and dt.dang_hieu_luc(date.today()) else None


def cong_ngay_lam_viec(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _sdt(s: str) -> str | None:
    p = norm_phone(s or "")
    return p if len(p) == 10 and p.startswith("0") else None


def _dang_giu(db: Session, sdt: str, now: datetime) -> list[NguonDon]:
    return db.execute(select(NguonDon).where(NguonDon.khach_sdt == sdt, NguonDon.trang_thai == "giu",
                                             NguonDon.tu <= now, NguonDon.den >= now).order_by(NguonDon.id)).scalars().all()


def _sales_dang_cham(db: Session, sdt: str, now: datetime) -> bool:
    return db.execute(select(Lead.id).where(Lead.phone == sdt, Lead.sales_id.is_not(None), Lead.last_contact_at.is_not(None),
                                            Lead.last_contact_at >= now - timedelta(days=SALES_UU_TIEN_NGAY),
                                            Lead.last_contact_at <= now)).first() is not None


def ghi_nguon(db: Session, dt: DoiTacBanHang, sdt_khach: str, loai: str, now: datetime | None = None, ten: str = "",
              yeu_cau_id: int | None = None) -> NguonDon | None:
    """Ghi một lần giữ nguồn theo luật trên. Trả dòng vừa ghi (kể cả «không giữ được») — None nếu SĐT sai hoặc
    chính CTV ấy đang giữ nguồn khách này rồi. Không commit."""
    now = now or datetime.now()
    sdt = _sdt(sdt_khach)
    if sdt is None:
        return None
    dang = _dang_giu(db, sdt, now)
    if any(n.doi_tac_id == dt.id for n in dang):
        return None
    n = NguonDon(khach_sdt=sdt, khach_ten=(ten or "")[:120], doi_tac_id=dt.id, loai=loai, tu=now,
                 den=now + timedelta(days=GIU_NGAY), yeu_cau_id=yeu_cau_id, luc=now)
    if _sdt(dt.dien_thoai) == sdt:
        n.trang_thai, n.ly_do = "thua", "Không tự giới thiệu: SĐT khách trùng SĐT của CTV"
    elif any(x.loai == "gioi_thieu" for x in dang):
        n.trang_thai, n.ly_do = "thua", "Khách đang được CTV khác giữ nguồn (giới thiệu trước)"
    elif _sales_dang_cham(db, sdt, now):
        n.trang_thai, n.ly_do = "thua", f"Sales đã liên hệ khách trong {SALES_UU_TIEN_NGAY} ngày trước — Sales được ưu tiên"
    else:
        for x in dang:            # còn lại chỉ có thể là nguồn link
            if loai == "link" or loai == "gioi_thieu":
                x.trang_thai, x.ly_do = "thay", f"{LOAI_NGUON[loai]} của CTV khác lúc {now:%d/%m/%Y %H:%M}"
    db.add(n)
    db.flush()
    return n


def nguon_hien_hanh(db: Session, sdt_khach: str, now: datetime | None = None) -> NguonDon | None:
    sdt = _sdt(sdt_khach)
    if sdt is None:
        return None
    dang = _dang_giu(db, sdt, now or datetime.now())
    return dang[-1] if dang else None


def gan_booking(db: Session, b: Booking, now: datetime | None = None) -> bool:
    """Gắn nguồn CTV cho booking mới (chưa gắn đối tác) nếu khách đang được giữ nguồn."""
    if b.doi_tac_id or b.nguon_don_id or b.cancelled:
        return False
    n = nguon_hien_hanh(db, b.customer_phone or "", now or b.created_at or datetime.now())
    if n is None:
        return False
    b.doi_tac_id, b.nguon_don_id = n.doi_tac_id, n.id
    return True


@event.listens_for(Session, "before_flush")
def _gan_luc_tao(session, flush_context, instances):
    for o in list(session.new):
        if isinstance(o, Booking):
            try:
                with session.no_autoflush:
                    gan_booking(session, o)
            except Exception:       # gắn nguồn không bao giờ được làm hỏng việc tạo booking
                pass


def nguon_cua_booking(db: Session, b: Booking) -> dict | None:
    if not b.nguon_don_id:
        return None
    n = db.get(NguonDon, b.nguon_don_id)
    dt = db.get(DoiTacBanHang, n.doi_tac_id) if n else None
    if n is None or dt is None:
        return None
    return {"doi_tac": dt.ten, "ma_ctv": ma_ctv(dt), "loai": LOAI_NGUON.get(n.loai, n.loai), "tu": n.tu.isoformat(timespec="minutes"),
            "den": n.den.date().isoformat(), "chinh_sach": n.chinh_sach}


# ── danh sách cho CTV ───────────────────────────────────────────────────────────────────────────

def ds_cua_ctv(db: Session, dt: DoiTacBanHang, now: datetime | None = None) -> list[dict]:
    from app.services.cong_ngoai import che
    now = now or datetime.now()
    ra = []
    for n in db.execute(select(NguonDon).where(NguonDon.doi_tac_id == dt.id).order_by(NguonDon.id.desc()).limit(100)).scalars():
        bks = db.execute(select(Booking.code).where(Booking.nguon_don_id == n.id)).scalars().all()
        tt = n.trang_thai
        if tt == "giu" and n.den < now:
            tt = "het_han"
        ra.append({"khach": f"{n.khach_ten} · {che(n.khach_sdt)}".strip(" ·"), "loai": LOAI_NGUON.get(n.loai, n.loai),
                   "tu": n.tu.isoformat(timespec="minutes"), "den": n.den.date().isoformat() if n.trang_thai == "giu" else None,
                   "trang_thai": tt, "trang_thai_ten": TRANG_THAI_NGUON.get(tt, tt), "ly_do": n.ly_do, "booking": list(bks)})
    return ra


# ── vụ việc ─────────────────────────────────────────────────────────────────────────────────────

def _ma_vv(db: Session, now: datetime) -> str:
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, VuViecDoiTac, f"VV-{now:%y%m}-", 3, cot="ma")


def mo_vu_viec(db: Session, dt: DoiTacBanHang, loai: str, noi_dung: str, booking_ma: str = "", khach_sdt: str = "",
               dong_id: int | None = None, now: datetime | None = None) -> VuViecDoiTac:
    now = now or datetime.now()
    nd = (noi_dung or "").strip()
    if len(nd) < 5:
        raise LoiNguon("Ghi rõ nội dung khiếu nại")
    if loai == "nguon" and not ((booking_ma or "").strip() or _sdt(khach_sdt)):
        raise LoiNguon("Ghi mã booking hoặc SĐT khách")
    v = VuViecDoiTac(ma=_ma_vv(db, now), doi_tac_id=dt.id, loai=loai, booking_ma=(booking_ma or "").strip()[:30],
                     khach_sdt=_sdt(khach_sdt) or "", dong_doi_soat_id=dong_id, noi_dung=nd[:2000],
                     han=cong_ngay_lam_viec(now.date(), VV_NGAY_LAM_VIEC), tao_luc=now)
    db.add(v); db.flush()
    from app.services import rules as R
    R.audit(db, f"doi_tac:{dt.id}", "doi_tac", "mo_vu_viec", f"vu_viec:{v.ma}", after={"loai": loai, "booking": v.booking_ma})
    return v


def _vv_out(db: Session, v: VuViecDoiTac, hn: date) -> dict:
    dt = db.get(DoiTacBanHang, v.doi_tac_id)
    return {"id": v.id, "ma": v.ma, "doi_tac": dt.ten if dt else "", "loai": "Nguồn đơn" if v.loai == "nguon" else "Đối soát",
            "booking": v.booking_ma, "noi_dung": v.noi_dung, "trang_thai": v.trang_thai,
            "trang_thai_ten": TRANG_THAI_VV.get(v.trang_thai, v.trang_thai), "han": v.han.isoformat(),
            "qua_han": v.trang_thai == "mo" and hn > v.han, "ket_qua": v.ket_qua, "xu_ly_boi": v.xu_ly_boi,
            "tao_luc": v.tao_luc.isoformat(timespec="minutes")}


def ds_vu_viec(db: Session, doi_tac_id: int | None = None, hom_nay: date | None = None) -> list[dict]:
    hn = hom_nay or date.today()
    cau = select(VuViecDoiTac).order_by(VuViecDoiTac.trang_thai != "mo", VuViecDoiTac.han, VuViecDoiTac.id)
    if doi_tac_id is not None:
        cau = cau.where(VuViecDoiTac.doi_tac_id == doi_tac_id)
    return [_vv_out(db, v, hn) for v in db.execute(cau.limit(200)).scalars()]


def xu_ly_vu_viec(db: Session, u: User, vid: int, chap_nhan: bool, ket_qua: str, now: datetime | None = None) -> VuViecDoiTac:
    """Trưởng KD / Kế toán xử lý. Vụ việc NGUỒN chấp nhận có mã booking → booking chuyển sang đối tác khiếu nại
    (ghi nhật ký). Vụ việc ĐỐI SOÁT chấp nhận → Kế toán tính lại kỳ gốc như mọi điều chỉnh."""
    from app.services.vai_ke_thua import vai_va_cha
    from app.services import rules as R
    if not set(vai_va_cha(u.role)) & set(VAI_XU_LY):
        raise LoiNguon("Chỉ Trưởng Kinh doanh / Kế toán xử lý vụ việc", 403)
    v = db.get(VuViecDoiTac, vid)
    if v is None:
        raise LoiNguon("Không có vụ việc này", 404)
    if v.trang_thai != "mo":
        raise LoiNguon("Vụ việc đã xử lý")
    kq = (ket_qua or "").strip()
    if len(kq) < 5:
        raise LoiNguon("Ghi kết quả / lý do xử lý")
    now = now or datetime.now()
    truoc = {}
    if chap_nhan and v.loai == "nguon" and v.booking_ma:
        b = db.execute(select(Booking).where(Booking.code == v.booking_ma)).scalars().first()
        if b is None:
            raise LoiNguon("Không có booking ghi trong vụ việc")
        truoc = {"doi_tac_id": b.doi_tac_id, "nguon_don_id": b.nguon_don_id}
        n = NguonDon(khach_sdt=_sdt(b.customer_phone) or "", khach_ten=b.customer_name or "", doi_tac_id=v.doi_tac_id,
                     loai="gioi_thieu", tu=now, den=now, trang_thai="het_han", ly_do=f"Gắn theo vụ việc {v.ma}", luc=now)
        db.add(n); db.flush()
        if b.nguon_don_id:
            cu = db.get(NguonDon, b.nguon_don_id)
            if cu is not None and cu.doi_tac_id != v.doi_tac_id:
                cu.trang_thai, cu.ly_do = "huy", f"Vụ việc {v.ma}: nguồn chuyển sang đối tác khiếu nại"
        b.doi_tac_id, b.nguon_don_id = v.doi_tac_id, n.id
    v.trang_thai, v.ket_qua, v.xu_ly_boi, v.xu_ly_luc = ("chap_nhan" if chap_nhan else "bac"), kq[:500], u.username, now
    R.audit(db, u.username, u.role, "xu_ly_vu_viec", f"vu_viec:{v.ma}", before=truoc or None,
            after={"ket_qua": v.trang_thai, "ly_do": kq[:200], "booking": v.booking_ma})
    db.commit(); db.refresh(v)
    return v
