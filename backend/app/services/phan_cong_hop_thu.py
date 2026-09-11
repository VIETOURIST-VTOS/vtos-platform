# -*- coding: utf-8 -*-
"""PQ-9 · Giao chủ cho hội thoại khách – luân phiên (Chủ tịch chọn 11/9/2026).

Đo bản đang chạy sáng 11/9: 100 trên 100 hội thoại để trống sales_id. Ba cái đã quá hạn SLA. AI đã
trả lời thay bốn cái. Cột sales_id có sẵn từ đầu và không ai điền – hệ thống chưa bao giờ có luật
nói hội thoại mới về thì vào tay ai, nên nó không vào tay ai cả.

Đây không phải chuyện hộp thư. Toàn bộ bảng luồng công việc dựng lên quanh nguyên tắc MỘT CỬA: mỗi
bước có đúng một người đẩy được, và người khác không làm thay được. Ở khâu đầu tiên của chuỗi bán
hàng – lúc khách vừa nhắn tin – nguyên tắc ấy không có cửa nào.

Hệ quả không nằm ở chỗ chậm trả lời. Nó nằm ở chỗ: khi không ai là chủ, thì lúc có chuyện cũng
không ai là người phải trả lời câu "vì sao khách này bị bỏ".

──────────────────────────────────────────────────────────────────────────────────────────────
CÁCH CHIA: luân phiên theo TẢI ĐANG MỞ, không theo con trỏ quay vòng.

Chủ tịch chọn "luân phiên". Có hai cách hiện thực và chúng khác nhau ở chỗ quan trọng:

  · Con trỏ quay vòng – nhớ "lần trước tới ai", lần sau đưa người kế tiếp. Dễ hiểu, nhưng phải lưu
    con trỏ, và con trỏ thì lệch: ai nghỉ một buổi là bị nhảy qua vĩnh viễn, ai vừa nhận mười hội
    thoại nặng vẫn tới lượt như người vừa nhận một.

  · Theo tải đang mở – đưa cho người đang giữ ÍT hội thoại mở nhất. Vẫn là luân phiên (mỗi người
    một cái rồi mới quay lại), nhưng tự sửa được: nghỉ một buổi thì hôm sau tải thấp và nhận bù,
    đóng nhanh thì nhận thêm. Không cần lưu con trỏ nên không có gì để lệch.

Chọn cách thứ hai. Hòa tải thì ưu tiên người LÂU NHẤT chưa được giao – để hai người cùng tải 0
không phải lúc nào cũng rơi vào người có id nhỏ hơn.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import User, ROLES
from app.models.crm import Conversation

# Vai trò nằm trong vòng luân phiên. Chỉ người TRỰC TIẾP bán hàng: trưởng nhóm có tên ở đây vì ở
# Vietourist trưởng nhóm vẫn giữ khách của mình, còn Trưởng phòng và Giám đốc Kinh doanh thì không –
# đưa hội thoại cho người quản lý là cách chắc chắn để nó nằm im trong hộp thư của người bận nhất.
VAI_TRO_NHAN = ("nv_kd", "tn_kd")

# Trạng thái coi là ĐANG MỞ khi đếm tải. "dong" là đã xong; số còn lại đều còn phải trông.
TRANG_THAI_DONG = ("dong",)

# Lý do không giao được – mỗi lý do là một dòng đếm được trên màn hình, không phải một khoảng lặng.
KHONG_CO_NGUOI = "khong_co_nguoi_trong_vong_luan_phien"
DA_CO_CHU = "da_co_chu"


def nguoi_trong_vong(db: Session) -> list[User]:
    """Người đang hoạt động, giữ vai trò trực tiếp bán hàng. Khóa tài khoản là ra khỏi vòng ngay."""
    return list(db.execute(
        select(User).where(User.active == True, User.role.in_(VAI_TRO_NHAN))  # noqa: E712
        .order_by(User.id)).scalars())


def tai_dang_mo(db: Session) -> dict[int, int]:
    """Mỗi người đang giữ bao nhiêu hội thoại chưa đóng."""
    rows = db.execute(
        select(Conversation.sales_id, func.count(Conversation.id))
        .where(Conversation.sales_id.isnot(None),
               Conversation.status.notin_(TRANG_THAI_DONG))
        .group_by(Conversation.sales_id)).all()
    return {int(uid): int(n) for uid, n in rows if uid is not None}


def _lan_giao_gan_nhat(db: Session) -> dict[int, datetime]:
    """Lần gần nhất mỗi người được giao một hội thoại – dùng để phá thế hòa tải."""
    rows = db.execute(
        select(Conversation.sales_id, func.max(Conversation.created_at))
        .where(Conversation.sales_id.isnot(None))
        .group_by(Conversation.sales_id)).all()
    return {int(uid): t for uid, t in rows if uid is not None and t is not None}


def nguoi_ke_tiep(db: Session) -> User | None:
    """Người đến lượt: tải đang mở thấp nhất; hòa thì người lâu nhất chưa được giao.

    Trả None khi không còn ai trong vòng – KHÔNG rơi xuống một người mặc định nào đó. Giao bừa cho
    người quản lý để danh sách trông sạch là cách biến một lỗ hổng đếm được thành một lỗ hổng không
    đếm được nữa.
    """
    ds = nguoi_trong_vong(db)
    if not ds:
        return None
    tai = tai_dang_mo(db)
    gan = _lan_giao_gan_nhat(db)
    cu = datetime.min
    return min(ds, key=lambda u: (tai.get(u.id, 0), gan.get(u.id, cu), u.id))


def giao(db: Session, c: Conversation, *, boi: str = "") -> dict:
    """Giao MỘT hội thoại chưa có chủ. Đã có chủ thì không đụng tới.

    Không đổi chủ ở đây, và đó là chủ ý: đổi chủ là một quyết định của người quản lý, có người chịu
    trách nhiệm và phải ghi vết. Một hàm chạy nền mà đổi chủ được thì chủ sở hữu chỉ là tạm thời,
    và "một cửa" mất nghĩa ngay từ chỗ ấy.
    """
    if c.sales_id:
        return {"da_giao": False, "ly_do": DA_CO_CHU, "sales_id": c.sales_id}
    u = nguoi_ke_tiep(db)
    if u is None:
        return {"da_giao": False, "ly_do": KHONG_CO_NGUOI, "sales_id": None}
    c.sales_id = u.id
    if c.status == "mo":
        c.status = "cho_sale"
    c.summary = (c.summary + " | " if c.summary else "") + \
        f"{datetime.now():%d/%m %H:%M} giao luân phiên cho {u.full_name}" + (f" ({boi})" if boi else "")
    return {"da_giao": True, "ly_do": "", "sales_id": u.id, "ten": u.full_name}


def giao_het_chua_co_chu(db: Session, *, boi: str = "") -> dict:
    """Quét hộp thư, giao mọi hội thoại chưa có chủ. Gọi từ vòng lặp robot và từ nút trên màn hình.

    Đếm cả phần KHÔNG giao được: một lần quét trả về "đã giao 0" mà không nói vì sao thì người đọc
    sẽ tưởng hộp thư đã sạch.
    """
    chua = list(db.execute(
        select(Conversation).where(Conversation.sales_id.is_(None),
                                   Conversation.status.notin_(TRANG_THAI_DONG))
        .order_by(Conversation.last_in_at.is_(None), Conversation.last_in_at, Conversation.id)).scalars())
    da = 0
    ly_do: dict[str, int] = {}
    for c in chua:
        kq = giao(db, c, boi=boi)
        if kq["da_giao"]:
            da += 1
        else:
            ly_do[kq["ly_do"]] = ly_do.get(kq["ly_do"], 0) + 1
    return {"xet": len(chua), "da_giao": da, "khong_giao_duoc": ly_do,
            "con_chua_co_chu": len(chua) - da}


def bao_cao(db: Session) -> dict:
    """Dòng "chưa có chủ" phải ĐẾM ĐƯỢC và nằm ngay trên màn hình.

    Cùng quy ước với dữ liệu chưa gán pháp nhân: chưa gán là MỘT DÒNG RIÊNG, không gộp im lặng vào
    người nào. Ngày 11/9 con số ấy là 100 trên 100 và không màn hình nào nói ra.
    """
    tong = int(db.execute(select(func.count(Conversation.id))
                          .where(Conversation.status.notin_(TRANG_THAI_DONG))).scalar() or 0)
    chua = int(db.execute(select(func.count(Conversation.id))
                          .where(Conversation.sales_id.is_(None),
                                 Conversation.status.notin_(TRANG_THAI_DONG))).scalar() or 0)
    tai = tai_dang_mo(db)
    ds = nguoi_trong_vong(db)
    ke = nguoi_ke_tiep(db)
    return {
        "cach_chia": "luân phiên theo tải đang mở",
        "vai_tro_trong_vong": [{"ma": v, "ten": ROLES.get(v, v)} for v in VAI_TRO_NHAN],
        "so_nguoi_trong_vong": len(ds),
        "hoi_thoai_dang_mo": tong,
        "chua_co_chu": chua,
        "nguoi_ke_tiep": {"id": ke.id, "ten": ke.full_name} if ke else None,
        "tai": [{"id": u.id, "ten": u.full_name, "vai_tro": ROLES.get(u.role, u.role),
                 "dang_giu": tai.get(u.id, 0)} for u in ds],
        "canh_bao": ("Không có ai trong vòng luân phiên – hội thoại mới sẽ không vào tay ai."
                     if not ds else ""),
        "ghi_chu": ("Chưa có chủ là một dòng riêng, không gộp vào ai. Robot chỉ GIAO hội thoại còn "
                    "trống; ĐỔI chủ là quyết định của người quản lý và đi qua cửa riêng."),
    }
