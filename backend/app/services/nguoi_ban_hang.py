"""Ai được bán hàng — nhân viên nào, và đối tác nào.

VẤN ĐỀ TỆP NÀY SINH RA ĐỂ GIẢI

Trước vòng này, "người của khối Kinh doanh" là một tuple bốn vai VIẾT CHẾT TRONG MÃ. Hướng dẫn viên
bán được một chuyến, Điều hành bán thêm một dịch vụ — hai việc có thật, đo được trên máy 19/9/2026
(Điều hành 4,24 tỷ, Visa 2,64 tỷ trong chín tháng) — nhưng muốn hệ thống ghi nhận thì phải sửa mã.
Một danh sách người mà mỗi lần thêm bớt phải gọi lập trình viên thì sớm muộn sẽ lệch với thực tế, và
lệch âm thầm.

Anh Tuấn 19/9/2026: "ngoài khối kinh doanh em mở thêm cho nhân viên sau này nhập tay vào, ví dụ hdv,
dh... cũng được quyền bán khách".

Nên "ai được bán" thành DỮ LIỆU: một ô tick trên từng người, Hành chính – Nhân sự bật. Vai trò đăng
nhập giữ nguyên — một hướng dẫn viên vẫn là hướng dẫn viên, chỉ thêm quyền bán.

BỐN NGĂN NGƯỜI BÁN, RỜI NHAU
    khoi_kd     nhân viên khối Kinh doanh (gd_kd, tp_kd, tn_kd, nv_kd) — vào chỉ tiêu
    ngoai_khoi  người bộ phận khác đã bật ô "được bán hàng" — không vào chỉ tiêu, trừ khi được giao riêng
    doi_tac     đối tác ngoài công ty (bảng doi_tac_ban_hang) — không vào chỉ tiêu
    chua_ro     chưa gán được ai — không vào chỉ tiêu

CHỖ DỄ SAI NHẤT: `ngoai_khoi` KHÁC `chua_ro`. Một bên là đã biết ai bán và người ấy được phép bán;
bên kia là chưa biết. Gộp làm một thì doanh thu của Điều hành và Visa biến mất khỏi mọi câu hỏi.

VAI KHỐI KINH DOANH VẪN VIẾT TRONG MÃ, VÀ ĐÓ LÀ CHỦ Ý. Bốn vai ấy quyết định ai bị GIAO CHỈ TIÊU —
một quyết định về cơ cấu, không phải một lựa chọn hằng ngày. Cái thành dữ liệu là quyền BÁN, không
phải nghĩa vụ ĐẠT CHỈ TIÊU. Trộn hai thứ là bật ô tick cho một tài xế rồi tự nhiên tài xế ấy xuất
hiện trong bảng xếp hạng kinh doanh.
"""
from datetime import date

from sqlalchemy import select

from app.models.core import User
from app.models.doi_tac_ban_hang import LOAI, NHAN_LOAI, DoiTacBanHang
from app.services import rules as R

# Vai được giao chỉ tiêu kinh doanh. Xem đoạn cuối lời mở đầu: đây là cơ cấu, không phải ô tick.
VAI_KHOI_KD = ("gd_kd", "tp_kd", "tn_kd", "nv_kd")

NGAN = ("khoi_kd", "ngoai_khoi", "doi_tac", "chua_ro")


def ngan_cua_nguoi(u: User | None) -> str:
    """Người bán này thuộc ngăn nào. `None` = không tra ra ai."""
    if u is None:
        return "chua_ro"
    if u.role in VAI_KHOI_KD:
        return "khoi_kd"
    return "ngoai_khoi" if getattr(u, "duoc_ban_hang", False) else "chua_ro"


# ─────────────────────────────── Quyền bán của nhân viên ───────────────────────────────

def dat_quyen_ban(db, boi: User, user_id: int, duoc: bool, ly_do: str) -> User:
    """Bật/tắt quyền bán hàng cho một người ngoài khối Kinh doanh."""
    u = db.get(User, user_id)
    if u is None:
        raise ValueError("Không tìm thấy tài khoản.")
    if not (ly_do or "").strip():
        raise ValueError("Bật hay tắt quyền bán đều phải ghi lý do — đây là thứ đổi doanh số của một người.")
    if u.role in VAI_KHOI_KD:
        raise ValueError(
            f"{u.full_name} đã thuộc khối Kinh doanh (vai {u.role!r}) nên bán hàng là việc đương nhiên. "
            "Ô này chỉ dành cho người bộ phận khác.")
    truoc = bool(u.duoc_ban_hang)
    if truoc == duoc:
        raise ValueError("Không có gì thay đổi — ô này đang ở đúng trạng thái ấy rồi.")
    u.duoc_ban_hang = duoc
    R.audit(db, boi.username, boi.role, "dat_quyen_ban_hang", f"user:{u.username}",
            before={"duoc_ban_hang": truoc}, after={"duoc_ban_hang": duoc, "ly_do": ly_do.strip()})
    return u


def ai_duoc_ban(db) -> dict:
    """Ba nhóm: khối Kinh doanh, người ngoài khối đã bật, và người ngoài khối chưa bật."""
    khoi, ngoai_bat, ngoai_tat = [], [], []
    for u in db.execute(select(User).where(User.active == True).order_by(User.full_name)).scalars():
        d = {"user_id": u.id, "ho_ten": u.full_name, "tai_khoan": u.username,
             "vai": u.role, "ma_nv": u.staff_code or ""}
        if u.role in VAI_KHOI_KD:
            khoi.append(d)
        elif u.duoc_ban_hang:
            ngoai_bat.append(d)
        else:
            ngoai_tat.append(d)
    return {"khoi_kinh_doanh": khoi, "ngoai_khoi_duoc_ban": ngoai_bat,
            "ngoai_khoi_chua_bat": ngoai_tat,
            "ghi_chu": "Khối Kinh doanh bán hàng là đương nhiên, không cần bật. Ô tick chỉ dành cho "
                       "người bộ phận khác — hướng dẫn viên, điều hành, visa."}


# ─────────────────────────────── Đối tác ───────────────────────────────

def tao_doi_tac(db, boi: User, ma: str, ten: str, loai: str = "ghep_le",
                lien_he: str = "", dien_thoai: str = "", ma_so_thue: str = "",
                hieu_luc_tu: date | None = None, ghi_chu: str = "") -> DoiTacBanHang:
    ma = (ma or "").strip().upper()
    ten = (ten or "").strip()
    if not ma:
        raise ValueError("Thiếu mã đối tác.")
    if not ten:
        raise ValueError("Thiếu tên đối tác.")
    if loai not in LOAI:
        raise ValueError(f"Loại hợp tác không hợp lệ: {loai!r}. Chỉ có {', '.join(LOAI)}.")
    if db.execute(select(DoiTacBanHang).where(DoiTacBanHang.ma == ma)).scalar_one_or_none():
        raise ValueError(f"Mã {ma!r} đã có đối tác khác dùng.")
    # Chặn đúng cái lách đã xảy ra: một dòng `users` mang tên đối tác. Nếu tên này đã tồn tại dưới
    # dạng tài khoản thì báo ra, để người khai biết mà đi dọn chứ không tạo thêm bản thứ hai.
    trung = db.execute(select(User).where(User.full_name.ilike(ten))).scalars().first()
    dt = DoiTacBanHang(ma=ma, ten=ten, loai=loai, lien_he=lien_he.strip(),
                       dien_thoai=dien_thoai.strip(), ma_so_thue=ma_so_thue.strip(),
                       hieu_luc_tu=hieu_luc_tu or date.today(), ghi_chu=ghi_chu.strip(), boi=boi.username)
    db.add(dt)
    db.flush()
    R.audit(db, boi.username, boi.role, "tao_doi_tac_ban_hang", f"doi_tac:{dt.ma}",
            after={"ma": dt.ma, "ten": dt.ten, "loai": dt.loai,
                   "trung_ten_tai_khoan": trung.username if trung else None})
    return dt


def dong_doi_tac(db, boi: User, doi_tac_id: int, den_ngay: date, ly_do: str) -> DoiTacBanHang:
    """Dừng hợp tác. KHÔNG XOÁ — xem quyết định BA ở đầu models/doi_tac_ban_hang.py."""
    dt = db.get(DoiTacBanHang, doi_tac_id)
    if dt is None:
        raise ValueError("Không tìm thấy đối tác.")
    if not (ly_do or "").strip():
        raise ValueError("Dừng hợp tác phải ghi lý do.")
    if den_ngay < dt.hieu_luc_tu:
        raise ValueError("Ngày dừng không được trước ngày bắt đầu hợp tác.")
    truoc = dt.hieu_luc_den.isoformat() if dt.hieu_luc_den else None
    dt.hieu_luc_den = den_ngay
    dt.ghi_chu = (dt.ghi_chu + "\n" if dt.ghi_chu else "") + f"Dừng {den_ngay}: {ly_do.strip()}"
    R.audit(db, boi.username, boi.role, "dong_doi_tac_ban_hang", f"doi_tac:{dt.ma}",
            before={"hieu_luc_den": truoc},
            after={"hieu_luc_den": den_ngay.isoformat(), "ly_do": ly_do.strip()})
    return dt


def danh_sach_doi_tac(db, ngay: date | None = None) -> list[dict]:
    ngay = ngay or date.today()
    ra = []
    for dt in db.execute(select(DoiTacBanHang).order_by(DoiTacBanHang.ma)).scalars():
        ra.append({"id": dt.id, "ma": dt.ma, "ten": dt.ten, "loai": dt.loai,
                   "loai_nhan": NHAN_LOAI.get(dt.loai, dt.loai),
                   "lien_he": dt.lien_he, "dien_thoai": dt.dien_thoai, "ma_so_thue": dt.ma_so_thue,
                   "hieu_luc_tu": dt.hieu_luc_tu.isoformat(),
                   "hieu_luc_den": dt.hieu_luc_den.isoformat() if dt.hieu_luc_den else None,
                   "con_hop_tac": dt.dang_hieu_luc(ngay), "ghi_chu": dt.ghi_chu})
    return ra
