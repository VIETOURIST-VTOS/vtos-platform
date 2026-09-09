"""Quyết toán tour theo điều hành – xem, phân loại dòng chưa có giá vốn.

Nạp tệp đi qua màn hình Nạp dữ liệu chung (bộ nạp 'quyet_toan_tour'), không có cơ chế nạp thứ hai.
Ở đây chỉ có phần ĐỌC và phần PHÂN LOẠI – việc mà máy không làm thay người được."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.quyet_toan import TourSettlement, PHAN_LOAI, LOAI_DON, TRANG_THAI_QT
from app.services import quyet_toan_tour as QT, rules as R

router = APIRouter(prefix="/api/v1/quyet-toan-tour", tags=["quyet-toan-tour"])

READ = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt")
WRITE = ("tp_dh", "nv_dh", "ketoan", "cntt")


def _ra(s: TourSettlement) -> dict:
    return {"id": s.id, "ky": s.ky, "ma_tour": s.ma_tour, "ten_tour": s.ten_tour,
            "loai": s.loai, "loai_ten": LOAI_DON.get(s.loai, s.loai),
            "dieu_hanh": s.dieu_hanh, "da_anh_xa": s.operator_id is not None, "sale": s.sale,
            "ngay_kh": s.ngay_kh, "ngay_kt": s.ngay_kt,
            "doanh_thu": s.doanh_thu, "gia_von": s.gia_von, "loi_nhuan": s.loi_nhuan(),
            "ty_le": (round(s.loi_nhuan() / (s.doanh_thu or 0), 4)
                      if s.loi_nhuan() is not None and s.doanh_thu else None),
            "trang_thai_qt": s.trang_thai_qt,
            "trang_thai_ten": TRANG_THAI_QT.get(s.trang_thai_qt, s.trang_thai_qt),
            "phan_loai": s.phan_loai, "phan_loai_ten": PHAN_LOAI.get(s.phan_loai, s.phan_loai),
            "phan_loai_boi": s.phan_loai_boi, "han_bao_luu": s.han_bao_luu,
            "ghi_chu": s.ghi_chu, "ten_tep": s.ten_tep, "boi": s.boi, "luc": s.luc}


@router.get("/meta")
def meta(u: User = Depends(require_roles(*READ))):
    return {"phan_loai": PHAN_LOAI, "loai": LOAI_DON, "trang_thai_qt": TRANG_THAI_QT}


@router.get("/tong-hop")
def tong_hop(ky: str = "", u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    return QT.tong_hop(db, ky)


@router.get("")
def danh_sach(ky: str = "", loai: str = "", cho_phan_loai: bool = False, thieu_gia_von: bool = False,
              u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    q = select(TourSettlement).order_by(TourSettlement.ngay_kt.desc(), TourSettlement.id.desc())
    if ky: q = q.where(TourSettlement.ky == ky)
    if loai: q = q.where(TourSettlement.loai == loai)
    if cho_phan_loai:
        q = q.where(TourSettlement.doanh_thu > 0, TourSettlement.gia_von.is_(None),
                    TourSettlement.loai == "khach_le", TourSettlement.phan_loai == "")
    if thieu_gia_von:
        q = q.where(TourSettlement.doanh_thu > 0, TourSettlement.gia_von.is_(None),
                    TourSettlement.loai == "tour")
    return [_ra(s) for s in db.execute(q.limit(1000)).scalars()]


class PhanLoaiIn(BaseModel):
    phan_loai: str
    ghi_chu: str = ""
    han_bao_luu: date | None = None


@router.post("/{sid}/phan-loai")
def phan_loai(sid: int, data: PhanLoaiIn, u: User = Depends(require_roles(*WRITE)),
              db: Session = Depends(get_db)):
    """Người xếp loại một dòng có doanh thu mà chưa có giá vốn.

    Máy không đoán thay: một khoản 93 triệu có thể là doanh thu khách lẻ, có thể là vé công tác của ban
    lãnh đạo ghi nhầm. Hai thứ đó khác nhau hoàn toàn trên báo cáo, và chỉ người đọc chứng từ mới biết."""
    try:
        s = QT.phan_loai(db, sid, data.phan_loai, u.username, data.ghi_chu, data.han_bao_luu)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "phan_loai_quyet_toan", f"tour:{s.ma_tour}",
            after={"phan_loai": s.phan_loai, "han": str(s.han_bao_luu or ""), "ghi_chu": data.ghi_chu})
    db.commit()
    return _ra(s)


class GiaVonIn(BaseModel):
    gia_von: float
    ghi_chu: str = ""


@router.post("/{sid}/gia-von")
def nhap_gia_von(sid: int, data: GiaVonIn, u: User = Depends(require_roles(*WRITE)),
                 db: Session = Depends(get_db)):
    """Điều hành bổ sung giá vốn cho một đơn đang nằm ở hàng đợi."""
    s = db.get(TourSettlement, sid)
    if s is None: raise HTTPException(404, "Không có dòng quyết toán này")
    if data.gia_von <= 0:
        raise HTTPException(422, "Giá vốn phải lớn hơn 0. Đơn không phát sinh giá vốn thì PHÂN LOẠI, "
                                 "đừng ghi 0 – 0 và 'chưa có số' là hai chuyện khác nhau.")
    truoc = s.gia_von
    s.gia_von = data.gia_von
    s.phan_loai = ""
    if data.ghi_chu: s.ghi_chu = (s.ghi_chu + " | " + data.ghi_chu).strip(" |")[:2000]
    R.audit(db, u.username, u.role, "bo_sung_gia_von", f"tour:{s.ma_tour}",
            before={"gia_von": truoc}, after={"gia_von": s.gia_von})
    db.commit()
    return _ra(s)
