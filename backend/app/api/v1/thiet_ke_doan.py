"""TK-1 · Khách tự thiết kế tour đoàn — hai nhóm cửa:

  /api/v1/tour-doan/*             — VTOS: danh sách thiết kế khách gửi (Sales thấy giá bán; Điều hành, Kế toán, BKS,
                                     Chủ tịch, TGĐ thấy cả giá vốn và biên) + đơn giá dịch vụ đoàn (Điều hành nhập,
                                     TP Điều hành / Chủ tịch / TGĐ duyệt).
  /api/v1/cong/khach/tour-doan/*  — phía NGOÀI (phiên cổng khách / cổ đông đã xác minh): khung, nguồn khách sạn + nhà
                                     hàng theo điểm, tạm tính, gửi, thiết kế của tôi.
Mọi con số tiền đều do máy chủ tính lại; trình duyệt chỉ gửi lựa chọn.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.db.session import get_db
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.services import thiet_ke_doan as S

router_vtos = APIRouter(prefix="/api/v1/tour-doan", tags=["tour-doan"])
router_cong = APIRouter(prefix="/api/v1/cong/khach/tour-doan", tags=["tour-doan"])


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiThietKe as ex:
        raise HTTPException(ex.status, str(ex))


# ── CỔNG ──────────────────────────────────────────────────────────────────────────────────────────
@router_cong.get("/khung")
def khung(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _goi(S._khach, tk)
    return S.khung_cong(db)


@router_cong.get("/nguon")
def nguon(diem: str, vao: str = "", ra: str = "", nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1,
          tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _goi(S._khach, tk)
    return _goi(S.nguon, db, diem[:80], vao, ra, nguoi_lon, tre_em, so_phong)


class ThietKeIn(BaseModel):
    thiet_ke: dict


class GuiIn(BaseModel):
    thiet_ke: dict
    ho_ten: str = ""            # KS-19m: bắt buộc khi hồ sơ khách chưa có tên
    dien_thoai: str = ""
    dong_y: bool = False
    ma: str = ""


@router_cong.post("/tinh")
def tinh(data: ThietKeIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(S.tinh_cong, db, tk, data.thiet_ke)


@router_cong.post("/gui")
def gui(data: GuiIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(S.gui, db, tk, data.model_dump())


@router_cong.get("/cua-toi")
def cua_toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return {"thiet_ke": _goi(S.cua_toi, db, tk)}


# ── VTOS ──────────────────────────────────────────────────────────────────────────────────────────
@router_vtos.get("")
def ds(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return _goi(S.ds_vtos, db, u)


@router_vtos.get("/ma/{ma}")
def lich_su(ma: str, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {"phien_ban": _goi(S.lich_su, db, u, ma)}


@router_vtos.get("/don-gia")
def don_gia(u: User = Depends(require_roles(*S.VAI_GIA_VON)), db: Session = Depends(get_db)):
    return _goi(S.ds_don_gia, db, u)


class DonGiaIn(BaseModel):
    loai: str
    ten: str
    pham_vi: str = "ca_hai"
    khu_vuc: str = ""
    gia: float | None = None
    tu_cho: int | None = None
    tu_diem: str = ""
    den_diem: str = ""
    hang_ve: str = ""
    gia_tre_em: float | None = None
    gia_em_be: float | None = None
    tu_ngay: str | None = None
    den_ngay: str | None = None
    ghi_chu: str = ""


class DuyetIn(BaseModel):
    dong_y: bool
    ly_do: str = ""


@router_vtos.post("/don-gia")
def tao_don_gia(data: DonGiaIn, u: User = Depends(require_roles(*S.VAI_NHAP_GIA)), db: Session = Depends(get_db)):
    return _goi(S.luu_don_gia, db, u, data.model_dump())


@router_vtos.post("/don-gia/{dg_id:int}")
def sua_don_gia(dg_id: int, data: DonGiaIn, u: User = Depends(require_roles(*S.VAI_NHAP_GIA)), db: Session = Depends(get_db)):
    return _goi(S.luu_don_gia, db, u, data.model_dump(), dg_id)


@router_vtos.post("/don-gia/{dg_id:int}/duyet")
def duyet(dg_id: int, data: DuyetIn, u: User = Depends(require_roles(*S.VAI_DUYET_GIA)), db: Session = Depends(get_db)):
    return _goi(S.duyet_don_gia, db, u, dg_id, data.dong_y, data.ly_do)


@router_vtos.post("/don-gia/{dg_id:int}/ngung")
def ngung(dg_id: int, u: User = Depends(require_roles(*S.VAI_DUYET_GIA)), db: Session = Depends(get_db)):
    return _goi(S.ngung_don_gia, db, u, dg_id)


# ── TK-1e · lịch ngày lễ Tết (thù lao HDV ×2 trong tạm tính) ────────────────────────────────────────
class NgayLeIn(BaseModel):
    ngay: str
    ten: str = ""


@router_vtos.get("/ngay-le")
def ngay_le(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return _goi(S.ds_ngay_le, db, u)


@router_vtos.post("/ngay-le")
def them_ngay_le(data: NgayLeIn, u: User = Depends(require_roles(*S.VAI_NHAP_GIA)), db: Session = Depends(get_db)):
    return _goi(S.luu_ngay_le, db, u, data.model_dump())


@router_vtos.post("/ngay-le/{nid:int}/xoa")
def xoa_ngay_le(nid: int, u: User = Depends(require_roles(*S.VAI_NHAP_GIA)), db: Session = Depends(get_db)):
    return _goi(S.xoa_ngay_le, db, u, nid)


# ── TK-2 · báo giá chính thức (giai đoạn 2) ──────────────────────────────────────────────────────────
from app.services import bao_gia_doan as BG  # noqa: E402


def _bg(f, *a, **k):
    try:
        return f(*a, **k)
    except (BG.LoiBaoGia, S.LoiThietKe) as ex:
        raise HTTPException(ex.status, str(ex))


class BaoGiaIn(BaseModel):
    dong: list[dict] | None = None
    bien_pt: float | None = None
    bao_gom: list[str] | None = None
    khong_bao_gom: list[str] | None = None
    ghi_chu: str | None = None


class LyDoIn(BaseModel):
    ly_do: str = ""


class DongYIn(BaseModel):
    ma_bam: str
    dong_y: bool = False


@router_vtos.post("/{tid:int}/bao-gia")
def lap_bao_gia(tid: int, u: User = Depends(require_roles(*BG.VAI_LAP)), db: Session = Depends(get_db)):
    return _bg(BG.lap, db, u, tid)


@router_vtos.get("/bao-gia/{bid:int}")
def xem_bao_gia(bid: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return _bg(BG.xem, db, u, bid)


@router_vtos.post("/bao-gia/{bid:int}")
def luu_bao_gia(bid: int, data: BaoGiaIn, u: User = Depends(require_roles(*BG.VAI_LAP)), db: Session = Depends(get_db)):
    return _bg(BG.luu, db, u, bid, data.model_dump(exclude_none=True))


@router_vtos.post("/bao-gia/{bid:int}/gui-duyet")
def gui_duyet_bao_gia(bid: int, data: LyDoIn, u: User = Depends(require_roles(*BG.VAI_LAP)), db: Session = Depends(get_db)):
    return _bg(BG.gui_duyet, db, u, bid, data.ly_do)


@router_vtos.post("/bao-gia/{bid:int}/duyet")
def duyet_bao_gia(bid: int, data: DuyetIn, u: User = Depends(require_roles(*BG.VAI_DUYET_TP)), db: Session = Depends(get_db)):
    return _bg(BG.duyet, db, u, bid, data.dong_y, data.ly_do)


@router_cong.post("/bao-gia/{bid:int}/dong-y")
def khach_dong_y(bid: int, data: DongYIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _bg(BG.khach_dong_y, db, tk, bid, data.ma_bam, data.dong_y)
