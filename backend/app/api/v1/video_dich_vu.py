"""KS-16f · cửa video — gắn vào ĐÚNG nhóm API sẵn có của khách sạn VTD và nhà hàng (không mở nhóm API mới):

  /api/v1/khach-san-vtd/{kid}/video, /api/v1/khach-san-vtd/video/{vid}/…   (VTOS, theo vai của khách sạn)
  /api/v1/nha-hang/{nid}/video,      /api/v1/nha-hang/video/{vid}/…        (VTOS, theo vai ảnh nhà hàng)
  /api/v1/ks-vtd-anh/video/{vid}/xem|anh  ·  /api/v1/am-thuc/video/{vid}/xem|anh
      — cho thẻ <video>/<img>: chỉ video ĐANG HIỆN của cơ sở ĐANG HIỆN; VTOS xem mọi video bằng vé ký ngắn hạn ?t=.
      Hai cửa ra đường này khai NGAY trong tệp của nhóm (khach_san_vtd.py, am_thuc.py), có phanh của nhóm.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import video_dich_vu as V


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except V.LoiVideo as ex:
        raise HTTPException(ex.status, str(ex))


class BatDauIn(BaseModel):
    ten_tep: str
    kich_thuoc: int
    thoi_luong: float = 0
    loai: str = "khac"
    tieu_de: str = ""
    nguon: str = ""
    xac_nhan_quyen: bool = False
    loai_phong_id: int | None = None
    mon_id: int | None = None
    thuc_don_id: int | None = None


class SuaIn(BaseModel):
    loai: str | None = None
    tieu_de: str | None = None
    nguon: str | None = None
    loai_phong_id: int | None = None
    mon_id: int | None = None
    thuc_don_id: int | None = None


def gan_cua_noi(router: APIRouter, doi: str, oid_ten: str) -> None:
    c = V._cfg(doi)
    xem = require_roles(*c["xem"], mo_ta="video")
    nhap = require_roles(*c["nhap"], mo_ta="tải video")

    @router.get(f"/{{{oid_ten}:int}}/video", name=f"video_ds_{doi}")
    def video_ds(request: Request, u: User = Depends(xem), db: Session = Depends(get_db)):
        return _goi(V.ds, db, u, doi, int(request.path_params[oid_ten]))

    @router.post(f"/{{{oid_ten}:int}}/video/bat-dau", name=f"video_bat_dau_{doi}")
    def video_bat_dau(request: Request, data: BatDauIn, u: User = Depends(nhap), db: Session = Depends(get_db)):
        v = _goi(V.bat_dau, db, u, doi, int(request.path_params[oid_ten]), data.model_dump())
        return {**V._out(v), "phan_byte": V.PHAN_BYTE, "so_phan": -(-v.kich_thuoc // V.PHAN_BYTE)}

    @router.put("/video/{vid:int}/phan/{so:int}", name=f"video_phan_{doi}")
    async def video_phan(vid: int, so: int, request: Request, u: User = Depends(nhap), db: Session = Depends(get_db)):
        data = await request.body()
        v = _goi(V.nhan_phan, db, u, vid, so, data)
        return {"ok": True, "da_nhan": len(v.phan or [])}

    @router.post("/video/{vid:int}/xong", name=f"video_xong_{doi}")
    def video_xong(vid: int, u: User = Depends(nhap), db: Session = Depends(get_db)):
        v = _goi(V.xong, db, u, vid)
        return {**V._out(v), "message": "Đã tải video — đang hiện"}

    @router.post("/video/{vid:int}/anh-dai-dien", name=f"video_anh_{doi}")
    async def video_anh(vid: int, tep: UploadFile = File(...), u: User = Depends(nhap), db: Session = Depends(get_db)):
        data = await tep.read(8 * 1024 * 1024 + 1)
        v = _goi(V.anh_dai_dien, db, u, vid, tep.filename or "anh.jpg", data)
        return {**V._out(v), "message": "Đã đổi ảnh đại diện"}

    @router.post("/video/{vid:int}/sua", name=f"video_sua_{doi}")
    def video_sua(vid: int, data: SuaIn, u: User = Depends(nhap), db: Session = Depends(get_db)):
        v = _goi(V.sua, db, u, vid, data.model_dump(exclude_unset=True))
        return {**V._out(v), "message": "Đã lưu"}

    @router.post("/video/{vid:int}/{viec}", name=f"video_viec_{doi}")
    def video_viec(vid: int, viec: str, u: User = Depends(nhap), db: Session = Depends(get_db)):
        f = {"an": lambda: V.an(db, u, vid, True), "hien": lambda: V.an(db, u, vid, False),
             "xoa": lambda: V.xoa(db, u, vid), "huy": lambda: V.huy(db, u, vid),
             "gioi-thieu": lambda: V.dat_gioi_thieu(db, u, vid),
             "len": lambda: V.doi_thu_tu(db, u, vid, True), "xuong": lambda: V.doi_thu_tu(db, u, vid, False)}.get(viec)
        if f is None:
            raise HTTPException(404, "Không có việc này")
        _goi(f)
        return {"ok": True, "message": {"an": "Đã ẩn video", "hien": "Video hiện lại", "xoa": "Đã xóa video",
                                        "huy": "Đã hủy tải", "gioi-thieu": "Đã đặt làm video giới thiệu"}.get(viec, "Đã đổi thứ tự")}


def tra_video(db: Session, vid: int, doi: str, t: str = ""):
    """Trả lời cho thẻ <video>: kho R2 → chuyển hướng sang đường tạm có chữ ký; kho cục bộ → tệp có hỗ trợ tua."""
    r = _goi(V.tep_xem, db, vid, doi, t)
    if r.get("url"):
        return RedirectResponse(r["url"], status_code=302, headers={"Cache-Control": "private, max-age=600"})
    return FileResponse(r["duong"], media_type=r["kieu"])


def tra_anh(db: Session, vid: int, doi: str, t: str = ""):
    data, a = _goi(V.tep_anh, db, vid, doi, t)
    return Response(content=data, media_type=a.kieu_noi_dung or "image/webp", headers={"Cache-Control": "public, max-age=86400"})
