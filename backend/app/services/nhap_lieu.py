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
    # HAI KIỂU THÊM NGÀY 18/9/2026, cho cửa nhập khách tiềm năng của Marketing.
    #
    # Sổ này là DANH SÁCH ĐÓNG: biểu nhập tay sinh ra từ nó, và `kiem_dong` phân nhánh theo nó. Một
    # cột khai kiểu lạ thì biểu vẽ ra một ô chữ trống trơn và `kiem_dong` KHÔNG kiểm gì cả – lọt
    # lặng, không ai thấy. Phép thử `test_khuon_ba_cua` canh đúng chỗ ấy và nó đã đỏ ngày 18/9.
    #
    # `ngay_gio` – NGÀY CÓ GIỜ, không phải ngày. Lead phát sinh lúc 09:20 và lead chốt lúc 17:05 là
    # hai mốc mà phép tính 30/60/90 ngày đọc tới; cắt mất giờ là làm tròn ngầm về 00:00 và mọi
    # khoảng cách lệch đi tới gần một ngày. Đã có kiểu `ngay` rồi vẫn phải thêm kiểu này, vì dùng
    # `ngay` cho một ô có giờ là mất giờ mà không báo.
    #
    # `he_thong_cap` – Ô CHỈ ĐỂ ĐỌC. Mã lead do hệ thống cấp; khai nó trong danh sách cột là để
    # người đọc biết ô ấy TỒN TẠI, không phải để ai gõ vào. Không có kiểu này thì biểu nhập tay vẽ
    # ra một ô chữ trống cho người dùng gõ mã lead – và thế là một con số có hai nguồn cấp, đúng
    # cái mà cả hệ thống đang tránh.
    "ngay_gio": "Ngày giờ", "he_thong_cap": "Hệ thống tự cấp – không nhập",
}


def _so(v):
    from app.services.intake import _so as s
    return s(v)


def _ngay(v):
    from app.services.intake import _ngay as n
    return n(v)


# Khuôn NGÀY GIỜ nhận được. Ít khuôn, và cố ý: mỗi khuôn thêm vào là một chuỗi mà máy đoán hộ người
# nhập, và có những chuỗi ("03/04/2026 09:20") đoán kiểu nào cũng ra một ngày có thật.
_KHUON_NGAY_GIO = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
                   "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


def _ngay_gio(v):
    """Đọc một ô NGÀY GIỜ. Ô chỉ có ngày thì trả 00:00 của ngày ấy. Đọc không ra thì NÉM LỖI.

    Trả `None` lặng lẽ cho chuỗi không đọc được là cách một ô có chữ trong tệp biến thành một ô
    rỗng trong sổ, và không dòng nào kêu lên.
    """
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    s = str(v or "").strip()
    if not s:
        return None
    for khuon in _KHUON_NGAY_GIO:
        try:
            return datetime.strptime(s, khuon)
        except ValueError:
            continue
    # Chỉ có ngày, không có giờ. `_ngay` NÉM LỖI cho mọi chuỗi không đọc được và chỉ trả `None` cho
    # ô rỗng – mà ô rỗng đã ra ở trên rồi. Nên đến đây không có đường nào ra `None`, và cố ý KHÔNG
    # thêm một dòng `if d is None: raise` cho chắc: dòng ấy không chạy bao giờ, nên nó không bảo vệ
    # được gì, chỉ làm người đọc sau tưởng có một trường hợp nữa cần lo.
    d = _ngay(s)
    return datetime(d.year, d.month, d.day)


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
        elif kieu == "ngay_gio":
            # Ô CÓ GIỜ. Không rơi vào nhánh `ngay` ở trên: `_ngay` cắt mất phần giờ, và cắt im lặng.
            try:
                _ngay_gio(v)
            except ValueError as ex:
                loi.append(f"{ten}: {ex}")
        elif kieu == "he_thong_cap":
            # CỐ Ý KHÔNG KIỂM GÌ, và đây là chỗ dễ sửa sai nên phải viết ra.
            #
            # Phản xạ đầu tiên là báo lỗi "ô này hệ thống cấp, đừng gõ vào". Sai: `kiem_dong` chạy
            # cho CẢ BA CỬA, kể cả cửa tải tệp, mà tệp xuất ra từ hệ thống rồi nạp lại thì MANG
            # SẴN mã ấy – và chính cái mã ấy là khoá chống trùng để nạp lại không nhân đôi dòng.
            # Cấm ở đây là cấm luôn đường nạp lại.
            #
            # Chỗ chặn người gõ tay là BIỂU NHẬP TAY: ô kiểu này vẽ ra dạng chỉ-đọc
            # (web/app/nap-du-lieu/page.tsx). Khai kiểu ở đây là để biểu biết mà vẽ như vậy.
            pass
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
