# -*- coding: utf-8 -*-
"""TC-46 · "ĐANG BÁN" VÀ "ĐANG CHẠY" LÀ HAI CÂU HỎI KHÁC NHAU — anh Tuấn chốt 16/9/2026.

Bản vẽ v3.0 thêm thẻ "Tour đang chạy" vào hàng thẻ nhỏ. Dựng nó làm lộ ra một điều mà chín vòng
trước không phải đối mặt:

    HỆ THỐNG KHÔNG CÓ TRẠNG THÁI "ĐANG CHẠY".

Một chuyến được duyệt xong mang trạng thái `da_duyet` và giữ nguyên suốt từ lúc mở bán, qua cả
hành trình, tới khi Điều hành bấm kết thúc. Nên con số "Tour đang bán" của bản cũ thật ra là "số
chuyến đã duyệt", gồm cả những đoàn đang trên đường — và không ai đọc ra điều đó từ cái nhãn.

Anh Tuấn chọn TÁCH HẲN, chấp nhận hệ quả: con số "Tour đang bán" trên màn hình NHỎ ĐI so với hôm
qua. Ghi ra để vòng sau đọc bản lưu cũ không tưởng là mất số.

══════════════════════════════════════════════════════════════════════════════════════════════
BA CHỖ DỄ HỎNG
══════════════════════════════════════════════════════════════════════════════════════════════
1. HAI NHÓM CHỒNG NHAU. Nếu "đang bán" vẫn đếm mọi chuyến đã duyệt còn "đang chạy" đếm những
   chuyến đang đi, thì các chuyến đang đi bị đếm ở CẢ HAI thẻ — hai thẻ cạnh nhau cộng lại ra một
   con số lớn hơn sự thật, mà nhìn hoàn toàn bình thường.
2. NHÓM THỨ BA BIẾN MẤT. Chuyến đã qua ngày về mà trạng thái vẫn "đã duyệt" không thuộc hai nhóm
   kia. Bỏ nó đi thì phép cộng hụt, và chỗ hụt ấy lặng lẽ — trong khi nó chính là một việc tồn:
   Điều hành chưa bấm kết thúc thì tiền chuyến ấy chưa vào hàng đợi quyết toán.
3. CHUYẾN THIẾU NGÀY — hoá ra là một GIẢ ĐỊNH, không phải một nhánh mã. Phép thử thử nạp một
   chuyến không có ngày và kho TỪ CHỐI: hai cột ngày đều NOT NULL. Nên thứ đáng canh không phải
   cách xếp chuyến ấy, mà là chính giả định "hai cột ngày luôn có" — xem phép thử cuối mục 1.
"""
import datetime as dt
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Tour
from app.services import dem_tour as DT

GOC = Path(__file__).resolve().parents[2]
TRANG = GOC / "web" / "app" / "page.tsx"
VH = GOC / "web" / "components" / "KhoiVanHanh.tsx"
BANG_DIEU_KHIEN = GOC / "backend" / "app" / "services" / "dashboard.py"

HOM_NAY = dt.date(2026, 9, 16)


def _db():
    """Kho rỗng, dựng đúng những bảng khai được — xem chú thích cùng tên ở test_tc44."""
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _nap(db, chuyen):
    """Ghi thẳng vào bảng, không qua ORM: bảng `tours` có nhiều cột bắt buộc không liên quan gì
    tới phép đếm này, và dựng đủ chúng chỉ làm phép thử khó đọc."""
    db.execute(insert(Tour.__table__), [
        dict(code=c, name=c, tour_type="package", operator_id=1,
             start_date=a, end_date=b, status=st)
        for c, a, b, st in chuyen])
    db.commit()


def _ma(s: str) -> str:
    s = re.sub(r"\{/\*(?:.|\n)*?\*/\}", " ", s)
    s = re.sub(r"/\*(?:.|\n)*?\*/", " ", s)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


# ═════════════════ 1 · PHÉP CHIA BA GIAI ĐOẠN ═════════════════

def test_ba_giai_doan_khong_trung_nhau_va_cong_ra_dung_tong():
    """Chỗ hỏng số 1 và số 2 cùng một lúc."""
    db = _db()
    _nap(db, [
        ("A", dt.date(2026, 9, 20), dt.date(2026, 9, 25), "da_duyet"),   # chưa đi
        ("B", dt.date(2026, 9, 10), dt.date(2026, 9, 18), "da_duyet"),   # đang đi
        ("C", dt.date(2026, 9, 16), dt.date(2026, 9, 16), "da_duyet"),   # khởi hành hôm nay
        ("D", dt.date(2026, 9, 1), dt.date(2026, 9, 15), "da_duyet"),    # đã về, chưa đóng sổ
        ("E", dt.date(2026, 8, 1), dt.date(2026, 8, 5), "ket_thuc"),     # không thuộc phép đếm
    ])
    r = DT.theo_giai_doan(db, hom_nay=HOM_NAY)
    assert r == {"dang_ban": 1, "dang_chay": 2, "da_ve_chua_dong_so": 1}
    assert sum(r.values()) == DT.dang_ban(db), (
        "Ba nhóm phải PHỦ KÍN các chuyến đã duyệt và không chồng nhau. Hụt thì một chuyến biến mất "
        "khỏi màn hình; chồng thì nó được đếm hai lần ở hai thẻ cạnh nhau."
    )


def test_khoi_hanh_dung_hom_nay_la_dang_chay_khong_phai_dang_ban():
    """Đoàn lên xe sáng nay thì không còn là chuyến đang bán nữa."""
    db = _db()
    _nap(db, [("C", HOM_NAY, HOM_NAY + dt.timedelta(days=3), "da_duyet")])
    assert DT.theo_giai_doan(db, hom_nay=HOM_NAY)["dang_chay"] == 1


def test_ve_dung_hom_nay_van_la_dang_chay():
    """Ngày về là ngày CUỐI của hành trình, không phải ngày đã kết thúc hành trình."""
    db = _db()
    _nap(db, [("C", HOM_NAY - dt.timedelta(days=4), HOM_NAY, "da_duyet")])
    r = DT.theo_giai_doan(db, hom_nay=HOM_NAY)
    assert r["dang_chay"] == 1 and r["da_ve_chua_dong_so"] == 0


def test_hai_cot_ngay_phai_con_bat_buoc():
    """Chỗ hỏng số 3, và nó hoá ra là một GIẢ ĐỊNH chứ không phải một nhánh mã.

    Bản đầu của vòng này viết sẵn nhánh "chuyến thiếu ngày thì xếp vào đang chạy", rồi phép thử
    thử nạp một chuyến không có ngày — và kho TỪ CHỐI: `tours.start_date` và `tours.end_date` đều
    NOT NULL. Tức nhánh ấy không bao giờ chạy.

    Nhánh phòng hờ vẫn giữ trong `theo_giai_doan` (rẻ, và nó chọn chỗ ít sai nhất nếu có ngày nào
    cột đổi luật), nhưng thứ đáng canh là CHÍNH GIẢ ĐỊNH: ngày nào hai cột ấy cho phép rỗng thì
    phép chia ba giai đoạn phải được đọc lại, và phép thử này là chỗ báo.
    """
    for ten in ("start_date", "end_date"):
        cot = Tour.__table__.columns[ten]
        assert not cot.nullable, (
            f"Cột `tours.{ten}` nay cho phép rỗng. Đọc lại `dem_tour.theo_giai_doan`: một chuyến "
            "đã duyệt mà không có ngày thì không nói được là chưa đi hay đã về, và cách xếp nó "
            "quyết định con số trên hai thẻ cạnh nhau."
        )


def test_khong_tu_doc_dong_ho_may_chu():
    """Mọi phép tính theo ngày đều phải thử được ở một ngày bất kỳ — cùng luật với lich_chup."""
    with pytest.raises(TypeError):
        DT.theo_giai_doan(_db())            # thiếu `hom_nay` thì phải báo lỗi, không lấy hôm nay


# ═════════════════ 2 · XE HÔM NAY — CÙNG MỘT LUẬT, ÁP CHO XE ═════════════════
#
# Anh Tuấn 16/9/2026: "cũng như xe hôm nay đang chạy là bao nhiêu, nằm ở bãi là bao nhiêu... khi
# có lịch khởi hành cụ thể thì hệ thống sẽ tự nhận ra đang chạy là bao nhiêu".
#
# Nguồn là LỆNH ĐIỀU XE (`dispatch_orders`), không phải nhật trình chuyến (`fleet_trips`) — xem
# chú thích đầu services/xe_hom_nay.py. Bốn phép thử dưới đây canh bốn chỗ dễ sai của phép đếm ấy.

def _db_xe():
    """Chỉ dựng HAI bảng cần thiết, sau khi nạp đủ mô-đun mô hình để khoá ngoại giải được.

    `create_all` không dùng được ở đây: bảng `vehicles` trỏ khoá ngoại sang `companies` và
    `employees`, và trong bản checkout rút gọn thì kiểu cột không giải ra được nếu chưa nạp hai
    mô-đun kia. Nạp rồi dựng đúng hai bảng là cách gọn nhất, và nó chạy y hệt ở CI.
    """
    import app.models.core        # noqa: F401 — nạp để `companies` có mặt
    import app.models.fleet       # noqa: F401 — nạp để `fleet_partners` có mặt
    from app.models.hr import DispatchOrder, Vehicle
    e = create_engine("sqlite://")
    Vehicle.__table__.create(e)
    DispatchOrder.__table__.create(e)
    return sessionmaker(bind=e)(), Vehicle, DispatchOrder


def _dung_doi_xe():
    """Ba xe điều được, một xe đã bán, một xe tắt hoạt động; năm lệnh điều xe quanh ngày 16/9."""
    from sqlalchemy import insert as _insert
    db, Vehicle, DispatchOrder = _db_xe()
    db.execute(_insert(Vehicle.__table__), [
        dict(plate="51A-001", active=True, lifecycle="dang_khai_thac", op_right="so_huu"),
        dict(plate="51A-002", active=True, lifecycle="dang_khai_thac", op_right="hop_tac"),
        dict(plate="51A-003", active=True, lifecycle="dang_khai_thac", op_right="so_huu"),
        dict(plate="51A-004", active=True, lifecycle="da_ban", op_right="so_huu"),
        dict(plate="51A-005", active=False, lifecycle="dang_khai_thac", op_right="so_huu"),
    ])
    db.execute(_insert(DispatchOrder.__table__), [
        # Xe 1 mang HAI lệnh chồng ngày — vẫn phải đếm là MỘT xe.
        dict(tour_id=1, vehicle_id=1, driver_id=1, date_from=dt.date(2026, 9, 14),
             date_to=dt.date(2026, 9, 18), status="da_xac_nhan", incident_note=""),
        dict(tour_id=2, vehicle_id=1, driver_id=1, date_from=dt.date(2026, 9, 16),
             date_to=dt.date(2026, 9, 17), status="cho_xac_nhan", incident_note=""),
        # Xe 2: lệnh CHỜ XÁC NHẬN, có sự cố.
        dict(tour_id=3, vehicle_id=2, driver_id=2, date_from=dt.date(2026, 9, 16),
             date_to=dt.date(2026, 9, 16), status="cho_xac_nhan", incident_note="Thủng lốp"),
        # Xe 3: một lệnh đã xong từ hôm qua, một lệnh hôm nay nhưng ĐÃ HUỶ.
        dict(tour_id=4, vehicle_id=3, driver_id=3, date_from=dt.date(2026, 9, 10),
             date_to=dt.date(2026, 9, 15), status="hoan_thanh", incident_note=""),
        dict(tour_id=5, vehicle_id=3, driver_id=3, date_from=dt.date(2026, 9, 16),
             date_to=dt.date(2026, 9, 20), status="huy", incident_note=""),
    ])
    db.commit()
    return db


def test_xe_dem_dung_bon_con_so():
    from app.services import xe_hom_nay as XE
    r = XE.dem(_dung_doi_xe(), hom_nay=HOM_NAY)
    assert r == {"dieu_duoc": 3, "dang_chay": 2, "o_bai": 1,
                 "bat_thuong": 1, "lech": 0, "co_nguon": True}, r


def test_xe_dem_XE_khong_dem_LENH():
    """Xe 1 mang hai lệnh chồng ngày. Đếm lệnh thì đội xe 3 chiếc hiện ra 3 xe đang chạy."""
    from app.services import xe_hom_nay as XE
    assert XE.dem(_dung_doi_xe(), hom_nay=HOM_NAY)["dang_chay"] == 2


def test_xe_lenh_cho_xac_nhan_van_tinh_lenh_huy_thi_khong():
    """Lệnh chờ xác nhận là chuyến ĐÃ ĐƯỢC XẾP — xe ấy vẫn đang trên đường. Đòi 'đã xác nhận' mới
    đếm là để một thao tác hành chính quyết định con số vận hành."""
    from app.services import xe_hom_nay as XE
    r = XE.dem(_dung_doi_xe(), hom_nay=HOM_NAY)
    assert r["bat_thuong"] == 1, "Xe 2 chỉ có lệnh CHỜ XÁC NHẬN — vẫn phải tính."
    assert r["dang_chay"] == 2, "Xe 3 chỉ có lệnh ĐÃ HUỶ hôm nay — không được tính."


def test_xe_o_bai_la_hieu_khong_phai_phep_dem_thu_hai():
    """Hai phép đếm độc lập thì ngày một bên đổi điều kiện là ngày chúng không còn cộng ra tổng."""
    from app.services import xe_hom_nay as XE
    r = XE.dem(_dung_doi_xe(), hom_nay=HOM_NAY)
    assert r["dang_chay"] + r["o_bai"] == r["dieu_duoc"]
    ma = _ma((GOC / "backend" / "app" / "services" / "xe_hom_nay.py").read_text(encoding="utf-8"))
    assert "dieu_duoc - dang_chay" in ma, "Ở bãi phải là HIỆU."


def test_xe_da_ban_hay_ngung_khai_thac_khong_nam_o_bai():
    """Xe đã bán không 'nằm ở bãi' — nó không còn là xe của mình. Gộp vào là mỗi xe bán đi lại làm
    bãi xe đầy thêm một chiếc."""
    from app.services import xe_hom_nay as XE
    assert XE.dem(_dung_doi_xe(), hom_nay=HOM_NAY)["dieu_duoc"] == 3


def test_xe_khong_tu_doc_dong_ho():
    from app.services import xe_hom_nay as XE
    with pytest.raises(TypeError):
        XE.dem(_dung_doi_xe())


def test_xe_khong_doc_nhat_trinh_chuyen():
    """`fleet_trips` là nhật trình tài xế ghi TRONG hoặc SAU chuyến. Hỏi 'hôm nay xe nào đang đi'
    bằng nó là hỏi một thứ chưa được viết xong — con số sẽ luôn hụt, và hụt một cách không ai phát
    hiện được."""
    # Canh Ở DÒNG NHẬP, không canh chuỗi ký tự: chính lời giải thích vì sao KHÔNG đọc nhật trình
    # cũng nhắc tên bảng ấy, và một phép soát theo chuỗi sẽ báo oan lời giải thích của chính mình
    # (đúng bài học TC-41: cấm một HÀNH VI, không cấm một dãy ký tự).
    nhap = [d for d in (GOC / "backend" / "app" / "services" / "xe_hom_nay.py")
            .read_text(encoding="utf-8").splitlines() if d.startswith(("import ", "from "))]
    assert any("DispatchOrder" in d for d in nhap), "Phải đọc LỆNH ĐIỀU XE."
    assert not any("fleet" in d for d in nhap), (
        "Đang nhập mô hình của nhật trình chuyến — nguồn phải là lệnh điều xe."
    )


def test_xe_khong_co_nguon_khac_voi_hom_nay_khong_dieu_xe():
    """0 là số THẬT khi đã có bảng xe; khi chưa có xe nào thì 0 là 'chưa có nguồn'."""
    from app.services import xe_hom_nay as XE
    db, _, _ = _db_xe()
    r = XE.dem(db, hom_nay=HOM_NAY)
    assert r["co_nguon"] is False and r["dieu_duoc"] == 0
    assert XE.dem(_dung_doi_xe(), hom_nay=dt.date(2026, 1, 1))["co_nguon"] is True, (
        "Có xe mà hôm ấy không điều lệnh nào thì vẫn là CÓ NGUỒN, và 'đang chạy 0' là số thật."
    )


# ═════════════════ 3 · MÀN HÌNH ═════════════════

def test_may_chu_gui_ba_giai_doan_xuong_man_hinh():
    ma = _ma(BANG_DIEU_KHIEN.read_text(encoding="utf-8"))
    assert 'sec["tour_giai_doan"] = DT.theo_giai_doan(db, hom_nay=today)' in ma, (
        "Phép chia theo ngày phải nằm ở máy chủ và gửi xuống — màn hình không tự chia (ranh giới 09/9)."
    )


def test_man_hinh_khong_tu_chia_giai_doan():
    """Màn hình chỉ được ĐỌC ba con số ấy, không tự so ngày.

    SỬA 22/10/2026 (TQ-1): các ô tour chuyển vào mục Vận hành (components/KhoiVanHanh.tsx) — soát
    đúng hàng «Hoạt động tour». (Phần đầu tệp ấy có so giờ để báo «số cũ» của MỐC dữ liệu; đó
    không phải phép chia giai đoạn chuyến nên nằm ngoài vùng soát.)"""
    ma = _ma(VH.read_text(encoding="utf-8"))
    khoi = ma[ma.index("Hoạt động tour"): ma.index("Tồn đọng công việc")]
    for cam in ("start_date", "end_date", "new Date(", "Date.now"):
        assert cam not in khoi, f"Hàng thẻ đang tự so ngày ({cam}) — phép ấy thuộc về máy chủ."


def test_the_chua_dong_so_co_cho_hien_va_co_bo_phan():
    """Nhóm thứ ba không có thẻ riêng, nhưng phải đọc được từ màn hình kèm bộ phận phải xử lý."""
    ma = _ma(VH.read_text(encoding="utf-8"))   # TQ-1: ô Chờ quyết toán nay ở mục Vận hành
    assert "da_ve_chua_dong_so" in ma, "Máy chủ đếm rồi mà màn hình không hiện là việc tồn vô hình."
    assert "chưa đóng sổ" in ma and "Điều hành" in ma, (
        "Phải nói rõ việc gì và ai phải làm — ranh giới 09/9."
    )


def test_hai_the_khong_lay_cung_mot_con_so():
    """Chỗ hỏng số 1, canh ở phía màn hình: hai thẻ phải đọc hai trường khác nhau.
    SỬA 22/10/2026 (TQ-1): hai ô nay ở hàng «Hoạt động tour» của mục Vận hành."""
    ma = _ma(VH.read_text(encoding="utf-8"))
    khoi = ma[ma.index("Hoạt động tour"): ma.index("Tồn đọng công việc")]
    assert "gd.dang_ban" in khoi and "gd.dang_chay" in khoi
    assert "c.da_duyet" not in khoi, (
        "Thẻ 'Tour đang bán' còn đọc tổng đã duyệt — tức nó vẫn gồm cả những chuyến đang chạy, và "
        "hai thẻ cạnh nhau chồng lên nhau."
    )
