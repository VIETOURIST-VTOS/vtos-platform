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


# ══ AT-2a · album ảnh nhà hàng ═══════════════════════════════════════════════════════════════════
@router.get("/{nid:int}/album")
def album(nid: int, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.album(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)


@router.post("/{nid:int}/album")
async def tai_album(nid: int, tep: UploadFile = File(...), nhom: str = Form(""), can_cu: str = Form(""),
                    can_cu_ghi_chu: str = Form(""), credit: str = Form(""), chu_thich: str = Form(""),
                    u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    """Một tệp mỗi lần — giao diện gửi lần lượt để báo tiến độ và thử lại đúng tệp lỗi."""
    data = await _doc(tep)
    try:
        x, moi = N.tai_anh_album(db, u, nid, tep.filename or "anh", tep.content_type or "", data,
                                 {"nhom": nhom, "can_cu": can_cu, "can_cu_ghi_chu": can_cu_ghi_chu, "credit": credit,
                                  "chu_thich": chu_thich})
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "moi": moi, "message": "Đã tải ảnh (Nháp)" if moi else "Ảnh này đã có trong album — không tạo bản trùng"}


class AnhIn(BaseModel):
    nhom: str | None = None
    chu_thich: str | None = None
    mo_ta_thay_the: str | None = None
    credit: str | None = None
    can_cu: str | None = None
    can_cu_ghi_chu: str | None = None


@router.post("/album/{pid:int}")
def sua_anh(pid: int, data: AnhIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        x = N.sua_anh(db, u, pid, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "trang_thai": x.trang_thai,
            "message": "Đã lưu" + (" — ảnh về «Chờ duyệt», thôi hiện cho tới khi TP Điều hành duyệt lại" if x.trang_thai == "cho_duyet" and not x.duyet_boi else "")}


@router.post("/album/{pid:int}/thay")
async def thay_anh(pid: int, tep: UploadFile = File(...), u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    data = await _doc(tep)
    try:
        x = N.thay_anh(db, u, pid, tep.filename or "anh", tep.content_type or "", data)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "message": "Đã thay ảnh — ảnh về «Nháp», gửi duyệt lại; tệp cũ vẫn trong kho"}


class IdsIn(BaseModel):
    ids: list[int] = []


@router.post("/{nid:int}/album/gui-duyet")
def gui_duyet(nid: int, data: IdsIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        n = N.gui_duyet(db, u, nid, data.ids)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"so": n, "message": f"Đã gửi duyệt {n} ảnh"}


@router.post("/{nid:int}/album/thu-tu")
def thu_tu(nid: int, data: IdsIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        N.xep_anh(db, u, nid, data.ids)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": "Đã lưu thứ tự"}


class DuyetAnhIn(BaseModel):
    ids: list[int]
    duyet: bool
    ly_do: str = ""


@router.post("/album/duyet")
def duyet_anh(data: DuyetAnhIn, u: User = Depends(require_roles(*N.VAI_DUYET_ANH)), db: Session = Depends(get_db)):
    try:
        r = N.duyet_anh(db, u, data.ids, data.duyet, data.ly_do)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {**r, "message": f"Đã {'duyệt' if data.duyet else 'trả lại'} {r['da_doi']} ảnh" + (f" · bỏ qua {len(r['bo_qua'])}" if r["bo_qua"] else "")}


@router.get("/album/cho-duyet")
def cho_duyet(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.anh_cho_duyet(db, u)
    except N.LoiNhaHang as ex:
        _loi(ex)


class AnIn(BaseModel):
    an: bool


@router.post("/album/{pid:int}/an")
def an_anh(pid: int, data: AnIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        x = N.an_anh(db, u, pid, data.an)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": "Đã ẩn ảnh" if x.trang_thai == "an" else "Đã bỏ ẩn — ảnh về «Nháp», gửi duyệt lại"}


@router.post("/album/{pid:int}/bia")
def dat_bia(pid: int, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        N.dat_bia(db, u, pid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": "Đã đặt làm ảnh bìa"}


@router.get("/album/{pid:int}/{co}")
def tep_album(pid: int, co: str, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        data, a = N.tep_album(db, u, pid, co)
    except N.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


# ══ AT-2b · món ăn và thực đơn ═══════════════════════════════════════════════════════════════════
@router.get("/{nid:int}/mon")
def ds_mon(nid: int, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.ds_mon(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)


class MonIn(BaseModel):
    ten: str
    ten_khac: str = ""
    nhom: str = "mon_chinh"
    mo_ta: str = ""
    di_ung: list[str] = []
    cay: bool = False
    chay: bool = False
    anh_id: int | None = None


@router.post("/{nid:int}/mon")
def them_mon(nid: int, data: MonIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        x = N.luu_mon(db, u, nid, data.model_dump())
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "message": f"Đã thêm món {x.ten} (Nháp)"}


@router.post("/{nid:int}/mon/{mid:int}")
def sua_mon(nid: int, mid: int, data: MonIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        x = N.luu_mon(db, u, nid, data.model_dump(), mid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"id": x.id, "trang_thai": x.trang_thai, "message": "Đã lưu món" + (" — về «Chờ duyệt»" if x.trang_thai == "cho_duyet" else "")}


class BatMonIn(BaseModel):
    bat: bool


@router.post("/mon/{mid:int}/noi-bat")
def mon_noi_bat(mid: int, data: BatMonIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        x = N.mon_noi_bat(db, u, mid, data.bat)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{x.ten}: " + ("gắn ★ nổi bật" if x.noi_bat else "bỏ ★")}


@router.post("/mon/{mid:int}/an")
def an_mon(mid: int, data: AnIn, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        x = N.an_mon(db, u, mid, data.an)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{x.ten}: " + ("đã ẩn" if x.trang_thai == "an" else "bỏ ẩn — về «Nháp»")}


@router.post("/{nid:int}/mon/gui-duyet")
def gui_duyet_mon(nid: int, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        n = N.gui_duyet_mon(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"so": n, "message": f"Đã gửi duyệt {n} món"}


@router.post("/mon/duyet")
def duyet_mon(data: DuyetAnhIn, u: User = Depends(require_roles(*N.VAI_DUYET_ANH)), db: Session = Depends(get_db)):
    try:
        r = N.duyet_mon(db, u, data.ids, data.duyet, data.ly_do)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {**r, "message": f"Đã {'duyệt' if data.duyet else 'trả lại'} {r['da_doi']} món" + (f" · bỏ qua {len(r['bo_qua'])}" if r["bo_qua"] else "")}


@router.get("/{nid:int}/thuc-don-nh")
def ds_thuc_don(nid: int, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.ds_thuc_don(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)


@router.post("/{nid:int}/thuc-don-nh")
async def tai_thuc_don(nid: int, tep: list[UploadFile] = File(...), loai: str = Form(""), hieu_luc_tu: str = Form(""),
                       can_cu: str = Form(""), u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    if len(tep) > N.TD_TOI_DA_TRANG:
        raise HTTPException(400, f"Tối đa {N.TD_TOI_DA_TRANG} tệp mỗi bản")
    ds = [(f.filename or "trang", await _doc(f)) for f in tep]
    try:
        b = N.tai_thuc_don(db, u, nid, loai, ds, hieu_luc_tu or None, can_cu)
    except N.LoiNhaHang as ex:
        _loi(ex)
    except ValueError:
        raise HTTPException(400, "Ngày hiệu lực không hợp lệ")
    return {"id": b.id, "message": f"Đã tải {N._ten_ban(b.so)} ({b.so_trang} trang) — chờ TP Điều hành duyệt"}


class DuyetTdIn(BaseModel):
    duyet: bool
    ly_do: str = ""


@router.post("/thuc-don-nh/{bid:int}/duyet")
def duyet_thuc_don(bid: int, data: DuyetTdIn, u: User = Depends(require_roles(*N.VAI_DUYET_ANH)), db: Session = Depends(get_db)):
    try:
        b = N.duyet_thuc_don(db, u, bid, data.duyet, data.ly_do)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{N._ten_ban(b.so)}: " + ("đã duyệt" if b.trang_thai == "duyet" else "đã trả lại")}


@router.get("/thuc-don/trang/{tid:int}/{co}")
def tep_trang(tid: int, co: str, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        data, a = N.tep_trang(db, u, tid, co)
    except N.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/noi-dung-cho-duyet")
def noi_dung_cho_duyet(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.cho_duyet_noi_dung(db, u)
    except N.LoiNhaHang as ex:
        _loi(ex)


# ══ AT-2c · biên tập và mức hoàn thiện ═══════════════════════════════════════════════════════════
@router.get("/hoan-thien")
def bang_hoan_thien(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.bang_hoan_thien(db, u)
    except N.LoiNhaHang as ex:
        _loi(ex)


@router.get("/hoan-thien.xlsx")
def xuat_thieu(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        data = N.xuat_thieu_xlsx(db, u)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="nha_hang_thieu_{date.today():%Y%m%d}.xlsx"'})


@router.get("/viec-cua-toi")
def viec_cua_toi(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.bang_hoan_thien(db, u, chi_cua=u.username)
    except N.LoiNhaHang as ex:
        _loi(ex)


class GiaoIn(BaseModel):
    ids: list[int]
    nguoi: str = ""
    han: date | None = None


@router.post("/bien-tap/giao")
def giao_bien_tap(data: GiaoIn, u: User = Depends(require_roles(*N.VAI_GIAO_BIEN_TAP)), db: Session = Depends(get_db)):
    try:
        n = N.giao_bien_tap(db, u, data.ids, data.nguoi, data.han)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"so": n, "message": (f"Đã giao {n} nhà hàng cho {data.nguoi}" if data.nguoi else f"Đã bỏ giao {n} nhà hàng")}


@router.get("/{nid:int}/hoan-thien")
def hoan_thien_mot(nid: int, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    try:
        return N.hoan_thien_mot(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)


@router.post("/{nid:int}/da-xin")
def da_xin(nid: int, u: User = Depends(require_roles(*N.VAI_ANH_NH)), db: Session = Depends(get_db)):
    try:
        N.ghi_da_xin(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": "Đã ghi: đã xin nhà hàng bổ sung"}


# ══ AT-3 · đánh giá sao — Marketing ẩn vi phạm, TP Điều hành xem lại ═══════════════════════════════════════
def _dg(f, *a, **k):
    from app.services import danh_gia_nh as DG
    try:
        return f(*a, **k)
    except DG.LoiDanhGia as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/danh-gia")
def ds_danh_gia(loc: str = "", u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import danh_gia_nh as DG
    return _dg(DG.ds_noi_bo, db, u, loc)


@router.get("/danh-gia.xlsx")
def xuat_danh_gia(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import danh_gia_nh as DG
    data = _dg(DG.xuat_xlsx, db, u)
    return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="danh_gia_nha_hang_{date.today():%Y%m%d}.xlsx"'})


class AnDgIn(BaseModel):
    ly_do: str = ""
    ghi_chu: str = ""
    phan: str = "bai"


@router.post("/danh-gia/{gid}/an")
def an_danh_gia(gid: int, data: AnDgIn, u: User = Depends(require_roles("nv_mkt", "ptgd_mkt")), db: Session = Depends(get_db)):
    from app.services import danh_gia_nh as DG
    _dg(DG.an, db, u, gid, data.ly_do, data.ghi_chu, data.phan)
    return {"message": "Đã ẩn — chờ TP Điều hành xem lại"}


class XemLaiIn(BaseModel):
    giu: bool = True
    ghi_chu: str = ""


@router.post("/danh-gia/{gid}/xem-lai")
def xem_lai_danh_gia(gid: int, data: XemLaiIn, u: User = Depends(require_roles("tp_dh", "chutich", "tgd")), db: Session = Depends(get_db)):
    from app.services import danh_gia_nh as DG
    _dg(DG.xem_lai, db, u, gid, data.giu, data.ghi_chu)
    return {"message": "Đã xem lại: giữ ẩn" if data.giu else "Đã xem lại: hiện lại bài"}


# ══ PL-1 · phân loại: «Đặc sản địa phương» + bậc sang trọng (Chủ tịch duyệt 30/10/2026) ═══════════════════
@router.get("/phan-loai")
def ds_phan_loai(u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    return PL.ds(db, u)


@router.get("/phan-loai/mau-michelin.xlsx")
def mau_michelin(u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    return Response(content=PL.mau_xlsx(db), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="michelin_hang_gia_{date.today():%Y%m%d}.xlsx"'})


@router.post("/phan-loai/nhap-michelin")
async def nhap_michelin(tep: UploadFile = File(...), thu: bool = Form(True),
                        u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    """Đọc thử (thu=true, không ghi) rồi ghi. Ô trống giữ nguyên."""
    from app.services import phan_loai_nh as PL
    data = await _doc(tep)
    try:
        return PL.nhap_xlsx(db, u, tep.filename or "", data, thu)
    except N.LoiNhaHang as ex:
        _loi(ex)


@router.get("/{nid:int}/phan-loai")
def mot_phan_loai(nid: int, u: User = Depends(require_roles(*N.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    try:
        return PL.chi_tiet(db, u, nid)
    except N.LoiNhaHang as ex:
        _loi(ex)


class MichelinIn(BaseModel):
    hang: str = ""
    gia: int = 0


@router.post("/{nid:int}/phan-loai/michelin")
def ghi_michelin(nid: int, data: MichelinIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    try:
        n = PL.ghi_michelin(db, u, nid, data.hang, data.gia)
    except N.LoiNhaHang as ex:
        _loi(ex)
    return {"message": f"{n.ten}: đã ghi hạng / mức giá Michelin"}


class BacIn(BaseModel):
    bac: str


@router.post("/{nid:int}/phan-loai/bac")
def de_xuat_bac(nid: int, data: BacIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    try:
        return PL.de_xuat_bac(db, u, nid, data.bac)
    except N.LoiNhaHang as ex:
        _loi(ex)


class ChotIn(BaseModel):
    dong_y: bool = True


@router.post("/{nid:int}/phan-loai/bac/chot")
def chot_bac(nid: int, data: ChotIn, u: User = Depends(require_roles(*N.VAI_BAT)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    try:
        return PL.chot_bac(db, u, nid, data.dong_y)
    except N.LoiNhaHang as ex:
        _loi(ex)


class DacSanIn(BaseModel):
    tay: str
    ly_do: str = ""


@router.post("/{nid:int}/phan-loai/dac-san")
def de_xuat_dac_san(nid: int, data: DacSanIn, u: User = Depends(require_roles(*N.VAI_NHAP)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    try:
        return PL.de_xuat_dac_san(db, u, nid, data.tay, data.ly_do)
    except N.LoiNhaHang as ex:
        _loi(ex)


@router.post("/{nid:int}/phan-loai/dac-san/chot")
def chot_dac_san(nid: int, data: ChotIn, u: User = Depends(require_roles(*N.VAI_BAT)), db: Session = Depends(get_db)):
    from app.services import phan_loai_nh as PL
    try:
        return PL.chot_dac_san(db, u, nid, data.dong_y)
    except N.LoiNhaHang as ex:
        _loi(ex)
