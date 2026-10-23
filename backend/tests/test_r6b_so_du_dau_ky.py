# -*- coding: utf-8 -*-
"""ĐỢT R6b-1 — SỐ DƯ ĐẦU KỲ. Giữ ba luật Chủ tịch chốt ngày 23/10/2026.

  1. TỔNG SỔ PHỤ = CỬA CHỐT.
  2. DÒNG THIẾU MÃ ĐỐI TƯỢNG KHÔNG VÀO TỔNG.
  3. DÒNG THIẾU MÃ KHÔNG BỊ XOÁ.

Luật 2 và 3 phải đi CÙNG NHAU trong một phép thử chạy thật, không phải hai phép thử đọc mã.
Lý do: mỗi luật một mình đều dễ làm đúng và dễ làm đúng theo cách phá luật kia. Bỏ dòng thiếu mã
khỏi tổng bằng cách XOÁ nó đi thì phép thử luật 2 xanh. Giữ nó lại rồi CỘNG vào tổng thì phép thử
luật 3 xanh. Chỉ khi hai điều kiện đo trên cùng một sổ thì không còn đường nào đi tắt.
"""
import os
import re
import sys
from datetime import date

import pytest

_DB = os.path.join(os.path.dirname(__file__), "r6b.sqlite")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import Numeric, create_engine, func, select       # noqa: E402
from sqlalchemy.orm import sessionmaker                          # noqa: E402

from app.db.session import Base                                  # noqa: E402
from app.models.accounting import Account                        # noqa: E402
from app.models.so_du_dau_ky import (SoDuDauKy, SoDuDauKyKhachHang,   # noqa: E402
                                     SoDuDauKyNhaCungCap, SoDuDauKyTaiSan)
from app.services import accounting as ACC                       # noqa: E402
from app.services import ks_cua_nhap as KCN                      # noqa: E402
from app.services import so_du_dau_ky as SD                      # noqa: E402
from app.services import intake_so_du_dau_ky as CN               # noqa: E402
from app.services.intake import BO_NAP, VAI_TRO, VAI_TRO_NAP_TEP  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KY = "2026-01"
TAM_BANG = ("so_du_dau_ky",) + tuple(f"so_du_dau_ky_{s['ma']}" for s in SD.SO_PHU)


def _ma(duong):
    with open(os.path.join(GOC, *duong.split("/")), encoding="utf-8") as f:
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
    # Cờ của Đợt E1: bộ đối chiếu ĐỌC cờ này để biết tài khoản nào bắt buộc có sổ phụ. Bật tay
    # ở đây chứ không sửa bộ seed — đợt này không đi đổi danh mục tài khoản của ai.
    for tk in ("131", "331", "1121", "141", "211", "242"):
        a = db.get(Account, tk)
        if a:
            a.td_doi_tuong = True
    a154 = db.get(Account, "154")
    if a154:
        a154.td_cong_trinh = True
    db.flush()
    return db


def _tk_chi_tiet(db, dau: str) -> str:
    """TK chi tiết đầu tiên bắt đầu bằng `dau` — KHÔNG gõ cứng "211" vào phép thử.

    Bản đầu gõ cứng và đỏ ngay: 211 là tài khoản TỔNG HỢP (có 2111, 2112…), mà cửa nạp từ chối
    tài khoản tổng hợp — đúng luật, vì số dư của nó là tổng của các con, nhập cả hai là cộng hai
    lần. Gõ cứng một mã là buộc phép thử biết trước danh mục tài khoản trông ra sao; hỏi danh
    mục thì nó đúng cả khi danh mục đổi.
    """
    a = db.get(Account, dau)
    if a is not None and a.is_detail:
        return dau
    con = [x for x in db.execute(select(Account)).scalars()
           if x.code.startswith(dau) and x.code != dau and x.is_detail]
    assert con, f"Danh mục không có tài khoản chi tiết nào dưới {dau}"
    return sorted(con, key=lambda x: x.code)[0].code


def _chot(db, tk, no=0.0, co=0.0):
    db.add(SoDuDauKy(ky=KY, tk=tk, du_no=no, du_co=co, ghi_boi="phep_thu"))
    db.flush()


def _ncc(db, tk, ma, no=0.0, co=0.0):
    db.add(SoDuDauKyNhaCungCap(ky=KY, tk=tk, ma_doi_tuong=ma, ten=f"NCC {ma}",
                               du_no=no, du_co=co, ghi_boi="phep_thu"))
    db.flush()


def _kh(db, tk, ma, no=0.0, co=0.0):
    db.add(SoDuDauKyKhachHang(ky=KY, tk=tk, ma_doi_tuong=ma, ten=f"KH {ma or 'chưa có mã'}",
                              du_no=no, du_co=co, ghi_boi="phep_thu"))
    db.flush()


# ──────────────────────────────────────────────────────────────────────────────────────────────
# LUẬT 0 — tám bảng phải CÓ MẶT và phải CÓ CỬA
# ──────────────────────────────────────────────────────────────────────────────────────────────

def test_r6b_1_tam_bang_deu_trong_mo_hinh():
    """Thiếu dòng nhập ở models/__init__.py thì bảng không vào Base.metadata: create_all không
    tạo, mọi phép thử soi metadata mù đúng phần này mà VẪN BÁO XANH, và alembic autogenerate
    đòi XOÁ bảng. Lần thứ mười bốn cùng một chuyện ở kho này."""
    thieu = [b for b in TAM_BANG if b not in Base.metadata.tables]
    assert not thieu, f"Tám bảng số dư đầu kỳ: {thieu} không nằm trong Base.metadata"


def test_r6b_2_tam_bang_deu_co_cua_nhap():
    """Ranh giới 09/9/2026: mỗi con số cần một cửa. Bảng mới mà không cửa là VIỆC CÒN THIẾU."""
    b = KCN.bang()
    khong = [t for t in TAM_BANG if t in b["khong_cua"]]
    assert not khong, (f"{khong} không có cửa nào — không bộ nạp, không màn hình nhập tay, "
                       f"không khai máy sinh")
    tep = KCN.cua_tai_tep()
    thieu = [t for t in TAM_BANG if t not in tep]
    assert not thieu, f"{thieu} không đọc được cửa TẢI TỆP từ sổ bộ nạp sống"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# LUẬT 1 — TỔNG SỔ PHỤ = CỬA CHỐT
# ──────────────────────────────────────────────────────────────────────────────────────────────

def test_r6b_3_tong_so_phu_bang_cua_chot():
    db = _rieng()
    _chot(db, "131", no=100_000_000)
    _kh(db, "131", "KH001", no=60_000_000)
    _kh(db, "131", "KH002", no=40_000_000)
    kq = SD.doi_chieu(db, KY)
    dong = [d for d in kq["dong"] if d["tk"] == "131" and d["so"] == "khach_hang"]
    assert len(dong) == 1, "Một tài khoản một sổ phụ phải ra ĐÚNG MỘT dòng đối chiếu"
    assert dong[0]["phu_no"] == pytest.approx(100_000_000)
    assert dong[0]["lech_no"] == pytest.approx(0)
    assert dong[0]["khop"] is True
    assert kq["khop"] is True, f"Khớp hết mà vẫn báo lệch: {kq['lech']} · {kq['chua_co_so_phu']}"


def test_r6b_4_lech_thi_noi_to_va_khong_tu_sua():
    """Lệch là một câu hỏi về số liệu. Phần mềm làm cho nó hiện ra, không làm cho nó mất đi."""
    db = _rieng()
    _chot(db, "331", co=41_117_900_000)
    _ncc(db, "331", "NCC001", co=40_869_300_000)
    kq = SD.doi_chieu(db, KY)
    assert kq["khop"] is False
    # Không bên nào bị sửa cho khớp
    assert db.get(SoDuDauKy, (KY, "331")).du_co == pytest.approx(41_117_900_000)
    assert db.execute(select(func.sum(SoDuDauKyNhaCungCap.du_co))
                      .where(SoDuDauKyNhaCungCap.tk == "331")).scalar() == pytest.approx(40_869_300_000)


# ──────────────────────────────────────────────────────────────────────────────────────────────
# LUẬT 2 + 3 — HAI LUẬT, MỘT SỔ. Xem ghi chú đầu tệp về vì sao không tách ra hai phép thử.
# ──────────────────────────────────────────────────────────────────────────────────────────────

def test_r6b_5_dong_thieu_ma_khong_vao_tong_va_khong_bi_xoa():
    db = _rieng()
    # Cửa chốt mang CẢ phần chưa gán mã: đúng hình thật — Kế toán nhập tổng tài khoản từ bảng
    # cân đối, rồi mới ngồi tách ra từng khách.
    _chot(db, "131", no=125_000_000)
    _kh(db, "131", "KH001", no=60_000_000)
    _kh(db, "131", "KH002", no=40_000_000)
    _kh(db, "131", "", no=15_000_000)        # chưa gán mã
    _kh(db, "131", "   ", no=10_000_000)     # chỉ có dấu cách — vẫn là CHƯA GÁN MÃ

    kq = SD.doi_chieu(db, KY)
    d = [x for x in kq["dong"] if x["tk"] == "131" and x["so"] == "khach_hang"][0]

    # LUẬT 2 — không vào tổng
    assert d["phu_no"] == pytest.approx(100_000_000), \
        "Dòng thiếu mã đối tượng đã bị cộng vào tổng đối chiếu"
    assert d["lech_no"] == pytest.approx(25_000_000)
    # Và số lệch BẰNG ĐÚNG tiền của các dòng thiếu mã — để người đọc thấy ngay việc phải làm là
    # gán mã, không phải đi tìm một con số sai.
    assert d["tien_thieu_ma"] == pytest.approx(d["lech_no"])
    assert d["so_dong_thieu_ma"] == 2, "Ô chỉ có dấu cách phải tính là CHƯA GÁN MÃ"
    assert kq["khop"] is False

    # LUẬT 3 — không bị xoá
    con = db.execute(select(func.count()).select_from(SoDuDauKyKhachHang)
                     .where(SoDuDauKyKhachHang.tk == "131")).scalar()
    assert con == 4, f"Sổ phụ phải còn đủ 4 dòng sau khi đối chiếu, đang còn {con}"
    tong_that = db.execute(select(func.sum(SoDuDauKyKhachHang.du_no))
                           .where(SoDuDauKyKhachHang.tk == "131")).scalar()
    assert float(tong_that) == pytest.approx(125_000_000), \
        "Tiền của dòng thiếu mã phải còn trong SỔ — chỉ không có trong TỔNG"

    # Và lời nhắc phải nói cả hai nửa, không chỉ nửa đầu
    loi_nhac = " ".join(kq["canh_bao"])
    assert "KHÔNG được cộng vào tổng" in loi_nhac
    assert "KHÔNG bị bỏ đi" in loi_nhac


def test_r6b_6_gan_ma_thi_phan_ay_vao_tong_ngay():
    """Nửa sau của luật 2: dòng thiếu mã không bị loại VĨNH VIỄN, nó chỉ đang chờ."""
    db = _rieng()
    _chot(db, "131", no=125_000_000)
    _kh(db, "131", "KH001", no=100_000_000)
    _kh(db, "131", "", no=25_000_000)
    assert SD.doi_chieu(db, KY)["khop"] is False
    o = db.execute(select(SoDuDauKyKhachHang)
                   .where(SoDuDauKyKhachHang.ma_doi_tuong == "")).scalars().first()
    o.ma_doi_tuong = "KH002"
    db.flush()
    kq = SD.doi_chieu(db, KY)
    assert kq["khop"] is True, f"Gán mã rồi mà vẫn lệch: {kq['lech']}"
    assert kq["so_dong_thieu_ma"] == 0


# ──────────────────────────────────────────────────────────────────────────────────────────────
# CỬA NẠP — phải CÓ ô mã đối tượng, và phải KHÔNG chặn dòng thiếu mã
# ──────────────────────────────────────────────────────────────────────────────────────────────

def test_r6b_7_moi_cua_so_phu_deu_co_o_ma_doi_tuong():
    for s in SD.SO_PHU:
        bo = BO_NAP[f"so_du_dau_ky_{s['ma']}"]
        khoa = {c["key"] for c in bo["cot"]}
        assert "ma_doi_tuong" in khoa, f"Cửa sổ phụ {s['ma']} không có ô mã đối tượng"
        assert "ky" in khoa and "tk" in khoa, f"Cửa sổ phụ {s['ma']} thiếu ô kỳ gốc hoặc tài khoản"
        o = [c for c in bo["cot"] if c["key"] == "ma_doi_tuong"][0]
        assert "BẮT BUỘC" in o["ghi_chu"], \
            f"Ô mã đối tượng của {s['ma']} không nói với người nhập rằng nó bắt buộc"


def test_r6b_7b_ky_goc_dung_mot_dinh_dang_cua_ca_he():
    """`kieu="thang"` của services/nhap_lieu.py là nguồn DUY NHẤT nói kỳ viết dạng nào. Khai kiểu
    'chu' rồi tự kiểm trong cửa là dựng nguồn thứ hai cho cùng một định dạng — và lúc hai nguồn
    lệch thì một tệp nạp được ở cửa này, bị từ chối ở cửa kia, cùng một con số."""
    for b in TAM_BANG:
        o = [c for c in BO_NAP[b]["cot"] if c["key"] == "ky"][0]
        assert o["kieu"] == "thang", f"Cửa {b}: ô kỳ gốc khai kiểu '{o['kieu']}', phải là 'thang'"
        assert o["bat_buoc"] is True


def test_r6b_8_cua_nap_canh_bao_chu_khong_chan_dong_thieu_ma():
    """Chặn ở cửa là đánh đổi sai: người nhập phải sửa tệp NGOÀI hệ thống, và lần sửa ấy không
    ai ghi lại. Xem đầu services/intake_so_du_dau_ky.py."""
    db = _rieng()
    for s in SD.SO_PHU:
        kiem = BO_NAP[f"so_du_dau_ky_{s['ma']}"]["kiem"]
        tk = _tk_chi_tiet(db, {"ngan_hang": "1121", "khach_hang": "131", "nha_cung_cap": "331",
                               "nhan_vien": "141", "tai_san": "211", "tra_truoc": "242",
                               "do_dang": "154"}[s["ma"]])
        loi, cb, khoa = kiem(db, {"ky": "2026-01", "tk": tk, "ma_doi_tuong": ""})
        assert not loi, f"Cửa {s['ma']} (TK {tk}) CHẶN dòng thiếu mã đối tượng: {loi}"
        assert any("KHÔNG cộng vào tổng" in c for c in cb), \
            f"Cửa {s['ma']} nhận dòng thiếu mã mà không nói hậu quả cho người nhập"
        assert khoa is None, "Dòng chưa có mã không được mang khoá chống trùng"
        loi2, _, khoa2 = kiem(db, {"ky": "2026-01", "tk": tk, "ma_doi_tuong": "X1"})
        assert not loi2 and khoa2, f"Cửa {s['ma']} (TK {tk}) từ chối một dòng đủ mã: {loi2}"


def test_r6b_8b_cua_nap_tu_choi_tai_khoan_TONG_HOP():
    """Chiều ngược của phép thử trên — và là lý do nó từng đỏ.

    Số dư của tài khoản tổng hợp là TỔNG của các tài khoản con. Nhận cả hai là cộng hai lần, mà
    sổ vẫn cân nên không phép kiểm số học nào bắt được. Cửa phải chặn ở đây, không ở đâu khác.
    """
    db = _rieng()
    tong = [a.code for a in db.execute(select(Account)).scalars() if not a.is_detail]
    assert tong, "Danh mục không có tài khoản tổng hợp nào — kiểm lại bộ seed"
    kiem = BO_NAP["so_du_dau_ky"]["kiem"]
    loi, _, _ = kiem(db, {"ky": "2026-01", "tk": sorted(tong)[0], "du_no": "1000"})
    assert any("TỔNG HỢP" in x for x in loi), \
        f"Cửa chốt nhận một tài khoản tổng hợp ({sorted(tong)[0]}): {loi}"


def test_r6b_9_cua_chot_chi_mo_cho_ke_toan():
    """HÀNG RÀO QUYỀN. Số dư đầu kỳ là con số nền của toàn sổ: một dòng sai ở đây đi theo mọi kỳ
    về sau, và không phép kiểm kỳ nào bắt được vì sổ vẫn cân.

    ĐÚNG MỘT VAI NGHIỆP VỤ — Kế toán. Chủ tịch chốt 23/10/2026 bằng đúng hai chữ "kế toán tải",
    và Kế toán trưởng CỐ Ý không có ở đây: ba vai của Đợt E2b có một bảng ký riêng
    (`test_le2b_ba_vai_ke_toan::test_f1_dot_nay_chi_mo_dung_nhung_cho_da_khai`), nên thêm một
    vai vào cửa này là đòi một chữ ký mới cho một câu Chủ tịch không nói. Kế toán trưởng vẫn
    THẤY màn hình — suy từ `ketoan` theo Đợt LG1 — chỉ không phải người nạp tệp, đúng hình với
    `/ket-so`."""
    cho_phep = {"chutich", "tgd", "cntt", "ketoan"}
    for b in TAM_BANG:
        assert set(VAI_TRO[b]) == cho_phep, f"Cửa {b} mở cho vai ngoài danh sách đã ký: {VAI_TRO[b]}"
        assert set(VAI_TRO_NAP_TEP[b]) == cho_phep, f"Cửa TẢI TỆP {b}: {VAI_TRO_NAP_TEP[b]}"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# MỘT NGUỒN CHO "CỘT NÀO LÀ CỘT CỘNG"
# ──────────────────────────────────────────────────────────────────────────────────────────────

def test_r6b_10_cot_cong_cua_moi_so_phu_la_cot_that():
    """`SO_PHU` là nguồn DUY NHẤT nói cột nào của sổ phụ cộng về cửa chốt. Cửa nạp đọc nó, bộ
    đối chiếu đọc nó. Khai sai một tên cột ở đây thì tổng im lặng ra 0 — không lỗi, không đỏ."""
    for s in SD.SO_PHU:
        for ten in (s["cot_no"], s["cot_co"]):
            if ten:
                assert hasattr(s["lop"], ten), \
                    f"Sổ phụ {s['ma']} khai cột cộng '{ten}' mà bảng {s['lop'].__tablename__} không có"
    # Tài sản cộng về cửa chốt bằng NGUYÊN GIÁ, không phải giá trị còn lại: cửa chốt TK 211 là
    # nguyên giá, khấu hao lũy kế là cửa chốt TK 214. Lấy giá trị còn lại thì lệch đúng bằng
    # khấu hao — một con số trông hợp lý, nên không ai tra lại.
    assert SD.SO_PHU_THEO_MA["tai_san"]["cot_no"] == "nguyen_gia"
    assert hasattr(SoDuDauKyTaiSan, "khau_hao_luy_ke")


def test_r6b_11_bo_doi_chieu_khong_ghi_mot_dong_nao():
    """Ranh giới 09/9/2026: bộ đối chiếu ĐỌC và trả lời. Nó không nhập hộ, không sửa, không xoá."""
    ma = _ma("app/services/so_du_dau_ky.py")
    # Bỏ chú thích trước khi soi: tệp này nói nhiều về chuyện KHÔNG xoá, và chữ 'xoá' trong một
    # dòng giải thích không phải một câu lệnh xoá.
    than = "\n".join(d for d in ma.splitlines() if not d.lstrip().startswith("#"))
    for cam in (r"\bdb\.add\(", r"\bdb\.delete\(", r"\bdb\.commit\(", r"\bdb\.merge\("):
        assert not re.search(cam, than), f"services/so_du_dau_ky.py có {cam} — bộ đối chiếu phải chỉ ĐỌC"


def test_r6b_12_khong_cua_nao_tu_bu_tru_hai_chieu():
    """Dư Nợ và dư Có đi hai cột. Bù trừ thành một số là xoá mất đúng cái mà phép kiểm số dư
    ngược chiều (Đợt R2-KC1) đi tìm."""
    db = _rieng()
    kiem = BO_NAP["so_du_dau_ky"]["kiem"]
    nap = BO_NAP["so_du_dau_ky"]["nap"]
    r = {"ky": "2026-01", "tk": "131", "du_no": "5000000", "du_co": "3000000"}
    loi, cb, _ = kiem(db, r)
    assert not loi, f"Cửa chốt chặn một tài khoản lưỡng tính: {loi}"
    assert any("lưỡng tính" in c for c in cb)
    o, _tt = nap(db, r, "phep_thu")
    assert o.du_no == pytest.approx(5_000_000) and o.du_co == pytest.approx(3_000_000), \
        "Cửa nạp đã bù trừ hai chiều thành một số"


# ──────────────────────────────────────────────────────────────────────────────────────────────
# QUY TẮC 4 — Ô TRỐNG LÀ CHƯA CÓ SỐ, KHÔNG PHẢI SỐ 0
# ──────────────────────────────────────────────────────────────────────────────────────────────

def test_r6b_13_khong_cot_tien_nao_vua_mac_dinh_0_vua_khong_cho_rong():
    """Luật của Đợt K2, và `test_kt12` bắt được đúng hai cột của bản đầu tệp này.

    Một cột tiền vừa có mặc định 0 vừa NOT NULL thì "chưa nhập" và "bằng 0" là MỘT, không phân
    biệt được. Soi THẲNG siêu dữ liệu của tám bảng chứ không đọc mã: khai một cột mới ở tháng
    sau mà quên luật này thì phép thử đỏ ngay, kèm tên cột.
    """
    xau = []
    for ten in TAM_BANG:
        for c in Base.metadata.tables[ten].columns:
            if not isinstance(c.type, Numeric):
                continue
            if not c.nullable or c.default is not None or c.server_default is not None:
                xau.append(f"{ten}.{c.name}")
    assert not xau, ("Cột tiền phải CHO RỖNG và KHÔNG có mặc định — ô trống là CHƯA CÓ SỐ: "
                     + ", ".join(xau))


def test_r6b_14_cua_nap_de_o_trong_la_RONG_chu_khong_ghi_0():
    """Đo trên đường nạp THẬT. Bảng khai đúng mà hàm nạp vẫn ghi 0 thì luật chỉ nằm trên giấy."""
    db = _rieng()
    nap = BO_NAP["so_du_dau_ky_tai_san"]["nap"]
    o, _ = nap(db, {"ky": KY, "tk": "211", "ma_doi_tuong": "TS001", "ten": "Xe 51A",
                    "nguyen_gia": "1200000000"}, "phep_thu")
    assert o.nguyen_gia == pytest.approx(1_200_000_000)
    assert o.khau_hao_luy_ke is None, (
        "Ô khấu hao để trống bị ghi thành 0 — 'chưa ai khai' và 'chưa trích đồng nào' thành một")
    assert o.so_ky_con is None
    # Và gõ số 0 vào thì PHẢI ra 0 thật, không ra rỗng: hai câu khác nhau, hai kết quả khác nhau.
    o2, _ = nap(db, {"ky": KY, "tk": "211", "ma_doi_tuong": "TS002", "ten": "Máy in",
                     "nguyen_gia": "5000000", "khau_hao_luy_ke": "0"}, "phep_thu")
    assert o2.khau_hao_luy_ke == pytest.approx(0)
