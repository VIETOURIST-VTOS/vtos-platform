"""DT-1 · Cổng đối tác VTD — Đại lý và Cộng tác viên bán hàng (Chủ tịch duyệt bản xem thử 27/10/2026).

BỐN ĐIỀU ĐÃ CHỐT
  1. NỐI HỒ SƠ do NGƯỜI DUYỆT xác nhận. Máy chỉ GỢI Ý: khớp mã số thuế trước, rồi số điện thoại đã
     xác thực. Nhiều đối tác cùng khớp thì máy không tự chọn. Chưa nối = cổng không hiện số liệu nào —
     tài khoản ngoài chỉ thấy đúng những booking mang `doi_tac_id` của đối tác đã nối.
  2. ĐẠI LÝ GIỮ CHỖ QUA ĐỦ CỔNG như Điều hành tạo booking (`tours.cong_tao_booking`: tour đã duyệt,
     dự toán, sức chứa). Không giảm giá trên cổng. Người tiếp nhận LUÔN là bàn Sales Admin LẺ; doanh số không
     vào chỉ tiêu nhân viên. Hết hạn giữ chỗ mà chưa cọc thì robot trả chỗ về tour như mọi booking.
  3. GIÁ = giá bán công bố (như khách lẻ) + hoa hồng D06. Cổng không bao giờ đưa giá vốn, lãi tour.
  4. CÔNG NỢ HAI CHIỀU HIỆN RIÊNG, KHÔNG BÙ TRỪ. «Đại lý còn phải trả» là tiền booking chưa được kế
     toán xác nhận; «Vietourist còn phải trả» là hoa hồng ĐÃ CHỐT chưa chi. Bù trừ cần thỏa thuận và
     chứng từ — không phải việc của một màn hình.

CTV không giữ chỗ, không thu tiền: giới thiệu khách thành lead vào hàng chờ Sales, kèm dấu thời gian
làm chứng cứ nguồn.
"""
import math
import re
from datetime import date, datetime, timedelta

from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.core import Tour, Booking, ServiceRequest, Alert, User
from app.models.crm import Lead
from app.models.cong_ngoai import TaiKhoanNgoai, LOAI_DOI_TAC
from app.models.cong_khach import YeuCauKhach
from app.models.doi_tac_ban_hang import DoiTacBanHang, NHAN_LOAI
from app.services import cong_khach as K
from app.services import cong_ngoai as C
from app.services import rules as R
from app.services.zalo import norm_phone

KENH_CTV = "CTV giới thiệu"
GIU_CHO_TOI_DA_NGAY = 20
GIOI_THIEU_TOI_DA_NGAY = 20
SAP_HET_GIO = 48
SO_THANG_D06 = 4
LOAI_CONG = ("dai_ly", "ctv_ban_hang")      # NCC: đợt sau


class LoiDoiTac(ValueError):
    def __init__(self, thong_diep: str, status: int = 400, ma: str = ""):
        super().__init__(thong_diep)
        self.status, self.ma = status, ma


def _so(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _hom_nay() -> date:
    return K._hom_nay()


# ---------------------------------------------------------------- nối hồ sơ (phía VTOS)

def _tom_tat(db: Session, dt: DoiTacBanHang) -> dict:
    so_bk = db.execute(select(func.count(Booking.id)).where(Booking.doi_tac_id == dt.id, Booking.cancelled.is_(False))).scalar_one()
    so_tk = db.execute(select(func.count(TaiKhoanNgoai.id)).where(TaiKhoanNgoai.doi_tac_id == dt.id)).scalar_one()
    return {"id": dt.id, "ma": dt.ma, "ten": dt.ten, "loai": dt.loai, "loai_ten": NHAN_LOAI.get(dt.loai, dt.loai),
            "ma_so_thue": dt.ma_so_thue, "dien_thoai": dt.dien_thoai, "so_booking": int(so_bk), "so_tai_khoan": int(so_tk),
            "con_hop_tac": dt.dang_hieu_luc(_hom_nay())}


def goi_y(db: Session, tk: TaiKhoanNgoai) -> dict:
    """Đối tác máy gợi ý nối. MST trước (đủ 10 số), rồi SĐT đã xác thực. Không tự quyết."""
    if tk.loai != "doi_tac":
        return {"khop": [], "theo": "", "tu_chon": None}
    ds = db.execute(select(DoiTacBanHang).order_by(DoiTacBanHang.id)).scalars().all()
    mst = _so(tk.ma_so_thue)
    khop, theo = [], ""
    if len(mst) >= 10:
        khop, theo = [d for d in ds if _so(d.ma_so_thue) == mst], "mã số thuế"
    if not khop and tk.dien_thoai:
        khop, theo = [d for d in ds if d.dien_thoai and norm_phone(d.dien_thoai) == tk.dien_thoai], "số điện thoại"
    ra = [_tom_tat(db, d) for d in khop]
    return {"khop": ra, "theo": theo if ra else "", "tu_chon": ra[0]["id"] if len(ra) == 1 else None}


def thong_tin_noi(db: Session, tk: TaiKhoanNgoai) -> dict:
    dt = db.get(DoiTacBanHang, tk.doi_tac_id) if tk.doi_tac_id else None
    return {"doi_tac": _tom_tat(db, dt) if dt else None, "goi_y": goi_y(db, tk) if dt is None else None,
            "co_cong": tk.loai_doi_tac in LOAI_CONG}


def ds_doi_tac(db: Session, q: str = "") -> list[dict]:
    cau = select(DoiTacBanHang).order_by(DoiTacBanHang.ten)
    if q.strip():
        k = f"%{q.strip()}%"
        cau = cau.where(or_(DoiTacBanHang.ten.ilike(k), DoiTacBanHang.ma.ilike(k), DoiTacBanHang.ma_so_thue.ilike(k)))
    return [{"id": d.id, "ma": d.ma, "ten": d.ten, "loai_ten": NHAN_LOAI.get(d.loai, d.loai), "ma_so_thue": d.ma_so_thue}
            for d in db.execute(cau.limit(30)).scalars()]


def _ma_moi(db: Session) -> str:
    n = db.execute(select(func.count(DoiTacBanHang.id))).scalar_one() + 1
    while db.execute(select(DoiTacBanHang.id).where(DoiTacBanHang.ma == f"DT-{n:04d}")).first():
        n += 1
    return f"DT-{n:04d}"


def noi(db: Session, u: User, tk: TaiKhoanNgoai, hanh_dong: str, doi_tac_id: int | None = None,
        duyet: bool = False) -> TaiKhoanNgoai:
    """hanh_dong: «noi» (vào đối tác có sẵn) · «tao_moi» (lập đối tác từ hồ sơ khai) · «go» (gỡ nối).
    `duyet` = nối xong duyệt luôn hồ sơ đang chờ (một lần bấm «Duyệt & nối»)."""
    if tk.loai != "doi_tac":
        raise LoiDoiTac("Chỉ tài khoản đối tác mới nối với đối tác bán hàng")
    if not C.xu_ly_duoc(u, tk):
        raise LoiDoiTac("Hồ sơ này không thuộc phần bạn được duyệt", 403)
    if tk.loai_doi_tac not in LOAI_CONG:
        raise LoiDoiTac("Cổng nhà cung cấp làm ở đợt sau — chưa nối được")
    if tk.trang_thai in ("tu_choi", "khoa"):
        raise LoiDoiTac("Tài khoản đã bị từ chối hoặc khoá — mở lại trước khi nối")
    truoc = tk.doi_tac_id
    if hanh_dong == "go":
        tk.doi_tac_id = None
    elif hanh_dong == "noi":
        dt = db.get(DoiTacBanHang, int(doi_tac_id or 0))
        if dt is None:
            raise LoiDoiTac("Không có đối tác này")
        if not dt.dang_hieu_luc(_hom_nay()):
            raise LoiDoiTac(f"{dt.ten} đã dừng hợp tác — không nối được")
        if (dt.loai == "ctv_ban_hang") != (tk.loai_doi_tac == "ctv_ban_hang"):
            raise LoiDoiTac(f"Hồ sơ khai {LOAI_DOI_TAC[tk.loai_doi_tac]} nhưng {dt.ten} là {NHAN_LOAI.get(dt.loai, dt.loai)} — chọn đúng đối tác")
        tk.doi_tac_id = dt.id
    elif hanh_dong == "tao_moi":
        from app.services.nguoi_ban_hang import tao_doi_tac
        ten = (tk.ten_don_vi or tk.ho_ten or "").strip()
        if not ten:
            raise LoiDoiTac("Hồ sơ chưa có tên đơn vị / họ tên — yêu cầu bổ sung trước")
        try:
            dt = tao_doi_tac(db, u, _ma_moi(db), ten, "ctv_ban_hang" if tk.loai_doi_tac == "ctv_ban_hang" else "dai_ly",
                             lien_he=tk.ho_ten or "", dien_thoai=tk.dien_thoai or "", ma_so_thue=tk.ma_so_thue or "",
                             ghi_chu=f"Lập từ hồ sơ cổng đối tác #{tk.id}")
        except ValueError as ex:
            raise LoiDoiTac(str(ex))
        tk.doi_tac_id = dt.id
    else:
        raise LoiDoiTac("Thao tác không hợp lệ")
    R.audit(db, u.username, u.role, f"tai_khoan_ngoai_{hanh_dong}_doi_tac", f"tai_khoan_ngoai:{tk.id}",
            before={"doi_tac_id": truoc}, after={"doi_tac_id": tk.doi_tac_id})
    db.flush()
    if duyet and tk.trang_thai == "cho_duyet":
        if not tk.doi_tac_id:
            raise LoiDoiTac("Nối đối tác trước rồi mới duyệt")
        C.xu_ly(db, u, tk, "duyet")       # tự commit
    else:
        db.commit()
    db.refresh(tk)
    return tk


# ---------------------------------------------------------------- phía đối tác

def doi_tac_cua(db: Session, tk: TaiKhoanNgoai) -> DoiTacBanHang:
    """Chặn mọi cửa đối tác: đúng loại, đang hoạt động, ĐÃ NỐI và đối tác còn hợp tác."""
    if tk.loai != "doi_tac":
        raise LoiDoiTac("Chức năng này dành cho tài khoản đối tác", 403)
    if tk.trang_thai != "hoat_dong":
        raise LoiDoiTac("Tài khoản đối tác chưa được duyệt", 403)
    dt = db.get(DoiTacBanHang, tk.doi_tac_id) if tk.doi_tac_id else None
    if dt is None:
        raise LoiDoiTac("Đang chờ Vietourist nối hồ sơ — chưa có số liệu", 403, "cho_noi")
    if not dt.dang_hieu_luc(_hom_nay()):
        raise LoiDoiTac("Hợp tác đã dừng — liên hệ Vietourist", 403, "dung")
    return dt


def la_ctv(dt: DoiTacBanHang) -> bool:
    return dt.loai == "ctv_ban_hang"


def _dai_ly(db: Session, tk: TaiKhoanNgoai) -> DoiTacBanHang:
    dt = doi_tac_cua(db, tk)
    if la_ctv(dt):
        raise LoiDoiTac("Cộng tác viên không giữ chỗ — dùng «Giới thiệu khách»", 403)
    return dt


def _ctv(db: Session, tk: TaiKhoanNgoai) -> DoiTacBanHang:
    dt = doi_tac_cua(db, tk)
    if not la_ctv(dt):
        raise LoiDoiTac("Chức năng giới thiệu khách dành cho cộng tác viên", 403)
    return dt


def _ky(d: date) -> str:
    return f"{d:%Y-%m}"


def _lui_thang(d: date, n: int) -> date:
    y, m = d.year, d.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def hoa_hong(db: Session, tk: TaiKhoanNgoai, so_thang: int = SO_THANG_D06) -> dict:
    """Hoa hồng D06 của đúng đối tác đã nối — số do Kế toán tính và chốt; cổng chỉ hiện."""
    from app.services import hoa_hong_d06 as HH
    dt = doi_tac_cua(db, tk)
    hn = _hom_nay()
    thang = []
    for i in range(so_thang):
        ky = _ky(_lui_thang(hn, i))
        th = HH.tong_hop(db, ky, hn)
        rows = [r for r in th["dong"] if r["doi_tac_id"] == dt.id]
        ht = HH.hinh_thuc_cua(db, dt.id, ky)
        da_chot = bool(rows) and all(r["trang_thai"] == "da_chot" for r in rows)
        tong = sum(r["tong"] for r in rows)
        da_tra = sum(r["da_tra"] for r in rows)
        if not rows:
            tt = "Chưa có doanh số đủ điều kiện"
        elif not th["dang_bat"]:
            tt = "Tính thử — D06 chưa có hiệu lực"
        elif da_chot and da_tra >= tong:
            tt = "Đã chi"
        elif da_chot:
            tt = "Đã chốt · chờ chi"
        else:
            tt = "Dự kiến"
        thang.append({"ky": ky, "hinh_thuc": HH.HINH_THUC.get(ht, ht) if ht else "Chưa chọn hình thức",
                      "doanh_so": sum(r["doanh_so"] for r in rows), "hoa_hong": tong, "da_tra": da_tra,
                      "con_phai_tra": (tong - da_tra) if da_chot else 0, "da_chot": da_chot, "trang_thai": tt,
                      "dang_bat": th["dang_bat"]})
    ky0 = _ky(hn)
    don = _don_hoa_hong(db, dt, hn, so_thang)
    ht0 = HH.hinh_thuc_cua(db, dt.id, ky0)
    bac = HH.BAC.get(ht0)
    return {"hinh_thuc": ht0, "hinh_thuc_ten": HH.HINH_THUC.get(ht0, "Chưa chọn hình thức") if ht0 else "Chưa chọn hình thức",
            "bac": [list(b) for b in bac["bac"]] if bac else [],
            "bac_hien_tai": HH.bac_hien_tai(thang[0]["doanh_so"], ht0) if bac else None,
            "hieu_luc_tu": (HH.hieu_luc_tu(db).isoformat() if HH.hieu_luc_tu(db) else None), "thang": thang,
            "doanh_so_thang": thang[0]["doanh_so"], "don": don, "v3": HH.la_v3(db, ky0)}


def _don_hoa_hong(db: Session, dt: DoiTacBanHang, hn: date, so_thang: int) -> list[dict]:
    """KS-16h: hoa hồng TỪNG ĐƠN (phần của đơn trong bậc lũy tiến tháng) + đơn tạm giữ kèm lý do."""
    from app.services import hoa_hong_d06 as HH
    from app.models.nguon_doi_soat import DongDoiSoat, BangDoiSoat, VuViecDoiTac
    ra = []
    vv = {v.booking_ma: v for v in db.execute(select(VuViecDoiTac).where(VuViecDoiTac.doi_tac_id == dt.id,
                                                                            VuViecDoiTac.trang_thai == "mo")).scalars()}
    for i in range(so_thang):
        ky = _ky(_lui_thang(hn, i))
        th = HH.tong_hop(db, ky, hn)
        for r in th["dong"]:
            if r["doi_tac_id"] != dt.id:
                continue
            da_tra = r["da_tra"] >= r["tong"] > 0
            for x in r["nguon"]:
                if x["booking"] in vv:
                    tt, ten = "khieu_nai", f"Đang khiếu nại {vv[x['booking']].ma}"
                elif da_tra:
                    tt, ten = "da_tra", "Đã trả"
                elif r["trang_thai"] == "da_chot":
                    tt, ten = "da_chot", "Đã chốt · chờ chi"
                else:
                    tt, ten = "du_kien", "Dự kiến" if th["dang_bat"] else "Tính thử"
                ra.append({"ky": ky, "ma": x["booking"], "ten": x.get("ten_tour") or "", "doanh_so": x["doanh_so"],
                           "gia_sau_giam": x.get("gia_sau_giam"), "vat_pct": x.get("vat_pct"),
                           "bac_bps": x.get("bac_bps", []), "hoa_hong": x.get("hoa_hong", 0), "trang_thai": tt, "trang_thai_ten": ten})
        if i == 0:
            for c in th["chua_du"]:
                if c["doi_tac_id"] == dt.id:
                    ra.append({"ky": ky, "ma": c["booking"], "ten": "", "doanh_so": None, "hoa_hong": None, "bac_bps": [],
                               "trang_thai": "tam_giu", "trang_thai_ten": f"Tạm giữ: {c['ly_do']}"})
    return ra


def nguon_cua_ctv(db: Session, tk: TaiKhoanNgoai) -> dict:
    from app.services import nguon_don as ND
    dt = _ctv(db, tk)
    m = ND.ma_ctv(dt)
    return {"ma_ctv": m, "link": f"https://kh.vietourist.vn/{m}", "giu_ngay": ND.GIU_NGAY, "nguon": ND.ds_cua_ctv(db, dt)}


def khieu_nai_nguon(db: Session, tk: TaiKhoanNgoai, booking_ma: str, khach_sdt: str, noi_dung: str):
    from app.services import nguon_don as ND
    dt = doi_tac_cua(db, tk)
    try:
        v = ND.mo_vu_viec(db, dt, "nguon", noi_dung, booking_ma=booking_ma, khach_sdt=khach_sdt)
    except ND.LoiNguon as ex:
        raise LoiDoiTac(str(ex))
    db.commit()
    return v


def vu_viec(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    from app.services import nguon_don as ND
    return ND.ds_vu_viec(db, doi_tac_cua(db, tk).id)


def doi_soat(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    from app.services import doi_soat_doi_tac as DS
    return DS.cua_doi_tac(db, doi_tac_cua(db, tk))


def doi_soat_dong_y(db: Session, tk: TaiKhoanNgoai, bang_id: int, dong_id: int | None):
    from app.services import doi_soat_doi_tac as DS
    try:
        DS.dong_y(db, doi_tac_cua(db, tk), bang_id, dong_id)
    except DS.LoiDoiSoat as ex:
        raise LoiDoiTac(str(ex), ex.status)


def doi_soat_khieu_nai(db: Session, tk: TaiKhoanNgoai, bang_id: int, dong_id: int, noi_dung: str):
    from app.services import doi_soat_doi_tac as DS
    try:
        return DS.khieu_nai(db, doi_tac_cua(db, tk), bang_id, dong_id, noi_dung)
    except DS.LoiDoiSoat as ex:
        raise LoiDoiTac(str(ex), ex.status)


def _bk_cua(db: Session, dt: DoiTacBanHang) -> list[Booking]:
    return db.execute(select(Booking).where(Booking.doi_tac_id == dt.id).order_by(Booking.created_at.desc(), Booking.id.desc())
                      .limit(300)).scalars().all()


def _coc_con(b: Booking, tien: dict) -> int:
    """Phần cọc còn thiếu (theo tiền kế toán đã xác nhận)."""
    return max(int(math.ceil(tien["gia_tri"] * float(b.deposit_pct or 0) / 100)) - tien["da_thu"], 0)


def _bk_out(db: Session, b: Booking, hn: date, now: datetime) -> dict:
    t = db.get(Tour, b.tour_id) if b.tour_id else None
    pv, muc = K._phuc_vu(b, t, hn)
    tien = K._tien(db, b)
    dang_giu = bool(not b.cancelled and b.giu_cho_den and not b.giu_cho_het and tien["da_thu"] == 0 and t and t.start_date > hn)
    if dang_giu:
        pv, muc = "Đang giữ chỗ", "warn"
    if b.giu_cho_het and tien["da_thu"] == 0 and not b.cancelled:
        pv, muc = "Hết hạn giữ chỗ – chỗ đã trả về tour", "bad"
    con_gio = (b.giu_cho_den - now).total_seconds() / 3600 if b.giu_cho_den else None
    return {"ma": b.code, "ten": t.name if t else (b.services_note or "Dịch vụ"), "ma_tour": t.code if t else "",
            "khoi_hanh": t.start_date.isoformat() if t else None, "khach": b.customer_name, "so_khach": b.pax,
            "phuc_vu": pv, "muc": muc, "huy": b.cancelled, "dang_giu": dang_giu,
            "giu_den": b.giu_cho_den.isoformat(timespec="minutes") if b.giu_cho_den else None,
            "con_gio": round(con_gio, 1) if con_gio is not None else None,
            "coc_con": _coc_con(b, tien) if not b.cancelled else 0, **tien}


def bookings(db: Session, tk: TaiKhoanNgoai, now: datetime | None = None) -> list[dict]:
    dt = _dai_ly(db, tk)
    now = now or datetime.now()
    hn = now.date()
    return [_bk_out(db, b, hn, now) for b in _bk_cua(db, dt)]


def cong_no(db: Session, tk: TaiKhoanNgoai, now: datetime | None = None) -> dict:
    """Hai chiều, hai số, không bù trừ."""
    ds = [b for b in bookings(db, tk, now) if not b["huy"] and b["con_lai"] > 0 and not (b["muc"] == "bad")]
    hh = hoa_hong(db, tk)
    vtd = [{"ky": m["ky"], "hoa_hong": m["hoa_hong"], "da_tra": m["da_tra"], "con_phai_tra": m["con_phai_tra"]}
           for m in hh["thang"] if m["con_phai_tra"] > 0]
    return {"dai_ly_phai_tra": sum(b["con_lai"] for b in ds), "booking": ds,
            "vietourist_phai_tra": sum(x["con_phai_tra"] for x in vtd), "hoa_hong": vtd}


def ban_lam_viec(db: Session, tk: TaiKhoanNgoai, now: datetime | None = None) -> dict:
    dt = doi_tac_cua(db, tk)
    now = now or datetime.now()
    hh = hoa_hong(db, tk, 1)
    m = hh["thang"][0]
    ra = {"doi_tac": {"ma": dt.ma, "ten": dt.ten, "loai": dt.loai, "loai_ten": NHAN_LOAI.get(dt.loai, dt.loai)},
          "ctv": la_ctv(dt), "d06": {"ky": m["ky"], "doanh_so": m["doanh_so"], "hoa_hong": m["hoa_hong"], "trang_thai": m["trang_thai"],
                                     "dang_bat": m["dang_bat"], "hinh_thuc": hh["hinh_thuc_ten"], "bac_hien_tai": hh["bac_hien_tai"]}}
    if la_ctv(dt):
        gt = gioi_thieu_ds(db, tk)
        ra.update({"gioi_thieu": gt[:5], "dang_cho": sum(1 for g in gt if g["trang_thai"].startswith("Đã gửi"))})
        return ra
    bk = bookings(db, tk, now)
    no = [b for b in bk if not b["huy"] and b["con_lai"] > 0 and b["muc"] != "bad"]
    sap = sorted([b for b in bk if b["dang_giu"] and b["con_gio"] is not None and b["con_gio"] <= SAP_HET_GIO], key=lambda b: b["con_gio"])
    ra.update({"phai_tra": sum(b["con_lai"] for b in no), "so_booking_no": len(no), "sap_het": sap})
    return ra


def tours(db: Session, tk: TaiKhoanNgoai, q: str = "", tu_ngay: date | None = None) -> dict:
    doi_tac_cua(db, tk)
    hh = hoa_hong(db, tk, 1)
    return {"tour": K.tours(db, q, tu_ngay, gioi_han=80), "hoa_hong": hh["hinh_thuc_ten"], "bac_hien_tai": hh["bac_hien_tai"]}


PHONG_LE = "kd_le"


def sale_admin_le(db: Session) -> User | None:
    """BÀN SALES ADMIN LẺ — một bàn chăm sóc mọi đại lý và CTV (Chủ tịch 27/10/2026). Nhận diện:
    vai `sales_admin` ĐANG HOẠT ĐỘNG và phòng ban Kinh doanh Lẻ (trên tài khoản, hoặc trên hồ sơ nhân sự
    nối với tài khoản). Cửa nhập là màn HCNS gán phòng ban — máy không đoán người."""
    from app.models.hr import Employee, DEPARTMENTS
    ten_le = DEPARTMENTS[PHONG_LE]
    ds = db.execute(select(User).where(User.role == "sales_admin", User.active.is_(True)).order_by(User.id)).scalars().all()
    for u in ds:
        if (u.department or "").strip() in (PHONG_LE, ten_le):
            return u
        e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        if e is not None and e.department == PHONG_LE:
            return u
    return None


def _sale_admin(db: Session) -> User:
    u = sale_admin_le(db)
    if u is None:
        raise LoiDoiTac("Vietourist chưa có bàn Sales Admin lẻ tiếp nhận — giữ chỗ tạm đóng, vui lòng gọi Sales", 409)
    return u


def giu_cho(db: Session, tk: TaiKhoanNgoai, tour_id: int, ten_khach: str, sdt_khach: str, nguoi_lon: int, tre_em: int,
            ghi_chu: str = "", now: datetime | None = None) -> Booking:
    """Đại lý tự giữ chỗ = một booking thật, QUA ĐỦ CỔNG như Điều hành tạo booking."""
    from fastapi import HTTPException
    from app.services import tours as TS
    from app.services import bookings as BK
    dt = _dai_ly(db, tk)
    now = now or datetime.now()
    ten_khach = (ten_khach or "").strip()[:120]
    if not ten_khach:
        raise LoiDoiTac("Ghi tên khách đại diện")
    sdt = norm_phone(sdt_khach or "")
    if len(sdt) != 10 or not sdt.startswith("0"):
        raise LoiDoiTac("Ghi số điện thoại khách đại diện (10 số)")
    nl, te = int(nguoi_lon or 0), int(tre_em or 0)
    if nl < 1 or te < 0 or nl + te > 200:
        raise LoiDoiTac("Ít nhất 1 người lớn; tổng không quá 200 khách")
    trong_ngay = db.execute(select(func.count(Booking.id)).where(
        Booking.doi_tac_id == dt.id, Booking.source == f"Đại lý cổng · {dt.ma}"[:60],
        Booking.created_at >= now - timedelta(days=1))).scalar_one()
    if trong_ngay >= GIU_CHO_TOI_DA_NGAY:
        raise LoiDoiTac("Đã giữ nhiều chỗ trong 24 giờ — liên hệ bàn Sales Admin lẻ để giữ thêm", 429)
    try:
        o = K.tour(db, int(tour_id or 0))          # đang mở bán, còn chỗ, chưa khởi hành, có giá
    except K.LoiKhach as ex:
        raise LoiDoiTac(str(ex))
    t = db.get(Tour, o["id"])
    try:
        TS.cong_tao_booking(db, t, nl + te, 0)
    except HTTPException as ex:
        db.rollback()
        d = ex.detail
        raise LoiDoiTac(d.get("message") if isinstance(d, dict) else str(d), 422)
    sa = _sale_admin(db)
    gia_nl = int(o["gia"])
    gia_te = int(o["gia_tre_em"] or gia_nl)
    nguon = f"Đại lý cổng · {dt.ma}"[:60]
    ghi = (ghi_chu or "").strip()[:500]
    note = f"[Cổng đối tác {now:%d/%m %H:%M}] {dt.ten} ({dt.ma}) giữ chỗ qua tài khoản #{tk.id}" + (f" · {ghi}" if ghi else "")
    r = ServiceRequest(tour_id=t.id, sales_id=sa.id, customer_name=ten_khach, customer_phone=sdt, source=nguon,
                       care_note=note, pax=nl + te, created_at=now)
    db.add(r); db.flush()
    n = db.execute(select(func.count()).select_from(Booking)).scalar() + 1
    b = Booking(code=f"BK{now:%y%m}{n:04d}", tour_id=t.id, request_id=r.id, sales_id=sa.id, created_by=sa.id, doi_tac_id=dt.id,
                customer_name=ten_khach, customer_phone=sdt, source=nguon, care_note=note, pax=nl + te, adl=nl, chd=te,
                amount=gia_nl * nl + gia_te * te, discount=0, counts_for_target=False, sla_minutes=0, sla_ok=True,
                company_id=t.company_id, created_at=now)
    db.add(b); db.flush(); r.booking_id = b.id
    BK.init_terms(db, b, t)
    db.add(Alert(kind="dai_ly_giu_cho", level="info", ref=b.code[:60],
                 message=f"{dt.ten} giữ {nl + te} chỗ {t.code} qua cổng đối tác ({b.code}) — giữ đến {b.giu_cho_den:%d/%m %H:%M} · tiếp nhận: {sa.full_name}",
                 to_roles="nv_dh,tp_dh,sales_admin"))
    R.audit(db, f"cong:{tk.id}", "doi_tac", "dai_ly_giu_cho", f"booking:{b.code}",
            after={"doi_tac": dt.ma, "tour": t.code, "nguoi_lon": nl, "tre_em": te, "amount": b.amount, "giu_den": str(b.giu_cho_den)})
    db.commit(); db.refresh(b)
    return b


def qr(db: Session, tk: TaiKhoanNgoai, ma: str, muc: str = "") -> dict:
    """QR chuyển khoản cho booking CỦA ĐẠI LÝ — cùng phép tính và cùng tài khoản nhận như cổng khách."""
    from app.services.payments import paid_amount
    from app.services import vietqr as Q
    dt = _dai_ly(db, tk)
    b = db.execute(select(Booking).where(Booking.code == ma, Booking.doi_tac_id == dt.id)).scalars().first()
    if b is None:
        raise LoiDoiTac("Không tìm thấy booking này của đại lý", 404)
    if b.cancelled:
        raise LoiDoiTac("Booking đã hủy — không thanh toán")
    gia_tri = int(round(float(b.amount or 0) - float(b.discount or 0)))
    da_nop = int(round(float(paid_amount(db, b.id))))
    con = gia_tri - da_nop
    if gia_tri <= 0 or con <= 0:
        raise LoiDoiTac("Booking đã thanh toán đủ — không cần chuyển thêm")
    coc = int(math.ceil(gia_tri * float(b.deposit_pct or 0) / 100)) - da_nop
    coc = coc if 0 < coc < con else 0
    muc = muc if muc in ("coc", "du") else ("coc" if coc else "du")
    if muc == "coc" and not coc:
        raise LoiDoiTac("Booking đã đủ cọc — chọn thanh toán phần còn lại")
    so_tien = coc if muc == "coc" else con
    ba = K.tai_khoan_qr(db)
    bin_ = Q.bin_cua(ba.bank_name) if ba is not None and ba.account_number else None
    if bin_ is None:
        raise LoiDoiTac("Thanh toán QR chưa mở — liên hệ bàn Sales Admin lẻ để nhận thông tin chuyển khoản")
    return {"ma": b.code, "muc": muc, "so_tien": so_tien, "coc": coc, "con_lai": con, "da_nop": da_nop,
            "payload": Q.payload(bin_, ba.account_number, so_tien, b.code), "noi_dung": Q.noi_dung_sach(b.code),
            "ngan_hang": ba.bank_name, "so_tk": ba.account_number, "chu_tk": ba.account_name, "tu_khop": muc == "du"}


# ---------------------------------------------------------------- CTV giới thiệu khách

def gioi_thieu(db: Session, tk: TaiKhoanNgoai, tour_id: int | None, ten_khach: str, sdt_khach: str, so_khach: int,
               ghi_chu: str, dong_y: bool, now: datetime | None = None) -> YeuCauKhach:
    from app.services.leads import upsert_lead, canon_channel
    dt = _ctv(db, tk)
    now = now or datetime.now()
    if not dong_y:
        raise LoiDoiTac("Đánh dấu ô xác nhận: khách đã đồng ý để bạn chuyển thông tin liên hệ cho Vietourist")
    ten_khach = (ten_khach or "").strip()[:120]
    if not ten_khach:
        raise LoiDoiTac("Ghi tên khách")
    sdt = norm_phone(sdt_khach or "")
    if len(sdt) != 10 or not sdt.startswith("0"):
        raise LoiDoiTac("Ghi số điện thoại khách (10 số)")
    if not 1 <= int(so_khach or 0) <= 500:
        raise LoiDoiTac("Số khách từ 1 đến 500")
    trong_ngay = db.execute(select(func.count(YeuCauKhach.id)).where(
        YeuCauKhach.tai_khoan_id == tk.id, YeuCauKhach.tao_luc >= now - timedelta(days=1))).scalar_one()
    if trong_ngay >= GIOI_THIEU_TOI_DA_NGAY:
        raise LoiDoiTac("Đã gửi nhiều giới thiệu trong 24 giờ — Sales sẽ xử lý dần", 429)
    ten_tour = "Chưa chọn tour"
    if tour_id:
        try:
            o = K.tour(db, int(tour_id))
        except K.LoiKhach as ex:
            raise LoiDoiTac(str(ex))
        ten_tour = f"{o['ma']} · {o['ten']} · {date.fromisoformat(o['khoi_hanh']):%d/%m/%Y}"
    ghi = (ghi_chu or "").strip()[:1000]
    kenh = canon_channel(KENH_CTV)
    # Khách đã có Sales chăm (lead kênh khác đã giao người) → để TP Kinh doanh xét nguồn. KHÔNG nói
    # điều ấy cho CTV: cổng không thành máy dò khách hàng của Vietourist.
    da_co = db.execute(select(Lead.id).where(Lead.phone == sdt, Lead.channel != kenh, Lead.sales_id.is_not(None))).first()
    lead, _moi = upsert_lead(db, "cong_doi_tac", {"phone": sdt, "name": ten_khach, "channel": KENH_CTV,
                                                  "received_at": now.isoformat(), "interest": ten_tour[:200]})
    # Giao thẳng bàn Sales Admin lẻ (Chủ tịch 27/10/2026). Lead đã có người phụ trách thì giữ nguyên;
    # chưa có bàn SA lẻ thì vẫn nhận giới thiệu (không làm mất nguồn của CTV), để trống người phụ trách.
    sa = sale_admin_le(db)
    if sa is not None and lead.sales_id is None:
        lead.sales_id = sa.id
    dong = (f"[CTV giới thiệu {now:%d/%m/%Y %H:%M}] {dt.ten} ({dt.ma}, tài khoản #{tk.id}): {ten_tour} · {so_khach} khách"
            + " · khách đã đồng ý chuyển liên hệ" + (" · khách đã có Sales chăm (máy xét nguồn theo luật 7 ngày)" if da_co else "")
            + (f" · {ghi}" if ghi else ""))
    cu = (lead.note or "").strip()
    lead.note = (((cu + "\n") if cu else "") + dong)[-2000:]
    yc = YeuCauKhach(tai_khoan_id=tk.id, loai="gioi_thieu", tour_id=int(tour_id) if tour_id else None, ten_tour=ten_tour[:200],
                     so_khach=int(so_khach), dien_thoai=sdt, ghi_chu=ghi, lead_id=lead.id, ten_khach=ten_khach, tao_luc=now)
    db.add(yc); db.flush()
    # KS-16h: giữ nguồn 30 ngày theo luật máy tự xử (services/nguon_don.py). Ghi kết quả vào lead cho Sales thấy.
    from app.services import nguon_don as ND
    nd = ND.ghi_nguon(db, dt, sdt, "gioi_thieu", now, ten_khach, yc.id)
    if nd is not None:
        lead.note = (lead.note + ("\n" if lead.note else "") + (
            f"[Nguồn đơn] Giữ nguồn CTV {dt.ten} ({ND.ma_ctv(dt)}) đến {nd.den:%d/%m/%Y} — booking của khách sẽ tự gắn CTV"
            if nd.trang_thai == "giu" else f"[Nguồn đơn] CTV {dt.ten} không giữ được nguồn: {nd.ly_do}"))[-2000:]
    R.audit(db, f"cong:{tk.id}", "doi_tac", "ctv_gioi_thieu", f"lead:{lead.id}", after={"doi_tac": dt.ma, "tour": ten_tour[:80]})
    db.commit(); db.refresh(yc)
    return yc


def gioi_thieu_ds(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    _ctv(db, tk)
    ds = db.execute(select(YeuCauKhach).where(YeuCauKhach.tai_khoan_id == tk.id, YeuCauKhach.loai == "gioi_thieu")
                    .order_by(YeuCauKhach.tao_luc.desc()).limit(100)).scalars().all()
    leads = {l.id: l for l in db.execute(select(Lead).where(Lead.id.in_([y.lead_id for y in ds if y.lead_id]))).scalars()} if ds else {}
    ra = []
    for y in ds:
        l = leads.get(y.lead_id)
        ra.append({"id": y.id, "gui_luc": y.tao_luc.isoformat(timespec="minutes"), "khach": y.ten_khach, "so_khach": y.so_khach,
                   "tour": y.ten_tour, "trang_thai": K.TRANG_THAI_LEAD.get(l.status if l else "moi", "Đã gửi")})
    return ra
