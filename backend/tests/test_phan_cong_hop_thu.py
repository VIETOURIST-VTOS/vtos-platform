# -*- coding: utf-8 -*-
"""PQ-9 · Giao chủ cho hội thoại khách, luân phiên.

Đo bản đang chạy 11/9/2026: 100 trên 100 hội thoại để trống sales_id, 3 quá hạn SLA, AI đã trả lời
thay 4. Cột sales_id có từ đầu; thứ chưa bao giờ có là LUẬT nói hội thoại mới vào tay ai.

Hai thứ tệp này canh kỹ nhất, vì cả hai đều là cách dễ nhất để con số 100 kia lặng lẽ quay lại:

  1. "Chưa có chủ" phải ĐẾM ĐƯỢC. Một hàm quét trả về "đã giao 0" mà không nói vì sao thì đọc ra
     giống hệt "hộp thư đã sạch".
  2. Robot chỉ GIAO chỗ trống, KHÔNG đổi chủ. Một hàm chạy nền mà đổi chủ được thì chủ sở hữu chỉ
     là tạm thời, và nguyên tắc một cửa mất nghĩa ngay từ chỗ ấy.
"""
from datetime import datetime, timedelta

import pytest

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
import app.models.crm   # noqa: F401
from app.models.core import User
from app.models.crm import Conversation
from app.services import phan_cong_hop_thu as PC


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md.create_all(eng)
    with Session(eng) as s:
        yield s


def _sale(db, ten, vai="nv_kd", active=True):
    u = User(username=ten, full_name=ten.upper(), role=vai, active=active, password_hash="x")
    db.add(u); db.flush()
    return u


def _hoi_thoai(db, ext, sales_id=None, status="mo", den=None):
    c = Conversation(channel="facebook", external_id=ext, sales_id=sales_id, status=status,
                     last_in_at=den or datetime.now(), unanswered=True)
    db.add(c); db.flush()
    return c


# ---------------------------------------------------------------------------------------------
# 1. Luân phiên: mỗi người một cái rồi mới quay lại
# ---------------------------------------------------------------------------------------------

def test_chia_deu_truoc_khi_quay_lai_nguoi_dau(db):
    a, b, c = _sale(db, "an"), _sale(db, "binh"), _sale(db, "cuong")
    nhan = []
    for i in range(6):
        h = _hoi_thoai(db, f"x{i}")
        PC.giao(db, h); db.flush()
        nhan.append(h.sales_id)
    dem = {u.id: nhan.count(u.id) for u in (a, b, c)}
    assert set(nhan[:3]) == {a.id, b.id, c.id}, "ba cái đầu phải rơi vào ba người khác nhau"
    assert set(dem.values()) == {2}, f"chia không đều: {dem}"


def test_nguoi_dang_giu_nhieu_thi_chua_toi_luot(db):
    """Đây là điểm khác giữa luân phiên theo tải và con trỏ quay vòng.

    Người vừa nhận mười hội thoại nặng mà vẫn tới lượt như người đang rảnh thì "luân phiên" chỉ
    công bằng trên sổ, không công bằng trên bàn làm việc.
    """
    a, b = _sale(db, "an"), _sale(db, "binh")
    for i in range(3):
        _hoi_thoai(db, f"cu{i}", sales_id=a.id)
    db.flush()
    h = _hoi_thoai(db, "moi")
    PC.giao(db, h)
    assert h.sales_id == b.id


def test_hoi_thoai_da_dong_khong_tinh_vao_tai(db):
    """Đếm cả việc đã xong nghĩa là phạt người làm nhanh – người đóng nhiều sẽ nhận ít dần.

    Bản đầu của phép thử này ĐỎ, và mã đúng chứ phép thử sai: nó cho a năm hội thoại đã đóng, cho b
    không gì cả, rồi đòi hội thoại mới phải rơi vào a. Hai người cùng tải 0 thật, nhưng luật phá thế
    hòa là "ai lâu nhất chưa được giao", và b chưa được giao bao giờ – nên b đúng là người tới lượt.
    Sửa phép thử chứ không sửa luật: cho b một hội thoại ĐANG MỞ, để phép thử đo đúng một điều nó
    sinh ra để đo – việc đã đóng không tính vào tải.
    """
    a, b = _sale(db, "an"), _sale(db, "binh")
    for i in range(5):
        _hoi_thoai(db, f"xong{i}", sales_id=a.id, status="dong")
    _hoi_thoai(db, "dang_lam", sales_id=b.id)
    db.flush()
    assert PC.tai_dang_mo(db).get(a.id, 0) == 0, "năm cái đã đóng vẫn bị tính là tải"
    assert PC.tai_dang_mo(db).get(b.id, 0) == 1
    h = _hoi_thoai(db, "moi")
    PC.giao(db, h)
    assert h.sales_id == a.id, "a đóng xong hết mà vẫn bị coi là bận hơn b"


def test_hoa_tai_thi_uu_tien_nguoi_lau_nhat_chua_duoc_giao(db):
    """Hòa tải mà luôn chọn id nhỏ hơn thì người vào làm trước chịu thiệt suốt đời."""
    a, b = _sale(db, "an"), _sale(db, "binh")
    cu = _hoi_thoai(db, "cu", sales_id=a.id, status="dong")
    cu.created_at = datetime.now()
    moi_hon = _hoi_thoai(db, "cu2", sales_id=b.id, status="dong")
    moi_hon.created_at = datetime.now() - timedelta(days=5)
    db.flush()
    h = _hoi_thoai(db, "moi")
    PC.giao(db, h)
    assert h.sales_id == b.id, "b được giao lâu hơn nên phải tới lượt b"


# ---------------------------------------------------------------------------------------------
# 2. Ai ở trong vòng
# ---------------------------------------------------------------------------------------------

def test_tai_khoan_da_khoa_ra_khoi_vong_ngay(db):
    a = _sale(db, "an", active=False)
    b = _sale(db, "binh")
    h = _hoi_thoai(db, "x")
    PC.giao(db, h)
    assert h.sales_id == b.id
    assert a.id not in {u.id for u in PC.nguoi_trong_vong(db)}


def test_quan_ly_khong_nam_trong_vong(db):
    """Giao cho Trưởng phòng hay Giám đốc là cách chắc chắn để hội thoại nằm im trong hộp thư bận nhất."""
    for vai in ("gd_kd", "tp_kd", "ptgd_mkt", "chutich"):
        assert vai not in PC.VAI_TRO_NHAN, vai
    assert "nv_kd" in PC.VAI_TRO_NHAN


def test_khong_con_ai_thi_KHONG_giao_bua_va_phai_noi_ra(db):
    """Giao bừa cho một người mặc định để danh sách trông sạch là biến lỗ hổng đếm được thành
    lỗ hổng không đếm được nữa."""
    _sale(db, "sep", vai="gd_kd")
    h = _hoi_thoai(db, "x")
    kq = PC.giao(db, h)
    assert kq["da_giao"] is False
    assert kq["ly_do"] == PC.KHONG_CO_NGUOI
    assert h.sales_id is None
    assert "Không có ai trong vòng" in PC.bao_cao(db)["canh_bao"]


# ---------------------------------------------------------------------------------------------
# 3. Chỉ giao chỗ trống – không đổi chủ
# ---------------------------------------------------------------------------------------------

def test_khong_bao_gio_doi_chu_mot_hoi_thoai_da_co_nguoi(db):
    a, b = _sale(db, "an"), _sale(db, "binh")
    for i in range(9):
        _hoi_thoai(db, f"tai{i}", sales_id=a.id)
    db.flush()
    h = _hoi_thoai(db, "cua_a", sales_id=a.id)
    kq = PC.giao(db, h)
    assert kq["da_giao"] is False and kq["ly_do"] == PC.DA_CO_CHU
    assert h.sales_id == a.id, "robot nền vừa đổi chủ – một cửa mất nghĩa từ chỗ này"


def test_quet_lai_lan_hai_khong_lam_gi_them(db):
    _sale(db, "an"); _sale(db, "binh")
    for i in range(4):
        _hoi_thoai(db, f"x{i}")
    db.flush()
    m = PC.giao_het_chua_co_chu(db); db.flush()
    hai = PC.giao_het_chua_co_chu(db)
    assert m["da_giao"] == 4 and m["con_chua_co_chu"] == 0
    assert hai["xet"] == 0 and hai["da_giao"] == 0


# ---------------------------------------------------------------------------------------------
# 4. "Chưa có chủ" phải đếm được
# ---------------------------------------------------------------------------------------------

def test_bao_cao_noi_ro_bao_nhieu_cai_chua_co_chu(db):
    _sale(db, "an")
    for i in range(3):
        _hoi_thoai(db, f"trong{i}")
    _hoi_thoai(db, "cua_an", sales_id=1)
    db.flush()
    r = PC.bao_cao(db)
    assert r["chua_co_chu"] == 3
    assert r["hoi_thoai_dang_mo"] == 4
    assert r["nguoi_ke_tiep"] is not None


def test_quet_khong_giao_duoc_thi_dem_ly_do_chu_khong_tra_ve_0_im_lang(db):
    """'đã giao 0' đọc ra giống hệt 'hộp thư đã sạch'. Hai thứ ấy phải phân biệt được."""
    for i in range(5):
        _hoi_thoai(db, f"x{i}")
    db.flush()
    r = PC.giao_het_chua_co_chu(db)
    assert r["da_giao"] == 0
    assert r["con_chua_co_chu"] == 5, "quét xong còn 5 cái không chủ mà báo cáo không nói"
    assert r["khong_giao_duoc"] == {PC.KHONG_CO_NGUOI: 5}


def test_uu_tien_hoi_thoai_KHACH_CHO_LAU_NHAT(db):
    """Chia đều là chưa đủ – khách chờ lâu nhất phải được xét trước.

    Đo thứ tự bằng KẾT QUẢ chứ không bằng dấu vết: hai tư vấn viên cùng tải 0, người được chọn đầu
    tiên là người có id nhỏ hơn. Vậy hội thoại nào rơi vào an chính là hội thoại được xét trước.

    Bản đầu chỉ hỏi "cu.summary có chữ giao luân phiên không" – câu ấy đúng dù quét theo thứ tự nào,
    nên một đột biến đảo ngược thứ tự quét đã lọt qua cả bộ. Phép thử xanh vì không đo gì.
    """
    an, binh = _sale(db, "an"), _sale(db, "binh")
    nay = datetime.now()
    # Tạo hội thoại CŨ trước để id của nó nhỏ hơn. Bản trước tạo ngược lại, nên một đột biến quét
    # theo id giảm dần vẫn tình cờ ra đúng thứ tự và lọt lưới: phép thử đo trúng kết quả nhưng
    # không tách được "đúng vì luật đúng" khỏi "đúng vì id tình cờ xếp như vậy".
    cu = _hoi_thoai(db, "cu", den=nay - timedelta(hours=20))
    moi = _hoi_thoai(db, "moi", den=nay)
    db.flush()
    PC.giao_het_chua_co_chu(db); db.flush()
    assert cu.sales_id == an.id, "khách chờ 20 giờ bị xét sau khách vừa nhắn"
    assert moi.sales_id == binh.id
    assert "giao luân phiên" in cu.summary
