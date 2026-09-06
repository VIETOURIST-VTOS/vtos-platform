"""Phụ thuộc chung: CSDL, người dùng hiện tại, kiểm tra vai trò."""
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.core.config import settings
from app.models.core import User, ROLES

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def current_user(request: Request, token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    data = decode_token(token)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập hết hạn hoặc không hợp lệ")
    u = db.execute(select(User).where(User.username == data["sub"], User.active == True)).scalars().first()
    if not u:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã khóa")
    from app.services.access import check_readonly_write
    check_readonly_write(u, request.method, request.url.path)   # Ban Kiểm soát chỉ đọc
    return u


# Chủ tịch HĐQT có toàn quyền trên mọi phân hệ (quyết định của Chủ tịch ngày 06/9/2026).
# Đặt ở ĐÚNG MỘT CHỖ này thay vì thêm "chutich" vào từng endpoint, để về sau không có endpoint nào bị bỏ sót
# và cũng không ai phải nhớ sửa hai nơi. Các chốt an toàn khác KHÔNG bị nới theo: kỳ đã khóa vẫn không ghi
# được, chứng từ đã ghi sổ vẫn bất biến (sai thì lập bút toán đảo), Ban Kiểm soát vẫn chỉ đọc, và mọi thao
# tác vẫn ghi nhật ký kiểm toán kèm tên người thực hiện nên vẫn truy được trách nhiệm.
FULL_ACCESS = ("chutich",)


def require_roles(*roles: str):
    def dep(u: User = Depends(current_user)) -> User:
        if roles and u.role not in roles and u.role not in FULL_ACCESS:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Vai trò {ROLES.get(u.role, u.role)} không có quyền thực hiện thao tác này")
        return u
    return dep


def robot_auth(x_robot_token: str | None = Header(default=None)):
    if not settings.ROBOT_TOKEN or not x_robot_token or x_robot_token != settings.ROBOT_TOKEN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sai ROBOT_TOKEN")


class Gate(HTTPException):
    """Cổng chặn nghiệp vụ – trả 422 kèm mã cổng để giao diện hiển thị."""
    def __init__(self, code: str, detail: str):
        super().__init__(422, {"gate": code, "message": detail})
