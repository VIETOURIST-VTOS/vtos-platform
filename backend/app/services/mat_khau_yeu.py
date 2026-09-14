# -*- coding: utf-8 -*-
"""MẬT KHẨU ĐÃ CÔNG KHAI và MẬT KHẨU QUÁ YẾU — hai việc khác nhau, cùng một hậu quả.

VÌ SAO TỆP NÀY CÓ, VÀ NÓ ĐẾN TỪ MỘT CHỖ HỎNG THẬT

Ngày 14/9/2026, trang đăng nhập của bản chạy trên internet công cộng **in ra màn hình** câu này:

    "Bản chạy thử: các tài khoản mẫu (chutich, tgd, ptgd.doan, tp.dieuhanh, dh.lan, dh.minh,
     kd.hoa, kd.tuan, ketoan, hcns, cntt, bks) dùng mật khẩu 123456."

Nghĩa là mười hai tài khoản — kể cả CHỦ TỊCH, TỔNG GIÁM ĐỐC và KẾ TOÁN — có mật khẩu ai cũng đọc
được, ngay trên trang ai cũng vào được. Lúc ấy trong hệ chỉ có dữ liệu chạy thử nên chưa mất gì.
Nhưng hệ đang chuẩn bị nhận số thật nửa đầu năm: doanh thu, giá vốn, danh sách khách, doanh số từng
nhân viên. Từ mốc ấy trở đi, một dòng chữ trên trang đăng nhập là một cánh cửa mở.

BỘ MÁY BUỘC ĐỔI MẬT KHẨU ĐÃ CÓ SẴN, CHỈ THIẾU NGƯỜI BẤM CỜ

`users.must_change_password` đã có; `deps.check_must_change_password` đã chặn mọi đường trừ ba đường
(xem mình là ai, đổi mật khẩu, đăng xuất); màn hình `/doi-mat-khau` đã có. Nhưng cờ ấy chỉ được bật
khi HCNS đặt lại mật khẩu cho ai đó. **Những tài khoản sinh ra từ lúc gieo dữ liệu mẫu chưa bao giờ
được bật cờ** — nên không ai bị buộc đổi, và mật khẩu công khai cứ thế sống.

Tệp này là phần còn thiếu: một phép **soát**, và một phép **bật cờ**.

CLAUDE KHÔNG ĐẶT MẬT KHẨU CHO AI

Ở đây chỉ có hai việc: *kiểm* xem một mật khẩu có nằm trong danh sách đã công khai không (bằng cách
so với bản băm — không đọc, không lưu, không truyền đi đâu), và *bật cờ* buộc người ấy tự đổi ở lần
đăng nhập kế tiếp. Mật khẩu mới do chính chủ tài khoản gõ.
"""
from __future__ import annotations

import re
import unicodedata

# Mật khẩu ĐÃ IN RA TRANG ĐĂNG NHẬP. Đây không phải "mật khẩu yếu" theo nghĩa đoán được — nó là mật
# khẩu đã bị công bố, và một mật khẩu đã công bố thì dài bao nhiêu cũng bằng không.
DA_CONG_KHAI = ("123456",)

# Mật khẩu quá yếu: đoán ra trong vài chục lần thử. Danh sách ngắn và cố ý ngắn — nó chặn cái tệ
# nhất chứ không thay cho một bộ kiểm mật khẩu đầy đủ.
QUA_YEU = (
    "12345678", "123456789", "1234567890", "password", "matkhau", "abc12345",
    "qwertyui", "11111111", "00000000", "vietourist", "vietrip", "vtos1234",
)

TOI_THIEU = 8


def _khong_dau(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def _lien_tiep(s: str) -> bool:
    """Toàn số và chạy liền một mạch: 12345678, 87654321."""
    if not s.isdigit() or len(s) < 4:
        return False
    b = [ord(c) for c in s]
    return all(y - x == 1 for x, y in zip(b, b[1:])) or all(x - y == 1 for x, y in zip(b, b[1:]))


def vi_sao_khong_dat_duoc(mk: str, *, username: str = "", ho_ten: str = "",
                          ma_nhan_vien: str = "") -> str:
    """Lý do KHÔNG đặt được mật khẩu này. Chuỗi rỗng nghĩa là đặt được.

    Trả về LÝ DO chứ không trả về True/False: người bị từ chối mà không biết vì sao thì họ thử lại
    một mật khẩu yếu khác, rồi lại bị từ chối, rồi họ ghi mật khẩu ra giấy dán màn hình.
    """
    m = (mk or "").strip()
    if len(m) < TOI_THIEU:
        return f"Mật khẩu phải từ {TOI_THIEU} ký tự."
    if m in DA_CONG_KHAI:
        return ("Mật khẩu này đã từng in công khai trên trang đăng nhập của hệ thống – "
                "ai cũng biết, nên không dùng lại được.")
    if _khong_dau(m) in QUA_YEU or _lien_tiep(m):
        return "Mật khẩu quá dễ đoán. Chọn một mật khẩu khác hẳn."
    if len(set(m)) <= 2:
        return "Mật khẩu chỉ gồm một hai ký tự lặp lại. Chọn một mật khẩu khác."

    # Tên đăng nhập, họ tên, mã nhân viên đều là thứ NGƯỜI KHÁC BIẾT. Mã nhân viên còn nằm công khai
    # trên bảng lương.
    thap = _khong_dau(m)
    for x, nhan in ((username, "tên đăng nhập"), (ho_ten, "họ tên"), (ma_nhan_vien, "mã nhân viên")):
        t = _khong_dau(str(x or "")).replace(" ", "")
        if t and len(t) >= 4 and t in thap.replace(" ", ""):
            return f"Mật khẩu không được chứa {nhan} – người khác biết thứ đó."
    return ""


def dang_dung_mat_khau_cong_khai(password_hash: str) -> bool:
    """Tài khoản này còn đang dùng một mật khẩu ĐÃ CÔNG KHAI hay không.

    So bằng bản băm. Không đọc được mật khẩu thật của ai, và cũng không cần đọc: câu hỏi duy nhất là
    "có trùng một trong những chuỗi đã bị in ra trang đăng nhập không".
    """
    from app.core.security import verify_password

    return any(verify_password(x, password_hash or "") for x in DA_CONG_KHAI)


def soat(db) -> dict:
    """Đếm xem còn bao nhiêu tài khoản đang dùng mật khẩu đã công khai. KHÔNG đổi gì."""
    from sqlalchemy import select

    from app.models.core import User

    ds = db.scalars(select(User).where(User.active == True)).all()      # noqa: E712
    dinh = [u for u in ds if dang_dung_mat_khau_cong_khai(u.password_hash)]
    return {
        "tong_tai_khoan": len(ds),
        "con_mat_khau_cong_khai": len(dinh),
        "da_buoc_doi": sum(1 for u in dinh if u.must_change_password),
        "chua_buoc_doi": sum(1 for u in dinh if not u.must_change_password),
        "danh_sach": [{"username": u.username, "ho_ten": u.full_name, "role": u.role,
                       "da_buoc_doi": bool(u.must_change_password)} for u in dinh],
        "ghi_chu": (
            f"{len(dinh)}/{len(ds)} tài khoản đang hoạt động còn dùng mật khẩu đã in công khai trên "
            "trang đăng nhập. Bật cờ thì lần đăng nhập kế tiếp họ buộc phải đổi trước khi vào được "
            "bất cứ màn hình nào. Không ai bị khoá, và không mật khẩu nào bị đặt hộ."),
    }


def bat_co(db, boi: str, xac_nhan: bool = False) -> dict:
    """Bật cờ BUỘC ĐỔI cho mọi tài khoản còn dùng mật khẩu đã công khai.

    Mặc định chỉ XEM TRƯỚC. Việc này chạm vào khả năng đăng nhập của người thật, nên nó phải qua một
    lần bấm và vào nhật ký mang tên người bấm.
    """
    from sqlalchemy import select

    from app.models.core import User

    kq = soat(db)
    if not xac_nhan:
        return {**kq, "da_bat": 0,
                "message": ("CHƯA ĐỔI GÌ. Đây là bản xem trước. Bấm xác nhận thì mới bật cờ, và lần "
                            "bấm ấy vào nhật ký mang tên người bấm.")}

    ten = [x["username"] for x in kq["danh_sach"] if not x["da_buoc_doi"]]
    n = 0
    for u in db.scalars(select(User).where(User.username.in_(ten))).all() if ten else []:
        u.must_change_password = True
        n += 1
    db.flush()
    return {**kq, "da_bat": n,
            "message": (f"Đã bật cờ buộc đổi mật khẩu cho {n} tài khoản. Lần đăng nhập kế tiếp họ "
                        "phải đặt mật khẩu mới trước khi vào được bất cứ màn hình nào. Không tài "
                        "khoản nào bị khoá, và không mật khẩu nào bị đặt hộ.")}
