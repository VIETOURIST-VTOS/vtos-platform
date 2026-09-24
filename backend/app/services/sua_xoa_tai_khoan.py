"""Sửa hồ sơ tài khoản, và xoá tài khoản đã trống — mục Tài khoản trùng (8.1.4).

ANH TUẤN CHỐT 24/9/2026, hai điều và chúng khác nhau:

  · SỬA và XOÁ hồ sơ người: chỉ HC-NS, Chủ tịch, Tổng giám đốc. KHÔNG có CNTT.
  · GỘP tài khoản trùng: thêm HC-NS vào ba vai cũ → chutich, tgd, hcns, cntt.

CNTT gộp được mà không sửa được, và đó là quyết định có chủ, không phải sót. Gộp là việc DỌN DỮ
LIỆU — chuyển các dòng đang trỏ vào tài khoản này sang tài khoản kia, không đổi một chữ nào trong
hồ sơ ai. Sửa họ tên hay mã nhân viên là đổi HỒ SƠ NHÂN SỰ, và hồ sơ nhân sự là của HC-NS.

XOÁ CHỈ KHI TÀI KHOẢN ĐÃ TRỐNG — ba điều kiện, không có ngoại lệ nào:

  1. Tài khoản phải ĐANG KHOÁ. Xoá thẳng một tài khoản đang mở là cắt ngang phiên làm việc của
     người đang dùng nó.
  2. Phải còn 0 DÒNG DỮ LIỆU trỏ tới. Đếm bằng chính bộ đếm của phép gộp, đọc từ siêu dữ liệu
     SQLAlchemy — nên cột khoá ngoại thứ 24 ai đó thêm tuần sau cũng tự được đếm.
  3. Không tự xoá chính mình.

VÌ SAO KHÔNG CHO XOÁ TÀI KHOẢN CÒN DỮ LIỆU, kể cả khi người bấm là Chủ tịch: đo 19/9/2026, cả 24
tài khoản trùng đều đang giữ booking, kể cả 13 cái đã bị khoá. Xoá là 129 booking mất chủ, báo cáo
doanh số hụt đúng phần ấy, và không ai biết vì sao. Đường đi đúng là GỘP TRƯỚC rồi mới xoá: gộp
chuyển hết dữ liệu sang tài khoản giữ, tài khoản bỏ về 0 dòng, lúc ấy nút xoá mới sáng.

BIA MỘ GHI TRƯỚC KHI XOÁ. Nhật ký nghiệp vụ ghi người làm bằng tên đăng nhập dạng chữ, nên xoá
xong thì mọi dòng nhật ký cũ trỏ tới một cái tên không tra ra ai. Bảng `tai_khoan_da_xoa` giữ lại
đúng phần ấy. Ghi bia mộ SAU khi đã xoá thì mất luôn dữ liệu cần ghi — thứ tự ở đây là bắt buộc.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.tai_khoan_da_xoa import TaiKhoanDaXoa
from app.services import rules as R
from app.services.gop_tai_khoan import cot_tro_toi_users
from app.db.session import Base

# Ô SỬA ĐƯỢC — cố ý NGẮN, và đúng bằng những cột `users` THỰC SỰ CÓ.
#
# Bản đầu của vòng này khai thêm `email` và `phone`; bảng `users` không có hai cột ấy. Thông tin
# liên hệ nằm ở hồ sơ nhân sự (`employees` / `employee_profiles`), là một sổ khác với cửa khác.
# Khai một ô không có cột là dựng một ô người dùng gõ vào rồi mất chữ mà không báo lỗi.
#
# VAI TRÒ, MẬT KHẨU và PHÂN CÔNG ĐƠN VỊ đều có cửa riêng ở màn hình Tài khoản & phân quyền và ở
# sơ đồ tổ chức. Mở lối thứ hai cho cùng một việc là hai chỗ phải rào, và quên một chỗ là hở —
# bài học đã ghi ở `/to-chuc-kd` và nhắc lại ở đây.
O_SUA = ("full_name", "staff_code", "department")
TEN_O = {"full_name": "Họ tên", "staff_code": "Mã nhân viên", "department": "Bộ phận"}


def _tom_tat(u: User) -> dict:
    return {"id": u.id, "tai_khoan": u.username, "ho_ten": u.full_name, "vai": u.role,
            "ma_nv": u.staff_code or "", "bo_phan": u.department or "",
            "dang_mo": bool(u.active)}


def dem_dong_tro_toi(db: Session, user_id: int) -> list[dict]:
    """Mỗi bảng đang giữ bao nhiêu dòng trỏ tới tài khoản này.

    ĐỌC TỪ SIÊU DỮ LIỆU, không chép tay danh sách cột — cùng bộ đếm với phép gộp. Chép tay là cầm
    chắc ngày ai đó thêm cột khoá ngoại thứ 24 và phép xoá lặng lẽ bỏ sót nó; bỏ sót ở đây nghĩa
    là xoá một tài khoản vẫn còn dữ liệu trỏ vào.
    """
    ra = []
    for bang, cot in cot_tro_toi_users():
        t = Base.metadata.tables[bang]
        n = db.execute(select(func.count()).select_from(t)
                       .where(t.c[cot] == user_id)).scalar_one()
        if n:
            ra.append({"bang": bang, "cot": cot, "so_dong": n})
    return sorted(ra, key=lambda x: -x["so_dong"])


def sua(db: Session, boi: User, uid: int, d: dict) -> dict:
    """Sửa ba ô nhận dạng. Vai trò, mật khẩu và phân công đơn vị KHÔNG sửa được ở đây — xem O_SUA."""
    u = db.get(User, uid)
    if u is None:
        raise ValueError(f"Không có tài khoản id {uid}.")

    ten = d.get("full_name")
    if ten is not None and not str(ten).strip():
        raise ValueError("Họ tên không được để trống.")

    ma = d.get("staff_code")
    if ma is not None and str(ma).strip():
        ma = str(ma).strip()
        # MÃ NHÂN VIÊN LÀ THỨ NHẬN RA NGƯỜI. Hai tài khoản cùng mã là hai bản ghi của một người mà
        # hệ thống lại coi là hai người — đúng cái mớ mà màn hình này sinh ra để dọn.
        trung = db.execute(select(User).where(User.staff_code == ma, User.id != uid)).scalars().first()
        if trung:
            raise ValueError(
                f"Mã nhân viên {ma} đã thuộc về {trung.full_name} ({trung.username}). "
                "Hai tài khoản cùng mã là hai bản ghi của một người — nếu đúng là một người thì "
                "dùng nút Gộp, đừng đặt trùng mã.")

    # CHỤP TRẠNG THÁI TRƯỚC KHI SỬA. Gọi sau khi đã gán thì cột "before" của nhật ký ghi lại đúng
    # trạng thái SAU — nhật ký nói dối còn tệ hơn không có. Bài học TC-78, nhắc lại để không lặp.
    truoc = {c: getattr(u, c) for c in O_SUA}
    doi = []
    for c in O_SUA:
        if c in d and d[c] is not None:
            moi = str(d[c]).strip()
            if moi != (getattr(u, c) or ""):
                doi.append(TEN_O[c])
            setattr(u, c, moi)

    if not doi:
        return {"id": u.id, "da_doi": [], "message": "Không có ô nào thay đổi."}

    R.audit(db, boi.username, boi.role, "sua_tai_khoan", f"user:{u.username}",
            before=truoc, after={c: getattr(u, c) for c in O_SUA})
    return {"id": u.id, "da_doi": doi,
            "message": f"Đã sửa {', '.join(doi).lower()} của {u.full_name}."}


def co_the_xoa(db: Session, boi: User, uid: int) -> dict:
    """Trả lời một câu: xoá được chưa, và nếu chưa thì vì sao. KHÔNG ghi gì."""
    u = db.get(User, uid)
    if u is None:
        raise ValueError(f"Không có tài khoản id {uid}.")
    dong = dem_dong_tro_toi(db, uid)
    tong = sum(x["so_dong"] for x in dong)

    can = []
    if u.id == boi.id:
        can.append("Không tự xoá tài khoản của chính mình.")
    if u.active:
        can.append("Tài khoản đang MỞ. Khoá nó lại trước — xoá thẳng một tài khoản đang mở là "
                   "cắt ngang phiên làm việc của người đang dùng.")
    if tong:
        dau = ", ".join(f"{x['bang']} ({x['so_dong']} dòng)" for x in dong[:5])
        can.append(f"Còn {tong} dòng dữ liệu trỏ tới tài khoản này: {dau}"
                   f"{' …' if len(dong) > 5 else ''}. Dùng nút GỘP để chuyển hết sang tài khoản "
                   "giữ lại, xong thì nút xoá mới sáng.")
    return {
        "tai_khoan": _tom_tat(u),
        "xoa_duoc": not can,
        "can_tro": can,
        "tong_dong_con_lai": tong,
        "chi_tiet": dong,
        "ghi_chu": ("Xoá là vĩnh viễn và không có nút hoàn lại. Hệ thống giữ một dòng bia mộ "
                    "(tên đăng nhập → họ tên) để nhật ký nghiệp vụ cũ còn tra ra người, nhưng "
                    "tài khoản thì không dựng lại được."),
    }


def xoa(db: Session, boi: User, uid: int, ly_do: str, xac_nhan: bool = False) -> dict:
    """Xoá vĩnh viễn một tài khoản đã trống. Ghi bia mộ TRƯỚC khi xoá."""
    kq = co_the_xoa(db, boi, uid)
    if not kq["xoa_duoc"]:
        raise ValueError(" ".join(kq["can_tro"]))
    if not (ly_do or "").strip():
        raise ValueError("Xoá tài khoản phải ghi lý do — đây là việc không hoàn lại được.")
    if not xac_nhan:
        return {**kq, "da_xoa": False,
                "ghi_chu_them": "Đây là bản xem trước. Bấm xác nhận thì tài khoản mới bị xoá."}

    u = db.get(User, uid)
    truoc = _tom_tat(u)

    # DẤU VẾT CỦA MỘT LẦN GỘP TRƯỚC ĐÓ. `gop()` đổi tên thành "... (đã gộp vào <tài khoản>)", nên
    # đọc ngược ra được tài khoản giữ. Không suy được thì để rỗng — đoán một cái tên vào đây là
    # làm hỏng đúng thứ bảng bia mộ sinh ra để giữ.
    gop_vao = ""
    if "(đã gộp vào " in (u.full_name or ""):
        gop_vao = u.full_name.rsplit("(đã gộp vào ", 1)[1].rstrip(") ").strip()[:50]

    db.add(TaiKhoanDaXoa(
        user_id_cu=u.id, tai_khoan=u.username, ho_ten=u.full_name,
        ma_nv=(u.staff_code or "")[:30], vai=(u.role or "")[:30],
        da_gop_vao=gop_vao, ly_do=ly_do.strip(), xoa_boi=boi.username))
    db.flush()

    R.audit(db, boi.username, boi.role, "xoa_tai_khoan", f"user:{u.username}",
            before=truoc, after={"ly_do": ly_do.strip(), "da_gop_vao": gop_vao,
                                 "bia_mo": "tai_khoan_da_xoa"})
    db.delete(u)
    return {"da_xoa": True, "tai_khoan": truoc,
            "message": f"Đã xoá {truoc['tai_khoan']}. Một dòng bia mộ đã được ghi lại để nhật ký "
                       "cũ còn tra ra người."}


def bia_mo(db: Session, tim: str = "") -> dict:
    """Danh sách tài khoản đã xoá. Bảng này KHÔNG có cửa xoá — cố ý, xem models/tai_khoan_da_xoa."""
    q = select(TaiKhoanDaXoa).order_by(TaiKhoanDaXoa.xoa_luc.desc())
    if tim.strip():
        k = f"%{tim.strip()}%"
        q = q.where((TaiKhoanDaXoa.tai_khoan.ilike(k)) | (TaiKhoanDaXoa.ho_ten.ilike(k)))
    rows = [{"id": b.id, "tai_khoan": b.tai_khoan, "ho_ten": b.ho_ten, "ma_nv": b.ma_nv,
             "vai": b.vai, "da_gop_vao": b.da_gop_vao, "ly_do": b.ly_do,
             "xoa_boi": b.xoa_boi,
             "xoa_luc": b.xoa_luc.isoformat(timespec="seconds") if b.xoa_luc else ""}
            for b in db.execute(q.limit(500)).scalars()]
    return {"rows": rows, "tong": len(rows),
            "ghi_chu": ("Mỗi dòng ở đây là một tài khoản đã bị xoá. Bảng này không có nút xoá, và "
                        "đó là chủ ý: nhật ký nghiệp vụ ghi người làm bằng tên đăng nhập dạng chữ, "
                        "nên đây là chỗ duy nhất tra ngược được một cái tên đã biến mất.")}
