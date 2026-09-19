"""Cửa API: ai được bán hàng — nhân viên nào, và đối tác nào.

TIỀN TỐ RIÊNG `/api/v1/nguoi-ban-hang`. Bài học đã trả giá ba lần trong kho này
(`/api/v1/tong-dai`, `/api/v1/so-con-no`, và suýt nữa ở TC-73): gắn cửa mới vào một tiền tố rộng
sẵn có là nới CẢ NHÓM cho mọi vai đang có nhóm ấy — phần dôi ra vẫn là quyền đã cấp.

HAI DANH SÁCH VAI

`XEM` rộng: cả khối Kinh doanh cần biết đối tác nào đang hợp tác và ai trong công ty được bán hàng.
Đây không phải bí mật, và giấu đi thì người ta hỏi nhau qua Zalo.

`GHI` hẹp: Hành chính – Nhân sự, Công nghệ thông tin, Ban Tổng giám đốc. Cố ý KHÔNG có `gd_kd`, cùng
lý lẽ đã ghi ở `to_chuc_kd.py`: bật quyền bán cho một người là đổi doanh số của người ấy, và người
tự bật được cho mình là người tự cấp được doanh số cho mình.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import nguoi_ban_hang as NB
from app.services.access import BASE_VIEW, SALES

XEM = BASE_VIEW + SALES + ("hcns", "hanh_chinh", "ptgd_doan", "ketoan", "cntt")
GHI = ("chutich", "tgd", "hcns", "cntt")

router = APIRouter(prefix="/api/v1/nguoi-ban-hang", tags=["nguoi-ban-hang"])


@router.get("")
def tong_quan(u: User = Depends(require_roles(*XEM, mo_ta="danh sách người bán hàng")),
              db: Session = Depends(get_db)):
    """Ba nhóm nhân viên và danh mục đối tác — tất cả những ai có thể đứng tên một booking."""
    return {**NB.ai_duoc_ban(db), "doi_tac": NB.danh_sach_doi_tac(db)}


class QuyenBan(BaseModel):
    user_id: int
    duoc: bool
    ly_do: str


@router.post("/quyen-ban")
def dat_quyen_ban(data: QuyenBan,
                  u: User = Depends(require_roles(*GHI, mo_ta="quyền bán hàng của nhân viên")),
                  db: Session = Depends(get_db)):
    try:
        nv = NB.dat_quyen_ban(db, u, data.user_id, data.duoc, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": ("Đã mở quyền bán hàng cho " if data.duoc else "Đã thu quyền bán hàng của ")
                       + nv.full_name}


class DoiTacMoi(BaseModel):
    ma: str
    ten: str
    loai: str = "ghep_le"
    lien_he: str = ""
    dien_thoai: str = ""
    ma_so_thue: str = ""
    hieu_luc_tu: date | None = None
    ghi_chu: str = ""


@router.post("/doi-tac")
def tao_doi_tac(data: DoiTacMoi,
                u: User = Depends(require_roles(*GHI, mo_ta="danh mục đối tác bán hàng")),
                db: Session = Depends(get_db)):
    try:
        dt = NB.tao_doi_tac(db, u, data.ma, data.ten, data.loai, data.lien_he,
                            data.dien_thoai, data.ma_so_thue, data.hieu_luc_tu, data.ghi_chu)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã thêm đối tác {dt.ma}", "id": dt.id}


class DongDoiTac(BaseModel):
    den_ngay: date
    ly_do: str


@router.post("/doi-tac/{doi_tac_id}/dong")
def dong_doi_tac(doi_tac_id: int, data: DongDoiTac,
                 u: User = Depends(require_roles(*GHI, mo_ta="dừng hợp tác với đối tác")),
                 db: Session = Depends(get_db)):
    try:
        dt = NB.dong_doi_tac(db, u, doi_tac_id, data.den_ngay, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": f"Đã dừng hợp tác với {dt.ten} từ {data.den_ngay}"}
