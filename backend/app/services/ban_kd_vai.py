"""R5-7 · Ba bàn làm việc của phòng Kinh doanh lẻ: Trưởng phòng, Trưởng nhóm, Chuyên viên.

Chủ tịch duyệt bản xem trước 13/11/2026 («ba bàn riêng»; khối Đội ngũ cho TP và Trưởng nhóm; Chuyên
viên chỉ thấy số của mình; Trưởng nhóm giữ ô «Doanh thu của tôi»; «Đề xuất gửi BLĐ» tạm dùng Báo cáo
công việc; chỉ tiêu do Chủ tịch giao).

CHỈ ĐỌC, KHÔNG SỞ HỮU CON SỐ NÀO — mỗi ô đọc lại hàm của màn gốc:

    doanh thu tính chỉ tiêu, theo người / theo đơn vị   ← services.doanh_thu_kd (/fit, tab doanh thu)
    chỉ tiêu đã giao                                    ← services.chi_tieu_kd  (/fit, giao chỉ tiêu)
    phạm vi đơn vị, người trong đơn vị                  ← services.to_chuc_kd   (/to-chuc-kd)
    phải thu booking lẻ, chuyến cần thúc bán            ← services.ban_kd_le    (bàn GĐ)

PHẠM VI THEO VAI, CẮT Ở MÁY CHỦ (không ẩn ở trình duyệt):
    tp_kd, tn_kd  →  `to_chuc_kd.pham_vi_xem` (đơn vị được phân công và mọi đơn vị con)
    nv_kd         →  chỉ chính mình. Không bao giờ có dòng của người khác trong câu trả lời.

`None` KHÁC 0: chưa giao chỉ tiêu → `None` kèm lý do «chưa giao»; chưa phân công đơn vị → phạm vi rỗng
kèm cảnh báo, không lấy phạm vi của ai khác cho đủ bàn.
"""
from calendar import monthrange
from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cskh import CareTicket
from app.models.core import Booking, User
from app.models.crm import Lead
from app.models.to_chuc_kd import DonViKD
from app.services import ban_kd_le as GD
from app.services import chi_tieu_kd as CT
from app.services import doanh_thu_kd as DT
from app.services import to_chuc_kd as TC

VAI_BAN = {"tp_kd": "tp", "tn_kd": "tn", "nv_kd": "nv"}
LUONG = "le"


def _cuoi(ky: str) -> date:
    y, m = int(ky[:4]), int(ky[5:])
    return date(y, m, monthrange(y, m)[1])


def _chi_tieu_nguoi(bang: dict, uid: int):
    """Chỉ tiêu đã giao cho MỘT người: ưu tiên luồng «le», rồi «tat_ca». Không có → None (chưa giao)."""
    v = bang["nguoi"].get(f"{uid}|le")
    return v if v is not None else bang["nguoi"].get(f"{uid}|tat_ca")


def _chi_tieu_don_vi(bang: dict, dv_id: int | None):
    if dv_id is None:
        return None
    v = bang["don_vi"].get(f"{dv_id}|le")
    return v if v is not None else bang["don_vi"].get(f"{dv_id}|tat_ca")


def _o(so, ly_do: str = "", **k) -> dict:
    return {"so": so, "ly_do": "" if so is not None else (ly_do or "chưa đo"), **k}


def pham_vi(db: Session, u: User, ky: str) -> dict:
    """Ai nằm trong bàn này: danh sách đơn vị, danh sách người, đơn vị của chính người xem."""
    cuoi = _cuoi(ky)
    vai = VAI_BAN.get(u.role, "")
    dv = TC.don_vi_cua(db, u.id, cuoi, LUONG)
    if vai == "nv":
        return {"vai": vai, "don_vi_ids": None, "user_ids": [u.id], "don_vi": dv, "canh_bao": ""}
    pv = TC.pham_vi_xem(db, u, cuoi, LUONG)
    if pv is None:                                  # vai xem toàn cây (không xảy ra với tp/tn, giữ cho đủ)
        pv = [d.id for d in db.execute(select(DonViKD).where(DonViKD.mang == LUONG)).scalars()]
    ids = sorted({n["user_id"] for n in TC.nguoi_trong(db, pv, cuoi)} | {u.id}) if pv else [u.id]
    canh_bao = "" if pv else ("Bạn chưa được phân công vào đơn vị nào của Kinh doanh lẻ, nên bàn chỉ có số của "
                              "chính bạn. Hành chính – Nhân sự phân công ở màn Cơ cấu tổ chức Kinh doanh.")
    return {"vai": vai, "don_vi_ids": pv, "user_ids": ids, "don_vi": dv, "canh_bao": canh_bao}


def tong_quan(db: Session, u: User, hom_nay: date | None = None) -> dict:
    d = hom_nay or date.today()
    ky = f"{d:%Y-%m}"
    p = pham_vi(db, u, ky)
    vai, uids = p["vai"], p["user_ids"]
    bang_ct = CT.tra_cuu(db, ky)

    # ── Doanh thu tính chỉ tiêu ─────────────────────────────────────────────────────────────────
    cua_toi = DT.cua_nguoi(db, u.id, ky, LUONG)
    dt_toi = cua_toi["tien"]
    ct_toi = _chi_tieu_nguoi(bang_ct, u.id)
    doi_ngu, theo_nhom, dt_pv, ct_pv = [], [], None, None
    if vai in ("tp", "tn"):
        kq = DT.thang(db, ky, LUONG, p["don_vi_ids"] or [])
        dt_pv = kq["tong_tinh_chi_tieu"] if p["don_vi_ids"] else None
        ct_pv = _chi_tieu_don_vi(bang_ct, p["don_vi"].id if p["don_vi"] else None)
        ban = {o["user_id"]: o for o in kq["theo_nguoi"]}
        ten = {n["user_id"]: n for n in TC.nguoi_trong(db, p["don_vi_ids"], _cuoi(ky))} if p["don_vi_ids"] else {}
        for uid in uids:
            o = ban.get(uid, {})
            nguoi = ten.get(uid) or {}
            usr = db.get(User, uid)
            ct = _chi_tieu_nguoi(bang_ct, uid)
            tien = float(o.get("tien", 0.0))
            doi_ngu.append({"user_id": uid, "ho_ten": usr.full_name if usr else str(uid),
                            "don_vi": nguoi.get("don_vi") or o.get("don_vi", ""),
                            "vai": nguoi.get("vai", ""), "tien": tien, "so_booking": o.get("so_booking", 0),
                            "chi_tieu": ct, "ty_le": (tien / ct) if ct else None, "la_toi": uid == u.id})
        doi_ngu.sort(key=lambda x: -x["tien"])
        if vai == "tp" and p["don_vi"] is not None:
            con = [c for c in db.execute(select(DonViKD).where(DonViKD.cha_id == p["don_vi"].id)).scalars()
                   if c.dang_hieu_luc(d)]
            dvt = {x["don_vi_id"]: x for x in kq["theo_don_vi"]}
            for c in sorted(con, key=lambda x: x.ma):
                ct = _chi_tieu_don_vi(bang_ct, c.id)
                tien = float(dvt.get(c.id, {}).get("tien", 0.0))
                theo_nhom.append({"don_vi_id": c.id, "ten": c.ten, "ma": c.ma, "tien": tien,
                                  "so_nguoi": len(TC.nguoi_trong(db, [c.id], d)),
                                  "chi_tieu": ct, "ty_le": (tien / ct) if ct else None})

    # ── Booking, lead, chăm sóc của phạm vi ────────────────────────────────────────────────────
    dau_thang = datetime.combine(d.replace(day=1), time.min)
    bk_moi = int(db.execute(select(func.count()).select_from(Booking).where(
        Booking.sales_id.in_(uids), Booking.cancelled == False,  # noqa: E712
        Booking.created_at >= dau_thang)).scalar() or 0)
    bk_chua_coc = int(db.execute(select(func.count()).select_from(Booking).where(
        Booking.sales_id.in_(uids), Booking.cancelled == False,  # noqa: E712
        Booking.created_at >= dau_thang, (Booking.paid == None) | (Booking.paid <= 0))).scalar() or 0)  # noqa: E711
    lead_moi = int(db.execute(select(func.count()).select_from(Lead).where(
        Lead.sales_id.in_(uids), Lead.status == "moi")).scalar() or 0)
    lead_chua_nhan = int(db.execute(select(func.count()).select_from(Lead).where(
        Lead.sales_id.is_(None), Lead.status == "moi")).scalar() or 0) if vai == "tp" else None
    cs_qua_han = int(db.execute(select(func.count()).select_from(CareTicket).where(
        CareTicket.owner_id.in_(uids), CareTicket.status.in_(["moi", "hen_lai"]),
        CareTicket.han_lien_he < d)).scalar() or 0)
    cs_toi_han = int(db.execute(select(func.count()).select_from(CareTicket).where(
        CareTicket.owner_id.in_(uids), CareTicket.status.in_(["moi", "hen_lai"]),
        CareTicket.han_lien_he <= d)).scalar() or 0)
    pt = GD.phai_thu_le(db, d, sales_ids=uids)

    the = {
        "doanh_thu": _o(dt_pv if vai in ("tp", "tn") else dt_toi,
                        p["canh_bao"] or "chưa có doanh thu",
                        chi_tieu=ct_pv if vai in ("tp", "tn") else ct_toi),
        "doanh_thu_toi": _o(dt_toi, chi_tieu=ct_toi),
        "booking_moi": _o(bk_moi, chua_coc=bk_chua_coc),
        "lead_moi": _o(lead_moi),
        "lead_chua_nhan": _o(lead_chua_nhan, "chỉ Trưởng phòng phân lead", pham_vi="toan_cong_ty"),
        "cham_soc_qua_han": _o(cs_qua_han, toi_han=cs_toi_han),
        "phai_thu": _o(pt["tong"], pt["ly_do"], so_booking=pt["so_booking"]),
    }

    viec = []
    if lead_chua_nhan:
        viec.append({"ma": "lead_chua_nhan", "muc": "do", "toi": "/leads?tab=leads",
                     "tieu_de": f"{lead_chua_nhan} lead chưa ai nhận", "mo_ta": "Phân người chăm ngay"})
    if lead_moi:
        viec.append({"ma": "lead_moi", "muc": "cam", "toi": "/leads?tab=leads",
                     "tieu_de": f"{lead_moi} lead mới chưa liên hệ",
                     "mo_ta": "Của tôi" if vai == "nv" else "Của người trong phạm vi"})
    if cs_qua_han:
        viec.append({"ma": "cham_soc_qua_han", "muc": "do", "toi": "/cham-soc",
                     "tieu_de": f"{cs_qua_han} phiếu chăm sóc quá hạn", "mo_ta": "Ghi kết quả liên hệ"})
    if bk_chua_coc:
        viec.append({"ma": "chua_coc", "muc": "cam", "toi": "/bookings?mang=le",
                     "tieu_de": f"{bk_chua_coc} booking tháng này chưa cọc", "mo_ta": "Nhắc khách đặt cọc"})
    if pt["tong"]:
        viec.append({"ma": "phai_thu", "muc": "vang", "toi": "/bookings?mang=le",
                     "tieu_de": f"{pt['so_booking']} booking khách còn nợ", "mo_ta": "Nhắc thu trước ngày đi"})

    return {"ngay": d.isoformat(), "ky": ky, "vai": vai, "ho_ten": u.full_name,
            "don_vi": ({"id": p["don_vi"].id, "ten": p["don_vi"].ten} if p["don_vi"] else None),
            "so_nguoi": len(uids), "canh_bao": p["canh_bao"],
            "the": the, "doi_ngu": doi_ngu, "theo_nhom": theo_nhom, "viec": viec,
            "phai_thu": pt, "thuc_ban": GD.thuc_ban(db)}


def doanh_thu_12(db: Session, u: User, nam: int) -> dict:
    """12 tháng doanh thu – chỉ tiêu của phạm vi bàn: Chuyên viên = của mình; TP, Trưởng nhóm = đơn vị.

    Cùng cơ sở với ô doanh thu trên bàn (giá trị booking, kỳ theo ngày tour kết thúc) — khác cơ sở biểu
    đồ của bàn GĐ (quyết toán), nên hai biểu đồ không cộng lẫn với nhau."""
    nay = date.today()
    vai = VAI_BAN.get(u.role, "")
    thang = []
    for m in range(1, 13):
        ky = f"{nam}-{m:02d}"
        if date(nam, m, 1) > nay:
            thang.append({"ky": ky, "doanh_thu": None, "chi_tieu": None})
            continue
        bang = CT.tra_cuu(db, ky)
        if vai == "nv":
            dt = DT.cua_nguoi(db, u.id, ky, LUONG)["tien"]
            ct = _chi_tieu_nguoi(bang, u.id)
        else:
            p = pham_vi(db, u, ky)
            dt = DT.thang(db, ky, LUONG, p["don_vi_ids"])["tong_tinh_chi_tieu"] if p["don_vi_ids"] else None
            ct = _chi_tieu_don_vi(bang, p["don_vi"].id if p["don_vi"] else None)
        thang.append({"ky": ky, "doanh_thu": dt, "chi_tieu": ct})
    return {"nam": nam, "vai": vai, "thang": thang,
            "co_so": "Giá trị booking chưa huỷ, kỳ theo tháng ngày tour kết thúc (cùng cơ sở chỉ tiêu)."}
