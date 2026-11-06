# -*- coding: utf-8 -*-
"""ĐỢT R5b-1 02/11/2026 — ĐỐI CHIẾU LÃI LỖ TOUR: SỔ ↔ BẢNG TÍNH. SÁU LUẬT CANH.

Chủ tịch chốt 01/11/2026: *"số từ SỔ là số thật, bảng tính để cạnh để so, có cột lệch"*,
*"ghép theo mã tour, và nói ra bên nào thiếu"*, và *"thêm thẻ đối chiếu, giữ chuẩn 09/9"*.

LUẬT 2 LÀ LUẬT QUAN TRỌNG NHẤT, và nó đo chiều ngược: tệp đối chiếu KHÔNG được tính lại một con
số lãi lỗ nào. Ngày 09/9/2026 VTOS có BỐN công thức lãi lỗ tour chạy song song cho bốn con số
khác nhau; một bảng mang tên "đối chiếu" mà tự cộng lấy là công thức thứ NĂM, và lần này còn khó
thấy hơn vì ai cũng tin một bảng đối chiếu.

Dùng khuôn `_rieng()` của `test_r6b_so_du_dau_ky.py`: một CSDL riêng trong bộ nhớ, không nạp
`app.main`, không đăng nhập — CI chạy nhiều tệp trong MỘT tiến trình.
"""
import os
import re
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENV", "dev")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.session import Base  # noqa: E402
from app.models.accounting import Account, JournalEntry, JournalLine  # noqa: E402
from app.models.core import Booking, Tour, User  # noqa: E402
from app.models.vietrip import TourCostLine  # noqa: E402
from app.services import accounting as ACC  # noqa: E402
from app.services import doi_chieu_lai_lo as DCL  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TU, DEN = date(2027, 4, 1), date(2027, 4, 30)
# Đặt trong tháng 4/2027 — sau mọi mốc chốt sổ mà các tệp phép thử khác dùng, nên không làm lệch
# một con số nào của tệp khác. Cùng lý do `test_books.py` chọn tháng 3/2027.
NGAY = date(2027, 4, 10)


def _ma(duong: str) -> str:
    with open(os.path.join(GOC, *duong.split("/")), encoding="utf-8") as f:
        return f.read()


def _than(duong: str) -> str:
    """MÃ CHẠY của một tệp — đã bỏ hết dòng chú thích.

    Ngày 01/11/2026 ba đợt liền đỏ vì phép đo bắt đúng lời chú thích của bản vá. Tệp này nói
    rất nhiều về `Booking` và `JournalLine` trong phần giải thích, nên phải lọc trước khi đo.
    """
    return "\n".join(d for d in _ma(duong).splitlines() if not d.lstrip().startswith("#"))


def _rieng():
    co = set(Base.metadata.tables)
    dung = [b for b in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in b.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    # MOT nguoi dung de gieo: `tours.operator_id` va `bookings.sales_id` deu NOT NULL. Gieo
    # tai cho chu khong goi bo seed demo — bo ay dung 14 nguoi dung, 1.258 tour va ca mot kho
    # du lieu mau, va mot phep thu dung len do thi do BO GIEO chu khong do luat (loi Dot
    # R7-MCT, 01/11/2026).
    u = User(username="phepthu.r5b1", full_name="Phép thử R5b-1", role="ketoan",
             password_hash="x")
    db.add(u)
    db.flush()
    db.info["u"] = u
    return db


def _tk(db, kind: str) -> str:
    """Một tài khoản CHI TIẾT thuộc loại doanh thu / chi phí — hỏi danh mục, không gõ cứng.

    Gõ cứng "511" là buộc phép thử biết trước danh mục trông ra sao; hỏi danh mục thì nó đúng
    cả khi danh mục đổi. Bài học `_tk_chi_tiet` của Đợt R6b-1.
    """
    ds = [a.code for a in db.execute(select(Account)).scalars()
          if a.kind == kind and a.is_detail]
    assert ds, f"Danh muc khong co tai khoan chi tiet nao loai {kind}"
    return sorted(ds)[0]


def _tour(db, ma: str, ten: str = "", ngay: date | None = None) -> Tour:
    t = Tour(code=ma, name=ten or f"Chuyến {ma}", tour_type="le_noi_dia",
             start_date=ngay or NGAY, end_date=ngay or NGAY, status="ket_thuc",
             operator_id=db.info["u"].id)
    db.add(t)
    db.flush()
    return t


def _bang_tinh(db, t: Tour, doanh_thu: float | None, gia_von: float | None):
    """Số BẢNG TÍNH: booking (doanh thu) và dòng chi phí quyết toán (giá vốn).

    Đi qua ĐÚNG hai bảng mà `lai_lo_tour.so_theo_vietrip` đọc. Gieo thẳng vào bảng khác rồi
    mong nó ra số là đo một đường không ai dùng.
    """
    if doanh_thu is not None:
        u = db.info["u"]
        db.add(Booking(tour_id=t.id, code=f"BK-{t.code}", customer_name="Khách thử",
                       customer_phone="", source="phep_thu", request_id=0,
                       sales_id=u.id, created_by=u.username,
                       pax=1, amount=doanh_thu, discount=0, paid=0, cancelled=False))
    if gia_von is not None:
        db.add(TourCostLine(tour_id=t.id, line_no=1, description="Chi phí thử",
                            actual=gia_von, paid=0, status="hd"))
    db.flush()


def _so(db, ma: str, doanh_thu: float, chi_phi: float, tk_dt: str, tk_cp: str):
    """Số SỔ: một bút toán ĐÃ GHI SỔ, có mã công trình.

    Doanh thu ghi bên CÓ tài khoản doanh thu, chi phí ghi bên NỢ tài khoản chi phí — đúng chiều
    mà `books.project_summary` cộng. Ghi ngược chiều thì bảng ra số âm và phép thử xanh oan.
    """
    e = JournalEntry(code=f"JE-{ma}", entry_date=NGAY, period=NGAY.strftime("%Y-%m"),
                     description=f"Thử R5b {ma}", status="da_ghi_so", created_by="phep_thu")
    db.add(e)
    db.flush()
    db.add(JournalLine(entry_id=e.id, account_code=tk_dt, debit=0, credit=doanh_thu,
                       project_code=ma))
    db.add(JournalLine(entry_id=e.id, account_code=tk_cp, debit=chi_phi, credit=0,
                       project_code=ma))
    db.flush()


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 1 — CỬA CÓ MẶT, CHỈ ĐỌC, VÀ KHÔNG MỞ CHO ĐIỀU HÀNH
# ─────────────────────────────────────────────────────────────────────────────

def test_r5b1_1_cua_chi_doc_va_khong_mo_cho_dieu_hanh():
    """Bảng ĐỐI CHIẾU VỚI SỔ là việc của Kế toán. `lai_lo_tour.XEM` có Điều hành vì lãi lỗ
    chuyến là số của họ; mở bảng này cho Điều hành là bày sổ kế toán ra một màn hình Điều hành,
    và đó là một quyền chưa ai ký.

    Và cửa CHỈ ĐỌC: đối chiếu là để NÓI RA chênh lệch, không để sửa cho khớp. Sửa bên sổ còn là
    ghi sổ không qua chứng từ.
    """
    cua = _ma("app/api/v1/accounting.py")
    moc = "ĐỢT R5b-1 02/11/2026 — CỬA ĐỐI CHIẾU LÃI LỖ TOUR"
    assert moc in cua, "khong thay khoi R5b-1 trong accounting.py"
    # CAT o BANNER CUA DOT KE TIEP, khong cat o CUOI TEP: moi dot cua phan he nay NOI khoi
    # cua minh vao cuoi `accounting.py`, nen cat o cuoi tep la nhin thay ca ma cua cac dot gop
    # SAU. Do duoc 02/11/2026: `@router.post` cua Dot R6b-3a lam luat 1 cua Dot R5b-1 do oan.
    # Moc ranh gioi la mot dong chu thich mo dau bang `ĐỢT ` IN HOA — moi dot trong kho nay deu
    # mo khoi bang mot dong nhu the.
    _t = cua.split(moc, 1)[1]
    _m = re.search(r"\n# (?:── )?ĐỢT ", _t)
    khoi = "\n".join(d for d in (_t[:_m.start()] if _m else _t).splitlines()
                     if not d.lstrip().startswith("#"))
    assert '@router.get("/accounting/doi-chieu-lai-lo")' in khoi, (
        "Thieu cua doi chieu DUOI NHOM /accounting. Khai o goc la mo mot NHOM API RIENG "
        "ma khong man hinh nao khai, nen khong vai nao cham duoc cua — bay cua Dot "
        "DON-R4c3, va ban dau cua chinh dot nay (02/11) mac lai.")
    assert khoi.count("require_roles(") == 1, "quyen phai khai o chu ky, dung mot lan"
    assert "require_roles(*READ" in khoi, "cua phai dung bo vai READ cua phan he ke toan"
    for cam in ("@router.post", "@router.put", "@router.patch", "@router.delete"):
        assert cam not in khoi, f"khoi R5b-1 co duong ghi {cam} — cua nay CHI DOC"
    for vai in ('"tp_dh"', '"nv_dh"'):
        assert vai not in khoi, f"khoi R5b-1 mo cho Dieu hanh ({vai}) — quyen chua ai ky"


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 2 — TỆP ĐỐI CHIẾU KHÔNG TÍNH LẠI MỘT CON SỐ LÃI LỖ NÀO
# ─────────────────────────────────────────────────────────────────────────────

def test_r5b1_2_khong_tinh_lai_mot_con_so_lai_lo_nao():
    """Luật quan trọng nhất của đợt, và nó đo CHIỀU NGƯỢC.

    Bốn công thức lãi lỗ song song của ngày 09/9/2026 sinh ra vì mỗi màn hình tự cộng lấy một
    kiểu. Tệp này chỉ được làm một phép TRỪ trên hai con số đã có. Soi theo TÊN BẢNG chứ không
    theo cú pháp: soi cú pháp thì luôn có một cách viết khác lọt qua.
    """
    than = _than("app/services/doi_chieu_lai_lo.py")
    for bang in ("Booking", "TourCostLine", "JournalLine", "JournalEntry", "TourSettlement"):
        assert bang not in than, (
            f"doi_chieu_lai_lo.py cham vao bang {bang} — do la tu tinh lai lai lo, "
            f"cong thuc thu NAM")
    assert "BK.project_summary(" in than, "khong goi nguon SO"
    assert "LL.so_theo_vietrip(" in than, "khong goi nguon BANG TINH"
    # Và nó không được gọi `LL.bang`: hàm ấy lọc theo phạm vi pháp nhân và có phân trang, nên
    # hai bên sẽ phủ hai tập chuyến khác nhau — lúc ấy cột lệch nói về hai tập, không về một.
    assert "LL.bang(" not in than, (
        "goi LL.bang() — ham ay loc theo pham vi va phan trang, nen hai ben phu hai tap khac nhau")


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 3 — LỆCH CHỈ TÍNH KHI CÓ CẢ HAI BÊN
# ─────────────────────────────────────────────────────────────────────────────

def test_r5b1_3_lech_chi_tinh_khi_co_ca_hai_ben():
    """Quy tắc 4. Một tour chưa ghi sổ mà báo "lệch 900 triệu" là nói SỔ SAI, trong khi sự thật
    là sổ chưa có gì. Thiếu một bên là "chưa so được" — một trạng thái THỨ BA.
    """
    db = _rieng()
    dt, cp = _tk(db, "DT"), _tk(db, "CP")
    t1 = _tour(db, "R5B-CHI-BT")
    _bang_tinh(db, t1, 900_000_000, 700_000_000)      # chỉ có bảng tính
    _so(db, "R5B-CHI-SO", 500_000_000, 400_000_000, dt, cp)  # chỉ có sổ

    kq = DCL.doi_chieu(db, TU, DEN)
    theo_ma = {d["ma"]: d for d in kq["dong"]}

    a = theo_ma["R5B-CHI-BT"]
    assert a["co_trong_bang_tinh"] is True and a["co_trong_so"] is False
    assert a["bt_loi_nhuan"] == 200_000_000
    assert a["so_loi_nhuan"] is None, "so chua co gi ma bao mot con so"
    assert a["lech_loi_nhuan"] is None, "thieu mot ben ma van tinh lech"
    assert a["chua_so_duoc"] is True and a["khop"] is False

    b = theo_ma["R5B-CHI-SO"]
    assert b["co_trong_so"] is True and b["co_trong_bang_tinh"] is False
    assert b["so_loi_nhuan"] == 100_000_000
    assert b["bt_loi_nhuan"] is None
    assert b["lech_loi_nhuan"] is None, "thieu mot ben ma van tinh lech"
    assert b["chua_so_duoc"] is True


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 4 — HAI RỔ THIẾU HIỆN RA, VÀ KHÔNG VÀO TỔNG
# ─────────────────────────────────────────────────────────────────────────────

def test_r5b1_4_hai_ro_thieu_hien_ra_va_khong_vao_tong():
    """Hai rổ ấy đúng là hai chỗ cần nhìn nhất — cùng hình với dòng thiếu mã của Đợt R6b.

    Và chúng KHÔNG được cộng vào tổng: cộng vào là tạo ra một con số lệch giả, giả theo hướng
    dễ chịu nên càng ít người đi kiểm. Cùng luật mà `lai_lo_tour._cong` đã đặt.
    """
    db = _rieng()
    dt, cp = _tk(db, "DT"), _tk(db, "CP")
    t = _tour(db, "R5B-DU")
    _bang_tinh(db, t, 1_000_000_000, 600_000_000)
    _so(db, "R5B-DU", 1_000_000_000, 600_000_000, dt, cp)      # khớp
    _bang_tinh(db, _tour(db, "R5B-BT-ONLY"), 300_000_000, 100_000_000)
    _so(db, "R5B-SO-ONLY", 200_000_000, 50_000_000, dt, cp)

    kq = DCL.doi_chieu(db, TU, DEN)
    assert kq["chi_co_bang_tinh"] == ["R5B-BT-ONLY"], kq["chi_co_bang_tinh"]
    assert kq["chi_co_trong_so"] == ["R5B-SO-ONLY"], kq["chi_co_trong_so"]
    assert kq["khop"] is False, "con hai ro thieu ma bao khop ca bang"

    loai = {c["loai"] for c in kq["canh_bao"]}
    assert {"chi_co_trong_so", "chi_co_bang_tinh"} <= loai, loai

    # TỔNG chỉ cộng dòng so được — đúng MỘT dòng ở đây.
    c = kq["cong"]
    assert c["so_dong_so_duoc"] == 1, c
    assert c["so_dong_chua_so_duoc"] == 2, c
    assert c["so_doanh_thu"] == 1_000_000_000, "tong da cong ca dong thieu mot ben"
    assert c["bt_doanh_thu"] == 1_000_000_000, "tong da cong ca dong thieu mot ben"
    assert c["lech_loi_nhuan"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 5 — KHỚP THÌ BÁO KHỚP, LỆCH THÌ NÓI ĐÚNG SỐ LỆCH
# ─────────────────────────────────────────────────────────────────────────────

def test_r5b1_5_khop_thi_bao_khop_lech_thi_noi_dung_so():
    """Chiều xuôi của luật 3, và nó cần thiết: một bản chỉ làm đúng luật 3 có thể báo "chưa so
    được" cho MỌI dòng và vẫn xanh. Hai chiều đo trên cùng một bảng thì không còn đường đi tắt.

    Và SỔ ĐỨNG TRƯỚC: lệch = sổ − bảng tính. Dấu của nó có nghĩa, nên phải đo cả dấu.
    """
    db = _rieng()
    dt, cp = _tk(db, "DT"), _tk(db, "CP")
    t1 = _tour(db, "R5B-KHOP")
    _bang_tinh(db, t1, 800_000_000, 500_000_000)
    _so(db, "R5B-KHOP", 800_000_000, 500_000_000, dt, cp)
    t2 = _tour(db, "R5B-LECH")
    _bang_tinh(db, t2, 800_000_000, 500_000_000)
    _so(db, "R5B-LECH", 750_000_000, 520_000_000, dt, cp)

    kq = DCL.doi_chieu(db, TU, DEN)
    theo_ma = {d["ma"]: d for d in kq["dong"]}

    k = theo_ma["R5B-KHOP"]
    assert k["khop"] is True and k["chua_so_duoc"] is False
    assert (k["lech_doanh_thu"], k["lech_chi_phi"], k["lech_loi_nhuan"]) == (0, 0, 0)

    l = theo_ma["R5B-LECH"]
    assert l["khop"] is False and l["chua_so_duoc"] is False
    # Sổ − bảng tính: doanh thu sổ THẤP hơn 50tr, chi phí sổ CAO hơn 20tr, lãi sổ thấp hơn 70tr.
    assert l["lech_doanh_thu"] == -50_000_000, l
    assert l["lech_chi_phi"] == 20_000_000, l
    assert l["lech_loi_nhuan"] == -70_000_000, l
    assert any(c["loai"] == "lech_so" for c in kq["canh_bao"]), kq["canh_bao"]


# ─────────────────────────────────────────────────────────────────────────────
# LUẬT 6 — HAI CƠ SỞ NGÀY KHÁC NHAU, VÀ CỬA NÓI RA
# ─────────────────────────────────────────────────────────────────────────────

def test_r5b1_6_hai_co_so_ngay_khac_nhau_va_cua_noi_ra():
    """Sổ lọc theo NGÀY HẠCH TOÁN; bảng tính lấy chuyến theo NGÀY KHỞI HÀNH. Một chuyến đi
    tháng 12 mà hóa đơn về tháng 1 nằm ở hai khoảng khác nhau — lệch ấy là THẬT và là một việc
    phải xử, không phải lỗi của phép đối chiếu.

    Giấu nó bằng cách gộp hai cơ sở ngày là xoá mất chính câu hỏi ấy. Nên cửa phải NÓI RA, và
    phải vẫn ghép được một chuyến khởi hành NGOÀI khoảng mà có mã trong sổ — nếu không, chuyến
    ấy rơi vào rổ "chỉ có trong sổ" một cách sai.
    """
    kq = DCL.doi_chieu(_rieng(), TU, DEN)
    assert "co_so_ngay" in kq and set(kq["co_so_ngay"]) == {"so", "bang_tinh"}, kq.get("co_so_ngay")
    assert "NGÀY HẠCH TOÁN" in kq["co_so_ngay"]["so"]
    assert "NGÀY KHỞI HÀNH" in kq["co_so_ngay"]["bang_tinh"]
    assert "số thật" in kq["ghi_chu"], "cua khong noi ra ben nao la so that"

    # Chuyến khởi hành NGOÀI khoảng, nhưng có bút toán TRONG khoảng: phải ghép được cả hai bên.
    db = _rieng()
    dt, cp = _tk(db, "DT"), _tk(db, "CP")
    t = _tour(db, "R5B-NGOAI-KHOANG", "Chuyến đi trước", ngay=date(2027, 1, 5))
    _bang_tinh(db, t, 400_000_000, 250_000_000)
    _so(db, "R5B-NGOAI-KHOANG", 400_000_000, 250_000_000, dt, cp)
    d = {x["ma"]: x for x in DCL.doi_chieu(db, TU, DEN)["dong"]}["R5B-NGOAI-KHOANG"]
    assert d["co_trong_so"] and d["co_trong_bang_tinh"], (
        "chuyen khoi hanh ngoai khoang ma co ma trong so phai ghep duoc ca hai ben")
    assert d["khop"] is True, d
