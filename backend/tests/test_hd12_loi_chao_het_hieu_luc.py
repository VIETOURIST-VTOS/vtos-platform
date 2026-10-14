"""HD-12 — lời chào hết hiệu lực: ĐẾM ĐƯỢC trước, NHẢ LỊCH sau một công tắc.

Đo được trước vòng này, trên main 6105fe1: một lời chào quá hạn 30 ngày vẫn khoá hướng dẫn viên
ấy; chạy đúng cụm robot máy chủ chạy mỗi 10 phút rồi đo lại, vẫn khoá. Toàn hệ thống chỉ có một
cửa người bấm mới đóng được nó.

Chỗ hỏng về CẤU TRÚC thì sâu hơn một con số: câu hỏi "lời chào còn hiệu lực không" được trả lời ở
lớp API, còn lớp quyết định AI ĐANG CHIẾM LỊCH không biết câu hỏi ấy tồn tại.

  A. Phép hỏi nằm một chỗ, và nói đúng cả ở ca thiếu dữ liệu.
  B. Cửa đếm: không cắt bớt, và nói thẳng người trong danh sách CÒN bị khoá hay không.
  C. Công tắc TẮT giữ nguyên hành vi hôm nay — vòng này không đổi gì trên máy đang chạy.
  D. Công tắc BẬT thì nhả lịch, và nhả KHÔNG phải là từ chối.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd12.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd12.db"):
    os.remove("test_hd12.db")

from datetime import date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import hdv as HDV  # noqa: E402

client = TestClient(app)
MK = "Vtos@Demo#2026"
ID: dict[str, int] = {}
D = datetime(2026, 12, 10, 6, 0)          # khoảng cần người của mọi ca dưới đây


def login(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def cong_tac(bat: bool):
    """Gạt công tắc qua ĐÚNG bảng tham số mà đời thật gạt, không nhét cờ vào mã.

    Giá trị "1"/"0" chứ không phải chữ: `get_param` ép về float. Sổ Đợt HD-9 đã ghi một lần rằng
    điền nhầm kiểu vào đây là công tắc im lặng không bật.
    """
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import Param
    from app.services import rules as R
    with SessionLocal() as db:
        for p in db.execute(select(Param).where(Param.key == HDV.TU_DONG_NHA_LICH)).scalars():
            db.delete(p)
        db.add(Param(key=HDV.TU_DONG_NHA_LICH, value="1" if bat else "0",
                     label="Lời chào quá hạn thôi chiếm lịch",
                     effective_from=date(2026, 1, 1), status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
        db.commit()
    R.clear_param_cache()


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment

        db = SessionLocal()
        op = db.execute(select(User)).scalars().first().id

        def _nv(ma, ten):
            e = Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                         start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                         member_org=True, contract_type="ctv", ctv_contract=True)
            db.add(e); db.commit()
            return e.id

        t = Tour(code="H12-T1", name="Phú Quốc 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 12, 10), end_date=date(2026, 12, 14))
        db.add(t); db.commit()

        def _chao(gid, han, trang_thai="cho_xac_nhan"):
            a = GuideAssignment(tour_id=t.id, guide_id=gid, days=4, rate_per_day=800_000,
                                bat_dau=D, ket_thuc=D + timedelta(days=4),
                                status=trang_thai, han_tra_loi=han)
            db.add(a); db.commit()
            return a.id

        nay = datetime.now()
        # Mỗi người MỘT cảnh riêng: dùng chung một người thì một ca nhả lịch sẽ đổi kết quả ca kia.
        ID["ng_chet"] = _nv("H12A", "Lời chào chết")
        ID["chet"] = _chao(ID["ng_chet"], nay - timedelta(days=30))

        ID["ng_song"] = _nv("H12B", "Lời chào còn hạn")
        ID["song"] = _chao(ID["ng_song"], nay + timedelta(hours=12))

        ID["ng_khong_han"] = _nv("H12C", "Lời chào không có hạn")
        ID["khong_han"] = _chao(ID["ng_khong_han"], None)

        ID["ng_da_nhan"] = _nv("H12D", "Đã nhận, hạn đã qua")
        ID["da_nhan"] = _chao(ID["ng_da_nhan"], nay - timedelta(days=30), "da_xac_nhan")

        # Dữ liệu mẫu KHÔNG có tài khoản `tp_hd` — đã đo: `seed.py` dựng 14 tài khoản, không có
        # vai này. Phép thử tự dựng người của mình thay vì bám vào dữ liệu mẫu: cảnh dựng tay thì
        # đọc được, còn bám dữ liệu mẫu thì một ngày nào đó ai sửa `seed.py` là bộ này đỏ vì lý do
        # chẳng liên quan gì tới điều nó canh.
        from app.core.security import hash_password
        db.add(User(username="tp_hd", full_name="Thử TP Hướng dẫn", role="tp_hd",
                    department="Hướng dẫn", password_hash=hash_password(MK)))
        db.commit()

        db.close()
        yield


def _a(khoa):
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    with SessionLocal() as db:
        return db.get(GuideAssignment, ID[khoa])


# ───────────────────── A · phép hỏi nằm MỘT chỗ ─────────────────────

def test_a1_loi_chao_qua_han_thi_het_hieu_luc():
    assert HDV.loi_chao_het_hieu_luc(_a("chet")) is True


def test_a2_con_han_thi_con_hieu_luc():
    assert HDV.loi_chao_het_hieu_luc(_a("song")) is False


def test_a3_KHONG_CO_HAN_thi_KHONG_het_hieu_luc():
    """Thiếu mốc là chưa đủ dữ liệu để kết luận, không phải là một kết luận.

    Cùng một lẽ với `khong_so_duoc` ở ngay trên nó trong cùng tệp. Đoán bừa ở đây là nhả lịch của
    hàng trăm người đang thật sự bận, vì bản ghi cũ không có hạn trả lời.
    """
    assert _a("khong_han").han_tra_loi is None
    assert HDV.loi_chao_het_hieu_luc(_a("khong_han")) is False


def test_a4_da_nhan_roi_thi_han_tra_loi_khong_con_nghia():
    """Hạn trả lời đã qua ba mươi ngày, nhưng người ta ĐÃ NHẬN. Nhả lịch ở đây là huỷ một chuyến
    đã có người nhận – sai nghiêm trọng hơn hẳn việc giữ thừa một chỗ."""
    assert _a("da_nhan").status == "da_xac_nhan"
    assert HDV.loi_chao_het_hieu_luc(_a("da_nhan")) is False


def test_a5_lop_API_thoi_tu_tinh_lai_cau_hoi_nay():
    """Canh bằng cây cú pháp: hai chỗ cùng tính một câu hỏi là hai chỗ sẽ lệch nhau, và lệch lặng
    lẽ. Tìm chuỗi sẽ bắt trúng chính lời giải thích trong chú thích, nên duyệt cây."""
    import ast
    import inspect
    from pathlib import Path

    from app.api.v1 import huong_dan as HD
    cay = ast.parse(Path(inspect.getsourcefile(HD)).read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if not (isinstance(nut, ast.Compare) and isinstance(nut.left, ast.Call)):
            continue
        ten = getattr(nut.left.func, "attr", "") or getattr(nut.left.func, "id", "")
        if ten == "now":
            moc = [getattr(c, "attr", "") for c in ast.walk(nut) if isinstance(c, ast.Attribute)]
            assert "han_tra_loi" not in moc, \
                "huong_dan.py còn tự so `datetime.now()` với `han_tra_loi` thay vì hỏi hdv.py"


# ───────────────────── B · cửa đếm ─────────────────────

def test_b1_cua_dem_liet_ke_dung_loi_chao_chet():
    r = client.get("/api/v1/huong-dan/chao-chuyen/qua-han", headers=login("tp_hd"))
    assert r.status_code == 200, r.text
    d = r.json()
    ds = [x["id"] for x in d["rows"]]
    assert ID["chet"] in ds
    for k in ("song", "khong_han", "da_nhan"):
        assert ID[k] not in ds, f"{k} không được nằm trong danh sách hết hiệu lực"
    assert d["so_luong"] == len(d["rows"])


def test_b2_cua_dem_noi_ro_nguoi_do_CON_bi_khoa_lich_hay_khong():
    """Một danh sách không nói hậu quả thì người đọc tự suy, và suy phổ biến nhất là 'chắc máy lo
    rồi'. Công tắc đang tắt thì phải nói thẳng: những người này VẪN bị coi là bận."""
    cong_tac(False)
    d = client.get("/api/v1/huong-dan/chao-chuyen/qua-han", headers=login("tp_hd")).json()
    assert d["dang_nha_lich"] is False
    assert all(x["con_chiem_lich"] is True for x in d["rows"])
    assert "VẪN chiếm lịch" in d["ghi_chu"]


# ───────────────────── C · công tắc TẮT giữ nguyên hành vi hôm nay ─────────────────────

def test_c1_cong_tac_TAT_thi_loi_chao_chet_VAN_chiem_lich():
    """Vòng này KHÔNG được đổi hành vi trên hệ thống đang chạy. Đây là ca canh điều đó."""
    cong_tac(False)
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        trung = HDV.dang_chiem_lich(db, ID["ng_chet"], D, D + timedelta(days=4))
    assert [a.id for a in trung] == [ID["chet"]]


def test_c2_cong_tac_TAT_la_mac_dinh_khi_CHUA_AI_KHAI():
    """Xoá sạch dòng tham số — không ai khai gì cả — thì vẫn phải TẮT, lấy từ giá trị mặc định
    trong `rules.py`. Một công tắc mà trạng thái lúc chưa ai đụng tới là 'bật' thì nó không phải
    công tắc, nó là một thay đổi lén."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import Param
    from app.services import rules as R
    with SessionLocal() as db:
        for p in db.execute(select(Param).where(Param.key == HDV.TU_DONG_NHA_LICH)).scalars():
            db.delete(p)
        db.commit()
    R.clear_param_cache()
    with SessionLocal() as db:
        assert HDV.nha_lich_khi_het_hieu_luc(db) is False


def test_c3_gia_tri_so_KHONG_bi_doc_thanh_chuoi():
    """Ca này canh đúng cái bẫy đã làm hỏng bản đầu của vòng này.

    `get_param` ép giá trị về float, nên `"1"` đọc ra là `1.0`. Bản đầu viết
    `str(get_param(...)) in ("1", ...)` — và `"1.0"` không khớp, nên công tắc bật rồi mà hệ thống
    vẫn coi như tắt. Hỏng về phía im lặng là loại hỏng không ai phát hiện.
    """
    from app.db.session import SessionLocal
    cong_tac(True)
    try:
        with SessionLocal() as db:
            assert HDV.nha_lich_khi_het_hieu_luc(db) is True, \
                "công tắc đã bật trong bảng tham số nhưng hệ thống vẫn đọc ra TẮT"
    finally:
        cong_tac(False)


# ───────────────────── D · công tắc BẬT ─────────────────────

def test_d1_cong_tac_BAT_thi_loi_chao_chet_THOI_chiem_lich():
    cong_tac(True)
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            trung = HDV.dang_chiem_lich(db, ID["ng_chet"], D, D + timedelta(days=4))
        assert trung == [], f"vẫn còn chiếm: {[a.id for a in trung]}"
    finally:
        cong_tac(False)


def test_d2_bat_cong_tac_KHONG_dong_loi_chao_va_KHONG_doi_trang_thai():
    """Hết hiệu lực KHÔNG phải là từ chối — luật thứ nhất của `models/giu_cho.py` cho ghế ngồi,
    Chủ tịch chốt 11/9/2026, áp nguyên văn sang đây. `cho_xac_nhan` vẫn đúng sự thật: không ai
    trả lời cả. Máy không được tự xoá một lời mời đã gửi cho người thật."""
    cong_tac(True)
    try:
        from app.db.session import SessionLocal
        # PHẢI commit rồi đọc lại bằng MỘT PHIÊN KHÁC. Bản đầu của ca này gọi `dang_chiem_lich`
        # rồi đóng phiên mà không commit, nên một phép đột biến đặt `a.status = "het_han"` ngay
        # trong hàm ấy KHÔNG làm ca này đỏ — thay đổi chết theo phiên và ca kiểm không thấy gì.
        # Đời thật thì khác hẳn: `dang_chiem_lich` được gọi giữa một yêu cầu có commit ở cuối, nên
        # đúng cái hỏng ấy sẽ ghi thật xuống cơ sở dữ liệu. Ca kiểm phải nhìn thấy điều đó.
        with SessionLocal() as db:
            HDV.dang_chiem_lich(db, ID["ng_chet"], D, D + timedelta(days=4))
            db.commit()
        a = _a("chet")
        assert a.status == "cho_xac_nhan", \
            f"nhả lịch đã ĐỔI trạng thái thành {a.status!r} — hết hiệu lực không phải là từ chối"
        assert a.ly_do == ""
        assert a.tra_loi_luc is None
    finally:
        cong_tac(False)


def test_d3_bat_cong_tac_KHONG_dung_toi_loi_chao_con_han():
    cong_tac(True)
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            trung = HDV.dang_chiem_lich(db, ID["ng_song"], D, D + timedelta(days=4))
        assert [a.id for a in trung] == [ID["song"]]
    finally:
        cong_tac(False)


def test_d4_bat_cong_tac_KHONG_dung_toi_loi_chao_khong_co_han():
    cong_tac(True)
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            trung = HDV.dang_chiem_lich(db, ID["ng_khong_han"], D, D + timedelta(days=4))
        assert [a.id for a in trung] == [ID["khong_han"]], \
            "lời chào KHÔNG CÓ HẠN bị nhả lịch — đó là đoán, không phải kết luận"
    finally:
        cong_tac(False)


def test_d5_bat_cong_tac_KHONG_dung_toi_chuyen_DA_CO_NGUOI_NHAN():
    cong_tac(True)
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            trung = HDV.dang_chiem_lich(db, ID["ng_da_nhan"], D, D + timedelta(days=4))
        assert [a.id for a in trung] == [ID["da_nhan"]], \
            "nhả lịch một chuyến ĐÃ có người nhận — sai nặng hơn hẳn việc giữ thừa một chỗ"
    finally:
        cong_tac(False)
