# -*- coding: utf-8 -*-
"""Đề xuất TẠO CHUYẾN còn thiếu từ kho quyết toán cũ T1–T6/2026.

VÌ SAO CÓ BƯỚC NÀY

Chủ tịch duyệt cấu trúc 13/9/2026 và giao nạp kho cũ để hệ thống chạy trên số thật nửa năm. Đo ngay
sau đó: VTOS có 1.150 chuyến nhưng chỉ 47/436 mã của kho khớp được — bản nạp Vietrip chỉ mang về từ
tháng 6, còn T1–T5/2026 gần như trống (0 · 1 · 1 · 2 · 5 chuyến). Không có chuyến thì dòng quyết
toán không có chỗ treo, nên phải tạo chuyến trước.

Tạo vài trăm chuyến là GHI LẠI LỊCH SỬ VẬN HÀNH của công ty. Nên bộ này chỉ ĐỀ XUẤT và phải nói ra
hết những gì nó định làm; phần ghi là một cửa riêng có người bấm.

  TC1  604 tệp KHÔNG phải 604 chuyến – bốn loại không phải chuyến phải bị để riêng ra
  TC2  chuyến đã có trong VTOS thì KHÔNG tạo lại
  TC3  tên gõ vào ô 'Mã tour' KHÔNG được thành mã chuyến
  TC4  VỎ MẪU CŨ: mã, ngày và TÊN trong tệp đều là của chuyến khác – phải bỏ cả ba
  TC5  vỏ cũ lây theo MÃ, kể cả tệp mà luật ngày không bắt được
  TC6  mã tạm phải DUY NHẤT – trùng là gộp nhầm hai chuyến
  TC7  không có ngày thì KHÔNG tạo chuyến, và phải nói ra
  TC8  thứ tự nguồn ngày: trong tệp → tên tệp → sáu số cuối của mã
  TC9  bộ này KHÔNG ghi gì – không có một lời gọi cơ sở dữ liệu nào
"""
import ast
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_taochuyen.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_taochuyen.db", "test_taochuyen.db-journal"):
    if os.path.exists(f):
        os.remove(f)

from app.services import tao_chuyen_kho_cu as TC                     # noqa: E402


def _t(tep, ma="", ngay=None, ten="", ten_doan=""):
    return {"ten_tep": tep, "ma_tour": ma, "ngay_di": ngay,
            "ten_tour": ten, "ten_doan": ten_doan, "so_khach": 20}


def test_tc1_bon_loai_khong_phai_chuyen_phai_de_rieng_ra():
    """604 tệp không phải 604 chuyến. 48 tệp là bảng gom việc lẻ theo tháng hoặc bảng của đối tác.

    Bỏ im lặng thì người duyệt tưởng đã nạp hết; tạo chuyến cho chúng thì đẻ ra mấy chục chuyến ma
    mang tên "QUYẾT TOÁN VISA MỸ THÁNG 4".
    """
    ds = [
        _t("QUYẾT TOÁN VISA MỸ THÁNG 4.xlsx"),
        _t("QT OUTBOUND GHÉP LE T03.26- ĐH PHẠM THÚY VY.xlsx"),
        _t("QTUC LE T05.26.xlsx"),
        _t("LAND TOUR MIỀN BẮC THÁNG 5.2026.xlsx"),
        _t("QT TOUR NHA TRANG 05.06.26.xlsx", "NT001.03050626", date(2026, 6, 5)),
    ]
    b = TC.bang(ds, set())
    assert b["bo_qua"] == 4 and b["tao_moi"] == 1, \
        f"phải để riêng đúng 4 tệp không-phải-chuyến, đang bỏ qua {b['bo_qua']} và tạo {b['tao_moi']}"
    assert set(b["bo_qua_theo_loai"]) == set(TC.KHONG_PHAI_CHUYEN)
    for h in b["hang"]:
        if h["viec"] == "bo_qua":
            assert h["vi_sao"], "bỏ qua thì phải nói ra vì sao và chỗ đúng của nó ở đâu"


def test_tc2_chuyen_da_co_trong_vtos_thi_khong_tao_lai():
    ds = [_t("QT NHA TRANG.xlsx", "NT001.03050626", date(2026, 6, 5))]
    b = TC.bang(ds, {"NT001.03050626"})
    assert b["da_co"] == 1 and b["tao_moi"] == 0
    assert "đã có" in b["hang"][0]["vi_sao"].lower()


def test_tc3_ten_go_vao_o_ma_tour_khong_duoc_thanh_ma_chuyen():
    """19 mã trong kho thật ra là TÊN: 'CÔNG TY DƯỢC', 'CẢNG SÀI GÒN', 'MIỀN TÂY 5N4Đ'…

    Tạo chuyến mang mã ấy thì nó nằm trong danh sách tour của công ty mãi mãi.
    """
    for xau in ("CÔNG TY DƯỢC", "CẢNG SÀI GÒN", "MIỀN TÂY 5N4Đ", "BẾN TRE"):
        assert not TC.la_ma_that(xau), f"{xau!r} là TÊN, không được nhận là mã"
    for that in ("NT001.03050626", "MICEPQ3N2D.03040326", "PHUQUOC012026", "TI310526"):
        assert TC.la_ma_that(that), f"{that!r} là mã thật, không được đá nhầm"

    b = TC.bang([_t("QT CẢNG SÀI GÒN 12.03.2026.xlsx", "CẢNG SÀI GÒN", date(2026, 3, 12))], set())
    h = b["hang"][0]
    assert h["ma"].startswith(TC.TIEN_TO_TAM) and h["ma_la_may_dat"]
    assert "TÊN" in h["vi_sao"]


def test_tc4_vo_mau_cu_thi_bo_ca_ma_ca_ngay_va_ca_TEN():
    """112 tệp 'QT NAM CÁT TIÊN' của 112 ngày khác nhau đều khai mã PT14012022, ngày 14/01/2022,
    TÊN 'PHAN THIẾT', và cùng một danh sách 22 khách – chép từ một tệp Phan Thiết 2022 mà quên sửa.

    Bỏ mã và ngày mà giữ tên thì sinh ra 112 chuyến Nam Cát Tiên mang tên Phan Thiết: không ai tra
    ra được gì, mà cũng chẳng có gì đỏ lên.
    """
    d = _t("QT NAM CÁT TIÊN 02.05.2026 (1 ngày).xlsx", "PT14012022", date(2022, 1, 14),
           ten="PHAN THIẾT")
    assert TC.vo_mau_cu(d), "ngày trong tệp lệch hơn 4 năm so với tên tệp mà không nhận ra là vỏ cũ"
    h = TC.de_xuat(d, set())
    assert h["vo_mau_cu"] and h["ma_la_may_dat"]
    assert h["ngay_di"] == date(2026, 5, 2), "ngày phải lấy từ TÊN TỆP, không lấy ngày trong vỏ cũ"
    assert "PHAN THIẾT" not in h["ten"].upper(), \
        f"tên chuyến vẫn lấy từ vỏ cũ: {h['ten']!r} – phải lấy từ tên tệp"
    assert "NAM CÁT TIÊN" in h["ten"].upper()


def test_tc5_vo_cu_lay_theo_MA_ke_ca_tep_luat_ngay_khong_bat_duoc():
    """Luật ngày-lệch chỉ bắt được tệp mà TÊN TỆP có ngày đọc được. Sáu tệp mang mã PT14012022 có
    tên không đọc ra ngày nên thoát lưới, rồi giữ nguyên cái mã đã bị 106 tệp khác chứng minh là
    của chuyến 2022. Một mã đã là vỏ cũ thì nó là vỏ cũ ở MỌI tệp mang nó."""
    ds = [
        _t("QT NAM CÁT TIÊN 02.05.2026.xlsx", "PT14012022", date(2022, 1, 14), ten="PHAN THIẾT"),
        _t("QT NAM CÁT TIÊN 08.032026.xlsx", "PT14012022", date(2022, 1, 14), ten="PHAN THIẾT"),
    ]
    b = TC.bang(ds, set())
    assert all(h["vo_mau_cu"] for h in b["hang"]), \
        "tệp thứ hai không bị luật ngày bắt, nhưng mang đúng cái mã đã bị chứng minh là vỏ cũ"
    assert not any(h.get("ma") == "PT14012022" for h in b["hang"]), \
        "mã của vỏ cũ vẫn lọt ra thành mã chuyến"


def test_tc6_ma_tam_phai_duy_nhat():
    """Mã tạm dựng từ ngày + vài chữ đầu tên tệp, nên hai tệp khác nhau vẫn ra cùng một chuỗi.
    Trùng mã thì cửa ghi gộp hai chuyến khác nhau làm một, và cả hai đều có dòng nên không ai thấy."""
    ds = [_t("QUYẾT TOÁN ĐOÀN A 11.01.2026.xlsx", "TÊN GÕ NHẦM", date(2026, 1, 11)),
          _t("QUYẾT TOÁN ĐOÀN B 11.01.2026.xlsx", "TÊN GÕ NHẦM", date(2026, 1, 11))]
    b = TC.bang(ds, set())
    ma = [h["ma"] for h in b["hang"]]
    assert len(set(ma)) == 2, f"hai tệp khác nhau ra cùng một mã tạm: {ma}"
    assert not b["ma_trung_nhau"], f"vẫn còn mã trùng: {b['ma_trung_nhau']}"


def test_tc7_khong_co_ngay_thi_khong_tao_chuyen_va_phai_noi_ra():
    """Chuyến bắt buộc có ngày đi và ngày về. Không có ngày mà vẫn tạo thì phải bịa – bịa một ngày
    khởi hành rồi tính thưởng, tính hạn quyết toán theo nó là chỗ sinh lỗi lặng."""
    b = TC.bang([_t("THÁNG 1.2026.xlsx", "")], set())
    h = b["hang"][0]
    assert h["viec"] == "thieu_ngay" and b["tao_moi"] == 0
    assert "ngày" in h["vi_sao"].lower() and "người" in h["vi_sao"].lower()


def test_tc8_thu_tu_nguon_ngay_trong_tep_roi_ten_tep_roi_sau_so_cuoi_cua_ma():
    """Ba nguồn, đáng tin giảm dần. Quy ước sáu số cuối = DDMMYY đo được 368/388 khớp (94%) nên
    dùng được, nhưng 6% lệch nên chỉ làm đường lui cuối."""
    assert TC.ngay_tu_ma("SM000.05120326") == date(2026, 3, 12)
    assert TC.ngay_tu_ma("CÔNG TY DƯỢC") is None

    # 1. ngày trong tệp thắng
    h = TC.de_xuat(_t("QT ABC 20.02.2026.xlsx", "NT001.03050226", date(2026, 2, 5)), set())
    assert h["ngay_di"] == date(2026, 2, 5)
    # 2. không có ngày trong tệp -> tên tệp
    h = TC.de_xuat(_t("QT ABC 20.02.2026.xlsx", "NT001.03050226", None), set())
    assert h["ngay_di"] == date(2026, 2, 20)
    # 3. cả hai câm -> sáu số cuối của mã
    h = TC.de_xuat(_t("SM000.05120326.xlsx", "SM000.05120326", None), set())
    assert h["ngay_di"] == date(2026, 3, 12)


def test_tc9_bo_nay_khong_ghi_gi():
    """Đề xuất và GHI là hai bước riêng – đó là cả lý do tệp này tồn tại. Một lời gọi ghi lọt vào
    đây thì bước "xem trước" không còn là xem trước nữa, và không ai nhận ra."""
    cay = ast.parse(open(TC.__file__, encoding="utf-8").read())
    cam = {"add", "commit", "flush", "delete", "execute", "merge", "bulk_save_objects"}
    thay = [f"dòng {n.lineno}: .{n.func.attr}()"
            for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in cam]
    assert not thay, f"bộ ĐỀ XUẤT đang gọi lệnh ghi cơ sở dữ liệu: {thay}"
    assert "Session" not in open(TC.__file__, encoding="utf-8").read(), \
        "bộ đề xuất không được nhận phiên cơ sở dữ liệu"


# ─────────────────────────────────────────────────────────────────────────────
# TC10–TC11 thêm ngày 16/9/2026, sau khi nạp xong 604 tệp lên bản chạy thật.
#
# Vòng nạp báo 54 tệp "không thấy chuyến". Đo lại từng tệp thì 49 trong số ấy đúng là không phải
# chuyến (bảng visa theo tháng, ghép lẻ theo tháng, dịch vụ lẻ theo tháng, bảng tháng của đối tác
# land) — để chúng ra ngoài là đúng. Nhưng 4 tệp thì KHÔNG: chúng có đủ mã, ngày, khách và dòng chi
# của chính đoàn mình, chỉ rơi qua khe giữa hai luật. 312,2 triệu doanh thu nằm ngoài hệ vì thế.
# ─────────────────────────────────────────────────────────────────────────────


def test_tc10_land_mot_doan_co_ngay_KHONG_phai_bang_thang_cua_doi_tac():
    """Chữ LAND trong tên không đủ để kết luận "không phải chuyến".

    Đo 16/9/2026 trên 13 tệp LAND: 11 là bảng THÁNG của đối tác, 2 là quyết toán MỘT ĐOÀN có mã
    thật, có ngày, có dòng chi phí riêng. Gộp cả 13 vào một rổ là bỏ rơi 49,7 triệu chi phí có
    chứng từ — mà bỏ rơi im lặng, vì rổ 'bỏ qua' không ai đi soát lại.
    """
    thang = [
        _t("LAND TOUR MIỀN BẮC THÁNG 5.2026.xlsx"),
        _t("QUYẾT TOÁN LAND PHU QUOC THANG 01.2026.xlsx", "PHUQUOC012026"),
        _t("QUYẾT TOÁN LAND ĐÀ NẴNG - HUẾ THÁNG 02.2026.xlsx", "MT022026"),
    ]
    for d in thang:
        assert TC.phan_loai(d["ten_tep"]) == "land_doi_tac", \
            f"bảng tháng của đối tác {d['ten_tep']!r} phải nằm ngoài, không được tạo chuyến"

    doan = [
        _t("QTT LAND VĨNH HY 03.03.2026 - SALE DIỆU TRINH VTD).xlsx", "DOANVH030326"),
        _t("QTT ĐOÀN LAND PT 04.06.2026 - SALE KIM OANH (VAT VTD).xlsx", "DOANPT040626"),
    ]
    for d in doan:
        assert TC.phan_loai(d["ten_tep"]) == "mot_chuyen", \
            f"{d['ten_tep']!r} là quyết toán MỘT ĐOÀN – có mã, có ngày, có dòng chi"

    b = TC.bang(thang + doan, set())
    assert b["bo_qua"] == 3 and b["tao_moi"] == 2, \
        f"phải để riêng 3 bảng tháng và tạo 2 chuyến, đang bỏ qua {b['bo_qua']} tạo {b['tao_moi']}"
    # Mã của hai đoàn là mã THẬT, không được thay bằng mã máy đặt.
    ma = {h["tep"]: h for h in b["hang"] if h["viec"] == "tao_moi"}
    for h in ma.values():
        assert h["ma_la_may_dat"] is False, f"{h['tep']!r} có mã thật {h['ma']!r}, đừng đặt mã tạm"


def test_tc11_ngay_nam_o_duoi_TEN_TEP_khi_o_ma_tour_cam():
    """Khe thứ tư: sáu số cuối nằm trên TÊN TỆP chứ không nằm trong ô 'Mã tour'.

    `ngay_tu_ten_tep` đòi ngày có dấu ngăn; `ngay_tu_ma` đọc sáu số cuối nhưng đọc ở ô mã. Tệp đặt
    tên bằng chính mã rồi bỏ trống ô ấy thì cả hai đều câm, dù ngày nằm ngay trên tên.

    Đo 16/9/2026: đúng 2 tệp rơi vào khe này — SM001.04090126.xlsx (40 khách, 160,3 tr) và
    SMI.05090126.xlsx (20 khách, 101,9 tr). Cả hai ghi 'Mã tour' là '3VSV', bốn ký tự, không qua
    nổi `la_ma_that`, nên trước đây bị xếp 'thiếu ngày' và bỏ hẳn.
    """
    assert TC.ngay_tu_duoi_ten_tep("SM001.04090126.xlsx") == date(2026, 1, 9)
    assert TC.ngay_tu_duoi_ten_tep("SMI.05090126.xlsx") == date(2026, 1, 9)
    assert TC.ngay_tu_duoi_ten_tep("THÁNG 1.2026.xlsx") is None, \
        "bảng tháng không có ngày – không được bịa ra một ngày cho nó"

    ds = [_t("SM001.04090126.xlsx", "3VSV", None), _t("SMI.05090126.xlsx", "3VSV", None)]
    b = TC.bang(ds, set())
    assert b["thieu_ngay"] == 0 and b["tao_moi"] == 2, \
        f"hai tệp này phải tạo được chuyến, đang thiếu ngày {b['thieu_ngay']}"
    h = {x["tep"]: x for x in b["hang"]}
    for x in h.values():
        assert x["ngay_di"] == date(2026, 1, 9)
        assert x["ma_la_may_dat"] is True, "'3VSV' là bốn ký tự – không phải mã, phải đặt mã tạm"
    assert h["SM001.04090126.xlsx"]["ma"] != h["SMI.05090126.xlsx"]["ma"], \
        "hai tệp khác nhau cùng ngày mà cùng mã thì cửa ghi gộp hai chuyến làm một"

    # ĐƯỜNG LUI CUỐI, không được vượt mặt ba nguồn trên. Tên tệp có đủ cả hai kiểu ngày thì kiểu
    # có dấu ngăn phải thắng.
    x = TC.de_xuat(_t("QT ABC 20.02.2026 - SM000.05120326.xlsx", "", None), set())
    assert x["ngay_di"] == date(2026, 2, 20), "ngày có dấu ngăn trên tên tệp phải thắng sáu số cuối"
