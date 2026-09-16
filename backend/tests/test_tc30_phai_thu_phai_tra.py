# -*- coding: utf-8 -*-
"""TC-30 · Khối 05 bản vẽ V1.4 — Phải thu / Phải trả theo hạn, nối vào sổ nghĩa vụ đã có.

Vòng TC-23 dựng giao diện hai khối này rồi để mọi ô ghi "Chưa kết nối". Anh Tuấn kiểm trang thật
ngày 14/9/2026 và nói màn hình Chủ tịch vẫn chưa xong — đo lại thì đúng: trong 7 trường của hợp
đồng dữ liệu, máy chủ mới trả 1.

Nguồn số KHÔNG phải dựng mới: sổ nghĩa vụ VPM-11 đã giữ hướng thu/chi, ngày cam kết và số còn lại.
Vòng này chỉ thêm PHÉP CHIA NHÓM THEO HẠN — không thêm cửa nhập nào, đúng ranh giới 09/9.

BA CHỖ DỄ SAI mà phần lớn phép thử dưới đây canh:
  1. Năm nhóm phải LIỀN NHAU, không hở không chồng — khác bảng dòng tiền bốn mốc LŨY KẾ ở khối 06.
  2. Mốc tháng theo THÁNG LỊCH, không phải 30/90 ngày.
  3. Sổ rỗng phải trả RỖNG kèm lý do, KHÔNG trả một hàng số 0 — năm số 0 đọc y như "không nợ ai
     đồng nào", trong khi sự thật là "chưa ai nạp sổ".
"""
import re
from datetime import date, timedelta
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
HCN = GOC / "backend" / "app" / "services" / "han_cong_no.py"
DASH = GOC / "backend" / "app" / "services" / "dashboard.py"
V14 = GOC / "web" / "components" / "KhoiV14.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"

NGAY_THU = [date(2026, 9, 14), date(2026, 1, 31), date(2026, 12, 31), date(2024, 2, 29)]


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
    import pytest
    try:
        from app.services import han_cong_no as H
    except ImportError as e:
        pytest.skip(f"không nạp được han_cong_no: {e}")
    return H


# ───────────────── 1 · NĂM NHÓM LIỀN NHAU, KHÔNG HỞ KHÔNG CHỒNG ─────────────────

def test_cac_nhom_lien_nhau_khong_ho_khong_chong():
    """Cộng các nhóm phải ra ĐÚNG tổng công nợ. Hở một ngày là một khoản biến mất khỏi bảng;
    chồng một ngày là một khoản đếm hai lần. Cả hai đều không báo lỗi, chỉ ra số sai.

    SỬA 16/9/2026 (TC-45): hai hàm `khoang_thu` / `khoang_tra` gộp thành MỘT `khoang` dùng chung
    cho cả hai hướng — anh Tuấn chốt một bộ bảy mốc. Luật không đổi một chữ, và vì nay chỉ còn một
    bộ khoảng nên nó chỉ phải đúng ở một chỗ thay vì hai.
    """
    H = _nap()
    for hom_nay in NGAY_THU:
        for ten, kh in (("chung", H.khoang(hom_nay)),):
            truoc = None
            for nhan, tu, den in kh:
                assert tu <= den, f"{ten}/{nhan} có khoảng ngược: {tu} → {den}"
                if truoc is not None:
                    assert tu == truoc + timedelta(days=1), (
                        f"{ten}/{nhan} ngày {hom_nay}: hở hoặc chồng — nhóm trước hết {truoc}, "
                        f"nhóm này bắt đầu {tu}"
                    )
                truoc = den


def test_nhom_cuoi_khong_co_tran_va_nhom_dau_khong_co_day():
    """Dài hạn phải mở về sau (date.max) và Quá hạn mở về trước (date.min) — không thì khoản rơi
    ngoài hai đầu biến mất lặng lẽ."""
    H = _nap()
    k = H.khoang(date(2026, 9, 14))
    assert k[0][1] == date.min, "Nhóm Quá hạn phải mở về quá khứ."
    assert k[-1][2] == date.max, "Nhóm Dài hạn phải mở về tương lai."


# ───────────────── 2 · MỐC THÁNG THEO THÁNG LỊCH, KHÔNG PHẢI 30/90 NGÀY ─────────────────

def test_cong_thang_theo_lich_khong_phai_30_ngay():
    """Anh Tuấn chốt mốc tháng theo THÁNG LỊCH hai lần (13/9 và 14/9). Ngày 31 cộng một tháng rơi
    vào tháng ngắn hơn thì lùi về ngày cuối tháng ấy."""
    H = _nap()
    assert H.cong_thang(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert H.cong_thang(date(2024, 1, 31), 1) == date(2024, 2, 29), "Năm nhuận."
    assert H.cong_thang(date(2026, 8, 31), 1) == date(2026, 9, 30)
    assert H.cong_thang(date(2026, 12, 15), 3) == date(2027, 3, 15), "Phải qua được ranh giới năm."


def test_khong_dung_30_hay_90_ngay_trong_ma():
    """Canh ngược: mốc tháng mà tính bằng timedelta(days=30*n) thì lệch vài ngày ở mốc ba tháng —
    đủ để một khoản nhảy sang nhóm khác mà không ai thấy."""
    ma = _bo_chu_thich_py(_doc(HCN))
    for xau in ("days=30", "days=60", "days=90", "30 * ", "days=365"):
        assert xau not in ma, f"Đang tính mốc tháng bằng {xau!r} thay vì tháng lịch."
    assert "calendar.monthrange" in ma, "Phải dùng monthrange để lùi về ngày cuối tháng."


# ───────────────── 3 · HẠN RƠI ĐÚNG NGÀY BÁO CÁO KHÔNG PHẢI QUÁ HẠN ─────────────────

def test_han_dung_ngay_bao_cao_thuoc_nhom_sap_den_han():
    """Người ta còn cả ngày hôm nay để trả. Xếp vào quá hạn là dán nhãn trễ cho người chưa trễ."""
    H = _nap()
    hn = date(2026, 9, 14)
    k = {n: (tu, den) for n, tu, den in H.khoang(hn)}
    assert k["Quá hạn"][1] == hn - timedelta(days=1), "Quá hạn phải dừng TRƯỚC ngày báo cáo."
    # SỬA 16/9/2026 (TC-45): nhóm sắp đến hạn đầu tiên nay là "1 tuần" cho CẢ HAI hướng — anh Tuấn
    # thêm mốc ấy vào bộ chung. Luật y nguyên: nhóm ấy bắt đầu ĐÚNG ngày báo cáo.
    assert k["1 tuần"][0] == hn, "Nhóm sắp đến hạn đầu tiên phải bắt đầu ĐÚNG ngày báo cáo."


def test_qua_han_nam_trong_cac_nhom_o_ca_hai_huong():
    """LUẬT NÀY ĐẢO CHIỀU NGÀY 16/9/2026 (TC-45). Ghi lại cả hai vế, vì cả hai đều có lý.

    Bản cũ để "Phải trả quá hạn" NGOÀI năm nhóm: một khoản đã trễ khác hẳn một khoản sắp tới hạn
    về mức khẩn, nên tách ra là đúng về nghiệp vụ.

    Nhưng hệ quả của nó là tổng các nhóm trên màn hình KHÔNG gồm khoản đã trễ — nên ai cộng thử
    bằng mắt sẽ ra một con số khác con số hệ thống hiểu là tổng công nợ, và không có gì nói ra điều
    đó. Phía THU thì quá hạn lại nằm TRONG nhóm, nên hai khối cạnh nhau cộng theo hai luật khác
    nhau.

    Anh Tuấn chốt một bộ mốc dùng chung, Quá hạn là nhóm ĐẦU TIÊN của cả hai hướng. Mức khẩn vẫn
    đọc ra ngay — nhóm ấy mang màu trạng thái trên biểu đồ — nhưng con số chỉ nằm đúng một chỗ.
    """
    H = _nap()
    nhan = [n for n, _, _ in H.khoang(date(2026, 9, 14))]
    assert nhan[0] == "Quá hạn", nhan
    assert nhan == list(H.MOC)


# ───────────────── 4 · NHÃN NHÓM KHỚP TỪNG CHỮ VỚI GIAO DIỆN ─────────────────

def test_nhan_nhom_khop_giua_may_chu_va_man_hinh():
    """Màn hình tra số theo ĐÚNG chuỗi nhãn. Lệch một dấu là ô hiện "Chưa kết nối" trong khi máy
    chủ đang có số — hỏng im lặng, không báo lỗi ở đâu cả."""
    H = _nap()
    tsx = _doc(V14)

    def nhan_tsx(ten: str) -> tuple:
        blk = tsx[tsx.index(f"const {ten}: NhomHan[]"):]
        return tuple(re.findall(r'nhan: "([^"]+)"', blk[:blk.index("];")]))

    # SỬA 16/9/2026 (TC-45): hai khung PHAI_THU / PHAI_TRA gộp thành MỘT `BAY_NHOM`, khớp với
    # `MOC` của máy chủ. Luật y nguyên — và nay chỉ còn một chỗ để lệch thay vì hai.
    assert nhan_tsx("BAY_NHOM") == H.MOC, (nhan_tsx("BAY_NHOM"), H.MOC)
    assert tuple(n for n, _, _ in H.khoang(date(2026, 9, 14))) == H.MOC


# ───────────────── 5 · RỖNG KHÁC KHÔNG, VÀ RỖNG PHẢI NÓI VÌ SAO ─────────────────

def test_so_rong_tra_rong_kem_ly_do_chu_khong_tra_mot_hang_so_0():
    ma = _bo_chu_thich_py(_doc(HCN))
    i = ma.index("def theo_han")
    than = ma[i:]
    assert "_co_khoan_nao" in than, (
        "theo_han() chưa đếm sổ trước khi cộng — sổ chưa nạp thì năm nhóm đều ra 0, và năm số 0 "
        "đọc y như 'không nợ ai đồng nào'."
    )
    assert "LY_DO_SO_RONG" in than, "Rỗng phải đi kèm lý do đọc được."
    assert "None" in than


def test_khoan_chua_co_han_theo_doi_rieng():
    """'Chưa ai điền ngày' và 'đến hạn sau ba tháng' là hai việc khác hẳn nhau."""
    ma = _bo_chu_thich_py(_doc(HCN))
    assert "ngay_cam_ket.is_(None)" in ma, "Chưa tách khoản không có ngày cam kết."
    i = ma.index("def _chua_co_han")
    than = ma[i:ma.index("\ndef ", i + 5)]
    assert "Dài hạn" not in than, "Khoản chưa có hạn đang bị xếp vào Dài hạn."

    tsx = _bo_chu_thich_tsx(_doc(V14))
    assert "chua_co_han" in tsx, (
        "Giao diện hứa ở dòng chú thích là khoản chưa có hạn theo dõi riêng, nhưng chưa có chỗ hiện."
    )
    # TC-40: khối Phải thu / Phải trả đã rời màn hình 01 (anh Tuấn chốt 15/9/2026 — cùng dữ liệu
    # ấy nay nằm ở biểu đồ cơ cấu). Nên chỗ truyền `chua_co_han` xuống không còn ở page.tsx nữa;
    # luật "theo dõi riêng, không gộp vào Dài hạn" vẫn được canh ở máy chủ và ở KhoiV14 bên trên.


def test_khong_co_con_so_bia_trong_ma():
    """Một con số trên bảng điều hành Chủ tịch là con số ông ấy dùng để quyết. Không có số mẫu."""
    ma = _bo_chu_thich_py(_doc(HCN))
    assert not re.search(r"\b\d{6,}\b", ma), "Có số tiền gõ cứng trong bộ tính."


# ───────────────── 6 · HÀNG RÀO SEC-02 ĐI CÙNG, KHÔNG ĐỂ QUÊN ─────────────────

def test_dashboard_truyen_vai_tro_xuong_bo_tinh():
    """`nghia_vu._loc()` lọc theo `nhom_duoc_xem(vai_tro)` NGAY TRONG CÂU TRUY VẤN. Không truyền vai
    trò là mở toàn sổ — Tổng giám đốc cộng luôn ba nhóm khoản vay vốn không thuộc tầm."""
    ma = _bo_chu_thich_py(_doc(DASH))
    i = ma.index("phai_thu_theo_han")
    than = ma[max(0, i - 900):i + 900]
    assert "vai_tro=role" in than, "dashboard chưa truyền vai trò xuống han_cong_no.theo_han()."


def test_khoi_05_chi_mo_cho_vai_duoc_xem_dong_tien():
    """Cùng tập vai với khối dòng tiền: Chủ tịch · TGĐ · Kế toán · Ban Kiểm soát."""
    ma = _bo_chu_thich_py(_doc(DASH))
    i = ma.index("phai_thu_theo_han")
    truoc = ma[:i]
    dk = truoc[truoc.rindex("if role in "):]
    dk = dk[:dk.index(":")]
    for vai in ("chutich", "tgd", "ketoan", "bks"):
        assert vai in dk, f"Vai {vai!r} thiếu trong điều kiện mở khối 05: {dk}"
    assert "nv_kd" not in dk and "hcns" not in dk, f"Khối 05 đang mở quá rộng: {dk}"


def test_dung_lai_phep_cong_cua_so_chu_khong_tu_cong_lay():
    """Cộng lại một lần nữa ở đây là mở đường cho hai con số: bảng dòng tiền lấy theo `NV.cong()`,
    khối 05 lấy theo phép cộng riêng, và lúc lệch thì không ai biết tin bên nào."""
    ma = _bo_chu_thich_py(_doc(HCN))
    assert "NV.cong(" in ma, "Không dùng lại phép cộng của sổ nghĩa vụ."
    i = ma.index("def _tong")
    than = ma[i:ma.index("\ndef ", i + 5)]
    assert "NV.cong(" in than and "con_lai()" not in than, (
        "_tong() đang tự duyệt từng dòng thay vì gọi phép cộng đã có."
    )
