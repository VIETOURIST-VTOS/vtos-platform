# -*- coding: utf-8 -*-
"""Đợt R5a (15/10/2026) — BỐN TÀI KHOẢN CÒN THIẾU, VÀ HÀNG RÀO ÁNH XẠ CHỈ TIÊU.

CHỖ HỎNG, ĐO ĐƯỢC TRƯỚC KHI VIẾT MỘT DÒNG MÃ NÀO

Bản BCTC bán niên ĐÃ KÝ tách tiền gửi có kỳ hạn làm hai:

    chỉ tiêu 112 (tương đương tiền)            4.203.801.096
    chỉ tiêu 123 (nắm giữ đến ngày đáo hạn)      508.355.556

Đợt E17 mở `12811` cho phần 112. Phần 123 thì **KHÔNG CÓ TÀI KHOẢN NÀO NHẬN**: `1281` là tài
khoản CHA, và sau E17 nó không còn là tài khoản chi tiết. Nên khi Kế toán nạp bộ số 31/12/2025,
508 triệu ấy không có chỗ đứng — hoặc bị từ chối, hoặc bị gõ nhầm vào 12811 và thổi phồng đúng
con số người đọc báo cáo nhìn đầu tiên: "công ty còn bao nhiêu tiền tiêu được ngay".

ĐO LẠI KHO MÃ: phương án R5a ban đầu liệt kê 15 tài khoản. MƯỜI HAI trong số đó ĐÃ CÓ từ các đợt
trước. Đợt này vì vậy chỉ mở BỐN, và bốn mã còn lại (2293, 8212, 22921, 22922) KHÔNG mở — xem
`test_r5a_5`.

TỆP NÀY CANH SÁU ĐIỀU

 1. Bốn tài khoản có mặt, đúng cha, đúng bậc, đúng ánh xạ.
 2. 12812 ăn chỉ tiêu 123, và 12811 VẪN là tài khoản DUY NHẤT ăn chỉ tiêu 112.
 3. **HÀNG RÀO**: mọi tài khoản trong danh mục phải có ít nhất một ánh xạ chỉ tiêu, trừ hai
    ngoại lệ KHAI ĐÍCH DANH. Đây mới là thứ đợt này để lại lâu dài.
 4. Ghi vào 12812 thì lên 123 — đo bằng chính bộ máy báo cáo, không đọc bảng khai.
 5. Bốn mã chưa truy được chỉ tiêu thì KHÔNG mở, và tệp này canh để không ai lặng lẽ mở chúng.
 6. Tên 12811 GIỮ NGUYÊN — tên phải nói ra LUẬT, không chỉ khớp chữ với MISA.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r5a.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import json                                                      # noqa: E402
import pathlib                                                   # noqa: E402

from sqlalchemy import create_engine                             # noqa: E402
from sqlalchemy.orm import sessionmaker                          # noqa: E402

from app.db.session import Base                                  # noqa: E402
from app.models.accounting import JournalEntry, JournalLine      # noqa: E402
from app.services import accounting as ACC                       # noqa: E402
from app.services import bctc as BCTC                            # noqa: E402

# Hai tài khoản KHÔNG có ánh xạ chỉ tiêu, và cả hai đều đúng:
#   627 chảy về 154 rồi mới ra 632 — nó không có dòng riêng trên báo cáo nào.
#   911 là tài khoản xác định kết quả, cuối kỳ về 0 — nó là chỗ đi qua, không phải chỗ đứng.
# Khai ĐÍCH DANH chứ không bỏ qua theo tiền tố: khai theo tiền tố thì ngày ai đó thêm 6271 hay
# 9111 mà quên ánh xạ, hàng rào sẽ im lặng cho qua.
KHONG_CAN_ANH_XA = {"627", "911"}

# Bốn mã CHƯA mở, và lý do. Xem `test_r5a_5`.
CHUA_MO = {"2293", "8212", "22921", "22922"}


def _chart() -> dict:
    p = pathlib.Path(ACC.__file__).resolve().parent.parent / "data" / "misa_tai_khoan.json"
    return {r["code"]: r for r in json.loads(p.read_text(encoding="utf-8"))["tai_khoan"]}


def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ — cửa hẹp của CI chạy nhiều tệp trong MỘT tiến trình, nên ghi
    vào CSDL dùng chung thì làm lệch số của tệp khác (test_misa đối chiếu tới từng đồng)."""
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    return db


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. BỐN TÀI KHOẢN
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r5a_1_bon_tai_khoan_dung_cha_dung_bac_dung_anh_xa():
    ch = _chart()
    mong = {
        "12812": ("1281", 3, "123", None, None),
        "1124":  ("112",  2, "111", None, None),
        "6426":  ("642",  2, None,  None, "26"),
        "82111": ("8211", 3, None,  None, "51"),
    }
    for ma, (cha, bac, bsd, bsc, pl) in mong.items():
        r = ch.get(ma)
        assert r is not None, f"Thiếu tài khoản {ma}"
        assert r["parent"] == cha, f"{ma}: cha phải là {cha}, đang là {r['parent']}"
        assert r["level"] == bac == len(ma) - 2, f"{ma}: bậc phải là {bac}"
        assert (r.get("bs_debit"), r.get("bs_credit"), r.get("pl_code")) == (bsd, bsc, pl), (
            f"{ma}: ánh xạ phải là {(bsd, bsc, pl)}, đang là "
            f"{(r.get('bs_debit'), r.get('bs_credit'), r.get('pl_code'))}")
        # Ánh xạ lấy từ CHA chứ không đoán — canh luôn điều đó, để lần sau ai sửa cha mà quên con
        # thì đỏ ở đây chứ không đỏ ở một con số cuối tháng.
        rc = ch[cha]
        assert (rc.get("bs_debit"), rc.get("bs_credit"), rc.get("pl_code")) == (bsd, bsc, pl), (
            f"{ma} lấy ánh xạ từ cha {cha}, mà cha nay khai khác. Hai cái phải đi cùng nhau.")


def test_r5a_2_12812_an_chi_tieu_123_va_12811_van_mot_minh_an_112():
    """Thêm một tài khoản KHÔNG được cướp chỉ tiêu của tài khoản đang có số dư thật."""
    ch = _chart()
    an_112 = sorted(c for c, r in ch.items() if (r.get("bs_debit") or "") == "112")
    assert an_112 == [ACC.TK_TUONG_DUONG_TIEN], (
        f"Chỉ tiêu 112 phải do ĐÚNG MỘT tài khoản nuôi, đang thấy: {an_112}. "
        "Hai tài khoản cùng ăn một chỉ tiêu là cộng đôi cùng một khoản tiền.")
    assert ch["12812"]["bs_debit"] == "123"
    assert ch["1281"]["bs_debit"] == "123" and ch["128"]["bs_debit"] == "123", (
        "Thêm tiểu khoản không được đổi nghĩa tài khoản cha đang có số dư thật.")


def test_r5a_3_ten_12811_giu_nguyen_vi_ten_phai_noi_ra_luat():
    """Chủ tịch chốt 15/10/2026: KHÔNG đổi tên 12811 theo chữ của MISA.

    Tên MISA là "Tiền gửi có kỳ hạn từ 1 đến 3 tháng" — HẸP HƠN luật. Một khoản gửi 2 tuần VẪN là
    tương đương tiền, nhưng tên ấy bảo là không. Đợt E17 đã chốt rằng tên tài khoản phải tự nói ra
    điều kiện, vì người gõ đọc TÊN trước khi đọc luật. Khớp chữ với MISA mà đổi lấy một cái tên
    sai luật là một món hời tồi.
    """
    ten = _chart()[ACC.TK_TUONG_DUONG_TIEN]["name"]
    assert "gốc" in ten, (
        "Tên phải giữ chữ 'gốc' — luật xét KỲ HẠN GỐC, không xét thời gian còn lại.")
    assert "3 tháng" in ten
    assert "từ 1 đến" not in ten, (
        "Đây là tên MISA, hẹp hơn luật: nó loại trừ khoản gửi dưới 1 tháng, mà khoản ấy VẪN là "
        "tương đương tiền.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. HÀNG RÀO — thứ đợt này để lại lâu dài
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r5a_4_moi_tai_khoan_deu_phai_co_anh_xa_chi_tieu():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP NÀY.

    Một tài khoản không có ánh xạ chỉ tiêu thì số dư của nó BIẾN MẤT khỏi báo cáo tài chính —
    không báo lỗi, không lệch cân, chỉ thiếu. Bảng cân đối vẫn cân vì cả hai vế cùng thiếu, nên
    không phép thử số học nào bắt được. Hàng rào này là chỗ duy nhất bắt được.

    ĐÃ THỬ PHÁ: xoá ánh xạ của một tài khoản bất kỳ → tệp này đỏ ngay, kèm tên tài khoản ấy.
    """
    ch = _chart()
    mu = sorted(c for c, r in ch.items()
                if not (r.get("bs_debit") or r.get("bs_credit") or r.get("pl_code"))
                and c not in KHONG_CAN_ANH_XA)
    assert not mu, (
        f"{len(mu)} tài khoản không có ánh xạ chỉ tiêu nào: {mu}. Số dư của chúng sẽ biến mất "
        "khỏi báo cáo tài chính mà bảng cân đối vẫn cân. Khai ánh xạ, hoặc nếu tài khoản ấy thật "
        "sự không có dòng riêng trên báo cáo thì thêm nó vào `KHONG_CAN_ANH_XA` kèm lý do.")
    # Và hai ngoại lệ phải CÓ THẬT — khai một ngoại lệ cho tài khoản không tồn tại là để lại một
    # lỗ hổng mang tên một mã đã bị xoá.
    for c in KHONG_CAN_ANH_XA:
        assert c in ch, f"Ngoại lệ {c} không có trong danh mục — gỡ nó khỏi KHONG_CAN_ANH_XA"


def test_r5a_5_bon_ma_chua_truy_duoc_chi_tieu_thi_KHONG_mo():
    """2293, 8212, 22921, 22922 — phương án có nêu, đợt này CỐ Ý không mở.

    Lý do: không truy được chỉ tiêu TT99 của chúng từ chính danh mục, và đoán một chỉ tiêu là đẩy
    tiền sang một dòng khác trên bảng cân đối MÀ BẢNG VẪN CÂN. `test_r5a_4` sẽ chặn nếu ai mở
    chúng mà để trống ánh xạ; phép thử này chặn chiều còn lại — mở chúng kèm một chỉ tiêu ĐOÁN.

    Mở được khi nào: Kế toán trưởng xác nhận chỉ tiêu. Lúc ấy xoá mã khỏi `CHUA_MO` và khai ánh
    xạ — hai việc trong cùng một lần sửa, không tách rời.
    """
    ch = _chart()
    lo = sorted(c for c in CHUA_MO if c in ch)
    assert not lo, (
        f"{lo} đã được mở mà chưa có xác nhận chỉ tiêu TT99 từ Kế toán trưởng. Nếu đã xác nhận "
        "thì gỡ mã khỏi `CHUA_MO` trong chính tệp này, cùng lần sửa khai ánh xạ.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. ĐO BẰNG BỘ MÁY BÁO CÁO, KHÔNG ĐỌC BẢNG KHAI
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r5a_6_ghi_vao_12812_thi_len_chi_tieu_123():
    """Đúng hai con số của bản đã ký, chạy qua chính `BCTC.bctc()` mà màn hình gọi."""
    db = _rieng()
    e = JournalEntry(code="R5A-1", entry_date=date(2026, 6, 30), period="2026-06",
                     description="Số dư thử Đợt R5a", status="da_ghi_so",
                     source_type="kiem_toan", source_ref="kt:20260630")
    db.add(e)
    db.flush()
    for tk, no in (("12811", 4_203_801_096), ("12812", 508_355_556)):
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=0,
                           partner_code="NH_THU"))
    db.add(JournalLine(entry_id=e.id, account_code="411", debit=0,
                       credit=4_203_801_096 + 508_355_556))
    db.commit()

    v = BCTC.balance_sheet_tt99(db, date(2026, 6, 30))["values"]
    assert v.get("112") == 4_203_801_096, (
        f"Chỉ tiêu 112 phải là 4.203.801.096, đang là {v.get('112')}")
    assert v.get("123") == 508_355_556, (
        f"Chỉ tiêu 123 phải là 508.355.556, đang là {v.get('123')}. ĐÂY LÀ CHỖ ĐỢT NÀY CHỮA: "
        "trước đợt này không có tài khoản nào nuôi chỉ tiêu 123 cho tiền gửi trên 3 tháng.")
    # KHÔNG cộng trùng: hai chỉ tiêu cộng lại đúng bằng tiền đã ghi, không hơn một đồng.
    assert v.get("112") + v.get("123") == 4_712_156_652
    assert abs(v.get("280", 0) - v.get("440", 0)) < 1, "bảng vẫn phải cân"
    db.close()
