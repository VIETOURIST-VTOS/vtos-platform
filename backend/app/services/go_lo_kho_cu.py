# -*- coding: utf-8 -*-
"""GỠ CẢ LÔ kho quyết toán cũ – đường đi ngược của hai cửa nạp.

VÌ SAO PHẢI CÓ

Chủ tịch giao nạp kho T1–T6/2026 lên để chạy trên số thật, nạp thử tháng 1 trước. Nhưng nạp thử mà
không gỡ lại được thì không phải "thử" – nó là một chiều, và người ta sẽ không dám bấm lần nào cả,
hoặc bấm rồi phải dọn tay mấy trăm dòng.

Hai cửa nạp đã làm đúng một nửa việc: nạp lại cùng một lô thì THAY, không nhân đôi. Nửa còn lại là
gỡ hẳn, và đó là tệp này.

CÁI KHÓ THẬT: MỘT CHUYẾN CÓ 33 BẢNG CÓ THỂ TREO VÀO

Rà mô hình ngày 13/9/2026: **33 cột khoá ngoại trỏ về `tours.id`**, rải khắp lop3_tour, accounting,
hr, cskh, fleet, visa, nghia_vu, su_co_tour, suppliers, ban_hang… Xoá một chuyến bằng cách liệt kê
tay các bảng con là cách chắc chắn để sót – và sót thì có hai kiểu:

  · sót một bảng CÓ ràng buộc khoá ngoại -> nổ. To tiếng, nhưng còn may.
  · sót một bảng KHÔNG ràng buộc chặt    -> còn lại dòng mồ côi trỏ vào chuyến không tồn tại.
    Im lặng, và tháng sau một báo cáo nào đó cộng phải nó.

Tệp này KHÔNG liệt kê tay. Nó hỏi chính mô hình: bảng nào có cột trỏ về `tours.id`. Bảng thứ 34
thêm vào tháng sau cũng được hỏi, không phải sửa gì ở đây.

VÀ QUY TẮC AN TOÀN ĐI KÈM: KHÔNG XOÁ CHUYẾN CÒN DỮ LIỆU CỦA NGƯỜI KHÁC

Gỡ lô nghĩa là gỡ ĐÚNG phần lô ấy mang vào, không phải "xoá sạch chuyến". Nếu sau khi nạp có người
đã gắn chứng từ, mở phiếu đặt, ghi sự cố hay lập đề nghị chi lên chuyến ấy thì việc của họ phải còn
nguyên – nên chuyến ấy được GIỮ LẠI và nêu ra, chứ không xoá kèm.

Thứ tự bắt buộc, và nó là thứ tự ngược của lúc nạp:

    1. Xoá DÒNG QUYẾT TOÁN mang nguồn kho_cu_h1_2026 (dòng chi, dòng khách, dòng HDV, PHIẾU ĐẶT),
       cùng SỔ SÁCH RIÊNG của lô (sổ tệp↔chuyến).
    2. Xoá CHUYẾN do cửa tạo chuyến sinh ra – CHỈ những chuyến sau bước 1 không còn gì treo vào.

Làm ngược lại thì bước 2 không bao giờ xoá được chuyến nào, vì dòng quyết toán của chính lô đang
treo ở đấy.
"""
from __future__ import annotations

from sqlalchemy import func, select

# Cùng một nhãn nguồn với hai cửa nạp – gỡ được đúng phần chúng mang vào.
from app.services.tao_chuyen_kho_cu import NGUON

# Ba bảng mà cửa nạp quyết toán ghi vào, và MỖI BẢNG GHI NGUỒN Ở MỘT CỘT KHÁC NHAU. Phải khai từng
# bảng một, y như lúc nạp: viết một vòng lặp chung rồi đoán tên cột là cách chắc chắn để hoặc nổ,
# hoặc tệ hơn – xoá nhầm dòng của nguồn khác vì điều kiện lọc không áp được.
def _bang_dong_quyet_toan():
    from app.models.core import Booking
    from app.models.lop3_tour import BookingKhach, TourHdvChi
    from app.models.vietrip import TourCostLine
    return (
        (TourCostLine, TourCostLine.source, "dòng chi phí"),
        (BookingKhach, BookingKhach.nguoi_sua, "dòng khách"),
        (TourHdvChi, TourHdvChi.nguoi_nhap, "dòng HDV"),
        # PHIẾU ĐẶT theo người bán – thêm 13/9/2026 cùng với việc dựng phiếu lúc nạp. Bảng này phải
        # đứng SAU `booking_khach` trong bộ này, vì dòng khách treo vào phiếu: xoá phiếu trước là để
        # lại khoá mồ côi. Và nó phải CÓ MẶT ở đây, vì gỡ lô mà sót phiếu là để lại doanh thu ma
        # trong mọi báo cáo doanh số – đúng cái mà lô này sinh ra để làm cho đúng.
        (Booking, Booking.source, "phiếu đặt"),
    )


def _bang_so_sach_cua_lo():
    """Bảng SỔ SÁCH RIÊNG của lô: treo vào chuyến, nhưng không phải việc của ai cả.

    `kho_cu_tep_chuyen` ghi tệp nào đẻ ra chuyến nào. Nó có khoá ngoại về `tours.id`, nên bộ dò
    bảng con thấy nó và – nếu để nguyên – nó CHẶN việc xoá mọi chuyến của lô, kể cả chuyến trống
    trơn. Nhưng nó không phải việc người khác gắn lên chuyến; nó là giấy tờ nội bộ của chính lô,
    sinh ra lúc nạp và phải mất đi lúc gỡ.

    Tách thành một khái niệm riêng thay vì "trừ tên bảng ra" ở vài chỗ: bảng sổ sách thứ hai thêm
    vào tháng sau chỉ cần khai ở đây, không phải sửa ba hàm.
    """
    from app.models.kho_cu import KhoCuTepChuyen
    return ((KhoCuTepChuyen, KhoCuTepChuyen.tour_id, "sổ tệp↔chuyến"),)


def _bang_treo_vao_chuyen():
    """Mọi bảng có cột khoá ngoại trỏ về `tours.id` – HỎI MÔ HÌNH, không liệt kê tay.

    Đây là chỗ quan trọng nhất của tệp. Danh sách viết tay hôm nay đúng 33 bảng; tháng sau có bảng
    thứ 34 thì danh sách ấy sai một cách im lặng, và không phép thử nào biết. Hỏi mô hình thì bảng
    mới tự có mặt.
    """
    from app.db.session import Base

    ra = []
    for bang in Base.metadata.tables.values():
        if bang.name == "tours":
            continue
        for cot in bang.columns:
            if any(k.column.table.name == "tours" and k.column.name == "id"
                   for k in cot.foreign_keys):
                ra.append((bang, cot))
                break
    return ra


def _chuyen_cua_lo(db):
    """Chuyến do CỬA TẠO CHUYẾN sinh ra. Dấu: hai ô confirmed_by / approved_by mang nhãn nguồn."""
    from app.models.core import Tour
    return db.scalars(select(Tour).where(Tour.confirmed_by == NGUON,
                                         Tour.approved_by == NGUON)).all()


def _con_gi_treo(db, tour_id: int, tru_bang: set[str]) -> dict[str, int]:
    """Sau khi xoá dòng của lô, chuyến này còn gì treo vào? Rỗng nghĩa là xoá được."""
    con = {}
    for bang, cot in _bang_treo_vao_chuyen():
        if bang.name in tru_bang:
            continue
        n = db.execute(select(func.count()).select_from(bang)
                       .where(cot == tour_id)).scalar() or 0
        if n:
            con[bang.name] = n
    return con


def xem(db) -> dict:
    """XEM TRƯỚC – KHÔNG xoá gì. Nói ra đúng thứ nút gỡ sẽ làm.

    Phải đếm được cả hai phần: dòng quyết toán sẽ mất, và chuyến nào xoá được / chuyến nào giữ lại
    vì đã có người gắn việc lên.
    """
    dong = {}
    for bang, cot_nguon, nhan in _bang_dong_quyet_toan():
        dong[nhan] = db.execute(
            select(func.count()).select_from(bang).where(cot_nguon == NGUON)).scalar() or 0

    # Mô phỏng bước 1: coi như ba bảng ấy đã sạch phần của lô, rồi hỏi chuyến còn gì khác không.
    # Trừ ra CẢ hai loại: bảng dòng quyết toán của lô (sẽ sạch sau bước 1) và bảng sổ sách riêng
    # của lô (sẽ mất theo lô). Không trừ sổ sách thì mọi chuyến đều "còn treo" và không chuyến nào
    # xoá được – lô thành thứ nạp vào được mà không gỡ ra được.
    ten_ba_bang = ({b.__tablename__ for b, _, _ in _bang_dong_quyet_toan()}
                   | {b.__tablename__ for b, _, _ in _bang_so_sach_cua_lo()})
    xoa_duoc, giu_lai = [], []
    for t in _chuyen_cua_lo(db):
        # Ba bảng của lô: đếm phần KHÔNG mang nhãn nguồn – đó mới là việc của người khác.
        khac = {}
        for bang, cot_nguon, nhan in _bang_dong_quyet_toan():
            n = db.execute(select(func.count()).select_from(bang)
                           .where(bang.tour_id == t.id, cot_nguon != NGUON)).scalar() or 0
            if n:
                khac[bang.__tablename__] = n
        khac.update(_con_gi_treo(db, t.id, ten_ba_bang))
        (giu_lai if khac else xoa_duoc).append(
            {"id": t.id, "ma": t.code, "ten": t.name, "ngay_di": t.start_date,
             "con_treo": khac})

    return {
        "nguon": NGUON,
        "dong_quyet_toan": dong,
        "tong_dong": sum(dong.values()),
        "chuyen_cua_lo": len(xoa_duoc) + len(giu_lai),
        "xoa_duoc": xoa_duoc,
        "giu_lai": giu_lai,
        "ghi_chu": (
            f"XEM TRƯỚC – chưa xoá gì. Sẽ gỡ {sum(dong.values())} dòng quyết toán mang nhãn "
            f"'{NGUON}' và xoá {len(xoa_duoc)} chuyến do lô này tạo ra. "
            f"{len(giu_lai)} chuyến ĐƯỢC GIỮ LẠI vì đã có người gắn việc lên chúng sau khi nạp – "
            f"gỡ kèm là xoá mất việc của họ. Dòng do Vietrip hay do người nhập tay tạo ra KHÔNG bị "
            f"đụng tới, kể cả khi nằm trên chính những chuyến này."),
    }


def go(db, boi: str, xac_nhan: bool = False) -> dict:
    """GỠ THẬT. Mặc định KHÔNG làm gì – phải bấm xác nhận.

    Mặc định không làm gì là cố ý: đây là nút duy nhất trong hệ xoá một lượt mấy trăm dòng và mấy
    trăm chuyến. Gọi nhầm một lần mà nó chạy luôn thì không có đường lui nào.
    """
    kq = xem(db)
    if not xac_nhan:
        return {**kq, "da_go_dong": 0, "da_xoa_chuyen": 0,
                "message": ("CHƯA GỠ GÌ. Đây là bản xem trước. Bấm xác nhận thì mới gỡ, và lần bấm "
                            "ấy vào nhật ký mang tên người bấm.")}

    from app.models.core import Tour

    # BƯỚC 1 – dòng quyết toán của lô.
    da_go = 0
    for bang, cot_nguon, _nhan in _bang_dong_quyet_toan():
        da_go += db.query(bang).filter(cot_nguon == NGUON).delete(synchronize_session=False)
    # Sổ sách riêng của lô: xoá theo CHUYẾN của lô, vì các bảng ấy không mang cột nguồn. Phải xoá ở
    # bước 1 cùng mọi thứ khác, nếu không chúng chặn bước 2 và không chuyến nào xoá được.
    ds_id = [t.id for t in _chuyen_cua_lo(db)]
    if ds_id:
        for bang, cot_tour, _nhan in _bang_so_sach_cua_lo():
            db.query(bang).filter(cot_tour.in_(ds_id)).delete(synchronize_session=False)
    db.flush()

    # BƯỚC 2 – chuyến của lô, CHỈ những chuyến giờ đã trống. Hỏi lại sau khi xoá dòng, không dùng
    # kết quả xem trước: bước 1 vừa đổi đúng cái mà bước 2 phải nhìn.
    # Hỏi TOÀN BỘ bảng, không trừ bảng nào. Sau bước 1, dòng còn lại trong ba bảng của lô đúng là
    # dòng của nguồn khác – chúng PHẢI chặn việc xoá chuyến, y như mọi bảng khác.
    xoa, giu = [], []
    for t in _chuyen_cua_lo(db):
        con = _con_gi_treo(db, t.id, set())
        if con:
            giu.append({"id": t.id, "ma": t.code, "con_treo": con})
            continue
        xoa.append(t.code)
        db.delete(t)
    db.flush()

    return {
        **kq,
        "da_go_dong": da_go, "da_xoa_chuyen": len(xoa), "giu_lai_khi_go": giu,
        "message": (
            f"Đã gỡ {da_go} dòng quyết toán mang nhãn '{NGUON}' và xoá {len(xoa)} chuyến do lô này "
            f"tạo ra. {len(giu)} chuyến giữ lại vì đã có người gắn việc lên. Dòng của Vietrip và "
            f"dòng người nhập tay còn nguyên."),
    }
