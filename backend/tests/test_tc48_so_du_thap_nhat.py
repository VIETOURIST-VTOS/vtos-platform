# -*- coding: utf-8 -*-
"""TC-48 · SỐ DƯ THẤP NHẤT DỰ KIẾN — đáy của dự báo 13 tuần, thay cho số dư cuối kỳ.

Anh Tuấn 17/9/2026, sau khi em giải thích "số dư tuần 13" là gì:

    "để đáy thấp nhất, bỏ số tuần 13"

══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ HỎNG GỐC — MỘT CON SỐ ĐÚNG TRẢ LỜI MỘT CÂU KHÔNG AI HỎI
══════════════════════════════════════════════════════════════════════════════════════════════
`dashboard.build` in `so_du_tuan_13 = fc["closing"]` — số dư CUỐI tuần thứ 13. Con số ấy có thật.
Nhưng dòng tiền có thể tụt ÂM ở tuần 5 rồi thu về hồi lại, và cuối tuần 13 vẫn dương đẹp. Màn hình
in con số đẹp ấy, còn chỗ phải xoay tiền thì nằm khuất sau nó.

Hệ thống VẪN BIẾT tuần 5: `alerts` có một dòng cho nó. Nhưng cảnh báo là CHỮ, còn con số to nhất
trên màn hình là con số che nó đi — mắt đọc số trước khi đọc chữ.

══════════════════════════════════════════════════════════════════════════════════════════════
NĂM CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. LẤY CUỐI KỲ THAY VÌ LẤY ĐÁY. Chính chỗ hỏng gốc. Hai con số trùng nhau ở phần lớn các tháng —
   nên một bản sửa nhầm vẫn chạy đúng hàng tháng trời, rồi sai đúng vào tháng có hố.
2. HOÀ NHAU LẤY NHẦM TUẦN SAU. Hai tuần cùng chạm đáy thì tuần SỚM mới là tuần phải xoay tiền;
   tuần sau chỉ là hệ quả. Báo tuần 9 trong khi phải hành động từ tuần 5 là mất bốn tuần.
3. DÃY RỖNG TRẢ 0. Không có tuần nào thì không có đáy nào. Trả 0 là bịa ra một con số — và 0 đồng
   trên khối dòng tiền đọc ra là "sắp hết tiền", tức bịa đúng cái cảnh báo nguy hiểm nhất.
4. GỘP "ÂM" VỚI "DƯỚI NGƯỠNG" LÀM MỘT. Âm = không đủ tiền trả, vỡ kế hoạch. Dưới ngưỡng = vẫn trả
   được nhưng thủng lớp đệm. Gộp lại thì công ty sắp mất khả năng chi trả trông y hệt công ty mỏng
   đệm — hai tình huống đòi hai hành động khác hẳn nhau.
5. GIỮ SONG SONG CẢ HAI CON SỐ. Anh Tuấn chọn BỎ HẲN số cuối kỳ. Hai con số dòng tiền cạnh nhau
   thì người đọc phải nhớ con nào là con nào, và con dễ đọc hơn (cuối kỳ, thường dương) sẽ thắng.
"""
import datetime as dt
import re
from pathlib import Path

from app.services import finance as F

GOC = Path(__file__).resolve().parents[2]
DICH_VU = GOC / "backend" / "app" / "services" / "finance.py"
BANG = GOC / "backend" / "app" / "services" / "dashboard.py"
KHOI = GOC / "web" / "components" / "KhoiDongTien.tsx"
TRANG = GOC / "web" / "app" / "page.tsx"
CSS = GOC / "web" / "app" / "globals.css"

NGUONG = 500.0


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_py(s: str) -> str:
    """Bỏ chuỗi tài liệu và chú thích — canh HÀNH VI, không canh chữ trong lời giải thích.

    Bài học TC-41, và vòng TC-47 vừa gặp lại: một phép thử đòi chuỗi "_month_tours" có mặt vẫn
    XANH sau khi lời gọi ấy bị bỏ, vì chuỗi còn nằm trong chú thích giải thích vì sao nó bị bỏ.
    """
    s = re.sub(r'"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


def _tuan(so: int, closing: float) -> dict:
    """Một tuần giả. `day_thap_nhat` là hàm THUẦN nên thử được bằng danh sách, không cần dựng sổ."""
    d = dt.date(2026, 9, 21) + dt.timedelta(days=7 * (so - 1))
    return {"week": so, "from": d, "to": d + dt.timedelta(days=6), "closing": closing}


# ═════════════════ 1 · LẤY ĐÁY, KHÔNG LẤY CUỐI KỲ ═════════════════

def test_lay_day_chu_khong_lay_tuan_cuoi():
    """Chỗ hỏng số 1 — dựng đúng tình huống che giấu: âm giữa kỳ, dương cuối kỳ."""
    rows = [_tuan(1, 8000.0), _tuan(2, 6500.0), _tuan(3, 3000.0), _tuan(4, 900.0),
            _tuan(5, -1200.0), _tuan(6, 900.0), _tuan(7, 2000.0), _tuan(8, 4800.0)]
    r = F.day_thap_nhat(rows, NGUONG)
    assert r["gia_tri"] == -1200.0, (
        "Cuối kỳ 4.800 nhìn rất yên tâm, nhưng tuần 5 công ty âm 1.200 — đó mới là con số bắt "
        "người đọc phải làm gì đó."
    )
    assert r["tuan"] == 5
    assert r["tu_ngay"] == dt.date(2026, 10, 19)


def test_day_van_dung_khi_ca_day_deu_duong_va_di_len():
    """Không có hố thì đáy là tuần đầu — vẫn phải ra một con số, không phải None."""
    rows = [_tuan(i, 1000.0 * i) for i in range(1, 6)]
    r = F.day_thap_nhat(rows, NGUONG)
    assert r["gia_tri"] == 1000.0 and r["tuan"] == 1
    assert r["am"] is False and r["duoi_nguong"] is False


# ═════════════════ 2 · HOÀ NHAU THÌ LẤY TUẦN SỚM NHẤT ═════════════════

def test_hoa_nhau_lay_tuan_som_nhat():
    """Chỗ hỏng số 2. Tuần sớm là tuần phải xoay tiền; tuần sau chỉ là hệ quả."""
    rows = [_tuan(1, 5000.0), _tuan(5, -300.0), _tuan(7, 2000.0), _tuan(9, -300.0)]
    r = F.day_thap_nhat(rows, NGUONG)
    assert r["tuan"] == 5, (
        "Báo tuần 9 trong khi phải hành động từ tuần 5 là mất bốn tuần chuẩn bị."
    )


# ═════════════════ 3 · RỖNG KHÁC KHÔNG ═════════════════

def test_day_rong_tra_none_chu_khong_tra_khong():
    """Chỗ hỏng số 3. 0 đồng trên khối dòng tiền đọc ra là 'sắp hết tiền'."""
    assert F.day_thap_nhat([], NGUONG) is None


def test_khoi_man_hinh_khong_ve_gi_khi_chua_co_so():
    """Không có đáy thì không vẽ dòng nào — không in '0 đ' thay cho ô trống."""
    ma = _doc(KHOI)
    assert "d.gia_tri === null || d.gia_tri === undefined) return null" in ma, (
        "Chưa có số thì khối phải trả về null, không dựng một dòng rỗng mang số 0."
    )


# ═════════════════ 4 · "ÂM" VÀ "DƯỚI NGƯỠNG" LÀ HAI VIỆC ═════════════════

def test_am_va_duoi_nguong_la_hai_co_khac_nhau():
    """Chỗ hỏng số 4 — ba mức, mỗi mức một hành động khác nhau."""
    tren = F.day_thap_nhat([_tuan(1, 900.0)], NGUONG)
    assert tren["am"] is False and tren["duoi_nguong"] is False

    mong = F.day_thap_nhat([_tuan(1, 200.0)], NGUONG)
    assert mong["am"] is False and mong["duoi_nguong"] is True, (
        "Vẫn trả được nhưng thủng lớp đệm — khác hẳn không đủ tiền trả."
    )

    vo = F.day_thap_nhat([_tuan(1, -200.0)], NGUONG)
    assert vo["am"] is True and vo["duoi_nguong"] is True


def test_thieu_so_voi_nguong_tinh_ca_phan_am():
    """Ngưỡng 500, đáy −200 thì phải bù 700 mới chạm ngưỡng, không phải 500."""
    assert F.day_thap_nhat([_tuan(1, -200.0)], NGUONG)["thieu_so_voi_nguong"] == 700.0
    assert F.day_thap_nhat([_tuan(1, 200.0)], NGUONG)["thieu_so_voi_nguong"] == 300.0
    assert F.day_thap_nhat([_tuan(1, 900.0)], NGUONG)["thieu_so_voi_nguong"] == 0.0, (
        "Đáy đã trên ngưỡng thì không thiếu gì cả — không trả số âm."
    )


def test_khoi_man_hinh_phan_biet_du_ba_muc():
    ma = _doc(KHOI)
    assert 'd.am ? "red"' in ma and 'd.duoi_nguong ? "warn"' in ma, (
        "Ba mức phải đọc ra được từ màu, không gộp hai mức đầu làm một."
    )


# ═════════════════ 5 · BỎ HẲN SỐ CUỐI KỲ ═════════════════

def test_bang_dieu_hanh_khong_con_tra_so_du_cuoi_ky():
    """Chỗ hỏng số 5 — canh HÀNH VI: trong MÃ (đã bỏ chú thích) không còn phép gán ấy."""
    ma = _ma_py(_doc(BANG))
    assert 'k["so_du_thap_nhat"]' in ma
    assert "so_du_tuan_13" not in ma, (
        "Giữ song song hai con số thì con dễ đọc hơn (cuối kỳ, thường dương) sẽ thắng."
    )


def test_du_bao_van_tra_day_cho_nguoi_goi():
    """`forecast_13w` phải gắn `thap_nhat` vào gói trả về, không để nơi gọi tự đi tìm đáy."""
    ma = _ma_py(_doc(DICH_VU))
    assert '"thap_nhat": day_thap_nhat(rows, min_cash)' in ma


def test_trang_truyen_day_xuong_khoi_dong_tien():
    ma = _doc(TRANG)
    assert "day={d.kpis?.so_du_thap_nhat}" in ma


# ═════════════════ RANH GIỚI 09/9 VÀ BỘ NHẬN DIỆN ═════════════════

def test_khoi_chi_ra_cua_nhap_chu_khong_tu_nhap():
    """Dự báo dựng một phần từ bảng kế hoạch thu–chi do Kế toán gõ — màn hình phải chỉ tới cửa ấy."""
    ma = _doc(KHOI)
    assert "/finance?tab=forecast" in ma, (
        "Ranh giới 09/9: màn hình chỉ bày, và phải nói được số này vào hệ thống bằng cửa nào."
    )


def test_css_khong_go_ma_mau_moi():
    """Ba mức dùng lại đúng ba màu của bộ nhận diện — không khai màu mới cho riêng khối này."""
    css = _doc(CSS)
    khoi = css.split(".dt-day{")[1].split("\n.dt-day-phu")[0]
    assert not re.search(r"#[0-9a-fA-F]{3,6}", khoi), "Phải dùng biến --vtos-*, không gõ mã màu."
    for bien in ("--vtos-success", "--vtos-warning", "--vtos-danger"):
        assert bien in khoi
