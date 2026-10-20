# -*- coding: utf-8 -*-
"""HQ-3 · Chuỗi 12 kỳ cho hình «Diễn biến hiệu quả đội xe» — 20/10/2026.

VÌ SAO VÒNG NÀY CÓ MẶT. Khối Chủ tịch đã có hình diễn biến từ vòng TC-71, nhưng chỗ dựng chuỗi để
RỖNG, nên hình luôn rơi về khối «chờ Đội xe nạp số». Đo trên hệ thật 20/10/2026: số của từng tháng
vẫn nằm sẵn và lấy được qua `/fleet/hieu-qua-doi-xe?moc=…` — tháng 8 doanh thu 1.591 triệu, tháng 9
là 779,5 triệu, tháng 10 là 457,5 triệu. Thứ thiếu là MỘT ĐOẠN MÃ ĐI LẤY, không phải dữ liệu.

Nói sai chỗ thiếu còn đắt hơn để trống: màn hình bảo "chờ Đội xe", nên người ta đi đòi Đội xe một
thứ Đội xe đã nộp rồi.

HAI ĐIỀU PHÉP THỬ NÀY CANH, và cả hai đều là chỗ dễ "sửa cho đẹp" rồi hỏng:

  1. ĐỦ 12 CỘT, kể cả tháng không có chuyến nào. Lọc tháng rỗng ra cho hình liền mạch là bóp hai
     tháng cách nhau một quãng nghỉ thành hai cột liền nhau — đường nối giữa chúng đọc ra như một
     đà tăng liên tục chưa từng có.
  2. THÁNG RỖNG MANG `None`, KHÔNG PHẢI 0. Vẽ 0 là nói rằng tháng ấy đội xe có chạy mà không thu
     được đồng nào. `BieuDoDuong` cắt đường tại `None` và nối qua số 0 — hai hình khác hẳn nhau.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle  # noqa: E402
from app.models.fleet import Trip  # noqa: E402
from app.services import hieu_qua_xe as HQ  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _xe(db, bien="50F-017.37", cho=45, vao=date(2025, 1, 1)):
    v = Vehicle(plate=bien, seats=cho, ngay_vao_doi=vao)
    db.add(v); db.flush()
    return v


def _chuyen(db, v, ma, di, ve, kd, kc, dt=0.0):
    t = Trip(ma_phieu=ma, vehicle_id=v.id, ngay_di=di, ngay_ve=ve, km_dau=kd, km_cuoi=kc,
             doanh_thu=dt, ten_tour="thử")
    db.add(t); db.flush()
    return t


def test_chuoi_la_12_thang_cua_NAM_T1_den_T12(db):
    v = _xe(db)
    _chuyen(db, v, "A1", date(2026, 10, 1), date(2026, 10, 2), 1000, 1300, dt=9_000_000)

    ds = HQ._chuoi(db, date(2026, 10, 20))

    assert len(ds) == 12, "Trục phải đủ 12 cột dù chỉ một tháng có chuyến"
    assert ds[0]["ky"] == "2026-01", "Cột đầu là THÁNG 1 của năm chứa `moc`"
    assert ds[-1]["ky"] == "2026-12", "Cột cuối là THÁNG 12 — kể cả khi tháng ấy chưa tới"
    assert [d["ky"] for d in ds] == sorted(d["ky"] for d in ds), "Phải xếp cũ → mới"


def test_thang_khong_co_chuyen_tra_None_chu_khong_phai_0(db):
    v = _xe(db)
    _chuyen(db, v, "A1", date(2026, 10, 1), date(2026, 10, 2), 1000, 1300, dt=9_000_000)

    ds = {d["ky"]: d for d in HQ._chuoi(db, date(2026, 10, 20))}

    assert ds["2026-10"]["doanh_thu"] == 9_000_000
    # Tháng 9 không nạp chuyến nào. `None` nghĩa là CHƯA CÓ SỐ; 0 nghĩa là CÓ CHẠY MÀ KHÔNG THU
    # ĐƯỢC ĐỒNG NÀO. Hình vẽ hai thứ ấy khác hẳn nhau, nên sổ phải phân biệt được.
    assert ds["2026-09"]["doanh_thu"] is None
    assert ds["2026-09"]["loi_nhuan"] is None
    # Tháng CHƯA TỚI cũng vậy: có cột, mang None. Bỏ cột đi thì hình co lại dần theo từng tháng
    # trong năm, và một hình đổi bề ngang mỗi lần mở là một hình không so được với lần mở trước.
    assert ds["2026-12"]["doanh_thu"] is None


def test_theo_ky_tra_kem_chuoi_de_man_hinh_khong_phai_goi_12_lan(db):
    v = _xe(db)
    _chuyen(db, v, "A1", date(2026, 10, 1), date(2026, 10, 2), 1000, 1300, dt=9_000_000)

    out = HQ.theo_ky(db, date(2026, 10, 20), hom_nay=date(2026, 10, 20))

    assert "chuoi" in out, "Màn hình phải lấy được cả chuỗi trong MỘT lượt gọi"
    assert len(out["chuoi"]) == 12
    assert out["chuoi"][-1]["ky"] == "2026-12"


def test_nhan_cot_doc_duoc_tren_truc_hep(db):
    _xe(db)
    ds = HQ._chuoi(db, date(2026, 10, 20))
    # 12 nhãn phải nằm vừa một trục ngang trên màn hình hẹp, nên dùng "T9/26" chứ không "09/2026".
    assert ds[-1]["nhan"] == "T12/26"
    assert ds[0]["nhan"] == "T1/26"
