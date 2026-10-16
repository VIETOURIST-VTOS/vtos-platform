# -*- coding: utf-8 -*-
"""Đợt R3a — DỌN HAI CHIỀU trước khi viết bộ máy báo cáo theo chiều.

Tệp này KHÔNG kiểm một con số tiền nào. Nó kiểm những thứ mà sai thì BÁO CÁO VẪN RA SỐ, VẪN CỘNG
ĐÚNG TỔNG, và chỉ người đọc mới thấy lạ — tức là loại hỏng không phép thử số học nào bắt được.
"""
import pathlib
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.services import khoan_muc_chi as KMC
from app.services import khoan_muc_chi_phi as KMCP

GOC = pathlib.Path(__file__).resolve().parents[1] / "app"


@pytest.fixture()
def db():
    """Cơ sở dữ liệu RIÊNG trong bộ nhớ — không dùng chung với tệp phép thử nào khác."""
    eng = create_engine("sqlite://", future=True)
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng, future=True)()
    try:
        yield s
    finally:
        s.close()


def test_r3a_1_journal_line_co_cot_bo_phan(db):
    """Cột `bo_phan` phải có thật trong lược đồ, không chỉ có trong mã Python."""
    cols = {c["name"] for c in inspect(db.get_bind()).get_columns("journal_lines")}
    assert "bo_phan" in cols, "journal_lines thiếu cột bo_phan"
    assert "item_code" in cols


def test_r3a_2_assets_khong_con_ghi_bo_phan_vao_item_code():
    """`assets.py` KHÔNG được ghi mã bộ phận vào cột khoản mục nữa.

    Kiểm trên MÃ ĐANG CHẠY chứ không trên lời kể: chuỗi phải biến mất khỏi tệp.
    """
    s = (GOC / "services" / "assets.py").read_text(encoding="utf-8")
    assert '"item_code": dept' not in s, "assets.py vẫn ghi mã bộ phận vào item_code"
    assert s.count('"bo_phan": dept') == 4, "phải có đúng bốn chỗ ghi bộ phận (khấu hao 2 + phân bổ 2)"


def test_r3a_3_ban_di_tru_chuyen_dung_hai_nguon():
    """Bản di trú phải chuyển dữ liệu cũ, và chọn đúng hai nguồn đã đo được."""
    d = GOC.parent / "alembic" / "versions"
    tep = [p for p in d.glob("*.py") if "tach_bo_phan" in p.name]
    assert len(tep) == 1, "phải có đúng một bản di trú tách bộ phận"
    s = tep[0].read_text(encoding="utf-8")
    assert "UPDATE journal_lines SET bo_phan = item_code" in s, "thiếu câu chuyển dữ liệu cũ"
    assert "'khau_hao', 'phan_bo'" in s, "phải chọn đúng hai nguồn ghi bộ phận"
    assert "item_code <> ''" in s, "thiếu điều kiện bỏ qua dòng rỗng"
    assert "def downgrade" in s and "SET item_code = bo_phan" in s, "phải lùi được"


def test_r3a_4_hai_chieu_kia_deu_co_chi_muc(db):
    """`item_code` phải có chỉ mục như hai chiều đã có báo cáo.

    Không có chỉ mục thì phép gom theo chiều này quét toàn bảng — trên SQLite không ai thấy, trên
    Postgres với sổ thật thì thấy. Nên hỏi ở đây, chỗ duy nhất hỏi được.
    """
    cot = set()
    for idx in inspect(db.get_bind()).get_indexes("journal_lines"):
        cot.update(idx["column_names"])
    for c in ("partner_code", "project_code", "item_code", "bo_phan"):
        assert c in cot, f"cột chiều `{c}` không có chỉ mục"


def test_r3a_5_ba_ma_khoan_muc_moi_co_mat(db):
    KMCP.nap_mac_dinh(db)
    db.commit()
    ma = {k["ma"] for k in KMCP.danh_sach(db)}
    for m in ("KM_VCK", "KM_QUA", "KM_PHI"):
        assert m in ma, f"thiếu mã khoản mục {m}"


def test_r3a_6_moi_ma_quyet_toan_deu_noi_duoc_sang_so_cai(db):
    """HÀNG RÀO CHÍNH CỦA ĐỢT NÀY.

    Mọi mã của danh mục quyết toán phải nối được sang một mã khoản mục sổ cái CÓ THẬT. Thiếu một
    mã thì tiền của nó biến mất khỏi báo cáo theo khoản mục — mà tổng vẫn cân, vì nó cũng biến mất
    khỏi mẫu số. Đây là chỗ duy nhất bắt được.
    """
    KMCP.nap_mac_dinh(db)
    db.commit()
    co_that = {k["ma"] for k in KMCP.danh_sach(db)}

    thieu = [ma for ma in KMC.KHOAN_MUC if not KMC.km_cua(ma)]
    assert not thieu, f"mã quyết toán chưa nối sang sổ cái: {thieu}"

    la = sorted({v for v in KMC.KM_CUA.values() if v not in co_that})
    assert not la, f"nối sang mã khoản mục KHÔNG CÓ trong danh mục sổ cái: {la}"

    thua = sorted(set(KMC.KM_CUA) - set(KMC.KHOAN_MUC))
    assert not thua, f"bảng nối khai mã không có trong danh mục quyết toán: {thua}"


def test_r3a_7_khong_doan_khi_khong_biet():
    """Mã lạ phải trả RỖNG, không được tự đổ vào KM_KHAC.

    Rỗng nói "chưa ai nối mã này"; KM_KHAC nói "đã xét, nó thuộc nhóm khác". Gộp hai câu ấy lại thì
    một mã bị bỏ quên trông y hệt một mã đã được quyết định.
    """
    assert KMC.km_cua("khong_co_ma_nay") == ""
    assert KMC.km_cua("") == ""
    assert KMC.km_cua(None) == ""


def test_r3a_8_bon_nhom_dung_cho_sau_khi_chot():
    """Bốn quyết định 16/10/2026 — ghim lại để lần sau ai sửa thì phải nói ra mình đang sửa gì."""
    assert KMC.km_cua("vc_tau_hoa") == "KM_VCK"
    assert KMC.km_cua("vc_tau_thuy") == "KM_VCK"
    # vé máy bay CỦA hướng dẫn viên là chi phí hướng dẫn, không phải vé của khách
    assert KMC.km_cua("hd_ve_may_bay_hdv") == "KM_HDV"
    assert KMC.km_cua("vc_ve_may_bay") == "KM_VEMB"
    # thuế lưu trú địa phương là thuế CỦA việc lưu trú
    assert KMC.km_cua("lt_city_tax") == "KM_KS"
    assert KMC.km_cua("qt_non") == "KM_QUA"
    assert KMC.km_cua("pk_phi_chuyen_khoan") == "KM_PHI"


def test_r3a_9_bo_phan_di_duoc_qua_but_toan(db):
    """Cột mới phải THẬT SỰ được ghi và đọc lại, không chỉ tồn tại trong lược đồ."""
    from app.models.accounting import JournalLine, JournalEntry
    from datetime import date
    e = JournalEntry(code="TN-R3A", entry_date=date(2026, 10, 16), ngay_chung_tu=date(2026, 10, 16),
                     period="2026-10", description="thử bộ phận", status="da_ghi_so",
                     source_type="khau_hao")
    db.add(e)
    db.flush()
    db.add(JournalLine(entry_id=e.id, account_code="6424", debit=1000.0, credit=0.0,
                       item_code="KM_PHI", bo_phan="HCNS"))
    db.commit()
    l = db.query(JournalLine).filter(JournalLine.entry_id == e.id).one()
    assert l.bo_phan == "HCNS"
    assert l.item_code == "KM_PHI"
