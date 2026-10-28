# -*- coding: utf-8 -*-
"""CD-2 · Sổ cổ đông, hồ sơ sở hữu, ưu đãi cổ đông (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Đọc tệp VSD: nhận cột theo tên, bỏ dòng tổng, báo lỗi theo dòng; giấy tờ chuẩn hóa.
  2. IR tải, Chủ tịch duyệt; người tải không tự duyệt; tệp trùng / hai lô chờ bị chặn; chưa duyệt không dùng.
  3. Nối: chỉ số giấy tờ có trong danh sách đang dùng; gỡ có lý do, không xoá; cổ đông chỉ thấy số của mình.
  4. Lô mới duyệt thay lô cũ; không còn tên → «không có tên».
  5. Gửi xác minh: thành câu hỏi IR «Tư cách», tệp đánh dấu nhạy cảm.
  6. Ưu đãi: cổ đông đã xác minh gửi được yêu cầu tour như khách hàng; cổ đông chưa duyệt bị chặn.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

HEAD = "STT,Họ và tên,Số ĐKSH,Số TK lưu ký,Số lượng CK\n"


def _csv(*dong):
    return (HEAD + "\n".join(dong) + "\n").encode("utf-8")


T1 = _csv("1,NGUYỄN VĂN A,001.088.012345,001C123456,\"12.500\"", "2,CÔNG TY X,0101234567,002C000001,1000000",
          "3,NGUYỄN VĂN A,001088012345,003C999999,500", "4,THIẾU GIẤY TỜ,,,10", "Tổng cộng,,,,1012510")
T2 = _csv("1,CÔNG TY X,0101234567,002C000001,1000000")


class _Kho:
    def __init__(self): self.d = {}
    def put(self, key, data, kieu=""):
        self.d[key] = data
        return type("L", (), {"key": key, "checksum": __import__("hashlib").sha256(data).hexdigest()})()
    def get(self, key): return self.d[key]


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.services import storage as ST
    ST._CACHE["s"] = _Kho()
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("ir", "ir_phapche"), ("ir2", "ir_phapche"), ("tgd", "tgd")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.commit()
    yield s
    s.close(); ST._CACHE.clear()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _tk(s, giay_to="001088012345", tt="hoat_dong", sdt="0901234567", loai="co_dong"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai=loai, dien_thoai=sdt, trang_thai=tt, ho_ten="A", giay_to=giay_to)
    s.add(tk); s.commit()
    return tk


def test_doc_tep_vsd():
    from app.services import so_co_dong as SC
    r = SC.doc_tep("ds.csv", T1)
    assert r["so_dong"] == 3 and r["tong_cp"] == 1013000 and r["so_nguoi"] == 2
    assert r["dong"][0]["giay_to"] == "001088012345" and r["dong"][0]["so_cp"] == 12500
    assert r["loi"] == [{"dong": 5, "loi": "thiếu số giấy tờ"}]      # dòng «Tổng cộng» bỏ qua, «Công ty X» giữ
    with pytest.raises(SC.LoiSo, match="ba cột"):
        SC.doc_tep("x.csv", b"a,b,c\n1,2,3\n")
    with pytest.raises(SC.LoiSo):
        SC.doc_tep("x.pdf", b"%PDF")


def test_tai_duyet_hai_nguoi_va_chan_trung(db):
    from app.services import so_co_dong as SC
    with pytest.raises(SC.LoiSo) as ex:
        SC.gui_duyet(db, _u(db, "ct"), dt.date(2026, 10, 20), "ds.csv", T1)
    assert ex.value.status == 403
    lo = SC.gui_duyet(db, _u(db, "ir"), dt.date(2026, 10, 20), "ds.csv", T1); db.commit()
    assert SC.lo_hien_hanh(db) is None                                   # chưa duyệt thì chưa dùng
    with pytest.raises(SC.LoiSo) as ex:
        SC.gui_duyet(db, _u(db, "ir"), dt.date(2026, 10, 20), "ds.csv", T1)
    assert ex.value.status == 409
    with pytest.raises(SC.LoiSo) as ex:
        SC.gui_duyet(db, _u(db, "ir2"), dt.date(2026, 10, 21), "ds2.csv", T2)
    assert ex.value.status == 409                                        # một lô chờ một lúc
    with pytest.raises(SC.LoiSo) as ex:
        SC.duyet(db, _u(db, "ir"), lo.id)
    assert ex.value.status == 403
    ct = _u(db, "ct"); ct.username = "ir"                                 # người duyệt trùng người tải
    with pytest.raises(SC.LoiSo, match="không tự duyệt"):
        SC.duyet(db, ct, lo.id)
    ct.username = "ct"
    SC.duyet(db, _u(db, "ct"), lo.id); db.commit()
    assert SC.lo_hien_hanh(db).id == lo.id


def test_noi_so_huu_va_lo_moi(db):
    from app.services import so_co_dong as SC
    from app.models.cong_co_dong import NoiSoCoDong
    tk, khac = _tk(db), _tk(db, giay_to="999", sdt="0902")
    assert SC.so_huu_cua(db, tk)["trang_thai"] == "chua_noi"
    lo = SC.gui_duyet(db, _u(db, "ir"), dt.date(2026, 10, 20), "ds.csv", T1); SC.duyet(db, _u(db, "ct"), lo.id); db.commit()
    ds = {d["tai_khoan_id"]: d for d in SC.ds_noi(db)["tai_khoan"]}
    assert ds[tk.id]["goi_y"]["so_cp"] == 13000 and ds[khac.id]["goi_y"] is None
    with pytest.raises(SC.LoiSo, match="không có trong danh sách"):
        SC.noi(db, _u(db, "ir"), khac.id, "999")
    with pytest.raises(SC.LoiSo) as ex:
        SC.noi(db, _u(db, "ct"), tk.id, "001088012345")
    assert ex.value.status == 403
    SC.noi(db, _u(db, "ir"), tk.id, "001.088.012345"); db.commit()
    r = SC.so_huu_cua(db, tk)
    assert r["trang_thai"] == "da_xac_minh" and r["so_cp"] == 13000 and r["ngay_can_cu"] == dt.date(2026, 10, 20)
    assert all(t.startswith("•") for t in r["tk_luu_ky"]) and "giay_to" not in r
    assert SC.so_huu_cua(db, khac)["trang_thai"] == "chua_noi"           # không thấy số người khác
    lo2 = SC.gui_duyet(db, _u(db, "ir"), dt.date(2026, 10, 27), "ds2.csv", T2); SC.duyet(db, _u(db, "ct"), lo2.id); db.commit()
    assert SC.so_huu_cua(db, tk)["trang_thai"] == "khong_co_ten"
    with pytest.raises(SC.LoiSo, match="lý do"):
        SC.go_noi(db, _u(db, "ir"), tk.id, "")
    SC.go_noi(db, _u(db, "ir"), tk.id, "Đã bán hết"); db.commit()
    assert db.execute(select(NoiSoCoDong)).scalars().one().go_luc is not None


def test_gui_xac_minh_tep_nhay_cam(db):
    from app.services import so_co_dong as SC
    from app.models.attachments import Attachment
    tk = _tk(db)
    with pytest.raises(SC.LoiSo, match="PDF"):
        SC.gui_xac_minh(db, tk, "Cập nhật tài khoản lưu ký", "a.docx", "", b"x")
    y = SC.gui_xac_minh(db, tk, "Cập nhật tài khoản lưu ký mới", "cccd.pdf", "application/pdf", b"%PDF-1.4 x"); db.commit()
    assert y.chu_de == "tu_cach" and y.attachment_id
    assert db.get(Attachment, y.attachment_id).nhay_cam is True
    with pytest.raises(SC.LoiSo) as ex:
        SC.gui_xac_minh(db, _tk(db, tt="cho_duyet", sdt="0903"), "Xin xác minh giúp", "", "", None)
    assert ex.value.status == 403


def test_uu_dai_co_dong_gui_yeu_cau_tour_nhu_khach(db):
    from app.services import cong_khach as K
    from app.models.crm import Lead
    tk = _tk(db, sdt="0901234567")
    yc = K.gui_yeu_cau(db, tk, "tour_doan", None, 4, "", dt.date.today() + dt.timedelta(days=30), "Gia đình 4 người", True)
    assert yc.id and "Cổng cổ đông" in db.get(Lead, yc.lead_id).note
    with pytest.raises(K.LoiKhach):
        K.gui_yeu_cau(db, _tk(db, tt="cho_duyet", sdt="0907"), "tour_doan", None, 2, "0907000000",
                      dt.date.today() + dt.timedelta(days=30), "", True)
    with pytest.raises(K.LoiKhach):
        K.don_cua_toi(db, tk)                                            # đơn / điểm vẫn chỉ của khách hàng
