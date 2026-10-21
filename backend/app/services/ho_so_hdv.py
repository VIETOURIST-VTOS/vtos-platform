# -*- coding: utf-8 -*-
"""Hồ sơ hướng dẫn viên — Đợt HD-14. CHỈ ĐỌC, không một cửa ghi nào.

VÌ SAO CÓ TỆP NÀY. Đợt HD-DG3 (16/10/2026) dựng xong hàng đợi duyệt «đăng nhận xét lên hồ sơ
hướng dẫn viên công khai», nhưng hồ sơ ấy chưa tồn tại — duyệt xong thì nhận xét không hiện ở đâu.
Tệp này là chỗ nó hiện.

PHẠM VI ĐÃ HỨA VỚI KHÁCH, KHÔNG ĐƯỢC NỚI. Câu lưu nguyên văn trong `dong_y_cong_khai.cau_hoi` là
«đăng công khai trên hồ sơ hướng dẫn viên TẠI VTOS, không kèm tên và thông tin liên hệ». Chủ tịch
chốt 17/10/2026: chỉ phòng Hướng dẫn và Ban lãnh đạo đọc, qua nhóm API `/api/v1/huong-dan` đã có.
Mở ra ngoài internet là một phạm vi RỘNG HƠN điều khách đã đồng ý — phải hỏi lại khách bằng một
câu mới, không phải đổi một dòng cấu hình.

MỘT ĐIỀU KIỆN, MỘT CHỖ. Nhận xét nào được hiện thì hỏi `dong_y.cong_khai_duoc()`, không viết lại
mệnh đề ở đây. Bài học KN-1: «quá hạn» từng được viết hai lần bằng hai thứ tiếng, và hai bản thì
sớm muộn lệch — lúc ấy màn hình nói một đằng, báo cáo nói một nẻo, không ai biết bên nào đúng.
Phép thử `test_hd14_ho_so_hdv.py` cấm tệp này tự dựng lại mệnh đề.

KHÔNG CÓ KHOÁ TUYẾN. `CO_TRUONG_TUYEN` của `dong_y.py` còn tắt, nên phần trả về KHÔNG mang khoá
tuyến nào — không trả rỗng, mà không có khoá. Một khối rỗng trên màn hình trông y như «hướng dẫn
viên này chưa dẫn tuyến nào», trong khi sự thật là VTOS chưa nối được chuyến về địa bàn (xem
`_DO-NEN-HD-13.md`).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai
from app.models.hr import Employee
from app.services import dong_y as DY

# Loại đối tượng được chấm. `DG_DOI_TUONG["hdv"]` và `DG_CO_KHOA` của `models/danh_gia.py` nói rõ:
# với "hdv" thì `doi_tuong_id` trỏ vào `employees.id`, và cột ấy BẮT BUỘC có.
LOAI = "hdv"

# Dưới ngưỡng này thì KHÔNG hiện điểm trung bình (Chủ tịch chốt 17/10/2026). Lý do: một hướng dẫn
# viên 2,8 điểm sẽ bị cả phòng thấy trước khi Trưởng phòng kịp nói chuyện với họ — mà 2,8 từ ba
# phiếu thì chưa nói được gì. Ngưỡng không giấu điểm thấp, nó chặn việc kết luận quá sớm.
#
# VẪN HIỆN SỐ LƯỢT THẬT khi chưa đủ: giấu cả hai thì người đọc không biết còn thiếu bao nhiêu.
NGUONG_HIEN_DIEM = 10


def tinh_trang_the(e: Employee) -> tuple[str, str]:
    """Ba trạng thái thẻ hành nghề, kèm chữ hiện trên chip.

    Có số thẻ mà KHÔNG có hạn là một trạng thái riêng, không gộp vào «còn hạn»: đó là hồ sơ nhập
    thiếu, và gộp nó vào màu xanh là nói với người đọc rằng thẻ đã được kiểm.
    """
    if not (e.card_no or "").strip():
        return ("chua_co", "Chưa có thẻ")
    han = e.card_expiry
    if han is None:
        return ("chua_ro", "Có số thẻ, chưa ghi hạn")
    if han < date.today():
        return ("het_han", f"Hết hạn {han.month:02d}/{han.year}")
    return ("con_han", f"Còn hạn đến {han.month:02d}/{han.year}")


def _cac_danh_gia(db: Session, guide_id: int) -> list[DanhGiaSauTour]:
    return list(db.execute(
        select(DanhGiaSauTour).where(
            DanhGiaSauTour.doi_tuong == LOAI,
            DanhGiaSauTour.doi_tuong_id == guide_id,
        )
    ).scalars().all())


def diem_cua(db: Session, guide_id: int) -> dict:
    """Điểm trung bình và số lượt. Dưới ngưỡng thì `diem` là None — KHÔNG phải 0.

    0 và «chưa đủ lượt» là hai chuyện khác nhau, và 0 là con số tệ nhất có thể in ra ở đây.
    """
    diem = [d.diem for d in _cac_danh_gia(db, guide_id) if d.diem is not None]
    n = len(diem)
    if n < NGUONG_HIEN_DIEM:
        return {"so_luot": n, "du_nguong": False, "diem": None, "nguong": NGUONG_HIEN_DIEM}
    return {"so_luot": n, "du_nguong": True, "diem": round(sum(diem) / n, 1),
            "nguong": NGUONG_HIEN_DIEM}


def nhan_xet_cong_khai(db: Session, guide_id: int) -> list[dict]:
    """Các nhận xét ĐƯỢC HIỆN của một hướng dẫn viên, mới nhất trước.

    Nhãn người viết lấy từ `dong_y.nhan_nguoi_viet` — không ghép nhãn ở đây, để ngày Đợt HD-13 bật
    tên địa bàn lên thì màn hình đổi theo mà không ai phải sửa chỗ thứ hai.
    """
    dgs = {d.id: d for d in _cac_danh_gia(db, guide_id)}
    if not dgs:
        return []
    rows = db.execute(
        select(DongYCongKhai).where(DongYCongKhai.danh_gia_id.in_(list(dgs.keys())))
    ).scalars().all()

    ra: list[dict] = []
    for r in rows:
        if not DY.cong_khai_duoc(r):
            continue
        dg = dgs.get(r.danh_gia_id)
        if dg is None or not (dg.nhan_xet or "").strip():
            continue
        ra.append({
            "nhan_xet": dg.nhan_xet,
            "diem": dg.diem,
            "nhan": DY.nhan_nguoi_viet(db, dg),
            "luc": dg.tao_luc,
        })
    ra.sort(key=lambda x: x["luc"] or datetime.min, reverse=True)
    return ra


def ho_so(db: Session, guide_id: int) -> dict | None:
    """Một hồ sơ. Trả None nếu không có người ấy, hoặc người ấy không phải hướng dẫn viên.

    Tầng cửa biến None thành 404 — KHÔNG trả về một trang trống, vì trang trống nói «người này
    chưa có gì», còn sự thật là không có người này.
    """
    e = db.get(Employee, guide_id)
    if e is None or e.position != LOAI:
        return None
    ma_the, chu_the = tinh_trang_the(e)
    d = diem_cua(db, guide_id)
    return {
        "id": e.id,
        "ma": e.code,
        "ho_ten": e.full_name,
        "phong_ban": e.department,
        "the": {"trang_thai": ma_the, "chu": chu_the, "so": e.card_no or "",
                "loai": e.card_type or ""},
        "diem": d,
        "nhan_xet": nhan_xet_cong_khai(db, guide_id),
    }


def danh_sach(db: Session) -> list[dict]:
    """Danh sách hướng dẫn viên đang cộng tác — lối vào hồ sơ (mục 4.10.2 của cây phân hệ).

    Hỏi từng người một. Hôm nay 13 người nên không đáng ngại; ngày danh sách dài lên thì gom lại
    thành một câu hỏi — ghi ra đây để người sau biết chỗ phải sửa, thay vì đi tìm.
    """
    es = db.execute(
        select(Employee).where(Employee.position == LOAI, Employee.active.is_(True))
        .order_by(Employee.full_name)
    ).scalars().all()

    ra: list[dict] = []
    for e in es:
        ma_the, chu_the = tinh_trang_the(e)
        d = diem_cua(db, e.id)
        ra.append({
            "id": e.id,
            "ma": e.code,
            "ho_ten": e.full_name,
            "the": {"trang_thai": ma_the, "chu": chu_the},
            "diem": d["diem"],
            "so_luot": d["so_luot"],
            "du_nguong": d["du_nguong"],
            "so_nhan_xet": len(nhan_xet_cong_khai(db, e.id)),
        })
    return ra
