"""Cửa nhập của lớp 3 quyết toán tour: dòng khách, doanh thu, phương tiện, chi phí khách, HDV chi.

Theo ranh giới công việc 09/9/2026: mỗi con số hệ thống cần phải có MỘT CỬA cho người dùng đưa vào.
Năm bảng của lớp 3 sinh ra ở bản nâng cấp x1c7d2e9f4a86 nhưng chưa có cửa nào – tệp này là cửa ấy.

Bảng thứ sáu, sua_sau_ky, CỐ Ý không có cửa nhập: nó là sổ dấu vết, hệ thống tự ghi khi người bấm sửa
một tờ đã ký. Một sổ dấu vết mà gõ thẳng vào được thì không còn là dấu vết.

BA NGUYÊN TẮC CỦA MỌI CỬA Ở ĐÂY

1. MÁY CHỦ CỘNG, NGƯỜI KHÔNG GÕ TỔNG. Không cửa nào nhận một ô "tổng". Thành tiền của dòng doanh thu
   do máy nhân từ đơn giá × số lượng rồi cộng thuế; tổng của chuyến do máy cộng từ các dòng. Đo trên
   tệp mẫu Nha Trang: ô tổng nhóm B ghi 3.990.000 trong khi năm dòng của chính nhóm ấy cộng lại được
   4.200.000 – thiếu 210.000 đ, và con số sai ấy đi thẳng vào lợi nhuận mà mọi tầng vẫn cân.

2. RỖNG KHÁC KHÔNG. Cột tiền để trống nghĩa là CHƯA AI NHẬP, và cửa giữ nguyên như thế. Quy ước K2.

3. SỬA TỜ ĐÃ KÝ THÌ PHẢI ĐỂ LẠI DẤU VẾT. Chủ tịch chốt 10/9/2026: chỉ tp_dh và ptgd_doan, bắt buộc
   nêu lý do. Cửa sửa ở đây gọi ghi_dau_vet() trước khi đổi số, và từ chối lý do dưới 10 ký tự.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import Booking, Tour, User
from app.models.lop3_tour import (BookingKhach, KhachChiPhi, SuaSauKy, TourDoanhThuDong,
                                  TourHdvChi, TourPhuongTien,
                                  LOAI_PHUONG_TIEN, LOAI_TUOI, NHOM_KHACH, LOAI_DOANH_THU)
from app.services import ghi_mot_lan as GML
from app.services import gia_khach as G
from app.services import khoan_muc_chi as KM
from app.services import pham_vi_phap_nhan as PV

router = APIRouter(prefix="/api/v1/quyet-toan-lop3", tags=["quyet-toan-lop3"])

# Ai được XEM. Cùng danh sách với màn hình lãi lỗ: đây là số giá vốn của chuyến.
XEM = ("chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt")
# Ai được NHẬP. Điều hành là người lập tờ quyết toán; Kế toán sửa phần chứng từ.
NHAP = ("tp_dh", "nv_dh", "ketoan", "cntt")
# Ai được SỬA TỜ ĐÃ KÝ – Chủ tịch chốt 10/9/2026, đúng hai vai trò, không nới.
SUA_SAU_KY = ("tp_dh", "ptgd_doan")

DAI_NHAT_LY_DO = 10     # lý do ngắn hơn thì từ chối: "sửa" không phải một lý do


# ---------------------------------------------------------------------------------------------
# Dùng chung
# ---------------------------------------------------------------------------------------------

def _tour(db: Session, tid: int, u: User) -> Tour:
    """Lấy chuyến và CHẶN nếu nó thuộc pháp nhân khác."""
    t = db.get(Tour, tid)
    if not t:
        raise HTTPException(404, "Không có tour")
    cid = PV.pham_vi(u)
    # Hồ sơ CHƯA GẮN pháp nhân vẫn cho xem – bỏ qua chúng là giấu luôn phần cần đi gán nhất.
    if cid is not None and t.company_id is not None and t.company_id != cid:
        raise HTTPException(403, "Tour thuộc pháp nhân khác – ngoài phạm vi của tài khoản")
    return t


def _da_ky(t: Tour) -> bool:
    """Tờ đã ký chưa. Đã đóng số hoặc kế toán đã xác nhận thì coi là đã ký."""
    return bool(t.closed_at or t.kt_confirmed_at)


def ghi_dau_vet(db: Session, t: Tour, u: User, bang: str, ban_ghi_id: int | None,
                truong: str, cu, moi, ly_do: str) -> None:
    """Ghi một dòng vào sổ dấu vết. Gọi TRƯỚC khi đổi số, để còn đọc được giá trị cũ.

    Không commit – người gọi commit cùng với thay đổi, để dấu vết và thay đổi vào sổ cùng lúc hoặc
    cùng không. Ghi dấu vết xong mà thay đổi hỏng là sổ có dòng ma; ngược lại là thay đổi không dấu.
    """
    db.add(SuaSauKy(tour_id=t.id, bang=bang, ban_ghi_id=ban_ghi_id, truong=truong,
                    gia_tri_cu=None if cu is None else str(cu),
                    gia_tri_moi=None if moi is None else str(moi),
                    ly_do=ly_do, nguoi_sua=u.username, vai_tro=u.role, sua_luc=datetime.now()))


def _kiem_sua_sau_ky(db: Session, t: Tour, u: User, ly_do: str) -> None:
    """Tờ chưa ký thì sửa tự do. Đã ký thì chỉ hai vai trò, và bắt buộc lý do."""
    if not _da_ky(t):
        return
    if u.role not in SUA_SAU_KY:
        raise HTTPException(
            403, "Tờ quyết toán đã ký. Chỉ Trưởng phòng Điều hành và Phó TGĐ đoàn sửa được.")
    if len((ly_do or "").strip()) < DAI_NHAT_LY_DO:
        raise HTTPException(
            422, f"Sửa tờ đã ký thì phải nêu lý do, ít nhất {DAI_NHAT_LY_DO} ký tự.")


def _thanh_tien(don_gia: float | None, so_luong: float | None,
                thue_suat: float | None) -> tuple[float | None, float | None, float | None]:
    """(trước thuế, tiền thuế, thành tiền). Rỗng vào thì rỗng ra – KHÔNG suy thành 0.

    Đây là chỗ thực thi nguyên tắc 1: người nhập đơn giá và số lượng, máy nhân. Cửa không có tham số
    nào cho "thành tiền".
    """
    if don_gia is None or so_luong is None:
        return None, None, None
    truoc = round(don_gia * so_luong, 2)
    if thue_suat is None:
        return truoc, None, truoc
    thue = round(truoc * thue_suat, 2)
    return truoc, thue, round(truoc + thue, 2)


# ---------------------------------------------------------------------------------------------
# Danh mục – để màn hình dựng ô chọn, không gõ chuỗi tự do
# ---------------------------------------------------------------------------------------------

@router.get("/danh-muc")
def danh_muc(hinh_thuc: str = "", u: User = Depends(require_roles(*XEM))):
    """Mọi danh mục để màn hình dựng ô CHỌN – không còn ô chữ tự do cho tên khoản mục.

    Truyền hinh_thuc để lọc: người làm tour nội địa không phải cuộn qua phí lãnh sự quán.
    """
    return {"nhom_khach": NHOM_KHACH, "loai_tuoi": LOAI_TUOI,
            "loai_phuong_tien": LOAI_PHUONG_TIEN, "loai_doanh_thu": LOAI_DOANH_THU,
            "quy_tac_phan_bo": G.BANG_PHAN_BO,
            "nhom_khoan_muc": KM.NHOM,
            "khoan_muc": KM.danh_sach(hinh_thuc or None)}


@router.get("/tra-ncc")
def tra_ncc(tim: str = "", gioi_han: int = 20,
            u: User = Depends(require_roles(*NHAP)), db: Session = Depends(get_db)):
    """Tra nhà cung cấp theo tên, trả SẴN mã số thuế – tên pháp nhân – địa chỉ – số tài khoản.

    Người nhập gõ vài chữ của tên; màn hình gọi cửa này rồi điền hộ phần còn lại. Gõ tay mã số thuế
    mười chữ số cho từng dòng chi là cách chắc chắn để có những mã sai một chữ số – mà mã sai thì hoá
    đơn ấy không kê khai khấu trừ được, và chỉ phát hiện ra vào lúc quyết toán thuế.

    TÊN PHÁP NHÂN KHÁC TÊN GIAO DỊCH, và hoá đơn chỉ chấp nhận tên pháp nhân: trên danh mục thật của
    công ty, "RESORT VĨNH HY" xuất hoá đơn dưới tên "CTY TNHH PHÁT HOÀNG LONG". Cửa này trả cả hai.
    """
    from app.models.suppliers import Supplier
    q = select(Supplier).where(Supplier.active.is_(True))
    if tim.strip():
        mau = f"%{tim.strip().lower()}%"
        q = q.where(func.lower(Supplier.ten).like(mau)
                    | func.lower(Supplier.ten_phap_nhan).like(mau)
                    | Supplier.ma_so_thue.like(f"%{tim.strip()}%"))
    ds = list(db.scalars(q.order_by(Supplier.ten).limit(max(1, min(gioi_han, 100)))))
    return {"so_dong": len(ds), "dong": [
        {"supplier_id": s.id, "code": s.code, "ten": s.ten, "ten_phap_nhan": s.ten_phap_nhan,
         "ma_so_thue": s.ma_so_thue, "dia_chi": s.dia_chi, "dien_thoai": s.dien_thoai,
         "so_tai_khoan": s.so_tai_khoan, "ngan_hang": s.ngan_hang,
         # Nói thẳng chỗ thiếu ngay tại ô chọn, để người nhập biết TRƯỚC khi dùng.
         "thieu": [t for t, v in (("mã số thuế", s.ma_so_thue),
                                  ("tên pháp nhân", s.ten_phap_nhan),
                                  ("địa chỉ", s.dia_chi)) if not (v or "").strip()]}
        for s in ds]}


# ---------------------------------------------------------------------------------------------
# Dòng khách
# ---------------------------------------------------------------------------------------------

class KhachVao(BaseModel):
    booking_id: int
    stt: int | None = None
    ho_ten: str | None = None
    nhom_khach: str | None = None
    ngay_sinh: date | None = None
    gia_ban: float | None = None
    ly_do_khac_chuan: str | None = None
    so_ho_chieu: str | None = None
    ma_dat_cho: str | None = None
    ly_do_sua: str = ""
    phien_ban: int | None = None


@router.get("/{tid}/khach")
def ds_khach(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    _tour(db, tid, u)
    ds = list(db.scalars(select(BookingKhach).where(BookingKhach.tour_id == tid)
                         .order_by(BookingKhach.stt, BookingKhach.id)))
    return {"so_dong": len(ds), "dong": [
        {"id": k.id, "booking_id": k.booking_id, "stt": k.stt, "ho_ten": k.ho_ten,
         "nhom_khach": k.nhom_khach, "loai_tuoi": k.loai_tuoi, "ngay_sinh": k.ngay_sinh,
         "tuoi_luc_di": k.tuoi_luc_di, "gia_chuan": k.gia_chuan, "gia_ban": k.gia_ban,
         "lech_chuan": k.lech_chuan(), "ly_do_khac_chuan": k.ly_do_khac_chuan,
         "so_ho_chieu": k.so_ho_chieu, "ma_dat_cho": k.ma_dat_cho} for k in ds]}


def _gia_nguoi_lon(db: Session, tid: int) -> float | None:
    """Giá người lớn của chuyến, lấy từ chính các dòng khách người lớn đang có.

    KHÔNG lấy từ tours.price_per_pax: ở tour nước ngoài mỗi khách một giá (tệp UK có tám mức giá
    người lớn khác nhau trên một chuyến), nên một con số trên bảng tours không đại diện được. Lấy
    mức PHỔ BIẾN NHẤT trong các dòng người lớn thật – nếu chưa có dòng nào thì trả None và giá chuẩn
    để rỗng, đúng quy ước rỗng-khác-không.
    """
    gia = [float(k.gia_ban) for k in db.scalars(
        select(BookingKhach).where(BookingKhach.tour_id == tid,
                                   BookingKhach.loai_tuoi == "nguoi_lon",
                                   BookingKhach.nhom_khach == "tra_tien"))
        if k.gia_ban]
    if not gia:
        return None
    return max(set(gia), key=gia.count)


@router.post("/{tid}/khach")
def them_khach(tid: int, v: KhachVao, u: User = Depends(require_roles(*NHAP)),
               db: Session = Depends(get_db)):
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    if v.nhom_khach and v.nhom_khach not in NHOM_KHACH:
        raise HTTPException(422, f"nhom_khach phải thuộc {sorted(NHOM_KHACH)}")
    b = db.get(Booking, v.booking_id)
    if not b or b.tour_id != tid:
        raise HTTPException(422, "booking không thuộc chuyến này")

    k = BookingKhach(booking_id=b.id, tour_id=tid, stt=v.stt, ho_ten=v.ho_ten,
                     nhom_khach=v.nhom_khach, ngay_sinh=v.ngay_sinh, gia_ban=v.gia_ban,
                     ly_do_khac_chuan=v.ly_do_khac_chuan, so_ho_chieu=v.so_ho_chieu,
                     ma_dat_cho=v.ma_dat_cho, nguoi_sua=u.username, sua_luc=datetime.now())
    db.add(k)
    G.xac_dinh_khach(db, k, t.start_date, _gia_nguoi_lon(db, tid), t.hinh_thuc)
    if _da_ky(t):
        db.flush()
        ghi_dau_vet(db, t, u, "booking_khach", k.id, "(thêm dòng)", None, k.ho_ten, v.ly_do_sua)
    db.commit(); db.refresh(k)
    return {"id": k.id, "loai_tuoi": k.loai_tuoi, "tuoi_luc_di": k.tuoi_luc_di,
            "gia_chuan": k.gia_chuan, "lech_chuan": k.lech_chuan()}


@router.put("/{tid}/khach/{kid}")
def sua_khach(tid: int, kid: int, v: KhachVao, u: User = Depends(require_roles(*NHAP)),
              db: Session = Depends(get_db)):
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    k = db.get(BookingKhach, kid)
    if not k or k.tour_id != tid:
        raise HTTPException(404, "Không có dòng khách này trong chuyến")
    # VPM-8 – khoá ghi một lần. Bảng mang cột phien_ban từ lúc sinh ra nhưng cửa này chưa đọc nó, nên
    # hai người cùng mở một dòng khách thì người lưu sau ghi đè lặng lẽ lên người lưu trước. Dòng
    # khách mang GIÁ BÁN, nên ghi đè lặng là mất tiền chứ không chỉ mất công gõ lại.
    GML.kiem_phien_ban(k, getattr(v, "phien_ban", None), f"Dòng khách {k.ho_ten or kid}",
                       lambda: {"id": k.id, "stt": k.stt, "ho_ten": k.ho_ten, "gia_ban": k.gia_ban})

    for truong, moi in (("ho_ten", v.ho_ten), ("nhom_khach", v.nhom_khach),
                        ("ngay_sinh", v.ngay_sinh), ("gia_ban", v.gia_ban),
                        ("ly_do_khac_chuan", v.ly_do_khac_chuan),
                        ("so_ho_chieu", v.so_ho_chieu), ("ma_dat_cho", v.ma_dat_cho)):
        cu = getattr(k, truong)
        if moi is not None and moi != cu:
            if _da_ky(t):
                ghi_dau_vet(db, t, u, "booking_khach", k.id, truong, cu, moi, v.ly_do_sua)
            setattr(k, truong, moi)
    k.nguoi_sua, k.sua_luc = u.username, datetime.now()
    G.xac_dinh_khach(db, k, t.start_date, _gia_nguoi_lon(db, tid), t.hinh_thuc)
    GML.tang_phien_ban(k)
    db.commit(); db.refresh(k)
    return {"id": k.id, "loai_tuoi": k.loai_tuoi, "gia_chuan": k.gia_chuan,
            "lech_chuan": k.lech_chuan()}


@router.get("/{tid}/soat-gia")
def soat_gia(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Soát giá bán từng khách so với quy tắc. KHÔNG sửa số nào – chỉ làm cho chênh lệch lộ ra.

    Trả kèm HÌNH THỨC của chuyến, vì biểu nhập tay cần biết nó đang dựng mẫu trong nước hay nước
    ngoài: hai hình thức khác nhau ở cột ngoại tệ, ở mục chi theo từng khách, và ở tỷ lệ giá trẻ em
    (trong nước 80%, nước ngoài 90%). Trả ở đây thay vì bắt màn hình gọi thêm một cửa nữa, và cũng
    thay vì sửa cửa /tours/{id}/detail của luồng khác.
    """
    t = _tour(db, tid, u)
    # MỘT NGUỒN SỰ THẬT VỀ QUYỀN NHẬP.
    #
    # Màn hình KHÔNG được tự suy quyền từ trạng thái chuyến: hàng rào thật là danh sách NHAP ngay
    # trong tệp này, và nó rộng hơn quyền sửa chuyến (Kế toán sửa được phần chứng từ mà không sửa
    # được chuyến). Hai tầng suy riêng thì tầng ngoài hẹp hơn sẽ GIẤU biểu khỏi đúng những người
    # được phép nhập, và không ai hiểu vì sao.
    return {**G.soat_gia(db, tid), "hinh_thuc": t.hinh_thuc, "ma_tour": t.code,
            "nhap_duoc": u.role in NHAP,
            "goi_y_hinh_thuc": _goi_y_hinh_thuc(t), "nuoc": t.country or ""}


# ---------------------------------------------------------------------------------------------
# Hình thức của chuyến – CỬA KHAI
# ---------------------------------------------------------------------------------------------

# Tên nước viết thường, không dấu, dùng để đoán. Chỉ để GỢI Ý – không tự ghi.
_TRONG_NUOC = ("viet nam", "vietnam", "vn", "trong nuoc", "noi dia")


def _bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt để so tên nước: 'Việt Nam' và 'viet nam' phải khớp nhau."""
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").strip()


def _goi_y_hinh_thuc(t: Tour) -> str | None:
    """Đoán hình thức từ cột country – CHỈ ĐỂ GỢI Ý cho người khai, không bao giờ tự ghi.

    Vì sao không tự ghi: hình thức quyết định phép kiểm nào chạy (nước ngoài bắt buộc tỷ giá và NGÀY
    tỷ giá cho mọi khoản ngoại tệ). Suy ngầm rồi tính tiền theo cái suy ấy là chỗ sinh lỗi lặng – một
    chuyến để trống country sẽ lặng lẽ thành 'trong nước' và cả tờ đi qua mà không ai khai tỷ giá.
    Cột country của hệ thống hiện rỗng ở phần lớn chuyến, nên đoán sai là chuyện thường.
    """
    n = _bo_dau(t.country)
    if not n:
        return None
    return "trong_nuoc" if n in _TRONG_NUOC else "nuoc_ngoai"


class HinhThucVao(BaseModel):
    hinh_thuc: str
    ly_do: str | None = None


@router.put("/{tid}/hinh-thuc")
def dat_hinh_thuc(tid: int, v: HinhThucVao, u: User = Depends(require_roles(*NHAP)),
                  db: Session = Depends(get_db)):
    """Khai chuyến này quyết toán theo mẫu TRONG NƯỚC hay NƯỚC NGOÀI.

    VÌ SAO CỬA NÀY PHẢI CÓ

    Cả biểu quyết toán dựng theo hình thức: hai hình thức khác nhau ở cột ngoại tệ, ở mục chi theo
    từng khách, và ở tỷ lệ giá trẻ em. Biểu nhập tay vì thế CHẶN khi hình thức còn rỗng. Nhưng cột
    tours.hinh_thuc sinh ra ở bản nâng cấp mà KHÔNG cửa nào ghi được – không API, không màn hình.
    Kết quả: cả 5 chuyến trên máy đều rỗng, và người mở tab quyết toán chỉ gặp một lời chặn bảo đi
    khai ở chỗ không tồn tại. Theo ranh giới 09/9/2026, thiếu cửa là việc còn thiếu.

    VÌ SAO ĐỔI HÌNH THỨC KHI TỜ ĐÃ CÓ SỐ LÀ CHUYỆN LỚN

    Đổi từ nước ngoài về trong nước làm những dòng ngoại tệ đã nhập mất chỗ khai tỷ giá, mà số tiền
    quy đổi thì vẫn nằm đó – tờ vẫn cân nhưng không còn giải thích được bằng gì. Nên: tờ còn trắng
    thì đổi tự do; đã có dòng thì buộc nêu lý do và ghi vào sổ dấu vết, như mọi lần sửa tờ đã ký.
    """
    t = _tour(db, tid, u)
    if v.hinh_thuc not in ("trong_nuoc", "nuoc_ngoai"):
        raise HTTPException(422, "hinh_thuc phải là 'trong_nuoc' hoặc 'nuoc_ngoai'")
    cu = t.hinh_thuc
    if cu == v.hinh_thuc:
        return {"hinh_thuc": cu, "da_doi": False}

    from app.models.vietrip import TourCostLine
    so_dong = (
        (db.scalar(select(func.count()).select_from(BookingKhach)
                   .where(BookingKhach.tour_id == tid)) or 0)
        + (db.scalar(select(func.count()).select_from(TourDoanhThuDong)
                     .where(TourDoanhThuDong.tour_id == tid)) or 0)
        + (db.scalar(select(func.count()).select_from(TourCostLine)
                     .where(TourCostLine.tour_id == tid)) or 0))

    # Lần khai ĐẦU TIÊN trên tờ trắng: không phải "sửa", không đòi lý do.
    if cu and so_dong:
        _kiem_sua_sau_ky(db, t, u, v.ly_do or "")
        if len((v.ly_do or "").strip()) < DAI_NHAT_LY_DO:
            raise HTTPException(
                422, f"Tờ đã có {so_dong} dòng. Đổi hình thức thì phải nêu lý do, "
                     f"ít nhất {DAI_NHAT_LY_DO} ký tự.")
        ghi_dau_vet(db, t, u, "tours", t.id, "hinh_thuc", cu, v.hinh_thuc, v.ly_do or "")

    t.hinh_thuc = v.hinh_thuc
    db.commit()
    return {"hinh_thuc": t.hinh_thuc, "da_doi": True, "so_dong_dang_co": so_dong}


@router.get("/{tid}/phan-bo")
def phan_bo(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Giá vốn từng khách, kèm lời giải thích nó gồm những gì và chia theo mẫu số nào."""
    _tour(db, tid, u)
    return G.phan_bo(db, tid)


# ---------------------------------------------------------------------------------------------
# Chi phí đích danh của khách
# ---------------------------------------------------------------------------------------------

class KhachChiPhiVao(BaseModel):
    khach_id: int
    loai: str | None = None
    noi_dung: str | None = None
    so_tien: float | None = None
    tien_te: str | None = None
    so_tien_goc: float | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None
    nha_cung_cap: str | None = None
    mst_ncc: str | None = None
    so_hoa_don: str | None = None
    ly_do_sua: str = ""


def quy_doi(tien_te, so_tien_goc, ty_gia, ngay_ty_gia, so_vnd_neu_noi_te):
    """Số tiền VND của một khoản, và phép kiểm ngoại tệ đi kèm. MỘT chỗ duy nhất làm việc này.

    Khoản VND thì trả lại đúng số đã tính sẵn. Khoản ngoại tệ thì MÁY QUY ĐỔI – người không gõ số
    VND bên cạnh số gốc và tỷ giá, vì gõ tay cả ba là mở đường cho ba con số không khớp nhau.

    Chủ tịch chốt 11/9/2026: quy đổi theo tỷ giá NGÀY CHI THẬT, nên ngày tỷ giá là bắt buộc. Không
    ghi ngày thì không bao giờ phân xử được số nào đúng – tệp UK có hai tỷ giá GBP khác nhau trong
    cùng một tệp (36.000 ở sheet chiết tính và 35.944 ở sheet quyết toán), và riêng trên giá land
    692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ.

    Ba phép kiểm dưới đây phải nằm ngay trước phép nhân, không tách sang hàm khác: tách ra thì người
    đọc mã (và bộ dò K2) không thấy được phép nhân này đã chặn rỗng hay chưa.
    """
    if not tien_te or tien_te == "VND":
        return so_vnd_neu_noi_te
    if ty_gia is None or ngay_ty_gia is None:
        raise HTTPException(422, "Khoản ngoại tệ phải khai cả tỷ giá và NGÀY tỷ giá "
                                 "(tỷ giá của ngày chi thật).")
    if so_tien_goc is None:
        raise HTTPException(422, "Khoản ngoại tệ phải khai số tiền bằng đồng tiền gốc.")
    return round(float(so_tien_goc) * float(ty_gia), 2)


@router.post("/{tid}/khach-chi-phi")
def them_khach_chi_phi(tid: int, v: KhachChiPhiVao, u: User = Depends(require_roles(*NHAP)),
                       db: Session = Depends(get_db)):
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    k = db.get(BookingKhach, v.khach_id)
    if not k or k.tour_id != tid:
        raise HTTPException(422, "khách không thuộc chuyến này")
    so_tien = quy_doi(v.tien_te, v.so_tien_goc, v.ty_gia, v.ngay_ty_gia, v.so_tien)

    x = KhachChiPhi(khach_id=k.id, tour_id=tid, loai=v.loai, noi_dung=v.noi_dung, so_tien=so_tien,
                    tien_te=v.tien_te, so_tien_goc=v.so_tien_goc, ty_gia=v.ty_gia,
                    ngay_ty_gia=v.ngay_ty_gia, nha_cung_cap=v.nha_cung_cap, mst_ncc=v.mst_ncc,
                    so_hoa_don=v.so_hoa_don)
    db.add(x); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "khach_chi_phi", x.id, "(thêm dòng)", None, v.noi_dung, v.ly_do_sua)
    db.commit()
    return {"id": x.id, "so_tien": x.so_tien}


@router.get("/{tid}/khach-chi-phi")
def ds_khach_chi_phi(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    _tour(db, tid, u)
    ds = list(db.scalars(select(KhachChiPhi).where(KhachChiPhi.tour_id == tid)))
    return {"so_dong": len(ds), "dong": [
        {"id": x.id, "khach_id": x.khach_id, "loai": x.loai, "noi_dung": x.noi_dung,
         "so_tien": x.so_tien, "tien_te": x.tien_te, "so_tien_goc": x.so_tien_goc,
         "ty_gia": x.ty_gia, "ngay_ty_gia": x.ngay_ty_gia, "nha_cung_cap": x.nha_cung_cap,
         "mst_ncc": x.mst_ncc, "so_hoa_don": x.so_hoa_don} for x in ds]}


# ---------------------------------------------------------------------------------------------
# Dòng doanh thu
# ---------------------------------------------------------------------------------------------

class DoanhThuVao(BaseModel):
    booking_id: int | None = None
    khach_id: int | None = None
    loai: str | None = None
    noi_dung: str | None = None
    doi_tuong: str | None = None
    don_gia_truoc_thue: float | None = None
    so_luong: float | None = None
    thue_suat: float | None = None
    chung_tu: str | None = None
    tien_te: str | None = None
    so_tien_goc: float | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


@router.post("/{tid}/doanh-thu")
def them_doanh_thu(tid: int, v: DoanhThuVao, u: User = Depends(require_roles(*NHAP)),
                   db: Session = Depends(get_db)):
    """Thêm một dòng doanh thu. KHÔNG có tham số 'thành tiền' – máy nhân và cộng thuế."""
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    if v.loai and v.loai not in LOAI_DOANH_THU:
        raise HTTPException(422, f"loai phải thuộc {sorted(LOAI_DOANH_THU)}")
    truoc, thue, tong = _thanh_tien(v.don_gia_truoc_thue, v.so_luong, v.thue_suat)
    tong = quy_doi(v.tien_te, v.so_tien_goc, v.ty_gia, v.ngay_ty_gia, tong)
    # Dòng ÂM được phép – hoàn tiền theo biên bản thanh lý là chuyện bình thường. Nhưng phải có căn
    # cứ: không có số hiệu biên bản thì không phân biệt được với gõ nhầm dấu trừ.
    if tong is not None and tong < 0 and not (v.chung_tu or "").strip():
        raise HTTPException(
            422, "Dòng doanh thu âm (hoàn tiền / thanh lý) phải ghi số hiệu chứng từ làm căn cứ.")

    d = TourDoanhThuDong(tour_id=tid, booking_id=v.booking_id, khach_id=v.khach_id, loai=v.loai,
                         noi_dung=v.noi_dung, doi_tuong=v.doi_tuong,
                         don_gia_truoc_thue=v.don_gia_truoc_thue, so_luong=v.so_luong,
                         thanh_tien_truoc_thue=truoc, thue_suat=v.thue_suat, tien_thue=thue,
                         thanh_tien=tong, chung_tu=v.chung_tu, tien_te=v.tien_te,
                         so_tien_goc=v.so_tien_goc, ty_gia=v.ty_gia, ngay_ty_gia=v.ngay_ty_gia,
                         ghi_chu=v.ghi_chu)
    db.add(d); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_doanh_thu_dong", d.id, "(thêm dòng)", None, v.noi_dung,
                    v.ly_do_sua)
    db.commit()
    return {"id": d.id, "thanh_tien_truoc_thue": truoc, "tien_thue": thue, "thanh_tien": tong}


@router.get("/{tid}/doanh-thu")
def ds_doanh_thu(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Danh sách dòng doanh thu KÈM tổng do máy cộng. Không ô nào cho người gõ tổng."""
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourDoanhThuDong).where(TourDoanhThuDong.tour_id == tid)))
    co = [d for d in ds if d.thanh_tien is not None]
    return {
        "so_dong": len(ds),
        "so_dong_chua_co_so": len(ds) - len(co),
        "tong_truoc_thue": round(sum(d.thanh_tien_truoc_thue or 0 for d in co), 2) if co else None,
        "tong_thue": round(sum(d.tien_thue or 0 for d in co), 2) if co else None,
        "tong_thu": round(sum(d.thanh_tien for d in co), 2) if co else None,
        "dong": [{"id": d.id, "loai": d.loai, "noi_dung": d.noi_dung, "doi_tuong": d.doi_tuong,
                  "don_gia_truoc_thue": d.don_gia_truoc_thue, "so_luong": d.so_luong,
                  "thanh_tien_truoc_thue": d.thanh_tien_truoc_thue, "thue_suat": d.thue_suat,
                  "tien_thue": d.tien_thue, "thanh_tien": d.thanh_tien, "chung_tu": d.chung_tu,
                  "khach_id": d.khach_id} for d in ds]}


# ---------------------------------------------------------------------------------------------
# Dòng chi phí – chọn khoản mục và nhà cung cấp, máy điền phần còn lại
# ---------------------------------------------------------------------------------------------

class ChiVao(BaseModel):
    ma_khoan_muc: str
    mo_ta: str | None = None            # chi tiết riêng của dòng, ví dụ "Ăn trưa ngày 2 – Marina Beach"
    ngay: str | None = None
    supplier_id: int | None = None
    # Bốn mặc định của khoản mục; để trống thì máy lấy từ danh mục.
    doi_tuong: str | None = None
    quy_tac_phan_bo: str | None = None
    don_gia: float | None = None
    so_luong: float | None = None
    he_so: float | None = None
    du_chi: float | None = None
    thuc_chi: float | None = None
    tien_te: str | None = None
    so_tien_goc: float | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None
    thue_suat: float | None = None
    khong_hoa_don: float | None = None
    so_hoa_don: str | None = None
    ngay_hoa_don: date | None = None
    ly_do_sua: str = ""


@router.post("/{tid}/chi")
def them_dong_chi(tid: int, v: ChiVao, u: User = Depends(require_roles(*NHAP)),
                  db: Session = Depends(get_db)):
    """Thêm một dòng chi. Người nhập CHỌN khoản mục và nhà cung cấp, rồi điền số tiền – hết.

    MÁY ĐIỀN HỘ BA THỨ

      * nhóm, đối tượng, quy tắc phân bổ  <- từ danh mục khoản mục
      * tên, tên pháp nhân, mã số thuế    <- từ hồ sơ nhà cung cấp
      * thành tiền                        <- đơn giá × số lượng × hệ số, hoặc số gốc × tỷ giá

    Không cửa nào cho gõ tay mã số thuế: mười chữ số gõ lại ở từng dòng chi là cách chắc chắn để có
    những mã sai một chữ số, và mã sai thì hoá đơn ấy không kê khai khấu trừ được.
    """
    from app.models.suppliers import Supplier
    from app.models.vietrip import TourCostLine
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)

    md = KM.mac_dinh(v.ma_khoan_muc)
    if not md:
        raise HTTPException(422, f"Mã khoản mục '{v.ma_khoan_muc}' không có trong danh mục. "
                                 f"Xem GET /api/v1/quyet-toan-lop3/danh-muc")

    ten_ncc = mst = ""
    if v.supplier_id:
        ncc = db.get(Supplier, v.supplier_id)
        if not ncc:
            raise HTTPException(422, "Không có nhà cung cấp này")
        ten_ncc, mst = ncc.ten, ncc.ma_so_thue

    # Thành tiền do MÁY nhân. Cửa không nhận tham số "thành tiền".
    thuc = v.thuc_chi
    if v.don_gia is not None and v.so_luong is not None:
        thuc = round(v.don_gia * v.so_luong * (v.he_so or 1), 2)
    thuc = quy_doi(v.tien_te, v.so_tien_goc, v.ty_gia, v.ngay_ty_gia, thuc)

    d = TourCostLine(
        tour_id=tid, ma_khoan_muc=v.ma_khoan_muc,
        # description giữ CHI TIẾT riêng của dòng; tên khoản mục lấy từ danh mục khi mô tả để trống.
        description=(v.mo_ta or KM.KHOAN_MUC[v.ma_khoan_muc]["ten"])[:200],
        ngay=v.ngay, nhom=md["nhom"],
        doi_tuong=v.doi_tuong or md["doi_tuong"],
        quy_tac_phan_bo=v.quy_tac_phan_bo or md["quy_tac_phan_bo"],
        supplier_id=v.supplier_id, supplier_name=ten_ncc, supplier_tax_code=mst,
        unit_price=v.don_gia, qty=v.so_luong or 0, coef=v.he_so or 1,
        budget=v.du_chi, actual=thuc,
        tien_te=v.tien_te, so_tien_goc=v.so_tien_goc, ty_gia=v.ty_gia, ngay_ty_gia=v.ngay_ty_gia,
        thue_suat=v.thue_suat,
        vat_hoa_don=(round(thuc * v.thue_suat, 2) if (thuc is not None and v.thue_suat is not None)
                     else None),
        khong_hoa_don=v.khong_hoa_don, so_hoa_don=v.so_hoa_don, ngay_hoa_don=v.ngay_hoa_don,
        source="vtos", status="hd", updated_by=u.username)
    db.add(d); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_cost_lines", d.id, "(thêm dòng)", None, d.description,
                    v.ly_do_sua)
    db.commit(); db.refresh(d)
    return {"id": d.id, "ma_khoan_muc": d.ma_khoan_muc, "noi_dung": d.description,
            "nhom": d.nhom, "doi_tuong": d.doi_tuong, "quy_tac_phan_bo": d.quy_tac_phan_bo,
            "nha_cung_cap": d.supplier_name, "ma_so_thue": d.supplier_tax_code,
            "du_chi": d.budget, "thuc_chi": d.actual, "tien_thue": d.vat_hoa_don,
            "la_khoan_khac": KM.la_khoan_khac(d.ma_khoan_muc)}


@router.get("/{tid}/chi")
def ds_chi(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """TỪNG DÒNG chi của chuyến – cửa đọc đi kèm cửa ghi POST /{tid}/chi.

    VÌ SAO CỬA NÀY PHẢI CÓ RIÊNG, KHÔNG DÙNG /chi-theo-khoan-muc THAY

    /chi-theo-khoan-muc trả số ĐÃ GỘP theo khoản mục và theo nhóm – nó trả lời "chuyến này chi bao
    nhiêu tiền khách sạn". Nó KHÔNG trả lời được "dòng thứ ba tôi vừa nhập đã vào chưa, đối tác ghi
    đúng chưa" – mà đó chính là câu người đang ngồi nhập cần.

    Thiếu cửa này thì biểu nhập tay hiện bảng RỖNG sau mỗi lần ghi, người nhập tưởng chưa vào nên
    gõ lại, và chuyến có hai lần giá vốn. Mỗi cửa GHI phải có một cửa ĐỌC đi kèm; thiếu là việc còn
    thiếu chứ không phải chuyện nhỏ.
    """
    from app.models.vietrip import TourCostLine
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourCostLine)
                         .where(TourCostLine.tour_id == tid, TourCostLine.status == "hd")
                         .order_by(TourCostLine.line_no, TourCostLine.id)))
    co_du = [x.budget for x in ds if x.budget is not None]
    co_thuc = [x.actual for x in ds if x.actual is not None]
    return {
        "so_dong": len(ds),
        # MÁY CỘNG TỪ DÒNG. Rỗng khác không: không dòng nào khai thì trả None, không trả 0.
        "tong_du_chi": round(sum(co_du), 2) if co_du else None,
        "tong_thuc_chi": round(sum(co_thuc), 2) if co_thuc else None,
        "dong": [{"id": x.id, "line_no": x.line_no, "ma_khoan_muc": x.ma_khoan_muc,
                  "mo_ta": x.description, "ngay": x.ngay, "nhom": x.nhom,
                  "doi_tuong": x.doi_tuong, "quy_tac_phan_bo": x.quy_tac_phan_bo,
                  "nha_cung_cap": x.supplier_name, "mst_ncc": x.supplier_tax_code,
                  "don_gia": x.unit_price, "so_luong": x.qty, "he_so": x.coef,
                  "du_chi": x.budget, "thuc_chi": x.actual,
                  "tien_te": x.tien_te, "so_tien_goc": x.so_tien_goc,
                  "ty_gia": (None if x.ty_gia is None else float(x.ty_gia)),
                  "ngay_ty_gia": x.ngay_ty_gia,
                  "thue_suat": x.thue_suat, "khong_hoa_don": x.khong_hoa_don,
                  "so_hoa_don": x.so_hoa_don, "ngay_hoa_don": x.ngay_hoa_don,
                  "hinh_thuc_tt": x.hinh_thuc_tt, "tai_khoan_the": x.tai_khoan_the,
                  "ngay_thanh_toan": x.ngay_thanh_toan, "han_thanh_toan": x.han_thanh_toan,
                  "loai_chung_tu": x.loai_chung_tu, "nguon": x.source} for x in ds]}


@router.get("/{tid}/chi-theo-khoan-muc")
def chi_theo_khoan_muc(tid: int, u: User = Depends(require_roles(*XEM)),
                       db: Session = Depends(get_db)):
    """Chi phí của chuyến CỘNG THEO KHOẢN MỤC và theo nhóm.

    Đây là thứ ô chữ tự do không bao giờ cho được. Kèm phần tiền rơi vào khoản mục "khác" – nhiều
    tiền ở đó không phải lỗi người nhập, đó là tín hiệu danh mục còn thiếu mã.
    """
    from app.models.vietrip import TourCostLine
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourCostLine).where(TourCostLine.tour_id == tid,
                                                    TourCostLine.status == "hd")))
    theo_ma: dict[str, float] = {}
    theo_nhom: dict[str, float] = {}
    chua_xep = khac = 0.0
    for d in ds:
        tien = d.actual if d.actual is not None else d.budget
        if tien is None:
            continue
        tien = float(tien)
        if not d.ma_khoan_muc:
            chua_xep += tien
            continue
        theo_ma[d.ma_khoan_muc] = theo_ma.get(d.ma_khoan_muc, 0) + tien
        theo_nhom[d.nhom or ""] = theo_nhom.get(d.nhom or "", 0) + tien
        if KM.la_khoan_khac(d.ma_khoan_muc):
            khac += tien
    return {
        "theo_khoan_muc": [{"ma": m, "ten": KM.KHOAN_MUC.get(m, {}).get("ten", m),
                            "so_tien": round(v, 2)}
                           for m, v in sorted(theo_ma.items(), key=lambda x: -x[1])],
        "theo_nhom": [{"nhom": n, "so_tien": round(v, 2)}
                      for n, v in sorted(theo_nhom.items())],
        "tong": round(sum(theo_ma.values()) + chua_xep, 2),
        "tien_khoan_khac": round(khac, 2),
        "tien_chua_xep_khoan_muc": round(chua_xep, 2),
    }


# ---------------------------------------------------------------------------------------------
# Phương tiện
# ---------------------------------------------------------------------------------------------

class PhuongTienVao(BaseModel):
    loai: str
    chang: str | None = None
    ngay: date | None = None
    gio_di: str | None = None
    gio_den: str | None = None
    so_hieu: str | None = None
    ma_dat_cho: str | None = None
    nha_cung_cap: str | None = None
    mst_ncc: str | None = None
    xe_nha: int | None = 0
    vehicle_id: int | None = None
    so_cho: int | None = None
    so_khach_su_dung: int | None = None
    don_gia: float | None = None
    so_luong: float | None = None
    tien_te: str | None = None
    so_tien_goc: float | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None
    dong_chi_phi_id: int | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


@router.post("/{tid}/phuong-tien")
def them_phuong_tien(tid: int, v: PhuongTienVao, u: User = Depends(require_roles(*NHAP)),
                     db: Session = Depends(get_db)):
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    if v.loai not in LOAI_PHUONG_TIEN:
        raise HTTPException(422, f"loai phải thuộc {sorted(LOAI_PHUONG_TIEN)}")
    tt = None
    if v.don_gia is not None and v.so_luong is not None:
        tt = round(v.don_gia * v.so_luong, 2)
    tt = quy_doi(v.tien_te, v.so_tien_goc, v.ty_gia, v.ngay_ty_gia, tt)

    x = TourPhuongTien(tour_id=tid, loai=v.loai, chang=v.chang, ngay=v.ngay, gio_di=v.gio_di,
                       gio_den=v.gio_den, so_hieu=v.so_hieu, ma_dat_cho=v.ma_dat_cho,
                       nha_cung_cap=v.nha_cung_cap, mst_ncc=v.mst_ncc, xe_nha=v.xe_nha,
                       vehicle_id=v.vehicle_id, so_cho=v.so_cho,
                       so_khach_su_dung=v.so_khach_su_dung, don_gia=v.don_gia,
                       so_luong=v.so_luong, thanh_tien=tt, tien_te=v.tien_te,
                       so_tien_goc=v.so_tien_goc, ty_gia=v.ty_gia, ngay_ty_gia=v.ngay_ty_gia,
                       dong_chi_phi_id=v.dong_chi_phi_id, ghi_chu=v.ghi_chu)
    db.add(x); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_phuong_tien", x.id, "(thêm chặng)", None, v.chang, v.ly_do_sua)
    db.commit()
    return {"id": x.id, "thanh_tien": x.thanh_tien}


@router.get("/{tid}/phuong-tien")
def ds_phuong_tien(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourPhuongTien).where(TourPhuongTien.tour_id == tid)
                         .order_by(TourPhuongTien.ngay, TourPhuongTien.id)))
    co = [x.thanh_tien for x in ds if x.thanh_tien is not None]
    return {"so_dong": len(ds),
            # MÁY CỘNG TỪ DÒNG. Rỗng khác không: chưa chặng nào khai tiền thì trả None, không trả 0
            # – bảng hiện "0 đ" cho một chuyến chưa nhập gì là nói dối người đọc.
            "tong": round(sum(co), 2) if co else None,
            # Chặng chưa nối vào dòng chi là chặng CHƯA VÀO GIÁ VỐN. Đếm ra đây chứ không để im.
            "so_chang_chua_vao_gia_von": sum(1 for x in ds if x.dong_chi_phi_id is None),
            # Trả ĐỦ những gì người nhập vừa gõ. Bản đầu bỏ sót giờ bay, mã đặt chỗ, đơn giá và số
            # lượng – người nhập gõ xong, bảng hiện lại thiếu mấy cột, và họ tưởng máy nuốt mất nên
            # gõ lại lần nữa. Cửa ĐỌC phải soi đúng cửa GHI.
            "dong": [{"id": x.id, "loai": x.loai, "chang": x.chang, "ngay": x.ngay,
                      "gio_di": x.gio_di, "gio_den": x.gio_den,
                      "so_hieu": x.so_hieu, "ma_dat_cho": x.ma_dat_cho,
                      "nha_cung_cap": x.nha_cung_cap, "mst_ncc": x.mst_ncc, "xe_nha": x.xe_nha,
                      "so_cho": x.so_cho, "so_khach_su_dung": x.so_khach_su_dung,
                      "don_gia": x.don_gia, "so_luong": x.so_luong,
                      "thanh_tien": x.thanh_tien, "tien_te": x.tien_te,
                      "dong_chi_phi_id": x.dong_chi_phi_id} for x in ds]}


# ---------------------------------------------------------------------------------------------
# HDV chi
# ---------------------------------------------------------------------------------------------

class HdvChiVao(BaseModel):
    phan_cong_id: int | None = None
    noi_dung: str | None = None
    don_gia: float | None = None
    so_luong: float | None = None
    tien_ung: float | None = None
    tien_te: str | None = None
    so_tien_goc: float | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None
    thu_ho_khach: int | None = 0
    dong_chiet_tinh_id: int | None = None
    loai_chung_tu: str | None = None
    ly_do_sua: str = ""


@router.post("/{tid}/hdv-chi")
def them_hdv_chi(tid: int, v: HdvChiVao, u: User = Depends(require_roles(*NHAP)),
                 db: Session = Depends(get_db)):
    """Ghi một khoản HDV chi trên đường, và TỰ TÍNH phần vượt chiết tính.

    Người nhập không gõ phần vượt: máy lấy dòng chiết tính tương ứng và trừ. Gõ tay phần vượt là mở
    đường cho người chi vượt tự khai mình không vượt.
    """
    from app.models.vietrip import TourCostLine
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    tt = None
    if v.don_gia is not None and v.so_luong is not None:
        tt = round(v.don_gia * v.so_luong, 2)
    tt = quy_doi(v.tien_te, v.so_tien_goc, v.ty_gia, v.ngay_ty_gia, tt)

    ct = vuot = None
    if v.dong_chiet_tinh_id:
        dong = db.get(TourCostLine, v.dong_chiet_tinh_id)
        if not dong or dong.tour_id != tid:
            raise HTTPException(422, "dòng chiết tính không thuộc chuyến này")
        ct = dong.actual if dong.actual is not None else dong.budget
        if tt is not None and ct is not None:
            vuot = round(tt - float(ct), 2)

    con_lai = None
    if v.tien_ung is not None and tt is not None:
        con_lai = round(v.tien_ung - tt, 2)

    x = TourHdvChi(tour_id=tid, phan_cong_id=v.phan_cong_id, noi_dung=v.noi_dung,
                   don_gia=v.don_gia, so_luong=v.so_luong, thanh_tien=tt, tien_ung=v.tien_ung,
                   tien_te=v.tien_te, so_tien_goc=v.so_tien_goc, ty_gia=v.ty_gia,
                   ngay_ty_gia=v.ngay_ty_gia, thu_ho_khach=v.thu_ho_khach,
                   dong_chiet_tinh_id=v.dong_chiet_tinh_id, thanh_tien_chiet_tinh=ct,
                   vuot=vuot, con_lai=con_lai, loai_chung_tu=v.loai_chung_tu,
                   nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(x); db.commit(); db.refresh(x)
    return {"id": x.id, "thanh_tien": x.thanh_tien, "thanh_tien_chiet_tinh": ct,
            "vuot": vuot, "con_lai": con_lai, "trang_thai_duyet": x.trang_thai_duyet}


class DuyetVao(BaseModel):
    duyet: bool
    ly_do: str = ""


@router.post("/{tid}/hdv-chi/{hid}/duyet")
def duyet_hdv_chi(tid: int, hid: int, v: DuyetVao,
                  u: User = Depends(require_roles("tp_dh", "ptgd_doan", "cntt")),
                  db: Session = Depends(get_db)):
    """Duyệt hoặc TỪ CHỐI phần HDV chi vượt chiết tính.

    Chủ tịch chốt 10/9/2026: vượt mà không được duyệt thì HDV bù tiền vào. Từ chối sinh ra
    phai_thu_hdv – một con số chờ, mang tên người. Phần mềm KHÔNG tự trừ lương: kế toán mới là người
    trừ, và phải có điều khoản trong quy chế hướng dẫn viên thì mới cưỡng chế được.

    Từ chối thì BẮT BUỘC nêu lý do: người bị trừ tiền có quyền biết vì sao.
    """
    _tour(db, tid, u)
    x = db.get(TourHdvChi, hid)
    if not x or x.tour_id != tid:
        raise HTTPException(404, "Không có khoản HDV chi này trong chuyến")
    if not v.duyet and len((v.ly_do or "").strip()) < DAI_NHAT_LY_DO:
        raise HTTPException(422, f"Từ chối thì phải nêu lý do, ít nhất {DAI_NHAT_LY_DO} ký tự.")

    x.trang_thai_duyet = "da_duyet" if v.duyet else "tu_choi"
    x.nguoi_duyet, x.duyet_luc, x.ly_do_duyet = u.username, datetime.now(), v.ly_do
    # Chỉ phần VƯỢT mới thành khoản phải thu, không phải toàn bộ khoản chi. Trừ cả khoản là trừ luôn
    # phần chi đúng dự toán.
    #
    # Riêng khoản KHÔNG CÓ trong chiết tính (dong_chiet_tinh_id rỗng) thì không có gì để so, nên toàn
    # bộ số tiền là phần phải duyệt – nặng hơn chi vượt, không nhẹ hơn.
    if v.duyet:
        x.phai_thu_hdv = None
    elif x.dong_chiet_tinh_id is None:
        x.phai_thu_hdv = x.thanh_tien
    else:
        vuot = x.vuot or 0
        x.phai_thu_hdv = vuot if vuot > 0 else None
    db.commit(); db.refresh(x)
    return {"id": x.id, "trang_thai_duyet": x.trang_thai_duyet, "phai_thu_hdv": x.phai_thu_hdv}


@router.get("/{tid}/hdv-chi")
def ds_hdv_chi(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Bảng chi của HDV, kèm hai phép so và số dòng còn chờ duyệt.

    Tờ quyết toán KHÔNG đóng được khi còn dòng chờ duyệt – im lặng không được tính là đồng ý.
    """
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourHdvChi).where(TourHdvChi.tour_id == tid)))
    co = [x for x in ds if x.thanh_tien is not None]
    ung = [x for x in ds if x.tien_ung is not None]
    tong_chi = round(sum(x.thanh_tien for x in co), 2) if co else None
    tong_ung = round(sum(x.tien_ung for x in ung), 2) if ung else None
    return {
        "so_dong": len(ds),
        "tong_chi": tong_chi,
        "tong_ung": tong_ung,
        # Âm nghĩa là HDV đã bỏ tiền túi ra trước và CÔNG TY nợ lại HDV – chiều ngược của quy tắc
        # chi vượt, và nó xảy ra thật (mẫu đoàn Đà Lạt: ứng 3.300.000, chi 3.696.000).
        "con_lai": (None if tong_chi is None or tong_ung is None else round(tong_ung - tong_chi, 2)),
        "tong_vuot_chiet_tinh": round(sum(x.vuot or 0 for x in ds if (x.vuot or 0) > 0), 2),
        "so_dong_cho_duyet": sum(1 for x in ds if x.trang_thai_duyet == "cho_duyet"),
        "tong_phai_thu_hdv": round(sum(x.phai_thu_hdv or 0 for x in ds), 2),
        "dong": [{"id": x.id, "noi_dung": x.noi_dung, "thanh_tien": x.thanh_tien,
                  "tien_ung": x.tien_ung, "thanh_tien_chiet_tinh": x.thanh_tien_chiet_tinh,
                  "vuot": x.vuot, "con_lai": x.con_lai, "loai_chung_tu": x.loai_chung_tu,
                  "thu_ho_khach": x.thu_ho_khach, "trang_thai_duyet": x.trang_thai_duyet,
                  "nguoi_duyet": x.nguoi_duyet, "ly_do_duyet": x.ly_do_duyet,
                  "phai_thu_hdv": x.phai_thu_hdv} for x in ds]}


# ---------------------------------------------------------------------------------------------
# Tải MẪU TRỐNG
# ---------------------------------------------------------------------------------------------

@router.get("/mau-trong")
def mau_trong(hinh_thuc: str = "trong_nuoc", u: User = Depends(require_roles(*NHAP))):
    """Tải tệp mẫu quyết toán TRỐNG, đúng hình thức của chuyến.

    VÌ SAO MẪU ĐƯỢC SINH RA TẠI ĐÂY CHỨ KHÔNG PHẢI MỘT TỆP GỬI QUA ZALO

    Sheet KHOẢN MỤC trong mẫu là bản sao danh mục của hệ thống (khoan_muc_chi.py), và ô chọn mã khoản
    mục của mọi dòng chi trỏ vào sheet ấy. Nếu mẫu là một tệp tĩnh ai đó tải về từ tháng trước, thì
    mỗi lần danh mục thêm một mã, bản cũ lại lệch thêm một bước – và người điền vẫn chọn đúng cái ô
    mà mẫu đưa cho, rồi bị bộ nạp từ chối vì "mã không có trong danh mục". Sinh tại chỗ thì mẫu và
    bộ kiểm không thể lệch: cùng một nguồn, cùng một lần chạy.

    Cửa này đòi quyền NHẬP chứ không phải quyền XEM. Mẫu trống không chứa số của ai, nhưng người tải
    mẫu là người sắp nộp tờ – và một cửa tải mở cho cả công ty thì về sau không trả lời được câu
    "tệp này ai lập".
    """
    if hinh_thuc not in ("trong_nuoc", "nuoc_ngoai"):
        raise HTTPException(422, "hinh_thuc phải là 'trong_nuoc' hoặc 'nuoc_ngoai'")
    # Nhập ở trong hàm: openpyxl chỉ cần khi có người bấm tải, không cần mỗi lần khởi động máy chủ.
    from app.services import dung_mau_quyet_toan as DM
    NN = hinh_thuc == "nuoc_ngoai"
    noi_dung = DM.dung(NN)
    ten = f"MAU_QT_TOUR_{'NUOC_NGOAI' if NN else 'TRONG_NUOC'}.xlsx"
    return Response(
        content=noi_dung,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{ten}"'})


# ---------------------------------------------------------------------------------------------
# Sổ dấu vết – CHỈ ĐỌC
# ---------------------------------------------------------------------------------------------

@router.get("/{tid}/dau-vet")
def dau_vet(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Những lần tờ này bị sửa sau khi đã ký.

    Không có cửa ghi và không có cửa xoá – kể cả Chủ tịch. Sửa sai thì sửa tiếp và ghi tiếp. Một sổ
    dấu vết mà người có quyền cao nhất xoá được thì không phải sổ dấu vết.
    """
    _tour(db, tid, u)
    ds = list(db.scalars(select(SuaSauKy).where(SuaSauKy.tour_id == tid)
                         .order_by(SuaSauKy.sua_luc.desc())))
    return {"so_lan_sua": len(ds), "dong": [
        {"id": x.id, "bang": x.bang, "ban_ghi_id": x.ban_ghi_id, "truong": x.truong,
         "gia_tri_cu": x.gia_tri_cu, "gia_tri_moi": x.gia_tri_moi, "ly_do": x.ly_do,
         "nguoi_sua": x.nguoi_sua, "vai_tro": x.vai_tro, "sua_luc": x.sua_luc} for x in ds]}
