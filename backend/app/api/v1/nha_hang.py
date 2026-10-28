"""KH-2 · Màn VTOS «Nhà hàng (cổng khách)» — Điều hành nhập, TP Điều hành bật hiện cổng (DT-2b, 28/10/2026)."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.core import User
from app.api.deps import require_roles
from app.services import nha_hang as N

router = APIRouter(prefix="/api/v1/nha-hang", tags=["nha-hang"])


def _loi(ex: N.LoiNhaHang):
    raise HTTPException(400, str(ex))


@router.get("")
def danh_sach(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    return N.danh_sach_vtos(db)


class NhaHangIn(BaseModel):
    ten: str
    tinh_thanh: str = ""
    khu_vuc: str = ""
    am_thuc: str = "Việt Nam"
    gio_phuc_vu: str = ""
    tien_ich: str = ""
    mo_ta: str = ""
    ghi_chu_noi_bo: str = ""


@router.post("")
def tao(data: NhaHangIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        nh = N.luu_nha_hang(db, u, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": nh.id, "message": f"Đã thêm {nh.ma} · {nh.ten}"}


@router.post("/{nid:int}")
def sua(nid: int, data: NhaHangIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        nh = N.luu_nha_hang(db, u, data.model_dump(), nid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": nh.id, "message": "Đã lưu" + ("" if nh.hien_cong or not nh.tat_ly_do else " — nhà hàng đang chờ TP Điều hành bật lại")}


class ThucDonIn(BaseModel):
    ten: str
    loai: str = "set"
    gia_nguoi_lon: float | None = None
    gia_tre_em: float | None = None
    so_khach_toi_thieu: int = 1
    mo_ta: str = ""
    dieu_kien: str = ""
    dieu_kien_huy: str = ""
    tu_ngay: date | None = None
    den_ngay: date | None = None
    dang_ban: bool = True


@router.post("/{nid}/thuc-don")
def them_thuc_don(nid: int, data: ThucDonIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        td = N.luu_thuc_don(db, u, nid, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": td.id, "message": f"Đã thêm gói {td.ten}"}


@router.post("/{nid}/thuc-don/{tid}")
def sua_thuc_don(nid: int, tid: int, data: ThucDonIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        td = N.luu_thuc_don(db, u, nid, data.model_dump(), tid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": td.id, "message": f"Đã lưu gói {td.ten}"}


class BatIn(BaseModel):
    bat: bool


@router.post("/{nid}/hien-cong")
def hien_cong(nid: int, data: BatIn, u: User = Depends(require_roles(*N.VAI_BAT)), db: Session = Depends(get_db)):
    try:
        nh = N.bat_hien(db, u, nid, data.bat)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{nh.ten}: " + ("đang hiện trên cổng khách" if nh.hien_cong else "đã tắt khỏi cổng khách")}


class NgungIn(BaseModel):
    ngung: bool


@router.post("/{nid}/ngung")
def ngung(nid: int, data: NgungIn, u: User = Depends(require_roles(*(N.VAI_BAT + ("tp_dh",)))), db: Session = Depends(get_db)):
    try:
        nh = N.ngung(db, u, nid, data.ngung)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{nh.ten}: " + ("đã ngừng hợp tác" if nh.ngung else "hợp tác lại")}


# ══ AT-1 · nhập danh sách, xác minh, hợp đồng, nội dung ══════════════════════════════════════════
from fastapi import File, Form, UploadFile  # noqa: E402
from fastapi.responses import Response  # noqa: E402

TOI_DA_TEP = 10 * 1024 * 1024


async def _doc(f: UploadFile) -> bytes:
    data = await f.read()
    if len(data) > TOI_DA_TEP:
        raise HTTPException(400, "Tệp quá 10 MB")
    return data


@router.post("/nhap-tep")
async def nhap_tep(tep: UploadFile = File(...), nguon: str = Form(""), thu: bool = Form(True),
                   u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    """Đọc thử (thu=true, không ghi gì) rồi nhập. Bản ghi mới chưa hiện, chưa có hợp đồng."""
    data = await _doc(tep)
    try:
        return N.nhap_tep(db, u, tep.filename or "", data, nguon, thu)
    except N.LoiNhaHang as ex:
        _loi(ex)


class HangLoatIn(BaseModel):
    ids: list[int]
    bat: bool


@router.post("/hien-hang-loat")
def hien_hang_loat(data: HangLoatIn, u: User = Depends(require_roles(*N.VAI_BAT)), db: Session = Depends(get_db)):
    try:
        r = N.hien_hang_loat(db, u, data.ids, data.bat)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {**r, "message": f"Đã {'bật' if data.bat else 'tắt'} {r['da_doi']} nhà hàng" + (f" · bỏ qua {len(r['bo_qua'])}" if r["bo_qua"] else "")}


class XacMinhIn(BaseModel):
    ok: bool


@router.post("/{nid}/xac-minh")
def xac_minh(nid: int, data: XacMinhIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    try:
        nh = N.xac_minh_lien_he(db, u, nid, data.ok)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{nh.ten}: " + ("đã xác minh liên hệ" if nh.lien_he_xac_minh else "bỏ đánh dấu xác minh")}


@router.post("/{nid}/hop-dong")
async def ghi_hop_dong(nid: int, tep: UploadFile = File(...), da_ky: bool = Form(False), so_hd: str = Form(""),
                       ngay_ky: str = Form(""), tu_ngay: str = Form(""), den_ngay: str = Form(""),
                       hoa_hong_pct: str = Form(""), hoa_hong_co_dinh: str = Form(""), co_so: str = Form(""),
                       ly_do: str = Form(""), u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    data = await _doc(tep)
    try:
        h = N.ghi_hop_dong(db, u, nid, {"da_ky": da_ky, "so_hd": so_hd, "ngay_ky": ngay_ky, "tu_ngay": tu_ngay,
                                        "den_ngay": den_ngay or None, "hoa_hong_pct": hoa_hong_pct,
                                        "hoa_hong_co_dinh": hoa_hong_co_dinh or None, "co_so": co_so, "ly_do": ly_do},
                           tep.filename or "hop_dong", tep.content_type or "", data)
    except N.LoiNhaHang as ex:
        _loi(ex)
    except ValueError:
        raise HTTPException(400, "Hoa hồng cố định phải là số")
    return {"id": h.id, "message": f"Đã ghi nhận hợp đồng {h.so_hd} (bản {h.phien_ban})"}


@router.get("/hop-dong/{hid}/tep")
def tep_hop_dong(hid: int, u: User = Depends(require_roles(*N.VAI_HOP_DONG_XEM)), db: Session = Depends(get_db)):
    try:
        data, a = N.tep_hop_dong(db, u, hid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return Response(content=data, media_type=a.kieu_noi_dung or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="hop_dong_{hid}"'})


class GioiThieuIn(BaseModel):
    mo_ta: str = ""
    mon_noi_bat: str = ""


@router.post("/{nid}/gioi-thieu")
def gioi_thieu(nid: int, data: GioiThieuIn, u: User = Depends(require_roles(*N.VAI_NOI_DUNG)), db: Session = Depends(get_db)):
    try:
        nh = N.luu_gioi_thieu(db, u, nid, data.mo_ta, data.mon_noi_bat)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"Đã lưu giới thiệu {nh.ten}"}


class NoiDungIn(BaseModel):
    loai: str
    ten: str
    ten_khac: str = ""
    nhom: str = ""
    tinh_thanh: str = ""
    tom_tat: str = ""
    noi_dung: str = ""
    vung: str = ""
    nen_an: str = ""
    thanh_phan: str = ""
    cach_goi: str = ""
    nha_hang_ids: list[int] = []
    thu_tu: int = 0
    hien: bool = False


@router.post("/noi-dung")
def tao_noi_dung(data: NoiDungIn, u: User = Depends(require_roles(*N.VAI_NOI_DUNG)), db: Session = Depends(get_db)):
    try:
        x = N.luu_noi_dung(db, u, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "message": f"Đã thêm {x.ten}"}


@router.post("/noi-dung/{xid}")
def sua_noi_dung(xid: int, data: NoiDungIn, u: User = Depends(require_roles(*N.VAI_NOI_DUNG)), db: Session = Depends(get_db)):
    try:
        x = N.luu_noi_dung(db, u, data.model_dump(), xid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "message": f"Đã lưu {x.ten}"}


# ── AT-1c · ảnh ─────────────────────────────────────────────────────────────────────────────────
@router.post("/anh/{doi}/{oid}")
async def tai_anh(doi: str, oid: int, tep: UploadFile = File(...), nguon: str = Form(""),
                  u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    data = await _doc(tep)
    try:
        aid = N.gan_anh(db, u, doi, oid, tep.filename or "anh", tep.content_type or "", data, nguon)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"anh_id": aid, "message": "Đã lưu ảnh"}


@router.get("/anh/{aid}")
def xem_anh(aid: int, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        data, a = N.anh_noi_bo(db, u, aid)
    except N.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg")
