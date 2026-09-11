"""KS-4 · Cảnh báo phải có vòng đời, và không được ngập.

Đo ngày 10/9/2026: 1.703 cảnh báo đang mở, 1.310 đỏ. Lớn nhất là 851 chuyến quá hạn quyết toán và
251 booking quá deadline thu. Một nghìn bảy trăm việc đỏ không ai đứng tên thì không phải một nghìn
bảy trăm việc — nó là một màn hình không ai mở nữa, và cảnh báo thứ 1.704 (cái thật) chìm trong đó.

Hai nguyên nhân tách bạch, và phép thử trong tệp này tách đúng như vậy:

  (a) BẢNG THIẾU CỘT. `alerts` có bảy cột: kind, level, ref, message, to_roles, created_at, resolved.
      Không có người nhận, không có hạn, không có trạng thái đang-xử-lý, không có bằng chứng đóng.
      VD1–VD3 đọc bản khai ở tools/ks4_canh_bao.py và ĐỎ cho tới khi lane Viết phần mềm dựng đủ.
      Đỏ ở đây là việc-còn-nợ đang được đếm, KHÔNG phải phép thử hỏng. Ai muốn xanh thì dựng bảng,
      đừng sửa bản khai.

  (b) QUÉT KHÔNG CÓ MỐC. `run_robots` duyệt MỌI chuyến `ket_thuc` quá hạn, không giới hạn thời gian,
      nên mỗi chuyến lịch sử đổ từ Vietrip sang thành một dòng đỏ. VD5 dựng 60 chuyến cũ rồi đếm —
      nó đo đúng cái cơ chế đã đẻ ra 851 dòng, chứ không đo con số 851.

  Phân hệ Chăm sóc đã gặp đúng chuyện (b) và đã có lời giải nằm sẵn trong kho: tham số
  `cham_soc_lui_ngay`. Cảnh báo cần mốc tương tự. Đó là lý do VD3 đòi `canh_bao_lui_ngay`.

VD4 và VD6 canh chiều ngược lại: chống trùng hiện đang đúng ở hầu hết nơi (mỗi robot tự dò theo
(kind, ref) trước khi thêm). Đó là tài sản dễ mất — người viết robot thứ mười hai không có gì nhắc.
Hai phép thử ấy XANH ngay hôm nay và phải ở lại để giữ cho nó xanh.
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_ks4_canhbao.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_ks4_canhbao.db", "test_ks4_canhbao.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import ast  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.models.core import Alert, Tour, User  # noqa: E402
from tools import ks4_canh_bao as Y  # noqa: E402

client = TestClient(app)
GOC_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


# =================================================================== (a) bảng thiếu cột

def test_vd1_bang_alerts_phai_co_du_cot_vong_doi():
    """ĐỎ cho tới khi lane Viết phần mềm dựng bảng. Đây là việc còn nợ, không phải phép thử hỏng.

    Đừng làm xanh bằng cách xoá dòng khai trong tools/ks4_canh_bao.py: mỗi cột ở đó có một câu trả
    lời cho câu hỏi 'vì sao 1.703 dòng đỏ này không ai xử lý'. Xoá khai là xoá câu hỏi, không phải
    trả lời nó.
    """
    co = set(Alert.__table__.columns.keys())
    thieu = {c: ly for c, ly in Y.COT_VONG_DOI.items() if c not in co}
    assert not thieu, (
        "bảng alerts thiếu %d cột vòng đời (đang có: %s)\n" % (len(thieu), sorted(co))
        + "\n".join(f"  · {c}\n      {ly}" for c, ly in thieu.items())
        + "\n\n  Việc của lane Viết phần mềm: thêm cột + migration. Kiểm soát khai, không dựng bảng.")


def test_vd2_trang_thai_phai_la_vong_doi_that_khong_phai_o_dung_sai():
    """`resolved` gộp 'chưa ai nhận', 'đang có người làm' và 'đã xong' vào một ô đúng/sai.

    Hệ quả đo được: không biết dòng nào đang có người, nên hai người cùng làm một việc mà không ai
    biết; và không phân biệt được 'đóng vì đã xử lý' với 'đóng vì là dữ liệu lịch sử'.
    """
    if "trang_thai" not in Alert.__table__.columns.keys():
        pytest.skip("chờ VD1 – chưa có cột trang_thai")
    from app.models import core as C
    khai = getattr(C, "ALERT_TRANG_THAI", None)
    assert khai is not None, (
        "có cột trang_thai nhưng không có bảng giá trị ALERT_TRANG_THAI trong models/core.py – "
        f"giá trị phải khai ra được cho máy đọc, gồm: {sorted(Y.TRANG_THAI)}")
    assert set(khai) == set(Y.TRANG_THAI), (
        f"ALERT_TRANG_THAI = {sorted(khai)} khác bản khai KS-4 {sorted(Y.TRANG_THAI)}")
    chuyen = getattr(C, "ALERT_CHUYEN", None)
    assert chuyen is not None and set(chuyen.get("moi", ())) == set(Y.CHUYEN["moi"]), (
        "phải khai bảng chuyển trạng thái ALERT_CHUYEN, và 'moi' KHÔNG được nhảy thẳng sang 'dong': "
        "đóng khi chưa ai nhận là đóng để cho sạch màn hình.")


def test_vd3_tham_so_moc_thoi_gian_phai_co_cua_cho_ban_tgd():
    """Ba con số này phải là THAM SỐ, không viết cứng trong mã.

    Ranh giới 09/9/2026: mỗi con số hệ thống cần một cửa nhập. Mốc vận hành thật và khoảng lùi là số
    Ban TGĐ chốt, không phải hằng số người viết phần mềm tự đặt rồi phải triển khai lại mới đổi được.
    """
    from app.services.rules import DEFAULT_PARAMS
    co = {k for k, *_ in DEFAULT_PARAMS}
    thieu = [(k, ly, dv) for k, ly, dv in Y.THAM_SO_CAN if k not in co]
    assert not thieu, (
        "thiếu tham số cho vòng đời cảnh báo:\n"
        + "\n".join(f"  · {k} ({dv})\n      {ly}" for k, ly, dv in thieu)
        + "\n\n  Đã có tiền lệ trong kho: 'cham_soc_lui_ngay' chặn đúng việc này cho phân hệ Chăm sóc.")


# =================================================================== (b) quét không có mốc

def _tao_chuyen_cu(db, n: int, lui_ngay: int = 400):
    """Dựng n chuyến ĐÃ KẾT THÚC từ lâu — hình dạng của dữ liệu đổ từ Vietrip sang."""
    op = db.execute(select(User).where(User.role == "nv_dh")).scalars().first() \
        or db.execute(select(User)).scalars().first()
    d = date.today() - timedelta(days=lui_ngay)
    for i in range(n):
        db.add(Tour(code=f"KS4-CU-{i:03d}", name=f"Chuyến lịch sử {i}", tour_type="le",
                    start_date=d, end_date=d + timedelta(days=2), operator_id=op.id,
                    status="ket_thuc", planned_pax=10))
    db.commit()


def test_vd5_mot_luot_quet_khong_duoc_de_ra_hang_loat_dong_do():
    """Đo đúng cơ chế đã sinh ra 851 dòng, không đo con số 851.

    Dựng 60 chuyến kết thúc từ hơn một năm trước rồi chạy robot một lượt. Nếu một lượt quét đẻ ra
    60 dòng đỏ thì lượt quét ấy đang duyệt toàn bộ lịch sử; với dữ liệu thật nó ra 851.

    Cách làm xanh KHÔNG phải là nâng trần: thêm mốc lùi (`canh_bao_lui_ngay`) để robot chỉ quét sự
    kiện gần đây, và gắn nguon='lich_su' cho phần còn lại để nó đi vào việc dọn dữ liệu chứ không
    nằm chung với vi phạm phát sinh.
    """
    from app.services import rules as R
    db = db_()
    truoc = {}
    for a in db.execute(select(Alert)).scalars():
        truoc[a.kind] = truoc.get(a.kind, 0) + 1
    _tao_chuyen_cu(db, 60)
    R.run_robots(db)
    sau = {}
    for a in db.execute(select(Alert)).scalars():
        sau[a.kind] = sau.get(a.kind, 0) + 1
    db.close()

    ngap = {k: sau[k] - truoc.get(k, 0) for k in sau
            if sau[k] - truoc.get(k, 0) > Y.TRAN_MOT_LOAI_MOT_LUOT
            and k not in Y.QUET_TOAN_LICH_SU_DUOC_PHEP}
    assert not ngap, (
        f"một lượt quét sinh quá {Y.TRAN_MOT_LOAI_MOT_LUOT} dòng cùng loại: {ngap}\n"
        "  60 chuyến dựng ra đều kết thúc hơn một năm trước — đúng hình dạng dữ liệu lịch sử đổ từ\n"
        "  Vietrip sang. Robot quét mọi chuyến 'ket_thuc' quá hạn, không có mốc thời gian nào.\n"
        "  Sửa bằng mốc lùi + cột nguon, KHÔNG bằng cách nâng TRAN_MOT_LOAI_MOT_LUOT.")


def test_vd6_quet_lai_khong_duoc_de_them_dong_moi():
    """Chạy hai lượt liên tiếp phải ra cùng số dòng. Đây là tài sản đang CÓ và phép thử giữ nó lại.

    Mỗi robot hiện tự dò trùng theo (kind, ref) trước khi thêm. Không có gì nhắc người viết robot
    thứ mười hai làm như vậy, và một nơi quên là mỗi lượt quét đẻ thêm một lượt dòng.
    """
    from app.services import rules as R
    db = db_()
    R.run_robots(db)
    n1 = db.execute(select(Alert)).scalars().all()
    R.run_robots(db)
    n2 = db.execute(select(Alert)).scalars().all()
    db.close()
    assert len(n2) == len(n1), (
        f"quét lượt hai đẻ thêm {len(n2) - len(n1)} dòng (lượt một {len(n1)} → lượt hai {len(n2)}). "
        "Có nơi thêm Alert mà không dò (kind, ref) đang mở.")


# =================================================================== chống trùng, đọc mã

def _noi_dung_alert() -> dict[str, set[str]]:
    """{đường dẫn tệp: {tên hàm cấp ngoài cùng có dựng Alert(...)}} — đọc bằng ast, không chạy mã."""
    ra: dict[str, set[str]] = {}
    for goc, _, tep in os.walk(GOC_APP):
        for t in sorted(tep):
            if not t.endswith(".py"):
                continue
            duong = os.path.join(goc, t)
            src = open(duong, encoding="utf-8", errors="replace").read()
            if "Alert(" not in src:
                continue
            try:
                cay = ast.parse(src)
            except SyntaxError:
                continue
            for nut in cay.body:
                if not isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                dung = any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "Alert"
                           for c in ast.walk(nut))
                if dung:
                    rel = os.path.relpath(duong, os.path.dirname(GOC_APP)).replace(os.sep, "/")
                    ra.setdefault(rel, set()).add(nut.name)
    return ra


def test_vd4_moi_noi_dung_canh_bao_deu_phai_co_cua_do_trung():
    """Đọc mã: hàm nào dựng Alert(...) thì trong chính hàm ấy phải có phép dò dòng đang mở.

    Phép thử này XANH hôm nay. Nó ở đây để giữ cho ngày mai vẫn xanh: người viết robot mới không có
    gì nhắc, và một nơi quên dò trùng thì mỗi lượt quét đẻ thêm một lượt dòng — 1.703 thành 3.406.
    """
    hong = []
    for tep, ham in sorted(_noi_dung_alert().items()):
        src = open(os.path.join(os.path.dirname(GOC_APP), tep), encoding="utf-8").read()
        cay = ast.parse(src)
        for nut in cay.body:
            if not isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)) or nut.name not in ham:
                continue
            if f"{tep}::{nut.name}" in Y.KHONG_CAN_DO_TRUNG:
                continue
            than = ast.get_source_segment(src, nut) or ""
            if "select(Alert)" not in than:
                hong.append(f"{tep}::{nut.name}")
    assert not hong, (
        "dựng Alert mà trong cùng hàm không có phép dò dòng đang mở: " + ", ".join(hong)
        + "\n  Khuôn đang dùng ở các robot khác:\n"
          "      if not db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref,\n"
          "                                            Alert.resolved == False)).scalars().first():\n"
          "          db.add(Alert(...))\n"
          "  Cố ý sinh dòng mới mỗi lần thì khai vào KHONG_CAN_DO_TRUNG kèm lý do.")


def test_vd7_moi_ngoai_le_deu_phai_co_ly_do_du_dai_va_danh_sach_phai_ngan():
    """Ngoại lệ là lối thoát dễ nhất, nên nó phải tốn công hơn việc làm đúng.

    Hai bảng khai dưới đây đều là chỗ 1.703 dòng đỏ có thể lặng lẽ quay lại: một bảng cho phép quét
    toàn lịch sử, một bảng cho phép bỏ dò trùng.
    """
    for ten, bang in (("QUET_TOAN_LICH_SU_DUOC_PHEP", Y.QUET_TOAN_LICH_SU_DUOC_PHEP),
                      ("KHONG_CAN_DO_TRUNG", Y.KHONG_CAN_DO_TRUNG)):
        assert len(bang) <= 5, (
            f"{ten} có {len(bang)} dòng. Quá 5 thì đó không còn là ngoại lệ, đó là quy tắc mới — "
            f"và quy tắc mới phải được nói ra chứ không lớn dần trong một bảng ngoại lệ.")
        ngan = {k: v for k, v in bang.items() if len(v.strip()) < Y.MIN_LY_DO}
        assert not ngan, (
            f"{ten}: lý do dưới {Y.MIN_LY_DO} ký tự ở {sorted(ngan)} — viết đủ để người duyệt phải nghĩ.")
