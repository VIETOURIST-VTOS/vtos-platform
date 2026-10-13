"""HD-8 — BÁO CÁO SAU TOUR VÀO LỚP TÁCH BẠCH TRÁCH NHIỆM ĐÃ CÓ, không dựng lại lần hai.

Chủ tịch chốt 13/10/2026, câu D2 = phương án A: ký SỰ TỒN TẠI của cặp «người nộp ≠ người xác nhận»,
MỨC ĐỂ TRỐNG — chạy ở "cảnh báo nhưng cho qua" và bị đếm lên, như hai cặp đã ký 09/10/2026.

VÌ SAO KHÔNG DỰNG MỚI. Đợt E2a (09/10/2026) đã xây đúng cơ chế này và đã đo: *"220 tài khoản, 6
người có từ hai tài khoản trở lên, tổng 24 dòng, bốn cặp đang mở cả hai."* Hai bảng `buoc_da_lam`
và `cap_tach_nhiem`, nhận diện người bằng MÃ NHÂN VIÊN. Việc của vòng này chỉ là đăng ký luồng báo
cáo sau tour vào đó: hai mã bước, một cặp có chữ ký, hai lời gọi `ghi_buoc()`.

HAI LỚP, HAI CÂU HỎI KHÁC NHAU — và đây là phần đáng đọc.

  `_khong_tu_kiem` (Đợt HD-7)   "tài khoản đang bấm có phải hồ sơ của hướng dẫn viên chuyến này
                                 không" — MỘT tài khoản, MỘT hồ sơ.
  cặp tách nhiệm (vòng này)     "NGƯỜI này đã nộp chính bản báo cáo ấy chưa" — nhận ra người qua
                                 mã nhân viên, nên thấy được CẢ HAI tài khoản của cùng một người.

Lớp trên không thay được lớp dưới: một người mở tài khoản thứ hai, nối hồ sơ khác, vẫn lọt lớp
trên. Lớp dưới bắt được vì nó không hỏi hồ sơ, nó hỏi người.

  A. Cặp đã đăng ký đúng luật của bảng: có chữ ký, có căn cứ, KHÔNG có mức.
  B. Hai dấu chân được ghi, và ghi vào ĐÚNG MỘT phạm vi.
  C. Một người hai tài khoản: cho qua nhưng BỊ NÊU; hai người khác nhau thì im.
  D. Ngày Chủ tịch đặt mức `canh_bao_va_chan` thì chặn THẬT, không phải sửa một dòng mã nào.
  E. Chứng minh các ca trên CẮN.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd8.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd8.db"):
    os.remove("test_hd8.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ks_tach_nhiem as KTN

client = TestClient(app)
MK = "Vtos@Demo#2026"
MA_CAP = "nop-bao-cao-tour-vs-kiem"
ID: dict[str, int] = {}
D = datetime(2026, 11, 20, 6, 0)


def _cap_quyen_kiem_thay(db, *ten_tai_khoan):
    """Cấp năng lực `kiem_bao_cao_tour` cho vai kiểm thay — Đợt HD-10, 13/10/2026.

    Từ HD-10, `hcns` và `cntt` không mặc nhiên xác nhận được báo cáo sau tour (Chủ tịch: *quyền
    quản trị kỹ thuật không tự sinh quyền duyệt*). Cảnh dựng ở đây đi qua ĐÚNG bảng ngoại lệ mà
    đời thật đi qua, kèm lý do và hạn, chứ không nhét một cờ vào mã — cảnh giả thì phép thử xanh
    mà hệ thống thật vẫn chặn.
    """
    from datetime import date as _d
    from datetime import timedelta as _td

    from sqlalchemy import select as _sel

    from app.models.core import User as _U
    from app.models.core import UserGrant as _G
    for un in ten_tai_khoan:
        t = db.execute(_sel(_U).where(_U.username == un)).scalars().first()
        assert t is not None, f"không có tài khoản {un} để cấp quyền"
        db.add(_G(user_id=t.id, kind="capability", value="kiem_bao_cao_tour",
                  from_date=_d.today(), to_date=_d.today() + _td(days=90),
                  reason="Phép thử: vai kiểm thay cần năng lực cấp riêng từ Đợt HD-10.",
                  granted_by="chutich", approved_by="chutich"))
    db.commit()


def login(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from sqlalchemy import select

        from app.core.security import hash_password
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment

        db = _db()
        op = db.execute(select(User)).scalars().first().id

        def _hdv(ma, ten):
            return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                            start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                            member_org=True, contract_type="ctv", ctv_contract=True)

        e1 = _hdv("H8001", "Trần Văn A")
        t = Tour(code="H8-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([e1, t])
        db.commit()

        # MỘT NGƯỜI, HAI TÀI KHOẢN — cùng mã nhân viên H8TP1. Tài khoản thứ nhất nộp hộ, tài khoản
        # thứ hai xác nhận. Lớp HD-7 không bắt được ca này vì không tài khoản nào nối với hồ sơ
        # của hướng dẫn viên chuyến ấy; lớp tách nhiệm bắt được vì nó so NGƯỜI.
        u_a = User(username="h8.mot.nop", full_name="Phạm Văn Trưởng", role="cntt",
                   department="", staff_code="H8TP1", password_hash=hash_password(MK))
        u_b = User(username="h8.mot.kiem", full_name="Phạm Văn Trưởng", role="hcns",
                   department="", staff_code="H8TP1", password_hash=hash_password(MK))
        # HAI NGƯỜI KHÁC NHAU — hai mã khác nhau.
        u_c = User(username="h8.hai.nop", full_name="Nguyễn Thị B", role="cntt",
                   department="", staff_code="H8KH2", password_hash=hash_password(MK))
        u_d = User(username="h8.ba.kiem", full_name="Lê Văn C", role="hcns",
                   department="", staff_code="H8KH3", password_hash=hash_password(MK))
        db.add_all([u_a, u_b, u_c, u_d])
        db.commit()

        def _pc():
            a = GuideAssignment(tour_id=t.id, guide_id=e1.id, days=4, rate_per_day=800_000,
                                bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
            db.add(a); db.commit()
            return a.id

        for k in ("mot_nguoi", "hai_nguoi", "dat_muc", "dau_chan"):
            ID[k] = _pc()
        _cap_quyen_kiem_thay(db, "h8.mot.kiem", "h8.ba.kiem")
        db.close()
        yield


def _nop(aid, ai):
    h = login(ai)
    r = client.post(f"/api/v1/guide-assignments/{aid}/bao-cao",
                    json={"chuong_trinh_thuc_hien": "đã đi đủ chương trình", "so_khach_thuc_te": 20},
                    headers=h)
    assert r.status_code in (200, 201), r.text
    r = client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/gui", json={}, headers=h)
    assert r.status_code in (200, 201), r.text


def _kiem(aid, ai):
    return client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/kiem",
                       json={"xac_nhan": True}, headers=login(ai))


# ───────────────────────── A · cặp đã đăng ký đúng luật của bảng ─────────────────────────

def test_a1_hai_ma_buoc_co_that_trong_bang_BUOC():
    """Một cặp trỏ vào bước không tồn tại là một cặp không bao giờ khớp — tức một hàng rào tắt."""
    from app.models.tach_nhiem import BUOC
    assert "nop_bao_cao_tour" in BUOC
    assert "kiem_bao_cao_tour" in BUOC


def test_a2_cap_co_chu_ky_va_can_cu():
    """Bất biến của bảng `cap_tach_nhiem`: không dòng nào vô chủ. Máy nạp sẵn một dòng không chữ ký
    là máy tự đặt quy chế hộ người."""
    from app.models.tach_nhiem import CAP_DA_KY
    d = [x for x in CAP_DA_KY if x["ma_cap"] == MA_CAP]
    assert len(d) == 1, "không tìm thấy cặp báo cáo sau tour trong CAP_DA_KY"
    assert d[0]["nguoi_ky"].strip() and d[0]["can_cu"].strip()
    assert "13/10/2026" in d[0]["can_cu"], "căn cứ phải ghi ngày Chủ tịch chốt"


def test_a3_cap_KHONG_duoc_dat_san_muc():
    """Chủ tịch ký SỰ TỒN TẠI của cặp, chưa ký MỨC (câu D2 = phương án A, 13/10/2026). Tự đặt
    'chặn' hộ là đúng lỗi đã phải sửa ở bản v1.0 ngày 09/10."""
    from app.models.tach_nhiem import CAP_DA_KY
    d = [x for x in CAP_DA_KY if x["ma_cap"] == MA_CAP][0]
    assert "muc_do" not in d, f"cặp bị đặt sẵn mức `{d.get('muc_do')}` — không ai ký mức ấy"


def test_a4_sau_khi_nap_thi_cap_bi_dem_len_vi_chua_co_muc():
    with _db() as db:
        KTN.nap_cap_da_ky(db)
        db.commit()
        assert MA_CAP in KTN.cap_chua_dat_muc(db), \
            "chưa đặt mức thì phải bị đếm lên, không được im"


# ───────────────────────── B · hai dấu chân, đúng một phạm vi ─────────────────────────

def _dau_chan(aid):
    """Mọi dấu chân của phân công này, BẤT KỂ phạm vi.

    Lọc đúng `pham_vi == f"pc:{aid}"` thì ca B2 không bao giờ bắt được điều nó đặt tên: một bước
    rơi sang phạm vi khác sẽ biến mất khỏi kết quả, và B2 thấy đúng một phạm vi nên xanh. Hỏi rộng
    rồi mới đếm phạm vi thì mới là hỏi đúng câu — bản nháp đầu của bộ này mắc đúng lỗi ấy, phép
    đột biến thứ ba lôi nó ra.
    """
    from sqlalchemy import select

    from app.models.tach_nhiem import BuocDaLam
    with _db() as db:
        return [(d.ma_buoc, d.pham_vi, d.ma_nguoi) for d in db.execute(
            select(BuocDaLam).where(BuocDaLam.pham_vi.like(f"%:{aid}"),
                                    BuocDaLam.ma_buoc.in_(("nop_bao_cao_tour",
                                                           "kiem_bao_cao_tour")))).scalars()]


def test_b1_gui_va_kiem_deu_de_lai_dau_chan():
    _nop(ID["dau_chan"], "h8.hai.nop")
    assert [x[0] for x in _dau_chan(ID["dau_chan"])] == ["nop_bao_cao_tour"]
    assert _kiem(ID["dau_chan"], "h8.ba.kiem").status_code == 200
    assert sorted(x[0] for x in _dau_chan(ID["dau_chan"])) == \
        ["kiem_bao_cao_tour", "nop_bao_cao_tour"]


def test_b2_hai_dau_chan_nam_trong_DUNG_MOT_pham_vi():
    """Hai bước rơi vào hai phạm vi khác nhau thì cặp KHÔNG BAO GIỜ khớp — và hàng rào trông như
    đang chạy trong khi nó đã tắt. Đây đúng chỗ `models/tach_nhiem.py` cảnh báo khi giải thích vì
    sao phạm vi là một chuỗi chứ không phải một số."""
    pv = {x[1] for x in _dau_chan(ID["dau_chan"])}
    assert len(pv) == 1, f"hai bước nằm ở {len(pv)} phạm vi khác nhau: {pv}"


# ───────────────────────── C · một người hai tài khoản ─────────────────────────

def test_c1_mot_nguoi_hai_tai_khoan_thi_CHO_QUA_nhung_BI_NEU():
    """Mức để trống nên chưa chặn — nhưng vi phạm phải hiện ra, cả trên màn hình lẫn trong nhật ký.
    Một cảnh báo người bấm không thấy thì nó chỉ cảnh báo cho tương lai."""
    _nop(ID["mot_nguoi"], "h8.mot.nop")
    r = _kiem(ID["mot_nguoi"], "h8.mot.kiem")
    assert r.status_code == 200, r.text
    vp = r.json().get("tach_nhiem")
    assert vp, f"cho qua nhưng KHÔNG nêu vi phạm nào: {r.json()}"
    assert vp[0]["ma_cap"] == MA_CAP
    assert vp[0]["muc_do"] == "canh_bao_cho_qua"

    from sqlalchemy import desc, select

    from app.models.core import AuditLog
    with _db() as db:
        d = db.execute(select(AuditLog).where(AuditLog.action == "kiem_bao_cao_tour")
                       .order_by(desc(AuditLog.id))).scalars().first()
        assert (d.after or {}).get("tach_nhiem") == [MA_CAP], \
            f"nhật ký không ghi vi phạm: {d.after!r}"


def test_c2_hai_nguoi_khac_nhau_thi_khong_neu_gi():
    _nop(ID["hai_nguoi"], "h8.hai.nop")
    r = _kiem(ID["hai_nguoi"], "h8.ba.kiem")
    assert r.status_code == 200, r.text
    assert not r.json().get("tach_nhiem"), f"hai người khác nhau mà vẫn báo vi phạm: {r.json()}"


# ───────────────────────── D · ngày Chủ tịch đặt mức thì chặn THẬT ─────────────────────────

def test_d1_dat_muc_chan_thi_cua_kiem_chan_ngay_khong_sua_dong_ma_nao():
    """Lời hứa của phương án A: để trống mức hôm nay, đặt mức sau mà không phải sửa mã. Phép thử
    này là chỗ kiểm lời hứa ấy — đặt mức vào CƠ SỞ DỮ LIỆU, không chạm một dòng mã nào."""
    from sqlalchemy import select

    from app.models.tach_nhiem import CapTachNhiem
    _nop(ID["dat_muc"], "h8.mot.nop")
    with _db() as db:
        KTN.nap_cap_da_ky(db)
        c = db.execute(select(CapTachNhiem).where(CapTachNhiem.ma_cap == MA_CAP)).scalars().first()
        assert c is not None, "cặp chưa được nạp vào cơ sở dữ liệu"
        cu = c.muc_do
        c.muc_do = "canh_bao_va_chan"
        db.commit()
    try:
        r = _kiem(ID["dat_muc"], "h8.mot.kiem")
        assert r.status_code == 403, f"đã đặt mức chặn mà vẫn cho qua: {r.status_code} {r.text}"
        assert "TACH_NHIEM" in r.text
    finally:
        with _db() as db:
            c = db.execute(select(CapTachNhiem).where(
                CapTachNhiem.ma_cap == MA_CAP)).scalars().first()
            c.muc_do = cu
            db.commit()


# ───────────────────────── E · chứng minh các ca trên CẮN ─────────────────────────

def test_e1_khong_co_dau_chan_NOP_thi_ca_C1_khong_thay_gi():
    """Nếu cửa gửi quên gọi `ghi_buoc`, cặp không có gì để đối chiếu và ca C1 im lặng xanh. Xoá dấu
    chân đi rồi hỏi lại chính câu ấy: phải không còn vi phạm nào — tức là C1 thật sự đang đo dấu
    chân, chứ không đo một thứ khác."""
    from sqlalchemy import select

    from app.models.core import User
    from app.models.tach_nhiem import BuocDaLam
    with _db() as db:
        u = db.execute(select(User).where(User.username == "h8.mot.kiem")).scalars().first()
        truoc = KTN.kiem(db, f"pc:{ID['mot_nguoi']}", "kiem_bao_cao_tour", u)
        assert truoc["vi_pham"], "dựng sai cảnh: ca C1 đáng lẽ đang có vi phạm"

        bo = [d for d in db.execute(select(BuocDaLam).where(
            BuocDaLam.pham_vi == f"pc:{ID['mot_nguoi']}",
            BuocDaLam.ma_buoc == "nop_bao_cao_tour")).scalars()]
        assert bo, "không có dấu chân nộp nào để gỡ"
        giu = [(d.ma_nguoi, d.username, d.vai) for d in bo]
        for d in bo:
            db.delete(d)
        db.commit()

        sau = KTN.kiem(db, f"pc:{ID['mot_nguoi']}", "kiem_bao_cao_tour", u)
        assert not sau["vi_pham"], "gỡ dấu chân rồi mà vẫn báo vi phạm – ca C1 đang đo thứ khác"

        for ma_nguoi, un, vai in giu:          # trả lại cảnh như cũ
            db.add(BuocDaLam(pham_vi=f"pc:{ID['mot_nguoi']}", ma_buoc="nop_bao_cao_tour",
                             ma_nguoi=ma_nguoi, username=un, vai=vai))
        db.commit()


def test_e2_pham_vi_khai_dung_MOT_cho_trong_ma_nguon():
    """Gõ chuỗi phạm vi tại hai nơi gọi là mời một dấu cách thừa vào làm hai dấu chân lệch phạm vi.
    Canh bằng cây cú pháp: chuỗi `pc:` chỉ được xuất hiện bên trong hàm khai phạm vi."""
    import ast
    import inspect
    from pathlib import Path

    from app.api.v1 import hr as HR
    cay = ast.parse(Path(inspect.getsourcefile(HR)).read_text(encoding="utf-8"))

    def _co_pc(nut) -> bool:
        for n in ast.walk(nut):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and "pc:" in n.value:
                return True
            if isinstance(n, ast.JoinedStr):
                for p in n.values:
                    if isinstance(p, ast.Constant) and isinstance(p.value, str) and "pc:" in p.value:
                        return True
        return False

    pham = [n.name for n in ast.walk(cay)
            if isinstance(n, ast.FunctionDef) and n.name != "_pv_bao_cao" and _co_pc(n)]
    assert not pham, f"chuỗi phạm vi 'pc:' bị gõ tay ngoài `_pv_bao_cao`: {', '.join(pham)}"
