# -*- coding: utf-8 -*-
"""QT-1 · Khối quyết toán lồng trên màn Chủ tịch (Chủ tịch duyệt bản xem thử 23/10/2026).

VÌ SAO CÓ VÒNG NÀY. Chủ tịch nhìn màn hình và hỏi: «hai ô Quá hạn quyết toán và Chờ quyết toán
có gì khác nhau? nếu trùng thì ẩn bớt một». Đo ra: KHÔNG trùng, nhưng ô Quá hạn là MỘT LÁT nằm
trọn trong nhóm A của ô kia — 681 ⊂ 709 ⊂ 1.742 hôm đo. Hai ô đứng cách nhau một hàng và không
chỗ nào nói cái nhỏ nằm trong cái lớn, nên đọc lướt thành hai cách đếm một việc. Nếu lúc ấy ẩn ô
Chờ quyết toán như ý đầu tiên thì mất tầm nhìn 1.061 tour, trong đó 1.033 tour đang nằm ở Kế toán
và KHÔNG ô nào khác trên màn ấy đếm.

Bộ này canh phần máy chủ của bản gộp: `cho_quyet_toan` phải trả đủ ba con số con để màn hình vẽ
được khối lồng mà KHÔNG phải tự trừ. Màn hình tự trừ là chỗ hỏng kinh điển: hai nơi cùng tính một
phép, rồi một nơi đổi.

  qt1_1  ba nhóm con cộng đúng bằng A — bất biến của cả khối
  qt1_2  tour quá hạn vào đúng nhóm quá hạn
  qt1_3  tour CÒN trong hạn không vào nhóm quá hạn
  qt1_4  đúng ngày hạn thì CHƯA quá hạn (mép, giữ cùng luật với DL06 của TQ-1)
  qt1_5  tour `da_dong_so` nằm ở B, không vào A và không vào quá hạn
  qt1_6  tổng = A + B, và «đã về chưa đóng sổ» KHÔNG cộng vào tổng
  qt1_7  ràng buộc NOT NULL của `tours.end_date` — thứ làm nhóm «chưa có ngày về» luôn bằng 0
  qt1_8  truyền sẵn `qua_han` cho kết quả y hệt lúc để nó tự đếm
  qt1_9  khoá trả về đủ cho màn hình — thiếu một khoá là khối lồng vỡ

CHUYẾN THIẾU NGÀY VỀ — MỘT PHÉP ĐO SỬA LẠI LỜI EM ĐÃ NÓI. Báo đầu tiên em nói với Chủ tịch
rằng 28 tour chênh giữa 709 và 681 có thể lẫn chuyến «thiếu ngày về» — nhóm sẽ không bao giờ
hiện ở ô quá hạn. Đo lại: KHÔNG CÓ nhóm ấy, và không thể có. `tours.end_date` là NOT NULL ở mô
hình, ở bản nâng cấp gốc, và không bản nâng cấp nào đổi. Em thử chèn thẳng bằng SQL thô để dựng
ca ấy và chính SQLite chặn: `IntegrityError: NOT NULL constraint failed: tours.end_date`. Vậy
28 tour ấy là đủ 28 tour «còn trong hạn».

VẪN GIỮ khoá `chua_co_ngay_ve` và vẫn ĐẾM THẬT (một câu COUNT, hôm nay luôn trả 0), vì điều kiện
quá hạn đòi `end_date` khác rỗng. Ngày nào ràng buộc ấy được nới, lấy hiệu `A - quá hạn` sẽ
lặng lẽ gọi những chuyến đó là «còn trong hạn» — một câu sai không ai thấy. Đếm riêng thì hôm
nay bằng 0 (màn hình ẩn dòng ấy) và ngày khác 0 thì nó tự hiện ra có tên. `qt1_7` canh chính ràng
buộc đó: nó đỏ ngày ai đó nới cột, và đó đúng lúc màn hình phải hiện dòng thứ ba.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
import app.models  # noqa: F401
from app.models.core import Tour, User
from app.services import tong_quan_tour as TQT

HOM_NAY = date(2026, 10, 23)


@pytest.fixture()
def db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    s.add(User(username="nvdh", full_name="nvdh", role="nv_dh", password_hash="x", active=True))
    s.commit()
    global DH
    DH = s.query(User).filter_by(username="nvdh").one().id
    yield s
    s.close()


def _han(db) -> int:
    from app.services import rules as R
    return int(R.get_param(db, "han_qt_le"))


def _tour(db, code, status, end, loai="le_noi_dia"):
    db.add(Tour(code=code, name=code, tour_type=loai, start_date=end - timedelta(days=3),
                end_date=end, status=status, planned_pax=1, operator_id=DH))


def _kq(db):
    return TQT.cho_quyet_toan(db, HOM_NAY)


# ───────────────────────── bất biến của cả khối ─────────────────────────
def test_qt1_1_ba_nhom_con_cong_dung_bang_A(db):
    """Khối lồng vẽ 709 rồi ba dòng con bên dưới. Ba dòng ấy KHÔNG cộng đủ là màn hình nói dối:
    người đọc thấy một phần biến mất mà không biết nó đi đâu."""
    han = _han(db)
    for i in range(4):
        _tour(db, f"QH{i}", "ket_thuc", HOM_NAY - timedelta(days=han + 1 + i))   # quá hạn
    for i in range(3):
        _tour(db, f"CH{i}", "ket_thuc", HOM_NAY - timedelta(days=i))             # còn trong hạn
    _tour(db, "DS1", "da_dong_so", HOM_NAY - timedelta(days=han + 9))            # nhóm B
    db.commit()
    k = _kq(db)
    assert k["ket_thuc"] == k["qua_han"] + k["con_trong_han"] + k["chua_co_ngay_ve"]
    assert (k["ket_thuc"], k["qua_han"], k["con_trong_han"]) == (7, 4, 3)


def test_qt1_2_tour_qua_han_vao_nhom_qua_han(db):
    han = _han(db)
    _tour(db, "A", "ket_thuc", HOM_NAY - timedelta(days=han + 1))
    db.commit()
    k = _kq(db)
    assert (k["qua_han"], k["con_trong_han"]) == (1, 0)


def test_qt1_3_tour_con_trong_han_khong_vao_qua_han(db):
    _tour(db, "A", "ket_thuc", HOM_NAY)
    db.commit()
    k = _kq(db)
    assert (k["qua_han"], k["con_trong_han"]) == (0, 1)


def test_qt1_4_dung_ngay_han_thi_chua_qua_han(db):
    """Mép. Giữ CÙNG luật với ô «Quá hạn quyết toán» đang chạy — nếu không, hai chỗ cùng một câu
    hỏi lại trả hai câu trả lời, đúng thứ vòng này sinh ra để dẹp."""
    han = _han(db)
    _tour(db, "BIEN", "ket_thuc", HOM_NAY - timedelta(days=han))
    db.commit()
    k = _kq(db)
    assert (k["qua_han"], k["con_trong_han"]) == (0, 1)
    assert TQT.qua_han_quyet_toan(db, HOM_NAY)["tong"] == k["qua_han"]


def test_qt1_5_da_dong_so_o_nhom_B_khong_vao_A(db):
    """1.033 tour chờ Kế toán là nhóm RIÊNG. Chủ tịch đã chốt chúng không vào ô quá hạn (có cảnh
    báo `kt_cham` riêng), nên chúng cũng không được lẫn vào A."""
    han = _han(db)
    _tour(db, "DS", "da_dong_so", HOM_NAY - timedelta(days=han + 50))
    db.commit()
    k = _kq(db)
    assert (k["da_dong_so"], k["ket_thuc"], k["qua_han"]) == (1, 0, 0)


def test_qt1_6_tong_la_A_cong_B_va_khong_gom_dong_phu(db):
    han = _han(db)
    _tour(db, "K1", "ket_thuc", HOM_NAY - timedelta(days=han + 2))
    _tour(db, "K2", "ket_thuc", HOM_NAY)
    _tour(db, "D1", "da_dong_so", HOM_NAY - timedelta(days=han + 2))
    _tour(db, "DV", "da_duyet", HOM_NAY - timedelta(days=5))     # đã qua ngày về mà chưa kết thúc
    db.commit()
    k = _kq(db)
    assert k["tong"] == k["ket_thuc"] + k["da_dong_so"] == 3
    assert k["da_ve_chua_dong_so"] >= 1
    assert k["tong"] != k["ket_thuc"] + k["da_dong_so"] + k["da_ve_chua_dong_so"]


def test_qt1_7_rang_buoc_not_null_giu_nhom_chua_co_ngay_ve_luon_bang_0(db):
    """Đổi chiều với nguồn thật thay vì tin lời em nói hôm 23/10.

    Em từng báo Chủ tịch rằng 28 tour chênh có thể lẫn chuyến thiếu ngày về. Phép thử này dựng
    đúng ca ấy bằng SQL thô để xem có dựng được không — và cơ sở dữ liệu từ chối. Chừng nào nó
    còn từ chối, nhóm «chưa có ngày về» luôn bằng 0 và màn hình ẩn dòng thứ ba. Ngày phép thử này
    ĐỎom là ngày ai đó nới cột, và lúc đó dòng thứ ba phải được hiện.
    """
    from sqlalchemy.exc import IntegrityError
    han = _han(db)
    _tour(db, "QH", "ket_thuc", HOM_NAY - timedelta(days=han + 1))
    _tour(db, "CH", "ket_thuc", HOM_NAY)
    db.commit()

    with pytest.raises(IntegrityError):
        db.execute(text(
            "INSERT INTO tours (code, name, tour_type, start_date, end_date, status,"
            " planned_pax, operator_id) VALUES ('NOEND', 'NOEND', 'le_noi_dia', '2026-10-01',"
            f" NULL, 'ket_thuc', 1, {DH})"))
    db.rollback()

    k = _kq(db)
    assert k["chua_co_ngay_ve"] == 0
    assert (k["ket_thuc"], k["qua_han"], k["con_trong_han"]) == (2, 1, 1)
    assert k["ket_thuc"] == k["qua_han"] + k["con_trong_han"] + k["chua_co_ngay_ve"]


def test_qt1_8_truyen_san_qua_han_cho_ket_qua_y_het(db):
    """`dashboard.build` truyền vào số đã đếm ở dòng trên để khỏi quét bảng tour hai lượt. Hai
    đường phải ra cùng một kết quả, không thì bảng điều hành và lời gọi lẻ nói hai con số."""
    han = _han(db)
    for i in range(3):
        _tour(db, f"Q{i}", "ket_thuc", HOM_NAY - timedelta(days=han + 1 + i))
    _tour(db, "C", "ket_thuc", HOM_NAY)
    db.commit()
    tu_dem = TQT.cho_quyet_toan(db, HOM_NAY)
    san = TQT.cho_quyet_toan(db, HOM_NAY, qua_han=TQT.qua_han_quyet_toan(db, HOM_NAY)["tong"])
    assert tu_dem == san
    assert san["qua_han"] == 3


def test_qt1_9_du_khoa_cho_man_hinh(db):
    """Khối lồng đọc đúng các khoá này. Thiếu một khoá thì một dòng của khối thành rỗng, và một
    dòng rỗng giữa các con số trông y hệt «chỗ này bằng không»."""
    db.commit()
    k = _kq(db)
    for khoa in ("tong", "ket_thuc", "da_dong_so", "da_ve_chua_dong_so",
                 "qua_han", "con_trong_han", "chua_co_ngay_ve", "cong_thuc"):
        assert khoa in k, f"thiếu khoá {khoa}"
