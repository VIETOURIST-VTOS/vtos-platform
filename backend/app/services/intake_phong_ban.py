"""Bộ nạp dữ liệu cho các phòng ban: nhân sự, khách hàng, booking, sao kê ngân hàng, chấm công.

Tách khỏi app/services/intake.py để phần MÁY (đọc tệp, kiểm tra, chống trùng, nhật ký) không phình lên
theo số phòng ban. Thêm một loại dữ liệu mới là thêm một khai báo ở đây, không sửa luồng nạp.

Mỗi bộ nạp trả về đúng ba thứ cho phần máy:
    kiem(db, r) -> (danh sách lỗi, danh sách cảnh báo, khóa nếu dòng này ĐÃ CÓ)
    nap(db, r, boi) -> mô tả ngắn kết quả ghi được

Ba nguyên tắc riêng của các bộ nạp phòng ban, học từ chỗ dữ liệu hay hỏng nhất:

  1. NẠP CHỈ TẠO MỚI, KHÔNG ĐÈ. Dòng đã có được đếm là "đã có", không ghi chồng. Một tệp nạp nhầm mà
     ghi đè được lương, số tiền hay số tài khoản thì không có cách nào biết giá trị cũ là gì nữa.
  2. KHÔNG NẠP KẾT QUẢ ĐÃ TÍNH. Nạp bảng lương thành phẩm là bỏ qua cả quy trình xác nhận – ở đây chỉ
     nạp ĐẦU VÀO (công thực tế), phần tính vẫn do hệ thống làm và vẫn qua các bước ký.
  3. NẠP KHÔNG TỰ ĐỘNG ĐỐI CHIẾU. Sao kê ngân hàng nạp lên nằm ở trạng thái "chưa khớp"; ghép nó với
     booking nào là việc có người chịu trách nhiệm, không phải hệ quả kèm theo của thao tác tải tệp.
"""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session


# ====================== NHÂN SỰ ======================
def _ns_kiem(db: Session, r):
    from app.models.hr import Employee, DEPARTMENTS, POSITIONS, OFFICES, SALES_GROUPS
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    ma = str(r.get("ma_nv") or "").strip().upper()
    pb = str(r.get("phong_ban") or "").strip()
    if pb and pb not in DEPARTMENTS:
        loi.append(f"Phòng ban '{pb}' không có trong danh mục ({', '.join(DEPARTMENTS)})")
    vt = str(r.get("vi_tri") or "nv").strip()
    if vt and vt not in POSITIONS: loi.append(f"Vị trí '{vt}' không hợp lệ ({', '.join(POSITIONS)})")
    vp = str(r.get("van_phong") or "hcm").strip()
    if vp and vp not in OFFICES: loi.append(f"Văn phòng '{vp}' không hợp lệ ({', '.join(OFFICES)})")
    nk = str(r.get("nhom_kd") or "").strip()
    if nk and nk not in SALES_GROUPS: loi.append(f"Nhóm kinh doanh '{nk}' không hợp lệ")
    lhd = str(r.get("loai_hop_dong") or "hdld").strip()
    if lhd not in ("hdld", "ctv", "doi_tac"): loi.append("Loại hợp đồng phải là hdld / ctv / doi_tac")
    try:
        _ngay(r.get("ngay_vao")); _ngay(r.get("ngay_sinh"))
    except ValueError as ex:
        loi.append(str(ex))
    if _so(r.get("luong_cong_viec")) < 0: loi.append("Lương công việc không được âm")
    if not str(r.get("dien_thoai") or "").strip():
        cb.append("Chưa có điện thoại – hồ sơ nhân sự thiếu số liên hệ thì lệnh điều động không gọi được ai")
    trung = db.execute(select(Employee).where(func.upper(Employee.code) == ma)).scalars().first() if ma else None
    if trung is None and str(r.get("ho_ten") or "").strip():
        # Trùng họ tên KHÔNG chặn (công ty có người trùng tên), nhưng phải nói ra để người nạp nhìn lại.
        cung_ten = db.execute(select(Employee).where(
            func.lower(Employee.full_name) == str(r["ho_ten"]).strip().lower())).scalars().first()
        if cung_ten is not None:
            cb.append(f"Đã có nhân sự cùng tên: {cung_ten.code} – kiểm tra kỹ trước khi tạo hồ sơ thứ hai")
    return loi, cb, (trung.code if trung is not None else None)


def _ns_nap(db: Session, r, boi):
    from app.models.hr import Employee
    from app.services.intake import _so, _ngay
    e = Employee(code=str(r["ma_nv"]).strip().upper(), full_name=str(r["ho_ten"]).strip()[:120],
                 department=str(r["phong_ban"]).strip(), position=str(r.get("vi_tri") or "nv").strip(),
                 title=str(r.get("chuc_danh") or "")[:60], office=str(r.get("van_phong") or "hcm").strip(),
                 sales_group=str(r.get("nhom_kd") or "").strip(),
                 contract_type=str(r.get("loai_hop_dong") or "hdld").strip(),
                 base_salary=_so(r.get("luong_cong_viec")), bhxh_base=_so(r.get("muc_dong_bhxh")),
                 start_date=_ngay(r.get("ngay_vao")), birth_date=_ngay(r.get("ngay_sinh")),
                 phone=str(r.get("dien_thoai") or "")[:30],
                 probation=str(r.get("thu_viec") or "").strip().lower() in ("1", "x", "co", "có", "true"),
                 duties=str(r.get("cong_viec_chinh") or ""))
    db.add(e); db.flush()
    return f"{e.code} – {e.full_name}"


# ====================== KHÁCH HÀNG (LEAD) ======================
def _kh_kiem(db: Session, r):
    from app.models.crm import Lead
    from app.services import leads as LE
    from app.services.zalo import norm_phone
    loi, cb = [], []
    ph = norm_phone(str(r.get("dien_thoai") or ""))
    if len(ph) < 7:
        loi.append(f"Số điện thoại không đọc được: {r.get('dien_thoai')!r}. Khách không có số thì không "
                   "chăm sóc được và cũng không đối chiếu được với booking sau này.")
    elif len(ph) < 10:
        cb.append(f"Số điện thoại thiếu chữ số ({ph}) – vẫn nạp nhưng đánh dấu để sửa lại")
    kenh = LE.canon_channel(str(r.get("kenh") or ""))
    thang = LE.month_of(r.get("thang") or r.get("ngay_nhan") or "")
    trung = None
    if len(ph) >= 7:
        trung = db.execute(select(Lead).where(Lead.phone == ph, Lead.lead_month == thang,
                                              Lead.channel == kenh)).scalars().first()
    return loi, cb, (f"{ph}/{thang}/{kenh}" if trung is not None else None)


def _kh_nap(db: Session, r, boi):
    from app.services import leads as LE
    l, _ = LE.upsert_lead(db, boi, {"phone": r.get("dien_thoai"), "name": r.get("ho_ten"),
                                    "channel": r.get("kenh"), "lead_month": r.get("thang") or r.get("ngay_nhan"),
                                    "campaign": r.get("chien_dich"), "interest": r.get("tour_quan_tam"),
                                    "note": r.get("ghi_chu")})
    return f"{l.phone} – {l.name or 'chưa có tên'} ({l.channel}, {l.lead_month})"


# ====================== BOOKING ======================
def _bk_tour(db: Session, ma):
    from app.models.core import Tour
    ma = str(ma or "").strip()
    return db.execute(select(Tour).where(func.lower(Tour.code) == ma.lower())).scalars().first() if ma else None


def _bk_sales(db: Session, ten):
    from app.models.core import User
    ten = str(ten or "").strip()
    if not ten: return None
    return db.execute(select(User).where(func.lower(User.username) == ten.lower())).scalars().first()


def _bk_kiem(db: Session, r):
    from app.models.core import Booking
    from app.services.intake import _so
    loi, cb = [], []
    ma = str(r.get("ma_booking") or "").strip()
    t = _bk_tour(db, r.get("ma_tour"))
    if t is None:
        loi.append(f"Không có tour mã '{r.get('ma_tour')}' – booking phải gắn tour, nếu không thì doanh thu "
                   "này không vào được kết quả của chuyến nào")
    if str(r.get("sales") or "").strip() and _bk_sales(db, r.get("sales")) is None:
        loi.append(f"Không có tài khoản nhân viên bán '{r.get('sales')}'")
    khach = _so(r.get("so_khach")) or (_so(r.get("nguoi_lon")) + _so(r.get("tre_em")) + _so(r.get("em_be")))
    if khach <= 0: loi.append("Số khách phải lớn hơn 0")
    tien = _so(r.get("tien_tour")); giam = _so(r.get("giam_gia")); thu = _so(r.get("da_thu"))
    if tien <= 0: loi.append("Tiền tour phải lớn hơn 0")
    if giam > tien: loi.append("Giảm giá lớn hơn tiền tour")
    if thu > tien - giam:
        loi.append(f"Đã thu {thu:,.0f} lớn hơn số phải thu {tien - giam:,.0f} – phần dôi ra là tiền bảo lưu "
                   "hay thu nhầm booking khác, phải làm rõ trước khi ghi vào sổ")
    if thu > 0:
        cb.append("Có số đã thu: nạp ở đây chỉ ghi vào booking, KHÔNG sinh phiếu thu và không đối chiếu "
                  "ngân hàng – phiếu thu vẫn phải đi đường thu tiền")
    trung = db.execute(select(Booking).where(func.lower(Booking.code) == ma.lower())).scalars().first() if ma else None
    return loi, cb, (trung.code if trung is not None else None)


def _bk_nap(db: Session, r, boi):
    from app.models.core import Booking, User
    from app.services import bookings as BK
    from app.services.intake import _so, _ngay
    t = _bk_tour(db, r["ma_tour"])
    s = _bk_sales(db, r.get("sales"))
    nguoi = db.execute(select(User).where(func.lower(User.username) == str(boi).lower())).scalars().first()
    sid = (s or nguoi).id if (s or nguoi) is not None else t.operator_id
    b = Booking(code=str(r["ma_booking"]).strip()[:30], tour_id=t.id, request_id=0,
                sales_id=sid, created_by=(nguoi.id if nguoi is not None else sid),
                customer_name=str(r.get("ten_khach") or "").strip()[:120],
                customer_phone=str(r.get("dien_thoai") or "")[:30],
                customer_email=str(r.get("email") or "")[:120],
                source=str(r.get("nguon") or "nap_tep")[:60],
                pax=int(_so(r.get("so_khach")) or (_so(r.get("nguoi_lon")) + _so(r.get("tre_em")) + _so(r.get("em_be")))),
                adl=int(_so(r.get("nguoi_lon"))), chd=int(_so(r.get("tre_em"))), inf=int(_so(r.get("em_be"))),
                amount=_so(r.get("tien_tour")), discount=_so(r.get("giam_gia")), paid=_so(r.get("da_thu")),
                care_note=str(r.get("ghi_chu") or ""), sla_minutes=0, sla_ok=True,
                company_id=t.company_id)
    ng = _ngay(r.get("ngay_tao"))
    if ng: b.created_at = datetime.combine(ng, datetime.min.time())
    db.add(b); db.flush()
    BK.init_terms(db, b, t)
    BK.refresh_status(b)
    return f"{b.code} – {b.customer_name} · {b.amount:,.0f} đ"


# ====================== SAO KÊ NGÂN HÀNG ======================
def _sk_ma(r):
    from app.services.intake import _chuan_cot
    return f"saoke:{_chuan_cot(r.get('ngan_hang'))}:{str(r.get('ma_gd') or '').strip()}"


def _sk_kiem(db: Session, r):
    from app.models.payments import BankTransaction
    from app.services.intake import _so
    loi, cb = [], []
    if not str(r.get("ma_gd") or "").strip():
        loi.append("Thiếu mã giao dịch của ngân hàng – không có mã thì nạp lại cùng tệp sẽ nhân đôi tiền")
    if not str(r.get("ngan_hang") or "").strip(): loi.append("Thiếu tên ngân hàng")
    loai = str(r.get("loai") or "").strip().lower()
    if loai not in ("vao", "ra", "in", "out", "có", "nợ", "co", "no"):
        loi.append("Loại phải ghi 'vao' (tiền vào) hoặc 'ra' (tiền ra)")
    if _so(r.get("so_tien")) <= 0:
        loi.append("Số tiền phải lớn hơn 0 – tiền ra ghi dương và đánh dấu ở cột loại, không ghi số âm")
    try:
        _sk_thoi_diem(r)
    except ValueError as ex:
        loi.append(str(ex))
    if not str(r.get("noi_dung") or "").strip():
        cb.append("Không có nội dung chuyển khoản – dòng này gần như chắc chắn phải khớp tay")
    ma = _sk_ma(r)
    trung = db.execute(select(BankTransaction).where(BankTransaction.sepay_id == ma)).scalars().first()
    return loi, cb, (trung.sepay_id if trung is not None else None)


def _sk_thoi_diem(r):
    from app.services.intake import _ngay
    v = r.get("thoi_diem") or r.get("ngay")
    if isinstance(v, datetime): return v
    s = str(v or "").strip()
    for f in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M"):
        try: return datetime.strptime(s, f)
        except ValueError: continue
    d = _ngay(v)
    if d is None: raise ValueError("Thiếu thời điểm giao dịch")
    return datetime.combine(d, datetime.min.time())


def _sk_nap(db: Session, r, boi):
    from app.models.payments import BankTransaction
    from app.services.intake import _so
    loai = str(r.get("loai") or "").strip().lower()
    vao = loai in ("vao", "in", "có", "co")
    t = BankTransaction(sepay_id=_sk_ma(r), gateway=str(r.get("ngan_hang") or "")[:40],
                        account_number=str(r.get("so_tai_khoan") or "")[:40],
                        transaction_date=_sk_thoi_diem(r), transfer_type="in" if vao else "out",
                        amount=_so(r.get("so_tien")), content=str(r.get("noi_dung") or ""),
                        reference_code=str(r.get("ma_tham_chieu") or "")[:80],
                        raw={"nguon": "nap_sao_ke", "boi": boi},
                        # Nạp sao kê KHÔNG khớp giúp: ghép tiền với booking là việc có người chịu trách
                        # nhiệm, không phải hệ quả kèm theo của thao tác tải tệp lên.
                        match_status="chua_khop")
    db.add(t); db.flush()
    return f"{t.gateway} · {'vào' if vao else 'ra'} {(t.amount or 0):,.0f} đ · {t.transaction_date:%d/%m/%Y}"


# ====================== CHẤM CÔNG CHO BẢNG LƯƠNG ======================
def _cc_kiem(db: Session, r):
    from app.models.hr import Employee
    from app.services import hr as H, luong as L
    from app.services.intake import _so
    loi, cb = [], []
    ky = str(r.get("ky") or "").strip()
    if len(ky) != 7 or ky[4] != "-": loi.append("Kỳ phải ghi dạng 2026-08")
    ma = str(r.get("ma_nv") or "").strip().upper()
    e = db.execute(select(Employee).where(func.upper(Employee.code) == ma)).scalars().first() if ma else None
    if e is None: loi.append(f"Không có nhân sự mã '{ma}'")
    elif L.che_do_cong(e) != L.CHAM_CONG:
        loi.append(f"{e.code} không thuộc chế độ chấm công theo ngày – nhập công cho người này không có "
                   "tác dụng lên lương, và dễ làm người đọc tưởng đã nhập đủ")
    c = _so(r.get("cong_thuc_te"))
    if c < 0 or c > 31: loi.append("Công thực tế phải nằm trong khoảng 0 – 31 ngày")
    trung = None
    if not loi:
        run = db.execute(select(H.PayrollRun).where(H.PayrollRun.period == ky)).scalars().first()
        if run is not None and run.status != "nhap":
            loi.append(f"Bảng lương kỳ {ky} đã qua bước xác nhận ({run.status}) – sửa công phải đi đường "
                       "điều chỉnh, không nạp đè")
        elif run is not None and str(ma) in ((run.inputs or {}).get("cong_thuc_te") or {}):
            trung = f"{ky}/{ma}"
    return loi, cb, trung


def _cc_nap(db: Session, r, boi):
    from app.services import hr as H
    from app.services.intake import _so
    ky = str(r["ky"]).strip(); ma = str(r["ma_nv"]).strip().upper(); c = _so(r.get("cong_thuc_te"))
    run = H.get_or_draft(db, ky)
    cur = dict(run.inputs or {})
    cur["cong_thuc_te"] = {**(cur.get("cong_thuc_te") or {}), ma: c}
    if str(r.get("cong_chuan") or "").strip(): cur["cong_chuan"] = _so(r.get("cong_chuan"))
    run.inputs = cur          # gán lại cả dict để SQLAlchemy nhìn thấy thay đổi trong cột JSON
    db.flush()
    return f"{ky} · {ma} · {c:g} công"


# ====================== HƯỚNG DẪN VIÊN ======================
def _hdv_kiem(db: Session, r):
    from app.models.hr import Employee
    from app.services.intake import _so, _ngay
    loi, cb = [], []
    the = str(r.get("the_so") or "").strip()
    if not the:
        loi.append("Thiếu số thẻ hướng dẫn viên – không có thẻ thì không hành nghề được, và cũng không "
                   "có khóa nào để nạp lại tệp mà không nhân đôi hồ sơ")
    lt = str(r.get("the_loai") or "").strip()
    if lt and lt not in ("noi_dia", "quoc_te"):
        loi.append("Loại thẻ phải là noi_dia hoặc quoc_te")
    try:
        het = _ngay(r.get("the_het_han"))
        if het is None:
            loi.append("Thiếu ngày hết hạn thẻ")
        else:
            from datetime import date as _d
            if het < _d.today():
                cb.append(f"Thẻ đã hết hạn ngày {het:%d/%m/%Y} – nạp được nhưng cổng 13 sẽ chặn chào chuyến")
    except ValueError as ex:
        loi.append(str(ex))
    if str(r.get("hoi_vien") or "").strip().lower() not in ("1", "x", "co", "có", "true", "roi", "rồi"):
        cb.append("Chưa ghi nhận hội viên tổ chức xã hội – nghề nghiệp: thiếu điều kiện thứ ba của "
                  "Điều 58 Luật Du lịch")
    if _so(r.get("han_muc_tam_ung")) < 0: loi.append("Hạn mức tạm ứng không được âm")
    trung = db.execute(select(Employee).where(Employee.card_no == the)).scalars().first() if the else None
    return loi, cb, (trung.card_no if trung is not None else None)


def _hdv_nap(db: Session, r, boi):
    from app.models.hr import Employee
    from app.services import hr as H
    from app.services.intake import _so, _ngay
    ma = str(r.get("ma_nv") or "").strip().upper() or H.next_code(db, Employee, "NS")
    co = str(r.get("hop_dong_cong_tac") or "").strip().lower() in ("1", "x", "co", "có", "true", "roi", "rồi")
    e = Employee(code=ma, full_name=str(r["ho_ten"]).strip()[:120], department="huong_dan",
                 position="hdv", contract_type="ctv",     # toàn bộ HDV là cộng tác viên (chốt 07/9/2026)
                 phone=str(r.get("dien_thoai") or "")[:30],
                 card_no=str(r["the_so"]).strip()[:30], card_type=str(r.get("the_loai") or "")[:20],
                 card_expiry=_ngay(r.get("the_het_han")),
                 member_org=str(r.get("hoi_vien") or "").strip().lower() in
                            ("1", "x", "co", "có", "true", "roi", "rồi"),
                 ctv_contract=co, advance_limit=_so(r.get("han_muc_tam_ung")),
                 duties=str(r.get("tuyen_phu_trach") or ""))
    db.add(e); db.flush()
    return f"{e.code} – {e.full_name} · thẻ {e.card_no}"


# ====================== KHAI BÁO ======================
def bo_nap(_c) -> dict:
    from app.services import quyet_toan_tour as QTT
    """Trả về các bộ nạp phòng ban. Nhận hàm _c của app/services/intake.py để mô tả cột cùng một kiểu."""
    from app.models.hr import DEPARTMENTS, POSITIONS, OFFICES
    return {
        "nhan_su": {
            "bang_dich": "employees", "phong_ban": "hcns",
            "ten": "Hồ sơ nhân sự",
            "mo_ta": "Danh sách nhân sự. Nạp chỉ TẠO MỚI: mã đã có thì bỏ qua, không ghi đè lương hay "
                     "phòng ban của người đang làm việc.",
            "khoa_chong_trung": "Mã nhân viên",
            "cot": [_c("ma_nv", "Mã nhân viên", True, vi_du="NS0142"),
                    _c("ho_ten", "Họ và tên", True, vi_du="Nguyễn Văn A"),
                    _c("phong_ban", "Phòng ban", True, vi_du="kd_le",
                       ghi_chu=" / ".join(DEPARTMENTS)),
                    _c("vi_tri", "Vị trí", vi_du="nv", ghi_chu=" / ".join(POSITIONS)),
                    _c("chuc_danh", "Chức danh trên bảng lương", vi_du="NVKD 2"),
                    _c("cong_viec_chinh", "Công việc chính", vi_du="Tuyến miền Trung"),
                    _c("van_phong", "Văn phòng", vi_du="hcm", ghi_chu=" / ".join(OFFICES)),
                    _c("nhom_kd", "Nhóm kinh doanh", vi_du="KD1"),
                    _c("loai_hop_dong", "Loại hợp đồng", vi_du="hdld", ghi_chu="hdld / ctv / doi_tac"),
                    _c("luong_cong_viec", "Lương công việc", kieu="so", vi_du="8000000"),
                    _c("muc_dong_bhxh", "Mức đóng BHXH", kieu="so",
                       ghi_chu="khác lương công việc – ghi đúng mức đang đóng"),
                    _c("ngay_vao", "Ngày vào làm", kieu="ngay", vi_du="01/03/2025"),
                    _c("ngay_sinh", "Ngày sinh", kieu="ngay"),
                    _c("dien_thoai", "Điện thoại"),
                    _c("thu_viec", "Thử việc", ghi_chu="ghi x nếu đang thử việc (hưởng 85%)")],
            "kiem": _ns_kiem, "nap": _ns_nap,
        },
        "khach_hang": {
            "bang_dich": "leads", "phong_ban": "kd_le",
            "ten": "Khách hàng / nguồn khách",
            "mo_ta": "Danh sách khách theo kênh và theo tháng. Cùng số điện thoại trong cùng tháng và cùng "
                     "kênh chỉ tính một khách – nạp lại tệp không thổi phồng số lead.",
            "khoa_chong_trung": "Số điện thoại + tháng + kênh",
            "cot": [_c("dien_thoai", "Số điện thoại", True, vi_du="0903123456"),
                    _c("ho_ten", "Tên khách", vi_du="Chị Lan"),
                    _c("kenh", "Kênh", True, vi_du="Hotline 1",
                       ghi_chu="Hotline 1 / Đặt tour web / VCHAT / Tiktok Ads / Zalo OA / Facebook / Khách cũ…"),
                    _c("thang", "Tháng phát sinh", vi_du="2026-08", ghi_chu="để trống thì lấy tháng hiện tại"),
                    _c("chien_dich", "Chiến dịch"), _c("tour_quan_tam", "Tour quan tâm"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _kh_kiem, "nap": _kh_nap,
        },
        "booking": {
            "bang_dich": "bookings", "phong_ban": "kd_le",
            "ten": "Booking khách đoàn / khách lẻ",
            "mo_ta": "Booking gắn vào tour đã có. Số đã thu chỉ ghi nhận trên booking, KHÔNG sinh phiếu thu "
                     "và không đối chiếu ngân hàng thay cho kế toán.",
            "khoa_chong_trung": "Mã booking",
            "cot": [_c("ma_booking", "Mã booking", True, vi_du="BK26080012"),
                    _c("ma_tour", "Mã tour", True, vi_du="DL2609-01"),
                    _c("ten_khach", "Tên khách", True, vi_du="Nguyễn Thị B"),
                    _c("dien_thoai", "Điện thoại"), _c("email", "Email"),
                    _c("nguon", "Nguồn khách", vi_du="Hotline 1"),
                    _c("sales", "Tài khoản nhân viên bán", ghi_chu="tên đăng nhập trên VTOS; "
                                                                   "để trống thì ghi tên người nạp"),
                    _c("so_khach", "Số khách", kieu="so", ghi_chu="để trống thì cộng người lớn + trẻ em + em bé"),
                    _c("nguoi_lon", "Người lớn", kieu="so"), _c("tre_em", "Trẻ em", kieu="so"),
                    _c("em_be", "Em bé", kieu="so"),
                    _c("tien_tour", "Tiền tour", True, kieu="so", vi_du="24000000"),
                    _c("giam_gia", "Giảm giá", kieu="so"),
                    _c("da_thu", "Đã thu", kieu="so", ghi_chu="không được lớn hơn tiền tour trừ giảm giá"),
                    _c("ngay_tao", "Ngày tạo booking", kieu="ngay"),
                    _c("ghi_chu", "Ghi chú chăm sóc")],
            "kiem": _bk_kiem, "nap": _bk_nap,
        },
        "sao_ke_ngan_hang": {
            "bang_dich": "bank_transactions", "phong_ban": "ketoan",
            "ten": "Sao kê ngân hàng",
            "mo_ta": "Sao kê tải từ ngân hàng. Dòng nạp lên nằm ở trạng thái CHƯA KHỚP – ghép với booking "
                     "là bước riêng có người xác nhận, không tự động theo tệp.",
            "khoa_chong_trung": "Ngân hàng + mã giao dịch",
            "cot": [_c("ma_gd", "Mã giao dịch", True, vi_du="FT26240012345",
                       ghi_chu="mã/số bút toán ngân hàng in trên sao kê – khóa chống nạp trùng"),
                    _c("ngan_hang", "Ngân hàng", True, vi_du="TPBank"),
                    _c("so_tai_khoan", "Số tài khoản", vi_du="01811267101"),
                    _c("thoi_diem", "Thời điểm", True, kieu="ngay", vi_du="31/08/2026 14:20"),
                    _c("loai", "Loại", True, vi_du="vao", ghi_chu="vao = tiền vào, ra = tiền ra"),
                    _c("so_tien", "Số tiền", True, kieu="so", vi_du="24000000",
                       ghi_chu="luôn ghi số dương, chiều tiền đọc ở cột loại"),
                    _c("noi_dung", "Nội dung chuyển khoản"),
                    _c("ma_tham_chieu", "Mã tham chiếu")],
            "kiem": _sk_kiem, "nap": _sk_nap,
        },
        "huong_dan_vien": {
            "bang_dich": "employees", "phong_ban": "huong_dan",
            "ten": "Hướng dẫn viên cộng tác",
            "mo_ta": "Danh sách HDV. Nạp luôn ghi loại hợp đồng là cộng tác viên – toàn bộ HDV đã chuyển "
                     "sang cộng tác viên từ 07/9/2026. Cố ý KHÔNG có bộ nạp bảng đơn giá tuyến: đơn giá "
                     "phải có chữ ký Chủ tịch và Tổng giám đốc, một tệp tải lên không thay được chữ ký.",
            "khoa_chong_trung": "Số thẻ hướng dẫn viên",
            "cot": [_c("the_so", "Số thẻ HDV", True, vi_du="HDV-NĐ-2023-0451",
                       ghi_chu="khóa chống trùng – mỗi thẻ chỉ có một người"),
                    _c("ho_ten", "Họ và tên", True, vi_du="Võ Minh Khang"),
                    _c("ma_nv", "Mã nhân viên", ghi_chu="để trống thì hệ thống tự cấp"),
                    _c("the_loai", "Loại thẻ", vi_du="noi_dia", ghi_chu="noi_dia / quoc_te"),
                    _c("the_het_han", "Ngày hết hạn thẻ", True, kieu="ngay", vi_du="31/12/2028"),
                    _c("hoi_vien", "Hội viên tổ chức XH – nghề nghiệp",
                       ghi_chu="ghi x nếu đã là hội viên (điều kiện thứ ba, Điều 58 Luật Du lịch)"),
                    _c("hop_dong_cong_tac", "Đã ký hợp đồng cộng tác", ghi_chu="ghi x nếu đã ký"),
                    _c("dien_thoai", "Điện thoại"),
                    _c("tuyen_phu_trach", "Tuyến phụ trách", vi_du="Miền Trung, Tây Nguyên"),
                    _c("han_muc_tam_ung", "Hạn mức tạm ứng", kieu="so", vi_du="5000000")],
            "kiem": _hdv_kiem, "nap": _hdv_nap,
        },
        "quyet_toan_tour": {
            "bang_dich": "tour_settlements", "phong_ban": "dieu_hanh",
            "lo": True,          # kiểm và nạp cả tệp một lần: tệp gốc là workbook nhiều sheet
            "ten": "Quyết toán tour theo điều hành",
            "mo_ta": "Tệp quyết toán tháng của Điều hành – mỗi điều hành viên một sheet, thêm sheet "
                     "khách lẻ do sale tự xử lý. Sheet Tổng hợp bị bỏ qua (số cộng lại). Ô giá vốn "
                     "bằng 0 đọc thành CHƯA CÓ SỐ, không phải 0 đồng.",
            "khoa_chong_trung": "Mã tour",
            "cot": [_c("ma_tour", "Mã tour", True, vi_du="MICEDL3N2D.03170726"),
                    _c("ten_tour", "Tên tour", vi_du="ĐÀ LẠT 3 NGÀY 2 ĐÊM"),
                    _c("ngay_kh", "Ngày KH", kieu="ngay", vi_du="17/07/2026"),
                    _c("ngay_kt", "Ngày KT", True, kieu="ngay", vi_du="19/07/2026",
                       ghi_chu="ngày kết thúc quyết định chuyến thuộc kỳ nào"),
                    _c("doanh_thu", "Doanh thu", True, kieu="tien", min=0),
                    _c("gia_von", "Giá vốn", kieu="tien", min=0,
                       ghi_chu="để TRỐNG nếu chưa có số – đừng ghi 0"),
                    _c("trang_thai_qt", "Trạng thái QT", vi_du="Đã quyết toán"),
                    _c("sale", "Sale", ghi_chu="chỉ có ở sheet khách lẻ")],
            "kiem": QTT.kiem, "nap": QTT.nap,      # không dùng ở chế độ lô, giữ để khai báo đủ
            "kiem_lo": QTT.kiem, "nap_lo": QTT.nap, "doc_tep": QTT.doc_tep,
        },
        "cham_cong": {
            "bang_dich": "payroll_runs", "phong_ban": "hcns",
            "ten": "Chấm công cho bảng lương",
            "mo_ta": "Công thực tế theo kỳ để hệ thống TÍNH bảng lương. Cố ý không có bộ nạp 'bảng lương "
                     "thành phẩm': nạp thẳng số lương đã tính là bỏ qua toàn bộ các bước xác nhận và ký. "
                     "Kỳ đã qua bước xác nhận thì không nạp được nữa.",
            "khoa_chong_trung": "Kỳ + mã nhân viên",
            "cot": [_c("ky", "Kỳ lương", True, vi_du="2026-08"),
                    _c("ma_nv", "Mã nhân viên", True, vi_du="NS0142"),
                    _c("cong_thuc_te", "Công thực tế", True, kieu="so", vi_du="24"),
                    _c("cong_chuan", "Công chuẩn của kỳ", kieu="so",
                       ghi_chu="chỉ cần ghi ở một dòng; để trống thì lấy tham số hệ thống"),
                    _c("ghi_chu", "Ghi chú")],
            "kiem": _cc_kiem, "nap": _cc_nap,
        },
    }
