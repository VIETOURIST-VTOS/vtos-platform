# -*- coding: utf-8 -*-
"""BÁO ĐỘNG KHỦNG HOẢNG — phút 0 báo Chủ tịch, phút 15 đánh thức thêm người (19/9/2026).

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ VÒNG NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

Bộ lọc `loc_khung_hoang` XẾP HÀNG tin đáng đọc trước cho người trực Marketing. Nó cố ý KHÔNG tự
quyết định cái gì là khủng hoảng — người đọc mới quyết.

Nhưng câu hỏi "ngoài giờ ai trực" có một câu trả lời làm hỏng thiết kế ấy: **Chủ tịch trực.** Nghĩa
là ban đêm KHÔNG CÓ người trực Marketing để đọc hàng đợi. Một hàng đợi không ai đọc lúc 2 giờ sáng
thì đúng bằng không có hàng đợi.

Nên có HAI MỨC, và Chủ tịch chốt 19/9/2026:

  · Trên ngưỡng thường  → vào hàng chờ người đọc. KHÔNG reo chuông. (giữ nguyên như cũ)
  · Trên ngưỡng ĐỎ, hoặc gặp DỐC → reo chuông NGAY, kể cả 2 giờ sáng.

Hai mức chứ không một, vì một mức thì phải chọn giữa hai cái hỏng: reo cho mọi tin thì sau vài đêm
người ta tắt chuông; chỉ reo khi có người tích tay thì ban đêm chuông không bao giờ reo.

──────────────────────────────────────────────────────────────────────────────────────────────
PHÚT 0 VÀ PHÚT 15 — VÀ VÌ SAO KHÔNG PHẢI LÀ CHIA QUYỀN
──────────────────────────────────────────────────────────────────────────────────────────────

Phút 0 báo Chủ tịch. Phút 15, nếu CHƯA AI BẤM "đã nhận", báo tiếp TGĐ và P.TGĐ Marketing.

Người thứ hai, thứ ba KHÔNG phải để chia quyền quyết — Chủ tịch vẫn là người quyết. Họ ở đó vì một
người trực mà không có ai đỡ phía sau là một chỗ hỏng chỉ cần một đêm ngủ say là lộ ra, và bảng
điều khiển khi ấy vẫn hiện "đã gửi cảnh báo thành công".

LEO THANG CHỈ MỘT LẦN cho mỗi cảnh báo. Không có người bấm nhận suốt đêm thì vẫn chỉ hai vòng —
một cửa báo động gửi lại mỗi phút là một cửa bị tắt vào sáng hôm sau.

──────────────────────────────────────────────────────────────────────────────────────────────
CHUÔNG KHÔNG PHẢI LÀ "TỚI ĐƯỢC NGƯỜI" — VÀ PHÉP ĐO PHẢI TÁCH HAI THỨ ẤY
──────────────────────────────────────────────────────────────────────────────────────────────

Chuông trong VTOS luôn "gửi thành công", vì gửi chuông chỉ là ghi một dòng vào sổ cảnh báo. Nhưng
2 giờ sáng không ai mở máy tính, nên chuông tới MÀN HÌNH chứ không tới NGƯỜI.

Nếu đếm chung, mọi vụ sẽ hiện 100% thành công trong khi thực tế không ai được đánh thức. Nên
`KENH_TOI_MAY` tách riêng ba kênh làm điện thoại kêu, và phép đo trả về `khong_kenh_nao_toi_may` —
con số ấy mới là con số phải nhìn.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bao_dong import VONG_DAU, CanhBaoGui
from app.models.core import Alert, User
from app.services import loc_khung_hoang as LK
from app.services import rules as R
from app.services import zalo as ZL
from app.services import zalo_nguoi_dung as ZN

KIND = "khung_hoang"

THAM_SO_NGUONG_DO = "pr_nguong_bao_dong"
THAM_SO_PHUT_LEO = "pr_phut_leo_thang"
THAM_SO_KENH = "pr_kenh_bao_dong"

VAI_VONG_0 = ("chutich",)
VAI_VONG_LEO = ("tgd", "ptgd_mkt")

# Ba kênh làm ĐIỆN THOẠI kêu. "chuong" cố ý KHÔNG có mặt ở đây — xem ghi chú đầu tệp.
KENH_TOI_MAY = ("zalo_oa", "zns", "email")
KENH_BIET = ("chuong",) + KENH_TOI_MAY


def nguong_do(db: Session) -> int:
    return int(R.get_param(db, THAM_SO_NGUONG_DO))


def phut_leo(db: Session) -> int:
    return int(R.get_param(db, THAM_SO_PHUT_LEO))


def kenh(db: Session) -> list[str]:
    """Kênh đang bật, theo tham số đã ký. Kênh lạ bị bỏ qua chứ không làm chết cửa quét."""
    tho = R.get_param_chu(db, THAM_SO_KENH)
    return [k for k in (x.strip() for x in tho.split(",")) if k in KENH_BIET]


# ---------------------------------------------------------------------------------------------
# Dòng nào đáng reo chuông
# ---------------------------------------------------------------------------------------------
def dang_do(dong: dict, nguong: int) -> bool:
    """Trên ngưỡng ĐỎ, hoặc là DỐC.

    DỐC reo chuông dù điểm chưa tới ngưỡng, và đó là chủ ý: mười người cùng viết một câu nhẹ dưới
    một bài trong một giờ là một làn sóng; mười câu ấy chấm riêng lẻ thì câu nào cũng hiền.
    """
    return int(dong.get("diem") or 0) >= nguong or any(
        str(l).startswith("Dốc") for l in (dong.get("ly_do") or []))


def khoa(dong: dict) -> str:
    """Khoá gom trùng: mỗi tin / bình luận chỉ sinh MỘT cảnh báo, quét lại bao nhiêu lần cũng thế."""
    return f"{KIND}:{dong.get('nguon')}:{dong.get('nguon_id')}"


def loi_nhan(dong: dict) -> str:
    """Nội dung gửi đi.

    KHÔNG có số điện thoại khách, KHÔNG có tên khách. Tin này đi ra ngoài VTOS — sang Zalo, sang
    hộp thư — nên nó chỉ mang đủ thứ để người nhận quyết định có mở máy hay không: nặng cỡ nào, ở
    đâu, và một đoạn trích. Ai cần biết khách là ai thì mở VTOS, nơi quyền đã đặt riêng cho việc ấy.
    """
    return (f"[VTOS] Cảnh báo khủng hoảng truyền thông — {dong.get('diem')} điểm.\n"
            f"Nguồn: {dong.get('kenh') or dong.get('nguon')}\n"
            f"Lúc: {dong.get('luc')}\n"
            f"Trích: {(dong.get('trich') or '')[:300]}\n"
            f"Mở VTOS → Marketing & PR → Khủng hoảng để xem và bấm ĐÃ NHẬN.")


# ---------------------------------------------------------------------------------------------
# Các kênh. Mỗi hàm trả (thành_công, lý_do, mã_ngoài) — KHÔNG ném ngoại lệ ra ngoài.
#
# Một kênh hỏng không được phép làm chết cả lượt gửi: ba người × bốn kênh, một lỗi mạng ở người
# thứ nhất mà dừng cả vòng thì hai người sau không nhận được gì và sổ không ghi được vì sao.
# ---------------------------------------------------------------------------------------------
def _kenh_chuong(db: Session, a: Alert, u: User, uid: str) -> tuple[bool, str, str]:
    """Chuông = chính dòng `alerts` đã ghi. Không có gì để gửi, nên luôn thành công.

    Đừng đọc con số này là "đã tới người": xem ghi chú đầu tệp và `KENH_TOI_MAY`.
    """
    return True, "", ""


def _kenh_zalo(db: Session, a: Alert, u: User, uid: str) -> tuple[bool, str, str]:
    if not uid:
        # KHÔNG bỏ qua im lặng. Đây là hàng quan trọng nhất của sổ: một người trong danh sách phải
        # báo mà chưa nối máy thì cửa báo động đang mù đúng một người.
        return False, "chua_noi_zalo", ""
    try:
        kq = ZL.send_oa_text(db, uid, loi_nhan_cua(a))
    except Exception as e:                                    # noqa: BLE001 - xem ghi chú trên
        return False, f"loi_gui_zalo: {str(e)[:120]}", ""
    if int(kq.get("error") or 0) != 0:
        return False, f"zalo_tu_choi: {str(kq.get('message') or kq)[:120]}", ""
    return True, "", str((kq.get("data") or {}).get("message_id") or "")


def _kenh_zns(db: Session, a: Alert, u: User, uid: str) -> tuple[bool, str, str]:
    """ZNS cần HAI thứ mà hệ CHƯA CÓ, và cả hai đều không phải việc của mã.

    1. Một mẫu tin được Zalo duyệt trước, khai trong ZALO_ZNS_TEMPLATES dưới mục đích
       `bao_dong_khung_hoang`.
    2. SỐ ĐIỆN THOẠI của từng người nhận — `users` không có cột nào giữ nó.

    Nên hôm nay kênh này luôn trả THẤT BẠI kèm lý do, và đó là trạng thái ĐÚNG: nó nói ra rằng
    kênh chưa dùng được, thay vì lặng lẽ không gửi rồi để bảng điều khiển hiện 100% thành công.
    """
    if not ZL.configured(db)["zns_templates"].get("bao_dong_khung_hoang"):
        return False, "chua_cau_hinh_mau_zns", ""
    return False, "chua_co_o_nhap_sdt", ""


def _kenh_email(db: Session, a: Alert, u: User, uid: str) -> tuple[bool, str, str]:
    """Email cần một ô nhập địa chỉ cho từng người — `users` không có cột email. Vòng sau dựng."""
    return False, "chua_co_o_nhap_email", ""


BO_KENH = {
    "chuong": _kenh_chuong,
    "zalo_oa": _kenh_zalo,
    "zns": _kenh_zns,
    "email": _kenh_email,
}


def loi_nhan_cua(a: Alert) -> str:
    return a.message or "[VTOS] Cảnh báo khủng hoảng truyền thông."


# ---------------------------------------------------------------------------------------------
# Gửi
# ---------------------------------------------------------------------------------------------
def _da_gui_vong(db: Session, alert_id: int, vong: int) -> bool:
    return db.execute(select(CanhBaoGui.id).where(CanhBaoGui.alert_id == alert_id,
                                                  CanhBaoGui.vong == vong)).scalars().first() is not None


def gui_vong(db: Session, a: Alert, vai: tuple, vong: int,
             bay_gio: datetime | None = None) -> list[CanhBaoGui]:
    """Gửi một cảnh báo cho MỌI người mang các vai ấy, trên MỌI kênh đang bật.

    `uid_theo_vai` trả CẢ người chưa nối Zalo, cố ý — nếu chỉ lấy người nối rồi thì sổ sẽ báo
    "2/2 thành công" và giấu mất người thứ ba.
    """
    gio = bay_gio or datetime.now()
    ds_kenh = kenh(db)
    ra: list[CanhBaoGui] = []
    for u, uid in ZN.uid_theo_vai(db, list(vai)):
        for k in ds_kenh:
            ok, ly_do, ma = BO_KENH[k](db, a, u, uid)
            g = CanhBaoGui(alert_id=a.id, user_id=u.id, kenh=k, vong=vong, gui_luc=gio,
                           thanh_cong=bool(ok), ly_do=ly_do, ma_ngoai=ma)
            db.add(g)
            ra.append(g)
    db.flush()
    return ra


def quet(db: Session, bay_gio: datetime | None = None) -> dict:
    """Đọc hàng đợi lọc, sinh cảnh báo cho dòng đạt ngưỡng ĐỎ, và gửi vòng 0."""
    gio = bay_gio or datetime.now()
    n = nguong_do(db)
    hang = LK.canh_bao(db, bay_gio=bay_gio)
    moi, da_co = 0, 0
    for d in hang["rows"]:
        # Dòng đã có người kết luận rồi thì thôi: người đã đọc thì không cần đánh thức ai.
        if d.get("ket_luan"):
            continue
        if not dang_do(d, n):
            continue
        kh = khoa(d)
        cu = db.execute(select(Alert).where(Alert.gom_khoa == kh)).scalars().first()
        if cu is not None:
            da_co += 1
            continue
        a = Alert(kind=KIND, level="red", ref=f"{d.get('nguon')}:{d.get('nguon_id')}",
                  message=loi_nhan(d), to_roles=",".join(VAI_VONG_0 + VAI_VONG_LEO),
                  gom_khoa=kh, created_at=gio, trang_thai="moi",
                  han_xu_ly=gio + timedelta(minutes=phut_leo(db)), nguon="phat_sinh")
        db.add(a)
        db.flush()
        gui_vong(db, a, VAI_VONG_0, VONG_DAU, gio)
        moi += 1
    return {"moi": moi, "da_co": da_co, "nguong_do": n, "kenh": kenh(db),
            "xem_hang": len(hang["rows"])}


def leo_thang(db: Session, bay_gio: datetime | None = None) -> dict:
    """Quá hạn mà chưa ai bấm nhận → đánh thức thêm TGĐ và P.TGĐ Marketing. ĐÚNG MỘT LẦN."""
    gio = bay_gio or datetime.now()
    moc = gio - timedelta(minutes=phut_leo(db))
    q = select(Alert).where(Alert.kind == KIND, Alert.nhan_luc.is_(None),
                            Alert.created_at <= moc).order_by(Alert.id)
    leo = 0
    for a in db.execute(q).scalars():
        if _da_gui_vong(db, a.id, phut_leo(db)):
            continue
        gui_vong(db, a, VAI_VONG_LEO, phut_leo(db), gio)
        leo += 1
    return {"leo_thang": leo, "phut": phut_leo(db)}


def nhan(db: Session, alert_id: int, u: User, bay_gio: datetime | None = None) -> dict:
    """Ai bấm 'đã nhận'. Bấm rồi thì đồng hồ leo thang dừng.

    Người bấm thứ hai KHÔNG ghi đè người thứ nhất: câu hỏi phép đo cần trả lời là "bao lâu thì có
    NGƯỜI ĐẦU TIÊN nhận", và ghi đè làm con số ấy biến mất.
    """
    a = db.get(Alert, int(alert_id))
    if a is None or a.kind != KIND:
        return {"ok": False, "ly_do": "khong_thay_canh_bao"}
    if a.nhan_luc is not None:
        return {"ok": False, "ly_do": "da_co_nguoi_nhan",
                "nguoi_nhan_id": a.nguoi_nhan_id,
                "nhan_luc": f"{a.nhan_luc:%Y-%m-%d %H:%M:%S}"}
    a.nguoi_nhan_id = u.id
    a.nhan_luc = bay_gio or datetime.now()
    a.trang_thai = "dang_xu_ly"
    db.flush()
    return {"ok": True, "nguoi_nhan_id": u.id, "nhan_luc": f"{a.nhan_luc:%Y-%m-%d %H:%M:%S}"}


# ---------------------------------------------------------------------------------------------
# PHÉP ĐO CHÍNH CỬA BÁO ĐỘNG
#
# Cửa nào cũng phải có phép đo chính nó, nếu không thì sau một tháng không ai trả lời được câu
# "nó có tác dụng không" và câu trả lời mặc định sẽ là niềm tin của người dựng ra nó.
# ---------------------------------------------------------------------------------------------
def do_bao_dong(db: Session, tu: datetime | None = None, den: datetime | None = None) -> dict:
    q = select(Alert).where(Alert.kind == KIND)
    if tu is not None:
        q = q.where(Alert.created_at >= tu)
    if den is not None:
        q = q.where(Alert.created_at <= den)
    ds = list(db.execute(q.order_by(Alert.id)).scalars())
    ids = [a.id for a in ds]

    gui = []
    if ids:
        gui = list(db.execute(select(CanhBaoGui).where(CanhBaoGui.alert_id.in_(ids))).scalars())

    toi_may = {g.alert_id for g in gui if g.thanh_cong and g.kenh in KENH_TOI_MAY}
    cho_phut = [round((a.nhan_luc - a.created_at).total_seconds() / 60.0, 1)
                for a in ds if a.nhan_luc and a.created_at]

    theo_kenh: dict[str, dict] = {}
    for g in gui:
        o = theo_kenh.setdefault(g.kenh, {"gui": 0, "thanh_cong": 0, "ly_do": {}})
        o["gui"] += 1
        if g.thanh_cong:
            o["thanh_cong"] += 1
        elif g.ly_do:
            o["ly_do"][g.ly_do] = o["ly_do"].get(g.ly_do, 0) + 1

    # Người NẰM TRONG danh sách phải báo mà không kênh nào tới máy được. Đây là chỗ mù của cửa
    # báo động, và nó phải có TÊN chứ không phải một con số — biết "còn một người" mà không biết
    # ai thì không sửa được.
    mu = []
    for u, uid in ZN.uid_theo_vai(db, list(VAI_VONG_0 + VAI_VONG_LEO)):
        co = [g for g in gui if g.user_id == u.id and g.thanh_cong and g.kenh in KENH_TOI_MAY]
        if not co:
            mu.append({"user_id": u.id, "username": u.username, "vai": u.role,
                       "da_noi_zalo": bool(uid)})

    return {
        "tong_vu": len(ds),
        # Hai con số Chủ tịch hỏi ngày 19/9/2026.
        "khong_ai_bam_nhan": sum(1 for a in ds if a.nhan_luc is None),
        "phut_trung_binh_toi_luc_nhan": (round(sum(cho_phut) / len(cho_phut), 1) if cho_phut else None),
        # Con số thứ ba, em thêm: gửi thành công tới một màn hình không ai mở vẫn là gửi thành công.
        "khong_kenh_nao_toi_may": sum(1 for a in ds if a.id not in toi_may),
        "da_leo_thang": sum(1 for a in ds if any(g.alert_id == a.id and g.vong > VONG_DAU for g in gui)),
        "theo_kenh": theo_kenh,
        "nguoi_chua_toi_duoc": mu,
        "kenh_dang_bat": kenh(db),
        "phut_leo_thang": phut_leo(db),
        "nguong_do": nguong_do(db),
    }
