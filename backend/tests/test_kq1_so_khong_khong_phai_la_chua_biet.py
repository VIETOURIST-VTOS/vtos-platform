# -*- coding: utf-8 -*-
"""“(0 DOANH THU)” TRÊN MÀN HÌNH CHỦ TỊCH NÓI NGƯỢC SỰ THẬT.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

Đo trên hệ thật ngày 06/10/2026, trang chủ của Chủ tịch in nguyên văn:

    Còn 19 chuyến đã đóng số mà chưa có giá vốn (0 doanh thu) — chưa vào hai con số trên…

Người đọc hiểu: mười chín chuyến ấy không đáng bao nhiêu, bỏ qua được. Sự thật ngược lại. Chính
chú thích của `ket_qua_that.dt_thieu_gia_von` đã ghi rằng doanh thu của những chuyến ấy "vẫn có thể
rỗng nốt", nên số 0 ở đây là PHẦN ĐÃ BIẾT bằng không — tức là **chưa biết gì cả**, không phải biết
rằng bằng không. Mười chín chuyến đã chạy xong, đã đóng số, và hệ thống không biết chúng thu về
bao nhiêu.

Máy chủ KHÔNG sai: nó cộng đúng phần đã biết, và nó đã nói ra điều đó trong chú thích. Chỗ sai là
màn hình in một con số tiền ở nơi đáng lẽ phải nói "chưa biết".

Và đây đúng là luật kho mã này nhắc đi nhắc lại ở chỗ khác:
  · `KsDiem.diem` để RỖNG chứ không chấm 0 — "chưa đủ cơ sở" khác "làm kém";
  · `ks_nap_lo.bon_so_tien` trả None chứ không trả 0 — "không đo được" khác "đo được và bằng 0";
  · `chua_phan_bo` rỗng khác 0 — "chưa từng phân bổ" khác "đã phân bổ hết".
Ô duy nhất chưa theo luật ấy lại là ô nằm trên màn hình Chủ tịch.

Tệp này giữ HAI nửa, vì mỗi nửa một mình đều không đủ:
  1. trạng thái ấy CÓ THẬT và máy chủ sinh ra được — nếu không thì luật trên màn hình là thừa;
  2. màn hình phân biệt được hai trường hợp, thay vì in thẳng con số.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import datetime as dt                                           # noqa: E402
import io                                                       # noqa: E402

from sqlalchemy import create_engine                            # noqa: E402
from sqlalchemy.orm import sessionmaker                         # noqa: E402

from app.db.session import Base                                 # noqa: E402
from app.models.core import Company, Tour, User                 # noqa: E402
from app.services import ket_qua_that as KQ                     # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN_HINH = os.path.join(GOC, "web", "components", "KhoiKetQuaKinhDoanh.tsx")


def _khoi_jsx(ma: str) -> str:
    """Khối JSX vẽ dòng “chuyến thiếu giá vốn”, cắt ra khỏi chú thích quanh nó."""
    i = ma.index("{thieu_gv > 0 && (")
    return ma[i:ma.index("{/*", i) if "{/*" in ma[i:i + 2000] else i + 1600]


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _dung(db, so_chuyen: int, doanh_thu):
    """Chuyến ĐÃ ĐÓNG SỐ mà giá vốn còn rỗng. `doanh_thu=None` = chưa ghi doanh thu nốt."""
    c = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True); db.add(c)
    u = User(username="dh", full_name="DH", role="nv_dh", password_hash="x"); db.add(u); db.commit()
    for i in range(so_chuyen):
        db.add(Tour(code=f"T{i}", name=f"C{i}", company_id=c.id, tour_type="le_noi_dia",
                    start_date=dt.date(2026, 9, 2), end_date=dt.date(2026, 9, 5), operator_id=u.id,
                    status="da_dong_so", closed_at=dt.datetime(2026, 9, 10, 9, 0),
                    actual_revenue=doanh_thu, actual_cost=None))
    db.commit()


# ============================== 1. TRẠNG THÁI ẤY CÓ THẬT ==============================
def test_kq1_chuyen_thieu_gia_von_ma_cung_chua_co_doanh_thu():
    """Số chuyến > 0 mà tiền = 0. Đây chính là cảnh trên hệ thật, dựng lại bằng khuôn thật."""
    db = _db(); _dung(db, 19, None)
    r = KQ.thang(db, "2026-09")
    assert r["thieu_gia_von"] == 19
    assert r["dt_thieu_gia_von"] == 0, (
        "Nếu con số này không còn bằng 0 thì cảnh đang nói tới đã khác, và câu chữ trên màn hình "
        "phải được đọc lại chứ không giữ nguyên.")


def test_kq1_co_doanh_thu_that_thi_con_so_khac_khong():
    """Nửa đối chứng: có doanh thu thật thì vẫn phải ra số, không bị câu chữ mới nuốt mất."""
    db = _db(); _dung(db, 3, 1_000_000)
    r = KQ.thang(db, "2026-09")
    assert r["thieu_gia_von"] == 3 and r["dt_thieu_gia_von"] == 3_000_000


# ============================== 2. MÀN HÌNH PHẢI PHÂN BIỆT ==============================
def test_kq1_man_hinh_khong_in_thang_con_so_tien():
    """PHÉP THỬ BẮT ĐÚNG LỖI GỐC — và nó phải đọc chính tệp màn hình, vì lỗi nằm ở đó.

    Máy chủ không sai một dòng nào; không có phép thử nào ở tầng Python bắt được câu chữ này.
    """
    assert os.path.exists(MAN_HINH), f"Không thấy {MAN_HINH}"
    ma = io.open(MAN_HINH, encoding="utf-8").read()
    # Neo vào ĐÚNG khối JSX, không neo vào chữ trong chú thích: chú thích nói về cùng chuyện nên
    # một phép tìm theo câu chữ sẽ bắt nhầm nó và phép thử xanh mà chẳng soi dòng mã nào.
    khuc = _khoi_jsx(ma)
    assert "tien_thieu_gia_von" in khuc, "Mất hẳn con số thì cũng là mất thông tin"
    assert "> 0" in khuc, (
        "Màn hình đang in thẳng số tiền của chuyến thiếu giá vốn. Số 0 ở đây nghĩa là CHƯA BIẾT, "
        "không phải không đồng nào — phải rẽ nhánh theo nó.")
    assert "chưa biết doanh thu" in khuc, (
        "Phải nói thành lời “chưa biết”, đừng chỉ giấu con số đi: giấu thì người đọc tưởng mọi "
        "chuyến đều đã có doanh thu.")


def test_kq1_khong_quay_lai_in_dong_khong_dong():
    """Chặn đúng cách sửa sai mà người sau dễ chọn: để `0 đ` cho gọn."""
    khuc = _khoi_jsx(io.open(MAN_HINH, encoding="utf-8").read())
    assert 'gonSo(Number(th.tien_thieu_gia_von || 0), "tien")' not in khuc, (
        "Dòng cũ quay lại: `|| 0` biến “chưa biết” thành “không đồng nào” ngay tại chỗ in.")
