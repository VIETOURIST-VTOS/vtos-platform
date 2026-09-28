# -*- coding: utf-8 -*-
"""TC-23 · Sáu khối còn lại của bản vẽ V1.4 trên màn hình 01 (13/9/2026).

Bản vẽ xếp TÁM khối. VTOS đã có 01 phạm vi/kỳ · 02 cần quyết định · 03 tám thẻ · 06 dòng tiền.
Vòng này dựng nốt: 04b Hiệu quả đội xe · 04c Tồn đọng theo bộ phận · 05a Phải thu · 05b Phải trả ·
07 Rủi ro trọng yếu · 08 Tiến độ báo cáo, và bổ sung bốn cột cho 04a Điều hành.

ĐIỀU CÁC PHÉP THỬ NÀY CANH, và vì sao:

Sáu khối hôm nay CHƯA CÓ MỘT CON SỐ NÀO — máy chủ chưa có bảng cho chúng. Đó chính là lúc dễ mắc
lỗi nhất: một ô trống nhìn xấu, và cách "chữa" nhanh nhất luôn là điền một con số 0, hoặc suy ra
từ khối bên cạnh, hoặc giấu khối đi cho gọn. Cả ba đều tệ hơn ô trống:

  · số 0 đọc là "đã đếm và bằng không", khác hẳn "chưa ai nhập";
  · số suy ra từ khối khác thì không ai biết nó không phải số thật;
  · giấu khối đi thì việc còn nợ biến mất khỏi tầm mắt, và không ai đòi nữa.

Nên các phép thử dưới đây canh đúng ba điều: KHÔNG có số bịa, MỖI ô rỗng nói rõ AI nhập và ĐI ĐÂU
để nhập, và ĐẦU CỘT vẫn dựng đủ dù chưa có dòng nào.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
KHOI = GOC / "web" / "components" / "KhoiV14.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
DIEU_HANH = GOC / "web" / "components" / "KhoiDieuHanh.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _bo_chu_thich(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


# ------------------------------------------------------- Đủ khối, đúng thứ tự

def test_ba_khoi_con_lai_giu_dung_thu_tu_ban_ve():
    """Thứ tự bản vẽ là thứ tự ĐỌC, không phải trang trí — và luật ấy vẫn đúng cho những khối CÒN
    LẠI trên màn hình.

    TC-40 (15/9/2026): anh Tuấn soát từng khối trên bản chạy thật và chốt danh sách giữ. Ba khối
    của tệp này còn lại — Hiệu quả đội xe → Phải thu → Phải trả — và chúng phải giữ nguyên thứ tự
    tương đối của bản vẽ. Ba khối bị gỡ (Tồn đọng theo bộ phận · Rủi ro trọng yếu · Tiến độ báo
    cáo) được canh riêng ở phép kiểm dưới.

    SỬA 16/9/2026 (TC-42): Phải thu và Phải trả lên nhóm SÁU Ô LỚN, còn Hiệu quả đội xe xuống dưới
    hàng thẻ nhỏ — nó là số liệu của MỘT bộ phận, không phải một trong sáu con số Chủ tịch đọc đầu
    tiên. Luật giữ nguyên: hai khối công nợ phải đứng cạnh nhau và đúng thứ tự thu trước trả sau,
    vì đó là thứ tự đọc "ai nợ mình → mình nợ ai".
    """
    nguon = _doc(TRANG)
    thu_tu = ["<KhoiPhaiThu", "<KhoiPhaiTra", "<KhoiHieuQuaXe"]
    vi_tri = []
    for k in thu_tu:
        i = nguon.find(k)
        assert i > 0, f"Màn hình 01 chưa gọi {k}"
        vi_tri.append(i)
    assert vi_tri == sorted(vi_tri), (
        "Ba khối còn lại phải đứng đúng thứ tự bản vẽ: Hiệu quả đội xe → Phải thu → Phải trả."
    )


def test_ba_khoi_da_go_van_con_MA_du_khong_con_tren_man_hinh():
    """Gỡ khỏi màn hình KHÔNG phải xoá mã. Các `type` trong tệp khối là HỢP ĐỒNG với máy chủ — bản
    mô tả những trường máy chủ còn nợ. Xoá đi là mất bản mô tả, và đến lúc dựng màn hình riêng cho
    từng phòng thì phải đi tìm lại bản vẽ."""
    trang = _doc(TRANG)
    khoi = _doc(KHOI)
    for k in ("KhoiTonDongBoPhan", "KhoiRuiRo", "KhoiTienDoBaoCao"):
        assert f"<{k}" not in trang, (
            f"{k} đã được anh Tuấn chốt gỡ khỏi màn hình 01 ngày 15/9/2026. Lắp lại thì phải kèm "
            f"lý do mới, và sửa phép kiểm này."
        )
        assert f"export function {k}" in khoi, f"Mã của {k} bị xoá — hợp đồng dữ liệu mất theo."


def test_moi_khoi_deu_co_hop_dong_du_lieu_khai_bang_type():
    """Làn viết máy chủ đọc chính các `type` này để biết phải trả trường gì."""
    nguon = _doc(KHOI)
    for t in ("HieuQuaXe", "DongTonDong", "NhomHan", "RuiRo", "DongTienDo"):
        assert f"export type {t}" in nguon, f"Thiếu hợp đồng dữ liệu cho {t}"


# ------------------------------------------------- Không bịa số, không giấu khối

def test_khong_lay_so_0_thay_cho_chua_co_nguon():
    """`rỗng khác không` – luật xuyên suốt VTOS.

    Cách canh: trong tệp khối không được có chỗ nào lấy 0 làm giá trị dự phòng cho một CON SỐ
    nghiệp vụ (kiểu `?? 0` hay `|| 0`). Ô rỗng phải đi tới nhánh "Chưa kết nối".
    """
    than = _bo_chu_thich(_doc(KHOI))
    xau = re.findall(r"\?\?\s*0\b|\|\|\s*0\b", than)
    assert not xau, (
        f"Có {len(xau)} chỗ lấy 0 thay cho 'chưa có nguồn' trong KhoiV14.tsx. Số 0 đọc là 'đã đếm "
        "và bằng không', khác hẳn 'chưa ai nhập'."
    )


def test_khong_bia_so_mau_trong_ma():
    """Không có mảng dữ liệu mẫu nào nằm sẵn trong tệp – khối rỗng thì phải rỗng thật."""
    than = _bo_chu_thich(_doc(KHOI))
    # SỬA 16/9/2026 (TC-45): hai khung PHAI_THU / PHAI_TRA gộp thành MỘT — `BAY_NHOM` — vì anh Tuấn
    # chốt một bộ mốc dùng chung cho cả hai hướng. Luật không đổi một chữ: khung chỉ được khai NHÃN
    # và MÔ TẢ khoảng, số phải đến từ máy chủ.
    for ten in ("BAY_NHOM",):
        i = than.find(f"const {ten}")
        assert i > 0, f"Thiếu khung {ten}"
        khung = than[i:than.find("];", i)]
        assert "so:" not in khung, (
            f"Khung {ten} đang mang sẵn giá trị `so:` – khung chỉ được khai nhãn và định nghĩa "
            "khoảng, số phải đến từ máy chủ."
        )


def test_moi_o_rong_deu_noi_ai_nhap_va_di_dau():
    """Ranh giới 09/9: mỗi con số phải có một cửa nhập. Ô trống không kèm cửa là việc không ai nhận."""
    nguon = _doc(KHOI)
    assert "function ChuaNoi" in nguon, "Thiếu mảnh dùng chung cho ô rỗng"
    i = nguon.find("function ChuaNoi")
    than = nguon[i:i + 700]
    assert "Chưa kết nối" in than and "nhập" in than and "the-cua" in than, (
        "Mảnh ô rỗng phải nói đủ ba thứ: chưa kết nối · ai nhập · đường dẫn tới cửa nhập."
    )
    # Sáu khối, mỗi khối phải chỉ ra một bộ phận.
    # SỬA 29/9/2026: bỏ "Kế toán" — hai khối Phải thu · Phải trả thôi in "Kế toán nạp chứng từ"
    # theo lệnh anh Tuấn "xoá hết ghi chú, chỉ để lại biểu đồ và con số, link vào xem chi tiết".
    for bo_phan in ("Đội xe", "Công nghệ thông tin", "Các phòng ban"):
        assert bo_phan in nguon, f"Chưa khối nào chỉ ra bộ phận {bo_phan}"


def test_bang_chua_co_dong_van_dung_du_dau_cot():
    """Đầu cột chính là bản mô tả việc còn nợ – giấu đi thì lúc dựng phải đi tìm lại bản vẽ."""
    nguon = _doc(KHOI)
    assert "function BangRong" in nguon, "Thiếu mảnh bảng rỗng vẫn dựng đủ đầu cột"
    for cot in ("Hồ sơ lâu nhất", "Người chịu trách nhiệm", "Hạn khắc phục",
                "Mức ảnh hưởng", "Người xử lý", "Tiến độ",
                "Hồ sơ / kết luận", "Đơn vị phụ trách", "Bước tiếp theo"):
        assert cot in nguon, f"Thiếu cột '{cot}' mà bản vẽ V1.4 đòi"


# --------------------------------------------- Luật nghiệp vụ của bản vẽ phải được ghi ra

def test_khoi_cong_no_chi_con_bieu_do_so_va_loi_xem_chi_tiet():
    """LUẬT ĐẢO NGÀY 29/9/2026.

        "trong phần phải thu phải trả em xoá hết ghi chú cho anh, chỉ để lại biểu đồ và con số,
         link vào xem chi tiết"                                        — anh Tuấn, 29/9/2026

    Bản cũ (TC-23, TC-45) bắt hai khối in câu "bảy nhóm không trùng nhau", mốc tháng lịch và câu
    "không xếp vào Dài hạn". Chủ tịch đọc màn hình mỗi ngày và bảo bỏ: khối chỉ còn biểu đồ, con
    số và một lối vào chi tiết. Luật chia nhóm không mất — nó nằm ở services/han_cong_no.py.
    """
    nguon = _doc(KHOI)
    khu = (GOC / "web" / "components" / "BaKhuBieuDo.tsx").read_text(encoding="utf-8")
    assert "trùng nhau nên cộng cả bảy" not in khu, "Câu chân biểu đồ công nợ phải bỏ."
    i = nguon.index("function KhoiHan")
    than = nguon[i:nguon.index("07 · RỦI RO", i)]
    for cau in ("Mốc tính từ ngày báo cáo", "xếp vào Dài hạn", "Số lấy từ sổ nghĩa vụ"):
        assert cau not in than, f"Khối công nợ còn ghi chú: {cau}"
    assert "Xem chi tiết" in than and 'chi_tiet="/cong-no"' in than and 'chi_tiet="/cong-no?tab=tra"' in than


def test_qua_han_la_mot_nhom_va_chi_nam_dung_mot_cho():
    """LUẬT NÀY ĐẢO CHIỀU NGÀY 16/9/2026 (TC-45), và đảo vì một lý do đáng ghi.

    Bản cũ để "Phải trả quá hạn" NGOÀI năm nhóm, theo dõi ở một ô riêng, đúng với lập luận "một
    khoản đã trễ khác hẳn một khoản sắp tới hạn". Lập luận ấy không sai. Nhưng hệ quả của nó là
    tổng năm nhóm trên màn hình KHÔNG gồm khoản đã trễ — nên ai cộng thử bằng mắt sẽ ra một con số
    khác con số hệ thống hiểu là tổng công nợ, và không có gì trên màn hình nói ra điều đó.

    Anh Tuấn chốt một bộ mốc dùng chung, trong đó Quá hạn là nhóm ĐẦU TIÊN của cả hai hướng. Mức
    khẩn vẫn đọc ra ngay — nó mang màu trạng thái trên biểu đồ — nhưng con số chỉ nằm ĐÚNG MỘT chỗ.

    Phép thử vì thế canh điều NGƯỢC LẠI điều nó canh hôm qua: không được có ô "quá hạn" thứ hai.
    """
    nguon = _bo_chu_thich(_doc(KHOI))
    # Bắt ĐÚNG cái ô ấy, không bắt chuỗi "qua_han": khối Tồn đọng theo bộ phận có trường
    # `ho_so_qua_han` hoàn toàn chính đáng, và một phép soát theo chuỗi sẽ báo oan nó — đúng bài
    # học TC-41 (cấm MỘT HÀNH VI, không cấm một dãy ký tự).
    assert "Phải trả quá hạn" not in nguon and "qua_han={" not in nguon, (
        "Còn ô 'phải trả quá hạn' riêng. Quá hạn nay là một trong bảy nhóm; giữ thêm một ô riêng "
        "là để cùng một khoản tiền hiện hai chỗ trên một màn hình."
    )
    hcn = (GOC / "backend" / "app" / "services" / "han_cong_no.py").read_text(encoding="utf-8")
    assert '"Quá hạn"' in hcn.split("MOC = ")[1].split("\n")[0], (
        "Quá hạn phải là một nhãn trong MOC, dùng chung cho cả hai hướng."
    )
    khu = (GOC / "web" / "components" / "BaKhuBieuDo.tsx").read_text(encoding="utf-8")
    assert 'trang_thai: true' in khu.split("KHUNG_HAN")[1][:300], (
        "Nhóm Quá hạn phải mang cờ trạng thái để đổi màu — mức khẩn vẫn phải đọc ra ngay."
    )


def test_hieu_qua_xe_giu_hai_cau_canh_bao_nghiep_vu():
    """Hai câu này là chỗ đọc sai con số, không phải chữ trang trí."""
    nguon = _doc(KHOI)
    assert "chưa chắc" in nguon, "Thiếu câu: xe không có lệnh CHƯA CHẮC sẵn sàng"
    assert "có thể" in nguon and "khai thác" in nguon, (
        "Thiếu câu: công suất tính trên thời gian xe CÓ THỂ khai thác, không phải số ngày trong kỳ."
    )


def test_ton_dong_bo_phan_noi_ro_chong_cong_trung():
    nguon = _doc(KHOI)
    assert "Mỗi hồ sơ chỉ tính" in nguon and "máy chủ" in nguon, (
        "Một hồ sơ phát ba cảnh báo vẫn là một hồ sơ; phải ghi rõ việc chống trùng làm ở MÁY CHỦ."
    )


# ------------------------------------------------------ Khối Điều hành: bốn cột mới

def test_khoi_dieu_hanh_du_bay_cot_ban_ve():
    """TC-40: khối Điều hành rời màn hình 01 sang tệp riêng, mang theo nguyên bảy cột của bản vẽ.
    Luật không đổi, chỉ đổi tệp chứa nó."""
    nguon = _doc(DIEU_HANH)
    for cot in ("Dịch vụ còn thiếu", "Xe", "HDV", "Phụ trách"):
        assert f"<th>{cot}</th>" in nguon, f"Khối Điều hành thiếu cột '{cot}' của bản vẽ V1.4"
    assert "chưa nối" in nguon, "Bốn cột mới phải ghi rõ ô nào máy chủ chưa trả"
    assert "không" in nguon and "mặc định chuyến đã sẵn sàng" in nguon, (
        "Bản vẽ ghi thẳng: KHÔNG mặc định chuyến đã sẵn sàng khi thiếu dữ liệu."
    )


# ------------------------------------------------------------- Không tràn ngang

def test_bang_moi_deu_nam_trong_khung_cuon():
    """Bài học ba lớp của TC-21c/d/e: bảng rộng hơn khung thì phải tự cuộn, không kéo cả trang."""
    nguon = _doc(KHOI)
    so_bang = nguon.count("<table className=\"v14-bang\"")
    so_wrap = nguon.count('<div className="wrap">')
    assert so_wrap >= so_bang, (
        f"Có {so_bang} bảng nhưng chỉ {so_wrap} khung cuộn – bảng nào cũng phải nằm trong .wrap."
    )
    css = _doc(CSS)
    # SỬA 16/9/2026 (TC-45): lớp .v14-han{ đi cùng bảy ô số vuông đã bỏ; hàng thanh ngang
    # (.bd-th-hang) thay chỗ nó và cũng phải có min-width:0 vì cùng một lý do.
    for luat in (".v14-o{", ".bd-th-hang{"):
        i = css.find(luat)
        assert i > 0, f"Thiếu luật {luat}"
        assert "min-width:0" in css[i:i + 260], (
            f"{luat} thiếu min-width:0 – ô lưới không co lại được thì lại đẩy tràn ngang."
        )


# ------------------------------------------------- Mục menu theo bản vẽ (đo 13/9)

def test_muc_menu_dung_dai_mau_dac_cua_ban_ve():
    """Anh Tuấn nhận xét bản của Claude tối hơn bản vẽ. Đo ra: nền trang, nền thanh và nền thẻ khớp
    từng mã (độ sáng trung bình 3,25% so với 3,31%), riêng MỤC MENU thì lớp phủ trắng 5% chỉ ra
    #1C3248 trong khi bản vẽ tô đặc #24476B – sáng gấp 1,98 lần.
    """
    css = _doc(CSS)
    tok = _doc(GOC / "web" / "app" / "tokens.css")
    assert "--vtos-muc-nav:      #24476B" in tok, "Thiếu màu dải mục menu của bản vẽ"
    i = css.find("aside.side .grp{")
    assert i > 0, "Không thấy luật mục menu"
    than = css[i:i + 500]
    assert "var(--vtos-muc-nav)" in than, "Mục menu phải dùng dải màu đặc, không phủ trắng 5%"
    assert "rgba(255,255,255,.05)" not in than, "Vẫn còn lớp phủ trắng 5% cũ"
    # Mục ĐANG CHỌN giữ quy tắc 1 của bộ nhận diện.
    j = css.find("aside.side .grp.on{")
    assert j > 0 and "rgba(255,255,255,.14)" in css[j:j + 300], (
        "Mục đang chọn phải giữ lớp phủ trắng 14% – quy tắc 1 anh Tuấn chốt 12/9. Bản vẽ tô xanh "
        "đặc, đó là chỗ bản vẽ chỏi với quy tắc, đã hỏi lại anh chứ không tự đổi."
    )
