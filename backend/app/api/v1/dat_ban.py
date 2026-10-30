"""DT-2 · Đặt bàn nhà hàng có thanh toán — ba nhóm cửa:

  /api/v1/cong/dat-ban/*      — phía NGOÀI (phiên cổng): khách, cổ đông, đại lý, CTV đặt / trả / hủy.
  /api/v1/onepay/*            — OnePay gọi về (trình duyệt và IPN). Không phiên — tin bằng CHỮ KÝ HMAC.
  /api/v1/dat-ban-nha-hang/*  — phía VTOS: Kế toán xác nhận tiền, đối soát thẻ, chốt doanh số, ghi đã hoàn;
                                Sales xác nhận hoàn / hủy.
"""
import time
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.db.session import get_db
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.services import dat_ban as S
from app.services import onepay as OP

router = APIRouter(prefix="/api/v1/cong/dat-ban", tags=["dat-ban"])
router_onepay = APIRouter(prefix="/api/v1/onepay", tags=["dat-ban"])
router_vtos = APIRouter(prefix="/api/v1/dat-ban-nha-hang", tags=["dat-ban"])

GOC_MAC_DINH = "https://kh.vietourist.vn"
# Phanh cho hai cửa OnePay gọi về (không phiên): chữ ký sai thì không đổi gì, phanh chặn dội.
CUA_SO_GIAY, TOI_DA_TRONG_CUA_SO = 600, 60
_LUOT: dict = defaultdict(list)


def _phanh(req: Request) -> None:
    ip = (req.client.host if req.client else "") or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_TRONG_CUA_SO:
        _LUOT[ip] = v
        raise HTTPException(429, "Quá nhiều lượt từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(bay_gio)
    _LUOT[ip] = v


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiDatBan as ex:
        raise HTTPException(ex.status, str(ex))


def _goc(request: Request) -> str:
    """Tên miền cổng đang dùng — CHỈ nhận tên miền của Vietourist (không mở đường chuyển hướng tùy ý)."""
    o = (request.headers.get("origin") or "").rstrip("/")
    host = o.split("://", 1)[-1].split(":", 1)[0].lower()
    if o.startswith("https://") and (host == "vietourist.vn" or host.endswith(".vietourist.vn")):
        return o
    if host in ("localhost", "127.0.0.1"):
        return o
    return GOC_MAC_DINH


# ---------------------------------------------------------------- phía người đặt
class DatBanIn(BaseModel):
    nha_hang_id: int
    thuc_don_id: int
    ngay: date | None = None
    gio: str = ""
    nguoi_lon: int = 0
    tre_em: int = 0
    cach_tt: str = ""
    ten_khach: str = ""
    dien_thoai: str = ""
    ghi_chu: str = ""
    dong_y_chinh_sach: bool = False
    dong_y_khach: bool = False


@router.get("")
def cua_toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _goi(S._nguoi_dat, db, tk)
    return {"dat_ban": S.ds_cua(db, tk), "tham_so": S.tham_so(db), "the_bat": OP.bat()}


@router.get("/nha-hang")
def ds_nha_hang(tinh: str = "", am_thuc: str = "", gia_toi_da: int = 0, q: str = "", chi_dat: bool = False, trang: int = 1, loai: str = "", bac: str = "", tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai),
                db: Session = Depends(get_db)):
    """Danh mục nhà hàng đang mở trên cổng — cho mọi người được đặt (khách, cổ đông, đại lý, CTV)."""
    from app.services import nha_hang as NH
    _goi(S._nguoi_dat, db, tk)
    return NH.danh_sach_cong(db, tinh, am_thuc, gia_toi_da, q, chi_dat, trang, loai=loai, bac=bac)


@router.get("/nha-hang/{nid}")
def mot_nha_hang(nid: int, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    """AT-1: trang một nhà hàng (giới thiệu; nơi mở đặt có thực đơn) — sau khi nhận OTP."""
    from app.services import nha_hang as NH
    _goi(S._nguoi_dat, db, tk)
    try:
        return NH.mot_nha_hang_cong(db, nid)[1]
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))


@router.post("")
def dat(data: DatBanIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    d = _goi(S.tao, db, tk, data.model_dump())
    return {"message": f"Đã gửi đặt bàn {d.ma}. Nhà hàng nhận bàn xong sẽ hiện thanh toán.", "ma": d.ma,
            "dat_ban": S.ds_cua(db, tk)}


@router.get("/{ma}/qr")
def qr(ma: str, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(S.qr, db, tk, ma)


@router.post("/{ma}/the")
def the(ma: str, request: Request, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "") or "").split(",")[0].strip()
    return {"url": _goi(S.onepay_bat_dau, db, tk, ma, _goc(request), ip)}


class ThayDoiIn(BaseModel):
    ngay: date | None = None
    gio: str = ""
    nguoi_lon: int | None = None
    tre_em: int | None = None


@router.post("/{ma}/thay-doi")
def thay_doi(ma: str, data: ThayDoiIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    d = _goi(S.thay_doi, db, tk, ma, data.ngay, data.gio, data.nguoi_lon, data.tre_em)
    msg = "Đã gửi thay đổi — chờ nhà hàng nhận" if d.thay_doi else "Đã cập nhật đơn"
    if d.hoan_tt == "cho_sales" and int(d.so_hoan or 0) > int(d.da_hoan_tien or 0):
        msg += f" · phần trả dư {int(d.so_hoan) - int(d.da_hoan_tien or 0):,} đ sẽ được hoàn".replace(",", ".")
    return {"message": msg, "dat_ban": S.ds_cua(db, tk)}


class HuyIn(BaseModel):
    ly_do: str = ""


@router.post("/{ma}/huy")
def huy(ma: str, data: HuyIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    d = _goi(S.huy_boi_nguoi_dat, db, tk, ma, data.ly_do)
    msg = (f"Đã hủy {d.ma}. Hoàn {int(d.so_hoan):,} đ".replace(",", ".") + " — Sales xác nhận, Kế toán hoàn trong 7 ngày làm việc."
           if d.so_hoan else f"Đã hủy {d.ma}.")
    return {"message": msg, "dat_ban": S.ds_cua(db, tk)}


# ---------------------------------------------------------------- AT-3 · đánh giá sao (người đặt, đơn «khách đã dùng»)
@router.post("/{ma}/danh-gia")
async def danh_gia(ma: str, diem: int = Form(0), diem_mon: int = Form(0), diem_phuc_vu: int = Form(0), diem_khong_gian: int = Form(0),
                   diem_gia: int = Form(0), nhan_xet: str = Form(""), dong_y: bool = Form(False), giu_anh: str = Form(""),
                   anh: list[UploadFile] = File(default=[]), tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    from app.services import danh_gia_nh as DG
    if len(anh) > DG.ANH_TOI_DA:
        raise HTTPException(400, f"Tối đa {DG.ANH_TOI_DA} ảnh")
    tep = [((f.filename or ""), await f.read()) for f in anh]
    giu = [int(x) for x in giu_anh.split(",") if x.strip().isdigit()]
    try:
        g = DG.viet(db, tk, ma, {"diem": diem, "diem_mon": diem_mon, "diem_phuc_vu": diem_phuc_vu, "diem_khong_gian": diem_khong_gian,
                                 "diem_gia": diem_gia, "nhan_xet": nhan_xet, "dong_y": dong_y}, tep, giu)
    except DG.LoiDanhGia as ex:
        raise HTTPException(ex.status, str(ex))
    return {"message": "Đã sửa đánh giá" if g.sua_luc else "Cảm ơn bạn — đánh giá đã hiện trên trang nhà hàng",
            "dat_ban": S.ds_cua(db, tk)}


# ---------------------------------------------------------------- OnePay gọi về
@router_onepay.get("/tra-ve")
def tra_ve(request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    p = dict(request.query_params)
    from app.api.v1 import don_ks_vtd as KV   # KS-14: mã giao dịch KS… là đơn đặt phòng khách sạn VTD
    if KV.S.cua_minh(p):
        return KV.onepay_tra_ve(db, p)
    kq = S.onepay_ket_qua(db, p)
    if kq is None:
        return RedirectResponse(f"{GOC_MAC_DINH}/cong?the=loi", status_code=303)
    d, t = kq
    goc = t.goc or GOC_MAC_DINH
    return RedirectResponse(f"{goc}/cong?dat_ban={d.ma}&the={'ok' if t.trang_thai == 'thanh_cong' else 'loi'}", status_code=303)


@router_onepay.get("/ipn")
def ipn(request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    from app.api.v1 import don_ks_vtd as KV   # KS-14: mã giao dịch KS… là đơn đặt phòng khách sạn VTD
    if KV.S.cua_minh(dict(request.query_params)):
        return KV.onepay_ipn(db, dict(request.query_params))
    kq = S.onepay_ket_qua(db, dict(request.query_params))
    if kq is None:
        return PlainTextResponse("responsecode=0&desc=confirm-fail")
    return PlainTextResponse(OP.PHAN_HOI_IPN)


# ---------------------------------------------------------------- phía VTOS
@router_vtos.get("")
def tong(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return S.tong_vtos(db, u)


class GanIn(BaseModel):
    txn_id: int


@router_vtos.post("/{did}/qr")
def gan_qr(did: int, data: GanIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    d = _goi(S.kt_gan_qr, db, u, did, data.txn_id)
    db.commit()
    return {"message": f"Đã xác nhận tiền vào cho {d.ma}", **S.tong_vtos(db, u)}


class DoiSoatIn(BaseModel):
    phi: int | None = None


@router_vtos.post("/the/{tid}/doi-soat")
def doi_soat(tid: int, data: DoiSoatIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    _goi(S.kt_doi_soat, db, u, tid, data.phi)
    db.commit()
    return {"message": "Đã đối soát giao dịch thẻ", **S.tong_vtos(db, u)}


class ChotIn(BaseModel):
    doanh_so: int


@router_vtos.post("/{did}/chot")
def chot(did: int, data: ChotIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    d = _goi(S.kt_chot, db, u, did, data.doanh_so)
    db.commit()
    return {"message": f"Đã chốt doanh số {d.ma} — đã khóa", **S.tong_vtos(db, u)}


class GhiChuIn(BaseModel):
    ghi_chu: str = ""


@router_vtos.post("/{did}/xac-nhan-hoan")
def xac_nhan_hoan(did: int, data: GhiChuIn, u: User = Depends(require_roles(*(S.VAI_SALES + S.VAI_MIEN_PHAT))),
                  db: Session = Depends(get_db)):
    _goi(S.sales_xac_nhan_hoan, db, u, did, data.ghi_chu)
    db.commit()
    return {"message": "Đã xác nhận — chuyển Kế toán hoàn tiền", **S.tong_vtos(db, u)}


@router_vtos.post("/{did}/da-hoan")
def da_hoan(did: int, data: GhiChuIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    _goi(S.kt_da_hoan, db, u, did, data.ghi_chu)
    db.commit()
    return {"message": "Đã ghi đã hoàn tiền", **S.tong_vtos(db, u)}


class HuyNoiBoIn(BaseModel):
    ly_do: str = ""
    mien_phat: bool = False


@router_vtos.post("/{did}/huy")
def huy_noi_bo(did: int, data: HuyNoiBoIn, u: User = Depends(require_roles(*(S.VAI_SALES + S.VAI_MIEN_PHAT))),
               db: Session = Depends(get_db)):
    d = _goi(S.sales_huy, db, u, did, data.ly_do, data.mien_phat)
    db.commit()
    return {"message": f"Đã hủy {d.ma}", **S.tong_vtos(db, u)}
