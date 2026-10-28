"""KS-1 · Khách sạn qua OTA — hai nhóm cửa:

  /api/v1/cong/khach-san/*  — phía NGOÀI (khách hàng, đối tác, cổ đông): đòi PHIÊN CỔNG NGOÀI.
  /api/v1/khach-san-ota/*   — phía VTOS: Chủ tịch nhập link, bật / tắt; Ban Kiểm soát, TGĐ xem.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.db.session import get_db
from app.models.core import User
from app.models.cong_ngoai import TaiKhoanNgoai
from app.services import khach_san_ota as S

router = APIRouter(prefix="/api/v1/cong/khach-san", tags=["khach-san-ota"])
router_vtos = APIRouter(prefix="/api/v1/khach-san-ota", tags=["khach-san-ota"])


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiOta as ex:
        raise HTTPException(ex.status, str(ex))


# ---------------------------------------------------------------- phía ngoài

@router.get("/ota")
def ds_ota(san_pham: str = "khach_san", tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    """VB-1: `san_pham=ve_may_bay` trả OTA vé máy bay (chỉ cổng Khách hàng, Cổ đông)."""
    return {"ota": _goi(S.ds_cong, db, tk, san_pham)}


class ChuyenIn(BaseModel):
    ota: str
    request_id: str
    diem_den: str = ""
    nhan_phong: str | None = None
    tra_phong: str | None = None
    so_phong: int = 1
    nguoi_lon: int = 2
    tre_em: int = 0
    # VB-1 · vé máy bay — máy chủ chọn bộ trường theo SẢN PHẨM của OTA, không theo trình duyệt
    diem_di: str = ""
    ngay_di: str | None = None
    ngay_ve: str | None = None
    em_be: int = 0
    hang_ve: str = "pho_thong"


@router.post("/chuyen")
def chuyen(data: ChuyenIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    d = data.model_dump()
    return _goi(S.chuyen, db, tk, d.pop("ota"), d.pop("request_id"), d)


@router.get("/lich-su")
def lich_su(san_pham: str = "khach_san", tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    if san_pham == "ve_may_bay":
        return {"luot": _goi(S.lich_su, db, tk, san_pham), "dat_phong": []}
    return {"luot": _goi(S.lich_su, db, tk), "dat_phong": _goi(S.dat_phong_xac_minh, db, tk)}


# ---------------------------------------------------------------- phía VTOS

@router_vtos.get("")
def ds(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return S.ds_quan_tri(db, u)


@router_vtos.get("/luot")
def luot(so_ngay: int = 7, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return S.thong_ke(db, so_ngay)


class PhapNhanIn(BaseModel):
    ma: str
    ten: str
    quoc_gia: str = ""
    ghi_chu: str = ""


@router_vtos.post("/phap-nhan")
def them_phap_nhan(data: PhapNhanIn, u: User = Depends(require_roles(*S.VAI_SUA)), db: Session = Depends(get_db)):
    p = _goi(S.them_phap_nhan, db, u, data.ma, data.ten, data.quoc_gia, data.ghi_chu)
    return {"message": f"Đã thêm pháp nhân {p.ten}", **S.ds_quan_tri(db, u)}


class SuaIn(BaseModel):
    trang_thai: str | None = None
    phap_nhan_id: int | None = None
    link: str | None = None
    ten_mien: str | None = None
    duong_dan: str | None = None
    da_kiem_link: bool | None = None
    duoc_dung_web: bool | None = None
    subid_cho_phep: bool | None = None
    subid_tham_so: str | None = None
    loai_link: str | None = None   # VB-1: hoa_hong | cong_khai (chỉ vé máy bay)
    bang_chung: str | None = None
    ghi_chu: str | None = None


@router_vtos.post("/{ota_id}")
def sua(ota_id: int, data: SuaIn, u: User = Depends(require_roles(*S.VAI_SUA)), db: Session = Depends(get_db)):
    o = _goi(S.sua, db, u, ota_id, data.model_dump())
    return {"message": f"Đã lưu {o.ten}" + (" — đang tắt" if not o.bat else ""), **S.ds_quan_tri(db, u)}


class BatIn(BaseModel):
    bat: bool


@router_vtos.post("/{ota_id}/bat")
def bat(ota_id: int, data: BatIn, u: User = Depends(require_roles(*S.VAI_SUA)), db: Session = Depends(get_db)):
    o = _goi(S.bat_tat, db, u, ota_id, data.bat)
    return {"message": f"Đã {'bật' if o.bat else 'tắt'} {o.ten}", **S.ds_quan_tri(db, u)}
