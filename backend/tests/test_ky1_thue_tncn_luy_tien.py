# -*- coding: utf-8 -*-
"""KY-1 · Thuế TNCN lũy tiến từng phần: phép tính dựng xong, công tắc để trống.

CĂN CỨ TRA NGÀY 08/10/2026, trước khi viết dòng mã nào:
  · Luật Thuế TNCN 2025 số 109/2025/QH15 — hiệu lực 01/7/2026, phần tiền lương tiền công của cá nhân
    cư trú áp dụng TỪ KỲ TÍNH THUẾ NĂM 2026; biểu lũy tiến rút từ bảy bậc xuống NĂM bậc.
  · Nghị quyết 110/2025/UBTVQH15 — giảm trừ gia cảnh 15.500.000 / 6.200.000 từ kỳ tính thuế 2026.
VTOS đang mang mức cũ 11.000.000 / 4.400.000 (NQ 954/2020) trên bàn chạy thật.

CHỦ TỊCH QUYẾT 08/10/2026: "VTOS tính", áp dụng từ kỳ tới, cân đối khi quyết toán năm.

BẢN NÀY LÀM PHÉP TÍNH, KHÔNG BẬT. Lý do viết thẳng ở đầu `services/thue_tncn.py` và được canh bằng
`test_ns3::test_cong_tac_bat_thue_luy_tien_khong_nam_trong_ma`: thuế lũy tiến của người HĐLĐ có thể
đang được MISA khấu trừ, và hai nơi cùng trừ một khoản thì người lao động là người phát hiện ra —
vào ngày nhận lương. Công tắc là tham số `tncn_luy_tien_tu_ky`, trống trong bộ mặc định, mở bằng hai
chữ ký ở màn hình Tham số.

PHÉP THỬ ĐẮT NHẤT TRONG TỆP là `test_moc_bieu_thue_khop_so_cong_bo`: nó không hỏi mã có chạy không,
nó hỏi mã có RA ĐÚNG SỐ CỦA LUẬT không, ở năm mốc tính tay được. Một biểu thuế gõ sai một chữ số vẫn
chạy trơn tru và vẫn in ra tiền.
"""
import os
import sys
from datetime import date
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ky1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ky1.db"):
    os.remove("test_ky1.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal              # noqa: E402
from app.services import thue_tncn as T              # noqa: E402
from app.services import rules as R                  # noqa: E402
from app.services.thu_nhap_su_kien import LOAI_KHOAN  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


# ------------------------------------------------- biểu thuế phải ra đúng số của luật

def test_moc_bieu_thue_khop_so_cong_bo():
    """Năm mốc tính tay được, cộng dồn từ bậc dưới lên — sai một chữ số là lệch ở đây.

    10tr → 10×5%                                    = 500.000
    30tr → 500.000 + 20tr×10%                       = 2.500.000
    60tr → 2.500.000 + 30tr×20%                     = 8.500.000
    100tr → 8.500.000 + 40tr×30%                    = 20.500.000
    150tr → 20.500.000 + 50tr×35%                   = 38.000.000
    """
    moc = {10_000_000: 500_000, 30_000_000: 2_500_000, 60_000_000: 8_500_000,
           100_000_000: 20_500_000, 150_000_000: 38_000_000}
    for tntt, thue in moc.items():
        assert T.thue_thang(tntt)["thue"] == thue, \
            f"thu nhập tính thuế {tntt:,} phải ra thuế {thue:,}, biểu thuế đang sai"


def test_bieu_thue_dung_nam_bac_va_lien_tuc():
    """Năm bậc, trần tăng dần, bậc cuối không trần, thuế suất tăng dần — và PHỦ KÍN từ 0 tới vô cùng.

    Hỏi cấu trúc chứ không chỉ hỏi vài con số: một biểu thiếu một bậc vẫn ra số cho mọi đầu vào, chỉ
    là ra sai, và cái sai ấy chỉ lộ ở đúng khoảng bị thiếu.
    """
    assert len(T.BAC_THUE) == 5, "Luật Thuế TNCN 2025 có đúng năm bậc"
    tran = [t for t, _ in T.BAC_THUE]
    assert tran[-1] is None, "bậc cuối phải không có trần"
    assert tran[:-1] == sorted(t for t in tran[:-1]), "trần các bậc không tăng dần"
    suat = [s for _, s in T.BAC_THUE]
    assert suat == sorted(suat) and len(set(suat)) == 5, "thuế suất phải tăng dần và khác nhau"
    assert suat[0] == 0.05 and suat[-1] == 0.35, "bậc đầu 5%, bậc cuối 35%"
    # Phủ kín: tổng phần của các bậc luôn bằng chính thu nhập tính thuế.
    for tntt in (1, 9_999_999, 10_000_000, 10_000_001, 59_999_999, 100_000_001, 500_000_000):
        kq = T.thue_thang(tntt)
        assert sum(b["phan"] for b in kq["bac"]) == tntt, f"biểu thuế bỏ sót một khoảng tại {tntt:,}"


def test_thu_nhap_duoi_muc_giam_tru_thi_khong_thue():
    for x in (-5_000_000, 0, None):
        assert T.thue_thang(x)["thue"] == 0, "thu nhập tính thuế không dương mà vẫn ra thuế"


# ------------------------------------------------- phân loại khoản: không được im lặng

def test_moi_loai_khoan_deu_duoc_xep_loai():
    """Ba túi phải phủ kín `LOAI_KHOAN`. Thêm loại khoản mới mà quên xếp → phép thử này đỏ.

    Đây là chỗ dễ hỏng lặng nhất của cả vòng: nếu mã mặc định "không biết thì coi như chịu thuế",
    một khoản miễn thuế thêm sau này sẽ bị trừ thuế mà không dòng nào kêu — và người bị trừ không
    có cách nào biết.
    """
    phu = set(T.CHIU_THUE) | set(T.MIEN_THUE) | set(T.KHAU_TRU_RIENG)
    assert phu == set(LOAI_KHOAN), (
        f"loại khoản chưa được xếp: {sorted(set(LOAI_KHOAN) - phu)}; "
        f"xếp thừa tên không có thật: {sorted(phu - set(LOAI_KHOAN))}")
    assert not (set(T.MIEN_THUE) & set(T.KHAU_TRU_RIENG)), "một loại khoản nằm hai túi"
    assert "cong_tac_phi_tx" in T.MIEN_THUE, "công tác phí tài xế bị tính vào thu nhập chịu thuế"
    assert "thu_lao_hdv" in T.KHAU_TRU_RIENG, "thù lao HDV đã khấu trừ 10% mà còn vào biểu lũy tiến"


def test_moi_loai_hop_dong_deu_co_cach_khau_tru():
    """Phủ kín `CONTRACT_KINDS` — loại hợp đồng mới mà không nói cách khấu trừ là một người tính sai thuế."""
    from app.models.hrm import CONTRACT_KINDS
    thieu = set(CONTRACT_KINDS) - set(T.CACH_THEO_LOAI_HD)
    assert not thieu, f"loại hợp đồng chưa có cách khấu trừ: {sorted(thieu)}"
    assert set(T.CACH_THEO_LOAI_HD.values()) <= {T.LUY_TIEN, T.KHAU_TRU_10}


# ------------------------------------------------- công tắc

def test_chua_bat_thi_khong_ai_bi_tru():
    """Mặc định là KHÔNG khấu trừ. Đây là trạng thái bản này giao cho Chủ tịch, không phải thiếu sót."""
    db = SessionLocal()
    try:
        assert T.ky_bat_dau(db) == "", "công tắc thuế lũy tiến đã bật sẵn — không ai ký mà đã trừ tiền"
        for ky in ("2026-09", "2026-10", "2027-01"):
            assert T.da_bat(db, ky) is False, f"kỳ {ky} đang bị coi là đã bật"
    finally:
        db.close()


def test_bat_roi_thi_chi_ap_tu_ky_duoc_ky_tro_di():
    """Bật giữa năm KHÔNG được quét ngược các kỳ đã qua: Chủ tịch quyết 'từ kỳ tới, cân đối khi quyết toán'."""
    db = SessionLocal()
    from app.models.core import Param
    # Hiệu lực SAU bản gieo mặc định (01/9/2026) và không muộn hơn hôm nay: `get_param_text` lấy bản
    # có hiệu lực mới nhất tính tới hôm nay, nên một bản ghi hiệu lực 01/01 sẽ bị bản gieo che mất.
    try:
        db.add(Param(key=T.KY_TU_KY_KEY, value="2026-11", label="x", unit="YYYY-MM",
                     effective_from=date(2026, 10, 1), source="phép thử", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="test"))
        db.commit()
        R.clear_param_cache()
        assert T.da_bat(db, "2026-10") is False, "kỳ TRƯỚC kỳ bật vẫn bị khấu trừ — quét ngược quá khứ"
        assert T.da_bat(db, "2026-11") is True
        assert T.da_bat(db, "2026-12") is True
    finally:
        db.query(Param).filter(Param.key == T.KY_TU_KY_KEY, Param.proposed_by == "test").delete()
        db.commit()
        R.clear_param_cache()
        db.close()


# ------------------------------------------------- mức giảm trừ lạc hậu phải ĐẾM ĐƯỢC

def test_muc_giam_tru_lac_hau_so_voi_luat_thi_bao_ra():
    """Bàn chạy thật đang mang mức 11tr/4,4tr. Mã KHÔNG tự sửa — nó đếm chênh và chỉ đường tới cửa ký.

    Đè thẳng lên giá trị đang hiệu lực là đi vòng qua đúng cái cửa hai chữ ký mà hệ thống dựng ra để
    không ai đổi tiền của người khác một mình.
    """
    db = SessionLocal()
    from app.models.core import Param
    try:
        db.add(Param(key="giam_tru_ban_than", value="11000000", label="x", unit="đồng/tháng",
                     effective_from=date(2026, 10, 1), source="phép thử", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="test_cu"))
        db.commit()
        R.clear_param_cache()
        lac = T.tham_so_lac_hau(db, "2026-10")
        khoa = {x["khoa"] for x in lac}
        assert "giam_tru_ban_than" in khoa, "mức giảm trừ cũ mà không dòng nào báo"
        x = [x for x in lac if x["khoa"] == "giam_tru_ban_than"][0]
        assert x["dang_ap"] == 11_000_000 and x["theo_luat"] == 15_500_000
        assert x["chenh"] == 4_500_000
        assert "Tham số" in x["viec_phai_lam"], "báo chênh mà không chỉ đường tới cửa sửa"
    finally:
        db.query(Param).filter(Param.proposed_by == "test_cu").delete()
        db.commit()
        R.clear_param_cache()
        db.close()


def test_bo_tham_so_mac_dinh_mang_muc_cua_luat_2026():
    """Cơ sở dữ liệu mới dựng phải ĐÚNG LUẬT ngay; bàn đang chạy thì chờ chữ ký."""
    mac_dinh = {k: v for k, v, *_ in R.DEFAULT_PARAMS}
    assert mac_dinh["giam_tru_ban_than"] == "15500000"
    assert mac_dinh["giam_tru_nguoi_phu_thuoc"] == "6200000"
    db = SessionLocal()
    try:
        assert T.tham_so_lac_hau(db, "2026-10") == [], \
            "bàn mới dựng mà mức giảm trừ đã lạc hậu — bộ tham số mặc định chưa theo NQ 110/2025"
        assert T.tham_so_lac_hau(db, "2025-12") == [], "mức mới áp từ kỳ 2026, không quét ngược 2025"
    finally:
        db.close()


# ------------------------------------------------- mức giảm trừ phải đọc theo KỲ, không theo hôm nay

def test_doc_muc_giam_tru_theo_ky_chu_khong_theo_hom_nay():
    """Ký mức mới hiệu lực từ 01/11 thì kỳ tháng 9 tính lại vẫn phải ra mức của tháng 9.

    Trước bản này `pit_deduction()` gọi `get_param` không kèm ngày, tức mọi kỳ cũ đều lấy mức mới
    nhất — một bảng lương cũ tính lại sẽ ra số khác với bản đã ký, và không ai biết vì sao.
    """
    db = SessionLocal()
    from app.models.core import Param
    try:
        db.add(Param(key="giam_tru_ban_than", value="99000000", label="x", unit="đồng/tháng",
                     effective_from=date(2026, 11, 1), source="phép thử", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="test_sau"))
        db.commit()
        R.clear_param_cache()
        assert T.muc_giam_tru(db, "2026-09")["ban_than"] != 99_000_000, \
            "kỳ tháng 9 đọc phải mức có hiệu lực từ tháng 11"
        assert T.muc_giam_tru(db, "2026-11")["ban_than"] == 99_000_000
    finally:
        db.query(Param).filter(Param.proposed_by == "test_sau").delete()
        db.commit()
        R.clear_param_cache()
        db.close()


# ------------------------------------------------- một dòng lương cụ thể

def _dong(thu_nhap: float, bhxh: float = 0.0, khoan=None, **kw) -> dict:
    d = {"ma": "X", "ten": "Người thử", "thu_nhap": thu_nhap, "bhxh": bhxh, "khoan": khoan or []}
    d.update(kw)
    return d


def test_mot_dong_luong_tru_dung_thu_tu_bao_hiem_roi_giam_tru_roi_moi_luy_tien():
    """40tr thu nhập, 2tr bảo hiểm, 1 người phụ thuộc, mức 15,5 + 6,2:
       TNTT = 40 − 2 − 21,7 = 16,3tr → 500.000 + 6,3tr×10% = 1.130.000."""
    db = SessionLocal()
    try:
        gt = {"ban_than": 15_500_000.0, "nguoi_phu_thuoc": 6_200_000.0}
        kq = T.tinh_cho_dong(db, "2026-11", _dong(40_000_000, 2_000_000), None, gt, 1)
        assert kq["giam_tru"] == 21_700_000
        assert kq["tntt"] == 16_300_000
        # Không có nhân sự → chưa xác định cách khấu trừ, nên thuế ghi 0 nhưng phép tính vẫn hiện ra.
        assert kq["cach"] == T.CHUA_CO_HOP_DONG and kq["thue"] == 0
        assert T.thue_thang(kq["tntt"])["thue"] == 1_130_000
    finally:
        db.close()


def test_khoan_mien_thue_va_khoan_da_khau_tru_rieng_bi_tru_khoi_nen_tinh_thue():
    """Công tác phí tài xế và thù lao HDV không được vào nền tính thuế lũy tiến."""
    db = SessionLocal()
    try:
        gt = {"ban_than": 15_500_000.0, "nguoi_phu_thuoc": 6_200_000.0}
        khoan = [{"ten": "Công tác phí", "tien": 3_000_000, "loai": "cong_tac_phi_tx"},
                 {"ten": "Thù lao dẫn", "tien": 5_000_000, "loai": "thu_lao_hdv"},
                 {"ten": "Hoa hồng", "tien": 4_000_000, "loai": "hh_thang_f"}]
        kq = T.tinh_cho_dong(db, "2026-11", _dong(42_000_000, 0, khoan), None, gt, 0)
        assert kq["mien_thue"] == 3_000_000 and kq["khau_tru_rieng"] == 5_000_000
        assert kq["thu_nhap_chiu_thue"] == 34_000_000, "nền tính thuế chưa trừ khoản miễn / đã khấu trừ riêng"
    finally:
        db.close()


def test_chua_co_muc_dong_bhxh_thi_noi_ra_thue_dang_cao_hon():
    """Không có mức đóng BHXH thì bảo hiểm không được trừ, nên thuế tạm tính CAO hơn số phải nộp.

    Im lặng ở đây là trừ thừa tiền của người lao động mà họ không có cách nào biết.
    """
    db = SessionLocal()
    try:
        gt = {"ban_than": 15_500_000.0, "nguoi_phu_thuoc": 6_200_000.0}
        kq = T.tinh_cho_dong(db, "2026-11", _dong(40_000_000, 0, None, thieu_muc_bhxh=True), None, gt, 0)
        assert any("BHXH" in c for c in kq["canh_bao"]), "thiếu mức đóng BHXH mà không dòng nào cảnh báo"
        assert any("CAO hơn" in c for c in kq["canh_bao"])
    finally:
        db.close()


# ------------------------------------------------- trả lời trước khi bấm

def test_thu_neu_bat_tra_loi_duoc_ca_khi_chua_bat():
    """Quyết định 'có bật không' phải quyết với con số trong tay, không quyết mò."""
    db = SessionLocal()
    try:
        kq = T.thu_neu_bat(db, "2026-10", [])
        assert kq["da_bat"] is False
        assert "CHƯA BẬT" in kq["ghi_chu"], "chưa bật mà lời không nói rõ, người đọc tưởng đã trừ rồi"
        assert "MISA" in kq["ghi_chu"], "không nhắc chỗ hỏng thật: hai nơi cùng khấu trừ một khoản"
        assert kq["tong_thue"] == 0 and kq["so_nguoi_xet"] == 0
    finally:
        db.close()


def test_cua_tncn_con_thieu_doi_loi_theo_cong_tac():
    """Cửa cũ vẫn trả lời, và nay mang thêm `da_bat` để màn hình khỏi đoán."""
    r = client.post("/api/v1/auth/login", data={"username": "hcns", "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, "không đăng nhập được để thử cửa"
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    kq = client.get("/api/v1/payroll-runs/1999-01/tncn-con-thieu", headers=h)
    assert kq.status_code == 200
    d = kq.json()
    assert d["da_bat"] is False
    assert "CHƯA" in d["ghi_chu"]
    assert "tham_so_lac_hau" in d

# ------------------------------------------------- phép thử đắt thứ hai: DÂY NỐI, không phải phép tính

def test_bat_cong_tac_thi_bang_luong_that_khau_tru_that():
    """Phép tính đúng mà không ai gọi thì bằng không có. Phép thử này đi qua `hr.compute_draft` thật.

    Bật công tắc → một người HĐLĐ có thu nhập trên mức giảm trừ phải có `tncn > 0` và có chi tiết
    từng bậc kèm theo; tắt công tắc → đúng người ấy về 0. Đỏ theo CẢ HAI CHIỀU trong một phép thử,
    vì một nửa chiều thì không phân biệt được "dây nối đúng" với "lúc nào cũng tính".
    """
    from app.services import hr as HR
    from app.models.core import Param
    from app.models.hr import Employee
    from app.models.hrm import LaborContract
    from sqlalchemy import select as _sel

    db = SessionLocal()
    ky = "2026-11"
    try:
        # Một người HĐLĐ có lương đủ cao để vượt mức giảm trừ bản thân.
        e = db.execute(_sel(Employee).where(Employee.active == True,
                                            Employee.contract_type == "hdld")).scalars().first()
        assert e is not None, "bàn demo không có người HĐLĐ nào – phép thử này không nói lên gì"
        cu_luong, cu_bhxh = e.base_salary, e.bhxh_base
        e.base_salary = 60_000_000
        # HỢP ĐỒNG PHẢI CÓ THẬT, và chỗ này là một phát hiện chứ không phải thủ tục dựng cảnh: bàn
        # demo có 0 bản ghi `labor_contracts`, nên bật công tắc lên thì KHÔNG AI bị khấu trừ — hàm
        # `cach_khau_tru` trả `chua_co_hop_dong` và thuế ghi 0. Đúng (không đoán cách khấu trừ của
        # người không có hợp đồng), nhưng im lặng thì thành "thuế bằng 0" trên màn hình. Đó chính là
        # lý do `thu_neu_bat()` đếm riêng `so_nguoi_chua_co_hop_dong`.
        db.add(LaborContract(employee_id=e.id, code="HD-KY1-TEST", kind="khong_xac_dinh",
                             effective_from=date(2026, 1, 1), effective_to=None,
                             salary=60_000_000, status="hieu_luc", created_by="test"))
        db.commit()

        tat, _ = HR.compute_draft(db, ky)
        dong_tat = [r for r in tat if r["ma"] == e.code]
        assert dong_tat, "không thấy người thử trong bảng lương"
        assert dong_tat[0]["tncn"] == 0, "công tắc đang TẮT mà bảng lương đã khấu trừ lũy tiến"
        assert "tncn_luy_tien" not in dong_tat[0]

        db.add(Param(key=T.KY_TU_KY_KEY, value=ky, label="x", unit="YYYY-MM",
                     effective_from=date(2026, 10, 1), source="phép thử", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="test_bat"))
        db.commit()
        R.clear_param_cache()

        bat, _ = HR.compute_draft(db, ky)
        dong = [r for r in bat if r["ma"] == e.code][0]
        assert dong["tncn"] > 0, "bật công tắc rồi mà bảng lương vẫn không khấu trừ – dây nối đứt"
        ct = dong["tncn_luy_tien"]
        assert ct["thue"] == dong["tncn"], "số trên dòng lệch với chi tiết của chính nó"
        assert ct["bac"], "khấu trừ mà không nói ra bậc nào ăn bao nhiêu"
        # Thuế phải nằm trong khoản trừ, và thực nhận phải tụt đúng bằng thuế.
        assert dong["khoan_tru"] >= dong["tncn"], "thuế không được cộng vào khoản trừ"
        assert dong["thu_nhap"] - dong["khoan_tru"] == dong["thuc_nhan"]
        assert dong["thuc_nhan"] == dong_tat[0]["thuc_nhan"] - dong["tncn"],             "thực nhận không tụt đúng bằng số thuế vừa khấu trừ"

        # Kỳ TRƯỚC kỳ bật vẫn không bị trừ – không quét ngược quá khứ.
        truoc, _ = HR.compute_draft(db, "2026-10")
        d2 = [r for r in truoc if r["ma"] == e.code]
        if d2:
            assert d2[0]["tncn"] == 0, "bật từ kỳ 11 mà kỳ 10 cũng bị khấu trừ"
    finally:
        db.query(Param).filter(Param.proposed_by == "test_bat").delete()
        db.query(LaborContract).filter(LaborContract.code == "HD-KY1-TEST").delete()
        e.base_salary, e.bhxh_base = cu_luong, cu_bhxh
        db.commit()
        R.clear_param_cache()
        db.close()

def test_bat_roi_thi_cua_tncn_con_thieu_doi_han_loi_va_doi_ca_cach_dem():
    """Bẻ ngược 08/10/2026 tìm ra CHỖ TRỐNG NÀY: không phép thử nào chứng minh `tncn_chua_tinh()`
    đổi lời khi công tắc bật. Ghim cứng `da_bat = False` trong hàm ấy thì cả bộ vẫn xanh.

    Và lời không phải thứ duy nhất phải đổi — CÁCH ĐẾM cũng đổi. Chưa bật thì "tncn = 0" là chỗ
    thiếu; bật rồi thì "tncn = 0" của người thu nhập dưới mức giảm trừ là ĐÚNG, còn chỗ thiếu dời
    sang hồ sơ: chưa có hợp đồng, chưa có mã số thuế, chưa có mức đóng BHXH. Một hàm đổi lời mà
    không đổi cách đếm sẽ in ra một câu đúng kèm một con số sai.
    """
    from app.services import hrm as H
    from app.models.core import Param
    db = SessionLocal()
    ky = "2026-11"
    dong = [{"ma": "NS0001", "tncn": 0, "thu_nhap": 60_000_000,
             "tncn_luy_tien": {"cach": T.CHUA_CO_HOP_DONG, "thue": 0}}]
    try:
        tat = H.tncn_chua_tinh(db, ky, dong)
        assert tat["da_bat"] is False and "CHƯA" in tat["ghi_chu"]
        assert tat["chua_co_hop_dong"] == 0, "chưa bật thì chưa đếm chỗ hở hồ sơ"

        db.add(Param(key=T.KY_TU_KY_KEY, value=ky, label="x", unit="YYYY-MM",
                     effective_from=date(2026, 10, 1), source="phép thử", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="test_loi"))
        db.commit()
        R.clear_param_cache()

        bat = H.tncn_chua_tinh(db, ky, dong)
        assert bat["da_bat"] is True, "công tắc bật mà cửa vẫn báo chưa bật"
        assert "CHƯA tự khấu trừ" not in bat["ghi_chu"], \
            "đã khấu trừ rồi mà màn hình còn nói chưa — đúng cái im lặng vòng NS-3 dựng hàng rào để chặn"
        assert bat["ky_bat_dau"] == ky, "không nói ra bật từ kỳ nào"
        assert bat["chua_co_hop_dong"] == 1, "bật rồi mà không đếm người chưa có hợp đồng hiệu lực"
    finally:
        db.query(Param).filter(Param.proposed_by == "test_loi").delete()
        db.commit()
        R.clear_param_cache()
        db.close()
