"""Cửa API: gộp hai tài khoản trùng của cùng một người.

TIỀN TỐ RIÊNG `/api/v1/gop-tai-khoan`, không gắn vào `/api/v1/access`. Nhóm phân quyền đã rộng sẵn
và có mười một cửa; thêm cửa gộp vào đó là ai mở được màn hình phân quyền cũng gộp được tài khoản —
mà gộp là thao tác chuyển doanh số của một người sang một người khác.

DANH SÁCH VAI HẸP NHẤT TRONG CẢ KHO CHO ĐẾN NAY: `cntt` và hai người Ban Tổng giám đốc. Cố ý KHÔNG
có `hcns`, dù chính họ giữ hồ sơ nhân sự và chính họ biết ai trùng ai — họ ĐỌC được bảng cặp trùng
để soát, nhưng nút gộp thì không. Lý do: gộp là việc một chiều. Chuyển 290 booking sang nhầm người
rồi thì không có nút tách ra lại, phải gộp ngược từng bảng bằng tay. Việc một chiều thì để ít người
làm được, và người ấy phải là người đọc được nhật ký để tự kiểm.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import gop_tai_khoan as GTK
from app.services.access import BASE_VIEW

XEM = BASE_VIEW + ("hcns", "ketoan", "cntt")
GOP = ("chutich", "tgd", "cntt")

router = APIRouter(prefix="/api/v1/gop-tai-khoan", tags=["gop-tai-khoan"])


@router.get("/cap-trung")
def cap_trung(u: User = Depends(require_roles(*XEM, mo_ta="danh sách tài khoản trùng")),
              db: Session = Depends(get_db)):
    """Người nào đang có từ hai tài khoản trở lên, mỗi tài khoản đang giữ bao nhiêu dòng dữ liệu."""
    ds = GTK.cap_trung(db)
    return {"tong_nguoi": len(ds), "rows": ds,
            "ghi_chu": "Gợi ý giữ tài khoản CÓ MÃ NHÂN VIÊN – bảng lương là chuẩn (chốt 19/9/2026). "
                       "Máy chỉ gợi ý, người bấm mới gộp."}


@router.get("/xem-truoc")
def xem_truoc(giu_id: int, bo_id: int,
              u: User = Depends(require_roles(*XEM, mo_ta="xem trước khi gộp")),
              db: Session = Depends(get_db)):
    """Gộp thì bao nhiêu dòng chuyển, ở bảng nào. Không ghi gì."""
    try:
        return GTK.xem_truoc(db, giu_id, bo_id)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class GopVao(BaseModel):
    giu_id: int
    bo_id: int
    ly_do: str
    xac_nhan: bool = False


@router.post("")
def gop(data: GopVao, u: User = Depends(require_roles(*GOP, mo_ta="gộp tài khoản")),
        db: Session = Depends(get_db)):
    """Chuyển hết dữ liệu sang tài khoản giữ, rồi KHOÁ tài khoản thừa.

    `xac_nhan=false` chỉ trả bản xem trước và KHÔNG ghi — đó là mặc định, cố ý: một thao tác một
    chiều thì bước mặc định phải là bước không làm gì.
    """
    try:
        kq = GTK.gop(db, u, data.giu_id, data.bo_id, data.ly_do, data.xac_nhan)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if data.xac_nhan:
        db.commit()
    return kq
