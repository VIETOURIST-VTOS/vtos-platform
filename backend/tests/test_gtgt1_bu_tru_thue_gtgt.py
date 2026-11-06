# -*- coding: utf-8 -*-
"""Đợt GTGT-1 07/11/2026 — BÙ TRỪ THUẾ GTGT CUỐI KỲ.

Chủ tịch chốt 07/11/2026 sau khi đọc tài liệu MISA: `Nợ 33311 / Có 1331` theo SỐ NHỎ HƠN giữa
thuế đầu ra phải nộp và thuế đầu vào được khấu trừ, theo đúng KỲ KÊ KHAI của công ty.

BỐN LUẬT, đo bằng CỬA THẬT qua `TestClient`, và cả bốn TỰ DỰNG CẢNH (ghi bút toán thuế thật)
chứ không trông chờ bộ dữ liệu mẫu tình cờ có sẵn số thuế — bài học Đợt TKC-1 và TD-1 (06/11):
một luật không bao giờ chạy thì không phải luật.

  1. Lấy ĐÚNG SỐ NHỎ HƠN, và hai công thức KHÔNG đối xứng (đầu ra trong kỳ, đầu vào có dư đầu kỳ).
  2. Ghi vào TÀI KHOẢN CON 33311/1331, không ghi vào tài khoản cha 3331/133.
  3. CHƯA ĐẶT KỲ KÊ KHAI thì TỪ CHỐI; kê khai QUÝ thì chỉ làm ở tháng cuối quý.
  4. Ghi rồi thì KHÔNG ghi lần hai, và tham số kỳ kê khai KHÔNG được tự ký trong bộ mặc định.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_gtgt1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_gtgt1.db"):
    os.remove("test_gtgt1.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
TOK = {}

# Kỳ dựng cảnh: tháng 3 là THÁNG CUỐI QUÝ, nên dùng được cho cả hai kiểu kê khai. Chọn một năm
# đã qua để không đụng kỳ nào của dữ liệu mẫu và không bao giờ rơi vào kỳ đã khóa của hôm nay.
KY = "2026-03"
NGAY = "2026-03-20"
KY_TRUOC = "2026-02"
NGAY_TRUOC = "2026-02-20"
KY_GIUA_QUY = "2026-02"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login",
                             data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        _dung_canh()
        yield


def _ghi(mo_ta, ngay, lines):
    r = client.post("/api/v1/journal", json={"entry_date": ngay, "description": mo_ta,
                                             "lines": lines, "post": True}, headers=login("ketoan"))
    assert r.status_code in (200, 201), (
        "không dựng được cảnh (" + str(r.status_code) + "): " + r.text[:300])


def _dat_ky_ke_khai(gia_tri):
    """Đặt tham số kỳ kê khai THẲNG VÀO CSDL.

    Không đi qua cửa `POST /params`: cửa ấy đòi hai chữ ký, mà luật 4 dưới đây chính là luật
    canh rằng tham số này KHÔNG được tự ký. Dựng cảnh bằng chính cửa mình đang đo là tự chứng
    minh mình đúng.
    """
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.core import Param
    from app.services import rules as R
    with SessionLocal() as db:
        p = db.execute(select(Param).where(Param.key == R.GTGT_KY_KE_KHAI_KEY)).scalars().first()
        assert p is not None, "chưa có dòng tham số `gtgt_ky_ke_khai` trong sổ tham số"
        p.value = gia_tri
        db.commit()
    R.clear_param_cache()


def _dung_canh():
    """Cảnh phải làm BỐN điều khác nhau lộ ra, và ba trong bốn là do ĐO NGƯỢC mới thấy thiếu.

        kỳ trước (2026-02): Nợ 1331  3.000.000 / Có 331    → dư Nợ 133 đầu kỳ = 3.000.000
        kỳ trước (2026-02): Nợ 131   4.000.000 / Có 33311  → đầu ra KỲ TRƯỚC, đã khai đã nộp
        kỳ này   (2026-03): Nợ 1331  2.000.000 / Có 331    → đầu vào = 3.000.000 + 2.000.000
        kỳ này   (2026-03): Nợ 131   9.000.000 / Có 33311  → đầu ra trên tài khoản CON
        kỳ này   (2026-03): Nợ 131   1.000.000 / Có 3331   → đầu ra trên tài khoản CHA

    Vì sao từng dòng phải có, đo được bằng cách phá mã rồi chạy lại:

      · Dòng đầu ra KỲ TRƯỚC: không có nó thì lũy kế bằng trong kỳ, và đổi công thức đầu ra sang
        lũy kế vẫn XANH — luật nói về sự không đối xứng mà không đo được nó.
      · Dòng ghi thẳng vào 3331: không có nó thì đọc-cả-cây bằng đọc-mỗi-lá, và rút `_cay_tk`
        xuống còn một tài khoản vẫn XANH. Đây là cảnh THẬT chứ không phải bịa: đo trên main
        07/11/2026, đường phát hành hóa đơn và đường bút toán đảo CÓ ghi thẳng vào 3331.
      · Dư đầu kỳ của 133: không có nó thì bỏ số dư đầu kỳ khỏi công thức đầu vào vẫn xanh.

    Cảnh cố ý đặt đầu vào (5.000.000) NHỎ HƠN đầu ra (10.000.000), nên số bù trừ phải là đầu vào.
    """
    _ghi("GTGT-1 dựng cảnh — thuế đầu vào kỳ trước", NGAY_TRUOC,
         [{"account": "1331", "debit": 3_000_000},
          {"account": "331", "credit": 3_000_000, "partner_code": "NCC-GTGT1"}])
    _ghi("GTGT-1 dựng cảnh — thuế đầu ra KỲ TRƯỚC (đã khai, đã nộp)", NGAY_TRUOC,
         [{"account": "131", "debit": 4_000_000, "partner_code": "KH-GTGT1"},
          {"account": "33311", "credit": 4_000_000}])
    _ghi("GTGT-1 dựng cảnh — thuế đầu vào kỳ này", NGAY,
         [{"account": "1331", "debit": 2_000_000},
          {"account": "331", "credit": 2_000_000, "partner_code": "NCC-GTGT1"}])
    _ghi("GTGT-1 dựng cảnh — thuế đầu ra kỳ này", NGAY,
         [{"account": "131", "debit": 9_000_000, "partner_code": "KH-GTGT1"},
          {"account": "33311", "credit": 9_000_000}])
    # GHI THẲNG VÀO TÀI KHOẢN CHA 3331 — cảnh thật, không phải bịa: đo trên main 07/11/2026,
    # đường phát hành hóa đơn và đường bút toán đảo đang ghi vào đây.
    _ghi("GTGT-1 dựng cảnh — thuế đầu ra ghi thẳng vào TÀI KHOẢN CHA 3331", NGAY,
         [{"account": "131", "debit": 1_000_000, "partner_code": "KH-GTGT1"},
          {"account": "3331", "credit": 1_000_000}])


def _xt(ky=KY):
    r = client.get("/api/v1/ket-so/bu-tru-gtgt/xem-truoc", headers=login("ketoan"), params={"ky": ky})
    assert r.status_code == 200, r.text[:300]
    return r.json()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_gtgt1_1_lay_dung_so_nho_hon_va_hai_cong_thuc_khong_doi_xung():
    """Hai công thức của MISA KHÔNG đối xứng — chép nhầm thành đối xứng là chỗ sai kinh điển.

        đầu ra phải nộp  = PS Có 3331 − PS Nợ 3331 TRONG KỲ          (không mang dư đầu kỳ)
        đầu vào khấu trừ = dư Nợ 133 ĐẦU KỲ + PS Nợ 133 − PS Có 133  (có mang dư đầu kỳ)

    Đầu ra chỉ tính trong kỳ vì phần kỳ trước đã khai và đã nộp; đầu vào mang theo dư đầu kỳ vì
    thuế chưa khấu trừ hết được chuyển sang kỳ sau. Dùng lũy kế cho cả hai là bù trừ lại phần đã
    bù trừ ở kỳ trước.
    """
    _dat_ky_ke_khai("thang")
    d = _xt()
    assert d["du_dau_ky_133"] == 3_000_000, (
        "dư Nợ 133 ĐẦU KỲ phải là 3.000.000 (ghi ở kỳ trước), nhận " + str(d["du_dau_ky_133"]) +
        " — thiếu nó nghĩa là công thức đầu vào đang bỏ qua số dư đầu kỳ")
    assert d["dau_vao_duoc_khau_tru"] == 5_000_000, (
        "đầu vào = 3.000.000 dư đầu kỳ + 2.000.000 trong kỳ, nhận "
        + str(d["dau_vao_duoc_khau_tru"]))
    assert d["dau_ra_phai_nop"] == 10_000_000, (
        "đầu ra = 9.000.000 trên 33311 + 1.000.000 trên 3331, CHỈ TRONG KỲ (4.000.000 của kỳ "
        "trước đã khai đã nộp, không được cộng vào), nhận " + str(d["dau_ra_phai_nop"]))
    assert d["so_bu_tru"] == 5_000_000, (
        "phải bù trừ theo SỐ NHỎ HƠN (đầu vào 5.000.000), nhận " + str(d["so_bu_tru"]))
    assert d["con_phai_nop"] == 5_000_000, "còn phải nộp = 10.000.000 − 5.000.000"
    assert d["con_duoc_khau_tru"] == 0, "khấu trừ hết đầu vào thì còn 0"

    # ĐỌC CẢ CÂY, VÀ NÓI RA PHẦN NẰM TRÊN TÀI KHOẢN CHA. Phép tính đúng, nhưng bút toán ghi vào
    # tài khoản con sẽ không dọn phần nằm ở tài khoản cha — im chỗ này là để sổ chi tiết lệch mà
    # không ai biết.
    assert d["du_tren_tk_cha"]["3331"] == -1_000_000, (
        "cửa không thấy 1.000.000 đang nằm trên CHÍNH tài khoản cha 3331, nhận "
        + str(d["du_tren_tk_cha"].get("3331")))
    assert any("3331" in c and "cha" in c for c in d["canh_bao"]), (
        "có tiền nằm trên tài khoản cha mà bản xem trước không nói ra")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_gtgt1_2_ghi_vao_TAI_KHOAN_CON_khong_ghi_vao_tai_khoan_cha():
    """Chủ tịch chốt 07/11/2026: ghi `Nợ 33311 / Có 1331`.

    Tài liệu MISA tự mâu thuẫn (bút toán mẫu ghi `Nợ 3331 / Có 133`), nhưng chính MISA cấm hạch
    toán vào tài khoản tổng hợp — mà 133 và 3331 đều có tài khoản con. Luật này canh để lần sau
    không ai «sửa cho giống tài liệu».
    """
    _dat_ky_ke_khai("thang")
    d = _xt()
    assert d["tk_no"] == "33311" and d["tk_co"] == "1331", (
        "cửa khai sai cặp tài khoản: " + repr((d["tk_no"], d["tk_co"])))
    bt = d["but_toan"]
    assert len(bt) == 2, "bút toán bù trừ phải đúng hai dòng, nhận " + str(len(bt))
    tk = {l["account"] for l in bt}
    assert tk == {"33311", "1331"}, "bút toán ghi vào " + repr(sorted(tk))
    assert "3331" not in tk and "133" not in tk, "bút toán ghi vào TÀI KHOẢN CHA"
    no = next(l for l in bt if l.get("debit"))
    co = next(l for l in bt if l.get("credit"))
    assert no["account"] == "33311" and co["account"] == "1331", "ngược chiều Nợ/Có"
    assert no["debit"] == co["credit"] == 5_000_000, "hai dòng phải cùng số bù trừ"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_gtgt1_3_chua_dat_ky_ke_khai_thi_TU_CHOI_va_quy_chi_lam_thang_cuoi_quy():
    """Kê khai tháng mà bù theo quý, hay ngược lại, là lệch đúng tờ khai đã nộp.

    Nên cửa KHÔNG ĐOÁN: chưa đặt thì từ chối và nói tên tham số.
    """
    _dat_ky_ke_khai("")
    d = _xt()
    assert d["da_bat"] is False, "chưa đặt kỳ kê khai mà cửa vẫn báo đã bật"
    assert any("gtgt_ky_ke_khai" in c for c in d["canh_bao"]), (
        "bản xem trước phải nói tên tham số cần đặt")
    r = client.post("/api/v1/ket-so/bu-tru-gtgt", json={"ky": KY}, headers=login("ketoan"))
    assert r.status_code == 400, "chưa đặt kỳ kê khai mà vẫn ghi được: " + str(r.status_code)
    assert "gtgt_ky_ke_khai" in r.text, "câu từ chối phải nói tên tham số"

    _dat_ky_ke_khai("quy")
    r2 = client.post("/api/v1/ket-so/bu-tru-gtgt", json={"ky": KY_GIUA_QUY}, headers=login("ketoan"))
    assert r2.status_code == 400, (
        "kê khai QUÝ mà vẫn bù trừ được ở tháng giữa quý: " + str(r2.status_code))
    # Và tháng CUỐI quý thì phải làm được — không có chiều này thì luật trên có thể cấm tất.
    assert _xt(KY)["da_bat"] is True, "kê khai quý, tháng cuối quý, mà cửa vẫn báo chưa bật"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_gtgt1_4_ghi_roi_KHONG_ghi_lan_hai_va_tham_so_KHONG_tu_ky():
    """Hai chuyện, cả hai đều là chỗ mất tiền nếu hỏng.

    Ghi hai lần là bù trừ hai lần — thuế phải nộp tự giảm mà sổ vẫn cân.
    Và tham số kỳ kê khai KHÔNG được mang sẵn giá trị trong `DEFAULT_PARAMS`: `seed_params` nạp
    mọi khóa với `status="active"` kèm HAI chữ ký mang tên Chủ tịch và Tổng giám đốc, nên điền
    sẵn một giá trị ở đó là TỰ KÝ một chính sách thuế.
    """
    from app.services import rules as R
    dong = [p for p in R.DEFAULT_PARAMS if p[0] == R.GTGT_KY_KE_KHAI_KEY]
    assert len(dong) == 1, "phải có đúng một dòng `gtgt_ky_ke_khai` trong DEFAULT_PARAMS"
    assert dong[0][1] == "", (
        "dòng `gtgt_ky_ke_khai` phải để TRỐNG trong bộ mặc định — điền sẵn là tự ký một chính "
        "sách thuế, vì `seed_params` nạp kèm hai chữ ký. Giá trị thật đi qua `POST /params`.")

    _dat_ky_ke_khai("thang")
    r1 = client.post("/api/v1/ket-so/bu-tru-gtgt", json={"ky": KY}, headers=login("ketoan"))
    assert r1.status_code == 200, r1.text[:300]
    k1 = r1.json()
    assert k1["da_ghi"] is True and k1["chung_tu"], "lần đầu phải ghi được một chứng từ"

    r2 = client.post("/api/v1/ket-so/bu-tru-gtgt", json={"ky": KY}, headers=login("ketoan"))
    assert r2.status_code == 200, r2.text[:300]
    k2 = r2.json()
    assert k2["chung_tu"] == k1["chung_tu"], "lần hai đã ghi một chứng từ KHÁC — bù trừ hai lần"
    assert "bỏ qua" in k2["message"].lower(), "lần hai phải nói rõ là bỏ qua"

    # Và sau khi ghi, bản xem trước phải nói đã ghi — không thì màn hình mời người bấm lần nữa.
    assert _xt()["da_ghi"] is True, "ghi rồi mà bản xem trước vẫn báo chưa ghi"

    # Một vai ngoài Kế toán không ghi được.
    r3 = client.post("/api/v1/ket-so/bu-tru-gtgt", json={"ky": KY}, headers=login("kd.hoa"))
    assert r3.status_code == 403, (
        "một vai Kinh doanh phải nhận 403 ở cửa ghi bù trừ GTGT, nhận " + str(r3.status_code))
