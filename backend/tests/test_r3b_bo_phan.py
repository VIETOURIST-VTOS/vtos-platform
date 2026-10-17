# -*- coding: utf-8 -*-
"""ĐỢT R3b 17/10/2026 — DANH MỤC BỘ PHẬN, VÀ TRẢ NỢ MÀN HÌNH CỦA ĐỢT R2.

Mỗi phép thử dưới đây canh MỘT câu có thể sai thành tiền hoặc thành mất dấu vết, không canh cú
pháp. Thứ tự đọc: bảng có thật → khuôn nạp đúng → mã bất biến → GÁN KHÔNG SỬA SỔ → máy không đoán
→ có cửa và có màn hình.
"""
import os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest                                              # noqa: E402
from sqlalchemy import create_engine, select, func         # noqa: E402
from sqlalchemy.orm import sessionmaker                    # noqa: E402

from app.db.session import Base                            # noqa: E402
import app.models.bo_phan as MBP                           # noqa: E402
from app.models.accounting import JournalEntry, JournalLine  # noqa: E402
from app.services import bo_phan as BP                     # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


_dem = [0]


def _dong(db, bo_phan: str, n: int = 1):
    """Ghi n dòng sổ mang đúng chữ `bo_phan` — để ĐẾM, không phải số liệu thật.

    `account_code` không gieo tài khoản thật: phép thử này chỉ cần dòng sổ có chữ bộ phận, và
    dựng cả bảng tài khoản chỉ để đếm là buộc phép thử phụ thuộc vào một danh mục khác.
    """
    _dem[0] += 1
    e = JournalEntry(code=f"CT{_dem[0]:05d}", entry_date=date(2026, 10, 1), period="2026-10",
                     description="thử")
    db.add(e)
    db.flush()
    for _ in range(n):
        db.add(JournalLine(entry_id=e.id, account_code="642", debit=1000, credit=0,
                           bo_phan=bo_phan))
    db.commit()


# ── 1. bảng có thật ─────────────────────────────────────────────────────────────────────────────
def test_r3b_1_bang_bo_phan_va_cot_but_danh_co_that():
    assert MBP.BoPhan.__tablename__ == "bo_phan"
    cot = {c.name for c in MBP.BoPhan.__table__.columns}
    assert {"ma", "ten", "dung", "but_danh", "thu_tu"} <= cot, f"thiếu cột: {cot}"
    assert MBP.BoPhan.__table__.c.ma.unique, "mã bộ phận phải là duy nhất"


# ── 2. khuôn nạp đúng, chạy lại không đè ────────────────────────────────────────────────────────
def test_r3b_2_nap_khuon_chay_lai_khong_de_len_ban_da_sua():
    db = _db()
    assert BP.nap_mac_dinh(db) == len(BP.MAC_DINH)
    ds = BP.danh_sach(db)
    assert len(ds) == len(BP.MAC_DINH)
    bp = next(x for x in ds if x["ma"] == "BP_CNTT")
    BP.sua(db, bp["id"], {"ten": "CNTT & Chuyển đổi số"})
    assert BP.nap_mac_dinh(db) == 0, "nạp lại không được thêm dòng nào"
    lai = next(x for x in BP.danh_sach(db) if x["ma"] == "BP_CNTT")
    assert lai["ten"] == "CNTT & Chuyển đổi số", "nạp lại ĐÃ ĐÈ lên tên HCNS sửa"


# ── 3. mã bất biến ──────────────────────────────────────────────────────────────────────────────
def test_r3b_3_ma_khong_doi_duoc_chi_ngung_dung():
    db = _db()
    BP.nap_mac_dinh(db)
    b = next(x for x in BP.danh_sach(db) if x["ma"] == "BP_XE")
    with pytest.raises(ValueError):
        BP.sua(db, b["id"], {"ma": "BP_VANTAI"})
    BP.sua(db, b["id"], {"dung": False})
    assert "BP_XE" not in {x["ma"] for x in BP.danh_sach(db)}
    assert "BP_XE" in {x["ma"] for x in BP.danh_sach(db, ca_ngung=True)}, \
        "ngừng dùng là ẩn khỏi danh sách chọn, KHÔNG phải xoá dòng"


# ── 4. LUẬT LỚN NHẤT: gán không sửa một dòng sổ nào ─────────────────────────────────────────────
def test_r3b_4_gan_but_danh_khong_sua_mot_dong_so_nao():
    """Chữ cũ vào bút danh; sổ giữ nguyên chữ nó đã ghi.

    Đỏ ở đây nghĩa là ai đó đã cho bản vá chạy `UPDATE journal_lines`. Kỳ đã khoá thì không ai được
    sửa — một bản vá viết đè lên sổ đã khoá là thứ kiểm toán không dựng lại được.
    """
    db = _db()
    BP.nap_mac_dinh(db)
    _dong(db, "cntt", 5)
    truoc = db.execute(select(JournalLine.bo_phan, func.count(JournalLine.id))
                       .group_by(JournalLine.bo_phan)).all()
    BP.gan(db, "cntt", "BP_CNTT")
    sau = db.execute(select(JournalLine.bo_phan, func.count(JournalLine.id))
                     .group_by(JournalLine.bo_phan)).all()
    assert truoc == sau, f"GÁN ĐÃ SỬA SỔ: {truoc} -> {sau}"
    bd = next(x for x in BP.danh_sach(db) if x["ma"] == "BP_CNTT")["but_danh"]
    assert "cntt" in bd, "chữ cũ phải nằm trong bút danh"


def test_r3b_5_go_but_danh_duoc_va_cung_khong_sua_so():
    db = _db()
    BP.nap_mac_dinh(db)
    _dong(db, "IT", 3)
    BP.gan(db, "IT", "BP_CNTT")
    BP.bo_but_danh(db, "BP_CNTT", "IT")
    assert "IT" not in next(x for x in BP.danh_sach(db) if x["ma"] == "BP_CNTT")["but_danh"]
    assert db.execute(select(func.count(JournalLine.id))
                      .where(JournalLine.bo_phan == "IT")).scalar() == 3, "gỡ bút danh đụng vào sổ"


def test_r3b_6_mot_chu_khong_thuoc_hai_bo_phan():
    db = _db()
    BP.nap_mac_dinh(db)
    BP.gan(db, "cntt", "BP_CNTT")
    with pytest.raises(ValueError):
        BP.gan(db, "cntt", "BP_KT")


# ── 7. máy không đoán, và để trống đếm riêng ────────────────────────────────────────────────────
def test_r3b_7_de_trong_dem_rieng_khong_lan_voi_chu_la():
    db = _db()
    BP.nap_mac_dinh(db)
    _dong(db, "", 7)
    _dong(db, "doi_xe", 4)
    ra = BP.chua_gan(db)
    assert ra["de_trong"] == 7, "dòng để trống phải đếm riêng"
    assert [x["chu"] for x in ra["chua_gan"]] == ["doi_xe"]
    assert all(x["chu"].strip() for x in ra["chua_gan"]), "chữ rỗng lọt vào danh sách chữ lạ"


def test_r3b_8_da_nhan_roi_thi_khong_con_trong_danh_sach_chua_gan():
    db = _db()
    BP.nap_mac_dinh(db)
    _dong(db, "doi_xe", 4)
    _dong(db, "BP_KT", 2)
    assert [x["chu"] for x in BP.chua_gan(db)["chua_gan"]] == ["doi_xe"], \
        "chữ trùng chính mã bộ phận không phải chữ lạ"
    BP.gan(db, "doi_xe", "BP_XE")
    assert BP.chua_gan(db)["chua_gan"] == [], "nhận rồi mà vẫn còn trong danh sách chưa gán"


# ── 9. có cửa, có màn hình ──────────────────────────────────────────────────────────────────────
def test_r3b_9_bang_moi_da_khai_cua_tay():
    s = open(os.path.join(GOC, "backend", "app", "services", "ks_cua_nhap.py"),
             encoding="utf-8").read()
    assert '"bo_phan"' in s, "bảng mới chưa khai vào CUA_TAY — mỗi con số phải có một cửa"


def test_r3b_10_hcns_vao_duoc_man_hach_toan():
    """Cho HCNS quyền ghi mà không cho vào màn là dựng một cửa không ai với tới."""
    s = open(os.path.join(GOC, "backend", "app", "services", "access.py"), encoding="utf-8").read()
    m = re.search(r'"/hach-toan":\s*BASE_VIEW\s*\+\s*\(([^)]*)\)', s)
    assert m and "hcns" in m.group(1), "màn /hach-toan chưa mở cho hcns"
    a = open(os.path.join(GOC, "backend", "app", "api", "v1", "hach_toan.py"), encoding="utf-8").read()
    assert re.search(r'^XEM = \([^)]*"hcns"', a, re.M), "cửa đọc /hach-toan chưa có hcns"
    assert 'GHI_BO_PHAN = ("hcns",)' in a, "vai ghi bộ phận phải là HCNS, không phải Kế toán"


def test_r3b_11_man_hinh_co_cho_sua_ca_hai_danh_muc():
    """Trả nợ Đợt R2: danh mục khoản mục có cửa máy chủ từ 15/10 mà chưa bao giờ có màn hình."""
    p = os.path.join(GOC, "web", "app", "hach-toan", "page.tsx")
    s = open(p, encoding="utf-8").read()
    # Canh ĐÚNG LỜI GỌI ĐỌC DANH SÁCH, không canh chuỗi "/hach-toan/khoan-muc" chung chung.
    # Lượt thử phá 17/10 cho thấy vì sao: gỡ hẳn lời gọi đọc danh mục khoản mục khỏi màn hình mà
    # phép thử vẫn XANH, vì chuỗi ấy còn sót trong đường dẫn của nút "nạp khuôn" và nút sửa. Một
    # luật khớp được bằng mảnh vụn của luật khác là một luật không canh gì cả.
    for goi, vi_sao in [
        ("/hach-toan/khoan-muc?ca_ngung=true", "chưa đọc danh mục khoản mục — nợ Đợt R2 còn nguyên"),
        ("/hach-toan/bo-phan?ca_ngung=true", "chưa đọc danh mục bộ phận"),
        ("/hach-toan/bo-phan/chua-gan", "chưa đọc danh sách chữ cũ chưa ai nhận"),
        ("/hach-toan/bo-phan/gan", "chưa có chỗ nhận chữ cũ về bút danh"),
    ]:
        assert goi in s, f"màn hình {vi_sao} ({goi})"
    assert "danh_muc" in s, "chưa có thẻ danh mục trong TABS"
