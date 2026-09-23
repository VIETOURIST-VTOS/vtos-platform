"""Cửa API: chuyển đổi và phối hợp Sales — nhóm 2.6.

TIỀN TỐ RIÊNG `/api/v1/chuyen-doi-lead`, KHÔNG gắn vào `/api/v1/leads`.

Nhóm `/api/v1/leads` là nhóm rộng nhất của cả phân hệ Marketing — nó đang mở cho BASE_VIEW +
SALES + OPERATIONS + MARKETING + ptgd_mkt + cntt, tức gần như cả công ty, vì ai cũng cần tra một
số điện thoại. Gắn cửa BÀN GIAO LEAD vào đó là cho ngần ấy vai quyền chuyển lead của người khác
sang tay mình. Bài học đã trả giá sáu lần trong kho này.

HAI DANH SÁCH VAI, VÀ CHỖ KHÁC NHAU ĐÁNG GHI

`XEM` gồm cả Marketing lẫn Kinh doanh. Đây là điểm khác hẳn nhóm 2.7: bảng 2.7 hỏi "tiền quảng
cáo thu về bao nhiêu" nên là việc của người tiêu tiền; ba câu của nhóm 2.6 hỏi về QUÃNG GIỮA hai
phòng — Marketing giao lead, Sales xử lý — nên cả hai bên phải nhìn thấy cùng một bảng. Giấu nửa
bảng khỏi một bên là cách chắc chắn để mỗi phòng tự giữ một con số riêng rồi mang ra cãi nhau.

`GHI` hẹp: người phụ trách, không phải người bị chấm. Cố ý KHÔNG có `nv_kd` — nhân viên kinh
doanh tự chuyển lead đang nằm im của mình sang người khác là tự xoá dấu vết tồn đọng của chính
mình, và bảng 2.6.2 tồn tại chính để nhìn thấy dấu vết ấy.

MỘT NGOẠI LỆ CÓ CHỦ Ý: `nv_mkt` được GHI. Người Marketing không nhận lead nên không có gì để
giấu, mà họ lại là người ngồi nhìn bảng tồn đọng hằng ngày và biết lead nào nên chuyển đi.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import chuyen_doi_lead as CD
from app.services.access import BASE_VIEW, MARKETING, SALES

XEM = BASE_VIEW + MARKETING + SALES + ("ptgd_mkt", "ptgd_doan", "hcns", "cntt")
GHI = ("chutich", "tgd", "ptgd_mkt", "gd_kd", "tp_kd", "cntt") + MARKETING

router = APIRouter(prefix="/api/v1/chuyen-doi-lead", tags=["chuyen-doi-lead"])


@router.get("/chuyen-doi")
def chuyen_doi(ky: str, kenh: str = "",
               u: User = Depends(require_roles(*XEM, mo_ta="chuyển đổi lead theo mốc ngày")),
               db: Session = Depends(get_db)):
    """2.6.1 — lead của kỳ này chốt sau 30 / 60 / 90 ngày."""
    try:
        return CD.chuyen_doi_theo_moc(db, ky, kenh)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/ton-dong")
def ton_dong(u: User = Depends(require_roles(*XEM, mo_ta="lead tồn đọng và thời hạn xử lý")),
             db: Session = Depends(get_db)):
    """2.6.2 — lead đang nằm im, ai giữ, quá hạn bao lâu.

    KHÔNG nhận tham số thời điểm từ người gọi. `bay_gio` của lớp dịch vụ chỉ để phép thử bơm một
    mốc cố định vào; mở nó ra cửa HTTP là cho người dùng tự chọn một thời điểm mà ở đó mình không
    quá hạn.
    """
    return CD.ton_dong(db)


@router.get("/ly-do-mat")
def ly_do_mat(ky: str = "",
              u: User = Depends(require_roles(*XEM, mo_ta="lý do mất khách")),
              db: Session = Depends(get_db)):
    """2.6.3 — mất vì lý do gì, và bao nhiêu số điện thoại quay lại sau khi đã đánh dấu mất."""
    return CD.ly_do_mat(db, ky)


@router.get("/lead/{lead_id}/ban-giao")
def lich_su(lead_id: int,
            u: User = Depends(require_roles(*XEM, mo_ta="lịch sử bàn giao một lead")),
            db: Session = Depends(get_db)):
    """Sổ bàn giao của một lead. Bảng `lead_ban_giao` đã có dữ liệu từ đường nạp tệp nhưng trước
    vòng này không màn hình nào đọc nó — dữ liệu được ghi mà không ai xem được."""
    return {"lead_id": lead_id, "rows": CD.lich_su_ban_giao(db, lead_id)}


class BanGiao(BaseModel):
    lead_id: int
    den_nguoi_id: int | None = None
    han_moi: date | None = None
    ly_do: str


@router.post("/ban-giao")
def ban_giao(data: BanGiao,
             u: User = Depends(require_roles(*GHI, mo_ta="bàn giao lead")),
             db: Session = Depends(get_db)):
    """Chuyển lead sang người khác, hoặc đổi hạn xử lý. Ghi vào `lead_ban_giao`, không dựng bảng
    nhật ký thứ hai cho cùng một việc."""
    try:
        kq = CD.ban_giao(db, u, data.lead_id, data.den_nguoi_id, data.han_moi, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return kq


class GhiLyDo(BaseModel):
    lead_id: int
    ma_ly_do: str
    ghi_chu: str = ""


@router.post("/ly-do-mat")
def ghi_ly_do(data: GhiLyDo,
              u: User = Depends(require_roles(*GHI, mo_ta="ghi lý do mất khách")),
              db: Session = Depends(get_db)):
    """CHỈ ĐIỀN CHỖ TRỐNG — cùng nếp với cửa gắn nguồn của nhóm 2.7. Sửa một lý do đã ghi là đổi
    câu trả lời cũ của người khác, việc ấy đi qua màn hình Khách hàng tiềm năng."""
    try:
        kq = CD.ghi_ly_do_mat(db, u, data.lead_id, data.ma_ly_do, data.ghi_chu)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return kq
