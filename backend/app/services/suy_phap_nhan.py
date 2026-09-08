"""Suy pháp nhân chủ quản cho TÀI KHOẢN từ hồ sơ nhân sự (08/9/2026).

Vì sao có tệp này. Đo trên hệ thống thật sau khi P6 lên: 109 trong 110 nhân sự đang làm việc đã có
pháp nhân chủ quản, nhưng chỉ 1 trong 116 tài khoản đang hoạt động có. Nghĩa là phạm vi pháp nhân
theo phiên đăng nhập – thứ vừa xây xong – hôm nay chỉ thật sự giới hạn đúng một người, và 115 người
còn lại vẫn thấy toàn bộ dữ liệu của cả tập đoàn.

Chỗ trống ấy KHÔNG phải chỗ trống của quyết định: người quản trị đã quyết rồi, quyết ở hồ sơ nhân
sự. Nó chỉ chưa được chép sang tài khoản. Bắt ai đó ngồi gán tay 115 lần trên màn hình là cách chắc
chắn để việc này không bao giờ xong – và một hàng rào chưa bật thì bằng không có hàng rào.

BỐN ĐIỀU MODULE NÀY KHÔNG LÀM, và mỗi điều là một cách hỏng thật:

1. **Không đoán.** Chỉ suy khi tài khoản nối được với MỘT hồ sơ nhân sự và hồ sơ ấy CÓ pháp nhân.
   Không suy từ phòng ban, không suy từ vai trò, không mặc định về công ty mẹ. Tài khoản không suy
   được thì nằm nguyên trong danh sách "phải gán tay", kèm lý do vì sao không suy được.

2. **Không đè.** Tài khoản đã có pháp nhân thì không đụng tới, kể cả khi hồ sơ nói khác. Gán tay là
   quyết định của con người; suy tự động là phỏng theo dữ liệu. Cái sau không được ghi đè cái trước.
   Chỗ hai bên nói khác nhau được BÁO RA thành một mục riêng để người quản trị xem, chứ không tự xử.

3. **Không ghi khi chưa ai nhìn.** Hàm này chạy hai lượt: xem trước rồi mới ghi. Ghi 115 dòng vào
   bảng tài khoản mà không ai nhìn trước danh sách là đúng loại việc mà lúc sai thì không ai biết
   sai ở đâu.

4. **Không im lặng.** Mỗi lần ghi để lại một dòng nhật ký kèm số lượng và danh sách mã nhân viên.

Nối tài khoản với hồ sơ theo ĐÚNG thứ tự mà phần còn lại của hệ thống đang dùng (xem hr.phieu_luong):
user_id trước, mã nhân viên sau. Hai đường này lệch nhau ở vài tài khoản là chuyện có thật, nên nối
sai thứ tự là gán pháp nhân của người khác cho một người.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User, Company, ROLES
from app.models.hr import Employee
from app.services import rules as R


def _ho_so_cua(db: Session) -> tuple[dict, dict]:
    """Hai bảng tra: theo user_id, và theo mã nhân viên. Chỉ lấy hồ sơ ĐANG LÀM VIỆC.

    Hồ sơ đã nghỉ vẫn giữ pháp nhân cũ; suy từ nó là gán pháp nhân theo một quan hệ đã chấm dứt.
    """
    theo_uid, theo_ma = {}, {}
    for e in db.execute(select(Employee)).scalars():
        if not e.active:
            continue
        if e.user_id:
            theo_uid[e.user_id] = e
        if e.code:
            theo_ma.setdefault(e.code, e)
    return theo_uid, theo_ma


def _noi(u: User, theo_uid: dict, theo_ma: dict):
    """Hồ sơ của một tài khoản, và cách nối được ra nó."""
    e = theo_uid.get(u.id)
    if e is not None:
        return e, "user_id"
    if u.staff_code:
        e = theo_ma.get(u.staff_code)
        if e is not None:
            return e, "ma_nhan_vien"
    return None, ""


def xem_truoc(db: Session) -> dict:
    """Suy được những gì, và không suy được cái gì vì lý do gì. KHÔNG ghi một dòng nào.

    Trả về bốn nhóm tách rời, cố ý không gộp thành một con số "tiến độ": ba nhóm sau là ba loại việc
    khác nhau, cần ba người khác nhau xử lý.
    """
    ten_cty = {c.id: c.code for c in db.execute(select(Company)).scalars()}
    theo_uid, theo_ma = _ho_so_cua(db)

    suy_duoc, khong_suy_duoc, da_co, lech = [], [], [], []
    for u in db.execute(select(User).order_by(User.username)).scalars():
        if not u.active:
            continue
        e, cach = _noi(u, theo_uid, theo_ma)
        dong = {"user_id": u.id, "username": u.username, "full_name": u.full_name,
                "role_name": ROLES.get(u.role, u.role), "department": u.department,
                "staff_code": u.staff_code, "ho_so": e.code if e else "", "noi_bang": cach}

        if u.company_id:
            dong["company_id"] = u.company_id
            dong["company"] = ten_cty.get(u.company_id, "")
            if e is not None and e.company_id and e.company_id != u.company_id:
                dong["ho_so_company"] = ten_cty.get(e.company_id, "")
                lech.append(dong)          # người xem quyết, module này không tự xử
            else:
                da_co.append(dong)
            continue

        if e is None:
            dong["ly_do"] = ("Tài khoản không nối được với hồ sơ nhân sự nào đang làm việc"
                             + (f" (mã {u.staff_code} không có trong danh sách)" if u.staff_code
                                else " và không có mã nhân viên"))
            khong_suy_duoc.append(dong)
        elif not e.company_id:
            dong["ly_do"] = f"Hồ sơ {e.code} cũng chưa có pháp nhân – phải gán ở màn hình Nhân sự trước"
            khong_suy_duoc.append(dong)
        else:
            dong["company_id"] = e.company_id
            dong["company"] = ten_cty.get(e.company_id, "")
            suy_duoc.append(dong)

    return {
        "suy_duoc": suy_duoc,
        "khong_suy_duoc": khong_suy_duoc,
        "da_co": da_co,
        "lech_voi_ho_so": lech,
        "dem": {"suy_duoc": len(suy_duoc), "khong_suy_duoc": len(khong_suy_duoc),
                "da_co": len(da_co), "lech_voi_ho_so": len(lech)},
        "ghi_chu": ("Chỉ suy khi tài khoản nối được với một hồ sơ nhân sự đang làm việc VÀ hồ sơ ấy đã "
                    "có pháp nhân. Không suy từ phòng ban hay vai trò, không mặc định về công ty mẹ. "
                    "Tài khoản đã có pháp nhân thì không bị ghi đè – chỗ lệch với hồ sơ được liệt kê "
                    "riêng để người quản trị xem, không tự sửa."),
    }


def ap_dung(db: Session, u: User, chi_nhung_id: list[int] | None = None) -> dict:
    """Ghi pháp nhân đã suy vào tài khoản. Chạy lại nhiều lần vẫn ra cùng kết quả.

    chi_nhung_id: chỉ ghi cho những tài khoản này (khi người quản trị bỏ tick vài dòng ở bảng xem
    trước). Bỏ trống là ghi cho toàn bộ nhóm suy được.
    """
    xem = xem_truoc(db)
    can = xem["suy_duoc"]
    if chi_nhung_id is not None:
        cho_phep = set(chi_nhung_id)
        can = [d for d in can if d["user_id"] in cho_phep]
    if not can:
        return {"da_ghi": 0, "rows": [], "message": "Không có tài khoản nào suy được pháp nhân từ hồ sơ."}

    for d in can:
        t = db.get(User, d["user_id"])
        if t is None or t.company_id:      # đọc lại ngay trước khi ghi: giữa lúc xem và lúc bấm có
            continue                       # thể đã có người gán tay, và gán tay thắng
        t.company_id = d["company_id"]

    R.audit(db, u.username, u.role, "suy_phap_nhan_tai_khoan_tu_ho_so", f"user:{len(can)}",
            after={"so_tai_khoan": len(can),
                   "ma_nhan_vien": [d["ho_so"] for d in can],
                   "theo_phap_nhan": {d["company"]: sum(1 for x in can if x["company"] == d["company"])
                                      for d in can}})
    db.commit()
    return {"da_ghi": len(can), "rows": can,
            "message": f"Đã gán pháp nhân cho {len(can)} tài khoản, suy từ hồ sơ nhân sự",
            "con_lai": xem["dem"]["khong_suy_duoc"]}
