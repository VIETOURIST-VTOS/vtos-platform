# -*- coding: utf-8 -*-
"""VT-2 · KHOÁ VIETRIP KHÔNG ĐƯỢC ĐI RA NGOÀI, VÀ CỬA THỬ KHÔNG ĐƯỢC CHẾT — 05/11/2026.

VÒNG NÀY SINH RA TỪ MỘT LẦN RÒ THẬT, không từ một lo xa. Ngày 05/11/2026, sau khi gộp VT-1,
biến `VIETRIP_FINANCE_KEY` trên Render bị dán nhầm CẢ CÂU LỆNH `curl` chép từ tài liệu PDF —
dính luôn hai dấu xuống dòng của chỗ ngắt dòng. `http.client` từ chối tiêu đề có xuống dòng và
ném `ValueError: Invalid header value b'curl -H "X-VieTrip-Key:<KHOÁ>"...'` — KÈM NGUYÊN KHOÁ.

`ValueError` không nằm trong ba loại lỗi mà VT-1 bắt (`HTTPError`, `URLError`,
`JSONDecodeError`), nên nó đi thẳng ra nhật ký Render. Khoá thật nằm nguyên văn trong nhật ký,
nhiều lần, cho tới khi có người đọc nhật ký mới biết. Phép thử `vt1_5` được dựng đúng để chặn
chuyện này — và nó xanh suốt, vì nó chỉ canh ba loại lỗi đã biết.

BÀI HỌC GHIM Ở ĐÂY: chặn rò rỉ bằng cách LIỆT KÊ loại lỗi là không đủ. Phải là mặc định.

  vt2_1  dán cả câu lệnh `curl` — đúng hình dạng đã xảy ra thật — bị chặn, và khoá không lọt ra
  vt2_2  mọi kiểu dán sai đều bị từ chối, lý do KHÔNG chứa giá trị
  vt2_3  lời từ chối nêu tên biến và chỉ đúng chỗ sửa
  vt2_4  «chưa đặt» và «đặt sai» là HAI câu khác nhau, không được gộp
  vt2_5  khoá đúng khuôn thì qua — ghim khuôn hiện tại, Vietrip đổi khuôn là đỏ ở đây
  vt2_6  lỗi LẠ từ thư viện: `goi` giữ tên loại, vứt lời lỗi, không rò khoá qua traceback
  vt2_7  lỗi LẠ: cửa thử KHÔNG ném, và không chữ nào của lời lỗi gốc lọt ra
  vt2_8  cửa thử KHÔNG BAO GIỜ ném, với mọi loại lỗi
  vt2_9  Vietrip đổi khuôn JSON thì cửa thử vẫn trả lời tử tế chứ không 500
  vt2_10 khoá đang sai thì KHÔNG gửi một yêu cầu nào ra ngoài
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from app.services import vietrip_tai_chinh as VTC

KHOA_GIA = "vtfin_KHOA_GIA_DE_THU_khong_phai_khoa_that_123456"

# Đúng hình dạng đã nằm trong nhật ký Render hôm 05/11/2026, chỉ thay khoá thật bằng khoá giả.
DAN_CA_LENH = f'curl -H "X-VieTrip-Key:\n{KHOA_GIA}"\n"https://app.vietrip.com.vn/api/fin'


def _dat(monkeypatch, gia_tri):
    monkeypatch.setenv(VTC.TEN_BIEN, gia_tri)


def _khong_duoc_goi_mang(monkeypatch):
    def _no(*a, **k):
        raise AssertionError("ĐÃ GỬI YÊU CẦU RA NGOÀI trong lúc khoá đang sai")
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _no)


def test_vt2_1_dan_ca_cau_lenh_curl_bi_chan_va_khoa_khong_lot_ra(monkeypatch):
    """Tái dựng đúng sự cố 05/11/2026."""
    _dat(monkeypatch, DAN_CA_LENH)
    _khong_duoc_goi_mang(monkeypatch)

    with pytest.raises(VTC.KhoaDangSai) as e:
        VTC.goi("receipts")
    assert KHOA_GIA not in str(e.value), "KHOÁ NẰM TRONG LỜI BÁO LỖI"
    assert "curl" not in str(e.value).replace(VTC.CACH_SUA, ""), \
        "lời báo đang chép lại giá trị người dùng dán vào"

    kq = VTC.thu_ket_noi()
    van = json.dumps(kq, ensure_ascii=False)
    assert kq["thong"] is False
    assert kq["co_khoa"] is True, "biến CÓ đặt — nói «chưa đặt» là chỉ sai chỗ sửa"
    assert kq["khoa_dung_duoc"] is False
    assert KHOA_GIA not in van, "KHOÁ NẰM TRONG KẾT QUẢ TRẢ VỀ CỦA CỬA THỬ"


@pytest.mark.parametrize("gia_tri,phai_noi", [
    (f"{KHOA_GIA}\n", ""),                                   # xuống dòng ngoài rìa: strip bỏ được
    (f"vtfin_ABC\nDEF", "xuống dòng"),
    (f"vtfin_ABC DEF", "khoảng trắng"),
    (f'"{KHOA_GIA}"', "nháy"),
    (f"X-VieTrip-Key:{KHOA_GIA}", "hai chấm"),
    (f"https://app.vietrip.com.vn/api/finance-data", "câu lệnh hoặc địa chỉ"),
    (DAN_CA_LENH, "khoảng trắng"),
])
def test_vt2_2_moi_kieu_dan_sai_deu_bi_tu_choi_va_khong_in_gia_tri(monkeypatch, gia_tri, phai_noi):
    _dat(monkeypatch, gia_tri)
    ly_do = VTC.soat_khoa()
    if not phai_noi:
        assert ly_do == "", "xuống dòng ở RÌA thì strip() bỏ được, không cần bắt người dán lại"
        return
    assert ly_do, f"lọt qua: {phai_noi}"
    assert phai_noi in ly_do, f"lý do nói không đúng chỗ sai: {ly_do}"
    # Lý do này đi vào nhật ký và vào cửa thử. Không một mẩu nào của giá trị được có mặt.
    for manh in (KHOA_GIA, "vtfin_ABC", "app.vietrip.com.vn", "X-VieTrip-Key"):
        assert manh not in ly_do, f"GIÁ TRỊ LỌT VÀO LÝ DO TỪ CHỐI: {manh}"


def test_vt2_3_loi_tu_choi_neu_ten_bien_va_chi_dung_cho_sua(monkeypatch):
    """Một câu «khoá không hợp lệ» trống không thì người đọc đi soát tường lửa, soát khoá với
    Vietrip, soát mã — ba chỗ đều đúng chẳng chỗ nào sai. Phải chỉ thẳng vào ô giá trị."""
    _dat(monkeypatch, DAN_CA_LENH)
    noi = VTC.thu_ket_noi()["noi"]
    assert VTC.TEN_BIEN in noi, "không nói tên biến thì không biết sửa cái gì"
    assert "Render" in noi and "Environment" in noi, "không nói sửa ở đâu"
    assert "mạng" not in noi.lower(), "đây KHÔNG phải lỗi mạng, nói thế là chỉ sai chỗ"


def test_vt2_4_chua_dat_va_dat_sai_la_hai_cau_khac_nhau(monkeypatch):
    monkeypatch.delenv(VTC.TEN_BIEN, raising=False)
    chua = VTC.thu_ket_noi()
    _dat(monkeypatch, DAN_CA_LENH)
    sai = VTC.thu_ket_noi()
    assert chua["co_khoa"] is False and sai["co_khoa"] is True
    assert chua["noi"] != sai["noi"], "gộp hai việc vào một câu là bắt người đọc đoán"


def test_vt2_5_khoa_dung_khuon_thi_qua_duoc(monkeypatch):
    """Ghim KHUÔN khoá Vietrip đang dùng: chữ, số, gạch dưới. Nếu mai kia Vietrip cấp khoá có
    dấu hai chấm hay chữ `http` bên trong thì phép thử này ĐỎ — cố ý, để `soat_khoa()` được
    nới ra một cách có ý thức chứ không phải lặng lẽ chặn khoá thật."""
    for khoa in (KHOA_GIA, "vtfin_2abcDEF_0123456789", "a" * 54):
        _dat(monkeypatch, khoa)
        assert VTC.soat_khoa() == "", f"khoá đúng khuôn mà bị chặn: {len(khoa)} ký tự"
        assert VTC.co_khoa() is True


def test_vt2_6_loi_la_giu_ten_loai_vut_loi_loi_va_khong_ro_khoa(monkeypatch):
    """Đây chính là lỗi đã xảy ra: `ValueError` từ `http.client`, mang theo cả tiêu đề."""
    _dat(monkeypatch, KHOA_GIA)

    def _no_ra_loi_la(*a, **k):
        raise ValueError(f"Invalid header value b'X-VieTrip-Key:{KHOA_GIA}'")
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _no_ra_loi_la)

    with pytest.raises(VTC.LoiGoi) as e:
        VTC.goi("receipts")

    assert e.value.ma == -2, "lỗi lạ phải có mã riêng, không trộn vào mã HTTP thật"
    assert e.value.loai == "ValueError", "mất tên loại thì không lần ra được chỗ hỏng"
    assert KHOA_GIA not in str(e.value), "KHOÁ NẰM TRONG LỜI BÁO LỖI"
    assert "Invalid header value" not in str(e.value), "đang chép lại lời lỗi gốc"

    in_ra = "".join(traceback.format_exception(type(e.value), e.value, e.value.__traceback__))
    assert KHOA_GIA not in in_ra, "KHOÁ NẰM TRONG CHUỖI LỖI PYTHON IN RA NHẬT KÝ"
    assert e.value.__cause__ is None
    assert e.value.__suppress_context__ is True, \
        "chưa chặn in lỗi gốc — chính lỗi gốc là thứ đã mang khoá ra nhật ký hôm 05/11"


def test_vt2_7_loi_la_thi_cua_thu_khong_nem_va_khong_ro_gi(monkeypatch):
    _dat(monkeypatch, KHOA_GIA)

    def _no_ra_loi_la(*a, **k):
        raise ValueError(f"Invalid header value b'X-VieTrip-Key:{KHOA_GIA}'")
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _no_ra_loi_la)

    kq = VTC.thu_ket_noi()                       # KHÔNG được ném
    van = json.dumps(kq, ensure_ascii=False)
    assert kq["thong"] is False
    assert KHOA_GIA not in van, "KHOÁ LỌT RA CỬA THỬ"
    assert "Invalid header value" not in van, "lời lỗi gốc lọt ra cửa thử"
    assert "ValueError" in van, "mất tên loại lỗi thì cửa thử không giúp lần ra chỗ hỏng"


@pytest.mark.parametrize("loi", [
    ValueError("x"), TypeError("x"), KeyError("x"), OSError("x"),
    RuntimeError("x"), UnicodeEncodeError("utf-8", "x", 0, 1, "x"), MemoryError(),
])
def test_vt2_8_cua_thu_khong_bao_gio_nem(monkeypatch, loi):
    """Cửa chẩn đoán mà trả 500 là cửa im lặng đúng lúc cần nói nhất — và mỗi 500 lại kéo thêm
    một chuỗi lỗi vào nhật ký, đúng chỗ khoá đã rò lần trước."""
    _dat(monkeypatch, KHOA_GIA)

    def _no(*a, **k):
        raise loi
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _no)

    kq = VTC.thu_ket_noi()
    assert isinstance(kq, dict) and kq["thong"] is False
    assert type(loi).__name__ in json.dumps(kq, ensure_ascii=False)


def test_vt2_9_vietrip_doi_khuon_json_thi_van_tra_loi_tu_te(monkeypatch):
    """Tài liệu nói cửa trả một đối tượng có `total`/`data`. Nếu một ngày nó trả thẳng một
    mảng, `.get` nổ — và nổ ở chỗ dựng câu trả lời thì vẫn là 500."""
    _dat(monkeypatch, KHOA_GIA)

    class _Tra:
        def read(self): return json.dumps([{"bookingId": 1}]).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(VTC.urllib.request, "urlopen", lambda *a, **k: _Tra())
    kq = VTC.thu_ket_noi()
    assert kq["thong"] is False and "loai_loi" in kq
    assert "bookingId" not in json.dumps(kq, ensure_ascii=False), "dữ liệu khách lọt ra"


def test_vt2_10_khoa_dang_sai_thi_khong_goi_mang(monkeypatch):
    """Gọi đi với một tiêu đề hỏng là vừa chắc chắn hỏng, vừa đẩy giá trị ấy qua thư viện —
    tức qua đúng chỗ đã rò. Chặn ngay ở nhà."""
    _dat(monkeypatch, DAN_CA_LENH)
    _khong_duoc_goi_mang(monkeypatch)
    assert VTC.thu_ket_noi()["thong"] is False
    assert VTC.thu_ket_noi("receipts")["thong"] is False
