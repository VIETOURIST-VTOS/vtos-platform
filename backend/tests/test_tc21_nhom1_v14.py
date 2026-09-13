# -*- coding: utf-8 -*-
"""TC-21 · Nhóm 1 của bảng đối chiếu với bản vẽ V1.4 (13/9/2026).

Năm việc sửa được ngay ở lớp giao diện, không cần bảng mới ở máy chủ:

  1. Chuông chặn trần 99+ thay cho con số 1944.
  2. Ô tài khoản không in chức danh hai lần.
  3. Khối cảnh báo mang tên "Rủi ro & việc cần theo dõi".
  4. Mã máy như sale_tra_loi_cham đổi thành câu tiếng Việt; mã lạ giữ nguyên mã.
  5. Dòng phụ ba thẻ ghi đúng thứ bản vẽ đòi, hoặc ghi rõ chỗ còn thiếu.

Cộng một việc đính chính: câu chỉ dẫn phạm vi trên màn hình 01 từng chỉ vào một ô KHÔNG CÓ.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
SHELL = GOC / "web" / "components" / "Shell.tsx"
KHOI = GOC / "web" / "components" / "KhoiTonDong.tsx"
DAU = GOC / "web" / "components" / "DauManHinh01.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _the(nguon: str, nhan: str) -> str:
    i = nguon.find(f'nhan: "{nhan}"')
    assert i > 0, f'Không tìm thấy thẻ "{nhan}" trong màn hình 01'
    return nguon[i:nguon.find("},", i) + 2]


# ------------------------------------------------------------------ 1. Chuông

def test_chuong_chan_tran_99_cong():
    """Bốn chữ số trên một cái chuông thì vừa vỡ khung vừa vô nghĩa (bản vẽ V1.4: tối đa 99+)."""
    nguon = _doc(SHELL)
    assert 'alerts > 99 ? "99+" : alerts' in nguon, (
        "Chuông phải chặn trần 99+. Bản chạy thật ngày 13/9 đang hiện 1944."
    )


def test_chuong_giu_so_that_cho_trinh_doc_man_hinh():
    """Chặn trần là đổi cách HIỆN, không được làm mất con số thật khỏi nhãn trợ năng."""
    nguon = _doc(SHELL)
    i = nguon.find('aria-label={`Cảnh báo nghiệp vụ')
    assert i > 0, "Nhãn trợ năng của chuông phải nói rõ đây là cảnh báo nghiệp vụ"
    assert "${alerts}" in nguon[i:i + 200], (
        "Nhãn trợ năng phải đọc con số THẬT, không đọc chuỗi 99+ đã chặn trần."
    )


# --------------------------------------------------------------- 2. Tài khoản

def test_o_tai_khoan_khong_in_chuc_danh_hai_lan():
    """Bản chạy thật đang hiện "Chủ tịch HĐQT · Chủ tịch HĐQT" – bản vẽ V1.4 nêu đích danh lỗi này."""
    nguon = _doc(SHELL)
    assert "function tenVaChuc" in nguon, "Thiếu hàm dựng ô tài khoản"
    assert "{tenVaChuc(user)}" in nguon, "Ô tài khoản phải dùng tenVaChuc"
    assert "{user?.full_name} · <b>{user?.role_name}</b>" not in nguon, (
        "Vẫn đang in thẳng full_name · role_name. Tài khoản chưa đặt tên thật thì hai trường bằng "
        "nhau và câu này in ra hai bản của cùng một chuỗi."
    )
    i = nguon.find("function tenVaChuc")
    than = nguon[i:i + 700]
    assert "toLowerCase() === chuc.toLowerCase()" in than, (
        "Phải so sánh không phân biệt hoa thường: tên và chức danh bằng nhau thì chỉ in một lần."
    )


# ------------------------------------------------------------ 3+4. Khối rủi ro

def test_ten_khoi_theo_ban_ve_v14():
    nguon = _doc(KHOI)
    assert "Rủi ro &amp; việc cần theo dõi" in nguon or "Rủi ro & việc cần theo dõi" in nguon, (
        'Bản vẽ V1.4 chốt tên khối là "Rủi ro & việc cần theo dõi", không phải "Cảnh báo từ robot" '
        'cũng không phải "Tồn đọng cần xử lý".'
    )


def test_ma_may_doi_thanh_cau_tieng_viet():
    """Bản vẽ nêu đích danh sale_tra_loi_cham."""
    nguon = _doc(KHOI)
    assert "const TEN_LOAI" in nguon, "Thiếu bảng dịch mã cảnh báo sang tiếng Việt"
    for ma in ("sale_tra_loi_cham", "bc_ngay_2", "cham_soc_qua_han", "qua_han_qt"):
        assert f"{ma}:" in nguon, (
            f"Thiếu câu tiếng Việt cho mã {ma}. Bốn mã này là toàn bộ mã máy chủ đang phát, "
            "đọc từ /api/v1/alerts ngày 13/9/2026."
        )
    assert "tenLoai(n.kind) || n.kind" in nguon, (
        "Mã LẠ phải giữ nguyên mã máy. Bịa một câu chung chung kiểu 'Cảnh báo khác' thì phần còn "
        "thiếu biến mất khỏi tầm mắt và không ai đi khai nữa."
    )


def test_bang_dich_khong_gan_bo_phan_va_khong_doi_muc_nang():
    """Bảng dịch chỉ đổi CÁCH GỌI. Gán bộ phận là tuyên bố nghiệp vụ, phải do máy chủ khai."""
    nguon = _doc(KHOI)
    i = nguon.find("const TEN_LOAI")
    bang = nguon[i:nguon.find("};", i)]
    for cam in ("Kế toán", "Kinh doanh", "Điều hành", "Marketing", "red", "warn"):
        assert cam not in bang, (
            f"Bảng dịch mã đang mang thêm '{cam}'. Nó chỉ được đổi TÊN của loại cảnh báo, không "
            "gán bộ phận và không đổi mức nặng."
        )


# -------------------------------------------------------- 5. Dòng phụ tám thẻ

def test_dong_phu_khong_bia_so_so_sanh():
    """Bản vẽ đòi so kế hoạch và kỳ trước; máy chủ chưa có. Ghi ra chỗ thiếu, không bịa tỷ lệ."""
    the = _the(_doc(TRANG), "Doanh thu tháng")
    assert "chưa có kế hoạch tháng và kỳ trước" in the, (
        "Thẻ Doanh thu phải nói rõ chưa có nguồn so sánh, kèm bộ phận phụ trách.\n" + the
    )
    assert "%" not in the, (
        "Không được in tỷ lệ phần trăm khi chưa có kế hoạch và kỳ trước – một mũi tên tăng giảm "
        "dựng từ số không có thật thì người đọc hiểu là kết quả, không hiểu là chỗ trống."
    )


def test_the_tour_dang_ban_noi_ro_chua_tinh_duoc_cho_con():
    the = _the(_doc(TRANG), "Tour đang bán")
    assert "chỗ còn" in the and "sức chứa" in the, (
        'Bản vẽ chốt dòng phụ là "Khách đã chốt / chỗ còn". Chưa có sức chứa từng chuyến thì phải '
        "ghi ra, không thay bằng một con số khác.\n" + the
    )


def test_the_ton_dong_noi_ro_hai_chi_so_con_thieu():
    the = _the(_doc(TRANG), "Tồn đọng cần xử lý")
    assert "chưa tách được hồ sơ quá hạn" in the and "chưa có người nhận" in the, (
        "Bản vẽ chốt ba chỉ số: hồ sơ quá hạn · nghiêm trọng · chưa có người nhận. Máy chủ mới có "
        "cái giữa – hai cái còn lại phải được nói ra.\n" + the
    )


# ------------------------------------------ Đính chính: câu chỉ dẫn phạm vi

def test_khong_chi_nguoi_dung_bam_vao_o_khong_ton_tai():
    """components/ChonDonVi.tsx trả null khi máy chủ chưa mở GET /pham-vi/don-vi – hôm nay là chưa.

    Bảo người ta bấm vào một ô không có là kiểu sai khó chịu nhất: họ đi tìm, không thấy, rồi cho
    rằng mình nhìn sót chứ không nghĩ là màn hình ghi sai.
    """
    nguon = _doc(DAU)
    # Bỏ chú thích trước khi soát: bản ghi lý do đổi câu có nhắc lại nguyên văn câu cũ, và đó là
    # chú thích chứ không phải chữ hiện lên màn hình.
    than = re.sub(r"/\*.*?\*/", "", nguon, flags=re.S)
    than = re.sub(r"^\s*//.*$", "", than, flags=re.M)
    assert "ô đơn vị trên thanh ngang" not in than, (
        "Màn hình 01 vẫn đang chỉ người dùng sang 'ô đơn vị trên thanh ngang', trong khi ô ấy chưa "
        "được vẽ vì máy chủ chưa mở đường phạm vi."
    )
    assert "chưa đổi được đơn vị" in nguon, (
        "Phải nói thẳng là chưa đổi được đơn vị, thay cho một chỉ dẫn trỏ vào chỗ trống."
    )


def test_css_can_bang_ngoac():
    css = re.sub(r"/\*.*?\*/", "", (GOC / "web" / "app" / "globals.css").read_text(encoding="utf-8"), flags=re.S)
    assert css.count("{") == css.count("}"), (
        f"globals.css lệch ngoặc: {css.count('{')} mở, {css.count('}')} đóng"
    )
