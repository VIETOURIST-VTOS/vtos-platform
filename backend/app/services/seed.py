"""Dữ liệu mẫu để chạy thử. Mật khẩu mọi tài khoản: 123456 (đổi trước khi chạy thật)."""
from datetime import date, datetime, timedelta
from app.core.security import hash_password
from sqlalchemy import select
from app.models.core import User, Tour, ServiceRequest, Booking
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
    core.audit(db, "seed", "cntt", "khoi_tao_du_lieu_mau", "system", after={"users": len(USERS), "tours": len(tours)})
    db.commit()
    core.run_robots(db)
