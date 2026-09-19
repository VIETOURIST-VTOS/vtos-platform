# -*- coding: utf-8 -*-
"""TC-71 · SỔ CHUYẾN CÒN NỢ — anh Tuấn 18/9/2026.

    "em dựng luôn và viết code thuật toán để kéo số liệu về màn hình CT, TGĐ và toàn bộ các phòng
     ban liên quan"

Màn hình này trả lời đúng một câu: **tiền đã về mà chưa vào sổ đang nằm ở đâu, ai giữ.**

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ MÀN HÌNH NÀY
═══════════════════════════════════════════════════════════════════════════════════════════════
Đo trên sổ thật 18/9/2026: 670 chuyến đã chạy xong, có doanh thu thật trong máy, tổng 24,38 tỷ —
mà không hiện ở đâu trên màn hình chủ tịch, chỉ vì chưa ai bấm đóng sổ. Trước TC-71 con số ấy bị
bỏ ra khỏi mọi phép cộng và không có một dòng nào nói là nó tồn tại.

TC-71 kéo nó vào con số gộp (xem luật A ở `services/ket_qua_that`). Nhưng một con số gộp mà không
có chỗ nào bấm vào xem chi tiết thì lãnh đạo biết "còn 24 tỷ" mà không biết **chuyến nào** và
**giao cho ai** — và tuần sau vẫn còn 24 tỷ. Màn hình này là chỗ bấm vào ấy.

═══════════════════════════════════════════════════════════════════════════════════════════════
RANH GIỚI 09/9 GIỮ NGUYÊN — ĐÂY LÀ MÀN HÌNH CHỈ ĐỌC
═══════════════════════════════════════════════════════════════════════════════════════════════
Tệp này KHÔNG đóng sổ hộ ai, KHÔNG nhập giá vốn, KHÔNG gắn pháp nhân. Nó liệt kê chuyến còn nợ và
đưa đường dẫn sang đúng chuyến để người có quyền tự làm ở cửa của họ. Anh Tuấn chọn đúng phương án
này khi em hỏi ("Danh sách + đường dẫn sang chuyến"), và lý do thì rõ: đóng sổ là việc khó lùi —
làm hàng loạt từ một màn hình tổng thì một cú bấm nhầm đi xa hơn nhiều so với cái lợi về tốc độ.

═══════════════════════════════════════════════════════════════════════════════════════════════
SEC-02 · CẮT DÒNG NẰM TRONG TRUY VẤN, KHÔNG PHẢI Ở GIAO DIỆN
═══════════════════════════════════════════════════════════════════════════════════════════════
Phạm vi pháp nhân đi qua `pham_vi_phap_nhan.loc` — đúng một cửa mà cả kho đang dùng, không viết
lại luật ở đây. Phép lọc ấy vào THẲNG câu truy vấn: dòng không được phép xem thì không rời khỏi
cơ sở dữ liệu, chứ không phải rời ra rồi giao diện giấu đi.

NÓI THẲNG CHO KHỎI HIỂU NHẦM: ở màn hình này, VAI TRÒ không cắt bớt dòng nào. Chủ tịch, TGĐ,
Điều hành và Kế toán cùng thấy một danh sách, vì cả bốn đều cần nhìn đúng một sự thật — chuyến
nào chưa về sổ. Thứ cắt dòng là PHÁP NHÂN, không phải chức vụ. Vai trò chỉ đổi cái nhãn
(`toan_cong_ty`) để màn hình biết nên viết "toàn công ty" hay "phần của đơn vị bạn".

Không khai sẵn danh sách vai cho Điều hành và Kế toán ở đây: khai một hằng số rồi không dùng tới
là để lại một lời hứa suông trong mã, và người đọc sau sẽ tưởng phép lọc theo vai đã có sẵn.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.services import pham_vi_phap_nhan as PV
from app.services.ket_qua_that import CHUA_DONG_SO, cong_ty_me

# Vai làm việc ở phạm vi toàn tập đoàn. Dùng ĐÚNG MỘT VIỆC: đặt nhãn `toan_cong_ty` để màn hình
# biết nên viết "toàn công ty" hay "phần của đơn vị bạn". KHÔNG dùng để cắt dòng — việc cắt dòng
# là của phạm vi pháp nhân, xem khối SEC-02 ở đầu tệp.
TOAN_CONG_TY = PV.TOAN_TAP_DOAN


def _ngay_moc(hom_nay: date | None = None) -> date:
    """Chuyến tính là ĐÃ CHẠY khi ngày khởi hành đã tới. Chuyến của ngày mai chưa nợ ai cái gì."""
    return (hom_nay or date.today())


def danh_sach(db: Session, u: User, tu: str = "", den: str = "",
              hom_nay: date | None = None, gioi_han: int = 500) -> dict:
    """Chuyến ĐÃ KHỞI HÀNH mà CHƯA ĐÓNG SỔ, trong phạm vi vai của người đang xem.

    `tu` / `den` dạng "2026-01" — lọc theo NGÀY KHỞI HÀNH, vì chuyến chưa đóng sổ không có
    `closed_at` để mà lọc. Bỏ trống thì lấy tất cả.

    Trả về:
      rows        – từng chuyến: mã, tên, ngày khởi hành, số khách, doanh thu, giá vốn, trạng
                    thái, bao nhiêu ngày đã trôi kể từ lúc chạy xong, và đường dẫn sang chuyến.
      tong        – tổng số chuyến còn nợ trong phạm vi (KHÔNG phải số dòng trả về — xem `cham_tran`).
      tien        – tổng doanh thu chưa vào sổ.
      cham_tran   – có bị cắt bớt hay không. Cắt thì được, IM LẶNG thì không (bài học KS-5).
      theo_thang  – gom theo tháng khởi hành, để màn hình vẽ được ngay chỗ nào đọng nhiều nhất.
      qua_han     – chuyến đã chạy xong quá 30 ngày mà vẫn chưa đóng sổ. Đây là phần đáng gọi tên:
                    chuyến mới về tuần trước thì chưa trách được ai.
    """
    moc = _ngay_moc(hom_nay)
    me = cong_ty_me(db)

    q = select(Tour).where(Tour.status.in_(CHUA_DONG_SO),
                           Tour.closed_at.is_(None),
                           Tour.start_date <= moc)
    # SEC-02 · phạm vi pháp nhân vào THẲNG truy vấn.
    q = PV.loc(q, Tour, u)
    if tu:
        q = q.where(Tour.start_date >= date(int(tu[:4]), int(tu[5:7]), 1))
    if den:
        y, m = int(den[:4]), int(den[5:7])
        q = q.where(Tour.start_date < date(y + (m == 12), 1 if m == 12 else m + 1, 1))

    ds = list(db.execute(q.order_by(Tour.start_date)).scalars())

    # LUẬT B của TC-71: pháp nhân rỗng quy về công ty mẹ. Cùng một luật với `ket_qua_that`, nên
    # hai màn hình không bao giờ nói hai con số khác nhau về cùng một tập chuyến.
    if me is not None:
        ds = [t for t in ds if t.company_id in (me, None)]

    han = moc - timedelta(days=30)
    rows, theo_thang, tien, qua_han = [], {}, 0.0, 0
    for t in ds:
        dt = float(t.actual_revenue or 0)
        tien += dt
        k = t.start_date.strftime("%Y-%m") if t.start_date else "?"
        o = theo_thang.setdefault(k, {"ky": k, "chuyen": 0, "tien": 0.0})
        o["chuyen"] += 1
        o["tien"] += dt
        tre = (moc - t.start_date).days if t.start_date else 0
        if t.start_date and t.start_date < han:
            qua_han += 1
        if len(rows) < gioi_han:
            rows.append({
                "id": t.id, "ma": t.code, "ten": t.name,
                "khoi_hanh": t.start_date.isoformat() if t.start_date else None,
                "ket_thuc": t.end_date.isoformat() if t.end_date else None,
                "trang_thai": t.status,
                "doanh_thu": None if t.actual_revenue is None else dt,
                "gia_von": None if t.actual_cost is None else float(t.actual_cost),
                # RỖNG KHÁC KHÔNG, y như luật 3 của TC-47: chuyến chưa ai nhập số thì để None cho
                # màn hình vẽ "—", đừng đọc thành 0 đồng rồi báo lãi bằng toàn bộ doanh thu.
                "chua_co_so": t.actual_revenue is None and t.actual_cost is None,
                "so_ngay_tre": tre,
                "qua_han": bool(t.start_date and t.start_date < han),
                "gan_mac_dinh": t.company_id is None,
                "duong_dan": f"/tours/{t.id}",
            })

    return {
        "rows": rows,
        "tong": len(ds),
        "tien": tien,
        "cham_tran": len(rows) < len(ds),
        "qua_han": qua_han,
        "ngay_qua_han": 30,
        "theo_thang": [theo_thang[k] for k in sorted(theo_thang)],
        # Ai đi làm việc này — ghi thẳng ở đây, màn hình không tự đoán tên bộ phận (ranh giới 09/9).
        "ai_dong_so": "Điều hành",
        "toan_cong_ty": getattr(u, "role", "") in TOAN_CONG_TY,
    }
