# -*- coding: utf-8 -*-
"""Đợt QUY-2a 04/11/2026 — CỬA TẢI LÔ SỔ QUỸ TIỀN MẶT.

Chủ tịch chốt 02/11/2026: *"tiền mặt vào sổ bằng CẢ HAI CỬA: thủ quỹ nhập tay từng phiếu VÀ tải
lô sổ quỹ"*. Đợt QUY-1 làm cửa thứ nhất; đợt này làm cửa thứ hai.

ĐIỀU ĐÁNG GIỮ NHẤT CỦA ĐỢT NÀY LÀ: HAI CỬA ĐI QUA ĐÚNG MỘT ĐƯỜNG.

Cửa tải lô gọi `phieu_quy.lap()` — cùng hàm nút «Lập phiếu» gọi. Nên nó chịu đúng những hàng rào
ấy: lý do phải nằm trong từ vựng bảng quy ước, bảng quy ước chọn cặp tài khoản, không khớp thì TỪ
CHỐI. Một cửa tải lô tự dựng bút toán lấy là một đường vòng quanh bảng quy ước, và đường vòng ấy
sẽ lặng lẽ ghi khác cửa nhập tay cho tới ngày có người đối chiếu. **Luật 6 đo đúng điều đó**, và
nó đo bằng cách CHẠY cả hai cửa trên cùng một dòng dữ liệu rồi so bút toán, không bằng soi chữ.

SỐ PHIẾU GỐC LÀ KHOÁ CHỐNG TRÙNG. Sổ quỹ giấy đánh số từng phiếu; lấy số ấy làm khoá nghĩa là nạp
lại cùng một tệp KHÔNG lập phiếu thứ hai. Không có khoá thì mỗi lần bấm nhầm là quỹ phình thêm một
lần — với tiền thì đó không phải phiền toái, đó là sổ sai. **Luật 2 đo bằng cách nạp hai lần.**

ĐỢT NÀY KHÔNG ĐỤNG MỘT TỆP `web/` NÀO. Khối «Sổ quỹ» trên màn `/collections` là Đợt QUY-2b, và nó
phải được đo trên anh main thật của `web/app/collections/page.tsx` trước khi viết — không viết
một khối React theo phỏng đoán về tệp ấy.
"""
import ast
import os
import re
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_quy2.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_quy2.db", "test_quy2.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_LO = os.path.join(GOC, "app", "services", "intake_so_quy.py")

# Lý do chắc chắn KHÔNG có trong từ vựng — dùng cho luật 3. Cố ý không phải một mã nghiệp vụ thật:
# nếu một ngày nào đó nó thành thật thì luật 3 đỏ, và đỏ ở đây là đúng (phải chọn lý do khác).
KHONG_CO_QUY_TAC = "khong_bao_gio_co_quy_tac_nao_khai_ly_do_nay"


def _db():
    from app.db.session import SessionLocal, engine, Base
    import app.models  # noqa – nạp toàn bộ mô hình
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def _nguoi(db, role="thu_quy"):
    from app.models.core import User
    u = db.query(User).filter(User.role == role).first()
    if u is None:
        # Đặt từng ô một và CHỈ những ô mô hình có thật: `User(...)` của SQLAlchemy ném `TypeError`
        # cho bất kỳ khoá nào không phải cột, nên một ô đoán sai làm đỏ cả tệp vì lý do chẳng liên
        # quan gì đến thứ nó đang canh. Bài học Đợt QUY-1.
        u = User(username=f"pq2_{role}", role=role)
        for ten, gt in (("full_name", f"Phép thử {role}"), ("hashed_password", "x"),
                        ("password_hash", "x"), ("is_active", True), ("active", True)):
            if hasattr(type(u), ten):
                setattr(u, ten, gt)
        db.add(u)
        db.flush()
    return u


def _san_sang(db):
    """Bảng quy ước mặc định + danh mục tài khoản. `post_entry` đòi tài khoản có thật."""
    from app.services import hach_toan as HT
    from app.services.accounting import seed_accounts
    seed_accounts(db)
    HT.nap_mac_dinh(db)


def _cua():
    """Lấy ĐÚNG khai báo đã đăng ký trong khung nạp, không nhập trực tiếp mô-đun.

    Khác biệt này là cả một luật: nếu `intake_so_quy` có thật mà hai dòng đăng ký trong
    `intake.py` không được vá thì không cửa nào hiện ra cho người dùng, và một phép thử nhập
    thẳng mô-đun vẫn xanh. Mọi luật dưới đây đi qua `BO_NAP` để không nói sai chuyện ấy.
    """
    from app.services.intake import BO_NAP
    assert "so_quy" in BO_NAP, (
        "khung nạp chưa biết cửa `so_quy` — thiếu hai dòng đăng ký trong app/services/intake.py")
    return BO_NAP["so_quy"]


def _dong(so_goc, chieu="chi", ly_do="tra_ncc", so_tien=2_000_000, ngay=None, **thêm):
    r = {"so_goc": so_goc, "chieu": chieu, "ly_do": ly_do, "so_tien": so_tien,
         "ngay": (ngay or date.today()).strftime("%d/%m/%Y"),
         "noi_dung": "Phép thử tải lô sổ quỹ",
         "ten_doi_tuong": "Khách sạn Phép Thử", "ma_doi_tuong": "NCC-PT-001",
         "khoan_muc": ""}
    r.update(thêm)
    return r


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_quy2_1_cot_so_goc_co_that_tren_co_so_du_lieu():
    """Khoá chống trùng phải là một CỘT, không phải một quy ước trong đầu người viết.

    Đo bằng cách GHI THẬT rồi đọc lại — soi chữ `so_goc` trong tệp mô hình chỉ chứng minh có một
    dòng mã, ghi rồi đọc mới chứng minh di trú đã chạy và cột nhận giá trị.
    """
    from app.models.payments import PhieuQuy
    from app.services import phieu_quy as PQ
    db = _db()
    try:
        p = PhieuQuy(code="PTQ-TEST-SG01", chieu="thu", ngay=date(2026, 11, 4), so_tien=1000,
                     ly_do="", noi_dung="phép thử", so_goc="SO-GOC-TEST-01",
                     created_by="phep_thu")
        db.add(p)
        db.commit()
        db.refresh(p)
        assert p.so_goc == "SO-GOC-TEST-01"
        assert PQ.ra(p).get("so_goc") == "SO-GOC-TEST-01", (
            "`phieu_quy.ra()` không trả `so_goc` — màn hình và cửa đọc sổ sẽ không thấy khoá "
            "chống trùng, nên không ai đối chiếu được phiếu trên máy với tờ phiếu giấy")
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_quy2_2_tai_lo_ghi_so_that_roi_nap_lai_KHONG_lap_them():
    """ĐÂY LÀ LÝ DO ĐỢT NÀY TỒN TẠI, và nó đo bằng cách nạp HAI LẦN cùng một lô.

    Chạy đúng hai hàm khung nạp gọi — `kiem` rồi `nap` — vì vòng chạy của khung bỏ qua đúng những
    dòng mà `kiem` trả về khoá đã có. Nên giá trị thứ ba của `kiem` CHÍNH LÀ chốt chống trùng, và
    luật này đo chính nó.
    """
    from app.models.accounting import JournalLine
    from app.models.payments import PhieuQuy
    cua = _cua()
    db = _db()
    try:
        _san_sang(db)
        u = _nguoi(db)
        db.commit()
        lo = [_dong("PT-2026-9001"), _dong("PT-2026-9002", so_tien=3_500_000)]

        for r in lo:
            loi, _cb, da_co = cua["kiem"](db, r)
            assert not loi, f"dòng {r['so_goc']} báo lỗi ngoài dự tính: {loi}"
            assert da_co is None, "lô mới mà đã báo trùng"
            cua["nap"](db, r, u.username)
        db.commit()

        co = db.query(PhieuQuy).filter(PhieuQuy.so_goc.in_(
            ["PT-2026-9001", "PT-2026-9002"])).all()
        assert len(co) == 2, f"nạp hai dòng mà sổ có {len(co)} phiếu"
        for p in co:
            assert p.journal_entry_id, (
                f"{p.code} không có bút toán — một phiếu quỹ không ghi sổ là một rổ chờ thứ hai "
                "không ai canh, và số dư quỹ sẽ lệch với sổ mà không gì kêu lên")
            assert db.query(JournalLine).filter(
                JournalLine.entry_id == p.journal_entry_id).count() >= 2, (
                f"bút toán của {p.code} không có đủ hai vế")
            assert p.quy_tac, f"{p.code} không ghi lại quy tắc đã khớp"

        # NẠP LẠI CÙNG MỘT LÔ — không được lập thêm phiếu nào.
        for r in lo:
            loi, _cb, da_co = cua["kiem"](db, r)
            assert not loi, f"nạp lại báo lỗi: {loi}"
            assert da_co == r["so_goc"], (
                f"nạp lại dòng {r['so_goc']} mà khung nạp KHÔNG thấy trùng — mỗi lần bấm nhầm là "
                "quỹ phình thêm một lần")
        assert db.query(PhieuQuy).filter(PhieuQuy.so_goc.in_(
            ["PT-2026-9001", "PT-2026-9002"])).count() == 2
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_quy2_3_ly_do_ngoai_tu_vung_bao_o_buoc_KIEM_va_khong_ghi_gi():
    """ĐO ĐÚNG CHIỀU NGUY HƠN, và đo rằng nó bị chặn SỚM.

    Một lý do gõ sai phải nổ ở bước XEM TRƯỚC — lúc người nạp còn sửa được tệp — chứ không nổ
    giữa chừng khi đã ghi mất nửa số dòng. Và sau khi báo, sổ phải sạch.

    Luật này cũng canh cái bẫy đo được lúc chạy thật 04/11/2026: với chiều THU, một lý do sai
    KHÔNG rơi xuống "không quy tắc nào khớp" — nó rơi vào `THU_CHUA_RO_TM`, vì điều kiện của dòng
    ấy là `{"khop_don": False}` và không nhắc `muc_thu` chút nào. Nên từ vựng phải được chặn
    TRƯỚC khi hỏi bảng quy ước, và luật này đo cả chiều thu lẫn chiều chi.
    """
    from app.models.payments import PhieuQuy
    cua = _cua()
    db = _db()
    try:
        _san_sang(db)
        _nguoi(db)
        db.commit()
        truoc = db.query(PhieuQuy).count()
        for chieu in ("thu", "chi"):
            r = _dong(f"PT-2026-98{chieu}", chieu=chieu, ly_do=KHONG_CO_QUY_TAC)
            loi, _cb, _da_co = cua["kiem"](db, r)
            assert loi, (
                f"lý do `{KHONG_CO_QUY_TAC}` chiều {chieu} KHÔNG bị báo ở bước kiểm — một lỗi gõ "
                "của thủ quỹ sẽ lặng lẽ thành một cặp tài khoản nào đó, và không gì kêu lên")
            assert any(KHONG_CO_QUY_TAC in str(x) for x in loi), (
                "câu báo lỗi không nhắc lý do sai, người nạp không biết sửa ô nào: " + repr(loi))
        assert db.query(PhieuQuy).count() == truoc, "bước kiểm đã ghi gì vào sổ — nó chỉ được ĐỌC"

        # Để TRỐNG lý do thì ĐƯỢC, và đây không phải lối thoát: `THU_KHACH_TM` /
        # `THU_CHUA_RO_TM` khớp bằng `khop_don` chứ không bằng lý do, nên bắt buộc có lý do sẽ
        # chặn mất hai đường thu tiền mặt thật nhất của quầy.
        loi, _cb, _da_co = cua["kiem"](db, _dong("PT-2026-9700", chieu="thu", ly_do=""))
        assert not loi, "để trống lý do mà bị chặn — chặn mất đường thu tiền mặt tại quầy: " + repr(loi)
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_quy2_4_cua_tai_lo_KHONG_go_cung_mot_tai_khoan_nao():
    """Cả đợt QUY không gõ cứng một cặp tài khoản nào — cửa tải lô cũng vậy.

    Bỏ ghi chú và chuỗi tài liệu trước khi tìm: những đoạn giải thích trong tệp CÓ nhắc 131/331
    để nói với người đọc, và một phép đo đếm cả ghi chú thì buộc người viết phải giải thích ít đi.
    """
    assert os.path.exists(TEP_LO), "thiếu app/services/intake_so_quy.py"
    src = open(TEP_LO, encoding="utf-8").read()
    cay = ast.parse(src)
    chuoi = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            chuoi.add(n.value)
    ma = "\n".join(d for d in src.split("\n") if not d.lstrip().startswith("#"))
    for s in sorted(chuoi, key=len, reverse=True):
        ma = ma.replace(s, " ")
    thay = re.findall(r'1(?:11|12)\d?', ma)
    assert not thay, (
        f"cửa tải lô gõ cứng tài khoản tiền {thay} — nó phải HỎI bảng quy ước. Một cửa tự dựng "
        "bút toán sẽ lặng lẽ ghi khác cửa nhập tay cho tới ngày có người đối chiếu")
    assert "PQ.lap(" in src, "cửa tải lô không gọi `phieu_quy.lap` — nó đang đi một đường khác"
    assert "PhieuQuy(" not in ma, (
        "cửa tải lô tự dựng đối tượng `PhieuQuy` — nó phải đi qua `phieu_quy.lap` để chịu đúng "
        "những hàng rào của cửa nhập tay")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 5
def test_quy2_5_cua_tai_lo_khai_du_cho_nguoi_dung_tu_tai_duoc():
    """Ranh giới Chủ tịch ký 09/9/2026: mỗi con số phải có một cửa cho NGƯỜI DÙNG tự nhập hay tự tải.

    Một cửa khai thiếu cột, thiếu ví dụ, thiếu khoá chống trùng thì vẫn là một cửa trên giấy:
    người thủ quỹ mở lên không biết tệp phải có những cột nào nên lại nhắn nhờ ai đó nhập hộ.
    """
    from app.db.session import Base
    cua = _cua()
    for k in ("ten", "bang_dich", "phong_ban", "mo_ta", "khoa_chong_trung", "cot", "kiem", "nap"):
        assert cua.get(k), f"cửa `so_quy` thiếu khai báo `{k}`"
    assert cua["bang_dich"] in Base.metadata.tables, (
        f"`bang_dich` trỏ tới bảng không có thật: {cua['bang_dich']}")
    assert callable(cua["kiem"]) and callable(cua["nap"])

    khoa = {c["key"] for c in cua["cot"]}
    for can in ("so_goc", "ngay", "chieu", "so_tien", "ly_do", "noi_dung",
                "ten_doi_tuong", "ma_doi_tuong"):
        assert can in khoa, f"cửa tải lô thiếu cột `{can}`"
    for c in cua["cot"]:
        assert c.get("ten"), f"cột {c['key']} không có tên tiếng Việt cho người nạp đọc"
    bat_buoc = {c["key"] for c in cua["cot"] if c.get("bat_buoc")}
    assert {"so_goc", "ngay", "chieu", "so_tien"} <= bat_buoc, (
        "bốn cột làm nên một tờ phiếu quỹ phải là bắt buộc, đang bắt buộc: " + repr(bat_buoc))
    assert "ly_do" not in bat_buoc, (
        "bắt buộc lý do sẽ chặn mất thu/chi tiền mặt thẳng với khách — hai đường thật nhất của quầy")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 6
def test_quy2_6_hai_cua_ghi_RA_CUNG_MOT_but_toan():
    """LUẬT QUAN TRỌNG NHẤT CỦA ĐỢT: hai cửa đi qua đúng một đường.

    Không đo bằng soi chữ. Nạp một dòng qua cửa TẢI LÔ, lập cùng dữ liệu ấy qua cửa NHẬP TAY
    (`phieu_quy.lap` — đúng hàm nút «Lập phiếu» gọi), rồi so quy tắc đã khớp và so từng vế bút
    toán. Lệch một vế là có hai cách ghi cho một việc, và đó là thứ chỉ lộ ra lúc đối chiếu.
    """
    from sqlalchemy import select

    from app.models.accounting import JournalLine
    from app.services import phieu_quy as PQ
    cua = _cua()
    db = _db()
    try:
        _san_sang(db)
        u = _nguoi(db)
        db.commit()

        r = _dong("PT-2026-9601")
        loi, _cb, _da = cua["kiem"](db, r)
        assert not loi, repr(loi)
        p_lo, _ = cua["nap"](db, r, u.username)
        db.commit()

        p_tay, _bt = PQ.lap(db, u, chieu="chi", ngay=date.today(), so_tien=2_000_000,
                            ly_do="tra_ncc", noi_dung="Phép thử tải lô sổ quỹ",
                            ten_doi_tuong="Khách sạn Phép Thử", ma_doi_tuong="NCC-PT-001")

        assert p_lo.quy_tac == p_tay.quy_tac, (
            f"hai cửa khớp hai quy tắc khác nhau: tải lô `{p_lo.quy_tac}` ≠ nhập tay "
            f"`{p_tay.quy_tac}` — một việc đang có hai cách ghi")

        def _ve(eid, code):
            """So TẤT CẢ các cột của từng vế, trừ những cột BẮT BUỘC phải khác nhau.

            Không gọi tên cột tiền bằng phỏng đoán: đọc thẳng bảng rồi so cả hàng. Nhờ vậy một
            cột mới thêm vào bút toán cũng được so, mà không ai phải sửa phép thử này.

            `doc_no` ĐỂ RA NGOÀI, và để ra có lý do chứ không phải để cho phép thử xanh: hai tờ
            phiếu khác nhau thì PHẢI mang hai số chứng từ khác nhau — bắt chúng bằng nhau là bắt
            sai. Đo được lúc chạy thật 04/11/2026: bản đầu của luật này đỏ đúng vì chỗ ấy, mọi ô
            còn lại đã trùng khít. Nên thay vì bỏ qua, nó được đo bằng một phép CHẶT HƠN ngay
            dưới đây: mỗi vế phải mang đúng số của tờ phiếu sinh ra nó.
            """
            t = JournalLine.__table__
            rows = db.execute(select(t).where(t.c.entry_id == eid)).mappings().all()
            assert rows, f"bút toán của {code} không có vế nào"
            for r in rows:
                assert r["doc_no"] == code, (
                    f"vế của bút toán mang số chứng từ {r['doc_no']!r}, không phải {code!r} — "
                    "sổ cái và tờ phiếu không trỏ về nhau nữa")
            bo_qua = {"id", "entry_id", "created_at", "updated_at", "doc_no"}
            return sorted(tuple(sorted((k, str(v)) for k, v in r.items() if k not in bo_qua))
                          for r in rows)

        ve_lo = _ve(p_lo.journal_entry_id, p_lo.code)
        ve_tay = _ve(p_tay.journal_entry_id, p_tay.code)
        assert ve_lo == ve_tay, ("bút toán hai cửa KHÁC NHAU:\n  tải lô   " + repr(ve_lo) +
                                 "\n  nhập tay " + repr(ve_tay))
        assert p_lo.code != p_tay.code, "hai tờ phiếu khác nhau mà mang cùng một mã"
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 7
def test_quy2_7_ngay_tuong_lai_va_so_tien_am_bi_chan():
    """Sổ quỹ ghi việc ĐÃ xảy ra. Hai ô người ta gõ sai nhiều nhất là ngày và số tiền."""
    cua = _cua()
    db = _db()
    try:
        _san_sang(db)
        _nguoi(db)
        db.commit()
        mai = date.today() + timedelta(days=1)
        loi, _cb, _d = cua["kiem"](db, _dong("PT-2026-9501", ngay=mai))
        assert loi and any("tương lai" in str(x) for x in loi), (
            "ngày ở tương lai không bị chặn: " + repr(loi))
        loi, _cb, _d = cua["kiem"](db, _dong("PT-2026-9502", so_tien=0))
        assert loi, "số tiền 0 không bị chặn"
        loi, _cb, _d = cua["kiem"](db, _dong("", ))
        assert loi and any("gốc" in str(x) for x in loi), (
            "thiếu Số phiếu gốc không bị chặn — mà đó là khoá chống trùng: " + repr(loi))
    finally:
        db.close()
# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 8
def test_quy2_8_cua_mo_dung_cho_NGUOI_CAN_DUNG():
    """Một cửa không ai bấm được thì vẫn là việc còn thiếu — đây là luật đắt nhất của đợt.

    Bản vá đầu của đợt này khai đủ cột, đủ `kiem`/`nap`, và vẫn hỏng: `intake.py` giữ một bảng
    `VAI_TRO` RIÊNG, và `duoc_nap()` rơi về `QUAN_TRI` cho bất kỳ bộ nạp nào không khai. Nghĩa là
    cửa mở ra mà Kế toán và thủ quỹ — đúng hai người cầm tờ phiếu quỹ — không bấm được, còn Chủ
    tịch thì bấm được. Đo bằng chính hai hàm người dùng đi qua, không soi chữ bảng.

    Hai vai đúng bằng hai vai của cửa nhập tay ở Đợt QUY-1, nên đợt này không nới một quyền nào ra
    ngoài quyết định 02/11 của Chủ tịch: *"thủ quỹ nhập tay từng phiếu VÀ tải lô sổ quỹ"*.
    """
    from app.services.intake import BO_NAP_CHAM_TIEN, duoc_nap, duoc_nap_tep
    _cua()
    for vai in ("ketoan", "thu_quy"):
        assert duoc_nap("so_quy", vai), f"`{vai}` KHÔNG nhập tay được sổ quỹ"
        assert duoc_nap_tep("so_quy", vai), (
            f"`{vai}` KHÔNG tải lô được sổ quỹ — mà tải lô chính là việc đợt này sinh ra để làm")
    assert not duoc_nap("so_quy", "nv_kd"), "nhân viên kinh doanh nạp được sổ quỹ tiền mặt"
    assert not duoc_nap_tep("so_quy", "hdv"), "hướng dẫn viên tải lô được sổ quỹ tiền mặt"
    assert "so_quy" in BO_NAP_CHAM_TIEN, (
        "sổ quỹ tiền mặt không được khai là bộ nạp CHẠM TIỀN — tiêu chí P4 là DỮ LIỆU ĐI ĐÂU, và "
        "dòng ở đây đi thẳng vào tiền mặt")
