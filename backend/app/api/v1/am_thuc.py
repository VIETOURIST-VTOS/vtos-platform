"""AT-1 · CỬA CÔNG KHAI «Khám phá ẩm thực» trên web VTD — xem trước khi đăng nhập (Chủ tịch duyệt 28/10/2026).

Ba luật của tệp này:
    1. CHỈ ĐỌC. Ba đường: danh sách, một nhà hàng, ảnh (chỉ ảnh đang dùng của mục đang hiện). Đặt bàn, thanh toán vẫn phải đăng nhập (cửa /cong/dat-ban).
    2. Chỉ in thứ TP Điều hành đã bật hiện, nội dung Marketing đã bật; không số điện thoại, không hợp đồng,
       không hoa hồng, không ghi chú nội bộ (dùng chung bộ lọc `_nh_cong` với cổng đã đăng nhập).
    3. Có phanh theo địa chỉ mạng.
"""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import nha_hang as NH

router = APIRouter(prefix="/api/v1/am-thuc", tags=["am-thuc-cong-khai"])

CUA_SO_GIAY, TOI_DA_TRONG_CUA_SO = 300, 60
_LUOT: dict = defaultdict(list)


_LUOT_ANH: dict = defaultdict(list)
TOI_DA_ANH = 400            # một trang có tới vài chục ảnh — ảnh đếm ở ngăn riêng, rộng hơn


def _phanh(req: Request) -> None:
    ip = (req.client.host if req.client else "") or "?"
    anh = "/anh/" in req.url.path
    luot, tran = (_LUOT_ANH, TOI_DA_ANH) if anh else (_LUOT, TOI_DA_TRONG_CUA_SO)
    bay_gio = time.time()
    v = [t for t in luot[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= tran:
        luot[ip] = v
        raise HTTPException(429, "Quá nhiều lượt từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(bay_gio)
    luot[ip] = v
    if len(luot) > 5000:
        for k in [k for k, x in luot.items() if not x or bay_gio - x[-1] > CUA_SO_GIAY]:
            luot.pop(k, None)


@router.get("")
def danh_sach(request: Request, tinh: str = "", q: str = "", chi_dat: bool = False, trang: int = 1,
              db: Session = Depends(get_db)):
    _phanh(request)
    return NH.danh_sach_cong(db, tinh[:80], "", 0, q[:80], chi_dat, max(1, min(trang, 200)))


@router.get("/anh/{aid}")
def anh(aid: int, request: Request, db: Session = Depends(get_db)):
    """Ảnh của nhà hàng đang hiện / nội dung đã bật. Ảnh khác (kể cả ảnh cũ đã thay) trả 404."""
    _phanh(request)
    try:
        data, a = NH.anh_cong(db, aid)
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{nid}")
def mot(nid: int, request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    try:
        return NH.mot_nha_hang_cong(db, nid)[1]
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
