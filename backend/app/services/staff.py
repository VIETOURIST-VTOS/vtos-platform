"""Danh sách nhân viên chính thức (mã NV HCNS / phòng ban / họ tên / nhóm) – nạp từ app/data/nhan_su_*.json (trích từ bảng lương HCNS, không chứa lương).

- Mã NV = mã trên bảng lương HCNS (vd 114), dùng làm Employee.code và User.staff_code – khớp với ô "Mã nhân viên" của form báo cáo ngày.
- Ghép với tài khoản VTOS theo họ tên (không dấu, không phân biệt hoa thường); người có tài khoản (Vietrip/seed) được cập nhật vai trò, phòng, nhóm.
- Người chưa có tài khoản nhưng thuộc khối phải báo cáo ngày (KD, Đoàn, ĐH, MKT, CNTT, Kế toán, HCNS) → tạo tài khoản: username = họ tên không dấu, mật khẩu mặc định = mã NV (HCNS yêu cầu đổi khi đăng nhập lần đầu).
- Từ 07/9/2026: tài xế đang đứng tên lái xe, HDV và chuyên viên visa CÓ tài khoản (vai trò xe_hdv / nv_visa,
  chỉ thấy màn hình của mình). Bảo vệ, pháp chế, QH nhà đầu tư chưa có vai trò → chỉ hồ sơ nhân sự.
- Tài khoản của người không còn trong bảng lương bị KHÓA (active=False), không xóa: nhật ký nghiệp vụ và
  chứng từ đã ghi vẫn trỏ tới tài khoản đó, xóa đi là mất dấu vết người thực hiện.
"""
import json, re, unicodedata
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.core import User, ROLES
from app.models.hr import Employee
from app.services import rules as R

DATA = Path(__file__).resolve().parent.parent / "data" / "nhan_su_2026-09.json"
ACCOUNT_DEPTS = ("kd_le", "kd_doan", "dieu_hanh", "marketing", "cntt", "ketoan", "hcns", "ban_tgd", "doi_xe", "huong_dan", "visa")
DEPT_ROLE_DEFAULT = {"kd_le": "nv_kd", "kd_doan": "nv_kd", "dieu_hanh": "nv_dh", "marketing": "nv_mkt", "cntt": "cntt", "ketoan": "ketoan", "hcns": "hcns", "visa": "nv_visa"}
GIU_TAI_KHOAN = ("chutich", "tgd", "cntt")   # tài khoản hệ thống: không hạ quyền, không khóa theo bảng lương


def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def name_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", strip_accents(s).lower())


def load_master() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))["nhan_su"]


def import_master(db: Session, actor: User | None = None, create_accounts: bool = True, reset_passwords: bool = False,
                  close_accounts: bool = True, dry_run: bool = False) -> dict:
    rows = load_master()
    emps = list(db.execute(select(Employee)).scalars())
    by_code = {e.code: e for e in emps}
    by_name = {}
    for e in emps: by_name.setdefault(name_key(e.full_name), e)
    users = list(db.execute(select(User)).scalars())
    u_by_name = {}
    for u in users: u_by_name.setdefault(name_key(u.full_name), u)
    u_by_code = {u.staff_code: u for u in users if u.staff_code}
    dang_gan: set[int] = set()      # id tài khoản ĐANG gắn với một người trong bảng lương – gom trong vòng lặp
                                    # bên dưới chứ không truy vấn lại, vì phiên làm việc này không tự flush.
    stat = {"updated": 0, "created": 0, "users_linked": 0, "users_created": 0, "passwords_reset": 0, "roles_changed": [], "skipped": [], "users_closed": []}
    for r in rows:
        code, name = str(r["ma"]), r["ten"].strip()
        e = by_code.get(code) or by_name.get(name_key(name))
        if e is None:
            e = Employee(code=code, full_name=name, department=r["phong"], position=r["vi_tri"]); db.add(e); db.flush()
            stat["created"] += 1; by_code[code] = e
        else:
            if e.code != code and code not in by_code:   # đổi mã NS/VT sang mã HCNS
                e.code = code; by_code[code] = e
            stat["updated"] += 1
        e.full_name, e.department, e.position = name, r["phong"], r["vi_tri"]
        e.title, e.sales_group, e.office = r.get("chuc_vu", ""), r.get("nhom", ""), r.get("van_phong", "hcm") or "hcm"
        e.contract_type = r.get("hop_dong") or ("ctv" if r["phong"] == "huong_dan" else "hdld")
        e.probation = bool(r.get("thu_viec")); e.active = True
        # tài khoản
        u = None
        if e.user_id: u = db.get(User, e.user_id)
        if u is None: u = u_by_code.get(code) or u_by_name.get(name_key(name))
        role = r.get("vai_tro") or DEPT_ROLE_DEFAULT.get(r["phong"], "")
        if u is None and create_accounts and r["phong"] in ACCOUNT_DEPTS and role:
            base = name_key(name)[:24] or f"nv{code}"
            uname = base; n = 1
            while db.execute(select(User).where(User.username == uname)).scalars().first():
                n += 1; uname = f"{base}{n}"
            u = User(username=uname, full_name=name, role=role, department=r["phong"], password_hash=hash_password(code), active=True)
            db.add(u); db.flush(); stat["users_created"] += 1; u_by_name[name_key(name)] = u
        if u is not None:
            dang_gan.add(u.id)
            if e.user_id != u.id: e.user_id = u.id; stat["users_linked"] += 1
            if role and u.role != role and u.role not in GIU_TAI_KHOAN:   # không hạ quyền tài khoản hệ thống
                stat["roles_changed"].append(f"{u.username}: {ROLES.get(u.role, u.role)} → {ROLES.get(role, role)}"); u.role = role
            u.department, u.sales_group, u.staff_code = r["phong"], r.get("nhom", ""), code
            u.full_name = name; u.active = True
            if reset_passwords and u.role not in GIU_TAI_KHOAN:   # đặt lại mật khẩu = mã NV (tài khoản nạp từ Vietrip có mật khẩu ngẫu nhiên)
                u.password_hash = hash_password(code); stat["passwords_reset"] += 1
    # nhân sự không còn trong danh sách chính thức → đánh dấu nghỉ (không xóa)
    codes = {str(r["ma"]) for r in rows}
    names = {name_key(r["ten"]) for r in rows}
    for e in emps:
        if e.code not in codes and name_key(e.full_name) not in names and e.active:
            e.active = False; stat["skipped"].append(f"{e.code} {e.full_name}: không có trong bảng lương → ngưng hoạt động")
    # và tài khoản của họ bị KHÓA – bảng lương là danh sách người đang làm việc, ai không có trong đó thì
    # không được đăng nhập nữa. Khóa chứ không xóa: nhật ký và chứng từ cũ vẫn phải truy ra được người thực hiện.
    if close_accounts:
        # Điều kiện giữ tài khoản là ĐANG GẮN với một hồ sơ trong bảng lương, không phải "trùng tên với ai đó
        # trong bảng lương". Dữ liệu nạp từ Vietrip có nhiều tài khoản trùng tên một người (tên thừa dấu cách
        # nên mỗi lần nạp lại đẻ thêm một bản: lethinh2..5, phamthithuyvy2..10); những bản dư ấy trùng tên với
        # người thật nên nếu xét theo tên thì chúng sống sót, mà mỗi bản là một lối đăng nhập vào dữ liệu khách.
        for u in users:
            if not u.active or u.role in GIU_TAI_KHOAN or u.id in dang_gan: continue
            u.active = False; stat["users_closed"].append(f"{u.username} ({u.full_name})")
    if dry_run:
        # Xem trước: hoàn tác mọi thay đổi, chỉ trả về danh sách sẽ làm gì. Khóa tài khoản là việc không
        # sửa lại được bằng một nút, nên phải nhìn thấy danh sách trước khi bấm.
        db.rollback(); stat["xem_truoc"] = True
        return stat
    if actor: R.audit(db, actor.username, actor.role, "nap_danh_sach_nhan_vien", "employees", after={k: (v if not isinstance(v, list) else len(v)) for k, v in stat.items()})
    db.commit()
    return stat


def staff_directory(db: Session) -> list[dict]:
    """Danh sách gọn cho form báo cáo / chọn người: mã, họ tên, phòng, nhóm, chức vụ."""
    out = []
    for e in db.execute(select(Employee).where(Employee.active == True).order_by(Employee.department, Employee.sales_group, Employee.code)).scalars():
        out.append({"code": e.code, "full_name": e.full_name, "department": e.department, "sales_group": e.sales_group, "title": e.title, "position": e.position, "office": e.office, "user_id": e.user_id})
    return out
