"""Ngoại lệ cần xử lý – nơi gom MỌI lần một quy tắc bị bẻ.

Khác "Cảnh báo nghiệp vụ" (/alerts) ở một điểm quyết định: cảnh báo nói "tình trạng đang xấu" và tự tắt
khi tình trạng hết xấu; ngoại lệ nói "đã có người cho qua một quy tắc" và KHÔNG tự tắt. Nó chỉ đóng khi
trả lời được ba câu: ai quyết, vì sao, và sau đó đã làm gì để không tái diễn.

Ngoại lệ được ĐỌC RA từ chính chỗ nó xảy ra – nhật ký bất biến, cờ trên chuyến, bảng miễn nộp visa, bảng
ngoại lệ quyền, nhật ký AI – chứ không chép sang bảng riêng. Chép ra bảng thứ hai thì có ngày hai bảng
nói khác nhau. Bảng duy nhất thêm vào (ngoai_le_xu_ly) chỉ lưu phần con người: nhận việc, giải trình, đóng.

Hai loại ngoại lệ, và sự khác nhau giữa chúng là toàn bộ giá trị của màn hình này:
  - CÓ CHỮ KÝ: quy tắc bị bẻ nhưng đúng người có thẩm quyền đã ký và ghi lý do. Đây là ngoại lệ lành mạnh
    – cần rà, không cần hoảng.
  - KHÔNG AI KÝ: hệ thống cho qua mà không ghi lại người nào. Cột "người quyết" phải để RỖNG chứ không
    điền một cái tên gần đúng cho đẹp bảng, và loại này luôn nổi lên đầu danh sách. Đóng một ngoại lệ
    loại này mà không nêu được tên người chịu trách nhiệm thì chỉ là xóa dấu vết, nên hệ thống chặn.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.core import AuditLog, Tour, User, UserGrant, AiRun, AiPause, Param, CAPABILITIES, KHONG_TRON_GOI
from app.models.ngoai_le import NgoaiLeXuLy, TRANG_THAI
from app.services import rules as R

# ---------------------------------------------------------------------------------------------
# Danh mục loại ngoại lệ. "muc" là mức nghiêm trọng MẶC ĐỊNH của loại; một số bộ dò nâng lên "do"
# theo hoàn cảnh (ví dụ ngoại lệ quyền không thời hạn).
#   do   = tiền hoặc trách nhiệm pháp lý đứng sau, phải có người trả lời
#   vang = cần rà soát định kỳ, chưa phải sự cố
# ---------------------------------------------------------------------------------------------
LOAI: dict[str, dict] = {
    "tour_duoi_bien": {"ten": "Duyệt chuyến dưới biên lợi nhuận", "muc": "do", "nhom": "tien",
                       "quy_tac": "Biên kế hoạch phải đạt ngưỡng nguong_bien (MHQT Điều 10)"},
    "d7_chay": {"ten": "Cho chạy chuyến dưới điểm hòa vốn (mốc D-7)", "muc": "do", "nhom": "tien",
                "quy_tac": "Chuyến chưa đủ khách hòa vốn phải ghép, dời hoặc hủy (ĐH Điều 13)"},
    "tour_chien_luoc": {"ten": "Gắn cờ tour chiến lược", "muc": "do", "nhom": "tien",
                        "quy_tac": "Cờ này miễn chế tài dưới biên khi tính hoa hồng – phải do Chủ tịch công bố"},
    "ban_khong_du_toan": {"ten": "Bán chuyến chưa có dự toán đủ cơ sở", "muc": "do", "nhom": "tien",
                          "quy_tac": "Không có giá vốn thì không tính được biên – cổng biên không thể ĐẠT (CONG_5)"},
    "dieu_chinh_quyet_toan": {"ten": "Thêm dòng điều chỉnh quyết toán thủ công", "muc": "do", "nhom": "tien",
                              "quy_tac": "Số quyết toán phải khớp chứng từ; dòng điều chỉnh tay là ngoại lệ"},
    "mo_lai_chuyen": {"ten": "Mở lại chuyến đã chốt", "muc": "do", "nhom": "tien",
                      "quy_tac": "Chuyến đã xác nhận thì đóng; mở lại là sửa số đã chốt"},
    "huy_hoa_don": {"ten": "Hủy hóa đơn đã lập", "muc": "do", "nhom": "tien",
                    "quy_tac": "Hóa đơn đã phát hành chỉ hủy theo quy định thuế"},
    "bo_qua_giao_dich": {"ten": "Bỏ qua giao dịch ngân hàng chưa khớp", "muc": "vang", "nhom": "tien",
                         "quy_tac": "Mọi giao dịch phải khớp về một chứng từ hoặc được nêu lý do"},
    "mo_khoa_booking": {"ten": "Mở khóa booking robot đã khóa", "muc": "vang", "nhom": "tien",
                        "quy_tac": "Robot khóa booking khi quá hạn cọc / quá deadline hủy chỗ"},
    "ngoai_le_quyen": {"ten": "Ngoại lệ quyền ngoài ma trận phân quyền", "muc": "vang", "nhom": "quyen",
                       "quy_tac": "Quyền cấp theo vai trò; cấp riêng cho một người là ngoại lệ có hạn"},
    "ai_cho_hau_kiem": {"ten": "AI mức 3 đã chạy, chưa ai hậu kiểm", "muc": "do", "nhom": "ai",
                        "quy_tac": "Mức 3 (tự động trong hạn mức) bắt buộc có người hậu kiểm"},
    "ai_tam_dung": {"ten": "AI đang bị hạ mức khẩn cấp", "muc": "vang", "nhom": "ai",
                    "quy_tac": "Nút tắt khẩn là trạng thái tạm; để lâu là đang chạy bằng tay"},
    "visa_mien_nop": {"ten": "Miễn nộp tài liệu visa bắt buộc", "muc": "vang", "nhom": "ho_so",
                      "quy_tac": "Mục bắt buộc trong danh mục hồ sơ phải nộp đủ"},
    "nap_bo_qua_dong_loi": {"ten": "Nạp dữ liệu có bỏ qua dòng lỗi", "muc": "vang", "nhom": "du_lieu",
                            "quy_tac": "Dòng lỗi phải sửa rồi nạp lại, không bỏ đi im lặng"},
    "tat_chan_giay_xe": {"ten": "Tắt chặn lệnh điều xe khi thiếu giấy tờ", "muc": "do", "nhom": "an_toan",
                         "quy_tac": "Xe/tài xế thiếu giấy tờ còn hạn thì không được phát lệnh (Đội xe v1.3 §7)"},
    "xe_khac_goi_y": {"ten": "Chốt lệnh điều xe khác phương án gợi ý", "muc": "vang", "nhom": "an_toan",
                      "quy_tac": "Chọn khác gợi ý phải nêu lý do (đã có), cần rà để biết gợi ý sai ở đâu"},
    # Robot Kiểm soát mở việc ra ở ĐÂY chứ không dựng một hàng đợi thứ hai: phòng ban đã có một cửa để
    # trả lời, thêm cửa nữa là thêm chỗ để quên.
    "ks_phat_hien": {"ten": "Robot Kiểm soát phát hiện", "muc": "do", "nhom": "kiem_soat",
                     "quy_tac": "Việc do vòng quét của robot Kiểm soát tìm ra, phòng ban phải giải trình"},
    # Cổng chặn giá vốn: đơn có doanh thu mà chưa có giá vốn thì KHÔNG được ghi doanh thu. Mỗi dòng ở
    # đây là một đơn đang bị giữ lại – để lâu là đến kỳ khóa sổ mà doanh thu vẫn chưa vào sổ.
    "dao_han_thieu_chan": {"ten": "Đáo hạn ngân hàng chỉ ghi một chân", "muc": "do", "nhom": "tien",
                           "quy_tac": "Đáo hạn là HAI bút toán – trả gốc khoản cũ và nhận giải ngân khoản mới. Bù trừ thành một dòng thì dư nợ vay không bao giờ đứng ở đỉnh"},
    "thieu_gia_von": {"ten": "Đơn có doanh thu nhưng chưa có giá vốn", "muc": "do", "nhom": "tien",
                      "quy_tac": "Mọi đơn đều có doanh thu và giá vốn (Chủ tịch 08/9/2026) – thiếu giá vốn là thiếu dữ liệu, không phải bản chất khác"},
}
NHOM = {"tien": "Tiền & quyết toán", "quyen": "Quyền hạn", "ai": "AI", "ho_so": "Hồ sơ",
        "du_lieu": "Dữ liệu", "an_toan": "An toàn vận hành", "kiem_soat": "Robot Kiểm soát"}
MUC = {"do": "Nghiêm trọng", "vang": "Cần rà soát"}

# Ngoại lệ cũ hơn số ngày này thì không dò nữa (trừ loại đang còn hiệu lực: quyền, tắt khẩn, tham số).
CUA_SO_NGAY = 180


def _u(db: Session, username: str) -> str:
    if not username: return ""
    r = db.execute(select(User.full_name).where(User.username == username)).scalars().first()
    return f"{r} ({username})" if r else username


def _mo(loai: str, khoa) -> str:
    return f"{loai}#{khoa}"


# ============================== CÁC BỘ DÒ ==============================
# Mỗi bộ dò trả về list dict cùng một khuôn:
#   ma, loai, muc, luc, doi_tuong, tom_tat, nguoi_quyet (rỗng = KHÔNG AI KÝ), ly_do, duong_dan

def _tu_nhat_ky(db: Session, tu_ngay: datetime, cau_hinh: dict[str, str]) -> list[dict]:
    """Ngoại lệ đã có chữ ký, đọc từ nhật ký bất biến theo tên hành động."""
    ra = []
    rows = db.execute(select(AuditLog).where(AuditLog.action.in_(list(cau_hinh)), AuditLog.ts >= tu_ngay)
                      .order_by(desc(AuditLog.ts))).scalars().all()
    for a in rows:
        loai = cau_hinh[a.action]
        sau = a.after if isinstance(a.after, dict) else {}
        ly_do = str(sau.get("ly_do") or sau.get("ghi_chu") or sau.get("note") or sau.get("mo_ta") or "").strip()
        ra.append({"ma": _mo(loai, a.id), "loai": loai, "muc": LOAI[loai]["muc"], "luc": a.ts,
                   "doi_tuong": a.entity, "nguoi_quyet": _u(db, a.actor), "ly_do": ly_do,
                   "tom_tat": f"{LOAI[loai]['ten']} – {a.entity}",
                   "duong_dan": f"/audit?q={a.entity}"})
    return ra


def _tour_chien_luoc(db: Session) -> list[dict]:
    """Cờ 'tour chiến lược' miễn chế tài dưới biên khi tính hoa hồng, nhưng KHÔNG có màn hình nào bật nó
    và không có bản ghi ai bật. Cờ đang bật = quyền lợi đang được miễn mà không ai ký."""
    ra = []
    for t in db.execute(select(Tour).where(Tour.strategic == True)).scalars():   # noqa: E712
        ra.append({"ma": _mo("tour_chien_luoc", t.code), "loai": "tour_chien_luoc", "muc": "do",
                   "luc": t.created_at, "doi_tuong": f"tour:{t.code}", "nguoi_quyet": "", "ly_do": "",
                   "tom_tat": f"{t.code} đang gắn cờ tour chiến lược – cờ này miễn chế tài dưới biên khi tính hoa hồng",
                   "duong_dan": f"/tours?q={t.code}"})
    return ra


def _ban_khong_du_toan(db: Session) -> list[dict]:
    """Chuyến nhập từ Vietrip được bán dù dự toán chưa đủ cơ sở tính. Hệ thống cố tình cho qua để không
    chặn dữ liệu lịch sử – nhưng mỗi chuyến như vậy là một chuyến đang bán mà không biết lãi hay lỗ."""
    ra = []
    thr = R.get_param(db, "nguong_bien")
    for t in db.execute(select(Tour).where(Tour.status.in_(["da_duyet", "ket_thuc"]))).scalars():
        if not getattr(t, "imported", False) or t.tour_type in KHONG_TRON_GOI: continue
        if not t.bookings: continue
        if R.calc_db(db, t, thr)["complete"]: continue
        ra.append({"ma": _mo("ban_khong_du_toan", t.code), "loai": "ban_khong_du_toan", "muc": "do",
                   "luc": t.created_at, "doi_tuong": f"tour:{t.code}",
                   "nguoi_quyet": "", "ly_do": "",
                   "tom_tat": f"{t.code} đã có {len(t.bookings)} booking nhưng dự toán chưa đủ cơ sở tính biên",
                   "duong_dan": f"/tours?q={t.code}"})
    return ra


def _ngoai_le_quyen(db: Session) -> list[dict]:
    ra = []
    for g in db.execute(select(UserGrant).where(UserGrant.active == True)).scalars():   # noqa: E712
        if not g.hieu_luc(): continue
        u = db.get(User, g.user_id)
        ten = CAPABILITIES.get(g.value, g.value) if g.kind == "capability" else f"màn hình {g.value}"
        han = "KHÔNG THỜI HẠN" if g.vo_han() else f"đến {g.to_date:%d/%m/%Y}"
        ra.append({"ma": _mo("ngoai_le_quyen", g.id), "loai": "ngoai_le_quyen",
                   "muc": "do" if g.vo_han() else "vang", "luc": g.created_at,
                   "doi_tuong": f"user:{u.username if u else g.user_id}",
                   "nguoi_quyet": _u(db, g.approved_by), "ly_do": g.reason,
                   "tom_tat": f"{u.full_name if u else g.user_id}: {ten} – {han}",
                   "duong_dan": "/access?tab=ngoai-le"})
    return ra


def _ai(db: Session) -> list[dict]:
    ra = []
    for r in db.execute(select(AiRun).where(AiRun.trang_thai == "cho_hau_kiem").order_by(desc(AiRun.ts))).scalars():
        ra.append({"ma": _mo("ai_cho_hau_kiem", r.id), "loai": "ai_cho_hau_kiem", "muc": "do", "luc": r.ts,
                   "doi_tuong": r.ref or f"ai_run:{r.id}", "nguoi_quyet": "", "ly_do": "",
                   "tom_tat": f"AI mức {r.muc} ({r.tac_vu}) đã chạy lúc {r.ts:%d/%m %H:%M}, chưa ai hậu kiểm",
                   "duong_dan": "/ai-roles?tab=nhat-ky"})
    p = db.get(AiPause, 1)
    if p is not None and p.tam_dung:
        ra.append({"ma": _mo("ai_tam_dung", "1"), "loai": "ai_tam_dung", "muc": "vang",
                   "luc": p.luc or datetime.now(), "doi_tuong": "ai_pause:1",
                   "nguoi_quyet": _u(db, p.boi), "ly_do": p.ly_do,
                   "tom_tat": "Toàn bộ ô AI mức 3 đang bị hạ xuống mức 2 (nút tắt khẩn)",
                   "duong_dan": "/ai-roles"})
    return ra


def _visa_mien_nop(db: Session, tu_ngay: datetime) -> list[dict]:
    try:
        from app.models.visa import VisaWaiver, VisaCase, VisaChecklistItem
    except Exception:
        return []
    ra = []
    for w in db.execute(select(VisaWaiver).where(VisaWaiver.decision == "APPROVED")).scalars():
        if w.decided_at and w.decided_at < tu_ngay: continue
        c = db.get(VisaCase, w.case_id)
        it = db.get(VisaChecklistItem, w.checklist_item_id)
        ra.append({"ma": _mo("visa_mien_nop", w.id), "loai": "visa_mien_nop", "muc": "vang",
                   "luc": w.decided_at or w.requested_at,
                   "doi_tuong": f"visa:{c.case_code if c else w.case_id}",
                   "nguoi_quyet": _u(db, w.decided_by), "ly_do": w.reason,
                   "tom_tat": f"Miễn nộp mục bắt buộc “{getattr(it, 'label', None) or getattr(it, 'key', '')}”"
                              f" – hồ sơ {c.case_code if c else w.case_id}",
                   "duong_dan": f"/visa?q={c.case_code if c else ''}"})
    return ra


def _nap_bo_qua(db: Session, tu_ngay: datetime) -> list[dict]:
    try:
        from app.models.intake import IntakeRun
    except Exception:
        return []
    ra = []
    for r in db.execute(select(IntakeRun).where(IntakeRun.bo_qua_dong_loi == True,      # noqa: E712
                                                IntakeRun.dong_loi > 0,
                                                IntakeRun.luc >= tu_ngay).order_by(desc(IntakeRun.luc))).scalars():
        ra.append({"ma": _mo("nap_bo_qua_dong_loi", r.id), "loai": "nap_bo_qua_dong_loi", "muc": "vang",
                   "luc": r.luc, "doi_tuong": f"intake:{r.loai}",
                   "nguoi_quyet": _u(db, r.boi), "ly_do": "",
                   "tom_tat": f"Nạp {r.loai} từ “{r.ten_tep}”: vào {r.da_nap} dòng, BỎ {r.dong_loi} dòng lỗi",
                   "duong_dan": "/nap-du-lieu"})
    return ra


def _tat_chan_giay_xe(db: Session) -> list[dict]:
    """Một tham số duy nhất tắt việc chặn lệnh điều xe khi xe hoặc tài xế thiếu giấy tờ còn hạn.
    Đây là ngoại lệ có bán kính rộng nhất trong hệ thống: nó không nhắm vào một chuyến nào, nó tắt
    kiểm tra cho MỌI lệnh điều xe."""
    v = db.execute(select(Param).where(Param.key == "xe_chan_khi_thieu_giay", Param.status == "active",
                                       Param.effective_from <= date.today())
                   .order_by(desc(Param.effective_from), desc(Param.id))).scalars().first()
    if v is None: return []
    try:
        bat = float(str(v.value).strip()) >= 1
    except ValueError:
        bat = False
    if bat: return []
    # Tham số đi qua cửa 2 chữ ký, nên NGƯỜI QUYẾT ở đây là người đề xuất bản ghi đang có hiệu lực –
    # rỗng khi giá trị này là giá trị khởi tạo của hệ thống, tức là không ai từng quyết định tắt nó.
    return [{"ma": _mo("tat_chan_giay_xe", "param"), "loai": "tat_chan_giay_xe", "muc": "do",
             "luc": datetime.combine(v.effective_from, datetime.min.time()),
             "doi_tuong": "param:xe_chan_khi_thieu_giay",
             "nguoi_quyet": _u(db, v.proposed_by) if (v.signed_chutich and v.signed_tgd) else "",
             "ly_do": v.source or "",
             "tom_tat": "Đang TẮT chặn phát lệnh điều xe khi thiếu giấy tờ xe/tài xế – áp dụng cho mọi lệnh",
             "duong_dan": "/params?q=xe_chan_khi_thieu_giay"}]


def _ks_phat_hien(db: Session) -> list[dict]:
    """Việc robot Kiểm soát đang thấy. Người quyết để RỖNG có chủ ý: chưa ai trả lời việc này."""
    try:
        from app.models.kiem_soat import KsPhatHien
    except Exception:
        return []
    ra = []
    for p in db.execute(select(KsPhatHien).where(KsPhatHien.con == True)).scalars():   # noqa: E712
        ra.append({"ma": _mo("ks_phat_hien", p.ma), "loai": "ks_phat_hien",
                   "muc": "do" if p.muc == "do" else "vang", "luc": p.lan_dau,
                   "doi_tuong": f"{p.phong_ban or 'toàn hệ thống'} · {p.doi_tuong}",
                   "nguoi_quyet": "", "ly_do": "",
                   "tom_tat": p.tom_tat + (f" (thấy lại {p.so_lan} lần)" if p.so_lan > 1 else ""),
                   "duong_dan": "/kiem-soat"})
    return ra


def _xe_khac_goi_y(db: Session, tu_ngay: datetime) -> list[dict]:
    try:
        from app.models.hr import DispatchOrder
    except Exception:
        return []
    ra = []
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.ly_do_khac_goi_y != "",
                                                    DispatchOrder.created_at >= tu_ngay)
                        .order_by(desc(DispatchOrder.created_at))).scalars():
        ra.append({"ma": _mo("xe_khac_goi_y", d.id), "loai": "xe_khac_goi_y", "muc": "vang",
                   "luc": d.created_at, "doi_tuong": f"lenh_dieu_xe:{d.id}",
                   "nguoi_quyet": _u(db, d.created_by), "ly_do": d.ly_do_khac_goi_y,
                   "tom_tat": f"Lệnh điều xe #{d.id} chốt khác phương án gợi ý",
                   "duong_dan": "/lenh-dieu-xe"})
    return ra


# Hành động trong nhật ký bất biến ⇒ loại ngoại lệ
TU_NHAT_KY = {
    "ky_duyet_duoi_bien": "tour_duoi_bien",
    "duyet_du_toan_2_chu_ky": "tour_duoi_bien",
    "d7_chay": "d7_chay",
    "mo_lai_chuyen": "mo_lai_chuyen",
    "mo_khoa_booking": "mo_khoa_booking",
    "bo_qua_giao_dich": "bo_qua_giao_dich",
    "dieu_chinh_quyet_toan": "dieu_chinh_quyet_toan",
    "huy_hoa_don": "huy_hoa_don",
}


def _cong_chan_gia_von(db: Session) -> list[dict]:
    """Hàng đợi cổng chặn giá vốn, đọc thẳng từ bảng thieu_gia_von – không chép sang bảng thứ hai."""
    from app.services import cong_chan as CC
    return CC.ngoai_le(db)


def _dao_han_thieu_chan(db: Session) -> list[dict]:
    from app.services import cong_chan as CC
    return CC.dao_han_thieu_chan(db)


def do_tim(db: Session, so_ngay: int = CUA_SO_NGAY) -> list[dict]:
    """Chạy toàn bộ bộ dò. Không ghi gì vào cơ sở dữ liệu – chỉ đọc."""
    tu_ngay = datetime.now() - timedelta(days=so_ngay)
    ra: list[dict] = []
    bo_do = (
        lambda: _tu_nhat_ky(db, tu_ngay, TU_NHAT_KY),
        lambda: _tour_chien_luoc(db),
        lambda: _ban_khong_du_toan(db),
        lambda: _ngoai_le_quyen(db),
        lambda: _ai(db),
        lambda: _visa_mien_nop(db, tu_ngay),
        lambda: _nap_bo_qua(db, tu_ngay),
        lambda: _tat_chan_giay_xe(db),
        lambda: _xe_khac_goi_y(db, tu_ngay),
        lambda: _ks_phat_hien(db),
        lambda: _cong_chan_gia_von(db),
        lambda: _dao_han_thieu_chan(db),
    )
    for f in bo_do:
        try:
            ra += f()
        except Exception as ex:      # một bộ dò hỏng không được làm trắng cả màn hình rủi ro
            ra.append({"ma": _mo("loi_bo_do", len(ra)), "loai": "tat_chan_giay_xe", "muc": "do",
                       "luc": datetime.now(), "doi_tuong": "he_thong", "nguoi_quyet": "", "ly_do": "",
                       "tom_tat": f"Một bộ dò ngoại lệ lỗi, danh sách có thể THIẾU: {str(ex)[:160]}",
                       "duong_dan": ""})
    ra.sort(key=lambda x: (x["muc"] != "do", -(x["luc"].timestamp() if x["luc"] else 0)))
    return ra


# ============================== GHÉP VỚI VIỆC XỬ LÝ ==============================
def _ho_so(db: Session, ma_list: list[str]) -> dict[str, NgoaiLeXuLy]:
    if not ma_list: return {}
    rows = db.execute(select(NgoaiLeXuLy).where(NgoaiLeXuLy.ma.in_(ma_list))).scalars().all()
    return {r.ma: r for r in rows}


# Một loại ngoại lệ có thể có hàng trăm dòng giống hệt nhau về bản chất – ví dụ "bán chuyến chưa có dự
# toán đủ cơ sở" đang là 754 chuyến nhập từ Vietrip. Trả hết ra thì màn hình dài vô ích và phần còn lại
# chìm nghỉm. Nên CẮT theo từng loại, nhưng CON SỐ TỔNG HỢP vẫn đếm trên toàn bộ: cắt để nhìn được, không
# phải để báo cáo nhỏ đi.
CAT_MOI_LOAI = 50


def danh_sach(db: Session, trang_thai: str = "", loai: str = "", nhom: str = "",
              chi_thieu_chu_ky: bool = False, so_ngay: int = CUA_SO_NGAY,
              cat_moi_loai: int = CAT_MOI_LOAI) -> dict:
    items = do_tim(db, so_ngay)
    ho_so = _ho_so(db, [i["ma"] for i in items])
    ra = []
    for i in items:
        h = ho_so.get(i["ma"])
        tt = h.trang_thai if h else "chua"
        thieu = not bool(i["nguoi_quyet"])
        row = {**i,
               "loai_ten": LOAI[i["loai"]]["ten"], "nhom": LOAI[i["loai"]]["nhom"],
               "nhom_ten": NHOM[LOAI[i["loai"]]["nhom"]], "quy_tac": LOAI[i["loai"]]["quy_tac"],
               "muc_ten": MUC[i["muc"]],
               "thieu_chu_ky": thieu,
               "trang_thai": tt, "trang_thai_ten": TRANG_THAI[tt],
               "nguoi_nhan": h.nguoi_nhan if h else "", "giai_trinh": h.giai_trinh if h else "",
               "da_lam": h.da_lam if h else "",
               "nguoi_chiu_trach_nhiem": h.nguoi_chiu_trach_nhiem if h else "",
               "dong_boi": h.dong_boi if h else "",
               "dong_luc": h.dong_luc.isoformat() if (h and h.dong_luc) else None,
               "luc": i["luc"].isoformat() if i["luc"] else None,
               "so_ngay_ton": (datetime.now() - i["luc"]).days if i["luc"] else None}
        if trang_thai and tt != trang_thai: continue
        if loai and i["loai"] != loai: continue
        if nhom and row["nhom"] != nhom: continue
        if chi_thieu_chu_ky and not thieu: continue
        ra.append(row)
    tong_hop = _tong_hop(ra)                      # đếm trên TOÀN BỘ, trước khi cắt
    dem: dict[str, int] = {}
    cat: dict[str, int] = {}
    gon = []
    for r in ra:
        dem[r["loai"]] = dem.get(r["loai"], 0) + 1
        if cat_moi_loai and dem[r["loai"]] > cat_moi_loai:
            cat[r["loai"]] = cat.get(r["loai"], 0) + 1
            continue
        gon.append(r)
    tong_hop["bi_cat"] = cat
    tong_hop["theo_loai"] = dem
    return {"rows": gon, "tong_hop": tong_hop, "loai": LOAI, "nhom": NHOM,
            "trang_thai": TRANG_THAI, "cua_so_ngay": so_ngay, "cat_moi_loai": cat_moi_loai}


def _tong_hop(rows: list[dict]) -> dict:
    mo = [r for r in rows if r["trang_thai"] != "dong"]
    return {
        "tong": len(rows),
        "chua_dong": len(mo),
        "nghiem_trong_chua_dong": len([r for r in mo if r["muc"] == "do"]),
        # Con số quan trọng nhất của màn hình: ngoại lệ mà hệ thống đã cho qua nhưng không ai ký.
        "khong_ai_ky": len([r for r in mo if r["thieu_chu_ky"]]),
        "ton_qua_30_ngay": len([r for r in mo if (r["so_ngay_ton"] or 0) > 30]),
        "theo_nhom": {k: len([r for r in mo if r["nhom"] == k]) for k in NHOM},
    }


# ============================== THAO TÁC ==============================
def _lay(db: Session, ma: str) -> tuple[NgoaiLeXuLy, dict]:
    goc = next((i for i in do_tim(db) if i["ma"] == ma), None)
    if goc is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Không tìm thấy ngoại lệ này (có thể đã ngoài cửa sổ dò)")
    h = db.execute(select(NgoaiLeXuLy).where(NgoaiLeXuLy.ma == ma)).scalars().first()
    if h is None:
        h = NgoaiLeXuLy(ma=ma); db.add(h); db.flush()
    return h, goc


def nhan(db: Session, u: User, ma: str) -> str:
    h, _ = _lay(db, ma)
    if h.trang_thai == "dong":
        from fastapi import HTTPException
        raise HTTPException(400, "Ngoại lệ đã đóng")
    h.nguoi_nhan, h.nhan_luc, h.trang_thai = u.username, datetime.now(), "dang"
    h.so_lan_ghi += 1
    R.audit(db, u.username, u.role, "nhan_ngoai_le", f"ngoai_le:{ma}", after={"nguoi_nhan": u.username})
    db.commit()
    return "Đã nhận xử lý"


def ghi(db: Session, u: User, ma: str, giai_trinh: str = "", da_lam: str = "",
        nguoi_chiu_trach_nhiem: str = "") -> str:
    h, _ = _lay(db, ma)
    if h.trang_thai == "dong":
        from fastapi import HTTPException
        raise HTTPException(400, "Ngoại lệ đã đóng – muốn ghi thêm phải mở lại")
    truoc = {"giai_trinh": h.giai_trinh, "da_lam": h.da_lam,
             "nguoi_chiu_trach_nhiem": h.nguoi_chiu_trach_nhiem}
    if giai_trinh.strip(): h.giai_trinh = giai_trinh.strip()
    if da_lam.strip(): h.da_lam = da_lam.strip()
    if nguoi_chiu_trach_nhiem.strip(): h.nguoi_chiu_trach_nhiem = nguoi_chiu_trach_nhiem.strip()
    if h.trang_thai == "chua":
        h.trang_thai, h.nguoi_nhan, h.nhan_luc = "dang", h.nguoi_nhan or u.username, h.nhan_luc or datetime.now()
    h.so_lan_ghi += 1
    R.audit(db, u.username, u.role, "ghi_ngoai_le", f"ngoai_le:{ma}", before=truoc,
            after={"giai_trinh": h.giai_trinh, "da_lam": h.da_lam,
                   "nguoi_chiu_trach_nhiem": h.nguoi_chiu_trach_nhiem})
    db.commit()
    return "Đã ghi"


def dong(db: Session, u: User, ma: str, ket_luan: str = "") -> str:
    from fastapi import HTTPException
    h, goc = _lay(db, ma)
    if h.trang_thai == "dong": raise HTTPException(400, "Đã đóng rồi")
    if ket_luan.strip(): h.da_lam = (h.da_lam + "\n" if h.da_lam else "") + ket_luan.strip()
    if len(h.giai_trinh.strip()) < 20:
        raise HTTPException(400, "Phải có giải trình (ít nhất 20 ký tự) trước khi đóng: vì sao quy tắc đã bị bẻ")
    if not h.da_lam.strip():
        raise HTTPException(400, "Phải ghi đã làm gì để ngoại lệ này không tái diễn")
    # Ngoại lệ không ai ký: đóng mà không nêu tên người chịu trách nhiệm thì chỉ là xóa dấu vết.
    if not goc["nguoi_quyet"] and not h.nguoi_chiu_trach_nhiem.strip():
        raise HTTPException(400, "Ngoại lệ này hệ thống cho qua mà không ai ký. Phải nêu tên người chịu "
                                 "trách nhiệm mới đóng được")
    h.trang_thai, h.dong_boi, h.dong_luc = "dong", u.username, datetime.now()
    h.so_lan_ghi += 1
    R.audit(db, u.username, u.role, "dong_ngoai_le", f"ngoai_le:{ma}",
            after={"giai_trinh": h.giai_trinh, "da_lam": h.da_lam,
                   "nguoi_chiu_trach_nhiem": h.nguoi_chiu_trach_nhiem, "loai": goc["loai"]})
    db.commit()
    return "Đã đóng ngoại lệ"


def mo_lai(db: Session, u: User, ma: str, ly_do: str) -> str:
    from fastapi import HTTPException
    if len(ly_do.strip()) < 10: raise HTTPException(400, "Mở lại phải nêu lý do")
    h, _ = _lay(db, ma)
    if h.trang_thai != "dong": raise HTTPException(400, "Ngoại lệ chưa đóng")
    h.trang_thai, h.dong_boi, h.dong_luc = "dang", "", None
    h.da_lam = (h.da_lam + "\n" if h.da_lam else "") + f"[Mở lại {datetime.now():%d/%m/%Y} bởi {u.username}] {ly_do.strip()}"
    h.so_lan_ghi += 1
    R.audit(db, u.username, u.role, "mo_lai_ngoai_le", f"ngoai_le:{ma}", after={"ly_do": ly_do.strip()})
    db.commit()
    return "Đã mở lại"
