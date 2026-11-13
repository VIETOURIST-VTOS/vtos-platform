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

# R5-5 (13/11/2026): bàn chạy ở /fit — màn của CẢ phòng Lẻ — nên phạm vi nhóm API rộng hơn bàn; hàng rào
# THẬT của bàn là danh sách này (TP, trưởng nhóm, NV mở /fit gặp trang hai tab, gọi cửa này thì 403).
# Gương: VAI_BAN_KD_LE ở web/components/Shell.tsx (phép thử so hai chỗ). Chủ tịch chốt 13/11/2026: Giám đốc KD làm việc
# trên bàn; Chủ tịch, TGĐ (và hai vai đọc nền bks, robot_ks) mở để xem. tp_kd, tn_kd chưa vào đợt này.
# R5-5: cntt rời danh sách — cntt không thuộc phòng Lẻ nên không mở được /fit, chỗ duy nhất còn bàn.
XEM = ("chutich", "tgd", "bks", "robot_ks", "gd_kd")

router = APIRouter(prefix="/api/v1/ban-kd-le", tags=["ban-kd-le"])


@router.get("/tong-quan")
def tong_quan(u: User = Depends(require_roles(*XEM, mo_ta="bàn làm việc Giám đốc Kinh doanh lẻ")),
              db: Session = Depends(get_db)):
    return S.tong_quan(db)


@router.get("/doanh-thu")
def doanh_thu(nam: int = 0, u: User = Depends(require_roles(*XEM, mo_ta="doanh thu – chỉ tiêu tour lẻ")),
              db: Session = Depends(get_db)):
    """Tách khỏi /tong-quan: 12 tháng doanh thu tốn vài giây, bàn hiện trước rồi biểu đồ hiện sau."""
    from datetime import date
    return S.doanh_thu_le(db, nam or date.today().year)
