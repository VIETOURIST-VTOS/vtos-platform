"""CỬA NHẬP KẾ HOẠCH THÁNG – đọc bảng một năm, ghi từng ô.

Phép tính và luật nằm ở services/ke_hoach.py; tệp này chỉ là cửa: nhận, chặn, gọi, trả.

═══════════════════════════════════════════════════════════════════════════════════════════════
HAI DANH SÁCH VAI TRÒ, KHÔNG PHẢI MỘT
═══════════════════════════════════════════════════════════════════════════════════════════════
XEM rộng hơn GHI, và đó là khác biệt đáng giữ. Ban lãnh đạo và Ban Kiểm soát phải ĐỌC được chỉ tiêu
để đối chiếu với kết quả; nhưng người GÕ chỉ tiêu vào hệ thống là Kế toán, một cửa duy nhất. Gộp hai
danh sách làm một thì hoặc Ban Kiểm soát sửa được thước đo mà mình đang dùng để đo, hoặc Chủ tịch
không đọc được kế hoạch của chính công ty mình.

Chủ tịch và Tổng giám đốc CÓ trong danh sách ghi – không phải để hai người ấy ngồi nhập bảng, mà vì
chỉ tiêu là quyết định của họ: khi Hội đồng quản trị điều chỉnh giữa năm, người sửa phải sửa được mà
không cần mượn tài khoản Kế toán. Nhật ký ghi rõ ai sửa, nên quyền rộng ở đây không làm mờ trách
nhiệm.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ke_hoach as KH

router = APIRouter(prefix="/api/v1/ke-hoach", tags=["ke-hoach-thang"])

XEM = ("chutich", "tgd", "bks", "robot_ks", "ketoan", "cntt")
GHI = ("chutich", "tgd", "ketoan")


class OKeHoach(BaseModel):
    ky: str
    company_id: int
    chi_tieu: str
    # `None` là XOÁ ô, không phải 0. Kiểu để mở đúng vì đây là ý nghĩa nghiệp vụ thật: Kế toán xoá
    # một ô nhập nhầm khác hẳn Kế toán đặt chỉ tiêu bằng không đồng.
    gia_tri: float | None = None
    ly_do: str = ""


@router.get("", dependencies=[Depends(require_roles(*XEM, mo_ta="kế hoạch tháng"))])
def xem(nam: int = 0, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Bảng kế hoạch của một năm. Không truyền năm thì lấy năm hiện tại.

    Cắt dòng theo phạm vi pháp nhân NẰM TRONG truy vấn (services/ke_hoach.doc_nam), không ở đây và
    tuyệt đối không ở giao diện.
    """
    from datetime import date
    nam = nam or date.today().year
    # Chặn năm vô lý ngay ở cửa: `ky.startswith("0-")` không lỗi, chỉ trả về rỗng, và một bảng rỗng
    # thì người dùng đọc thành "chưa ai nhập" chứ không đọc thành "anh gõ sai năm".
    if nam < 2000 or nam > 2100:
        raise HTTPException(422, f"Năm {nam} nằm ngoài khoảng 2000–2100.")
    return KH.doc_nam(db, nam, u)


@router.put("", dependencies=[Depends(require_roles(*GHI, mo_ta="kế hoạch tháng"))])
def ghi(o: OKeHoach, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Lưu MỘT ô. Một ô một lần gọi – không nhận cả bảng.

    Vì sao không nhận cả bảng trong một lần gọi: bảng 12 tháng × nhiều pháp nhân × 2 chỉ tiêu, và
    trong đó thường chỉ vài ô vừa đổi. Gửi cả bảng thì mỗi lần bấm Lưu là mỗi dòng đi qua hàm ghi,
    và hàm ghi phải tự đoán ô nào thật sự đổi. Đoán sai theo hướng nào cũng hỏng: đếm nhầm số lần
    sửa muộn, hoặc đòi lý do cho những ô người dùng không hề chạm vào.
    """
    try:
        kq = KH.ghi(db, o.ky, o.company_id, o.chi_tieu, o.gia_tri, o.ly_do, u)
    except ValueError as ex:
        # Không commit: ngoại lệ ném ra giữa chừng thì phiên đang mang thay đổi dở dang.
        db.rollback()
        raise HTTPException(422, str(ex))
    db.commit()
    return kq


@router.get("/hop-nhat", dependencies=[Depends(require_roles(*XEM, mo_ta="kế hoạch tháng"))])
def hop_nhat(ky: str = "", db: Session = Depends(get_db)):
    """Kế hoạch hợp nhất của MỘT tháng – hoặc rỗng kèm danh sách pháp nhân còn thiếu."""
    from datetime import date
    ky = ky or KH.ky_cua(date.today())
    if not KH.hop_le_ky(ky):
        raise HTTPException(422, f"Kỳ '{ky}' không đúng dạng YYYY-MM.")
    return KH.hop_nhat(db, ky)


@router.get("/theo-thang", dependencies=[Depends(require_roles(*XEM, mo_ta="kế hoạch tháng"))])
def theo_thang(nam: int = 0, db: Session = Depends(get_db)):
    """Mười hai tháng của một năm, cho biểu đồ trên màn hình nhập."""
    from datetime import date
    nam = nam or date.today().year
    if nam < 2000 or nam > 2100:
        raise HTTPException(422, f"Năm {nam} nằm ngoài khoảng 2000–2100.")
    return {"nam": nam, "thang": KH.theo_thang(db, nam),
            "chi_tieu": [{"ma": k, "ten": v} for k, v in KH.CHI_TIEU.items()]}
