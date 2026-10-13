"""HD-5 — CỔNG CẤP QUYỀN THEO TỪNG HỒ SƠ VÀ TỪNG THAO TÁC: phép thử phải CẮN.

Chủ tịch chốt 13/10/2026, sau bước rà soát mã: "Chuẩn hóa các kiểm tra đang rải rác thành cơ chế cấp
quyền theo từng hồ sơ và từng thao tác, bắt buộc dùng cho cổng HDV" — phủ xem, sửa, tải tệp, xuất
danh sách, nhận thông báo và dữ liệu tổng hợp.

Và một yêu cầu thứ hai, đứng ngang hàng: phép thử phải CHỨNG MINH ĐƯỢC là nó cắn. Hôm 12/10 có bảy
hàng rào trả lời một câu khác với câu chúng đặt tên. Một trong số đó còn sống trên `main` lúc viết
bộ này:

    test_chao_chuyen_hdv.py:127  "không trả lời thay lời chào của người khác"

Người thứ hai ở phép thử ấy được dựng với `staff_code="KHONG-CO"` và KHÔNG CÓ hồ sơ Employee nào.
Nên nó chứng minh "tài khoản chưa nối hồ sơ thì bị 404", không chứng minh "hướng dẫn viên B có hồ sơ
thật thì không chạm được lời mời của A". Bỏ hẳn vế `a.guide_id != e.id` đi, nó vẫn xanh.

Bộ này không để điều đó lặp lại. Nhóm D chạy lại chính các ca của nhóm B và C qua HAI BẢN CỔNG CỐ Ý
VIẾT SAI — chép đúng hình dạng hai lỗi có thật trong mã — và đòi ca ấy phải phân biệt được. Nhóm E
canh bằng cây cú pháp chứ không bằng tìm chuỗi, vì tìm chuỗi thì chú thích cũng khớp.

  A. Một hàm tra người, thay cho bốn dạng đang cùng tồn tại.
  B. Cổng: sáu thao tác là sáu câu hỏi riêng; không tra được người là TỪ CHỐI.
  C. Bộ lọc danh sách / xuất / số tổng hợp: thu hẹp về đúng hồ sơ của người đăng nhập.
  D. Chứng minh các ca trên CẮN: cùng ca ấy, bản cổng sai phải cho qua.
  E. Hàng rào cú pháp: trong cổng không được có nhánh "tra không ra thì bỏ qua phép so".
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd5.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd5.db"):
    os.remove("test_hd5.db")

import ast
import inspect
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import quyen_ho_so as Q

client = TestClient(app)
ID: dict[str, int] = {}
NGUOI: dict[str, object] = {}

QUAN_LY = ("tp_hd", "hcns", "cntt")


def _hdv(ma: str, ten: str):
    from app.models.hr import Employee
    return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                    start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                    member_org=True, contract_type="ctv", ctv_contract=True)


def _tk(ten: str, vai: str = "hdv", ma_nv: str = ""):
    from app.core.security import hash_password
    from app.models.core import User
    return User(username=ten, full_name=ten, role=vai, department="Hướng dẫn",
                staff_code=ma_nv, password_hash=hash_password("Vtos@Demo#2026"))


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    """Dựng sáu tài khoản, mỗi tài khoản là MỘT ca biên có thật trên hệ thống hôm nay."""
    with TestClient(app) as c:
        global client
        client = c
        from app.db.session import SessionLocal

        db = SessionLocal()

        # Hai hướng dẫn viên THẬT, mỗi người một hồ sơ. Đây là ca mà phép thử cũ không có.
        e1, e2 = _hdv("Q5001", "Trần Văn A"), _hdv("Q5002", "Nguyễn Thị B")
        # Hồ sơ nối bằng MÃ NHÂN VIÊN chứ chưa nối tài khoản — giai đoạn HCNS chưa ghép `user_id`.
        e3 = _hdv("Q5003", "Lê Văn C")
        # Hai hồ sơ cùng trỏ MỘT tài khoản — dữ liệu hỏng, hôm nay `.first()` lặng lẽ lấy cái đầu.
        e4a, e4b = _hdv("Q5004", "Hoàng Văn D"), _hdv("Q5005", "Hoàng Văn D (trùng)")
        # Hồ sơ mà tài khoản nối tới, trong khi `staff_code` lại ghi mã của người khác.
        e5 = _hdv("Q5006", "Đỗ Thị E")
        db.add_all([e1, e2, e3, e4a, e4b, e5])

        u1, u2 = _tk("q5.mot"), _tk("q5.hai")
        u3 = _tk("q5.chi_ma", ma_nv="Q5003")           # chỉ có mã, chưa ghép tài khoản
        u4 = _tk("q5.trung_ho_so")                     # hai hồ sơ cùng trỏ vào
        u5 = _tk("q5.lech_ma", ma_nv="Q5003")          # nối e5 nhưng mã ghi Q5003
        u6 = _tk("q5.khong_ho_so")                     # không hồ sơ nào cả
        u7 = _tk("q5.truong_phong", vai="tp_hd")       # quản lý, cũng không nối hồ sơ
        db.add_all([u1, u2, u3, u4, u5, u6, u7])
        db.commit()

        e1.user_id, e2.user_id = u1.id, u2.id
        e4a.user_id = e4b.user_id = u4.id
        e5.user_id = u5.id
        db.commit()

        for k, e in (("e1", e1), ("e2", e2), ("e3", e3), ("e5", e5)):
            ID[k] = e.id
        for k, u in (("mot", u1), ("hai", u2), ("chi_ma", u3), ("trung", u4),
                     ("lech", u5), ("khong", u6), ("tp", u7)):
            NGUOI[k] = u
        db.close()
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


# ───────────────────────── A · một hàm tra người ─────────────────────────

def test_a1_noi_bang_tai_khoan_thi_tra_dung_ho_so():
    with _db() as db:
        assert Q.ho_so_cua(db, NGUOI["mot"]).code == "Q5001"


def test_a2_noi_bang_ma_nhan_vien_cung_tra_duoc():
    """Dạng 2 (`user_id`, không có đường lùi) TRƯỢT ca này — hr.py:753 từ chối đúng người này, trong
    khi hr.py:319 cho qua. Cổng chung phải cho qua: hồ sơ có trước tài khoản, giai đoạn chưa ghép là
    giai đoạn có thật chứ không phải lỗi."""
    with _db() as db:
        assert Q.ho_so_cua(db, NGUOI["chi_ma"]).code == "Q5003"


def test_a3_khong_noi_gi_thi_NEM_chu_khong_tra_rong():
    """Cái rỗng là nguồn của lỗi fail-open ở hr.py:882. Ở đây nó không tồn tại."""
    with _db() as db:
        with pytest.raises(Q.LoiHoSo) as ex:
            Q.ho_so_cua(db, NGUOI["khong"])
        assert ex.value.status_code == 404


def test_a4_hai_ho_so_cung_tro_mot_tai_khoan_thi_NEM():
    """`.first()` ở 12 chỗ hiện nay lặng lẽ lấy hồ sơ đầu — nghĩa là người dùng có thể đang thao tác
    dưới tên một đồng nghiệp. Lỗi phải GỌI TÊN cả hai hồ sơ để HCNS biết gỡ cái nào."""
    with _db() as db:
        with pytest.raises(Q.LoiHoSo) as ex:
            Q.ho_so_cua(db, NGUOI["trung"])
        assert ex.value.status_code == 409
        loi = ex.value.detail["message"]
        assert "Q5004" in loi and "Q5005" in loi, loi


def test_a5_hai_duong_noi_tro_hai_nguoi_thi_NEM():
    """Tài khoản nối hồ sơ Q5006 nhưng mã nhân viên ghi Q5003. Một trong hai đang trỏ nhầm người, và
    chưa biết đường nào — không được chọn hộ."""
    with _db() as db:
        with pytest.raises(Q.LoiHoSo) as ex:
            Q.ho_so_cua(db, NGUOI["lech"])
        assert ex.value.status_code == 409
        loi = ex.value.detail["message"]
        assert "Q5006" in loi and "Q5003" in loi, loi


def test_a6_ban_hoac_rong_chi_rong_khi_chua_noi_chu_khong_khi_noi_sai():
    """`ho_so_cua_hoac_rong` trả rỗng nghĩa là CHƯA NỐI. Nối sai vẫn phải ném — rỗng không được
    dùng làm chỗ nuốt dữ liệu hỏng."""
    with _db() as db:
        assert Q.ho_so_cua_hoac_rong(db, NGUOI["khong"]) is None
        with pytest.raises(Q.LoiHoSo):
            Q.ho_so_cua_hoac_rong(db, NGUOI["trung"])


# ───────────────────────── B · cổng sáu thao tác ─────────────────────────

SAU_VIEC = ("xem", "sua", "tai_tep", "xuat_danh_sach", "thong_bao", "so_tong_hop")


def test_b0_bang_thao_tac_dung_sau_viec_Chu_tich_neu():
    """Chủ tịch nêu đúng sáu: xem, sửa, tải tệp, xuất danh sách, thông báo, dữ liệu tổng hợp. Bớt
    một là một cánh cửa không ai canh; thêm một mà không chốt là một quyền tự mọc."""
    assert tuple(Q.THAO_TAC) == SAU_VIEC


def test_b1_chu_ho_so_di_qua_ca_sau():
    with _db() as db:
        for viec in SAU_VIEC:
            assert Q.kiem(db, NGUOI["mot"], viec, ID["e1"], QUAN_LY).code == "Q5001", viec


def test_b2_hai_hdv_that_khong_cham_duoc_cua_nhau_o_ca_sau_viec():
    """CA MÀ BỘ PHÉP THỬ HÔM NAY CHƯA CÓ. Hai hướng dẫn viên thật, mỗi người một hồ sơ thật."""
    with _db() as db:
        for viec in SAU_VIEC:
            with pytest.raises(Q.LoiHoSo) as ex:
                Q.kiem(db, NGUOI["hai"], viec, ID["e1"], QUAN_LY)
            assert ex.value.status_code == 403, viec
            # Người bị chặn phải đọc ra bị chặn Ở VIỆC GÌ, không phải một chữ 403 trơ.
            assert Q.THAO_TAC[viec] in ex.value.detail["message"], viec


def test_b3_quan_ly_di_qua_ca_sau_va_bao_la_quan_ly():
    with _db() as db:
        for viec in SAU_VIEC:
            assert Q.kiem(db, NGUOI["tp"], viec, ID["e1"], QUAN_LY) is None, viec


def test_b4_tra_khong_ra_nguoi_thi_TU_CHOI_chu_khong_bo_qua_phep_so():
    """Đây đúng chỗ hr.py:882 làm ngược lại: `if e is not None and e.id == a.guide_id` — tài khoản
    người kiểm chưa nối hồ sơ thì cả phép kiểm im lặng không chạy."""
    with _db() as db:
        for viec in SAU_VIEC:
            with pytest.raises(Q.LoiHoSo) as ex:
                Q.kiem(db, NGUOI["khong"], viec, ID["e1"], QUAN_LY)
            assert ex.value.status_code == 404, viec


def test_b5_go_sai_ten_thao_tac_thi_NO_chu_khong_mac_dinh_cho_qua():
    """Một cổng mà gõ nhầm thì mở là cổng tệ hơn không có cổng: nó làm người đọc tin là đã canh."""
    with _db() as db:
        with pytest.raises(Q.LoiHoSo) as ex:
            Q.kiem(db, NGUOI["mot"], "xem_het", ID["e1"], QUAN_LY)
        assert ex.value.status_code == 500


def test_b6_ban_ghi_chua_ghi_chu_thi_khong_coi_la_cua_minh():
    """`chu_ho_so_id` rỗng là bản ghi chưa gắn người. Không có gì để đối chiếu thì không được suy ra
    'chắc là của mình'."""
    with _db() as db:
        with pytest.raises(Q.LoiHoSo) as ex:
            Q.kiem(db, NGUOI["mot"], "xem", None, QUAN_LY)
        assert ex.value.status_code == 404


# ───────────────────────── C · bộ lọc danh sách / xuất / số tổng hợp ─────────────────────────
#
# Ba thao tác mà cổng `kiem` không với tới, vì lúc ấy chưa có một hồ sơ cụ thể để hỏi. Đây chính là
# chỗ hôm nay đang hở: `thu-lao/doi-soat` (hr.py:1082) trả toàn kỳ; `khoan_treo` (hr.py:2050) lọc
# bằng chuỗi ma thuật `"\u0000"`.

def _ma_sau_khi_loc(db, u, vai=QUAN_LY):
    from sqlalchemy import select

    from app.models.hr import Employee
    q = Q.loc(select(Employee).where(Employee.code.like("Q50%")), Employee.id, db, u,
              "xuat_danh_sach", vai)
    return sorted(e.code for e in db.execute(q).scalars())


def test_c1_hdv_chi_thay_dong_cua_chinh_minh():
    with _db() as db:
        assert _ma_sau_khi_loc(db, NGUOI["mot"]) == ["Q5001"]
        assert _ma_sau_khi_loc(db, NGUOI["hai"]) == ["Q5002"]


def test_c2_quan_ly_thay_het():
    with _db() as db:
        assert len(_ma_sau_khi_loc(db, NGUOI["tp"])) >= 6


def test_c3_tra_khong_ra_nguoi_thi_NEM_chu_khong_tra_danh_sach_rong():
    """Rỗng trông y hệt 'không có việc nào'. Một hướng dẫn viên nhìn bảng thù lao trống sẽ tưởng kỳ
    này mình không có chuyến nào — đó là một con số sai, không phải một màn hình trống."""
    with _db() as db:
        with pytest.raises(Q.LoiHoSo):
            _ma_sau_khi_loc(db, NGUOI["khong"])


# ───────────────────────── D · chứng minh các ca trên CẮN ─────────────────────────
#
# Quy trình Chủ tịch đặt: đỏ trước → hiện thực → GỠ PHÉP KIỂM RA XEM CÓ ĐỎ LẠI KHÔNG. Bước thứ ba
# thường làm ở máy rồi quên, nên không ai kiểm lại được. Ở đây nó nằm TRONG kho mã và chạy mỗi lần
# CI chạy: hai bản cổng cố ý viết sai, chép đúng hình dạng hai lỗi có thật.


def _cong_sai_kieu_882(db, u, viec, chu_ho_so_id, vai_quan_ly=()):
    """Bản SAI thứ nhất — chép hình dạng hr.py:882: tra không ra người thì bỏ qua phép so."""
    if Q.la_quan_ly(u, vai_quan_ly):
        return None
    e = Q.ho_so_cua_hoac_rong(db, u)
    if e is not None and e.id != chu_ho_so_id:
        raise Q.LoiHoSo(403, "chan")
    return e


def _cong_sai_chi_hoi_co_ho_so(db, u, viec, chu_ho_so_id, vai_quan_ly=()):
    """Bản SAI thứ hai — chép hình dạng test_chao_chuyen_hdv.py:127: chỉ hỏi 'có hồ sơ không', không
    so hồ sơ ấy có phải chủ bản ghi không."""
    if Q.la_quan_ly(u, vai_quan_ly):
        return None
    return Q.ho_so_cua(db, u)


def test_d1_ca_b4_phan_biet_duoc_ban_dung_va_ban_sai_kieu_882():
    """Nếu ca B4 không cắn thì bản sai cũng qua được nó. Đòi bản sai CHO QUA đúng chỗ bản đúng chặn."""
    with _db() as db:
        # bản SAI: tài khoản không hồ sơ đi lọt, không một tiếng động
        assert _cong_sai_kieu_882(db, NGUOI["khong"], "xem", ID["e1"], QUAN_LY) is None
        # bản ĐÚNG: chặn
        with pytest.raises(Q.LoiHoSo):
            Q.kiem(db, NGUOI["khong"], "xem", ID["e1"], QUAN_LY)


def test_d2_ca_b2_phan_biet_duoc_ban_dung_va_ban_chi_hoi_co_ho_so():
    """Đây là phép thử mà test_chao_chuyen_hdv.py:127 đáng lẽ phải là. Bản sai cho HDV B chạm hồ sơ
    của HDV A; bản đúng chặn."""
    with _db() as db:
        assert _cong_sai_chi_hoi_co_ho_so(db, NGUOI["hai"], "xem", ID["e1"], QUAN_LY).code == "Q5002"
        with pytest.raises(Q.LoiHoSo):
            Q.kiem(db, NGUOI["hai"], "xem", ID["e1"], QUAN_LY)


def test_d3_ca_a2_phan_biet_duoc_co_va_khong_co_duong_lui_theo_ma():
    """Dạng 2 đang dùng ở 8 chỗ. Dựng lại nó và đòi ca A2 bắt được."""
    from sqlalchemy import select

    from app.models.hr import Employee
    with _db() as db:
        dang_2 = db.execute(
            select(Employee).where(Employee.user_id == NGUOI["chi_ma"].id)).scalars().first()
        assert dang_2 is None, "dựng sai cảnh: tài khoản này đáng lẽ CHƯA nối user_id"
        assert Q.ho_so_cua(db, NGUOI["chi_ma"]).code == "Q5003"


# ───────────────────────── E · hàng rào cú pháp trên chính cổng ─────────────────────────
#
# Canh bằng CÂY CÚ PHÁP chứ không bằng tìm chuỗi. Bài học 12/10: hàng rào của BL-2 tìm chuỗi và bắt
# trúng chính khối chú thích giải thích nó, rồi kết luận ngược với sự thật.


def _than(ten_ham) -> ast.FunctionDef:
    cay = ast.parse(Path(inspect.getsourcefile(Q)).read_text(encoding="utf-8"))
    for nut in cay.body:
        if isinstance(nut, ast.FunctionDef) and nut.name == ten_ham:
            return nut
    raise AssertionError(f"không tìm thấy hàm {ten_ham} trong quyen_ho_so.py")


def test_e1_cong_khong_duoc_co_nhanh_tra_khong_ra_thi_bo_qua():
    """Hình dạng phải cấm: `if <x> is not None and <...>` — vế đầu sai thì cả phép kiểm biến mất.
    Đó là nguyên văn hr.py:882, và là cách một hàng rào tự tắt mà không báo gì."""
    for nut in ast.walk(_than("kiem")):
        if isinstance(nut, ast.BoolOp) and isinstance(nut.op, ast.And):
            for ve in nut.values:
                if (isinstance(ve, ast.Compare) and len(ve.ops) == 1
                        and isinstance(ve.ops[0], ast.IsNot)
                        and isinstance(ve.comparators[0], ast.Constant)
                        and ve.comparators[0].value is None):
                    raise AssertionError(
                        "cổng có nhánh 'is not None and …': tra không ra người thì phép so biến mất")


def test_e2_ham_tra_nguoi_mac_dinh_khong_co_duong_tra_ve_rong():
    """`ho_so_cua` không được có `return None`, kể cả ngầm. Có một đường rỗng là sớm muộn sẽ có một
    nhánh `if e is not None` thứ hai ra đời."""
    than = _than("ho_so_cua")
    for nut in ast.walk(than):
        if isinstance(nut, ast.Return):
            assert not (isinstance(nut.value, ast.Constant) and nut.value.value is None), \
                "ho_so_cua trả về None – đúng cái rỗng mà cổng này sinh ra để xóa"
        assert not isinstance(nut, ast.Return) or nut.value is not None, \
            "ho_so_cua có `return` trống"
