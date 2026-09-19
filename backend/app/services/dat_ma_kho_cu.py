# -*- coding: utf-8 -*-
"""CỬA ĐẶT MÃ TOUR cho những tệp quyết toán cũ không khai mã.

VÌ SAO PHẢI CÓ CỬA NÀY

Đo ngày 18/9/2026 trên 740 bản ghi quyết toán gốc đối chiếu với đủ 1.744 chuyến của VTOS:

    ghép được với chuyến đã có : 649
    còn lại                    :  91
        trong đó 19 tệp KHÔNG KHAI MÃ TOUR NÀO — 29,85 tỷ đồng

29,85 tỷ ấy không "thiếu", nó VÔ DANH. Không có mã thì hai việc đều tắc:
  - không tạo được chuyến: `tours.code` là chỗ cửa nạp quyết toán đi tìm chuyến để treo dòng vào;
  - không đối chiếu được: không ai biết chuyến ấy đã nằm trên VTOS hay chưa, nên mỗi lần nạp là
    một lần có thể nạp chồng — mà giá vốn gấp đôi thì mọi bảng vẫn cân.

Cửa `tao_chuyen_kho_cu` đã đặt sẵn mã tạm `KHOCU-DDMMYY-…` cho những tệp ấy, và đó là lựa chọn
đúng cho một cái máy: nó nhìn là biết máy đặt, và nó không giả vờ là mã thật. Nhưng mã tạm nằm
trong danh sách tour mãi mãi cho tới khi có người sửa, mà KHÔNG CÓ CHỖ NÀO ĐỂ SỬA — bảng xem
trước bày mã ra nhưng không nhận lại gì. Đó là việc còn thiếu, và tệp này là chỗ bù vào.

CHỦ TỊCH CHỐT 18/9/2026 về cách đặt mã:

    "(EU220726 = Châu Âu khởi hành 22/07/2026) = em đặt theo cách này"

tức viết tắt tuyến + ngày khởi hành ddmmyy. Cửa này KHÔNG tự sinh mã theo nếp ấy: suy tuyến từ
tên tệp là đoán, và đoán sai thì mã sai nằm lại trong danh sách tour. Cửa này NHẬN mã người đặt,
soát nó, và nói ra mọi chỗ có thể sai trước khi ai bấm.

BỐN PHÉP SOÁT, VÀ VÌ SAO TỪNG CÁI

1. MÃ PHẢI TRÔNG NHƯ MÃ. Dùng lại `la_ma_that()` — luật rút từ 436 mã có thật: không khoảng
   trắng, có ít nhất một chữ số, dài 6–24. Kho cũ đã có 19 tệp gõ TÊN KHÁCH vào ô mã ("CÔNG TY
   DƯỢC", "CẢNG SÀI GÒN"); nhận thêm một cái nữa là để tên khách nằm trong danh sách tour.

2. KHÔNG ĐƯỢC TRÙNG MÃ CHUYẾN ĐANG CÓ. Đây là phép soát QUAN TRỌNG NHẤT và là lý do cửa này
   không thể chỉ là một ô nhập tự do. Đặt trùng mã một chuyến đã có thì cửa tạo chuyến bỏ qua
   (không tạo), rồi cửa nạp quyết toán treo toàn bộ dòng chi của tệp này lên CHUYẾN CỦA NGƯỜI
   KHÁC — giá vốn chuyến ấy gấp đôi, lợi nhuận âm, và mọi bảng vẫn cân vì tổng nào cũng cộng từ
   dòng. Đo được đúng kiểu hỏng ấy ngày 18/9: 57 chuyến mang giá vốn gấp đôi, ghi dư 2,63 tỷ,
   và không có gì đỏ lên suốt hai tuần.

3. HAI TỆP KHÔNG ĐƯỢC CÙNG MỘT MÃ — TRỪ KHI CÓ NGƯỜI NÓI RÕ LÀ CỐ Ý. Hai tệp cùng chuyến có
   thật (bảng chính và bảng land, hai xe của một đoàn). Nhưng nó cũng là hình dạng của lỗi chép
   bản mẫu quên sửa mã. Máy không phân biệt được, nên nó DỪNG và hỏi, chứ không chọn hộ.

4. MÃ ĐÃ ĐẶT RỒI THÌ ĐẶT LẠI LÀ THAY, KHÔNG ĐẺ DÒNG THỨ HAI. Và một tệp ĐÃ SINH RA CHUYẾN
   (`tour_id` khác None) thì KHÔNG cho đổi mã ở đây: lúc ấy đổi mã là đổi mã của một chuyến đang
   có dòng tiền treo lên, việc ấy phải đi đường sửa chuyến, có nhật ký riêng.

CỬA NÀY KHÔNG TẠO CHUYẾN. Nó chỉ ghi "tệp này tên là mã gì". Tạo chuyến vẫn là cửa
`tao_chuyen_kho_cu`, vẫn một lần bấm riêng, vẫn một dòng nhật ký riêng.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import tao_chuyen_kho_cu as TC


def _ban_do(db: Session) -> dict[str, object]:
    from app.models.kho_cu import KhoCuTepChuyen
    return {r.khoa_tep: r for r in db.scalars(select(KhoCuTepChuyen))}


def ma_nguoi_dat(db: Session) -> dict[str, str]:
    """{khoá tệp: mã} của những tệp đã có người đặt mã và CHƯA sinh ra chuyến.

    Chỉ trả phần `tour_id is None`. Tệp đã sinh chuyến thì mã của nó là mã của một chuyến đang
    sống, không còn là một đề xuất — trả nó về đây sẽ khiến cửa tạo chuyến tưởng là mã mới.
    """
    return {k: r.ma_tour for k, r in _ban_do(db).items() if r.tour_id is None and r.ma_tour}


def _ma_da_co(db: Session) -> set[str]:
    from app.models.core import Tour
    return {(c or "").strip().upper() for c in db.scalars(select(Tour.code))}


def soat(db: Session, cap: list[dict]) -> dict:
    """Soát một lô {ten_tep, ma_tour}. KHÔNG ghi gì. Trả về từng dòng kèm mức."""
    da_co = _ma_da_co(db)
    ban_do = _ban_do(db)
    hang, thay_trong_lo = [], {}
    for x in cap:
        ten = (x.get("ten_tep") or "").strip()
        ma = (x.get("ma_tour") or "").strip()
        khoa = TC.khoa_tep(ten)
        h = {"ten_tep": ten, "khoa_tep": khoa, "ma_tour": ma, "chan": [], "hoi": []}
        if not khoa:
            h["chan"].append("Thiếu tên tệp – không biết đặt mã cho tệp nào")
        if not ma:
            h["chan"].append("Thiếu mã tour")
        elif not TC.la_ma_that(ma):
            h["chan"].append(
                f"{ma!r} không có dạng một mã tour (mã không có khoảng trắng, có ít nhất một chữ "
                f"số, dài 6–24 ký tự). Kho cũ đã có 19 tệp gõ TÊN KHÁCH vào ô mã – nhận thêm là "
                f"để tên khách nằm trong danh sách tour.")
        if ma and ma.upper() in da_co:
            h["chan"].append(
                f"Đã có chuyến mang mã {ma!r} trong VTOS. Đặt trùng thì cửa tạo chuyến bỏ qua, rồi "
                f"cửa nạp quyết toán treo toàn bộ dòng chi của tệp này lên CHUYẾN CỦA NGƯỜI KHÁC – "
                f"giá vốn chuyến ấy gấp đôi mà mọi bảng vẫn cân.")
        if ma:
            thay_trong_lo.setdefault(ma.upper(), []).append(ten)
        cu = ban_do.get(khoa)
        if cu is not None and cu.tour_id is not None:
            h["chan"].append(
                f"Tệp này đã sinh ra chuyến {cu.ma_tour!r} (tour id {cu.tour_id}). Đổi mã ở đây là "
                f"đổi mã một chuyến đang có dòng tiền treo lên – việc ấy đi đường sửa chuyến.")
        elif cu is not None and cu.ma_tour and cu.ma_tour != ma:
            h["hoi"].append(f"Tệp này đang mang mã {cu.ma_tour!r}; đặt lại là THAY, không thêm dòng.")
        hang.append(h)

    for ma, ten_ds in thay_trong_lo.items():
        if len(ten_ds) < 2:
            continue
        for h in hang:
            if (h["ma_tour"] or "").upper() == ma:
                h["hoi"].append(
                    f"{len(ten_ds)} tệp cùng đặt mã {ma!r}: {', '.join(t[:40] for t in ten_ds)}. "
                    f"Có thể đúng (bảng chính + bảng land, hai xe một đoàn), có thể là chép bản mẫu "
                    f"quên sửa. Máy không phân biệt được – người đặt xác nhận.")
    return {
        "so_dong": len(hang),
        "dat_duoc": sum(1 for h in hang if not h["chan"]),
        "bi_chan": sum(1 for h in hang if h["chan"]),
        "phai_xac_nhan": sum(1 for h in hang if not h["chan"] and h["hoi"]),
        "hang": hang,
    }


def dat(db: Session, cap: list[dict], boi: str, xac_nhan: bool = False,
        ke_ca_phai_hoi: bool = False) -> dict:
    """Ghi mã người đặt. `xac_nhan=False` chỉ xem. KHÔNG commit – người gọi commit."""
    from app.models.kho_cu import KhoCuTepChuyen

    kq = soat(db, cap)
    if not xac_nhan:
        return {**kq, "da_ghi": 0, "message": "Mới XEM – chưa ghi gì."}

    ban_do = _ban_do(db)
    ghi, bo = 0, []
    for h in kq["hang"]:
        if h["chan"]:
            bo.append({"ten_tep": h["ten_tep"], "vi_sao": h["chan"][0]})
            continue
        if h["hoi"] and not ke_ca_phai_hoi:
            bo.append({"ten_tep": h["ten_tep"], "vi_sao": h["hoi"][0]})
            continue
        r = ban_do.get(h["khoa_tep"])
        if r is None:
            db.add(KhoCuTepChuyen(khoa_tep=h["khoa_tep"][:200], ten_tep=h["ten_tep"][:255],
                                  ma_tour=h["ma_tour"][:30], tour_id=None))
        else:
            r.ten_tep = h["ten_tep"][:255]
            r.ma_tour = h["ma_tour"][:30]
        ghi += 1
    db.flush()
    return {**kq, "da_ghi": ghi, "bo": bo,
            "message": (f"Đã đặt mã cho {ghi} tệp. CHƯA tạo chuyến nào – tạo chuyến là cửa "
                        f"'Tạo CHUYẾN còn thiếu từ kho quyết toán cũ', một lần bấm riêng.")}
