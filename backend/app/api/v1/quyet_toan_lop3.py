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

from app.api.deps import require_roles, toan_quyen
from app.db.session import get_db
from app.models.core import Booking, Tour, User
from app.models.lop3_tour import (BookingKhach, DeNghiLanhSu, DeNghiLanhSuDong,
                                  KhachChiPhi, SuaSauKy, TourBenBan,
                                  TourBenBanDong, TourDoanhThuDong,
                                  TourHdvChi, TourPhuongTien, TourTlCongNo, TourVeKhach,
                                  TourVeMa, TourVeThanhToan,
                                  LOAI_PHUONG_TIEN, LOAI_TUOI, NHOM_KHACH, LOAI_DOANH_THU,
                                  LOAI_CONG_NO_TL, LOAI_VE, TRANG_THAI_MA,
                                  LOAI_DONG_BEN_BAN, CACH_CHIA)
from app.services import ben_ban_tour as BBT
from app.services import cong_no_truong_doan as TLCN
from app.services import dat_ma_kho_cu as DMK
from app.services import de_nghi_lanh_su as DNLS
from app.services import dich_vu_le_thang as DVL
from app.services import dong_so_kho_cu as DSK
from app.services import ghi_mot_lan as GML
from app.services import go_lo_kho_cu as GLK
from app.services import khop_nguoi_ban as KNB
from app.services import phieu_dat_kho_cu as PDK
from app.services import rules as R
from app.services import gia_khach as G
from app.services import khoan_muc_chi as KM
from app.services import pham_vi_phap_nhan as PV
from app.services import soat_du_chi as SDC
from app.services import thu_ho_chi_ho as THC
from app.services import thue_gtgt_chuyen as THUE
from app.services import tip_tour as TIP
from app.services import ve_may_bay as VMB

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
    if u.role not in SUA_SAU_KY and not toan_quyen(u):
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
            "nhap_duoc": u.role in NHAP or toan_quyen(u),
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
    # Đ-7: chỉ có nghĩa với dòng loại `thu_ho`. Rỗng chủ tiền = chưa xác định, và bộ soát CHẶN.
    chu_tien: str | None = None
    han_xu_ly: date | None = None
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
                         chu_tien=v.chu_tien, han_xu_ly=v.han_xu_ly,
                         ghi_chu=v.ghi_chu)
    db.add(d); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_doanh_thu_dong", d.id, "(thêm dòng)", None, v.noi_dung,
                    v.ly_do_sua)
    db.commit()
    return {"id": d.id, "thanh_tien_truoc_thue": truoc, "tien_thue": thue, "thanh_tien": tong}


@router.get("/{tid}/doanh-thu")
def ds_doanh_thu(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Danh sách dòng doanh thu KÈM tổng do máy cộng. Không ô nào cho người gõ tổng.

    Đ-7 (13/9/2026): dòng loại `thu_ho` KHÔNG vào tổng doanh thu. Nó là tiền của khách đi ngang qua
    – cộng vào là thổi doanh thu lên bằng tiền của người khác. Nó vẫn hiện trong danh sách và vẫn có
    tổng riêng, để không ai tưởng nó biến mất.
    """
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourDoanhThuDong).where(TourDoanhThuDong.tour_id == tid)))
    co = [d for d in ds if d.thanh_tien is not None and THC.la_doanh_thu(d.loai)]
    ho = [d for d in ds if d.thanh_tien is not None and not THC.la_doanh_thu(d.loai)]
    return {
        "so_dong": len(ds),
        "so_dong_chua_co_so": len([d for d in ds if d.thanh_tien is None]),
        "tong_truoc_thue": round(sum(d.thanh_tien_truoc_thue or 0 for d in co), 2) if co else None,
        "tong_thue": round(sum(d.tien_thue or 0 for d in co), 2) if co else None,
        "tong_thu": round(sum(d.thanh_tien for d in co), 2) if co else None,
        # Tách hẳn, có nhãn riêng: người đọc phải thấy nó tồn tại mà không lẫn vào doanh thu.
        "tong_thu_ho": round(sum(d.thanh_tien for d in ho), 2) if ho else None,
        "dong": [{"id": d.id, "loai": d.loai, "noi_dung": d.noi_dung, "doi_tuong": d.doi_tuong,
                  "don_gia_truoc_thue": d.don_gia_truoc_thue, "so_luong": d.so_luong,
                  "thanh_tien_truoc_thue": d.thanh_tien_truoc_thue, "thue_suat": d.thue_suat,
                  "tien_thue": d.tien_thue, "thanh_tien": d.thanh_tien, "chung_tu": d.chung_tu,
                  "la_doanh_thu": THC.la_doanh_thu(d.loai),
                  "chu_tien": d.chu_tien, "han_xu_ly": d.han_xu_ly,
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


# ---------------------------------------------------------------------------------------------
# TIỀN TIP — Đ-6, Chủ tịch chốt 12/9/2026
# ---------------------------------------------------------------------------------------------
#
#   "tiền tip tour châu Âu chia 1 phần với công ty"
#   "tỷ lệ chia tiền tip em cài phép toán và form sẵn cho điều hành tự nhập % vào ô đó"
#
# Hai đường: XEM TRƯỚC (không ghi gì) và GHI (tạo một dòng doanh thu loại tip_cong_ty).
#
# Tách hai đường vì phép chia này có một cái bẫy đắt: cùng một khoản 810 € viết được bằng hai đơn vị
# (27 €/khách/chuyến hoặc 3 €/khách/ngày × 9 ngày), và gõ nhầm ô là sai GẤP CHÍN LẦN. Người nhập phải
# nhìn thấy con số trước khi nó thành một dòng doanh thu.


class TipVao(BaseModel):
    don_gia: float | None = None
    don_vi: str | None = None            # moi_khach_moi_ngay / moi_khach_ca_chuyen
    so_khach: int | None = None
    so_ngay: int | None = None
    ty_gia: float | None = None
    tien_te: str | None = None
    ty_le_phan_tram: str | None = None   # ô % Điều hành gõ; rỗng thì lùi về tham số đã ký
    ghi_chu: str | None = None
    ly_do_sua: str = ""


def _tip(db: Session, t: Tour, v: TipVao) -> dict:
    return TIP.tinh(db, don_gia=v.don_gia, don_vi=v.don_vi, so_khach=v.so_khach,
                    so_ngay=v.so_ngay, ty_gia=v.ty_gia, ty_le_chuyen=v.ty_le_phan_tram,
                    hom_nay=t.start_date)


@router.get("/tip/don-vi")
def tip_don_vi():
    """Hai đơn vị của đơn giá tip. Ô này BẮT BUỘC – không khai thì phép tính dừng."""
    return {"don_vi": TIP.DON_VI_TIP}


@router.post("/{tid}/tip/xem-truoc")
def tip_xem_truoc(tid: int, v: TipVao, u: User = Depends(require_roles(*XEM)),
                  db: Session = Depends(get_db)):
    """Tính thử, KHÔNG ghi gì. Người nhập nhìn số rồi mới bấm ghi."""
    t = _tour(db, tid, u)
    return _tip(db, t, v)


@router.post("/{tid}/tip")
def ghi_tip(tid: int, v: TipVao, u: User = Depends(require_roles(*NHAP)),
            db: Session = Depends(get_db)):
    """Ghi PHẦN CÔNG TY thành một dòng doanh thu loại tip_cong_ty.

    Phần của trưởng đoàn KHÔNG ghi ở đây – nó là khoản phải trả cho trưởng đoàn và đi vào bản chốt
    công nợ TL. Ghi cả cục vào doanh thu là thổi doanh thu lên bằng tiền của người khác.
    """
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    kq = _tip(db, t, v)
    if kq["chua_chia"]:
        raise HTTPException(422, kq["vi_sao"])

    ghi_chu = (f"Tip {kq['tong']:,.0f} đ – công ty {kq['ty_le_phan_tram']:g}%, "
               f"trưởng đoàn {kq['truong_doan']:,.0f} đ"
               + (f". {v.ghi_chu}" if v.ghi_chu else ""))
    d = TourDoanhThuDong(tour_id=tid, loai="tip_cong_ty",
                         noi_dung="Phần tiền tip thuộc công ty",
                         so_luong=1, don_gia_truoc_thue=kq["cong_ty"],
                         thanh_tien_truoc_thue=kq["cong_ty"], thanh_tien=kq["cong_ty"],
                         tien_te=v.tien_te, ty_gia=v.ty_gia, ghi_chu=ghi_chu)
    db.add(d); db.flush()
    # Tỷ lệ chia tiền giữa công ty và người lao động PHẢI vào sổ dấu vết, kể cả khi tờ chưa ký:
    # sáu tháng sau phải trả lời được "vì sao đoàn này công ty lấy 40% còn đoàn kia lấy 70%".
    ghi_dau_vet(db, t, u, "tour_doanh_thu_dong", d.id, "ty_le_tip_cong_ty",
                None, f"{kq['ty_le_phan_tram']:g}% ({kq['nguon_ty_le']})",
                v.ly_do_sua or "Điều hành nhập tỷ lệ chia tiền tip")
    db.commit()
    return {"id": d.id, **kq}


# ---------------------------------------------------------------------------------------------
# Đ-10 · DỰ CHI ↔ THỰC CHI, cả hai chiều
# ---------------------------------------------------------------------------------------------

@router.get("/{tid}/soat-du-chi")
def soat_du_chi(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """So dự chi với thực chi trên TỪNG DÒNG.

    Vượt quá ngưỡng mà không giải trình thì CHẶN; thấp hơn quá ngưỡng thì CẢNH BÁO, không chặn —
    chặn một chuyến vì nó tiết kiệm được tiền là cách nhanh nhất để người ta thôi ghi dự toán.
    """
    t = _tour(db, tid, u)
    return SDC.soat_dong(db, tid, t.end_date)


# ---------------------------------------------------------------------------------------------
# Đ-7 · THU HỘ – CHI HỘ
# ---------------------------------------------------------------------------------------------

@router.get("/{tid}/thu-ho")
def xem_thu_ho(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Số dư giữ hộ của chuyến, tách theo CHỦ TIỀN.

    Số dư khác 0 là bình thường (thu hôm nay, trả ngày mai). Chỉ CHẶN khi một khoản thu hộ không
    biết của ai — không có chủ thì không trả lại được cho ai.
    """
    _tour(db, tid, u)
    return THC.soat(db, tid)


# ---------------------------------------------------------------------------------------------
# Đ-11 · CHỨNG TỪ GẮN VÀO TỪNG DÒNG CHI
# ---------------------------------------------------------------------------------------------
#
# KHÔNG dựng kho tệp thứ hai. Đường này chỉ nói cho màn hình biết PHẢI GỌI kho tệp chung với đối
# tượng nào — `dong_chi_phi` + id của dòng. Cửa tải và cửa đọc là /api/v1/tep đã có sẵn, kèm toàn bộ
# phần đã làm ở đó: vân tay chống trùng, thu hồi có lý do, phân quyền theo nhóm hồ sơ.
#
# Dựng thêm một cửa tải riêng cho dòng chi là có hai kho tệp, và lần sửa quy tắc lưu trữ đầu tiên sẽ
# sửa ở một kho rồi quên kho kia.

@router.get("/{tid}/chung-tu-dong-chi")
def chung_tu_dong_chi(tid: int, u: User = Depends(require_roles(*XEM)),
                      db: Session = Depends(get_db)):
    """Mỗi dòng chi cần bao nhiêu chứng từ, và đang có bao nhiêu.

    CẢNH BÁO chứ không chặn khi dòng có số hoá đơn mà chưa có tệp: lúc nhập liệu chưa chắc đã có bản
    scan, và chặn ở đó là chặn cả luồng làm việc.
    """
    from app.models.attachments import Attachment
    from app.models.vietrip import TourCostLine
    _tour(db, tid, u)
    ds = list(db.scalars(select(TourCostLine)
                         .where(TourCostLine.tour_id == tid, TourCostLine.status == "hd")
                         .order_by(TourCostLine.line_no, TourCostLine.id)))
    ids = [str(x.id) for x in ds]
    dem: dict[str, int] = {}
    if ids:
        q = select(Attachment.doi_tuong_id, func.count(Attachment.id)).where(
            Attachment.doi_tuong == "dong_chi_phi", Attachment.doi_tuong_id.in_(ids),
            Attachment.thu_hoi == False).group_by(Attachment.doi_tuong_id)   # noqa: E712
        dem = {k: int(v) for k, v in db.execute(q).all()}

    dong, thieu = [], []
    for x in ds:
        so_tep = dem.get(str(x.id), 0)
        # doc_data là cửa CŨ, một tệp một dòng. Còn dữ liệu ở đó thì vẫn tính là có chứng từ, nhưng
        # nói rõ nó là bản cũ để người dùng biết chuyển sang kho tệp chung.
        cu = bool(x.doc_name)
        d = {"dong_id": x.id, "line_no": x.line_no, "mo_ta": x.description,
             "so_hoa_don": x.so_hoa_don, "thuc_chi": x.actual,
             "so_tep": so_tep, "co_tep_ban_cu": cu,
             "doi_tuong": "dong_chi_phi", "doi_tuong_id": str(x.id)}
        dong.append(d)
        if x.so_hoa_don and not so_tep and not cu:
            thieu.append(d)
    return {"tour_id": tid, "so_dong": len(ds), "dong": dong,
            "thieu_chung_tu": thieu, "so_thieu": len(thieu),
            "muc": "canh_bao",
            "ghi_chu": ("Dòng có số hoá đơn mà chưa gắn tệp thì CẢNH BÁO, không chặn – lúc nhập "
                        "liệu chưa chắc đã có bản scan. Tải tệp qua /api/v1/tep với đối tượng "
                        "«dong_chi_phi» và mã là id của dòng; một dòng gắn được NHIỀU tệp.")}


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-8 (13/9/2026) · CỬA NHẬP KHỐI VÉ MÁY BAY
# ═════════════════════════════════════════════════════════════════════════════════════════════════
#
# Ba bảng, ba cửa, và KHÔNG cửa nào nhận một ô tổng:
#   · mã đặt chỗ      – khối chỗ giữ ở hãng, mang hạn xuất vé
#   · dòng vé từng khách – SỐ CHỐT; thành tiền do máy cộng bốn ô tiền
#   · đợt thanh toán   – chỉ trừ dần vào nợ đại lý, không phải bản sao của tổng tiền vé

class VeMaVao(BaseModel):
    ma_dat_cho: str
    hang_bay: str | None = None
    hanh_trinh: str | None = None
    so_cho_giu: int | None = None
    han_xuat_ve: date | None = None
    trang_thai: str | None = None
    nha_cung_cap: str | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


class VeKhachVao(BaseModel):
    ve_ma_id: int | None = None
    khach_id: int | None = None
    ho_ten_ve: str | None = None
    loai: str | None = None
    gia_ve: float | None = None
    gia_ve_noi_dia: float | None = None
    phi_khac: float | None = None
    phi_nang_hang: float | None = None
    tien_te: str | None = None
    ty_gia: float | None = None
    so_hoa_don: str | None = None
    ly_do: str | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


class VeThanhToanVao(BaseModel):
    ve_ma_id: int | None = None
    ngay: date | None = None
    so_tien: float | None = None
    tien_te: str | None = None
    ty_gia: float | None = None
    hinh_thuc: str | None = None
    so_chung_tu: str | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


@router.get("/ve/loai")
def ve_loai(u: User = Depends(require_roles(*XEM))):
    """Danh mục loại dòng vé và trạng thái mã – để biểu nhập không tự bịa danh sách của riêng nó."""
    return {"loai_dong": LOAI_VE, "trang_thai_ma": TRANG_THAI_MA}


@router.post("/{tid}/ve/ma")
def them_ve_ma(tid: int, v: VeMaVao, u: User = Depends(require_roles(*NHAP)),
               db: Session = Depends(get_db)):
    """Thêm một mã đặt chỗ. Không có ô tiền nào ở đây – tiền nằm ở dòng khách."""
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    if not (v.ma_dat_cho or "").strip():
        raise HTTPException(422, "Mã đặt chỗ không được để trống.")
    if v.trang_thai and v.trang_thai not in TRANG_THAI_MA:
        raise HTTPException(422, f"trang_thai phải thuộc {sorted(TRANG_THAI_MA)}")
    m = TourVeMa(tour_id=tid, ma_dat_cho=v.ma_dat_cho.strip(), hang_bay=v.hang_bay,
                 hanh_trinh=v.hanh_trinh, so_cho_giu=v.so_cho_giu, han_xuat_ve=v.han_xuat_ve,
                 trang_thai=v.trang_thai or "giu_cho", nha_cung_cap=v.nha_cung_cap,
                 ghi_chu=v.ghi_chu, nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(m); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_ve_ma", m.id, "(thêm mã)", None, v.ma_dat_cho, v.ly_do_sua)
    db.commit()
    return {"id": m.id, "ma_dat_cho": m.ma_dat_cho}


@router.post("/{tid}/ve/khach")
def them_ve_khach(tid: int, v: VeKhachVao, u: User = Depends(require_roles(*NHAP)),
                  db: Session = Depends(get_db)):
    """Thêm một dòng vé của một khách. KHÔNG có tham số 'thành tiền' – máy cộng bốn ô tiền."""
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    loai = v.loai or "ve"
    if loai not in LOAI_VE:
        raise HTTPException(422, f"loai phải thuộc {sorted(LOAI_VE)}")
    if v.ve_ma_id is not None:
        m = db.get(TourVeMa, v.ve_ma_id)
        if not m or m.tour_id != tid:
            raise HTTPException(422, "Mã đặt chỗ không thuộc chuyến này.")
    # Chặn ngay tại cửa hai chuyện làm con số mất nghĩa. Bộ soát cũng bắt lại, nhưng chặn ở cửa thì
    # người nhập biết ngay lúc đang gõ chứ không phải lúc đi đóng số.
    if loai == "hoan_ve" and not (v.ly_do or "").strip():
        raise HTTPException(422, "Dòng hoàn vé phải ghi LÝ DO hoàn.")
    d = TourVeKhach(tour_id=tid, ve_ma_id=v.ve_ma_id, khach_id=v.khach_id, ho_ten_ve=v.ho_ten_ve,
                    loai=loai, gia_ve=v.gia_ve, gia_ve_noi_dia=v.gia_ve_noi_dia,
                    phi_khac=v.phi_khac, phi_nang_hang=v.phi_nang_hang,
                    tien_te=v.tien_te, ty_gia=v.ty_gia, so_hoa_don=v.so_hoa_don,
                    ly_do=v.ly_do, ghi_chu=v.ghi_chu,
                    nguoi_nhap=u.username, nhap_luc=datetime.now())
    d.thanh_tien = VMB.thanh_tien_dong(d)
    db.add(d); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_ve_khach", d.id, "(thêm dòng vé)", None, v.ho_ten_ve,
                    v.ly_do_sua)
    db.commit()
    return {"id": d.id, "thanh_tien": d.thanh_tien}


@router.post("/{tid}/ve/thanh-toan")
def them_ve_thanh_toan(tid: int, v: VeThanhToanVao, u: User = Depends(require_roles(*NHAP)),
                       db: Session = Depends(get_db)):
    """Ghi một đợt thanh toán cho đại lý vé. Nó TRỪ DẦN vào nợ, không phải bản sao của tổng vé."""
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    x = TourVeThanhToan(tour_id=tid, ve_ma_id=v.ve_ma_id, ngay=v.ngay, so_tien=v.so_tien,
                        tien_te=v.tien_te, ty_gia=v.ty_gia, hinh_thuc=v.hinh_thuc,
                        so_chung_tu=v.so_chung_tu, ghi_chu=v.ghi_chu,
                        nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(x); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_ve_thanh_toan", x.id, "(thêm đợt trả)", None,
                    str(v.so_tien), v.ly_do_sua)
    db.commit()
    return {"id": x.id}


@router.get("/{tid}/ve")
def ds_ve(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Toàn bộ khối vé: dòng khách, khối theo mã do MÁY CỘNG, và số dư với đại lý."""
    _tour(db, tid, u)
    return VMB.soat(db, tid)


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-9 (13/9/2026) · CỬA NHẬP CÔNG NỢ TRƯỞNG ĐOÀN
# ═════════════════════════════════════════════════════════════════════════════════════════════════

class TlCongNoVao(BaseModel):
    phan_cong_id: int | None = None
    ten_truong_doan: str | None = None
    stt: int | None = None
    noi_dung: str | None = None
    loai: str
    so_tien: float | None = None
    tien_te: str | None = None
    ty_gia: float | None = None
    ngay_ty_gia: date | None = None
    hdv_chi_id: int | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


@router.get("/tl-cong-no/loai")
def tl_loai(u: User = Depends(require_roles(*XEM))):
    """Danh mục loại khoản KÈM CHIỀU DẤU của từng loại, và câu quy ước để biểu in ngay cạnh ô số."""
    return {
        "quy_uoc_dau": TLCN.CAU_QUY_UOC,
        "loai": [{"ma": k, "chieu": v[0], "ten": v[1],
                  "dau_dung": ("dương – công ty trả trưởng đoàn" if v[0] > 0
                               else "âm – trưởng đoàn nộp lại")}
                 for k, v in LOAI_CONG_NO_TL.items()],
    }


@router.post("/{tid}/tl-cong-no")
def them_tl_cong_no(tid: int, v: TlCongNoVao, u: User = Depends(require_roles(*NHAP)),
                    db: Session = Depends(get_db)):
    """Thêm một dòng công nợ trưởng đoàn.

    Cửa này CHẶN NGAY khi dấu mâu thuẫn với loại khoản, chứ không để dồn tới lúc đóng số. Đó là lỗi
    duy nhất ở đây có thể làm cả tờ ra kết quả ngược chiều mà mọi tổng vẫn cân – và nó xảy ra đúng
    lúc người ta đang chép tờ châu Âu, vốn ghi ngược quy ước của chính nó.
    """
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    chieu = TLCN.chieu_cua_loai(v.loai)
    if chieu is None:
        raise HTTPException(422, f"loai phải thuộc {sorted(LOAI_CONG_NO_TL)}")
    if v.so_tien is not None and v.so_tien != 0 and (v.so_tien > 0) != (chieu > 0):
        dung = "DƯƠNG" if chieu > 0 else "ÂM"
        raise HTTPException(422, f"«{LOAI_CONG_NO_TL[v.loai][1]}» phải mang dấu {dung}. "
                                 f"{TLCN.CAU_QUY_UOC}")
    d = TourTlCongNo(tour_id=tid, phan_cong_id=v.phan_cong_id,
                     ten_truong_doan=v.ten_truong_doan, stt=v.stt, noi_dung=v.noi_dung,
                     loai=v.loai, so_tien=v.so_tien, tien_te=v.tien_te, ty_gia=v.ty_gia,
                     ngay_ty_gia=v.ngay_ty_gia, hdv_chi_id=v.hdv_chi_id, ghi_chu=v.ghi_chu,
                     nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(d); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_tl_cong_no", d.id, "(thêm dòng)", None, v.noi_dung, v.ly_do_sua)
    db.commit()
    return {"id": d.id}


@router.get("/{tid}/tl-cong-no")
def ds_tl_cong_no(tid: int, phan_cong_id: int | None = None,
                  u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Số dư công nợ trưởng đoàn: theo TỪNG đồng tiền, rồi mới gộp về VND."""
    _tour(db, tid, u)
    return TLCN.soat(db, tid, phan_cong_id)


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-4 · Đ-6b (13/9/2026) · CỬA NHẬP NHIỀU BÊN BÁN, VÀ HOÀN TIP VỀ BÊN BÁN
# ═════════════════════════════════════════════════════════════════════════════════════════════════

class BenBanVao(BaseModel):
    ten_ben: str
    la_vietourist: bool = False
    mst: str | None = None
    so_khach_nguoi_lon: int | None = None
    so_khach_tre_em: int | None = None
    so_khach_em_be: int | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


class BenBanDongVao(BaseModel):
    ben_ban_id: int
    stt: int | None = None
    noi_dung: str | None = None
    loai: str | None = None
    cach_chia: str | None = None
    don_gia: float | None = None
    so_luong: float | None = None
    ngay: date | None = None
    so_chung_tu: str | None = None
    ghi_chu: str | None = None
    ly_do_sua: str = ""


class HoanTipVao(BaseModel):
    don_gia: float | None = None
    don_vi: str | None = None
    so_ngay: int | None = None
    ty_gia: float | None = None


@router.get("/ben-ban/danh-muc")
def ben_ban_danh_muc(u: User = Depends(require_roles(*XEM))):
    """Loại dòng và cách chia – để biểu nhập không tự bịa danh sách của riêng nó."""
    return {"loai_dong": LOAI_DONG_BEN_BAN, "cach_chia": CACH_CHIA}


@router.post("/{tid}/ben-ban")
def them_ben_ban(tid: int, v: BenBanVao, u: User = Depends(require_roles(*NHAP)),
                 db: Session = Depends(get_db)):
    """Thêm một bên bán. Vietourist cũng là MỘT dòng ở đây, không phải phần còn lại."""
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    if not (v.ten_ben or "").strip():
        raise HTTPException(422, "Tên bên bán không được để trống.")
    b = TourBenBan(tour_id=tid, ten_ben=v.ten_ben.strip(),
                   la_vietourist=1 if v.la_vietourist else 0, mst=v.mst,
                   so_khach_nguoi_lon=v.so_khach_nguoi_lon, so_khach_tre_em=v.so_khach_tre_em,
                   so_khach_em_be=v.so_khach_em_be, ghi_chu=v.ghi_chu,
                   nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(b); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_ben_ban", b.id, "(thêm bên bán)", None, v.ten_ben, v.ly_do_sua)
    db.commit()
    return {"id": b.id, "ten_ben": b.ten_ben}


@router.post("/{tid}/ben-ban/dong")
def them_ben_ban_dong(tid: int, v: BenBanDongVao, u: User = Depends(require_roles(*NHAP)),
                      db: Session = Depends(get_db)):
    """Thêm một dòng vào tờ của một bên bán. KHÔNG có tham số 'thành tiền' – máy nhân.

    Cũng KHÔNG có tham số 'số lượng mặc định': số lượng của dòng cố ý tách khỏi số khách của bên,
    vì trên tệp thật dòng VISA của một bên 3 khách ghi 4 suất. Xem services/ben_ban_tour.py.
    """
    t = _tour(db, tid, u)
    _kiem_sua_sau_ky(db, t, u, v.ly_do_sua)
    b = db.get(TourBenBan, v.ben_ban_id)
    if not b or b.tour_id != tid:
        raise HTTPException(422, "Bên bán không thuộc chuyến này.")
    loai = v.loai or "phan_bo"
    if loai not in LOAI_DONG_BEN_BAN:
        raise HTTPException(422, f"loai phải thuộc {sorted(LOAI_DONG_BEN_BAN)}")
    if v.cach_chia and v.cach_chia not in CACH_CHIA:
        raise HTTPException(422, f"cach_chia phải thuộc {sorted(CACH_CHIA)}")
    tt = BBT.thanh_tien_dong(v.don_gia, v.so_luong)
    if loai in ("hoan_tip", "giam_tru") and tt is not None and tt > 0:
        raise HTTPException(422, f"«{LOAI_DONG_BEN_BAN[loai]}» phải mang dấu ÂM – khoản giảm trừ "
                                 "mang dấu dương thì nợ của bên bán phồng lên thay vì giảm đi.")
    d = TourBenBanDong(tour_id=tid, ben_ban_id=v.ben_ban_id, stt=v.stt, noi_dung=v.noi_dung,
                       loai=loai, cach_chia=v.cach_chia, don_gia=v.don_gia, so_luong=v.so_luong,
                       thanh_tien=tt, ngay=v.ngay, so_chung_tu=v.so_chung_tu, ghi_chu=v.ghi_chu,
                       nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(d); db.flush()
    if _da_ky(t):
        ghi_dau_vet(db, t, u, "tour_ben_ban_dong", d.id, "(thêm dòng)", None, v.noi_dung,
                    v.ly_do_sua)
    db.commit()
    return {"id": d.id, "thanh_tien": tt}


@router.get("/{tid}/ben-ban")
def ds_ben_ban(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Tờ quyết toán của TỪNG bên bán, và số dư của từng bên."""
    _tour(db, tid, u)
    return BBT.soat(db, tid)


@router.post("/{tid}/ben-ban/hoan-tip/xem-truoc")
def xem_truoc_hoan_tip(tid: int, v: HoanTipVao, u: User = Depends(require_roles(*XEM)),
                       db: Session = Depends(get_db)):
    """Tính THỬ tiền tip hoàn về từng bên bán. KHÔNG ghi gì – nhìn số rồi mới bấm ghi."""
    _tour(db, tid, u)
    return BBT.xem_truoc_hoan_tip(db, tid, don_gia=v.don_gia, don_vi=v.don_vi,
                                  so_ngay=v.so_ngay, ty_gia=v.ty_gia)


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-12 (13/9/2026) · CỬA NHẬP ĐỀ NGHỊ CHI PHÍ LÃNH SỰ
# ═════════════════════════════════════════════════════════════════════════════════════════════════

class DeNghiVao(BaseModel):
    ma: str | None = None
    tour_id: int | None = None
    thi_truong: str | None = None
    ngay: date | None = None
    don_vi_thu: str | None = None
    mst_don_vi_thu: str | None = None
    ghi_chu: str | None = None


class DeNghiDongVao(BaseModel):
    stt: int | None = None
    ho_ten: str | None = None
    gioi_tinh: str | None = None
    ngay_sinh: date | None = None
    sale: str | None = None
    ben_ban_id: int | None = None
    khach_id: int | None = None
    phi_tls_cao_cap: float | None = None
    phi_tls_co_ban: float | None = None
    phi_lsq: float | None = None
    mst: str | None = None
    ghi_chu: str | None = None


@router.post("/lanh-su")
def tao_de_nghi_lanh_su(v: DeNghiVao, u: User = Depends(require_roles(*NHAP)),
                        db: Session = Depends(get_db)):
    """Mở một tờ đề nghị chi phí lãnh sự.

    `tour_id` để RỖNG là hợp lệ: visa lẻ không thuộc chuyến nào. Ép phải có tour là chặn đúng mảng
    visa lẻ, vốn là nơi những tờ này xuất hiện nhiều nhất.
    """
    if v.tour_id is not None:
        _tour(db, v.tour_id, u)
    t = DeNghiLanhSu(ma=v.ma, tour_id=v.tour_id, thi_truong=v.thi_truong, ngay=v.ngay,
                     don_vi_thu=v.don_vi_thu, mst_don_vi_thu=v.mst_don_vi_thu,
                     ghi_chu=v.ghi_chu, nguoi_nhap=u.username, nhap_luc=datetime.now())
    db.add(t); db.commit()
    return {"id": t.id, "ma": t.ma}


@router.post("/lanh-su/{did}/dong")
def them_de_nghi_dong(did: int, v: DeNghiDongVao, u: User = Depends(require_roles(*NHAP)),
                      db: Session = Depends(get_db)):
    """Thêm một khách vào tờ đề nghị. KHÔNG có tham số 'thành tiền' – máy cộng ba ô phí."""
    t = db.get(DeNghiLanhSu, did)
    if t is None:
        raise HTTPException(404, "Không có tờ đề nghị này")
    if t.tour_id is not None:
        _tour(db, t.tour_id, u)
    d = DeNghiLanhSuDong(de_nghi_id=did, stt=v.stt, ho_ten=v.ho_ten, gioi_tinh=v.gioi_tinh,
                         ngay_sinh=v.ngay_sinh, sale=v.sale, ben_ban_id=v.ben_ban_id,
                         khach_id=v.khach_id, phi_tls_cao_cap=v.phi_tls_cao_cap,
                         phi_tls_co_ban=v.phi_tls_co_ban, phi_lsq=v.phi_lsq,
                         mst=v.mst, ghi_chu=v.ghi_chu)
    d.thanh_tien = DNLS.thanh_tien_dong(d)
    db.add(d); db.flush(); db.commit()
    return {"id": d.id, "thanh_tien": d.thanh_tien}


@router.get("/lanh-su/{did}")
def xem_de_nghi_lanh_su(did: int, u: User = Depends(require_roles(*XEM)),
                        db: Session = Depends(get_db)):
    """Tờ đề nghị KÈM phép soát – trong đó có phép bắt MỘT NGƯỜI ĐỨNG HAI LẦN."""
    t = db.get(DeNghiLanhSu, did)
    if t is None:
        raise HTTPException(404, "Không có tờ đề nghị này")
    if t.tour_id is not None:
        _tour(db, t.tour_id, u)
    return DNLS.soat(db, did)


@router.get("/{tid}/lanh-su")
def ds_de_nghi_theo_tour(tid: int, u: User = Depends(require_roles(*XEM)),
                         db: Session = Depends(get_db)):
    """Các tờ đề nghị lãnh sự của một chuyến."""
    _tour(db, tid, u)
    ds = list(db.scalars(select(DeNghiLanhSu).where(DeNghiLanhSu.tour_id == tid)
                         .order_by(DeNghiLanhSu.ngay, DeNghiLanhSu.id)))
    return {"tour_id": tid, "so_to": len(ds),
            "to": [DNLS.soat(db, x.id) for x in ds]}


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-5 (13/9/2026) · DỊCH VỤ LẺ THEO THÁNG — MỘT CÁCH NHÌN, KHÔNG PHẢI MỘT SỔ MỚI
# ═════════════════════════════════════════════════════════════════════════════════════════════════
#
# Không có cửa GHI nào ở đây, và đó là chủ ý: dữ liệu đã vào hệ thống qua /non-package (booking) và
# qua màn hình quyết toán của chính chuyến KLE (dòng chi phí). Thêm một cửa ghi thứ hai cho cùng
# một con số là mở đường cho hai con số. Xem services/dich_vu_le_thang.py.

@router.get("/dich-vu-le/{nam}/{thang}")
def xem_dich_vu_le_thang(nam: int, thang: int, mang: str | None = None,
                         u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Tờ dịch vụ lẻ của một tháng, dựng đúng hình tệp Excel của Điều hành — kèm phép soát."""
    if not (1 <= thang <= 12):
        raise HTTPException(422, "Tháng phải từ 1 đến 12.")
    return DVL.soat(db, nam, thang, mang)


# ═════════════════════════════════════════════════════════════════════════════════════════════════
# KHO QUYẾT TOÁN CŨ T1–T6/2026 (13/9/2026) · GỠ CẢ LÔ — đường đi ngược của hai cửa nạp
# ═════════════════════════════════════════════════════════════════════════════════════════════════
#
# Chủ tịch giao nạp thử tháng 1 trước. Nhưng nạp thử mà không gỡ lại được thì không phải "thử": nó
# là một chiều, và người ta hoặc không dám bấm, hoặc bấm rồi phải dọn tay mấy trăm dòng.
#
# Hai cửa NẠP nằm ở màn hình /tep (khung ba cửa chung: tải → soát → ghi). Nút GỠ đặt ở đây, trong
# phân hệ quyết toán tour, vì đó là nơi người ta nhìn thấy hậu quả của việc nạp.
#
# QUYỀN: đúng bằng cửa tạo chuyến. Hẹp hơn thì có người tạo được mà không gỡ được — và một nút tạo
# không có nút gỡ tương ứng là nút không ai dám bấm.
GO_LO = ("chutich", "tgd", "cntt", "tp_dh")


@router.get("/kho-cu/xem-go")
def xem_go_lo_kho_cu(u: User = Depends(require_roles(*GO_LO)), db: Session = Depends(get_db)):
    """XEM TRƯỚC – không xoá gì. Nói ra đúng thứ nút gỡ sẽ làm."""
    return GLK.xem(db)


class GoLoVao(BaseModel):
    xac_nhan: bool = False


@router.post("/kho-cu/go")
def go_lo_kho_cu(v: GoLoVao, u: User = Depends(require_roles(*GO_LO)),
                 db: Session = Depends(get_db)):
    """GỠ THẬT. `xac_nhan` mặc định False nên gọi nhầm KHÔNG xoá gì.

    Ghi nhật ký kiểm toán TRƯỚC khi commit, và ghi cả con số đã gỡ — để câu "ai gỡ lô kho cũ, lúc
    nào, mất bao nhiêu dòng" là câu tra được chứ không phải câu phải nhớ.
    """
    kq = GLK.go(db, boi=u.username, xac_nhan=v.xac_nhan)
    if v.xac_nhan:
        R.audit(db, u.username, u.role, "go_lo_kho_cu_h1_2026", f"nguon:{GLK.NGUON}",
                after={"da_go_dong": kq["da_go_dong"], "da_xoa_chuyen": kq["da_xoa_chuyen"],
                       "giu_lai": len(kq.get("giu_lai_khi_go") or [])})
        db.commit()
    return kq


# =================================================================================================
# GÁN NGƯỜI BÁN cho kho quyết toán cũ — màn hình cho người giải nốt phần máy không giải được
#
# Đo 13/9/2026 trên 604 tệp: 145 tên trong cột SALES, máy khớp chắc chắn được phần lớn, còn lại là
# hai loại chỉ người mới giải: tên ứng với nhiều người, và tên không có trong danh sách nhân sự
# (phần lớn là người đã nghỉ trong nửa đầu năm).
#
# QUYỀN: rộng hơn cửa gỡ đúng một vai — HCNS. Họ giữ danh sách nhân sự và biết ai đã nghỉ, mà đó
# đúng là câu hỏi phải trả lời ở màn hình này. Nhưng KHÔNG có nv_kd: để chính người bán tự nhận
# doanh số về mình là mở một cửa không nên mở.
GAN_NB = GO_LO + ("hcns",)


@router.get("/kho-cu/nguoi-ban")
def bang_gan_nguoi_ban(u: User = Depends(require_roles(*GAN_NB)), db: Session = Depends(get_db)):
    """Bảng cho màn hình gán: ai đã khớp, ai còn chờ, mỗi cái tên đáng bao nhiêu dòng khách."""
    return KNB.bang(db)


class GanNguoiBanVao(BaseModel):
    khoa_ten: str
    # None nghĩa là "để trống CÓ CHỦ Ý" — người đã nhìn và kết luận đây không phải nhân viên nào
    # (đại lý ngoài, ghi chú lọt vào ô). Lần nạp sau phải tôn trọng, không tự khớp lại.
    user_id: int | None = None


@router.post("/kho-cu/nguoi-ban/gan")
def gan_nguoi_ban(v: GanNguoiBanVao, u: User = Depends(require_roles(*GAN_NB)),
                  db: Session = Depends(get_db)):
    """Gán một cái tên cho một tài khoản. Vào nhật ký mang tên người gán: đây là việc dịch doanh số
    sang tên người thật, nên phải tra được ai đã quyết."""
    try:
        kq = KNB.gan_tay(db, v.khoa_ten, v.user_id, boi=u.username)
    except ValueError as e:
        raise HTTPException(400, str(e))
    R.audit(db, u.username, u.role, "gan_nguoi_ban_kho_cu", f"ten:{v.khoa_ten}",
            after={"user_id": v.user_id, "so_dong": kq["so_dong"]})
    db.commit()
    return kq


class GanLaiVao(BaseModel):
    xac_nhan: bool = False


@router.get("/kho-cu/gan-lai")
def xem_gan_lai_phieu(u: User = Depends(require_roles(*GAN_NB)), db: Session = Depends(get_db)):
    """XEM TRƯỚC: gán tên xong thì bao nhiêu phiếu đặt chuyển về được đúng người, bao nhiêu tiền."""
    return PDK.gan_lai(db, boi=u.username, xac_nhan=False)


@router.post("/kho-cu/gan-lai")
def gan_lai_phieu(v: GanLaiVao, u: User = Depends(require_roles(*GAN_NB)),
                  db: Session = Depends(get_db)):
    """Chuyển phiếu đặt 'chưa gán' về đúng người bán. KHÔNG nạp lại lô — chỉ đổi chủ phiếu."""
    kq = PDK.gan_lai(db, boi=u.username, xac_nhan=v.xac_nhan)
    if v.xac_nhan:
        R.audit(db, u.username, u.role, "gan_lai_phieu_kho_cu", f"nguon:{GLK.NGUON}",
                after={"da_doi": kq["da_doi"], "tien": kq.get("tien_ve_nguoi_that")})
        db.commit()
    return kq


# =================================================================================================
# ĐÓNG SỐ BÙ cho kho quyết toán cũ — Chủ tịch ký thay các phòng ban (chốt 17/9/2026)
#
#   "Vì đây là nhập dữ liệu cũ lên hệ thống nên em để Chủ tịch ký thay toàn bộ các phòng ban luôn.
#    Khi nào vào vận hành chính thức thì phòng nào ký phòng đó, đúng vai trò thiết lập."
#
# Cửa nạp kho cũ ghi dòng khách và dòng chi nhưng CỐ Ý không đóng số — nên màn hình Chủ tịch rỗng
# T1–T5 trong khi ≈36 tỷ đã nằm trong hệ. Cửa này gỡ đúng chỗ tắc ấy, cho đúng một lô.
#
# QUYỀN KÝ: chỉ `chutich`. HẸP HƠN mọi cửa kho cũ khác ở trên, và đó là chủ ý — ba cửa kia sắp xếp
# lại dữ liệu, cửa này GHI TIỀN VÀO BÁO CÁO KẾT QUẢ KINH DOANH thay cho chữ ký của Điều hành và Kế
# toán. Lời chốt ở trên nêu đích danh một người; mở rộng ra "tgd, cntt, tp_dh" cho tiện là tự ý nới
# một chữ ký, và CNTT thì không có việc gì phải ký một con số lãi lỗ.
KY_DONG_BU = ("chutich",)

# Cửa XEM mở rộng hơn cửa ký: Điều hành và Kế toán phải soi được lô này trước và sau khi Chủ tịch
# ký — họ là người sẽ phải sống với con số — nhưng không ai trong số họ bấm được nút.
XEM_DONG_BU = KY_DONG_BU + ("tgd", "tp_dh", "ketoan", "cntt")


@router.get("/kho-cu/dong-so-bu/xem")
def xem_dong_so_bu(moi_lo: int | None = None, bo_qua: int = 0,
                   u: User = Depends(require_roles(*XEM_DONG_BU)), db: Session = Depends(get_db)):
    """XEM TRƯỚC – không ghi một dòng nào.

    Trả về đủ ba thứ người ký cần biết TRƯỚC khi ký: đóng bao nhiêu chuyến, tiền rơi vào THÁNG NÀO
    (`theo_ky`), và những chuyến không đóng được thì vì sao (`vi_sao_khong_dong`).

    Xem theo LÔ như cửa ghi: `moi_lo` chuyến mỗi lần, `bo_qua` là con trỏ lấy từ `bo_qua_tiep` của
    lần gọi trước. Bỏ trống cả hai thì xem lô đầu.
    """
    return DSK.xem(db, gioi_han=moi_lo if moi_lo is not None else DSK.MOI_LO, bo_qua=bo_qua)


class DongSoBuVao(BaseModel):
    xac_nhan: bool = False
    # Số chuyến xử trong MỘT lần gọi. Bỏ trống thì lấy mặc định của bộ dịch vụ (50).
    #
    # Vì sao cửa này làm theo lô, đo 19/9/2026 trên hệ thật: gọi một lần cho cả 476 chuyến thì
    # cổng cắt giữa chừng và trả về một trang HTML — trình duyệt chỉ thấy "Unexpected token '<'".
    # Giao dịch bị huỷ trọn nên dữ liệu không hỏng, nhưng nút thì không bao giờ bấm xong.
    #
    # Nay MỖI LẦN GỌI LÀ MỘT GIAO DỊCH: xử một lô, ghi nhật ký, chốt, trả về `con_lai`. Người bấm
    # gọi tiếp cho tới khi `con_lai` = 0. Dừng giữa chừng thì phần đã làm vẫn sạch.
    moi_lo: int | None = None
    # CON TRỎ. Lấy từ `bo_qua_tiep` của lần gọi trước và truyền lại y nguyên.
    #
    # Không có nó thì vòng lặp có thể KẸT: chuyến không đóng được (và ở cửa gỡ là chuyến Điều hành
    # đã đóng THẬT — đo 17/9/2026 có 82 chuyến, nhiều hơn một lô) vẫn khớp điều kiện lấy lô và luôn
    # đứng đầu hàng, nên lô sau lấy đúng chúng, làm được 0 chuyến, `con_lai` không giảm.
    bo_qua: int = 0


@router.post("/kho-cu/dong-so-bu")
def chay_dong_so_bu(v: DongSoBuVao, u: User = Depends(require_roles(*KY_DONG_BU)),
                    db: Session = Depends(get_db)):
    """ĐÓNG SỐ THẬT. `xac_nhan` mặc định False nên gọi nhầm KHÔNG ghi gì.

    Nhật ký ghi TRƯỚC khi commit, và ghi cả số tiền theo từng kỳ — vì câu sẽ phải trả lời sau này
    không phải "ai bấm nút" mà là "ai đã ký cho 36 tỷ rơi vào những tháng nào".
    """
    kq = DSK.chay(db, boi=u.username, xac_nhan=v.xac_nhan,
                  gioi_han=v.moi_lo if v.moi_lo is not None else DSK.MOI_LO, bo_qua=v.bo_qua)
    if v.xac_nhan:
        R.audit(db, u.username, u.role, "dong_so_bu_kho_cu_h1_2026", f"nguon:{DSK.NGUON}",
                after={"da_dong": kq["da_dong"],
                       "tong_doanh_thu": kq.get("tong_doanh_thu"),
                       "tong_gia_von": kq.get("tong_gia_von"),
                       "theo_ky": kq.get("theo_ky_da_dong"),
                       # Ghi cả vị trí lô vào nhật ký: 476 chuyến đóng làm mươi lần bấm, nhật ký
                       # phải ráp lại được thành một việc chứ không phải mươi việc rời.
                       "moi_lo": kq.get("moi_lo"), "bo_qua": kq.get("bo_qua"),
                       "con_lai": kq.get("con_lai"),
                       "khong_dong_duoc": kq.get("khong_dong_duoc"),
                       "ky_thay": "toàn bộ các phòng ban – Chủ tịch chốt 17/9/2026"})
        db.commit()
    return kq


@router.post("/kho-cu/dong-so-bu/go")
def go_dong_so_bu(v: DongSoBuVao, u: User = Depends(require_roles(*KY_DONG_BU)),
                  db: Session = Depends(get_db)):
    """GỠ lại phần CHÍNH CỬA NÀY đã đóng. Không đụng chuyến Điều hành đã đóng số thật.

    Cùng quyền với cửa ký: không được phép gỡ một chữ ký mà mình không đủ quyền đặt xuống.
    """
    kq = DSK.go(db, boi=u.username, xac_nhan=v.xac_nhan,
                gioi_han=v.moi_lo if v.moi_lo is not None else DSK.MOI_LO, bo_qua=v.bo_qua)
    if v.xac_nhan:
        R.audit(db, u.username, u.role, "go_dong_so_bu_kho_cu", f"nguon:{DSK.NGUON}",
                after={"da_go": kq["da_go"], "con_lai": kq.get("con_lai"),
                       "moi_lo": kq.get("moi_lo"), "bo_qua": kq.get("bo_qua"),
                       "giu_lai_do_dong_that": kq.get("giu_lai_do_dong_that")})
        db.commit()
    return kq


# =================================================================================================
# Đ-2c · HAI Ô THUẾ SUẤT TRÊN CHUYẾN — Chủ tịch chốt 14/9/2026
#
#   "Thuế GTGT tour châu Âu là tour nước ngoài nên tính 0%, nhưng em cứ viết cấu trúc và thuật
#    toán, còn tỷ lệ % để cho Điều hành nhập vào."
#
# Nên 0% không phải một con số trong mã, và 8% cũng vậy. Cả hai là ô trên chuyến, rỗng thì lùi về
# tham số công ty đã ký. Máy không bao giờ tự điền vào ô — điền sẵn thì sáu tháng sau không ai phân
# biệt được "Điều hành đã cân nhắc và chọn" với "máy để mặc định và không ai nhìn".

class ThueSuatVao(BaseModel):
    # ĐƠN VỊ LÀ PHẦN TRĂM: gõ 8 nghĩa là 8%. None = xoá ô, lùi về tham số công ty.
    thue_suat_ra_pt: float | None = None
    thue_suat_ngoai_vn_pt: float | None = None
    ly_do: str | None = None


@router.get("/{tid}/thue-suat")
def xem_thue_suat(tid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Hai ô trên chuyến, và MỨC ĐANG THẬT SỰ ÁP DỤNG kèm chỗ nó đến từ đâu.

    Trả cả `dang_ap_dung` chứ không chỉ hai ô: ô rỗng nghĩa là "dùng tham số công ty", và người nhập
    phải nhìn thấy con số ấy là bao nhiêu. Bày ô rỗng không kèm mức hiện hành là bắt người ta đoán.
    """
    t = _tour(db, tid, u)
    hom_nay = getattr(t, "start_date", None)
    return {
        "thue_suat_ra_pt": t.thue_suat_ra_pt,
        "thue_suat_ngoai_vn_pt": t.thue_suat_ngoai_vn_pt,
        "dang_ap_dung": {
            "thue_suat_ra": THUE.thue_suat_ra(db, hom_nay, t.thue_suat_ra_pt),
            "thue_suat_ngoai_vn": THUE.thue_suat_ngoai_vn(db, hom_nay, t.thue_suat_ngoai_vn_pt),
            "nguon_ra": ("go_tren_chuyen" if TIP.doc_phan_tram(t.thue_suat_ra_pt) is not None
                         else "tham_so_cong_ty"),
            "nguon_ngoai_vn": ("go_tren_chuyen"
                               if TIP.doc_phan_tram(t.thue_suat_ngoai_vn_pt) is not None
                               else "tham_so_cong_ty"),
        },
        "hinh_thuc": t.hinh_thuc,
        "nhap_duoc": u.role in NHAP or toan_quyen(u),
    }


@router.put("/{tid}/thue-suat")
def dat_thue_suat(tid: int, v: ThueSuatVao, u: User = Depends(require_roles(*NHAP)),
                  db: Session = Depends(get_db)):
    """Khai thuế suất RIÊNG cho chuyến này. Rỗng thì chuyến dùng tham số công ty.

    Khoảng hợp lệ là [0, 100] vì ô là phần trăm. Ngoài khoảng ấy thì TỪ CHỐI chứ không kẹp: kẹp một
    con số người ta gõ nhầm về biên là ghi vào sổ một con số không ai chọn.
    """
    t = _tour(db, tid, u)
    for ten, x in (("thue_suat_ra_pt", v.thue_suat_ra_pt),
                   ("thue_suat_ngoai_vn_pt", v.thue_suat_ngoai_vn_pt)):
        if x is not None and not (0 <= x <= 100):
            raise HTTPException(422, f"{ten} là PHẦN TRĂM, phải nằm trong khoảng 0–100 (gõ 8 = 8%)")
    cu = {"thue_suat_ra_pt": t.thue_suat_ra_pt,
          "thue_suat_ngoai_vn_pt": t.thue_suat_ngoai_vn_pt}
    t.thue_suat_ra_pt = v.thue_suat_ra_pt
    t.thue_suat_ngoai_vn_pt = v.thue_suat_ngoai_vn_pt
    moi = {"thue_suat_ra_pt": v.thue_suat_ra_pt, "thue_suat_ngoai_vn_pt": v.thue_suat_ngoai_vn_pt}
    # Thuế suất là con số quyết định tiền thuế của cả chuyến, nên MỌI lần đổi vào sổ dấu vết — kể cả
    # lần đổi đầu tiên. Sáu tháng sau phải trả lời được "vì sao chuyến này khai 0% còn chuyến kia 8%".
    R.audit(db, u.username, u.role, "dat_thue_suat_chuyen", f"tour:{t.code}",
            before=cu, after={**moi, "ly_do": (v.ly_do or "")[:200]})
    db.commit()
    return {**moi, "canh_bao": [c for c in (
        TIP.canh_bao_phan_tram(v.thue_suat_ra_pt),
        TIP.canh_bao_phan_tram(v.thue_suat_ngoai_vn_pt)) if c]}


# =================================================================================================
# ĐẶT MÃ TOUR cho tệp quyết toán cũ không khai mã — Chủ tịch chốt 18/9/2026
#
#   "(EU220726 = Châu Âu khởi hành 22/07/2026) = em đặt theo cách này"
#
# Đo 18/9/2026: trong 91 bản ghi quyết toán chưa ghép được với chuyến nào, 19 tệp KHÔNG khai mã
# tour — 29,85 tỷ đồng, chiếm 82% phần chưa ghép. Không có mã thì không tạo được chuyến, và cũng
# không đối chiếu được xem đã có trên VTOS hay chưa.
#
# Cửa tạo chuyến đã đặt sẵn mã tạm KHOCU-… và bày ra ở bảng xem trước, nhưng KHÔNG NHẬN LẠI GÌ —
# tức là có chỗ đọc mà không có chỗ ghi. Đó là việc còn thiếu, không phải việc để máy tự quyết.
#
# QUYỀN: hẹp bằng đúng cửa tạo chuyến (`tao_chuyen_kho_cu`: QUẢN TRỊ + tp_dh). Đặt mã là đặt TÊN
# cho một chuyến trong lịch sử vận hành của công ty; Kế toán không có việc gì phải làm ở đây.
DAT_MA = ("chutich", "tgd", "cntt", "tp_dh")


class DatMaDong(BaseModel):
    ten_tep: str
    ma_tour: str


class DatMaVao(BaseModel):
    cap: list[DatMaDong]
    xac_nhan: bool = False
    ke_ca_phai_hoi: bool = False


@router.post("/kho-cu/dat-ma/xem")
def xem_dat_ma_kho_cu(v: DatMaVao, u: User = Depends(require_roles(*DAT_MA)),
                      db: Session = Depends(get_db)):
    """SOÁT, KHÔNG GHI. Trả về từng dòng kèm mọi chỗ có thể sai."""
    return DMK.soat(db, [x.model_dump() for x in v.cap])


@router.post("/kho-cu/dat-ma")
def dat_ma_kho_cu(v: DatMaVao, u: User = Depends(require_roles(*DAT_MA)),
                  db: Session = Depends(get_db)):
    """GHI mã người đặt. `xac_nhan` mặc định False nên gọi nhầm KHÔNG ghi gì.

    KHÔNG tạo chuyến. Tạo chuyến vẫn là cửa 'Tạo CHUYẾN còn thiếu', một lần bấm riêng — vì tạo
    chuyến là ghi lại lịch sử vận hành, còn cửa này chỉ đặt tên cho tệp.
    """
    kq = DMK.dat(db, [x.model_dump() for x in v.cap], boi=u.username,
                 xac_nhan=v.xac_nhan, ke_ca_phai_hoi=v.ke_ca_phai_hoi)
    if v.xac_nhan:
        R.audit(db, u.username, u.role, "dat_ma_tour_kho_cu", "nguon:kho_cu_h1_2026",
                after={"da_ghi": kq["da_ghi"],
                       "ma": [{"tep": h["ten_tep"], "ma": h["ma_tour"]}
                              for h in kq["hang"] if not h["chan"]][:50]})
        db.commit()
    return kq
