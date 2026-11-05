# -*- coding: utf-8 -*-
"""Đợt QUY-3 05/11/2026 — SỐ DƯ QUỸ TIỀN MẶT.

Chuỗi QUY đã mở ba cửa ghi (máy chủ, tải lô, màn hình) nhưng thủ quỹ vẫn **không thấy quỹ còn bao
nhiêu** — mà đó là con số họ cần nhất lúc cầm tờ phiếu chi trên tay.

CẢ ĐỢT NÀY XOAY QUANH MỘT CÂU: KHÔNG DỰNG SỔ THỨ HAI.

Một con số tồn quỹ cộng bằng cách duyệt bảng `phieu_quy`, hay cộng tại chỗ trên màn hình từ danh
sách phiếu đang bày, là một sổ thứ hai. Nó chỉ đúng với những phiếu nó nhìn thấy — một trang, một
khoảng ngày, và không có bút toán nào do cửa khác sinh ra (phiếu thu của khách, sao kê, kết
chuyển). Rồi nó lệch với sổ cái, lặng lẽ, vì không gì bắt hai bên phải bằng nhau.

Nên số dư tính bằng ĐÚNG cái máy của sổ cái — `books._subtree` / `_opening` / `_totals`, cùng bộ
hàm `cash_book` dùng. **Luật 1 đo đúng điều đó bằng cách lập phiếu thật rồi so hai con số.**
**Luật 4 canh phía màn hình**: nó phải ĐỌC số dư từ cửa, không được tự cộng.
"""
import os
import re
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_quy3.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_quy3.db", "test_quy3.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "collections", "page.tsx")


def _db():
    from app.db.session import SessionLocal, engine, Base
    import app.models  # noqa
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def _nguoi(db, role="thu_quy"):
    from app.models.core import User
    u = db.query(User).filter(User.role == role).first()
    if u is None:
        u = User(username=f"pq3_{role}", role=role)
        for ten, gt in (("full_name", f"Phép thử {role}"), ("hashed_password", "x"),
                        ("password_hash", "x"), ("is_active", True), ("active", True)):
            if hasattr(type(u), ten):
                setattr(u, ten, gt)
        db.add(u)
        db.flush()
    return u


def _san_sang(db):
    from app.services import hach_toan as HT
    from app.services.accounting import seed_accounts
    seed_accounts(db)
    HT.nap_mac_dinh(db)


def _man() -> str:
    assert os.path.exists(MAN), "khong thay web/app/collections/page.tsx"
    return open(MAN, encoding="utf-8").read()


def _khong_ghi_chu(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return "\n".join(d for d in s.split("\n") if not d.strip().startswith("//"))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_quy3_1_so_du_bang_DUNG_con_so_cua_SO_CAI():
    """LUẬT ĐẮT NHẤT CỦA ĐỢT — và nó đo bằng cách GHI THẬT rồi so hai con số.

    Lập ba phiếu quỹ qua đúng cửa người dùng đi, rồi so `so_du_tien(...)` với
    `cash_book(...)["closing"]`. Hai bên lệch nghĩa là hệ thống đang có hai câu trả lời cho câu
    hỏi «quỹ còn bao nhiêu» — và lúc ấy không ai biết câu nào đúng.
    """
    from app.services import books as B
    from app.services import phieu_quy as PQ
    db = _db()
    try:
        _san_sang(db)
        u = _nguoi(db)
        db.commit()
        hom_nay = date.today()
        dau_thang = hom_nay.replace(day=1)
        PQ.lap(db, u, chieu="thu", ngay=hom_nay, so_tien=5_000_000, ly_do="",
               noi_dung="khách nộp tiền mặt", ten_doi_tuong="Khách lẻ", ma_doi_tuong="KH-PT-1")
        PQ.lap(db, u, chieu="chi", ngay=hom_nay, so_tien=2_000_000, ly_do="tra_ncc",
               noi_dung="trả NCC", ten_doi_tuong="NCC Phép Thử", ma_doi_tuong="NCC-PT-1")
        PQ.lap(db, u, chieu="chi", ngay=hom_nay, so_tien=500_000, ly_do="tra_ncc",
               noi_dung="trả NCC lần hai", ten_doi_tuong="NCC Phép Thử", ma_doi_tuong="NCC-PT-1")

        sd = B.so_du_tien(db, hom_nay)
        so = B.cash_book(db, dau_thang, hom_nay)
        assert sd["so_du"] == so["closing"], (
            f"số dư quỹ {sd['so_du']} ≠ tồn cuối kỳ của sổ quỹ {so['closing']} — hệ thống đang có "
            "HAI câu trả lời cho câu hỏi «quỹ còn bao nhiêu»")
        assert sd["thu"] == so["total"]["in"] and sd["chi"] == so["total"]["out"], (
            f"phát sinh lệch: số dư nói thu {sd['thu']} / chi {sd['chi']}, sổ quỹ nói "
            f"{so['total']['in']} / {so['total']['out']}")
        assert sd["dau_ky"] == so["opening"], "tồn đầu kỳ lệch"
        assert sd["so_du"] == sd["dau_ky"] + sd["thu"] - sd["chi"], "bốn con số không khớp nhau"
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_quy3_2_so_du_tinh_DEN_MOT_NGAY_chu_khong_phai_tat_ca():
    """Tồn quỹ hôm nay không được cộng một phiếu ghi ngày mai.

    Nghe hiển nhiên, nhưng một hàm cộng «tất cả phiếu trong bảng» sẽ sai đúng chỗ này, và sai
    một cách khó thấy: nó chỉ lệch vào những ngày có người lập phiếu lùi hoặc tới.
    """
    from app.services import books as B
    from app.services import phieu_quy as PQ
    db = _db()
    try:
        _san_sang(db)
        u = _nguoi(db)
        db.commit()
        hom_nay = date.today()
        hom_qua = hom_nay - timedelta(days=1)
        PQ.lap(db, u, chieu="thu", ngay=hom_qua, so_tien=1_000_000, ly_do="",
               noi_dung="thu hôm qua", ten_doi_tuong="Khách lẻ", ma_doi_tuong="KH-PT-2")
        # ĐO BẰNG CHÊNH LỆCH, không bằng một con số tuyệt đối. Các luật trong tệp này dùng CHUNG
        # một cơ sở dữ liệu, nên sổ đã có sẵn những phiếu của luật trước — một phép so tuyệt đối
        # sẽ đỏ vì lý do chẳng liên quan gì đến thứ luật này đang canh. Đo được lúc chạy thật
        # 05/11/2026, và cái đỏ ấy là lỗi của phép đo chứ không phải của mã.
        qua_truoc = B.so_du_tien(db, hom_qua)["so_du"]
        nay_truoc = B.so_du_tien(db, hom_nay)["so_du"]
        PQ.lap(db, u, chieu="thu", ngay=hom_nay, so_tien=7_000_000, ly_do="",
               noi_dung="thu hôm nay", ten_doi_tuong="Khách lẻ", ma_doi_tuong="KH-PT-2")
        qua_sau = B.so_du_tien(db, hom_qua)["so_du"]
        assert qua_truoc == qua_sau, (
            f"một phiếu ghi ngày {hom_nay} đã làm đổi tồn quỹ tính đến {hom_qua} "
            f"({qua_truoc} → {qua_sau}) — hàm đang cộng cả những thứ chưa xảy ra tới ngày ấy")
        assert B.so_du_tien(db, hom_nay)["so_du"] == nay_truoc + 7_000_000, (
            "tồn quỹ hôm nay không tăng đúng bằng số tiền vừa thu")
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_quy3_3_cua_doc_gac_dung_hai_vai_va_KHONG_mo_nhom_moi():
    """Cửa nằm dưới nhóm `/api/v1/receipts` đã khai — mở nhóm mới làm lệch hai bảng CÓ CHỮ KÝ
    (`PHAM_VI_DA_CHOT` mười sáu dòng vai, và hai con số ghim trong `test_lg9`) trong khi KHÔNG
    vai nào bấm được thêm một cửa nào."""
    import inspect

    from app.api.v1 import payments as API
    from app.main import app
    assert "/api/v1/receipts/quy/so-du" in {getattr(r, "path", "") for r in app.routes}, (
        "cửa `/receipts/quy/so-du` không có trên máy chủ")
    src = inspect.getsource(API)
    assert '@router.get("/receipts/quy/so-du")' in src, "cửa không nằm trong nhóm /receipts đã khai"
    assert '"/api/v1/quy"' not in open(
        os.path.join(GOC, "backend", "app", "services", "access.py"), encoding="utf-8").read(), (
        "đợt này mở một nhóm cửa mới — làm lệch bảng phạm vi đã ký")
    i = src.find("def so_du_quy(")
    assert i > 0, "khong tim thay ham so_du_quy"
    than = src[i:i + 600]
    assert 'require_roles("ketoan", "thu_quy"' in than, (
        "cửa số dư không gác đúng hai vai của cửa lập phiếu")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_quy3_4_man_hinh_DOC_so_du_chu_KHONG_tu_cong():
    """Màn hình cộng lấy con số tồn quỹ là dựng một sổ thứ hai ngay trên trình duyệt.

    Nó chỉ đúng với những phiếu màn hình đang giữ — một trang, một khoảng ngày — và mù hẳn với
    mọi bút toán tiền mặt do cửa khác sinh ra: phiếu thu của khách, sao kê, kết chuyển. Rồi nó
    lệch với sổ cái mà không gì kêu lên.
    """
    man = _khong_ghi_chu(_man())
    assert "/receipts/quy/so-du" in man, "màn hình không đọc số dư từ cửa máy chủ"
    assert "soDu" in man, "màn hình chưa có ô tồn quỹ"
    xau = re.findall(r"quy\s*\.\s*reduce\s*\(", man)
    assert not xau, (
        "màn hình đang TỰ CỘNG danh sách phiếu để ra tồn quỹ — đó là một sổ thứ hai; "
        "số dư phải đọc từ cửa `/receipts/quy/so-du`")
    assert "loadSoDu()" in man, "lập phiếu xong mà không đọc lại số dư — con số trên màn sẽ cũ"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 5
def test_quy3_5_so_du_dung_dung_may_cua_so_cai_chu_khong_duyet_bang_phieu():
    """Đo ở tầng mã: hàm số dư phải nằm trong `books.py` và dùng bộ hàm của sổ cái.

    Luật 1 đã đo bằng cách chạy thật — luật này nói thêm vì sao nó đúng, và chặn một bản viết lại
    sau này lặng lẽ đổi sang duyệt bảng `phieu_quy` (lúc ấy luật 1 vẫn có thể xanh nếu mọi bút
    toán tiền mặt tình cờ đều do phiếu quỹ sinh ra — và đó chính là lúc nó nguy hiểm nhất).
    """
    import inspect

    from app.services import books as B
    assert hasattr(B, "so_du_tien"), "books.py chưa có hàm `so_du_tien`"
    src = inspect.getsource(B.so_du_tien)
    for can in ("_subtree(", "_opening(", "_totals("):
        assert can in src, f"`so_du_tien` không dùng `{can}` của sổ cái"
    assert "PhieuQuy" not in src, (
        "`so_du_tien` đang duyệt bảng `phieu_quy` — đó là sổ thứ hai. Tồn quỹ phải cộng từ SỔ CÁI, "
        "vì tiền mặt còn vào sổ bằng những cửa khác nữa")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 6
def test_quy3_6_so_du_KHONG_go_cung_mot_tai_khoan_nao_ngoai_hang_so_san_co():
    """`CASH_ACCOUNT` đã có sẵn trong `books.py` từ trước; đợt này không gõ thêm một mã tài khoản
    nào ở cửa máy chủ hay trên màn hình."""
    import inspect

    from app.api.v1 import payments as API
    from app.services import books as B
    src = inspect.getsource(B.so_du_tien)
    assert "CASH_ACCOUNT" in src, "`so_du_tien` không dùng hằng số CASH_ACCOUNT sẵn có"
    assert not re.search(r'"1(?:11|12)\d?"', src), "`so_du_tien` gõ cứng một mã tài khoản"
    i = inspect.getsource(API).find("def so_du_quy(")
    than = inspect.getsource(API)[i:i + 900]
    assert not re.search(r'"1(?:11|12)\d?"', than), "cửa số dư gõ cứng một mã tài khoản"
    assert not re.search(r'"1(?:11|12)\d?"|\b1111\b|\b1121\b', _khong_ghi_chu(_man())), (
        "màn hình gõ cứng một mã tài khoản tiền")
