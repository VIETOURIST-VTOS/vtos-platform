"""Dashboard theo cấp (HĐQT / BĐH / phòng ban – mục 11 MHQT) và robot R7 báo cáo tự động (ngày / tuần / tháng) kèm nhận xét."""
import json, os
from datetime import date, datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session, selectinload
from app.models.core import Tour, Booking, ServiceRequest, Alert, Param, User
from app.models.payments import BankTransaction, Receipt
from app.models.accounting import JournalEntry, Invoice
from app.models.ops import PaymentRequest, DailyReport, PageShift
from app.models.hr import PayrollRun, Employee, VehicleRate
from app.models.finance import FinSchedule
from app.models.reports_auto import AutoReport
from app.services import rules as R
from app.services import reports as RP
from app.services import finance as FIN
from app.services import ops as OPS
from app.core.config import settings

# Khối 04a Điều hành trên màn hình 01 — CỬA SỔ NGÀY KHỞI HÀNH.
#
# Anh Tuấn chốt 14/9/2026: lấy theo BẢN VẼ V1.4, tức 14 ngày. Trước đó máy chủ lọc 21 ngày, còn bản
# vẽ ghi 14 — màn hình phải in cả hai con số ra để không ai đọc nhầm, mà in cả hai thì chẳng ai biết
# tin con nào. Nay một con số.
#
# Để ở đây, KHÔNG rải trong câu truy vấn: số ngày này là một quyết định nghiệp vụ, và chỗ nào cần
# nó thì đọc từ đây. Màn hình cũng đọc con số này qua `sap_khoi_hanh_so_ngay` chứ không gõ lại.
SO_NGAY_SAP_KHOI_HANH = 14


def _month_tours(db: Session, y: int, m: int) -> list[Tour]:
    """Chuyến Kế toán xác nhận trong THÁNG y-m. Lọc mốc thời gian ngay trong SQL: bản cũ nạp toàn bộ
    chuyến đã xác nhận (hàng nghìn chuyến, kèm booking nạp lười theo sau) rồi mới bỏ đi hầu hết."""
    dau = datetime(y, m, 1)
    cuoi = datetime(y + (m == 12), 1 if m == 12 else m + 1, 1)
    # selectinload: các bảng phía dưới duyệt t.bookings của từng chuyến. Không nạp sẵn thì mỗi chuyến
    # là một câu truy vấn riêng – vài trăm chuyến thành vài trăm chuyến đi–về tới Singapore.
    return list(db.execute(select(Tour).options(selectinload(Tour.bookings))
                           .where(Tour.status.in_(["kt_xac_nhan", "khoa"]),
                                  Tour.kt_confirmed_at >= dau, Tour.kt_confirmed_at < cuoi)).scalars())


def doanh_thu_phong(db: Session, today: date) -> dict:
    """TC-98 · Doanh thu PKD Lẻ và PKD Đoàn: tháng này và lũy kế năm đến hôm nay.

    Đọc qua ĐÚNG `ket_qua_that.thang` mà khối Doanh thu ở đầu màn hình dùng, nên tổng hai phòng
    (cộng phần "khác") khớp con số doanh thu tháng/năm ở trên — không có công thức thứ hai.
    Tháng chưa có chuyến nào đủ số thì phòng ấy là 0 đồng, 0 chuyến."""
    from app.services import ket_qua_that as KQT
    nho: dict = {}
    ky_nay = f"{today:%Y-%m}"
    ra = {"ky": ky_nay, "nam": today.year}
    thang_nay = KQT.thang(db, ky_nay, nho=nho)["theo_mang"]
    luy_ke = {m: {"doanh_thu": 0.0, "chuyen": 0} for m in KQT.NGAN}
    for mth in range(1, today.month + 1):
        tm = KQT.thang(db, f"{today.year:04d}-{mth:02d}", nho=nho)["theo_mang"]
        for m in luy_ke:
            luy_ke[m]["doanh_thu"] += tm[m]["doanh_thu"]
            luy_ke[m]["chuyen"] += tm[m]["chuyen"]
    # 07/10/2026 — IN RA CẢ NĂM NGĂN, không chỉ hai. Trước bản này màn hình chỉ in `le` và `doan`
    # trong khi con số doanh thu ở đầu màn hình cộng đủ mọi chuyến, nên phần chênh không có tên và
    # không ai cộng ngược lại được. Hợp đồng thuê xe làm phần chênh ấy to lên và có thật, nên nó
    # phải đứng thành một dòng — đúng lời Chủ tịch dặn: không chạy lẫn vào doanh thu tour.
    for m in KQT.NGAN:
        ra[m] = {"thang": thang_nay[m]["doanh_thu"], "chuyen_thang": thang_nay[m]["chuyen"],
                 "nam": luy_ke[m]["doanh_thu"], "chuyen_nam": luy_ke[m]["chuyen"]}
    return ra


def build(db: Session, u: User) -> dict:
    """Số liệu dashboard theo vai trò – chỉ đọc, tính từ dữ liệu hiện có."""
    today = date.today(); p = f"{today:%Y-%m}"
    role = u.role
    out: dict = {"role": role, "as_of": datetime.now(), "approvals": [], "kpis": {}, "sections": {}}
    # KS-NHANH bước 2 (07/11/2026): đo từng khối để tìm khối ăn 38 giây trên crm thật. Chỉ ghi số
    # mili-giây vào `do_ms`, không đổi phép tính nào.
    import time as _t
    _m = {"_": _t.time()}; _do = out["do_ms"] = {}
    def _cham(ten):
        now = _t.time(); _do[ten] = int((now - _m["_"]) * 1000); _m["_"] = now
    # --- việc chờ duyệt của tôi (mọi phân hệ) ---
    ap = out["approvals"]
    if role in ("chutich", "tgd"):
        n = db.execute(select(func.count()).select_from(Param).where(Param.status == "pending")).scalar()
        if n: ap.append({"label": f"{n} tham số chính sách chờ ký", "href": "/params"})
        n = db.execute(select(func.count()).select_from(VehicleRate).where(VehicleRate.status == "pending")).scalar()
        if n: ap.append({"label": f"{n} giá xe chờ ký", "href": "/hr"})
        # ═══════════════════════════════════════════════════════════════════════════════════
        # HÀNG ĐỢI CHỜ DUYỆT — phải TRÙNG KHÍT với người thật sự bấm được (Đợt F1)
        # ═══════════════════════════════════════════════════════════════════════════════════
        #
        # Hai dòng cũ ở đây lọc `two_signatures == True` cho Chủ tịch, tức CHỈ khoản ngoài dự toán.
        # Một khoản 300 triệu trong dự toán không hiện ra ở đâu trên bàn ông, trong khi theo luật
        # mốc tiền nó là khoản ông phải duyệt. Nên chỗ này hỏi `OPS.cap_duyet` — ĐÚNG hàm mà bước
        # duyệt hỏi — chứ không tự suy từ một cờ. Hai chỗ suy riêng là hình của lỗi 13/9 và 10/10.
        #
        # ĐỔI MỘT CÂU ĐẾM THÀNH MỘT LƯỢT ĐỌC: `cap_duyet` cần `amount` và cột mốc của TỪNG hồ sơ,
        # không viết được thành một câu `count`. Tập đọc là hồ sơ ĐANG chờ duyệt — vài chục dòng,
        # không phải cả bảng.
        #
        # MARKETING ĐỨNG NGOÀI CẢ HAI Ô: do P.TGĐ Marketing duyệt một chữ ký (23/9/2026).
        _cho = db.execute(select(PaymentRequest).where(
            PaymentRequest.status == "cho_duyet",
            PaymentRequest.category != "marketing")).scalars().all()
        _cd = [(p, OPS.cap_duyet(db, p)) for p in _cho]
        _cua_toi = "can_chutich" if role == "chutich" else "can_tgd"
        n = sum(1 for p, c in _cd if c[_cua_toi])
        if n: ap.append({"label": f"{n} đề nghị chi chờ " + ("CHỦ TỊCH ký" if role == "chutich"
                                                            else "TGĐ duyệt"), "href": "/expenses"})
        # CẢ HAI VẪN THẤY CẢ HAI PHÍA CỦA MỐC — Chủ tịch chốt 10/10/2026, hai câu liền nhau:
        # "dưới 100 triệu TGĐ duyệt nhưng Chủ tịch vẫn phải thấy", và "trên 100 triệu TGĐ cũng vẫn
        # thấy, nhưng không bấm duyệt". Mốc chia QUYỀN BẤM, không chia TẦM NHÌN.
        #
        # Bản đầu của đợt này lọc hẳn phía bên kia mốc khỏi bàn mỗi người, và đó là đổi một chỗ
        # hỏng thành chỗ hỏng ngược lại: trước thì Chủ tịch không thấy khoản LỚN, sau thì không
        # thấy khoản NHỎ.
        #
        # PHẢI LÀ MỘT DÒNG RIÊNG, và câu chữ nói rõ ĐỂ XEM chứ không phải để bấm. Gộp vào ô trên
        # thì con số ấy thành một việc đang chờ chính người đọc — họ bấm vào, không ký được khoản
        # nào, và lần sau không ai tin con số trên bàn mình nữa. Cùng cách Marketing đã làm
        # 23/9/2026: dữ liệu vẫn đẩy lên TGĐ và Chủ tịch, nhưng để XEM, không phải để bấm.
        nx = sum(1 for p, c in _cd if not c[_cua_toi] and not c["chua_chot"])
        if nx:
            _ben = ("dưới mốc, TGĐ duyệt" if role == "chutich" else "từ mốc trở lên, Chủ tịch ký")
            ap.append({"label": f"{nx} đề nghị chi {_ben} — để xem, không phải để bấm",
                       "href": "/expenses"})
        # Hồ sơ ĐỨNG CHỜ vì chưa chốt mốc: đếm RIÊNG và trỏ sang màn hình Tham số. Lọc chúng ra
        # khỏi ô trên mà không nói gì là làm một đống việc tắc nghẽn trở thành vô hình — đúng kiểu
        # hỏng im lặng mà M5 của Marketing đã phải dựng một cái miệng để chống.
        nk = sum(1 for p, c in _cd if c["chua_chot"])
        if nk: ap.append({"label": f"{nk} đề nghị chi KHÔNG DUYỆT ĐƯỢC: chưa chốt ngưỡng duyệt chi",
                          "href": "/params"})
        n = sum(1 for t in db.execute(select(Tour).where(Tour.status == "cho_duyet")).scalars())
        if n: ap.append({"label": f"{n} dự toán tour chờ duyệt", "href": "/tours"})
        # ĐỢT E6 13/10/2026 — hai dòng, và chúng nói hai việc KHÁC NHAU.
        #
        # Dòng thứ nhất là việc chờ anh bấm. Dòng thứ hai KHÔNG chờ ai bấm — nó là một kỳ đang
        # mở mà chưa ai khóa lại, và nó phải nằm đây cho tới lúc có người khóa. Một kỳ mở mà ai
        # cũng quên là chỗ số liệu lặng lẽ đổi sau lưng; để nó im lặng thì đúng ba tuần sau không
        # ai nhớ vì sao sổ tháng ấy khác bản đã in.
        from app.services import mo_lai_ky as _MLK
        _cho = _MLK.dang_cho_ky(db)
        if _cho:
            ap.append({"label": f"{len(_cho)} kỳ kế toán chờ CHỦ TỊCH ký mở lại — kỳ "
                                + ", ".join(d.period for d in _cho), "href": "/accounting?tab=periods"})
        _mo = _MLK.dang_mo_lai(db)
        if _mo:
            ap.append({"label": "ĐANG MỞ LẠI, chưa khóa lại: kỳ "
                                + ", ".join(d.period for d in _mo)
                                + " — ghi xong thì khóa lại", "href": "/accounting?tab=periods"})
        # ĐỢT E12 13/10/2026 — BẢNG KÝ QUYỀN. Chủ tịch chốt chỗ đặt: nối vào hàng việc chờ quyết,
        # bấm vào XỔ RA chi tiết ngay tại chỗ.
        #
        # Dòng này KHÔNG phải một việc chờ bấm, và đó là lý do nó mang theo `chi_tiet` thay vì một
        # đường dẫn: nó là một điều cần ĐỌC LẠI. Dẫn sang một màn hình riêng thì phải mở một khoá
        # menu mới — tức xin thêm quyền cho một loạt vai mà chưa ai ký, đúng cái việc bảng này
        # sinh ra để canh.
        #
        # ĐẾM LẠI mỗi lần đọc, không chép con số đã đo: chép thì con số đóng băng ở ngày đo còn
        # cửa thì mỗi đợt lại thêm, và một con số cũ trông y hệt một con số đúng.
        from app.services import bang_ky_cua as _BKC
        ap += _BKC.dong_ban_lam_viec()
    if role == "tgd":
        r = db.execute(select(PayrollRun).where(PayrollRun.status == "hcns_lap")).scalars().first()
        if r: ap.append({"label": f"Bảng lương {r.period} chờ TGĐ ký lô", "href": "/hr"})
    # ĐỢT R4b-2c — `ketoan_truong` ĐƯỢC THÊM VÀO ĐÚNG MỘT CHỖ: khối này.
    #
    # Vai ấy đã có `books.READ` (Chủ tịch ký 23/10/2026) và đã có màn hình `/hoa-don-thieu`
    # qua phép suy `ketoan` → `ketoan_truong` của Đợt LG1. Đây chỉ là CHỖ ĐỌC con số, không
    # mở thêm cửa nào. Các dòng khác trong khối vẫn trỏ tới màn hình mà vai ấy vốn đã mở được.
    if role in ("ketoan", "ketoan_truong"):
        n = db.execute(select(func.count()).select_from(BankTransaction).where(BankTransaction.match_status == "cho_ke_toan")).scalar()
        if n: ap.append({"label": f"{n} giao dịch SePay chờ khớp", "href": "/collections"})
        n = db.execute(select(func.count()).select_from(Receipt).where(Receipt.status == "tu_dong")).scalar()
        if n: ap.append({"label": f"{n} phiếu thu robot chờ xác nhận", "href": "/collections"})
        n = db.execute(select(func.count()).select_from(PaymentRequest).where(PaymentRequest.status.in_(["cho_kt", "cho_chi"]))).scalar()
        if n: ap.append({"label": f"{n} đề nghị chi chờ Kế toán kiểm tra / chi", "href": "/expenses"})
        n = db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.status == "nhap")).scalar()
        if n: ap.append({"label": f"{n} chứng từ nháp chờ ghi sổ", "href": "/accounting"})
        n = sum(1 for t in db.execute(select(Tour).where(Tour.status == "da_dong_so")).scalars())
        if n: ap.append({"label": f"{n} quyết toán tour chờ Kế toán xác nhận (3 ngày)", "href": "/tours"})
        r = db.execute(select(PayrollRun).where(PayrollRun.status == "nhap")).scalars().first()
        if r: ap.append({"label": f"Bảng lương {r.period} chờ xác nhận cơ sở", "href": "/hr"})
        # ĐỢT R4b-2c 23/10/2026 — HÓA ĐƠN CÒN THIẾU.
        #
        # Dòng này KHÔNG phải một việc chờ ai bấm duyệt — nó là một đống việc đang tồn. Đặt ở đây
        # vì bàn làm việc là chỗ duy nhất người ta mở mỗi ngày; để nó chỉ nằm trong màn hình riêng
        # thì ai không mở màn hình ấy sẽ không bao giờ biết còn bao nhiêu hóa đơn chưa về.
        #
        # KHÔNG CHẶN KHÓA KỲ — Chủ tịch chốt 22/10/2026. Thiếu hóa đơn chỉ ĐẾM.
        #
        # Gọi `dem_hoa_don_thieu` chứ KHÔNG gọi `hoa_don_thieu`: hàm kia dựng cả danh sách và đọc
        # tài khoản đối ứng, quá đắt cho một ô mở mỗi lần vào trang chủ.
        from app.services import books as _BK
        _hd = _BK.dem_hoa_don_thieu(db, date(today.year, today.month, 1), today)
        if _hd["chua_nhan"]:
            ap.append({"label": f"{_hd['chua_nhan']} dòng chưa nhận được hóa đơn "
                                 f"(thuế GTGT {_fmt(_hd['thue'])} đ) — KHÔNG CHẶN KHÓA KỲ",
                       "href": "/hoa-don-thieu"})
    if role == "hcns":
        r = db.execute(select(PayrollRun).where(PayrollRun.status == "kt_xac_nhan")).scalars().first()
        if r: ap.append({"label": f"Bảng lương {r.period} chờ HCNS lập", "href": "/hr"})
        n = db.execute(select(func.count()).select_from(Alert).where(Alert.kind == "bc_ngay_2", Alert.resolved == False)).scalar()
        if n: ap.append({"label": f"{n} nhân sự thiếu báo cáo 2 ngày liên tiếp", "href": "/reports"})
    if role in ("tp_dh", "ptgd_mkt", "gd_kd", "tp_kd", "tn_kd"):
        conf = [k for k, v in OPS.CATEGORY_CONFIRMER.items() if role in v]
        n = db.execute(select(func.count()).select_from(PaymentRequest).where(PaymentRequest.status == "cho_tp", PaymentRequest.category.in_(conf))).scalar()
        if n: ap.append({"label": f"{n} đề nghị chi chờ bộ phận xác nhận", "href": "/expenses"})
    if role in ("tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "ptgd_mkt", "hcns"):
        n = sum(1 for r in db.execute(select(DailyReport).where(DailyReport.reviewed_by == "")).scalars())
        if n: ap.append({"label": f"{n} báo cáo ngày chưa chấm", "href": "/reports"})
    if role == "cntt":
        n = sum(1 for t in db.execute(select(Tour).where(Tour.status == "kt_xac_nhan")).scalars())
        if n: ap.append({"label": f"{n} quyết toán chờ CNTT đối chiếu & khóa", "href": "/tours"})
    if role == "nv_dh":
        n = db.execute(select(func.count()).select_from(ServiceRequest).where(ServiceRequest.booking_id == None)).scalar()
        if n: ap.append({"label": f"{n} yêu cầu chờ tạo booking (≤ 2 giờ)", "href": "/requests"})

    _cham("viec_cho_duyet")
    # --- KPI theo cấp ---
    k = out["kpis"]
    tours_m = _month_tours(db, today.year, today.month)
    sett = [R.settlement_summary(db, t) for t in tours_m]
    k["doanh_thu_thang"] = sum((s["revenue"] or 0) for s in sett); k["loi_nhuan_thang"] = sum(s["profit"] for s in sett); k["so_chuyen_thang"] = len(tours_m)
    _nguong = R.get_param(db, "nguong_bien")
    k["chuyen_duoi_10"] = sum(1 for s in sett if s["margin"] < _nguong)
    m0 = datetime(today.year, today.month, 1)
    row = db.execute(select(func.count(), func.coalesce(func.sum(func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0)), 0)).where(Booking.created_at >= m0, Booking.cancelled == False)).one()
    k["booking_thang"] = int(row[0]); k["doanh_thu_booking_thang"] = float(row[1])
    k["canh_bao_do"] = db.execute(select(func.count()).select_from(Alert).where(Alert.resolved == False, Alert.level == "red")).scalar()
    _cham("kpi_thang")
    if role in ("chutich", "tgd", "ketoan", "bks", "cntt"):
        b = RP.balances(db, p)
        k["tien"] = sum(b.get(c, 0.0) for c in ("111", "112"))
        from app.models.finance import FinContract
        k["no_vay"] = sum((c.outstanding or 0) for c in db.execute(select(FinContract).where(FinContract.kind == "vay", FinContract.status != "tat_toan")).scalars())
        k["phai_thu"] = float(db.execute(select(func.coalesce(func.sum(func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0) - func.coalesce(Booking.paid, 0)), 0)).where(Booking.cancelled == False, (func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0) - func.coalesce(Booking.paid, 0)) > 0)).scalar() or 0)
        # TC-48 · ĐÁY thay cho CUỐI KỲ (anh Tuấn chốt 17/9/2026: "để đáy thấp nhất, bỏ số tuần 13").
        # `so_du_tuan_13` bỏ hẳn, không giữ song song: hai con số dòng tiền cạnh nhau thì người đọc
        # phải nhớ con nào là con nào, và con dễ đọc hơn (cuối kỳ, thường dương) sẽ thắng. Vì sao
        # đáy mới là câu người điều hành hỏi — xem chú thích `day_thap_nhat` ở services/finance.py.
        _cham("ld_so_du_no_vay_phai_thu")   # KS-XE: đo từng phần của khối KPI lãnh đạo
        fc = FIN.forecast_13w(db); k["du_bao_canh_bao"] = len(fc["alerts"])
        k["so_du_thap_nhat"] = fc["thap_nhat"]
        # TC-57 · DÒNG TIỀN NAY LÀ MỘT BIỂU ĐỒ, KHÔNG PHẢI BỐN Ô "CHƯA CÓ NGUỒN".
        #
        #   "em xoa bo cai nay khoi man hinh chu tich, thay vao do la bieu do va so lieu phan tich
        #    dong tien ngang o duoi PHAI THU VA PHAI TRA"      — anh Tuấn, 17/9/2026
        #
        # Máy chủ dọn sẵn đúng những gì màn hình vẽ, KHÔNG gửi cả `fc` sang: gói đầy đủ có 13 tuần
        # × mọi khoản thu chi theo mã, nặng hơn cần thiết nhiều lần và mở đường cho màn hình tự
        # cộng lại một con số máy chủ đã cộng rồi — đúng cái ranh giới 09/9 cấm.
        #
        # `tong_thu` và `tong_chi` cộng ở ĐÂY chứ không để màn hình cộng, vì lý do trên. Bốn con số
        # (đầu kỳ · dự kiến thu · dự kiến chi · cuối tuần 13) là bốn con số của cùng MỘT phép cân:
        # đầu kỳ + thu − chi = cuối kỳ. Để màn hình tự cộng là mở đường cho bốn con số không còn
        # cân nhau mà chẳng ai biết.
        # `out["sections"]` chứ không phải `sec`: bí danh `sec` chỉ được đặt ở phần "theo phòng" bên
        # dưới, còn khối này nằm trong nhánh vai tài chính ở trên. Cùng một cuốn sổ, khác cái tên.
        out["sections"]["du_bao_13_tuan"] = {
            "dau_ky": fc["opening"],
            "tong_thu": sum(float(w.get("total_in") or 0) for w in fc["weeks"]),
            "tong_chi": sum(float(w.get("total_out") or 0) for w in fc["weeks"]),
            "cuoi_ky": fc["closing"],
            "nguong": fc["min_cash"],
            # TC-59 (17/9/2026) · THÊM `thu` và `chi` TỪNG TUẦN, để biểu đồ vẽ được BA ĐƯỜNG như
            # bản mẫu anh Tuấn gửi: THU · CHI · TỒN. Trước đây chỉ gửi `so_du`, nên hình chỉ nói
            # được "còn bao nhiêu" mà không nói được "vì sao còn bấy nhiêu".
            #
            # BA CON SỐ NÀY RÀNG BUỘC NHAU TỪNG TUẦN: số dư tuần n = số dư tuần n−1 + thu − chi.
            # Chúng lấy từ CÙNG một `fc["weeks"]` đã dùng để cộng `tong_thu` / `tong_chi` ở trên,
            # nên tổng mười ba tuần của đường THU đúng bằng ô "Dự kiến thu" — hai chỗ không thể
            # nói khác nhau, vì chỉ có một phép cộng.
            "tuan": [{"tuan": w["week"], "tu": w["from"], "den": w["to"], "so_du": w["closing"],
                      "thu": w.get("total_in"), "chi": w.get("total_out")}
                     for w in fc["weeks"]],
        }
        _cham("ld_du_bao_13_tuan")
        pl = RP.income_statement(db, p); k["ln_ke_toan_thang"] = dict((r[0], r[2]) for r in pl["rows"])["50"]
        # TC-41 (16/9/2026) – KẾ HOẠCH THÁNG, cửa nhập vừa mở ở /ke-hoach-thang.
        #
        # Suốt bốn vòng, thẻ "Doanh thu tháng" in câu "chưa có kế hoạch tháng để so sánh (Kế toán)"
        # vì không có bảng nào giữ chỉ tiêu. Nay có. Ba điều phải giữ đúng ở đây:
        #
        #   1. TỈ LỆ ĐẠT TÍNH Ở MÁY CHỦ, không ở màn hình. Ranh giới 09/9: màn hình chỉ bày.
        #   2. THIẾU MỘT PHÁP NHÂN LÀ CHƯA CÓ KẾ HOẠCH (services/ke_hoach, LUẬT 1). Hàm hợp_nhat trả
        #      `du=False` kèm tên pháp nhân còn thiếu, và thẻ in đúng câu ấy — không cộng phần đã
        #      nhập rồi gọi nó là chỉ tiêu tháng.
        #   3. KẾ HOẠCH BẰNG 0 KHÔNG SINH RA TỈ LỆ. `ty_le_dat` trả None; in "đạt ∞%" hay "đạt 0%"
        #      đều là trả lời một câu hỏi không có nghĩa.
        #
        # Chỉ trả cho nhóm vai trò của nhánh này. Chỉ tiêu cả tập đoàn không phải thứ mọi tài khoản
        # đăng nhập đều đọc được, và cửa /ke-hoach cũng chặn đúng danh sách ấy.
        _cham("ld_lai_lo_thang")
        from app.services import ke_hoach as KH
        kh = KH.hop_nhat(db, KH.ky_cua(today))
        k["ke_hoach_thang"] = {
            "ky": kh["ky"],
            "doanh_thu": kh["doanh_thu"],
            "loi_nhuan_truoc_thue": kh["loi_nhuan_truoc_thue"],
            "ty_le_dat_doanh_thu": KH.ty_le_dat(k.get("doanh_thu_thang"),
                                                kh["doanh_thu"]["gia_tri"]),
            "ty_le_dat_loi_nhuan": KH.ty_le_dat(k.get("ln_ke_toan_thang"),
                                                kh["loi_nhuan_truoc_thue"]["gia_tri"]),
            "cua_nhap": "/ke-hoach-thang",
        }
    _cham("kpi_lanh_dao")
    # --- phần theo phòng ---
    sec = out["sections"]
    # Hai phòng Kinh doanh được đo bằng hai thước đo khác nhau, nên màn hình phải hiện hai bảng khác nhau
    # (chỉ đạo 07/9/2026). Phòng Lẻ: doanh thu tính chỉ tiêu so mốc → bậc thang hoa hồng. Phòng Đoàn: chia
    # LỢI NHUẬN quyết toán, không có mốc doanh thu. Trước đây chỉ có bảng của phòng Lẻ, nên người phòng Đoàn
    # mở trang chủ ra không thấy gì về phần việc của mình – đúng cách tính lương của họ cũng không thấy.
    if role in ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "ptgd_doan", "chutich", "tgd"):
        moc = R.get_param(db, "moc_chi_tieu_hcm")
        le: dict[int, float] = {}; doan: dict[int, float] = {}; doan_tours = 0
        for t, s in zip(tours_m, sett):                  # dùng lại `sett` đã tính, không gọi quyết toán lần hai
            if R.is_doan(t):
                doan_tours += 1
                rev = s["revenue"]
                for b in t.bookings:
                    if b.cancelled: continue
                    # Chia lợi nhuận theo tỷ trọng doanh thu booking – cùng công thức bảng lương (services/hr.py),
                    # để con số trên trang chủ và con số trả lương không nói khác nhau.
                    doan[b.sales_id] = doan.get(b.sales_id, 0.0) + s["profit"] * ((b.amount or 0) / rev if rev else 0)
                continue
            for b in t.bookings:
                if b.counts_for_target: le[b.sales_id] = le.get(b.sales_id, 0) + (b.amount or 0) - (b.discount or 0)
        users = {x.id: x.full_name for x in db.execute(select(User)).scalars()}
        sec["kd_le"] = sorted([{"sales": users.get(i, i), "revenue": v, "pct": v / moc if moc else 0} for i, v in le.items()], key=lambda r: -(r["revenue"] or 0))
        sec["kd_doan"] = {"so_chuyen": doan_tours,
                          "rows": sorted([{"sales": users.get(i, i), "profit_share": v} for i, v in doan.items()], key=lambda r: -r["profit_share"])}
        sec["doanh_thu_phong"] = doanh_thu_phong(db, today)
    _cham("kinh_doanh")
    if role in ("tp_dh", "nv_dh", "chutich", "tgd"):
        d7 = int(R.get_param(db, "moc_d7")); rows = []
        for t in db.execute(select(Tour).options(selectinload(Tour.bookings))
                            .where(Tour.status == "da_duyet", Tour.start_date >= today,
                                   Tour.start_date <= today + timedelta(days=SO_NGAY_SAP_KHOI_HANH))).scalars():
            c = R.calc_db(db, t, R.get_param(db, "nguong_bien", t.start_date)); left = (t.start_date - today).days
            pax = R.booked_pax(t)
            rows.append({"code": t.code, "start": t.start_date, "days_left": left, "booked": pax,
                         "breakeven": c["breakeven_pax"], "below": pax < (c["breakeven_pax"] or 0)})
        sec["sap_khoi_hanh"] = sorted(rows, key=lambda r: r["days_left"])
        # Trả LUÔN số ngày ra cho màn hình, đừng để màn hình gõ lại con số.
        # Trước 14/9 máy chủ lọc 21 ngày còn tiêu đề trên màn hình ghi "21 ngày tới" bằng chữ
        # gõ tay. Đổi một nơi là hai nơi nói khác nhau, và người đọc không có cách nào biết
        # nơi nào đúng. Nay một chỗ khai, một chỗ đọc.
        sec["sap_khoi_hanh_so_ngay"] = SO_NGAY_SAP_KHOI_HANH
        _cham("dh_sap_khoi_hanh")
        # TC-46 · BA GIAI ĐOẠN CỦA CHUYẾN ĐÃ DUYỆT (anh Tuấn chốt 16/9/2026, theo bản vẽ v3.0).
        # `counts` do routes.py dựng chỉ đếm theo TRẠNG THÁI, mà trạng thái không phân biệt được
        # chuyến chưa đi với chuyến đang trên đường. Phép chia theo NGÀY nằm ở dem_tour, khai một
        # lần — xem chú thích TC-46 ở đó.
        from app.services import dem_tour as DT
        sec["tour_giai_doan"] = DT.theo_giai_doan(db, hom_nay=today)
        _cham("dh_giai_doan")
        # TQ-1 (Chủ tịch chốt v1.1, 22/10/2026): số ĐẦY ĐỦ cho mục «Vận hành & công việc».
        # Bọc try riêng: một ô hỏng không kéo sập cả bảng điều hành.
        try:
            from app.services import tong_quan_tour as TQT
            sec["qua_han_qt_tong"] = TQT.qua_han_quyet_toan(db, today, trang=1, co=1)["tong"]
            # Truyền lại số vừa đếm ở dòng trên. Thiếu thì `cho_quyet_toan` tự đếm, tức quét
            # bảng tour HAI lượt mỗi lần dựng bảng điều hành — máy chủ 512 MB.
            sec["cho_quyet_toan"] = TQT.cho_quyet_toan(db, today, qua_han=sec["qua_han_qt_tong"])
            sec["thieu_lich"] = TQT.thieu_lich(db, today)
        except Exception as ex:
            sec["qua_han_qt_tong"] = sec["cho_quyet_toan"] = sec["thieu_lich"] = None
            R.audit(db, "robot", "robot", "tq1_tour_loi", "dashboard", after={"ly_do": str(ex)[:200]})
        # XE HÔM NAY — cùng MỘT luật với tour, áp cho xe: lịch hôm nay trùng lịch điều xe thì xe ấy
        # đang chạy, còn lại là nằm bãi (anh Tuấn 16/9/2026). Nguồn là LỆNH ĐIỀU XE, không phải
        # nhật trình chuyến — xem chú thích đầu services/xe_hom_nay.py để biết vì sao khác nhau.
        _cham("dh_quyet_toan_tq1")
        from app.services import xe_hom_nay as XE
        sec["xe_hom_nay"] = XE.dem(db, hom_nay=today)
        # XS-1 (Chủ tịch 25/10/2026): CHƯA có lệnh điều xe nào thì đọc sheet quyết toán của Đội xe.
        # Có lệnh rồi thì LỆNH THAY SHEET — không tính, để màn hình không có hai con số «xe đang đi».
        # Trường riêng, không trộn vào `xe_hom_nay`: số ấy đếm LỆNH, số này đếm DÒNG SHEET.
        # Bọc try riêng: sheet ngừng công bố hay mạng hỏng không được kéo sập bảng điều hành.
        _cham("dh_xe_hom_nay")
        sec["xe_theo_sheet"] = None
        if not sec["xe_hom_nay"].get("co_lenh"):
            try:
                from app.services import xe_theo_sheet as XS
                sec["xe_theo_sheet"] = XS.tom_tat(db, today)
            except Exception as ex:
                R.audit(db, "robot", "robot", "xs1_sheet_loi", "dashboard", after={"ly_do": str(ex)[:200]})
        # ── HQ-1 (13/10/2026) · khối 04b Hiệu quả đội xe ────────────────────────────────────
        # Bốn ô này nằm trên bản vẽ từ lâu và giao diện đã dựng xong (KhoiV14.tsx), nhưng máy chủ
        # chưa bao giờ trả trường nào — rà cả kho mã ngày 12/10 thì `ngay_xe_hoat_dong`,
        # `cong_suat_khai_thac`, `km_chay_rong`, `chi_phi_moi_km` xuất hiện ở ĐÚNG 0 tệp backend.
        # Nên khối hiện "Chưa kết nối" không phải vì thiếu số, mà vì không ai gửi số.
        #
        # Nối được từ hôm nay vì lượt nạp 676 chuyến (13/10) mang đủ km đầu/km cuối cho CẢ 676 —
        # không có km thì ba trong bốn ô vẫn phải để trống.
        #
        # Bọc try cùng lý lẽ với các khối khác: một ô hỏng không được kéo sập bảng điều hành. Và khi
        # hỏng thì để KHUYẾT trường chứ không trả 0 — màn hình tự hiện "Chưa kết nối", còn số 0 đọc
        # ra là "đội xe chạy 0 ngày".
        _cham("dh_sheet_doi_xe")
        try:
            from app.services import hieu_qua_xe as HQ
            tk = HQ.theo_ky(db, today, hom_nay=today, nho=HQ.nho_cho_bang(today))   # KS-XE
            # HQ-2 — danh sách kỳ CÓ CHUYẾN đi kèm ngay lần vẽ đầu. Thiếu nó thì ô chọn kỳ không
            # hiện ra cho tới khi người đọc đổi kỳ một lần — tức là không bao giờ.
            tk["ky_co_chuyen"] = HQ.ky_co_chuyen(db)
            sec["hieu_qua_xe"] = tk["thang"]
            sec["hieu_qua_xe_theo_ky"] = tk
        except Exception as ex:
            sec["hieu_qua_xe"] = None
            sec["hieu_qua_xe_theo_ky"] = None
            R.audit(db, "robot", "robot", "hieu_qua_xe_loi", "dashboard",
                    after={"ly_do": str(ex)[:200]})
        # Quá hạn quyết toán. Hạn = ngày kết thúc + số ngày theo tham số (đoàn và lẻ khác nhau), nên
        # lọc luôn bằng ngày kết thúc: chuyến kết thúc SAU today − hạn dài nhất thì chắc chắn chưa quá
        # hạn, không cần nạp về. Bản cũ nạp 400 chuyến gần nhất rồi bỏ đi phần lớn.
        _cham("dh_hieu_qua_xe")
        han_le = int(R.get_param(db, "han_qt_le")); han_doan = int(R.get_param(db, "han_qt_doan"))
        moc = today - timedelta(days=min(han_le, han_doan))
        sec["qua_han_qt"] = [{"code": t.code, "deadline": R.settlement_deadline(db, t)}
                             for t in db.execute(select(Tour).where(Tour.status == "ket_thuc", Tour.end_date < moc)
                                                 .order_by(desc(Tour.end_date)).limit(300)).scalars()
                             if today > R.settlement_deadline(db, t)][:100]
    _cham("dieu_hanh")   # KS-XH: trong vai điều hành, phần còn lại sau `dh_hieu_qua_xe` là danh sách quá hạn quyết toán
    # ── Khối 05 của bản vẽ V1.4: Phải thu / Phải trả theo HẠN THANH TOÁN ──────────────────────
    #
    # Giao diện dựng từ vòng TC-23 (13/9) nhưng mọi ô ghi "Chưa kết nối". Anh Tuấn kiểm 14/9: màn
    # hình Chủ tịch vẫn chưa xong. Rà lại thì nguồn số ĐÃ CÓ — sổ nghĩa vụ VPM-11 — nên đây chỉ là
    # phép chia nhóm theo hạn, không phải một cửa nhập mới.
    #
    # VAI TRÒ TRUYỀN VÀO `theo_han` là hàng rào SEC-02 thật: `nghia_vu._loc()` lọc ngay trong câu
    # truy vấn theo `nhom_duoc_xem(vai_tro)`, nên Tổng giám đốc không cộng được ba nhóm khoản vay.
    # Không truyền vai trò là mở toàn sổ cho mọi người xem màn hình này.
    if role in ("chutich", "tgd", "ketoan", "bks"):
        from app.services import han_cong_no as HCN
        thu = HCN.theo_han(db, HCN.THU, vai_tro=role, hom_nay=today)
        tra = HCN.theo_han(db, HCN.CHI, vai_tro=role, hom_nay=today)
        sec["phai_thu_theo_han"] = thu["nhom"]
        sec["phai_thu_chua_co_han"] = thu["chua_co_han"]
        sec["phai_tra_theo_han"] = tra["nhom"]
        sec["phai_tra_chua_co_han"] = tra["chua_co_han"]
        # TC-45 (16/9/2026): bỏ `phai_tra_qua_han`. Quá hạn nay là MỘT trong bảy nhóm ở cả hai
        # hướng, nên giữ thêm một con số riêng cho nó là để cùng một khoản tiền hiện hai chỗ trên
        # một màn hình — và tổng bảy nhóm sẽ không khớp với con số riêng ấy khi ai đó cộng thử.
        # Lý do RỖNG đi kèm số rỗng. Ô trống không nói vì sao là ô nằm đó mãi.
        sec["phai_thu_vi_sao"] = thu["vi_sao"]
        sec["phai_tra_vi_sao"] = tra["vi_sao"]

    _cham("phai_thu_tra")
    # ── TC-32 · khối 04c Tồn đọng theo bộ phận ───────────────────────────────────────────────
    # KHÔNG thêm cửa nhập nào (ranh giới 09/9): bộ phận suy ra từ chuỗi PQ-9 đã có sẵn
    # cảnh báo → người phụ trách → users.department.
    #
    # HÀNG RÀO SEC-02: `bo_phan_duoc_xem=None` là xem TOÀN BỘ công ty, nên chỉ cấp lãnh đạo và
    # CNTT (người chạy lượt giao chủ) được None. Mọi vai khác chỉ thấy phòng MÌNH — và vai chưa
    # khai phòng thì thấy MỘT TẬP RỖNG, không phải toàn bộ. Mặc định "chưa khai = xem hết" là
    # cách một tài khoản thiếu dữ liệu biến thành một tài khoản thừa quyền.
    if role in ("chutich", "tgd", "bks", "cntt"):
        _pham_vi_bp = None
    else:
        _pham_vi_bp = {u.department} if getattr(u, "department", "") else set()
    from app.services import ton_dong_bo_phan as TDBP
    _td = TDBP.theo_bo_phan(db, bo_phan_duoc_xem=_pham_vi_bp, hom_nay=today)
    sec["ton_dong_bo_phan"] = _td["dong"]
    sec["ton_dong_chua_ro_bo_phan"] = _td["chua_ro_bo_phan"]
    sec["ton_dong_da_loai"] = _td["da_loai"]
    sec["ton_dong_vi_sao"] = _td["vi_sao"]

    _cham("ton_dong_bo_phan")
    # ── TC-36 · xu hướng bốn chỉ tiêu (biểu đồ nhỏ trên thẻ) ─────────────────────────────────
    # Anh Tuấn chốt 15/9: thẻ vừa hiện số vừa hiện xu hướng so kỳ trước. Phép tính nằm trọn ở
    # `xu_huong.py`; ở đây chỉ gọi. KHÔNG tính lại doanh thu/lợi nhuận bằng công thức riêng —
    # `xu_huong.doc_that` gọi đúng những hàm bảng này đang gọi, nên biểu đồ không thể nói khác thẻ.
    #
    # Bọc try riêng: xu hướng là phần TRANG TRÍ THÔNG TIN, hỏng thì thẻ vẫn phải hiện con số. Một
    # lỗi ở chuỗi lịch sử không được kéo sập cả bảng điều hành.
    try:
        from app.services import xu_huong as XH
        # KS-XH: MỘT hàm đọc cho cả hai lời gọi dưới, nhớ tháng đã đóng — xem `xu_huong.doc_cho_bang`.
        _doc_xh = XH.doc_cho_bang(db, hom_nay=today)
        sec["xu_huong"] = XH.cho_man_hinh(db, so_ky=6, hom_nay=today, doc=_doc_xh)
        # TC-42 (16/9/2026) · anh Tuấn chốt sáu ô lớn, hai ô đầu có ô chọn THÁNG / QUÝ / NĂM.
        #
        # Ba chuỗi dựng ĐỘC LẬP (xu_huong.bo_ba_ky), không lấy chuỗi tháng làm lối lui cho quý và
        # năm. Bài học đã phải trả giá ở khối Hiệu quả đội xe (TC-40): ba nút mà bấm sang kỳ nào
        # cũng ra cùng một bộ số là nói dối bằng giao diện — người đọc kết luận quý bằng tháng, chứ
        # không kết luận là chưa có số.
        #
        # Quý và năm là TỔNG CỦA CÁC THÁNG, không phải một truy vấn thứ hai cho cùng một câu hỏi.
        sec["ba_ky"] = XH.ba_ky_cho_man_hinh(db, hom_nay=today, doc=_doc_xh)
    except Exception as ex:
        sec["xu_huong"] = {}
        sec["ba_ky"] = {}
        R.audit(db, "robot", "robot", "xu_huong_loi", "dashboard", after={"ly_do": str(ex)[:200]})

    _cham("xu_huong")
    # ── TC-42 · Tồn đọng cần xử lý, tách theo ba mức độ ──────────────────────────────────────
    # Trước vòng này màn hình có đúng MỘT con số (1483 cảnh báo đỏ), và một con số nằm một mình
    # thì không nói được điều gì để hành động. `Alert.level` đã có sẵn trong sổ nên chiều "mức độ"
    # vẽ được NGAY, không phải chờ bản lưu kỳ nào tích luỹ — đó là lý do chọn chiều này trước.
    #
    # Bọc try riêng cùng lý lẽ với xu hướng: một ô hỏng không được kéo sập cả bảng điều hành.
    try:
        from app.services import canh_bao_muc as CBM
        sec["ton_dong_theo_muc"] = CBM.theo_muc(db)
    except Exception as ex:
        sec["ton_dong_theo_muc"] = None
        R.audit(db, "robot", "robot", "ton_dong_muc_loi", "dashboard",
                after={"ly_do": str(ex)[:200]})
    _cham("ton_dong_muc")
    # TQ-1: VIỆC đang mở — lọc theo quyền người xem TRƯỚC, gộp theo hồ sơ SAU (tong_quan_viec).
    # `ton_dong_theo_muc` ở trên đếm LƯỢT CẢNH BÁO và không lọc theo quyền; giữ tới khi màn hình
    # chuyển hẳn sang khối mới rồi bỏ.
    try:
        from app.services import tong_quan_viec as TQV
        sec["viec_van_hanh"] = TQV.tong(db, u)
    except Exception as ex:
        sec["viec_van_hanh"] = None
        R.audit(db, "robot", "robot", "tq1_viec_loi", "dashboard", after={"ly_do": str(ex)[:200]})

    _cham("viec_dang_mo")
    # ── TC-33 · khối 08 Tiến độ báo cáo & kết luận chỉ đạo ───────────────────────────────────
    # Cũng không thêm bảng nào: danh sách phòng phải nộp đã khai ở `bao_cao_phong.PHONG`, bản đã
    # nộp nằm ở `bao_cao_luu`. Đối chiếu hai cái là ra.
    #
    # Đo KỲ VỪA ĐÓNG, không đo kỳ đang chạy: báo cáo tháng 09 không thể "trễ" vào ngày 15/09, và
    # tám dòng đỏ vô nghĩa là cách nhanh nhất để người ta thôi tin cả khối.
    #
    # HÀNG RÀO SEC-02 dùng lại đúng bảng khai quyền của `bao_cao_phong` — không khai riêng ở đây,
    # vì hai bản khai cùng một thứ thì sớm muộn lệch nhau.
    from app.services import tien_do_bao_cao as TDBC
    _bc = TDBC.tien_do(db, kind="thang", hom_nay=today, vai_tro=role)
    sec["tien_do_bao_cao"] = _bc["dong"]
    sec["tien_do_ten_ky"] = _bc["ten_ky"]
    sec["tien_do_so_da_nop"] = _bc["so_da_nop"]
    sec["tien_do_so_thieu"] = _bc["so_thieu"]
    sec["tien_do_vi_sao"] = _bc["vi_sao"]
    sec["tien_do_chi_dao_vi_sao"] = _bc["chi_dao_vi_sao"]
    _cham("tien_do_bao_cao")
    if role in ("hcns", "chutich", "tgd"):
        s = OPS.work_days_in(today.year, today.month, until=today)
        emps = OPS.nhan_vien_phai_nop(db)   # BC-1: mọi nhân viên văn phòng trừ HDV, tài xế, Ban TGĐ
        # Chỉ cần ĐẾM báo cáo trong tháng – đếm bằng SQL thay vì nạp toàn bộ bảng báo cáo ngày rồi lọc.
        so_bao_cao = db.execute(select(func.count()).select_from(DailyReport)
                                .where(DailyReport.report_date >= date(today.year, today.month, 1),
                                       DailyReport.report_date <= today)).scalar() or 0
        sec["bao_cao_ngay"] = {"nhan_su": len(emps), "ngay_lam_viec": len(s), "ty_le_nop": (so_bao_cao / (len(emps) * len(s))) if emps and s else 0,
                              "thieu_2_ngay": db.execute(select(func.count()).select_from(Alert).where(Alert.kind == "bc_ngay_2", Alert.resolved == False)).scalar()}
    _cham("cuoi")
    return out


# ====================== ROBOT R7 – BÁO CÁO TỰ ĐỘNG ======================
def _fmt(v): return f"{v:,.0f}"


def compose(db: Session, kind: str) -> tuple[str, dict]:
    """Gom số liệu báo cáo ngày/tuần/tháng thành markdown + dict số liệu."""
    today = date.today(); p = f"{today:%Y-%m}"
    data: dict = {"kind": kind, "date": str(today)}
    lines = []
    if kind == "ngay":
        alerts = db.execute(select(Alert).where(Alert.resolved == False).order_by(desc(Alert.created_at))).scalars().all()
        txns = [t for t in db.execute(select(BankTransaction)).scalars() if t.received_at.date() == today]
        cho = [t for t in txns if t.match_status == "cho_ke_toan"]
        reqs = [r for r in db.execute(select(ServiceRequest).where(ServiceRequest.booking_id == None)).scalars()]
        fc = FIN.forecast_13w(db)
        data.update({"alerts_red": sum(1 for a in alerts if a.level == "red"), "alerts": len(alerts), "sepay_in": sum((t.amount or 0) for t in txns if t.transfer_type == "in"), "sepay_cho": len(cho),
                     "yc_cho_booking": len(reqs), "tien": fc["opening"], "canh_bao_dong_tien": fc["alerts"][:3]})
        lines += [f"# Báo cáo ngày {today:%d/%m/%Y} (robot R7)", "",
                  f"- Tiền hiện có: **{_fmt(fc['opening'])} đ**; dự báo 13 tuần: {len(fc['alerts'])} tuần cảnh báo" + (f" – {fc['alerts'][0]}" if fc["alerts"] else ""),
                  f"- SePay hôm nay: tiền vào {_fmt(data['sepay_in'])} đ; {len(cho)} giao dịch chờ Kế toán khớp",
                  f"- Yêu cầu chưa tạo booking: {len(reqs)}",
                  f"- Cảnh báo mở: {len(alerts)} (đỏ: {data['alerts_red']})"] + [f"  - [{a.level}] {a.message}" for a in alerts[:8]]
    elif kind == "tuan":
        w = FIN.weekly_finance(db); fc = FIN.forecast_13w(db)
        d7 = [t for t in db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars() if 0 <= (t.start_date - today).days <= 7 and R.booked_pax(t) < (R.calc_db(db, t, R.get_param(db, "nguong_bien"))["breakeven_pax"] or 0)]
        qh = [t for t in db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars() if today > R.settlement_deadline(db, t)]
        bk = [b for b in db.execute(select(Booking)).scalars() if (today - b.created_at.date()).days < 7]
        data.update({"tien": w["cash"], "no_vay": w["total_loans"], "phai_thu": w["receivables_total"], "dau_tu": w["investments_total"], "wip_154": w["wip_154"], "accrued_335": w["accrued_335"],
                     "han_4_tuan": sum((x["amount"] or 0) for x in w["due_4w"]), "d7": [t.code for t in d7], "qua_han_qt": [t.code for t in qh], "booking_tuan": len(bk), "dt_booking_tuan": sum((b.amount or 0) - (b.discount or 0) for b in bk),
                     "canh_bao_dong_tien": fc["alerts"][:5], "qua_han_tai_chinh": w["overdue"]})
        lines += [f"# Báo cáo tuần – đến {today:%d/%m/%Y} (robot R7)", "", "## Tài chính (Chủ tịch, TGĐ, KTT, BKS)",
                  f"- Tiền: **{_fmt(w['cash'])} đ** · Dư nợ vay: {_fmt(w['total_loans'])} đ · Phải thu khách: {_fmt(w['receivables_total'])} đ",
                  f"- Đầu tư, hợp tác, ký quỹ, cọc, cho vay còn lại: {_fmt(w['investments_total'])} đ; quá hạn thu hồi: {len(w['overdue'])} khoản",
                  f"- Hạn trả gốc/lãi/thu hồi 4 tuần tới: {_fmt(data['han_4_tuan'])} đ ({len(w['due_4w'])} dòng)",
                  f"- 154 tồn đọng: {_fmt(w['wip_154'])} đ · 335 chưa hóa đơn: {_fmt(w['accrued_335'])} đ",
                  f"- Dự báo 13 tuần: {len(fc['alerts'])} tuần cảnh báo" + ("; " + "; ".join(fc["alerts"][:2]) if fc["alerts"] else ""),
                  "", "## Kinh doanh – Điều hành", f"- Booking tuần: {len(bk)} · doanh thu booking {_fmt(data['dt_booking_tuan'])} đ",
                  f"- Chuyến D-7 dưới hòa vốn: {', '.join(data['d7']) or 'không'}", f"- Tour quá hạn quyết toán: {', '.join(data['qua_han_qt']) or 'không'}"]
    else:  # thang
        y, m = today.year, today.month
        tours_m = _month_tours(db, y, m); sett = [(t, R.settlement_summary(db, t)) for t in tours_m]
        pl = RP.income_statement(db, p); plr = dict((r[0], r[2]) for r in pl["rows"])
        run = db.execute(select(PayrollRun).where(PayrollRun.period == p)).scalars().first()
        by_op = {}
        for t, s in sett:
            o = by_op.setdefault(t.operator.full_name if t.operator else "?", {"chuyen": 0, "ln": 0.0, "dat": 0})
            o["chuyen"] += 1; o["ln"] += s["profit"]; o["dat"] += 1 if s["margin"] >= R.get_param(db, "nguong_bien") else 0
        data.update({"so_chuyen": len(tours_m), "doanh_thu_qt": sum((s["revenue"] or 0) for _, s in sett), "loi_nhuan_qt": sum(s["profit"] for _, s in sett),
                     "chuyen_duoi_10": sum(1 for _, s in sett if s["margin"] < R.get_param(db, "nguong_bien")), "quy_thuong_dh": sum(s["fund"] for _, s in sett),
                     "kqkd": plr, "lai_vay": pl["management"]["interest"], "khau_hao": pl["management"]["depreciation"], "theo_dieu_hanh": by_op,
                     "bang_luong": run.status if run else "chưa lập", "thuc_nhan": run.totals.get("thuc_nhan") if run else 0})
        lines += [f"# Báo cáo tháng {m:02d}/{y} (robot R7)", "", "## Kết quả kinh doanh (BCKQKD tách lãi vay, khấu hao – Kế toán ngày 10)",
                  f"- Doanh thu kế toán: **{_fmt(plr['01'])} đ** · Giá vốn: {_fmt(plr['11'])} đ · LN trước thuế: **{_fmt(plr['50'])} đ**",
                  f"- Lãi vay: {_fmt(pl['management']['interest'])} đ · Khấu hao: {_fmt(pl['management']['depreciation'])} đ · LN sau lãi vay trước khấu hao: {_fmt(pl['management']['profit_after_interest_before_dep'])} đ",
                  "", "## Quyết toán chuyến (căn cứ thưởng)", f"- {len(tours_m)} chuyến Kế toán xác nhận · doanh thu {_fmt(data['doanh_thu_qt'])} đ · lợi nhuận {_fmt(data['loi_nhuan_qt'])} đ · {data['chuyen_duoi_10']} chuyến dưới 10% · quỹ thưởng ĐH {_fmt(data['quy_thuong_dh'])} đ"]
        lines += [f"  - {n}: {o['chuyen']} chuyến, LN {_fmt(o['ln'])} đ, đạt 10%: {o['dat']}/{o['chuyen']}" for n, o in by_op.items()]
        lines += ["", "## Nhân sự", f"- Bảng lương {p}: {data['bang_luong']}; thực nhận {_fmt(data['thuc_nhan'] or 0)} đ"]
    return "\n".join(lines), data


def claude_comment(md: str, data: dict, db=None) -> str:
    """Nhận xét ngắn bằng tiếng Việt qua Anthropic API nếu có khóa; không có khóa → nhận xét theo quy tắc.

    Nhận xét này đi thẳng lên bàn Chủ tịch và TGĐ, nên phải để lại vết như mọi việc AI làm: truyền db vào
    thì ghi nhật ký AI (chỉ đạo 07/9/2026). Để db=None thì vẫn chạy như cũ – hàm này còn được gọi từ chỗ
    không có phiên cơ sở dữ liệu.
    """
    prompt = ("Bạn là robot báo cáo quản trị của Vietourist Holdings (công ty lữ hành). Đọc số liệu dưới đây và viết 3–5 câu nhận xét ngắn gọn bằng tiếng Việt cho Ban Điều hành: điểm cần chú ý, rủi ro, việc nên làm trong tuần. Không bịa số.\n\n" + md)

    def _ghi(ket_qua: str, nguon: str, mo_hinh: str = "", t_in: int = 0, t_ra: int = 0, loi: str = ""):
        if db is None: return
        try:
            from app.services import ai_log as AL
            AL.ghi(db, tac_vu="vb_noi_bo", muc=1, dau_vao=prompt, ket_qua=ket_qua, nguon=nguon,
                   mo_hinh=mo_hinh, ref="bao_cao_quan_tri", tokens_vao=t_in, tokens_ra=t_ra, loi=loi)
        except Exception:  # noqa – nhật ký hỏng không được làm hỏng báo cáo
            pass

    key = settings.ANTHROPIC_API_KEY
    if key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(model=settings.ANTHROPIC_MODEL, max_tokens=400, messages=[{"role": "user", "content": prompt}])
            out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            u = getattr(msg, "usage", None)
            _ghi(out, "claude", settings.ANTHROPIC_MODEL,
                 int(getattr(u, "input_tokens", 0) or 0), int(getattr(u, "output_tokens", 0) or 0))
            return out
        except Exception as ex:  # noqa
            out = f"(Không gọi được Claude API: {type(ex).__name__}) " + rule_comment(data)
            _ghi(out, "quy_tac", loi=f"{type(ex).__name__}: {ex}")
            return out
    out = rule_comment(data)
    _ghi(out, "quy_tac", loi="chưa cấu hình ANTHROPIC_API_KEY")
    return out


def rule_comment(d: dict) -> str:
    notes = []
    if d.get("canh_bao_dong_tien"): notes.append("Dòng tiền dự báo có tuần dưới ngưỡng/âm – cần đẩy thu booking trước D-7 và giãn lệnh chi chưa cấp thiết.")
    if d.get("qua_han_qt"): notes.append(f"Có {len(d['qua_han_qt'])} tour quá hạn quyết toán – người điều hành mất thưởng chuyến, Kế toán cần danh sách hằng tuần.")
    if d.get("d7"): notes.append(f"{len(d['d7'])} chuyến D-7 dưới hòa vốn chưa có quyết định ghép/dời/hủy.")
    if d.get("sepay_cho"): notes.append(f"{d['sepay_cho']} giao dịch ngân hàng chờ Kế toán khớp – nên xử lý trong ngày để công nợ khách chính xác.")
    if d.get("chuyen_duoi_10"): notes.append(f"{d['chuyen_duoi_10']} chuyến quyết toán dưới biên 10% – rà giá vốn định mức và mã khuyến mãi.")
    if d.get("qua_han_tai_chinh"): notes.append(f"{len(d['qua_han_tai_chinh'])} khoản thu hồi đầu tư/hợp tác quá hạn – trình HĐQT phương án.")
    return " ".join(notes) or "Không có điểm bất thường theo quy tắc; số liệu trong ngưỡng."


def run_report(db: Session, kind: str, actor: str = "robot") -> AutoReport:
    if kind not in ("ngay", "tuan", "thang"): raise ValueError("kind: ngay / tuan / thang")
    md, data = compose(db, kind)
    comment = claude_comment(md, data, db)
    md += "\n\n## Nhận xét của robot\n" + comment
    today = date.today()
    period = str(today) if kind == "ngay" else f"{today:%Y}-W{today.isocalendar()[1]:02d}" if kind == "tuan" else f"{today:%Y-%m}"
    rep = db.execute(select(AutoReport).where(AutoReport.kind == kind, AutoReport.period == period)).scalars().first()
    if rep is None:
        rep = AutoReport(kind=kind, period=period); db.add(rep)
    rep.content, rep.data, rep.comment, rep.created_by, rep.created_at = md, data, comment, actor, datetime.now()
    R.audit(db, actor, "robot", "robot_bao_cao", f"report:{kind}:{period}", after={"dai": len(md)})
    db.commit(); db.refresh(rep)
    return rep
