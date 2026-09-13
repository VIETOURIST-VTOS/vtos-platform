"""Đ-2 · Thuế GTGT ở MỨC CHUYẾN — và vì sao nó phải trừ vào lợi nhuận.

CHỦ TỊCH CHỐT 12/9/2026:

    "VAT đầu vào tương ứng với đầu ra. Nếu đầu vào không đủ thì sẽ phải đóng 8% VAT chênh lệch.
     Nên trừ vào lợi nhuận của tour."

Trước bản này VTOS tính lợi nhuận chuyến bằng `doanh thu − giá vốn` (lai_lo_tour.py). Doanh thu ấy ĐÃ
GỒM thuế đầu ra, giá vốn ĐÃ GỒM thuế đầu vào, và hai phần thuế KHÔNG triệt tiêu nhau — vì thuế suất
đầu ra và đầu vào khác nhau, và vì luôn có một phần chi KHÔNG CÓ HOÁ ĐƠN (không sinh thuế đầu vào).

Đo trên tệp thật của phòng Điều hành — đoàn Hồ Tràm 2N1Đ (MICEHT2N1D.02110726):

    doanh thu (gồm VAT)   92.855.000
    tổng chi              76.972.600     (trong đó 11.150.000 không hoá đơn)
    VAT đầu ra             6.878.148
    VAT đầu vào            4.868.815
    thuế phát sinh         2.009.333
    ---------------------------------------------------
    lợi nhuận ĐÚNG        13.873.067     (chính tệp Điều hành tính như vậy)
    lợi nhuận VTOS cũ     15.882.400     ← THỪA 2.009.333 đ = 14,5% lợi nhuận thật

Kiểm chéo bằng đường khác cho cùng một số: doanh thu trước thuế 85.976.852 − (chi 76.972.600 − thuế
đầu vào được khấu trừ 4.868.815) = 13.873.067. Hai đường phải ra một số, và ở đây chúng ra một số.

--------------------------------------------------------------------------------------------------
BỐN ĐIỀU TỆP NÀY CỐ Ý LÀM, VÀ VÌ SAO
--------------------------------------------------------------------------------------------------

1. KHÔNG KẸP VỀ 0 Ở MỨC CHUYẾN.

   Một chuyến có thuế đầu vào lớn hơn đầu ra thì `thue_gtgt` ÂM. Số âm ấy là khấu trừ THẬT — nó bù
   sang chuyến khác trong cùng kỳ khai thuế. Kẹp về 0 ở mức chuyến thì tổng thuế của tất cả các
   chuyến không bao giờ khớp tờ khai kỳ, và không ai tìm ra chênh ở đâu vì mỗi chuyến đều "đúng".

   Vì thế tên hàm và tên cột là `thue_gtgt_phat_sinh` chứ không phải "thuế phải nộp". Thuế PHẢI NỘP
   là của KỲ (xem reports.vat_return); ở mức chuyến chỉ có phần PHÁT SINH.

2. THUẾ ĐẦU VÀO CHỈ TÍNH PHẦN CÓ HOÁ ĐƠN.

   Cột `khong_hoa_don` trên dòng chi phí đã có sẵn và nó chính là con số Chủ tịch nói tới: phần chi
   không có hoá đơn thì không khấu trừ được gì, nên công ty gánh trọn 8% trên phần ấy. Tệp Hồ Tràm
   tách hẳn hai dòng "CHI PHÍ CÓ VAT" và "CHI PHÍ KO VAT" đúng vì lý do này.

3. TOUR NƯỚC NGOÀI KHÔNG TỰ ÁP 8% LÊN TOÀN BỘ DOANH THU.

   Với tour trọn gói có phần dịch vụ tiêu dùng ngoài Việt Nam, giá tính thuế GTGT đầu ra KHÔNG hiển
   nhiên là toàn bộ doanh thu. Đây là chỗ phải có Kế toán chốt, không phải chỗ để mã đoán.

   Mức độ nghiêm trọng của việc đoán sai: tệp UK 27/5 có doanh thu 2.479.513.034 đ. Áp 8% lên toàn
   bộ ra thuế đầu ra ~183,7 triệu; nếu giá tính thuế thật hẹp hơn nhiều thì con số ấy sai hàng trăm
   triệu TRÊN MỘT CHUYẾN, và nó sai theo chiều làm lợi nhuận teo lại — tức là chiều khiến người đọc
   kết luận ngược hẳn về việc có nên chạy tuyến ấy nữa không.

   Nên: `hinh_thuc == "nuoc_ngoai"` thì trả về `thue_gtgt = None` với cơ sở `cho_ke_toan_nuoc_ngoai`.
   Rỗng là rỗng. Khi Kế toán chốt cách tính, mở khoá bằng THAM SỐ, không phải bằng cách sửa tệp này.

4. NÓI RÕ SỐ ĐẦU RA LÀ ĐO ĐƯỢC HAY SUY RA.

   Có dòng doanh thu chi tiết (`tour_doanh_thu_dong`) thì thuế đầu ra là số ĐO ĐƯỢC — cộng cột
   `tien_thue`. Chưa có dòng nào thì suy từ thuế suất đã khai trong tham số. Hai thứ ấy khác nhau về
   độ tin, nên phải khác nhau về NHÃN. Trộn chung là tạo ra một con số không ai biết nên tin tới đâu.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.lop3_tour import TourDoanhThuDong
from app.models.vietrip import TourCostLine
from app.services import thu_ho_chi_ho as THC
from app.services.rules import get_param, get_param_text

# Khoá tham số thuế suất đầu ra. Chủ tịch chốt 8% ngày 12/9/2026; khai trong rules.DEFAULT_PARAMS.
KHOA_THUE_SUAT_RA = "thue_suat_dau_ra"
KHOA_GOM_THUE = "gia_ban_gom_thue_gtgt"

CO_SO = {
    "do_tu_dong_doanh_thu": "Đo được – cộng thuế đầu ra của từng dòng doanh thu",
    "suy_tu_thue_suat": "Suy ra – chưa có dòng doanh thu chi tiết, lấy thuế suất đã khai",
    "nuoc_ngoai_hai_phan": "Tour nước ngoài – phần giá vốn 0%, phần lợi nhuận chịu thuế",
    "nuoc_ngoai_chua_co_gia_von": "Tour nước ngoài – chưa có giá vốn nên chưa tách được hai phần",
    "chua_co_doanh_thu": "Chưa có doanh thu – không có gì để tính thuế",
}

VI_SAO = {
    "nuoc_ngoai_chua_co_gia_von":
        "Tour nước ngoài xuất hoá đơn hai dòng: phần giá vốn 0%, phần lợi nhuận chịu thuế. Chưa có "
        "giá vốn thì chưa biết ranh giới giữa hai dòng ấy nằm ở đâu.",
    "chua_co_doanh_thu":
        "Chuyến chưa có doanh thu.",
}


def thue_suat_ra(db: Session, hom_nay: date | None = None) -> float:
    """Thuế suất đầu ra đang hiệu lực. Tham số có hiệu lực THEO NGÀY: chuyến đã đi giữ nguyên thuế
    suất của ngày nó khởi hành, nên đổi chính sách hôm nay không làm đổi tờ quyết toán đã ký."""
    return get_param(db, KHOA_THUE_SUAT_RA, hom_nay)


def gia_ban_gom_thue(db: Session, hom_nay: date | None = None) -> bool:
    """Giá bán niêm yết ĐÃ GỒM thuế GTGT hay CHƯA.

    Đây là một quy ước, không phải một phép tính — và hai quy ước lệch nhau đúng 8% của chính phần
    chịu thuế. Trên một chuyến châu Âu 1 tỷ với 100 triệu lợi nhuận, chênh giữa hai cách là 592.593 đ
    tiền thuế; không lớn, nhưng nó lệch ở MỌI chuyến và không bao giờ tự lộ ra.

    Mặc định là ĐÃ GỒM, vì đó là quy ước đang dùng trong chính tệp quyết toán của phòng Điều hành:
    đoàn Hồ Tràm tính `3.790.000 / 1.08` để ra giá trước thuế, tức giá niêm yết cho khách là giá
    cuối cùng khách trả.
    """
    return str(get_param_text(db, KHOA_GOM_THUE, hom_nay) or "1").strip() not in ("0", "", "khong")


# ------------------------------------------------------------------------------------------------
# Hai vế của phép trừ
# ------------------------------------------------------------------------------------------------

def vat_dau_ra_do_duoc(db: Session, tour_ids: list[int]) -> dict[int, dict]:
    """Cộng thuế đầu ra từ DÒNG DOANH THU. Chỉ đếm dòng đã khai `tien_thue`.

    Trả về `{tour_id: {"vat_ra": float, "so_dong": int, "so_dong_chua_khai_thue": int}}`.
    Chuyến không có dòng nào thì KHÔNG có mặt trong dict — khác hẳn có mặt với giá trị 0.
    """
    if not tour_ids:
        return {}
    q = select(
        TourDoanhThuDong.tour_id.label("tid"),
        func.coalesce(func.sum(func.coalesce(TourDoanhThuDong.tien_thue, 0)), 0).label("vat"),
        func.count(TourDoanhThuDong.id).label("so_dong"),
        # Dòng chưa khai thuế suất là dòng chưa ai nói nó chịu thuế bao nhiêu. Đếm riêng để nói ra,
        # không lặng lẽ coi bằng 0.
        func.coalesce(func.sum(case((TourDoanhThuDong.thue_suat.is_(None), 1), else_=0)), 0).label("chua_khai"),
    ).where(
        TourDoanhThuDong.tour_id.in_(tour_ids),
        # Đ-7: DÒNG THU HỘ KHÔNG PHẢI DOANH THU nên không có mặt ở đây.
        #
        # Không phải vì nó mang thuế — nó không mang. Mà vì SỰ CÓ MẶT của nó làm `so_dong > 0`, và
        # `mot_chuyen()` đọc điều đó thành "chuyến đã có dòng doanh thu chi tiết, thuế đầu ra là số
        # ĐO ĐƯỢC". Một chuyến chỉ mới ghi mỗi khoản thu hộ sẽ báo thuế đầu ra bằng 0 với nhãn
        # "đo được" — sai, và sai với cái nhãn đáng tin nhất.
        TourDoanhThuDong.loai.not_in(THC.LOAI_KHONG_PHAI_DOANH_THU),
    ).group_by(TourDoanhThuDong.tour_id)
    return {r.tid: {"vat_ra": float(r.vat or 0), "so_dong": int(r.so_dong or 0),
                    "so_dong_chua_khai_thue": int(r.chua_khai or 0)}
            for r in db.execute(q).all()}


def vat_dau_vao(db: Session, tour_ids: list[int]) -> dict[int, dict]:
    """Cộng thuế đầu vào ĐƯỢC KHẤU TRỪ từ dòng chi phí còn hiệu lực, kèm phần chi không hoá đơn.

    `vat_hoa_don` rỗng nghĩa là chưa ai nhập hoá đơn cho dòng ấy — nó KHÔNG được khấu trừ, và số dòng
    như vậy được đếm riêng để bảng còn nói ra được "con số này có thể còn thiếu".
    """
    if not tour_ids:
        return {}
    q = select(
        TourCostLine.tour_id.label("tid"),
        func.coalesce(func.sum(func.coalesce(TourCostLine.vat_hoa_don, 0)), 0).label("vat"),
        func.coalesce(func.sum(func.coalesce(TourCostLine.khong_hoa_don, 0)), 0).label("khong_hd"),
        func.count(TourCostLine.id).label("so_dong"),
        func.coalesce(func.sum(case((TourCostLine.vat_hoa_don.is_(None), 1), else_=0)), 0).label("chua_khai"),
    ).where(TourCostLine.status == "hd", TourCostLine.tour_id.in_(tour_ids)).group_by(TourCostLine.tour_id)
    return {r.tid: {"vat_vao": float(r.vat or 0), "chi_khong_hoa_don": float(r.khong_hd or 0),
                    "so_dong_chi": int(r.so_dong or 0),
                    "so_dong_chua_khai_vat": int(r.chua_khai or 0)}
            for r in db.execute(q).all()}


# ------------------------------------------------------------------------------------------------
# Phép tính
# ------------------------------------------------------------------------------------------------

def _rong(co_so: str) -> dict:
    return {"co_so": co_so, "co_so_ten": CO_SO[co_so], "vat_ra": None, "vat_vao": None,
            "thue_gtgt": None, "chi_khong_hoa_don": 0.0, "thue_suat_ra": None,
            "vi_sao": VI_SAO.get(co_so, ""), "canh_bao": []}


def _thue_trong_so(tien: float, ts: float, gom_thue: bool) -> float:
    """Tiền thuế của một khoản, tuỳ khoản ấy ĐÃ GỒM thuế hay CHƯA.

    Hai cách ra hai con số khác nhau đúng 8% của chính nó, nên không được để mặc định ngầm.
    """
    return (tien - tien / (1.0 + ts)) if gom_thue else (tien * ts)


def mot_chuyen(db: Session, *, hinh_thuc: str | None, doanh_thu: float | None,
               ra: dict | None, vao: dict | None, gia_von: float | None = None,
               hom_nay: date | None = None) -> dict:
    """Thuế GTGT phát sinh của MỘT chuyến.

    `ra` / `vao` là phần tử của hai hàm cộng ở trên (None khi chuyến chưa có dòng nào).
    `hinh_thuc` là `trong_nuoc` / `nuoc_ngoai` / None (chưa xếp).
    `gia_von` CHỈ dùng cho tour nước ngoài – nó là ranh giới giữa hai dòng hoá đơn.
    """
    if not doanh_thu:
        return _rong("chua_co_doanh_thu")

    ts = thue_suat_ra(db, hom_nay)
    gom = gia_ban_gom_thue(db, hom_nay)
    v_vao = float(vao["vat_vao"]) if vao else 0.0
    khong_hd = float(vao["chi_khong_hoa_don"]) if vao else 0.0
    canh_bao = []

    # -------------------------------------------------------------------------------------------
    # TOUR NƯỚC NGOÀI — HOÁ ĐƠN HAI DÒNG (Chủ tịch chốt 12/9/2026)
    # -------------------------------------------------------------------------------------------
    if hinh_thuc == "nuoc_ngoai":
        if gia_von is None:
            kq = _rong("nuoc_ngoai_chua_co_gia_von")
            kq["chi_khong_hoa_don"] = khong_hd
            return kq
        phan_0 = min(float(gia_von), float(doanh_thu))
        phan_chiu_thue = float(doanh_thu) - phan_0
        v_ra = _thue_trong_so(phan_chiu_thue, ts, gom)

        # KẸP Ở ĐÂY LÀ ĐÚNG, và nó KHÁC HẲN chỗ cấm kẹp ở mục 1 phần đầu tệp.
        #
        # Mục 1 cấm kẹp `vat_ra − vat_vao` về 0, vì số âm ở đó là KHẤU TRỪ THẬT, bù sang chuyến khác.
        # Ở đây kẹp là chuyện khác: một chuyến bán DƯỚI giá vốn thì tờ hoá đơn chỉ có đúng một dòng
        # 0%, không có dòng thứ hai nào để ghi số âm lên. Hoá đơn không có dòng âm. Phần lỗ vẫn là lỗ
        # thật và vẫn hiện ở lãi gộp — nó chỉ không sinh ra thuế đầu ra âm.
        if float(gia_von) > float(doanh_thu):
            canh_bao.append(
                f"Bán dưới giá vốn {float(gia_von) - float(doanh_thu):,.0f} đ – cả hoá đơn là một dòng "
                "0%, không có phần lợi nhuận để chịu thuế. Lỗ vẫn hiện ở lãi gộp.")
        if vao and vao["so_dong_chua_khai_vat"]:
            canh_bao.append(
                f"{vao['so_dong_chua_khai_vat']} dòng chi chưa nhập thuế trên hoá đơn – phần này KHÔNG "
                "được khấu trừ")
        return {
            "co_so": "nuoc_ngoai_hai_phan", "co_so_ten": CO_SO["nuoc_ngoai_hai_phan"],
            "vat_ra": v_ra, "vat_vao": v_vao,
            "thue_gtgt": v_ra - v_vao,
            "chi_khong_hoa_don": khong_hd,
            "thue_suat_ra": ts,
            "gia_ban_gom_thue": gom,
            # Hai dòng của tờ hoá đơn, để màn hình và tệp xuất dùng ĐÚNG số này, không tự chia lại.
            "hoa_don_hai_dong": [
                {"noi_dung": "Phần dịch vụ tiêu dùng ngoài Việt Nam", "so_tien": phan_0,
                 "thue_suat": 0.0, "tien_thue": 0.0},
                {"noi_dung": "Phần chênh lệch (lợi nhuận)", "so_tien": phan_chiu_thue,
                 "thue_suat": ts, "tien_thue": v_ra},
            ],
            "vi_sao": "",
            "canh_bao": canh_bao,
        }

    # -------------------------------------------------------------------------------------------
    # TOUR TRONG NƯỚC — toàn bộ doanh thu chịu thuế
    # -------------------------------------------------------------------------------------------
    if ra and ra["so_dong"] > 0:
        co_so = "do_tu_dong_doanh_thu"
        v_ra = float(ra["vat_ra"])
    else:
        co_so = "suy_tu_thue_suat"
        v_ra = _thue_trong_so(float(doanh_thu), ts, gom)

    if co_so == "do_tu_dong_doanh_thu" and ra and ra["so_dong_chua_khai_thue"]:
        canh_bao.append(
            f"{ra['so_dong_chua_khai_thue']} dòng doanh thu chưa khai thuế suất – thuế đầu ra có thể còn thiếu")
    if vao and vao["so_dong_chua_khai_vat"]:
        canh_bao.append(
            f"{vao['so_dong_chua_khai_vat']} dòng chi chưa nhập thuế trên hoá đơn – phần này KHÔNG được "
            "khấu trừ, nên thuế phát sinh đang cao hơn thực tế nếu các dòng ấy có hoá đơn")
    if khong_hd:
        canh_bao.append(
            f"{khong_hd:,.0f} đ chi không có hoá đơn – công ty gánh trọn thuế đầu ra trên phần này")

    return {
        "co_so": co_so, "co_so_ten": CO_SO[co_so],
        "vat_ra": v_ra, "vat_vao": v_vao,
        # KHÔNG kẹp về 0 — xem mục 1 của phần đầu tệp.
        "thue_gtgt": v_ra - v_vao,
        "chi_khong_hoa_don": khong_hd,
        "thue_suat_ra": ts,
        "vi_sao": "",
        "canh_bao": canh_bao,
    }


def nhieu_chuyen(db: Session, chuyen: list[dict], hom_nay: date | None = None) -> dict[int, dict]:
    """Tính cho cả bảng bằng HAI câu truy vấn, không phải hai câu cho mỗi chuyến.

    `chuyen` là list `{"tour_id", "hinh_thuc", "doanh_thu", "gia_von"}` – `gia_von` chỉ cần cho tour
    nước ngoài.
    """
    ids = [c["tour_id"] for c in chuyen]
    ra = vat_dau_ra_do_duoc(db, ids)
    vao = vat_dau_vao(db, ids)
    return {c["tour_id"]: mot_chuyen(db, hinh_thuc=c.get("hinh_thuc"),
                                     doanh_thu=c.get("doanh_thu"),
                                     ra=ra.get(c["tour_id"]), vao=vao.get(c["tour_id"]),
                                     gia_von=c.get("gia_von"),
                                     hom_nay=hom_nay)
            for c in chuyen}


def loi_nhuan_sau_thue(loi_nhuan_truoc_thue: float | None, thue: float | None) -> float | None:
    """Một chỗ duy nhất làm phép trừ cuối, để không màn hình nào tự trừ lại theo cách của mình.

    Thiếu một trong hai vế thì RỖNG, không phải bằng vế còn lại: một con số "sau thuế" mà chưa trừ
    thuế là con số nói dối đúng vào chỗ nó đang hứa.
    """
    if loi_nhuan_truoc_thue is None or thue is None:
        return None
    return loi_nhuan_truoc_thue - thue
