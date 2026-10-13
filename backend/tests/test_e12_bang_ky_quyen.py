# -*- coding: utf-8 -*-
"""Đợt E12 (13/10/2026) — BẢNG KÝ QUYỀN: một dòng ký mở ra bao nhiêu cửa.

VÌ SAO CÓ TỆP NÀY

Ngày 11/10/2026 Chủ tịch ký một dòng — `VAI_KE_THUA = {"ketoan_truong": "ketoan"}` — và một dòng
ấy mở THÊM hàng trăm cửa. Con số ấy không nằm trong dòng ký; nó là HỆ QUẢ, phải đo mới biết. Hôm
ký thì đo tay rồi báo miệng, và sau đó không chỗ nào trong hệ thống còn nói ra nó.

Tệp này canh ba điều, và điều thứ hai là điều quan trọng nhất:

 1. Phép đếm ĐỌC TỪ CHỮ KÝ HÀM, không phân tích mã nguồn.
 2. KHÔNG CON SỐ NÀO ĐƯỢC CHÉP CỨNG. Chép thì nó đóng băng ở ngày đo, còn cửa thì mỗi đợt lại
    thêm — và một con số cũ trông y hệt một con số đúng. Phép thử dưới đây DỰNG THÊM một cửa rồi
    đòi con số phải nhúc nhích theo.
 3. Dòng trên bàn làm việc mang theo chi tiết, và nó KHÔNG đòi ai bấm duyệt gì cả.
"""
import os
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e12.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                              # noqa: E402

from app.services import bang_ky_cua as BKC                 # noqa: E402
from app.services import vai_ke_thua as VKT                 # noqa: E402


def test_e12_1_doc_tu_chu_ky_ham_chu_khong_phan_tich_ma():
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "services", "bang_ky_cua.py")
    ma = open(p, encoding="utf-8").read()
    assert "vai_tro_yeu_cau" in ma
    assert "ast" not in ma.split('"""', 2)[-1], "đang phân tích cây cú pháp thay vì đọc chữ ký hàm"


def test_e12_2_dem_ra_so_that_va_tach_duoc_cua_mo_cho_moi_nguoi():
    d = BKC.dem_cua("ketoan_truong")
    assert d["dich_danh"] > 100, "Kế toán trưởng phải mở được hàng trăm cửa sau dòng ký 11/10"
    assert d["mo_het"] >= 1, "phải có ít nhất một cửa không khai vai (mọi người đã đăng nhập)"
    assert d["tong"] == d["dich_danh"] + d["mo_het"]


def test_e12_3_KHONG_CON_SO_NAO_CHEP_CUNG():
    """Phép thử quan trọng nhất của tệp: dựng THÊM một cửa rồi đòi con số nhúc nhích theo.

    Một bảng chép lại con số đã đo thì phép thử này xanh ở ngày viết và sai lặng lẽ mọi ngày sau.
    """
    from fastapi import APIRouter, Depends

    from app.api.deps import require_roles
    from app.main import app

    truoc = BKC.dem_cua("ketoan_truong")["dich_danh"]
    r = APIRouter(prefix="/api/v1", tags=["thu-e12"])

    @r.get("/e12-cua-thu-nghiem")
    def _thu(u=Depends(require_roles("ketoan"))):
        return {}

    app.include_router(r)
    try:
        sau = BKC.dem_cua("ketoan_truong")["dich_danh"]
        # +1 vì `require_roles("ketoan")` tự nới sang `ketoan_truong` qua VAI_KE_THUA — nên phép
        # đếm phải thấy cửa mới NGAY, không cần ai khai thêm gì.
        assert sau == truoc + 1, f"thêm một cửa mà con số không đổi ({truoc} → {sau}) — đang chép cứng"
    finally:
        app.router.routes = [x for x in app.router.routes
                             if getattr(x, "path", "") != "/api/v1/e12-cua-thu-nghiem"]
    assert BKC.dem_cua("ketoan_truong")["dich_danh"] == truoc


def test_e12_4_moi_quyet_dinh_deu_co_nguoi_ky_va_can_cu():
    """Không dòng nào được thiếu người ký — cùng bất biến với `cap_tach_nhiem` của Đợt E2a."""
    thieu = [q["ma"] for q in BKC.QUYET_DINH
             if not q.get("nguoi_ky") or not q.get("can_cu") or not q.get("ngay_ky")
             or not q.get("dao_lai")]
    assert not thieu, f"Quyết định nới quyền thiếu người ký / căn cứ / ngày / cách đảo lại: {thieu}"


def test_e12_5_dem_duoc_so_cua_vai_con_thay_VI_vai_cha_thay():
    """Con số đáng giá nhất của bảng — không phải tổng, mà là phần mất đi nếu xoá dòng kế thừa.

    BẢN ĐẦU CỦA PHÉP ĐẾM TRẢ VỀ 0, và phép thử này bắt được. Lý do: `require_roles` gọi
    `VKT.mo_rong` NGAY LÚC KHAI rồi mới ghi `vai_tro_yeu_cau`, nên tới lúc đọc thì vai con đã nằm
    sẵn trong mọi cửa của vai cha — phép suy chạy trước, phép đo chạy sau. Giữ phép thử này ở
    đúng hình ấy để lần sau ai sửa cách đếm mà quên điều đó thì đỏ ngay.
    """
    d = BKC.bang_ky()[0]
    assert d["cua_nho_ke_thua"] > 100, "phép đếm trả về số nhỏ bất thường — xem lại thứ tự nới/đo"
    assert d["cua_nho_ke_thua"] <= d["cua_dich_danh"]
    assert d["ten_vai"] == "Kế toán trưởng"


def test_e12_6_dao_lai_duoc_bang_dung_mot_dong():
    """Câu "đảo lại bằng một dòng" phải ĐÚNG, không phải một lời hứa trong chú thích."""
    assert VKT.VAI_KE_THUA.get("ketoan_truong") == "ketoan"
    assert len(VKT.VAI_KE_THUA) == 1, "có dòng kế thừa thứ hai mà bảng ký chưa khai"


def test_e12_7_mui_cua_luong_khai_du_va_dem_duoc():
    d = BKC.bang_ky()[0]
    assert len(d["cua_luong_da_ky"]) == len(VKT.CUA_LUONG_DA_KY)
    assert all(c["duong_dan"].startswith("/api/v1/") for c in d["cua_luong_da_ky"])
    assert d["can_cu_cua_luong"]


def test_e12_8_dong_ban_lam_viec_mang_chi_tiet_va_KHONG_doi_ai_bam():
    ds = BKC.dong_ban_lam_viec()
    assert len(ds) == 1
    d = ds[0]
    assert d["chi_tiet"], "dòng không mang chi tiết thì bấm vào không xổ ra gì"
    assert d["href"] == "", "dòng này không dẫn đi đâu — nó xổ ra tại chỗ"
    assert "cửa" in d["label"]
    # KHÔNG dùng chữ "chờ" / "duyệt": đây không phải việc chờ ai bấm, và gọi nó là việc chờ duyệt
    # thì hàng việc thật của Chủ tịch dài thêm một dòng mãi mãi không bao giờ vơi.
    for cam in ("chờ", "duyệt"):
        assert cam not in d["label"].lower(), f"nhãn gọi đây là một việc chờ bấm: {d['label']}"
