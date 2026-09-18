# -*- coding: utf-8 -*-
"""TC-62 · MỘT THANH NGANG · BA CÂU ĐỌC HỘ XUỐNG CHỖ RÊ CHUỘT · HAI KHUNG RIÊNG · CỘT BẰNG NHAU.

    "gộp thành 1 thanh ngang, bỏ bớt chú thích không quan trọng … chỉ giữ lại chữ kế hoạch
     tháng và mũi tên để cho CHỦ TỊCH nhập vào"                       — anh Tuấn, 18/9/2026

    "khung em vừa vẽ ok, nhưng mà cột biểu đồ của doanh thu và lợi nhuận bằng nhau, hiện tại
     cái to cái nhỏ"                                                  — anh Tuấn, 18/9/2026

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN VIỆC CỦA MỘT VÒNG, VÀ CHỖ DỄ HỎNG CỦA TỪNG VIỆC
══════════════════════════════════════════════════════════════════════════════════════════════
1. ĐẦU TRANG GỘP THÀNH MỘT THANH. Canh ở test_tc31 (cả hai mặt của luật) và ở test_tc35 (nút In
   phải đứng cùng thân hàm với kỳ báo cáo). Tệp này không canh lại.

2. BA CÂU ĐỌC HỘ XUỐNG `title`. Chỗ hỏng: có người "dọn dẹp" bằng cách xoá hẳn `chu` cho gọn —
   lúc ấy mục tiêu kỳ, tỉ lệ đạt và biên lợi nhuận biến mất khỏi hệ thống chứ không phải khỏi màn
   hình. Đó là mất một câu trả lời, đúng thứ luật "rỗng khác không" chặn.

3. HAI KHUNG RIÊNG NHƯNG MỘT KỲ. Chỗ hỏng NGUY HIỂM NHẤT của cả vòng: tách khối thành hai thành
   phần, mỗi thành phần tự gọi máy chủ. Lúc ấy Doanh thu xem QUÝ còn Lợi nhuận xem THÁNG, hai con
   số nằm cạnh nhau như thể so được — đúng trạng thái mà TC-44 sinh ra để bỏ. Không lỗi nào báo.

4. MỘT BỀ RỘNG THÂN CỘT. Chỗ hỏng: ai đó thêm một hình mới và đặt lại `left`/`right` bằng số cứng
   cho riêng hình ấy, thế là quay về "cái to cái nhỏ" mà không ai thấy trong mã.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DAU = GOC / "web" / "components" / "DauManHinh01.tsx"
KQ = GOC / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx"
BD = GOC / "web" / "components" / "BieuDo.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _ma(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


def _css() -> str:
    return re.sub(r"/\*(?:.|\n)*?\*/", " ", CSS.read_text(encoding="utf-8"))


# ───────────────────── 1 · THANH NGANG MANG ĐỦ BỐN THỨ ─────────────────────

def test_thanh_ngang_mang_du_bon_thu_cua_dau_trang():
    """Gộp ba tầng thành một thanh là để BỚT CHỮ, không phải để bớt câu trả lời.

    Bốn thứ dưới đây mỗi thứ trả lời được câu "bỏ đi thì ai mất gì": tên trang, kỳ báo cáo (và cửa
    sang quý/năm), phạm vi, ngày báo cáo — ngày báo cáo là mốc phân nhóm của mọi bảng theo hạn ở
    dưới, nên thiếu nó thì người đọc phải đoán "quá hạn" là quá so với ngày nào.
    """
    ma = _ma(DAU)
    than = ma[ma.index("export function TieuDe"):]
    than = than[:than.index("export function", 1)]
    # TC-65 (18/9/2026) · DANH SÁCH DÀI RA MỘT MỤC, VÀ MỘT MỤC ĐỔI CHỖ BÁM.
    #   · Phạm vi: anh Tuấn chốt "bỏ Vietourist công ty mẹ" khỏi thanh, nên nhãn rê chuột chuyển
    #     sang bám vào TÊN TRANG. Câu trả lời không mất khỏi hệ thống, chỉ đổi chỗ.
    #   · Việc chờ quyết: khối riêng "Cần Chủ tịch quyết định" nhập vào thanh, nên thanh phải
    #     BÀY ĐƯỢC danh sách ấy. Thiếu chỗ này thì việc chờ Chủ tịch biến mất mà không lỗi nào báo.
    # Luật của phép thử không đổi: thanh gộp lại là để BỚT CHỮ, không phải để bớt câu trả lời.
    for can, vi in (
        ("mh01-thanh-ten", "tên trang"),
        ('title="Kỳ báo cáo"', "kỳ báo cáo"),
        ("Quý và năm →", "cửa sang quý và năm"),
        ('title="Phạm vi: Vietourist — công ty mẹ"', "phạm vi"),
        ('title="Ngày báo cáo"', "ngày báo cáo"),
        ("cho.map(", "hàng nút việc chờ quyết"),
    ):
        assert can in than, f"Thanh ngang thiếu {vi}."


# ───────────────────── 2 · BA CÂU ĐỌC HỘ CÒN SỐNG, CHỈ ĐỔI CHỖ ─────────────────────

def test_ba_cau_doc_ho_khong_bi_xoa_ma_chuyen_sang_title():
    """Chỗ hỏng số 2 — canh cái NỘI DUNG, không canh chỗ nó hiện ra.

    `cau_ke_hoach` mang mục tiêu kỳ và tỉ lệ đạt; `cau_bien` mang biên lợi nhuận; câu thứ ba phân
    biệt lợi nhuận tour với lợi nhuận trước thuế. Cả ba là SỐ hoặc là ranh giới giữa hai con số —
    xoá là bớt một câu trả lời của hệ thống, chứ không phải dọn màn hình.
    """
    ma = _ma(KQ)
    assert "const cau_ke_hoach" in ma, "Mất câu kế hoạch (mục tiêu kỳ + tỉ lệ đạt)."
    assert "const cau_bien" in ma, "Mất câu biên lợi nhuận."
    assert "chưa gánh chi phí chung" in ma, (
        "Mất ranh giới giữa lợi nhuận tour và lợi nhuận trước thuế."
    )
    assert "chu={cau_ke_hoach}" in ma and "chu={cau_bien}" in ma, (
        "Ba câu ấy phải đi vào `chu` của ô số — tức thuộc tính title, đọc được khi rê chuột."
    )
    than = ma[ma.index("function OSo"):]
    than = than[:than.index("\n}", than.index("return (")) ]
    assert "title={chu}" in than, "`OSo` phải gắn `chu` vào title, nếu không nó là một tham số chết."
    assert "kqkd-phu" not in ma, (
        "Lớp `.kqkd-phu` của dòng chú thích cũ còn được gắn — ba câu ấy lại hiện ra trên màn hình."
    )


def test_chan_khoi_chi_con_mot_cua_nhap():
    """"chỉ giữ lại chữ kế hoạch tháng và mũi tên để cho CHỦ TỊCH nhập vào".

    Đoạn văn bốn dòng ở chân khối cũ nói ba việc, và cả ba nay có chỗ nói đúng hơn: phạm vi ghi
    trên thanh đầu trang, "thang đo riêng" do chính hai khung riêng nói hộ, đơn vị đọc ngay trên
    nhãn trục. Giữ lại đoạn văn ấy là nói lại lần thứ hai ở chỗ ít ai đọc nhất.
    """
    ma = _ma(KQ)
    assert "Kế hoạch tháng →" in ma, "Mất cửa nhập kế hoạch tháng của Chủ tịch."
    assert "đừng so chiều cao cột" not in ma, "Đoạn văn chân khối cũ vẫn còn."
    assert "công ty con và liên kết" not in ma, "Đoạn văn chân khối cũ vẫn còn."


# ───────────────────── 3 · HAI KHUNG RIÊNG, MỘT KỲ ─────────────────────

def test_hai_khung_rieng_tren_man_hinh():
    """Hai `<section className="panel">` — không còn một khung chứa hai tầng."""
    ma = _ma(KQ)
    assert ma.count('<section className="panel"') == 3, (
        "Phải có đúng ba `<section className=\"panel\"`: một khung lúc chưa tải được, rồi hai "
        "khung Doanh thu và Lợi nhuận."
    )
    assert "kqkd-chong" not in ma, "Bố cục hai tầng của TC-47 vẫn còn."
    assert "an_nhan_x" not in _ma(BD), (
        "`an_nhan_x` chỉ có một người dùng và người ấy đã đi; để lại là một tham số mồ côi."
    )
    css = _css()
    for lop in (".kqkd-chong", ".kqkd-tang", ".kqkd-ten", ".kqkd-phu", ".bd-nhanx.an"):
        assert lop not in css, f"Kiểu {lop} còn trong globals.css nhưng không ai dùng."


def test_mot_bo_chon_ky_cho_ca_hai_khung():
    """Chỗ hỏng số 3 — điều quan trọng nhất của vòng này.

    Hai khung phải do CÙNG MỘT thành phần dựng ra, từ CÙNG MỘT trạng thái kỳ. Tách thành hai thành
    phần tự gọi máy chủ là dựng lại trạng thái mà TC-44 sinh ra để bỏ: doanh thu xem QUÝ còn lợi
    nhuận xem THÁNG, hai con số nằm cạnh nhau như thể so được với nhau. Và biên lợi nhuận — phép
    chia chỉ có nghĩa khi tử và mẫu cùng kỳ — mất theo.
    """
    ma = _ma(KQ)
    assert ma.count("export default function") == 1, (
        "Khối Kết quả kinh doanh phải là MỘT thành phần dựng ra hai khung."
    )
    assert ma.count("const dieu_khien") == 1 and ma.count("{dieu_khien}") == 2, (
        "Bộ chọn kỳ phải được khai một lần và bày ở đúng một chỗ trên màn hình (khung Doanh thu) "
        "cộng với nhánh chưa tải được."
    )
    assert ma.count('api(`/bao-cao/ket-qua-kinh-doanh') == 1, (
        "Chỉ được gọi máy chủ ở MỘT chỗ — hai lời gọi là hai kỳ có thể lệch nhau."
    )
    # Cả hai con số đều in kỳ của chúng, nên người đọc thấy hai khung cùng kỳ mà không cần chú thích.
    assert ma.count("nhan_ky") >= 3, "Mỗi con số phải mang kỳ của nó."


# ───────────────────── 4 · MỘT BỀ RỘNG THÂN CỘT ─────────────────────

def test_than_cot_khai_dung_mot_lan_va_moi_hinh_deu_lay_tu_do():
    """"cột biểu đồ của doanh thu và lợi nhuận bằng nhau, hiện tại cái to cái nhỏ".

    Trước TC-62 bề rộng thân cột không hề được khai: cột đơn ăn TRỌN ô lưới còn cột đôi chia đôi
    chính ô ấy, nên một cây cột ở hình Doanh thu rộng gấp đôi một cây ở hình Lợi nhuận. Bề rộng là
    một kênh thị giác — hai bề rộng khác nhau cho hai chỉ tiêu ngang hàng nói một điều mà số liệu
    không nói.
    """
    css = _css()
    assert css.count("--bd-cot-rong:") == 1, (
        "Bề rộng thân cột phải khai ĐÚNG MỘT LẦN; khai hai lần là hai hình có thể khác nhau."
    )
    # Thân cột đơn và thân cột đôi đều phải lấy từ biến ấy, không được đặt số cứng.
    than = css[css.index(".bd-thanh{"):css.index(".bd-thanh{") + 200]
    assert "var(--bd-cot-le)" in than, "Thân cột đơn không lấy bề rộng đã khai."
    doi = css[css.index(".bd-mot.doi>.bd-thanh{"):]
    doi = doi[:doi.index("\n", doi.index(".bd-mot.doi>.bd-thanh.hai{"))]
    assert doi.count("var(--bd-cot-rong)") == 2, (
        "Hai thân của cột đôi phải rộng bằng đúng `--bd-cot-rong` — không phải một thân bị xẻ đôi."
    )


def test_o_trong_rong_bang_dung_than_cot():
    """Ô trống hẹp hơn hay rộng hơn thân cột đều là hình nói ngược.

    `.bd-khuyet` là khung nét đứt cho tháng CHƯA AI NỘP SỐ. Trước TC-62 nó chính là ô lưới nên nó
    luôn khớp với cột đơn — chú thích của TC-47 đã ghi đúng điều này và vì thế đã chọn nới KHE thay
    vì thu thân cột. Nay thân cột hẹp lại thì khung nét đứt phải hẹp theo, nếu không một tháng chưa
    có số lại rộng hơn một tháng đã có số.
    """
    css = _css()
    assert ".bd-khuyet::before{" in css, (
        "Ô trống phải vẽ bằng `::before` để hẹp theo thân cột — đổi viền của chính `.bd-mot` thì "
        "nhãn tháng bên dưới lệch khỏi tâm ô."
    )
    khoi = css[css.index(".bd-khuyet::before{"):]
    khoi = khoi[:khoi.index("}")]
    assert "var(--bd-cot-le)" in khoi, "Ô trống không lấy cùng bề rộng với thân cột."
