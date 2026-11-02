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


# DK-4 (02/11/2026): hai cửa cũ `POST /cong/ma` + `POST /cong/xac-thuc` đã XOÁ. Chúng cho tạo tài khoản
# KHÔNG MẬT KHẨU chỉ bằng mã một lần — trái điều 5 Chủ tịch chốt 01/11/2026 («mã không bao giờ thay
# được mật khẩu»). DK-3 bỏ chúng khỏi màn hình, nhưng ai gọi thẳng vào máy chủ vẫn mở được tài khoản.
# Nay mã chỉ còn là LỚP THỨ HAI ở ba chỗ: tạo tài khoản (/dang-ky/*), máy lạ (/dang-nhap/xac-minh),
# đặt lại mật khẩu (/quen-mat-khau/*). Phép thử: test_cg1 · test_dk4_cua_vao_bang_ma_da_mat_khoi_may_chu.


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
# Năm cửa dưới đây đều CÔNG KHAI: người gõ CHƯA CÓ tài khoản nên không có vai trò nào để đòi.
# Chỗ chặn của chúng là phanh theo địa chỉ mạng, và DK-1b đưa nó lên CHỮ KÝ hàm thay vì để
# lẫn trong thân hàm — để máy đọc được, và để ai mở cửa mới mà quên phanh thì phép thử khai
# quyền (KS-2 · q1) bắt được ngay thay vì phải có người đọc mã.

def cong_cua_mo(request: Request) -> str:
    """Cửa CÔNG KHAI của cổng ngoài — trả về địa chỉ mạng sau khi đã qua phanh.

    Không mang vai trò vì người dùng của nó không có tài khoản VTOS. Đây là chỗ DUY NHẤT
    chặn các cửa ấy, nên nó phải nằm ở nơi máy nhìn thấy.
    """
    return _phanh(request)



class DangKyLienHeIn(BaseModel):
    loai: str
    ho_ten: str
    dien_thoai: str = ""
    email: str = ""


@router.post("/dang-ky/lien-he")
def dang_ky_lien_he(data: DangKyLienHeIn, ip: str = Depends(cong_cua_mo),
                    db: Session = Depends(get_db)):
    """Bước 1. Câu trả lời KHÔNG đổi dù liên hệ đã có tài khoản hay chưa."""
    try:
        return C.dang_ky_b1(db, data.loai, data.ho_ten, data.dien_thoai, data.email, ip)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyMatKhauIn(BaseModel):
    khoa: str
    mat_khau: str


@router.post("/dang-ky/mat-khau")
def dang_ky_mat_khau(data: DangKyMatKhauIn, ip: str = Depends(cong_cua_mo),
                     db: Session = Depends(get_db)):
    """Bước 2. Từ chối thì nói rõ vì sao — câu ấy hiện thẳng dưới ô nhập."""
    try:
        return C.dang_ky_b2(db, data.khoa, data.mat_khau)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyDieuKhoanIn(BaseModel):
    khoa: str
    dong_y_dieu_khoan: bool = False
    nhan_tin_quang_cao: bool = False


@router.post("/dang-ky/dieu-khoan")
def dang_ky_dieu_khoan(data: DangKyDieuKhoanIn, ip: str = Depends(cong_cua_mo),
                       db: Session = Depends(get_db)):
    """Bước 3. Nhận tin quảng cáo mặc định TẮT, không bao giờ tự bật."""
    try:
        return C.dang_ky_b3(db, data.khoa, data.dong_y_dieu_khoan, data.nhan_tin_quang_cao)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyMaIn(BaseModel):
    khoa: str
    kenh: str


@router.post("/dang-ky/ma")
def dang_ky_ma(data: DangKyMaIn, ip: str = Depends(cong_cua_mo),
               db: Session = Depends(get_db)):
    """Bước 4a — gửi mã tới chủ liên hệ."""
    try:
        return C.dang_ky_gui_ma(db, data.khoa, data.kenh, ip)
    except C.LoiCong as ex:
        _loi(ex)


class DangKyXongIn(BaseModel):
    khoa: str
    ma: str


@router.post("/dang-ky/xong")
def dang_ky_xong(data: DangKyXongIn, ip: str = Depends(cong_cua_mo),
                 db: Session = Depends(get_db)):
    """Bước 4b — gõ mã. Cửa duy nhất sinh ra một `TaiKhoanNgoai` có mật khẩu."""
    try:
        tk, phien = C.dang_ky_xong(db, data.khoa, data.ma)
    except C.LoiCong as ex:
        _loi(ex)
    return {"phien": phien, "toi": C.toi_out(tk)}


# ──────────────────────────────────────────── DK-2 · đăng nhập bằng mật khẩu, nhớ máy, quên mật khẩu
# Bốn cửa đầu CÔNG KHAI (qua cong_cua_mo đã khai ở DK-1b); hai cửa cuối đòi PHIÊN CỔNG NGOÀI.

class DangNhapIn(BaseModel):
    loai: str
    lien_he: str
    mat_khau: str
    dau_nho: str = ""
    kenh: str = ""


@router.post("/dang-nhap")
def dang_nhap(data: DangNhapIn, ip: str = Depends(cong_cua_mo), db: Session = Depends(get_db)):
    """Bước 1. Mọi kiểu sai trả CÙNG MỘT câu — màn này không được thành máy dò."""
    try:
        return C.dang_nhap(db, data.loai, data.lien_he, data.mat_khau, data.dau_nho, data.kenh, ip)
    except C.LoiCong as ex:
        _loi(ex)


class DangNhapXacMinhIn(BaseModel):
    khoa: str
    ma: str
    nho_may: bool = False
    ten_may: str = ""


@router.post("/dang-nhap/xac-minh")
def dang_nhap_xac_minh(data: DangNhapXacMinhIn, ip: str = Depends(cong_cua_mo),
                       db: Session = Depends(get_db)):
    """Bước 2, chỉ khi máy lạ. Mã MỘT MÌNH không mở được gì — phải qua bước 1 trước."""
    try:
        return C.dang_nhap_xac_minh(db, data.khoa, data.ma, data.nho_may, data.ten_may, ip)
    except C.LoiCong as ex:
        _loi(ex)


class QuenMaIn(BaseModel):
    loai: str
    lien_he: str
    kenh: str


@router.post("/quen-mat-khau/ma")
def quen_mat_khau_ma(data: QuenMaIn, ip: str = Depends(cong_cua_mo),
                     db: Session = Depends(get_db)):
    """Câu trả lời KHÔNG đổi dù liên hệ có tài khoản hay không."""
    try:
        return C.quen_mat_khau_gui_ma(db, data.loai, data.lien_he, data.kenh, ip)
    except C.LoiCong as ex:
        _loi(ex)


class QuenDatLaiIn(BaseModel):
    khoa: str
    ma: str
    mat_khau: str


@router.post("/quen-mat-khau/dat-lai")
def quen_mat_khau_dat_lai(data: QuenDatLaiIn, ip: str = Depends(cong_cua_mo),
                          db: Session = Depends(get_db)):
    """Đặt lại xong: đăng xuất mọi nơi và quên mọi máy đã nhớ."""
    try:
        return C.quen_mat_khau_dat_lai(db, data.khoa, data.ma, data.mat_khau)
    except C.LoiCong as ex:
        _loi(ex)


@router.get("/may")
def may_cua_toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    """Người dùng tự xem danh sách máy đã nhớ."""
    return {"dong": C.may_cua_toi(db, tk), "nho_ngay": C.NHO_MAY_NGAY,
            "toi_da": C.NHO_MAY_TOI_DA}


@router.post("/may/{may_id}/go")
def go_may(may_id: int, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai),
           db: Session = Depends(get_db)):
    """Và tự gỡ được từng máy — không phải gọi tổng đài."""
    try:
        C.go_may(db, tk, may_id)
    except C.LoiCong as ex:
        _loi(ex)
    return {"message": "Đã gỡ máy này. Lần sau vào từ máy ấy phải xác minh lại."}
