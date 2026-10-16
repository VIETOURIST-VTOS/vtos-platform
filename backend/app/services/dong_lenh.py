# -*- coding: utf-8 -*-
"""DL-3 — ĐÓNG LỆNH THÌ MÁY SINH CHUYẾN: nối hai quyển sổ chưa từng gặp nhau.

CHỖ ĐỨT, đo từ mã nguồn 14/10/2026. Cột `fleet_trips.dispatch_id` TỒN TẠI, cửa tạo chuyến nhận
được nó, cửa nạp Excel để trống. Soát toàn bộ `backend/app`: chỗ duy nhất nhắc tới nó là một khai
báo trường nhận vào — KHÔNG một đường nào ghi. Hệ quả đo trên bản chạy thật: **756 chuyến và 1
lệnh**, hai quyển sổ không gặp nhau. Mà lãi lỗ đội xe chỉ đọc chuyến, nên một lệnh đã chạy thật
mà chưa ai nạp Excel thì KHÔNG TỒN TẠI với mọi phép tính tiền.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ NGUY NHẤT: TẠO MỚI KHI ĐÃ CÓ CHUYẾN LÀ CỘNG DOANH THU HAI LẦN
═══════════════════════════════════════════════════════════════════════════════════════════════

Đội xe đã nạp 756 chuyến bằng Excel. Nếu đóng lệnh mà máy cứ tạo một dòng mới thì một chuyến có
thật thành hai dòng, và doanh thu đội xe cộng hai lần — sai theo hướng đẹp lên, tức hướng khó bị
phát hiện nhất. Nên trước khi tạo, máy luôn soát xem đã có chuyến nào của chính lệnh này chưa, rồi
mới tới các mức khớp.

BA MỨC, và ranh giới giữa chúng là điều Chủ tịch chốt 15/10/2026:

  1. ĐÃ CÓ chuyến mang `dispatch_id` của lệnh  → không làm gì, nói ra là đã có.
  2. KHỚP CẢ BỐN (xe · ngày đi · ngày về · tour) và chuyến ấy chưa gắn lệnh nào → GẮN, không tạo.
  3. NGHI KHỚP (cùng xe, cùng ngày đi, nhưng lệch tour hoặc ngày về) → **KHÔNG TẠO, KHÔNG GẮN**,
     chỉ báo ra cho người xác nhận. Đây là chỗ máy dừng lại: tự gắn thì nối nhầm hai chuyến khác
     nhau, tự tạo thì đếm hai lần. Cả hai đều sai, nên việc đúng là đưa cho người nhìn.

Chỉ khi không có cả ba, máy mới dựng một dòng chuyến mới.

TIỀN: `internal_price` của lệnh chép sang `doanh_thu` của chuyến (Chủ tịch chốt 15/10/2026). Đây
KHÔNG phải máy bịa số — người lập lệnh đã khai nó, và sổ hiện tại cũng đang lấy giá thuê nội bộ
làm doanh thu chuyến. Để trống thì mỗi chuyến máy sinh là một dòng doanh thu 0 kéo lãi lỗ xuống
sai. Dòng nào do lệnh sinh ra đều mang `nguon = "lenh_dieu_xe"`, nên luôn truy được số ấy từ đâu.

KHÔNG CHÉP KM VÀ CHI PHÍ: lệnh không có km thật, không có dầu, không có cầu đường. Những ô ấy để
trống cho Đội xe khai qua cửa của họ — mỗi con số một cửa nhập, như mọi chỗ khác.
"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fleet import Trip
from app.models.hr import DispatchOrder

NGUON_LENH = "lenh_dieu_xe"
KHONG_SINH = ("huy",)


def _chuyen_cua_lenh(db: Session, d: DispatchOrder) -> Trip | None:
    return db.execute(select(Trip).where(Trip.dispatch_id == d.id)).scalars().first()


def _khop_het(db: Session, d: DispatchOrder) -> Trip | None:
    """Khớp CẢ BỐN. Thiếu một là không đủ để máy tự nối hai dòng mà không ai nhìn."""
    if d.tour_id is None:
        return None
    return db.execute(select(Trip).where(
        Trip.dispatch_id.is_(None),
        Trip.vehicle_id == d.vehicle_id,
        Trip.tour_id == d.tour_id,
        Trip.ngay_di == d.date_from,
        Trip.ngay_ve == d.date_to,
    )).scalars().first()


def _nghi_khop(db: Session, d: DispatchOrder) -> list[Trip]:
    """Cùng xe, cùng ngày đi, chưa gắn lệnh — nhưng chưa đủ bốn. Chỉ để BÁO, không để nối."""
    return list(db.execute(select(Trip).where(
        Trip.dispatch_id.is_(None),
        Trip.vehicle_id == d.vehicle_id,
        Trip.ngay_di == d.date_from,
    )).scalars())


def _tom_tat(t: Trip) -> dict:
    return {"id": t.id, "ten_tour": t.ten_tour, "ngay_di": t.ngay_di, "ngay_ve": t.ngay_ve,
            "doanh_thu": float(t.doanh_thu) if t.doanh_thu is not None else None}


def dong(db: Session, d: DispatchOrder, boi: str = "") -> dict:
    """Gọi khi một lệnh chuyển sang `hoan_thanh`. Trả về việc đã làm, luôn nói ra."""
    if d.status in KHONG_SINH:
        return {"viec": "bo_qua", "noi": "Lệnh đã huỷ — không sinh chuyến."}

    co = _chuyen_cua_lenh(db, d)
    if co:
        return {"viec": "da_co", "chuyen_id": co.id,
                "noi": f"Lệnh này đã có chuyến #{co.id} — không tạo thêm."}

    khop = _khop_het(db, d)
    if khop:
        khop.dispatch_id = d.id
        db.flush()
        return {"viec": "da_gan", "chuyen_id": khop.id,
                "noi": f"Đã gắn lệnh vào chuyến #{khop.id} có sẵn (khớp xe, tour và cả hai ngày) "
                       "— không tạo dòng mới."}

    nghi = _nghi_khop(db, d)
    if nghi:
        return {"viec": "nghi_trung", "chuyen_nghi": [_tom_tat(t) for t in nghi],
                "noi": ("CHƯA SINH CHUYẾN: có " + str(len(nghi)) + " chuyến cùng xe cùng ngày đi "
                        "nhưng chưa khớp hết (lệch tour hoặc ngày về). Tạo mới là đếm doanh thu "
                        "hai lần, tự gắn là nối nhầm hai chuyến khác nhau — cần người xác nhận.")}

    t = Trip(
        vehicle_id=d.vehicle_id, driver_id=d.driver_id, tour_id=d.tour_id,
        ten_tour=_ten_tour(db, d), ngay_di=d.date_from, ngay_ve=d.date_to,
        doanh_thu=d.internal_price, dispatch_id=d.id,
        nguon=NGUON_LENH, created_by=(boi or d.created_by or "")[:50],
    )
    db.add(t); db.flush()
    thieu = cham_co(db, t)
    return {"viec": "da_sinh", "chuyen_id": t.id, "thieu": thieu,
            "noi": f"Đã sinh chuyến #{t.id} từ lệnh. Còn thiếu: {' · '.join(thieu)}."
                   if thieu else f"Đã sinh chuyến #{t.id} từ lệnh."}


# ═════════════════ DL-6 · CHUYẾN MÁY SINH PHẢI NÓI RA NÓ CÒN THIẾU GÌ ═════════════════
#
# Chủ tịch chốt 16/10/2026, sau một lần em báo sai và phải đính chính: cửa nhập km VÀ bảng chi phí
# chuyến ĐÃ CÓ ĐỦ từ lâu — km đầu, km cuối, km GPS, nguồn số km; chi phí có loại, số tiền, số lít,
# chứng từ, bên chịu. Chỗ hỏng không phải thiếu cửa.
#
# Chỗ hỏng là chuyến máy sinh ra ĐẾN LẶNG LẼ. Ba việc, mỗi việc một dòng trong mã:
#
#   1. CỜ KHÔNG ĐƯỢC CHẤM. `Trip.co` mặc định là "vang" và `co_ly_do` rỗng. Một chuyến vàng mà
#      không nói vì sao thì người xem hoặc bỏ qua, hoặc đoán — và đoán sai thì tệ hơn không có cờ.
#      `kiem_chuyen` đã biết chấm; chỉ là chưa ai gọi nó cho chuyến sinh từ lệnh.
#   2. LỜI ĐÓNG LỆNH nói "km và chi phí còn trống" cho MỌI chuyến, kể cả chuyến đã đủ số. Một câu
#      luôn đúng là một câu không ai đọc.
#   3. KHÔNG CÓ DANH SÁCH để làm theo. Biết "còn 12 chuyến thiếu số" mà phải tự đi tìm 12 chuyến ấy
#      trong sổ thì con số đếm chỉ làm người ta thấy có lỗi, không giúp sửa.
#
# KHÔNG CHẶN. Chủ tịch chọn «báo và đếm», không chọn «chặn xác nhận chuyến» — và đúng: 756 chuyến
# nạp bằng Excel đều không có km, một hàng rào chặn ở đây sẽ chặn nhầm cả sổ cũ.

THIEU_KM = "km thật (đầu/cuối)"
THIEU_CHI_PHI = "chưa có dòng chi phí nào"


def _con_thieu(db: Session, t: Trip) -> list[str]:
    """Một chuyến còn thiếu những số THẬT nào. Chỉ đọc, không ghi."""
    from app.models.fleet import TripCost
    ra = []
    if t.km_dau is None or t.km_cuoi is None:
        ra.append(THIEU_KM)
    n = db.execute(select(func.count()).select_from(TripCost).where(
        TripCost.trip_id == t.id)).scalar() or 0
    if not n:
        ra.append(THIEU_CHI_PHI)
    return ra


def cham_co(db: Session, t: Trip) -> list[str]:
    """Chấm cờ cho chuyến bằng CHÍNH bộ chấm cờ của Đội xe, không dựng bộ thứ hai.

    Dựng một bộ chấm riêng cho chuyến sinh từ lệnh thì hai bộ sẽ lệch nhau sau vài tháng, và lúc
    ấy không ai biết bộ nào đúng. Trả về danh sách còn thiếu để nơi gọi nói lại cho người bấm.
    """
    from app.services import fleet as FL
    kt = FL.kiem_chuyen(db, t)
    t.co, t.co_ly_do = kt["co"], " · ".join(kt["ly_do"])
    db.flush()
    return _con_thieu(db, t)


def chuyen_tu_lenh_thieu_so(db: Session, gioi_han: int = 50) -> dict:
    """Ô đếm thứ ba, kèm DANH SÁCH để bấm vào nhập — không chỉ một con số.

    Chỉ đếm chuyến SINH TỪ LỆNH (`nguon = lenh_dieu_xe`). Sổ cũ nạp bằng Excel cũng thiếu km, nhưng
    đó là việc nạp bù của Đội xe, không phải chỗ hở của chuỗi lệnh — gộp chung thì con số này không
    bao giờ về 0 và sẽ bị bỏ qua như mọi con số không bao giờ về 0.
    """
    ds = list(db.execute(select(Trip).where(Trip.nguon == NGUON_LENH)
                         .order_by(Trip.ngay_di.desc(), Trip.id.desc())).scalars())
    thieu = [(t, _con_thieu(db, t)) for t in ds]
    thieu = [(t, c) for t, c in thieu if c]
    return {"so": len(thieu), "tong_chuyen_tu_lenh": len(ds),
            "danh_sach": [{"chuyen_id": t.id, "lenh_id": t.dispatch_id, "tour": t.ten_tour,
                           "ngay_di": t.ngay_di.isoformat(), "ngay_ve": t.ngay_ve.isoformat(),
                           "co": t.co, "thieu": c}
                          for t, c in thieu[:gioi_han]]}


def _ten_tour(db: Session, d: DispatchOrder) -> str:
    from app.models.core import Tour
    t = db.get(Tour, d.tour_id) if d.tour_id else None
    return ((t.name if t else "") or "")[:160]


def gan_tay(db: Session, d: DispatchOrder, t: Trip) -> dict:
    """Cửa cho người xác nhận một chuyến NGHI KHỚP. Máy không tự làm việc này."""
    if t.dispatch_id is not None:
        raise ValueError(f"Chuyến #{t.id} đã gắn lệnh #{t.dispatch_id} rồi.")
    co = _chuyen_cua_lenh(db, d)
    if co:
        raise ValueError(f"Lệnh này đã có chuyến #{co.id}.")
    t.dispatch_id = d.id
    db.flush()
    # DL-6: gắn tay cũng là một chuyến vào chuỗi lệnh, nên cũng phải chấm cờ và nói còn thiếu gì.
    # Bỏ sót ở đây thì ô đếm mới đúng với chuyến máy sinh mà sai với chuyến người gắn.
    thieu = cham_co(db, t)
    return {"viec": "da_gan_tay", "chuyen_id": t.id, "lenh_id": d.id, "thieu": thieu}


# ═════════════════ HAI CON SỐ ĐẾM CHỖ CHUỖI CHƯA LIỀN ═════════════════
# Cùng hình dáng với ô «1/1 lệnh lập không qua cửa đề nghị» đã có: đếm chỗ hở, không chặn ai.

def lenh_xong_chua_co_chuyen(db: Session) -> dict:
    da_gan = select(Trip.dispatch_id).where(Trip.dispatch_id.is_not(None))
    n = db.execute(select(func.count()).select_from(DispatchOrder).where(
        DispatchOrder.status == "hoan_thanh", DispatchOrder.id.not_in(da_gan))).scalar() or 0
    tong = db.execute(select(func.count()).select_from(DispatchOrder).where(
        DispatchOrder.status == "hoan_thanh")).scalar() or 0
    return {"so": n, "tong_lenh_hoan_thanh": tong}


def chuyen_chua_gan_lenh(db: Session) -> dict:
    n = db.execute(select(func.count()).select_from(Trip).where(
        Trip.dispatch_id.is_(None))).scalar() or 0
    tong = db.execute(select(func.count()).select_from(Trip)).scalar() or 0
    return {"so": n, "tong_chuyen": tong}
