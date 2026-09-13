# -*- coding: utf-8 -*-
"""CỬA TẠO CHUYẾN cho kho quyết toán cũ T1–T6/2026 – bộ nạp thứ hai, đứng TRƯỚC cửa nạp quyết toán.

VÌ SAO PHẢI CÓ CỬA NÀY

Chủ tịch duyệt cấu trúc 13/9/2026 và giao nạp kho cũ để hệ thống chạy trên số thật nửa năm. Đo ngay
sau đó thì lộ ra chỗ tắc:

    VTOS có 1.150 chuyến, nhưng chỉ 47 / 436 mã của kho khớp được. Thiếu 389.
    Chuyến trong VTOS theo tháng khởi hành: T1 = 0 · T2 = 1 · T3 = 1 · T4 = 2 · T5 = 5 · T6 = 279.

Bản nạp Vietrip chỉ mang về từ tháng 6. Cửa nạp quyết toán (`intake_kho_cu`) chặn cứng đúng ở đấy –
*"không có chuyến mang mã ấy trong VTOS"* – và cái tick bỏ-qua-cảnh-báo cố ý không cứu được nó.

VÀ VÌ SAO NÓ LÀ MỘT CỬA RIÊNG, KHÔNG GỘP VÀO CỬA KIA

Gộp thì tiện hơn: một lần bấm, vừa tạo chuyến vừa nạp quyết toán. Nhưng tạo chuyến là GHI LẠI LỊCH
SỬ VẬN HÀNH của công ty – mấy trăm dòng trong danh sách tour, mỗi dòng là một chuyến có thật với
ngày, khách và tiền. Biến nó thành hệ quả phụ của việc đọc tệp thì một lần bấm nhầm đẻ ra vài trăm
chuyến mà không ai kịp nhìn, và gỡ ra thì phải gỡ cả phần quyết toán đã treo lên chúng.

Hai cửa, hai lần bấm, hai dòng nhật ký. Thứ tự bắt buộc: TẠO CHUYẾN trước, NẠP QUYẾT TOÁN sau.

BỐN QUY ƯỚC, VÀ VÌ SAO TỪNG CÁI

1. NGƯỜI ĐIỀU HÀNH = tài khoản hệ thống, đọc từ tham số `kho_cu_tai_khoan_dieu_hanh`.

   Ô `operator_id` quyết định THƯỞNG CHUYẾN thuộc về ai. Gán bừa một nhân viên vào mấy trăm chuyến
   lịch sử là đụng vào tiền của người thật. Mặc định là `dieuhanhvietrip` – tài khoản đang KHOÁ, và
   đang là điều hành của 1.145 chuyến nạp từ Vietrip, nên kho cũ đi cùng một đường với bản nạp trước
   nó. Điều hành gán lại từng chuyến cho đúng người là việc sau.

2. TRẠNG THÁI = `ket_thuc` ("Đã kết thúc – chờ quyết toán").

   Đúng nghĩa đen: chuyến đã chạy xong, quyết toán đang được nạp vào. KHÔNG đặt `khoa` – khoá nghĩa
   là CNTT đã đối chiếu độc lập, mà chưa ai đối chiếu. 788 chuyến Vietrip cũng đang ở `ket_thuc`.

3. `hinh_thuc` (trong nước / nước ngoài) ĐỂ RỖNG.

   Đây là ô quyết định PHÉP TÍNH: tour nước ngoài bắt buộc khai tỷ giá và ngày tỷ giá cho mọi khoản
   ngoại tệ, giá trẻ em soát theo tỷ lệ khác. Suy ngầm rồi tính tiền theo cái suy ấy là chỗ sinh lỗi
   lặng – đúng lời chú thích ở chính cột ấy. Để rỗng thì biểu quyết toán hỏi người khai, y như mọi
   chuyến khác.

4. `tour_type` máy đặt, và CHẤP NHẬN ĐƯỢC vì nó chỉ là cái NHÃN.

   Đoàn hay lẻ: đọc từ 'MICE'/'ĐOÀN' trong mã hoặc tên tệp. Nội địa hay nước ngoài: chỉ nhận khi tệp
   CÓ bảng chi bằng ngoại tệ – tức là bằng chứng trong số liệu, không phải đoán từ cái tên.

   Tín hiệu ấy THIẾU, và biết là thiếu: nhiều tour nước ngoài mua land bằng VND của đại lý trong
   nước nên không có bảng ngoại tệ nào ("QUYẾT TOÁN MONO SIN 30.06.2026" bị xếp nội địa). Chấp nhận
   được vì `tour_type` không đi vào một phép tính nào – thứ đi vào phép tính là `hinh_thuc`, và nó
   đang để rỗng cho người khai. Nhãn sai thì sửa một ô; con số sai thì không ai biết mà sửa.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime

from app.services import nap_kho_cu as KHO
from app.services import tao_chuyen_kho_cu as TC

# Cùng nguồn với cửa nạp quyết toán: gỡ lại thì gỡ được cả hai bằng một khoá.
NGUON = TC.NGUON

# Tham số giữ tài khoản điều hành nhận cả lô. Để ở tham số chứ không viết cứng: đổi người nhận là
# đổi một dòng ở màn hình tham số, không phải sửa mã và đẩy một bản nâng cấp.
KHOA_TAI_KHOAN = "kho_cu_tai_khoan_dieu_hanh"
TAI_KHOAN_MAC_DINH = "dieuhanhvietrip"

TRANG_THAI = "ket_thuc"


def _kd(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").upper()


def loai_chuyen(d: dict) -> str:
    """tour_type – xem quy ước 4 ở đầu tệp. Chỉ là nhãn, không đi vào phép tính nào."""
    t = _kd((d.get("ten_tep") or d.get("_tep") or "")) + " " + _kd(d.get("ma_tour") or "")
    doan = "MICE" in t or "DOAN" in t
    ngoai = bool(d.get("ngoai_te"))
    return ("doan_" if doan else "le_") + ("nuoc_ngoai" if ngoai else "noi_dia")


def doc_tep_lo(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    """Một tệp = một dòng. Dùng ĐÚNG bộ đọc của cửa nạp quyết toán – không viết bộ đọc thứ hai.

    Hai cửa đọc bằng hai bộ đọc khác nhau thì sớm muộn chúng đọc ra hai mã khác nhau từ cùng một
    tệp, và lúc ấy chuyến được tạo mang mã A còn quyết toán đi tìm mã B.
    """
    return [KHO.doc_tep(noi_dung, ten_tep)]


def _ma_da_co(db) -> set[str]:
    from sqlalchemy import select

    from app.models.core import Tour
    return {(c or "").strip().upper() for c in db.scalars(select(Tour.code))}


def kiem_lo(db, rows: list[dict]) -> dict:
    """CỬA SOÁT – KHÔNG ghi một dòng nào. Trả về đúng thứ người duyệt cần nhìn trước khi quyết."""
    b = TC.bang(rows, _ma_da_co(db))
    may_dat = sum(1 for h in b["hang"] if h["viec"] == "tao_moi" and h["ma_la_may_dat"])
    vo_cu = sum(1 for h in b["hang"] if h.get("vo_mau_cu"))

    # HAI TỆP CÙNG MỘT MÃ THẬT thì chỉ tạo được MỘT chuyến – `tours.code` là cột duy nhất. Phải trừ
    # ra ngay ở bảng xem trước, không để phần ghi tự âm thầm bớt đi: bảng xem trước nói "sẽ tạo 81"
    # rồi ghi ra 80 là một bảng xem trước nói dối, và lần sau không ai tin nó nữa.
    #
    # KHÔNG tự tách chúng thành hai mã: hai tệp cùng mã thường là hai phần của MỘT chuyến (bảng
    # chính và bảng land, hoặc hai đợt khách), gộp vào một chuyến mới là đúng. Tách ra mới là bịa.
    da_thay: set[str] = set()
    trung_lo = 0
    for h in b["hang"]:
        if h["viec"] != "tao_moi":
            continue
        k = (h["ma"] or "").upper()
        if k in da_thay:
            h["trung_trong_lo"] = True
            trung_lo += 1
        da_thay.add(k)
    tao_that = b["tao_moi"] - trung_lo
    return {
        "so_dong": b["tong_tep"],
        # Ánh xạ sang ngôn ngữ của khung nạp:
        "da_nap": tao_that,                           # sẽ TẠO nếu bấm bây giờ
        "da_co": b["da_co"],                          # đã có chuyến – bỏ qua
        "dong_loi": b["bo_qua"] + b["thieu_ngay"],    # không tạo được
        "dem": {"tao_moi": tao_that, "trung_trong_lo": trung_lo, "da_co": b["da_co"],
                "khong_phai_chuyen": b["bo_qua"], "thieu_ngay": b["thieu_ngay"],
                "ma_may_dat": may_dat, "vo_mau_cu": vo_cu},
        "bo_qua_theo_loai": b["bo_qua_theo_loai"],
        "ma_trung_nhau": b["ma_trung_nhau"],
        "chi_tiet": b["hang"],
        "ghi_chu": (
            f"XEM TRƯỚC – chưa ghi gì. Sẽ TẠO {tao_that} chuyến · {b['da_co']} chuyến đã có · "
            f"{trung_lo} tệp dùng chung mã với tệp khác trong lô (gộp vào cùng một chuyến) · "
            f"{b['bo_qua']} tệp KHÔNG PHẢI một chuyến (visa/ghép lẻ/dịch vụ lẻ theo tháng, land của "
            f"đối tác) · {b['thieu_ngay']} tệp thiếu ngày nên không tạo được. "
            f"{may_dat} chuyến mang mã do MÁY đặt (tiền tố {TC.TIEN_TO_TAM}) – Điều hành sửa dần. "
            f"Ô 'hình thức' để RỖNG: biểu quyết toán sẽ hỏi người khai, vì đó là ô quyết định phép "
            f"tính. Tạo chuyến xong mới nạp được quyết toán."),
    }


def _tai_khoan_dieu_hanh(db):
    """Tài khoản nhận cả lô. Không có thì DỪNG – không lấy bừa một người đang làm việc."""
    from sqlalchemy import select

    from app.models.core import User
    from app.services import rules as R

    ten = TAI_KHOAN_MAC_DINH
    try:
        ten = (R.get_param_text(db, KHOA_TAI_KHOAN) or TAI_KHOAN_MAC_DINH).strip()
    except Exception:      # noqa – chưa có tham số thì dùng mặc định
        pass
    return db.scalars(select(User).where(User.username == ten)).first(), ten


def nap_lo(db, rows: list[dict], boi: str, ten_tep: str = "",
           bo_qua_dong_loi: bool = False) -> dict:
    """CỬA GHI. Tạo chuyến cho những dòng xếp là `tao_moi`, không đụng gì khác.

    KHÔNG ghi doanh thu, giá vốn, dự toán hay hình thức. Chuyến tạo ra là một cái KHUNG RỖNG có mã,
    tên, ngày và số khách – đủ để cửa nạp quyết toán có chỗ treo dòng vào. Mọi con số tiền đi qua
    cửa kia, và cửa kia cũng không ghi tiền mức chuyến (xem `intake_kho_cu`).

    `bo_qua_dong_loi` ở đây KHÔNG nới gì cả, và cố ý thế: tệp không phải một chuyến thì không có
    cách nào biến thành chuyến, tệp thiếu ngày thì không có ngày để điền. Không có lối tắt nào cho
    hai thứ đó – phải sửa tệp hoặc để người điền.
    """
    from app.models.core import Tour

    kq = kiem_lo(db, rows)
    nguoi, ten_tk = _tai_khoan_dieu_hanh(db)
    if nguoi is None:
        return {**kq, "da_nap": 0, "da_tao": 0,
                "message": (f"KHÔNG tạo gì cả: không tìm thấy tài khoản {ten_tk!r} để làm điều hành "
                            f"của lô này. Đặt tham số {KHOA_TAI_KHOAN} về một tài khoản có thật.")}

    da_co = _ma_da_co(db)
    tao, bo = [], []
    for h in kq["chi_tiet"]:
        if h["viec"] != "tao_moi":
            continue
        # Kiểm lại NGAY TRƯỚC KHI GHI, không tin bảng xem trước: giữa lúc xem và lúc bấm có thể có
        # người vừa tạo đúng chuyến ấy, và `tours.code` là cột duy nhất – ghi vào là nổ cả lô.
        if h.get("trung_trong_lo"):
            bo.append({"tep": h["tep"], "ma": h["ma"],
                       "vi_sao": "dùng chung mã với một tệp khác trong lô – gộp vào cùng chuyến"})
            continue
        if h["ma"].upper() in da_co:
            bo.append({"tep": h["tep"], "ma": h["ma"], "vi_sao": "mã vừa có người khác tạo"})
            continue
        d = next((r for r in rows if (r.get("ten_tep") or r.get("_tep")) == h["tep"]), {})
        db.add(Tour(
            code=h["ma"][:30], name=h["ten"][:200],
            tour_type=loai_chuyen(d),
            start_date=h["ngay_di"], end_date=h["ngay_ve"] or h["ngay_di"],
            operator_id=nguoi.id,
            planned_pax=int(h["so_khach"] or 0),
            status=TRANG_THAI,
            hinh_thuc=None,                    # cố ý – xem quy ước 3 ở đầu tệp
            confirmed_by=NGUON, approved_by=NGUON,
        ))
        da_co.add(h["ma"].upper())
        tao.append(h["ma"])
    db.flush()

    return {
        **kq,
        "da_nap": len(tao), "da_tao": len(tao), "bo_vi_vua_co": bo,
        "dieu_hanh": f"{nguoi.username} (id {nguoi.id})",
        "message": (
            f"Đã tạo {len(tao)} chuyến, điều hành = {nguoi.username}, trạng thái "
            f"'{TRANG_THAI}', hình thức để RỖNG. "
            f"{kq['dem']['ma_may_dat']} chuyến mang mã máy đặt ({TC.TIEN_TO_TAM}…) cần Điều hành "
            f"sửa lại. Chưa nạp một dòng quyết toán nào – việc đó ở cửa 'Kho quyết toán CŨ'."),
    }


def bo_nap(_c) -> dict:
    """Khai bộ nạp. `_c` là hàm khai cột CỦA KHUNG – nhận từ intake.py, không tự viết lại.

    Viết lại thì chỉ cần đặt tên khoá lệch một chữ ("nhan" thay vì "ten") là cửa phát CSV mẫu nổ
    KeyError, mà nổ ở một đường khác hẳn nên đọc lỗi không ra ngay. Phép thử
    `test_moi_bo_nap_deu_co_tep_mau` bắt được đúng chuyện đó.
    """
    return {
        "tao_chuyen_kho_cu": {
            "bang_dich": "tours",
            "phong_ban": "dieu_hanh",
            "lo": True,
            "ten": "Tạo CHUYẾN còn thiếu từ kho quyết toán cũ T1–T6/2026",
            "mo_ta": (
                "CHẠY TRƯỚC cửa 'Kho quyết toán CŨ'. Đo ngày 13/9/2026: VTOS có 1.150 chuyến nhưng "
                "chỉ 47/436 mã của kho khớp được – bản nạp Vietrip chỉ mang về từ tháng 6, còn "
                "T1–T5/2026 gần như trống (0 · 1 · 1 · 2 · 5 chuyến). Không có chuyến thì dòng quyết "
                "toán không có chỗ treo, và cửa nạp quyết toán chặn cứng đúng ở đấy.\n\n"
                "CỬA NÀY CHỈ TẠO KHUNG CHUYẾN: mã, tên, ngày đi, ngày về, số khách. KHÔNG ghi doanh "
                "thu, giá vốn, dự toán. Điều hành = tài khoản hệ thống đọc từ tham số "
                f"'{KHOA_TAI_KHOAN}' (mặc định {TAI_KHOAN_MAC_DINH}, đang khoá, đã là điều hành của "
                "1.145 chuyến Vietrip) – vì ô ấy quyết định thưởng chuyến thuộc về ai, gán bừa một "
                "nhân viên vào mấy trăm chuyến lịch sử là đụng vào tiền người thật.\n\n"
                "Ô HÌNH THỨC ĐỂ RỖNG. Đó là ô quyết định phép tính (tour nước ngoài bắt buộc khai tỷ "
                "giá và ngày tỷ giá cho mọi khoản), nên để biểu quyết toán hỏi người khai chứ không "
                "suy ngầm rồi tính tiền theo cái suy ấy.\n\n"
                "604 TỆP KHÔNG PHẢI 604 CHUYẾN: 21 tệp visa theo tháng, 11 outbound ghép lẻ, 3 dịch "
                "vụ lẻ và 13 bảng land của đối tác đều KHÔNG phải một chuyến – cửa này để chúng ra "
                "ngoài và nói ra, chứ không tạo chuyến ma cho chúng.\n\n"
                "112 tệp 'QT NAM CÁT TIÊN' chép từ một tệp mẫu Phan Thiết ngày 14/01/2022 và quên "
                "sửa phần đầu: cùng mã, cùng ngày, cùng tên, cùng danh sách 22 khách. Cửa này nhận "
                "ra vỏ mẫu cũ (ngày trong tệp lệch quá 60 ngày so với ngày trên tên tệp), bỏ cả mã "
                "lẫn ngày lẫn tên trong vỏ, và đặt mã tạm có tiền tố "
                f"{TC.TIEN_TO_TAM} để Điều hành sửa dần."),
            "khoa_chong_trung": "Mã chuyến (tours.code) – trùng thì bỏ qua, không ghi đè",
            "cot": [
                _c("ma_tour", "Mã tour", vi_du="NT001.03100726",
                   ghi_chu="nhãn 'Mã tour:'. Không có thì cửa đặt mã tạm KHOCU-… theo ngày trên tên tệp"),
                _c("ten_tour", "Tên tour", vi_du="NHA TRANG"),
                # Cột BẮT BUỘC duy nhất, và bắt buộc ở mức TỆP chứ không ở mức một ô: ngày khởi
                # hành đọc được từ MỘT trong ba nguồn. Không nguồn nào có thì không tạo chuyến —
                # chuyến bắt buộc có ngày đi và ngày về, mà bịa một ngày khởi hành rồi tính hạn
                # quyết toán và thưởng chuyến theo nó là chỗ sinh lỗi lặng.
                _c("ngay_di", "Ngày đi", True, kieu="ngay", vi_du="10/01/2026",
                   ghi_chu="thứ tự nguồn: nhãn 'Ngày đi:' trong tệp → ngày trên TÊN TỆP → sáu chữ "
                           "số cuối của mã (DDMMYY). Không nguồn nào có thì KHÔNG tạo chuyến"),
                _c("ngay_ve", "Ngày về", kieu="ngay", ghi_chu="không đọc được thì lấy bằng ngày đi"),
                _c("so_khach", "Số khách", kieu="so"),
            ],
            "kiem": kiem_lo, "nap": nap_lo,
            "kiem_lo": kiem_lo, "nap_lo": nap_lo, "doc_tep": doc_tep_lo,
        },
    }


def vai_tro(QUAN_TRI: tuple) -> dict:
    """Ai bấm được nút tạo.

    HẸP HƠN cả cửa nạp quyết toán – chỉ quản trị và Trưởng phòng Điều hành. Kế toán có mặt ở cửa kia
    vì họ giữ bản đối chiếu H1 để soát TIỀN; ở đây không có con số tiền nào, chỉ có chuyện chuyến
    nào từng chạy – và đó là việc của Điều hành.
    """
    return {"tao_chuyen_kho_cu": QUAN_TRI + ("tp_dh",)}
