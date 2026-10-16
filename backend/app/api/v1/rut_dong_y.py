# -*- coding: utf-8 -*-
"""CỬA CÔNG KHAI THỨ HAI — khách tự rút đồng ý đăng. KHÔNG cần đăng nhập.

═══════════════════════════════════════════════════════════════════════════════════════════════
ĐỌC KỸ TRƯỚC KHI SỬA TỆP NÀY — VÀ ĐỌC CẢ `khao_sat_cong_khai.py`
═══════════════════════════════════════════════════════════════════════════════════════════════
Trước đợt này VTOS có ĐÚNG MỘT cửa không đứng sau `Depends(current_user)`: trang khảo sát. Chú
thích trong tệp ấy ghi rõ "KHÔNG thêm đường thứ ba ở đây" — nên cửa rút KHÔNG nối vào đó mà đứng
riêng, đúng cái tệp ấy dặn, và có tiền tố riêng `/api/v1/rut-dong-y`.

MỞ CỬA THỨ HAI RA ĐƯỜNG LÀ MỘT QUYẾT ĐỊNH VỀ AN TOÀN DỮ LIỆU, KHÔNG PHẢI MỘT VIỆC KỸ THUẬT.
Chủ tịch chốt ngày 16/10/2026 sau khi nghe đánh đổi: đường tự phục vụ thì khách rút được ngay
không phiền ai, đổi lại là thêm một cửa ra đường. Ghi ra đây để người sau biết đây là quyết định
có người ký, không phải một tệp ai đó tiện tay thêm vào.

BỐN ĐIỀU KIỆN CỨNG, và cả bốn đều có phép thử canh:

    1. MÃ DÙNG MỘT LẦN. Bấm rồi thì mọi lần sau chỉ đọc ra câu xác nhận, không đổi được gì nữa.
    2. KHÔNG MỘT CHỮ NÀO VỀ KHÁCH TRONG ĐƯỜNG DẪN. Mã sinh bằng `secrets.token_urlsafe(24)`,
       không suy được từ mã booking hay số điện thoại.
    3. CỬA NÀY CHỈ RÚT. Nó KHÔNG trả về nhận xét, KHÔNG trả về tên hướng dẫn viên, không trả về
       một trường dữ liệu nào. Một cửa không cần đăng nhập mà đọc được thì nó là cửa ĐỌC, và lúc
       ấy ta đã mở một thứ khác hẳn thứ mình định mở.
    4. CÓ HẠN VÀ CÓ PHANH. Hạn ở `dong_y.RUT_SONG_NGAY`; phanh đếm lượt theo địa chỉ mạng, cùng
       hình với cửa khảo sát.

MỘT ĐIỀU NỮA, DỄ QUÊN: cửa này KHÔNG nói cho người bấm biết mã ấy có thật hay không khi mã sai.
"Đường dẫn không đúng hoặc đã hết hiệu lực" là một câu duy nhất cho mọi trường hợp hỏng — mã bịa,
mã hết hạn, mã của người khác. Trả lời khác nhau cho từng trường hợp là biến cửa này thành máy dò.
"""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import dong_y as DY

router = APIRouter(prefix="/api/v1/rut-dong-y", tags=["rut-dong-y-cong-khai"])

# Phanh cùng hình với `khao_sat_cong_khai.py`, cố ý chép lại chứ không gom thành hàm chung: hai
# cửa ra đường nên hỏng độc lập với nhau. Gom lại thì một ngày ai đó nới phanh cho cửa khảo sát
# là nới luôn cho cửa này, mà không ai định thế.
_LUOT: dict[str, list[float]] = defaultdict(list)
CUA_SO_GIAY = 300.0
TOI_DA_TRONG_CUA_SO = 20


def _phanh(req: Request) -> bool:
    ip = (req.client.host if req.client else "") or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_TRONG_CUA_SO:
        _LUOT[ip] = v
        return False
    v.append(bay_gio)
    _LUOT[ip] = v
    if len(_LUOT) > 5000:
        for k in [k for k, x in _LUOT.items() if not x or bay_gio - x[-1] > CUA_SO_GIAY]:
            _LUOT.pop(k, None)
    return True


class XinRut(BaseModel):
    ly_do: str = ""


@router.get("/{ma}")
def xem(ma: str, request: Request):
    """Trang xác nhận trước khi rút. KHÔNG tra cơ sở dữ liệu, KHÔNG trả về dữ liệu nào.

    Cố ý không tra mã ở đây: tra rồi trả lời "mã này có thật" hay "mã này sai" là biến cửa thành
    máy dò. Trang chỉ hiện đúng câu hỏi xác nhận; đúng sai của mã chỉ lộ ra lúc khách bấm.
    """
    if not _phanh(request):
        return {"cho_phep": False,
                "loi_nhan": "Anh/chị thử hơi nhiều lần. Xin đợi vài phút rồi mở lại."}
    return {
        "cho_phep": True,
        "tieu_de": "Gỡ nhận xét khỏi hồ sơ hướng dẫn viên",
        "loi_nhan": ("Anh/chị bấm nút dưới đây thì nhận xét của anh/chị sẽ được gỡ khỏi hồ sơ "
                     "hướng dẫn viên công khai. Việc này không cần đăng nhập và không ảnh hưởng "
                     "tới chuyến đi hay tài khoản của anh/chị."),
        "nut": "Gỡ nhận xét của tôi",
    }


@router.post("/{ma}")
def rut(ma: str, data: XinRut, request: Request, db: Session = Depends(get_db)):
    """Khách bấm gỡ. Một mã chỉ đổi được trạng thái MỘT lần; bấm lại chỉ đọc ra câu xác nhận."""
    if not _phanh(request):
        return {"xong": False, "loi": "Anh/chị thử hơi nhiều lần. Xin đợi vài phút rồi mở lại."}
    kq = DY.rut(db, ma, data.ly_do)
    if kq.get("xong"):
        db.commit()
    return kq
