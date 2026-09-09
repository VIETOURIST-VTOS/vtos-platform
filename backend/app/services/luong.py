"""Bốn điểm lệch của Phụ lục đối chiếu đặc tả VTOS Nhân sự (Ban TGĐ, 27/8/2026), áp dụng từ 01/9/2026.

Bốn điểm này không phải tính năng thêm cho đẹp; ba trong bốn điểm là chỗ hệ thống có thể trả sai tiền
mà không ai nhìn thấy:

1. XÁC ĐỊNH MỨC LƯƠNG CỦA KỲ là một BƯỚC RIÊNG đứng trước bước tính thu nhập, không phải một khoản trừ.
   Điều 127 khoản 2 Bộ luật Lao động 2019 cấm phạt tiền và cắt lương thay xử lý kỷ luật; nếu mô hình hoá
   phần chênh do doanh thu dưới mốc thành một dòng trừ vào lương thì về hình thức đó là cắt lương. Vì vậy
   hàm ở đây trả về CHÍNH mức lương của kỳ kèm căn cứ, và không sinh dòng trừ nào.

2. CHẾ ĐỘ CÔNG LÀ THUỘC TÍNH CỦA BỘ PHẬN, không phải một luồng dùng chung. Năm phòng đã chấm dứt chấm
   công theo ngày từ 01/9/2026; nếu vẫn để một luồng chung thì mọi kỳ lương đều hiện cảnh báo thiếu công
   và người dùng sẽ học cách bỏ qua cảnh báo – cách nhanh nhất làm hỏng một hệ thống kiểm soát.

3. CỬA SỔ BA THÁNG TRƯỢT của Phòng Đoàn phải ghi lại ba kỳ nguồn và giá trị từng kỳ tại thời điểm tính,
   để sau này giải thích lại được con số đã trả. Người chưa đủ ba tháng thì chia cho số tháng thực có.

4. HOA HỒNG QUÁ HẠN QUYẾT TOÁN LÀ TREO, KHÔNG PHẢI CẮT. Đây là chỗ dễ làm mất tiền của người lao động
   nhất mà không ai phát hiện, vì khoản treo không hiện trên phiếu lương nào. Báo cáo dưới đây dựng khoản
   treo bằng cách SUY TỪ tour chưa quyết toán, nên về mặt cấu trúc không có đường nào làm nó hết hiệu lực
   theo thời gian: chừng nào tour chưa chốt thì khoản còn nằm đó, chốt xong thì kỳ lương tương ứng trả đủ.
"""
import math
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.core import Tour, User
from app.models.hr import Employee, GuideAssignment, PayrollRun
from app.services import rules as R

# ---------------------------------------------------------------- chế độ công
CHAM_CONG, BAO_CAO_NGAY, THEO_CHUYEN, LUONG_CTP = "cham_cong", "bao_cao_ngay", "theo_chuyen", "luong_cong_tac_phi"

CHE_DO_CONG = {
    "ketoan": CHAM_CONG, "hcns": CHAM_CONG,
    "kd_le": BAO_CAO_NGAY, "kd_doan": BAO_CAO_NGAY, "dieu_hanh": BAO_CAO_NGAY,
    "marketing": BAO_CAO_NGAY, "cntt": BAO_CAO_NGAY, "visa": BAO_CAO_NGAY, "ban_tgd": BAO_CAO_NGAY,
    "huong_dan": THEO_CHUYEN,
    "doi_xe": LUONG_CTP,
}
CHE_DO_LABEL = {
    CHAM_CONG: "Chấm công theo ngày",
    BAO_CAO_NGAY: "Báo cáo công việc trước 20 giờ (Điều 12) – không có mẫu số công chuẩn",
    THEO_CHUYEN: "Thù lao theo từng chuyến dẫn",
    LUONG_CTP: "Lương cơ bản đủ tháng cộng công tác phí theo ngày đi tour",
}


def che_do_cong(e: Employee) -> str:
    return CHE_DO_CONG.get(e.department, BAO_CAO_NGAY)


# ------------------------------------------------- bước xác định mức lương kỳ
def xac_dinh_thang_doanh_thu(e: Employee, doanh_thu: float, moc: float, cut: float, chuyen_chua_quyet_toan: int = 0) -> dict:
    """Phụ lục C – Kinh doanh Lẻ: mỗi 10% mốc doanh thu thiếu thì lương giảm một cấp, tới 0.

    Trả về MỨC LƯƠNG của kỳ, kèm căn cứ. Phần chênh so với mức hợp đồng KHÔNG được xuất hiện ở bất cứ đâu
    dưới dạng khoản trừ của người lao động (tiêu chí VT02).
    """
    step = moc * 0.10
    cap = 0 if doanh_thu >= moc else min(10, math.ceil((moc - doanh_thu) / step)) if step else 0
    muc = max(0.0, (e.base_salary or 0) - cap * cut) if cap else (e.base_salary or 0)
    # Doanh thu tính chỉ tiêu chỉ đếm chuyến Kế toán ĐÃ xác nhận quyết toán. Người còn chuyến chưa chốt thì
    # con số 0 ở đây KHÔNG có nghĩa là bán được 0 đồng, mà là chưa đủ cơ sở tính – hai chuyện khác hẳn nhau,
    # và cái sau mà trả ra lương 0 thì là trả sai. Hệ thống nói rõ chỗ nó chưa biết thay vì im lặng.
    chua_du = chuyen_chua_quyet_toan > 0 and doanh_thu <= 0
    return {"che_do": "thang_doanh_thu", "muc_hop_dong": (e.base_salary or 0), "muc_ky": round(muc),
            "cap": cap, "moc": moc, "can_cu": {"doanh_thu_tinh_chi_tieu": round(doanh_thu),
                                               "chuyen_chua_quyet_toan": chuyen_chua_quyet_toan},
            "chua_du_co_so": chua_du,
            "giai_thich": (f"CHƯA ĐỦ CƠ SỞ TÍNH: còn {chuyen_chua_quyet_toan} chuyến chưa chốt quyết toán nên doanh thu "
                           f"tính chỉ tiêu chưa xác định được. Không được hiểu là doanh thu bằng 0 – Kế toán phải chốt "
                           f"quyết toán trước khi trình ký kỳ lương này" if chua_du else
                           f"Đạt mốc {moc:,.0f} – hưởng đủ mức hợp đồng" if cap == 0 else
                           f"Doanh thu {doanh_thu:,.0f} dưới mốc {moc:,.0f} → cấp {cap} Phụ lục C, "
                           f"mức lương của kỳ {muc:,.0f} (đây là mức lương, không phải khoản trừ)")}


def binh_quan_ba_thang(e: Employee, lich_su: list[dict]) -> dict:
    """Điều 5 Phòng Đoàn: bình quân lợi nhuận quyết toán ba tháng gần nhất.

    lich_su là danh sách {"ky": "2026-07", "loi_nhuan": …} theo thứ tự từ xa tới gần. Người vào làm chưa
    đủ ba tháng thì chia cho SỐ THÁNG THỰC CÓ, không chia cho ba – chia cho ba là tự dựng thêm những
    tháng không tồn tại với lợi nhuận bằng 0 và ép người mới xuống bậc thấp nhất.
    """
    n = len(lich_su)
    tong = sum(x["loi_nhuan"] for x in lich_su)
    return {"binh_quan": round(tong / n) if n else 0.0, "so_ky": n, "lookback": lich_su}


def xac_dinh_thang_loi_nhuan(e: Employee, lich_su: list[dict], moc: float, thang: list[tuple[float, float]]) -> dict:
    bq = binh_quan_ba_thang(e, lich_su)
    ty_le_moc = bq["binh_quan"] / moc if moc else 0
    bac_i, he_so = 0, 0.0
    for i, (nguong, hs) in enumerate(thang):
        if ty_le_moc >= nguong: bac_i, he_so = i, hs
    bac = "Đạt" if he_so >= 1 else f"f{bac_i}"
    muc = round((e.base_salary or 0) * he_so)
    return {"che_do": "thang_loi_nhuan", "muc_hop_dong": e.base_salary, "muc_ky": muc, "bac": bac,
            "ty_le": he_so, "moc": moc, "can_cu": {"binh_quan_3_thang": bq["binh_quan"], "so_ky_lay_binh_quan": bq["so_ky"]},
            "lookback_inputs": bq["lookback"], "snapshot_at": datetime.now().isoformat(timespec="seconds"),
            "giai_thich": (f"Bình quân lợi nhuận quyết toán {bq['so_ky']} kỳ = {bq['binh_quan']:,.0f} "
                           f"({ty_le_moc*100:.0f}% chỉ tiêu {moc:,.0f}) → bậc {bac}, {he_so*100:.0f}% mức hợp đồng")}


def xac_dinh_theo_cong(e: Employee, cong_chuan: float, cong_thuc_te: float | None) -> dict:
    """Kế toán và Nhân sự Hành chính – hai bộ phận duy nhất còn chấm công theo ngày."""
    if cong_thuc_te is None:
        return {"che_do": "cham_cong", "muc_hop_dong": (e.base_salary or 0), "muc_ky": round((e.base_salary or 0)),
                "can_cu": {"cong_chuan": cong_chuan, "cong_thuc_te": None}, "thieu_du_lieu": True,
                "giai_thich": f"CHƯA NHẬP CÔNG THỰC TẾ – tạm lấy đủ tháng {e.base_salary:,.0f}, HCNS phải nhập trước khi trình ký"}
    muc = (e.base_salary or 0) / cong_chuan * cong_thuc_te if cong_chuan else 0
    return {"che_do": "cham_cong", "muc_hop_dong": (e.base_salary or 0), "muc_ky": round(muc),
            "can_cu": {"cong_chuan": cong_chuan, "cong_thuc_te": cong_thuc_te},
            "giai_thich": f"{cong_thuc_te}/{cong_chuan} công × {(e.base_salary or 0):,.0f}"}


def xac_dinh_co_dinh(e: Employee, ly_do: str = "") -> dict:
    return {"che_do": "co_dinh", "muc_hop_dong": (e.base_salary or 0), "muc_ky": round((e.base_salary or 0)),
            "can_cu": {}, "giai_thich": ly_do or "Lương cơ bản cố định theo hợp đồng"}


def kiem_tra_khong_phai_khoan_tru(row: dict) -> list[str]:
    """Tiêu chí VT02: phần chênh giữa mức hợp đồng và mức của kỳ không được xuất hiện dưới dạng dòng trừ.

    Đây là ràng buộc pháp lý nên kiểm ở tầng dữ liệu, không phải tầng giao diện: một dòng khoản âm mà lý
    do gắn với việc xếp bậc theo doanh thu / lợi nhuận là hành vi cắt lương thay xử lý kỷ luật.
    """
    tu_khoa = ("phụ lục c", "thang giảm", "dưới mốc", "xếp bậc", "bình quân", "không đạt chỉ tiêu")
    loi = []
    for k in row.get("khoan", []):
        if k.get("tien", 0) < 0 and any(t in (k.get("ten", "") + k.get("ghi_chu", "")).lower() for t in tu_khoa):
            loi.append(f"{row.get('ma')}: dòng trừ '{k.get('ten')}' bắt nguồn từ xếp bậc – vi phạm Điều 127.2 BLLĐ")
    return loi


# ------------------------------------------------------------ khoản treo
def khoan_treo(db: Session, den_ngay: date | None = None) -> dict:
    """Hoa hồng và thưởng chuyến đang TREO vì chuyến đã kết thúc nhưng chưa chốt quyết toán.

    Dựng bằng cách suy từ tour chưa quyết toán chứ không lưu thành bản ghi có hạn, nên không tồn tại
    đường nào làm khoản treo hết hiệu lực theo thời gian: chuyến còn chưa chốt thì khoản còn nằm đây,
    chốt xong là kỳ lương của tháng chốt trả đủ.
    """
    hom_nay = den_ngay or date.today()
    emps = {e.user_id: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars() if e.user_id}
    rows = []
    for t in db.execute(select(Tour).where(Tour.end_date <= hom_nay)).scalars():
        if t.status in ("kt_xac_nhan", "khoa"):
            continue                                  # đã chốt – hoa hồng đã hoặc sẽ vào kỳ lương của tháng chốt
        han = R.settlement_deadline(db, t)
        qua_han = (hom_nay - han).days
        # Phân biệt hai tình huống rất khác nhau về việc phải làm:
        #  - "chờ chốt": bảng quyết toán đã có đủ số thu–chi trong hệ thống, chỉ còn thiếu người bấm chốt;
        #  - "chưa có số": chưa ai lập bảng quyết toán.
        # Gộp hai cái này lại thì Kế toán không biết bắt đầu từ đâu trong hàng trăm chuyến.
        co_so = bool(t.actual_revenue or t.actual_cost)
        buoc = "Đã có bảng quyết toán – chờ chốt" if co_so else "Chưa có bảng quyết toán"
        nguoi = {}
        for b in t.bookings:
            e = emps.get(b.sales_id)
            if e is None: continue
            g = nguoi.setdefault(e.id, {"ma": e.code, "ten": e.full_name, "phong": e.department, "doanh_thu": 0.0, "so_booking": 0})
            g["doanh_thu"] += (b.amount or 0) - (b.discount or 0); g["so_booking"] += 1
        dh = emps.get(t.operator_id)
        for g in nguoi.values():
            rows.append({"tour_code": t.code, "tour_name": t.name, "ket_thuc": t.end_date, "han_quyet_toan": han,
                         "qua_han_ngay": max(0, qua_han), "vai_tro": "Kinh doanh", **g,
                         "co_so_quyet_toan": co_so, "buoc_tiep_theo": buoc,
                         "trang_thai": "treo", "ly_do": "Chuyến chưa chốt quyết toán – hoa hồng chưa phát sinh, KHÔNG bị cắt"})
        if dh is not None:
            rows.append({"tour_code": t.code, "tour_name": t.name, "ket_thuc": t.end_date, "han_quyet_toan": han,
                         "qua_han_ngay": max(0, qua_han), "vai_tro": "Điều hành", "ma": dh.code, "ten": dh.full_name,
                         "phong": dh.department, "doanh_thu": 0.0, "so_booking": 0, "trang_thai": "treo",
                         "co_so_quyet_toan": co_so, "buoc_tiep_theo": buoc,
                         "ly_do": "Thưởng chuyến chưa phát sinh – chờ quyết toán"})
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.status == "da_xac_nhan")).scalars():
        if a.report_submitted and a.advance_settled: continue
        t = db.get(Tour, a.tour_id)
        if t is None or t.end_date > hom_nay: continue
        e = db.get(Employee, a.guide_id)
        if e is None: continue
        thieu = [x for x, ok in (("báo cáo tour", a.report_submitted), ("hoàn ứng", a.advance_settled)) if not ok]
        rows.append({"tour_code": t.code, "tour_name": t.name, "ket_thuc": t.end_date,
                     "han_quyet_toan": R.settlement_deadline(db, t), "qua_han_ngay": max(0, (hom_nay - R.settlement_deadline(db, t)).days),
                     "vai_tro": "Hướng dẫn viên", "ma": e.code, "ten": e.full_name, "phong": e.department,
                     "so_tien": round(a.rate_per_day * a.days * (2 if a.holiday else 1)), "doanh_thu": 0.0, "so_booking": 0,
                     "trang_thai": "treo", "ly_do": "Thiếu " + " và ".join(thieu)})
    rows.sort(key=lambda r: (-r["qua_han_ngay"], r["ma"]))
    theo_nguoi = {}
    for r in rows:
        g = theo_nguoi.setdefault(r["ma"], {"ma": r["ma"], "ten": r["ten"], "phong": r["phong"], "so_chuyen": 0, "qua_han": 0})
        g["so_chuyen"] += 1
        if r["qua_han_ngay"] > 0: g["qua_han"] += 1
    cho_chot = {r["tour_code"] for r in rows if r.get("co_so_quyet_toan")}
    chua_co_so = {r["tour_code"] for r in rows if not r.get("co_so_quyet_toan")}
    return {"rows": rows, "theo_nguoi": sorted(theo_nguoi.values(), key=lambda x: -x["so_chuyen"]),
            "tong_chuyen": len({r["tour_code"] for r in rows}), "tong_dong": len(rows),
            "cho_chot": len(cho_chot), "chua_co_bang_quyet_toan": len(chua_co_so),
            "viec_can_lam": (f"{len(cho_chot)} chuyến đã có bảng quyết toán với đủ số thu–chi, chỉ còn thiếu thao tác chốt "
                             f"trên Vietrip; {len(chua_co_so)} chuyến chưa có bảng quyết toán."),
            "ghi_chu": "Khoản treo là cơ chế HOÃN, không phải cắt: chốt quyết toán xong thì kỳ lương tương ứng trả đủ. "
                       "Danh sách này suy từ chuyến chưa chốt nên không có cách nào làm khoản treo hết hiệu lực theo thời gian."}


# --------------------------------------------------- chặn chạy kỳ lương
def xung_dot_ho_so(db: Session) -> list[dict]:
    """Xung đột hồ sơ phải xử lý TRƯỚC khi chạy kỳ lương (Phần IV Phụ lục: xung đột mã 294).

    Một mã dùng cho hai người, hay một tài khoản gắn hai hồ sơ, nghĩa là hệ thống không biết trả tiền cho
    ai. Trường hợp mã 294 trong phụ lục là mức lương giảm 14 triệu có thể rơi vào hồ sơ người khác. Ở tình
    huống đó hệ thống phải DỪNG và nói ra, không được tự chọn dòng đầu tiên.
    """
    ds = list(db.execute(select(Employee).where(Employee.active == True)).scalars())
    loi = []
    theo_ma, theo_user = {}, {}
    for e in ds:
        theo_ma.setdefault(e.code, []).append(e)
        if e.user_id: theo_user.setdefault(e.user_id, []).append(e)
    for ma, nhom in theo_ma.items():
        if len(nhom) > 1:
            loi.append({"loai": "trung_ma", "ma": ma, "ho_so": [x.full_name for x in nhom],
                        "thong_diep": f"Mã {ma} đang dùng cho {len(nhom)} người: {', '.join(x.full_name for x in nhom)}"})
    for uid, nhom in theo_user.items():
        if len(nhom) > 1:
            u = db.get(User, uid)
            loi.append({"loai": "trung_tai_khoan", "tai_khoan": u.username if u else str(uid),
                        "ho_so": [f"{x.code} {x.full_name}" for x in nhom],
                        "thong_diep": f"Tài khoản {u.username if u else uid} gắn với {len(nhom)} hồ sơ: {', '.join(x.code + ' ' + x.full_name for x in nhom)}"})
    for e in ds:
        if not e.user_id: continue
        u = db.get(User, e.user_id)
        if u and u.staff_code and u.staff_code != e.code:
            loi.append({"loai": "lech_ma", "ma": e.code, "tai_khoan": u.username,
                        "thong_diep": f"Hồ sơ {e.code} {e.full_name} gắn tài khoản {u.username} mang mã nhân viên {u.staff_code}"})
    return loi


# --------------------------------------------------------- lưu trữ 10 năm
NAM_LUU_TRU_TOI_THIEU = 10


def duoc_xoa_bang_luong(period: str, hom_nay: date | None = None) -> tuple[bool, str]:
    """Bảng lương là chứng từ kế toán: Nghị định 174/2016 hướng dẫn Luật Kế toán 2015 buộc lưu tối thiểu
    mười năm. Sàn cài sẵn để chủ nghiệp vụ chỉ nới dài được, không hạ xuống."""
    hom_nay = hom_nay or date.today()
    y, m = map(int, period.split("-"))
    tuoi = (hom_nay.year - y) * 12 + (hom_nay.month - m)
    if tuoi < NAM_LUU_TRU_TOI_THIEU * 12:
        return False, (f"Bảng lương kỳ {period} mới {tuoi // 12} năm {tuoi % 12} tháng. Chứng từ kế toán phải lưu tối "
                       f"thiểu {NAM_LUU_TRU_TOI_THIEU} năm theo Nghị định 174/2016 hướng dẫn Luật Kế toán 2015 – không xóa được.")
    return True, ""
