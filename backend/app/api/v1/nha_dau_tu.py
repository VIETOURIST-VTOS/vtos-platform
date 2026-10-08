"""API Đợt D3 – quan hệ nhà đầu tư: danh bạ, sổ tiếp xúc, sổ cấp quyền xem hồ sơ.

CÙNG TIỀN TỐ `/api/v1/ir-phap-che` với D1 và D2 – đợt này cũng KHÔNG tự khai thêm một lát quyền
nào. Bên trong còn HẸP hơn: email và điện thoại chỉ ba vai xem đầy đủ (Chủ tịch, TGĐ, IR–Pháp
chế); Ban Kiểm soát và CNTT thấy đã tiếp xúc với ai nhưng không thấy số liên lạc. Thu hẹp thì
không cần chữ ký; nới mới cần.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.nha_dau_tu import (HINH_THUC_TIEP_XUC, LOAI_LIEN_HE, LienHeNhaDauTu,
                                   QuyenTruyCapHoSo, TuongTacNhaDauTu)
from app.services import nha_dau_tu as ND
from app.services import rules as R

router = APIRouter(prefix="/api/v1/ir-phap-che", tags=["ir-phap-che"])

XEM = ("chutich", "tgd", "ir_phapche", "bks", "cntt")
GHI = ("chutich", "tgd", "ir_phapche")


class LienHeIn(BaseModel):
    ten: str
    to_chuc: str = ""
    chuc_danh: str = ""
    loai: str = "khac"
    email: str = ""
    dien_thoai: str = ""
    can_cu_thu_thap: str = ""
    ghi_chu: str = ""
    dang_hoat_dong: bool = True


class TuongTacIn(BaseModel):
    lien_he_id: int
    ngay: date
    hinh_thuc: str = "gap"
    noi_dung_tom_tat: str = ""
    nguoi_du: list | None = None
    co_thong_tin_chua_cong_bo: bool = False
    thong_tin_da_tiet_lo: str = ""


class NoiCongBoIn(BaseModel):
    ban_ghi_cong_bo_id: int


class QuyenIn(BaseModel):
    ho_so: str
    nguoi_duoc_cap: str
    to_chuc: str = ""
    lien_he_id: int | None = None
    ly_do: str = ""
    ho_so_chua_cong_bo: bool = True
    cam_ket_bao_mat: bool = False
    can_cu_cam_ket: str = ""
    tu_ngay: date
    den_ngay: date | None = None


@router.get("/meta-ndt")
def meta_ndt(u: User = Depends(require_roles(*XEM))):
    return {"loai_lien_he": LOAI_LIEN_HE, "hinh_thuc_tiep_xuc": HINH_THUC_TIEP_XUC,
            "trang_thai_quyen": ND.TRANG_THAI_QUYEN, "ngay_bao_som": ND.NGAY_BAO_SOM,
            "ghi_duoc": GHI, "xem_du_lien_he": ND.VAI_XEM_DU_LIEN_HE,
            "xem_du": u.role in ND.VAI_XEM_DU_LIEN_HE}


@router.get("/nha-dau-tu")
def bang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return ND.bang_nha_dau_tu(db, u.role)


# ─────────────── danh bạ ───────────────
@router.post("/lien-he", status_code=201)
def lien_he_tao(body: LienHeIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    try:
        lh = ND.tao_lien_he(db, body.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    # Không ghi email/điện thoại vào nhật ký kiểm toán: nhật ký đọc được rộng hơn màn hình này.
    R.audit(db, u.username, u.role, "them_lien_he_nha_dau_tu", f"lien_he:{lh.id}",
            after={"ten": lh.ten, "to_chuc": lh.to_chuc, "loai": lh.loai})
    db.commit()
    return {"message": f"Đã thêm {lh.ten}", "lien_he": ND.ra_lh(lh, u.role)}


# ─────────────── sổ tiếp xúc ───────────────
@router.post("/tiep-xuc", status_code=201)
def tiep_xuc_ghi(body: TuongTacIn, u: User = Depends(require_roles(*GHI)),
                 db: Session = Depends(get_db)):
    if db.get(LienHeNhaDauTu, body.lien_he_id) is None:
        raise HTTPException(404, "Không có liên hệ này")
    try:
        tt = ND.ghi_tuong_tac(db, body.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role,
            "tiep_xuc_ndt_co_tiet_lo" if tt.co_thong_tin_chua_cong_bo else "tiep_xuc_ndt",
            f"tiep_xuc:{tt.id}", after={"ngay": str(tt.ngay), "hinh_thuc": tt.hinh_thuc})
    db.commit()
    return {"message": ("Đã ghi – lần này CÓ thông tin chưa công bố, phải nối tới bản công bố"
                        if ND.chua_xu_ly_tiet_lo(tt) else "Đã ghi lần tiếp xúc"),
            "tiep_xuc": ND.ra_tt(db, tt, u.role)}


@router.post("/tiep-xuc/{tid}/noi-cong-bo")
def tiep_xuc_noi_cong_bo(tid: int, body: NoiCongBoIn, u: User = Depends(require_roles(*GHI)),
                         db: Session = Depends(get_db)):
    tt = db.get(TuongTacNhaDauTu, tid)
    if tt is None:
        raise HTTPException(404, "Không có lần tiếp xúc này")
    try:
        ND.noi_ban_cong_bo(db, tt, body.ban_ghi_cong_bo_id)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "noi_tiet_lo_voi_ban_cong_bo", f"tiep_xuc:{tt.id}",
            after={"ban_ghi_cong_bo_id": tt.ban_ghi_cong_bo_id})
    db.commit()
    return {"message": "Đã nối tới bản công bố", "tiep_xuc": ND.ra_tt(db, tt, u.role)}


# ─────────────── quyền xem hồ sơ ───────────────
@router.post("/quyen-ho-so", status_code=201)
def quyen_cap(body: QuyenIn, u: User = Depends(require_roles(*GHI)),
              db: Session = Depends(get_db)):
    if body.lien_he_id is not None and db.get(LienHeNhaDauTu, body.lien_he_id) is None:
        raise HTTPException(404, "Không có liên hệ này")
    try:
        q = ND.cap_quyen(db, body.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "cap_quyen_xem_ho_so", f"quyen_ho_so:{q.id}",
            after={"ho_so": q.ho_so, "nguoi": q.nguoi_duoc_cap, "den_ngay": str(q.den_ngay)})
    db.commit()
    d = ND.ra_q(q)
    return {"message": ("Đã cấp quyền – KHÔNG có ngày hết hạn, đây là một việc phải xử lý"
                        if d["trang_thai"] == "khong_co_han" else "Đã cấp quyền"), "quyen": d}


@router.post("/quyen-ho-so/{qid}/thu-hoi")
def quyen_thu_hoi(qid: int, u: User = Depends(require_roles(*GHI)),
                  db: Session = Depends(get_db)):
    q = db.get(QuyenTruyCapHoSo, qid)
    if q is None:
        raise HTTPException(404, "Không có bản ghi cấp quyền này")
    try:
        ND.thu_hoi(db, q, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "thu_hoi_quyen_xem_ho_so", f"quyen_ho_so:{q.id}")
    db.commit()
    return {"message": "Đã thu hồi", "quyen": ND.ra_q(q)}
