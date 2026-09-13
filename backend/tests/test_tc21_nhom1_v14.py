# -*- coding: utf-8 -*-
"""TC-21 · Nhóm 1 của bảng đối chiếu với bản vẽ V1.4 (13/9/2026).

Năm việc sửa được ngay ở lớp giao diện, không cần bảng mới ở máy chủ:

  1. Ô tài khoản không in chức danh hai lần.
  2. Dòng phụ ba thẻ ghi đúng thứ bản vẽ đòi, hoặc ghi rõ chỗ còn thiếu.
  3. Đính chính: câu chỉ dẫn phạm vi trên màn hình 01 từng chỉ vào một ô KHÔNG CÓ.

HAI ĐỀ NGHỊ CỦA BẢN VẼ ĐÃ BỊ BÁC (anh Tuấn xem bản đã làm rồi quyết, 13/9/2026). Cả hai đều được
canh NGƯỢC LẠI ở dưới, để vòng sau không lặng lẽ áp bản vẽ đè lên quyết định:

  · Chuông giữ SỐ THẬT, không chặn trần 99+.
  · Khối cảnh báo giữ tên "Tồn đọng cần xử lý" và giữ MÃ MÁY, không dịch sang câu tiếng Việt.
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

def test_chuong_giu_so_that_khong_chan_tran():
    """QUYẾT ĐỊNH 13/9/2026: giữ số thật của VTOS, bác đề nghị 99+ của bản vẽ V1.4.

    Lý do đứng được: 1944 nói lên quy mô tồn đọng, còn "99+" che mất chính điều ấy – một cái chuông
    đứng ở 99+ suốt nhiều tuần thì không ai biết nó đang là 120 hay 1900.
    """
    nguon = _doc(SHELL)
    # Bỏ chú thích: bản ghi lý do bác đề nghị có nhắc chữ 99+, và đó là chú thích chứ không phải
    # chữ hiện lên chuông.
    than = re.sub(r"/\*.*?\*/", "", nguon, flags=re.S)
    than = re.sub(r"^\s*//.*$", "", than, flags=re.M)
    assert "99+" not in than, (
        "Chuông đang bị chặn trần 99+. Anh Tuấn đã xem bản chặn trần và quyết GIỮ SỐ THẬT ngày "
        "13/9/2026 – đừng áp lại bản vẽ đè lên quyết định ấy."
    )
    i = nguon.find('aria-label={`Cảnh báo nghiệp vụ')
    assert i > 0, "Nhãn trợ năng của chuông phải nói rõ đây là cảnh báo nghiệp vụ, không phải 'thông báo chưa đọc'"
    assert "${alerts}" in nguon[i:i + 200], "Nhãn trợ năng phải đọc con số thật"


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


# -------------------------------------------------------------- 2. Khối cảnh báo

def test_khoi_giu_ten_ton_dong_can_xu_ly():
    """QUYẾT ĐỊNH 13/9/2026: giữ tên của VTOS, bác đề nghị "Rủi ro & việc cần theo dõi".

    Lý do: thẻ chỉ tiêu ở trên đã tên là "Tồn đọng cần xử lý"; hai chỗ nói về cùng một thứ thì phải
    gọi cùng một tên, nếu không người đọc tưởng là hai con số khác nhau.
    """
    nguon = _doc(KHOI)
    assert "<h2>Tồn đọng cần xử lý</h2>" in nguon, (
        'Khối phải giữ tên "Tồn đọng cần xử lý" cho khớp thẻ chỉ tiêu ở trên (anh Tuấn chốt 13/9).'
    )


def test_giu_ma_may_khong_dich_sang_cau_tieng_viet():
    """QUYẾT ĐỊNH 13/9/2026: giữ mã máy, bác đề nghị dịch mã của bản vẽ V1.4.

    Lý do: mã là thứ tra ngược được về robot đã phát ra dòng ấy; câu dịch thì mỗi người nhớ một
    kiểu. Câu ví dụ ngay dưới mỗi dòng đã đủ để người đọc hiểu loại ấy là gì.
    """
    nguon = _doc(KHOI)
    assert "TEN_LOAI" not in nguon and "tenLoai" not in nguon, (
        "Bảng dịch mã cảnh báo đã bị bác ngày 13/9/2026 – đừng đưa lại."
    )
    assert "<b>{n.kind}</b>" in nguon, "Dòng gom nhóm phải in thẳng mã máy"


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


def test_khoi_ton_dong_khong_the_day_tran_ngang():
    """Vá 13/9/2026 sau khi đo bản chạy thật: trang rộng 1329px trong khung 1265px.

    Khối nằm trong .grid, mà ô lưới mặc định là min-width:auto – không bao giờ hẹp hơn nội dung.
    Cộng với bảng auto layout lấy chuỗi dài nhất làm bề rộng tối thiểu, một câu ví dụ không xuống
    dòng là đủ đẩy cả trang cuộn ngang. Ba luật dưới đây chặn đúng ba nguyên nhân ấy.
    """
    css = (GOC / "web" / "app" / "globals.css").read_text(encoding="utf-8")
    assert "#ton-dong{min-width:0}" in css, (
        "Khối phải được phép co lại; thiếu min-width:0 thì ô lưới giữ nguyên bề rộng nội dung."
    )
    assert "table-layout:fixed" in css, (
        "Bảng gom nhóm phải dùng table-layout:fixed, nếu không cột nở theo chuỗi dài nhất."
    )
    i = css.index(".td-vd{")
    assert "max-width:52ch" not in css[i:i + 200], (
        "max-width theo ch làm chính nó thành bề rộng tối thiểu khi ô lưới hẹp hơn – lại tràn."
    )
