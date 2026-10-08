# -*- coding: utf-8 -*-
"""KY-2 · TK 627 cho chi phí sửa xe, bước kết chuyển 627 → 154, và ba cái tên còn chữ của TT 200.

CĂN CỨ TRA NGÀY 08/10/2026 trước khi sửa danh mục: Thông tư 99/2025/TT-BTC, hiệu lực 01/01/2026,
áp dụng cho năm tài chính bắt đầu từ 01/01/2026. Phụ lục I gọi 112 là "Tiền gửi không kỳ hạn",
242 là "Chi phí chờ phân bổ", 244 là "Ký quỹ, ký cược"; 627 là "Chi phí sản xuất chung".

CHỦ TỊCH QUYẾT 08/10/2026, hai vế:
  · sửa chữa xe hạch toán **627**, cuối kỳ **kết chuyển 154**;
  · **"chi phí sửa xe tháng nào tính tháng đó"** — KHÔNG treo 242 chờ phân bổ.

Vế sau là vế dễ mất nhất, nên nó có hàng rào riêng. Một lần đại tu 300 triệu đẩy sang 242 rồi rải
24 tháng thì tháng nào cũng đẹp và không tháng nào thật.

CHỖ DỄ HỎNG NHẤT CỦA VÒNG NÀY, và nó không nằm ở chỗ ai cũng nhìn: `TIEN_TO_KQKD` nhận mọi tài
khoản đầu 5/6/7/8, nên ngay khi danh mục có 627 thì bộ dò "tài khoản không thuộc bước nào" sẽ kêu
nó lên. Cách chữa SAI là nhét 627 vào một bước đóng về 911 — làm thế thì chi phí đội xe bị trừ vào
lãi hai lần: một lần qua 911, một lần nữa khi 154 ra 632. Nên 627 có bước RIÊNG, đích là 154.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ky2.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass

import json                                          # noqa: E402
from datetime import date, datetime                  # noqa: E402
from pathlib import Path                             # noqa: E402

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402

GOC = Path(__file__).resolve().parents[2]
KY = "2026-05"          # kỳ riêng của bộ test này


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


@pytest.fixture()
def ke_toan(db):
    from app.models.core import User
    return db.execute(select(User).where(User.role == "ketoan")).scalars().first()


def but_toan(db, ngay, lines, mo_ta="thử"):
    from app.services import accounting as ACC
    from app.models.core import User
    u = db.execute(select(User).where(User.role == "ketoan")).scalars().first()
    return ACC.post_entry(db, u.username, u.role, date.fromisoformat(ngay), mo_ta, lines,
                          "thu_cong", f"ky2:{datetime.now().timestamp()}")


# ------------------------------------------------- ba cái tên theo TT 99

TEN_TT99 = {"112": "Tiền gửi không kỳ hạn", "242": "Chi phí chờ phân bổ",
            "244": "Ký quỹ, ký cược", "627": "Chi phí sản xuất chung"}


def test_danh_muc_json_mang_dung_ten_cua_phu_luc_I():
    rows = json.loads((GOC / "backend" / "app" / "data" / "misa_tai_khoan.json")
                      .read_text(encoding="utf-8"))["tai_khoan"]
    ten = {r["code"]: r["name"] for r in rows}
    for ma, t in TEN_TT99.items():
        assert ten.get(ma) == t, f"TK {ma} đang là {ten.get(ma)!r}, TT 99 gọi là {t!r}"


def test_danh_muc_rut_gon_va_json_khong_noi_nguoc_nhau():
    """Hai danh mục cùng tồn tại thì phải cùng một chữ. Lệch nhau là người đọc tin nhầm cái sai.

    Và lệch kiểu này rất khó thấy: `seed_accounts` nạp JSON trước rồi mới bổ sung từ danh sách rút
    gọn những mã CHƯA CÓ — nên tên trong danh sách rút gọn gần như không bao giờ tới được cơ sở dữ
    liệu, và một cái tên sai ở đó sống mãi mà không ai phát hiện bằng cách nhìn màn hình.
    """
    from app.services import accounting as ACC
    rut_gon = {c: n for c, n, _k, _p in ACC.CHART}
    rows = json.loads(ACC.MISA_CHART.read_text(encoding="utf-8"))["tai_khoan"]
    ten_json = {r["code"]: r["name"] for r in rows}
    for ma, t in TEN_TT99.items():
        assert rut_gon.get(ma) == t, f"danh mục rút gọn gọi TK {ma} là {rut_gon.get(ma)!r}, phải là {t!r}"
        assert ten_json.get(ma) == t


def test_khong_con_chu_cua_tt200_o_ba_tai_khoan_nay():
    """Kiểm NGƯỢC: tên cũ phải biến mất, không chỉ tên mới phải xuất hiện.

    Đổi tên mà quên một chỗ thì phép thử "có tên mới" vẫn xanh trong khi màn hình kia còn tên cũ.
    """
    from app.services import accounting as ACC
    nguon = ACC.MISA_CHART.read_text(encoding="utf-8") + "\n" + "\n".join(
        f"{c}|{n}" for c, n, _k, _p in ACC.CHART)
    for cu in ('"Tiền gửi Ngân hàng"', '"Tiền gửi ngân hàng"',
               '"Chi phí trả trước"', '"Cầm cố, thế chấp, ký quỹ, ký cược"'):
        assert cu not in nguon, f"còn tên của TT 200 trong danh mục tài khoản: {cu}"


def test_bang_can_doi_in_ra_ten_moi():
    """Nhãn trên báo cáo cũng là tên tài khoản — hai nơi nói hai tên là một chỗ để người đọc nghi ngờ."""
    bc = (GOC / "backend" / "app" / "services" / "reports.py").read_text(encoding="utf-8")
    assert '"Chi phí chờ phân bổ"' in bc and '("242", "Chi phí trả trước"' not in bc


# ------------------------------------------------- 627 và quyết định của Chủ tịch

def test_627_co_trong_danh_muc_va_ghi_so_duoc(db):
    """Khai trong bảng là một chuyện, GHI ĐƯỢC là chuyện khác: `post_entry` tra `Account` thật."""
    from app.models.accounting import Account
    a = db.get(Account, "627")
    assert a is not None, "627 chưa vào cơ sở dữ liệu – seed_accounts chưa nạp"
    assert a.name == TEN_TT99["627"] and a.kind == "CP"
    e = but_toan(db, f"{KY}-10", [{"account": "627", "debit": 5_000_000, "note": "sửa xe 51B-12345"},
                                  {"account": "331", "credit": 5_000_000,
                                   "partner_code": "GARA01", "partner": "Garage thử"}])
    assert e.id, "không ghi được bút toán 627"


def test_sua_chua_xe_khai_627_va_khong_con_o_trong_nao(db):
    from app.services import misa as MS
    assert MS.CATEGORY_ACCOUNT["sua_chua_xe"] == "627"
    assert MS.thieu_tai_khoan() == [], "còn loại chi chạy được mà chưa khai tài khoản"


def test_sua_xe_khong_duoc_treo_242():
    """'Tháng nào tính tháng đó' — vế thứ hai của quyết định, và là vế dễ mất nhất.

    Hàng rào hỏi thẳng: không một loại chi nào được dẫn về 242. 242 là chi phí CHỜ PHÂN BỔ; đẩy một
    lần đại tu vào đó rồi rải nhiều tháng thì tháng phát sinh nhẹ đi và các tháng sau gánh hộ — lãi
    lỗ đội xe của mọi tháng đều sai, và sai theo hướng đẹp hơn thật.

    Nếu một ngày có khoản thật sự phải phân bổ (bảo hiểm xe 12 tháng chẳng hạn — đã có đường riêng
    qua `models/assets.py` loại `cp_tra_truoc`), thì sửa phép thử này kèm NGÀY và NGƯỜI QUYẾT, đừng
    xoá nó đi.
    """
    from app.services import misa as MS
    treo = {k: v for k, v in MS.CATEGORY_ACCOUNT.items() if str(v).startswith("242")}
    assert not treo, f"loại chi đang treo 242 chờ phân bổ: {treo}"
    assert not str(MS.CATEGORY_ACCOUNT["sua_chua_xe"]).startswith("242")


# ------------------------------------------------- bước 0: 627 → 154

def test_627_thuoc_mot_buoc_ket_chuyen_chu_khong_phai_lo_thung():
    from app.services import ket_so as KS
    assert KS._tk_cua_buoc("627") == 0, "627 không thuộc bước nào – sẽ bị báo là tài khoản bỏ sót"
    assert KS.BUOC_KET_CHUYEN[0]["ve_tk"] == KS.TK_CHI_PHI_DO_DANG == "154"
    for b in KS.BUOC_VE_911:
        assert KS.BUOC_KET_CHUYEN[b]["ve_tk"] == KS.TK_XAC_DINH_KQ, \
            f"bước {b} phải đóng về 911; đổi đích của nó là đổi cả báo cáo kết quả kinh doanh"


def test_ket_chuyen_627_qua_154_sang_632_chu_khong_ve_911(db, ke_toan):
    """Phép thử đắt nhất tệp: nó không hỏi "có chạy không", nó hỏi tiền ĐI ĐÚNG CHỖ không.

    627 về 911 thì chi phí đội xe bị trừ vào lãi hai lần — một lần ở đây, một lần nữa khi 154 ra 632
    lúc quyết toán chuyến. Cả hai lần đều ra số, nên không có gì báo động; chỉ có lãi sai.
    """
    from app.services import ket_so as KS
    but_toan(db, f"{KY}-11", [{"account": "627", "debit": 8_000_000, "note": "sửa xe"},
                              {"account": "331", "credit": 8_000_000,
                               "partner_code": "GARA02", "partner": "Garage thử 2"}])
    db.commit()

    xt = KS.xem_truoc_ket_chuyen(db, KY)
    b0 = next(b for b in xt["buoc"] if b["buoc"] == 0)
    assert b0["tong"] >= 8_000_000 and any(d["tk"] == "627" for d in b0["dong"])
    lai_truoc = xt["lai_truoc_buoc_4"]

    kq = KS.ket_chuyen(db, ke_toan, KY, [0])
    db.commit()
    assert [x["buoc"] for x in kq["da_ghi"]] == [0]

    from app.models.accounting import JournalEntry, JournalLine
    e = db.execute(select(JournalEntry).where(JournalEntry.source_ref == f"kc:{KY}:0")).scalars().one()
    assert e.source_type == KS.NGUON_KET_CHUYEN
    # CỘNG DỒN theo tài khoản, không lấy dòng cuối: chứng từ này có HAI dòng 154 (một nợ, một có),
    # và một dict dựng bằng comprehension sẽ lặng lẽ giữ dòng sau rồi báo 154 chỉ có bên Có.
    tk: dict[str, list] = {}
    for l in e.lines:
        o = tk.setdefault(l.account_code, [0.0, 0.0])
        o[0] += l.debit or 0
        o[1] += l.credit or 0
    assert "911" not in tk, "627 đang đóng về 911 – chi phí đội xe sẽ bị trừ vào lãi hai lần"
    assert tk["627"][1] >= 8_000_000, "627 phải ghi CÓ để đóng số dư"
    # Chủ tịch quyết 09/10/2026: đi QUA 154 rồi sang THẲNG 632, không chia theo chuyến. Hai chặng
    # trong CÙNG một chứng từ – nếu tách hai chứng từ thì có một khoảnh khắc 154 giữ số dư dở dang
    # không chuyến nào nhận, và khoảnh khắc ấy kéo dài bằng khoảng cách giữa hai lần ai đó bấm.
    assert tk["154"][0] >= 8_000_000 and tk["154"][1] >= 8_000_000, \
        "154 phải vừa nhận vừa trả trong cùng chứng từ – không để lại số dư dở dang"
    assert round(tk["154"][0] - tk["154"][1]) == 0, "154 phải về 0 trong chính chứng từ này"
    assert tk["632"][0] >= 8_000_000, "chi phí đội xe chưa sang giá vốn"

    # Bước 0 KHÔNG được làm đổi lãi của kỳ: nó mới chuyển chi phí sang dở dang.
    xt2 = KS.xem_truoc_ket_chuyen(db, KY)
    assert xt2["lai_truoc_buoc_4"] == lai_truoc, \
        "kết chuyển 627 về 154 mà lãi của kỳ đổi – tức nó đã lọt vào tổng 911"
    b0b = next(b for b in xt2["buoc"] if b["buoc"] == 0)
    assert b0b["da_ghi"], "ghi rồi mà bản xem trước vẫn báo chưa"

    lan2 = KS.ket_chuyen(db, ke_toan, KY, [0])
    assert lan2["da_ghi"] == [] and lan2["bo_qua"], "bấm lần hai ghi thêm một bộ bút toán nữa"


def test_phan_154_khong_cong_trinh_phai_ve_khong(db, ke_toan):
    """Cái giá của bước 0, và nó phải hiện ra chứ không lớn dần trong im lặng.

    Bút toán 154 bình thường bắt buộc có mã công trình; bước 0 đi lọt vì `account_rule_check` tha
    cho nguồn `ket_chuyen`. Nhờ thế mới không phải bịa một công thức chia chi phí đội xe cho từng
    chuyến — nhưng phần 154 ấy không thuộc chuyến nào, nên đường quyết toán chuyến sẽ không bao giờ
    dọn tới nó.
    """
    from app.services import ket_so as KS
    du = KS.du_154_khong_cong_trinh(db, KY)
    assert du["so_du"] == 0, (
        f"154 còn giữ {du['so_du']:,.0f} đ không thuộc chuyến nào – bước 0 phải đẩy hết sang 632 "
        "trong cùng chứng từ (Chủ tịch quyết 09/10/2026)")
    xt = KS.xem_truoc_ket_chuyen(db, KY)
    assert not any("154 đang giữ" in c for c in xt["canh_bao"]), "còn cảnh báo 154 treo mà lẽ ra đã sạch"


def test_627_co_so_du_thi_vao_buoc_0_chu_khong_vao_ro_bo_sot(db):
    """Bản đầu của phép thử này là TRANG TRÍ, và bẻ ngược mới lộ.

    Nó đọc kỳ KY — nơi phép thử trên vừa kết chuyển xong 627 nên số dư bằng 0. Mà rổ "tài khoản
    không thuộc bước nào" chỉ chứa tài khoản CÓ SỐ DƯ. Nên xoá hẳn bước 0 khỏi bảng, phép thử vẫn
    xanh: nó khẳng định "627 không bị kêu" trong đúng tình huống 627 chẳng có gì để kêu.

    Bản này ghi 627 ở MỘT KỲ KHÁC, chưa kết chuyển, rồi mới hỏi — lúc ấy câu hỏi mới có nghĩa.
    """
    from app.services import ket_so as KS
    ky2 = "2026-06"
    but_toan(db, f"{ky2}-09", [{"account": "627", "debit": 3_000_000, "note": "sửa xe kỳ sau"},
                               {"account": "331", "credit": 3_000_000,
                                "partner_code": "GARA03", "partner": "Garage thử 3"}])
    db.commit()
    xt = KS.xem_truoc_ket_chuyen(db, ky2)
    b0 = next(b for b in xt["buoc"] if b["buoc"] == 0)
    assert any(d["tk"] == "627" for d in b0["dong"]), "627 có số dư mà bước 0 không nhận"
    assert "627" not in {x["tk"] for x in xt["tai_khoan_khong_thuoc_buoc_nao"]}, \
        "627 vừa có bước nhận vừa bị kêu là bỏ sót — hai bộ máy đang nói ngược nhau"

def test_ban_xem_truoc_phai_phu_HET_cac_buoc_khai_trong_bang(db):
    """Bẻ ngược vòng này tìm ra LỖ IM LẶNG, và đây là hàng rào viết ra vì nó.

    Bỏ bước 0 khỏi vòng lặp của `xem_truoc_ket_chuyen` mà vẫn để nó trong `BUOC_KET_CHUYEN` thì:
    627 không được kết chuyển, VÀ `_tk_cua_buoc("627")` vẫn trả 0 nên bộ dò "tài khoản không thuộc
    bước nào" cũng không kêu. Số dư ấy không đi đâu cả và không dòng nào nói. Bảy phép thử khác của
    tệp này đều xanh trong tình huống đó.

    Nên phép thử hỏi đúng chỗ nối: MỌI bước khai trong bảng phải có mặt trong bản xem trước. Nó bắt
    được cả cách hỏng ngược lại — thêm một bước vào bảng rồi quên cho nó chạy.
    """
    from app.services import ket_so as KS
    xt = KS.xem_truoc_ket_chuyen(db, KY)
    co = {b["buoc"] for b in xt["buoc"]}
    thieu = set(KS.BUOC_KET_CHUYEN) - co
    assert not thieu, (
        f"bước {sorted(thieu)} khai trong BUOC_KET_CHUYEN mà bản xem trước không có — số dư của nó "
        "không được kết chuyển và cũng không bị báo là bỏ sót")
    assert 4 in co, "bước 4 (kết chuyển lãi lỗ) phải luôn có mặt"

def test_buoc_2_dong_ca_phan_632_ma_buoc_0_vua_day_sang(db, ke_toan):
    """Bản xem trước phải nói ĐÚNG với người sắp bấm, kể cả về số mà chính nó sắp tạo ra.

    Bước 0 đẩy chi phí đội xe vào 632 ngay trong lần chạy này. Nếu bước 2 chỉ đọc số dư 632 có SẴN
    lúc dựng bản xem trước thì phần ấy nằm lại tới kỳ sau — và tệ hơn, người đọc bản xem trước thấy
    một con số giá vốn thiếu đúng bằng chi phí đội xe rồi bấm, tin rằng mình vừa đóng hết.

    Ghi rồi thì KHÔNG gộp nữa: lúc ấy số đã nằm trong sổ và `_du_trong_ky` đã tính — gộp thêm lần
    nữa là đếm đôi.
    """
    from app.services import ket_so as KS
    ky3 = "2026-07"
    but_toan(db, f"{ky3}-08", [{"account": "627", "debit": 6_000_000, "note": "sửa xe"},
                               {"account": "331", "credit": 6_000_000,
                                "partner_code": "GARA04", "partner": "Garage thử 4"}])
    but_toan(db, f"{ky3}-09", [{"account": "632", "debit": 10_000_000, "project_code": "TOUR-THU"},
                               {"account": "331", "credit": 10_000_000,
                                "partner_code": "NCC01", "partner": "NCC thử"}])
    db.commit()

    xt = KS.xem_truoc_ket_chuyen(db, ky3)
    b2 = next(b for b in xt["buoc"] if b["buoc"] == 2)
    assert any(d.get("tu_buoc_0") for d in b2["dong"]), \
        "bước 2 không gộp phần 632 mà bước 0 sắp đẩy sang – bản xem trước nói thiếu"
    assert b2["tong"] >= 16_000_000, "tổng bước 2 thiếu đúng bằng chi phí đội xe"

    KS.ket_chuyen(db, ke_toan, ky3, [0, 2])
    db.commit()
    xt2 = KS.xem_truoc_ket_chuyen(db, ky3)
    b2b = next(b for b in xt2["buoc"] if b["buoc"] == 2)
    assert not any(d.get("tu_buoc_0") for d in b2b["dong"]), \
        "bước 0 đã ghi rồi mà bước 2 còn gộp thêm lần nữa – đếm đôi chi phí đội xe"

    # GHIM CÁI THẬT SỰ CHẶN ĐẾM ĐÔI, không phải cái trông như đang chặn. Bẻ ngược 09/10/2026: bỏ điều
    # kiện `ref not in da_ghi` đi thì phép thử trên VẪN XANH. Vì thứ ngăn đếm đôi không phải cái cờ
    # `da_ghi` — mà là số dư 627 đã về 0 ngay khi bước 0 ghi, nên tổng bước 0 bằng 0 và chẳng còn gì
    # để gộp. Cờ `da_ghi` chỉ là lớp khoá thứ hai.
    #
    # Phân biệt này quan trọng: người sửa sau đọc cái cờ rồi tưởng nó là chốt chặn, và khi đổi cách
    # tính tổng bước 0 (ví dụ lấy phát sinh trong kỳ thay vì lũy kế trừ phần đã kết chuyển) thì chốt
    # thật biến mất trong khi cái cờ vẫn còn đó, trông vẫn an toàn.
    b0b = next(b for b in xt2["buoc"] if b["buoc"] == 0)
    assert b0b["da_ghi"] and b0b["tong"] == 0, (
        "ghi bước 0 xong mà tổng của nó chưa về 0 – tức số dư 627 chưa được đóng, và ĐÂY mới là thứ "
        "ngăn bước 2 gộp lần thứ hai")
    assert KS.du_154_khong_cong_trinh(db, ky3)["so_du"] == 0
