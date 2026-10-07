# -*- coding: utf-8 -*-
"""TX-5 · Cửa nạp cho GPS / thẻ dầu / ePass — Chủ tịch chốt 07/10/2026.

> "GPS / thẻ dầu / ePass — cửa nạp tệp sao kê, bước rẻ nhất trong ba bước anh chốt."

Rà xong thì ba thứ ấy không cùng tình trạng, và chỗ hỏng không nằm ở chỗ tưởng:

  THẺ DẦU  — đã có cửa nạp (`nhien_lieu` → `fleet_external_txns`). Không phải việc của vòng này.
  ePass    — đã có cửa nạp (`phi_cau_duong` → cùng bảng), NHƯNG đội xe đi đường bằng HAI VÍ thuộc
             HAI PHÁP NHÂN (V001889627 = Vận tải Vietrip, V003014969 = Vietourist). Cửa nạp không có
             ô tài khoản và hàm ghi không ghi cột `tai_khoan`, nên giao dịch của cả hai ví rơi chung
             một rổ `source="epass"`. TỔNG VẪN ĐÚNG, phần của từng pháp nhân mới sai — nên không ai
             nhìn ra. Đúng một kiểu hỏng với doanh thu thuê xe lẫn vào doanh thu tour (TX-4).
  GPS      — mới là chỗ trống thật, và trống theo kiểu tệ nhất. `Trip.km_gps` có cột, tham số ngưỡng
             `xe_lech_km_gps` có, và `services/fleet.py::kiem_chuyen` ĐỌC `km_gps` để bật cờ ĐỎ khi
             đồng hồ lệch GPS. Nhưng không một bộ nạp nào, không một màn hình nào từng GHI `km_gps`.
             Một cái cờ không bao giờ đỏ được thì vô hại về số và nguy hiểm về niềm tin: người xem
             tin là đã đối chiếu, trong khi chưa bao giờ đối chiếu.

Hai cái bẫy vòng này cố ý canh, vì cả hai đều "chạy xanh" mà sai:

  1. LẤY GPS SO VỚI GPS. Nếu km đầu/cuối cũng lấy từ cổng GPS thì phép so lệch luôn khớp. Vì vậy số
     km phải đi kèm NGUỒN (`KM_NGUON`), và khi nguồn là gps_* thì cờ nói thẳng "chưa đối chiếu".
  2. ĐOÁN HỘ VÍ LẠ. Ví thứ ba xuất hiện thì bộ nạp CẢNH BÁO chứ không chặn và không đoán. Chặn là
     một tệp không nạp được; đoán là số của ví mới chạy vào tên pháp nhân cũ — hỏng hơn cái đang sửa.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.models.fleet import KM_NGUON, VI_EPASS                        # noqa: E402
from app.services import intake as IN                                  # noqa: E402
from app.services import intake_phong_ban_2 as IP2                     # noqa: E402


def _doc(*phan):
    with open(os.path.join(GOC, *phan), encoding="utf-8") as f:
        return f.read()


def _cot(bo: dict) -> dict:
    return {c["key"]: c for c in bo["cot"]}


# ───────────────────────── nửa GPS ─────────────────────────
def test_cua_nap_chuyen_xe_co_o_km_gps_va_nguon():
    """Cửa nạp chuyến xe phải có CẢ HAI ô: số GPS và nguồn của số km.

    Chỉ thêm ô `km_gps` mà không có `km_nguon` thì rơi vào bẫy số 1 – lấy GPS so với GPS."""
    bo = IN.BO_NAP["chuyen_xe"]
    c = _cot(bo)
    assert "km_gps" in c, ("Bộ nạp chuyến xe thiếu ô 'Km theo GPS'. Cột Trip.km_gps có người ĐỌC "
                           "(services/fleet.py::kiem_chuyen bật cờ đỏ khi lệch) mà không có người GHI – "
                           "cờ ấy chưa từng chạy một lần nào.")
    assert "km_nguon" in c, ("Bộ nạp chuyến xe thiếu ô 'Nguồn số km'. Số đo không kèm nguồn thì không "
                             "biết km đầu/cuối là số đồng hồ hay số GPS, và lấy GPS so GPS thì luôn khớp.")


def test_nap_chuyen_xe_de_trong_km_gps_la_chua_do_khong_phai_khong():
    """Ô trống phải thành None, không được thành 0.

    Dùng 0 làm 'chưa có' là cách chắc chắn nhất để một ngày nào đó hệ thống báo lệch GPS 100%."""
    nguon = _doc("app", "services", "intake.py")
    assert 'int(_so(r.get("km_gps"))) or None' in nguon, (
        "Hàm nạp chuyến xe phải quy ô km_gps trống về None. Ghi 0 là tạo ra một số đo không tồn tại, "
        "và phép so lệch sẽ chia cho 0 hoặc báo lệch 100% cho mọi chuyến chưa đo.")


def test_moi_cong_gps_dang_dung_deu_co_trong_danh_muc():
    """Ba cổng giám sát hành trình Chủ tịch cho biết 07/10/2026 phải khai đủ, mỗi cổng một giá trị.

    Gộp cả ba vào một giá trị 'gps' thì khi hai cổng vênh nhau không ai biết hỏi bên nào."""
    for k in ("gps_ttc", "gps_tcd", "gps_vietmap"):
        assert k in KM_NGUON, (f"Thiếu cổng GPS '{k}' trong KM_NGUON. Ba cổng đang dùng là TTC, TCD và "
                               "Vietmap; gộp chung một giá trị thì lúc hai cổng vênh nhau không truy được.")
    assert "anh_dong_ho" in KM_NGUON, ("Thiếu 'anh_dong_ho'. Phải có ít nhất một nguồn ĐỌC TỪ ĐỒNG HỒ, "
                                       "không thì không còn gì để đối chiếu với số GPS.")
    assert "gps" in KM_NGUON, ("Đừng bỏ giá trị cũ 'gps' – các dòng đã nạp trước 07/10/2026 ghi đúng chữ "
                               "ấy. Bỏ đi là những dòng đó thành nguồn không tra ra được.")


def test_co_lech_gps_khong_tu_so_voi_chinh_no():
    """Khi km đầu/cuối cũng lấy từ GPS thì cờ phải nói 'chưa đối chiếu', không được báo xanh."""
    nguon = _doc("app", "services", "fleet.py")
    assert '(t.km_nguon or "").startswith("gps")' in nguon, (
        "services/fleet.py::kiem_chuyen phải xét km_nguon trước khi so lệch GPS. Nếu chính km đầu/cuối "
        "lấy từ cổng GPS thì đây là lấy GPS so với GPS: luôn khớp, luôn xanh, và cái xanh ấy làm người "
        "xem tin là đã kiểm trong khi chưa kiểm gì cả.")
    assert "CHƯA ĐỐI CHIẾU" in nguon, (
        "Phải có một câu nói thẳng ra là chưa đối chiếu được. Im lặng ở đây đồng nghĩa với báo xanh.")


def test_co_so_gps_thi_phai_noi_lay_tu_cong_nao():
    """Cửa chuyến xe phải từ chối số GPS không kèm nguồn."""
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert "Có số km theo GPS nhưng chưa ghi nguồn số km" in nguon, (
        "POST /chuyen phải chặn trường hợp có km_gps mà không có km_nguon. Số GPS không biết của cổng "
        "nào thì lúc đối chất với nhà cung cấp không có gì để đối chất.")
    assert "data.km_nguon not in KM_NGUON" in nguon, (
        "POST /chuyen phải kiểm km_nguon theo danh mục KM_NGUON. Nhận chữ tự do là ba tháng sau có "
        "'GPS', 'gps ', 'Vietmap' và 'vietmap' cùng tồn tại trong một cột.")


# ───────────────────────── nửa ePass ─────────────────────────
def test_hai_vi_epass_duoc_khai_dich_danh():
    """Hai ví của hai pháp nhân phải khai rõ số nào của bên nào."""
    assert "V001889627" in VI_EPASS and "V003014969" in VI_EPASS, (
        "VI_EPASS phải khai đủ hai ví ePass đội xe đang dùng (Chủ tịch cho biết 07/10/2026). Thiếu một "
        "ví là chi phí cầu đường của một pháp nhân không quy được về đâu.")
    assert len(set(VI_EPASS.values())) == len(VI_EPASS), (
        "Hai ví phải mang tên hai pháp nhân khác nhau – nếu trùng tên thì tách ra để làm gì.")


def test_cua_nap_epass_co_o_tai_khoan():
    bo = IN.BO_NAP["phi_cau_duong"]
    assert "tai_khoan" in _cot(bo), (
        "Bộ nạp 'Phí cầu đường' thiếu ô Tài khoản ePass. Mỗi tệp sao kê tải từ MỘT ví; không có ô này "
        "thì giao dịch của hai pháp nhân cộng chung một rổ – tổng vẫn khớp nên không ai nhìn ra.")


def test_ham_ghi_giao_dich_co_ghi_cot_tai_khoan():
    nguon = _doc("app", "services", "intake_phong_ban_2.py")
    assert 'tai_khoan=str(r.get("tai_khoan") or "").strip()[:40]' in nguon, (
        "_gd_nap phải ghi cột tai_khoan. Trước 07/10/2026 cột này có trong bảng mà không ai ghi: ô nhập "
        "thêm vào cửa nạp cũng vô nghĩa nếu hàm ghi bỏ qua giá trị đó.")


def test_vi_la_thi_canh_bao_chu_khong_chan_va_khong_doan():
    """Ví chưa khai: cảnh báo. Không chặn tệp, và tuyệt đối không gán hộ vào một pháp nhân."""
    nguon = _doc("app", "services", "intake_phong_ban_2.py")
    assert "chưa khai trong hệ thống" in nguon, (
        "_epass_kiem phải cảnh báo khi số tài khoản không nằm trong VI_EPASS. Im lặng ở đây là ví thứ ba "
        "nằm lẫn trong bảng mà không ai biết đã có ví thứ ba.")
    i = nguon.index("def _epass_kiem")
    than = nguon[i:nguon.index("def _epass_nap")]
    assert "loi.append" not in than, (
        "_epass_kiem không được CHẶN vì ví lạ – một ví mới mở sẽ thành một tệp không nạp được. Cảnh báo "
        "là đủ: dòng vẫn vào bảng với đúng số tài khoản của nó.")
    for ma in VI_EPASS:
        assert f'"{ma}"' not in than.replace(f'f"{ma}"', ""), (
            f"_epass_kiem không được gán cứng ví '{ma}' làm giá trị mặc định. Đoán hộ thì số của ví mới "
            "chạy vào tên pháp nhân cũ – hỏng nặng hơn chính cái đang đi sửa.")


def test_cua_doc_giao_dich_chia_theo_vi():
    """Ghi được mà không đọc ra thì vẫn là một cột không ai dùng."""
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert '"theo_vi"' in nguon, (
        "GET /giao-dich phải chia tổng theo ví ePass. Một cột chỉ có người ghi mà không có người đọc thì "
        "hai pháp nhân vẫn đang bị cộng chung trên mọi báo cáo – đúng chỗ hỏng vòng này đi sửa.")
    assert '"tong_chua_quy_ve_vi"' in nguon, (
        "Phải ĐẾM RIÊNG phần chưa ghi tài khoản. Các kỳ sao kê cũ không có cột này; không đếm được thì "
        "không biết còn nợ bao nhiêu, và sớm muộn có người chia hộ theo tỷ lệ.")


def test_khong_chia_ho_theo_ty_le():
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert "không phải chia hộ theo tỷ lệ" in nguon, (
        "Giữ lại câu dặn trong mã: phần chưa quy được về ví phải nạp lại tệp có cột tài khoản, không "
        "được phân bổ theo tỷ lệ. Phân bổ theo tỷ lệ là bịa ra số của từng pháp nhân.")
