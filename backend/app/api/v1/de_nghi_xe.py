# -*- coding: utf-8 -*-
"""CỬA ĐỀ NGHỊ XE — mắt đầu của chuỗi điều xe (Chủ tịch đặc tả 11/10/2026).

Gắn màn hình `/lenh-dieu-xe` đã có: đề nghị và lệnh là hai mặt của một việc, nên chúng ở cùng một
màn hình. Dựng màn hình thứ hai cho đề nghị là bắt Giám đốc đội xe mở hai trang để làm một việc.

HAI NHÓM VAI, và chúng KHÁC NHAU đúng ở chỗ phải khác:

  ĐỀ NGHỊ  — Điều hành, vì họ là người biết chuyến cần xe.
  TỪ CHỐI  — Giám đốc đội xe, vì chỉ người có xe mới nói được "không còn xe".

Người đề nghị KHÔNG từ chối được đề nghị của chính mình, và người đội xe KHÔNG huỷ hộ Điều hành:
mỗi bên gỡ việc của mình, và mỗi lần gỡ đều phải ghi lý do.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import de_nghi_xe as DN
from app.services.access import FULL_VIEW, MENU_ROLES, OPERATIONS

router = APIRouter(prefix="/api/v1/de-nghi-xe", tags=["de-nghi-xe"])

# XEM = ĐÚNG những người mở được màn hình `/lenh-dieu-xe`, và SUY TỪ bảng ấy chứ không gõ lại.
#
# Bài học LG1 (10/10/2026): một phép suy có TÊN, nhiều nơi cùng đọc. Gõ lại danh sách ở đây thì hôm
# nay nó khớp, và ngày nào ai thêm một vai vào màn hình mà quên chỗ này thì người ấy mở được trang
# nhưng mọi cửa trên trang trả 403 — cửa mở mà không có tay nắm. Bản đầu em gõ tay và đã lệch thật:
# thừa `ptgd_doan` và `ketoan`, hai vai không có trong `MENU_ROLES` của màn hình này.
XEM = MENU_ROLES["/lenh-dieu-xe"]
# ĐỀ NGHỊ: Điều hành. Hai vai nền có mặt vì Chủ tịch và TGĐ phải làm được mọi việc họ nhìn thấy.
DE_NGHI = FULL_VIEW + OPERATIONS + ("cntt",)
# TỪ CHỐI: đội xe. Người đề nghị không từ chối việc của chính mình.
TU_CHOI = FULL_VIEW + ("gd_doi_xe", "cntt")


class DeNghiIn(BaseModel):
    tour_id: int
    so_khach: int
    km_du_kien: int = 0
    so_xe_can: int = 1
    yeu_cau: str = ""
    ngay_di: str | None = None
    ngay_ve: str | None = None


class LyDoIn(BaseModel):
    ly_do: str


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    """Trả kèm HAI CÂU TRẢ LỜI VỀ QUYỀN, để màn hình không gõ lại danh sách vai.

    Bài học LG1 lặp lại ở lớp giao diện: nếu `page.tsx` tự viết `["tp_dh","nv_dh",...]` để quyết
    hiện nút nào, thì ngày nào bảng vai ở máy chủ đổi, giao diện vẫn hiện nút cũ — người bấm vào và
    nhận 403, hoặc tệ hơn, người ĐƯỢC phép lại không thấy nút. Một phép suy, một nơi suy.
    """
    return {"trang_thai": DN.TRANG_THAI, "du_toan_da_duyet": list(DN.DU_TOAN_DA_DUYET),
            "toi_duoc_de_nghi": u.role in DE_NGHI, "toi_duoc_tu_choi": u.role in TU_CHOI}


@router.get("/tour-cho-de-nghi")
def tour_cho_de_nghi(tu: str, den: str, u: User = Depends(require_roles(*XEM)),
                     db: Session = Depends(get_db)):
    from datetime import date as _d
    try:
        return DN.tour_cho_de_nghi(db, _d.fromisoformat(tu), _d.fromisoformat(den))
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("")
def danh_sach(trang_thai: str = "", tour_id: int | None = None,
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    try:
        return DN.danh_sach(db, trang_thai, tour_id)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/lenh-khong-qua-de-nghi")
def lenh_khong_qua_de_nghi(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Đếm chỗ chuỗi ba mắt chưa được dùng. Không có cửa này thì chỗ hở ở lại mãi mà không ai đo."""
    return DN.lenh_khong_qua_de_nghi(db)


@router.post("", status_code=201)
def tao(data: DeNghiIn, u: User = Depends(require_roles(*DE_NGHI)), db: Session = Depends(get_db)):
    from datetime import date as _d
    try:
        d = DN.de_nghi(db, u, data.tour_id, data.so_khach, data.km_du_kien, data.so_xe_can,
                       data.yeu_cau,
                       _d.fromisoformat(data.ngay_di) if data.ngay_di else None,
                       _d.fromisoformat(data.ngay_ve) if data.ngay_ve else None)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"id": d.id, "message": f"Đã gửi đề nghị xe #{d.id} – chờ Giám đốc đội xe lập lệnh"}


@router.post("/{did}/tu-choi")
def tu_choi(did: int, data: LyDoIn, u: User = Depends(require_roles(*TU_CHOI)),
            db: Session = Depends(get_db)):
    try:
        d = DN.tu_choi(db, u, did, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã từ chối đề nghị #{d.id}. Điều hành sẽ thấy lý do và thuê xe ngoài."}


@router.post("/{did}/huy")
def huy(did: int, data: LyDoIn, u: User = Depends(require_roles(*DE_NGHI)),
        db: Session = Depends(get_db)):
    try:
        d = DN.huy(db, u, did, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã huỷ đề nghị #{d.id}."}
