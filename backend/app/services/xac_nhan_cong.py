# -*- coding: utf-8 -*-
"""CN-1 · XÁC NHẬN CÔNG THÁNG (Chủ tịch chốt 21/10/2026).

Trước bản này VTOS không có bước nào nói «số công của phòng này tháng này đã có người chịu trách
nhiệm». Bảng chấm công ai sửa cũng được tới phút chót, bảng lương đọc số HCNS gõ tay, và hồ sơ nhân
viên báo «Hệ thống chưa có cửa nhập» cho ô «Được xác nhận công».

LUẬT, mỗi dòng một quyết định của Chủ tịch:
  · HCNS lập và xác nhận → TGĐ duyệt. Chủ tịch duyệt được (quyền của Chủ tịch là toàn diện).
  · Đơn nghỉ KHÔNG đổi: trưởng phòng vẫn ký đơn của phòng mình (`hrm.TUYEN_KY_DON`).
  · Áp dụng cho phòng chấm công theo ngày và phòng báo cáo công việc trước 20 giờ. Hướng dẫn (theo
    chuyến) và Đội xe (lương + công tác phí) KHÔNG áp dụng — tập phòng lấy từ `luong.CHE_DO_CONG`,
    không gõ lại danh sách.
  · Hạn xác nhận: ngày 3 tháng sau; quá hạn thì chuông đỏ.
  · Phòng chưa được duyệt công thì bảng lương CHẶN. Vòng CN-2 sẽ đổi thành «giữ lương riêng phòng
    ấy»; tới lúc đó chặn cả kỳ (Chủ tịch chọn an toàn hơn để lương trôi qua).

HIỆU LỰC TÍNH LẠI MỖI LẦN ĐỌC. Lúc HCNS bấm, máy chụp các con số và lấy dấu. Đọc lại thì so dấu của
số HÔM NAY với dấu đã chụp; khác nhau là «số đã đổi sau khi xác nhận» và cả hai bước phải làm lại.
Không có cờ nào phải nhớ bật ở chỗ sửa công.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Alert, User
from app.models.hr import Employee
from app.models.hrm import LeaveRequest, XacNhanCong
from app.models.ops import DailyReport

VAI_XAC_NHAN = ("hcns",)
VAI_DUYET = ("tgd", "chutich")
HAN_NGAY = 3                       # ngày 3 tháng sau
CHUONG_HCNS, CHUONG_TGD = "cong_cho_hcns", "cong_cho_tgd"

TRANG_THAI = {
    "chua": "Chưa xác nhận",
    "hcns_xac_nhan": "HCNS đã xác nhận – chờ TGĐ duyệt",
    "da_duyet": "TGĐ đã duyệt",
    "het_hieu_luc": "Số đã đổi sau khi xác nhận – cần xác nhận lại",
}


class LoiXacNhan(ValueError):
    pass


# ------------------------------------------------------------------ phạm vi
def phong_ap_dung() -> dict[str, str]:
    """{phòng: chế độ công} của các phòng phải xác nhận công."""
    from app.services import luong as L
    return {p: cd for p, cd in L.CHE_DO_CONG.items() if cd in (L.CHAM_CONG, L.BAO_CAO_NGAY)}


def ky_hop_le(period: str) -> str:
    try:
        y, m = int(period[:4]), int(period[5:7])
        assert len(period) == 7 and period[4] == "-" and 1 <= m <= 12
    except Exception:
        raise LoiXacNhan(f"Kỳ không hợp lệ: {period} (dạng YYYY-MM)")
    if (y, m) > (date.today().year, date.today().month):
        raise LoiXacNhan(f"Kỳ {period} chưa bắt đầu – không xác nhận công trước")
    return period


def han_cua_ky(period: str) -> date:
    y, m = int(period[:4]), int(period[5:7])
    return date(y + (m == 12), 1 if m == 12 else m + 1, HAN_NGAY)


# ------------------------------------------------------------------ số liệu
def so_lieu(db: Session, period: str, phong: str) -> list[dict]:
    """Các con số được xác nhận của MỘT phòng trong MỘT kỳ, mỗi người một dòng, xếp theo mã."""
    from app.services import hrm as H
    from app.services import luong as L
    cd = phong_ap_dung().get(phong)
    if cd is None:
        raise LoiXacNhan(f"Phòng {phong} không áp dụng xác nhận công")
    ngay = H.month_days(period)
    dau, cuoi = ngay[0], ngay[-1]
    emps = list(db.execute(select(Employee).where(Employee.active == True, Employee.department == phong)  # noqa: E712
                           .order_by(Employee.code)).scalars())
    nghi = dict(db.execute(
        select(LeaveRequest.employee_id, func.coalesce(func.sum(LeaveRequest.days), 0))
        .where(LeaveRequest.status == "duyet", LeaveRequest.date_from >= dau, LeaveRequest.date_from <= cuoi)
        .group_by(LeaveRequest.employee_id)).all())
    ra: list[dict] = []
    if cd == L.CHAM_CONG:
        bang = {r["employee_id"]: r for r in H.attendance_sheet(db, period, phong)["rows"]}
        for e in emps:
            r = bang.get(e.id, {})
            ra.append({"employee_id": e.id, "ma": e.code, "ho_ten": e.full_name,
                       "cong": r.get("work_days", 0.0), "ngay_phep": r.get("leave_days", 0.0),
                       "ngay_khong_luong": r.get("unpaid_days", 0.0),
                       "nghi_da_duyet": float(nghi.get(e.id, 0)), "can_xem": ""})
        return ra
    # Báo cáo công việc trước 20 giờ. Chỉ đếm ngày làm việc đã qua: giữa tháng, ngày mai chưa tới
    # thì chưa phải ngày «không báo cáo».
    lam_viec = [d for d in ngay if d.weekday() < 5 and d <= date.today()]
    for e in emps:
        if e.user_id is None:
            ra.append({"employee_id": e.id, "ma": e.code, "ho_ten": e.full_name, "ngay_bao_cao": 0,
                       "dung_gio": 0, "tp_da_cham": 0, "nghi_da_duyet": float(nghi.get(e.id, 0)),
                       "can_xem": "Hồ sơ chưa nối tài khoản – không đếm được báo cáo ngày"})
            continue
        bc = list(db.execute(select(DailyReport).where(DailyReport.user_id == e.user_id,
                                                       DailyReport.report_date >= dau,
                                                       DailyReport.report_date <= cuoi)).scalars())
        ngay_bc = {b.report_date for b in bc}
        nghi_n = float(nghi.get(e.id, 0))
        thieu = max(0, len([d for d in lam_viec if d not in ngay_bc]) - int(nghi_n))
        ra.append({"employee_id": e.id, "ma": e.code, "ho_ten": e.full_name,
                   "ngay_bao_cao": len(ngay_bc), "dung_gio": sum(1 for b in bc if b.on_time),
                   "tp_da_cham": sum(1 for b in bc if b.manager_score is not None),
                   "nghi_da_duyet": nghi_n,
                   "can_xem": f"{thieu} ngày không báo cáo, không đơn nghỉ" if thieu else ""})
    return ra


def van_tay(dong: list[dict]) -> str:
    """Dấu của các con số NGUỒN. Bỏ cột «cần xem»: nó là lời nhắc suy ra, và giữa tháng nó đổi mỗi
    ngày theo đồng hồ — để nó vào dấu thì một xác nhận hết hiệu lực chỉ vì sang ngày mới."""
    nguon = [{k: v for k, v in d.items() if k != "can_xem"} for d in dong]
    return hashlib.sha256(json.dumps(nguon, sort_keys=True, ensure_ascii=False, default=str)
                          .encode()).hexdigest()


# ------------------------------------------------------------------ trạng thái
def _dong(db: Session, period: str, phong: str) -> XacNhanCong | None:
    return db.execute(select(XacNhanCong).where(XacNhanCong.period == period,
                                                XacNhanCong.phong == phong)).scalars().first()


def trang_thai(db: Session, period: str, phong: str, dong_so: list[dict] | None = None) -> dict:
    x = _dong(db, period, phong)
    if x is None or x.hcns_at is None:
        tt = "chua"
    else:
        hien = dong_so if dong_so is not None else so_lieu(db, period, phong)
        if van_tay(hien) != x.van_tay:
            tt = "het_hieu_luc"
        else:
            tt = "da_duyet" if x.tgd_at else "hcns_xac_nhan"
    return {"period": period, "phong": phong, "trang_thai": tt, "trang_thai_ten": TRANG_THAI[tt],
            "hcns_by": x.hcns_by if x else "", "hcns_at": x.hcns_at if x else None,
            "tgd_by": x.tgd_by if x else "", "tgd_at": x.tgd_at if x else None,
            "han": han_cua_ky(period), "qua_han": tt != "da_duyet" and date.today() > han_cua_ky(period)}


def bang_ky(db: Session, period: str) -> dict:
    """Toàn bộ kỳ: mỗi phòng áp dụng một khối (trạng thái + số liệu hôm nay)."""
    from app.services import luong as L
    from app.models.hr import DEPARTMENTS
    ky_hop_le(period)
    khoi = []
    for p, cd in phong_ap_dung().items():
        dong_so = so_lieu(db, period, p)
        khoi.append({**trang_thai(db, period, p, dong_so), "phong_ten": DEPARTMENTS.get(p, p),
                     "che_do": cd, "che_do_ten": L.CHE_DO_LABEL.get(cd, cd), "dong": dong_so})
    return {"period": period, "han": han_cua_ky(period), "phong": khoi, "trang_thai": TRANG_THAI}


# ------------------------------------------------------------------ hai bước
def hcns_xac_nhan(db: Session, u: User, period: str, phong: str) -> XacNhanCong:
    from app.services import rules as R
    if u.role not in VAI_XAC_NHAN:
        raise PermissionError("Chỉ HCNS lập và xác nhận công")
    ky_hop_le(period)
    dong_so = so_lieu(db, period, phong)
    x = _dong(db, period, phong)
    if x is None:
        x = XacNhanCong(period=period, phong=phong)
        db.add(x)
    elif x.tgd_at and van_tay(dong_so) == x.van_tay:
        raise LoiXacNhan(f"Công phòng {phong} kỳ {period} đã được duyệt và số chưa đổi – không cần xác nhận lại")
    # Xác nhận lại là xoá chữ duyệt cũ: TGĐ đã duyệt một bộ số KHÁC.
    x.so_lieu, x.van_tay = dong_so, van_tay(dong_so)
    x.hcns_by, x.hcns_at = u.username, datetime.now()
    x.tgd_by, x.tgd_vai, x.tgd_at = "", "", None
    R.audit(db, u.username, u.role, "hcns_xac_nhan_cong", f"cong:{period}:{phong}",
            after={"so_nguoi": len(dong_so), "van_tay": x.van_tay[:12]})
    _tat_chuong(db, period, phong, "hcns", "HCNS đã xác nhận")
    _bao_chuong(db, period, phong, "tgd")
    db.commit()
    return x


def tgd_duyet(db: Session, u: User, period: str, phong: str) -> XacNhanCong:
    from app.services import rules as R
    if u.role not in VAI_DUYET:
        raise PermissionError("Chỉ TGĐ (hoặc Chủ tịch) duyệt công")
    x = _dong(db, period, phong)
    if x is None or x.hcns_at is None:
        raise LoiXacNhan("HCNS chưa xác nhận công của phòng này")
    if x.tgd_at:
        raise LoiXacNhan("Công phòng này kỳ này đã được duyệt")
    if van_tay(so_lieu(db, period, phong)) != x.van_tay:
        # 409 ở cửa HTTP: số đã đổi sau khi HCNS bấm — người duyệt đang nhìn một bộ số không còn đúng.
        raise LoiXacNhan("Số đã đổi sau khi HCNS xác nhận – HCNS phải xác nhận lại trước khi duyệt")
    x.tgd_by, x.tgd_vai, x.tgd_at = u.username, u.role, datetime.now()
    R.audit(db, u.username, u.role, "duyet_cong", f"cong:{period}:{phong}", after={"van_tay": x.van_tay[:12]})
    _tat_chuong(db, period, phong, "tgd", "TGĐ đã duyệt")
    db.commit()
    return x


# ------------------------------------------------------------------ bảng lương
def phong_chua_duyet(db: Session, period: str, ma_nv: list[str]) -> list[dict]:
    """Phòng có người trong bảng lương mà công kỳ này chưa được duyệt (hoặc đã hết hiệu lực)."""
    ap = phong_ap_dung()
    can = sorted({e.department for e in db.execute(select(Employee).where(Employee.code.in_(ma_nv))).scalars()
                  if e.department in ap}) if ma_nv else []
    ra = []
    for p in can:
        t = trang_thai(db, period, p)
        if t["trang_thai"] != "da_duyet":
            ra.append(t)
    return ra


def chan_ky_luong(db: Session, run) -> None:
    """Gọi NGAY TRƯỚC chữ ký bảng lương. Không phân vai: ai ký cũng dừng như nhau."""
    chua = phong_chua_duyet(db, run.period, [r.get("ma") for r in run.rows or [] if r.get("ma")])
    if chua:
        raise ValueError("Chưa ký được: công chưa duyệt ở " +
                         "; ".join(f"{t['phong']} ({t['trang_thai_ten']})" for t in chua))


# ------------------------------------------------------------------ chuông
def _ref(period: str, phong: str) -> str:
    return f"cong:{period}:{phong}"


def _bao_chuong(db: Session, period: str, phong: str, buoc: str, do: bool = False) -> None:
    from app.services import cskh as CS
    kind = CHUONG_HCNS if buoc == "hcns" else CHUONG_TGD
    viec = "HCNS xác nhận công" if buoc == "hcns" else "TGĐ duyệt công"
    CS.giao_viec(db, kind, _ref(period, phong),
                 f"{viec} phòng {phong} kỳ {period} — hạn {han_cua_ky(period):%d/%m/%Y}; "
                 "chưa duyệt thì bảng lương kỳ ấy bị chặn",
                 nguoi_id=None, han_gio=None, roles="hcns" if buoc == "hcns" else "tgd,chutich",
                 level="red" if do else "warn")


def _tat_chuong(db: Session, period: str, phong: str, buoc: str, ly_do: str) -> int:
    kind = CHUONG_HCNS if buoc == "hcns" else CHUONG_TGD
    n = 0
    for a in db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == _ref(period, phong),
                                            Alert.resolved == False)).scalars():  # noqa: E712
        a.resolved, a.trang_thai, a.bang_chung = True, "dong", f"Tự đóng: {ly_do}"
        n += 1
    return n


def quet(db: Session, hom_nay: date | None = None) -> int:
    """Robot: từ ngày 1 tháng sau, kỳ vừa qua phòng nào chưa xong thì có chuông cho đúng bước.

    Quá hạn (sau ngày 3) thì chuông chuyển đỏ: chuông vàng cũ đóng, chuông đỏ mở. Kỳ đã duyệt thì
    mọi chuông của nó đóng. Chỉ soi KỲ VỪA QUA — kỳ cũ hơn nếu còn sót thì bảng lương đã chặn nó.
    """
    d = hom_nay or date.today()
    ky = f"{d.year - (d.month == 1)}-{12 if d.month == 1 else d.month - 1:02d}"
    do = d > han_cua_ky(ky)
    moi = 0
    for p in phong_ap_dung():
        tt = trang_thai(db, ky, p)["trang_thai"]
        if tt == "da_duyet":
            _tat_chuong(db, ky, p, "hcns", "đã duyệt"); _tat_chuong(db, ky, p, "tgd", "đã duyệt")
            continue
        buoc = "tgd" if tt == "hcns_xac_nhan" else "hcns"
        _tat_chuong(db, ky, p, "tgd" if buoc == "hcns" else "hcns", "chuyển bước")
        kind = CHUONG_HCNS if buoc == "hcns" else CHUONG_TGD
        cu = db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == _ref(ky, p),
                                            Alert.resolved == False)).scalars().first()  # noqa: E712
        if cu is not None and do and cu.level != "red":
            _tat_chuong(db, ky, p, buoc, "quá hạn – chuyển chuông đỏ")
            db.flush()
            cu = None
        if cu is None:
            _bao_chuong(db, ky, p, buoc, do=do)
            moi += 1
    db.commit()
    return moi


# ------------------------------------------------------------------ hồ sơ nhân viên
def cho_ho_so(db: Session, e: Employee, hom_nay: date | None = None) -> str:
    """Câu cho ô «Được xác nhận công»: trạng thái của kỳ vừa qua của phòng người này."""
    d = hom_nay or date.today()
    if e.department not in phong_ap_dung():
        return "Không áp dụng (lương theo chuyến / công tác phí)"
    ky = f"{d.year - (d.month == 1)}-{12 if d.month == 1 else d.month - 1:02d}"
    t = trang_thai(db, ky, e.department)
    if t["trang_thai"] == "da_duyet":
        return f"Kỳ {ky}: đã duyệt ({t['tgd_by']}, {t['tgd_at']:%d/%m/%Y})"
    return f"Kỳ {ky}: {t['trang_thai_ten'].lower()}"
