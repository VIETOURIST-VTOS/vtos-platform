# -*- coding: utf-8 -*-
"""VT-1 · BỘ GỌI HAI CỬA TÀI CHÍNH VIETRIP và CỬA THỬ ĐƯỜNG — 05/11/2026.

VÌ SAO CÓ VÒNG NÀY. Vietrip mở hai cửa JSON chỉ đọc (`/receipts`, `/receivables`) thay cho hai
đường VTOS đang dùng, cả hai đều yếu: công nợ NẠP TAY mỗi sáng (quên một ngày là màn Chủ tịch
nói số hôm trước mà không gì báo), và phiếu thu lấy bằng cách ĐĂNG NHẬP BẰNG MẬT KHẨU rồi ĐỌC
HTML (đổi bố cục trang là gãy, đổi mật khẩu cũng gãy — đã gãy thật nhiều lần).

VÒNG NÀY CHƯA ĐỒNG BỘ GÌ. Không máy nào trong tay làn này gọi được tới `app.vietrip.com.vn`,
nên viết bộ đồng bộ bây giờ là viết dựa trên một tệp PDF chứ không dựa trên thứ máy chủ Vietrip
thật sự trả về. Dựng bộ gọi + một cửa để người thật tự xem đường có thông không, rồi mới xây.

  vt1_1  chưa đặt khoá thì nói ĐÚNG là chưa đặt, không nói là lỗi mạng
  vt1_2  gọi đúng địa chỉ, đúng tên header, và tham số rỗng thì BỎ chứ không gửi đi
  vt1_3  cửa lạ bị chặn ngay, không gửi một yêu cầu nào ra ngoài
  vt1_4  mỗi mã HTTP nói đúng việc phải làm
  vt1_5  KHOÁ KHÔNG BAO GIỜ lọt vào lời báo lỗi hay kết quả trả về
  vt1_6  cửa thử KHÔNG trả về dòng dữ liệu nào
  vt1_7  khoá không nằm trong mã nguồn, và tên biến khai đúng một chỗ
  vt1_8  cửa thử gắn được vào app và chặn đúng vai
"""
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from app.services import vietrip_tai_chinh as VTC

KHOA_GIA = "vtfin_KHOA_GIA_DE_THU_khong_phai_khoa_that_123456"


@pytest.fixture()
def co_khoa(monkeypatch):
    monkeypatch.setenv(VTC.TEN_BIEN, KHOA_GIA)


@pytest.fixture()
def khong_khoa(monkeypatch):
    monkeypatch.delenv(VTC.TEN_BIEN, raising=False)


def test_vt1_1_chua_dat_khoa_thi_noi_dung_la_chua_dat(khong_khoa):
    """«Chưa đặt khoá» và «không nối được mạng» là HAI việc sửa khác hẳn nhau. Gộp chúng vào
    một câu là người đọc đi sửa nhầm chỗ — đi soát tường lửa trong khi chỉ thiếu một biến."""
    assert VTC.co_khoa() is False
    kq = VTC.thu_ket_noi()
    assert kq["thong"] is False and kq["co_khoa"] is False
    assert VTC.TEN_BIEN in kq["noi"], "không nói tên biến thì người đọc không biết đặt cái gì"
    assert "mạng" not in kq["noi"].lower()
    with pytest.raises(VTC.ChuaCoKhoa):
        VTC.goi("receivables")


def test_vt1_2_goi_dung_dia_chi_dung_header_va_bo_tham_so_rong(co_khoa, monkeypatch):
    da_goi = {}

    class _Tra:
        def read(self): return json.dumps({"total": 7, "data": []}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _mo(req, timeout=None):
        da_goi["url"] = req.full_url
        da_goi["headers"] = dict(req.headers)
        da_goi["timeout"] = timeout
        return _Tra()

    monkeypatch.setattr(VTC.urllib.request, "urlopen", _mo)
    VTC.goi("receivables", departFrom="2026-11-01", includePaid=None, page="", pageSize=1)

    assert da_goi["url"].startswith("https://app.vietrip.com.vn/api/finance-data/receivables?")
    # Tên header phải ĐÚNG CHỮ HOA CHỮ THƯỜNG như tài liệu; urllib viết hoa chữ đầu mỗi từ.
    assert any(k.lower() == "x-vietrip-key" for k in da_goi["headers"]), da_goi["headers"]
    assert "departFrom=2026-11-01" in da_goi["url"] and "pageSize=1" in da_goi["url"]
    assert "includePaid" not in da_goi["url"], "gửi tham số rỗng là một bộ lọc KHÁC với không gửi"
    assert "page=" not in da_goi["url"].replace("pageSize=", "")
    assert da_goi["timeout"] == VTC.HAN_CHO


def test_vt1_3_cua_la_bi_chan_truoc_khi_goi(co_khoa, monkeypatch):
    def _no_goi(*a, **k):
        raise AssertionError("đã gửi yêu cầu ra ngoài với một cửa không có thật")
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _no_goi)
    with pytest.raises(ValueError):
        VTC.goi("khong-co-cua-nay")


@pytest.mark.parametrize("ma,phai_co", [(401, "khoá"), (429, "1 phút"), (500, "Vietrip")])
def test_vt1_4_moi_ma_http_noi_dung_viec_phai_lam(co_khoa, monkeypatch, ma, phai_co):
    def _hong(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, ma, "x", {}, None)
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _hong)
    kq = VTC.thu_ket_noi()
    assert kq["thong"] is False and kq["ma_http"] == ma
    assert phai_co.lower() in kq["noi"].lower(), f"mã {ma} báo không rõ phải làm gì: {kq['noi']}"


def test_vt1_5_khoa_khong_bao_gio_lot_ra_ngoai(co_khoa, monkeypatch):
    """Thư viện có thể kèm cả tiêu đề yêu cầu — tức cả khoá — vào chuỗi lỗi, và chuỗi lỗi thì
    đi thẳng vào nhật ký máy chủ, nơi nhiều người đọc được. Đây là chỗ khoá rò ra dễ nhất."""
    def _hong(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, f"từ chối, header={dict(req.headers)}", {}, None)
    monkeypatch.setattr(VTC.urllib.request, "urlopen", _hong)

    with pytest.raises(VTC.LoiGoi) as e:
        VTC.goi("receipts")
    assert KHOA_GIA not in str(e.value), "KHOÁ NẰM TRONG LỜI BÁO LỖI"

    # SOÁT CẢ CHUỖI LỖI IN RA, không chỉ câu của mình. Bản đầu của phép thử này chỉ xem
    # `__cause__`, mà bỏ `from None` thì lỗi gốc đi vào `__context__` chứ không phải `__cause__`
    # — nên phá chốt mà phép thử vẫn xanh, lượt kiểm ngược bắt được. Python in cả chuỗi ấy ra
    # («During handling of the above exception…»), và chuỗi ấy đi thẳng vào nhật ký máy chủ.
    import traceback
    in_ra = "".join(traceback.format_exception(type(e.value), e.value, e.value.__traceback__))
    assert KHOA_GIA not in in_ra, "KHOÁ NẰM TRONG CHUỖI LỖI PYTHON IN RA NHẬT KÝ"
    # `raise ... from None` KHÔNG xoá `__context__`, nó bật `__suppress_context__` — và chính cờ
    # ấy mới là thứ `traceback` đọc để quyết định có in lỗi gốc ra hay không. Canh đúng cờ ấy.
    assert e.value.__cause__ is None
    assert e.value.__suppress_context__ is True, \
        "chưa chặn in lỗi gốc — nó mang theo tiêu đề yêu cầu, tức mang theo khoá"

    assert KHOA_GIA not in json.dumps(VTC.thu_ket_noi(), ensure_ascii=False), \
        "KHOÁ NẰM TRONG KẾT QUẢ TRẢ VỀ CỦA CỬA THỬ"


def test_vt1_6_cua_thu_khong_tra_ve_dong_du_lieu_nao(co_khoa, monkeypatch):
    """Cửa thử để xem ĐƯỜNG CÓ THÔNG, không phải để xem số liệu. Trả dòng ra là mở một lối đọc
    công nợ khách mà không qua màn hình nào — tức một cửa không ai canh."""
    rieng_tu = {"bookingId": 127763, "customerName": "NGUYỄN VĂN B", "remaining": 1100000}

    class _Tra:
        def read(self):
            return json.dumps({"total": 256, "generatedAt": "2026-11-04T19:17:57",
                               "data": [rieng_tu]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(VTC.urllib.request, "urlopen", lambda *a, **k: _Tra())
    kq = VTC.thu_ket_noi()
    assert kq["thong"] is True and kq["tong_dong"] == 256
    van = json.dumps(kq, ensure_ascii=False)
    for lo in ("NGUYỄN VĂN B", "127763", "1100000"):
        assert lo not in van, f"dữ liệu khách lọt ra cửa thử: {lo}"


def test_vt1_7_khoa_khong_nam_trong_ma_nguon():
    """Khoá thật bắt đầu bằng `vtfin_`. Nó phải sống trong biến môi trường, không trong kho mã —
    kho mã có lịch sử, và một khoá đã commit thì gỡ ra cũng vẫn còn trong lịch sử."""
    import pathlib
    goc = pathlib.Path(__file__).resolve().parent.parent
    for duong in list(goc.rglob("*.py")) + list(goc.rglob("*.yml")) + list(goc.rglob("*.yaml")):
        if "/tests/" in duong.as_posix() or duong.name == pathlib.Path(__file__).name:
            continue
        noi_dung = duong.read_text(encoding="utf-8", errors="ignore")
        assert "vtfin_" not in noi_dung, f"khoá Vietrip nằm trong mã nguồn: {duong}"
    nguon = (goc / "app" / "services" / "vietrip_tai_chinh.py").read_text(encoding="utf-8")
    assert nguon.count('TEN_BIEN = "VIETRIP_FINANCE_KEY"') == 1, \
        "tên biến phải khai đúng MỘT chỗ — hai chỗ là sớm muộn lệch nhau"


def test_vt1_8_cua_thu_gan_vao_app_va_chan_dung_vai():
    from app.api.v1.cong_no_vietrip import XEM, router
    duong = [r.path for r in router.routes]
    assert "/api/v1/cong-no-vietrip/thu-ket-noi" in duong, "cửa thử chưa gắn vào router"
    assert "cntt" in XEM and "chutich" in XEM
    assert "nv_kd" not in XEM, "vai không xem được công nợ thì cũng không xem đường lấy công nợ"
