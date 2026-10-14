"""HD-11 — hai nhánh IM LẶNG trong lớp giữ lịch hướng dẫn viên.

Chủ tịch nêu 13/10/2026 khi duyệt phương án: *"Dịch vụ hiện đã có kiểm trùng và khóa, nhưng còn
nhánh bỏ qua lỗi khóa; cần rà soát trước khi dùng cho giao dịch bên ngoài."*

MỘT · `khoa_hdv` nuốt MỌI lỗi. Bản trước viết `except Exception: pass`, chú thích nói nhánh ấy dành
cho SQLite (không có khoá hàng). Chú thích đúng ý nhưng câu lệnh rộng hơn ý: `Exception` nuốt luôn
LOCK TIMEOUT, DEADLOCK và SERIALIZATION FAILURE trên PostgreSQL — đúng ba thứ mà khoá hàng sinh ra
để báo. Khi một trong ba xảy ra, lớp 1 coi như không tồn tại và hệ thống dựa hết vào lớp 2 mà không
ai biết. Nay hỏi thẳng `dialect.name`: bỏ qua đúng máy chủ không có khoá hàng, còn lỗi thật thì BAY
LÊN.

HAI · `canh_trung_sau_khi_ghi` trả về ÊM khi thiếu mốc giờ. Mọi nơi gọi đều đã tự hỏi
`khong_so_duoc` trước, nên tới được đó mà thiếu mốc là lỗi của người viết mã — và một hàm canh
trùng lặng lẽ không canh gì trông y hệt một hàm canh xong không thấy gì. Nay ném `ValueError`.

MỘT ĐIỀU EM ĐÃ NÓI QUÁ, SỬA LẠI Ở ĐÂY. Trong báo cáo rà soát sáng 13/10 em viết rằng ghép hai nhánh
im lặng ấy lại thì *"một phân công không có giờ đi qua cả hai lớp mà không một dòng nào nói chưa đủ
dữ liệu kiểm lịch"*. KHÔNG ĐÚNG. Cửa `/guide-assignments/yeu-cau/thieu` đã liệt kê đúng những phân
công ấy kèm nguyên văn *"Phân công chưa có giờ thì KHÔNG kiểm được trùng lịch – đây là việc còn
thiếu, không phải đã kiểm và không trùng"*, và hai cửa ghi giờ cũng trả lời như vậy. Nhóm C dưới đây
canh chính điều em từng phủ nhận, để lần sau không ai (kể cả em) nói lại câu sai ấy.

  A. `khoa_hdv`: bỏ qua đúng máy chủ không có khoá hàng; lỗi khoá thật thì ném.
  B. `canh_trung_sau_khi_ghi`: thiếu mốc giờ thì KÊU, và mọi nơi gọi đều đã chặn trước nên người
     dùng không bao giờ gặp tiếng kêu ấy.
  C. Hệ thống ĐÃ nói "chưa đủ dữ liệu kiểm lịch" — giữ cho nó tiếp tục nói.
  D. Chứng minh các ca trên CẮN.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd11.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd11.db"):
    os.remove("test_hd11.db")

import ast
import inspect
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import hdv as HDV

client = TestClient(app)
MK = "Vtos@Demo#2026"
ID: dict[str, int] = {}
D = datetime(2026, 11, 20, 6, 0)


def login(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


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
        e = Employee(code="HB001", full_name="Trần Văn A", department="huong_dan", position="hdv",
                     start_date=date(2024, 1, 1), card_no="HB001",
                     card_expiry=date(2030, 1, 1), member_org=True,
                     contract_type="ctv", ctv_contract=True)
        t = Tour(code="HB-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([e, t])
        db.commit()
        # Một phân công CÓ giờ và một phân công THIẾU giờ — thiếu giờ là ca của nhóm B và C.
        co = GuideAssignment(tour_id=t.id, guide_id=e.id, days=4, rate_per_day=800_000,
                             bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
        thieu = GuideAssignment(tour_id=t.id, guide_id=e.id, days=4, rate_per_day=800_000,
                                status="da_xac_nhan")
        db.add_all([co, thieu])
        db.commit()
        ID["co_gio"], ID["thieu_gio"], ID["hdv"] = co.id, thieu.id, e.id
        db.close()
        yield


# ───────────────────────── A · khoa_hdv ─────────────────────────

class _PhienGia:
    """Phiên giả: nói mình chạy trên máy chủ nào, và `execute` làm gì."""

    def __init__(self, ten_dialect, loi=None):
        self._ten, self._loi, self.da_goi = ten_dialect, loi, 0

    def get_bind(self):
        class _B:
            class dialect:
                name = self._ten
        _B.dialect.name = self._ten
        return _B()

    def execute(self, *a, **k):
        self.da_goi += 1
        if self._loi:
            raise self._loi
        return None


def test_a1_may_chu_khong_co_khoa_hang_thi_BO_QUA_va_khong_goi_cau_lenh():
    """SQLite không có khoá hàng. Bỏ qua là đúng — nhưng phải bỏ qua vì BIẾT, không vì bắt được lỗi."""
    p = _PhienGia("sqlite", loi=RuntimeError("đáng lẽ không được gọi"))
    HDV.khoa_hdv(p, 1)
    assert p.da_goi == 0, "đã gọi câu khoá hàng trên máy chủ không có khoá hàng"


def test_a2_may_chu_CO_khoa_hang_thi_loi_khoa_PHAI_BAY_LEN():
    """Ca trung tâm của vòng này. Lock timeout / deadlock / serialization failure là tin phải báo;
    nuốt rồi thì người xếp lịch tưởng đã giữ chỗ trong khi chưa giữ được gì."""
    class LoiKhoa(Exception):
        pass

    p = _PhienGia("postgresql", loi=LoiKhoa("canh_bao: lock timeout"))
    with pytest.raises(LoiKhoa):
        HDV.khoa_hdv(p, 1)
    assert p.da_goi == 1


def test_a3_may_chu_CO_khoa_hang_va_khong_loi_thi_chay_binh_thuong():
    p = _PhienGia("postgresql")
    HDV.khoa_hdv(p, 1)
    assert p.da_goi == 1


def _than(ten_ham: str) -> ast.FunctionDef:
    cay = ast.parse(Path(inspect.getsourcefile(HDV)).read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if isinstance(nut, ast.FunctionDef) and nut.name == ten_ham:
            return nut
    raise AssertionError(f"không tìm thấy hàm {ten_ham}")


GOI_DUOC_BOC = ("get_bind",)


def test_a4_khoa_hdv_khong_con_bat_Exception_tran_quanh_viec_khoa():
    """Canh bằng cây cú pháp, không tìm chuỗi: khối chú thích ngay trên hàm có chép lại nguyên văn
    câu lệnh cũ để người sau hiểu, nên tìm chuỗi sẽ bắt trúng chính lời giải thích.

    Soi THÂN của khối `try`, không soi thân của `except`. Bản cũ bắt `Exception` với thân `pass` —
    không có lời gọi nào TRONG `except`, nên soi nhầm chỗ thì ca này không phân biệt được hai bản.
    Cái cần canh là: có việc gì đang được bọc trong một `except Exception` trần. Chỉ cho phép đúng
    một việc — đọc tên phương ngữ (`get_bind`) — vì đó không phải việc khoá; mọi lời gọi khác,
    `db.execute` trước hết, phải nằm ngoài vùng nuốt lỗi.
    """
    for nut in ast.walk(_than("khoa_hdv")):
        if not isinstance(nut, ast.Try):
            continue
        tran = any((getattr(h.type, "id", "") if h.type is not None else "")
                   in ("Exception", "BaseException", "") for h in nut.handlers)
        if not tran:
            continue
        for than in nut.body:
            for n in ast.walk(than):
                if isinstance(n, ast.Call):
                    ten = getattr(n.func, "attr", None) or getattr(n.func, "id", "?")
                    assert ten in GOI_DUOC_BOC, \
                        f"khoa_hdv bọc lời gọi «{ten}» trong một `except Exception` trần — lỗi khoá " \
                        "hàng sẽ bị nuốt"


# ───────────────────────── B · canh_trung_sau_khi_ghi ─────────────────────────

def test_b1_thieu_moc_gio_thi_KEU_chu_khong_tra_ve_em():
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment
    with SessionLocal() as db:
        a = db.get(GuideAssignment, ID["thieu_gio"])
        with pytest.raises(ValueError) as ex:
            HDV.canh_trung_sau_khi_ghi(db, a)
        assert "chưa đủ dữ liệu kiểm lịch" in str(ex.value)


def test_b2_moi_noi_goi_deu_da_chan_truoc_nen_nguoi_dung_khong_gap_tieng_keu():
    """Tiếng kêu ở B1 là dành cho NGƯỜI VIẾT MÃ. Nếu có một chỗ gọi mà quên hỏi `khong_so_duoc`
    trước thì tiếng kêu ấy rơi xuống đầu Điều hành dưới dạng lỗi 500 — nên phải canh bằng cấu trúc,
    không bằng niềm tin."""
    from app.api.v1 import hr as HR
    cay = ast.parse(Path(inspect.getsourcefile(HR)).read_text(encoding="utf-8"))

    def _la_canh_trung(n):
        return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "canh_trung_sau_khi_ghi")

    def _la_chan(n):
        """`if not HDV.khong_so_duoc(...)`"""
        return (isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
                and isinstance(n.test.op, ast.Not) and isinstance(n.test.operand, ast.Call)
                and isinstance(n.test.operand.func, ast.Attribute)
                and n.test.operand.func.attr == "khong_so_duoc")

    tat_ca = {id(n) for n in ast.walk(cay) if _la_canh_trung(n)}
    assert tat_ca, "không tìm thấy lời gọi canh_trung_sau_khi_ghi nào trong hr.py"
    duoc_chan = set()
    for nut in ast.walk(cay):
        if _la_chan(nut):
            for con in nut.body:
                duoc_chan |= {id(n) for n in ast.walk(con) if _la_canh_trung(n)}
    assert tat_ca == duoc_chan, \
        f"{len(tat_ca - duoc_chan)} lời gọi canh_trung_sau_khi_ghi KHÔNG nằm trong nhánh đã hỏi " \
        "`khong_so_duoc` trước"


# ───────────────────────── C · hệ thống ĐÃ nói ra, giữ cho nó nói tiếp ─────────────────────────

def test_c1_phan_cong_thieu_gio_duoc_LIET_KE_rieng_chu_khong_bi_coi_la_sach():
    """Đây là chỗ em từng nói quá. Cửa này đã liệt kê đúng những phân công chưa có giờ từ trước
    vòng HD-11 — và bộ này giữ cho nó tiếp tục làm thế."""
    r = client.get("/api/v1/guide-assignments/yeu-cau/thieu", headers=login("cntt"))
    assert r.status_code == 200, r.text
    d = r.json()
    ds = [x["id"] for x in d.get("phan_cong_chua_co_gio", [])]
    assert ID["thieu_gio"] in ds, f"phân công thiếu giờ không được liệt kê: {ds}"
    assert ID["co_gio"] not in ds


def test_c2_cua_ay_noi_RO_rang_day_la_viec_con_thieu():
    """Một danh sách không kèm lời giải thích thì người đọc tự suy, và suy phổ biến nhất là 'chắc
    không sao'."""
    r = client.get("/api/v1/guide-assignments/yeu-cau/thieu", headers=login("cntt"))
    ghi_chu = r.json().get("ghi_chu", "")
    assert "KHÔNG kiểm được trùng lịch" in ghi_chu, ghi_chu
    assert "không phải đã kiểm và không trùng" in ghi_chu, ghi_chu


# ───────────────────────── D · chứng minh các ca trên CẮN ─────────────────────────

def test_d1_dung_lai_nhanh_nuot_loi_thi_ca_A2_mat_can_cu():
    """Bản cũ: `try: execute(...) except Exception: pass`. Chạy lại chính ca A2 qua nó và đòi nó
    NUỐT — không phân biệt được hai bản thì A2 chẳng đo gì."""
    class LoiKhoa(Exception):
        pass

    def khoa_ban_cu(db, guide_id):
        try:
            db.execute(None)
        except Exception:
            pass

    p = _PhienGia("postgresql", loi=LoiKhoa("lock timeout"))
    khoa_ban_cu(p, 1)          # bản CŨ: im lặng đi qua
    p2 = _PhienGia("postgresql", loi=LoiKhoa("lock timeout"))
    with pytest.raises(LoiKhoa):
        HDV.khoa_hdv(p2, 1)    # bản MỚI: ném


def test_d2_dung_lai_nhanh_tra_ve_em_thi_ca_B1_mat_can_cu():
    from app.db.session import SessionLocal
    from app.models.hr import GuideAssignment

    def canh_ban_cu(db, a):
        if HDV.khong_so_duoc(a.bat_dau, a.ket_thuc):
            return                      # bản CŨ: êm
        raise AssertionError("không tới đây trong ca này")

    with SessionLocal() as db:
        a = db.get(GuideAssignment, ID["thieu_gio"])
        assert canh_ban_cu(db, a) is None       # bản cũ: không nói gì
        with pytest.raises(ValueError):          # bản mới: nói
            HDV.canh_trung_sau_khi_ghi(db, a)
