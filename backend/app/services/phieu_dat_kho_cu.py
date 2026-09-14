# -*- coding: utf-8 -*-
"""SINH PHIẾU ĐẶT theo NGƯỜI BÁN cho kho quyết toán cũ T1–T6/2026.

VÌ SAO PHẢI CÓ TỆP NÀY – MỘT CHỖ HỎNG ĐO ĐƯỢC

Rà ngày 13/9/2026, theo câu hỏi của Chủ tịch "đẩy lên quyết toán thì số có chạy về phòng ban không":
KHÔNG, và lý do nằm gọn ở một chỗ. Cửa tạo chuyến sinh chuyến mà KHÔNG sinh phiếu đặt; `booking_khach`
có cột `booking_id` bắt buộc; nên `intake_kho_cu` lặng lẽ bỏ TOÀN BỘ dòng khách của mọi chuyến mới –
chỉ chi phí vào được. Hệ quả dây chuyền:

  · bảng lãi lỗ thấy giá vốn mà không thấy doanh thu → mỗi chuyến thành một khoản LỖ bằng đúng chi phí,
    và số ấy cộng thẳng vào lãi gộp toàn công ty;
  · mọi báo cáo doanh số – sales lẻ, sales đoàn, hoa hồng, chỉ tiêu – đọc `bookings.sales_id`, nên
    không có phiếu đặt là không có gì để đọc.

Tệp này vá đúng chỗ ấy: dựng phiếu đặt cho những chuyến kho cũ, MỖI NGƯỜI BÁN MỘT PHIẾU.

VÌ SAO MỖI NGƯỜI BÁN MỘT PHIẾU, KHÔNG PHẢI MỖI CHUYẾN MỘT PHIẾU

Cột SALES nằm ở TỪNG DÒNG KHÁCH, không phải ở đầu tệp: một chuyến ghép thường có khách của bốn năm
người bán khác nhau. Gộp cả chuyến vào một phiếu là phải chọn một người để ghi tên – tức là gán doanh
số của bốn người cho một người. Chia theo người bán thì mỗi đồng doanh thu về đúng người đã bán ra nó,
và đó là cả mục đích của việc nạp lô này.

DÒNG KHÁCH CHƯA GÁN ĐƯỢC NGƯỜI BÁN THÌ SAO

Đo thật: 18.162 dòng khách, 3.196 dòng không ghi tên người bán, và trong số có ghi thì một phần chưa
khớp được tài khoản. Chúng KHÔNG bị bỏ – bỏ là mất doanh thu thật của công ty, và bảng lãi lỗ lại sai
đúng kiểu cũ. Chúng vào một phiếu riêng đứng tên TÀI KHOẢN ĐIỀU HÀNH KHOÁ (`dieuhanhvietrip`, đang là
điều hành của 1.145 chuyến Vietrip – không có thì rơi về điều hành của chính chuyến) với
`counts_for_target = False`:

  · doanh thu công ty và lãi lỗ chuyến ĐÚNG ngay từ đầu;
  · không một nhân viên thật nào bị cộng nhầm doanh số vào chỉ tiêu;
  · và số dòng đang đỗ ở đó hiện rõ trên màn hình gán, nên nó là việc còn nợ chứ không phải chỗ giấu.

Gán tên xong thì gọi `gan_lai` – khách chuyển sang phiếu của đúng người, không phải nạp lại cả lô.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.services import khop_nguoi_ban as KN
from app.services.tao_chuyen_kho_cu import NGUON

# Mã phiếu đặt của lô. `bookings.code` chỉ có 30 ký tự và là cột DUY NHẤT, nên mã phải vừa ngắn vừa
# không đụng mã người khác: KC- + số chuyến + số thứ tự người bán trong chuyến ấy.
TIEN_TO = "KC-"


def _tai_khoan_do(db):
    """Tài khoản đứng tên phiếu 'chưa gán'. Dùng LẠI tài khoản điều hành của cửa tạo chuyến.

    Không dựng tài khoản mới cho việc này: mỗi tài khoản trong hệ là một người đăng nhập được, và
    đẻ thêm tài khoản để chứa dữ liệu là cách mở một cửa vào hệ mà không ai nhớ đã mở.
    """
    from app.services.intake_tao_chuyen import _tai_khoan_dieu_hanh

    return _tai_khoan_dieu_hanh(db)


# Ô ghi TÊN NGƯỜI BÁN NHƯ TRONG TỆP, trên chính phiếu 'chưa gán'. Đây là chỗ xoay của cả tệp:
# không giữ lại cái tên thô thì sau khi người gán xong, không gì trên hệ biết phiếu ấy đáng lẽ
# thuộc về ai – và cách duy nhất còn lại là đọc lại 604 tệp Excel.
NHAN_TEN = "người bán trong tệp: "


def ten_trong_phieu(b) -> str:
    """Rút lại tên người bán đã ghi trên phiếu 'chưa gán'. Rỗng = tệp vốn không ghi tên ai."""
    for dong in (getattr(b, "care_note", "") or "").splitlines():
        if dong.startswith(NHAN_TEN):
            return dong[len(NHAN_TEN):].strip()
    return ""


def _gom_theo_ten(khach: list[dict]) -> dict[str, list]:
    """{tên người bán như trong tệp: [dòng khách]}. Gom theo TÊN chứ không theo tài khoản.

    Gom theo tài khoản thì hai cái tên chưa khớp được (`user_id` đều là None) dồn vào chung một
    phiếu, và cái tên gốc mất – gán xong không lần lại được của ai. Gom theo tên thì mỗi phiếu giữ
    đúng một tên, và `gan_lai` chỉ việc đổi chủ phiếu.
    """
    nhom: dict[str, list] = {}
    for x in khach:
        nhom.setdefault((x.get("sale") or "").strip(), []).append(x)
    return nhom


def _tien(x: dict) -> float:
    """Doanh thu một dòng khách. `tong_thu` là số chốt của dòng (đã gồm phụ thu, phí lãnh sự…);
    `gia_ban` chỉ là cột đầu của khối THU. Lấy tổng khi có, không cộng hai lần."""
    v = x.get("tong_thu")
    if v is None:
        v = x.get("gia_ban")
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def dem_nguoi_ban(rows: list[dict]) -> dict[str, int]:
    """{tên người bán: số dòng khách} trên cả lô – để ghi vào sổ gán trước khi nạp."""
    dem: dict[str, int] = {}
    for d in rows:
        for x in d.get("khach") or []:
            ten = (x.get("sale") or "").strip()
            if ten:
                dem[ten] = dem.get(ten, 0) + 1
    return dem


def xoa_phieu_cua_lo(db, tour_id: int) -> int:
    """Xoá phiếu đặt của LÔ trên một chuyến – và chỉ của lô.

    Phải xoá dòng khách treo vào chúng TRƯỚC, nếu không `booking_khach.booking_id` thành khoá mồ côi
    trỏ vào phiếu không còn tồn tại. Im lặng, và tháng sau một báo cáo nào đó đọc phải.
    """
    from app.models.core import Booking
    from app.models.lop3_tour import BookingKhach

    ids = [b.id for b in db.scalars(
        select(Booking).where(Booking.tour_id == tour_id, Booking.source == NGUON)).all()]
    if not ids:
        return 0
    db.query(BookingKhach).filter(BookingKhach.booking_id.in_(ids)).delete(
        synchronize_session=False)
    n = db.query(Booking).filter(Booking.id.in_(ids)).delete(synchronize_session=False)
    db.flush()
    return n


def sinh(db, tour_id: int, khach: list[dict], boi: str) -> dict:
    """Dựng phiếu đặt cho một chuyến. Trả về {user_id|None: booking_id} để treo dòng khách vào.

    Gọi lại lần hai trên cùng chuyến thì THAY, không nhân đôi – cùng quy ước với hai cửa nạp.
    """
    from app.models.core import Booking, Tour

    t = db.get(Tour, tour_id)
    if t is None:
        return {"loi": "khong-co-chuyen", "theo_nguoi_ban": {}, "so_phieu": 0}
    nguoi_do, ten_do = _tai_khoan_do(db)
    if nguoi_do is None:
        # Rơi về ĐIỀU HÀNH CỦA CHÍNH CHUYẾN. Chuyến nào cũng có điều hành (`tours.operator_id` là
        # cột bắt buộc), nên nhánh này giữ cho cửa nạp chạy được trên chuyến đã có sẵn trong VTOS
        # mà không cần ai dựng trước một tài khoản hệ thống. Doanh thu đỗ ở đây vẫn KHÔNG vào chỉ
        # tiêu của ai (`counts_for_target=False`), nên điều hành ấy không bị cộng doanh số bán hàng.
        from app.models.core import User as _U
        nguoi_do = db.get(_U, t.operator_id) if t.operator_id else None
    if nguoi_do is None:
        # Không còn chỗ đỗ nào thì KHÔNG dựng phiếu nào cả, kể cả phiếu của người đã khớp: dựng
        # một nửa là chuyến có doanh thu thiếu, mà bảng nào cũng cân vì tổng nào cũng cộng từ dòng.
        return {"loi": f"chua-co-tai-khoan-{ten_do}", "theo_ten_nguoi_ban": {}, "so_phieu": 0}

    xoa_phieu_cua_lo(db, tour_id)
    nhom = _gom_theo_ten(khach)

    ra: dict[str, int] = {}
    chua_gan_dong = chua_gan_tien = 0
    for i, ten_ban in enumerate(sorted(nhom), 1):
        ds = nhom[ten_ban]
        uid = KN.tra_so(db, ten_ban) if ten_ban else None
        tien = round(sum(_tien(x) for x in ds), 2)
        co_nguoi = uid is not None
        if not co_nguoi:
            chua_gan_dong += len(ds)
            chua_gan_tien += tien
        ten_kh = (ds[0].get("ho_ten") or "").strip()
        b = Booking(
            code=f"{TIEN_TO}{t.id}-{i}"[:30],
            tour_id=tour_id,
            request_id=0,                       # kho cũ không có yêu cầu gốc – 0 nghĩa là không có
            sales_id=uid if co_nguoi else nguoi_do.id,
            created_by=nguoi_do.id,
            customer_name=(ten_kh + (f" và {len(ds) - 1} khách" if len(ds) > 1 else ""))[:120],
            customer_phone="",
            source=NGUON,
            care_note=("" if co_nguoi else
                       (f"{NHAN_TEN}{ten_ban}\n" if ten_ban else "tệp không ghi tên người bán\n") +
                       "Chưa gán được người bán – doanh thu vẫn tính cho công ty, KHÔNG tính vào "
                       "chỉ tiêu của ai. Gán tên ở màn hình người bán rồi bấm gán lại."),
            pax=len(ds),
            adl=len(ds),
            amount=tien,
            discount=0,
            # Đây là chốt an toàn của cả tệp: dòng chưa gán được người thì KHÔNG vào chỉ tiêu ai cả.
            counts_for_target=co_nguoi,
            sla_minutes=0, sla_ok=True,
            created_at=datetime.now(),
        )
        db.add(b)
        db.flush()
        ra[ten_ban] = b.id
    return {"theo_ten_nguoi_ban": ra, "so_phieu": len(ra),
            "chua_gan_dong": chua_gan_dong, "chua_gan_tien": round(chua_gan_tien, 2)}


def gan_lai(db, boi: str, xac_nhan: bool = False) -> dict:
    """Sau khi người gán tên: ĐỔI CHỦ những phiếu 'chưa gán' nay đã tra ra tài khoản.

    KHÔNG nạp lại lô. Nạp lại là đọc lại 604 tệp và ghi đè mọi thứ, kể cả phần người ta đã sửa tay
    trên hệ sau khi nạp. Ở đây chỉ đụng đúng hai ô trên phiếu: `sales_id` và `counts_for_target`.
    Dòng khách, dòng chi, số tiền – không ô nào bị động tới.

    Mặc định chỉ XEM TRƯỚC. Đây là việc dịch doanh số sang tên người thật, nên nó phải qua một lần
    bấm và vào nhật ký mang tên người bấm.
    """
    from app.models.core import Booking, User

    nguoi_do, ten_do = _tai_khoan_do(db)
    if nguoi_do is None:
        return {"loi": f"chua-co-tai-khoan-{ten_do}", "doi_duoc": [], "da_doi": 0}

    phieu_do = db.scalars(select(Booking).where(
        Booking.source == NGUON, Booking.sales_id == nguoi_do.id,
        Booking.counts_for_target == False)).all()                       # noqa: E712
    ten_tk = {u.id: u.full_name for u in db.scalars(select(User)).all()}

    doi, con_treo = [], []
    for b in phieu_do:
        ten_ban = ten_trong_phieu(b)
        uid = KN.tra_so(db, ten_ban) if ten_ban else None
        if uid is None:
            con_treo.append({"phieu": b.code, "tour_id": b.tour_id, "ten_trong_tep": ten_ban,
                             "so_khach": b.pax, "tien": float(b.amount or 0)})
            continue
        doi.append({"phieu": b.code, "tour_id": b.tour_id, "ten_trong_tep": ten_ban,
                    "ve_tai_khoan": ten_tk.get(uid, str(uid)), "so_khach": b.pax,
                    "tien": float(b.amount or 0)})
        if xac_nhan:
            b.sales_id = uid
            b.counts_for_target = True
            b.care_note = ""
    if xac_nhan:
        db.flush()

    tien = round(sum(x["tien"] for x in doi), 2)
    return {
        "doi_duoc": doi, "con_treo": con_treo,
        "da_doi": len(doi) if xac_nhan else 0,
        "tien_ve_nguoi_that": tien,
        "ghi_chu": (
            (f"Đã chuyển {len(doi)} phiếu ({tien:,.0f} đ) về đúng người bán. "
             if xac_nhan else
             f"XEM TRƯỚC – chưa đổi gì. {len(doi)} phiếu ({tien:,.0f} đ) nay tra ra tài khoản và "
             f"sẽ được chuyển về đúng người bán. ") +
            f"{len(con_treo)} phiếu vẫn chưa gán được – gán tên ở màn hình người bán rồi bấm lại."),
    }
