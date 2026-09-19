# -*- coding: utf-8 -*-
"""BÌNH LUẬN CÔNG KHAI DƯỚI BÀI ĐĂNG FANPAGE — nhận, giữ, và đưa vào hàng đợi cảnh báo.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO PHẢI NỐI RIÊNG MỘT LUỒNG NỮA
──────────────────────────────────────────────────────────────────────────────────────────────

Hộp thư đa kênh của VTOS nhận TIN NHẮN RIÊNG (`messages` webhook field). Bình luận dưới bài đăng
đi bằng một trường webhook KHÁC — `feed` — và tới dưới dạng `entry[].changes[]`, không phải
`entry[].messaging[]`. Đăng ký một trường không tự kéo theo trường kia, nên suốt thời gian qua
Fanpage của công ty vẫn nhận bình luận mà VTOS không thấy dòng nào.

Đây là khoảng trống ở đúng chỗ đau nhất: một khách bực NHẮN RIÊNG thì chỉ công ty đọc; một khách
bực BÌNH LUẬN dưới bài quảng cáo thì mọi người đang xem quảng cáo ấy đều đọc. Cái thứ hai mới là
thứ đồng hồ hai giờ sinh ra để trị.

──────────────────────────────────────────────────────────────────────────────────────────────
BA ĐIỀU TỆP NÀY GIỮ
──────────────────────────────────────────────────────────────────────────────────────────────

1. BÌNH LUẬN BỊ XOÁ THÌ GIỮ LẠI DÒNG. Facebook gửi `verb: "remove"` và KHÔNG gửi kèm nội dung.
   Mình đánh dấu `da_xoa` và giữ nguyên chữ đã nhận lúc đầu. Một bình luận bị xoá là bằng chứng
   nó đã TỪNG có, và nó thường bị xoá đúng vào lúc đáng giữ nhất — kể cả khi người xoá là người
   của mình.

2. KHÔNG CHẤM BÌNH LUẬN CỦA CHÍNH PAGE. Page trả lời dưới bài của mình cũng về qua cùng webhook.
   Chấm nó là để hàng đợi tự nuôi chính nó: mình trả lời một vụ khủng hoảng, câu trả lời mang đầy
   từ đỏ, và nó lại nhảy lên đầu hàng đợi như một vụ mới.

3. KHÔNG DỰNG NÚT ẨN BÌNH LUẬN, và đây là một lựa chọn chứ không phải thiếu sót. Ẩn một bình luận
   chê là cách nhanh nhất biến một khách bực thành một bài đăng "Vietourist xoá bình luận của
   tôi" — thứ lan xa hơn hẳn bình luận gốc. Công cụ nào dễ bấm thì sẽ được bấm lúc 11 giờ đêm bởi
   người đang hoảng. Muốn ẩn thì vào Facebook mà ẩn, có cân nhắc; VTOS không đưa sẵn cái nút ấy.

   Cùng lẽ đó, tệp này KHÔNG gửi gì ra ngoài. Trả lời công khai là PHÁT NGÔN, và phát ngôn đã có
   một cửa với một vai đã ký (P.TGĐ Marketing, `pr_vai_phat_ngon`) — không mở cửa thứ hai đi vòng.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.marketing import FbBinhLuan

# `item` khác ("post", "reaction", "share", "status"...) không phải bình luận. Đếm để biết webhook
# còn sống, nhưng không ghi dòng: một lượt thả tim không phải một việc ai đó phải đọc.
ITEM_NHAN = ("comment",)


def _gio(v) -> datetime:
    """`created_time` của Facebook là giây từ 1970. Có bản gửi chuỗi ISO, nên nhận cả hai.

    Không parse được thì lấy GIỜ HIỆN TẠI chứ không bỏ dòng: mốc sai vài giây còn hơn mất hẳn một
    bình luận vì nhà cung cấp đổi định dạng.
    """
    if v in (None, ""):
        return datetime.now()
    try:
        return datetime.fromtimestamp(int(v))
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.now()


def ghi(db: Session, value: dict, page_id: str = "") -> tuple[FbBinhLuan | None, str]:
    """Nhận MỘT phần tử `entry[].changes[].value`. Trả (dòng, việc đã làm).

    `việc` là một trong: "moi" / "sua" / "xoa" / "bo_qua". Trả ra để cửa webhook đếm được và để
    phép thử đọc được — một hàm chỉ trả None/khác None thì không phân biệt nổi "đã ghi" với
    "cố ý bỏ".
    """
    if str(value.get("item") or "") not in ITEM_NHAN:
        return None, "bo_qua"
    cid = str(value.get("comment_id") or "").strip()
    if not cid:
        return None, "bo_qua"

    verb = str(value.get("verb") or "add").lower()
    tu = value.get("from") or {}
    tac_gia_id = str(tu.get("id") or "")
    cu = db.execute(select(FbBinhLuan).where(FbBinhLuan.comment_id == cid)).scalars().first()

    if verb in ("remove", "hide"):
        # KHÔNG xoá dòng. Xem đầu tệp. Chưa từng thấy bình luận này (webhook `add` rớt mất) thì vẫn
        # dựng một dòng rỗng có dấu `da_xoa`: biết rằng đã có một bình luận bị gỡ vẫn hơn không
        # biết gì.
        if cu is None:
            cu = FbBinhLuan(comment_id=cid, post_id=str(value.get("post_id") or ""),
                            page_id=page_id, tac_gia_id=tac_gia_id,
                            tac_gia_ten=str(tu.get("name") or "")[:120],
                            noi_dung="", tao_luc=_gio(value.get("created_time")))
            db.add(cu)
        cu.da_xoa = True
        db.flush()
        return cu, "xoa"

    noi_dung = str(value.get("message") or "")
    la_page = bool(page_id) and tac_gia_id == str(page_id)

    if cu is None:
        cu = FbBinhLuan(
            comment_id=cid,
            post_id=str(value.get("post_id") or "")[:64],
            parent_id=str(value.get("parent_id") or "")[:64],
            page_id=(page_id or "")[:40],
            tac_gia_id=tac_gia_id[:64],
            tac_gia_ten=str(tu.get("name") or "")[:120],
            noi_dung=noi_dung,
            link=str(value.get("permalink_url") or "")[:400],
            la_cua_page=la_page,
            tao_luc=_gio(value.get("created_time")),
            nhan_luc=datetime.now(),
        )
        db.add(cu)
        db.flush()
        return cu, "moi"

    # Sửa: GIỮ LẠI BẢN CŨ trong nội dung, không đè. Người ta sửa một bình luận gắt thành một bình
    # luận nhẹ rồi chụp màn hình bảo "tôi có nói gì đâu"; đè mất bản cũ là mất đúng chỗ ấy.
    if noi_dung and noi_dung != cu.noi_dung:
        cu.noi_dung = (cu.noi_dung + "\n--- sửa lúc " + f"{datetime.now():%d/%m %H:%M}" + " ---\n"
                       + noi_dung) if cu.noi_dung else noi_dung
        cu.da_sua = True
    cu.da_xoa = False
    db.flush()
    return cu, "sua"


def nhan_changes(db: Session, entry: dict) -> dict:
    """Toàn bộ `entry[].changes[]` của một entry. Chỉ đọc trường `feed`."""
    page_id = str(entry.get("id") or "")
    dem = {"moi": 0, "sua": 0, "xoa": 0, "bo_qua": 0}
    for ch in entry.get("changes") or []:
        if str(ch.get("field") or "") != "feed":
            dem["bo_qua"] += 1
            continue
        _bl, viec = ghi(db, ch.get("value") or {}, page_id)
        dem[viec] = dem.get(viec, 0) + 1
    return dem


def dang_doc_duoc(bl: FbBinhLuan) -> bool:
    """Dòng đáng đưa cho bộ lọc chấm: có chữ, không phải của Page."""
    return bool((bl.noi_dung or "").strip()) and not bl.la_cua_page


def trong_cua_so(db: Session, ngay: int, bay_gio: datetime | None = None, tran: int = 5000) -> list:
    moc = (bay_gio or datetime.now()) - timedelta(days=max(1, int(ngay)))
    q = (select(FbBinhLuan)
         .where(FbBinhLuan.tao_luc >= moc, FbBinhLuan.la_cua_page.is_(False))
         .order_by(FbBinhLuan.tao_luc.desc()).limit(tran + 1))
    return list(db.execute(q).scalars().all())


def dem_cum_bai(db: Session, post_ids: list[str], phut: int,
                bay_gio: datetime | None = None) -> dict:
    """Số bình luận của mỗi BÀI ĐĂNG trong `phut` phút gần nhất.

    Dốc của bình luận đếm theo BÀI, không theo người: một vụ thật trên Fanpage là nhiều người khác
    nhau cùng đổ vào một bài, chứ không phải một người nói nhiều lần. Khác hẳn hình của tin nhắn
    riêng, nơi dốc là một người nhắn dồn — nên hai chỗ đếm hai kiểu, cố ý.
    """
    if not post_ids:
        return {}
    moc = (bay_gio or datetime.now()) - timedelta(minutes=max(1, int(phut)))
    rows = db.execute(
        select(FbBinhLuan.post_id, func.count(FbBinhLuan.id))
        .where(FbBinhLuan.post_id.in_(post_ids), FbBinhLuan.tao_luc >= moc,
               FbBinhLuan.la_cua_page.is_(False))
        .group_by(FbBinhLuan.post_id)).all()
    return {p: n for p, n in rows}
