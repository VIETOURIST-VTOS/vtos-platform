# -*- coding: utf-8 -*-
"""DX-4 — BHXH PHẦN CÔNG TY ĐÓNG: máy tính để ĐỐI CHIẾU, không để ghi hộ.

Việc cuối của danh sách bảy việc lập trình đội xe (chốt 11/10/2026). Chủ tịch duyệt 16/10/2026.

MỘT ĐIỀU PHẢI NÓI TRƯỚC, vì nó đổi hẳn phạm vi việc này. Bản rà 11/10 ghi «`rules.py` chỉ có
`bhxh_nld`, không có phần công ty đóng». Đúng — nhưng đo lại 16/10 thì phía ĐỘI XE đã có cửa:
`NHOM_CHI_PHI_KY` có sẵn nhóm `bhxh` («Bảo hiểm nhân viên công ty đóng», phạm vi cả đội), và Kế
toán nhập tay số của từng kỳ qua cửa chi phí kỳ. Nên cái thiếu KHÔNG phải một cửa nhập.

Cái thiếu là MỘT PHÉP ĐỐI CHIẾU. Con số nhập tay không có gì soi lại: gõ nhầm một chữ số, hoặc
quên một kỳ, thì giá vốn đội xe lệch mà không ai biết. Tệp này tính con số máy từ chính bảng
lương đã chốt, đặt cạnh con số nhập tay, và nói ra khoảng lệch.

═══════════════════════════════════════════════════════════════════════════════════════════════
MÁY KHÔNG TỰ GHI VÀO SỔ
═══════════════════════════════════════════════════════════════════════════════════════════════

Ranh giới Chủ tịch đặt 09/9/2026: hệ thống viết CẤU TRÚC và PHÉP TÍNH, người của các bộ phận
nhập SỐ LIỆU. Nên ở đây không có đường nào ghi vào `fleet_period_costs`. Máy nói «tính ra 182
triệu, sổ đang ghi 170 triệu, lệch 12 triệu» rồi dừng — Kế toán quyết con số nào đúng và tự sửa
ở cửa của họ. Tự ghi đè là lấy mất chữ ký của người chịu trách nhiệm về con số ấy.

RỖNG THÌ NÓI CHƯA CHỐT, KHÔNG COI LÀ 0. Tham số `bhxh_cty` cố ý để trống tới khi Chủ tịch ký.
Coi rỗng là 0 thì màn hình hiện «máy tính 0 đ, sổ ghi 180 triệu, lệch 180 triệu» — một con số
lệch do chính hệ thống bịa ra, và người đọc đi tìm lỗi ở chỗ không có lỗi.

CĂN CỨ LÀ MỨC ĐÓNG BHXH, KHÔNG PHẢI LƯƠNG HỢP ĐỒNG. Cùng căn cứ với phần người lao động đã
tính trong `hr.py`: bảng BHXH tháng 8/2026 ghi mức tham gia 5.310.000 trong khi lương hợp đồng
nhiều người 15–20 triệu. Lấy lương hợp đồng làm căn cứ ra một con số gấp nhiều lần số phải nộp.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fleet import FleetPeriodCost
from app.models.hr import PayrollRun

PHONG_DOI_XE = "doi_xe"
NHOM_BHXH = "bhxh"


def ty_le(db: Session) -> float | None:
    """Tỷ lệ công ty đóng. None = CHƯA AI KÝ, và None không phải là 0."""
    from app.services import rules as R
    chu = (R.get_param_text(db, "bhxh_cty") or "").strip()
    if not chu:
        return None
    try:
        v = float(chu)
    except ValueError:
        return None
    return v if v > 0 else None


def _ky_luong(db: Session, ky: str) -> PayrollRun | None:
    return db.execute(select(PayrollRun).where(PayrollRun.period == ky)).scalars().first()


def may_tinh(db: Session, ky: str) -> dict:
    """Số máy tính được cho ĐỘI XE một kỳ. Chỉ đọc."""
    ty = ty_le(db)
    run = _ky_luong(db, ky)
    if run is None:
        return {"tinh_duoc": False, "so_tien": None, "so_nguoi": 0,
                "vi_sao": f"Chưa có bảng lương kỳ {ky}"}
    dong = [r for r in (run.rows or []) if r.get("phong") == PHONG_DOI_XE]
    co_muc = [r for r in dong if (r.get("bhxh_base") or 0) > 0]
    nen = sum(float(r.get("bhxh_base") or 0) for r in co_muc)
    if ty is None:
        return {"tinh_duoc": False, "so_tien": None, "so_nguoi": len(co_muc), "nen_dong": nen,
                "vi_sao": "Chưa chốt tỷ lệ BHXH phần công ty đóng – Kế toán đề và Chủ tịch ký "
                          "tham số `bhxh_cty` ở màn hình Tham số thì ô này tự tính"}
    return {"tinh_duoc": True, "so_tien": round(nen * ty), "ty_le": ty,
            "nen_dong": nen, "so_nguoi": len(co_muc),
            "so_nguoi_chua_co_muc_dong": len(dong) - len(co_muc),
            "trang_thai_bang_luong": run.status}


def da_nhap_tay(db: Session, ky: str) -> dict:
    """Số Kế toán đã nhập vào chi phí kỳ của đội, nhóm `bhxh`."""
    ds = list(db.execute(select(FleetPeriodCost).where(
        FleetPeriodCost.ky == ky, FleetPeriodCost.nhom == NHOM_BHXH)).scalars())
    return {"so_tien": sum(float(x.so_tien or 0) for x in ds), "so_dong": len(ds)}


def doi_chieu(db: Session, ky: str) -> dict:
    """Đặt hai con số cạnh nhau. KHÔNG sửa dòng nào — xem phần đầu tệp."""
    may = may_tinh(db, ky)
    tay = da_nhap_tay(db, ky)
    lech = None
    if may["tinh_duoc"]:
        lech = round(float(may["so_tien"]) - tay["so_tien"])
    return {
        "ky": ky, "may_tinh": may, "da_nhap_tay": tay, "lech": lech,
        "khop": (lech == 0) if lech is not None else None,
        "ghi_chu": ("Máy tính từ mức đóng BHXH trên bảng lương đã chốt, nhân tỷ lệ công ty đóng. "
                    "Máy KHÔNG tự sửa sổ: Kế toán quyết con số nào đúng và sửa ở cửa chi phí kỳ. "
                    "Căn cứ là MỨC ĐÓNG BHXH, không phải lương hợp đồng – hai con số ấy chênh "
                    "nhau nhiều lần."),
    }
