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
#
# SỬA 11/9/2026 – Chủ tịch quyết, sau lần đo bản đang chạy sáng 11/9:
#   ptgd_mkt và nv_mkt ở ô tin_khach hạ từ mức 3 (tự động trong hạn mức) xuống mức 2 (soạn nháp).
#
# Lý do, ghi lại vì con số 3 ấy trông vô hại: bảng đặt mức 3 từ 07/9 với giả định "chưa có khoá API
# thì AI chưa làm gì được". Đo ngày 11/9 cho thấy giả định đó SAI – sáu tin đã được soạn và đẩy đi ở
# mức 3, tất cả bằng đường quy tắc dựng sẵn, trong khi 120/121 lượt chạy ghi lỗi thiếu khoá. Thiếu
# khoá không phải là cái phanh. Mức 2 mới là cái phanh, vì mức 2 không có đường nào tự gửi ra ngoài.
#
# Không vai trò nào còn ô mức 3 ở tin_khach. Nếu về sau có người đặt lại mức 3 ở đây, xin đọc kèm
# noi_dung_duoc_tu_gui() bên dưới trước khi đặt.
MAC_DINH: dict[str, tuple] = {
    "chutich":    (2, 0, 2, 1, 1, 4), "tgd":        (2, 0, 2, 1, 1, 4),
    "ptgd_doan":  (2, 2, 2, 1, 1, 4), "ptgd_mkt":   (2, 2, 2, 1, 1, 4),
    "tp_dh":      (2, 2, 2, 2, 1, 4), "nv_dh":      (1, 2, 2, 2, 0, 4),
    "gd_kd":      (2, 2, 2, 1, 1, 4), "tp_kd":      (2, 2, 2, 1, 1, 4),
    "tn_kd":      (1, 2, 1, 0, 0, 4), "nv_kd":      (1, 2, 1, 0, 0, 4),
    "nv_mkt":     (1, 2, 2, 0, 0, 4), "ketoan":     (2, 0, 2, 2, 0, 4),
    "hcns":       (1, 0, 2, 1, 1, 4), "hanh_chinh": (1, 0, 2, 1, 0, 4),
    "cntt":       (2, 0, 2, 1, 0, 4),
    # Vị trí Kiểm soát do AI giữ (chỉ đạo 07/9/2026): kiểm tra, thử, giám sát, báo cáo mọi phòng ban
    # về Chủ tịch. Ba ô mức 3 – hỏi đáp trên dữ liệu, soạn báo cáo nội bộ, chấm điểm phòng ban – và
    # mức 3 nghĩa là TỰ ĐỘNG TRONG HẠN MỨC, người hậu kiểm là Chủ tịch. Ô tin_khach để 0 và phải ở 0:
    # người đi giám sát không nói chuyện với khách hàng. Ô cảnh báo là mức 4 vì đó là quy tắc xác định.
    "bks":        (3, 0, 3, 2, 3, 4),
    "tai_xe":     (1, 0, 0, 1, 0, 4), "hdv":        (1, 0, 0, 1, 0, 4),
    "gd_doi_xe":  (1, 0, 1, 1, 0, 4),
    "nv_visa":    (1, 2, 1, 2, 0, 4),
}
COT = ("hoi_dap", "tin_khach", "vb_noi_bo", "doc_chung_tu", "cham_diem", "canh_bao")

# Hạn mức mặc định cho ô tin cho khách của Marketing. Từ 11/9/2026 ô này ở mức 2 nên hạn mức không
# còn là cái chặn; nó vẫn phải khai đủ, vì đây là bản khai người ta đọc khi cân nhắc nâng lại mức 3.
#
# nguoi_hau_kiem đổi ptgd_mkt → chutich (Chủ tịch quyết 11/9/2026, trong giai đoạn chạy demo).
# Bản cũ để ptgd_mkt hậu kiểm chính đầu ra của ptgd_mkt – người hậu kiểm phải ngồi ngoài nhóm việc
# mình kiểm, nếu không thì ô ấy chỉ là một cái tên điền cho đủ chỗ trống.
HAN_MUC_MAC_DINH = {
    "khung_gio": "08:00-21:00",
    "so_luot_ngay": 30,
    "loai_noi_dung": "lịch khởi hành, giá công bố, chính sách cọc và hủy, xin tên và số điện thoại",
    "nguoi_hau_kiem": "chutich",
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


# ---------------------------------------------------------------------------------------------
# PQ-3 · Cổng quyền cho CẢ SÁU nhóm việc
# ---------------------------------------------------------------------------------------------
# Năm nhóm việc do MÔ HÌNH NGÔN NGỮ làm. Trần của chúng là mức 3: luôn phải có hạn mức và người
# hậu kiểm. Mức 4 – tự động toàn phần – chỉ dành cho việc do MÃ XÁC ĐỊNH làm, tức canh_bao: cùng
# một dữ liệu vào thì luôn ra cùng một kết quả, và đọc mã là biết nó sẽ làm gì.
#
# Vì sao khai thành danh sách thay vì để người đặt mức tự cân nhắc: đặt mức là thao tác một ô, còn
# hậu quả thì nằm ở chỗ khác. Một ô mức 4 cho việc mô hình làm nghĩa là bỏ luôn khung giờ, số lượt
# và người hậu kiểm — ba thứ vốn là toàn bộ lý do bảng này tồn tại.
TAC_VU_MO_HINH = ("hoi_dap", "tin_khach", "vb_noi_bo", "doc_chung_tu", "cham_diem")
TAC_VU_MA_XAC_DINH = ("canh_bao",)


def duoc_lam(db: Session, vai_tro: str, tac_vu: str,
             luc: datetime | None = None) -> tuple[bool, str]:
    """Vị trí này có được TỰ LÀM việc ấy lúc này không, và nếu không thì VÌ SAO.

    Bốn phép kiểm, đúng bốn phép của bản cũ, nay áp cho cả sáu nhóm việc chứ không riêng tin cho
    khách: mức đang áp dụng · hạn mức đã khai đủ chưa · có trong khung giờ không · còn lượt trong
    ngày không. Đo ngày 10/9/2026: bảng khai sáu nhóm việc nhưng chỉ HAI nhóm thật sự bị chặn
    trong mã – tin_khach đi qua cổng này, doc_chung_tu chỉ đọc mức rồi thôi, còn vb_noi_bo,
    cham_diem, hoi_dap, canh_bao chạy mà không hỏi bảng. Bốn nút không nối vào đâu trên một bảng
    điều khiển thì nguy hiểm hơn là không có bảng.

    LUÔN trả kèm lý do. "Hôm nay AI không làm gì cả" mà không kèm lý do là thứ khiến người ta đi
    tắt tính năng thay vì sửa hạn mức.

    Việc NỐI cổng này vào từng chỗ gọi mô hình là VPM-6, thuộc làn Viết phần mềm. Tệp này chỉ khai
    luật và cho người khác đọc.
    """
    luc = luc or datetime.now()
    if tac_vu not in COT:
        return False, f"'{tac_vu}' không phải nhóm việc có trong bảng quyền AI"

    p = db.execute(select(AiPosition).where(AiPosition.vai_tro == vai_tro,
                                            AiPosition.tac_vu == tac_vu)).scalars().first()
    if p is None:
        return False, f"chưa cấu hình quyền AI cho {ROLES.get(vai_tro, vai_tro)} ở nhóm việc {tac_vu}"

    # Tắt khẩn chặn mọi việc do MÔ HÌNH làm. Nó KHÔNG chạm mức 4 của việc do mã xác định làm –
    # đúng bằng muc_cua(), vốn chỉ hạ mức 3 xuống 2. Tắt luôn cảnh báo tự động khi đang có sự cố
    # là tắt đúng cái đang cần nhất.
    tam = dang_tam_dung(db)
    if tam and not (p.muc >= 4 and tac_vu in TAC_VU_MA_XAC_DINH):
        return False, f"AI đối ngoại đang tạm dừng ({tam.ly_do or 'không ghi lý do'})"

    if p.muc >= 4:
        # Mức 4 hợp lệ thì cho qua ngay – việc do mã xác định làm không có hạn mức để kiểm.
        if tac_vu in TAC_VU_MA_XAC_DINH:
            return True, ""
        return False, (f"nhóm việc '{tac_vu}' do mô hình ngôn ngữ làm nên trần là mức 3; "
                       f"mức 4 chỉ dành cho việc do mã xác định làm")

    if p.muc < 3:
        return False, f"mức đang áp dụng là {p.muc} – {AI_LEVELS.get(p.muc, '')}, chỉ soạn nháp"

    thieu = thieu_han_muc(p.muc, p.han_muc)
    if thieu:
        return False, "mức 3 nhưng thiếu hạn mức: " + ", ".join(thieu)
    hm = p.han_muc or {}
    if not _trong_khung_gio(str(hm.get("khung_gio") or ""), luc):
        return False, f"ngoài khung giờ cho phép ({hm.get('khung_gio')})"
    gioi_han = int(hm.get("so_luot_ngay") or 0)
    da_lam = so_luot_hom_nay(db, tac_vu, luc.date())
    if gioi_han and da_lam >= gioi_han:
        return False, f"đã dùng hết {gioi_han} lượt trong ngày"
    return True, ""


def duoc_tu_gui(db: Session, luc: datetime | None = None) -> tuple[bool, str]:
    """AI có được tự gửi tin cho khách lúc này không, và nếu không thì VÌ SAO.

    Giữ nguyên tên và nguyên hành vi vì robot hộp thư đang gọi hàm này ở hai chỗ trong
    services/inbox.py – đó là mã nghiệp vụ, không phải tệp của làn Phân quyền. Nay nó là một lớp
    mỏng trên duoc_lam(): cùng một luật, một chỗ viết.

    Vẫn hỏi theo CHU_QUAN_HOP_THU chứ không theo vai trò người phụ trách hội thoại — AI trả lời
    khách là năng lực của KÊNH; tính theo từng tư vấn viên thì cùng một hộp thư lúc tự gửi lúc
    không, tuỳ hội thoại đã gán cho ai.
    """
    return duoc_lam(db, CHU_QUAN_HOP_THU, "tin_khach", luc)


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


# =============================================================================================
# PQ-3b (11/9/2026) · Cửa thứ hai: xét NỘI DUNG, không chỉ xét vai trò
# =============================================================================================
# duoc_lam() và duoc_tu_gui() trả lời câu "vai trò này có được tự động ở nhóm việc này không". Câu
# đó cần, nhưng nó được hỏi lúc BẮT ĐẦU – trước khi biết ai thật sự viết ra nội dung sắp gửi đi.
#
# Ngày 11/9/2026 đo trên bản đang chạy thấy khoảng trống ấy đã mở ra một lần thật: sáu tin gửi khách
# ở mức 3, cả sáu mang nguon="quy_tac", trong khi 120/121 lượt chạy ghi lỗi "chưa cấu hình
# ANTHROPIC_API_KEY". Lời gọi mô hình hỏng, mã rơi về một câu dựng sẵn, rồi vẫn gửi đi.
#
# Chỗ hỏng không phải là câu dựng sẵn ấy xấu – nó lịch sự và vô hại. Chỗ hỏng là mức 3 đã được cấp
# cho MỘT THỨ KHÁC: nhóm việc tin_khach nằm trong TAC_VU_MO_HINH, tức bảng quyền cho phép một câu
# trả lời do mô hình viết ra và bị ràng bởi loai_noi_dung đã khai. Một câu dựng sẵn trong mã không
# đọc loai_noi_dung, không biết khách vừa hỏi gì, và không ai duyệt nó qua bảng này bao giờ.
#
# Hệ quả nguy hiểm nhất là hệ quả về niềm tin: một lần gọi mô hình HỎNG lại biến thành một tin đã
# gửi, nên hệ thống càng hỏng thì càng gửi, và nhật ký vẫn xanh vì có ghi lỗi tử tế ở cột bên cạnh.


def noi_dung_duoc_tu_gui(tac_vu: str, nguon: str) -> tuple[bool, str]:
    """Nội dung vừa soạn xong này có được TỰ GỬI ra ngoài không, xét theo ai đã viết ra nó.

    Gọi SAU khi có nội dung và TRƯỚC khi gửi, chứ không thay cho duoc_tu_gui(): hai cửa hỏi hai câu
    khác nhau và phải qua cả hai.

      · nhóm việc do mô hình làm  → chỉ nội dung nguon="claude" mới được tự gửi
      · nhóm việc mã xác định     → nguon="quy_tac" mới đúng, vì đó chính là thứ mức 4 cho phép

    Trả về (được, lý do). Không được thì người gọi hạ xuống nháp – KHÔNG gửi, và cũng không im lặng
    bỏ qua: một hội thoại không được trả lời vẫn phải nhìn thấy được ở màn hình hộp thư.
    """
    if tac_vu in TAC_VU_MA_XAC_DINH:
        if nguon == "claude":
            return False, (f"nhóm việc '{tac_vu}' là quy tắc xác định, không phải việc của mô hình "
                           "ngôn ngữ – nội dung do mô hình viết không được tự gửi ở đây")
        return True, ""
    if nguon == "claude":
        return True, ""
    return False, (f"nội dung do {nguon or 'nguồn không ghi'} dựng sẵn chứ không do mô hình viết; "
                   f"mức 3 ở nhóm việc '{tac_vu}' cấp cho câu trả lời của mô hình có ràng buộc "
                   "loai_noi_dung, không cấp cho câu dựng sẵn trong mã")
