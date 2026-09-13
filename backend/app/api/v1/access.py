"""Màn hình Tài khoản & phân quyền (đặc tả 07/9/2026, phần B).

Nguyên tắc của màn hình này: ma trận quyền VẪN nằm trong mã nguồn, ở đây chỉ CÔNG BỐ chứ không sửa.
Cho sửa ma trận trên giao diện thì mất hai thứ đang bảo vệ hệ thống – phép thử tự động và lịch sử thay
đổi trong git – và một lần bấm nhầm là mở cả sổ lương. Thứ sửa được ở đây chỉ có ba: ai ở vai trò nào,
tài khoản mở hay khóa, và ngoại lệ có thời hạn (API ngoại lệ nằm ở routes.py).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles, toan_quyen_ke_ca_tach_bach
from app.models.core import User, ROLES, Company
from app.services import access as AC
from app.services import access_admin as AA
from app.services import rules as R
from app.services import luong_viec_bao_cao as LVBC   # PQ-2 – trình bày bảng luồng việc

router = APIRouter(prefix="/api/v1/access", tags=["phan-quyen"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# robot_pq ĐỌC được màn hình phân quyền – đó là bàn làm việc của nó. Nó KHÔNG có trong THAO_TAC, nên
# đổi vai trò, khoá/mở tài khoản, gán pháp nhân vẫn phải do người bấm. Robot đề xuất, người quyết.
XEM = ("chutich", "tgd", "cntt", "hcns", "bks", "robot_pq", "robot_ks")   # mở được màn hình
THAO_TAC = ("cntt", "hcns")                          # đổi vai trò, khóa/mở, đặt lại mật khẩu
# Ba vai trò còn phạm vi rộng nhất sau khi siết ma trận: đổi AI SANG một trong ba vai trò này phải do
# Chủ tịch hoặc TGĐ làm. Quyền nhìn toàn bộ tiền và sổ sách tương đương quyền ký – một người ở HCNS
# hoặc CNTT không nên tự trao được cho ai.
VAI_TRO_NHAY_CAM = ("ketoan", "cntt", "bks")


@router.get("/matrix")
def matrix(u: User = Depends(require_roles(*XEM))):
    return AA.ma_tran()


@router.get("/matrix.xlsx")
def matrix_xlsx(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Bản Excel để TGĐ ký rà quyền hằng tháng."""
    noi_dung = AA.ma_tran_xlsx(db)
    R.audit(db, u.username, u.role, "xuat_ma_tran_quyen", "access"); db.commit()
    return Response(content=noi_dung, media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="MA_TRAN_PHAN_QUYEN_{datetime.now():%d%m%y}.xlsx"'})


# ---------------------------------------------------------------------------------------------
# PQ-2 · Luồng công việc – ai được ĐẨY VIỆC sang bước sau
# ---------------------------------------------------------------------------------------------
# Ba đường dưới đây trả lời một câu mà ma trận quyền ở trên KHÔNG trả lời được: ma trận nói ai được
# NHÌN màn hình nào; luồng việc nói ai được đẩy một hồ sơ sang bước tiếp theo. Hai câu khác nhau,
# và câu thứ hai mới là chuỗi chỉ huy thật của công ty.
@router.get("/luong-viec")
def luong_viec(u: User = Depends(require_roles(*XEM))):
    return LVBC.bao_cao()


@router.get("/luong-viec/vai-tro/{vai_tro}")
def luong_viec_theo_vai_tro(vai_tro: str, u: User = Depends(require_roles(*XEM))):
    """Tra ngược: người giữ vai trò này đẩy được những bước nào."""
    return LVBC.tra_cuu_vai_tro(vai_tro)


@router.get("/luong-viec.xlsx")
def luong_viec_xlsx(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Bản Excel để Chủ tịch rà và ký – có sẵn hai ô ký ở cuối."""
    noi_dung = LVBC.xlsx(db)
    R.audit(db, u.username, u.role, "xuat_luong_cong_viec", "access"); db.commit()
    return Response(content=noi_dung, media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="LUONG_CONG_VIEC_{datetime.now():%d%m%y}.xlsx"'})


@router.get("/accounts")
def accounts(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return {"rows": AA.danh_sach_tai_khoan(db), "roles": ROLES,
            "companies": [{"id": c.id, "code": c.code, "name": c.name}
                          for c in db.execute(select(Company).where(Company.active == True).order_by(Company.code)).scalars()],
            "vai_tro_nhay_cam": VAI_TRO_NHAY_CAM}


@router.get("/gaps")
def gaps(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return AA.chenh_lech(db)


@router.get("/audit")
def audit_log(limit: int = 200, ke_ca_dang_nhap: bool = False,
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return {"rows": AA.nhat_ky_quyen(db, limit, bo_dang_nhap=not ke_ca_dang_nhap)}


class TaoTaiKhoanIn(BaseModel):
    ho_ten: str
    ma_nv: str                       # mã nhân viên HCNS – cũng là mật khẩu tạm
    role: str
    department: str = ""
    username: str = ""               # để trống thì sinh từ họ tên không dấu
    ngoai_bien_che: bool = False
    company_id: int | None = None
    tao_ho_so: bool = True           # tạo luôn hồ sơ nhân sự và nối vào tài khoản


def _khong_dau(s: str) -> str:
    import unicodedata, re
    t = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


@router.post("/accounts", status_code=201)
def tao_tai_khoan(data: TaoTaiKhoanIn,
                  u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Tạo tài khoản cho một người. Trước bản này chỉ có đường nạp cả danh sách từ bảng lương, nên thêm
    MỘT người – kế toán trưởng thuê ngoài, người mới vào giữa kỳ – là không có cách nào ngoài sửa tệp dữ
    liệu và nạp lại cả danh sách, mà lệnh nạp đó còn đóng tài khoản của người không có trong danh sách.

    Mật khẩu tạm = mã nhân viên và cờ buộc đổi được bật sẵn: người dùng đổi ở lần đăng nhập đầu, trước
    đó chưa vào được dữ liệu nào.
    """
    from app.core.security import hash_password
    from app.models.hr import Employee
    from app.services import hr as H
    if data.role not in ROLES: raise HTTPException(422, f"Vai trò không hợp lệ: {data.role}")
    if data.role in VAI_TRO_NHAY_CAM and u.role not in ("chutich", "tgd"):
        raise HTTPException(403, f"Tạo tài khoản vai trò {ROLES[data.role]} phải do Chủ tịch hoặc Tổng giám đốc")
    ho_ten = (data.ho_ten or "").strip()
    ma = (data.ma_nv or "").strip()
    if len(ho_ten) < 3: raise HTTPException(422, "Chưa nhập họ tên")
    if len(ma) < 2: raise HTTPException(422, "Chưa nhập mã nhân viên – mã này cũng là mật khẩu tạm")
    if data.company_id is not None and not db.get(Company, data.company_id):
        raise HTTPException(422, "Pháp nhân không có trong danh mục")

    uname = _khong_dau(data.username or ho_ten)[:24] or f"nv{ma}"
    goc, n = uname, 1
    while db.execute(select(User).where(User.username == uname)).scalars().first():
        n += 1; uname = f"{goc}{n}"
    if db.execute(select(User).where(User.staff_code == ma)).scalars().first():
        raise HTTPException(422, f"Đã có tài khoản mang mã nhân viên {ma}")

    t = User(username=uname, full_name=ho_ten, role=data.role, department=data.department or "",
             staff_code=ma, password_hash=hash_password(ma), active=True,
             must_change_password=True, ngoai_bien_che=data.ngoai_bien_che, company_id=data.company_id)
    db.add(t); db.flush()

    ho_so = ""
    if data.tao_ho_so:
        e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
        if e is None:
            e = Employee(code=ma, full_name=ho_ten, department=data.department or "ketoan",
                         position="nv", contract_type="doi_tac" if data.ngoai_bien_che else "hdld")
            db.add(e); db.flush()
        e.user_id, e.active = t.id, True
        if data.company_id is not None: e.company_id = data.company_id
        ho_so = e.code

    R.audit(db, u.username, u.role, "tao_tai_khoan", f"user:{t.username}",
            after={"ho_ten": ho_ten, "ma_nv": ma, "vai_tro": t.role,
                   "ngoai_bien_che": t.ngoai_bien_che, "ho_so": ho_so})
    db.commit()
    return {"id": t.id, "username": t.username, "ho_so": ho_so,
            "message": f"Đã tạo tài khoản {t.username} cho {ho_ten} – mật khẩu tạm là mã nhân viên {ma}, "
                       f"người dùng phải đổi ở lần đăng nhập đầu"}


class DoiVaiTroIn(BaseModel):
    role: str
    reason: str


@router.post("/role-change/{uid}")
def role_change(uid: int, data: DoiVaiTroIn,
                u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Đổi vai trò kèm lý do bằng lời. Ba chốt chặn, mỗi cái vá một cách mất kiểm soát khác nhau."""
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if data.role not in ROLES: raise HTTPException(422, f"Vai trò không hợp lệ: {data.role}")
    if not (data.reason or "").strip(): raise HTTPException(422, "Phải ghi lý do đổi vai trò")
    if t.id == u.id: raise HTTPException(422, "Không tự đổi vai trò của chính mình")
    if t.role in ("chutich", "tgd") and u.role != "cntt" and not toan_quyen_ke_ca_tach_bach(u, db):
        raise HTTPException(403, "Chỉ CNTT thao tác trên tài khoản lãnh đạo")
    if data.role in VAI_TRO_NHAY_CAM and u.role not in ("chutich", "tgd"):
        raise HTTPException(403, f"Đổi sang vai trò {ROLES[data.role]} phải do Chủ tịch hoặc Tổng giám đốc – "
                                 f"đây là vai trò nhìn được toàn bộ tiền và sổ sách")
    if data.role == t.role: raise HTTPException(422, "Vai trò không thay đổi")
    before = {"vai_tro": t.role}
    t.role, t.role_changed_at, t.role_changed_by = data.role, datetime.now(), u.username
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"vai_tro": t.role, "ly_do": data.reason.strip()[:300]})
    db.commit()
    return {"message": f"Đã đổi vai trò {t.full_name} thành {ROLES[t.role]}", "role": t.role}


class PhapNhanIn(BaseModel):
    company_id: int | None = None


@router.put("/users/{uid}/company")
def gan_phap_nhan(uid: int, data: PhapNhanIn,
                  u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Gán pháp nhân chủ quản cho tài khoản. Để trống là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ –
    giữ đúng quy ước đã dùng ở tour, booking, xe và hồ sơ nhân sự."""
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if data.company_id is not None and not db.get(Company, data.company_id):
        raise HTTPException(422, "Pháp nhân không có trong danh mục")
    before = {"company_id": t.company_id}
    t.company_id = data.company_id
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"company_id": t.company_id})
    db.commit()
    return {"message": "Đã cập nhật pháp nhân chủ quản", "company_id": t.company_id}


class HoSoIn(BaseModel):
    ma_nv: str | None = None
    ho_ten: str | None = None
    department: str | None = None


@router.put("/users/{uid}/ho-so")
def sua_ho_so(uid: int, data: HoSoIn,
              u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Sửa mã nhân viên, họ tên, phòng của một tài khoản ĐÃ CÓ, và nối vào hồ sơ nhân sự cùng mã.

    Vì sao cần: tài khoản nạp từ Vietrip hoặc tạo tay trước đây có thể không mang mã nhân viên nào. Mã
    đó là khóa nối tài khoản với hồ sơ và bảng lương, nên thiếu nó thì người này nằm ngoài mọi đối chiếu
    – và cũng không đặt lại mật khẩu mặc định được, vì mật khẩu mặc định chính là mã nhân viên.
    """
    from app.models.hr import Employee
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    truoc = {"ma_nv": t.staff_code, "ho_ten": t.full_name, "phong": t.department}
    if data.ma_nv is not None:
        ma = data.ma_nv.strip()
        if ma:
            khac = db.execute(select(User).where(User.staff_code == ma, User.id != uid)).scalars().first()
            if khac: raise HTTPException(422, f"Mã {ma} đã thuộc tài khoản {khac.username} ({khac.full_name})")
        t.staff_code = ma
        if ma:
            e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
            if e is not None and e.user_id in (None, uid):
                e.user_id = uid          # nối hồ sơ cùng mã, nếu hồ sơ đó chưa gắn cho ai khác
    if data.ho_ten is not None and data.ho_ten.strip(): t.full_name = data.ho_ten.strip()
    if data.department is not None: t.department = data.department.strip()
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=truoc,
            after={"ma_nv": t.staff_code, "ho_ten": t.full_name, "phong": t.department})
    db.commit()
    return {"message": f"Đã cập nhật hồ sơ tài khoản {t.username}", "staff_code": t.staff_code}


class BienCheIn(BaseModel):
    ngoai_bien_che: bool


@router.put("/users/{uid}/bien-che")
def danh_dau_bien_che(uid: int, data: BienCheIn,
                      u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Đánh dấu tài khoản NGOÀI biên chế (kế toán trưởng thuê ngoài, kiểm toán, tư vấn): có tài khoản
    nhưng không có trong bảng lương. Không đánh dấu thì danh sách đối chiếu báo lệch mãi mãi, và rà
    quyền hằng tháng không nhìn ra ai là người ngoài."""
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    before = {"ngoai_bien_che": t.ngoai_bien_che}
    t.ngoai_bien_che = data.ngoai_bien_che
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"ngoai_bien_che": t.ngoai_bien_che})
    db.commit()
    return {"message": "Đã đánh dấu ngoài biên chế" if data.ngoai_bien_che else "Đã bỏ đánh dấu ngoài biên chế"}


# ---------- P10: tra cứu ngược – chọn một người, hiện họ làm được gì và VÌ SAO ----------
@router.get("/tra-cuu/{uid}")
def tra_cuu_quyen_mot_nguoi(uid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Ba lớp quyền của một tài khoản, mỗi dòng kèm lý do chỉ thẳng vào dòng cho phép.

    Quyền XEM chứ không phải THAO_TAC: người quản lý phải tra được quyền của nhân viên mình mà không
    cần quyền sửa vai trò. Nếu buộc phải có quyền sửa mới tra được thì kỳ rà quyền hằng tháng chỉ hai
    người làm được, và rà quyền một tháng một lần bởi hai người là không rà.
    """
    from app.services import tra_cuu_quyen as TC
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    return TC.tra_cuu(db, t)


@router.get("/tra-cuu-vai-tro/{vai_tro}")
def tra_cuu_theo_vai_tro(vai_tro: str, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Chiều ngược lại của cùng câu hỏi: một VAI TRÒ vào được những đâu, và ai đang ở vai trò đó.

    Cần cả hai chiều vì hai câu hỏi khác nhau xảy ra ở hai lúc khác nhau: "vì sao anh này vào được"
    hỏi khi có sự cố, "đổi vai trò này thì ảnh hưởng bao nhiêu người" hỏi trước khi siết.
    """
    if vai_tro not in ROLES: raise HTTPException(404, "Không có vai trò này")
    from app.services import tra_cuu_quyen as TC
    nguoi = list(db.execute(select(User).where(User.role == vai_tro, User.active == True)).scalars())
    mau = nguoi[0] if nguoi else User(id=0, username="(chưa ai)", full_name="(chưa ai ở vai trò này)",
                                      role=vai_tro, department="", staff_code="", active=True,
                                      ngoai_bien_che=False, company_id=None, password_hash="")
    kq = TC.tra_cuu(db, mau)
    return {"vai_tro": vai_tro, "vai_tro_ten": ROLES[vai_tro],
            "so_nguoi": len(nguoi),
            "nguoi": [{"id": x.id, "full_name": x.full_name, "staff_code": x.staff_code,
                       "department": x.department} for x in nguoi],
            "man_hinh": kq["man_hinh"], "api": kq["api"],
            "dem": kq["dem"],
            "canh_bao": (["Vai trò này chưa có ai – quyền đang mở cho một chỗ trống."] if not nguoi else [])
                       + [c for c in kq["canh_bao"] if "Tài khoản đã khóa" not in c]}


# ---------- Suy pháp nhân cho tài khoản từ hồ sơ nhân sự ----------
@router.get("/phap-nhan/suy-tu-ho-so")
def xem_truoc_suy_phap_nhan(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Xem trước: tài khoản nào suy được pháp nhân từ hồ sơ, tài khoản nào không và vì sao.

    Mở cho quyền XEM vì đây là bảng đối chiếu, không sửa gì. Ghi thì phải quyền THAO_TAC – hai việc
    tách nhau để người rà quyền xem được danh sách mà không cần quyền ghi vào bảng tài khoản.
    """
    from app.services import suy_phap_nhan as SPN
    return SPN.xem_truoc(db)


class SuyPhapNhanIn(BaseModel):
    user_ids: list[int] | None = None      # bỏ trống là ghi cho toàn bộ nhóm suy được


@router.post("/phap-nhan/suy-tu-ho-so")
def ghi_suy_phap_nhan(data: SuyPhapNhanIn,
                      u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")),
                      db: Session = Depends(get_db)):
    """Ghi pháp nhân đã suy vào tài khoản. Không đè giá trị đã gán tay, và có ghi nhật ký.

    Cùng bộ vai trò với PUT /users/{uid}/company: đây là cùng một việc, chỉ khác là làm hàng loạt.
    Cho phép nhóm rộng hơn ở đây thì hàng loạt trở thành đường vòng của lẻ.
    """
    from app.services import suy_phap_nhan as SPN
    return SPN.ap_dung(db, u, data.user_ids)


# ---------- Tài khoản cho vai trò máy (P8) ----------
class TaoRobotIn(BaseModel):
    role: str                        # phải là một vai trò máy
    ho_ten: str = ""                 # để trống thì lấy tên vai trò


@router.post("/accounts/robot", status_code=201)
def tao_tai_khoan_robot(data: TaoRobotIn,
                        u: User = Depends(require_roles("chutich", "tgd", "cntt")),
                        db: Session = Depends(get_db)):
    """Tạo tài khoản đăng nhập cho MỘT vai trò máy, mật khẩu ngẫu nhiên, hiện đúng một lần.

    Ba điều khác hẳn tài khoản người, mỗi điều một lý do:

    1. MẬT KHẨU NGẪU NHIÊN, không phải mã nhân viên. Tài khoản người dùng mã nhân viên làm mật khẩu
       tạm vì người sẽ đổi ngay lần đăng nhập đầu; robot không có ai ngồi đổi hộ, nên mật khẩu ban đầu
       CHÍNH LÀ mật khẩu lâu dài – lấy từ nguồn ngẫu nhiên mật mã, không phải từ một con số nằm công
       khai trên bảng lương.

    2. KHÔNG bắt đổi lần đầu. Với người, cờ ấy là hàng rào; với máy, nó là cái khoá cửa từ bên trong –
       robot bị đẩy sang màn hình đổi mật khẩu mà không có ai bấm.

    3. Đánh dấu NGOÀI BIÊN CHẾ: robot không có trong bảng lương, và danh sách đối chiếu nhân sự không
       được báo lệch vì ba tài khoản không phải người.

    Mật khẩu trả về ĐÚNG MỘT LẦN trong phản hồi này và không lưu ở đâu dưới dạng đọc được. Mất thì đặt
    lại, không tra lại được – đó là chủ ý.
    """
    import secrets
    from app.core.security import hash_password
    if not AC.la_vai_tro_may(data.role):
        raise HTTPException(422, f"{data.role} không phải vai trò máy. Chỉ tạo được cho: "
                                 f"{', '.join(AC.VAI_TRO_MAY)}")
    da_co = db.execute(select(User).where(User.role == data.role, User.active == True)).scalars().all()  # noqa: E712
    if da_co:
        raise HTTPException(409, f"{ROLES[data.role]} đã có tài khoản {da_co[0].username}. Một vai trò "
                                 f"máy chỉ nên có MỘT tài khoản – hai cái thì không truy được lần chạy "
                                 f"nào của bên nào.")
    mat_khau = secrets.token_urlsafe(24)
    t = User(username=data.role, full_name=data.ho_ten or ROLES[data.role], role=data.role,
             department="", staff_code="", password_hash=hash_password(mat_khau),
             active=True, must_change_password=False, ngoai_bien_che=True)
    db.add(t)
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{data.role}",
            after={"tao_tai_khoan_robot": data.role, "ngoai_bien_che": True})
    db.commit(); db.refresh(t)
    return {"message": f"Đã tạo tài khoản {t.username} cho {ROLES[data.role]}. Chép mật khẩu ngay – "
                       f"màn hình này là nơi duy nhất nó hiện ra.",
            "username": t.username, "mat_khau": mat_khau, "role": t.role,
            "luu_y": "Mật khẩu không lưu ở dạng đọc được. Mất thì đặt lại, không tra lại được."}
