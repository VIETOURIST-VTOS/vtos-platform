# -*- coding: utf-8 -*-
"""TC-45 · MỘT BỘ MỐC HẠN CHO CẢ PHẢI THU LẪN PHẢI TRẢ, và bảy thanh ngang thay bảy ô vuông.

Anh Tuấn 16/9/2026, sau khi xem bản vẽ Codex đặt cạnh bản chạy thật:

  · "Phải thu / Phải trả: đổi năm ô vuông thành năm thanh ngang."
  · Mốc hạn: "quá hạn - 2 tuần - 4 tuần - 2 tháng - 3 tháng - dài hạn", rồi sau khi em nêu rằng bỏ
    "1 tuần" là bỏ mất câu "tuần này phải chi bao nhiêu": "làm cho anh 7 nhóm thêm 1 tuần".

Thành: Quá hạn · 1 tuần · 2 tuần · 4 tuần · 2 tháng · 3 tháng · Dài hạn — DÙNG CHUNG cho cả hai
hướng, khai đúng một chỗ (`han_cong_no.MOC`).

══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO HAI BỘ MỐC KHÁC NHAU LÀ MỘT LỖI, DÙ KHÔNG CON SỐ NÀO SAI
══════════════════════════════════════════════════════════════════════════════════════════════
Bản cũ: Phải thu có "Quá hạn" trong nhóm, nhóm cuối là 2 tháng. Phải trả bắt đầu ở "1 tuần", nhóm
cuối là 3 tháng, còn quá hạn theo dõi riêng NGOÀI năm nhóm. Hai khối ấy nằm cạnh nhau, cùng một
kiểu trình bày, cùng một đơn vị tiền — nên mắt sẽ dóng hàng "4 tuần" bên này với "4 tuần" bên kia
và đọc ra một phép so. Phép so ấy sai ở hai chỗ: mép sau của hai nhóm không trùng nhau, và tổng
bên phải trả không gồm khoản đã trễ trong khi tổng bên phải thu thì có.

Không con số nào sai. Cái sai nằm ở phép trừ người đọc tự làm trong đầu, và đó là loại lỗi không
bộ kiểm nào bắt được nếu bộ mốc không được khai chung một chỗ.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ HỎNG CỦA VÒNG NÀY
══════════════════════════════════════════════════════════════════════════════════════════════
1. KHOẢNG HỞ HOẶC CHỒNG MỘT NGÀY. Hở thì một khoản rơi vào khe và biến mất khỏi mọi nhóm; chồng
   thì nó bị đếm hai lần. Cả hai đều cho ra một bảng trông hoàn toàn bình thường.
2. MỐC THÁNG TÍNH BẰNG 30 NGÀY. Ngày 31 và tháng 2 làm lệch vài ngày ở mốc ba tháng — đủ để một
   khoản nhảy nhóm.
3. XẾP BẢY THANH THEO ĐỘ LỚN. Bộ biểu đồ mặc định xếp nhiều-trước; để nguyên là trục thời gian
   biến mất và "Quá hạn" rơi xuống giữa bảng.
4. KHỐI ĐỦ SỐ VẪN IN "CHƯA NỐI NGUỒN". Bản cũ chỉ có hai nhánh, nên nhánh `else` in câu ấy ngay
   dưới bảy con số thật. Tìm ra bằng cách dựng ảnh; đọc mã thì nhánh `else` trông hợp lý.
"""
import datetime as dt
import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[2]
V14 = GOC / "web" / "components" / "KhoiV14.tsx"
KHU = GOC / "web" / "components" / "BaKhuBieuDo.tsx"
BIEU_DO = GOC / "web" / "components" / "BieuDo.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
CSS = GOC / "web" / "app" / "globals.css"
BANG_DIEU_KHIEN = GOC / "backend" / "app" / "services" / "dashboard.py"

HOM_NAY = dt.date(2026, 9, 16)


def _hcn():
    """Nạp dịch vụ hạn công nợ, hoặc BỎ QUA phép thử nếu bản checkout thiếu tệp mô hình.

    `han_cong_no` nhập `app.models.nghia_vu`; bản checkout rút gọn dùng để soát cục bộ không có tệp
    ấy, còn CI thì có đủ. Bỏ qua ở đây KHÔNG phải nới lỏng: các phép thử về màn hình bên dưới vẫn
    chạy, và phần toán ngày vẫn được canh đầy đủ ở CI.
    """
    return pytest.importorskip(
        "app.services.han_cong_no",
        reason="bản checkout cục bộ thiếu app/models/nghia_vu.py; CI chạy đủ")


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


# ═════════════════ 1 · BẢY MỐC, KHAI ĐÚNG MỘT CHỖ ═════════════════

def test_bay_nhom_dung_thu_tu_anh_Tuan_chot():
    HCN = _hcn()
    assert HCN.MOC == ("Quá hạn", "1 tuần", "2 tuần", "4 tuần", "2 tháng", "3 tháng", "Dài hạn")


def test_mot_bo_moc_dung_cho_ca_hai_huong():
    """Không còn `khoang_thu` / `khoang_tra` riêng — một hàm, hai hướng gọi chung."""
    HCN = _hcn()
    assert not hasattr(HCN, "khoang_thu") and not hasattr(HCN, "khoang_tra"), (
        "Hai hàm khoảng riêng đã bỏ. Giữ lại là để hai hướng có thể lệch nhau lần nữa."
    )
    nhan = [n for n, _, _ in HCN.khoang(HOM_NAY)]
    assert nhan == list(HCN.MOC), "Nhãn khoảng phải đúng bằng MOC, cùng thứ tự."


@pytest.mark.parametrize("hom_nay", [
    dt.date(2026, 9, 16), dt.date(2026, 1, 31), dt.date(2026, 12, 31),
    dt.date(2026, 2, 28), dt.date(2028, 2, 29),      # năm nhuận
])
def test_bay_khoang_lien_nhau_khong_ho_khong_chong(hom_nay):
    """Chỗ hỏng số 1. Hở một ngày thì một khoản biến mất; chồng một ngày thì nó bị đếm hai lần."""
    HCN = _hcn()
    k = HCN.khoang(hom_nay)
    for (_, _, den), (ten_sau, tu_sau, _) in zip(k, k[1:]):
        assert den + dt.timedelta(days=1) == tu_sau, (
            f"Khe giữa hai nhóm trước {ten_sau!r}: khoảng trước hết ngày {den}, khoảng sau bắt đầu "
            f"{tu_sau}. Liền nhau nghĩa là hơn nhau ĐÚNG một ngày."
        )
    assert k[0][1] == dt.date.min and k[-1][2] == dt.date.max, (
        "Hai đầu phải phủ vô cùng: một khoản hạn từ năm 2019 hay năm 2040 vẫn phải có nhóm."
    )


def test_han_roi_dung_ngay_bao_cao_khong_phai_qua_han():
    """Người ta còn cả ngày hôm nay để trả. Xếp vào quá hạn là dán nhãn trễ cho người chưa trễ."""
    HCN = _hcn()
    k = dict((n, (tu, den)) for n, tu, den in HCN.khoang(HOM_NAY))
    assert k["Quá hạn"][1] == HOM_NAY - dt.timedelta(days=1)
    assert k["1 tuần"][0] == HOM_NAY


def test_moc_thang_theo_thang_lich_khong_phai_30_ngay():
    """Chỗ hỏng số 2."""
    HCN = _hcn()
    assert HCN.cong_thang(dt.date(2026, 1, 31), 1) == dt.date(2026, 2, 28), (
        "Ngày 31 cộng một tháng lịch rơi vào tháng 2 thì lùi về ngày cuối tháng ấy."
    )
    assert HCN.cong_thang(dt.date(2028, 1, 31), 1) == dt.date(2028, 2, 29), "Năm nhuận."
    assert HCN.cong_thang(dt.date(2026, 12, 15), 3) == dt.date(2027, 3, 15), "Qua mốc năm."
    k = dict((n, (tu, den)) for n, tu, den in HCN.khoang(dt.date(2026, 1, 31)))
    assert k["2 tháng"][1] == dt.date(2026, 3, 31) and k["3 tháng"][1] == dt.date(2026, 4, 30)


def test_khong_con_truong_qua_han_rieng():
    """Quá hạn nay là MỘT trong bảy nhóm ở cả hai hướng — giữ thêm một con số riêng cho nó là để
    cùng một khoản tiền hiện hai chỗ, và tổng bảy nhóm sẽ không khớp với nó khi ai đó cộng thử."""
    ma = _ma(_doc(GOC / "backend" / "app" / "services" / "han_cong_no.py"))
    assert '"qua_han"' not in ma, "Dịch vụ còn trả trường `qua_han` riêng."
    # Bắt ĐÚNG câu gán, không bắt chuỗi: chính chú thích giải thích vì sao đã bỏ trường ấy cũng
    # nhắc tên nó, và một phép soát theo chuỗi sẽ báo oan lời giải thích của chính mình.
    assert 'sec["phai_tra_qua_han"]' not in _doc(BANG_DIEU_KHIEN), (
        "Bảng điều khiển còn gửi `phai_tra_qua_han` xuống màn hình."
    )
    assert "qua_han=" not in _ma(_doc(TRANG)), "Màn hình còn chuyền `qua_han` vào khối Phải trả."


# ═════════════════ 2 · MÀN HÌNH: BẢY THANH NGANG ═════════════════

def test_khung_man_hinh_khop_tung_chu_voi_may_chu():
    """Lệch một dấu là dòng hiện 'chưa có số' trong khi máy chủ có số — và không ai đoán ra vì sao."""
    MOC = _hcn().MOC
    khu = _doc(KHU)
    doan = khu[khu.index("const KHUNG_HAN"): khu.index("];", khu.index("const KHUNG_HAN"))]
    assert [m for m in re.findall(r'nhan: "([^"]+)"', doan)] == list(MOC)
    v14 = _doc(V14)
    doan2 = v14[v14.index("const BAY_NHOM"): v14.index("];", v14.index("const BAY_NHOM"))]
    assert [m for m in re.findall(r'nhan: "([^"]+)"', doan2)] == list(MOC)
    assert "so:" not in doan2, "Khung chỉ khai nhãn và mô tả khoảng; số đến từ máy chủ."


def test_bay_thanh_xep_theo_thoi_gian_khong_theo_do_lon():
    """Chỗ hỏng số 3. Bộ biểu đồ mặc định xếp nhiều-trước, nên phải TẮT tường minh."""
    ma = _ma(_doc(KHU))
    # Cắt TỪ THÂN HÀM, không từ đầu tệp: kiểu `BoBieuDo` cũng có dòng `phai_thu:`, và cắt nhầm ở
    # đó thì phép thử đo một đoạn không có biểu đồ nào.
    than = ma[ma.index("export function bieuDoCua"):]
    doan = than[than.index("phai_thu:"): than.index("kd_le:")]
    assert doan.count("xep={false}") == 2, (
        "Cả hai khối công nợ phải tắt phép xếp. Để nguyên là trục thời gian biến mất và 'Quá hạn' "
        "rơi xuống giữa bảng — lúc ấy không ai đọc ra nợ đang dồn về phía nào."
    )


def test_qua_han_mang_mau_trang_thai_va_van_dung_dau():
    """Mức khẩn phải đọc ra ngay, nhưng KHÔNG được vì thế mà bị đẩy ra khỏi thứ tự thời gian."""
    khu = _ma(_doc(KHU))
    doan = khu[khu.index("const KHUNG_HAN"): khu.index("];", khu.index("const KHUNG_HAN"))]
    assert doan.index("trang_thai: true") < doan.index('"1 tuần"'), (
        "Cờ trạng thái phải nằm ở nhóm Quá hạn, và nhóm ấy vẫn đứng đầu."
    )
    bd = _ma(_doc(BIEU_DO))
    assert 'h.trang_thai ? " tt" : ""' in bd, "Thiếu lớp màu cho dòng trạng thái."
    assert "nhan_phu" in bd and "xepThanh" in bd, (
        "`trang_thai` KHÁC `nhan_phu`: `nhan_phu` đẩy dòng xuống cuối vì nó không cùng loại; "
        "`trang_thai` chỉ đổi màu, vì Quá hạn VẪN là một trong bảy nhóm."
    )
    css = _doc(CSS)
    i = css.index(".bd-th-thanh.tt")
    assert "--vtos-danger" in css[i:i + 120], (
        "Dòng trạng thái phải cùng màu với khúc trạng thái của biểu đồ cơ cấu — một khái niệm hai "
        "màu là hai khái niệm."
    )


def test_khoi_du_so_khong_duoc_noi_chua_noi_nguon():
    """SỬA 29/9/2026: khối không in câu nguồn nào nữa (anh Tuấn: "xoá hết ghi chú"), nên cũng
    không còn chỗ nào dán "chưa nối nguồn" lên một khối đầy số. Chỉ còn một lối "Xem chi tiết"."""
    ma = _ma(_doc(V14))
    than = ma[ma.index("function KhoiHan"): ma.index("export function KhoiPhaiThu")]
    assert "ChuaNoi" not in than and "Số lấy từ sổ nghĩa vụ thanh toán" not in than
    assert than.count("Xem chi tiết") == 1


def test_khong_con_bay_o_so_vuong_lap_lai_bieu_do():
    """MỘT CON SỐ · MỘT CHỖ · MỘT HÌNH (TC-40), áp cho chính khối này."""
    ma = _ma(_doc(V14))
    for lop in ("v14-han-ds", "v14-han-nhan", "v14-han-so", "v14-han-ty"):
        assert lop not in ma, f"Còn sót ô số vuông ({lop}) bên cạnh biểu đồ vẽ đúng hàng số ấy."
    css = _doc(CSS)
    assert ".v14-han{" not in css and ".v14-han-ds{" not in css, (
        "CSS của bảy ô vuông phải dọn theo. Để lại là hai cách bày cùng một hàng số nằm chờ, và "
        "ngày ai đó sửa màu ở một bộ là ngày hai khối cạnh nhau không còn giống nhau."
    )


def test_moc_tinh_tu_dau_van_con_tren_man_hinh():
    """Bỏ bảy câu mô tả dưới bảy ô KHÔNG được thành bỏ luôn thông tin: '4 tuần' đếm từ ngày nào."""
    ma = _ma(_doc(V14))
    # SỬA 29/9/2026: dòng "Mốc tính từ ngày báo cáo" bỏ khỏi màn hình theo lệnh anh Tuấn; câu mô
    # tả từng nhóm vẫn giữ trong BAY_NHOM để khung biểu đồ và phép thử đọc được.
    assert "Mốc tính từ ngày báo cáo" not in ma
    doan = ma[ma.index("const BAY_NHOM"): ma.index("];", ma.index("const BAY_NHOM"))]
    assert doan.count("mo_ta:") == 7, "Mỗi nhóm phải còn câu mô tả khoảng của nó."


def test_so_tren_man_hinh_doc_cung_mot_kieu():
    """Bảy thanh in '2 tỷ' còn ô bên cạnh in '400.000.000' là bắt mắt đổi thước giữa hai con số."""
    ma = _ma(_doc(V14))
    than = ma[ma.index("function KhoiHan"): ma.index("export function KhoiPhaiThu")]
    assert 'gonSo(chua_co_han, "tien")' in than, (
        "Khoản chưa có hạn phải đọc cùng kiểu với bảy thanh ngay trên nó."
    )
