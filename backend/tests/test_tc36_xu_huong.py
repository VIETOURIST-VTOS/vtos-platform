# -*- coding: utf-8 -*-
"""TC-36 · Xu hướng chỉ tiêu — bốn luật của chuỗi số.

Anh Tuấn 15/9/2026: bốn thẻ Doanh thu · Lợi nhuận trước thuế · Tour đang bán · Tour chờ quyết toán
nên "vừa thấy số liệu vừa thấy biểu đồ so sánh với tháng trước", và "ưu tiên viết cấu trúc, thuật
toán, luồng logic; dữ liệu quá khứ anh sẽ nạp lên sau".

Nên bộ kiểm này kiểm PHÉP TÍNH, chạy hoàn toàn bằng sổ giả — không cần cơ sở dữ liệu, không cần dữ
liệu quá khứ. Đúng thứ phải đúng trước khi có số thật đổ vào.

Bốn luật, và mỗi luật sinh ra từ một cách đọc sai cụ thể:

 1. CHỈ KỲ ĐÃ ĐÓNG — tháng đang chạy mới đi nửa đường, đặt cạnh tháng đủ 30 ngày thì cột cuối luôn
    thấp và đường xu hướng luôn trông như đang lao dốc.
 2. THIẾU LÀ Ô TRỐNG — nối liền qua chỗ trống là bịa dữ liệu; thay bằng 0 là nói kỳ ấy doanh thu
    bằng không.
 3. DƯỚI HAI ĐIỂM THÌ KHÔNG VẼ — một cột kèm mũi tên ▲ đọc ra là "đang tăng", sự thật là "mới có
    một kỳ".
 4. CHỈ SO HAI KỲ LIỀN NHAU VÀ ĐỀU CÓ SỐ — nhảy cóc sang kỳ cũ hơn là so hai thứ cách nhau ba
    tháng mà nhãn vẫn ghi "kỳ trước".
"""
import datetime as dt
import re

import pytest

from app.services import xu_huong as XH

HOM_NAY = dt.date(2026, 9, 15)


def _doc(bang: dict):
    """Hàm đọc giả: lấy số từ một cuốn sổ viết sẵn."""
    return lambda ma, ky: bang.get(ky)


# ───────────────── LUẬT 1 · CHỈ KỲ ĐÃ ĐÓNG ─────────────────

@pytest.mark.parametrize("hom_nay,ky_cuoi", [
    (dt.date(2026, 9, 15), "2026-08"),
    (dt.date(2026, 9, 1), "2026-08"),      # ngày đầu tháng
    (dt.date(2026, 9, 30), "2026-08"),     # ngày cuối tháng
    (dt.date(2026, 1, 3), "2025-12"),      # bắc qua năm
    (dt.date(2026, 3, 1), "2026-02"),      # tháng ngắn
])
def test_ky_moi_nhat_luon_la_ky_vua_dong(hom_nay, ky_cuoi):
    assert XH.cac_ky(hom_nay, 6)[-1] == ky_cuoi


def test_ky_dang_chay_khong_bao_gio_nam_trong_chuoi():
    """Đây là luật quan trọng nhất: tháng đang chạy đặt cạnh các tháng đủ ngày thì cột cuối luôn
    thấp, và người đọc thấy một đường lao dốc không có thật."""
    for ngay in (1, 5, 15, 28):
        hn = dt.date(2026, 9, ngay)
        assert "2026-09" not in XH.cac_ky(hn, 12), f"{hn}: kỳ đang chạy lọt vào chuỗi"


def test_chuoi_xep_cu_truoc_moi_sau_va_khong_trung():
    ks = XH.cac_ky(HOM_NAY, 12)
    assert ks == sorted(ks) and len(set(ks)) == 12


def test_so_ky_khong_hop_le_thi_bao_loi():
    with pytest.raises(ValueError):
        XH.cac_ky(HOM_NAY, 0)


# ───────────────── LUẬT 2 · THIẾU LÀ Ô TRỐNG, KHÔNG PHẢI 0 ─────────────────

def test_ky_thieu_giu_None_khong_quy_doi_thanh_0():
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-06": 100.0, "2026-08": 140.0}),
                 so_ky=4, hom_nay=HOM_NAY)
    gt = {d["ky"]: d["gia_tri"] for d in r["diem"]}
    assert gt["2026-07"] is None, "Kỳ thiếu phải là None"
    assert gt["2026-05"] is None
    assert 0 not in [d["gia_tri"] for d in r["diem"]], "Không được quy đổi kỳ thiếu thành 0"


def test_o_trong_van_giu_dung_cho_trong_chuoi():
    """Bỏ kỳ thiếu ra khỏi chuỗi thì sáu kỳ trông như bốn kỳ liền nhau — khoảng cách thời gian bị
    bóp méo mà biểu đồ vẫn trông bình thường."""
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-08": 1.0}), so_ky=6, hom_nay=HOM_NAY)
    assert len(r["diem"]) == 6


def test_so_0_that_van_la_so_that():
    """0 đ doanh thu là một con số có thật và khác hẳn 'chưa có số'. Gộp hai thứ là mất đúng cái
    khác biệt mà cả hệ thống này đang canh."""
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-07": 0.0, "2026-08": 50.0}),
                 so_ky=3, hom_nay=HOM_NAY)
    assert r["so_ky_co_so"] == 2 and r["du_ve"]


# ───────────────── LUẬT 3 · DƯỚI HAI ĐIỂM THÌ KHÔNG VẼ ─────────────────

def test_mot_diem_thi_khong_ve_va_noi_vi_sao():
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-08": 100.0}), so_ky=4, hom_nay=HOM_NAY)
    assert not r["du_ve"] and r["so_sanh"] is None
    assert r["vi_sao"].strip(), "Không vẽ thì phải nói vì sao"


def test_khong_diem_nao_thi_cung_noi_vi_sao():
    r = XH.chuoi("doanh_thu_thang", _doc({}), so_ky=4, hom_nay=HOM_NAY)
    assert not r["du_ve"] and r["vi_sao"].strip()


def test_ton_kho_rong_noi_dung_ly_do_rieng():
    """'Tour đang bán' là số đếm TẠI MỘT THỜI ĐIỂM. Hôm qua bao nhiêu, không ai chụp thì vĩnh viễn
    không biết — lý do khác hẳn 'chưa đủ hai kỳ', nên câu giải thích cũng phải khác."""
    r = XH.chuoi("tour_dang_ban", _doc({}), so_ky=4, hom_nay=HOM_NAY)
    assert not r["du_ve"]
    assert r["vi_sao"] == XH.LY_DO_TON_KHO_RONG
    assert "không tính lại được" in r["vi_sao"]


def test_hai_diem_thi_ve_duoc():
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-07": 10.0, "2026-08": 20.0}),
                 so_ky=4, hom_nay=HOM_NAY)
    assert r["du_ve"] and r["vi_sao"] == ""


# ───────────────── LUẬT 4 · SO SÁNH ─────────────────

def test_so_dung_hai_ky_cuoi_lien_nhau():
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-07": 100.0, "2026-08": 125.0}),
                 so_ky=3, hom_nay=HOM_NAY)
    s = r["so_sanh"]
    assert s["ky"] == "2026-08" and s["ky_truoc"] == "2026-07"
    assert s["tang"] and abs(s["phan_tram"] - 0.25) < 1e-9


def test_ky_lien_truoc_rong_thi_khong_nhay_coc():
    """Nhảy sang kỳ cũ hơn để có cái mà so là dán nhãn 'kỳ trước' lên một kỳ cách đó ba tháng."""
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-05": 100.0, "2026-08": 125.0}),
                 so_ky=4, hom_nay=HOM_NAY)
    assert r["so_sanh"] is None


def test_ky_truoc_bang_0_thi_phan_tram_de_rong():
    """Chia cho 0 thì phần trăm không tồn tại. Trả 0% hay ∞ đều là bịa."""
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-07": 0.0, "2026-08": 50.0}),
                 so_ky=3, hom_nay=HOM_NAY)
    s = r["so_sanh"]
    assert s is not None and s["phan_tram"] is None
    assert s["chenh"] == 50.0, "Vẫn nói được chênh lệch tuyệt đối"


def test_lo_it_di_van_la_tang():
    """−40 lên −10 là ĐỠ LỖ, tức tốt lên. Chia cho b (số âm) thì ra âm và mũi tên chỉ xuống —
    đọc ngược hẳn sự thật. Nên chia cho TRỊ TUYỆT ĐỐI."""
    r = XH.chuoi("ln_ke_toan_thang", _doc({"2026-07": -40.0, "2026-08": -10.0}),
                 so_ky=3, hom_nay=HOM_NAY)
    s = r["so_sanh"]
    assert s["tang"] and not s["giam"]
    assert abs(s["phan_tram"] - 0.75) < 1e-9


def test_giam_thi_bao_giam():
    r = XH.chuoi("doanh_thu_thang", _doc({"2026-07": 200.0, "2026-08": 150.0}),
                 so_ky=3, hom_nay=HOM_NAY)
    assert r["so_sanh"]["giam"] and not r["so_sanh"]["tang"]


# ───────────────── KHAI BÁO CHỈ TIÊU ─────────────────

def test_chi_tieu_khai_dung_nhung_gi_anh_Tuan_chi_dinh():
    """Tám thẻ mà tám biểu đồ thì không thẻ nào còn nổi bật. Bốn thẻ nhỏ (Tour sắp khởi hành · Đội
    xe · Marketing · Tồn đọng) là việc phải xử LÚC NÀY, không phải xu hướng — chúng KHÔNG được có
    chỉ tiêu ở đây.

    SỰ THẬT ĐỔI, LUẬT KHÔNG ĐỔI (TC-47, 16/9/2026). Bản cũ chốt cứng "đúng bốn", và con số bốn ấy
    là HỆ QUẢ của luật chứ không phải luật. Anh Tuấn chốt thêm cột "lợi nhuận tour" đứng cạnh lợi
    nhuận trước thuế, nên nay là năm. Luật vẫn nguyên: chỉ khai chỉ tiêu cho thứ ĐÁNG NHÌN THEO
    THỜI GIAN, và bốn thẻ nhỏ vẫn nằm ngoài. Canh đúng luật ấy chứ không canh con số.
    """
    phai_co = {"doanh_thu_thang", "lai_tour_thang", "ln_ke_toan_thang",
               "tour_dang_ban", "tour_cho_quyet_toan"}
    assert phai_co <= set(XH.CHI_TIEU)
    cam = {"tour_sap_khoi_hanh", "doi_xe_hom_nay", "xe_dang_di", "marketing", "ton_dong"}
    assert not (cam & set(XH.CHI_TIEU)), (
        "Bốn thẻ nhỏ là việc phải xử lúc này, không phải xu hướng — thêm biểu đồ cho chúng là làm "
        "loãng đúng những hình đáng nhìn."
    )


def test_hai_loai_chi_tieu_khai_dung():
    """Phân biệt dòng chảy / tồn kho quyết định cả thiết kế: cái đầu tính lại được cho kỳ đã qua,
    cái sau thì không."""
    assert XH.CHI_TIEU["doanh_thu_thang"].loai == XH.DONG_CHAY
    assert XH.CHI_TIEU["ln_ke_toan_thang"].loai == XH.DONG_CHAY
    assert XH.CHI_TIEU["tour_dang_ban"].loai == XH.TON_KHO
    assert XH.CHI_TIEU["tour_cho_quyet_toan"].loai == XH.TON_KHO


def test_chi_tieu_chua_khai_thi_bao_loi():
    with pytest.raises(ValueError):
        XH.chuoi("khong_co_that", _doc({}), hom_nay=HOM_NAY)


def test_khong_tu_viet_cong_thuc_doanh_thu_lan_hai():
    """`doc_that` phải GỌI hàm dùng chung, không viết công thức riêng. Hai nơi cùng tính một con số
    là hai nơi sớm muộn ra hai kết quả, và lúc lệch thì không ai biết tin bên nào.

    HAI ĐIỀU ĐÃ ĐỔI Ở VÒNG TC-47, cùng một lý do — anh Tuấn chốt mốc là ngày Điều hành đóng số và
    phạm vi là Vietourist mẹ:

      · Hàm dùng chung nay là `ket_qua_that.thang`, không còn là `_month_tours` +
        `settlement_summary`. `settlement_summary` vẫn đúng cho việc của nó (quỹ thưởng, căn cứ là
        số Kế toán đã xác nhận) — chỉ là nó trả lời một câu hỏi KHÁC.
      · Phép thử này từng CANH CHỮ: nó đòi chuỗi "_month_tours" có mặt trong tệp. Sau khi bỏ lời
        gọi ấy đi, nó VẪN XANH — vì chuỗi ấy còn nằm trong chính đoạn chú thích giải thích vì sao
        nó bị bỏ. Đúng bài học TC-41: cấm hay đòi một CHUỖI KÝ TỰ thì phép thử canh lời giải
        thích chứ không canh việc làm. Nay bỏ chú thích trước khi soát.
    """
    nguon = open(XH.__file__, encoding="utf-8").read()
    ma = re.sub(r'"""(?:.|\n)*?"""', " ", nguon)
    ma = re.sub(r"^\s*#.*$", " ", ma, flags=re.M)
    assert "KQ.thang(db, ky)" in ma, "Doanh thu và lãi tour phải đi qua ket_qua_that."
    assert "income_statement" in ma
    assert "_month_tours" not in ma and "settlement_summary" not in ma, (
        "Phép tính cũ lọc theo ngày Kế toán xác nhận và không lọc pháp nhân — không còn dùng ở đây."
    )


def test_ton_kho_chi_doc_ban_luu_khong_suy_tu_hom_nay():
    """Suy số kỳ trước từ số hôm nay là bịa ra một quá khứ."""
    nguon = open(XH.__file__, encoding="utf-8").read()
    than = nguon[nguon.index("def _doc_ban_luu"):]
    assert "BaoCaoLuu" in than
    assert "date.today" not in than, "Hàm đọc bản lưu không được dùng tới ngày hôm nay."
