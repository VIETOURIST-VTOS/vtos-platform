"""Số liệu cho màn hình Tài khoản & phân quyền (đặc tả 07/9/2026, mục B2–B6).

Tách khỏi services/access.py có chủ đích: access.py là NGUỒN QUYỀN – nó quyết định ai xem được gì và
được nhiều nơi trong máy chủ gọi tới. Tệp này chỉ ĐỌC và TRÌNH BÀY lại nguồn đó cho một màn hình quản
trị. Trộn hai việc vào một tệp là mở đường cho một thay đổi giao diện vô tình sửa quyền.
"""
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.core import User, ROLES, AuditLog, Company
from app.models.hr import Employee
from app.services import access as AC
from app.services import ho_so_nhan_vien as HSNV

NGAY_BO_HOANG = 60          # quá số ngày này không đăng nhập thì coi là tài khoản bỏ hoang


def ma_tran() -> dict:
    """Ma trận công bố: vai trò × màn hình, dựng THẲNG từ access.py.

    Không có bản sao nào của ma trận ở đây. Màn hình chỉ được phép hiển thị đúng cái máy chủ đang áp
    dụng – nếu chép ra một bảng riêng thì đến lúc lệch nhau, người đọc tin bảng chứ không tin hệ thống.
    """
    paths = sorted(AC.MENU_ROLES)
    rows = []
    for vai, ten in ROLES.items():
        gioi_han = vai in AC.RESTRICTED_ROLE_MENUS
        mo = set(AC.RESTRICTED_ROLE_MENUS[vai]) if gioi_han else {p for p, v in AC.MENU_ROLES.items() if vai in v}
        rows.append({
            "vai_tro": vai, "ten": ten,
            "man_hinh": {p: (p in mo) for p in paths},
            "so_mo": len([p for p in paths if p in mo]),
            "danh_sach_cho_phep": gioi_han,
            "chi_doc": vai in AC.READ_ONLY_ROLES,
            "toan_quyen": vai in AC.FULL_VIEW,
            "tab_nhan_su": [t for t, v in AC.HR_TAB_ROLES.items() if vai in v],
        })
    return {
        "man_hinh": paths, "rows": rows, "tong": len(paths),
        "hr_tabs": AC.HR_TABS,
        "ghi_chu": [
            "Chủ tịch HĐQT và Tổng giám đốc xem được mọi màn hình – đúng hai người.",
            "Ban Kiểm soát đọc được mọi màn hình nhưng bị chặn mọi thao tác ghi (Luật Doanh nghiệp).",
            "Tài xế & HDV, Giám đốc điều hành đội xe và Chuyên viên Visa dùng DANH SÁCH CHO PHÉP: "
            "màn hình mới thêm vào hệ thống sẽ không tự động mở cho họ.",
            "Bảng lương tách khỏi Hồ sơ nhân sự: xem cột 'tab nhân sự' để biết ai mở được tab nào.",
        ],
    }


def _ho_so_theo_user(db: Session) -> dict:
    return {e.user_id: e for e in db.execute(select(Employee).where(Employee.user_id != None)).scalars()}


def danh_sach_tai_khoan(db: Session) -> list[dict]:
    hs = _ho_so_theo_user(db)
    cos = {c.id: c.code for c in db.execute(select(Company)).scalars()}
    ra = []
    for u in db.execute(select(User).order_by(User.username)).scalars():
        e = hs.get(u.id)
        ra.append({
            "id": u.id, "username": u.username, "full_name": u.full_name,
            "role": u.role, "role_name": ROLES.get(u.role, u.role),
            "department": u.department, "sales_group": u.sales_group, "staff_code": u.staff_code,
            "company_id": u.company_id, "company": cos.get(u.company_id, ""), "email_cong_viec": u.email_cong_viec or "",
            "active": bool(u.active), "ngoai_bien_che": bool(u.ngoai_bien_che),
            "must_change_password": bool(u.must_change_password),
            "last_login": u.last_login,
            "chua_dang_nhap": u.last_login is None,
            "role_changed_at": u.role_changed_at, "role_changed_by": u.role_changed_by,
            "ho_so": e.code if e else "", "ho_so_active": bool(e.active) if e else None,
            # HS-6 · 16/10/2026 — ID hồ sơ, không chỉ mã. Cửa ghi nghỉ việc
            # (`POST /bien-dong-ns/nghi-viec`) làm việc theo `employee_id`, nên màn hình
            # Tài khoản chỉ có mã thì phải tra thêm một lượt — và lượt tra ấy là chỗ sinh ra
            # cách nối thứ hai giữa tài khoản và hồ sơ. Trả thẳng ID ở đây để chỉ còn một cách.
            "ho_so_id": e.id if e else None,
        })
    # HS-8 · 17/10/2026 — XẾP THEO SƠ ĐỒ TỔ CHỨC, không theo tên đăng nhập.
    #
    # Chủ tịch duyệt thứ tự này ngày 15/10 (bản vẽ số 1: «gom theo phòng, xếp theo cấp bậc»), và
    # `ho_so_nhan_vien.xep_bang_tai_khoan` được viết đúng hôm ấy — rồi KHÔNG AI GỌI NÓ. Bảng 121
    # dòng vẫn xếp theo `username`, nên Chủ tịch mở màn hình ra thấy thứ tự chữ cái và báo lại.
    #
    # Bài học ghi thẳng ở đây: một lớp tính không có ai gọi thì CHƯA PHẢI việc đã xong. Phép thử
    # của vòng ấy xanh hết — vì nó thử đúng hàm ấy, không thử xem màn hình có dùng hàm ấy không.
    xep = HSNV.xep_bang_tai_khoan(ra)
    return [ng for n in xep["nhom"] for ng in n["nguoi"]]


def chenh_lech(db: Session) -> dict:
    """Sáu danh sách đối chiếu của thẻ 3. Mỗi danh sách là một câu hỏi cụ thể, không phải một cảnh báo chung."""
    users = list(db.execute(select(User)).scalars())
    emps = list(db.execute(select(Employee)).scalars())
    theo_uid = {e.user_id: e for e in emps if e.user_id}
    moc = datetime.now() - timedelta(days=NGAY_BO_HOANG)

    def u_out(u, **kw):
        return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
                "role_name": ROLES.get(u.role, u.role), "staff_code": u.staff_code, **kw}

    # 1. nhân sự đang làm việc mà chưa có tài khoản
    chua_tk = [{"id": e.id, "code": e.code, "full_name": e.full_name, "department": e.department}
               for e in emps if e.active and not e.user_id]
    # 2. tài khoản hoạt động nhưng không có hồ sơ, hoặc hồ sơ đã nghỉ
    bo_quen = []
    for u in users:
        if not u.active or u.ngoai_bien_che: continue
        e = theo_uid.get(u.id)
        if e is None:
            bo_quen.append(u_out(u, ly_do="không có hồ sơ nhân sự"))
        elif not e.active:
            bo_quen.append(u_out(u, ly_do=f"hồ sơ {e.code} đã ghi nghỉ việc"))
    # 3. còn mật khẩu tạm do người khác đặt
    mat_khau_tam = [u_out(u) for u in users if u.active and u.must_change_password]
    # 4. chưa đăng nhập bao giờ, hoặc quá lâu không đăng nhập
    bo_hoang = [u_out(u, last_login=u.last_login,
                      ly_do="chưa đăng nhập bao giờ" if u.last_login is None else f"không đăng nhập quá {NGAY_BO_HOANG} ngày")
                for u in users if u.active and (u.last_login is None or u.last_login < moc)]
    # 5. chưa gán pháp nhân chủ quản
    chua_phap_nhan = [u_out(u) for u in users if u.active and not u.company_id]
    # 6. hồ sơ trùng: cùng họ tên, cùng phòng, hai mã khác nhau (trường hợp Trần Vinh mã 296/297)
    gom: dict = {}
    for e in emps:
        if not e.active: continue
        gom.setdefault((e.full_name.strip().lower(), e.department), []).append(e)
    trung = [{"full_name": v[0].full_name, "department": v[0].department,
              "ma": [x.code for x in v], "so_luong": len(v)} for v in gom.values() if len(v) > 1]

    # 7. ngoại lệ quyền KHÔNG THỜI HẠN – quyền duy nhất trong hệ thống không tự co lại, nên phải nổi lên
    #    ở đây mỗi kỳ rà quyền. Đổi "tự hết hạn" lấy "không bao giờ bị quên".
    from app.models.core import UserGrant, CAPABILITIES
    ten_u = {x.id: x for x in users}
    vo_han = []
    for g in db.execute(select(UserGrant).where(UserGrant.active == True)).scalars():
        if not (g.vo_han() and g.hieu_luc()): continue
        x = ten_u.get(g.user_id)
        vo_han.append({"id": g.id, "user_id": g.user_id,
                       "full_name": x.full_name if x else f"user:{g.user_id}",
                       "staff_code": x.staff_code if x else "",
                       "role_name": ROLES.get(x.role, "") if x else "",
                       "quyen": CAPABILITIES.get(g.value, g.value),
                       "ly_do": f"cấp {g.from_date:%d/%m/%Y} bởi {g.approved_by} – {g.reason}"})

    ds = {"nhan_su_chua_co_tai_khoan": chua_tk, "tai_khoan_bo_quen": bo_quen,
          "con_mat_khau_tam": mat_khau_tam, "bo_hoang": bo_hoang,
          "chua_gan_phap_nhan": chua_phap_nhan, "ho_so_trung": trung,
          "ngoai_le_vo_han": vo_han}
    return {"danh_sach": ds, "dem": {k: len(v) for k, v in ds.items()},
            "tong": sum(len(v) for v in ds.values()), "nguong_bo_hoang_ngay": NGAY_BO_HOANG}


# Đổi quyền AI cũng là đổi quyền: cùng một câu hỏi "ai được làm gì", chỉ khác chủ thể là máy chứ không
# phải người. Để ở nhật ký riêng thì lúc rà quyền hằng tháng sẽ nhìn sót đúng phần rủi ro nhất.
# Gán pháp nhân chủ quản cho tài khoản CŨNG là đổi quyền, dù nó không nằm trong ma trận vai trò:
# từ 08/9/2026 pháp nhân của tài khoản quyết định người đó nhìn thấy dữ liệu của công ty nào. Một lần
# gán hàng loạt cho hơn trăm tài khoản mà không hiện ở nhật ký quyền là đúng loại thay đổi lớn nhất
# đi qua lặng lẽ nhất.
HANH_DONG_QUYEN = ("dang_nhap", "sua_tai_khoan", "dat_lai_mat_khau", "doi_mat_khau",
                   "cap_ngoai_le_quyen", "thu_hoi_ngoai_le_quyen",
                   "dat_quyen_ai", "tat_khan_ai", "hau_kiem_ai",
                   "suy_phap_nhan_tai_khoan_tu_ho_so")


def nhat_ky_quyen(db: Session, limit: int = 200, bo_dang_nhap: bool = True) -> list[dict]:
    """Nhật ký thao tác về quyền. Mặc định BỎ dòng đăng nhập: mỗi người đăng nhập vài lần một ngày,
    để lẫn vào thì việc cấp và thu quyền – thứ cần nhìn – bị trôi mất giữa hàng nghìn dòng."""
    hd = tuple(a for a in HANH_DONG_QUYEN if not (bo_dang_nhap and a == "dang_nhap"))
    rows = db.execute(select(AuditLog).where(AuditLog.action.in_(hd))
                      .order_by(AuditLog.id.desc()).limit(min(limit, 1000))).scalars()
    return [{"id": r.id, "ts": r.ts, "actor": r.actor, "role": r.role,
             "role_name": ROLES.get(r.role, r.role), "action": r.action,
             "entity": r.entity, "before": r.before, "after": r.after} for r in rows]


def ma_tran_xlsx(db: Session | None = None) -> bytes:
    """Xuất ma trận ra Excel để TGĐ ký rà quyền hằng tháng – yêu cầu ở Bản đề xuất v2.0 mục 6."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    mt = ma_tran()
    wb = Workbook(); ws = wb.active; ws.title = "Ma tran phan quyen"
    F = "Arial"
    hdr = PatternFill("solid", fgColor="1F3864"); yes = PatternFill("solid", fgColor="C6E0B4")
    full = PatternFill("solid", fgColor="FFF2CC")
    thin = Side(style="thin", color="B0B7C3"); box = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = "MA TRẬN PHÂN QUYỀN VTOS – BẢN ĐANG ÁP DỤNG TRÊN HỆ THỐNG"
    ws["A1"].font = Font(name=F, size=14, bold=True, color="1F3864")
    ws["A2"] = f"Xuất lúc {datetime.now():%H:%M %d/%m/%Y}. Đây là bản đọc thẳng từ máy chủ, không nhập tay."
    ws["A2"].font = Font(name=F, size=10, italic=True)
    for i, g in enumerate(mt["ghi_chu"]):
        ws.cell(row=3 + i, column=1, value="• " + g).font = Font(name=F, size=9, italic=True, color="606060")

    r0 = 4 + len(mt["ghi_chu"])
    head = ["Vai trò", "Mã", "Số màn hình", "Tab nhân sự"] + mt["man_hinh"]
    for j, h in enumerate(head, start=1):
        c = ws.cell(row=r0, column=j, value=h)
        c.font = Font(name=F, size=9, bold=True, color="FFFFFF"); c.fill = hdr
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True, textRotation=90 if j > 4 else 0)
        c.border = box
    ws.row_dimensions[r0].height = 120

    for i, row in enumerate(mt["rows"]):
        r = r0 + 1 + i
        for j, v in enumerate([row["ten"], row["vai_tro"], row["so_mo"],
                               ", ".join(row["tab_nhan_su"]) or "—"], start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.font = Font(name=F, size=9, bold=(j == 1)); c.border = box
            if row["toan_quyen"] or row["chi_doc"]: c.fill = full
        for k, p in enumerate(mt["man_hinh"]):
            c = ws.cell(row=r, column=5 + k, value="x" if row["man_hinh"][p] else None)
            c.font = Font(name=F, size=9); c.alignment = Alignment(horizontal="center"); c.border = box
            if row["man_hinh"][p]: c.fill = full if (row["toan_quyen"] or row["chi_doc"]) else yes

    ky = r0 + len(mt["rows"]) + 3
    ws.cell(row=ky, column=1, value="Người rà: ………………………").font = Font(name=F, size=10)
    ws.cell(row=ky, column=5, value="Tổng giám đốc xác nhận: ………………………").font = Font(name=F, size=10)

    ws.freeze_panes = ws.cell(row=r0 + 1, column=5)
    for j, w in enumerate([26, 14, 12, 22], start=1): ws.column_dimensions[get_column_letter(j)].width = w
    for k in range(len(mt["man_hinh"])): ws.column_dimensions[get_column_letter(5 + k)].width = 4.5

    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()
