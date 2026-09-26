"""CỬA CÔNG KHAI — trang khách tự chấm điểm sau tour. KHÔNG cần đăng nhập.

═══════════════════════════════════════════════════════════════════════════════════════════════
ĐỌC KỸ TRƯỚC KHI SỬA TỆP NÀY
═══════════════════════════════════════════════════════════════════════════════════════════════
Đây là cửa DUY NHẤT của VTOS không đứng sau `Depends(current_user)`. Mọi cửa khác trong kho đều
hỏi ai đang gọi trước khi làm gì; cửa này thì không, vì khách không có tài khoản.

Ba luật của tệp này, và không luật nào được nới mà không có người quyết định:

    1. CHỈ hai đường: đọc phiếu, ghi một lần. Không thêm đường thứ ba ở đây. Muốn khách làm thêm
       việc gì thì hỏi lại xem việc ấy có đáng mở một cửa ra đường nữa không.
    2. KHÔNG in ra thứ gì khách chưa biết. Không số điện thoại, không giá, không mã booking,
       không tên khách khác cùng đoàn. Mọi thứ in ở đây là in cho bất kỳ ai cầm được đường dẫn.
    3. CÓ hàng rào số lần thử. Mã sinh bằng `secrets.token_urlsafe(24)` nên dò mù là vô vọng,
       nhưng một cửa ra đường không có phanh vẫn là một cửa người ta dội vào được.

Tiền tố `/api/v1/khao-sat` đặt riêng, KHÔNG gắn nhờ vào nhóm nào — cùng lập luận đã ghi ở
`ptgd_doan.py` và `sales_admin.py`, cộng thêm một lý do nặng hơn: nhóm nào chứa cửa này thì cả
nhóm ấy có một cửa không cần đăng nhập, và người đọc bảng phân quyền sẽ không thấy điều đó.
"""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import danh_gia as DG

router = APIRouter(prefix="/api/v1/khao-sat", tags=["khao-sat-cong-khai"])

# Phanh đơn giản, đủ cho việc này: đếm lượt theo địa chỉ mạng trong một cửa sổ trượt. Không dùng
# kho ngoài vì thêm một phụ thuộc cho một cửa chỉ khách dùng là đắt hơn cái nó mua.
_LUOT: dict[str, list[float]] = defaultdict(list)
CUA_SO_GIAY = 300.0
TOI_DA_TRONG_CUA_SO = 30


def _phanh(req: Request) -> None:
    ip = (req.client.host if req.client else "") or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_TRONG_CUA_SO:
        _LUOT[ip] = v
        raise DG.Gate("KHAO_SAT_NHIEU", "Anh/chị thử hơi nhiều lần. Xin đợi vài phút rồi mở lại.")
    v.append(bay_gio)
    _LUOT[ip] = v
    # Dọn bớt để bộ nhớ không phình mãi trên một tiến trình chạy dài.
    if len(_LUOT) > 5000:
        for k in [k for k, x in _LUOT.items() if not x or bay_gio - x[-1] > CUA_SO_GIAY]:
            _LUOT.pop(k, None)


class MotMuc(BaseModel):
    doi_tuong: str
    doi_tuong_id: int | None = None
    doi_tuong_ten: str = ""
    diem: int | None = None
    nhan_xet: str = ""


class GuiDanhGia(BaseModel):
    diem: list[MotMuc] = []
    nhu_cau_tiep: str = ""
    dong_y_dung_danh_gia: str = ""
    gop_y: str = ""


@router.get("/{ma}")
def xem(ma: str, request: Request, db: Session = Depends(get_db)):
    """Khách mở đường dẫn trong tin Zalo. Lượt mở được đếm — đó là thước đo 'khách có đọc tin
    không', và mốc nghiệm thu của đề xuất cần đúng con số ấy."""
    _phanh(request)
    return DG.mo_phieu(db, ma)


@router.post("/{ma}")
def gui(ma: str, data: GuiDanhGia, request: Request, db: Session = Depends(get_db)):
    """Khách bấm gửi. MỘT lần cho một mã."""
    _phanh(request)
    return DG.ghi_danh_gia(db, ma, data.model_dump())
