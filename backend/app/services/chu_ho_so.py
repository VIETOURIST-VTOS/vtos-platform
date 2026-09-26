# -*- coding: utf-8 -*-
"""MỘT CHỦ HỒ SƠ — ai soạn và đóng quyết toán của một chuyến. Chủ tịch quyết 25/9/2026, câu 4.

═══════════════════════════════════════════════════════════════════════════════════════════════
VIỆC NÀY THAY CÁI GÌ
═══════════════════════════════════════════════════════════════════════════════════════════════
Trước hôm nay, cổng quyết toán viết thẳng một phép so sánh vào năm chỗ:

    if u.id != t.operator_id: raise Gate("CONG_6", "Một cửa: chỉ người điều hành chuyến ...")

Luật ấy gọi là "Một cửa" và nó giữ đúng một điều rất đáng giữ: **con số quyết toán có tên một
người**, và chức vụ không thay được trách nhiệm ấy — Trưởng phòng cũng không nhập hộ.

Chỗ nó sai không phải ở "một người", mà ở chỗ **người ấy bị khoá cứng vào cột `operator_id`** —
một cột được sinh ra để trả lời câu hỏi khác hẳn: *ai chạy chuyến này, và do đó thưởng chuyến
thuộc về ai*. Hai câu hỏi trùng nhau ở tour lẻ, nhưng ở phòng Đoàn thì không: người gom hợp đồng,
gom chứng từ và gõ quyết toán là **Sale Admin**, còn người chạy chuyến ngoài hiện trường là điều
hành. Bắt điều hành gõ quyết toán đoàn là bắt người không giữ chứng từ nhập con số mình không có.

Nên luật đổi tên và đổi chỗ chứa, KHÔNG đổi bản chất:

    "Một cửa"          →  "Một chủ hồ sơ"
    operator_id        →  chu_ho_so(db, t)   — vẫn trả về ĐÚNG MỘT id, không bao giờ một danh sách

═══════════════════════════════════════════════════════════════════════════════════════════════
BA BẬC TRẢ LỜI, VÀ THỨ TỰ LÀ CỐ Ý
═══════════════════════════════════════════════════════════════════════════════════════════════
  1. `tours.chu_ho_so_id` — chuyến này đã CHỈ ĐÍCH DANH một người. Thắng mọi thứ còn lại.
  2. Chuyến thuộc **mảng Đoàn** và tham số `chu_ho_so_doan` chỉ tới một tài khoản đang hoạt động
     → người ấy. Đây là câu trả lời của Chủ tịch: "tour đoàn thì mặc định về Sale Admin".
  3. `tours.operator_id` — như cũ. Tour lẻ, dịch vụ lẻ, và mọi chuyến chưa khai gì đều rơi vào đây.

Bậc 2 chỉ áp cho **mảng Đoàn** theo `segments.mang_of`. Dịch vụ lẻ (`non_package`) trả về chuỗi
rỗng ở hàm ấy nên không bao giờ chạm tới bậc 2 — đúng ý: dịch vụ lẻ là loại hàng riêng, và câu
hỏi hôm nay không nói gì về nó.

═══════════════════════════════════════════════════════════════════════════════════════════════
RỦI RO CỦA BẬC 2, VÀ CÁCH CHẶN
═══════════════════════════════════════════════════════════════════════════════════════════════
Bậc 2 tính SỐNG mỗi lần gọi. Nghĩa là **đổi một dòng tham số là chuyển chủ của hàng trăm chuyến
cùng một lúc** — kể cả những chuyến đang soạn dở. Em đã nói rủi ro này ra trước khi Chủ tịch chọn.
Ba thứ giữ cho nó không thành tai nạn:

  · ĐÓNG DẤU Ở LẦN GHI ĐẦU (`ghi_dau_chu`). Ai ghi được dòng quyết toán đầu tiên thì tên người ấy
    được đóng cứng vào `chu_ho_so_id` ngay lúc đó. Từ giây ấy trở đi hồ sơ lên bậc 1, và không
    tham số nào lấy đi được nữa. Hồ sơ chưa ai chạm vào thì đổi chủ không mất gì.
  · CỔNG CHỈ MỞ Ở TRẠNG THÁI SOẠN (`EDITABLE`). Hồ sơ đã đóng số thì không ai soạn nữa, nên bậc 2
    có đổi cũng không với tới con số đã chốt.
  · THAM SỐ SAI THÌ NÓI RA, KHÔNG IM. Tham số trỏ tới một tài khoản đã nghỉ hoặc gõ sai → rơi về
    bậc 3 và trả kèm câu giải thích, giống hệt cách `fleet.nguoi_duoc_lap_lenh` đã làm. Im lặng bỏ
    qua thì chỉ đạo của Chủ tịch âm thầm hết hiệu lực; chặn sạch thì cả phòng Đoàn đứng vì một ô
    gõ nhầm.

═══════════════════════════════════════════════════════════════════════════════════════════════
THƯỞNG CHUYẾN KHÔNG ĐI THEO — ĐÂY LÀ LÝ DO PHẢI THÊM CỘT MỚI
═══════════════════════════════════════════════════════════════════════════════════════════════
`operator_id` vẫn là căn cứ duy nhất tính thưởng chuyến (`rules.py::_quy_thuong`, `hr.py`,
`luong.py`). Bàn giao hồ sơ quyết toán **không** bàn giao thưởng chuyến, và cũng không đổi ai là
người điều hành chuyến trên mọi báo cáo khác.

Đây chính là lý do không được "cho gọn" bằng cách ghi đè `operator_id` khi bàn giao: làm thế là
lấy tiền thưởng của điều hành đưa cho người gõ quyết toán, bằng một cú bấm mang tên "bàn giao hồ
sơ", và không màn hình nào nói ra điều đó.
"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.services import rules as R
from app.services import segments as SEG

# Ai được GIỮ một hồ sơ quyết toán. Đây là danh sách người NHẬN khi bàn giao — không phải một
# đường vòng của cổng: cổng vẫn chỉ cho đúng một người trong số này, người đang giữ hồ sơ.
#
# Khối Kinh doanh KHÔNG có trong danh sách. Quyết toán là bảng "mình mua của ai, bao nhiêu";
# `sales_admin` ở đây với tư cách người giữ hồ sơ phòng Đoàn, đúng vai mô tả Phần V đã khai, chứ
# không phải với tư cách người bán.
CHU_HO_SO_ROLES = ("nv_dh", "tp_dh", "sales_admin")

# Ai được BÀN GIAO hồ sơ sang người khác. Cố ý KHÔNG có `sales_admin` ở đây: cho người nhận tự
# lấy hồ sơ về tay mình là bỏ luôn ý nghĩa của việc bàn giao. Chủ hồ sơ hiện tại thì trao đi được
# (điều đó không tự cho mình thêm gì), và Chủ tịch đi qua bằng luật toàn quyền.
GIAO_ROLES = ("tp_dh",)

# Bàn giao khi hồ sơ đã chốt số thì không đổi được gì, chỉ làm rối bản ghi.
TRANG_THAI_KHONG_GIAO = ("da_dong_so", "kt_xac_nhan", "khoa")


# Khoá nhớ tạm TRONG MỘT PHIÊN. Đặt ở đây chứ không dùng đệm tham số toàn cục, vì hai lý do khác
# nhau và cả hai đều phải giữ:
#
#   · `get_param_text` CỐ Ý không đệm (xem chú thích của nó): tham số dạng chữ giữ những thứ như
#     "ai được làm việc này", và sửa xong mà 60 giây sau mới có hiệu lực thì người vừa sửa tưởng
#     mình gõ sai. Đệm toàn cục ở đây là phá đúng tính chất ấy.
#   · Nhưng `tour_view` gọi hàm này MỘT LẦN CHO MỖI CHUYẾN, và màn hình danh sách dựng 300 chuyến.
#     Đo bằng phép thử KS-5 ngay khi vừa viết xong: 80 chuyến → 86 lượt đọc bảng tham số, vượt
#     trần 40 lượt của một lần đọc danh sách. Đây đúng là "truy vấn nằm trong vòng lặp".
#
# Một PHIÊN là một lượt gọi API. Nhớ trong phạm vi ấy thì màn hình danh sách đọc tham số đúng một
# lần, còn lượt gọi sau — kể cả ngay sau khi ai đó vừa sửa tham số — vẫn đọc lại từ đầu. Không mất
# gì, và không được sửa thành đệm theo thời gian.
_KHOA_NHO = "chu_ho_so_doan__da_tra"


def nguoi_giu_ho_so_doan(db: Session) -> tuple[User | None, str]:
    """Tài khoản giữ hồ sơ quyết toán mảng Đoàn, theo tham số `chu_ho_so_doan`.

    Trả `(None, lý do)` khi chưa cấu hình hoặc cấu hình không khớp ai — nơi gọi rơi về người điều
    hành chuyến và MANG THEO câu lý do ấy ra màn hình.

    Nhận tài khoản hoặc mã nhân viên, đúng một người. Gõ nhiều tên ngăn bởi dấu phẩy thì KHÔNG
    chọn bừa người đầu: "một chủ hồ sơ" mà tham số khai hai người là một câu hỏi cấu hình chưa
    trả lời xong, và đoán hộ ở đây là đoán một trách nhiệm.
    """
    nho = db.info.get(_KHOA_NHO)
    if nho is not None:
        return nho
    ra = _doc_nguoi_giu_ho_so_doan(db)
    db.info[_KHOA_NHO] = ra
    return ra


def quen_nho(db: Session) -> None:
    """Bỏ phần nhớ tạm của phiên. Phép thử đổi tham số giữa chừng gọi cái này; mã chạy thật thì
    không cần, vì mỗi lượt gọi API là một phiên mới."""
    db.info.pop(_KHOA_NHO, None)


def _doc_nguoi_giu_ho_so_doan(db: Session) -> tuple[User | None, str]:
    raw = (R.get_param_text(db, "chu_ho_so_doan") or "").strip()
    if not raw:
        return None, ""
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if len(keys) > 1:
        return None, (f"Tham số chu_ho_so_doan đang khai {len(keys)} người (\"{raw}\") — hồ sơ quyết "
                      "toán chỉ có MỘT chủ. Tạm áp dụng người điều hành chuyến, cần sửa lại tham số.")
    u = db.execute(select(User).where(User.active == True,  # noqa: E712
                                      or_(User.username == keys[0], User.staff_code == keys[0]))).scalars().first()
    if u is None:
        return None, (f"Tham số chu_ho_so_doan đang đặt là \"{raw}\" nhưng không khớp tài khoản đang "
                      "hoạt động nào — tạm áp dụng người điều hành chuyến, cần sửa lại tham số.")
    if u.role not in CHU_HO_SO_ROLES:
        return None, (f"Tham số chu_ho_so_doan trỏ tới {u.username} (vai {u.role}) — vai này không "
                      "được giữ hồ sơ quyết toán. Tạm áp dụng người điều hành chuyến.")
    return u, ""


def chu_ho_so(db: Session, t: Tour) -> int | None:
    """ĐÚNG MỘT id, hoặc None khi chuyến chưa có cả người điều hành. Không bao giờ một danh sách."""
    if getattr(t, "chu_ho_so_id", None):
        return t.chu_ho_so_id
    if SEG.mang_of(t) == "doan":
        u, _ = nguoi_giu_ho_so_doan(db)
        if u is not None:
            return u.id
    return t.operator_id


def la_chu_ho_so(db: Session, u: User, t: Tour) -> bool:
    return u.id == chu_ho_so(db, t)


def ten_chu_ho_so(db: Session, t: Tour) -> str:
    i = chu_ho_so(db, t)
    n = db.get(User, i) if i else None
    return n.full_name if n else "chưa có ai"


def xem(db: Session, t: Tour) -> dict:
    """Bản mô tả cho màn hình: ai đang giữ, vì sao là người ấy, và tham số có trục trặc gì không."""
    u_doan, ly_do = nguoi_giu_ho_so_doan(db)
    if getattr(t, "chu_ho_so_id", None):
        nguon = "chi_dinh"
    elif SEG.mang_of(t) == "doan" and u_doan is not None:
        nguon = "mac_dinh_doan"
    else:
        nguon = "dieu_hanh_chuyen"
    i = chu_ho_so(db, t)
    n = db.get(User, i) if i else None
    return {
        "chu_ho_so_id": i,
        "chu_ho_so_ten": n.full_name if n else "",
        "chu_ho_so_vai": n.role if n else "",
        "nguon": nguon,
        "nguon_mo_ta": {
            "chi_dinh": "Chuyến này đã chỉ đích danh chủ hồ sơ",
            "mac_dinh_doan": "Mặc định của mảng Đoàn (tham số chu_ho_so_doan)",
            "dieu_hanh_chuyen": "Người điều hành chuyến",
        }[nguon],
        # Lời cảnh báo tham số đi kèm CẢ KHI chuyến này không dùng tới bậc 2 — người đọc màn hình
        # một chuyến là người có khả năng đi sửa tham số nhất.
        "canh_bao_tham_so": ly_do,
        "thuong_chuyen_van_thuoc": (t.operator.full_name if t.operator else ""),
    }


def ghi_dau_chu(db: Session, t: Tour, nguoi_id: int) -> bool:
    """Đóng dấu chủ hồ sơ vào chuyến ở LẦN GHI ĐẦU. Trả True nếu vừa đóng dấu.

    Gọi ngay SAU khi cổng đã cho qua, nên `nguoi_id` luôn đúng bằng người mà `chu_ho_so` vừa trả
    về. Không commit — người gọi đang ở giữa một phiên ghi và sẽ commit một lượt.
    """
    if getattr(t, "chu_ho_so_id", None) or not nguoi_id:
        return False
    t.chu_ho_so_id = nguoi_id
    return True


def giao_ho_so(db: Session, u: User, t: Tour, nguoi_moi: User, ly_do: str) -> str:
    """Bàn giao hồ sơ quyết toán sang một người khác. Có lý do, có nhật ký, có dòng thời gian."""
    from app.api.deps import Gate, toan_quyen
    from app.services.products import event as EV

    cu_id = chu_ho_so(db, t)
    if not (u.role in GIAO_ROLES or u.id == cu_id or toan_quyen(u)):
        raise Gate("CONG_6", "Chỉ Trưởng phòng Điều hành hoặc chính người đang giữ hồ sơ mới bàn giao được")
    if t.status in TRANG_THAI_KHONG_GIAO:
        raise Gate("TRANG_THAI", "Quyết toán đã đóng số — bàn giao lúc này không đổi được gì trên số liệu")
    if nguoi_moi.role not in CHU_HO_SO_ROLES:
        raise Gate("CONG_6", f"Vai {nguoi_moi.role} không được giữ hồ sơ quyết toán. "
                             f"Chỉ: {', '.join(CHU_HO_SO_ROLES)}")
    if not nguoi_moi.active:
        raise Gate("CONG_6", "Tài khoản đã ngừng hoạt động")
    if nguoi_moi.id == cu_id:
        raise Gate("CONG_6", "Người này đang giữ hồ sơ rồi")
    if len((ly_do or "").strip()) < 20:
        raise Gate("QT_NHAP", "Bàn giao hồ sơ phải ghi lý do, tối thiểu 20 ký tự")

    cu = db.get(User, cu_id) if cu_id else None
    t.chu_ho_so_id = nguoi_moi.id
    ten_cu = cu.full_name if cu else "chưa có ai"
    EV(db, t, "giao_ho_so", u.username, ly_do.strip(),
       title=f"Bàn giao hồ sơ quyết toán: {ten_cu} → {nguoi_moi.full_name}")
    R.audit(db, u.username, u.role, "giao_ho_so_quyet_toan", f"tour:{t.code}",
            before={"chu_ho_so_id": cu_id, "chu_ho_so": ten_cu},
            after={"chu_ho_so_id": nguoi_moi.id, "chu_ho_so": nguoi_moi.full_name,
                   "ly_do": ly_do.strip()[:200],
                   # Chép lại vào nhật ký để người đọc sau này không phải tin vào lời hứa ở trên.
                   "thuong_chuyen_van_thuoc": (t.operator.full_name if t.operator else "")})
    db.commit()
    return (f"Hồ sơ quyết toán {t.code} đã chuyển từ {ten_cu} sang {nguoi_moi.full_name}. "
            f"Thưởng chuyến vẫn thuộc {t.operator.full_name if t.operator else 'người điều hành chuyến'}.")
