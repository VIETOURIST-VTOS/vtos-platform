# -*- coding: utf-8 -*-
"""CỬA 5.6 ĐÁNH GIÁ NHÂN SỰ — hai đường, vì hai nhóm người khác nhau.

    /api/v1/danh-gia-ns      → người CHẤM và người ĐỌC TỔNG HỢP, gắn màn hình /hr (thẻ Đánh giá & sự vụ)
    /api/v1/danh-gia-cua-toi → MỌI NHÂN VIÊN đọc bản của chính mình, gắn màn hình /cham-cong

TÁCH HAI ĐƯỜNG THAY VÌ MỘT, và đây là phần đáng ghi lại. Chủ tịch chốt 08/10/2026 "nhân viên được
thấy của mình". Màn hình /hr chỉ mở cho sáu vai — nhét cửa "bản của tôi" vào cùng tiền tố thì hoặc
phải nới /hr cho cả công ty (mở luôn hồ sơ nhân sự và bảng lương cho mọi người), hoặc nhân viên
không với tới cửa ấy. Cửa mở mà người không với tới thì cửa ấy chưa tồn tại — đúng lời khai của
`MOI_NHAN_VIEN` ở access.py khi mở màn hình đơn nghỉ phép.

Nên bản của tôi đi theo /cham-cong, màn hình đã mở cho mọi người làm việc ở đây. 0 dòng đổi trong
MENU_ROLES.

BA Ô MÁY ĐIỀN KHÔNG CÓ CỬA GHI. Không phải quên: trưởng phòng sửa được ô máy thì cái neo đo độ lệch
"điểm người − điểm máy" mất hết nghĩa. Thân hàm `cham()` bỏ qua mọi khoá a1/a2/a3 gửi lên, và có
một phép thử gửi thẳng a1_diem=5 lên để chắc nó bị bỏ.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import danh_gia_ns as DG
from app.services.access import BASE_VIEW, HR_TAB_ROLES, MOI_NHAN_VIEN, READ_ALL

router = APIRouter(prefix="/api/v1/danh-gia-ns", tags=["danh-gia-ns"])
router_toi = APIRouter(prefix="/api/v1/danh-gia-cua-toi", tags=["danh-gia-ns"])

# DÙNG LẠI bộ vai của thẻ "Đánh giá & sự vụ" thay vì khai bộ mới: khai bộ mới ở đây là lần viết
# phần mềm tự đặt quyền, mà quyền thuộc làn Phân quyền và có chữ ký.
XEM = HR_TAB_ROLES["incidents"]
# Người chấm là vai của TUYẾN KÝ ĐƠN — không khai danh sách thứ hai ở đây. Cửa nhận mọi vai trong
# XEM rồi `services.danh_gia_ns.cham()` mới đối chiếu phòng của người bị chấm với tuyến ấy; làm
# ngược lại thì có hai danh sách và chúng sẽ lệch nhau ở lần đổi người thứ nhất.
CHAM = XEM


class ChamIn(BaseModel):
    employee_id: int
    ky_loai: str = "thang"
    ky: str
    b1_diem: int | None = None
    b1_ly_do: str = ""
    b2_diem: int | None = None
    b2_ly_do: str = ""
    b3_diem: int | None = None
    b3_ly_do: str = ""
    nhan_xet: str = ""
    viec_phai_sua: str = ""
    de_xuat: str = ""


class MoIn(BaseModel):
    employee_id: int
    ky_loai: str = "thang"
    ky: str


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return DG.meta()


@router.get("")
def danh_sach(ky_loai: str = "thang", ky: str = "", phong: str = "",
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    try:
        return {"rows": DG.danh_sach(db, ky_loai, ky, phong)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/mo")
def mo(body: MoIn, u: User = Depends(require_roles(*CHAM)), db: Session = Depends(get_db)):
    """Mở bảng chấm của một người. Nạp lại ba ô máy điền theo số MỚI NHẤT cho tới lúc gửi."""
    try:
        return DG.mo_bang(db, body.employee_id, body.ky_loai, body.ky)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/cham")
def cham(body: ChamIn, u: User = Depends(require_roles(*CHAM)), db: Session = Depends(get_db)):
    o = body.model_dump(exclude={"employee_id", "ky_loai", "ky"})
    try:
        return DG.cham(db, u, body.employee_id, body.ky_loai, body.ky, o)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{danh_gia_id}/gui")
def gui(danh_gia_id: int, u: User = Depends(require_roles(*CHAM)), db: Session = Depends(get_db)):
    try:
        return DG.gui(db, u, danh_gia_id)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/do-lech")
def do_lech(ky_loai: str = "thang", ky: str = "",
            u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Độ lệch điểm người − điểm máy theo từng người chấm. CÁI NEO khi điểm bắt đầu đẻ ra tiền."""
    try:
        return DG.do_lech_nguoi_may(db, ky_loai, ky)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/thieu-nguon")
def thieu_nguon(ky: str = "", u: User = Depends(require_roles(*XEM)),
                db: Session = Depends(get_db)):
    """Kỳ này bao nhiêu người KHÔNG có số cho A1/A2 và vì sao — việc còn phải làm, không phải ô trống."""
    try:
        DG.kiem_ky("thang", ky)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return DG.thieu_nguon(db, ky)


@router.get("/phong-khong-ai-cham")
def phong_khong_ai_cham(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Phòng mà vai được chấm không tài khoản nào giữ — bảng của cả phòng ấy sẽ nằm im."""
    return {"rows": DG.phong_khong_ai_cham(db)}


# ── Bản của chính mình — mọi nhân viên ────────────────────────────────────────────────────────
@router_toi.get("")
def cua_toi(ky_loai: str = "", ky: str = "",
            u: User = Depends(require_roles(*(MOI_NHAN_VIEN + READ_ALL))),
            db: Session = Depends(get_db)):
    return {"rows": DG.cua_toi(db, u, ky_loai, ky)}
