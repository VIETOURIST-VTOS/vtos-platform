"""Đồng bộ Vietrip → VTOS (robot chuyển đổi dữ liệu, mục 11.3 Thiết kế).

Bước 1 – nạp thô: mọi bản ghi Vietrip lưu vào vt_records (idempotent theo entity + vietrip_id).
Bước 2 – ánh xạ: tour → tours (+ dòng chi phí), booking → bookings, phiếu thu → receipts, chi NCC → payment_requests (đã chi),
         user → users + employees, xe → vehicles. Giữ mã Vietrip trong trường tham chiếu để tra ngược. Không sinh bút toán
         (số dư đầu kỳ lấy từ MISA/BCTC khi cắt chuyển) – các bản ghi nhập đánh dấu imported/source=vietrip.
"""
import re, secrets
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, User, Product, TourEvent
from app.models.payments import Receipt
from app.models.ops import PaymentRequest
from app.models.hr import Employee, Vehicle
from app.models.vietrip import VtRecord, TourCostLine
from app.core.security import hash_password
from app.services import rules as R

ENTITIES = ("tour", "booking", "receipt", "supplier_payment", "user", "vehicle", "proposal", "settlement", "product")

# KS-12 · 21/10/2026 — LOẠI KÉO VỀ MÀ CỐ Ý CHƯA CÓ LỚP ÁP DỤNG, khai Ở ĐÂY kèm lý do.
#
# VÌ SAO CÓ BẢNG NÀY. `proposal` nằm trong `ENTITIES` nên robot kéo về đều — 24 dòng tính tới
# 17/10/2026 — nhưng KHÔNG hàm nào đọc `VtRecord.entity == "proposal"`, tức là không ai áp.
# Tự nó đã tệ; chỗ tệ hơn là con số đáng lẽ phải kêu lên thì được viết để loại nó ra:
#
#     out["remaining"] = ...where(applied == False, VtRecord.entity != "proposal", ...)
#
# Một chữ `!= "proposal"` giấu trong câu truy vấn, và ô «còn tồn» báo 0 trong khi 24 dòng nằm im.
# Đó là kiểu hỏng tệ nhất của cả hệ: nó trông y hệt lúc không có gì để làm.
#
# Từ nay chỗ loại trừ DUY NHẤT là bảng này, và nó phải mang LÝ DO đọc được. `apply_all` kê thẳng
# số dòng của từng loại ở đây ra cạnh `remaining`, nên loại nào chưa có lớp áp thì hiện lên bàn
# giám sát chứ không biến mất. `test_ks12` canh: mỗi loại trong `ENTITIES` phải HOẶC có lớp áp,
# HOẶC đứng tên ở đây.
KHONG_AP_DUNG: dict[str, str] = {
    "proposal": ("Đề nghị chi đang chờ duyệt bên Vietrip. CHƯA dựng lớp áp vì `supplier_payment` "
                 "đã tạo `PaymentRequest` rồi — nếu hai loại này là cùng một đề nghị ở hai giai "
                 "đoạn thì áp cả hai sẽ ĐẾM ĐÔI tiền ra. Phải đối chiếu trên hệ thật trước, và "
                 "đó là một vòng riêng có người quyết, không phải việc đoán."),
}
DEPT_MAP = {"Kế toán": ("ketoan", "ketoan"), "Điều hành": ("dieu_hanh", "nv_dh"), "Tour": ("kd_le", "nv_kd"), "Tour MICE": ("kd_doan", "nv_kd"), "Hướng dẫn": ("huong_dan", "nv_kd"),
            "CSKH": ("marketing", "nv_kd"), "IT": ("cntt", "cntt"), "Giám đốc": ("ban_tgd", "tgd"), "Kinh doanh": ("kd_le", "nv_kd"), "Marketing": ("marketing", "nv_kd"), "ĐỐI TÁC": ("kd_le", "nv_kd")}
STATUS_TEXT = {"KC": "đã xác nhận", "QQ": "chờ duyệt", "XX": "từ chối/hủy", "GD": "GĐ duyệt"}


def _dt(s):
    if not s: return None
    try: return datetime.fromisoformat(str(s)[:19])
    except ValueError: return None


def _d(s):
    x = _dt(s); return x.date() if x else None


def upsert(db: Session, entity: str, rows: list[dict]) -> tuple[int, int]:
    """Nạp thô. Trả về (mới, cập nhật)."""
    if entity not in ENTITIES: raise ValueError("entity không hợp lệ")
    key = {"tour": "recID", "booking": "recID", "receipt": "RecID", "supplier_payment": "RecID", "user": "recID", "vehicle": "recID", "proposal": "proposalId", "settlement": "tourId", "product": "id"}[entity]
    new = upd = 0
    existing = {r.vietrip_id: r for r in db.execute(select(VtRecord).where(VtRecord.entity == entity)).scalars()}
    seen = set()
    for raw in rows:
        vid = str(raw.get(key) or "")
        if not vid or vid in seen: continue
        seen.add(vid)
        ref = str(raw.get("tourcode") or raw.get("Tourcode") or raw.get("BookingID") or raw.get("licensePlate") or "")
        on = _d(raw.get("fstUpdate") or raw.get("FstUpdate") or raw.get("ngayKhoiHanh") or raw.get("submittedAt") or raw.get("lstUpdate"))
        amt = float(raw.get("totalDue") or raw.get("SoTien") or raw.get("Amount") or raw.get("amount") or raw.get("doanhThu") or 0)
        r = existing.get(vid)
        if r:
            if r.raw != raw:
                r.raw, r.ref, r.on_date, r.amount, r.applied = raw, ref, on, amt, False; upd += 1
        else:
            db.add(VtRecord(entity=entity, vietrip_id=vid, ref=ref, on_date=on, amount=amt, raw=raw)); new += 1
    db.commit()
    return new, upd


def status_counts(db: Session) -> dict:
    out = {}
    for e in ENTITIES:
        tot = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.entity == e)).scalar()
        ap = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.entity == e, VtRecord.applied == True)).scalar()
        mn = db.execute(select(func.min(VtRecord.on_date)).where(VtRecord.entity == e)).scalar()
        mx = db.execute(select(func.max(VtRecord.on_date)).where(VtRecord.entity == e)).scalar()
        out[e] = {"total": tot, "applied": ap, "from": mn, "to": mx}
    return out


# ---------- ánh xạ ----------
def _user_for(db: Session, name: str, cache: dict) -> User:
    """Tìm/tạo tài khoản VTOS cho người dùng Vietrip theo họ tên (mật khẩu ngẫu nhiên – HCNS cấp lại)."""
    key = (name or "").strip().upper()
    if not key: key = "VIETRIP"
    if key in cache: return cache[key]
    u = db.execute(select(User).where(func.upper(User.full_name) == key)).scalars().first()
    if not u:
        base = re.sub(r"[^a-z0-9]", "", _strip_accents(key).lower())[:20] or "vt"
        uname = base; n = 1
        while db.execute(select(User).where(User.username == uname)).scalars().first():
            n += 1; uname = f"{base}{n}"
        u = User(username=uname, full_name=name or "Vietrip", role="nv_kd", department="Vietrip", password_hash=hash_password(secrets.token_urlsafe(12)), active=True)
        db.add(u); db.flush()
    cache[key] = u
    return u


def _strip_accents(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tour_type_of(raw: dict) -> str:
    code = (raw.get("tourcode") or "").upper(); nuoc = (raw.get("nuoc") or "").strip()
    if code.startswith("KLE"): return "non_package"   # Vietrip: dịch vụ Non-package tạo mã KLEddmmyy[_n]
    doan = code.startswith("MICE") or "MICE" in (raw.get("tenSanPham") or "").upper()
    if doan: return "doan_nuoc_ngoai" if nuoc else "doan_noi_dia"
    return "le_nuoc_ngoai" if nuoc else "le_noi_dia"


def _stub_tour(db: Session, raw: dict, cache: dict):
    """Tạo tour tạm từ mã tour Vietrip (dạng MÃSP.NNddmmyy – NN số ngày) khi tour không còn trong danh sách điều hành."""
    code = raw.get("tourcode") or ""
    m = re.search(r"\.(\d{2})(\d{2})(\d{2})(\d{2})", code)
    if not m: return None
    try: start = date(2000 + int(m.group(4)), int(m.group(3)), int(m.group(2)))
    except ValueError: return None
    from datetime import timedelta
    days = max(int(m.group(1)), 1); end = start + timedelta(days=days - 1)
    t = db.execute(select(Tour).where(Tour.code == code)).scalars().first()
    if t: return t
    op = _user_for(db, "Điều hành Vietrip", cache)
    t = Tour(code=code, operator_id=op.id, name=f"{code} (tour không còn trong danh sách điều hành Vietrip)", tour_type=tour_type_of(raw), start_date=start, end_date=end,
             product_code=code.split(".")[0], days=days, imported=True, confirmed_by="vietrip", approved_by="vietrip",
             status="ket_thuc" if end < date.today() else "da_duyet")
    if str(raw.get("tourID") or "").isdigit(): t.vietrip_id = int(raw["tourID"])
    db.add(t); db.flush()
    return t


def apply_products(db: Session, limit: int = 400) -> int:
    """Sản phẩm Vietrip (/product/edit/{id}) → products: thông tin cơ bản, cơ cấu chi phí 11 khoản, dòng chi phí NCC, chương trình giá; nối tour cùng mã."""
    from app.services.products import guess_type
    n = 0; cache = {}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "product", VtRecord.applied == False).order_by(VtRecord.id).limit(limit)).scalars():
        raw = r.raw; code = (raw.get("ProductCode") or "").strip().upper()
        if not code: r.applied, r.apply_note = True, "bỏ qua: thiếu mã"; continue
        p = db.execute(select(Product).where(Product.code == code)).scalars().first()
        if not p: p = Product(code=code, name=raw.get("ProductName") or code, source="vietrip"); db.add(p)
        p.name = (raw.get("ProductName") or code)[:200]; p.vietrip_id = int(raw.get("id") or 0) or None
        p.tour_type = guess_type(code, raw.get("TourType") or "", p.name)
        p.departure_point = (raw.get("DeparturePoint") or "")[:80]; p.region = (raw.get("Region") or "")[:80]; p.country = (raw.get("Country") or "")[:60]; p.sale_point = (raw.get("SalePoint") or "")[:80]
        p.transport = (raw.get("Transportation") or "")[:40]; p.vehicle_type = (raw.get("VehicleType") or "")[:40]; p.length_text = (raw.get("TourLength") or "")[:20]
        p.days = int(float(raw.get("Duration") or 0) or 0) or max(1, p.days or 1)
        num = lambda v: float(str(v or "0").replace(",", "").replace(".", "") or 0) if isinstance(v, str) and "," in str(v) else float(v or 0)
        p.reference_price = num(raw.get("ReferencePrice")); p.deposit_pct = float(raw.get("DepositPercentage") or 0); p.days_to_close = int(float(raw.get("DaysToCloseTour") or 0))
        p.requires_confirmation = str(raw.get("RequiresConfirmation")).lower() in ("true", "1", "on")
        keys = {"ve_may_bay": "Flight", "land": "Land", "phi_lsq": "LSQFee", "bao_hiem": "Insurance", "qua_tang": "Gift", "phi_tl": "TLFee", "hop_doan": "GroupMeeting", "dieu_hanh": "Operating", "dich_thuat": "Translation", "hoa_hong_ve": "TicketCommission", "phi_ck": "CKFee", "khac": "OtherCost"}
        p.cost_structure = {k: num(raw.get(v)) for k, v in keys.items()}
        p.cost_lines = [{"loai": l.get("loai") or "", "ncc": l.get("ncc") or "", "mst": l.get("mst") or "", "kind": "theo_khach" if str(l.get("kind") or "").lower().startswith("per") or l.get("kind") == "theo_khach" else "co_dinh",
                         "mo_ta": l.get("mo_ta") or "", "don_gia": num(l.get("don_gia")), "sl": float(l.get("sl") or 1), "so_tien": num(l.get("so_tien"))} for l in (raw.get("cost_lines") or [])][:200]
        p.program = (raw.get("PriceInfoText") or "")[:20000]; p.services = (raw.get("services") or "")[:300]; p.status = "active" if str(raw.get("status") or "Hoạt động").lower().startswith("hoạt") else "inactive"
        if raw.get("NVDH_name"): p.operator_id = _user_for(db, raw["NVDH_name"], cache).id
        db.flush()
        for t in db.execute(select(Tour).where(Tour.product_code == code, Tour.product_id == None)).scalars(): t.product_id = p.id
        r.applied, r.apply_note = True, f"product:{code}"; n += 1
    db.commit()
    return n


def apply_users(db: Session, limit: int = 400) -> int:
    n = 0; cache = {}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "user", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; name = raw.get("hoTen") or ""
        dept, role = DEPT_MAP.get(raw.get("phongBan") or "", ("kd_le", "nv_kd"))
        cv = raw.get("chucVu") or ""
        u = _user_for(db, name, cache)
        if u.department == "Vietrip":
            u.department = raw.get("phongBan") or "Vietrip"
            u.role = "tp_dh" if (cv == "Trưởng phòng" and dept == "dieu_hanh") else "gd_kd" if (cv == "Giám đốc" and dept == "kd_le") else role
        e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        if not e:
            code = f"VT{int(raw['recID']):04d}"
            if not db.execute(select(Employee).where(Employee.code == code)).scalars().first():
                pos = "tp" if cv == "Trưởng phòng" else "gd_kd" if cv == "Giám đốc" and dept == "kd_le" else "hdv" if dept == "huong_dan" else "nv"
                db.add(Employee(code=code, user_id=u.id, full_name=name, department=dept, position=pos, contract_type="ctv" if dept == "huong_dan" else "hdld"))
        r.applied, r.apply_note = True, f"user:{u.username}"; n += 1
    db.commit()
    return n


def apply_vehicles(db: Session, limit: int = 400) -> int:
    n = 0
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "vehicle", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; plate = (raw.get("licensePlate") or "").replace(" ", "-")
        v = db.execute(select(Vehicle).where(Vehicle.plate == plate)).scalars().first()
        if not v:
            v = Vehicle(plate=plate, seats=45, kind="noi_bo"); db.add(v); db.flush()
        drv = raw.get("driverName") or ""
        if drv:
            e = db.execute(select(Employee).where(func.upper(Employee.full_name) == drv.upper())).scalars().first()
            if not e:
                code = f"TX{int(raw['recID']):03d}"
                if not db.execute(select(Employee).where(Employee.code == code)).scalars().first():
                    e = Employee(code=code, full_name=drv, department="doi_xe", position="tai_xe", contract_type="hdld", base_salary=7_000_000); db.add(e); db.flush()
            if e: v.driver_id = e.id
        r.applied, r.apply_note = True, f"vehicle:{plate}"; n += 1
    db.commit()
    return n


"""TC-52 · DẤU "ĐÃ ĐÓNG SỐ" LẤY TỪ BƯỚC QUY TRÌNH CỦA VIETRIP, KHÔNG LẤY TỪ HAI CỜ CHẾT."""

# Trạng thái VTOS coi là đã đóng số. Giống hệt `ket_qua_that.DA_DONG_SO` — chép sang đây thay vì
# nhập khẩu để tránh vòng tròn, và có phép thử canh hai bản không được lệch nhau.
DA_DONG_SO = ("da_dong_so", "kt_xac_nhan", "khoa")

# Bước quy trình Vietrip tính là ĐÃ QUYẾT TOÁN. Anh Tuấn chốt 17/9/2026: từ Bước 5 trở lên.
#
#   1 Lập dự toán · 2 KSNB dự toán · 3 Phê duyệt dự toán  → DỰ TOÁN, không phải số thực
#   5 Lập quyết toán · 6 KSNB quyết toán · 7 Phê duyệt quyết toán · 8 Thanh toán, đối chiếu · 9 Báo cáo
#
# Vì sao không dùng `quyetToan`/`duyetChi` như apply_tours: hai cờ ấy false ở CẢ 1.363 bản ghi tour
# Vietrip gửi sang (đếm ngày 17/9/2026, không sót một chuyến). Luật dựa trên chúng không bao giờ ra
# một con số nào — màn hình Chủ tịch đứng ở một dấu gạch suốt, mà không ai biết vì sao.
#
# Vì sao không lấy cả Bước 1–3, dù chúng cũng có cột thực chi và cộng lại ra 2,89 tỷ "lãi": ở những
# bước ấy bảng còn là DỰ TOÁN. Lấy dự toán làm giá vốn thì biên kế hoạch bằng biên thực tế và cảnh
# báo vượt dự toán không bao giờ kích hoạt — đúng cái bẫy Ý kiến thẩm định 06/9/2026 (B2, B3) đã
# chỉ ra và vòng này không được bước lại vào.
BUOC_DA_QUYET_TOAN = 5


def buoc_vietrip(step: str | None) -> int | None:
    """Số thứ tự bước trong chuỗi "Bước 7: Phê duyệt Quyết toán". None khi không đọc được.

    Trang quyết toán Vietrip chỉ hiện MỘT dòng "Bước N" — bước hiện tại, không phải thanh tiến độ
    liệt kê cả chín bước (đã mở trang thật kiểm ngày 17/9/2026). Nên lấy chuỗi đầu tiên là đúng.
    """
    m = re.search(r"Bước\s*(\d+)", step or "")
    return int(m.group(1)) if m else None


def da_quyet_toan_tren_vietrip(raw: dict) -> bool:
    """Bảng quyết toán này đã tới bước được coi là đã đóng số chưa.

    Không đọc được bước thì trả False. Đoán "chắc là xong rồi" ở đây là đưa một chuyến chưa quyết
    toán vào kết quả kinh doanh của Chủ tịch — rỗng thì còn nhìn ra, đoán sai thì không.
    """
    b = buoc_vietrip(raw.get("step"))
    return b is not None and b >= BUOC_DA_QUYET_TOAN


def phap_nhan_mac_dinh(db: Session) -> int | None:
    """Pháp nhân gắn cho chuyến nhập từ Vietrip: CÔNG TY MẸ (anh Tuấn chốt 17/9/2026).

    ═══════════════════════════════════════════════════════════════════════════════════════════
    VÌ SAO PHẢI CÓ HÀM NÀY — VÀ VÌ SAO NÓ CHỈ ÁP CHO TOUR VIETRIP
    ═══════════════════════════════════════════════════════════════════════════════════════════
    `tours.company_id` để rỗng nghĩa là CHƯA XÁC ĐỊNH, và luật chung là không mặc định về công ty
    mẹ — đoán sai pháp nhân thì mọi con số tiền trên màn hình là của một công ty khác, mà nhìn
    thì không khác gì số đúng.

    Nhưng chuyến nhập từ Vietrip là trường hợp KHÔNG PHẢI ĐOÁN: Vietrip là app điều hành của công
    ty mẹ, chuyến nào chạy trên đó là chuyến của mẹ. Anh Tuấn chốt như vậy ngày 17/9/2026, sau khi
    mở màn hình chủ tịch và thấy Doanh thu hiện "—" trong khi VTOS đang giữ 1.244 chuyến và 10.303
    booking nhập từ Vietrip: `ket_qua_that.thang()` lọc theo pháp nhân mẹ, mà 1.743 chuyến đều
    `company_id = NULL`, nên phép lọc trả về rỗng.

    Ba ranh giới của luật này, mỗi cái là một phép thử:
      1. CHỈ chuyến `imported = True` (nguồn Vietrip). Chuyến dựng tay trong VTOS vẫn phải do người
         chọn pháp nhân — luật cũ giữ nguyên cho chúng.
      2. KHÔNG ghi đè. `company_id` đã có giá trị thì để yên, kể cả khi giá trị ấy khác công ty mẹ:
         ai đó đã gắn tay là đã có chủ ý, robot không được cãi.
      3. KHÔNG bịa. Danh mục công ty chưa có dòng `kind='me'` thì trả None và không gắn gì cả —
         thà để rỗng còn hơn gắn nhầm vào công ty đầu tiên trong bảng.
    """
    from app.services.ket_qua_that import cong_ty_me
    return cong_ty_me(db)


def gan_phap_nhan_con_rong(db: Session, boi: str = "robot-vietrip") -> dict:
    """Gắn pháp nhân MẸ cho MỌI chuyến còn để rỗng — anh Tuấn chốt 17/9/2026: "gán hết cho
    Vietourist Holdings".

    ═══════════════════════════════════════════════════════════════════════════════════════════
    TC-56 · RANH GIỚI "CHỈ CHUYẾN NGUỒN VIETRIP" CỦA TC-51 ĐÃ BỎ — GHI LẠI CẢ HAI VẾ
    ═══════════════════════════════════════════════════════════════════════════════════════════
    TC-51 cố ý chỉ gắn cho chuyến `imported = True`, với lý lẽ: chuyến dựng tay trong VTOS phải do
    NGƯỜI chọn pháp nhân, gắn thay là lặng lẽ xoá mất câu hỏi "chuyến này của ai".

    Lý lẽ ấy bỏ sót một trường hợp thứ ba, và nó lộ ra ngay hôm sau: **kho cũ**. Chuyến nạp từ kho
    lịch sử không phải nguồn Vietrip, cũng không phải ai dựng tay — nên nó rơi đúng vào khe giữa
    hai nhánh. Đếm ngày 17/9: 477/765 chuyến H1 không có pháp nhân, và màn hình Chủ tịch lọc theo
    Vietourist mẹ nên chúng bị lọc ra sạch, dù đã đóng số hay chưa.

    Anh Tuấn chốt gắn hết. Điều đó đúng với thực tế VTOS hôm nay: đây là hệ điều hành của
    Vietourist, pháp nhân khác là ngoại lệ và được gắn tay khi cần.

    HAI RANH GIỚI CÒN LẠI GIỮ NGUYÊN, và chúng mới là chỗ bảo vệ thật:
      · KHÔNG GHI ĐÈ. `company_id` đã có giá trị thì để yên, kể cả khác công ty mẹ — ai gắn tay là
        đã có chủ ý, và ngoại lệ chỉ sống được nếu robot không cãi lại nó.
      · KHÔNG BỊA. Danh mục chưa có dòng `kind='me'` thì trả None và không gắn gì cả.
    """
    me = phap_nhan_mac_dinh(db)
    if me is None:
        return {"da_gan": 0, "con_rong": None, "cong_ty_me": None,
                "message": "Danh mục công ty chưa có pháp nhân mẹ (kind='me') — không gắn gì cả"}
    rows = db.execute(select(Tour).where(Tour.company_id.is_(None))).scalars().all()
    tu_vietrip = sum(1 for t in rows if t.imported)
    for t in rows:
        t.company_id = me
    R.audit(db, boi, "robot", "gan_phap_nhan_con_rong", "tours",
            after={"so_chuyen": len(rows), "tu_vietrip": tu_vietrip,
                   "nguon_khac": len(rows) - tu_vietrip, "company_id": me})
    db.commit()
    con_rong = db.execute(select(func.count(Tour.id)).where(Tour.company_id.is_(None))).scalars().first()
    return {"da_gan": len(rows), "tu_vietrip": tu_vietrip, "nguon_khac": len(rows) - tu_vietrip,
            "con_rong": int(con_rong or 0), "cong_ty_me": me,
            "message": f"Đã gắn pháp nhân mẹ cho {len(rows)} chuyến còn rỗng"}


def dong_so_theo_buoc_vietrip(db: Session, boi: str = "robot-vietrip") -> dict:
    """Vá MỘT LẦN: đóng số cho chuyến có bảng quyết toán đã tới Bước 5 trở lên (TC-52).

    Cần cửa riêng vì 837 bảng quyết toán đã nhập đều `applied = True`; `apply_settlements` chỉ chạm
    tới bản ghi CHƯA ánh xạ, nên luật mới một mình nó chỉ áp cho bảng về từ mai trở đi.

    Bấm lại lần hai vô hại: chuyến đã `da_dong_so` không thoả điều kiện nữa. Trả về cả phần KHÔNG
    đóng được kèm lý do — con số bị bỏ lại phải nhìn thấy được, không được im lặng biến mất.
    """
    ra = {"da_dong_so": 0, "bo_qua_chua_du_buoc": 0, "bo_qua_da_dong_roi": 0,
          "bo_qua_chua_ket_thuc": 0, "bo_qua_khong_thay_tour": 0,
          "doanh_thu": 0.0, "gia_von": 0.0, "thieu_gia_von": 0}
    hom_nay = date.today()
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "settlement")).scalars():
        raw = r.raw or {}
        if not da_quyet_toan_tren_vietrip(raw):
            ra["bo_qua_chua_du_buoc"] += 1; continue
        t = db.execute(select(Tour).where(Tour.code == raw.get("tourcode"))).scalars().first()
        if not t:
            ra["bo_qua_khong_thay_tour"] += 1; continue
        if t.status in DA_DONG_SO:
            ra["bo_qua_da_dong_roi"] += 1; continue
        if not t.end_date or t.end_date > hom_nay:
            ra["bo_qua_chua_ket_thuc"] += 1; continue
        t.status = "da_dong_so"
        t.closed_at = t.closed_at or datetime.combine(t.end_date, datetime.min.time())
        ra["da_dong_so"] += 1
        ra["doanh_thu"] += float(t.actual_revenue or 0)
        if t.actual_cost is None: ra["thieu_gia_von"] += 1
        else: ra["gia_von"] += float(t.actual_cost)
    R.audit(db, boi, "robot", "dong_so_theo_buoc_vietrip", "tours", after=ra)
    db.commit()
    ra["message"] = (f"Đã đóng số {ra['da_dong_so']} chuyến theo bước quyết toán Vietrip "
                     f"(từ Bước {BUOC_DA_QUYET_TOAN})")
    return ra


def apply_tours(db: Session, only_from: date | None = None, limit: int = 400) -> int:
    n = 0; cache = {}
    me = phap_nhan_mac_dinh(db)   # tra MỘT lần cho cả lô, không phải mỗi chuyến một câu truy vấn
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "tour", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; code = raw.get("tourcode") or ""
        start, end = _d(raw.get("ngayKhoiHanh")), _d(raw.get("ngayKetThuc"))
        if not code or not start: r.applied, r.apply_note = True, "bỏ qua: thiếu mã/ngày"; continue
        if only_from and start < only_from: r.applied, r.apply_note = True, "ngoài phạm vi"; continue
        t = db.execute(select(Tour).where(Tour.code == code)).scalars().first()
        op = _user_for(db, raw.get("fstUser") if not str(raw.get("fstUser") or "").isdigit() else "Điều hành Vietrip", cache)
        if not t:
            t = Tour(code=code, operator_id=op.id); db.add(t)
        t.name = raw.get("tenSanPham") or raw.get("ghiChu") or code
        t.tour_type = tour_type_of(raw); t.start_date, t.end_date = start, end or start
        t.price_per_pax = float(raw.get("adl") or 0); t.price_chd = float(raw.get("chd") or 0); t.price_inf = float(raw.get("inf") or 0); t.price_promo = float(raw.get("adl_KM") or 0)
        t.planned_pax = int(raw.get("soChoMoBan") or 0); t.seats_open = int(raw.get("soChoMoBan") or 0); t.seats_promo = int(raw.get("soChoMoBan_KM") or 0)
        t.product_code = code.split(".")[0]
        if not t.product_id:
            pr = db.execute(select(Product).where(Product.code == t.product_code)).scalars().first()
            if pr: t.product_id = pr.id
        t.vehicle_type = raw.get("loaiXe") or ""; t.departure_point = raw.get("diemKhoiHanh") or ""; t.transport = raw.get("phuongTien") or ""
        t.days = int(raw.get("soNgay") or 0); t.country = raw.get("nuoc") or ""; t.vietrip_id = int(raw["recID"]); t.imported = True
        # Gắn pháp nhân mẹ khi chỗ ấy còn rỗng — xem phap_nhan_mac_dinh() cho luật và ba ranh giới.
        # `is None` chứ không phải `not t.company_id`: id công ty không bao giờ là 0, nhưng viết
        # `not` thì ngày nào đó có id 0 là robot ghi đè mất pháp nhân người ta gắn tay.
        if t.company_id is None and me is not None:
            t.company_id = me
        t.settled_vietrip = bool(raw.get("quyetToan")) or bool(raw.get("duyetChi"))
        # Với tour CHƯA quyết toán, trường tongChiPhi của Vietrip chỉ là các khoản phí nhập sẵn theo khách
        # (bảo hiểm, vé máy bay, land, quà tặng, phí LSQ) chứ không phải giá vốn chuyến – tour DL001.03130926
        # có tongChiPhi = 6.500 chính là phí bảo hiểm. Lấy số đó làm giá vốn thì lợi nhuận xấp xỉ toàn bộ
        # doanh thu (Ý kiến thẩm định 06/9/2026, B3). Chỉ nhận doanh thu/giá vốn khi Vietrip đã quyết toán.
        if t.settled_vietrip:
            t.actual_revenue = float(raw.get("doanhThu") or 0); t.actual_cost = float(raw.get("tongChiPhi") or 0)
        elif t.status not in DA_DONG_SO:
            t.actual_revenue = t.actual_cost = 0.0
        # TC-52 · `elif t.status not in DA_DONG_SO` thay cho `else` trơn — CHỖ RÒ RỈ LẶNG LẼ NHẤT.
        #
        # `quyetToan`/`duyetChi` của Vietrip LUÔN false (đã soi cả 1.363 bản ghi ngày 17/9/2026 —
        # không sót một chuyến nào), nên nhánh `else` này chạy cho MỌI chuyến, mọi lần đồng bộ. Mà
        # `apply_settlements` mới là chỗ ghi doanh thu/giá vốn thật từ bảng quyết toán. Hai hàm ấy
        # đọc hai loại bản ghi khác nhau: tour được nạp lại thì tour chạy một mình, và nó xoá trắng
        # số quyết toán đã ghi — không báo lỗi, không audit, chỉ là hai cột tiền về 0 sau mỗi đêm.
        t.confirmed_by, t.approved_by = "vietrip", "vietrip"
        today = date.today()
        if raw.get("duyetChi"): t.status = "khoa"; t.closed_at = t.closed_at or _dt(raw.get("ngayDuyetChi")) or datetime.combine(t.end_date, datetime.min.time()); t.kt_confirmed_at = t.kt_confirmed_at or _dt(raw.get("ngayDuyetChi")); t.cntt_checked_at = t.cntt_checked_at or _dt(raw.get("ngayDuyetChi"))
        elif raw.get("quyetToan"): t.status = "kt_xac_nhan"; t.closed_at = t.closed_at or datetime.combine(t.end_date, datetime.min.time()); t.kt_confirmed_at = t.kt_confirmed_at or datetime.combine(t.end_date, datetime.min.time())
        elif t.status in DA_DONG_SO: pass   # TC-52: đã đóng số rồi thì KHÔNG hạ cấp ngược về "kết thúc"
        elif t.end_date < today: t.status = "ket_thuc"
        else: t.status = "da_duyet"
        r.applied, r.apply_note = True, f"tour:{code}"; n += 1
    db.commit()
    return n


def apply_settlements(db: Session, limit: int = 400) -> int:
    """Dòng chi phí quyết toán theo tour → tour_cost_lines; suy ra chi phí cố định / theo khách cho dự toán VTOS."""
    n = 0
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "settlement", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; t = db.execute(select(Tour).where(Tour.code == raw.get("tourcode"))).scalars().first()
        if not t: r.apply_note = "chưa có tour"; continue
        db.execute(TourCostLine.__table__.delete().where(TourCostLine.tour_id == t.id, TourCostLine.source == "vietrip"))
        for i, l in enumerate(raw.get("lines") or [], 1):
            sup = l.get("ncc") or ""; m = re.search(r"\((\d{10,14})\)\s*$", sup)
            kind = "theo_khach" if "theo khách" in (l.get("mo_ta") or "").lower() else "co_dinh"
            actual = float(l.get("thuc_chi") or 0)
            db.add(TourCostLine(tour_id=t.id, line_no=i, description=(l.get("mo_ta") or "").split("|")[0].strip()[:200], cost_kind=kind, service_type=l.get("loai") or "",
                                supplier_name=re.sub(r"\s*\(\d{10,14}\)\s*$", "", sup)[:200], supplier_tax_code=m.group(1) if m else "", unit_price=float(l.get("don_gia") or 0),
                                qty=float(l.get("sl") or 0), coef=float(l.get("hs") or 1), actual=actual, paid=float(l.get("da_tt") or 0), note=(l.get("ghi_chu") or "")[:200]))
        # KHÔNG suy ngược dự toán từ dòng quyết toán (Ý kiến thẩm định 06/9/2026, B2): làm vậy thì
        # "dự toán" chính là số thực chi, biên kế hoạch luôn bằng biên thực tế và cảnh báo vượt dự toán
        # không bao giờ kích hoạt. Dự toán do Điều hành lập; thiếu thì lấy cơ cấu chi phí sản phẩm làm
        # tham chiếu (rules.budget_of), ghi rõ nguồn.
        if raw.get("tong_thu"): t.actual_revenue = float(raw["tong_thu"])
        total_lines = sum(float(l.get("thuc_chi") or 0) for l in (raw.get("lines") or []))
        if raw.get("tong_chi"): t.actual_cost = float(raw["tong_chi"])
        elif total_lines: t.actual_cost = total_lines
        # TC-52 · ĐÓNG SỐ theo bước quy trình Vietrip (anh Tuấn chốt 17/9/2026: từ Bước 5).
        #
        # Đây là chỗ duy nhất trong cả hệ biết chuyến này đã quyết toán hay chưa, vì bảng quyết toán
        # là thứ mang cái bước ấy. Trước vòng này, 1.743 chuyến nằm ở "kết thúc" với doanh thu và giá
        # vốn ĐÃ GHI ĐỦ ngay bên cạnh (đếm 17/9: 558 bảng có thực chi, 57,9 tỷ) — thiếu đúng hai
        # trường `status` và `closed_at` nên màn hình Chủ tịch bỏ qua sạch.
        #
        # Ba ranh giới, mỗi cái một phép thử:
        #   1. CHỈ NÂNG, KHÔNG HẠ. Chuyến đã `kt_xac_nhan`/`khoa` là đã qua tay Kế toán — kéo ngược
        #      về `da_dong_so` là xoá một chữ ký.
        #   2. KHÔNG ĐÓNG SỐ CHUYẾN CHƯA CHẠY XONG. Bảng quyết toán có thể lập sớm; chuyến chưa tới
        #      ngày kết thúc mà đã tính vào kết quả tháng là ghi nhận doanh thu trước khi có.
        #   3. MỐC LÀ NGÀY CHUYẾN KẾT THÚC, không phải ngày robot chạy. Lấy ngày robot thì doanh thu
        #      tháng 6 rơi vào tháng 9 chỉ vì hôm nay mới đồng bộ — bài học TC-47 số 4.
        if (da_quyet_toan_tren_vietrip(raw) and t.status not in DA_DONG_SO
                and t.end_date and t.end_date <= date.today()):
            t.status = "da_dong_so"
            t.closed_at = t.closed_at or datetime.combine(t.end_date, datetime.min.time())
        # lịch sử quy trình Vietrip → tour_events (nguồn vietrip), không nhân bản
        hist = raw.get("history") or []
        if hist:
            db.execute(TourEvent.__table__.delete().where(TourEvent.tour_id == t.id, TourEvent.source == "vietrip"))
            for h in hist[:60]:
                db.add(TourEvent(tour_id=t.id, step="vietrip", title=(h.get("title") or "")[:200], note=(h.get("note") or "")[:2000], actor=(h.get("actor") or "")[:120], source="vietrip", at=_dt(h.get("at")) or datetime.now()))
        if raw.get("step"): r.apply_note = f"{len(raw.get('lines') or [])} dòng – {raw['step'][:60]}"
        else: r.apply_note = f"{len(raw.get('lines') or [])} dòng"
        r.applied = True; n += 1
    db.commit()
    return n


def repair_derived_budgets(db: Session, actor: str = "cntt") -> dict:
    """Dọn dữ liệu cũ của B2: các tour nhập từ Vietrip có dự toán được suy ngược từ dòng quyết toán
    (bản trước 06/9/2026). Đặt lại về rỗng để hệ thống dùng cơ cấu chi phí sản phẩm làm dự toán tham
    chiếu, hoặc ghi rõ "chưa có dự toán" – thay vì trình bày số thực chi như thể là dự toán.
    Chạy một lần sau khi triển khai; chỉ đụng tới tour có cờ imported và có dòng chi phí nguồn vietrip.
    """
    from app.services import rules as R
    n = m = 0
    tour_ids = {r[0] for r in db.execute(select(TourCostLine.tour_id).where(TourCostLine.source == "vietrip")).all()}
    for t in db.execute(select(Tour).where(Tour.imported == True)).scalars():
        if t.id in tour_ids and ((t.fixed_cost or 0) > 0 or (t.var_cost_per_pax or 0) > 0):
            t.fixed_cost, t.var_cost_per_pax = 0.0, 0.0
            n += 1
        if not t.settled_vietrip and t.id not in tour_ids and (t.actual_cost or t.actual_revenue):
            t.actual_cost = t.actual_revenue = 0.0      # phí nhập sẵn theo khách bị nhận nhầm là giá vốn
            m += 1
    R.audit(db, actor, "cntt", "don_du_toan_suy_nguoc_vietrip", "vietrip", after={"du_toan_suy_nguoc": n, "gia_von_gia": m})
    db.commit()
    return {"tours": n, "gia_von_gia": m,
            "message": f"Đã xóa dự toán suy ngược từ quyết toán ở {n} tour và giá vốn giả (phí nhập sẵn theo khách) "
                       f"ở {m} tour chưa quyết toán – dự toán và thực chi nay là hai số độc lập"}


def apply_bookings(db: Session, limit: int = 400) -> int:
    n = 0; cache = {}
    tours = {t.code: t for t in db.execute(select(Tour)).scalars()}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "booking", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; t = tours.get(raw.get("tourcode") or "")
        if not t:
            # Tour không còn trong danh sách điều hành Vietrip (đã hủy/gộp): booking hủy → bỏ qua; booking OK → tạo tour tạm từ mã tour
            if (raw.get("status") or "OK") != "OK": r.applied, r.apply_note = True, "tour đã hủy – bỏ qua"; continue
            t = _stub_tour(db, raw, cache)
            if not t: r.apply_note = "chưa có tour"; continue
            tours[t.code] = t
        code = f"VT{int(raw['recID'])}"
        b = db.execute(select(Booking).where(Booking.code == code)).scalars().first()
        sales = _user_for(db, raw.get("fstUser") or "", cache)
        if not b:
            b = Booking(code=code, tour_id=t.id, request_id=0, sales_id=sales.id, created_by=sales.id, sla_minutes=0, sla_ok=True); db.add(b)
        b.tour_id = t.id; b.customer_name = (raw.get("tenNguoiBook") or "")[:120]; b.customer_phone = (raw.get("phone") or "")[:30]; b.source = "Vietrip"
        b.adl, b.chd, b.inf = int(raw.get("adl") or 0), int(raw.get("chd") or 0), int(raw.get("inf") or 0)
        b.pax = b.adl + b.chd + b.inf; b.amount = float(raw.get("totalDue") or 0); b.pmt_status = raw.get("pmtStatus") or ""
        b.cancel_deadline = _dt(raw.get("deadlineHuyCho")); b.cancelled = (raw.get("status") or "OK") != "OK"; b.services_note = (raw.get("dichVuLe") or "")[:200]
        b.created_at = _dt(raw.get("fstUpdate")) or b.created_at or datetime.now(); b.vietrip_id = int(raw["recID"])
        b.counts_for_target = bool(b.customer_phone) and not b.cancelled
        if b.cancelled: b.amount = 0
        r.applied, r.apply_note = True, f"booking:{code}"; n += 1
    db.commit()
    return n


def apply_receipts(db: Session, limit: int = 400) -> int:
    n = 0; touched = set(); made = set()
    bk = {b.vietrip_id: b for b in db.execute(select(Booking).where(Booking.vietrip_id != None)).scalars()}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "receipt", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw
        if raw.get("Status") != "KC": r.applied, r.apply_note = True, "chưa xác nhận – bỏ qua"; continue
        b = bk.get(int(raw.get("BookingID") or 0))
        if not b: r.apply_note = "chưa có booking"; continue
        if raw.get("LoaiPhieu") == "PhieuChi":   # phiếu chi trả khách (hoàn tiền) → đề nghị chi hoàn tiền đã chi
            code = f"VTPC{int(raw['RecID'])}"
            pr = db.execute(select(PaymentRequest).where(PaymentRequest.code == code)).scalars().first()
            if not pr:
                pr = PaymentRequest(code=code, category="hoan_tien", supplier_name="", amount=0, description="", created_by="vietrip"); db.add(pr)
            pr.tour_id = b.tour_id; pr.supplier_name = (raw.get("NguoiThanhToan") or b.customer_name)[:160]; pr.amount = float(raw.get("SoTien") or 0)
            pr.description = f"Hoàn tiền khách {b.code} – {raw.get('GhiChu') or ''} [Vietrip]"[:300]; pr.status = "da_chi"; pr.approved_by = "vietrip"; pr.signed_tgd = True
            pr.created_at = _dt(raw.get("FstUpdate")) or datetime.now(); pr.paid_at = pr.created_at; pr.paid_method = "tien_mat" if "mặt" in (raw.get("HinhThuc") or "").lower() else "chuyen_khoan"
            r.applied, r.apply_note = True, code; n += 1; continue
        code = f"VTPT{int(raw['RecID'])}"
        if code in made: r.applied, r.apply_note = True, f"{code} (trùng)"; continue
        rc = db.execute(select(Receipt).where(Receipt.code == code)).scalars().first()
        if not rc:
            rc = Receipt(code=code, booking_id=b.id); db.add(rc)
        made.add(code); touched.add(b.id)
        rc.amount = float(raw.get("SoTien") or 0); rc.method = "tien_mat" if "mặt" in (raw.get("HinhThuc") or "").lower() else "chuyen_khoan"
        rc.payer = (raw.get("NguoiThanhToan") or b.customer_name)[:120]; rc.note = f"Vietrip {raw.get('TaiKhoanCongTy') or ''} {raw.get('GhiChu') or ''}".strip()[:200]
        rc.status = "ke_toan_xac_nhan"; rc.created_by = "vietrip"; rc.confirmed_by = (raw.get("FstUser") or "vietrip")[:50]
        rc.created_at = _dt(raw.get("FstUpdate")) or datetime.now(); rc.confirmed_at = rc.created_at
        r.applied, r.apply_note = True, code; n += 1
    db.flush()
    # cập nhật đã thu cho các booking vừa chạm (1 truy vấn gộp)
    if touched:
        sums = dict(db.execute(select(Receipt.booking_id, func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.booking_id.in_(list(touched)), Receipt.status != "huy").group_by(Receipt.booking_id)).all())
        by_id = {b.id: b for b in bk.values()}
        for bid in touched:
            if bid in by_id: by_id[bid].paid = float(sums.get(bid, 0) or 0)
    db.commit()
    return n


def apply_supplier_payments(db: Session, limit: int = 400) -> int:
    n = 0
    tours = {t.code: t for t in db.execute(select(Tour)).scalars()}
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "supplier_payment", VtRecord.applied == False).order_by(VtRecord.apply_note, VtRecord.id).limit(limit)).scalars():
        raw = r.raw; code = f"VTDC{int(raw['RecID'])}"
        if raw.get("Status") == "XX": r.applied, r.apply_note = True, "từ chối – bỏ qua"; continue
        pr = db.execute(select(PaymentRequest).where(PaymentRequest.code == code)).scalars().first()
        t = tours.get(raw.get("Tourcode") or "")
        if not pr:
            pr = PaymentRequest(code=code, category="chi_tour" if t else "hanh_chinh", supplier_name="", amount=0, description="", created_by="vietrip"); db.add(pr)
        pr.tour_id = t.id if t else None; pr.supplier_name = (raw.get("TenNCC") or f"NCC Vietrip #{raw.get('OrgID')}")[:160]; pr.supplier_bank = (raw.get("TaiKhoanNCC") or "")[:120]
        pr.amount = float(raw.get("Amount") or 0); pr.description = ((raw.get("MoTa") or raw.get("GhiChu") or "") + f" [Vietrip {raw.get('FOP') or ''}]").strip()[:300]
        pr.has_document = bool(raw.get("File")); pr.document_ref = (raw.get("File") or "")[:120]
        pr.created_at = _dt(raw.get("FstUpdate")) or datetime.now()
        st = raw.get("Status")
        if st == "KC": pr.status, pr.paid_at, pr.paid_method, pr.approved_by, pr.signed_tgd = "da_chi", pr.created_at, "tien_mat" if raw.get("FOP") == "CSH" else "chuyen_khoan", "vietrip", True
        elif st == "GD": pr.status, pr.approved_by, pr.signed_tgd = "cho_chi", "vietrip", True
        else: pr.status = "cho_duyet"
        r.applied, r.apply_note = True, code; n += 1
    db.commit()
    return n


def apply_all(db: Session, actor: str, limit: int = 400) -> dict:
    """Ánh xạ theo lô (mỗi lần tối đa `limit` bản ghi mỗi loại) để không quá thời gian request; gọi lặp tới khi remaining = 0."""
    out = {"users": apply_users(db, limit), "vehicles": apply_vehicles(db, limit), "products": apply_products(db, limit), "tours": apply_tours(db, limit=limit), "settlements": apply_settlements(db, limit),
           "bookings": apply_bookings(db, limit), "receipts": apply_receipts(db, limit), "supplier_payments": apply_supplier_payments(db, limit)}
    # KS-12 — loại chưa có lớp áp dụng KHÔNG bị trừ lặng lẽ nữa: vẫn nằm ngoài `remaining` (đúng,
    # vì không lớp nào áp được chúng) nhưng ĐỨNG NGAY CẠNH nó, có số dòng và có lý do.
    out["chua_co_lop_ap_dung"] = {
        e: {"so_dong": db.execute(select(func.count()).select_from(VtRecord)
                                  .where(VtRecord.applied == False, VtRecord.entity == e)).scalar(),
            "ly_do": ly_do}
        for e, ly_do in KHONG_AP_DUNG.items()}
    out["remaining"] = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.applied == False,
                                                                                  ~VtRecord.entity.in_(tuple(KHONG_AP_DUNG)),
                                                                                  ~VtRecord.apply_note.in_(["chưa có tour", "chưa có booking"]))).scalar()
    out["blocked"] = db.execute(select(func.count()).select_from(VtRecord).where(VtRecord.applied == False, VtRecord.apply_note.in_(["chưa có tour", "chưa có booking"]))).scalar()
    R.audit(db, actor, "cntt", "dong_bo_vietrip_ap_dung", "vietrip", after=out); db.commit()
    return out


def id_booking_con_thieu(db: Session, gioi_han: int = 500) -> list[int]:
    """Mã booking Vietrip mà một phiếu thu ĐANG CÓ trỏ tới, nhưng VTOS chưa có booking ấy.

    Đây là danh sách đầu vào cho `vietrip_client.nap_booking_theo_id`. Đọc từ chính bản ghi thô đã
    kéo về, không đoán và không gọi ra ngoài.

    Chỉ lấy phiếu ĐÃ XÁC NHẬN (`Status == "KC"`): phiếu chưa xác nhận vốn bị bỏ qua ở
    `apply_receipts`, đi kéo booking cho chúng là kéo thừa.
    """
    # `select(MỘT CỘT)` + `.scalars()` trả về CHÍNH giá trị cột, không trả về hàng ORM. Bản đầu
    # viết `{b.vietrip_id for b in ...}` và nổ ngay dòng đầu:
    #     AttributeError: 'int' object has no attribute 'vietrip_id'
    # Nổ trên hệ thật ngày 29/9/2026, và không phép thử nào bắt được vì hàm này CHƯA TỪNG có phép
    # thử nào gọi tới — bộ phép thử của TC-65 chỉ soi vòng lật trang, truyền thẳng `db=None`.
    co = set(db.execute(
        select(Booking.vietrip_id).where(Booking.vietrip_id != None)).scalars())
    ra: list[int] = []
    for r in db.execute(select(VtRecord).where(
            VtRecord.entity == "receipt", VtRecord.applied == False).limit(gioi_han * 4)).scalars():
        raw = r.raw or {}
        if raw.get("Status") != "KC":
            continue
        bid = int(raw.get("BookingID") or 0)
        if bid and bid not in co and bid not in ra:
            ra.append(bid)
            if len(ra) >= gioi_han:
                break
    return ra
