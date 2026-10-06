"""Phòng Hướng dẫn viên — phép chặn hai chuyến chồng giờ, và phép đếm phần còn thiếu.

Chủ tịch chốt 06/10/2026: KHÔNG xếp một hướng dẫn viên vào hai chuyến chồng giờ. Không phải "cảnh
báo rồi vẫn cho qua" — cấm.

────────────────────────────────── CHỒNG GIỜ LÀ GÌ ──────────────────────────────────

Hai khoảng [a1,a2) và [b1,b2) chồng nhau khi:  a1 < b2  VÀ  b1 < a2

Viết nửa mở — đầu đóng, cuối mở — là điều phải nói rõ, vì nó quyết định một ca có thật và hay gặp:
chuyến A kết thúc ĐÚNG 18h, chuyến B bắt đầu ĐÚNG 18h. Với nửa mở thì a1 < b2 đúng nhưng b1 < a2 sai
(18h < 18h là sai), nên KHÔNG chồng — và đó là điều đúng về mặt nghiệp vụ: giao đoàn xong là hết
việc. Nếu viết <= thì mọi lần nối tiếp liền mạch đều bị chặn, và người xếp lịch sẽ học cách lùi giờ
một phút để lách — tức là hệ thống dạy người dùng ghi sai giờ.

Phần đệm đi lại KHÔNG cộng ở đây mà nằm trong chính hai mốc giờ của phân công: "khoảng cần người"
tính cả chuẩn bị và di chuyển (xem app/models/hdv.py). Cộng thêm một khoảng đệm cứng ở tầng phép
tính thì con số ấy không ai nhìn thấy, không ai sửa được, và sẽ đúng cho tuyến này sai cho tuyến kia.

──────────────────────── RỖNG KHÔNG PHẢI LÀ KHÔNG CHỒNG ────────────────────────

Phân công thiếu giờ thì KHÔNG so được — và `khong_so_duoc` nói đúng điều đó thay vì trả về "không
chồng". Hai chuyện khác nhau: "đã kiểm, không chồng" là một kết luận; "chưa đủ dữ liệu để kiểm" là
một việc còn thiếu. Gộp hai thứ ấy làm một thì hàng trăm phân công cũ không có giờ sẽ lặng lẽ được
coi là đã kiểm xong, và cái cấm mà Chủ tịch vừa chốt thành ra chỉ áp cho dữ liệu mới.

Cửa lập phân công vì thế ĐÒI đủ hai mốc giờ — không có giờ thì không chặn được, mà không chặn được
thì không được phép ghi. Bản ghi CŨ thiếu giờ vẫn giữ nguyên, hiện ở danh sách việc còn thiếu.

──────────────────────────── CHẶN THẬT, KHÔNG CHỈ HỎI TRƯỚC ────────────────────────────

Hỏi trước khi ghi ("có ai trùng không?" rồi mới ghi) KHÔNG đủ: hai phiên cùng hỏi lúc chưa ai ghi,
cả hai cùng thấy trống, cả hai cùng ghi. Nên ở đây làm hai lớp:

  1. Trước khi ghi: khoá hàng hướng dẫn viên trong `employees` bằng SELECT ... FOR UPDATE. Postgres
     xếp hàng hai phiên tại đúng chỗ này. SQLite không có FOR UPDATE và cũng không cần — nó khoá
     toàn tệp.
  2. SAU khi ghi, TRƯỚC khi chốt giao dịch: đếm lại số phân công chồng giờ của chính người ấy. Nếu
     còn ai khác ngoài bản vừa ghi thì có người đã chen vào giữa — lùi lại và từ chối.

Lớp 2 là lớp thật sự bảo đảm, và nó chạy đúng trên cả hai loại máy chủ. Lớp 1 chỉ để hai phiên không
phải cùng làm rồi cùng hỏng.
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hdv import TRANG_THAI_DONG as YC_DONG
from app.models.hdv import YeuCauHdv
from app.models.hr import GuideAssignment

# Phân công ở hai trạng thái này KHÔNG chiếm lịch nữa: người ta đã từ chối, hoặc lời chào đã hết hạn.
# Nhưng bản ghi vẫn còn — giữ dấu vết là điều kiện để sau này trả lời được "ai đã từ chối chuyến nào".
KHONG_CHIEM_LICH = ("tu_choi", "huy", "het_han")


def chong_gio(a1: datetime | None, a2: datetime | None,
              b1: datetime | None, b2: datetime | None) -> bool:
    """Hai khoảng nửa mở có chồng nhau không. Thiếu bất kỳ mốc nào thì trả về False – nhưng người
    gọi KHÔNG được coi đó là 'đã kiểm, không chồng': dùng `khong_so_duoc` để phân biệt."""
    if khong_so_duoc(a1, a2) or khong_so_duoc(b1, b2):
        return False
    return a1 < b2 and b1 < a2


def khong_so_duoc(t1: datetime | None, t2: datetime | None) -> bool:
    """Thiếu mốc, hoặc hai mốc ngược chiều nhau. Ngược chiều cũng là không so được chứ không phải
    'khoảng rỗng': kết thúc trước bắt đầu là một lần gõ nhầm, phải nói ra."""
    return t1 is None or t2 is None or t2 <= t1


def dang_chiem_lich(db: Session, guide_id: int, bat_dau: datetime, ket_thuc: datetime,
                    bo_qua_id: int | None = None) -> list[GuideAssignment]:
    """Những phân công còn hiệu lực của người này chồng giờ với khoảng đưa vào.

    Lọc theo trạng thái Ở TRONG PYTHON chứ không nhét vào câu truy vấn: danh sách phân công của một
    người trong một kỳ là vài chục dòng, và viết ra ngoài thì người đọc thấy ngay quy tắc nào đang
    áp – quy tắc "từ chối thì không chiếm lịch" là quy tắc nghiệp vụ, không nên chôn trong SQL.
    """
    q = select(GuideAssignment).where(GuideAssignment.guide_id == guide_id)
    if bo_qua_id is not None:
        q = q.where(GuideAssignment.id != bo_qua_id)
    ds = []
    for a in db.execute(q).scalars():
        if a.status in KHONG_CHIEM_LICH:
            continue
        if chong_gio(bat_dau, ket_thuc, a.bat_dau, a.ket_thuc):
            ds.append(a)
    return ds


def khoa_hdv(db: Session, guide_id: int) -> None:
    """Lớp 1 – xếp hàng hai phiên cùng xếp một người. Trên Postgres là khoá hàng thật; trên SQLite
    câu này chạy không lỗi và không làm gì, vì SQLite đã khoá ở mức tệp."""
    from app.models.hr import Employee
    try:
        db.execute(select(Employee).where(Employee.id == guide_id).with_for_update())
    except Exception:
        # Máy chủ không hỗ trợ FOR UPDATE (SQLite). KHÔNG phải lý do để dừng, và cũng KHÔNG được
        # nuốt im lặng thành "đã khoá": lớp 2 mới là lớp bảo đảm, và nó chạy ở mọi máy chủ.
        pass


def canh_trung_sau_khi_ghi(db: Session, a: GuideAssignment) -> None:
    """Lớp 2 – gọi SAU db.flush() và TRƯỚC db.commit().

    Nếu giữa lúc kiểm và lúc ghi có người chen vào thì đến đây sẽ thấy. Ném 422 kèm TÊN CHUYẾN đang
    chồng, không chỉ ném chữ 'trùng lịch': người xếp lịch cần biết phải gỡ chuyến nào.
    """
    if khong_so_duoc(a.bat_dau, a.ket_thuc):
        return
    trung = dang_chiem_lich(db, a.guide_id, a.bat_dau, a.ket_thuc, bo_qua_id=a.id)
    if not trung:
        return
    from app.models.core import Tour
    ten = []
    for k in trung[:3]:
        t = db.get(Tour, k.tour_id)
        nhan = t.code if t else f"tour {k.tour_id}"
        if k.bat_dau and k.ket_thuc:
            nhan += f" ({k.bat_dau:%d/%m %H:%M}–{k.ket_thuc:%d/%m %H:%M})"
        ten.append(nhan)
    db.rollback()
    raise HTTPException(422, {
        "gate": "TRUNG_GIO_HDV",
        "message": "Hướng dẫn viên này đã có chuyến chồng giờ: " + "; ".join(ten)
                   + ". Gỡ phân công cũ hoặc chọn người khác.",
        "trung_voi": [k.id for k in trung],
    })


def con_thieu(db: Session, yc: YeuCauHdv) -> int:
    """QUY ƯỚC CHUNG cho chữ 'chuyến chưa đủ nguồn lực' – phần xe phải có một hàm cùng nghĩa.

    Đếm số người CÒN PHẢI TÌM: số yêu cầu trừ đi số phân công còn hiệu lực đang trỏ về yêu cầu này.
    Người đã từ chối không tính là đã có – đó chính là chỗ một màn hình đếm sai sẽ báo "đã đủ" cho
    một chuyến không còn ai.
    """
    if yc.trang_thai in YC_DONG:
        return 0
    da_co = 0
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.yeu_cau_id == yc.id)).scalars():
        if a.status not in KHONG_CHIEM_LICH:
            da_co += 1
    return max(0, (yc.so_hdv or 0) - da_co)


def cap_nhat_trang_thai(db: Session, yc: YeuCauHdv) -> None:
    """Trạng thái yêu cầu suy từ phần còn thiếu, KHÔNG do người bấm tay – trừ huỷ. Để người bấm tay
    thì sẽ có yêu cầu mang nhãn 'đã đủ' mà không còn ai, ngay sau một lần từ chối."""
    if yc.trang_thai == "huy":
        return
    thieu = con_thieu(db, yc)
    if thieu == 0:
        yc.trang_thai = "da_du"
    elif thieu < (yc.so_hdv or 0):
        yc.trang_thai = "dang_xep"
    else:
        yc.trang_thai = "moi"
