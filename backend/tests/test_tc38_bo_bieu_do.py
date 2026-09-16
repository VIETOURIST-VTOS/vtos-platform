# -*- coding: utf-8 -*-
"""TC-38 · Bộ biểu đồ dùng chung + ba khu biểu đồ trên màn hình 01.

Anh Tuấn 15/9/2026 gửi mấy mẫu bảng điều hành (Power BI, dashboard bán hàng) và chốt hai điều:
biểu đồ dựng "đầy đủ — trục, lưới, nhãn số, chú giải", và chia làm ba nhóm: (1) Dòng tiền,
(2) Doanh thu + Lợi nhuận, (3) Nhân sự & Quản trị nội bộ.

BA CHỖ TRONG MẪU ANH GỬI MÀ VTOS CỐ Ý KHÔNG BẮT CHƯỚC — ghi ra đây vì sau này sẽ có người mở mẫu
ra và hỏi "sao không giống":

  · BÁNH TRÒN 10 PHẦN. Mắt người so được độ dài, không so được góc. Mười lát thì phải đọc chú
    thích mới biết lát nào là gì; cùng số ấy vẽ thanh ngang xếp thứ tự là đọc xong trong một giây.
  · ĐƯỜNG CONG MƯỢT. Đường cong vẽ ra những giá trị NẰM GIỮA hai mốc, mà giữa tháng 5 và tháng 6
    không tồn tại số nào. Đó là số do máy vẽ tự sinh ra.
  · HAI TRỤC TUNG TRÊN MỘT BIỂU ĐỒ. Đổi thang trục là đổi được kết luận; hai đường cắt nhau ở đâu
    là do người vẽ chọn, không phải do số liệu.

VÌ SAO MỘT BỘ DÙNG CHUNG: trước vòng này VTOS đã có ba chỗ vẽ cột bằng tay và ba chỗ ấy đã bắt
đầu lệch nhau. Thêm ba khu nữa mà vẫn vẽ tay là sáu bản chép của cùng một phép tính.

Bộ kiểm chạy hoàn toàn trên MÃ NGUỒN màn hình — không cần cơ sở dữ liệu, không cần trình duyệt.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
BD = GOC / "web" / "components" / "BieuDo.tsx"
KHU = GOC / "web" / "components" / "BaKhuBieuDo.tsx"
V14 = GOC / "web" / "components" / "KhoiV14.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
CSS = GOC / "web" / "app" / "globals.css"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _bo_chu_thich_tsx(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", "", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", "", s)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


def _bo_chu_thich_css(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def _than(nguon: str, ten: str) -> str:
    """Thân một hàm, từ chỗ khai tới chỗ khai kế tiếp."""
    i = nguon.index(ten)
    sau = nguon[i + len(ten):]
    ket = [m.start() for m in re.finditer(r"\nexport (?:function|const|type)|\nfunction ", sau)]
    return sau[: ket[0]] if ket else sau


# ═════════════════ NĂM LUẬT VẼ ═════════════════

def test_luat1_rong_khac_khong_o_ca_ba_kieu_bieu_do():
    """Quy `null` thành 0 là nói kỳ ấy doanh thu bằng không; bỏ nó khỏi chuỗi là bóp méo khoảng
    thời gian mà biểu đồ vẫn trông bình thường. Cả ba kiểu đều phải giữ null."""
    t = _bo_chu_thich_tsx(_doc(BD))
    # Cột: lọc ra điểm có số để ĐẾM, nhưng vẫn vẽ trọn `diem` — không vẽ trọn `coSo`.
    cot = _than(t, "export function BieuDoCot")
    assert "diem.map(" in cot, "Biểu đồ cột phải vẽ trọn dãy điểm, kể cả kỳ rỗng."
    assert "bd-khuyet" in cot, "Kỳ rỗng phải ra một ô trống, không bị bỏ qua."
    # Thanh ngang: dòng chưa có số ra khung nét đứt.
    thanh = _than(t, "export function BieuDoThanh")
    assert "bd-th-khuyet" in thanh and "chưa có số" in thanh


def test_luat1_khong_co_phep_quy_doi_null_thanh_0_o_cua_vao():
    """Chỗ dễ phá luật nhất không phải lúc vẽ mà lúc ĐỌC dữ liệu máy chủ: một cái `?? 0` ở đây là
    đủ để mọi luật phía sau thành vô nghĩa, mà biểu đồ vẫn vẽ ra bình thường."""
    t = _bo_chu_thich_tsx(_doc(KHU))
    for xau in ("?? 0", "|| 0"):
        assert xau not in t, f"Có phép quy đổi rỗng thành 0 ở cửa vào dữ liệu: {xau!r}"


def test_luat2_duoi_hai_diem_thi_khong_ve_va_noi_vi_sao():
    """Một cột đứng một mình không so với cái gì cả — nhưng người đọc vẫn sẽ đọc ra một xu hướng."""
    t = _bo_chu_thich_tsx(_doc(BD))
    cot = _than(t, "export function BieuDoCot")
    thanh = _than(t, "export function BieuDoThanh")
    # TC-40: điều kiện vẽ tách ra thành hàm thuần `duVeCot` / `duVeThanh`, vì nơi GỌI cũng phải
    # hỏi được "vẽ nổi không" trước khi quyết bày hay không. Hai bản chép của cùng một điều kiện
    # thì sớm muộn lệch nhau, nên thành phần vẽ phải GỌI đúng hàm ấy chứ không chép lại.
    assert "duVeCot(diem)" in cot, "Biểu đồ cột phải gọi duVeCot, không chép lại điều kiện."
    assert "duVeThanh(hang)" in thanh, "Thanh ngang phải gọi duVeThanh, không chép lại điều kiện."
    assert re.search(r"filter\(\(d\) => d\.gt !== null\)\.length >= 2",
                     _bo_chu_thich_tsx(_than(t, "export function duVeCot"))), (
        "duVeCot phải là đúng luật 'dưới hai điểm có số thì không vẽ'."
    )
    assert "BieuDoRong" in cot and "BieuDoRong" in thanh, "Không vẽ thì phải nói vì sao."


def test_luat3_truc_luon_chua_0():
    """Cắt chân trục làm một chênh lệch 3% trông như gấp đôi. Đây là cách bóp méo phổ biến nhất
    trên các bảng điều hành, và nó không cần ai cố ý."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function mocTruc"))
    assert "Math.min(0, min)" in t and "Math.max(0, max)" in t, (
        "mocTruc phải ép thang đo bao lấy mốc 0 ở cả hai đầu."
    )


def test_luat4_khong_co_truc_tung_thu_hai():
    """Bản vẽ mẫu anh Tuấn gửi có cột tiền kèm đường %. Đổi thang trục là đổi được kết luận, nên
    VTOS tách làm hai biểu đồ. `moc` là MỘT VẠCH trên cùng một trục, không phải một thang thứ hai:
    nó phải được tính bằng chính hàm `y()` của thang chính."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoCot"))
    assert "top: y(moc.gt)" in t, "Vạch mốc phải nằm trên chính thang đo của cột."
    assert t.count("const bien") == 1, "Chỉ được có MỘT thang đo trong một biểu đồ."
    # Thang phải nới ra ôm lấy mốc, chứ không vẽ mốc ngoài khung rồi cắt cụt.
    assert "moc ? moc.gt : 0" in t


def test_luat5_khong_lam_muot_duong():
    """Đường cong mượt vẽ ra những giá trị nằm giữa hai mốc, mà giữa hai tháng không có số nào."""
    t = _bo_chu_thich_tsx(_doc(BD)).lower()
    for xau in ("curve", "bezier", "spline", "smooth", "cubic-bezier(", "catmull"):
        assert xau not in t, f"Có dấu vết làm mượt đường: {xau}"


# ═════════════════ THANG ĐO & ĐỊNH DẠNG ═════════════════

def test_buoc_truc_chi_lay_1_2_5_nhan_luy_thua_10():
    """Bước lẻ (ví dụ 3.700.000) thì nhãn trục toàn số lẻ và không ai ước lượng được cột cao bao
    nhiêu chỉ bằng mắt."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "function buoc"))
    assert re.search(r"ty <= 1 \? 1 : ty <= 2 \? 2 : ty <= 5 \? 5 : 10", t)


def test_dinh_dang_dem_khong_bao_gio_doi_ra_ty_hay_trieu():
    """412 hồ sơ mà in ra '0,4 ng' thì con số hết còn là con số."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function gonSo"))
    i_dem = t.index('dd === "dem"')
    i_ty = t.index("1e9")
    assert i_dem < i_ty, "Nhánh 'đếm' phải trả về trước khi chạm tới nhánh rút gọn tỷ/triệu."


def test_ti_le_khong_in_hai_lan():
    """Đo trên bản dựng: thanh cơ cấu 'Báo cáo ngày' in ra '63% 63%' vì số gốc ĐÃ là tỉ lệ, mà
    thanh vẫn in thêm phần trăm tính từ tổng. Và dòng 'Tổng 100%' là câu thừa: một tỉ lệ thì
    đương nhiên cộng đủ 100%."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoCoCau"))
    assert t.count('dinh_dang !== "phan_tram"') >= 2, (
        "Cả số gốc lẫn dòng tổng đều phải tắt khi bản thân dữ liệu đã là tỉ lệ."
    )


# ═════════════════ THANH CƠ CẤU ═════════════════

def test_co_cau_doi_du_moi_phan_moi_ve():
    """Mọi tỉ lệ đều tính trên tổng các phần. Thiếu một phần thì tổng đã sai, và các phần còn lại
    cùng phình to lên — nhìn vẫn rất hợp lý, nên không ai kiểm được."""
    t = _than(_doc(BD), "export function BieuDoCoCau")
    assert "thieu.length" in t
    assert "không quy đổi phần thiếu thành 0" in t


def test_co_cau_tu_choi_phan_am_va_noi_ro_tong_0_la_so_that():
    t = _than(_doc(BD), "export function BieuDoCoCau")
    assert re.search(r"some\(\(v\)\s*=>\s*v\s*<\s*0\)", _bo_chu_thich_tsx(t))
    assert "tong === 0" in t and "Đây là số THẬT" in t


def test_be_rong_khuc_dat_bang_flex_grow_khong_phai_phan_tram():
    """Các khúc cách nhau 2px. Các bề rộng phần trăm cộng đúng 100% thì tổng cả gap vượt khung và
    khúc CUỐI bị cắt cụt — tức phần cuối luôn trông nhỏ hơn sự thật."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoCoCau"))
    assert "flexGrow" in t and "flexBasis: 0" in t
    assert "width:" not in t


def test_dai_mau_mot_sac_dam_dan_va_mau_trang_thai_tach_rieng():
    """Các phần của một tổng là các nấc của CÙNG một thứ, nên phải trông như một dải liên tục.
    Năm màu rời nói đây là năm loại khác nhau. Riêng phần TRẠNG THÁI (quá hạn, còn thiếu) mang màu
    cảnh báo vì nó không nằm trên cùng cái thước với các nấc kia."""
    c = _bo_chu_thich_css(_doc(CSS))
    dam = [float(m) for m in re.findall(r"\.bd-mau-\d\{opacity:([\d.]+)\}", c)]
    assert len(dam) == 5, f"Phải đủ năm nấc, đang có {len(dam)}"
    assert dam == sorted(dam, reverse=True), f"Độ đậm phải giảm dần, đang là {dam}"
    assert re.search(r"\.bd-mau-tt\{background:var\(--vtos-danger\)", c)


# ═════════════════ THANH NGANG ═════════════════

def test_ba_cot_thanh_ngang_rong_co_dinh_de_moi_dong_chung_mot_thuoc():
    """Lỗi ĐÃ ĐO ở vòng trước: để cột tên và cột số co theo nội dung thì dòng có số bốn chữ số bị
    rãnh hẹp hơn dòng ba chữ số (882,5px so với 891,8px). Mỗi dòng đo trên một cái thước khác
    nhau mà nhìn vẫn hoàn toàn bình thường — đúng loại sai không ai kiểm được."""
    c = _bo_chu_thich_css(_doc(CSS))
    m = re.search(r"\.bd-th-hang\{[^}]*grid-template-columns:([^;]+);", c)
    assert m, "Không tìm thấy khai cột của .bd-th-hang"
    cot = m.group(1)
    assert "auto" not in cot, f"Cột co theo nội dung làm lệch thước giữa các dòng: {cot}"
    assert "minmax(0,1fr)" in cot, "Chỉ cột rãnh được co giãn."


def test_chua_co_so_nam_trong_rai_khong_nam_o_cot_so():
    """Hệ quả trực tiếp của phép đo trên: câu 'chưa có số' dài hơn mọi con số."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoThanh"))
    rai = t[t.index("bd-th-rai"): t.index("bd-th-so")]
    assert "chưa có số" in rai


def test_bang_0_thi_rong_dung_0():
    """0 là tin tốt và phải trông đúng như tin tốt. Kéo lên vài pixel 'cho dễ nhìn' là nói có số."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoThanh"))
    assert re.search(r"h\.gt === 0 \? 0 :", t)


def test_dong_chua_co_so_don_xuong_cuoi_khong_coi_nhu_0():
    """Xếp theo độ lớn thì một dòng chưa ai đếm không có chỗ nào trong thứ tự ấy. Nhét nó xuống
    cuối THEO SỐ 0 là gán cho nó một giá trị nó không có."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function xepThanh"))
    assert "a.gt === null" in t and "b.gt === null" in t


def test_dong_nhan_phu_luon_dung_cuoi_va_mang_mau_khac():
    """'Chưa rõ bộ phận' KHÔNG phải một phòng. Tô cùng màu là xếp một chỗ chưa ai nhận ngang hàng
    với một phòng có người chịu trách nhiệm."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function xepThanh"))
    assert "nhan_phu" in t and "[...chinh,...phu]" in t.replace(" ", "")
    c = _bo_chu_thich_css(_doc(CSS))
    assert re.search(r"\.bd-th-thanh\.phu\{background:var\(--vtos-warning\)", c)


def test_thanh_am_ve_ve_ben_trai_moc_0():
    """Vẽ mọi thanh từ mép trái khi có số âm là biến một khoản lỗ thành một thanh ngắn trông như
    khoản lãi ít tiền."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoThanh"))
    assert "bd-th-truc0" in t, "Có số âm thì phải vẽ ra mốc 0."
    assert "h.gt < 0" in t and "right:" in t


# ═════════════════ Ô RỖNG PHẢI CÓ LỜI VÀ CÓ CHỦ ═════════════════

def test_o_rong_luon_noi_vi_sao():
    """Một khung xám không lời thì người đọc kết luận hệ thống hỏng — mà sự thật thường là chưa ai
    nhập, tức một việc có chủ."""
    t = _bo_chu_thich_tsx(_than(_doc(BD), "export function BieuDoRong"))
    assert "vi_sao" in t and "bd-rong-ly" in t


def test_bieu_do_chua_du_so_thi_tra_null_chu_khong_tra_khung_rong():
    """TC-40 (anh Tuấn chốt 15/9/2026) · Ô SỐ ĐÃ NÓI RỒI THÌ BIỂU ĐỒ ĐỪNG NÓI LẠI.

    Trước vòng này mỗi biểu đồ chưa đủ số vẫn dựng ra một khung ghi "chưa có số, bộ phận X nạp".
    Nhưng biểu đồ nằm NGAY TRONG khối của nó, và ô số ngay trên đã ghi đúng câu ấy kèm bộ phận và
    cửa nhập. Hai khung nói cùng một chuyện, cách nhau 40px.

    Nên `bieuDoCua` trả `null`, và khối chỉ hiện ô số. Ranh giới 09/9 không hề bị nới: chỗ chưa có
    số VẪN đọc được từ màn hình — nó nằm ở ô số, chỗ đúng của nó."""
    t = _bo_chu_thich_tsx(_doc(KHU))
    so_bd = len(re.findall(r"<BieuDo(?:Cot|Thanh|CoCau)\b", t))
    so_null = len(re.findall(r"\n\s*: null,", t))
    # SỬA 16/9/2026 (TC-42): hai biểu đồ CỘT theo kỳ (doanh thu, lợi nhuận) rời tệp này sang
    # components/KhoiSauO.tsx cùng hai Ô LỚN của chúng — nên bộ này còn NĂM. Luật thì không đổi
    # một chữ, và nó nằm ở phép so bên dưới: mỗi biểu đồ phải có đúng một nhánh trả `null`.
    assert so_bd >= 5, f"Bộ biểu đồ phải đủ dùng cho các khối, đang đếm {so_bd}"
    assert so_null == so_bd, (
        f"{so_bd} biểu đồ nhưng chỉ {so_null} nhánh trả null. Mỗi biểu đồ phải có nhánh 'chưa đủ "
        f"số thì trả null' — trả một khung rỗng là nói lại điều ô số đã nói."
    )
    # TC-42: `duVeCot` theo hai biểu đồ cột sang KhoiSauO.tsx, nên tệp này chỉ còn hai hàm hỏi.
    # Luật là "hỏi qua hàm thuần, không viết lại điều kiện tại chỗ" — nên canh CẢ HAI tệp, thay vì
    # nới lỏng cho tệp này.
    assert "duVeCoCau(" in t and "duVeThanh(" in t, (
        "Điều kiện vẽ phải hỏi qua hàm thuần của bộ biểu đồ, không viết lại tại chỗ."
    )
    sau_o = _bo_chu_thich_tsx(
        (GOC / "web" / "components" / "KhoiSauO.tsx").read_text(encoding="utf-8"))
    assert "duVeCot(" in sau_o and "duVeCoCau(" in sau_o, (
        "Hai Ô LỚN theo kỳ và ô Tồn đọng cũng phải hỏi qua hàm thuần, không tự xét điều kiện vẽ."
    )


# ═════════════════ BA KHU TRÊN MÀN HÌNH 01 ═════════════════

def test_khong_con_khu_bieu_do_rieng_va_khong_danh_so():
    """Anh Tuấn chốt 15/9/2026: "chỉ dùng biểu đồ cho 1 loại duy nhất, ko dùng biểu đồ 1, biểu đồ
    2...". Ba khu đánh số đã bỏ; biểu đồ về nằm trong khối của nó."""
    # Bỏ chú thích trước khi soi: mã NÊN kể lại đường đi ba vòng (TC-37 → TC-38 → TC-40) để vòng
    # sau không dựng lại khu đánh số với cùng một lý do. Cái không được phép là còn dấu vết trong
    # THỨ HIỆN RA MÀN HÌNH.
    t = _bo_chu_thich_tsx(_doc(KHU)) + _bo_chu_thich_tsx(_doc(TRANG))
    for xau in ("Biểu đồ 1", "Biểu đồ 2", "Biểu đồ 3", "<Khu so=", "khu-bieu-do"):
        assert xau not in t, f"Còn dấu vết khu biểu đồ đánh số: {xau!r}"


def test_bieu_do_nam_TRONG_khoi_cua_no():
    """TC-40 · MỘT CON SỐ — MỘT CHỖ — MỘT HÌNH.

    Đường đi ba vòng đáng ghi lại: TC-37 vẽ trong khối → TC-38 gom ra ba khu riêng → TC-40 đưa về.
    Gom ra khu riêng nghe rất hợp lý ("khu biểu đồ" là thứ bảng điều hành nào cũng có), nhưng trên
    bản chạy thật nó tách CON SỐ khỏi HÌNH của chính con số ấy, và người đọc phải cuộn qua lại để
    ghép hai thứ vốn là một. Anh Tuấn nhìn ra ngay: "các mục lặp lại khá nhiều".
    """
    trang = _bo_chu_thich_tsx(_doc(TRANG))
    assert "bieuDoCua(sec)" in trang, "Trang phải dựng bộ biểu đồ một lần rồi giao cho từng khối."
    for khoi, khoa in (("<KhoiPhaiThu", "bd.phai_thu"), ("<KhoiPhaiTra", "bd.phai_tra"),
                       ("<KhoiKinhDoanhLe", "bd.kd_le"), ("<KhoiKinhDoanhDoan", "bd.kd_doan"),
                       ("<KhoiBaoCaoNgay", "bd.bao_cao_ngay")):
        assert khoi in trang, f"Màn hình 01 thiếu khối {khoi}"
        assert khoa in trang, f"Khối {khoi} chưa nhận biểu đồ của nó ({khoa})."
    # Khối V14 không tự vẽ nữa — nó NHẬN hình qua prop. Tự vẽ là bản chép thứ hai của cùng phép tính.
    v14 = _bo_chu_thich_tsx(_doc(V14))
    for xau in ("ThanhCoCau", "BieuDoBoPhan", "v14-cc-o", "v14-bp-"):
        assert xau not in v14, f"Khối V14 còn tự vẽ biểu đồ: {xau}"
    assert "bieu_do" in v14, "Khối V14 phải nhận biểu đồ qua prop."


def test_khoi_dong_tien_dung_bo_bieu_do_chung():
    """Anh Tuấn 15/9/2026: "dòng tiền rất quan trọng, cần có số và biểu đồ phân tích".

    Bản vẽ tay cũ trong KhoiDongTien đúng về hình nhưng là bản chép THỨ TƯ của cùng một phép tính
    trục — và bốn bản chép thì sớm muộn lệch nhau. Nay gọi bộ chung, và thêm một câu đọc hộ nói
    mốc nào âm sớm nhất, thiếu bao nhiêu."""
    dt = _bo_chu_thich_tsx(_doc(GOC / "web" / "components" / "KhoiDongTien.tsx"))
    assert "BieuDoCot" in dt, "Khối dòng tiền phải dùng bộ biểu đồ chung."
    assert "dt-bd-thanh" not in dt, "Bản vẽ tay cũ còn sót lại."
    assert "docHoDongTien" in dt, "Thiếu câu đọc hộ cho khối quan trọng nhất màn hình."


def test_cau_doc_ho_khong_tu_tinh_chi_tieu_moi():
    """Câu đọc hộ chỉ ĐỌC LẠI số máy chủ gửi: mốc nào âm, thiếu bao nhiêu. Nó không cộng, không
    chia, không suy ra một chỉ tiêu nào — ranh giới 09/9 giữ nguyên."""
    dt = _doc(GOC / "web" / "components" / "KhoiDongTien.tsx")
    than = dt[dt.index("function docHoDongTien"): dt.index("/** Bốn mốc dòng tiền thuần.")]
    assert "Math.abs" in than, "Được phép lấy trị tuyệt đối để đọc thành chữ."
    for phep in (" / ", " * "):
        assert phep not in _bo_chu_thich_tsx(than), f"Câu đọc hộ đang tự tính: {phep!r}"


def test_khoi_van_giu_ti_le_bang_CHU_o_o_so():
    """Bỏ hình không có nghĩa là bỏ thông tin: tỉ lệ từng nhóm là CHỮ, đọc ngay tại ô số, và nó
    không trùng với biểu đồ nào cả."""
    t = _bo_chu_thich_tsx(_doc(V14))
    assert "v14-han-ty" in t and "cc.ve &&" in t


def test_man_hinh_khong_tu_tinh_con_so_nghiep_vu_nao():
    """Ranh giới 09/9: Claude viết cấu trúc và phép tính ở MÁY CHỦ, màn hình chỉ bày. Ngoại lệ duy
    nhất là tách tỉ lệ nộp thành hai vế, và chỗ ấy phải ghi rõ ngay tại chỗ."""
    t = _bo_chu_thich_tsx(_doc(KHU))
    cong = re.findall(r"[a-zA-Z_\].]\s[+\-*/]\s[a-zA-Z_(]", t)
    assert len(cong) <= 1, f"Có phép tính lạ trên màn hình: {cong}"
    assert "phép tính DUY NHẤT" in _doc(KHU), "Ngoại lệ phải được ghi rõ trong mã."


# ═════════════════ BỘ NHẬN DIỆN & IN GIẤY ═════════════════

def test_khong_dung_mau_go_thang():
    c = _bo_chu_thich_css(_doc(CSS))
    la = set(re.findall(r"#[0-9a-fA-F]{3,8}", c))
    assert la <= {"#fff"}, f"Màu gõ thẳng ngoài chú thích: {sorted(la)}"
    for p in (BD, KHU):
        t = _bo_chu_thich_tsx(_doc(p))
        assert not re.search(r"#[0-9a-fA-F]{3,8}", t), f"{p.name} có mã màu gõ thẳng."


def test_bieu_do_in_ra_giay_duoc():
    """Bản vẽ có nút In / Lưu PDF vì Chủ tịch mang bảng này vào phòng họp. Mất màu cột thì biểu đồ
    thành một khung trắng vô nghĩa."""
    c = _doc(CSS)
    khoi_in = c[c.rindex("@media print"):]
    assert "print-color-adjust:exact" in khoi_in
    assert "break-inside:avoid" in khoi_in


def test_khong_ve_banh_tron():
    """Mắt so được độ dài, không so được góc."""
    for p in (BD, KHU):
        t = _bo_chu_thich_tsx(_doc(p)).lower()
        for xau in ("conic-gradient", "border-radius:50%", "doughnut", "<pie"):
            assert xau not in t, f"{p.name} có dấu vết bánh tròn: {xau}"
