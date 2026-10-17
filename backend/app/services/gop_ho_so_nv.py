# -*- coding: utf-8 -*-
"""HS-11 — MỘT NGƯỜI, MỘT NGÀY SINH. Gộp hai chỗ chứa cùng một thông tin về một nguồn.

VÌ SAO CÓ TỆP NÀY

Cùng một thông tin nằm ở HAI bảng, và hai màn hình ghi vào hai nơi khác nhau:

    ô «Ngày sinh» ở HC–NS › Hồ sơ nhân sự   →  employees.birth_date
    ô «Ngày sinh» ở Hợp đồng lao động       →  employee_profiles.dob

Không có đường nối nào giữa hai cột ấy. HCNS điền một bên, bên kia vẫn trống hoặc giữ số cũ —
và vì cả hai màn hình đều hiện ra một ô có nhãn «Ngày sinh», không ai có lý do để nghi ngờ.
Bộ đếm «hồ sơ đủ bao nhiêu phần trăm» (`PROFILE_REQUIRED`) chỉ nhìn `dob`, nên một người đã có
ngày sinh ở màn nhân sự vẫn bị đếm là THIẾU HỒ SƠ, và HCNS đi đòi lại thứ họ đã nhập rồi.

`điện thoại` cùng một hình, và còn tệ hơn một bậc: `ho_so_nhan_vien.doc_ho_so` có một luật NGẦM —
hễ `profile.phone` không rỗng thì nó đè lên `employees.phone`. Luật ấy không khai ở đâu, không
phép thử nào canh, và nó quyết định số điện thoại nào hiện ra trên màn hồ sơ.

Ô thứ hai của ngày sinh là do chính vòng HS-9 (17/10/2026) dựng ra: cột `dob` vốn có trong cơ sở
dữ liệu mà chưa có cửa nhập, HS-9 mở cửa cho đủ 17 trường của `ProfileIn` mà không soát xem ngày
sinh đã có chỗ khác chưa.

BA LUẬT CỦA VÒNG NÀY — Chủ tịch chốt 17/10/2026

1. GỘP VỀ HỒ SƠ CÁ NHÂN. `employee_profiles` là nơi để CCCD, hộ khẩu, sổ BHXH; ngày sinh và
   điện thoại thuộc về cùng chỗ đó. Từ nay CHỈ GHI vào hồ sơ cá nhân — cả màn HC–NS lẫn hai cửa
   nạp dữ liệu (nhân sự phòng ban, tài xế).

2. ĐỌC THÌ ƯU TIÊN HỒ SƠ, RỚT VỀ CỘT CŨ. `doc()` dưới đây là chỗ DUY NHẤT nói ra luật ấy. Đây
   chính là luật ngầm cũ của `doc_ho_so`, nay viết ra thành một dòng mã có tên, có phép thử.

3. KHÔNG XOÁ CỘT CŨ Ở VÒNG NÀY, và không tự chọn bên nào thắng. Cột `employees.birth_date` còn
   giữ nguyên dữ liệu đang có; nó chỉ thôi được GHI. Xoá cột trước khi HCNS dọn xong danh sách
   lệch là xoá mất đúng cái bằng chứng dùng để dọn.

HAI CỬA, VÀ RANH GIỚI GIỮA CHÚNG

    soat_lech()        chỉ ĐỌC. Kê ra từng người hai bên không khớp. Máy không chọn.
    chuyen_cho_trong() chỉ ghi vào Ô CÒN TRỐNG bên hồ sơ. Chép vào một ô trống không phải là
                       chọn — không có gì để đè. Ô hai bên đều có số mà KHÁC NHAU thì cửa này
                       KHÔNG đụng tới, nó nằm lại trong danh sách để HCNS tự quyết.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import Employee
from app.models.hrm import EmployeeProfile
from app.services import rules as R

# (cột ở bảng nhân sự, cột ở hồ sơ cá nhân, tên tiếng Việt). Thêm một cặp trùng mới thì khai vào
# ĐÂY — `test_hs11` đọc thẳng danh sách này, nên một cặp quên khai là một cặp không ai soát.
CAP_TRUNG: tuple[tuple[str, str, str], ...] = (
    ("birth_date", "dob", "Ngày sinh"),
    ("phone", "phone", "Điện thoại"),
)


def ban_do_ho_so(db: Session, ids: list[int] | None = None) -> dict[int, EmployeeProfile]:
    """{employee_id: hồ sơ} trong MỘT lượt hỏi.

    Gọi `profile_of` trong vòng lặp 121 người là 121 lượt hỏi cơ sở dữ liệu, trên gói 0,5 CPU của
    Render — đúng kiểu đã làm `GET /tours` chạy 16–30 giây ở vòng TC-69.
    """
    q = select(EmployeeProfile)
    if ids is not None:
        if not ids:
            return {}
        q = q.where(EmployeeProfile.employee_id.in_(ids))
    return {p.employee_id: p for p in db.execute(q).scalars()}


def doc(e: Employee, pf: EmployeeProfile | None, cot_nv: str, cot_hs: str):
    """Giá trị ĐANG DÙNG của một cặp trùng: hồ sơ cá nhân trước, cột cũ sau.

    Mọi chỗ hiển thị phải đi qua đây. Đọc thẳng `e.birth_date` ở một màn hình nào đó nghĩa là màn
    ấy nói một con số khác với phần còn lại của hệ thống, và nó sẽ nói sai đúng với những người
    mà HCNS vừa cập nhật hồ sơ.
    """
    if pf is not None:
        v = getattr(pf, cot_hs, None)
        if v:
            return v
    return getattr(e, cot_nv, None)


def ghi(db: Session, u, employee_id: int, du_lieu: dict) -> None:
    """Ghi một hoặc vài cặp trùng — LUÔN vào hồ sơ cá nhân, không bao giờ vào cột cũ.

    `du_lieu` khoá theo cột HỒ SƠ (`dob`, `phone`). Rỗng thì không gọi.
    """
    sach = {k: v for k, v in du_lieu.items() if v not in (None, "")}
    if not sach:
        return
    from app.services import hrm as H
    H.save_profile(db, u, employee_id, sach)


def _trang_thai(a, b) -> str:
    if a and b:
        return "khop" if a == b else "lech"
    if a:
        return "chi_bang_nhan_su"
    if b:
        return "chi_ho_so"
    return "ca_hai_trong"


NHAN = {"lech": "Hai bên khác nhau — HCNS chọn",
        "chi_bang_nhan_su": "Chỉ bảng nhân sự có — chép sang được",
        "chi_ho_so": "Chỉ hồ sơ có — đã đúng một nguồn",
        "khop": "Khớp",
        "ca_hai_trong": "Cả hai còn trống"}


def soat_lech(db: Session, gom_ca_khop: bool = False) -> dict:
    """CHỈ ĐỌC. Kê từng người, từng cặp trùng, hai bên đang mang gì.

    Mặc định bỏ qua những người đã khớp hoặc cả hai còn trống: danh sách này sinh ra để HCNS
    ĐI DỌN, nên 121 dòng không có việc gì để làm sẽ chôn mất mấy dòng có việc.
    """
    emps = list(db.execute(select(Employee).order_by(Employee.code)).scalars())
    hs = ban_do_ho_so(db, [e.id for e in emps])
    dong, dem = [], {k: 0 for k in NHAN}
    for e in emps:
        pf = hs.get(e.id)
        for cot_nv, cot_hs, ten in CAP_TRUNG:
            a = getattr(e, cot_nv, None) or None
            b = (getattr(pf, cot_hs, None) or None) if pf is not None else None
            tt = _trang_thai(a, b)
            dem[tt] += 1
            if tt in ("khop", "ca_hai_trong") and not gom_ca_khop:
                continue
            dong.append({
                "employee_id": e.id, "code": e.code or "", "full_name": e.full_name,
                "department": e.department or "", "active": bool(e.active),
                "truong": cot_hs, "ten_truong": ten,
                "o_bang_nhan_su": a.isoformat() if hasattr(a, "isoformat") else a,
                "o_ho_so": b.isoformat() if hasattr(b, "isoformat") else b,
                "trang_thai": tt, "noi": NHAN[tt],
            })
    return {
        "count": len(dong), "rows": dong,
        "tom_tat": {NHAN[k]: v for k, v in dem.items()},
        "cap_trung": [{"truong": h, "ten": t} for _, h, t in CAP_TRUNG],
        "ghi_chu": ("Máy KHÔNG tự chọn bên nào thắng. Dòng «Hai bên khác nhau» phải do HCNS sửa "
                    "tay ở màn Hợp đồng lao động; nút chép chỉ đụng vào ô CÒN TRỐNG bên hồ sơ."),
    }


def chuyen_cho_trong(db: Session, u, xac_nhan: bool = False) -> dict:
    """Chép cột cũ sang hồ sơ, CHỈ ở những ô hồ sơ còn trống. Không bao giờ đè.

    `xac_nhan=False` là bước KHÔNG LÀM GÌ: nó kê ra sẽ chép bao nhiêu, và kê cả phần KHÔNG chép
    kèm lý do. Một cửa chỉ kê phần nó sắp làm sẽ khiến người bấm tin rằng phần còn lại không tồn
    tại — đúng bài học của cửa bàn giao HS-7.
    """
    emps = list(db.execute(select(Employee).order_by(Employee.code)).scalars())
    hs = ban_do_ho_so(db, [e.id for e in emps])
    se_chep, o_lai = [], []
    for e in emps:
        pf = hs.get(e.id)
        for cot_nv, cot_hs, ten in CAP_TRUNG:
            a = getattr(e, cot_nv, None) or None
            if a is None:
                continue
            b = (getattr(pf, cot_hs, None) or None) if pf is not None else None
            muc = {"employee_id": e.id, "code": e.code or "", "full_name": e.full_name,
                   "truong": cot_hs, "ten_truong": ten,
                   "gia_tri": a.isoformat() if hasattr(a, "isoformat") else a}
            if b is None:
                se_chep.append(muc)
            elif b == a:
                o_lai.append({**muc, "ly_do": "hai bên đã khớp"})
            else:
                o_lai.append({**muc, "ly_do": "hai bên KHÁC NHAU — HCNS phải tự chọn",
                              "o_ho_so": b.isoformat() if hasattr(b, "isoformat") else b})

    if not xac_nhan:
        return {"da_chep": False, "se_chep": se_chep, "o_lai": o_lai,
                "message": f"Sẽ chép {len(se_chep)} ô còn trống; {len(o_lai)} ô giữ nguyên."}

    # GHI THẲNG, MỘT LẦN COMMIT, MỘT DÒNG NHẬT KÝ — cố ý KHÔNG gọi `ghi()`/`save_profile()` ở đây.
    # `save_profile` commit và ghi nhật ký cho MỖI người; chạy nó 121 lượt trong một yêu cầu trên
    # gói 0,5 CPU của Render là cách chắc chắn nhất để vượt 60 giây và cướp CPU của nhịp tim
    # `/health` 5 giây — đúng thứ đã giết máy chủ giữa chừng suốt ngày 27/9/2026.
    theo_nguoi: dict[int, dict] = {}
    for m in se_chep:
        cot_nv = next(nv for nv, h, _ in CAP_TRUNG if h == m["truong"])
        theo_nguoi.setdefault(m["employee_id"], {})[m["truong"]] = getattr(
            db.get(Employee, m["employee_id"]), cot_nv)
    for eid, gia_tri in theo_nguoi.items():
        pf = hs.get(eid)
        if pf is None:
            pf = EmployeeProfile(employee_id=eid)
            db.add(pf)
            hs[eid] = pf
        for cot_hs, v in gia_tri.items():
            setattr(pf, cot_hs, v)
        pf.updated_by = u.username
    R.audit(db, u.username, u.role, "gop_ho_so_chep_o_trong", "nhan_su",
            after={"so_nguoi": len(theo_nguoi), "so_o_chep": len(se_chep),
                   "so_o_giu_nguyen": len(o_lai)})
    db.commit()
    return {"da_chep": True, "se_chep": se_chep, "o_lai": o_lai,
            "message": f"Đã chép {len(se_chep)} ô còn trống sang hồ sơ cá nhân; "
                       f"{len(o_lai)} ô giữ nguyên, không đè lên ai."}
