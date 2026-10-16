# -*- coding: utf-8 -*-
"""HS-6 — hộp Sửa tài khoản: gom sáu việc về một chỗ mà KHÔNG dựng thêm cửa nào.

Vòng này gần như toàn bộ là giao diện, nên phần lớn bộ thử ở đây ĐỌC MÃ NGUỒN của màn hình chứ
không gọi API. Lý do: cái dễ hỏng nhất của một hộp gom nhiều việc không phải phép tính, mà là
màn hình và máy chủ nói hai thứ khác nhau — nút hiện ra cho một vai mà cửa từ chối vai ấy, hoặc
một ô nhập gửi lên trường mà cửa không nhận. Cả hai kiểu hỏng ấy đều IM LẶNG cho tới khi có
người bấm thật.

`test_hs6_2` là phép thử nặng nhất: nó đọc bốn danh sách vai trong tệp .tsx và so với bốn bộ vai
khai ở Python. Bản sao nào cũng trôi; bản sao có người canh thì không.
"""
import os, re, sys, tempfile

# Cơ sở dữ liệu thử để Ở THƯ MỤC TẠM, không để cạnh mã nguồn như các bộ khác. Lý do đo được
# 16/10/2026: trên máy Chủ tịch, thư mục kho được gắn kết với quyền XOÁ TẮT, nên một tệp .db hỏng
# từ lần chạy trước không xoá đi được và mọi lần chạy sau đều đỏ "disk I/O error" — một cái đỏ
# không nói gì về mã. Thư mục tạm thì xoá được, và trong CI thì máy chạy nào cũng sạch.
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hs6.db")
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
TEP_HOP = os.path.join(GOC, "web", "components", "SuaTaiKhoan.tsx")
TEP_MAN = os.path.join(GOC, "web", "app", "access", "page.tsx")


def _doc(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def hop():
    assert os.path.exists(TEP_HOP), f"Thiếu {TEP_HOP} — hộp Sửa là deliverable của vòng HS-6."
    return _doc(TEP_HOP)


@pytest.fixture(scope="module")
def man():
    return _doc(TEP_MAN)


def _danh_sach(src: str, ten: str) -> list[str]:
    """Lấy một mảng chuỗi khai bằng `const <ten> = [...]` trong tệp .tsx."""
    m = re.search(r"const\s+" + ten + r"\s*=\s*\[(.*?)\]", src, re.S)
    assert m, f"Không tìm thấy `const {ten} = [...]` trong SuaTaiKhoan.tsx"
    return sorted(re.findall(r'"([^"]+)"', m.group(1)))


# ---------------------------------------------------------------------------------------------
# 1. Cửa danh sách phải trả ID hồ sơ, không chỉ mã
# ---------------------------------------------------------------------------------------------
def test_hs6_1_danh_sach_tai_khoan_tra_ho_so_id():
    """Cửa ghi nghỉ việc làm việc theo `employee_id`. Màn hình chỉ có mã thì phải tra thêm một
    lượt, và lượt tra ấy là cách nối thứ hai giữa tài khoản và hồ sơ — đúng thứ
    `services/quyen_ho_so.py` ra đời để dẹp."""
    from fastapi.testclient import TestClient
    from app.db.session import SessionLocal
    from app.main import app
    from app.models.hr import Employee
    from app.services.access_admin import danh_sach_tai_khoan

    # Mở TestClient để vòng đời ứng dụng dựng bảng và nạp dữ liệu mẫu — gọi thẳng dịch vụ trên
    # một cơ sở dữ liệu chưa dựng thì đỏ vì "no such table", một cái đỏ không nói gì về vòng này.
    with TestClient(app):
        db = SessionLocal()
        try:
            rows = danh_sach_tai_khoan(db)
            assert rows, "Cơ sở dữ liệu thử không có tài khoản nào."
            assert all("ho_so_id" in r for r in rows), "Có dòng thiếu hẳn khoá `ho_so_id`."

            # Dòng nào có mã hồ sơ thì phải có ID, và ID ấy phải trỏ đúng hồ sơ mang mã đó.
            co_ma = [r for r in rows if r.get("ho_so")]
            for r in co_ma:
                assert r["ho_so_id"] is not None, f"{r['username']} có mã {r['ho_so']} mà `ho_so_id` rỗng."
                e = db.get(Employee, r["ho_so_id"])
                assert e is not None, f"`ho_so_id`={r['ho_so_id']} của {r['username']} không có hồ sơ nào."
                assert e.code == r["ho_so"], (
                    f"{r['username']}: `ho_so_id` trỏ hồ sơ {e.code} nhưng `ho_so` ghi {r['ho_so']} — "
                    "hai khoá nói hai người khác nhau.")

            # Và ngược lại: không có mã thì không được bịa ra ID.
            for r in rows:
                if not r.get("ho_so"):
                    assert r["ho_so_id"] is None, (
                        f"{r['username']} không có mã hồ sơ mà `ho_so_id`={r['ho_so_id']}.")
        finally:
            db.close()


# ---------------------------------------------------------------------------------------------
# 2. Bốn danh sách vai của màn hình phải TRÙNG KHÍT bộ vai của cửa
# ---------------------------------------------------------------------------------------------
def test_hs6_2_bon_danh_sach_vai_khop_voi_cua(hop):
    """Sáu cửa trong hộp có BỐN bộ vai khác nhau, vì chúng là bốn mức hệ quả khác nhau.

    Lệch theo chiều RỘNG thì nút hiện ra rồi bấm vào nhận 403 — người bấm không biết mình thiếu
    quyền hay hệ thống lỗi. Lệch theo chiều HẸP thì một vai có quyền thật bị giấu mất việc, và
    không ai báo vì không ai biết đáng lẽ phải thấy.
    """
    from app.api.v1.access import THAO_TAC
    from app.api.v1.hr import HR_WRITE
    from app.api.v1.bien_dong_ns import GHI
    from app.api.v1.gop_tai_khoan import XOA

    assert _danh_sach(hop, "VAI_SUA_HO_SO") == sorted(set(THAO_TAC) | {"chutich", "tgd"}), (
        "VAI_SUA_HO_SO lệch với `THAO_TAC + chutich + tgd` của app/api/v1/access.py — "
        "ba cửa /ho-so, /company, /bien-che đều khai đúng bộ ấy.")
    assert _danh_sach(hop, "VAI_KHOA") == sorted(HR_WRITE), (
        "VAI_KHOA lệch với `HR_WRITE` của app/api/v1/hr.py — `PUT /users/{uid}` và "
        "`POST /users/{uid}/reset-password` đều khai bộ này.")
    assert _danh_sach(hop, "VAI_NGHI_VIEC") == sorted(GHI), (
        "VAI_NGHI_VIEC lệch với `GHI` của app/api/v1/bien_dong_ns.py.")
    assert _danh_sach(hop, "VAI_XOA") == sorted(XOA), (
        "VAI_XOA lệch với `XOA` của app/api/v1/gop_tai_khoan.py. Lưu ý bản vẽ duyệt 15/10 ghi "
        "«chỉ Chủ tịch · CNTT» — mã thật khác, và MÃ là thứ quyết định ai qua được cửa.")


# ---------------------------------------------------------------------------------------------
# 3. Mọi đường hộp gọi phải có thật trong bảng đường của máy chủ
# ---------------------------------------------------------------------------------------------
def test_hs6_3_moi_duong_hop_goi_deu_co_that(hop):
    """Một đường gõ sai chính tả trong .tsx không ai thấy cho tới khi có người bấm."""
    from app.main import app

    co_that = set()
    for r in app.routes:
        duong = getattr(r, "path", "")
        if duong:
            co_that.add(re.sub(r"\{[^}]+\}", "{}", duong))

    thieu = []
    for duong in re.findall(r'api<?[^>]*>?\(\s*[`"\']([^`"\']*)', hop):
        if not duong.startswith("/"):
            continue
        d = re.sub(r"\$\{[^}]+\}", "{}", duong).split("?")[0].rstrip("/")
        if "/api/v1" + d not in co_that:
            thieu.append(duong)
    assert not thieu, (
        f"Hộp Sửa gọi những đường KHÔNG CÓ trong máy chủ: {thieu}. "
        "Vòng HS-6 cố ý không viết thêm cửa nào — đường nào không khớp là gõ sai.")


# ---------------------------------------------------------------------------------------------
# 4. Bàn giao chưa có cửa thì phải KHAI RA, không được vẽ một ô không làm gì
# ---------------------------------------------------------------------------------------------
def test_hs6_4_ghi_nghi_viec_khong_tu_ban_giao_va_ban_giao_la_nut_rieng(hop):
    """16/10/2026 — phép thử này ĐÃ ĐỔI ĐIỀU NÓ CANH, và chỗ đổi đáng ghi lại.

    Bản đầu đòi màn hình KHAI RA rằng bàn giao chưa có cửa. Nay cửa đã có (HS-7,
    `POST /bien-dong-ns/ban-giao-viec`), nên đòi như cũ là đòi màn hình nói dối. Chính phép thử
    ấy đã đỏ đúng lúc cửa ra đời — đó là việc nó sinh ra để làm.

    Điều cần canh BÂY GIỜ vẫn là chỗ hỏng cũ, chỉ đổi hình: `ghi_nghi_viec` vẫn KHÔNG chuyển một
    tour, booking hay phân công nào. Nếu một ngày ai đó gộp bàn giao vào cửa ghi nghỉ việc cho
    tiện thì một lần bấm làm hai việc không hoàn lại được như nhau, mà người bấm chỉ đọc một câu
    xác nhận. Hai nút, hai lần xác nhận.
    """
    import inspect
    from app.services import bien_dong_ns as BD

    tham_so = set(inspect.signature(BD.ghi_nghi_viec).parameters)
    assert not (tham_so & {"nguoi_nhan", "nguoi_nhan_id", "ban_giao", "ban_giao_cho"}), (
        "`ghi_nghi_viec` nhận tham số bàn giao — hai việc không hoàn lại được bị gộp vào một lần "
        "bấm. Bàn giao có cửa riêng: `POST /bien-dong-ns/ban-giao-viec`.")

    goi = re.search(r"/bien-dong-ns/nghi-viec\"[^;]*?\{(.*?)\}", hop, re.S)
    assert goi, "Không tìm thấy lời gọi `/bien-dong-ns/nghi-viec` trong hộp Sửa."
    for cam in ("nguoi_nhan", "ban_giao", "den_user_id"):
        assert cam not in goi.group(1), (
            f"Hộp Sửa gửi `{cam}` lên cửa ghi nghỉ việc, mà cửa ấy không nhận — trường gửi thừa "
            "bị bỏ im lặng, và người dùng tưởng đã bàn giao.")

    assert "/bien-dong-ns/ban-giao-viec" in hop, (
        "Hộp Sửa không có nút bàn giao. Cửa đã có từ HS-7; không nối vào thì người dùng vẫn phải "
        "đi chuyển tay từng thứ ở màn của nó.")
    assert "banGiao(false)" in hop and "banGiao(true)" in hop, (
        "Bàn giao phải đi HAI bước: xem trước (`xac_nhan=false`, máy chủ KHÔNG ghi gì) rồi mới "
        "bàn giao thật. Nó dịch chuyển doanh số giữa hai người.")
    assert "o_lai" in hop, (
        "Bản xem trước không in phần Ở LẠI. Chỉ kê thứ sắp chuyển sẽ khiến người bấm tin rằng "
        "mọi thứ khác không tồn tại.")


# ---------------------------------------------------------------------------------------------
# 5. Xoá phải đi hai bước và phải hỏi máy chủ trước
# ---------------------------------------------------------------------------------------------
def test_hs6_5_xoa_hai_buoc_va_hoi_may_chu_truoc(hop):
    """Một thao tác không hoàn lại được thì bước mặc định phải là bước KHÔNG LÀM GÌ."""
    assert "co-the-xoa" in hop, (
        "Hộp Sửa không gọi `GET /gop-tai-khoan/co-the-xoa/{uid}`. Không hỏi thì nút Xoá hoặc "
        "sáng bừa, hoặc tối mà không nói vì sao — cả hai đều đẩy người dùng đi hỏi CNTT.")
    assert "xac_nhan: false" in hop and "xac_nhan: true" in hop, (
        "Xoá phải đi HAI bước: `xac_nhan=false` lấy bản xem trước (máy chủ KHÔNG ghi gì), rồi "
        "mới `xac_nhan=true`. Thiếu bước một là một lần bấm nhầm mất vĩnh viễn một bản ghi.")
    assert "can_tro" in hop, (
        "Hộp Sửa không in `can_tro` — câu giải thích vì sao chưa xoá được phải lấy từ cửa, "
        "không phải một câu đoán ở màn hình.")


# ---------------------------------------------------------------------------------------------
# 6. Nút Khoá trên bảng phải gác bằng đúng bộ vai của cửa nó gọi
# ---------------------------------------------------------------------------------------------
def test_hs6_6_nut_khoa_tren_bang_gac_dung_bo_vai(man):
    """Lỗi có sẵn vòng này vá: `PUT /users/{uid}` khai `HR_WRITE` (hcns + cntt) nhưng nút «Khóa»
    trên bảng gác bằng `canWrite` (bốn vai), nên Chủ tịch và TGĐ bấm vào nhận 403.

    Chú thích của chính màn hình ấy đã cảnh báo đúng chuyện này cho nút «Đặt lại MK» ngay bên
    cạnh — và bỏ sót nút này. Một lời cảnh báo đúng mà áp thiếu một chỗ thì chỗ thiếu ấy còn khó
    thấy hơn, vì người đọc tin rằng cả vùng đã được soi.
    """
    from app.api.v1.hr import HR_WRITE

    m = re.search(r"const\s+canKhoa\s*=\s*\[(.*?)\]", man, re.S)
    assert m, "Màn hình Tài khoản không khai `canKhoa` — nút Khoá đang gác bằng danh sách nào?"
    assert sorted(re.findall(r'"([^"]+)"', m.group(1))) == sorted(HR_WRITE), (
        "`canKhoa` lệch với `HR_WRITE` của app/api/v1/hr.py.")

    assert re.search(r"\{canKhoa && <button[^>]*>?[^}]*?/users/\$\{r\.id\}", man, re.S) \
        or "{canKhoa && <button" in man, "Nút Khoá trên bảng chưa gác bằng `canKhoa`."
    # Và không được quay lại gác bằng canWrite.
    assert 'canWrite && <button className="act" style={{ margin: 0, marginRight: 4 }}\n' \
           '              onClick={() => send(`/users/' not in man, (
        "Nút Khoá lại gác bằng `canWrite` — bốn vai, trong đó hai vai chắc chắn nhận 403.")


# ---------------------------------------------------------------------------------------------
# 7. Hộp không được dựng bản sao thứ hai của cửa đổi vai trò
# ---------------------------------------------------------------------------------------------
def test_hs6_7_khong_co_duong_doi_vai_tro_thu_hai(hop):
    """Bảng đã có ô chọn vai trò, kèm hộp hỏi LÝ DO bắt buộc. Dựng ô thứ hai trong hộp Sửa là hai
    đường đổi vai trò, và một trong hai đường sớm muộn quên mất phần hỏi lý do — lúc ấy nhật ký
    quyền có những dòng đổi vai không ai biết vì sao."""
    assert "role-change" not in hop, (
        "Hộp Sửa gọi `/access/role-change/{uid}` — đó là đường thứ hai cho cùng một việc. "
        "Đổi vai trò ở ô chọn trên bảng, nơi đã có phần hỏi lý do bắt buộc.")


# ---------------------------------------------------------------------------------------------
# 8. Hàng rào phạm vi màn hình KHÔNG NHÌN THẤY tệp này — nên tự canh lấy
# ---------------------------------------------------------------------------------------------
def test_hs6_8_moi_vai_duoc_bay_nut_deu_voi_toi_cua_sau_nut_ay(hop):
    """CHỖ HỞ ĐO ĐƯỢC 16/10/2026, và nó là lý do phép thử này tồn tại.

    `test_p2_pham_vi_vai_tro::test_ban_do_man_hinh_api_khong_lech_voi_giao_dien` canh đúng việc
    này — màn hình gọi nhóm API nào thì phải khai nhóm ấy — nhưng nó chỉ quét `app/*/page.tsx`.
    Hộp Sửa nằm trong `components/`, nên mọi đường nó gọi đều NẰM NGOÀI TẦM phép thử ấy.

    Hàng rào thật thì không bỏ sót: `check_restricted_scope` chạy trong `current_user` cho MỌI
    đường và so với `pham_vi_day_du(vai)` — hợp của mọi màn hình vai ấy thấy. Hộp này gọi
    `/bien-dong-ns` và `/gop-tai-khoan`, hai nhóm KHÔNG có trong bản đồ của riêng màn `/access`;
    hôm nay chạy được là nhờ các vai ấy với tới chúng qua màn hình KHÁC. "Chạy được nhờ một màn
    hình khác" là chỗ dựa không ai ghi lại: ngày nào có người thu hẹp bản đồ của màn hình kia,
    hộp này gãy và không ai nối được nguyên nhân với hậu quả.

    SO THEO TỪNG NÚT, không theo cả màn hình. Bản đầu của phép thử này đòi MỌI vai mở được màn
    Tài khoản phải với tới MỌI đường hộp gọi, và nó đỏ ở `robot_pq` — vai robot mở được màn ấy
    nhưng không nằm trong danh sách nào của hai nút dưới, nên hộp KHÔNG BAO GIỜ gọi hai cửa ấy
    thay nó. Một phép thử đòi nhiều hơn điều cần đòi thì lần sau người ta nới nó cho hết đỏ, và
    nới xong thì nó không còn canh gì nữa.
    """
    from app.services.access import MAN_HINH_API, pham_vi_day_du

    assert MAN_HINH_API.get("/access"), "Màn /access không còn trong bản đồ màn hình — kiểm lại."

    # Mỗi nhóm đường đi kèm ĐÚNG danh sách vai mà hộp cho phép bấm nút gọi nó.
    theo_nut = {
        "/api/v1/access/users": "VAI_SUA_HO_SO",
        "/api/v1/users":        "VAI_KHOA",
        "/api/v1/bien-dong-ns": "VAI_NGHI_VIEC",
        "/api/v1/gop-tai-khoan": "VAI_XOA",
    }

    duong = set()
    for d in re.findall(r'api<?[^>]*>?\(\s*[`"\']([^`"\']*)', hop):
        if d.startswith("/"):
            duong.add("/api/v1" + re.sub(r"\$\{[^}]+\}", "x", d).split("?")[0])
    assert duong, "Không đọc được đường gọi nào trong hộp Sửa."

    hong, mo_coi = [], []
    for d in sorted(duong):
        nhom = [k for k in theo_nut if d.startswith(k)]
        if not nhom:
            mo_coi.append(d); continue
        ten = theo_nut[max(nhom, key=len)]
        for vai in _danh_sach(hop, ten):
            if not any(d.startswith(p) for p in pham_vi_day_du(vai)):
                hong.append(f"{vai} được bày nút gọi {d} nhưng hàng rào phạm vi chặn")

    assert not mo_coi, (
        f"Hộp Sửa gọi đường không thuộc nút nào đã khai: {mo_coi}. Thêm nó vào `theo_nut` cùng "
        "danh sách vai gác nút ấy — đường không có vai gác là đường không ai canh.")
    assert not hong, (
        "Hộp Sửa bày ra nút mà hàng rào phạm vi sẽ chặn bằng 403 — và 403 ấy trông y hệt một "
        "quyết định có chủ:\n  " + "\n  ".join(hong))
