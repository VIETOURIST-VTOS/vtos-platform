"""KS-14 · Đặt phòng khách sạn VTD có thanh toán — luật ở `app/models/don_ks_vtd.py`.

Ai làm gì:
  · Khách (khách hàng / đối tác / cổ đông): chọn phòng, trả ngay 100% (QR / thẻ), hủy theo gói.
  · NV / TP Điều hành: số phòng bán mỗi đêm, chốt đơn với khách sạn (mã xác nhận) hoặc báo hết phòng.
  · Sales: xác nhận số hoàn; TP / GĐ Kinh doanh miễn phạt (ghi lý do).
  · Kế toán: ghi sổ tiền QR máy đã khớp, gán QR chưa khớp, đối soát thẻ, chuyển hoàn, chốt hoa hồng.

Không có ô nào cho trình duyệt gửi số tiền.
"""
from __future__ import annotations

import re
import secrets
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.don_ks_vtd import (HOAN_TT_KS, KENH_KS, TRANG_THAI_DON, TT_DA_TRA_KS, TT_TT_KS, DonKsVtd, PhongTrongVtd,
                                   ThanhToanKsVtd)
from app.models.khach_san_vtd import GoiGiaVtd, KhachSanVtd, LoaiPhongVtd
from app.models.payments import BankTransaction
from app.services import khach_san_vtd as S
from app.services import onepay as OP
from app.services import sepay_pg as SP
from app.services import rules as R

GIU_PHUT = 15                       # phòng giữ cho khách trong lúc trả tiền
CHOT_GIO = 2                        # Điều hành chốt với khách sạn trong 2 giờ làm việc
GIO_LAM = (time(8, 0), time(17, 30))  # thứ Hai – thứ Bảy
DON_CHO_TRA_TOI_DA = 3              # một tài khoản giữ tối đa 3 đơn chưa trả cùng lúc
VAI_DH = S.VAI_NHAP
VAI_KE_TOAN = ("ketoan",)
VAI_SALES = ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "sales_admin")
VAI_MIEN_PHAT = ("tp_kd", "gd_kd", "chutich", "tgd")
VAI_XEM_DON = tuple(dict.fromkeys(S.VAI_XEM + VAI_KE_TOAN + VAI_SALES))
MA_RE = re.compile(r"KS\d{4}[A-HJ-NP-Z2-9]{4}")
_CHU = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TK_TIEN, TK_THU_HO, TK_PHI = "1121", "3388", "6428"
TK_KM = "641"                       # KS-16: voucher VTD Rewards — chi phí bán hàng, VTD chịu thay khách
NGUON_SO = "ks_vtd"


class LoiDon(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _vnd(x) -> str:
    return f"{int(round(float(x or 0))):,}".replace(",", ".")


# ===================================================================== giờ làm việc
def cong_gio_lam(t: datetime, gio: float = CHOT_GIO) -> datetime:
    """Cộng `gio` giờ làm việc (T2–T7, 8:00–17:30) vào mốc t."""
    con = timedelta(hours=gio)
    cur = t
    while True:
        if cur.weekday() == 6:                               # Chủ nhật → sáng thứ Hai
            cur = datetime.combine(cur.date() + timedelta(days=1), GIO_LAM[0])
            continue
        mo, dong = datetime.combine(cur.date(), GIO_LAM[0]), datetime.combine(cur.date(), GIO_LAM[1])
        if cur < mo:
            cur = mo
        if cur >= dong:
            cur = datetime.combine(cur.date() + timedelta(days=1), GIO_LAM[0])
            continue
        if cur + con <= dong:
            return cur + con
        con -= dong - cur
        cur = datetime.combine(cur.date() + timedelta(days=1), GIO_LAM[0])


# ===================================================================== phòng trống
def _so_ban(db: Session, lps: list[LoaiPhongVtd], d0: date, d1: date) -> dict:
    """{(loại phòng, đêm): số phòng bán} — dòng Điều hành sửa, không có thì theo hồ sơ loại phòng; đóng bán = 0."""
    ids = [x.id for x in lps]
    sua = {(p.loai_phong_id, p.ngay): p for p in db.execute(select(PhongTrongVtd).where(
        PhongTrongVtd.loai_phong_id.in_(ids), PhongTrongVtd.ngay >= d0, PhongTrongVtd.ngay < d1)).scalars()} if ids else {}
    ra_ = {}
    for x in lps:
        for dem in S.cac_dem(d0, d1):
            p = sua.get((x.id, dem))
            ra_[(x.id, dem)] = 0 if (p and p.dong) else (p.so_ban if p and p.so_ban is not None else int(x.so_phong or 0))
    return ra_


def _dang_giu(now: datetime):
    return or_(DonKsVtd.trang_thai.in_(("da_tra", "da_xac_nhan")),
               (DonKsVtd.trang_thai == "cho_tra") & (DonKsVtd.giu_den > now))


def _da_nhan(db: Session, lp_ids: list[int], d0: date, d1: date, now: datetime, bo_don: int | None = None) -> dict:
    """{(loại phòng, đêm): số phòng đã nhận} — đơn đang giữ 15 phút, đã trả, đã xác nhận."""
    ra_: dict = {}
    if not lp_ids:
        return ra_
    tap = set(lp_ids)
    q = select(DonKsVtd).where(_dang_giu(now), DonKsVtd.vao < d1, DonKsVtd.ra > d0)
    for d in db.execute(q).scalars():
        if bo_don and d.id == bo_don:
            continue
        for x in d.dong or []:
            if x.get("loai_phong_id") not in tap:
                continue
            for dem in S.cac_dem(max(d.vao, d0), min(d.ra, d1)):
                k = (x["loai_phong_id"], dem)
                ra_[k] = ra_.get(k, 0) + int(x.get("so") or 0)
    return ra_


def con_phong(db: Session, lps: list[LoaiPhongVtd], vao: date, ra: date, now: datetime | None = None,
              bo_don: int | None = None) -> dict[int, int]:
    """{loại phòng: số phòng còn bán được cho CẢ kỳ ở} = nhỏ nhất qua các đêm."""
    now = now or datetime.now()
    ban = _so_ban(db, lps, vao, ra)
    nhan = _da_nhan(db, [x.id for x in lps], vao, ra, now, bo_don)
    return {x.id: max(0, min((ban[(x.id, dem)] - nhan.get((x.id, dem), 0)) for dem in S.cac_dem(vao, ra)))
            for x in lps}


def bang_phong_trong(db: Session, u: User, kid: int, tu: str | date | None = None, so_ngay: int = 14,
                     now: datetime | None = None) -> dict:
    if u.role not in VAI_XEM_DON:
        raise LoiDon("Không có quyền xem", 403)
    now = now or datetime.now()
    try:
        S._ks(db, kid)
    except S.LoiKhachSan as ex:
        raise LoiDon(str(ex), ex.status)
    try:
        d0 = tu if isinstance(tu, date) else (date.fromisoformat(str(tu)[:10]) if tu else now.date())
    except ValueError:
        raise LoiDon("Ngày không hợp lệ")
    so_ngay = max(1, min(31, int(so_ngay or 14)))
    d1 = d0 + timedelta(days=so_ngay)
    lps = S._lp_cua(db, kid)
    ban = _so_ban(db, lps, d0, d1)
    nhan = _da_nhan(db, [x.id for x in lps], d0, d1, now)
    sua = {(p.loai_phong_id, p.ngay): p for p in db.execute(select(PhongTrongVtd).where(
        PhongTrongVtd.loai_phong_id.in_([x.id for x in lps] or [0]), PhongTrongVtd.ngay >= d0, PhongTrongVtd.ngay < d1)).scalars()}
    ngay = S.cac_dem(d0, d1)
    return {"ngay": [x.isoformat() for x in ngay], "duoc_sua": u.role in VAI_DH,
            "phong": [{"id": x.id, "ten": x.ten, "so_phong": x.so_phong, "dang_ban": x.dang_ban,
                       "o": [{"ngay": dem.isoformat(), "ban": ban[(x.id, dem)], "nhan": nhan.get((x.id, dem), 0),
                              "con": max(0, ban[(x.id, dem)] - nhan.get((x.id, dem), 0)),
                              "dong": bool(sua.get((x.id, dem)) and sua[(x.id, dem)].dong),
                              "da_sua": bool(sua.get((x.id, dem)) and sua[(x.id, dem)].so_ban is not None)} for dem in ngay]}
                      for x in lps]}


def luu_phong_trong(db: Session, u: User, lid: int, ngay: list[str], so_ban: int | None, dong: bool,
                    now: datetime | None = None) -> int:
    """Điều hành sửa số phòng bán / đóng bán cho một hoặc nhiều đêm. so_ban None = về theo hồ sơ."""
    now = now or datetime.now()
    if u.role not in VAI_DH:
        raise LoiDon("Chỉ Điều hành sửa số phòng bán", 403)
    lp = db.get(LoaiPhongVtd, lid)
    if lp is None:
        raise LoiDon("Không có loại phòng này", 404)
    if so_ban is not None and not (0 <= int(so_ban) <= 500):
        raise LoiDon("Số phòng bán 0 – 500")
    try:
        ds = sorted({date.fromisoformat(str(x)[:10]) for x in ngay})
    except ValueError:
        raise LoiDon("Ngày không hợp lệ")
    if not ds or len(ds) > 366:
        raise LoiDon("Chọn 1 – 366 đêm")
    if ds[0] < now.date():
        raise LoiDon("Không sửa đêm đã qua")
    n = 0
    for dem in ds:
        p = db.execute(select(PhongTrongVtd).where(PhongTrongVtd.loai_phong_id == lid, PhongTrongVtd.ngay == dem)).scalars().first()
        if p is None:
            p = PhongTrongVtd(loai_phong_id=lid, ngay=dem)
            db.add(p)
        p.so_ban, p.dong, p.sua_boi, p.sua_luc = (int(so_ban) if so_ban is not None else None), bool(dong), u.username, now
        n += 1
    R.audit(db, u.username, u.role, "ks_vtd_phong_trong", f"loai_phong_vtd:{lid}",
            after={"tu": ds[0].isoformat(), "den": ds[-1].isoformat(), "so_dem": n, "so_ban": so_ban, "dong": bool(dong)})
    db.flush()
    return n


# ===================================================================== đơn
def _ma_moi(db: Session, vao: date) -> str:
    for _ in range(30):
        ma = f"KS{vao:%y%m}" + "".join(secrets.choice(_CHU) for _ in range(4))
        if not db.execute(select(DonKsVtd.id).where(DonKsVtd.ma == ma)).first():
            return ma
    raise LoiDon("Chưa tạo được mã đơn — thử lại", 503)


def da_tra(db: Session, d: DonKsVtd) -> int:
    return int(db.execute(select(func.coalesce(func.sum(ThanhToanKsVtd.so_tien), 0)).where(
        ThanhToanKsVtd.don_id == d.id, ThanhToanKsVtd.trang_thai.in_(TT_DA_TRA_KS))).scalar() or 0)


def _voucher_doi_chieu(db: Session, d: DonKsVtd, now: datetime) -> None:
    """KS-16: đơn có voucher vừa hủy / hết giờ giữ → trả điểm voucher nếu đủ điều kiện."""
    if d.voucher_id:
        from app.services import rewards as RW
        RW.doi_chieu_voucher_ks(db, d, now)


def cap_nhat(db: Session, d: DonKsVtd, now: datetime | None = None) -> DonKsVtd:
    now = now or datetime.now()
    if d.trang_thai == "cho_tra" and d.giu_den and d.giu_den <= now:
        d.trang_thai = "het_han"
        _voucher_doi_chieu(db, d, now)
        db.flush()
    return d


def het_han_tat(db: Session, now: datetime | None = None) -> None:
    now = now or datetime.now()
    for d in db.execute(select(DonKsVtd).where(DonKsVtd.trang_thai == "cho_tra", DonKsVtd.giu_den <= now)).scalars().all():
        d.trang_thai = "het_han"
        _voucher_doi_chieu(db, d, now)
    db.flush()


def _dong_dat(db: Session, k: KhachSanVtd, vao: date, ra: date, chon: list[dict], nl: int = 1, te: int = 0, tuoi=None) -> list[dict]:
    """Dòng đơn máy tính từ gói đã duyệt. chon = [{goi_id, so}] — không nhận số tiền."""
    gop: dict[int, int] = {}
    for c in chon or []:
        n = int(c.get("so") or 0)
        if n > 0:
            gop[int(c.get("goi_id") or 0)] = gop.get(int(c.get("goi_id") or 0), 0) + n
    if not gop:
        raise LoiDon("Chọn ít nhất một phòng")
    dong = []
    for gid, n in gop.items():
        g = db.get(GoiGiaVtd, gid)
        lp = db.get(LoaiPhongVtd, g.loai_phong_id) if g else None
        if g is None or lp is None or lp.khach_san_id != k.id or g.trang_thai != "da_duyet" or not g.dang_ban or not lp.dang_ban:
            raise LoiDon("Gói giá đã thay đổi — tải lại trang để xem giá mới", 409)
        p = S.gia_luu(g, S._mua_cua(db, [g.id]).get(g.id, []), vao, ra)
        if p is None:
            raise LoiDon(f"«{lp.ten} · {g.ten}» chưa có giá cho các ngày này", 409)
        tien = int(p["tong"]) * n
        hh = S.han_huy(g, vao)
        dong.append({"goi_id": g.id, "loai_phong_id": lp.id, "loai_phong": lp.ten, "goi": g.ten, "so": n, "tien": tien,
                     "bua_sang": bool(g.bua_sang), "huy_han": hh.isoformat() if hh else None, "_lp": lp})
    # KS-16j: phụ thu trẻ em / giường phụ máy tự cộng vào dòng (chưa thuế phí, cùng tỷ lệ thuế phí như giá phòng)
    try:
        pts = S.phu_thu_dong(k, dong, {x["loai_phong_id"]: x["_lp"] for x in dong}, nl, te, tuoi, (ra - vao).days)
    except S.LoiKhachSan as ex:
        raise LoiDon(str(ex))
    for x, pt in zip(dong, pts):
        x.pop("_lp")
        if pt:
            x["phu_thu"] = pt
            x["tien"] += pt
        x["thue"] = int(round(x["tien"] * float(k.thue_phi_pt or 0) / 100))
    return dong


def dat(db: Session, tk, kid: int, d: dict, now: datetime | None = None) -> DonKsVtd:
    """Khách bấm «Đặt và thanh toán»: máy kiểm phòng trống, giữ phòng 15 phút, tạo đơn «Chờ thanh toán»."""
    now = now or datetime.now()
    vao, ra = S._kiem_ky(d.get("vao"), d.get("ra"), now.date())
    k = db.get(KhachSanVtd, kid)
    if k is None or not k.hien_cong or k.ngung:
        raise LoiDon("Khách sạn này không còn hiện trên VTD", 404)
    ho_ten = " ".join(str(d.get("ho_ten") or "").split())[:120]
    lien_he = str(d.get("lien_he") or "").strip()[:120]
    email = str(d.get("email") or "").strip()[:160]
    if len(ho_ten.split()) < 2:
        raise LoiDon("Ghi đủ họ và tên khách nhận phòng")
    if len(re.sub(r"\D", "", lien_he)) < 9:
        raise LoiDon("Ghi số điện thoại / Zalo để Vietourist báo xác nhận")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise LoiDon("Email chưa đúng")
    if not d.get("dong_y"):
        raise LoiDon("Đánh dấu đồng ý chính sách hủy và điều kiện đặt phòng")
    nl, te = max(1, int(d.get("nguoi_lon") or 1)), max(0, int(d.get("tre_em") or 0))
    dang = db.execute(select(func.count(DonKsVtd.id)).where(DonKsVtd.tai_khoan_ngoai_id == tk.id, DonKsVtd.trang_thai == "cho_tra",
                                                            DonKsVtd.giu_den > now)).scalar() or 0
    if dang >= DON_CHO_TRA_TOI_DA:
        raise LoiDon("Bạn đang có đơn chờ thanh toán — trả hoặc hủy đơn đó trước", 409)
    tuoi = S.doc_tuoi(te, d.get("tuoi_tre_em"))
    dong = _dong_dat(db, k, vao, ra, d.get("chon") or [], nl, te, tuoi)
    so = sum(x["so"] for x in dong)
    if so > 9:
        raise LoiDon("Tối đa 9 phòng một lần đặt")
    lp_ids = sorted({x["loai_phong_id"] for x in dong})
    # Khoá hàng loại phòng (Postgres) để hai khách cùng bấm không bán quá số phòng; SQLite bỏ qua.
    lps = db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.id.in_(lp_ids)).with_for_update()).scalars().all()
    con = con_phong(db, lps, vao, ra, now)
    can: dict[int, int] = {}
    for x in dong:
        can[x["loai_phong_id"]] = can.get(x["loai_phong_id"], 0) + x["so"]
    for lp in lps:
        if can[lp.id] > con[lp.id]:
            raise LoiDon(f"«{lp.ten}» chỉ còn {con[lp.id]} phòng cho các ngày này" if con[lp.id] else f"«{lp.ten}» đã hết phòng cho các ngày này", 409)
    tien = sum(x["tien"] for x in dong)
    thue = int(round(tien * float(k.thue_phi_pt or 0) / 100))
    v = None
    if str(d.get("ma_voucher") or "").strip():                      # KS-16: khách tự nhập voucher, VTD chịu
        from app.services import rewards as RW
        try:
            v = RW.kiem_voucher_ks(db, tk, d.get("ma_voucher"), tien + thue, now.date())
        except RW.LoiDiem as ex:
            raise LoiDon(str(ex))
    giam = int(v.gia_tri) if v else 0
    don = DonKsVtd(ma=_ma_moi(db, vao), khach_san_id=k.id, tai_khoan_ngoai_id=tk.id, cong=tk.loai, ho_ten=ho_ten,
                   lien_he=lien_he, email=email, yeu_cau=((f"Tuổi trẻ em: {', '.join(str(t) for t in tuoi)}\n" if tuoi else "")
                                                                   + str(d.get("yeu_cau") or "").strip())[:1500], vao=vao, ra=ra,
                   nguoi_lon=nl, tre_em=te, dong=dong, so_phong=so, tien_phong=tien, thue_phi=thue, tong=tien + thue - giam,
                   trang_thai="cho_tra", giu_den=now + timedelta(minutes=GIU_PHUT), tao_luc=now,
                   voucher_id=v.id if v else None, giam_voucher=giam)
    db.add(don)
    db.flush()
    if v is not None:
        RW.ap_voucher_ks(db, tk, v, don, now)
    R.audit(db, f"cong:{tk.id}", tk.loai, "ks_vtd_dat", f"don_ks_vtd:{don.ma}",
            after={"tong": tien + thue - giam, "so_phong": so, "giam_voucher": giam})
    db.flush()
    return don


def _sau_khi_tra(db: Session, d: DonKsVtd, now: datetime) -> None:
    """Đủ tiền → «Đã thanh toán», hạn chốt 2 giờ làm việc. Trả sau khi hết giờ giữ mà phòng đã hết → hủy, hoàn 100%."""
    if d.trang_thai not in ("cho_tra", "het_han") or da_tra(db, d) < int(d.tong):
        return
    if d.trang_thai == "het_han":
        lps = db.execute(select(LoaiPhongVtd).where(LoaiPhongVtd.id.in_({x["loai_phong_id"] for x in d.dong}))).scalars().all()
        con = con_phong(db, lps, d.vao, d.ra, now, bo_don=d.id)
        can: dict[int, int] = {}
        for x in d.dong:
            can[x["loai_phong_id"]] = can.get(x["loai_phong_id"], 0) + int(x["so"])
        if any(can[i] > con.get(i, 0) for i in can) or d.vao < now.date():
            _huy(db, d, "may", "Tiền vào sau khi hết giờ giữ phòng và phòng đã hết", now, toan_bo=True)
            return
        if d.voucher_id and not _voucher_con_giu(db, d):
            _huy(db, d, "may", "Tiền vào sau khi hết giờ giữ phòng — voucher đã trả điểm lại cho khách", now, toan_bo=True)
            return
    d.trang_thai, d.tra_luc, d.han_chot = "da_tra", now, cong_gio_lam(now)
    R.audit(db, "may", "may", "ks_vtd_da_tra", f"don_ks_vtd:{d.ma}", after={"tong": int(d.tong)})
    db.flush()


def _voucher_con_giu(db: Session, d: DonKsVtd) -> bool:
    from app.models.rewards import VoucherRewards
    v = db.get(VoucherRewards, d.voucher_id) if d.voucher_id else None
    return v is not None and v.trang_thai == "da_dung" and v.don_ks_id == d.id


def so_hoan_neu_huy(d: DonKsVtd, tra: int, hom_nay: date) -> int:
    """Hoàn theo gói: dòng còn trong hạn miễn phí hủy (hôm nay TRƯỚC ngày hạn) → hoàn phần dòng đó (gồm thuế phí).
    KS-16: đơn có voucher mà được hoàn thì voucher trả điểm lại, nên phần hoàn của gói trừ đi số voucher."""
    if tra <= 0:
        return 0
    if all(x.get("huy_han") and hom_nay < date.fromisoformat(x["huy_han"]) for x in d.dong):
        return tra
    n = sum(int(x["tien"]) + int(x.get("thue") or 0) for x in d.dong if x.get("huy_han") and hom_nay < date.fromisoformat(x["huy_han"]))
    return min(tra, max(0, n - int(d.giam_voucher or 0)))


def _huy(db: Session, d: DonKsVtd, boi: str, ly_do: str, now: datetime, toan_bo: bool = False) -> DonKsVtd:
    tra = da_tra(db, d)
    d.so_hoan = tra if toan_bo else so_hoan_neu_huy(d, tra, now.date())
    d.trang_thai, d.huy_boi, d.huy_luc, d.ly_do_huy = "da_huy", boi[:60], now, (ly_do or "").strip()[:300]
    d.hoan_tt = "cho_sales" if int(d.so_hoan) > 0 else ""
    _voucher_doi_chieu(db, d, now)
    db.flush()
    return d


# ===================================================================== phía khách
def _cua(db: Session, tk, ma: str) -> DonKsVtd:
    d = db.execute(select(DonKsVtd).where(DonKsVtd.ma == str(ma or "").upper().strip())).scalars().first()
    if d is None or d.tai_khoan_ngoai_id != tk.id:
        raise LoiDon("Không có đơn này trong tài khoản của bạn", 404)
    return d


def _tt_out(t: ThanhToanKsVtd) -> dict:
    return {"id": t.id, "kenh": t.kenh, "kenh_ten": KENH_KS.get(t.kenh, t.kenh), "so_tien": int(t.so_tien),
            "trang_thai": t.trang_thai, "trang_thai_ten": TT_TT_KS.get(t.trang_thai, t.trang_thai),
            "luc": t.luc.isoformat(timespec="minutes") if t.luc else None, "so_gd_cong": t.so_gd_cong,
            "phi_the": int(t.phi_the) if t.phi_the is not None else None, "but_toan": t.but_toan, "ghi_chu": t.ghi_chu}


def ra_khach(db: Session, d: DonKsVtd, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    k = db.get(KhachSanVtd, d.khach_san_id)
    tra = da_tra(db, d)
    huy_duoc = d.trang_thai in ("cho_tra", "het_han", "da_tra", "da_xac_nhan") and now.date() < d.vao
    return {"ma": d.ma, "khach_san": {"id": k.id, "ten": k.ten, "sao": k.sao, "khu_vuc": k.khu_vuc, "tinh_thanh": k.tinh_thanh,
                                       "gio_nhan": k.gio_nhan, "gio_tra": k.gio_tra, "dia_chi": k.dia_chi} if k else None,
            "vao": d.vao.isoformat(), "ra": d.ra.isoformat(), "dem": (d.ra - d.vao).days, "nguoi_lon": d.nguoi_lon,
            "tre_em": d.tre_em, "dong": d.dong, "so_phong": d.so_phong, "tien_phong": int(d.tien_phong),
            "thue_phi": int(d.thue_phi), "tong": int(d.tong), "da_tra": tra, "con_phai_tra": max(0, int(d.tong) - tra),
            "giam_voucher": int(d.giam_voucher or 0), "voucher": _ma_voucher_don(db, d),
            "trang_thai": d.trang_thai, "trang_thai_ten": TRANG_THAI_DON.get(d.trang_thai, d.trang_thai),
            "giu_den": d.giu_den.isoformat(timespec="seconds") if d.giu_den else None,
            "giay_con": max(0, int((d.giu_den - now).total_seconds())) if d.trang_thai == "cho_tra" and d.giu_den else 0,
            "tra_luc": d.tra_luc.isoformat(timespec="minutes") if d.tra_luc else None,
            "han_chot": d.han_chot.isoformat(timespec="minutes") if d.han_chot else None,
            "ma_xac_nhan_ks": d.ma_xac_nhan_ks, "xac_nhan_luc": d.xac_nhan_luc.isoformat(timespec="minutes") if d.xac_nhan_luc else None,
            "ho_ten": d.ho_ten, "lien_he": d.lien_he, "email": d.email,
            "ly_do_huy": d.ly_do_huy, "so_hoan": int(d.so_hoan), "hoan_tt": d.hoan_tt, "hoan_tt_ten": HOAN_TT_KS.get(d.hoan_tt, ""),
            "da_hoan_tien": int(d.da_hoan_tien), "co_the_tra": d.trang_thai == "cho_tra" and tra < int(d.tong),
            "co_the_huy": huy_duoc, "hoan_neu_huy": so_hoan_neu_huy(d, tra, now.date()) if huy_duoc else 0,
            "danh_gia": _dg(db, d, now),
            "the_bat": SP.cong_the_bat(), "tao_luc": d.tao_luc.isoformat(timespec="minutes") if d.tao_luc else None}


def _ma_voucher_don(db: Session, d: DonKsVtd) -> dict | None:
    if not d.voucher_id:
        return None
    from app.models.rewards import VoucherRewards, TRANG_THAI_VOUCHER
    v = db.get(VoucherRewards, d.voucher_id)
    return {"ma": v.ma, "gia_tri": int(v.gia_tri), "trang_thai": v.trang_thai,
            "trang_thai_ten": TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai)} if v else None


def khuyen_mai(db: Session, d: DonKsVtd) -> int:
    """Phần voucher VTD CHỊU trên đơn: chỉ khi voucher đã dùng hẳn (đơn ở, hoặc hủy không hoàn)."""
    return int(d.giam_voucher or 0) if d.voucher_id and _voucher_con_giu(db, d) else 0


def _dg(db: Session, d: DonKsVtd, now: datetime) -> dict:
    from app.services import danh_gia_ks as DGK   # KS-15
    return DGK.trang_thai_don(db, d, now)


def ds_cua(db: Session, tk, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    ds = db.execute(select(DonKsVtd).where(DonKsVtd.tai_khoan_ngoai_id == tk.id).order_by(DonKsVtd.id.desc()).limit(50)).scalars().all()
    for d in ds:
        cap_nhat(db, d, now)
    db.commit()
    return [ra_khach(db, d, now) for d in ds]


def mot_cua(db: Session, tk, ma: str, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    db.commit()
    return ra_khach(db, d, now)


def qr(db: Session, tk, ma: str, now: datetime | None = None) -> dict:
    from app.services import cong_khach as K
    from app.services import vietqr as Q
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    db.commit()
    con = int(d.tong) - da_tra(db, d)
    if d.trang_thai != "cho_tra" or con <= 0:
        raise LoiDon(f"Đơn đang «{TRANG_THAI_DON.get(d.trang_thai, d.trang_thai)}» — không thanh toán", 409)
    ba = K.tai_khoan_qr(db)
    if ba is None or not ba.account_number:
        raise LoiDon("Thanh toán QR chưa mở — dùng thẻ hoặc liên hệ Vietourist", 409)
    bin_ = Q.bin_cua(ba.bank_name)
    if bin_ is None:
        raise LoiDon("Thanh toán QR chưa mở cho ngân hàng này — dùng thẻ hoặc liên hệ Vietourist", 409)
    return {"ma": d.ma, "so_tien": con, "payload": Q.payload(bin_, ba.account_number, con, d.ma), "noi_dung": Q.noi_dung_sach(d.ma),
            "ngan_hang": ba.bank_name, "so_tk": ba.account_number, "chu_tk": ba.account_name, "tu_khop": True,
            "giu_den": d.giu_den.isoformat(timespec="seconds") if d.giu_den else None}


def onepay_bat_dau(db: Session, tk, ma: str, goc: str, ip: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    if not OP.bat():
        raise LoiDon("Thanh toán thẻ chưa mở — dùng QR chuyển khoản", 409)
    d = cap_nhat(db, _cua(db, tk, ma), now)
    con = int(d.tong) - da_tra(db, d)
    if d.trang_thai != "cho_tra" or con <= 0:
        db.commit()
        raise LoiDon(f"Đơn đang «{TRANG_THAI_DON.get(d.trang_thai, d.trang_thai)}» — không thanh toán", 409)
    t = ThanhToanKsVtd(don_id=d.id, kenh="onepay", so_tien=con, trang_thai="cho", luc=now, goc=goc[:80])
    db.add(t)
    db.flush()
    t.ma_gd = f"{d.ma}T{t.id}"
    url = OP.duong_thanh_toan(t.ma_gd, con, f"Dat phong {d.ma}", f"{goc}/api/v1/onepay/tra-ve", ip, f"{goc}/cong")
    db.commit()
    return url


def the_bat_dau(db: Session, tk, ma: str, goc: str, ip: str, now: datetime | None = None) -> dict:
    """SP-1: cổng thẻ SePay (ưu tiên) → {"form": biểu mẫu POST}; SePay chưa có khóa mà OnePay có → {"url": …}."""
    now = now or datetime.now()
    if not SP.bat():
        return {"url": onepay_bat_dau(db, tk, ma, goc, ip, now)}
    d = cap_nhat(db, _cua(db, tk, ma), now)
    con = int(d.tong) - da_tra(db, d)
    if d.trang_thai != "cho_tra" or con <= 0:
        db.commit()
        raise LoiDon(f"Đơn đang «{TRANG_THAI_DON.get(d.trang_thai, d.trang_thai)}» — không thanh toán", 409)
    t = ThanhToanKsVtd(don_id=d.id, kenh="sepay", so_tien=con, trang_thai="cho", luc=now, goc=goc[:80])
    db.add(t)
    db.flush()
    t.ma_gd = f"{d.ma}T{t.id}"
    ve = f"{goc}/cong?ks_vtd={d.ma}&the="
    f = SP.bieu_mau(t.ma_gd, con, f"Dat phong {d.ma}", ve + "cho", ve + "loi", ve + "huy")
    db.commit()
    return {"form": f}


def sepay_ket_qua(db: Session, kq: dict, now: datetime | None = None) -> tuple[DonKsVtd, ThanhToanKsVtd] | None:
    """IPN SePay đã qua khóa: chạy lại không ghi thêm. ORDER_PAID + APPROVED + đúng số tiền → thành công."""
    now = now or datetime.now()
    t = db.execute(select(ThanhToanKsVtd).where(ThanhToanKsVtd.ma_gd == kq["ma_gd"], ThanhToanKsVtd.kenh == "sepay")).scalars().first()
    if t is None:
        return None
    d = db.get(DonKsVtd, t.don_id)
    if kq["loai"] == "TRANSACTION_VOID":
        t.ghi_chu = (f"SePay báo hủy giao dịch {kq['so_gd']} — Kế toán kiểm tra" + (f" · {t.ghi_chu}" if t.ghi_chu else ""))[:300]
        R.audit(db, "sepay", "sepay", "ks_vtd_the_huy_gd", f"don_ks_vtd:{d.ma}", after={"so_gd": kq["so_gd"], "trang_thai": t.trang_thai})
        db.commit()
        return d, t
    if t.trang_thai in ("cho", "that_bai"):
        t.ket_qua, t.so_gd_cong = kq["ma_kq"], kq["so_gd"]
        if kq["thanh_cong"] and kq["so_tien"] == int(t.so_tien):
            t.trang_thai = "thanh_cong"
            t.ghi_chu = " · ".join(x for x in (kq["cach"], kq["the"]) if x)[:300]
            R.audit(db, "sepay", "sepay", "ks_vtd_the_thanh_cong", f"don_ks_vtd:{d.ma}", after={"so_tien": int(t.so_tien), "so_gd": kq["so_gd"]})
        else:
            t.trang_thai = "that_bai"
            t.ghi_chu = "Số tiền không khớp" if kq["thanh_cong"] else f"SePay: {kq['loai']} {kq['ma_kq']}"[:300]
        cap_nhat(db, d, now)
        _sau_khi_tra(db, d, now)
        db.commit()
    return d, t


def cua_minh(p: dict) -> bool:
    """Kết quả OnePay này thuộc đơn khách sạn VTD (mã giao dịch bắt đầu KS) — đường trả về dùng chung với đặt bàn."""
    return str(p.get("vpc_MerchTxnRef") or "").upper().startswith("KS")


def onepay_ket_qua(db: Session, p: dict, now: datetime | None = None) -> tuple[DonKsVtd, ThanhToanKsVtd] | None:
    now = now or datetime.now()
    kq = OP.ket_qua(p)
    if not kq["hop_le"]:
        return None
    t = db.execute(select(ThanhToanKsVtd).where(ThanhToanKsVtd.ma_gd == kq["ma_gd"], ThanhToanKsVtd.kenh == "onepay")).scalars().first()
    if t is None:
        return None
    d = db.get(DonKsVtd, t.don_id)
    if t.trang_thai == "cho":
        t.ket_qua, t.so_gd_cong = kq["ma_kq"], kq["so_gd"]
        if kq["thanh_cong"] and kq["so_tien"] == int(t.so_tien):
            t.trang_thai = "thanh_cong"
            R.audit(db, "onepay", "onepay", "ks_vtd_the_thanh_cong", f"don_ks_vtd:{d.ma}", after={"so_tien": int(t.so_tien), "so_gd": kq["so_gd"]})
        else:
            t.trang_thai = "that_bai"
            t.ghi_chu = "Số tiền không khớp" if kq["thanh_cong"] else f"Mã kết quả {kq['ma_kq']}"
        cap_nhat(db, d, now)
        _sau_khi_tra(db, d, now)
        db.commit()
    return d, t


def tu_khop(db: Session, txn: BankTransaction, now: datetime | None = None) -> bool:
    """Gọi từ khớp giao dịch ngân hàng: nội dung có mã đơn KS… → nhận thay đường booking.
    Đúng mã + ĐÚNG số còn phải trả + đơn còn giữ (hoặc vừa hết giờ mà phòng còn) → đơn «Đã thanh toán»;
    tiền ghi sổ khi Kế toán xác nhận. Lệch gì cũng để Kế toán quyết định. Trả True khi giao dịch là của KS-14."""
    now = now or datetime.now()
    m = MA_RE.search((txn.content or "").upper().replace(" ", ""))
    if not m:
        return False
    d = db.execute(select(DonKsVtd).where(DonKsVtd.ma == m.group(0))).scalars().first()
    if d is None:
        txn.match_status, txn.match_note = "cho_ke_toan", f"Mã đặt phòng {m.group(0)} không tồn tại"
        return True
    if db.execute(select(ThanhToanKsVtd.id).where(ThanhToanKsVtd.bank_txn_id == txn.id)).first():
        return True
    cap_nhat(db, d, now)
    con = int(d.tong) - da_tra(db, d)
    so = int(round(float(txn.amount or 0)))
    if d.trang_thai in ("cho_tra", "het_han") and con > 0 and so == con:
        t = ThanhToanKsVtd(don_id=d.id, kenh="qr", so_tien=so, trang_thai="tu_khop", bank_txn_id=txn.id,
                           luc=txn.transaction_date or now, ghi_chu="Máy khớp mã đơn + đúng số tiền")
        db.add(t)
        db.flush()
        txn.match_status, txn.match_note = "da_khop", f"Đặt phòng {d.ma} — máy khớp, chờ Kế toán ghi sổ"
        _sau_khi_tra(db, d, now)
        R.audit(db, "robot", "robot", "ks_vtd_qr_tu_khop", f"don_ks_vtd:{d.ma}", after={"so_tien": so, "txn": txn.id})
        return True
    txn.match_status = "cho_ke_toan"
    txn.match_note = (f"Đặt phòng {d.ma} ({TRANG_THAI_DON.get(d.trang_thai, d.trang_thai)}): chuyển {_vnd(so)} đ, "
                      f"còn phải trả {_vnd(max(con, 0))} đ — Kế toán quyết định")[:300]
    return True


def huy_boi_khach(db: Session, tk, ma: str, ly_do: str = "", now: datetime | None = None) -> DonKsVtd:
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    if d.trang_thai not in ("cho_tra", "het_han", "da_tra", "da_xac_nhan"):
        raise LoiDon(f"Đơn đang «{TRANG_THAI_DON.get(d.trang_thai, d.trang_thai)}» — không hủy được", 409)
    if now.date() >= d.vao:
        raise LoiDon("Đã tới ngày nhận phòng — liên hệ Vietourist để được hỗ trợ", 409)
    for t in db.execute(select(ThanhToanKsVtd).where(ThanhToanKsVtd.don_id == d.id, ThanhToanKsVtd.trang_thai == "cho")).scalars():
        t.trang_thai, t.ghi_chu = "that_bai", "Khách hủy đơn khi chưa xong thanh toán thẻ"
    _huy(db, d, f"khach:{tk.id}", ly_do or "Khách hủy", now)
    R.audit(db, f"cong:{tk.id}", tk.loai, "ks_vtd_khach_huy", f"don_ks_vtd:{d.ma}", after={"so_hoan": int(d.so_hoan)})
    db.flush()
    return d


# ===================================================================== phía VTOS
def _don(db: Session, did: int) -> DonKsVtd:
    d = db.get(DonKsVtd, did)
    if d is None:
        raise LoiDon("Không có đơn đặt phòng này", 404)
    return d


def _quyen(u: User, vai: tuple, viec: str) -> None:
    if u.role not in vai:
        raise LoiDon(f"Không có quyền {viec}", 403)


def ra_vtos(db: Session, d: DonKsVtd, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    o = ra_khach(db, d, now)
    tts = db.execute(select(ThanhToanKsVtd).where(ThanhToanKsVtd.don_id == d.id).order_by(ThanhToanKsVtd.id)).scalars().all()
    o.update({"id": d.id, "cong": d.cong, "yeu_cau": d.yeu_cau, "thanh_toan": [_tt_out(t) for t in tts if t.trang_thai != "cho" or t.luc > now - timedelta(hours=1)],
              "xac_nhan_boi": d.xac_nhan_boi, "huy_boi": d.huy_boi, "huy_luc": d.huy_luc.isoformat(timespec="minutes") if d.huy_luc else None,
              "mien_phat_boi": d.mien_phat_boi, "hoan_boi": d.hoan_boi, "hoan_ghi_chu": d.hoan_ghi_chu,
              "hoa_hong": int(d.hoa_hong) if d.hoa_hong is not None else None,
              "phai_tra_ks": int(d.phai_tra_ks) if d.phai_tra_ks is not None else None, "chot_boi": d.chot_boi,
              "qua_han_chot": bool(d.trang_thai == "da_tra" and d.han_chot and d.han_chot < now),
              "giu_lai": max(0, o["da_tra"] - int(d.so_hoan)) if d.trang_thai == "da_huy" else None,
              "khuyen_mai": khuyen_mai(db, d), "km_but_toan": d.km_but_toan, "de_nghi_chi": _dnc(db, d.payment_request_id),
              "dt_but_toan": d.dt_but_toan})
    return o


def _dnc(db: Session, pid: int | None) -> dict | None:
    """KS-16d — mã + trạng thái đề nghị chi trả NCC đã lập lúc chốt."""
    if not pid:
        return None
    from app.models.ops import PaymentRequest
    r = db.get(PaymentRequest, pid)
    return {"id": r.id, "code": r.code, "status": r.status, "so_tien": int(r.amount or 0)} if r else None


def ds_vtos(db: Session, u: User, loc: str = "", kid: int | None = None, now: datetime | None = None) -> dict:
    _quyen(u, VAI_XEM_DON, "xem đơn đặt phòng")
    now = now or datetime.now()
    het_han_tat(db, now)
    db.commit()
    q = select(DonKsVtd)
    if kid:
        q = q.where(DonKsVtd.khach_san_id == kid)
    if loc == "cho_chot":
        q = q.where(DonKsVtd.trang_thai == "da_tra")
    elif loc in TRANG_THAI_DON:
        q = q.where(DonKsVtd.trang_thai == loc)
    else:
        q = q.where(DonKsVtd.trang_thai != "het_han")
    ds = db.execute(q.order_by(DonKsVtd.id.desc()).limit(300)).scalars().all()
    dem = dict(db.execute(select(DonKsVtd.trang_thai, func.count(DonKsVtd.id)).group_by(DonKsVtd.trang_thai)).all())
    return {"don": [ra_vtos(db, d, now) for d in ds], "dem": dem, "trang_thai": TRANG_THAI_DON,
            "vai": {"dh": u.role in VAI_DH, "kt": u.role in VAI_KE_TOAN, "sales": u.role in VAI_SALES + VAI_MIEN_PHAT,
                    "mien_phat": u.role in VAI_MIEN_PHAT}}


def dh_xac_nhan(db: Session, u: User, did: int, ma_ks: str, now: datetime | None = None) -> DonKsVtd:
    now = now or datetime.now()
    _quyen(u, VAI_DH, "chốt đơn với khách sạn")
    d = _don(db, did)
    if d.trang_thai != "da_tra":
        raise LoiDon("Chỉ chốt đơn đã thanh toán", 409)
    ma_ks = str(ma_ks or "").strip()
    if len(ma_ks) < 3:
        raise LoiDon("Ghi mã xác nhận của khách sạn")
    d.trang_thai, d.ma_xac_nhan_ks, d.xac_nhan_boi, d.xac_nhan_luc = "da_xac_nhan", ma_ks[:60], u.username, now
    R.audit(db, u.username, u.role, "ks_vtd_xac_nhan", f"don_ks_vtd:{d.ma}", after={"ma_ks": ma_ks[:60]})
    db.flush()
    return d


def dh_het_phong(db: Session, u: User, did: int, ly_do: str, now: datetime | None = None) -> DonKsVtd:
    now = now or datetime.now()
    _quyen(u, VAI_DH, "báo khách sạn hết phòng")
    d = _don(db, did)
    if d.trang_thai not in ("da_tra", "da_xac_nhan"):
        raise LoiDon("Chỉ báo hết phòng cho đơn đã thanh toán", 409)
    if len((ly_do or "").strip()) < 5:
        raise LoiDon("Ghi lý do (vd: khách sạn báo hết phòng hạng này)")
    _huy(db, d, u.username, "Khách sạn không giữ được phòng: " + ly_do.strip(), now, toan_bo=True)
    R.audit(db, u.username, u.role, "ks_vtd_het_phong", f"don_ks_vtd:{d.ma}", after={"so_hoan": int(d.so_hoan)})
    db.flush()
    return d


def sales_xac_nhan_hoan(db: Session, u: User, did: int, ghi_chu: str = "", now: datetime | None = None) -> DonKsVtd:
    _quyen(u, VAI_SALES + VAI_MIEN_PHAT, "xác nhận hoàn")
    d = _don(db, did)
    if d.hoan_tt != "cho_sales":
        raise LoiDon("Đơn không chờ Sales xác nhận hoàn", 409)
    d.hoan_tt = "cho_chi"
    d.hoan_ghi_chu = (((d.hoan_ghi_chu + "\n") if d.hoan_ghi_chu else "") + f"Sales {u.username}: xác nhận hoàn {_vnd(d.so_hoan)} đ {(ghi_chu or '').strip()}")[-1000:]
    R.audit(db, u.username, u.role, "ks_vtd_xac_nhan_hoan", f"don_ks_vtd:{d.ma}", after={"so_hoan": int(d.so_hoan)})
    db.flush()
    return d


def sales_mien_phat(db: Session, u: User, did: int, ly_do: str, now: datetime | None = None) -> DonKsVtd:
    """TP / GĐ Kinh doanh miễn phạt đơn đã hủy: hoàn đủ số khách đã trả."""
    _quyen(u, VAI_MIEN_PHAT, "miễn phạt (TP / GĐ Kinh doanh)")
    d = _don(db, did)
    if d.trang_thai != "da_huy":
        raise LoiDon("Chỉ miễn phạt đơn đã hủy", 409)
    if d.hoa_hong is not None:
        raise LoiDon("Đơn đã chốt hoa hồng — đã khóa", 409)
    if len((ly_do or "").strip()) < 5:
        raise LoiDon("Ghi lý do miễn phạt")
    tra = da_tra(db, d)
    if int(d.so_hoan) >= tra:
        raise LoiDon("Đơn đã được hoàn đủ — không có gì để miễn", 409)
    d.so_hoan, d.mien_phat_boi = tra, u.username
    d.hoan_tt = "cho_chi"
    d.hoan_ghi_chu = (((d.hoan_ghi_chu + "\n") if d.hoan_ghi_chu else "") + f"Miễn phạt bởi {u.username}: {ly_do.strip()}")[-1000:]
    _voucher_doi_chieu(db, d, now or datetime.now())   # KS-16: miễn phạt = hoàn đủ → voucher trả điểm lại
    R.audit(db, u.username, u.role, "ks_vtd_mien_phat", f"don_ks_vtd:{d.ma}", after={"so_hoan": tra, "ly_do": ly_do.strip()[:200]})
    db.flush()
    return d


def _doi_tuong_ks(db: Session, d: DonKsVtd) -> tuple[str, str]:
    from app.models.suppliers import Supplier
    k = db.get(KhachSanVtd, d.khach_san_id)
    s = db.get(Supplier, k.supplier_id) if k and k.supplier_id else None
    return (s.ten, s.code) if s else ((k.ten if k else "Khách sạn"), (k.ma if k else ""))


def _ghi_so(db: Session, u: User, ngay: date, mo_ta: str, lines: list[dict], ma_nguon: str, nghiep_vu: str) -> str:
    """Bút toán vào sổ CTCP Vietourist Holdings (công ty mẹ). Kỳ khóa / trùng sự kiện → lỗi, không ghi."""
    from app.models.core import Company
    from app.services import accounting as ACC
    try:
        if nghiep_vu == "thu_tien_khach":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type=NGUON_SO, source_ref=ma_nguon,
                               nghiep_vu="thu_tien_khach")
        elif nghiep_vu == "chi_tien":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type=NGUON_SO, source_ref=ma_nguon,
                               nghiep_vu="chi_tien")
        elif nghiep_vu == "khuyen_mai_rewards":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type=NGUON_SO, source_ref=ma_nguon,
                               nghiep_vu="khuyen_mai_rewards")
        elif nghiep_vu == "doanh_thu_hoa_hong":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type=NGUON_SO, source_ref=ma_nguon,
                               nghiep_vu="doanh_thu_hoa_hong")
        else:
            raise ValueError(f"nghiệp vụ {nghiep_vu} không thuộc đặt phòng")
    except ValueError as ex:
        raise LoiDon(f"Chưa ghi sổ được: {ex}", 409)
    me = db.execute(select(Company).where(Company.kind == "me").order_by(Company.id)).scalars().first()
    if me is not None:
        e.company_id = me.id
    return e.code


def kt_xac_nhan_qr(db: Session, u: User, tt_id: int, now: datetime | None = None) -> ThanhToanKsVtd:
    """Kế toán xác nhận tiền QR máy đã khớp → ghi sổ thu hộ (Nợ 1121 / Có 3388)."""
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "ghi sổ tiền vào (Kế toán)")
    t = db.get(ThanhToanKsVtd, tt_id)
    if t is None or t.kenh != "qr":
        raise LoiDon("Không có khoản QR này", 404)
    if t.trang_thai != "tu_khop":
        raise LoiDon("Khoản này không chờ Kế toán xác nhận", 409)
    d = db.get(DonKsVtd, t.don_id)
    tx = db.get(BankTransaction, t.bank_txn_id) if t.bank_txn_id else None
    ten, ma_dt = _doi_tuong_ks(db, d)
    t.but_toan = _ghi_so(db, u, ((tx.transaction_date if tx else None) or t.luc or now).date(), f"Thu hộ khách sạn — đặt phòng {d.ma} (QR)",
                         [{"account": TK_TIEN, "debit": int(t.so_tien), "note": d.ma},
                          {"account": TK_THU_HO, "credit": int(t.so_tien), "partner": ten, "partner_code": ma_dt, "note": d.ma}],
                         f"{d.ma}:tt{t.id}", "thu_tien_khach")
    t.trang_thai, t.xac_nhan_boi, t.xac_nhan_luc = "da_xac_nhan", u.username, now
    if tx is not None:
        tx.match_note = f"Đặt phòng {d.ma} — Kế toán {u.username} xác nhận · {t.but_toan}"
    R.audit(db, u.username, u.role, "ks_vtd_kt_xac_nhan_qr", f"don_ks_vtd:{d.ma}", after={"so_tien": int(t.so_tien), "but_toan": t.but_toan})
    db.flush()
    return t


def giao_dich_cho(db: Session, u: User, now: datetime | None = None) -> list[dict]:
    """Giao dịch QR tiền vào chưa khớp mà nội dung có mã đặt phòng KS… — Kế toán gán hoặc bỏ qua."""
    _quyen(u, VAI_KE_TOAN + ("chutich", "tgd", "bks", "robot_ks"), "xem giao dịch chờ")
    now = now or datetime.now()
    ra_ = []
    for t in db.execute(select(BankTransaction).where(BankTransaction.transfer_type == "in",
                                                      BankTransaction.match_status.in_(("cho_ke_toan", "chua_khop")),
                                                      BankTransaction.transaction_date >= now - timedelta(days=90))
                        .order_by(BankTransaction.transaction_date.desc()).limit(300)).scalars():
        m = MA_RE.search((t.content or "").upper().replace(" ", ""))
        if not m:
            continue
        d = db.execute(select(DonKsVtd).where(DonKsVtd.ma == m.group(0))).scalars().first()
        ra_.append({"txn_id": t.id, "luc": t.transaction_date.isoformat(timespec="minutes") if t.transaction_date else None,
                    "so_tien": int(round(float(t.amount or 0))), "noi_dung": (t.content or "")[:160], "ghi_chu": t.match_note or "",
                    "don_id": d.id if d else None, "ma": m.group(0), "tong": int(d.tong) if d else None,
                    "con_phai_tra": (int(d.tong) - da_tra(db, d)) if d else None,
                    "trang_thai_ten": TRANG_THAI_DON.get(d.trang_thai, d.trang_thai) if d else "Không có đơn mã này"})
    return ra_


def kt_gan_qr(db: Session, u: User, did: int, txn_id: int, now: datetime | None = None) -> DonKsVtd:
    """Kế toán gán một giao dịch chưa khớp (thiếu / thừa / sai nội dung) vào đơn → ghi sổ ngay."""
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "gán tiền vào (Kế toán)")
    d = _don(db, did)
    t = db.get(BankTransaction, txn_id)
    if t is None or t.transfer_type != "in":
        raise LoiDon("Không có giao dịch tiền vào này", 404)
    if t.match_status not in ("cho_ke_toan", "chua_khop"):
        raise LoiDon("Giao dịch đã được xử lý ở nơi khác", 409)
    if db.execute(select(ThanhToanKsVtd.id).where(ThanhToanKsVtd.bank_txn_id == t.id)).first():
        raise LoiDon("Giao dịch đã gán cho một đơn đặt phòng", 409)
    cap_nhat(db, d, now)
    tt = ThanhToanKsVtd(don_id=d.id, kenh="qr", so_tien=int(round(float(t.amount or 0))), trang_thai="da_xac_nhan",
                        bank_txn_id=t.id, luc=t.transaction_date or now, xac_nhan_boi=u.username, xac_nhan_luc=now,
                        ghi_chu="Kế toán gán tay")
    db.add(tt)
    db.flush()
    ten, ma_dt = _doi_tuong_ks(db, d)
    tt.but_toan = _ghi_so(db, u, (t.transaction_date or now).date(), f"Thu hộ khách sạn — đặt phòng {d.ma} (QR, gán tay)",
                          [{"account": TK_TIEN, "debit": int(tt.so_tien), "note": d.ma},
                           {"account": TK_THU_HO, "credit": int(tt.so_tien), "partner": ten, "partner_code": ma_dt, "note": d.ma}],
                          f"{d.ma}:tt{tt.id}", "thu_tien_khach")
    t.match_status, t.match_note = "da_khop", f"Đặt phòng {d.ma} — Kế toán {u.username} gán · {tt.but_toan}"
    db.flush()
    if d.trang_thai == "da_huy":
        # Tiền vào đơn đã hủy: toàn bộ khoản này phải trả lại khách.
        d.so_hoan = int(d.so_hoan) + int(tt.so_tien)
        d.hoan_tt = "cho_sales" if d.hoan_tt in ("", "da_hoan") else d.hoan_tt
    else:
        _sau_khi_tra(db, d, now)
    R.audit(db, u.username, u.role, "ks_vtd_kt_gan_qr", f"don_ks_vtd:{d.ma}", after={"so_tien": int(tt.so_tien), "txn": t.id})
    db.flush()
    return d


def kt_doi_soat(db: Session, u: User, tt_id: int, phi: int | None, now: datetime | None = None) -> ThanhToanKsVtd:
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "đối soát thẻ (Kế toán)")
    t = db.get(ThanhToanKsVtd, tt_id)
    if t is None or t.kenh not in ("onepay", "sepay"):
        raise LoiDon("Không có giao dịch thẻ này", 404)
    if t.trang_thai != "thanh_cong":
        raise LoiDon("Chỉ đối soát giao dịch cổng thẻ báo thành công", 409)
    if phi is None or int(phi) < 0 or int(phi) >= int(t.so_tien):
        raise LoiDon("Ghi phí thẻ theo sao kê cổng thẻ (0 nếu không trừ phí)")
    d = db.get(DonKsVtd, t.don_id)
    ten, ma_dt = _doi_tuong_ks(db, d)
    dong = [{"account": TK_TIEN, "debit": int(t.so_tien) - int(phi), "note": t.so_gd_cong or d.ma}]
    if int(phi):
        dong.append({"account": TK_PHI, "debit": int(phi), "note": f"Phí thẻ {d.ma}"})
    dong.append({"account": TK_THU_HO, "credit": int(t.so_tien), "partner": ten, "partner_code": ma_dt, "note": d.ma})
    t.but_toan = _ghi_so(db, u, now.date(), f"Thu hộ khách sạn — đặt phòng {d.ma} (thẻ, GD {t.so_gd_cong})", dong,
                         f"{d.ma}:tt{t.id}", "thu_tien_khach")
    t.phi_the = int(phi)
    t.trang_thai, t.xac_nhan_boi, t.xac_nhan_luc = "da_doi_soat", u.username, now
    R.audit(db, u.username, u.role, "ks_vtd_doi_soat_the", f"don_ks_vtd:{d.ma}", after={"so_tien": int(t.so_tien), "phi": int(phi), "but_toan": t.but_toan})
    db.flush()
    return t


def kt_chuyen_hoan(db: Session, u: User, did: int, ly_do: str, now: datetime | None = None) -> DonKsVtd:
    """Đơn có tiền nhưng không đi tiếp được (trả thiếu, trả khi đã hết giờ giữ) → hủy, hoàn đủ số đã nhận."""
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "chuyển hoàn (Kế toán)")
    d = cap_nhat(db, _don(db, did), now)
    if d.trang_thai not in ("cho_tra", "het_han"):
        raise LoiDon("Chỉ chuyển hoàn đơn chưa đủ tiền — đơn đã thanh toán đi đường hủy / hết phòng", 409)
    if da_tra(db, d) <= 0:
        raise LoiDon("Đơn chưa nhận đồng nào", 409)
    if len((ly_do or "").strip()) < 5:
        raise LoiDon("Ghi lý do")
    _huy(db, d, u.username, ly_do.strip(), now, toan_bo=True)
    R.audit(db, u.username, u.role, "ks_vtd_chuyen_hoan", f"don_ks_vtd:{d.ma}", after={"so_hoan": int(d.so_hoan)})
    db.flush()
    return d


def kt_da_hoan(db: Session, u: User, did: int, ghi_chu: str, now: datetime | None = None) -> DonKsVtd:
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "ghi đã hoàn (Kế toán)")
    d = _don(db, did)
    if d.hoan_tt != "cho_chi":
        raise LoiDon("Đơn chưa được Sales xác nhận hoàn", 409)
    if len((ghi_chu or "").strip()) < 3:
        raise LoiDon("Ghi chứng từ hoàn (mã hoàn OnePay / số UNC)")
    cho = db.execute(select(ThanhToanKsVtd.id).where(ThanhToanKsVtd.don_id == d.id, ThanhToanKsVtd.trang_thai.in_(("tu_khop", "thanh_cong")))).first()
    if cho:
        raise LoiDon("Còn khoản tiền vào chưa ghi sổ — ghi sổ / đối soát trước rồi mới hoàn", 409)
    lan = int(d.so_hoan) - int(d.da_hoan_tien or 0)
    if lan <= 0:
        raise LoiDon("Không còn số phải hoàn", 409)
    ten, ma_dt = _doi_tuong_ks(db, d)
    from app.models.accounting import JournalEntry
    n = (db.execute(select(func.count(JournalEntry.id)).where(JournalEntry.source_type == NGUON_SO,
                                                            JournalEntry.source_ref.like(f"{d.ma}:hoan%"))).scalar() or 0) + 1
    ma_ct = _ghi_so(db, u, now.date(), f"Hoàn khách — đặt phòng {d.ma} ({ghi_chu.strip()[:60]})",
                    [{"account": TK_THU_HO, "debit": lan, "partner": ten, "partner_code": ma_dt, "note": d.ma},
                     {"account": TK_TIEN, "credit": lan, "note": ghi_chu.strip()[:200]}], f"{d.ma}:hoan{n}", "chi_tien")
    d.da_hoan_tien = int(d.so_hoan)
    d.hoan_tt, d.hoan_boi, d.hoan_luc = "da_hoan", u.username, now
    d.hoan_ghi_chu = (((d.hoan_ghi_chu + "\n") if d.hoan_ghi_chu else "") + f"Kế toán {u.username}: hoàn {_vnd(lan)} đ · {ma_ct} · {ghi_chu.strip()}")[-1000:]
    R.audit(db, u.username, u.role, "ks_vtd_da_hoan", f"don_ks_vtd:{d.ma}", after={"so_hoan": lan, "but_toan": ma_ct})
    db.flush()
    return d


def kt_chot(db: Session, u: User, did: int, hoa_hong: int | None, now: datetime | None = None) -> DonKsVtd:
    """Sau ngày trả phòng (hoặc đơn hủy có giữ tiền): Kế toán gõ hoa hồng theo hợp đồng → phải trả khách sạn; khóa."""
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "chốt hoa hồng (Kế toán)")
    d = _don(db, did)
    if d.hoa_hong is not None:
        raise LoiDon("Đơn đã chốt — đã khóa", 409)
    if d.trang_thai == "da_xac_nhan":
        if now.date() < d.ra:
            raise LoiDon("Chốt sau ngày khách trả phòng", 409)
    elif d.trang_thai == "da_huy":
        if d.hoan_tt in ("cho_sales", "cho_chi"):
            raise LoiDon("Đơn còn chờ hoàn — hoàn xong mới chốt", 409)
    else:
        raise LoiDon("Chỉ chốt đơn đã xác nhận (khách đã ở) hoặc đơn đã hủy có giữ tiền", 409)
    if db.execute(select(ThanhToanKsVtd.id).where(ThanhToanKsVtd.don_id == d.id, ThanhToanKsVtd.trang_thai.in_(("tu_khop", "thanh_cong")))).first():
        raise LoiDon("Còn khoản tiền vào chưa ghi sổ / đối soát", 409)
    km = khuyen_mai(db, d)                     # KS-16: voucher VTD chịu → khách sạn vẫn nhận như không có voucher
    giu = da_tra(db, d) - int(d.so_hoan) + km
    if giu <= 0:
        raise LoiDon("Đơn không giữ lại đồng nào — không có gì để chốt", 409)
    if hoa_hong is None or not (0 <= int(hoa_hong) <= giu):
        raise LoiDon(f"Ghi hoa hồng theo hợp đồng, 0 – {_vnd(giu)} đ")
    if km > 0:
        ten, ma_dt = _doi_tuong_ks(db, d)
        d.km_but_toan = _ghi_so(db, u, now.date(), f"Voucher VTD Rewards — đặt phòng {d.ma} (Vietourist chịu thay khách)",
                                [{"account": TK_KM, "debit": km, "note": d.ma},
                                 {"account": TK_THU_HO, "credit": km, "partner": ten, "partner_code": ma_dt, "note": d.ma}],
                                f"{d.ma}:km", "khuyen_mai_rewards")
    d.hoa_hong, d.phai_tra_ks = int(hoa_hong), giu - int(hoa_hong)
    d.chot_boi, d.chot_luc = u.username, now
    R.audit(db, u.username, u.role, "ks_vtd_chot", f"don_ks_vtd:{d.ma}",
            after={"hoa_hong": int(hoa_hong), "phai_tra_ks": d.phai_tra_ks, "khuyen_mai": km, "but_toan_km": d.km_but_toan})
    db.flush()
    if d.phai_tra_ks == 0 and d.hoa_hong > 0:   # KS-16e: không còn gì trả khách sạn → ghi doanh thu hoa hồng ngay
        ghi_dt_hoa_hong(db, u, d, now.date())
    if d.phai_tra_ks > 0:                       # KS-16d: một đơn → một đề nghị chi trả khách sạn, TP Điều hành xác nhận
        k = db.get(KhachSanVtd, d.khach_san_id)
        d.payment_request_id = lap_de_nghi_chi_ncc(
            db, u, k.supplier_id if k else None, k.ten if k else "Khách sạn", int(d.phai_tra_ks),
            f"Trả khách sạn {k.ten if k else ''} — đơn {d.ma} ({d.vao:%d/%m}–{d.ra:%d/%m/%Y}), tiền thu hộ sau hoa hồng "
            f"{_vnd(int(hoa_hong))} đ", f"Đơn {d.ma}" + (f" · mã xác nhận KS {d.ma_xac_nhan_ks}" if d.ma_xac_nhan_ks else "")).id
        db.flush()
    return d


TK_DT_HH = "511"


def ghi_dt_hoa_hong(db: Session, u: User, d: DonKsVtd, ngay: date) -> str:
    """KS-16e (Chủ tịch 31/10/2026): doanh thu hoa hồng khách sạn — Nợ 3388 / Có 511, chưa gồm VAT (Kế toán xử lý
    VAT riêng). Ghi khi đề nghị chi trả khách sạn đã chi; không còn gì phải trả thì ghi ngay lúc chốt."""
    if d.dt_but_toan or not d.hoa_hong or int(d.hoa_hong) <= 0:
        return d.dt_but_toan
    ten, ma_dt = _doi_tuong_ks(db, d)
    hh = int(d.hoa_hong)
    d.dt_but_toan = _ghi_so(db, u, ngay, f"Doanh thu hoa hồng khách sạn — đặt phòng {d.ma} ({ten})",
                            [{"account": TK_THU_HO, "debit": hh, "partner": ten, "partner_code": ma_dt, "note": d.ma},
                             {"account": TK_DT_HH, "credit": hh, "note": d.ma}], f"{d.ma}:hh", "doanh_thu_hoa_hong")
    R.audit(db, u.username, u.role, "ks_vtd_ghi_dt_hoa_hong", f"don_ks_vtd:{d.ma}", after={"hoa_hong": hh, "but_toan": d.dt_but_toan})
    db.flush()
    return d.dt_but_toan


def _cho_ghi_dt(db: Session) -> list[dict]:
    """KS-16e — đơn đã chốt có hoa hồng, khoản trả khách sạn đã chi (hoặc đơn cũ chi tay) mà chưa có bút toán doanh thu."""
    from app.models.ops import PaymentRequest
    ra_ = []
    for d in db.execute(select(DonKsVtd).where(DonKsVtd.hoa_hong > 0, DonKsVtd.dt_but_toan == "").order_by(DonKsVtd.id)).scalars():
        pr = db.get(PaymentRequest, d.payment_request_id) if d.payment_request_id else None
        if cho_ghi_dt(d, pr.status if pr else None):
            k = db.get(KhachSanVtd, d.khach_san_id)
            ra_.append({"id": d.id, "ma": d.ma, "khach_san": k.ten if k else "", "hoa_hong": int(d.hoa_hong),
                        "chot_luc": d.chot_luc.isoformat(timespec="minutes") if d.chot_luc else None,
                        "de_nghi_chi": pr.code if pr else None})
    return ra_


def cho_ghi_dt(d: DonKsVtd, pr_status: str | None) -> bool:
    """Đã chốt, có hoa hồng, chưa ghi doanh thu, và khoản trả khách sạn đã chi (hoặc đơn chốt trước KS-16d, chi tay)."""
    return bool(d.hoa_hong and int(d.hoa_hong) > 0 and not d.dt_but_toan
                and (d.payment_request_id is None or pr_status == "da_chi"))


def kt_ghi_dt_hoa_hong(db: Session, u: User, did: int, now: datetime | None = None) -> DonKsVtd:
    """Nút «Ghi doanh thu hoa hồng» — Kế toán ghi bù cho đơn đã chốt trước KS-16e (hoặc lần ghi tự động hỏng)."""
    from app.models.ops import PaymentRequest
    now = now or datetime.now()
    _quyen(u, VAI_KE_TOAN, "ghi doanh thu hoa hồng (Kế toán)")
    d = _don(db, did)
    if d.dt_but_toan:
        raise LoiDon(f"Đã ghi doanh thu hoa hồng ({d.dt_but_toan})", 409)
    pr = db.get(PaymentRequest, d.payment_request_id) if d.payment_request_id else None
    if not cho_ghi_dt(d, pr.status if pr else None):
        raise LoiDon("Chỉ ghi khi đơn đã chốt có hoa hồng và khoản trả khách sạn đã chi", 409)
    ghi_dt_hoa_hong(db, u, d, now.date())
    return d


def sau_khi_chi_tra_ncc(db: Session, u: User, r) -> None:
    """Gọi từ ops.step(pay) cho loại tra_ncc_thu_ho: ghi Nợ 3388 / Có 511 hoa hồng của đơn khách sạn / đặt bàn gốc.
    Lỗi ghi sổ (kỳ khóa…) không chặn việc «Đã chi» — đơn nằm lại danh sách chờ ghi để Kế toán ghi bù."""
    from app.models.dat_ban import DonDatBan
    from app.services import dat_ban as DB
    try:
        d = db.execute(select(DonKsVtd).where(DonKsVtd.payment_request_id == r.id)).scalars().first()
        if d is not None:
            ghi_dt_hoa_hong(db, u, d, date.today())
            return
        b = db.execute(select(DonDatBan).where(DonDatBan.payment_request_id == r.id)).scalars().first()
        if b is not None:
            DB.ghi_dt_hoa_hong(db, u, b, date.today())
    except (LoiDon, DB.LoiDatBan) as ex:
        R.audit(db, "robot", "robot", "ghi_dt_hoa_hong_that_bai", f"dc:{r.code}", after={"ly_do": str(ex)})


def lap_de_nghi_chi_ncc(db: Session, u: User, supplier_id: int | None, ten_du_phong: str, so_tien: int, mo_ta: str,
                        chung_tu: str):
    """KS-16d — đề nghị chi loại «tra_ncc_thu_ho» (Nợ 3388 / Có 331 lúc duyệt) cho công ty mẹ; NCC lấy từ danh bạ."""
    from app.models.core import Company
    from app.models.suppliers import Supplier
    from app.services import ops as O
    s = db.get(Supplier, supplier_id) if supplier_id else None
    try:
        r = O.create_request(db, u, {"category": "tra_ncc_thu_ho", "_may_lap": True, **_ncc_vao(s, ten_du_phong), "amount": so_tien,
                                     "description": mo_ta[:300], "has_document": True, "document_ref": chung_tu[:200]})
    except ValueError as ex:
        raise LoiDon(f"Chưa lập được đề nghị chi: {ex}", 409)
    me = db.execute(select(Company).where(Company.kind == "me").order_by(Company.id)).scalars().first()
    if me is not None:
        r.company_id = me.id
    _robot_buoc(db, r, s)
    return r


def _ncc_vao(s, ten_du_phong: str) -> dict:
    ngh = " · ".join(x for x in (s.so_tai_khoan, s.ngan_hang, s.chu_tai_khoan) if x) if s is not None and s.so_tai_khoan else ""
    return {"supplier_name": (s.ten if s else ten_du_phong)[:160], "supplier_tax_code": (s.ma_so_thue or "") if s else "",
            "supplier_bank": ngh[:120]}


def _robot_buoc(db: Session, r, s) -> None:
    """KS-16d — robot kế toán (Chủ tịch 31/10/2026): xác nhận thay bộ phận + kiểm thay Kế toán. Đủ NCC (đã gắn, có MST,
    có số tài khoản) → chuyển TGĐ / Chủ tịch duyệt. Thiếu → DỪNG ở bước kiểm, ghi lý do để người bổ sung."""
    if r.status == "cho_tp":
        r.status, r.tp_by = "cho_kt", "robot"
    if r.status != "cho_kt":
        return
    thieu = ([] if s is not None else ["chưa gắn nhà cung cấp cho khách sạn / nhà hàng"]) + \
            ([x for x, co in (("thiếu MST", s.ma_so_thue), ("thiếu số tài khoản", s.so_tai_khoan)) if not (co or "").strip()]
             if s is not None else [])
    if thieu:
        r.robot_ghi_chu = ("Robot dừng: " + "; ".join(thieu) + " — bổ sung ở Nhà cung cấp rồi bấm «Robot kiểm lại»")[:300]
        R.audit(db, "robot", "robot", "de_nghi_chi_robot_dung", f"dc:{r.code}", after={"thieu": thieu})
    else:
        for k, v in _ncc_vao(s, r.supplier_name).items():
            setattr(r, k, v)
        r.status, r.kt_by, r.robot_ghi_chu = "cho_duyet", "robot", ""
        R.audit(db, "robot", "robot", "de_nghi_chi_robot_kiem", f"dc:{r.code}", after={"ncc": s.code, "so_tien": float(r.amount)})
    db.flush()


def robot_kiem_de_nghi(db: Session, u: User, r) -> str:
    """Nút «Robot kiểm lại»: đọc lại NCC từ khách sạn / nhà hàng của đơn gốc rồi chạy lại bước robot."""
    from app.models.dat_ban import DonDatBan
    from app.models.nha_hang import NhaHang
    from app.models.suppliers import Supplier
    if r.category != "tra_ncc_thu_ho" or r.status not in ("cho_tp", "cho_kt"):
        raise LoiDon("Chỉ chạy lại robot cho đề nghị trả NCC tiền thu hộ đang chờ kiểm", 409)
    sid = None
    d = db.execute(select(DonKsVtd).where(DonKsVtd.payment_request_id == r.id)).scalars().first()
    if d is not None:
        k = db.get(KhachSanVtd, d.khach_san_id)
        sid = k.supplier_id if k else None
    else:
        b = db.execute(select(DonDatBan).where(DonDatBan.payment_request_id == r.id)).scalars().first()
        if b is None:
            raise LoiDon("Không tìm thấy đơn gốc của đề nghị chi", 404)
        nh = db.get(NhaHang, b.nha_hang_id)
        sid = nh.supplier_id if nh else None
    _robot_buoc(db, r, db.get(Supplier, sid) if sid else None)
    R.audit(db, u.username, u.role, "de_nghi_chi_robot_kiem_lai", f"dc:{r.code}", after={"trang_thai": r.status})
    db.commit()
    return (f"{r.code}: robot đã kiểm — chuyển TGĐ / Chủ tịch duyệt" if r.status == "cho_duyet" else f"{r.code}: {r.robot_ghi_chu}")


def hang_ke_toan(db: Session, u: User, now: datetime | None = None) -> dict:
    """Màn Tiền & hoàn: tiền vào chờ ghi sổ, giao dịch chờ gán, hoàn, đơn thiếu tiền, chờ chốt, phải trả từng khách sạn."""
    _quyen(u, VAI_XEM_DON, "xem tiền đặt phòng")
    now = now or datetime.now()
    het_han_tat(db, now)
    db.commit()
    tt_cho = db.execute(select(ThanhToanKsVtd).where(ThanhToanKsVtd.trang_thai.in_(("tu_khop", "thanh_cong")))
                        .order_by(ThanhToanKsVtd.id)).scalars().all()
    don_ids = {t.don_id for t in tt_cho}
    hoan = db.execute(select(DonKsVtd).where(DonKsVtd.hoan_tt.in_(("cho_sales", "cho_chi"))).order_by(DonKsVtd.id)).scalars().all()
    thieu = [d for d in db.execute(select(DonKsVtd).where(DonKsVtd.trang_thai.in_(("cho_tra", "het_han")))).scalars()
             if da_tra(db, d) > 0]
    cho_chot = [d for d in db.execute(select(DonKsVtd).where(DonKsVtd.hoa_hong.is_(None),
                                                             DonKsVtd.trang_thai.in_(("da_xac_nhan", "da_huy")))).scalars()
                if (d.trang_thai == "da_xac_nhan" and d.ra <= now.date())
                or (d.trang_thai == "da_huy" and d.hoan_tt not in ("cho_sales", "cho_chi") and da_tra(db, d) > int(d.so_hoan))]
    don_tt = {d.id: d for d in db.execute(select(DonKsVtd).where(DonKsVtd.id.in_(don_ids or {0}))).scalars()}
    phai_tra: dict[int, dict] = {}
    for d in db.execute(select(DonKsVtd).where(DonKsVtd.phai_tra_ks.is_not(None))).scalars():
        k = db.get(KhachSanVtd, d.khach_san_id)
        o = phai_tra.setdefault(d.khach_san_id, {"khach_san": k.ten if k else "", "ma": k.ma if k else "", "so_don": 0,
                                                 "giu_lai": 0, "hoa_hong": 0, "phai_tra": 0, "khuyen_mai": 0, "de_nghi_chi": []})
        o["so_don"] += 1
        o["giu_lai"] += int(d.hoa_hong) + int(d.phai_tra_ks)
        o["hoa_hong"] += int(d.hoa_hong)
        o["phai_tra"] += int(d.phai_tra_ks)
        o["khuyen_mai"] += khuyen_mai(db, d) if d.km_but_toan else 0
        if d.payment_request_id:
            o["de_nghi_chi"].append({"don": d.ma, **_dnc(db, d.payment_request_id)})
    return {"tien_cho": [{**_tt_out(t), "don_id": t.don_id, "ma": don_tt[t.don_id].ma if t.don_id in don_tt else ""} for t in tt_cho],
            "giao_dich_cho": giao_dich_cho(db, u, now) if u.role in VAI_KE_TOAN + ("chutich", "tgd", "bks", "robot_ks") else [],
            "hoan": [ra_vtos(db, d, now) for d in hoan], "thieu": [ra_vtos(db, d, now) for d in thieu],
            "cho_chot": [ra_vtos(db, d, now) for d in cho_chot], "phai_tra_ks": list(phai_tra.values()),
            "cho_ghi_dt": _cho_ghi_dt(db),
            "vai": {"kt": u.role in VAI_KE_TOAN, "sales": u.role in VAI_SALES + VAI_MIEN_PHAT, "mien_phat": u.role in VAI_MIEN_PHAT}}
