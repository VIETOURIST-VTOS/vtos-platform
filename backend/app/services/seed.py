"""Dữ liệu mẫu để chạy thử. Mật khẩu mọi tài khoản: 123456 (đổi trước khi chạy thật)."""
from datetime import date, datetime, timedelta
from app.core.security import hash_password
from sqlalchemy import select
from app.models.core import User, Tour, ServiceRequest, Booking
from app.models.hr import GuideRate, Employee, VisaFile, GuideAssignment, Vehicle, VehicleRate, DispatchOrder
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
    pw = hash_password("123456")
    users = {}
    for un, name, role, dept in USERS:
        u = User(username=un, full_name=name, role=role, department=dept, password_hash=pw)
        db.add(u); users[un] = u
    db.flush()
    today = date.today()
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
        # Tour lẻ đã khóa tháng này (để bảng lương nháp có số)
        Tour(code="DL-0825", name="Đà Lạt 3N2Đ", tour_type="le_noi_dia",
             start_date=today - timedelta(days=20), end_date=today - timedelta(days=18), operator_id=lan.id,
             price_per_pax=2_690_000, fixed_cost=21_000_000, var_cost_per_pax=1_050_000, planned_pax=28,
             rest_stops="Bảo Lộc", status="khoa", confirmed_by="tp.dieuhanh", approved_by="tgd",
             actual_revenue=75_320_000, actual_cost=50_400_000, promo_value=1_500_000,
             closed_at=datetime.combine(today - timedelta(days=16), datetime.min.time()),
             kt_confirmed_at=datetime.combine(today - timedelta(days=14), datetime.min.time()),
             cntt_checked_at=datetime.combine(today - timedelta(days=13), datetime.min.time())),
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
    x1 = Vehicle(plate="50F-009.60", seats=45, kind="noi_bo", driver_id=d1.id, internal_rate_per_day=3_500_000)
    x2 = Vehicle(plate="50E-957.34", seats=45, kind="noi_bo", driver_id=d2.id, internal_rate_per_day=3_500_000)
    x3 = Vehicle(plate="50E-955.31", seats=45, kind="hop_tac", driver_id=None, internal_rate_per_day=0)
    x4 = Vehicle(plate="50H-496.23", seats=45, kind="hop_tac", driver_id=None, internal_rate_per_day=0)
    db.add_all([x1, x2, x3, x4]); db.flush()
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

    Tên pháp lý đầy đủ, mã số thuế và tỷ lệ sở hữu để Kế toán bổ sung; hệ thống không tự suy đoán.
    """
    from app.models.core import Company
    from app.models.hr import Employee, Vehicle
    DS = [
        ("VTD", "Công ty Cổ phần Du lịch Vietourist (Vietourist Holdings)", "me", 100, True, "Công ty mẹ – mã chứng khoán VTD, niêm yết UPCoM"),
        ("VTRIP-VT", "Công ty TNHH Vận tải Vietrip", "con", 100, True, "Sở hữu đội xe; cho công ty mẹ thuê xe là giao dịch nội bộ, loại trừ khi hợp nhất"),
        ("NNX-TN", "Du lịch Nông nghiệp Xanh Tây Nguyên", "doc_lap", 0, True, "Bổ sung tên pháp lý đầy đủ, MST và tỷ lệ sở hữu"),
        ("LH-VTR", "Lữ hành Vietourist", "doc_lap", 0, False, "ĐANG TẠM NGƯNG hoạt động; giữ hồ sơ lịch sử"),
        ("LANGAU", "Retreat & Wellness La Ngâu", "lien_ket", 0, True, "Vốn chủ sở hữu – cần tỷ lệ sở hữu để áp dụng phương pháp"),
        ("HKTN", "Xã hội Hoàng Kim Tây Nguyên", "lien_ket", 0, True, "Vốn chủ sở hữu – cần tỷ lệ sở hữu để áp dụng phương pháp"),
        ("LAVENDER", "Khách sạn Lavender Đà Lạt", "doc_lap", 0, True, "Bổ sung tên pháp lý đầy đủ, MST và tỷ lệ sở hữu"),
        ("BUFFALO", "Việt Nam Buffalotours", "doc_lap", 0, True, "Bổ sung tên pháp lý đầy đủ, MST và tỷ lệ sở hữu"),
    ]
    have = {c.code: c for c in db.execute(select(Company)).scalars()}
    for code, name, kind, pct, active, note in DS:
        if code in have: continue
        db.add(Company(code=code, name=name, kind=kind, ownership_pct=pct, active=active, note=note))
    db.flush()
    cos = {c.code: c for c in db.execute(select(Company)).scalars()}
    me, vt = cos.get("VTD"), cos.get("VTRIP-VT")
    for code in ("VTRIP-VT", "NNX-TN", "LH-VTR", "LANGAU", "HKTN", "LAVENDER", "BUFFALO"):
        c = cos.get(code)
        if c is not None and c.parent_id is None and me is not None and c.code != "VTD":
            c.parent_id = me.id
    n = h = 0
    if vt:
        for v in db.execute(select(Vehicle).where(Vehicle.company_id == None)).scalars():
            if v.kind == "noi_bo":            # xe hợp tác là xe thuê ngoài, không thuộc pháp nhân trong tập đoàn
                v.company_id = vt.id; n += 1
    if me:
        # Anh Tuấn chốt 06/9/2026: HDV vẫn thuộc công ty mẹ, kể cả khi chuyển sang cộng tác viên
        for e in db.execute(select(Employee).where(Employee.company_id == None, Employee.department == "huong_dan")).scalars():
            e.company_id = me.id; h += 1
    db.commit()
    return {"xe": n, "hdv": h}
