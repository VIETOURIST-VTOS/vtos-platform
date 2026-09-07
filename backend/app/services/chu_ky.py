"""Bước duyệt cần đủ n chữ ký của các vai trò được chỉ định đích danh (Phụ lục đối chiếu 27/8/2026, mục 3.2).

Yêu cầu "đủ hai chữ ký Chủ tịch Hội đồng quản trị và Tổng giám đốc" lặp lại ở nhiều chỗ trong bộ chính
sách: sửa đổi mọi quy chế, duyệt chuyến chạy dưới biên 10%, chế tài sự vụ mức 3. Đối tượng duyệt trước đây
là chuỗi bước tuần tự MỘT người mỗi bước, nên hai điều sau không có chỗ nào chặn:

  1. Người TRÌNH hồ sơ tự ký duyệt hồ sơ của chính mình. Chữ ký thứ hai khi đó không còn là một lớp kiểm
     soát độc lập – nó chỉ là cùng một người ký hai lần dưới hai vai.
  2. Một người mang nhiều vai trò ký thay cả hai vai.

Gộp vào một chỗ để mọi phân hệ dùng chung, thay vì mỗi nơi tự viết một kiểu rồi sót một nơi.
"""
from fastapi import HTTPException
from app.models.core import User, ROLES


def kiem_tra_nguoi_ky(u: User, vai_tro_can: tuple[str, ...], nguoi_trinh: str = "", da_ky: dict[str, str] | None = None) -> None:
    """Ném HTTPException nếu người này không được ký bước hiện tại."""
    da_ky = da_ky or {}
    if u.role not in vai_tro_can:
        raise HTTPException(403, "Bước này cần chữ ký của " + " và ".join(ROLES.get(r, r) for r in vai_tro_can))
    if nguoi_trinh and u.username == nguoi_trinh:
        raise HTTPException(422, "Người trình hồ sơ không được ký duyệt chính hồ sơ mình trình – "
                                 "chữ ký thứ hai phải là một người khác thì mới là một lớp kiểm soát")
    if da_ky.get(u.role):
        raise HTTPException(422, f"Vai trò {ROLES.get(u.role, u.role)} đã ký hồ sơ này rồi")
    if u.username in da_ky.values():
        raise HTTPException(422, f"{u.username} đã ký hồ sơ này ở vai trò khác – một người không ký thay cả hai vai")


def du_chu_ky(da_ky: dict[str, str], vai_tro_can: tuple[str, ...]) -> bool:
    return all(da_ky.get(r) for r in vai_tro_can)


def con_thieu(da_ky: dict[str, str], vai_tro_can: tuple[str, ...]) -> list[str]:
    return [ROLES.get(r, r) for r in vai_tro_can if not da_ky.get(r)]
