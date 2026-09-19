# -*- coding: utf-8 -*-
"""NỐI TÀI KHOẢN VTOS VỚI ZALO, và chặn người của công ty trở thành khách hàng giả.

──────────────────────────────────────────────────────────────────────────────────────────────
HAI VIỆC, VÀ VIỆC THỨ HAI LÀ CÁI KHÔNG AI NGỜ
──────────────────────────────────────────────────────────────────────────────────────────────

1. NỐI. Hàm gửi tin OA cần một UID Zalo. Người dùng tự xin một mã trong VTOS, tự nhắn mã ấy vào OA
   công ty; webhook nhận được thì Zalo đã nói cho mình biết UID — không ai phải gõ nó, không ai
   tra hộ ai, nên không có đường nào để nối nhầm UID của người này vào tài khoản người kia.

2. CHẶN LEAD GIẢ. Webhook OA đang xử lý `follow` và `user_send_text` bằng cách TẠO MỘT LEAD, kênh
   "Zalo OA", số điện thoại giả dạng `zalo…`. Nó viết cho KHÁCH và đúng với khách. Nhưng nó không
   phân biệt được khách với NGƯỜI CỦA CÔNG TY.

   Hệ quả đo được ngay hôm nay: Chủ tịch, TGĐ và P.TGĐ Marketing bấm "Quan tâm" OA để nhận cảnh
   báo khủng hoảng — và ba người lãnh đạo biến thành ba khách hàng tiềm năng trong sổ lead, chảy
   thẳng vào mẫu số của TỶ LỆ CHỐT LEAD mà Sales đang được đo bằng.

   Không ai phát hiện ra. Người ta chỉ thấy "dạo này chốt kém". Đúng cùng một hình với việc đổ
   bình luận Fanpage vào hộp thư, chỉ khác là lỗi này đã nằm sẵn trong hệ từ trước.

   Nên: UID nào đã nối với một tài khoản nhân viên thì KHÔNG tạo lead, và cũng KHÔNG đẩy vào hộp
   thư khách — vì hộp thư khách có đồng hồ SLA của Sales, và Sales không nợ Chủ tịch một câu trả
   lời trong mười lăm phút.

──────────────────────────────────────────────────────────────────────────────────────────────
ĐỘ MẠNH CỦA MÃ — viết ra để người sau khỏi phải đoán
──────────────────────────────────────────────────────────────────────────────────────────────

8 ký tự trên bảng 32 ký tự = 32^8 ≈ 1,1 nghìn tỷ khả năng, sống 10 phút, dùng một lần. Kẻ muốn
đoán phải nhắn hàng tỷ tin vào OA trong mười phút — Zalo chặn trước khi tới lượt mình chặn.

VẪN ĐẾM SỐ LẦN NHẮN SAI (`lan_sai`), nhưng KHÔNG khoá theo nó. Khoá theo số lần sai ở đây mở ra một
cửa mới: ai biết mình đang bị nhắm có thể cố tình nhắn sai để khoá mã của người khác. Con số ấy để
NHÌN — lớn bất thường nghĩa là có người đang dò, và biết trước thì hơn.

Bảng chữ bỏ hẳn I, O, 0, 1: người ta đọc mã trên màn hình rồi gõ sang điện thoại, và bốn ký tự ấy
là bốn cách phổ biến nhất để một mã đúng bị gõ thành sai.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.zalo_noi import ZaloMaNoi, ZaloNoiTaiKhoan

BANG_CHU = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DAI_MA = 8
SONG_PHUT = 10


def sinh_ma() -> str:
    return "".join(secrets.choice(BANG_CHU) for _ in range(DAI_MA))


def chuan(s: str) -> str:
    """Bỏ khoảng trắng và viết hoa. Người ta nhắn 'ma cua toi: abcd efgh' hoặc gõ thường — mã vẫn
    là mã ấy, và bắt người dùng gõ chính xác từng dấu cách chỉ tạo ra những lần nối hỏng vô cớ."""
    return "".join(ch for ch in (s or "").upper() if ch in BANG_CHU)


def tao_ma(db: Session, u: User) -> ZaloMaNoi:
    """Mã mới cho CHÍNH người đang đăng nhập. Mã cũ chưa dùng bị huỷ ngay.

    Huỷ mã cũ chứ không để song song: hai mã cùng sống nghĩa là một mã người ta tưởng đã hết hạn
    vẫn nối được, và cửa sổ mười phút mất hết ý nghĩa.
    """
    for cu in db.execute(select(ZaloMaNoi).where(ZaloMaNoi.user_id == u.id,
                                                 ZaloMaNoi.da_dung.is_(False))).scalars():
        cu.da_dung = True
    m = ZaloMaNoi(user_id=u.id, ma=sinh_ma(),
                  het_han=datetime.now() + timedelta(minutes=SONG_PHUT))
    db.add(m)
    db.flush()
    return m


def _ma_song(db: Session, ma: str, bay_gio: datetime | None = None) -> ZaloMaNoi | None:
    gio = bay_gio or datetime.now()
    return db.execute(
        select(ZaloMaNoi).where(ZaloMaNoi.ma == ma, ZaloMaNoi.da_dung.is_(False),
                                ZaloMaNoi.het_han > gio).order_by(ZaloMaNoi.id.desc())).scalars().first()


def thu_ma(db: Session, uid: str, text: str, bay_gio: datetime | None = None) -> dict:
    """Thử coi tin khách vừa nhắn vào OA có phải một mã nối không.

    Trả về {"noi": bool, ...}. `noi=False` nghĩa là tin thường — nơi gọi cứ xử lý như cũ.

    KHÔNG báo lại cho người nhắn biết "mã sai" hay "mã đã hết hạn" một cách phân biệt: hai câu ấy
    nói cho kẻ đang dò biết nó đã đoán trúng một mã từng tồn tại.
    """
    ma = chuan(text)
    if len(ma) != DAI_MA:
        return {"noi": False, "ly_do": "khong_phai_ma"}

    m = _ma_song(db, ma, bay_gio)
    if m is None:
        het = db.execute(select(ZaloMaNoi).where(ZaloMaNoi.ma == ma)).scalars().first()
        if het is not None:
            het.lan_sai = (het.lan_sai or 0) + 1
            db.flush()
        return {"noi": False, "ly_do": "ma_khong_dung"}

    u = db.get(User, m.user_id)
    if u is None:
        return {"noi": False, "ly_do": "khong_con_tai_khoan"}

    # UID này đã nối với người khác rồi thì DỪNG, không lặng lẽ chuyển sang tài khoản mới: một
    # chiếc điện thoại nhận cảnh báo của hai người là đúng cái tình huống bảng này sinh ra để chặn.
    da_co_uid = db.execute(select(ZaloNoiTaiKhoan)
                           .where(ZaloNoiTaiKhoan.zalo_uid == uid)).scalars().first()
    if da_co_uid is not None and da_co_uid.user_id != u.id:
        return {"noi": False, "ly_do": "uid_da_noi_nguoi_khac"}

    cu = db.execute(select(ZaloNoiTaiKhoan)
                    .where(ZaloNoiTaiKhoan.user_id == u.id)).scalars().first()
    if cu is None:
        cu = ZaloNoiTaiKhoan(user_id=u.id, zalo_uid=uid, gan_boi=u.username)
        db.add(cu)
    else:
        cu.zalo_uid = uid
        cu.gan_luc = datetime.now()
        cu.gan_boi = u.username
    m.da_dung = True
    db.flush()
    return {"noi": True, "user_id": u.id, "username": u.username,
            "ho_ten": getattr(u, "full_name", "") or u.username}


def la_nhan_vien(db: Session, uid: str) -> bool:
    """UID này đã nối với một tài khoản VTOS chưa. Dùng để KHÔNG tạo lead, KHÔNG đẩy vào hộp thư."""
    if not uid:
        return False
    return db.execute(select(ZaloNoiTaiKhoan.id)
                      .where(ZaloNoiTaiKhoan.zalo_uid == uid)).scalars().first() is not None


def tai_khoan_cua(db: Session, uid: str) -> User | None:
    n = db.execute(select(ZaloNoiTaiKhoan).where(ZaloNoiTaiKhoan.zalo_uid == uid)).scalars().first()
    return db.get(User, n.user_id) if n else None


def uid_cua(db: Session, user_id: int) -> str:
    n = db.execute(select(ZaloNoiTaiKhoan)
                   .where(ZaloNoiTaiKhoan.user_id == int(user_id))).scalars().first()
    return n.zalo_uid if n else ""


def uid_theo_vai(db: Session, vai: list[str] | tuple) -> list[tuple[User, str]]:
    """Mọi tài khoản ĐANG HOẠT ĐỘNG mang một trong các vai ấy, kèm UID Zalo (rỗng = chưa nối).

    Trả CẢ người chưa nối, cố ý. Cửa báo động cần biết "ba người phải báo, hai người tới được" —
    một danh sách chỉ gồm người nối rồi sẽ báo cáo 2/2 thành công và giấu mất người thứ ba.
    """
    q = select(User).where(User.role.in_(list(vai)))
    if hasattr(User, "active"):
        q = q.where(User.active.is_(True))
    ra = []
    for u in db.execute(q.order_by(User.id)).scalars():
        ra.append((u, uid_cua(db, u.id)))
    return ra


def go_noi(db: Session, u: User) -> bool:
    n = db.execute(select(ZaloNoiTaiKhoan).where(ZaloNoiTaiKhoan.user_id == u.id)).scalars().first()
    if n is None:
        return False
    db.delete(n)
    db.flush()
    return True


def trang_thai(db: Session, u: User) -> dict:
    uid = uid_cua(db, u.id)
    return {
        "da_noi": bool(uid),
        # KHÔNG trả UID đầy đủ ra màn hình. Nó là mã định danh của một người trên Zalo; hiện đủ ra
        # thì nó nằm trong ảnh chụp màn hình, trong nhật ký trình duyệt, trong mọi chỗ người ta dán.
        # Bốn số cuối đủ để người dùng nhận ra máy nào đang nối.
        "duoi_uid": uid[-4:] if uid else "",
    }
