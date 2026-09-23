"""TC-76 · CHỈ TIÊU KINH DOANH VÀ MÀN HÌNH BỐN VAI.

BỐN CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH — đều là loại nhìn màn hình KHÔNG phát hiện được:

 1. RÒ DÒNG QUA CỬA `/don-vi/{id}`. Đây là cửa duy nhất của vòng nhận một id từ người gọi. Một Team
    Leader gõ tay id của team khác phải nhận 403, KHÔNG phải một bảng rỗng — bảng rỗng làm người ta
    tưởng team ấy không bán được đồng nào, và nó biến một lỗ hổng thành một con số sai.

 2. RỖNG KHÁC `None` TRONG PHẠM VI XEM. `pham_vi_xem` trả `None` = xem tất cả, danh sách RỖNG =
    chưa được phân công nên không thấy gì. Viết `if not pham_vi` là biến người chưa phân công thành
    người xem được toàn bộ công ty. Đã có phép thử riêng cho đúng một dòng ấy.

 3. TRÙNG Ô CHỈ TIÊU KHI MỘT CỘT RỖNG. `UniqueConstraint("ky","don_vi_id","user_id","luong")` có hai
    cột cho rỗng, mà trong SQL thì RỖNG KHÁC RỖNG — cơ sở dữ liệu cho ghi hai dòng cùng một ô. Nếu
    phép kiểm ở lớp dịch vụ hỏng thì một người có hai chỉ tiêu và bảng nào cũng đọc một con số khác.

 4. CHỈ TIÊU TỰ SINH RA TỪ SỐ THỰC HIỆN. Ranh giới 09/9/2026: Claude viết cấu trúc, không nhập số.
    `test_khong_co_ham_nao_suy_chi_tieu_tu_thuc_hien` đọc mã bằng cây cú pháp và đòi lớp dịch vụ
    chỉ tiêu KHÔNG được chạm vào bảng booking hay bảng tour.
"""
import ast
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.chi_tieu_kd import LUONG_CHI_TIEU, ChiTieuKD
from app.models.core import Booking, Tour, User
from app.services import chi_tieu_kd as CT
from app.services import to_chuc_kd as TC

GOC = Path(__file__).resolve().parents[1]


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten, vai="nv_kd"):
    u = User(username=ten, full_name=ten, role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _co_cau(db):
    """Chi nhánh CT → phòng CT-P → hai team. Trả về (hcns, ct, phong, team1, team2)."""
    hc = _u(db, "hcns", "hcns")
    d1 = dt.date(2026, 1, 1)
    ct = TC.tao_don_vi(db, hc, "CT", "Chi nhánh Cần Thơ", "chi_nhanh", hieu_luc_tu=d1)
    p = TC.tao_don_vi(db, hc, "CT-P", "Phòng KDL", "phong", cha_id=ct.id, hieu_luc_tu=d1)
    t1 = TC.tao_don_vi(db, hc, "CT-T1", "Team 1", "team", cha_id=p.id, hieu_luc_tu=d1)
    t2 = TC.tao_don_vi(db, hc, "CT-T2", "Team 2", "team", cha_id=p.id, hieu_luc_tu=d1)
    db.commit()
    return hc, ct, p, t1, t2


# ═════════════════════════════ MỘT NƠI NHẬN, KHÔNG HAI ═════════════════════════════

def test_chi_tieu_phai_co_dung_mot_noi_nhan():
    """Cả hai rỗng, hoặc cả hai điền — đều bị chặn. Đây là phép chặn DUY NHẤT: ràng buộc ở cơ sở dữ
    liệu chỉ chặn trùng ô, nó không biết gì về luật "đúng một nơi nhận"."""
    db = _db()
    hc, ct, p, t1, _ = _co_cau(db)
    nv = _u(db, "nv1")
    with pytest.raises(ValueError, match="ĐÚNG MỘT"):
        CT.dat(db, hc, "2026-10", 1_000, don_vi_id=None, user_id=None)
    with pytest.raises(ValueError, match="ĐÚNG MỘT"):
        CT.dat(db, hc, "2026-10", 1_000, don_vi_id=t1.id, user_id=nv.id)


def test_khong_giao_chi_tieu_cho_don_vi_da_dong():
    """Một chỉ tiêu giao cho đơn vị đã đóng là con số không ai thực hiện, mà vẫn cộng vào tổng của
    phòng cha — phòng ấy vĩnh viễn không đạt, vì một lý do không nhìn ra khi đọc bảng."""
    db = _db()
    hc, ct, p, t1, _ = _co_cau(db)
    TC.dong_don_vi(db, hc, t1.id, dt.date(2026, 9, 30), "gộp vào Team 2")
    db.commit()
    with pytest.raises(ValueError, match="đã đóng"):
        CT.dat(db, hc, "2026-10", 1_000, don_vi_id=t1.id)
    # Kỳ mà đơn vị CÒN hiệu lực thì vẫn giao được — đóng từ 30/9 nên tháng 9 vẫn hợp lệ.
    assert CT.dat(db, hc, "2026-09", 1_000, don_vi_id=t1.id).muc_tieu == 1_000


def test_khong_giao_chi_tieu_cho_tai_khoan_da_khoa():
    db = _db()
    hc, *_ = _co_cau(db)
    nv = _u(db, "nv_khoa")
    nv.active = False
    db.commit()
    with pytest.raises(ValueError, match="bị khoá"):
        CT.dat(db, hc, "2026-10", 1_000, user_id=nv.id)


# ═════════════════════════════ TRÙNG Ô — RỖNG KHÁC RỖNG ═════════════════════════════

def test_giao_lai_cung_mot_o_thi_DE_LEN_chu_khong_them_dong():
    """Chỗ nguy hiểm số 3 ở đầu tệp: ràng buộc duy nhất KHÔNG bắt được, vì `don_vi_id` rỗng."""
    db = _db()
    hc, *_ = _co_cau(db)
    nv = _u(db, "nv1")
    TC.phan_cong(db, hc, nv.id, _co_cau_team(db), "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    CT.dat(db, hc, "2026-10", 1_000, user_id=nv.id)
    CT.dat(db, hc, "2026-10", 2_000, user_id=nv.id, ly_do="anh Tuấn duyệt nâng")
    db.commit()
    ds = db.query(ChiTieuKD).filter(ChiTieuKD.user_id == nv.id, ChiTieuKD.ky == "2026-10").all()
    assert len(ds) == 1, f"Đè lên ô cũ phải còn MỘT dòng, đang có {len(ds)}"
    assert ds[0].muc_tieu == 2_000
    assert ds[0].so_lan_sua == 1
    assert "duyệt nâng" in ds[0].ly_do_sua


def _co_cau_team(db):
    """Team đầu tiên trong kho — dùng cho những phép thử chỉ cần MỘT chỗ để phân công."""
    from app.models.to_chuc_kd import DonViKD
    return db.query(DonViKD).filter(DonViKD.cap == "team").first().id


def test_de_len_so_da_giao_thi_bat_buoc_ghi_ly_do():
    """Cuối kỳ sẽ có người hỏi vì sao chỉ tiêu đổi, và lúc ấy không còn ai nhớ."""
    db = _db()
    hc, *_ = _co_cau(db)
    CT.dat(db, hc, "2026-10", 1_000, don_vi_id=_co_cau_team(db))
    db.commit()
    with pytest.raises(ValueError, match="lý do"):
        CT.dat(db, hc, "2026-10", 2_000, don_vi_id=_co_cau_team(db))


def test_lan_dau_giao_thi_KHONG_doi_ly_do():
    """Bắt ghi lý do ngay lần đầu là bắt người ta gõ một câu vô nghĩa — và một ô bắt buộc mà ai cũng
    gõ bừa thì về sau không ai đọc nữa, kể cả những lần đáng đọc."""
    db = _db()
    hc, *_ = _co_cau(db)
    ct = CT.dat(db, hc, "2026-10", 1_000, don_vi_id=_co_cau_team(db))
    assert ct.muc_tieu == 1_000 and ct.so_lan_sua == 0


def test_hai_luong_khac_nhau_la_hai_o_khac_nhau():
    """Một team nhận chỉ tiêu riêng cho tour lẻ và riêng cho dịch vụ lẻ — hai dòng, không phải đè."""
    db = _db()
    hc, *_ = _co_cau(db)
    tid = _co_cau_team(db)
    CT.dat(db, hc, "2026-10", 1_000, don_vi_id=tid, luong="le")
    CT.dat(db, hc, "2026-10", 300, don_vi_id=tid, luong="dich_vu_le")
    db.commit()
    assert db.query(ChiTieuKD).filter(ChiTieuKD.don_vi_id == tid).count() == 2


def test_tat_ca_la_mot_gia_tri_that_khong_phai_tong_ba_luong():
    """`tat_ca` nghĩa là "một con số chung cho mọi luồng". Cộng nó với ba luồng kia là đếm hai lần —
    phép thử này ghim rằng nó nằm trong danh sách hợp lệ, để không ai gỡ đi rồi tự cộng."""
    assert set(LUONG_CHI_TIEU) == {"le", "doan", "dich_vu_le", "tat_ca"}


# ═════════════════════════════ KỲ VÀ SỐ ═════════════════════════════

@pytest.mark.parametrize("ky", ["2026-9", "26-09", "2026/09", "", "2026-13", "thang muoi"])
def test_ky_sai_dang_bi_chan(ky):
    """'2026-9' một chữ số thì sắp xếp chuỗi ra sai thứ tự và không ai thấy cho tới lúc in báo cáo."""
    db = _db()
    hc, *_ = _co_cau(db)
    with pytest.raises(ValueError):
        CT.dat(db, hc, ky, 1_000, don_vi_id=_co_cau_team(db))


def test_chi_tieu_am_bi_chan():
    db = _db()
    hc, *_ = _co_cau(db)
    with pytest.raises(ValueError, match="âm"):
        CT.dat(db, hc, "2026-10", -1, don_vi_id=_co_cau_team(db))


def test_chi_tieu_bang_khong_van_ghi_duoc():
    """0 KHÁC bỏ ô: 0 nghĩa là "không được giao đồng nào", bỏ ô nghĩa là "nơi này không nhận chỉ
    tiêu kỳ này". Hai câu khác nhau, màn hình hiện khác nhau."""
    db = _db()
    hc, *_ = _co_cau(db)
    ct = CT.dat(db, hc, "2026-10", 0, don_vi_id=_co_cau_team(db))
    assert ct.muc_tieu == 0


def test_xoa_o_khac_han_dat_ve_khong():
    db = _db()
    hc, *_ = _co_cau(db)
    tid = _co_cau_team(db)
    ct = CT.dat(db, hc, "2026-10", 1_000, don_vi_id=tid)
    db.commit()
    with pytest.raises(ValueError, match="lý do"):
        CT.xoa(db, hc, ct.id, "")
    CT.xoa(db, hc, ct.id, "team giải thể giữa kỳ")
    db.commit()
    assert db.query(ChiTieuKD).filter(ChiTieuKD.don_vi_id == tid).count() == 0


# ═════════════════════════════ PHẠM VI — RỖNG KHÁC None ═════════════════════════════

def test_danh_sach_pham_vi_None_khac_han_pham_vi_rong():
    """Chỗ nguy hiểm số 2 ở đầu tệp. `None` = xem tất cả; RỖNG = chưa phân công nên không thấy gì.
    Viết `if not don_vi_ids` là biến người chưa phân công thành người xem được cả công ty."""
    db = _db()
    hc, ct, p, t1, _ = _co_cau(db)
    CT.dat(db, hc, "2026-10", 1_000, don_vi_id=t1.id)
    db.commit()
    assert len(CT.danh_sach(db, "2026-10", None)) == 1, "None phải là XEM TẤT CẢ"
    assert CT.danh_sach(db, "2026-10", []) == [], "danh sách rỗng phải là KHÔNG THẤY GÌ"
    assert len(CT.danh_sach(db, "2026-10", [t1.id])) == 1


def test_chi_tieu_cua_mot_nguoi_thuoc_pham_vi_don_vi_cua_nguoi_ay():
    """Chỉ tiêu giao thẳng cho một người vẫn phải bị cắt theo đơn vị của người ấy, nếu không thì
    Trưởng phòng A đọc được chỉ tiêu của nhân viên phòng B."""
    db = _db()
    hc, ct, p, t1, t2 = _co_cau(db)
    a = _u(db, "nv_a"); b = _u(db, "nv_b")
    TC.phan_cong(db, hc, a.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    TC.phan_cong(db, hc, b.id, t2.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    CT.dat(db, hc, "2026-10", 1_000, user_id=a.id)
    CT.dat(db, hc, "2026-10", 2_000, user_id=b.id)
    db.commit()
    chi_t1 = CT.danh_sach(db, "2026-10", [t1.id])
    assert [r["ma_noi_nhan"] for r in chi_t1] == ["nv_a"]


def test_tra_cuu_tra_ve_khoa_doc_duoc_trong_json():
    db = _db()
    hc, ct, p, t1, _ = _co_cau(db)
    nv = _u(db, "nv1")
    TC.phan_cong(db, hc, nv.id, t1.id, "nhan_vien", dt.date(2026, 1, 1))
    db.commit()
    CT.dat(db, hc, "2026-10", 5_000, don_vi_id=t1.id, luong="le")
    CT.dat(db, hc, "2026-10", 800, user_id=nv.id, luong="tat_ca")
    db.commit()
    b = CT.tra_cuu(db, "2026-10")
    assert b["don_vi"][f"{t1.id}|le"] == 5_000
    assert b["nguoi"][f"{nv.id}|tat_ca"] == 800


# ═════════════════════════════ RANH GIỚI 09/9 — KHÔNG TỰ SINH SỐ ═════════════════════════════

def test_khong_co_ham_nao_suy_chi_tieu_tu_thuc_hien():
    """Ranh giới 09/9/2026: Claude viết CẤU TRÚC, không nhập SỐ LIỆU.

    Đọc bằng cây cú pháp chứ không tìm chuỗi: lớp dịch vụ chỉ tiêu không được nhập `Booking` hay
    `Tour`. Suy chỉ tiêu từ thực hiện kỳ trước thì tháng nào bán kém, tháng sau chỉ tiêu tự hạ
    xuống — thước đo thành cái bóng của chính số bị đo, mà không ai thấy gì bất thường.
    """
    cay = ast.parse((GOC / "app" / "services" / "chi_tieu_kd.py").read_text(encoding="utf-8"))
    nhap = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom):
            nhap.update(a.name for a in n.names)
        elif isinstance(n, ast.Import):
            nhap.update(a.name for a in n.names)
    cam = nhap & {"Booking", "Tour", "doanh_thu_kd"}
    assert not cam, (
        f"services/chi_tieu_kd.py nhập {sorted(cam)} — chỉ tiêu là điều NGƯỜI TA QUYẾT ĐỊNH, "
        "không phải điều hệ thống đo được. Suy nó từ thực hiện là biến thước đo thành cái bóng "
        "của chính số bị đo.")


def test_ban_nang_cap_khong_chen_mot_dong_chi_tieu_nao():
    """Bản alembic chỉ tạo bảng RỖNG. Một dòng `op.bulk_insert` hay `INSERT` ở đây là Claude nhập
    số hộ người dùng — đúng thứ ranh giới 09/9 cấm."""
    tep = list((GOC / "alembic" / "versions").glob("tc76*.py"))
    assert len(tep) == 1, f"Phải có đúng một bản nâng cấp TC-76, thấy {[t.name for t in tep]}"
    s = tep[0].read_text(encoding="utf-8")
    for xau in ("bulk_insert", "INSERT INTO", "insert().values"):
        assert xau not in s, f"Bản nâng cấp TC-76 có '{xau}' — bản nâng cấp không phải chỗ nhập số."


def test_bang_chi_tieu_da_duoc_khai_la_co_cua_nhap_tay():
    """Lần trước bảng này bị rút khỏi TC-74 vì chưa có cửa. Phép thử ghim rằng lần này nó CÓ."""
    from app.services import ks_cua_nhap as KS
    assert "chi_tieu_kd" in KS.CUA_TAY, (
        "Bảng `chi_tieu_kd` phải được khai là có cửa nhập tay. Một bảng không có cửa là việc CÒN "
        "THIẾU — ranh giới 09/9.")


def test_man_hinh_kinh_doanh_le_co_trong_cay_phan_he():
    """`test_khong_man_hinh_nao_cua_menu_bi_rot_khoi_cay` bắt chiều ngược lại; đây là chiều xuôi,
    để một màn hình có cửa mà quên treo vào cây cũng bị bắt."""
    s = (GOC.parent / "web" / "lib" / "cay_phan_he.ts").read_text(encoding="utf-8")
    assert '"/kinh-doanh-le"' in s


def test_kinh_doanh_le_KHONG_duoc_khai_la_nhanh_dung_chung():
    """Nhánh dùng chung đã tăng BA → BỐN → NĂM trong ba vòng liên tiếp, và
    `test_nam_nhanh_dung_chung_dung_la_nam_nhanh_da_chot` ghi rõ nhánh thứ sáu không nên đi tiếp
    đường ấy. Đây là nhánh thứ sáu, và nó cố ý RIÊNG cho Kinh doanh lẻ.

    Phép thử này tồn tại để lần sau ai định thêm `chung: true` cho tiện thì vấp vào lời giải thích,
    chứ không phải vấp vào một con số đếm không nói gì.
    """
    s = (GOC.parent / "web" / "lib" / "cay_phan_he.ts").read_text(encoding="utf-8")
    dong = [d for d in s.splitlines() if '"/kinh-doanh-le"' in d and "ma:" in d]
    assert len(dong) == 1, f"Phải có đúng một mục menu cho /kinh-doanh-le, thấy {len(dong)}"
    assert "chung: true" not in dong[0], (
        "Mục 3.8 cố ý KHÔNG dùng chung hai phòng. Kinh doanh Đoàn sẽ có mục riêng khi bản bàn giao "
        "KDĐ về, vì hai phòng đọc hai bảng chỉ tiêu khác nhau — treo chung thì người phòng Đoàn bấm "
        "vào và thấy số phòng Lẻ.")


# ═════════════════════════════ CỬA API — SEC-02 ═════════════════════════════

def test_cua_api_khong_nhan_pham_vi_tu_trinh_duyet():
    """SEC-02: phép cắt dòng nằm TRÊN MÁY CHỦ, trong truy vấn. Một tham số `pham_vi` hay `tat_ca`
    trên cửa HTTP là cho người gọi tự chọn xem bao nhiêu — đúng thứ SEC-02 cấm.

    Đọc bằng cây cú pháp: duyệt THAM SỐ của từng hàm cửa, chứ không tìm chuỗi trong cả tệp (chuỗi
    thì một dòng chú thích nhắc tên tham số cũng làm phép thử đỏ oan).
    """
    cay = ast.parse((GOC / "app" / "api" / "v1" / "kinh_doanh.py").read_text(encoding="utf-8"))
    xau = []
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ten = {a.arg for a in n.args.args + n.args.kwonlyargs}
            co = ten & {"pham_vi", "don_vi_ids", "tat_ca", "xem_tat_ca", "pham_vi_ids"}
            if co:
                xau.append(f"{n.name}({', '.join(sorted(co))})")
    assert not xau, (
        "Cửa API Kinh doanh nhận tham số phạm vi từ người gọi: " + "; ".join(xau) +
        ". SEC-02 đòi phạm vi được tính ở máy chủ từ phân công của chính người đăng nhập.")


def test_cua_don_vi_hoi_quyen_TRUOC_khi_doc():
    """Cửa `/don-vi/{id}` là chỗ dễ thủng nhất của vòng — nó nhận một id từ người gọi.

    Đòi hàm ấy tự nó gọi `duoc_xem`, đọc bằng cây cú pháp: tìm chuỗi trong cả tệp thì một hàm khác
    trong cùng tệp có gọi là đủ làm phép thử xanh — đúng kiểu báo an toàn giả.
    """
    cay = ast.parse((GOC / "app" / "api" / "v1" / "kinh_doanh.py").read_text(encoding="utf-8"))
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "mot_don_vi"), None)
    assert ham is not None, "Không tìm thấy hàm mot_don_vi() — cửa xem xuống một đơn vị"
    goi = {n.func.attr for n in ast.walk(ham)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "duoc_xem" in goi, (
        "mot_don_vi() phải tự gọi to_chuc_kd.duoc_xem trước khi đọc dữ liệu. Trả bảng rỗng thay vì "
        "403 làm người ta tưởng đơn vị ấy không bán được đồng nào.")


def test_cua_cua_toi_khong_nhan_user_id():
    """`/cua-toi` trả booking của CHÍNH người đăng nhập. Nhận thêm `user_id` là mở cho ai cũng đọc
    được doanh số của người khác chỉ bằng cách đổi một con số trên đường dẫn."""
    cay = ast.parse((GOC / "app" / "api" / "v1" / "kinh_doanh.py").read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "cua_toi")
    assert "user_id" not in {a.arg for a in ham.args.args + ham.args.kwonlyargs}


def test_giao_chi_tieu_hep_hon_xem():
    from app.api.v1 import kinh_doanh as API
    assert set(API.GIAO_CHI_TIEU) < set(API.XEM), "Nhóm giao chỉ tiêu phải hẹp hơn nhóm xem"
    assert "tp_kd" not in API.GIAO_CHI_TIEU, (
        "Trưởng phòng NHẬN chỉ tiêu, không tự giao cho mình.")
    assert "gd_kd" in API.GIAO_CHI_TIEU, (
        "Giám đốc Kinh doanh phải giao được chỉ tiêu — đó là việc chính của vai ấy. Khác với quyền "
        "BÁN (nguoi_ban_hang.GHI cố ý loại gd_kd ra): tự bật quyền bán cho mình là tự cấp doanh số, "
        "còn hạ chỉ tiêu của chính mình thì cấp trên nhìn thấy ngay trên cùng màn hình.")


def test_cua_kinh_doanh_dung_tien_to_rieng():
    """Gắn cửa mới vào một tiền tố rộng sẵn có là nới CẢ NHÓM cho mọi vai đang có nhóm ấy — phần dôi
    ra vẫn là quyền đã cấp. Đã trả giá bốn lần trong kho này."""
    from app.api.v1 import kinh_doanh as API
    assert API.router.prefix == "/api/v1/kinh-doanh"


def test_man_hinh_kinh_doanh_le_chi_goi_cua_cua_no():
    """Màn hình gọi thêm một tiền tố khác thì phép thử khai quyền sẽ bắt khai tiền tố ấy, và khai
    vào đây là cấp cả nhóm ấy cho mọi vai mở được màn hình này — TC-73 đã suýt vấp đúng chỗ."""
    from app.services.access import MAN_HINH_API
    assert MAN_HINH_API["/kinh-doanh-le"] == ("/api/v1/kinh-doanh",)


def test_bang_chi_tieu_khong_mang_cot_phien_ban():
    """Tiêu chí của `ghi_mot_lan.py` là "bản ghi mà NHIỀU NGƯỜI cùng sửa trong một kỳ". Chỉ tiêu do
    một người giao, mỗi kỳ một lần. Thêm cột khoá ở đây là thêm một cột KHÔNG AI ĐỌC — mà cột không
    ai đọc tệ hơn không có cột, vì nó làm người sau tin rằng chỗ ấy đã được canh."""
    assert "phien_ban" not in ChiTieuKD.__table__.columns


def test_bang_chi_tieu_khong_mang_cot_phap_nhan():
    """Pháp nhân của một chỉ tiêu là pháp nhân của đơn vị nhận — `don_vi_kd.company_id` đã giữ rồi.
    Chép sang đây là tạo chỗ thứ hai có thể nói khác, và ngày hai chỗ lệch thì không ai biết bên
    nào đúng."""
    assert "company_id" not in ChiTieuKD.__table__.columns
