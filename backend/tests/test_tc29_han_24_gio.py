# -*- coding: utf-8 -*-
"""TC-29 · Hạn xử lý 24 giờ cho dòng tiền chưa đủ nguồn (anh Tuấn chốt 14/9/2026).

Từ vòng TC-25, cột "Hạn xử lý" trên trang /dong-tien/nguon ghi "chưa đặt" cho mọi dòng — hệ thống
chưa có chỗ nào giữ hạn. Anh Tuấn chốt hạn 24 giờ, nên cột ấy nay phải nói một con số thật.

CHỖ DỄ SAI NHẤT, và là điều phần lớn phép thử dưới đây canh: hạn phải đếm từ lúc LƯỢT QUÉT PHÁT
HIỆN, không phải từ lúc mở trang. Lấy "bây giờ + 24 giờ" lúc vẽ trang thì một dòng treo cả tuần vẫn
hiện "còn 24 giờ" mỗi lần mở — hạn trôi theo người xem, không bao giờ quá hạn, và một hạn không bao
giờ quá hạn thì chẳng nhắc được ai. Đó là cách một tính năng trông như đã làm xong mà thật ra không
làm gì cả.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
HAN = GOC / "backend" / "app" / "services" / "han_dong_tien.py"
API = GOC / "backend" / "app" / "api" / "v1" / "dong_tien.py"
RULES = GOC / "backend" / "app" / "services" / "rules.py"
XL = GOC / "backend" / "app" / "services" / "xuat_dong_tien_excel.py"
NGUON = GOC / "web" / "app" / "dong-tien" / "nguon" / "page.tsx"
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _bo_chu_thich_py(s: str) -> str:
    s = re.sub(r'"""(?:.|\n)*?"""', "", s)
    return re.sub(r"^\s*#.*$", "", s, flags=re.M)


def _bo_chu_thich_tsx(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", "", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", "", s)
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)


def _nap():
    """Nạp module thật. Bản sao cục bộ thiếu sqlalchemy nên bỏ qua — CI có đủ và chạy hết."""
    import pytest
    try:
        from app.services import han_dong_tien as H
    except ImportError as e:
        pytest.skip(f"không nạp được han_dong_tien: {e}")
    return H


# ─────────────────── 1 · HẠN ĐẾM TỪ LÚC PHÁT HIỆN, KHÔNG PHẢI TỪ LÚC MỞ TRANG ───────────────────

def test_cua_get_khong_duoc_de_canh_bao():
    """`gan_han` chạy trên đường vẽ màn hình. Nó tạo Alert là số cảnh báo tăng theo số lần bấm F5."""
    ma = _bo_chu_thich_py(_doc(HAN))
    than = ma[ma.index("def gan_han"):]
    assert "Alert(" not in than and "db.add" not in than, (
        "gan_han() đang GHI. Cửa GET không được đẻ dữ liệu — việc sinh hạn là của quet()."
    )


def test_han_ghi_mot_lan_roi_khong_doi():
    """Dòng ĐÃ có hạn thì lượt quét sau giữ nguyên, không cấp hạn mới."""
    H = _nap()
    o = {"ma": "tra_ncc", "trang_thai": "con_thieu"}
    assert H.quyet_dinh(o, da_co_han=True) == H.GIU, (
        "Lượt quét đang cấp lại hạn cho dòng đã có hạn — hạn sẽ lùi mỗi lượt quét và không bao giờ trễ."
    )
    assert H.quyet_dinh(o, da_co_han=False) == H.MO


def test_dong_du_nguon_thi_dong_han():
    H = _nap()
    du = {"ma": "tra_ncc", "trang_thai": "day_du"}
    assert H.quyet_dinh(du, da_co_han=True) == H.DONG
    assert H.quyet_dinh(du, da_co_han=False) == H.BO_QUA, "Dòng đủ nguồn mà chưa có hạn thì không làm gì."


def test_dong_tu_cong_khong_bi_doi_han():
    """Dòng tự cộng không có cửa nhập — đòi hạn ở nó là đòi một người không tồn tại."""
    H = _nap()
    assert H.quyet_dinh({"ma": "tong_thu", "tu_tinh": True, "trang_thai": "con_thieu"}, False) == H.BO_QUA


# ─────────────────────────── 2 · CHƯA QUÉT THÌ NÓI CHƯA QUÉT ───────────────────────────

def test_chua_quet_thi_khong_bia_han():
    """Dòng đang thiếu mà lượt quét chưa chạy tới: KHÔNG lấy 'bây giờ + 24 giờ' cho có."""
    H = _nap()
    goi = {"xem_duoc": True, "dong": [{"ma": "tra_ncc", "trang_thai": "con_thieu"}]}
    ra = H._gan(goi, {}, datetime(2026, 9, 14, 10, 0), 24.0)
    d = ra["dong"][0]
    assert d["han_chua_quet"] is True
    assert d["han_hien"] == "" and d["han_xu_ly"] is None, (
        f"Đã bịa một hạn tại chỗ: {d['han_hien']!r}. Hạn ấy sẽ lùi lại mỗi lần mở trang."
    )
    assert ra["so_qua_han"] == 0


def test_dong_day_du_khong_mang_han():
    H = _nap()
    gio = datetime(2026, 9, 14, 10, 0)
    goi = {"xem_duoc": True, "dong": [{"ma": "tra_ncc", "trang_thai": "day_du"}]}
    d = H._gan(goi, {"tra_ncc": gio - timedelta(hours=1)}, gio, 24.0)["dong"][0]
    assert d["han_hien"] == "" and d["qua_han"] is False and d["han_chua_quet"] is False


# ─────────────────────────────── 3 · QUÁ HẠN PHẢI ĐẾM ĐƯỢC ───────────────────────────────

def test_qua_han_dem_duoc_va_noi_tre_bao_lau():
    H = _nap()
    gio = datetime(2026, 9, 14, 10, 0)
    goi = {"xem_duoc": True, "dong": [
        {"ma": "tra_ncc", "trang_thai": "con_thieu"},          # hạn đã qua 3 giờ
        {"ma": "thu_khach", "trang_thai": "chua_doi_soat"},    # hạn còn 5 giờ
        {"ma": "hoa_hong", "trang_thai": "con_thieu"},         # hạn đã qua 2 ngày
    ]}
    ra = H._gan(goi, {
        "tra_ncc": gio - timedelta(hours=3),
        "thu_khach": gio + timedelta(hours=5),
        "hoa_hong": gio - timedelta(days=2, hours=1),
    }, gio, 24.0)
    d = {o["ma"]: o for o in ra["dong"]}
    assert d["tra_ncc"]["qua_han"] is True and d["tra_ncc"]["tre_hien"] == "trễ 3 giờ"
    assert d["thu_khach"]["qua_han"] is False and d["thu_khach"]["tre_hien"] == ""
    assert d["hoa_hong"]["tre_hien"] == "trễ 2 ngày"
    assert ra["so_qua_han"] == 2, "Số dòng quá hạn phải đếm được, không chỉ tô đỏ từng dòng."
    assert "2 dòng quá hạn" in ra["cau_han"]


def test_ngay_gio_do_may_chu_dung_chu_khong_phai_trinh_duyet():
    """Bài học vòng TC-26: hai nơi cùng dựng ngày thì ra hai kiểu ngày trên cùng một dòng."""
    H = _nap()
    gio = datetime(2026, 9, 14, 10, 0)
    goi = {"xem_duoc": True, "dong": [{"ma": "tra_ncc", "trang_thai": "con_thieu"}]}
    d = H._gan(goi, {"tra_ncc": datetime(2026, 9, 15, 8, 30)}, gio, 24.0)["dong"][0]
    assert d["han_hien"] == "15-09-2026 08:30", d["han_hien"]

    ma = _bo_chu_thich_tsx(_doc(NGUON))
    assert "toLocaleString" not in ma and "toLocaleDate" not in ma, (
        "Trang nguồn số đang tự dựng lại định dạng ngày — phải đọc chuỗi máy chủ gửi sang."
    )
    assert "han_hien" in ma, "Trang nguồn số chưa đọc hạn máy chủ trả."


# ────────────────────────────── 4 · 24 GIỜ LÀ THAM SỐ, CÓ CỬA ĐỔI ──────────────────────────────

def test_24_gio_nam_trong_so_tham_so():
    """Ranh giới 09/9: mỗi con số phải có một cửa. Số gõ cứng trong mã thì Chủ tịch không đổi được."""
    s = _doc(RULES)
    assert '("dong_tien_han_xu_ly_gio", "24"' in s, (
        "Hạn 24 giờ phải nằm trong DEFAULT_PARAMS để đổi được qua cửa tham số, không gõ cứng."
    )
    assert "THAM_SO_HAN = \"dong_tien_han_xu_ly_gio\"" in _doc(HAN)


def test_luot_quet_goi_tu_robot_canh_bao():
    """Sinh hạn phải nằm trong lượt quét định kỳ, cùng chỗ với mọi cảnh báo khác."""
    ma = _bo_chu_thich_py(_doc(RULES))
    i = ma.index("def run_robots")
    than = ma[i:ma.index("\ndef ", i + 5)]
    assert "han_dong_tien" in than and "quet(db)" in than, (
        "run_robots chưa gọi lượt quét hạn dòng tiền — không ai sinh hạn thì cột hạn mãi trống."
    )


def test_mot_phap_nhan_hong_khong_nuot_mat_canh_bao_khac():
    """Pháp nhân chưa có nền dữ liệu dòng tiền sẽ ném lỗi. Lỗi ấy không được dừng cả lượt quét."""
    ma = _bo_chu_thich_py(_doc(HAN))
    i = ma.index("def quet")
    than = ma[i:ma.index("\ndef ", i + 5)]
    assert "try:" in than and "continue" in than, (
        "quet() chưa bọc phần đọc bảng bốn mốc — một pháp nhân hỏng là cả lượt quét dừng."
    )


# ───────────────────────────── 5 · MÀN HÌNH VÀ EXCEL NÓI GIỐNG NHAU ─────────────────────────────

def test_excel_bo_chu_chua_dat():
    """Cột Hạn xử lý trong Excel không được còn ghi 'chưa đặt' cho mọi dòng như vòng TC-25."""
    ma = _bo_chu_thich_py(_doc(XL))
    i = ma.index("def _trang_nguon")
    than = ma[i:ma.index("\ndef ", i + 5)]
    assert '"chưa đặt"' not in than, "Trang Nguồn số trong Excel vẫn ghi cứng 'chưa đặt'."
    assert "_o_han(r)" in than, "Ô hạn phải lấy từ gói máy chủ trả."


def test_excel_noi_ro_ba_trang_thai_cua_o_han():
    import pytest
    try:
        from app.services import xuat_dong_tien_excel as X
    except ImportError as e:
        pytest.skip(f"không nạp được bộ dựng tệp: {e}")
    assert X._o_han({"han_chua_quet": True}) == "chờ lượt quét"
    assert X._o_han({"han_hien": "15-09-2026 08:30"}) == "15-09-2026 08:30"
    o = X._o_han({"han_hien": "13-09-2026 08:30", "qua_han": True, "tre_hien": "trễ 1 ngày"})
    assert "QUÁ HẠN" in o and "trễ 1 ngày" in o, o


def test_hai_cua_deu_gan_han():
    """Màn hình và Excel phải đi qua CÙNG một đường — lệch một chỗ là hai nơi nói khác nhau."""
    ma = _bo_chu_thich_py(_doc(API))
    assert ma.count("HAN.gan_han(") == 2, (
        "Một trong hai cửa (/khung và /khung/excel) chưa gắn hạn."
    )


def test_khoi_dong_tien_dem_qua_han_rieng():
    """'Còn thiếu' và 'quá hạn' là hai điều khác nhau — gộp là mất cái khiến người ta đứng dậy làm."""
    ma = _bo_chu_thich_tsx(_doc(KHOI))
    assert "so_qua_han" in ma, "Dòng tóm tắt trên màn hình 01 chưa nói số dòng quá hạn."


def test_khong_co_ten_vai_tro_trong_trang_nguon():
    """SEC-02 — trình duyệt không lọc theo vai. Vẫn canh lại ở vòng này vì trang vừa bị sửa."""
    ma = _bo_chu_thich_tsx(_doc(NGUON))
    for vai in ("chutich", "tgd", "ketoan", "bks"):
        assert vai not in ma, f"Trang nguồn số nhắc tên vai {vai!r} — việc cắt dòng là của máy chủ."
