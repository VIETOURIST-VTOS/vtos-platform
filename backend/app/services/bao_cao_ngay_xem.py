"""BC-2 — Tổng hợp báo cáo ngày cho NGƯỜI XEM XÉT (Chủ tịch duyệt bản xem thử 26/10/2026).

Ba câu hỏi một trưởng phòng mở màn này để trả lời, theo đúng thứ tự trên màn hình:
  · còn bao nhiêu báo cáo tôi chưa xem, bao nhiêu đang chờ nhân viên bổ sung, ai quá hạn chưa nộp;
  · hôm ấy phòng tôi nộp thế nào (đúng hạn / muộn / chưa đến hạn / quá hạn / không có nghĩa vụ);
  · việc nào phòng khác đang chờ phòng tôi xử lý.

PHẠM VI — đọc thẳng bảng `bao_cao_phong.PHONG` (ai chịu trách nhiệm con số của phòng nào), không
khai lại. Chủ tịch, TGĐ, Ban Kiểm soát thấy cả công ty. HCNS thấy TRẠNG THÁI nghĩa vụ cả công ty
(để đối chiếu công, phép) nhưng chỉ đọc NỘI DUNG của phòng mình — máy chủ không trả nội dung, chứ
không phải trả rồi giấu ở giao diện. Phòng không có dòng trong bảng ấy (CNTT, CSKH, IR–Pháp chế)
chỉ Chủ tịch/TGĐ xem: thêm người xem là thêm một dòng ở `bao_cao_phong`, có người quyết.

BA BẤT BIẾN
  · Không ai xem xét báo cáo của chính mình — chuyển lên cấp trên (R06).
  · Trả bổ sung phải có lý do; nộp lại vẫn giữ giờ nộp lần đầu (R04).
  · «Đã xem» không chốt ngày công, và người xem không sửa nội dung của nhân viên.
"""
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import Employee, DEPARTMENTS
from app.models.ops import DailyReport, DailyReportReview, DailyReportFollowUp, DailyReportVersion
from app.services import ops as O
from app.services import rules as R
from app.services import bao_cao_phong as BP

XEM = ("cho_xem", "da_xem", "can_bo_sung")
TEN_XEM = {"cho_xem": "Chờ xem", "da_xem": "Đã xem", "can_bo_sung": "Cần bổ sung"}
TRANG_THAI_VIEC = {"mo": "Mở", "dang_xu_ly": "Đang xử lý", "da_xong": "Đã xong", "rut": "Đã rút"}
VIEC_DONG = ("da_xong", "rut")
# Ai được ghi «đã xem / trả bổ sung / giao hỗ trợ»: những vai đang xem báo cáo cũ (MANAGERS ở
# api/v1/ops) cộng người xem của từng phòng trong `bao_cao_phong` (TP Hướng dẫn, GĐ đội xe, Kế
# toán). Đây chỉ là cửa ngoài; phạm vi thật xét ở `co_quyen_noi_dung` theo phòng của báo cáo.
VAI_CO_PHONG = tuple(sorted({v for cfg in BP.PHONG.values() for v in cfg["xem"]}))


# ---------------------------------------------------------------- phạm vi

def ten_phong(ma: str) -> str:
    return (BP.PHONG.get(ma) or {}).get("ten") or DEPARTMENTS.get(ma) or O.DEPT_FORMS.get(ma, {}).get("ten") or ma


def phong_cua_user(db: Session, user_id: int) -> str:
    e = db.execute(select(Employee).where(Employee.user_id == user_id)).scalars().first()
    if e and e.department:
        return e.department
    u = db.get(User, user_id)
    return O.dept_of_user(db, u) if u else ""


def pham_vi_noi_dung(db: Session, u: User) -> set[str] | None:
    """Các phòng mà người này đọc được NỘI DUNG báo cáo và xem xét được. None = cả công ty."""
    pv = BP.pham_vi_cho_nguoi(db, u)
    if BP.TOAN_CTY in pv:
        return None
    return set(pv)


def pham_vi_trang_thai(db: Session, u: User) -> set[str] | None:
    """Các phòng mà người này thấy TRẠNG THÁI nộp. HCNS: cả công ty (đối chiếu công, phép)."""
    from app.services.vai_ke_thua import vai_va_cha
    if "hcns" in vai_va_cha(u.role):
        return None
    return pham_vi_noi_dung(db, u)


def trong(pv: set[str] | None, phong: str) -> bool:
    return pv is None or phong in pv


def co_quyen_noi_dung(db: Session, u: User, r: DailyReport) -> bool:
    return r.user_id == u.id or trong(pham_vi_noi_dung(db, u), phong_cua_user(db, r.user_id))


def trang_thai_xem(r: DailyReport | None) -> str:
    if r is None:
        return ""
    if r.reviewed_by:
        return "da_xem"
    return "can_bo_sung" if r.xem_trang_thai == "can_bo_sung" else "cho_xem"


# ---------------------------------------------------------------- xem xét

def xem_xet(db: Session, u: User, r: DailyReport, hanh_dong: str, diem: float | None = None,
            ly_do: str = "", lan: int | None = None) -> DailyReport:
    """«Đã xem» (điểm không bắt buộc) hoặc «Yêu cầu bổ sung» (lý do bắt buộc).

    PermissionError → 403, LookupError → 409 (báo cáo vừa nộp lại), ValueError → 422."""
    if r.user_id == u.id:
        raise PermissionError("Không xem xét báo cáo của chính mình — báo cáo này chuyển lên cấp trên")
    if not co_quyen_noi_dung(db, u, r):
        raise PermissionError("Báo cáo này không thuộc phòng bạn được xem")
    if lan is not None and lan != (r.so_lan_nop or 1):
        raise LookupError("Nhân viên vừa nộp lại báo cáo này — mở lại để xem bản mới rồi hãy xem xét")
    hien = trang_thai_xem(r)
    ly_do = (ly_do or "").strip()[:300]
    if hanh_dong == "da_xem":
        if hien == "da_xem":
            raise ValueError("Báo cáo này đã được xem")
        if diem is not None and not 0 <= diem <= 10:
            raise ValueError("Điểm 0–10")
        r.reviewed_by, r.reviewed_at = u.username, datetime.now()
        r.manager_score = diem
        r.manager_note = ly_do
        r.xem_trang_thai = "da_xem"
        r.bo_sung_ly_do = ""
    elif hanh_dong == "bo_sung":
        if hien == "da_xem":
            raise ValueError("Báo cáo đã xem thì đã khoá — không trả bổ sung được nữa")
        if not ly_do:
            raise ValueError("Trả bổ sung phải ghi lý do để nhân viên biết cần bổ sung gì")
        r.xem_trang_thai = "can_bo_sung"
        r.bo_sung_ly_do = ly_do
    else:
        raise ValueError("Thao tác không hợp lệ")
    db.add(DailyReportReview(report_id=r.id, hanh_dong=hanh_dong, ly_do=ly_do, diem=diem,
                             lan_nop=r.so_lan_nop or 1, boi=u.username, luc=datetime.now()))
    R.audit(db, u.username, u.role, "xem_xet_bao_cao_ngay", f"report:{r.user_id}:{r.report_date}",
            after={"hanh_dong": hanh_dong, "diem": diem, "ly_do": ly_do, "lan_nop": r.so_lan_nop})
    db.commit(); db.refresh(r)
    return r


def sau_khi_nop(db: Session, u: User, r: DailyReport, phong: str) -> None:
    """Gọi từ `ops.submit_report` trước khi commit: nộp lại sau «cần bổ sung» đưa báo cáo về chờ
    xem; vướng mắc Phần 4 có phòng nhận thì sinh (hoặc cập nhật) MỘT việc theo dõi."""
    if r.xem_trang_thai == "can_bo_sung":
        r.xem_trang_thai = ""
    f = db.execute(select(DailyReportFollowUp).where(
        DailyReportFollowUp.report_id == r.id, DailyReportFollowUp.loai == "vuong_mac")).scalars().first()
    noi_dung = (r.part3_issues or "").strip()
    co = bool(r.vuong_mac_cho and noi_dung)
    if f is None:
        if co:
            db.add(DailyReportFollowUp(report_id=r.id, loai="vuong_mac", tu_phong=phong, den_phong=r.vuong_mac_cho,
                                       noi_dung=noi_dung, han=r.vuong_mac_han, tao_boi=u.username, tao_luc=datetime.now()))
        return
    if f.trang_thai in VIEC_DONG and f.trang_thai != "rut":
        return                     # bên nhận đã xong: lần nộp lại không mở lại việc của họ
    if co:
        f.den_phong, f.noi_dung, f.han = r.vuong_mac_cho, noi_dung, r.vuong_mac_han
        if f.trang_thai == "rut":
            f.trang_thai = "mo"
    elif f.trang_thai == "mo":
        f.trang_thai = "rut"
    f.cap_nhat_boi, f.cap_nhat_luc = u.username, datetime.now()


def giao_ho_tro(db: Session, u: User, r: DailyReport, nguoi_user_id: int, noi_dung: str,
                han: date | None) -> DailyReportFollowUp:
    if not co_quyen_noi_dung(db, u, r) or r.user_id == u.id:
        raise PermissionError("Chỉ người xem xét báo cáo này mới giao hỗ trợ được")
    noi_dung = (noi_dung or "").strip()
    if not noi_dung:
        raise ValueError("Ghi rõ việc cần hỗ trợ")
    e = db.execute(select(Employee).where(Employee.user_id == nguoi_user_id, Employee.active == True)).scalars().first()  # noqa: E712
    if e is None or not trong(pham_vi_noi_dung(db, u), e.department):
        raise ValueError("Chỉ giao được cho người đang làm trong phòng bạn phụ trách")
    if han and han < O.gio_vn().date():
        raise ValueError("Hạn không được ở quá khứ")
    f = DailyReportFollowUp(report_id=r.id, loai="ho_tro", tu_phong=phong_cua_user(db, r.user_id), den_phong=e.department,
                            nguoi_nhan_id=nguoi_user_id, noi_dung=noi_dung[:2000], han=han,
                            tao_boi=u.username, tao_luc=datetime.now())
    db.add(f)
    R.audit(db, u.username, u.role, "giao_ho_tro_bao_cao_ngay", f"report:{r.user_id}:{r.report_date}",
            after={"nguoi_nhan": e.full_name, "han": han.isoformat() if han else None})
    db.commit(); db.refresh(f)
    return f


def cap_nhat_viec(db: Session, u: User, f: DailyReportFollowUp, trang_thai: str, ghi_chu: str = "") -> DailyReportFollowUp:
    la_nguoi_nhan = f.nguoi_nhan_id == u.id
    if not (la_nguoi_nhan or trong(pham_vi_noi_dung(db, u), f.den_phong)):
        raise PermissionError("Việc này không chuyển đến bạn hay phòng bạn phụ trách")
    if trang_thai not in ("dang_xu_ly", "da_xong"):
        raise ValueError("Trạng thái không hợp lệ")
    if f.trang_thai in VIEC_DONG:
        raise ValueError(f"Việc đã {TRANG_THAI_VIEC[f.trang_thai].lower()} — không đổi được nữa")
    if trang_thai == "dang_xu_ly" and f.trang_thai == "dang_xu_ly":
        raise ValueError("Việc đang xử lý rồi")
    truoc = f.trang_thai
    f.trang_thai, f.ghi_chu = trang_thai, (ghi_chu or "").strip()[:300] or f.ghi_chu
    f.cap_nhat_boi, f.cap_nhat_luc = u.username, datetime.now()
    R.audit(db, u.username, u.role, "cap_nhat_viec_bao_cao_ngay", f"follow_up:{f.id}",
            before={"trang_thai": truoc}, after={"trang_thai": trang_thai})
    db.commit(); db.refresh(f)
    return f


def viec_out(db: Session, f: DailyReportFollowUp, users: dict, hom_nay: date) -> dict:
    r = db.get(DailyReport, f.report_id)
    nguoi_nop = users.get(r.user_id) if r else None
    nhan = users.get(f.nguoi_nhan_id) if f.nguoi_nhan_id else None
    con = (f.han - hom_nay).days if f.han else None
    return {"id": f.id, "loai": f.loai, "tu_phong": f.tu_phong, "tu_phong_ten": ten_phong(f.tu_phong),
            "den_phong": f.den_phong, "den_phong_ten": ten_phong(f.den_phong),
            "nguoi_nhan": nhan.full_name if nhan else "", "nguoi_nop": nguoi_nop.full_name if nguoi_nop else "",
            "ngay_bao_cao": r.report_date.isoformat() if r else None, "noi_dung": f.noi_dung,
            "han": f.han.isoformat() if f.han else None, "con_ngay": con,
            "qua_han": con is not None and con < 0 and f.trang_thai not in VIEC_DONG,
            "trang_thai": f.trang_thai, "trang_thai_ten": TRANG_THAI_VIEC.get(f.trang_thai, f.trang_thai),
            "ghi_chu": f.ghi_chu, "tao_boi": f.tao_boi, "cap_nhat_boi": f.cap_nhat_boi}


def viec_cua(db: Session, u: User, ngay: int = 30) -> dict:
    """Việc chuyển đến phòng mình (vướng mắc + hỗ trợ trong phạm vi) và việc giao cho chính mình.
    Việc còn mở hiện hết; việc đã xong/đã rút chỉ hiện trong `ngay` ngày gần nhất."""
    hom_nay = O.gio_vn().date()
    tu = datetime.now() - timedelta(days=ngay)
    pv = pham_vi_noi_dung(db, u)
    users = {x.id: x for x in db.execute(select(User)).scalars()}
    den, cua_toi = [], []
    for f in db.execute(select(DailyReportFollowUp).order_by(DailyReportFollowUp.id.desc())).scalars():
        if f.trang_thai in VIEC_DONG and (f.cap_nhat_luc or f.tao_luc or tu) < tu:
            continue
        if f.trang_thai == "rut":
            continue
        if f.nguoi_nhan_id == u.id:
            cua_toi.append(viec_out(db, f, users, hom_nay))
        elif pv is not None and not pv:
            continue
        elif trong(pv, f.den_phong):
            den.append(viec_out(db, f, users, hom_nay))
    khoa = lambda x: (x["trang_thai"] in VIEC_DONG, x["han"] or "9999")   # noqa: E731
    return {"den_phong": sorted(den, key=khoa), "cua_toi": sorted(cua_toi, key=khoa)}


# ---------------------------------------------------------------- tổng hợp

def _noi_dung(db: Session, r: DailyReport) -> dict:
    from app.models.attachments import Attachment
    tep = 0
    try:
        tep = len(list(db.execute(select(Attachment.id).where(
            Attachment.doi_tuong == "bao_cao_ngay", Attachment.doi_tuong_id == str(r.id))).scalars()))
    except Exception:          # bảng tệp đổi tên cột thì vẫn mở được năm phần
        tep = 0
    lich_su = [{"hanh_dong": x.hanh_dong, "ly_do": x.ly_do, "diem": x.diem, "lan_nop": x.lan_nop, "boi": x.boi,
                "luc": x.luc.isoformat() if x.luc else None}
               for x in db.execute(select(DailyReportReview).where(DailyReportReview.report_id == r.id)
                                   .order_by(DailyReportReview.id)).scalars()]
    return {"p1": r.part1_done, "p2": O.parse_part2(r.part2_numbers), "p3": r.part4_plan, "p4": r.part3_issues,
            "vuong_mac_cho": r.vuong_mac_cho, "vuong_mac_cho_ten": ten_phong(r.vuong_mac_cho) if r.vuong_mac_cho else "",
            "vuong_mac_han": r.vuong_mac_han.isoformat() if r.vuong_mac_han else None,
            "so_tep": tep, "lich_su_xem": lich_su,
            "so_phien_ban": len(list(db.execute(select(DailyReportVersion.id).where(
                DailyReportVersion.report_id == r.id)).scalars()))}


def tong_hop(db: Session, u: User, d: date, phong: str = "", now: datetime | None = None) -> dict:
    now = now or O.gio_vn()
    pv_tt, pv_nd = pham_vi_trang_thai(db, u), pham_vi_noi_dung(db, u)
    if pv_tt is not None and not pv_tt:
        raise PermissionError("Bạn chưa được giao xem báo cáo ngày của phòng nào")
    emps = [e for e in O.nhan_vien_phai_nop(db) if trong(pv_tt, e.department)]
    cac_phong = sorted({e.department for e in emps}, key=lambda m: ten_phong(m))
    if phong:
        emps = [e for e in emps if e.department == phong]
    bc = {r.user_id: r for r in db.execute(select(DailyReport).where(DailyReport.report_date == d)).scalars()}
    dong, dem = [], {"dung_han": 0, "muon": 0, "chua_den_han": 0, "qua_han": 0, "khong_nghia_vu": 0}
    xl = {"cho_xem": 0, "can_bo_sung": 0, "qua_han": 0}
    for e in emps:
        tt = O.trang_thai_ngay(db, e, e.user_id, d, now)
        dem[tt["ma"]] = dem.get(tt["ma"], 0) + 1
        r = bc.get(e.user_id)
        doc = r is not None and (r.user_id == u.id or trong(pv_nd, e.department))
        xem = trang_thai_xem(r)
        tu_minh = e.user_id == u.id
        if tt["ma"] == "qua_han":
            xl["qua_han"] += 1
        if r is not None and doc and not tu_minh and xem in xl:
            xl[xem] += 1
        dong.append({
            "user_id": e.user_id, "code": e.code, "ten": e.full_name, "phong": e.department, "phong_ten": ten_phong(e.department),
            "thoi_han": tt["ma"], "thoi_han_ten": tt["ten"],
            "report_id": r.id if r else None,
            "lan_dau": (r.first_submitted_at or r.submitted_at).isoformat() if r else None,
            "so_lan": (r.so_lan_nop or 1) if r else 0,
            "xem": xem, "xem_ten": TEN_XEM.get(xem, ""), "bo_sung_ly_do": r.bo_sung_ly_do if r else "",
            "diem_robot": r.robot_score if r else None, "ghi_chu_robot": r.robot_note if r else "",
            "diem_tp": r.manager_score if r else None, "nguoi_xem": r.reviewed_by if r else "",
            "doc_duoc": doc, "xem_xet_duoc": bool(r is not None and doc and not tu_minh and xem != "da_xem"),
            "tu_minh": tu_minh,
            "noi_dung": _noi_dung(db, r) if doc else None,
        })
    thu_tu = {"qua_han": 0, "muon": 1, "chua_den_han": 2, "dung_han": 3, "khong_nghia_vu": 4}
    xem_tt = {"cho_xem": 0, "can_bo_sung": 1, "da_xem": 2, "": 3}
    dong.sort(key=lambda x: (xem_tt.get(x["xem"], 3) if x["report_id"] else -1 if x["thoi_han"] == "qua_han" else 4,
                             thu_tu.get(x["thoi_han"], 9), x["phong_ten"], x["ten"]))
    phai = len(emps) - dem["khong_nghia_vu"]
    da_nop = dem["dung_han"] + dem["muon"]
    nguoi_giao = [{"user_id": e.user_id, "ten": e.full_name, "phong_ten": ten_phong(e.department)}
                  for e in O.nhan_vien_phai_nop(db) if trong(pv_nd, e.department) and e.user_id != u.id] \
        if pv_nd is None or pv_nd else []
    return {
        "ngay": d.isoformat(), "as_of": now.isoformat(timespec="minutes"), "mui_gio": "Asia/Ho_Chi_Minh",
        "han": O.han_chu(db, d),
        "pham_vi": "toan_cty" if pv_tt is None else "phong",
        "chi_trang_thai": pv_nd is not None and pv_tt is None,
        "cac_phong": [{"ma": m, "ten": ten_phong(m), "doc_noi_dung": trong(pv_nd, m)} for m in cac_phong],
        "phong": phong, "xu_ly": xl, "dem": dem, "phai_nop": phai, "da_nop": da_nop,
        "ty_le": round(da_nop * 100 / phai) if phai else None,
        "dong": dong, "nguoi_giao_duoc": sorted(nguoi_giao, key=lambda x: (x["phong_ten"], x["ten"])),
    }
