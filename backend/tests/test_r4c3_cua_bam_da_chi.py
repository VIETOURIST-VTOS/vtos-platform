# -*- coding: utf-8 -*-
"""Đợt R4c-3 02/11/2026 — CỬA BẤM ĐÃ CHI: bỏ phép đoán hai chữ cái, vế tiền sang cấp chi tiết.

Chủ tịch duyệt bản xem thử 02/11/2026.

HAI CHỖ ĐO ĐƯỢC TRƯỚC KHI VIẾT, cả hai trong `services/ops.py`:

  dòng 646  `paid_method = "tien_mat" if reason.lower().startswith("tm")`
            `reason` là ô "mã giao dịch / lý do" Kế toán gõ TAY. Nên vế tiền của bút toán chi
            được quyết bằng HAI CHỮ CÁI ĐẦU của một ô văn bản tự do. Và hộp `prompt()` trên màn
            hình còn DẠY người dùng phép đoán ấy: "hoặc 'TM' nếu tiền mặt".

  dòng 676  `cash = "111" if r.paid_method == "tien_mat" else "112"`
            Cả hai là tài khoản CHA; `1111`/`1121` mới là chi tiết. `post_entry` NHẬN bút toán
            vào tài khoản cha, không chặn. Chạy thật `cap_dinh_khoan.ngoai_luat` với đúng hai bút
            toán chỉ khác vế tiền: `331/112` NGOÀI LUẬT, `331/1121` trong luật — vì quy tắc
            TRA_NCC khai vế Có là `1121` và phép đối chiếu so bằng tiền tố.

Tức là MỌI khoản đã chi đều rơi vào rổ "định khoản ngoài luật" — cái rổ Kế toán trưởng mở ra để
tìm bút toán sai.
"""
import re
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.accounting import JournalEntry, JournalLine
from app.models.core import Tour, User
from app.models.hach_toan import HINH_THUC_TT, HTTT_QUA_NGAN_HANG, HTTT_QUA_TIEN_MAT
from app.models.ops import PaymentRequest
from app.services import accounting as ACC
from app.services import hach_toan as HT
from app.services import ops as O

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "expenses" / "page.tsx"
SVC = GOC / "backend" / "app" / "services" / "ops.py"


def _khong_loi_noi_tsx(s: str) -> str:
    """Bỏ lời chú thích trước khi đo. Một phép đo bắt cả LỜI NÓI VỀ việc làm thì nó không đo việc
    làm — va phải ba lần ngày 01/11/2026."""
    s = re.sub(r"\{/\*.*?\*/\}", "", s, flags=re.S)
    return "\n".join(d for d in s.splitlines() if not d.strip().startswith("//"))


def _khong_loi_noi_py(s: str) -> str:
    return "\n".join(d for d in s.splitlines() if not d.strip().startswith("#"))


def _rieng():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    db = sessionmaker(bind=e)()
    ACC.seed_accounts(db)
    HT.nap_mac_dinh(db)
    return db


def _unc(db, ma: str):
    """Một tệp UNC gắn với đề nghị chi.

    Cửa `pay` của main có hàng rào KS-16d (Chủ tịch chốt 31/10/2026): MỌI loại chi phải có UNC /
    phiếu chi tải lên trước khi bấm «Đã chi». Hàng rào ấy đứng TRƯỚC ô hình thức thanh toán của
    đợt này, và đó là đúng thứ tự — không có chứng từ thì chưa đến lượt hỏi trả bằng gì. Phép thử
    phải đi qua nó như người dùng thật, chứ không được gỡ nó ra cho dễ đo.
    """
    from app.models.attachments import Attachment
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id=ma, loai="unc",
                      ten_tep="unc.pdf", checksum="x" * 8, khoa_luu="k/" + ma,
                      thu_hoi=False))
    db.commit()


def _ho_so(db, ketoan, ma="DC-R4C3-1"):
    r = PaymentRequest(code=ma, category="chi_tour", supplier_name="NCC A",
                       amount=1_000_000.0, description="test R4c-3", created_by="nv_dh",
                       status="cho_chi", approved_by="tgd", signed_tgd=True)
    db.add(r)
    db.commit()
    _unc(db, r.code)
    return r


def _ketoan(db):
    u = User(username="kt.r4c3", full_name="Kế toán R4c-3", role="ketoan",
             password_hash="x")
    db.add(u)
    db.commit()
    return u


# ─────────────────────────────────────────────────────────────────────── LUẬT 1
def test_r4c3_1_o_trong_bi_tu_choi_khong_doan_va_khong_mac_dinh():
    """Ô trống là CHƯA CÓ SỐ — quy ước 4 ngày 09/9/2026.

    Và KHÔNG mặc định `chuyen_khoan`: một mặc định ở đây y hệt phép đoán cũ, chỉ im lặng hơn —
    nó cũng điền một con số không ai nói, và lần này còn không có hai chữ cái nào để lần ra vì sao.
    """
    db = _rieng()
    u = _ketoan(db)
    r = _ho_so(db, u)

    with pytest.raises(ValueError) as ex:
        O.step(db, u, r, "pay", "CK 123")
    assert "hình thức thanh toán" in str(ex.value).lower()

    # Và hồ sơ KHÔNG bị đổi trạng thái khi bị từ chối.
    db.refresh(r)
    assert r.status == "cho_chi", "bị từ chối mà hồ sơ vẫn chuyển sang đã chi"
    assert r.paid_method == "", "bị từ chối mà vẫn ghi hình thức"


# ─────────────────────────────────────────────────────────────────────── LUẬT 2
def test_r4c3_2_phep_doan_hai_chu_cai_khong_con_trong_ma_nguon():
    """Phép đoán phải MẤT khỏi mã nguồn, không chỉ bị đi vòng qua.

    Đo trên mã đã bỏ lời chú thích: bản vá này nói VỀ phép đoán cũ trong chú thích, nên một phép
    đo soi cả chú thích sẽ thấy nó và báo đỏ dù việc đã làm xong.
    """
    than = _khong_loi_noi_py(SVC.read_text(encoding="utf-8"))
    assert 'startswith("tm")' not in than, "phép đoán hai chữ cái CÒN trong mã"
    assert '"111" if' not in than, "vế tiền còn ghi vào tài khoản cha 111"
    assert 'cash = "1111" if r.paid_method in HTTT_QUA_TIEN_MAT else "1121"' in than, \
        "vế tiền chưa đọc HTTT_QUA_TIEN_MAT của máy chủ"
    # KHÔNG so chuỗi `== "tien_mat"` ở chỗ chọn vế tiền: séc tiền mặt vẫn rút trên tài khoản
    # ngân hàng, nên nó thuộc bên 112x — luật ấy đã khai một lần ở models/hach_toan.py.
    assert 'r.paid_method == "tien_mat"' not in than, \
        "còn so chuỗi tien_mat — khai lại luật séc tiền mặt lần thứ hai"


# ─────────────────────────────────────────────────────────────────────── LUẬT 3
@pytest.mark.parametrize("ht,tk", [("tien_mat", "1111"), ("chuyen_khoan", "1121"),
                                   ("sec_tien_mat", "1121"), ("unc", "1121")])
def test_r4c3_3_duong_chay_that_ve_tien_dung_cap_chi_tiet(ht, tk):
    """ĐƯỜNG CHẠY THẬT: bấm `pay` rồi đọc SỔ, không đọc mã.

    `sec_tien_mat` nằm trong danh sách này có chủ đích: séc lĩnh tiền mặt vẫn rút trên tài khoản
    ngân hàng, nên vế tiền của nó là 112x chứ không phải 111x. Một bản vá so chuỗi "tien_mat" sẽ
    đỏ ở đúng dòng này.
    """
    db = _rieng()
    u = _ketoan(db)
    r = _ho_so(db, u)

    O.step(db, u, r, "pay", "CT-001", hinh_thuc_tt=ht)
    db.refresh(r)
    assert r.status == "da_chi"
    assert r.paid_method == ht

    ds = [l.account_code for l in db.execute(
        select(JournalLine).join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.source_type == "lenh_chi")).scalars()]
    assert tk in ds, f"hình thức {ht}: sổ KHÔNG có vế tiền {tk} — {ds}"
    assert "111" not in ds and "112" not in ds, f"sổ còn ghi vào tài khoản cha: {ds}"


# ─────────────────────────────────────────────────────────────────────── LUẬT 4
def test_r4c3_4_chua_tt_bi_chan_va_hinh_thuc_la_cua_may_chu():
    """`chua_tt` bị chặn riêng, và danh sách nhận là `HINH_THUC_TT` của máy chủ chứ không gõ lại."""
    db = _rieng()
    u = _ketoan(db)

    r1 = _ho_so(db, u)
    with pytest.raises(ValueError) as ex:
        O.step(db, u, r1, "pay", "", hinh_thuc_tt="chua_tt")
    assert "chưa thanh toán" in str(ex.value).lower()

    r2 = _ho_so(db, u, "DC-R4C3-2")
    with pytest.raises(ValueError):
        O.step(db, u, r2, "pay", "", hinh_thuc_tt="bank_transfer")

    # Mọi hình thức CÒN LẠI của máy chủ đều phải đi được — không hard-code một bộ con.
    nhan = [k for k in HINH_THUC_TT if k and k != "chua_tt"]
    assert set(nhan) == set(HTTT_QUA_NGAN_HANG) | set(HTTT_QUA_TIEN_MAT), \
        "bộ hình thức của máy chủ đã đổi mà hai bảng con chưa khớp"
    for i, ht in enumerate(nhan):
        rx = PaymentRequest(code=f"DC-R4C3-ok{i}", category="chi_tour", supplier_name="B",
                            amount=100_000.0, description="x", created_by="nv_dh",
                            status="cho_chi", approved_by="tgd", signed_tgd=True)
        db.add(rx)
        db.commit()
        _unc(db, rx.code)
        O.step(db, u, rx, "pay", "", hinh_thuc_tt=ht)
        db.refresh(rx)
        assert rx.status == "da_chi", f"hình thức {ht} của máy chủ bị cửa từ chối"


# ─────────────────────────────────────────────────────────────────────── LUẬT 5
def test_r4c3_5_man_hinh_co_hai_o_roi_nhau_va_bo_hop_prompt():
    """Màn hình: hai ô RỜI NHAU, không còn `prompt()` cho bước `pay`, và lời trên trang đúng số.

    Hộp `prompt()` cũ không chỉ bất tiện — lời trong nó DẠY phép đoán ("hoặc 'TM' nếu tiền mặt").
    Bỏ mã mà để lời ấy thì màn hình vẫn dạy sai.
    """
    than = _khong_loi_noi_tsx(TRANG.read_text(encoding="utf-8"))

    assert "hinh_thuc_tt" in than, "màn hình KHÔNG gửi hình thức thanh toán"
    assert "'TM' nếu tiền mặt" not in than and "TM' nếu" not in than, \
        "lời dạy phép đoán CÒN trên màn hình"
    assert "Nợ 331 – Có 112<" not in than and "Có 112 " not in than, \
        "lời đầu trang còn nói vế tiền là 112"
    assert "1121" in than, "lời đầu trang chưa nói vế tiền ở cấp chi tiết"

    # Ô chọn đọc từ máy chủ, KHÔNG gõ lại nhãn tiếng Việt.
    assert re.search(r"(httt|hinhThuc|ht)\b", than), "không có nguồn danh sách hình thức"
    for chu in ("Séc chuyển khoản", "Ủy nhiệm chi"):
        assert chu not in than, f"màn hình gõ lại nhãn {chu!r} — nguồn thứ hai cho cùng một luật"


# ─────────────────────────────────────────────────────────────────────── LUẬT 6
def test_r4c3_6_cua_doc_but_toan_cap_cha_chi_doc():
    """Cửa liệt kê bút toán cấp cha: đếm đúng, và KHÔNG có một thân ghi nào.

    Chủ tịch chốt 02/11: để nguyên bút toán cũ. Một cửa "liệt kê để sửa" là đi ngược quyết định
    ấy, nên luật này đo cả việc cửa KHÔNG sửa được gì.
    """
    from app.api.v1 import accounting as API

    db = _rieng()
    for n, tk in ((1, "112"), (2, "1121"), (3, "111")):
        ACC.post_entry(db, "t", "ketoan", date(2026, 10, n), f"chi {tk}",
                       [{"account": "331", "debit": 1_000_000.0, "partner": "A"},
                        {"account": tk, "credit": 1_000_000.0, "partner": "A"}],
                       "lenh_chi", f"dc:T{n}", nghiep_vu="chi_tien")

    kq = API.tien_ghi_cap_cha.__wrapped__(None, None, 500, None, db) \
        if hasattr(API.tien_ghi_cap_cha, "__wrapped__") else None
    if kq is None:
        kq = API.tien_ghi_cap_cha(tu=None, den=None, gioi_han=500, u=None, db=db)

    assert kq["so_dong"] == 2, f"đếm sai số dòng cấp cha: {kq['so_dong']}"
    assert {d["tai_khoan"] for d in kq["dong"]} == {"111", "112"}, \
        "cửa bắt cả tài khoản chi tiết"
    assert kq["so_tien"] == 2_000_000

    # CHỈ ĐỌC: thân của cửa không được có một lời ghi nào.
    than = _khong_loi_noi_py(
        (GOC / "backend" / "app" / "api" / "v1" / "accounting.py").read_text(encoding="utf-8"))
    i = than.index("def tien_ghi_cap_cha")
    khoi = than[i:i + 2500]
    for ghi in ("db.add", "db.delete", "db.commit", "db.merge", "post_entry"):
        assert ghi not in khoi, f"cửa CHỈ ĐỌC mà có {ghi}"


# ─────────────────────────────────────────────────────────────────────── LUẬT 7
def test_r4c3_7_ba_tep_phep_thu_cu_giu_nguyen_y_dinh():
    """Đợt này SỬA ba tệp phép thử đang xanh — và luật này canh việc sửa ấy không bỏ phần nào.

    `test_settlement.py` và `test_bookings.py` gọi `pay` không kèm hình thức rồi đòi 200. Sau đợt
    này máy chủ từ chối, nên hai tệp ấy SẼ ĐỎ. Ý định gốc của chúng là "cả luồng duyệt chi chạy
    được từ đầu đến cuối", KHÔNG phải "một hình thức trống được nhận" — nên em thêm một ô vào
    đúng lời gọi ấy chứ không bỏ phép đo nào.

    Một bản vá làm xanh một phép thử bằng cách BỎ phần nó đo là một bản vá tự cấp phép cho mình.
    Nên luật này đo lại đúng việc ấy, bằng cách đếm.
    """
    t = GOC / "backend" / "tests"
    # Đếm đo được trên main trước khi vá: 33 và 39. Đợt này chỉ THÊM một ô vào lời gọi, nên hai
    # con số ấy không được giảm.
    for ten, so_assert in (("test_settlement.py", 33), ("test_bookings.py", 39)):
        s = (t / ten).read_text(encoding="utf-8")
        assert '"action": "pay"' in s or '"pay"' in s, f"{ten}: mất lời gọi pay"
        assert "hinh_thuc_tt" in s, f"{ten}: lời gọi pay chưa mang hình thức thanh toán"
        assert s.count("assert ") >= so_assert, \
            f"{ten}: còn {s.count('assert ')} phép đo — đợt này đã BỎ phép đo của tệp cũ"

    # Tệp thứ ba: đường SePay tự khớp. Không phải một phép đoán — `payments.py` đặt
    # `paid_method = "chuyen_khoan"` hẳn hòi vì một dòng sao kê NGÂN HÀNG thì biết chắc. Chỉ con
    # số tài khoản trong phép thử là ghim cấp CHA, đúng cái đợt này sửa. Đếm trên main: 35.
    s = (t / "test_ops.py").read_text(encoding="utf-8")
    assert '("1121", 0, 20_000_000)' in s, "test_ops.py chưa đổi vế tiền sang cấp chi tiết"
    assert '("112", 0, 20_000_000)' not in s, "test_ops.py còn ghim tài khoản cha"
    assert s.count("assert ") >= 35, \
        f"test_ops.py: còn {s.count('assert ')} phép đo — đợt này đã BỎ phép đo của tệp cũ"
