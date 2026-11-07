# -*- coding: utf-8 -*-
"""Đợt CPTT-2 07/11/2026 — CỘT «TK CHI PHÍ» TRONG MẪU EXCEL NẠP CCDC.

Đợt CPTT-1 (PR #709) bắt buộc chọn TK chi phí ở cửa NHẬP TAY. Nhưng đường nạp HÀNG LOẠT
(`intake_phong_ban_2._cc_nap`) tạo thẳng `PrepaidExpense`, KHÔNG đi qua `create_prepaid`, nên
vẫn rơi vào mặc định của MÔ HÌNH là `6423` — lỗ còn lại, và chính Đợt CPTT-1 đã nói ra nó.

Chủ tịch chốt 07/11/2026: bắt buộc NGAY ở cả hai đường, và thêm luôn cột mã công trình.

BỐN LUẬT:
  1. Mẫu Excel có đủ hai cột mới, và `tk_chi_phi` là cột BẮT BUỘC.
  2. MỘT BỘ LUẬT, HAI ĐƯỜNG NHẬP: cả hai gọi chung `assets.kiem_tk_chi_phi`.
  3. Cửa kiểm từ chối đúng từng loại sai, và nói rõ sai gì.
  4. Dòng nạp hợp lệ ĐI VÀO bản ghi — cả TK chi phí lẫn mã công trình.
"""
import inspect
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_cptt2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.exists("test_cptt2.db"):
    os.remove("test_cptt2.db")

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _mau():
    """Mẫu nạp CCDC, lấy từ `intake.BO_NAP` — tức qua ĐÚNG đường mà cửa tải tệp đọc.

    Không gọi thẳng `intake_phong_ban_2.bo_nap(_c)`: bộ nạp được ghép từ nhiều mô-đun vào
    `BO_NAP`, và đo ở bản ghép mới biết mẫu này có thật sự tới được cửa hay không.
    """
    from app.services.intake import BO_NAP
    assert "cong_cu_dung_cu" in BO_NAP, (
        "không thấy mẫu `cong_cu_dung_cu` trong bộ nạp — DỪNG LẠI, main đã đổi")
    return BO_NAP["cong_cu_dung_cu"]


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _dong(**o):
    goc = {"ma_ccdc": "CPTT2-A", "ten": "Bảo hiểm xe 12 tháng", "loai": "cp_tra_truoc",
           "bo_phan": "doi_xe", "tk_chi_phi": "627", "ngay_bat_dau_pb": "01/08/2026",
           "gia_tri": 48_000_000, "so_ky_pb": 12}
    return {**goc, **o}


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_cptt2_1_mau_excel_co_du_hai_cot_moi_va_tk_chi_phi_la_BAT_BUOC():
    """Mẫu thiếu cột thì người nạp không có chỗ ghi, và cửa kiểm đòi một thứ không ai điền được.

    `_c()` khai MỘT LẦN cho cả ba cửa (nhập tay, tải tệp, ảnh do AI đọc) — nên thiếu ở đây là
    thiếu ở cả ba.
    """
    cot = {c["key"]: c for c in _mau()["cot"]}
    assert "tk_chi_phi" in cot, (
        "mẫu Excel nạp CCDC không có cột `tk_chi_phi` — đường nạp hàng loạt vẫn đẻ ra khoản "
        "phân bổ vào 6423 mà không ai chọn")
    assert cot["tk_chi_phi"]["bat_buoc"] is True, (
        "cột `tk_chi_phi` không bắt buộc — để trống thì lại rơi vào mặc định, đúng thứ đợt này "
        "bịt (Chủ tịch chốt 07/11/2026: bắt buộc ngay)")
    assert "ma_cong_trinh" in cot, "mẫu thiếu cột `ma_cong_trinh`"
    assert cot["ma_cong_trinh"]["bat_buoc"] is False, (
        "`ma_cong_trinh` phải ĐỂ TRỐNG ĐƯỢC — không phải khoản nào cũng thuộc một chuyến")
    # Ví dụ trong mẫu phải là một tài khoản THẬT, không thì người nạp chép theo rồi bị từ chối.
    from app.services import assets as AS
    with _db() as db:
        assert AS.kiem_tk_chi_phi(db, cot["tk_chi_phi"]["vi_du"]) == "", (
            "ví dụ trong mẫu không qua được chính cửa kiểm: " + repr(cot["tk_chi_phi"]["vi_du"]))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_cptt2_2_MOT_bo_luat_HAI_duong_nhap_deu_goi_chung_mot_ham():
    """Chép luật ra hai chỗ thì sớm muộn hai chỗ lệch nhau.

    Và lúc ấy một khoản nạp qua Excel được nhận trong khi cùng khoản ấy nhập tay bị từ chối —
    không ai hiểu nổi vì sao. Nên luật này đo rằng CẢ HAI đường đều gọi chung một hàm, và rằng
    `create_prepaid` KHÔNG còn giữ bản sao của bộ luật.
    """
    from app.services import assets as AS
    from app.services import intake_phong_ban_2 as IN
    assert hasattr(AS, "kiem_tk_chi_phi"), "chưa rút bộ luật ra thành một hàm dùng chung"

    tao = inspect.getsource(AS.create_prepaid)
    assert "kiem_tk_chi_phi" in tao, "cửa nhập tay không gọi hàm chung"
    tao_ma = "\n".join(d.split("#")[0] for d in tao.split("\n"))
    assert "là tài khoản tổng hợp" not in tao_ma, (
        "`create_prepaid` còn giữ BẢN SAO của bộ luật — rút ra hàm chung rồi thì chỗ cũ phải đi, "
        "không thì hai chỗ cùng nói một luật")

    kiem = inspect.getsource(IN._cc_kiem)
    assert "kiem_tk_chi_phi" in kiem, "cửa nạp Excel không gọi hàm chung"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_cptt2_3_cua_kiem_tu_choi_dung_tung_loai_sai_va_noi_ro_sai_gi():
    """Bốn cảnh, và cả bốn phải nói ra ĐIỀU KHÁC NHAU.

    Một câu từ chối chung chung («dòng 7 không hợp lệ») buộc người nạp phải đoán, và họ sẽ sửa
    nhầm cột khác.
    """
    from app.services import intake_phong_ban_2 as IN
    with _db() as db:
        ok, _, _ = IN._cc_kiem(db, _dong())
        assert not ok, "dòng hợp lệ mà vẫn bị từ chối: " + repr(ok)

        thieu, _, _ = IN._cc_kiem(db, _dong(tk_chi_phi=""))
        assert any("Chưa chọn TK chi phí" in x for x in thieu), (
            "để trống TK chi phí mà cửa kiểm không nói gì: " + repr(thieu))

        cha, _, _ = IN._cc_kiem(db, _dong(tk_chi_phi="642"))
        assert any("tổng hợp" in x and "642" in x for x in cha), (
            "`642` là tài khoản cha mà cửa kiểm vẫn nhận: " + repr(cha))

        ngoai, _, _ = IN._cc_kiem(db, _dong(tk_chi_phi="6323"))
        assert any("nhóm nhận phân bổ" in x for x in ngoai), (
            "`6323` là giá vốn, không nằm trong nhóm MISA liệt kê làm đích phân bổ — chi phí sẽ "
            "bị tính hai lần qua 627 → 154 → 632. Cửa kiểm nhận nó: " + repr(ngoai))

        bia, _, _ = IN._cc_kiem(db, _dong(tk_chi_phi="9999"))
        assert any("không có trong danh mục" in x for x in bia), (
            "tài khoản không có thật mà cửa kiểm vẫn nhận: " + repr(bia))


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_cptt2_4_dong_nap_hop_le_DI_VAO_ban_ghi():
    """Cột có trong mẫu và qua được cửa kiểm thì chưa đủ — nó phải ĐI VÀO bản ghi.

    Đây đúng chỗ Đợt CPTT-1 phát hiện ở màn hình: ô có trên form mà không gửi lên máy chủ thì
    bằng không có ô. Ở đường Excel, cột có trong mẫu mà `_cc_nap` không đọc thì cũng vậy.
    """
    from sqlalchemy import select
    from app.models.assets import PrepaidExpense
    from app.services import intake_phong_ban_2 as IN
    with _db() as db:
        IN._cc_nap(db, _dong(ma_ccdc="CPTT2-NAP", tk_chi_phi="6422",
                             ma_cong_trinh="CPTT2TOUR"), "test")
        db.commit()
        p = db.execute(select(PrepaidExpense).where(
            PrepaidExpense.code == "CPTT2-NAP")).scalars().first()
        assert p is not None, "không nạp được dòng hợp lệ"
        assert p.expense_account == "6422", (
            "TK chi phí không vào bản ghi, nhận " + repr(p.expense_account) +
            " — cột có trong mẫu mà `_cc_nap` không đọc thì bằng không có cột")
        assert p.project_code == "CPTT2TOUR", (
            "mã công trình không vào bản ghi, nhận " + repr(p.project_code))
        # Và KHÔNG rơi vào mặc định cũ của mô hình.
        assert p.expense_account != "6423", "vẫn rơi vào mặc định 6423"
