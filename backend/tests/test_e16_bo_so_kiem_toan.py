# -*- coding: utf-8 -*-
"""Đợt E16 (14/10/2026) — BỘ SỐ BCTC KIỂM TOÁN: KẾ TOÁN TẢI LÊN, CHỦ TỊCH KÝ.

VÌ SAO CÓ TỆP NÀY

Trước đợt này, bộ số BCTC đã soát xét nằm trong KHO MÃ — `app/data/kiem_toan_2026h1.json`, ba mươi
tài khoản, do robot gõ. Cửa "Chốt sổ theo BCTC kiểm toán" trên màn hình gửi lên ĐÚNG HAI tham số
(`column`, `replace`) và KHÔNG có ô tải tệp nào: nó chỉ phát lại một bộ số cố định, không ai ký.

Bộ số ấy không phải một bảng dữ liệu bình thường. Nó là ĐÁP ÁN: `misa.import_audited_checkpoint`
lấy nó làm chuẩn rồi kéo toàn bộ sổ về bằng chênh lệch. Một con số sai ở đây không lệch một dòng —
nó viết lại bảng cân đối kế toán của một công ty đại chúng.

TỆP NÀY CANH SÁU ĐIỀU

 1. BỐN PHÉP KIỂM TRƯỚC KHI GHI. Không cân → trả tệp. Dòng đối tượng cộng không khớp dòng tài
    khoản → trả tệp. Dòng đối tượng mồ côi → trả tệp. Ô tiền là chữ, mã trùng → trả tệp.
 2. HAI NGƯỜI. Kế toán tải lên, Chủ tịch ký; Chủ tịch — người ký duy nhất — không tự tải lên.
 3. CHƯA KÝ THÌ CHƯA CHỐT SỔ, và câu từ chối phải chỉ đúng việc còn thiếu.
 4. KÝ RỒI KHÔNG SỬA — bản mới ký thì bản cũ chuyển `da_thay_the` và vẫn đọc được.
 5. LUẬT CHỮ KÝ ĐỌC TỪ BẢNG `chu_ky.VAI_KY_CAN`, không viết tay trong dịch vụ.
 6. BỘ SỐ KHÔNG CÒN TRONG KHO MÃ, và không có đường nào đọc lại một tệp trong kho mã.
"""
import io
import os
import sys
import tempfile
from datetime import date

# MỘT TỆP PHÉP THỬ, MỘT CƠ SỞ DỮ LIỆU RIÊNG — đúng lệ của kho này (`tests/run_all.sh` chạy mỗi tệp
# một tiến trình). Đặt biến TRƯỚC khi nhập mô-đun ứng dụng: máy kết nối dựng đúng một lần lúc nhập.
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e16.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

import pytest                                                   # noqa: E402
from openpyxl import Workbook, load_workbook                     # noqa: E402
from sqlalchemy import select                                    # noqa: E402

from app.db.session import Base, SessionLocal, engine            # noqa: E402
from app.models.bo_so_kiem_toan import BoSoKiemToan              # noqa: E402
from app.models.core import User                                 # noqa: E402
from app.models.intake import IntakeRun                          # noqa: E402
from app.services import bo_so_kiem_toan as BS                   # noqa: E402
from app.services import chu_ky as CK                            # noqa: E402

Base.metadata.create_all(engine)

# Bộ số mẫu, TỰ CÂN ở cả hai cột: tài sản 25 tỷ = nguồn vốn 25 tỷ (cuối kỳ).
TK = [
    ("1111", "Tiền mặt", "", "", 3_000_000_000, 0, 2_000_000_000, 0),
    ("1121", "Tiền gửi ngân hàng", "", "", 5_000_000_000, 0, 5_000_000_000, 0),
    ("131", "Phải thu khách hàng", "", "", 10_000_000_000, 0, 10_000_000_000, 0),
    ("131", "", "KH_A", "Khách A", 6_000_000_000, 0, 6_000_000_000, 0),
    ("131", "", "KH_B", "Khách B", 4_000_000_000, 0, 4_000_000_000, 0),
    ("2111", "Tài sản cố định hữu hình", "", "", 8_000_000_000, 0, 8_000_000_000, 0),
    ("331", "Phải trả người bán", "", "", 0, 3_000_000_000, 0, 3_000_000_000),
    ("331", "", "NCC_X", "Nhà cung cấp X", 0, 3_000_000_000, 0, 3_000_000_000),
    ("411", "Vốn góp của chủ sở hữu", "", "", 0, 15_000_000_000, 0, 15_000_000_000),
    ("421", "LNST chưa phân phối", "", "", 0, 8_000_000_000, 0, 7_000_000_000),
]


def db_():
    return SessionLocal()


def _nguoi(db, ten: str, vai: str) -> User:
    u = db.execute(select(User).where(User.username == ten)).scalars().first()
    if not u:
        u = User(username=ten, full_name=ten, role=vai, password_hash="x")
        db.add(u)
        db.commit()
    return u


def tep(dong=None, tieu_de=None) -> bytes:
    """Một tệp Excel đúng mẫu. Tiêu đề lấy từ chính bảng `COT` của bộ đọc — không gõ lại."""
    wb = Workbook()
    ws = wb.active
    ws.append(tieu_de if tieu_de is not None else [nhan for _, nhan in BS.COT])
    for r in (dong if dong is not None else TK):
        ws.append(list(r))
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _tai_len(db, dong=None, ngay=date(2026, 6, 30), **kw):
    kt = _nguoi(db, "e16_ketoan", "ketoan")
    tham = {"ky": "H1/2026", "don_vi_kiem_toan": "Baker Tilly A&C", "so_bao_cao": "4.0299/26/TC-AC",
            "ngay_bao_cao": date(2026, 8, 28)}
    tham.update(kw)
    return BS.tai_len(db, kt, tep(dong), "bo_so.xlsx", ngay, **tham)


def _ky(db, b):
    return BS.ky(db, _nguoi(db, "e16_chutich", "chutich"), b)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. LUẬT CHỮ KÝ — khai MỘT chỗ, và dịch vụ đọc đúng chỗ ấy
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e16_1_luat_chu_ky_khai_trong_bang_chung():
    assert CK.can_ky(BS.LOAI_CHU_KY) == ("chutich",)


def test_e16_2_dich_vu_khong_viet_tay_ten_vai():
    """Đợt LG2 dựng MỘT bảng chữ ký vì luật viết rời ở sáu chỗ thì sửa một chỗ là sót năm chỗ.

    Phép thử này canh đúng điều ấy cho tệp mới: `bo_so_kiem_toan.py` được phép HỎI bảng luật,
    không được phép tự khai một tên vai. ĐÃ THỬ PHÁ: gõ "chutich" vào dịch vụ → tệp đỏ ngay.
    """
    import inspect
    nguon = inspect.getsource(BS)
    for vai in ("chutich", "ketoan_truong", "tgd"):
        assert f'"{vai}"' not in nguon and f"'{vai}'" not in nguon, (
            f"`bo_so_kiem_toan.py` viết tay tên vai {vai!r}. Luật chữ ký khai ở "
            f"`chu_ky.VAI_KY_CAN`; hỏi bảng ấy bằng `can_ky(LOAI_CHU_KY)`.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. BỐN PHÉP KIỂM, CHẠY TRƯỚC KHI GHI MỘT DÒNG NÀO
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e16_3_khong_can_thi_tra_tep():
    """K2 — bộ số là ĐÁP ÁN, nhận một bộ số không cân là viết một bảng cân đối không cân."""
    xau = [list(r) for r in TK]
    xau[-1][7] = 6_000_000_000            # 421 thiếu 1 tỷ ở cột cuối kỳ
    with pytest.raises(BS.SaiBoSo) as ex:
        BS.doc_excel(tep(xau))
    assert "K2" in str(ex.value) and "cuối kỳ" in str(ex.value)
    assert "1,000,000,000" in str(ex.value), "câu từ chối phải nói LỆCH BAO NHIÊU, không chỉ 'sai'"


def test_e16_4_dong_doi_tuong_cong_khong_khop_thi_tra_tep():
    """K3 — mã cũ TIN rằng tổng đối tượng bằng dòng tài khoản mà không kiểm (chú thích "target
    được tính sẵn bằng tổng các đối tượng" trong misa.py). Tin mà không kiểm thì lệch chui vào
    đúng chỗ ấy, và nó chui vào dưới dạng một bút toán KHÔNG CÂN — người đọc đi sửa nhầm chỗ."""
    xau = [list(r) for r in TK]
    xau[3][6] = 5_000_000_000             # KH_A còn 5 tỷ, dòng tổng 131 vẫn 10 tỷ
    with pytest.raises(BS.SaiBoSo) as ex:
        BS.doc_excel(tep(xau))
    assert "K3" in str(ex.value) and "131" in str(ex.value)


def test_e16_5_dong_doi_tuong_mo_coi_thi_tra_tep():
    """K1 — dòng đối tượng của một tài khoản không có dòng tổng là dòng không ai cộng vào đâu."""
    xau = [list(r) for r in TK] + [["136", "", "KH_C", "Khách C", 0, 0, 1_000_000_000, 0]]
    with pytest.raises(BS.SaiBoSo) as ex:
        BS.doc_excel(tep(xau))
    assert "K1" in str(ex.value) and "136" in str(ex.value)


def test_e16_6_o_tien_la_chu_va_ma_trung():
    """K4 — `float("1.234.567")` hỏng ồn ào, nhưng một ô chữ lọt qua thì nó hỏng IM LẶNG."""
    xau = [list(r) for r in TK]
    xau[0][6] = "hai tỷ"
    with pytest.raises(BS.SaiBoSo) as ex:
        BS.doc_excel(tep(xau))
    assert "hai tỷ" in str(ex.value) and "Dư Nợ cuối kỳ" in str(ex.value)

    trung = [list(r) for r in TK] + [["1111", "Tiền mặt (lần hai)", "", "", 0, 0, 0, 0]]
    with pytest.raises(BS.SaiBoSo) as ex2:
        BS.doc_excel(tep(trung))
    assert "1111" in str(ex2.value)


def test_e16_7_o_tien_de_trong_la_khong_co_du_ben_ay():
    """RỖNG ở bảng số dư nghĩa là tài khoản không có dư bên ấy — đó là cách người ta điền bảng cân
    đối, và bắt họ gõ số 0 vào 500 ô là đẩy người dùng sang một tệp khác."""
    co_o_trong = [list(r) for r in TK]
    for r in co_o_trong:
        for i in (4, 5, 6, 7):
            if r[i] == 0:
                r[i] = None
    dong = BS.doc_excel(tep(co_o_trong))
    assert len(dong) == len(TK)
    assert dong[0]["close_c"] == 0.0


def test_e16_8_tep_khong_dung_mau():
    with pytest.raises(BS.SaiBoSo) as ex:
        BS.doc_excel(tep(tieu_de=["Mã", "Tên", "Số tiền"]))
    assert "tiêu đề" in str(ex.value)


def test_e16_9_mau_excel_khong_co_mot_con_so_nao():
    """Mẫu có sẵn số là mẫu người ta sẽ sửa vài ô rồi tải lên — phần không sửa là số của robot đi
    thẳng vào bảng cân đối dưới chữ ký của người khác."""
    ws = load_workbook(io.BytesIO(BS.mau_excel())).worksheets[0]
    nhan = [nhan for _, nhan in BS.COT]
    tieu_de = [r for r in ws.iter_rows(values_only=True) if list(r)[:1] == [nhan[0]]]
    assert tieu_de and list(tieu_de[0]) == nhan, "mẫu phải có đúng dòng tiêu đề mà bộ đọc chờ"
    for r in ws.iter_rows(values_only=True):
        for o in r:
            assert not isinstance(o, (int, float)), f"mẫu KHÔNG được có sẵn con số nào: {o!r}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. HAI NGƯỜI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e16_10_khai_nguon_la_bat_buoc():
    db = db_()
    try:
        for thieu in ("don_vi_kiem_toan", "so_bao_cao", "ngay_bao_cao"):
            with pytest.raises(BS.SaiBoSo) as ex:
                _tai_len(db, **{thieu: "" if thieu != "ngay_bao_cao" else None})
            assert "Phải khai" in str(ex.value)
    finally:
        db.close()


def test_e16_11_chu_tich_khong_tu_tai_len():
    """Chủ tịch là người ký DUY NHẤT, nên ông tự tải lên là một hồ sơ KHÔNG AI KÝ ĐƯỢC. Cùng một
    phép chặn, cùng một câu, với `mo_lai_ky.de_nghi` (Đợt E6) và `propose_param` (Đợt LG2)."""
    db = db_()
    try:
        ct = _nguoi(db, "e16_chutich", "chutich")
        with pytest.raises(BS.SaiBoSo) as ex:
            BS.tai_len(db, ct, tep(), "x.xlsx", date(2026, 6, 30), "H1/2026",
                       "Baker Tilly A&C", "4.0299", date(2026, 8, 28))
        assert "không tự tải lên" in str(ex.value)
    finally:
        db.close()


def test_e16_12_nguoi_tai_len_khong_tu_ky():
    """Hôm nay không ai đi tới được nhánh này: người tải lên là Kế toán, người ký là Chủ tịch, và
    cửa ký đã chặn vai. Phép chặn vẫn đứng đây vì bảng luật `VAI_KY_CAN` ĐỔI ĐƯỢC — ngày ai đó
    thêm `ketoan_truong` vào dòng ký, nhánh này là thứ duy nhất còn chặn một người ký hồ sơ của
    chính mình."""
    db = db_()
    try:
        b = _tai_len(db)
        ct = _nguoi(db, "e16_chutich", "chutich")
        b.tai_len_boi = ct.username
        db.commit()
        with pytest.raises(BS.SaiBoSo) as ex:
            BS.ky(db, ct, b)
        assert "không tự ký" in str(ex.value)
    finally:
        db.close()


def test_e16_13_vai_khac_khong_ky_duoc():
    db = db_()
    try:
        b = _tai_len(db)
        with pytest.raises(BS.SaiBoSo) as ex:
            BS.ky(db, _nguoi(db, "e16_cntt", "cntt"), b)
        assert "ký bộ số kiểm toán được" in str(ex.value)
        assert db.get(BoSoKiemToan, b.id).trang_thai == "cho_ky"
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. CHƯA KÝ THÌ CHƯA CHỐT SỔ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e16_14_chua_ky_thi_ban_de_chot_nem_kem_viec_phai_lam():
    db = db_()
    try:
        b = _tai_len(db, ngay=date(2029, 12, 31))
        with pytest.raises(BS.SaiBoSo) as ex:
            BS.ban_de_chot(db, b.id)
        assert "chưa ký thì chưa chốt sổ" in str(ex.value)
    finally:
        db.close()


def test_e16_15_tu_choi_phai_co_ly_do_va_dong_ho_so():
    db = db_()
    try:
        b = _tai_len(db, ngay=date(2029, 11, 30))
        ct = _nguoi(db, "e16_chutich", "chutich")
        with pytest.raises(BS.SaiBoSo):
            BS.tu_choi(db, ct, b, "   ")
        BS.tu_choi(db, ct, b, "Số 131 chưa khớp thư xác nhận công nợ của ba khách lớn.")
        assert b.trang_thai == "tu_choi" and b.tu_choi_ly_do
        with pytest.raises(BS.SaiBoSo) as ex:
            BS.ky(db, ct, b)
        assert "không còn chờ ký" in str(ex.value)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. KÝ RỒI KHÔNG SỬA — TẢI BẢN MỚI, BẢN CŨ VẪN ĐỌC ĐƯỢC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e16_16_ban_moi_ky_thi_ban_cu_thanh_da_thay_the():
    db = db_()
    try:
        ngay = date(2028, 6, 30)
        cu = _tai_len(db, ngay=ngay)
        _ky(db, cu)
        assert cu.trang_thai == "da_ky"

        khac = [list(r) for r in TK]
        khac[0][6] = 1_000_000_000          # tiền mặt giảm 1 tỷ…
        khac[-1][7] = 6_000_000_000         # …và 421 giảm theo, để vẫn cân
        moi = _tai_len(db, dong=khac, ngay=ngay)
        _ky(db, moi)

        assert moi.trang_thai == "da_ky" and moi.thay_the_id == cu.id
        assert cu.trang_thai == "da_thay_the", "bản cũ phải đứng lại được — kiểm toán sẽ hỏi bản nào"
        assert cu.dong, "và các dòng của nó KHÔNG được xoá"
        assert BS.ban_da_ky(db, ngay).id == moi.id
    finally:
        db.close()


def test_e16_17_du_lieu_dung_hinh_dang_bo_chot_so_van_doc():
    """Hình dáng trả về phải khớp ĐÚNG tệp JSON cũ: `nguon`, `as_of`, `tai_khoan[]`, và
    `doi_tuong[]` cho tài khoản xét theo đối tượng. Giữ hình dáng là có chủ ý — phép tính của bộ
    chốt sổ không đổi một dòng nào ở đợt này, nên số có khác thì nguyên nhân nằm ở BỘ SỐ."""
    db = db_()
    try:
        b = _tai_len(db, ngay=date(2028, 3, 31))
        _ky(db, b)
        d = BS.du_lieu(b)
        assert d["as_of"] == date(2028, 3, 31)
        assert "Baker Tilly A&C" in d["nguon"] and "4.0299/26/TC-AC" in d["nguon"]
        ma = {a["code"]: a for a in d["tai_khoan"]}
        assert set(ma) == {r[0] for r in TK}, "mỗi tài khoản đúng MỘT mục, dòng đối tượng nằm trong"
        assert ma["1111"]["close_d"] == 2_000_000_000
        assert [o["ma"] for o in ma["131"]["doi_tuong"]] == ["KH_A", "KH_B"]
        assert "doi_tuong" not in ma["1111"]
        assert sum(o["close_d"] for o in ma["131"]["doi_tuong"]) == ma["131"]["close_d"]
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. BỘ SỐ KHÔNG CÒN TRONG KHO MÃ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def test_e16_18_khong_con_tep_so_lieu_nao_trong_kho_ma():
    """Đây là phép thử ĐẮT NHẤT của tệp này: nó canh chính cái ranh giới 09/9/2026.

    Thêm lại một tệp số liệu vào `app/data` và đọc nó ra là quay về đúng chỗ cũ — ba mươi con số
    đi vào bảng cân đối mà không ai ký.
    """
    import inspect
    import pathlib

    from app.services import misa as MISA
    nguon = inspect.getsource(MISA)
    assert "KIEM_TOAN_FILE" not in nguon, (
        "`misa.py` còn đọc một tệp bộ số trong kho mã. Bộ số phải đến từ `bo_so_kiem_toan` — "
        "người tải lên, người ký.")
    assert "BSKT.ban_de_chot" in nguon

    goc = pathlib.Path(MISA.__file__).resolve().parent.parent / "data"
    con = sorted(p.name for p in goc.glob("kiem_toan*.json")) if goc.exists() else []
    assert not con, f"còn tệp bộ số kiểm toán trong kho mã: {con}"


def test_e16_19_ghi_nhat_ky_lo():
    """Cửa nạp nào không để lại một dòng sổ thì bộ đối chiếu lô K5 không nhìn thấy nó (09/9/2026:
    sổ có đúng một dòng trong khi 25.728 bút toán đã vào qua bộ nạp MISA)."""
    from app.services import ks_nap_lo as NL
    assert any(c == "bo_so_kiem_toan.tai_len" for c, _, ghi, _ in NL.CUA_NAP if ghi), (
        "cửa nạp này phải khai trong `ks_nap_lo.CUA_NAP` là CÓ ghi nhật ký lô")
    db = db_()
    try:
        _tai_len(db, ngay=date(2027, 6, 30))
        lo = db.execute(select(IntakeRun).where(IntakeRun.loai == "bo_so_kiem_toan")).scalars().all()
        assert lo, "tải lên một bộ số mà nhật ký lô không có dòng nào"
        assert lo[-1].so_dong == len(TK)
    finally:
        db.close()


def test_e16_20_khai_cua_nhap_va_pham_vi_phap_nhan():
    """Ranh giới 09/9/2026: bảng nào cũng phải có một cửa cho người dùng, và bảng nào mang cột
    pháp nhân cũng phải khai nó được lọc hay không."""
    from app.services import ks_cua_nhap as KCN
    from app.services import pham_vi_phap_nhan as PV
    for b in ("bo_so_kiem_toan", "bo_so_kiem_toan_dong"):
        assert b in KCN.CUA_TAY, f"bảng `{b}` chưa khai cửa nhập"
    assert "BoSoKiemToan" in PV.PHAI_LOC
    assert "BoSoKiemToan" not in PV.mo_hinh_thieu_loc(), (
        "khai PHẢI LỌC mà không nơi nào gọi `PV.loc` cho nó là một lời hứa chưa thực hiện")
