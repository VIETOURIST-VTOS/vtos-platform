# -*- coding: utf-8 -*-
"""TQ-1 · Các ô tour của mục «Vận hành & công việc» (Chủ tịch chốt v1.1 ngày 22/10/2026).

Ba việc, mỗi việc sửa một con số đang nói sai:

1. QUÁ HẠN QUYẾT TOÁN ĐẾM ĐỦ. `dashboard.build` cắt danh sách ở `.limit(300)` rồi `[:100]`, nên
   ô «100 tour quá hạn» là TRẦN chứ không phải số thật. Ở đây: đếm đủ, danh sách chia trang theo
   thứ tự ổn định (hạn sớm trước, rồi mã), cùng một điều kiện cho cả tổng lẫn danh sách.
   Điều kiện giữ nguyên như hiện hành: chuyến `ket_thuc` đã quá `rules.settlement_deadline`.
   Chuyến `da_dong_so` chờ Kế toán KHÔNG vào đây — nó có cảnh báo `kt_cham` riêng (Chủ tịch chốt).

   KHÔNG NẠP ĐỐI TƯỢNG ORM. Chỉ đọc năm cột dạng bộ; tham số hạn tra một lần cho mỗi (loại, ngày
   kết thúc) — máy chủ có 512 MB, và CF-1 từng sập vì một báo cáo nạp cả sổ.

2. CHỜ QUYẾT TOÁN TÁCH BA NHÓM. Tổng = A (kết thúc) + B (đã đóng sổ, chờ Kế toán) — định nghĩa
   hiện hành, Chủ tịch chốt giữ. C (đã qua ngày về mà Điều hành chưa bấm kết thúc) là DÒNG PHỤ,
   không cộng vào tổng. Ba nhóm là ba trạng thái tách biệt nên không giao nhau.

3. CHUYẾN THIẾU LỊCH. `dem_tour.theo_giai_doan` xếp chuyến đã duyệt mà thiếu ngày đi hoặc ngày
   về vào «đang chạy». Giữ nguyên số chính (tách ra là quyết định nghiệp vụ riêng), nhưng đếm
   riêng để ô ghi «N chuyến thiếu lịch cần rà soát — đang được tính trong số trên».
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Tour


def _han_ngay(db: Session, cache: dict, doan: bool, ket_thuc: date) -> int:
    from app.services import rules as R
    k = ("han_qt_doan" if doan else "han_qt_le", ket_thuc)
    if k not in cache:
        cache[k] = int(R.get_param(db, k[0], ket_thuc))
    return cache[k]


def qua_han_quyet_toan(db: Session, hom_nay: date, trang: int = 1, co: int = 50) -> dict:
    """{"tong", "trang", "co", "dong": [...]} — tổng ĐẦY ĐỦ, danh sách một trang."""
    from app.services import rules as R
    from app.services import segments as SEG
    # Lọc sơ bằng SQL: chuyến về SAU hôm nay − hạn ngắn nhất thì chắc chắn chưa quá hạn.
    han_min = min(int(R.get_param(db, "han_qt_le")), int(R.get_param(db, "han_qt_doan")))
    moc = hom_nay - timedelta(days=han_min)
    cache: dict = {}
    ds = []
    for tid, code, name, end, loai in db.execute(
            select(Tour.id, Tour.code, Tour.name, Tour.end_date, Tour.tour_type)
            .where(Tour.status == "ket_thuc", Tour.end_date.is_not(None), Tour.end_date < moc)).all():
        doan = SEG.mang_of(SimpleNamespace(tour_type=loai, code=code)) == "doan"
        han = end + timedelta(days=_han_ngay(db, cache, doan, end))
        if hom_nay > han:
            ds.append({"tour_id": tid, "code": code, "ten": name, "ket_thuc": end, "han": han,
                       "qua_han_ngay": (hom_nay - han).days, "mang": "doan" if doan else "le"})
    ds.sort(key=lambda r: (r["han"], r["code"] or "", r["tour_id"]))
    co = max(1, min(int(co or 50), 200))
    trang = max(1, int(trang or 1))
    return {"tong": len(ds), "trang": trang, "co": co, "dong": ds[(trang - 1) * co: trang * co]}


def cho_quyet_toan(db: Session, hom_nay: date, qua_han: int | None = None) -> dict:
    """Tổng chờ quyết toán, VÀ bóc nhóm A ra ba phần để màn hình vẽ được một khối lồng.

    QT-1 (Chủ tịch hỏi 23/10/2026: «hai ô này có trùng nhau không?»). Đo ra: KHÔNG trùng,
    nhưng ô «Quá hạn quyết toán» là MỘT LÁT nằm trọn trong nhóm A của ô này
    (681 ⊂ 709 ⊂ 1.742 hôm đo). Hai ô đứng cách nhau một hàng, không chỗ nào nói cái nhỏ
    nằm trong cái lớn, nên đọc lướt thành hai cách đếm một việc. Sửa ở đây: trả luôn ba
    con số con, để màn hình không phải tự trừ và không tự đặt ra một nhóm nào.

    `qua_han` để người gọi truyền VÀO số đã đếm sẵn. `dashboard.build` đếm nó ngay dòng
    trước; thiếu tham số này là mỗi lần dựng bảng điều hành quét bảng tour HAI lượt thay vì một.
    Để trống thì tự đếm, vì phép thử và người gọi lẻ gọi hàm này một mình.

    `chua_co_ngay_ve` ĐẾM THẬT chứ không ghi cứng 0, dù đo 23/10/2026 nó luôn là 0:
    `tours.end_date` là NOT NULL ở cả mô hình lẫn bản nâng cấp gốc, và không bản nâng cấp nào
    đổi. Nhưng điều kiện quá hạn đòi `end_date` khác rỗng, nên NẾU cột ấy có ngày thành
    cho phép rỗng, những chuyến đó sẽ không bao giờ hiện ở ô quá hạn. Lấy hiệu `a - qua_han`
    là lặng lẽ gộp chúng vào «còn trong hạn» — một câu sai mà không ai thấy. Đếm riêng thì
    hôm nay là 0 (màn hình ẩn dòng ấy) và ngày nào khác 0 thì nó tự hiện ra có tên.
    """
    from app.services import dem_tour as DT
    dem = DT.theo_trang_thai(db)
    a, b = dem.get("ket_thuc", 0), dem.get("da_dong_so", 0)
    c = DT.theo_giai_doan(db, hom_nay=hom_nay)["da_ve_chua_dong_so"]
    qh = qua_han_quyet_toan(db, hom_nay, trang=1, co=1)["tong"] if qua_han is None else int(qua_han)
    chua_co_ngay_ve = db.execute(
        select(func.count()).select_from(Tour)
        .where(Tour.status == "ket_thuc", Tour.end_date.is_(None))).scalar_one()
    return {"tong": a + b, "ket_thuc": a, "da_dong_so": b, "da_ve_chua_dong_so": c,
            "qua_han": qh, "con_trong_han": a - qh - chua_co_ngay_ve,
            "chua_co_ngay_ve": chua_co_ngay_ve,
            "cong_thuc": "Tổng = kết thúc chờ quyết toán + đã đóng sổ chờ Kế toán; «đã về chưa đóng sổ» "
                         "là dòng phụ, không cộng vào tổng (Chủ tịch chốt 22/10/2026). "
                         "Kết thúc = quá hạn + còn trong hạn + chưa có ngày về (QT-1, 23/10/2026)"}


def dem_thieu_lich(cap_ngay, hom_nay: date) -> int:
    """Phép đếm thuần trên các cặp (ngày đi, ngày về) — tách ra để thử được mọi nhánh."""
    n = 0
    for bat_dau, ket_thuc in cap_ngay:
        if bat_dau is not None and bat_dau > hom_nay:
            continue
        if ket_thuc is not None and ket_thuc < hom_nay:
            continue
        if bat_dau is None or ket_thuc is None:
            n += 1
    return n


def thieu_lich(db: Session, hom_nay: date) -> int:
    """Chuyến thiếu ngày đi hoặc ngày về mà `theo_giai_doan` đã xếp vào «đang chạy».

    Đi ĐÚNG ba nhánh của `dem_tour.theo_giai_doan`: chuyến thiếu ngày đi nhưng đã có ngày về trong
    quá khứ thì nằm ở «đã về», chuyến có ngày đi trong tương lai thì nằm ở «đang bán» — không đếm
    vào đây, không thì dòng phụ nói một con số không nằm trong số chính.

    ĐO 22/10/2026: `tours.start_date` và `tours.end_date` là NOT NULL trong mô hình, nên trên cơ sở
    dữ liệu dựng bằng mô hình con số này luôn là 0 — nhánh «thiếu ngày» của `theo_giai_doan` chỉ là
    phòng thủ. Vẫn đếm thật thay vì ghi cứng 0: bảng sản phẩm dựng qua bản nâng cấp có thể khác.
    """
    from app.services import dem_tour as DT
    return dem_thieu_lich(db.execute(select(Tour.start_date, Tour.end_date)
                                     .where(Tour.status.in_(DT.DANG_BAN))).all(), hom_nay)
