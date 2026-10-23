# -*- coding: utf-8 -*-
"""ĐỢT R4b-2c (23/10/2026) — THẺ "HÓA ĐƠN CÒN THIẾU" TRÊN BÀN LÀM VIỆC KẾ TOÁN.

VÌ SAO CÓ TỆP NÀY

Đợt R4b-2a dựng phép tính, R4b-2b dựng màn hình. Cả hai đều đúng và cả hai đều có thể nằm đó
không ai mở. Màn hình `/hoa-don-thieu` chỉ có ích với người đã biết là mình cần mở nó — tức là
với người đã biết câu trả lời. Bàn làm việc là chỗ duy nhất người ta mở mỗi ngày mà không cần
ai nhắc, nên con số phải xuất hiện ở đó.

Một ô đếm trên bàn làm việc là chỗ dễ sinh ra hai điều hỏng, và tệp này canh đúng hai điều ấy:

  · HAI PHÉP ĐẾM LỆCH NHAU. Bàn làm việc mở mỗi lần vào trang chủ nên nó cần một câu đếm rẻ,
    không dựng cả danh sách. Thế là có hai đường tới cùng một con số — và hai đường thì sớm
    muộn lệch. Lệch thì không ai biết con nào đúng: người đọc thấy "7 dòng" trên bàn, bấm vào
    thấy 9 dòng, và từ lần ấy thôi tin cả hai. R4b2c_3 bắt hai con số phải bằng nhau TRÊN SỔ
    THẬT, không bằng cách đọc mã.

  · MỘT Ô ĐẾM MỞ THÊM CỬA. Đợt này thêm `ketoan_truong` vào khối bàn làm việc của Kế toán.
    Khối ấy có sáu dòng trỏ sang sáu màn hình. Thêm một vai vào khối là đặt sáu đường dẫn lên
    bàn vai ấy — và nếu một trong sáu màn hình vai ấy không mở được thì ta vừa làm ra đúng món
    nợ mà `test_lg4` sinh ra để cấm, chỉ là ở một chỗ `test_lg4` không nhìn tới. R4b2c_5 đi
    từng `href` trong khối và đòi vai ấy vốn đã thấy màn hình đó.

VÀ MỘT ĐIỀU NỮA, nhỏ hơn nhưng đã sai một lần trong đợt này: THIẾU HÓA ĐƠN KHÔNG CHẶN KHÓA KỲ
(Chủ tịch chốt 22/10/2026). Một dòng trên bàn làm việc rất dễ bị người đọc hiểu là một việc
chặn — nên câu chữ phải tự nói ra, và R4b2c_4 ghim câu ấy.
"""
import os
import re
import sys
import tempfile
from datetime import date

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_r4b2c.db")
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
from app.services import books as BK                             # noqa: E402
from app.services import hach_toan as HT                         # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUONG = "/hoa-don-thieu"
TU = date(2026, 1, 1)
DEN = date(2026, 12, 31)


def _ma(ten):
    with open(os.path.join(GOC, "app", "services", ten), encoding="utf-8") as f:
        return f.read()


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


def _ct(db, dong, ngay=date(2026, 3, 15)):
    """Ghi thẳng một chứng từ: (tài khoản, nợ, có). Không đi qua `post_entry` — đợt này ĐỌC sổ,
    và sổ thật có cả những bút toán không đi qua cửa ấy."""
    _n[0] += 1
    e = JournalEntry(code=f"R4B2C-{_n[0]}", entry_date=ngay, ngay_chung_tu=ngay,
                     period=f"{ngay:%Y-%m}", description="Sổ thử Đợt R4b-2c",
                     status="da_ghi_so", source_type="thu_cong", source_ref="")
    db.add(e)
    db.flush()
    for tk, no, co in dong:
        db.add(JournalLine(entry_id=e.id, account_code=tk, debit=no, credit=co))
    db.commit()
    return e


def _khoi_ketoan():
    """Thân khối bàn làm việc của Kế toán, lấy theo THỤT LỀ chứ không theo số dòng."""
    d = _ma("dashboard.py").splitlines()
    vt = [k for k, l in enumerate(d) if re.match(r'^\s*if role in \("ketoan", "ketoan_truong"\):', l)]
    assert len(vt) == 1, (
        "Không tìm thấy ĐÚNG MỘT khối `if role in (\"ketoan\", \"ketoan_truong\"):` trong "
        f"dashboard.py — thấy {len(vt)} chỗ. Đợt R4b-2c sửa đúng một chỗ ấy; nếu khối bị tách "
        "hay đổi tên thì phép thử R4b2c_5 đang canh một chỗ không còn tồn tại.")
    k = vt[0]
    tl = len(d[k]) - len(d[k].lstrip())
    than = []
    for l in d[k + 1:]:
        if l.strip() and (len(l) - len(l.lstrip())) <= tl:
            break
        than.append(l)
    return "\n".join(than)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. CÓ HÀM ĐẾM, VÀ BÀN LÀM VIỆC GỌI NÓ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4b2c_1_ban_lam_viec_goi_ham_dem():
    assert hasattr(BK, "dem_hoa_don_thieu"), "Đợt R4b-2c chưa thêm `books.dem_hoa_don_thieu`"
    kh = _khoi_ketoan()
    assert "dem_hoa_don_thieu(" in kh, (
        "Khối bàn làm việc của Kế toán không gọi `dem_hoa_don_thieu`. Phép tính có mà không ai "
        "gọi thì con số không bao giờ lên tới mắt người đọc — đúng tình trạng của R4b-2a trước "
        "khi có màn hình, và của R4b-2b trước khi có dòng này.")
    assert DUONG in kh, f"Dòng trên bàn làm việc phải trỏ về màn hình `{DUONG}`"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. BÀN LÀM VIỆC KHÔNG ĐƯỢC GỌI HÀM ĐẮT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4b2c_2_ban_lam_viec_KHONG_goi_ham_dung_danh_sach():
    """`hoa_don_thieu()` nạp tới XLSX_LIMIT dòng rồi đọc thêm `_contra_map` cho từng bút toán.

    Đúng cho một màn hình việc cần làm, mở khi người ta thật sự muốn xem. Sai cho một ô đếm mở
    mỗi lần ai đó vào trang chủ — `/dashboard` vốn tính bằng phần tư giây, và một hàm như thế
    kéo nó lên vài giây cho MỌI người, kể cả người không bao giờ nhìn ô ấy.
    """
    kh = _khoi_ketoan()
    xau = [l for l in kh.splitlines()
           if re.search(r"(?<!dem_)hoa_don_thieu\s*\(", l) and not l.lstrip().startswith("#")]
    assert not xau, (
        "Khối bàn làm việc gọi `hoa_don_thieu()` — hàm DỰNG DANH SÁCH. Ô đếm phải gọi "
        f"`dem_hoa_don_thieu()`. Dòng vi phạm: {xau}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. HAI PHÉP ĐẾM PHẢI RA MỘT CON SỐ — ĐO TRÊN SỔ THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4b2c_3_hai_phep_dem_khong_duoc_lech():
    """Phép thử QUAN TRỌNG NHẤT của tệp này.

    Đối chiếu bằng cách CHẠY cả hai hàm trên cùng một cuốn sổ, không bằng cách đọc mã: hai câu
    SQL viết khác nhau vẫn có thể cùng trông hợp lý mà ra hai con số.
    """
    db = _rieng()
    # Một bút toán CÓ thuế: hai dòng không phải thuế → hai dòng chưa nhận hóa đơn.
    e1 = _ct(db, [("1561", 10_000_000, 0), ("1331", 1_000_000, 0), ("331", 0, 11_000_000)])
    # Một bút toán KHÔNG thuế: không đòi hóa đơn, không được đếm.
    _ct(db, [("642", 5_000_000, 0), ("1111", 0, 5_000_000)])

    dem = BK.dem_hoa_don_thieu(db, TU, DEN)
    day_du = BK.hoa_don_thieu(db, TU, DEN)
    assert dem["chua_nhan"] == day_du["dem"]["chua_nhan"] == 2, (
        "Hai phép đếm lệch nhau hoặc đếm sai. Ô đếm trên bàn làm việc và màn hình việc cần làm "
        f"phải nói cùng một con số. Ô đếm: {dem['chua_nhan']}; màn hình: "
        f"{day_du['dem']['chua_nhan']}; chờ: 2 (hai dòng không phải thuế của bút toán có thuế).")
    assert dem["thue"] == day_du["thue"] == 1_000_000, (
        f"Phần thuế lệch: ô đếm {dem['thue']}, màn hình {day_du['thue']}, chờ 1.000.000. "
        "Hai hàm phải cộng trên CÙNG tập bút toán — những bút toán còn dòng chưa nhận hóa đơn.")

    # GHI HÓA ĐƠN CHO MỘT DÒNG rồi đo lại: con số phải TỤT ở CẢ HAI, cùng một nhịp.
    from sqlalchemy import select as _sel
    d = db.execute(_sel(JournalLine).where(JournalLine.entry_id == e1.id,
                                           JournalLine.account_code == "1561")).scalars().one()
    BK.ghi_hoa_don(db, d.id, BK.HD_DA_NHAP, "ketoan",
                   ngay_hoa_don=date(2026, 3, 16), so_hoa_don="1C26TSH 0004127")
    db.commit()
    dem2 = BK.dem_hoa_don_thieu(db, TU, DEN)
    day_du2 = BK.hoa_don_thieu(db, TU, DEN)
    assert dem2["chua_nhan"] == day_du2["dem"]["chua_nhan"] == 1, (
        f"Ghi hóa đơn cho một dòng mà hai con số không cùng tụt: ô đếm {dem2['chua_nhan']}, "
        f"màn hình {day_du2['dem']['chua_nhan']}, chờ 1.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. CÂU CHỮ PHẢI NÓI RÕ: KHÔNG CHẶN KHÓA KỲ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4b2c_4_dong_tren_ban_phai_noi_khong_chan_khoa_ky():
    """Chủ tịch chốt 22/10/2026: thiếu hóa đơn chỉ ĐẾM, không chặn khóa kỳ.

    Ghim CÂU CHỮ chứ không ghim phép tính, vì chỗ hỏng ở đây là chỗ HIỂU: một dòng nằm trong
    hàng "việc chờ duyệt" mà không nói gì thì người đọc mặc định nó chặn, rồi đi tìm xem phải
    bấm gì để khóa được kỳ. Chi phí của câu ấy là bốn chữ; chi phí của việc thiếu nó là một
    cuộc gọi cho Kế toán trưởng.
    """
    kh = _khoi_ketoan()
    # BỎ DÒNG CHÚ THÍCH TRƯỚC KHI TÌM: câu này phải nằm trong NHÃN người đọc nhìn thấy, không
    # phải trong một dòng chú thích chỉ lập trình viên đọc. Một chú thích nói "không chặn khóa
    # kỳ" mà nhãn im lặng thì phép thử xanh còn người đọc vẫn hiểu sai.
    ma = "\n".join(l for l in kh.splitlines() if not l.lstrip().startswith("#"))
    assert "KHÔNG CHẶN KHÓA KỲ" in ma.upper(), (
        "Nhãn của dòng hóa đơn còn thiếu trên bàn làm việc không nói ra rằng nó KHÔNG CHẶN "
        "KHÓA KỲ (Chủ tịch chốt 22/10/2026). Phần mã của khối đang là:\n" + ma)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. THÊM MỘT VAI VÀO KHỐI KHÔNG ĐƯỢC MỞ THÊM CỬA NÀO
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4b2c_5_ketoan_truong_vao_khoi_KHONG_mo_them_cua():
    """Đợt này thêm `ketoan_truong` vào khối bàn làm việc của Kế toán — sáu dòng, sáu đường dẫn.

    `test_lg4` canh món nợ "thấy menu mà không gọi được API". Bàn làm việc là một món nợ KHÁC
    mà `test_lg4` không nhìn tới: một đường dẫn trên bàn trỏ tới màn hình vai ấy KHÔNG mở được.
    Người đọc bấm vào, nhận một trang trắng hoặc một lỗi quyền, và lần sau thôi tin cả bàn.

    Quy ước `ks_ma_tran`: trang KHÔNG liệt kê trong `MENU_ROLES` là trang ai đăng nhập cũng
    thấy — nên chỗ ấy không phải lỗi, và phép thử nói rõ điều đó thay vì im lặng cho qua.
    """
    from app.services.access import MENU_ROLES
    kh = _khoi_ketoan()
    duong = sorted({h.split("?")[0] for h in re.findall(r'"href":\s*"([^"]+)"', kh)})
    assert duong, "Không đọc được đường dẫn nào trong khối — phép thử này đang canh khoảng không"
    thieu = [d for d in duong if d in MENU_ROLES and "ketoan_truong" not in MENU_ROLES[d]]
    assert not thieu, (
        "Khối bàn làm việc nay mở cho `ketoan_truong`, nhưng có đường dẫn trỏ tới màn hình vai "
        "ấy KHÔNG mở được. Chọn một trong hai: bỏ dòng ấy ra khỏi khối, hoặc xin ký mở màn hình "
        f"cho vai ấy — ĐỪNG lặng lẽ để nó trên bàn. Đường dẫn vi phạm: {thieu}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. LUẬT ĐẾM KHÔNG ĐƯỢC CHÉP LẦN THỨ HAI
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_r4b2c_6_ham_dem_doc_hang_so_chu_khong_go_lai():
    """Hai hàm đếm cùng một thứ là chỗ dễ lệch nhất; chúng chỉ an toàn khi cùng đọc MỘT bản khai.

    R4b2c_3 đo được cái lệch hôm nay. Phép thử này chặn cái lệch của NGÀY MAI: hôm nào Chủ tịch
    thêm một nhánh tài khoản thuế, người sửa `TK_THUE` sẽ không nghĩ tới việc đi tìm một chuỗi
    "133" gõ tay nằm trong một hàm khác.
    """
    import inspect
    ma = inspect.getsource(BK.dem_hoa_don_thieu)
    than = "\n".join(l for l in ma.splitlines() if not l.lstrip().startswith("#"))
    assert "TK_THUE" in than, "`dem_hoa_don_thieu` phải đọc `TK_THUE`, không tự khai nhánh thuế"
    assert "HD_CHUA" in than, "`dem_hoa_don_thieu` phải đọc `HD_CHUA`, không gõ lại chuỗi rỗng"
    for t in BK.TK_THUE:
        assert f'"{t}"' not in than and f"'{t}'" not in than, (
            f"`dem_hoa_don_thieu` gõ thẳng số hiệu tài khoản {t!r} thay vì đọc `TK_THUE`")
