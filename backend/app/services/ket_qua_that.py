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

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Company, Tour

# Chuyến ĐÃ ĐÓNG SỐ và mọi bước sau đó. Kế toán xác nhận rồi, hay đã khoá, thì chuyến vẫn nằm
# trong tháng nó được đóng số — trạng thái đi tiếp không đẩy nó sang tháng khác.
DA_DONG_SO = ("da_dong_so", "kt_xac_nhan", "khoa")

# Bước cuối của chuyến: từ đây trở đi Kế toán không trả lại được nữa, nên tháng ấy mới thật sự đứng
# yên. Dùng để trả lời "con số này còn nhúc nhích được không", xem luật 1 ở đầu tệp.
KHONG_TRA_LAI_DUOC = ("khoa",)

# ══════════════════════════════════════════════════════════════════════════════════════════════
#  TC-71 · 19/9/2026 — HAI LUẬT BỊ ĐẢO. Ghi cả hai bên, vì bên cũ có lý do thật và lý do ấy
#  KHÔNG mất đi, chỉ bị anh Tuấn cân nhắc rồi chọn khác.
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
#  ─── LUẬT A · CHUYẾN CHƯA ĐÓNG SỐ NAY CŨNG ĐƯỢC CỘNG ─────────────────────────────────────────
#  BÊN CŨ (TC-47, 16/9): chỉ chuyến ĐÃ ĐÓNG SỐ mới được cộng. Lý do: đóng số là lúc người điều
#    hành chốt sổ quyết toán, trước đó con số còn nhúc nhích. Con số khớp sổ kế toán.
#  BÊN MỚI (18/9): anh Tuấn chọn "gộp thành một số". Lý do đo được hôm ấy: 670 chuyến đã chạy
#    xong, có doanh thu thật trong máy, tổng 24,38 tỷ — nhưng không hiện ở đâu trên màn hình chủ
#    tịch vì chưa ai bấm đóng số. Tiền đã về mà lãnh đạo không thấy là một kiểu mù còn tệ hơn con
#    số nhúc nhích.
#  HỆ QUẢ PHẢI CHỊU, VÀ ĐÃ NÓI TRƯỚC VỚI ANH TUẤN: con số này KHÔNG còn khớp sổ kế toán và không
#    khớp BCTC. Nên nó BẮT BUỘC đi kèm nhãn cơ sở, và phần "đã đóng sổ" phải trả về RIÊNG để màn
#    hình luôn bày được cả hai. Xem `dt_da_dong_so` / `dt_chua_dong_so` dưới đây — chúng không
#    phải số phụ, chúng là thứ giữ cho con số gộp không thành lời nói dối.
#
#  MỐC THÁNG CỦA CHUYẾN CHƯA ĐÓNG SỐ là NGÀY KHỞI HÀNH, vì nó chưa có `closed_at` để mà theo.
#  Hai mốc khác nhau trong cùng một cột là điều phải nói ra chứ không giấu — nhưng trộn hai mốc
#  vẫn đúng hơn là bỏ hẳn 24,38 tỷ ra ngoài màn hình.
#
#  CHỈ TÍNH CHUYẾN ĐÃ KHỞI HÀNH. Chuyến của tháng sau chưa chạy mà đã cộng doanh thu là ghi nhận
#  trước doanh thu — sai ở mọi chuẩn kế toán, và sai cả về lẽ thường.
#
#  ─── LUẬT B · PHÁP NHÂN RỖNG NAY QUY VỀ CÔNG TY MẸ ───────────────────────────────────────────
#  BÊN CŨ (TC-47 luật 2, dẫn `services/pham_vi_phap_nhan`): `company_id` rỗng là CHƯA XÁC ĐỊNH,
#    không mặc định về công ty mẹ; chuyến ấy ra một dòng riêng chứ không cộng vào Vietourist.
#    Lý do: đoán sai pháp nhân thì mọi con số tiền là của một công ty khác mà nhìn không khác gì
#    số đúng.
#  BÊN MỚI (18/9): anh Tuấn — "7,26 tỷ em tự gắn pháp nhân cố định cho vietourist luôn". Đo được
#    hôm ấy: cả 38 chuyến chưa gắn đều là DỊCH VỤ LẺ (visa, dịch vụ khác, mã DVL-*), đã đóng số
#    xong, và anh Tuấn đã chốt từ trước "gán hết cho Vietourist Holdings". Nên đây không phải máy
#    đoán pháp nhân — đây là chép lại một quyết định đã có của người có thẩm quyền.
#  RANH GIỚI 09/9 VẪN NGUYÊN: tệp này KHÔNG ghi một dòng dữ liệu nào. Nó không đặt `company_id`
#    cho chuyến nào cả — nó chỉ CỘNG chuyến rỗng vào phạm vi công ty mẹ lúc tính. Cột trong cơ sở
#    dữ liệu vẫn rỗng, Hành chính vẫn gắn đè được bất cứ lúc nào, và lúc ấy luật này tự nhường
#    chỗ. Nếu ghi thẳng vào cột thì mới là em nhập số liệu hộ, và em không làm thế.
#  VÀ NÓ PHẢI ĐẾM ĐƯỢC: `gan_mac_dinh` nói ra bao nhiêu chuyến đang vào đây bằng luật mặc định
#    chứ không do ai gắn thật. Một quy tắc mặc định mà không đếm được là một quy tắc không ai
#    kiểm tra lại được.

# Chuyến CHƯA đóng số nhưng đã chạy xong — phần mà luật A kéo thêm vào. "ket_thuc" là chuyến đã
# về, "da_duyet" là chuyến đã duyệt và tới ngày khởi hành thì coi như đã chạy.
CHUA_DONG_SO = ("ket_thuc", "da_duyet")


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


def so_cua_chuyen(db: Session, chuyen: list[Tour]) -> dict[int, tuple[float | None, float | None]]:
    """SỔ CỦA MỖI CHUYẾN — chuyến đã đóng số đọc sổ quyết toán, chuyến chưa đóng số đọc sổ Vietrip.

    ═════════════════════════════════════════════════════════════════════════════════════════
    08/10/2026 · MỘT LỖI, KHÔNG PHẢI MỘT LUẬT MỚI
    ═════════════════════════════════════════════════════════════════════════════════════════
    Luật A (TC-71, 18/9) đã quyết: chuyến đã khởi hành mà chưa đóng số thì CŨNG ĐƯỢC CỘNG, vì
    "670 chuyến đã chạy xong, có doanh thu thật trong máy, tổng 24,38 tỷ — nhưng không hiện ở đâu
    trên màn hình chủ tịch". Luật ấy kéo đúng những chuyến ấy vào `cua_me`, nhưng rồi đọc doanh
    thu của chúng ở `tours.actual_revenue` — và `services/vietrip.apply_tours` GHI 0 vào đúng hai
    cột ấy cho mọi chuyến Vietrip chưa quyết toán (`elif t.status not in DA_DONG_SO`). Nên chuyến
    vào được tập cộng mà mang theo 0 đồng: cột doanh thu không đổi một hào, và luật A chỉ làm
    phình số chuyến. Đo 08/10/2026 trên bàn chạy thật: 637 chuyến đã khởi hành chưa đóng số, sổ
    booking mang 24.490.260.789 đ, khối Doanh thu màn hình Chủ tịch hiện T9 = 8,51 tỷ trong khi
    sổ booking của T9 là 17,1 tỷ.

    Chủ tịch 08/10/2026, khi được báo con số không lên: *"có bao nhiêu số liệu trên vietrip em cứ
    nối về vtos, ko cần phải đóng sổ, nghĩa là vietrip làm như thế nào thì vtos theo vậy"*.

    ═════════════════════════════════════════════════════════════════════════════════════════
    THỨ TỰ ƯU TIÊN, VÀ VÌ SAO KHÔNG PHẢI PHÉP CỘNG
    ═════════════════════════════════════════════════════════════════════════════════════════
    Một chuyến đã đóng số thì CÓ CẢ HAI: sổ quyết toán (`actual_revenue`) và sổ booking của chính
    nó. Cộng cả hai là nhân đôi doanh thu của mọi chuyến đã quyết toán — một lỗi cộng đúp mà tổng
    vẫn trông hợp lý, nên không ai nhìn ra. Vì vậy đây là CHỌN MỘT, không phải cộng:

      · `closed_at` khác rỗng → sổ quyết toán. Đây là con số khớp sổ kế toán, do người điều hành
        chốt tại cửa đóng số. Không đụng tới, không "kiểm tra lại bằng booking".
      · `closed_at` rỗng      → sổ Vietrip (`lai_lo_tour.so_theo_vietrip`): doanh thu từ booking
        chưa huỷ cộng phí huỷ giữ lại, giá vốn từ dòng chi phí quyết toán.

    `closed_at` chứ không phải trạng thái — một chuyến Kế toán trả lại có `closed_at = None` và
    trạng thái về "ket_thuc" (xem hệ quả của luật 1 ở đầu tệp); lọc theo trạng thái thì chuyến ấy
    vừa đọc sổ quyết toán cũ đã bỏ vừa đọc sổ booking.

    SỔ VIETRIP LÀ CHỖ LÙI VỀ, KHÔNG PHẢI CHỖ GHI ĐÈ — và đây là chỗ bản đầu của vòng này làm sai.
    Một chuyến chưa đóng số VẪN CÓ THỂ có `actual_revenue` thật trên hàng: Kế toán trả lại một
    chuyến đã quyết toán thì `settlement.py` xoá `closed_at` nhưng GIỮ hai cột tiền (xem hệ quả
    của luật 1 ở đầu tệp). Đọc booking thay cho con số ấy là ném đi một con số người ta đã nhập
    tay, và bảy phép thử của TC-47 đỏ lên đúng vì vậy — chúng đang canh đúng điều cần canh.

    Nên với chuyến chưa đóng số, mỗi nửa chọn nguồn GIÀU NHẤT CÒN LẠI và KHÔNG BAO GIỜ lùi về 0:
      · doanh thu: `actual_revenue` nếu có và KHÁC 0, ngược lại sổ booking.
      · giá vốn:   `lai_lo_tour._gia_von` — ưu tiên dòng chi phí, lùi về `actual_cost` khác 0,
        rồi mới rỗng. Luật này có từ đợt K2; gọi lại chứ không chép sang đây.

    `KHÁC 0` mới là chỗ chữa được lỗi: `apply_tours` ghi đúng số 0 vào hai cột ấy, nên "0 đồng" ở
    một chuyến chưa quyết toán nghĩa là CHƯA CÓ SỐ, không phải "bán không ra đồng nào". Một chuyến
    bán không ra đồng nào thì cũng không có booking, nên sổ booking trả rỗng và chuyến ấy vẫn ra
    `thieu_gia_von` — không có đường nào để 0 đồng thành doanh thu.

    RỖNG VẪN KHÁC KHÔNG. Chuyến chưa có booking nào trả doanh thu None, chuyến chưa có giá vốn
    trả giá vốn None, và `thang()` ở dưới vẫn để chúng ra `thieu_gia_von` đúng như trước. Việc này
    KHÔNG mở cửa cho chuyến có doanh thu mà không có giá vốn chui vào cột chính — xem khối "vì sao
    doanh thu cũng phải bỏ chuyến thiếu giá vốn ra khỏi cột chính" ở đầu tệp, luật ấy còn nguyên.
    Phần doanh thu ấy ra `dt_thieu_gia_von`, và màn hình đã có khúc mờ để vẽ nó
    (`ket_qua_kinh_doanh` gắn vào ô `cho` của cột doanh thu).

    RANH GIỚI 09/9 NGUYÊN VẸN: hàm này không ghi một cột nào, chỉ chọn nguồn lúc tính.
    """
    from app.services import lai_lo_tour as LL

    chua_dong = [t for t in chuyen if t.closed_at is None]
    vt = LL.so_theo_vietrip(db, chua_dong)
    ra: dict[int, tuple[float | None, float | None]] = {}
    for t in chuyen:
        gv_hang = (None if t.actual_cost is None
                   else float(t.actual_cost) + float(t.promo_value or 0))
        dt_hang = None if t.actual_revenue is None else float(t.actual_revenue)
        if t.closed_at is not None:
            ra[t.id] = (dt_hang, gv_hang)
            continue
        dt_vt, gv_vt = vt.get(t.id, (None, None))
        ra[t.id] = (dt_hang if dt_hang else dt_vt, gv_vt)
    return ra


def _lai_so(so: dict, t: Tour) -> float | None:
    """Lãi một chuyến theo sổ đã chọn ở `so_cua_chuyen`. None khi thiếu một trong hai nửa."""
    dt, gv = so.get(t.id, (None, None))
    return None if (dt is None or gv is None) else dt - gv


def _dt_so(so: dict, t: Tour) -> float:
    """Doanh thu một chuyến theo sổ đã chọn; rỗng cộng 0 — chỗ gọi đã đếm riêng số dòng rỗng."""
    return so.get(t.id, (None, None))[0] or 0.0


def _dem_dong_bu(ds: list[Tour]) -> int:
    """Bao nhiêu chuyến trong danh sách này vào tháng bằng CỬA ĐÓNG SỐ BÙ của kho cũ.

    Dấu nhận đúng bằng dấu mà cửa gỡ dùng (`dong_so_kho_cu._do_cua_nay`): nguồn là kho cũ và
    `closed_at` rơi trúng mốc kỳ. Gọi lại hàm bên ấy chứ không chép luật sang đây — hai bản sao của
    cùng một luật là hai bản sẽ lệch nhau vào ngày không ai để ý.
    """
    from app.services.dong_so_kho_cu import NGUON as N_BU, _do_cua_nay

    return sum(1 for t in ds if t.confirmed_by == N_BU and _do_cua_nay(t))


NGAN = ("le", "doan", "dich_vu_le", "thue_xe", "khac")


def _theo_mang(ds: list[Tour], so: dict) -> dict:
    """Doanh thu và số chuyến của một danh sách chuyến, chia theo ngăn.

    07/10/2026 — NGĂN "khac" ĐƯỢC TÁCH LÀM BA, và đây không phải việc làm đẹp bảng.

    Trước bản này mọi chuyến không thuộc mảng Lẻ và không thuộc mảng Đoàn rơi chung vào `khac`:
    dịch vụ lẻ, và từ hôm nay cả hợp đồng thuê xe. Màn hình Chủ tịch (`dashboard`) chỉ IN ra `le`
    và `doan`, trong khi con số tổng ở trên lại cộng đủ cả ba — nên hai con số trên cùng một màn
    hình không cộng lại được với nhau, và phần chênh không có tên.

    Chủ tịch dặn khi chốt hợp đồng thuê xe: doanh thu thuê xe không được chạy lẫn vào doanh thu
    tour. Giữ nó trong một ngăn tên là "khác" thì vẫn là chạy lẫn — chỉ là lẫn ở một chỗ khó thấy
    hơn. Nên mỗi thứ một ngăn, mang đúng tên của nó, và `khac` nay chỉ còn nghĩa "chưa ai xếp".

    `khac` RỖNG là trạng thái bình thường và đáng mong; nó khác 0 nghĩa là có loại chuyến chưa ai
    quyết xếp vào đâu — xem `KHONG_TRON_GOI` ở `models/core.py` và phép thử `test_tx4`.
    """
    from app.services import segments as SEG
    ra = {m: {"doanh_thu": 0.0, "chuyen": 0} for m in NGAN}
    for t in ds:
        m = SEG.mang_of(t) or {"non_package": "dich_vu_le", "thue_xe": "thue_xe"}.get(t.tour_type, "khac")
        ra[m]["doanh_thu"] += _dt_so(so, t)
        ra[m]["chuyen"] += 1
    return ra


def thang(db: Session, ky: str, nho: dict | None = None) -> dict:
    """Doanh thu và lãi tour của MỘT tháng, phạm vi Vietourist mẹ.

    TC-64 · `nho` là chỗ nhớ của MỘT lần dựng bảng, do chỗ gọi tạo ra và truyền vào (xem chú thích
    dài ở `ket_qua_kinh_doanh.bang`). Bảng Kết quả kinh doanh hỏi ba lần về cùng một tháng; có
    `nho` thì lượt thứ hai và thứ ba lấy lại kết quả lượt đầu thay vì xuống cơ sở dữ liệu.
    KHÔNG truyền `nho` thì hàm chạy y như trước — mọi chỗ gọi khác không phải đổi một chữ.

    `ky` dạng "2026-09" — đúng quy ước dùng chung cả kho (`services/xu_huong`).

    Trả về:
      doanh_thu / lai_tour   – của những chuyến ĐỦ SỐ (có cả doanh thu lẫn giá vốn). None khi
                               tháng ấy chưa có chuyến nào đủ số: 0 đồng và "chưa ai đóng số"
                               là hai việc khác hẳn nhau.
      du_so                  – số chuyến góp vào hai con số trên.
      thieu_gia_von          – chuyến đã đóng số mà giá vốn còn rỗng (Điều hành nhập).
      dt_thieu_gia_von       – phần doanh thu của những chuyến ấy: khúc mờ trên cột.
      chua_gan_phap_nhan     – TC-71 · ĐỔI NGHĨA: chuyến chưa ai gán pháp nhân, nay ĐÃ CỘNG vào
                               Vietourist bằng quy tắc mặc định (luật B). Trước 18/9 thì ngược
                               lại: bị để ngoài. Tên khoá giữ nguyên để chỗ đọc khỏi sửa, nhưng
                               CHỮ TRÊN MÀN HÌNH phải đổi theo, nếu không nó nói ngược sự thật.
      dt_da_dong_so          – TC-71 · phần doanh thu của chuyến ĐÃ đóng số. Đây là con số khớp
                               sổ kế toán; giữ riêng để đối chiếu ngược được.
      dt_chua_dong_so        – TC-71 · phần luật A kéo thêm vào: chuyến đã chạy, chưa đóng số.
      chuyen_da_dong_so /
      chuyen_chua_dong_so    – số chuyến của hai phần trên.
      da_khoa                – tháng này còn chuyến Kế toán trả lại được hay không.
      co_nguon               – danh mục pháp nhân đã có công ty mẹ chưa.
      dong_so_bu             – trong số chuyến của Vietourist mẹ tháng này, bao nhiêu chuyến vào
                               đây bằng CỬA ĐÓNG SỐ BÙ (Chủ tịch ký thay, lô kho cũ) chứ không do
                               Điều hành đóng số thật. Xem khối 17/9 ở đầu tệp.
    """
    khoa = ("kqt.thang", ky)
    if nho is not None and khoa in nho:
        return nho[khoa]

    y, m = int(ky[:4]), int(ky[5:7])
    dau, cuoi = _khoang_thang(y, m)
    me = cong_ty_me(db)

    # ── LUẬT A · hai lượt gom, hai mốc thời gian khác nhau ────────────────────────────────────
    # (1) Chuyến ĐÃ đóng số, xếp theo NGÀY ĐÓNG SỐ — y như TC-47, không đổi một chữ.
    da_dong = list(db.execute(
        select(Tour).where(Tour.status.in_(DA_DONG_SO),
                           Tour.closed_at >= dau, Tour.closed_at < cuoi)).scalars())

    # (2) Chuyến CHƯA đóng số nhưng ĐÃ KHỞI HÀNH, xếp theo NGÀY KHỞI HÀNH.
    #     `Tour.closed_at.is_(None)` là điều kiện quyết định, không phải trạng thái: một chuyến bị
    #     Kế toán trả lại có `closed_at = None` và trạng thái về "ket_thuc" (xem hệ quả của luật 1
    #     ở đầu tệp). Lọc theo trạng thái không thôi thì chuyến ấy rơi vào cả hai lượt và bị đếm
    #     hai lần — lỗi cộng đúp không ai nhìn ra vì tổng vẫn "hợp lý".
    hom_nay = date.today()
    ngay_cuoi = min(cuoi.date(), hom_nay + timedelta(days=1))
    chua_dong: list[Tour] = []
    if ngay_cuoi > dau.date():
        chua_dong = list(db.execute(
            select(Tour).where(Tour.status.in_(CHUA_DONG_SO),
                               Tour.closed_at.is_(None),
                               Tour.start_date >= dau.date(),
                               Tour.start_date < ngay_cuoi)).scalars())

    chuyen = da_dong + chua_dong

    # ── LUẬT B · pháp nhân rỗng quy về công ty mẹ ─────────────────────────────────────────────
    # KHÔNG ghi vào `t.company_id` — chỉ gom lúc tính. Xem khối luật B ở đầu tệp.
    gan_that = [t for t in chuyen if me is not None and t.company_id == me]
    gan_mac_dinh = [t for t in chuyen if t.company_id is None]
    cua_me = gan_that + gan_mac_dinh if me is not None else []

    # Danh sách CHƯA ĐÓNG SỐ, sau khi đã quy pháp nhân — đây là phần luật A kéo thêm vào, và là
    # phần mà màn hình "Sổ chuyến còn nợ" sẽ liệt kê cho Điều hành đi đóng.
    cua_me_chua_dong = [t for t in cua_me if t.closed_at is None]
    cua_me_da_dong = [t for t in cua_me if t.closed_at is not None]

    # 08/10/2026 · MỘT lượt chọn nguồn cho cả tháng, rồi mọi con số dưới đây đọc qua nó. Hai chỗ
    # tự đọc `actual_revenue` là hai chỗ sẽ lệch nhau — xem `so_cua_chuyen`.
    so = so_cua_chuyen(db, cua_me)
    du = [t for t in cua_me if _lai_so(so, t) is not None]
    thieu = [t for t in cua_me if _lai_so(so, t) is None]
    # 08/10/2026 · TẬP CỦA CỘT DOANH THU, KHÁC tập của cột lãi — xem khối "doanh thu đi hết" dưới.
    co_dt = [t for t in cua_me if so.get(t.id, (None, None))[0] is not None]

    ra = {
        "ky": ky,
        # ── CON SỐ GỘP (anh Tuấn chọn 18/9) ──────────────────────────────────────────────────
        # Gồm CẢ chuyến chưa đóng số. Không khớp sổ kế toán — màn hình phải ghi nhãn cơ sở.
        #
        # ══════════════════════════════════════════════════════════════════════════════════════
        # 08/10/2026 · DOANH THU ĐI HẾT, LÃI THÌ KHÔNG — và đây là chỗ TC-47 bị đảo, có chữ ký.
        # ══════════════════════════════════════════════════════════════════════════════════════
        # Chủ tịch 08/10/2026: *"ý của anh là lấy số liệu y chang của vietrip"*, sau khi em báo
        # rằng bản vá sổ Vietrip vẫn chưa làm con số lên.
        #
        # VÌ SAO BẢN VÁ MỘT MÌNH CHƯA ĐỦ, đo trên bàn chạy thật 08/10: trong 116 chuyến T9 đã khởi
        # hành chưa đóng số, chỉ 5 chuyến có dòng chi phí (109.470.000 đ); 57 chuyến có doanh thu
        # booking mà KHÔNG có dòng chi phí nào — 10.583.459.435 đ. T10 còn rõ hơn: 0 chuyến có
        # dòng chi phí, 17 chuyến mang 3.159.099.709 đ không có giá vốn. Luật TC-47 "cột chính chỉ
        # gồm chuyến ĐỦ SỐ" vì thế giữ gần như toàn bộ số tiền ấy ở ngoài: bản vá chỉ thêm được
        # 109 triệu cho T9 và 0 đồng cho T10.
        #
        # BÊN CŨ CÓ LÝ DO THẬT, và lý do ấy không mất đi (TC-47, chỗ hỏng 5): doanh thu và lãi
        # đứng cạnh nhau trên một trục ngang, người đọc sẽ CHIA chúng cho nhau để ra biên lợi
        # nhuận — tử số của tập này chia cho mẫu số của tập kia thì biên ra thấp hơn thật.
        #
        # BÊN MỚI giải đúng chỗ ấy chứ không bỏ qua nó: cột doanh thu đi hết tập `co_dt`, cột lãi
        # vẫn chỉ tập `du`, và MẪU SỐ CỦA CỘT LÃI được trả ra thành một con số riêng có tên —
        # `dt_co_gia_von`. Có nó thì biên lợi nhuận tính được ĐÚNG (`lai_tour / dt_co_gia_von`),
        # và màn hình bày được cả hai tập. Giấu phần thiếu để hai cột cùng tập là đổi một con số
        # sai thành một con số thiếu 10,5 tỷ — Chủ tịch đã chọn, và đây là chỗ ghi lại.
        #
        # HỆ QUẢ PHẢI CHỊU, NÓI TRƯỚC: `doanh_thu / lai_tour` KHÔNG còn là biên lợi nhuận. Mọi
        # chỗ đọc hai ô này để chia phải chia bằng `dt_co_gia_von`. Phép thử `kq2_8` canh đúng
        # điều đó, và `ket_qua_kinh_doanh` vẽ phần thiếu thành khúc mờ NẰM TRONG cột doanh thu
        # (cột đặc = `dt_co_gia_von`, khúc mờ = `dt_thieu_gia_von`, cao cả cột = `doanh_thu`).
        "doanh_thu": float(sum(_dt_so(so, t) for t in co_dt)) if co_dt else None,
        "lai_tour": float(sum(_lai_so(so, t) or 0 for t in du)) if du else None,
        "du_so": len(du),
        # MẪU SỐ CỦA `lai_tour`. Rỗng khi chưa chuyến nào đủ số — không phải 0, vì chia cho 0 và
        # chia cho "chưa biết" là hai việc khác nhau.
        "dt_co_gia_von": float(sum(_dt_so(so, t) for t in du)) if du else None,
        "du_so_dt": len(co_dt),
        # ── HAI NỬA CỦA CON SỐ GỘP, luôn trả riêng ───────────────────────────────────────────
        # Thiếu hai dòng này thì con số gộp không còn cách nào đối chiếu ngược về sổ kế toán, và
        # ngày kiểm toán hỏi "85 hay 116" thì không ai chỉ ra được chỗ chênh nằm ở đâu.
        "dt_da_dong_so": float(sum(_dt_so(so, t) for t in cua_me_da_dong)),
        "dt_chua_dong_so": float(sum(_dt_so(so, t) for t in cua_me_chua_dong)),
        "chuyen_da_dong_so": len(cua_me_da_dong),
        "chuyen_chua_dong_so": len(cua_me_chua_dong),
        "thieu_gia_von": len(thieu),
        # Doanh thu của chuyến thiếu giá vốn vẫn có thể rỗng nốt — lúc ấy cộng 0 là đúng, vì phần
        # được vẽ ra là phần ĐÃ BIẾT, và số chuyến bên cạnh nói phần chưa biết còn bao nhiêu dòng.
        "dt_thieu_gia_von": float(sum(_dt_so(so, t) for t in thieu)),
        # ── LUẬT B · đếm phần vào bằng quy tắc mặc định ──────────────────────────────────────
        # Tên cũ `chua_gan_phap_nhan` GIỮ NGUYÊN để mọi chỗ đọc nó không phải sửa, nhưng NGHĨA đã
        # đổi: trước là "bị để ngoài Vietourist", nay là "đã vào Vietourist bằng quy tắc mặc
        # định, Hành chính gắn đè được". Màn hình phải đổi chữ theo — xem KhoiKetQuaKinhDoanh.
        "chua_gan_phap_nhan": len(gan_mac_dinh),
        "dt_chua_gan_phap_nhan": float(sum(_dt_so(so, t) for t in gan_mac_dinh)),
        # `da_khoa` chỉ xét phần ĐÃ ĐÓNG SỐ: phần chưa đóng số thì đương nhiên còn nhúc nhích, hỏi
        # nó có khoá chưa là hỏi một câu vô nghĩa. Và còn chuyến chưa đóng số thì tháng CHƯA đứng
        # yên, nên thêm điều kiện ấy chứ không bỏ qua.
        "da_khoa": (bool(cua_me_da_dong) and not cua_me_chua_dong
                    and all(t.status in KHONG_TRA_LAI_DUOC for t in cua_me_da_dong)),
        "co_nguon": me is not None,
        "dong_so_bu": _dem_dong_bu(cua_me_da_dong),
        # TC-98 · DOANH THU THEO PHÒNG (anh Tuấn 29/9/2026: "nối doanh thu của PKD Lẻ và PKD Đoàn
        # vào màn hình chủ tịch"). Chia ĐÚNG tập đã cộng ra `doanh_thu` ở trên — không phải một
        # phép tính thứ hai — nên lẻ + đoàn + khác luôn bằng `doanh_thu`. Mảng theo
        # `segments.mang_of`, cùng luật với bộ lọc phòng và bảng lương.
        #
        # 08/10/2026 ĐỔI TỪ `du` SANG `co_dt` theo đúng cột doanh thu. Để `du` thì tổng các phòng
        # thiếu 10,5 tỷ so với con số ngay phía trên nó trên CÙNG MỘT màn hình — đúng lỗi TC-98
        # vừa sửa ngày 07/10, chỉ là lặp lại ở chiều ngược.
        "theo_mang": _theo_mang(co_dt, so),
    }
    if nho is not None:
        nho[khoa] = ra
    return ra
