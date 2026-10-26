"""KH-4 · Cổng khách — đánh giá chuyến đi, góp ý riêng lãnh đạo, yêu cầu hỗ trợ.

Chủ tịch duyệt bản xem thử 27/10/2026 (màn KH20, KH21, KH22, KH24, KH25 của bộ v3.2):

ĐÁNH GIÁ
  · Ghi vào ĐÚNG bảng `danh_gia_sau_tour` (nguồn «khach») mà phiếu khảo sát Zalo đang ghi — màn
    /danh-gia, hồ sơ HDV và luật mở khiếu nại khi điểm thấp đọc chung một chỗ. Không dựng bảng điểm
    thứ hai.
  · Chỉ chuyến ĐÃ ĐI (tour kết thúc, booking không hủy). Mở chấm 30 ngày sau ngày kết thúc; gửi rồi
    sửa được 30 ngày kể từ lần gửi đầu.
  · Chín mục; mục nào chuyến không có thì không hiện; bỏ trống = không chấm, KHÔNG phải 0.
  · Đồng ý công khai hỏi riêng, không mặc định; công khai luôn không kèm tên (câu hỏi của
    `dong_y.CAU_HOI`). Sửa đánh giá không đổi được «không» thành «có» — một nhận xét một câu trả
    lời; đổi «có» thành «không» thì rút đồng ý bằng đúng đường rút của `dong_y`.
  · Điểm thấp → gọi lại `cskh.ghi_ket_qua`, luật mở khiếu nại DUY NHẤT của kho.

GÓP Ý RIÊNG LÃNH ĐẠO — chỉ Chủ tịch và TGĐ trả lời; BKS / robot Kiểm soát đọc theo luật chung
(BASE_VIEW), không ghi. Không ai khác đọc — kể cả người bị nhắc tên.

HỖ TRỢ — đổi / hủy → Sales phụ trách booking; hóa đơn → Kế toán; khác hoặc đơn chưa có Sales →
Sale Admin. CHỈ LÀ YÊU CẦU: màn này không hủy booking, không xuất hóa đơn, không chi tiền.
"""
import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.core import Booking, Tour, User
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.cskh import CareTicket
from app.models.danh_gia import DG_CO_KHOA, DG_DOI_TUONG, DanhGiaSauTour
from app.models.hr import DispatchOrder, Employee, GuideAssignment
from app.models.suppliers import ServiceOrder
from app.models.cham_soc_khach import (PhieuDanhGiaKhach, GopYLanhDao, HoTroKhach, TRANG_THAI_VIEC,
                                       LOAI_HO_TRO, BO_PHAN, MUC_GOP_Y, LIEN_HE_LAI)
from app.services import cong_khach as K

MO_CHAM_NGAY = 30          # mở chấm bao lâu sau khi tour kết thúc
SUA_NGAY = 30              # sửa được bao lâu sau lần gửi đầu
GUI_TOI_DA_NGAY = 10       # góp ý + hỗ trợ: tối đa mỗi loại / 24 giờ / tài khoản

THU_TU_MUC = ("tour", "hanh_trinh", "hdv", "tai_xe", "xe", "khach_san", "an_uong", "tham_quan", "tu_van")
TEN_MUC = {**DG_DOI_TUONG, "tour": "Tổng thể chuyến đi", "an_uong": "Nhà hàng / ăn uống",
           "khach_san": "Khách sạn"}

# Ai đọc / làm gì ở VTOS
VAI_GOP_Y_TRA_LOI = ("chutich", "tgd")
VAI_GOP_Y_DOC = ("chutich", "tgd", "bks", "robot_ks")
VAI_BO_PHAN = {"kinh_doanh": ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "sales_admin"),
               "ke_toan": ("ketoan",),            # Kế toán trưởng suy từ ketoan (vai_ke_thua)
               "sales_admin": ("sales_admin", "tp_kd", "gd_kd")}
VAI_XEM_HET = ("chutich", "tgd", "bks", "robot_ks")
VAI_CHI_VIEC_MINH = ("nv_kd", "tn_kd")       # Sales chỉ thấy yêu cầu giao cho chính mình


class LoiCham(ValueError):
    pass


def _bay_gio() -> datetime:
    return datetime.now()


def _ma(db: Session, model, dau: str) -> str:
    for _ in range(20):
        m = f"{dau}-{secrets.token_hex(2).upper()}"
        if not db.execute(select(model.id).where(model.ma == m)).first():
            return m
    raise LoiCham("Không sinh được mã, thử lại")


def che(s: str) -> str:
    s = (s or "").strip()
    if "@" in s:
        a, b = s.split("@", 1)
        return a[:2] + "•••@" + b
    return (s[:3] + "•••" + s[-2:]) if len(s) > 5 else s


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐÁNH GIÁ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _muc_cua_chuyen(db: Session, b: Booking, t: Tour) -> list[dict]:
    """Các mục chuyến này CÓ. Thiếu dữ liệu dịch vụ thì hiện mục mảng để khách tự bỏ trống."""
    muc = [{"doi_tuong": "tour", "id": None, "ten": t.name}, {"doi_tuong": "hanh_trinh", "id": None, "ten": ""}]
    for a in db.execute(select(GuideAssignment).where(
            GuideAssignment.tour_id == t.id, GuideAssignment.status.in_(["da_xac_nhan", "cho_xac_nhan"]))).scalars():
        e = db.get(Employee, a.guide_id)
        if e:
            muc.append({"doi_tuong": "hdv", "id": e.id, "ten": e.full_name})
    lenh = db.execute(select(DispatchOrder).where(DispatchOrder.tour_id == t.id, DispatchOrder.status != "huy")).scalars().all()
    da_tx = set()
    for d in lenh:
        if d.driver_id in da_tx:
            continue
        e = db.get(Employee, d.driver_id)
        if e:
            da_tx.add(d.driver_id)
            muc.append({"doi_tuong": "tai_xe", "id": e.id, "ten": e.full_name})
    loai = {x for x in db.execute(select(ServiceOrder.loai).where(ServiceOrder.tour_id == t.id,
                                                                  ServiceOrder.status != "huy")).scalars()}
    chua_ro = not loai          # chưa ai nhập đơn dịch vụ → không biết chuyến có gì
    nhieu_ngay = bool(t.start_date and t.end_date and t.end_date > t.start_date)
    if lenh or "van_chuyen" in loai or chua_ro:
        muc.append({"doi_tuong": "xe", "id": None, "ten": ""})
    if "khach_san" in loai or (chua_ro and nhieu_ngay):
        muc.append({"doi_tuong": "khach_san", "id": None, "ten": ""})
    if "nha_hang" in loai or chua_ro:
        muc.append({"doi_tuong": "an_uong", "id": None, "ten": ""})
    if "ve_tham_quan" in loai or chua_ro:
        muc.append({"doi_tuong": "tham_quan", "id": None, "ten": ""})
    s = db.get(User, b.sales_id) if b.sales_id else None
    if s:
        muc.append({"doi_tuong": "tu_van", "id": None, "ten": s.full_name})
    for m in muc:
        m["nhan"] = TEN_MUC[m["doi_tuong"]]
    return muc


def _care(db: Session, b: Booking) -> CareTicket:
    c = db.execute(select(CareTicket).where(CareTicket.booking_id == b.id)).scalars().first()
    if c:
        return c
    from app.services import cskh as CS
    CS.sinh_phieu(db, b.tour_id)          # sinh đúng kiểu robot sinh — một booking một phiếu
    c = db.execute(select(CareTicket).where(CareTicket.booking_id == b.id)).scalars().first()
    if not c:
        raise LoiCham("Chuyến này chưa mở đánh giá — tour chưa đóng trên hệ thống")
    return c


def _diem_da_cham(db: Session, care_id: int) -> list[DanhGiaSauTour]:
    return db.execute(select(DanhGiaSauTour).where(DanhGiaSauTour.care_id == care_id,
                                                   DanhGiaSauTour.nguon == "khach")).scalars().all()


def chuyen_danh_gia(db: Session, tk: TaiKhoanNgoai, now: datetime | None = None) -> list[dict]:
    K.la_khach(tk)
    now = now or _bay_gio()
    hom_nay = now.date()
    ra = []
    for b in K._booking_cua(db, tk):
        t = db.get(Tour, b.tour_id) if b.tour_id else None
        if not t or b.cancelled or t.status == "huy":
            continue
        phieu = db.execute(select(PhieuDanhGiaKhach).where(PhieuDanhGiaKhach.booking_id == b.id)).scalars().first()
        da_di = bool(t.end_date and t.end_date < hom_nay)
        mo_den = (t.end_date + timedelta(days=MO_CHAM_NGAY)) if t.end_date else None
        x = {"ma": b.code, "ten": t.name, "khoi_hanh": t.start_date.isoformat() if t.start_date else None,
             "ket_thuc": t.end_date.isoformat() if t.end_date else None}
        if phieu:
            care = db.get(CareTicket, phieu.care_id)
            dong = _diem_da_cham(db, phieu.care_id)
            x.update(trang_thai="da_gui", sua_duoc=hom_nay <= phieu.han_sua, han_sua=phieu.han_sua.isoformat(),
                     cong_khai=phieu.cong_khai, gop_y=phieu.gop_y, nhu_cau_tiep=(care.nhu_cau_tiep if care else ""),
                     da_cham=[{"doi_tuong": d.doi_tuong, "id": d.doi_tuong_id, "ten": d.doi_tuong_ten,
                               "nhan": TEN_MUC.get(d.doi_tuong, d.doi_tuong), "diem": d.diem, "nhan_xet": d.nhan_xet}
                              for d in dong])
            x["muc"] = _muc_cua_chuyen(db, b, t) if x["sua_duoc"] else []
        elif not da_di:
            x.update(trang_thai="chua_di", muc=[])
        elif mo_den and hom_nay > mo_den:
            x.update(trang_thai="het_han", muc=[])
        else:
            x.update(trang_thai="mo", han_cham=mo_den.isoformat() if mo_den else None, muc=_muc_cua_chuyen(db, b, t))
        ra.append(x)
    return ra


def gui_danh_gia(db: Session, tk: TaiKhoanNgoai, ma: str, data: dict, now: datetime | None = None) -> dict:
    """Gửi (lần đầu) hoặc sửa đánh giá một chuyến."""
    K.la_khach(tk)
    now = now or _bay_gio()
    hom_nay = now.date()
    b = next((x for x in K._booking_cua(db, tk) if x.code == ma), None)
    if b is None:
        raise LoiCham("Không tìm thấy đơn này trong tài khoản của bạn")
    t = db.get(Tour, b.tour_id) if b.tour_id else None
    if not t or b.cancelled or t.status == "huy":
        raise LoiCham("Đơn này không có chuyến đi để đánh giá")
    if not (t.end_date and t.end_date < hom_nay):
        raise LoiCham("Chỉ đánh giá được chuyến đã đi xong")
    phieu = db.execute(select(PhieuDanhGiaKhach).where(PhieuDanhGiaKhach.booking_id == b.id)).scalars().first()
    if phieu is None and hom_nay > t.end_date + timedelta(days=MO_CHAM_NGAY):
        raise LoiCham(f"Đã quá {MO_CHAM_NGAY} ngày sau chuyến đi — liên hệ Vietourist nếu bạn vẫn muốn góp ý")
    if phieu is not None and hom_nay > phieu.han_sua:
        raise LoiCham("Đã quá hạn sửa đánh giá")

    hop_le = {(m["doi_tuong"], m["id"]): m for m in _muc_cua_chuyen(db, b, t)}
    dong = []
    for d in data.get("diem") or []:
        dt = (d.get("doi_tuong") or "").strip()
        did = d.get("id")
        did = int(did) if (dt in DG_CO_KHOA and did) else None
        m = hop_le.get((dt, did))
        if m is None:
            raise LoiCham(f"Mục không thuộc chuyến này: {TEN_MUC.get(dt, dt)}")
        sao = d.get("diem")
        if sao in (None, "", 0):
            sao = None
        else:
            sao = int(sao)
            if not 1 <= sao <= 5:
                raise LoiCham("Điểm chỉ từ 1 đến 5 sao")
        nx = (d.get("nhan_xet") or "").strip()[:2000]
        dong.append((dt, did, m["ten"] or TEN_MUC[dt], sao, nx))
    if not any(x[3] for x in dong):
        raise LoiCham("Bạn chấm ít nhất một mục giúp Vietourist")
    if data.get("nhu_cau_tiep") not in ("co", "khong"):
        raise LoiCham("Bạn cho biết có muốn Vietourist gợi ý chuyến tiếp theo không")
    cong_khai = data.get("cong_khai")
    if phieu is None and cong_khai not in ("co", "khong"):
        raise LoiCham("Bạn chọn có hay không đồng ý công khai nhận xét")

    care = _care(db, b)
    from app.services import dong_y as DY
    cu = {(x.doi_tuong, x.doi_tuong_id): x for x in _diem_da_cham(db, care.id)}
    giu = set()
    for dt, did, ten, sao, nx in dong:
        x = cu.get((dt, did))
        if x is None:
            if sao is None and not nx:
                continue
            from app.services import danh_gia as DG
            DG.ghi_dong_khach_tu_cham(db, care, dt, did, ten, sao, nx,
                                      phieu.cong_khai if phieu else cong_khai, "cong_khach")
        else:
            x.diem, x.nhan_xet = sao, nx
        giu.add((dt, did))
    for k, x in cu.items():          # mục khách xoá khi sửa: để rỗng, không xoá dòng (nhật ký điểm)
        if k not in giu:
            x.diem, x.nhan_xet = None, ""

    if phieu is None:
        phieu = PhieuDanhGiaKhach(booking_id=b.id, care_id=care.id, tai_khoan_id=tk.id, gui_luc=now,
                                  han_sua=hom_nay + timedelta(days=SUA_NGAY), cong_khai=cong_khai)
        db.add(phieu)
    else:
        phieu.sua_luc, phieu.so_lan_sua = now, phieu.so_lan_sua + 1
        if cong_khai == "khong" and phieu.cong_khai == "co":       # rút đồng ý: đúng đường rút của dong_y
            from app.models.danh_gia import DongYCongKhai
            for r in db.execute(select(DongYCongKhai).where(DongYCongKhai.care_id == care.id)).scalars():
                if r.tra_loi == "co" and r.ma_rut and r.rut_luc is None:
                    DY.rut(db, r.ma_rut, "Khách đổi lựa chọn khi sửa đánh giá trên cổng")
            phieu.cong_khai = "khong"
    phieu.gop_y = (data.get("gop_y") or "").strip()[:2000]
    db.flush()

    # Điểm chung = điểm «tổng thể»; không có thì trung bình các mục, LÀM TRÒN XUỐNG (như danh_gia.py).
    dd = [x for x in _diem_da_cham(db, care.id) if x.diem]
    tong = next((x.diem for x in dd if x.doi_tuong == "tour"), None)
    if tong is None:
        tong = int(sum(x.diem for x in dd) / len(dd)) if dd else 3
    thap = {"hdv": "hdv", "tai_xe": "xe", "xe": "xe", "khach_san": "khach_san", "an_uong": "an_uong",
            "hanh_trinh": "lich_trinh"}
    chua_hl = sorted({thap[x.doi_tuong] for x in dd if x.doi_tuong in thap and x.diem <= 3})
    from app.services import cskh as CS
    from app.services import danh_gia as DG
    CS.ghi_ket_qua(db, DG._may(db), care, {
        "lien_he_duoc": "co", "hinh_thuc": "cong", "hai_long": max(1, min(5, tong)),
        "nhu_cau_tiep": data["nhu_cau_tiep"], "dong_y_dung_danh_gia": phieu.cong_khai,
        "diem_chua_hai_long": chua_hl, "ghi_chu": phieu.gop_y})
    db.commit()
    return {"message": "Cảm ơn bạn đã đánh giá." if phieu.so_lan_sua == 0 else "Đã lưu đánh giá đã sửa.",
            "han_sua": phieu.han_sua.isoformat()}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# GÓP Ý RIÊNG LÃNH ĐẠO
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _dem_24h(db: Session, model, tk_id: int, now: datetime) -> int:
    return len(db.execute(select(model.id).where(model.tai_khoan_id == tk_id,
                                                 model.tao_luc > now - timedelta(hours=24))).all())


def _booking_ma(db: Session, tk: TaiKhoanNgoai, ma: str | None) -> Booking | None:
    if not ma:
        return None
    b = next((x for x in K._booking_cua(db, tk) if x.code == ma), None)
    if b is None:
        raise LoiCham("Không tìm thấy đơn này trong tài khoản của bạn")
    return b


def gui_gop_y(db: Session, tk: TaiKhoanNgoai, data: dict, now: datetime | None = None) -> GopYLanhDao:
    K.la_khach(tk)
    now = now or _bay_gio()
    tieu_de = (data.get("tieu_de") or "").strip()
    noi_dung = (data.get("noi_dung") or "").strip()
    if len(tieu_de) < 3 or len(noi_dung) < 10:
        raise LoiCham("Bạn ghi tiêu đề và nội dung góp ý (ít nhất 10 ký tự)")
    muc = data.get("muc") or "thuong"
    lh = data.get("lien_he_qua") or "email"
    if muc not in MUC_GOP_Y or lh not in LIEN_HE_LAI:
        raise LoiCham("Lựa chọn không hợp lệ")
    if _dem_24h(db, GopYLanhDao, tk.id, now) >= GUI_TOI_DA_NGAY:
        raise LoiCham("Bạn đã gửi nhiều góp ý trong 24 giờ — vui lòng thử lại sau")
    b = _booking_ma(db, tk, data.get("ma_don"))
    g = GopYLanhDao(ma=_ma(db, GopYLanhDao, "GY"), tai_khoan_id=tk.id, booking_id=b.id if b else None,
                    tieu_de=tieu_de[:200], noi_dung=noi_dung[:5000], muc=muc, lien_he_qua=lh, tao_luc=now)
    db.add(g)
    db.commit()
    return g


def _gop_y_out(db: Session, g: GopYLanhDao, noi_bo: bool) -> dict:
    b = db.get(Booking, g.booking_id) if g.booking_id else None
    x = {"id": g.id, "ma": g.ma, "tieu_de": g.tieu_de, "noi_dung": g.noi_dung, "don": b.code if b else "",
         "muc": g.muc, "muc_ten": MUC_GOP_Y[g.muc], "lien_he_qua": LIEN_HE_LAI.get(g.lien_he_qua, ""),
         "trang_thai": g.trang_thai, "trang_thai_ten": TRANG_THAI_VIEC[g.trang_thai],
         "tra_loi": g.tra_loi, "tra_loi_luc": g.tra_loi_luc.isoformat(timespec="minutes") if g.tra_loi_luc else None,
         "gui_luc": g.tao_luc.isoformat(timespec="minutes")}
    if noi_bo:
        tk = db.get(TaiKhoanNgoai, g.tai_khoan_id)
        x.update(khach=(tk.ho_ten if tk else "") or "Khách", lien_he=che((tk.dien_thoai or tk.email) if tk else ""),
                 ghi_chu_noi_bo=g.ghi_chu_noi_bo, tra_loi_boi=g.tra_loi_boi, cap_nhat_boi=g.cap_nhat_boi)
    return x


def gop_y_cua(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    K.la_khach(tk)
    ds = db.execute(select(GopYLanhDao).where(GopYLanhDao.tai_khoan_id == tk.id).order_by(GopYLanhDao.tao_luc.desc())).scalars()
    return [_gop_y_out(db, g, False) for g in ds]


def ds_gop_y(db: Session, u: User, trang_thai: str = "") -> list[dict]:
    if u.role not in VAI_GOP_Y_DOC:
        raise LoiCham("Chỉ Chủ tịch và Tổng Giám đốc đọc góp ý riêng của khách")
    q = select(GopYLanhDao).order_by(GopYLanhDao.tao_luc.desc())
    if trang_thai:
        q = q.where(GopYLanhDao.trang_thai == trang_thai)
    return [_gop_y_out(db, g, True) for g in db.execute(q).scalars()]


def cap_nhat_gop_y(db: Session, u: User, gid: int, data: dict, now: datetime | None = None) -> dict:
    if u.role not in VAI_GOP_Y_TRA_LOI:
        raise LoiCham("Chỉ Chủ tịch và Tổng Giám đốc trả lời góp ý riêng của khách")
    now = now or _bay_gio()
    g = db.get(GopYLanhDao, gid)
    if not g:
        raise LoiCham("Không tìm thấy góp ý")
    truoc = {"trang_thai": g.trang_thai, "tra_loi": g.tra_loi}
    tt = data.get("trang_thai") or g.trang_thai
    if tt not in TRANG_THAI_VIEC:
        raise LoiCham("Trạng thái không hợp lệ")
    tl = (data.get("tra_loi") or "").strip()
    if tl and tl != g.tra_loi:
        g.tra_loi, g.tra_loi_boi, g.tra_loi_luc = tl[:5000], u.username, now
    if tt == "da_tra_loi" and not g.tra_loi:
        raise LoiCham("Ghi câu trả lời trước khi đánh dấu đã trả lời")
    if "ghi_chu_noi_bo" in data:
        g.ghi_chu_noi_bo = (data.get("ghi_chu_noi_bo") or "").strip()[:5000]
    g.trang_thai, g.cap_nhat_boi, g.cap_nhat_luc = tt, u.username, now
    from app.services import rules as R
    R.audit(db, u.username, u.role, "cap_nhat_gop_y_lanh_dao", f"gop_y_lanh_dao:{g.id}", truoc,
            {"trang_thai": g.trang_thai, "tra_loi": g.tra_loi})
    db.commit()
    return _gop_y_out(db, g, True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HỖ TRỢ: ĐỔI · HỦY · HÓA ĐƠN · KHÁC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def bo_phan_cho(db: Session, loai: str, b: Booking | None) -> tuple[str, int | None]:
    if loai in ("doi", "huy") and b is not None and b.sales_id:
        u = db.get(User, b.sales_id)
        if u and getattr(u, "active", True):
            return "kinh_doanh", u.id
    if loai == "hoa_don":
        return "ke_toan", None
    return "sales_admin", None


def gui_ho_tro(db: Session, tk: TaiKhoanNgoai, data: dict, now: datetime | None = None) -> HoTroKhach:
    K.la_khach(tk)
    now = now or _bay_gio()
    loai = data.get("loai")
    if loai not in LOAI_HO_TRO:
        raise LoiCham("Bạn chọn loại yêu cầu")
    b = _booking_ma(db, tk, data.get("ma_don"))
    if loai in ("doi", "huy", "hoa_don") and b is None:
        raise LoiCham("Bạn chọn đơn cần hỗ trợ")
    if loai in ("doi", "huy") and b.cancelled:
        raise LoiCham("Đơn này đã hủy")
    noi_dung = (data.get("noi_dung") or "").strip()
    hd = None
    if loai == "hoa_don":
        h = data.get("hoa_don") or {}
        hd = {k: (str(h.get(k) or "").strip())[:300] for k in ("ten_don_vi", "mst", "dia_chi", "email")}
        if not hd["ten_don_vi"] or not hd["mst"] or not hd["dia_chi"]:
            raise LoiCham("Hóa đơn cần tên đơn vị, mã số thuế và địa chỉ")
        if not hd["mst"].replace("-", "").isdigit() or len(hd["mst"].replace("-", "")) not in (10, 13):
            raise LoiCham("Mã số thuế gồm 10 hoặc 13 chữ số")
    elif len(noi_dung) < 5:
        raise LoiCham("Bạn ghi rõ nội dung cần hỗ trợ")
    if _dem_24h(db, HoTroKhach, tk.id, now) >= GUI_TOI_DA_NGAY:
        raise LoiCham("Bạn đã gửi nhiều yêu cầu trong 24 giờ — vui lòng thử lại sau")
    bp, giao = bo_phan_cho(db, loai, b)
    y = HoTroKhach(ma=_ma(db, HoTroKhach, "HT"), tai_khoan_id=tk.id, booking_id=b.id if b else None, loai=loai,
                   noi_dung=noi_dung[:3000], hoa_don=hd, bo_phan=bp, giao_cho_id=giao, tao_luc=now)
    db.add(y)
    db.commit()
    return y


def _ho_tro_out(db: Session, y: HoTroKhach, noi_bo: bool) -> dict:
    b = db.get(Booking, y.booking_id) if y.booking_id else None
    g = db.get(User, y.giao_cho_id) if y.giao_cho_id else None
    x = {"id": y.id, "ma": y.ma, "loai": y.loai, "loai_ten": LOAI_HO_TRO[y.loai], "don": b.code if b else "",
         "noi_dung": y.noi_dung, "hoa_don": y.hoa_don, "bo_phan": y.bo_phan, "bo_phan_ten": BO_PHAN[y.bo_phan],
         "trang_thai": y.trang_thai, "trang_thai_ten": TRANG_THAI_VIEC[y.trang_thai], "tra_loi": y.tra_loi,
         "tra_loi_luc": y.tra_loi_luc.isoformat(timespec="minutes") if y.tra_loi_luc else None,
         "gui_luc": y.tao_luc.isoformat(timespec="minutes")}
    if noi_bo:
        tk = db.get(TaiKhoanNgoai, y.tai_khoan_id)
        x.update(khach=(b.customer_name if b else "") or (tk.ho_ten if tk else "") or "Khách",
                 lien_he=che((tk.dien_thoai or tk.email) if tk else ""), giao_cho=g.full_name if g else "",
                 giao_cho_id=y.giao_cho_id, nhan_boi=y.nhan_boi, tra_loi_boi=y.tra_loi_boi)
    return x


def ho_tro_cua(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    K.la_khach(tk)
    ds = db.execute(select(HoTroKhach).where(HoTroKhach.tai_khoan_id == tk.id).order_by(HoTroKhach.tao_luc.desc())).scalars()
    return [_ho_tro_out(db, y, False) for y in ds]


def _thuoc(vai: str, nhom: tuple) -> bool:
    from app.services import vai_ke_thua as VKT
    return vai in VKT.mo_rong(nhom)


def _thay_duoc(u: User, y: HoTroKhach) -> bool:
    if u.role in VAI_XEM_HET:
        return True
    if u.role in VAI_CHI_VIEC_MINH:
        return y.giao_cho_id == u.id
    return _thuoc(u.role, VAI_BO_PHAN.get(y.bo_phan, ()))


def ds_ho_tro(db: Session, u: User, trang_thai: str = "") -> list[dict]:
    q = select(HoTroKhach).order_by(HoTroKhach.tao_luc.desc())
    if trang_thai == "mo":
        q = q.where(HoTroKhach.trang_thai != "dong")
    elif trang_thai:
        q = q.where(HoTroKhach.trang_thai == trang_thai)
    if u.role not in VAI_XEM_HET:
        bp = [k for k, v in VAI_BO_PHAN.items() if _thuoc(u.role, v)]
        if not bp:
            return []
        q = q.where(or_(HoTroKhach.bo_phan.in_(bp), HoTroKhach.giao_cho_id == u.id))
    return [_ho_tro_out(db, y, True) for y in db.execute(q).scalars() if _thay_duoc(u, y)]


def cap_nhat_ho_tro(db: Session, u: User, yid: int, data: dict, now: datetime | None = None) -> dict:
    now = now or _bay_gio()
    y = db.get(HoTroKhach, yid)
    if not y or not _thay_duoc(u, y):
        raise LoiCham("Không tìm thấy yêu cầu trong phạm vi của bạn")
    truoc = {"trang_thai": y.trang_thai, "bo_phan": y.bo_phan, "giao_cho_id": y.giao_cho_id, "tra_loi": y.tra_loi}
    hd = data.get("hanh_dong")
    if hd == "nhan":
        y.trang_thai, y.nhan_boi = ("dang_xu_ly" if y.trang_thai == "moi" else y.trang_thai), u.username
        if y.giao_cho_id is None:
            y.giao_cho_id = u.id
    elif hd == "tra_loi":
        tl = (data.get("tra_loi") or "").strip()
        if len(tl) < 3:
            raise LoiCham("Ghi câu trả lời cho khách")
        y.tra_loi, y.tra_loi_boi, y.tra_loi_luc, y.trang_thai = tl[:5000], u.username, now, "da_tra_loi"
    elif hd == "dong":
        if not y.tra_loi:
            raise LoiCham("Trả lời khách trước khi đóng yêu cầu")
        y.trang_thai = "dong"
    elif hd == "chuyen":
        bp = data.get("bo_phan")
        if bp not in BO_PHAN:
            raise LoiCham("Bộ phận không hợp lệ")
        y.bo_phan, y.giao_cho_id, y.trang_thai = bp, None, "moi"
    else:
        raise LoiCham("Thao tác không hợp lệ")
    y.cap_nhat_luc = now
    from app.services import rules as R
    R.audit(db, u.username, u.role, f"ho_tro_khach_{hd}", f"ho_tro_khach:{y.id}", truoc,
            {"trang_thai": y.trang_thai, "bo_phan": y.bo_phan, "giao_cho_id": y.giao_cho_id, "tra_loi": y.tra_loi})
    db.commit()
    return _ho_tro_out(db, y, True)
