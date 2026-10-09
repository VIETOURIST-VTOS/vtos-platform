"""5.6 Đánh giá nhân sự — phép tính, và chỗ nào VTOS CHƯA có số thì nói ra là chưa có.

Chủ tịch chốt 08–09/10/2026: trưởng phòng chấm, nhân viên đọc được bản của mình, HCNS và TGĐ/Chủ
tịch tổng hợp; kỳ tháng/quý/năm; điểm CHỈ ĐỂ XÉT thưởng — không có công thức trả tiền.

BA NGUYÊN TẮC CỦA TỆP NÀY

1. KHÔNG BỊA MỘT CON SỐ ĐỂ Ô KHÔNG TRỐNG. Ô máy điền nào chưa có nguồn thì trả `None` kèm MỘT CÂU
   nói rõ thiếu nguồn gì. Chấm 3 cho qua chuyện là đưa một con số bịa vào bảng đem đi xét thưởng —
   mà một con số bịa trông y hệt một con số thật khi đã nằm trong cột.

2. MỖI Ô PHẢI NÓI ĐƯỢC NGUỒN. `*_nguon` không phải chú thích cho đẹp: người bị chấm 2 điểm mà không
   biết con số ấy từ đâu ra thì không có cách nào cãi, và một thang điểm không cãi được thì không ai
   tin. Nguồn in thẳng lên màn hình cạnh điểm.

3. THIẾU NGUỒN LÀ VIỆC CÒN PHẢI LÀM, KHÔNG PHẢI MỘT TRẠNG THÁI YÊN. `thieu_nguon()` đếm chúng và
   màn hình in ra, nên chỗ hở không chìm đi sau vài kỳ.

ĐIỂM ĐẺ RA TIỀN THÌ ĐIỂM SẼ TRÔI — `do_lech_nguoi_may()` là cái neo.
Ba ô máy điền không ai sửa được (không cửa ghi nào nhận chúng). Trưởng phòng chấm tay cao hơn số máy
một cách đều đặn thì hiện ra ngay kỳ sau, không phải đợi hết năm.
"""
from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import Employee, Incident
from app.models.hrm import AttendanceDay
from app.models.core import User
from app.models.nhan_su_danh_gia import (
    DanhGiaNhanSu, KY_LOAI, KY_TU_TONG_HOP, THANG_DIEM, O_MAY_DIEN, O_NGUOI_CHAM,
    DIEM_BAT_BUOC_LY_DO, XEP_HANG, XEP_HANG_PHAI_GHI_VIEC, DG_TRANG_THAI,
)
from app.services import hrm as HRM

O_MAY = ("a1", "a2", "a3")
O_NGUOI = ("b1", "b2", "b3")
MOI_O = O_MAY + O_NGUOI


# ══════════════════════════════════════════════════════════════════════════════════════════════
# KỲ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def kiem_ky(ky_loai: str, ky: str) -> str:
    """Trả về `ky` đã chuẩn hoá, hoặc ném ValueError. Dạng kỳ SAI thì bảng tổng hợp sẽ gom nhầm."""
    if ky_loai not in KY_LOAI:
        raise ValueError(f"Loại kỳ không hợp lệ: {ky_loai!r}. Chỉ có {', '.join(KY_LOAI)}.")
    ky = (ky or "").strip()
    if ky_loai == "thang":
        if len(ky) != 7 or ky[4] != "-" or not ky[:4].isdigit() or not ky[5:].isdigit() \
                or not 1 <= int(ky[5:]) <= 12:
            raise ValueError(f"Kỳ tháng phải dạng 2026-10, nhận được {ky!r}.")
    elif ky_loai == "quy":
        if len(ky) != 7 or ky[4:6] != "-Q" or not ky[:4].isdigit() or ky[6] not in "1234":
            raise ValueError(f"Kỳ quý phải dạng 2026-Q4, nhận được {ky!r}.")
    else:
        if len(ky) != 4 or not ky.isdigit():
            raise ValueError(f"Kỳ năm phải dạng 2026, nhận được {ky!r}.")
    return ky


def ky_con(ky_loai: str, ky: str) -> list[tuple[str, str]]:
    """Các kỳ con của một kỳ tổng hợp: quý → ba tháng, năm → bốn quý. Kỳ tháng không có kỳ con."""
    if ky_loai == "quy":
        nam, q = ky[:4], int(ky[6])
        return [("thang", f"{nam}-{m:02d}") for m in range(q * 3 - 2, q * 3 + 1)]
    if ky_loai == "nam":
        return [("quy", f"{ky}-Q{q}") for q in (1, 2, 3, 4)]
    return []


def _bien_thang(ky: str) -> tuple[date, date]:
    nam, thang = int(ky[:4]), int(ky[5:])
    dau = date(nam, thang, 1)
    cuoi = date(nam + (thang == 12), (thang % 12) + 1, 1)
    return dau, cuoi


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BA Ô MÁY ĐIỀN
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# A1 — KẾT QUẢ THEO CHỈ TIÊU. Hai phòng Kinh doanh đã có đủ hai vế (chỉ tiêu và số thật), các phòng
# còn lại CHƯA. Khai thẳng từng phòng thiếu cái gì, thay vì mượn tạm một con số gần đúng: mượn tạm
# thì không ai biết nó là mượn, còn khai thiếu thì có người đi dựng nốt.
#
# LẺ ĐO DOANH THU, ĐOÀN ĐO LỢI NHUẬN — lấy đúng quy ước đã có ở `doanh_thu_kd` (tour đoàn giá trị
# lớn mà biên mỏng; đo doanh thu đoàn là dạy người bán hạ giá để chạy số).
NGUON_A1_CHUA_CO = {
    "dieu_hanh": "chưa có bộ đếm chuyến điều hành đúng hạn theo từng người",
    "visa":      "chưa có bộ đếm hồ sơ visa đúng hạn theo từng người",
    "doi_xe":    "chưa có bộ đếm ngày xe chạy không sự cố theo từng tài xế",
    "huong_dan": "chưa có chỉ tiêu cho hướng dẫn viên",
    "marketing": "chưa có chỉ tiêu theo người cho Marketing",
    "cntt":      "công việc không đo bằng chỉ tiêu số",
    "ketoan":    "công việc không đo bằng chỉ tiêu số",
    "hcns":      "công việc không đo bằng chỉ tiêu số",
    "ban_tgd":   "không chấm theo chỉ tiêu phòng",
}
BAC_A1 = ((1.20, 5), (1.00, 4), (0.80, 3), (0.50, 2), (0.0, 1))


def _a1(db: Session, nv: Employee, ky_loai: str, ky: str) -> tuple[int | None, str]:
    phong = nv.department or ""
    if phong not in ("kd_le", "kd_doan"):
        vi_sao = NGUON_A1_CHUA_CO.get(phong, "phòng này chưa khai nguồn chỉ tiêu")
        return None, f"chưa có số — {vi_sao}"
    if ky_loai != "thang":
        return None, "chỉ tiêu đặt theo tháng; kỳ quý và năm lấy trung bình các tháng đã chấm"
    if not nv.user_id:
        return None, "chưa có số — hồ sơ nhân sự này chưa nối với một tài khoản đăng nhập"

    from app.models.chi_tieu_kd import ChiTieuKD
    from app.services import doanh_thu_kd as DT

    luong = "le" if phong == "kd_le" else "doan"
    muc = db.execute(
        select(ChiTieuKD).where(ChiTieuKD.ky == ky, ChiTieuKD.user_id == nv.user_id,
                               ChiTieuKD.luong.in_((luong, "tat_ca")))
    ).scalars().first()
    if muc is None or not float(muc.muc_tieu or 0):
        return None, f"chưa có số — kỳ {ky} chưa ai đặt chỉ tiêu cho người này"

    muc_tieu = float(muc.muc_tieu)
    if luong == "le":
        that = float(DT.cua_nguoi(db, nv.user_id, ky, "le").get("tien") or 0)
        ten_so = "doanh thu lẻ"
    else:
        that = float(DT.ln_doan_cua_ky(db, nv.user_id, ky) or 0)
        ten_so = "lợi nhuận đoàn quyết toán"
    ty_le = that / muc_tieu if muc_tieu else 0.0
    for nguong, diem in BAC_A1:
        if ty_le >= nguong:
            return diem, f"{ten_so} {that:,.0f} / chỉ tiêu {muc_tieu:,.0f} = {ty_le*100:.0f}%"
    return 1, f"{ten_so} {that:,.0f} / chỉ tiêu {muc_tieu:,.0f} = {ty_le*100:.0f}%"


# A2 — KỶ LUẬT THỜI GIAN. Đếm ngày `vang` (nghỉ không phép) trên bảng chấm công.
#
# VẾ CÒN THIẾU PHẢI NÓI RA: bộ tiêu chí Chủ tịch ký có thêm "chuyến quyết toán quá hạn", mà VTOS
# chưa có bộ đếm quá hạn quyết toán GẮN VỚI TỪNG NGƯỜI. Im lặng bỏ vế ấy thì điểm A2 trông như đã
# đếm đủ; nên nó nằm trong `a2_nguon` và trong `thieu_nguon()`.
A2_VE_CHUA_NOI = "chưa nối: số chuyến quyết toán quá hạn theo từng người"


def _a2(db: Session, nv: Employee, ky_loai: str, ky: str) -> tuple[int | None, str]:
    if ky_loai != "thang":
        return None, "kỳ quý và năm lấy trung bình các tháng đã chấm"
    dau, cuoi = _bien_thang(ky)
    vang = db.execute(
        select(AttendanceDay).where(AttendanceDay.employee_id == nv.id,
                                    AttendanceDay.day >= dau, AttendanceDay.day < cuoi,
                                    AttendanceDay.kind == "vang")
    ).scalars().all()
    co_cham_cong = db.execute(
        select(AttendanceDay.id).where(AttendanceDay.employee_id == nv.id,
                                       AttendanceDay.day >= dau, AttendanceDay.day < cuoi)
    ).first()
    if co_cham_cong is None:
        return None, f"chưa có số — kỳ {ky} chưa ai chấm công cho người này ({A2_VE_CHUA_NOI})"
    diem = max(1, 5 - len(vang))
    return diem, f"{len(vang)} ngày nghỉ không phép ({A2_VE_CHUA_NOI})"


# A3 — SỰ VỤ. Chỉ đếm biên bản ĐÃ CÓ HIỆU LỰC: biên bản đang khiếu nại thì chế tài đang treo, đếm
# nó vào điểm là kết luận thay người có thẩm quyền.
def _a3(db: Session, nv: Employee, ky_loai: str, ky: str) -> tuple[int | None, str]:
    if ky_loai != "thang":
        return None, "kỳ quý và năm lấy trung bình các tháng đã chấm"
    dau, cuoi = _bien_thang(ky)
    ds = db.execute(
        select(Incident).where(Incident.employee_id == nv.id, Incident.level >= 2,
                               Incident.occurred_on >= dau, Incident.occurred_on < cuoi,
                               Incident.effective_at.is_not(None))
    ).scalars().all()
    m2 = sum(1 for i in ds if i.level == 2)
    m3 = sum(1 for i in ds if i.level >= 3)
    if m3 >= 2:
        diem = 1
    elif m3 == 1:
        diem = 2
    elif m2 >= 2:
        diem = 3
    elif m2 == 1:
        diem = 4
    else:
        diem = 5
    return diem, f"{m2} sự vụ mức 2, {m3} sự vụ mức 3 (đã có hiệu lực)"


def may_dien(db: Session, nv: Employee, ky_loai: str, ky: str) -> dict:
    """Ba ô máy điền của một người trong một kỳ. Trưởng phòng KHÔNG sửa được ba ô này."""
    a1, n1 = _a1(db, nv, ky_loai, ky)
    a2, n2 = _a2(db, nv, ky_loai, ky)
    a3, n3 = _a3(db, nv, ky_loai, ky)
    return {"a1_diem": a1, "a1_nguon": n1[:200], "a2_diem": a2, "a2_nguon": n2[:200],
            "a3_diem": a3, "a3_nguon": n3[:200]}


def thieu_nguon(db: Session, ky: str) -> dict:
    """Đếm chỗ hở: bao nhiêu người kỳ này KHÔNG có số cho A1, A2 — và vì sao.

    Không có hàm này thì "chưa có số" là một ô trống trên màn hình và không bao giờ thành việc.
    """
    nv_ds = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().all()
    theo_o: dict[str, dict[str, int]] = {"a1": {}, "a2": {}}
    for nv in nv_ds:
        for o, (diem, nguon) in (("a1", _a1(db, nv, "thang", ky)), ("a2", _a2(db, nv, "thang", ky))):
            if diem is None:
                theo_o[o][nguon] = theo_o[o].get(nguon, 0) + 1
    return {"ky": ky, "so_nguoi": len(nv_ds), "theo_o": theo_o,
            "tong_thieu": {o: sum(v.values()) for o, v in theo_o.items()}}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐIỂM TỔNG, XẾP HẠNG, VÀ NHỮNG Ô BẮT BUỘC VIẾT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def tinh_diem_tong(o: dict) -> tuple[float | None, str]:
    """Trung bình CÁC Ô CÓ SỐ. Ô "chưa có số" không kéo điểm xuống — nó không phải điểm 0."""
    co = [float(o[f"{k}_diem"]) for k in MOI_O if o.get(f"{k}_diem") is not None]
    if not co:
        return None, ""
    diem = round(sum(co) / len(co), 2)
    for nguong, khoa, _ten in XEP_HANG:
        if diem >= nguong:
            return diem, khoa
    return diem, XEP_HANG[-1][1]


def ten_xep_hang(khoa: str) -> str:
    return next((t for _n, k, t in XEP_HANG if k == khoa), "")


def thieu_chu(o: dict) -> list[str]:
    """Những ô BẮT BUỘC viết mà còn trống. Một bảng toàn điểm không có chữ nào không ai đọc lần hai."""
    thieu = []
    for k in O_NGUOI:
        d = o.get(f"{k}_diem")
        if d is not None and int(d) in DIEM_BAT_BUOC_LY_DO and not (o.get(f"{k}_ly_do") or "").strip():
            thieu.append(f"{k} ({O_NGUOI_CHAM[k]}) chấm {int(d)} điểm thì phải ghi lý do")
    _diem, hang = tinh_diem_tong(o)
    if hang in XEP_HANG_PHAI_GHI_VIEC and not (o.get("viec_phai_sua") or "").strip():
        thieu.append(f"xếp hạng {ten_xep_hang(hang)} thì bắt buộc ghi việc cụ thể phải sửa kỳ tới")
    return thieu


# ══════════════════════════════════════════════════════════════════════════════════════════════
# AI ĐƯỢC CHẤM — DÙNG LẠI TUYẾN KÝ ĐƠN NGHỈ, KHÔNG DỰNG TUYẾN THỨ HAI
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Hai tuyến sẽ lệch nhau ở lần đổi người thứ nhất, và lúc ấy không ai biết tuyến nào mới là tuyến
# Chủ tịch ký. Nên ở đây gọi thẳng `hrm.nguoi_ky_cua_phong`.
def vai_duoc_cham(phong: str) -> tuple[str, ...]:
    return HRM.nguoi_ky_don(phong)


def phong_khong_ai_cham(db: Session) -> list[dict]:
    """Phòng mà vai được chấm KHÔNG tài khoản nào giữ — y hệt chỗ hở của đơn nghỉ phép.

    Danh sách này phải IN RA màn hình: một phòng không có người chấm thì bảng của cả phòng ấy nằm
    im mà không dòng nào báo, và tới cuối quý mới có người hỏi.
    """
    return HRM.phong_khong_ai_giu_vai_ky(db)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MỞ BẢNG, CHẤM, GỬI
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _tom_tat(db: Session, r: DanhGiaNhanSu) -> dict:
    nv = db.get(Employee, r.employee_id)
    o = {k: getattr(r, k) for k in
         [f"{x}_diem" for x in MOI_O] + [f"{x}_ly_do" for x in O_NGUOI] + ["viec_phai_sua"]}
    return {
        "id": r.id, "employee_id": r.employee_id,
        "ho_ten": nv.full_name if nv else "", "ma_nv": nv.code if nv else "",
        "ky_loai": r.ky_loai, "ky": r.ky, "department": r.department,
        **{f"{k}_diem": getattr(r, f"{k}_diem") for k in MOI_O},
        **{f"{k}_nguon": getattr(r, f"{k}_nguon") for k in O_MAY},
        **{f"{k}_ly_do": getattr(r, f"{k}_ly_do") for k in O_NGUOI},
        "diem_tong": r.diem_tong, "xep_hang": r.xep_hang, "xep_hang_ten": ten_xep_hang(r.xep_hang),
        "nhan_xet": r.nhan_xet, "viec_phai_sua": r.viec_phai_sua, "de_xuat": r.de_xuat,
        "thieu_ky_con": r.thieu_ky_con, "thieu_chu": thieu_chu(o),
        "trang_thai": r.trang_thai, "trang_thai_ten": DG_TRANG_THAI.get(r.trang_thai, r.trang_thai),
        "nguoi_cham": r.nguoi_cham, "vai_nguoi_cham": r.vai_nguoi_cham,
        "cham_luc": r.cham_luc.isoformat() if r.cham_luc else None,
        "gui_luc": r.gui_luc.isoformat() if r.gui_luc else None,
    }


def mo_bang(db: Session, employee_id: int, ky_loai: str, ky: str) -> dict:
    """Mở (hoặc lấy lại) bản đánh giá của một người một kỳ, và NẠP LẠI ba ô máy điền.

    Nạp lại mỗi lần mở là có chủ ý: sự vụ có hiệu lực muộn, chấm công sửa sau. Ô máy điền phải theo
    số mới nhất cho tới lúc GỬI; gửi xong thì khoá — nếu không, bản HCNS đang đọc sẽ đổi dưới tay họ.
    """
    ky = kiem_ky(ky_loai, ky)
    nv = db.get(Employee, employee_id)
    if nv is None:
        raise ValueError(f"Không có hồ sơ nhân sự id={employee_id}.")
    r = db.execute(select(DanhGiaNhanSu).where(
        DanhGiaNhanSu.employee_id == employee_id,
        DanhGiaNhanSu.ky_loai == ky_loai, DanhGiaNhanSu.ky == ky)).scalars().first()
    if r is None:
        r = DanhGiaNhanSu(employee_id=employee_id, ky_loai=ky_loai, ky=ky,
                          department=nv.department or "")
        db.add(r)
    if r.trang_thai != "da_gui":
        if ky_loai in KY_TU_TONG_HOP:
            _tong_hop_vao(db, r)
        else:
            for k, v in may_dien(db, nv, ky_loai, ky).items():
                setattr(r, k, v)
        _tinh_lai(r)
    db.flush()
    return _tom_tat(db, r)


def _tinh_lai(r: DanhGiaNhanSu) -> None:
    o = {f"{k}_diem": getattr(r, f"{k}_diem") for k in MOI_O}
    r.diem_tong, r.xep_hang = tinh_diem_tong(o)


def cham(db: Session, boi: User, employee_id: int, ky_loai: str, ky: str, o: dict) -> dict:
    """Trưởng phòng chấm ba ô B. BA Ô A KHÔNG NHẬN GHI — cửa này bỏ qua chúng, có phép thử canh."""
    ky = kiem_ky(ky_loai, ky)
    nv = db.get(Employee, employee_id)
    if nv is None:
        raise ValueError(f"Không có hồ sơ nhân sự id={employee_id}.")
    vais = vai_duoc_cham(nv.department or "")
    if boi.role not in vais:
        raise PermissionError(
            f"Phòng {nv.department!r} do vai {', '.join(vais)} chấm; tài khoản này là {boi.role!r}. "
            "Tuyến chấm dùng lại đúng tuyến ký đơn nghỉ (hrm.TUYEN_KY_DON) — đổi tuyến là một quyết "
            "định của Chủ tịch, không phải một lần nới ở đây.")
    if nv.user_id and nv.user_id == boi.id:
        raise PermissionError("Không tự chấm bản của chính mình.")
    mo_bang(db, employee_id, ky_loai, ky)
    r = db.execute(select(DanhGiaNhanSu).where(
        DanhGiaNhanSu.employee_id == employee_id,
        DanhGiaNhanSu.ky_loai == ky_loai, DanhGiaNhanSu.ky == ky)).scalars().first()
    if r.trang_thai == "da_gui":
        raise ValueError("Bản này đã gửi HCNS — muốn sửa thì phải mở lại, và lần mở lại phải có dấu vết.")
    for k in O_NGUOI:
        if f"{k}_diem" in o:
            d = o[f"{k}_diem"]
            if d is not None and int(d) not in THANG_DIEM:
                raise ValueError(f"Ô {k} phải là điểm 1–5, nhận được {d!r}.")
            setattr(r, f"{k}_diem", None if d is None else int(d))
        if f"{k}_ly_do" in o:
            setattr(r, f"{k}_ly_do", (o[f"{k}_ly_do"] or "").strip())
    for k in ("nhan_xet", "viec_phai_sua", "de_xuat"):
        if k in o:
            setattr(r, k, (o[k] or "").strip())
    _tinh_lai(r)
    r.trang_thai = "da_cham"
    r.nguoi_cham, r.vai_nguoi_cham, r.cham_luc = boi.username, boi.role, datetime.now()
    db.flush()
    return _tom_tat(db, r)


def gui(db: Session, boi: User, danh_gia_id: int) -> dict:
    """Gửi HCNS / TGĐ. Chặn ở đây, không chặn lúc chấm: người chấm được phép lưu dở."""
    r = db.get(DanhGiaNhanSu, danh_gia_id)
    if r is None:
        raise ValueError(f"Không có bản đánh giá id={danh_gia_id}.")
    if r.trang_thai == "da_gui":
        raise ValueError("Bản này đã gửi rồi.")
    o = {f"{k}_diem": getattr(r, f"{k}_diem") for k in MOI_O}
    o.update({f"{k}_ly_do": getattr(r, f"{k}_ly_do") for k in O_NGUOI})
    o["viec_phai_sua"] = r.viec_phai_sua
    thieu = thieu_chu(o)
    if thieu:
        raise ValueError("Chưa gửi được, còn thiếu: " + "; ".join(thieu))
    if any(getattr(r, f"{k}_diem") is None for k in O_NGUOI):
        raise ValueError("Ba ô trưởng phòng chấm phải có đủ điểm trước khi gửi.")
    r.trang_thai, r.gui_luc = "da_gui", datetime.now()
    db.flush()
    return _tom_tat(db, r)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# QUÝ VÀ NĂM TỰ TỔNG HỢP — VÀ NÓI RA THIẾU KỲ NÀO
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _tong_hop_vao(db: Session, r: DanhGiaNhanSu) -> None:
    con = ky_con(r.ky_loai, r.ky)
    ban_con = []
    thieu = []
    for loai, k in con:
        b = db.execute(select(DanhGiaNhanSu).where(
            DanhGiaNhanSu.employee_id == r.employee_id,
            DanhGiaNhanSu.ky_loai == loai, DanhGiaNhanSu.ky == k)).scalars().first()
        if b is None or b.diem_tong is None:
            thieu.append(k)
        else:
            ban_con.append(b)
    for o in MOI_O:
        co = [float(getattr(b, f"{o}_diem")) for b in ban_con if getattr(b, f"{o}_diem") is not None]
        setattr(r, f"{o}_diem", round(sum(co) / len(co)) if co else None)
        if o in O_MAY:
            setattr(r, f"{o}_nguon",
                    (f"trung bình {len(co)} kỳ con có số" if co else "chưa kỳ con nào có số")[:200])
    # Thiếu kỳ con thì NÓI RA kỳ nào. Lấy hai tháng chia ba rồi im lặng là in ra một trung bình
    # trông y hệt trung bình đủ nguồn — và nó sẽ được đem đi xét thưởng như nhau.
    r.thieu_ky_con = (", ".join(thieu))[:200]


def do_lech_nguoi_may(db: Session, ky_loai: str, ky: str) -> dict:
    """Độ lệch "điểm người − điểm máy" theo từng người chấm, và phân bố điểm theo phòng.

    CÁI NEO của cả bộ. Ba ô máy điền không ai sửa được; ai chấm tay cao hơn số máy một cách đều đặn
    thì hiện ra ngay kỳ sau, không phải đợi hết năm. Kỳ đầu (chưa ra tiền) là MỐC SO.
    """
    ky = kiem_ky(ky_loai, ky)
    ds = db.execute(select(DanhGiaNhanSu).where(
        DanhGiaNhanSu.ky_loai == ky_loai, DanhGiaNhanSu.ky == ky)).scalars().all()
    theo_nguoi: dict[str, dict] = {}
    theo_phong: dict[str, dict] = {}
    for r in ds:
        may = [float(getattr(r, f"{k}_diem")) for k in O_MAY if getattr(r, f"{k}_diem") is not None]
        nguoi = [float(getattr(r, f"{k}_diem")) for k in O_NGUOI if getattr(r, f"{k}_diem") is not None]
        p = theo_phong.setdefault(r.department or "", {"so_ban": 0, "tong_diem": 0.0, "co_diem": 0})
        p["so_ban"] += 1
        if r.diem_tong is not None:
            p["tong_diem"] += float(r.diem_tong)
            p["co_diem"] += 1
        if not may or not nguoi:
            continue
        g = theo_nguoi.setdefault(r.nguoi_cham or "(chưa chấm)",
                                  {"so_ban": 0, "tong_lech": 0.0, "vai": r.vai_nguoi_cham})
        g["so_ban"] += 1
        g["tong_lech"] += sum(nguoi) / len(nguoi) - sum(may) / len(may)
    for g in theo_nguoi.values():
        g["lech_tb"] = round(g["tong_lech"] / g["so_ban"], 2) if g["so_ban"] else None
    for p in theo_phong.values():
        p["diem_tb"] = round(p["tong_diem"] / p["co_diem"], 2) if p["co_diem"] else None
    return {"ky_loai": ky_loai, "ky": ky, "so_ban": len(ds),
            "theo_nguoi_cham": theo_nguoi, "theo_phong": theo_phong}


def cua_toi(db: Session, boi: User, ky_loai: str = "", ky: str = "") -> list[dict]:
    """Bản của CHÍNH MÌNH — Chủ tịch chốt 08/10/2026 "nhân viên được thấy của mình".

    Chỉ trả bản ĐÃ CHẤM trở đi: bản nháp là bản trưởng phòng đang nghĩ dở, đọc nó rồi hỏi lại thì
    cuộc nói chuyện xảy ra trước khi người chấm kịp xong ý của mình.
    """
    nv = db.execute(select(Employee).where(Employee.user_id == boi.id)).scalars().first()
    if nv is None:
        return []
    q = select(DanhGiaNhanSu).where(DanhGiaNhanSu.employee_id == nv.id,
                                    DanhGiaNhanSu.trang_thai.in_(("da_cham", "da_gui")))
    if ky_loai:
        q = q.where(DanhGiaNhanSu.ky_loai == ky_loai)
    if ky:
        q = q.where(DanhGiaNhanSu.ky == ky)
    return [_tom_tat(db, r) for r in db.execute(q).scalars().all()]


def danh_sach(db: Session, ky_loai: str, ky: str, phong: str = "") -> list[dict]:
    ky = kiem_ky(ky_loai, ky)
    q = select(DanhGiaNhanSu).where(DanhGiaNhanSu.ky_loai == ky_loai, DanhGiaNhanSu.ky == ky)
    if phong:
        q = q.where(DanhGiaNhanSu.department == phong)
    return [_tom_tat(db, r) for r in db.execute(q).scalars().all()]


def meta() -> dict:
    """Danh mục cho màn hình — khai MỘT chỗ để màn hình và cửa máy chủ không lệch nhau."""
    return {"ky_loai": KY_LOAI, "thang_diem": THANG_DIEM, "o_may_dien": O_MAY_DIEN,
            "o_nguoi_cham": O_NGUOI_CHAM, "trang_thai": DG_TRANG_THAI,
            "diem_bat_buoc_ly_do": list(DIEM_BAT_BUOC_LY_DO),
            "xep_hang": [{"tu": n, "khoa": k, "ten": t} for n, k, t in XEP_HANG],
            "xep_hang_phai_ghi_viec": list(XEP_HANG_PHAI_GHI_VIEC)}
