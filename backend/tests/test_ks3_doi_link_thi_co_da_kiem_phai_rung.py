# -*- coding: utf-8 -*-
"""KS-3 · Đổi link OTA thì cờ «đã kiểm» phải rụng.

Sinh ra từ một chỗ đo được 29/10/2026 trên mã đang chạy. `sua()` xoá `da_kiem_link` khi link
đổi, nhưng vòng lặp ngay sau đó ghi đè lại bằng dữ liệu của chính lượt gửi lên — mà màn Sửa thì
gửi cả năm ô (`link`, `ten_mien`, `duong_dan`, `da_kiem_link`, `duoc_dung_web`) trong MỘT lượt.
Kết quả: dấu ✓ ĐÃ KIỂM của link cũ ở lại trên link mới.

KHÔNG ĐỤNG CƠ SỞ DỮ LIỆU: `sua()` chỉ cần một dòng OTA, một phiên để chốt, và một đường ghi
nhật ký. Thay cả ba bằng vật giả là soi được đúng phần cần soi, không cần `conftest`, và chạy
trong một phần nghìn giây.
"""
import pytest

from app.services import khach_san_ota as S


class _Ota:
    """Một dòng OTA giả — đúng những cột mà `sua()` và `_snap()` đọc tới."""

    def __init__(self):
        self.id, self.ma, self.ten = 1, "expedia", "Expedia"
        self.san_pham, self.loai_link = "khach_san", "hoa_hong"
        self.trang_thai = "da_duyet"
        self.link = "https://www.expedia.com/affiliate/cu"
        self.ten_mien, self.duong_dan = "www.expedia.com", "/affiliate"
        self.da_kiem_link, self.duoc_dung_web, self.bat = True, True, True
        self.quyen, self.moi_truong = "AFFILIATE", "that"   # KS-5 thêm hai cột
        self.phien_ban, self.phap_nhan_id = 2, 1
        self.subid_cho_phep, self.subid_tham_so = False, ""
        self.bang_chung, self.ghi_chu = "", ""
        self.sua_boi, self.sua_luc = "", None


class _Db:
    def get(self, *a, **k):
        return object()

    def commit(self):
        pass

    def refresh(self, o):
        pass


class _U:
    username, role = "chutich", "chutich"


@pytest.fixture
def dung(monkeypatch):
    o = _Ota()
    monkeypatch.setattr(S, "_lay", lambda db, i: o)
    monkeypatch.setattr(S, "sua_duoc", lambda u: True)
    monkeypatch.setattr(S.R, "audit", lambda *a, **k: None)
    return o


def test_ks3_1_doi_link_thi_co_da_kiem_phai_rung_du_cung_luot_gui_len_true(dung, monkeypatch):
    """Đây đúng là lượt mà màn Sửa gửi: link mới VÀ da_kiem_link=True trong cùng một lần bấm Lưu."""
    o = S.sua(_Db(), _U(), 1, {
        "link": "https://www.expedia.com/affiliate/moi",
        "ten_mien": "www.expedia.com",
        "duong_dan": "/affiliate",
        "da_kiem_link": True,
        "duoc_dung_web": True,
    })
    assert o.link.endswith("/moi")
    assert o.da_kiem_link is False, (
        "Đổi link xong mà dấu «đã kiểm» của link CŨ vẫn ở lại trên link MỚI. Hàng rào bốn điều "
        "kiện còn ba, và nó vẫn xanh nên không ai biết.")
    assert o.bat is False, "Link mới chưa kiểm thì OTA phải tự tắt"
    assert o.phien_ban == 3, "Link mới là phiên bản mới — lượt cũ không được phát lại link cũ"


def test_ks3_2_chi_doi_ten_mien_cung_phai_kiem_lai(dung):
    """Không chỉ ô `link`. Đổi tên miền hay đường dẫn cho phép cũng là đổi đích đến."""
    o = S.sua(_Db(), _U(), 1, {
        "ten_mien": "www.expedia.com, expedia.com",
        "da_kiem_link": True,
    })
    assert o.da_kiem_link is False
    assert o.bat is False


def test_ks3_3_khong_doi_link_thi_tich_da_kiem_van_an(dung):
    """Phép vá không được làm hỏng nhịp bình thường: lưu lần hai chỉ để tích Đã kiểm."""
    o = S.sua(_Db(), _U(), 1, {"da_kiem_link": True, "duoc_dung_web": True})
    assert o.da_kiem_link is True, (
        "Không đụng tới link thì dấu đã kiểm phải tích được — nếu không thì không bao giờ bật "
        "được một OTA nào nữa.")
    assert o.phien_ban == 2, "Không đổi link thì không lên phiên bản"


def test_ks3_4_bo_tich_da_kiem_van_bo_duoc(dung):
    """Chiều ngược lại cũng phải còn: Chủ tịch gỡ dấu đã kiểm khi thấy link hỏng."""
    o = S.sua(_Db(), _U(), 1, {"da_kiem_link": False})
    assert o.da_kiem_link is False
    assert o.bat is False, "Mất một điều kiện thì tự tắt"
