"""CD-1 · Cổng Cổ đông đợt 1 (Chủ tịch duyệt bản xem thử 28/10/2026).

  1. Tài liệu lên cổng CHỈ từ bản ghi công bố ĐÃ công bố; chỉ IR – Pháp chế đưa; chỉ PDF.
  2. «Chỉ cổ đông» không lộ ra cửa công khai; gỡ thì biến khỏi cả hai phía, dòng còn, có lý do.
  3. Bản thay: bản cũ đổi trạng thái, cổng hiện lịch sử; gỡ bản mới thì bản cũ hiện lại.
  4. Chỉ cổ đông ĐÃ XÁC MINH vào cổng; khách hàng, đối tác, cổ đông chưa duyệt bị chặn.
  5. Sự kiện: nháp không ra cổng; quan tâm bật / bỏ không xoá dòng; đã hủy phải có lý do.
  6. IR: mã IR-xxxx, phanh số câu chờ; trả lời phải xác nhận «không chứa thông tin chưa công bố».
  7. Cửa API: phiên cổng ngoài và cửa VTOS tách nhau; cửa công khai có phanh.
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

PDF = b"%PDF-1.4\n% bao cao quy III\n%%EOF\n"


class _Kho:
    def __init__(self):
        self.d = {}

    def put(self, key, data, kieu=""):
        self.d[key] = data
        return type("L", (), {"key": key, "checksum": __import__("hashlib").sha256(data).hexdigest()})()

    def get(self, key):
        return self.d[key]


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.models.core import User
    from app.models.phap_che import BanGhiCongBo, NghiaVuCongBo
    from app.services import storage as ST
    ST._CACHE["s"] = _Kho()
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai in (("ct", "chutich"), ("tgd", "tgd"), ("ir", "ir_phapche"), ("bks", "bks"), ("kt", "ketoan")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x"))
    s.add(NghiaVuCongBo(id=1, ma="BCTC_QUY", ten="Báo cáo tài chính quý", can_cu="Thông tư 96/2020"))
    s.add(BanGhiCongBo(id=1, nghia_vu_id=1, ky="2026-Q3", da_cong_bo_luc=dt.datetime(2026, 10, 22, 16, 0), noi_cong_bo="HNX"))
    s.add(BanGhiCongBo(id=2, nghia_vu_id=1, ky="2026-Q4"))                                    # chưa công bố
    s.add(BanGhiCongBo(id=3, nghia_vu_id=1, ky="2026-Q3-dc", da_cong_bo_luc=dt.datetime(2026, 10, 25, 9, 0), noi_cong_bo="HNX"))
    s.commit()
    yield s
    s.close()
    ST._CACHE.clear()


def _u(s, ten):
    from app.models.core import User
    return s.execute(select(User).where(User.username == ten)).scalars().one()


def _tk(s, loai="co_dong", trang_thai="hoat_dong", sdt="0901234567"):
    from app.models.cong_ngoai import TaiKhoanNgoai
    tk = TaiKhoanNgoai(loai=loai, dien_thoai=sdt, trang_thai=trang_thai, ho_ten="Cổ đông A")
    s.add(tk); s.commit()
    return tk


def _dua(s, bg=1, pham_vi="cong_khai", ten="tai-lieu.pdf", **k):
    from app.services import cong_co_dong as S
    t = S.dua_len(s, _u(s, "ir"), bg, k.pop("tieu_de", "Báo cáo tài chính Quý III/2026"), "tai_chinh", pham_vi,
                  ten, "application/pdf", k.pop("data", PDF), **k)
    s.commit()
    return t


# ── 1 · CHỈ BẢN GHI ĐÃ CÔNG BỐ, CHỈ IR, CHỈ PDF ─────────────────────────────────────────────

def test_chi_ban_ghi_da_cong_bo_chi_ir_chi_pdf(db):
    from app.services import cong_co_dong as S
    with pytest.raises(S.LoiCoDong, match="CHƯA công bố"):
        _dua(db, bg=2)
    for ai in ("ct", "tgd", "bks", "kt"):
        with pytest.raises(S.LoiCoDong) as ex:
            S.dua_len(db, _u(db, ai), 1, "x", "tai_chinh", "cong_khai", "a.pdf", "application/pdf", PDF)
        assert ex.value.status == 403
    with pytest.raises(S.LoiCoDong, match="PDF"):
        _dua(db, ten="bao-cao.docx")
    t = _dua(db)
    assert t.trang_thai == "hien" and t.attachment_id
    with pytest.raises(S.LoiCoDong) as ex:          # một bản ghi công bố — một tài liệu trên cổng
        _dua(db)
    assert ex.value.status == 409
    data, a = S.tep_tai_lieu(db, t.id, False)
    assert data == PDF and a.doi_tuong == "van_ban"


# ── 2 · PHẠM VI VÀ GỠ ────────────────────────────────────────────────────────────────────────

def test_chi_co_dong_khong_lo_ra_cong_khai_va_go_co_ly_do(db):
    from app.models.cong_co_dong import TaiLieuCongCoDong
    from app.services import cong_co_dong as S
    rieng = _dua(db, pham_vi="co_dong")
    assert S.ds_tai_lieu(db, False) == []
    assert [d["id"] for d in S.ds_tai_lieu(db, True)] == [rieng.id]
    with pytest.raises(S.LoiCoDong) as ex:
        S.mot_tai_lieu(db, rieng.id, False)
    assert ex.value.status == 404
    with pytest.raises(S.LoiCoDong):
        S.tep_tai_lieu(db, rieng.id, False)
    with pytest.raises(S.LoiCoDong) as ex:
        S.go(db, _u(db, "bks"), rieng.id, "x")
    assert ex.value.status == 403
    with pytest.raises(S.LoiCoDong, match="lý do"):
        S.go(db, _u(db, "tgd"), rieng.id, "  ")
    S.go(db, _u(db, "tgd"), rieng.id, "Đăng nhầm phạm vi")
    db.commit()
    assert S.ds_tai_lieu(db, True) == []
    with pytest.raises(S.LoiCoDong):
        S.tep_tai_lieu(db, rieng.id, True)
    dong = db.get(TaiLieuCongCoDong, rieng.id)
    assert dong.trang_thai == "go" and dong.go_boi == "tgd"
    # gỡ rồi thì đưa lại được từ cùng bản ghi
    lai = _dua(db, pham_vi="cong_khai")
    assert [d["id"] for d in S.ds_tai_lieu(db, False)] == [lai.id]


# ── 3 · BẢN THAY ─────────────────────────────────────────────────────────────────────────────

def test_ban_thay_giu_lich_su_va_go_ban_moi_thi_ban_cu_hien_lai(db):
    from app.services import cong_co_dong as S
    cu = _dua(db)
    with pytest.raises(S.LoiCoDong, match="lý do"):
        _dua(db, bg=3, thay_cho_id=cu.id, ly_do_thay="")
    moi = _dua(db, bg=3, tieu_de="Báo cáo tài chính Quý III/2026 (đính chính)", data=PDF + b"v2",
               thay_cho_id=cu.id, ly_do_thay="Đính chính thuyết minh 5")
    assert db.get(type(cu), cu.id).trang_thai == "thay_the"
    assert [d["id"] for d in S.ds_tai_lieu(db, True)] == [moi.id]
    d = S.mot_tai_lieu(db, moi.id, False)
    assert d["lich_su"][0]["id"] == cu.id and d["lich_su"][0]["ly_do_thay_boi_ban_sau"] == "Đính chính thuyết minh 5"
    assert S.mot_tai_lieu(db, cu.id, False)["ban_moi_id"] == moi.id      # bản cũ vẫn đọc được, trỏ tới bản mới
    S.go(db, _u(db, "ct"), moi.id, "Đính chính sai")
    db.commit()
    assert [d["id"] for d in S.ds_tai_lieu(db, True)] == [cu.id]


# ── 4 · AI VÀO ĐƯỢC CỔNG ─────────────────────────────────────────────────────────────────────

def test_chi_co_dong_da_xac_minh(db):
    from app.services import cong_co_dong as S
    assert S.tong_quan(db, _tk(db))["ir_cho"] == 0
    for loai, tt in (("khach_hang", "hoat_dong"), ("doi_tac", "hoat_dong"), ("co_dong", "cho_duyet"), ("co_dong", "khoa")):
        with pytest.raises(S.LoiCoDong) as ex:
            S.tong_quan(db, _tk(db, loai, tt, sdt=f"09{len(loai)}{len(tt)}000000"))
        assert ex.value.status == 403


# ── 5 · SỰ KIỆN ──────────────────────────────────────────────────────────────────────────────

def test_su_kien_nhap_khong_ra_cong_quan_tam_va_huy(db):
    from app.models.cong_co_dong import QuanTamSuKien
    from app.services import cong_co_dong as S
    tk = _tk(db)
    tl = _dua(db)
    sau = dt.datetime.now() + dt.timedelta(days=20)
    with pytest.raises(S.LoiCoDong) as ex:
        S.tao_su_kien(db, _u(db, "ct"), {"ten": "Gặp gỡ", "loai": "gap_go", "bat_dau": sau})
    assert ex.value.status == 403
    with pytest.raises(S.LoiCoDong, match="không đang hiện"):
        S.tao_su_kien(db, _u(db, "ir"), {"ten": "Gặp gỡ", "loai": "gap_go", "bat_dau": sau, "tai_lieu_ids": [999]})
    s = S.tao_su_kien(db, _u(db, "ir"), {"ten": "Gặp gỡ cổ đông cuối năm", "loai": "gap_go", "bat_dau": sau,
                                         "dia_diem": "Hà Nội", "tai_lieu_ids": [tl.id]})
    db.commit()
    assert S.ds_su_kien_cong(db, tk) == []
    with pytest.raises(S.LoiCoDong):
        S.quan_tam(db, tk, s.id, True)
    S.doi_trang_thai_su_kien(db, _u(db, "ir"), s.id, "cong_bo")
    db.commit()
    ds = S.ds_su_kien_cong(db, tk)
    assert ds[0]["tai_lieu"] == [{"id": tl.id, "tieu_de": tl.tieu_de}] and ds[0]["toi_quan_tam"] is False
    assert S.quan_tam(db, tk, s.id, True)["toi_quan_tam"] is True
    assert S.quan_tam(db, tk, s.id, True)["toi_quan_tam"] is True        # bấm hai lần không sinh hai dòng
    assert S.quan_tam(db, tk, s.id, False)["toi_quan_tam"] is False
    db.commit()
    rows = list(db.execute(select(QuanTamSuKien)).scalars())
    assert len(rows) == 1 and rows[0].bo_luc is not None                  # bỏ quan tâm không xoá dòng
    assert S.ds_quan_tam(db, s.id)[0]["bo_luc"] is not None
    with pytest.raises(S.LoiCoDong, match="lý do"):
        S.doi_trang_thai_su_kien(db, _u(db, "ir"), s.id, "huy")
    S.doi_trang_thai_su_kien(db, _u(db, "ir"), s.id, "huy", "Đổi lịch sang quý I")
    db.commit()
    d = S.ds_su_kien_cong(db, tk)[0]
    assert d["trang_thai"] == "huy" and d["ly_do_huy"] == "Đổi lịch sang quý I"
    with pytest.raises(S.LoiCoDong):
        S.quan_tam(db, tk, s.id, True)
    # sự kiện đã qua không nhận quan tâm
    qua = S.tao_su_kien(db, _u(db, "ir"), {"ten": "Đã qua", "loai": "khac", "bat_dau": dt.datetime.now() - dt.timedelta(days=1)})
    S.doi_trang_thai_su_kien(db, _u(db, "ir"), qua.id, "cong_bo")
    with pytest.raises(S.LoiCoDong, match="đã diễn ra"):
        S.quan_tam(db, tk, qua.id, True)


# ── 6 · YÊU CẦU IR ───────────────────────────────────────────────────────────────────────────

def test_ir_ma_phanh_va_xac_nhan_khi_tra_loi(db):
    from app.services import cong_co_dong as S
    tk, khac = _tk(db), _tk(db, sdt="0907654321")
    y = S.gui_ir(db, tk, "quyen_loi", "Cho tôi hỏi lịch chi trả cổ tức năm 2026?")
    db.commit()
    assert y.ma == "IR-0001"
    with pytest.raises(S.LoiCoDong):
        S.gui_ir(db, tk, "khong_co", "Câu hỏi hợp lệ")
    with pytest.raises(S.LoiCoDong):
        S.gui_ir(db, tk, "khac", "ab")
    for i in range(4):
        S.gui_ir(db, tk, "khac", f"Câu hỏi số {i}")
    with pytest.raises(S.LoiCoDong) as ex:
        S.gui_ir(db, tk, "khac", "Câu thứ sáu")
    assert ex.value.status == 429
    assert S.ir_cua_toi(db, khac) == []                                   # không thấy câu của người khác
    with pytest.raises(S.LoiCoDong, match="xác nhận"):
        S.tra_loi_ir(db, _u(db, "ir"), y.id, "Theo nghị quyết ĐHĐCĐ.", False)
    with pytest.raises(S.LoiCoDong) as ex:
        S.tra_loi_ir(db, _u(db, "ct"), y.id, "Theo nghị quyết ĐHĐCĐ.", True)
    assert ex.value.status == 403
    S.tra_loi_ir(db, _u(db, "ir"), y.id, "Theo nghị quyết ĐHĐCĐ và thông báo chính thức.", True)
    db.commit()
    with pytest.raises(S.LoiCoDong) as ex:
        S.tra_loi_ir(db, _u(db, "ir"), y.id, "Trả lời lần hai", True)
    assert ex.value.status == 409
    toi = {d["ma"]: d for d in S.ir_cua_toi(db, tk)}
    assert toi["IR-0001"]["trang_thai"] == "da_tra_loi" and "tra_loi_boi" not in toi["IR-0001"]
    with pytest.raises(S.LoiCoDong, match="lý do"):
        S.dong_ir(db, _u(db, "ir"), 2, "")
    S.dong_ir(db, _u(db, "ir"), 2, "Trùng câu IR-0001")
    db.commit()
    assert S.gui_ir(db, tk, "khac", "Giờ gửi tiếp được").ma == "IR-0006"      # câu thứ sáu bị chặn không chiếm mã


# ── 7 · CỬA API ──────────────────────────────────────────────────────────────────────────────

def test_cua_api_tach_phia_va_cong_khai_co_phanh():
    import inspect

    from app.api.v1 import cong_co_dong as A
    from app.api.v1.cong_ngoai import tai_khoan_ngoai
    from app.main import app
    duong = {r.path: r for r in app.routes if getattr(r, "path", "").startswith(("/api/v1/cong/co-dong", "/api/v1/cong/ir-cong-khai", "/api/v1/ir-cong-co-dong"))}
    assert len([p for p in duong if p.startswith("/api/v1/cong/co-dong")]) >= 6
    for p, r in duong.items():
        nguon = inspect.getsource(r.endpoint)
        if p.startswith("/api/v1/cong/co-dong"):
            assert "_co_dong" in nguon and "require_roles" not in nguon, p
        elif p.startswith("/api/v1/cong/ir-cong-khai"):
            assert "_phanh(request)" in nguon and "require_roles" not in nguon and "_co_dong" not in nguon, p
        else:
            assert "require_roles" in nguon and "_co_dong" not in nguon, p
    assert A.TOI_DA_TRONG_CUA_SO <= 60
    assert inspect.getsource(A._co_dong).count("tai_khoan_ngoai") == 1 and tai_khoan_ngoai.la_cong_chan_quyen
