# -*- coding: utf-8 -*-
"""HS-9 — MỖI TRƯỜNG CỬA NHẬN PHẢI CÓ MỘT Ô TRÊN MÀN HÌNH. Chủ tịch báo 17/10/2026.

Chủ tịch hỏi «đã có form đầy đủ cho HCNS tạo chưa». Soát ra năm chỗ thiếu, và cả năm cùng một
hình: **cửa máy chủ nhận trường ấy, màn hình không có ô cho nó**. Không phép thử nào của kho bắt
được, vì mọi phép thử đều đo phía máy chủ — cửa nhận đủ 17 trường thì cửa đúng, và nó đúng thật.
Chỗ hỏng nằm ở MỐI NỐI, đúng bài học vòng HS-8 vừa rút ra.

Hậu quả đo được, không phải suy đoán:

  · `start_date` (ngày vào làm) — 0 lần xuất hiện trong màn Nhân sự. Thâm niên, phép năm, BHXH và
    thuế đều đọc nó. Người tuyển giữa kỳ thì không ai gõ được ngày vào.
  · `code` (mã nhân viên) — biểu tạo không có ô, cửa luôn tự sinh `NS001`. Mã thật của công ty là
    SỐ TRÊN BẢNG LƯƠNG (114, 276), và chính nó nối `Employee.code` ↔ `User.staff_code`.
  · chín trường hồ sơ, trong đó có NGÀY CẤP và NƠI CẤP căn cước — màn «Hồ sơ nhân viên» HIỆN
    chúng ra, nên chúng trống vĩnh viễn và trông y hệt «người này chưa khai».
  · `allowance`, `annual_leave_days`, `note` của hợp đồng — hai trong ba nằm sẵn trong gói gửi đi
    mà chưa bao giờ có ô, nên mọi hợp đồng đã ghi đều có phụ cấp rỗng.

CÁCH ĐO PHẢI TÌM Ô NHẬP, KHÔNG PHẢI TÌM CHỮ. Lần soát đầu em chỉ tìm tên trường trong tệp .tsx và
bỏ sót `allowance`, `note` — chúng có mặt trong gói gửi đi nên chữ ấy khớp, mà ô nhập thì không
có. Phép thử dưới đây đòi tên trường phải xuất hiện trong một chỗ GẮN VÀO Ô: `value={f.x}`,
`setF({...f, x:` hoặc một khoá trong bảng khai ô.
"""
import os, re, sys, tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hs9.db")
for _f in (_DB, _DB + "-journal"):
    if os.path.exists(_f):
        try: os.remove(_f)
        except OSError: pass
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN_HD = os.path.join(GOC, "web", "app", "hop-dong-lao-dong", "page.tsx")
MAN_NS = os.path.join(GOC, "web", "components", "HrScreens.tsx")


def _doc(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def co_o_nhap(src: str, truong: str) -> bool:
    """Trường có được GẮN VÀO một ô nhập không — không chỉ là có mặt trong tệp."""
    t = re.escape(truong)
    mau = (
        rf'value=\{{[^}}]*\b{t}\b',          # value={f.x}  /  value={(fHs as any)[k]}
        rf'\.\.\.\s*\w+\s*,\s*{t}\s*:',       # setF({ ...f, x: ... })
        rf'\[\s*"{t}"\s*,',                   # bảng khai ô: ["x", "Nhãn"]
        rf'd\(\s*"{t}"',                      # d("x", ...) của biểu sửa
        rf'checked=\{{[^}}]*\b{t}\b',         # ô đánh dấu
    )
    return any(re.search(m, src) for m in mau)


def truong_model(tep: str, ten_lop: str) -> list[str]:
    s = _doc(os.path.join(GOC, "backend", tep))
    m = re.search(r"^class " + ten_lop + r"\(BaseModel\):(.*?)(?=^class |\Z)", s, re.S | re.M)
    assert m, f"Không tìm thấy lớp {ten_lop} trong {tep}"
    return re.findall(r"^\s{4}([a-z_][a-z0-9_]*)\s*:", m.group(1), re.M)


# ---------------------------------------------------------------------------------------------
# 1. Hồ sơ cá nhân — ĐỦ 17 TRƯỜNG
# ---------------------------------------------------------------------------------------------
def test_hs9_1_moi_truong_ho_so_deu_co_o_nhap():
    """`ProfileIn` nhận 17 trường. Màn «Hợp đồng lao động» phải có đủ 17 ô.

    Thêm một trường vào `ProfileIn` mà quên dựng ô thì đỏ ở đây — chứ không phải đỏ sáu tháng sau
    khi có người đi tìm ngày cấp căn cước để làm hồ sơ BHXH và thấy ô trống.
    """
    src = _doc(MAN_HD)
    tr = truong_model("app/api/v1/hrm.py", "ProfileIn")
    assert len(tr) >= 17, f"ProfileIn chỉ còn {len(tr)} trường — kiểm lại, phép thử này đang đo nhầm."
    thieu = [t for t in tr if not co_o_nhap(src, t)]
    assert not thieu, (
        f"{len(thieu)} trường hồ sơ KHÔNG CÓ Ô NHẬP trên màn Hợp đồng lao động: {thieu}.\n"
        "Màn «Hồ sơ nhân viên» hiện những trường ấy ra, nên thiếu ô nhập thì chúng trống vĩnh "
        "viễn và trông y hệt «người này chưa khai» — hai câu hoàn toàn khác nhau.")


# ---------------------------------------------------------------------------------------------
# 2. Hợp đồng lao động — mọi trường đều nhập được
# ---------------------------------------------------------------------------------------------
def test_hs9_2_moi_truong_hop_dong_deu_co_o_nhap():
    """`allowance` và `note` nằm trong gói gửi đi TỪ ĐẦU mà chưa bao giờ có ô, nên mọi hợp đồng đã
    ghi đều mang phụ cấp rỗng. `annual_leave_days` thì cửa mặc định 12 — một con số mặc định mà
    người ký không đổi được không phải là một thoả thuận."""
    src = _doc(MAN_HD)
    bo_qua = {"employee_id"}        # chọn từ danh sách nhân viên, không phải ô gõ tay
    tr = [t for t in truong_model("app/api/v1/hrm.py", "ContractIn") if t not in bo_qua]
    thieu = [t for t in tr if not co_o_nhap(src, t)]
    assert not thieu, f"Trường hợp đồng không có ô nhập: {thieu}"


# ---------------------------------------------------------------------------------------------
# 3. Hồ sơ nhân sự — biểu TẠO và biểu SỬA cùng một bộ câu hỏi
# ---------------------------------------------------------------------------------------------
# Khai thẳng những trường CỐ Ý không có ô, kèm lý do. Danh sách này là một lời hứa: mọi trường
# khác phải nhập được. Thêm trường mới vào `EmployeeIn` mà không khai ở đây thì đỏ.
KHONG_DUNG_O_DAY = {
    "phien_ban": "số bản màn hình đang cầm, máy tự gửi",
    "dieu_chuyen_tu_ngay": "ô riêng của khối điều chuyển, chỉ hiện khi đổi phòng/chức vụ",
    "dieu_chuyen_ly_do": "ô riêng của khối điều chuyển",
    "user_id": "nối hồ sơ với tài khoản — làm ở màn Tài khoản qua ô Mã nhân viên. Hai cửa cho "
               "cùng một mối nối là đúng thứ `services/quyen_ho_so.py` ra đời để dẹp",
    "card_type": "loại thẻ HDV suy từ số thẻ, phòng Hướng dẫn quản",
    "duties": "mô tả công việc — ô riêng ở khối Hướng dẫn viên",
    "active": "ngưng / mở lại hồ sơ là một NÚT trên dòng, không phải ô đánh dấu trong biểu. Cố ý: "
              "ngưng hồ sơ có hệ quả (ra khỏi bảng lương, kiểm tài xế đang lái xe) nên phải hỏi "
              "xác nhận, mà một ô tích thì bấm nhầm không ai biết",
}


def test_hs9_3_bieu_tao_va_bieu_sua_cung_mot_bo_cau_hoi():
    """Trước vòng này biểu tạo có 6 ô còn biểu sửa có 14: HCNS tạo xong phải bấm Sửa ngay để nhập
    tiếp, và bước thứ hai ấy thì ai cũng quên. Hai biểu cho cùng một hồ sơ thì phải hỏi cùng một
    bộ câu hỏi."""
    src = _doc(MAN_NS)
    tr = truong_model("app/api/v1/hr.py", "EmployeeIn")
    thieu = [t for t in tr if t not in KHONG_DUNG_O_DAY and not co_o_nhap(src, t)]
    assert not thieu, (
        f"Trường của hồ sơ nhân sự không có ô nhập ở màn Nhân sự: {thieu}.\n"
        "Nếu CỐ Ý không dựng ô thì khai vào `KHONG_DUNG_O_DAY` kèm lý do — im lặng bỏ qua thì "
        "người sau không phân biệt được 'đã cân nhắc' với 'quên'.")
    thua = [t for t in KHONG_DUNG_O_DAY if t not in tr]
    assert not thua, f"`KHONG_DUNG_O_DAY` khai {thua} mà `EmployeeIn` không còn trường ấy — dọn đi."


def test_hs9_4_ngay_vao_lam_phai_nhap_duoc():
    """Tách riêng vì đây là trường nặng nhất: thâm niên, phép năm, BHXH và thuế đều đọc nó, mà
    trước vòng này nó xuất hiện ĐÚNG 0 LẦN trong cả màn Nhân sự."""
    src = _doc(MAN_NS)

    # ĐO TỪNG BIỂU MỘT, không đếm số lần xuất hiện. Bản đầu của phép thử này đòi
    # `src.count("start_date") >= 3` — và phép kiểm ngược cho thấy nó VÔ DỤNG: bỏ hẳn ô ở biểu
    # sửa thì riêng biểu tạo đã có năm lần nhắc tên trường, nên vẫn xanh. Một phép thử đếm chữ
    # thì đo được độ dài của mã, không đo được điều nó nói là đang canh.
    assert re.search(r'fEmp\.start_date', src), (
        "Biểu TẠO không có ô «Ngày vào làm» — người tuyển giữa kỳ không gõ được ngày vào ngay "
        "lúc tạo, và bước nhập bù sau thì ai cũng quên.")
    assert re.search(r'd\(\s*"start_date"', src), (
        "Biểu SỬA không có ô «Ngày vào làm» — nhập sai một lần là không chữa được trên màn hình.")


# ---------------------------------------------------------------------------------------------
# 4. Mã nhân viên: cửa phải nhận, và không cho trùng
# ---------------------------------------------------------------------------------------------
def test_hs9_5_cua_tao_nhan_ma_nhan_vien_va_chan_trung():
    """Mã thật của công ty là SỐ TRÊN BẢNG LƯƠNG HCNS, và nó là khoá nối `Employee.code` ↔
    `User.staff_code`. Cửa luôn tự sinh `NS###` nghĩa là người tạo qua biểu mẫu mang mã khác hệ,
    không khớp bảng lương, và lần nạp `import-master` sau coi họ là người mới."""
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.main import app
    from app.models.core import User

    from app.api.v1.hr import EmployeeIn
    assert "code" in EmployeeIn.model_fields, "Cửa tạo hồ sơ không nhận mã nhân viên."

    MK = "hs9_123456"
    with TestClient(app) as c:
        db = SessionLocal()
        if db.execute(select(User).where(User.username == "hs9_hcns")).scalars().first() is None:
            db.add(User(username="hs9_hcns", full_name="Thu HCNS", role="hcns",
                        department="hcns", password_hash=hash_password(MK), active=True))
            db.commit()
        db.close()
        r = c.post("/api/v1/auth/login", data={"username": "hs9_hcns", "password": MK})
        assert r.status_code == 200, r.text
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        than = {"full_name": "Nguyen Van Thu HS9", "department": "kd_le", "position": "nv"}

        # (a) có mã thì DÙNG ĐÚNG mã ấy, không tự sinh
        r1 = c.post("/api/v1/employees", headers=h, json={**than, "code": "HS9777"})
        assert r1.status_code == 201, r1.text
        assert r1.json()["employee"]["code"] == "HS9777", (
            f"Gửi mã HS9777 mà hồ sơ mang mã {r1.json()['employee']['code']} — cửa vẫn tự sinh.")

        # (b) mã trùng thì TỪ CHỐI, không lặng lẽ tạo hồ sơ thứ hai cùng mã
        r2 = c.post("/api/v1/employees", headers=h, json={**than, "code": "HS9777"})
        assert r2.status_code == 422, (
            f"Mã trùng mà cửa vẫn nhận (mã {r2.status_code}) — hai hồ sơ cùng mã thì bảng lương "
            "và tài khoản không biết trỏ vào ai.")

        # (c) để trống thì vẫn tự sinh như cũ — không bắt buộc, vì có lúc chưa biết mã
        r3 = c.post("/api/v1/employees", headers=h, json={**than, "full_name": "Nguyen Van Thu HS9b"})
        assert r3.status_code == 201, r3.text
        assert r3.json()["employee"]["code"], "Để trống mã mà cửa không tự sinh."


def test_hs9_6_cua_sua_khong_doi_duoc_ma():
    """Đổi mã của một hồ sơ ĐANG CHẠY là cắt mối nối với tài khoản và với mọi dòng lương đã tính
    dưới mã cũ. Nhận mã ở cửa tạo là một chuyện; nhận ở cửa sửa là chuyện khác, cần quyết định
    riêng. Phép thử này giữ ranh giới ấy."""
    import inspect
    from app.api.v1 import hr as HR

    nguon = inspect.getsource(HR.update_employee)
    assert '"code"' not in nguon and "'code'" not in nguon, (
        "`update_employee` đụng tới `code`. Nếu thật sự muốn cho sửa mã thì phải kèm việc dời "
        "`User.staff_code` và soát lại các kỳ lương cũ — không làm lặng lẽ ở đây.")
