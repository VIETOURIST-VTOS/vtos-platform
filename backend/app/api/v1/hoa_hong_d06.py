"""DH-1 · Hoa hồng đối tác bán hàng (D06) — màn Kế toán. Luật và phép tính: services/hoa_hong_d06.py."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import hoa_hong_d06 as H

router = APIRouter(prefix="/api/v1/hoa-hong-d06", tags=["hoa-hong-d06"])


def _ky(ky: str | None) -> str:
    if ky:
        try:
            H.dau_thang(ky)
            return ky
        except Exception:
            raise HTTPException(422, "Kỳ phải dạng YYYY-MM")
    d = H._hom_nay()
    return f"{d:%Y-%m}"


@router.get("")
def xem(ky: str | None = None, u: User = Depends(require_roles(*H.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import doi_soat_doi_tac as DS
    k = _ky(ky)
    ra = H.tong_hop(db, k)
    if ra["v3"]:     # KS-16h: cột Đối soát
        for r in ra["dong"]:
            r["doi_soat"] = DS.tom_tat(db, r["doi_tac_id"], k)
    return ra


class DoiSoatIn(BaseModel):
    doi_tac_id: int
    ky: str


@router.post("/doi-soat")
def gui_doi_soat(data: DoiSoatIn, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    from app.services import doi_soat_doi_tac as DS
    try:
        b = DS.lap_va_gui(db, u, data.doi_tac_id, _ky(data.ky))
    except DS.LoiDoiSoat as ex:
        raise HTTPException(ex.status if ex.status != 400 else 422, str(ex))
    return {"message": f"Đã gửi bảng đối soát kỳ {b.ky} — đối tác phản hồi đến {b.han_phan_hoi:%d/%m/%Y}, hạn trả {b.han_tra:%d/%m/%Y}"}


@router.get("/doi-soat/{doi_tac_id}")
def xem_doi_soat(doi_tac_id: int, u: User = Depends(require_roles(*H.VAI_XEM)), db: Session = Depends(get_db)):
    from app.services import doi_soat_doi_tac as DS
    from app.models.doi_tac_ban_hang import DoiTacBanHang
    dt = db.get(DoiTacBanHang, doi_tac_id)
    if dt is None:
        raise HTTPException(404, "Không có đối tác này")
    return {"ten": dt.ten, "bang": DS.cua_doi_tac(db, dt)}


VAI_VU_VIEC = H.VAI_XEM


@router.get("/vu-viec")
def ds_vu_viec(u: User = Depends(require_roles(*VAI_VU_VIEC)), db: Session = Depends(get_db)):
    from app.services import nguon_don as ND
    return {"vu_viec": ND.ds_vu_viec(db)}


class XuLyIn(BaseModel):
    chap_nhan: bool
    ket_qua: str


@router.post("/vu-viec/{vid}")
def xu_ly_vu_viec(vid: int, data: XuLyIn, u: User = Depends(require_roles(*VAI_VU_VIEC)), db: Session = Depends(get_db)):
    from app.services import nguon_don as ND
    try:
        v = ND.xu_ly_vu_viec(db, u, vid, data.chap_nhan, data.ket_qua)
    except ND.LoiNguon as ex:
        raise HTTPException(ex.status if ex.status != 400 else 422, str(ex))
    return {"message": f"{v.ma}: {'chấp nhận' if v.trang_thai == 'chap_nhan' else 'bác'}"}


class KyIn(BaseModel):
    ky: str


@router.post("/tinh-lai")
def tinh_lai(data: KyIn, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    try:
        return H.tinh_lai(db, u, _ky(data.ky))
    except H.LoiD06 as ex:
        raise HTTPException(422, str(ex))


@router.post("/ky/{ky_id}/chot")
def chot(ky_id: int, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    try:
        k = H.chot(db, u, ky_id)
    except H.LoiD06 as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã chốt kỳ {k.ky}"}


@router.post("/ky/{ky_id}/de-nghi-chi")
def de_nghi_chi(ky_id: int, u: User = Depends(require_roles(*H.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    try:
        r = H.de_nghi_chi(db, u, ky_id)
    except (H.LoiD06, ValueError) as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã lập đề nghị chi {r.code} — {int(r.amount):,} đ, đi luồng duyệt chi".replace(",", "."), "code": r.code}


class HinhThucIn(BaseModel):
    doi_tac_id: int
    hinh_thuc: str


@router.post("/hinh-thuc")
def hinh_thuc(data: HinhThucIn, u: User = Depends(require_roles(*H.VAI_HINH_THUC)), db: Session = Depends(get_db)):
    try:
        r = H.dat_hinh_thuc(db, u, data.doi_tac_id, data.hinh_thuc)
    except H.LoiD06 as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Đã đặt «{H.HINH_THUC[r.hinh_thuc]}» có hiệu lực từ {r.hieu_luc_tu:%d/%m/%Y}"}


VAI_PHU_LUC = tuple(dict.fromkeys(H.VAI_KE_TOAN + ("gd_kd", "chutich", "tgd")))


class PhuLucIn(BaseModel):
    d06_phu_luc: bool
    vat_pct: float = 8


@router.post("/tour/{tid}/phu-luc")
def dat_phu_luc(tid: int, data: PhuLucIn, u: User = Depends(require_roles(*VAI_PHU_LUC)), db: Session = Depends(get_db)):
    """KS-16h: tour có phụ lục hoa hồng D06 + % VAT trong giá bán (D06 theo v3 loại VAT)."""
    from app.models.core import Tour
    from app.services import rules as R
    t = db.get(Tour, tid)
    if t is None:
        raise HTTPException(404, "Không có tour này")
    if not 0 <= data.vat_pct <= 20:
        raise HTTPException(422, "% VAT từ 0 đến 20")
    truoc = {"d06_phu_luc": t.d06_phu_luc, "vat_pct": t.vat_pct}
    t.d06_phu_luc, t.vat_pct = bool(data.d06_phu_luc), float(data.vat_pct)
    R.audit(db, u.username, u.role, "d06_phu_luc_tour", f"tour:{t.code}", before=truoc,
            after={"d06_phu_luc": t.d06_phu_luc, "vat_pct": t.vat_pct})
    db.commit()
    return {"message": f"{t.code}: {'có' if t.d06_phu_luc else 'không có'} phụ lục hoa hồng D06 · VAT {t.vat_pct:g}%"}
