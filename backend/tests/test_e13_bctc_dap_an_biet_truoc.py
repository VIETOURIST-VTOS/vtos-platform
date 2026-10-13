# -*- coding: utf-8 -*-
"""Đợt E13 (13/10/2026) — BCTC NÓI ĐÚNG SỐ: một bộ số liệu BIẾT TRƯỚC ĐÁP ÁN.

VÌ SAO CÓ TỆP NÀY

Trước đợt này, cả ba báo cáo tài chính — B01 cân đối, B02 kết quả kinh doanh, B03 lưu chuyển tiền
tệ — có đúng MỘT phép thử (`test_reports.py`), và phép thử ấy hỏi *"bảng có CÂN không"*. Cân là
một điều kiện cần rất yếu: một bảng cộng sai cùng một số ở cả hai vế vẫn cân, và một bảng toàn số
0 thì cân hoàn hảo.

Điều chưa ai hỏi là *"số có ĐÚNG không"*. Muốn hỏi được câu ấy thì phải có một bộ số liệu mà đáp
án tính được bằng tay TRƯỚC khi chạy máy — đó là toàn bộ nội dung tệp này.

BỘ SỐ LIỆU, và nó cố ý nhỏ: sáu bút toán, số tròn, một kỳ. Nhỏ thì tính tay được, mà tính tay
được thì khi phép thử đỏ ta biết ngay MÁY sai chứ không phải phép thử sai. Một bộ dữ liệu to và
thật trông thuyết phục hơn nhiều, nhưng không ai dựng lại được đáp án của nó, nên lúc nó đỏ thì
việc đầu tiên người ta làm là sửa phép thử.

CƠ SỞ DỮ LIỆU RIÊNG VÀ KHÔNG NẠP DỮ LIỆU MẪU: bộ mẫu có hàng nghìn bút toán và đổi theo tháng
(bài học 06/10 ghi trong `test_reports.py`). Đáp án tính tay chỉ đúng khi không có gì khác trong sổ.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e13.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                               # noqa: E402

from app.core.config import settings                         # noqa: E402
from app.db.session import Base, SessionLocal, engine        # noqa: E402
from app.models.accounting import Account                    # noqa: E402
from app.services import accounting as ACC                   # noqa: E402
from app.services import reports as RP                       # noqa: E402

Base.metadata.create_all(engine)

KY = "2099-03"
NGAY = date(2099, 3, 10)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# BỘ SỐ LIỆU — SÁU BÚT TOÁN, SỐ TRÒN, ĐÁP ÁN TÍNH TAY Ở NGAY DƯỚI
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
#  1. Góp vốn            Nợ 112  1.000.000.000 / Có 411  1.000.000.000
#  2. Bán dịch vụ        Nợ 131      1.100.000 / Có 511  1.000.000 · Có 3331  100.000
#  3. Khách trả tiền     Nợ 112      1.100.000 / Có 131  1.100.000
#  4. Mua dịch vụ NCC    Nợ 154        600.000 / Có 331    600.000
#  5. Trả tiền NCC       Nợ 331        600.000 / Có 112    600.000
#  6. Kết chuyển giá vốn Nợ 632        600.000 / Có 154    600.000
#  7. Chi phí quản lý    Nợ 642        200.000 / Có 112    200.000
#
# SỐ DƯ CUỐI KỲ, tính tay:
#   112 = 1.000.000.000 + 1.100.000 − 600.000 − 200.000 = 1.000.300.000
#   131 = 1.100.000 − 1.100.000 = 0          154 = 600.000 − 600.000 = 0
#   331 = 600.000 − 600.000 = 0              3331 = 100.000 (dư Có)
#   411 = 1.000.000.000 (dư Có)
#   511 = 1.000.000 (dư Có)   632 = 600.000 (dư Nợ)   642 = 200.000 (dư Nợ)
# ĐỐI TƯỢNG trên các dòng công nợ là BẮT BUỘC, và đây không phải chi tiết trang trí: bản đầu của
# bộ số liệu này bỏ trống, và `accounting.account_rule_check` chặn ngay — "Tài khoản 131 phải ghi
# mã đối tượng". Hàng rào của chính hệ thống bắt bộ dữ liệu của phép thử, đúng việc nó sinh ra để
# làm; ghi lại vì một bộ số liệu đi vòng qua được hàng rào thật thì nó không còn chứng minh được
# rằng đường đi thật cũng ra đúng ngần ấy.
# `154` và `632` còn đòi MÃ CÔNG TRÌNH (mã tour) — `NEED_PROJECT`. Hàng rào bắt bộ số liệu này
# hai lần liên tiếp, mỗi lần một luật khác; cả hai lần đều đúng.
KHACH, NCC, TOUR = "Khách A", "Nhà cung cấp B", "E13TOUR"

BUT_TOAN = [
    ("Góp vốn chủ sở hữu", [("112", 1_000_000_000, 0, ""), ("411", 0, 1_000_000_000, "")]),
    ("Bán dịch vụ cho khách", [("131", 1_100_000, 0, KHACH), ("511", 0, 1_000_000, ""),
                               ("3331", 0, 100_000, "")]),
    ("Khách trả tiền", [("112", 1_100_000, 0, ""), ("131", 0, 1_100_000, KHACH)]),
    ("Mua dịch vụ nhà cung cấp", [("154", 600_000, 0, ""), ("331", 0, 600_000, NCC)]),  # 154 kèm mã tour
    ("Trả tiền nhà cung cấp", [("331", 600_000, 0, NCC), ("112", 0, 600_000, "")]),
    ("Kết chuyển giá vốn", [("632", 600_000, 0, ""), ("154", 0, 600_000, "")]),
    ("Chi phí quản lý doanh nghiệp", [("642", 200_000, 0, ""), ("112", 0, 200_000, "")]),
]

TK = (("111", "Tiền mặt", "TS"), ("112", "Tiền gửi ngân hàng", "TS"),
      ("131", "Phải thu khách hàng", "TS"), ("154", "Chi phí SXKD dở dang", "TS"),
      ("331", "Phải trả người bán", "NV"), ("3331", "Thuế GTGT phải nộp", "NV"),
      ("411", "Vốn góp của chủ sở hữu", "NV"), ("511", "Doanh thu", "DT"),
      ("632", "Giá vốn hàng bán", "CP"), ("642", "Chi phí quản lý doanh nghiệp", "CP"))


@pytest.fixture(scope="module", autouse=True)
def _so():
    db = SessionLocal()
    for c, n, k in TK:
        if not db.get(Account, c):
            db.add(Account(code=c, name=n, kind=k, is_detail=True))
    db.commit()
    for i, (dien_giai, dong) in enumerate(BUT_TOAN, 1):
        ACC.post_entry(db, "e13", "ketoan", NGAY, dien_giai,
                       [{"account": a, "debit": d or None, "credit": c or None,
                         **({"partner": dt} if dt else {}),
                         **({"project_code": TOUR} if a.startswith(("154", "632", "5113")) else {})}
                        for a, d, c, dt in dong],
                       "thu_cong", f"e13:{i}", nghiep_vu="but_toan_tay")
    db.commit()
    yield db
    db.close()


def _dong(bang, ma):
    return next(x[2] for x in bang if x[0] == ma)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B02 — KẾT QUẢ KINH DOANH
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e13_1_b02_tung_dong_dung_bang_dap_an_tinh_tay(_so):
    r = {ma: so for ma, _ten, so in RP.income_statement(_so, KY)["rows"]}
    assert r["01"] == 1_000_000, "doanh thu"
    assert r["11"] == 600_000, "giá vốn"
    assert r["20"] == 400_000, "lợi nhuận gộp = 1.000.000 − 600.000"
    assert r["26"] == 200_000, "chi phí quản lý"
    assert r["30"] == 200_000, "lợi nhuận thuần = 400.000 − 200.000"
    assert r["50"] == 200_000, "lợi nhuận trước thuế"
    assert r["51"] == 0, "chưa có bút toán thuế TNDN"
    assert r["60"] == 200_000, "lợi nhuận sau thuế"


def test_e13_2_b02_phan_biet_ky_hoa_von_voi_ky_chua_ai_ghi_so(_so):
    """Luật RỖNG KHÁC 0 ở chỗ tốn kém nhất: một kỳ chưa ai ghi sổ KHÔNG được đọc là hoà vốn."""
    assert RP.income_statement(_so, KY)["co_but_toan"] is True
    assert RP.income_statement(_so, "2099-11")["co_but_toan"] is False


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B01 — CÂN ĐỐI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e13_3_b01_tung_dong_dung_bang_dap_an_tinh_tay(_so):
    b = RP.balance_sheet(_so, KY)
    assert _dong(b["assets"], "110") == 1_000_300_000, "tiền = 1.000.000.000 + 1.100.000 − 600.000 − 200.000"
    assert _dong(b["assets"], "131") == 0, "khách đã trả hết"
    assert _dong(b["assets"], "154") == 0, "đã kết chuyển hết sang giá vốn"
    assert _dong(b["liabilities"], "331") == 0, "đã trả hết nhà cung cấp"
    assert _dong(b["liabilities"], "333") == 100_000, "thuế GTGT đầu ra còn phải nộp"
    assert _dong(b["equity"], "411") == 1_000_000_000
    assert _dong(b["equity"], "421") == 200_000, "lãi chưa kết chuyển = lợi nhuận sau thuế B02"


def test_e13_4_b01_can_VA_can_vi_dung_so_chu_khong_phai_vi_toan_so_khong(_so):
    """Cân là điều kiện rất yếu: một bảng toàn số 0 thì cân hoàn hảo. Đòi cả hai."""
    b = RP.balance_sheet(_so, KY)
    assert b["balanced"] is True
    assert b["total_assets"] == 1_000_300_000
    assert b["total_liabilities"] == 100_000
    assert b["total_equity"] == 1_000_200_000
    assert b["total_assets"] == b["total_liabilities"] + b["total_equity"]


def test_e13_5_b01_khop_voi_b02_o_dong_lai_chua_ket_chuyen(_so):
    """Hai báo cáo phải nói CÙNG một con số lãi — chỗ lệch nhau thì không ai biết tin cái nào."""
    assert RP.balance_sheet(_so, KY)["unposted_pl"] == \
        {ma: so for ma, _t, so in RP.income_statement(_so, KY)["rows"]}["60"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B03 — LƯU CHUYỂN TIỀN TỆ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e13_6_b03_tien_cuoi_ky_dung_bang_so_du_112_tren_B01(_so):
    """Phép nối hai báo cáo: tiền cuối kỳ của B03 phải bằng dòng tiền của B01. Không bằng thì
    một trong hai đang đếm sót một chứng từ, và không có phép thử này thì không ai biết."""
    cf = {ma: so for ma, _t, so in RP.cash_flow(_so, KY)["rows"]}
    assert cf["70"] == _dong(RP.balance_sheet(_so, KY)["assets"], "110") == 1_000_300_000
    assert cf["60"] == 0, "kỳ đầu tiên, tiền đầu kỳ bằng 0"
    assert cf["50"] == 1_000_300_000, "lưu chuyển thuần = tiền cuối kỳ − tiền đầu kỳ"


def test_e13_7_b03_phan_loai_dung_tien_thu_khach_va_tien_chi_NCC(_so):
    cf = {ma: so for ma, _t, so in RP.cash_flow(_so, KY)["rows"]}
    assert cf["01"] == 1_100_000, "tiền thu từ bán hàng — chứng từ Nợ 112 / Có 131"
    assert cf["02"] == -600_000, "tiền chi trả người cung cấp — chứng từ Nợ 331 / Có 112"


@pytest.mark.xfail(strict=True, reason=(
    "CHỖ SAI ĐO ĐƯỢC 13/10/2026, CHƯA SỬA VÌ CHƯA CÓ NGƯỜI KÝ. Góp vốn chủ sở hữu (Nợ 112 / Có "
    "411) đang rơi vào 'Tiền thu khác' của HOẠT ĐỘNG KINH DOANH, nên dòng 20 phồng lên đúng bằng "
    "số vốn góp còn dòng 40 — hoạt động tài chính — bằng 0. Theo TT99 đây là luồng tiền từ hoạt "
    "động TÀI CHÍNH. `cash_flow` phân loại theo tài khoản đối ứng và bảng ấy không có nhánh cho "
    "411, nên mọi thứ không khớp nhánh nào đều rơi vào 'khác'. Sửa là ĐỔI MỘT CÔNG THỨC ĐÃ CHỐT "
    "và nó làm đổi số trên một báo cáo đã phát hành — phải có chữ ký. Phép thử để XFAIL STRICT: "
    "nó đỏ-có-chủ-ý hôm nay, và ngày ai đó sửa mà quên tệp này thì bộ phép thử ĐỎ, buộc người ấy "
    "phải tới đây đọc và xoá dòng xfail. Một chỗ sai đã biết mà không có dấu vết nào trong mã là "
    "một chỗ sai sẽ được phát hiện lại từ đầu sau sáu tháng."))
def test_e13_8_b03_gop_von_chu_so_huu_phai_nam_o_hoat_dong_TAI_CHINH(_so):
    cf = {ma: so for ma, _t, so in RP.cash_flow(_so, KY)["rows"]}
    assert cf["40"] == 1_000_000_000, "góp vốn chủ sở hữu thuộc luồng tiền hoạt động tài chính"
    assert cf["06"] == 0, "và KHÔNG được nằm ở 'tiền thu khác' của hoạt động kinh doanh"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TÊN CÔNG TY TRÊN TỜ KHAI THUẾ
# ══════════════════════════════════════════════════════════════════════════════════════════════

TEN_PHAP_LY = "CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS"


def test_e13_9_he_thong_chi_noi_MOT_ten_cong_ty(_so):
    """Đo 13/10/2026: `COMPANY_NAME` còn là tên CŨ 'CÔNG TY CỔ PHẦN DU LỊCH VIETOURIST', trong khi
    sáu chỗ khác đã ghi tên hiện hành. Hệ thống nói hai tên tuỳ đi cửa nào — và cái tên cũ đi
    thẳng lên TỜ KHAI THUẾ XML qua `to_xml(company=settings.COMPANY_NAME)`.

    Chủ tịch chốt 13/10/2026: dùng tên pháp lý hiện hành.
    """
    assert settings.COMPANY_NAME == TEN_PHAP_LY
    xml = RP.to_xml(RP.vat_return(_so, KY), tax_code=settings.COMPANY_TAX_CODE,
                    company=settings.COMPANY_NAME)
    assert TEN_PHAP_LY in xml
    assert "DU LỊCH VIETOURIST" not in xml, "tờ khai thuế còn mang tên công ty cũ"


def test_e13_10_khong_con_ten_cu_nam_mac_dinh_trong_ma(_so):
    """Tên công ty viết mặc định trong chữ ký hàm là chỗ nguy hiểm nhất: nơi gọi quên truyền thì
    nó im lặng dùng tên cũ. Quét cả `app/` — bất kỳ chỗ nào còn tên cũ đều phải sửa hoặc khai ra."""
    goc = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")
    con = []
    for g, _d, ts in os.walk(goc):
        for t in ts:
            if not t.endswith(".py"):
                continue
            p = os.path.join(g, t)
            if "DU LỊCH VIETOURIST" in open(p, encoding="utf-8").read():
                con.append(os.path.relpath(p, goc).replace(os.sep, "/"))
    assert not con, f"còn tên công ty cũ ở: {sorted(con)}"
