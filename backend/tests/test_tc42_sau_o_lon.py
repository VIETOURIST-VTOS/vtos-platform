# -*- coding: utf-8 -*-
"""TC-42 · SÁU Ô LỚN, và doanh thu / lợi nhuận theo THÁNG · QUÝ · NĂM.

Anh Tuấn 16/9/2026, sau khi mở bản chạy thật lần nữa:

    "8 ô này anh muốn thay đổi vị trí — doanh thu, lợi nhuận trước thuế, dòng tiền, phải thu, phải
     trả, tồn đọng cần xử lý: 6 ô này làm biểu đồ lớn lên, chia ra các chart khác nhau theo cấu
     trúc; phần doanh thu và lợi nhuận phân ra theo tháng, quý, năm. Giảm từ 8 ô xuống còn 6 ô.
     Các phần tour đang bán, tour chờ quyết toán, tour sắp khởi hành, đội xe hôm nay, marketing
     đưa xuống vị trí dưới."

══════════════════════════════════════════════════════════════════════════════════════════════
ĐIỀU ĐÁNG GHI LẠI KHÔNG PHẢI LÀ "SÁU TO NĂM NHỎ", MÀ LÀ RANH GIỚI GIỮA HAI NHÓM
══════════════════════════════════════════════════════════════════════════════════════════════
Bản V1.2 xếp tám thẻ ngang hàng nhau. Trên bản chạy thật, tám thẻ ngang hàng hoá ra là tám con số
ngang hàng — mà chúng không ngang hàng chút nào:

  · "Doanh thu 4,3 tỷ" một mình KHÔNG nói được gì. Tốt hay xấu thì phải đặt cạnh kế hoạch và cạnh
    kỳ trước mới trả lời được. Nó là con số phải NGHĨ.
  · "93 tour sắp khởi hành" thì đọc xong là xong. Nó là con số để LIẾC.

Trộn hai loại vào một lưới tám ô thì loại thứ nhất không có chỗ để bày cái nó cần (biểu đồ, kế
hoạch, ba bề rộng kỳ), còn loại thứ hai lại chiếm đúng chỗ ấy. Sáu ô lớn và năm thẻ nhỏ là cách
tách hai loại ra.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ HỎNG CỦA VÒNG NÀY
══════════════════════════════════════════════════════════════════════════════════════════════
1. QUÝ LẤY BỘ SỐ CỦA THÁNG LÀM LỐI LUI. Ba nút mà bấm sang kỳ nào cũng ra cùng bộ số là nói dối
   bằng giao diện — người đọc kết luận quý bằng tháng, chứ không kết luận là chưa có số. Bài học
   đã phải trả giá ở khối Hiệu quả đội xe (TC-40), và ở đây nó quay lại nguyên dạng.
2. CỘNG TỒN KHO. "Tour đang bán" của quý 3 KHÔNG phải tổng ba tháng — một chuyến bán suốt quý bị
   đếm ba lần, ra một con số to gấp ba mà vẫn trông hợp lý.
3. QUÝ THIẾU MỘT THÁNG VẪN CỘNG. Con số thiếu một tháng nhìn không khác gì con số đầy đủ, và
   không ai đi hỏi một con số trông bình thường.
4. KỲ ĐANG CHẠY LỌT VÀO BIỂU ĐỒ. Một quý mới đi được hai tuần đứng cạnh các quý đủ ba tháng thì
   cột cuối luôn thấp và đường xu hướng luôn trông như đang lao dốc.
"""
import datetime as dt
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Alert
from app.services import canh_bao_muc as CBM
from app.services import xu_huong as XH

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "page.tsx"
SAU_O = GOC / "web" / "components" / "KhoiSauO.tsx"
KHOI_KQ = GOC / "web" / "components" / "KhoiKetQuaKinhDoanh.tsx"
DAU = GOC / "web" / "components" / "DauManHinh01.tsx"
CSS = GOC / "web" / "app" / "globals.css"
BANG_DIEU_KHIEN = GOC / "backend" / "app" / "services" / "dashboard.py"

HOM_NAY = dt.date(2026, 9, 16)


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


# ═════════════════ 1 · BA BỀ RỘNG KỲ, VÀ CHỈ KỲ ĐÃ ĐÓNG ═════════════════

def test_cac_ky_chi_lay_ky_da_dong():
    """Luật 1 của xu_huong.py áp cho cả ba bề rộng, không riêng tháng."""
    assert XH.cac_ky(HOM_NAY, 6, "thang")[-1] == "2026-08", "tháng 9 đang chạy, không được vào"
    assert XH.cac_ky(HOM_NAY, 4, "quy")[-1] == "2026-Q2", "quý 3 đang chạy, không được vào"
    assert XH.cac_ky(HOM_NAY, 3, "nam")[-1] == "2025", "năm 2026 đang chạy, không được vào"


def test_cac_ky_xep_cu_truoc_moi_sau_va_lui_dung_moc():
    assert XH.cac_ky(HOM_NAY, 4, "quy") == ["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"]
    assert XH.cac_ky(HOM_NAY, 3, "nam") == ["2023", "2024", "2025"]
    # Lùi qua mốc năm: tháng 1 lùi một tháng phải ra tháng 12 năm trước, không phải tháng 0.
    assert XH.cac_ky(dt.date(2026, 1, 20), 2, "thang") == ["2025-11", "2025-12"]
    assert XH.cac_ky(dt.date(2026, 1, 20), 2, "quy") == ["2025-Q3", "2025-Q4"]


@pytest.mark.parametrize("ky,loai", [
    ("2026-08", "thang"), ("2026-Q3", "quy"), ("2026", "nam"),
])
def test_doc_duoc_be_rong_tu_chinh_ma_ky(ky, loai):
    assert XH.kieu_ky(ky) == loai


def test_thang_cua_ky_dung_bien_quy_va_nam():
    assert XH.thang_cua_ky("2026-Q1") == ["2026-01", "2026-02", "2026-03"]
    assert XH.thang_cua_ky("2026-Q4") == ["2026-10", "2026-11", "2026-12"]
    assert XH.thang_cua_ky("2025")[0] == "2025-01" and XH.thang_cua_ky("2025")[-1] == "2025-12"
    # Tháng trả về CHÍNH NÓ — nhờ vậy nơi gọi không phải rẽ nhánh.
    assert XH.thang_cua_ky("2026-08") == ["2026-08"]
    with pytest.raises(ValueError):
        XH.thang_cua_ky("2026-Q5")


def test_be_rong_ky_la_bi_tu_choi():
    with pytest.raises(ValueError):
        XH.cac_ky(HOM_NAY, 3, "tuan")
    with pytest.raises(ValueError):
        XH.chuoi("doanh_thu_thang", lambda ma, ky: None, kind="tuan")


# ═════════════════ 2 · CỘNG KỲ: DÒNG CHẢY CỘNG, TỒN KHO KHÔNG ═════════════════

SO = {"2026-01": 1.0, "2026-02": 2.0, "2026-03": 3.0,
      "2026-04": 10.0, "2026-05": 20.0, "2026-06": 30.0,
      "2026-07": 40.0, "2026-08": None}


def _doc_gia():
    return XH.doc_theo_ky(lambda ma, ky: SO.get(ky))


def test_dong_chay_cong_duoc_cac_thang_trong_ky():
    d = _doc_gia()
    assert d("doanh_thu_thang", "2026-Q1") == 6.0
    assert d("doanh_thu_thang", "2026-Q2") == 60.0


def test_thieu_mot_thang_thi_ca_ky_chua_co_so():
    """Chỗ hỏng nguy hiểm nhất của phép cộng kỳ, nên canh riêng.

    Quý 3 có tháng 7 (40) và tháng 8 (chưa có số). Cộng phần có rồi gọi đó là "doanh thu quý 3"
    cho ra 40 — một con số NHỎ HƠN thật mà nhìn không khác gì con số đầy đủ. Không ai đi hỏi một
    con số trông bình thường.
    """
    assert _doc_gia()("doanh_thu_thang", "2026-Q3") is None
    assert _doc_gia()("doanh_thu_thang", "2026") is None


def test_ton_kho_khong_cong_ma_lay_thang_cuoi_ky():
    """"Tour đang bán" của quý 2 KHÔNG phải 10+20+30 — một chuyến bán suốt quý bị đếm ba lần."""
    d = _doc_gia()
    assert d("tour_dang_ban", "2026-Q2") == 30.0, "phải lấy số đếm tại NGÀY CUỐI QUÝ"
    assert d("tour_cho_quyet_toan", "2026-Q1") == 3.0


def test_thang_di_thang_qua_khong_bi_boc_them_lop_nao():
    assert _doc_gia()("doanh_thu_thang", "2026-05") == 20.0


# ═════════════════ 3 · KỲ ĐANG CHẠY: CÓ SỐ, NHƯNG KHÔNG VÀO BIỂU ĐỒ ═════════════════

def test_ky_dang_chay_va_cac_thang_da_troi():
    assert XH.ky_dang_chay(HOM_NAY, "thang") == ("2026-09", ["2026-09"])
    assert XH.ky_dang_chay(HOM_NAY, "quy") == ("2026-Q3", ["2026-07", "2026-08", "2026-09"])
    ky, thang = XH.ky_dang_chay(HOM_NAY, "nam")
    assert ky == "2026" and thang[-1] == "2026-09" and len(thang) == 9, (
        "Năm đang chạy chỉ gồm các tháng ĐÃ TRÔI — gồm cả tháng 10 đến 12 là cộng vào những tháng "
        "chưa xảy ra."
    )


def test_bo_ba_ky_dung_ba_chuoi_doc_lap_va_ky_dang_chay_nam_ngoai_bieu_do():
    so = dict(SO); so["2026-09"] = 5.0
    d = XH.doc_theo_ky(lambda ma, ky: so.get(ky))
    b = XH.bo_ba_ky("doanh_thu_thang", d, hom_nay=HOM_NAY)

    assert set(b) == {"thang", "quy", "nam"}
    # Ba chuỗi KHÁC NHAU — quý không lấy bộ số của tháng làm lối lui.
    assert [x["ky"] for x in b["thang"]["diem"]] != [x["ky"] for x in b["quy"]["diem"]]
    assert b["quy"]["kind"] == "quy" and b["nam"]["kind"] == "nam"

    for k in ("thang", "quy", "nam"):
        ky_chay = b[k]["dang_chay"]["ky"]
        assert ky_chay not in [x["ky"] for x in b[k]["diem"]], (
            f"Kỳ đang chạy {ky_chay} lọt vào biểu đồ — nó mới đi được nửa đường, đứng cạnh các kỳ "
            f"đủ ngày thì cột cuối luôn thấp và xu hướng luôn trông như đang lao dốc."
        )
    assert b["thang"]["dang_chay"]["gia_tri"] == 5.0
    # Quý đang chạy = 7 + 8 + 9, mà tháng 8 chưa có số → cả kỳ chưa có số.
    assert b["quy"]["dang_chay"]["gia_tri"] is None


def test_chi_hai_chi_tieu_co_o_chon_ba_ky():
    """CỐ Ý chỉ hai: tồn kho cộng không được, và bốn ô chọn kỳ trên một màn hình thì không ô nào
    còn đáng bấm."""
    assert XH.CHI_TIEU_BA_KY == ("doanh_thu_thang", "ln_ke_toan_thang")


# ═════════════════ 4 · TỒN ĐỌNG THEO MỨC ĐỘ ═════════════════

@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=[Alert.__table__])
    s = sessionmaker(bind=e)()
    try:
        yield s
    finally:
        s.close()


def _cb(db, level, xong=False, n=1):
    for i in range(n):
        db.add(Alert(kind="k", level=level, ref=f"r{level}{i}", message="m", to_roles="",
                     resolved=xong))


def test_chi_dem_viec_chua_xu_ly(db):
    _cb(db, "red", n=3)
    _cb(db, "red", xong=True, n=5)
    db.flush()
    kq = CBM.theo_muc(db)
    assert kq["tong"] == 3, (
        "Đếm cả việc đã xử lý là biến ô 'cần xử lý' thành ô 'đã từng có' — con số ấy chỉ tăng chứ "
        "không bao giờ giảm, và nhìn vào không ai biết hôm nay còn nợ bao nhiêu."
    )


def test_ba_muc_dung_thu_tu_nang_truoc(db):
    _cb(db, "red", n=2); _cb(db, "warn", n=5); _cb(db, "info", n=7)
    db.flush()
    p = CBM.theo_muc(db)["phan"]
    assert [x["ma"] for x in p] == ["red", "warn", "info"]
    assert [x["so"] for x in p] == [2, 5, 7]
    assert p[0]["trang_thai"] is True and p[1]["trang_thai"] is False, (
        "Chỉ mức đỏ mang màu cảnh báo: nó là TRẠNG THÁI (việc đã thành vấn đề), không phải nấc "
        "nặng nhất của một thang."
    )


def test_muc_chua_khai_hien_ra_chu_khong_bien_mat(db):
    """`Alert.level` là cột chuỗi, nên một robot viết sai chính tả là sinh ra mức thứ tư.

    Bỏ qua nó thì tổng trên màn hình NHỎ HƠN số việc thật — sai không ai nhìn ra. Hiện nó ra thì
    trong tuần sẽ có người đi sửa.
    """
    _cb(db, "red", n=1); _cb(db, "nghiem_trong", n=4)
    db.flush()
    kq = CBM.theo_muc(db)
    assert kq["co_muc_la"] is True
    assert kq["tong"] == 5, "Tổng phải gồm cả mức lạ."
    la = [x for x in kq["phan"] if x["ma"] == CBM.CHUA_PHAN_LOAI]
    assert la and la[0]["so"] == 4 and la[0] is kq["phan"][-1], "Nhóm mức lạ đứng cuối và hiện ra."


def test_khong_co_viec_nao_thi_ba_muc_deu_bang_khong(db):
    kq = CBM.theo_muc(db)
    assert kq["tong"] == 0 and kq["co_muc_la"] is False
    assert [x["so"] for x in kq["phan"]] == [0, 0, 0], (
        "Ba mức vẫn phải có mặt với số 0 — ở đây 0 là SỐ THẬT (đã đếm, không có việc nào), khác "
        "hẳn 'chưa có nguồn'."
    )


# ═════════════════ 5 · MÀN HÌNH: SÁU Ô LỚN VÀ NĂM THẺ NHỎ ═════════════════

# SỬA 16/9/2026 (TC-44): sáu Ô vẫn là sáu CON SỐ, nhưng hai con số đầu nay nằm chung MỘT khối
# `<KhoiKetQuaKinhDoanh` với một bộ chọn kỳ dùng chung (bản vẽ anh Tuấn gửi chiều cùng ngày).
# Đổi CÁCH BÀY, không đổi danh sách — nên phép thử vẫn canh đúng điều cũ: đủ mặt và đúng thứ tự.
# SỬA 17/9/2026 (TC-57): Dòng tiền xuống SAU hai khối công nợ và nằm ngang hết bề ngang — anh Tuấn
# chốt. Danh sách vẫn đủ sáu con số, chỉ đổi thứ tự; xem THU_TU_BAN_VE ở test_tc31 cho cả hai vế.
SAU_O_KHOI = ["<KhoiKetQuaKinhDoanh",
              "<KhoiPhaiThu", "<KhoiPhaiTra", "<KhoiDongTien", "<KhoiTonDongMuc"]


def test_du_sau_o_lon_va_dung_thu_tu_anh_Tuan_ke():
    ma = _ma(_doc(TRANG))
    vi = []
    for k in SAU_O_KHOI:
        i = ma.find(k)
        assert i > 0, f"Màn hình 01 thiếu ô lớn {k}"
        vi.append((k, i))
    sai = [(a[0], b[0]) for a, b in zip(vi, vi[1:]) if a[1] > b[1]]
    assert not sai, ("Sáu ô phải đúng thứ tự anh Tuấn kể: "
                     + "; ".join(f"{x} trước {y}" for x, y in sai))


def test_ba_khoi_chuyen_len_khong_de_lai_ban_sao_o_duoi():
    """Anh Tuấn chọn "thay luôn — gộp lên trên". Giữ cả hai chỗ là để một con số nằm hai nơi, đúng
    cái ông bảo bỏ ở vòng TC-40 ("các mục lặp lại thì bỏ hết")."""
    ma = _ma(_doc(TRANG))
    for k in ("<KhoiDongTien", "<KhoiPhaiThu", "<KhoiPhaiTra"):
        assert ma.count(k) == 1, f"{k} xuất hiện {ma.count(k)} lần — một con số, một chỗ, một hình."


def test_the_nho_khong_mang_bieu_do():
    """SỬA 16/9/2026 (TC-46): năm thẻ thành SÁU theo bản vẽ v3.0. Luật thì y nguyên, và nó nằm ở
    phép soát thứ hai: hàng thẻ là những con số để LIẾC, không thẻ nào được mang biểu đồ."""
    ma = _ma(_doc(TRANG))
    khoi = ma[ma.index("const the: The[] = ["): ma.index("];", ma.index("const the: The[] = ["))]
    assert len(re.findall(r'nhan: "', khoi)) == 6
    assert "xu_huong" not in khoi, (
        "Hàng thẻ nhỏ là con số để LIẾC. Thêm hình vào chúng là kéo mắt khỏi sáu ô lớn phía trên — "
        "đúng điều anh Tuấn chốt khi chọn 'thẻ số nhỏ, một hàng, không biểu đồ'."
    )


def test_o_lon_khong_lay_bo_so_cua_thang_lam_loi_lui_cho_quy():
    """Chỗ RẤT dễ làm sai, và đã sai một lần ở khối Hiệu quả đội xe (TC-40).

    SỬA 16/9/2026 (TC-44): hai ô lớn sang KhoiKetQuaKinhDoanh và đổi cách lấy số — hỏi thẳng máy
    chủ đúng kỳ đang chọn thay vì chọn nhánh trong một gói dựng sẵn. Lối lui về bộ số của tháng vì
    thế không còn chỗ tồn tại, nhưng phép thử vẫn phải đứng đây: cách làm đổi, cám dỗ thì không.
    """
    ma = _ma(_doc(KHOI_KQ))
    assert "ket-qua-kinh-doanh?kind=" in ma, "Mỗi kỳ phải hỏi máy chủ đúng kỳ ấy."
    for cam in ("|| ba_ky?.thang", '?? ba_ky?.thang', 'kind === "thang" ? '):
        assert cam not in ma, (
            f"Có lối lui về bộ số của tháng ({cam}). Bấm sang Quý mà thấy y hệt bộ số của Tháng là "
            f"nói dối bằng giao diện — người đọc kết luận quý bằng tháng, chứ không kết luận là "
            f"chưa có số."
        )


def test_o_lon_khong_tu_tinh_con_so_nghiep_vu_nao():
    """Ranh giới 09/9: màn hình bày, máy chủ tính.

    PHÉP SOÁT PHẢI CẤM MỘT HÀNH VI, KHÔNG CẤM MỘT KÝ TỰ — bài học vừa phải trả giá ở TC-41, khi
    một phép soát cấm chuỗi "slice(" trong cả tệp đã báo oan một phép cắt hoàn toàn chính đáng.
    Nên ở đây: bỏ chuỗi ký tự và đường dẫn trước, rồi mới tìm phép chia thật (` / ` giữa hai vế).
    """
    # SỬA 16/9/2026 (TC-44): soát cả khối Kết quả kinh doanh — nơi hai ô lớn chuyển sang, và là
    # nơi có nhiều con số dễ bị tính tại chỗ nhất (tỉ lệ đạt, biên lợi nhuận).
    ma = _ma(_doc(SAU_O) + "\n" + _doc(KHOI_KQ))
    ma = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'|`[^`]*`', '""', ma)   # bỏ mọi chuỗi ký tự
    for dong in ma.splitlines():
        assert "reduce(" not in dong, f"Có phép gộp trên màn hình: {dong.strip()}"
        if re.search(r"\w\s/\s\w|\)\s/\s", dong):
            # Phép chia duy nhất được phép là đổi tỉ lệ sang phần trăm khi IN.
            assert "* 100" in dong or "Math.round" in dong, (
                f"Phép chia trên màn hình phải là phép đổi sang phần trăm khi in: {dong.strip()}"
            )


def test_nhan_truc_khong_bao_gio_mo_ho_ve_nam():
    """Bốn quý gần nhất thường là "Q3 Q4 Q1 Q2" — đọc dãy ấy thì không ai biết Q3 thuộc năm nào,
    và cùng màn hình còn có quý ĐANG CHẠY cũng tên Q3. Tìm ra bằng cách dựng ảnh, không phải bằng
    cách đọc mã.

    SỬA 16/9/2026 (TC-44): bản TC-42 chữa bằng cách THÊM năm vào nhãn khi chuỗi vắt qua hai năm
    (`kem_nam`). Bản vẽ chiều 16/9 chữa tận gốc: trục LUÔN là mười hai tháng của ĐÚNG MỘT năm, và
    năm ấy in ở phụ đề. Không còn chuỗi nào vắt qua hai năm thì cũng không còn nhãn nào mơ hồ.
    Luật không đổi — nhãn trục không được để người đọc phải đoán năm; cách giữ luật thì đổi.
    """
    ma = _ma(_doc(KHOI_KQ))
    assert 'nhan: `T${c.thang}`' in ma, "Trục phải là mười hai tháng, đánh số 1–12."
    assert "12 tháng ${nam}" in ma, "Phụ đề phải in NĂM của mười hai cột ấy."
    assert "cac_thang = [f\"{nam:04d}" in _doc(
        GOC / "backend" / "app" / "services" / "ket_qua_kinh_doanh.py"), (
        "Mười hai cột phải dựng từ MỘT năm ở máy chủ — trộn tháng của hai năm vào một trục là đúng "
        "cái mơ hồ mà phép thử này sinh ra để chặn."
    )


def test_luoi_sau_o_hai_cot_tren_man_rong_va_mot_cot_tren_dien_thoai():
    css = _doc(CSS)
    assert ".mh01-sau-o{" in css, "Thiếu lưới sáu ô"
    i = css.index(".mh01-sau-o{")
    doan = css[i:i + 400]
    assert "grid-template-columns:1fr" in doan, "Điện thoại phải là MỘT cột"
    assert "min-width:900px" in css[i:i + 600] and "1fr 1fr" in css[i:i + 600], (
        "Màn rộng hai cột, KHÔNG phải ba: mỗi ô mang một biểu đồ có trục và nhãn số, ba cột thì "
        "mỗi biểu đồ chỉ còn hơn 300px — cột chồng nhãn, nhãn cắt cụt."
    )


def test_bang_dieu_khien_goi_dung_ham_cua_may_chu():
    ma = _doc(BANG_DIEU_KHIEN)
    assert "XH.ba_ky_cho_man_hinh(db" in ma, "Ba bề rộng kỳ phải do xu_huong dựng."
    assert "CBM.theo_muc(db)" in ma, "Ba mức tồn đọng phải do canh_bao_muc gom."
