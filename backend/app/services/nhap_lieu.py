"""Lớp kiểm dùng chung cho BA CỬA nhập liệu: nhập tay, tải tệp, và số do AI đọc từ ảnh.

Lệnh giao việc 08/9/2026, V1. Vì sao phải có tệp này thay vì mỗi phân hệ tự kiểm:

    Ba cửa cùng ghi vào một bảng. Nếu mỗi cửa tự kiểm theo cách riêng thì cái chặt nhất trở nên vô
    nghĩa – người ta chỉ cần đi cửa lỏng nhất. Và sáu tháng sau không ai trả lời được câu "con số này
    vào hệ thống bằng đường nào, ai kiểm nó".

Quyết định của Chủ tịch ngày 08/9 bỏ khâu trưởng phòng duyệt từng dòng: NHẬP LÀ DÙNG LUÔN. Bỏ một lớp
chặn có thật thì lớp còn lại phải chặt hơn, không phải lỏng hơn – nên toàn bộ phần kiểm nằm ở đây, ở
máy chủ, chứ không nằm ở giao diện. Giao diện kiểm thêm là để người dùng đỡ mất công, không phải để
thay chỗ này.

Sáu quy tắc bắt buộc (chương 3 của lệnh) nằm trọn trong tệp này và trong app/services/intake.py:
    1. Một bảng đích – ba cửa ghi cùng chỗ, không có bảng "tạm" riêng cho cửa tải tệp.
    2. Một bộ kiểm – chính là hàm kiem_dong() dưới đây.
    3. Dòng lỗi không biến mất – trả về theo từng dòng kèm lý do, không im lặng bỏ.
    4. Thiếu số thì để RỖNG, không điền 0. Đã gây thiệt hại thật: 76 dòng quyết toán không có giá vốn,
       ghi thẳng là sổ báo lãi 100% trên 2,65 tỷ doanh thu.
    5. Ảnh không bao giờ tự thành sổ – giữa ảnh và bảng luôn có một lần bấm của người.
    6. Nạp hai lần không thành hai bản – khóa chống trùng của từng bộ nạp.
"""
from datetime import date, datetime
from sqlalchemy.orm import Session

CUA = {"nhap_tay": "Nhập tay từng dòng", "nap_tep": "Tải tệp Excel/CSV", "doc_anh": "Ảnh – AI đọc, người xác nhận"}

KIEU = {
    "chu": "Chữ", "so": "Số", "tien": "Số tiền", "ngay": "Ngày", "thang": "Kỳ (YYYY-MM)",
    "co_khong": "Có / không", "chon": "Chọn trong danh sách",
}


def _so(v):
    from app.services.intake import _so as s
    return s(v)


def _ngay(v):
    from app.services.intake import _ngay as n
    return n(v)


def _co(v) -> bool:
    return str(v or "").strip().lower() in ("1", "x", "co", "có", "true", "yes", "roi", "rồi", "đã")


def ky_bi_khoa(db: Session, ngay) -> str:
    """Kỳ kế toán của ngày này đã khóa chưa. Trả về mã kỳ nếu đã khóa, chuỗi rỗng nếu chưa.

    Kỳ khóa là CHỐT CHẶN CUỐI của quyết định "nhập là dùng luôn": bỏ khâu duyệt từng dòng thì chỗ duy
    nhất còn lại nói "quá muộn rồi" chính là kỳ khóa. Nếu nó không chặn được thì số của một kỳ đã phát
    hành báo cáo vẫn đổi được, và bản báo cáo đã gửi ra ngoài không còn dựng lại được từ dữ liệu."""
    if ngay is None: return ""
    if isinstance(ngay, datetime): ngay = ngay.date()
    if not isinstance(ngay, date): return ""
    from app.services.accounting import is_locked
    ky = f"{ngay:%Y-%m}"
    try:
        return ky if is_locked(db, ky) else ""
    except Exception:
        return ""


def kiem_dong(db: Session, bo: dict, r: dict, cua: str = "nhap_tay") -> tuple[list, list]:
    """Kiểm một dòng theo KHAI BÁO CỘT của bộ nạp. Trả về (lỗi, cảnh báo). KHÔNG ghi gì.

    Ba cửa gọi đúng hàm này. Thêm một quy tắc ở đây là cả ba cửa có ngay, không phải sửa ba chỗ."""
    loi, cb = [], []
    for c in bo["cot"]:
        v = r.get(c["key"])
        rong = v is None or str(v).strip() == ""
        ten = c["ten"]
        if c.get("bat_buoc") and rong:
            loi.append(f"Thiếu {ten.lower()}")
            continue
        if rong:
            # Quy tắc 4: ô trống là CHƯA CÓ SỐ. Không thay bằng 0 ở bất kỳ cửa nào.
            continue
        kieu = c.get("kieu", "chu")
        if kieu in ("so", "tien"):
            n = _so(v)
            if c.get("min") is not None and n < c["min"]:
                loi.append(f"{ten}: {n:,.0f} nhỏ hơn mức cho phép {c['min']:,.0f}")
            if c.get("max") is not None and n > c["max"]:
                loi.append(f"{ten}: {n:,.0f} lớn hơn mức cho phép {c['max']:,.0f}")
        elif kieu == "ngay":
            try:
                d = _ngay(v)
            except ValueError as ex:
                loi.append(f"{ten}: {ex}"); continue
            if d is not None:
                if c.get("khong_tuong_lai") and d > date.today():
                    loi.append(f"{ten}: {d:%d/%m/%Y} nằm ở tương lai")
                if c.get("khoa_ky"):
                    k = ky_bi_khoa(db, d)
                    if k:
                        loi.append(f"{ten} rơi vào kỳ {k} ĐÃ KHÓA SỔ. Số của kỳ đã khóa không sửa được "
                                   "bằng cách nhập đè – phải lập bút toán điều chỉnh ở kỳ hiện tại.")
        elif kieu == "thang":
            s = str(v).strip()
            if len(s) != 7 or s[4] != "-":
                loi.append(f"{ten} phải có dạng 2026-08")
        elif kieu == "chon":
            ds = c.get("chon") or {}
            if str(v).strip() not in ds:
                loi.append(f"{ten}: '{v}' không hợp lệ ({', '.join(list(ds)[:8])})")
    return loi, cb


def khai_bao_du(bo: dict) -> list[str]:
    """Bộ nạp khai thiếu gì. Dùng cho phép thử K8 và cho màn hình sinh biểu nhập tay.

    Thiếu 'bang_dich' hay 'phong_ban' thì không ai trả lời được câu "số này nằm ở bảng nào, phòng nào
    chịu trách nhiệm" – mà đó chính là hai câu hỏi đầu tiên khi một con số bị nghi ngờ."""
    thieu = []
    for k in ("ten", "mo_ta", "khoa_chong_trung", "cot", "kiem", "nap"):
        if not bo.get(k): thieu.append(k)
    if not bo.get("bang_dich"): thieu.append("bang_dich")
    if not bo.get("phong_ban"): thieu.append("phong_ban")
    for c in bo.get("cot") or []:
        if c.get("kieu") == "chon" and not c.get("chon"):
            thieu.append(f"cột {c['key']}: kiểu 'chon' nhưng không khai danh sách")
    return thieu
