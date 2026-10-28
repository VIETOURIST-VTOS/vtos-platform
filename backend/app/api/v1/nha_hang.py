"""KH-2 · Màn VTOS «Nhà hàng (cổng khách)» — Điều hành nhập, TP Điều hành bật hiện cổng (DT-2b, 28/10/2026)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.core import User
from app.api.deps import require_roles
from app.services import nha_hang as N

router = APIRouter(prefix="/api/v1/nha-hang", tags=["nha-hang"])


def _loi(ex: N.LoiNhaHang):
    raise HTTPException(400, str(ex))


@router.get("")
def danh_sach(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    return N.danh_sach_vtos(db)


class NhaHangIn(BaseModel):
    ten: str
    tinh_thanh: str = ""
    khu_vuc: str = ""
    am_thuc: str = "Việt Nam"
    gio_phuc_vu: str = ""
    tien_ich: str = ""
    mo_ta: str = ""
    ghi_chu_noi_bo: str = ""


@router.post("")
def tao(data: NhaHangIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        nh = N.luu_nha_hang(db, u, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": nh.id, "message": f"Đã thêm {nh.ma} · {nh.ten}"}


@router.post("/{nid}")
def sua(nid: int, data: NhaHangIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        nh = N.luu_nha_hang(db, u, data.model_dump(), nid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": nh.id, "message": "Đã lưu" + ("" if nh.hien_cong or not nh.tat_ly_do else " — nhà hàng đang chờ TP Điều hành bật lại")}


class ThucDonIn(BaseModel):
    ten: str
    loai: str = "set"
    gia_nguoi_lon: float | None = None
    gia_tre_em: float | None = None
    so_khach_toi_thieu: int = 1
    mo_ta: str = ""
    dieu_kien: str = ""
    dieu_kien_huy: str = ""
    tu_ngay: date | None = None
    den_ngay: date | None = None
    dang_ban: bool = True


@router.post("/{nid}/thuc-don")
def them_thuc_don(nid: int, data: ThucDonIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        td = N.luu_thuc_don(db, u, nid, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": td.id, "message": f"Đã thêm gói {td.ten}"}


@router.post("/{nid}/thuc-don/{tid}")
def sua_thuc_don(nid: int, tid: int, data: ThucDonIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        td = N.luu_thuc_don(db, u, nid, data.model_dump(), tid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": td.id, "message": f"Đã lưu gói {td.ten}"}


class BatIn(BaseModel):
    bat: bool


@router.post("/{nid}/hien-cong")
def hien_cong(nid: int, data: BatIn, u: User = Depends(require_roles(*N.VAI_BAT)), db: Session = Depends(get_db)):
    try:
        nh = N.bat_hien(db, u, nid, data.bat)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{nh.ten}: " + ("đang hiện trên cổng khách" if nh.hien_cong else "đã tắt khỏi cổng khách")}


class NgungIn(BaseModel):
    ngung: bool


@router.post("/{nid}/ngung")
def ngung(nid: int, data: NgungIn, u: User = Depends(require_roles(*(N.VAI_BAT + ("tp_dh",)))), db: Session = Depends(get_db)):
    try:
        nh = N.ngung(db, u, nid, data.ngung)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{nh.ten}: " + ("đã ngừng hợp tác" if nh.ngung else "hợp tác lại")}
