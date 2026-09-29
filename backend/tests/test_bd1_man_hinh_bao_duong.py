# -*- coding: utf-8 -*-
"""BD-1 · Bảo dưỡng & sửa chữa phải có màn hình, và ngưỡng chỉ được có MỘT bản.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHUYỆN ĐÃ XẢY RA
═══════════════════════════════════════════════════════════════════════════════════════════════
Bảng `fleet_maintenance`, hai cửa `GET/POST /api/v1/fleet/bao-duong` và thuật toán `moc_bao_duong()`
có từ Đợt 1 đội xe. Đo ngày 29/9/2026: KHÔNG màn hình nào gọi tới, và mục 4.9.6 "Bảo dưỡng & sửa
chữa" của cây phân hệ không có đường dẫn. Đội xe không có chỗ nhập lịch bảo dưỡng, trong khi bộ
điều kiện phát lệnh điều xe vẫn CHẶN xe vượt mốc — tức là máy chặn bằng một con số mà không ai có
cửa để cập nhật.

Và một chỗ hở thứ hai, sâu hơn: luật ngưỡng ("vượt mốc" / "sắp tới mốc") chỉ nằm BÊN TRONG
`kiem_tra()`, nên nó chỉ trả lời được khi đang lập một lệnh cụ thể. Câu "cả đội xe, xe nào sắp tới
hạn" — câu người quản đội hỏi mỗi sáng — không có ai trả lời. Cách sai mà người sau dễ chọn là để
màn hình tự so `odo_km` với mốc; làm thế là dựng công thức thứ hai cho cùng một ngưỡng, và ngày ai
đó đổi tham số `xe_bd_gap_km` thì hai chỗ nói hai điều khác nhau. Đúng cái bẫy đã sinh ra bốn công
thức lãi lỗ tour trong kho này.
"""
import os, re, sys, pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test_bd1.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_bd1.db", "test_bd1.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = pathlib.Path(__file__).resolve().parents[2]
MAN = GOC / "web" / "app" / "doi-xe" / "page.tsx"
CAY = GOC / "web" / "lib" / "cay_phan_he.ts"
DV_SV = GOC / "backend" / "app" / "services" / "fleet.py"


def _ma(src: str) -> str:
    """Soi MÃ chứ không soi lời kể về mã: chú thích nhắc đúng tên vừa bị xoá thì phép thử mù."""
    src = re.sub(r"\{/\*.*?\*/\}", " ", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", src, flags=re.M)


def test_bd1_1_hai_cua_bao_duong_deu_co_man_hinh_goi_toi():
    man = _ma(MAN.read_text(encoding="utf-8"))
    for cua in ("/fleet/bao-duong", "/fleet/bao-duong/theo-xe"):
        assert cua in man, (
            f"Cửa {cua} chưa có màn hình nào gọi tới. Cửa sống không có lối vào là VIỆC CÒN THIẾU "
            "theo ranh giới 09/9/2026, không phải việc đã xong.")


def test_bd1_2_man_hinh_KHONG_tu_tinh_nguong_bao_duong():
    """Ngưỡng chỉ được có một bản, và nó nằm ở máy chủ.

    Phép thử này canh đúng cái cách hỏng dễ xảy ra nhất: màn hình tự so km đồng hồ với mốc, hoặc
    chép con số ngưỡng `xe_bd_gap_km` sang giao diện."""
    man = _ma(MAN.read_text(encoding="utf-8"))
    assert "xe_bd_gap_km" not in man, \
        "Tham số ngưỡng bị chép sang màn hình — ngưỡng phải ở máy chủ, màn hình chỉ vẽ lại."
    khoi = man[man.index('tab === "baoduong"'):]
    for xau in ("odo_km >", "odo_km <", "km_ky_toi -", "- x.odo_km"):
        assert xau not in khoi, (
            f"Màn hình tự so/tự trừ (“{xau}”) để ra tình trạng bảo dưỡng. Cả mức lẫn số km còn lại "
            "phải do /fleet/bao-duong/theo-xe trả về.")


def test_bd1_3_mot_nguon_duy_nhat_cho_luat_nguong():
    """`kiem_tra()` và cửa mới phải gọi CÙNG một hàm. Hai lối tính song song thì sớm muộn lệch, và
    ngày chúng lệch, màn hình nói xe đạt trong khi bộ phát lệnh chặn nó."""
    sv = DV_SV.read_text(encoding="utf-8")
    assert "def tinh_trang_bao_duong(" in sv, "Thiếu hàm chung tinh_trang_bao_duong()"
    api = (GOC / "backend" / "app" / "api" / "v1" / "fleet.py").read_text(encoding="utf-8")
    assert "tinh_trang_bao_duong" in api, "Cửa mới phải gọi hàm chung, không dựng lại phép so sánh"
    # Bộ điều kiện phát lệnh KHÔNG được còn giữ bản so sánh riêng của nó. Đếm số lần mã cổng
    # "VUOT_MOC_BAO_DUONG" xuất hiện: đúng MỘT lần, và lần ấy phải nằm trong hàm chung.
    assert sv.count('"VUOT_MOC_BAO_DUONG"') == 1, (
        "Mã cổng vượt mốc bảo dưỡng xuất hiện nhiều hơn một chỗ trong fleet.py — tức là luật ngưỡng "
        "đã bị chép lại. Chỉ `tinh_trang_bao_duong()` được dựng cổng ấy.")
    chung = sv[sv.index("def tinh_trang_bao_duong("):]
    assert '"VUOT_MOC_BAO_DUONG"' in chung[:chung.index("\ndef ", 10)] if "\ndef " in chung[10:] else True, \
        "Mã cổng phải nằm trong hàm chung"
    than = sv[sv.index("def kiem_tra_dieu_xe("):sv.index("def san_sang(")]
    assert "tinh_trang_bao_duong(" in than, \
        "kiem_tra_dieu_xe() phải dựng cổng bảo dưỡng từ hàm chung, không tự so lại"


def test_bd1_4_chua_du_du_lieu_khong_duoc_doc_thanh_dat():
    """Xe chưa có lịch sử bảo dưỡng hoặc chưa có số km đồng hồ là CHƯA ĐỦ DỮ LIỆU, không phải đạt.

    Đây là chỗ dễ mặc định thành "không sao" rồi để xe chạy quá kỳ mà không ai biết — đặc tả đội xe
    nêu đích danh, và màn hình phải nói ra điều đó chứ không chỉ để một ô trống."""
    from app.services import fleet as FL
    assert FL.tinh_trang_bao_duong.__doc__, "Hàm chung phải ghi lý do, không chỉ trả số"
    man = _ma(MAN.read_text(encoding="utf-8"))
    assert "ghi_chu" in man[man.index('tab === "baoduong"'):], \
        "Màn hình phải in lời khai của máy chủ về ý nghĩa “chưa đủ dữ liệu”."


def test_bd1_5_muc_4_9_6_thoi_de_trong():
    """Mục đã dựng xong thì phải có đường dẫn thật, nếu không lần đo sau lại đếm nó vào việc còn
    thiếu — hoặc tệ hơn, đếm nhầm là đã xong vì có tên trong cây."""
    dong = [d for d in CAY.read_text(encoding="utf-8").splitlines() if 'ma: "4.9.6"' in d]
    assert dong, "Không tìm thấy mục 4.9.6 trong cây phân hệ"
    assert "href" in dong[0] and "/doi-xe" in dong[0], \
        f"Mục 4.9.6 vẫn chưa có đường dẫn thật: {dong[0].strip()}"
