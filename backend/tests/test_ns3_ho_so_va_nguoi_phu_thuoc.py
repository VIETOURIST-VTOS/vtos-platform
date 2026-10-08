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


def test_cong_tac_bat_thue_luy_tien_khong_nam_trong_ma():
    """Phép thử này ĐÃ ĐỎ MỘT LẦN, đúng như nó được viết ra để làm — và đây là bản viết lại.

    Bản ngày 08/10/2026 (NS-3) chặn việc VTOS lặng lẽ bắt đầu khấu trừ thuế lũy tiến, bằng cách cấm
    `services/hr.py` nhắc tới `pit_deduction` hay `giam_tru_ban_than`. Cùng ngày Chủ tịch quyết
    "VTOS tính", nên vòng KY-1 dựng phép tính thật — và phép thử cũ sẽ VẪN XANH, vì phép tính mới
    gọi `thue_tncn.muc_giam_tru()` chứ không gọi hai cái tên bị cấm. Một hàng rào canh TÊN GỌI thì
    đổi tên là qua được; cho nên nó không canh gì cả.

    Bản này canh điều thật sự phải giữ: phép tính có sẵn thì được, nhưng NGÀY BẬT không được nằm
    trong mã. Lý do rất cụ thể — thuế của người HĐLĐ có thể đang được MISA khấu trừ, và hai nơi cùng
    trừ một khoản thì người lao động phát hiện ra vào ngày nhận lương. Bật là việc có bàn giao và có
    chữ ký, không phải một dòng mặc định.
    """
    from app.services import thue_tncn as T
    from app.services import rules as R
    mac_dinh = {k: v for k, v, *_ in R.DEFAULT_PARAMS}
    assert T.KY_TU_KY_KEY in mac_dinh, "công tắc thuế lũy tiến không có trong bộ tham số — không ai bật được"
    assert (mac_dinh[T.KY_TU_KY_KEY] or "").strip() == "", (
        "bộ tham số mặc định đã điền sẵn kỳ bật thuế lũy tiến. Điền sẵn một kỳ vào đó là ký thay "
        "Chủ tịch bằng một dòng mã — cùng lẽ với ngay_van_hanh_that đang để trống")

    hr = (GOC / "backend" / "app" / "services" / "hr.py").read_text(encoding="utf-8")
    assert "TNCN.da_bat(db, period)" in hr, (
        "services/hr.py cộng thuế lũy tiến mà không hỏi công tắc — tức nó bật sẵn cho mọi kỳ")
    # Thuế suất CTV vẫn là tham số, không chôn cứng.
    assert 'R.get_param(db, "hdv_tncn")' in hr, "thuế suất khấu trừ CTV bị chôn cứng vào mã"


def test_man_hinh_luong_doi_loi_theo_cong_tac_chu_khong_noi_mot_lo():
    """Khung TNCN phải đọc `da_bat` của máy chủ. Một khung chỉ biết một lời sẽ nói sai vào đúng ngày đổi."""
    nguon = _tep(MH_LUONG)
    # KIỂM NGƯỢC 08/10/2026: bản đầu của phép thử này chỉ hỏi `"tncn.da_bat" in nguon`, và nó VẪN XANH
    # khi tắt cứng nhánh "đã bật" — vì chuỗi ấy còn nằm trong nhánh `!tncn.da_bat` ngay dưới. Một hàng
    # rào canh sự CÓ MẶT của một chuỗi thì chỉ cần chuỗi ấy còn ở đâu đó là qua. Nên hỏi CẢ HAI nhánh.
    assert re.search(r'tncn\s*&&\s*tncn\.da_bat\s*&&', nguon), \
        "khung TNCN không có nhánh cho trạng thái ĐÃ BẬT — nó sẽ còn nói 'chưa tính' sau khi đã tính"
    assert re.search(r'tncn\s*&&\s*!tncn\.da_bat\s*&&', nguon), \
        "khung TNCN không có nhánh cho trạng thái CHƯA BẬT — nó sẽ nói đã khấu trừ trong khi chưa"
    assert "tncn.tham_so_lac_hau" in nguon, (
        "màn hình không in ra chỗ mức giảm trừ đang lạc hậu so với luật — Kế toán sẽ không biết phải đề xuất gì")


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
    # Đổi 08/10/2026 (KY-1): trước đây lời này nói "quyết định của Kế toán trưởng" vì VTOS chưa có
    # phép tính. Nay phép tính đã có và Chủ tịch đã quyết "VTOS tính", nên điều người đọc cần biết
    # không còn là AI quyết mà là PHẢI BẤM GÌ — tên tham số công tắc, và cửa nào mở nó.
    assert "tncn_luy_tien_tu_ky" in kq["ghi_chu"], "cửa phải nói ra bấm gì để bật, không chỉ nói chưa bật"
    assert "Tham số" in kq["ghi_chu"], "nói tên tham số mà không chỉ màn hình nào sửa được"


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
