# -*- coding: utf-8 -*-
"""TC-24 · Mốc hoà vốn bằng 0 không được đọc thành "đã đạt mốc" (13/9/2026).

LỖI ĐÃ THẤY TRÊN TRANG THẬT. Bảng Điều hành in mỗi chuyến một nhãn trạng thái:

    {r.below ? <Tag cls="red">dưới hòa vốn</Tag> : <Tag cls="ok">ok</Tag>}

`r.below` do máy chủ tính là `booked < breakeven`. Nhưng hôm nay máy chủ trả `breakeven = 0` cho
gần như mọi chuyến, vì chưa ai nhập điểm hoà vốn. Với 0 thì `booked < 0` luôn sai, nên `below` luôn
sai, nên NHÁNH XANH luôn chạy: một chuyến 0 khách khởi hành ngày mai vẫn hiện "0/0 khách · ok".

Đây đúng là điều bản vẽ V1.4 cấm bằng chữ: "không mặc định chuyến đã sẵn sàng". Và nó là một ca
khác của luật RỖNG KHÁC KHÔNG: chỗ này không phải "đã đếm và bằng không", mà là "chưa ai nhập" —
đọc nhầm cái sau thành cái trước rồi dán nhãn xanh lên là cách tệ nhất, vì nhãn xanh khiến người
đọc thôi không hỏi nữa.

Cách sửa: chưa có mốc thì nói CHƯA CÓ MỐC, không xanh cũng không đỏ.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
# TC-40 (15/9/2026): khối Điều hành đã rời màn hình 01 — anh Tuấn chốt bỏ, vì nó cao 3.693px để
# trình 92 chuyến mà bốn trên bảy cột ghi "chưa nối". Mã KHÔNG xoá: nó tách ra thành khối riêng và
# mang theo nguyên bốn luật mà bộ kiểm này canh. Luật không đổi, chỉ đổi tệp chứa nó.
TRANG = GOC / "web" / "components" / "KhoiDieuHanh.tsx"


def _bo_chu_thich(s: str) -> str:
    """Bỏ chú thích trước khi soi. Chú thích ở đây GIẢI THÍCH lỗi cũ nên có chứa nguyên văn câu
    lệnh sai; không bỏ đi thì phép thử bắt nhầm chính lời giải thích của mình."""
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


def _ma() -> str:
    assert TRANG.exists(), "Thiếu web/app/page.tsx"
    return _bo_chu_thich(TRANG.read_text(encoding="utf-8"))


def test_khong_con_nhanh_hai_ngach():
    """Ô số khách không còn đi thẳng từ số vào nhánh đỏ/xanh.

    Nhánh `r.below ? đỏ : xanh` tự nó vẫn đúng và vẫn được giữ — nó là hai ngách TRONG của ba
    ngách. Cái phải biến mất là ô đi THẲNG từ con số vào nhánh ấy mà không xét mốc rỗng trước.
    Vì vậy phép thử soi đúng hình dạng cũ của cả ô, không soi riêng nhánh."""
    ma = _ma()
    assert "{r.booked}/{r.breakeven} khách {r.below" not in ma, (
        "Ô số khách vẫn đi thẳng vào nhánh đỏ/xanh: mốc hoà vốn bằng 0 sẽ rơi vào ngách xanh."
    )


def test_co_ngach_chua_co_moc():
    """Phải có ngách thứ ba, và nó phải nói rõ là CHƯA CÓ MỐC."""
    ma = _ma()
    assert "chưa có mốc hoà vốn" in ma, (
        "Thiếu nhãn 'chưa có mốc hoà vốn' — người đọc không biết ô này chưa ai nhập."
    )
    assert "!r.breakeven" in ma, (
        "Thiếu phép kiểm mốc hoà vốn rỗng; phải xét trước khi so booked với breakeven."
    )


def test_ngach_rong_dung_truoc_ngach_do_xanh():
    """Thứ tự phải là: rỗng trước, rồi mới đỏ/xanh. Đảo lại thì ngách rỗng không bao giờ chạy."""
    ma = _ma()
    i_rong = ma.find("!r.breakeven")
    i_do = ma.find("dưới hòa vốn")
    assert i_rong != -1 and i_do != -1, "Thiếu một trong hai ngách."
    assert i_rong < i_do, (
        "Phép kiểm mốc rỗng phải đứng TRƯỚC nhánh đỏ/xanh, nếu không nó không bao giờ tới lượt."
    )


def test_khong_in_so_khong_thay_cho_moc_trong():
    """Cột số khách không được in '0' ở chỗ mốc hoà vốn khi chưa có mốc."""
    ma = _ma()
    assert "{r.breakeven || \"—\"}" in ma, (
        "Mốc hoà vốn rỗng vẫn đang in ra số 0; phải in dấu gạch như mọi ô chưa có nguồn khác."
    )


def test_van_con_canh_bao_khong_mac_dinh_san_sang():
    """Câu cảnh báo của bản vẽ phải còn nguyên — nó là lý do tồn tại của ba ngách trên."""
    ma = _ma()
    assert "không</b> mặc định chuyến đã sẵn sàng" in ma or "mặc định chuyến đã sẵn sàng" in ma, (
        "Mất câu 'không mặc định chuyến đã sẵn sàng' của bản vẽ V1.4."
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════
# QUÉT MÀU VIẾT CỨNG TRÊN CÁC MÀN HÌNH KHÁC
#
# Nền tảng chuyển sang NỀN TỐI ngày 13/9. Sáu màn hình dưới đây mang riêng một khối <style jsx>
# với bảng màu SÁNG viết cứng (#0f172a, #cbd5e1, #f8fafc…). Trên nền tối chúng thành sáu mảng
# giấy trắng giữa trang, và ô nhập thì chữ đen trên nền trắng trong khi cả trang màu tối.
#
# Hai chỗ nữa nặng hơn, vì chúng không chỉ lệch màu mà KHÔNG ĐỌC ĐƯỢC:
#   · nút "Cài ngay" và nút "Thử lại" đặt chữ trắng lên `--vtos-navy`. Ở bản sáng biến ấy là navy
#     đậm #14538D nên chữ trắng đạt 8,9. Bản tối đổi nó thành màu CHỮ #6FA8F0 — chữ trắng còn 2,46.
#   · số lệch ở màn Kế toán tô "#b00" (đỏ sẫm) trên nền trang #091624: 2,70.
# Cả hai đều dưới ngưỡng 4,5 của WCAG AA. Đây chính là cái giá của việc một biến gánh hai vai;
# tokens.css đã ghi rõ MỘT BIẾN MỘT VAI, và hai chỗ này là hai chỗ còn sót.
# ═════════════════════════════════════════════════════════════════════════════════════════════

MAN_HINH_STYLE_JSX = [
    "web/app/bao-gia/page.tsx", "web/app/bang-gia/page.tsx", "web/app/ket-so/page.tsx",
    "web/app/doc-chung-tu/page.tsx", "web/app/hop-dong-khach/page.tsx",
    "web/app/ra-soat-cot-tien/page.tsx",
]

# #fff được phép: nó là màu trắng thật, dùng làm chữ trên nền đặc, và tokens.css cũng khai
# --vtos-text-on-navy là #FFFFFF. Ngoài nó ra, mọi mã màu trong khối <style jsx> đều là màu sáng
# của bảng Tailwind lọt vào từ thời bản sáng.
CHO_PHEP = {"#fff", "#ffffff"}


def _khoi_style(duong_dan: str) -> str:
    p = GOC / duong_dan
    assert p.exists(), f"Thiếu {duong_dan}"
    s = p.read_text(encoding="utf-8")
    i = s.find("<style jsx>")
    assert i != -1, f"{duong_dan}: không còn khối <style jsx>"
    j = s.find("</style>", i)
    return s[i:j]


def test_sau_man_hinh_khong_con_ma_mau_viet_cung():
    sot = {}
    for t in MAN_HINH_STYLE_JSX:
        ma_mau = [h for h in re.findall(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", _khoi_style(t))
                  if h.lower() not in CHO_PHEP]
        if ma_mau:
            sot[t] = ma_mau
    assert not sot, (
        "Còn mã màu viết cứng trong khối <style jsx>; trên nền tối chúng thành mảng sáng: "
        + "; ".join(f"{k}: {v}" for k, v in sot.items())
    )


def test_sau_man_hinh_dung_bien_bo_nhan_dien():
    """Không chỉ 'không còn hex' — phải THẬT SỰ dùng biến, chứ không phải xoá màu đi cho qua."""
    for t in MAN_HINH_STYLE_JSX:
        khoi = _khoi_style(t)
        assert "var(--vtos-" in khoi, f"{t}: khối <style jsx> không dùng biến bộ nhận diện nào."


def test_nut_khong_dat_chu_trang_len_vtos_navy():
    """--vtos-navy là màu CHỮ trên nền tối. Đặt chữ trắng lên nó là 2,46 lần — không đọc được."""
    for t in ["web/components/CaiDatApp.tsx", "web/app/offline/page.tsx"]:
        s = _bo_chu_thich((GOC / t).read_text(encoding="utf-8"))
        assert "background: \"var(--vtos-navy" not in s, (
            f"{t}: vẫn tô nền bằng --vtos-navy; nền nút phải là --vtos-sky, nền trang là --vtos-nav-bg."
        )


def test_khong_con_nen_trang_cung_tren_nen_toi():
    for t in ["web/components/CaiDatApp.tsx", "web/app/offline/page.tsx"]:
        s = _bo_chu_thich((GOC / t).read_text(encoding="utf-8"))
        assert "background: \"#FFFFFF\"" not in s, (
            f"{t}: còn một mảng nền trắng viết cứng giữa nền tối."
        )


def test_so_lech_ke_toan_doc_duoc_tren_nen_toi():
    s = _bo_chu_thich((GOC / "web/app/accounting/page.tsx").read_text(encoding="utf-8"))
    assert '"#b00"' not in s, "Số lệch vẫn tô #b00 — trên nền trang chỉ đạt 2,70 lần."
    assert "var(--vtos-danger)" in s, "Số lệch phải lấy màu đỏ của bộ nhận diện."


def test_khong_con_ten_mau_cua_trinh_duyet():
    """`orange` là màu của trình duyệt, không phải màu của Vietourist — nó không đổi theo bộ."""
    s = _bo_chu_thich((GOC / "web/app/inbox/page.tsx").read_text(encoding="utf-8"))
    assert "solid orange" not in s, "Vạch 'chưa trả lời' còn dùng tên màu orange của trình duyệt."
    s2 = _bo_chu_thich((GOC / "web/app/tours/[id]/page.tsx").read_text(encoding="utf-8"))
    assert '"#888"' not in s2, "Vạch nguồn Vietrip còn tô #888 viết cứng."


# ═════════════════════════════════════════════════════════════════════════════════════════════
# BA NƠI KHAI MÀU MỞ APP PHẢI KHỚP NHAU
#
# Khi bấm biểu tượng VTOS trên điện thoại, người dùng thấy ba thứ nối nhau trong chưa đầy một giây:
#   1. ảnh chờ  /public/splash/*.png      (iOS dùng)
#   2. background_color trong manifest    (Android dựng màn hình chờ từ đây)
#   3. themeColor trong layout.tsx        (thanh trạng thái của hệ điều hành)
# Ba nơi mang ba màu khác nhau thì mở app loé một nhịp navy sáng rồi mới vào nền tối — trông như
# app lỗi. Nên phép thử này canh CẢ BA CÙNG MỘT MÃ, và sẽ gãy nếu ai đó chỉ đổi một nơi.
# ═════════════════════════════════════════════════════════════════════════════════════════════

NEN_MO_APP = "#14538D"   # --vtos-nav-bg (logo v2 · 07/11/2026; trước là #10273E)


def test_ba_noi_khai_mau_mo_app_khop_nhau():
    import json
    mf = json.loads((GOC / "web/public/manifest.json").read_text(encoding="utf-8"))
    assert mf["background_color"].upper() == NEN_MO_APP, (
        f"manifest background_color = {mf['background_color']}, phải là {NEN_MO_APP}."
    )
    assert mf["theme_color"].upper() == NEN_MO_APP, (
        f"manifest theme_color = {mf['theme_color']}, phải là {NEN_MO_APP}."
    )
    lay = _bo_chu_thich((GOC / "web/app/layout.tsx").read_text(encoding="utf-8"))
    assert f'themeColor: "{NEN_MO_APP}"' in lay, (
        f"layout.tsx chưa đặt themeColor {NEN_MO_APP} — thanh trạng thái sẽ lệch màu thanh ngang."
    )


def test_anh_cho_da_doi_sang_nen_toi():
    """Đủ 16 ảnh và điểm ảnh góc của mỗi ảnh phải đúng nền thanh ngang (navy #14538D từ logo v2)."""
    thu_muc = GOC / "web/public/splash"
    anh = sorted(thu_muc.glob("splash-*.png"))
    assert len(anh) == 16, f"Phải đủ 16 ảnh chờ, đang có {len(anh)}."
    try:
        from PIL import Image
    except ImportError:
        return  # máy chạy kiểm không có Pillow thì bỏ qua phần đo điểm ảnh
    mong_doi = (0x14, 0x53, 0x8D)
    lech = {}
    for p in anh:
        goc = Image.open(p).convert("RGB").getpixel((2, 2))
        if goc != mong_doi:
            lech[p.name] = goc
    assert not lech, f"Ảnh chờ còn nền cũ: {lech} (phải là {mong_doi} = {NEN_MO_APP})."
