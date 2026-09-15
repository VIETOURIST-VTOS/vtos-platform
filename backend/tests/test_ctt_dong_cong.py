# -*- coding: utf-8 -*-
"""SHEET CHIẾT TÍNH — dòng CỘNG không phải dòng CHI, và SỐ KHÔNG không phải CHƯA KHAI.

CHỖ HỎNG THẬT, ĐO NGÀY 15/9/2026 TRÊN SỐ ĐÃ VÀO HỆ THỐNG

Lúc 01:19 ngày 15/9, một tệp quyết toán thật được nạp qua cửa "Quyết toán tour – chi tiết một
chuyến": `QUYẾT TOÁN TOUR ĐÀ LẠT 3N3D TỐI 23.01.2026.xlsx`. Nhật ký ghi 39 dòng, 39 đã nạp, "2 dòng
lỗi (bỏ qua)".

Đọc lại sheet CTT của chính tệp ấy bằng tay:

    A. VẬN CHUYỂN   5 dòng có tiền  ->  30.557.000   (khớp ô TỔNG của nhóm)
    B. CHI PHÍ KHÁC 4 dòng          ->   2.545.000   (khớp ô cộng của nhóm)
    TỔNG CỘNG CHI                       33.102.000   (khớp phép cộng hai nhóm)

Tệp TỰ CÂN. Nhưng cái vào hệ thống là **66.204.000 đ** – gấp đúng hai lần. Phần dôi ra chính là HAI
Ô CỘNG: bộ đọc đếm chúng như hai dòng chi phí.

Chuyến ấy doanh thu 42.880.000 đ. Giá vốn gấp đôi biến một chuyến LÃI 9,8 triệu thành LỖ 23 triệu.
Không có gì kêu lên, vì bảng vẫn cân – nó cân với chính con số đã sai. Và nếu 81 tệp tháng 1 nạp
tiếp thì cả tháng thành lỗ, rồi số ấy chạy về báo cáo phòng, lãi lỗ tour và bảng của TGĐ/Chủ tịch.

BA CHỖ, VÀ CHỈ MỘT CHỖ ĐỘNG VÀO TIỀN

  1. DÒNG CỘNG ĐẾM THÀNH DÒNG CHI  -> giá vốn gấp đôi. Đây là chỗ động vào tiền.
  2. NHÓM "B.CHI PHÍ KHÁC" KHÔNG ĐƯỢC NHẬN RA vì bộ đọc đòi dấu cách sau dấu chấm, còn tệp viết
     liền. Bốn dòng của B bị xếp vào A. Tổng tiền không sai, nhưng báo cáo chi phí theo nhóm thì sai.
  3. SỐ LƯỢNG 0 BỊ THAY BẰNG 1 (`x or 1`) nên hai dòng có số lượng 0 và thành tiền 0 – hoàn toàn
     đúng – bị kêu "thành tiền khác phép nhân". Người nạp phải tích "bỏ qua dòng lỗi" để đi tiếp, và
     bỏ qua thành thói quen thì đến dòng lệch THẬT cũng bị bỏ qua.

LUẬT NHẬN RA DÒNG CỘNG PHẢI TỰ KIỂM ĐƯỢC

Một dòng chi thật luôn có đơn giá hoặc số lượng; dòng cộng thì chỉ có mỗi thành tiền. Nhưng "chỉ có
thành tiền" chưa đủ để kết luận, vì một khoản khoán trọn gói cũng thế. Nên máy CỘNG THỬ: số ấy đúng
bằng tổng các dòng kể từ ô cộng gần nhất thì mới là ô cộng. Luật ấy không bao giờ nuốt mất tiền thật
– và CC5 dưới đây canh đúng điều đó.

  CC1  dòng CỘNG không vào vế chi; giá vốn bằng đúng ô TỔNG CỘNG CHI của tệp
  CC2  vế THU không bị đụng tới
  CC3  nhóm viết liền "B.CHI PHÍ KHÁC" vẫn được tách đúng
  CC4  số lượng 0 là số thật – không còn dòng lỗi giả
  CC5  khoản khoán chỉ có thành tiền, KHÔNG khớp phép cộng thử -> giữ lại là dòng chi thật
  CC6  ô cộng ghi lệch với tổng các dòng của chính nó -> vẫn kêu lên
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_ctt_cong.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_ctt_cong.db", "test_ctt_cong.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import openpyxl                                                        # noqa: E402

import app.models                                                      # noqa: E402,F401
from app.db.session import Base, engine                                 # noqa: E402
from app.services import quyet_toan_chi_tiet as QTCT                    # noqa: E402

Base.metadata.create_all(engine)

# Dựng lại ĐÚNG bố cục sheet CTT của tệp thật ngày 23/01/2026 – kể cả hai chỗ mà bộ đọc cũ vấp:
# nhóm B viết liền không dấu cách, và hai ô cộng (một có chữ "TỔNG", một không ghi gì).
CTT = [
    ["CHI PHÍ TOUR ĐÀ LẠT 3N3D"],
    ["MÃ TOUR:", "DL002.03230126", "SỐ LƯỢNG", 39],
    ["KHỞI HÀNH:", "Tối 23-26/01/2026"],
    [],
    [],
    ["NGÀY", "NỘI DUNG", "ĐỐI TÁC", "ĐƠN GIÁ", "SL", "DIỄN GIẢI", "THÀNH TIỀN", "GHI CHÚ"],
    ["I/GIÁ TOUR:"],
    [None, None, "NGƯỜI LỚN", 1690000, 4, None, 6760000],
    [None, None, "NGƯỜI LỚN - KM", 920000, 9, None, 8280000],
    [None, None, "PHỤ THU PHÒNG", 800000, 2, None, 1600000],
    ["TỔNG CỘNG THU", None, None, None, None, None, 16640000],
    ["II/ CHI PHÍ:"],
    ["A. VẬN CHUYỂN:"],
    [None, "XE 45C", "VIETRIP", 9000000, 1, 1, 9000000],
    ["LƯU TRÚ", "KHÁCH SẠN 3*", "Lan Anh Hotel", 175000, 39, 2, 13650000],
    [None, None, "Phụ thu TE", 140000, 0, 1, 0],          # SỐ LƯỢNG 0 – thành tiền 0 là ĐÚNG
    ["TỔNG", None, None, None, None, None, 22650000],     # ô cộng CÓ CHỮ
    ["B.CHI PHÍ KHÁC"],                                   # viết LIỀN, không dấu cách
    [None, "Nước", None, 5000, 164, 1, 820000],
    [None, "Bảo hiểm", None, 5000, 40, 1, 200000],
    [None, None, None, None, None, None, 1020000],        # ô cộng KHÔNG GHI GÌ
    ["TỔNG CỘNG CHI", None, None, None, None, None, 23670000],
    ["GIA NET:"],
]
CHI_THAT = 9000000 + 13650000 + 0 + 820000 + 200000          # = 23.670.000
THU_THAT = 6760000 + 8280000 + 1600000                        # = 16.640.000


def _dung(hang) -> "openpyxl.worksheet.worksheet.Worksheet":
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CTT"
    for h in hang:
        ws.append(list(h) if h else [None])
    return ws


def _doc(hang=None):
    return QTCT.doc_sheet_ctt(_dung(hang or CTT))


# ── Tiền ────────────────────────────────────────────────────────────────────────────────────────

def test_cc1_dong_cong_khong_vao_ve_chi():
    d = _doc()
    chi = [x for x in d["dong"] if x["ve"] == "chi"]
    cong = sum(x["thanh_tien"] or 0 for x in chi)
    assert cong == CHI_THAT, (
        f"giá vốn đọc ra {cong:,.0f} đ, đáng lẽ {CHI_THAT:,.0f} đ. Lệch đúng bằng các ô cộng thì "
        "nghĩa là dòng cộng lại bị đếm như dòng chi – y hệt chuyến DL002.03230126 ngày 15/9.")
    assert cong == d["tong"]["chi"], "giá vốn phải khớp ô TỔNG CỘNG CHI của chính tệp"
    assert len(chi) == 5, f"phải còn 5 dòng chi thật, đang có {len(chi)}"
    assert not any((x["noi_dung"] or "").strip().upper().startswith("TỔNG") for x in chi), \
        "còn một dòng mang chữ TỔNG nằm trong vế chi"


def test_cc2_ve_thu_khong_bi_dung_toi():
    d = _doc()
    thu = [x for x in d["dong"] if x["ve"] == "thu"]
    assert sum(x["thanh_tien"] or 0 for x in thu) == THU_THAT
    assert len(thu) == 3


def test_cc3_nhom_viet_lien_van_duoc_tach():
    """Tệp thật viết "B.CHI PHÍ KHÁC" – không có dấu cách sau dấu chấm."""
    d = _doc()
    nhom = {x["nhom"] for x in d["dong"] if x["ve"] == "chi"}
    assert nhom == {"A. VẬN CHUYỂN:", "B.CHI PHÍ KHÁC"}, (
        f"nhóm chi đọc ra {nhom} – nhóm viết liền không được nhận ra thì mọi dòng của nó bị xếp "
        "nhầm sang nhóm trước, và báo cáo chi phí theo nhóm sai trong khi tổng vẫn đúng")


def test_cc4_so_luong_0_la_so_that_khong_phai_chua_khai():
    """0 là một con số khai rõ. RỖNG mới là chưa khai."""
    d = _doc()
    kq = QTCT.kiem({"ctt": d, "sheet_qt": {"dong": []}, "dt": {"dong": []},
                    "hdv_chi": {"dong": []}, "dau": {}, "ma_tour": "DL002.03230126"})
    # `kiem` trả danh sách phát hiện dưới khoá "doi_chieu"; "phat_hien" là tên mà `kiem_lo` đặt
    # lại khi gói kết quả. Bản đầu của phép thử này đọc nhầm "phat_hien" nên `lech` luôn rỗng và
    # phép thử XANH cả khi lỗi còn nguyên – thử phá ngày 15/9 lộ ra đúng chuyện ấy.
    assert kq.get("doi_chieu") is not None, "đọc sai khoá kết quả thì phép thử không kiểm gì cả"
    assert kq["so_dong_chiet_tinh_lech"] == 0, (
        f"{kq['so_dong_chiet_tinh_lech']} dòng bị kêu lệch, đáng lẽ 0")
    lech = [x for x in kq["doi_chieu"] if x["muc"] == "chiet_tinh_sai_phep_nhan"]
    assert not lech, (
        f"dòng số lượng 0 bị kêu lệch: {lech}. Người nạp buộc phải tích 'bỏ qua dòng lỗi' để đi "
        "tiếp, và bỏ qua thành thói quen thì đến dòng lệch THẬT cũng bị bỏ qua.")


# ── Luật nhận dòng cộng phải tự kiểm được ───────────────────────────────────────────────────────

def test_cc5_khoan_khoan_chi_co_thanh_tien_van_duoc_giu():
    """Phép thử quan trọng nhất của tệp này: luật mới KHÔNG được nuốt mất tiền thật.

    Một khoản khoán trọn gói cũng chỉ có mỗi thành tiền, y như một ô cộng. Phân biệt bằng CỘNG THỬ:
    số nào đúng bằng tổng các dòng phía trên thì là ô cộng; không bằng thì là tiền thật.
    """
    hang = [h[:] for h in CTT]
    # Chen một khoản khoán 7.000.000 vào nhóm B – chỉ có thành tiền, và KHÔNG khớp phép cộng thử.
    hang.insert(19, [None, "Vé máy bay trọn gói", None, None, None, None, 7000000])
    hang[21] = [None, None, None, None, None, None, 1020000 + 7000000]   # ô cộng của B tăng theo
    hang[22] = ["TỔNG CỘNG CHI", None, None, None, None, None, 23670000 + 7000000]
    d = QTCT.doc_sheet_ctt(_dung(hang))
    chi = [x for x in d["dong"] if x["ve"] == "chi"]
    assert any(x["thanh_tien"] == 7000000 for x in chi), (
        "khoản khoán 7.000.000 đ bị nuốt mất vì tưởng là dòng cộng – luật nhận dòng cộng phải tự "
        "kiểm bằng phép cộng thử, không được đoán theo hình dạng")
    assert sum(x["thanh_tien"] or 0 for x in chi) == CHI_THAT + 7000000


def test_cc6_o_cong_ghi_lech_thi_van_keu_len():
    """Bỏ dòng cộng ra khỏi vế chi KHÔNG được làm mất phép kiểm ô cộng.

    Ô cộng sai là chỗ hỏng nguy hiểm nhất của tệp Excel: mọi tầng phía sau lấy lại đúng cái tổng đã
    sai ấy nên bảng vẫn cân. Máy phải cộng lại và nói ra.
    """
    hang = [h[:] for h in CTT]
    hang[16] = ["TỔNG", None, None, None, None, None, 22650000 - 210000]   # ô cộng nhóm A thiếu 210k
    d = QTCT.doc_sheet_ctt(_dung(hang))
    oc = [o for o in d["o_cong"] if o["nhom"].startswith("A.")]
    assert oc, "không còn ghi lại ô cộng nào – phép kiểm ô cộng mất chỗ bám"
    assert oc[0]["ghi"] != oc[0]["cong_lai"], "ô cộng ghi lệch mà máy không thấy"
    assert oc[0]["cong_lai"] == 22650000, "phép cộng thử phải ra tổng thật của các dòng nhóm A"
