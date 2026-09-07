"""Quyền AI theo vị trí – đọc mức, kiểm hạn mức, tắt khẩn (đặc tả 07/9/2026, phần C).

Điểm quan trọng nhất của tệp này không phải là bảng, mà là việc bảng ĐƯỢC ĐỌC: hàm duoc_tu_gui() được
robot hộp thư gọi trước mỗi lần định gửi tin cho khách. Một bảng phân quyền mà hệ thống không đọc thì
đến lúc có chuyện, nó chỉ chứng minh rằng người ta đã tưởng là mình kiểm soát được.
"""
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import AiPosition, AiPause, AiRun, AI_GROUPS, AI_LEVELS, AI_HAN_MUC_BAT_BUOC, ROLES

# Mức mặc định theo Phụ lục A của đặc tả, anh Tuấn duyệt 07/9/2026.
# Thứ tự cột: hỏi–đáp · tin cho khách · văn bản nội bộ · đọc chứng từ · chấm điểm người · cảnh báo
MAC_DINH: dict[str, tuple] = {
    "chutich":    (2, 0, 2, 1, 1, 4), "tgd":        (2, 0, 2, 1, 1, 4),
    "ptgd_doan":  (2, 2, 2, 1, 1, 4), "ptgd_mkt":   (2, 3, 2, 1, 1, 4),
    "tp_dh":      (2, 2, 2, 2, 1, 4), "nv_dh":      (1, 2, 2, 2, 0, 4),
    "gd_kd":      (2, 2, 2, 1, 1, 4), "tp_kd":      (2, 2, 2, 1, 1, 4),
    "tn_kd":      (1, 2, 1, 0, 0, 4), "nv_kd":      (1, 2, 1, 0, 0, 4),
    "nv_mkt":     (1, 3, 2, 0, 0, 4), "ketoan":     (2, 0, 2, 2, 0, 4),
    "hcns":       (1, 0, 2, 1, 1, 4), "hanh_chinh": (1, 0, 2, 1, 0, 4),
    "cntt":       (2, 0, 2, 1, 0, 4),
    # Vị trí Kiểm soát do AI giữ (chỉ đạo 07/9/2026): kiểm tra, thử, giám sát, báo cáo mọi phòng ban
    # về Chủ tịch. Ba ô mức 3 – hỏi đáp trên dữ liệu, soạn báo cáo nội bộ, chấm điểm phòng ban – và
    # mức 3 nghĩa là TỰ ĐỘNG TRONG HẠN MỨC, người hậu kiểm là Chủ tịch. Ô tin_khach để 0 và phải ở 0:
    # người đi giám sát không nói chuyện với khách hàng. Ô cảnh báo là mức 4 vì đó là quy tắc xác định.
    "bks":        (3, 0, 3, 2, 3, 4),
    "xe_hdv":     (1, 0, 0, 1, 0, 4), "gd_doi_xe":  (1, 0, 1, 1, 0, 4),
    "nv_visa":    (1, 2, 1, 2, 0, 4),
}
COT = ("hoi_dap", "tin_khach", "vb_noi_bo", "doc_chung_tu", "cham_diem", "canh_bao")

# Hạn mức mặc định cho hai ô mức 3 duy nhất trong bảng (Marketing gửi tin cho khách).
HAN_MUC_MAC_DINH = {
    "khung_gio": "08:00-21:00",
    "so_luot_ngay": 30,
    "loai_noi_dung": "lịch khởi hành, giá công bố, chính sách cọc và hủy, xin tên và số điện thoại",
    "nguoi_hau_kiem": "ptgd_mkt",
}

# Vai trò được coi là CHỦ QUẢN hộp thư đa kênh. AI tự trả lời khách là năng lực của KÊNH, không phải của
# từng tư vấn viên – nếu tính theo vai trò người phụ trách hội thoại thì cùng một hộp thư sẽ lúc tự gửi
# lúc không, tùy hội thoại đó đã gán cho ai.
CHU_QUAN_HOP_THU = "ptgd_mkt"

# Hạn mức riêng cho vị trí Kiểm soát. Khác Marketing ở hai chỗ: không giới hạn khung giờ hẹp (sự cố
# không chờ giờ hành chính) và người hậu kiểm là Chủ tịch, đúng đường báo cáo anh Tuấn giao.
HAN_MUC_KIEM_SOAT = {
    "khung_gio": "00:00-23:59",
    "so_luot_ngay": 24,
    "loai_noi_dung": "kết quả quét, kết quả kiểm thử vai trò, nhận xét và chấm điểm phòng ban, báo cáo "
                     "gửi Chủ tịch. KHÔNG nội dung gửi khách hàng, KHÔNG kết luận kỷ luật",
    "nguoi_hau_kiem": "chutich",
}


def nap_mac_dinh(db: Session) -> int:
    """Nạp bảng mặc định cho vai trò/tác vụ chưa có dòng. Không đụng tới dòng lãnh đạo đã sửa."""
    co = {(p.vai_tro, p.tac_vu) for p in db.execute(select(AiPosition)).scalars()}
    them = 0
    for vai, mucs in MAC_DINH.items():
        for tac_vu, muc in zip(COT, mucs):
            if (vai, tac_vu) in co: continue
            mac = HAN_MUC_KIEM_SOAT if vai == "bks" else HAN_MUC_MAC_DINH
            db.add(AiPosition(vai_tro=vai, tac_vu=tac_vu, muc=muc,
                              han_muc=dict(mac) if muc == 3 else {}))
            them += 1
    if them: db.flush()
    return them


def dang_tam_dung(db: Session) -> AiPause | None:
    p = db.get(AiPause, 1)
    return p if (p and p.tam_dung) else None


def muc_cua(db: Session, vai_tro: str, tac_vu: str) -> int:
    """Mức ĐANG ÁP DỤNG. Tắt khẩn hạ mọi mức 3 xuống 2 – tức AI vẫn soạn nháp, chỉ không tự gửi nữa."""
    p = db.execute(select(AiPosition).where(AiPosition.vai_tro == vai_tro,
                                            AiPosition.tac_vu == tac_vu)).scalars().first()
    muc = p.muc if p else 0
    if muc == 3 and dang_tam_dung(db): return 2
    return muc


def thieu_han_muc(muc: int, han_muc: dict | None) -> list[str]:
    """Mức 3 phải khai đủ hạn mức. Trả về danh sách phần còn thiếu – rỗng nghĩa là đủ."""
    if muc != 3: return []
    hm = han_muc or {}
    return [k for k in AI_HAN_MUC_BAT_BUOC if not str(hm.get(k) or "").strip()]


def _trong_khung_gio(khung: str, luc: datetime) -> bool:
    """'08:00-21:00'. Khung sai định dạng thì coi là NGOÀI giờ – hỏng thì đóng, không mở."""
    try:
        a, b = khung.split("-")
        ha, ma = (int(x) for x in a.strip().split(":"))
        hb, mb = (int(x) for x in b.strip().split(":"))
    except Exception:
        return False
    phut = luc.hour * 60 + luc.minute
    return ha * 60 + ma <= phut <= hb * 60 + mb


def so_luot_hom_nay(db: Session, tac_vu: str, ngay: date | None = None) -> int:
    ngay = ngay or date.today()
    return int(db.execute(select(func.count(AiRun.id)).where(
        AiRun.tac_vu == tac_vu, AiRun.muc == 3,
        AiRun.ts >= datetime.combine(ngay, datetime.min.time()))).scalar() or 0)


def duoc_tu_gui(db: Session, luc: datetime | None = None) -> tuple[bool, str]:
    """AI có được tự gửi tin cho khách lúc này không, và nếu không thì VÌ SAO.

    Trả cả lý do để nhật ký và màn hình nói được điều đã xảy ra. "Hôm nay AI không trả lời ai cả" mà
    không kèm lý do là thứ khiến người ta đi tắt tính năng thay vì sửa hạn mức.
    """
    luc = luc or datetime.now()
    p = db.execute(select(AiPosition).where(AiPosition.vai_tro == CHU_QUAN_HOP_THU,
                                            AiPosition.tac_vu == "tin_khach")).scalars().first()
    if p is None:
        return False, "chưa cấu hình quyền AI cho hộp thư"
    tam = dang_tam_dung(db)
    if tam:
        return False, f"AI đối ngoại đang tạm dừng ({tam.ly_do or 'không ghi lý do'})"
    if p.muc < 3:
        return False, f"mức đang áp dụng là {p.muc} – {AI_LEVELS.get(p.muc, '')}, chỉ soạn nháp"
    thieu = thieu_han_muc(p.muc, p.han_muc)
    if thieu:
        return False, "mức 3 nhưng thiếu hạn mức: " + ", ".join(thieu)
    hm = p.han_muc or {}
    if not _trong_khung_gio(str(hm.get("khung_gio") or ""), luc):
        return False, f"ngoài khung giờ cho phép ({hm.get('khung_gio')})"
    gioi_han = int(hm.get("so_luot_ngay") or 0)
    da_gui = so_luot_hom_nay(db, "tin_khach", luc.date())
    if gioi_han and da_gui >= gioi_han:
        return False, f"đã dùng hết {gioi_han} lượt trong ngày"
    return True, ""


def bang(db: Session) -> dict:
    """Bảng đầy đủ cho màn hình: 19 vị trí × 6 nhóm việc."""
    co = {(p.vai_tro, p.tac_vu): p for p in db.execute(select(AiPosition)).scalars()}
    tam = dang_tam_dung(db)
    rows = []
    for vai, ten in ROLES.items():
        o = {}
        for tac_vu in COT:
            p = co.get((vai, tac_vu))
            muc = p.muc if p else 0
            o[tac_vu] = {"muc": muc, "muc_ap_dung": 2 if (muc == 3 and tam) else muc,
                         "han_muc": (p.han_muc or {}) if p else {},
                         "thieu_han_muc": thieu_han_muc(muc, p.han_muc if p else {})}
        rows.append({"vai_tro": vai, "ten": ten, "o": o})
    return {
        "rows": rows, "nhom_viec": AI_GROUPS, "cot": list(COT), "muc": AI_LEVELS,
        "han_muc_bat_buoc": list(AI_HAN_MUC_BAT_BUOC),
        "tam_dung": bool(tam),
        "tam_dung_ly_do": tam.ly_do if tam else "", "tam_dung_boi": tam.boi if tam else "",
        "tam_dung_luc": tam.luc if tam else None,
        "chu_quan_hop_thu": CHU_QUAN_HOP_THU,
        "duoc_tu_gui": duoc_tu_gui(db)[0], "ly_do_khong_tu_gui": duoc_tu_gui(db)[1],
        "da_gui_hom_nay": so_luot_hom_nay(db, "tin_khach"),
    }
