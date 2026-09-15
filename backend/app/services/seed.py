"""Dữ liệu mẫu để chạy thử.

MẬT KHẨU GIEO Ở ĐÂY KHÔNG ĐƯỢC LÀ MỘT CHUỖI AI CŨNG ĐOÁN RA.

Đến 14/9/2026 tệp này gieo "123456" cho mọi tài khoản, và trang đăng nhập của bản chạy trên internet
công cộng in thẳng danh sách tài khoản kèm chuỗi ấy ra màn hình. Mười hai tài khoản — kể cả Chủ
tịch, Tổng giám đốc và Kế toán — mở được bằng một dòng chữ ai cũng đọc.

Nay cửa đăng nhập nhận ra mật khẩu đã bị công bố (`services/mat_khau_yeu.DA_CONG_KHAI`) và buộc đổi
ngay tại chỗ. Nên gieo lại đúng chuỗi ấy là tự khoá mọi tài khoản mẫu ra khỏi hệ thống — và đó là
điều ĐÚNG, chỉ có điều dữ liệu mẫu thì không cần trả giá ấy. Chuỗi dưới đây chỉ là mật khẩu cho bản
chạy thử; bản chạy thật không dùng tệp này.
"""
from datetime import date, datetime, timedelta
from app.core.security import hash_password
from sqlalchemy import select
from app.models.core import User, Tour, ServiceRequest, Booking
from app.models.hr import GuideRate, Employee, VisaFile, GuideAssignment, Vehicle, VehicleRate, DispatchOrder
from app.models.fleet import VehiclePlate, FleetVerification
from app.services import rules as core

USERS = [
    ("chutich", "Chủ tịch HĐQT", "chutich", "HĐQT"),
    ("tgd", "Tổng giám đốc", "tgd", "Ban TGĐ"),
    ("ptgd.doan", "Phó TGĐ tour đoàn", "ptgd_doan", "Ban TGĐ"),
    ("ptgd.mkt", "Phó TGĐ Marketing", "ptgd_mkt", "Ban TGĐ"),
    ("tp.dieuhanh", "Trưởng phòng Điều hành", "tp_dh", "Điều hành"),
    ("dh.lan", "Nguyễn Thị Lan (điều hành nội địa)", "nv_dh", "Điều hành"),
    ("dh.minh", "Trần Văn Minh (điều hành outbound)", "nv_dh", "Điều hành"),
    ("gd.kd", "Giám đốc Kinh doanh", "gd_kd", "Kinh doanh Lẻ"),
    ("kd.hoa", "Lê Thị Hoa (sale lẻ HCM)", "nv_kd", "Kinh doanh Lẻ"),
    ("kd.tuan", "Phạm Anh Tuấn (sale đoàn)", "nv_kd", "Kinh doanh Đoàn"),
    ("ketoan", "Kế toán tổng hợp", "ketoan", "Kế toán"),
    ("hcns", "Nhân sự Hành chính", "hcns", "Hỗ trợ"),
    ("cntt", "Chuyên viên Hệ thống AI", "cntt", "CNTT"),
    ("bks", "Ban Kiểm soát", "bks", "BKS"),
]


def neo_tour_mau(today: date) -> date:
    """Ngày ĐẦU THÁNG của kỳ lương mà tour mẫu DL-0825 thuộc về. Mọi mốc của tour ấy neo vào đây.

    ════════════════════════════════════════════════════════════════════════════════════════════
    VÌ SAO PHẢI CÓ HÀM NÀY — LỖI ĐO ĐƯỢC NGÀY 15/9/2026
    ════════════════════════════════════════════════════════════════════════════════════════════
    Trước đây bảy mốc của tour mẫu rải từ `today-20` (ngày đi) tới `today-13` (CNTT kiểm). Chú
    thích ngay cạnh ghi "đã khóa THÁNG NÀY" — nhưng một khoảng tám ngày thì BẮC QUA ranh giới
    tháng, và lúc ấy lời chú thích sai mà không ai thấy.

    Hai chỗ đọc tour này lấy kỳ theo hai mốc KHÁC NHAU:

        bảng lương   `hr.month_tours`   → tháng của `kt_confirmed_at`  (today-14)
        đội xe       `fleet_summary`    → tháng của `DispatchOrder.date_to` (theo ngày đi, today-18)

    Trùng tháng thì không sao. Lệch tháng thì bảng lương tìm trong tháng này còn chuyến nằm ở
    tháng trước: `so_chuyen` = 0 và `total_revenue` = 0, trong khi dữ liệu mẫu vẫn đủ.

    ĐO TRÊN LỊCH 2026: khoảng ấy bắc qua ranh giới tháng vào NGÀY 15 ĐẾN 20 mỗi tháng — 72 ngày,
    tức 20% số ngày trong năm. `test_hr.py::test_draft_from_seed` và `::test_fleet_summary` đỏ
    đúng những ngày ấy rồi tự xanh lại từ ngày 21.

    Đó là kiểu hỏng nguy hiểm nhất của một bộ kiểm: đỏ theo LỊCH chứ không theo MÃ. Vài lần như
    thế thì không ai phân biệt được "đỏ thật" với "đỏ tới ngày", và lúc có lỗi thật nó trôi qua.

    CÁCH SỬA: neo cả vòng đời tour vào ĐẦU THÁNG của kỳ lương, chứ không đếm lùi từ hôm nay. Mọi
    mốc rơi vào ngày 5–12 của tháng ấy, nên không mốc nào bắc sang tháng khác, ngày nào trong năm
    cũng vậy. `test_hr.py` không phải sửa: kỳ nó tính (`today-14`) đúng bằng tháng neo này.
    """
    ky = today - timedelta(days=14)          # mốc Kế toán xác nhận ĐỊNH NGHĨA kỳ lương
    return date(ky.year, ky.month, 1)


def seed_all(db):
    if db.execute(select(User)).scalars().first():
        # CSDL đã có dữ liệu (bản demo trên cloud): chỉ bổ sung phần nhân sự nếu chưa có
        seed_vehicle_rates(db); seed_guide_rates(db); db.commit(); seed_companies(db)
        if not db.execute(select(Employee)).scalars().first():
            users = {u.username: u for u in db.execute(select(User)).scalars()}
            tours = {t.code: t for t in db.execute(select(Tour)).scalars()}
            if "DL-0825" in tours and "kd.hoa" in users:
                seed_hr(db, users, [tours.get("PT-DL-0912"), tours.get("TL-BKK-1005"), tours.get("DN-HCM-0820"), tours["DL-0825"]], date.today())
                db.commit()
        return
    pw = hash_password("Vtos@Demo#2026")
    users = {}
    for un, name, role, dept in USERS:
        u = User(username=un, full_name=name, role=role, department=dept, password_hash=pw)
        db.add(u); users[un] = u
    db.flush()
    today = date.today()
    _neo = neo_tour_mau(today)
    lan, minh = users["dh.lan"], users["dh.minh"]
    tours = [
        # Tour lẻ đạt biên, đang bán, khởi hành 5 ngày nữa nhưng thiếu khách → D-7
        Tour(code="PT-DL-0912", name="Phan Thiết – Mũi Né 2N1Đ (khởi hành định kỳ)", tour_type="le_noi_dia",
             start_date=today + timedelta(days=5), end_date=today + timedelta(days=6), operator_id=lan.id,
             price_per_pax=1_990_000, fixed_cost=14_000_000, var_cost_per_pax=850_000, planned_pax=30,
             rest_stops="Trạm dừng Dầu Giây; Phan Thiết Center", status="da_duyet", confirmed_by="tp.dieuhanh", approved_by="tgd"),
        # Tour lẻ nước ngoài, biên mỏng → cần 2 chữ ký, đang chờ duyệt
        Tour(code="TL-BKK-1005", name="Bangkok – Pattaya 5N4Đ", tour_type="le_nuoc_ngoai",
             start_date=today + timedelta(days=36), end_date=today + timedelta(days=40), operator_id=minh.id,
             price_per_pax=7_490_000, fixed_cost=48_000_000, var_cost_per_pax=5_200_000, planned_pax=25,
             rest_stops="Sân bay TSN; Suvarnabhumi", status="cho_duyet", below_margin=True, confirmed_by="tp.dieuhanh",
             justification="Lý do: giá vé máy bay mùa cao điểm tăng 18%. Khoản làm mỏng biên: vé máy bay và visa. Phương án bù: bán thêm dịch vụ tùy chọn 1,2 triệu/khách. Lỗ tối đa nếu đủ 25 khách: 0 đ; nếu 20 khách: −6,2 triệu."),
        # Tour đoàn, đã duyệt bởi PTGĐ đoàn, đã kết thúc → chờ quyết toán (hạn 7 ngày)
        Tour(code="DN-HCM-0820", name="Đoàn Công ty ABC – Đà Nẵng 3N2Đ (45 khách)", tour_type="doan_noi_dia",
             start_date=today - timedelta(days=12), end_date=today - timedelta(days=10), operator_id=lan.id,
             price_per_pax=4_200_000, fixed_cost=52_000_000, var_cost_per_pax=2_400_000, planned_pax=45,
             rest_stops="Sân bay Đà Nẵng", status="ket_thuc", confirmed_by="tp.dieuhanh", approved_by="ptgd.doan"),
        # Tour lẻ đã khóa, NẰM GỌN TRONG MỘT THÁNG (xem `neo_tour_mau` ở đầu tệp)
        Tour(code="DL-0825", name="Đà Lạt 3N2Đ", tour_type="le_noi_dia",
             start_date=_neo + timedelta(days=4), end_date=_neo + timedelta(days=6), operator_id=lan.id,
             price_per_pax=2_690_000, fixed_cost=21_000_000, var_cost_per_pax=1_050_000, planned_pax=28,
             rest_stops="Bảo Lộc", status="khoa", confirmed_by="tp.dieuhanh", approved_by="tgd",
             actual_revenue=75_320_000, actual_cost=50_400_000, promo_value=1_500_000,
             closed_at=datetime.combine(_neo + timedelta(days=8), datetime.min.time()),
             kt_confirmed_at=datetime.combine(_neo + timedelta(days=10), datetime.min.time()),
             cntt_checked_at=datetime.combine(_neo + timedelta(days=11), datetime.min.time())),
        # Tour nháp mới
        Tour(code="SG-CT-1020", name="Cần Thơ – Sóc Trăng 2N1Đ", tour_type="le_noi_dia",
             start_date=today + timedelta(days=46), end_date=today + timedelta(days=47), operator_id=lan.id,
             price_per_pax=1_650_000, fixed_cost=9_500_000, var_cost_per_pax=700_000, planned_pax=0, rest_stops="Trạm dừng Mỹ Thuận", status="nhap"),
    ]
    for t in tours:
        db.add(t)
    db.flush()
    hoa, tuan = users["kd.hoa"], users["kd.tuan"]
    # booking cho tour Phan Thiết: 9 khách (dưới hòa vốn 13)
    for i, (name, pax) in enumerate([("Nguyễn Văn A", 4), ("Trần Thị B", 3), ("Lê C", 2)]):
        r = ServiceRequest(tour_id=tours[0].id, sales_id=hoa.id, customer_name=name, customer_phone=f"09000000{i}",
                           source="Fanpage", care_note="Khách quen, thích phòng tầng cao", pax=pax,
                           created_at=datetime.now() - timedelta(days=3, hours=i))
        db.add(r); db.flush()
        b = Booking(code=f"BK{today:%y%m}{i+1:04d}", tour_id=tours[0].id, request_id=r.id, sales_id=hoa.id, created_by=lan.id,
                    customer_name=name, customer_phone=r.customer_phone, source=r.source, care_note=r.care_note, pax=pax,
                    amount=pax * tours[0].price_per_pax, sla_minutes=40 + i * 30, sla_ok=True, created_at=r.created_at + timedelta(minutes=40 + i * 30))
        db.add(b); db.flush(); r.booking_id = b.id
    # booking đoàn Đà Nẵng
    r = ServiceRequest(tour_id=tours[2].id, sales_id=tuan.id, customer_name="Công ty ABC", customer_phone="0281234567",
                       source="Khách hàng cũ", care_note="Hợp đồng số 12/HĐ-ABC, thanh toán 2 đợt", pax=45, created_at=datetime.now() - timedelta(days=30))
    db.add(r); db.flush()
    b = Booking(code=f"BK{today:%y%m}0004", tour_id=tours[2].id, request_id=r.id, sales_id=tuan.id, created_by=lan.id,
                customer_name=r.customer_name, customer_phone=r.customer_phone, source=r.source, care_note=r.care_note, pax=45,
                amount=45 * 4_200_000, sla_minutes=55, sla_ok=True, created_at=r.created_at + timedelta(minutes=55))
    db.add(b); db.flush(); r.booking_id = b.id
    # booking đã khóa Đà Lạt
    r = ServiceRequest(tour_id=tours[3].id, sales_id=hoa.id, customer_name="Nhóm 28 khách", customer_phone="0912345678",
                       source="Zalo", care_note="Có 2 trẻ em", pax=28, created_at=datetime.now() - timedelta(days=40))
    db.add(r); db.flush()
    b = Booking(code=f"BK{today:%y%m}0005", tour_id=tours[3].id, request_id=r.id, sales_id=hoa.id, created_by=lan.id,
                customer_name=r.customer_name, customer_phone=r.customer_phone, source=r.source, care_note=r.care_note, pax=28,
                amount=28 * 2_690_000, discount=1_500_000, promo_code="HE2026", sla_minutes=70, sla_ok=True, created_at=r.created_at + timedelta(minutes=70))
    db.add(b); db.flush(); r.booking_id = b.id
    # yêu cầu chưa tạo booking (quá 2 giờ)
    db.add(ServiceRequest(tour_id=tours[0].id, sales_id=hoa.id, customer_name="Võ Thị D", customer_phone="0977000111",
                          source="Website", care_note="Cần xuất hóa đơn công ty", pax=2, created_at=datetime.now() - timedelta(hours=3)))
    seed_hr(db, users, tours, today)
    core.audit(db, "seed", "cntt", "khoi_tao_du_lieu_mau", "system", after={"users": len(USERS), "tours": len(tours)})
    db.commit()
    core.run_robots(db)


def seed_hr(db, users, tours, today):
    """Hồ sơ nhân sự mẫu gắn tài khoản, 2 HDV CTV, 2 xe + tài xế, hồ sơ visa, phân chuyến và lệnh điều xe cho tour Đà Lạt đã khóa."""
    E = []
    def emp(code, name, dept, pos, office="hcm", ct="hdld", sal=0, user=None, **kw):
        e = Employee(code=code, full_name=name, department=dept, position=pos, office=office, contract_type=ct, base_salary=sal,
                     user_id=users[user].id if user else None, start_date=date(2025, 1, 6), **kw)
        db.add(e); E.append(e); return e
    emp("NS0001", "Giám đốc Kinh doanh", "kd_le", "gd_kd", sal=12_000_000, user="gd.kd")
    emp("NS0002", "Lê Thị Hoa (sale lẻ HCM)", "kd_le", "nv", sal=7_000_000, user="kd.hoa")
    emp("NS0003", "Phạm Anh Tuấn (sale đoàn)", "kd_doan", "nv", sal=9_000_000, user="kd.tuan")
    emp("NS0004", "Phó TGĐ tour đoàn", "kd_doan", "ptgd_doan", sal=12_000_000, user="ptgd.doan")
    emp("NS0005", "Trưởng phòng Điều hành", "dieu_hanh", "tp", sal=12_000_000, user="tp.dieuhanh")
    emp("NS0006", "Nguyễn Thị Lan (điều hành nội địa)", "dieu_hanh", "nv", sal=8_000_000, user="dh.lan")
    emp("NS0007", "Trần Văn Minh (điều hành outbound)", "dieu_hanh", "nv", sal=8_500_000, user="dh.minh")
    v1 = emp("NS0008", "Đỗ Thị Vy (visa HCM)", "visa", "visa", sal=8_000_000)
    v2 = emp("NS0009", "Bùi Văn Nam (visa HCM)", "visa", "visa", sal=7_500_000)
    v3 = emp("NS0010", "Hoàng Lan Anh (visa Hà Nội)", "visa", "visa", office="hanoi", sal=8_000_000)
    h1 = emp("NS0011", "Võ Minh Khang (HDV nội địa)", "huong_dan", "hdv", ct="ctv", card_no="HDV-NĐ-2023-0451", card_type="noi_dia",
             card_expiry=date(2028, 3, 1), member_org=True, ctv_contract=True, advance_limit=5_000_000)
    h2 = emp("NS0012", "Ngô Thu Hà (HDV quốc tế – thẻ hết hạn)", "huong_dan", "hdv", ct="ctv", card_no="HDV-QT-2020-0102", card_type="quoc_te",
             card_expiry=date(2025, 12, 31), member_org=True, ctv_contract=True)
    d1 = emp("NS0013", "Lý Văn Sơn (tài xế)", "doi_xe", "tai_xe", ct="hdld", sal=7_000_000)
    d2 = emp("NS0014", "Trương Công Bình (tài xế)", "doi_xe", "tai_xe", ct="hdld", sal=7_000_000)
    emp("NS0015", "Kế toán tổng hợp", "ketoan", "nv", sal=10_000_000, user="ketoan")
    emp("NS0016", "Nhân sự Hành chính", "hcns", "nv", sal=9_000_000, user="hcns")
    db.flush()
    # Đội xe Đợt 1: mỗi xe có MÃ cố định, và quyền khai thác tách khỏi vòng đời tài sản.
    x1 = Vehicle(plate="50F-009.60", code="XE0001", seats=45, kind="noi_bo", driver_id=d1.id, internal_rate_per_day=3_500_000, op_right="so_huu")
    x2 = Vehicle(plate="50E-957.34", code="XE0002", seats=45, kind="noi_bo", driver_id=d2.id, internal_rate_per_day=3_500_000, op_right="so_huu")
    x3 = Vehicle(plate="50E-955.31", code="XE0003", seats=45, kind="hop_tac", driver_id=None, internal_rate_per_day=0, op_right="hop_tac",
                 partner_name="Đối tác hợp tác (chưa xác minh định danh đầy đủ)", source_note="hồ sơ 3 xe hợp tác")
    x4 = Vehicle(plate="50H-496.23", code="XE0004", seats=45, kind="hop_tac", driver_id=None, internal_rate_per_day=0, op_right="hop_tac",
                 partner_name="Đối tác hợp tác (chưa xác minh định danh đầy đủ)", source_note="hồ sơ 3 xe hợp tác")
    db.add_all([x1, x2, x3, x4]); db.flush()
    seed_fleet_dot1(db, [x1, x2, x3, x4])
    seed_vehicle_rates(db); seed_guide_rates(db)
    seed_companies(db)
    dalat = tours[3]
    db.add(GuideAssignment(tour_id=dalat.id, guide_id=h1.id, days=3, rate_per_day=450_000, assigned_by="dh.lan", status="da_xac_nhan",
                           confirmed_at=datetime.combine(dalat.start_date - timedelta(days=5), datetime.min.time()), report_submitted=True, advance_settled=True))
    db.add(DispatchOrder(tour_id=dalat.id, vehicle_id=x1.id, driver_id=d1.id, date_from=dalat.start_date, date_to=dalat.end_date, internal_price=3 * 3_500_000,
                         created_by="dh.lan", status="hoan_thanh", confirmed_at=datetime.combine(dalat.start_date - timedelta(days=3), datetime.min.time())))
    for i, (cus, mk, me, hd, off, al) in enumerate([("Nguyễn Văn E", "Schengen (Pháp)", "tu_xu_ly", v1, "hcm", False), ("Trần Thị F", "Úc", "gui_doi_tac", v2, "hcm", False),
                                                     ("Công ty G (liên minh)", "Anh", "tu_xu_ly", v1, "hcm", True), ("Lê Văn H", "Hàn Quốc", "tu_xu_ly", v3, "hanoi", False)]):
        db.add(VisaFile(code=f"VS{i+1:04d}", customer_name=cus, market=mk, method=me, handler_id=hd.id, office=off, alliance=al, revenue=2_500_000,
                        status="hoan_thanh", completed_at=dalat.kt_confirmed_at.date() - timedelta(days=i)))
    db.add(VisaFile(code="VS0005", customer_name="Phạm Thị I", market="Nhật Bản", method="tu_xu_ly", handler_id=v2.id, office="hcm", revenue=1_800_000))


# Bảng giá xe (6/5/2026) – anh Tuấn cung cấp 05/9/2026: (tuyến, số ngày, giá xe nội bộ Vietrip–VTD, giá xe hợp tác hỗ trợ từ 5/8/2026)
VEHICLE_RATES = [
    ("Tây Nguyên", 4, 22_000_000, 23_000_000), ("Tây Nguyên – Tà Đùng", 5, 23_000_000, 24_000_000), ("Tuy Hòa – Quy Nhơn", 4, 23_000_000, 24_000_000),
    ("Di sản miền Trung", 7, 38_000_000, 0), ("Di sản miền Trung – New", 7, 44_000_000, 0), ("Tây Nguyên – miền Trung", 7, 31_000_000, 0),
    ("Nha Trang – Đà Lạt", 5, 20_000_000, 20_000_000), ("Nha Trang", 3, 15_000_000, 17_000_000), ("Đà Lạt – Vĩnh Hy", 4, 16_000_000, 18_000_000),
    ("Đà Lạt", 4, 13_000_000, 16_000_000), ("Vĩnh Hy", 3, 14_000_000, 15_000_000), ("Bình Hưng", 3, 14_000_000, 0),
    ("Miền Tây", 3, 16_000_000, 18_000_000), ("Miền Tây 5N", 5, 20_000_000, 22_000_000), ("Buôn Ma Thuột – Nha Trang", 4, 21_000_000, 21_000_000),
    ("Đà Lạt – Phan Thiết", 4, 15_000_000, 17_000_000), ("Hòn Cò 2N", 2, 12_000_000, 13_000_000), ("Hòn Cò 3N", 3, 15_000_000, 15_000_000),
    ("Phan Thiết 2 ngày", 2, 9_000_000, 10_000_000), ("Phan Thiết 3 ngày", 3, 9_000_000, 10_000_000), ("Tây Ninh", 1, 5_000_000, 6_000_000),
    ("Hồ Tràm", 2, 7_000_000, 8_000_000), ("Đà Lạt 4 ngày", 4, 16_000_000, 18_000_000), ("Tà Đùng – Đà Lạt – Phan Thiết", 4, 17_000_000, 18_000_000),
    ("Châu Đốc", 3, 12_000_000, 16_000_000), ("Nam Cát Tiên", 1, 6_000_000, 7_000_000), ("La Ngâu (mới)", 0, 8_000_000, 10_000_000),
    ("Bảo Lộc", 0, 8_000_000, 10_000_000), ("Mỹ Tho 1 ngày", 1, 5_000_000, 5_000_000),
]


# Bảng giá thù lao HDV theo tuyến (đồng/ngày) – giá mới áp dụng 01/9/2026 (giá cũ để đối chiếu), lễ Tết ×2
GUIDE_RATES = [("Phan Thiết", 3, 350000, 500000), ("Đà Lạt 3N2Đ", 3, 350000, 600000), ("Đà Lạt Phan Thiết 4N3Đ", 4, 350000, 500000), ("Đà Lạt Nha Trang 5N4Đ", 5, 350000, 500000),
               ("Đà Lạt Vĩnh Hy 4N3Đ", 4, 350000, 500000), ("Miền Tây 3N2Đ", 3, 400000, 600000), ("Vĩnh Hy 3N2Đ", 3, 400000, 600000), ("Quy Nhơn Phú Yên 4N3Đ", 4, 400000, 700000),
               ("Tây Nguyên Miền Trung 7N6Đ", 7, 500000, 700000), ("Tây Nguyên 4N3Đ", 4, 500000, 800000), ("Nha Trang 3N2Đ", 3, 400000, 600000), ("Tánh Linh Tà Pao 2N1Đ", 2, 400000, 500000),
               ("Hồ Tràm 2N1Đ", 2, 400000, 600000), ("Tây Ninh 1N", 1, 500000, 600000), ("Nam Cát Tiên 1N", 1, 500000, 700000), ("Miền Tây 1N", 1, 500000, 600000),
               ("Buôn Mê – Nha Trang", 4, 400000, 500000), ("Sapa – TQ", 5, 500000, 800000), ("Di sản Miền Trung", 6, 500000, 700000), ("Tây Nguyên – Tà Đùng", 5, 500000, 700000),
               ("Tà Đùng – Đà Lạt – Phan Thiết", 4, 350000, 600000), ("Phú Yên 3N2Đ", 3, 400000, 700000), ("Đà Lạt 3N3Đ", 3.5, 350000, 500000)]


def seed_guide_rates(db):
    if db.execute(select(GuideRate)).scalars().first():
        return
    for route, days, old, new in GUIDE_RATES:
        db.add(GuideRate(route=route, days=days, rate_per_day=new, old_rate_per_day=old, effective_from=date(2026, 9, 1), status="active",
                         signed_chutich=True, signed_tgd=True, proposed_by="seed", note="Bảng giá HDV 23 tuyến – giá mới từ 01/9/2026; lễ Tết ×2"))


def seed_vehicle_rates(db):
    if db.execute(select(VehicleRate)).scalars().first():
        return
    for route, days, ip, pp in VEHICLE_RATES:
        db.add(VehicleRate(route=route, days=days, internal_price=ip, partner_price=pp, effective_from=date(2026, 5, 6), status="active",
                           signed_chutich=True, signed_tgd=True, proposed_by="seed", note="Bảng giá xe 6/5/2026; cột hợp tác áp dụng từ 5/8/2026 (50E-955.31, 50H-496.23)"))

def seed_companies(db):
    """Danh mục pháp nhân của tập đoàn (anh Tuấn cung cấp 06/9/2026) và gắn chủ quản cho xe / HDV.

    Phạm vi hợp nhất chỉ gồm công ty mẹ và công ty con. Công ty liên kết áp dụng phương pháp vốn chủ
    sở hữu; công ty độc lập cùng nhóm quản trị nhưng không hợp nhất – giao dịch với hai nhóm này là
    giao dịch với bên liên quan, phải thuyết minh chứ không loại trừ.

    Tên pháp lý và mã số thuế lấy từ hồ sơ 8 pháp nhân anh Tuấn cung cấp 06/9/2026. Tỷ lệ sở hữu công ty
    con và công ty liên kết lấy từ Thuyết minh I.5a–5b của Báo cáo tài chính hợp nhất giữa niên độ
    6 tháng đầu năm 2026 (A&C soát xét, phát hành 28/8/2026) – không suy đoán.
    """
    from app.models.core import Company
    from app.models.hr import Employee, Vehicle
    DS = [
        # code, tên pháp lý, MST, loại, tỷ lệ sở hữu, đang hoạt động, ghi chú
        ("VTD", "Công ty Cổ phần Vietourist Holdings", "0311273634", "me", 100, True,
         "Công ty mẹ – mã chứng khoán VTD, UPCoM. ĐKDN 26/10/2011, thay đổi lần 16 ngày 12/3/2025"),
        ("VTRIP-VT", "Công ty TNHH Vận tải Vietrip", "0317478116", "con", 100, True,
         "Công ty con duy nhất được hợp nhất; tỷ lệ lợi ích và quyền biểu quyết 100% (BCTC hợp nhất bán niên 2026, TM I.5a). Sở hữu đội xe"),
        ("MEDICSHARE", "Công ty Cổ phần Dịch vụ và Giải pháp Y tế Medicshare", "", "lien_ket", 48.14, True,
         "Liên kết theo BCTC hợp nhất bán niên 2026 (TM I.5b): vốn góp / sở hữu / biểu quyết đều 48,14%. Không có trong danh sách 8 pháp nhân anh Tuấn đưa 06/9 – cần đối chiếu"),
        ("VMUINE", "Công ty Cổ phần Nhà hàng Việt Mũi Né", "", "lien_ket", 40, True,
         "Liên kết theo BCTC hợp nhất bán niên 2026 (TM I.5b): 40%. Không có trong danh sách 8 pháp nhân anh Tuấn đưa 06/9 – cần đối chiếu"),
        ("LANGAU", "Công ty Cổ phần Retreat & Wellness La Ngâu", "3401269941", "lien_ket", 45, True,
         "Liên kết – 45% theo BCTC hợp nhất bán niên 2026 (TM I.5b)"),
        ("HKTN", "Công ty Cổ phần Xã hội Hoàng Kim Tây Nguyên", "5901054923", "lien_ket", 45.33, True,
         "Liên kết – 45,33% theo BCTC hợp nhất bán niên 2026 (TM I.5b)"),
        ("NNX-TN", "Công ty Cổ phần Du lịch Nông nghiệp Xanh Tây Nguyên", "5901168039", "doc_lap", 0, True,
         "Đổi tên từ CTCP Khách sạn Tre Xanh Gia Lai, thay đổi lần 6 ngày 01/10/2025. KHÔNG xuất hiện trên BCTC hợp nhất bán niên 2026"),
        ("LAVENDER", "Công ty TNHH Khách sạn Lavender Đà Lạt", "5801480861", "doc_lap", 0, True,
         "KHÔNG xuất hiện trên BCTC hợp nhất bán niên 2026"),
        ("BUFFALO", "Công ty Cổ phần Việt Nam Buffalotours", "0319297570", "doc_lap", 0, True,
         "KHÔNG xuất hiện trên BCTC hợp nhất bán niên 2026. MST nguồn lưu 9 chữ số, đã thêm 0 đầu – đối chiếu giấy ĐKDN"),
        ("LH-VTR", "Công ty Cổ phần Lữ hành Vietourist", "0316063542", "doc_lap", 0, False,
         "ĐANG TẠM NGƯNG theo anh Tuấn (Drive còn ghi Hoạt động, chưa có thời hạn). KHÔNG xuất hiện trên BCTC hợp nhất bán niên 2026"),
    ]
    have = {c.code: c for c in db.execute(select(Company)).scalars()}
    for code, name, mst, kind, pct, active, note in DS:
        c = have.get(code)
        if c is None:
            db.add(Company(code=code, name=name, tax_code=mst, kind=kind, ownership_pct=pct, active=active, note=note))
        else:
            # cập nhật số liệu đã kiểm chứng (hồ sơ pháp nhân + BCTC hợp nhất) lên bản ghi cũ
            c.name, c.kind, c.active, c.note = name, kind, active, note
            if mst: c.tax_code = mst
            if pct: c.ownership_pct = pct
    db.flush()
    cos = {c.code: c for c in db.execute(select(Company)).scalars()}
    me, vt = cos.get("VTD"), cos.get("VTRIP-VT")
    for code in ("VTRIP-VT", "MEDICSHARE", "VMUINE", "NNX-TN", "LH-VTR", "LANGAU", "HKTN", "LAVENDER", "BUFFALO"):
        c = cos.get(code)
        if c is not None and c.parent_id is None and me is not None and c.code != "VTD":
            c.parent_id = me.id
    n = h = 0
    # KHÔNG suy pháp nhân đứng tên xe từ cờ nội bộ/hợp tác: hồ sơ đội xe 06/9/2026 cho thấy chỉ 1 trong
    # 11 xe đứng tên Vận tải Vietrip, còn lại đứng tên Vietourist. Chủ quản xe nạp từ giấy đăng ký qua
    # POST /fleet/apply (services/drivers.fleet_apply).
    if me:
        # Anh Tuấn chốt 06/9/2026: hướng dẫn viên (kể cả cộng tác viên) VÀ tài xế đều hưởng lương ở công ty
        # mẹ, dù xe thuộc Vận tải Vietrip. Tách bạch: TÀI SẢN (xe) thuộc công ty con, CON NGƯỜI thuộc công ty
        # mẹ – khi hợp nhất, chi phí lương nằm ở sổ mẹ còn khấu hao xe nằm ở sổ con.
        for e in db.execute(select(Employee).where(Employee.company_id == None)).scalars():
            if e.department in ("huong_dan", "doi_xe") or e.position == "tai_xe":
                e.company_id = me.id; h += 1
    db.commit()
    return {"xe": n, "hdv": h}


def seed_fleet_dot1(db, xe: list) -> None:
    """Dữ liệu nền Đợt 1 đội xe: lịch sử biển số cho xe đang có, và vài việc xác minh làm mẫu.

    Cố ý KHÔNG nạp giấy tờ giả: nếu bản demo có sẵn đăng kiểm còn hạn thì màn hình sẽ hiện xanh và người xem
    tưởng hệ thống đã kiểm tra hồ sơ thật. Để trống, xe sẽ ở mức "Chưa đủ dữ liệu" – đúng như thực tế hôm nay.
    """
    for v in xe:
        db.add(VehiclePlate(vehicle_id=v.id, plate=v.plate, source="dữ liệu có sẵn trước Đợt 1",
                            note="Biển đang dùng khi nạp Đợt 1; ngày bắt đầu chưa biết nên để trống thay vì đoán"))
    db.add(FleetVerification(entity="vehicle", vehicle_id=xe[2].id, ref=xe[2].plate,
                             issue="Xác minh định danh đầy đủ của đối tác hợp tác và pháp nhân đứng tên hợp đồng",
                             source="hồ sơ 3 xe hợp tác"))
    db.add(FleetVerification(entity="vehicle", vehicle_id=xe[3].id, ref=xe[3].plate,
                             issue="Đối chiếu tên tài xế giữa hai nguồn và ngày bàn giao xe",
                             source="hồ sơ 3 xe hợp tác"))
    db.flush()
