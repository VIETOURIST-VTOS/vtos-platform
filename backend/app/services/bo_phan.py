# -*- coding: utf-8 -*-
"""Đợt R3b 17/10/2026 — danh mục bộ phận: nạp khuôn, đọc, sửa, ngừng dùng, và gán chữ cũ.

TÁM DÒNG KHUÔN là cơ cấu Vietourist Holdings đang chạy, anh Tuấn duyệt 17/10/2026. Đây là KHUÔN,
không phải số liệu: HCNS sửa tên, thêm dòng, hoặc ngừng dùng bất kỳ dòng nào.

GÁN CHỮ CŨ KHÔNG SỬA MỘT DÒNG SỔ NÀO — xem `gan()`. Chữ cũ vào bút danh, sổ giữ nguyên.

MÁY KHÔNG ĐOÁN. `chua_gan()` chỉ LIỆT KÊ những chữ đang có trong sổ mà chưa bộ phận nào nhận, kèm
số dòng; người chọn mã. Đoán "IT" là "CNTT" thì đúng chín lần rồi sai lần thứ mười, và không ai
biết lần nào là lần thứ mười.
"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.bo_phan import BoPhan

# Khuôn cơ cấu — anh Tuấn duyệt 17/10/2026.
MAC_DINH = (
    ("BP_HCNS", "Hành chính – Nhân sự", 10),
    ("BP_KT",   "Kế toán",              20),
    ("BP_DH",   "Điều hành",            30),
    ("BP_KD",   "Kinh doanh",           40),
    ("BP_HDV",  "Hướng dẫn",            50),
    ("BP_XE",   "Đội xe",               60),
    ("BP_CNTT", "Công nghệ thông tin",  70),
    ("BP_MKT",  "Marketing",            80),
)


def nap_mac_dinh(db: Session) -> int:
    """Gieo khuôn. Mã nào đã có thì GIỮ NGUYÊN — chạy lại không đè lên bản HCNS đã sửa."""
    co = {m for (m,) in db.execute(select(BoPhan.ma)).all()}
    them = 0
    for ma, ten, tt in MAC_DINH:
        if ma in co:
            continue
        db.add(BoPhan(ma=ma, ten=ten, thu_tu=tt, dung=True))
        them += 1
    if them:
        db.commit()
    return them


def _ra(b: BoPhan) -> dict:
    return {"id": b.id, "ma": b.ma, "ten": b.ten, "thu_tu": b.thu_tu, "dung": b.dung,
            "but_danh": [x for x in (b.but_danh or "").split("\n") if x.strip()],
            "ghi_chu": b.ghi_chu or ""}


def danh_sach(db: Session, ca_ngung: bool = False) -> list[dict]:
    q = select(BoPhan).order_by(BoPhan.thu_tu, BoPhan.ma)
    if not ca_ngung:
        q = q.where(BoPhan.dung.is_(True))
    return [_ra(b) for b in db.execute(q).scalars().all()]


def ma_dang_dung(db: Session) -> set[str]:
    return {m for (m,) in db.execute(select(BoPhan.ma).where(BoPhan.dung.is_(True))).all()}


def them(db: Session, data: dict) -> BoPhan:
    ma = str(data.get("ma") or "").strip().upper()[:20]
    if not ma:
        raise ValueError("Thiếu mã bộ phận")
    if db.execute(select(BoPhan).where(BoPhan.ma == ma)).scalar_one_or_none():
        raise ValueError(f"Mã {ma} đã có trong danh mục")
    b = BoPhan(ma=ma, ten=str(data.get("ten") or ma)[:200],
               thu_tu=int(data.get("thu_tu") or 100), dung=True,
               ghi_chu=str(data.get("ghi_chu") or ""))
    db.add(b)
    db.commit()
    return b


def sua(db: Session, bid: int, data: dict) -> BoPhan:
    """Sửa tên / thứ tự / ghi chú, và BẬT-TẮT dùng.

    MÃ KHÔNG ĐỔI ĐƯỢC — cùng lẽ với danh mục khoản mục của Đợt R2: bút toán cũ và tài sản cũ trỏ
    vào mã này, đổi mã là làm mồ côi mọi dòng đã ghi, mà kỳ đã khoá thì không sửa lại được.
    """
    b = db.get(BoPhan, bid)
    if not b:
        raise ValueError(f"Không có bộ phận id={bid}")
    if "ma" in data and str(data["ma"]).strip().upper() != b.ma:
        raise ValueError("Mã bộ phận không đổi được — ngừng dùng dòng cũ rồi thêm dòng mới")
    for k in ("ten", "thu_tu", "dung", "ghi_chu"):
        if k in data and data[k] is not None:
            setattr(b, k, data[k])
    db.commit()
    return b


def chua_gan(db: Session) -> dict:
    """Những chữ đang nằm trong sổ mà chưa bộ phận nào nhận, kèm số dòng. KHÔNG đoán hộ ai.

    Đếm cả dòng ĐỂ TRỐNG và trả riêng: để trống nghĩa là chưa ai khai, khác hẳn với một chữ đã gõ
    mà chưa ai gán mã. Gộp hai thứ ấy thì người đọc không biết phải đi hỏi ai.
    """
    from app.models.accounting import JournalLine
    ma = {m for (m,) in db.execute(select(BoPhan.ma)).all()}
    danh = set()
    for (bd,) in db.execute(select(BoPhan.but_danh)).all():
        danh |= {x.strip() for x in (bd or "").split("\n") if x.strip()}
    rows = db.execute(
        select(JournalLine.bo_phan, func.count(JournalLine.id))
        .group_by(JournalLine.bo_phan)).all()
    la, trong = [], 0
    for chu, n in rows:
        chu = chu or ""
        if not chu.strip():
            trong += int(n)
        elif chu not in ma and chu not in danh:
            la.append({"chu": chu, "so_dong": int(n)})
    la.sort(key=lambda x: -x["so_dong"])
    return {"chua_gan": la, "de_trong": trong}


def gan(db: Session, chu: str, ma: str) -> dict:
    """Nhận một chữ cũ về làm BÚT DANH của một bộ phận. KHÔNG SỬA MỘT DÒNG SỔ NÀO.

    VÌ SAO KHÔNG `UPDATE journal_lines`: "cntt → BP_CNTT" là quyết định của người HÔM NAY áp lên
    những dòng ĐÃ GHI. Kỳ đã khoá thì không ai được sửa — đó là lẽ của việc khoá sổ, và một bản vá
    chạy đè lên sổ đã khoá là thứ kiểm toán không dựng lại được. Giữ sổ nguyên chữ nó đã ghi, báo
    cáo tra ngược qua bút danh; gán nhầm thì xoá một bút danh, không phải dựng lại sổ.
    """
    chu = (chu or "").strip()
    if not chu:
        raise ValueError("Thiếu chữ cần gán")
    b = db.execute(select(BoPhan).where(BoPhan.ma == (ma or "").strip().upper())).scalar_one_or_none()
    if not b:
        raise ValueError(f"Không có bộ phận mã {ma}")
    for (bid, bd) in db.execute(select(BoPhan.id, BoPhan.but_danh)).all():
        if chu in {x.strip() for x in (bd or "").split("\n") if x.strip()}:
            raise ValueError(f"Chữ '{chu}' đã là bút danh của một bộ phận khác")
    if chu == b.ma:
        raise ValueError("Chữ trùng chính mã bộ phận — không cần bút danh")
    cu = [x for x in (b.but_danh or "").split("\n") if x.strip()]
    b.but_danh = "\n".join(cu + [chu])
    db.commit()
    return {"ma": b.ma, "but_danh": cu + [chu]}


def bo_but_danh(db: Session, ma: str, chu: str) -> dict:
    """Gỡ một bút danh. Có cửa gỡ vì gán nhầm phải sửa được, nếu không người ta sẽ ngại gán."""
    b = db.execute(select(BoPhan).where(BoPhan.ma == (ma or "").strip().upper())).scalar_one_or_none()
    if not b:
        raise ValueError(f"Không có bộ phận mã {ma}")
    con = [x for x in (b.but_danh or "").split("\n") if x.strip() and x.strip() != (chu or "").strip()]
    b.but_danh = "\n".join(con)
    db.commit()
    return {"ma": b.ma, "but_danh": con}
