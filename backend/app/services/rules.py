"""Rules engine, nhật ký hash-chain, tính toán dự toán, robot cảnh báo."""
import hashlib, json, math
from datetime import datetime, date, timedelta
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models.core import Param, AuditLog, Tour, Booking, ServiceRequest, Alert, TOUR_TYPES, User

# ====================== THAM SỐ MẶC ĐỊNH (theo bộ chính sách 27/8/2026 + Văn bản đính chính) ======================
DEFAULT_PARAMS = [
    ("nguong_bien", "0.10", "Ngưỡng biên lợi nhuận kế hoạch (cổng chặn)", "tỷ lệ", "MHQT Điều 10"),
    ("han_qt_doan", "7", "Hạn quyết toán tour đoàn", "ngày", "MHQT Điều 10; ĐC Điều 1"),
    ("han_qt_le", "3", "Hạn quyết toán tour lẻ", "ngày", "MHQT Điều 10; ĐC Điều 1"),
    ("han_kt_xac_nhan", "3", "Kế toán xác nhận sau khi đóng số", "ngày làm việc", "KT-HCNS; ĐC Điều 1"),
    ("sla_booking_phut", "120", "Điều hành tạo booking sau khi nhận yêu cầu", "phút làm việc", "ĐH Điều 2"),
    ("moc_d7", "7", "Mốc D-n kiểm tra chuyến dưới hòa vốn", "ngày", "ĐH Điều 13"),
    # Đội xe Đợt 1: bật thành 1 khi hồ sơ giấy tờ 14 xe đã nhập đủ. Để 0 trong giai đoạn nhập liệu, vì chặn
    # theo giấy tờ khi chưa có giấy tờ nào trong hệ thống thì mọi lệnh điều xe đều dừng.
    ("xe_chan_khi_thieu_giay", "0", "Chặn phát lệnh khi thiếu dữ liệu giấy tờ xe/tài xế", "0 hoặc 1", "Đội xe Vietrip v1.3 §7"),
    ("han_muc_mkt", "5000000", "Hạn mức chi Marketing cần 2 chữ ký", "đồng", "MKT Điều 8"),
    ("coc_mac_dinh_pct", "30", "Tỷ lệ cọc mặc định khi sản phẩm không quy định", "%", "Vận hành Vietrip"),
    ("han_coc_gio", "24", "Hạn khách đặt cọc sau khi tạo booking (quá → cảnh báo sale/ĐH)", "giờ", "Vận hành Vietrip"),
    ("han_huy_cho_ngay", "3", "Deadline hủy chỗ / thu đủ trước khởi hành (đóng tour, khóa booking)", "ngày", "Vận hành Vietrip"),
    ("bao_luu_han_ngay", "90", "Hạn hiệu lực tiền bảo lưu (cảnh báo trước 7 ngày)", "ngày", "Vận hành Vietrip"),
    ("sla_tra_loi_chat_phut", "5", "Sale phải trả lời tin nhắn khách (Facebook/Zalo/web) trong giờ làm việc; quá → AI trả lời thay", "phút", "MKT/KD – hộp thư đa kênh"),
    ("sla_tra_loi_ngoai_gio_phut", "15", "Ngoài giờ làm việc (trước 8h, sau 21h): AI trả lời thay sau", "phút", "MKT/KD – hộp thư đa kênh"),
    ("ai_tra_loi_bat", "1", "Bật robot AI trả lời thay khi sale trễ (1 bật / 0 tắt)", "cờ", "MKT/KD – hộp thư đa kênh"),
    ("quy_dh_le_noi_dia", "0.02", "Quỹ thưởng Điều hành – tour lẻ nội địa", "tỷ lệ LN", "ĐH Điều 5"),
    ("quy_dh_le_nuoc_ngoai", "0.01", "Quỹ thưởng Điều hành – tour lẻ nước ngoài", "tỷ lệ LN", "ĐH Điều 5"),
    ("quy_dh_doan", "0.01", "Quỹ thưởng Điều hành – tour đoàn (không phụ thuộc biên)", "tỷ lệ LN", "ĐH Điều 5; ĐC Điều 7"),
    ("quy_dh_chia_nv", "0.70", "Phần nhân viên trong quỹ Điều hành (Trưởng phòng 30%)", "tỷ lệ", "ĐH Điều 6"),
    ("hh_doan_ty_le", "0.10", "Hoa hồng NV kinh doanh đoàn trên phần LN vượt mốc", "tỷ lệ", "Đoàn Điều 7"),
    ("hh_doan_moc", "20000000", "Mốc LN đoàn/tháng bắt đầu tính hoa hồng", "đồng", "Đoàn Điều 7"),
    ("ptgd_doan_ty_le", "0.05", "PTGĐ tour đoàn – tỷ lệ LN sau quyết toán", "tỷ lệ", "TP Đoàn"),
    ("sale_admin_ty_le", "0.02", "Sale Admin – tỷ lệ LN sau quyết toán", "tỷ lệ", "TP Đoàn"),
    ("visa_tu_xu_ly", "200000", "Đơn giá visa – hồ sơ tự xử lý", "đồng/hồ sơ", "ĐH Điều 7"),
    ("visa_gui_doi_tac", "50000", "Đơn giá visa – gửi đối tác", "đồng/hồ sơ", "ĐH Điều 7"),
    ("moc_chi_tieu_hcm", "200000000", "Mốc chỉ tiêu doanh thu NV kinh doanh lẻ HCM", "đồng/tháng", "KD Lẻ"),
    ("moc_chi_tieu_cantho", "120000000", "Mốc chỉ tiêu doanh thu NV Cần Thơ và văn phòng tỉnh (Bình Dương khách lẻ dùng mốc HCM)", "đồng/tháng", "KD Lẻ Phụ lục B.2"),
    ("thang_f_bang", "65:0,70:0,90:0,100:0,110:0.5,130:0.8,160:1.1,200:1.4,250:1.7,300:2,350:2.3,400:2.6,450:2.9,500:3.2,550:3.5,600:3.8,700:4.1,800:4.4,900:4.7,1000:5",
     "Bảng B.1 thang f: 'ngưỡng % mốc:hệ số %' từ f1 đến f19 và trần 1000%; f0 dưới ngưỡng đầu; ngưỡng tiền = % × mốc văn phòng", "bảng", "KD Lẻ Phụ lục A, B.1"),
    ("ca_truc_phut", "5", "Thời gian trả lời khách trong ca trực page", "phút", "KD Lẻ Điều 2a"),
    ("tai_xe_cong_tac_phi", "200000", "Công tác phí tài xế mỗi ngày tour", "đồng/ngày", "Đội xe"),
    # ---- Đội xe Vietrip Đợt 2. Đặc tả nói thẳng: "Toàn bộ số dưới đây phải nằm trong bảng cấu hình có giao
    # diện sửa, kèm lịch sử thay đổi. Lập trình viên không được viết thẳng vào mã." Dùng luôn bảng tham số
    # chính sách sẵn có thay vì dựng bảng cấu hình thứ hai: nó đã có hiệu lực theo ngày, có lịch sử và có
    # chữ ký duyệt – mà mấy con số này là tiền, nên đi qua cửa ký là đúng chứ không phải phiền.
    # Công tác phí tài xế dùng lại khóa tai_xe_cong_tac_phi ở trên (200.000 đ/ngày, khớp giá trị đã xác nhận).
    ("xe_chu_ky_bao_duong_km", "9000", "Chu kỳ bảo dưỡng xe (mốc chung; xe có mốc riêng thì ghi ở hồ sơ xe)", "km", "Đội xe v1.3 – A1, A5"),
    ("xe_bd_gap_km", "2000", "Còn dưới mốc này tới kỳ bảo dưỡng thì báo GẤP", "km", "Đội xe v1.3 – A5"),
    ("xe_bd_theo_doi_km", "5000", "Còn dưới mốc này thì đưa vào diện theo dõi bảo dưỡng", "km", "Đội xe v1.3 – A5"),
    ("xe_giay_to_vang_ngay", "30", "Giấy tờ xe/GPLX còn dưới số ngày này thì cảnh báo vàng", "ngày", "Đội xe v1.3 – A5"),
    ("xe_giay_to_do_ngay", "7", "Giấy tờ còn dưới số ngày này (hoặc đã quá hạn) thì cảnh báo đỏ", "ngày", "Đội xe v1.3 – A5"),
    ("xe_luong_khoan_hop_tac_thang", "7000000", "Lương khoán tài xế xe hợp tác", "đồng/xe/tháng", "Đội xe v1.3 – A6, chốt 07/9/2026"),
    ("xe_phi_bai_dau_thang", "2000000", "Phí bãi đậu xe (chưa VAT)", "đồng/xe/tháng", "Đội xe v1.3 – A6, chốt 07/9/2026"),
    ("xe_bai_dau_vat", "0.08", "Thuế suất VAT phí bãi đậu xe", "tỷ lệ", "Đội xe v1.3 – A6, chốt 07/9/2026"),
    ("xe_tieu_hao_min", "2.5", "Cận dưới dải tiêu hao nhiên liệu hợp lý", "km/lít", "Đội xe v1.3 – A2"),
    ("xe_tieu_hao_max", "4.5", "Cận trên dải tiêu hao nhiên liệu hợp lý", "km/lít", "Đội xe v1.3 – A2"),
    ("xe_lech_dau_vang", "0.10", "Định mức dầu đ/km lệch quá mức này so với trung bình 6 tháng của CHÍNH xe đó → vàng", "tỷ lệ", "Đội xe v1.3 – A3"),
    ("xe_lech_dau_do", "0.20", "Lệch quá mức này → đỏ", "tỷ lệ", "Đội xe v1.3 – A3"),
    ("xe_lech_km_gps", "0.05", "Km đọc từ ảnh lệch km GPS quá mức này → đỏ", "tỷ lệ", "Đội xe v1.3 – A2"),
    ("xe_lech_km_noi_chuyen", "50", "Km cuối chuyến trước lệch km đầu chuyến sau quá mức này → vàng (nghi có chuyến chưa khai)", "km", "Đội xe v1.3 – A2"),
    ("xe_vay_dao_han_ngay", "60", "Cảnh báo trước ngày đáo hạn khế ước", "ngày", "Đội xe v1.3 – A8"),
    ("xe_vay_tra_goc_ngay", "10", "Cảnh báo trước kỳ trả gốc", "ngày", "Đội xe v1.3 – A8"),
    ("xe_chung_tu_bat_buoc_tu", "10000000", "Khoản chi từ mức này bắt buộc có chứng từ gốc đính kèm", "đồng", "Đội xe v1.3 – B6"),
    ("xe_chenh_gia_ban_vang", "0.20", "Giá chào bán thấp hơn định giá nội bộ quá mức này → cờ vàng bắt buộc giải trình", "tỷ lệ", "Đội xe v1.3 – A9"),
    # Chỉ đạo Chủ tịch 07/9/2026: GĐ điều hành đội xe là người DUY NHẤT được tạo và chốt lệnh điều xe.
    # Ghi bằng tài khoản/mã nhân viên trong tham số chứ KHÔNG viết tên một người vào mã nguồn – thay người
    # phụ trách thì sửa tham số, không phải sửa phần mềm và triển khai lại. Nhận nhiều giá trị, ngăn bởi dấu
    # phẩy; để trống là giữ nguyên quy tắc theo vai trò như trước.
    ("xe_sua_chua_ben_chiu", "vietourist_tam_ung", "Sửa chữa/bảo dưỡng mặc định bên nào chịu",
     "vietourist_tam_ung hoặc chu_xe", "Chủ tịch chốt lại cuối ngày 07/9/2026 – giữ cách chi hộ đang làm"),
    ("xe_ky_quyet_toan_ap_dung_tu", "2026-09", "Kỳ đầu tiên áp dụng cách cắt kỳ theo tháng dương lịch; kỳ "
     "trước mốc này đã quyết toán xong theo cách cũ nên máy không dựng lại", "YYYY-MM", "Chủ tịch 07/9/2026"),
    ("xe_nguoi_lap_lenh", "53","Tài khoản (hoặc mã nhân viên) được tạo và chốt lệnh điều xe – để trống là theo vai trò", "danh sách", "Chủ tịch 07/9/2026"),
    ("moc_luong_doan", "30000000", "Mốc bình quân LN quyết toán 3 tháng để hưởng đủ lương NV kinh doanh đoàn", "đồng", "Đoàn Điều 5"),
    ("phat_su_vu", "1000000", "Chế tài mỗi sự vụ từ mức 2 (chỉ trừ hoa hồng)", "đồng/vụ", "KD Lẻ"),
    # Khoản trừ của NGƯỜI LAO ĐỘNG, áp từ kỳ lương 01/9/2026 (Bộ tính lương Vietourist, sheet Tham số).
    # BHXH tính trên MỨC LƯƠNG HỢP ĐỒNG (tiền lương làm căn cứ đóng), không tính trên mức lương của kỳ:
    # mức của kỳ thay đổi theo doanh thu, lấy nó làm căn cứ đóng là sai bản chất và sai cả số phải nộp.
    ("bhxh_nld", "0.105", "Bảo hiểm xã hội phần người lao động", "tỷ lệ trên lương hợp đồng", "Bộ tính lương 01/9/2026"),
    ("doan_phi_ty_le", "0.005", "Đoàn phí công đoàn – tỷ lệ trên tiền lương làm căn cứ đóng BHXH",
     "tỷ lệ", "Thỏa thuận khấu trừ đoàn phí: mức theo quy định Tổng LĐLĐ, tính trên tiền lương đóng BHXH bắt buộc"),
    ("visa_lien_minh", "300000", "Đơn giá hồ sơ visa khách liên minh", "đồng/hồ sơ", "ĐH Điều 7"),
    ("hdv_tncn", "0.10", "Khấu trừ TNCN thù lao HDV cộng tác viên", "tỷ lệ", "Bảng thuê ngoài 04-LĐTL"),
    ("gd_kd_thuong_50", "3000000", "Thưởng GĐ KD khi 50–85% NV đạt chỉ tiêu", "đồng", "Chính sách GĐ KD"),
    ("gd_kd_thuong_85", "6000000", "Thưởng GĐ KD khi ≥ 85% NV đạt chỉ tiêu", "đồng", "Chính sách GĐ KD"),
    ("so_du_tien_toi_thieu", "500000000", "Ngưỡng số dư tiền tối thiểu – cảnh báo dự báo dòng tiền 13 tuần", "đồng", "Thiết kế 3.4"),
    ("thue_gtgt", "0.10", "Thuế suất GTGT dịch vụ lữ hành (Kế toán chỉnh theo mức giảm thuế hiện hành)", "tỷ lệ", "Luật Thuế GTGT"),
    ("giam_tru_ban_than", "11000000", "Giảm trừ gia cảnh cho bản thân người nộp thuế TNCN (Kế toán chỉnh khi Nhà nước nâng mức)", "đồng/tháng", "NQ 954/2020/UBTVQH14"),
    ("giam_tru_nguoi_phu_thuoc", "4400000", "Giảm trừ gia cảnh cho mỗi người phụ thuộc (Kế toán chỉnh khi Nhà nước nâng mức)", "đồng/tháng/người", "NQ 954/2020/UBTVQH14"),
]


def get_param(db: Session, key: str, on: date | None = None) -> float:
    on = on or date.today()
    row = db.execute(select(Param).where(Param.key == key, Param.status == "active",
                                          Param.effective_from <= on)
                     .order_by(desc(Param.effective_from), desc(Param.id))).scalars().first()
    if row is None:
        for k, v, *_ in DEFAULT_PARAMS:
            if k == key:
                return float(v)
        raise KeyError(key)
    return float(row.value)


def get_param_text(db: Session, key: str, on: date | None = None) -> str:
    on = on or date.today()
    row = db.execute(select(Param).where(Param.key == key, Param.status == "active", Param.effective_from <= on)
                     .order_by(desc(Param.effective_from), desc(Param.id))).scalars().first()
    if row is None:
        for k, v, *_ in DEFAULT_PARAMS:
            if k == key: return v
        raise KeyError(key)
    return row.value


def seed_params(db: Session):
    """Nạp tham số mặc định; CSDL đã có thì chỉ bổ sung khóa mới xuất hiện trong bộ chính sách (không đè giá trị đang hiệu lực)."""
    have = {p.key for p in db.execute(select(Param)).scalars()}
    for k, v, label, unit, src in DEFAULT_PARAMS:
        if k in have: continue
        db.add(Param(key=k, value=v, label=label, unit=unit, effective_from=date(2026, 9, 1),
                     source=src, status="active", signed_chutich=True, signed_tgd=True, proposed_by="seed"))
    db.commit()


# ====================== NHẬT KÝ BẤT BIẾN ======================
def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def audit(db: Session, actor: str, role: str, action: str, entity: str, before=None, after=None):
    db.flush()  # để bản ghi audit chưa commit trong cùng giao dịch được nhìn thấy khi lấy hash cuối
    last = db.execute(select(AuditLog).order_by(desc(AuditLog.id))).scalars().first()
    prev = last.hash if last else "0" * 64
    ts = datetime.now()
    payload = _canon({"ts": ts.isoformat(), "actor": actor, "role": role, "action": action,
                      "entity": entity, "before": before, "after": after})
    h = hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()
    db.add(AuditLog(ts=ts, actor=actor, role=role, action=action, entity=entity,
                    before=before, after=after, prev_hash=prev, hash=h))


def verify_chain(db: Session) -> tuple[bool, int, str]:
    prev = "0" * 64
    n = 0
    for row in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        payload = _canon({"ts": row.ts.isoformat(), "actor": row.actor, "role": row.role, "action": row.action,
                          "entity": row.entity, "before": row.before, "after": row.after})
        h = hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()
        if row.prev_hash != prev or row.hash != h:
            return False, n, f"Chuỗi bị phá tại bản ghi #{row.id}"
        prev = h
        n += 1
    return True, n, "Chuỗi nhật ký toàn vẹn"


# ====================== DỰ TOÁN 3 CON SỐ & CỔNG BIÊN ======================
def is_doan(tour: Tour) -> bool:
    """Tour có thuộc mảng Đoàn không – dùng cho định tuyến duyệt, hạn quyết toán, và cách tính hoa hồng.

    Trước 07/9/2026 hàm này chỉ nhìn loại chuyến. Từ khi Kinh doanh tách hai phòng, "thuộc mảng nào" được
    định nghĩa một chỗ duy nhất ở app/services/segments.py (hợp của loại chuyến đoàn VÀ quy ước mã MICE).
    Nếu để hai định nghĩa song song thì sẽ có ngày một tour nằm ở màn hình phòng Đoàn nhưng lại được trả
    hoa hồng theo bậc thang của phòng Lẻ – lệch tiền chứ không chỉ lệch màn hình.

    Trên dữ liệu thật ngày 07/9/2026 hai định nghĩa cho kết quả GIỐNG HỆT nhau (115/115 tour mã MICE đều là
    doan_noi_dia), nên thay đổi này không dịch một đồng nào của kỳ lương nào; nó chỉ chặn trường hợp nhập lệch
    về sau. Muốn quay lại quy tắc cũ thì sửa đúng segments.py, không sửa riêng chỗ này."""
    from app.services import segments as SEG
    return SEG.mang_of(tour) == "doan"


BUDGET_SOURCES = {"du_toan_tour": "dự toán của chuyến", "san_pham": "cơ cấu chi phí sản phẩm (tham chiếu)", "chua_co": "chưa có dự toán"}


def calc(tour: Tour, threshold: float, fixed: float | None = None, var: float | None = None, source: str | None = None) -> dict:
    """Ba con số dự toán và cổng biên.

    THIẾU CHI PHÍ KHÔNG PHẢI LÀ CHI PHÍ BẰNG 0 (Ý kiến thẩm định 06/9/2026, B1): giá vốn 0 từng cho
    biên 100% nên cổng biên luôn báo "ĐẠT" – vô hiệu hóa cổng chặn số 1. Nay dự toán thiếu giá vốn
    có complete=False và gate_state="chua_du_co_so"; pass_gate chỉ đúng khi dự toán đủ cơ sở tính.
    """
    p, n = tour.price_per_pax, tour.planned_pax
    f = tour.fixed_cost if fixed is None else fixed
    v = tour.var_cost_per_pax if var is None else var
    if source is None:
        source = "du_toan_tour" if (f > 0 or v > 0) else "chua_co"
    revenue = p * n
    cost = f + v * n
    has_cost = f > 0 or v > 0
    margin = (revenue - cost) / revenue if revenue else 0.0
    unit = p - v
    breakeven = math.ceil(f / unit) if unit > 0 else None
    unit10 = p * (1 - threshold) - v
    pax_margin = math.ceil(f / unit10) if unit10 > 0 else None
    # Dự toán tham chiếu lấy từ cơ cấu chi phí sản phẩm KHÔNG đủ tư cách cho cổng biên: dữ liệu sản phẩm
    # hiện chỉ 21/313 mã có cơ cấu chi phí và phần lớn sai (có mã ghi 11 đ/khách → biên 99,99%). Dùng nó
    # để mở cổng thì cổng lại bị vô hiệu hóa lần nữa – chỉ hiển thị tham chiếu, cổng vẫn "chưa đủ cơ sở".
    own = source == "du_toan_tour"
    complete = all([p > 0, n > 0, has_cost, own]) and breakeven is not None
    passed = complete and margin >= threshold
    return {"revenue": revenue, "cost": cost, "profit": revenue - cost, "margin": margin,
            "breakeven_pax": breakeven, "pax_for_margin": pax_margin, "threshold": threshold,
            "fixed_cost": f, "var_cost_per_pax": v, "has_cost": has_cost,
            "budget_source": source, "budget_source_label": BUDGET_SOURCES.get(source, source),
            "reference_only": source == "san_pham",
            "pass_gate": passed, "complete": complete,
            "gate_state": "dat" if passed else ("chua_du_co_so" if not complete else "khong_dat")}


def budget_of(db: Session, t: Tour) -> tuple[float, float, str]:
    """Dự toán của chuyến và NGUỒN của nó – tách hẳn khỏi chi phí thực chi (B2).

    Trước đây dự toán của tour nhập từ Vietrip được suy ngược từ dòng quyết toán, nên biên kế hoạch
    luôn bằng biên thực tế và cảnh báo vượt dự toán không bao giờ kích hoạt. Nay: dự toán do Điều hành
    lập; nếu chuyến chưa có thì lấy cơ cấu chi phí sản phẩm làm dự toán THAM CHIẾU (ghi rõ nguồn);
    không có nữa thì trả về "chưa có dự toán", không suy ra số 0.
    """
    if t.fixed_cost > 0 or t.var_cost_per_pax > 0:
        return t.fixed_cost, t.var_cost_per_pax, "du_toan_tour"
    from app.models.core import Product
    p = None
    if t.product_id: p = db.get(Product, t.product_id)
    if p is None and t.product_code:
        p = db.execute(select(Product).where(Product.code == t.product_code)).scalars().first()
    if p is not None:
        f, v = p.fixed_cost(), p.var_cost_per_pax()
        if f > 0 or v > 0:
            return f, v, "san_pham"
    return 0.0, 0.0, "chua_co"


def calc_db(db: Session, t: Tour, threshold: float) -> dict:
    """calc() có tra cứu dự toán tham chiếu từ sản phẩm – dùng cho hiển thị, báo cáo và robot.
    Riêng bước TRÌNH dự toán vẫn dùng calc() thuần: Điều hành phải tự nhập đủ ba con số."""
    f, v, src = budget_of(db, t)
    return calc(t, threshold, f, v, src)


def booked_pax(tour: Tour) -> int:
    return sum(b.pax for b in tour.bookings if not b.cancelled)


def settlement_deadline(db: Session, tour: Tour) -> date:
    days = get_param(db, "han_qt_doan" if is_doan(tour) else "han_qt_le", tour.end_date)
    return tour.end_date + timedelta(days=int(days))


def approver_role(tour: Tour) -> str:
    """Điều 4 Văn bản đính chính: lẻ → TGĐ; đoàn → PTGĐ tour đoàn."""
    return "ptgd_doan" if is_doan(tour) else "tgd"


def settlement_summary(db: Session, tour: Tour) -> dict:
    """Số liệu quyết toán và quỹ thưởng theo mục 6.4 (chỉ tính khi đã Kế toán xác nhận)."""
    rev = tour.actual_revenue
    cost = tour.actual_cost + tour.promo_value  # ĐC Điều 3: giá trị mã KM là một dòng giá vốn nội bộ
    profit = rev - cost
    margin = profit / rev if rev else 0
    thr = get_param(db, "nguong_bien", tour.end_date)
    deadline = settlement_deadline(db, tour)
    on_time = tour.closed_at is not None and tour.closed_at.date() <= deadline
    key = {"le_noi_dia": "quy_dh_le_noi_dia", "le_nuoc_ngoai": "quy_dh_le_nuoc_ngoai", "non_package": "quy_dh_le_noi_dia"}.get(tour.tour_type, "quy_dh_doan")
    rate = get_param(db, key, tour.end_date)
    # ĐC Điều 7: tour lẻ < ngưỡng hoặc duyệt dưới biên → không quỹ; đoàn không phụ thuộc biên. Quá hạn → mất thưởng chuyến.
    eligible = on_time and (is_doan(tour) or (margin >= thr and not tour.below_margin))
    fund = profit * rate if (eligible and profit > 0) else 0
    share_nv = get_param(db, "quy_dh_chia_nv", tour.end_date)
    return {"revenue": rev, "cost": cost, "profit": profit, "margin": margin, "deadline": deadline,
            "on_time": on_time, "eligible": eligible, "fund": fund, "fund_nv": fund * share_nv,
            "fund_tp": fund * (1 - share_nv), "rate": rate}


# ====================== ROBOT CẢNH BÁO (R3/R7 thu gọn) ======================
def run_robots(db: Session) -> int:
    """Sinh cảnh báo D-7, quá hạn quyết toán, SLA booking. Chạy định kỳ; không sửa dữ liệu nghiệp vụ."""
    today = date.today()
    created = 0

    def add(kind, level, ref, msg, roles):
        nonlocal created
        exists = db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref, Alert.resolved == False)).scalars().first()
        if not exists:
            db.add(Alert(kind=kind, level=level, ref=ref, message=msg, to_roles=roles))
            created += 1

    d7 = int(get_param(db, "moc_d7"))
    for t in db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars():
        if t.tour_type == "non_package":
            if t.end_date < today: t.status = "ket_thuc"
            continue
        thr = get_param(db, "nguong_bien", t.start_date)
        c = calc_db(db, t, thr)
        days_left = (t.start_date - today).days
        if 0 <= days_left <= d7 and c["breakeven_pax"] and booked_pax(t) < c["breakeven_pax"] and not t.chairman_run_decision:
            level = "red" if days_left <= d7 - 1 else "warn"
            add("d7", level, t.code,
                f"{t.code} khởi hành {t.start_date:%d/%m}: {booked_pax(t)}/{c['breakeven_pax']} khách hòa vốn – cần ghép/dời/hủy hoặc Chủ tịch duyệt chạy",
                "tp_dh,gd_kd,tgd,chutich")
        if t.end_date < today:
            t.status = "ket_thuc"
    for t in db.execute(select(Tour).where(Tour.status == "ket_thuc", Tour.tour_type != "non_package")).scalars():
        dl = settlement_deadline(db, t)
        if today > dl:
            add("qua_han_qt", "red", t.code,
                f"{t.code} quá hạn quyết toán (hạn {dl:%d/%m}): xếp nhóm dưới 10% / hoãn thưởng tới khi chốt; người điều hành mất thưởng chuyến",
                "tp_dh,ketoan,tgd")
    for t in db.execute(select(Tour).where(Tour.status == "da_dong_so")).scalars():
        if t.closed_at and (today - t.closed_at.date()).days > int(get_param(db, "han_kt_xac_nhan")):
            add("kt_cham", "warn", t.code, f"{t.code}: Kế toán chưa xác nhận sau {get_param(db,'han_kt_xac_nhan'):.0f} ngày làm việc", "ketoan,tgd")
    try:
        from app.services import bookings as BK
        created += BK.robot_check(db)["new_alerts"]
        from app.services import sales_reports as SR
        created += SR.r9_run(db)["new_alerts"]
    except Exception as ex:   # không để lỗi R4 chặn các cảnh báo khác
        audit(db, "robot", "robot", "robot_r4_loi", "robot", after={"ly_do": str(ex)[:200]})
    sla = int(get_param(db, "sla_booking_phut"))
    for r in db.execute(select(ServiceRequest).where(ServiceRequest.booking_id == None)).scalars():
        mins = (datetime.now() - r.created_at).total_seconds() / 60
        if mins > sla:
            add("sla_booking", "warn", f"YC-{r.id}", f"Yêu cầu #{r.id} ({r.customer_name}) chưa được tạo booking sau {mins/60:.1f} giờ", "tp_dh,nv_dh")
    db.commit()
    return created


# ====================== TÍNH THU NHẬP THÁNG (bản nháp cho Robot Lương) ======================
def monthly_payroll_draft(db: Session, year: int, month: int) -> list[dict]:
    """Bản nháp: quỹ thưởng Điều hành theo chuyến đã Kế toán xác nhận trong tháng; hoa hồng đoàn theo người chốt."""
    rows = []
    tours = [t for t in db.execute(select(Tour).where(Tour.status.in_(["kt_xac_nhan", "khoa"]))).scalars()
             if t.kt_confirmed_at and t.kt_confirmed_at.year == year and t.kt_confirmed_at.month == month]
    by_op: dict[int, dict] = {}
    doan_profit_by_sales: dict[int, float] = {}
    for t in tours:
        s = settlement_summary(db, t)
        o = by_op.setdefault(t.operator_id, {"name": t.operator.full_name, "role": "nv_dh", "chuyen": 0, "fund_nv": 0.0, "fund_tp": 0.0})
        o["chuyen"] += 1
        o["fund_nv"] += s["fund_nv"]
        o["fund_tp"] += s["fund_tp"]
        if is_doan(t):
            for b in t.bookings:
                doan_profit_by_sales[b.sales_id] = doan_profit_by_sales.get(b.sales_id, 0) + s["profit"] * (b.amount / s["revenue"] if s["revenue"] else 0)
    for uid, o in by_op.items():
        rows.append({"nguoi": o["name"], "khoan": "Thưởng chuyến Điều hành (70%)", "so_chuyen": o["chuyen"], "tien": round(o["fund_nv"])})
    tp_total = sum(o["fund_tp"] for o in by_op.values())
    if tp_total:
        rows.append({"nguoi": "Trưởng phòng Điều hành", "khoan": "30% quỹ toàn phòng", "so_chuyen": len(tours), "tien": round(tp_total)})
    moc = get_param(db, "hh_doan_moc"); rate = get_param(db, "hh_doan_ty_le")
    for uid, pr in doan_profit_by_sales.items():
        u = db.get(User, uid)
        rows.append({"nguoi": u.full_name if u else uid, "khoan": f"Hoa hồng đoàn 10% × (LN − {moc:,.0f})", "so_chuyen": "", "tien": round(max(0, pr - moc) * rate)})
    return rows
