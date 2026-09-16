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
    # Các hằng khung (PHAI_THU/PHAI_TRA) chỉ chứa NHÃN và MÔ TẢ khoảng, không được mang số tiền.
    for ten in ("PHAI_THU", "PHAI_TRA"):
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
    for bo_phan in ("Đội xe", "Công nghệ thông tin", "Kế toán", "Các phòng ban"):
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

def test_nam_nhom_han_khong_trung_nhau_va_noi_ro_khac_bang_luy_ke():
    """Đây là chỗ dễ đọc sai nhất trên cả màn hình.

    Năm nhóm hạn KHÔNG trùng nhau nên cộng cả năm ra đúng tổng công nợ. Bảng dòng tiền bốn mốc ở
    trên thì LŨY KẾ – cột 14 ngày đã chứa trọn cột 7 ngày, cộng vào là sai gấp mấy lần. Hai bảng
    trông giống nhau nằm trên cùng một màn hình, nên màn hình phải tự nói ra sự khác biệt.
    """
    nguon = _doc(KHOI)
    assert "không lũy kế và không trùng nhau" in nguon, (
        "Khối phải nói rõ năm nhóm không lũy kế, và khác bảng dòng tiền bốn mốc ở trên."
    )
    assert "tháng lịch" in nguon, (
        "Mốc 2 tháng / 3 tháng tính theo THÁNG LỊCH từ ngày báo cáo, không mặc định 60/90 ngày "
        "(bản vẽ ghi rõ) – phải ghi ra màn hình."
    )
    assert "chưa có hạn" in nguon, (
        "Khoản chưa có hạn thanh toán theo dõi riêng, không tự xếp vào Dài hạn."
    )


def test_phai_tra_qua_han_theo_doi_rieng():
    """Gộp quá hạn vào nhóm 1 tuần là làm một khoản ĐÃ TRỄ trông giống một khoản SẮP tới hạn."""
    nguon = _doc(KHOI)
    assert "không cộng" in nguon and "v14-quahan" in nguon, (
        "Phải trả quá hạn phải đứng riêng và ghi rõ không cộng vào nhóm 1 tuần."
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
    for luat in (".v14-o{", ".v14-han{"):
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
