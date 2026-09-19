"""TC-71 · CỬA SỔ CHUYẾN CÒN NỢ — anh Tuấn 18/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO LÀ MỘT TIỀN TỐ RIÊNG, KHÔNG NẰM TRONG `/api/v1/bao-cao`
═══════════════════════════════════════════════════════════════════════════════════════════════
Bản nháp đầu của vòng này đặt cửa vào `bao_cao.py`, tức là dùng lại tiền tố `/api/v1/bao-cao`.
Đo bằng bộ kiểm P2 thì thấy ngay hệ quả: `nv_dh` và `cntt` được nới TOÀN BỘ nhóm báo cáo, chỉ vì
họ mở được màn hình mới này — trong khi thứ họ cần đúng một cửa.

Đó chính là bài học kho này đã ghi ngày 09/9/2026 ở chỗ nhóm `/api/v1/tong-dai`:

    "Cố ý KHÔNG gắn vào /inbox dù cuộc gọi rồi sẽ hiện ở hộp thư: gắn ở đó là mở tiền tố cho
     mười ba vai trò trong khi chỉ bốn vai trò gọi được, và PHẦN DÔI RA VẪN LÀ QUYỀN ĐÃ CẤP."

Hàng rào trong (`require_roles` ở từng cửa của `/bao-cao`) vẫn giữ, nên phần dôi ra không mở được
gì hôm nay. Nhưng nó là quyền đã cấp, và cửa `/bao-cao` nào thêm về sau sẽ tự mở cho hai vai ấy
mà không ai nhận ra. Tiền tố riêng thì phần nới đúng bằng phần cần — chín vai mở được màn hình
này được thêm đúng một nhóm, và nhóm ấy chỉ có mỗi cửa này.

Cùng khuôn mẫu với `/api/v1/lai-lo-tour` gắn vào màn hình `/lai-lo-tour` (09/9/2026, +1 cho chín
vai) — không phải một cách làm mới.

═══════════════════════════════════════════════════════════════════════════════════════════════
KHÔNG NHỚ TẠM Ở CỬA NÀY
═══════════════════════════════════════════════════════════════════════════════════════════════
`/bao-cao/ket-qua-kinh-doanh` nhớ năm phút vì nó là con số tổng, nguồn đổi chậm. Cửa này là DANH
SÁCH VIỆC PHẢI LÀM: người điều hành vừa đóng sổ một chuyến xong bấm lại mà chuyến ấy vẫn nằm đó
thì họ tưởng bấm hụt, và sẽ bấm lại lần nữa.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
# DÙNG LẠI `COST_ROLES`, KHÔNG BỊA DANH SÁCH VAI MỚI. Dòng ấy vốn nghĩa là "cơ cấu chi phí NCC,
# quyết toán, dòng tiền tour" — đúng miền của sổ quyết toán chuyến, và nó đã gồm sẵn đúng ba nhóm
# anh Tuấn chọn 18/9: Chủ tịch/TGĐ, Điều hành (tp_dh, nv_dh) và Kế toán.
#
# Một danh sách vai mới cho mỗi màn hình mới là cách ma trận quyền mục ruỗng dần: sáu tháng sau
# không ai còn trả lời được "Điều hành xem được những gì" mà không đọc hết từng cửa một.
from app.services.access import COST_ROLES as XEM

router = APIRouter(prefix="/api/v1/so-con-no", tags=["so-con-no"])


@router.get("")
def danh_sach(tu: str = "", den: str = "", gioi_han: int = 500,
              u: User = Depends(require_roles(*XEM, mo_ta="sổ chuyến còn nợ")),
              db: Session = Depends(get_db)):
    """Chuyến đã khởi hành mà chưa đóng sổ — tiền đã về nhưng chưa vào sổ kế toán.

    `tu` / `den` dạng "2026-01", lọc theo NGÀY KHỞI HÀNH (chuyến chưa đóng sổ không có ngày đóng
    sổ để mà lọc). Bỏ trống thì lấy tất cả.

    Phạm vi pháp nhân cắt NGAY TRONG TRUY VẤN — xem khối SEC-02 ở đầu `services/so_con_no.py`.
    """
    from app.services import so_con_no as SN
    try:
        return SN.danh_sach(db, u, tu=tu, den=den, gioi_han=gioi_han)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
