"""CG-1 · Cổng kết nối VTD — hai nhóm cửa:

  /api/v1/cong/*              — phía NGOÀI (khách hàng, đối tác, cổ đông). Hai cửa công khai (gửi mã,
                                xác thực) có phanh theo địa chỉ mạng; còn lại đòi PHIÊN NGOÀI, ký bằng
                                khoá riêng — đưa phiên ấy vào bất kỳ cửa nội bộ nào cũng là 401.
  /api/v1/tai-khoan-ngoai/*   — phía VTOS: hàng chờ duyệt hồ sơ đối tác / cổ đông, khoá / mở khoá.
"""
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.cong_ngoai import TaiKhoanNgoai, TRANG_THAI_NGOAI
from app.services import cong_ngoai as C

router = APIRouter(prefix="/api/v1/cong", tags=["cong-ket-noi"])
router_vtos = APIRouter(prefix="/api/v1/tai-khoan-ngoai", tags=["cong-ket-noi"])

# Phanh theo địa chỉ mạng cho hai cửa công khai — cùng khuôn với cửa khảo sát khách hàng.
CUA_SO_GIAY, TOI_DA = 600, 30
_LUOT: dict[str, list[float]] = defaultdict(list)


def _phanh(req: Request) -> str:
    ip = (req.client.host if req.client else "") or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA:
        _LUOT[ip] = v
        raise HTTPException(429, "Quá nhiều lượt thử từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(bay_gio)
    _LUOT[ip] = v
    return ip


def _loi(ex: C.LoiCong):
    raise HTTPException(ex.status, {"message": str(ex), "ma": ex.ma} if ex.ma else str(ex))


_bearer = HTTPBearer(auto_error=False)


def tai_khoan_ngoai(cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
                    db: Session = Depends(get_db)) -> TaiKhoanNgoai:
    tk = C.doc_phien(db, cred.credentials if cred else "")
    if tk is None:
        raise HTTPException(401, "Phiên đăng nhập cổng đã hết hạn — đăng nhập lại")
    return tk


tai_khoan_ngoai.la_cong_chan_quyen = True   # bộ kiểm quyền (ks2, ks_robot) nhận đây là cổng chặn


# ---------------------------------------------------------------- phía ngoài

@router.get("/kenh")
def kenh(db: Session = Depends(get_db)):
    """Kênh nhận mã đang mở — giao diện khoá nút kênh chưa cấu hình và ghi lý do."""
    return C.kenh_san_sang(db)


class GuiMaIn(BaseModel):
    loai: str
    lien_he: str
    kenh: str


@router.post("/ma")
def gui_ma(data: GuiMaIn, request: Request, db: Session = Depends(get_db)):
    ip = _phanh(request)
    try:
        return C.gui_ma(db, data.loai, data.lien_he, data.kenh, ip)
    except C.LoiCong as ex:
        _loi(ex)


class XacThucIn(BaseModel):
    khoa: str
    ma: str
    dong_y_dieu_khoan: bool = False


@router.post("/xac-thuc")
def xac_thuc(data: XacThucIn, request: Request, db: Session = Depends(get_db)):
    _phanh(request)
    try:
        tk, phien = C.xac_thuc(db, data.khoa, data.ma, data.dong_y_dieu_khoan)
    except C.LoiCong as ex:
        _loi(ex)
    return {"phien": phien, "toi": C.toi_out(tk)}


@router.get("/toi")
def toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai)):
    return C.toi_out(tk)


class ToiIn(BaseModel):
    ho_ten: str | None = None
    nhan_tin_quang_cao: bool | None = None


@router.post("/toi")
def sua_toi(data: ToiIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return C.toi_out(C.cap_nhat_toi(db, tk, data.ho_ten, data.nhan_tin_quang_cao))


class HoSoIn(BaseModel):
    ho_ten: str
    loai_doi_tac: str = ""
    ten_don_vi: str = ""
    ma_so_thue: str = ""
    giay_to: str = ""
    tk_luu_ky: str = ""
    ghi_chu: str = ""


@router.post("/ho-so")
def gui_ho_so(data: HoSoIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    try:
        t = C.gui_ho_so(db, tk, data.model_dump())
    except C.LoiCong as ex:
        _loi(ex)
    return {"message": "Đã gửi hồ sơ — Vietourist sẽ duyệt và báo lại khi bạn đăng nhập", "toi": C.toi_out(t)}


@router.post("/dang-xuat")
def dang_xuat(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    C.dang_xuat(db, tk)
    return {"message": "Đã đăng xuất"}


# ---------------------------------------------------------------- phía VTOS

@router_vtos.get("")
def danh_sach(trang_thai: str = "", u: User = Depends(require_roles(*C.VAI_XEM)), db: Session = Depends(get_db)):
    return {"dong": C.danh_sach(db, u, trang_thai), "trang_thai": TRANG_THAI_NGOAI, "kenh": C.kenh_san_sang(db)}


class XuLyIn(BaseModel):
    hanh_dong: str            # duyet / bo_sung / tu_choi / khoa / mo_khoa
    ly_do: str = ""


@router_vtos.post("/{tid}")
def xu_ly(tid: int, data: XuLyIn, u: User = Depends(require_roles(*C.VAI_XEM)),
          db: Session = Depends(get_db)):
    tk = db.get(TaiKhoanNgoai, tid)
    if tk is None:
        raise HTTPException(404, "Không có tài khoản này")
    try:
        t = C.xu_ly(db, u, tk, data.hanh_dong, data.ly_do)
    except C.LoiCong as ex:
        _loi(ex)
    return {"message": f"Đã chuyển sang «{TRANG_THAI_NGOAI[t.trang_thai]}»", "dong": C.quan_tri_out(t, u)}


# ──────────────────────────────────────────── DK-1 · tạo tài khoản bốn bước, mã ở bước CUỐI
# Bốn cửa dưới đây đều CÔNG KHAI nên đều đi qua phanh theo địa chỉ mạng, như hai cửa cũ.

class DangKyLienHeIn(BaseModel):
    loai: str
    ho_ten: str
    dien_thoai: str = ""
    email: str = ""


@router.post("/dang-ky/lien-he")
def dang_ky_lien_he(data: DangKyLienHeIn, request: Request, db: Session = Depends(get_db)):
    """Bước 1. Câu trả lời KHÔNG đổi dù liên hệ đã có tài khoản hay chưa."""
    ip = _phanh(request)
    try:
        return C.dang_ky_b1(db, data.loai, data.ho_ten, data.dien_thoai, data.email, ip)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyMatKhauIn(BaseModel):
    khoa: str
    mat_khau: str


@router.post("/dang-ky/mat-khau")
def dang_ky_mat_khau(data: DangKyMatKhauIn, request: Request, db: Session = Depends(get_db)):
    """Bước 2. Từ chối thì nói rõ vì sao — câu ấy hiện thẳng dưới ô nhập."""
    _phanh(request)
    try:
        return C.dang_ky_b2(db, data.khoa, data.mat_khau)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyDieuKhoanIn(BaseModel):
    khoa: str
    dong_y_dieu_khoan: bool = False
    nhan_tin_quang_cao: bool = False


@router.post("/dang-ky/dieu-khoan")
def dang_ky_dieu_khoan(data: DangKyDieuKhoanIn, request: Request, db: Session = Depends(get_db)):
    """Bước 3. Nhận tin quảng cáo mặc định TẮT, không bao giờ tự bật."""
    _phanh(request)
    try:
        return C.dang_ky_b3(db, data.khoa, data.dong_y_dieu_khoan, data.nhan_tin_quang_cao)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyMaIn(BaseModel):
    khoa: str
    kenh: str


@router.post("/dang-ky/ma")
def dang_ky_ma(data: DangKyMaIn, request: Request, db: Session = Depends(get_db)):
    """Bước 4a — gửi mã tới chủ liên hệ."""
    ip = _phanh(request)
    try:
        return C.dang_ky_gui_ma(db, data.khoa, data.kenh, ip)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyXongIn(BaseModel):
    khoa: str
    ma: str


@router.post("/dang-ky/xong")
def dang_ky_xong(data: DangKyXongIn, request: Request, db: Session = Depends(get_db)):
    """Bước 4b — gõ mã. Cửa duy nhất sinh ra một `TaiKhoanNgoai` có mật khẩu."""
    _phanh(request)
    try:
        tk, phien = C.dang_ky_xong(db, data.khoa, data.ma)
    except C.LoiCong as ex:
        _loi(ex)
    return {"phien": phien, "toi": C.toi_out(tk)}
