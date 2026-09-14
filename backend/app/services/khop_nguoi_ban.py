# -*- coding: utf-8 -*-
"""KHỚP TÊN NGƯỜI BÁN trong kho quyết toán cũ với tài khoản VTOS.

BÀI TOÁN

Cột SALES trong 604 tệp Excel ghi tên người, không ghi mã nhân viên. Báo cáo doanh thu của VTOS thì
gắn vào `bookings.sales_id` – một khoá trỏ về tài khoản. Giữa hai thứ ấy phải có một bước dịch, và
bước ấy là tệp này.

ĐO TRÊN TOÀN KHO NGÀY 13/9/2026 (không phải ước lượng)

    18.162 dòng khách · 14.966 dòng có tên người bán (82%) · 145 tên khác nhau
    khớp đúng cả họ tên hoặc đuôi tên duy nhất : 13.662 dòng (91% số dòng có tên)
    trùng tên, nhiều người cùng ứng           :    286 dòng (6 tên)
    không có ai trong danh sách nhân sự       :  1.018 dòng (61 tên)

BỐN LUẬT, THEO ĐÚNG THỨ TỰ NÀY

  1. ĐÚNG CẢ HỌ TÊN thì khớp. "NGUYỄN NGỌC VÂN ANH" → đúng một người.
  2. ĐUÔI TÊN THEO TỪ khớp, VÀ CHỈ CÓ MỘT NGƯỜI ứng, thì khớp. Điều hành hay gõ tắt "UYỂN NHI" cho
     "Lê Thị Uyển Nhi"; đuôi tên là cách gọi thật trong công ty, bỏ đi thì mất 1.500 dòng.
  3. NHIỀU NGƯỜI cùng ứng mà CHỈ MỘT NGƯỜI Ở PHÒNG KINH DOANH thì khớp người ấy. Cột SALES ghi
     người BÁN: giữa một chị HCNS và một chị Team KD 4 cùng gọi tắt "Thùy Trang", người bán là chị
     Team KD 4. Luật này gỡ 5 trong 6 ca bí – chủ tịch chỉ ra ngày 13/9 rằng chúng không phải trùng
     người, chỉ là trùng cách gọi.
  4. Còn lại từ HAI NGƯỜI BÁN HÀNG trở lên thì KHÔNG KHỚP, và nêu cả hai ra cho người chọn.

Luật 4 là lý do tệp này tồn tại thay vì một dòng `startswith`. Máy chọn bừa một trong hai người cùng
tên là cộng doanh số của người này sang người kia, và không ai phát hiện ra, vì con số tổng công ty
vẫn đúng. Sai lặng lẽ trong bảng chỉ tiêu cá nhân là loại sai tệ nhất trong hệ này: nó ra tiền thưởng.

VÀ MỘT CÁI BẪY ĐÃ SẬP MỘT LẦN: khớp đuôi phải khớp THEO TỪ, không theo ký tự. Bản đầu khớp theo ký
tự, và "YẾN NHI" (yennhi) thành đuôi của "Lê Thị Uyển Nhi" (le-thi-uyennhi) – hai người khác hẳn
nhau mà nhìn bằng mắt không ai ngờ máy lẫn được. Theo từ thì ["yen","nhi"] ≠ ["uyen","nhi"].

KHÔNG ĐOÁN GẦN ĐÚNG. Không có khoảng cách Levenshtein, không có "giống 80%". Tên người là thứ chỉ
người mới xác nhận được; máy chỉ được phép khớp khi CHẮC CHẮN, còn lại đẩy ra màn hình cho người gán.
Gán một lần rồi thì bảng `kho_cu_nguoi_ban` nhớ mãi – lần nạp sau không phải gán lại.
"""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import select

from app.services.staff import name_key, strip_accents

# Rác thường gặp trong cột SALES: chữ ghi chú lọt vào, đầu mối ngoài công ty, ô đánh dấu.
# Không phải tên người thì không đi tìm tài khoản – nhưng VẪN ghi vào sổ để người ta nhìn thấy mà
# quyết, chứ không âm thầm vứt.
TOI_THIEU = 3
TOI_DA = 60


def chuan(ten: str) -> str:
    """Khoá khớp: bỏ dấu, bỏ khoảng trắng, hạ chữ thường. Dùng chung với `staff.name_key`."""
    return name_key(ten or "")


def tu(ten: str) -> list[str]:
    """Tên tách thành TỪ, đã bỏ dấu. Khớp đuôi phải khớp theo TỪ, không theo ký tự.

    Ca thật bắt được ngày 13/9/2026: khớp theo ký tự thì "YẾN NHI" (yennhi) là đuôi của
    "Lê Thị Uyển Nhi" (lethiuyennhi) — vì "uyennhi" kết thúc bằng "yennhi". Hai người khác nhau, và
    máy khớp nhầm mà không ai ngờ, vì nhìn bằng mắt thì hai cái tên rõ ràng khác. Theo TỪ thì
    ["yen","nhi"] ≠ ["uyen","nhi"], và người thật — Trần Thị Yến Nhi — mới là người được khớp.
    """
    s = strip_accents(ten or "").lower()
    return [w for w in re.split(r"[^a-z0-9]+", s) if w]


def _duoi_theo_tu(ho_ten: str, w: list[str]) -> bool:
    t = tu(ho_ten)
    return bool(w) and len(t) >= len(w) and t[-len(w):] == w


# Phòng có bán hàng. Dùng để GỠ THẾ BÍ khi một cách gọi tắt ứng với nhiều người: cột SALES trong
# tệp quyết toán ghi người BÁN, nên giữa một chị HCNS và một chị Team KD 4 cùng tên "Thùy Trang",
# người bán là chị Team KD 4. Chỉ gỡ được khi CÒN ĐÚNG MỘT người bán hàng; hai người bán hàng cùng
# tên thì vẫn phải để người chọn.
PHONG_BAN_HANG = ("kd_le", "kd_doan")


def _la_ban_hang(u) -> bool:
    return (getattr(u, "department", "") or "") in PHONG_BAN_HANG or bool(
        (getattr(u, "sales_group", "") or "").strip())


def danh_sach_tk(db) -> list:
    """Tài khoản đem ra khớp. Gọi MỘT LẦN rồi truyền vào `khop_mot` khi khớp cả lô 145 tên – không
    thì mỗi cái tên là một lần quét cả bảng tài khoản."""
    from app.models.core import User

    return db.scalars(select(User)).all()


def khop_mot(db, ten: str, ds: list | None = None) -> dict:
    """Khớp MỘT cái tên. KHÔNG ghi gì – dùng được cho cả xem trước lẫn lúc ghi.

    Khớp cả tài khoản đã tắt (`active=False`): người nghỉ tháng 6 vẫn phải nhận doanh số tháng 1–5
    của họ. Lọc theo `active` ở đây là làm mất đúng phần dữ liệu lịch sử mà lô này sinh ra để có.
    """
    t = (ten or "").strip()
    khoa = chuan(t)
    if not khoa or len(khoa) < TOI_THIEU or len(t) > TOI_DA:
        return {"ten": t, "khoa": khoa, "user_id": None, "cach_khop": "khong_phai_ten",
                "ung_vien": []}

    ds = danh_sach_tk(db) if ds is None else ds
    dung = [u for u in ds if chuan(u.full_name) == khoa]
    if len(dung) == 1:
        return {"ten": t, "khoa": khoa, "user_id": dung[0].id, "cach_khop": "dung_ten",
                "ung_vien": [{"id": dung[0].id, "ten": dung[0].full_name}]}
    if len(dung) > 1:
        # Hai tài khoản cùng đúng nguyên họ tên: hiếm, nhưng có – và máy vẫn không được chọn.
        return {"ten": t, "khoa": khoa, "user_id": None, "cach_khop": "trung_ten",
                "ung_vien": [{"id": u.id, "ten": u.full_name} for u in dung]}

    w = tu(t)
    duoi = [u for u in ds if _duoi_theo_tu(u.full_name, w)]
    if len(duoi) == 1:
        return {"ten": t, "khoa": khoa, "user_id": duoi[0].id, "cach_khop": "duoi_ten",
                "ung_vien": [{"id": duoi[0].id, "ten": duoi[0].full_name}]}
    if len(duoi) > 1:
        # Gỡ thế bí bằng PHÒNG: cột SALES ghi người bán, nên giữa một người HCNS và một người Team
        # KD cùng tên gọi tắt, người bán là người ở phòng kinh doanh. Chỉ gỡ khi còn ĐÚNG MỘT.
        ban = [u for u in duoi if _la_ban_hang(u)]
        if len(ban) == 1:
            return {"ten": t, "khoa": khoa, "user_id": ban[0].id, "cach_khop": "duoi_ten_phong_kd",
                    "ung_vien": [{"id": u.id, "ten": u.full_name} for u in duoi]}
        return {"ten": t, "khoa": khoa, "user_id": None, "cach_khop": "trung_ten",
                "ung_vien": [{"id": u.id, "ten": u.full_name} for u in duoi]}
    return {"ten": t, "khoa": khoa, "user_id": None, "cach_khop": "ngoai_danh_sach",
            "ung_vien": []}


def tra_so(db, ten: str) -> int | None:
    """Tài khoản của một tên, ƯU TIÊN sổ gán tay.

    Thứ tự này là cả nội dung của hàm: người đã gán tay thì máy KHÔNG được khớp đè lên. Nếu ai đó
    đã chọn "THÙY TRANG" là Quách Thị Thuỳ Trang thì tháng sau công ty tuyển thêm một Thùy Trang nữa
    cũng không được làm lung lay lựa chọn ấy.
    """
    from app.models.kho_cu import KhoCuNguoiBan

    khoa = chuan(ten)
    if not khoa:
        return None
    d = db.scalars(select(KhoCuNguoiBan).where(KhoCuNguoiBan.khoa_ten == khoa)).first()
    if d is not None and d.user_id:
        return d.user_id
    if d is not None and d.cach_khop in ("nguoi_gan", "trung_ten", "ngoai_danh_sach",
                                         "khong_phai_ten"):
        # Đã có người nhìn qua và để trống (hoặc máy đã kết luận là không khớp được): tôn trọng,
        # không âm thầm khớp lại ở lần nạp sau.
        return None
    return khop_mot(db, ten)["user_id"]


def ghi_so(db, dem: dict[str, int]) -> dict:
    """Ghi những cái tên vừa gặp vào sổ gán, kèm số dòng khách mang tên ấy.

    `dem` là {tên thô: số dòng}. Hàm KHÔNG đè lên lựa chọn của người: dòng đã có `nguoi_gan` thì chỉ
    cập nhật số dòng, không đụng vào `user_id`.
    """
    from app.models.kho_cu import KhoCuNguoiBan

    gop: dict[str, tuple[str, int]] = {}
    for ten, n in dem.items():
        k = chuan(ten)
        if not k:
            continue
        ten_cu, n_cu = gop.get(k, (ten, 0))
        gop[k] = (ten_cu, n_cu + n)

    ds_tk = danh_sach_tk(db)
    moi = sua = 0
    for khoa, (ten, n) in gop.items():
        d = db.scalars(select(KhoCuNguoiBan).where(KhoCuNguoiBan.khoa_ten == khoa)).first()
        if d is None:
            kq = khop_mot(db, ten, ds_tk)
            db.add(KhoCuNguoiBan(
                khoa_ten=khoa, ten_trong_tep=ten[:120], user_id=kq["user_id"],
                cach_khop=kq["cach_khop"],
                ung_vien="; ".join(f"{u['id']}:{u['ten']}" for u in kq["ung_vien"])[:400],
                so_dong=n, da_nghi=(kq["cach_khop"] == "ngoai_danh_sach")))
            moi += 1
            continue
        d.so_dong = n
        if d.cach_khop != "nguoi_gan" and not d.user_id:
            # Chưa ai gán tay: cho máy thử lại – danh sách nhân sự có thể vừa thêm người.
            kq = khop_mot(db, ten, ds_tk)
            d.user_id = kq["user_id"]
            d.cach_khop = kq["cach_khop"]
            d.ung_vien = "; ".join(f"{u['id']}:{u['ten']}" for u in kq["ung_vien"])[:400]
            d.da_nghi = kq["cach_khop"] == "ngoai_danh_sach"
        sua += 1
    db.flush()
    return {"ten_moi": moi, "ten_cu": sua, "tong_ten": len(gop)}


def gan_tay(db, khoa_ten: str, user_id: int | None, boi: str) -> dict:
    """Người chọn tài khoản cho một cái tên. `user_id=None` nghĩa là 'để trống có chủ ý'."""
    from app.models.core import User
    from app.models.kho_cu import KhoCuNguoiBan

    d = db.scalars(select(KhoCuNguoiBan).where(KhoCuNguoiBan.khoa_ten == khoa_ten)).first()
    if d is None:
        raise ValueError(f"chưa có tên nào mang khoá '{khoa_ten}' trong sổ gán")
    if user_id is not None and db.get(User, user_id) is None:
        raise ValueError(f"không có tài khoản số {user_id}")
    # KHÔNG chặn tài khoản đã tắt: người nghỉ tháng 6 vẫn phải nhận doanh số tháng 1–5 của họ.
    d.user_id = user_id
    d.cach_khop = "nguoi_gan"
    d.nguoi_gan = (boi or "")[:50]
    d.gan_luc = datetime.now()
    db.flush()
    return {"khoa_ten": d.khoa_ten, "ten_trong_tep": d.ten_trong_tep, "user_id": d.user_id,
            "cach_khop": d.cach_khop, "so_dong": d.so_dong}


def bang(db) -> dict:
    """Bảng cho màn hình gán: ai đã khớp, ai cần người chọn, và mỗi cái tên đáng bao nhiêu dòng."""
    from app.models.core import User
    from app.models.kho_cu import KhoCuNguoiBan

    ds = db.scalars(select(KhoCuNguoiBan).order_by(KhoCuNguoiBan.so_dong.desc())).all()
    ten_tk = {u.id: u.full_name for u in db.scalars(select(User)).all()}
    ra = [{"khoa_ten": d.khoa_ten, "ten_trong_tep": d.ten_trong_tep, "user_id": d.user_id,
           "ten_tai_khoan": ten_tk.get(d.user_id or 0, ""), "cach_khop": d.cach_khop,
           "ung_vien": [x for x in (d.ung_vien or "").split("; ") if x],
           "so_dong": d.so_dong, "nguoi_gan": d.nguoi_gan} for d in ds]
    xong = [r for r in ra if r["user_id"]]
    can = [r for r in ra if not r["user_id"] and r["cach_khop"] != "nguoi_gan"]
    return {
        "tong_ten": len(ra),
        "da_khop": len(xong), "dong_da_khop": sum(r["so_dong"] for r in xong),
        "can_gan": len(can), "dong_can_gan": sum(r["so_dong"] for r in can),
        "dong": ra,
        "ghi_chu": (
            f"{len(xong)} tên đã có tài khoản ({sum(r['so_dong'] for r in xong)} dòng khách); "
            f"{len(can)} tên còn chờ người gán ({sum(r['so_dong'] for r in can)} dòng). Dòng chưa "
            f"gán VẪN có doanh thu cho công ty, chỉ không tính vào chỉ tiêu của ai – vì cộng nhầm "
            f"cho người khác tệ hơn là để trống."),
    }
