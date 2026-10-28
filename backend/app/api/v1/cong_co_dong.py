"""CD-1 · Cổng Cổ đông đợt 1 — ba nhóm cửa:

  /api/v1/cong/co-dong/*        — phía NGOÀI, đòi phiên cổng của cổ đông ĐÃ XÁC MINH.
  /api/v1/cong/ir-cong-khai/*   — thư viện tài liệu «Công khai», KHÔNG cần đăng nhập (màn A18), có phanh
                                  theo địa chỉ mạng. Chỉ đọc; không trả gì về cổ đông hay tài khoản.
  /api/v1/ir-cong-co-dong/*     — phía VTOS: IR – Pháp chế đưa tài liệu, tạo sự kiện, trả lời IR;
                                  Chủ tịch, TGĐ gỡ tài liệu; BKS, robot kiểm soát xem.
"""
import time
from collections import defaultdict
from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.db.session import get_db
from app.models.attachments import Attachment
from app.models.cong_co_dong import TaiLieuCongCoDong, YeuCauIr
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.services import attachments as AT
from app.services import cong_co_dong as S

router = APIRouter(prefix="/api/v1/cong/co-dong", tags=["cong-co-dong"])
router_cong_khai = APIRouter(prefix="/api/v1/cong/ir-cong-khai", tags=["cong-co-dong"])
router_vtos = APIRouter(prefix="/api/v1/ir-cong-co-dong", tags=["cong-co-dong"])

CUA_SO_GIAY, TOI_DA_TRONG_CUA_SO = 600, 60
_LUOT: dict[str, list[float]] = defaultdict(list)


def _phanh(req: Request) -> None:
    ip = (req.client.host if req.client else "") or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_TRONG_CUA_SO:
        _LUOT[ip] = v
        raise HTTPException(429, "Quá nhiều lượt xem từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(bay_gio)
    _LUOT[ip] = v


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiCoDong as ex:
        raise HTTPException(ex.status, str(ex))


def _tep(data: bytes, a, tai: bool = False) -> Response:
    ten = quote(a.ten_tep or "tai-lieu.pdf")
    return Response(content=data, media_type=a.kieu_noi_dung or "application/pdf",
                    headers={"Content-Disposition": f"{'attachment' if tai else 'inline'}; filename*=UTF-8''{ten}",
                             "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


def _co_dong(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai)) -> TaiKhoanNgoai:
    return _goi(S.cua_co_dong, tk)


# ---------------------------------------------------------------- phía cổ đông
@router.get("/tong-quan")
def tong_quan(tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    return _goi(S.tong_quan, db, tk)


@router.get("/tai-lieu")
def tai_lieu(nhom: str = "", nam: int | None = None, tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    return {"tai_lieu": S.ds_tai_lieu(db, True, nhom, nam), "nam": S.nam_co_tai_lieu(db, True), "nhom": S.NHOM_TAI_LIEU}


@router.get("/tai-lieu/{tid}")
def mot_tai_lieu(tid: int, tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    return _goi(S.mot_tai_lieu, db, tid, True)


@router.get("/tai-lieu/{tid}/tep")
def tep(tid: int, tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    data, a = _goi(S.tep_tai_lieu, db, tid, True)
    return _tep(data, a)


@router.get("/su-kien")
def su_kien(tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    return {"su_kien": S.ds_su_kien_cong(db, tk)}


class QuanTamIn(BaseModel):
    bat: bool = True


@router.post("/su-kien/{sid}/quan-tam")
def quan_tam(sid: int, data: QuanTamIn, tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    sk = _goi(S.quan_tam, db, tk, sid, data.bat)
    db.commit()
    return {"message": "Đã ghi nhận quan tâm — IR sẽ liên hệ xác nhận" if data.bat else "Đã bỏ quan tâm", "su_kien": sk}


@router.get("/ir")
def ir(tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    return {"yeu_cau": _goi(S.ir_cua_toi, db, tk), "chu_de": S.CHU_DE_IR}


class IrIn(BaseModel):
    chu_de: str
    noi_dung: str


@router.post("/ir")
def gui_ir(data: IrIn, tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    y = _goi(S.gui_ir, db, tk, data.chu_de, data.noi_dung)
    db.commit()
    return {"message": f"Đã gửi {y.ma} — IR – Pháp chế tiếp nhận", "ma": y.ma, "yeu_cau": S.ir_cua_toi(db, tk)}


# ---------------------------------------------------------------- công khai, không đăng nhập (A18)
@router_cong_khai.get("/tai-lieu")
def cong_khai_ds(request: Request, nhom: str = "", nam: int | None = None, db: Session = Depends(get_db)):
    _phanh(request)
    return {"tai_lieu": S.ds_tai_lieu(db, False, nhom, nam), "nam": S.nam_co_tai_lieu(db, False), "nhom": S.NHOM_TAI_LIEU}


@router_cong_khai.get("/tai-lieu/{tid}")
def cong_khai_mot(tid: int, request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    return _goi(S.mot_tai_lieu, db, tid, False)


@router_cong_khai.get("/tai-lieu/{tid}/tep")
def cong_khai_tep(tid: int, request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    data, a = _goi(S.tep_tai_lieu, db, tid, False)
    return _tep(data, a)


# ---------------------------------------------------------------- phía VTOS
@router_vtos.get("/tai-lieu")
def vt_tai_lieu(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {**S.quan_tri_tai_lieu(db), "duoc_dua": u.role in S.VAI_GHI, "duoc_go": u.role in S.VAI_GO}


@router_vtos.post("/tai-lieu")
async def vt_dua_len(ban_ghi_id: int = Form(...), tieu_de: str = Form(...), nhom: str = Form(...),
                     pham_vi: str = Form(...), thay_cho_id: int | None = Form(None), ly_do_thay: str = Form(""),
                     tep: UploadFile = File(...), u: User = Depends(require_roles(*S.VAI_GHI)),
                     db: Session = Depends(get_db)):
    data = await tep.read()
    t = _goi(S.dua_len, db, u, ban_ghi_id, tieu_de, nhom, pham_vi, tep.filename or "", tep.content_type or "",
             data, thay_cho_id, ly_do_thay)
    db.commit()
    return {"message": f"Đã đưa «{t.tieu_de}» lên cổng cổ đông", **S.quan_tri_tai_lieu(db),
            "duoc_dua": True, "duoc_go": u.role in S.VAI_GO}


class LyDoIn(BaseModel):
    ly_do: str = ""


@router_vtos.post("/tai-lieu/{tid}/go")
def vt_go(tid: int, data: LyDoIn, u: User = Depends(require_roles(*S.VAI_GO)), db: Session = Depends(get_db)):
    t = _goi(S.go, db, u, tid, data.ly_do)
    db.commit()
    return {"message": f"Đã gỡ «{t.tieu_de}» khỏi cổng", **S.quan_tri_tai_lieu(db),
            "duoc_dua": u.role in S.VAI_GHI, "duoc_go": True}


@router_vtos.get("/tai-lieu/{tid}/tep")
def vt_tep(tid: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    t = db.get(TaiLieuCongCoDong, tid)
    a = db.get(Attachment, t.attachment_id) if t else None
    if a is None:
        raise HTTPException(404, "Không có tệp này")
    try:
        return _tep(AT.doc(db, a), a)
    except Exception as ex:
        raise HTTPException(503, str(ex))


@router_vtos.get("/su-kien")
def vt_su_kien(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {**S.quan_tri_su_kien(db), "duoc_ghi": u.role in S.VAI_GHI,
            "tai_lieu_hien": [{"id": d["id"], "tieu_de": d["tieu_de"]} for d in S.ds_tai_lieu(db, True)]}


class SuKienIn(BaseModel):
    ten: str
    loai: str
    bat_dau: datetime
    dia_diem: str = ""
    ngay_chot_ds: date | None = None
    mo_ta: str = ""
    tai_lieu_ids: list[int] = []
    nhan_quan_tam: bool = True


@router_vtos.post("/su-kien")
def vt_tao_su_kien(data: SuKienIn, u: User = Depends(require_roles(*S.VAI_GHI)), db: Session = Depends(get_db)):
    s = _goi(S.tao_su_kien, db, u, data.model_dump())
    db.commit()
    return {"message": f"Đã tạo bản nháp «{s.ten}» — bấm Thông báo để hiện trên cổng", **vt_su_kien(u, db)}


@router_vtos.put("/su-kien/{sid}")
def vt_sua_su_kien(sid: int, data: SuKienIn, u: User = Depends(require_roles(*S.VAI_GHI)), db: Session = Depends(get_db)):
    s = _goi(S.sua_su_kien, db, u, sid, data.model_dump())
    db.commit()
    return {"message": f"Đã lưu «{s.ten}»", **vt_su_kien(u, db)}


class TrangThaiIn(BaseModel):
    trang_thai: str
    ly_do: str = ""


@router_vtos.post("/su-kien/{sid}/trang-thai")
def vt_trang_thai(sid: int, data: TrangThaiIn, u: User = Depends(require_roles(*S.VAI_GHI)), db: Session = Depends(get_db)):
    s = _goi(S.doi_trang_thai_su_kien, db, u, sid, data.trang_thai, data.ly_do)
    db.commit()
    return {"message": f"«{s.ten}»: {S.TRANG_THAI_SU_KIEN[s.trang_thai]}", **vt_su_kien(u, db)}


@router_vtos.get("/su-kien/{sid}/quan-tam")
def vt_quan_tam(sid: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {"quan_tam": _goi(S.ds_quan_tam, db, sid)}


@router_vtos.get("/ir")
def vt_ir(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {**S.quan_tri_ir(db), "duoc_ghi": u.role in S.VAI_GHI}


class TraLoiIn(BaseModel):
    tra_loi: str
    xac_nhan_da_cong_bo: bool = False


@router_vtos.post("/ir/{yid}/tra-loi")
def vt_tra_loi(yid: int, data: TraLoiIn, u: User = Depends(require_roles(*S.VAI_GHI)), db: Session = Depends(get_db)):
    y = _goi(S.tra_loi_ir, db, u, yid, data.tra_loi, data.xac_nhan_da_cong_bo)
    db.commit()
    return {"message": f"Đã trả lời {y.ma}", **vt_ir(u, db)}


@router_vtos.post("/ir/{yid}/dong")
def vt_dong(yid: int, data: LyDoIn, u: User = Depends(require_roles(*S.VAI_GHI)), db: Session = Depends(get_db)):
    y = _goi(S.dong_ir, db, u, yid, data.ly_do)
    db.commit()
    return {"message": f"Đã đóng {y.ma}", **vt_ir(u, db)}


# ================================================================ CD-2 · sổ cổ đông và hồ sơ sở hữu
from app.services import so_co_dong as SC  # noqa: E402


def _goi_so(f, *a, **k):
    try:
        return f(*a, **k)
    except SC.LoiSo as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/so-huu")
def so_huu(tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    return SC.so_huu_cua(db, tk)


@router.post("/xac-minh")
async def xac_minh(noi_dung: str = Form(...), tep: UploadFile | None = File(None),
                   tk: TaiKhoanNgoai = Depends(_co_dong), db: Session = Depends(get_db)):
    data = await tep.read() if tep is not None else None
    y = _goi_so(SC.gui_xac_minh, db, tk, noi_dung, (tep.filename if tep else "") or "", (tep.content_type if tep else "") or "", data)
    db.commit()
    return {"message": f"Đã gửi {y.ma} — IR – Pháp chế tiếp nhận. Theo dõi ở mục Liên hệ IR.", "ma": y.ma}


@router_vtos.get("/so-co-dong")
def vt_so(u: User = Depends(require_roles(*SC.VAI_XEM)), db: Session = Depends(get_db)):
    return SC.quan_tri(db, u)


@router_vtos.post("/so-co-dong/doc-thu")
async def vt_so_doc_thu(tep: UploadFile = File(...), u: User = Depends(require_roles(*SC.VAI_NAP))):
    return _goi_so(SC.doc_thu, u, tep.filename or "", await tep.read())


@router_vtos.post("/so-co-dong")
async def vt_so_gui(ngay_can_cu: date = Form(...), tep: UploadFile = File(...),
                    u: User = Depends(require_roles(*SC.VAI_NAP)), db: Session = Depends(get_db)):
    lo = _goi_so(SC.gui_duyet, db, u, ngay_can_cu, tep.filename or "", await tep.read())
    db.commit()
    return {"message": f"Đã gửi lô {lo.ma} ({lo.so_dong} dòng) — chờ Chủ tịch duyệt", **SC.quan_tri(db, u)}


class XuLyLoIn(BaseModel):
    hanh_dong: str
    ly_do: str = ""


@router_vtos.post("/so-co-dong/{lo_id}")
def vt_so_xu_ly(lo_id: int, data: XuLyLoIn, u: User = Depends(require_roles(*SC.VAI_DUYET)), db: Session = Depends(get_db)):
    if data.hanh_dong == "duyet":
        lo = _goi_so(SC.duyet, db, u, lo_id)
    elif data.hanh_dong == "tu_choi":
        lo = _goi_so(SC.tu_choi, db, u, lo_id, data.ly_do)
    else:
        raise HTTPException(422, "Hành động không hợp lệ")
    db.commit()
    return {"message": f"Lô {lo.ma}: {SC.TRANG_THAI_LO_SCD[lo.trang_thai]}", **SC.quan_tri(db, u)}


@router_vtos.get("/so-co-dong/{lo_id}/dong")
def vt_so_dong(lo_id: int, q: str = "", u: User = Depends(require_roles(*SC.VAI_XEM)), db: Session = Depends(get_db)):
    return {"dong": SC.dong_cua_lo(db, lo_id, q)}


@router_vtos.get("/noi")
def vt_noi(u: User = Depends(require_roles(*SC.VAI_XEM)), db: Session = Depends(get_db)):
    return {**SC.ds_noi(db), "duoc_noi": u.role in SC.VAI_NAP}


class NoiIn(BaseModel):
    giay_to: str = ""
    ly_do: str = ""


@router_vtos.post("/noi/{tk_id}")
def vt_noi_tk(tk_id: int, data: NoiIn, u: User = Depends(require_roles(*SC.VAI_NAP)), db: Session = Depends(get_db)):
    _goi_so(SC.noi, db, u, tk_id, data.giay_to)
    db.commit()
    return {"message": "Đã nối tài khoản với danh sách sở hữu", **SC.ds_noi(db), "duoc_noi": True}


@router_vtos.post("/noi/{tk_id}/go")
def vt_go_noi(tk_id: int, data: NoiIn, u: User = Depends(require_roles(*SC.VAI_NAP)), db: Session = Depends(get_db)):
    _goi_so(SC.go_noi, db, u, tk_id, data.ly_do)
    db.commit()
    return {"message": "Đã gỡ nối", **SC.ds_noi(db), "duoc_noi": True}


@router_vtos.get("/ir/{yid}/tep")
def vt_ir_tep(yid: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    y = db.get(YeuCauIr, yid)
    a = db.get(Attachment, y.attachment_id) if y and y.attachment_id else None
    if a is None:
        raise HTTPException(404, "Yêu cầu này không có tệp")
    try:
        return _tep(AT.doc(db, a), a)
    except Exception as ex:
        raise HTTPException(503, str(ex))
