"""Giá từng khách theo tuổi, và phân bổ chi phí chung cho từng khách.

Hai việc này đi cùng nhau vì chúng là hai nửa của một tờ quyết toán: doanh thu của từng khách và
giá vốn của từng khách. Sheet QT của Điều hành chính là hai nửa ấy đặt cạnh nhau.

QUY TẮC GIÁ – Chủ tịch chốt 10/9/2026, sửa tỷ lệ 11/9/2026

                       TRONG NƯỚC      NƯỚC NGOÀI
    dưới  2 tuổi  -> em bé        10%             30%
    dưới 12 tuổi  -> trẻ em       90%             90%
    từ  12 tuổi   -> người lớn    giá đầy đủ      giá đầy đủ

TỶ LỆ TÁCH THEO HÌNH THỨC TOUR. Một tỷ lệ chung cho cả hai là sai về nghiệp vụ chứ không chỉ sai con
số: tour nước ngoài có vé máy bay quốc tế, visa và bảo hiểm mà trẻ nhỏ vẫn trả gần bằng người lớn,
nên hạ sâu là lỗ ngay; tour trong nước thì phần lớn chi phí là ghế xe và suất ăn.

Sáu con số nằm ở bảng tham số (tuoi_em_be, tuoi_tre_em, ty_le_tre_em_trong_nuoc,
ty_le_tre_em_nuoc_ngoai, ty_le_em_be_trong_nuoc, ty_le_em_be_nuoc_ngoai) và có hiệu lực
THEO NGÀY – tệp này không gán cứng con số nào. Chuyến đã đi giữ nguyên tỷ lệ của ngày nó khởi hành,
nên đổi chính sách hôm nay không làm đổi lợi nhuận của những tờ quyết toán đã ký.

Tỷ lệ 0,90 đến từ việc đo bốn mẫu thật: SIN/MAL 89,99%, UK 88,67%, Nha Trang 83,80%. Con số 0,75 chốt
hôm 10/9 không mẫu nào đang theo.

HAI TRỤC, HAI CỘT

    nhom_khach : tra_tien / mien_phi / noi_bo / dai_ly   -> AI TRẢ TIỀN
    loai_tuoi  : nguoi_lon / tre_em / em_be              -> TÍNH GIÁ BAO NHIÊU

Tệp này chỉ quyết định loai_tuoi. nhom_khach do người nhập chọn, vì máy không đoán được ai là nhân
viên nội bộ và ai là khách của đại lý.

TUỔI TÍNH TẠI NGÀY KHỞI HÀNH, KHÔNG PHẢI HÔM NAY

Đứa trẻ 11 tuổi rưỡi lúc đi tour sẽ 12 tuổi vào lúc kế toán mở lại tờ quyết toán ba tháng sau. Tính
lại lúc đọc là đổi số trên một tờ đã ký.

THIẾU NGÀY SINH THÌ KHÔNG ĐOÁN

Không có ngày sinh thì trả None, và tờ quyết toán phải kêu lên. Mặc định thành người lớn là thu thừa
tiền của khách mà không ai phát hiện, vì bảng vẫn cân.

NĂM QUY TẮC PHÂN BỔ

Đọc ngược ra từ chính tệp mẫu. Mỗi cột chi trong sheet QT chia theo một mẫu số khác nhau, và tệp
không viết mẫu số ấy ở đâu cả:

    Bảo hiểm  210.000 ÷ 42 =  5.000   -> chia đều MỌI khách, kể cả hai cháu miễn phí
    Nước suối 630.000 ÷ 40 = 15.750   -> chia đều khách CÓ THU
    Phí TL  1.500.000 ÷ 40 = 37.500   -> chia đều khách CÓ THU
    Land   48.310.000       -> 1.343.030 người lớn / 570.000 trẻ em -> theo ĐỐI TƯỢNG

"Khách CÓ THU" nghĩa là nhóm tra_tien và có tiền bán > 0. Khách của đại lý và nhân viên nội bộ KHÔNG
tính vào mẫu số ấy dù họ vẫn ngồi ghế và vẫn ăn suất ăn – đo trên mẫu SIN/MAL, 22 người của hai đại
lý SGS và VV ngồi cùng chuyến mà toàn bộ chi phí chỉ chia cho 9 khách của Vietourist.

Từ đây mỗi dòng chi phải MANG theo quy tắc của nó (cột quy_tac_phan_bo), và máy chia. Khi ai hỏi
"vì sao khách này chịu 15.750 mà khách kia không chịu", có câu trả lời tra được, thay vì phải mở lại
tệp Excel gốc.
"""
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, Booking
from app.models.lop3_tour import BookingKhach
from app.models.vietrip import TourCostLine
from app.services import rules as R

# Năm quy tắc phân bổ. Khoá đi vào cột tour_cost_lines.quy_tac_phan_bo.
BANG_PHAN_BO = {
    "deu_moi_khach": "Chia đều cho MỌI khách, kể cả khách miễn phí",
    "deu_khach_co_thu": "Chia đều cho khách CÓ THU tiền (bỏ khách miễn phí)",
    "theo_doi_tuong": "Chia trong bậc tuổi của chính dòng ấy (người lớn / trẻ em / em bé)",
    "theo_ty_le_doanh_thu": "Chia theo tỷ lệ tiền từng khách đã trả",
    "khong_phan_bo": "Không chia cho khách nào – chi phí chung của chuyến",
}


# ---------------------------------------------------------------------------------------------
# Tuổi và loại khách
# ---------------------------------------------------------------------------------------------

def tuoi_tai(ngay_sinh: date | None, moc: date | None) -> int | None:
    """Tuổi tròn tại một mốc ngày. None khi thiếu một trong hai – không đoán."""
    if not ngay_sinh or not moc:
        return None
    t = moc.year - ngay_sinh.year
    if (moc.month, moc.day) < (ngay_sinh.month, ngay_sinh.day):
        t -= 1
    return max(t, 0)


def xep_loai(db: Session, ngay_sinh: date | None, ngay_di: date | None) -> tuple[str | None, int | None]:
    """(loai_tuoi, tuoi) tại ngày khởi hành. (None, None) khi chưa có ngày sinh."""
    t = tuoi_tai(ngay_sinh, ngay_di)
    if t is None:
        return None, None
    if t < int(R.get_param(db, "tuoi_em_be", ngay_di)):
        return "em_be", t
    if t < int(R.get_param(db, "tuoi_tre_em", ngay_di)):
        return "tre_em", t
    return "nguoi_lon", t


def gia_chuan(db: Session, loai: str | None, gia_nguoi_lon: float | None,
              ngay_di: date | None, hinh_thuc: str | None = None) -> float | None:
    """Giá đúng quy tắc cho một bậc tuổi. None khi thiếu bậc tuổi, giá gốc, hoặc HÌNH THỨC tour.

    Hình thức quyết định tỷ lệ, nên thiếu nó thì KHÔNG đoán: đoán nhầm một tour nước ngoài thành
    tour trong nước là hạ giá em bé từ 30% xuống 10%, tức bán rẻ hơn hai phần ba mà không ai bấm
    nút nào. Trả None và để tờ quyết toán kêu lên thì sửa được; đoán thì không.
    """
    if loai is None or gia_nguoi_lon is None:
        return None
    if loai == "nguoi_lon":
        return float(gia_nguoi_lon)
    if hinh_thuc not in ("trong_nuoc", "nuoc_ngoai"):
        return None
    khoa = f"ty_le_{'em_be' if loai == 'em_be' else 'tre_em'}_{hinh_thuc}"
    return round(gia_nguoi_lon * R.get_param(db, khoa, ngay_di), 2)


def xac_dinh_khach(db: Session, kh: BookingKhach, ngay_di: date | None,
                   gia_nguoi_lon: float | None, hinh_thuc: str | None = None) -> BookingKhach:
    """Xếp loại và tính giá chuẩn cho một dòng khách, GHI LẠI vào bản ghi.

    Ghi lại chứ không tính khi đọc: xem docstring đầu tệp. Hàm này không commit – người gọi commit,
    vì một booking có nhiều khách và chúng phải vào sổ cùng lúc.
    """
    kh.loai_tuoi, kh.tuoi_luc_di = xep_loai(db, kh.ngay_sinh, ngay_di)
    kh.gia_chuan = gia_chuan(db, kh.loai_tuoi, gia_nguoi_lon, ngay_di, hinh_thuc)
    return kh


def soat_gia(db: Session, tour_id: int) -> dict:
    """Soát giá bán từng khách của một chuyến so với quy tắc.

    KHÔNG sửa số nào. Bán khác quy tắc không phải lỗi – bán cao hơn quy tắc là chuyện tốt, bán thấp
    hơn có thể là khuyến mãi đã duyệt. Việc của hàm này là làm cho nó LỘ RA.
    """
    t = db.get(Tour, tour_id)
    khach = list(db.scalars(select(BookingKhach).where(BookingKhach.tour_id == tour_id)))
    thieu_ngay_sinh = [k for k in khach if k.ngay_sinh is None]
    # Chưa xếp hình thức thì không có tỷ lệ nào áp được cho trẻ em và em bé – nói ra chứ không lặng lẽ
    # bỏ qua, vì im lặng ở đây trông y hệt "mọi khách đều bán đúng chuẩn".
    chua_hinh_thuc = (t is not None and t.hinh_thuc not in ("trong_nuoc", "nuoc_ngoai")
                      and any(k.loai_tuoi in ("tre_em", "em_be") for k in khach))
    lech = []
    for k in khach:
        d = k.lech_chuan()
        # Dưới 1.000 đ là phần lẻ của phép nhân tỷ lệ, không phải chênh lệch giá.
        if d is not None and abs(d) >= 1000:
            lech.append({
                "khach_id": k.id, "ho_ten": k.ho_ten, "loai_tuoi": k.loai_tuoi,
                "nhom_khach": k.nhom_khach,
                "tuoi": k.tuoi_luc_di, "gia_chuan": k.gia_chuan, "gia_ban": k.gia_ban,
                "lech": d, "ly_do": k.ly_do_khac_chuan or "",
            })
    return {
        "tour_id": tour_id,
        "ngay_di": t.start_date if t else None,
        "so_khach": len(khach),
        "so_thieu_ngay_sinh": len(thieu_ngay_sinh),
        # Câu này đi thẳng lên màn hình. Nói rõ hệ quả, không chỉ nói con số.
        "canh_bao_ngay_sinh": (
            f"{len(thieu_ngay_sinh)} khách chưa có ngày sinh – quy tắc giá theo tuổi không kiểm được "
            f"cho những khách này" if thieu_ngay_sinh else ""),
        "hinh_thuc": t.hinh_thuc if t else None,
        "canh_bao_hinh_thuc": (
            "Chuyến chưa xếp hình thức trong nước / nước ngoài – không tính được giá chuẩn cho trẻ em "
            "và em bé, vì hai hình thức dùng hai tỷ lệ khác nhau" if chua_hinh_thuc else ""),
        "so_lech_gia": len(lech),
        "tong_lech_gia": round(sum(x["lech"] for x in lech), 2) if lech else 0,
        "lech": lech,
    }


# ---------------------------------------------------------------------------------------------
# Phân bổ chi phí cho từng khách
# ---------------------------------------------------------------------------------------------

def _mau_so(quy_tac: str, doi_tuong: str | None, khach: list[BookingKhach]) -> list[BookingKhach]:
    """Những khách CHỊU một dòng chi phí, theo quy tắc của chính dòng ấy."""
    if quy_tac == "deu_moi_khach":
        return khach
    if quy_tac == "deu_khach_co_thu":
        return [k for k in khach if k.co_thu()]
    if quy_tac == "theo_doi_tuong":
        if doi_tuong in (None, "", "chung"):
            return khach
        return [k for k in khach if k.loai_tuoi == doi_tuong]
    return []


def phan_bo(db: Session, tour_id: int) -> dict:
    """Chia chi phí của chuyến về từng khách, theo quy tắc khai trên từng dòng chi.

    Trả về giá vốn từng khách CÙNG VỚI lời giải thích nó gồm những gì. Đây là chỗ khác hẳn tệp Excel:
    trong tệp, cột LAND chỉ là một con số và mẫu số của phép chia không nằm ở đâu cả.

    Dòng nào chưa khai quy tắc thì KHÔNG chia và KHÔNG đoán – nó vào 'chua_khai_quy_tac', và tổng
    cộng lại sẽ không khớp giá vốn của chuyến. Chỗ không khớp ấy là việc phải làm, không phải chỗ để
    máy tự lấp.
    """
    khach = list(db.scalars(
        select(BookingKhach).where(BookingKhach.tour_id == tour_id).order_by(BookingKhach.stt, BookingKhach.id)))
    dong = list(db.scalars(
        select(TourCostLine).where(TourCostLine.tour_id == tour_id, TourCostLine.status == "hd")))

    chia: dict[int, list[dict]] = {k.id: [] for k in khach}
    chua_khai: list[dict] = []
    khong_chia: list[dict] = []

    for d in dong:
        tien = d.actual if d.actual is not None else d.budget
        if tien is None:
            continue
        qt = d.quy_tac_phan_bo or ""
        if not qt:
            chua_khai.append({"dong_id": d.id, "noi_dung": d.description, "so_tien": float(tien)})
            continue
        if qt == "khong_phan_bo":
            khong_chia.append({"dong_id": d.id, "noi_dung": d.description, "so_tien": float(tien)})
            continue
        if qt == "theo_ty_le_doanh_thu":
            tong = sum(float(k.gia_ban or 0) for k in khach)
            if tong <= 0:
                chua_khai.append({"dong_id": d.id, "noi_dung": d.description,
                                  "so_tien": float(tien),
                                  "vi_sao": "chia theo tỷ lệ doanh thu nhưng chuyến chưa có doanh thu"})
                continue
            for k in khach:
                p = float(tien) * float(k.gia_ban or 0) / tong
                if p:
                    chia[k.id].append({"noi_dung": d.description, "so_tien": round(p, 2),
                                       "quy_tac": qt})
            continue
        chiu = _mau_so(qt, d.doi_tuong, khach)
        if not chiu:
            chua_khai.append({"dong_id": d.id, "noi_dung": d.description, "so_tien": float(tien),
                              "vi_sao": f"quy tắc '{qt}' không chọn ra khách nào"})
            continue
        moi = float(tien) / len(chiu)
        for k in chiu:
            chia[k.id].append({"noi_dung": d.description, "so_tien": round(moi, 2),
                               "quy_tac": qt, "mau_so": len(chiu)})

    dong_khach = []
    for k in khach:
        gv = round(sum(x["so_tien"] for x in chia[k.id]), 2)
        thu = float(k.gia_ban or 0)
        dong_khach.append({
            "khach_id": k.id, "stt": k.stt, "ho_ten": k.ho_ten,
            "loai_tuoi": k.loai_tuoi, "nhom_khach": k.nhom_khach, "tuoi": k.tuoi_luc_di,
            "thu": thu, "gia_von": gv, "loi_nhuan": round(thu - gv, 2),
            "gom": chia[k.id],
        })

    da_chia = round(sum(x["gia_von"] for x in dong_khach), 2)
    return {
        "tour_id": tour_id,
        "so_khach": len(khach),
        "dong": dong_khach,
        "tong_thu": round(sum(x["thu"] for x in dong_khach), 2),
        "tong_da_phan_bo": da_chia,
        "khong_phan_bo": khong_chia,
        "tong_khong_phan_bo": round(sum(x["so_tien"] for x in khong_chia), 2),
        "chua_khai_quy_tac": chua_khai,
        "tong_chua_khai": round(sum(x["so_tien"] for x in chua_khai), 2),
    }
