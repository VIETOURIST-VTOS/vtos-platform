# -*- coding: utf-8 -*-
"""NS-2 · Bảng chấm công có màn hình, đơn nghỉ mở cho cả mười một phòng, và con số công nói ra chỗ lệch.

Vòng này sinh ra từ BA chỗ hỏng cùng một họ — **máy chủ mở đường mà người không với tới** — và hai
lời khai SAI trong chính tài liệu của phân hệ:

  1. `attendance_days` được khai "có cửa nhập tay" trong bộ kiểm 09/9, mà ra cả thư mục `web/` thì
     KHÔNG MỘT TỆP NÀO gọi `/attendance`. Bộ kiểm ấy chỉ biết bảng ĐÃ ĐƯỢC KHAI; chính docstring của
     nó nói trước điều đó và nói "chỗ đó do K12 gác". K12 đối chiếu ma trận quyền với thư mục trang —
     nó không hỏi câu ấy. Không ai gác.
  2. `POST /leaves` nhận đơn của bất kỳ ai đăng nhập, nhưng ô bấm chỉ có trên /xe-hdv. Chín phòng
     không có đường vào.
  3. Bảng chấm công và bảng lương là HAI nguồn và chỉ MỘT nguồn trả tiền: đơn nghỉ đã duyệt ghi vào
     `attendance_days`, bảng lương đọc `inputs["cong_thuc_te"]` HCNS gõ tay, và không một dòng nào
     trong `services/hr.py` đọc `AttendanceDay`. Docstring đầu `services/hrm.py` thì khai ngược lại.

PHÉP THỬ ĐẮT NHẤT TRONG TỆP là `test_o_dem_cong_du_tong_so_dong` — nó không biết chỗ hỏng nằm ở đâu,
nó chỉ hỏi "các ô đếm có cộng đủ số dòng không", đúng khuôn phép thử đã bắt được vụ mười một chiếc xe
biến mất khỏi ô đếm ngày 07/10/2026.
"""
import os
import re
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ns2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ns2.db"):
    os.remove("test_ns2.db")

from datetime import date                            # noqa: E402
import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal              # noqa: E402
from app.models.core import ROLES                    # noqa: E402
from app.models.hr import Employee                   # noqa: E402
from app.models.hrm import AttendanceDay, ATT_KINDS  # noqa: E402
from app.services import access as AC                # noqa: E402
from app.services import hrm as H                    # noqa: E402
from app.services import luong as L                  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web"
TRANG_CC = WEB / "app" / "cham-cong" / "page.tsx"
TP_DON = WEB / "components" / "DonNghiPhep.tsx"
TP_LUOI = WEB / "components" / "LuoiChamCong.tsx"
MH_LUONG = WEB / "components" / "HrScreens.tsx"

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _tep(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ----------------------------------------------------------------- ma trận quyền

def test_moi_nhan_vien_du_vai_nguoi_va_khong_vai_robot():
    """`MOI_NHAN_VIEN` phải bằng ĐÚNG tập vai của NGƯỜI — không thiếu ai, không lọt một robot nào.

    Hai chiều, hai loại sai khác hẳn nhau. Thiếu một vai: người của phòng ấy mở màn hình ra nhận 403
    và không gửi được đơn nghỉ — đúng cái hỏng vòng này sinh ra để sửa, chỉ là nhỏ hơn nên lâu hơn
    mới có người thấy. Lọt một vai robot: một tài khoản máy có mục menu đơn từ, và ngày nào đó có
    người tưởng robot đang chờ ký đơn của ai.

    Tính TẠI CHỖ từ `ROLES` chứ không viết con số 22 vào đây: viết số thì ngày thêm vai thứ 23 phép
    thử đỏ mà không nói được thiếu ai, và người sửa sẽ sửa con số.
    """
    cua_nguoi = {r for r in ROLES if not r.startswith("robot")}
    thieu = cua_nguoi - set(AC.MOI_NHAN_VIEN)
    thua = set(AC.MOI_NHAN_VIEN) - cua_nguoi
    assert not thieu, f"vai của người chưa gửi được đơn nghỉ: {sorted(thieu)}"
    assert not thua, f"MOI_NHAN_VIEN có vai không phải của người: {sorted(thua)}"
    assert len(AC.MOI_NHAN_VIEN) == len(set(AC.MOI_NHAN_VIEN)), "MOI_NHAN_VIEN có tên trùng"


def test_man_hinh_cham_cong_khai_du_hai_bang_va_khong_khai_thua():
    """Màn hình mới phải khai ở CẢ HAI bảng, và mọi tiền tố khai ra phải có người gọi thật.

    Khai thiếu `MENU_ROLES`: theo quy ước "trang không liệt kê thì ai đăng nhập cũng thấy", màn hình
    không bị khoá lại mà MỞ TOANG. Khai thừa ở `MAN_HINH_API`: phạm vi vai trò cộng ra từ bảng ấy,
    nên một tiền tố không ai gọi là một lần nới quyền thật — và nó làm bảng phân quyền trông đầy đủ
    hơn thực tế, đúng chỗ hỏng mà chính vòng này đi tìm.
    """
    assert "/cham-cong" in AC.MENU_ROLES, "/cham-cong chưa khai trong MENU_ROLES → màn hình mở toang"
    assert "/cham-cong" in AC.MAN_HINH_API, "/cham-cong chưa khai trong MAN_HINH_API"
    # Hợp của hai nhóm, không phải một: `MOI_NHAN_VIEN` là nhóm của NGƯỜI, còn `READ_ALL` mang
    # `robot_ks` — vai mà `test_ma_tran_quyen` đòi có mặt ở mọi dòng, vì robot Kiểm soát không soi
    # được màn hình nó không thấy. Robot không nằm trong nhóm người: nó không nghỉ phép.
    assert set(AC.MENU_ROLES["/cham-cong"]) == set(AC.MOI_NHAN_VIEN) | set(AC.READ_ALL), \
        "màn hình đơn nghỉ phải mở cho mọi người làm việc ở đây (MOI_NHAN_VIEN) cộng nhóm đọc toàn hệ"
    # ĐỌC CẢ CÁC THÀNH PHẦN TRANG NÀY NHẬP VÀO, không chỉ hai tệp viết tay.
    #
    # Sửa 09/10/2026, và lý do đáng ghi: bản cũ ghim đúng `page.tsx` + `DonNghiPhep.tsx`. Ngày màn
    # hình mọc thêm một khối — khối "Đánh giá của tôi" của mục 5.6 — thì cửa mới nằm trong thành
    # phần thứ ba và hàng rào đỏ, dù màn hình gọi cửa ấy thật. Một hàng rào đỏ vì người ta làm
    # ĐÚNG sẽ bị sửa cho hết đỏ, và lần sửa ấy thường là nới chỗ nó đang canh. Nên nó đi THEO
    # dòng `import ... from "@/components/..."` của chính trang, và giữ nguyên câu hỏi cũ: mọi
    # tiền tố khai cho màn hình này phải có người gọi thật.
    import re as _re
    nguon = _tep(TRANG_CC) + _tep(TP_DON)
    for ten in _re.findall(r'from "@/components/([A-Za-z0-9_]+)"', _tep(TRANG_CC)):
        tp = WEB / "components" / f"{ten}.tsx"
        if tp.exists():
            nguon += _tep(tp)
    for tien_to in AC.MAN_HINH_API["/cham-cong"]:
        duong = tien_to.replace("/api/v1", "")
        assert duong in nguon, f"khai {tien_to} cho /cham-cong mà màn hình không gọi tới"


# ------------------------------------------------- cửa nhập tay phải có người với tới

def test_bang_cham_cong_co_man_hinh_goi_toi():
    """Cửa `/attendance` phải có một màn hình GHI vào được — đây là chỗ không ai gác trước 08/10/2026.

    `ks_cua_nhap` biết bảng `attendance_days` đã được KHAI là có cửa nhập tay; nó không biết màn hình
    còn sống hay chưa bao giờ có. K12 đối chiếu ma trận quyền với thư mục trang; nó cũng không hỏi câu
    này. Nên câu hỏi ấy hỏi ở đây, và hỏi hẹp đúng một bảng thay vì dựng một bộ quét cả hệ thống —
    bản quét ấy đã thử và cho kết quả không dùng được (xem lệnh giao việc NS-2).
    """
    goi = [p for p in list(WEB.rglob("*.tsx")) + list(WEB.rglob("*.ts"))
           if "node_modules" not in str(p) and "/attendance" in _tep(p)]
    assert goi, "không màn hình nào gọi /attendance → bảng chấm công không có cửa nhập"
    ghi = [p for p in goi if re.search(r'api\(\s*"/attendance"\s*,\s*\{\s*method:\s*"POST"', _tep(p))]
    assert ghi, "có màn hình ĐỌC /attendance mà không màn hình nào GHI được – cửa nhập vẫn còn thiếu"


def test_don_nghi_dung_mot_thanh_phan_khong_hai_ban_chep():
    """Khung gửi đơn nghỉ chỉ được sống ở MỘT tệp.

    Chép nó sang màn hình thứ hai thì hôm nay giống nhau từng chữ và lệch nhau ở lần sửa thứ nhất.
    Lúc ấy người của phòng này đọc một bộ luật, người của phòng kia đọc một bộ khác, mà cả hai đều
    tin mình đang xem cùng một màn hình. Đếm theo lời gọi GHI `POST /leaves`, không đếm chữ "nghỉ
    phép": một màn hình chỉ ĐỌC danh sách đơn thì không phải một bản chép.
    """
    chep = [p for p in list(WEB.rglob("*.tsx")) + list(WEB.rglob("*.ts"))
            if "node_modules" not in str(p)
            and re.search(r'api\(\s*"/leaves"\s*,\s*\{\s*method:\s*"POST"', _tep(p))]
    assert [p.name for p in chep] == ["DonNghiPhep.tsx"], \
        f"cửa gửi đơn nghỉ phải nằm ở đúng một thành phần dùng chung, đang thấy: {[p.name for p in chep]}"
    # Hỏi THẺ JSX, không hỏi tên tệp: dòng `import` cũng chứa đúng cái tên ấy, nên hỏi tên thì gỡ
    # thẻ ra khỏi kết xuất mà phép thử vẫn xanh. Đã kiểm ngược cả hai dòng.
    assert "<DonNghiPhep" in _tep(WEB / "app" / "xe-hdv" / "page.tsx"), \
        "/xe-hdv phải DỰNG thành phần chung, không dựng lại khung của riêng nó"
    assert "<DonNghiPhep" in _tep(TRANG_CC), "/cham-cong phải DỰNG thành phần chung"


def test_ky_hieu_luoi_du_moi_ma_cham_cong():
    """Mọi mã trong `ATT_KINDS` phải có một ký hiệu trong lưới.

    Bảng ký hiệu là một bảng gõ tay song song với bảng của máy chủ, nên nó lệch ở lần thêm mã thứ
    nhất — và lúc lệch thì ô ấy in ra một chuỗi không ai đọc được. Cùng bài học TX-7: ô đếm phải dựng
    từ thang, danh sách gõ lại phải có người canh.
    """
    nguon = _tep(TP_LUOI)
    khoi = nguon[nguon.index("const KY_HIEU"):nguon.index("export default function LuoiChamCong")]
    thieu = [k for k in ATT_KINDS if f"{k}:" not in khoi]
    assert not thieu, f"loại chấm công chưa có ký hiệu trên lưới: {thieu}"


def test_man_hinh_luong_phai_noi_ra_cho_lech():
    """Màn hình Lương phải gọi cửa lệch công và phải NÓI RA rằng bảng chấm công không trả tiền.

    Gỡ khung này đi thì con số lại im lặng, và cái im lặng ấy chính là chỗ hỏng vòng này sửa. Phép thử
    đòi cả hai: lời gọi, và câu nói ra — một khung vẽ ra mà không nói bảng nào trả tiền thì người đọc
    tưởng hai số đang cãi nhau chứ không biết số nào đang được dùng.
    """
    nguon = _tep(MH_LUONG)
    # So bằng ĐƯỜNG ĐẦY ĐỦ, kết bằng dấu nháy ngược đóng chuỗi. Bản đầu của phép thử này chỉ hỏi
    # `"/lech-cong" in nguon`, và kiểm ngược bắt được ngay: đổi tên đường thành `/lech-cong-tam` thì
    # phép thử vẫn XANH, vì chuỗi cũ là khúc đầu của chuỗi mới. Một hàng rào khớp theo khúc đầu là
    # hàng rào trang trí — nó xanh đúng vào lúc đường gọi hỏng.
    assert re.search(r'/payroll-runs/\$\{period\}/lech-cong`', nguon), \
        "màn hình Lương chưa gọi đúng cửa /payroll-runs/{period}/lech-cong"
    assert "lech.dem" in nguon and "lech.loai" in nguon, \
        "ô đếm phải dựng TỪ bảng loại máy chủ trả về, không gõ lại danh sách ở màn hình"
    assert "không theo bảng" in nguon or "KHÔNG phải" in nguon, \
        "khung phải nói ra bảng lương trả theo số HCNS nhập, không theo bảng chấm công"


def test_bang_luong_van_chua_doc_bang_cham_cong():
    """Chốt lại sự thật mà `lech_cong()` dựa trên: `services/hr.py` KHÔNG đọc `AttendanceDay`.

    Phép thử này đỏ theo CẢ HAI chiều, và chiều thứ hai mới là chiều đáng giá. Nếu một ngày có người
    nối bảng chấm công vào bảng lương thì câu khai trong docstring của `lech_cong()` — "hai nguồn, một
    nguồn trả tiền" — thành sai, và ba loại lệch kia mất nghĩa. Lúc ấy phép thử này đỏ để người sửa
    PHẢI quay lại viết lại cả hai, chứ không để một lời khai cũ nằm lại trong mã và dẫn người đọc đi
    sai. Đổi nguồn trả lương là quyết định của Chủ tịch / Kế toán trưởng; phép thử không cấm, nó đòi
    nói ra.
    """
    nguon = (GOC / "backend" / "app" / "services" / "hr.py").read_text(encoding="utf-8")
    assert "AttendanceDay" not in nguon, (
        "services/hr.py nay đọc AttendanceDay — nếu đây là quyết định đổi căn cứ trả lương thì phải "
        "sửa lại docstring của hrm.lech_cong() và ba loại lệch, rồi sửa chính phép thử này")


def _token() -> str:
    r = client.post("/api/v1/auth/login", data={"username": "hcns", "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ----------------------------------------------------------------- chạy thật

def _hai_nguoi(db):
    """Hai người thật trong cơ sở dữ liệu thử: một phòng chấm công theo ngày, một phòng lương cố định."""
    ra = {}
    for ma, phong in (("NS_CC_1", "ketoan"), ("NS_CD_1", "kd_le")):
        e = db.execute(select(Employee).where(Employee.code == ma)).scalar_one_or_none()
        if e is None:
            e = Employee(code=ma, full_name=f"Người thử {ma}", department=phong,
                         contract_type="hdld", base_salary=10_000_000, active=True)
            db.add(e); db.commit(); db.refresh(e)
        ra[phong] = e
    assert L.che_do_cong(ra["ketoan"]) == L.CHAM_CONG
    assert L.che_do_cong(ra["kd_le"]) != L.CHAM_CONG
    return ra["ketoan"], ra["kd_le"]


def test_o_dem_cong_du_tong_so_dong():
    """PHÉP THỬ ĐẮT NHẤT TRONG TỆP: các ô đếm phải cộng đủ số dòng.

    Nó không biết chỗ hỏng nằm ở đâu và không cần biết — nó chỉ hỏi một câu. Cùng khuôn với phép thử
    đã bắt được vụ mười một chiếc xe rơi ra ngoài mọi ô đếm ngày 07/10/2026: lúc ấy màn hình in 16 xe
    và ba ô cộng lại ra 5, không ai thấy, vì mỗi con số riêng lẻ đều trông hợp lý.
    """
    with SessionLocal() as db:
        ky = date.today().strftime("%Y-%m")
        kq = H.lech_cong(db, ky, {})
        assert set(kq["dem"]) == set(H.LOAI_LECH_CONG), \
            "ô đếm phải dựng TỪ LOAI_LECH_CONG — thêm loại mà quên ô đếm thì số không cộng đủ"
        assert sum(kq["dem"].values()) == kq["so_dong"] == len(kq["dong"]), \
            f"ô đếm {kq['dem']} không cộng đủ {kq['so_dong']} dòng"
        assert all(d["loai"] in H.LOAI_LECH_CONG for d in kq["dong"])


def test_bat_duoc_ba_loai_lech_tren_du_lieu_that():
    """Gọi hàm thật, trên dữ liệu thật, và đòi đúng ba chỗ nó sinh ra để nhìn thấy."""
    with SessionLocal() as db:
        ky = date.today().strftime("%Y-%m")
        cc, cd = _hai_nguoi(db)

        # (1) CHƯA NHẬP – phòng chấm công theo ngày mà không ai gõ số công.
        kq = H.lech_cong(db, ky, {})
        chua = [d for d in kq["dong"] if d["ma"] == cc.code]
        assert chua and chua[0]["loai"] == "chua_nhap", f"không bắt được 'chưa nhập': {chua}"

        # (2) LỆCH – số gõ tay khác số bảng chấm công cộng ra.
        theo_bang = chua[0]["cong_theo_bang"]
        kq = H.lech_cong(db, ky, {"cong_thuc_te": {cc.code: theo_bang + 3}})
        d = [x for x in kq["dong"] if x["ma"] == cc.code]
        assert d and d[0]["loai"] == "lech" and d[0]["cong_da_nhap"] == theo_bang + 3, \
            f"không bắt được 'lệch': {d}"

        # Gõ ĐÚNG số bảng chấm công thì người ấy rời khỏi danh sách – không báo oan.
        kq = H.lech_cong(db, ky, {"cong_thuc_te": {cc.code: theo_bang}})
        assert not [x for x in kq["dong"] if x["ma"] == cc.code], "gõ đúng số mà vẫn bị báo lệch"

        # (3) KHÔNG TRỪ – phòng lương cố định, có ngày nghỉ không lương ĐÃ GHI vào bảng chấm công.
        ngay = date.today().replace(day=2)
        cu = db.execute(select(AttendanceDay).where(AttendanceDay.employee_id == cd.id,
                                                    AttendanceDay.day == ngay)).scalar_one_or_none()
        if cu is None:
            cu = AttendanceDay(employee_id=cd.id, day=ngay)
            db.add(cu)
        cu.kind, cu.work = "khong_luong", 0.0
        db.commit()
        kq = H.lech_cong(db, ky, {})
        d = [x for x in kq["dong"] if x["ma"] == cd.code]
        assert d and d[0]["loai"] == "khong_tru" and d[0]["ngay_khong_luong"] >= 1, \
            f"ngày không lương đã duyệt mà bảng lương không trừ gì – không bắt được: {d}"


def test_cua_lech_cong_tra_loi_ca_khi_ky_chua_co_bang_luong():
    """Kỳ chưa có bảng lương thì vẫn soi được bảng chấm công, và cửa phải NÓI RA là chưa có.

    Trả về rỗng ở đây sẽ là trả lời "không có chỗ lệch" cho một câu chưa ai hỏi — đúng loại im lặng
    làm người đọc yên tâm sai.
    """
    r = client.get("/api/v1/payroll-runs/1999-01/lech-cong",
                   headers={"Authorization": "Bearer " + _token()})
    assert r.status_code == 200, r.text
    kq = r.json()
    assert kq["co_bang_luong"] is False
    assert set(kq["dem"]) == set(H.LOAI_LECH_CONG)
