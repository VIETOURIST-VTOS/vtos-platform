"""Màn hình "Ngoại lệ cần xử lý" (Kiểm soát & Chính sách).

Ai xem: Chủ tịch, TGĐ, Ban Kiểm soát (đọc), Kế toán, CNTT, Trưởng phòng Điều hành, hai Phó TGĐ.
Ai ghi: người xem được, trừ Ban Kiểm soát (chặn ghi ở lớp chung).
Ai ĐÓNG: Chủ tịch và TGĐ. Đóng một ngoại lệ là tuyên bố "tôi đã xem và chịu trách nhiệm" – nếu ai
xử lý cũng đóng được thì việc đóng chỉ còn nghĩa là dọn màn hình cho sạch.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import ngoai_le as NL

router = APIRouter(prefix="/api/v1/ngoai-le", tags=["ngoai-le"])

# robot_ks chỉ ĐỌC danh sách ngoại lệ (nó mở việc qua vòng quét, không qua API này). KHÔNG có mặt ở
# GHI và DONG: robot mở việc mà đóng được việc thì lớp kiểm soát chỉ còn là hình thức.
XEM = ("chutich", "tgd", "bks", "ketoan", "cntt", "tp_dh", "ptgd_doan", "ptgd_mkt", "robot_ks")
GHI = ("chutich", "tgd", "ketoan", "cntt", "tp_dh", "ptgd_doan", "ptgd_mkt")
DONG = ("chutich", "tgd")


@router.get("")
def danh_sach(trang_thai: str = "", loai: str = "", nhom: str = "",
              chi_thieu_chu_ky: bool = False, so_ngay: int = Query(NL.CUA_SO_NGAY, ge=1, le=1095),
              cat_moi_loai: int = Query(NL.CAT_MOI_LOAI, ge=0, le=5000),
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """cat_moi_loai = 0 nghĩa là lấy hết. Con số ở tong_hop luôn đếm trên toàn bộ, không phụ thuộc cắt."""
    return NL.danh_sach(db, trang_thai, loai, nhom, chi_thieu_chu_ky, so_ngay, cat_moi_loai)


class NhanIn(BaseModel):
    ma: str


class GhiIn(BaseModel):
    ma: str
    giai_trinh: str = ""
    da_lam: str = ""
    nguoi_chiu_trach_nhiem: str = ""


class DongIn(BaseModel):
    ma: str
    ket_luan: str = ""


class MoLaiIn(BaseModel):
    ma: str
    ly_do: str


@router.post("/nhan")
def nhan(data: NhanIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    return {"message": NL.nhan(db, u, data.ma)}


@router.post("/ghi")
def ghi(data: GhiIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    return {"message": NL.ghi(db, u, data.ma, data.giai_trinh, data.da_lam, data.nguoi_chiu_trach_nhiem)}


@router.post("/dong")
def dong(data: DongIn, u: User = Depends(require_roles(*DONG)), db: Session = Depends(get_db)):
    return {"message": NL.dong(db, u, data.ma, data.ket_luan)}


@router.post("/mo-lai")
def mo_lai(data: MoLaiIn, u: User = Depends(require_roles(*DONG)), db: Session = Depends(get_db)):
    return {"message": NL.mo_lai(db, u, data.ma, data.ly_do)}
