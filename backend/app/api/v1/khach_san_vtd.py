"""KS-13 · Khách sạn hợp tác VTD — ba nhóm cửa:

  /api/v1/khach-san-vtd/*   — phía VTOS: Điều hành nhập, TP Điều hành duyệt + bật hiện.
  /api/v1/cong/ks-vtd/*     — phía NGOÀI (phiên cổng): tìm, xem, tính giá lựa chọn, gửi yêu cầu giữ phòng.
  /api/v1/ks-vtd-anh/*      — ảnh ĐÃ DUYỆT của khách sạn ĐANG HIỆN (bản hiển thị / ảnh nhỏ). Không phiên, có phanh.
"""
import time
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.db.session import get_db
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.services import khach_san_vtd as S

router_vtos = APIRouter(prefix="/api/v1/khach-san-vtd", tags=["khach-san-vtd"])
router_cong = APIRouter(prefix="/api/v1/cong/ks-vtd", tags=["khach-san-vtd"])
router_anh = APIRouter(prefix="/api/v1/ks-vtd-anh", tags=["khach-san-vtd"])

TOI_DA_TEP = 12 * 1024 * 1024
_LUOT: dict = defaultdict(list)
# Cửa ra đường chỉ có một đường ảnh — đếm ở ngăn riêng, rộng hơn (một trang danh sách có vài chục ảnh), như am_thuc.
CUA_SO_GIAY, TOI_DA_TRONG_CUA_SO, TOI_DA_ANH = 300, 60, 400


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiKhachSan as ex:
        raise HTTPException(ex.status, str(ex))


def _khach(tk: TaiKhoanNgoai) -> None:
    if tk.loai == "khach_hang" and tk.trang_thai != "khoa":
        return
    if tk.loai in ("doi_tac", "co_dong") and tk.trang_thai == "hoat_dong":
        return
    raise HTTPException(403, "Tài khoản chưa dùng được mục Khách sạn")


# ── VTOS ──────────────────────────────────────────────────────────────────────────────────────────
@router_vtos.get("")
def ds(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return _goi(S.ds_vtos, db, u)


# ── KS-15 · đánh giá: Marketing ẩn vì vi phạm, TP Điều hành xem lại ─────────────────────────────────────
@router_vtos.get("/danh-gia")
def dg_ds(loc: str = "", u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import danh_gia_ks as DGK
    try:
        return DGK.ds_noi_bo(db, u, loc)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))


class AnDgIn(BaseModel):
    ly_do: str
    ghi_chu: str = ""
    phan: str = "bai"


class XemLaiDgIn(BaseModel):
    giu: bool = True
    ghi_chu: str = ""


@router_vtos.post("/danh-gia/{gid:int}/an")
def dg_an(gid: int, data: AnDgIn, u: User = Depends(require_roles("nv_mkt", "ptgd_mkt")), db: Session = Depends(get_db)):
    from app.services import danh_gia_ks as DGK
    try:
        DGK.an(db, u, gid, data.ly_do, data.ghi_chu, data.phan)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))
    return {"message": "Đã ẩn — chờ TP Điều hành xem lại", **DGK.ds_noi_bo(db, u)}


@router_vtos.post("/danh-gia/{gid:int}/xem-lai")
def dg_xem_lai(gid: int, data: XemLaiDgIn, u: User = Depends(require_roles("tp_dh", "chutich", "tgd")), db: Session = Depends(get_db)):
    from app.services import danh_gia_ks as DGK
    try:
        DGK.xem_lai(db, u, gid, data.giu, data.ghi_chu)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))
    return {"message": "Giữ ẩn" if data.giu else "Đã hiện lại", **DGK.ds_noi_bo(db, u)}


@router_vtos.get("/cho-duyet")
def cho_duyet(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return _goi(S.cho_duyet, db, u)


class KsIn(BaseModel):
    ten: str
    tinh_thanh: str = ""
    khu_vuc: str = ""
    dia_chi: str = ""
    sao: int = 0
    loai: str = "khach_san"
    km_trung_tam: float | None = None
    gan: str = ""
    noi_bat: str = ""
    mo_ta: str = ""
    tien_ich: list[str] = []
    gio_nhan: str = "14:00"
    gio_tra: str = "12:00"
    cs_tre_em: str = ""
    cs_giuong_phu: str = ""
    cs_vat_nuoi: str = ""
    cs_khac: str = ""
    thue_phi_pt: float = 0
    lien_he_noi_bo: str = ""
    ghi_chu_noi_bo: str = ""


@router_vtos.post("")
def tao(data: KsIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    k = _goi(S.luu_ks, db, u, data.model_dump())
    return {"id": k.id, "message": f"Đã thêm {k.ma} · {k.ten}"}


@router_vtos.get("/{kid:int}")
def mot(kid: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return _goi(S.mot_vtos, db, u, kid)


@router_vtos.post("/{kid:int}")
def sua(kid: int, data: KsIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    k = _goi(S.luu_ks, db, u, data.model_dump(), kid)
    return {"id": k.id, "message": "Đã lưu hồ sơ"}


class BatIn(BaseModel):
    bat: bool


@router_vtos.post("/{kid:int}/hien-cong")
def hien_cong(kid: int, data: BatIn, u: User = Depends(require_roles(*S.VAI_DUYET)), db: Session = Depends(get_db)):
    k = _goi(S.bat_hien, db, u, kid, data.bat)
    return {"message": f"{k.ten}: " + ("đang hiện trên cổng khách" if k.hien_cong else "đã tắt hiện")}


@router_vtos.post("/{kid:int}/ngung")
def ngung(kid: int, data: BatIn, u: User = Depends(require_roles(*S.VAI_DUYET)), db: Session = Depends(get_db)):
    k = _goi(S.ngung, db, u, kid, data.bat)
    return {"message": f"{k.ten}: " + ("đã ngừng hợp tác" if k.ngung else "hợp tác lại")}


class LoaiPhongIn(BaseModel):
    ten: str
    dien_tich: int = 0
    giuong: str = ""
    mo_ta: str = ""
    toi_da_nguoi_lon: int = 2
    toi_da_tre_em: int = 0
    so_phong: int = 1
    thu_tu: int = 0
    dang_ban: bool = True


@router_vtos.post("/{kid:int}/loai-phong")
def them_lp(kid: int, data: LoaiPhongIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    lp = _goi(S.luu_loai_phong, db, u, kid, data.model_dump())
    return {"id": lp.id, "message": f"Đã thêm loại phòng {lp.ten}"}


@router_vtos.post("/{kid:int}/loai-phong/{lid:int}")
def sua_lp(kid: int, lid: int, data: LoaiPhongIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    lp = _goi(S.luu_loai_phong, db, u, kid, data.model_dump(), lid)
    return {"id": lp.id, "message": f"Đã lưu {lp.ten}"}


class MuaIn(BaseModel):
    tu_ngay: str
    den_ngay: str
    gia_thuong: float
    gia_cuoi_tuan: float | None = None
    gia_niem_yet: float | None = None
    ghi_chu: str = ""


class GoiIn(BaseModel):
    ten: str
    bua_sang: bool = False
    huy_truoc_ngay: int | None = None
    dang_ban: bool = True
    mua: list[MuaIn] = []


@router_vtos.post("/loai-phong/{lid:int}/goi")
def them_goi(lid: int, data: GoiIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    g = _goi(S.luu_goi, db, u, lid, data.model_dump())
    return {"id": g.id, "message": f"Đã lưu gói {g.ten} — bấm «Gửi duyệt» để TP Điều hành duyệt"}


@router_vtos.post("/loai-phong/{lid:int}/goi/{gid:int}")
def sua_goi(lid: int, gid: int, data: GoiIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    g = _goi(S.luu_goi, db, u, lid, data.model_dump(), gid)
    return {"id": g.id, "message": f"Đã lưu gói {g.ten} — gói về «Nháp», bấm «Gửi duyệt»"}


@router_vtos.post("/goi/{gid:int}/gui-duyet")
def gui_duyet_goi(gid: int, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    g = _goi(S.gui_duyet_goi, db, u, gid)
    return {"message": f"Đã gửi duyệt gói {g.ten}"}


class DuyetIn(BaseModel):
    dong_y: bool = True
    ly_do: str = ""


@router_vtos.post("/goi/{gid:int}/duyet")
def duyet_goi(gid: int, data: DuyetIn, u: User = Depends(require_roles(*S.VAI_DUYET)), db: Session = Depends(get_db)):
    g = _goi(S.duyet_goi, db, u, gid, data.dong_y, data.ly_do)
    return {"message": f"Gói {g.ten}: " + ("đã duyệt — giá lên cổng" if g.trang_thai == "da_duyet" else "đã trả lại")}


async def _doc(f: UploadFile) -> bytes:
    data = await f.read()
    if len(data) > TOI_DA_TEP:
        raise HTTPException(400, "Tệp quá 12 MB")
    return data


@router_vtos.post("/{kid:int}/anh")
async def tai_anh(kid: int, tep: UploadFile = File(...), nhom: str = Form(""), loai_phong_id: str = Form(""),
                  chu_thich: str = Form(""), nguon: str = Form(""),
                  u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    data = await _doc(tep)
    x, moi = _goi(S.tai_anh, db, u, kid, tep.filename or "", data,
                  {"nhom": nhom, "loai_phong_id": loai_phong_id, "chu_thich": chu_thich, "nguon": nguon})
    return {"id": x.id, "moi": moi, "message": "Đã tải ảnh" if moi else "Ảnh này đã có trong album"}


class SuaAnhIn(BaseModel):
    nhom: str | None = None
    loai_phong_id: int | None = None
    chu_thich: str | None = None
    thu_tu: int | None = None
    la_bia: bool = False


@router_vtos.post("/anh/{pid:int}")
def sua_anh(pid: int, data: SuaAnhIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    d = {k: v for k, v in data.model_dump().items() if v is not None}
    if "loai_phong_id" not in data.model_fields_set:
        d.pop("loai_phong_id", None)
    else:
        d["loai_phong_id"] = data.loai_phong_id
    _goi(S.sua_anh, db, u, pid, d)
    return {"message": "Đã lưu ảnh"}


class IdsIn(BaseModel):
    ids: list[int]
    dong_y: bool = True
    ly_do: str = ""


@router_vtos.post("/anh/gui-duyet")
def gui_duyet_anh(data: IdsIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    n = _goi(S.gui_duyet_anh, db, u, data.ids)
    return {"message": f"Đã gửi duyệt {n} ảnh"}


@router_vtos.post("/anh/duyet")
def duyet_anh(data: IdsIn, u: User = Depends(require_roles(*S.VAI_DUYET)), db: Session = Depends(get_db)):
    r = _goi(S.duyet_anh, db, u, data.ids, data.dong_y, data.ly_do)
    bo = f" · bỏ qua {len(r['bo_qua'])} ảnh: {r['bo_qua'][0]['ly_do']}" if r["bo_qua"] else ""
    return {**r, "message": f"Đã {'duyệt' if data.dong_y else 'trả lại'} {r['da_doi']} ảnh{bo}"}


@router_vtos.post("/anh/{pid:int}/an")
def an_anh(pid: int, data: BatIn, u: User = Depends(require_roles(*S.VAI_NHAP)), db: Session = Depends(get_db)):
    _goi(S.an_anh, db, u, pid, data.bat)
    return {"message": "Đã ẩn ảnh" if data.bat else "Ảnh về nháp"}


@router_vtos.get("/anh/{pid:int}/{co}")
def anh_vtos(pid: int, co: str, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    data, a = _goi(S.tep_anh, db, u, pid, co)
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "private, max-age=600"})


# ── CỔNG ──────────────────────────────────────────────────────────────────────────────────────────
@router_cong.get("/tim")
def tim(tinh: str = "", vao: str = "", ra: str = "", nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
        tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return _goi(S.tim, db, tinh, vao, ra, nguoi_lon, tre_em, so_phong)


@router_cong.get("/{kid:int}")
def chi_tiet(kid: int, vao: str = "", ra: str = "", nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
             tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return _goi(S.chi_tiet_cong, db, kid, vao, ra, nguoi_lon, tre_em, so_phong)


class ChonIn(BaseModel):
    goi_id: int
    so: int


class TinhIn(BaseModel):
    vao: str
    ra: str
    chon: list[ChonIn]


@router_cong.get("/{kid:int}/danh-gia")
def danh_gia_cong(kid: int, trang: int = 1, xep: str = "moi", tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    """KS-15: bài đánh giá đang hiện của một khách sạn (tên khách đã che)."""
    from app.services import danh_gia_ks as DGK
    _khach(tk)
    try:
        return DGK.cong(db, kid, trang, 10, xep)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))


@router_cong.post("/{kid:int}/tinh")
def tinh(kid: int, data: TinhIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return _goi(S.tinh_lua_chon, db, kid, data.vao, data.ra, [c.model_dump() for c in data.chon])


class YeuCauIn(BaseModel):
    ngay_nhan: date
    ngay_tra: date
    nguoi_lon: int = 2
    tre_em: int = 0
    so_phong: int = 1
    chon: list[ChonIn] = []
    loai_phong: str = ""
    nguoi_nhan_phong: str = ""
    lien_he: str = ""
    yeu_cau_them: str = ""


@router_cong.post("/{kid:int}/yeu-cau")
def yeu_cau(kid: int, data: YeuCauIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    d = data.model_dump()
    d["chon"] = [c for c in d["chon"] if c["so"] > 0]
    r = _goi(S.gui_yeu_cau_giu, db, tk, kid, d)
    return {"don": r, "message": f"Đã gửi yêu cầu {r['the_tham_chieu']} · Vietourist báo giá trong giờ làm việc"}


def _phanh(req: Request) -> None:
    ip = (req.client.host if req.client else "") or "?"
    now = time.time()
    v = [t for t in _LUOT[ip] if now - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_ANH:
        _LUOT[ip] = v
        raise HTTPException(429, "Quá nhiều lượt từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(now)
    _LUOT[ip] = v
    if len(_LUOT) > 5000:
        for k in [k for k, x in _LUOT.items() if not x or now - x[-1] > CUA_SO_GIAY]:
            _LUOT.pop(k, None)


@router_anh.get("/dg/{gid:int}/{i:int}/{co}")
def anh_danh_gia(gid: int, i: int, co: str, request: Request, db: Session = Depends(get_db)):
    """KS-15: ảnh khách đánh giá (bản làm nhẹ, bài đang hiện, ảnh chưa ẩn, khách sạn đang hiện)."""
    _phanh(request)
    from app.services import danh_gia_ks as DGK
    try:
        data, a = DGK.tep_anh(db, gid, i, co)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/webp", headers={"Cache-Control": "public, max-age=86400"})


@router_anh.get("/{pid:int}/{co}")
def anh_cong(pid: int, co: str, request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    data, a = _goi(S.tep_anh, db, None, pid, co)
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
