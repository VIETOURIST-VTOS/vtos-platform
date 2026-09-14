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

BẢN ĐẦU CỦA TỆP NÀY ĐI QUÉT — VÀ QUÉT LÀ SAI

Bản 14/9 giải bài bằng cách **quét**: duyệt mọi tài khoản đang hoạt động, mỗi tài khoản gọi
`verify_password` một lần để xem có trùng chuỗi đã bị công bố không.

Ở bộ thử có năm tài khoản nên nó xanh trong một giây. Trên bản thật có **116 tài khoản**, và nó
treo. Đo trên máy dựng: `bcrypt.checkpw` **0,274 giây/lần** — bcrypt chậm là CỐ Ý, đó chính là thứ
làm nó chống dò được. 116 lần là ~32 giây ở máy mạnh, trên máy chủ nhỏ là hơn hai phút. Mà phép
quét ấy lại chạy **mỗi lần có người mở màn hình Tài khoản**.

CÁCH SỬA KHÔNG PHẢI LÀM CHO QUÉT NHANH HƠN — MÀ LÀ BỎ QUÉT ĐI

Có đúng hai lúc biết được một tài khoản còn dùng mật khẩu đã công bố hay không, và cả hai đều KHÔNG
cần bcrypt:

  1. LÚC NGƯỜI TA ĐĂNG NHẬP. Máy đang cầm mật khẩu họ vừa gõ. So chuỗi ấy với danh sách đã công bố
     là một phép so chuỗi — gần như không tốn gì, và biết CHẮC CHẮN chứ không phải đoán. Ai đăng
     nhập bằng mật khẩu đã công bố thì bị bật cờ ngay tại chỗ, trước khi vào được màn hình nào.

  2. TÀI KHOẢN CHƯA TỪNG ĐĂNG NHẬP (`last_login` rỗng). Chưa ai dùng thì mật khẩu vẫn nguyên như
     lúc gieo. Không cần thử cũng biết. Bật cờ cả lượt, không một lần bcrypt.

Hai đường ấy phủ kín: ai có dùng tài khoản thì (1) bắt được ở lần đăng nhập kế tiếp, ai không dùng
thì (2) bắt được ngay. Và phép quét cũ **không nhanh hơn được chút nào về hiệu lực**: cờ bật lên,
dù bật bằng đường nào, cũng chỉ có tác dụng ở LẦN ĐĂNG NHẬP KẾ TIẾP. Nó tốn hai phút để biết sớm
một điều không dùng sớm được.

CLAUDE KHÔNG ĐẶT MẬT KHẨU CHO AI

Ở đây chỉ có hai việc: *nhận ra* một mật khẩu nằm trong danh sách đã công bố, và *bật cờ* buộc người
ấy tự đổi ở lần đăng nhập kế tiếp. Mật khẩu mới do chính chủ tài khoản gõ.
"""
from __future__ import annotations

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
    if la_mat_khau_da_cong_khai(m):
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


def la_mat_khau_da_cong_khai(mk: str) -> bool:
    """Chuỗi người dùng vừa gõ có nằm trong danh sách đã bị công bố không.

    SO CHUỖI, KHÔNG BĂM. Đây là phép dùng ở LÚC ĐĂNG NHẬP, khi máy đang cầm sẵn mật khẩu người ta
    vừa gõ — nên nó không tốn gì, và nó biết chắc chứ không phải thử. Bản trước của tệp này đi băm
    từng tài khoản một để hỏi cùng câu hỏi đó, và trả giá hơn hai phút cho 116 tài khoản.

    Không ghi lại, không truyền đi đâu: chuỗi vào rồi ra ngay, chỉ còn lại một câu trả lời có/không.
    """
    return (mk or "").strip() in DA_CONG_KHAI


def co_phai_dang_ngu(u) -> bool:
    """Tài khoản CHƯA TỪNG ĐĂNG NHẬP — mật khẩu còn nguyên như lúc gieo.

    Không cần thử mật khẩu cũng biết: chưa ai dùng thì chưa ai đổi. Đây là nửa còn lại của bài toán,
    nửa mà đường đăng nhập không với tới được.
    """
    return getattr(u, "last_login", None) is None


def tom_tat(db) -> dict:
    """Ba con số cho màn hình. KHÔNG băm một lần nào, nên mở màn hình không phải chờ.

    Đây là phép chạy lúc TẢI TRANG, nên nó phải rẻ. Bản trước gọi phép quét ở đây và màn hình Tài
    khoản treo hơn hai phút trên bản thật.
    """
    from sqlalchemy import select

    from app.models.core import User

    ds = db.scalars(select(User).where(User.active == True)).all()      # noqa: E712
    ngu = [u for u in ds if co_phai_dang_ngu(u) and not u.must_change_password]
    return {
        "tong_tai_khoan": len(ds),
        "dang_buoc_doi": sum(1 for u in ds if u.must_change_password),
        "chua_tung_dang_nhap": len(ngu),
        "danh_sach": [{"username": u.username, "ho_ten": u.full_name, "role": u.role}
                      for u in ngu],
        "ghi_chu": (
            f"{len(ngu)}/{len(ds)} tài khoản đang hoạt động CHƯA TỪNG ĐĂNG NHẬP — mật khẩu của "
            "chúng còn nguyên như lúc gieo, trong đó có những tài khoản từng bị in mật khẩu công "
            "khai trên trang đăng nhập. Bật cờ thì lần đăng nhập đầu tiên họ phải đổi trước khi vào "
            "được bất cứ màn hình nào. Không ai bị khoá, và không mật khẩu nào bị đặt hộ.\n\n"
            "Những tài khoản ĐÃ từng đăng nhập không nằm trong danh sách này: nếu ai còn dùng mật "
            "khẩu đã công bố thì máy nhận ra ngay ở lần đăng nhập kế tiếp của chính họ và bật cờ "
            "tại chỗ — không cần ai bấm gì."),
    }


def bat_co(db, boi: str, xac_nhan: bool = False) -> dict:
    """Bật cờ BUỘC ĐỔI cho mọi tài khoản đang hoạt động mà CHƯA TỪNG ĐĂNG NHẬP.

    Mặc định chỉ XEM TRƯỚC. Việc này chạm vào khả năng đăng nhập của người thật, nên nó phải qua một
    lần bấm và vào nhật ký mang tên người bấm.
    """
    from sqlalchemy import select

    from app.models.core import User

    kq = tom_tat(db)
    if not xac_nhan:
        return {**kq, "da_bat": 0,
                "message": ("CHƯA ĐỔI GÌ. Đây là bản xem trước. Bấm xác nhận thì mới bật cờ, và lần "
                            "bấm ấy vào nhật ký mang tên người bấm.")}

    ten = [x["username"] for x in kq["danh_sach"]]
    n = 0
    for u in db.scalars(select(User).where(User.username.in_(ten))).all() if ten else []:
        u.must_change_password = True
        n += 1
    db.flush()
    return {**tom_tat(db), "da_bat": n,
            "message": (f"Đã bật cờ buộc đổi mật khẩu cho {n} tài khoản chưa từng đăng nhập. Lần "
                        "đăng nhập đầu tiên họ phải đặt mật khẩu mới trước khi vào được bất cứ màn "
                        "hình nào. Không tài khoản nào bị khoá, và không mật khẩu nào bị đặt hộ.")}
