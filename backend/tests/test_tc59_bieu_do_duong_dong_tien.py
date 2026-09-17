# -*- coding: utf-8 -*-
"""TC-59 · BA ĐƯỜNG THU · CHI · TỒN, VÀ MỘT KHUNG DUY NHẤT CHO CẢ KHỐI DÒNG TIỀN.

    "em thiet ke lai cho anh biểu đồ giống nhu hình mẫu 1, và gòm hinh 2 lai cho gọn nằm trong
     khung cua biểu đồ dòng tiền o phan chú thich bên dưới biểu đồ ... gom hinh 2 vao chung hình
     va nối liền với biều đồ hình 4"                                  — anh Tuấn, 17/9/2026

Anh Tuấn gửi bốn ảnh: một bản mẫu "BIẾN ĐỘNG DÒNG TIỀN" ba đường, và ba mảnh rời của khối dòng
tiền đang chạy. Lệnh giao gồm hai việc, và việc thứ hai mới là việc khó:

  1. HÌNH: từ một hình cột chỉ vẽ số dư → ba đường THU · CHI · TỒN cùng một khung.
  2. BỐ CỤC: ba mảnh rời gộp thành MỘT khung — hình trước, chú thích sau, bốn mốc nối liền.

══════════════════════════════════════════════════════════════════════════════════════════════
SÁU CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. ĐƯỜNG NỐI QUA CHỖ TRỐNG. Đây là lý do `BieuDoCot` chọn cột chứ không chọn đường ngay từ đầu:
   nối hai điểm hai bên một lỗ hổng là VẼ RA giá trị của tuần ở giữa — một con số không ai nhập
   và không ai kiểm được, mà hình thì trông hoàn toàn bình thường.
2. HAI ĐƯỜNG CHẬP LÀM MỘT VỚI NGƯỜI MÙ MÀU. Xanh lá + hồng cách nhau ΔE 2,1 với mắt mù màu lục —
   người ấy không phân biệt được đường thu với đường chi. Chọn màu bằng mắt thì không bao giờ
   thấy chỗ này.
3. HAI TRỤC TUNG. Bản mẫu có số ở cả hai mép. Nếu hai mép đọc từ hai mảng khác nhau thì đó là hai
   thang đo, và luật 4 của bộ biểu đồ đổ — đổi thang là đổi được kết luận.
4. `thu` / `chi` TỪNG TUẦN LỆCH VỚI Ô TỔNG. Hai ô "Dự kiến thu" và "Dự kiến chi" là tổng mười ba
   tuần của chính hai đường ấy. Cộng ở hai chỗ khác nhau thì sớm muộn ra hai kết quả.
5. SUY `thu` TỪ HIỆU HAI SỐ DƯ. Hiệu ấy là thu TRỪ chi. Gọi nó là "thu" thì con số sai mà hình
   vẫn trông đúng — không phép cộng nào bắt được.
6. BỐ CỤC TÁCH LẠI THÀNH BA MẢNH. Đúng cái anh Tuấn bảo gộp. Khe hở giữa ba khối đọc ra là ba
   chuyện khác nhau, trong khi cả ba nói về một dòng tiền.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
BIEUDO = GOC / "web" / "components" / "BieuDo.tsx"
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"
CSS = GOC / "web" / "app" / "globals.css"
BANG = GOC / "backend" / "app" / "services" / "dashboard.py"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_tsx(s: str) -> str:
    """Bỏ chú thích — canh HÀNH VI, không canh chữ trong lời giải thích (bài học TC-41)."""
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


def _ma_css(s: str) -> str:
    return re.sub(r"/\*(?:.|\n)*?\*/", " ", s)


def _ma_py(s: str) -> str:
    return re.sub(r"#.*$", " ", s, flags=re.M)


# ═════════════════ 1 · ĐƯỜNG ĐỨT Ở CHỖ TRỐNG ═════════════════

def test_duong_khong_noi_qua_cho_trong():
    """Chỗ hỏng số 1 — luật 1 của bộ biểu đồ (rỗng khác không) sống trong hình này ở `doanLien`."""
    ma = _ma_tsx(_doc(BIEUDO))
    assert "export function doanLien(" in ma, (
        "Phải có hàm cắt chuỗi thành các đoạn liền. Vẽ thẳng một `polyline` qua cả mảng là nối "
        "liền qua mọi lỗ hổng — và một tuần chưa ai nhập số sẽ có một giá trị do máy vẽ tự sinh."
    )
    i = ma.index("export function doanLien(")
    than = ma[i:ma.index("\n}", i)]
    assert "cur = []" in than and "ra.push(cur)" in than, (
        "Gặp `null` phải ĐÓNG đoạn đang mở và mở đoạn mới, không phải bỏ qua điểm ấy rồi đi tiếp: "
        "bỏ qua là hai điểm hai bên lỗ hổng nối thẳng vào nhau."
    )
    assert "doan.length < 2 ? null" in ma, (
        "Đoạn chỉ có MỘT điểm thì không vẽ nét — một nét nối một điểm với chính nó là một chấm giả."
    )


def test_du_ve_duong_doi_it_nhat_hai_diem_co_so():
    """Luật 2: dưới hai điểm có số thì không vẽ, và phải nói vì sao."""
    ma = _ma_tsx(_doc(BIEUDO))
    i = ma.index("export function duVeDuong(")
    than = ma[i:ma.index("\n}", i)]
    assert ">= 2" in than, "Một điểm đứng một mình không so với kỳ nào."
    assert "BieuDoRong" in ma[ma.index("export function BieuDoDuong("):], (
        "Không đủ điều kiện vẽ thì hiện KHUNG RỖNG có nhãn thật và lý do, không trả `null` im lặng."
    )


# ═════════════════ 2 · MÀU CHỌN BẰNG BỘ KIỂM, KHÔNG BẰNG MẮT ═════════════════

def test_ba_mau_chuoi_la_ba_bien_khac_nhau_va_khong_trung_mau_vach_nguong():
    """Chỗ hỏng số 2.

    Không canh được ΔE bằng phép thử này — bộ kiểm mù màu chạy lúc dựng. Cái canh được, và cũng
    là cái dễ hỏng về sau, là: ba chuỗi KHÁC màu nhau, và không chuỗi nào trùng màu vạch ngưỡng.
    Một vạch cùng màu với một chuỗi là chỗ người đọc nhìn nhầm vạch thành số.
    """
    css = _ma_css(_doc(CSS))
    mau = {}
    for lop in ("d1", "d2", "d3"):
        m = re.search(r"\.bd-net\." + lop + r"\{stroke:var\((--[a-z-]+)\)\}", css)
        assert m, f"Thiếu màu nét cho chuỗi .{lop}"
        mau[lop] = m.group(1)
    assert len(set(mau.values())) == 3, f"Ba chuỗi phải ba màu khác nhau, đang là {mau}"

    m = re.search(r"\.bd-nguong\{[^}]*dashed var\((--[a-z-]+)\)", css)
    assert m, "Vạch ngưỡng phải là nét ĐỨT, để khác hẳn ba nét liền của ba chuỗi."
    assert m.group(1) not in mau.values(), (
        f"Vạch ngưỡng đang dùng {m.group(1)} — trùng màu một chuỗi. Xem chú thích TC-59 ở BieuDo.tsx."
    )


def test_ghi_lai_vi_sao_khong_dung_bo_mau_cua_ban_mau():
    """Bản mẫu dùng cam · xanh dương · xanh lá. Bộ thật khác — và lý do phải để lại dấu vết.

    Bài học TC-49: một lựa chọn bị đổi mà không ghi lý do thì vòng sau có người đổi nó về, tưởng
    đang sửa cho giống bản mẫu hơn.
    """
    s = _doc(BIEUDO)
    i = s.index("BIỂU ĐỒ ĐƯỜNG (NHIỀU CHUỖI)")
    trich = s[i:i + 3000]
    assert "mù màu" in trich, "Phải ghi vì sao bộ màu khác bản mẫu."
    assert "2,1" in trich, "Ghi cả con số đo được, không chỉ nói chung chung là 'khó phân biệt'."


def test_chu_mang_mau_chu_khong_mang_mau_chuoi():
    """Nhãn số mang màu CHỮ; danh tính nằm ở cái chấm cạnh nó. Chữ tô màu chuỗi thì độ tương phản
    của con số phụ thuộc vào màu của một chuỗi — và một trong ba chuỗi sẽ luôn là chuỗi nhạt nhất."""
    css = _ma_css(_doc(CSS))
    i = css.index(".bd-duong-nhan{")
    than = css[i:css.index("}", i)]
    assert "color:var(--vtos-text)" in than, "Nhãn số phải mang màu chữ, không mang màu chuỗi."


# ═════════════════ 3 · MỘT TRỤC TUNG, IN HAI LẦN ═════════════════

def test_hai_mep_doc_tu_cung_mot_mang_moc():
    """Chỗ hỏng số 3 — luật 4 của bộ biểu đồ là luật khó nhất của hình này."""
    ma = _ma_tsx(_doc(BIEUDO))
    i = ma.index("export function BieuDoDuong(")
    than = ma[i:]
    assert than.count("const mocs = mocTruc(") == 1, (
        "Chỉ được tính mốc trục MỘT lần. Hai lời gọi `mocTruc` là hai thang đo, dù hôm nay chúng "
        "tình cờ ra cùng kết quả."
    )
    # Cả hai cột mép đều duyệt trên `mocs`, không cột nào có mảng riêng.
    assert than.count("mocs.map((m) => (") >= 2, "Mép phải phải in lại CHÍNH mảng `mocs` của mép trái."
    assert "doi_xung" in than, "Mép phải là tuỳ chọn, không phải mặc định."


def test_nhan_truc_dat_theo_dung_chieu_cao_vach_luoi():
    """Nhãn mốc phải đặt tuyệt đối theo `pct(m)`, không xếp đều bằng flex.

    Xếp đều chỉ trùng khi các mốc cách đều nhau; `mocTruc` có thể trả mốc đầu lệch khi có giá trị
    âm, và lúc ấy nhãn lệch khỏi vạch — người đọc tin nhãn. Tìm ra bằng cách dựng ảnh ở vòng này.
    """
    ma = _ma_tsx(_doc(BIEUDO))
    i = ma.index("export function BieuDoDuong(")
    than = ma[i:]
    assert 'className="bd-duong-truc"' in than
    assert than.count("bottom: `${pct(m)}%`") >= 2, (
        "Cả hai cột mốc phải định vị theo `pct(m)` — cùng phép tính với vạch lưới."
    )


# ═════════════════ 4 · MỘT PHÉP CỘNG, KHÔNG PHẢI HAI ═════════════════

def test_thu_chi_tung_tuan_lay_tu_cung_mot_nguon_voi_hai_o_tong():
    """Chỗ hỏng số 4 và số 5 cùng một lúc."""
    ma = _ma_py(_doc(BANG))
    i = ma.index('out["sections"]["du_bao_13_tuan"]')
    khoi = ma[i:i + 1400]
    assert '"thu": w.get("total_in")' in khoi and '"chi": w.get("total_out")' in khoi, (
        "Từng tuần phải lấy `total_in` / `total_out` — ĐÚNG hai trường mà `tong_thu` / `tong_chi` "
        "cộng lên. Lấy trường khác là hai ô tổng và mười ba điểm của hình nói hai chuyện."
    )
    assert 'sum(float(w.get("total_in") or 0) for w in fc["weeks"])' in khoi, (
        "Ô tổng vẫn cộng trên CÙNG `fc[\"weeks\"]`, không có nguồn thứ hai."
    )
    assert "closing" not in khoi.split('"thu"')[1][:200], (
        "Không được suy `thu` từ hiệu hai số dư liền nhau: hiệu ấy là thu TRỪ chi."
    )


def test_man_hinh_khong_tu_suy_thu_chi():
    """Màn hình chỉ ĐỌC `thu` / `chi` máy chủ gửi. Ranh giới 09/9: máy chủ tính, màn hình bày."""
    ma = _ma_tsx(_doc(KHOI))
    i = ma.index("function Hinh13Tuan(")
    than = ma[i:ma.index("\n}", i)]
    assert 'chuoi("thu")' in than and 'chuoi("chi")' in than and 'chuoi("so_du")' in than
    for dau in ("-", "+"):
        assert f"so_du{dau}" not in than.replace(" ", ""), (
            "Không tính thu/chi từ số dư ở trình duyệt."
        )


# ═════════════════ 5 · MỘT KHUNG, KHÔNG PHẢI BA MẢNH ═════════════════


# ═════════════════ 6 · ĐÚNG HAI HÀNG, VÀ BA CÂU CHÚ THÍCH ĐÃ ĐI ═════════════════

def test_dai_chu_thich_dung_HAI_hang_khong_hon():
    """TC-60 (chiều 17/9/2026): "em xoa nhung chú thich này, va gom lại thành 2 hàng ở dưới biểu
    đồ cho gọn".

    Canh ĐÚNG HAI, không phải "ít hàng": ba hàng vẫn gọn hơn bản cũ nên sẽ lọt qua nếu chỉ canh
    "ít đi". Hai hàng chia theo SỐ / THAO TÁC — thêm một hàng thứ ba là đã phá cách chia ấy.
    """
    ma = _ma_tsx(_doc(KHOI))
    i = ma.index('className="dt-chan"')
    dai = ma[i:ma.index("<BonMocDuBao", i)]
    # Hàng 1 do `DayDuBao` dựng, hàng 2 viết thẳng ở đây — nên đếm ở hai chỗ, và cả hai phải là MỘT.
    assert "<DayDuBao" in dai, "Hàng 1 là con số đáy dự báo."
    assert dai.count('className="dt-hang') == 1, (
        "Ngoài hàng do `DayDuBao` dựng, dải chú thích chỉ được có ĐÚNG MỘT hàng nữa. Ba hàng vẫn "
        "gọn hơn bản cũ nên sẽ lọt qua nếu chỉ canh 'ít đi' — nên canh đúng con số."
    )
    assert "dt-kieu" in dai and "Xuất Excel" in dai, "Hàng 2 là thao tác."

    j = ma.index("function DayDuBao(")
    than = ma[j:ma.index("\n}", j)]
    assert than.count('"dt-hang') == 1, (
        "`DayDuBao` phải dựng ĐÚNG MỘT hàng — nó là hàng 1, không còn là một khối hai dòng như "
        "trước TC-60."
    )


def test_ba_cau_chu_thich_da_xoa():
    """Đúng ba câu anh Tuấn khoanh trong ảnh gửi 17/9/2026."""
    ma = _ma_tsx(_doc(KHOI))
    assert "cau_pham_vi" not in ma, (
        "Câu 'Bảng này gồm toàn bộ dòng tiền của pháp nhân đang xem' đã bỏ — đầu màn hình đã ghi "
        "'Phạm vi: Vietourist — công ty mẹ'."
    )
    assert "một phép cân" not in ma, "Câu 'Bốn con số là một phép cân…' đã bỏ."
    assert "một thang đo in hai lần" not in ma, "Câu chân của biểu đồ đã bỏ."
    i = ma.index("<BieuDoDuong")
    assert "chan={" not in ma[i:ma.index("/>", i)], "Biểu đồ không còn câu chân."


def test_con_so_nguong_khong_bien_mat_theo_cau_chu_thich():
    """Bỏ một câu chữ là gọn; làm mất một CON SỐ là chuyện khác.

    Câu chân cũ là chỗ duy nhất in giá trị ngưỡng dự phòng. Bỏ nó mà không chuyển con số đi đâu
    thì trên cả màn hình còn lại một vạch đứt không ai biết ở mức nào.
    """
    ma = _ma_tsx(_doc(BIEUDO))
    i = ma.index('className="bd-nguong"')
    quanh = ma[i:i + 300]
    assert "title=" in quanh and "moc.nhan" in quanh and "moc.gt" in quanh, (
        "Vạch ngưỡng phải mang nhãn rê chuột gồm TÊN và GIÁ TRỊ của nó."
    )


def test_lop_css_mo_coi_da_xoa_theo():
    """Cùng bài học với hàm `O` gỡ ở TC-57: một lớp không ai gọi vẫn qua mọi phép kiểm, và vòng
    sau có người dựng lại cái nó tạo kiểu chỉ vì thấy lớp còn nằm đó."""
    css = _ma_css(_doc(CSS))
    for lop in (".dt-dubao-chan{", ".dt-tomtat{", ".dt-day-phu{", ".dt-dubao{"):
        assert lop not in css, f"Lớp mồ côi {lop[:-1]} phải xoá cùng với thứ nó tạo kiểu."


def test_hinh_chu_thich_bon_moc_nam_trong_mot_khung_dung_thu_tu():
    """Chỗ hỏng số 6 — đúng chữ anh Tuấn dùng: gộp lại cho gọn, nối liền."""
    ma = _ma_tsx(_doc(KHOI))
    i = ma.index('className="dt-gop"')
    j = ma.index("</section>", i)
    khung = ma[i:j]
    for ten in ("<Hinh13Tuan", 'className="dt-chan"', "<BonMocDuBao"):
        assert ten in khung, f"{ten} phải nằm TRONG khung gộp."
    assert khung.index("<Hinh13Tuan") < khung.index('className="dt-chan"') < khung.index("<BonMocDuBao"), (
        "Thứ tự: HÌNH trước, chú thích sau, bốn mốc cuối. Đặt chữ lên trước là bắt người đọc đọc "
        "chú thích của một hình họ chưa nhìn thấy."
    )
    assert "<DayDuBao" in khung, (
        "Con số đáy dự báo là điểm thấp nhất của chính đường TỒN — nó thuộc về dải chú thích dưới "
        "hình, không đứng riêng phía trên."
    )
    assert khung.index("<DayDuBao") > khung.index("<Hinh13Tuan"), (
        "TC-60: con số đáy là HÀNG 1 của dải chú thích, tức nằm SAU hình."
    )


def test_khung_gop_khong_de_ba_vien_long_nhau():
    """Khung gộp có viền; ba mảnh bên trong KHÔNG có viền riêng — viền lồng viền đọc ra là ba khối."""
    css = _ma_css(_doc(CSS))
    i = css.index(".dt-gop{")
    than = css[i:css.index("}", i)]
    assert "border:1px solid" in than, "Khung gộp phải có đúng MỘT viền."
    assert ".dt-gop .bd{" in css, "Hình bên trong phải bỏ viền riêng của nó."
    j = css.index(".dt-gop .bd{")
    assert "border:0" in css[j:css.index("}", j)]
