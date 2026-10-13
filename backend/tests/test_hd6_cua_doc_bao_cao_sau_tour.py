"""HD-6 — CỬA ĐỌC BÁO CÁO SAU TOUR: khai vai nào thì vai ấy phải VÀO ĐƯỢC.

Chủ tịch chốt 13/10/2026: "Chủ tịch, TGĐ, TP HDV và BKS đọc được báo cáo sau tour của HDV."

CHUYỆN ĐÃ XẢY RA, đo được trước khi sửa. Cửa `GET /guide-assignments/{aid}/bao-cao` khai 13 vai qua
`HR_READ`, nhưng thân hàm gọi `_phan_cong_cua_toi`, vốn chỉ miễn kiểm sở hữu cho ba vai `BC_KIEM`.
Đăng nhập thật từng vai trên cây dựng từ `git archive origin/main`:

    cntt 200 · hcns 200 — và TÁM vai bị 403: bks, chutich, tgd, ketoan, nv_dh, tp_dh, gd_kd, ptgd_doan

Chủ tịch, Tổng giám đốc và Ban Kiểm soát đều nằm trong tám vai ấy. Đây không phải chuyện dữ liệu
mẫu: phép so là `e.id != a.guide_id`, nên ai không thuộc `BC_KIEM` và không đúng là hướng dẫn viên
của chuyến thì KHÔNG BAO GIỜ qua được, trên máy nào cũng vậy.

GỐC CỦA LỖI: bốn cửa báo cáo — đọc, lập, gửi, lập bản mới — dùng CHUNG một cổng, và cổng ấy viết cho
việc GHI. Luật của việc ghi ("chỉ hướng dẫn viên của chuyến mới nộp được") đè lên cả việc đọc. ĐỌC và
SỬA là hai câu hỏi; cổng `quyen_ho_so` của vòng HD-5 tách sáu thao tác ra đúng để hỏi riêng được.

BỘ NÀY CANH BA ĐIỀU:
  A. Vai nào cửa KHAI thì vai ấy vào được — hàng rào chống "cánh cửa khóa im lặng", đọc danh sách
     vai THẲNG TỪ route chứ không chép tay lại.
  B. Hướng dẫn viên vẫn chỉ đọc được của chính mình, và chặn theo HỒ SƠ chứ không theo tên.
  C. Vai không được khai thì bị chặn — thu danh sách lại là thu thật, không phải đổi chữ.
  D. Chứng minh nhóm A cắn: dựng lại đúng cổng cũ, đòi nhóm A phải đỏ.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hd6.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hd6.db"):
    os.remove("test_hd6.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ID: dict[str, int] = {}
MK = "Vtos@Demo#2026"
DUONG = "/api/v1/guide-assignments/{aid}/bao-cao"
# Hướng dẫn viên KHÔNG đi qua cửa trên. Bản đồ màn hình chặn trước cả cổng sở hữu: vai `hdv` không
# có màn hình nào khai nhóm `/api/v1/guide-assignments`, nên gọi thẳng vào đó là 403 vì một lý do
# khác hẳn. Đó là chủ ý của đợt HDV-2 (`test_i1`): bốn cửa `/xe-hdv/bao-cao/*` là lối vào của chính
# hướng dẫn viên, gọi lại đúng bốn hàm cũ, đặt trong nhóm đã khai cho màn hình của họ.
DUONG_HDV = "/api/v1/xe-hdv/bao-cao/{aid}"
# Vai Chủ tịch KHÔNG chốt cho cửa đọc báo cáo sau tour — dùng ở nhóm C.
NGOAI_DANH_SACH = ("ketoan", "nv_dh", "tp_dh", "gd_kd", "ptgd_doan", "nv_kd", "tai_xe")
D = datetime(2026, 11, 20, 6, 0)


def login(ten):
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": MK})
    assert r.status_code == 200, f"{ten}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def vai_cua_cua() -> tuple[str, ...]:
    """Danh sách vai mà CỬA đang khai — đọc thẳng từ route.

    Không chép tay lại hằng số `XEM_BC`: chép tay thì phép thử và cửa cùng lấy từ một chỗ, và hàng
    rào biến thành một phép so chính nó với chính nó. Ô `vai_tro_yeu_cau` do `require_roles` ghi ra
    là tập ĐÃ NỚI vai kế thừa, tức là đúng những vai thật sự đi qua được chữ ký cửa.
    """
    for r in app.routes:
        if getattr(r, "path", "") == "/api/v1/guide-assignments/{aid}/bao-cao" and "GET" in getattr(r, "methods", ()):
            for p in r.dependant.dependencies:
                vai = getattr(p.call, "vai_tro_yeu_cau", None)
                if vai:
                    return tuple(vai)
    raise AssertionError("không đọc được danh sách vai của cửa đọc báo cáo")


@pytest.fixture(scope="module", autouse=True)
def _dung_canh():
    with TestClient(app) as c:
        global client
        client = c
        from app.core.security import hash_password
        from app.db.session import SessionLocal
        from sqlalchemy import select

        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment

        db = SessionLocal()
        op = db.execute(select(User)).scalars().first().id

        def _hdv(ma, ten):
            return Employee(code=ma, full_name=ten, department="huong_dan", position="hdv",
                            start_date=date(2024, 1, 1), card_no=ma, card_expiry=date(2030, 1, 1),
                            member_org=True, contract_type="ctv", ctv_contract=True)

        e1, e2 = _hdv("H6001", "Trần Văn A"), _hdv("H6002", "Nguyễn Thị B")
        t = Tour(code="H6-T1", name="Huế 4 ngày", tour_type="le_noi_dia", operator_id=op,
                 start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([e1, e2, t])
        db.commit()
        a = GuideAssignment(tour_id=t.id, guide_id=e1.id, days=4, rate_per_day=800_000,
                            bat_dau=D, ket_thuc=D + timedelta(days=4), status="da_xac_nhan")
        db.add(a)

        # Một tài khoản cho MỖI vai cửa đang khai. Tự dựng chứ không dựa vào bản mẫu: bản mẫu không
        # có tài khoản cho mọi vai, và một vai không có tài khoản là một vai không được thử.
        # Gộp hai danh sách rồi LỌC TRÙNG. Hôm nay hai danh sách không giao nhau, nhưng ngày Chủ
        # tịch mở thêm một vai thì chúng sẽ giao — và nếu chỗ này dựng hai tài khoản cùng tên thì
        # cả bộ phép thử sập ở bước dựng cảnh, tức là báo đỏ vì một lý do chẳng liên quan gì đến
        # điều nó canh. Một hàng rào đỏ sai lý do cũng vô dụng như một hàng rào xanh sai lý do.
        for vai in dict.fromkeys(tuple(vai_cua_cua()) + NGOAI_DANH_SACH):
            if db.execute(select(User).where(User.username == f"h6.{vai}")).scalars().first():
                continue
            db.add(User(username=f"h6.{vai}", full_name=f"Thử {vai}", role=vai,
                        department="", password_hash=hash_password(MK)))
        u1 = User(username="h6.hdv.mot", full_name="Trần Văn A", role="hdv",
                  department="Hướng dẫn", password_hash=hash_password(MK))
        u2 = User(username="h6.hdv.hai", full_name="Nguyễn Thị B", role="hdv",
                  department="Hướng dẫn", password_hash=hash_password(MK))
        db.add_all([u1, u2])
        db.commit()
        e1.user_id, e2.user_id = u1.id, u2.id
        db.commit()
        ID["a"] = a.id
        db.close()
        yield


def _doc(ten):
    return client.get(DUONG.format(aid=ID["a"]), headers=login(ten)).status_code


def _doc_hdv(ten):
    return client.get(DUONG_HDV.format(aid=ID["a"]), headers=login(ten)).status_code


# ───────────────────────── A · khai vai nào thì vai ấy vào được ─────────────────────────

def test_a1_moi_vai_cua_KHAI_deu_doc_duoc_that():
    """Hàng rào chống cánh cửa khóa im lặng. Trước vòng này, tám trên mười ba vai được khai tên vẫn
    bị 403 — trong đó có Chủ tịch, TGĐ và Ban Kiểm soát."""
    hong = {}
    for vai in vai_cua_cua():
        if vai == "hdv":
            continue        # hướng dẫn viên vào được theo HỒ SƠ, không theo vai — nhóm B thử riêng
        ma = _doc(f"h6.{vai}")
        if ma != 200:
            hong[vai] = ma
    assert not hong, ("cửa khai những vai này nhưng không cho vào: "
                      + ", ".join(f"{v}={m}" for v, m in sorted(hong.items())))


def test_a2_bon_vai_Chu_tich_chot_deu_co_ten_tren_cua():
    """Chủ tịch chốt 13/10/2026. Bốn vai này không được rơi ra khỏi danh sách trong một lần dọn dẹp
    sau này mà không ai nhận ra."""
    vai = set(vai_cua_cua())
    for can in ("chutich", "tgd", "tp_hd", "bks"):
        assert can in vai, f"thiếu vai {can} trên cửa đọc báo cáo sau tour"


def test_a3_nguoi_kiem_van_doc_duoc():
    """Người kiểm mà không đọc được thì không kiểm được gì."""
    from app.api.v1.hr import BC_KIEM
    for vai in BC_KIEM:
        assert _doc(f"h6.{vai}") == 200, vai


# ───────────────────────── B · hướng dẫn viên chỉ đọc của chính mình ─────────────────────────

def test_b1_hdv_cua_chuyen_doc_duoc_bao_cao_cua_minh():
    assert _doc_hdv("h6.hdv.mot") == 200


def test_b2_hdv_khac_KHONG_doc_duoc_du_cung_vai():
    """Hai hướng dẫn viên THẬT, mỗi người một hồ sơ thật. Đây là ca mà phép thử
    `test_chao_chuyen_hdv.py:127` mang tên nhưng không thử: ở đó người thứ hai không có hồ sơ nào,
    nên nó chỉ chứng minh 'tài khoản chưa nối hồ sơ thì bị chặn'."""
    assert _doc_hdv("h6.hdv.hai") == 403


def test_b3_hdv_van_khong_goi_thang_nhom_guide_assignments():
    """Hai lớp chặn, hai lý do khác nhau, và cả hai đều phải còn. Bản đồ màn hình chặn vai `hdv` ở
    nhóm `/api/v1/guide-assignments` — mở nhóm ấy cho họ là mở luôn chùm cửa điều động, tạm ứng và
    đề xuất. Cổng sở hữu chặn ở lớp trong. Nới một lớp mà tưởng còn lớp kia là cách một hàng rào
    biến mất êm."""
    assert _doc("h6.hdv.mot") == 403


# ───────────────────────── C · thu danh sách lại là thu THẬT ─────────────────────────

def test_c1_vai_khong_duoc_khai_thi_bi_chan():
    """Chủ tịch không chốt các vai này cho cửa đọc báo cáo sau tour. Thu khỏi danh sách phải là thu
    thật — cửa trả 403 chứ không phải chỉ đổi chữ trên màn hình."""
    vai = set(vai_cua_cua())
    for khong in NGOAI_DANH_SACH:
        if khong in vai:
            continue        # Chủ tịch mở thêm sau này thì đây không còn là ca cấm
        assert _doc(f"h6.{khong}") in (401, 403), khong


# ───────────────────────── D · chứng minh nhóm A cắn ─────────────────────────

def test_d1_dung_lai_cong_cu_thi_nhom_A_phai_do():
    """Cổng cũ: miễn kiểm sở hữu cho `BC_KIEM`, mọi vai khác phải đúng là hướng dẫn viên của chuyến.
    Chạy lại chính phép thử nhóm A qua cổng ấy và đòi nó ĐỎ. Không đỏ thì nhóm A không đo gì."""
    from sqlalchemy import select

    from app.api.v1.hr import BC_KIEM
    from app.db.session import SessionLocal
    from app.models.core import User
    from app.models.hr import Employee, GuideAssignment

    def cong_cu(u, a):
        if u.role in BC_KIEM:
            return 200
        with SessionLocal() as db:
            e = db.execute(select(Employee).where(Employee.user_id == u.id)).scalars().first()
            return 200 if (e is not None and e.id == a.guide_id) else 403

    with SessionLocal() as db:
        a = db.get(GuideAssignment, ID["a"])
        hong = {}
        for vai in vai_cua_cua():
            if vai == "hdv":
                continue
            u = db.execute(select(User).where(User.username == f"h6.{vai}")).scalars().first()
            if u is None:
                continue
            ma = cong_cu(u, a)
            if ma != 200:
                hong[vai] = ma
    assert hong, "cổng cũ cho mọi vai đi qua – vậy nhóm A không phân biệt được cũ với mới"
    for can in ("chutich", "tgd", "bks"):
        assert hong.get(can) == 403, f"cổng cũ đáng lẽ chặn {can}, đo được {hong.get(can)}"
