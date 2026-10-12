"""API nhân sự – lương: hồ sơ, visa, HDV & phân chuyến, đội xe & lệnh điều xe, sự vụ, bảng lương (robot R6)."""
import json
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services import chu_ky as _CK   # bang chu ky, Dot LG2 - nhap o DAU TEP vi require_roles doc no luc nap mo-dun
from app.api.deps import current_user, require_roles, cong_chan_quyen, loc_theo_nguoi_dung, toan_quyen_ke_ca_tach_bach
from app.models.core import ROLES, Tour, User, Company
from app.models.hdv import CHU_TIEN, LOAI_DE_XUAT, QUYET_DINH, TRANG_THAI as YC_TRANG_THAI, TRANG_THAI_BC, TRANG_THAI_DX, TRANG_THAI_UNG, BaoCaoSauTour, BuocDuyetHdv, CauHinhDuyetHdv, DeXuatHdv, TamUngHdv, YeuCauHdv
from app.models.hr import SALES_GROUPS, Employee, VisaFile, GuideAssignment, Vehicle, VehicleRate, DispatchOrder, Incident, PayrollRun, GuideRate, INCIDENT_LEVELS, INCIDENT_STATUS, DEPARTMENTS, POSITIONS, OFFICES
from app.models.chi_luong import (ChiKyLuong, KET_LUAN as CL_KET_LUAN,
                                  TRA_TRANG_THAI as CL_TRA_TRANG_THAI)
from app.services import hr as H
from app.services import rules as R
from app.services import nhan_lenh as _NL
from app.services.access import FULL_VIEW
from app.services import hdv as HDV
from app.services import pham_vi_phap_nhan as PV
from app.services import ghi_mot_lan as GML

router = APIRouter(prefix="/api/v1", tags=["nhan-su"])
HR_WRITE = ("hcns", "cntt")

# Bảng lương tách khỏi hồ sơ nhân sự (chỉ đạo 07/9/2026): theo VAI TRÒ chỉ còn HCNS, Chủ tịch, TGĐ và
# Ban Kiểm soát. Kế toán trưởng xem toàn công ty bằng NGOẠI LỆ THEO NGƯỜI, vì vai trò "ketoan" có nhiều
# người mà quyền chỉ cấp cho một. Không dùng require_roles được vì quyết định phụ thuộc dữ liệu.
@cong_chan_quyen
def bang_luong(u: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    from app.services import access as AC
    if "payroll" not in AC.hr_tabs_for(db, u):
        raise HTTPException(403, "Vai trò của bạn không được xem bảng lương toàn công ty")
    return u
HR_READ = ("hcns", "cntt", "ketoan", "tgd", "chutich", "bks", "tp_dh", "gd_kd", "tp_kd", "ptgd_doan")


def emp_out(e: Employee) -> dict:
    return {"id": e.id, "code": e.code, "user_id": e.user_id, "full_name": e.full_name, "department": e.department, "department_name": DEPARTMENTS.get(e.department, e.department),
            "position": e.position, "position_name": POSITIONS.get(e.position, e.position), "title": e.title, "duties": e.duties, "sales_group": e.sales_group, "office": e.office, "office_name": OFFICES.get(e.office, e.office),
            "contract_type": e.contract_type, "base_salary": e.base_salary, "start_date": e.start_date, "probation": e.probation, "transition_list": e.transition_list,
            "card_no": e.card_no, "card_type": e.card_type, "card_expiry": e.card_expiry, "member_org": e.member_org, "ctv_contract": e.ctv_contract,
            "advance_limit": e.advance_limit, "active": e.active, "company_id": e.company_id, "birth_date": e.birth_date, "phone": e.phone,
            "bhxh_base": e.bhxh_base, "member_org": e.member_org,
            # NỬA CÒN LẠI CỦA PHÉP KIỂM LỆCH PHIÊN BẢN — trả nợ 12/10/2026.
            # `update_employee` gọi `kiem_phien_ban` từ đợt VPM-8, nhưng phép ấy CHỈ chạy khi màn
            # hình GỬI phiên bản lên, và màn hình chỉ gửi được khi cửa đọc TRẢ RA. Thiếu đúng một
            # khoá này nên hàng rào chống hai người sửa đè nhau chưa chạy ngày nào kể từ VPM-8:
            # hai người mở cùng một hồ sơ, người lưu sau ghi đè người lưu trước, không ai biết.
            # Vòng TK-1 (12/10) đã dựng đầu màn hình nhưng KHÔNG thêm được khoá này vì tệp đang
            # bị làn Phân quyền giữ; ghi nợ rồi trả ở đây khi dòng ấy đóng.
            "phien_ban": e.phien_ban,
            "guide_ok": H.guide_eligible(e, date.today())[0] if e.department == "huong_dan" else None}


@router.get("/hr/meta")
def hr_meta(u: User = Depends(current_user)):
    return {"departments": DEPARTMENTS, "positions": POSITIONS, "offices": OFFICES}


# ---------- Hồ sơ nhân sự ----------
@router.get("/employees")
def employees(department: str | None = None, u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    q = select(Employee).order_by(Employee.department, Employee.code)
    if department: q = q.where(Employee.department == department)
    return [emp_out(e) for e in db.execute(q).scalars()]


class EmployeeIn(BaseModel):
    # Đợt C – chỉ dùng khi lần sửa này là một lần ĐIỀU CHUYỂN (đổi phòng / chức vụ /
    # văn phòng / pháp nhân). Rỗng thì lấy ngày hôm nay, và màn hình phải nói rõ điều đó:
    # một điều chuyển có hiệu lực lùi mà ghi ngày hôm nay là ghi sai lịch sử.
    dieu_chuyen_tu_ngay: date | None = None
    dieu_chuyen_ly_do: str = ""
    """Sửa hồ sơ chỉ ghi đè những trường được gửi lên (exclude_unset), nên màn hình cũ gửi thiếu
    trường mới sẽ không xóa mất dữ liệu đã nạp (ngày sinh, điện thoại, pháp nhân, chức danh)."""
    phien_ban: int | None = None      # VPM-8 – bản màn hình đang cầm
    full_name: str
    department: str
    position: str = "nv"
    office: str = "hcm"
    contract_type: str = "hdld"
    base_salary: float | None = None
    user_id: int | None = None
    start_date: date | None = None
    probation: bool = False
    card_no: str = ""
    card_type: str = ""
    card_expiry: date | None = None
    member_org: bool = False
    ctv_contract: bool = False
    advance_limit: float | None = None
    title: str | None = None
    duties: str | None = None
    sales_group: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    company_id: int | None = None
    active: bool | None = None


@router.get("/staff")
def staff_directory(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Danh bạ nhân viên (mã NV, họ tên, phòng, nhóm) – mọi người đăng nhập đều xem được để chọn người/ghi báo cáo."""
    from app.services import staff as STF
    return {"rows": STF.staff_directory(db), "departments": DEPARTMENTS, "groups": SALES_GROUPS}


@router.post("/employees/import-master")
def import_master(reset_passwords: bool = False, close_accounts: bool = True, dry_run: bool = False,
                  u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """Nạp danh sách nhân viên chính thức từ bảng lương HCNS (app/data/nhan_su_*.json): mã NV, phòng, nhóm, chức vụ; ghép/tạo tài khoản.
    reset_passwords=true: đặt lại mật khẩu mọi tài khoản trong danh sách = mã NV (trừ Chủ tịch/TGĐ/CNTT) – dùng khi cấp tài khoản lần đầu."""
    from app.services import staff as STF
    st = STF.import_master(db, u, reset_passwords=reset_passwords, close_accounts=close_accounts, dry_run=dry_run)
    return {"message": f"Đã nạp: cập nhật {st['updated']}, tạo mới {st['created']} hồ sơ; ghép {st['users_linked']} tài khoản, tạo {st['users_created']} tài khoản mới" + (f", đặt lại {st['passwords_reset']} mật khẩu = mã NV" if reset_passwords else ""), **st}


class TaiKhoanIn(BaseModel):
    active: bool | None = None
    role: str | None = None


@router.get("/users/khoa")
def users_locked(u: User = Depends(require_roles(*HR_WRITE, "tgd", "chutich", "bks")), db: Session = Depends(get_db)):
    """Tài khoản đang bị khóa. GET /users chỉ trả tài khoản đang hoạt động nên khóa xong là không còn nhìn
    thấy ở đâu – không mở lại được người bị khóa nhầm, cũng không rà được ai đã bị khóa."""
    from app.models.core import ROLES as R_
    rows = db.execute(select(User).where(User.active == False).order_by(User.username)).scalars()
    return [{"id": x.id, "username": x.username, "full_name": x.full_name, "role": x.role,
             "role_name": R_.get(x.role, x.role), "staff_code": x.staff_code, "department": x.department} for x in rows]


@router.put("/users/{uid}")
def update_user(uid: int, data: TaiKhoanIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """Khóa / mở khóa tài khoản và đổi vai trò. Khóa chứ không xóa: nhật ký và chứng từ cũ vẫn phải truy ra
    được người thực hiện."""
    from app.models.core import ROLES as R_
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if t.id == u.id: raise HTTPException(422, "Không tự đổi vai trò hoặc tự khóa tài khoản của mình")
    if t.role in ("chutich", "tgd") and u.role != "cntt" and not toan_quyen_ke_ca_tach_bach(u, db): raise HTTPException(403, "Chỉ CNTT thao tác trên tài khoản lãnh đạo")
    if data.role is not None and data.role not in R_: raise HTTPException(422, f"Vai trò không hợp lệ: {data.role}")
    before = {"vai_tro": t.role, "hoat_dong": t.active}
    if data.role is not None and data.role != t.role:
        t.role, t.role_changed_at, t.role_changed_by = data.role, datetime.now(), u.username
    if data.active is not None: t.active = data.active
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"vai_tro": t.role, "hoat_dong": t.active})
    db.commit()
    return {"message": f"Đã cập nhật tài khoản {t.username}" + ("" if t.active else " – đã khóa đăng nhập"),
            "user": {"id": t.id, "username": t.username, "role": t.role, "role_name": R_.get(t.role, t.role), "active": t.active}}


class ResetPwIn(BaseModel):
    new_password: str = ""      # trống = mã NV


@router.post("/users/{uid}/reset-password")
def reset_password(uid: int, data: ResetPwIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    """HCNS/CNTT đặt lại mật khẩu cho một tài khoản (mặc định = mã NV)."""
    from app.core.security import hash_password
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if t.role in ("chutich", "tgd") and u.role != "cntt" and not toan_quyen_ke_ca_tach_bach(u, db): raise HTTPException(403, "Chỉ CNTT đặt lại mật khẩu lãnh đạo")
    pw = data.new_password.strip() or t.staff_code
    if not pw or len(pw) < 3: raise HTTPException(422, "Chưa có mã NV – nhập mật khẩu mới")
    t.password_hash = hash_password(pw)
    t.must_change_password = True      # mật khẩu do người khác đặt là mật khẩu TẠM, phải đổi ở lần đăng nhập đầu
    R.audit(db, u.username, u.role, "dat_lai_mat_khau", f"user:{t.username}", after={"buoc_doi": True}); db.commit()
    return {"message": f"Đã đặt lại mật khẩu cho {t.full_name} ({t.username})" + (" = mã NV" if not data.new_password.strip() else "")
                       + " – người dùng phải đổi mật khẩu ở lần đăng nhập kế tiếp"}


@router.post("/employees", status_code=201)
def create_employee(data: EmployeeIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    if data.department not in DEPARTMENTS or data.position not in POSITIONS: raise HTTPException(422, "Phòng/chức danh không hợp lệ")
    tao = {k: v for k, v in data.model_dump(exclude_none=True).items()
           if k not in ("dieu_chuyen_tu_ngay", "dieu_chuyen_ly_do")}
    e = Employee(code=H.next_code(db, Employee, "NS"), **tao)
    db.add(e); db.flush()
    R.audit(db, u.username, u.role, "tao_ho_so_nhan_su", f"emp:{e.code}", after={"ten": e.full_name, "phong": e.department, "luong": e.base_salary})
    db.commit(); db.refresh(e)
    return {"employee": emp_out(e), "message": f"Đã tạo hồ sơ {e.code}"}


@router.put("/employees/{eid}")
def update_employee(eid: int, data: EmployeeIn, u: User = Depends(require_roles(*HR_WRITE)), db: Session = Depends(get_db)):
    e = db.get(Employee, eid)
    if not e: raise HTTPException(404, "Không có hồ sơ")
    fields = data.model_dump(exclude_unset=True)
    from app.services import to_chuc_lich_su as LS
    dc_tu = fields.pop("dieu_chuyen_tu_ngay", None)
    dc_ly_do = fields.pop("dieu_chuyen_ly_do", "")
    truoc_to_chuc = LS.anh_chup(e)
    if fields.get("active") is False and e.active:
        xe = db.execute(select(Vehicle).where(Vehicle.driver_id == e.id, Vehicle.active == True)).scalars().all()
        if xe: raise HTTPException(422, f"{e.full_name} đang là tài xế của xe {', '.join(v.plate for v in xe)} – giao xe cho người khác trước khi ngưng hồ sơ")
    before = {"luong": e.base_salary, "chuc_vu": e.position, "phong": e.department, "dang_lam": e.active}
    GML.kiem_phien_ban(e, fields.pop("phien_ban", None), f"Hồ sơ nhân sự {e.code}",
                       lambda: {**before, "phien_ban": e.phien_ban})
    for k, v in fields.items(): setattr(e, k, v)
    GML.tang_phien_ban(e)
    # Điều chuyển ghi Ở ĐÂY, không ở một cửa riêng: đổi phòng đã có một cửa là màn hình này, và
    # cửa thứ hai nghĩa là có một đường đổi phòng không ghi lịch sử. `truoc_to_chuc` chụp trước khi
    # gán nên chặng cũ mang giá trị CŨ – thiếu nó thì lịch sử ghi rằng người này vốn đã ở phòng mới
    # từ ngày vào làm, và sai kiểu ấy không bao giờ tự lộ.
    dieu_chuyen = LS.can_dieu_chuyen(e, truoc_to_chuc)
    if dieu_chuyen:
        try:
            LS.ghi_dieu_chuyen(db, e, truoc_to_chuc, dc_tu, dc_ly_do, u.username)
        except ValueError as ex:
            db.rollback()
            raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "sua_ho_so_nhan_su", f"emp:{e.code}", before=before,
            after={"luong": e.base_salary, "chuc_vu": e.position, "phong": e.department, "dang_lam": e.active})
    db.commit()
    ngung = " – hồ sơ đã chuyển sang Ngưng làm việc" if e.active is False else ""
    dc = (f" – đã ghi một chặng lịch sử tổ chức từ {dc_tu or date.today():%d/%m/%Y}" if dieu_chuyen else "")
    return {"employee": emp_out(e), "message": "Đã cập nhật (tăng lương/điều chỉnh nhân sự cần Chủ tịch duyệt theo Điều 9 – ghi nhật ký)" + ngung + dc}


@router.get("/employees/{eid}/lich-su-to-chuc")
def lich_su_to_chuc(eid: int, u: User = Depends(require_roles(*HR_WRITE, "tgd", "chutich", "bks")),
                    db: Session = Depends(get_db)):
    """Các chặng tổ chức của một người, theo thứ tự thời gian.

    Dòng có `suy_ra = true` là chặng hệ thống DỰNG LẠI từ hồ sơ đang có tại lần điều chuyển đầu
    tiên, không phải bản ghi lập lúc ấy. Màn hình phải nói ra điều đó: trộn một phỏng đoán hợp lý
    vào cùng hàng với bản ghi thật là biến nó thành chứng cứ, mà chứng cứ thì có người sẽ dựa vào
    để trả lời kiểm toán.
    """
    from app.services import to_chuc_lich_su as LS
    e = db.get(Employee, eid)
    if not e:
        raise HTTPException(404, "Không có hồ sơ")
    return {"ma_nv": e.code, "ten": e.full_name,
            "hien_tai": {"phong": e.department, "chuc_vu": e.position, "van_phong": e.office},
            "chang": [LS.ra(c) for c in LS.lich_su(db, e.code)],
            "ghi_chu": "Lịch sử bắt đầu được ghi từ 07/10/2026. Người chưa điều chuyển lần nào kể "
                       "từ đó thì chưa có chặng nào – đó là chưa có dữ liệu, không phải thiếu hồ sơ."}


@cong_chan_quyen
def cong_xem_tong_quan_hcns(u: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    """Cổng xem Tổng quan HCNS. ĐẶT Ở CHỮ KÝ để máy đọc được, không viết trong thân endpoint.

    LUẬT KHÔNG ĐỔI MỘT CHỮ so với lúc nó nằm trong thân `hcns_tong_quan` – chỉ dời ra chữ ký và
    đặt tên. Cùng một ca với `cong_xem_chi_luong` ngày 08/10/2026, và cùng một lý do:

    Hàng rào P1 đòi MÁY nhận ra quyền mà không phải phân tích mã nguồn. Chặn viết trong thân một
    hàm endpoint thì máy chỉ thấy được bằng cách đọc mã, và cửa này làm P1 cùng ba phép thử P1b
    đỏ trên `main` sáng 08/10/2026 – kéo theo mọi làn đang mở, vì main đỏ thì không gì gộp được.

    KHÔNG đổi thành `require_roles(...)`: luật ở đây là "mở được thẻ tong_quan", mà tập thẻ ấy do
    `access` tính theo TỪNG NGƯỜI trong cơ sở dữ liệu, không phải một danh sách vai cố định. Ép
    thành danh sách vai vừa chặn nhầm người đang có ngoại lệ, vừa mở cho người cùng vai mà không
    có ngoại lệ – tức là sửa hàng rào cho hợp phép thử, đúng cái phép thử sinh ra để chặn.
    """
    from app.services import access as AC
    if "tong_quan" not in AC.hr_tabs_for(db, u):
        raise HTTPException(403, "Vai trò của bạn không mở được Tổng quan HCNS")
    return u


@router.get("/hr/tong-quan")
def hcns_tong_quan(u: User = Depends(cong_xem_tong_quan_hcns), db: Session = Depends(get_db)):
    """HC01 – Tổng quan HCNS. Chỉ đọc, và không sinh con số nào của riêng nó.

    Đặt dưới tiền tố `/api/v1/hr` vì tiền tố ấy ĐÃ được khai cho màn hình `/hr` trong bảng
    `MAN_HINH_API`. Mở một tiền tố mới `/api/v1/hcns` là khai thêm một mảnh quyền, mà khai quyền
    thuộc làn Phân quyền chứ không thuộc lần viết này.

    Khối Bảng lương chỉ gắn vào khi người gọi thật sự mở được thẻ ấy. Thẻ Tổng quan mở rộng hơn
    thẻ Bảng lương, nên in thẳng tổng thực nhận ở đây là mở Bảng lương bằng cửa sau. Phép xét ấy
    nay nằm trong `TQ.tong_quan_cho` chứ không viết lại ở đây – thân một endpoint không còn chỗ
    nào nói về quyền nữa, đó là điều kiện để P1 đọc được cửa này.
    """
    from app.services import hcns_tong_quan as TQ
    return TQ.tong_quan_cho(db, u)


# ---------- Hồ sơ visa ----------
@router.get("/visa")
def visa_list(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    return [{"id": f.id, "code": f.code, "customer_name": f.customer_name, "market": f.market, "method": f.method, "handler_id": f.handler_id, "handler": emps.get(f.handler_id, ""),
             "office": f.office, "alliance": f.alliance, "tour_id": f.tour_id, "revenue": f.revenue, "status": f.status, "completed_at": f.completed_at}
            for f in db.execute(select(VisaFile).order_by(desc(VisaFile.id))).scalars()]


class VisaIn(BaseModel):
    customer_name: str
    market: str
    method: str = "tu_xu_ly"
    handler_id: int
    office: str = "hcm"
    alliance: bool = False
    tour_id: int | None = None
    revenue: float | None = None


@router.post("/visa", status_code=201)
def visa_create(data: VisaIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt")), db: Session = Depends(get_db)):
    if data.method not in ("tu_xu_ly", "gui_doi_tac"): raise HTTPException(422, "Cách xử lý: tu_xu_ly / gui_doi_tac")
    f = VisaFile(code=H.next_code(db, VisaFile, "VS"), **data.model_dump())
    db.add(f); db.flush()
    R.audit(db, u.username, u.role, "tao_ho_so_visa", f"visa:{f.code}", after=data.model_dump(mode="json"))
    db.commit()
    return {"message": f"Đã tạo hồ sơ {f.code}"}


@router.post("/visa/{vid}/complete")
def visa_complete(vid: int, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt")), db: Session = Depends(get_db)):
    f = db.get(VisaFile, vid)
    if not f: raise HTTPException(404, "Không có hồ sơ")
    if f.status == "hoan_thanh": raise HTTPException(422, "Hồ sơ đã hoàn thành")
    f.status, f.completed_at = "hoan_thanh", date.today()
    R.audit(db, u.username, u.role, "hoan_thanh_visa", f"visa:{f.code}", after={"thang": f"{f.completed_at:%Y-%m}", "cach": f.method})
    db.commit()
    return {"message": f"{f.code} hoàn thành – tính quỹ visa tháng {f.completed_at:%m/%Y}"}


# ---------- Xe Vietrip & HDV: màn hình của chính người ở hiện trường ----------
@router.get("/xe-hdv/cua-toi")
def xe_hdv_cua_toi(u: User = Depends(require_roles("tai_xe", "hdv", "nv_dh", "tp_dh", "hcns", "cntt", "tgd", "chutich", "ketoan", "bks", "ptgd_doan", "ptgd_mkt")),
                   db: Session = Depends(get_db)):
    """Tài xế thấy xe mình đứng tên và lệnh điều xe của mình; HDV thấy phân chuyến và hạn thẻ của mình.

    Chỉ trả về việc của CHÍNH người đăng nhập – không phải bản rút gọn của màn hình Điều hành. Người ở hiện
    trường không có lý do gì phải nhìn thấy hàng đợi của cả đội, và cũng không được thấy giá xe nội bộ.
    """
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e is None and u.staff_code:
        e = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()
    if e is None:
        raise HTTPException(404, "Tài khoản này chưa gắn với hồ sơ nhân sự – báo HCNS ghép mã nhân viên")

    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    ho_so = {"code": e.code, "full_name": e.full_name, "department": e.department,
             "department_name": DEPARTMENTS.get(e.department, e.department),
             "position_name": POSITIONS.get(e.position, e.position), "phone": e.phone, "birth_date": e.birth_date}

    xe = [{"id": v.id, "plate": v.plate, "seats": v.seats, "active": v.active,
           "company": (cos[v.company_id].name if v.company_id in cos else ""),
           "kind": "Xe nội bộ" if v.kind != "hop_tac" else "Xe hợp tác"}
          for v in db.execute(select(Vehicle).where(Vehicle.driver_id == e.id)).scalars()]

    lenh = []
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.driver_id == e.id).order_by(desc(DispatchOrder.id)).limit(50)).scalars():
        t = db.get(Tour, d.tour_id); v = db.get(Vehicle, d.vehicle_id)
        lenh.append({"id": d.id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
                     "vehicle": v.plate if v else "", "date_from": d.date_from, "date_to": d.date_to,
                     "days": (d.date_to - d.date_from).days + 1, "status": d.status,
                     "confirmed_at": d.confirmed_at, "incident_note": d.incident_note,
                     # DL-1b: mắt thứ ba. `trang_thai_nhan` tính TẠI CHỖ (xem nhan_lenh.py) nên "quá hạn"
                     # luôn đúng với đồng hồ lúc mở màn hình, không cần ai chạy nền cập nhật.
                     "trang_thai_nhan": _NL.trang_thai_nhan(d),
                     "han_nhan": (_NL.han_nhan(d).isoformat() if _NL.han_nhan(d) else None),
                     "nhan_luc": d.nhan_luc, "nhan_boi": d.nhan_boi,
                     "tu_choi_nhan_ly_do": d.tu_choi_nhan_ly_do,
                     "con_cho_nhan": d.status not in _NL.KHONG_CHO_NHAN})

    chuyen = []
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.guide_id == e.id).order_by(desc(GuideAssignment.id)).limit(50)).scalars():
        t = db.get(Tour, a.tour_id)
        chuyen.append({"id": a.id, "tour_code": t.code if t else "", "tour_name": t.name if t else "",
                       "start_date": t.start_date if t else None, "days": a.days, "holiday": a.holiday,
                       "amount": (a.rate_per_day or 0) * a.days * (2 if a.holiday else 1), "status": a.status,
                       "confirmed_at": a.confirmed_at, "report_submitted": a.report_submitted,
                       "advance_settled": a.advance_settled, "ly_do": a.ly_do,
                       "han_tra_loi": a.han_tra_loi,
                       "con_tra_loi_duoc": (a.status == "cho_xac_nhan"
                                            and (a.han_tra_loi is None or datetime.now() <= a.han_tra_loi)),
                       # Đợt 2 · báo cáo sau tour. Gửi kèm NGAY Ở ĐÂY thay vì bắt màn hình gọi thêm một
                       # cửa cho từng chuyến: hướng dẫn viên mở máy ngoài hiện trường, mỗi lần gọi thêm
                       # là một lần chờ sóng.
                       "bao_cao": _bc_tom_tat(db, a)})

    the = None
    if e.department == "huong_dan":
        ok, vi_sao = H.guide_eligible(e, date.today())
        the = {"card_no": e.card_no, "card_expiry": e.card_expiry, "du_dieu_kien": ok, "vi_sao": vi_sao}

    # Đợt 3 · số dư tạm ứng CỦA CHÍNH MÌNH, tách theo túi. Người ở hiện trường cần biết mình đang
    # giữ bao nhiêu tiền công ty trước khi xin thêm — và phải thấy đúng từng túi, vì tiền thu hộ
    # khách không bù trừ sang túi công ty.
    tui = HDV.so_du_ung(db, e.id) if e.department == "huong_dan" else []
    return {"ho_so": ho_so, "xe": xe, "lenh_dieu_xe": lenh, "phan_chuyen": chuyen, "the_hdv": the,
            "tui_ung": tui}


def _bc_tom_tat(db: Session, a: GuideAssignment) -> dict | None:
    """Tóm tắt báo cáo sau tour của một phân công, cho màn hình hiện trường.

    Trả None khi CHƯA CÓ BẢN NÀO — và màn hình phải phân biệt None với "có bản chưa xong": một bên là
    chưa ai viết gì, một bên là viết rồi đang chờ. Hai cái gọi hai hành động khác nhau.
    """
    b = HDV.ban_dang_xet(db, a.id)
    if b is None:
        return None
    return {"id": b.id, "ban_so": b.ban_so, "trang_thai": b.trang_thai, "phien_ban": b.phien_ban,
            "han_nop": b.han_nop, "tre_han": b.tre_han(), "da_khoa": b.da_khoa(),
            "y_kien_kiem": b.y_kien_kiem}


class TraLoiIn(BaseModel):
    ly_do: str = ""


def _loi_chao_cua_toi(db: Session, u: User, aid: int) -> GuideAssignment:
    """Lấy lời chào và kiểm tra nó là của CHÍNH người đang đăng nhập.

    Không kiểm chỗ này thì một hướng dẫn viên nhận thay chuyến của người khác chỉ bằng cách đổi số trên
    đường dẫn – và người bị nhận thay là người phải đi dẫn."""
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e is None and u.staff_code:
        e = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()
    if e is None:
        raise HTTPException(404, "Tài khoản này chưa gắn với hồ sơ nhân sự – báo HCNS ghép mã nhân viên")
    a = db.get(GuideAssignment, aid)
    if a is None or a.guide_id != e.id:
        raise HTTPException(404, "Không có lời chào này")
    return a


@router.post("/xe-hdv/chao-chuyen/{aid}/nhan")
def nhan_chuyen(aid: int, u: User = Depends(require_roles("hdv")), db: Session = Depends(get_db)):
    """Hướng dẫn viên nhận chuyến được chào."""
    a = _loi_chao_cua_toi(db, u, aid)
    if a.status != "cho_xac_nhan":
        raise HTTPException(422, f"Lời chào không còn chờ trả lời (đang ở '{a.status}')")
    if a.han_tra_loi is not None and datetime.now() > a.han_tra_loi:
        raise HTTPException(422, "Lời chào đã hết hiệu lực – liên hệ phòng Hướng dẫn để được chào lại. "
                                 "Không phải lỗi của anh/chị, chỉ là chuyến cần chốt người sớm.")
    a.status = "da_xac_nhan"; a.confirmed_at = datetime.now(); a.tra_loi_luc = a.confirmed_at
    R.audit(db, u.username, u.role, "nhan_chuyen", f"assign:{a.id}"); db.commit()
    return {"message": "Đã nhận chuyến."}


@router.post("/xe-hdv/chao-chuyen/{aid}/tu-choi")
def tu_choi_chuyen(aid: int, data: TraLoiIn, u: User = Depends(require_roles("hdv")),
                   db: Session = Depends(get_db)):
    """Hướng dẫn viên từ chối lời chào.

    KHÔNG kèm chế tài và không ghi vào hồ sơ đánh giá. Hướng dẫn viên là cộng tác viên: từ chối một
    lời chào là quyền của người cung cấp dịch vụ. Một hệ thống phạt việc từ chối là một hệ thống ghi
    lại bằng chứng rằng công ty giao việc chứ không phải đặt dịch vụ."""
    a = _loi_chao_cua_toi(db, u, aid)
    if a.status != "cho_xac_nhan":
        raise HTTPException(422, f"Lời chào không còn chờ trả lời (đang ở '{a.status}')")
    a.status = "tu_choi"; a.ly_do = (data.ly_do or "")[:200]; a.tra_loi_luc = datetime.now()
    R.audit(db, u.username, u.role, "tu_choi_chuyen", f"assign:{a.id}", after={"ly_do": a.ly_do})
    db.commit()
    return {"message": "Đã ghi nhận từ chối. Chuyến sẽ được chào cho người khác – không có ghi chú bất "
                       "lợi nào cho anh/chị."}


# AI ĐẶT HÀNG, AI CHỌN NGƯỜI — Chủ tịch chốt 06/10/2026, và đây là hai việc khác nhau:
#
#   · YC_LAP    – ĐẶT HÀNG. Điều hành biết chuyến cần mấy người, đi từ giờ nào, cần ngoại ngữ gì.
#                 Họ gửi yêu cầu. Họ KHÔNG chọn ai đi.
#   · DIEU_DONG – CHỌN NGƯỜI. "Việc quyết định điều động HDV là do TP HD làm" – Chủ tịch 06/10/2026.
#                 Trưởng phòng Hướng dẫn biết ai rảnh, ai hợp tuyến, ai vừa đi về mệt. Điều hành
#                 không có thông tin ấy, và nếu Điều hành xếp thẳng được người thì phòng HDV mất
#                 quyền điều phối chính nhân sự của mình.
#
# GIỜ CỦA PHÂN CÔNG CŨNG THUỘC DIEU_DONG. Điều hành ghi giờ cần người ở YÊU CẦU; phòng HDV chốt giờ
# của từng người. Hai mốc ấy thường bằng nhau — cửa lập phân công tự chép sang — nhưng khi lệch thì
# người chịu trách nhiệm xếp lịch là người được sửa.
YC_LAP = ("nv_dh", "tp_dh", "tp_hd", "hcns", "cntt")
DIEU_DONG = ("tp_hd", "hcns", "cntt")


# ---------- HDV & phân chuyến (cổng 13) ----------
@router.get("/guide-assignments")
def assignments(u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    out = []
    for a in db.execute(select(GuideAssignment).order_by(desc(GuideAssignment.id))).scalars():
        t = db.get(Tour, a.tour_id)
        out.append({"id": a.id, "tour_id": a.tour_id, "tour_code": t.code if t else "", "tour_name": t.name if t else "", "guide_id": a.guide_id, "guide": emps.get(a.guide_id, ""),
                    # Đơn giá gửi RA MÀN HÌNH để nguyên, kể cả rỗng: "chưa nhập đơn giá" phải hiện là ô
                    # trống, không phải số 0. Chỉ phép TÍNH mới xử rỗng thành 0.
                    "days": a.days, "rate_per_day": a.rate_per_day, "holiday": a.holiday,
                    "amount": (a.rate_per_day or 0) * a.days * (2 if a.holiday else 1),
                    "assigned_by": a.assigned_by, "assigned_at": a.assigned_at, "confirmed_at": a.confirmed_at, "report_submitted": a.report_submitted,
                    "advance_settled": a.advance_settled, "status": a.status})
    return out


class AssignIn(BaseModel):
    rate_id: int | None = None
    tour_id: int
    guide_id: int
    days: int
    rate_per_day: float | None = None
    holiday: bool = False
    # Phòng HDV Đợt 1 · 06/10/2026.
    #
    # Giờ ở đây CÒN ĐỂ TRỐNG ĐƯỢC, và đó là một món nợ có chủ ý, không phải một chỗ quên. Cấm chồng
    # giờ chỉ áp được khi có giờ; nhưng bắt buộc ngay hôm nay thì mọi màn hình đang gọi cửa này sẽ
    # hỏng trong một lần nâng cấp — cùng lý do mà `kiem_phien_ban` cho qua khi người gọi chưa gửi
    # phiên bản. Chỗ siết lại là ĐÂY, khi màn hình đã gửi giờ; ghi ra để người sau biết còn nợ.
    #
    # Khi CÓ giờ thì chặn thật: trùng là từ chối, không phải cảnh báo rồi vẫn ghi.
    bat_dau: datetime | None = None
    ket_thuc: datetime | None = None
    vai_tro: str = "chinh"
    yeu_cau_id: int | None = None


@router.post("/guide-assignments", status_code=201)
def assign(data: AssignIn, u: User = Depends(require_roles(*DIEU_DONG)), db: Session = Depends(get_db)):
    e = db.get(Employee, data.guide_id); t = db.get(Tour, data.tour_id)
    if not e or not t: raise HTTPException(404, "Không có HDV hoặc tour")
    ok, why = H.guide_eligible(e, t.start_date)
    if not ok: raise HTTPException(422, {"gate": "CONG_13", "message": f"Không phân chuyến: {why}"})
    a = GuideAssignment(**data.model_dump(), assigned_by=u.username)
    if data.rate_id:
        gr = db.get(GuideRate, data.rate_id)
        if not gr or gr.status != "active": raise HTTPException(422, "Tuyến không có trong bảng giá HDV hiệu lực")
        a.rate_per_day = gr.rate_per_day
        if not data.days or data.days <= 0: a.days = max(1, int(round(gr.days)))
    if (a.rate_per_day or 0) <= 0: raise HTTPException(422, "Chọn tuyến trong bảng giá HDV hoặc nhập đơn giá/ngày")
    if data.bat_dau and data.ket_thuc and data.ket_thuc <= data.bat_dau:
        raise HTTPException(422, "Giờ kết thúc phải sau giờ bắt đầu")
    yc = db.get(YeuCauHdv, data.yeu_cau_id) if data.yeu_cau_id else None
    if data.yeu_cau_id and not yc:
        raise HTTPException(404, "Không có yêu cầu HDV")
    # Giờ chưa gõ thì LẤY THEO YÊU CẦU, nếu yêu cầu đã có giờ. Đây không phải suy đoán: Điều hành đã
    # ghi khoảng cần người ở đúng chỗ ấy, và người được xếp vào đúng yêu cầu đó thì đi đúng khoảng đó.
    if yc and not a.bat_dau and not a.ket_thuc and not yc.thieu_gio():
        a.bat_dau, a.ket_thuc = yc.bat_dau, yc.ket_thuc
    # Khoá TRƯỚC khi ghi, kiểm lại SAU khi ghi – xem app/services/hdv.py, mục "chặn thật".
    if not HDV.khong_so_duoc(a.bat_dau, a.ket_thuc):
        HDV.khoa_hdv(db, a.guide_id)
    db.add(a); db.flush()
    if not HDV.khong_so_duoc(a.bat_dau, a.ket_thuc):
        HDV.canh_trung_sau_khi_ghi(db, a)
    if yc:
        HDV.cap_nhat_trang_thai(db, yc)
    R.audit(db, u.username, u.role, "phan_cong_hdv", f"tour:{t.code}", after={"hdv": e.full_name, "ngay": data.days, "don_gia": data.rate_per_day, "bat_dau": str(a.bat_dau or ""), "ket_thuc": str(a.ket_thuc or "")})
    db.commit()
    return {"message": f"Đã lập văn bản phân công {e.full_name} dẫn {t.code} – HDV xác nhận trong 24 giờ"}


class AssignUpdate(BaseModel):
    confirm: bool | None = None
    report_submitted: bool | None = None
    advance_settled: bool | None = None


@router.post("/guide-assignments/{aid}/update")
def assign_update(aid: int, data: AssignUpdate, u: User = Depends(require_roles("nv_dh", "tp_dh", "hcns", "cntt", "ketoan")), db: Session = Depends(get_db)):
    a = db.get(GuideAssignment, aid)
    if not a: raise HTTPException(404, "Không có phân công")
    if data.confirm: a.status, a.confirmed_at = "da_xac_nhan", datetime.now()
    if data.report_submitted is not None: a.report_submitted = data.report_submitted
    if data.advance_settled is not None: a.advance_settled = data.advance_settled
    R.audit(db, u.username, u.role, "cap_nhat_phan_cong_hdv", f"assign:{a.id}", after=data.model_dump(exclude_none=True, mode="json"))
    db.commit()
    return {"message": "Đã cập nhật"}


# ---------- Phòng HDV Đợt 1: yêu cầu HDV và giờ phân công (06/10/2026) ----------
# Ba cửa, đúng ba việc của Đợt 1:
#   · POST /guide-assignments/yeu-cau      – Điều hành ĐẶT HÀNG phòng HDV. Trước đây không có chỗ nào chứa một
#                                 chuyến CHƯA xếp được người, nên không đếm được phần còn thiếu.
#   · POST /guide-assignments/{id}/gio – gõ hoặc sửa hai mốc giờ cho phân công CŨ. Hàng trăm bản ghi
#                                 cũ không có giờ; không có cửa sửa thì chúng kẹt mãi ở ô "chưa kiểm
#                                 được trùng", và cái cấm Chủ tịch chốt 06/10 chỉ áp cho dữ liệu mới.
#   · GET  /guide-assignments/yeu-cau/thieu – DANH SÁCH VIỆC. Một con số thiếu mà không ai nhìn thấy thì không
#                                 ai đi nhập.
#
# Vai trò: KHÔNG nghĩ ra vai trò mới. Cửa lập yêu cầu dùng đúng danh sách đang được phép lập phân
# công (`nv_dh`, `tp_dh`, `tp_hd`, `hcns`, `cntt`) — vì người đặt hàng và người xếp người là cùng hai
# phòng ấy. Cửa đọc dùng đúng danh sách đang đọc được phân công.


def yc_out(db: Session, y: YeuCauHdv) -> dict:
    t = db.get(Tour, y.tour_id)
    return {"id": y.id, "phien_ban": y.phien_ban, "tour_id": y.tour_id,
            "tour_code": t.code if t else "", "tour_name": t.name if t else "",
            "so_hdv": y.so_hdv, "con_thieu": HDV.con_thieu(db, y),
            "bat_dau": y.bat_dau, "ket_thuc": y.ket_thuc, "thieu_gio": y.thieu_gio(),
            "ngoai_ngu": y.ngoai_ngu, "nang_luc": y.nang_luc, "diem_hen": y.diem_hen,
            "han_phan_hoi": y.han_phan_hoi, "ghi_chu": y.ghi_chu,
            "trang_thai": y.trang_thai, "trang_thai_ten": YC_TRANG_THAI.get(y.trang_thai, y.trang_thai),
            "nguoi_lap": y.nguoi_lap, "lap_luc": y.lap_luc}


class YeuCauIn(BaseModel):
    tour_id: int
    so_hdv: int = 1
    # Giờ ĐỂ TRỐNG ĐƯỢC ở cửa yêu cầu: lúc Điều hành gửi yêu cầu thì giờ đón nhiều khi chưa chốt với
    # khách. Cửa PHÂN CÔNG mới là chỗ bắt buộc có giờ, vì đó là lúc phải chặn trùng.
    bat_dau: datetime | None = None
    ket_thuc: datetime | None = None
    ngoai_ngu: str = ""
    nang_luc: str = ""
    diem_hen: str = ""
    han_phan_hoi: datetime | None = None
    ghi_chu: str = ""


@router.get("/guide-assignments/yeu-cau")
def yeu_cau_ds(u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd")), db: Session = Depends(get_db)):
    # P6 – hàng rào phạm vi pháp nhân, khai ở PHAI_LOC. Khai mà không nối thì hàng rào chưa bật, và
    # tệ hơn là người đọc mã tin rằng chỗ này đã được canh.
    q = PV.loc(select(YeuCauHdv).order_by(desc(YeuCauHdv.id)), YeuCauHdv, u)
    return [yc_out(db, y) for y in db.execute(q).scalars().all()]


@router.get("/guide-assignments/yeu-cau/thieu")
def yeu_cau_con_thieu(u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd")), db: Session = Depends(get_db)):
    """Hai rổ, KHÔNG gộp làm một con số: "còn thiếu người" và "chưa đủ giờ để kiểm trùng" là hai việc
    khác nhau, giao cho hai người khác nhau. Gộp lại thì không ai biết phải làm gì."""
    thieu_nguoi, thieu_gio = [], []
    q = PV.loc(select(YeuCauHdv).order_by(YeuCauHdv.bat_dau), YeuCauHdv, u)
    for y in db.execute(q).scalars():
        if y.trang_thai == "huy":
            continue
        d = yc_out(db, y)
        if d["con_thieu"] > 0:
            thieu_nguoi.append(d)
        if y.thieu_gio():
            thieu_gio.append(d)
    pc_thieu_gio = []
    for a in db.execute(select(GuideAssignment)).scalars():
        if a.status in HDV.KHONG_CHIEM_LICH:
            continue
        if HDV.khong_so_duoc(a.bat_dau, a.ket_thuc):
            t = db.get(Tour, a.tour_id)
            pc_thieu_gio.append({"id": a.id, "tour_id": a.tour_id, "tour_code": t.code if t else "",
                                 "guide_id": a.guide_id, "days": a.days, "status": a.status})
    return {"yeu_cau_con_thieu_nguoi": thieu_nguoi,
            "yeu_cau_chua_co_gio": thieu_gio,
            "phan_cong_chua_co_gio": pc_thieu_gio,
            "ghi_chu": "Phân công chưa có giờ thì KHÔNG kiểm được trùng lịch – đây là việc còn thiếu, "
                       "không phải đã kiểm và không trùng."}


@router.post("/guide-assignments/yeu-cau", status_code=201)
def yeu_cau_lap(data: YeuCauIn, u: User = Depends(require_roles(*YC_LAP)), db: Session = Depends(get_db)):
    t = db.get(Tour, data.tour_id)
    if not t:
        raise HTTPException(404, "Không có chuyến")
    if (data.so_hdv or 0) <= 0:
        raise HTTPException(422, "Số hướng dẫn viên phải lớn hơn 0")
    if data.bat_dau and data.ket_thuc and data.ket_thuc <= data.bat_dau:
        raise HTTPException(422, "Giờ kết thúc phải sau giờ bắt đầu")
    y = YeuCauHdv(**data.model_dump(), nguoi_lap=u.username,
                  company_id=getattr(t, "company_id", None))
    db.add(y); db.flush()
    R.audit(db, u.username, u.role, "lap_yeu_cau_hdv", f"tour:{t.code}",
            after={"so_hdv": y.so_hdv, "bat_dau": str(y.bat_dau or ""), "ket_thuc": str(y.ket_thuc or "")})
    db.commit()
    return {"id": y.id, "message": f"Đã gửi yêu cầu {y.so_hdv} hướng dẫn viên cho {t.code}"}


class YeuCauHuy(BaseModel):
    phien_ban: int | None = None
    ly_do: str = ""


@router.post("/guide-assignments/yeu-cau/{yid}/huy")
def yeu_cau_huy(yid: int, data: YeuCauHuy, u: User = Depends(require_roles(*YC_LAP)), db: Session = Depends(get_db)):
    y = db.get(YeuCauHdv, yid)
    if not y:
        raise HTTPException(404, "Không có yêu cầu")
    if not (data.ly_do or "").strip():
        raise HTTPException(422, "Huỷ yêu cầu phải ghi lý do")
    GML.kiem_phien_ban(y, data.phien_ban, f"Yêu cầu HDV #{y.id}", lambda: yc_out(db, y))
    y.trang_thai, y.ly_do_huy = "huy", data.ly_do[:200]
    y.sua_boi, y.sua_luc = u.username, datetime.now()
    GML.tang_phien_ban(y)
    R.audit(db, u.username, u.role, "huy_yeu_cau_hdv", f"yeu_cau:{y.id}", after={"ly_do": y.ly_do_huy})
    db.commit()
    return {"message": "Đã huỷ yêu cầu"}


class GioIn(BaseModel):
    """Gửi RỖNG cả hai mốc = GỠ giờ, đưa phân công về lại ô 'chưa kiểm được trùng'. Gỡ được là bắt
    buộc: gõ nhầm mà không xoá về 'chưa biết' được thì người nhập sẽ để nguyên giờ sai – tệ hơn trống."""
    phien_ban: int | None = None
    bat_dau: datetime | None = None
    ket_thuc: datetime | None = None


@router.post("/guide-assignments/{aid}/gio")
def assign_gio(aid: int, data: GioIn, u: User = Depends(require_roles(*DIEU_DONG)), db: Session = Depends(get_db)):
    a = db.get(GuideAssignment, aid)
    if not a:
        raise HTTPException(404, "Không có phân công")
    if a.status in ("tu_choi", "huy", "het_han"):
        raise HTTPException(422, f"Phân công đã ở trạng thái '{a.status}' – sửa giờ không còn ý nghĩa")
    GML.kiem_phien_ban(a, data.phien_ban, f"Phân công HDV #{a.id}",
                       lambda: {"id": a.id, "bat_dau": a.bat_dau, "ket_thuc": a.ket_thuc, "phien_ban": a.phien_ban})
    if data.bat_dau and data.ket_thuc and data.ket_thuc <= data.bat_dau:
        raise HTTPException(422, "Giờ kết thúc phải sau giờ bắt đầu")
    a.bat_dau, a.ket_thuc = data.bat_dau, data.ket_thuc
    a.gio_boi, a.gio_luc = u.username, datetime.now()
    GML.tang_phien_ban(a)
    if not HDV.khong_so_duoc(a.bat_dau, a.ket_thuc):
        HDV.khoa_hdv(db, a.guide_id)
        db.flush()
        HDV.canh_trung_sau_khi_ghi(db, a)
    R.audit(db, u.username, u.role, "dat_gio_phan_cong_hdv", f"assign:{a.id}",
            after={"bat_dau": str(a.bat_dau or ""), "ket_thuc": str(a.ket_thuc or "")})
    db.commit()
    return {"message": "Đã gỡ giờ – phân công quay lại danh sách chưa kiểm được trùng"
                       if HDV.khong_so_duoc(a.bat_dau, a.ket_thuc) else "Đã ghi giờ, không trùng với chuyến nào"}


# ---------- Phòng HDV Đợt 2: báo cáo sau tour (06/10/2026) ----------
# Bốn cửa, đúng một vòng đời: lập nháp → gửi → trả bổ sung / xác nhận.
#
# AI ĐƯỢC LÀM GÌ. Người NỘP là hướng dẫn viên của chính phân công ấy (Chủ tịch chốt 06/10: HDV có tài
# khoản VTOS). Người KIỂM là Trưởng phòng Hướng dẫn. Hai vai KHÔNG được là một: tự nộp rồi tự xác
# nhận thì cái kiểm ấy không kiểm gì cả. Cổng `_khong_tu_kiem` canh đúng điều đó.
#
# Vai trò lấy từ danh sách ĐÃ CÓ, không nghĩ ra vai mới.
BC_KIEM = ("tp_hd", "hcns", "cntt")


def bc_out(db: Session, b: BaoCaoSauTour) -> dict:
    t = db.get(Tour, b.tour_id)
    return {"id": b.id, "phien_ban": b.phien_ban, "assignment_id": b.assignment_id,
            "tour_id": b.tour_id, "tour_code": t.code if t else "", "guide_id": b.guide_id,
            "ban_so": b.ban_so, "thay_cho_id": b.thay_cho_id, "bi_thay": b.bi_thay,
            "chuong_trinh_thuc_hien": b.chuong_trinh_thuc_hien,
            # Số khách gửi ra màn hình ĐỂ NGUYÊN, kể cả rỗng: "chưa đếm" phải hiện là ô trống, không
            # phải số 0. Chỉ phép TÍNH mới xử rỗng thành 0.
            "so_khach_thuc_te": b.so_khach_thuc_te,
            "danh_gia_ncc": b.danh_gia_ncc, "su_co": b.su_co,
            "khoan_chi_thu_ho": b.khoan_chi_thu_ho, "viec_chua_xong": b.viec_chua_xong,
            "trang_thai": b.trang_thai, "trang_thai_ten": TRANG_THAI_BC.get(b.trang_thai, b.trang_thai),
            "han_nop": b.han_nop, "tre_han": b.tre_han(), "da_khoa": b.da_khoa(),
            "nguoi_nop": b.nguoi_nop, "nop_luc": b.nop_luc,
            "nguoi_kiem": b.nguoi_kiem, "kiem_luc": b.kiem_luc, "y_kien_kiem": b.y_kien_kiem}


def _phan_cong_cua_toi(db: Session, u: User, aid: int) -> GuideAssignment:
    """Hướng dẫn viên chỉ chạm được phân công của chính mình. Kiểm bằng hồ sơ nhân sự nối với tài
    khoản, KHÔNG bằng tên — hai người trùng tên là chuyện có thật."""
    a = db.get(GuideAssignment, aid)
    if not a:
        raise HTTPException(404, "Không có phân công")
    if u.role in BC_KIEM:
        return a
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e is None or e.id != a.guide_id:
        raise HTTPException(403, "Chỉ hướng dẫn viên của chuyến này mới nộp được báo cáo")
    return a


class BaoCaoIn(BaseModel):
    chuong_trinh_thuc_hien: str = ""
    so_khach_thuc_te: int | None = None
    danh_gia_ncc: str = ""
    su_co: str = ""
    khoan_chi_thu_ho: str = ""
    viec_chua_xong: str = ""


@router.get("/guide-assignments/{aid}/bao-cao")
def bc_doc(aid: int, u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd", "hdv")), db: Session = Depends(get_db)):
    a = _phan_cong_cua_toi(db, u, aid)
    # P6 – hàng rào phạm vi pháp nhân, khai ở PHAI_LOC. Khai mà không nối thì hàng rào chưa bật.
    q = PV.loc(select(BaoCaoSauTour).where(BaoCaoSauTour.assignment_id == a.id)
               .order_by(BaoCaoSauTour.ban_so), BaoCaoSauTour, u)
    ds = db.execute(q).scalars().all()
    dang_xet = HDV.ban_dang_xet(db, a.id)
    return {"dang_xet": bc_out(db, dang_xet) if dang_xet else None,
            "cac_ban": [bc_out(db, b) for b in ds],
            "ghi_chu": "Chưa có bản nào KHÁC với có bản chưa xong – hai việc gọi hai người khác nhau."}


@router.post("/guide-assignments/{aid}/bao-cao", status_code=201)
def bc_lap(aid: int, data: BaoCaoIn, u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd", "hdv")), db: Session = Depends(get_db)):
    """Lập bản nháp, hoặc sửa bản nháp đang có. Bản ĐÃ GỬI thì không sửa ở đây – gửi bản mới."""
    a = _phan_cong_cua_toi(db, u, aid)
    cu = HDV.ban_dang_xet(db, a.id)
    if cu is not None and cu.da_khoa():
        raise HTTPException(422, {
            "gate": "BAO_CAO_DA_KHOA",
            "message": f"Bản {cu.ban_so} đã gửi, không sửa đè được. Dùng cửa 'gửi bản mới' để lập bản "
                       f"tiếp theo – bản cũ vẫn giữ nguyên để đọc lại.",
            "ban_dang_co": cu.id})
    t = db.get(Tour, a.tour_id)
    if cu is None:
        b = BaoCaoSauTour(assignment_id=a.id, tour_id=a.tour_id, guide_id=a.guide_id,
                          company_id=getattr(t, "company_id", None),
                          han_nop=HDV.han_nop_cua(getattr(t, "end_date", None)),
                          nguoi_nop=u.username, **data.model_dump())
        db.add(b)
    else:
        b = cu
        for k, v in data.model_dump().items():
            setattr(b, k, v)
        b.trang_thai = "nhap"
        GML.tang_phien_ban(b)
    db.flush()
    HDV.dong_bo_co_bao_cao(db, a)
    R.audit(db, u.username, u.role, "luu_nhap_bao_cao_tour", f"assign:{a.id}", after={"ban_so": b.ban_so})
    db.commit()
    return {"id": b.id, "ban_so": b.ban_so, "message": "Đã lưu nháp – chưa gửi, Trưởng phòng chưa thấy"}


class BcGui(BaseModel):
    phien_ban: int | None = None


@router.post("/guide-assignments/{aid}/bao-cao/gui")
def bc_gui(aid: int, data: BcGui, u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd", "hdv")), db: Session = Depends(get_db)):
    a = _phan_cong_cua_toi(db, u, aid)
    b = HDV.ban_dang_xet(db, a.id)
    if b is None:
        raise HTTPException(404, "Chưa có bản nháp nào để gửi")
    if b.da_khoa():
        raise HTTPException(422, f"Bản {b.ban_so} đã gửi rồi")
    GML.kiem_phien_ban(b, data.phien_ban, f"Báo cáo tour bản {b.ban_so}", lambda: bc_out(db, b))
    # Gửi một tờ trống thì không phải là đã báo cáo. Chương trình thực hiện là phần tối thiểu: nó là
    # thứ người kiểm đối chiếu với chương trình đã bán.
    if not (b.chuong_trinh_thuc_hien or "").strip():
        raise HTTPException(422, "Phải ghi chương trình thực hiện trước khi gửi")
    b.trang_thai, b.nop_luc, b.nguoi_nop = "da_gui", datetime.now(), u.username
    GML.tang_phien_ban(b)
    HDV.dong_bo_co_bao_cao(db, a)
    R.audit(db, u.username, u.role, "gui_bao_cao_tour", f"assign:{a.id}", after={"ban_so": b.ban_so})
    db.commit()
    return {"message": f"Đã gửi bản {b.ban_so}. Nội dung khoá lại; muốn sửa thì gửi bản mới.",
            "tre_han": b.tre_han()}


class BcKiem(BaseModel):
    phien_ban: int | None = None
    xac_nhan: bool
    y_kien: str = ""


# ───── Cửa báo cáo cho CHÍNH HDV, nằm trong nhóm API của màn hình /xe-hdv ─────
# Màn hình /xe-hdv khai nhóm `/api/v1/xe-hdv` (app/services/access.py::MAN_HINH_API). Nếu màn hình ấy
# gọi thẳng `/api/v1/guide-assignments` thì phải khai thêm nhóm ấy cho nó — mà khai như vậy là NỚI
# QUYỀN THẬT: tài xế cũng mở màn hình này, và nhóm guide-assignments chứa cả cửa điều động, cửa tạm
# ứng, cửa đề xuất. Mở một cửa cho HDV mà kéo theo cả chùm cho tài xế là trả giá sai chỗ.
#
# Nên bốn cửa dưới đây chỉ là LỐI VÀO KHÁC của đúng bốn hàm trên: cùng một thân, cùng `_phan_cong_cua_toi`
# canh người, nhưng đường dẫn nằm trong nhóm màn hình này đã được khai, và vai trò thu lại còn ĐÚNG `hdv`.
# Tài xế không vào được, và bản đồ quyền không phải sửa một dòng nào.
@router.get("/xe-hdv/bao-cao/{aid}")
def bc_doc_cua_toi(aid: int, u: User = Depends(require_roles("hdv")), db: Session = Depends(get_db)):
    return bc_doc(aid, u, db)


@router.post("/xe-hdv/bao-cao/{aid}", status_code=201)
def bc_lap_cua_toi(aid: int, data: BaoCaoIn, u: User = Depends(require_roles("hdv")), db: Session = Depends(get_db)):
    return bc_lap(aid, data, u, db)


@router.post("/xe-hdv/bao-cao/{aid}/gui")
def bc_gui_cua_toi(aid: int, data: BcGui, u: User = Depends(require_roles("hdv")), db: Session = Depends(get_db)):
    return bc_gui(aid, data, u, db)


@router.post("/xe-hdv/bao-cao/{aid}/ban-moi", status_code=201)
def bc_ban_moi_cua_toi(aid: int, data: BaoCaoIn, u: User = Depends(require_roles("hdv")), db: Session = Depends(get_db)):
    return bc_ban_moi(aid, data, u, db)


@router.post("/guide-assignments/{aid}/bao-cao/kiem")
def bc_kiem(aid: int, data: BcKiem, u: User = Depends(require_roles(*BC_KIEM)), db: Session = Depends(get_db)):
    """Trưởng phòng xác nhận, hoặc trả lại kèm lý do."""
    a = db.get(GuideAssignment, aid)
    if not a:
        raise HTTPException(404, "Không có phân công")
    b = HDV.ban_dang_xet(db, a.id)
    if b is None or b.trang_thai != "da_gui":
        raise HTTPException(422, "Không có bản nào đang chờ kiểm")
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if e is not None and e.id == a.guide_id:
        raise HTTPException(403, "Không tự kiểm báo cáo của chính mình")
    GML.kiem_phien_ban(b, data.phien_ban, f"Báo cáo tour bản {b.ban_so}", lambda: bc_out(db, b))
    if not data.xac_nhan and not (data.y_kien or "").strip():
        raise HTTPException(422, "Trả lại phải ghi rõ thiếu gì – không ghi thì người nộp phải đoán")
    b.trang_thai = "da_xac_nhan" if data.xac_nhan else "can_bo_sung"
    b.nguoi_kiem, b.kiem_luc, b.y_kien_kiem = u.username, datetime.now(), (data.y_kien or "")[:2000]
    GML.tang_phien_ban(b)
    HDV.dong_bo_co_bao_cao(db, a)
    R.audit(db, u.username, u.role, "kiem_bao_cao_tour", f"assign:{a.id}",
            after={"ban_so": b.ban_so, "ket_qua": b.trang_thai})
    db.commit()
    return {"message": "Đã xác nhận – gỡ treo chào chuyến và treo thù lao cho phân công này"
                       if data.xac_nhan else "Đã trả lại kèm lý do – phân công vẫn còn nợ báo cáo"}


@router.post("/guide-assignments/{aid}/bao-cao/ban-moi", status_code=201)
def bc_ban_moi(aid: int, data: BaoCaoIn, u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd", "hdv")), db: Session = Depends(get_db)):
    """Lập bản TIẾP THEO thay cho bản đã gửi. Bản cũ giữ nguyên, chỉ đánh dấu đã bị thay."""
    a = _phan_cong_cua_toi(db, u, aid)
    cu = HDV.ban_dang_xet(db, a.id)
    if cu is None:
        raise HTTPException(404, "Chưa có bản nào – dùng cửa lập nháp")
    if not cu.da_khoa() and cu.trang_thai != "can_bo_sung":
        raise HTTPException(422, f"Bản {cu.ban_so} còn là nháp, sửa thẳng chứ không cần bản mới")
    t = db.get(Tour, a.tour_id)
    moi = BaoCaoSauTour(assignment_id=a.id, tour_id=a.tour_id, guide_id=a.guide_id,
                        company_id=getattr(t, "company_id", None),
                        han_nop=cu.han_nop, ban_so=cu.ban_so + 1, thay_cho_id=cu.id,
                        nguoi_nop=u.username, **data.model_dump())
    cu.bi_thay = True
    db.add(moi); db.flush()
    HDV.dong_bo_co_bao_cao(db, a)
    R.audit(db, u.username, u.role, "lap_ban_moi_bao_cao_tour", f"assign:{a.id}",
            after={"ban_so": moi.ban_so, "thay_cho": cu.id})
    db.commit()
    return {"id": moi.id, "ban_so": moi.ban_so,
            "message": f"Đã lập bản {moi.ban_so} thay cho bản {cu.ban_so} – bản cũ vẫn đọc lại được"}


@router.get("/guide-assignments/bao-cao/thieu-theo-tour")
def bc_thieu_theo_tour(tour_id: int, u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd")), db: Session = Depends(get_db)):
    """Căn cứ để màn hình quyết toán KHÔNG gọi một tờ là 'hoàn tất' khi phần hướng dẫn viên chưa xong
    – Chủ tịch chốt 06/10/2026. Trả về DANH SÁCH NGƯỜI, không trả một ô đỏ: người làm quyết toán cần
    biết phải gọi ai."""
    thieu = HDV.thieu_bao_cao_cua_tour(db, tour_id)
    return {"tour_id": tour_id, "con_thieu": len(thieu), "danh_sach": thieu,
            "duoc_goi_hoan_tat": len(thieu) == 0}


# ---------- Phòng HDV Đợt 3: tiền của hướng dẫn viên (07/10/2026) ----------
# Ba cửa: lập khoản ứng · ghi nhận tiền đã nhận / chi hộ / nộp lại · đọc sổ theo NGƯỜI.
#
# SỔ NÀY KHÔNG THAY `tour_guide_advances`. Bảng kia là dòng chi trên tờ quyết toán của MỘT CHUYẾN;
# sổ này là sổ của MỘT NGƯỜI. Hai cái trả lời hai câu khác nhau: "chuyến này chi cho HDV bao nhiêu"
# và "người này còn giữ bao nhiêu tiền công ty". Câu thứ hai là câu phải trả lời trước khi đưa tiếp
# một khoản ứng mới, và hôm nay chưa hỏi được.
#
# TIỀN THÌ KẾ TOÁN GHI. Cửa lập khoản ứng mở cho phòng HDV (đề nghị), nhưng ba cột tiền thật sự —
# đã nhận, chi hộ được duyệt, đã nộp lại — chỉ Kế toán ghi. Để phòng tự ghi "đã nhận" thì con số ấy
# không còn là chứng cứ, nó chỉ là lời khai.
UNG_LAP = ("tp_hd", "hcns", "cntt", "ketoan")
UNG_GHI_TIEN = ("ketoan", "cntt")


def ung_out(db: Session, x: TamUngHdv) -> dict:
    t = db.get(Tour, x.tour_id) if x.tour_id else None
    return {"id": x.id, "phien_ban": x.phien_ban, "guide_id": x.guide_id,
            "assignment_id": x.assignment_id, "tour_id": x.tour_id,
            "tour_code": t.code if t else "",
            "chu_tien": x.chu_tien, "chu_tien_ten": CHU_TIEN.get(x.chu_tien, x.chu_tien),
            "loai_tien": x.loai_tien,
            # Bốn cột tiền gửi ra màn hình ĐỂ NGUYÊN, kể cả rỗng: "chưa nhận tiền" phải hiện ô trống,
            # không phải số 0. Chỉ phép TÍNH mới xử rỗng thành 0.
            "de_nghi": x.de_nghi, "da_nhan": x.da_nhan,
            "chi_ho_duyet": x.chi_ho_duyet, "da_nop_lai": x.da_nop_lai,
            "so_du": x.so_du(), "muc_dich": x.muc_dich,
            "trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_UNG.get(x.trang_thai, x.trang_thai),
            "ngay_de_nghi": x.ngay_de_nghi, "ngay_nhan": x.ngay_nhan, "ngay_tat_toan": x.ngay_tat_toan,
            "ghi_chu": x.ghi_chu, "nguoi_lap": x.nguoi_lap}


class UngIn(BaseModel):
    guide_id: int
    assignment_id: int | None = None
    tour_id: int | None = None
    chu_tien: str = "vietourist"
    loai_tien: str = "VND"
    de_nghi: float | None = None
    muc_dich: str = ""
    ngay_de_nghi: date | None = None
    ghi_chu: str = ""


@router.post("/guide-assignments/tam-ung", status_code=201)
def ung_lap(data: UngIn, u: User = Depends(require_roles(*UNG_LAP)), db: Session = Depends(get_db)):
    e = db.get(Employee, data.guide_id)
    if not e:
        raise HTTPException(404, "Không có hướng dẫn viên")
    if data.chu_tien not in CHU_TIEN:
        raise HTTPException(422, f"Chủ tiền phải là một trong: {', '.join(CHU_TIEN)}")
    t = db.get(Tour, data.tour_id) if data.tour_id else None
    x = TamUngHdv(**data.model_dump(), nguoi_lap=u.username,
                  company_id=getattr(t, "company_id", None))
    db.add(x); db.flush()
    R.audit(db, u.username, u.role, "lap_tam_ung_hdv", f"hdv:{e.code or e.id}",
            after={"de_nghi": data.de_nghi, "chu_tien": data.chu_tien, "loai_tien": data.loai_tien})
    db.commit()
    return {"id": x.id, "message": f"Đã lập đề nghị ứng cho {e.full_name} – chờ Kế toán chi"}


class UngTien(BaseModel):
    """Ba cột tiền. Gửi RỖNG một cột = KHÔNG đổi cột ấy; muốn xoá về chưa-có thì gửi `xoa` kèm tên cột.
    Phân biệt hai việc ấy là bắt buộc: không phân biệt thì mỗi lần ghi chi hộ sẽ vô tình xoá số đã nhận."""
    phien_ban: int | None = None
    da_nhan: float | None = None
    chi_ho_duyet: float | None = None
    da_nop_lai: float | None = None
    ngay_nhan: date | None = None
    xoa: list[str] = []
    ghi_chu: str = ""


@router.post("/guide-assignments/tam-ung/{uid}/tien")
def ung_ghi_tien(uid: int, data: UngTien, u: User = Depends(require_roles(*UNG_GHI_TIEN)), db: Session = Depends(get_db)):
    x = db.get(TamUngHdv, uid)
    if not x:
        raise HTTPException(404, "Không có khoản ứng")
    if x.trang_thai in ("tat_toan", "huy"):
        raise HTTPException(422, f"Khoản ứng đã ở trạng thái '{x.trang_thai}' – ghi thêm tiền vào một "
                                 f"khoản đã đóng chỉ làm sai lại một việc đã xong")
    GML.kiem_phien_ban(x, data.phien_ban, f"Khoản ứng #{x.id}", lambda: ung_out(db, x))
    for c in ("da_nhan", "chi_ho_duyet", "da_nop_lai"):
        v = getattr(data, c)
        if c in data.xoa:
            setattr(x, c, None)
        elif v is not None:
            if v < 0:
                raise HTTPException(422, f"{c} không âm – chi hộ vượt ứng thì để số dư âm, không để cột âm")
            setattr(x, c, v)
    if data.ngay_nhan is not None:
        x.ngay_nhan = data.ngay_nhan
    if x.da_nhan is not None and x.trang_thai == "de_nghi":
        x.trang_thai = "da_nhan"
    if data.ghi_chu:
        x.ghi_chu = data.ghi_chu
    x.sua_boi, x.sua_luc = u.username, datetime.now()
    GML.tang_phien_ban(x)
    R.audit(db, u.username, u.role, "ghi_tien_tam_ung_hdv", f"ung:{x.id}",
            after={"da_nhan": x.da_nhan, "chi_ho": x.chi_ho_duyet, "nop_lai": x.da_nop_lai, "so_du": x.so_du()})
    db.commit()
    return {"so_du": x.so_du(),
            "message": "Đã ghi. Số dư âm nghĩa là công ty nợ lại hướng dẫn viên – hệ thống không tự trả."
                       if x.so_du() < 0 else "Đã ghi"}


class UngTatToan(BaseModel):
    phien_ban: int | None = None
    ngay: date | None = None


@router.post("/guide-assignments/tam-ung/{uid}/tat-toan")
def ung_tat_toan(uid: int, data: UngTatToan, u: User = Depends(require_roles(*UNG_GHI_TIEN)), db: Session = Depends(get_db)):
    x = db.get(TamUngHdv, uid)
    if not x:
        raise HTTPException(404, "Không có khoản ứng")
    GML.kiem_phien_ban(x, data.phien_ban, f"Khoản ứng #{x.id}", lambda: ung_out(db, x))
    if abs(x.so_du()) > 0.004:
        raise HTTPException(422, {
            "gate": "UNG_CHUA_VE_KHONG",
            "message": f"Số dư còn {x.so_du():,.0f} – tất toán một khoản chưa về 0 là giấu mất phần "
                       f"chênh. Ghi nốt tiền nộp lại, hoặc để Kế toán trả phần công ty nợ.",
            "so_du": x.so_du()})
    x.trang_thai, x.ngay_tat_toan = "tat_toan", data.ngay or date.today()
    x.sua_boi, x.sua_luc = u.username, datetime.now()
    GML.tang_phien_ban(x)
    R.audit(db, u.username, u.role, "tat_toan_tam_ung_hdv", f"ung:{x.id}")
    db.commit()
    return {"message": "Đã tất toán"}


@router.get("/guide-assignments/tam-ung/so-theo-nguoi")
def ung_so_theo_nguoi(guide_id: int, u: User = Depends(require_roles(*HR_READ, "nv_dh", "tp_hd")), db: Session = Depends(get_db)):
    """Câu hỏi mà hôm nay chưa hỏi được: hướng dẫn viên này còn giữ bao nhiêu tiền công ty.

    Trả về NHIỀU TÚI, không một con số – xem `so_du_ung` trong app/services/hdv.py.
    """
    e = db.get(Employee, guide_id)
    if not e:
        raise HTTPException(404, "Không có hướng dẫn viên")
    q = PV.loc(select(TamUngHdv).where(TamUngHdv.guide_id == guide_id)
               .order_by(desc(TamUngHdv.id)), TamUngHdv, u)
    return {"guide_id": guide_id, "hdv": e.full_name,
            "cac_tui": HDV.so_du_ung(db, guide_id),
            "cac_khoan": [ung_out(db, x) for x in db.execute(q).scalars()],
            "ghi_chu": "Không gộp khác chủ tiền hoặc khác loại tiền. Tiền thu hộ khách là túi riêng, "
                       "không bù trừ sang túi công ty."}


@router.get("/guide-assignments/thu-lao/doi-soat")
def thu_lao_doi_soat(tu_ngay: date, den_ngay: date,
                     u: User = Depends(require_roles(*HR_READ, "tp_hd")), db: Session = Depends(get_db)):
    """BẢNG ĐỐI SOÁT THÙ LAO KỲ — CHỈ ĐỌC. Chủ tịch chốt 06/10/2026: quyết toán tour là sổ gốc, bảng
    kỳ chỉ đọc và tổng hợp, KHÔNG ghi tiền lần hai.

    Nên ở đây không có một cột nào được ghi xuống cơ sở dữ liệu. Mọi con số tính lại từ phân công và
    bảng giá mỗi lần mở. Chậm hơn một bảng lưu sẵn, và đó là cái giá phải trả để không bao giờ có hai
    con số thù lao khác nhau cho cùng một chuyến.

    Thiếu bảng giá thì để TRỐNG và đếm riêng, không trả 0: một bảng thù lao toàn số 0 trông như đã
    tính xong và đã trả đủ.
    """
    ten = {e.id: e for e in db.execute(select(Employee)).scalars()}
    dong, thieu_gia = [], 0
    for a in db.execute(select(GuideAssignment)).scalars():
        if a.status in HDV.KHONG_CHIEM_LICH:
            continue
        t = db.get(Tour, a.tour_id)
        if t is None or t.end_date is None or not (tu_ngay <= t.end_date <= den_ngay):
            continue
        gr = db.get(GuideRate, a.rate_id) if a.rate_id else None
        don_gia = a.rate_per_day if a.rate_per_day is not None else (gr.rate_per_day if gr else None)
        tien = HDV.thu_lao(a.days, don_gia, a.holiday)
        if tien is None:
            thieu_gia += 1
        e = ten.get(a.guide_id)
        bc = HDV.ban_dang_xet(db, a.id)
        dong.append({"assignment_id": a.id, "guide_id": a.guide_id,
                     "hdv": e.full_name if e else "", "tour_code": t.code, "loai_tour": t.tour_type,
                     "ngay_ket_thuc": t.end_date, "so_ngay": a.days, "don_gia": don_gia,
                     "le_tet": a.holiday, "thu_lao": tien, "vai_tro": a.vai_tro,
                     "da_bao_cao": bool(bc and bc.trang_thai == "da_xac_nhan"),
                     "da_hoan_ung": a.advance_settled,
                     # Treo thù lao là luật ĐÃ CÓ ở app/services/luong.py – ở đây chỉ HIỂN THỊ lại,
                     # không đặt luật thứ hai.
                     "treo_thu_lao": not (a.report_submitted and a.advance_settled)})
    tong = sum(d["thu_lao"] or 0 for d in dong)
    return {"tu_ngay": tu_ngay, "den_ngay": den_ngay, "so_dong": len(dong),
            "tong_thu_lao_tinh_duoc": tong, "so_dong_thieu_bang_gia": thieu_gia,
            "dong": dong,
            "ghi_chu": "Bảng ĐỌC, không ghi. Dòng thiếu bảng giá để trống và đếm riêng, không tính 0."}


# ---------- Phòng HDV Đợt 4: đề xuất và bước duyệt có cấp (07/10/2026) ----------
# Đặc tả v1.0 §10–§12. Đợt này dựng CÁI MÁY; các CON SỐ — loại hồ sơ nào, hạn mức bao nhiêu, ai duyệt
# — là chính sách và phải có người ký. Bảng cấu hình sinh ra RỖNG, và cửa trình CHẶN khi chưa có dòng
# nào khớp. Đó không phải chỗ làm dở: hệ thống tự chọn cấp duyệt khi thiếu cấu hình thì đường nó chọn
# thành tiền lệ, không ai ký mà vẫn thành luật.
DX_LAP = ("tp_hd", "hcns", "cntt")
CH_KY = ("chutich", "tgd")


def _ten_cap(vai: str) -> str:
    """Tên người đọc được của một cấp. `chutich|tgd` ra "Chủ tịch HĐQT hoặc Tổng giám đốc".

    Màn hình phải đọc được chữ "hoặc", vì nhìn chuỗi `chutich|tgd` thì người dùng không phân biệt
    được với hai cấp nối tiếp — mà hai cái ấy khác nhau ở số chữ ký.
    """
    return " hoặc ".join(ROLES.get(v, v) for v in [x.strip() for x in vai.split("|") if x.strip()])


def ch_out(c: CauHinhDuyetHdv) -> dict:
    return {"id": c.id, "loai": c.loai, "loai_ten": LOAI_DE_XUAT.get(c.loai, c.loai),
            "tu_so_tien": c.tu_so_tien, "den_so_tien": c.den_so_tien,
            "cac_cap": c.danh_sach_cap(), "cac_cap_ten": [_ten_cap(x) for x in c.danh_sach_cap()],
            "hieu_luc_tu": c.hieu_luc_tu,
            "trang_thai": c.trang_thai, "ky_boi": c.ky_boi, "ky_luc": c.ky_luc,
            "ghi_chu": c.ghi_chu, "lap_boi": c.lap_boi}


def dx_out(db: Session, d: DeXuatHdv) -> dict:
    buoc = db.execute(select(BuocDuyetHdv).where(BuocDuyetHdv.de_xuat_id == d.id)
                      .order_by(BuocDuyetHdv.thu_tu)).scalars().all()
    t = db.get(Tour, d.tour_id) if d.tour_id else None
    return {"id": d.id, "ma": d.ma, "phien_ban": d.phien_ban, "loai": d.loai,
            "loai_ten": LOAI_DE_XUAT.get(d.loai, d.loai), "ky": d.ky,
            "tour_id": d.tour_id, "tour_code": t.code if t else "", "guide_id": d.guide_id,
            "noi_dung": d.noi_dung, "ly_do": d.ly_do, "can_cu_tinh": d.can_cu_tinh,
            # Số tiền ra màn hình để nguyên: đề xuất không mang tiền (xin bổ sung nhân sự) phải hiện
            # ô trống, không phải 0.
            "so_tien": d.so_tien, "loai_tien": d.loai_tien, "han_xu_ly": d.han_xu_ly,
            "trang_thai": d.trang_thai, "trang_thai_ten": TRANG_THAI_DX.get(d.trang_thai, d.trang_thai),
            "cap_dang_cho": d.cap_dang_cho,
            "duong_di": [{"thu_tu": b.thu_tu, "vai_tro": b.vai_tro, "cac_vai": b.cac_vai(),
                          "vai_tro_ten": _ten_cap(b.vai_tro), "trang_thai": b.trang_thai,
                          "nguoi": b.nguoi, "luc": b.luc, "y_kien": b.y_kien} for b in buoc],
            "nguoi_lap": d.nguoi_lap, "lap_luc": d.lap_luc, "trinh_luc": d.trinh_luc,
            "xong_luc": d.xong_luc}


class CauHinhIn(BaseModel):
    loai: str
    tu_so_tien: float | None = None
    # RỖNG = KHÔNG CÓ TRẦN. Không phải "chưa biết" – xem chú thích ở CauHinhDuyetHdv.
    den_so_tien: float | None = None
    cac_cap: list[str] = []
    hieu_luc_tu: date | None = None
    ghi_chu: str = ""


@router.get("/guide-assignments/de-xuat/cau-hinh")
def ch_ds(u: User = Depends(require_roles(*HR_READ, "tp_hd")), db: Session = Depends(get_db)):
    ds = db.execute(select(CauHinhDuyetHdv).order_by(CauHinhDuyetHdv.loai, CauHinhDuyetHdv.id)).scalars().all()
    return {"so_dong": len(ds), "dong": [ch_out(c) for c in ds],
            "ghi_chu": "Bảng này sinh ra RỖNG. Chưa có dòng hiệu lực nào khớp thì cửa trình bị chặn – "
                       "hệ thống không tự chọn cấp duyệt."}


@router.post("/guide-assignments/de-xuat/cau-hinh", status_code=201)
def ch_lap(data: CauHinhIn, u: User = Depends(require_roles("hcns", "cntt", "tp_hd")), db: Session = Depends(get_db)):
    """Trình một dòng cấu hình. CHƯA có hiệu lực cho tới khi Chủ tịch hoặc TGĐ ký."""
    if data.loai not in LOAI_DE_XUAT:
        raise HTTPException(422, f"Loại hồ sơ phải là một trong: {', '.join(LOAI_DE_XUAT)}")
    if not data.cac_cap:
        raise HTTPException(422, "Phải khai ít nhất một cấp duyệt – một cấu hình không cấp nào là "
                                 "một đường đi vòng qua mọi chữ ký")
    # Mỗi phần tử của `cac_cap` là MỘT cấp; trong một cấp, `|` nghĩa là ai trong số đó ký cũng được.
    # Kiểm từng tên vai trò ở cửa nhập, vì một tên viết sai sẽ thành một cấp KHÔNG AI ký được, và hồ sơ
    # đứng mãi ở cấp ấy mà không ai biết tại sao — lỗi lúc nhập thì sửa một dòng, lỗi lúc chạy thì phải
    # dò cả bảng.
    cac_cap: list[str] = []
    for cap in data.cac_cap:
        vais = [x.strip() for x in str(cap).split("|") if x.strip()]
        if not vais:
            raise HTTPException(422, "Có một cấp duyệt để trống")
        for v in vais:
            if v not in ROLES:
                raise HTTPException(422, f"Vai trò không có trong danh mục: '{v}'")
        if len(set(vais)) != len(vais):
            raise HTTPException(422, f"Một cấp khai trùng vai trò: '{cap}'")
        cac_cap.append("|".join(vais))
    if (data.tu_so_tien is not None and data.den_so_tien is not None
            and data.den_so_tien < data.tu_so_tien):
        raise HTTPException(422, "Trần phải lớn hơn sàn")
    c = CauHinhDuyetHdv(loai=data.loai, tu_so_tien=data.tu_so_tien, den_so_tien=data.den_so_tien,
                        cac_cap=",".join(cac_cap),
                        hieu_luc_tu=data.hieu_luc_tu, ghi_chu=data.ghi_chu, lap_boi=u.username)
    db.add(c); db.flush()
    R.audit(db, u.username, u.role, "trinh_cau_hinh_duyet_hdv", f"cauhinh:{c.id}",
            after={"loai": c.loai, "cac_cap": c.cac_cap})
    db.commit()
    return {"id": c.id, "message": "Đã trình cấu hình – chờ Chủ tịch hoặc TGĐ ký mới có hiệu lực"}


@router.post("/guide-assignments/de-xuat/cau-hinh/khai-mot-cap", status_code=201)
def ch_khai_mot_cap(u: User = Depends(require_roles(*CH_KY)), db: Session = Depends(get_db)):
    """Khai THẲNG luật đã chốt 06/10/2026: MỘT CẤP, Chủ tịch HOẶC TGĐ ký là xong, MỌI MỨC TIỀN.

    Cửa này KHÔNG NHẬN THAM SỐ. Cố ý: nó chỉ làm được đúng một việc — áp luật ấy cho sáu loại hồ sơ,
    một khoảng duy nhất từ 0 không trần. Nếu nó nhận tham số thì nó thành một cửa khai cấu hình thứ
    hai, và cửa thứ hai ấy đi vòng qua vòng trình–ký của cửa thường. Muốn một đường đi KHÁC luật
    06/10 thì phải qua `POST .../cau-hinh` rồi có người ký, như mọi dòng cấu hình khác.

    Chỉ CHỦ TỊCH hoặc TGĐ gọi được, và `ky_boi` là chính người gọi — không phải robot. Ở đây người
    trình và người ký là một, khác quy tắc "người trình không tự ký" của cửa thường. Đó là có lý do:
    quy tắc kia để chặn cấp dưới tự duyệt hồ sơ mình trình; còn đây là cấp cao nhất CÔNG BỐ chính
    sách, và một công bố thì không có ai cao hơn để ký tiếp. Nhật ký ghi rõ là công bố trực tiếp.

    KHÔNG ĐÈ dòng đã có hiệu lực. Loại nào đã có đường đi rồi thì BỎ QUA và kể tên ra, vì đè lên một
    chính sách đang chạy là đổi luật mà không ai thấy — nguy hơn cả việc thiếu luật.
    """
    hom_nay = date.today()
    CAC_CAP = "chutich|tgd"
    GHI_CHU = "Quyết định Chủ tịch 06/10/2026: một cấp, CT hoặc TGĐ ký là xong, mọi mức tiền"
    da_khai, bo_qua = [], []
    for loai in LOAI_DE_XUAT:
        try:
            cu = HDV.tra_cau_hinh(db, loai, 0, hom_nay)
        except HTTPException:
            cu = None
        if cu is not None:
            bo_qua.append({"loai": loai, "loai_ten": LOAI_DE_XUAT[loai], "cau_hinh_id": cu.id,
                           "cac_cap": cu.danh_sach_cap()})
            continue
        c = CauHinhDuyetHdv(loai=loai, tu_so_tien=0, den_so_tien=None, cac_cap=CAC_CAP,
                            hieu_luc_tu=hom_nay, trang_thai="hieu_luc",
                            ky_boi=u.username, ky_luc=datetime.now(),
                            ghi_chu=GHI_CHU, lap_boi=u.username)
        db.add(c); db.flush()
        da_khai.append({"loai": loai, "loai_ten": LOAI_DE_XUAT[loai], "cau_hinh_id": c.id})
        R.audit(db, u.username, u.role, "cong_bo_cau_hinh_duyet_hdv", f"cauhinh:{c.id}",
                after={"loai": loai, "cac_cap": CAC_CAP, "tu_so_tien": 0, "den_so_tien": None,
                       "can_cu": GHI_CHU, "nguoi_cong_bo": u.username})
    db.commit()
    return {"da_khai": da_khai, "bo_qua": bo_qua,
            "message": (f"Đã công bố {len(da_khai)} loại hồ sơ theo luật một cấp CT hoặc TGĐ."
                        + (f" Bỏ qua {len(bo_qua)} loại đã có đường đi — không đè lên chính sách đang chạy."
                           if bo_qua else ""))}


@router.post("/guide-assignments/de-xuat/cau-hinh/{cid}/ky")
def ch_ky(cid: int, u: User = Depends(require_roles(*CH_KY)), db: Session = Depends(get_db)):
    c = db.get(CauHinhDuyetHdv, cid)
    if not c or c.trang_thai != "cho_ky":
        raise HTTPException(404, "Không có cấu hình chờ ký")
    if c.lap_boi and u.username == c.lap_boi:
        raise HTTPException(422, "Người trình cấu hình không tự ký cấu hình mình trình")
    c.trang_thai, c.ky_boi, c.ky_luc = "hieu_luc", u.username, datetime.now()
    R.audit(db, u.username, u.role, "ky_cau_hinh_duyet_hdv", f"cauhinh:{c.id}")
    db.commit()
    return {"message": "Đã ký – cấu hình có hiệu lực"}


class DeXuatIn(BaseModel):
    loai: str
    tour_id: int | None = None
    guide_id: int | None = None
    ky: str = ""
    noi_dung: str = ""
    ly_do: str = ""
    can_cu_tinh: str = ""
    so_tien: float | None = None
    loai_tien: str = "VND"
    han_xu_ly: date | None = None


@router.post("/guide-assignments/de-xuat", status_code=201)
def dx_lap(data: DeXuatIn, u: User = Depends(require_roles(*DX_LAP)), db: Session = Depends(get_db)):
    if data.loai not in LOAI_DE_XUAT:
        raise HTTPException(422, f"Loại hồ sơ phải là một trong: {', '.join(LOAI_DE_XUAT)}")
    t = db.get(Tour, data.tour_id) if data.tour_id else None
    n = db.execute(select(func.count()).select_from(DeXuatHdv)).scalar() or 0
    d = DeXuatHdv(**data.model_dump(), ma=f"HDV-DX-{n + 1:05d}", nguoi_lap=u.username,
                  company_id=getattr(t, "company_id", None))
    db.add(d); db.flush()
    R.audit(db, u.username, u.role, "lap_de_xuat_hdv", f"dx:{d.ma}", after={"loai": d.loai, "so_tien": d.so_tien})
    db.commit()
    return {"id": d.id, "ma": d.ma, "message": "Đã lưu nháp – chưa trình, chưa ai thấy"}


class DxTrinh(BaseModel):
    phien_ban: int | None = None


@router.post("/guide-assignments/de-xuat/{did}/trinh")
def dx_trinh(did: int, data: DxTrinh, u: User = Depends(require_roles(*DX_LAP)), db: Session = Depends(get_db)):
    """Trình hồ sơ. Lập ĐỦ các bước ngay tại đây, theo cấu hình đang hiệu lực."""
    d = db.get(DeXuatHdv, did)
    if not d:
        raise HTTPException(404, "Không có đề xuất")
    if d.trang_thai not in ("nhap", "can_bo_sung"):
        raise HTTPException(422, f"Đề xuất đang ở '{d.trang_thai}' – không trình lại")
    GML.kiem_phien_ban(d, data.phien_ban, f"Đề xuất {d.ma}", lambda: dx_out(db, d))
    if not (d.ly_do or "").strip():
        raise HTTPException(422, "Phải ghi lý do trước khi trình")
    # Ném 422 THIEU_CAU_HINH_DUYET nếu chưa ai khai cấp duyệt cho mức tiền này.
    ch = HDV.tra_cau_hinh(db, d.loai, d.so_tien)
    HDV.lap_cac_buoc(db, d, ch)
    d.cau_hinh_id, d.trang_thai, d.cap_dang_cho = ch.id, "cho_duyet", 1
    d.trinh_luc = datetime.now()
    GML.tang_phien_ban(d)
    R.audit(db, u.username, u.role, "trinh_de_xuat_hdv", f"dx:{d.ma}",
            after={"duong_di": ch.danh_sach_cap()})
    db.commit()
    return {"message": f"Đã trình – đường đi: {' → '.join(ch.danh_sach_cap())}",
            "duong_di": ch.danh_sach_cap()}


class DxQuyet(BaseModel):
    phien_ban: int | None = None
    quyet_dinh: str          # dong_y / tra_bo_sung / tu_choi
    y_kien: str = ""


@router.post("/guide-assignments/de-xuat/{did}/quyet")
def dx_quyet(did: int, data: DxQuyet, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Cấp đang xử lý quyết định. Ba hành động, đúng như §12: đồng ý, trả bổ sung, từ chối.

    Quyền KHÔNG lấy từ require_roles: nó phụ thuộc DỮ LIỆU — bước đang chờ cần vai nào. Khai cứng một
    danh sách vai ở đây thì mỗi lần cấu hình thêm một cấp mới lại phải sửa mã, và cấp mới ấy sẽ bị
    chặn ở cửa dù cấu hình đã có chữ ký.

    CHỦ TỊCH QUYẾT 07/10/2026: cửa này khai vào bảng ngoại lệ KS-2 (`tools/ks2_khai_quyen.py`,
    mục CHAN_TANG_DICH_VU → `hdv:kiem_nguoi_quyet`), chứ KHÔNG khai một danh sách vai ở đây.

    Lý do chọn như vậy: danh sách vai được phép ký nằm trong bảng cấu hình ĐÃ CÓ CHỮ KÝ, không nằm
    trong mã. Khai cứng ở đây thì mã sẽ chặn đúng những cấp mà người ký vừa thêm — mã phủ quyết chữ
    ký. Đã thử `require_roles("chutich", "tgd")` và nó làm đỏ 7 phép thử của chính Đợt 4, vì đặc tả
    §10 cho phép khai cấu hình nhiều cấp với vai khác.

    Lời khai ấy KHÔNG được tin suông: phép thử KS-2 mở `hdv.kiem_nguoi_quyet` ra đọc, và đỏ ngay nếu
    hàng rào trong đó bị gỡ. Ba hàng rào: đúng vai của bước đang chờ, không phải người trình, và bước
    chưa ai quyết.
    """
    d = db.get(DeXuatHdv, did)
    if not d:
        raise HTTPException(404, "Không có đề xuất")
    if d.trang_thai != "cho_duyet":
        raise HTTPException(422, f"Đề xuất đang ở '{d.trang_thai}' – không có bước nào chờ quyết")
    if data.quyet_dinh not in QUYET_DINH:
        raise HTTPException(422, f"Quyết định phải là một trong: {', '.join(QUYET_DINH)}")
    b = HDV.buoc_dang_cho(db, d)
    if b is None:
        raise HTTPException(422, "Không có bước nào đang chờ")
    GML.kiem_phien_ban(d, data.phien_ban, f"Đề xuất {d.ma}", lambda: dx_out(db, d))
    HDV.kiem_nguoi_quyet(d, b, u.username, u.role)
    if data.quyet_dinh in ("tra_bo_sung", "tu_choi") and not (data.y_kien or "").strip():
        raise HTTPException(422, "Trả bổ sung hoặc từ chối đều PHẢI ghi lý do – không ghi thì người "
                                 "trình phải đoán, và thường đoán sai")
    b.trang_thai, b.nguoi, b.luc = data.quyet_dinh, u.username, datetime.now()
    b.y_kien = (data.y_kien or "")[:2000]
    if data.quyet_dinh == "dong_y":
        tiep = HDV.buoc_dang_cho(db, d)
        if tiep is None:
            d.trang_thai, d.cap_dang_cho, d.xong_luc = "da_duyet", 0, datetime.now()
            loi = "Đã duyệt đủ cấp"
        else:
            d.cap_dang_cho = tiep.thu_tu
            loi = f"Đã đồng ý – chuyển cấp {tiep.thu_tu} ({tiep.vai_tro})"
    else:
        d.trang_thai = "can_bo_sung" if data.quyet_dinh == "tra_bo_sung" else "tu_choi"
        d.cap_dang_cho = 0
        if data.quyet_dinh == "tu_choi":
            d.xong_luc = datetime.now()
        loi = "Đã trả lại kèm lý do" if data.quyet_dinh == "tra_bo_sung" else "Đã từ chối kèm lý do"
    GML.tang_phien_ban(d)
    R.audit(db, u.username, u.role, "quyet_de_xuat_hdv", f"dx:{d.ma}",
            after={"buoc": b.thu_tu, "quyet_dinh": data.quyet_dinh, "trang_thai": d.trang_thai})
    db.commit()
    return {"message": loi, "trang_thai": d.trang_thai}


@router.get("/guide-assignments/de-xuat")
def dx_ds(u: User = Depends(require_roles(*HR_READ, "tp_hd", "nv_dh")), db: Session = Depends(get_db)):
    q = PV.loc(select(DeXuatHdv).order_by(desc(DeXuatHdv.id)), DeXuatHdv, u)
    return [dx_out(db, d) for d in db.execute(q).scalars()]


@router.get("/guide-assignments/de-xuat/cho-toi-quyet")
def dx_cho_toi(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Hồ sơ đang chờ ĐÚNG vai trò của người đang đăng nhập. Không trả hồ sơ do chính họ trình."""
    ra = []
    q = PV.loc(select(DeXuatHdv).where(DeXuatHdv.trang_thai == "cho_duyet"), DeXuatHdv, u)
    for d in db.execute(q).scalars():
        b = HDV.buoc_dang_cho(db, d)
        if b is not None and b.vai_tro == u.role and d.nguoi_lap != u.username:
            ra.append(dx_out(db, d))
    return {"so_ho_so": len(ra), "ho_so": ra}


# ---------- Đội xe ----------
@router.get("/vehicles")
def vehicles(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    return [{"id": v.id, "plate": v.plate, "seats": v.seats, "kind": v.kind, "driver_id": v.driver_id, "driver": emps.get(v.driver_id, ""),
             "internal_rate_per_day": v.internal_rate_per_day, "active": v.active, "company_id": v.company_id,
             "company": cos[v.company_id].name if v.company_id in cos else "", "company_code": cos[v.company_id].code if v.company_id in cos else ""}
            for v in db.execute(select(Vehicle).order_by(Vehicle.plate)).scalars()]


class VehicleIn(BaseModel):
    plate: str
    seats: int = 45
    kind: str = "noi_bo"
    driver_id: int | None = None
    internal_rate_per_day: float | None = None


@router.post("/vehicles", status_code=201)
def vehicle_create(data: VehicleIn, u: User = Depends(require_roles("cntt", "hcns")), db: Session = Depends(get_db)):
    v = Vehicle(**data.model_dump()); db.add(v); db.flush()
    R.audit(db, u.username, u.role, "tao_xe", f"vehicle:{v.plate}", after=data.model_dump(mode="json")); db.commit()
    return {"message": f"Đã thêm xe {v.plate}"}


class VehicleUpdate(BaseModel):
    # extra="forbid": gửi một trường không nhận ở đây (lifecycle, company_id, source_note… – những trường
    # thuộc hồ sơ đội xe, sửa qua PUT /fleet/xe/{id}) sẽ báo 422 chứ không trả 200 rồi lặng lẽ bỏ qua.
    # Một lần "Đã cập nhật xe" mà thực ra không sửa gì là cách chắc chắn nhất để người dùng tin nhầm.
    model_config = ConfigDict(extra="forbid")
    plate: str | None = None
    seats: int | None = None
    kind: str | None = None
    driver_id: int | None = None
    internal_rate_per_day: float | None = None
    active: bool | None = None


@router.put("/vehicles/{vid}")
def vehicle_update(vid: int, data: VehicleUpdate, u: User = Depends(require_roles("cntt", "hcns", "tp_dh")), db: Session = Depends(get_db)):
    """Sửa hồ sơ xe – dùng để bổ sung số chỗ cho xe mới nạp và sửa loại xe nội bộ / hợp tác.
    Đổi loại sang xe hợp tác thì gỡ luôn pháp nhân sở hữu: xe thuê ngoài không phải tài sản của tập đoàn."""
    v = db.get(Vehicle, vid)
    if not v: raise HTTPException(404, "Không có xe")
    before = {"plate": v.plate, "seats": v.seats, "kind": v.kind, "driver_id": v.driver_id, "company_id": v.company_id}
    # exclude_unset: gửi driver_id = null là GỠ tài xế khỏi xe; trường không gửi thì giữ nguyên.
    # (exclude_none trước đây khiến không bao giờ gỡ được tài xế đã gán nhầm.)
    for k, val in data.model_dump(exclude_unset=True).items(): setattr(v, k, val)
    if v.kind == "hop_tac": v.company_id = None
    R.audit(db, u.username, u.role, "sua_ho_so_xe", f"vehicle:{v.plate}", before=before,
            after={"plate": v.plate, "seats": v.seats, "kind": v.kind, "driver_id": v.driver_id, "company_id": v.company_id}); db.commit()
    return {"message": f"Đã cập nhật xe {v.plate}"}


# ---------- Bảng giá xe nội bộ (master data, Chủ tịch + TGĐ duyệt) ----------
def rate_out(r: VehicleRate) -> dict:
    return {"id": r.id, "route": r.route, "days": r.days, "internal_price": r.internal_price, "partner_price": r.partner_price, "effective_from": r.effective_from,
            "status": r.status, "signed_chutich": r.signed_chutich, "signed_tgd": r.signed_tgd, "note": r.note, "proposed_by": r.proposed_by}


# ---------- Bảng giá HDV theo tuyến ----------
def grate_out(r: GuideRate) -> dict:
    return {"id": r.id, "route": r.route, "loai_tour": r.loai_tour, "days": r.days, "rate_per_day": r.rate_per_day, "old_rate_per_day": r.old_rate_per_day, "effective_from": r.effective_from,
            "status": r.status, "signed_chutich": r.signed_chutich, "signed_tgd": r.signed_tgd, "note": r.note, "proposed_by": r.proposed_by}


@router.get("/guide-rates")
def guide_rates(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [grate_out(r) for r in db.execute(select(GuideRate).order_by(GuideRate.status.desc(), GuideRate.id)).scalars()]


class GuideRateIn(BaseModel):
    route: str
    # RỖNG = bản giá chung, áp cho mọi loại tour. Không phải "chưa biết" – xem chú thích ở GuideRate.
    loai_tour: str = ""
    days: float = 0
    rate_per_day: float | None = None
    old_rate_per_day: float | None = None
    effective_from: date
    note: str = ""


@router.post("/guide-rates", status_code=201)
def guide_rate_propose(data: GuideRateIn, u: User = Depends(require_roles("cntt", "hcns", "tp_dh", "tp_hd")), db: Session = Depends(get_db)):
    r = GuideRate(**data.model_dump(), proposed_by=u.username); db.add(r); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_gia_hdv", f"grate:{r.id}", after=data.model_dump(mode="json")); db.commit()
    _ai = " và ".join(ROLES.get(v, v) for v in _CK.can_ky("don_gia_hdv"))
    return {"message": f"Đã trình đơn giá HDV tuyến {r.route} – chờ {_ai} ký"}


@router.post("/guide-rates/{rid}/sign")
def guide_rate_sign(rid: int, u: User = Depends(require_roles(*_CK.can_ky("don_gia_hdv"))), db: Session = Depends(get_db)):
    """ĐỢT LG2: đơn giá HDV đi MỘT chữ ký Chủ tịch (Chủ tịch chốt 11/10/2026). Cửa trình vẫn là
    CNTT / HCNS / TP Điều hành / TP Hướng dẫn, nên không có chuyện người ký tự trình."""
    CK = _CK
    r = db.get(GuideRate, rid)
    if not r or r.status != "pending": raise HTTPException(404, "Không có đề xuất chờ ký")
    can = CK.can_ky("don_gia_hdv")
    da_ky = CK.da_ky_cua(r)
    CK.kiem_tra_nguoi_ky(u, can, nguoi_trinh=r.proposed_by, da_ky=da_ky)
    setattr(r, f"signed_{u.role}", True)
    da_ky[u.role] = "x"
    if CK.du_chu_ky(da_ky, can):
        # Chỉ thay bản cũ CÙNG TUYẾN VÀ CÙNG LOẠI TOUR. Thiếu vế loại tour thì một bản giá mới cho
        # đoàn nước ngoài sẽ hạ luôn bản giá khách lẻ cùng tuyến – hai con số khác nhau bị coi là một.
        for old in db.execute(select(GuideRate).where(GuideRate.route == r.route, GuideRate.loai_tour == r.loai_tour, GuideRate.status == "active", GuideRate.id != r.id)).scalars():
            if old.effective_from <= r.effective_from: old.status = "rejected"; old.note = (old.note + f" | thay bởi #{r.id}")[:200]
        r.status = "active"
    R.audit(db, u.username, u.role, "ky_gia_hdv", f"grate:{r.id}", after={"trang_thai": r.status}); db.commit()
    return {"message": "Đã ký" + (" – đơn giá có hiệu lực" if r.status == "active" else ", chờ chữ ký còn lại")}


@router.get("/vehicle-rates")
def vehicle_rates(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [rate_out(r) for r in db.execute(select(VehicleRate).order_by(VehicleRate.status.desc(), VehicleRate.id)).scalars()]


class RateIn(BaseModel):
    route: str
    days: int = 0
    internal_price: float | None = None
    partner_price: float | None = None
    effective_from: date
    note: str = ""


@router.post("/vehicle-rates", status_code=201)
def rate_propose(data: RateIn, u: User = Depends(require_roles("cntt", "hcns", "tp_dh")), db: Session = Depends(get_db)):
    r = VehicleRate(**data.model_dump(), proposed_by=u.username); db.add(r); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_gia_xe", f"rate:{r.id}", after=data.model_dump(mode="json")); db.commit()
    _ai = " và ".join(ROLES.get(v, v) for v in _CK.can_ky("gia_xe"))
    return {"message": f"Đã trình giá tuyến {r.route} – chờ {_ai} ký"}


@router.post("/vehicle-rates/{rid}/sign")
def rate_sign(rid: int, u: User = Depends(require_roles(*_CK.can_ky("gia_xe"))), db: Session = Depends(get_db)):
    """ĐỢT LG2: giá xe theo tuyến đi MỘT chữ ký Chủ tịch (Chủ tịch chốt 11/10/2026)."""
    CK = _CK
    r = db.get(VehicleRate, rid)
    if not r or r.status != "pending": raise HTTPException(404, "Không có đề xuất chờ ký")
    can = CK.can_ky("gia_xe")
    da_ky = CK.da_ky_cua(r)
    CK.kiem_tra_nguoi_ky(u, can, nguoi_trinh=r.proposed_by, da_ky=da_ky)
    setattr(r, f"signed_{u.role}", True)
    da_ky[u.role] = "x"
    if CK.du_chu_ky(da_ky, can):
        for old in db.execute(select(VehicleRate).where(VehicleRate.route == r.route, VehicleRate.status == "active", VehicleRate.id != r.id)).scalars():
            if old.effective_from <= r.effective_from: old.status = "rejected"; old.note = (old.note + f" | thay bởi #{r.id}")[:200]
        r.status = "active"
    R.audit(db, u.username, u.role, "ky_gia_xe", f"rate:{r.id}", after={"trang_thai": r.status}); db.commit()
    return {"message": "Đã ký" + (" – bảng giá có hiệu lực" if r.status == "active" else ", chờ chữ ký còn lại")}


def _owner(v, cos: dict) -> dict:
    """Xe của một pháp nhân trong phạm vi hợp nhất → lệnh điều xe là giao dịch nội bộ, phải loại trừ khi hợp nhất."""
    c = cos.get(v.company_id) if v is not None and v.company_id else None
    return {"company": c.name if c else "", "company_code": c.code if c else "",
            "noi_bo": bool(c and c.in_group()),
            "canh_bao": "" if c else "Xe chưa gán công ty chủ quản – chưa xác định được đây có phải giao dịch nội bộ hay không"}


@router.get("/dispatch")
def dispatch_list(u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    vobj = {v.id: v for v in db.execute(select(Vehicle)).scalars()}
    veh = {i: v.plate for i, v in vobj.items()}
    cos = {c.id: c for c in db.execute(select(Company)).scalars()}
    out = []
    for d in db.execute(select(DispatchOrder).order_by(desc(DispatchOrder.id))).scalars():
        t = db.get(Tour, d.tour_id)
        rt = db.get(VehicleRate, d.rate_id) if d.rate_id else None
        out.append({"id": d.id, "tour_code": t.code if t else "", "vehicle": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "date_from": d.date_from, "date_to": d.date_to, "route": rt.route if rt else "",
                    "days": (d.date_to - d.date_from).days + 1, "internal_price": (d.internal_price or 0), "status": d.status, "created_by": d.created_by, "confirmed_at": d.confirmed_at, "incident_note": d.incident_note,
                    # DL-1b: cột mới đứng CẠNH `status`, không thay nó. `da_xac_nhan` nghĩa là GIÁM ĐỐC
                    # ĐỘI XE đã chốt lệnh; cột dưới đây là TÀI XẾ đã nhận chưa. Hai câu hỏi khác nhau.
                    "trang_thai_nhan": _NL.trang_thai_nhan(d),
                    "han_nhan": (_NL.han_nhan(d).isoformat() if _NL.han_nhan(d) else None),
                    "nhan_luc": d.nhan_luc, "tu_choi_nhan_ly_do": d.tu_choi_nhan_ly_do,
                    **_owner(vobj.get(d.vehicle_id), cos)})
    return out


class DispatchIn(BaseModel):
    tour_id: int
    vehicle_id: int
    date_from: date
    date_to: date
    rate_id: int | None = None
    internal_price: float | None = None
    # Đợt 4: chọn xe ngoài top gợi ý thì phải ghi lý do TRƯỚC khi lưu. Đây là dữ liệu duy nhất để sau mỗi quý
    # biết thuật toán gợi ý có tốt lên không – không có nó thì chỉ còn tranh luận bằng cảm nhận.
    ly_do_khac_goi_y: str = ""
    km_du_kien: int = 0
    so_khach: int = 0
    # DL-1 (11/10/2026): lệnh này ra từ đề nghị nào. Để rỗng ĐƯỢC — xem chú thích ở cột
    # `DispatchOrder.de_nghi_id` và `de_nghi_xe.lenh_khong_qua_de_nghi()`.
    de_nghi_id: int | None = None


@router.post("/dispatch", status_code=201)
def dispatch_create(data: DispatchIn,
                    u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt", "gd_doi_xe")),
                    db: Session = Depends(get_db)):
    v = db.get(Vehicle, data.vehicle_id); t = db.get(Tour, data.tour_id)
    if not v or not t: raise HTTPException(404, "Không có xe hoặc tour")
    if data.date_to < data.date_from: raise HTTPException(422, "Ngày không hợp lệ")
    rt = db.get(VehicleRate, data.rate_id) if data.rate_id else None
    if rt and rt.status != "active": raise HTTPException(422, "Tuyến trong bảng giá chưa được Chủ tịch + TGĐ duyệt")
    if rt:
        price = rt.partner_price if v.kind == "hop_tac" else rt.internal_price
        if price <= 0: raise HTTPException(422, f"Tuyến {rt.route} không có giá cho loại xe {v.kind}")
    else:
        price = (data.internal_price or 0) or (v.internal_rate_per_day or 0) * ((data.date_to - data.date_from).days + 1)
    if v.kind != "hop_tac" and not v.driver_id: raise HTTPException(422, "Xe chưa gán tài xế")
    driver_id = v.driver_id
    if not driver_id:   # xe hợp tác: tài xế của đối tác – ghi vào hồ sơ xe khi có; tạm gắn người lập lệnh để theo dõi
        drv = db.execute(select(Employee).where(Employee.department == "doi_xe").order_by(Employee.id)).scalars().first()
        if not drv: raise HTTPException(422, "Chưa có hồ sơ tài xế")
        driver_id = drv.id
    # Bộ điều kiện phát lệnh (Đợt 1 đội xe, đặc tả §7). Mức BLOCK chặn thật, không có nút vượt chung; các mức
    # còn lại đi kèm lệnh để người điều hành thấy, và được ghi vào nhật ký cùng lệnh.
    from app.services import fleet as FL
    # Chỉ đạo Chủ tịch 07/9/2026: GĐ điều hành đội xe là người DUY NHẤT được tạo và chốt lệnh điều xe.
    ai, ly_do = FL.nguoi_duoc_lap_lenh(db)
    if ai and u.id not in {x.id for x in ai}:
        ten = ", ".join(f"{x.full_name} ({x.username})" for x in ai)
        raise HTTPException(403, f"Chỉ {ten} được tạo lệnh điều xe (chỉ đạo 07/9/2026). "
                                 "Đổi người phụ trách thì sửa tham số chính sách xe_nguoi_lap_lenh.")
    # Truyền tài xế THẬT của xe, không truyền người thay thế ở trên. Với xe hợp tác do đối tác tự lái, hệ
    # thống đang tạm gắn một nhân sự đội xe chỉ để có chỗ ghi – gọi đó là "tài xế" khi kiểm trùng lịch thì
    # hai xe hợp tác chạy cùng ngày sẽ báo tài xế trùng lịch, trong khi ngoài đời là hai người khác nhau.
    # Bộ kiểm tra vẫn nêu "chưa gán tài xế" ở mức chưa đủ dữ liệu, nên vấn đề không bị giấu đi.
    kt = FL.kiem_tra_dieu_xe(db, v, data.date_from, data.date_to, v.driver_id,
                             chan_khi_thieu_giay=bool(R.get_param(db, "xe_chan_khi_thieu_giay")))
    if kt["muc"] == FL.BLOCK:
        raise HTTPException(422, {"message": "Không đủ điều kiện phát lệnh điều xe",
                                  "vi_pham": [i for i in kt["items"] if i["level"] == FL.BLOCK]})
    # Ghi vết gợi ý điều xe (đặc tả A1): chọn phương án hệ thống đánh giá THẤP HƠN nhóm đề xuất thì phải ghi
    # lý do trước khi lưu.
    #
    # Chữ "thấp hơn" ở đây là có chủ đích, không phải chỉ "nằm ngoài top 3". Với đội xe nhỏ, hoặc khi các xe
    # chưa có số liệu vận hành, điểm của chúng BẰNG NHAU – lúc đó bắt người chốt lệnh giải trình vì sao chọn
    # xe này thay vì xe kia là bắt họ giải thích một khác biệt mà chính hệ thống không nhìn thấy. Kết quả chỉ
    # là một ô lý do điền cho xong, và ít lâu sau là một tính năng bị tắt. Chỉ hỏi khi hệ thống thật sự có ý
    # kiến khác: xe được chọn có điểm THẤP HƠN phương án thấp nhất trong nhóm đề xuất.
    from app.services import fleet_ai as AI
    gy = AI.goi_y_dieu_xe(db, data.date_from, data.date_to, data.so_khach, data.km_du_kien)
    top_ids = [p["vehicle_id"] for p in gy["phuong_an"]]
    pa_chon = next((p for p in gy.get("tat_ca", []) if p["vehicle_id"] == v.id), None)
    diem_chon = pa_chon["diem"] if pa_chon else None
    diem_thap_nhat_trong_top = min((p["diem"] for p in gy["phuong_an"]), default=None)
    kem_hon = (top_ids and v.id not in top_ids and diem_chon is not None
               and diem_thap_nhat_trong_top is not None and diem_chon < diem_thap_nhat_trong_top)
    if kem_hon and not (data.ly_do_khac_goi_y or "").strip():
        raise HTTPException(422, {"message": "Xe được chọn được hệ thống đánh giá thấp hơn nhóm đề xuất – "
                                             "phải ghi lý do trước khi lưu",
                                  "diem_xe_chon": diem_chon,
                                  "diem_thap_nhat_trong_nhom_de_xuat": diem_thap_nhat_trong_top,
                                  # Nói ra hệ thống chê điểm gì, chứ không chỉ đưa hai con số điểm: người
                                  # chốt lệnh cần biết mình đang bác lại nhận xét nào để viết lý do cho đúng.
                                  "he_thong_nhan_xet": pa_chon["ly_do"] if pa_chon else [],
                                  "goi_y": gy["phuong_an"]})
    # DL-1: nếu lệnh đi theo một đề nghị thì đề nghị ấy phải thuộc đúng chuyến này và còn đang chờ.
    # Kiểm TRƯỚC khi tạo lệnh: tạo rồi mới phát hiện đề nghị sai chuyến là đã có một lệnh mồ côi.
    if data.de_nghi_id:
        from app.models.de_nghi_xe import DeNghiXe
        dn = db.get(DeNghiXe, data.de_nghi_id)
        if dn is None:
            raise HTTPException(404, f"Không có đề nghị xe #{data.de_nghi_id}")
        if dn.tour_id != t.id:
            raise HTTPException(422, f"Đề nghị #{dn.id} là của chuyến khác – lệnh và đề nghị phải "
                                     "cùng một chuyến, nếu không thì chuỗi đề nghị → lệnh đứt mà "
                                     "bảng vẫn trông đầy đủ")
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=driver_id, de_nghi_id=data.de_nghi_id, date_from=data.date_from, date_to=data.date_to, rate_id=rt.id if rt else None, internal_price=price, created_by=u.username,
                      phuong_an_ai_goi_y=json.dumps(gy["phuong_an"], ensure_ascii=False, default=str)[:8000],
                      phuong_an_da_chon=v.code or v.plate, ly_do_khac_goi_y=data.ly_do_khac_goi_y.strip())
    db.add(d); db.flush()
    if data.de_nghi_id:
        from app.services import de_nghi_xe as DN
        try:
            DN.danh_dau_da_lap_lenh(db, data.de_nghi_id, d.id)
        except ValueError as ex:
            raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "lenh_dieu_xe", f"tour:{t.code}", after={"xe": v.plate, "tuyen": rt.route if rt else "", "tu": str(data.date_from), "den": str(data.date_to), "gia_noi_bo": price, "kiem_tra": kt["muc"]})
    db.commit()
    canh_bao = [i["msg"] for i in kt["items"]]
    if ly_do: canh_bao.append(ly_do)      # cấu hình người lập lệnh sai thì nói ra, không im lặng bỏ qua
    return {"message": f"Đã lập lệnh điều xe {v.plate} cho {t.code} – Đội xe xác nhận trong 4 giờ",
            "kiem_tra": {"muc": kt["muc"], "muc_ten": kt["muc_ten"], "canh_bao": canh_bao},
            "theo_goi_y": v.id in top_ids, "kem_hon_de_xuat": bool(kem_hon), "goi_y": gy["phuong_an"]}


class DispatchUpdate(BaseModel):
    status: str
    incident_note: str = ""


@router.post("/dispatch/{did}/update")
def dispatch_update(did: int, data: DispatchUpdate,
                    u: User = Depends(require_roles("cntt", "tp_dh", "nv_dh", "hcns", "gd_doi_xe")),
                    db: Session = Depends(get_db)):
    d = db.get(DispatchOrder, did)
    if not d: raise HTTPException(404, "Không có lệnh")
    if data.status not in ("da_xac_nhan", "hoan_thanh", "huy"): raise HTTPException(422, "Trạng thái không hợp lệ")
    if data.status == "da_xac_nhan":
        # "Tạo VÀ CHỐT" – chốt lệnh cũng chỉ một người, nếu không thì siết cửa vào mà bỏ ngỏ cửa ra.
        from app.services import fleet as FL
        ai, _ = FL.nguoi_duoc_lap_lenh(db)
        if ai and u.id not in {x.id for x in ai}:
            ten = ", ".join(f"{x.full_name} ({x.username})" for x in ai)
            raise HTTPException(403, f"Chỉ {ten} được chốt lệnh điều xe (chỉ đạo 07/9/2026)")
    if data.status == "da_xac_nhan": d.confirmed_at = datetime.now()
    cu = d.status
    d.status = data.status; d.incident_note = data.incident_note or d.incident_note
    # LUẬT 3 (Chủ tịch chốt 12/10/2026): lệnh ĐỔI NỘI DUNG thì dấu nhận của tài xế hết hiệu
    # lực. Huỷ và hoàn thành KHÔNG xoá dấu: một lệnh đã chạy xong mà xoá mất dấu "tài xế đã
    # nhận" là xoá một dữ kiện có thật của quá khứ.
    da_xoa = False
    if data.status == "da_xac_nhan" and cu != "da_xac_nhan":
        da_xoa = _NL.xoa_dau_nhan(db, d, "lệnh được chốt lại", u.username)
    R.audit(db, u.username, u.role, "cap_nhat_lenh_dieu_xe", f"dispatch:{d.id}", after=data.model_dump(mode="json")); db.commit()
    # Nói RA việc đã xoá dấu nhận. Xoá âm thầm là bắt tài xế bấm lại mà không ai báo, còn
    # người sửa lệnh thì tưởng chuyến ấy vẫn có người đã nhận.
    return {"message": ("Đã cập nhật lệnh điều xe. Dấu nhận của tài xế đã được xoá – lệnh "
                        "cần tài xế nhận lại." if da_xoa else "Đã cập nhật lệnh điều xe")}


# ══════════════════ DL-1b · TÀI XẾ NHẬN LỆNH (Chủ tịch đặc tả 11/10, chốt luật 12/10/2026)
#
# BA CỬA HẸP, KHÔNG MỞ CẢ CỤM `/dispatch` CHO TÀI XẾ. Phạm vi vai `tai_xe` đo trên main hôm nay chỉ
# có `/incidents`, `/payment-requests`, `/fleet/bao-hong`, `/leaves`, `/leave-balance` — không có
# `/dispatch`. Mở cả tiền tố ấy là cho tài xế đọc GIÁ THUÊ NỘI BỘ của mọi lệnh trong công ty, tức
# nới hàng rào rộng hơn nhiều lần việc cần làm — đúng lý lẽ đã ghi cho `/fleet/de-lap-lenh`.
#
# Nên ba cửa dưới đây đứng trên tiền tố RIÊNG `/nhan-lenh`, và mỗi cửa chỉ chạm ĐÚNG một lệnh.
_NHAN = FULL_VIEW + ("tai_xe", "cntt")
_XEM_NHAN = FULL_VIEW + ("gd_doi_xe", "tp_dh", "nv_dh", "cntt")


class LyDoNhanIn(BaseModel):
    ly_do: str


def _lenh_cua_toi(db: Session, u: User, did: int):
    """Lấy lệnh và chặn người lạ.

    Vai nền (Chủ tịch, TGĐ) và CNTT bấm hộ được — có thật: tài xế mất điện thoại giữa chuyến thì
    vẫn phải có đường ghi nhận. Nhưng `nhan_boi` ghi ĐÚNG người bấm, nên bấm hộ không biến thành
    một dấu nhận không ai chịu trách nhiệm.
    """
    from app.services import nhan_lenh as NL
    d = db.get(DispatchOrder, did)
    if d is None:
        raise HTTPException(404, "Không có lệnh điều xe này")
    if u.role == "tai_xe" and not NL._la_tai_xe_cua_lenh(db, u, d):
        raise HTTPException(403, "Lệnh này không phải của anh – chỉ tài xế ghi trên lệnh mới nhận được")
    return d


@router.post("/nhan-lenh/{did}/nhan")
def nhan_lenh(did: int, u: User = Depends(require_roles(*_NHAN)), db: Session = Depends(get_db)):
    from app.services import nhan_lenh as NL
    d = _lenh_cua_toi(db, u, did)
    try:
        NL.nhan(db, u, d.id)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"message": "Đã ghi nhận. Giám đốc đội xe thấy lệnh này đã có người nhận."}


@router.post("/nhan-lenh/{did}/tu-choi")
def tu_choi_nhan_lenh(did: int, data: LyDoNhanIn, u: User = Depends(require_roles(*_NHAN)),
                      db: Session = Depends(get_db)):
    from app.services import nhan_lenh as NL
    d = _lenh_cua_toi(db, u, did)
    try:
        NL.tu_choi(db, u, d.id, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    # Nói rõ lệnh VẪN CÒN HIỆU LỰC. Không nói thì tài xế tưởng mình vừa huỷ xong chuyến, và sáng
    # hôm sau không ra bến.
    return {"message": ("Đã gửi lý do cho Giám đốc đội xe. Lệnh VẪN CÒN HIỆU LỰC cho tới khi ông "
                        "quyết – anh đừng tự bỏ chuyến.")}


@router.get("/nhan-lenh/can-biet")
def nhan_lenh_can_biet(u: User = Depends(require_roles(*_XEM_NHAN)), db: Session = Depends(get_db)):
    """Lệnh quá hạn chưa nhận và lệnh tài xế đã báo không nhận được — cho Giám đốc đội xe."""
    from app.services import nhan_lenh as NL
    return NL.can_giam_doc_xe_biet(db)


@router.get("/fleet/summary")
def fleet_summary(period: str, u: User = Depends(require_roles(*HR_READ, "nv_dh")), db: Session = Depends(get_db)):
    """Trung tâm lợi nhuận Đội xe: doanh thu nội bộ và số ngày tour tài xế trong tháng (CNTT quyết toán)."""
    y, m = map(int, period.split("-"))
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    veh = {v.id: v.plate for v in db.execute(select(Vehicle)).scalars()}
    rows = {}
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.status.in_(["da_xac_nhan", "hoan_thanh"]))).scalars():
        if d.date_to.year == y and d.date_to.month == m:
            r = rows.setdefault(d.vehicle_id, {"vehicle": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "trips": 0, "days": 0, "revenue": 0.0})
            r["trips"] += 1; r["days"] += (d.date_to - d.date_from).days + 1; r["revenue"] += (d.internal_price or 0)
    ctp = R.get_param(db, "tai_xe_cong_tac_phi")
    for r in rows.values(): r["driver_allowance"] = r["days"] * ctp
    return {"period": period, "rows": list(rows.values()), "total_revenue": sum((r["revenue"] or 0) for r in rows.values())}


# ---------- Sự vụ ----------
@router.get("/incident-levels")
def incident_levels(u: User = Depends(current_user)):
    return {"levels": INCIDENT_LEVELS, "status": INCIDENT_STATUS, "quy_trinh": "Trưởng bộ phận lập biên bản → HCNS xác nhận (≥ mức 2) → duyệt (mức 2: GĐ KD/PTGĐ; mức 3: Chủ tịch + TGĐ) → 3 ngày làm việc khiếu nại (treo chế tài) → hiệu lực"}


def inc_out(i: Incident, emps: dict, my_emp_ids: set | None = None) -> dict:
    return {"id": i.id, "is_mine": bool(my_emp_ids and i.employee_id in my_emp_ids), "employee_id": i.employee_id, "employee": emps.get(i.employee_id, ""), "tour_id": i.tour_id, "level": i.level, "level_name": INCIDENT_LEVELS.get(i.level, {}).get("ten", f"Mức {i.level}"),
            "description": i.description, "occurred_on": i.occurred_on, "confirmed_by": i.confirmed_by, "created_by": i.created_by, "status": i.status, "status_name": INCIDENT_STATUS.get(i.status, i.status),
            "approved_by": i.approved_by, "approved_at": i.approved_at, "employee_opinion": i.employee_opinion, "appeal_note": i.appeal_note, "appeal_result": i.appeal_result, "effective_at": i.effective_at,
            "appeal_deadline": (H.add_working_days(i.approved_at.date(), 3) if i.approved_at else None)}


@router.get("/incidents")
# Trước 05/10/2026 "hdv" chỉ là mã CHỨC DANH (POSITIONS) và KHÔNG có vai trò nào tên như vậy, nên dòng
# này từng viết "hdv" vào chỗ chờ mã VAI TRÒ: hướng dẫn viên (khi ấy mang vai `xe_hdv`) không xem được
# sự vụ của chính mình, còn nhánh lọc bên dưới thì không bao giờ chạy tới. Kiểu lỗi im lặng: không báo
# gì, chỉ là một cánh cửa khóa. Từ 05/10/2026 hai bảng dùng CHUNG mã `hdv` và `tai_xe`, nên viết nhầm
# bảng này sang bảng kia không còn sinh ra cánh cửa khóa im lặng nữa.
def incidents(u: User = Depends(require_roles(*HR_READ, "nv_kd", "nv_dh", "tai_xe", "hdv", "tp_hd")),
              db: Session = Depends(get_db)):
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    rows = db.execute(select(Incident).order_by(desc(Incident.id))).scalars().all()
    mine = {e.id for e in db.execute(select(Employee).where(Employee.user_id == u.id)).scalars()}
    if u.role in ("nv_kd", "nv_dh", "tai_xe", "hdv"):   # nhân viên chỉ xem sự vụ của mình
        rows = [i for i in rows if i.employee_id in mine]
    return [inc_out(i, emps, mine) for i in rows]


class IncidentIn(BaseModel):
    employee_id: int
    level: int
    description: str
    occurred_on: date
    tour_id: int | None = None


@router.post("/incidents", status_code=201)
def incident_create(data: IncidentIn, u: User = Depends(require_roles("hcns", "tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "tgd", "cntt", "tp")), db: Session = Depends(get_db)):
    """Trưởng bộ phận nơi phát sinh lập biên bản (TP KD với tour lẻ, PTGĐ đoàn với Phòng Đoàn, TP ĐH với Điều hành, phụ trách Phòng HD với HDV)."""
    if data.level not in INCIDENT_LEVELS: raise HTTPException(422, "Mức sự vụ 1–3 theo bảng phân mức")
    i = Incident(**data.model_dump(), created_by=u.username)
    if data.level == 1: i.status, i.effective_at = "hieu_luc", datetime.now()     # mức 1: nhắc nhở, ghi hồ sơ – không chế tài
    elif u.role == "hcns": i.confirmed_by, i.status = u.username, "hcns_xac_nhan"
    db.add(i); db.flush()
    R.audit(db, u.username, u.role, "lap_bien_ban_su_vu", f"incident:{i.id}", after=data.model_dump(mode="json")); db.commit()
    return {"message": "Đã lập biên bản sự vụ" + ("" if i.status != "lap" else " – chờ HCNS xác nhận")}


@router.post("/incidents/{iid}/confirm")
def incident_confirm(iid: int, u: User = Depends(require_roles("hcns")), db: Session = Depends(get_db)):
    i = db.get(Incident, iid)
    if not i or i.status != "lap": raise HTTPException(404, "Không có sự vụ chờ HCNS xác nhận")
    i.confirmed_by, i.status = u.username, "hcns_xac_nhan"
    R.audit(db, u.username, u.role, "hcns_xac_nhan_su_vu", f"incident:{i.id}"); db.commit()
    return {"message": "HCNS đã xác nhận – chờ cấp có thẩm quyền duyệt"}


@router.post("/incidents/{iid}/approve")
def incident_approve(iid: int, u: User = Depends(require_roles("gd_kd", "ptgd_doan", "tgd", "chutich")), db: Session = Depends(get_db)):
    i = db.get(Incident, iid)
    if not i or i.status != "hcns_xac_nhan": raise HTTPException(404, "Sự vụ chưa được HCNS xác nhận hoặc đã duyệt")
    from app.services import chu_ky as CK
    allowed = INCIDENT_LEVELS[i.level]["duyet"]
    signers = [x for x in i.approved_by.split(",") if x]
    da_ky = {}
    for x in signers:
        usr = db.execute(select(User).where(User.username == x)).scalars().first()
        if usr: da_ky[usr.role] = usr.username
    # Mức 3 cần đủ chữ ký Chủ tịch + TGĐ; người lập biên bản không được nằm trong tập người ký.
    CK.kiem_tra_nguoi_ky(u, tuple(allowed), nguoi_trinh=i.created_by, da_ky=da_ky)
    signers.append(u.username); da_ky[u.role] = u.username
    i.approved_by = ",".join(signers)
    can = ("chutich", "tgd") if i.level >= 3 else tuple(allowed)
    du = CK.du_chu_ky(da_ky, can) if i.level >= 3 else True
    if du:
        i.status, i.approved_at = "cho_khieu_nai", datetime.now()
    R.audit(db, u.username, u.role, "duyet_su_vu", f"incident:{i.id}", after={"trang_thai": i.status}); db.commit()
    return {"message": "Đã duyệt – người bị lập biên bản có 3 ngày làm việc để khiếu nại" if i.status == "cho_khieu_nai"
            else "Đã ký, còn chờ chữ ký của " + ", ".join(CK.con_thieu(da_ky, ("chutich", "tgd")))}


class OpinionIn(BaseModel):
    opinion: str = ""
    appeal: str = ""


@router.post("/incidents/{iid}/opinion")
def incident_opinion(iid: int, data: OpinionIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Người bị lập biên bản ghi ý kiến; khiếu nại trong 3 ngày làm việc kể từ khi duyệt → treo chế tài."""
    i = db.get(Incident, iid)
    if not i: raise HTTPException(404, "Không có sự vụ")
    e = db.get(Employee, i.employee_id)
    if not e or e.user_id != u.id: raise HTTPException(403, "Chỉ người bị lập biên bản được ghi ý kiến")
    if data.opinion: i.employee_opinion = data.opinion[:300]
    if data.appeal:
        if i.status not in ("lap", "hcns_xac_nhan", "cho_khieu_nai"): raise HTTPException(422, "Đã hết thời hạn khiếu nại hoặc sự vụ đã kết thúc")
        if i.status == "cho_khieu_nai" and i.approved_at and date.today() > H.add_working_days(i.approved_at.date(), 3): raise HTTPException(422, "Quá 3 ngày làm việc kể từ khi duyệt")
        i.appeal_note = data.appeal[:300]
        if i.status == "cho_khieu_nai": i.status = "khieu_nai"
    R.audit(db, u.username, u.role, "y_kien_su_vu", f"incident:{i.id}", after=data.model_dump()); db.commit()
    return {"message": "Đã ghi nhận" + (" – chế tài treo cho tới khi cấp trên kết luận" if i.status == "khieu_nai" else "")}


class ResolveIn(BaseModel):
    accept: bool          # true = chấp nhận khiếu nại (hủy chế tài)
    result: str = ""


@router.post("/incidents/{iid}/resolve")
def incident_resolve(iid: int, data: ResolveIn, u: User = Depends(require_roles("gd_kd", "ptgd_doan", "tgd", "chutich")), db: Session = Depends(get_db)):
    """Cấp trên một bậc kết luận khiếu nại; hoặc chốt hiệu lực khi hết hạn khiếu nại."""
    i = db.get(Incident, iid)
    if not i or i.status not in ("khieu_nai", "cho_khieu_nai"): raise HTTPException(404, "Sự vụ không ở trạng thái chờ kết luận")
    if i.status == "cho_khieu_nai" and data.accept: raise HTTPException(422, "Không có khiếu nại để chấp nhận")
    i.appeal_result = data.result[:300]
    if data.accept: i.status = "huy"
    else: i.status, i.effective_at = "hieu_luc", datetime.now()
    R.audit(db, u.username, u.role, "ket_luan_su_vu", f"incident:{i.id}", after={"chap_nhan": data.accept, "ket_luan": data.result}); db.commit()
    return {"message": "Khiếu nại được chấp nhận – hủy chế tài" if data.accept else "Sự vụ có hiệu lực – chế tài áp dụng kỳ lương tháng phát sinh"}


@router.post("/robot/incidents/finalize")
def robot_incidents_finalize(x_robot_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    from app.core.config import settings
    if not settings.ROBOT_TOKEN or x_robot_token != settings.ROBOT_TOKEN: raise HTTPException(401, "Sai robot token")
    n = 0
    for i in db.execute(select(Incident).where(Incident.status == "cho_khieu_nai")).scalars():
        if i.approved_at and date.today() > H.add_working_days(i.approved_at.date(), 3): i.status, i.effective_at = "hieu_luc", datetime.now(); n += 1
    R.audit(db, "robot", "robot", "chot_su_vu_het_han_khieu_nai", "incidents", after={"so_luong": n}); db.commit()
    return {"count": n}


@router.post("/incidents/finalize-expired")
def incidents_finalize(u: User = Depends(require_roles("hcns", "cntt")), db: Session = Depends(get_db)):
    """Robot/HCNS: sự vụ đã duyệt, quá 3 ngày làm việc không khiếu nại → hiệu lực."""
    n = 0
    for i in db.execute(select(Incident).where(Incident.status == "cho_khieu_nai")).scalars():
        if i.approved_at and date.today() > H.add_working_days(i.approved_at.date(), 3):
            i.status, i.effective_at = "hieu_luc", datetime.now(); n += 1
    R.audit(db, u.username, u.role, "chot_su_vu_het_han_khieu_nai", "incidents", after={"so_luong": n}); db.commit()
    return {"message": f"Đã chốt hiệu lực {n} sự vụ", "count": n}


# ---------- Bảng lương ----------
def run_out(r: PayrollRun) -> dict:
    return {"id": r.id, "period": r.period, "status": r.status, "rows": r.rows, "totals": r.totals, "inputs": r.inputs or {},
            "kt_confirmed_by": r.kt_confirmed_by, "kt_confirmed_at": r.kt_confirmed_at,
            "hcns_by": r.hcns_by, "hcns_at": r.hcns_at, "tgd_by": r.tgd_by, "tgd_at": r.tgd_at, "entry_ids": r.entry_ids, "updated_at": r.updated_at}


@router.get("/payroll-runs/{period}")
def payroll_run(period: str, refresh: bool = False, u: User = Depends(bang_luong), db: Session = Depends(get_db)):
    try:
        return run_out(H.get_or_draft(db, period, refresh=refresh))
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class ChamCongIn(BaseModel):
    cong_chuan: float | None = None
    cong_thuc_te: dict[str, float] = {}      # mã NV → công thực tế


@router.put("/payroll-runs/{period}/cham-cong")
def payroll_attendance(period: str, data: ChamCongIn, u: User = Depends(require_roles("hcns", "cntt")), db: Session = Depends(get_db)):
    """Công thực tế của Kế toán và Nhân sự Hành chính – hai bộ phận duy nhất còn chấm công theo ngày.

    Năm phòng còn lại đã chuyển sang căn cứ báo cáo công việc trước 20 giờ (Điều 12), nên KHÔNG nhận
    và cũng không cảnh báo thiếu công cho họ."""
    run = H.get_or_draft(db, period)
    if run.status != "nhap": raise HTTPException(422, "Bảng lương đã qua bước xác nhận – sửa công phải qua điều chỉnh")
    from app.services import luong as L
    emps = {e.code: e for e in db.execute(select(Employee).where(Employee.active == True)).scalars()}
    sai = [ma for ma in data.cong_thuc_te if ma not in emps or L.che_do_cong(emps[ma]) != L.CHAM_CONG]
    if sai: raise HTTPException(422, f"Những mã này không thuộc chế độ chấm công theo ngày: {', '.join(sorted(sai))}")
    cur = dict(run.inputs or {})
    if data.cong_chuan is not None: cur["cong_chuan"] = data.cong_chuan
    cur["cong_thuc_te"] = {**(cur.get("cong_thuc_te") or {}), **data.cong_thuc_te}
    run.inputs = cur
    R.audit(db, u.username, u.role, "nhap_cong_bang_luong", f"payroll:{period}", after={"so_nguoi": len(data.cong_thuc_te)})
    db.commit()
    run = H.get_or_draft(db, period, refresh=True)
    return {"message": f"Đã nhập công cho {len(data.cong_thuc_te)} người kỳ {period}", "run": run_out(run)}


@router.get("/phieu-luong/khoan-treo")
def khoan_treo_cua_toi(u: User = Depends(loc_theo_nguoi_dung("khoản lương treo của chính người đăng nhập")),
                       db: Session = Depends(get_db)):
    """Cùng dữ liệu khoản treo, dưới tiền tố cá nhân /api/v1/phieu-luong.

    Vì sao phải có: đường dẫn cũ nằm dưới /api/v1/payroll, tiền tố chỉ được khai sau màn hình /hr. Người
    lao động bình thường không có /hr nên hàng rào phạm vi NGOÀI chặn họ ở 403, dù thân hàm đã tự lọc
    đúng về phần của họ – quyền có, lọc có, chỉ thiếu đường vào. Khoản treo là hoa hồng và thưởng chuyến
    chưa phát sinh vì chuyến chưa chốt quyết toán; nó không hiện trên phiếu lương nào, nên người không
    xem được nó là người không có cách nào biết mình đang bị treo bao nhiêu.
    """
    return khoan_treo(u, db)


@router.get("/payroll/khoan-treo")
def khoan_treo(u: User = Depends(loc_theo_nguoi_dung("khoản lương treo – ai không xem được bảng lương thì chỉ thấy phần của chính mình")),
               db: Session = Depends(get_db)):
    """Hoa hồng và thưởng chuyến đang treo vì chuyến chưa chốt quyết toán.

    Người lao động xem được phần của chính mình: đây là chỗ dễ mất tiền nhất mà không ai phát hiện, vì
    khoản treo không hiện trên phiếu lương nào."""
    from app.services import luong as L
    kq = L.khoan_treo(db)
    from app.services import access as AC
    if "payroll" not in AC.hr_tabs_for(db, u) and u.role not in ("gd_kd", "tp_kd", "tp_dh", "ptgd_doan"):
        e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
        ma = e.code if e else "\u0000"
        kq["rows"] = [r for r in kq["rows"] if r["ma"] == ma]
        kq["theo_nguoi"] = [r for r in kq["theo_nguoi"] if r["ma"] == ma]
        kq["chi_cua_toi"] = True
    return kq


@router.get("/payroll/xung-dot-ho-so")
def payroll_conflicts(u: User = Depends(bang_luong), db: Session = Depends(get_db)):
    """Xung đột hồ sơ chặn chạy kỳ lương: một mã dùng cho hai người, một tài khoản gắn hai hồ sơ."""
    from app.services import luong as L
    ds = L.xung_dot_ho_so(db)
    return {"rows": ds, "so_luong": len(ds),
            "ghi_chu": "Còn xung đột thì kỳ lương không chạy được – hệ thống không tự chọn hồ sơ nào." if ds else "Không còn xung đột."}


@router.delete("/payroll-runs/{period}")
def payroll_delete(period: str, u: User = Depends(require_roles("cntt", "chutich")), db: Session = Depends(get_db)):
    """Xóa bảng lương – chặn trong thời hạn lưu trữ tối thiểu."""
    from app.services import luong as L
    ok, vi_sao = L.duoc_xoa_bang_luong(period)
    if not ok: raise HTTPException(422, vi_sao)
    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    if run is None: raise HTTPException(404, "Không có bảng lương kỳ này")
    R.audit(db, u.username, u.role, "xoa_bang_luong", f"payroll:{period}", before={"tong": run.totals})
    db.delete(run); db.commit()
    return {"message": f"Đã xóa bảng lương {period}"}


class BhxhRow(BaseModel):
    ma: str = ""
    ten: str = ""
    muc: float


class BhxhBatch(BaseModel):
    rows: list[BhxhRow]
    ky: str = ""            # 2026-08 – chỉ để ghi nhật ký, mức áp dụng từ kỳ nạp trở đi


@router.post("/bhxh/nap")
def nap_muc_bhxh(data: BhxhBatch, u: User = Depends(require_roles("hcns", "ketoan", "cntt", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nạp tiền lương làm căn cứ đóng BHXH bắt buộc từ danh sách đóng BHXH của kỳ.

    Ghép theo mã nhân viên trước, không có mã thì theo họ tên không dấu. Người không ghép được KHÔNG bị bỏ
    qua im lặng mà trả về để HCNS xử lý – bỏ sót một người là kỳ lương đó không trừ bảo hiểm của họ.
    """
    from app.services.staff import name_key
    emps = list(db.execute(select(Employee).where(Employee.active == True)).scalars())
    by_code = {e.code: e for e in emps}
    by_name: dict[str, list[Employee]] = {}
    for e in emps: by_name.setdefault(name_key(e.full_name), []).append(e)
    da_nap, khong_ghep, trung_ten = 0, [], []
    for r in data.rows:
        e = by_code.get(r.ma.strip()) if r.ma.strip() else None
        if e is None and r.ten.strip():
            nhom = by_name.get(name_key(r.ten), [])
            if len(nhom) == 1: e = nhom[0]
            elif len(nhom) > 1: trung_ten.append(f"{r.ten} ({', '.join(x.code for x in nhom)})"); continue
        if e is None:
            khong_ghep.append(f"{r.ma} {r.ten}".strip()); continue
        e.bhxh_base = float(r.muc); da_nap += 1
    R.audit(db, u.username, u.role, "nap_muc_dong_bhxh", f"bhxh:{data.ky or 'khong_ghi_ky'}",
            after={"da_nap": da_nap, "khong_ghep": len(khong_ghep), "trung_ten": len(trung_ten)})
    db.commit()
    con_thieu = [f"{e.code} {e.full_name}" for e in emps if e.contract_type == "hdld" and not e.bhxh_base]
    return {"da_nap": da_nap, "khong_ghep_duoc": khong_ghep, "trung_ten_can_chi_dinh_ma": trung_ten,
            "hdld_chua_co_muc_dong": con_thieu,
            "message": f"Đã nạp mức đóng BHXH cho {da_nap} người" +
                       (f"; {len(khong_ghep)} dòng chưa ghép được" if khong_ghep else "") +
                       (f"; còn {len(con_thieu)} người HĐLĐ chưa có mức đóng" if con_thieu else "")}


class DoanVienBatch(BaseModel):
    ho_ten: list[str]
    thay_the: bool = True    # True: danh sách này là toàn bộ đoàn viên hiện tại


@router.post("/doan-vien/nap")
def nap_doan_vien(data: DoanVienBatch, u: User = Depends(require_roles("hcns", "ketoan", "cntt", "chutich", "tgd")), db: Session = Depends(get_db)):
    """Nạp danh sách đoàn viên đã ký thỏa thuận khấu trừ đoàn phí.

    Chỉ nhận HỌ TÊN. Bản thỏa thuận có số căn cước và số điện thoại nhưng phân hệ lương không cần tới, nên
    không đưa vào hệ thống: dữ liệu không cần thì không lưu.
    """
    from app.services.staff import name_key
    emps = list(db.execute(select(Employee).where(Employee.active == True)).scalars())
    by_name: dict[str, list[Employee]] = {}
    for e in emps: by_name.setdefault(name_key(e.full_name), []).append(e)
    danh_sach, khong_ghep, trung_ten = set(), [], []
    for ten in data.ho_ten:
        nhom = by_name.get(name_key(ten), [])
        if len(nhom) == 1: danh_sach.add(nhom[0].id)
        elif len(nhom) > 1: trung_ten.append(f"{ten} ({', '.join(x.code for x in nhom)})")
        else: khong_ghep.append(ten)
    n_bat, n_tat = 0, 0
    for e in emps:
        if e.id in danh_sach and not e.member_org: e.member_org = True; n_bat += 1
        elif data.thay_the and e.id not in danh_sach and e.member_org: e.member_org = False; n_tat += 1
    R.audit(db, u.username, u.role, "nap_danh_sach_doan_vien", "doan_phi",
            after={"doan_vien": len(danh_sach), "bat_them": n_bat, "go": n_tat, "khong_ghep": len(khong_ghep)})
    db.commit()
    return {"doan_vien": len(danh_sach), "bat_them": n_bat, "go_khoi_danh_sach": n_tat,
            "khong_ghep_duoc": khong_ghep, "trung_ten_can_chi_dinh_ma": trung_ten,
            "message": f"Đã ghi nhận {len(danh_sach)} đoàn viên" + (f"; {len(khong_ghep)} tên chưa ghép được" if khong_ghep else "")}


@router.get("/phieu-luong/ky-cua-toi")
def ky_luong_cua_toi(u: User = Depends(loc_theo_nguoi_dung("danh sách kỳ lương của chính người đăng nhập")),
                     db: Session = Depends(get_db)):
    """Những kỳ lương CÓ dòng của chính người đăng nhập – để họ mở được phiếu của mình.

    Vì sao phải có endpoint này chứ không để giao diện tự đoán tháng: người lao động không biết kỳ nào
    đã lập. Bắt họ gõ thử từng tháng rồi đọc lỗi "chưa có bảng lương kỳ 2026-06" là cách chắc chắn để
    không ai mở phiếu lương của mình lần thứ hai.

    Chỉ trả về kỳ ĐÃ QUA bản nháp – bản nháp là số robot tính chưa ai xác nhận, đưa cho người lao động
    xem là tạo ra một con số họ nhớ mà công ty không đứng sau. Người xem được bảng lương toàn công ty
    thì thấy cả bản nháp, vì đó chính là việc của họ.
    """
    from app.services import access as AC
    quan_tri = "payroll" in AC.hr_tabs_for(db, u)
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if not e and u.staff_code:
        e = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()
    ma = e.code if e else ""
    if not ma:
        return {"ma_nv": "", "co_ho_so": False, "rows": [],
                "message": "Tài khoản chưa gắn hồ sơ nhân sự nên chưa có phiếu lương. Báo HCNS ghép mã "
                           "nhân viên vào tài khoản – không tự sửa được ở màn hình này."}
    ra = []
    for run in db.execute(select(PayrollRun).order_by(PayrollRun.period.desc())).scalars():
        if run.status == "nhap" and not quan_tri: continue
        dong = next((r for r in (run.rows or []) if r.get("ma") == ma), None)
        if dong is None: continue
        ra.append({"period": run.period, "trang_thai": run.status, "da_ky": bool(run.tgd_by),
                   "thuc_nhan": dong.get("thuc_nhan", 0)})
    return {"ma_nv": ma, "co_ho_so": True, "ho_ten": e.full_name, "rows": ra,
            "message": "" if ra else "Chưa có kỳ lương nào đã lập cho mã nhân viên này."}


@router.get("/phieu-luong/{period}")
def phieu_luong_cua_toi(period: str, ma: str = "",
                        u: User = Depends(loc_theo_nguoi_dung("phiếu lương của chính người đăng nhập")),
                        db: Session = Depends(get_db)):
    """Cùng một phiếu lương, nhưng đứng dưới tiền tố RIÊNG /api/v1/phieu-luong.

    Vì sao phải có đường dẫn thứ hai cho cùng một dữ liệu: hàng rào phạm vi ngoài chỉ phân biệt tới mức
    tiền tố. Tiền tố /api/v1/payroll-runs chứa cả bảng lương TOÀN CÔNG TY, nên mở nó cho mọi vai trò –
    để tài xế xem được phiếu của mình – là hạ hàng rào ngoài của cả bảng lương công ty, chỉ còn hàng rào
    trong đỡ. Tiền tố này chỉ chứa endpoint tự lọc về đúng người, nên mở cho mọi người là an toàn ở CẢ
    HAI lớp. Đường dẫn cũ giữ nguyên cho màn hình Nhân sự của HCNS/Kế toán.
    """
    return _phieu_luong(period, ma, u, db)


@router.get("/payroll-runs/{period}/phieu-luong")
def phieu_luong(period: str, ma: str = "",
                u: User = Depends(loc_theo_nguoi_dung("phiếu lương – phiếu của chính mình ai cũng xem được, phiếu người khác thì phải xem được bảng lương")),
                db: Session = Depends(get_db)):
    return _phieu_luong(period, ma, u, db)


def _phieu_luong(period: str, ma: str, u: User, db: Session):
    """Phiếu lương của CHÍNH người đăng nhập (hoặc của một mã NV, với Kế toán / HCNS / lãnh đạo).

    Người lao động phải tự xem được lương của mình. Phiếu ghi đủ ba khối theo bộ tính lương: thu nhập,
    khoản trừ, phải trả – kèm căn cứ xác định mức lương của kỳ và các khoản đang TREO của chính người đó.
    Khoản treo không nằm trong phiếu lương nào là chỗ dễ mất tiền nhất mà không ai phát hiện, nên phiếu
    lương ở đây hiển thị luôn phần treo bên cạnh phần được trả.
    """
    from app.services import luong as L
    from app.services import access as AC
    quan_tri = "payroll" in AC.hr_tabs_for(db, u)      # xem phiếu lương của NGƯỜI KHÁC; phiếu của chính mình luôn xem được
    e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
    if not e and u.staff_code:
        e = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()
    ma_can = (ma or "").strip() or (e.code if e else "")
    if not ma_can: raise HTTPException(404, "Tài khoản chưa gắn hồ sơ nhân sự – báo HCNS ghép mã nhân viên")
    if ma and not quan_tri and (not e or ma != e.code):
        raise HTTPException(403, "Chỉ xem được phiếu lương của chính mình")

    run = db.execute(select(PayrollRun).where(PayrollRun.period == period)).scalars().first()
    if run is None: raise HTTPException(404, f"Chưa có bảng lương kỳ {period}")
    if run.status == "nhap" and not quan_tri:
        raise HTTPException(422, "Bảng lương kỳ này còn là bản nháp của robot – chờ Kế toán xác nhận cơ sở tính")
    row = next((r for r in run.rows if r["ma"] == ma_can), None)
    if row is None: raise HTTPException(404, f"Không có dòng lương của mã {ma_can} trong kỳ {period}")

    emp = db.execute(select(Employee).where(Employee.code == ma_can)).scalars().first()
    cty = db.get(Company, emp.company_id) if emp and emp.company_id else None
    treo = [x for x in L.khoan_treo(db)["rows"] if x["ma"] == ma_can]
    return {"period": period, "trang_thai_bang_luong": run.status, "da_ky": bool(run.tgd_by),
            "nhan_su": {"ma": ma_can, "ten": row["ten"], "phong": DEPARTMENTS.get(row["phong"], row["phong"]),
                        "chuc_vu": row.get("chuc_vu"), "hop_dong": row["hop_dong"],
                        "phap_nhan_tra_luong": cty.name if cty else "", "che_do_cong": row.get("che_do_cong_ten")},
            "xac_dinh_luong": row.get("xac_dinh_luong"), "muc_dong_bhxh": row.get("bhxh_base", 0),
            "thu_nhap": {"luong_co_ban_ky": row["luong_cb"],
                         "cac_khoan": [k for k in row["khoan"] if k["tien"] > 0],
                         "tong": row.get("thu_nhap", row["luong_cb"] + row["bien_doi"])},
            "khoan_tru": {"che_tai_su_vu": row.get("tru_su_vu", 0), "chi_tiet_che_tai": [k for k in row["khoan"] if k["tien"] < 0],
                          "bhxh_nguoi_lao_dong": row.get("bhxh", 0), "doan_phi_cong_doan": row.get("doan_phi", 0),
                          "tncn_khau_tru": row.get("tncn", 0), "tong": row.get("khoan_tru", 0)},
            "thuc_nhan": row["thuc_nhan"], "ghi_chu": row.get("ghi_chu", ""),
            "khoan_dang_treo": treo,
            "luu_y": ("Khoản treo là hoa hồng và thưởng chuyến CHƯA phát sinh vì chuyến chưa chốt quyết toán. "
                      "Đây là cơ chế hoãn, không phải cắt: chốt quyết toán xong thì kỳ lương tương ứng trả đủ.")
            if treo else ""}


@router.get("/payroll-runs/{period}/theo-phap-nhan")
def payroll_by_company(period: str, u: User = Depends(bang_luong), db: Session = Depends(get_db)):
    """Bảng lương chia theo pháp nhân trả lương – đối chiếu trước khi TGĐ ký lô và ghi sổ."""
    run = H.get_or_draft(db, period)
    return {"period": period, "rows": H.but_toan_theo_phap_nhan(db, run),
            "ghi_chu": "Mỗi pháp nhân là một bộ chứng từ lương riêng. Người chưa xác định pháp nhân được tách "
                       "thành một dòng riêng, không dồn vào công ty mẹ."}


@router.post("/payroll-runs/{period}/kiem-co-so")
def payroll_kiem_co_so(period: str, u: User = Depends(require_roles("hcns", "cntt")), db: Session = Depends(get_db)):
    """Chạy bộ kiểm cơ sở của kỳ. Máy quyết đạt hay không, người chỉ bấm cho nó chạy.

    Chủ tịch gọi bước này là "AI kiểm tra cơ sở" (07/10/2026). Mã thực hiện bằng QUY TẮC XÁC ĐỊNH:
    cùng đầu vào luôn ra cùng danh sách cờ, chạy lại được, từng dòng mở ra xem được bằng chứng. Mô
    hình ngôn ngữ có thể diễn giải một cờ cho dễ hiểu, nhưng không được là thứ quyết định bảng lương
    đi tiếp hay không — một bộ kiểm hôm nay nói đạt hôm mai nói không, với cùng con số, thì không ai
    dám dùng nó để trả tiền.

    CÒN CỜ CHẶN THÌ KHÔNG QUA. Không có cờ KHÔNG có nghĩa là bảng đúng, chỉ nghĩa là những thứ đã
    biết cách kiểm thì đều sạch — nên trạng thái mới tên là `da_kiem_co_so`, không phải `dung`.
    """
    from app.services import luong_khoa as LK
    run = H.get_or_draft(db, period)
    if run.status not in ("nhap",) + H.DA_KIEM:
        raise HTTPException(422, f"Kỳ {period} đã qua bước kiểm (đang ở '{run.status}')")
    co = LK.kiem_co_so(db, run)
    chan = LK.co_chan(co)
    if not chan and run.status == "nhap":
        run.status = "da_kiem_co_so"
        R.audit(db, u.username, u.role, "bang_luong_kiem_co_so", f"payroll:{period}",
                after={"so_co": len(co), "so_chan": 0})
        db.commit()
    return {"period": period, "trang_thai": run.status, "dat": not chan,
            "so_co": len(co), "co": co,
            "message": ("Đủ điều kiện trình" if not chan else
                        f"Còn {len(chan)} điều kiện chặn – chưa trình được"),
            "ghi_chu": "Không có cờ nghĩa là những thứ đã biết cách kiểm đều sạch, không nghĩa là bảng đúng."}


@router.get("/payroll-runs/{period}/so-thu-nhap")
def payroll_so_thu_nhap(period: str, u: User = Depends(bang_luong), db: Session = Depends(get_db)):
    """Sổ sự kiện thu nhập của kỳ: ai đã được trả khoản gì, vì căn cứ nào, nguồn là những gì.

    Đây là cửa trả lời câu "khoản này đã trả chưa" — câu mà trước Đợt B hệ thống không có chỗ nào
    trả lời được, vì mọi khoản đều được tính lại từ đầu và dấu vết duy nhất là một dòng chữ.

    Chỉ ĐỌC. Sổ ghi lúc ký, trong cùng giao dịch với bản khóa; không có cửa nào gõ tay vào đây, và
    việc không có cửa ấy là tính chất an toàn chứ không phải việc còn thiếu.
    """
    from app.services import thu_nhap_su_kien as TN
    return {"period": period, "loai_khoan": TN.LOAI_KHOAN, "doc_chiem": list(TN.DOC_CHIEM),
            "dong": TN.so_cua_ky(db, period)}


@router.get("/payroll-runs/{period}/ban-khoa")
def payroll_ban_khoa(period: str, u: User = Depends(bang_luong), db: Session = Depends(get_db)):
    """Bản khóa của kỳ, và kết quả tính lại hôm nay so với nó.

    Đây là cửa trả lời câu "cùng đầu vào có ra cùng kết quả không" — câu người ta hỏi khi giải trình
    một kỳ lương. Lệch KHÔNG tự là sai, nhưng lệch phải hiện ra chứ không được im.
    """
    from app.services import luong_khoa as LK
    run = H.get_or_draft(db, period)
    b = LK.ban_dang_hieu_luc(db, period)
    return {"period": period, "trang_thai": run.status,
            "ban_khoa": None if b is None else {
                "ban_so": b.ban_so, "khoa_boi": b.khoa_boi, "khoa_vai": b.khoa_vai,
                "khoa_luc": b.khoa_luc, "dau_van_tay": b.dau_van_tay, "quy_tac": b.quy_tac},
            "doi_chieu": LK.doi_chieu_voi_ban_khoa(db, run)}


@router.post("/payroll-runs/{period}/advance")
def payroll_advance(period: str, u: User = Depends(require_roles("hcns", "tgd", "chutich")), db: Session = Depends(get_db)):
    run = H.get_or_draft(db, period)
    try:
        msg = H.advance(db, u, run)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"message": msg, "run": run_out(run)}


# ====================== ĐỢT A2 · KẾ TOÁN CHI – UNC – ĐỐI CHIẾU ======================
#
# Khúc cuối của chuỗi Chủ tịch chốt 07/10/2026. Năm cửa, và thứ tự của chúng là thứ tự có thật trên
# bàn kế toán: mở một lần chi → tải Ủy nhiệm chi → tải phụ lục → sửa chỗ máy đọc sai → bấm đối chiếu.
#
# VÌ SAO KẾ TOÁN KHÔNG BẤM ĐƯỢC "ĐÃ TRẢ ĐỦ"
#
# Không có cửa nào cho người gõ vào kết luận. Kết luận đủ / một phần / lỗi do `services/chi_luong.py`
# tính ra từ bản khóa, mặt UNC và phụ lục — người sửa được SỐ LIỆU máy đọc sai, không sửa được KẾT
# LUẬN. Một ô cho người gõ "đã trả đủ" sẽ biến cả chuỗi này thành một lời khai, mà lời khai thì không
# cần tới phần mềm nào.
CHI_LUONG_ROLES = ("ketoan", "cntt")


class ChiSuaIn(BaseModel):
    """Người sửa chỗ máy đọc sai. Chỉ các ô máy ĐỌC, không có ô nào cho kết luận."""
    so_tien_unc: float | None = None
    ngan_hang: str | None = None
    tai_khoan_cong_ty: str | None = None
    ngay_chuyen: date | None = None
    so_tham_chieu: str | None = None
    noi_dung_unc: str | None = None
    dong_phu_luc: list[dict] | None = None


def _ban_da_ky(db: Session, period: str):
    """Bản khóa đang hiệu lực của kỳ. Không có thì chưa chi được, và lý do phải nói thẳng."""
    from app.services import luong_khoa as LK
    b = LK.ban_dang_hieu_luc(db, period)
    if b is None:
        raise HTTPException(422, f"Kỳ {period} chưa có bản khóa nào – phải có chữ ký Chủ tịch hoặc "
                                 "TGĐ trước, rồi mới tới bước chi")
    return b


def _chi_out(c) -> dict:
    return {"id": c.id, "period": c.period, "lan": c.lan, "ban_khoa_id": c.ban_khoa_id,
            "ngan_hang": c.ngan_hang, "tai_khoan_cong_ty": c.tai_khoan_cong_ty,
            "ngay_chuyen": c.ngay_chuyen, "so_tham_chieu": c.so_tham_chieu,
            "so_tien_unc": c.so_tien_unc, "noi_dung_unc": c.noi_dung_unc,
            "co_unc": c.unc_attachment_id is not None, "co_phu_luc": c.phu_luc_attachment_id is not None,
            "so_dong_phu_luc": len(c.dong_phu_luc or []), "dong_phu_luc": c.dong_phu_luc or [],
            "phu_luc_ghi_chu": c.phu_luc_ghi_chu, "ket_luan": c.ket_luan,
            "ket_luan_ten": CL_KET_LUAN.get(c.ket_luan, ""), "ket_qua": c.ket_qua or {},
            "doi_chieu_luc": c.doi_chieu_luc, "chi_boi": c.chi_boi, "luc": c.luc}


def _lay_chi(db: Session, period: str, lan: int):
    c = db.execute(select(ChiKyLuong).where(ChiKyLuong.period == period,
                                            ChiKyLuong.lan == lan)).scalars().first()
    if c is None:
        raise HTTPException(404, f"Không có lần chi {lan} của kỳ {period}")
    return c


@cong_chan_quyen
def cong_xem_chi_luong(u: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    """Cổng xem các lần chi của một kỳ lương. ĐẶT Ở CHỮ KÝ để máy đọc được, không viết trong thân.

    LUẬT KHÔNG ĐỔI MỘT CHỮ so với lúc nó nằm trong thân `chi_danh_sach` – chỉ dời ra chữ ký và
    đặt tên. Lý do dời:

    Hàng rào P1 đòi MÁY nhận ra quyền mà không phải phân tích mã nguồn. Chặn viết trong thân một
    hàm endpoint thì máy chỉ thấy được bằng cách đọc mã, và ngày 08/10/2026 chính cửa này làm P1
    đỏ trên `main` – kéo theo mọi làn đang mở, vì main đỏ thì không gì gộp được.

    HAI LỐI SỬA SAI đã cân nhắc và bỏ, ghi ra đây để không ai đi lại:

    (1) Đổi thành `require_roles(...)` ở chữ ký – rẻ nhất, và SAI. Luật này không phải một danh
        sách vai trò: nó là "mở được thẻ payroll" HOẶC "thuộc nhóm vai được chi", mà vế đầu phụ
        thuộc ngoại lệ theo TỪNG NGƯỜI trong cơ sở dữ liệu. Ép thành danh sách vai cố định vừa
        chặn nhầm người đang có ngoại lệ, vừa mở cho người cùng vai mà không có ngoại lệ. Sửa
        hàng rào cho hợp phép thử là đúng cái việc phép thử sinh ra để chặn.

    (2) Dời chặn sang một hàm dịch vụ rồi thôi. Làm thế thì `inspect.getsource` của endpoint
        không còn thấy dấu hiệu nào nữa và P1 xanh – nhưng xanh vì P1 ĐÃ MÙ, không vì quyền đã
        khai. Bảng `CHAN_TANG_DICH_VU` sinh ra cho lối ấy và có Q2 đọc lại hàm được nêu tên, song
        khoá tra bảng (`ks_robot._khoa_khai`) chỉ dựng cho POST/PUT/PATCH/DELETE – một cửa GET
        như cửa này KHÔNG khai vào đó được. Nên lối ấy ở đây là giấu, không phải khai.

    Còn lại đúng một lối thẳng, và kho đã có sẵn đúng cái móc ấy: `@cong_chan_quyen` của
    `api/deps.py` – docstring của nó lấy chính BẢNG LƯƠNG làm ví dụ, vì đây đúng loại cửa mà
    quyền phụ thuộc DỮ LIỆU chứ không phụ thuộc vai trò. Cổng nằm ở chữ ký nên
    `ks_robot.chan_o_chu_ky` đọc được, và tên cổng khai vào `CUA_KHONG_THEO_VAI_TRO` của KS-2.
    """
    from app.api.deps import toan_quyen
    from app.services import access as AC
    # `and not toan_quyen(u)` theo quyết định 06/9/2026: không cửa TỪ CHỐI THEO VAI TRÒ nào
    # được chặn Chủ tịch, trừ khi đó là TÁCH BẠCH TRÁCH NHIỆM và có khai ở ks_toan_quyen.
    # Đây là cửa XEM, không phải cửa ký hay cửa chi, nên không có gì để tách bạch.
    if ("payroll" not in AC.hr_tabs_for(db, u) and u.role not in CHI_LUONG_ROLES
            and not toan_quyen(u)):
        raise HTTPException(403, "Vai trò của bạn không xem được các lần chi lương")
    return u


@router.get("/payroll-runs/{period}/chi")
def chi_danh_sach(period: str, u: User = Depends(cong_xem_chi_luong),
                  db: Session = Depends(get_db)):
    """Các lần chi của kỳ, kèm trạng thái trả tiền của cả kỳ.

    Không dùng cổng `bang_luong` ở đây: cổng ấy gác BẢNG LƯƠNG TOÀN CÔNG TY, mà vai trò "ketoan"
    chỉ vào được bằng ngoại lệ theo người. Người chi tiền phải thấy được việc mình vừa chi, kể cả
    khi họ không được mở bảng lương – và màn hình này không có dòng lương của ai, chỉ có số tiền
    chuyển, ngày, số tham chiếu và kết luận đối chiếu.
    """
    from app.services import chi_luong as CL
    ds = list(db.execute(select(ChiKyLuong).where(ChiKyLuong.period == period)
                         .order_by(ChiKyLuong.lan)).scalars())
    return {"period": period, "tra_trang_thai": CL.trang_thai_ky(db, period),
            "tra_trang_thai_ten": CL_TRA_TRANG_THAI.get(CL.trang_thai_ky(db, period), ""),
            "lan_chi": [_chi_out(c) for c in ds]}


@router.post("/payroll-runs/{period}/chi", status_code=201)
def chi_mo_lan(period: str, u: User = Depends(require_roles(*CHI_LUONG_ROLES)),
               db: Session = Depends(get_db)):
    """Mở một lần chi mới cho kỳ. Gắn vào BẢN KHÓA đang hiệu lực, không gắn vào kỳ.

    Trả lương hai đợt, trả bù một người bị sót, chuyển nhầm rồi chuyển lại – mỗi việc một lần chi.
    Cộng dồn vào một dòng là xoá mất câu "tiền ra khỏi tài khoản mấy lần".
    """
    run = H.get_or_draft(db, period)
    if run.status not in H.DA_KY:
        raise HTTPException(422, f"Kỳ {period} chưa được ký (đang ở '{run.status}') – chưa chi được")
    b = _ban_da_ky(db, period)
    cu = db.execute(select(ChiKyLuong).where(ChiKyLuong.period == period)
                    .order_by(ChiKyLuong.lan.desc())).scalars().first()
    c = ChiKyLuong(period=period, ban_khoa_id=b.id, lan=(cu.lan + 1) if cu else 1,
                   chi_boi=u.username, chi_vai=u.role)
    db.add(c)
    R.audit(db, u.username, u.role, "mo_lan_chi_luong", f"payroll:{period}",
            after={"lan": c.lan, "ban_khoa_id": b.id})
    db.commit()
    return {"message": f"Đã mở lần chi {c.lan} cho kỳ {period} – tải Ủy nhiệm chi lên để máy đọc",
            "chi": _chi_out(c)}


@router.post("/payroll-runs/{period}/chi/{lan}/unc")
async def chi_tai_unc(period: str, lan: int, tep: UploadFile = File(...),
                      u: User = Depends(require_roles(*CHI_LUONG_ROLES)),
                      db: Session = Depends(get_db)):
    """Tải MẶT Ủy nhiệm chi. Máy đọc sáu ô: ngân hàng, tài khoản công ty, ngày, số tham chiếu,
    số tiền, nội dung. Không đọc danh sách người trên tấm này."""
    from app.services import chi_luong as CL, doc_chung_tu as DCT
    c = _lay_chi(db, period, lan)
    if c.ket_luan:
        raise HTTPException(422, f"Lần chi {lan} đã đối chiếu xong – mở lần chi mới nếu có chuyển bù")
    data = await tep.read()
    try:
        kq = CL.doc_mat_unc(db, c, tep.filename or "unc", data, tep.content_type or "",
                            u.username, u.role)
    except DCT.KhongDocDuoc as ex:
        raise HTTPException(400, str(ex))
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    db.commit()
    return {**kq, "chi": _chi_out(c),
            "message": ("Máy đã đọc mặt Ủy nhiệm chi. Số này là NHÁP – kiểm lại rồi mới bấm đối chiếu."
                        if kq.get("so_tien_unc") is not None else
                        "Máy KHÔNG đọc được số tiền – ô để TRỐNG chứ không điền 0. Mời nhập tay.")}


@router.post("/payroll-runs/{period}/chi/{lan}/phu-luc")
async def chi_tai_phu_luc(period: str, lan: int, tep: UploadFile = File(...),
                          u: User = Depends(require_roles(*CHI_LUONG_ROLES)),
                          db: Session = Depends(get_db)):
    """Tải PHỤ LỤC danh sách chuyển lương. Máy đọc ĐÚNG hai ô mỗi dòng: họ tên và số tiền.

    Mở theo ngoại lệ có chữ ký Chủ tịch 07/10/2026, khai ở models/doc_chung_tu.py::MO_DOC_CO_CHU_KY.
    Số tài khoản, ngày sinh, CCCD, lương cơ bản, bảo hiểm, thuế – máy không đọc, và nếu mô hình tự
    trả về thì bị bỏ ở phía ta trước khi lưu, kèm một dòng ghi chú nói đã bỏ cái gì.
    """
    from app.services import chi_luong as CL, doc_chung_tu as DCT
    c = _lay_chi(db, period, lan)
    if c.ket_luan:
        raise HTTPException(422, f"Lần chi {lan} đã đối chiếu xong – mở lần chi mới nếu có chuyển bù")
    data = await tep.read()
    try:
        kq = CL.doc_phu_luc(db, c, tep.filename or "phu-luc", data, tep.content_type or "",
                            u.username, u.role)
    except DCT.KhongDocDuoc as ex:
        raise HTTPException(400, str(ex))
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    db.commit()
    return {**kq, "chi": _chi_out(c),
            "message": f"Máy đọc được {kq['so_dong']} dòng. Kiểm lại rồi bấm đối chiếu."}


@router.put("/payroll-runs/{period}/chi/{lan}")
def chi_sua(period: str, lan: int, body: ChiSuaIn,
            u: User = Depends(require_roles(*CHI_LUONG_ROLES)), db: Session = Depends(get_db)):
    """Người sửa chỗ máy đọc sai. Không có ô nào cho kết luận – xem chú thích đầu khối này."""
    c = _lay_chi(db, period, lan)
    if c.ket_luan:
        raise HTTPException(422, f"Lần chi {lan} đã đối chiếu xong – không sửa được nữa")
    truoc = {"so_tien_unc": c.so_tien_unc, "so_dong": len(c.dong_phu_luc or [])}
    for k in ("so_tien_unc", "ngan_hang", "tai_khoan_cong_ty", "ngay_chuyen", "so_tham_chieu",
              "noi_dung_unc"):
        v = getattr(body, k)
        if v is not None:
            setattr(c, k, v)
    if body.dong_phu_luc is not None:
        # Chỉ giữ hai ô cho phép. Người gõ tay cũng đi qua đúng bộ lọc mà máy đi qua: cửa nhập tay
        # mà rộng hơn cửa máy đọc thì lệnh cấm chỉ còn cấm được cái máy.
        from app.models.doc_chung_tu import MO_DOC_CO_CHU_KY
        cho_phep = MO_DOC_CO_CHU_KY["phu_luc_unc_luong"]["truong"]
        c.dong_phu_luc = [{k: d.get(k) for k in cho_phep} for d in body.dong_phu_luc
                          if str(d.get("ho_ten") or "").strip()]
    R.audit(db, u.username, u.role, "sua_lan_chi_luong", f"payroll:{period}:{lan}",
            before=truoc, after={"so_tien_unc": c.so_tien_unc, "so_dong": len(c.dong_phu_luc or [])})
    db.commit()
    return {"message": "Đã lưu", "chi": _chi_out(c)}


@router.post("/payroll-runs/{period}/chi/{lan}/doi-chieu")
def chi_doi_chieu(period: str, lan: int, u: User = Depends(require_roles(*CHI_LUONG_ROLES)),
                  db: Session = Depends(get_db)):
    """Đối chiếu lần chi với bản đã ký và ghi nhận ĐÃ TRẢ.

    Kết luận do quy tắc xác định tính ra, không do mô hình ngôn ngữ và không do người gõ. Chạy lại
    với cùng dữ liệu luôn ra cùng kết luận – đó là điều kiện để một kết luận "đã trả đủ" có giá trị.
    """
    from app.models.luong_khoa import BangLuongKhoa
    from app.services import chi_luong as CL
    c = _lay_chi(db, period, lan)
    run = H.get_or_draft(db, period)
    ban = db.get(BangLuongKhoa, c.ban_khoa_id)
    if ban is None:
        raise HTTPException(422, "Không tìm thấy bản khóa của lần chi này")
    kq = CL.ghi_nhan(db, c, ban, run)
    if not c.ket_luan:
        db.rollback()
        raise HTTPException(422, kq.get("ly_do") or "Chưa đối chiếu được")
    R.audit(db, u.username, u.role, f"doi_chieu_chi_luong_{c.ket_luan}", f"payroll:{period}:{lan}",
            after={"ket_luan": c.ket_luan, "tra_trang_thai": run.tra_trang_thai})
    db.commit()
    return {"message": f"{CL_KET_LUAN.get(c.ket_luan, c.ket_luan)} – {kq['ly_do']}",
            "ket_luan": c.ket_luan, "ket_qua": kq, "chi": _chi_out(c),
            "tra_trang_thai": run.tra_trang_thai,
            "tra_trang_thai_ten": CL_TRA_TRANG_THAI.get(run.tra_trang_thai, "")}
