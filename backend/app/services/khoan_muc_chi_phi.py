# -*- coding: utf-8 -*-
"""Đợt R2 15/10/2026 — danh mục khoản mục chi phí: nạp khuôn, đọc, sửa, ngừng dùng.

MƯỜI DÒNG KHUÔN là chiều phân tích của ngành tour, lấy đúng cách Vietourist đã chia giá vốn một
đoàn trên bảng quyết toán: landtour, vé máy bay, khách sạn, ăn uống, vé tham quan, hướng dẫn viên,
bảo hiểm, visa, xe, và một ô "khác" có chủ đích hẹp.

Vì sao có "KHAC" mà vẫn không sợ mọi thứ đổ vào đó: `KM_KHAC` để riêng một tên hằng, và phép thử
`test_r2_8` canh tỷ trọng của nó. Một chiều phân tích mà 60% số tiền rơi vào "khác" thì nó không
còn là chiều phân tích nữa — nó là một cột rỗng đội lốt.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.khoan_muc_chi_phi import KhoanMucChiPhi, NHOM_KHOAN_MUC

KM_KHAC = "KM_KHAC"

# ma, ten, nhom, thu_tu
MAC_DINH = [
    ("KM_LAND",  "Landtour / dịch vụ trọn gói mua của đối tác",   "gia_von", 10),
    ("KM_VEMB",  "Vé máy bay",                                    "gia_von", 20),
    ("KM_KS",    "Khách sạn / lưu trú",                           "gia_von", 30),
    ("KM_AN",    "Ăn uống",                                       "gia_von", 40),
    ("KM_VETQ",  "Vé tham quan / vé thắng cảnh",                  "gia_von", 50),
    ("KM_HDV",   "Hướng dẫn viên",                                "gia_von", 60),
    ("KM_BH",    "Bảo hiểm du lịch",                              "gia_von", 70),
    ("KM_VISA",  "Visa / thủ tục xuất nhập cảnh",                 "gia_von", 80),
    ("KM_XE",    "Vận chuyển đường bộ",                           "gia_von", 90),
    # ĐỢT R3a 16/10/2026 — ba mã mở thêm vì 55 mã của danh mục quyết toán tour không ghép hết
    # được vào mười mã cũ. Mở mã mới chứ KHÔNG đổ vào KM_KHAC: đổ vào đó thì tiền vận chuyển
    # đường thuỷ, tiền quà tặng và phí ngân hàng nằm lẫn trong một dòng "khác", và báo cáo theo
    # khoản mục mất đúng phần người đọc muốn nhìn. Chủ tịch chốt 16/10/2026.
    ("KM_VCK",   "Vận chuyển khác (tàu hoả, tàu thuỷ, ca nô)",     "gia_von", 95),
    ("KM_QUA",   "Quà tặng và vật phẩm cho khách",                "gia_von", 100),
    ("KM_PHI",   "Phí và lệ phí khác của chuyến",                 "gia_von", 110),
    (KM_KHAC,    "Chi phí tour khác",                             "gia_von", 999),
]


def nap_mac_dinh(db: Session) -> int:
    """Nạp mười dòng khuôn. Chạy được nhiều lần — mã nào đã có thì GIỮ NGUYÊN.

    Giữ nguyên chứ không đè, cùng lẽ với `hach_toan.nap_mac_dinh`: Kế toán đổi tên "Vận chuyển
    đường bộ" thành "Xe" rồi mà một lần khởi động lại đổi ngược về thì bảng không còn là của họ.
    """
    co = {k.ma for k in db.execute(select(KhoanMucChiPhi)).scalars()}
    them = 0
    for ma, ten, nhom, tt in MAC_DINH:
        if ma in co:
            continue
        db.add(KhoanMucChiPhi(ma=ma, ten=ten[:200], nhom=nhom, thu_tu=tt, dung=True))
        them += 1
    if them:
        db.commit()
    return them


def danh_sach(db: Session, ca_ngung: bool = False) -> list[dict]:
    q = select(KhoanMucChiPhi)
    if not ca_ngung:
        q = q.where(KhoanMucChiPhi.dung.is_(True))
    rows = db.execute(q.order_by(KhoanMucChiPhi.thu_tu, KhoanMucChiPhi.ma)).scalars().all()
    return [{"id": k.id, "ma": k.ma, "ten": k.ten, "nhom": k.nhom,
             "nhom_ten": NHOM_KHOAN_MUC.get(k.nhom, k.nhom), "thu_tu": k.thu_tu,
             "dung": k.dung, "ghi_chu": k.ghi_chu} for k in rows]


def ma_dang_dung(db: Session) -> set[str]:
    return {k.ma for k in db.execute(
        select(KhoanMucChiPhi).where(KhoanMucChiPhi.dung.is_(True))).scalars()}


def them(db: Session, data: dict) -> KhoanMucChiPhi:
    ma = str(data.get("ma") or "").strip().upper()[:20]
    if not ma:
        raise ValueError("Thiếu mã khoản mục")
    if db.execute(select(KhoanMucChiPhi).where(KhoanMucChiPhi.ma == ma)).scalar_one_or_none():
        raise ValueError(f"Mã {ma} đã có trong danh mục")
    nhom = data.get("nhom") or "gia_von"
    if nhom not in NHOM_KHOAN_MUC:
        raise ValueError(f"Nhóm không hợp lệ: {nhom}")
    k = KhoanMucChiPhi(ma=ma, ten=str(data.get("ten") or ma)[:200], nhom=nhom,
                       thu_tu=int(data.get("thu_tu") or 100), dung=True,
                       ghi_chu=str(data.get("ghi_chu") or ""))
    db.add(k)
    db.commit()
    return k


def sua(db: Session, kid: int, data: dict) -> KhoanMucChiPhi:
    """Sửa tên, nhóm, thứ tự, ghi chú, và BẬT/TẮT dùng. MÃ KHÔNG ĐỔI ĐƯỢC.

    Mã không đổi được là có chủ ý: mã đã nằm trong `JournalLine.item_code` của những bút toán đã
    ghi. Đổi mã ở đây thì các dòng sổ ấy trỏ vào một mã không còn tồn tại, và chúng biến mất khỏi
    mọi báo cáo theo khoản mục mà không ai thấy gì sai. Muốn đổi thì NGỪNG DÙNG mã cũ và thêm mã
    mới — cách ấy để lại dấu vết đọc được.
    """
    k = db.get(KhoanMucChiPhi, kid)
    if not k:
        raise ValueError("Không có khoản mục này")
    if "ten" in data:
        k.ten = str(data["ten"])[:200]
    if "nhom" in data:
        if data["nhom"] not in NHOM_KHOAN_MUC:
            raise ValueError(f"Nhóm không hợp lệ: {data['nhom']}")
        k.nhom = data["nhom"]
    if "thu_tu" in data:
        k.thu_tu = int(data["thu_tu"] or 100)
    if "ghi_chu" in data:
        k.ghi_chu = str(data["ghi_chu"] or "")
    if "dung" in data:
        k.dung = bool(data["dung"])
    db.commit()
    return k
