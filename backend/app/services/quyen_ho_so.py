"""CỔNG CẤP QUYỀN THEO TỪNG HỒ SƠ VÀ TỪNG THAO TÁC — phòng Hướng dẫn, 13/10/2026.

Vì sao có tệp này. Rà soát 13/10/2026 trên `origin/main` đếm được 25 vị trí đang hỏi cùng MỘT câu
hỏi — "tài khoản đang đăng nhập ứng với hồ sơ nhân viên nào" — bằng BỐN cách khác nhau, và bốn cách
ấy trả lời khác nhau ở bốn ca biên khác nhau:

  dạng 1  `user_id`, rỗng thì lùi về `staff_code`   — hr.py:319, 417, 2173, 2225
  dạng 2  `user_id`, không có đường lùi             — hr.py:753, 882, 1862, 2050; ops.py:44; fleet.py:688
  dạng 3  `scalar_one_or_none()`                    — hrm.py:33   (hai hồ sơ cùng trỏ một tài khoản → nổ 500)
  dạng 4  đi ngược từ bản ghi rồi so `user_id`      — nhan_lenh.py:89

Hậu quả ĐO ĐƯỢC, không phải lo xa: một hướng dẫn viên có hồ sơ nối bằng mã nhân viên nhưng chưa nối
tài khoản thì MỞ ĐƯỢC "Lịch của tôi" (dạng 1) và "Lời mời" (dạng 1), nhưng BỊ TỪ CHỐI ở "Báo cáo sau
tour" (dạng 2). Cùng một người, cùng một tài khoản, hai câu trả lời — và không màn hình nào nói ra
vì sao.

Tệp này KHÔNG phát minh cơ chế mới. VTOS đã diễn đạt quyền sở hữu từ lâu (hr.py:319, hr.py:736,
nhan_lenh.py:89, hrm.py:290). Việc ở đây là CHUẨN HÓA các phép kiểm đang rải rác thành một cơ chế
cấp quyền theo từng hồ sơ và từng thao tác, bắt buộc dùng cho cổng HDV.

HAI NGUYÊN TẮC, cả hai đều rút từ một lỗi có thật trong mã hiện tại:

1. KHÔNG CÓ ĐƯỜNG TRẢ VỀ RỖNG. `hr.py:882` viết `if e is not None and e.id == a.guide_id: raise` —
   tài khoản người kiểm chưa nối hồ sơ thì vế đầu sai, cả phép kiểm "không tự kiểm báo cáo của
   chính mình" IM LẶNG không chạy. Cái rỗng chính là nguồn của lỗi ấy, nên ở đây nó không tồn tại:
   `ho_so_cua` trả về hồ sơ hoặc ném. Chỗ nào thật sự cần "có thể rỗng" thì gọi
   `ho_so_cua_hoac_rong` — tên hàm nói thẳng ra để người đọc bản vá sau này không nhầm.

2. SÁU THAO TÁC LÀ SÁU CÂU HỎI RIÊNG. Chủ tịch chốt 13/10/2026: cổng phải phủ xem, sửa, tải tệp,
   xuất danh sách, nhận thông báo và số tổng hợp — không chỉ đường dẫn chi tiết. Gộp sáu thành một
   là lý do `GET /guide-assignments/tam-ung/so-theo-nguoi?guide_id=` hôm nay nhận mã người làm tham
   số truy vấn mà không ai hỏi "người này được XEM hồ sơ ấy không": cửa chỉ lọc phạm vi PHÁP NHÂN
   (`pham_vi_phap_nhan.loc`), không phải phạm vi NGƯỜI.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import Employee

# ───────────────────────── Sáu thao tác, và CHỮ đi kèm mỗi thao tác ─────────────────────────
#
# Giá trị là mệnh đề điền vào câu từ chối. Người bị chặn phải đọc ra ĐƯỢC CHẶN Ở VIỆC GÌ, không
# phải một chữ "403" trơ. Nhật ký cũng đọc chuỗi này, nên sửa chữ ở đây là sửa cả hai nơi.
THAO_TAC: dict[str, str] = {
    "xem":            "đọc hồ sơ này",
    "sua":            "ghi vào hồ sơ này",
    "tai_tep":        "tải tệp đính kèm hồ sơ này",
    "xuat_danh_sach": "xuất danh sách có hồ sơ này",
    "thong_bao":      "nhận thông báo về hồ sơ này",
    "so_tong_hop":    "đọc số tổng hợp có hồ sơ này",
}

# Mã cổng, để màn hình nhận ra và hiện đúng lời, giống `CONG_13` và `TRUNG_GIO_HDV` đang dùng.
CONG = "QUYEN_HO_SO"


class LoiHoSo(HTTPException):
    """Tách riêng để chỗ gọi bắt được đúng loại lỗi này mà không bắt nhầm 404 của bản ghi khác."""


def _loi(ma_so: int, viec: str, ly_do: str) -> LoiHoSo:
    return LoiHoSo(ma_so, {"gate": CONG, "viec": viec, "message": ly_do})


# ───────────────────────── Một hàm tra người, thay cho bốn dạng ─────────────────────────

def ho_so_cua_hoac_rong(db: Session, u: User) -> Employee | None:
    """Tra hồ sơ nhân sự của tài khoản, TRẢ VỀ RỖNG khi không có.

    Chỉ dùng khi chỗ gọi thật sự xử lý được cái rỗng và NÓI RA được nó xử lý thế nào. Mọi chỗ khác
    gọi `ho_so_cua`. Hàm này vẫn ném khi dữ liệu MÂU THUẪN — rỗng nghĩa là "chưa nối", không phải
    "nối sai mà thôi kệ".
    """
    theo_tk = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().all()

    # Hai hồ sơ cùng trỏ một tài khoản là dữ liệu hỏng, không phải ca biên để chọn đại. `.first()`
    # ở 12 chỗ hiện nay lặng lẽ lấy hồ sơ đầu tiên — nghĩa là người dùng có thể đang thao tác dưới
    # tên một đồng nghiệp mà không ai biết. `scalar_one_or_none()` ở hrm.py:33 thì nổ 500, đúng
    # hướng nhưng không nói được hỏng ở đâu.
    if len(theo_tk) > 1:
        ma = ", ".join(sorted(e.code for e in theo_tk))
        raise _loi(409, "tra_ho_so",
                   f"Tài khoản {u.username} đang nối với {len(theo_tk)} hồ sơ nhân sự ({ma}). "
                   "HCNS phải gỡ bớt – hệ thống không tự chọn hộ, vì chọn sai là thao tác dưới tên "
                   "người khác.")

    theo_ma = None
    if u.staff_code:
        theo_ma = db.execute(select(Employee).where(Employee.code == u.staff_code)).scalars().first()

    e = theo_tk[0] if theo_tk else None

    # Nối bằng tài khoản một đằng, mã nhân viên một nẻo. Hôm nay hr.py:2225 lấy hồ sơ theo `user_id`
    # rồi so mã với tham số, nên ca này đi qua êm. Nó không êm: một trong hai đường nối đang trỏ
    # nhầm người, và chưa biết đường nào.
    if e is not None and theo_ma is not None and theo_ma.id != e.id:
        raise _loi(409, "tra_ho_so",
                   f"Tài khoản {u.username} nối với hồ sơ {e.code} nhưng mã nhân viên ghi trên tài "
                   f"khoản lại là {theo_ma.code}. Hai đường nối trỏ hai người – HCNS sửa lại một "
                   "trong hai trước khi dùng màn hình này.")

    # Đường lùi theo mã nhân viên. Đây là dạng 1 ở hr.py:319 – dạng rộng nhất trong bốn dạng, và là
    # dạng đúng: hồ sơ có trước tài khoản, nên giai đoạn HCNS chưa ghép `user_id` là giai đoạn CÓ
    # THẬT chứ không phải lỗi. `Employee.code` là cột duy nhất nên đường lùi này không mơ hồ.
    return e or theo_ma


def ho_so_cua(db: Session, u: User) -> Employee:
    """Tra hồ sơ nhân sự của tài khoản. KHÔNG BAO GIỜ trả về rỗng – không có thì ném.

    Đây là hàm mặc định. Không có đường rỗng thì không có chỗ cho nhánh `if e is not None and …`
    ra đời lần thứ hai.
    """
    e = ho_so_cua_hoac_rong(db, u)
    if e is None:
        raise _loi(404, "tra_ho_so",
                   f"Tài khoản {u.username} chưa gắn với hồ sơ nhân sự – báo HCNS ghép mã nhân "
                   "viên. Chưa ghép thì hệ thống không biết đây là ai để mở phần việc của ai.")
    return e


# ───────────────────────── Cổng: một thao tác, một hồ sơ ─────────────────────────

def la_quan_ly(u: User, vai_quan_ly: tuple[str, ...]) -> bool:
    """Người này có đang xem với tư cách quản lý không.

    Tách thành hàm riêng để chỗ gọi khai DANH SÁCH VAI ngay tại cửa, nhìn thấy được khi đọc cửa ấy –
    thay vì chôn trong cổng rồi mỗi lần thêm vai phải sửa cổng.
    """
    return u.role in vai_quan_ly


def kiem(db: Session, u: User, viec: str, chu_ho_so_id: int | None,
         vai_quan_ly: tuple[str, ...] = ()) -> Employee | None:
    """Người đang đăng nhập có được LÀM `viec` TRÊN hồ sơ `chu_ho_so_id` không.

    Trả về hồ sơ của chính người ấy khi đi qua với tư cách chủ hồ sơ, hoặc `None` khi đi qua với tư
    cách quản lý – chỗ gọi phân biệt được hai đường mà không phải hỏi lại.

    Ném khi không được. Không có đường trả về "có vẻ được".
    """
    # Gõ sai tên thao tác phải NỔ, không được mặc định cho qua. Một cổng mà gõ nhầm thì mở là một
    # cổng tệ hơn không có cổng, vì nó làm người đọc tin là đã canh.
    if viec not in THAO_TAC:
        raise _loi(500, viec,
                   f"Thao tác '{viec}' không có trong bảng – khai thêm vào THAO_TAC trước khi gọi.")

    if la_quan_ly(u, vai_quan_ly):
        return None

    # Tra người TRƯỚC khi so. Không tra được là TỪ CHỐI, không phải bỏ qua phép so – đây đúng chỗ
    # hr.py:882 làm ngược lại.
    e = ho_so_cua(db, u)

    if chu_ho_so_id is None:
        raise _loi(404, viec, "Bản ghi này chưa ghi ai là chủ – không có gì để đối chiếu quyền.")

    if e.id != chu_ho_so_id:
        raise _loi(403, viec,
                   f"Chỉ người của hồ sơ này mới {THAO_TAC[viec]}. Tài khoản {u.username} đang ở hồ "
                   f"sơ {e.code}.")
    return e


def loc(q, cot, db: Session, u: User, viec: str, vai_quan_ly: tuple[str, ...] = ()):
    """Thu hẹp một câu truy vấn về đúng hồ sơ của người đăng nhập.

    Dành cho DANH SÁCH, XUẤT DANH SÁCH và SỐ TỔNG HỢP – ba thao tác mà cổng `kiem` ở trên không với
    tới được, vì lúc ấy chưa có một hồ sơ cụ thể để hỏi. Đây chính là chỗ hôm nay đang hở:
    `thu-lao/doi-soat` trả toàn kỳ, `khoan_treo` lọc bằng một chuỗi ma thuật `"\\u0000"`.

    Quản lý thì không thu hẹp. Người thường thì thu hẹp về hồ sơ của mình – và nếu không tra được
    người thì NÉM, chứ không trả danh sách rỗng: rỗng trông y hệt "không có việc nào", và một
    hướng dẫn viên nhìn bảng thù lao trống sẽ tưởng kỳ này mình không có chuyến nào.
    """
    if viec not in THAO_TAC:
        raise _loi(500, viec,
                   f"Thao tác '{viec}' không có trong bảng – khai thêm vào THAO_TAC trước khi gọi.")
    if la_quan_ly(u, vai_quan_ly):
        return q
    e = ho_so_cua(db, u)
    return q.where(cot == e.id)
