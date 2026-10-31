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


@router.get("/anh/nh/{pid}/{co}")
def anh_album(pid: int, co: str, request: Request, db: Session = Depends(get_db)):
    """AT-2a: ảnh album nhà hàng — chỉ ảnh ĐÃ DUYỆT, căn cứ đã xác minh, của nhà hàng đang hiện; chỉ bản hiển thị
    / ảnh nhỏ (bản gốc không bao giờ ra cổng)."""
    _phanh(request)
    try:
        data, a = NH.tep_album(db, None, pid, co)
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/anh/td/{tid}/{co}")
def anh_thuc_don(tid: int, co: str, request: Request, db: Session = Depends(get_db)):
    """AT-2b: trang thực đơn của bản ĐANG DÙNG, nhà hàng đang hiện; không bao giờ tệp gốc."""
    _phanh(request)
    try:
        data, a = NH.tep_trang(db, None, tid, co)
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/anh/{aid}")
def anh(aid: int, request: Request, db: Session = Depends(get_db)):
    """Ảnh của nhà hàng đang hiện / nội dung đã bật. Ảnh khác (kể cả ảnh cũ đã thay) trả 404."""
    _phanh(request)
    try:
        data, a = NH.anh_cong(db, aid)
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/anh/dg/{gid}/{i}/{co}")
def anh_danh_gia(gid: int, i: int, co: str, request: Request, db: Session = Depends(get_db)):
    """AT-3: ảnh khách đính kèm đánh giá — bài và ảnh đang hiện, nhà hàng đang hiện; chỉ bản làm nhẹ (đã bỏ EXIF).
    Lưu đệm ngắn: Marketing ẩn ảnh vi phạm thì ảnh rút khỏi trang trong ít phút."""
    from app.services import danh_gia_nh as DG
    _phanh(request)
    try:
        data, a = DG.tep_anh(db, gid, i, co)
    except DG.LoiDanhGia as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/webp", headers={"Cache-Control": "public, max-age=600"})


@router.get("/danh-gia/{nid}")
def danh_gia(nid: int, request: Request, trang: int = 1, xep: str = "moi", db: Session = Depends(get_db)):
    """AT-3: đánh giá đang hiện của một nhà hàng đang hiện — chỉ đọc; tên đã che, không SĐT, không mã đơn."""
    from app.services import danh_gia_nh as DG
    _phanh(request)
    try:
        NH.mot_nha_hang_cong(db, nid)
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return DG.cong(db, nid, trang, 20, xep)


# ── KS-16f · video nhà hàng cho thẻ <video> trên cổng (chỉ video đang hiện của nhà hàng đang hiện) ─────────
from app.api.v1.video_dich_vu import tra_anh as _vd_anh, tra_video as _vd_xem  # noqa: E402


@router.get("/video/{vid:int}/xem")
def video_xem(vid: int, request: Request, t: str = "", db: Session = Depends(get_db)):
    """KS-16f — video đang hiện của nhà hàng đang hiện (hoặc vé VTOS ?t=); có phanh."""
    _phanh(request)
    return _vd_xem(db, vid, "nha_hang", t)


@router.get("/video/{vid:int}/anh")
def video_anh(vid: int, request: Request, t: str = "", db: Session = Depends(get_db)):
    _phanh(request)
    return _vd_anh(db, vid, "nha_hang", t)
