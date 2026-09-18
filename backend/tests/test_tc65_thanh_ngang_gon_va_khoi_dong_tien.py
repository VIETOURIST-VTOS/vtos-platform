# -*- coding: utf-8 -*-
"""TC-65 · THANH NGANG NUỐT LUÔN HÀNG VIỆC CHỜ QUYẾT · CỬA LÊN CẠNH TÊN HÌNH · HÀNG ĐÁY IM KHI YÊN.

    "hình 1 gom lại thành 1 thanh ngang, bỏ chữ chờ chủ tịch quyết, bỏ Vietourist cty mẹ;
     hình 2 đưa chữ cấu trúc chi tiết dòng tiền lên kề bên chữ dự báo dòng tiền 13 tuần, và
     lấp khoảng hở ở hình 2 cho đẹp; hình 3 xoá hoặc ẩn khỏi màn hình chủ tịch"
                                                                    — anh Tuấn, 18/9/2026

══════════════════════════════════════════════════════════════════════════════════════════════
BA VIỆC, VÀ MỘT LUẬT CHUNG CHO CẢ BA
══════════════════════════════════════════════════════════════════════════════════════════════
Cả ba đều là BỚT CHỮ, không phải bớt câu trả lời. Mỗi chỗ bỏ đi một dòng chữ thì thứ nó nói phải
còn ở đâu đó — trên nhãn rê chuột, trong chính cái hình, hoặc ở màn hình mà cửa dẫn sang. Phép thử
này canh đúng điều ấy: KHÔNG canh "chữ đã biến mất", mà canh "chữ biến mất VÀ câu trả lời còn".

BỐN CHỖ DỄ HỎNG
1. HÀNG VIỆC CHỜ QUYẾT BIẾN MẤT THEO. Bỏ khối là dễ; bỏ luôn danh sách `d.approvals` mà không ai
   thấy cũng dễ y như vậy, vì màn hình lúc ấy trông sạch sẽ và không lỗi nào báo. Đây là việc
   DUY NHẤT trên màn hình mà Chủ tịch phải bấm.
2. AI ĐÓ `slice` DANH SÁCH cho gọn thanh. Luật 13/9/2026 cấm cắt bớt hồ sơ chờ quyết: hồ sơ thứ
   sáu nằm ngoài tầm mắt người duy nhất được quyết nó.
3. HÀNG ĐÁY DỰ BÁO BỊ XOÁ HẲN. Ở trạng thái xanh nó thừa; ở trạng thái đỏ ("ÂM — không đủ tiền
   trả") nó là dòng quan trọng nhất cả màn hình. Xoá hẳn là bỏ mất đúng cái cảnh báo ấy.
4. CỬA SANG /dong-tien BỊ BỎ LUÔN khi dọn đoạn văn dưới đáy khối. Bảng bốn mốc đã sang đó từ
   TC-63; bỏ cửa là bỏ luôn lối đi tới nó.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DAU = GOC / "web" / "components" / "DauManHinh01.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
DT = GOC / "web" / "components" / "KhoiDongTien.tsx"
BD = GOC / "web" / "components" / "BieuDo.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _ma(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


def _than(ma: str, ten: str) -> str:
    i = ma.index(f"export function {ten}")
    j = ma.find("export function", i + 10)
    return ma[i:j if j > 0 else len(ma)]


def _css() -> str:
    return re.sub(r"/\*(?:.|\n)*?\*/", " ", CSS.read_text(encoding="utf-8"))


# ───────────── 1 · VIỆC CHỜ QUYẾT VẪN TRÊN MÀN HÌNH, CHỈ MẤT KHUNG ─────────────

def test_hang_viec_cho_quyet_van_con_va_di_du_khong_cat():
    """Chỗ hỏng số 1 và số 2 — canh cùng một chỗ vì chúng hỏng cùng một lúc.

    Bỏ khối riêng là điều anh Tuấn chốt. Bỏ luôn DANH SÁCH thì màn hình vẫn trông sạch sẽ, không
    lỗi nào báo, và việc duy nhất Chủ tịch phải bấm biến mất. Nên canh cả ba vế: thanh nhận được
    danh sách, thanh bày ra từng mục, và thanh không cắt bớt mục nào.
    """
    trang = _ma(TRANG)
    assert "quyet_dinh={d.approvals" in trang, (
        "Thanh ngang không nhận danh sách hồ sơ chờ quyết — việc duy nhất Chủ tịch phải bấm đã "
        "biến mất khỏi màn hình."
    )
    than = _than(_ma(DAU), "TieuDe")
    assert "cho.map(" in than, "Thanh ngang không bày danh sách hồ sơ chờ quyết."
    assert "mh01-qd-nut" in than, "Mỗi hồ sơ phải là một nút bấm được, không phải một dòng chữ."
    assert "slice(" not in than, (
        "Danh sách hồ sơ chờ quyết đang bị cắt bớt. Luật 13/9/2026: hồ sơ thứ sáu nằm ngoài tầm "
        "mắt người DUY NHẤT được quyết nó, mà thứ tự ưu tiên thì máy chủ chưa xếp."
    )


def test_khong_con_khoi_rieng_va_khong_con_ba_dong_chu_gioi_thieu():
    """Vế ngược của luật trên: dựng lại khối riêng là quay về đúng cái anh Tuấn bảo gộp."""
    dau = _ma(DAU)
    assert "function KhoiQuyetDinh" not in dau, "`KhoiQuyetDinh` sống lại thành khối riêng."
    assert "<KhoiQuyetDinh" not in _ma(TRANG), "Khối riêng được lắp lại trên trang."
    assert "hồ sơ đang chờ" not in dau, (
        "Thẻ nhãn đếm hồ sơ sống lại — nó đếm đúng số nút đứng ngay cạnh nó."
    )
    assert "Cần Chủ tịch quyết định" not in dau and "Cần Tổng giám đốc quyết định" not in dau, (
        "Tiêu đề khối sống lại — nó nói lại điều tên trang đã nói."
    )
    css = _css()
    for lop in (".mh01-qd{", ".mh01-qd-ds"):
        assert lop not in css, f"Kiểu {lop} còn trong globals.css nhưng không ai dùng (bài học TC-60)."


def test_pham_vi_khong_mat_khoi_he_thong_chi_xuong_cho_re_chuot():
    """"bỏ Vietourist cty mẹ" — bỏ khỏi THANH, không bỏ khỏi màn hình.

    TC-55 đặt ra luật "phạm vi là một câu trả lời, không phải một ô chọn", vì hai người mở cùng
    một trang mà mỗi người đang xem một pháp nhân khác nhau rồi cùng bàn về "con số đó" là kiểu sai
    không ai phát hiện ra trong phòng họp. Luật ấy còn nguyên; chỉ chỗ đứng đổi.
    """
    than = _than(_ma(DAU), "TieuDe")
    assert 'title="Phạm vi: Vietourist — công ty mẹ"' in than, (
        "Mất câu trả lời phạm vi. Nó phải bám vào tên trang, đọc được khi rê chuột."
    )
    assert "Báo cáo tài chính hợp nhất" not in than, (
        "Chưa được dẫn sang màn hình hợp nhất: nó CHƯA DỰNG (bài học 13/9)."
    )


# ───────────── 2 · CỬA ĐỨNG CẠNH TÊN HÌNH, KHÔNG NẰM MỘT MÌNH DƯỚI ĐÁY ─────────────

def test_cua_sang_dong_tien_dung_canh_ten_hinh():
    """Chỗ hỏng số 4 — và "lấp khoảng hở" chính là hệ quả của việc dời nó lên.

    Đoạn văn cũ nằm một mình dưới đáy khối, cách khung biểu đồ một dải trống rộng gần cả màn hình.
    Anh Tuấn chụp đúng dải trống ấy. Dời cửa lên cạnh tên hình thì dải trống không còn chỗ tồn tại
    — nên phép thử canh CẢ HAI: cửa còn, và đoạn văn cũ đi.
    """
    ma = _ma(DT)
    assert 'ben_ten={<Link className="the-cua" href="/dong-tien">' in ma, (
        "Cửa 'Cấu trúc chi tiết dòng tiền →' phải đứng cạnh tên hình 13 tuần, qua `ben_ten`."
    )
    assert "dt-nut-chi-tiet" not in ma, (
        "Đoạn văn một dòng dưới đáy khối sống lại — chính nó tạo ra dải trống anh Tuấn chụp."
    )
    assert "dt-nut-chi-tiet" not in _css(), "Kiểu của đoạn văn ấy còn trong CSS nhưng không ai dùng."


def test_khung_bieu_do_co_cho_cho_cua_va_cho_ay_dung_truoc_chu_giai():
    """Cửa phải đứng GIỮA tên hình và chú giải.

    Chú giải mang `margin-left:auto` nên nó luôn bị đẩy sang mép phải; đặt cửa SAU chú giải là đẩy
    cửa ra tận mép, cách tên hình cả một khung — đúng cái vừa sửa, chỉ theo chiều ngang.
    """
    ma = _ma(BD)
    i = ma.index("<figcaption className=\"bd-dau\">")
    khoi = ma[i:ma.index("</figcaption>", i)]
    assert "{ben_ten}" in khoi, "`KhungBieuDo` chưa có chỗ cho cửa cạnh tên hình."
    assert khoi.index("{ben_ten}") < khoi.index("{chuGiai}"), (
        "Cửa phải đứng TRƯỚC chú giải; đứng sau là nó bị đẩy ra tận mép phải."
    )
    assert "ben_ten={ben_ten}" in ma, "`BieuDoDuong` không chuyển tiếp `ben_ten` xuống khung."


# ───────────── 3 · HÀNG ĐÁY DỰ BÁO: YÊN THÌ IM, NGUY THÌ NÓI ─────────────

def test_hang_day_du_bao_chi_hien_khi_co_chuyen():
    """Chỗ hỏng số 3 — cái phép thử này canh là CẢNH BÁO, không phải một dòng chữ.

    Anh Tuấn chụp hàng này ở trạng thái XANH ("Trên ngưỡng dự phòng") và bảo xoá hoặc ẩn. Ở trạng
    thái xanh nó nói lại đúng điều hình ngay trên đã vẽ. Ở trạng thái đỏ nó nói tuần nào hết tiền
    và thiếu bao nhiêu — không có chỗ nào khác trên màn hình nói điều đó thành chữ.

    Nên: ẩn CÓ ĐIỀU KIỆN. Xoá hẳn hàm là bỏ mất cảnh báo; bỏ điều kiện là trả lại dòng chữ "mọi
    thứ ổn" in ra mỗi ngày, thứ dạy người ta thôi đọc chỗ ấy.
    """
    ma = _ma(DT)
    assert "function DayDuBao" in ma, (
        "`DayDuBao` bị xoá hẳn — lúc dòng tiền âm thì không còn gì nói cho Chủ tịch biết."
    )
    assert "<DayDuBao" in ma, "`DayDuBao` không được gọi — hàm mồ côi, cảnh báo không bao giờ hiện."
    than = ma[ma.index("function DayDuBao"):]
    than = than[:than.index("\n}", than.index("return ("))]
    assert "if (!d.am && !d.duoi_nguong) return null;" in than, (
        "Thiếu điều kiện ẩn ở trạng thái yên. Không có nó thì hàng 'Trên ngưỡng dự phòng' lại in "
        "ra mỗi ngày — đúng cái anh Tuấn chụp và bảo bỏ."
    )
    # Hai mức nguy hiểm phải còn đủ chữ, không được gộp làm một.
    assert "ÂM — không đủ tiền trả" in than and "Dưới ngưỡng dự phòng" in than, (
        "Gộp hai mức nguy thành một thì một công ty sắp mất khả năng chi trả trông y hệt một công "
        "ty mỏng đệm — hai tình huống đòi hai hành động khác hẳn nhau."
    )


def test_cua_nhap_du_bao_khong_mat_theo_hang_day():
    """Hàng đáy mang theo cửa nhập dự báo 13 tuần. Ẩn hàng ở trạng thái xanh mà cửa ấy không có bản
    sao nào thì ranh giới 09/9 bị thủng: một con số trên màn hình mà không có cửa cho người nhập.

    Bản sao có sẵn: chính hình 13 tuần đã mang `cua` của nó.
    """
    ma = _ma(DT)
    hinh = ma[ma.index("function Hinh13Tuan"):]
    hinh = hinh[:hinh.index("\n}", hinh.index("return ("))]
    assert 'cua="/finance?tab=forecast"' in hinh, (
        "Hình 13 tuần phải mang cửa nhập dự báo — đó là bản sao giữ ranh giới 09/9 khi hàng đáy ẩn."
    )
