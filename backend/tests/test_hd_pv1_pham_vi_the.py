"""HD-PV1 — PHẠM VI HÀNH NGHỀ THEO LOẠI THẺ: đếm được trước, chặn sau.

Đo được trên main 3c28f6d trước vòng này: hướng dẫn viên thẻ NỘI ĐỊA xếp vào tour ĐOÀN NƯỚC NGOÀI
vẫn CHO QUA cổng 13. Không phải vì ai viết sai một dòng, mà vì `guide_eligible(e, on)` không nhận
tham số nào về chuyến — nó KHÔNG THỂ biết loại chuyến, nên câu hỏi ấy chưa từng được hỏi ở đâu cả.
Điều 58 khoản 1 Luật Du lịch 2017 dành việc đưa khách Việt Nam ra nước ngoài cho hướng dẫn viên
QUỐC TẾ.

VÒNG NÀY KHÔNG CHẶN AI, và bộ phép thử này canh đúng điều đó. `card_type` mặc định rỗng, nên chặn
ngay hôm nay là dừng việc xếp chuyến của cả phòng. Đếm trước, khoá sau — khuôn Chủ tịch đã duyệt ở
Đợt HD-9 và HD-12.

  A. Bảng phạm vi là DỮ LIỆU CÓ CĂN CỨ, không phải chữ viết cứng trong thân hàm.
  B. Phép hỏi trả BA giá trị, và "chưa kết luận được" không bị gộp vào "không đạt".
  C. Cửa đếm tách ba nhóm, không cắt bớt, và mỗi dòng không đạt phải NÓI RA căn cứ.
  D. Cửa đếm phải NÓI THẬT về việc nó có chặn hay không — ca này là ca sẽ đỏ đúng lúc cần đỏ.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd_pv1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd_pv1.db"):
    os.remove("test_hd_pv1.db")

from datetime import date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models.hr import CHUYEN_CHUA_KHAI_PHAM_VI, Employee, PHAM_VI_THE  # noqa: E402
from app.services.hr import (  # noqa: E402
    PV_CHUA_KET_LUAN, PV_DAT, PV_KHONG_DAT, pham_vi_the)

client = TestClient(app)
MK = "Vtos@Demo#2026"
TAI_KHOAN = "tp_hd_pv1"
ID: dict[str, int] = {}
D = datetime(2026, 12, 10, 6, 0)


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

        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from app.models.core import Tour, User
        from app.models.hr import GuideAssignment

        db = SessionLocal()
        op = db.execute(select(User)).scalars().first().id

        def _nv(ma, ten, loai_the):
            e = Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                         start_date=date(2024, 1, 1), card_no=ma, card_type=loai_the,
                         card_expiry=date(2030, 1, 1), member_org=True,
                         contract_type="ctv", ctv_contract=True)
            db.add(e); db.commit()
            return e.id

        def _tour(ma, loai):
            t = Tour(code=ma, name=ma, tour_type=loai, operator_id=op,
                     start_date=date(2026, 12, 10), end_date=date(2026, 12, 14))
            db.add(t); db.commit()
            return t.id

        def _chao(gid, tid, trang_thai="cho_xac_nhan"):
            a = GuideAssignment(tour_id=tid, guide_id=gid, days=4, rate_per_day=800_000,
                                bat_dau=D, ket_thuc=D + timedelta(days=4), status=trang_thai,
                                han_tra_loi=datetime.now() + timedelta(hours=12))
            db.add(a); db.commit()
            return a.id

        # Mỗi cảnh một người và một chuyến riêng: dùng chung thì một ca đổi kết quả của ca kia.
        ID["qt"] = _nv("PV1A", "Thẻ quốc tế", "quoc_te")
        ID["nd"] = _nv("PV1B", "Thẻ nội địa", "noi_dia")
        ID["nd2"] = _nv("PV1C", "Thẻ nội địa, chuyến trong nước", "noi_dia")
        ID["trong"] = _nv("PV1D", "Chưa khai loại thẻ", "")
        ID["qt2"] = _nv("PV1E", "Thẻ quốc tế, thuê xe", "quoc_te")
        ID["nd3"] = _nv("PV1F", "Thẻ nội địa, đã từ chối", "noi_dia")

        ID["t_qt"] = _tour("PV1-T-QT", "doan_nuoc_ngoai")
        ID["t_nd"] = _tour("PV1-T-ND", "doan_nuoc_ngoai")
        ID["t_nd2"] = _tour("PV1-T-TRONGNUOC", "le_noi_dia")
        ID["t_trong"] = _tour("PV1-T-TRONG", "le_noi_dia")
        ID["t_xe"] = _tour("PV1-T-XE", "thue_xe")
        ID["t_bo"] = _tour("PV1-T-BO", "doan_nuoc_ngoai")

        ID["a_qt"] = _chao(ID["qt"], ID["t_qt"])             # đạt
        ID["a_nd"] = _chao(ID["nd"], ID["t_nd"])             # KHÔNG đạt
        ID["a_nd2"] = _chao(ID["nd2"], ID["t_nd2"])          # đạt
        ID["a_trong"] = _chao(ID["trong"], ID["t_trong"])    # chưa kết luận được
        ID["a_xe"] = _chao(ID["qt2"], ID["t_xe"])            # chưa kết luận được
        ID["a_bo"] = _chao(ID["nd3"], ID["t_bo"], "tu_choi")  # đã từ chối – không đếm

        # Dữ liệu mẫu không dựng tài khoản vai `tp_hd`; phép thử tự dựng người của mình thay vì
        # bám vào seed.py, để sau này ai sửa seed cũng không làm bộ này đỏ vì chuyện chẳng liên
        # quan. TÊN TÀI KHOẢN MANG MÃ ĐỢT, không đặt là `tp_hd` chung: bộ HD-12 cũng dựng một tài
        # khoản tên ấy, và khi hai bộ chạy chung một lượt thì chúng dùng CHUNG một kho dữ liệu —
        # bước dựng cảnh của bộ chạy sau sập vì trùng tên, rồi mười lăm ca đỏ hàng loạt vì một lý
        # do chẳng liên quan gì tới điều chúng canh. Đã đo thật: xếp bộ này chạy trước HD-12 thì
        # HD-12 đổ 15 lỗi dựng cảnh; cùng thứ tự ấy trên cây sạch thì xanh. Bài này sổ Đợt HD-6
        # đã ghi một lần.
        if db.execute(select(User).where(User.username == TAI_KHOAN)).scalars().first() is None:
            db.add(User(username=TAI_KHOAN, full_name="Thử TP Hướng dẫn (HD-PV1)", role="tp_hd",
                        department="Hướng dẫn", password_hash=hash_password(MK)))
            db.commit()
        db.close()
        yield


def _the(loai):
    """Một hồ sơ KHÔNG ghi vào sổ: phép hỏi chỉ đọc `card_type`, không cần đi qua cơ sở dữ liệu."""
    return Employee(code="X", full_name="X", department="huong_dan", card_type=loai)


def _cua():
    r = client.get("/api/v1/huong-dan/pham-vi-the/lech", headers=login(TAI_KHOAN))
    assert r.status_code == 200, r.text
    return r.json()


# ═════════════ A · bảng phạm vi là DỮ LIỆU CÓ CĂN CỨ ═════════════

def test_a1_moi_dong_phai_noi_ra_can_cu():
    """Một luật không nói căn cứ là một luật người sau gỡ mà không biết mình đang gỡ cái gì.

    Cùng một lẽ với `CAP_DA_KY` của lớp tách bạch trách nhiệm (Đợt E2a).
    """
    assert PHAM_VI_THE, "Bảng phạm vi rỗng"
    for d in PHAM_VI_THE:
        assert d["can_cu"].strip(), f"Dòng «{d['loai_the']}» không nói căn cứ"
        assert "Điều 58" in d["can_cu"], \
            f"Căn cứ của «{d['loai_the']}» không dẫn điều luật nào: {d['can_cu']!r}"
        assert d["nhan"], f"Dòng «{d['loai_the']}» không nhận loại chuyến nào – dòng chết"


def test_a2_moi_loai_the_chi_co_MOT_dong():
    ds = [d["loai_the"] for d in PHAM_VI_THE]
    assert len(ds) == len(set(ds)), f"Loại thẻ khai hai lần, dòng sau che dòng trước: {ds}"


def test_a3_bang_khong_khai_ra_loai_chuyen_khong_ton_tai():
    """Khai một loại chuyến hệ thống không có là mở một cửa không bao giờ ai đi qua – và tệ hơn,
    làm người đọc tin rằng loại ấy đã được xét."""
    from app.models.core import TOUR_TYPES
    for d in PHAM_VI_THE:
        la = set(d["nhan"]) - set(TOUR_TYPES)
        assert not la, f"Dòng «{d['loai_the']}» khai loại chuyến không có trong TOUR_TYPES: {la}"


def test_a4_loai_chuyen_de_trong_thi_khong_dong_nao_duoc_nhan():
    """`non_package` và `thue_xe` CỐ Ý chưa khai phạm vi. Một dòng vừa khai nhận chúng vừa nằm
    trong danh sách 'chưa khai' là bảng tự mâu thuẫn, và phép hỏi sẽ trả lời theo dòng nào tới
    trước chứ không theo ý ai."""
    for d in PHAM_VI_THE:
        trung = set(d["nhan"]) & set(CHUYEN_CHUA_KHAI_PHAM_VI)
        assert not trung, f"Dòng «{d['loai_the']}» vừa nhận vừa để trống: {trung}"


# ═════════════ B · phép hỏi trả BA giá trị ═════════════

def test_b1_the_quoc_te_nhan_ca_bon_loai_chuyen_huong_dan():
    for lt in ("le_noi_dia", "le_nuoc_ngoai", "doan_noi_dia", "doan_nuoc_ngoai"):
        kq, vi_sao = pham_vi_the(_the("quoc_te"), lt)
        assert kq == PV_DAT, f"quoc_te + {lt} ra {kq}: {vi_sao}"


def test_b2_the_noi_dia_nhan_chuyen_trong_nuoc():
    for lt in ("le_noi_dia", "doan_noi_dia"):
        kq, _ = pham_vi_the(_the("noi_dia"), lt)
        assert kq == PV_DAT, f"noi_dia + {lt} ra {kq}"


def test_b3_the_noi_dia_KHONG_nhan_chuyen_ra_nuoc_ngoai():
    """Chỗ hỏng đo được trên main. Lý do trả về phải DẪN ĐƯỢC điều luật, vì người đọc nó là người
    điều phối đang bị chặn và họ có quyền biết mình bị chặn theo cái gì."""
    for lt in ("le_nuoc_ngoai", "doan_nuoc_ngoai"):
        kq, vi_sao = pham_vi_the(_the("noi_dia"), lt)
        assert kq == PV_KHONG_DAT, f"noi_dia + {lt} ra {kq} – đúng ra phải không đạt"
        assert "Điều 58" in vi_sao, f"Lý do không dẫn căn cứ: {vi_sao!r}"


def test_b4_chua_khai_the_la_CHUA_KET_LUAN_DUOC_chu_khong_phai_khong_dat():
    """Gộp ô còn thiếu vào 'không đạt' là biến một việc phải NHẬP thành một lời buộc tội. Cùng một
    lẽ với `khong_so_duoc` trong `services/hdv.py`."""
    for lt in ("le_noi_dia", "doan_nuoc_ngoai"):
        kq, vi_sao = pham_vi_the(_the(""), lt)
        assert kq == PV_CHUA_KET_LUAN, f"thẻ rỗng + {lt} ra {kq}"
        assert kq != PV_KHONG_DAT
        assert vi_sao.strip()


def test_b5_chuyen_chua_khai_loai_cung_la_chua_ket_luan_duoc():
    for lt in (None, "", "   "):
        kq, _ = pham_vi_the(_the("noi_dia"), lt)
        assert kq == PV_CHUA_KET_LUAN, f"loại chuyến {lt!r} ra {kq}"


def test_b6_hai_loai_chuyen_de_trong_khong_ket_luan_voi_BAT_KY_loai_the_nao():
    for the in ("quoc_te", "noi_dia"):
        for lt in CHUYEN_CHUA_KHAI_PHAM_VI:
            kq, vi_sao = pham_vi_the(_the(the), lt)
            assert kq == PV_CHUA_KET_LUAN, f"{the} + {lt} ra {kq} – chưa ai chốt loại này"
            assert lt in vi_sao


def test_b7_loai_the_chua_khai_trong_bang_thi_khong_ket_luan_bua():
    """Điều 58 có ba loại thẻ; VTOS mới nhận hai. Gặp loại thứ ba thì phép hỏi phải NÓI RA là nó
    chưa biết, chứ không được mặc định đạt (cho qua ẩu) hay mặc định không đạt (chặn oan)."""
    kq, vi_sao = pham_vi_the(_the("tai_diem"), "le_noi_dia")
    assert kq == PV_CHUA_KET_LUAN, f"thẻ tại điểm ra {kq}"
    assert "tai_diem" in vi_sao


# ═════════════ C · cửa đếm ═════════════

def test_c1_cua_tach_ba_nhom_dung_nguoi_dung_viec():
    d = _cua()
    kd = {x["phan_cong_id"] for x in d["khong_dat"]}
    ck = {x["phan_cong_id"] for x in d["chua_ket_luan_duoc"]}
    assert ID["a_nd"] in kd, "Thẻ nội địa + đoàn nước ngoài không nằm trong nhóm không đạt"
    assert ID["a_trong"] in ck and ID["a_xe"] in ck
    assert ID["a_qt"] not in kd | ck and ID["a_nd2"] not in kd | ck
    assert d["so_khong_dat"] == len(d["khong_dat"])
    assert d["so_chua_ket_luan_duoc"] == len(d["chua_ket_luan_duoc"])
    assert d["so_dat"] >= 2


def test_c2_khong_gop_hai_nhom_lam_mot():
    d = _cua()
    kd = {x["phan_cong_id"] for x in d["khong_dat"]}
    ck = {x["phan_cong_id"] for x in d["chua_ket_luan_duoc"]}
    assert not (kd & ck), f"Một phân công nằm ở cả hai nhóm: {kd & ck}"
    assert ID["a_trong"] not in kd, "Hồ sơ chưa khai thẻ bị xếp vào nhóm VI PHẠM"
    assert ID["a_xe"] not in kd, "Loại chuyến chưa khai luật bị xếp vào nhóm VI PHẠM"


def test_c3_loi_chao_da_tu_choi_khong_bi_dem():
    """Đếm cả bản ghi đã từ chối là thổi phồng con số Chủ tịch sẽ dựa vào để bật khoá."""
    d = _cua()
    moi = {x["phan_cong_id"] for x in d["khong_dat"] + d["chua_ket_luan_duoc"]}
    assert ID["a_bo"] not in moi


def test_c4_moi_dong_khong_dat_phai_noi_ra_can_cu():
    for x in _cua()["khong_dat"]:
        assert "Điều 58" in x["vi_sao"], f"Dòng #{x['phan_cong_id']} chặn mà không nói theo gì"
        assert x["the_loai"] and x["loai_chuyen"], "Dòng không nói rõ thẻ gì, chuyến gì"


def test_c5_cua_khong_mo_cho_nguoi_khong_dang_nhap():
    assert client.get("/api/v1/huong-dan/pham-vi-the/lech").status_code in (401, 403)


# ═════════════ D · cửa phải NÓI THẬT, và luật phải ở lại chỗ của luật ═════════════

def test_d1_co_bao_dang_chan_phai_khop_voi_viec_cong_13_co_chan_that_khong():
    """Ca quan trọng nhất của vòng này, và là ca sẽ ĐỎ ĐÚNG LÚC CẦN ĐỎ.

    Hôm nay cổng 13 vẫn cho qua, nên cửa phải nói `dang_chan: False`. Ngày nào ai đó gắn phép hỏi
    vào cổng 13 mà quên sửa dòng chữ ở cửa đếm, bộ này đỏ – vì lúc ấy cửa đang nói với Chủ tịch
    rằng hệ thống chưa chặn trong khi nó đã chặn. Một cái cờ nói sai về chính mình còn nguy hơn
    không có cờ nào: người đọc tin vào nó mà ra quyết định.
    """
    h = login(TAI_KHOAN)
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.core import Tour, User
    with SessionLocal() as db:
        op = db.execute(select(User)).scalars().first().id
        t = Tour(code="PV1-T-DO", name="Đo cổng 13", tour_type="doan_nuoc_ngoai", operator_id=op,
                 start_date=date(2026, 12, 20), end_date=date(2026, 12, 24))
        db.add(t); db.commit()
        tid = t.id
    r = client.post("/api/v1/huong-dan/chao-chuyen", headers=h,
                    json={"tour_id": tid, "guide_id": ID["nd"], "days": 4, "rate_per_day": 800_000})
    chan_that = r.status_code == 422 and "CONG_13" in r.text
    assert _cua()["dang_chan"] is chan_that, (
        f"Cửa đếm báo dang_chan={_cua()['dang_chan']} nhưng cổng 13 trả {r.status_code}: {r.text}")


def test_d2_cua_nhap_loai_the_va_bang_luat_phai_di_cung_nhau():
    """Canh bằng cây cú pháp, không tìm chuỗi – chú thích trong tệp cũng chứa đúng mấy chữ ấy.

    Thêm một loại thẻ ở cửa nhập mà không khai phạm vi cho nó là mở một loại hành nghề mà hệ thống
    không biết nó được nhận chuyến gì. Phép hỏi sẽ trả 'chưa kết luận được' mãi mãi, lặng lẽ.
    """
    import ast
    import inspect
    from pathlib import Path

    from app.api.v1 import huong_dan as HD
    cay = ast.parse(Path(inspect.getsourcefile(HD)).read_text(encoding="utf-8"))
    nhan = None
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.Compare) or not isinstance(nut.ops[0], ast.NotIn):
            continue
        if getattr(nut.left, "attr", "") != "the_loai":
            continue
        ve_phai = nut.comparators[0]
        if isinstance(ve_phai, (ast.Tuple, ast.List, ast.Set)):
            nhan = {e.value for e in ve_phai.elts if isinstance(e, ast.Constant)}
    assert nhan is not None, "Không tìm thấy cửa nhập loại thẻ trong huong_dan.py"
    khai = {d["loai_the"] for d in PHAM_VI_THE}
    thieu = {x for x in nhan if x} - khai
    assert not thieu, f"Cửa nhập nhận loại thẻ chưa khai phạm vi hành nghề: {thieu}"


def test_d3_luat_o_lai_trong_models_khong_chui_vao_than_ham():
    """Viết cứng danh sách loại chuyến vào thân `pham_vi_the` là giấu luật vào mã: người sửa luật
    sau này sẽ sửa bảng ở `models/hr.py` và tưởng mình đã sửa xong."""
    import ast
    import inspect
    from pathlib import Path

    from app.services import hr as HRS
    cay = ast.parse(Path(inspect.getsourcefile(HRS)).read_text(encoding="utf-8"))
    than = next((n for n in ast.walk(cay)
                 if isinstance(n, ast.FunctionDef) and n.name == "pham_vi_the"), None)
    assert than is not None, "Không còn hàm pham_vi_the trong services/hr.py"
    from app.models.core import TOUR_TYPES
    for nut in ast.walk(than):
        if isinstance(nut, (ast.Tuple, ast.List, ast.Set)):
            hang = {e.value for e in nut.elts if isinstance(e, ast.Constant)}
            la = hang & set(TOUR_TYPES)
            assert not la, f"Thân hàm pham_vi_the viết cứng loại chuyến: {la}"
