# -*- coding: utf-8 -*-
"""NS-3 · Hồ sơ định danh, người phụ thuộc, và cột TNCN nói ra nó bỏ sót ai.

Bốn cửa máy chủ nằm im từ ngày viết, không một tệp nào trong `web/` gọi tới:
`GET/PUT /employees/{id}/profile`, `/hrm/profile-gaps`, `/dependents`, `/employees/{id}/pit-deduction`.

Hậu quả ĐO ĐƯỢC chứ không suy đoán: `pit_deduction()` chỉ được gọi từ đúng cửa API của chính nó —
người phụ thuộc không có cửa khai, nên mức giảm trừ gia cảnh của mọi người đều bằng mức bản thân, và
cả phép tính ấy là một nhánh chạy không tải suốt từ lúc viết.

Và cột TNCN trên bảng lương chỉ gồm 10% thù lao cộng tác viên: `services/hr.py` cộng TNCN đúng một
chỗ, còn người hợp đồng lao động đi qua `row(e)` với `tncn: 0.0`. Số 0 ấy chìm vào tổng "Khoản trừ"
và đọc ra thành "công ty khấu trừ bấy nhiêu". Vòng này KHÔNG tự bắt đầu tính thuế lũy tiến — việc
VTOS có tính hay để MISA tính là quyết định của Kế toán trưởng — nó làm chỗ thiếu ĐẾM ĐƯỢC.
"""
import os
import re
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ns3.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ns3.db"):
    os.remove("test_ns3.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal              # noqa: E402
from app.models.hr import Employee                   # noqa: E402
from app.models.hrm import Dependent                 # noqa: E402
from app.services import access as AC                # noqa: E402
from app.services import hrm as H                    # noqa: E402

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web"
TRANG = WEB / "app" / "hop-dong-lao-dong" / "page.tsx"
MH_LUONG = WEB / "components" / "HrScreens.tsx"
CAY = WEB / "lib" / "cay_phan_he.ts"

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _tep(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ------------------------------------------------- cửa phải có người với tới

def test_bon_cua_ho_so_deu_co_man_hinh_goi_toi():
    """Bốn cửa nằm im phải có ít nhất một màn hình gọi — đây là chỗ hỏng vòng này sinh ra để sửa.

    Hỏi theo ĐƯỜNG GỌI THẬT, không hỏi theo tên bảng: `ks_cua_nhap` đã biết bốn bảng ấy "được khai là
    có cửa nhập tay", và chính chỗ ấy là chỗ nó không bắt được. Cửa có trên máy chủ mà người phải dùng
    nó không với tới thì cửa ấy chưa tồn tại.
    """
    nguon = "".join(_tep(p) for p in list(WEB.rglob("*.tsx")) + list(WEB.rglob("*.ts"))
                    if "node_modules" not in str(p))
    # KHỚP THEO ĐƯỜNG ĐẦY ĐỦ, kết bằng dấu nháy đóng chuỗi hoặc tham số — KHÔNG dùng `"/x" in nguon`.
    # Đây là lần THỨ BA kiểu khớp lỏng ấy lọt qua: `"/lech-cong" in nguon` vẫn xanh khi đường đổi thành
    # `/lech-cong-tam`, `"DonNghiPhep" in mh` vẫn xanh khi gỡ thẻ JSX vì dòng `import` còn tên, và bản
    # đầu của chính phép thử này vẫn xanh khi `/pit-deduction` đổi thành `/pit-deduction-tam`. Một hàng
    # rào khớp theo khúc đầu là hàng rào trang trí: nó xanh đúng vào lúc đường gọi hỏng.
    for mau, viec in ((r'"/hrm/profile-gaps"', "đếm người còn thiếu hồ sơ"),
                      (r'/pit-deduction\?period=', "mức giảm trừ gia cảnh"),
                      (r'/dependents\?employee_id=', "sổ người phụ thuộc của một người")):
        assert re.search(mau, nguon), f"không màn hình nào gọi đúng cửa {mau} ({viec})"
    assert re.search(r'/employees/\$\{[^}]+\}/profile`', nguon), \
        "không màn hình nào gọi cửa hồ sơ định danh của một người"


def test_cua_ghi_ho_so_va_nguoi_phu_thuoc_that_su_bam_duoc():
    """Có cửa ĐỌC mà không cửa GHI thì vẫn là việc còn thiếu — đúng chỗ thẻ Chấm công của Đợt C vấp.

    Màn hình ấy in bảng chấm công mà không ô nào gọi `POST /attendance`, nên Nhân sự xem được chứ
    không chấm được. Phép thử này hỏi cả ba lối ghi của vòng NS-3, không chỉ lối đọc.
    """
    t = _tep(TRANG)
    assert re.search(r'method:\s*"PUT"', t), "màn hình chưa lưu được hồ sơ định danh"
    assert re.search(r'api\(\s*"/dependents"\s*,\s*\{\s*method:\s*"POST"', t), \
        "màn hình chưa thêm được người phụ thuộc"
    assert re.search(r'method:\s*"DELETE"', t), "màn hình chưa ngừng được một người phụ thuộc"


def test_khong_dung_them_mot_dong_nao_trong_ma_tran_quyen():
    """Hai cửa này phải sống trong phạm vi ĐÃ KHAI, không được nới thêm.

    `/hop-dong-lao-dong` khai sẵn `/api/v1/hrm`, `/api/v1/dependents` và `/api/v1/employees` từ trước.
    Dựng một trang mới cho cùng những cửa ấy là thêm một dòng vào ma trận quyền mà không thêm một
    quyền nào — thêm đúng một chỗ để hai bản khai lệch nhau. Phép thử giữ cho lần sửa sau không lặng
    lẽ tách ra trang riêng rồi khai lại.
    """
    khai = AC.MAN_HINH_API["/hop-dong-lao-dong"]
    for t in ("/api/v1/hrm", "/api/v1/dependents", "/api/v1/employees"):
        assert t in khai, f"/hop-dong-lao-dong thiếu khai {t}"
    assert "/cham-cong" in AC.MENU_ROLES, "mốc NS-2 biến mất"
    # Màn hình hồ sơ KHÔNG được mở rộng ra ngoài nhóm đã ký: dữ liệu cá nhân theo Nghị định 13/2023.
    assert set(AC.MENU_ROLES["/hop-dong-lao-dong"]) <= set(AC.BASE_VIEW) | {"hcns", "cntt"}, \
        "màn hình hồ sơ định danh bị mở rộng cho vai ngoài HCNS"


# ------------------------------------------------- cột TNCN phải nói ra nó bỏ sót ai

def test_man_hinh_luong_noi_ra_cot_tncn_bo_sot_ai():
    """Gỡ dòng này đi thì số 0 lại im lặng, và cái im lặng ấy chính là chỗ hỏng.

    So ĐƯỜNG ĐẦY ĐỦ kết bằng dấu nháy ngược — bài học kiểm ngược của NS-2: `"/tncn" in nguon` sẽ vẫn
    xanh khi ai đó đổi tên đường thành `/tncn-tam`, vì chuỗi cũ là khúc đầu của chuỗi mới.
    """
    nguon = _tep(MH_LUONG)
    assert re.search(r'/payroll-runs/\$\{period\}/tncn-con-thieu`', nguon), \
        "màn hình Lương chưa gọi đúng cửa tncn-con-thieu"
    assert "tncn.ghi_chu" in nguon, "khung phải IN RA câu máy chủ nói, không tự đặt lời"
    assert "tncn.so_nguoi_hdld_khong_tncn" in nguon, "khung chưa nói ra bao nhiêu người bị bỏ sót"


def test_khong_ai_lang_le_bat_dau_tinh_thue_luy_tien():
    """Chặn đúng điều vòng này CỐ Ý KHÔNG làm, và đỏ theo cả hai chiều.

    Tính thuế lũy tiến từng phần cho hơn trăm người là một quyết định có chữ ký của Kế toán trưởng,
    không phải một lần sửa cho tiện. Nếu một ngày nó được thêm thật thì phép thử này đỏ, để người sửa
    PHẢI quay lại viết lại `tncn_chua_tinh()` và khung trên màn hình — nếu không, màn hình sẽ còn nói
    "chưa tính TNCN cho người HĐLĐ" trong khi bảng lương đã khấu trừ của họ.
    """
    hr = (GOC / "backend" / "app" / "services" / "hr.py").read_text(encoding="utf-8")
    assert "pit_deduction" not in hr and "giam_tru_ban_than" not in hr, (
        "services/hr.py nay tính giảm trừ gia cảnh — nếu đây là quyết định của Kế toán trưởng thì phải "
        "sửa lại hrm.tncn_chua_tinh(), khung trên màn hình Lương, và chính phép thử này")
    # Thuế suất CTV vẫn là tham số, không chôn cứng.
    assert 'R.get_param(db, "hdv_tncn")' in hr, "thuế suất khấu trừ CTV bị chôn cứng vào mã"


# ------------------------------------------------- cây phân hệ phải nói đúng

def test_cay_phan_he_khong_con_khai_thieu_hon_thuc_te():
    """Bốn mục từng khai "chưa dựng" trong khi màn hình đã có — cây là bản đồ, bản đồ sai thì đi lạc."""
    cay = _tep(CAY)
    def _dong(ma: str) -> str:
        i = cay.index(f'ma: "{ma}"')
        return cay[i:cay.index("\n", i)]
    for ma in ("5.1", "4.10.4", "8.3.1", "4.10.5"):
        assert "href:" in _dong(ma), f"mục {ma} vẫn khai chưa dựng trong khi màn hình đã có"
    # 8.3.1 KHÔNG được mang tham số ?tab=: /access không đọc `?tab=` từ URL, nên liên kết sẽ sai thẻ.
    assert "?tab=" not in _dong("8.3.1"), \
        "/access không đọc ?tab= — đường dẫn có tham số mở đúng trang mà sai thẻ"
    # 5.1 thì ĐƯỢC, vì HrScreens đọc ?tab= thật.
    assert "get(\"tab\")" in _tep(MH_LUONG), "HrScreens thôi đọc ?tab= — mục 5.1 phải sửa theo"


# ------------------------------------------------- chạy thật

def _token(u: str = "hcns") -> str:
    r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_giam_tru_gia_canh_doi_theo_so_nguoi_phu_thuoc_that():
    """Gọi hàm thật: thêm một người phụ thuộc thì mức giảm trừ phải tăng đúng một suất.

    Soi mã nguồn bắt được chuyện ai đó xoá cửa đi, nhưng KHÔNG bắt được chuyện cửa còn nguyên mà phép
    tính phía sau không chạy tới — nhánh chết là loại hỏng đã xảy ra thật trong chính kho này.
    """
    with SessionLocal() as db:
        e = db.execute(select(Employee).where(Employee.active == True)).scalars().first()
        assert e is not None
        truoc = H.pit_deduction(db, e.id, "2026-10")
        db.add(Dependent(employee_id=e.id, full_name="Người thử NS3", relation="con",
                         from_period="2026-01", created_by="test"))
        db.commit()
        sau = H.pit_deduction(db, e.id, "2026-10")
        assert sau["dependents"] == truoc["dependents"] + 1
        assert round(sau["total"] - truoc["total"]) == round(truoc["dependent_rate"]), \
            f"thêm một người phụ thuộc mà mức giảm trừ không tăng đúng một suất: {truoc} → {sau}"


def test_cua_tncn_con_thieu_tra_loi_ca_khi_chua_co_bang_luong():
    """Kỳ chưa có bảng lương thì vẫn trả lời được, và phải NÓI RA là chưa có.

    Trả về rỗng ở đây là trả lời "không bỏ sót ai" cho một câu chưa ai hỏi — đúng loại im lặng làm
    người đọc yên tâm sai.
    """
    r = client.get("/api/v1/payroll-runs/1999-01/tncn-con-thieu",
                   headers={"Authorization": "Bearer " + _token()})
    assert r.status_code == 200, r.text
    kq = r.json()
    assert kq["co_bang_luong"] is False
    assert kq["so_nguoi_hdld_khong_tncn"] == 0
    assert "Kế toán trưởng" in kq["ghi_chu"], "cửa phải nói ra ai là người quyết"


def test_cua_ho_so_chan_dung_vai():
    """Đọc thì HR_READ, ghi thì HR_ADMIN — và một vai ngoài khối phải bị từ chối ở MÁY CHỦ.

    Màn hình đã ẩn nút Lưu với người không phải HCNS, nhưng ẩn là để đỡ rối chứ không phải để canh:
    hồ sơ định danh là dữ liệu cá nhân theo Nghị định 13/2023.
    """
    with SessionLocal() as db:
        e = db.execute(select(Employee).where(Employee.active == True)).scalars().first()
    # Tài khoản thật của bản demo, vai nv_kd — không tạo tài khoản mới: thêm một dòng vào
    # `seed.USERS` là đổi dữ liệu nền mà bốn làn cùng dùng, và vài phép thử đang đếm đúng số ấy.
    h = {"Authorization": "Bearer " + _token("kd.hoa")}
    assert client.get(f"/api/v1/employees/{e.id}/profile", headers=h).status_code == 403
    assert client.get(f"/api/v1/dependents?employee_id={e.id}", headers=h).status_code == 403
    assert client.put(f"/api/v1/employees/{e.id}/profile", headers=h, json={"phone": "0900000000"}).status_code == 403
