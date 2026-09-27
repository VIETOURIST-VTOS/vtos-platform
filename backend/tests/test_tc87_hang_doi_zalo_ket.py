"""TC-87 · HAI TRĂM LỜI MỜI NẰM IM HAI NGÀY — và không ai được báo.

Đo bản đang chạy ngày 27/9/2026, khi anh Tuấn nhờ thử gửi mã khảo sát qua Zalo OA:

  · `oa` = true — token OA còn sống.
  · `zns_templates` = {} — chưa mẫu nào được Zalo duyệt.
  · hàng đợi: **200 tin** ở trạng thái `cho_cau_hinh`, tất cả kênh `zns`, mục đích `cham_soc`,
    tạo lúc 20:45:12–20:45:14 ngày 26/9 — tức một lượt chạy duy nhất của `gui_loi_moi_cham_diem`,
    đủ 200 là mức trần một lượt.

Không tin nào tới khách. Nguyên nhân dây chuyền: webhook OA chưa khai (nhật ký máy chủ cả ngày
không có một dòng `POST /api/v1/zalo/webhook` nào) → không khách nào có `zalo_uid` → mọi tin rơi
xuống đường ZNS → ZNS chưa mẫu → xếp `cho_cau_hinh`.

CHỖ NGUY HIỂM KHÔNG PHẢI BA MẮT XÍCH ẤY. Ba cái đó là cấu hình, khai xong là chạy. Chỗ nguy hiểm
là robot vẫn chạy đúng và vẫn trả về "đã xếp N tin" mỗi lượt: một con số tăng đều trông y hệt một
hệ thống đang hoạt động. Hai ngày trôi qua, không một cảnh báo nào, và người duy nhất phát hiện ra
là người tình cờ đi thử một việc khác.

Mỗi lời mời còn đeo một MÃ KHẢO SÁT CÓ HẠN. Im lặng đủ lâu thì mã chết trước khi khách kịp mở, và
phần khảo sát của kỳ ấy mất trắng — không thu lại được, vì tour đã qua.

PHÉP THỬ NÀY CANH BỐN CHỖ:
 1. Quá ngưỡng thì PHẢI có cảnh báo, và cảnh báo phải tới CNTT và P.TGĐ Marketing — hai người làm
    được việc cấu hình. Gửi cho Kinh doanh là gửi cho người không sửa được gì.
 2. Dưới ngưỡng thì KHÔNG reo. Một cảnh báo reo cả khi không có chuyện là một cảnh báo bị tắt.
 3. Hết chuyện thì cảnh báo cũ TỰ RÚT. Cùng luật với `cham_soc_qua_han` — cảnh báo chỉ thêm mà
    không bao giờ rút thì bảng dài mãi và người ta thôi đọc nó.
 4. Ngưỡng là THAM SỐ có khai, không phải số viết cứng.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Alert
from app.models.crm import ZaloMessage
from app.services import cskh as CS
from app.services import rules as R


@pytest.fixture()
def db():
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    yield s
    s.close()


def _tin(db, n, luc=None, trang_thai="cho_cau_hinh"):
    for i in range(n):
        db.add(ZaloMessage(kind="zns", phone=f"09000000{i:02d}", purpose="cham_soc",
                           status=trang_thai, created_at=luc or datetime.now()))
    db.commit()


def _canh_bao(db):
    return db.execute(select(Alert).where(Alert.kind == "zalo_ket_hang",
                                          Alert.resolved == False)).scalars().all()   # noqa: E712


def test_tc87_1_qua_nguong_thi_reo_va_goi_dung_nguoi(db):
    _tin(db, 25, luc=datetime.now() - timedelta(days=2))
    CS.robot_cskh(db)

    ds = _canh_bao(db)
    assert len(ds) == 1, "200 tin nam im hai ngay ma khong co canh bao nao - dung loi da xay ra 26-27/9"
    a = ds[0]
    assert a.level == "red"
    for vai in ("cntt", "ptgd_mkt"):
        assert vai in a.to_roles, f"thieu {vai}: hai viec phai lam deu la cau hinh, khong phai ma"
    assert "25" in a.message, "phai noi ro bao nhieu tin dang ket"


def test_tc87_2_duoi_nguong_thi_im(db):
    _tin(db, 3)
    CS.robot_cskh(db)
    assert _canh_bao(db) == [], "reo ca khi khong co chuyen thi som muon cung bi tat"


def test_tc87_3_het_chuyen_thi_tu_rut(db):
    _tin(db, 25)
    CS.robot_cskh(db)
    assert len(_canh_bao(db)) == 1

    # Khai xong cấu hình, hàng đợi được đẩy đi: mọi tin chuyển sang đã gửi.
    for m in db.execute(select(ZaloMessage)).scalars():
        m.status = "da_gui"
    db.commit()

    CS.robot_cskh(db)
    assert _canh_bao(db) == [], "canh bao chi them ma khong bao gio rut thi bang dai mai"


def test_tc87_4_nguong_la_tham_so_co_khai(db):
    assert R.get_param(db, "zalo_hang_doi_nguong"), "nguong phai la tham so, khong viet cung"
    ten = [x[0] for x in R.PARAMS] if hasattr(R, "PARAMS") else []
    if ten:
        assert "zalo_hang_doi_nguong" in ten, "tham so phai duoc KHAI de hien tren man hinh cai dat"
