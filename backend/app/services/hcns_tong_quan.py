"""Đợt C – HC01 Tổng quan HCNS. CHỈ ĐỌC, và không sinh ra một con số nào của riêng nó.

NGUYÊN TẮC CỦA MÀN HÌNH NÀY: mỗi ô là một phép đếm trên bảng đã có, và mỗi ô mở ra được tới đúng
danh sách đã sinh ra nó. Một bảng tổng quan có con số mà không mở ra được là một bảng người ta
nhìn rồi bỏ qua; tệ hơn, nó là chỗ một con số sai sống lâu nhất, vì không ai đối chiếu được.

Không có ô nào ở đây được tính bằng công thức riêng. Hợp đồng đến hạn đọc `hrm.contract_alerts`,
hồ sơ thiếu đọc `hrm.profile_completeness`, phép năm đọc `hrm.leave_balance` — cùng hàm mà các
màn hình kia đang dùng. Viết lại phép đếm ở đây là tạo ra một nguồn thứ hai, và hai nguồn sẽ lệch.

BẢNG LƯƠNG KHÔNG MẶC ĐỊNH HIỆN RA. Thẻ Hồ sơ nhân sự mở cho nhiều vai hơn thẻ Bảng lương (Kế toán,
Trưởng phòng Điều hành, Giám đốc Kinh doanh…). Nếu tổng quan in thẳng tổng thực nhận của kỳ thì nó
vừa mở bảng lương cho tất cả những vai ấy bằng cửa sau. Khối lương chỉ được gắn vào khi người gọi
thật sự mở được thẻ Bảng lương, và quyết định ấy do `access.hr_tabs_for` trả lời, không do tệp này.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import DEPARTMENTS, Employee, Incident, PayrollRun
from app.models.hrm import LeaveRequest
from app.models.lich_su_to_chuc import LichSuToChuc


def tong_quan(db: Session, co_bang_luong: bool, hom_nay: date | None = None) -> dict:
    from app.services import hrm as H

    nay = hom_nay or date.today()
    ky = f"{nay:%Y-%m}"
    nhan_su = list(db.execute(select(Employee).where(Employee.active == True)
                              .order_by(Employee.code)).scalars())

    theo_phong: dict[str, dict] = {}
    for e in nhan_su:
        g = theo_phong.setdefault(e.department, {"ma": e.department,
                                                 "ten": DEPARTMENTS.get(e.department, e.department),
                                                 "tong": 0, "hdld": 0, "ctv": 0})
        g["tong"] += 1
        g["hdld" if e.contract_type == "hdld" else "ctv"] += 1

    thieu_ho_so = []
    for e in nhan_su:
        c = H.profile_completeness(db, e.id)
        if c["missing"]:
            thieu_ho_so.append({"ma": e.code, "ten": e.full_name, "phong": e.department,
                                "phan_tram": c["percent"], "thieu": c["missing"]})

    hd = H.contract_alerts(db)

    cho_duyet = [r for r in db.execute(select(LeaveRequest)).scalars() if r.status == "cho_duyet"]
    nghi = [{"id": r.id, "employee_id": r.employee_id, "loai": r.kind, "tu": r.date_from,
             "den": r.date_to, "so_ngay": r.days} for r in cho_duyet]

    su_vu = [i for i in db.execute(select(Incident).where(Incident.status == "hieu_luc")).scalars()
             if i.occurred_on.year == nay.year and i.occurred_on.month == nay.month]

    # Người chưa có một dòng lịch sử tổ chức nào. KHÔNG phải lỗi: lịch sử bắt đầu được ghi từ Đợt C,
    # nên người chưa từng điều chuyển kể từ đó thì chưa có dòng nào. Hiện ra để HCNS biết lịch sử
    # đang phủ tới đâu, thay vì tưởng nó đã phủ hết.
    co_ls = {c.ma_nv for c in db.execute(select(LichSuToChuc)).scalars()}
    chua_co_ls = [{"ma": e.code, "ten": e.full_name, "phong": e.department}
                  for e in nhan_su if e.code not in co_ls]

    ra = {
        "ky": ky,
        "nhan_su": {"tong": len(nhan_su),
                    "hdld": sum(1 for e in nhan_su if e.contract_type == "hdld"),
                    "ctv": sum(1 for e in nhan_su if e.contract_type != "hdld"),
                    "theo_phong": sorted(theo_phong.values(), key=lambda g: -g["tong"])},
        "ho_so_thieu": {"so_nguoi": len(thieu_ho_so), "rows": thieu_ho_so},
        "hop_dong": hd,
        "nghi_phep_cho_duyet": {"so_don": len(nghi), "rows": nghi},
        "su_vu_trong_thang": {"so_vu": len(su_vu),
                              "rows": [{"employee_id": i.employee_id, "muc": i.level,
                                        "ngay": i.occurred_on} for i in su_vu]},
        "lich_su_to_chuc": {"chua_co_dong_nao": len(chua_co_ls), "rows": chua_co_ls,
                            "ghi_chu": "Lịch sử tổ chức bắt đầu được ghi từ Đợt C (07/10/2026). "
                                       "Người chưa từng điều chuyển kể từ đó thì chưa có dòng nào – "
                                       "đó là chưa có dữ liệu, không phải thiếu sót hồ sơ."},
        "co_bang_luong": co_bang_luong,
    }

    if co_bang_luong:
        run = db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first()
        ra["bang_luong"] = None if run is None else {
            "period": run.period, "trang_thai": run.status,
            "so_nguoi": (run.totals or {}).get("so_nguoi"),
            "thuc_nhan": (run.totals or {}).get("thuc_nhan"),
            "tra_trang_thai": getattr(run, "tra_trang_thai", "")}
    return ra
