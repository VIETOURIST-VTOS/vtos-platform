"""Cửa API: đối soát dữ liệu Marketing — nhóm 2.8.

TIỀN TỐ RIÊNG `/api/v1/doi-soat-marketing`. Bài học đã trả giá bảy lần trong kho này: gắn cửa mới
vào một tiền tố rộng sẵn có là nới CẢ NHÓM cho mọi vai đang có nhóm ấy, và phần dôi ra vẫn là
quyền đã cấp.

MỘT CỬA GHI DUY NHẤT: `POST /chot-ky`. Đây là hành động thật của người dùng — chốt số một kỳ để
lấy mốc chuẩn — chứ không phải một cửa dựng cho có để qua phép thử "màn hình nào cũng phải có cửa
nhập". Ba bảng còn lại của màn hình đều là gương soi những con số đã có cửa ở nơi khác:
    số lead khai báo   → màn hình Khách hàng tiềm năng
    chi theo hạng mục  → màn hình Ngân sách & chiến dịch
    nguồn của booking  → màn hình Đóng góp doanh thu của Marketing

VAI ĐƯỢC CHỐT SỐ HẸP HƠN VAI ĐƯỢC XEM, và chỗ hẹp đáng ghi: chốt số là đặt một mốc mà mọi báo cáo
sau đó đem ra so. Người tự đặt được mốc cho mình là người tự chấm được mình. Nên nhóm ghi chỉ có
Ban Tổng giám đốc, Phó TGĐ Marketing và Công nghệ thông tin — KHÔNG có `nv_mkt`, dù họ ghi được ở
cả hai nhóm 2.6 và 2.7.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import doi_soat_marketing as DS
from app.services.access import BASE_VIEW, MARKETING

XEM = BASE_VIEW + MARKETING + ("ptgd_mkt", "gd_kd", "ketoan", "cntt")

# Hẹp hơn XEM. Xem chú thích đầu tệp: người tự đặt được mốc cho mình là người tự chấm được mình.
CHOT = ("chutich", "tgd", "ptgd_mkt", "cntt")

router = APIRouter(prefix="/api/v1/doi-soat-marketing", tags=["doi-soat-marketing"])


@router.get("/doi-chieu")
def doi_chieu(ky: str,
              u: User = Depends(require_roles(*XEM, mo_ta="đối chiếu lead, doanh thu và chi phí")),
              db: Session = Depends(get_db)):
    """2.8.2 — ba con số đặt cạnh nhau, và hai sổ chi phí đặt cạnh nhau.

    Cửa này KHÔNG chọn bên nào đúng. Nó in cả hai, in phần chênh, dừng ở đó — chọn hộ một bên là
    đúng cái việc mà nhóm 2.8 sinh ra để ngăn.
    """
    try:
        return DS.doi_chieu(db, ky)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/trung-va-thieu-nguon")
def trung_va_thieu_nguon(ky: str,
                         u: User = Depends(require_roles(*XEM, mo_ta="trùng khách và thiếu nguồn")),
                         db: Session = Depends(get_db)):
    """2.8.1 — hai loại trùng để riêng: cùng số điện thoại (bình thường) và cùng dấu vân tay (rò)."""
    try:
        return DS.trung_va_thieu_nguon(db, ky)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/do-troi")
def do_troi(ky: str,
            u: User = Depends(require_roles(*XEM, mo_ta="độ trôi của số đã chốt")),
            db: Session = Depends(get_db)):
    """2.8.3 — số hiện tại đã trôi bao nhiêu so với lúc chốt. Trôi không phải là lỗi."""
    return DS.do_troi(db, ky)


class ChotKy(BaseModel):
    ky: str
    ghi_chu: str = ""


@router.post("/chot-ky")
def chot_ky(data: ChotKy,
            u: User = Depends(require_roles(*CHOT, mo_ta="chốt số kỳ Marketing")),
            db: Session = Depends(get_db)):
    """Chụp lại số của kỳ vào bảng `bao_cao_luu` — bảng SẴN CÓ, dùng chung với báo cáo phòng.

    Chụp lại là ghi đè bản cũ: mỗi kỳ giữ đúng MỘT mốc chuẩn. Muốn biết nó từng là gì thì đọc
    nhật ký nghiệp vụ — mỗi lần chốt để lại một dòng kèm cả bộ số cũ lẫn bộ số mới.
    """
    try:
        kq = DS.chot_ky(db, u, data.ky, data.ghi_chu)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return kq
