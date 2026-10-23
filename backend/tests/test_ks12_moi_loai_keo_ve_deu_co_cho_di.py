# -*- coding: utf-8 -*-
"""KS-12 — MỖI LOẠI KÉO VỀ TỪ VIETRIP ĐỀU PHẢI CÓ CHỖ ĐI, hoặc phải đứng tên nói rõ vì sao chưa.

VÌ SAO CÓ TỆP NÀY. Đo trên `origin/main` ngày 21/10/2026:

    ENTITIES            : tour booking receipt supplier_payment user vehicle proposal settlement product
    có lớp áp dụng      : tour booking receipt supplier_payment user vehicle          settlement product
    kéo về mà KHÔNG ai áp: proposal

`proposal` được kéo về đều từ `/expense-proposals/approvals/data` — 24 dòng tính tới 17/10 — và
không hàm nào đọc `VtRecord.entity == "proposal"`. Tự nó đã là một lỗ. Chỗ tệ hơn là con số đáng
lẽ phải kêu lên thì được viết để loại nó ra:

    out["remaining"] = ...where(applied == False, VtRecord.entity != "proposal", ...)

Ô «còn tồn» báo 0 trong khi 24 đề nghị chi nằm im. Không ai nhắc tới hai con số ấy trong bất kỳ
tờ canh đường nào, suốt từ lúc cửa `proposal` được mở — vì bộ đếm nói rằng không có gì để nhắc.

BA PHÉP THỬ CHÍNH, và chúng canh ba cách lỗ này mọc lại:

  ks12_1  thêm một loại vào `ENTITIES` mà quên viết lớp áp → ĐỎ, trừ khi khai lý do.
  ks12_4  ai đó lại viết một chữ `entity != "..."` thẳng vào câu truy vấn → ĐỎ. Đây là hình dạng
          CHÍNH XÁC của lỗ cũ; cấm hình dạng ấy là phần đắt nhất của cả tệp này.
  ks12_5  chạy thật: loại chưa có lớp áp phải HIỆN RA trong kết quả `apply_all` kèm số dòng, chứ
          không phải biến mất.

ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM: không đòi `proposal` phải có lớp áp dụng. Dựng lớp áp cho nó là việc
đụng vào tiền ra — `supplier_payment` đã tạo `PaymentRequest`, nếu hai loại là cùng một đề nghị ở
hai giai đoạn thì áp cả hai sẽ đếm đôi. Phép thử này chỉ đòi MỘT điều: chỗ nào chưa làm thì phải
nói ra, không được giấu trong một câu truy vấn.
"""
import os
import re
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ks12.db")
for _f in (_DB, _DB + "-journal"):
    if os.path.exists(_f):
        try: os.remove(_f)
        except OSError: pass
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

from app.main import app

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NGUON = os.path.join(GOC, "backend", "app", "services", "vietrip.py")


@pytest.fixture(scope="module", autouse=True)
def _dung_bang():
    """Mở `TestClient` một lượt để `app` dựng bảng — `test_ks12_5` chạy thật trên cơ sở dữ liệu."""
    with TestClient(app):
        yield


def _ma() -> str:
    """Nguồn đã BỎ phần chú thích — phép thử này nói về MÃ CHẠY, không nói về văn.

    Chú thích của chính vòng KS-12 có trích lại dòng hỏng cũ để người sau đọc hiểu; soát cả chú
    thích thì phép thử sẽ đỏ vì đúng cái câu kể lại lỗi, và người ta sẽ xoá lời kể chứ không xoá
    lỗi.
    """
    return "\n".join(d.split("#")[0] for d in open(NGUON, encoding="utf-8").read().splitlines())


def _entities() -> list[str]:
    from app.services.vietrip import ENTITIES
    return list(ENTITIES)


def _co_lop_ap() -> set[str]:
    return set(re.findall(r'VtRecord\.entity == "([a-z_]+)"', _ma()))


# ---------------------------------------------------------------------------------------------
def test_ks12_1_moi_loai_hoac_co_lop_ap_hoac_dung_ten_noi_ro_vi_sao():
    from app.services.vietrip import KHONG_AP_DUNG
    co_lop, khai = _co_lop_ap(), set(KHONG_AP_DUNG)
    mo_coi = [e for e in _entities() if e not in co_lop and e not in khai]
    assert not mo_coi, (
        f"KÉO VỀ MÀ KHÔNG AI ÁP, VÀ KHÔNG AI KHAI: {mo_coi}.\n"
        "Mỗi loại trong `ENTITIES` phải HOẶC có một hàm đọc `VtRecord.entity == \"<loại>\"`, "
        "HOẶC đứng tên trong `KHONG_AP_DUNG` kèm lý do. Kéo về rồi nằm im là kiểu hỏng trông y "
        "hệt lúc không có gì để làm.")


def test_ks12_2_mot_loai_khong_the_vua_co_lop_ap_vua_khai_la_chua_ap():
    from app.services.vietrip import KHONG_AP_DUNG
    ca_hai = sorted(_co_lop_ap() & set(KHONG_AP_DUNG))
    assert not ca_hai, (
        f"{ca_hai} vừa có lớp áp dụng vừa được khai là CHƯA áp. Một trong hai lời khai ấy sai, và "
        "dòng khai sai sẽ loại loại ấy khỏi bộ đếm `remaining` trong khi nó vẫn đang được áp.")


def test_ks12_3_khai_thua_thi_phai_don():
    from app.services.vietrip import KHONG_AP_DUNG
    la = sorted(set(KHONG_AP_DUNG) - set(_entities()))
    assert not la, (
        f"{la} được khai trong `KHONG_AP_DUNG` mà không còn trong `ENTITIES`. Một dòng khai cho "
        "loại không còn tồn tại là một dòng không ai đọc lại, và nó che mất lúc tên loại đổi.")


def test_ks12_4_khong_duoc_loai_tru_mot_loai_THANG_trong_cau_truy_van():
    """Đây là hình dạng CHÍNH XÁC của lỗ cũ. Cấm nó là phần đắt nhất của tệp này."""
    xau = [f"dòng {i}: {d.strip()[:100]}"
           for i, d in enumerate(_ma().splitlines(), start=1)
           if re.search(r'VtRecord\.entity\s*!=\s*["\']', d)]
    assert not xau, (
        "LOẠI TRỪ MỘT LOẠI THẲNG TRONG CÂU TRUY VẤN:\n" + "\n".join("  · " + x for x in xau)
        + "\n\nChỗ loại trừ duy nhất là `KHONG_AP_DUNG`, vì ở đó nó mang theo LÝ DO và bị `apply_all` "
          "kê ra. Một chữ `!= \"...\"` giấu trong truy vấn thì không ai đọc được, và đúng một chữ "
          "như thế đã giấu 24 đề nghị chi suốt nhiều tuần.")


def test_ks12_5_apply_all_phai_KE_RA_loai_chua_co_lop_ap_kem_so_dong():
    """Chạy thật trên cơ sở dữ liệu thử: loại chưa có lớp áp phải HIỆN RA, không được biến mất."""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.services import vietrip as VT
    from app.models.vietrip import VtRecord

    db = SessionLocal()
    try:
        loai = next(iter(VT.KHONG_AP_DUNG))
        truoc = db.execute(select(VtRecord).where(VtRecord.entity == loai,
                                                  VtRecord.applied == False)).scalars().all()
        them = 2 - len(truoc)
        for i in range(max(0, them)):
            db.add(VtRecord(entity=loai, vietrip_id=900000 + i, raw={"thu": i}, applied=False))
        db.commit()
        n_mong = db.execute(select(VtRecord).where(VtRecord.entity == loai,
                                                   VtRecord.applied == False)).scalars().all()
        kq = VT.apply_all(db, "ks12_thu", limit=5)
    finally:
        db.close()

    assert "chua_co_lop_ap_dung" in kq, (
        "`apply_all` không kê phần «chưa có lớp áp dụng». Thiếu nó thì loại ấy nằm ngoài "
        "`remaining` mà không chỗ nào nói ra — đúng cái lỗ KS-12 sinh ra để bịt.")
    muc = kq["chua_co_lop_ap_dung"].get(loai)
    assert muc, f"Loại {loai} không có trong bản kê."
    assert muc["so_dong"] == len(n_mong), (
        f"Số dòng kê sai: kê {muc['so_dong']}, thật {len(n_mong)}.")
    assert muc.get("ly_do") and len(muc["ly_do"]) >= 30, (
        f"Loại {loai} khai mà không có lý do đọc được. Một dòng khai không lý do thì lần sau "
        "không ai biết nên dựng lớp áp hay nên bỏ loại ấy đi.")


def test_ks12_6_moi_ly_do_deu_phai_doc_duoc():
    from app.services.vietrip import KHONG_AP_DUNG
    cut = {e: ly for e, ly in KHONG_AP_DUNG.items() if not ly or len(ly.strip()) < 30}
    assert not cut, (
        f"Lý do quá ngắn, không đọc được: {sorted(cut)}. Lý do là thứ người sau dùng để quyết "
        "dựng lớp áp hay bỏ loại ấy — viết cho người đọc, không viết cho đủ chỗ.")
