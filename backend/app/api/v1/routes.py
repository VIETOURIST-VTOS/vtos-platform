"""API v1 – toàn bộ endpoint JSON cho web/app/n8n."""
from datetime import timedelta, date, datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, desc, func, text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, robot_auth, Gate, loc_theo_nguoi_dung, toan_quyen
from app.api import schemas as S
from pydantic import BaseModel
from app.core.security import verify_password, create_token, hash_password
from app.models.core import (User, Tour, ServiceRequest, Booking, Param, Alert, AuditLog, ROLES,
                             TOUR_TYPES, TOUR_STATUS,
                             GIAO_DIEN_NEN, GIAO_DIEN_CO_MIN, GIAO_DIEN_CO_MAX,
                             GIAO_DIEN_MAC_DINH_NEN, GIAO_DIEN_MAC_DINH_CO)
from app.services import rules as R
from app.services import mat_khau_yeu as MKY
from app.services import tours as T
from app.services import bookings as BK
from app.services import access as AC
from app.services import pham_vi_phap_nhan as PV

router = APIRouter(prefix="/api/v1")


def user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "role_name": ROLES.get(u.role, u.role), "department": u.department}


# ---------- auth ----------
@router.post("/auth/login", response_model=S.Token, tags=["auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.username == form.username, User.active == True)).scalars().first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    # Ở ĐÚNG CHỖ NÀY máy đang cầm mật khẩu người ta vừa gõ. So nó với danh sách đã bị in công khai
    # là MỘT PHÉP SO CHUỖI – không tốn gì, và biết chắc chứ không phải thử. Bản 14/9 hỏi cùng câu
    # hỏi ấy bằng cách băm lại từng tài khoản một ở màn hình quản trị, và trả giá hơn hai phút cho
    # 116 tài khoản. Cùng một hiệu lực: cờ bật lên, dù bật bằng đường nào, cũng chỉ chặn được từ
    # lần đăng nhập KẾ TIẾP – mà lần kế tiếp ấy chính là lần này.
    if MKY.la_mat_khau_da_cong_khai(form.password):
        u.must_change_password = True
    u.last_login = datetime.now()          # để rà được tài khoản bỏ hoang và người đã nghỉ chưa khóa
    R.audit(db, u.username, u.role, "dang_nhap", "user"); db.commit()
    return {"access_token": create_token(u.username, u.role), "token_type": "bearer", "user": me(u, db)}


@router.get("/auth/me", tags=["auth"])
def me(u: User = Depends(loc_theo_nguoi_dung("hồ sơ của chính người đăng nhập")), db: Session = Depends(get_db)):
    return {**user_out(u), "hidden_menus": AC.hidden_menus_for(u, db), "can_see_cost": AC.can_see_cost(u), "read_only": u.role in AC.READ_ONLY_ROLES,
            "can_create_request": u.role in AC.REQUEST_CREATE_ROLES or toan_quyen(u), "can_create_booking": u.role in AC.OPERATIONS or toan_quyen(u),
            "must_change_password": bool(u.must_change_password), "hr_tabs": AC.hr_tabs_for(db, u),
            "company_id": u.company_id, "ngoai_bien_che": bool(u.ngoai_bien_che),
            "pham_vi": PV.mo_ta(db, u),
            # TC-67 · Giao diện của chính người này. Gửi kèm ở đây chứ không đẻ thêm một cửa đọc
            # riêng: màn hình nào cũng gọi /auth/me ngay khi mở, nên thêm một cửa nữa là thêm một
            # lượt xếp hàng dọc – đúng cái TC-66 vừa bỏ đi ở /dong-tien/meta.
            #
            # TRẢ RA ĐÚNG THỨ ĐANG CẤT, KHÔNG ĐIỀN SẴN MẶC ĐỊNH. `None` nghĩa là người này chưa
            # chọn, và màn hình phải phân biệt được "chưa chọn" với "đã chọn nền tối" – xem lý do
            # dài ở models/core.py. Mặc định gửi kèm riêng một trường để màn hình không phải
            # chép cứng hai con số ấy vào mã JavaScript; đổi mặc định thì đổi một chỗ ở máy chủ.
            "giao_dien": {"nen": u.gd_nen or None, "co_chu": u.gd_co_chu},
            "giao_dien_mac_dinh": {"nen": GIAO_DIEN_MAC_DINH_NEN, "co_chu": GIAO_DIEN_MAC_DINH_CO}}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TC-67 · CỬA GHI GIAO DIỆN – anh Tuấn 18/9/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
# RANH GIỚI 09/9/2026 nói mỗi con số hệ thống cần một cửa nhập cho người dùng. Đây là một trong số
# ít trường hợp cửa và dữ liệu là MỘT: người dùng tự chọn giao diện của chính mình, không ai nhập
# hộ ai, nên cửa này chính là bảng "Giao diện" trên màn hình.
#
# KHÔNG NHẬN ID NGƯỜI DÙNG, và đó là hàng rào thật chứ không phải hàng rào bằng lời: cửa ghi thẳng
# vào `u` – người đang cầm phiếu đăng nhập. Không có tham số nào để trỏ sang người khác, nên không
# có đường nào để một người đổi giao diện của người khác, kể cả khi ai đó sửa nhầm luật phân quyền
# về sau. Một cửa nhận `user_id` rồi kiểm "có phải chính mình không" thì an toàn đúng đến lần sửa
# tiếp theo.
#
# KIỂM Ở MÁY CHỦ chứ không tin màn hình: `nen` phải nằm trong ba giá trị đã khai, `co_chu` phải
# nằm trong dải đã khai. Màn hình có thanh trượt 14–20 thì cửa vẫn phải chặn, vì ai cũng gọi được
# API bằng tay. Dải và bộ giá trị lấy từ CHÍNH hằng số mà mô hình dùng, không chép lại – chép lại
# là ngày nào đó dải ở hai nơi lệch nhau.
#
# KHÔNG GHI NHẬT KÝ KIỂM TOÁN. `R.audit` dành cho việc đụng tới tiền, quyền và số liệu. Một người
# đổi nền màn hình của chính mình không phải việc ấy; ghi vào đó là làm loãng sổ kiểm toán đến mức
# lúc cần tra một việc thật thì phải lọc qua hàng nghìn dòng đổi cỡ chữ.
class GiaoDienVao(BaseModel):
    nen: str | None = None
    co_chu: int | None = None


@router.put("/auth/giao-dien", tags=["auth"])
def dat_giao_dien(data: GiaoDienVao, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if data.nen is not None:
        if data.nen not in GIAO_DIEN_NEN:
            raise HTTPException(422, f"Nền không hợp lệ – chỉ nhận: {', '.join(GIAO_DIEN_NEN)}")
        u.gd_nen = data.nen
    if data.co_chu is not None:
        if not (GIAO_DIEN_CO_MIN <= data.co_chu <= GIAO_DIEN_CO_MAX):
            raise HTTPException(422, f"Cỡ chữ phải từ {GIAO_DIEN_CO_MIN} đến {GIAO_DIEN_CO_MAX} px")
        u.gd_co_chu = data.co_chu
    db.commit()
    # Trả lại ĐÚNG thứ vừa cất, đọc từ chính bản ghi chứ không dội lại thứ màn hình gửi lên: màn
    # hình cần biết máy chủ đã nhận cái gì, không phải biết nó đã gửi cái gì.
    return {"nen": u.gd_nen or None, "co_chu": u.gd_co_chu}


@router.delete("/auth/giao-dien", tags=["auth"])
def xoa_giao_dien(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Trả về mặc định – XOÁ lựa chọn, không ghi đè bằng giá trị mặc định.

    Khác nhau ở chỗ: xoá rồi thì người này quay về "chưa chọn", nên mai kia hệ thống đổi mặc định
    là họ đi theo mặc định mới. Ghi đè bằng "toi"/16 thì họ bị đóng đinh vào hai con số của hôm
    nay, và chính họ cũng không biết. Nút trên màn hình viết là "Trả về mặc định", nên nó phải
    làm đúng nghĩa ấy.
    """
    u.gd_nen, u.gd_co_chu = "", None
    db.commit()
    return {"nen": None, "co_chu": None}


@router.post("/auth/password", tags=["auth"])
def change_password(data: S.PasswordChange, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, u.password_hash): raise HTTPException(400, "Mật khẩu cũ không đúng")
    # Một bộ luật, ở MỘT CHỖ. Trước 14/9/2026 chỗ này kiểm tay hai điều (đủ 6 ký tự, khác mã nhân
    # viên) và vẫn nhận "12345678" hay chính tên đăng nhập. Nó cũng nói "từ 6 ký tự" trong khi lược
    # đồ đã chặn ở 8 – hai con số khác nhau cho cùng một luật là chỗ sớm muộn cũng lệch.
    vi_sao = MKY.vi_sao_khong_dat_duoc(data.new_password, username=u.username,
                                       ho_ten=u.full_name, ma_nhan_vien=u.staff_code)
    if vi_sao:
        raise HTTPException(422, vi_sao)
    if verify_password(data.new_password, u.password_hash):
        raise HTTPException(422, "Mật khẩu mới trùng mật khẩu cũ – đổi thành mật khẩu khác.")
    u.password_hash = hash_password(data.new_password)
    u.must_change_password = False
    R.audit(db, u.username, u.role, "doi_mat_khau", "user"); db.commit()
    return {"ok": True, "must_change_password": False}


@router.get("/meta", tags=["meta"])
def meta(db: Session = Depends(get_db)):
    """Danh mục dùng chung cho giao diện.

    KHÔNG ép mọi tham số về số. Bảng chính sách có cả tham số bằng lời – danh sách vai trò được ký chữ
    ký thứ hai, bên chịu chi phí sửa xe – và một float() trên chuỗi đó làm cả endpoint trả 500. Endpoint
    này là thứ giao diện gọi khi mở màn hình, nên hỏng ở đây là hỏng với mọi vai trò cùng lúc: thêm một
    tham số bằng lời vào bảng chính sách không được phép là hành động làm sập hệ thống."""
    ps: dict[str, float | str] = {}
    for k, *_ in R.DEFAULT_PARAMS:
        try:
            ps[k] = R.get_param(db, k)
        except (ValueError, TypeError):
            ps[k] = R.get_param_text(db, k)
    return {"roles": ROLES, "tour_types": TOUR_TYPES, "tour_status": TOUR_STATUS, "params": ps}


@router.get("/users", tags=["users"])
def users(role: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(User).where(User.active == True)
    if role: q = q.where(User.role.in_(role.split(",")))
    return [user_out(x) for x in db.execute(q.order_by(User.id)).scalars()]


# ---------- dashboard ----------
_DASH_CACHE: dict = {}   # (role, uid) → (ts, payload) – bảng điều khiển tính nặng, giữ 5 phút
_DASH_DIRTY: bool = True  # có thao tác ghi kể từ lần dựng gần nhất → robot nền dựng lại


# Khóa cache của một người dùng. Vai trò nào nhìn dữ liệu của riêng mình thì thêm id vào khóa.
def dash_key(u: User) -> tuple:
    return (u.role, u.id if u.role in ("nv_dh", "tp_dh", "nv_kd") else 0)


def build_dashboard(db: Session, u: User) -> dict:
    """Dựng bảng điều khiển và ghi vào cache. Tách ra khỏi endpoint để robot nền dựng sẵn được –
    người mở trang không phải là người trả giá cho lần dựng đầu."""
    import time
    payload = _dashboard_payload(db, u)
    _DASH_CACHE[dash_key(u)] = (time.time(), payload)
    return payload


def lam_moi_cache_nen(db: Session) -> int:
    """Dựng lại đúng những khóa ĐANG có trong cache – tức những vai trò thật sự có người dùng.

    Gọi từ vòng lặp robot. Không đoán trước vai trò nào sẽ đăng nhập: khóa nào đã từng được dựng
    thì có người dùng nó, khóa nào chưa thì dựng sẵn cũng phí công trên máy chủ 512 MB.
    """
    from app.models.core import User as _U
    n = 0
    for role, uid in list(_DASH_CACHE.keys()):
        u = db.get(_U, uid) if uid else db.execute(select(_U).where(_U.role == role, _U.active == True)).scalars().first()
        if u is None: continue
        try:
            build_dashboard(db, u); n += 1
        except Exception as e:   # noqa – một vai trò lỗi không được làm hỏng cả vòng lặp
            print("lam_moi_cache_nen", role, e)
    return n


@router.get("/dashboard", tags=["dashboard"])
def dashboard(refresh: bool = False, u: User = Depends(current_user), db: Session = Depends(get_db)):
    import time
    key = dash_key(u)
    hit = _DASH_CACHE.get(key)
    if hit and not refresh and time.time() - hit[0] < 300:
        return {**hit[1], "cached": True}
    return build_dashboard(db, u)


def _dashboard_payload(db: Session, u: User) -> dict:
    # việc chờ tôi xử lý: chỉ xét tour đang trong luồng (không quét tour đã kết thúc / đã duyệt hàng loạt)
    active = db.execute(select(Tour).where(Tour.status.in_(["nhap", "cho_xac_nhan", "cho_duyet", "da_dong_so", "kt_xac_nhan"]))).scalars().all()
    if u.role in ("chutich", "tp_dh"):
        # chairman_run_decision là CHUỖI ghi nội dung quyết định ("Chủ tịch duyệt chạy 07/09/2026"),
        # không phải cờ đúng/sai. So với False thì SQLite âm thầm ép kiểu và chạy, còn PostgreSQL
        # từ chối: 'operator does not exist: character varying = boolean' → toàn bộ bảng điều khiển
        # của Chủ tịch và TP Điều hành trả lỗi 500 và trang chủ đứng ở "Đang tải…" vĩnh viễn.
        active += db.execute(select(Tour).where(Tour.status == "da_duyet", Tour.chairman_run_decision == "", Tour.start_date >= date.today(), Tour.start_date <= date.today() + timedelta(days=7))).scalars().all()
    if u.role in ("nv_dh", "tp_dh"):
        active += db.execute(select(Tour).where(Tour.status.in_(["ket_thuc", "da_duyet"]), Tour.operator_id == u.id, Tour.end_date <= date.today())).scalars().all()
    todo = []
    for t in active:
        for a in T.allowed_actions(db, t, u):
            if a in ("confirm", "sign", "approve", "close", "kt_confirm", "cntt_check"):
                todo.append({"tour_id": t.id, "code": t.code, "name": t.name, "action": a})
    counts = {st: n for st, n in db.execute(select(Tour.status, func.count()).group_by(Tour.status)).all()}
    alerts = [a for a in db.execute(select(Alert).where(Alert.resolved == False).order_by(desc(Alert.created_at)).limit(300)).scalars()
              if u.role in a.to_roles.split(",") or u.role in ("chutich", "tgd", "cntt", "bks")][:60]
    from app.services import dashboard as DB_
    extra = DB_.build(db, u)
    # ══════════════════════════════════════════════════════════════════════════════════════════
    # TC-66 · GỬI KÈM MÃ PHÁP NHÂN ĐỂ KHỐI DÒNG TIỀN KHÔNG PHẢI HỎI THÊM MỘT LƯỢT
    # ══════════════════════════════════════════════════════════════════════════════════════════
    # Đo 18/9/2026: màn hình gọi `/dong-tien/meta` (0,85 giây) chỉ để biết mã pháp nhân, rồi mới
    # gọi được `/dong-tien/khung/{pn}` — hai cửa nối đuôi nhau, cộng ~1,1 giây vào cuối lần mở
    # trang. Gói này vốn đã về trước, nên nó mang luôn câu trả lời ấy đi cùng.
    #
    # HÀNG RÀO GIỮ NGUYÊN, KHÔNG NỚI MỘT LI: chỉ gửi cho vai nằm trong `XEM` của phân hệ dòng
    # tiền — đúng hàng rào của `/dong-tien/meta` — và dựng bằng CHÍNH hàm mà cửa ấy gọi, nên phép
    # lọc phạm vi không thể lệch giữa hai nơi. Vai ngoài danh sách thì trường này KHÔNG có mặt, và
    # màn hình rơi về lối cũ là tự gọi `/dong-tien/meta`.
    try:
        from app.api.v1.dong_tien import XEM as DT_XEM, danh_muc_phap_nhan
        if u.role in DT_XEM:
            extra = {**extra, "dong_tien_phap_nhan": danh_muc_phap_nhan(db, u)}
    except Exception:      # noqa: BLE001 — một danh mục lỗi không được làm sập cả bảng điều khiển
        pass
    payload = {"counts": counts, "n_tours": sum(counts.values()), "todo": todo[:100],
               "pending_requests": db.execute(select(func.count()).select_from(ServiceRequest).where(ServiceRequest.booking_id == None)).scalar(),
               "pending_params": db.execute(select(func.count()).select_from(Param).where(Param.status == "pending")).scalar(),
               "alerts": [alert_out(a) for a in alerts], "threshold": R.get_param(db, "nguong_bien"), **extra}
    return payload


# ---------- tours ----------
@router.get("/tours", tags=["tours"])
def list_tours(status: str | None = None, q: str = "", month: str = "", limit: int = 300, offset: int = 0, tour_type: str = "", mang: str = "", u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh sách tour có phân trang/tìm kiếm (mặc định 300 chuyến mới nhất) – 1.200+ tour nhập từ Vietrip. Mặc định ẩn dịch vụ lẻ (KLE) trừ khi tìm theo mã hoặc chọn tour_type."""
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload
    from app.models.core import Booking as _Bk
    # KS-5: NẠP SẴN quan hệ, đừng để tour_view đi hỏi từng chuyến một.
    #
    # Đo được trước khi sửa: 40 chuyến → 54 lượt truy vấn, 80 chuyến → 91 lượt. Số lượt tăng theo số
    # dòng nghĩa là có truy vấn nằm trong vòng lặp – ở đây là t.operator, t.bookings và b.sales, mỗi
    # thuộc tính lười một lượt cho MỖI chuyến. Câu bookings chạy 85 lần trong một lần mở màn hình.
    #
    # Trớ trêu là danh sách bookings dựng xong rồi bị `v.pop("bookings")` ném đi ngay dưới kia – màn
    # hình danh sách không cần nó. Nhưng booked_pax(t) lại đọc t.bookings để đếm khách, nên không bỏ
    # được, chỉ nạp sẵn được. Ba lượt selectinload thay cho hàng trăm lượt lẻ.
    qs = (select(Tour).order_by(desc(Tour.start_date))
          .options(selectinload(Tour.operator),
                   selectinload(Tour.bookings).selectinload(_Bk.sales)))
    qs = PV.loc(qs, Tour, u)                 # P6: phạm vi pháp nhân của phiên đăng nhập
    from app.services import segments as SEG
    try:
        cond = SEG.tour_cond(mang)          # mang=le / doan – lọc theo mảng kinh doanh
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if cond is not None: qs = qs.where(cond)
    if tour_type: qs = qs.where(Tour.tour_type == tour_type)
    elif not (q and q.upper().startswith("KLE")): qs = qs.where(Tour.tour_type != "non_package")
    if status: qs = qs.where(Tour.status.in_(status.split(",")))
    if q: qs = qs.where(or_(Tour.code.ilike(f"%{q}%"), Tour.name.ilike(f"%{q}%"), Tour.product_code.ilike(f"%{q}%")))
    if month:
        y, m = map(int, month.split("-")); qs = qs.where(func.extract("year", Tour.start_date) == y, func.extract("month", Tour.start_date) == m)
    # KS-5 · T5: CẮT THÌ ĐƯỢC, IM LẶNG THÌ KHÔNG.
    #
    # Cửa này vẫn luôn cắt ở 300 chuyến, nhưng trả về một mảng trần nên giao diện không có cách nào
    # biết là đã cắt – người đọc tin mình đang nhìn toàn bộ và ra quyết định trên phần bị cắt. Với
    # 1.200+ tour nhập từ Vietrip thì "toàn bộ" ấy thiếu ba phần tư.
    #
    # Từ 11/9/2026 phản hồi là một PHONG BÌ: rows · tong · offset · limit · cham_tran. Đây là thay
    # đổi PHÁ VỠ với mọi bên đang đọc mảng trần, nên web và phép thử sửa cùng một lần với chỗ này.
    tran = max(1, min(limit, 1000))
    tong = db.execute(select(func.count()).select_from(qs.order_by(None).subquery())).scalar_one()
    out = []
    for t in db.execute(qs.offset(offset).limit(tran)).scalars():
        v = T.tour_view(db, t)
        v.pop("bookings", None)
        out.append(v)
    return {"rows": out, "tong": tong, "offset": offset, "limit": tran,
            "cham_tran": offset + len(out) < tong}


@router.post("/tours", tags=["tours"], status_code=201)
def create_tour(data: S.TourCreate, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return T.tour_view(db, T.create(db, u, data), u)


def _tour(db: Session, tid: int) -> Tour:
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    return t


@router.get("/tours/{tid}", tags=["tours"])
def get_tour(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _tour(db, tid)
    v = T.tour_view(db, t, u)
    # Hỏi theo CHUYẾN chứ không theo vai trò, và CÙNG MỘT HÀM với `GET /tours/{id}/detail`:
    # `AC.che_gia_von` giữ ba bậc (giá vốn đầy đủ · chuyến đoàn của Kinh doanh · ba con số dự toán
    # cho Kinh doanh trên tour lẻ, Chủ tịch quyết 25/9/2026). Hai cửa chép hai khối che riêng đã
    # lệch nhau một lần rồi — lý do đầy đủ nằm trong chính hàm ấy.
    if AC.can_see_cost_tren_chuyen(u, t):
        v["audit"] = [audit_out(l) for l in db.execute(select(AuditLog).where(AuditLog.entity == f"tour:{t.code}").order_by(desc(AuditLog.id))).scalars()]
    return AC.che_gia_von(v, u, t, db)


@router.put("/tours/{tid}", tags=["tours"])
def edit_tour(tid: int, data: S.TourEdit, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return T.tour_view(db, T.edit(db, u, _tour(db, tid), data), u)


# ── Hai cửa của Sale Admin phòng Đoàn (24/9/2026) ───────────────────────────────────────────
# Khai quyền Ở CHỮ KÝ HÀM, đúng luật KS-2: chặn trong thân hàm thì bộ kiểm quyền của robot Kiểm
# soát không đọc được, và nó sẽ báo hai cửa này là "không có chặn nào".
#
# `cntt` KHÔNG có trong danh sách: đây là hai cửa NGHIỆP VỤ, không phải cửa vận hành hệ thống.
# Chủ tịch vẫn đi qua được bằng luật toàn quyền, và chỗ ấy khai trong chính hàm dịch vụ.
@router.post("/tours/{tid}/chuyen-dieu-hanh", tags=["tours"])
def chuyen_dieu_hanh_tour(tid: int, data: S.ActionNote | None = None,
                          u: User = Depends(require_roles("sales_admin", "chutich",
                                                          mo_ta="chuyển dự toán đoàn sang Điều hành")),
                          db: Session = Depends(get_db)):
    return {"message": T.chuyen_dieu_hanh(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/tra-lai-kinh-doanh", tags=["tours"])
def tra_lai_kinh_doanh_tour(tid: int, data: S.ActionNote | None = None,
                            u: User = Depends(require_roles("sales_admin", "chutich",
                                                            mo_ta="trả dự toán đoàn về Kinh doanh")),
                            db: Session = Depends(get_db)):
    return {"message": T.tra_lai_kinh_doanh(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/submit", tags=["tours"])
def submit_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.submit(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/confirm", tags=["tours"])
def confirm_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.confirm(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/approve", tags=["tours"])
def approve_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.approve(db, u, _tour(db, tid), (data.note if data else ""))}


# CỬA MỞ THÊM CHỖ — Chủ tịch quyết 25/9/2026, và nó đóng đúng một vòng hở đã có từ trước:
# `giu_cho.gia_han` bảo người dùng "Điều hành phải mở thêm chỗ" trong khi KHÔNG có cửa nào làm việc
# ấy. Quyền khai ở chữ ký (Điều hành + Sale Admin), và thân hàm khai lại — hai hàng rào, một danh
# sách, vì `tours.mo_them_cho` còn kiểm cả trạng thái, lý do và lợi nhuận.
@router.post("/tours/{tid}/mo-them-cho", tags=["tours"])
def mo_them_cho_tour(tid: int, data: S.MoThemCho,
                     u: User = Depends(require_roles(*T.MO_THEM_CHO_ROLES, mo_ta="mở thêm chỗ trên chuyến đang bán")),
                     db: Session = Depends(get_db)):
    return {"message": T.mo_them_cho(db, u, _tour(db, tid), data.so_cho, data.fixed_cost, data.ly_do)}


@router.post("/tours/{tid}/d7", tags=["tours"])
def d7_tour(tid: int, data: S.D7Decision, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.d7(db, u, _tour(db, tid), data.decision, getattr(data, "note", "") or "")}


@router.post("/tours/{tid}/close", tags=["tours"])
def close_tour(tid: int, data: S.TourClose, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.close(db, u, _tour(db, tid), data, getattr(data, "note", "") or "")}


@router.post("/tours/{tid}/kt-confirm", tags=["tours"])
def kt_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.kt_confirm(db, u, _tour(db, tid), (data.note if data else ""))}


@router.post("/tours/{tid}/cntt-check", tags=["tours"])
def cntt_tour(tid: int, data: S.ActionNote | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": T.cntt_check(db, u, _tour(db, tid), (data.note if data else ""))}


# ---------- requests & bookings ----------
def req_out(r: ServiceRequest, sla: int = 120, db: Session | None = None) -> dict:
    """Một yêu cầu luôn phải trả về: ai chịu trách nhiệm nhận việc, hạn xử lý và bước tiếp theo –
    không chỉ hiển thị thời gian chờ (Đề xuất 06/9 mục 4)."""
    t = r.tour
    waited = int((datetime.now() - r.created_at).total_seconds() / 60)
    deadline = r.created_at + timedelta(minutes=sla)
    op = t.operator if t and t.operator else None
    bk = db.get(Booking, r.booking_id) if (db and r.booking_id) else None
    if r.booking_id:
        view, sla_state = "hoan_tat", "hoan_tat"
        used = bk.sla_minutes if bk else None
        next_step = f"Đã tạo booking {bk.code}" + (f" sau {used} phút" if used is not None else "") if bk else "Đã tạo booking"
    else:
        ratio = waited / sla if sla else 0
        view = sla_state = "qua_han" if ratio >= 1 else "sap_qua_han" if ratio >= 0.75 else "cho_phan_cong"
        next_step = f"Điều hành tạo booking – phụ trách {op.full_name}" if op else "Điều hành tạo booking – chưa xác định người phụ trách"
    return {"id": r.id, "tour_id": r.tour_id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
            "tour_start": t.start_date if t else None, "sales_id": r.sales_id, "sales_name": r.sales.full_name if r.sales else "",
            "operator_id": op.id if op else None, "operator_name": op.full_name if op else "",
            "customer_name": r.customer_name, "customer_phone": r.customer_phone, "source": r.source, "care_note": r.care_note, "pax": r.pax,
            "campaign_code": r.campaign_code, "promo_code": r.promo_code, "discount": r.discount, "created_at": r.created_at, "booking_id": r.booking_id,
            "booking_code": bk.code if bk else "", "amount": max(0.0, ((t.price_per_pax or 0) * r.pax - (r.discount or 0)) if t else 0.0),
            "waited_minutes": waited, "deadline": deadline, "sla_minutes": sla, "sla_state": sla_state, "view": view, "next_step": next_step}


def booking_out(b: Booking) -> dict:
    """sla_known=False: booking nhập từ hệ thống khác (Vietrip) không mang mốc tiếp nhận yêu cầu
    → giao diện ghi 'Chưa đủ dữ liệu', không hiển thị là xử lý trong 0 phút."""
    return {"id": b.id, "code": b.code, "tour_id": b.tour_id, "sales_id": b.sales_id, "tour_code": b.tour.code if b.tour else "", "customer_name": b.customer_name,
            "customer_phone": b.customer_phone, "source": b.source, "pax": b.pax, "amount": b.amount, "discount": b.discount, "promo_code": b.promo_code,
            "sales_name": b.sales.full_name if b.sales else "", "sla_minutes": b.sla_minutes, "sla_ok": b.sla_ok,
            "sla_known": bool(b.request_id),
            "counts_for_target": b.counts_for_target, "created_at": b.created_at, "paid": (b.paid or 0), "due": (b.amount or 0) - (b.discount or 0) - (b.paid or 0),
            "adl": b.adl, "chd": b.chd, "inf": b.inf, "vietrip_id": b.vietrip_id, "tour_start": b.tour.start_date if b.tour else None,
            "company_id": b.company_id, "chua_gan_phap_nhan": b.company_id is None,
            # VPM-8 – màn hình phải NHẬN được số phiên bản thì mới có cái để gửi lại khi lưu.
            # Thiếu dòng này thì khoá 409 vĩnh viễn không bao giờ chạm tới, vì không ai gửi số nào.
            "phien_ban": b.phien_ban,
            **BK.booking_view(b)}


@router.get("/mang", tags=["bookings"])
def mang_catalog(u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="danh mục mảng kinh doanh")), db: Session = Depends(get_db)):
    """Danh mục mảng kinh doanh + đối chiếu hai quy tắc xác định mảng Đoàn.

    Mảng Đoàn được nhận theo HỢP của hai quy tắc (loại chuyến là đoàn, HOẶC mã tour bắt đầu bằng MICE) nên
    không tour nào bị rơi khỏi màn hình phòng Đoàn. Phần đối chiếu chỉ đích danh tour mà hai quy tắc bất đồng
    để Kinh doanh sửa dữ liệu gốc."""
    from app.services import segments as SEG
    return {"mang": SEG.MANG, "quy_tac_doan": {"loai_chuyen": list(SEG.DOAN_TYPES), "tien_to_ma": SEG.MICE_PREFIX},
            "doi_chieu": SEG.lech_quy_tac(db)}


@router.get("/requests", tags=["bookings"])
def list_requests(open_only: bool = False, view: str = "", mang: str = "", u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="yêu cầu đặt dịch vụ")), db: Session = Depends(get_db)):
    """view: cho_phan_cong / sap_qua_han / qua_han / hoan_tat / cua_toi (rỗng = tất cả)."""
    q = select(ServiceRequest).order_by(desc(ServiceRequest.created_at))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: q = q.where(ServiceRequest.sales_id.in_(vis))
    if open_only: q = q.where(ServiceRequest.booking_id == None)
    from app.services import segments as SEG
    try:
        cond = SEG.tour_cond(mang)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if cond is not None: q = q.join(Tour, Tour.id == ServiceRequest.tour_id).where(cond)
    sla = int(R.get_param(db, "sla_booking_phut"))
    rows = [req_out(r, sla, db) for r in db.execute(q).scalars()]
    if view == "cua_toi": rows = [r for r in rows if u.id in (r["sales_id"], r["operator_id"])]
    elif view: rows = [r for r in rows if r["view"] == view]
    return rows


@router.post("/requests", tags=["bookings"], status_code=201)
def create_request(data: S.RequestCreate, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = T.create_request(db, u, data)
    return {"request": req_out(r), "message": f"Đã gửi yêu cầu #{r.id} sang Điều hành (đồng hồ {R.get_param(db, 'sla_booking_phut'):.0f} phút bắt đầu)"}


@router.post("/requests/{rid}/booking", tags=["bookings"], status_code=201)
def create_booking(rid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(ServiceRequest, rid)
    if not r: raise HTTPException(404, "Không có yêu cầu")
    b, msg = T.create_booking(db, u, r)
    return {"booking": booking_out(b), "message": msg}


def _bookings_query(db: Session, u: User, q: str, status: str, tour_id: int | None, mang: str = ""):
    from app.services import segments as SEG
    qs = select(Booking).order_by(desc(Booking.created_at))
    qs = PV.loc(qs, Booking, u)              # P6: phạm vi pháp nhân của phiên đăng nhập
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: qs = qs.where(Booking.sales_id.in_(vis))   # NV KD: của mình; trưởng nhóm: của nhóm
    if tour_id: qs = qs.where(Booking.tour_id == tour_id)
    cond = SEG.tour_cond(mang)                       # mảng nằm ở TOUR nên phải nối bảng tours
    if cond is not None or q:
        qs = qs.join(Tour, Tour.id == Booking.tour_id)   # nối MỘT lần, kể cả khi vừa lọc mảng vừa tìm kiếm
    if cond is not None: qs = qs.where(cond)
    if q:
        like = f"%{q.strip()}%"
        qs = qs.where((Booking.code.ilike(like)) | (Booking.customer_name.ilike(like)) | (Booking.customer_phone.ilike(like)) | (Tour.code.ilike(like)))
    if status == "cancelled": qs = qs.where(Booking.cancelled == True)
    elif status == "locked": qs = qs.where(Booking.locked == True, Booking.cancelled == False)
    elif status in ("unpaid", "depo", "paid"): qs = qs.where(Booking.pmt_status == status.upper(), Booking.cancelled == False)
    elif status == "due": qs = qs.where(Booking.cancelled == False, Booking.pmt_status != "PAID")
    return qs


@router.get("/bookings", tags=["bookings"])
def list_bookings(limit: int = 100, offset: int = 0, q: str = "", status: str = "", tour_id: int | None = None, mang: str = "", u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="danh sách booking")), db: Session = Depends(get_db)):
    """status: unpaid / depo / paid / cancelled / locked / due (còn phải thu, chưa hủy).
    Danh sách có phân trang – tổng số lấy ở /bookings/count, KHÔNG suy từ số dòng đang hiển thị (B7)."""
    try:
        qs = _bookings_query(db, u, q, status, tour_id, mang)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return [booking_out(b) for b in db.execute(qs.offset(offset).limit(min(limit, 1000))).scalars()]


@router.get("/bookings/count", tags=["bookings"])
def count_bookings(q: str = "", status: str = "", tour_id: int | None = None, mang: str = "", u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="danh sách booking")), db: Session = Depends(get_db)):
    """Tổng số booking trong phạm vi người dùng được xem và số thỏa bộ lọc – để giao diện không lấy
    số dòng đang tải làm tổng toàn hệ thống (Ý kiến thẩm định 06/9/2026, B7)."""
    def n(query):
        return db.execute(select(func.count()).select_from(query.order_by(None).subquery())).scalar() or 0
    try:
        # "total" giữ nguyên phạm vi MẢNG đang xem, chỉ bỏ bộ lọc tìm kiếm/trạng thái – nếu không thì phòng Đoàn
        # thấy "12 / 10.074" và tưởng mình đang bị giấu dữ liệu.
        return {"total": n(_bookings_query(db, u, "", "", None, mang)),
                "filtered": n(_bookings_query(db, u, q, status, tour_id, mang))}
    except ValueError as ex:
        raise HTTPException(422, str(ex))


def _booking(db: Session, bid: int) -> Booking:
    b = db.get(Booking, bid)
    if not b: raise HTTPException(404, "Không có booking")
    return b


@router.get("/bookings/{bid}", tags=["bookings"])
def get_booking(bid: int, u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="booking")), db: Session = Depends(get_db)):
    b = _booking(db, bid)
    vis = AC.sales_ids_visible(db, u)
    if vis is not None and b.sales_id not in vis: raise HTTPException(403, "Chỉ xem được booking do mình / nhóm mình phụ trách")
    v = booking_out(b)
    from app.models.payments import Receipt, Retention
    v["receipts"] = [{"id": r.id, "code": r.code, "amount": r.amount, "method": r.method, "status": r.status, "payer": r.payer, "note": r.note, "created_at": r.created_at} for r in db.execute(select(Receipt).where(Receipt.booking_id == b.id).order_by(Receipt.id)).scalars()]
    v["retentions"] = [BK.retention_out(r, db) for r in db.execute(select(Retention).where(Retention.booking_id == b.id)).scalars()]
    return v


@router.put("/bookings/{bid}", tags=["bookings"])
def update_booking(bid: int, data: S.BookingCustomerIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return booking_out(BK.update_customer(db, u, _booking(db, bid), data.model_dump(exclude_none=True)))


@router.post("/bookings/{bid}/cancel", tags=["bookings"])
def cancel_booking(bid: int, data: S.BookingCancelIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return BK.cancel(db, u, _booking(db, bid), data.reason, data.charge, data.retain, data.expires_days)


# ---------- VPM-7: giữ chỗ có thời hạn ----------
# KHÔI PHỤC 11/9/2026. Khối này đã nằm trong commit VPM-7 (PR #4, đã gộp vào main) rồi BIẾN MẤT khỏi
# cây làm việc chung – một phiên khác lưu đè tệp này bằng bản mở từ trước khi VPM-7 gộp. Thiếu nó thì
# màn hình Booking gọi bốn đường dẫn không tồn tại, và commit tiếp theo chạm routes.py sẽ ĐẨY NGƯỢC
# việc đã gộp ra khỏi main mà không ai đọc thấy trong bản khác biệt.
#
# Đặt dưới tiền tố /bookings đã được cấp quyền sẵn, KHÔNG mở tiền tố API mới.
@router.get("/bookings/{bid}/giu-cho", tags=["bookings"])
def xem_giu_cho(bid: int, u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="giữ chỗ của booking")), db: Session = Depends(get_db)):
    from app.services import giu_cho as GC
    return GC.bang(db, _booking(db, bid))


@router.post("/bookings/{bid}/giu-cho/gia-han", tags=["bookings"])
def gia_han_giu_cho(bid: int, data: S.GiaHanGiuChoIn, u: User = Depends(require_roles(*AC.GIU_CHO_ROLES, mo_ta="gia hạn giữ chỗ")), db: Session = Depends(get_db)):
    from app.services import giu_cho as GC
    try:
        return GC.gia_han(db, u, _booking(db, bid), data.den, data.ly_do)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/bookings/{bid}/giu-cho/khoi-phuc", tags=["bookings"])
def khoi_phuc_giu_cho(bid: int, data: S.ActionNote, u: User = Depends(require_roles(*AC.GIU_CHO_ROLES, mo_ta="khôi phục giữ chỗ")), db: Session = Depends(get_db)):
    from app.services import giu_cho as GC
    try:
        return GC.khoi_phuc(db, u, _booking(db, bid), data.note)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/bookings/giu-cho/tong-hop", tags=["bookings"])
def tong_hop_giu_cho(u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="tổng hợp giữ chỗ")), db: Session = Depends(get_db)):
    from app.services import giu_cho as GC
    return GC.tong_hop(db)


# KS-2 (sửa 25/9/2026): cửa này khai quyền ở THÂN HÀM (`bookings.UNLOCK_ROLES`) còn chữ ký endpoint
# để trống, trong khi `/lock` ngay dưới thì khai ở chữ ký. Bộ kiểm quyền đọc chữ ký endpoint nên nó
# đọc ra "ai đăng nhập cũng gọi được" — người bị từ chối vẫn nhận 403 từ thân hàm, nhưng bản khai
# quyền của hệ thống nói sai. Khai ở CẢ HAI: hàng rào ngoài chặn theo màn hình, hàng rào trong chặn
# theo việc, và `bookings.unlock` còn được gọi từ chỗ khác chứ không chỉ từ endpoint này.
@router.post("/bookings/{bid}/unlock", tags=["bookings"])
def unlock_booking(bid: int, data: S.ActionNote, u: User = Depends(require_roles(*BK.UNLOCK_ROLES, mo_ta="mở khóa booking")), db: Session = Depends(get_db)):
    return {"message": BK.unlock(db, u, _booking(db, bid), data.note)}


@router.post("/bookings/{bid}/lock", tags=["bookings"])
def lock_booking(bid: int, data: S.ActionNote, u: User = Depends(require_roles("nv_dh", "tp_dh", "gd_kd", "tp_kd", "cntt")), db: Session = Depends(get_db)):
    b = _booking(db, bid); BK.lock(db, b, data.note or f"Khóa bởi {u.username}", u.username); db.commit()
    return {"message": f"Đã khóa {b.code}"}


@router.post("/bookings/check", tags=["bookings"])
def bookings_check(u: User = Depends(require_roles("tp_dh", "nv_dh", "gd_kd", "tp_kd", "ketoan", "cntt", "tgd")), db: Session = Depends(get_db)):
    return BK.robot_check(db)


@router.post("/robot/bookings/check", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_bookings_check(db: Session = Depends(get_db)):
    return BK.robot_check(db)


# ---------- tiền bảo lưu ----------
@router.get("/retentions", tags=["bookings"])
def list_retentions(status: str = "hieu_luc", q: str = "", u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="tiền bảo lưu")), db: Session = Depends(get_db)):
    from app.models.payments import Retention
    qs = select(Retention).order_by(desc(Retention.created_at))
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: qs = qs.join(Booking, Booking.id == Retention.booking_id).where(Booking.sales_id.in_(vis))
    if status and status != "all": qs = qs.where(Retention.status == status)
    if q:
        like = f"%{q.strip()}%"; qs = qs.where((Retention.code.ilike(like)) | (Retention.customer_name.ilike(like)) | (Retention.customer_phone.ilike(like)) | (Retention.tour_code.ilike(like)))
    return {"summary": BK.retention_summary(db), "rows": [BK.retention_out(r, db) for r in db.execute(qs.limit(500)).scalars()]}


def _ret(db: Session, rid: int):
    from app.models.payments import Retention
    r = db.get(Retention, rid)
    if not r: raise HTTPException(404, "Không có khoản bảo lưu")
    return r


@router.post("/retentions/{rid}/apply", tags=["bookings"])
def apply_retention(rid: int, data: S.RetentionApplyIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    rc = BK.apply_retention(db, u, _ret(db, rid), _booking(db, data.booking_id), data.amount)
    return {"message": f"Đã dùng {rc.amount:,.0f} đ bảo lưu cho booking – phiếu thu {rc.code}", "receipt": rc.code}


@router.post("/retentions/{rid}/refund", tags=["bookings"])
def refund_retention(rid: int, data: S.RetentionRefundIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    pr = BK.refund_retention(db, u, _ret(db, rid), data.amount, data.note)
    return {"message": f"Đã lập đề nghị hoàn tiền {pr.code} ({(pr.amount or 0):,.0f} đ) – chờ xác nhận/duyệt/chi", "request": pr.code}


@router.post("/retentions/{rid}/cancel", tags=["bookings"])
def cancel_retention(rid: int, data: S.ActionNote, u: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"message": BK.cancel_retention(db, u, _ret(db, rid), data.note)}


# ---------- params ----------
def param_out(p: Param) -> dict:
    return {"id": p.id, "key": p.key, "value": p.value, "label": p.label, "unit": p.unit, "effective_from": p.effective_from, "source": p.source,
            "status": p.status, "signed_chutich": p.signed_chutich, "signed_tgd": p.signed_tgd, "proposed_by": p.proposed_by, "created_at": p.created_at}


@router.get("/params", tags=["params"])
def list_params(u: User = Depends(require_roles(*AC.PARAM_ROLES, mo_ta="bảng tham số chính sách")), db: Session = Depends(get_db)):
    return [param_out(p) for p in db.execute(select(Param).order_by(Param.key, desc(Param.effective_from), desc(Param.id))).scalars()]


@router.post("/params", tags=["params"], status_code=201)
def propose_param(data: S.ParamPropose, u: User = Depends(require_roles("tp_dh", "gd_kd", "ptgd_doan", "ptgd_mkt", "ketoan", "hcns", "cntt", "tgd", "chutich")), db: Session = Depends(get_db)):
    ref = db.execute(select(Param).where(Param.key == data.key).order_by(desc(Param.id))).scalars().first()
    if not ref: raise Gate("THAM_SO", "Không có tham số này")
    # Tham số ngày đi qua cửa khác: float("01-12-2026") ném lỗi, nên trước 11/9/2026 không có
    # đường nào nhập được hai mốc vận hành thật. Kiểm định dạng thay cho kiểm số – vẫn là kiểm,
    # không phải bỏ kiểm: một mốc gõ sai định dạng thì bị đọc ra "chưa chốt" và im lặng.
    #
    # Dùng chung đúng một hàm đọc ngày với nơi ĐỌC mốc ra. Nếu cửa nhận rộng hơn chỗ đọc thì có
    # những giá trị nhập vào được mà đọc ra là None – tức là ký xong mà hệ thống vẫn bảo chưa chốt.
    if data.key in getattr(R, "THAM_SO_NGAY", ()):
        from app.services import moi_truong_du_lieu as _MT
        if _MT.doc_ngay(str(data.value)) is None:
            raise Gate("THAM_SO", f"Giá trị phải là ngày dạng {_MT.DINH_DANG_NGAY}, ví dụ {_MT._VI_DU_NGAY}")
    else:
        try: float(data.value)
        except ValueError: raise Gate("THAM_SO", "Giá trị phải là số")
    p = Param(key=data.key, value=data.value, label=ref.label, unit=ref.unit, effective_from=data.effective_from,
              source=data.source or ref.source, status="pending", proposed_by=u.username)
    db.add(p); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_tham_so", f"param:{data.key}", before={"value": ref.value}, after={"value": data.value, "hieu_luc": str(data.effective_from)}); db.commit()
    return {"param": param_out(p), "message": "Đã trình đề xuất – chờ Chủ tịch và TGĐ ký (Điều 1 MHQT)"}


@router.post("/params/{pid}/sign", tags=["params"])
def sign_param(pid: int, u: User = Depends(require_roles("chutich", "tgd")), db: Session = Depends(get_db)):
    from app.services import chu_ky as CK
    p = db.get(Param, pid)
    if not p or p.status != "pending": raise Gate("TRANG_THAI", "Không ở trạng thái chờ ký")
    # Người trình đề xuất không được tự ký duyệt đề xuất của chính mình (Phụ lục đối chiếu mục 3.2).
    CK.kiem_tra_nguoi_ky(u, ("chutich", "tgd"), nguoi_trinh=p.proposed_by,
                         da_ky={"chutich": "x" if p.signed_chutich else "", "tgd": "x" if p.signed_tgd else ""})
    setattr(p, f"signed_{u.role}", True)
    R.audit(db, u.username, u.role, "ky_tham_so", f"param:{p.key}", after={"id": p.id, "value": p.value})
    if p.signed_chutich and p.signed_tgd:
        p.status = "active"
        R.audit(db, u.username, u.role, "tham_so_hieu_luc", f"param:{p.key}", after={"value": p.value, "hieu_luc": str(p.effective_from)})
    db.commit()
    R.clear_param_cache()      # tham số vừa đổi – bỏ đệm ngay, không để hệ thống chạy bằng giá trị cũ
    return {"param": param_out(p), "message": "Đã ký" + (" – tham số có hiệu lực theo ngày đã ghi" if p.status == "active" else ", chờ chữ ký còn lại")}


# ---------- alerts / robots ----------
def alert_out(a: Alert) -> dict:
    from datetime import datetime as _dt
    han = getattr(a, "han_xu_ly", None)
    return {"id": a.id, "kind": a.kind, "level": a.level, "ref": a.ref, "message": a.message,
            "to_roles": a.to_roles, "created_at": a.created_at, "resolved": a.resolved,
            # KS-4 – vòng đời. `tre` tính ở máy chủ: màn hình không được tự suy hạn, vì mỗi nơi suy
            # một kiểu là mỗi nơi ra một danh sách "đang trễ" khác nhau.
            "trang_thai": getattr(a, "trang_thai", "moi"), "han_xu_ly": han,
            "tre": bool(han and not a.resolved and han < _dt.now()),
            "nguoi_nhan_id": getattr(a, "nguoi_nhan_id", None), "nhan_luc": getattr(a, "nhan_luc", None),
            "dong_luc": getattr(a, "dong_luc", None), "dong_boi_id": getattr(a, "dong_boi_id", None),
            "bang_chung": getattr(a, "bang_chung", ""), "nguon": getattr(a, "nguon", "")}


@router.get("/alerts", tags=["alerts"])
def list_alerts(trang_thai: str = "", nguon: str = "", cua_toi: bool = False,
                limit: int = 200, offset: int = 0,
                u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh sách cảnh báo, CÓ TRẦN và lọc ở máy chủ.

    KS-5 đo 10/9/2026: cửa này đọc TOÀN BỘ bảng alerts – 1.703 dòng đang mở – rồi mới lọc theo vai
    trò bằng Python. Danh sách không trần nghĩa là số dòng trả về tăng mãi theo dữ liệu: hôm nay
    1.703, sang năm không ai biết.

    Trần phải đặt SAU bộ lọc vai trò, không phải trước: cắt trước khi lọc thì người chỉ thấy cảnh
    báo của mình có thể nhận về một trang rỗng trong khi việc của họ nằm ở dòng thứ 400.
    """
    from sqlalchemy import func as _f, or_ as _or
    qs = select(Alert).order_by(Alert.resolved, desc(Alert.created_at))
    if trang_thai:
        qs = qs.where(Alert.trang_thai.in_(trang_thai.split(",")))
    if nguon:
        qs = qs.where(Alert.nguon == nguon)
    if cua_toi:
        qs = qs.where(Alert.nguoi_nhan_id == u.id)

    # ══════════════════════════════════════════════════════════════════════════════════════════
    # TC-66 · LỌC VAI TRÒ Ở MÁY CHỦ, TRONG CÂU TRUY VẤN — anh Tuấn 18/9/2026 duyệt chữa cửa này.
    # ══════════════════════════════════════════════════════════════════════════════════════════
    # Đo trên bản chạy thật: 0,87 — 0,95 — 1,30 giây, lần nào cũng chậm, không có lần nhanh. Lý do
    # nằm ngay ở đây: câu truy vấn KHÔNG có trần, nên mỗi lần bấm F5 là đọc TOÀN BỘ bảng alerts về
    # bộ nhớ (KS-5 đo 10/9/2026: 1.703 dòng đang mở) rồi mới lọc bằng Python và cắt trang. Trần
    # `limit` chỉ cắt phần TRẢ VỀ, không cắt phần ĐỌC LÊN.
    #
    # KHÔNG CHỮA BẰNG CHỖ NHỚ. `/alerts` là cửa CẢNH BÁO: nhớ lại năm phút nghĩa là giữ một cảnh
    # báo cũ trên màn hình năm phút, và giữ một cảnh báo ĐÃ XỬ LÝ cũng đúng ngần ấy lâu. Cái sai
    # ở đây là đọc quá nhiều, nên phải chữa đúng chỗ ấy.
    #
    # LUẬT PHÂN QUYỀN GIỮ NGUYÊN TỪNG CHỮ, chỉ đổi chỗ thi hành:
    #   · Lãnh đạo, Ban Kiểm soát, Kế toán, CNTT thấy MỌI cảnh báo. Trước 07/9/2026 dùng nhóm "xem
    #     tất cả" cũ (bảy vai trò); nay nhóm đó đã giải thể nên liệt kê thẳng — bốn nhóm có trách
    #     nhiệm giám sát toàn hệ thống.
    #   · Vai khác chỉ thấy cảnh báo GỬI TỚI vai mình. Cảnh báo là thứ phải có người nhận, không
    #     phải thứ ai cũng đọc cho biết.
    #
    # `to_roles` là một chuỗi ngăn bằng dấu phẩy, nên phải so KHỚP CẢ MẨU chứ không `LIKE '%vai%'`:
    # tìm chuỗi con thì vai "kt" trúng luôn mọi dòng gửi cho "ketoan", tức nới quyền mà không ai
    # thấy. Bốn nhánh dưới đây phủ đúng bốn vị trí một mẩu có thể đứng trong chuỗi: một mình, đầu,
    # cuối, giữa. Phép thử test_tc66 canh rằng nó cho ra ĐÚNG tập mà luật Python cũ cho ra.
    if u.role not in AC.BASE_VIEW + ("ketoan", "cntt"):
        vai = u.role
        qs = qs.where(_or(Alert.to_roles == vai,
                          Alert.to_roles.like(f"{vai},%"),
                          Alert.to_roles.like(f"%,{vai}"),
                          Alert.to_roles.like(f"%,{vai},%")))

    tran = max(1, min(limit, 500))
    # Đếm bằng COUNT chứ không bằng len() của danh sách đã đọc: `tong` là con số nói "còn bao nhiêu
    # dòng nữa", và đọc cả bảng chỉ để đếm là quay lại đúng cái vừa bỏ.
    tong = db.execute(select(_f.count()).select_from(qs.subquery())).scalar() or 0
    trang = list(db.execute(qs.offset(offset).limit(tran)).scalars())
    # Tên người nhận lấy MỘT lượt cho cả trang. Gắn quan hệ vào Alert thì mỗi dòng một lượt hỏi –
    # đúng cái N+1 mà KS-5 vừa gỡ ở /tours, không rước lại ở đây.
    ids = {a.nguoi_nhan_id for a in trang if a.nguoi_nhan_id}
    ten = dict(db.execute(select(User.id, User.username).where(User.id.in_(ids))).all()) if ids else {}
    dong = []
    for a in trang:
        v = alert_out(a)
        v["nguoi_nhan"] = ten.get(a.nguoi_nhan_id, "")
        dong.append(v)
    # Cùng một khuôn phong bì với GET /tours: rows · tong · offset · limit · cham_tran. Một khuôn
    # cho mọi danh sách thì giao diện viết MỘT lần; hai khuôn thì chỗ nào cũng phải nhớ khuôn nào.
    return {"rows": dong, "tong": tong, "offset": offset, "limit": tran,
            "cham_tran": offset + len(dong) < tong}


@router.post("/alerts/{aid}/nhan", tags=["alerts"])
def nhan_alert(aid: int, u: User = Depends(require_roles(*AC.CANH_BAO_ROLES, mo_ta="nhận cảnh báo")),
               db: Session = Depends(get_db)):
    """Nhận việc. Từ đây dòng này có TÊN MỘT NGƯỜI, không còn là việc của bốn vai trò."""
    from datetime import datetime as _dt
    a = db.get(Alert, aid)
    if not a:
        raise HTTPException(404, "Không có cảnh báo")
    if a.trang_thai not in ("moi", "bo_qua"):
        raise HTTPException(422, f"Cảnh báo đang ở trạng thái '{a.trang_thai}', không nhận lại được")
    a.trang_thai, a.nguoi_nhan_id, a.nhan_luc = "dang_xu_ly", u.id, _dt.now()
    R.audit(db, u.username, u.role, "nhan_canh_bao", f"alert:{aid}", after={"kind": a.kind, "ref": a.ref})
    db.commit()
    return alert_out(a)


class DongCanhBaoIn(BaseModel):
    bang_chung: str = ""
    bo_qua: bool = False


@router.post("/alerts/{aid}/resolve", tags=["alerts"])
def resolve_alert(aid: int, data: DongCanhBaoIn | None = None,
                  u: User = Depends(require_roles(*AC.CANH_BAO_ROLES, mo_ta="đóng cảnh báo")),
                  db: Session = Depends(get_db)):
    """Đóng một cảnh báo – phải nói dựa vào đâu.

    Trước 11/9/2026 cửa này KHÔNG có chặn nào: bất kỳ tài khoản nào đăng nhập được đều đóng được
    BẤT KỲ cảnh báo nào, kể cả cảnh báo đỏ của phòng khác. Thân hàm chỉ đặt resolved=True rồi ghi
    nhật ký, và bảng alerts không có cột ai-đóng nên sau khi đóng thì không truy lại được ai bấm và
    dựa vào đâu. Bộ kiểm KS-2 tìm ra; KS-4 khai các cột.

    Đóng mà không phải nói dựa vào đâu thì nút đóng là nút giấu việc – nên bằng chứng là BẮT BUỘC,
    trừ nhánh `bo_qua` dành cho dữ liệu lịch sử, nhánh ấy đòi lý do cũng dài như vậy.
    """
    from datetime import datetime as _dt
    from app.models.core import ALERT_CHUYEN
    a = db.get(Alert, aid)
    if not a:
        raise HTTPException(404, "Không có cảnh báo")
    d = data or DongCanhBaoIn()
    bc = (d.bang_chung or "").strip()
    if len(bc) < 10:
        raise HTTPException(422, "Đóng cảnh báo phải ghi bằng chứng: số chứng từ, mã bản ghi, hoặc "
                                 "lý do viết ra – ít nhất 10 ký tự.")
    dich = "bo_qua" if d.bo_qua else "dong"
    hien = a.trang_thai or "moi"
    # Không cho nhảy thẳng mới → đóng: đóng khi chưa ai nhận là đóng để cho sạch màn hình. Nhận rồi
    # đóng ngay trong một lần bấm thì vẫn phải đi qua 'dang_xu_ly' – và lúc ấy sổ có tên người nhận.
    if dich == "dong" and hien == "moi":
        raise HTTPException(422, "Chưa ai nhận cảnh báo này. Bấm Nhận trước rồi mới đóng được – "
                                 "đóng khi chưa ai nhận là đóng để cho sạch màn hình.")
    if dich not in ALERT_CHUYEN.get(hien, ()) and not (dich == "dong" and hien == "da_xu_ly"):
        raise HTTPException(422, f"Không chuyển được từ '{hien}' sang '{dich}'")
    a.trang_thai, a.resolved = dich, True
    a.dong_luc, a.dong_boi_id, a.bang_chung = _dt.now(), u.id, bc
    R.audit(db, u.username, u.role, "dong_canh_bao", f"alert:{aid}",
            after={"kind": a.kind, "ref": a.ref, "trang_thai": dich, "bang_chung": bc[:200]})
    db.commit()
    return alert_out(a)


@router.post("/robots/run", tags=["alerts"])
def run_robots(u: User = Depends(require_roles("cntt", "tgd", "chutich")), db: Session = Depends(get_db)):
    from app.services import ops as OPS
    n = R.run_robots(db) + OPS.check_missing_reports(db)
    R.audit(db, u.username, u.role, "chay_robot", "robot", after={"canh_bao_moi": n}); db.commit()
    return {"new_alerts": n, "message": f"Robot đã chạy, {n} cảnh báo mới"}


# ---------- audit / payroll ----------
def audit_out(l: AuditLog) -> dict:
    return {"id": l.id, "ts": l.ts, "actor": l.actor, "role": l.role, "action": l.action, "entity": l.entity, "before": l.before, "after": l.after, "hash": l.hash}


@router.get("/audit", tags=["audit"])
def list_audit(limit: int = 300, actor: str = "", action: str = "", entity: str = "",
               tu: str = "", den: str = "",
               u: User = Depends(require_roles(*AC.AUDIT_ROLES, mo_ta="nhật ký kiểm toán")), db: Session = Depends(get_db)):
    """Nhật ký nghiệp vụ – CHỈ ĐỌC, và không có endpoint ghi nào ở phân hệ này.

    Bộ lọc thêm 10/9/2026 (V7 Đợt 3). Trước bản này màn hình chỉ đọc được 300 dòng gần nhất, nên câu
    hỏi thật của một cuộc kiểm toán – "ai đã sửa chứng từ X", "tháng 6 ông A làm những gì" – trả lời
    bằng cách cuộn tay hoặc không trả lời được. Lọc ở MÁY CHỦ chứ không ở màn hình: lọc trên 300 dòng
    đã tải về thì bản ghi tháng 6 chưa từng rời khỏi cơ sở dữ liệu.

    `danh_muc` trả về tập giá trị đang có của ba cột lọc, để màn hình dựng ô chọn từ dữ liệu thật thay
    vì một danh sách chép tay sẽ lạc hậu ngay lần thêm hành động tiếp theo.
    """
    q = select(AuditLog)
    if actor: q = q.where(AuditLog.actor == actor)
    if action: q = q.where(AuditLog.action == action)
    # Đối tượng lọc theo TIỀN TỐ: entity ghi dạng "su_co_tour:SC2609-001", nên gõ "su_co_tour" phải ra
    # cả phân hệ, còn gõ đủ mã thì ra đúng một hồ sơ.
    if entity: q = q.where(AuditLog.entity.like(f"{entity}%"))
    for chuoi, dieu_kien in ((tu, True), (den, False)):
        if not chuoi: continue
        try:
            moc = datetime.fromisoformat(chuoi)
        except ValueError:
            raise HTTPException(422, "Mốc thời gian phải theo dạng YYYY-MM-DD hoặc YYYY-MM-DDTHH:MM")
        q = q.where(AuditLog.ts >= moc) if dieu_kien else q.where(AuditLog.ts <= moc)
    ok, n, msg = R.verify_chain(db)
    return {"chain_ok": ok, "records": n, "chain_message": msg,
            "danh_muc": {
                "actor": sorted({x for x in db.execute(select(AuditLog.actor).distinct()).scalars() if x}),
                "action": sorted({x for x in db.execute(select(AuditLog.action).distinct()).scalars() if x}),
                "entity": sorted({(x or "").split(":")[0] for x in db.execute(select(AuditLog.entity).distinct()).scalars() if x}),
            },
            "rows": [audit_out(l) for l in db.execute(q.order_by(desc(AuditLog.id)).limit(limit)).scalars()]}


@router.get("/payroll", tags=["payroll"])
def payroll(ym: str | None = None, u: User = Depends(require_roles("ketoan", "hcns", "tgd", "chutich", "cntt", "tp_dh")), db: Session = Depends(get_db)):
    ym = ym or date.today().strftime("%Y-%m")
    y, m = map(int, ym.split("-"))
    rows = R.monthly_payroll_draft(db, y, m)
    return {"ym": ym, "rows": rows, "total": sum(r["tien"] for r in rows)}


# ---------- robot API (n8n) ----------
# ---------- Ngoại lệ quyền có thời hạn (chỉ đạo 07/9/2026) ----------
class GrantIn(BaseModel):
    user_id: int
    kind: str                    # menu / capability
    value: str
    reason: str
    to_date: date | None = None      # rỗng = không thời hạn (chỉ Chủ tịch cấp được)
    from_date: date | None = None


@router.get("/access/grants", tags=["access"])
def grants_list(con_hieu_luc: bool = False, u: User = Depends(require_roles("chutich", "tgd", "cntt", "hcns", "bks")),
                db: Session = Depends(get_db)):
    from app.models.core import UserGrant, CAPABILITIES, GRANT_KINDS, GRANT_MAX_DAYS
    rows = list(db.execute(select(UserGrant).order_by(UserGrant.id.desc())).scalars())
    if con_hieu_luc: rows = [g for g in rows if g.hieu_luc()]
    ten = {x.id: x for x in db.execute(select(User)).scalars()}
    return {"rows": [{"id": g.id, "user_id": g.user_id,
                      "ho_ten": ten[g.user_id].full_name if g.user_id in ten else "",
                      "username": ten[g.user_id].username if g.user_id in ten else "",
                      "kind": g.kind, "value": g.value,
                      "ten_quyen": CAPABILITIES.get(g.value, g.value) if g.kind == "capability" else g.value,
                      "from_date": g.from_date, "to_date": g.to_date, "vo_han": g.vo_han(), "reason": g.reason,
                      "granted_by": g.granted_by, "approved_by": g.approved_by,
                      "active": g.active, "hieu_luc": g.hieu_luc()} for g in rows],
            "kinds": GRANT_KINDS, "capabilities": CAPABILITIES, "max_days": GRANT_MAX_DAYS}


@router.post("/access/grants", status_code=201, tags=["access"])
def grant_create(data: GrantIn, u: User = Depends(require_roles("chutich", "tgd")), db: Session = Depends(get_db)):
    """Cấp ngoại lệ quyền cho MỘT người, có thời hạn. Chỉ Chủ tịch hoặc TGĐ – người cấp cũng là người duyệt,
    nên không có bước chờ; điều bắt buộc là phải có hạn và có lý do bằng lời."""
    from app.models.core import UserGrant, CAPABILITIES, GRANT_MAX_DAYS
    t = db.get(User, data.user_id)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if data.kind not in ("menu", "capability"): raise HTTPException(422, "kind: menu / capability")
    if data.kind == "capability" and data.value not in CAPABILITIES:
        raise HTTPException(422, f"Năng lực không hợp lệ: {data.value}")
    if data.kind == "menu" and data.value not in AC.ALL_MENU_PATHS:
        raise HTTPException(422, f"Không có màn hình {data.value}")
    if not (data.reason or "").strip(): raise HTTPException(422, "Phải ghi lý do cấp quyền")
    tu = data.from_date or date.today()
    if data.to_date is None:
        # Không thời hạn: chỉ Chủ tịch, vì đây là quyền duy nhất trong hệ thống không tự co lại.
        if u.role != "chutich":
            raise HTTPException(403, "Ngoại lệ KHÔNG THỜI HẠN chỉ Chủ tịch HĐQT cấp được – "
                                     "quyền không có hạn là quyền không tự thu về")
    else:
        if data.to_date < tu: raise HTTPException(422, "Ngày hết hạn phải sau ngày bắt đầu")
        if (data.to_date - tu).days > GRANT_MAX_DAYS:
            raise HTTPException(422, f"Ngoại lệ có thời hạn tối đa {GRANT_MAX_DAYS} ngày – "
                                     f"cần lâu hơn thì để trống ngày hết hạn (Chủ tịch cấp), "
                                     f"hoặc đổi vai trò, hoặc sửa ma trận quyền")
    g = UserGrant(user_id=t.id, kind=data.kind, value=data.value, from_date=tu, to_date=data.to_date,
                  reason=data.reason.strip()[:300], granted_by=u.username, approved_by=u.username)
    db.add(g); db.flush()
    R.audit(db, u.username, u.role, "cap_ngoai_le_quyen", f"user:{t.username}",
            after={"kind": g.kind, "value": g.value, "den_ngay": str(g.to_date) if g.to_date else "khong_thoi_han",
                   "ly_do": g.reason})
    db.commit(); db.refresh(g)
    han = f"hết hiệu lực ngày {g.to_date:%d/%m/%Y}" if g.to_date else "KHÔNG THỜI HẠN – sẽ hiện ở danh sách rà quyền hằng tháng"
    return {"id": g.id, "message": f"Đã cấp cho {t.full_name}: {g.value}, {han}"}


@router.delete("/access/grants/{gid}", tags=["access"])
def grant_revoke(gid: int, u: User = Depends(require_roles("chutich", "tgd")), db: Session = Depends(get_db)):
    """Thu hồi sớm. Tắt cờ chứ không xóa dòng – phải truy được là quyền đã từng được cấp."""
    from app.models.core import UserGrant
    g = db.get(UserGrant, gid)
    if not g: raise HTTPException(404, "Không có ngoại lệ này")
    g.active = False
    R.audit(db, u.username, u.role, "thu_hoi_ngoai_le_quyen", f"grant:{gid}", after={"value": g.value})
    db.commit()
    return {"message": "Đã thu hồi ngoại lệ quyền", "id": gid}


# ---------- Nhật ký AI (chỉ đạo 07/9/2026) ----------
AI_LOG_ROLES = ("chutich", "tgd", "bks", "cntt", "ptgd_mkt")


@router.get("/ai/runs", tags=["ai"])
def ai_runs(tac_vu: str = "", trang_thai: str = "", limit: int = 200,
            u: User = Depends(require_roles(*AI_LOG_ROLES)), db: Session = Depends(get_db)):
    """Nhật ký mọi lần phần mềm dùng mô hình ngôn ngữ. Không mở cho mọi người: nội dung tóm tắt có tên khách."""
    from app.models.core import AiRun, AI_TASKS, AI_LEVELS, AI_REVIEW_STATES
    from app.services import ai_log as AL
    q = select(AiRun)
    if tac_vu: q = q.where(AiRun.tac_vu.in_(tac_vu.split(",")))
    if trang_thai: q = q.where(AiRun.trang_thai.in_(trang_thai.split(",")))
    rows = list(db.execute(q.order_by(AiRun.id.desc()).limit(min(limit, 500))).scalars())
    return {"rows": [{"id": r.id, "ts": r.ts, "tac_vu": r.tac_vu, "tac_vu_ten": AI_TASKS.get(r.tac_vu, r.tac_vu),
                      "muc": r.muc, "muc_ten": AI_LEVELS.get(r.muc, str(r.muc)), "ref": r.ref,
                      "phuc_vu_vai_tro": r.phuc_vu_vai_tro, "phuc_vu_nguoi": r.phuc_vu_nguoi,
                      "mo_hinh": r.mo_hinh, "nguon": r.nguon, "dau_vao_hash": r.dau_vao_hash,
                      "ket_qua": r.ket_qua, "tokens_vao": r.tokens_vao, "tokens_ra": r.tokens_ra,
                      "trang_thai": r.trang_thai, "trang_thai_ten": AI_REVIEW_STATES.get(r.trang_thai, r.trang_thai),
                      "hau_kiem_boi": r.hau_kiem_boi, "hau_kiem_luc": r.hau_kiem_luc,
                      "hau_kiem_ghi_chu": r.hau_kiem_ghi_chu, "loi": r.loi} for r in rows],
            "tong_hop": AL.tong_hop(db), "tac_vu": AI_TASKS, "muc": AI_LEVELS, "trang_thai_ten": AI_REVIEW_STATES}


class HauKiemIn(BaseModel):
    ket_luan: str                      # chap_nhan / da_sua / thu_hoi
    ghi_chu: str = ""


@router.post("/ai/runs/{rid}/hau-kiem", tags=["ai"])
def ai_hau_kiem(rid: int, data: HauKiemIn,
                u: User = Depends(require_roles("chutich", "tgd", "cntt", "ptgd_mkt", "gd_kd", "tp_kd")),
                db: Session = Depends(get_db)):
    """Người hậu kiểm chốt: chấp nhận / người đã sửa lại / thu hồi. Ban Kiểm soát KHÔNG có mặt ở đây –
    họ đọc và giám sát, chứ không phải người chịu trách nhiệm về nội dung AI gửi cho khách."""
    from app.models.core import AiRun, AI_REVIEW_STATES
    ket_luan, ghi_chu = data.ket_luan, data.ghi_chu
    if ket_luan not in ("chap_nhan", "da_sua", "thu_hoi"):
        raise HTTPException(422, "ket_luan: chap_nhan / da_sua / thu_hoi")
    r = db.get(AiRun, rid)
    if not r: raise HTTPException(404, "Không có bản ghi nhật ký AI")
    if r.trang_thai not in ("cho_hau_kiem", "chap_nhan", "da_sua", "thu_hoi"):
        raise HTTPException(422, "Bản ghi này không thuộc diện phải hậu kiểm")
    before = {"trang_thai": r.trang_thai}
    r.trang_thai, r.hau_kiem_boi, r.hau_kiem_luc, r.hau_kiem_ghi_chu = ket_luan, u.username, datetime.now(), ghi_chu[:300]
    R.audit(db, u.username, u.role, "hau_kiem_ai", f"ai_run:{rid}", before=before, after={"trang_thai": ket_luan, "ghi_chu": ghi_chu[:300]})
    db.commit()
    return {"message": f"Đã ghi nhận: {AI_REVIEW_STATES[ket_luan]}", "id": rid, "trang_thai": ket_luan}


@router.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)):
    ok, n, msg = R.verify_chain(db)
    return {"status": "ok", "audit_chain_ok": ok, "audit_records": n, "time": datetime.now().isoformat()}


@router.post("/robot/run", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_run(db: Session = Depends(get_db)):
    n = R.run_robots(db)
    R.audit(db, "robot", "robot", "chay_robot_api", "robot", after={"canh_bao_moi": n}); db.commit()
    return {"new_alerts": n}


@router.get("/robot/alerts", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_alerts(db: Session = Depends(get_db)):
    return [alert_out(a) for a in db.execute(select(Alert).where(Alert.resolved == False)).scalars()]


@router.get("/robot/tours", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_tours(db: Session = Depends(get_db)):
    out = []
    for t in db.execute(select(Tour)).scalars():
        v = T.tour_view(db, t); v.pop("bookings", None); out.append(v)
    return out


# ---------- Robot R7 – báo cáo tự động ----------
from app.models.reports_auto import AutoReport


def _rep_out(r: AutoReport) -> dict:
    return {"id": r.id, "kind": r.kind, "period": r.period, "content": r.content, "comment": r.comment, "data": r.data, "created_by": r.created_by, "created_at": r.created_at}


@router.get("/auto-reports", tags=["robot"])
def auto_reports(kind: str | None = None, limit: int = 30, u: User = Depends(require_roles("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "ketoan", "cntt", "bks", "hcns", "tp_dh", "gd_kd", "tp_kd")), db: Session = Depends(get_db)):
    q = select(AutoReport).order_by(desc(AutoReport.created_at))
    if kind: q = q.where(AutoReport.kind == kind)
    return [_rep_out(r) for r in db.execute(q.limit(limit)).scalars()]


@router.post("/auto-reports/{kind}", tags=["robot"])
def auto_report_run(kind: str, u: User = Depends(require_roles("cntt", "tgd", "chutich", "ketoan")), db: Session = Depends(get_db)):
    from app.services import dashboard as DB_
    try:
        r = DB_.run_report(db, kind, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": f"Robot đã lập báo cáo {kind} {r.period}", "report": _rep_out(r)}


@router.post("/robot/report/{kind}", tags=["robot"], dependencies=[Depends(robot_auth)])
def robot_report(kind: str, db: Session = Depends(get_db)):
    """n8n gọi theo lịch: 20:30 hằng ngày (ngay), thứ Bảy (tuan), ngày 10 (thang). Trả markdown để gửi Zalo/Email."""
    from app.services import dashboard as DB_
    try:
        r = DB_.run_report(db, kind)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"period": r.period, "markdown": r.content, "comment": r.comment}


# ---------- dung lượng dữ liệu ----------
@router.get("/he-thong/dung-luong", tags=["he-thong"])
def dung_luong(u: User = Depends(require_roles("cntt", "chutich", "tgd", "bks", "ketoan")), db: Session = Depends(get_db)):
    """Số dòng và dung lượng từng bảng, để biết chỗ nào đang phình trước khi nghĩ tới nâng cấu hình.

    Chỉ ĐỌC. Cố ý không kèm nút xoá: xoá dữ liệu vận hành là việc phải quyết theo từng bảng cụ thể,
    không phải một nút trên màn hình.
    """
    from app.db.session import Base
    ten_bang = sorted(Base.metadata.tables.keys())
    rows = []
    for t in ten_bang:
        try:
            n = db.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() or 0
        except Exception:
            db.rollback(); continue
        rows.append({"bang": t, "so_dong": int(n)})
    kich_thuoc = {}
    try:    # PostgreSQL: kích thước thật trên đĩa, kể cả chỉ mục
        for ten, byte_ in db.execute(text(
                "SELECT relname, pg_total_relation_size(relid) FROM pg_catalog.pg_statio_user_tables")).all():
            kich_thuoc[ten] = int(byte_)
    except Exception:
        db.rollback()
    for r in rows:
        r["bytes"] = kich_thuoc.get(r["bang"], 0)
    rows.sort(key=lambda r: (-r["bytes"], -r["so_dong"]))
    return {"tong_so_dong": sum(r["so_dong"] for r in rows), "tong_bytes": sum(r["bytes"] for r in rows),
            "so_bang": len(rows), "bang": rows}
