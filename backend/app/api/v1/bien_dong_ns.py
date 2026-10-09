# -*- coding: utf-8 -*-
"""CỬA 5.8 BÁO CÁO BIẾN ĐỘNG NHÂN SỰ (Chủ tịch giao 08/10/2026).

Gắn màn hình `/hr` thẻ "Tổng quan HCNS" — không dựng màn hình mới. Đây là báo cáo VỀ nhân sự, cùng
một tập người và cùng một nhóm người đọc với thẻ ấy; dựng thêm một màn hình là tách hai thứ phải
đọc cạnh nhau ra hai chỗ, và người xem phải nhớ đi hai nơi để trả lời một câu hỏi.

XEM rộng bằng đúng thẻ Tổng quan; GHI (ngày nghỉ việc) hẹp bằng HR_ADMIN — ghi ngày nghỉ là đóng
một người khỏi bảng lương, không phải một ô ghi chú.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import bien_dong_ns as BD
from app.services.access import HR_TAB_ROLES

router = APIRouter(prefix="/api/v1/bien-dong-ns", tags=["bien-dong-ns"])

XEM = HR_TAB_ROLES["tong_quan"]
GHI = ("hcns", "cntt", "tgd", "chutich")      # đúng HR_ADMIN của api/v1/hrm.py


class NghiViecIn(BaseModel):
    employee_id: int
    ngay: date
    ly_do_loai: str = "tu_xin"
    ly_do: str = ""


class HuyIn(BaseModel):
    employee_id: int
    ly_do: str


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return BD.meta()


@router.get("")
def bao_cao(ky_loai: str = "thang", ky: str = "",
            u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    try:
        return BD.bao_cao(db, ky_loai, ky)
    except (ValueError, IndexError) as e:
        raise HTTPException(400, str(e))


@router.get("/co-cau")
def co_cau(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return BD.co_cau(db)


@router.get("/chua-biet-ngay-nghi")
def chua_biet(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Người đã nghỉ mà chưa ai điền ngày — việc của HCNS, không phải số để báo cáo lên."""
    return BD.chua_biet_ngay_nghi(db)


@router.post("/nghi-viec")
def nghi_viec(body: NghiViecIn, u: User = Depends(require_roles(*GHI)),
              db: Session = Depends(get_db)):
    try:
        r = BD.ghi_nghi_viec(db, u, body.employee_id, body.ngay, body.ly_do_loai, body.ly_do)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))


@router.post("/huy-nghi-viec")
def huy_nghi_viec(body: HuyIn, u: User = Depends(require_roles(*GHI)),
                  db: Session = Depends(get_db)):
    try:
        r = BD.huy_nghi_viec(db, u, body.employee_id, body.ly_do)
        db.commit()
        return r
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
