"""DT-1 · Cổng đối tác VTD — hai nhóm cửa:

  /api/v1/cong/doi-tac/*             — phía ĐỐI TÁC: đòi PHIÊN CỔNG NGOÀI (khoá ký riêng), tài khoản đối
                                       tác đang hoạt động VÀ đã nối với một đối tác bán hàng.
  /api/v1/tai-khoan-ngoai/{tid}/...  — phía VTOS: người duyệt hồ sơ xem gợi ý và NỐI tài khoản với đối tác.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.cong_ngoai import TaiKhoanNgoai
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.services import cong_ngoai as C
from app.services import doi_tac_cong as D

router = APIRouter(prefix="/api/v1/cong/doi-tac", tags=["cong-doi-tac"])
router_noi = APIRouter(prefix="/api/v1/tai-khoan-ngoai", tags=["cong-doi-tac"])


def _loi(ex: D.LoiDoiTac):
    raise HTTPException(ex.status, {"message": str(ex), "ma": ex.ma} if ex.ma else str(ex))


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except D.LoiDoiTac as ex:
        _loi(ex)


# ---------------------------------------------------------------- phía đối tác

@router.get("/ban-lam-viec")
def ban_lam_viec(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(D.ban_lam_viec, db, tk)


@router.get("/tour")
def ds_tour(q: str = "", tu_ngay: date | None = None, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(D.tours, db, tk, q, tu_ngay)


class GiuChoIn(BaseModel):
    tour_id: int
    ten_khach: str
    dien_thoai: str
    nguoi_lon: int = 1
    tre_em: int = 0
    ghi_chu: str = ""


@router.post("/giu-cho")
def giu_cho(data: GiuChoIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    b = _goi(D.giu_cho, db, tk, data.tour_id, data.ten_khach, data.dien_thoai, data.nguoi_lon, data.tre_em, data.ghi_chu)
    return {"message": f"Đã giữ chỗ {b.code} — giữ đến {b.giu_cho_den:%d/%m %H:%M}. Chuyển cọc với nội dung «{b.code}».",
            "ma": b.code}


@router.get("/booking")
def ds_booking(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return {"booking": _goi(D.bookings, db, tk)}


@router.get("/booking/{ma}/qr")
def qr(ma: str, muc: str = "", tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(D.qr, db, tk, ma, muc)


@router.get("/hoa-hong")
def hoa_hong(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(D.hoa_hong, db, tk)


@router.get("/cong-no")
def cong_no(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(D.cong_no, db, tk)


class GioiThieuIn(BaseModel):
    tour_id: int | None = None
    ten_khach: str
    dien_thoai: str
    so_khach: int = 1
    ghi_chu: str = ""
    dong_y: bool = False


@router.post("/gioi-thieu")
def gioi_thieu(data: GioiThieuIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _goi(D.gioi_thieu, db, tk, data.tour_id, data.ten_khach, data.dien_thoai, data.so_khach, data.ghi_chu, data.dong_y)
    return {"message": "Đã gửi giới thiệu — nhu cầu vào hàng chờ Sales, ghi nhận nguồn từ bạn kèm thời điểm gửi"}


@router.get("/gioi-thieu")
def ds_gioi_thieu(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return {"gioi_thieu": _goi(D.gioi_thieu_ds, db, tk)}


# ---------------------------------------------------------------- KS-16h: nguồn đơn · vụ việc · đối soát

@router.get("/nguon")
def nguon(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return _goi(D.nguon_cua_ctv, db, tk)


class KhieuNaiNguonIn(BaseModel):
    booking_ma: str = ""
    khach_sdt: str = ""
    noi_dung: str


@router.post("/khieu-nai")
def khieu_nai_nguon(data: KhieuNaiNguonIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    v = _goi(D.khieu_nai_nguon, db, tk, data.booking_ma, data.khach_sdt, data.noi_dung)
    return {"message": f"Đã ghi khiếu nại {v.ma} — xử lý trong 5 ngày làm việc (hạn {v.han:%d/%m/%Y})", "ma": v.ma}


@router.get("/vu-viec")
def vu_viec(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return {"vu_viec": _goi(D.vu_viec, db, tk)}


@router.get("/doi-soat")
def doi_soat(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return {"bang": _goi(D.doi_soat, db, tk)}


class DongYIn(BaseModel):
    dong_id: int | None = None


@router.post("/doi-soat/{bang_id}/dong-y")
def doi_soat_dong_y(bang_id: int, data: DongYIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _goi(D.doi_soat_dong_y, db, tk, bang_id, data.dong_id)
    return {"message": "Đã ghi đồng ý" + ("" if data.dong_id else " cả bảng")}


class KhieuNaiDongIn(BaseModel):
    dong_id: int
    noi_dung: str


@router.post("/doi-soat/{bang_id}/khieu-nai")
def doi_soat_khieu_nai(bang_id: int, data: KhieuNaiDongIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    v = _goi(D.doi_soat_khieu_nai, db, tk, bang_id, data.dong_id, data.noi_dung)
    return {"message": f"Đã ghi khiếu nại {v.ma} — đơn này tách riêng, phần còn lại vẫn trả đúng hạn", "ma": v.ma}


# ---------------------------------------------------------------- phía VTOS: nối hồ sơ

def _tk(db: Session, tid: int, u: User) -> TaiKhoanNgoai:
    tk = db.get(TaiKhoanNgoai, tid)
    if tk is None or not C.xem_duoc(u, tk):
        raise HTTPException(404, "Không có tài khoản này")
    return tk


@router_noi.get("/doi-tac-ban-hang")
def tim_doi_tac(q: str = "", u: User = Depends(require_roles(*C.VAI_XEM)), db: Session = Depends(get_db)):
    return {"doi_tac": D.ds_doi_tac(db, q)}


@router_noi.get("/{tid}/doi-tac")
def xem_noi(tid: int, u: User = Depends(require_roles(*C.VAI_XEM)), db: Session = Depends(get_db)):
    return D.thong_tin_noi(db, _tk(db, tid, u))


class NoiIn(BaseModel):
    hanh_dong: str              # noi / tao_moi / go
    doi_tac_id: int | None = None
    duyet: bool = False


@router_noi.post("/{tid}/doi-tac")
def noi(tid: int, data: NoiIn, u: User = Depends(require_roles(*C.VAI_XEM)), db: Session = Depends(get_db)):
    tk = _goi(D.noi, db, u, _tk(db, tid, u), data.hanh_dong, data.doi_tac_id, data.duyet)
    msg = {"noi": "Đã nối hồ sơ", "tao_moi": "Đã lập đối tác mới và nối hồ sơ", "go": "Đã gỡ nối"}.get(data.hanh_dong, "Đã lưu")
    if data.duyet and tk.trang_thai == "hoat_dong":
        msg += " · đã duyệt tài khoản"
    return {"message": msg, "dong": C.quan_tri_out(tk, u), "noi": D.thong_tin_noi(db, tk)}
