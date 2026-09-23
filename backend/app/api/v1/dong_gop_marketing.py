"""Cửa API: đóng góp doanh thu của Marketing — nhóm 2.7.

TIỀN TỐ RIÊNG `/api/v1/dong-gop-marketing`, KHÔNG gắn vào `/api/v1/marketing`.

Nhóm `/api/v1/marketing` đang có hơn ba mươi cửa, trong đó có cửa LẬP và DUYỆT ngân sách. Gắn cửa
đọc doanh thu vào đó là nới cả nhóm ấy cho mọi vai mở được màn hình này — phần dôi ra vẫn là quyền
đã cấp. Bài học đã trả giá năm lần trong kho này (`/api/v1/tong-dai`, `/api/v1/so-con-no`, TC-73,
TC-74, TC-76).

MỘT CỬA GHI DUY NHẤT: `POST /gan-nguon`, gắn nguồn cho một booking chưa truy được nguồn.

Bản đầu của vòng này định khai màn hình là "chỉ xem". `test_man_hinh_co_cua_nhap` chặn lại, và
chặn đúng: danh sách ngoại lệ ấy đã chạm trần 8, và nó có trần để ngăn đúng việc nới thêm một dòng
thay vì dừng lại hỏi con số kia vào hệ thống bằng cửa nào. Hỏi xong thì thấy cửa phải nằm ở đây
thật — người biết một booking đến từ kênh nào là người Marketing, và họ chỉ phát hiện ra nó thiếu
khi nhìn bảng độ phủ của chính màn hình này.

Ô chọn chiến dịch trên DÒNG CHI thì vẫn nằm ở cửa cũ `/api/v1/marketing` và màn hình cũ
`/marketing` — đúng nơi người lập ngân sách đang làm việc, không dựng cửa nhập thứ hai cho nó.

KHÔNG CẮT DÒNG THEO ĐƠN VỊ, VÀ ĐÓ LÀ MỘT QUYẾT ĐỊNH CHỨ KHÔNG PHẢI MỘT CHỖ QUÊN. Màn hình Kinh
doanh Lẻ cắt theo phân công (SEC-02) vì câu hỏi ở đó là "người của tôi bán được bao nhiêu" — số
của người khác không phải việc của mình. Câu hỏi ở đây khác hẳn: "tiền quảng cáo của công ty kéo về
được bao nhiêu doanh thu". Một chiến dịch chạy trên toàn công ty, cắt nó theo team bán hàng thì con
số không còn nghĩa gì. Hàng rào ở đây là DANH SÁCH VAI hẹp, không phải phép cắt dòng.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import dong_gop_marketing as DG
from app.services.access import BASE_VIEW, MARKETING

# Cùng danh sách vai với màn hình `/marketing` (ngân sách và chiến dịch), cộng `ptgd_kd`? KHÔNG.
# Giữ đúng bằng `/marketing`: ai lập được ngân sách thì xem được kết quả của ngân sách ấy, không
# rộng hơn một vai nào. Kế toán có mặt vì họ đối chiếu chi phí; Giám đốc Kinh doanh có mặt vì phần
# doanh thu trong bảng này là doanh thu của khối anh ấy, nhìn từ phía nguồn khách.
XEM = BASE_VIEW + MARKETING + ("ptgd_mkt", "gd_kd", "ketoan", "cntt")

# GHI hẹp hơn XEM. Cố ý KHÔNG có `gd_kd` và `ketoan`: hai vai ấy đọc bảng này để đối chiếu, còn
# người biết một booking đến từ kênh nào là người Marketing. Cũng cố ý không có `bks`/`robot_ks` —
# hai vai đọc-tất-cả ấy bị chặn mọi thao tác ghi ở mọi nơi khác trong kho, giữ đúng nếp ở đây.
GHI = ("chutich", "tgd", "ptgd_mkt", "cntt") + MARKETING

router = APIRouter(prefix="/api/v1/dong-gop-marketing", tags=["dong-gop-marketing"])


@router.get("/thang")
def thang(ky: str, mang: str = "",
          u: User = Depends(require_roles(*XEM, mo_ta="đóng góp doanh thu của Marketing")),
          db: Session = Depends(get_db)):
    """Một kỳ: doanh thu theo kênh, theo chiến dịch, và độ phủ truy nguồn.

    `mang` rỗng = cả ba luồng. Truyền "le" hoặc "doan" để trả lời mục 2.7.2 — hiệu quả khách lẻ so
    với khách đoàn.
    """
    try:
        return DG.thang(db, ky, mang)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/chien-dich/{chien_dich_id}")
def mot_chien_dich(chien_dich_id: int, ky: str,
                   u: User = Depends(require_roles(*XEM, mo_ta="truy vết một chiến dịch")),
                   db: Session = Depends(get_db)):
    """Mục 2.7.1 — truy vết từ chiến dịch xuống từng booking nó kéo về.

    Cố ý xuống TỪNG BOOKING chứ không dừng ở con số tổng: một chiến dịch báo 2 tỷ mà không chỉ ra
    được hai tỷ ấy gồm những đơn nào thì không ai kiểm được, và một con số không kiểm được sớm muộn
    sẽ bị đem ra cãi thay vì đem ra dùng.
    """
    try:
        return DG.chien_dich_chi_tiet(db, chien_dich_id, ky)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class GanNguon(BaseModel):
    booking_id: int
    kenh: str = ""
    chien_dich_id: int | None = None
    ly_do: str


@router.post("/gan-nguon")
def gan_nguon(data: GanNguon,
              u: User = Depends(require_roles(*GHI, mo_ta="gắn nguồn cho booking chưa rõ nguồn")),
              db: Session = Depends(get_db)):
    """Điền chỗ TRỐNG, không sửa đè. Ba hàng rào và lý do từng cái ở `services/dong_gop_marketing.py`."""
    try:
        kq = DG.gan_nguon(db, u, data.booking_id, data.kenh, data.chien_dich_id, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return kq
