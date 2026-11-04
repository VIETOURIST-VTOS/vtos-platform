# -*- coding: utf-8 -*-
"""Đợt QUY-1 04/11/2026 — SỔ QUỸ TIỀN MẶT: BẢNG PHIẾU QUỸ VÀ HAI CỬA LẬP PHIẾU (phần máy chủ).

Chủ tịch chốt 04/11/2026 qua tin nhắn: **bảng phiếu quỹ RIÊNG**, và **ghi sổ ngay, không thêm
bước xác nhận**.

VÌ SAO KHÔNG NỚI `Receipt` — ĐO ĐƯỢC, KHÔNG PHỎNG ĐOÁN

    app/models/payments.py:   booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))

`Receipt.booking_id` là NOT NULL ở TẦNG CƠ SỞ DỮ LIỆU, không chỉ ở `CashIn`. Nên một khoản nộp
quỹ / hoàn ký quỹ / thu khác KHÔNG THỂ là một `Receipt` mà không có di trú. Và `Receipt` là phiếu
thu CỦA KHÁCH — nó mang `payer`, `bank_txn_id`, `method`; nhét "nộp quỹ vào ngân hàng" vào đấy là
mô hình sai, không phải một ô còn thiếu.

Đo thêm trên main: tìm `cash_payment` / `chi_tien_mat` / `CashOut` trong `app/` → **0 kết quả**.
Không có phiếu chi tiền mặt ở bất cứ đâu.

ĐỢT NÀY KHÔNG ĐOÁN TÀI KHOẢN — NÓ HỎI BẢNG QUY ƯỚC

Phiếu quỹ KHÔNG gõ cứng một cặp tài khoản nào. Nó dựng bối cảnh (`hinh_thuc_tt = "tien_mat"`,
`muc_thu`/`muc_chi` = lý do người lập chọn) rồi gọi `HT.xem_truoc`. Không có quy tắc nào khớp thì
**TỪ CHỐI lập phiếu** và trả về danh sách lý do bảng quy ước đang nhận — chứ không lưu một phiếu
treo. Lưu phiếu mà không ghi sổ là dựng một rổ chờ thứ hai không ai canh, và số dư quỹ trên màn
hình sẽ lệch với sổ mà không gì kêu lên.

HỆ QUẢ PHẢI NÓI RA: ngày gộp đợt này, bốn lý do chi và hai lý do thu CHẠY ĐƯỢC NGAY vì sáu dòng
tiền mặt của Đợt R2 (15/10/2026) đã có trên main — `TRA_NCC_TM`, `TAM_UNG_TM`, `TRA_LUONG_TM`,
`CHI_QLDN_TM`, `THU_KHACH_TM`, `THU_CHUA_RO_TM`. Còn **nộp quỹ**, **rút quỹ** và **thu khác** thì
CHƯA, vì ba quy tắc ấy nằm trong mười dòng Chủ tịch chốt 02/11 mà Kế toán chưa trình qua cửa.
Đấy là hàng rào làm đúng việc: cửa có trước, quy ước có sau, và không ai phải sửa phép thử này.

LUẬT 5 ĐO ĐÚNG CHIỀU NGUY HƠN: một lý do không có quy tắc thì phải BỊ TỪ CHỐI.
"""
import ast
import os
import sys
from datetime import date, datetime

os.environ["DATABASE_URL"] = "sqlite:///./test_quy1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_quy1.db", "test_quy1.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SV = os.path.join(GOC, "app", "services", "phieu_quy.py")

# Lý do chắc chắn KHÔNG có trong từ vựng — dùng cho luật 5. Cố ý không phải một mã nghiệp vụ
# thật: nếu một ngày nào đó nó thành thật thì luật 5 đỏ, và đỏ ở đây là đúng (phải chọn lý do khác).
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
        # Đặt từng ô một và CHỈ những ô mô hình có thật: `User(...)` của SQLAlchemy ném
        # `TypeError` cho bất kỳ khoá nào không phải cột, nên một ô đoán sai (`is_active`) làm
        # đỏ bốn luật vì lý do chẳng liên quan gì đến thứ chúng đang canh.
        u = User(username=f"pq_{role}", role=role)
        for ten, gt in (("full_name", f"Phép thử {role}"), ("hashed_password", "x"),
                        ("password_hash", "x"), ("is_active", True), ("active", True)):
            if hasattr(type(u), ten):
                setattr(u, ten, gt)
        db.add(u)
        db.flush()
    return u


def _nap_quy_uoc(db):
    from app.services import hach_toan as HT
    HT.nap_mac_dinh(db)


def _nap_tai_khoan(db):
    """Danh mục tài khoản — `post_entry` đòi tài khoản có thật trong danh mục."""
    from app.services.accounting import seed_accounts
    seed_accounts(db)


# ───────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_quy1_1_bang_phieu_quy_co_trong_mo_hinh_va_CO_CUA():
    """Bảng mới phải có cửa — ranh giới Chủ tịch ký 09/9/2026.

    Đo bằng chính bộ kiểm KS-7 (`ks_cua_nhap.bang()`), không soi chữ một tệp: `phieu_quy` phải
    KHÔNG nằm trong rổ `khong_cua`. Thiếu dòng khai thì `test_cn1` của cửa hẹp cũng đỏ, nên luật
    này chỉ nói ra cho người đọc biết đợt này đã trả xong món ấy.
    """
    from app.services import ks_cua_nhap as CN
    b = CN.bang()
    assert "phieu_quy" not in (b.get("khong_cua") or []), (
        "bảng `phieu_quy` chưa có cửa nào — khai nó trong `ks_cua_nhap.CUA_TAY`")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_quy1_2_phieu_quy_lap_duoc_khi_KHONG_co_booking():
    """ĐÂY LÀ LÝ DO ĐỢT NÀY TỒN TẠI, và nó đo bằng cách GHI THẬT rồi đọc lại.

    `Receipt.booking_id` là NOT NULL; một khoản thu tiền mặt không gắn khách không có cửa nào.
    Soi chữ `nullable=True` trong tệp mô hình chỉ chứng minh có một dòng mã; ghi thật một dòng
    rồi đọc lại mới chứng minh cột ấy nhận NULL trên cơ sở dữ liệu.
    """
    from app.models.payments import PhieuQuy
    db = _db()
    try:
        p = PhieuQuy(code="PTQ-TEST-0001", chieu="thu", ngay=date(2026, 11, 4), so_tien=1000,
                     ly_do="thu_khac", noi_dung="phép thử", created_by="phep_thu")
        db.add(p)
        db.flush()
        db.commit()
        lai = db.get(PhieuQuy, p.id)
        assert lai is not None and lai.booking_id is None, (
            "phieu_quy.booking_id không nhận NULL — cả đợt này mất nghĩa")
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_quy1_3_hai_nghiep_vu_moi_co_that_va_moi_cho_goi_deu_khai_dung():
    """Hai chuyện, và chuyện thứ hai là chuyện `test_e3_1` canh cho cả kho.

    (a) Hai mã nghiệp vụ mới phải nằm trong `chung_tu_loai.NGHIEP_VU`, loại chứng từ PT và PC —
        không phải PKT: một phiếu quỹ LÀ tờ phiếu thu / phiếu chi, không phải phiếu kế toán.
    (b) Mọi mã `services/phieu_quy.py` KHAI RA (bảng `CHIEU`) phải có trong bảng ấy, và mọi chỗ
        gọi `post_entry` trong tệp phải truyền `nghiep_vu=`.

    BẢN ĐẦU CỦA LUẬT NÀY SAI, và ghi lại vì cái sai đáng nhớ hơn bản đúng: nó đọc cây cú pháp rồi
    chỉ nhặt `nghiep_vu=` mang một HẰNG CHUỖI. Nhưng dịch vụ đọc mã nghiệp vụ TỪ BẢNG `CHIEU` nên
    chỗ gọi truyền một TÊN BIẾN — phép đo không nhặt được gì và kết luận "không khai chỗ nào",
    trong khi tệp khai đủ. Một phép đo chỉ chấp nhận hằng chuỗi là một phép đo bắt người viết gõ
    cứng, tức là bắt họ viết tệ đi. Sửa: đo CHÍNH BẢNG khai, và đo riêng việc chỗ gọi có truyền
    khoá ấy hay không.
    """
    from app.services.chung_tu_loai import NGHIEP_VU
    from app.services import phieu_quy as PQ
    assert NGHIEP_VU.get("thu_quy_tien_mat", ("", ""))[1] == "PT", "thu_quy_tien_mat phải là PT"
    assert NGHIEP_VU.get("chi_quy_tien_mat", ("", ""))[1] == "PC", "chi_quy_tien_mat phải là PC"

    ma = [v[2] for v in PQ.CHIEU.values()]
    assert len(ma) == 2, f"bảng CHIEU phải có đúng hai chiều, đang có {sorted(PQ.CHIEU)}"
    la = sorted(set(ma) - set(NGHIEP_VU))
    assert not la, f"khai nghiệp vụ không có trong `chung_tu_loai.NGHIEP_VU`: {la}"

    cay = ast.parse(open(SV, encoding="utf-8").read(), SV)
    goi = [n for n in ast.walk(cay) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "post_entry"]
    assert goi, "`services/phieu_quy.py` không gọi `post_entry` ở đâu cả"
    for n in goi:
        assert any(kw.arg == "nghiep_vu" for kw in n.keywords), (
            f"chỗ gọi `post_entry` dòng {n.lineno} không khai `nghiep_vu=` — `test_e3_1` canh "
            "đúng điều này cho cả kho")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_quy1_4_chi_tien_mat_ghi_dung_1111_chu_khong_phai_111():
    """CHẠY THẬT, và đọc SỐ chứ không đọc mã.

    Lập một phiếu chi tiền mặt trả nhà cung cấp rồi đọc `journal_lines`. Vế tiền phải là `1111`.
    `111` là tài khoản CHA; ghi vào cha thì bút toán rơi vào rổ "định khoản ngoài luật" — đúng họ
    lỗi mà chuỗi R4c vừa chữa ở ba chỗ khác. Soi chữ trong tệp chỉ chứng minh có một dòng mã.
    """
    from app.services import phieu_quy as PQ
    db = _db()
    try:
        _nap_tai_khoan(db)
        _nap_quy_uoc(db)
        u = _nguoi(db, "thu_quy")
        p, bt = PQ.lap(db, u, chieu="chi", ngay=date(2026, 11, 4), so_tien=2_000_000,
                       ly_do="tra_ncc", noi_dung="Trả tiền mặt landtour",
                       ten_doi_tuong="NCC Phép Thử", ma_doi_tuong="NCC001")
        assert p.quy_tac == "TRA_NCC_TM", f"khớp quy tắc {p.quy_tac!r}, cần TRA_NCC_TM"
        assert p.journal_entry_id, "phiếu lập rồi mà không có bút toán nào"
        from app.models.accounting import JournalLine
        dong = db.query(JournalLine).filter(JournalLine.entry_id == p.journal_entry_id).all()
        # Cột là `account_code`, không phải `account`: `post_entry` NHẬN các dòng dạng
        # `{"account": ...}` rồi tự đổi tên khi ghi, nên khoá của lời gọi và tên cột KHÁC nhau.
        tk = sorted(l.account_code for l in dong)
        assert "1111" in tk, f"vế tiền không phải 1111 — các tài khoản: {tk}"
        assert "111" not in tk, f"GHI VÀO TÀI KHOẢN CHA 111 — các tài khoản: {tk}"
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────── LUẬT 5
def test_quy1_5_ly_do_KHONG_co_quy_tac_thi_phai_bi_TU_CHOI():
    """Chiều ngược, và đây là chiều nguy hơn.

    Đoán hộ một cặp tài khoản là làm sai sổ một cách im lặng — đúng ranh giới 09/9/2026: máy không
    đoán hộ người. Lưu phiếu rồi để treo cũng không được: số dư quỹ trên màn hình sẽ lệch với sổ.
    Nên phải TỪ CHỐI, KHÔNG lưu một dòng nào, và câu từ chối phải mang danh sách lý do bảng quy
    ước đang nhận — người gặp lỗi cần biết chọn gì, không phải đoán tiếp.

    CHẠY THẬT NGÀY 04/11/2026 BẮT RA MỘT LỖI THIẾT KẾ, và luật này giữ cho nó không quay lại: bản
    đầu của dịch vụ chỉ dựa vào "bảng quy ước có khớp không". Nhưng với chiều THU, một lý do gõ
    sai KHÔNG rơi xuống "không khớp" — nó rơi vào `THU_CHUA_RO_TM`, vì điều kiện của dòng ấy là
    `{"khop_don": False}` và KHÔNG nhắc tới `muc_thu` chút nào. Nên một lỗi gõ của thủ quỹ lặng lẽ
    thành 1111/3388 «tiền chưa rõ». Chữa: lý do là một TỪ VỰNG ĐÓNG, dịch vụ chặn trước khi hỏi
    bảng quy ước.
    """
    from app.models.payments import PhieuQuy
    from app.services import phieu_quy as PQ
    db = _db()
    try:
        _nap_tai_khoan(db)
        _nap_quy_uoc(db)
        u = _nguoi(db, "thu_quy")
        truoc = db.query(PhieuQuy).count()
        try:
            PQ.lap(db, u, chieu="thu", ngay=date(2026, 11, 4), so_tien=500_000,
                   ly_do=KHONG_CO_QUY_TAC, noi_dung="phép thử chiều ngược")
        except ValueError as ex:
            cau = str(ex)
        else:
            raise AssertionError("lập được phiếu với lý do không có quy tắc nào — phải bị từ chối")
        db.rollback()
        assert db.query(PhieuQuy).count() == truoc, "đã lưu một phiếu dù từ chối ghi sổ"
        assert KHONG_CO_QUY_TAC in cau, f"câu từ chối không nhắc lý do bị loại: {cau!r}"
        assert "quy ước" in cau.lower(), f"câu từ chối không nói vì sao: {cau!r}"
        assert PQ.ly_do_nhan_duoc(db, "chi"), "không trả về danh sách lý do nào để chọn"

        # VÀ CHIỀU THỨ BA: để TRỐNG lý do thì KHÔNG bị chặn — `THU_KHACH_TM` / `THU_CHUA_RO_TM`
        # khớp bằng `khop_don` chứ không bằng lý do, nên bắt buộc có lý do sẽ chặn mất hai đường
        # thu tiền mặt thật nhất của quầy. Không có phép đo này thì bản chữa của luật trên rất dễ
        # bị siết quá tay thành "lý do bắt buộc", và không gì nói ra.
        p, _ = PQ.lap(db, u, chieu="thu", ngay=date(2026, 11, 4), so_tien=300_000, ly_do="",
                      noi_dung="Khách nộp tiền mặt tại quầy, chưa rõ đơn",
                      ten_doi_tuong="Khách lẻ", ma_doi_tuong="KL001")
        assert p.journal_entry_id, "để trống lý do mà không ghi sổ được"
    finally:
        db.close()


# ───────────────────────────────────────────────────────────────────────────── LUẬT 6
def test_quy1_6_nhom_cua_quy_da_khai_va_moi_duong_co_that():
    """Ba cửa phải nằm TRONG một nhóm đã khai, và KHÔNG được mở thêm một nhóm nào.

    Chủ tịch chốt 04/11/2026 sau khi vòng bấm đầu đo ra cái giá: khai một nhóm cửa mới
    `/api/v1/quy` cho màn `/collections` làm `PHAM_VI_DA_CHOT` lệch 16 dòng vai và hai con số
    ghim trong `test_lg9` — HAI BẢNG CÓ CHỮ KÝ — trong khi KHÔNG vai nào bấm được thêm một cửa
    nào, vì ba cửa đều gác `require_roles("ketoan", "thu_quy")`. Đổi một bảng đã ký để đọc cho
    thuận tên là trả giá đắt cho một thứ không ai nhận được gì.

    Nên ba cửa nằm dưới `/api/v1/receipts` — nhóm đã khai sẵn cho màn `/collections`. Luật này
    canh CẢ HAI chiều: cửa phải có thật trên máy chủ (bài học ba đợt liên tiếp của họ lỗi
    "khai một đường không có thật"), và `access.py` phải KHÔNG hề đổi.
    """
    from app.services import access as AC
    from app.main import app
    duong = AC.MAN_HINH_API["/collections"]
    assert "/api/v1/receipts" in duong, "`/api/v1/receipts` biến mất khỏi bản đồ màn /collections"
    assert "/api/v1/quy" not in duong, (
        "đã mở nhóm cửa `/api/v1/quy` — Chủ tịch chốt 04/11/2026 KHÔNG mở, vì nó dịch hai bảng "
        "phạm vi đã ký mà không ai được thêm quyền gì")
    co = {r.path for r in app.routes}
    for duong_cua in ("/api/v1/receipts/quy/phieu", "/api/v1/receipts/quy/ly-do"):
        assert duong_cua in co, f"máy chủ không có cửa `{duong_cua}`"
    for p in duong:
        assert any(x == p or x.startswith(p + "/") for x in co), (
            f"bản đồ trỏ vào nhóm cửa `{p}` mà máy chủ không có đường nào")


# ───────────────────────────────────────────────────────────────────────────── LUẬT 7
def test_quy1_7_cua_lap_mo_dung_hai_vai_va_KHONG_dung_cua_xac_nhan():
    """Chủ tịch chốt 04/11/2026: ghi sổ ngay, không thêm bước xác nhận — nên cửa LẬP mở cho cả
    `ketoan` và `thu_quy`.

    Đọc bộ vai ĐÃ MỞ RỘNG (`dep.vai_tro_yeu_cau`) chứ không đọc tham số gốc: `require_roles` chạy
    `VKT.mo_rong` nên tham số gốc không nói hết sự thật — một lỗi em đã mắc ở Đợt DỌN-R4c3.

    Và `confirm_receipt` PHẢI CÒN `require_roles("ketoan",)`. Mở cả lập lẫn xác nhận cho một vai
    là bỏ tách bạch trách nhiệm, và đó là một quyết định phải có chữ ký riêng — không phải hệ quả
    của câu trả lời hôm nay.
    """
    import inspect
    from app.api.v1 import payments as API

    def vai_cua(f):
        ra = set()
        for ts in inspect.signature(f).parameters.values():
            phu = getattr(ts.default, "dependency", None)
            v = getattr(phu, "vai_tro_yeu_cau", None)
            if v:
                ra |= set(v)
        return ra

    lap = vai_cua(API.lap_phieu_quy)
    for vai in ("ketoan", "thu_quy"):
        assert vai in lap, f"cửa lập phiếu quỹ không mở cho vai {vai!r} — đang mở: {sorted(lap)}"

    # Chiều ngược. Đo bằng «thủ quỹ KHÔNG có trong bộ vai», không bằng «bộ vai đúng bằng
    # {'ketoan'}»: `require_roles("ketoan",)` chạy `VKT.mo_rong` nên `ketoan_truong` suy ra và
    # CÓ trong bộ. Một phép đo đòi bộ vai bằng đúng một tên sẽ đỏ vì phép suy, không vì cái sai
    # nó đang canh — và lúc ấy người đọc sẽ sửa phép thử chứ không sửa mã.
    xn = vai_cua(API.confirm_receipt)
    for vai in ("thu_quy", "ketoan_tt"):
        assert vai not in xn, (
            f"`confirm_receipt` đã mở cho {vai!r} — mở cả lập lẫn xác nhận cho một vai là bỏ tách "
            f"bạch trách nhiệm, và đó là quyết định phải có chữ ký riêng. Đang mở: {sorted(xn)}")
    assert "ketoan" in xn, f"`confirm_receipt` mất vai ketoan — đang mở: {sorted(xn)}"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 8
def test_quy1_8_mach_migration_con_dung_mot_dau():
    """Alembic từ chối chạy khi mạch có nhiều hơn một đầu, và Dockerfile chạy `alembic upgrade
    head` lúc container khởi động — nên hai đầu nghĩa là lần deploy tới API không lên được.

    Gọi thẳng bộ đọc của `test_mach_migration`, không viết lại phép đo thứ hai có thể lệch.
    """
    sys.path.insert(0, os.path.join(GOC, "tests"))
    from test_mach_migration import doc_mach
    mach = doc_mach()
    dau = sorted(set(mach) - {d for d in mach.values() if d})
    assert len(dau) == 1, f"mạch migration có {len(dau)} đầu: {dau}"


# ───────────────────────────────────────────────────────────────────────────── LUẬT 9
def test_quy1_9_so_quy_tien_mat_doc_ra_phieu_vua_lap():
    """Phiếu quỹ phải HIỆN TRONG SỔ QUỸ (S07-DN), không chỉ nằm trong bảng của nó.

    Đo bằng `books.cash_book` — đúng cái sổ Kế toán và kiểm toán mở ra. Một phiếu ghi sổ xong mà
    sổ quỹ không thấy thì nó không phải một phiếu quỹ, nó là một dòng trong một bảng rời.
    """
    from app.services import books as B
    from app.services import phieu_quy as PQ
    db = _db()
    try:
        _nap_tai_khoan(db)
        _nap_quy_uoc(db)
        u = _nguoi(db, "ketoan")
        p, _ = PQ.lap(db, u, chieu="chi", ngay=date(2026, 11, 4), so_tien=777_000,
                      ly_do="quan_ly", noi_dung="Mua văn phòng phẩm tiền mặt",
                      ten_doi_tuong="NCC VPP", ma_doi_tuong="NCC002")
        so = B.cash_book(db, date(2026, 11, 1), date(2026, 11, 30))
        dong = so["rows"]
        assert any(abs(float(d["amount_out"] or 0) - 777_000) < 1 for d in dong), (
            f"sổ quỹ không thấy phiếu {p.code} – {len(dong)} dòng trong kỳ")
    finally:
        db.close()
