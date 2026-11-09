"""DT-2 · Đặt bàn nhà hàng có thanh toán — xem luật ở `app/models/dat_ban.py`.

Ai làm gì:
  · Người đặt (khách, cổ đông đã xác minh, đại lý, CTV đã nối): gửi đơn, trả trước (QR / thẻ), hủy.
  · Nhà hàng (cổng NCC): nhận / từ chối bàn (NCC-1), báo khách đã dùng kèm bill, báo khách không đến.
  · Kế toán: xác nhận tiền QR, đối soát tiền thẻ, chốt doanh số, ghi đã hoàn tiền.
  · Sales: xác nhận số hoàn; TP / GĐ Kinh doanh hủy miễn phạt (có lý do).

Không có ô nào cho trình duyệt gửi số tiền: tạm tính, số phải trả, số giữ / hoàn đều do máy tính từ giá đã
duyệt và tham số; doanh số D06 là số Kế toán gõ.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cong_khach import YeuCauKhach
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.models.dat_ban import (CACH_TT, HOAN_TT, KENH, NGUON, TRANG_THAI, TT_DA_TRA, TT_THANH_TOAN, DonDatBan,
                                ThanhToanDatBan)
from app.models.nha_hang import NhaHang, ThucDonNhaHang
from app.models.payments import BankTransaction
from app.services import onepay as OP
from app.services import sepay_pg as SP
from app.services import rules as R

VAI_KE_TOAN = ("ketoan",)
VAI_SALES = ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "sales_admin")
VAI_MIEN_PHAT = ("tp_kd", "gd_kd", "chutich", "tgd")
VAI_XEM = tuple(dict.fromkeys(("chutich", "tgd", "bks", "robot_ks") + VAI_KE_TOAN + VAI_SALES))
MA_RE = re.compile(r"NH\d{8}")
DON_TOI_DA_NGAY = 10
TRANG_THAI_HUY_DUOC = ("cho_nhan", "cho_tra", "da_giu", "het_han")
DOI_DUOC = ("cho_nhan", "cho_tra", "da_giu")
TK_TIEN, TK_THU_HO, TK_PHI = "1121", "3388", "6428"      # DT-3: đại lý thu hộ nhà hàng; phí thẻ như phí ngân hàng
# KS-16b: voucher VTD Rewards — VTD chịu thay khách.
# ĐỢT TKC-5 08/11/2026: `641` là tài khoản TỔNG HỢP (sáu con). Lấy ở bảng khai
# `services/tk_chi_tiet.py` — một hằng số ở đây là một nguồn thứ hai cho cùng một luật.


def _co_the_tra(d: DonDatBan, tra: int) -> bool:
    """Trả trước khi nhà hàng đã nhận bàn; đã giữ bàn mà thêm khách thì trả được phần trả trước thêm."""
    return d.trang_thai in ("cho_tra", "da_giu") and tra - int(d.so_hoan or 0) < int(d.phai_tra_truoc)


class LoiDatBan(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def tham_so(db: Session) -> dict:
    g = lambda k: int(R.get_param(db, k))  # noqa: E731
    return {"doan_tu": g("dat_ban_doan_tu"), "coc_le": g("dat_ban_coc_le_pct"), "coc_doan": g("dat_ban_coc_doan_pct"),
            "han_tra_gio": g("dat_ban_han_tra_gio"), "mien_phi_gio": g("dat_ban_huy_mien_phi_gio"),
            "gan_gio": g("dat_ban_huy_gan_gio"), "phat": g("dat_ban_phat_pct"), "phat_doan_gan": g("dat_ban_phat_doan_gan_pct")}


def _nghin(x: float) -> int:
    """Làm tròn LÊN tới nghìn đồng."""
    x = int(round(x))
    return ((x + 999) // 1000) * 1000


def gio_an(d: DonDatBan) -> datetime:
    h, m = (int(v) for v in d.gio.split(":"))
    return datetime.combine(d.ngay, datetime.min.time()).replace(hour=h, minute=m)


def da_tra(db: Session, d: DonDatBan) -> int:
    v = db.execute(select(func.coalesce(func.sum(ThanhToanDatBan.so_tien), 0)).where(
        ThanhToanDatBan.don_id == d.id, ThanhToanDatBan.trang_thai.in_(TT_DA_TRA))).scalar()
    return int(round(float(v or 0)))


def _ma_moi(db: Session, now: datetime) -> str:
    dau = f"NH{now:%y%m}"
    n = db.execute(select(func.count(DonDatBan.id)).where(DonDatBan.ma.like(dau + "%"))).scalar() or 0
    return f"{dau}{n + 1:04d}"


def la_doan(ts: dict, td: dict, nguoi: int) -> bool:
    return nguoi >= ts["doan_tu"] and td.get("loai") != "goi_mon"


def phai_tra(ts: dict, tam: int, doan: bool, cach: str) -> tuple[int, int]:
    """(tỷ lệ %, số phải trả trước)."""
    if cach == "du":
        return 100, int(tam)
    pct = ts["coc_doan"] if doan else ts["coc_le"]
    return pct, min(int(tam), _nghin(tam * pct / 100))


def tra_truoc(ts: dict, td: dict, tam: int, doan: bool, cach: str) -> tuple[int, int]:
    """P1-03: gói gọi món có cọc cố định mỗi khách → trả trước = cọc × khách + phụ thu; còn lại theo luật 28/10."""
    co_dinh = int((td.get("tinh") or {}).get("coc_co_dinh") or 0)
    if co_dinh:
        truoc = min(int(tam), co_dinh)
        return (min(100, max(1, round(truoc * 100 / tam))) if tam else 100), truoc
    return phai_tra(ts, tam, doan, cach)


# ====================================================================== tạo đơn
def _nguoi_dat(db: Session, tk: TaiKhoanNgoai):
    """(nguon, doi_tac | None). Chặn tài khoản không được đặt."""
    from app.services import cong_khach as K
    from app.services import doi_tac_cong as DT
    if tk.loai == "doi_tac":
        try:
            dt = DT.doi_tac_cua(db, tk)
        except DT.LoiDoiTac as ex:
            raise LoiDatBan(str(ex), 403)
        return ("ctv" if DT.la_ctv(dt) else "dai_ly"), dt
    try:
        K.la_khach_hoac_co_dong(tk)
    except K.LoiKhach as ex:
        raise LoiDatBan(str(ex), 403)
    return ("co_dong" if tk.loai == "co_dong" else "khach_hang"), None


TT_CHUA_MO = "Thanh toán trực tuyến chưa mở cho nhà hàng này"


def _mo_tt(db: Session, n) -> bool:
    from app.services import nha_hang as NH
    return NH.mo_thanh_toan_nh(db, n)


def _kiem_mo_tt(db: Session, nha_hang_id: int) -> None:
    """AT-2 (Chủ tịch 01/11/2026): mọi đơn đặt bàn đều trả trước (cọc / đủ) → chỉ nhận đơn và nhận tiền khi công tắc
    chung VÀ công tắc của nhà hàng đều bật (TP Điều hành bật trên VTOS). Chưa mở: không tạo đơn, không giữ bàn."""
    from app.models.nha_hang import NhaHang
    from app.services import nha_hang as NH
    n = db.get(NhaHang, nha_hang_id)
    if n is None or not NH.mo_thanh_toan_nh(db, n):
        raise LoiDatBan(TT_CHUA_MO, 409)


def tao(db: Session, tk: TaiKhoanNgoai, d: dict, now: datetime | None = None) -> DonDatBan:
    from app.services import nha_hang as NH
    from app.services.leads import upsert_lead
    from app.services import cong_khach as K
    now = now or datetime.now()
    nguon, dt = _nguoi_dat(db, tk)
    cach = d.get("cach_tt")
    if cach not in CACH_TT:
        raise LoiDatBan("Chọn cách thanh toán: cọc hoặc trả đủ")
    if not d.get("dong_y_chinh_sach"):
        raise LoiDatBan("Đánh dấu ô đồng ý chính sách thanh toán và hủy bàn")
    nl, te = int(d.get("nguoi_lon") or 0), int(d.get("tre_em") or 0)
    try:
        ngay = d.get("ngay")
        ngay = ngay if isinstance(ngay, date) else (date.fromisoformat(ngay) if ngay else None)
        o, td, tam = NH.kiem_dat_ban(db, int(d.get("nha_hang_id") or 0), int(d.get("thuc_don_id") or 0), ngay,
                                     str(d.get("gio") or ""), nl, te, now.date(), tuoi=d.get("tuoi_tre"),
                                     chon_phu_thu=d.get("phu_thu_chon"), bat_tuoi=True)
    except (NH.LoiNhaHang, ValueError) as ex:
        raise LoiDatBan(str(ex))
    tam = int(round(tam))
    if tam <= 0:
        raise LoiDatBan("Gói này chưa có giá — gửi yêu cầu để Sales báo giá")
    ct = td["tinh"]
    if ct["coc_co_dinh"]:
        cach = "coc"                                               # P1-03: gọi món cọc cố định — không có «trả đủ»
    _kiem_mo_tt(db, o["id"])                                       # AT-2
    ten_khach = (d.get("ten_khach") or "").strip()[:120]
    sdt = K.norm_phone(d.get("dien_thoai") or ("" if dt else tk.dien_thoai))
    if dt is not None:
        if not ten_khach:
            raise LoiDatBan("Ghi tên khách")
        if not d.get("dong_y_khach"):
            raise LoiDatBan("Đánh dấu ô: khách đã đồng ý để bạn chuyển thông tin cho Vietourist")
    else:
        ten_khach = ten_khach or (tk.ho_ten or "")
    if len(sdt) != 10 or not sdt.startswith("0"):
        raise LoiDatBan("Ghi số điện thoại khách (10 số)")
    trong_ngay = db.execute(select(func.count(DonDatBan.id)).where(DonDatBan.tai_khoan_id == tk.id,
                                                                   DonDatBan.tao_luc >= now - timedelta(days=1))).scalar() or 0
    if trong_ngay >= DON_TOI_DA_NGAY:
        raise LoiDatBan("Đã gửi nhiều đơn đặt bàn trong 24 giờ — vui lòng chờ hoặc gọi Sales", 429)
    ts = tham_so(db)
    doan = la_doan(ts, td, nl + te)
    pct, truoc = tra_truoc(ts, td, tam, doan, cach)
    ma = _ma_moi(db, now)
    ghi = (d.get("ghi_chu") or "").strip()[:1000]
    noi_dung = f"{o['ten']} · {td['ten']} · {ngay:%d/%m/%Y} {d['gio']} · {nl} NL + {te} TE"
    if ct["phu_thu"]:
        ghi = (ghi + (" · " if ghi else "") + "Phụ thu: " + "; ".join(f"{x['ten']} {x['so_tien']:,} đ" for x in ct["phu_thu"]).replace(",", "."))[:1000]
    if d.get("tuoi_tre") and te:
        ghi = (ghi + (" · " if ghi else "") + "Tuổi trẻ: " + ", ".join(str(int(x)) for x in d["tuoi_tre"]))[:1000]
    # Lead đi đúng cửa sẵn có của Kinh doanh. Đơn qua đối tác: kênh CTV giới thiệu, giao bàn Sales Admin lẻ.
    if dt is not None:
        from app.services import doi_tac_cong as DT
        lead, _ = upsert_lead(db, "cong_doi_tac", {"phone": sdt, "name": ten_khach, "channel": DT.KENH_CTV,
                                                  "received_at": now.isoformat(), "interest": noi_dung[:200]})
        sa = DT.sale_admin_le(db)
        if sa is not None and lead.sales_id is None:
            lead.sales_id = sa.id
        nhan = f"{NGUON[nguon]} {dt.ten} ({dt.ma})"
    else:
        lead, _ = upsert_lead(db, "cong_khach", {"phone": sdt, "name": ten_khach, "channel": K.KENH_LEAD,
                                                "received_at": now.isoformat(), "interest": noi_dung[:200]})
        nhan = "Cổng cổ đông" if nguon == "co_dong" else "Cổng khách hàng"
    dong = (f"[{nhan} {now:%d/%m %H:%M}] Đặt bàn {ma}: {noi_dung} · tạm tính {tam:,} đ · {CACH_TT[cach]} {pct}%".replace(",", ".")
            + (f" · {ghi}" if ghi else ""))
    cu = (lead.note or "").strip()
    lead.note = (((cu + "\n") if cu else "") + dong)[-2000:]
    yc = YeuCauKhach(tai_khoan_id=tk.id, loai="nha_hang", ten_tour=noi_dung[:200], so_khach=nl + te, ngay_mong_muon=ngay,
                     dien_thoai=sdt, ghi_chu=ghi, lead_id=lead.id, nha_hang_id=o["id"], thuc_don_id=td["id"], gio_den=d["gio"],
                     tre_em=te, tam_tinh=tam, ten_khach=ten_khach if dt is not None else "", tao_luc=now)
    db.add(yc); db.flush()
    don = DonDatBan(ma=ma, yeu_cau_id=yc.id, tai_khoan_id=tk.id, nguon=nguon, doi_tac_id=dt.id if dt else None,
                    nha_hang_id=o["id"], thuc_don_id=td["id"], ngay=ngay, gio=d["gio"], nguoi_lon=nl, tre_em=te,
                    ten_khach=ten_khach, dien_thoai=sdt, la_doan=doan, cach_tt=cach, ty_le_coc=pct, tam_tinh=tam,
                    phai_tra_truoc=truoc, trang_thai="cho_nhan", tao_luc=now,
                    phu_thu=[{"i": x["i"], "ten": x["ten"], "so_tien": x["so_tien"]} for x in ct["phu_thu"]] or None,
                    tuoi_tre=[int(x) for x in d["tuoi_tre"]] if d.get("tuoi_tre") and te else None,
                    han_phan_hoi=(now + timedelta(hours=int(td["han_phan_hoi_gio"]))) if td.get("han_phan_hoi_gio") else None)
    db.add(don); db.flush()
    R.audit(db, f"cong:{tk.id}", tk.loai, "dat_ban_tao", f"dat_ban:{ma}", after={"tam_tinh": tam, "cach": cach, "pct": pct,
                                                                                   "nguon": nguon})
    db.commit(); db.refresh(don)
    return don


# ====================================================================== trạng thái
def cap_nhat(db: Session, d: DonDatBan, now: datetime | None = None) -> DonDatBan:
    """Chuyển trạng thái theo thời gian / tiền: chờ trả quá hạn → hết hạn; đã trả đủ → giữ bàn."""
    now = now or datetime.now()
    if d.trang_thai == "cho_tra":
        if da_tra(db, d) - int(d.so_hoan or 0) >= int(d.phai_tra_truoc):
            d.trang_thai = "da_giu"
        elif d.han_tra and now > d.han_tra:
            d.trang_thai = "het_han"
            _vc_doi_chieu(db, d, now)
    return d


# ====================================================================== KS-16b · voucher VTD Rewards
def _vc_doi_chieu(db: Session, d: DonDatBan, now: datetime) -> None:
    if d.voucher_id:
        from app.services import rewards as RW
        RW.doi_chieu_voucher_db(db, d, now)


def vc_con_giu(db: Session, d: DonDatBan) -> int:
    """Số voucher đang tính vào phần trả trước (voucher chưa trả điểm lại)."""
    if not d.voucher_id:
        return 0
    from app.models.rewards import VoucherRewards
    v = db.get(VoucherRewards, d.voucher_id)
    return int(d.giam_voucher or 0) if v is not None and v.trang_thai == "da_dung" and v.dat_ban_id == d.id else 0


def khuyen_mai(db: Session, d: DonDatBan) -> int:
    """Phần voucher VTD chịu, thuộc nhà hàng: đơn đang chạy → voucher đang giữ; đơn đã xong / hủy → `km_vtd` chốt lúc đó."""
    if d.trang_thai in ("cho_nhan", "cho_tra", "da_giu"):
        return vc_con_giu(db, d)
    return int(d.km_vtd or 0) if vc_con_giu(db, d) else 0


def _km_khi_dong(db: Session, d: DonDatBan, phat_tong: int) -> None:
    """Đơn kết thúc không hoàn đồng nào mà voucher dùng hẳn: nhà hàng được phần phạt còn thiếu, tối đa bằng voucher."""
    g = vc_con_giu(db, d)
    d.km_vtd = min(g, max(0, int(phat_tong) - (da_tra(db, d) - int(d.so_hoan or 0)))) if g and int(d.so_hoan or 0) <= 0 else 0


def ap_voucher(db: Session, tk: TaiKhoanNgoai, ma: str, ma_voucher: str, now: datetime | None = None) -> DonDatBan:
    """Khách / cổ đông tự đặt nhập voucher trước khi trả: trừ vào số phải trả trước."""
    from app.services import rewards as RW
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    if d.doi_tac_id or tk.loai not in ("khach_hang", "co_dong"):
        raise LoiDatBan("Đơn đặt qua đại lý / CTV không dùng voucher cá nhân", 403)
    if d.trang_thai not in ("cho_nhan", "cho_tra") or da_tra(db, d) > 0:
        raise LoiDatBan("Chỉ nhập voucher trước khi trả tiền", 409)
    if d.voucher_id:
        raise LoiDatBan("Đơn đã có voucher — bỏ voucher cũ trước", 409)
    try:
        v = RW.kiem_voucher_db(db, tk, ma_voucher, d, now.date())
    except RW.LoiDiem as ex:
        raise LoiDatBan(str(ex))
    v.trang_thai, v.dat_ban_id, v.ap_boi, v.ap_luc = "da_dung", d.id, f"cong:{tk.id}", now
    d.voucher_id, d.giam_voucher = v.id, int(v.gia_tri)
    d.phai_tra_truoc = int(d.phai_tra_truoc) - int(v.gia_tri or 0)
    R.audit(db, f"cong:{tk.id}", tk.loai, "ap_voucher_rewards", f"dat_ban:{d.ma}", after={"voucher": v.ma, "gia_tri": v.gia_tri})
    cap_nhat(db, d, now)
    db.commit()
    return d


def bo_voucher(db: Session, tk: TaiKhoanNgoai, ma: str, now: datetime | None = None) -> DonDatBan:
    from app.models.rewards import VoucherRewards
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    if not d.voucher_id:
        raise LoiDatBan("Đơn chưa có voucher", 409)
    if d.trang_thai not in ("cho_nhan", "cho_tra") or da_tra(db, d) > 0:
        raise LoiDatBan("Đã trả tiền — không bỏ voucher được", 409)
    v = db.get(VoucherRewards, d.voucher_id)
    if v is not None and v.trang_thai == "da_dung":
        v.trang_thai, v.dat_ban_id, v.ap_boi, v.ap_luc = "cho_dung", None, "", None
    d.phai_tra_truoc = int(d.phai_tra_truoc) + int(d.giam_voucher or 0)
    d.voucher_id, d.giam_voucher = None, 0
    R.audit(db, f"cong:{tk.id}", tk.loai, "bo_voucher_rewards", f"dat_ban:{d.ma}", after={"voucher": v.ma if v else ""})
    db.commit()
    return d


def kt_ghi_km(db: Session, u: User, did: int, now: datetime | None = None) -> DonDatBan:
    """Kế toán ghi phần voucher VTD chịu: Nợ 641 / Có 3388 (đối tượng: nhà hàng). Gọi khi chốt, hoặc tay cho đơn hủy."""
    now = now or datetime.now()
    if u.role not in VAI_KE_TOAN:
        raise LoiDatBan("Chỉ Kế toán ghi sổ", 403)
    d = _don(db, did)
    km = khuyen_mai(db, d)
    if d.trang_thai in ("cho_nhan", "cho_tra", "da_giu") or km <= 0:
        raise LoiDatBan("Đơn không có phần voucher VTD chịu để ghi", 409)
    if d.km_but_toan:
        raise LoiDatBan("Đã ghi sổ phần voucher", 409)
    from app.services import tk_chi_tiet as TKCT
    ten, ma_dt = _doi_tuong_nh(db, d)
    d.km_but_toan = _ghi_so(db, u, d, now.date(), f"Voucher VTD Rewards — đặt bàn {d.ma} (Vietourist chịu thay khách)",
                            [{"account": TKCT.chon(db, "khuyen_mai_rewards"), "debit": km, "note": d.ma},
                             {"account": TK_THU_HO, "credit": km, "partner": ten, "partner_code": ma_dt, "note": d.ma}],
                            f"{d.ma}:km", "khuyen_mai_rewards")
    R.audit(db, u.username, u.role, "dat_ban_ghi_km", f"dat_ban:{d.ma}", after={"km": km, "but_toan": d.km_but_toan})
    db.flush()
    return d


def ghi_dt_hoa_hong(db: Session, u: User, d: DonDatBan, ngay: date) -> str:
    """KS-16e — doanh thu hoa hồng nhà hàng: Nợ 3388 / Có 511 (chưa gồm VAT). Ghi khi đã chi trả nhà hàng, hoặc ngay
    lúc chốt nếu không còn gì phải trả."""
    if d.dt_but_toan or not (d.hoa_hong or 0) or int(d.hoa_hong or 0) <= 0:
        return d.dt_but_toan
    from app.services import tk_chi_tiet as TKCT
    ten, ma_dt = _doi_tuong_nh(db, d)
    hh = int(d.hoa_hong)
    d.dt_but_toan = _ghi_so(db, u, d, ngay, f"Doanh thu hoa hồng nhà hàng — đặt bàn {d.ma} ({ten})",
                            [{"account": TK_THU_HO, "debit": hh, "partner": ten, "partner_code": ma_dt, "note": d.ma},
                             {"account": TKCT.chon(db, "hoa_hong_nha_hang"), "credit": hh, "note": d.ma}], f"{d.ma}:hh", "doanh_thu_hoa_hong")
    R.audit(db, u.username, u.role, "dat_ban_ghi_dt_hoa_hong", f"dat_ban:{d.ma}", after={"hoa_hong": hh, "but_toan": d.dt_but_toan})
    db.flush()
    return d.dt_but_toan


def kt_ghi_dt_hoa_hong(db: Session, u: User, did: int, now: datetime | None = None) -> DonDatBan:
    """Nút «Ghi doanh thu hoa hồng» — ghi bù khi khoản trả nhà hàng đã chi mà chưa có bút toán."""
    from app.models.ops import PaymentRequest
    now = now or datetime.now()
    if u.role not in VAI_KE_TOAN:
        raise LoiDatBan("Chỉ Kế toán ghi sổ", 403)
    d = _don(db, did)
    if d.dt_but_toan:
        raise LoiDatBan(f"Đã ghi doanh thu hoa hồng ({d.dt_but_toan})", 409)
    pr = db.get(PaymentRequest, d.payment_request_id) if d.payment_request_id else None
    if not ((d.hoa_hong or 0) and int(d.hoa_hong or 0) > 0 and (pr is None or pr.status == "da_chi")):
        raise LoiDatBan("Chỉ ghi khi đơn đã chốt có hoa hồng và khoản trả nhà hàng đã chi", 409)
    ghi_dt_hoa_hong(db, u, d, now.date())
    return d


def _sau_khi_tra(db: Session, d: DonDatBan, now: datetime) -> None:
    cap_nhat(db, d, now)
    if d.trang_thai in ("het_han", "huy", "tu_choi"):
        # Tiền về khi bàn không còn giữ: phải hoàn (trừ phần đã giữ theo chính sách khi hủy).
        tra = da_tra(db, d)
        d.so_giu = min(int(d.so_giu or 0), tra)
        d.so_hoan = tra - int(d.so_giu or 0)
        if (d.so_hoan or 0) > int(d.da_hoan_tien or 0) and d.hoan_tt in ("", "khong_hoan", "da_hoan"):
            d.hoan_tt = "cho_sales"
        _vc_doi_chieu(db, d, now)


def nha_hang_xu_ly(db: Session, y: YeuCauKhach, nhan: bool, now: datetime | None = None) -> None:
    """Gọi từ cổng NCC khi nhà hàng nhận / từ chối bàn (NCC-1). Yêu cầu cũ không có đơn thì bỏ qua."""
    now = now or datetime.now()
    d = db.execute(select(DonDatBan).where(DonDatBan.yeu_cau_id == y.id)).scalars().first()
    if d is None:
        return
    if d.trang_thai != "cho_nhan":
        raise LoiDatBan("Đơn đặt bàn không còn chờ nhà hàng nhận", 409)
    if not nhan:
        d.trang_thai = "tu_choi"
        _sau_khi_tra(db, d, now)
        _vc_doi_chieu(db, d, now)
        return
    ts = tham_so(db)
    ga = gio_an(d)
    d.nhan_luc = now
    d.han_tra = max(ga - timedelta(hours=ts["han_tra_gio"]), min(now + timedelta(hours=2), ga - timedelta(minutes=30)))
    d.trang_thai = "cho_tra"
    cap_nhat(db, d, now)


def phat(db: Session, d: DonDatBan, now: datetime | None = None, khong_den: bool = False) -> int:
    """Số giữ lại theo chính sách (chưa trừ trần «không quá số đã trả»)."""
    now = now or datetime.now()
    if d.mien_phat:
        return 0
    ts = tham_so(db)
    con = (gio_an(d) - now).total_seconds() / 3600
    if khong_den or con < ts["gan_gio"]:
        pct = ts["phat_doan_gan"] if d.la_doan else ts["phat"]
    elif con < ts["mien_phi_gio"]:
        pct = ts["phat"]
    else:
        pct = 0
    return _nghin(float(d.tam_tinh) * pct / 100) if pct else 0


def _huy(db: Session, d: DonDatBan, boi: str, ly_do: str, now: datetime, mien_phat: bool = False) -> DonDatBan:
    cap_nhat(db, d, now)
    if d.trang_thai not in TRANG_THAI_HUY_DUOC:
        raise LoiDatBan(f"Đơn đang «{TRANG_THAI[d.trang_thai]}» — không hủy được", 409)
    d.mien_phat = bool(mien_phat) or bool(d.huy_mien_phi)
    tra = da_tra(db, d)
    p = phat(db, d, now)
    giu = min(p, tra - int(d.so_hoan or 0))      # phần đã phải hoàn trước đó (bớt khách) không giữ lại
    if d.trang_thai == "het_han":
        giu, p = 0, 0                   # bàn đã trả lại vì quá hạn — không phạt người chưa giữ được bàn
    d.trang_thai, d.huy_luc, d.huy_boi, d.huy_ly_do = "huy", now, boi, (ly_do or "").strip()[:1000]
    d.so_giu, d.so_hoan = giu, tra - giu
    d.thay_doi = None
    d.hoan_tt = "cho_sales" if (d.so_hoan or 0) > int(d.da_hoan_tien or 0) else ("khong_hoan" if tra and not (d.da_hoan_tien or 0) else d.hoan_tt or "")
    _km_khi_dong(db, d, p)             # KS-16b: voucher dùng hẳn → nhà hàng nhận phần phạt còn thiếu từ voucher
    _vc_doi_chieu(db, d, now)
    return d


# ====================================================================== phía người đặt
def _cua(db: Session, tk: TaiKhoanNgoai, ma: str) -> DonDatBan:
    d = db.execute(select(DonDatBan).where(DonDatBan.ma == (ma or "").strip().upper())).scalars().first()
    if d is None or d.tai_khoan_id != tk.id:
        raise LoiDatBan("Không có đơn đặt bàn này trong tài khoản của bạn", 404)
    return d


def ra(db: Session, d: DonDatBan, now: datetime | None = None, doi_tac: bool = False, noi_bo: bool = False) -> dict:
    now = now or datetime.now()
    nh = db.get(NhaHang, d.nha_hang_id)
    td = db.get(ThucDonNhaHang, d.thuc_don_id)
    y = db.get(YeuCauKhach, d.yeu_cau_id)
    tra = da_tra(db, d)
    tts = db.execute(select(ThanhToanDatBan).where(ThanhToanDatBan.don_id == d.id).order_by(ThanhToanDatBan.id)).scalars().all()
    r = {"id": d.id, "ma": d.ma, "nha_hang": nh.ten if nh else "", "thuc_don": td.ten if td else "", "ngay": d.ngay.isoformat(),
         "gio": d.gio, "nguoi_lon": d.nguoi_lon, "tre_em": d.tre_em, "la_doan": d.la_doan, "cach_tt": d.cach_tt,
         "cach_tt_ten": ("Cọc giữ bàn" if td and td.coc_moi_khach and td.loai == "goi_mon"
                         else f"{CACH_TT[d.cach_tt]} {d.ty_le_coc}%") if d.cach_tt == "coc" else CACH_TT[d.cach_tt],
         # P1-03
         "phu_thu": d.phu_thu or [], "tuoi_tre": d.tuoi_tre or [],
         "han_phan_hoi": d.han_phan_hoi.isoformat(timespec="minutes") if d.han_phan_hoi else None,
         "qua_han_phan_hoi": bool(d.trang_thai == "cho_nhan" and d.han_phan_hoi and now > d.han_phan_hoi),
         "tam_tinh": int(d.tam_tinh), "phai_tra_truoc": int(d.phai_tra_truoc), "da_tra": tra,
         "con_phai_tra_truoc": max(0, int(d.phai_tra_truoc) - (tra - int(d.so_hoan or 0))),
         "mo_thanh_toan": bool(nh) and _mo_tt(db, nh),                 # AT-2: khóa nút trả khi công tắc đóng
         "tra_tai_ban_du_kien": max(0, int(d.tam_tinh) - tra - vc_con_giu(db, d)),
         "giam_voucher": int(d.giam_voucher or 0), "voucher": _vc_out(db, d), "km_vtd": khuyen_mai(db, d), "km_but_toan": d.km_but_toan,
         "dung_voucher": d.doi_tac_id is None and d.trang_thai in ("cho_nhan", "cho_tra") and tra <= 0,
         "han_tra": d.han_tra.isoformat(timespec="minutes") if d.han_tra else None,
         "trang_thai": d.trang_thai, "trang_thai_ten": TRANG_THAI[d.trang_thai],
         "ly_do_tu_choi": (y.nha_hang_ghi_chu if y and d.trang_thai == "tu_choi" else ""),
         "co_the_tra": _co_the_tra(d, tra), "co_the_huy": d.trang_thai in TRANG_THAI_HUY_DUOC,
         "co_the_doi": d.trang_thai in DOI_DUOC and not d.thay_doi, "thay_doi": d.thay_doi, "so_lan_doi": d.so_lan_doi,
         "thay_doi_ghi_chu": d.thay_doi_ghi_chu, "huy_mien_phi": d.huy_mien_phi, "da_hoan_tien": int(d.da_hoan_tien or 0),
         "the_bat": SP.cong_the_bat(), "bill_thuc_te": d.bill_thuc_te, "so_giu": d.so_giu, "so_hoan": d.so_hoan,
         "hoan_tt": d.hoan_tt, "hoan_tt_ten": HOAN_TT.get(d.hoan_tt, ""), "huy_ly_do": d.huy_ly_do,
         "phat_neu_huy_bay_gio": (0 if d.huy_mien_phi else min(phat(db, d, now), tra - int(d.so_hoan or 0)))
                                 if d.trang_thai in ("da_giu", "cho_tra") else 0,
         "thanh_toan": [{"kenh": KENH[t.kenh], "so_tien": int(t.so_tien), "trang_thai": t.trang_thai,
                         "trang_thai_ten": TT_THANH_TOAN[t.trang_thai], "luc": t.luc.isoformat(timespec="minutes")} for t in tts]}
    if doi_tac or noi_bo:
        r.update({"ten_khach": d.ten_khach, "doanh_so": d.doanh_so,
                  "ky_d06": (f"{max(d.ngay, d.chot_luc.date()):%Y-%m}" if d.chot_luc and d.doanh_so is not None else None)})
    if noi_bo:
        r.update({"dien_thoai": d.dien_thoai, "nguon": NGUON[d.nguon], "doi_tac_id": d.doi_tac_id, "chot_boi": d.chot_boi,
                  "thu_tai_ban": d.thu_tai_ban, "dung_ghi_chu": d.dung_ghi_chu, "co_bill": d.bill_attachment_id is not None,
                  "huy_boi": d.huy_boi, "mien_phat": d.mien_phat, "hoan_ghi_chu": d.hoan_ghi_chu,
                  "thanh_toan_id": [t.id for t in tts],
                  "hoa_hong": int(d.hoa_hong) if d.hoa_hong is not None else None,
                  "phai_tra_nh": int(d.phai_tra_nh) if d.phai_tra_nh is not None else None,
                  "de_nghi_chi": _dnc(db, d.payment_request_id), "dt_but_toan": d.dt_but_toan})
        for t, o in zip(tts, r["thanh_toan"]):
            o.update({"id": t.id, "kenh_ma": t.kenh, "so_gd_cong": t.so_gd_cong, "ma_gd": t.ma_gd, "xac_nhan_boi": t.xac_nhan_boi,
                      "phi_the": t.phi_the, "but_toan": t.but_toan})
    return r


def _vc_out(db: Session, d: DonDatBan) -> dict | None:
    if not d.voucher_id:
        return None
    from app.models.rewards import VoucherRewards, TRANG_THAI_VOUCHER
    v = db.get(VoucherRewards, d.voucher_id)
    return {"ma": v.ma, "gia_tri": int(v.gia_tri), "trang_thai": v.trang_thai,
            "trang_thai_ten": TRANG_THAI_VOUCHER.get(v.trang_thai, v.trang_thai)} if v else None


def ds_cua(db: Session, tk: TaiKhoanNgoai, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    ds = db.execute(select(DonDatBan).where(DonDatBan.tai_khoan_id == tk.id).order_by(DonDatBan.id.desc()).limit(100)).scalars().all()
    for d in ds:
        cap_nhat(db, d, now)
    db.commit()
    from app.services import danh_gia_nh as DG       # AT-3: được viết / sửa đánh giá không
    return [{**ra(db, d, now, doi_tac=tk.loai == "doi_tac"), "danh_gia": DG.trang_thai_don(db, d, now)} for d in ds]


def qr(db: Session, tk: TaiKhoanNgoai, ma: str, now: datetime | None = None) -> dict:
    from app.services import cong_khach as K
    from app.services import vietqr as Q
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    db.commit()
    con = int(d.phai_tra_truoc) - (da_tra(db, d) - int(d.so_hoan or 0))
    if not _co_the_tra(d, da_tra(db, d)):
        raise LoiDatBan(f"Đơn đang «{TRANG_THAI[d.trang_thai]}» — không thanh toán" if con > 0 else "Đã đủ số phải trả trước", 409)
    _kiem_mo_tt(db, d.nha_hang_id)                                 # AT-2
    ba = K.tai_khoan_qr(db)
    if ba is None or not ba.account_number:
        raise LoiDatBan("Thanh toán QR chưa mở — vui lòng liên hệ Sales", 409)
    bin_ = Q.bin_cua(ba.bank_name)
    if bin_ is None:
        raise LoiDatBan("Thanh toán QR chưa mở cho ngân hàng này — vui lòng liên hệ Sales", 409)
    return {"ma": d.ma, "muc": "du", "so_tien": con, "coc": 0, "con_lai": con, "da_nop": da_tra(db, d),
            "payload": Q.payload(bin_, ba.account_number, con, d.ma), "noi_dung": Q.noi_dung_sach(d.ma),
            "ngan_hang": ba.bank_name, "so_tk": ba.account_number, "chu_tk": ba.account_name, "tu_khop": False,
            "han_tra": d.han_tra.isoformat(timespec="minutes") if d.han_tra else None}


def onepay_bat_dau(db: Session, tk: TaiKhoanNgoai, ma: str, goc: str, ip: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    if not OP.bat():
        raise LoiDatBan("Thanh toán thẻ chưa mở — dùng QR chuyển khoản", 409)
    d = cap_nhat(db, _cua(db, tk, ma), now)
    con = int(d.phai_tra_truoc) - (da_tra(db, d) - int(d.so_hoan or 0))
    if not _co_the_tra(d, da_tra(db, d)):
        db.commit()
        raise LoiDatBan(f"Đơn đang «{TRANG_THAI[d.trang_thai]}» — không thanh toán" if con > 0 else "Đã đủ số phải trả trước", 409)
    _kiem_mo_tt(db, d.nha_hang_id)                                 # AT-2
    t = ThanhToanDatBan(don_id=d.id, kenh="onepay", so_tien=con, trang_thai="cho", luc=now, goc=goc[:80])
    db.add(t); db.flush()
    t.ma_gd = f"{d.ma}T{t.id}"
    url = OP.duong_thanh_toan(t.ma_gd, con, f"Dat ban {d.ma}", f"{goc}/api/v1/onepay/tra-ve", ip, f"{goc}/cong")
    db.commit()
    return url


def the_bat_dau(db: Session, tk: TaiKhoanNgoai, ma: str, goc: str, ip: str, now: datetime | None = None) -> dict:
    """SP-1: cổng thẻ SePay (ưu tiên) → {"form": biểu mẫu POST}; SePay chưa có khóa mà OnePay có → {"url": …}."""
    now = now or datetime.now()
    if not SP.bat():
        return {"url": onepay_bat_dau(db, tk, ma, goc, ip, now)}
    d = cap_nhat(db, _cua(db, tk, ma), now)
    con = int(d.phai_tra_truoc) - (da_tra(db, d) - int(d.so_hoan or 0))
    if not _co_the_tra(d, da_tra(db, d)):
        db.commit()
        raise LoiDatBan(f"Đơn đang «{TRANG_THAI[d.trang_thai]}» — không thanh toán" if con > 0 else "Đã đủ số phải trả trước", 409)
    _kiem_mo_tt(db, d.nha_hang_id)                                 # AT-2
    t = ThanhToanDatBan(don_id=d.id, kenh="sepay", so_tien=con, trang_thai="cho", luc=now, goc=goc[:80])
    db.add(t); db.flush()
    t.ma_gd = f"{d.ma}T{t.id}"
    ve = f"{goc}/cong?dat_ban={d.ma}&the="
    f = SP.bieu_mau(t.ma_gd, con, f"Dat ban {d.ma}", ve + "cho", ve + "loi", ve + "huy")
    db.commit()
    return {"form": f}


def sepay_ket_qua(db: Session, kq: dict, now: datetime | None = None) -> tuple[DonDatBan, ThanhToanDatBan] | None:
    """IPN SePay đã qua khóa: chạy lại không ghi thêm."""
    now = now or datetime.now()
    t = db.execute(select(ThanhToanDatBan).where(ThanhToanDatBan.ma_gd == kq["ma_gd"], ThanhToanDatBan.kenh == "sepay")).scalars().first()
    if t is None:
        return None
    d = db.get(DonDatBan, t.don_id)
    if kq["loai"] == "TRANSACTION_VOID":
        t.ghi_chu = (f"SePay báo hủy giao dịch {kq['so_gd']} — Kế toán kiểm tra" + (f" · {t.ghi_chu}" if t.ghi_chu else ""))[:300]
        R.audit(db, "sepay", "sepay", "dat_ban_the_huy_gd", f"dat_ban:{d.ma}", after={"so_gd": kq["so_gd"], "trang_thai": t.trang_thai})
        db.commit()
        return d, t
    if t.trang_thai in ("cho", "that_bai"):
        t.ket_qua, t.so_gd_cong = kq["ma_kq"], kq["so_gd"]
        if kq["thanh_cong"] and kq["so_tien"] == int(t.so_tien):
            t.trang_thai = "thanh_cong"
            t.ghi_chu = " · ".join(x for x in (kq["cach"], kq["the"]) if x)[:300]
            R.audit(db, "sepay", "sepay", "dat_ban_the_thanh_cong", f"dat_ban:{d.ma}", after={"so_tien": int(t.so_tien), "so_gd": kq["so_gd"]})
        else:
            t.trang_thai = "that_bai"
            t.ghi_chu = "Số tiền không khớp" if kq["thanh_cong"] else f"SePay: {kq['loai']} {kq['ma_kq']}"[:300]
        _sau_khi_tra(db, d, now)
        db.commit()
    return d, t


def onepay_ket_qua(db: Session, p: dict, now: datetime | None = None) -> tuple[DonDatBan, ThanhToanDatBan] | None:
    """Xử lý kết quả OnePay (đường trả về và IPN dùng chung, chạy lại không ghi thêm)."""
    now = now or datetime.now()
    kq = OP.ket_qua(p)
    if not kq["hop_le"]:
        return None
    t = db.execute(select(ThanhToanDatBan).where(ThanhToanDatBan.ma_gd == kq["ma_gd"], ThanhToanDatBan.kenh == "onepay")).scalars().first()
    if t is None:
        return None
    d = db.get(DonDatBan, t.don_id)
    if t.trang_thai == "cho":
        t.ket_qua, t.so_gd_cong = kq["ma_kq"], kq["so_gd"]
        if kq["thanh_cong"] and kq["so_tien"] == int(t.so_tien):
            t.trang_thai = "thanh_cong"
            R.audit(db, "onepay", "onepay", "dat_ban_the_thanh_cong", f"dat_ban:{d.ma}", after={"so_tien": int(t.so_tien), "so_gd": kq["so_gd"]})
        else:
            t.trang_thai = "that_bai"
            t.ghi_chu = "Số tiền không khớp" if kq["thanh_cong"] else f"Mã kết quả {kq['ma_kq']}"
        _sau_khi_tra(db, d, now)
        db.commit()
    return d, t


def huy_boi_nguoi_dat(db: Session, tk: TaiKhoanNgoai, ma: str, ly_do: str, now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    d = _huy(db, _cua(db, tk, ma), f"cong:{tk.id}", ly_do, now)
    R.audit(db, f"cong:{tk.id}", tk.loai, "dat_ban_huy", f"dat_ban:{d.ma}", after={"giu": d.so_giu, "hoan": d.so_hoan})
    db.commit()
    return d


# ====================================================================== thay đổi sau khi đặt (DT-3)
def _ap_dung(db: Session, d: DonDatBan, ngay: date, gio: str, nl: int, te: int, now: datetime) -> None:
    """Áp lịch / số khách mới: tính lại tạm tính, đoàn, số phải trả trước; trả dư → khoản hoàn."""
    from app.services import nha_hang as NH
    ts = tham_so(db)
    con_gio = (gio_an(d) - now).total_seconds() / 3600
    doi_lich = (ngay, gio) != (d.ngay, d.gio)
    hn = now.date() if ngay != d.ngay else min(now.date(), ngay - timedelta(days=1))   # giữ ngày cũ: không kiểm lại «sau hôm nay»
    try:
        _o, td, tam = NH.kiem_dat_ban(db, d.nha_hang_id, d.thuc_don_id, ngay, gio, nl, te, hn,
                                      tuoi=d.tuoi_tre, chon_phu_thu=[x.get("i") for x in (d.phu_thu or []) if x.get("i") is not None])
    except NH.LoiNhaHang as ex:
        raise LoiDatBan(str(ex))
    tam = int(round(tam))
    if tam < int(d.tam_tinh) and con_gio < ts["mien_phi_gio"]:
        tam = max(tam, _nghin(float(d.tam_tinh) * 0.8))       # bớt khách trong 24 giờ: tính tối thiểu 80%
    doan = la_doan(ts, td, nl + te)
    pct, truoc = tra_truoc(ts, td, tam, doan, d.cach_tt)
    d.ngay, d.gio, d.nguoi_lon, d.tre_em = ngay, gio, nl, te
    d.phu_thu = [{"i": x["i"], "ten": x["ten"], "so_tien": x["so_tien"]} for x in td["tinh"]["phu_thu"]] or None
    if d.tuoi_tre and len(d.tuoi_tre) != te:
        d.tuoi_tre = None                                      # số trẻ đổi: tuổi cũ không còn khớp
    g = min(vc_con_giu(db, d), truoc)                        # KS-16b: voucher vẫn trừ vào phần trả trước
    if d.voucher_id and g != int(d.giam_voucher or 0):
        d.giam_voucher = g
    d.tam_tinh, d.la_doan, d.ty_le_coc, d.phai_tra_truoc = tam, doan, pct, truoc - g
    if doi_lich:
        d.so_lan_doi = int(d.so_lan_doi or 0) + 1
        if d.trang_thai == "cho_tra":
            ga = gio_an(d)
            d.han_tra = max(ga - timedelta(hours=ts["han_tra_gio"]), min(now + timedelta(hours=2), ga - timedelta(minutes=30)))
    tra = da_tra(db, d)
    du = tra - int(d.so_hoan or 0) - truoc
    if du > 0 and d.trang_thai in ("cho_tra", "da_giu"):
        d.so_hoan = int(d.so_hoan or 0) + du
        d.hoan_tt = "cho_sales"
    y = db.get(YeuCauKhach, d.yeu_cau_id)
    if y is not None:
        y.ngay_mong_muon, y.gio_den, y.so_khach, y.tre_em, y.tam_tinh = ngay, gio, nl + te, te, tam
    d.thay_doi, d.thay_doi_luc = None, None
    cap_nhat(db, d, now)


def thay_doi(db: Session, tk: TaiKhoanNgoai, ma: str, ngay, gio: str, nguoi_lon: int, tre_em: int,
             now: datetime | None = None) -> DonDatBan:
    """Người đặt đổi lịch và / hoặc số khách. Chưa nhận bàn: áp ngay. Đã nhận: bớt khách áp ngay; đổi lịch,
    thêm khách chờ nhà hàng nhận lại."""
    now = now or datetime.now()
    d = cap_nhat(db, _cua(db, tk, ma), now)
    if d.trang_thai not in DOI_DUOC:
        raise LoiDatBan(f"Đơn đang «{TRANG_THAI[d.trang_thai]}» — không thay đổi được", 409)
    if d.thay_doi:
        raise LoiDatBan("Đang có một yêu cầu thay đổi chờ nhà hàng — chờ nhà hàng trả lời", 409)
    ngay = ngay if isinstance(ngay, date) else (date.fromisoformat(ngay) if ngay else d.ngay)
    gio = (gio or d.gio).strip()
    nl = int(nguoi_lon if nguoi_lon is not None else d.nguoi_lon)
    te = int(tre_em if tre_em is not None else d.tre_em)
    doi_lich = (ngay, gio) != (d.ngay, d.gio)
    if not doi_lich and (nl, te) == (d.nguoi_lon, d.tre_em):
        raise LoiDatBan("Chưa có gì thay đổi")
    ts = tham_so(db)
    if doi_lich:
        if (gio_an(d) - now).total_seconds() / 3600 < ts["mien_phi_gio"]:
            raise LoiDatBan(f"Đổi ngày giờ phải báo trước {ts['mien_phi_gio']} giờ — muốn đổi thì hủy theo chính sách rồi đặt lại", 409)
        if int(d.so_lan_doi or 0) >= 1:
            raise LoiDatBan("Đã đổi lịch miễn phí 1 lần — muốn đổi nữa thì hủy theo chính sách rồi đặt lại", 409)
    from app.services import nha_hang as NH
    hn = now.date() if ngay != d.ngay else min(now.date(), ngay - timedelta(days=1))
    try:
        NH.kiem_dat_ban(db, d.nha_hang_id, d.thuc_don_id, ngay, gio, nl, te, hn, tuoi=d.tuoi_tre,
                        chon_phu_thu=[x.get("i") for x in (d.phu_thu or []) if x.get("i") is not None])
    except NH.LoiNhaHang as ex:
        raise LoiDatBan(str(ex))
    cu = d.nguoi_lon + d.tre_em
    can_nha_hang = d.trang_thai != "cho_nhan" and (doi_lich or nl > d.nguoi_lon or te > d.tre_em)
    if can_nha_hang:
        d.thay_doi = {"ngay": ngay.isoformat(), "gio": gio, "nguoi_lon": nl, "tre_em": te}
        d.thay_doi_luc, d.thay_doi_ghi_chu = now, ""
    else:
        _ap_dung(db, d, ngay, gio, nl, te, now)
    R.audit(db, f"cong:{tk.id}", tk.loai, "dat_ban_thay_doi", f"dat_ban:{d.ma}",
            after={"ngay": ngay.isoformat(), "gio": gio, "khach": f"{cu}→{nl + te}", "cho_nha_hang": can_nha_hang})
    db.commit()
    return d


def ncc_thay_doi(db: Session, tk: TaiKhoanNgoai, s, yid: int, nhan: bool, ghi_chu: str = "",
                 now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    d = cap_nhat(db, _don_ncc(db, s, yid), now)
    if not d.thay_doi:
        raise LoiDatBan("Đơn không có yêu cầu thay đổi đang chờ", 409)
    if d.trang_thai not in DOI_DUOC:
        d.thay_doi = None
        raise LoiDatBan(f"Đơn đang «{TRANG_THAI[d.trang_thai]}»", 409)
    td = d.thay_doi
    if nhan:
        _ap_dung(db, d, date.fromisoformat(td["ngay"]), td["gio"], int(td["nguoi_lon"]), int(td["tre_em"]), now)
        d.thay_doi_ghi_chu = f"Nhà hàng đã nhận thay đổi {now:%d/%m %H:%M}" + (f" · {ghi_chu.strip()}" if (ghi_chu or "").strip() else "")
    else:
        if not (ghi_chu or "").strip():
            raise LoiDatBan("Từ chối phải ghi lý do")
        d.thay_doi, d.thay_doi_luc = None, None
        d.huy_mien_phi = True                      # khách giữ lịch cũ, hoặc hủy được hoàn đủ
        d.thay_doi_ghi_chu = f"Nhà hàng từ chối thay đổi: {ghi_chu.strip()[:300]} — bạn giữ lịch cũ hoặc hủy được hoàn đủ"
    R.audit(db, f"cong:ncc-{tk.id}", "ncc", "dat_ban_thay_doi_nha_hang", f"dat_ban:{d.ma}", after={"nhan": nhan})
    db.flush()
    return d


# ====================================================================== phía nhà hàng (cổng NCC)
def don_cua_yeu_cau(db: Session, ids: list[int]) -> dict[int, DonDatBan]:
    if not ids:
        return {}
    return {d.yeu_cau_id: d for d in db.execute(select(DonDatBan).where(DonDatBan.yeu_cau_id.in_(ids))).scalars()}


def ra_ncc(db: Session, d: DonDatBan, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    cap_nhat(db, d, now)
    tra = da_tra(db, d)
    return {"ma_don": d.ma, "tt_don": d.trang_thai, "tt_don_ten": TRANG_THAI[d.trang_thai], "la_doan": d.la_doan,
            "cach_tt_ten": f"{CACH_TT[d.cach_tt]} {d.ty_le_coc}%" if d.cach_tt == "coc" else CACH_TT[d.cach_tt],
            "phai_tra_truoc": int(d.phai_tra_truoc) + vc_con_giu(db, d), "da_tra_vtd": tra + vc_con_giu(db, d),
            "phu_thu": d.phu_thu or [], "tuoi_tre": d.tuoi_tre or [],                                  # P1-03
            "han_phan_hoi": d.han_phan_hoi.isoformat(timespec="minutes") if d.han_phan_hoi else None,
            "thu_tai_ban_du_kien": max(0, int(d.tam_tinh) - tra - vc_con_giu(db, d)),
            "bill_thuc_te": d.bill_thuc_te, "thu_tai_ban": d.thu_tai_ban, "so_giu": d.so_giu,
            "thay_doi": d.thay_doi, "thay_doi_ghi_chu": d.thay_doi_ghi_chu,
            "bao_dung_duoc": d.trang_thai == "da_giu", "bao_khong_den_duoc": d.trang_thai == "da_giu" and now >= gio_an(d) + timedelta(minutes=30)}


def _don_ncc(db: Session, s, yid: int) -> DonDatBan:
    nh = {n.id for n in db.execute(select(NhaHang).where(NhaHang.supplier_id == s.id)).scalars()}
    d = db.execute(select(DonDatBan).where(DonDatBan.yeu_cau_id == yid)).scalars().first()
    if d is None or d.nha_hang_id not in nh:
        raise LoiDatBan("Không có đơn đặt bàn này", 404)
    return d


def ncc_da_dung(db: Session, tk: TaiKhoanNgoai, s, yid: int, bill: int, thu_tai_ban: int, ghi_chu: str,
                ten_tep: str = "", kieu: str = "", data: bytes | None = None, now: datetime | None = None) -> DonDatBan:
    from app.services import attachments as AT
    now = now or datetime.now()
    d = cap_nhat(db, _don_ncc(db, s, yid), now)
    if d.trang_thai != "da_giu":
        raise LoiDatBan("Chỉ báo «khách đã dùng» cho bàn đã giữ (khách đã trả trước)", 409)
    if now < gio_an(d) - timedelta(hours=1):
        raise LoiDatBan("Chưa tới giờ ăn — chưa báo được", 409)
    if not bill or int(bill) <= 0:
        raise LoiDatBan("Ghi số bill thực tế")
    if thu_tai_ban is None or int(thu_tai_ban) < 0:
        raise LoiDatBan("Ghi số đã thu tại bàn (0 nếu khách đã trả đủ trước)")
    if data:
        try:
            a, _ = AT.dinh_kem(db, "nha_cung_cap", s.code, ten_tep, data, kieu=kieu, loai="chung_tu",
                               mo_ta=f"Bill đặt bàn {d.ma}", boi=f"cong:ncc-{tk.id}")
        except ValueError as ex:
            raise LoiDatBan(str(ex))
        d.bill_attachment_id = a.id
    d.trang_thai, d.bill_thuc_te, d.thu_tai_ban, d.dung_luc = "da_dung", int(bill), int(thu_tai_ban), now
    d.km_vtd = vc_con_giu(db, d)                     # KS-16b: voucher dùng hẳn — VTD trả nhà hàng phần này
    d.dung_ghi_chu = (ghi_chu or "").strip()[:1000]
    R.audit(db, f"cong:ncc-{tk.id}", "ncc", "dat_ban_da_dung", f"dat_ban:{d.ma}", after={"bill": int(bill), "tai_ban": int(thu_tai_ban)})
    db.flush()
    return d


def ncc_khong_den(db: Session, tk: TaiKhoanNgoai, s, yid: int, now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    d = cap_nhat(db, _don_ncc(db, s, yid), now)
    if d.trang_thai != "da_giu" or now < gio_an(d) + timedelta(minutes=30):
        raise LoiDatBan("Chỉ báo «khách không đến» khi bàn đã giữ và đã quá giờ hẹn 30 phút", 409)
    tra = da_tra(db, d)
    d.trang_thai = "khong_den"
    p = phat(db, d, now, khong_den=True)
    d.so_giu = min(p, tra)
    d.so_hoan = tra - (d.so_giu or 0)
    d.hoan_tt = "cho_sales" if (d.so_hoan or 0) > 0 else "khong_hoan"
    _km_khi_dong(db, d, p)
    _vc_doi_chieu(db, d, now)
    d.huy_luc, d.huy_boi, d.huy_ly_do = now, f"cong:ncc-{tk.id}", "Nhà hàng báo khách không đến"
    R.audit(db, f"cong:ncc-{tk.id}", "ncc", "dat_ban_khong_den", f"dat_ban:{d.ma}", after={"giu": (d.so_giu or 0), "hoan": (d.so_hoan or 0)})
    db.flush()
    return d


def thu_ho_ncc(db: Session, s) -> list[dict]:
    """Tiền Vietourist đã thu hộ cho các nhà hàng của NCC (trừ phần đã / sẽ hoàn khách). Chỉ để xem — chi qua đề nghị chi."""
    nh = {n.id: n.ten for n in db.execute(select(NhaHang).where(NhaHang.supplier_id == s.id)).scalars()}
    if not nh:
        return []
    ra_ = []
    for d in db.execute(select(DonDatBan).where(DonDatBan.nha_hang_id.in_(list(nh))).order_by(DonDatBan.ngay.desc())).scalars():
        tra = da_tra(db, d)
        km = khuyen_mai(db, d)
        if tra <= 0 and km <= 0:
            continue
        ra_.append({"ma": d.ma, "nha_hang": nh[d.nha_hang_id], "ngay": d.ngay.isoformat(), "da_thu_ho": tra,
                    "hoan_khach": int(d.so_hoan or 0), "thuoc_nha_hang": tra - int(d.so_hoan or 0) + km, "voucher_vtd": km,
                    "trang_thai_ten": TRANG_THAI[d.trang_thai]})
    return ra_


def _dnc(db: Session, pid: int | None) -> dict | None:
    from app.services.don_ks_vtd import _dnc as f
    return f(db, pid)


# ====================================================================== ghi sổ (DT-3: đại lý thu hộ nhà hàng)
def _doi_tuong_nh(db: Session, d: DonDatBan) -> tuple[str, str]:
    """(tên, mã) đối tượng công nợ 3388 — nhà cung cấp của nhà hàng; chưa gắn NCC thì tên nhà hàng."""
    from app.models.suppliers import Supplier
    nh = db.get(NhaHang, d.nha_hang_id)
    s = db.get(Supplier, nh.supplier_id) if nh and nh.supplier_id else None
    return (s.ten, s.code) if s else ((nh.ten if nh else "Nhà hàng"), (nh.ma if nh else ""))


def _ghi_so(db: Session, u: User, d: DonDatBan, ngay: date, mo_ta: str, lines: list[dict], ma_nguon: str, nghiep_vu: str) -> str:
    """Bút toán vào sổ CTCP Vietourist Holdings (công ty mẹ). Kỳ khóa / trùng sự kiện → lỗi, không ghi."""
    from app.models.core import Company
    from app.services import accounting as ACC
    try:
        if nghiep_vu == "thu_tien_khach":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type="dat_ban", source_ref=ma_nguon,
                               nghiep_vu="thu_tien_khach")
        elif nghiep_vu == "chi_tien":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type="dat_ban", source_ref=ma_nguon,
                               nghiep_vu="chi_tien")
        elif nghiep_vu == "khuyen_mai_rewards":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type="dat_ban", source_ref=ma_nguon,
                               nghiep_vu="khuyen_mai_rewards")
        elif nghiep_vu == "doanh_thu_hoa_hong":
            e = ACC.post_entry(db, u.username, u.role, ngay, mo_ta, lines, source_type="dat_ban", source_ref=ma_nguon,
                               nghiep_vu="doanh_thu_hoa_hong")
        else:
            raise ValueError(f"nghiệp vụ {nghiep_vu} không thuộc đặt bàn")
    except ValueError as ex:
        raise LoiDatBan(f"Chưa ghi sổ được: {ex}", 409)
    me = db.execute(select(Company).where(Company.kind == "me").order_by(Company.id)).scalars().first()
    if me is not None:
        e.company_id = me.id
    return e.code


# ====================================================================== phía VTOS
def _don(db: Session, did: int) -> DonDatBan:
    d = db.get(DonDatBan, did)
    if d is None:
        raise LoiDatBan("Không có đơn đặt bàn này", 404)
    return d


def giao_dich_cho(db: Session, now: datetime | None = None) -> list[dict]:
    """Giao dịch QR tiền vào chưa khớp mà nội dung có mã đơn đặt bàn — Kế toán gán."""
    now = now or datetime.now()
    ra_ = []
    for t in db.execute(select(BankTransaction).where(BankTransaction.transfer_type == "in",
                                                      BankTransaction.match_status.in_(("cho_ke_toan", "chua_khop")),
                                                      BankTransaction.transaction_date >= now - timedelta(days=90))
                        .order_by(BankTransaction.transaction_date.desc()).limit(300)).scalars():
        m = MA_RE.search((t.content or "").upper().replace(" ", ""))
        if not m:
            continue
        d = db.execute(select(DonDatBan).where(DonDatBan.ma == m.group(0))).scalars().first()
        ra_.append({"txn_id": t.id, "luc": t.transaction_date.isoformat(timespec="minutes"), "so_tien": int(t.amount or 0),
                    "noi_dung": (t.content or "")[:160], "don_id": d.id if d else None, "ma": m.group(0),
                    "con_phai_tra": (int(d.phai_tra_truoc) - da_tra(db, d)) if d else None,
                    "trang_thai_ten": TRANG_THAI[d.trang_thai] if d else "Không có đơn mã này"})
    return ra_


def kt_gan_qr(db: Session, u: User, did: int, txn_id: int, now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    if u.role not in VAI_KE_TOAN:
        raise LoiDatBan("Chỉ Kế toán xác nhận tiền vào", 403)
    d = _don(db, did)
    t = db.get(BankTransaction, txn_id)
    if t is None or t.transfer_type != "in":
        raise LoiDatBan("Không có giao dịch tiền vào này", 404)
    if t.match_status not in ("cho_ke_toan", "chua_khop"):
        raise LoiDatBan("Giao dịch đã được xử lý ở nơi khác", 409)
    if db.execute(select(ThanhToanDatBan.id).where(ThanhToanDatBan.bank_txn_id == t.id)).first():
        raise LoiDatBan("Giao dịch đã gán cho một đơn đặt bàn", 409)
    tt = ThanhToanDatBan(don_id=d.id, kenh="qr", so_tien=int(round(float(t.amount or 0))), trang_thai="da_xac_nhan",
                         bank_txn_id=t.id, luc=t.transaction_date or now, xac_nhan_boi=u.username, xac_nhan_luc=now)
    db.add(tt); db.flush()
    ten, ma_dt = _doi_tuong_nh(db, d)
    tt.but_toan = _ghi_so(db, u, d, (t.transaction_date or now).date(), f"Thu hộ nhà hàng — đặt bàn {d.ma} (QR)",
                          [{"account": TK_TIEN, "debit": tt.so_tien, "note": d.ma},
                           {"account": TK_THU_HO, "credit": tt.so_tien, "partner": ten, "partner_code": ma_dt, "note": d.ma}],
                          f"{d.ma}:tt{tt.id}", "thu_tien_khach")
    t.match_status, t.match_note = "da_khop", f"Đặt bàn {d.ma} — Kế toán {u.username} xác nhận · {tt.but_toan}"
    db.flush()
    _sau_khi_tra(db, d, now)
    R.audit(db, u.username, u.role, "dat_ban_xac_nhan_qr", f"dat_ban:{d.ma}", after={"so_tien": float(t.amount or 0), "txn": t.id})
    db.flush()
    return d


def kt_doi_soat(db: Session, u: User, tt_id: int, phi: int | None = None, now: datetime | None = None) -> ThanhToanDatBan:
    now = now or datetime.now()
    if u.role not in VAI_KE_TOAN:
        raise LoiDatBan("Chỉ Kế toán đối soát", 403)
    t = db.get(ThanhToanDatBan, tt_id)
    if t is None or t.kenh not in ("onepay", "sepay"):
        raise LoiDatBan("Không có giao dịch thẻ này", 404)
    if t.trang_thai != "thanh_cong":
        raise LoiDatBan("Chỉ đối soát giao dịch OnePay báo thành công", 409)
    if phi is None or int(phi) < 0 or int(phi) >= int(t.so_tien or 0):
        raise LoiDatBan("Ghi phí thẻ theo sao kê OnePay / cổng thẻ (0 nếu không trừ phí)")
    d = db.get(DonDatBan, t.don_id)
    ten, ma_dt = _doi_tuong_nh(db, d)
    dong = [{"account": TK_TIEN, "debit": int(t.so_tien or 0) - int(phi), "note": t.so_gd_cong or d.ma}]
    if int(phi):
        dong.append({"account": TK_PHI, "debit": int(phi), "note": f"Phí thẻ {d.ma}"})
    dong.append({"account": TK_THU_HO, "credit": int(t.so_tien), "partner": ten, "partner_code": ma_dt, "note": d.ma})
    t.but_toan = _ghi_so(db, u, d, now.date(), f"Thu hộ nhà hàng — đặt bàn {d.ma} (thẻ, GD {t.so_gd_cong})", dong,
                         f"{d.ma}:tt{t.id}", "thu_tien_khach")
    t.phi_the = int(phi)
    t.trang_thai, t.xac_nhan_boi, t.xac_nhan_luc = "da_doi_soat", u.username, now
    R.audit(db, u.username, u.role, "dat_ban_doi_soat_the", f"thanh_toan_dat_ban:{t.id}",
            after={"so_tien": int(t.so_tien), "phi": int(phi), "but_toan": t.but_toan})
    db.flush()
    return t


def sales_huy(db: Session, u: User, did: int, ly_do: str, mien_phat: bool, now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    if u.role not in VAI_SALES + VAI_MIEN_PHAT:
        raise LoiDatBan("Chỉ Kinh doanh hủy đơn đặt bàn", 403)
    if mien_phat and u.role not in VAI_MIEN_PHAT:
        raise LoiDatBan("Hủy miễn phạt cần TP / GĐ Kinh doanh", 403)
    if len((ly_do or "").strip()) < 5:
        raise LoiDatBan("Ghi lý do hủy")
    d = _huy(db, _don(db, did), u.username, ly_do, now, mien_phat)
    R.audit(db, u.username, u.role, "dat_ban_huy_noi_bo", f"dat_ban:{d.ma}", after={"mien_phat": d.mien_phat, "giu": d.so_giu, "hoan": d.so_hoan})
    db.flush()
    return d


def sales_xac_nhan_hoan(db: Session, u: User, did: int, ghi_chu: str, now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    if u.role not in VAI_SALES + VAI_MIEN_PHAT:
        raise LoiDatBan("Chỉ Kinh doanh xác nhận hoàn", 403)
    d = _don(db, did)
    if d.hoan_tt != "cho_sales":
        raise LoiDatBan("Đơn không chờ Sales xác nhận hoàn", 409)
    d.hoan_tt = "cho_chi"
    d.hoan_ghi_chu = (((d.hoan_ghi_chu + "\n") if d.hoan_ghi_chu else "") + f"Sales {u.username}: {(ghi_chu or '').strip()}")[-1000:]
    R.audit(db, u.username, u.role, "dat_ban_xac_nhan_hoan", f"dat_ban:{d.ma}", after={"so_hoan": d.so_hoan})
    db.flush()
    return d


def kt_da_hoan(db: Session, u: User, did: int, ghi_chu: str, now: datetime | None = None) -> DonDatBan:
    now = now or datetime.now()
    if u.role not in VAI_KE_TOAN:
        raise LoiDatBan("Chỉ Kế toán ghi đã hoàn", 403)
    d = _don(db, did)
    if d.hoan_tt != "cho_chi":
        raise LoiDatBan("Đơn chưa được Sales xác nhận hoàn", 409)
    if len((ghi_chu or "").strip()) < 3:
        raise LoiDatBan("Ghi chứng từ hoàn (mã hoàn OnePay / số UNC)")
    lan = int(d.so_hoan or 0) - int(d.da_hoan_tien or 0)
    if lan <= 0:
        raise LoiDatBan("Không còn số phải hoàn", 409)
    ten, ma_dt = _doi_tuong_nh(db, d)
    from app.models.accounting import JournalEntry
    n = (db.execute(select(func.count(JournalEntry.id)).where(JournalEntry.source_type == "dat_ban",
                                                            JournalEntry.source_ref.like(f"{d.ma}:hoan%"))).scalar() or 0) + 1
    ma_ct = _ghi_so(db, u, d, now.date(), f"Hoàn khách — đặt bàn {d.ma} ({ghi_chu.strip()[:60]})",
                    [{"account": TK_THU_HO, "debit": lan, "partner": ten, "partner_code": ma_dt, "note": d.ma},
                     {"account": TK_TIEN, "credit": lan, "note": ghi_chu.strip()[:200]}], f"{d.ma}:hoan{n}", "chi_tien")
    d.da_hoan_tien = int(d.so_hoan)
    d.hoan_tt, d.hoan_boi, d.hoan_luc = "da_hoan", u.username, now
    d.hoan_ghi_chu = ((d.hoan_ghi_chu + "\n") if d.hoan_ghi_chu else "") + f"Kế toán {u.username}: hoàn {lan:,} đ · {ma_ct} · {ghi_chu.strip()}"[:500]
    R.audit(db, u.username, u.role, "dat_ban_da_hoan", f"dat_ban:{d.ma}", after={"so_hoan": lan, "but_toan": ma_ct})
    db.flush()
    return d


def kt_chot(db: Session, u: User, did: int, doanh_so: int, now: datetime | None = None, hoa_hong: int | None = None) -> DonDatBan:
    """Kế toán chốt doanh số + hoa hồng nhà hàng (KS-16d). Phải trả nhà hàng = thu hộ − hoàn + voucher VTD chịu − hoa hồng;
    > 0 → máy lập ngay một đề nghị chi trả nhà hàng (TP Điều hành xác nhận). Hoa hồng bỏ trống = 0."""
    now = now or datetime.now()
    if u.role not in VAI_KE_TOAN:
        raise LoiDatBan("Chỉ Kế toán chốt doanh số", 403)
    d = _don(db, did)
    if d.trang_thai != "da_dung":
        raise LoiDatBan("Chỉ chốt khi nhà hàng đã báo khách đã dùng", 409)
    if d.doanh_so is not None:
        raise LoiDatBan("Đơn đã chốt doanh số — đã khóa", 409)
    if doanh_so is None or int(doanh_so) <= 0:
        raise LoiDatBan("Ghi doanh số")
    giu = da_tra(db, d) - int(d.so_hoan or 0) + khuyen_mai(db, d)
    hh = int(hoa_hong or 0)
    if not (0 <= hh <= max(giu, 0)):
        raise LoiDatBan(f"Ghi hoa hồng theo hợp đồng, 0 – {max(giu, 0):,} đ".replace(",", "."))
    d.doanh_so, d.chot_boi, d.chot_luc = int(doanh_so), u.username, now
    d.hoa_hong, d.phai_tra_nh = hh, max(giu, 0) - hh
    if khuyen_mai(db, d) > 0 and not d.km_but_toan:          # KS-16b
        kt_ghi_km(db, u, d.id, now)
    R.audit(db, u.username, u.role, "dat_ban_chot_doanh_so", f"dat_ban:{d.ma}",
            after={"doanh_so": int(doanh_so), "bill": d.bill_thuc_te, "hoa_hong": hh, "phai_tra_nh": d.phai_tra_nh})
    db.flush()
    if (d.phai_tra_nh or 0) == 0 and hh > 0:          # KS-16e: không còn gì trả nhà hàng → ghi doanh thu hoa hồng ngay
        ghi_dt_hoa_hong(db, u, d, now.date())
    if (d.phai_tra_nh or 0) > 0:
        from app.services.don_ks_vtd import LoiDon, lap_de_nghi_chi_ncc
        nh = db.get(NhaHang, d.nha_hang_id)
        try:
            r = lap_de_nghi_chi_ncc(db, u, nh.supplier_id if nh else None, nh.ten if nh else "Nhà hàng", int(d.phai_tra_nh),
                                    f"Trả nhà hàng {nh.ten if nh else ''} — đặt bàn {d.ma} ngày {d.ngay:%d/%m/%Y}, tiền thu hộ "
                                    f"sau hoa hồng {hh:,} đ".replace(",", "."), f"Đặt bàn {d.ma}")
        except LoiDon as ex:
            raise LoiDatBan(str(ex), 409)
        d.payment_request_id = r.id
        db.flush()
    return d


def tong_vtos(db: Session, u: User, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    ds = db.execute(select(DonDatBan).order_by(DonDatBan.id.desc()).limit(300)).scalars().all()
    for d in ds:
        cap_nhat(db, d, now)
    db.commit()
    don = [ra(db, d, now, noi_bo=True) for d in ds]
    the = []
    for t in db.execute(select(ThanhToanDatBan).where(ThanhToanDatBan.kenh.in_(("onepay", "sepay")), ThanhToanDatBan.trang_thai == "thanh_cong")
                        .order_by(ThanhToanDatBan.id)).scalars():
        d = db.get(DonDatBan, t.don_id)
        the.append({"id": t.id, "ma": d.ma, "so_tien": int(t.so_tien), "so_gd_cong": t.so_gd_cong, "ma_gd": t.ma_gd,
                    "luc": t.luc.isoformat(timespec="minutes")})
    return {"don": don, "giao_dich_cho": giao_dich_cho(db, now), "the_cho_doi_soat": the, "the_bat": SP.cong_the_bat(),
            "tham_so": tham_so(db),
            "quyen": {"ke_toan": u.role in VAI_KE_TOAN, "sales": u.role in VAI_SALES + VAI_MIEN_PHAT, "mien_phat": u.role in VAI_MIEN_PHAT}}


# ====================================================================== nguồn D06
def nguon_d06(db: Session, d0: date, d1: date) -> dict:
    """{(doi_tac_id, 0): [nguồn]} — đơn đặt bàn qua đối tác đã dùng và Kế toán đã chốt, vào tháng của
    ngày MUỘN HƠN giữa ngày ăn và ngày chốt (cùng lẽ «tour kết thúc và thu đủ»)."""
    nhom: dict = {}
    for d in db.execute(select(DonDatBan).where(DonDatBan.doi_tac_id.is_not(None), DonDatBan.trang_thai == "da_dung",
                                                DonDatBan.doanh_so.is_not(None))).scalars():
        ngay = max(d.ngay, d.chot_luc.date())
        if not (d0 <= ngay < d1):
            continue
        nh = db.get(NhaHang, d.nha_hang_id)
        nhom.setdefault((d.doi_tac_id, 0), []).append({
            "booking_id": None, "booking": d.ma, "tour": "", "ten_tour": f"Đặt bàn {nh.ten if nh else ''}".strip(),
            "ket_thuc": d.ngay.isoformat(), "thu_du": d.chot_luc.date().isoformat(), "doanh_so": int(round(float(d.doanh_so or 0)))})
    return nhom
