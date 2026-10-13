"""HD-9 (D1) — `tp_hd` phải có MÃ NHÂN VIÊN, nhưng hôm nay chỉ ĐẾM chứ chưa chặn.

Chủ tịch chốt 13/10/2026, câu D1 = phương án A: giữ nguyên cách định danh người theo mã nhân viên,
và bắt buộc `tp_hd` phải có mã.

VÌ SAO KHÔNG BẬT THẲNG. Cặp xung đột ký ở Đợt HD-8 nhận ra người bằng `users.staff_code`. Trưởng
phòng Hướng dẫn thiếu mã thì hai tài khoản của cùng một người thành hai người, và cặp ấy không bắt
được gì — tức là một hàng rào trông như đang chạy mà đã tắt. Nhưng bắt buộc NGAY HÔM NAY là khóa
Trưởng phòng ra khỏi cửa xác nhận nếu dữ liệu HCNS chưa đủ, và em không nhìn được máy chủ thật để
biết dữ liệu ấy đã đủ hay chưa.

Lớp tách nhiệm đã có sẵn lời giải cho đúng tình huống này từ Đợt E2a: công tắc theo ngày
`tach_nhiem_bat_buoc_ma_nv_tu`. Tham số rỗng thì ĐẾM và liệt kê cho HCNS đi điền, chưa chặn ai;
Chủ tịch đặt ngày thì chặn thật. Vòng này chỉ thêm `tp_hd` vào danh sách vai đi qua công tắc ấy.

MỘT ĐIỀU KHÔNG NỚI. Đợt E2a cố ý KHÔNG mở rộng danh sách CHẶN, vì nới ra là chặn `hcns` ở những
bước họ không hề làm. Lý do ấy còn nguyên giá trị, và bộ này canh để nó không bị phá. `tp_hd` khác
`hcns` ở đúng một điểm: Trưởng phòng Hướng dẫn LÀM CẢ HAI BƯỚC của cặp xung đột — vừa dẫn tour nên
nộp báo cáo, vừa là người xác nhận. Chặn người làm cả hai bước không phải chặn oan.

  A. Hai danh sách vẫn tách bạch, và `VAI_TIEN` không bị ai nhét thêm vào.
  B. Hôm nay: đếm, liệt kê cho HCNS, KHÔNG chặn ai.
  C. Ngày Chủ tịch đặt tham số: chặn thật, không sửa một dòng mã nào.
  D. Chứng minh các ca trên CẮN.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd9.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd9.db"):
    os.remove("test_hd9.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ks_tach_nhiem as KTN
from app.services import rules as R

client = TestClient(app)
MK = "Vtos@Demo#2026"
ID: dict[str, int] = {}
D = datetime(2026, 11, 20, 6, 0)


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

        # Trưởng phòng THIẾU mã: có hồ sơ (nối bằng user_id, nên cổng HD-7 cho qua) nhưng tài
        # khoản trống `staff_code`, nên lớp tách nhiệm không nhận ra người.
        e_thieu = _hdv("H9TP0", "Trưởng phòng thiếu mã")
        e_du = _hdv("H9TP1", "Trưởng phòng đủ mã")
        hdv = _hdv("H9001", "Trần Văn A")
        t = Tour(code="H9-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([e_thieu, e_du, hdv, t])
        db.commit()

        u_thieu = User(username="h9.tp.thieu_ma", full_name="Trưởng phòng thiếu mã",
                       role="tp_hd", department="Hướng dẫn", password_hash=hash_password(MK))
        u_du = User(username="h9.tp.du_ma", full_name="Trưởng phòng đủ mã", role="tp_hd",
                    department="Hướng dẫn", staff_code="H9TP1", password_hash=hash_password(MK))
        u_hcns = User(username="h9.hcns.thieu_ma", full_name="HCNS thiếu mã", role="hcns",
                      department="", password_hash=hash_password(MK))
        u_nop = User(username="h9.nguoi_nop", full_name="Người nộp hộ", role="cntt",
                     department="", staff_code="H9KH9", password_hash=hash_password(MK))
        db.add_all([u_thieu, u_du, u_hcns, u_nop])
        db.commit()
        e_thieu.user_id, e_du.user_id = u_thieu.id, u_du.id
        db.commit()

        def _pc():
            a = GuideAssignment(tour_id=t.id, guide_id=hdv.id, days=4, rate_per_day=800_000,
                                bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
            db.add(a); db.commit()
            return a.id

        for k in ("chua_bat", "da_bat", "du_ma"):
            ID[k] = _pc()
        db.close()
        yield


def _nop(aid):
    h = login("h9.nguoi_nop")
    assert client.post(f"/api/v1/guide-assignments/{aid}/bao-cao",
                       json={"chuong_trinh_thuc_hien": "xong", "so_khach_thuc_te": 20},
                       headers=h).status_code in (200, 201)
    assert client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/gui", json={},
                       headers=h).status_code in (200, 201)


def _kiem(aid, ai):
    return client.post(f"/api/v1/guide-assignments/{aid}/bao-cao/kiem",
                       json={"xac_nhan": True}, headers=login(ai))


def _tk(ten):
    from sqlalchemy import select

    from app.models.core import User
    with _db() as db:
        return db.execute(select(User).where(User.username == ten)).scalars().first()


# ───────────────────────── A · hai danh sách vẫn tách bạch ─────────────────────────

def test_a1_tp_hd_nam_trong_danh_sach_PHAI_CO_MA():
    from app.models.tach_nhiem import VAI_PHAI_CO_MA_NV
    assert "tp_hd" in VAI_PHAI_CO_MA_NV


def test_a2_VAI_TIEN_KHONG_bi_nhet_them_tp_hd():
    """Tên biến `VAI_TIEN` được nhắc trong năm tệp khác. Nhét một vai không dính tiền vào đó là
    để lại một cái tên nói sai — đúng loại bẫy cho người đọc sau mà cả ngày hôm nay đang dọn."""
    from app.models.tach_nhiem import VAI_TIEN
    assert "tp_hd" not in VAI_TIEN
    assert set(VAI_TIEN) == {"ketoan", "ketoan_truong", "ketoan_tt", "thu_quy", "chutich", "tgd"}


def test_a3_danh_sach_PHEP_DO_van_rong_hon_danh_sach_CHAN():
    """Bất biến của Đợt E2a: danh sách vai mà thiếu mã làm phép đo MÙ phải bao trùm danh sách vai
    BỊ CHẶN. Hẹp hơn là có vai bị chặn mà không ai đếm."""
    from app.models.tach_nhiem import VAI_PHAI_CO_MA_NV
    rong = set(KTN.vai_can_ma_de_phep_do_thay())
    assert set(VAI_PHAI_CO_MA_NV) <= rong


def test_a4_hcns_thieu_ma_van_KHONG_bi_coi_la_vi_pham():
    """Đợt E2a cố ý không nới danh sách chặn sang `hcns`, vì nới là chặn họ ở bước họ không làm.
    Vòng này thêm đúng `tp_hd`, không nới thêm gì khác."""
    assert KTN.thieu_ma_nhan_vien(_tk("h9.hcns.thieu_ma")) is False


# ───────────────────────── B · hôm nay: đếm, không chặn ─────────────────────────

def test_b1_tp_hd_thieu_ma_bi_tinh_la_thieu():
    assert KTN.thieu_ma_nhan_vien(_tk("h9.tp.thieu_ma")) is True
    assert KTN.thieu_ma_nhan_vien(_tk("h9.tp.du_ma")) is False


def test_b2_tp_hd_thieu_ma_hien_trong_danh_sach_HCNS_di_dien():
    """Trả danh sách chứ không trả số: một con số thì không ai biết phải đi tìm ai."""
    with _db() as db:
        ten = {d["username"] for d in KTN.tai_khoan_thieu_ma_nv(db)}
    assert "h9.tp.thieu_ma" in ten
    assert "h9.tp.du_ma" not in ten


def test_b3_CHUA_dat_tham_so_thi_KHONG_khoa_ai():
    """Lời hứa của vòng này. Trưởng phòng thiếu mã vẫn xác nhận được báo cáo hôm nay."""
    with _db() as db:
        assert KTN.bat_buoc_ma_nv(db) is False, "dựng sai cảnh: tham số đáng lẽ chưa đặt"
    _nop(ID["chua_bat"])
    r = _kiem(ID["chua_bat"], "h9.tp.thieu_ma")
    assert r.status_code == 200, r.text


# ───────────────────────── C · ngày đặt tham số thì chặn thật ─────────────────────────

def _dat_tham_so(bat: bool):
    """Bật/tắt công tắc bằng DỮ LIỆU, không bằng mã."""
    from sqlalchemy import select

    from app.models.core import Param
    from app.models.tach_nhiem import KHOA_BAT_BUOC_MA_NV
    with _db() as db:
        for p in db.execute(select(Param).where(Param.key == KHOA_BAT_BUOC_MA_NV)).scalars():
            db.delete(p)
        if bat:
            # Giá trị "1" chứ không phải một ngày: `bat_buoc_ma_nv` đọc qua `get_param`, vốn ép
            # về số. Xem ghi chú trong sổ vòng này — tên tham số có đuôi `_tu` gợi một NGÀY,
            # nhưng người đọc nó lại ép về số, nên điền ngày vào là công tắc im lặng không bật.
            db.add(Param(key=KHOA_BAT_BUOC_MA_NV, value="1",
                         label="Bắt buộc mã nhân viên cho vai phải so được người",
                         effective_from=date(2026, 1, 1), status="active",
                         signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
        db.commit()
    R.clear_param_cache()


def test_c1_dat_tham_so_thi_tp_hd_thieu_ma_BI_CHAN():
    _nop(ID["da_bat"])
    _dat_tham_so(True)
    try:
        with _db() as db:
            assert KTN.bat_buoc_ma_nv(db) is True, "công tắc không bật — phép thử không đo gì"
        r = _kiem(ID["da_bat"], "h9.tp.thieu_ma")
        assert r.status_code == 403, f"đã bật công tắc mà vẫn cho qua: {r.status_code} {r.text}"
        assert "mã nhân viên" in r.text
    finally:
        _dat_tham_so(False)


def test_c2_da_bat_cong_tac_thi_tp_hd_CO_ma_van_di_qua():
    """Chặn phải trúng người thiếu mã, không trúng cả vai."""
    _nop(ID["du_ma"])
    _dat_tham_so(True)
    try:
        r = _kiem(ID["du_ma"], "h9.tp.du_ma")
        assert r.status_code == 200, r.text
    finally:
        _dat_tham_so(False)


# ───────────────────────── D · chứng minh các ca trên CẮN ─────────────────────────

def test_d1_bo_tp_hd_khoi_danh_sach_thi_ca_B1_va_C1_mat_can_cu():
    """Dựng lại phép kiểm theo danh sách CŨ (`VAI_TIEN`) và đòi nó cho qua đúng tài khoản mà bản
    mới bắt. Không phân biệt được hai bản thì B1 và C1 chẳng đo gì."""
    from app.models.tach_nhiem import VAI_TIEN
    u = _tk("h9.tp.thieu_ma")

    def thieu_ban_cu(x) -> bool:
        return (getattr(x, "role", "") in VAI_TIEN
                and not (getattr(x, "staff_code", "") or "").strip())

    assert thieu_ban_cu(u) is False, "bản cũ đáng lẽ KHÔNG thấy tài khoản này"
    assert KTN.thieu_ma_nhan_vien(u) is True, "bản mới phải thấy"


def test_d2_cong_tac_that_su_la_thu_quyet_dinh_chan_hay_khong():
    """Cùng một tài khoản, cùng một phân công: tắt công tắc thì qua, bật thì chặn. Nếu kết quả
    giống nhau ở hai trạng thái thì ca C1 đang đo một thứ khác."""
    from sqlalchemy import select

    from app.models.hr import GuideAssignment
    with _db() as db:
        a = db.get(GuideAssignment, ID["chua_bat"])
        assert a is not None
        u = _tk("h9.tp.thieu_ma")
        _dat_tham_so(False)
        tat = KTN.kiem(db, f"pc:{a.id}", "kiem_bao_cao_tour", u)
        _dat_tham_so(True)
        try:
            bat = KTN.kiem(db, f"pc:{a.id}", "kiem_bao_cao_tour", u)
        finally:
            _dat_tham_so(False)
    assert tat["chan"] is False and bat["chan"] is True, \
        f"công tắc không đổi được kết quả: tắt={tat['chan']} bật={bat['chan']}"
