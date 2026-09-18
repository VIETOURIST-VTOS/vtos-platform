# -*- coding: utf-8 -*-
"""TC-61 → TC-63 · HÌNH VÀ BẢNG BỐN MỐC RỜI HẲN MÀN HÌNH CHỦ TỊCH.

    "BỎ khỏi màn hình chủ tịch, và thiết kế lại cho đẹp giống bản thử 01"
                                                          — anh Tuấn, 17/9/2026
    "em chuyển qua gộp với dòng tiền hoặc là ẩn khỏi màn hình chủ tịch"
                                                          — anh Tuấn, 18/9/2026

══════════════════════════════════════════════════════════════════════════════════════════════
MỘT LUẬT ĐI HAI CHẶNG — GHI CẢ HAI, VÌ CHẶNG SAU CHỈ HIỂU ĐƯỢC KHI BIẾT CHẶNG TRƯỚC
══════════════════════════════════════════════════════════════════════════════════════════════
CHẶNG 1 (TC-61, 17/9). Anh Tuấn chụp một khung biểu đồ RỖNG kèm câu "Chưa có kỳ nào có số trong 4
kỳ gần nhất" và bảo bỏ. Lúc ấy KHÔNG xoá được: soát cả `/dong-tien` thì màn hình ấy không có hình
nào vẽ bốn mốc, nên xoá hẳn là bỏ mất bản vẽ DUY NHẤT của một con số mà Kế toán sẽ nạp — mất một
năng lực chỉ vì hôm nay nó chưa có số, đúng cái luật "rỗng khác không" sinh ra để chặn. Nên nó
xuống nằm trong nếp gấp "Bảng bốn mốc" ngay tại chỗ, và phép thử canh nó nằm TRONG nếp gấp.

CHẶNG 2 (TC-63, 18/9). Nếp gấp giấu được bảng khỏi mắt, nhưng không bỏ được cái TRÙNG: cùng một
dòng tiền vẫn bị đếm ba lần trên một màn hình — bốn mốc luỹ kế theo ngày cam kết, Phải thu/Phải
trả theo bảy nhóm hạn, hình 13 tuần theo tuần. Anh Tuấn cho hai lối, và lối "gộp với dòng tiền"
là lối giữ được mọi thứ: cả khối sang components/BangBonMoc.tsx và đứng trên /dong-tien, THAY cho
bảng bốn mốc cũ ở đó. Hai cái nút mà TC-61 lo mất — đổi kiểu xem và Xuất Excel — đi cùng bảng.

Vậy phép thử này lật chiều: hình bốn mốc không được có mặt trong KhoiDongTien.tsx nữa, và phải có
mặt trong BangBonMoc.tsx. Cái nó canh vẫn là MỘT RÀNG BUỘC, không phải một tên: bốn mốc phải được
vẽ ĐÚNG MỘT CHỖ trong hệ thống, và chỗ ấy không phải màn hình Chủ tịch.

HAI CHỖ DỄ HỎNG
1. AI ĐÓ KÉO HÌNH VỀ màn hình Chủ tịch "cho dễ thấy". Không lỗi nào báo, và anh Tuấn lại gặp đúng
   cái khung rỗng cũ.
2. AI ĐÓ XOÁ HẲN CHO GỌN, kéo theo `docHoDongTien` — câu đọc hộ mà TC-38 và TC-40 canh — hoặc kéo
   theo nút Xuất Excel. Lúc ấy không còn chỗ nào trong hệ thống vẽ bốn mốc, và mất một cửa xuất
   tệp không có bản sao ở đâu khác.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"
BANG = GOC / "web" / "components" / "BangBonMoc.tsx"
TRANG_DT = GOC / "web" / "app" / "dong-tien" / "page.tsx"


def _ma(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


def test_hinh_bon_moc_khong_con_tren_man_hinh_chu_tich():
    """Chỗ hỏng số 1 — canh cả hai chiều."""
    ma = _ma(KHOI)
    assert "<BieuDoBonMoc" not in ma and "function BieuDoBonMoc" not in ma, (
        "Hình bốn mốc trở lại màn hình Chủ tịch — đúng cái khung rỗng anh Tuấn chụp và bảo bỏ "
        "ngày 17/9/2026, và đúng cái trùng anh chỉ ra ngày 18/9."
    )
    assert "<details" not in ma, (
        "Nếp gấp 'Bảng bốn mốc' sống lại. Từ TC-63 bảng không còn ở màn hình này để mà gấp."
    )
    # Cửa dẫn sang phải còn — bỏ bảng mà bỏ luôn lối đi tới nó là giấu mất cả hai.
    assert 'href="/dong-tien"' in ma, "Mất cửa 'Cấu trúc chi tiết dòng tiền →'."


def test_hinh_bon_moc_ve_dung_mot_cho_va_cho_ay_la_man_hinh_dong_tien():
    """Bỏ khỏi màn hình Chủ tịch KHÔNG có nghĩa là bỏ khỏi hệ thống.

    `/dong-tien` trước TC-63 không có hình nào vẽ bốn mốc — đó chính là lý do TC-61 chưa xoá được.
    Nay có, và có đúng một chỗ.
    """
    bm = _ma(BANG)
    assert bm.count("function BieuDoBonMoc") == 1, "Hình bốn mốc phải được khai ĐÚNG MỘT chỗ."
    assert bm.count("<BieuDoBonMoc") == 1, "Chỉ được vẽ ở MỘT chỗ."
    trang = _ma(TRANG_DT)
    assert "<BangBonMoc" in trang, (
        "Khối bốn mốc chưa được gắn lên màn hình /dong-tien — rời màn hình Chủ tịch mà không tới "
        "nơi nào là xoá mất một năng lực, không phải chuyển nó."
    )


def test_hinh_dung_truoc_bang():
    """Hình trả lời 'bốn mốc đi lên hay đi xuống', bảng trả lời 'dòng nào làm nên điều đó'.

    Đảo thứ tự là bắt người đọc đi qua mười bốn dòng số trước khi thấy hình dáng của chúng — cùng
    lý lẽ đã dùng khi xếp hình trước chú thích ở TC-59.
    """
    ma = _ma(BANG)
    assert ma.index("<BieuDoBonMoc") < ma.index("<table>")


def test_hai_nut_di_theo_bang_chu_khong_bi_bo_lai():
    """Chỗ hỏng số 2 — hai cái nút mà TC-61 đã lo sẽ mất.

    Nút đổi kiểu xem (luỹ kế ↔ trong từng khoảng) và nút Xuất Excel KHÔNG có bản sao ở đâu khác
    trong hệ thống. Chúng điều khiển chính cái bảng này, nên chúng phải ở cùng tệp với nó.
    """
    bm = _ma(BANG)
    assert "dt-kieu" in bm and "Trong từng khoảng" in bm, "Mất nút đổi kiểu xem bốn mốc."
    assert "taiTep(" in bm and "Xuất Excel" in bm, "Mất nút Xuất Excel."


def test_cau_doc_ho_van_con_va_van_di_cung_hinh():
    """Chỗ hỏng số 2 — canh cái ràng buộc, không canh cái tên.

    `docHoDongTien` là câu đọc hộ mà TC-38 và TC-40 canh. Nó chỉ có một người dùng: hình bốn mốc.
    Xoá hình mà quên nó thì nó thành hàm mồ côi; xoá cả hai thì hai phép thử kia đỏ, và đó chính là
    cái chuông phải reo — không được tắt chuông bằng cách sửa phép thử.
    """
    ma = _ma(BANG)
    assert "function docHoDongTien" in ma
    i = ma.index("function BieuDoBonMoc")
    than = ma[i:ma.index("\n}", ma.index("return (", i))]
    assert "docHoDongTien(" in than, "Câu đọc hộ phải được gọi từ chính hình nó đọc hộ."
    assert "function docHoDongTien" not in _ma(KHOI), (
        "Câu đọc hộ còn nằm lại ở màn hình Chủ tịch — một hàm không ai gọi là cách vòng sau dựng "
        "lại cả khối mà không biết vì sao nó từng bị bỏ (bài học `O` ở TC-57)."
    )


def test_man_hinh_dong_tien_chi_con_MOT_bang_bon_moc():
    """Chuyển cái trùng đi nơi khác mà để lại bản cũ thì cái trùng vẫn còn, chỉ đổi chỗ.

    `/dong-tien` trước TC-63 tự dựng một bảng bốn mốc từ `/dong-tien/bang`. Khối chuyển sang dựng
    từ `/dong-tien/khung`, mà `khung_dong_tien.ghep()` nhận CHÍNH `bang` ấy làm đầu vào rồi bổ sung
    trạng thái nguồn số, số theo từng khoảng và dòng đáy — tức nó là tập CHA. Để cả hai là bày hai
    bảng cùng tên, cùng bốn cột, cùng một dòng tiền, cạnh nhau trên một màn hình.
    """
    trang = _ma(TRANG_DT)
    assert trang.count("Bảng bốn mốc") == 0, (
        "Màn hình /dong-tien vẫn tự dựng một bảng bốn mốc riêng. Bảng ấy do <BangBonMoc> lo, và "
        "hai bảng cùng tên cạnh nhau là đúng cái trùng anh Tuấn bảo bỏ ngày 18/9/2026."
    )
    assert "<BangBonMoc" in trang


def test_bon_o_dau_trang_va_o_canh_bao_van_o_lai_voi_goi_bang():
    """Gói `khung` KHÔNG trả bốn ô đầu trang và danh sách dòng chưa có nguồn — chúng thuộc gói
    `bang`. Thay bảng mà gỡ luôn lời gọi `bang` là mất cả hai, mà mất chúng thì không lỗi nào báo.
    """
    trang = _ma(TRANG_DT)
    assert "/dong-tien/bang/" in trang, "Mất lời gọi gói `bang` — bốn ô đầu trang lấy từ đó."
    assert "tien_kha_dung_dau_ky" in trang, "Mất ô tiền khả dụng đầu kỳ."
    assert "chua_co_nguon" in trang, "Mất ô cảnh báo 'còn N dòng chưa có nguồn'."
