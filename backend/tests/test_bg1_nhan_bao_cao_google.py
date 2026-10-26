# -*- coding: utf-8 -*-
"""BG-1 · Cửa nhận báo cáo ngày từ hệ Google — anh Tuấn chốt 25/10/2026.

Màn hình /reports dựng xong trước khi có dữ liệu: ngày 24/10 bảng hiện **0/86 đã nộp** và cả 86
người xếp D, trong khi 24 người trong số đó ĐÃ nộp thật sáng hôm ấy trên hệ Google Apps Script —
nơi 86 người đang nộp từ 01/9/2026. Một bảng nói sai về người thật thì người đọc thôi tin nó, kể
cả sau khi dữ liệu về.

Bộ hàng rào này canh năm điều, mỗi điều là một cách hỏng đã thấy ở nơi khác trong chính kho này:

  1. CỬA KHÔNG ĐƯỢC CÓ LUẬT RIÊNG. Nó phải gọi `submit_report` — cùng đường người nộp thẳng trên
     VTOS đi qua — để bản chụp, đường BC-2, mốc hạn BC-1 và điểm nháp không bao giờ lệch. Viết lại
     phép tính ở cửa nhận là dựng hai chỗ trả lời một câu.
  2. GỬI LẠI PHẢI ĐÈ, không sinh dòng thứ hai. Nhân viên sửa rồi gửi lại trong ngày là chuyện
     thường; sinh dòng mới là cách bảng tháng đếm một người thành hai.
  3. ĐÚNG HẠN TÍNH THEO `han_nop`, không tự so với một con số viết chết. Mốc 0 giờ của BC-1 có
     ngày hiệu lực và không hồi tố; một cửa tự so "20:00" sẽ chấm sai mọi ngày sau mốc.
  4. MÃ LẠ THÌ BÁO, KHÔNG TỰ TẠO NGƯỜI. Cửa nhận dữ liệu tự đẻ ra tài khoản là lúc danh sách nhân
     sự có hai nguồn sự thật.
  5. ĐIỂM KHÔNG ĐỨNG MỘT MÌNH. `loai="diem"` chỉ gắn được lên báo cáo đã có.
"""
import datetime as dt
import io as _io
import json
import os as _os
import sys

sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
GOC = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))

from sqlalchemy import create_engine, select          # noqa: E402
from sqlalchemy.orm import sessionmaker               # noqa: E402

from app.db.session import Base                       # noqa: E402
from app.models.core import User                      # noqa: E402
from app.models.hr import Employee                    # noqa: E402
from app.models.ops import DailyReport                # noqa: E402
from app.services import ops as O                     # noqa: E402
from app.services import bao_cao_google as BG         # noqa: E402

NGAY = dt.date(2026, 10, 24)


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    u = User(username="linh", full_name="Nguyễn Thị Thùy Linh", role="nv_kd",
             department="kd_le", password_hash="x")
    s.add(u)
    s.flush()
    s.add(Employee(code="165", user_id=u.id, full_name="Nguyễn Thị Thùy Linh",
                   department="kd_le", position="nv", active=True))
    s.commit()
    return s


def _muc(**kw):
    m = {"maNV": "165", "ngay": NGAY,
         "phan1": "Chốt booking 128037 khách Trần Thị H tuyến Đà Nẵng",
         "phan3": "Gọi lại nhóm lead Đà Lạt còn tồn từ tuần trước",
         "phan4": "Cần Điều hành xác nhận còn phòng tuyến Đà Nẵng",
         "soLieu": [["Lead nhận trong ngày", "14"], ["Booking chốt trong ngày", "2"]],
         "nopLuc": "2026-10-24T17:42:00+07:00"}
    m.update(kw)
    return m


def test_bg1_1_nhan_duoc_va_gui_lai_thi_de():
    s = _db()
    kq = BG.nhan(s, [_muc()], "baocao")
    assert kq["nhan"] == 1 and kq["loi"] == []
    kq2 = BG.nhan(s, [_muc(phan1="Bản sửa lại, dài hơn hai mươi ký tự")], "baocao")
    assert kq2["nhan"] == 1, kq2
    rows = s.execute(select(DailyReport)).scalars().all()
    assert len(rows) == 1, "gửi lại phải ĐÈ, không sinh dòng thứ hai"
    assert "Bản sửa lại" in rows[0].part1_done
    assert (rows[0].so_lan_nop or 0) == 2, "phải đếm được số lần nộp như người nộp thẳng"


def test_bg1_2_dung_han_tinh_theo_han_nop_cua_BC1():
    """Không so với một con số viết chết: mốc 0 giờ có ngày hiệu lực và KHÔNG hồi tố."""
    s = _db()
    BG.nhan(s, [_muc()], "baocao")
    r = s.execute(select(DailyReport)).scalars().first()
    nop = dt.datetime(2026, 10, 24, 17, 42)
    assert r.first_submitted_at == nop, "giờ nộp phải lấy từ bản đẩy sang, không phải giờ máy chủ"
    assert r.on_time is (nop < O.han_nop(s, NGAY))

    s2 = _db()
    sau = dt.date(2026, 11, 2)   # sau mốc 0 giờ
    BG.nhan(s2, [_muc(ngay=sau, nopLuc="2026-11-02T21:12:00+07:00")], "baocao")
    r2 = s2.execute(select(DailyReport)).scalars().first()
    assert r2.on_time is True, "sau mốc BC-1 thì 21:12 cùng ngày vẫn trong hạn"


def test_bg1_3_ma_la_thi_bao_chu_khong_tu_tao_nguoi():
    s = _db()
    truoc = len(s.execute(select(User)).scalars().all())
    kq = BG.nhan(s, [_muc(maNV="999")], "baocao")
    assert kq["nhan"] == 0 and len(kq["loi"]) == 1 and kq["loi"][0]["maNV"] == "999"
    assert len(s.execute(select(User)).scalars().all()) == truoc, "không được tự tạo tài khoản"
    assert s.execute(select(DailyReport)).scalars().first() is None


def test_bg1_4_truong_phong_da_cham_thi_khong_de():
    s = _db()
    BG.nhan(s, [_muc()], "baocao")
    r = s.execute(select(DailyReport)).scalars().first()
    r.manager_score, r.reviewed_by = 9.0, "tpkd"
    s.commit()
    kq = BG.nhan(s, [_muc(phan1="Bản mới không được đè lên bài đã chấm")], "baocao")
    assert kq["nhan"] == 0 and "đã được trưởng phòng chấm" in kq["loi"][0]["vi_sao"]
    s.expire_all()
    assert "không được đè" not in s.execute(select(DailyReport)).scalars().first().part1_done


def test_bg1_5_diem_khong_dung_mot_minh():
    s = _db()
    kq = BG.nhan(s, [{"maNV": "165", "ngay": NGAY, "diemRobot": 8}], "diem")
    assert kq["nhan"] == 0, "chưa có báo cáo thì không gắn điểm"
    BG.nhan(s, [_muc()], "baocao")
    kq = BG.nhan(s, [{"maNV": "165", "ngay": NGAY, "diemRobot": 8, "xepLoaiRobot": "A",
                                    "canhBao": ["dán 3 số điện thoại khách"]}], "diem")
    assert kq["nhan"] == 1
    s.expire_all()
    r = s.execute(select(DailyReport)).scalars().first()
    assert r.robot_score == 8 and "A" in r.robot_note and "điện thoại" in r.robot_note


def test_bg1_6_phan_2_giu_nguyen_nhan_va_hai_phan_khong_bi_doi_cho():
    s = _db()
    BG.nhan(s, [_muc(nghiPhep="Nghỉ phép")], "baocao")
    r = s.execute(select(DailyReport)).scalars().first()
    p2 = json.loads(r.part2_numbers)
    assert p2["Lead nhận trong ngày"] == "14"
    assert "Nghỉ phép" in p2["Nghỉ phép / công tác / lễ"]
    assert "lead Đà Lạt" in r.part4_plan, "Phần 3 của form Google là VIỆC NGÀY MAI"
    assert "Điều hành xác nhận" in r.part3_issues, "Phần 4 của form Google là VƯỚNG MẮC"


def test_bg1_7_cua_chan_bang_robot_token_va_khong_co_luat_rieng():
    """Hai điều: cửa phải chặn, và cửa KHÔNG được tự tính hạn nộp lần thứ hai.

    Điều thứ hai mới là điều đắt. Bản viết đầu tiên tự tính `on_time` bằng `REPORT_DEADLINE` trên
    một bản mã cũ hơn main 465 dòng — nó không biết BC-1 vừa đặt mốc hạn 0 giờ CÓ NGÀY HIỆU LỰC.
    Đẩy lên thì cửa chấm sai hạn mọi ngày sau mốc mà không phép thử nào đỏ, vì luật mới nằm trong
    hàm mà cửa không gọi tới.
    """
    api = _io.open(_os.path.join(GOC, "app", "api", "v1", "tu_dong.py"), encoding="utf-8").read()
    i = api.index("/bao-cao-ngay/nhan-tu-google")
    assert "robot_auth" in api[api.rindex("@router", 0, i):i + 200], "cửa nhận phải chặn bằng robot_auth"
    svc = _io.open(_os.path.join(GOC, "app", "services", "bao_cao_google.py"), encoding="utf-8").read()
    than = svc[svc.index("def nhan("):]
    assert "submit_report(" in than, "phải đi qua submit_report, không được có luật nộp riêng"
    for cam in ("REPORT_DEADLINE", "time(20", "on_time ="):
        assert cam not in than, "cửa nhận tự tính hạn nộp lần thứ hai: " + cam


def test_bg1_8_khong_dung_vao_tep_lan_khac_dang_giu():
    """Làn Phân quyền đang giữ `ops.py` cho BC-1/BC-2. Vòng này cố ý đứng ngoài hai tệp ấy."""
    svc = _io.open(_os.path.join(GOC, "app", "services", "ops.py"), encoding="utf-8").read()
    api = _io.open(_os.path.join(GOC, "app", "api", "v1", "ops.py"), encoding="utf-8").read()
    assert "nhan_bao_cao_google" not in svc and "nhan-tu-google" not in api
