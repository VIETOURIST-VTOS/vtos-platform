# -*- coding: utf-8 -*-
"""DT-1 · DT-2 — tiền khả dụng và cửa chốt số dư đã đối soát.

Tệp này canh SÁU luật của lệnh giao việc Robot A. Cả sáu đều là loại luật dễ bị gỡ mất về sau, vì gỡ
đi thì màn hình trông ĐẸP HƠN: có số ở mọi ô, có một dòng tổng, không ô nào để trống. Đó chính là
lý do phải có phép thử giữ chúng.

  D1  thiếu đầu vào thì RỖNG, không phải 0
  D2  không bù trừ giữa hai pháp nhân
  D3  mốc đối soát là ngày CŨ NHẤT, không phải ngày mới nhất
  D4  chốt lại thì bản cũ bị THAY THẾ, không bị xoá
  D5  lệch so với sao kê mà không giải thích thì không cho chốt
  D6  không chốt cho ngày chưa tới
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_dong_tien.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_dong_tien.db", "test_dong_tien.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.accounting import Account, JournalEntry, JournalLine  # noqa: E402
from app.models.banks import BankAccount  # noqa: E402
from app.models.core import Company  # noqa: E402
from app.models.dong_tien import ChotSoDu  # noqa: E402
from app.models.ops import PaymentRequest  # noqa: E402
from app.services import dong_tien as DT  # noqa: E402

HOM_NAY = date.today()


@pytest.fixture(scope="module", autouse=True)
def _dung_bang():
    # Dựng bảng qua ĐÚNG bước khởi động của ứng dụng, không gọi create_all tay: gọi tay thì bảng
    # được dựng từ metadata tại thời điểm gọi, còn ứng dụng thật dựng sau khi đã nạp xong mọi mô
    # hình – hai thứ lệch nhau thì phép thử xanh trên một lược đồ không ai chạy.
    with TestClient(app):
        pass
    db = SessionLocal()
    for ma, ten in (("1111", "Tiền mặt"), ("3388", "Phải trả khác")):
        if db.get(Account, ma) is None:
            db.add(Account(code=ma, name=ten, kind="TS"))
    db.add_all([Company(code="DT_A", name="Pháp nhân A"),
                Company(code="DT_B", name="Pháp nhân B")])
    db.add(BankAccount(code="DT_TK1", bank_name="TPBank"))
    db.add(BankAccount(code="DT_TK2", bank_name="Vietcombank"))
    db.commit()
    db.close()
    yield


def _db():
    return SessionLocal()


def _pn(db, ma):
    return db.execute(select(Company).where(Company.code == ma)).scalars().first()


def _tk(db, ma):
    return db.execute(select(BankAccount).where(BankAccount.code == ma)).scalars().first()


def _but_toan(db, cty, ma_tk, no=None, co=None, ngay=None):
    """Một bút toán ĐÃ GHI SỔ – để phân biệt 'sổ đang sống' với 'sổ chưa ai ghi'."""
    n = db.execute(select(JournalEntry)).scalars().all()
    e = JournalEntry(code=f"DT{len(n) + 1:04d}", entry_date=ngay or HOM_NAY, period="2026-09",
                     description="phép thử dòng tiền", status="da_ghi_so", company_id=cty.id)
    db.add(e)
    db.flush()
    db.add(JournalLine(entry_id=e.id, account_code=ma_tk, debit=no, credit=co))
    db.commit()


# --------------------------------------------------------------------------------- D1 · rỗng ≠ 0

def test_d1_thieu_dau_vao_thi_RONG_chu_khong_phai_khong():
    """Luật đắt nhất của cả phân hệ, và là luật dễ bị gỡ nhất.

    Bảng trả RỖNG trông như bảng hỏng, nên sớm muộn có người "sửa" nó thành 0 cho đẹp. Nhưng bảng
    trả 0 trông như bảng CHẠY TỐT và công ty hết tiền – người đọc tin nó, rồi dừng một khoản chi
    đáng lẽ phải chi. Rỗng thì người đọc đi hỏi; số 0 thì không ai hỏi gì cả.
    """
    db = _db()
    a = _pn(db, "DT_A")
    r = DT.tien_kha_dung(db, a.id)
    assert r["tien_kha_dung"] is None, "chưa chốt gì mà đã có số – số ấy ở đâu ra?"
    assert r["tien_kha_dung"] is not 0 and r["tien_kha_dung"] != 0  # noqa: F632
    assert r["doi_soat_den_ngay"] is None, "không có bản chốt nào mà vẫn có mốc đối soát"
    assert r["con_thieu"], "trả rỗng thì phải nói được thiếu cái gì"
    assert "0" not in r["vi_sao"][:40] or "không phải bằng 0" in r["vi_sao"]
    db.close()


def test_d1b_so_chua_ghi_thi_RONG_nhung_so_dang_song_ma_3388_trong_thi_la_KHONG():
    """Một tài khoản không có bút toán nào là câu trả lời MẬP MỜ – phải hỏi thêm một câu nữa.

    "Pháp nhân này không thu hộ ai" và "sổ của pháp nhân này chưa được ghi" nhìn giống hệt nhau khi
    chỉ soi TK 3388, mà kết luận thì ngược nhau: một bên 0 là số thật, bên kia 0 là số bịa – và bịa
    theo chiều nguy hiểm, tức khai khống tiền khả dụng.
    """
    db = _db()
    a = _pn(db, "DT_A")
    tk1 = _tk(db, "DT_TK1")
    DT.chot(db, "ketoan", a.id, "ngan_hang", tk1.id, HOM_NAY, 5_000_000_000)
    DT.chot(db, "ketoan", a.id, "tien_mat", None, HOM_NAY, 200_000_000)
    db.commit()

    r = DT.tien_kha_dung(db, a.id)
    assert r["tien_kha_dung"] is None, "sổ chưa có bút toán nào mà đã dám kết luận thu hộ bằng 0"
    assert any("chưa có bút toán" in t for t in r["con_thieu"])

    _but_toan(db, a, "1111", no=1000.0)          # sổ bắt đầu sống
    r = DT.tien_kha_dung(db, a.id)
    assert r["thanh_phan"]["tru_thu_ho_khach"] == 0, "sổ đang sống, 3388 trống – đó là 0 thật"
    assert r["tien_kha_dung"] == 5_200_000_000

    _but_toan(db, a, "3388", co=300_000_000.0)   # có khoản thu hộ thật
    r = DT.tien_kha_dung(db, a.id)
    assert r["tien_kha_dung"] == 4_900_000_000, "tiền thu hộ khách phải bị TRỪ khỏi tiền khả dụng"
    assert r["ghi_nho"]["tien_thu_ho_khach"] == 300_000_000, \
        "trừ rồi vẫn phải hiện riêng thành dòng ghi nhớ – người đọc cần thấy khoản ấy tồn tại"
    db.close()


def test_d1c_lenh_chi_da_duyet_chua_chuyen_bi_tru():
    """Tiền đã hứa không còn là tiền tiêu được, dù nó vẫn nằm trong tài khoản."""
    db = _db()
    a = _pn(db, "DT_A")
    truoc = DT.tien_kha_dung(db, a.id)["tien_kha_dung"]
    db.add(PaymentRequest(code="DTDC001", category="chi_tour", supplier_name="NCC thử",
                          amount=150_000_000, description="phép thử", status="cho_chi",
                          created_by="ketoan", company_id=a.id))
    db.commit()
    sau = DT.tien_kha_dung(db, a.id)["tien_kha_dung"]
    assert sau == truoc - 150_000_000, "đề nghị chi đã duyệt chờ chuyển phải bị trừ"
    db.close()


# ------------------------------------------------------------------- D2 · không bù trừ pháp nhân

def test_d2_khong_bu_tru_giua_hai_phap_nhan():
    """Tiền của A không trả được nợ của B nếu không có hợp đồng vay nội bộ và một lệnh chuyển thật."""
    db = _db()
    b = _pn(db, "DT_B")
    r = DT.tien_kha_dung(db, b.id)
    assert r["tien_kha_dung"] is None, "pháp nhân B chưa chốt gì mà đã hưởng tiền của A"
    assert any("pháp nhân này" in t for t in r["con_thieu"])
    db.close()


def test_d2b_toan_canh_la_MOT_DANH_SACH_khong_co_dong_tong():
    """Một dòng tổng ở đây là lời nói dối tiện tay: nó gợi rằng tám pháp nhân có chung một túi tiền.

    Con số hợp nhất là việc của báo cáo hợp nhất, nơi có bút toán loại trừ nội bộ – không phải việc
    của một phép cộng trên màn hình dòng tiền.
    """
    db = _db()
    a, b = _pn(db, "DT_A"), _pn(db, "DT_B")
    ds = DT.tien_kha_dung_nhieu_phap_nhan(db, [a.id, b.id])
    assert isinstance(ds, list) and len(ds) == 2
    assert all("phap_nhan" in x for x in ds), "mỗi dòng phải nói rõ nó là của pháp nhân nào"
    assert not any(str(x.get("phap_nhan", {}).get("ma", "")).lower() in ("tong", "tất cả", "all")
                   for x in ds), "có dòng tổng – đúng thứ hàm này cố ý không làm"
    db.close()


# ------------------------------------------------------------------------ D3 · mốc là ngày CŨ NHẤT

def test_d3_moc_doi_soat_lay_ngay_CU_NHAT():
    """Số này chỉ đáng tin tới mốc yếu nhất của nó.

    Chốt tài khoản 1 hôm nay và tài khoản 2 từ tuần trước thì tổng ấy KHÔNG phải số của hôm nay –
    nó là số của tuần trước cộng thêm một phần mới. Ghi mốc là ngày mới nhất là nói quá mức tin cậy
    của chính mình, và người đọc sẽ dùng nó như số hôm nay.
    """
    db = _db()
    a = _pn(db, "DT_A")
    tk2 = _tk(db, "DT_TK2")
    cu = HOM_NAY - timedelta(days=7)
    DT.chot(db, "ketoan", a.id, "ngan_hang", tk2.id, cu, 1_000_000_000)
    db.commit()
    r = DT.tien_kha_dung(db, a.id)
    assert r["doi_soat_den_ngay"] == cu, \
        f"mốc phải là ngày cũ nhất {cu}, nhận {r['doi_soat_den_ngay']}"
    db.close()


# ------------------------------------------------------------------------- D4 · thay thế, không xoá

def test_d4_chot_lai_thi_ban_cu_bi_THAY_THE_chu_khong_bi_xoa():
    """Ai đã chốt nhầm và ai đã sửa là câu kiểm toán sẽ hỏi. Xoá bản cũ là xoá đúng câu trả lời."""
    db = _db()
    a = _pn(db, "DT_A")
    ngay = HOM_NAY - timedelta(days=2)
    b1 = DT.chot(db, "ketoan", a.id, "tien_mat", None, ngay, 100_000_000)
    db.commit()
    id_cu = b1.id
    b2 = DT.chot(db, "ketoan", a.id, "tien_mat", None, ngay, 105_000_000, ghi_chu="đếm lại")
    db.commit()

    cu = db.get(ChotSoDu, id_cu)
    assert cu is not None, "bản chốt cũ bị XOÁ – mất dấu vết ai chốt nhầm"
    assert cu.trang_thai == "da_thay_the"
    assert b2.thay_the_id == id_cu, "bản mới phải trỏ về bản nó thay thế"

    hieu_luc = db.execute(select(ChotSoDu).where(
        ChotSoDu.company_id == a.id, ChotSoDu.nguon == "tien_mat",
        ChotSoDu.den_ngay == ngay, ChotSoDu.trang_thai == "hieu_luc")).scalars().all()
    assert len(hieu_luc) == 1, "một ngày chỉ được có MỘT bản chốt đang hiệu lực"
    assert hieu_luc[0].so_du == 105_000_000
    db.close()


# ------------------------------------------------------------------------------ D5 · lệch phải nói

def test_d5_lech_so_voi_sao_ke_ma_khong_giai_thich_thi_khong_cho_chot():
    """Lệch mà không ai giải thích thì lần sau không ai biết lệch ấy đã được xem chưa."""
    db = _db()
    a = _pn(db, "DT_A")
    tk = BankAccount(code="DT_TK3", bank_name="MBBank",
                     sepay_account_number="999", opening_balance=1_000_000)
    db.add(tk)
    db.commit()

    with pytest.raises(DT.LoiChot) as e:
        DT.chot(db, "ketoan", a.id, "ngan_hang", tk.id, HOM_NAY, 7_777_777)
    assert "lý do" in str(e.value).lower()
    db.rollback()

    b = DT.chot(db, "ketoan", a.id, "ngan_hang", tk.id, HOM_NAY, 7_777_777,
                ly_do_lech="SePay chưa đẩy giao dịch ngày 11/9")
    db.commit()
    assert b.lech == 7_777_777 - 1_000_000
    assert b.ly_do_lech
    db.close()


def test_d5b_may_khong_cong_duoc_thi_lech_RONG_chu_khong_phai_khong():
    """0 là 'đã đối chiếu và khớp'. Rỗng là 'không đối chiếu được'. Một ô rỗng không phân biệt được
    hai chuyện ấy, và cột lệch sẽ kêu ở mọi quỹ tiền mặt cho tới khi không ai đọc nó nữa."""
    db = _db()
    a = _pn(db, "DT_A")
    b = DT.chot(db, "ketoan", a.id, "tien_mat", None, HOM_NAY - timedelta(days=3), 50_000_000)
    db.commit()
    assert b.so_may_cong is None and b.lech is None
    db.close()


# ------------------------------------------------------------------------------- D6 · ngày chưa tới

def test_d6_khong_chot_cho_ngay_chua_toi():
    """Đối soát là việc đã làm xong, không phải việc dự kiến."""
    db = _db()
    a = _pn(db, "DT_A")
    with pytest.raises(DT.LoiChot):
        DT.chot(db, "ketoan", a.id, "tien_mat", None, HOM_NAY + timedelta(days=1), 1_000_000)
    db.rollback()
    db.close()


def test_d6b_chot_khong_co_phap_nhan_thi_bi_chan():
    """Số dư không gắn pháp nhân không cộng vào tiền của ai cả – và không được mặc định về công ty mẹ."""
    db = _db()
    with pytest.raises(DT.LoiChot) as e:
        DT.chot(db, "ketoan", None, "tien_mat", None, HOM_NAY, 1_000_000)
    assert "pháp nhân" in str(e.value).lower()
    db.rollback()
    db.close()


def test_d6c_chot_ngan_hang_phai_chon_tung_tai_khoan():
    """Gộp các tài khoản thành một dòng thì lúc lệch không tìm ra lệch ở tài khoản nào."""
    db = _db()
    a = _pn(db, "DT_A")
    with pytest.raises(DT.LoiChot) as e:
        DT.chot(db, "ketoan", a.id, "ngan_hang", None, HOM_NAY, 1_000_000)
    assert "tài khoản" in str(e.value).lower()
    db.rollback()
    db.close()


# ----------------------------------------------------------- nghiệm thu: bảng mới phải có cửa nhập

def test_bang_moi_co_cua_nhap_theo_ranh_gioi_09_9():
    """Ranh giới Chủ tịch đặt 09/9: mỗi con số phải có một cửa cho người nhập.

    Bảng `chot_so_du` thêm vào hôm nay, nên chốt chặn `test_ks_cua_nhap` phải nhìn thấy nó có cửa –
    nếu không thì chính bảng này là việc còn thiếu, và nó làm đỏ CI của mọi làn khác.
    """
    from app.services import ks_cua_nhap as CN
    b = CN.bang()
    assert "chot_so_du" not in b["khong_cua"], \
        "bảng chot_so_du chưa có cửa nhập – khai vào CUA_TAY của ks_cua_nhap.py"


# ============================================================================ DT-3 · bốn mốc lũy kế

def test_dt3_bon_cot_cung_mot_quy_tac_bao_gom_ngay():
    """Cột 7 ngày đếm 7 ngày thì cột 14 ngày phải đếm 14 – không phải 15.

    Lệch quy tắc bao gồm ngày giữa các cột là kiểu sai không ai nhìn ra, vì cả hai con số đều "trông
    hợp lý". Kiểm ở ngày 31 tháng 1 để bắt luôn chuyện cộng tháng vào tháng ngắn hơn.
    """
    from app.services.dong_tien import MOC, khoang_cua_moc
    for hn in (date(2026, 1, 31), date(2026, 9, 11), date(2026, 12, 31)):
        for ma, _nhan, kieu, n in MOC:
            tu, den = khoang_cua_moc(hn, ma)
            assert tu == hn, f"{ma}: mọi cột phải bắt đầu từ cùng một ngày"
            assert den >= tu
            if kieu == "ngay":
                assert (den - tu).days + 1 == n, \
                    f"{ma} ở ngày {hn}: đếm {(den - tu).days + 1} ngày, phải là {n}"
    # 31/1 + 1 tháng = 28/2 – con số này v1.1 viết thẳng ra, và bản cũ của Robot A cho 27/2.
    # Đây là chỗ chia tầng sửa một lỗi thật, không chỉ gộp hai bản trùng nhau.
    assert khoang_cua_moc(date(2026, 1, 31), "1t")[1] == date(2026, 2, 28)


def test_dt3_khong_co_o_tong_bon_cot_va_noi_ro_vi_sao():
    """Bốn cột lũy kế từ cùng một ngày thì chồng lên nhau. Cộng chúng lại là nhân đôi nhân ba."""
    db = _db()
    a = _pn(db, "DT_A")
    b = DT.bang_bon_moc(db, a.id)
    assert "tong_bon_cot" not in b and "tong" not in b, "có ô tổng bốn cột – đúng thứ phải không có"
    assert b["cong_bon_cot_la_sai"], "phải nói thẳng ra vì sao không được cộng"
    # Cột sau phải bao trọn cột trước – đó chính là lý do không cộng được.
    ma_cot = [c["ma"] for c in b["cot"]]
    khoang = {c["ma"]: (c["tu_ngay"], c["den_ngay"]) for c in b["cot"]}
    for truoc, sau in zip(ma_cot, ma_cot[1:]):
        assert khoang[sau][1] > khoang[truoc][1], f"{sau} phải bao trọn {truoc}"
    db.close()


def test_dt3_tien_dau_ky_la_CUNG_MOT_MOC_cho_ca_bon_cot():
    """Bốn mốc khác nhau thì bốn cột không so được với nhau nữa."""
    db = _db()
    a = _pn(db, "DT_A")
    b = DT.bang_bon_moc(db, a.id)
    assert "tien_kha_dung_dau_ky" in b, "tiền đầu kỳ phải là MỘT số dùng chung, không phải bốn số"
    assert isinstance(b["tien_kha_dung_dau_ky"], (float, int, type(None)))
    db.close()


def test_dt3_dong_chua_co_nguon_thi_RONG_va_co_ten_bo_phan():
    """Nguyên tắc B6 của lệnh giao việc: chưa có cửa thì ghi 'Chưa có nguồn' kèm bộ phận chịu trách
    nhiệm – không hiện 0, không nhập hộ.

    Một dòng thiếu nguồn mà trả 0 nhìn y hệt một dòng thật sự bằng 0, và cả bảng sẽ trông đủ trong
    khi thiếu mất hai khoản chi lớn nhất là lương và thuế.
    """
    db = _db()
    a = _pn(db, "DT_A")
    b = DT.bang_bon_moc(db, a.id)
    thieu = [d for d in b["dong"] if d.get("chua_co_nguon")]
    assert thieu, "bảng hiện tại phải còn dòng chưa có nguồn – DT-7 là việc rút danh sách này về rỗng"
    for d in thieu:
        assert all(v is None for v in d["so"].values()), \
            f"dòng {d['ma']} chưa có nguồn mà vẫn có số – số ấy ở đâu ra?"
        assert d["bo_phan_chiu_trach_nhiem"], \
            f"dòng {d['ma']} chưa có nguồn mà không ghi bộ phận nào chịu trách nhiệm"
    db.close()


def test_dt3_thieu_mot_dong_thi_KHONG_co_so_du_cuoi():
    """Cộng mười dòng có số rồi bỏ qua bốn dòng rỗng là ra con số ĐẸP HƠN thực tế.

    Đúng kiểu sai Chủ tịch đã chỉ đích danh ngày 11/9: người đọc thấy "còn 5 tỷ" trong lúc công ty
    còn 400 triệu sau khi trả nợ.
    """
    db = _db()
    a = _pn(db, "DT_A")
    b = DT.bang_bon_moc(db, a.id)
    if b["chua_co_nguon"]:
        assert all(v is None for v in b["so_du_du_kien_cuoi_khoang"].values()), \
            "còn dòng thiếu nguồn mà vẫn dựng ra số dư cuối"
        assert all(v is None for v in b["dong_tien_thuan"].values())
        assert b["vi_sao_khong_co_so_cuoi"], "để trống thì phải nói được vì sao"
    db.close()


def test_dt3_hai_dong_ghi_nho_khong_cong_vao_dong_tien_thuan():
    """DT-8: tiền thu hộ khách và ký quỹ giấy phép hiện riêng, KHÔNG cộng vào và không bù trừ."""
    db = _db()
    a = _pn(db, "DT_A")
    b = DT.bang_bon_moc(db, a.id)
    ma_dong = {d["ma"] for d in b["dong"]}
    assert "tien_thu_ho_khach" not in ma_dong and "ky_quy_giay_phep" not in ma_dong, \
        "dòng ghi nhớ lọt vào thân bảng – nó sẽ bị cộng vào dòng tiền thuần"
    assert "ghi_nho" in b, "hai dòng ghi nhớ phải hiện riêng, không bị giấu đi"
    db.close()


# ==================================================== DT-4 · số dư từng ngày và mức dự phòng

def test_dt4_nguong_du_phong_doi_DU_HAI_CHU_KY_TGD_va_CHU_TICH():
    """Chủ tịch quyết 11/9/2026: hai chữ ký là TỔNG GIÁM ĐỐC và CHỦ TỊCH – không phải Kế toán trưởng.

    Một ngưỡng tự có hiệu lực khi chưa ai ký là ngưỡng mang chữ ký của người viết mã. Ngưỡng này
    quyết định lúc nào hệ thống kêu "sắp thiếu tiền", nên nó phải đi qua đúng cửa ký.
    """
    from app.models.core import Param
    db = _db()
    a = _pn(db, "DT_A")

    v, ly_do = DT.muc_du_phong(db, a.id)
    assert v is None and "Chưa có ngưỡng" in ly_do, "chưa chốt gì mà đã có ngưỡng"

    p = Param(key=DT.khoa_muc_du_phong(a.id), value="500000000",
              label=f"Mức dự phòng {a.code}", effective_from=HOM_NAY, status="active",
              signed_tgd=True, signed_chutich=False)
    db.add(p)
    db.commit()
    v, ly_do = DT.muc_du_phong(db, a.id)
    assert v is None, "mới một chữ ký mà ngưỡng đã có hiệu lực"
    assert "Chủ tịch" in ly_do, "phải nói rõ còn thiếu chữ ký của ai"

    p.signed_chutich = True
    db.commit()
    v, ly_do = DT.muc_du_phong(db, a.id)
    assert v == 500_000_000 and not ly_do
    db.close()


def test_dt4_nguong_theo_TUNG_phap_nhan():
    """Mức dự phòng của pháp nhân A không phải mức của pháp nhân B."""
    db = _db()
    a, b = _pn(db, "DT_A"), _pn(db, "DT_B")
    assert DT.khoa_muc_du_phong(a.id) != DT.khoa_muc_du_phong(b.id)
    v_b, ly_do_b = DT.muc_du_phong(db, b.id)
    assert v_b is None, "pháp nhân B chưa ký gì mà đã hưởng ngưỡng của A"
    db.close()


def test_dt4_con_dong_thieu_nguon_thi_KHONG_ve_duong_so_du():
    """Một đường vẽ từ sáu trong mười một dòng luôn nằm CAO HƠN thực tế – và nằm cao đúng ở chỗ
    người đọc cần nó chính xác nhất."""
    db = _db()
    a = _pn(db, "DT_A")
    r = DT.so_du_tung_ngay(db, a.id)
    assert r["chua_co_nguon"], "phép thử này chỉ có nghĩa khi còn dòng thiếu nguồn"
    assert r["ngay"] == [], "còn dòng thiếu nguồn mà vẫn vẽ đường số dư"
    assert r["ngay_dau_thieu_tien"] is None and r["muc_thieu_lon_nhat"] is None
    assert r["vi_sao_khong_ve_duoc"], "không vẽ được thì phải nói vì sao"
    db.close()


def test_dt4_bat_duoc_THIEU_TIEN_GIUA_KY_du_cuoi_ky_van_duong(monkeypatch):
    """Đây là toàn bộ lý do DT-4 tồn tại, tách khỏi DT-3.

    Một kỳ hai tháng có thể kết thúc DƯƠNG mà vẫn có ngày âm ở giữa: ngày trả gốc vay rơi trước ngày
    khách thanh toán đợt hai. Bảng bốn mốc nói "cuối kỳ còn tiền" và nói đúng; công ty vẫn mất khả
    năng chi trả mấy ngày ở giữa.

    Thu hẹp sổ khai dòng về hai dòng CÓ NGUỒN để đo đúng phép tính đường số dư. Việc "còn dòng thiếu
    nguồn thì không vẽ" đã có phép thử riêng ngay trên.
    """
    from app.models.ban_hang import HopDongKhach, LichThanhToanHD
    from app.models.core import Param
    from app.models.finance import FinContract, FinSchedule

    db = _db()
    # Pháp nhân RIÊNG cho phép thử này: các phép thử trên đã để lại số dư cho DT_A, và một phép thử
    # phụ thuộc vào trạng thái phép thử khác để lại thì lúc đỏ không ai biết vì sao.
    a = db.execute(select(Company).where(Company.code == "DT_C")).scalars().first()
    if a is None:
        a = Company(code="DT_C", name="Pháp nhân C")
        db.add(a)
        db.flush()
    tkc = db.execute(select(BankAccount).where(BankAccount.code == "DT_TKC")).scalars().first()
    if tkc is None:
        tkc = BankAccount(code="DT_TKC", bank_name="ACB")
        db.add(tkc)
        db.flush()
    # Tiền khả dụng đầu kỳ 1 tỷ. Ngưỡng dự phòng 500 triệu.
    DT.chot(db, "ketoan", a.id, "ngan_hang", tkc.id, HOM_NAY, 1_000_000_000)
    DT.chot(db, "ketoan", a.id, "tien_mat", None, HOM_NAY, 0)
    _but_toan(db, a, "1111", no=1.0)      # sổ đang sống ⇒ thu hộ = 0 thật
    khoa = DT.khoa_muc_du_phong(a.id)
    db.add(Param(key=khoa, value="500000000", label="Mức dự phòng", effective_from=HOM_NAY,
                 status="active", signed_tgd=True, signed_chutich=True))
    db.commit()
    # Trả gốc vay 3 tỷ vào ngày thứ 5; khách trả 4 tỷ vào ngày thứ 20.
    hd = FinContract(code="DTV001", kind="vay", partner="Ngân hàng thử", company_id=a.id)
    db.add(hd)
    db.flush()
    db.add(FinSchedule(contract_id=hd.id, due_date=HOM_NAY + timedelta(days=4),
                       kind="tra_goc", amount=3_000_000_000, status="ke_hoach"))
    hdk = HopDongKhach(so_hop_dong="DTHD001", khach_ten="Khách thử", gia_tri=4_000_000_000,
                       company_id=a.id, trang_thai="hieu_luc")
    db.add(hdk)
    db.flush()
    db.add(LichThanhToanHD(hop_dong_id=hdk.id, dot=1, ten="Đợt 2", so_tien=4_000_000_000,
                           han=HOM_NAY + timedelta(days=19), moc="co_dinh"))
    db.commit()

    monkeypatch.setattr(DT, "DONG_BANG", (
        ("thu_khach", "Thu khách", "vao", "lich_thanh_toan_hd", ""),
        ("tra_goc_vay", "Trả gốc vay", "ra", "fin_schedule:tra_goc", ""),
    ))

    b = DT.bang_bon_moc(db, a.id)
    assert not b["chua_co_nguon"], "sổ khai thu hẹp rồi thì không còn dòng thiếu nguồn"
    cuoi_2_thang = b["so_du_du_kien_cuoi_khoang"]["2t"]

    r = DT.so_du_tung_ngay(db, a.id)
    assert r["ngay"], "đủ nguồn rồi mà vẫn không vẽ được đường số dư"
    assert r["ngay_dau_thieu_tien"] is not None, \
        (f"cuối kỳ còn {cuoi_2_thang:,.0f} nên bảng bốn mốc nói 'ổn', nhưng ngày trả gốc 3 tỷ rơi "
         f"TRƯỚC ngày khách trả 4 tỷ – DT-4 phải bắt được chỗ hụt giữa kỳ ấy")
    assert r["ngay_dau_thieu_tien"] == HOM_NAY + timedelta(days=4), \
        "ngày đầu thiếu tiền phải đúng ngày trả gốc"
    assert r["muc_thieu_lon_nhat"] and r["muc_thieu_lon_nhat"] > 0

    # Và cuối kỳ thì vẫn dương – đó chính là điều làm bảng bốn mốc một mình không đủ.
    assert cuoi_2_thang > r["muc_du_phong"], \
        "phép thử mất ý nghĩa nếu cuối kỳ cũng âm – chọn lại số"
    db.close()


# ================================ DT-5 · hai cơ sở ngày · DT-6 · chống tính trùng
#
# MƯỜI PHÉP THỬ CŨ Ở ĐÂY ĐÃ BỎ, CÙNG VỚI ĐOẠN MÃ CHÚNG CANH.
#
# Chúng canh bảng `nghia_vu_tien` của Robot A. Ngày 11/9/2026, khi gộp, thấy lằn VPM-11 đã dựng
# đúng khái niệm ấy ở `nghia_vu_thanh_toan`, hoàn chỉnh hơn, và Chủ tịch chốt giữ bản VPM-11.
#
# Phép thử của bản được giữ nằm ở `tests/test_vpm11_so_nghia_vu.py`. Ở đó cũng có bài canh hai cơ
# sở ngày và bài canh chống đếm trùng, nên bỏ mười phép thử này KHÔNG để hở chỗ nào: chỗ ấy vẫn có
# người canh, chỉ là canh bảng còn sống chứ không canh bảng đã bỏ.
#
# HAI BÀI CANH CHƯA CÓ NGƯỜI NHẬN, đã bàn giao sang lằn VPM và ghi lại ở cuối
# `app/services/dong_tien.py` để không rơi:
#   1. Dời `ngay_du_kien_tra` mà không ghi lý do thì phải BỊ CHẶN.
#   2. Khi cơ sở `du_kien` mượn `ngay_cam_ket`, từng dòng phải NÓI RA là đang mượn.
