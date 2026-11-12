"""R5 · Cửa đọc của bàn làm việc Giám đốc Kinh doanh lẻ (/ban-kd-le) — Chủ tịch duyệt 13/11/2026.

MỘT TIỀN TỐ RIÊNG, cùng lập luận với `ban_tour_le.py`: gắn nhờ vào một nhóm API có sẵn là nới CẢ
nhóm ấy cho mọi vai mở được màn mới.

CHỈ ĐỌC. Bàn không có cửa ghi nào: mọi việc làm ở màn đang giữ nghiệp vụ, mở ngay trong bàn.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ban_kd_le as S

# Hẹp đúng bằng dòng "/ban-kd-le" của MENU_ROLES. Chủ tịch chốt 13/11/2026: Giám đốc KD làm việc
# trên bàn; Chủ tịch, TGĐ (và hai vai đọc nền bks, robot_ks) mở để xem. tp_kd, tn_kd chưa vào đợt này.
XEM = ("chutich", "tgd", "bks", "robot_ks", "gd_kd", "cntt")

router = APIRouter(prefix="/api/v1/ban-kd-le", tags=["ban-kd-le"])


@router.get("/tong-quan")
def tong_quan(u: User = Depends(require_roles(*XEM, mo_ta="bàn làm việc Giám đốc Kinh doanh lẻ")),
              db: Session = Depends(get_db)):
    return S.tong_quan(db)
