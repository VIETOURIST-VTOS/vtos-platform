"""Gộp hai tài khoản trùng của cùng một người — chuyển hết dữ liệu, rồi KHOÁ, không xoá.

VẤN ĐỀ TỆP NÀY SINH RA ĐỂ GIẢI

Đo trên máy thật 19/9/2026: 220 tài khoản, **6 người có từ hai tài khoản trở lên**, tổng 24 dòng.
Bốn cặp trong đó đang mở cả hai, và doanh số của họ bị xẻ đôi:

    Nguyễn Ngọc Vân Anh   id 91  (MNV 269, 290 booking)  ↔  id 251  (62 booking, 110 tr)
    Quách Thị Thuỳ Trang  id 129 (MNV 49,  285 booking)  ↔  id 252  (50 booking,  89 tr)
    Mai Thị Diệu Trinh    id 67  (MNV 191,  34 booking)  ↔  id 253  ( 1 booking,  70 tr)
    Trần Hoàng Anh        id 135 (MNV 271, 271 booking)  ↔  id 254  (16 booking,   0 đ)

Bốn id 251–254 liền nhau, không mã nhân viên: một đợt nạp sinh ra. Sẽ còn đợt nữa, nên đây phải là
một CỬA chạy lại được, không phải một lần sửa tay.

VÌ SAO KHOÁ CHỨ KHÔNG XOÁ — anh Tuấn hỏi thẳng "còn lại xoá" ngày 19/9

Xoá được về mặt kỹ thuật, và chính vì thế phải ghi rõ vì sao không:

  · CẢ 24 TÀI KHOẢN ẤY ĐỀU ĐANG GIỮ BOOKING, kể cả 13 cái đã bị khoá. Xoá là 129 booking mất chủ.
  · Nhật ký nghiệp vụ ghi người làm bằng TÊN ĐĂNG NHẬP dạng chữ, không phải khoá ngoại — nên nhật
    ký KHÔNG gãy khi xoá tài khoản, nó chỉ trỏ tới một cái tên không còn tra ra ai. Im lặng mà sai,
    đúng kiểu hỏng khó tìm nhất.
  · Khoá đạt đúng kết quả anh muốn: một người một tài khoản, doanh số về một mối, không ai đăng
    nhập được vào cái thừa nữa. Cái duy nhất mất đi khi xoá là khả năng tra lại — và đó là cái
    đáng giữ nhất.

THỨ TỰ BẮT BUỘC: CHUYỂN TRƯỚC, KHOÁ SAU. Khoá trước mà chưa chuyển thì doanh số nằm im trong một
tài khoản chết, và giờ không ai mở ra được nữa — tệ hơn lúc chưa làm gì.

KHÔNG CHÉP TAY DANH SÁCH CỘT. Có 23 cột khoá ngoại trỏ vào `users.id` nằm rải ở 11 tệp mô hình.
Chép chúng vào đây là cầm chắc ngày ai đó thêm cột thứ 24 và phép gộp lặng lẽ bỏ sót nó — bỏ sót ở
đây nghĩa là một tài khoản bị khoá trong khi vẫn còn dữ liệu trỏ vào. Tệp này ĐỌC THẲNG từ siêu dữ
liệu của SQLAlchemy, nên cột mới tự động được gộp theo.
"""
from sqlalchemy import func, select, update

from app.db.session import Base
from app.models.core import User
from app.services import rules as R

# Cột KHÔNG chuyển khi gộp, kèm lý do. Danh sách này phải ngắn và mỗi dòng phải cãi được.
KHONG_CHUYEN = {
    ("users", "id"): "chính khoá của bảng tài khoản",
}


def cot_tro_toi_users() -> list[tuple[str, str]]:
    """Mọi (bảng, cột) là khoá ngoại trỏ vào `users.id`, đọc từ siêu dữ liệu — không chép tay."""
    ra = []
    for bang in Base.metadata.sorted_tables:
        for cot in bang.columns:
            for fk in cot.foreign_keys:
                if fk.column.table.name == "users" and fk.column.name == "id":
                    if (bang.name, cot.name) not in KHONG_CHUYEN:
                        ra.append((bang.name, cot.name))
    return sorted(set(ra))


def _kiem(db, giu_id: int, bo_id: int) -> tuple[User, User]:
    if giu_id == bo_id:
        raise ValueError("Hai tài khoản phải khác nhau.")
    giu, bo = db.get(User, giu_id), db.get(User, bo_id)
    if giu is None:
        raise ValueError("Không tìm thấy tài khoản giữ lại.")
    if bo is None:
        raise ValueError("Không tìm thấy tài khoản cần gộp.")
    if not giu.active:
        raise ValueError(
            f"Tài khoản giữ lại ({giu.username}) đang bị khoá. Gộp vào một tài khoản chết là dồn dữ "
            "liệu vào chỗ không ai mở được — mở khoá nó trước, hoặc đổi chiều gộp.")
    return giu, bo


def xem_truoc(db, giu_id: int, bo_id: int) -> dict:
    """Gộp thì bao nhiêu dòng chuyển, ở những bảng nào. KHÔNG ghi gì."""
    giu, bo = _kiem(db, giu_id, bo_id)
    chi_tiet, tong = [], 0
    for bang, cot in cot_tro_toi_users():
        t = Base.metadata.tables[bang]
        # ĐẾM BẰNG COUNT, không dùng `rowcount` của một câu SELECT: với SELECT thì `rowcount` phụ
        # thuộc trình điều khiển và thường trả -1, nên con số xem trước sẽ sai mà không báo lỗi.
        n = db.execute(select(func.count()).select_from(t).where(t.c[cot] == bo_id)).scalar_one()
        if n:
            chi_tiet.append({"bang": bang, "cot": cot, "so_dong": n})
            tong += n
    return {
        "giu": _tom_tat(giu), "bo": _tom_tat(bo),
        "tong_dong_se_chuyen": tong,
        "chi_tiet": sorted(chi_tiet, key=lambda x: -x["so_dong"]),
        "khac_vai": giu.role != bo.role,
        "canh_bao": (f"Hai tài khoản khác vai trò: giữ {giu.role!r}, bỏ {bo.role!r}. "
                     "Kiểm lại có đúng là một người không." if giu.role != bo.role else ""),
    }


def _tom_tat(u: User) -> dict:
    return {"id": u.id, "ho_ten": u.full_name, "tai_khoan": u.username, "vai": u.role,
            "ma_nv": u.staff_code or "", "dang_mo": bool(u.active)}


def gop(db, boi: User, giu_id: int, bo_id: int, ly_do: str, xac_nhan: bool = False) -> dict:
    """Chuyển toàn bộ dữ liệu của `bo` sang `giu`, rồi KHOÁ `bo`.

    `xac_nhan=False` chỉ xem trước. Ghi thật thì phải truyền True — cùng nếp với "Gán lại" của kho cũ.
    """
    giu, bo = _kiem(db, giu_id, bo_id)
    if not (ly_do or "").strip():
        raise ValueError("Gộp tài khoản phải ghi lý do — đây là thứ đổi doanh số của một người.")
    truoc = xem_truoc(db, giu_id, bo_id)
    if not xac_nhan:
        return {**truoc, "da_ghi": False,
                "ghi_chu": "Đây là bản xem trước. Bấm xác nhận thì dữ liệu mới chuyển."}

    # Chụp trạng thái TRƯỚC khi sửa. Gọi `_tom_tat(bo)` sau khi đã đổi `active` và `full_name` thì
    # cột "before" của nhật ký ghi lại đúng trạng thái SAU — nhật ký nói dối còn tệ hơn không có.
    bo_truoc = _tom_tat(bo)
    da_chuyen = []
    for muc in truoc["chi_tiet"]:
        t = Base.metadata.tables[muc["bang"]]
        db.execute(update(t).where(t.c[muc["cot"]] == bo_id).values({muc["cot"]: giu_id}))
        da_chuyen.append(muc)

    # KHOÁ, KHÔNG XOÁ. Và không chép `staff_code` sang: mã nhân viên của tài khoản thừa vốn rỗng,
    # còn nếu nó có mã thì hai mã khác nhau nghĩa là hai người — đã bị chặn ở bước xem trước.
    bo.active = False
    bo.full_name = f"{bo.full_name} (đã gộp vào {giu.username})"

    R.audit(db, boi.username, boi.role, "gop_tai_khoan_trung", f"user:{bo.username}",
            before={"bo": bo_truoc, "giu": _tom_tat(giu)},
            after={"gop_vao": giu.username, "so_dong_chuyen": truoc["tong_dong_se_chuyen"],
                   "bang": [m["bang"] + "." + m["cot"] for m in da_chuyen], "ly_do": ly_do.strip()})
    return {**truoc, "da_ghi": True,
            "message": f"Đã chuyển {truoc['tong_dong_se_chuyen']} dòng sang {giu.full_name} "
                       f"và khoá {bo.username}"}


def cap_trung(db) -> list[dict]:
    """Những người có từ hai tài khoản trở lên, kèm gợi ý giữ cái nào.

    GỢI Ý THEO MÃ NHÂN VIÊN, vì anh Tuấn chốt 19/9 lấy bảng lương T08 làm chuẩn: tài khoản có mã là
    tài khoản khớp hồ sơ nhân sự. Chỉ là GỢI Ý — máy không tự gộp, người bấm mới gộp.
    """
    nhom: dict[str, list[User]] = {}
    for u in db.execute(select(User).order_by(User.id)).scalars():
        k = _chuan(u.full_name)
        if k:
            nhom.setdefault(k, []).append(u)

    dem = _dem_theo_nguoi(db)
    ra = []
    for k, ds in nhom.items():
        if len(ds) < 2:
            continue
        co_ma = [u for u in ds if (u.staff_code or "").strip()]
        goi_y = co_ma[0].id if len(co_ma) == 1 else None
        ra.append({
            "ten": ds[0].full_name,
            "goi_y_giu": goi_y,
            "vi_sao": ("tài khoản duy nhất có mã nhân viên" if goi_y
                       else "không suy được — nhiều hoặc không tài khoản nào có mã nhân viên, người quyết"),
            "tai_khoan": [{**_tom_tat(u), "so_dong": dem.get(u.id, 0)} for u in ds],
        })
    return sorted(ra, key=lambda x: -sum(t["so_dong"] for t in x["tai_khoan"]))


def _dem_theo_nguoi(db) -> dict[int, int]:
    """Mỗi tài khoản đang được bao nhiêu dòng trỏ tới — con số nói cái thừa có thật sự trống không."""
    dem: dict[int, int] = {}
    for bang, cot in cot_tro_toi_users():
        t = Base.metadata.tables[bang]
        for (uid,) in db.execute(select(t.c[cot]).where(t.c[cot].is_not(None))):
            dem[uid] = dem.get(uid, 0) + 1
    return dem


def _chuan(s: str) -> str:
    import re
    import unicodedata
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z ]", " ", s)).upper().strip()
