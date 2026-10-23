# -*- coding: utf-8 -*-
"""Đợt R4b-2a (22/10/2026) — HAI CỘT HÓA ĐƠN TRÊN DÒNG BÚT TOÁN.

VÌ SAO ĐỢT NÀY KHÔNG DÙNG LẠI `doc_no`, và vì sao điều đó đáng một phép thử

`journal_lines.doc_no` đã có sẵn, và chú thích cũ của nó ghi "số hóa đơn / số chứng từ gốc" —
một cột hai nghĩa. Đo trên main 22/10/2026: chỗ DUY NHẤT ghi vào nó trong bộ quy tắc là
`services/hach_toan.py` và nó ghi `boi_canh["so_chung_tu"]`, tức SỐ CHỨNG TỪ; sáu chỗ trong
`services/books.py` chỉ đọc; giao diện không dùng; phép thử KHÔNG CÓ CHỖ NÀO.

Dùng lại nó làm số hóa đơn thì mỗi lần bộ quy tắc tự ghi sổ sẽ đè mất số hóa đơn — sổ vẫn cân,
báo cáo vẫn ra số, không phép thử nào đỏ. Đúng hình dạng lỗi `item_code` chở hai nghĩa mà Đợt
R3a phải đi gỡ. `test_r4b2_1` là chỗ giữ cho chuyện ấy không quay lại.

NĂM CHUYỆN TỆP NÀY CANH:

 1. `doc_no` giữ nguyên nghĩa SỐ CHỨNG TỪ, và hai cột hóa đơn là cột RIÊNG.
 2. Luật ba trạng thái — gọi thẳng hàm thuần `kiem_hoa_don`, không cần phiên hay bảng.
 3. Excel Sổ chi tiết: bốn hàng (tiêu đề, đầu kỳ, dữ liệu, cộng) phải CÙNG số ô. Lệch một ô là
    cả cột lệch hàng, mà bảng vẫn mở được bình thường — không ai thấy cho tới lúc đối chiếu.
 4. Bản di trú có đủ sáu cột, và KHÔNG đụng `doc_no`.
 5. Luật đếm ghim ở đúng nhánh tài khoản thuế GTGT.
"""
import ast
import os
import re
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "app", "models", "accounting.py")
SVC = os.path.join(ROOT, "app", "services", "books.py")
VER = os.path.join(ROOT, "alembic", "versions")


def _doc(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_r4b2_1_doc_no_GIU_NGUYEN_nghia_so_chung_tu():
    """Mất chốt này thì ai đó lại gộp hai nghĩa vào một cột, và không gì bắt được."""
    s = _doc(MODEL)
    assert "so_hoa_don: Mapped[str]" in s and "ngay_hoa_don: Mapped[date | None]" in s, (
        "Thiếu một trong hai cột hóa đơn riêng trên `journal_lines`.")
    dong = [d for d in s.splitlines() if "doc_no: Mapped[str]" in d]
    assert len(dong) == 1, f"Chờ đúng một dòng khai `doc_no`, thấy {len(dong)}."
    assert "số hóa đơn" not in dong[0], (
        "Chú thích của `doc_no` lại nói nó là số hóa đơn. Cột ấy mang SỐ CHỨNG TỪ — đo 22/10/2026: "
        "chỗ duy nhất ghi vào nó là `hach_toan.py`, và nó ghi `so_chung_tu`. Một cột một nghĩa.\n"
        f"Dòng đang có: {dong[0].strip()}")


def test_r4b2_2_luat_ba_trang_thai():
    """Hàm THUẦN, nên phép thử này không cần phiên, không cần bảng, và sẽ không bị ai bỏ."""
    import sys
    sys.path.insert(0, ROOT)
    from app.services.books import HD_CHUA, HD_DA_NHAP, HD_KHONG, kiem_hoa_don

    kiem_hoa_don(HD_DA_NHAP, date(2026, 10, 12), "1C26TSH 0004127", "")
    kiem_hoa_don(HD_KHONG, None, "", "vé giấy tại trạm, không lấy được hóa đơn")
    kiem_hoa_don(HD_CHUA, None, "", "")

    for tt, ngay, so, ly in (
        (HD_DA_NHAP, None, "1C26 0001", ""),        # thiếu ngày
        (HD_DA_NHAP, date(2026, 10, 1), "   ", ""),  # số toàn khoảng trắng
        (HD_KHONG, None, "", "   "),                 # miễn hóa đơn mà không nói vì sao
        ("da_duyet", None, "", ""),                  # trạng thái không có thật
    ):
        try:
            kiem_hoa_don(tt, ngay, so, ly)
        except ValueError:
            continue
        raise AssertionError(f"Phải đỏ mà lại cho qua: {(tt, ngay, so, ly)}")


def test_r4b2_3_excel_so_chi_tiet_BON_HANG_CUNG_SO_O():
    """Lệch một ô là cả cột lệch hàng — bảng vẫn mở được, nên không ai thấy cho tới lúc đối chiếu."""
    import sys
    sys.path.insert(0, ROOT)
    from app.services import books as BK

    rep = {"account": "331", "name": "Phải trả người bán", "kind": "no", "accounts": ["331"],
           "since": date(2026, 10, 1), "upto": date(2026, 10, 31),
           "partner_code": "", "project_code": "", "opening": -214600000.0, "detail": True,
           "total": {"debit": 250000000.0, "credit": 137100000.0}, "closing": -101700000.0,
           "total_rows": 1, "shown_rows": 1, "truncated": False, "limit": 2000,
           "rows": [{"date": date(2026, 10, 3), "code": "HDM-2610-052", "doc_no": "CT-01",
                     "description": "Dịch vụ xe", "account": "331", "contra": "1541",
                     "partner": "Vietrip", "partner_code": "VT", "project_code": "T1",
                     "debit": 0, "credit": 32000000.0, "entry_id": 1, "line_id": 1,
                     "ngay_hoa_don": date(2026, 10, 3), "so_hoa_don": "1C26TVT 0000918",
                     "hoa_don_trang_thai": "da_nhap", "balance_debit": None,
                     "balance_credit": 246600000.0}]}
    b = BK.account_book_xlsx(rep)
    assert isinstance(b, (bytes, bytearray)) and len(b) > 0

    s = _doc(SVC)
    i = s.find('title = ("SỔ CHI TIẾT TÀI KHOẢN')
    than = s[i:i + 2600]
    assert '"Ngày hóa đơn", "Số hóa đơn"' in than, "Excel Sổ chi tiết thiếu hai cột hóa đơn."
    cols = re.search(r"cols = \[(.*?)\]", than, re.S).group(1)
    widths = re.search(r"widths = \[(.*?)\]", than, re.S).group(1)
    n_cols = len([x for x in cols.split(",") if x.strip()])
    n_w = len([x for x in widths.split(",") if x.strip()])
    assert n_cols == n_w == 14, f"cols={n_cols} widths={n_w} — chờ 14 và 14."


def test_r4b2_4_ban_di_tru_du_sau_cot_va_khong_dung_doc_no():
    # Lọc theo MÃ BẢN DI TRÚ, không theo chữ trong tên tệp. Kho đã có sẵn hai bản di trú khác
    # mang chữ "hoa_don" (`..._hoa_don_dau_vao_dong_chi_phi` và `..._so_nhay_hoa_don`), nên lọc
    # theo tên sẽ bắt nhầm cả ba — đã đỏ thật ở lần chạy thử 22/10/2026 lúc 23:51.
    tep = [f for f in os.listdir(VER) if f.startswith("r4b2a") and f.endswith(".py")]
    assert len(tep) == 1, f"Chờ đúng một bản di trú của Đợt R4b-2a, thấy {tep}"
    s = _doc(os.path.join(VER, tep[0]))
    ast.parse(s)
    for c in ("ngay_hoa_don", "so_hoa_don", "hoa_don_trang_thai", "hoa_don_ly_do",
              "hoa_don_nguoi_ghi", "hoa_don_ghi_luc"):
        assert f'"{c}"' in s, f"bản di trú thiếu cột {c}"
    assert "doc_no" not in s, (
        "Bản di trú chạm tới `doc_no`. Đợt này KHÔNG được đụng cột ấy — nó đang mang số chứng từ "
        "của mọi bút toán đã ghi sổ.")
    assert "op.drop_column" in s, "thiếu downgrade dọn lại — một bản di trú không lùi được là một ngõ cụt"


def test_r4b2_6_cua_ghi_KHONG_tu_noi_hai_vai_hep():
    """Bản đầu của đợt này khai `ketoan_tt` + `ketoan_truong` và `hang-rao-gop` ĐỎ ngay.

    Hai vai ấy có bảng ký đã chốt từ Đợt E2b, ghim ở `test_le2b_ba_vai_ke_toan`. Thêm một cửa
    cho chúng là nới một quyền chưa ai ký — đúng cái Lỗi 3 mà bản rà soát v1.0 đã bắt một lần.
    Muốn mở thì sửa BẢNG KÝ trước, bằng một quyết định có chữ ký.
    """
    s = _doc(os.path.join(ROOT, "app", "api", "v1", "books.py"))
    dong = [d for d in s.splitlines() if d.startswith("GHI_HOA_DON")]
    assert len(dong) == 1, f"Chờ đúng một dòng khai GHI_HOA_DON, thấy {len(dong)}."
    assert dong[0].strip() == 'GHI_HOA_DON = ("ketoan",)', (
        "Cửa ghi hóa đơn đang mở cho vai khác vai nền `ketoan`. Nếu đó là chủ ý thì phải sửa bảng "
        "ký của Đợt E2b trước — `test_le2b_ba_vai_ke_toan` ghim bảng ấy và sẽ đỏ.\n"
        f"Dòng đang có: {dong[0].strip()}")


def test_r4b2_5_luat_dem_ghim_o_nhanh_thue():
    import sys
    sys.path.insert(0, ROOT)
    from app.services.books import TK_THUE
    assert set(TK_THUE) == {"133", "3331"}, (
        "Luật đếm đổi mà không ai quyết. Chủ tịch chốt 22/10/2026: một dòng CẦN hóa đơn khi chứng "
        "từ của nó có chạm thuế GTGT — nhánh 133 (đầu vào) hoặc 3331 (đầu ra). Nới ra là kéo vào "
        f"cả những dòng thật sự không cần hóa đơn. Đang thấy: {TK_THUE}")
