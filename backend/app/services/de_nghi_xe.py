# -*- coding: utf-8 -*-
"""Đề nghị xe: mắt đầu của chuỗi điều xe (Chủ tịch đặc tả 11/10/2026).

CỬA CHẶN DUY NHẤT là dự toán tour đã duyệt. Chủ tịch quyết: chi phí xe đã nằm trong dự toán ấy, nên
không thêm chữ ký nào nữa — Giám đốc đội xe lập lệnh là mắt kiểm, và từ chối thì bắt buộc ghi lý do.

MỘT ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM: không tự chọn xe, và không tự lập lệnh khi đề nghị được tạo. Tự
lập lệnh thì chuỗi ba mắt rút lại thành một mắt, và chữ "Giám đốc đội xe lập lệnh" trong đặc tả mất
nghĩa.
"""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.models.de_nghi_xe import DeNghiXe, DU_TOAN_DA_DUYET, TRANG_THAI
from app.services import rules as R


def _tour(db: Session, tour_id: int) -> Tour:
    t = db.get(Tour, tour_id)
    if t is None:
        raise ValueError(f"Không có chuyến id={tour_id}.")
    return t


def kiem_cua(db: Session, t: Tour) -> str:
    """Trả lời đúng một câu: chuyến này đề nghị xe được chưa. Rỗng là được.

    Trả về LỜI chứ không trả về True/False, vì người điều hành cần biết mình phải làm gì tiếp — và
    một câu "chưa được" không nói vì sao là một câu làm người ta đi hỏi vòng.
    """
    if t.status not in DU_TOAN_DA_DUYET:
        return (f"Dự toán chuyến {t.code} chưa được duyệt (đang ở '{t.status}'). Chi phí xe nằm "
                "trong dự toán, nên phải duyệt dự toán trước rồi mới đề nghị xe.")
    return ""


def de_nghi(db: Session, boi: User, tour_id: int, so_khach: int, km_du_kien: int = 0,
            so_xe_can: int = 1, yeu_cau: str = "",
            ngay_di: date | None = None, ngay_ve: date | None = None) -> DeNghiXe:
    t = _tour(db, tour_id)
    chan = kiem_cua(db, t)
    if chan:
        raise ValueError(chan)
    d1 = ngay_di or t.start_date
    d2 = ngay_ve or t.end_date
    if d1 is None or d2 is None:
        raise ValueError(f"Chuyến {t.code} chưa có ngày đi/ngày về – chưa đề nghị xe được.")
    if d2 < d1:
        raise ValueError("Ngày về trước ngày đi.")
    if so_khach <= 0:
        # Số khách là đầu vào của bộ gợi ý điều xe: thiếu nó thì bộ gợi ý không lọc được theo số ghế
        # và sẽ đề xuất một chiếc 29 chỗ cho đoàn 40 người.
        raise ValueError("Phải ghi số khách – bộ gợi ý điều xe lọc theo số ghế, thiếu số khách thì "
                         "nó không lọc được.")
    if so_xe_can <= 0:
        raise ValueError("Số xe cần phải lớn hơn 0.")
    d = DeNghiXe(tour_id=t.id, ngay_di=d1, ngay_ve=d2, so_khach=so_khach,
                 km_du_kien=max(0, km_du_kien), so_xe_can=so_xe_can,
                 yeu_cau=(yeu_cau or "").strip()[:2000], nguoi_de_nghi=boi.username)
    db.add(d); db.flush()
    R.audit(db, boi.username, boi.role, "de_nghi_xe", f"tour:{t.code}",
            after={"de_nghi": d.id, "so_khach": so_khach, "so_xe_can": so_xe_can})
    return d


def _dong(db: Session, d: DeNghiXe) -> dict:
    t = db.get(Tour, d.tour_id)
    return {"id": d.id, "tour_id": d.tour_id, "ma_tour": t.code if t else "", "ten_tour": t.name if t else "",
            "ngay_di": d.ngay_di.isoformat(), "ngay_ve": d.ngay_ve.isoformat(),
            "so_ngay": (d.ngay_ve - d.ngay_di).days + 1,
            "so_khach": d.so_khach, "km_du_kien": d.km_du_kien, "so_xe_can": d.so_xe_can,
            "yeu_cau": d.yeu_cau, "trang_thai": d.trang_thai,
            "trang_thai_ten": TRANG_THAI.get(d.trang_thai, d.trang_thai), "ly_do": d.ly_do,
            "nguoi_de_nghi": d.nguoi_de_nghi, "luc": d.luc.isoformat() if d.luc else None,
            "xu_ly_boi": d.xu_ly_boi, "xu_ly_luc": d.xu_ly_luc.isoformat() if d.xu_ly_luc else None}


def danh_sach(db: Session, trang_thai: str = "", tour_id: int | None = None) -> dict:
    q = select(DeNghiXe).order_by(DeNghiXe.id.desc())
    if trang_thai:
        if trang_thai not in TRANG_THAI:
            raise ValueError(f"Trạng thái không hợp lệ: {trang_thai}")
        q = q.where(DeNghiXe.trang_thai == trang_thai)
    if tour_id:
        q = q.where(DeNghiXe.tour_id == tour_id)
    ds = [_dong(db, d) for d in db.execute(q).scalars()]
    dem = {k: 0 for k in TRANG_THAI}
    for d in db.execute(select(DeNghiXe)).scalars():
        dem[d.trang_thai] = dem.get(d.trang_thai, 0) + 1
    return {"rows": ds, "dem": dem, "trang_thai": TRANG_THAI}


def _doi_trang_thai(db: Session, boi: User, de_nghi_id: int, moi: str, ly_do: str) -> DeNghiXe:
    d = db.get(DeNghiXe, de_nghi_id)
    if d is None:
        raise ValueError(f"Không có đề nghị #{de_nghi_id}.")
    if d.trang_thai != "cho_lap_lenh":
        raise ValueError(f"Đề nghị #{d.id} đang ở '{TRANG_THAI.get(d.trang_thai, d.trang_thai)}' – "
                         "chỉ đề nghị đang CHỜ LẬP LỆNH mới đổi được.")
    if not (ly_do or "").strip():
        # Từ chối hoặc huỷ mà không ghi lý do thì tháng sau không ai trả lời được vì sao chuyến ấy
        # phải thuê xe ngoài — và đó đúng là câu hỏi báo cáo đối chiếu tour/lượt xe đi tìm.
        raise ValueError("Phải ghi lý do.")
    d.trang_thai = moi
    d.ly_do = ly_do.strip()[:300]
    d.xu_ly_boi = boi.username
    d.xu_ly_luc = datetime.now()
    db.flush()
    t = db.get(Tour, d.tour_id)
    R.audit(db, boi.username, boi.role, f"de_nghi_xe_{moi}", f"tour:{t.code if t else d.tour_id}",
            after={"de_nghi": d.id, "ly_do": d.ly_do})
    return d


def tu_choi(db: Session, boi: User, de_nghi_id: int, ly_do: str) -> DeNghiXe:
    """Đội xe từ chối. Lý do bắt buộc — xem chú thích trong `_doi_trang_thai`."""
    return _doi_trang_thai(db, boi, de_nghi_id, "tu_choi", ly_do)


def huy(db: Session, boi: User, de_nghi_id: int, ly_do: str) -> DeNghiXe:
    """Điều hành huỷ đề nghị của chính mình (khách huỷ, dời ngày, ghép chuyến)."""
    return _doi_trang_thai(db, boi, de_nghi_id, "huy", ly_do)


def danh_dau_da_lap_lenh(db: Session, de_nghi_id: int, lenh_id: int) -> None:
    """Cửa lập lệnh gọi vào đây sau khi lệnh được tạo.

    Đặt ở đây chứ không viết thẳng trong cửa lập lệnh: trạng thái của đề nghị là việc của tệp này,
    và hai nơi cùng đổi một trạng thái là chỗ chúng sẽ có ngày nói khác nhau.
    """
    d = db.get(DeNghiXe, de_nghi_id)
    if d is None:
        raise ValueError(f"Không có đề nghị #{de_nghi_id}.")
    if d.trang_thai == "da_lap_lenh":
        return                      # một đề nghị có thể dẫn tới nhiều lệnh (tour cần hai xe)
    if d.trang_thai != "cho_lap_lenh":
        raise ValueError(f"Đề nghị #{d.id} đang ở '{TRANG_THAI.get(d.trang_thai)}' – không lập lệnh "
                         "cho đề nghị đã từ chối hoặc đã huỷ.")
    d.trang_thai = "da_lap_lenh"
    d.xu_ly_luc = datetime.now()
    db.flush()


def lenh_khong_qua_de_nghi(db: Session) -> dict:
    """ĐẾM chỗ chuỗi ba mắt chưa được dùng — cùng khuôn với `misa.thieu_tai_khoan()`.

    `POST /dispatch` vẫn nhận lệnh KHÔNG kèm đề nghị, và đó là cố ý: bắt buộc ngay thì mười tệp phép
    kiểm của các làn khác đỏ, và quan trọng hơn là Điều hành chưa kịp chuyển sang dùng cửa đề nghị.
    Nhưng một chỗ hở không đếm được là một chỗ hở sẽ ở lại mãi. Hàm này làm nó đếm được.

    Khi con số về 0 và giữ 0 một thời gian, siết `de_nghi_id` thành bắt buộc là một dòng trong cửa
    lập lệnh cộng một phép kiểm — và lúc ấy việc siết KHÔNG còn làm ai đứng việc.
    """
    from app.models.hr import DispatchOrder
    ds = list(db.execute(select(DispatchOrder)).scalars())
    thieu = [d for d in ds if not d.de_nghi_id]
    return {"tong_lenh": len(ds), "khong_qua_de_nghi": len(thieu),
            "ty_le": (round(len(thieu) / len(ds), 4) if ds else None),
            "lenh": [{"id": d.id, "tour_id": d.tour_id, "vehicle_id": d.vehicle_id,
                      "tu": d.date_from.isoformat(), "den": d.date_to.isoformat(),
                      "lap_boi": d.created_by} for d in thieu[:200]],
            "ghi_chu": ("Lệnh điều xe lập KHÔNG qua cửa đề nghị xe. Chuỗi Chủ tịch đặc tả 11/10/2026 "
                        "là: Điều hành đề nghị → Giám đốc đội xe lập lệnh → tài xế nhận. Con số này "
                        "về 0 thì siết đề nghị thành bắt buộc được.")}


def tour_cho_de_nghi(db: Session, tu: date, den: date) -> list:
    """Chuyến ĐỀ NGHỊ XE ĐƯỢC trong khoảng ngày — và chỉ bốn cột lịch trình.

    Vì sao không để màn hình dùng lại `/fleet/de-lap-lenh`: đường ấy trả MỌI chuyến giao nhau với
    khoảng ngày, không nhìn trạng thái dự toán. Người điều hành sẽ chọn một chuyến chưa duyệt, bấm
    gửi, và nhận một câu 422. Một cửa bày ra thứ bấm vào là lỗi thì mỗi ngày nó dạy người dùng rằng
    màn hình này hay báo lỗi.

    Không trả giá bán, dự toán hay biên lợi nhuận — cùng lý do đã ghi ở `/fleet/de-lap-lenh`: đội xe
    và điều hành cần mã chuyến để đề nghị xe, không cần biết chuyến ấy lãi bao nhiêu.
    """
    if den < tu:
        raise ValueError("Ngày kết thúc trước ngày bắt đầu.")
    ts = db.execute(select(Tour).where(Tour.start_date <= den, Tour.end_date >= tu,
                                       Tour.status.in_(DU_TOAN_DA_DUYET))
                    .order_by(Tour.start_date)).scalars().all()
    dang_mo: dict[int, int] = {}
    for d in db.execute(select(DeNghiXe).where(DeNghiXe.trang_thai.in_(("cho_lap_lenh",
                                                                       "da_lap_lenh")))).scalars():
        dang_mo[d.tour_id] = dang_mo.get(d.tour_id, 0) + 1
    return [{"id": t.id, "code": t.code, "name": t.name,
             "start_date": t.start_date.isoformat() if t.start_date else None,
             "end_date": t.end_date.isoformat() if t.end_date else None,
             "planned_pax": t.planned_pax, "status": t.status,
             # Đã có đề nghị KHÔNG chặn: một chuyến cần thêm xe thì đề nghị thêm. Chỉ nói ra để người
             # điều hành không gửi trùng vì tưởng lần trước chưa gửi được.
             "da_co_de_nghi": dang_mo.get(t.id, 0)} for t in ts]
