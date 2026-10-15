# -*- coding: utf-8 -*-
"""Đợt R4a (15/10/2026) — MA TRẬN CẶP ĐỊNH KHOẢN, và đối chiếu với BẢNG QUY ƯỚC.

VÌ SAO CÓ TỆP NÀY

Bảng quy ước hạch toán nói sổ NÊN có những cặp định khoản nào. Trước đợt này không có gì nói sổ
ĐANG có những cặp nào. Hai thứ ấy lệch nhau bằng đúng những bút toán ai đó định khoản tay — và một
bút toán tay sai tài khoản thì sổ VẪN CÂN, báo cáo VẪN ra số, không phép thử nào đỏ.

TỆP NÀY CANH BẢY ĐIỀU

 1. Cặp lấy từ CHÍNH SỔ, không lấy từ bảng quy ước.
 2. Một vế Nợ – nhiều vế Có: chia đúng, KHÔNG mất một đồng nào.
 3. Nhiều Nợ – nhiều Có: **KHÔNG vào ma trận, và được đếm riêng kèm số tiền**. Đây là phép thử
    quan trọng nhất của tệp: giấu phần không chia được là tội nặng hơn không phân tích nó.
 4. Cặp có trong quy ước thì KHÔNG bị gọi là ngoài luật — kể cả khi sổ ghi tài khoản CON còn quy
    ước khai tài khoản CHA.
 5. Vế THUẾ của một quy ước cũng là cặp hợp luật.
 6. Nguồn không đi qua bảng quy ước (số dư đầu kỳ, kết chuyển, lương…) được miễn.
 7. Một cặp bịa ra thì PHẢI hiện lên — nếu không, cả báo cáo vô dụng.
"""
import os
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r4a.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

from sqlalchemy import create_engine                             # noqa: E402
from sqlalchemy.orm import sessionmaker                          # noqa: E402

from app.db.session import Base                                  # noqa: E402
from app.models.accounting import JournalEntry, JournalLine      # noqa: E402
from app.services import accounting as ACC                       # noqa: E402
from app.services import cap_dinh_khoan as CDK                   # noqa: E402
from app.services import hach_toan as HT                         # noqa: E402

DEN = date(2026, 6, 30)


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


def _ct(db, dong, nguon="thu_cong", ngay=date(2026, 3, 15)):
    """Ghi thẳng một chứng từ: (tài khoản, nợ, có). Không đi qua `post_entry` — đợt này ĐỌC sổ,
    và sổ thật có cả những bút toán không đi qua cửa ấy."""
    _n[0] += 1
    e = JournalEntry(code=f"R4A-{_n[0]}", entry_date=ngay, ngay_chung_tu=ngay,
                     period=f"{ngay:%Y-%m}", description="Sổ thử Đợt R4a",
                     status="da_ghi_so", source_type=nguon, source_ref="")
    db.add(e)
    db.flush()
    for tk, no, co in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co))
    db.commit()
    return e


def _cap(rep, no, co):
    return next((c for c in rep["cap"] if c["tk_no"] == no and c["tk_co"] == co), None)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. MA TRẬN ĐỌC TỪ SỔ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4a_1_cap_lay_tu_so_khong_lay_tu_quy_uoc():
    db = _rieng()
    _ct(db, [("1121", 100_000_000, 0), ("131", 0, 100_000_000)])
    _ct(db, [("1121", 50_000_000, 0), ("131", 0, 50_000_000)])
    rep = CDK.ma_tran(db, DEN)
    c = _cap(rep, "1121", "131")
    assert c is not None, "Cặp có thật trong sổ mà không lên ma trận"
    assert c["so_tien"] == 150_000_000 and c["so_chung_tu"] == 2
    assert rep["so_cap"] == 1, f"Chỉ có một cặp trong sổ, ma trận báo {rep['so_cap']}"
    db.close()


def test_r4a_2_mot_no_nhieu_co_chia_dung_khong_mat_dong_nao():
    """Doanh thu tách thuế: Nợ 131 / Có 5113 + Có 3331."""
    db = _rieng()
    _ct(db, [("131", 108_000_000, 0), ("5113", 0, 100_000_000), ("3331", 0, 8_000_000)])
    rep = CDK.ma_tran(db, DEN)
    assert _cap(rep, "131", "5113")["so_tien"] == 100_000_000
    assert _cap(rep, "131", "3331")["so_tien"] == 8_000_000
    assert rep["tong_tien"] == 108_000_000, (
        f"Tổng ma trận phải đúng bằng tiền đã ghi (108.000.000), đang là {rep['tong_tien']} — "
        "chia mà mất hoặc thừa một đồng thì cả báo cáo không tin được.")
    db.close()


def test_r4a_3_mot_co_nhieu_no_cung_chia_dung():
    db = _rieng()
    _ct(db, [("154", 100_000_000, 0), ("133", 8_000_000, 0), ("331", 0, 108_000_000)])
    rep = CDK.ma_tran(db, DEN)
    assert _cap(rep, "154", "331")["so_tien"] == 100_000_000
    assert _cap(rep, "133", "331")["so_tien"] == 8_000_000
    assert rep["tong_tien"] == 108_000_000
    db.close()


def test_r4a_4_nhieu_nhieu_KHONG_vao_ma_tran_va_duoc_dem_rieng():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP NÀY.

    Hai vế Nợ và hai vế Có cho BỐN cặp, mà tiền của từng cặp không nằm ở đâu trong sổ cả. Chia đều
    là bịa ra một con số chưa từng được ghi rồi đặt nó vào một báo cáo người đọc tin là đọc từ sổ.

    Và giấu nó đi còn tệ hơn: người đọc sẽ thấy một ma trận trông đầy đủ mà thiếu thầm. Nên nó
    phải được ĐẾM RIÊNG, kèm số tiền và mã chứng từ.
    """
    db = _rieng()
    _ct(db, [("1121", 60_000_000, 0), ("1111", 40_000_000, 0),
             ("131", 0, 70_000_000), ("3388", 0, 30_000_000)])
    rep = CDK.ma_tran(db, DEN)
    assert rep["so_cap"] == 0, (
        f"Chứng từ nhiều–nhiều KHÔNG được vào ma trận, đang thấy {rep['so_cap']} cặp. "
        "Một con số chia bừa trong báo cáo nguy hiểm hơn một ô trống.")
    nn = rep["nhieu_nhieu"]
    assert nn["so_chung_tu"] == 1, "Phải đếm riêng chứng từ không chia được"
    assert nn["so_tien"] == 100_000_000, (
        f"Phải nói ra SỐ TIỀN không được phân tích, đang là {nn['so_tien']}. Không nói số tiền "
        "thì người đọc không biết phần thiếu là 100 triệu hay 100 tỷ.")
    assert nn["chung_tu"], "Phải liệt kê mã chứng từ để còn lần ra được"
    db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. ĐỐI CHIẾU VỚI BẢNG QUY ƯỚC
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4a_5_cap_co_trong_quy_uoc_thi_khong_bi_goi_la_ngoai_luat():
    """Kể cả khi sổ ghi tài khoản CON còn quy ước khai tài khoản CHA — lệ V8."""
    db = _rieng()
    # DOANH_THU khai Nợ 131 / Có 5113; sổ ghi 51131 (tài khoản con, mở ở Đợt R5a).
    _ct(db, [("131", 100_000_000, 0), ("51131", 0, 100_000_000)])
    rep = CDK.ngoai_luat(db, DEN)
    assert rep["so_cap_ngoai_luat"] == 0, (
        f"Cặp 131/51131 nằm dưới quy ước 131/5113 nên KHÔNG ngoài luật, đang báo: "
        f"{rep['cap_ngoai_luat']}")
    db.close()


def test_r4a_6_ve_thue_cua_quy_uoc_cung_la_cap_hop_luat():
    db = _rieng()
    # MUA_CO_HD: Nợ 154 / Có 331, thuế đầu vào Nợ 133.
    _ct(db, [("154", 100_000_000, 0), ("133", 8_000_000, 0), ("331", 0, 108_000_000)])
    rep = CDK.ngoai_luat(db, DEN)
    assert rep["so_cap_ngoai_luat"] == 0, (
        f"Vế thuế 133/331 do chính quy ước MUA_CO_HD sinh ra, không được gọi là ngoài luật: "
        f"{rep['cap_ngoai_luat']}")
    db.close()


def test_r4a_7_nguon_khong_qua_quy_uoc_thi_duoc_mien():
    db = _rieng()
    _ct(db, [("1111", 500_000_000, 0), ("411", 0, 500_000_000)], nguon="so_du_dau_ky")
    _ct(db, [("5113", 900_000_000, 0), ("911", 0, 900_000_000)], nguon="ket_chuyen")
    rep = CDK.ngoai_luat(db, DEN)
    assert rep["so_cap_ngoai_luat"] == 0, (
        f"Số dư đầu kỳ và kết chuyển không đi qua bảng quy ước: {rep['cap_ngoai_luat']}")
    assert set(rep["nguon_duoc_mien"]) >= {"so_du_dau_ky", "ket_chuyen"}
    db.close()


def test_r4a_8_mot_cap_bia_ra_thi_PHAI_hien_len():
    """Nếu phép thử này xanh mà không có gì hiện lên thì cả báo cáo vô dụng.

    Cặp dựng ở đây là một bút toán tay sai thật: ghi hoa hồng bán tour thẳng vào phải trả người
    lao động, thay vì vào phải trả nhà cung cấp (HOA_HONG khai 641/331). Sổ VẪN CÂN, báo cáo VẪN
    ra số, công nợ NCC thiếu đúng khoản ấy và quỹ lương thừa đúng khoản ấy — không hàng rào nào
    khác bắt được.

    MỘT CHỖ PHÉP THỬ NÀY BẮT ĐƯỢC TRONG LÚC VIẾT: bản đầu dùng cặp 6428/2141 làm cặp "bịa", và
    báo cáo nói nó HỢP LUẬT. Báo cáo đúng, phép thử sai: 6428 nằm dưới quy ước khấu hao 642/2141.
    Giữ lại ghi chú này vì nó là bằng chứng phép so theo tài khoản CHA chạy đúng.
    """
    db = _rieng()
    _ct(db, [("641", 77_000_000, 0), ("334", 0, 77_000_000)])
    rep = CDK.ngoai_luat(db, DEN)
    assert rep["so_cap_ngoai_luat"] == 1, (
        f"Cặp 641/334 phải hiện lên, đang có {rep['so_cap_ngoai_luat']} cặp ngoài luật")
    c = rep["cap_ngoai_luat"][0]
    assert (c["tk_no"], c["tk_co"]) == ("641", "334")
    assert rep["so_tien_ngoai_luat"] == 77_000_000, (
        "Phải nói ra số tiền ngoài luật — một cặp lạ trị giá 7.000đ và một cặp lạ trị giá 77 triệu "
        "là hai mức độ khẩn khác hẳn nhau.")
    assert rep["ghi_chu"] and "KHÔNG đương nhiên là sai" in rep["ghi_chu"], (
        "Báo cáo phải tự nói rằng ngoài luật chưa chắc là sai — gọi nó là lỗi thì người đọc sẽ "
        "sửa bút toán đúng cho vừa một bảng quy ước còn thiếu dòng.")
    db.close()


def test_r4a_9_bao_cao_ngoai_luat_mang_theo_phan_khong_chia_duoc():
    """Không mang theo thì 'sổ sạch' là một kết luận đọc từ một báo cáo đã bỏ sót phần lớn nhất."""
    db = _rieng()
    _ct(db, [("1121", 60_000_000, 0), ("1111", 40_000_000, 0),
             ("131", 0, 70_000_000), ("3388", 0, 30_000_000)])
    rep = CDK.ngoai_luat(db, DEN)
    assert rep["so_cap_ngoai_luat"] == 0
    assert rep["nhieu_nhieu"]["so_chung_tu"] == 1, (
        "Báo cáo ngoài luật phải mang theo phần không chia được. Thiếu nó, người đọc thấy "
        "'0 cặp ngoài luật' và kết luận sổ sạch, trong khi 100 triệu chưa hề được xét.")
    db.close()
