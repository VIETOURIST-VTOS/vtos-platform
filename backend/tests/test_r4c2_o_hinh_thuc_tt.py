# -*- coding: utf-8 -*-
"""Đợt R4c-2 02/11/2026 — Ô HÌNH THỨC THANH TOÁN Ở HAI CỬA.

Chủ tịch duyệt bản xem thử 02/11/2026.

ĐO ĐƯỢC TRƯỚC KHI VIẾT: `hinh_thuc_tt` xuất hiện **0 lần trong toàn bộ dự án web**. Hệ quả không
ai nhìn thấy vì nó im lặng:

  · Cửa trình `/hach-toan` không có ô ấy, nên Kế toán không trình được một quy tắc tiền mặt nào
    qua màn hình — chỉ bằng `curl`.
  · Cửa phân loại `/ket-so` chỉ có hai ô. `ket_so._boi_canh` gõ cứng `"chuyen_khoan"`, và chú
    thích ngay dòng đó nói "Kế toán ghi đè được qua `phan_loai`" — nhưng màn hình KHÔNG BAO GIỜ
    cho ghi đè. Nên SÁU quy tắc tiền mặt của Đợt R2 (15/10/2026) chưa từng khớp được một dòng.

Một cửa viết trong lời chú thích mà không dựng ngoài màn hình thì nó không phải là một cửa.
LUẬT 4 của tệp này đo đúng việc ấy, bằng ĐƯỜNG CHẠY THẬT chứ không bằng cách soi chữ.
"""
import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.hach_toan import HINH_THUC_TT
from app.models.payments import BankTransaction
from app.services import accounting as ACC
from app.services import hach_toan as HT
from app.services import ket_so as KS

GOC = Path(__file__).resolve().parents[2]
TRANG_HT = GOC / "web" / "app" / "hach-toan" / "page.tsx"
TRANG_KS = GOC / "web" / "app" / "ket-so" / "page.tsx"


def _khong_loi_noi(s: str) -> str:
    """Bỏ mọi dòng lời chú thích trước khi đo.

    Bài học 01/11/2026, va phải BA LẦN: một phép đo soi mã nguồn sẽ bắt cả LỜI NÓI VỀ việc làm.
    Bản vá nào viết `// thêm ô hinh_thuc_tt` là tự làm xanh phép đo của chính nó. Một phép đo bắt
    cả lời nói thì nó không đo việc làm.
    """
    return "\n".join(d for d in s.splitlines() if not d.strip().startswith("//"))


def _rieng():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    HT.nap_mac_dinh(db)
    return db


# ─────────────────────────────────────────────────────────────── LUẬT 1
def test_r4c2_1_may_chu_tra_danh_sach_va_khong_go_lai():
    """Cửa sao kê trả về danh sách bảy hình thức, VÀ nó đúng là `HINH_THUC_TT` của máy chủ.

    So bằng ĐỐI TƯỢNG chứ không bằng số phần tử: bảy dòng gõ lại ở chỗ khác cũng có bảy phần tử.
    Màn hình phải đọc một nguồn duy nhất, nếu không thì thêm một hình thức ở máy chủ mà quên nơi
    gõ lại sẽ im lặng không bao giờ khớp.
    """
    db = _rieng()
    xt = KS.xem_truoc_sao_ke(db, "2026-10")
    assert "hinh_thuc_tt" in xt, "phản hồi sao kê thiếu danh sách hình thức thanh toán"
    assert xt["hinh_thuc_tt"] == HINH_THUC_TT, "danh sách KHÔNG phải của models.hach_toan"
    assert "tien_mat" in xt["hinh_thuc_tt"] and "chuyen_khoan" in xt["hinh_thuc_tt"]


# ─────────────────────────────────────────────────────────────── LUẬT 2
def test_r4c2_2_cua_trinh_gui_hai_o_va_khong_go_lai_bay_dong():
    """Cửa trình `/hach-toan`: ô chọn đọc từ máy chủ, và thân yêu cầu MANG hai ô đi."""
    than = _khong_loi_noi(TRANG_HT.read_text(encoding="utf-8"))

    assert "hinh_thuc_tt" in than, "trang trình KHÔNG có ô hình thức thanh toán"

    # Ô VUÔNG, đo bằng NHÃN của chính nó. Không đo chữ `can_khoan_muc` chung chung: chữ ấy cũng
    # nằm trong thân yêu cầu (chỗ DÙNG), nên một phép đo soi nó sẽ bảo xanh cho một màn hình
    # không có ô vuông nào. Em va đúng cái bẫy này ở lần chạy đầu của chính đợt này.
    assert "Bắt buộc chọn khoản mục chi phí" in than, "trang trình KHÔNG có ô vuông khoản mục"
    assert "can_khoan_muc: e.target.checked" in than, "ô vuông không ghi vào biểu"

    # Ô chọn phải đọc từ phản hồi máy chủ (`d?.hinh_thuc_tt`), KHÔNG gõ lại bảy chuỗi.
    assert re.search(r"d\?\.hinh_thuc_tt", than), "ô chọn không đọc danh sách từ máy chủ"
    for chu in ("Séc chuyển khoản", "Ủy nhiệm chi", "Séc tiền mặt",
                "Không phụ thuộc hình thức thanh toán"):
        assert chu not in than, f"trang gõ lại nhãn {chu!r} — nguồn thứ hai cho cùng một luật"

    # Thân yêu cầu trình: hai ô phải nằm trong đó, không chỉ nằm trong khuôn rỗng.
    i = than.index("const trinh")
    j = than.index("const RONG") if than.index("const RONG") > i else len(than)
    khoi = than[i:than.find("\n  };", i)]
    assert "hinh_thuc_tt:" in khoi, "hàm trình KHÔNG gửi hinh_thuc_tt"
    assert "can_khoan_muc:" in khoi, "hàm trình KHÔNG gửi can_khoan_muc"
    assert "RONG" in than and "hinh_thuc_tt" in than[than.index("const RONG"):
                                                     than.index("const RONG") + 500], \
        "khuôn rỗng thiếu hinh_thuc_tt — mở biểu mẫu sẽ là undefined"


# ─────────────────────────────────────────────────────────────── LUẬT 3
def test_r4c2_3_cua_phan_loai_them_cot_ma_khong_bo_cot_nao():
    """Cửa `/ket-so`: thêm MỘT cột, và hai ô đã có CÒN NGUYÊN.

    Một bản vá làm xanh phép đo bằng cách bỏ phần nó đo là một bản vá tự cấp phép cho mình. Nên
    luật này đòi cả hai chiều: cột mới CÓ, và `ma_doi_tuong` cùng ô `Phân loại` KHÔNG mất.
    """
    than = _khong_loi_noi(TRANG_KS.read_text(encoding="utf-8"))

    assert "hinh_thuc_tt" in than, "bảng chưa định khoản KHÔNG có cột hình thức"
    assert re.search(r"sk\?\.hinh_thuc_tt|sk\.hinh_thuc_tt", than), \
        "cột hình thức không đọc danh sách từ phản hồi máy chủ"
    for chu in ("Séc chuyển khoản", "Ủy nhiệm chi"):
        assert chu not in than, f"trang gõ lại nhãn {chu!r}"

    # Ghi vào cùng một sổ `pl` mà nút ghi lô đang gửi đi — không dựng sổ thứ hai.
    assert 'datPl(x.id, "hinh_thuc_tt"' in than, "ô mới không ghi vào sổ phân loại `pl`"
    assert 'datPl(x.id, "ma_doi_tuong"' in than, "ô mã đối tượng đã có bị mất"
    assert "phan_loai_giup_khop" in than, "ô Phân loại đã có bị mất"
    assert "phan_loai: pl" in than, "nút ghi lô không còn gửi sổ phân loại"


# ─────────────────────────────────────────────────────────────── LUẬT 4
def test_r4c2_4_duong_chay_that_quy_tac_tien_mat_khop_duoc():
    """PHÉP ĐO QUAN TRỌNG NHẤT CỦA ĐỢT: đi đúng đường người dùng đi.

    Cùng MỘT dòng sao kê, chỉ đổi `hinh_thuc_tt` trong sổ phân loại:
      · không đổi  → khớp quy tắc NGÂN HÀNG, vế tiền 112x
      · 'tien_mat' → khớp quy tắc TIỀN MẶT,  vế tiền 1111

    Đây là chỗ chứng minh sáu quy tắc tiền mặt của Đợt R2 từ nay KHỚP ĐƯỢC. Soi chữ trong tệp
    `.tsx` không chứng minh được điều đó: nó chỉ chứng minh có một ô trên màn hình.
    """
    db = _rieng()
    t = BankTransaction(sepay_id="R4C2-TM-1", transfer_type="out", amount=5_000_000.0,
                        transaction_date=datetime(2026, 10, 15, 9, 0),
                        content="TAM UNG HDV DOAN DL2610", reference_code="")
    db.add(t)
    db.commit()

    pl_ck = {t.id: {"muc_chi": "tam_ung", "ma_doi_tuong": "NV001"}}
    pl_tm = {t.id: {"muc_chi": "tam_ung", "ma_doi_tuong": "NV001",
                    "hinh_thuc_tt": "tien_mat"}}

    def _ve_tien(phan_loai):
        xt = KS.xem_truoc_sao_ke(db, "2026-10", phan_loai)
        hop = [x for x in xt["khop"] if x["id"] == t.id]
        assert hop, ("dòng không khớp quy ước nào — "
                     + str([x.get("ly_do") for x in xt["chua_nhan_dien"]]))
        return hop[0]["quy_tac"], [l["account"] for l in hop[0]["lines"]]

    ma_ck, tk_ck = _ve_tien(pl_ck)
    ma_tm, tk_tm = _ve_tien(pl_tm)

    assert any(k.startswith("112") for k in tk_ck), f"đường cũ không ghi 112x: {tk_ck}"
    assert any(k.startswith("1111") for k in tk_tm), f"đường tiền mặt không ghi 1111: {tk_tm}"
    assert ma_ck != ma_tm, "hai đường chọn CÙNG một quy tắc — ô mới không vào tới bối cảnh"


# ─────────────────────────────────────────────────────────────── LUẬT 5
def test_r4c2_5_dot_nay_khong_them_mot_dong_quy_tac_nao():
    """Hai chữ ký. Và mặc định của `_boi_canh` KHÔNG đổi.

    Thêm một dòng vào `MAC_DINH` là tự ký cả hai chữ ký mà chính `api/v1/hach_toan.py` dựng ra để
    chặn. Đợt này bù CỬA, không đi qua cửa.
    """
    assert len(HT.MAC_DINH) == 36, f"đợt này đã thêm/bớt MAC_DINH: {len(HT.MAC_DINH)}"
    assert len(HT.MAC_DINH_TIEN_MAT) == 6, "đợt này đã đụng sáu quy tắc tiền mặt"

    db = _rieng()
    assert HT.nap_mac_dinh(db) == 0, "nạp lần hai mà vẫn thêm dòng"

    t = BankTransaction(sepay_id="R4C2-MD-1", transfer_type="in", amount=1_000_000.0,
                        transaction_date=datetime(2026, 10, 20, 9, 0), content="CK DEN")
    db.add(t)
    db.commit()
    bc = KS._boi_canh(db, t)
    assert bc["hinh_thuc_tt"] == "chuyen_khoan", \
        "mặc định của một dòng sao kê KHÔNG còn là chuyển khoản"

    # Và sổ phân loại vẫn ghi đè được — đó là toàn bộ việc của đợt này.
    bc2 = KS._boi_canh(db, t, {"hinh_thuc_tt": "tien_mat"})
    assert bc2["hinh_thuc_tt"] == "tien_mat", "sổ phân loại không ghi đè được"
