# -*- coding: utf-8 -*-
"""CỬA DUYỆT CÔNG BỐ NHẬN XÉT — Đợt HD-DG3. Chủ tịch chốt 16/10/2026.

Tách thành tệp riêng chứ không nối vào `danh_gia.py`, vì hai lý do khác nhau:

  1. Đây là việc CÔNG BỐ, không phải việc đọc bảng điểm. Chủ tịch chốt 16/10 rằng quyền xem, xử
     lý khiếu nại, công bố và gỡ nội dung phải TÁCH RIÊNG — tách trong mã là cách giữ cho câu ấy
     không mòn đi sau vài đợt.
  2. Quyền ở đây KHÔNG thuần theo vai. Hai vai duyệt được (`chutich`, `tgd`), người thứ ba duyệt
     bằng quyền cấp đích danh có hạn. Trộn một cửa như thế vào tệp mà mọi cửa đều khai bằng
     `require_roles` là làm người đọc bảng phân quyền tưởng cửa này cũng thế.

CỬA NÀY KHÔNG DÙNG `require_roles` CHO VIỆC BẤM. `require_roles` chỉ biết vai; quyền của người
thứ ba nằm ở `user_grants`. Hai cửa GHI hỏi `dong_y.ai_duyet_duoc` và từ chối thẳng, và mỗi lần
bấm ghi lại bấm bằng quyền nào.

ĐỌC THÌ VẪN DO LỚP MÀN HÌNH GÁC, KHÔNG PHẢI "AI ĐĂNG NHẬP CŨNG ĐỌC ĐƯỢC" — chép lại ở đây vì bản
đầu của tệp này viết sai đúng câu ấy, và phép đo qua HTTP bác lại. Kho có một lớp chặn chung:
một đường API mà KHÔNG màn hình nào khai trong `access.MAN_HINH_API` thì không ai gọi được, kể
cả Chủ tịch; và khai rồi thì chỉ các vai trong `access.MENU_ROLES` của màn hình ấy gọi được.
Nên tập người đọc được hàng đợi ĐÚNG BẰNG tập vai khai cho `/duyet-cong-bo`.

HỆ QUẢ CHO NGƯỜI THỨ BA, VÀ ĐÂY LÀ CHỖ DỄ HỎNG NHẤT CỦA ĐỢT NÀY: anh Nguyễn Tất Thắng cần HAI
dòng cấp, không phải một — một dòng `menu` cho `/duyet-cong-bo` để màn hình mở ra, và một dòng
`capability` cho `duyet_cong_bo_nhan_xet` để nút bấm được. Cấp mỗi quyền năng lực thì anh ấy
bấm được nhưng không vào được màn hình; cấp mỗi menu thì vào được mà nút không sáng. Cả hai dòng
đều tối đa 90 ngày và đều chỉ Chủ tịch hoặc TGĐ cấp được.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.core import User
from app.models.danh_gia import DanhGiaSauTour
from app.services import dong_y as DY

router = APIRouter(prefix="/api/v1/cong-bo", tags=["cong-bo"])


class QuyetDinh(BaseModel):
    dong_y: bool
    ly_do: str = ""


class XinGo(BaseModel):
    ly_do: str = ""


@router.get("/hang-doi")
def hang_doi(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Hàng đợi + ba ô đếm, cho các vai khai ở `/duyet-cong-bo` (xem đầu tệp).

    Người ĐỌC được mà KHÔNG duyệt được vẫn có ích: Ban Kiểm soát và CNTT thấy hàng đợi dài bao
    nhiêu và cái cũ nhất chờ mấy ngày — đó là con số quản trị. `ban_duyet_duoc` trả về False nên
    màn hình không sáng nút, và hai cửa ghi ở dưới từ chối thẳng.
    """
    return DY.hang_doi(db, u)


@router.post("/{danh_gia_id}/duyet")
def duyet(danh_gia_id: int, data: QuyetDinh,
          u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Một trong ba người bấm. MỘT chữ ký là đủ — Chủ tịch chốt 16/10/2026."""
    dg = db.get(DanhGiaSauTour, danh_gia_id)
    if not dg:
        raise HTTPException(404, "Không có nhận xét này")
    kq = DY.duyet(db, u, dg, data.dong_y, data.ly_do)
    if not kq.get("xong"):
        raise HTTPException(403, kq.get("loi") or "Không bấm được")
    db.commit()
    return kq


@router.post("/{danh_gia_id}/go")
def go(danh_gia_id: int, data: XinGo,
       u: User = Depends(current_user), db: Session = Depends(get_db)):
    """GỠ — lệch chiều có chủ ý so với đăng: xem `dong_y.go`.

    Không có hàng rào chồng vai ở đây. Một hàng rào ngăn người ta gỡ một thứ đang hiển thị sai là
    hàng rào đặt ngược chiều.
    """
    dg = db.get(DanhGiaSauTour, danh_gia_id)
    if not dg:
        raise HTTPException(404, "Không có nhận xét này")
    kq = DY.go(db, u, dg, data.ly_do)
    if not kq.get("xong"):
        raise HTTPException(403, kq.get("loi") or "Không gỡ được")
    db.commit()
    return kq
