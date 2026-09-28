"""TC-94 · VIỆC NỀN KHÔNG ĐƯỢC CHẶN MÁY CHỦ — 28/9/2026.

ĐO ĐƯỢC, không suy đoán. Ngày 28/9/2026 Render báo health check trượt đều đặn mỗi 12–13 phút suốt
cả ngày. Nhật ký ứng dụng ghi lời chào health check mỗi ~5 giây, và lúc 20:14:12 → 20:14:34 KHÔNG
có dòng nào: một khoảng câm 22 GIÂY. Trong tiến trình chỉ có MỘT thứ chạy định kỳ — `main.robot_loop`
— và nhánh nặng của nó là `i % 10`. Chu kỳ thật là 60 giây cộng thời gian làm việc, nên "mỗi 10
phút" trôi thành mỗi ~12,5 phút, khớp đúng khoảng cách đo được.

Nguyên nhân là HÌNH DẠNG của mã, không phải một phép tính sai: `robot_loop` khai `async` nhưng gọi
thẳng các việc cơ sở dữ liệu đồng bộ, nên vòng lặp sự kiện của uvicorn đứng lại trong suốt lượt ấy.

Bộ kiểm này canh ba chuyện, và chuyện thứ ba là chuyện dễ mất nhất về sau:

 1. HÌNH DẠNG — `robot_loop` chỉ được `await asyncio.to_thread(...)`, không gọi thẳng việc nền.
    Canh bằng cây cú pháp, vì đây là loại lỗi mà chạy thử KHÔNG thấy: bản gọi thẳng vẫn chạy đúng,
    vẫn ra đúng kết quả, chỉ chặn máy chủ trong lúc chạy.

 2. VIỆC NỀN VẪN LÀM ĐÚNG VIỆC — tách ra luồng mà hỏng chức năng thì chữa bệnh này sinh bệnh khác.

 3. CÁCH SỬA THẬT SỰ CÓ TÁC DỤNG — dựng lại đúng cảnh cũ và cảnh mới trong một vòng lặp sự kiện
    thật, rồi ĐẾM xem nó còn quay được bao nhiêu nhịp. Không có phép thử này thì luật số 1 chỉ là
    một quy ước về cách viết, và người sau có quyền hỏi "đổi làm gì".
"""
import ast
import asyncio
import inspect
import os
import sys
import tempfile
import time

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_tc94.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x):
            os.remove(_x)
    except OSError:
        pass

from app.db.session import Base, engine        # noqa: E402
import app.main as M                            # noqa: E402

# Tên các việc nền NẶNG. Một trong số này xuất hiện trong thân `robot_loop` nghĩa là bản vá đã bị
# gỡ — dù người gỡ có ý tốt đến đâu.
VIEC_NANG = {"run_robots", "robot_cskh", "den_luot", "robot_check", "nap_nguong",
             "lam_moi_cache_nen", "SessionLocal"}


def _than_ham(ten: str) -> ast.AST:
    cay = ast.parse(inspect.getsource(M))
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == ten:
            return n
    raise AssertionError(f"main.py không còn hàm {ten}")


# ═════════════════ 1. HÌNH DẠNG ═════════════════
def test_robot_loop_KHONG_goi_thang_viec_nen():
    """Canh đúng dòng đã gây ra 22 giây câm trên máy chủ."""
    than = _than_ham("robot_loop")
    ten_goi = set()
    for n in ast.walk(than):
        if isinstance(n, ast.Call):
            f = n.func
            ten_goi.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    xau = VIEC_NANG & ten_goi
    assert not xau, (
        f"robot_loop đang gọi THẲNG việc nền {sorted(xau)} trên vòng lặp sự kiện. "
        "Máy chủ sẽ câm suốt thời gian ấy — đúng lỗi TC-94 sửa. Đẩy qua asyncio.to_thread.")
    assert "to_thread" in ten_goi, "robot_loop không còn đẩy việc nền sang luồng riêng"


def test_mot_luot_robot_la_ham_DONG_BO():
    """Biến nó thành `async` là lặng lẽ kéo cả lượt việc trở lại vòng lặp sự kiện."""
    assert not inspect.iscoroutinefunction(M._mot_luot_robot), \
        "_mot_luot_robot phải là hàm đồng bộ — asyncio.to_thread không chạy được hàm async"


def test_phien_co_so_du_lieu_dong_trong_moi_truong_hop():
    """`finally`, không phải dòng cuối thân hàm: mỗi lượt hỏng bỏ lại một kết nối treo."""
    than = _than_ham("_mot_luot_robot")
    co = any(isinstance(n, ast.Try) and n.finalbody
             and any("close" in ast.dump(x) for x in n.finalbody)
             for n in ast.walk(than))
    assert co, "_mot_luot_robot chưa đóng phiên cơ sở dữ liệu trong khối finally"


# ═════════════════ 2. VIỆC NỀN VẪN LÀM ĐÚNG VIỆC ═════════════════
def test_mot_luot_robot_chay_duoc_ca_luot_nhe_va_luot_nang():
    """Lượt 1 (nhẹ) và lượt 10 (nhánh i % 10, nặng nhất) đều phải chạy trót lọt."""
    Base.metadata.create_all(engine)
    from app.db.session import SessionLocal
    from app.services import rules as R
    db = SessionLocal()
    R.seed_params(db)
    db.close()
    for i in (1, 10):
        M._mot_luot_robot(i)      # ném lỗi là đỏ, không cần assert gì thêm


def test_chay_duoc_trong_LUONG_khac_dung_nhu_may_chu_se_chay():
    """Chạy qua chính `asyncio.to_thread` — phiên cơ sở dữ liệu phải mở được ở luồng khác."""
    async def di():
        await asyncio.to_thread(M._mot_luot_robot, 2)
    asyncio.run(di())


# ═════════════════ 3. CÁCH SỬA THẬT SỰ CÓ TÁC DỤNG ═════════════════
def _dem_nhip(qua_luong: bool, giay: float = 0.8, nhip: float = 0.02) -> int:
    """Dựng một vòng lặp sự kiện thật, cho một 'đồng hồ' chạy trong đó, rồi làm một việc đồng bộ
    tốn `giay` giây — một lần qua luồng riêng, một lần gọi thẳng. Trả về số nhịp đồng hồ đếm được.

    Đây là bản thu nhỏ của đúng thứ đã xảy ra trên máy chủ: 'đồng hồ' đóng vai lời chào health
    check mỗi 5 giây, và việc đồng bộ đóng vai cụm robot."""
    async def kich_ban():
        dem = 0

        async def dong_ho():
            nonlocal dem
            while True:
                await asyncio.sleep(nhip)
                dem += 1

        t = asyncio.create_task(dong_ho())
        await asyncio.sleep(nhip)            # cho đồng hồ chạy trước một nhịp
        if qua_luong:
            await asyncio.to_thread(time.sleep, giay)
        else:
            time.sleep(giay)                 # CẢNH CŨ: chặn thẳng vòng lặp sự kiện
        t.cancel()
        return dem

    return asyncio.run(kich_ban())


def test_day_sang_luong_rieng_thi_may_chu_VAN_TRA_LOI_duoc():
    dem = _dem_nhip(qua_luong=True)
    assert dem >= 8, (
        f"đẩy sang luồng riêng mà vòng lặp sự kiện chỉ quay được {dem} nhịp trong 0,8 giây — "
        "cách sửa của TC-94 không có tác dụng")


def test_goi_thang_thi_may_chu_CAM_dung_nhu_da_do_duoc():
    """Hàng rào tự kiểm: dựng lại cảnh cũ và đòi nó PHẢI hỏng. Nếu phép thử này xanh cả khi gọi
    thẳng thì cả tệp này đang canh một cánh cửa không khoá."""
    dem = _dem_nhip(qua_luong=False)
    assert dem <= 3, (
        f"gọi thẳng mà vòng lặp sự kiện vẫn quay được {dem} nhịp — phép đo này không tái hiện "
        "được cảnh đã gây ra 22 giây câm trên máy chủ, nên đừng tin hai phép thử trên nó")
