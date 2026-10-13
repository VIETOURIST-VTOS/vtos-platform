# -*- coding: utf-8 -*-
"""Đợt E3 — ngày chứng từ, loại chứng từ, loại nghiệp vụ, và khoá chống ghi sổ hai lần.

Năm điều tệp này canh:

  A. MỌI chỗ gọi `post_entry` đều KHAI nghiệp vụ. Đây là hàng rào quan trọng nhất của đợt: khoá
     sự kiện ghép từ ba vế, thiếu vế thứ ba ở một chỗ gọi là hàng rào tắt âm thầm đúng chỗ ấy —
     và một hàng rào tắt âm thầm nguy hiểm hơn không có hàng rào nào. Bài học Đợt LG3.
  B. Ba bảng phân loại khớp nhau, và khớp với những giá trị mã THẬT đang dùng.
  C. Ba nguồn NHIỀU-CHỨNG-TỪ ra ba khoá KHÁC nhau. Đây chính là chỗ bản thiết kế hai vế chết, nên
     nó phải có phép thử riêng chứ không nằm trong một lời chú thích.
  D. Hai chỗ miễn khoá được KHAI RA kèm lý do, và chỉ có hai.
  E. Ghi lại đúng một sự kiện thì bị chặn, kèm mã chứng từ đã ghi.
"""
import ast
import io
import os
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e3.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    if os.path.exists(_DB):
        os.remove(_DB)
except OSError:
    pass

from datetime import date, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import chung_tu_loai as CTL  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_APP = os.path.join(GOC, "app")


def _tep_py():
    for g, _d, ts in os.walk(GOC_APP):
        for t in sorted(ts):
            if t.endswith(".py"):
                p = os.path.join(g, t)
                yield os.path.relpath(p, GOC_APP).replace(os.sep, "/"), io.open(p, encoding="utf-8").read()


def _cho_goi():
    """Mọi lời gọi post_entry trong app/, kèm nghiệp vụ đã khai (None nếu không khai)."""
    ra = []
    for rel, src in _tep_py():
        for n in ast.walk(ast.parse(src)):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            ten = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if ten != "post_entry":
                continue
            nv = None
            for k in n.keywords:
                if k.arg == "nghiep_vu":
                    nv = k.value.value if isinstance(k.value, ast.Constant) else "<biến>"
            st = None
            if len(n.args) >= 7 and isinstance(n.args[6], ast.Constant):
                st = n.args[6].value
            for k in n.keywords:
                if k.arg == "source_type" and isinstance(k.value, ast.Constant):
                    st = k.value.value
            ra.append((rel, n.lineno, st, nv))
    return ra


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. MỌI CHỖ GỌI ĐỀU KHAI NGHIỆP VỤ
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e3_1_moi_cho_goi_post_entry_deu_khai_nghiep_vu():
    thieu = [(f, d) for f, d, _st, nv in _cho_goi() if nv is None]
    assert not thieu, (
        "Những chỗ gọi `post_entry` sau KHÔNG khai `nghiep_vu=`:\n  "
        + "\n  ".join(f"app/{f}:{d}" for f, d in thieu)
        + "\nKhoá chống ghi sổ hai lần ghép từ nguồn, mã nguồn và nghiệp vụ. Thiếu vế thứ ba thì "
          "hai bút toán khác việc của cùng một nguồn sẽ va nhau, hoặc tệ hơn, cùng rơi vào mặc "
          "định `but_toan_tay` và khoá mất ý nghĩa.")


def test_e3_2_co_du_32_cho_goi_khong_sot_tep_nao():
    """Đếm để lần sau ai thêm một chỗ gọi thì con số này nói ra. Đo 12/10/2026: 32."""
    assert len(_cho_goi()) >= 32


# ĐỢT E6 13/10/2026 — MỘT CHỖ GỌI KHAI NGHIỆP VỤ QUA BẢNG, KHÔNG VIẾT THẲNG MỘT HÀNG CHỮ.
#
# Bộ quét dưới đây đọc CÂY CÚ PHÁP và chỉ hiểu một hằng chữ; gặp một biểu thức nó ghi "<biến>".
# Đợt DỌN-2 (13/10/2026) đổi `vay_but_toan.ghi_so` sang `NGHIEP_VU_THEO_KY.get(s.kind, ...)` vì
# đáo hạn là HAI chân cùng một khế ước và hai chân phải mang hai tên nghiệp vụ khác nhau — không
# viết thẳng được một hằng chữ ở đó. Kết quả: `test_e3_3` đỏ trên main từ lúc gộp DỌN-2, với đúng
# một dòng "<biến>", trong khi cả ba tên DỌN-2 dùng đều đã khai đúng.
#
# KHÔNG BỎ "<biến>" KHỎI PHÉP THỬ — làm thế là tắt hàng rào đúng chỗ nó còn việc: từ đó ai truyền
# một biến bừa vào `nghiep_vu=` cũng lọt. Đổi lại: chỗ gọi qua một BẢNG KHAI SẴN thì phải KHAI RA
# ở đây, và phép thử đi kiểm GIÁ TRỊ của bảng ấy. Thêm một chỗ gọi truyền biến mà không khai vẫn
# đỏ; thêm một tên chưa khai vào bảng ấy cũng đỏ.
GOI_QUA_BANG = {
    "services/vay_but_toan.py": ("NGHIEP_VU_THEO_KY",
                                 "Đáo hạn là HAI chân cùng một khế ước, hai chân hai tên nghiệp "
                                 "vụ — Đợt DỌN-2 13/10/2026"),
    "api/v1/accounting.py": ("NGHIEP_VU_LAP_TAY",
                             "Cửa lập tay nhận HAI loại bút toán — bút toán thường và bút toán sửa "
                             "sai sót kỳ trước — nên Kế toán phải CHỌN, và cái chọn ấy thành một "
                             "biến. Danh sách hợp lệ hẹp đúng hai giá trị ảy, khóa là thứ màn hình gửi "
                             "lên — Đợt E14 13/10/2026"),
}


def test_e3_3_nghiep_vu_khai_o_cho_goi_deu_co_trong_bang():
    la = sorted({f"app/{f}:{d} → {nv}" for f, d, _st, nv in _cho_goi()
                 if nv and nv != "<biến>" and nv not in CTL.NGHIEP_VU})
    assert not la, f"Nghiệp vụ chưa khai trong `chung_tu_loai.NGHIEP_VU`: {la}"


def test_e3_3b_cho_goi_truyen_bien_phai_khai_la_goi_qua_bang():
    """Một chỗ gọi truyền biến vào `nghiep_vu=` mà KHÔNG khai ở `GOI_QUA_BANG` thì đỏ.

    Đây là vế giữ cho sửa của Đợt E6 không thành một lỗ: bỏ "<biến>" khỏi phép thử trên mà không
    có phép thử này là tắt hàng rào, chứ không phải nới nó đúng chỗ.
    """
    la = sorted({f for f, _d, _st, nv in _cho_goi() if nv == "<biến>" and f not in GOI_QUA_BANG})
    assert not la, (
        f"Những chỗ gọi `post_entry` sau truyền BIẾN vào `nghiep_vu=` mà chưa khai: {la}. "
        "Khai vào `GOI_QUA_BANG` KÈM LÝ DO và tên bảng, rồi phép thử dưới sẽ kiểm giá trị của "
        "bảng ấy — hoặc viết thẳng một hằng chữ nếu chỗ ấy chỉ có một tên.")


def test_e3_3c_moi_gia_tri_trong_bang_duoc_khai_deu_co_trong_NGHIEP_VU():
    """Khai "gọi qua bảng" không miễn kiểm — nó chuyển phép kiểm từ chỗ gọi sang bảng."""
    import importlib
    xau = []
    for rel, (ten_bang, _ly_do) in GOI_QUA_BANG.items():
        m = importlib.import_module("app." + rel[:-3].replace("/", "."))
        bang = getattr(m, ten_bang, None)
        assert isinstance(bang, dict), f"app/{rel} không có bảng `{ten_bang}` kiểu dict"
        assert bang, f"app/{rel}::{ten_bang} RỖNG — một bảng rỗng không khai gì cả"
        xau += [f"{rel}::{ten_bang}[{k!r}] = {v!r}" for k, v in bang.items()
                if v not in CTL.NGHIEP_VU]
    assert not xau, f"Nghiệp vụ chưa khai trong `chung_tu_loai.NGHIEP_VU`: {sorted(xau)}"


def test_e3_4_moi_nguon_dung_trong_ma_deu_co_trong_bang_NGUON():
    """Chú thích cũ trên cột `source_type` khai NĂM giá trị; mã thật dùng 17. Bảng NGUON thay nó,
    và phép thử này là thứ giữ cho nó không lệch lần nữa."""
    la = sorted({st for _f, _d, st, _nv in _cho_goi() if st and st not in CTL.NGUON})
    assert not la, f"Nguồn chưa khai trong `chung_tu_loai.NGUON`: {la}"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. BA BẢNG KHỚP NHAU
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e3_5_moi_nghiep_vu_tro_ve_mot_loai_chung_tu_co_that():
    xau = {k: v[1] for k, v in CTL.NGHIEP_VU.items() if v[1] not in CTL.LOAI_CHUNG_TU}
    assert not xau, f"Nghiệp vụ trỏ tới loại chứng từ không có: {xau}"


def test_e3_6_nghiep_vu_go_sai_thi_NEM_LOI_chu_khong_tra_rong():
    """Trả rỗng thì một mã gõ sai thành một chứng từ không khoá được, mà nó trông y hệt một
    chứng từ được miễn khoá có lý do. Hai thứ ấy phải phân biệt được."""
    with pytest.raises(CTL.SaiLoai):
        CTL.nghiep_vu_hop_le("nghiep_vu_khong_co_that")
    with pytest.raises(CTL.SaiLoai):
        CTL.khoa("thu_tien", "receipt:PT1", "go_nham")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. BA NGUỒN NHIỀU-CHỨNG-TỪ RA BA KHOÁ KHÁC NHAU
# ═════════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("nguon,ma,bo_nghiep_vu", [
    ("luong", "payroll:2026-09:VTD",
     ["luong_hdld", "thu_lao_ctv", "khau_tru_tncn", "bhxh_nld", "doan_phi"]),
    ("ket_chuyen", "period:2026-09",
     ["ket_chuyen_doanh_thu", "ket_chuyen_chi_phi", "ket_chuyen_lai_lo"]),
    ("quyet_toan", "tour:HT001",
     ["quyet_toan_hoan_ung", "quyet_toan_trich_truoc", "quyet_toan_gia_von"]),
])
def test_e3_7_nguon_nhieu_chung_tu_khong_va_nhau(nguon, ma, bo_nghiep_vu):
    """ĐÂY LÀ CHỖ BẢN THIẾT KẾ HAI VẾ CHẾT. Khoá chỉ gồm nguồn và mã nguồn thì năm bút toán lương
    của một kỳ va nhau, và bảng lương tháng 9 chết ở bút toán thứ hai."""
    khoa = [CTL.khoa(nguon, ma, nv) for nv in bo_nghiep_vu]
    assert len(set(khoa)) == len(bo_nghiep_vu), f"Hai bút toán khác việc ra cùng một khoá: {khoa}"
    assert all(k is not None for k in khoa)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. HAI CHỖ MIỄN KHOÁ, KHAI RA KÈM LÝ DO
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e3_8_dung_hai_cho_mien_khoa_va_moi_cho_co_ly_do():
    assert len(CTL.KHONG_KHOA_SU_KIEN) == 2, (
        "Thêm một chỗ miễn khoá là thu hẹp hàng rào chống ghi sổ hai lần. Phải có người biết, "
        "nên con số này cố ý ghim ở đây.")
    for mau, ly_do in CTL.KHONG_KHOA_SU_KIEN.items():
        assert len(ly_do) > 60, f"Chỗ miễn khoá `{mau}` cần một lý do viết ra, không phải một chữ."


def test_e3_9_hai_cho_mien_khoa_tra_None_con_lai_tra_khoa():
    assert CTL.khoa("thu_cong", "", "but_toan_tay") is None
    assert CTL.khoa("quy_tac", "quy_tac:TOUR_DOANH_THU", "theo_quy_tac") is None
    assert CTL.khoa("quy_tac", "HD-2026-00123", "theo_quy_tac") == "quy_tac|HD-2026-00123|theo_quy_tac"
    assert CTL.khoa("thu_tien", "receipt:PT1", "thu_tien_khach") == "thu_tien|receipt:PT1|thu_tien_khach"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# E. BỐN CỘT CÓ THẬT, VÀ BẢN DI TRÚ KHAI ĐÚNG BỐN CỘT ẤY
# ═════════════════════════════════════════════════════════════════════════════════════════════
BON_COT = ("ngay_chung_tu", "loai_chung_tu", "loai_nghiep_vu", "khoa_su_kien")


def test_e3_10_mo_hinh_co_du_bon_cot_va_khoa_su_kien_la_duy_nhat():
    from app.models.accounting import JournalEntry
    cols = JournalEntry.__table__.columns
    for c in BON_COT:
        assert c in cols, f"Mô hình thiếu cột {c}"
    assert cols["khoa_su_kien"].nullable is True, (
        "`khoa_su_kien` PHẢI nhận NULL: NULL không va nhau trong chỉ mục duy nhất, còn chuỗi rỗng "
        "thì va — và mọi chứng từ lập tay đều không có khoá.")
    assert cols["ngay_chung_tu"].nullable is False


def test_e3_11_ban_di_tru_khai_dung_bon_cot_va_dung_chi_muc_duy_nhat():
    d = os.path.join(GOC, "alembic", "versions")
    tep = [t for t in os.listdir(d) if t.startswith("e3c4d5e6f7a8")]
    assert len(tep) == 1, f"Không thấy bản di trú E3 trong {d}"
    s = io.open(os.path.join(d, tep[0]), encoding="utf-8").read()
    for c in BON_COT:
        assert f'"{c}"' in s, f"Bản di trú không thêm cột {c}"
    assert "uq_journal_entries_khoa_su_kien" in s
    assert "unique=True" in s
    assert "ngay_chung_tu = entry_date" in s, "Bản di trú phải chép ngày chứng từ cho sổ cũ."


# ═════════════════════════════════════════════════════════════════════════════════════════════
# F. CHẠY THẬT TRÊN CƠ SỞ DỮ LIỆU
# ═════════════════════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def _dong(tien=1_000_000):
    # 131 là tài khoản công nợ nên bắt buộc có mã đối tượng – `account_rule_check` của Đợt E1.
    return [{"account": "111", "debit": tien},
            {"account": "131", "credit": tien, "partner": "Khách lẻ E3", "partner_code": "E3-KH"}]


def test_e3_12_ngay_chung_tu_mac_dinh_bang_ngay_ghi_so_va_doi_duoc(db):
    from app.services import accounting as ACC
    d = date(2026, 9, 10)
    e = ACC.post_entry(db, "ketoan", "ketoan", d, "E3 – mặc định", _dong(),
                       "thu_tien", "receipt:E3-MACDINH", nghiep_vu="thu_tien_khach")
    assert e.ngay_chung_tu == d
    assert e.loai_chung_tu == "PT" and e.loai_nghiep_vu == "thu_tien_khach"
    e2 = ACC.post_entry(db, "ketoan", "ketoan", d, "E3 – hóa đơn về muộn", _dong(),
                        "thu_tien", "receipt:E3-MUON", nghiep_vu="thu_tien_khach",
                        ngay_chung_tu=d - timedelta(days=6))
    assert e2.ngay_chung_tu == d - timedelta(days=6) and e2.entry_date == d
    db.rollback()


def test_e3_13_ghi_lai_dung_su_kien_thi_bi_chan_va_noi_ra_chung_tu_cu(db):
    from app.services import accounting as ACC
    d = date(2026, 9, 11)
    e = ACC.post_entry(db, "ketoan", "ketoan", d, "E3 – lần một", _dong(),
                       "thu_tien", "receipt:E3-TRUNG", nghiep_vu="thu_tien_khach")
    db.flush()
    with pytest.raises(ValueError) as ex:
        ACC.post_entry(db, "ketoan", "ketoan", d, "E3 – lần hai", _dong(),
                       "thu_tien", "receipt:E3-TRUNG", nghiep_vu="thu_tien_khach")
    loi = str(ex.value)
    assert e.code in loi, "Lời chặn phải NÓI RA mã chứng từ đã ghi, không chỉ nói 'trùng'."
    assert "đảo" in loi, "Lời chặn phải chỉ ra đường đi đúng: lập bút toán đảo."
    db.rollback()


def test_e3_14_nam_but_toan_luong_cua_mot_ky_deu_ghi_duoc(db):
    """Phép thử NGƯỢC của hàng rào trên: nếu ai siết khoá về hai vế thì đúng chỗ này đỏ."""
    from app.services import accounting as ACC
    d = date(2026, 9, 12)
    ma = "payroll:2026-09:E3TEST"
    for nv in ("luong_hdld", "thu_lao_ctv", "khau_tru_tncn", "bhxh_nld", "doan_phi"):
        ACC.post_entry(db, "ketoan", "ketoan", d, f"E3 – {nv}", _dong(), "luong", ma, nghiep_vu=nv)
        db.flush()
    db.rollback()


def test_e3_15_chung_tu_lap_tay_khong_co_ma_nguon_thi_lap_duoc_nhieu_to(db):
    from app.services import accounting as ACC
    d = date(2026, 9, 13)
    for i in (1, 2, 3):
        e = ACC.post_entry(db, "ketoan", "ketoan", d, f"E3 – phiếu kế toán {i}", _dong(),
                           "thu_cong", "", nghiep_vu="but_toan_tay")
        assert e.khoa_su_kien is None
        db.flush()
    db.rollback()


def test_e3_16_dung_JournalEntry_thang_ma_quen_ngay_chung_tu_thi_may_tu_dien(db):
    """Luật "rỗng thì bằng ngày ghi sổ" nằm ở móc `before_insert` của bảng, không nằm trong
    `post_entry`. Bốn tệp phép thử đang dựng `JournalEntry(...)` thẳng, và mã sau này cũng sẽ —
    luật nằm trong một hàm thì ai đi đường khác là mất luật."""
    from app.models.accounting import JournalEntry
    d = date(2026, 9, 14)
    e = JournalEntry(code="CT-E3-TRUC-TIEP", entry_date=d, period="2026-09",
                     description="E3 – dựng thẳng", source_type="thu_cong", source_ref="")
    db.add(e)
    db.flush()
    assert e.ngay_chung_tu == d
    db.rollback()
