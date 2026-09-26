# -*- coding: utf-8 -*-
"""THANG BẬC ĐÒI NỢ KHÁCH — Chủ tịch quyết 25/9/2026, câu 5.

Câu hỏi 5 gửi Chủ tịch: *trễ thu tiền của khách thì ai chịu?* — trả lời:

    Mảng ĐOÀN:  nhân viên sale đã bán  →  Sale Admin        →  Phó TGĐ Đoàn
    Mảng LẺ:    nhân viên sale đã bán  →  Trưởng phòng KD   →  Giám đốc KD

═══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ HỞ THẬT, ĐO TRÊN MÃ ĐANG CHẠY
═══════════════════════════════════════════════════════════════════════════════════════════════
Cảnh báo `qua_deadline_thu` ĐÃ CÓ từ lâu (`bookings.robot_check`). Hai chỗ nó chưa làm được:

  1. NÓ KHÔNG CÓ CHỦ. Sinh ra với `to_roles = "nv_kd,gd_kd,tp_dh,ketoan"` và `nguoi_phu_trach`
     để trống — đúng thứ PQ-9 (11/9/2026) đo ra và gọi tên: *gửi cho bốn vai trò là gửi cho
     không ai*, 1.557 trên 1.703 cảnh báo chưa ai xử lý. `chu_canh_bao.suy_chu` biết suy ra sale
     phụ trách, nhưng đó là một bộ DỌN chạy sau, không phải luật lúc sinh.
  2. NÓ KHÔNG BAO GIỜ ĐI LÊN. Một khoản trễ ba ngày và một khoản trễ ba tháng nằm cùng một dòng
     đỏ, cùng một người nhận, cho tới lúc có người nhớ ra. Không có thang bậc thì "ai chịu" chỉ
     có một câu trả lời, và câu ấy luôn là người ở dưới cùng.

═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT CẢNH BÁO ĐI LÊN, KHÔNG PHẢI BA CẢNH BÁO
═══════════════════════════════════════════════════════════════════════════════════════════════
Một khoản nợ là MỘT việc. Sinh thêm một dòng đỏ ở mỗi bậc thì bảng cảnh báo có ba bản của cùng
một vấn đề, đóng một bản còn lại hai, và con số "bao nhiêu khoản đang trễ" đếm gấp ba. Nên ở đây
bậc cao hơn GHI ĐÈ chủ và người nhận tin của chính dòng cũ, cộng thêm một dòng vào lời nhắn nói
rõ nó vừa được đẩy lên.

Bậc là một HÀM của thời gian — `bac_can_co(quá hạn bao nhiêu ngày)` — và mỗi lượt quét TÍNH LẠI
rồi ghi đè `alerts.bac`. Cột ấy không phải nguồn sự thật thứ hai; nó là chỗ nhớ "đã báo tới bậc
mấy rồi", để lượt sau biết có phải vừa leo một bậc hay không mà không nối thêm một dòng nhắn vào
lời nhắn mỗi giờ. Nhờ tính lại mỗi lượt, bộ này tự sửa được cả những dòng cũ sinh trước hôm nay.

(Bản đầu em định không thêm cột, suy bậc từ `to_roles`. Nó sai ở một chỗ cụ thể: thang mảng Lẻ là
nv_kd → tp_kd → **gd_kd**, mà `gd_kd` VỐN ĐÃ nằm trong danh sách báo tin gốc của cảnh báo này —
suy như thế thì mọi khoản nợ lẻ trông như đã ở bậc 3 ngay từ lúc sinh ra.)

`to_roles` CHỈ CỘNG THÊM khi leo bậc, KHÔNG thu hẹp về một vai. Hai cột trả lời hai câu khác nhau
(PQ-9): `nguoi_phu_trach` là người PHẢI ĐÒI, `to_roles` là những người ĐƯỢC BIẾT. Điều hành giữ
ghế và Kế toán giữ sổ vẫn cần thấy khoản nợ ấy — thu danh sách về một vai là lặng lẽ lấy cảnh báo
ra khỏi bảng của hai bộ phận đang theo nó.

═══════════════════════════════════════════════════════════════════════════════════════════════
BẬC 2 VÀ 3 LÀ VAI TRÒ, MÀ CHỦ PHẢI LÀ MỘT NGƯỜI — CHỖ NÀY KHÔNG ĐOÁN
═══════════════════════════════════════════════════════════════════════════════════════════════
Bậc 1 có sẵn một người: `booking.sales_id`. Bậc 2 và 3 Chủ tịch chỉ định bằng VAI TRÒ. Vai ấy có
đúng một người đang hoạt động thì giao đích danh; có không ai, hoặc có hai người, thì để chủ TRỐNG
và gửi theo vai — cùng một quy ước với `chu_canh_bao` (*suy không ra thì để trống và ĐẾM, không
đẩy bừa*) và với `chu_ho_so.nguoi_giu_ho_so_doan`. Chọn bừa người đầu danh sách là tạo ra một
người chịu trách nhiệm giả, và người ấy không biết mình vừa được giao việc.

Số dòng rơi vào trường hợp ấy trả ra trong kết quả chạy, để nó là một con số phải xử lý chứ không
phải một khoảng lặng.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Alert, Booking, Tour, User
from app.services import rules as R
from app.services import segments as SEG

KIND = "qua_deadline_thu"

# Thang bậc, khai theo MẢNG. Hai chuỗi khác nhau hoàn toàn ở bậc 2 và 3 — đó là lý do phải khai
# theo mảng chứ không một thang chung: phòng Đoàn và phòng Lẻ có hai tuyến chỉ huy khác nhau.
THANG = {
    "doan": ("nv_kd", "sales_admin", "ptgd_doan"),
    "le":   ("nv_kd", "tp_kd", "gd_kd"),
}
# Chuyến không thuộc mảng nào (dịch vụ lẻ `non_package`, dữ liệu cũ chưa khai loại chuyến) đi
# thang của mảng LẺ. Nói ra ở đây chứ không để `SEG.mang_of` trả rỗng rồi rơi vào chỗ không khai:
# một khoản nợ không có ai đòi vì loại chuyến để trống là cách tệ nhất để mất tiền.
THANG_MAC_DINH = THANG["le"]

TEN_BAC = {1: "nhân viên sale đã bán", 2: "cấp trên trực tiếp", 3: "lãnh đạo khối"}


def moc_ngay(db: Session) -> tuple[int, int]:
    """(ngày lên bậc 2, ngày lên bậc 3) — đếm từ hạn hủy chỗ. Sửa ở màn hình Chính sách."""
    return int(R.get_param(db, "no_khach_bac2_ngay")), int(R.get_param(db, "no_khach_bac3_ngay"))


def bac_can_co(tre_ngay: int, m2: int, m3: int) -> int:
    """Trễ bao nhiêu ngày thì ở bậc nào. Mốc RƠI ĐÚNG NGÀY là ĐÃ lên bậc — khác với quy ước của
    `han_cong_no` (hạn rơi đúng ngày báo cáo chưa phải quá hạn), và khác có lý do: ở kia mốc là
    hạn TRẢ TIỀN, người ta còn cả ngày hôm nay; ở đây mốc là hạn ĐÃ QUA rồi, đếm thêm ngày."""
    if tre_ngay >= m3: return 3
    if tre_ngay >= m2: return 2
    return 1


def nguoi_cua_vai(db: Session, vai: str) -> tuple[int | None, str]:
    """Đúng MỘT người đang hoạt động mang vai này, hoặc (None, lý do). Không chọn bừa."""
    ds = list(db.execute(select(User).where(User.active == True, User.role == vai)).scalars())  # noqa: E712
    if len(ds) == 1:
        return ds[0].id, ""
    if not ds:
        return None, f"chưa có tài khoản nào đang hoạt động mang vai {vai}"
    return None, f"có {len(ds)} tài khoản mang vai {vai} – không đoán được ai chịu khoản này"


def thang_cua(t: Tour | None) -> tuple[str, ...]:
    return THANG.get(SEG.mang_of(t) if t else "", THANG_MAC_DINH)


def _tre_ngay(a: Alert, b: Booking | None, hom_nay: date) -> int:
    """Trễ tính từ HẠN HỦY CHỖ của booking. Không có hạn ấy thì tính từ lúc cảnh báo sinh ra —
    một dòng cũ không có hạn vẫn phải đi lên được, nếu không nó đứng mãi ở bậc 1."""
    moc = b.cancel_deadline.date() if (b is not None and b.cancel_deadline) else None
    if moc is None:
        moc = a.created_at.date() if a.created_at else hom_nay
    return (hom_nay - moc).days


def quet(db: Session, hom_nay: date | None = None) -> dict:
    """Đặt lại chủ và người nhận tin cho MỌI cảnh báo trễ thu tiền còn mở, theo đúng bậc của nó.

    Chạy lại nhiều lần không đổi gì thêm (đặt đúng bậc đang cần, không cộng dồn). Chỉ ghi nhật ký
    ở những dòng THỰC SỰ đổi bậc, nếu không thì mỗi lượt quét đẻ một trang nhật ký không tin nào.
    """
    hom_nay = hom_nay or date.today()
    m2, m3 = moc_ngay(db)
    bookings = {b.code: b for b in db.execute(select(Booking)).scalars()}
    tours = {t.id: t for t in db.execute(select(Tour)).scalars()}

    dem = {1: 0, 2: 0, 3: 0}
    day_len, khong_ro_chu = 0, []
    for a in db.execute(select(Alert).where(Alert.kind == KIND, Alert.resolved == False)).scalars():  # noqa: E712
        ma = (a.ref or "").split("booking:", 1)[-1]
        b = bookings.get(ma)
        t = tours.get(b.tour_id) if b is not None else None
        thang = thang_cua(t)
        bac = bac_can_co(_tre_ngay(a, b, hom_nay), m2, m3)
        vai = thang[bac - 1]

        if bac == 1:
            chu, ly_do = (b.sales_id if b is not None else None), ("không tìm thấy booking" if b is None else "")
            if b is not None and not b.sales_id:
                ly_do = "booking chưa có sale phụ trách"
        else:
            chu, ly_do = nguoi_cua_vai(db, vai)

        dem[bac] += 1
        if ly_do:
            khong_ro_chu.append({"canh_bao": a.id, "booking": ma, "bac": bac, "vai": vai, "ly_do": ly_do})

        if bac > (a.bac or 1):
            a.message = (a.message or "") + (
                f"\n[ĐẨY LÊN BẬC {bac} ngày {hom_nay:%d/%m/%Y}] Quá hạn thu đã {_tre_ngay(a, b, hom_nay)} ngày — "
                f"chuyển {TEN_BAC[bac]} ({vai}).")[:4000]
            R.audit(db, "robot_doi_no", "robot_ks", "day_bac_doi_no", f"alert:{a.id}",
                    before={"bac": a.bac, "nguoi_phu_trach": a.nguoi_phu_trach},
                    after={"bac": bac, "vai": vai, "nguoi_phu_trach": chu, "booking": ma,
                           "ly_do_khong_ro_chu": ly_do})
            day_len += 1

        # Đặt lại CẢ KHI không đổi bậc: dòng cũ sinh trước hôm nay có chủ để trống, và chúng phải
        # được kéo về đúng luật ngay lượt quét đầu tiên chứ không phải chờ tới lúc leo bậc.
        a.bac, a.nguoi_phu_trach = bac, chu
        # `to_roles` CHỈ CỘNG THÊM, không thu hẹp. Người chịu trách nhiệm đổi theo bậc; người
        # ĐƯỢC BIẾT thì không bớt đi — Điều hành giữ ghế và Kế toán giữ sổ vẫn cần nhìn thấy
        # khoản nợ ấy trên bảng của mình. Thu `to_roles` về đúng một vai là lấy một cảnh báo ra
        # khỏi bảng của hai bộ phận đang theo nó, và không ai nhận ra cho tới lúc hỏi "sao không
        # thấy nữa".
        co = [x for x in (a.to_roles or "").split(",") if x.strip()]
        if vai not in co:
            co.append(vai)
        a.to_roles = ",".join(co)[:120]
        if chu and not a.giao_luc:
            a.giao_luc = datetime.now()
        if bac == 3:
            a.level = "red"

    db.commit()
    return {"bac_1": dem[1], "bac_2": dem[2], "bac_3": dem[3],
            "day_len_bac": day_len, "moc_ngay": [m2, m3],
            # Con số phải xử lý, không phải một khoảng lặng: mỗi dòng ở đây là một khoản nợ mà hệ
            # thống KHÔNG biết giao cho ai, và nó sẽ nằm im nếu không ai đọc danh sách này.
            "khong_ro_chu": khong_ro_chu}
