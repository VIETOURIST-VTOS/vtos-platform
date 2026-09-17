# -*- coding: utf-8 -*-
"""TC-61 · HÌNH BỐN MỐC KHÔNG CÒN ĐỨNG TRÊN MÀN HÌNH CHỦ TỊCH.

    "BỎ khỏi màn hình chủ tịch, và thiết kế lại cho đẹp giống bản thử 01"
                                                          — anh Tuấn, 17/9/2026

Anh Tuấn chụp đúng một khung biểu đồ RỖNG kèm câu "Chưa có kỳ nào có số trong 4 kỳ gần nhất".

══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CHUYỂN XUỐNG CHỨ KHÔNG XOÁ — VÀ VÌ SAO ĐIỀU ẤY PHẢI CÓ PHÉP THỬ CANH
══════════════════════════════════════════════════════════════════════════════════════════════
Từ TC-59, câu hỏi "ba tháng tới tiền đi thế nào" đã có hình 13 tuần trả lời ở đầu khối. Hình bốn
mốc ở giữa màn hình vì thế vừa rỗng vừa nói lại một việc đã có người nói — đúng thứ phải bỏ.

Nhưng `/dong-tien` KHÔNG có hình nào vẽ bốn mốc (đã soát cả tệp). Xoá hẳn là bỏ mất bản vẽ DUY
NHẤT của một con số mà Kế toán sẽ nạp — tức bỏ một năng lực chỉ vì hôm nay nó chưa có số, đúng
cái lỗi mà luật "rỗng khác không" của dự án sinh ra để chặn.

Nên nó xuống nằm cạnh CHÍNH cái bảng nó mô tả, trong nếp gấp "Bảng bốn mốc". Màn hình lúc mở ra
không còn thấy nó; ai cần thì bung nếp gấp là có cả hình lẫn bảng.

HAI CHỖ DỄ HỎNG
1. HÌNH TRÔI NGƯỢC LÊN. Một vòng sau có người thấy `BieuDoBonMoc` "đáng lẽ phải nổi bật hơn" và
   kéo nó ra khỏi nếp gấp. Không lỗi nào báo, và anh Tuấn lại thấy đúng cái khung rỗng cũ.
2. AI ĐÓ XOÁ HẲN CHO GỌN, kéo theo `docHoDongTien` — câu đọc hộ mà TC-38 và TC-40 canh — rồi phải
   gỡ luôn hai phép thử ấy. Lúc ấy không còn chỗ nào trong hệ thống vẽ bốn mốc.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"


def _ma(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


def test_hinh_bon_moc_nam_trong_nep_gap_khong_nam_tren_man_hinh():
    """Chỗ hỏng số 1."""
    ma = _ma(KHOI)
    assert "<BieuDoBonMoc" in ma, "Hình vẫn phải còn — xem chuỗi tài liệu đầu tệp trước khi xoá."
    assert ma.count("<BieuDoBonMoc") == 1, "Chỉ được vẽ ở MỘT chỗ."
    i = ma.index("<details")
    assert ma.index("<BieuDoBonMoc") > i, (
        "Hình bốn mốc phải nằm TRONG nếp gấp 'Bảng bốn mốc'. Đứng ngoài là nó trở lại giữa màn "
        "hình Chủ tịch — đúng cái khung rỗng anh Tuấn chụp và bảo bỏ ngày 17/9/2026."
    )


def test_hinh_dung_truoc_bang_trong_nep_gap():
    """Hình trả lời 'bốn mốc đi lên hay đi xuống', bảng trả lời 'dòng nào làm nên điều đó'.

    Đảo thứ tự là bắt người vừa bung nếp gấp đọc mười bốn dòng số trước khi thấy hình dáng của
    chúng — cùng lý lẽ đã dùng khi xếp hình trước chú thích ở TC-59.
    """
    ma = _ma(KHOI)
    i = ma.index("<details")
    assert ma.index("<BieuDoBonMoc", i) < ma.index('className="panel wrap"', i)


def test_cau_doc_ho_van_con_va_van_di_cung_hinh():
    """Chỗ hỏng số 2 — canh cái ràng buộc, không canh cái tên.

    `docHoDongTien` là câu đọc hộ mà TC-38 và TC-40 canh. Nó chỉ có một người dùng: hình bốn mốc.
    Xoá hình mà quên nó thì nó thành hàm mồ côi; xoá cả hai thì hai phép thử kia đỏ, và đó chính là
    cái chuông phải reo — không được tắt chuông bằng cách sửa phép thử.
    """
    ma = _ma(KHOI)
    assert "function docHoDongTien" in ma
    i = ma.index("function BieuDoBonMoc")
    than = ma[i:ma.index("\n}", ma.index("return (", i))]
    assert "docHoDongTien(" in than, "Câu đọc hộ phải được gọi từ chính hình nó đọc hộ."
