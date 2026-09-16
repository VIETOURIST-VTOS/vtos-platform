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
    """Bản vẽ đòi so KẾ HOẠCH và KỲ TRƯỚC. Ghi ra chỗ còn thiếu, không bịa tỷ lệ.

    SỬA 15/9/2026 (TC-36): vế "kỳ trước" ĐÃ CÓ — `services/xu_huong.py` dựng chuỗi các kỳ đã đóng và
    tính chênh lệch từ số thật.

    SỬA 16/9/2026 (TC-41 rồi TC-42): vế "kế hoạch tháng" NAY CŨNG CÓ — cửa nhập /ke-hoach-thang đã
    mở. Câu dòng phụ do `docHoKeHoachKy` dựng ở components/KhoiSauO.tsx, cùng chỗ với hai Ô LỚN
    Doanh thu và Lợi nhuận mà nó phục vụ. Nên phép thử đổi CHỖ NHÌN, và đổi luôn ĐIỀU nhìn:

      · Câu ấy phải là một HÀM, không phải chuỗi viết cứng — tức nó đọc số máy chủ gửi xuống.
      · Hàm ấy phải còn đủ BA nhánh: chưa ai nhập · nhập thiếu pháp nhân · đủ. Nhánh giữa là nhánh
        đáng canh nhất: bỏ nó đi thì phần đã nhập bị cộng lại thành "kế hoạch tháng", và tỉ lệ đạt
        cao vọt mà không có gì trông giống lỗi.
      · Trang KHÔNG được tự tính tỉ lệ đạt — phép chia phải nằm ở máy chủ (ranh giới 09/9).

    Ba lần sửa, cùng một luật: thẻ nói đúng sự thật đang có, và nói ra chỗ còn thiếu kèm người phải
    nhập. Sự thật đổi, luật không đổi.
    """
    sau_o = (GOC / "web" / "components" / "KhoiSauO.tsx").read_text(encoding="utf-8")
    assert "docHoKeHoachKy" in sau_o, (
        "Dòng phụ phải dựng bằng docHoKeHoachKy, không phải một câu viết cứng."
    )
    assert "Chưa có kế hoạch tháng" in sau_o, (
        "Phải còn nhánh 'chưa ai nhập kế hoạch' – bỏ đi là im lặng khi thiếu nguồn so sánh."
    )
    assert "Kế toán" in sau_o, "Phải nói AI nhập kế hoạch tháng."
    assert "thieu" in sau_o and "chưa đủ" in sau_o, (
        "Phải còn nhánh 'nhập thiếu pháp nhân' và phải kê tên pháp nhân còn thiếu: cộng phần đã "
        "nhập lại rồi gọi là kế hoạch tháng là chỗ hỏng nguy hiểm nhất của khối này."
    )

    # Màn hình KHÔNG tự chia. Tỉ lệ đạt do services/ke_hoach.ty_le_dat tính và gửi xuống.
    ma = re.sub(r"/\*.*?\*/", " ", _doc(TRANG) + sau_o, flags=re.S)
    ma = re.sub(r"^\s*//.*$", " ", ma, flags=re.M)
    assert "doanh_thu_thang /" not in ma and "/ ke_hoach" not in ma, (
        "Màn hình không được tự chia thực hiện cho kế hoạch – phép chia ấy nằm ở máy chủ."
    )


def test_the_tour_dang_ban_noi_ro_chua_tinh_duoc_cho_con():
    the = _the(_doc(TRANG), "Tour đang bán")
    assert "chỗ còn" in the and "sức chứa" in the, (
        'Bản vẽ chốt dòng phụ là "Khách đã chốt / chỗ còn". Chưa có sức chứa từng chuyến thì phải '
        "ghi ra, không thay bằng một con số khác.\n" + the
    )


def test_khoi_ton_dong_noi_ro_hai_chi_so_con_thieu():
    """SỬA 16/9/2026 (TC-42): "Tồn đọng cần xử lý" từ một THẺ SỐ thành một Ô LỚN có biểu đồ cơ cấu
    theo ba mức độ (components/KhoiSauO.tsx). Luật không đổi một chữ — bản vẽ chốt BA chỉ số và máy
    chủ mới đếm được một, nên hai chỉ số còn thiếu vẫn phải được nói ra chứ không im lặng.
    """
    sau_o = (GOC / "web" / "components" / "KhoiSauO.tsx").read_text(encoding="utf-8")
    thap = sau_o.lower()
    assert "chưa tách được hồ sơ quá hạn" in thap and "chưa có người nhận" in thap, (
        "Bản vẽ chốt ba chỉ số: hồ sơ quá hạn · nghiêm trọng · chưa có người nhận. Máy chủ mới có "
        "cái giữa – hai cái còn lại phải được nói ra."
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


def test_moi_o_luoi_deu_co_lai_duoc():
    """Vá 13/9/2026 (lần hai). Sau khi chữa riêng khối Tồn đọng, trang vẫn thò 10px – lần này do
    bảng "Điều hành 21 ngày tới" ở KHUNG BÊN CẠNH.

    Đó là bản chất của lỗi này: thủ phạm nằm ở khung khác chứ không phải khung mình đang sửa, nên
    chữa từng khung một là chữa mãi không hết. Một luật cho mọi ô lưới thì chặn được cả lớp lỗi.
    """
    css = (GOC / "web" / "app" / "globals.css").read_text(encoding="utf-8")
    assert ".grid>*{min-width:0}" in css, (
        "Thiếu luật .grid>*{min-width:0}. Ô lưới mặc định là min-width:auto – không bao giờ hẹp "
        "hơn nội dung, nên một bảng dài trong bất kỳ khung nào cũng đẩy cả trang cuộn ngang."
    )


def test_bang_dai_tren_man_hinh_01_nam_trong_khung_cuon_rieng():
    """Vá 13/9/2026 (lần ba). .grid>*{min-width:0} cho KHUNG co lại, nhưng BẢNG bên trong khung thì
    vẫn rộng hơn khung và thò ra ngoài – đo được: khung Điều hành hết ở 1249px, ô <td> của nó ở
    1275px, trong khung nhìn 1265px.

    Bảng rộng hơn chỗ chứa nó thì phải tự cuộn trong khung của nó, chứ không kéo cả trang cuộn
    ngang: đó là quy ước .wrap đã có sẵn trong globals.css.
    """
    import re as _re
    # TC-40 (15/9/2026): màn hình 01 KHÔNG còn bảng nào — ba bảng dài đã chuyển sang khối riêng.
    # Luật không đổi, chỉ đổi chỗ áp dụng: MỌI bảng dài, ở bất kỳ khối nào, phải nằm trong .wrap.
    # Kiểm ngay trên trang là cách chắc nhất để luật không rỉ ra khi có ai lắp bảng mới vào đây.
    nguon = TRANG.read_text(encoding="utf-8")
    assert "<table" not in nguon, (
        "Màn hình 01 có bảng trở lại. Nếu là bảng cố ý thì phải bọc trong <div className=\"wrap\">, "
        "và sửa lại phép kiểm này kèm lý do."
    )
    khoi = "".join((GOC / "web" / "components" / t).read_text(encoding="utf-8")
                   for t in ("KhoiDieuHanh.tsx", "KhoiV14.tsx", "KhoiDongTien.tsx", "KhoiTonDong.tsx"))
    bang = len(_re.findall(r"<table", khoi))
    # Cho phép xuống dòng giữa thẻ bọc và <table>, và cho phép "wrap" đứng ở bất kỳ vị trí nào
    # trong danh sách lớp ("wrap mh01-cuon", "panel wrap"). Bắt đúng một cách viết là bắt CÁCH
    # VIẾT, không bắt ý định — và cách viết thì đổi, ý định thì không.
    boc = len(_re.findall(r'<div className="[^"]*\bwrap\b[^"]*">\s*<table', khoi))
    assert bang > 0 and boc >= 3, (
        f"Các khối dài phải nằm trong <div className=\"wrap\"> để tự cuộn trong khung của chúng "
        f"— đang có {bang} bảng, {boc} bảng được bọc."
    )
    css = (GOC / "web" / "app" / "globals.css").read_text(encoding="utf-8")
    assert ".wrap{overflow-x:auto}" in css, "Quy ước .wrap phải còn trong globals.css"
