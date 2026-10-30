"""KS-14 · Đặt phòng khách sạn VTD có thanh toán — hai nhóm cửa:

  /api/v1/cong/ks-vtd/don/*      — phía NGOÀI (phiên cổng): đặt, QR, thẻ, xem, hủy.
  /api/v1/khach-san-vtd/don/*    — phía VTOS: Điều hành (phòng trống, chốt), Sales (hoàn), Kế toán (tiền).
Kết quả OnePay đi chung đường /api/v1/onepay/tra-ve | /ipn với đặt bàn (mã giao dịch KS… rẽ về đây).
"""
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.api.v1.dat_ban import GOC_MAC_DINH, _goc
from app.api.v1.khach_san_vtd import _khach
from app.db.session import get_db
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.services import don_ks_vtd as S
from app.services import onepay as OP

router_cong = APIRouter(prefix="/api/v1/cong/ks-vtd/don", tags=["khach-san-vtd"])
router_vtos = APIRouter(prefix="/api/v1/khach-san-vtd/don", tags=["khach-san-vtd"])


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiDon as ex:
        raise HTTPException(ex.status, str(ex))


# ── phía khách ────────────────────────────────────────────────────────────────────────────────────
class ChonIn(BaseModel):
    goi_id: int
    so: int


class DatIn(BaseModel):
    vao: date
    ra: date
    nguoi_lon: int = 2
    tre_em: int = 0
    chon: list[ChonIn]
    ho_ten: str
    lien_he: str
    email: str = ""
    yeu_cau: str = ""
    dong_y: bool = False
    ma_voucher: str = ""            # KS-16: voucher VTD Rewards khách tự nhập (tối đa 5% đơn)


@router_cong.get("")
def cua_toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return {"don": _goi(S.ds_cua, db, tk)}


@router_cong.post("/dat/{kid:int}")
def dat(kid: int, data: DatIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    d = _goi(S.dat, db, tk, kid, data.model_dump())
    db.commit()
    return {"don": S.ra_khach(db, d), "message": f"Đã giữ phòng {S.GIU_PHUT} phút — thanh toán để hoàn tất"}


class KiemVoucherIn(BaseModel):
    ma: str
    tong: int


@router_cong.post("/kiem-voucher")
def kiem_voucher(data: KiemVoucherIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    """KS-16: nút «Áp dụng» ở bước thanh toán — chỉ kiểm, chưa giữ voucher (giữ khi bấm Đặt và thanh toán)."""
    from app.services import rewards as RW
    _khach(tk)
    try:
        v = RW.kiem_voucher_ks(db, tk, data.ma, max(0, int(data.tong)))
    except RW.LoiDiem as ex:
        raise HTTPException(400, str(ex))
    return {"ma": v.ma, "gia_tri": int(v.gia_tri), "tran": int(int(data.tong) * RW.TRAN_VOUCHER)}


@router_cong.get("/{ma}")
def mot(ma: str, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return _goi(S.mot_cua, db, tk, ma)


@router_cong.get("/{ma}/qr")
def qr(ma: str, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return _goi(S.qr, db, tk, ma)


@router_cong.post("/{ma}/the")
def the(ma: str, request: Request, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "") or "").split(",")[0].strip()
    return _goi(S.the_bat_dau, db, tk, ma, _goc(request), ip)   # SP-1: {"form"} (SePay) hoặc {"url"} (OnePay)


class HuyIn(BaseModel):
    ly_do: str = ""


@router_cong.post("/{ma}/huy")
def huy(ma: str, data: HuyIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    d = _goi(S.huy_boi_khach, db, tk, ma, data.ly_do)
    db.commit()
    so = int(d.so_hoan)
    return {"don": S.ra_khach(db, d),
            "message": (f"Đã hủy {d.ma} · Vietourist hoàn {S._vnd(so)} đ trong 3–7 ngày làm việc" if so else f"Đã hủy {d.ma}")}


# ── KS-15 · khách đã ở viết đánh giá (multipart: điểm thang 10 + tối đa 3 ảnh) ─────────────────────────
@router_cong.post("/{ma}/danh-gia")
async def danh_gia(ma: str, diem: int = Form(0), diem_sach: int = Form(0), diem_vi_tri: int = Form(0), diem_phong: int = Form(0),
                   diem_phuc_vu: int = Form(0), diem_gia: int = Form(0), di_cung: str = Form(""), tieu_de: str = Form(""),
                   nhan_xet: str = Form(""), dong_y: bool = Form(False), giu_anh: str = Form(""),
                   anh: list[UploadFile] = File(default=[]), tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    from app.services import danh_gia_ks as DGK
    _khach(tk)
    if len(anh) > DGK.ANH_TOI_DA:
        raise HTTPException(400, f"Tối đa {DGK.ANH_TOI_DA} ảnh")
    tep = [((f.filename or ""), await f.read()) for f in anh]
    giu = [int(x) for x in giu_anh.split(",") if x.strip().isdigit()]
    try:
        g = DGK.viet(db, tk, ma, {"diem": diem, "diem_sach": diem_sach, "diem_vi_tri": diem_vi_tri, "diem_phong": diem_phong,
                                  "diem_phuc_vu": diem_phuc_vu, "diem_gia": diem_gia, "di_cung": di_cung, "tieu_de": tieu_de,
                                  "nhan_xet": nhan_xet, "dong_y": dong_y}, tep, giu)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))
    return {"message": "Đã sửa đánh giá" if g.sua_luc else "Cảm ơn bạn — đánh giá đã hiện trên trang khách sạn",
            "don": _goi(S.mot_cua, db, tk, ma)}


# ── OnePay gọi về (rẽ từ đường chung của đặt bàn) ─────────────────────────────────────────────────
def onepay_tra_ve(db: Session, p: dict):
    kq = S.onepay_ket_qua(db, p)
    if kq is None:
        return RedirectResponse(f"{GOC_MAC_DINH}/cong?ks_vtd=&the=loi", status_code=303)
    d, t = kq
    goc = t.goc or GOC_MAC_DINH
    return RedirectResponse(f"{goc}/cong?ks_vtd={d.ma}&the={'ok' if t.trang_thai == 'thanh_cong' else 'loi'}", status_code=303)


def onepay_ipn(db: Session, p: dict):
    if S.onepay_ket_qua(db, p) is None:
        return PlainTextResponse("responsecode=0&desc=confirm-fail")
    return PlainTextResponse(OP.PHAN_HOI_IPN)


# ── phía VTOS ─────────────────────────────────────────────────────────────────────────────────────
def _xong(db: Session, u: User, d) -> dict:
    db.commit()
    return S.ra_vtos(db, d)


@router_vtos.get("")
def ds(loc: str = "", kid: int | None = None, u: User = Depends(require_roles(*S.VAI_XEM_DON)), db: Session = Depends(get_db)):
    return _goi(S.ds_vtos, db, u, loc, kid)


@router_vtos.get("/tien")
def tien(u: User = Depends(require_roles(*S.VAI_XEM_DON)), db: Session = Depends(get_db)):
    return _goi(S.hang_ke_toan, db, u)


@router_vtos.get("/phong-trong/{kid:int}")
def phong_trong(kid: int, tu: str = "", so_ngay: int = 14, u: User = Depends(require_roles(*S.VAI_XEM_DON)),
                db: Session = Depends(get_db)):
    return _goi(S.bang_phong_trong, db, u, kid, tu or None, so_ngay)


class PhongTrongIn(BaseModel):
    ngay: list[str]
    so_ban: int | None = None
    dong: bool = False


@router_vtos.post("/phong-trong/{lid:int}")
def luu_phong_trong(lid: int, data: PhongTrongIn, u: User = Depends(require_roles(*S.VAI_DH)), db: Session = Depends(get_db)):
    n = _goi(S.luu_phong_trong, db, u, lid, data.ngay, data.so_ban, data.dong)
    db.commit()
    return {"message": f"Đã lưu {n} đêm"}


class MaKsIn(BaseModel):
    ma_ks: str


class LyDoIn(BaseModel):
    ly_do: str = ""


class GhiChuIn(BaseModel):
    ghi_chu: str = ""


class GanIn(BaseModel):
    txn_id: int


class PhiIn(BaseModel):
    phi: int | None = None


class HoaHongIn(BaseModel):
    hoa_hong: int | None = None


@router_vtos.post("/{did:int}/xac-nhan")
def xac_nhan(did: int, data: MaKsIn, u: User = Depends(require_roles(*S.VAI_DH)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.dh_xac_nhan, db, u, did, data.ma_ks))


@router_vtos.post("/{did:int}/het-phong")
def het_phong(did: int, data: LyDoIn, u: User = Depends(require_roles(*S.VAI_DH)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.dh_het_phong, db, u, did, data.ly_do))


@router_vtos.post("/{did:int}/sales-hoan")
def sales_hoan(did: int, data: GhiChuIn, u: User = Depends(require_roles(*(S.VAI_SALES + S.VAI_MIEN_PHAT))), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.sales_xac_nhan_hoan, db, u, did, data.ghi_chu))


@router_vtos.post("/{did:int}/mien-phat")
def mien_phat(did: int, data: LyDoIn, u: User = Depends(require_roles(*S.VAI_MIEN_PHAT)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.sales_mien_phat, db, u, did, data.ly_do))


@router_vtos.post("/tt/{tid:int}/xac-nhan")
def kt_xac_nhan(tid: int, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    t = _goi(S.kt_xac_nhan_qr, db, u, tid)
    db.commit()
    return {"message": f"Đã ghi sổ {t.but_toan}"}


@router_vtos.post("/tt/{tid:int}/doi-soat")
def kt_doi_soat(tid: int, data: PhiIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    t = _goi(S.kt_doi_soat, db, u, tid, data.phi)
    db.commit()
    return {"message": f"Đã đối soát · {t.but_toan}"}


@router_vtos.post("/{did:int}/gan-qr")
def kt_gan(did: int, data: GanIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.kt_gan_qr, db, u, did, data.txn_id))


@router_vtos.post("/{did:int}/chuyen-hoan")
def kt_chuyen_hoan(did: int, data: LyDoIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.kt_chuyen_hoan, db, u, did, data.ly_do))


@router_vtos.post("/{did:int}/da-hoan")
def kt_da_hoan(did: int, data: GhiChuIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.kt_da_hoan, db, u, did, data.ghi_chu))


@router_vtos.post("/{did:int}/chot")
def kt_chot(did: int, data: HoaHongIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    return _xong(db, u, _goi(S.kt_chot, db, u, did, data.hoa_hong))
