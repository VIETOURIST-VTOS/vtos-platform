# -*- coding: utf-8 -*-
"""TC-47 · DOANH THU VÀ LÃI LẤY TỪ SỔ QUYẾT TOÁN CỦA CHUYẾN ĐÃ ĐÓNG SỐ.

Anh Tuấn 16/9/2026, sau khi nhìn thẻ Kết quả kinh doanh hiện "—" ở Doanh thu và 830 tr ở Lợi nhuận:

    "doanh thu và lợi nhuận là lấy thực tế từ tour đã bán hoàn thành, không phải kế hoạch của HĐQT,
     lấy từ luồng dữ liệu PKD, Điều hành và Kế toán chạy về, bỏ Vietrip chỉ tập trung vào doanh thu
     và lợi nhuận của Vietourist, các cty con và cty liên kết chỉ vào mục hợp nhất BCTC"

Và ba lựa chọn anh chốt hôm nay: mốc tính là **Điều hành đóng số**; lãi tour lấy từ **sổ quyết toán
tour**; lợi nhuận trước thuế chỉ phạm vi **Vietourist mẹ**.

═══════════════════════════════════════════════════════════════════════════════════════════════
SỔ QUYẾT TOÁN CỦA MỘT CHUYẾN NẰM Ở ĐÂU
═══════════════════════════════════════════════════════════════════════════════════════════════
Ở `tours.actual_revenue` / `actual_cost` / `promo_value`, do chính người điều hành chuyến ghi tại
cửa đóng số (`services/tours.close`), cùng lúc với `closed_at` và trạng thái `da_dong_so`.

KHÔNG phải bảng `tour_settlements`. Bảng ấy là CỬA NẠP tệp Excel quyết toán của Điều hành cho 495
chuyến tháng 7–8/2026 (`tour_settlements.tour_id` còn để rỗng được, nghĩa là chưa tra ra chuyến
thật). Đọc nó ở đây là dựng nguồn sự thật thứ hai cho cùng một câu hỏi, và ngày hai nguồn lệch nhau
thì không ai biết tin bên nào.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA ĐIỀU ĐỔI SO VỚI PHÉP TÍNH CŨ, VÀ CẢ BA ĐỀU LÀM CON SỐ TRÊN MÀN HÌNH ĐỔI THEO
═══════════════════════════════════════════════════════════════════════════════════════════════
Phép cũ (`dashboard._month_tours` + `rules.settlement_summary`) lọc chuyến theo `kt_confirmed_at`
và trạng thái `("kt_xac_nhan", "khoa")`, không lọc pháp nhân, và gộp rỗng về 0.

1. MỐC LÀ NGÀY ĐÓNG SỐ, KHÔNG PHẢI NGÀY KẾ TOÁN XÁC NHẬN. Chuyến về tháng 8, Điều hành đóng số
   30/8, Kế toán xác nhận 12/9 thì phép cũ xếp nó vào tháng 9. Doanh thu tháng 8 vì thế phụ thuộc
   vào tốc độ duyệt của Kế toán chứ không vào việc bán được bao nhiêu. Anh Tuấn chốt mốc đóng số.

   HỆ QUẢ PHẢI CHỊU: Kế toán trả lại một chuyến thì `settlement.py` đặt `closed_at = None` và trạng
   thái về `ket_thuc` — chuyến ấy RỜI KHỎI tháng đã tính, và tổng tháng ấy giảm xuống. Đó là đúng
   (số cũ vốn sai), nhưng một tháng đã đóng mà con số còn nhúc nhích là điều phải nói ra chứ không
   để người đọc tự phát hiện: xem `da_khoa` ở dưới.

2. CHỈ VIETOURIST MẸ. `tours.company_id` rỗng là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ —
   luật của `services/pham_vi_phap_nhan`, giữ nguyên ở đây. Chuyến chưa gán pháp nhân KHÔNG cộng
   vào Vietourist và KHÔNG biến mất: nó ra một dòng riêng (`chua_gan_phap_nhan`).

3. RỖNG KHÁC KHÔNG. `rules.settlement_summary` viết `cost = (tour.actual_cost or 0) + …`, tức một
   chuyến chưa ai nhập giá vốn được đọc thành giá vốn 0 đồng — và chuyến ấy báo lãi bằng đúng toàn
   bộ doanh thu, biên 100%. Bảng vẫn cân nên không ai nhìn ra. Đây chính là điều mà chú thích đầu
   `models/quyet_toan.py` đã cảnh báo ("ghi thẳng vào một cột không phân biệt được 0 đồng với chưa
   ai điền là sổ báo lãi 100% trên 2,65 tỷ"), nhưng cảnh báo ấy mới chỉ được thi hành ở bảng nạp,
   chưa thi hành ở phép tính. Tệp này thi hành nó.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO DOANH THU CŨNG PHẢI BỎ CHUYẾN THIẾU GIÁ VỐN RA KHỎI CỘT CHÍNH
═══════════════════════════════════════════════════════════════════════════════════════════════
Cách dễ là: doanh thu cộng hết, còn lãi thì chỉ cộng những chuyến đủ giá vốn. Mỗi con số đều đúng
với chính nó. Nhưng hai con số ấy đứng cạnh nhau trên cùng một trục ngang, và người đọc sẽ chia
chúng cho nhau để ra biên lợi nhuận — một phép chia giữa TỬ SỐ của tập này và MẪU SỐ của tập kia.
Biên ra thấp hơn thật, và không có gì trên màn hình nói rằng hai cột nói về hai tập chuyến khác nhau.

Đúng bài học TC-45 ("hai cuốn sổ cạnh nhau là lỗi dù không con số nào sai"): cột chính của CẢ HAI
hình chỉ gồm những chuyến ĐỦ SỐ. Phần doanh thu của chuyến thiếu giá vốn không mất đi — nó là một
khúc mờ nối tiếp trên chính cây cột doanh thu, có tên và có bộ phận chịu trách nhiệm.

RANH GIỚI 09/9 GIỮ NGUYÊN: tệp này không nhập số nào. Giá vốn thiếu thì Điều hành nhập ở cửa đóng
số; pháp nhân thiếu thì Hành chính gán. Hệ thống chỉ nói ra là còn thiếu bao nhiêu và ai nhập.

═══════════════════════════════════════════════════════════════════════════════════════════════
17/9/2026 · `closed_at` TỪ NAY MANG HAI NGHĨA — ĐỌC KỸ TRƯỚC KHI SỬA PHÉP LỌC Ở DƯỚI
═══════════════════════════════════════════════════════════════════════════════════════════════
Chủ tịch chốt: *"vì đây là nhập dữ liệu cũ lên hệ thống nên em để Chủ tịch ký thay toàn bộ các
phòng ban luôn, khi nào vào vận hành chính thức thì phòng nào ký phòng đó"*. Từ đó có cửa
`services/dong_so_kho_cu` đóng số bù cho 456 chuyến T1–T5/2026 của kho quyết toán cũ.

Cửa ấy KHÔNG ghi `closed_at = now()` như cửa thật, mà ghi **cuối ngày kết thúc của chính chuyến**.
Nếu ghi `now()` thì cả ≈36 tỷ của năm tháng đầu năm nhảy hết vào tháng bấm nút: cột tháng 9 phình
lên nhìn y hệt một tháng bán tốt, còn T1–T5 vẫn rỗng. Sai kiểu ấy tệ hơn rỗng, vì rỗng thì người
đọc biết là thiếu.

NÊN Ở ĐÂY: với lô kho cũ, `closed_at` là **KỲ CỦA CHUYẾN**, không phải "lúc người ta bấm đóng số".
Ngày bấm thật và người ký nằm ở nhật ký kiểm toán (`dong_so_bu_kho_cu_h1_2026`) và ở dòng sự kiện
của chuyến. Luật 1 ở trên — "mốc là ngày đóng số" — vẫn đúng cho mọi chuyến vận hành; lô bù là
ngoại lệ có chữ ký, đếm riêng ở `dong_so_bu` trong bản trả về, để một tháng gồm phần lớn là số bù
thì người đọc thấy ngay chứ không phải đi tra.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Company, Tour

# Chuyến ĐÃ ĐÓNG SỐ và mọi bước sau đó. Kế toán xác nhận rồi, hay đã khoá, thì chuyến vẫn nằm
# trong tháng nó được đóng số — trạng thái đi tiếp không đẩy nó sang tháng khác.
DA_DONG_SO = ("da_dong_so", "kt_xac_nhan", "khoa")

# Bước cuối của chuyến: từ đây trở đi Kế toán không trả lại được nữa, nên tháng ấy mới thật sự đứng
# yên. Dùng để trả lời "con số này còn nhúc nhích được không", xem luật 1 ở đầu tệp.
KHONG_TRA_LAI_DUOC = ("khoa",)


def cong_ty_me(db: Session) -> int | None:
    """id của pháp nhân mẹ. None khi danh mục công ty chưa có dòng nào `kind='me'`.

    Không lùi về "công ty đầu tiên trong bảng": đoán sai pháp nhân thì mọi con số tiền trên màn
    hình là của một công ty khác, mà nhìn thì không khác gì số đúng.
    """
    return db.execute(
        select(Company.id).where(Company.kind == "me", Company.active.is_(True))
        .order_by(Company.id)).scalars().first()


def _khoang_thang(y: int, m: int) -> tuple[datetime, datetime]:
    return (datetime(y, m, 1),
            datetime(y + (m == 12), 1 if m == 12 else m + 1, 1))


def _lai(t: Tour) -> float | None:
    """Lãi của một chuyến theo sổ quyết toán của chính nó. None khi CHƯA CÓ giá vốn.

    `promo_value` là một dòng giá vốn nội bộ (ĐC Điều 3) — giữ nguyên cách cộng của
    `rules.settlement_summary`; chỗ khác duy nhất là `actual_cost` rỗng không còn đọc thành 0.
    """
    if t.actual_revenue is None or t.actual_cost is None:
        return None
    return float(t.actual_revenue) - (float(t.actual_cost) + float(t.promo_value or 0))


def _dem_dong_bu(ds: list[Tour]) -> int:
    """Bao nhiêu chuyến trong danh sách này vào tháng bằng CỬA ĐÓNG SỐ BÙ của kho cũ.

    Dấu nhận đúng bằng dấu mà cửa gỡ dùng (`dong_so_kho_cu._do_cua_nay`): nguồn là kho cũ và
    `closed_at` rơi trúng mốc kỳ. Gọi lại hàm bên ấy chứ không chép luật sang đây — hai bản sao của
    cùng một luật là hai bản sẽ lệch nhau vào ngày không ai để ý.
    """
    from app.services.dong_so_kho_cu import NGUON as N_BU, _do_cua_nay

    return sum(1 for t in ds if t.confirmed_by == N_BU and _do_cua_nay(t))


def thang(db: Session, ky: str) -> dict:
    """Doanh thu và lãi tour của MỘT tháng, phạm vi Vietourist mẹ.

    `ky` dạng "2026-09" — đúng quy ước dùng chung cả kho (`services/xu_huong`).

    Trả về:
      doanh_thu / lai_tour   – của những chuyến ĐỦ SỐ (có cả doanh thu lẫn giá vốn). None khi
                               tháng ấy chưa có chuyến nào đủ số: 0 đồng và "chưa ai đóng số"
                               là hai việc khác hẳn nhau.
      du_so                  – số chuyến góp vào hai con số trên.
      thieu_gia_von          – chuyến đã đóng số mà giá vốn còn rỗng (Điều hành nhập).
      dt_thieu_gia_von       – phần doanh thu của những chuyến ấy: khúc mờ trên cột.
      chua_gan_phap_nhan     – chuyến đã đóng số mà chưa ai gán pháp nhân (Hành chính gán).
                               KHÔNG cộng vào Vietourist — xem luật 2.
      da_khoa                – tháng này còn chuyến Kế toán trả lại được hay không.
      co_nguon               – danh mục pháp nhân đã có công ty mẹ chưa.
      dong_so_bu             – trong số chuyến của Vietourist mẹ tháng này, bao nhiêu chuyến vào
                               đây bằng CỬA ĐÓNG SỐ BÙ (Chủ tịch ký thay, lô kho cũ) chứ không do
                               Điều hành đóng số thật. Xem khối 17/9 ở đầu tệp.
    """
    y, m = int(ky[:4]), int(ky[5:7])
    dau, cuoi = _khoang_thang(y, m)
    me = cong_ty_me(db)

    chuyen = list(db.execute(
        select(Tour).where(Tour.status.in_(DA_DONG_SO),
                           Tour.closed_at >= dau, Tour.closed_at < cuoi)).scalars())

    chua_gan = [t for t in chuyen if t.company_id is None]
    cua_me = [t for t in chuyen if me is not None and t.company_id == me]

    du = [t for t in cua_me if _lai(t) is not None]
    thieu = [t for t in cua_me if _lai(t) is None]

    return {
        "ky": ky,
        "doanh_thu": float(sum(float(t.actual_revenue or 0) for t in du)) if du else None,
        "lai_tour": float(sum(_lai(t) or 0 for t in du)) if du else None,
        "du_so": len(du),
        "thieu_gia_von": len(thieu),
        # Doanh thu của chuyến thiếu giá vốn vẫn có thể rỗng nốt — lúc ấy cộng 0 là đúng, vì phần
        # được vẽ ra là phần ĐÃ BIẾT, và số chuyến bên cạnh nói phần chưa biết còn bao nhiêu dòng.
        "dt_thieu_gia_von": float(sum(float(t.actual_revenue or 0) for t in thieu)),
        "chua_gan_phap_nhan": len(chua_gan),
        "dt_chua_gan_phap_nhan": float(sum(float(t.actual_revenue or 0) for t in chua_gan)),
        "da_khoa": bool(cua_me) and all(t.status in KHONG_TRA_LAI_DUOC for t in cua_me),
        "co_nguon": me is not None,
        "dong_so_bu": _dem_dong_bu(cua_me),
    }
