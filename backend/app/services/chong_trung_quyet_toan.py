# -*- coding: utf-8 -*-
"""CHỐNG TRÙNG khi nạp kho quyết toán cũ vào VTOS.

Chủ tịch chốt 11/9/2026: nạp trọn kho tháng 1–6/2026, NHƯNG không được trùng với dữ liệu đang có
trên VTOS. Tệp này là chỗ duy nhất trả lời câu "nạp cái này vào thì có thành hai lần không".

BỐN KIỂU TRÙNG, KHÁC NHAU HẲN VỀ CÁCH XỬ

1. TRÙNG TỆP – hai tệp khác tên nhưng cùng một chuyến.
   Bản đối chiếu H1 tự ghi: "Cần kiểm tra 8 cặp file khác ngày khởi hành nhưng trùng…". Nạp cả hai
   là một chuyến có hai lần giá vốn. Máy KHÔNG tự chọn bên nào – nó nêu cặp ra và dừng.

2. TRÙNG NGUỒN – chuyến đã có giá vốn từ Vietrip hoặc từ bộ nạp khác.
   Đây là kiểu nguy nhất vì nó KHÔNG tự lộ: cộng thêm một bộ dòng chi vào chuyến đã có dòng chi thì
   giá vốn gấp đôi, lợi nhuận âm, mà mọi bảng vẫn cân vì tổng nào cũng cộng từ dòng.

3. NẠP LẠI – cùng một tệp nạp lần thứ hai.
   Xử bằng XOÁ-RỒI-GHI theo (tour, nguồn): nạp bao nhiêu lần cũng ra một kết quả. Đây là kiểu duy
   nhất máy tự xử được mà không cần hỏi ai.

4. TRÙNG TRONG CHÍNH TỆP – một khoản chi ghi hai dòng giống hệt nhau.
   Không chặn: tour thật có chi hai lần cùng một thứ (hai bữa trưa cùng giá, hai phòng cùng hạng).
   Chỉ đánh dấu để người lập tờ nhìn lại.

NGUYÊN TẮC XUYÊN SUỐT: KHÔNG BAO GIỜ TỰ ĐỘNG ĐÈ

Máy được phép thay phần do CHÍNH NÓ ghi trước đó (cùng nguồn). Đè lên phần do nguồn khác ghi – nhất
là dữ liệu Vietrip đồng bộ về – là xoá dữ liệu thật của công ty theo suy đoán của một bộ nạp. Việc
ấy phải có người bấm, và bấm thì để lại dấu vết.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

# Nguồn mà bộ nạp kho cũ được phép thay khi nạp lại. Mọi nguồn khác là của người khác.
NGUON_CUA_TOI = "kho_cu_h1_2026"

# Mức: "nang" chặn nạp, "hoi" phải có người quyết, "nhe" chỉ ghi chú.
NANG, HOI, NHE = "nang", "hoi", "nhe"


def _chuan(s: str) -> str:
    """Chuẩn hoá một chuỗi để so sánh: bỏ dấu, bỏ khoảng trắng thừa, viết hoa.

    Kho cũ gõ mã tour bằng nhiều kiểu: "NT001.03100726", "nt001.03100726", "NT001. 03100726".
    So bằng chuỗi thô thì ba cái ấy là ba chuyến khác nhau, và chống trùng thành vô nghĩa.
    """
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def van_tay_tep(noi_dung: bytes) -> str:
    """Mã băm nội dung tệp. Hai tệp khác tên mà cùng mã băm là CÙNG MỘT TỆP."""
    return hashlib.sha256(noi_dung).hexdigest()[:16]


def van_tay_chuyen(d: dict) -> str:
    """Dấu nhận dạng một CHUYẾN, để bắt hai tệp cùng chuyến mà khác tên.

    Dùng mã tour khi có. Không có mã thì ghép ngày đi + số khách + tổng thu – ba thứ cùng trùng thì
    gần như chắc chắn là một chuyến. Cố ý KHÔNG dùng tên tệp: kho cũ đặt tên bằng tay, hai tệp cùng
    chuyến có tên khác hẳn nhau ("QT TOUR ĐÀ LẠT 14.06.2026" và "QTT DL001.03140626").
    """
    if d.get("ma_tour"):
        return "MA:" + _chuan(d["ma_tour"])
    # Suy từ ba thứ. Nhưng CẢ BA cùng rỗng thì không suy được gì – lúc ấy phải trả về một dấu RIÊNG
    # cho từng tệp, chứ không để chúng gom thành một nhóm "cùng chuyến".
    #
    # Bản đầu trả về chuỗi "SUY:None|None|None" cho mọi tệp không đọc được gì, và 24 tệp khác hẳn
    # nhau bị báo là "cùng khai một chuyến". Một phép chống trùng báo trùng ở chỗ không trùng thì
    # người ta học cách bỏ qua nó, và rồi bỏ qua cả lúc nó báo đúng.
    if d.get("ngay_di") is None and d.get("so_khach") is None and d.get("tong_thu") is None:
        return "RIENG:" + _chuan(d.get("ten_tep"))
    return "SUY:{}|{}|{}".format(d.get("ngay_di"), d.get("so_khach"),
                                 None if d.get("tong_thu") is None else round(d["tong_thu"]))


# ---------------------------------------------------------------------------------------------
# 1. Trùng giữa các tệp trong chính lô nạp
# ---------------------------------------------------------------------------------------------

def trung_trong_lo(ds: list[dict]) -> list[dict]:
    """Những chuyến bị nhiều tệp cùng khai. Trả về danh sách va chạm, KHÔNG tự chọn bên nào.

    Chọn hộ là chỗ dễ sai nhất: hai tệp cùng mã tour có thể là (a) một tệp sửa lại của tệp kia, (b)
    hai chuyến thật khác ngày mà ai đó gõ nhầm mã, hoặc (c) một tệp nháp quên xoá. Ba trường hợp ấy
    xử ba cách khác nhau và chỉ người làm mới biết là cái nào.
    """
    theo_van_tay: dict[str, list[dict]] = {}
    theo_bam: dict[str, list[dict]] = {}
    for d in ds:
        theo_van_tay.setdefault(van_tay_chuyen(d), []).append(d)
        if d.get("van_tay_tep"):
            theo_bam.setdefault(d["van_tay_tep"], []).append(d)

    ra = []
    for bam, nhom in theo_bam.items():
        if len(nhom) > 1:
            ra.append({"kieu": "tep_giong_het", "muc": NANG, "khoa": bam,
                       "tep": [x["ten_tep"] for x in nhom],
                       "noi": (f"{len(nhom)} tệp có nội dung GIỐNG HỆT nhau (cùng mã băm). Đây là "
                               f"cùng một tệp được lưu nhiều tên – chỉ nạp MỘT.")})
    da_bao = {t for x in ra for t in x["tep"]}
    for vt, nhom in theo_van_tay.items():
        if len(nhom) < 2:
            continue
        ten = [x["ten_tep"] for x in nhom]
        if set(ten) <= da_bao:
            continue
        # MÃ TOUR CÒN SÓT TỪ BẢN MẪU – đây là một kiểu hỏng riêng, không phải trùng chuyến.
        #
        # Đo được: 112 tệp cùng khai mã "PT14012022". Đó là mã của bản mẫu Phan Thiết tháng 1/2022
        # mà người lập chép lại rồi quên sửa. Chúng KHÔNG phải một chuyến – chúng là 112 chuyến khác
        # nhau mang chung một cái mã sai. Gọi đây là "trùng" rồi bảo "chọn một" là hướng người ta
        # xoá 111 chuyến thật.
        if len(nhom) >= 10:
            ra.append({
                "kieu": "ma_tour_con_sot_tu_ban_mau", "muc": NANG, "khoa": vt, "tep": ten,
                "noi": (f"{len(nhom)} tệp cùng mang mã tour '{vt.replace('MA:', '')}'. Số lượng này "
                        f"lớn tới mức không thể là trùng chuyến – gần như chắc chắn là mã còn sót "
                        f"trong bản mẫu mà người lập quên sửa. ĐỪNG gộp chúng: phải gán lại mã tour "
                        f"thật cho từng tệp trước khi nạp, nếu không {len(nhom)} chuyến sẽ dồn hết "
                        f"vào một chuyến.")})
            continue
        thu = {None if x.get("tong_thu") is None else round(x["tong_thu"]) for x in nhom}
        ra.append({
            "kieu": "cung_chuyen_khac_tep", "muc": NANG, "khoa": vt, "tep": ten,
            "noi": (f"{len(nhom)} tệp cùng khai chuyến {vt.replace('MA:', '')}. "
                    + ("Doanh thu đọc được GIỐNG nhau – nhiều khả năng là bản sao, chọn một."
                       if len(thu) == 1 else
                       f"Doanh thu đọc được KHÁC nhau ({', '.join(str(x) for x in sorted(thu, key=str))}) "
                       f"– phải xem là hai chuyến thật hay một tệp đã sửa lại."))})
    return ra


# ---------------------------------------------------------------------------------------------
# 2. Trùng với dữ liệu ĐANG CÓ trên VTOS
# ---------------------------------------------------------------------------------------------

def doi_chieu_he_thong(db, d: dict, tour_id: int | None) -> list[dict]:
    """Chuyến này trên VTOS đã có sẵn những gì. Chỉ ĐỌC, không sửa gì.

    Gọi trước khi ghi, cho TỪNG chuyến. Trả về danh sách va chạm kèm mức.
    """
    from sqlalchemy import func, select
    from app.models.lop3_tour import BookingKhach, TourDoanhThuDong, TourHdvChi
    from app.models.vietrip import TourCostLine

    ra = []
    if tour_id is None:
        ra.append({"kieu": "khong_co_chuyen", "muc": NANG,
                   "noi": (f"Không có chuyến mã '{d.get('ma_tour') or '(trống)'}' trong VTOS. "
                           f"Quyết toán phải gắn vào chuyến đã có – tạo chuyến trước rồi nạp lại.")})
        return ra

    # ---- dòng chi đang có, TÁCH THEO NGUỒN ----
    theo_nguon = dict(db.execute(
        select(TourCostLine.source, func.count(TourCostLine.id))
        .where(TourCostLine.tour_id == tour_id)
        .group_by(TourCostLine.source)).all())
    cua_toi = theo_nguon.pop(NGUON_CUA_TOI, 0)
    cua_nguoi_khac = {k: v for k, v in theo_nguon.items() if v}

    if cua_toi:
        ra.append({"kieu": "nap_lai", "muc": NHE,
                   "noi": (f"Chuyến này đã được nạp từ kho cũ trước đó ({cua_toi} dòng chi). "
                           f"Nạp lại là THAY phần ấy, không cộng thêm.")})
    if cua_nguoi_khac:
        mo = ", ".join(f"{k or '(không ghi nguồn)'}: {v} dòng" for k, v in sorted(cua_nguoi_khac.items()))
        ra.append({
            "kieu": "da_co_gia_von_nguon_khac", "muc": HOI,
            "noi": (f"Chuyến này ĐÃ CÓ giá vốn từ nguồn khác – {mo}. Nạp thêm kho cũ vào là chuyến "
                    f"có HAI lần giá vốn: lợi nhuận âm, mà mọi bảng vẫn cân vì tổng nào cũng cộng "
                    f"từ dòng nên không ai nhìn ra. Phải chọn: giữ nguồn đang có và bỏ tệp này, hay "
                    f"xoá nguồn đang có rồi nạp. Máy không tự chọn.")})

    # ---- dòng khách và doanh thu ----
    # ĐẾM RIÊNG PHẦN CỦA CHÍNH BỘ NẠP NÀY.
    #
    # Nếu gộp chung thì sau lần nạp đầu, chính những dòng vừa ghi trở thành "dữ liệu đang có" và
    # lần nạp thứ hai bị chặn bằng cảnh báo do chính nó tạo ra. Người chạy sẽ thấy "bỏ qua 453 tệp"
    # mà không hiểu vì sao, rồi gõ --ke-ca-canh-bao để cho qua – và từ đó cái cờ ấy được bật mặc
    # định, kể cả khi va chạm là thật.
    sk_toi = db.scalar(select(func.count(BookingKhach.id)).where(
        BookingKhach.tour_id == tour_id, BookingKhach.nguoi_sua == NGUON_CUA_TOI)) or 0
    sk = (db.scalar(select(func.count(BookingKhach.id))
                    .where(BookingKhach.tour_id == tour_id)) or 0) - sk_toi
    if sk and d.get("khach"):
        ra.append({"kieu": "da_co_dong_khach", "muc": HOI,
                   "noi": (f"Chuyến này đã có {sk} dòng khách do nguồn KHÁC tạo, tệp mang thêm "
                           f"{len(d['khach'])} dòng. Hai danh sách khách chồng nhau thì số khách "
                           f"của chuyến sai, và giá vốn bình quân đầu khách sai theo.")})
    sd = db.scalar(select(func.count(TourDoanhThuDong.id))
                   .where(TourDoanhThuDong.tour_id == tour_id)) or 0
    if sd:
        ra.append({"kieu": "da_co_doanh_thu", "muc": HOI,
                   "noi": f"Chuyến này đã có {sd} dòng doanh thu trong VTOS."})
    sh_toi = db.scalar(select(func.count(TourHdvChi.id)).where(
        TourHdvChi.tour_id == tour_id, TourHdvChi.nguoi_nhap == NGUON_CUA_TOI)) or 0
    sh = (db.scalar(select(func.count(TourHdvChi.id))
                    .where(TourHdvChi.tour_id == tour_id)) or 0) - sh_toi
    if sh and d.get("hdv", {}).get("dong"):
        ra.append({"kieu": "da_co_hdv_chi", "muc": HOI,
                   "noi": f"Chuyến này đã có {sh} dòng HDV chi do nguồn KHÁC tạo."})
    return ra


# ---------------------------------------------------------------------------------------------
# 3. Trùng trong chính một tệp
# ---------------------------------------------------------------------------------------------

def trung_trong_tep(d: dict) -> list[dict]:
    """Hai dòng chi giống hệt nhau trong cùng một tệp. CHỈ ĐÁNH DẤU, không chặn.

    Tour thật có chi hai lần cùng một thứ: hai bữa trưa cùng giá, hai phòng cùng hạng, hai chặng xe
    cùng tuyến. Chặn ở đây là chặn nhầm dữ liệu đúng. Nhưng cũng có thật chuyện dán nhầm một dòng,
    nên nói ra để người lập tờ nhìn lại trước khi ký.
    """
    dem: dict[tuple, list[int]] = {}
    for x in d.get("chi", []):
        if x.get("thanh_tien") is None:
            continue
        k = (_chuan(x.get("noi_dung")), _chuan(x.get("doi_tac")), round(x["thanh_tien"], 2))
        dem.setdefault(k, []).append(x.get("_hang"))
    ra = []
    for (nd, _dt, tien), hang in dem.items():
        if len(hang) > 1:
            ra.append({"kieu": "dong_chi_lap", "muc": NHE, "hang": hang,
                       "noi": (f"{len(hang)} dòng chi giống hệt nhau ({tien:,.0f} đ) ở hàng "
                               f"{', '.join(str(h) for h in hang)}. Có thể đúng (hai bữa cùng giá), "
                               f"có thể là dán nhầm – người lập tờ xác nhận.")})
    return ra


# ---------------------------------------------------------------------------------------------
# 4. Đối chiếu với bản H1 đã tổng hợp – phép kiểm thứ hai
# ---------------------------------------------------------------------------------------------

SAI_SO = 0.005          # 0,5%


def doi_chieu_ban_tong_hop(d: dict, ref: dict | None) -> list[dict]:
    """So số bộ đọc rút ra với số của bản đối chiếu H1 mà Kế toán đã chốt.

    HAI NGUỒN, MỘT SỰ THẬT – LỆCH THÌ DỪNG, KHÔNG CHỌN BỪA

    Bản đối chiếu H1 là số đã đối chiếu với MISA và đã dùng để lập báo cáo. Bộ đọc kho cũ là một lần
    đọc độc lập. Chúng khớp nhau thì tin được; lệch nhau thì một trong hai sai và không có cách nào
    biết bên nào nếu không mở tệp ra xem.

    Đo trên 594 tệp khớp được tên: doanh thu bộ đọc ra 90,7% số đã chốt, giá vốn 71,1%. Phần lệch
    nằm gần hết ở tour châu Âu – sheet land ghi bằng EUR/GBP, và vài tệp mang theo một sheet 'MẪU'
    là bản trắng năm 2020. Cho nên TIỀN thì lấy theo bản đã chốt, còn bộ đọc làm phép kiểm.
    """
    if ref is None:
        return [{"kieu": "khong_co_trong_ban_tong_hop", "muc": HOI,
                 "noi": ("Tệp này không có trong bản đối chiếu H1. Không có số thứ hai để soát – "
                         "phải có người xác nhận trước khi nạp.")}]
    ra = []
    for khoa, ten in (("tong_thu", "doanh thu"), ("tong_chi", "giá vốn")):
        a, b = d.get(khoa), ref.get(khoa)
        if b is None:
            continue
        if a is None:
            ra.append({"kieu": f"khong_doc_duoc_{khoa}", "muc": NHE,
                       "noi": (f"Bộ đọc không rút được {ten} từ tệp; lấy theo bản đã chốt "
                               f"({b:,.0f} đ).")})
            continue
        if abs(a - b) > max(1000.0, abs(b) * SAI_SO):
            ra.append({"kieu": f"lech_{khoa}", "muc": HOI,
                       "noi": (f"{ten.capitalize()} lệch: bộ đọc {a:,.0f} đ, bản đã chốt {b:,.0f} đ "
                               f"(chênh {a - b:+,.0f} đ). Lấy theo bản đã chốt và đánh dấu tệp này "
                               f"để người xem lại.")})
    return ra


# ---------------------------------------------------------------------------------------------
# Gộp
# ---------------------------------------------------------------------------------------------

def kiem_mot(d: dict, ref: dict | None, db=None, tour_id: int | None = None) -> dict:
    """Toàn bộ phép chống trùng cho MỘT tệp. db=None thì bỏ qua phần đối chiếu hệ thống."""
    va = []
    va += doi_chieu_ban_tong_hop(d, ref)
    va += trung_trong_tep(d)
    if db is not None:
        va += doi_chieu_he_thong(db, d, tour_id)
    for x in d.get("thieu", []):
        va.append({"kieu": "doc_thieu", "muc": NHE, "noi": x})
    return {
        "ten_tep": d.get("ten_tep"),
        "ma_tour": d.get("ma_tour"),
        "va_cham": va,
        "nang": [x for x in va if x["muc"] == NANG],
        "hoi": [x for x in va if x["muc"] == HOI],
        "nap_duoc": not any(x["muc"] == NANG for x in va),
    }
