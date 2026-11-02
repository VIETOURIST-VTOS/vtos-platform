"""KS-16h · Đối soát hoa hồng với đối tác — Chủ tịch duyệt bản xem thử 31/10/2026 (đề xuất v3 mục 6, «đủ vòng trên cổng»).

LỊCH (áp cho kỳ tính D06 theo v3 — tham số `d06_v3_tu`)
  · Ngày 1–5 tháng sau: Kế toán bấm «Lập & gửi bảng đối soát» cho từng đối tác (sau khi đã tính lại kỳ).
    Quá ngày 5 chưa gửi → màn D06 báo trễ.
  · Trong 5 ngày làm việc từ lúc gửi: đối tác bấm «Đồng ý» / «Khiếu nại» từng đơn trên cổng dt.
    Quá hạn không phản hồi = coi như đồng ý (không giữ tiền của ai vì im lặng).
  · Chậm nhất ngày 15 tháng sau (rơi vào thứ Bảy / Chủ nhật thì sang thứ Hai): trả phần đã thống nhất.
    Đơn đang khiếu nại TÁCH RIÊNG (vụ việc có mã) — không giữ cả bảng.

Bảng chỉ CHỤP số D06 lúc gửi; nguồn sự thật vẫn là sổ hoa hồng. Khiếu nại được chấp nhận thì Kế toán tính lại
kỳ gốc như mọi điều chỉnh.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.doi_tac_ban_hang import DoiTacBanHang
from app.models.hoa_hong_d06 import KyHoaHong
from app.models.nguon_doi_soat import BangDoiSoat, DongDoiSoat, VuViecDoiTac, TRANG_THAI_BANG
from app.services import hoa_hong_d06 as H
from app.services import nguon_don as ND
from app.services import rules as R

HAN_GUI_NGAY = 5
PHAN_HOI_NGAY_LAM_VIEC = 5
HAN_TRA_NGAY = 15


class LoiDoiSoat(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _thang_sau(ky: str) -> date:
    d0 = H.dau_thang(ky)
    return date(d0.year + (d0.month == 12), d0.month % 12 + 1, 1)


def han_gui(ky: str) -> date:
    return _thang_sau(ky).replace(day=HAN_GUI_NGAY)


def han_tra(ky: str) -> date:
    d = _thang_sau(ky).replace(day=HAN_TRA_NGAY)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _bang(db: Session, doi_tac_id: int, ky: str) -> BangDoiSoat | None:
    return db.execute(select(BangDoiSoat).where(BangDoiSoat.doi_tac_id == doi_tac_id, BangDoiSoat.ky == ky)).scalars().first()


def _dong(db: Session, b: BangDoiSoat) -> list[DongDoiSoat]:
    return db.execute(select(DongDoiSoat).where(DongDoiSoat.bang_id == b.id).order_by(DongDoiSoat.id)).scalars().all()


def _vv_mo(db: Session, dong_ids: list[int]) -> dict:
    if not dong_ids:
        return {}
    return {v.dong_doi_soat_id: v for v in db.execute(select(VuViecDoiTac).where(
        VuViecDoiTac.dong_doi_soat_id.in_(dong_ids))).scalars()}


def trang_thai(db: Session, b: BangDoiSoat | None, hom_nay: date | None = None) -> str:
    if b is None:
        return "chua_gui"
    hn = hom_nay or date.today()
    ds = _dong(db, b)
    if any(d.y_kien == "khieu_nai" for d in ds):
        return "co_khieu_nai"
    if ds and all(d.y_kien == "dong_y" for d in ds):
        return "dong_y"
    return "qua_han" if hn > b.han_phan_hoi else "da_gui"


def tom_tat(db: Session, doi_tac_id: int, ky: str, hom_nay: date | None = None) -> dict:
    """Cột «Đối soát» trên màn D06 của Kế toán."""
    hn = hom_nay or date.today()
    b = _bang(db, doi_tac_id, ky)
    tt = trang_thai(db, b, hn)
    ds = _dong(db, b) if b else []
    return {"trang_thai": tt, "ten": "Chưa gửi" if tt == "chua_gui" else TRANG_THAI_BANG[tt],
            "gui_luc": b.gui_luc.isoformat(timespec="minutes") if b else None,
            "han_phan_hoi": b.han_phan_hoi.isoformat() if b else None, "han_gui": han_gui(ky).isoformat(),
            "tre_gui": b is None and hn > han_gui(ky) and hn >= _thang_sau(ky), "han_tra": han_tra(ky).isoformat(),
            "so_khieu_nai": sum(1 for d in ds if d.y_kien == "khieu_nai")}


def lap_va_gui(db: Session, u: User, doi_tac_id: int, ky: str, now: datetime | None = None) -> BangDoiSoat:
    from app.services.vai_ke_thua import vai_va_cha
    if not set(vai_va_cha(u.role)) & set(H.VAI_KE_TOAN + ("chutich", "tgd")):
        raise LoiDoiSoat("Chỉ Kế toán lập bảng đối soát", 403)
    now = now or datetime.now()
    if not H.la_v3(db, ky) or not H.dang_bat(db, ky):
        raise LoiDoiSoat("Đối soát trên cổng áp cho kỳ D06 theo v3 (tham số «d06_v3_tu») khi D06 đã bật")
    if now.date() < _thang_sau(ky):
        raise LoiDoiSoat("Tháng chưa kết thúc — chưa lập bảng đối soát")
    th = H.tong_hop(db, ky, now.date())
    rows = [r for r in th["dong"] if r["doi_tac_id"] == doi_tac_id and r["da_ghi_so"]]
    if not rows:
        raise LoiDoiSoat("Kỳ chưa tính lại cho đối tác này — bấm «Tính lại kỳ» trước")
    b = _bang(db, doi_tac_id, ky)
    if b is not None:
        if any(d.y_kien for d in _dong(db, b)):
            raise LoiDoiSoat("Đối tác đã phản hồi bảng này — không gửi lại; xử lý qua vụ việc")
        for d in _dong(db, b):
            db.delete(d)
        b.gui_boi, b.gui_luc = u.username, now
        b.han_phan_hoi = ND.cong_ngay_lam_viec(now.date(), PHAN_HOI_NGAY_LAM_VIEC)
    else:
        b = BangDoiSoat(doi_tac_id=doi_tac_id, ky=ky, gui_boi=u.username, gui_luc=now,
                        han_phan_hoi=ND.cong_ngay_lam_viec(now.date(), PHAN_HOI_NGAY_LAM_VIEC), han_tra=han_tra(ky))
        db.add(b)
    db.flush()
    for r in rows:
        for x in r["nguon"]:
            db.add(DongDoiSoat(bang_id=b.id, ma_don=x["booking"], ten=(x.get("ten_tour") or "")[:200],
                               doanh_so=int(x["doanh_so"]), hoa_hong=int(x["hoa_hong"])))
    R.audit(db, u.username, u.role, "gui_doi_soat", f"doi_tac:{doi_tac_id}", after={"ky": ky, "han_phan_hoi": b.han_phan_hoi.isoformat()})
    db.commit(); db.refresh(b)
    return b


# ── cổng đối tác ────────────────────────────────────────────────────────────────────────────────

def cua_doi_tac(db: Session, dt: DoiTacBanHang, hom_nay: date | None = None) -> list[dict]:
    hn = hom_nay or date.today()
    ra = []
    for b in db.execute(select(BangDoiSoat).where(BangDoiSoat.doi_tac_id == dt.id).order_by(BangDoiSoat.ky.desc()).limit(6)).scalars():
        ds = _dong(db, b)
        vv = _vv_mo(db, [d.id for d in ds])
        tt = trang_thai(db, b, hn)
        ra.append({"id": b.id, "ky": b.ky, "trang_thai": tt, "trang_thai_ten": TRANG_THAI_BANG[tt],
                   "gui_luc": b.gui_luc.isoformat(timespec="minutes"), "han_phan_hoi": b.han_phan_hoi.isoformat(),
                   "han_tra": b.han_tra.isoformat(), "con_han": hn <= b.han_phan_hoi,
                   "tong_doanh_so": sum((d.doanh_so or 0) for d in ds), "tong_hoa_hong": sum((d.hoa_hong or 0) for d in ds),
                   "dong": [{"id": d.id, "ma_don": d.ma_don, "ten": d.ten, "doanh_so": d.doanh_so, "hoa_hong": d.hoa_hong,
                             "y_kien": d.y_kien or ("dong_y" if hn > b.han_phan_hoi else ""),
                             "vu_viec": ({"ma": vv[d.id].ma, "trang_thai": vv[d.id].trang_thai, "han": vv[d.id].han.isoformat(),
                                          "ket_qua": vv[d.id].ket_qua} if d.id in vv else None)} for d in ds]})
    return ra


def _bang_cua(db: Session, dt: DoiTacBanHang, bang_id: int, hn: date) -> BangDoiSoat:
    b = db.get(BangDoiSoat, bang_id)
    if b is None or b.doi_tac_id != dt.id:
        raise LoiDoiSoat("Không có bảng đối soát này", 404)
    if hn > b.han_phan_hoi:
        raise LoiDoiSoat(f"Đã quá hạn phản hồi ({b.han_phan_hoi:%d/%m/%Y}) — bảng coi như đồng ý; khiếu nại nguồn / đơn mới qua «Khiếu nại»")
    return b


def dong_y(db: Session, dt: DoiTacBanHang, bang_id: int, dong_id: int | None = None, now: datetime | None = None) -> None:
    now = now or datetime.now()
    b = _bang_cua(db, dt, bang_id, now.date())
    for d in _dong(db, b):
        if (dong_id is None and not d.y_kien) or d.id == dong_id:
            if d.y_kien == "khieu_nai":
                raise LoiDoiSoat("Đơn này đang khiếu nại — chờ kết quả vụ việc")
            d.y_kien, d.y_kien_luc = "dong_y", now
    b.phan_hoi_luc = now
    R.audit(db, f"doi_tac:{dt.id}", "doi_tac", "dong_y_doi_soat", f"bang_doi_soat:{b.id}", after={"dong": dong_id or "ca_bang"})
    db.commit()


def khieu_nai(db: Session, dt: DoiTacBanHang, bang_id: int, dong_id: int, noi_dung: str, now: datetime | None = None):
    now = now or datetime.now()
    b = _bang_cua(db, dt, bang_id, now.date())
    d = db.get(DongDoiSoat, dong_id)
    if d is None or d.bang_id != b.id:
        raise LoiDoiSoat("Không có đơn này trong bảng", 404)
    if d.y_kien:
        raise LoiDoiSoat("Đơn này đã có ý kiến")
    try:
        v = ND.mo_vu_viec(db, dt, "doi_soat", noi_dung, booking_ma=d.ma_don, dong_id=d.id, now=now)
    except ND.LoiNguon as ex:
        raise LoiDoiSoat(str(ex))
    d.y_kien, d.y_kien_luc, b.phan_hoi_luc = "khieu_nai", now, now
    db.commit()
    return v


# ── chặn đề nghị chi trước khi đối soát xong ─────────────────────────────────────────────────────

def so_duoc_chi(db: Session, k: KyHoaHong, hom_nay: date | None = None) -> int | None:
    """Kỳ D06 theo v3: tổng quyền hưởng ĐƯỢC CHI theo đối soát (phần đã thống nhất). None = kỳ không theo v3
    (giữ luồng cũ). Ném lỗi khi chưa gửi bảng hoặc đối tác còn trong hạn phản hồi mà chưa trả lời hết."""
    if not H.la_v3(db, k.ky):
        return None
    hn = hom_nay or date.today()
    b = _bang(db, k.doi_tac_id, k.ky)
    if b is None:
        raise LoiDoiSoat("Chưa gửi bảng đối soát cho đối tác — lập & gửi trước, rồi mới đề nghị chi")
    ds = _dong(db, b)
    if hn <= b.han_phan_hoi and any(not d.y_kien for d in ds):
        raise LoiDoiSoat(f"Đối tác còn hạn phản hồi đến {b.han_phan_hoi:%d/%m/%Y} — chờ đồng ý hoặc hết hạn")
    vv = _vv_mo(db, [d.id for d in ds])
    tranh = {d.ma_don for d in ds if d.y_kien == "khieu_nai" and d.id in vv and vv[d.id].trang_thai == "mo"}
    th = H.tong_hop(db, k.ky, hn)
    r = next((x for x in th["dong"] if x["ky_id"] == k.id), None)
    if r is None:
        return 0
    if not tranh:
        return r["tong"]
    d_ok = sum(x["doanh_so"] for x in r["nguon"] if x["booking"] not in tranh)
    return H.quyen_huong(d_ok, k.chuong_trinh)["tong"] + (r["tong"] - H.quyen_huong(r["doanh_so"], k.chuong_trinh)["tong"])
