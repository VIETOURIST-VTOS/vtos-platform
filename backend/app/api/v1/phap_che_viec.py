"""API Đợt D2 – bàn làm việc Pháp chế: yêu cầu, rà soát hợp đồng, sổ chữ ký, xác nhận chủ số liệu.

CÙNG MỘT TIỀN TỐ `/api/v1/ir-phap-che` với Đợt D1, và đó là chủ ý: tiền tố ấy đã được khai trong
`access.MAN_HINH_API` và đã có trong bảng phạm vi đã chốt của test_p2. Đặt các cửa mới vào đúng
nhóm cũ nghĩa là đợt này KHÔNG tự khai thêm một lát quyền nào.

CHƯA MỞ CỬA GỬI YÊU CẦU CHO CÁC PHÒNG BAN, và đây là một việc còn thiếu chứ không phải một việc đã
xong. Hôm nay chỉ năm vai của D1 ghi được, nên một trưởng phòng muốn hỏi Pháp chế thì Pháp chế ghi
hộ, có cột `phong_gui`/`nguoi_gui` để biết việc của ai. Mở cửa cho mọi vai là NỚI QUYỀN trên tiền
tố này cho toàn bộ tài khoản – một lần nới phải có người ký, làn viết phần mềm không tự khai.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.phap_che import BanGhiCongBo
from app.models.phap_che_viec import (BanGhiChuKy, KET_LUAN_RS, LOAI_CHU_KY, LOAI_YEU_CAU, MUC_DO,
                                      MUC_RUI_RO, RaSoatHopDong, TRANG_THAI_XN, TRANG_THAI_YC,
                                      XacNhanChuSoLieu, YeuCauPhapChe)
from app.services import phap_che_viec as PV
from app.services import rules as R

router = APIRouter(prefix="/api/v1/ir-phap-che", tags=["ir-phap-che"])

XEM = ("chutich", "tgd", "ir_phapche", "bks", "cntt")
GHI = ("chutich", "tgd", "ir_phapche")


class YeuCauIn(BaseModel):
    loai: str = "y_kien_phap_ly"
    tieu_de: str
    noi_dung: str = ""
    phong_gui: str = ""
    nguoi_gui: str = ""
    muc_do: str = "thuong"
    han_mong_muon: date | None = None
    attachment_id: int | None = None


class DongIn(BaseModel):
    trang_thai: str = "xong"
    ket_qua: str = ""


class BoSungIn(BaseModel):
    can_bo_sung: str = ""


class RaSoatIn(BaseModel):
    so_hop_dong: str = ""
    doi_tac: str = ""
    loai_hop_dong: str = ""
    gia_tri: float | None = None
    ngay_nhan: date | None = None
    ngay_tra: date | None = None
    ket_luan: str = ""
    rui_ro: list | None = None
    dieu_kien: str = ""
    nguoi_ra_soat: str = ""
    attachment_id: int | None = None


class ChuKyIn(BaseModel):
    van_ban_id: int | None = None
    mo_ta: str = ""
    nguoi_ky: str
    chuc_danh: str = ""
    ngay_ky: date
    loai_chu_ky: str = "tuoi"
    can_cu_tham_quyen: str = ""
    ghi_chu: str = ""
    attachment_id: int | None = None


class XacNhanIn(BaseModel):
    chi_muc: str
    chu_so_lieu: str


class TraLoiIn(BaseModel):
    dong_y: bool
    y_kien: str = ""


@router.get("/meta-viec")
def meta_viec(u: User = Depends(require_roles(*XEM))):
    return {"loai_yeu_cau": LOAI_YEU_CAU, "trang_thai_yeu_cau": TRANG_THAI_YC, "muc_do": MUC_DO,
            "ket_luan_ra_soat": KET_LUAN_RS, "muc_rui_ro": MUC_RUI_RO,
            "loai_chu_ky": LOAI_CHU_KY, "trang_thai_xac_nhan": TRANG_THAI_XN,
            "ngay_coi_la_ton": PV.NGAY_COI_LA_TON, "ghi_duoc": GHI,
            "con_thieu": ("Chưa có cửa cho phòng ban tự gửi yêu cầu – mở cửa ấy là nới quyền trên "
                          "nhóm API này cho mọi vai, phải có người ký.")}


# ─────────────── yêu cầu ───────────────
@router.get("/yeu-cau")
def yeu_cau_ds(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return PV.ban_lam_viec(db)


@router.post("/yeu-cau", status_code=201)
def yeu_cau_tao(body: YeuCauIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    if body.loai not in LOAI_YEU_CAU:
        raise HTTPException(422, f"Loại yêu cầu không hợp lệ: {body.loai}")
    if body.muc_do not in MUC_DO:
        raise HTTPException(422, f"Mức độ không hợp lệ: {body.muc_do}")
    if not (body.tieu_de or "").strip():
        raise HTTPException(422, "Phải ghi tiêu đề")
    yc = PV.tao_yeu_cau(db, body.model_dump(), u.username)
    R.audit(db, u.username, u.role, "mo_yeu_cau_phap_che", f"yeu_cau:{yc.id}",
            after={"loai": yc.loai, "tieu_de": yc.tieu_de})
    db.commit()
    return {"message": f"Đã mở yêu cầu #{yc.id}", "yeu_cau": PV.ra_yc(db, yc)}


def _lay_yc(db: Session, yid: int) -> YeuCauPhapChe:
    yc = db.get(YeuCauPhapChe, yid)
    if yc is None:
        raise HTTPException(404, "Không có yêu cầu này")
    return yc


@router.post("/yeu-cau/{yid}/nhan")
def yeu_cau_nhan(yid: int, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    yc = _lay_yc(db, yid)
    try:
        PV.nhan_viec(db, yc, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "nhan_yeu_cau_phap_che", f"yeu_cau:{yc.id}")
    db.commit()
    return {"message": f"{u.username} đã nhận việc #{yc.id}", "yeu_cau": PV.ra_yc(db, yc)}


@router.post("/yeu-cau/{yid}/cho-bo-sung")
def yeu_cau_cho_bo_sung(yid: int, body: BoSungIn, u: User = Depends(require_roles(*GHI)),
                        db: Session = Depends(get_db)):
    yc = _lay_yc(db, yid)
    try:
        PV.cho_bo_sung(db, yc, body.can_bo_sung)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "yeu_cau_cho_bo_sung", f"yeu_cau:{yc.id}")
    db.commit()
    return {"message": "Đã chuyển sang chờ bổ sung", "yeu_cau": PV.ra_yc(db, yc)}


@router.post("/yeu-cau/{yid}/dong")
def yeu_cau_dong(yid: int, body: DongIn, u: User = Depends(require_roles(*GHI)),
                 db: Session = Depends(get_db)):
    """Đóng việc. Không có kết quả viết ra thì không đóng được – xem services/phap_che_viec.py."""
    yc = _lay_yc(db, yid)
    try:
        PV.dong_yeu_cau(db, yc, body.trang_thai, body.ket_qua, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, f"dong_yeu_cau_{yc.trang_thai}", f"yeu_cau:{yc.id}",
            after={"ket_qua": yc.ket_qua[:200]})
    db.commit()
    return {"message": f"Đã đóng #{yc.id} – {TRANG_THAI_YC[yc.trang_thai]}",
            "yeu_cau": PV.ra_yc(db, yc)}


# ─────────────── rà soát hợp đồng ───────────────
@router.get("/yeu-cau/{yid}/ra-soat")
def ra_soat_xem(yid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    _lay_yc(db, yid)
    rs = db.execute(select(RaSoatHopDong).where(RaSoatHopDong.yeu_cau_id == yid)).scalars().first()
    return {"co": rs is not None, "ra_soat": PV.ra_rs(rs) if rs else None}


@router.put("/yeu-cau/{yid}/ra-soat")
def ra_soat_ghi(yid: int, body: RaSoatIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    yc = _lay_yc(db, yid)
    try:
        rs = PV.ghi_ra_soat(db, yc, body.model_dump(exclude_unset=True), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "ghi_ra_soat_hop_dong", f"ra_soat:{rs.id}",
            after={"ket_luan": rs.ket_luan, "so_hop_dong": rs.so_hop_dong})
    db.commit()
    return {"message": "Đã lưu rà soát", "ra_soat": PV.ra_rs(rs)}


# ─────────────── sổ chữ ký ───────────────
@router.get("/chu-ky")
def chu_ky_ds(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    ds = list(db.execute(select(BanGhiChuKy).order_by(BanGhiChuKy.ngay_ky.desc(),
                                                      BanGhiChuKy.id.desc())).scalars())
    return {"so": len(ds),
            "rows": [{"id": b.id, "van_ban_id": b.van_ban_id, "mo_ta": b.mo_ta,
                      "nguoi_ky": b.nguoi_ky, "chuc_danh": b.chuc_danh, "ngay_ky": b.ngay_ky,
                      "loai_chu_ky": b.loai_chu_ky,
                      "loai_chu_ky_ten": LOAI_CHU_KY.get(b.loai_chu_ky, b.loai_chu_ky),
                      "can_cu_tham_quyen": b.can_cu_tham_quyen, "ghi_chu": b.ghi_chu,
                      "attachment_id": b.attachment_id, "boi": b.boi, "luc": b.luc} for b in ds],
            "ghi_chu": ("Căn cứ thẩm quyền là bắt buộc: một chữ ký không nói được ký theo thẩm "
                        "quyền nào chính là câu hỏi đầu tiên của mọi lần soát lại.")}


@router.post("/chu-ky", status_code=201)
def chu_ky_ghi(body: ChuKyIn, u: User = Depends(require_roles(*GHI)),
               db: Session = Depends(get_db)):
    if body.loai_chu_ky not in LOAI_CHU_KY:
        raise HTTPException(422, f"Loại chữ ký không hợp lệ: {body.loai_chu_ky}")
    try:
        b = PV.ghi_chu_ky(db, body.model_dump(), u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "ghi_so_chu_ky", f"chu_ky:{b.id}",
            after={"nguoi_ky": b.nguoi_ky, "ngay_ky": str(b.ngay_ky)})
    db.commit()
    return {"message": f"Đã ghi sổ chữ ký #{b.id}", "id": b.id}


# ─────────────── xác nhận chủ số liệu ───────────────
def _lay_bg(db: Session, bid: int) -> BanGhiCongBo:
    bg = db.get(BanGhiCongBo, bid)
    if bg is None:
        raise HTTPException(404, "Không có bản ghi công bố này")
    return bg


@router.get("/ban-ghi/{bid}/xac-nhan")
def xac_nhan_ds(bid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    _lay_bg(db, bid)
    ds = list(db.execute(select(XacNhanChuSoLieu).where(
        XacNhanChuSoLieu.ban_ghi_id == bid).order_by(XacNhanChuSoLieu.id)).scalars())
    chan = PV.chan_cong_bo(db, bid)
    return {"so": len(ds), "rows": [PV.ra_xn(x) for x in ds],
            "cong_bo_duoc": not chan, "vi_sao_chua": chan}


@router.post("/ban-ghi/{bid}/xac-nhan", status_code=201)
def xac_nhan_mo(bid: int, body: XacNhanIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    bg = _lay_bg(db, bid)
    try:
        x = PV.mo_xac_nhan(db, bg, body.chi_muc, body.chu_so_lieu, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "hoi_xac_nhan_chu_so_lieu", f"cong_bo:{bid}",
            after={"chi_muc": x.chi_muc, "chu_so_lieu": x.chu_so_lieu})
    db.commit()
    return {"message": f"Đã hỏi {x.chu_so_lieu} về '{x.chi_muc}'", "xac_nhan": PV.ra_xn(x)}


@router.post("/xac-nhan/{xid}/tra-loi")
def xac_nhan_tra_loi(xid: int, body: TraLoiIn, u: User = Depends(require_roles(*GHI)),
                     db: Session = Depends(get_db)):
    x = db.get(XacNhanChuSoLieu, xid)
    if x is None:
        raise HTTPException(404, "Không có xác nhận này")
    try:
        PV.tra_loi_xac_nhan(db, x, body.dong_y, body.y_kien, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, f"xac_nhan_{x.trang_thai}", f"xac_nhan:{x.id}",
            after={"chi_muc": x.chi_muc, "y_kien": x.y_kien[:200]})
    db.commit()
    return {"message": TRANG_THAI_XN[x.trang_thai], "xac_nhan": PV.ra_xn(x)}
