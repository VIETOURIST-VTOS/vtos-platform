"""5.8 Báo cáo biến động nhân sự (Chủ tịch giao 08/10/2026: "báo cáo biến động em đề xuất").

MỘT PHÉP TÍNH, VÀ NÓ PHẢI CÂN:

    đầu kỳ  +  tăng trong kỳ  −  giảm trong kỳ  =  cuối kỳ

Báo cáo này không có phép tính thứ hai. Mọi con số khác — cơ cấu theo phòng, tỷ lệ nghỉ việc, thâm
niên — đều là cách CẮT cùng một tập người, không phải một nguồn số mới. Nên có một hàng rào đòi
đẳng thức trên đúng cho MỌI phòng; lệch một người là có một đường vào hoặc ra mà bộ đếm không thấy.

────────────────────────────────────────────────────────────────────────────────────────────────
BA CHỖ DỄ LÀM SAI, VÀ CÁCH TỆP NÀY TRÁNH
────────────────────────────────────────────────────────────────────────────────────────────────

1. ĐẾM NGƯỜI ĐÃ NGHỈ MÀ CHƯA CÓ NGÀY NGHỈ VÀO "GIẢM KỲ NÀY". VTOS trước VB-1 chỉ có `active`, nên
   có sẵn một nhóm người `active = False` không ngày. Nhét họ vào kỳ đang xem thì tháng đầu tiên
   chạy báo cáo sẽ có một cú giảm giả bằng cả lịch sử công ty. Họ nằm riêng ở `chua_biet_ngay_nghi`
   và màn hình in ra — đó là việc HCNS điền, không phải số để báo cáo lên.

2. LẤY `department` HÔM NAY CHO MỘT KỲ ĐÃ QUA. Người chuyển phòng giữa năm thì bản đồ cơ cấu của
   quý trước tự viết lại mỗi lần mở. Ở đây nói THẲNG rằng cơ cấu cắt theo phòng HIỆN TẠI, và chuyển
   phòng KHÔNG đếm là tăng/giảm (nó không đổi tổng đầu người) — muốn lịch sử phòng thì cần một sổ
   chuyển phòng, và đó là việc chưa có, khai ra ở `CHUA_CO`.

3. TÍNH TỶ LỆ NGHỈ VIỆC TRÊN ĐẦU KỲ. Chuẩn là trên BÌNH QUÂN đầu kỳ và cuối kỳ: một phòng 2 người
   mất 1 người thì chia cho 2 ra 50%, chia cho bình quân 1,5 ra 67% — và 67% mới là thứ mô tả đúng
   cái phòng ấy vừa trải qua. Công thức ghi ngay cạnh con số trên màn hình.
"""
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import Employee
from app.models.hrm import LaborContract

# Lý do giảm. Khai ở đây MỘT chỗ; màn hình đọc đúng bảng này nên không có chuyện hai danh sách lệch.
# "chuyen_cong_ty" tách riêng khỏi "tu_xin" vì chuyển sang pháp nhân khác trong tập đoàn KHÔNG phải
# người rời Vietourist Holdings — gộp chung thì tỷ lệ nghỉ việc của nhóm báo cáo lên HĐQT bị thổi lên.
LY_DO_GIAM = {
    "tu_xin": "Tự xin nghỉ",
    "het_han": "Hết hạn hợp đồng, không ký tiếp",
    "cho_thoi": "Công ty cho thôi việc",
    "chuyen_cong_ty": "Chuyển sang pháp nhân khác trong tập đoàn",
    "khac": "Khác",
}
# Lý do KHÔNG tính vào tỷ lệ nghỉ việc — người vẫn ở trong tập đoàn.
GIAM_KHONG_TINH_NGHI_VIEC = ("chuyen_cong_ty",)

# Khai THẲNG những thứ báo cáo này chưa trả lời được, thay vì để người đọc tự suy ra từ chỗ trống.
CHUA_CO = {
    "chuyen_phong": "chưa có sổ chuyển phòng — cơ cấu cắt theo phòng HIỆN TẠI của mỗi người, "
                    "nên bản đồ phòng của một kỳ đã qua sẽ đổi nếu có người chuyển phòng sau đó",
    "ly_do_tuyen": "chưa có nguồn tuyển (giới thiệu / tin tuyển / hội chợ việc làm) trên hồ sơ",
}


def _bien(ky_loai: str, ky: str) -> tuple[date, date]:
    """Ngày đầu và ngày SAU ngày cuối của kỳ — nửa khoảng [đầu, sau_cuoi)."""
    if ky_loai == "thang":
        nam, thang = int(ky[:4]), int(ky[5:7])
        return date(nam, thang, 1), date(nam + (thang == 12), (thang % 12) + 1, 1)
    if ky_loai == "quy":
        nam, q = int(ky[:4]), int(ky[6])
        dau = date(nam, q * 3 - 2, 1)
        return dau, (date(nam + 1, 1, 1) if q == 4 else date(nam, q * 3 + 1, 1))
    if ky_loai == "nam":
        nam = int(ky)
        return date(nam, 1, 1), date(nam + 1, 1, 1)
    raise ValueError(f"Loại kỳ không hợp lệ: {ky_loai!r}. Chỉ có thang, quy, nam.")


def _co_mat(e: Employee, moc: date) -> bool:
    """Người này có mặt trong bảng lương tại thời điểm `moc` không?

    Vào trước mốc (hoặc không khai ngày vào) VÀ chưa nghỉ tính đến mốc. Người chưa khai `start_date`
    được coi là đã có mặt từ trước: VTOS nhận bảng lương từ kho cũ, và loại họ ra thì đầu kỳ của
    tháng đầu tiên sẽ nhỏ hơn số người thật đúng bằng nhóm chưa khai ngày vào.
    """
    if e.start_date and e.start_date >= moc:
        return False
    if e.ended_on and e.ended_on < moc:
        return False
    return True


def bao_cao(db: Session, ky_loai: str, ky: str) -> dict:
    dau, sau_cuoi = _bien(ky_loai, ky)
    nv = list(db.execute(select(Employee)).scalars())

    theo_phong: dict[str, dict] = {}

    def o(p: str) -> dict:
        return theo_phong.setdefault(p or "(chưa khai phòng)", {
            "dau_ky": 0, "tang": 0, "giam": 0, "cuoi_ky": 0,
            "giam_nghi_viec": 0, "giam_chuyen_cong_ty": 0})

    for e in nv:
        p = o(e.department)
        if _co_mat(e, dau):
            p["dau_ky"] += 1
        if _co_mat(e, sau_cuoi):
            p["cuoi_ky"] += 1
        if e.start_date and dau <= e.start_date < sau_cuoi:
            p["tang"] += 1
        if e.ended_on and dau <= e.ended_on < sau_cuoi:
            p["giam"] += 1
            if e.end_kind in GIAM_KHONG_TINH_NGHI_VIEC:
                p["giam_chuyen_cong_ty"] += 1
            else:
                p["giam_nghi_viec"] += 1

    for p in theo_phong.values():
        # Tỷ lệ nghỉ việc trên BÌNH QUÂN đầu kỳ và cuối kỳ, không trên đầu kỳ.
        bq = (p["dau_ky"] + p["cuoi_ky"]) / 2
        p["binh_quan"] = bq
        p["ty_le_nghi_viec"] = round(p["giam_nghi_viec"] / bq * 100, 1) if bq else None
        # Đẳng thức phải cân cho TỪNG phòng. Lệch là có một đường vào hoặc ra bộ đếm không thấy.
        p["lech"] = p["dau_ky"] + p["tang"] - p["giam"] - p["cuoi_ky"]

    tong = {k: sum(p[k] for p in theo_phong.values())
            for k in ("dau_ky", "tang", "giam", "cuoi_ky", "giam_nghi_viec",
                      "giam_chuyen_cong_ty", "lech")}
    bq = (tong["dau_ky"] + tong["cuoi_ky"]) / 2
    tong["binh_quan"] = bq
    tong["ty_le_nghi_viec"] = round(tong["giam_nghi_viec"] / bq * 100, 1) if bq else None

    return {
        "ky_loai": ky_loai, "ky": ky,
        "tu_ngay": dau.isoformat(), "den_ngay": (sau_cuoi).isoformat(),
        "theo_phong": theo_phong, "tong": tong,
        "cach_tinh_ty_le": "giảm (không kể chuyển pháp nhân) ÷ bình quân đầu kỳ và cuối kỳ",
        "chua_biet_ngay_nghi": chua_biet_ngay_nghi(db),
        "chua_co": CHUA_CO,
    }


def chua_biet_ngay_nghi(db: Session) -> dict:
    """Người đã `active = False` mà CHƯA có ngày nghỉ — việc HCNS phải điền, không phải số để báo cáo.

    Không có bộ đếm này thì nhóm ấy chìm đi: họ không nằm trong bất kỳ kỳ nào, nên mọi kỳ đều cân,
    và cái cân ấy là cân giả — tổng cuối kỳ thiếu đúng bằng số người không ai biết nghỉ hôm nào.
    """
    ds = list(db.execute(select(Employee).where(
        Employee.active.is_(False), Employee.ended_on.is_(None))).scalars())
    theo_phong: dict[str, int] = {}
    for e in ds:
        k = e.department or "(chưa khai phòng)"
        theo_phong[k] = theo_phong.get(k, 0) + 1
    return {"so_nguoi": len(ds), "theo_phong": theo_phong,
            "rows": [{"employee_id": e.id, "ma_nv": e.code, "ho_ten": e.full_name,
                      "department": e.department} for e in ds[:200]]}


def co_cau(db: Session) -> dict:
    """Cơ cấu người ĐANG LÀM, cắt theo ba chiều. Cắt theo phòng HIỆN TẠI — xem CHUA_CO."""
    nv = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())
    def dem(f):
        r: dict[str, int] = {}
        for e in nv:
            k = f(e) or "(chưa khai)"
            r[k] = r.get(k, 0) + 1
        return r
    hom_nay = date.today()
    tham_nien = {"duoi_1_nam": 0, "1_den_3_nam": 0, "tren_3_nam": 0, "chua_khai_ngay_vao": 0}
    for e in nv:
        if not e.start_date:
            tham_nien["chua_khai_ngay_vao"] += 1
            continue
        nam = (hom_nay - e.start_date).days / 365.25
        tham_nien["duoi_1_nam" if nam < 1 else "1_den_3_nam" if nam < 3 else "tren_3_nam"] += 1
    return {"so_nguoi": len(nv), "theo_phong": dem(lambda e: e.department),
            "theo_loai_hop_dong": dem(lambda e: e.contract_type),
            "theo_van_phong": dem(lambda e: e.office), "tham_nien": tham_nien}


def ghi_nghi_viec(db: Session, boi: User, employee_id: int, ngay: date, ly_do_loai: str,
                  ly_do: str = "") -> dict:
    """CỬA NHẬP của mục 5.8 — HCNS ghi ngày nghỉ. Không có cửa này thì hai cột kia mãi rỗng.

    Ghi ngày nghỉ KHÔNG tự chấm dứt hợp đồng lao động, và ngược lại: hai việc có hai chứng từ và
    hai ngày có thể khác nhau (bàn giao xong mới ký thanh lý). Nối tự động thì một lần bấm ở đây
    lặng lẽ đóng một hợp đồng mà không ai ký.
    """
    e = db.get(Employee, employee_id)
    if e is None:
        raise ValueError(f"Không có hồ sơ nhân sự id={employee_id}.")
    if ly_do_loai not in LY_DO_GIAM:
        raise ValueError(f"Lý do nghỉ không hợp lệ: {ly_do_loai!r}. "
                         f"Chỉ có {', '.join(LY_DO_GIAM)}.")
    if e.start_date and ngay < e.start_date:
        raise ValueError(f"Ngày nghỉ {ngay} trước ngày vào {e.start_date}.")
    if ngay > date.today():
        raise ValueError("Ngày nghỉ ở tương lai — báo cáo biến động đọc ngày này, "
                         "một ngày chưa tới sẽ làm kỳ hiện tại giảm trước khi người ấy nghỉ.")
    e.ended_on, e.end_kind, e.end_reason = ngay, ly_do_loai, (ly_do or "").strip()[:300]
    e.active = False
    db.flush()
    return {"employee_id": e.id, "ma_nv": e.code, "ho_ten": e.full_name,
            "ended_on": e.ended_on.isoformat(), "end_kind": e.end_kind,
            "end_kind_ten": LY_DO_GIAM[e.end_kind], "end_reason": e.end_reason,
            "active": e.active}


def huy_nghi_viec(db: Session, boi: User, employee_id: int, ly_do: str) -> dict:
    """Gỡ ngày nghỉ (ghi nhầm người, hoặc người quay lại). BẮT BUỘC ghi lý do.

    Có cửa gỡ là có chủ ý: không có nó thì một lần bấm nhầm sẽ được chữa bằng cách sửa thẳng cơ sở
    dữ liệu, và lần sửa ấy không để lại dấu vết nào.
    """
    if not (ly_do or "").strip():
        raise ValueError("Gỡ ngày nghỉ thì phải ghi lý do.")
    e = db.get(Employee, employee_id)
    if e is None:
        raise ValueError(f"Không có hồ sơ nhân sự id={employee_id}.")
    if e.ended_on is None:
        raise ValueError("Hồ sơ này chưa có ngày nghỉ để gỡ.")
    e.ended_on, e.end_kind = None, ""
    e.end_reason = f"[gỡ {date.today():%d/%m/%Y} bởi {boi.username}] {ly_do.strip()}"[:300]
    e.active = True
    db.flush()
    return {"employee_id": e.id, "ended_on": None, "active": True, "end_reason": e.end_reason}


def meta() -> dict:
    return {"ly_do_giam": LY_DO_GIAM,
            "giam_khong_tinh_nghi_viec": list(GIAM_KHONG_TINH_NGHI_VIEC),
            "chua_co": CHUA_CO}
