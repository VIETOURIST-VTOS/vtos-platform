"""V12 – khế ước vay nối vào sổ, và mã đáo hạn nối hai chân một lần đảo nợ.

Nghiệm thu V12: "nhập một khế ước thật, chạy hết một chu kỳ gồm một lần đáo hạn: dư nợ vay trên sổ
khớp lịch trả nợ, và không có ngoại lệ đáo hạn thiếu chân."

Bộ này canh cả những điều Chủ tịch đã QUYẾT, vì chúng dễ bị người sau "sửa cho hợp lý":
  · lãi vay ghi KHI TRẢ, không trích trước (quyết định 08/9 mục 5)
  · gốc và lãi là HAI bút toán, không bù trừ
  · cặp tài khoản lấy từ BẢNG QUY ƯỚC, không dựng tay trong mã

Và có một phép thử ngược quan trọng: ghi sổ HỎNG thì kỳ KHÔNG được đánh dấu đã thực hiện. Bản trước
V12 bắt lỗi rồi vẫn đánh dấu – đó chính là cách "dư nợ trên sổ" và "lịch trả nợ" thành hai con số
sống riêng, và một phép thử không canh điều đó thì mọi phép thử khác vẫn xanh trong lúc sổ sai.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v12.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

client = TestClient(app)
HOM_NAY = date.today()


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str = "ketoan") -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        assert u is not None, f"dữ liệu mẫu không có vai trò {vai}"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _khe_uoc(so_tien=1_000_000_000, ten="Ngân hàng thử V12"):
    from app.db.session import SessionLocal
    from app.models.finance import FinContract
    with SessionLocal() as db:
        n = db.execute(select(FinContract)).scalars().all()
        c = FinContract(code=f"V12-{len(n) + 1:04d}", kind="vay", partner=ten,
                        principal=so_tien, outstanding=0, interest_rate=10.0,
                        signed_on=HOM_NAY, status="hieu_luc")
        db.add(c); db.commit()
        return c.id


def _ky(cid, kind, so_tien, ngay=None, ky=None, ma_dao_han=""):
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    with SessionLocal() as db:
        s = FinSchedule(contract_id=cid, kind=kind, amount=so_tien,
                        due_date=ngay or HOM_NAY, ky=ky, ma_dao_han=ma_dao_han)
        db.add(s); db.commit()
        return s.id


def _settle(sid, ngay=None):
    return client.post(f"/api/v1/fin/schedule/{sid}/settle", headers=login(),
                       json={"done_on": (ngay or HOM_NAY).isoformat(), "bank_ref": "GD-V12"})


# ====================== 1. CẶP TÀI KHOẢN LẤY TỪ BẢNG QUY ƯỚC ======================
def test_cap_tai_khoan_lay_tu_BANG_QUY_UOC_chu_khong_dung_tay():
    """Dựng tay trong mã thì bảng quy ước thành bản trang trí: kế toán sửa một chỗ, mã chạy chỗ kia,
    và không ai biết cho tới lúc đối chiếu."""
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    from app.models.hach_toan import QuyTacHachToan
    from app.services import vay_but_toan as VBT
    cid = _khe_uoc(); sid = _ky(cid, "nhan_vay", 500_000_000)
    with SessionLocal() as db:
        q = db.execute(select(QuyTacHachToan).where(QuyTacHachToan.ma == "VAY_NHAN",
                                                    QuyTacHachToan.status == "active")).scalars().first()
        assert q is not None, "bảng quy ước chưa nạp VAY_NHAN"
        xt = VBT.xem_truoc(db, db.get(FinSchedule, sid))
    assert xt["quy_uoc"] == "VAY_NHAN"
    assert xt["dong"][0]["account"] == q.tk_no and xt["dong"][1]["account"] == q.tk_co
    # và đúng cặp 1121/3411 chứ không phải 112/341 như bản dựng tay cũ
    assert {xt["dong"][0]["account"], xt["dong"][1]["account"]} == {"1121", "3411"}


def test_thieu_quy_uoc_thi_DUNG_chu_khong_tu_dung_lay():
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    from app.services import vay_but_toan as VBT
    cid = _khe_uoc(); sid = _ky(cid, "nhan_vay", 1_000_000)
    with SessionLocal() as db:
        s = db.get(FinSchedule, sid)
        with pytest.raises(VBT.CongVay) as ex:
            VBT._quy_uoc(db, "QUY_UOC_KHONG_CO_THAT")
        assert ex.value.detail["gate"] == "THIEU_QUY_UOC"


# ====================== 2. GỐC VÀ LÃI LÀ HAI BÚT TOÁN ======================
def test_goc_va_lai_la_HAI_but_toan_khong_bu_tru():
    """Bù trừ thành một dòng thì dư nợ vay trên sổ không bao giờ đứng ở đỉnh và dòng tiền mất một vòng."""
    cid = _khe_uoc()
    g = _ky(cid, "tra_goc", 100_000_000, ky=1)
    l = _ky(cid, "tra_lai", 8_000_000, ky=1)
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    from app.services import vay_but_toan as VBT
    with SessionLocal() as db:
        xg = VBT.xem_truoc(db, db.get(FinSchedule, g))
        xl = VBT.xem_truoc(db, db.get(FinSchedule, l))
    assert xg["quy_uoc"] == "VAY_TRA_GOC" and xl["quy_uoc"] == "VAY_LAI"
    assert {d["account"] for d in xg["dong"]} == {"3411", "1121"}
    assert "635" in {d["account"] for d in xl["dong"]}, "lãi vay phải vào 635, không gộp vào gốc"
    assert xg["so_tien"] != xl["so_tien"]


def test_KHONG_co_ham_trich_truoc_lai_vay():
    """Chủ tịch quyết 08/9: lãi vay ghi KHI TRẢ, không trích trước theo kỳ. Phép thử này canh để
    người sau không lặng lẽ thêm vào – hệ quả (lãi lỗ theo tháng không so được giữa các tháng) là
    điều đã được chấp nhận có ý thức, không phải một thiếu sót cần vá."""
    import inspect
    from app.services import vay_but_toan as VBT
    ma = inspect.getsource(VBT)
    for tu in ("trich_truoc", "du_thu_lai", "lai_du_tra"):
        assert tu not in ma, f"đã có '{tu}' – phải hỏi lại Chủ tịch trước khi thêm"


# ====================== 3. PHÉP THỬ NGƯỢC: GHI SỔ HỎNG THÌ KHÔNG ĐÁNH DẤU ======================
def test_ghi_so_HONG_thi_ky_KHONG_duoc_danh_dau_da_thuc_hien():
    """Phép thử quan trọng nhất của tệp này.

    Bản trước V12 bắt ValueError rồi VẪN đánh dấu đã thực hiện. Kỳ xong mà sổ không có bút toán –
    đúng cách hai con số thành hai con số sống riêng, và không có gì đỏ."""
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    from app.models.accounting import PeriodLock
    cid = _khe_uoc(); sid = _ky(cid, "tra_goc", 50_000_000, ky=1)
    ky_khoa = HOM_NAY.strftime("%Y-%m")
    with SessionLocal() as db:
        if db.get(PeriodLock, ky_khoa) is None:
            db.add(PeriodLock(period=ky_khoa, locked_by="thu_v12")); db.commit()
    try:
        r = _settle(sid)
        assert r.status_code != 200, "ghi sổ vào kỳ đã khóa mà vẫn báo thành công"
        with SessionLocal() as db:
            s = db.get(FinSchedule, sid)
            assert s.status != "da_thuc_hien", "ghi sổ hỏng mà kỳ vẫn được đánh dấu đã thực hiện"
            assert s.entry_id is None
    finally:
        with SessionLocal() as db:
            k = db.get(PeriodLock, ky_khoa)
            if k is not None: db.delete(k); db.commit()


def test_ghi_hai_lan_mot_ky_bi_chan():
    """Ghi lại là trừ dư nợ hai lần – sai ở đúng chỗ kiểm toán mở ra đầu tiên."""
    cid = _khe_uoc(); sid = _ky(cid, "nhan_vay", 200_000_000)
    assert _settle(sid).status_code == 200
    r2 = _settle(sid)
    assert r2.status_code == 422


# ====================== 4. MÃ ĐÁO HẠN – HAI CHÂN ======================
def test_dao_han_hai_chan_mang_cung_source_ref_de_cong_nhin_thay():
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    from app.models.accounting import JournalEntry
    from app.services import vay_but_toan as VBT
    cu = _khe_uoc(ten="NH đảo nợ – khoản cũ"); moi = _khe_uoc(ten="NH đảo nợ – khoản mới")
    _settle(_ky(cu, "nhan_vay", 300_000_000))          # có dư nợ để mà trả
    g = _ky(cu, "tra_goc", 300_000_000, ky=1)
    n = _ky(moi, "nhan_vay", 300_000_000)
    r = client.post("/api/v1/fin/dao-han", headers=login(),
                    json={"tra_goc_id": g, "nhan_moi_id": n, "ma": "DH-V12-001"})
    assert r.status_code == 200, r.text
    assert _settle(g).status_code == 200 and _settle(n).status_code == 200
    with SessionLocal() as db:
        ids = [db.get(FinSchedule, x).entry_id for x in (g, n)]
        refs = {db.get(JournalEntry, i).source_ref for i in ids}
    assert refs == {"dao_han:DH-V12-001"}, refs


def test_cong_dao_han_KHONG_bao_thieu_chan_khi_du_hai_chan():
    """Nghiệm thu V12 nói 'không có ngoại lệ đáo hạn thiếu chân'."""
    from app.db.session import SessionLocal
    from app.services import cong_chan as CC
    with SessionLocal() as db:
        thieu = [x for x in CC.dao_han_thieu_chan(db) if "DH-V12-001" in x.get("doi_tuong", "")]
    assert not thieu, thieu


def test_dat_ma_dao_han_SAU_khi_ghi_so_bi_tu_choi():
    """Bút toán đã ghi mang source_ref cũ; đặt mã sau đó thì cổng không bao giờ nhìn thấy cặp này –
    tức là đặt xong mà vẫn thiếu chân, và người đặt tưởng mình đã xong."""
    cu = _khe_uoc(); moi = _khe_uoc()
    _settle(_ky(cu, "nhan_vay", 100_000_000))
    g = _ky(cu, "tra_goc", 100_000_000); n = _ky(moi, "nhan_vay", 100_000_000)
    assert _settle(g).status_code == 200
    r = client.post("/api/v1/fin/dao-han", headers=login(),
                    json={"tra_goc_id": g, "nhan_moi_id": n, "ma": "DH-MUON"})
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "DA_GHI_SO"


def test_ma_dao_han_mot_chan_bi_bao_tren_LICH_truoc_khi_ghi_so():
    """Soi SỔ chỉ thấy sau khi đã ghi; soi LỊCH thấy trước, tức còn kịp sửa mà không phải điều chỉnh."""
    from app.db.session import SessionLocal
    from app.services import vay_but_toan as VBT
    cid = _khe_uoc()
    _ky(cid, "tra_goc", 10_000_000, ma_dao_han="DH-MOT-CHAN")
    with SessionLocal() as db:
        ds = VBT.dao_han_thieu_chan_tren_lich(db)
    assert any(x["ma_dao_han"] == "DH-MOT-CHAN" for x in ds), ds


def test_hai_chan_cung_loai_cung_bi_bao():
    from app.db.session import SessionLocal
    from app.services import vay_but_toan as VBT
    cid = _khe_uoc()
    _ky(cid, "tra_goc", 1_000_000, ma_dao_han="DH-CUNG-LOAI")
    _ky(cid, "tra_goc", 1_000_000, ma_dao_han="DH-CUNG-LOAI")
    with SessionLocal() as db:
        ds = {x["ma_dao_han"]: x for x in VBT.dao_han_thieu_chan_tren_lich(db)}
    assert "DH-CUNG-LOAI" in ds and "cùng loại" in ds["DH-CUNG-LOAI"]["vi_sao"]


def test_chan_sai_loai_bi_tu_choi():
    cid = _khe_uoc()
    a = _ky(cid, "tra_lai", 1_000_000); b = _ky(cid, "nhan_vay", 1_000_000)
    r = client.post("/api/v1/fin/dao-han", headers=login(),
                    json={"tra_goc_id": a, "nhan_moi_id": b, "ma": "DH-SAI"})
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "CHAN_SAI"


def test_ma_dao_han_rong_bi_tu_choi():
    cid = _khe_uoc()
    a = _ky(cid, "tra_goc", 1_000_000); b = _ky(cid, "nhan_vay", 1_000_000)
    assert client.post("/api/v1/fin/dao-han", headers=login(),
                       json={"tra_goc_id": a, "nhan_moi_id": b, "ma": "   "}).status_code == 422


# ====================== 5. ĐỐI CHIẾU SỔ ↔ LỊCH ======================
def test_doi_chieu_KHOP_sau_mot_chu_ky_day_du():
    """Câu nghiệm thu chính: dư nợ vay trên sổ khớp lịch trả nợ."""
    r = client.get("/api/v1/fin/doi-chieu-vay", headers=login())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["khop"] is True, d["ket_luan"]
    assert not d["ky_da_thuc_hien_ma_chua_ghi_so"], d["ky_da_thuc_hien_ma_chua_ghi_so"]


def test_bo_doi_chieu_PHAT_HIEN_duoc_khi_lech():
    """Một bộ đối chiếu luôn nói 'khớp' cũng làm phép thử trên xanh. Dựng một kỳ đánh dấu thực hiện
    mà không ghi sổ – đúng tình huống bản trước V12 tạo ra – và đòi nó kêu lên."""
    from app.db.session import SessionLocal
    from app.models.finance import FinSchedule
    from app.services import vay_but_toan as VBT
    cid = _khe_uoc()
    sid = _ky(cid, "nhan_vay", 777_000_000)
    with SessionLocal() as db:
        s = db.get(FinSchedule, sid); s.status = "da_thuc_hien"; db.commit()
        d = VBT.doi_chieu(db)
    assert d["khop"] is False
    assert abs(d["lech"] + 777_000_000) < 1 or abs(d["lech"] - 777_000_000) < 1, d["lech"]
    assert any(k["id"] == sid for k in d["ky_da_thuc_hien_ma_chua_ghi_so"])
    assert "LỆCH" in d["ket_luan"]
    with SessionLocal() as db:                       # trả lại để phép thử sau không lệch
        s = db.get(FinSchedule, sid); s.status = "ke_hoach"; db.commit()


def test_du_no_theo_lich_chi_tinh_ky_DA_THUC_HIEN():
    """Tính cả kỳ kế hoạch thì con số nói về tương lai, còn sổ nói về quá khứ – hai thứ không so được,
    và một phép so sai còn tệ hơn không so."""
    from app.db.session import SessionLocal
    from app.services import vay_but_toan as VBT
    cid = _khe_uoc()
    with SessionLocal() as db:
        truoc = VBT.du_no_theo_lich(db)
    _ky(cid, "nhan_vay", 999_000_000)               # để nguyên trạng thái kế hoạch
    with SessionLocal() as db:
        assert VBT.du_no_theo_lich(db) == truoc
