"""Bàn làm việc của robot Kiểm soát (chỉ đạo 07/9/2026: vị trí Kiểm soát do AI giữ).

Ai xem: Chủ tịch, TGĐ, chính vai trò bks, và CNTT (người vận hành robot).
Ai chạy quét và chấm điểm: bks (robot) và CNTT; Chủ tịch, TGĐ đi qua FULL_ACCESS.
Ai HẬU KIỂM điểm: Chủ tịch và TGĐ. Điểm máy chấm là đề xuất cho tới lúc đó.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import ks_robot as KS

router = APIRouter(prefix="/api/v1/kiem-soat", tags=["kiem-soat"])

XEM = ("chutich", "tgd", "bks", "cntt")
CHAY = ("bks", "cntt")            # Chủ tịch và TGĐ vẫn qua được (FULL_ACCESS trong deps)
HAU_KIEM = ("chutich", "tgd")
# Rà soát kỹ thuật (K1/K2: một cột là tiền hay không) mở thêm cho Kế toán, vì đó là phán đoán kế toán
# chứ không phải giám sát. Xem chú thích ở MENU_ROLES["/kiem-soat"].
RA_SOAT = XEM + ("ketoan",)

# Màn hình có bốn thẻ, và không phải ai mở được màn hình cũng mở được cả bốn. Trả danh sách này ra để
# giao diện chỉ vẽ thẻ người dùng thật sự bấm được: một cái nút bấm vào là 403 còn khó chịu hơn không
# có nút, và người dùng không phân biệt được "không có quyền" với "phần mềm hỏng".
THE = {
    "phat_hien": XEM,          # việc robot tìm ra
    "bao_cao": XEM,            # báo cáo gửi Chủ tịch
    "diem": XEM,               # chấm điểm phòng ban – phòng ban KHÔNG đọc điểm của chính mình
    "ra_soat": RA_SOAT,        # rà soát cột tiền và sự kiện kỹ thuật
}


def the_duoc_xem(vai_tro: str) -> list[str]:
    from app.api.deps import FULL_ACCESS
    return [k for k, vt in THE.items() if vai_tro in vt or vai_tro in FULL_ACCESS]


@router.get("/the")
def the(u: User = Depends(require_roles(*RA_SOAT))):
    """Thẻ nào người đang đăng nhập mở được. Giao diện gọi trước khi vẽ thanh thẻ."""
    return {"the": the_duoc_xem(u.role)}


@router.get("")
def bang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    ra = KS.bang(db)
    ra["the_duoc_xem"] = the_duoc_xem(u.role)
    return ra


@router.post("/quet")
def quet(u: User = Depends(require_roles(*CHAY)), db: Session = Depends(get_db)):
    """Một vòng quét: mạch nâng cấp, quyền lệch, vai trò trống, ngoại lệ tồn, AI chưa hậu kiểm.
    Chỉ sinh báo cáo gửi Chủ tịch khi có việc NGHIÊM TRỌNG mới."""
    return KS.quet(db, boi=u.username)


@router.post("/cham-diem")
def cham_diem(ky: str | None = None, u: User = Depends(require_roles(*CHAY)), db: Session = Depends(get_db)):
    return KS.cham_diem(db, ky, boi=u.username)


class HauKiemIn(BaseModel):
    diem_id: int
    chap_nhan: bool
    ghi_chu: str = ""


@router.post("/hau-kiem-diem")
def hau_kiem_diem(data: HauKiemIn, u: User = Depends(require_roles(*HAU_KIEM)),
                  db: Session = Depends(get_db)):
    return {"message": KS.hau_kiem_diem(db, u, data.diem_id, data.chap_nhan, data.ghi_chu)}


class XemIn(BaseModel):
    bao_cao_id: int


@router.post("/da-xem")
def da_xem(data: XemIn, u: User = Depends(require_roles(*HAU_KIEM)), db: Session = Depends(get_db)):
    return {"message": KS.danh_dau_da_xem(db, u, data.bao_cao_id)}
