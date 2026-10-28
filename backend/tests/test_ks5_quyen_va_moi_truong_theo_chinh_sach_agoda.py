# -*- coding: utf-8 -*-
"""KS-5 · Chính sách Agoda Fulfill Assisted — quyền, môi trường, và cấm chạm số thẻ.

Agoda (trang getting-started, đọc 28/10/2026) định nghĩa Fulfill Assisted bằng đúng một câu:
«Agoda will directly charge your customers». Vietourist KHÔNG thu tiền khách, nên KHÔNG BAO GIỜ
chạm vào số thẻ — và đó phải là một hàng rào, không phải một lời hứa trong tài liệu.

Bộ đề xuất v1.4 cảnh báo chỗ thứ hai: «Không mặc định được thu thẻ, hủy qua API, sử dụng ảnh,
hoặc nhận dữ liệu đơn chỉ vì đã có tài khoản Affiliate.» Quyền là thứ NGUỒN CẤP.

Bốn phép dưới đây không đụng cơ sở dữ liệu: ba phép đầu thay `kho` bằng một dòng OTA giả, phép
cuối soi NGUỒN. Lý do giống KS-4 — bộ kiểm chạy trên SQLite, soi hành vi CSDL ở đó là soi nhầm.
"""
import re
from pathlib import Path

import pytest

from app.models.khach_san_ota import QUYEN_OTA, MOI_TRUONG_OTA
from app.services import khach_san_ota as S

GOC_APP = Path(S.__file__).resolve().parents[1]


class _Ota:
    """Dòng OTA giả — đúng những cột mà `thieu_de_bat` và `sua` đọc tới."""

    def __init__(self, **kw):
        self.id, self.ma, self.ten = 1, "expedia", "Expedia"
        self.san_pham, self.loai_link = "khach_san", "hoa_hong"
        self.trang_thai = "da_duyet"
        self.link = "https://www.expedia.com/affiliate/abc"
        self.ten_mien, self.duong_dan = "www.expedia.com", "/affiliate"
        self.da_kiem_link, self.duoc_dung_web, self.bat = True, True, True
        self.quyen, self.moi_truong = "AFFILIATE", "that"
        self.phien_ban, self.phap_nhan_id = 2, 1
        self.subid_cho_phep, self.subid_tham_so = False, ""
        self.bang_chung, self.ghi_chu = "Thư duyệt 27/10/2026", ""
        self.sua_boi, self.sua_luc = "", None
        for k, v in kw.items():
            setattr(self, k, v)


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


def test_ks5_1_chua_ghi_nhan_quyen_affiliate_thi_khong_bat_duoc():
    """Chuyển khách qua link hoa hồng LÀ dùng quyền Affiliate. Chưa ghi nhận nguồn cấp thì chưa bật."""
    o = _Ota(quyen="")
    assert "chưa ghi nhận nguồn cấp quyền AFFILIATE" in S.thieu_de_bat(o)
    assert S.dang_mo(o) is False

    o2 = _Ota(quyen="AFFILIATE")
    assert S.thieu_de_bat(o2) == [], S.thieu_de_bat(o2)
    assert S.dang_mo(o2) is True

    # Có SEARCH mà không có AFFILIATE thì vẫn không bật được — quyền không thay nhau.
    o3 = _Ota(quyen="SEARCH,BOOK")
    assert "chưa ghi nhận nguồn cấp quyền AFFILIATE" in S.thieu_de_bat(o3)


def test_ks5_2_moi_truong_tat_thi_khong_bat_duoc():
    """Chưa certification thì môi trường còn Tắt, và Tắt nghĩa là máy chủ chặn, không chỉ ẩn nút."""
    o = _Ota(moi_truong="tat")
    assert "môi trường đang Tắt" in S.thieu_de_bat(o)
    assert S.dang_mo(o) is False
    assert set(MOI_TRUONG_OTA) == {"tat", "thu", "that"}


def test_ks5_3_khong_nhan_quyen_la_va_khong_mo_chay_that_khi_thieu_bang_chung(dung, monkeypatch):
    """Gõ sai một chữ mà im lặng bỏ qua thì màn nói đã cấp còn máy chủ nghĩ chưa — hỏng mà vẫn xanh."""
    with pytest.raises(S.LoiOta):
        S.sua(_Db(), _U(), 1, {"quyen": "AFFILIATE,SEARCHH"})

    o = S.sua(_Db(), _U(), 1, {"quyen": "book, affiliate"})
    assert o.quyen == "AFFILIATE,BOOK", "Lưu theo thứ tự danh mục, không theo thứ tự người gõ"
    assert S.ds_quyen(o) == ["AFFILIATE", "BOOK"]
    assert S.co_quyen(o, "book") is True and S.co_quyen(o, "CANCEL") is False

    with pytest.raises(S.LoiOta):
        S.sua(_Db(), _U(), 1, {"moi_truong": "khong_co_cai_nay"})

    # Mở «Chạy thật» mà chưa có bằng chứng thì phải chặn: không có cách nào soát lại về sau.
    trong = _Ota(bang_chung="")
    monkeypatch.setattr(S, "_lay", lambda db, i: trong)
    with pytest.raises(S.LoiOta):
        S.sua(_Db(), _U(), 1, {"moi_truong": "that"})
    o2 = S.sua(_Db(), _U(), 1, {"moi_truong": "that", "bang_chung": "Certification Agoda 29/10/2026"})
    assert o2.moi_truong == "that"


def test_ks5_4_khong_mot_cho_nao_trong_phan_khach_san_cham_vao_so_the():
    """Fulfill Assisted: «Agoda will directly charge your customers».

    Vietourist không thu tiền khách, nên trong phần khách sạn không được có một ô, một cột hay
    một trường nào nhận số thẻ. Đây là hàng rào, không phải lời hứa trong tài liệu: ngày có người
    viết thêm đường đặt phòng, phép thử này đỏ trước khi mã kịp lên hệ thật.
    """
    cam = re.compile(
        r"\b(card_number|cardnumber|credit_card|creditcard|the_tin_dung|so_the|"
        r"\bcvv\b|\bcvc\b|\bpan\b|expiry_month|expiry_year|card_holder)\b", re.I)
    tep = [
        GOC_APP / "models" / "khach_san_ota.py",
        GOC_APP / "services" / "khach_san_ota.py",
        GOC_APP / "api" / "v1" / "khach_san_ota.py",
        GOC_APP / "services" / "doi_soat_ota.py",
        GOC_APP / "api" / "v1" / "doi_soat_ota.py",
    ]
    dinh = []
    for p in tep:
        if not p.is_file():
            continue
        for i, d in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if cam.search(d) and "KS-5" not in d:
                dinh.append(f"{p.name}:{i}: {d.strip()[:110]}")
    assert not dinh, (
        "Phần khách sạn có chỗ nhận số thẻ:\n    " + "\n    ".join(dinh)
        + "\n\nMô hình đã chọn là Agoda Fulfill Assisted: AGODA thu tiền khách, Vietourist không "
          "bao giờ chạm vào số thẻ. Muốn tự thu thì đó là mô hình Partner Fulfillment — một quyết "
          "định của Chủ tịch, kéo theo nghĩa vụ bảo mật thẻ, chứ không phải một ô thêm vào form."
    )
    assert set(QUYEN_OTA) >= {"AFFILIATE", "SEARCH", "BOOK", "CANCEL"}
