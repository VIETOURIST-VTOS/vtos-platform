# -*- coding: utf-8 -*-
"""Đ-6 · Tiền tip — dòng tiền không phải doanh thu, cũng không phải giá vốn.

CHỦ TỊCH CHỐT 12/9/2026: "tiền tip tour châu Âu chia 1 phần với công ty."

Nguyên tắc đã chốt. TỶ LỆ THÌ CHƯA — và tệp này cố ý TỪ CHỐI chạy cho tới khi có người ký tỷ lệ.

--------------------------------------------------------------------------------------------------
TIỀN TIP ĐI NHƯ THẾ NÀO, ĐO TRÊN TỆP THẬT
--------------------------------------------------------------------------------------------------

Tệp QUYẾT TOÁN CHÂU ÂU 6 NƯỚC 27.05–04.06/2026, sheet QT, ba dòng cuối bảng:

    Tiền tip thu từ TL          + 24.705.000     = 27 € × 30 khách × 30.500 đ/€
    Tiền tip hoàn cho JTRAVEL   −  2.470.500     = 27 € ×  3 khách × 30.500
    Tiền tip hoàn cho VTOURIST  −  4.117.500     = 27 € ×  5 khách × 30.500
    ------------------------------------------------------------------------
    còn lại cộng vào lợi nhuận đoàn   18.117.000

Và sheet QUYẾT TOÁN TL cùng tệp cho thấy chiều còn lại: trưởng đoàn nộp công ty 810 € tiền tip, rồi
trừ đi công tác phí 270 €, city tax Milan 120 €, nhà hàng REGINA 480 € — còn −60 €, tức TL nộp lại.

Ba điều đọc ra từ đó:

  1. Tiền tip là TIỀN CỦA KHÁCH trả cho hướng dẫn viên, công ty đang GIỮ HỘ. Cho tới lúc chia, nó
     không phải doanh thu của công ty và cũng không phải chi phí.
  2. Phần công ty giữ lại SAU KHI CHIA mới là doanh thu. Phần của trưởng đoàn là khoản PHẢI TRẢ cho
     trưởng đoàn — nó đi vào bản chốt công nợ TL (Đ-9), không đi vào bảng lãi lỗ.
  3. Khách của ĐẠI LÝ thì phần tip ấy hoàn về đại lý, không chia với ai cả.

CHỦ TỊCH CHỐT THÊM 12/9/2026 — CÁCH GHI NHẬN: phần công ty giữ lại là DOANH THU KHÁC của chuyến,
ghi bằng dòng `TourDoanhThuDong` loại `tip_cong_ty`. Không phải khoản giảm chi phí trưởng đoàn, và
không treo chờ quyết. Hai cách kia cho ra cùng một con số lợi nhuận nhưng khác chỗ đứng trên báo
cáo, nên phải chốt một — và đã chốt.

--------------------------------------------------------------------------------------------------
TỶ LỆ CHIA: Ô CHO ĐIỀU HÀNH NHẬP (Chủ tịch chốt 12/9/2026)
--------------------------------------------------------------------------------------------------

    "tỷ lệ chia tiền tip em cài phép toán và form sẵn cho điều hành tự nhập % vào ô đó"

Nên tỷ lệ là một Ô TRÊN TỪNG CHUYẾN, không phải một hằng số của cả công ty. Hợp với thực tế: mỗi
đoàn một hợp đồng với trưởng đoàn, và đoàn châu Âu chín ngày khác đoàn Nha Trang ba ngày.

Thứ tự lấy số:  ô người Điều hành gõ  →  tham số công ty (nếu đã ký)  →  RỖNG, phép chia dừng.

Vẫn giữ tham số ở giữa vì một chuyến bỏ trống ô ấy thì phải có chỗ lùi về, và lùi về một con số ĐÃ
KÝ tốt hơn lùi về một con số mã tự đoán. Máy KHÔNG BAO GIỜ tự điền: không có cả hai thì hệ thống nói
"đã thu 24.705.000 đ, chưa chia được vì chưa có tỷ lệ" — một câu đúng — thay vì một con số bịa.

MỘT ĐIỀU PHẢI GHI VÀO SỔ, không phải để cản ai: tỷ lệ này chia tiền giữa công ty và người lao động.
Khi nó là một ô gõ tay trên từng chuyến thì AI GÕ và GÕ LÚC NÀO phải vào sổ dấu vết — `sua_sau_ky`
đã có sẵn cơ chế ấy. Một ô đổi được mà không ai biết ai đổi là chỗ mà sáu tháng sau không ai trả lời
được câu "vì sao đoàn này công ty lấy 40% còn đoàn kia lấy 70%".

--------------------------------------------------------------------------------------------------
PHẦN CÒN NỢ, ĐÃ GHI RÕ ĐỂ LÀN SAU KHÔNG PHẢI ĐOÁN
--------------------------------------------------------------------------------------------------

HOÀN TIP CHO ĐẠI LÝ chưa làm được ở bản này, vì nó cần biết khách nào thuộc bên bán nào — đó là
Đ-4 (`tour_ben_ban`), chưa dựng. `hoan_cho_ben_ban()` dưới đây nhận sẵn danh sách số khách theo bên
để khi Đ-4 xong thì chỉ việc nối vào, KHÔNG phải viết lại phép chia.

Bản này CỐ Ý không tự suy số khách của đại lý từ `booking_khach.nhom_khach == "dai_ly"`: nhãn ấy nói
khách thuộc đại lý nào đó, không nói thuộc đại lý NÀO. Hoàn nhầm tiền cho sai đại lý là sai kiểu
không ai phát hiện — vì tổng hoàn vẫn đúng.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.services.lam_tron_tien import lam_tron
from app.services.rules import get_param_text

KHOA_TY_LE = "ty_le_tip_cong_ty"

# Lý do trả về khi không chia được. Mỗi lý do là một câu nói được với người dùng, không phải một mã.
CHUA_CHIA = {
    "chua_co_ty_le": "Chưa có tỷ lệ chia tiền tip – Điều hành nhập % vào ô «Phần công ty» trên biểu "
                     "quyết toán, hoặc ký tham số ty_le_tip_cong_ty làm mức mặc định cho mọi chuyến.",
    "chua_co_tip": "Chuyến chưa khai tiền tip.",
}


def _so(x) -> float | None:
    if x is None or str(x).strip() == "":
        return None
    try:
        return float(str(x).strip().rstrip("%").replace(",", "."))
    except (TypeError, ValueError):
        return None


def doc_phan_tram(x) -> float | None:
    """Đọc ô % TRÊN BIỂU NHẬP. Luôn là phần trăm: gõ 40 nghĩa là 40%.

    BẢN NHÁP ĐẦU CỦA HÀM NÀY NHẬN CẢ HAI CÁCH VIẾT — `0.4` và `40` — bằng một luật ngầm "lớn hơn 1
    thì chia 100". Đó là một cái bẫy tự đặt ra:

        gõ 1    → 100%  hay 1%?
        gõ 0.4  → 0,4%  hay 40%?

    Cả hai đều đọc xuôi tai, và số tiền chênh nhau HÀNG TRĂM LẦN. Một ngưỡng phép màu đặt giữa hai
    cách viết là chỗ chắc chắn có ngày chia sai mà không ai biết vì sao.

    Nên bỏ hẳn luật ngầm: ô trên biểu là PHẦN TRĂM, không có ngoại lệ. Tham số hệ thống là SỐ THẬP
    PHÂN, đọc bằng hàm khác. Hai cách viết, hai cửa, không đoán.

    Ngoài khoảng [0, 100] là số hỏng: trả None để phép chia DỪNG, thay vì chia ra một phần âm hoặc
    một phần lớn hơn cả số tiền có thật.
    """
    v = _so(x)
    if v is None or v < 0 or v > 100:
        return None
    return v / 100.0


def doc_ty_le_tham_so(x) -> float | None:
    """Đọc tham số hệ thống. Luôn là số thập phân: `0.4` nghĩa là 40%."""
    v = _so(x)
    if v is None or v < 0 or v > 1:
        return None
    return v


def canh_bao_phan_tram(x) -> str:
    """Người gõ 0,4 vào ô có nhãn % thì hệ thống đọc đúng 0,4% — và rất có thể họ định gõ 40%.

    Không tự sửa số của người ta. Nhưng cũng không im: nói ra để họ nhìn lại.
    """
    v = _so(x)
    if v is not None and 0 < v < 1:
        return (f"Ô này là PHẦN TRĂM: gõ {v} nghĩa là {v}% – công ty chỉ lấy {v} phần trăm tiền tip. "
                f"Nếu định {v * 100:g}% thì gõ {v * 100:g}.")
    return ""


def ty_le_cong_ty(db: Session, hom_nay: date | None = None,
                  ty_le_chuyen=None) -> float | None:
    """Tỷ lệ phần tip thuộc công ty.

    CHỦ TỊCH CHỐT 12/9/2026: "tỷ lệ chia tiền tip em cài phép toán và form sẵn cho Điều hành tự nhập
    % vào ô đó." Nên thứ tự là:

        1. Ô người Điều hành gõ trên chính chuyến ấy      ← ưu tiên
        2. Tham số công ty đang hiệu lực (nếu đã ký)      ← mức dự phòng
        3. RỖNG – phép chia từ chối chạy

    Vì sao vẫn giữ bước 2 dù Chủ tịch đã cho nhập tay: một chuyến bỏ trống ô ấy thì phải có chỗ lùi
    về, và lùi về một con số ĐÃ KÝ thì tốt hơn lùi về một con số mã tự đoán. Khi tham số có giá trị,
    biểu nhập điền sẵn nó vào ô — người Điều hành vẫn sửa được, nhưng mặc định không phải số trống.

    Và vì tỷ lệ nay do người gõ trên từng chuyến, AI GÕ và GÕ LÚC NÀO phải vào sổ dấu vết — đây là
    một quyết định chia tiền giữa công ty và người lao động, không phải một ô ghi chú.
    """
    tren_chuyen = doc_phan_tram(ty_le_chuyen)
    if tren_chuyen is not None:
        return tren_chuyen
    return doc_ty_le_tham_so(get_param_text(db, KHOA_TY_LE, hom_nay))


def chia(tong_tip: float | None, ty_le: float | None) -> dict:
    """Chia một khoản tip thành phần công ty và phần trưởng đoàn.

    PHẦN TRƯỞNG ĐOÀN = TỔNG − PHẦN CÔNG TY, cố ý không tính bằng `tong × (1 − tỷ lệ)`.

    Làm tròn hai phía độc lập nhau thì hai phần cộng lại lệch tổng một đồng, và một đồng lệch trên
    bảng chia tiền là chỗ người ta ngồi dò cả buổi mà không tìm ra vì không phía nào sai. Lấy phần
    còn lại làm phần thứ hai thì tổng LUÔN khớp, bất kể tỷ lệ lẻ đến đâu.
    """
    if tong_tip is None or ty_le is None:
        return {"tong": lam_tron(tong_tip), "cong_ty": None, "truong_doan": None}
    tong = lam_tron(tong_tip)
    phan_cty = lam_tron(float(tong_tip) * ty_le)
    return {"tong": tong, "cong_ty": phan_cty, "truong_doan": tong - phan_cty}


# ĐƠN VỊ CỦA ĐƠN GIÁ TIP — bắt buộc khai, KHÔNG có mặc định.
#
# Bản nháp đầu ngày 12/9 chỉ có một tham số `don_gia_ngay` và luôn nhân với số ngày. Làn rà soát
# (Codex) bắt được: chính tệp EU 6 nước ghi CẢ HAI đơn vị cho cùng một khoản tiền —
#
#     sheet QT             T56 = 27 × 30 × 30.500        → 27 €/khách/CHUYẾN
#     sheet QUYẾT TOÁN TL  D11 = 3 × 9 × 30, ghi chú "3E/PAX/DAY X 9DAY X 30PAX"
#                                                        → 3 €/khách/NGÀY, 9 ngày
#
# Hai cách viết ra cùng 810 €. Nhưng nếu người nhập gõ 27 vào một ô có nhãn "đơn giá mỗi ngày" rồi
# hệ thống nhân tiếp 9 ngày, số tiền ra 7.290 € — GẤP CHÍN LẦN, và nó vẫn trông như một con số hợp
# lệ. Tiền tip là tiền của khách; nhân nhầm chín lần ở đây là chia sai chín lần cho người thật.
#
# Nên đơn vị là một ô BẮT BUỘC. Không khai thì phép tính dừng, không đoán.
DON_VI_TIP = {
    "moi_khach_moi_ngay": "mỗi khách mỗi NGÀY – nhân với số ngày",
    "moi_khach_ca_chuyen": "mỗi khách CẢ CHUYẾN – KHÔNG nhân số ngày",
}


def tien_tip_thu(don_gia: float | None, don_vi: str | None, so_khach: int | None,
                 so_ngay: int | None = None, ty_gia: float | None = None) -> float | None:
    """Tổng tip thu được, quy đổi nếu là ngoại tệ.

    Thiếu BẤT KỲ thành phần nào thì trả None — kể cả `don_vi`. Coi thiếu bằng 0 là ra một con số nhỏ
    hơn sự thật mà trông vẫn như một con số: đúng chiều làm người đọc yên tâm, tức chiều nguy hiểm.
    """
    if don_gia is None or so_khach is None or don_vi not in DON_VI_TIP:
        return None
    tien = float(don_gia) * int(so_khach)
    if don_vi == "moi_khach_moi_ngay":
        if so_ngay is None:
            return None
        tien *= int(so_ngay)
    if ty_gia is not None:
        tien *= float(ty_gia)
    return tien


def tinh(db: Session, *, don_gia: float | None, don_vi: str | None, so_khach: int | None,
         so_ngay: int | None = None, ty_gia: float | None = None, ty_le_chuyen=None,
         hom_nay: date | None = None) -> dict:
    """Bản chia tip của một chuyến.

    Luôn trả về con số TỔNG nếu tính được, kể cả khi chưa chia được – vì "đã thu bao nhiêu" là câu
    trả lời được ngay, còn "chia thế nào" mới là câu còn chờ người điền.
    """
    tong = tien_tip_thu(don_gia, don_vi, so_khach, so_ngay, ty_gia)
    tl = ty_le_cong_ty(db, hom_nay, ty_le_chuyen)
    kq = chia(tong, tl)
    kq["ty_le_cong_ty"] = tl
    kq["ty_le_phan_tram"] = None if tl is None else round(tl * 100, 4)
    kq["nguon_ty_le"] = ("go_tren_chuyen" if doc_phan_tram(ty_le_chuyen) is not None
                         else ("tham_so" if tl is not None else ""))
    kq["canh_bao"] = [c for c in (canh_bao_phan_tram(ty_le_chuyen),) if c]
    if tong is None:
        kq["chua_chia"], kq["vi_sao"] = "chua_co_tip", CHUA_CHIA["chua_co_tip"]
    elif tl is None:
        kq["chua_chia"], kq["vi_sao"] = "chua_co_ty_le", CHUA_CHIA["chua_co_ty_le"]
    else:
        kq["chua_chia"], kq["vi_sao"] = "", ""
    return kq


def hoan_cho_ben_ban(don_gia: float | None, don_vi: str | None, so_ngay: int | None,
                     khach_theo_ben: dict[str, int], ty_gia: float | None = None) -> dict:
    """Tiền tip hoàn về từng bên bán — đúng hai dòng «Tiền tip hoàn cho JTV / VTR» của tệp EU.

    `khach_theo_ben` là `{tên bên: số khách}`. Khi Đ-4 (`tour_ben_ban`) xong thì dict ấy lấy từ bảng;
    tới lúc đó đây vẫn là phép chia duy nhất, không phải viết lại.

    Trả về số DƯƠNG cho từng bên. Ghi vào sổ doanh thu thì là dòng ÂM và bắt buộc khai số chứng từ —
    cơ chế ấy đã có sẵn ở `TourDoanhThuDong` và không được đi vòng qua.
    """
    if don_gia is None or don_vi not in DON_VI_TIP:
        return {}
    return {ben: tien_tip_thu(don_gia, don_vi, sk, so_ngay, ty_gia)
            for ben, sk in khach_theo_ben.items() if sk}
