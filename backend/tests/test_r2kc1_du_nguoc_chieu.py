# -*- coding: utf-8 -*-
"""ĐỢT R2-KC1 (24/10/2026) — SỐ DƯ NGƯỢC CHIỀU: NÓI RA, VÀ KẾT CHUYỂN ĐƯỢC THẬT.

VÌ SAO CÓ TỆP NÀY

Cờ `nguoc_chieu` đã nằm trong `ket_so.py` từ lâu và nó ĐÚNG. Nhưng ngày 23/10/2026 rà cả kho thì
`nguoc_chieu` xuất hiện ở ĐÚNG HAI tệp backend và KHÔNG tệp web nào — cái dấu ấy không vào
`canh_bao`, nên `tinh_trang_ky` không thấy, nên `/ket-so` không vẽ, nên **không người nào đọc
được nó**. Một dấu không ai đọc được thì bằng không có dấu.

VÀ BẢN 1 CỦA ĐỢT NÀY, CHẠY ĐÊM 23/10, ĐÃ ĐỎ — ĐỎ ĐÚNG

Nó lôi ra một chỗ hỏng nặng hơn: `ket_chuyen` bê thẳng `so_tien` ÂM của dòng dư ngược chiều vào
`lines`, nên `post_entry` chặn. Nghĩa là quyết định "VẪN kết chuyển" của Chủ tịch 23/10/2026
**chưa từng chạy được** — chỉ chưa ai biết, vì trước đợt này không phép thử nào dựng một sổ có dư
ngược chiều. `test_r2kc1_6` là phép thử ấy, và nó là lý do tệp này tồn tại.

KHÔNG CHẶN. Chủ tịch chốt 23/10/2026: hàng bán bị trả lại nhiều hơn doanh thu là việc CÓ THẬT.
Chặn kỳ vì nó là đổi một chỗ hỏng thành chỗ hỏng ngược lại — bài học Đợt F1 10/10/2026.
`test_r2kc1_3` đỏ nếu ai đó biến cảnh báo này thành một cái chặn.
"""
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from types import SimpleNamespace                                # noqa: E402

from sqlalchemy import create_engine, select                     # noqa: E402
from sqlalchemy.orm import sessionmaker                          # noqa: E402

from app.db.session import Base                                  # noqa: E402
from app.models.accounting import Account, JournalEntry, JournalLine   # noqa: E402
from app.services import accounting as ACC                       # noqa: E402
from app.services import hach_toan as HT                          # noqa: E402
from app.services import ket_so as KS                             # noqa: E402

# KHÔNG ĐẶT `os.environ["DATABASE_URL"]` Ở ĐÂY.
#
# Bản 1 đặt biến ấy trỏ sang một tệp sqlite riêng rồi XOÁ tệp đó — và chính nó không hề dùng tới
# biến ấy (mọi phép thử dưới đây chạy trên `_rieng()`, một CSDL trong bộ nhớ). Hàng rào gộp chạy
# nhiều tệp phép thử trong MỘT tiến trình, nên một dòng như thế là đặt mìn dưới chân tệp khác:
# đêm 23/10 nó đi kèm ba phép thử `test_misa` đỏ với số lệch 10 và 11 triệu.
#
# Luật rút ra: một tệp phép thử không được sửa biến môi trường dùng chung, nhất là biến nó không
# dùng.

KY = "2026-06"
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KE_TOAN = SimpleNamespace(username="ketoan_thu", role="ketoan", full_name="Kế toán thử")


def _rieng():
    """MỘT CSDL RIÊNG TRONG BỘ NHỚ — cửa hẹp của CI chạy nhiều tệp trong MỘT tiến trình."""
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    HT.nap_mac_dinh(db)
    return db


_n = [0]


def _ct(db, dong, ngay=date(2026, 6, 15)):
    """Ghi thẳng một chứng từ: (tài khoản, nợ, có). Không đi qua `post_entry` — đợt này ĐỌC sổ,
    và sổ thật có cả những bút toán không đi qua cửa ấy."""
    _n[0] += 1
    e = JournalEntry(code=f"R2KC1-{_n[0]}", entry_date=ngay, ngay_chung_tu=ngay,
                     period=f"{ngay:%Y-%m}", description="Sổ thử Đợt R2-KC1",
                     status="da_ghi_so", source_type="thu_cong", source_ref="")
    db.add(e)
    db.flush()
    for tk, no, co in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co))
    db.commit()
    return e


def _so_binh_thuong(db):
    """Doanh thu ghi ĐÚNG chiều: Nợ 131 / Có 5113."""
    _ct(db, [("131", 100_000_000, 0), ("5113", 0, 100_000_000)])
    _ct(db, [("632", 60_000_000, 0), ("156", 0, 60_000_000)])


def _so_nguoc_chieu(db):
    """5113 còn dư NỢ — hàng bán bị trả lại nhiều hơn doanh thu, hoặc ai đó ghi sai chiều.

    Sổ vẫn cân từng chứng từ. Đó chính là lý do không có gì bắt được nó trước đợt này.
    """
    _ct(db, [("131", 100_000_000, 0), ("5113", 0, 100_000_000)])
    _ct(db, [("5113", 140_000_000, 0), ("131", 0, 140_000_000)])


def _cau(ds):
    return next((c for c in ds if "NGƯỢC CHIỀU" in c.upper()), "")


def _dong_cua(db, ma_ct):
    e = db.execute(select(JournalEntry).where(JournalEntry.code == ma_ct)).scalars().first()
    assert e is not None, f"không tìm thấy chứng từ {ma_ct}"
    return list(e.lines)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. DƯ NGƯỢC CHIỀU PHẢI HIỆN RA, KÈM TÊN TÀI KHOẢN
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_1_du_nguoc_chieu_phai_hien_ra_kem_ten_tai_khoan():
    """Đòi cả hai: khóa `du_nguoc_chieu` để máy đọc, VÀ một câu trong `canh_bao` để người đọc.

    Thiếu câu thứ hai thì ta quay về đúng tình trạng trước đợt này — có dấu mà không ai thấy.
    Và câu ấy phải mang TÊN TÀI KHOẢN: "có 1 tài khoản bất thường" không cho ai làm được gì.
    """
    db = _rieng()
    _so_nguoc_chieu(db)
    xt = KS.xem_truoc_ket_chuyen(db, KY)
    assert xt["du_nguoc_chieu"], (
        "Sổ có 5113 dư NỢ (ngược chiều với bước kết chuyển doanh thu) mà `du_nguoc_chieu` rỗng.")
    assert any(x["tk"].startswith("5113") for x in xt["du_nguoc_chieu"]), \
        f"phải chỉ đích danh 5113, đang thấy: {xt['du_nguoc_chieu']}"
    c = _cau(xt["canh_bao"])
    assert c, ("Có dòng dư ngược chiều mà `canh_bao` không nói gì. Một dấu không ai đọc được thì "
               f"bằng không có dấu. canh_bao đang là: {xt['canh_bao']}")
    assert "5113" in c, f"câu cảnh báo phải mang tên tài khoản, đang là: {c}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. SỔ BÌNH THƯỜNG THÌ IM — KHÔNG REO GIẢ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_2_so_binh_thuong_thi_khong_reo():
    """Reo giả lặp lại là cách nhanh nhất để người ta thôi đọc cảnh báo — và lúc ấy cảnh báo
    thật cũng chết theo. Nên phép thử này canh chiều ngược lại của phép thử 1."""
    db = _rieng()
    _so_binh_thuong(db)
    xt = KS.xem_truoc_ket_chuyen(db, KY)
    assert not xt["du_nguoc_chieu"], f"sổ ghi đúng chiều mà vẫn báo: {xt['du_nguoc_chieu']}"
    assert not _cau(xt["canh_bao"]), f"reo giả: {_cau(xt['canh_bao'])}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. VẪN KẾT CHUYỂN ĐƯỢC — CHỦ TỊCH CHỐT 23/10/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_3_canh_bao_KHONG_duoc_bien_thanh_mot_cai_chan():
    """Đợt này mở MỘT CÁI MIỆNG, không dựng một cái cổng.

    Hàng bán bị trả lại nhiều hơn doanh thu là việc CÓ THẬT. Chặn kỳ vì nó là đổi một chỗ hỏng
    thành chỗ hỏng ngược lại — bài học Đợt F1 10/10/2026. Phép thử này đỏ nếu ai đó, vì thiện
    chí, biến cảnh báo thành điều kiện chặn.
    """
    db = _rieng()
    _so_nguoc_chieu(db)
    kq = KS.ket_chuyen(db, KE_TOAN, KY, buoc_chon=[1])
    assert kq["da_ghi"], (
        "Có dư ngược chiều thì VẪN phải kết chuyển được (Chủ tịch chốt 23/10/2026). "
        f"Không ghi được bước nào. Bỏ qua: {kq['bo_qua']}")
    assert _cau(kq["canh_bao"]), "ghi xong vẫn phải mang theo câu cảnh báo"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. CÂU ẤY PHẢI ĐI TỚI MÀN HÌNH — KHÔNG SỬA MỘT DÒNG WEB NÀO
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_4_cau_canh_bao_di_toi_duoc_man_hinh_ket_so():
    """`/ket-so` đọc `tinh_trang_ky()["canh_bao"]` và đã vẽ sẵn khối `.warn` cho nó từ trước.

    Nối vào ĐÚNG đường ấy là lý do đợt này không đụng một dòng web nào. Phép thử canh rằng
    đường ấy còn thông — nếu ai đó sau này dựng một khóa riêng cho cảnh báo kết chuyển, câu này
    sẽ rụng giữa đường và không ai biết.
    """
    db = _rieng()
    _so_nguoc_chieu(db)
    tt = KS.tinh_trang_ky(db, KY)
    assert _cau(tt["canh_bao"]), (
        "Câu cảnh báo dư ngược chiều không đi tới `tinh_trang_ky`, nên màn hình `/ket-so` không "
        f"bao giờ hiện nó. canh_bao của kỳ: {tt['canh_bao']}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. LUẬT KHAI Ở MÁY CHỦ, KHÔNG CHÉP XUỐNG MÀN HÌNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_5_man_hinh_KHONG_duoc_tu_dung_cau_canh_bao():
    """Cùng luật mà Đợt R4b-2b đã đặt cho màn hình Hóa đơn còn thiếu.

    Màn hình chỉ BÀY câu máy chủ gửi xuống. Gõ tay một câu tương tự vào `page.tsx` là có hai bản
    khai cho một luật, và lúc chúng lệch thì không ai biết bên nào đúng.
    """
    p = os.path.join(GOC, "..", "web", "app", "ket-so", "page.tsx")
    if not os.path.exists(p):
        return  # nhánh backend-only: không có cây web thì không có gì để canh
    with open(p, encoding="utf-8") as f:
        ma = f.read()
    for xau in ("ngược chiều", "NGƯỢC CHIỀU", "nguoc_chieu"):
        assert xau not in ma, (
            f"`web/app/ket-so/page.tsx` nhắc tới {xau!r}. Luật này khai ở máy chủ "
            "(`ket_so.xem_truoc_ket_chuyen`) và đi xuống qua `canh_bao`; màn hình chỉ bày.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. SỔ KHÔNG BAO GIỜ CHỨA SỐ ÂM — PHÉP THỬ LÀM CHO QUYẾT ĐỊNH 23/10 CHẠY ĐƯỢC THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_6_ket_chuyen_du_nguoc_chieu_khong_duoc_ghi_mot_so_am_nao():
    """ĐÂY LÀ PHÉP THỬ ĐÃ LÔI RA CHỖ HỎNG THẬT, đêm 23/10/2026.

    `test_r2kc1_3` chỉ hỏi "có ghi được không". Phép thử này hỏi tiếp: **ghi ra cái gì**. Bản cũ
    ghi `{5113: debit -40.000.000}` và `{911: credit -40.000.000}` — hai số bằng nhau nên trông
    như cân, nhưng sổ không chứa số âm bao giờ: mọi câu tổng hợp đều cộng `debit` và `credit`
    như số dương, nên một dòng âm làm lệch đúng hai lần trị tuyệt đối của nó, ở hai bên.

    Nên luật ở đây không phải "ghi được", mà là: **không một dòng nào mang số âm**, và chứng từ
    cân bằng chính nó.
    """
    db = _rieng()
    _so_nguoc_chieu(db)
    kq = KS.ket_chuyen(db, KE_TOAN, KY, buoc_chon=[1])
    assert kq["da_ghi"], f"không ghi được bước 1. Bỏ qua: {kq['bo_qua']}"
    dong = _dong_cua(db, kq["da_ghi"][0]["chung_tu"])
    am = [(l.account_code, l.debit, l.credit) for l in dong
          if (l.debit or 0) < 0 or (l.credit or 0) < 0]
    assert not am, (
        "Chứng từ kết chuyển có dòng mang SỐ ÂM: " + repr(am) + ". Dòng dư ngược chiều phải được "
        "ĐẢO CHIỀU (ghi sang bên kia với trị tuyệt đối), không được ghi dấu trừ vào sổ.")
    td = round(sum(float(l.debit or 0) for l in dong), 0)
    tc = round(sum(float(l.credit or 0) for l in dong), 0)
    assert td > 0 and abs(td - tc) < 1, f"chứng từ không cân: Nợ {td:,.0f} / Có {tc:,.0f}"
    # 5113 dư Nợ 40tr ở bước đóng số dư CÓ -> đảo chiều thành CÓ 5113 40tr.
    tk5113 = [l for l in dong if l.account_code.startswith("5113")]
    assert tk5113, f"chứng từ không có dòng 5113: {[l.account_code for l in dong]}"
    assert round(float(tk5113[0].credit or 0), 0) == 40_000_000, (
        "5113 đang dư NỢ 40tr, kết chuyển phải ghi CÓ 5113 40tr để đóng nó. Đang thấy "
        f"Nợ {tk5113[0].debit} / Có {tk5113[0].credit}.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7. BƯỚC NÉT BẰNG 0 MÀ CÓ DÒNG THÌ VẪN PHẢI GHI — CHỦ TỊCH KÝ 24/10/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_7_buoc_net_bang_0_ma_co_dong_thi_van_phai_ghi():
    """Lỗ im lặng có sẵn trước đợt này, Chủ tịch ký dọn luôn 24/10/2026.

    `ket_chuyen` từng bỏ qua một bước khi `abs(tong) < 1`. Nhưng nét 0 KHÔNG CÓ NGHĨA là không
    có gì để đóng: một dòng thuận 100tr và một dòng ngược 100tr triệt tiêu nhau đúng bằng 0 thì
    bước ấy bị bỏ qua, và **cả hai số dư nằm lại trên sổ** — không bút toán nào đóng chúng,
    không câu nào báo, và kỳ sau chúng vẫn ở đó.

    Nay bỏ qua chỉ khi KHÔNG CÓ DÒNG NÀO. Nét 0 thì vẫn ghi, và chứng từ đóng hai bên vào nhau
    mà không đụng tới 911 — vì quả thật kỳ này hai khoản ấy không ra kết quả kinh doanh nào.
    """
    db = _rieng()
    ma = sorted(a.code for a in db.execute(select(Account)).scalars()
                if a.code.startswith(("511", "515", "711")) and a.is_detail)
    if len(ma) < 2:
        pytest.skip(f"danh mục chỉ có {len(ma)} tài khoản chi tiết ở bước 1, cần 2 để dựng nét 0")
    a, b = ma[0], ma[1]
    _ct(db, [("131", 100_000_000, 0), (a, 0, 100_000_000)])     # a dư CÓ 100tr (thuận)
    _ct(db, [(b, 100_000_000, 0), ("131", 0, 100_000_000)])     # b dư NỢ 100tr (ngược)
    xt = KS.xem_truoc_ket_chuyen(db, KY)
    b1 = next(x for x in xt["buoc"] if x["buoc"] == 1)
    assert abs(b1["tong"]) < 1, f"phép thử này cần bước 1 nét 0, đang là {b1['tong']}"
    assert b1["dong"], "bước 1 phải có dòng — nếu không thì phép thử đang dựng sai"

    kq = KS.ket_chuyen(db, KE_TOAN, KY, buoc_chon=[1])
    assert kq["da_ghi"], (
        f"Bước 1 nét 0 nhưng CÓ {len(b1['dong'])} dòng thật ({a}, {b}) mà vẫn bị bỏ qua: "
        f"{kq['bo_qua']}. Bỏ qua ở đây là để số dư hai bên nằm lại trên sổ, không ai đóng.")
    dong = _dong_cua(db, kq["da_ghi"][0]["chung_tu"])
    co = {l.account_code for l in dong}
    assert a in co and b in co, f"chứng từ phải đóng cả hai tài khoản, đang có: {sorted(co)}"
    assert "911" not in co, (
        "nét 0 thì không có phần nào ra kết quả kinh doanh, nên không được chạm 911: "
        f"{sorted(co)}")
    td = round(sum(float(l.debit or 0) for l in dong), 0)
    tc = round(sum(float(l.credit or 0) for l in dong), 0)
    assert td > 0 and abs(td - tc) < 1, f"chứng từ không cân: Nợ {td:,.0f} / Có {tc:,.0f}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 8. CÂU BÁO LỖI PHẢI NÓI ĐÚNG CHỖ HỎNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r2kc1_8_cau_bao_loi_tong_no_khong_duong_khong_duoc_noi_la_khong_can():
    """Đêm 23/10/2026 tốn một đêm vì đúng câu này.

    `post_entry` gộp hai điều kiện — `td <= 0` và `abs(td - tc) >= 1` — vào một câu báo chỉ kể
    chuyện thứ hai. Gọi nó với Nợ = Có = -40.000.000 thì nó in ra **hai số bằng nhau** rồi bảo
    "≠", và người đọc đi tìm chỗ lệch tiền trong khi chỗ hỏng là một dòng ghi số âm.

    Một câu báo lỗi nói sai chỗ hỏng còn tệ hơn không có câu nào. Phép thử này đỏ nếu ai đó gộp
    hai điều kiện ấy lại lần nữa.
    """
    db = _rieng()
    with pytest.raises(ValueError) as ex:
        ACC.post_entry(db, "ketoan_thu", "ketoan", date(2026, 6, 15), "thử số âm",
                       [{"account": "5113", "debit": -40_000_000},
                        {"account": "911", "credit": -40_000_000}],
                       "thu_cong", "", nghiep_vu="but_toan_tay")
    c = str(ex.value)
    assert "≠" not in c, (
        "Tổng Nợ và tổng Có BẰNG NHAU (cùng -40.000.000); chỗ hỏng là tổng Nợ không dương. "
        f"Câu báo không được nói là hai bên không bằng nhau. Đang là: {c}")
    assert "DƯƠNG" in c.upper(), (
        f"câu báo phải nói rõ tổng Nợ phải là số dương. Đang là: {c}")
