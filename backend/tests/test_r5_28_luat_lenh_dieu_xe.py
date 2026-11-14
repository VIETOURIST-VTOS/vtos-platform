# -*- coding: utf-8 -*-
"""R5-28 · Luật lệnh điều xe (Chủ tịch 14/11/2026 «chỉ GĐ điều xe», chọn «1 và 2»).

  1a. Ngày lệnh phải nằm trong ngày tour.
  1b. Một đề nghị ra tối đa đúng số xe nó xin (lệnh huỷ không tính).
  2.  Tham số người lập lệnh trống / gõ sai thì CHỈ vai Giám đốc đội xe lập được — không mở cho Điều hành, TP
      Điều hành, CNTT như trước. Lập, chốt, đóng, huỷ, đổi xe, đổi tài xế đi qua MỘT hàng rào.
"""
import inspect

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services import rules as R
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    R.clear_param_cache()
    yield s
    s.close()


def _u(db, ten, vai, active=True):
    from app.models.core import User
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x", active=active)
    db.add(u); db.flush()
    return u


def _dat(db, gia_tri):
    from app.models.core import Param
    from app.services import rules as R
    p = db.query(Param).filter_by(key="xe_nguoi_lap_lenh").first()
    if p is None:
        p = Param(key="xe_nguoi_lap_lenh", value=gia_tri, label="Người lập lệnh", effective_from=__import__("datetime").date(2026, 1, 1)); db.add(p)
    p.value = gia_tri
    db.commit(); R.clear_param_cache()


@pytest.mark.parametrize("gia_tri", ["", "khong-ai-ten-nay"])
def test_tham_so_trong_hoac_sai_thi_chi_gd_doi_xe(db, gia_tri):
    from app.services import fleet as FL
    gd = _u(db, "gd.xe", "gd_doi_xe"); dh = _u(db, "dh.a", "nv_dh"); tp = _u(db, "tp.dh", "tp_dh")
    _u(db, "gd.cu", "gd_doi_xe", active=False)
    cn = _u(db, "it", "cntt")
    _dat(db, gia_tri)
    ai, ly_do = FL.nguoi_duoc_lap_lenh(db)
    assert [x.username for x in ai] == ["gd.xe"] and "chỉ Giám đốc đội xe" in ly_do
    FL.chan_neu_khong_phai(db, gd)
    for x in (dh, tp, cn):
        with pytest.raises(PermissionError):
            FL.chan_neu_khong_phai(db, x)


def test_khong_con_gd_nao_thi_chan_het(db):
    from app.services import fleet as FL
    cn = _u(db, "it", "cntt")
    _dat(db, "")
    assert FL.nguoi_duoc_lap_lenh(db)[0] == []
    with pytest.raises(PermissionError):
        FL.chan_neu_khong_phai(db, cn)


def test_tham_so_dung_thi_dung_nguoi_ay(db):
    from app.services import fleet as FL
    gd = _u(db, "nguyenhonghuan", "gd_doi_xe"); _u(db, "gd.khac", "gd_doi_xe")
    _dat(db, "nguyenhonghuan")
    assert [x.id for x in FL.nguoi_duoc_lap_lenh(db)[0]] == [gd.id]


def test_moi_cua_ghi_lenh_qua_mot_hang_rao_va_dieu_hanh_roi_cua():
    from app.api.v1 import hr
    for f in (hr.dispatch_create, hr.dispatch_update, hr._lenh_de_doi):
        assert "FL.chan_neu_khong_phai(" in inspect.getsource(f), f.__name__
    for f in (hr.dispatch_create, hr.dispatch_doi_xe, hr.dispatch_doi_tai_xe):
        dau = inspect.getsource(f).split(")):")[0]
        assert '"nv_dh"' not in dau and '"tp_dh"' not in dau, f.__name__
    up = inspect.getsource(hr.dispatch_update)
    assert '"hoan_thanh": "đóng lệnh điều xe"' in up and '"huy": "huỷ lệnh điều xe"' in up


def test_ngay_lenh_trong_ngay_tour_va_so_lenh_theo_so_xe():
    from app.api.v1 import hr
    src = inspect.getsource(hr.dispatch_create)
    assert "data.date_from < t.start_date or data.date_to > t.end_date" in src
    assert 'DispatchOrder.status != "huy"' in src and "da_lap >= can" in src


def test_du_lieu_mau_co_giam_doc_doi_xe():
    from app.services import seed
    assert ("gd.doixe", "Giám đốc điều hành đội xe", "gd_doi_xe", "Đội xe") in seed.USERS
