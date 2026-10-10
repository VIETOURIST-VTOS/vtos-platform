# -*- coding: utf-8 -*-
"""ĐỢT F1 — NGƯỠNG DUYỆT CHI: dưới mốc TGĐ, từ mốc trở lên CHỦ TỊCH.

Chủ tịch chốt bằng lời: "dưới 100 triệu TGĐ, từ 100 triệu Chủ tịch". Tệp này canh CẤU TRÚC của luật
ấy, và canh cả việc mã KHÔNG tự điền con số 100.000.000 vào đâu.

──────────────────────────────────────────────────────────────────────────────────────────────
BA CHỖ HỎNG ĐO ĐƯỢC TRƯỚC KHI VIẾT, trên `origin/main` tại 0779e79
──────────────────────────────────────────────────────────────────────────────────────────────

(a) CHỦ TỊCH BỊ TỪ CHỐI ở chính bước duyệt. `services/ops.py` dòng 428–430:
        if u.role == "tgd": r.signed_tgd = True
        elif u.role == "chutich" and r.two_signatures: r.signed_chutich = True
        else: raise ValueError("Chỉ TGĐ (và Chủ tịch khi cần 2 chữ ký) duyệt chi")
    Khoản 300 triệu TRONG dự toán có `two_signatures = False`, nên Chủ tịch rơi vào `else`. Còn TGĐ
    thì ký được. Đúng ngược cả hai đầu — nên F1 đổi AI ĐƯỢC BẤM, không phải thêm một phép kiểm.
    Canh ở `test_f1_c*`.

(b) HÀNG ĐỢI CỦA CHỦ TỊCH LỌC SAI CỜ. `services/dashboard.py` dòng 82 lọc `two_signatures == True`,
    tức chỉ khoản NGOÀI DỰ TOÁN. Khoản từ mốc trở lên không hiện trên bàn ông: "cửa mở, biển đề
    đóng" lần thứ ba, lần này trên một hàng đợi. Canh ở `test_f1_e*`.

(c) MỘT NHÃN NÓI SAI TRÊN MÀN HÌNH. `api/v1/ops.py` dòng 312 viết "≥ hạn mức → 2 chữ ký" cho cờ
    `two_signatures`, mà cờ ấy nghĩa là NGOÀI DỰ TOÁN. Canh ở `test_f1_f*`.

──────────────────────────────────────────────────────────────────────────────────────────────
HAI LÝ DO PHẢI ĐỨNG RIÊNG — và đây là phép thử dễ bị sửa sai nhất về sau
──────────────────────────────────────────────────────────────────────────────────────────────

`two_signatures` chỉ được bật ở MỘT chỗ trong cả kho: `ops.py` dòng 353, cho `chi_tour`/`tam_ung`
vượt dự toán tour. Nó nghĩa NGOÀI DỰ TOÁN và chỉ nghĩa thế. Mượn lại cờ ấy cho mốc 100 triệu thì
mã ngắn hơn và mọi phép thử ở đây vẫn xanh — nhưng từ đó không ai đọc được một hồ sơ hai chữ ký là
vì vượt dự toán hay vì lớn tiền. `test_f1_d2` dựng đúng cái bẫy: một khoản DƯỚI mốc mà ngoài dự
toán vẫn phải cần cả hai chữ ký.

MỐC KHÔNG NẰM TRONG MÃ. Tham số `nguong_chu_tich_duyet_chi` để RỖNG trong bộ mặc định và mở bằng
hai chữ ký. `test_f1_a2` canh điều ấy, và nó sẽ ĐỎ nếu ai đó "cho tiện" điền 100000000 vào
`DEFAULT_PARAMS` — vì `seed_params` nạp mọi khóa với `status="active"` kèm hai chữ ký mang tên
"seed", tức ký thay Chủ tịch bằng một dòng mã.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_f1ngc.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_f1ngc.db"):
    os.remove("test_f1ngc.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import Param, User  # noqa: E402
from app.models.ops import PaymentRequest  # noqa: E402
from app.services import dashboard as DB  # noqa: E402
from app.services import ops as O  # noqa: E402
from app.services import rules as R  # noqa: E402

client = TestClient(app)
TOK = {}

MOC = 100_000_000.0


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def login(u: str) -> dict:
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Dụng cụ: bật/tắt mốc. KHÔNG đi qua cửa `POST /params` vì cửa ấy đòi hai chữ ký và `sign_param`
# chặn người trình tự ký — đúng luật, nhưng ở đây thứ cần đo là HÀNH VI KHI ĐÃ CÓ MỐC. Ghi thẳng
# một dòng `active` là dựng sẵn trạng thái "đã ký", không phải đi vòng qua cửa.
# ─────────────────────────────────────────────────────────────────────────────────────────────
def dat_moc(gia_tri: str | None):
    db = SessionLocal()
    try:
        for p in db.execute(select(Param).where(Param.key == O.NGUONG_CHU_TICH_KEY,
                                                Param.proposed_by == "phep_thu")).scalars().all():
            db.delete(p)
        if gia_tri is not None:
            db.add(Param(key=O.NGUONG_CHU_TICH_KEY, value=gia_tri,
                         label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                         effective_from=date(2026, 9, 2), source="phép thử F1",
                         status="active", signed_chutich=True, signed_tgd=True,
                         proposed_by="phep_thu"))
        db.commit()
    finally:
        db.close()
    R.clear_param_cache()


@pytest.fixture()
def co_moc():
    dat_moc(str(int(MOC)))
    yield MOC
    dat_moc(None)


@pytest.fixture()
def khong_moc():
    dat_moc(None)
    yield
    dat_moc(None)


def _lap(tien: float, nguoi: str = "cntt", **kw):
    body = {"category": "hanh_chinh", "supplier_name": "Cong ty ABC",
            "supplier_tax_code": "0301234567", "amount": tien,
            "description": "Chi hanh chinh thang " + f"{date.today():%m}",
            "has_document": True, "document_ref": "HD-01", **kw}
    return client.post("/api/v1/payment-requests", json=body, headers=login(nguoi))


def _buoc(rid: int, hanh_dong: str, nguoi: str):
    return client.post(f"/api/v1/payment-requests/{rid}/step",
                       json={"action": hanh_dong}, headers=login(nguoi))


def _den_cho_duyet(tien: float, **kw) -> int:
    """Đưa một hồ sơ `hanh_chinh` tới đúng bước chờ duyệt. `hanh_chinh` không gắn mã tour, nên
    `over_budget`/`two_signatures` đứng im — tập trung đo đúng mốc tiền."""
    r = _lap(tien, **kw)
    assert r.status_code == 201, r.text
    rid = r.json()["request"]["id"]
    assert _buoc(rid, "confirm", "hcns").status_code == 200
    assert _buoc(rid, "check", "ketoan").status_code == 200
    return rid


def _ho_so(rid: int) -> PaymentRequest:
    db = SessionLocal()
    try:
        return db.get(PaymentRequest, rid)
    finally:
        db.close()


def _dat_hai_chu_ky(rid: int):
    """Bật cờ NGOÀI DỰ TOÁN trên một hồ sơ `hanh_chinh`. Cờ ấy chỉ được mã bật cho
    `chi_tour`/`tam_ung` vượt dự toán tour; ở đây bật tay để đo rằng mốc tiền CỘNG THÊM vào nó."""
    db = SessionLocal()
    try:
        r = db.get(PaymentRequest, rid)
        r.over_budget, r.two_signatures = True, True
        db.commit()
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. Mốc là CHỮ KÝ, không phải mã
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_a1_khoa_co_mat_trong_bo_tham_so():
    """`propose_param` đòi khóa đã có ít nhất một dòng. Khóa chưa khai là khóa KHÔNG NHẬP ĐƯỢC —
    đúng chỗ hỏng PQ-4b của hai mốc vận hành thật, 11/9/2026."""
    co = [d for d in R.DEFAULT_PARAMS if d[0] == O.NGUONG_CHU_TICH_KEY]
    assert co, (f"khong co cua nao nhap duoc `{O.NGUONG_CHU_TICH_KEY}`. Khoa phai nam trong "
                "rules.DEFAULT_PARAMS de seed_params dung mot dong, roi POST /params moi nhan.")


def test_f1_a2_gia_tri_mac_dinh_PHAI_RONG():
    """HÀNG RÀO QUAN TRỌNG NHẤT CỦA TỆP NÀY.

    `seed_params` nạp mọi khóa trong `DEFAULT_PARAMS` với `status="active"` và CẢ HAI chữ ký mang
    tên "seed". Điền sẵn 100000000 vào đó là hệ thống tự chốt một mốc tiền bằng một dòng mã, và
    con số ấy đứng y như đã có hai người ký. Đỏ ở đây KHÔNG phải lỗi mã — nó nghĩa là có người vừa
    ký thay Chủ tịch.
    """
    d = [x for x in R.DEFAULT_PARAMS if x[0] == O.NGUONG_CHU_TICH_KEY][0]
    assert d[1] == "", (f"`{O.NGUONG_CHU_TICH_KEY}` dang mang gia tri mac dinh {d[1]!r}. Moc tien "
                        "phan cap duyet phai de TRONG va mo bang hai chu ky tren man hinh Tham so.")


def test_f1_a3_khong_ai_go_cung_100_trieu_trong_ma():
    """Con số không được nằm trong mã nghiệp vụ — kể cả như một hằng số "dự phòng"."""
    import inspect
    for mo_dun in (O, DB):
        ma = inspect.getsource(mo_dun)
        for xau in ("100000000", "100_000_000"):
            assert xau not in ma, (f"{mo_dun.__name__} co go cung {xau}. Moc nay la mot CHU KY, "
                                   "khong phai mot hang so.")


def test_f1_a4_ten_khong_dung_tien_to_han_muc():
    """`han_muc_mkt` đã tồn tại với nghĩa khác hẳn. Hai cái tên gần nhau cho hai luật khác nhau là
    đúng cái bẫy đã phải trả giá một lần ở `so_tien_goc`."""
    assert not O.NGUONG_CHU_TICH_KEY.startswith("han_muc")
    assert O.NGUONG_CHU_TICH_KEY != "han_muc_mkt"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. Đọc mốc, và ba mốc tiền
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_b1_chua_ky_thi_doc_ra_None(khong_moc):
    """RỖNG đọc ra `None` = CHƯA CHỐT. Không được đọc ra 0, và tuyệt đối không được nổ ValueError:
    `get_param` làm `float("")` nên chỗ này phải dùng `get_param_text`."""
    db = SessionLocal()
    try:
        assert O.nguong_chu_tich_dang_hieu_luc(db) is None
    finally:
        db.close()


def test_f1_b2_ky_roi_thi_doc_ra_dung_so(co_moc):
    db = SessionLocal()
    try:
        assert O.nguong_chu_tich_dang_hieu_luc(db) == MOC
    finally:
        db.close()


@pytest.mark.parametrize("tien,tren_moc", [
    (99_999_999, False),      # ngay dưới mốc một đồng
    (100_000_000, True),      # ĐÚNG mốc — "từ 100 triệu" nghĩa là TÍNH CẢ mốc
    (100_000_001, True),      # ngay trên mốc một đồng
])
def test_f1_b3_ba_moc_tien(co_moc, tien, tren_moc):
    """Ba mốc, và mốc giữa là mốc dễ sai: `>` thay vì `>=` thì đúng 100 triệu tụt xuống cấp TGĐ."""
    rid = _den_cho_duyet(tien)
    db = SessionLocal()
    try:
        cd = O.cap_duyet(db, db.get(PaymentRequest, rid))
    finally:
        db.close()
    assert cd["tren_moc"] is tren_moc, f"{tien:,.0f}d: tren_moc doc ra {cd['tren_moc']}"
    assert cd["can_chutich"] is tren_moc
    assert cd["can_tgd"] is (not tren_moc)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. Ai được bấm — chỗ hỏng (a)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_c1_chu_tich_duyet_duoc_khoan_tu_moc_tro_len(co_moc):
    """CHỖ HỎNG (a). Trước F1, khoản 300 triệu trong dự toán làm Chủ tịch rơi vào `else` và nhận
    "Chỉ TGĐ (và Chủ tịch khi cần 2 chữ ký) duyệt chi"."""
    rid = _den_cho_duyet(300_000_000)
    r = _buoc(rid, "approve", "chutich")
    assert r.status_code == 200, ("Chu tich khong duyet duoc khoan 300 trieu trong du toan - ma "
                                 f"dang noi nguoc luat. {r.text}")
    assert _ho_so(rid).status == "cho_chi"
    assert _ho_so(rid).signed_chutich is True


def test_f1_c2_tgd_KHONG_duyet_duoc_khoan_tu_moc_tro_len(co_moc):
    """Mặt còn lại của cùng chỗ hỏng: trước F1 TGĐ ký được MỌI khoản."""
    rid = _den_cho_duyet(250_000_000)
    r = _buoc(rid, "approve", "tgd")
    assert r.status_code == 422, "TGD van duyet duoc khoan tu moc tro len - moc tien chua co hieu luc"
    assert "Chủ tịch" in r.text and "250,000,000" in r.text, (
        "loi bao phai noi ro so tien, moc, va AI duyet - nguoi doc se di go dung nguoi ay. "
        f"Dang la: {r.text}")
    assert _ho_so(rid).status == "cho_duyet", "bi tu choi ma trang thai van bi doi"


def test_f1_c3_tgd_duyet_duoc_khoan_duoi_moc(co_moc):
    rid = _den_cho_duyet(99_000_000)
    assert _buoc(rid, "approve", "tgd").status_code == 200
    assert _ho_so(rid).status == "cho_chi"


def test_f1_c4_chu_tich_toan_quyen_van_ky_duoc_khoan_duoi_moc(co_moc):
    """Luật toàn quyền 06/9/2026 không bị mốc tiền thu hẹp. Chữ ký ghi vào ô TGĐ vì đó là CẤP
    DUYỆT của khoản này; còn ai bấm thì nhật ký kiểm toán ghi tên."""
    rid = _den_cho_duyet(10_000_000)
    assert _buoc(rid, "approve", "chutich").status_code == 200
    h = _ho_so(rid)
    assert h.status == "cho_chi" and h.signed_tgd is True and h.approved_by == "chutich"


def test_f1_c5_vai_khac_khong_duyet_duoc(co_moc):
    rid = _den_cho_duyet(5_000_000)
    assert _buoc(rid, "approve", "ketoan").status_code == 422


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. Ngoài dự toán là một lý do KHÁC, và nó CỘNG THÊM
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_d1_tu_moc_tro_len_ma_NGOAI_DU_TOAN_can_ca_hai(co_moc):
    rid = _den_cho_duyet(400_000_000)
    _dat_hai_chu_ky(rid)
    assert _buoc(rid, "approve", "chutich").status_code == 200
    assert _ho_so(rid).status == "cho_duyet", "mot chu ky da du - co ngoai du toan bi bo qua"
    assert _buoc(rid, "approve", "tgd").status_code == 200
    assert _ho_so(rid).status == "cho_chi"


def test_f1_d2_DUOI_moc_ma_ngoai_du_toan_van_can_ca_hai(co_moc):
    """CÁI BẪY. Nếu ai đó "cho gọn" mà dùng lại `two_signatures` làm cờ mốc tiền, phép thử này đỏ:
    một khoản 20 triệu ngoài dự toán sẽ chỉ còn cần một chữ ký TGĐ."""
    rid = _den_cho_duyet(20_000_000)
    _dat_hai_chu_ky(rid)
    assert _buoc(rid, "approve", "tgd").status_code == 200
    assert _ho_so(rid).status == "cho_duyet", (
        "khoan DUOI moc nhung NGOAI DU TOAN da di qua voi mot chu ky - hai ly do dang bi tron vao "
        "mot co")
    assert _buoc(rid, "approve", "chutich").status_code == 200
    assert _ho_so(rid).status == "cho_chi"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# E. RỖNG thì CHẶN, và chỗ tắc phải ĐẾM ĐƯỢC — chỗ hỏng (b)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_e1_chua_chot_moc_thi_khong_duyet_duoc(khong_moc):
    """Rỗng không phải "không có mốc". Một công tắc an toàn hỏng phải hỏng về phía ĐÓNG."""
    rid = _den_cho_duyet(30_000_000)
    for vai in ("tgd", "chutich"):
        r = _buoc(rid, "approve", vai)
        assert r.status_code == 422, f"{vai} duyet duoc trong khi chua ai chot moc"
        assert O.NGUONG_CHU_TICH_KEY in r.text, (
            "loi bao phai noi ro TEN THAM SO va noi phai ky. Dang la: " + r.text)
    assert _ho_so(rid).status == "cho_duyet"


def test_f1_e2_cua_LAP_van_mo_khi_chua_chot_moc(khong_moc):
    """Chặn ở cửa lập là bắt người lập chịu một việc chưa ký của cấp trên — và không lập được thì
    không có gì đếm ra để ai đó đi ký. Nhưng nhãn phải nói thẳng là hồ sơ sẽ nằm chờ."""
    r = _lap(40_000_000)
    assert r.status_code == 201, r.text
    assert "CHƯA CHỐT NGƯỠNG" in r.json()["message"], (
        "cua lap im lang ve viec ho so se nam cho - dung kieu hong im lang ma M5 cua Marketing da "
        f"phai dung mot cai mieng de chong. Loi bao dang la: {r.json()['message']}")
    assert r.json()["request"]["nguong_duyet_ap_dung"] is None


def test_f1_e3_hang_doi_chu_tich_co_khoan_tu_moc_tro_len(co_moc):
    """CHỖ HỎNG (b). Trước F1 hàng đợi lọc `two_signatures == True`, nên khoản 500 triệu TRONG dự
    toán không hiện ở đâu trên bàn Chủ tịch."""
    _den_cho_duyet(500_000_000)
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == "chutich")).scalars().first()
        ap = DB.build(db, u)["approvals"]
    finally:
        db.close()
    dong = [a for a in ap if "chờ CHỦ TỊCH ký" in a["label"]]
    assert dong, "hang doi cua Chu tich khong co dong nao cho khoan tu moc tro len"


def test_f1_e4_ho_so_tac_vi_chua_chot_moc_phai_dem_duoc(khong_moc):
    """Lọc chúng khỏi hàng đợi mà không nói gì là làm một đống việc tắc nghẽn thành vô hình."""
    _den_cho_duyet(60_000_000)
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == "chutich")).scalars().first()
        ap = DB.build(db, u)["approvals"]
    finally:
        db.close()
    tac = [a for a in ap if "KHÔNG DUYỆT ĐƯỢC" in a["label"]]
    assert tac, "khong co dong nao dem so ho so dang tac vi chua chot nguong"
    assert tac[0]["href"] == "/params", "dong tac phai tro sang man hinh Tham so - noi co the xu"


def test_f1_e5_chu_tich_VAN_THAY_khoan_duoi_moc(co_moc):
    """Chủ tịch nói rõ 10/10/2026: "dưới 100 triệu TGĐ duyệt nhưng Chủ tịch vẫn phải thấy".

    Bản đầu của đợt này lọc hẳn khoản dưới mốc khỏi bàn ông — đổi một chỗ hỏng thành chỗ hỏng
    ngược lại: trước thì ông không thấy khoản LỚN, sau thì không thấy khoản NHỎ.

    Và nó phải là MỘT DÒNG RIÊNG nói rõ ĐỂ XEM: gộp vào ô "chờ Chủ tịch ký" thì con số ấy thành
    một việc đang chờ chính ông, ông bấm vào mà không ký được khoản nào.
    """
    _den_cho_duyet(7_000_000)
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == "chutich")).scalars().first()
        ap = DB.build(db, u)["approvals"]
    finally:
        db.close()
    xem = [a for a in ap if "để xem" in a["label"]]
    assert xem, ("ban Chu tich KHONG thay khoan duoi moc. Chu tich chot: duoi moc TGD duyet nhung "
                 "Chu tich van phai thay.")
    ky = [a for a in ap if "chờ CHỦ TỊCH ký" in a["label"]]
    for d in ky:
        assert "để xem" not in d["label"], "tron hai o lam nhau: viec phai ky va viec chi de xem"


def test_f1_e6_tgd_VAN_THAY_khoan_tu_moc_tro_len_ma_khong_bam_duoc(co_moc):
    """Chiều ngược lại, Chủ tịch chốt cùng ngày: "trên 100 triệu TGĐ cũng vẫn thấy, nhưng không
    bấm duyệt". Mốc chia QUYỀN BẤM, không chia TẦM NHÌN.

    Hai điều phải đúng CÙNG LÚC, và đây là chỗ dễ làm nửa vời nhất: TGĐ THẤY con số ấy trên bàn
    mình, và TGĐ KHÔNG ký được nó. Thấy mà ký được là mất mốc; ký không được mà không thấy là
    mất tầm nhìn.
    """
    rid = _den_cho_duyet(900_000_000)
    db = SessionLocal()
    try:
        u = db.execute(select(User).where(User.username == "tgd")).scalars().first()
        ap = DB.build(db, u)["approvals"]
    finally:
        db.close()
    xem = [a for a in ap if "để xem" in a["label"]]
    assert xem, ("ban TGD KHONG thay khoan tu moc tro len. Chu tich chot: tren moc TGD cung van "
                 "thay, chi la khong bam duyet.")
    assert _buoc(rid, "approve", "tgd").status_code == 422, (
        "TGD thay VA ky duoc - thay thi dung, ky duoc thi mat moc")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# F. Nhãn trên màn hình — chỗ hỏng (c)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_f1_nhan_cua_lap_noi_dung_ai_duyet(co_moc):
    tren = _lap(200_000_000).json()
    assert "CHỦ TỊCH" in tren["message"] or "Chủ tịch" in tren["message"], tren["message"]
    duoi = _lap(2_000_000).json()
    assert "TGĐ" in duoi["message"], duoi["message"]


def test_f1_f2_nhan_khong_con_cau_han_muc_2_chu_ky(co_moc):
    """Câu "≥ hạn mức → 2 chữ ký" gắn vào cờ NGOÀI DỰ TOÁN là một nhãn nói sai."""
    import inspect
    from app.api.v1 import ops as AO
    # Bỏ dòng chú thích trước khi soi: bản vá CỐ Ý trích lại nguyên văn câu cũ vào chú thích để
    # người đọc sau thấy nó sai ở đâu. Soi cả tệp thì chính lời trích làm phép thử đỏ — phép thử
    # phải soi MÃ ĐANG CHẠY, không soi lời kể. (Bản 1 của phép thử này đỏ đúng vì vậy.)
    ma = chr(10).join(l for l in inspect.getsource(AO).splitlines() if not l.lstrip().startswith("#"))
    assert "≥ hạn mức → 2 chữ ký" not in ma, (
        "nhan cu van con: no viet 'han muc' cho co `two_signatures`, ma co ay nghia NGOAI DU TOAN")


def test_f1_f3_dong_ai_bam_tiep_noi_dung_nguoi(co_moc):
    rid = _den_cho_duyet(150_000_000)
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    h = [x for x in ds if x["id"] == rid][0]
    assert "Chủ tịch" in h["next"], f"dong 'ai bam tiep' chi sai nguoi: {h['next']}"
    assert h["nguong_duyet_ap_dung"] == MOC


# ═════════════════════════════════════════════════════════════════════════════════════════════
# F4–F6. Màn hình vẽ nút theo MÁY CHỦ, không tự suy
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_f4_vai_ky_duoc_dung_hai_phia_moc(co_moc):
    """`web/app/expenses/page.tsx` trước đợt này tự suy cấp duyệt bằng
    `role === "tgd" || (role === "chutich" && r.two_signatures)` — đúng cái cờ sai F1 vừa sửa ở
    máy chủ. Nên máy chủ TRẢ RA danh sách vai và màn hình chỉ đọc."""
    rid_t = _den_cho_duyet(220_000_000)
    rid_d = _den_cho_duyet(8_000_000)
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    h = {x["id"]: x for x in ds}
    assert h[rid_t]["vai_ky_duoc"] == ["chutich"], h[rid_t]["vai_ky_duoc"]
    assert h[rid_d]["vai_ky_duoc"] == ["tgd"], (
        "duoi moc ma danh sach co `chutich` — man hinh se moi Chu tich bam, trong khi Chu tich "
        f"chi phai THAY. Dang la: {h[rid_d]['vai_ky_duoc']}")


def test_f1_f5_chua_chot_moc_thi_danh_sach_vai_RONG(khong_moc):
    """Rỗng = KHÔNG AI bấm được lúc này. Màn hình không vẽ nút, và dòng tắc trên bàn Chủ tịch
    mới là chỗ nói ra vì sao."""
    rid = _den_cho_duyet(12_000_000)
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    h = [x for x in ds if x["id"] == rid][0]
    assert h["vai_ky_duoc"] == []


def test_f1_f6_ngoai_du_toan_thi_ca_hai_vai_co_nut(co_moc):
    rid = _den_cho_duyet(15_000_000)
    _dat_hai_chu_ky(rid)
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    h = [x for x in ds if x["id"] == rid][0]
    assert set(h["vai_ky_duoc"]) == {"chutich", "tgd"}, h["vai_ky_duoc"]


def test_f1_f7_marketing_van_la_mot_vai(co_moc):
    r = client.post("/api/v1/payment-requests", json={
        "category": "marketing", "marketing_muc": "quang_cao", "supplier_name": "Meta",
        "supplier_tax_code": "0301234567", "amount": 700_000_000,
        "description": "Quang cao lon", "has_document": True, "document_ref": "BG-09",
    }, headers=login("cntt"))
    rid = r.json()["request"]["id"]
    assert _buoc(rid, "check", "ketoan").status_code == 200
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    h = [x for x in ds if x["id"] == rid][0]
    assert h["vai_ky_duoc"] == ["ptgd_mkt"], (
        "khoan Marketing 700 trieu bi moc tien keo vao — Marketing mot chu ky o moi muc tien")


def test_f1_f8_man_hinh_khong_con_tu_suy(co_moc):
    """Canh chính tệp giao diện: nó phải ĐỌC `vai_ky_duoc`, không dựng lại luật bằng tay."""
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
                      "web", "app", "expenses", "page.tsx")
    assert _os.path.exists(p), p
    ma = chr(10).join(l for l in open(p, encoding="utf-8").read().splitlines()
                      if not l.lstrip().startswith("//"))
    assert "vai_ky_duoc" in ma, "man hinh khong doc `vai_ky_duoc` tu may chu"
    assert 'role === "chutich" && r.two_signatures' not in ma, (
        "man hinh van tu suy cap duyet tu co `two_signatures` — co ay nghia NGOAI DU TOAN")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# G. Mốc ghi XUỐNG hồ sơ — đổi tham số không đổi cấp duyệt của hồ sơ đã trình
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_g1_doi_tham_so_sau_do_khong_doi_cap_duyet_ho_so_da_trinh(co_moc):
    """Nếu `cap_duyet` đọc tham số thay vì đọc ô trên hồ sơ, phép thử này đỏ: hồ sơ 150 triệu đã
    trình theo mốc 100 triệu sẽ TỰ TỤT xuống cấp TGĐ khi ai đó nâng mốc lên 500 triệu — không ai
    bấm gì và không dòng nhật ký nào ghi lại."""
    rid = _den_cho_duyet(150_000_000)
    assert _ho_so(rid).nguong_duyet_ap_dung == MOC
    dat_moc("500000000")
    try:
        r = _buoc(rid, "approve", "tgd")
        assert r.status_code == 422, ("nang moc len 500 trieu da lam ho so 150 trieu tut xuong cap "
                                      "TGD - cap duyet dang doc tu tham so, khong tu ho so")
        assert _buoc(rid, "approve", "chutich").status_code == 200
    finally:
        dat_moc(str(int(MOC)))


def test_f1_g2_ho_so_cu_khong_co_o_moc_thi_ghi_xuong_luc_duyet(co_moc):
    """Hồ sơ lập TRƯỚC bản nâng cấp này rỗng ô mốc. Lấy mốc đang hiệu lực là sự thật tốt nhất đọc
    được, và phải ghi xuống để lần đọc sau không đổi nữa."""
    rid = _den_cho_duyet(120_000_000)
    db = SessionLocal()
    try:
        db.get(PaymentRequest, rid).nguong_duyet_ap_dung = None
        db.commit()
    finally:
        db.close()
    assert _buoc(rid, "approve", "chutich").status_code == 200
    assert _ho_so(rid).nguong_duyet_ap_dung == MOC, "duyet xong ma khong ghi moc xuong ho so"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# H. Marketing đứng ngoài
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_h1_khoan_marketing_khong_ghi_o_moc(co_moc):
    """Marketing đi một chữ ký P.TGĐ Marketing cho MỌI mức tiền (23/9/2026). Điền một con số vào ô
    mốc của nó là mời người đọc sau này hiểu sai."""
    r = client.post("/api/v1/payment-requests", json={
        "category": "marketing", "marketing_muc": "quang_cao", "supplier_name": "Meta",
        "supplier_tax_code": "0301234567", "amount": 800_000_000,
        "description": "Quang cao", "has_document": True, "document_ref": "BG-01",
    }, headers=login("cntt"))
    assert r.status_code == 201, r.text
    d = r.json()["request"]
    assert d["nguong_duyet_ap_dung"] is None
    assert d["two_signatures"] is False
    # Hồ sơ Marketing vào THẲNG bước Kế toán (bỏ bước bộ phận xác nhận, 23/9/2026), nên dòng "ai
    # bấm tiếp" lúc này là Kế toán. Đi thêm một bước rồi mới đòi đúng tên người duyệt.
    assert d["status"] == "cho_kt"
    assert _buoc(d["id"], "check", "ketoan").status_code == 200
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    h = [x for x in ds if x["id"] == d["id"]][0]
    assert "P.TGĐ Marketing" in h["next"], h["next"]
    assert h["nguong_duyet_ap_dung"] is None


def test_f1_h2_marketing_khong_bi_chan_khi_chua_chot_moc(khong_moc):
    """Chưa chốt mốc KHÔNG được làm đứng luồng Marketing — mốc không áp vào nó."""
    r = client.post("/api/v1/payment-requests", json={
        "category": "marketing", "marketing_muc": "noi_dung", "supplier_name": "Meta",
        "supplier_tax_code": "0301234567", "amount": 3_000_000,
        "description": "Noi dung", "has_document": True, "document_ref": "BG-02",
    }, headers=login("cntt"))
    rid = r.json()["request"]["id"]
    assert _buoc(rid, "check", "ketoan").status_code == 200
    assert _buoc(rid, "approve", "ptgd.mkt").status_code == 200
    assert _ho_so(rid).status == "cho_chi"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# I. Cột và bản nâng cấp
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_i1_cot_nullable_khong_mac_dinh():
    """K2: RỖNG khác 0. Hàng nghìn hồ sơ đã có trong bảng đều lập trước luật này — điền một con số
    vào đó là bịa ra một cấp duyệt chưa ai quyết."""
    c = PaymentRequest.__table__.c["nguong_duyet_ap_dung"]
    assert c.nullable is True
    assert c.default is None and c.server_default is None


def test_f1_i2_ban_nang_cap_mot_dau():
    import os as _os
    import re as _re
    d = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "alembic", "versions")
    revs, downs = {}, set()
    for t in _os.listdir(d):
        if not t.endswith(".py"):
            continue
        s = open(_os.path.join(d, t), encoding="utf-8").read()
        m = _re.search(r"^revision\b[^=]*=\s*[\"\']([^\"\']+)", s, _re.M)
        n = _re.search(r"^down_revision\b[^=]*=\s*(.+)$", s, _re.M)
        if m:
            revs[m.group(1)] = t
        if n:
            for x in _re.findall(r"[\"\']([^\"\']+)[\"\']", n.group(1)):
                downs.add(x)
    dau = [r for r in revs if r not in downs]
    assert len(dau) == 1, f"mach nang cap co {len(dau)} dau: {[(r, revs[r]) for r in dau]}"
    assert "f1n7c3e9b2a54" in revs, "khong thay ban nang cap cua dot F1"
