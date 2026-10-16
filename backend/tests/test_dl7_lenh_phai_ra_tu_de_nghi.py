# -*- coding: utf-8 -*-
"""DL-7 · Lệnh điều xe phải ra từ một ĐỀ NGHỊ XE (Chủ tịch chốt 16/10/2026).

VÌ SAO SIẾT, VÀ VÌ SAO LÀ HÔM NAY. DL-1 (11/10) dựng chuỗi ba mắt — Điều hành đề nghị → Giám đốc
đội xe lập lệnh → tài xế nhận — nhưng để `de_nghi_id` RỖNG ĐƯỢC, có chủ ý, và ghi sẵn luật thoát
trong `de_nghi_xe.lenh_khong_qua_de_nghi()`: «con số về 0 thì siết thành bắt buộc là một dòng».

Đo trên hệ thật 16/10/2026, đọc thẳng màn hình Lệnh điều xe: **Lệnh đã lập (0)**, **Đề nghị xe
đang chờ lập lệnh (0)**. Không có lệnh nào trong hệ thống. Siết lúc này không làm ai đứng việc, và
đây là lúc RẺ NHẤT để siết — chưa ai có thói quen cũ phải bỏ.

KHÔNG CÓ NÚT VƯỢT TỪNG LẦN. Một ô «vượt kèm lý do» trên từng lệnh sẽ thành đường chính sau vài
tuần — đúng như đã xảy ra với ô lý do chọn khác gợi ý. Chỉ có MỘT công tắc chính sách cấp hệ
thống, Chủ tịch đổi, và việc đổi có ghi nhật ký.
"""
import os
import tempfile
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.services import rules as R  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def test_tham_so_duoc_khai_va_BAT_SAN(db):
    """Khai mà để 0 thì chuỗi vẫn hở — và một hàng rào tắt sẵn là một hàng rào không ai bật."""
    khoa = {k: v for k, v, *_ in R.BO_THAM_SO} if hasattr(R, "BO_THAM_SO") else None
    if khoa is None:
        import re
        src = open(R.__file__, encoding="utf-8").read()
        m = re.search(r'\("xe_bat_buoc_qua_de_nghi",\s*"([^"]*)"', src)
        assert m, "chưa khai tham số xe_bat_buoc_qua_de_nghi trong rules.py"
        assert m.group(1) == "1", "tham số phải BẬT SẴN"
    else:
        assert khoa.get("xe_bat_buoc_qua_de_nghi") == "1"


def test_cua_lap_lenh_doc_tham_so_va_chan_khi_thieu_de_nghi():
    """Đọc mã nguồn: cửa lập lệnh phải TỰ nó kiểm, không để nơi khác kiểm hộ."""
    import inspect
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_create)
    assert "xe_bat_buoc_qua_de_nghi" in src, "cửa lập lệnh không đọc tham số siết chuỗi"
    assert "de_nghi_id" in src


def test_cau_tu_choi_phai_CHI_DUONG_chu_khong_chi_noi_khong():
    """Người bị chặn lúc 7 giờ sáng cần biết bấm vào đâu, chứ không cần biết ai quyết ngày nào."""
    import inspect
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_create)
    i = src.find("xe_bat_buoc_qua_de_nghi")
    doan = src[i:i + 900]
    assert "Lấy vào mẫu" in doan, "câu từ chối không nói người dùng phải bấm nút nào"
    assert "Điều hành đề nghị xe" in doan, "câu từ chối không nói khối nào trên màn hình"


def test_KHONG_co_nut_vuot_tung_lan_trong_cua_lap_lenh():
    """Đường vòng có ghi lý do thành đường chính sau vài tuần. Chỉ được có công tắc cấp hệ thống."""
    import inspect
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_create)
    for xau in ("bo_qua_de_nghi", "khong_can_de_nghi", "vuot_de_nghi", "ly_do_khong_de_nghi"):
        assert xau not in src, f"có đường vòng từng lần: {xau}"


def test_tat_tham_so_thi_lenh_khong_kem_de_nghi_lai_qua_duoc(db):
    """Công tắc phải thật sự là công tắc: tắt thì về đúng hành vi cũ, không phải nửa vời."""
    import inspect
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_create)
    # chỉ chặn khi tham số bật — không chặn vô điều kiện
    assert "if not data.de_nghi_id and bool(R.get_param(db, \"xe_bat_buoc_qua_de_nghi\"))" in src


def test_o_dem_cu_cua_DL1_van_con_de_do_lai_sau_khi_siet(db):
    """Siết rồi vẫn phải đếm được: nếu công tắc từng bị tắt thì con số nói ra bao nhiêu lệnh đã lọt."""
    from app.services import de_nghi_xe as DN
    ra = DN.lenh_khong_qua_de_nghi(db)
    assert ra["tong_lenh"] == 0 and ra["khong_qua_de_nghi"] == 0
    assert "ghi_chu" in ra
