# -*- coding: utf-8 -*-
"""Đ-3 · Ba phép kiểm «hai đường cộng phải ra một số».

Ba lỗi có thật, tìm được trong ba tệp quyết toán khác nhau của phòng Điều hành, mỗi lỗi một cơ chế —
và CẢ BA đều vô hình trong Excel vì bảng vẫn cân:

  1. Nha Trang 10/07/2026, sheet CTT: ô tổng khối «B. TRẺ EM» viết =SUM(G23:G26) cho một khối có
     NĂM dòng. Cộng đủ là 4.200.000; ô tổng ghi 3.990.000. Thiếu 210.000 đ (vé Tháp Bà trẻ em), và
     số thiếu ấy chảy thẳng qua TỔNG CỘNG CHI rồi thành lãi ảo.

  2. Châu Âu 6 nước 27/05: cộng theo CỘT ra 1.705.894.683; cộng theo DÒNG ra 1.683.377.252. Chênh
     22.517.431 đ, đúng bằng vé 22.425.781 + bảo hiểm 91.650 của trưởng đoàn — khoản ấy đã được
     chia đều về 30 khách qua cột PHÍ TL, nhưng trưởng đoàn CÒN một dòng riêng ở cuối bảng. Không
     dòng nào sai riêng lẻ; giữ CẢ HAI mới là sai.

  3. Nha Trang, giữa hai sheet: HDV CHI ghi vé tham quan 44 × 30.000 = 1.320.000, trong khi chiết
     tính chỉ có 40 suất = 1.200.000. Lệch 120.000 đ, và không sheet nào biết sheet kia tồn tại.

--------------------------------------------------------------------------------------------------
GIỚI HẠN CỦA BỘ KIỂM NÀY — ĐỌC TRƯỚC KHI TIN NÓ
--------------------------------------------------------------------------------------------------

Làn rà soát (Codex, 12/9/2026) nói một câu đúng và tệp này chép lại nguyên văn để không ai quên:

    «Hai báo cáo cùng dùng một nguồn sai vẫn có thể khớp nhau. Kiểm tra số học không tự phát hiện
     sai cách xử lý thuế.»

Ba phép kiểm ở đây chỉ canh TÍNH NHẤT QUÁN SỐ HỌC giữa hai đường cộng của cùng một bộ dữ liệu. Chúng
KHÔNG biết số gốc có đúng không, KHÔNG biết một dòng chi có bị bỏ quên hẳn không, và KHÔNG bắt được
sai về cách xử lý thuế hay cách ghi nhận doanh thu. Đối chiếu với nguồn độc lập (hoá đơn, sao kê, tờ
khai) là việc khác và phải làm riêng.

Nói ra giới hạn ấy quan trọng hơn là có thêm một phép kiểm: một bộ kiểm được tin quá mức là thứ làm
người ta thôi tự nhìn.

--------------------------------------------------------------------------------------------------
CHỦ TỊCH CHỐT 12/9/2026 — SỐ NÀO LÀ SỐ CHỐT
--------------------------------------------------------------------------------------------------

    «Số chi tiết là số chốt, tự cộng lại từ dòng.»

Đây là ĐẢO NGƯỢC quyết định ngày 10/9/2026 đang ghi trong app/models/quyet_toan.py — bản ấy chốt
«số tổng là số chốt, lớp chi tiết chỉ là lớp dưới». Hai chỗ không được nói ngược nhau, nên tệp này
ghi rõ bản 12/9 là bản đang có hiệu lực, và K-b đổi vai: từ «chặn» thành «cộng lại từ dòng, rồi
NÓI RA chênh so với ô tổng của tệp gốc».

Hệ quả phải biết, vì nó là cái giá của lựa chọn này: cộng lại từ dòng KHÔNG bắt được một dòng chi bị
bỏ quên hẳn — thiếu dòng thì tổng mới cứ thế thấp đi và không có gì để so. Ô tổng của tệp gốc vì thế
được GIỮ LẠI và hiện ra, chứ không bị xoá: nó là bằng chứng duy nhất còn lại của việc thiếu dòng.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quyet_toan import TourSettlement, TourSettlementCostLine
from app.models.vietrip import TourCostLine
from app.services import gia_khach as GK

# Một đồng lệch là lệch. Nhưng phép chia phân bổ làm tròn tới 2 chữ số thập phân trên từng dòng, nên
# một chuyến 40 khách × 10 dòng chi có thể dồn sai số tới vài trăm đồng mà không ai làm gì sai.
# Ngưỡng này là ngưỡng của SAI SỐ LÀM TRÒN, không phải ngưỡng bỏ qua: trên nó là lỗi thật.
NGUONG_LAM_TRON = 1000.0

MUC = {"do": "Chặn – phải sửa trước khi đóng số", "vang": "Cảnh báo – phải có người nhìn"}


def _ket(ma: str, ten: str, muc: str, dat: bool, chenh: float | None = None,
         chi_tiet: str = "", so_lieu: dict | None = None) -> dict:
    return {"ma": ma, "ten": ten, "muc": muc, "dat": dat,
            "chenh": chenh, "chi_tiet": chi_tiet, "so_lieu": so_lieu or {}}


# =================================================================================================
# K-a · HAI CHIỀU CỘNG CỦA CÙNG MỘT BẢNG
# =================================================================================================

def ka_hai_chieu_cong(db: Session, tour_id: int) -> dict:
    """Σ giá vốn theo KHÁCH phải bằng Σ dòng chi ĐƯỢC PHÂN BỔ.

    Đây là phép kiểm bắt được lỗi châu Âu 6 nước. Trong tệp Excel hai con số ấy nằm ở hai ô cách
    nhau bốn mươi dòng và không ai đặt chúng cạnh nhau bao giờ.

    Dòng khai `khong_phan_bo` và dòng `chua_khai_quy_tac` CỐ Ý không nằm trong phép so: chúng không
    được chia về khách nên không có mặt ở vế trái. Nhưng số tiền của chúng được trả về để màn hình
    hiện ra — một chuyến có 50 triệu «chưa khai quy tắc» thì phép kiểm này đạt mà tờ quyết toán vẫn
    chưa xong.
    """
    pb = GK.phan_bo(db, tour_id)
    theo_khach = float(pb["tong_da_phan_bo"])

    dong = list(db.scalars(select(TourCostLine).where(
        TourCostLine.tour_id == tour_id, TourCostLine.status == "hd")))
    duoc_chia = 0.0
    for d in dong:
        tien = d.actual if d.actual is not None else d.budget
        qt = d.quy_tac_phan_bo or ""
        if tien is None or not qt or qt == "khong_phan_bo":
            continue
        duoc_chia += float(tien)

    chenh = round(theo_khach - duoc_chia, 2)
    dat = abs(chenh) <= NGUONG_LAM_TRON
    return _ket(
        "K-a", "Tổng theo khách = tổng theo dòng chi", "do", dat, chenh,
        "" if dat else
        ("Cùng một khoản chi đang nằm ở hai chỗ, hoặc một dòng chi được chia nhiều hơn số tiền nó "
         "có. Đây đúng là cơ chế đã làm tệp châu Âu 6 nước lệch 22.517.431 đ."),
        {"tong_theo_khach": theo_khach, "tong_dong_duoc_chia": duoc_chia,
         "tong_khong_phan_bo": float(pb["tong_khong_phan_bo"]),
         "tong_chua_khai_quy_tac": float(pb["tong_chua_khai"]),
         "so_dong_chua_khai": len(pb["chua_khai_quy_tac"])})


# =================================================================================================
# K-b · SỐ CHI TIẾT LÀ SỐ CHỐT — và chênh với ô tổng của tệp gốc phải HIỆN RA
# =================================================================================================

def kb_cong_lai_tu_dong(db: Session, settlement_id: int) -> dict:
    """Cộng lại từ dòng chiết tính, rồi so với ô tổng mà tệp Điều hành ghi sẵn.

    Theo chốt 12/9/2026 thì số cộng lại LÀ SỐ CHỐT. Ô tổng của tệp không bị xoá và không chặn ai —
    nó ở lại làm bằng chứng, vì nó là thứ duy nhất còn nói được «tệp gốc nghĩ tổng là bao nhiêu».

    Mức VÀNG chứ không ĐỎ: theo đúng lựa chọn của Chủ tịch, chênh ở đây không chặn việc đóng số.
    Nhưng nó nằm trong danh sách cảnh báo ở ĐẦU bảng, không giấu ở cuối.
    """
    s = db.get(TourSettlement, settlement_id)
    if s is None:
        return _ket("K-b", "Cộng lại từ dòng", "vang", True, None, "Không tìm thấy bản quyết toán")

    dong = list(db.scalars(select(TourSettlementCostLine).where(
        TourSettlementCostLine.settlement_id == settlement_id)))
    cong_chi = sum(float(d.thanh_tien or 0) for d in dong if d.ve == "chi")
    cong_thu = sum(float(d.thanh_tien or 0) for d in dong if d.ve == "thu")

    o_tong_chi = float(s.gia_von) if s.gia_von is not None else None
    o_tong_thu = float(s.doanh_thu) if s.doanh_thu is not None else None
    chenh_chi = None if o_tong_chi is None else round(cong_chi - o_tong_chi, 2)
    chenh_thu = None if o_tong_thu is None else round(cong_thu - o_tong_thu, 2)

    lech = [c for c in (chenh_chi, chenh_thu) if c is not None and abs(c) > NGUONG_LAM_TRON]
    dat = not lech
    return _ket(
        "K-b", "Số chốt lấy từ dòng chi tiết", "vang", dat,
        chenh_chi if chenh_chi not in (None, 0) else chenh_thu,
        "" if dat else
        ("Ô tổng trong tệp gốc khác với tổng cộng lại từ các dòng. Theo chốt 12/9 thì SỐ CỘNG LẠI là "
         "số chốt — nhưng chênh này phải có người nhìn, vì ô tổng thấp hơn cũng có thể là dấu hiệu "
         "một dòng chi bị bỏ quên hẳn, và cộng lại từ dòng KHÔNG bắt được chuyện đó."),
        {"cong_lai_chi": cong_chi, "o_tong_chi_cua_tep": o_tong_chi, "chenh_chi": chenh_chi,
         "cong_lai_thu": cong_thu, "o_tong_thu_cua_tep": o_tong_thu, "chenh_thu": chenh_thu,
         "so_dong": len(dong)})


# =================================================================================================
# K-c · MỘT KHOẢN CHỈ ĐƯỢC Ở MỘT CHỖ
# =================================================================================================

def kc_mot_khoan_mot_cho(db: Session, tour_id: int) -> dict:
    """Một dòng chi KHÔNG được vừa chia đều về mọi khách vừa gán đích danh cho một khách.

    Đây là ràng buộc CẤU TRÚC chặn tận gốc cơ chế đã gây lỗi châu Âu — K-a bắt hậu quả, K-c bắt
    nguyên nhân. Có cả hai vì K-a chỉ kêu khi hai con số đã lệch; nếu ai đó vừa nhân đôi một khoản
    vừa sửa mẫu số cho khớp thì K-a im, K-c vẫn kêu.

    `ma_khoan_muc` có cờ «đích danh» trong danh mục (vé máy bay, phí lãnh sự, dịch thuật). Dòng mang
    mã đích danh mà lại khai quy tắc phân bổ là mâu thuẫn ngay trên chính dòng ấy.
    """
    from app.services import khoan_muc_chi as KM

    dong = list(db.scalars(select(TourCostLine).where(
        TourCostLine.tour_id == tour_id, TourCostLine.status == "hd")))
    xung_dot = []
    for d in dong:
        qt = d.quy_tac_phan_bo or ""
        if not qt or qt == "khong_phan_bo":
            continue
        ma = d.ma_khoan_muc or ""
        # Mã lạ thì mac_dinh() trả rỗng và dòng ấy KHÔNG bị coi là đích danh – đúng, vì chưa biết
        # thì không kết luận. Dòng mã lạ đã có hàng đợi riêng ở danh mục khoản mục.
        if bool(KM.mac_dinh(ma).get("dich_danh")):
            xung_dot.append({
                "dong_id": d.id, "noi_dung": d.description, "ma_khoan_muc": ma,
                "quy_tac_phan_bo": qt,
                "vi_sao": "khoản mục này là chi ĐÍCH DANH cho một khách, nhưng dòng lại khai quy "
                          "tắc chia đều – hai cách ghi loại trừ nhau",
            })
    dat = not xung_dot
    return _ket(
        "K-c", "Một khoản chỉ được ở một chỗ", "do", dat, None,
        "" if dat else "Có dòng chi vừa khai đích danh vừa khai chia đều – chọn một.",
        {"xung_dot": xung_dot})


# =================================================================================================
# Gọi cả ba
# =================================================================================================

def soat(db: Session, tour_id: int, settlement_id: int | None = None) -> dict:
    """Chạy cả ba phép kiểm cho một chuyến.

    `settlement_id` rỗng thì bỏ K-b — chuyến nhập thẳng trong VTOS không có «ô tổng của tệp gốc» để
    so, và đó là trạng thái bình thường chứ không phải thiếu sót.
    """
    kq = [ka_hai_chieu_cong(db, tour_id), kc_mot_khoan_mot_cho(db, tour_id)]
    if settlement_id is not None:
        kq.insert(1, kb_cong_lai_tu_dong(db, settlement_id))
    chan = [k for k in kq if not k["dat"] and k["muc"] == "do"]
    canh = [k for k in kq if not k["dat"] and k["muc"] == "vang"]
    return {
        "tour_id": tour_id, "phep_kiem": kq,
        "duoc_dong_so": not chan,
        "so_chan": len(chan), "so_canh_bao": len(canh),
        "gioi_han": ("Bộ kiểm này chỉ canh tính nhất quán số học giữa hai đường cộng. Nó KHÔNG bắt "
                     "được một dòng chi bị bỏ quên hẳn, và không bắt được sai về cách xử lý thuế. "
                     "Đối chiếu với hoá đơn và sao kê là việc riêng."),
    }
