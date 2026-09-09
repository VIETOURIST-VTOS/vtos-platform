"""Báo cáo tự động trên màn hình – lọc theo NGƯỜI ĐANG ĐĂNG NHẬP.

Chỗ chặn nằm ở đây chứ không ở màn hình: màn hình chỉ vẽ thứ máy chủ trả về, nên nếu máy chủ trả về
báo cáo của mọi phòng rồi để giao diện lọc thì ai mở công cụ nhà phát triển cũng đọc được hết.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.db.session import get_db
from app.models.core import User
from app.services import bao_cao_phong as BP

router = APIRouter(prefix="/api/v1/bao-cao", tags=["bao-cao-tu-dong"])


@router.get("/pham-vi")
def pham_vi(u: User = Depends(current_user)):
    """Các báo cáo người này mở được. Rỗng = màn hình nói rõ 'chưa có báo cáo nào dành cho vai trò
    của anh/chị', chứ không hiện một trang trắng."""
    ds = BP.pham_vi_duoc_xem(u.role)
    ten = {BP.TOAN_CTY: "Toàn công ty", **{k: v["ten"] for k, v in BP.PHONG.items()}}
    return {"pham_vi": [{"ma": p, "ten": ten[p]} for p in ds],
            "ky": [{"ma": k, "ten": v} for k, v in BP.TEN_KY.items()],
            "vai_tro": u.role}


@router.get("")
def xem(pham_vi: str = BP.TOAN_CTY, kind: str = "ngay", ngay: str = "",
        u: User = Depends(current_user), db: Session = Depends(get_db)):
    if pham_vi not in BP.pham_vi_duoc_xem(u.role):
        # Nói rõ là KHÔNG THUỘC PHẠM VI, không nói "không tồn tại": người dùng cần biết mình đang
        # đứng sai chỗ chứ không phải nghi hệ thống hỏng.
        raise HTTPException(403, "Báo cáo này không thuộc phạm vi của vai trò anh/chị. "
                                 "Trưởng phòng xem báo cáo phòng mình; báo cáo toàn công ty dành "
                                 "cho Chủ tịch, Tổng giám đốc và Ban Kiểm soát.")
    try:
        moc = date.fromisoformat(ngay) if ngay else None
        return BP.bao_cao(db, kind, pham_vi, moc)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
