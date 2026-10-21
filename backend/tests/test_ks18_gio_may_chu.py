# -*- coding: utf-8 -*-
"""ĐỢT KS-18 — máy chủ phải chạy ĐÚNG múi giờ đã khai, và phải có cửa để tự xem.

ĐO ĐƯỢC 21/10/2026, tái hiện trên một máy, chỉ khác chỗ có hay không có `/usr/share/zoneinfo`:

    có  tzdata : datetime.now() = 2026-10-22 00:23   ·  time.tzname = ('+07', '+07')
    KHÔNG      : datetime.now() = 2026-10-21 17:23   ·  time.tzname = ('Asia', 'Asia')

`render.yaml` khai `TZ: Asia/Ho_Chi_Minh` từ lâu, nhưng ảnh nền là `python:3.12-slim` và ảnh
`slim` của Debian KHÔNG mang gói `tzdata`. Thiếu tệp múi giờ thì thư viện C không báo lỗi: nó cắt
chuỗi ở dấu gạch chéo, coi `Asia` là tên múi, lệch 0 — tức UTC. Một biến môi trường được KHAI
không có nghĩa là nó có HIỆU LỰC.

Hậu quả: mỗi ngày từ 00h tới 07h giờ Việt Nam, mọi chữ "hôm nay" trong VTOS lùi lại một ngày.

ĐỪNG sửa phép thử cho hết đỏ. Đỏ ở đây nghĩa là hệ thật lại đang lệch ngày vào ban đêm.
"""
import datetime
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import gio_may_chu as GMC  # noqa: E402

GOC = pathlib.Path(__file__).resolve().parents[2]
DOCKERFILE = GOC / "backend/Dockerfile"
RENDER = GOC / "render.yaml"


# ── 1. hạ tầng: khai TZ thì ảnh PHẢI có tzdata ──────────────────────────────────────────────
def test_ks18_1_khai_TZ_thi_anh_may_chu_phai_cai_tzdata():
    r = RENDER.read_text(encoding="utf-8")
    if not re.search(r"key:\s*TZ", r):
        return                                   # không khai TZ thì không đòi gì
    d = DOCKERFILE.read_text(encoding="utf-8")
    cai = [l for l in d.splitlines() if l.strip().startswith("RUN apt-get")]
    assert cai, "Dockerfile không cài gói hệ thống nào — không thể có tzdata"
    assert any("tzdata" in l for l in cai), (
        "render.yaml khai TZ nhưng ảnh máy chủ KHÔNG cài `tzdata`. Thiếu nó thì TZ bị đọc thành "
        "lệch 0 giờ mà không báo lỗi, và máy chủ lặng lẽ chạy theo UTC.")


def test_ks18_2_anh_nen_van_la_loai_slim_nen_dung_bo_tzdata_di():
    """Nếu ai đó đổi sang ảnh đầy đủ thì phép thử trên thành thừa — nhưng giữ tzdata vẫn đúng."""
    d = DOCKERFILE.read_text(encoding="utf-8")
    assert d.lstrip().startswith("FROM python:"), "đổi ảnh nền thì đọc lại Đợt KS-18"


# ── 2. phép đo: đọc từ đồng hồ máy, không suy từ tên ────────────────────────────────────────
def test_ks18_3_do_lech_bang_chinh_dong_ho_may():
    lech = GMC.lech_phut_hien_tai()
    that = round((datetime.datetime.now() - datetime.datetime.utcnow()).total_seconds() / 60)
    assert abs(lech - that) <= 1


def test_ks18_4_dung_gio_thi_khong_keu():
    ra = GMC.soat("Asia/Ho_Chi_Minh", lech_mong_doi=GMC.lech_phut_hien_tai())
    assert ra["dung_gio"] is True
    assert ra["vi_sao"] == "" and ra["anh_huong"] == ""


def test_ks18_5_lech_thi_noi_ro_lech_bao_nhieu():
    ra = GMC.soat("Asia/Ho_Chi_Minh", lech_mong_doi=GMC.lech_phut_hien_tai() + 60)
    assert ra["dung_gio"] is False
    assert ra["vi_sao"] and "phút" in ra["vi_sao"]
    assert "hôm nay" in ra["anh_huong"]


def test_ks18_6_nhan_ra_dau_vet_THIEU_TZDATA_chu_khong_chi_noi_lech():
    """Khi thư viện C đọc nhầm, `time.tzname` mang đoạn đầu của chuỗi TZ (`Asia`, `America`…).

    Phân biệt được hai cảnh — lệch vì CHƯA CÀI tzdata, và lệch vì khai sai múi — mới chỉ đúng
    được việc cần làm. Bản đầu chỉ nói "lệch N phút", đọc xong vẫn không biết sửa ở đâu.
    """
    import time as _t
    cu = _t.tzname
    try:
        _t.tzname = ("Asia", "Asia")
        ra = GMC.soat("Asia/Ho_Chi_Minh", lech_mong_doi=GMC.lech_phut_hien_tai() + 60)
        assert "tzdata" in ra["vi_sao"], ra["vi_sao"]
    finally:
        _t.tzname = cu


def test_ks18_7_cua_chi_doc_khong_cham_co_so_du_lieu():
    import inspect
    ma = inspect.getsource(GMC)
    for cam in ("Session", "db.", "select("):
        assert cam not in ma, f"phép đo giờ máy chủ không được chạm cơ sở dữ liệu ({cam})"


def test_ks18_8_health_KHONG_bi_lam_nang_them():
    """Cửa `/health` Render gọi 5 giây một lần và đã từng làm sập máy chủ — đừng cắm gì vào đó."""
    ma = (GOC / "backend/app/api/v1/routes.py").read_text(encoding="utf-8")
    than = ma.split('@router.get("/health"', 1)[1].split("@router.", 1)[0]
    assert "gio_may_chu" not in than and "GMC" not in than
