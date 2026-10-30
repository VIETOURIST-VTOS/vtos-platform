"""NCC-1 · Cổng Nhà cung cấp N01–N18 — phép tính và hàng rào (Chủ tịch duyệt bản xem thử 28/10/2026).

QUY TẮC (đúng bản xem thử):
  1. Tài khoản NCC chỉ thấy số liệu khi đã NỐI vào một NCC trong danh mục (gợi ý MST → SĐT; TP Điều hành,
     GĐ KD, Chủ tịch, TGĐ nối). Chưa nối: «Đang chờ nối hồ sơ».
  2. Đơn dịch vụ: NCC chỉ thấy đơn CỦA MÌNH đã gửi (không nháp), không thấy tên / SĐT khách. «Xác nhận đơn»
     đổi NGAY đơn sang «NCC đã xác nhận» kèm mã xác nhận. Từ chối có lý do: đơn giữ nguyên, Điều hành xử lý.
  3. Giá: NCC chỉ ĐỀ XUẤT; Điều hành (tp_dh) duyệt mới thành giá áp dụng. Không đổi giá trên đơn đã đặt.
     Nhà hàng: đề xuất thực đơn / giá → duyệt thì ghi vào thực đơn nhà hàng.
  4. Công nợ: Vietourist phải trả = đơn đã xác nhận / đã dùng mà đề nghị chi gắn đơn CHƯA ở «đã chi».
     Chiều NCC phải trả Vietourist: chưa có nguồn — trả None, không phải 0. Hai chiều không bù trừ.
  5. Bản kê: Kế toán lập theo kỳ từ đơn đã xác nhận / đã dùng; NCC xác nhận (khóa) hoặc báo chênh lệch từng dòng.
     Xác nhận bản kê không phải duyệt chi.
  6. Đề nghị của NCC không tự thành phiếu chi; bộ phận phụ trách trả lời.
  7. Đổi tài khoản ngân hàng: tạo yêu cầu trong quy trình đổi TK HAI NGƯỜI hiện có; chưa xác nhận thì không dùng.
  8. Nhà hàng: nhận / từ chối đơn đặt bàn của nhà hàng mình; không thấy SĐT khách.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.services.zalo import norm_phone
from app.models.attachments import Attachment
from app.models.cong_khach import YeuCauKhach
from app.models.cong_ncc import (BO_PHAN_DE_NGHI, DANH_CHO, LOAI_DE_NGHI, NHA_HANG_TT, NHOM_HOC_LIEU,
                                 TRANG_THAI_BAN_KE, TRANG_THAI_DE_NGHI, TRANG_THAI_DE_XUAT, BanKeNcc,
                                 DeNghiNcc, DeXuatGiaNcc, DongBanKeNcc, GiaNcc, HocLieuDoiTac, PhanHoiDonNcc)
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import Tour, User
from app.models.nha_hang import NhaHang, ThucDonNhaHang  # noqa: F401  (API dùng S.NhaHang)
from app.models.ops import PaymentRequest
from app.models.suppliers import LOAI_NCC, TRANG_THAI_DON, ServiceOrder, Supplier, SupplierBankChange
from app.services import attachments as AT
from app.services import rules as R
from app.services import suppliers as SV

VAI_XEM = ("chutich", "tgd", "bks", "robot_ks", "tp_dh", "nv_dh", "gd_kd", "ketoan", "nv_mkt", "ptgd_mkt")
VAI_NOI = ("chutich", "tgd", "tp_dh", "gd_kd")
VAI_DUYET_GIA = ("tp_dh",)
VAI_KE_TOAN = ("ketoan",)
VAI_DIEU_HANH = ("tp_dh", "nv_dh")
VAI_HOC_LIEU = ("tp_dh", "nv_mkt", "ptgd_mkt")
DON_HIEN = ("da_gui", "da_xac_nhan", "da_su_dung", "huy")
DON_NO = ("da_xac_nhan", "da_su_dung")


class LoiNcc(Exception):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def _so(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def _che(s: str, giu: int = 4) -> str:
    s = str(s or "")
    return ("•" * max(0, len(s) - giu) + s[-giu:]) if s else ""


# ====================================================================== cửa vào cổng
def ncc_cua(db: Session, tk: TaiKhoanNgoai) -> Supplier:
    if tk.loai != "doi_tac" or tk.loai_doi_tac != "ncc":
        raise LoiNcc("Mục này dành cho tài khoản nhà cung cấp", 403)
    if tk.trang_thai != "hoat_dong":
        raise LoiNcc("Tài khoản nhà cung cấp chưa được duyệt", 403)
    s = db.get(Supplier, tk.ncc_id) if tk.ncc_id else None
    if s is None:
        raise LoiNcc("Tài khoản chưa nối với nhà cung cấp trong danh mục — TP Điều hành nối hồ sơ", 409)
    return s


def _ho_so(s: Supplier) -> dict:
    return {"id": s.id, "code": s.code, "ten": s.ten, "ten_phap_nhan": s.ten_phap_nhan, "loai": s.loai,
            "loai_ten": LOAI_NCC.get(s.loai, s.loai), "ma_so_thue": s.ma_so_thue, "dia_chi": s.dia_chi,
            "dieu_khoan_tt": s.dieu_khoan_tt, "active": s.active}


def _nha_hang_cua(db: Session, s: Supplier) -> list[NhaHang]:
    return list(db.execute(select(NhaHang).where(NhaHang.supplier_id == s.id)).scalars())


# ====================================================================== nối tài khoản (VTOS)
def goi_y(db: Session, tk: TaiKhoanNgoai) -> dict:
    ds = db.execute(select(Supplier).where(Supplier.active.is_(True))).scalars().all()
    mst = _so(tk.ma_so_thue)
    khop, theo = [], ""
    if len(mst) >= 10:
        khop, theo = [s for s in ds if _so(s.ma_so_thue) == mst], "mã số thuế"
    if not khop and tk.dien_thoai:
        khop, theo = [s for s in ds if s.dien_thoai and norm_phone(s.dien_thoai) == tk.dien_thoai], "số điện thoại"
    return {"khop": [{"id": s.id, "code": s.code, "ten": s.ten, "ma_so_thue": s.ma_so_thue} for s in khop],
            "theo": theo if khop else ""}


def ds_tai_khoan(db: Session) -> list[dict]:
    ra = []
    for tk in db.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.loai == "doi_tac", TaiKhoanNgoai.loai_doi_tac == "ncc")
                         .order_by(TaiKhoanNgoai.id.desc())).scalars():
        s = db.get(Supplier, tk.ncc_id) if tk.ncc_id else None
        ra.append({"tai_khoan_id": tk.id, "ho_ten": tk.ho_ten, "ten_don_vi": tk.ten_don_vi, "ma_so_thue": tk.ma_so_thue,
                   "lien_he": tk.dien_thoai or tk.email, "trang_thai": tk.trang_thai,
                   "ncc": {"id": s.id, "code": s.code, "ten": s.ten} if s else None,
                   "goi_y": goi_y(db, tk) if s is None else None})
    return ra


def tim_ncc(db: Session, q: str) -> list[dict]:
    k = f"%{(q or '').strip()}%"
    rows = db.execute(select(Supplier).where(or_(Supplier.ten.ilike(k), Supplier.code.ilike(k), Supplier.ma_so_thue.ilike(k)))
                      .order_by(Supplier.ten).limit(30)).scalars()
    return [{"id": s.id, "code": s.code, "ten": s.ten, "ma_so_thue": s.ma_so_thue} for s in rows]


def noi(db: Session, u: User, tk_id: int, ncc_id: int | None) -> TaiKhoanNgoai:
    if u.role not in VAI_NOI:
        raise LoiNcc("Chỉ TP Điều hành, GĐ KD, Chủ tịch, TGĐ nối tài khoản NCC", 403)
    tk = db.get(TaiKhoanNgoai, tk_id)
    if tk is None or tk.loai != "doi_tac" or tk.loai_doi_tac != "ncc":
        raise LoiNcc("Không có tài khoản nhà cung cấp này", 404)
    truoc = tk.ncc_id
    if ncc_id:
        s = db.get(Supplier, ncc_id)
        if s is None or not s.active:
            raise LoiNcc("Nhà cung cấp không tồn tại hoặc đã ngưng")
        tk.ncc_id = s.id
    else:
        tk.ncc_id = None
    db.flush()
    R.audit(db, u.username, u.role, "cong_ncc_noi" if ncc_id else "cong_ncc_go_noi", f"tai_khoan_ngoai:{tk.id}",
            before={"ncc_id": truoc}, after={"ncc_id": tk.ncc_id})
    return tk


def _co_khach_san(db: Session, s) -> bool:
    from app.models.khach_san_vtd import KhachSanVtd
    return db.execute(select(KhachSanVtd.id).where(KhachSanVtd.supplier_id == s.id)).first() is not None


def gan_nha_hang(db: Session, u: User, nha_hang_id: int, ncc_id: int | None) -> NhaHang:
    if u.role not in VAI_NOI:
        raise LoiNcc("Chỉ TP Điều hành, GĐ KD, Chủ tịch, TGĐ gắn nhà hàng với NCC", 403)
    n = db.get(NhaHang, nha_hang_id)
    if n is None:
        raise LoiNcc("Không có nhà hàng này", 404)
    if ncc_id and db.get(Supplier, ncc_id) is None:
        raise LoiNcc("Không có NCC này", 404)
    n.supplier_id = ncc_id or None
    db.flush()
    R.audit(db, u.username, u.role, "cong_ncc_gan_nha_hang", f"nha_hang:{n.ma}", after={"supplier_id": n.supplier_id})
    return n


# ====================================================================== đơn dịch vụ (N05–N06)
def _tour_ma(db: Session, tid: int) -> str:
    t = db.get(Tour, tid)
    return getattr(t, "code", "") if t else ""


def _ra_don(db: Session, d: ServiceOrder, chi_tiet: bool = False) -> dict:
    pr = db.get(PaymentRequest, d.payment_request_id) if d.payment_request_id else None
    ph = list(db.execute(select(PhanHoiDonNcc).where(PhanHoiDonNcc.service_order_id == d.id)
                         .order_by(PhanHoiDonNcc.id.desc())).scalars())
    tu_choi = next((p for p in ph if p.hanh_dong == "tu_choi" and not p.xu_ly_luc), None) if d.status == "da_gui" else None
    r = {"id": d.id, "code": d.code, "noi_dung": d.noi_dung, "ngay_su_dung": d.ngay_su_dung, "so_luong": d.so_luong,
         "don_vi": d.don_vi, "don_gia": d.don_gia, "thanh_tien": d.thanh_tien, "status": d.status,
         "status_ten": "Bạn đã từ chối · chờ Điều hành" if tu_choi else ("Chờ bạn xác nhận" if d.status == "da_gui" else TRANG_THAI_DON.get(d.status, d.status)),
         "xac_nhan_ncc": d.xac_nhan_ncc, "tour": _tour_ma(db, d.tour_id), "ngay_den_han": d.ngay_den_han,
         "da_chi": bool(pr and pr.status == "da_chi"), "phieu_chi": pr.code if pr else ""}
    if chi_tiet:
        t = db.get(Tour, d.tour_id)
        r["so_khach_doan"] = getattr(t, "planned_pax", None) or None
        r["phan_hoi"] = [{"hanh_dong": p.hanh_dong, "ma_xac_nhan": p.ma_xac_nhan, "ghi_chu": p.ghi_chu,
                          "co_tep": p.attachment_id is not None, "luc": p.luc, "xu_ly_luc": p.xu_ly_luc} for p in ph]
    return r


def ds_don(db: Session, s: Supplier) -> list[dict]:
    rows = db.execute(select(ServiceOrder).where(ServiceOrder.supplier_id == s.id, ServiceOrder.status.in_(DON_HIEN))
                      .order_by(ServiceOrder.ngay_su_dung.desc().nullslast(), ServiceOrder.id.desc()).limit(300)).scalars()
    return [_ra_don(db, d) for d in rows]


def _don_cua(db: Session, s: Supplier, did: int) -> ServiceOrder:
    d = db.get(ServiceOrder, did)
    if d is None or d.supplier_id != s.id or d.status not in DON_HIEN:
        raise LoiNcc("Không có đơn này", 404)
    return d


def mot_don(db: Session, s: Supplier, did: int) -> dict:
    return _ra_don(db, _don_cua(db, s, did), True)


def phan_hoi_don(db: Session, tk: TaiKhoanNgoai, s: Supplier, did: int, hanh_dong: str, ma: str = "", ghi_chu: str = "",
                 ten_tep: str = "", kieu: str = "", data: bytes | None = None) -> dict:
    d = _don_cua(db, s, did)
    ma, ghi_chu = (ma or "").strip()[:100], (ghi_chu or "").strip()[:2000]
    att = None
    if hanh_dong == "xac_nhan":
        if d.status != "da_gui":
            raise LoiNcc("Đơn này không ở trạng thái chờ xác nhận", 409)
        if not ma:
            raise LoiNcc("Ghi mã / số xác nhận của bạn")
        SV.chuyen_trang_thai(db, d, "da_xac_nhan", f"cong:ncc-{tk.id}", f"Cổng NCC · {ma}")
    elif hanh_dong == "tu_choi":
        if d.status != "da_gui":
            raise LoiNcc("Chỉ từ chối được đơn đang chờ xác nhận", 409)
        if not ghi_chu:
            raise LoiNcc("Từ chối phải ghi lý do")
    elif hanh_dong == "chung_tu":
        if not data:
            raise LoiNcc("Chọn tệp chứng từ")
        try:
            att, _ = AT.dinh_kem(db, "don_dich_vu", d.code, ten_tep, data, kieu=kieu, loai="chung_tu",
                                 mo_ta=f"NCC gửi qua cổng · {ghi_chu[:100]}", boi=f"cong:ncc-{tk.id}")
        except ValueError as ex:
            raise LoiNcc(str(ex))
    else:
        raise LoiNcc("Hành động không hợp lệ")
    db.add(PhanHoiDonNcc(service_order_id=d.id, tai_khoan_id=tk.id, hanh_dong=hanh_dong, ma_xac_nhan=ma,
                         ghi_chu=ghi_chu, attachment_id=att.id if att else None, luc=datetime.now()))
    db.flush()
    R.audit(db, f"cong:ncc-{tk.id}", "doi_tac", f"cong_ncc_don_{hanh_dong}", f"service_order:{d.code}",
            after={"ma": ma, "status": d.status})
    return _ra_don(db, d, True)


def don_bi_tu_choi(db: Session) -> list[dict]:
    ra = []
    for p in db.execute(select(PhanHoiDonNcc).where(PhanHoiDonNcc.hanh_dong == "tu_choi", PhanHoiDonNcc.xu_ly_luc.is_(None))
                        .order_by(PhanHoiDonNcc.id.desc())).scalars():
        d = db.get(ServiceOrder, p.service_order_id)
        s = db.get(Supplier, d.supplier_id) if d else None
        ra.append({"id": p.id, "don": d.code if d else "", "ncc": s.ten if s else "", "noi_dung": d.noi_dung if d else "",
                   "ly_do": p.ghi_chu, "luc": p.luc, "status": d.status if d else ""})
    return ra


def xu_ly_tu_choi(db: Session, u: User, pid: int) -> None:
    if u.role not in VAI_DIEU_HANH:
        raise LoiNcc("Chỉ Điều hành xử lý", 403)
    p = db.get(PhanHoiDonNcc, pid)
    if p is None or p.hanh_dong != "tu_choi":
        raise LoiNcc("Không có phản hồi này", 404)
    p.xu_ly_boi, p.xu_ly_luc = u.username, datetime.now()
    db.flush()


# ====================================================================== giá & đề xuất (N02–N04, N14)
def _ra_gia(g: GiaNcc) -> dict:
    return {"id": g.id, "dich_vu": g.dich_vu, "don_vi": g.don_vi, "gia": g.gia, "so_luong_mo": g.so_luong_mo,
            "tu_ngay": g.tu_ngay, "den_ngay": g.den_ngay, "ngay_khong_phuc_vu": g.ngay_khong_phuc_vu}


def _ra_dx(db: Session, x: DeXuatGiaNcc) -> dict:
    s = db.get(Supplier, x.supplier_id)
    return {"id": x.id, "ncc": s.ten if s else "", "loai": x.loai, "gia_ncc_id": x.gia_ncc_id, "thuc_don_id": x.thuc_don_id,
            "nha_hang_id": x.nha_hang_id, "dich_vu": x.dich_vu, "don_vi": x.don_vi, "gia": x.gia, "gia_tre_em": x.gia_tre_em,
            "so_luong_mo": x.so_luong_mo, "tu_ngay": x.tu_ngay, "den_ngay": x.den_ngay,
            "ngay_khong_phuc_vu": x.ngay_khong_phuc_vu, "ghi_chu": x.ghi_chu, "trang_thai": x.trang_thai,
            "trang_thai_ten": TRANG_THAI_DE_XUAT.get(x.trang_thai, x.trang_thai), "ly_do": x.ly_do, "luc": x.luc}


def gia_dang_ap_dung(db: Session, s: Supplier) -> list[dict]:
    return [_ra_gia(g) for g in db.execute(select(GiaNcc).where(GiaNcc.supplier_id == s.id, GiaNcc.het_hieu_luc.is_(False))
                                           .order_by(GiaNcc.dich_vu, GiaNcc.tu_ngay)).scalars()]


def thuc_don_cua(db: Session, s: Supplier) -> list[dict]:
    ra = []
    for n in _nha_hang_cua(db, s):
        for t in db.execute(select(ThucDonNhaHang).where(ThucDonNhaHang.nha_hang_id == n.id).order_by(ThucDonNhaHang.id)).scalars():
            ra.append({"id": t.id, "nha_hang_id": n.id, "nha_hang": n.ten, "ten": t.ten, "gia_nguoi_lon": t.gia_nguoi_lon,
                       "gia_tre_em": t.gia_tre_em, "tu_ngay": t.tu_ngay, "den_ngay": t.den_ngay, "dang_ban": t.dang_ban})
    return ra


def _ngay(v) -> date | None:
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        raise LoiNcc("Ngày không hợp lệ")


def de_xuat(db: Session, tk: TaiKhoanNgoai, s: Supplier, d: dict) -> DeXuatGiaNcc:
    loai = d.get("loai") or "gia"
    gia = float(d.get("gia") or 0)
    if gia <= 0:
        raise LoiNcc("Giá đề xuất phải lớn hơn 0")
    tu, den = _ngay(d.get("tu_ngay")), _ngay(d.get("den_ngay"))
    if tu and den and den < tu:
        raise LoiNcc("Ngày kết thúc trước ngày bắt đầu")
    x = DeXuatGiaNcc(supplier_id=s.id, tai_khoan_id=tk.id, loai=loai, gia=gia, tu_ngay=tu, den_ngay=den,
                     ghi_chu=str(d.get("ghi_chu") or "").strip()[:2000], luc=datetime.now())
    if loai == "gia":
        if d.get("gia_ncc_id"):
            g = db.get(GiaNcc, int(d["gia_ncc_id"]))
            if g is None or g.supplier_id != s.id or g.het_hieu_luc:
                raise LoiNcc("Dòng giá không thuộc bạn", 404)
            x.gia_ncc_id, x.dich_vu, x.don_vi = g.id, g.dich_vu, g.don_vi
        else:
            x.dich_vu = str(d.get("dich_vu") or "").strip()[:200]
            x.don_vi = str(d.get("don_vi") or "").strip()[:30]
            if not x.dich_vu:
                raise LoiNcc("Ghi tên dịch vụ")
        sl = d.get("so_luong_mo")
        x.so_luong_mo = int(sl) if sl not in (None, "") else None
        x.ngay_khong_phuc_vu = str(d.get("ngay_khong_phuc_vu") or "").strip()[:300]
    elif loai == "thuc_don":
        nh_ids = {n.id for n in _nha_hang_cua(db, s)}
        if d.get("thuc_don_id"):
            t = db.get(ThucDonNhaHang, int(d["thuc_don_id"]))
            if t is None or t.nha_hang_id not in nh_ids:
                raise LoiNcc("Thực đơn không thuộc nhà hàng của bạn", 404)
            x.thuc_don_id, x.nha_hang_id, x.dich_vu = t.id, t.nha_hang_id, t.ten
        else:
            nid = int(d.get("nha_hang_id") or 0)
            if nid not in nh_ids:
                raise LoiNcc("Nhà hàng không thuộc bạn", 404)
            x.nha_hang_id, x.dich_vu = nid, str(d.get("dich_vu") or "").strip()[:200]
            if not x.dich_vu:
                raise LoiNcc("Ghi tên thực đơn")
        gte = d.get("gia_tre_em")
        x.gia_tre_em = float(gte) if gte not in (None, "") else None
    else:
        raise LoiNcc("Loại đề xuất không hợp lệ")
    db.add(x); db.flush()
    return x


def ds_de_xuat_cua(db: Session, s: Supplier) -> list[dict]:
    return [_ra_dx(db, x) for x in db.execute(select(DeXuatGiaNcc).where(DeXuatGiaNcc.supplier_id == s.id)
                                              .order_by(DeXuatGiaNcc.id.desc()).limit(100)).scalars()]


def ds_de_xuat_cho(db: Session) -> list[dict]:
    return [_ra_dx(db, x) for x in db.execute(select(DeXuatGiaNcc).where(DeXuatGiaNcc.trang_thai == "cho")
                                              .order_by(DeXuatGiaNcc.id)).scalars()]


def xu_ly_de_xuat(db: Session, u: User, xid: int, duyet: bool, ly_do: str = "") -> DeXuatGiaNcc:
    if u.role not in VAI_DUYET_GIA:
        raise LoiNcc("Chỉ TP Điều hành duyệt giá NCC", 403)
    x = db.get(DeXuatGiaNcc, xid)
    if x is None:
        raise LoiNcc("Không có đề xuất này", 404)
    if x.trang_thai != "cho":
        raise LoiNcc("Đề xuất đã xử lý", 409)
    x.xu_ly_boi, x.xu_ly_luc = u.username, datetime.now()
    if not duyet:
        if not (ly_do or "").strip():
            raise LoiNcc("Từ chối phải ghi lý do")
        x.trang_thai, x.ly_do = "tu_choi", ly_do.strip()[:2000]
    elif x.loai == "gia":
        cu = db.get(GiaNcc, x.gia_ncc_id) if x.gia_ncc_id else None
        g = GiaNcc(supplier_id=x.supplier_id, dich_vu=x.dich_vu, don_vi=x.don_vi, gia=x.gia, so_luong_mo=x.so_luong_mo,
                   tu_ngay=x.tu_ngay, den_ngay=x.den_ngay, ngay_khong_phuc_vu=x.ngay_khong_phuc_vu,
                   thay_cho_id=cu.id if cu else None, de_xuat_id=x.id, duyet_boi=u.username, luc=datetime.now())
        db.add(g)
        if cu is not None:
            cu.het_hieu_luc = True
        x.trang_thai = "duyet"
    else:
        if x.thuc_don_id:
            t = db.get(ThucDonNhaHang, x.thuc_don_id)
            t.gia_nguoi_lon, t.gia_tre_em = x.gia, x.gia_tre_em
            if x.tu_ngay:
                t.tu_ngay = x.tu_ngay
            if x.den_ngay:
                t.den_ngay = x.den_ngay
            t.sua_boi, t.sua_luc = u.username, datetime.now()
        else:
            db.add(ThucDonNhaHang(nha_hang_id=x.nha_hang_id, ten=x.dich_vu, gia_nguoi_lon=x.gia, gia_tre_em=x.gia_tre_em,
                                  tu_ngay=x.tu_ngay, den_ngay=x.den_ngay, mo_ta=x.ghi_chu, dang_ban=False,
                                  sua_boi=u.username, sua_luc=datetime.now()))
        x.trang_thai = "duyet"
    db.flush()
    R.audit(db, u.username, u.role, f"cong_ncc_de_xuat_{x.trang_thai}", f"de_xuat_gia_ncc:{x.id}",
            after={"gia": x.gia, "loai": x.loai})
    return x


# ====================================================================== công nợ (N07, N18)
def cong_no(db: Session, s: Supplier) -> dict:
    dong, phai_tra = [], 0.0
    for d in db.execute(select(ServiceOrder).where(ServiceOrder.supplier_id == s.id, ServiceOrder.status.in_(DON_NO))
                        .order_by(ServiceOrder.ngay_su_dung)).scalars():
        pr = db.get(PaymentRequest, d.payment_request_id) if d.payment_request_id else None
        da_chi = bool(pr and pr.status == "da_chi")
        con = 0.0 if da_chi else float(d.thanh_tien or 0)
        phai_tra += con
        dong.append({"code": d.code, "noi_dung": d.noi_dung, "ngay_su_dung": d.ngay_su_dung, "gia_tri": d.thanh_tien,
                     "phieu_chi": pr.code if pr else "", "phieu_trang_thai": pr.status if pr else "",
                     "da_chi": da_chi, "con": con, "ngay_den_han": d.ngay_den_han})
    from app.services import dat_ban as DB
    return {"vtd_phai_tra": phai_tra, "ncc_phai_tra": None, "dong": dong, "dat_ban_thu_ho": DB.thu_ho_ncc(db, s),
            "ghi_chu": "Chỉ tính đơn đã xác nhận / đã dùng. «Đã chi» = đề nghị chi gắn đơn đã ở bước đã chi. "
                       "Chiều nhà cung cấp phải trả Vietourist chưa có nguồn số liệu. Hai chiều không tự bù trừ."}


# ====================================================================== bản kê (N08–N09, N17)
def _ra_bk(db: Session, b: BanKeNcc, noi_bo: bool = False) -> dict:
    s = db.get(Supplier, b.supplier_id)
    dong = [{"id": x.id, "ma_don": x.ma_don, "noi_dung": x.noi_dung, "ngay": x.ngay, "gia_tri": x.gia_tri,
             "ncc_gia_tri": x.ncc_gia_tri, "ncc_ghi_chu": x.ncc_ghi_chu, "tra_loi": x.tra_loi}
            for x in db.execute(select(DongBanKeNcc).where(DongBanKeNcc.ban_ke_id == b.id).order_by(DongBanKeNcc.id)).scalars()]
    r = {"id": b.id, "ma": b.ma, "ky": b.ky, "trang_thai": b.trang_thai, "trang_thai_ten": TRANG_THAI_BAN_KE.get(b.trang_thai, b.trang_thai),
         "tong": b.tong, "lap_luc": b.lap_luc, "xac_nhan_luc": b.xac_nhan_luc, "dong": dong,
         "ncc": {"id": s.id, "code": s.code, "ten": s.ten} if s else None}
    if noi_bo:
        r["lap_boi"] = b.lap_boi
    return r


def lap_ban_ke(db: Session, u: User, ncc_id: int, ky: str) -> BanKeNcc:
    if u.role not in VAI_KE_TOAN:
        raise LoiNcc("Chỉ Kế toán lập bản kê", 403)
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", ky or ""):
        raise LoiNcc("Kỳ dạng YYYY-MM")
    s = db.get(Supplier, ncc_id)
    if s is None:
        raise LoiNcc("Không có NCC này", 404)
    if db.execute(select(BanKeNcc).where(BanKeNcc.supplier_id == s.id, BanKeNcc.ky == ky,
                                         BanKeNcc.trang_thai != "da_xac_nhan")).scalars().first():
        raise LoiNcc("NCC này đã có bản kê kỳ này chưa khóa — xử lý bản kê ấy trước", 409)
    y, m = map(int, ky.split("-"))
    tu = date(y, m, 1)
    den = date(y + (m == 12), m % 12 + 1, 1)
    don = list(db.execute(select(ServiceOrder).where(ServiceOrder.supplier_id == s.id, ServiceOrder.status.in_(DON_NO),
                                                     ServiceOrder.ngay_su_dung >= tu, ServiceOrder.ngay_su_dung < den)
                          .order_by(ServiceOrder.ngay_su_dung)).scalars())
    if not don:
        raise LoiNcc("Kỳ này không có đơn đã xác nhận / đã dùng của NCC này")
    so = (db.execute(select(func.count(BanKeNcc.id)).where(BanKeNcc.supplier_id == s.id, BanKeNcc.ky == ky)).scalar() or 0)
    b = BanKeNcc(ma=f"BK-{s.code}-{ky.replace('-', '')[2:]}" + (f"-{so + 1}" if so else ""), supplier_id=s.id, ky=ky,
                 tong=sum(float(d.thanh_tien or 0) for d in don), lap_boi=u.username, lap_luc=datetime.now())
    db.add(b); db.flush()
    db.add_all([DongBanKeNcc(ban_ke_id=b.id, service_order_id=d.id, ma_don=d.code, noi_dung=d.noi_dung, ngay=d.ngay_su_dung,
                             gia_tri=float(d.thanh_tien or 0)) for d in don])
    db.flush()
    R.audit(db, u.username, u.role, "cong_ncc_lap_ban_ke", f"ban_ke_ncc:{b.ma}", after={"tong": b.tong, "so_dong": len(don)})
    return b


def ds_ban_ke_cua(db: Session, s: Supplier) -> list[dict]:
    return [_ra_bk(db, b) for b in db.execute(select(BanKeNcc).where(BanKeNcc.supplier_id == s.id)
                                              .order_by(BanKeNcc.id.desc()).limit(36)).scalars()]


def ds_ban_ke(db: Session) -> list[dict]:
    return [_ra_bk(db, b, True) for b in db.execute(select(BanKeNcc).order_by(BanKeNcc.id.desc()).limit(200)).scalars()]


def _bk_cua(db: Session, s: Supplier, bid: int) -> BanKeNcc:
    b = db.get(BanKeNcc, bid)
    if b is None or b.supplier_id != s.id:
        raise LoiNcc("Không có bản kê này", 404)
    return b


def xac_nhan_ban_ke(db: Session, tk: TaiKhoanNgoai, s: Supplier, bid: int) -> BanKeNcc:
    b = _bk_cua(db, s, bid)
    if b.trang_thai == "da_xac_nhan":
        raise LoiNcc("Bản kê đã khóa", 409)
    mo = db.execute(select(DongBanKeNcc).where(DongBanKeNcc.ban_ke_id == b.id, DongBanKeNcc.ncc_gia_tri.is_not(None),
                                               DongBanKeNcc.tra_loi == "")).scalars().first()
    if mo is not None:
        raise LoiNcc("Còn dòng chênh lệch chờ Kế toán trả lời — chưa xác nhận được", 409)
    b.trang_thai, b.xac_nhan_tk_id, b.xac_nhan_luc = "da_xac_nhan", tk.id, datetime.now()
    db.flush()
    R.audit(db, f"cong:ncc-{tk.id}", "doi_tac", "cong_ncc_xac_nhan_ban_ke", f"ban_ke_ncc:{b.ma}", after={"tong": b.tong})
    return b


def bao_chenh_lech(db: Session, tk: TaiKhoanNgoai, s: Supplier, bid: int, dong_id: int, gia_tri, ghi_chu: str) -> BanKeNcc:
    b = _bk_cua(db, s, bid)
    if b.trang_thai == "da_xac_nhan":
        raise LoiNcc("Bản kê đã khóa — sai thì đề nghị lập bản kê điều chỉnh", 409)
    x = db.get(DongBanKeNcc, dong_id)
    if x is None or x.ban_ke_id != b.id:
        raise LoiNcc("Không có dòng này", 404)
    if not (ghi_chu or "").strip():
        raise LoiNcc("Ghi căn cứ chênh lệch")
    x.ncc_gia_tri = float(gia_tri) if gia_tri not in (None, "") else x.gia_tri
    x.ncc_ghi_chu, x.tra_loi = ghi_chu.strip()[:2000], ""
    b.trang_thai = "co_chenh_lech"
    db.flush()
    return b


def tra_loi_chenh_lech(db: Session, u: User, dong_id: int, tra_loi: str) -> BanKeNcc:
    if u.role not in VAI_KE_TOAN:
        raise LoiNcc("Chỉ Kế toán trả lời chênh lệch", 403)
    x = db.get(DongBanKeNcc, dong_id)
    if x is None:
        raise LoiNcc("Không có dòng này", 404)
    if not (tra_loi or "").strip():
        raise LoiNcc("Ghi nội dung trả lời")
    x.tra_loi = tra_loi.strip()[:2000]
    b = db.get(BanKeNcc, x.ban_ke_id)
    con = db.execute(select(DongBanKeNcc).where(DongBanKeNcc.ban_ke_id == b.id, DongBanKeNcc.ncc_gia_tri.is_not(None),
                                                DongBanKeNcc.tra_loi == "")).scalars().first()
    if con is None and b.trang_thai == "co_chenh_lech":
        b.trang_thai = "cho_ncc"
    db.flush()
    return b


# ====================================================================== đề nghị (N10)
def _ra_dn(db: Session, x: DeNghiNcc, noi_bo: bool = False) -> dict:
    r = {"id": x.id, "ma": x.ma, "loai": x.loai, "loai_ten": LOAI_DE_NGHI.get(x.loai, x.loai),
         "bo_phan": "Kế toán" if x.bo_phan == "ketoan" else "Điều hành", "so_tien": x.so_tien, "noi_dung": x.noi_dung,
         "trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_DE_NGHI.get(x.trang_thai, x.trang_thai),
         "tra_loi": x.tra_loi, "xu_ly_luc": x.xu_ly_luc, "luc": x.luc, "co_tep": x.attachment_id is not None}
    if noi_bo:
        s = db.get(Supplier, x.supplier_id)
        r.update({"ncc": s.ten if s else "", "ncc_code": s.code if s else "", "xu_ly_boi": x.xu_ly_boi, "bo_phan_ma": x.bo_phan})
    return r


def gui_de_nghi(db: Session, tk: TaiKhoanNgoai, s: Supplier, loai: str, so_tien, noi_dung: str,
                ten_tep: str = "", kieu: str = "", data: bytes | None = None) -> DeNghiNcc:
    if loai not in LOAI_DE_NGHI:
        raise LoiNcc("Loại đề nghị không hợp lệ")
    noi_dung = (noi_dung or "").strip()
    if len(noi_dung) < 5:
        raise LoiNcc("Ghi nội dung / căn cứ")
    st = float(so_tien) if so_tien not in (None, "") else None
    if st is not None and st < 0:
        raise LoiNcc("Số tiền không hợp lệ")
    mo = db.execute(select(func.count(DeNghiNcc.id)).where(DeNghiNcc.supplier_id == s.id,
                                                           DeNghiNcc.trang_thai.in_(("moi", "dang_xu_ly")))).scalar() or 0
    if mo >= 20:
        raise LoiNcc("Đang có nhiều đề nghị chưa xử lý — chờ phản hồi rồi gửi tiếp", 429)
    so = (db.execute(select(func.max(DeNghiNcc.id))).scalar() or 0) + 1
    x = DeNghiNcc(ma=f"DN-NCC-{so:04d}", supplier_id=s.id, tai_khoan_id=tk.id, loai=loai, bo_phan=BO_PHAN_DE_NGHI[loai],
                  so_tien=st, noi_dung=noi_dung[:4000], luc=datetime.now())
    if data:
        try:
            a, _ = AT.dinh_kem(db, "nha_cung_cap", s.code, ten_tep, data, kieu=kieu, loai="chung_tu",
                               mo_ta=f"Đề nghị NCC qua cổng · {x.ma}", boi=f"cong:ncc-{tk.id}")
        except ValueError as ex:
            raise LoiNcc(str(ex))
        x.attachment_id = a.id
    db.add(x); db.flush()
    return x


def ds_de_nghi_cua(db: Session, s: Supplier) -> list[dict]:
    return [_ra_dn(db, x) for x in db.execute(select(DeNghiNcc).where(DeNghiNcc.supplier_id == s.id)
                                              .order_by(DeNghiNcc.id.desc()).limit(100)).scalars()]


def ds_de_nghi(db: Session) -> list[dict]:
    return [_ra_dn(db, x, True) for x in db.execute(select(DeNghiNcc).order_by(DeNghiNcc.id.desc()).limit(300)).scalars()]


def xu_ly_de_nghi(db: Session, u: User, did: int, trang_thai: str, tra_loi: str) -> DeNghiNcc:
    x = db.get(DeNghiNcc, did)
    if x is None:
        raise LoiNcc("Không có đề nghị này", 404)
    duoc = VAI_KE_TOAN if x.bo_phan == "ketoan" else VAI_DIEU_HANH
    if u.role not in duoc:
        raise LoiNcc(f"Đề nghị này do {'Kế toán' if x.bo_phan == 'ketoan' else 'Điều hành'} xử lý", 403)
    if trang_thai not in ("dang_xu_ly", "xong", "tu_choi"):
        raise LoiNcc("Trạng thái không hợp lệ")
    if x.trang_thai in ("xong", "tu_choi"):
        raise LoiNcc("Đề nghị đã đóng", 409)
    if not (tra_loi or "").strip():
        raise LoiNcc("Ghi nội dung trả lời — NCC đọc được")
    x.trang_thai, x.tra_loi, x.xu_ly_boi, x.xu_ly_luc = trang_thai, tra_loi.strip()[:2000], u.username, datetime.now()
    db.flush()
    return x


# ====================================================================== hồ sơ, ngân hàng, thành viên (N11–N12)
def ho_so_tep(db: Session, s: Supplier) -> list[dict]:
    return [{"id": a.id, "ten_tep": a.ten_tep, "luc": a.luc, "mo_ta": a.mo_ta}
            for a in db.execute(select(Attachment).where(Attachment.doi_tuong == "nha_cung_cap", Attachment.doi_tuong_id == s.code,
                                                         Attachment.thu_hoi.is_(False)).order_by(Attachment.id.desc()).limit(50)).scalars()]


def gui_ho_so(db: Session, tk: TaiKhoanNgoai, s: Supplier, ten_tep: str, kieu: str, data: bytes, mo_ta: str) -> None:
    if not data:
        raise LoiNcc("Chọn tệp")
    try:
        AT.dinh_kem(db, "nha_cung_cap", s.code, ten_tep, data, kieu=kieu, loai="hop_dong",
                    mo_ta=f"NCC gửi qua cổng · {(mo_ta or '')[:150]}", boi=f"cong:ncc-{tk.id}")
    except ValueError as ex:
        raise LoiNcc(str(ex))


def ngan_hang(db: Session, s: Supplier) -> dict:
    cho = db.execute(select(SupplierBankChange).where(SupplierBankChange.supplier_id == s.id,
                                                      SupplierBankChange.status == "cho_xac_nhan")).scalars().first()
    return {"so_tai_khoan": _che(s.so_tai_khoan), "ngan_hang": s.ngan_hang, "chu_tai_khoan": s.chu_tai_khoan,
            "dang_cho_doi": cho is not None, "doi_luc": cho.de_nghi_luc if cho else None}


def doi_tai_khoan(db: Session, tk: TaiKhoanNgoai, s: Supplier, so_tk: str, ngan_hang_: str, chu_tk: str, ly_do: str,
                  ten_tep: str, kieu: str, data: bytes | None) -> None:
    """Đi đúng quy trình đổi TK HAI NGƯỜI: tạo yêu cầu chờ xác nhận; số TK đang hiệu lực KHÔNG đổi."""
    if not data:
        raise LoiNcc("Kèm văn bản đề nghị đổi tài khoản (PDF / ảnh) — đổi tài khoản không văn bản là đường vào gian lận")
    try:
        a, _ = AT.dinh_kem(db, "nha_cung_cap", s.code, ten_tep, data, kieu=kieu, loai="chung_tu",
                           mo_ta="Văn bản đề nghị đổi tài khoản — NCC gửi qua cổng", boi=f"cong:ncc-{tk.id}")
        SV.de_nghi_doi_tk(db, s, {"so_tk_moi": so_tk, "ngan_hang_moi": ngan_hang_, "chu_tk_moi": chu_tk,
                                  "ly_do": (ly_do or "")[:300], "chung_tu": f"Cổng NCC · tệp #{a.id} {a.ten_tep}"[:200]},
                          f"cong:ncc-{tk.id}")
    except ValueError as ex:
        raise LoiNcc(str(ex))


def thanh_vien(db: Session, s: Supplier) -> list[dict]:
    return [{"ho_ten": t.ho_ten, "lien_he": _che(t.dien_thoai, 3) if t.dien_thoai else re.sub(r"(?<=.).(?=[^@]*@)", "•", t.email or ""),
             "trang_thai": t.trang_thai}
            for t in db.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.ncc_id == s.id)).scalars()]


# ====================================================================== học liệu (N13)
def _ra_hl(h: HocLieuDoiTac) -> dict:
    return {"id": h.id, "tieu_de": h.tieu_de, "nhom": h.nhom, "nhom_ten": NHOM_HOC_LIEU.get(h.nhom, h.nhom),
            "danh_cho": h.danh_cho or [], "hien": h.hien, "luc": h.luc, "dang_boi": h.dang_boi}


def hoc_lieu_cho(db: Session, loai_doi_tac: str) -> list[dict]:
    return [_ra_hl(h) for h in db.execute(select(HocLieuDoiTac).where(HocLieuDoiTac.hien.is_(True))
                                          .order_by(HocLieuDoiTac.id.desc())).scalars() if loai_doi_tac in (h.danh_cho or [])]


def tep_hoc_lieu(db: Session, hid: int, loai_doi_tac: str | None) -> tuple[bytes, Attachment]:
    h = db.get(HocLieuDoiTac, hid)
    if h is None or (loai_doi_tac is not None and (not h.hien or loai_doi_tac not in (h.danh_cho or []))):
        raise LoiNcc("Không có học liệu này", 404)
    a = db.get(Attachment, h.attachment_id)
    try:
        return AT.doc(db, a), a
    except Exception as ex:
        raise LoiNcc(str(ex), 503)


def dang_hoc_lieu(db: Session, u: User, tieu_de: str, nhom: str, danh_cho: list[str], ten_tep: str, kieu: str, data: bytes) -> HocLieuDoiTac:
    if u.role not in VAI_HOC_LIEU:
        raise LoiNcc("Chỉ Điều hành / Marketing đưa học liệu", 403)
    if nhom not in NHOM_HOC_LIEU:
        raise LoiNcc("Nhóm không hợp lệ")
    dc = [x for x in danh_cho if x in DANH_CHO]
    if not dc:
        raise LoiNcc("Chọn ít nhất một nhóm đối tác")
    if not (tieu_de or "").strip():
        raise LoiNcc("Thiếu tên tài liệu")
    try:
        a, _ = AT.dinh_kem(db, "noi_dung", "hoc-lieu-doi-tac", ten_tep, data, kieu=kieu, loai="chung_tu",
                           mo_ta=f"Học liệu đối tác · {tieu_de[:120]}", boi=u.username)
    except ValueError as ex:
        raise LoiNcc(str(ex))
    h = HocLieuDoiTac(tieu_de=tieu_de.strip()[:200], nhom=nhom, danh_cho=dc, attachment_id=a.id, dang_boi=u.username, luc=datetime.now())
    db.add(h); db.flush()
    return h


def go_hoc_lieu(db: Session, u: User, hid: int) -> None:
    if u.role not in VAI_HOC_LIEU:
        raise LoiNcc("Chỉ Điều hành / Marketing gỡ học liệu", 403)
    h = db.get(HocLieuDoiTac, hid)
    if h is None:
        raise LoiNcc("Không có học liệu này", 404)
    h.hien, h.go_boi = False, u.username
    db.flush()


def ds_hoc_lieu(db: Session) -> list[dict]:
    return [_ra_hl(h) for h in db.execute(select(HocLieuDoiTac).order_by(HocLieuDoiTac.id.desc())).scalars()]


# ====================================================================== nhà hàng: đơn đặt bàn (N15–N16)
def don_dat_ban(db: Session, s: Supplier) -> list[dict]:
    nh = {n.id: n for n in _nha_hang_cua(db, s)}
    if not nh:
        return []
    from app.services import dat_ban as DB
    ra = []
    ys = db.execute(select(YeuCauKhach).where(YeuCauKhach.loai == "nha_hang", YeuCauKhach.nha_hang_id.in_(list(nh)))
                    .order_by(YeuCauKhach.ngay_mong_muon.desc().nullslast(), YeuCauKhach.id.desc()).limit(200)).scalars().all()
    dons = DB.don_cua_yeu_cau(db, [y.id for y in ys])
    for y in ys:
        td = db.get(ThucDonNhaHang, y.thuc_don_id) if y.thuc_don_id else None
        don = dons.get(y.id)
        ra.append({**(DB.ra_ncc(db, don) if don else {}),"id": y.id, "ma": f"YC-{y.id:04d}", "nha_hang": nh[y.nha_hang_id].ten, "thuc_don": td.ten if td else "",
                   "ngay": y.ngay_mong_muon, "gio": y.gio_den, "nguoi_lon": max(0, (y.so_khach or 0) - (y.tre_em or 0)),
                   "tre_em": y.tre_em, "tam_tinh": y.tam_tinh, "ghi_chu": y.ghi_chu, "trang_thai": y.nha_hang_tt or "cho",
                   "trang_thai_ten": NHA_HANG_TT.get(y.nha_hang_tt or "cho"), "ghi_chu_nh": y.nha_hang_ghi_chu})
    return ra


def xu_ly_dat_ban(db: Session, tk: TaiKhoanNgoai, s: Supplier, yid: int, nhan: bool, ghi_chu: str) -> None:
    nh = {n.id for n in _nha_hang_cua(db, s)}
    y = db.get(YeuCauKhach, yid)
    if y is None or y.loai != "nha_hang" or y.nha_hang_id not in nh:
        raise LoiNcc("Không có đơn đặt bàn này", 404)
    if (y.nha_hang_tt or "cho") != "cho":
        raise LoiNcc("Đơn đã được xử lý", 409)
    if not nhan and not (ghi_chu or "").strip():
        raise LoiNcc("Từ chối phải ghi lý do")
    # DT-2: đơn đặt bàn có thanh toán đổi trạng thái theo (nhận → chờ khách trả; từ chối → không phải trả).
    from app.services import dat_ban as DB
    try:
        DB.nha_hang_xu_ly(db, y, nhan)
    except DB.LoiDatBan as ex:
        raise LoiNcc(str(ex), ex.status)
    y.nha_hang_tt, y.nha_hang_ghi_chu, y.nha_hang_luc = ("nhan" if nhan else "tu_choi"), (ghi_chu or "").strip()[:1000], datetime.now()
    db.flush()


# ====================================================================== bàn làm việc (N01)
def ban_lam_viec(db: Session, s: Supplier) -> dict:
    don = ds_don(db, s)
    cn = cong_no(db, s)
    bk = ds_ban_ke_cua(db, s)
    return {"ncc": _ho_so(s), "don_cho": sum(1 for d in don if d["status"] == "da_gui"),
            "de_xuat_cho": db.execute(select(func.count(DeXuatGiaNcc.id)).where(DeXuatGiaNcc.supplier_id == s.id,
                                                                                DeXuatGiaNcc.trang_thai == "cho")).scalar() or 0,
            "de_nghi_mo": db.execute(select(func.count(DeNghiNcc.id)).where(DeNghiNcc.supplier_id == s.id,
                                                                           DeNghiNcc.trang_thai.in_(("moi", "dang_xu_ly")))).scalar() or 0,
            "vtd_phai_tra": cn["vtd_phai_tra"], "ncc_phai_tra": None,
            "ban_ke_cho": next((b for b in bk if b["trang_thai"] != "da_xac_nhan"), None),
            "la_nha_hang": bool(_nha_hang_cua(db, s)),
            "la_khach_san": _co_khach_san(db, s),   # KS-15: tab «Đánh giá khách sạn»
            "dat_ban_cho": sum(1 for x in don_dat_ban(db, s) if x["trang_thai"] == "cho")}
