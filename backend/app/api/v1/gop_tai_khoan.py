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
from app.services import sua_xoa_tai_khoan as SX
from app.services.access import BASE_VIEW

XEM = BASE_VIEW + ("hcns", "ketoan", "cntt")

# BA DANH SÁCH GHI, ANH TUẤN CHỐT 24/9/2026 — và chỗ chúng khác nhau là chỗ đáng đọc.
#
# GỘP thêm `hcns` so với bản 19/9. HC-NS là người phát hiện ra trùng khi đối chiếu bảng lương;
# bắt họ đi nhờ người khác bấm một việc chính họ tìm ra là thêm một bước không ai được lợi.
#
# SỬA và XOÁ KHÔNG CÓ `cntt`, dù gộp thì có. Không phải sót. Gộp là DỌN DỮ LIỆU — chuyển các dòng
# đang trỏ vào tài khoản này sang tài khoản kia, không đổi một chữ nào trong hồ sơ ai. Sửa họ tên
# hay mã nhân viên là đổi HỒ SƠ NHÂN SỰ, và hồ sơ nhân sự là của HC-NS, không phải của CNTT.
#
# XOÁ hẹp đúng bằng SỬA chứ không hẹp hơn, vì hàng rào thật của nút xoá không nằm ở danh sách vai:
# nó nằm ở ba điều kiện trong `sua_xoa_tai_khoan.co_the_xoa` — đã khoá, còn 0 dòng, không tự xoá
# mình. Một tài khoản còn dữ liệu thì Chủ tịch bấm cũng không xoá được.
GOP = ("chutich", "tgd", "hcns", "cntt")
SUA = ("hcns", "chutich", "tgd")
XOA = ("hcns", "chutich", "tgd")

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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# SỬA VÀ XOÁ HỒ SƠ TÀI KHOẢN — TC-83, anh Tuấn chốt 24/9/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐẶT DƯỚI TIỀN TỐ SẴN CÓ `/api/v1/gop-tai-khoan`, không sinh tiền tố mới: ba việc này cùng một
# màn hình và cùng một chủ đề — dọn lại hồ sơ tài khoản. Không tiền tố mới nghĩa là bảng phạm vi
# vai trò KHÔNG đổi một con số nào, và hàng rào thật nằm ở `require_roles` của từng cửa.

class SuaHoSo(BaseModel):
    full_name: str | None = None
    staff_code: str | None = None
    department: str | None = None


@router.put("/ho-so/{uid}")
def sua_ho_so(uid: int, data: SuaHoSo,
              u: User = Depends(require_roles(*SUA, mo_ta="sửa hồ sơ tài khoản")),
              db: Session = Depends(get_db)):
    """Sửa họ tên, mã nhân viên, bộ phận.

    KHÔNG sửa được vai trò, mật khẩu hay phân công đơn vị ở đây — ba thứ ấy có cửa riêng ở màn
    hình Tài khoản & phân quyền và ở sơ đồ tổ chức. Hai lối vào cho cùng một việc là hai chỗ phải
    rào, và quên một chỗ là hở.
    """
    try:
        kq = SX.sua(db, u, uid, {k: v for k, v in data.model_dump().items() if v is not None})
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return kq


@router.get("/co-the-xoa/{uid}")
def co_the_xoa(uid: int,
               u: User = Depends(require_roles(*XOA, mo_ta="kiểm tra xoá được tài khoản chưa")),
               db: Session = Depends(get_db)):
    """Xoá được chưa, và nếu chưa thì vì sao. KHÔNG ghi gì.

    Màn hình gọi cửa này để quyết định nút Xoá sáng hay tối, và để in ra CÂU GIẢI THÍCH thay vì
    một nút tối không nói gì. Một nút tối không nói vì sao là một nút người dùng bấm mãi rồi đi
    hỏi CNTT.
    """
    try:
        return SX.co_the_xoa(db, u, uid)
    except ValueError as ex:
        raise HTTPException(404, str(ex))


class XoaTaiKhoan(BaseModel):
    ly_do: str
    xac_nhan: bool = False


@router.delete("/{uid}")
def xoa_tai_khoan(uid: int, data: XoaTaiKhoan,
                  u: User = Depends(require_roles(*XOA, mo_ta="xoá tài khoản")),
                  db: Session = Depends(get_db)):
    """Xoá vĩnh viễn một tài khoản ĐÃ TRỐNG. Không có nút hoàn lại.

    `xac_nhan=false` chỉ trả bản xem trước và KHÔNG ghi — mặc định, cố ý, cùng nếp với nút gộp:
    một thao tác không hoàn lại được thì bước mặc định phải là bước không làm gì.

    Bia mộ ghi TRƯỚC khi xoá. Ghi sau thì mất luôn dữ liệu cần ghi.
    """
    try:
        kq = SX.xoa(db, u, uid, data.ly_do, data.xac_nhan)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if data.xac_nhan:
        db.commit()
    return kq


@router.get("/bia-mo")
def bia_mo(tim: str = "",
           u: User = Depends(require_roles(*XEM, mo_ta="danh sách tài khoản đã xoá")),
           db: Session = Depends(get_db)):
    """Những tài khoản đã bị xoá — chỗ duy nhất tra ngược một tên đăng nhập đã biến mất.

    MỞ CHO CẢ NHÓM XEM chứ không chỉ nhóm xoá, và đó là điểm của nó: người cần tra là người đang
    đọc một dòng nhật ký cũ, thường là Kế toán hoặc Ban kiểm soát, không phải người đã bấm xoá.
    """
    return SX.bia_mo(db, tim)
