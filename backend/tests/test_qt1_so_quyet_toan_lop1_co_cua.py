# -*- coding: utf-8 -*-
"""QT-1 · Sổ quyết toán tour lớp 1 phải có lối vào — và phải nằm TRONG /lai-lo-tour.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHUYỆN ĐÃ XẢY RA
═══════════════════════════════════════════════════════════════════════════════════════════════
Đo ngày 29/9/2026 trên bản main: bảng `tour_settlements` và SÁU cửa `/api/v1/quyet-toan-tour/**`
có đủ từ 10/9, mà KHÔNG màn hình nào gọi tới. Mục 4.5 "Quyết toán tour" của cây phân hệ trỏ về
`/tours` — người cần xem sổ bị đẩy sang danh sách chuyến, nơi không có hai hàng đợi của sổ này.
Sáu cửa sống không có lối vào là VIỆC CÒN THIẾU theo ranh giới Chủ tịch đặt 09/9/2026.

Hàng rào P11 không bắt được vì nó canh chiều ngược lại (khai quyền cho màn hình chưa có). Bộ kiểm
menu cũng không, vì mục 4.5 CÓ href — chỉ là href sai chỗ. Tệp này canh đúng khoảng trống ấy.

VÌ SAO NẰM TRONG /lai-lo-tour CHỨ KHÔNG PHẢI MỘT TRANG RIÊNG: bản nháp đầu dựng trang
`/quyet-toan-tour`, và `test_lop1_stt_gia_ban_va_man_hinh_lop2` đỏ ngay. Nó đỏ ĐÚNG — kho này từng
có bốn công thức lãi lỗ tour chạy song song, hai trang trông giống nhau thì sinh cái thứ năm. Anh
Tuấn chọn gắn vào màn hình sẵn có và KHÔNG nới hàng rào cũ một dòng nào. Phép thử ở đây canh cho
lựa chọn ấy không bị lặng lẽ đảo ngược về sau.
"""
import os, re, sys, pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test_qt1.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_qt1.db", "test_qt1.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = pathlib.Path(__file__).resolve().parents[2]
CUA = GOC / "backend" / "app" / "api" / "v1" / "quyet_toan_tour.py"
MAN = GOC / "web" / "app" / "lai-lo-tour" / "page.tsx"
CAY = GOC / "web" / "lib" / "cay_phan_he.ts"


def _bo_chu_thich(src: str) -> str:
    """Soi MÃ chứ không soi lời kể về mã — cùng một lý do đã ghi ở test_lop1."""
    src = re.sub(r"\{/\*.*?\*/\}", " ", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def test_qt1_1_nam_cua_lam_viec_deu_co_man_hinh_goi_toi():
    """Đọc THẲNG tệp cửa để lấy danh sách, không chép lại vào đây: chép là dựng bản sao thứ hai
    của sự thật, và bản sao sẽ cũ đi đúng lúc ai đó thêm cửa thứ bảy mà quên màn hình.

    NĂM chứ không phải sáu, và con số ấy có lý do đo được — xem phép thử ngay dưới."""
    duong = [d for _m, d in re.findall(r'@router\.(get|post)\("([^"]*)"', CUA.read_text(encoding="utf-8"))]
    assert len(duong) == 6, f"Số cửa của sổ quyết toán đã đổi: {duong}"

    man = _bo_chu_thich(MAN.read_text(encoding="utf-8"))
    thieu = []
    for d in duong:
        if d.endswith("/chi-tiet"):
            continue                      # cửa trùng, xem test_qt1_1b
        mau = [x for x in re.split(r"\{[^}]*\}", "/quyet-toan-tour" + d) if len(x.strip("/")) > 2]
        if not all(x in man for x in mau):
            thieu.append(f"{d or '(danh sách)'} → thiếu {[x for x in mau if x not in man]}")
    assert not thieu, "Cửa chưa có lối vào: " + "; ".join(thieu)


def test_qt1_1b_cua_chi_tiet_la_cua_TRUNG_nen_co_y_khong_co_man_hinh():
    """Cửa thứ sáu `/{sid}/chi-tiet` KHÔNG thiếu màn hình — nó TRÙNG.

    Đo ngày 29/9/2026: thân cửa ấy gọi thẳng `lai_lo_tour._ban_quyet_toan`, tức là trả về ĐÚNG cái
    mà lớp 2 của /lai-lo-tour đã trả. Dựng thêm một lối vẽ nữa cho cùng một khối dữ liệu là đúng
    hình mà `test_lop1_stt_gia_ban_va_man_hinh_lop2` cấm, chỉ khác là lần này ở tầng API.

    Nên phép thử này KHÔNG đòi màn hình cho nó. Nó ghim lại LÝ DO, để lần đo sau đừng đếm cửa này
    vào "việc còn thiếu", và để nếu một ngày thân cửa thôi gọi `_ban_quyet_toan` — tức là nó bắt
    đầu trả một thứ KHÁC — thì phép thử đỏ và có người phải quyết lại."""
    src = CUA.read_text(encoding="utf-8")
    than = src[src.index('/{sid}/chi-tiet'):]
    assert "_ban_quyet_toan" in than, (
        "Cửa /{sid}/chi-tiet thôi trả bản quyết toán của lớp 2 — nó không còn là cửa trùng nữa, "
        "nên phải quyết lại: hoặc cho nó một màn hình, hoặc bỏ nó đi.")


def test_qt1_2_cua_nhap_gia_von_chan_so_khong_ngay_tren_man_hinh():
    """Cột `gia_von` để NULL được — đó là toàn bộ lý do bảng `tour_settlements` tồn tại riêng thay
    vì ghi vào `tours` (76 dòng doanh thu 2,65 tỷ từng có giá vốn 0 và sổ vẫn cân). Ghi 0 vào đây
    là xoá mất sự phân biệt ấy. Máy chủ đã chặn; màn hình chặn thêm một lớp để người khỏi mất một
    vòng gọi — hai lớp là cố ý, không phải thừa."""
    man = _bo_chu_thich(MAN.read_text(encoding="utf-8"))
    assert re.search(r"if\s*\(\s*!\s*\(\s*v\s*>\s*0\s*\)\s*\)", man), \
        "Màn hình phải chặn giá vốn ≤ 0 TRƯỚC khi gọi cửa."
    assert "PHÂN LOẠI" in man, "Câu chặn phải chỉ sang cửa PHÂN LOẠI, nếu không người dùng bế tắc."


def test_qt1_3_khoi_so_an_voi_vai_ma_cua_khong_nhan():
    """Màn hình /lai-lo-tour mở RỘNG HƠN cửa quyết toán (có sales_admin, robot_ks). Vẽ khối sổ cho
    mọi người là cho hai vai ấy một khối luôn báo 403 — người dùng không phân biệt được 'không có
    quyền' với 'màn hình hỏng'."""
    from app.services import access as AC
    doc = re.search(r'^READ\s*=\s*\(([^)]*)\)', CUA.read_text(encoding="utf-8"), re.M)
    assert doc, "Không tìm thấy tuple READ trong api/v1/quyet_toan_tour.py"
    vai_cua = {x.strip().strip('"') for x in doc.group(1).split(",") if x.strip()}

    man = _bo_chu_thich(MAN.read_text(encoding="utf-8"))
    m = re.search(r"const\s+VAI_DOC_SO\s*=\s*\[([^\]]*)\]", man)
    assert m, "Màn hình phải khai hằng số VAI_DOC_SO để lọc khối sổ"
    vai_man = {x.strip().strip('"') for x in m.group(1).split(",") if x.strip()}
    assert vai_man == vai_cua, (
        f"VAI_DOC_SO lệch tuple READ của cửa. Chỉ màn hình có: {sorted(vai_man - vai_cua)}; "
        f"chỉ cửa có: {sorted(vai_cua - vai_man)}")
    assert "doc_so &&" in man, "Khối sổ phải bị ẩn khi vai không đọc được"

    # Và phần dôi ra phải được KHAI RA ở bản đồ quyền, không để người sau phải suy từ mã giao diện.
    assert "/api/v1/quyet-toan-tour" in AC.MAN_HINH_API["/lai-lo-tour"], \
        "Nhóm API của sổ quyết toán phải khai vào MAN_HINH_API['/lai-lo-tour']"


def test_qt1_4_khong_nhan_ban_bon_mat_len_khoi_so():
    """Bốn mặt chi tiết chỉ được có MỘT chỗ. Nhân bản lên khối sổ là dựng lại đúng cái mà
    `test_lop1_stt_gia_ban_va_man_hinh_lop2` cấm, chỉ khác là lần này trong cùng một tệp nên hàng
    rào ấy không thấy."""
    man = _bo_chu_thich(MAN.read_text(encoding="utf-8"))
    khoi = man[man.index("function SoQuyetToan"):man.index("function LaiLoTour")]
    for mat in ("chiet_tinh", "hdv_chi", "so_dong_khach", "chi-tiet"):
        assert mat not in khoi, (
            f"Khối sổ lớp 1 KHÔNG được vẽ lại mặt “{mat}” — bốn mặt nằm ở lớp 2 bên dưới, "
            "mở theo từng chuyến.")


def test_qt1_5_cay_phan_he_thoi_tro_ve_tours():
    """Mục 4.5 đã có màn hình thật thì phải trỏ vào đó. Để nguyên /tours là giữ lại đúng cái lỗi
    vừa sửa, và lần đo sau sẽ lại kết luận 'đã có màn hình' vì mã 4.5 có href."""
    dong = [d for d in CAY.read_text(encoding="utf-8").splitlines() if 'ma: "4.5"' in d]
    assert dong, "Không tìm thấy mục 4.5 trong cây phân hệ"
    assert "/lai-lo-tour" in dong[0], f"Mục 4.5 vẫn chưa trỏ về màn hình thật: {dong[0].strip()}"
