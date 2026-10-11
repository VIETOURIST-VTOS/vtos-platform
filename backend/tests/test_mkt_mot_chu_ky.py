# -*- coding: utf-8 -*-
"""CHI MARKETING ĐI HAI BƯỚC — Chủ tịch chốt 10/10/2026 (Đợt F1b).

──────────────────────────────────────────────────────────────────────────────────────────────
LUẬT, VÀ LỊCH SỬ CỦA NÓ
──────────────────────────────────────────────────────────────────────────────────────────────

  Bước 1 — P.TGĐ Marketing duyệt NỘI DUNG / KẾ HOẠCH / NGÂN SÁCH, ở bước `confirm`.
  Bước 2 — LỆNH CHI, ở bước `approve`, theo mốc `nguong_chu_tich_duyet_chi`: dưới mốc TGĐ ký,
           từ mốc trở lên Chủ tịch ký.

Tệp này TỪNG mang tên nội dung ngược lại. Ngày 23/9/2026 Chủ tịch chốt "Marketing đi MỘT chữ ký
của P.TGĐ ở mọi mức tiền", xác nhận lại 24/9, và tệp này được viết để canh đúng luật ấy. Ngày
10/10/2026 Chủ tịch đảo lại: hai lần duyệt, hai người khác nhau bấm.

TÊN TỆP GIỮ NGUYÊN (`test_mkt_mot_chu_ky.py`) dù nội dung đã đảo. Đổi tên tệp phép thử là làm
đứt lịch sử của nó trong `git log --follow` và làm mọi đường dẫn đang trỏ tới nó (cửa hẹp CI, các
dòng giữ chỗ, lời nhắn ghi mã cũ) trỏ vào hư không. Cái tên nay là một cái mốc lịch sử, không
phải một lời mô tả — và dòng này là chỗ nói ra điều đó.

VÌ SAO BẢN VÁ GỠ CHỨ KHÔNG THÊM. Để làm được "một chữ ký", mã 23/9 CẮT BỎ bước bộ phận của
Marketing (`r.status = "cho_kt"` ngay lúc lập), lý do khi ấy: người xác nhận bộ phận của Marketing
CHÍNH LÀ P.TGĐ, mà ông đang ký ở cuối, nên giữ cả hai bước là bắt một người bấm hai lần. Nay hai
bước do hai người bấm, nên lý do ấy hết hiệu lực và việc phải làm là GỠ ngoại lệ, không phải thêm
một trạng thái mới.

──────────────────────────────────────────────────────────────────────────────────────────────
NĂM THỨ KHÔNG ĐỔI QUA CẢ HAI LẦN ĐẢO LUẬT — mỗi thứ một phép thử
──────────────────────────────────────────────────────────────────────────────────────────────

  M1  Kế toán vẫn kiểm chứng từ và mã số thuế trước khi chi
  M2  cờ `over_budget` vẫn bật và vẫn ghi vào mô tả
  M3  P.TGĐ Marketing KHÔNG lập hồ sơ
  M4  người lập không tự ký — kể cả Chủ tịch toàn quyền
  M5  vai `ptgd_mkt` rỗng thì hồ sơ nằm chờ, và hệ thống phải NÓI RA

M5 nay đổi CHỖ ĐỨNG chứ không mất: vai rỗng làm hồ sơ đứng ở bước `cho_tp` (xác nhận nội dung),
không phải `cho_duyet`. Một lời báo chỉ sai bước là lời báo đẩy người đọc đi tìm nhầm chỗ.

M2 thì đổi RĂNG: từ 23/9 tới 10/10, `over_budget` chỉ còn NÓI chứ không CHẶN. Nay khoản ngoài dự
toán đi qua nhánh chung, và nhánh chung đòi CẢ HAI chữ ký (cổng 15) — nên nó có răng trở lại.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_mkt1ck.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_mkt1ck.db"):
    os.remove("test_mkt1ck.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import Param, User  # noqa: E402
from app.services import ops as O  # noqa: E402
from app.services import rules as R  # noqa: E402

client = TestClient(app)
TOK = {}
MOC = 100_000_000.0


@pytest.fixture(scope="module", autouse=True)
def _startup():
    """Mở client theo kiểu ngữ cảnh để vòng đời ứng dụng chạy — đó là chỗ tạo bảng và nạp dữ liệu
    mẫu. Không có nó thì mọi truy vấn đều 'no such table: users'."""
    with TestClient(app) as c:
        global client
        client = c
        yield


@pytest.fixture(scope="module", autouse=True)
def _nguong_f1(_startup):
    """ĐỢT F1 — bối cảnh: công ty ĐÃ CHỐT ngưỡng duyệt chi.

    Từ F1, bước duyệt một đề nghị chi KHÔNG đi được khi tham số `nguong_chu_tich_duyet_chi` còn
    rỗng. Bộ mặc định cố ý để trống vì `seed_params` nạp mọi khóa kèm hai chữ ký mang tên "seed".
    Mốc 100 triệu ở đây là DỮ LIỆU CỦA PHÉP THỬ, không phải mốc đã ký của công ty.
    """
    db = SessionLocal()
    try:
        db.add(Param(key=O.NGUONG_CHU_TICH_KEY, value="100000000",
                     label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                     effective_from=date(2026, 9, 2), source="bối cảnh phép thử F1b",
                     status="active", signed_chutich=True, signed_tgd=True,
                     proposed_by="phep_thu"))
        db.commit()
    finally:
        db.close()
    R.clear_param_cache()
    yield


def login(u: str) -> dict:
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


def _lap(nguoi: str = "cntt", tien: float = 2_000_000, muc: str = "quang_cao", **kw):
    body = {"category": "marketing", "marketing_muc": muc, "supplier_name": "Meta",
            "supplier_tax_code": "0301234567", "amount": tien,
            "description": "Quang cao thang " + f"{date.today():%m}",
            "has_document": True, "document_ref": "BG-01", **kw}
    return client.post("/api/v1/payment-requests", json=body, headers=login(nguoi))


def _buoc(rid: int, hanh_dong: str, nguoi: str, ly_do: str = ""):
    return client.post(f"/api/v1/payment-requests/{rid}/step",
                       json={"action": hanh_dong, "reason": ly_do}, headers=login(nguoi))


def _ho_so(rid: int) -> dict:
    ds = client.get("/api/v1/payment-requests", headers=login("ketoan")).json()
    return [x for x in ds if x["id"] == rid][0]


def _ai_giu_vai():
    db = SessionLocal()
    try:
        return O.ai_duyet_duoc_mkt(db)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Luật chính — HAI BƯỚC
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_mk1_ho_so_bat_dau_o_buoc_xac_nhan_noi_dung():
    """Trước F1b hồ sơ Marketing vào THẲNG bước Kế toán. Nay nó bắt đầu ở `cho_tp`, và `cho_tp`
    chính là bước một: P.TGĐ Marketing duyệt nội dung."""
    d = _lap(tien=3_000_000).json()["request"]
    assert d["status"] == "cho_tp", (
        f"ho so Marketing van nhay coc qua buoc xac nhan noi dung, dang o {d['status']}")
    assert "P.TGĐ Marketing" in d["next"], d["next"]


def test_mk2_duoi_moc_thi_TGD_ky_lenh_chi():
    """Đường đi đầy đủ, dưới mốc: nhân viên lập → P.TGĐ MKT duyệt nội dung → Kế toán kiểm →
    TGĐ ký lệnh chi → sang Kế toán chi."""
    rid = _lap(tien=30_000_000, muc="noi_dung").json()["request"]["id"]
    assert _buoc(rid, "confirm", "ptgd.mkt").status_code == 200
    assert _ho_so(rid)["status"] == "cho_kt"
    assert _buoc(rid, "check", "ketoan").status_code == 200
    # P.TGĐ Marketing KHÔNG còn ký được lệnh chi — chữ ký của ông là bước một, đã bấm xong.
    assert _buoc(rid, "approve", "ptgd.mkt").status_code == 422, (
        "P.TGD Marketing van ky duoc lenh chi - luat mot chu ky chua duoc go")
    r = _buoc(rid, "approve", "tgd")
    assert r.status_code == 200, r.text
    h = _ho_so(rid)
    assert h["status"] == "cho_chi" and h["approved_by"] == "tgd"


def test_mk3_tu_moc_tro_len_thi_CHU_TICH_ky_lenh_chi():
    """200 triệu — trên mốc. Trước 10/10 khoản này chỉ cần một chữ ký P.TGĐ Marketing."""
    rid = _lap(tien=200_000_000, muc="noi_dung").json()["request"]["id"]
    assert _buoc(rid, "confirm", "ptgd.mkt").status_code == 200
    assert _buoc(rid, "check", "ketoan").status_code == 200
    assert _buoc(rid, "approve", "tgd").status_code == 422, (
        "TGD ky duoc khoan Marketing 200 trieu - moc tien chua ap vao Marketing")
    assert _buoc(rid, "approve", "chutich").status_code == 200
    assert _ho_so(rid)["status"] == "cho_chi"


def test_mk4_vai_ky_duoc_cua_marketing_theo_MOC_chu_khong_phai_ptgd_mkt():
    """Màn hình đọc `vai_ky_duoc` để vẽ nút. Nếu nó còn trả `ptgd_mkt` ở bước lệnh chi thì màn
    hình mời sai người bấm, và người ấy bấm vào nhận 422."""
    rid = _lap(tien=250_000_000).json()["request"]["id"]
    _buoc(rid, "confirm", "ptgd.mkt")
    _buoc(rid, "check", "ketoan")
    assert _ho_so(rid)["vai_ky_duoc"] == ["chutich"], _ho_so(rid)["vai_ky_duoc"]


# ─────────────────────────────────────────────────────────────────────────────────────────────
# M1–M5 — năm thứ không đổi qua cả hai lần đảo luật
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_mk5_ke_toan_van_kiem_chung_tu(_nguong_f1):
    """M1. Hai lần duyệt KHÔNG có nghĩa là bỏ bước kiểm chứng từ — đó là kiểm soát tài chính."""
    rid = _lap(tien=1_000_000, has_document=False).json()["request"]["id"]
    assert _buoc(rid, "confirm", "ptgd.mkt").status_code == 200
    r = _buoc(rid, "check", "ketoan")
    assert r.status_code == 422 and "chứng từ" in r.text


def test_mk6_ptgd_mkt_khong_lap_ho_so():
    """M3. Lý do đổi nhưng kết luận giữ: trước là vì ông ký cuối, nay là vì ông xác nhận bước
    một — lập rồi tự xác nhận vẫn là một người bấm hai lần."""
    r = _lap(nguoi="ptgd.mkt")
    assert r.status_code == 422, "P.TGD Marketing van lap duoc ho so"
    assert "không lập hồ sơ" in r.text


def test_mk7_nguoi_lap_khong_tu_ky_lenh_chi():
    """M4. Cửa lập đã chặn P.TGĐ MKT, nhưng Chủ tịch toàn quyền thì lập được — nên ranh giới này
    phải đứng ở bước KÝ mới kín.

    Trước F1b phép chặn này CHỈ nằm trong nhánh riêng của Marketing; gỡ nhánh ấy mà không bù vào
    là mở một lỗ. Đo kỹ thì nhánh chung vốn đã hở sẵn cho sáu loại chi còn lại, nên bản vá bù vào
    nhánh chung và bịt cho cả bảy loại cùng lúc.
    """
    rid = _lap(nguoi="chutich", tien=4_000_000).json()["request"]["id"]
    assert _buoc(rid, "confirm", "ptgd.mkt").status_code == 200
    assert _buoc(rid, "check", "ketoan").status_code == 200
    r = _buoc(rid, "approve", "chutich")
    assert r.status_code == 422 and "không tự ký" in r.text, (
        "nguoi lap tu ky duoc lenh chi cua chinh minh. " + r.text)


def test_mk8_vuot_du_toan_van_chi_NOI_chu_khong_CHAN():
    """M2 — và đây là chỗ em ĐÃ NÓI QUÁ, phép thử bắt được trước khi đẩy.

    Bản đầu của phép thử này đòi "răng mọc lại": khoản Marketing ngoài dự toán đi qua nhánh chung
    nên lại cần CẢ HAI chữ ký (cổng 15). ĐỎ. Vì `two_signatures` là một cờ RIÊNG, chỉ được bật ở
    đúng một chỗ trong cả kho — `chi_tour`/`tam_ung` vượt dự toán TOUR — và quyết định 23/9/2026
    đã gỡ nó khỏi Marketing. Đợt F1b gỡ ngoại lệ ở bước DUYỆT, không đụng tới chỗ bật cờ ấy.

    Nên hành vi thật hôm nay: khoản Marketing ngoài dự toán vẫn NÓI mà không CHẶN — cờ bật, mô tả
    ghi, màn hình hiện, và cấp duyệt vẫn chỉ theo MỐC TIỀN.

    CÒN LẠI CHO CHỦ TỊCH QUYẾT, ghi ra để không ai tưởng đã xong: có nối lại cổng 15 cho Marketing
    không. Không nối thì Marketing vẫn là một ngoại lệ, chỉ là một ngoại lệ nhỏ hơn: một khoản 20
    triệu ngoài dự toán của Điều hành cần hai chữ ký, cùng khoản ấy của Marketing chỉ cần TGĐ.
    Nối thì phải cân một hệ quả đo được: `over_budget` của Marketing còn bật cả khi CHƯA GẮN HẠNG
    MỤC, nên nối thẳng là mọi hồ sơ chưa gắn hạng mục đều cần hai chữ ký. Đó là một quyết định
    nghiệp vụ, không phải một dòng mã cho gọn.
    """
    d = _lap(tien=900_000_000, muc="quang_cao").json()["request"]
    assert d["over_budget"] is True, "khoan 900 trieu chac chan vuot du toan ma khong ghi co"
    assert "ngoài dự toán" in d["description"], "phai ghi vao mo ta de nguoi duyet doc thay"
    assert d["two_signatures"] is False, (
        "co hai chu ky da bat cho Marketing. Neu day la co y (noi lai cong 15) thi sua phep thu "
        "nay VA ghi can cu; neu khong thi mot thay doi nao do vua lam ro ri cho bat co.")
    rid = d["id"]
    _buoc(rid, "confirm", "ptgd.mkt")
    _buoc(rid, "check", "ketoan")
    # 900 triệu ≥ mốc → Chủ tịch ký, và chỉ Chủ tịch. Ngoài dự toán KHÔNG thêm chữ ký nào.
    assert _ho_so(rid)["vai_ky_duoc"] == ["chutich"], _ho_so(rid)["vai_ky_duoc"]
    assert _buoc(rid, "approve", "chutich").status_code == 200
    assert _ho_so(rid)["status"] == "cho_chi"


def test_mk9_han_muc_mkt_van_la_mot_tham_so_CHET():
    """`han_muc_mkt` = 5.000.000đ là phanh riêng của Marketing, gỡ ngày 23/9/2026. F1b KHÔNG nối
    lại nó: mốc tiền của Marketing từ nay là mốc CHUNG. Hai mốc cho cùng một câu hỏi là chỗ mà
    lần sửa sau sẽ lệch nhau."""
    import inspect
    ma = chr(10).join(l for l in inspect.getsource(O).splitlines()
                      if not l.lstrip().startswith("#"))
    assert "han_muc_mkt" not in ma, "`han_muc_mkt` da duoc noi lai vao ma nghiep vu"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# M5 — chỗ hỏng im lặng, nay ĐỔI CHỖ ĐỨNG
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_mk10_phai_co_nguoi_giu_vai_ptgd_mkt():
    """HÀNG RÀO. Đỏ ở đây KHÔNG phải lỗi mã: nghĩa là chưa gắn ai vào vai P.TGĐ Marketing, hoặc
    người đang giữ vai đã bị khoá. Cách xử là vào Quản trị hệ thống → Phân quyền gắn người."""
    assert _ai_giu_vai(), (
        "KHÔNG TÀI KHOẢN ĐANG HOẠT ĐỘNG NÀO GIỮ VAI P.TGĐ MARKETING (`ptgd_mkt`).\n"
        "Mọi hồ sơ chi Marketing dừng ở bước XÁC NHẬN NỘI DUNG của vai này. Vai rỗng nghĩa là mọi "
        "hồ sơ đứng im — và trên màn hình nó trông y hệt 'đang chờ bộ phận'.\n"
        "Cách xử: Quản trị hệ thống → Phân quyền → gắn một người vào vai `ptgd_mkt`.")


def test_mk11_vai_rong_thi_cua_lap_phai_noi_ra_DUNG_BUOC():
    """Hàng rào trên canh lúc dựng bản. Lúc CHẠY THẬT thì người lập phải được báo ngay, và lời
    báo phải nói đúng BƯỚC hồ sơ sẽ đứng — nay là bước xác nhận nội dung, không phải bước duyệt.
    Trả lại nguyên trạng ở cuối: phép thử không để lại dấu vết trong dữ liệu."""
    db = SessionLocal()
    try:
        for n in db.execute(select(User).where(User.role == O.VAI_DUYET_MKT,
                                               User.active.is_(True))).scalars().all():
            n.active = False
        db.commit()
    finally:
        db.close()
    try:
        assert _ai_giu_vai() == [], "khoa het roi ma van dem ra nguoi giu vai"
        kq = _lap(tien=1_500_000, muc="noi_dung").json()
        assert "CHƯA AI GIỮ VAI" in kq["message"], (
            "vai duyet dang rong ma cua lap khong noi gi. " + kq["message"])
        assert "xác nhận nội dung" in kq["message"], (
            "loi bao con chi sai BUOC - ho so nay se dung o buoc xac nhan noi dung, khong phai "
            "buoc duyet. " + kq["message"])
    finally:
        db = SessionLocal()
        try:
            for n in db.execute(select(User).where(User.role == O.VAI_DUYET_MKT)).scalars():
                n.active = True
            db.commit()
        finally:
            db.close()
    assert _ai_giu_vai(), "chua tra lai nguyen trang sau phep thu"
