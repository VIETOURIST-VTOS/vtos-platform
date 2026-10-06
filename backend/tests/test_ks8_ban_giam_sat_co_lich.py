# -*- coding: utf-8 -*-
"""BÀN GIÁM SÁT PHẢI CÓ LỊCH — và phải nói ra tuổi của tấm ảnh nó đang vẽ.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

Ngày 30/9/2026, màn hình `/kiem-soat` trên hệ thật treo đỏ một việc nghiêm trọng:

    1 đường dẫn trả lỗi máy chủ trong 7 ngày gần đây (116 lượt).
    Đường dẫn hỏng nhiều nhất: POST /api/v1/robot/sepay/pull ×116

Đọc bảng sự kiện kỹ thuật 7 ngày gần nhất thì đường dẫn ấy KHÔNG có lấy một lượt nào. Lần cuối nó
hỏng là 10/9/2026 22:15 — hai mươi ngày trước. Việc đã hết từ lâu mà vẫn nằm đỏ trên bàn của Chủ tịch.

Nguyên nhân không nằm trong `KS.quet`: hàm ấy đã biết tự đóng việc đã hết (`con=False` cho mã không
còn thấy ở lượt quét mới). Nguyên nhân là **vòng quét không có lịch nào cả**. Tệp
`.github/workflows/robots.yml` xếp lịch cho Vietrip, SePay, báo cáo ngày/tuần/tháng — và không có
một dòng nào gọi vòng quét Kiểm soát. Nó chỉ chạy được bằng nút trên màn hình, tức là chỉ chạy khi
có người nhớ ra mà bấm. Ba lần bấm trong đời: 08/9, 09/9, 10/9.

Hậu quả đi theo cả hai chiều, và chiều thứ hai nặng hơn:
  1. việc đã hết vẫn treo — bàn giám sát mất uy tín, người đọc học cách bỏ qua màu đỏ;
  2. việc MỚI không mở ra được — lỗi 500 của cửa nạp bù chạy từ 27/9 đến 29/9, mười lượt, và
     robot Kiểm soát không hề biết. Thứ tìm ra nó là một người đi đọc bảng sự kiện bằng tay.

Một bàn giám sát đứng hình nguy hơn một bàn giám sát trống, vì người đọc nó tin rằng mình đang nhìn
hôm nay.

Ba việc tệp này giữ:
  · cửa lịch có thật, và mở bằng ROBOT_TOKEN chứ không bằng vai trò người;
  · tệp lịch THẬT SỰ gọi cửa ấy — phép thử đọc `robots.yml`, vì lỗi gốc nằm đúng trong tệp đó
    chứ không nằm trong mã Python nào;
  · bàn khai ra tuổi của mình, và tuổi ấy đọc từ chuỗi kiểm toán chứ không từ `lan_cuoi` của phát
    hiện — một lượt quét sạch không đóng dấu lên phát hiện nào, nên đọc `max(lan_cuoi)` sẽ làm
    "bảng sạch" và "robot đã chết" hiện ra giống nhau.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import datetime as dt                                           # noqa: E402
import io                                                       # noqa: E402

from sqlalchemy import create_engine                            # noqa: E402
from sqlalchemy.orm import sessionmaker                         # noqa: E402

from app.db.session import Base                                 # noqa: E402
from app.models.core import AuditLog                            # noqa: E402
from app.models.kiem_soat import KsPhatHien                     # noqa: E402
from app.services import ks_robot as KS                         # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LICH = os.path.join(GOC, ".github", "workflows", "robots.yml")
DUONG_DAN_QUET = "/kiem-soat/robot/quet"


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _da_quet(db, cach_day_gio: float):
    """Ghi một dấu vết "đã quét" vào chuỗi kiểm toán, lùi lại `cach_day_gio` giờ."""
    ts = dt.datetime.now() - dt.timedelta(hours=cach_day_gio)
    db.add(AuditLog(ts=ts, actor="robot_ks", role="bks", action="robot_ks_quet", entity="kiem_soat",
                    after={"moi": 0, "lap_lai": 0, "het": 0}, prev_hash="0" * 64, hash="x" * 64))
    db.commit()


# ============================== 1. CỬA LỊCH ==============================
def test_co_cua_lich_cho_vong_quet():
    """Phải có một cửa POST mà máy gọi được. Không có cửa thì không có lịch nào khả thi."""
    from app.main import app
    duong = {r.path for r in app.routes if hasattr(r, "endpoint")}
    assert "/api/v1" + DUONG_DAN_QUET in duong, (
        "Không có cửa lịch cho vòng quét Kiểm soát. Vòng quét chỉ chạy khi có người bấm nút, và "
        "trên hệ thật điều đó nghĩa là 19 ngày không quét.")


def test_cua_lich_doi_robot_token():
    """Cửa máy gọi phải chặn bằng ROBOT_TOKEN. Một cửa quét mở trần là cửa cho người ngoài đọc
    toàn bộ phát hiện giám sát của công ty."""
    from app.main import app
    r = next(x for x in app.routes
             if getattr(x, "path", "") == "/api/v1" + DUONG_DAN_QUET)
    ten = [getattr(d.call, "__name__", "") for d in (r.dependant.dependencies or [])]
    assert "robot_auth" in ten, f"Cửa lịch không có robot_auth: {ten}"


def test_cua_lich_khong_cham_diem():
    """Quét là ĐỌC, chấm điểm là PHÁN. Chỉ đem đọc ra lịch.

    Điểm phòng ban gắn vào hồ sơ con người và theo chỉ đạo 07/9/2026 nó chỉ là ĐỀ XUẤT tới khi Chủ
    tịch hậu kiểm. Một cái lịch tự chấm điểm mỗi đêm đẻ ra hàng loạt điểm không ai đối chất được.
    """
    import inspect
    from app.api.v1 import kiem_soat as MOD
    ma = inspect.getsource(MOD.robot_quet)
    assert "cham_diem" not in ma, "Cửa lịch không được gọi chấm điểm"


# ============================== 2. TỆP LỊCH THẬT SỰ GỌI CỬA ==============================
def test_lich_robot_co_goi_vong_quet():
    """PHÉP THỬ BẮT ĐÚNG LỖI GỐC.

    Lỗi ngày 30/9 không nằm trong một dòng Python nào — mã `quet` hoàn toàn đúng. Nó nằm ở chỗ
    `robots.yml` không nhắc tên vòng quét. Nên phép thử phải đọc chính tệp lịch ấy.
    """
    assert os.path.exists(LICH), f"Không thấy tệp lịch robot: {LICH}"
    noi_dung = io.open(LICH, encoding="utf-8").read()
    assert DUONG_DAN_QUET in noi_dung, (
        f"{LICH} không gọi {DUONG_DAN_QUET}. Vòng quét Kiểm soát lại không có lịch — đó đúng là "
        f"tình trạng đã để bàn giám sát của Chủ tịch đứng hình 19 ngày.")


def test_vong_quet_co_lich_hang_ngay():
    """Không chỉ "có được gọi ở đâu đó" mà phải nằm trong nhánh chạy MỖI NGÀY.

    Nếu nó rơi vào nhánh `tuan` hay `thang` thì bàn giám sát vẫn cũ tới bảy ngày, và bảy ngày là
    quá dài cho một lỗi 500 đang chạy.
    """
    noi_dung = io.open(LICH, encoding="utf-8").read()
    i = noi_dung.index(DUONG_DAN_QUET)
    truoc = noi_dung[:i]
    nhanh = truoc.rsplit("case ", 1)[-1]
    assert "ngay" in nhanh.split(")")[0] or "ngay|" in nhanh, (
        "Vòng quét không nằm trong nhánh chạy hằng ngày")
    assert 'cron: "30 13 * * *"' in noi_dung, (
        "Mất lịch 20:30 giờ VN — nhánh `ngay` không còn gì đánh thức")


# ============================== 3. BÀN KHAI RA TUỔI CỦA MÌNH ==============================
def test_chua_quet_lan_nao_thi_ban_noi_ra():
    """Chưa quét lần nào KHÁC "quét rồi mà không thấy gì". Bàn phải phân biệt được hai chuyện đó."""
    db = _db()
    ra = KS.bang(db)
    assert ra["quet_lan_cuoi"] is None
    assert ra["ban_cu"] is True
    assert ra["ban_cu_ly_do"], "Bàn cũ mà không nói lý do thì màn hình không có gì để hiện"


def test_vua_quet_thi_ban_khong_bi_goi_la_cu():
    db = _db()
    _da_quet(db, cach_day_gio=2)
    ra = KS.bang(db)
    assert ra["ban_cu"] is False
    assert ra["quet_lan_cuoi"] is not None
    assert 1.5 < ra["quet_cach_day_gio"] < 2.5


def test_quet_cach_day_muoi_chin_ngay_thi_ban_la_anh_cu():
    """Đúng tình trạng đo được trên hệ thật ngày 30/9/2026."""
    db = _db()
    _da_quet(db, cach_day_gio=19 * 24)
    ra = KS.bang(db)
    assert ra["ban_cu"] is True
    assert "19" in ra["ban_cu_ly_do"] or "18" in ra["ban_cu_ly_do"]


def test_tuoi_ban_khong_duoc_doc_tu_lan_cuoi_cua_phat_hien():
    """CHỖ DỄ VIẾT SAI NHẤT.

    `max(lan_cuoi)` của bảng phát hiện trông như cùng một con số. Nhưng một vòng quét SẠCH không
    đóng dấu thời gian lên phát hiện nào — và khi ấy `max(lan_cuoi)` đứng lại y hệt lúc robot chết.
    Bảng dựng ở đây: phát hiện cũ 30 ngày, vòng quét cách đây 1 giờ. Bàn phải là MỚI.
    """
    db = _db()
    cu = dt.datetime.now() - dt.timedelta(days=30)
    db.add(KsPhatHien(ma="thu#mot", loai="may_chu_loi", muc="do", tom_tat="viec cu",
                      lan_dau=cu, lan_cuoi=cu, so_lan=1, con=False))
    db.commit()
    _da_quet(db, cach_day_gio=1)
    ra = KS.bang(db)
    assert ra["ban_cu"] is False, (
        "Tuổi bàn đang đọc từ `lan_cuoi` của phát hiện: một lượt quét sạch sẽ bị đọc thành "
        "robot đã chết.")


def test_quet_dong_viec_da_het():
    """Cái lịch chỉ có nghĩa nếu vòng quét thật sự ĐÓNG được việc đã hết.

    Đây là nửa còn lại của lỗi ngày 30/9: `con=False` chạy đúng, nó chỉ chưa bao giờ được gọi.
    """
    db = _db()
    db.add(KsPhatHien(ma="khong_bao_gio_thay#x", loai="may_chu_loi", muc="do",
                      tom_tat="viec khong con", con=True))
    db.commit()
    KS.quet(db, boi="robot_ks")
    p = db.query(KsPhatHien).filter_by(ma="khong_bao_gio_thay#x").one()
    assert p.con is False, "Vòng quét không đóng việc đã hết — bàn sẽ treo đỏ mãi"
    assert KS.quet_lan_cuoi(db) is not None, "Vòng quét không để lại dấu trong chuỗi kiểm toán"
