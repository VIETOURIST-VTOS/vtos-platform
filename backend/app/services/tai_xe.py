"""Hồ sơ tài xế – danh sách người lái, tình trạng bằng và xe đang đứng tên.

VÌ SAO CÓ TỆP NÀY (05/10/2026). Cây phân hệ Điều hành xe có mục 4.9.3 "Tài xế" ghi "Đã có", nhưng
đường dẫn của nó trỏ vào /xe-hdv – màn hình VIỆC CỦA CHÍNH TÀI XẾ. Người quản lý đội xe bấm vào đó
không thấy hồ sơ ai cả; tài khoản không gắn mã nhân viên thì chỉ nhận được một dòng báo lỗi. Hồ sơ
tài xế thật sự chưa từng có màn hình nào, dù dữ liệu đã nằm sẵn trong hệ thống từ lâu.

HAI ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM:

 1. KHÔNG trả một đồng lương nào. Cùng lý do đã viết ở api/v1/huong_dan.py: muốn biết ai còn hạn
    bằng thì không phải mở bảng lương toàn công ty ra để đọc.

 2. KHÔNG tự kết luận "đạt" khi thiếu dữ liệu. Bằng lái không ghi ngày hết hạn thì tình trạng là
    CHƯA ĐỦ DỮ LIỆU, không phải còn hạn; hạng để trống thì số chỗ tối đa là chưa biết, không phải
    không giới hạn. Đây là cùng một luật mà services/fleet.py đã giữ ở cổng điều xe, và màn hình
    phải nói đúng như cổng nói – hai nơi kết luận khác nhau về cùng một tài xế thì người điều hành
    sẽ tin nơi dễ chịu hơn.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fleet import Trip, VehicleDocument
from app.models.hr import Employee, Vehicle
from app.services.hang_gplx import so_cho_toi_da

SAP_HET_HAN = 60          # ngày: báo trước khi bằng lái hết hạn, cùng mốc với thẻ HDV
NHIN_LAI_NGAY = 90        # ngày: khoảng đếm số chuyến đã chạy


def la_tai_xe(e: Employee) -> bool:
    """Ai được tính là tài xế. Giữ ĐÚNG một định nghĩa với services/drivers.py dòng 62 – hai nơi
    đếm theo hai cách là hai con số khác nhau cho cùng một câu hỏi."""
    return e.department == "doi_xe" or e.position == "tai_xe"


def _gplx_moi_nhat(db: Session, ids: list[int]) -> dict[int, VehicleDocument]:
    """Bằng lái còn hiệu lực của từng người, MỘT LƯỢT HỎI cho cả danh sách.

    Cùng luật chọn với fleet._docs: giữ giấy có hạn xa nhất, và giấy chưa ghi hạn không được lấn
    giấy đã ghi hạn. Chép luật ấy ra đây thay vì gọi _docs trong vòng lặp, vì _docs hỏi một lượt
    cho mỗi người – đúng cái đã làm cửa /cham-soc mất 12 giây (TC-99).
    """
    if not ids:
        return {}
    ra: dict[int, VehicleDocument] = {}
    q = select(VehicleDocument).where(VehicleDocument.employee_id.in_(ids),
                                      VehicleDocument.kind == "gplx",
                                      VehicleDocument.active == True)    # noqa: E712
    for d in db.execute(q.order_by(VehicleDocument.id)).scalars():
        cu = ra.get(d.employee_id)
        if cu is None or (d.expires_on and (cu.expires_on is None or d.expires_on > cu.expires_on)):
            ra[d.employee_id] = d
    return ra


def _mot_nguoi(e: Employee, g: VehicleDocument | None, xe: list[Vehicle],
               so_chuyen: int, hom_nay: date, co_tai_khoan: bool = False) -> dict:
    con = (g.expires_on - hom_nay).days if (g and g.expires_on) else None
    toi_da, ly_do_hang = so_cho_toi_da(g.hang, g.issued_on) if g else (-1, "chưa có bằng lái trong hồ sơ")

    # BA kết luận, và không có kết luận thứ tư. `chua_biet` và `khong_dat` là hai cờ RIÊNG, không
    # phải hai mức của một thang: một người thiếu ngày hết hạn và một người bằng đã hết hạn đều
    # "không đủ điều kiện", nhưng việc phải làm với hai người ấy khác hẳn nhau – một bên đi đòi
    # giấy, một bên ngừng điều xe. Gộp hai cờ thành một chữ là xoá mất đúng chỗ khác nhau đó.
    thieu: list[str] = []
    chua_biet = False
    khong_dat = False
    if g is None:
        chua_biet = True
        thieu.append("chưa có bằng lái trong hồ sơ")
    else:
        if g.expires_on is None:
            chua_biet = True
            thieu.append("bằng lái chưa ghi ngày hết hạn")
        elif g.expires_on < hom_nay:
            khong_dat = True
            thieu.append(f"bằng lái hết hạn từ {g.expires_on:%d/%m/%Y}")
        if toi_da == -1:
            chua_biet = True
            thieu.append(ly_do_hang)
        elif toi_da == 0:
            khong_dat = True
            thieu.append(ly_do_hang)

    return {
        "id": e.id, "code": e.code, "full_name": e.full_name, "phone": e.phone,
        "loai_hop_dong": e.contract_type, "dang_lam": e.active,
        "gplx_so": g.number if g else "", "gplx_hang": g.hang if g else "",
        "gplx_cap": g.issued_on if g else None, "gplx_het_han": g.expires_on if g else None,
        "con_lai_ngay": con,
        "sap_het_han": con is not None and 0 <= con <= SAP_HET_HAN,
        # None = hạng không giới hạn số chỗ; -1 = chưa đọc được. Hai thứ KHÁC NHAU, và màn hình
        # phải in khác nhau, nên giữ nguyên cả hai giá trị thay vì quy về 0.
        "so_cho_toi_da": toi_da, "ly_do_hang": ly_do_hang,
        "xe_dang_dung_ten": [{"ma": v.code, "bien": v.plate, "so_cho": v.seats} for v in xe],
        "so_chuyen_90_ngay": so_chuyen,
        # VH-3 · 10/11/2026: tài xế không có tài khoản thì không bấm nhận lệnh, không ghi chuyến
        # trên điện thoại được — cả luồng VH-1 dừng ở người ấy. Màn gọn đếm riêng nhóm này.
        "co_tai_khoan": co_tai_khoan,
        "du_dieu_kien": not thieu,
        "chua_du_du_lieu": chua_biet,
        "khong_dat": khong_dat,
        "thieu": thieu,
    }


def _co_tai_khoan(db: Session, nguoi: list[Employee]) -> set[int]:
    """Người nào đăng nhập được. Cùng luật nối với /xe-hdv/cua-toi: `Employee.user_id`, hoặc mã
    nhân viên trùng `User.staff_code`. Tài khoản đã khoá không tính — khoá rồi thì không nhận lệnh."""
    from app.models.core import User
    users = list(db.execute(select(User.id, User.staff_code).where(User.active == True)))  # noqa: E712
    uid = {r[0] for r in users}
    ma = {(r[1] or "").strip() for r in users if (r[1] or "").strip()}
    return {e.id for e in nguoi
            if (getattr(e, "user_id", None) in uid) or ((e.code or "").strip() in ma)}


def danh_sach(db: Session, hom_nay: date | None = None) -> dict:
    """Danh sách tài xế kèm tình trạng hành nghề. Không có trường lương của bất kỳ ai."""
    hom_nay = hom_nay or date.today()
    tu_ngay = hom_nay - timedelta(days=NHIN_LAI_NGAY)

    nguoi = [e for e in db.execute(select(Employee).order_by(Employee.code)).scalars() if la_tai_xe(e)]
    ids = [e.id for e in nguoi]
    gplx = _gplx_moi_nhat(db, ids)

    xe_theo_nguoi: dict[int, list[Vehicle]] = {}
    if ids:
        for v in db.execute(select(Vehicle).where(Vehicle.driver_id.in_(ids))).scalars():
            xe_theo_nguoi.setdefault(v.driver_id, []).append(v)

    chuyen: dict[int, int] = {}
    if ids:
        chuyen = {r[0]: r[1] for r in db.execute(
            select(Trip.driver_id, func.count()).where(Trip.driver_id.in_(ids),
                                                       Trip.ngay_di >= tu_ngay)
            .group_by(Trip.driver_id))}

    co_tk = _co_tai_khoan(db, nguoi)
    ds = [_mot_nguoi(e, gplx.get(e.id), xe_theo_nguoi.get(e.id, []),
                     chuyen.get(e.id, 0), hom_nay, e.id in co_tk) for e in nguoi]
    dang_lam = [x for x in ds if x["dang_lam"]]
    return {
        "rows": ds,
        "tong": len(ds),
        "dang_lam": len(dang_lam),
        "du_dieu_kien": sum(1 for x in dang_lam if x["du_dieu_kien"]),
        "chua_du_du_lieu": sum(1 for x in dang_lam if x["chua_du_du_lieu"]),
        "khong_dat": sum(1 for x in dang_lam if x["khong_dat"]),
        "bang_sap_het_han": sum(1 for x in dang_lam if x["sap_het_han"]),
        "chua_gan_xe": sum(1 for x in dang_lam if not x["xe_dang_dung_ten"]),
        "chua_co_tai_khoan": sum(1 for x in dang_lam if not x["co_tai_khoan"]),
        "ghi_chu": ("Đủ điều kiện nghĩa là bằng lái có trong hồ sơ, còn hạn, và đọc được hạng. "
                    "Thiếu một trong ba thì ô này KHÔNG đếm – thiếu dữ liệu không phải là đạt. "
                    "Hạng bằng có đủ cho số chỗ của chiếc xe cụ thể hay không thì cổng điều xe "
                    "quyết định lúc phát lệnh, vì câu đó phụ thuộc vào chiếc xe, không phải người."),
        "cua_nhap": ("Hồ sơ nhân sự nạp ở Nhân sự. Bằng lái nạp bằng bộ nạp tệp 'Bằng lái tài xế' "
                     "(mã nhân viên, số GPLX, hạng, ngày cấp, ngày hết hạn). Xe gán tài xế ở màn "
                     "hình Đội xe."),
    }
