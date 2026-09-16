# -*- coding: utf-8 -*-
"""TC-36 · XU HƯỚNG CHỈ TIÊU — chuỗi số theo kỳ để vẽ biểu đồ nhỏ trên thẻ màn hình 01.

Anh Tuấn 15/9/2026: *"doanh thu, lợi nhuận trước thuế, tour đang bán, tour chờ quyết toán — nên
làm biểu đồ cho dễ nhìn, vừa thấy số liệu vừa thấy biểu đồ so sánh với tháng trước, quý trước"*,
và *"em ưu tiên viết cấu trúc, thuật toán, luồng logic; dữ liệu quá khứ anh sẽ nạp lên sau"*.

Nên tệp này là CẤU TRÚC VÀ PHÉP TÍNH, không phải dữ liệu. Nó chạy đúng ngay cả khi chưa có một kỳ
quá khứ nào — lúc ấy nó trả về một chuỗi toàn ô rỗng kèm lý do, chứ không trả về một đường phẳng.

════════════════════════════════════════════════════════════════════════════════════════════════
HAI LOẠI CHỈ TIÊU, VÀ ĐÂY LÀ CHỖ QUYẾT ĐỊNH CẢ THIẾT KẾ

    DÒNG CHẢY  — lượng cộng dồn TRONG một kỳ: doanh thu tháng, lợi nhuận tháng.
                 TÍNH LẠI ĐƯỢC cho bất kỳ tháng nào đã qua, vì chứng từ còn nguyên trong sổ.

    TỒN KHO    — số đếm TẠI MỘT THỜI ĐIỂM: tour đang bán, tour chờ quyết toán.
                 KHÔNG tính lại được. Hôm qua có bao nhiêu tour đang bán, nếu không ai chụp lại
                 thì vĩnh viễn không biết — không có phép tính nào dựng lại được con số ấy.

Phân biệt này không phải chi tiết kỹ thuật. Nó quyết định: hai chỉ tiêu đầu có xu hướng THẬT ngay
hôm nay; hai chỉ tiêu sau chỉ có xu hướng kể từ ngày bắt đầu lưu báo cáo kỳ. Gộp chung rồi vẽ như
nhau là hứa với Chủ tịch một đường xu hướng mà một nửa trong đó không có thật.

Chỗ chụp lại đã có sẵn: bảng `bao_cao_luu`. Chú thích của chính bảng ấy viết:

    "Màn hình trả lời 'bây giờ thế nào', bản lưu trả lời 'cuối tháng trước thế nào'. Câu thứ hai
     không tính lại được — không chụp lại lúc ấy thì câu hỏi ấy vĩnh viễn không có câu trả lời."

════════════════════════════════════════════════════════════════════════════════════════════════
BỐN LUẬT CỦA CHUỖI SỐ

1 · CHỈ LẤY KỲ ĐÃ ĐÓNG. Tháng đang chạy mới đi được nửa đường; đặt nó cạnh các tháng đủ 30 ngày
    thì cột cuối luôn thấp, và đường xu hướng luôn trông như đang lao dốc. Đúng cái bẫy khối 08
    đã tránh. Con số LỚN trên thẻ vẫn là kỳ đang chạy; BIỂU ĐỒ là các kỳ đã đóng.

2 · THIẾU LÀ Ô TRỐNG, KHÔNG PHẢI SỐ 0. Kỳ chưa có số thì `gia_tri = None`. Nối liền qua chỗ trống
    là bịa ra một đoạn dữ liệu; thay bằng 0 là nói rằng kỳ ấy doanh thu bằng không.

3 · DƯỚI HAI ĐIỂM THẬT THÌ KHÔNG VẼ. Một cột đơn độc kèm mũi tên ▲ đọc ra là "đang tăng", trong
    khi sự thật là "mới có một kỳ". `du_ve` nói thẳng ra điều đó.

4 · CHỈ SO HAI KỲ LIỀN NHAU VÀ CẢ HAI ĐỀU CÓ SỐ THẬT. So kỳ đã đóng với kỳ đang chạy là so nửa
    tháng với cả tháng. So với một kỳ rỗng thì phần trăm là vô nghĩa.

════════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO TÁCH HÀM ĐỌC RA NGOÀI

`chuoi()` nhận một hàm `doc(ma, ky)`. Nhờ vậy toàn bộ phép tính — bước kỳ, luật ô trống, luật so
sánh — kiểm được bằng sổ giả, không cần cả kho lẫn cơ sở dữ liệu. Phần nối vào sổ thật nằm gọn ở
`doc_that()` và mỏng đến mức nhìn là thấy đúng.

Nó cũng chặn một lỗi thường gặp: KHÔNG tính lại doanh thu bằng công thức riêng ở đây. `doc_that()`
gọi đúng những hàm mà bảng điều hành đang gọi, nên biểu đồ không thể nói khác con số ngay trên nó.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

DONG_CHAY = "dong_chay"
TON_KHO = "ton_kho"

# Phạm vi bản lưu dùng cho màn hình Chủ tịch. Khai một chỗ, không rải chuỗi "toan_cty" khắp nơi.
PHAM_VI = "toan_cty"
KY_THANG = "thang"


class ChiTieu:
    """Một chỉ tiêu có xu hướng. `khoa_luu` là khoá của nó trong `bao_cao_luu.chi_tieu`."""

    def __init__(self, ma: str, ten: str, loai: str, khoa_luu: str = "", dinh_dang: str = "tien"):
        self.ma, self.ten, self.loai = ma, ten, loai
        self.khoa_luu = khoa_luu or ma
        self.dinh_dang = dinh_dang


# Bốn chỉ tiêu anh Tuấn chỉ đích danh. CỐ Ý không khai cả tám thẻ: bốn thẻ còn lại (Tour sắp khởi
# hành · Đội xe hôm nay · Marketing · Tồn đọng) là việc phải xử LÚC NÀY, không phải xu hướng —
# tám biểu đồ trên tám thẻ thì không thẻ nào còn nổi bật.
CHI_TIEU: dict[str, ChiTieu] = {
    "doanh_thu_thang": ChiTieu("doanh_thu_thang", "Doanh thu tháng", DONG_CHAY),
    "ln_ke_toan_thang": ChiTieu("ln_ke_toan_thang", "Lợi nhuận trước thuế", DONG_CHAY),
    "tour_dang_ban": ChiTieu("tour_dang_ban", "Tour đang bán", TON_KHO, dinh_dang="dem"),
    "tour_cho_quyet_toan": ChiTieu("tour_cho_quyet_toan", "Tour chờ quyết toán", TON_KHO,
                                   dinh_dang="dem"),
}

LY_DO_TON_KHO_RONG = ("Đây là số đếm tại một thời điểm, không tính lại được cho kỳ đã qua. Xu "
                      "hướng bắt đầu có từ kỳ đầu tiên được lưu báo cáo.")
LY_DO_CHUA_DU = "Mới có một kỳ có số — chưa đủ hai điểm để nói xu hướng."


def _lui_thang(y: int, m: int, n: int) -> tuple[int, int]:
    """Lùi n tháng. Tự viết vì `timedelta` không có đơn vị tháng, và cộng 30 ngày thì tháng 2 lệch."""
    t = (y * 12 + (m - 1)) - n
    return t // 12, t % 12 + 1


def cac_ky(hom_nay: date, so_ky: int) -> list[str]:
    """`so_ky` kỳ ĐÃ ĐÓNG gần nhất, xếp cũ → mới. Kỳ đang chạy KHÔNG nằm trong đây (luật 1)."""
    if so_ky < 1:
        raise ValueError("so_ky phải ≥ 1")
    y, m = _lui_thang(hom_nay.year, hom_nay.month, 1)      # tháng vừa đóng
    ra = []
    for i in range(so_ky):
        yy, mm = _lui_thang(y, m, i)
        ra.append(f"{yy}-{mm:02d}")
    return list(reversed(ra))


def so_sanh(diem: list[dict]) -> dict | None:
    """So HAI KỲ ĐÃ ĐÓNG LIỀN NHAU ở cuối chuỗi, và chỉ khi cả hai đều có số thật (luật 4).

    Trả None khi không so được — người gọi hiện "—", chứ không hiện 0%.
    """
    if len(diem) < 2:
        return None
    nay, truoc = diem[-1], diem[-2]
    a, b = nay.get("gia_tri"), truoc.get("gia_tri")
    if a is None or b is None:
        return None
    chenh = a - b
    # Chia cho 0 thì phần trăm không tồn tại — để None chứ không trả 0% hay "vô cực".
    pt = (chenh / abs(b)) if b else None
    return {"ky": nay["ky"], "ky_truoc": truoc["ky"], "chenh": chenh,
            "phan_tram": pt, "tang": chenh > 0, "giam": chenh < 0}


def chuoi(ma: str, doc: Callable[[str, str], float | None], *,
          so_ky: int = 6, hom_nay: date | None = None) -> dict:
    """Chuỗi xu hướng của một chỉ tiêu.

    `doc(ma, ky)` trả số của chỉ tiêu ở kỳ ấy, hoặc None nếu kỳ ấy chưa có số. Tách ra ngoài để
    phép tính kiểm được bằng sổ giả — xem chú thích đầu tệp.
    """
    ct = CHI_TIEU.get(ma)
    if ct is None:
        raise ValueError(f"chỉ tiêu chưa khai: {ma!r}")
    hom_nay = hom_nay or date.today()
    diem = [{"ky": ky, "gia_tri": doc(ma, ky)} for ky in cac_ky(hom_nay, so_ky)]
    co_so = [d for d in diem if d["gia_tri"] is not None]

    # Luật 3: dưới hai điểm thật thì KHÔNG vẽ, và nói vì sao. Một cột đơn độc kèm mũi tên đọc ra
    # là một xu hướng — mà một điểm thì không có xu hướng nào cả.
    du_ve = len(co_so) >= 2
    vi_sao = ""
    if not du_ve:
        vi_sao = (LY_DO_TON_KHO_RONG if (ct.loai == TON_KHO and not co_so)
                  else (LY_DO_CHUA_DU if co_so else
                        "Chưa có kỳ nào có số để vẽ xu hướng."))

    return {
        "ma": ma, "ten": ct.ten, "loai": ct.loai, "dinh_dang": ct.dinh_dang,
        "diem": diem,
        "so_ky_co_so": len(co_so),
        "du_ve": du_ve,
        "vi_sao": vi_sao,
        "so_sanh": so_sanh(diem) if du_ve else None,
    }


# ───────────────────────────── NỐI VÀO SỔ THẬT ─────────────────────────────
# Phần dưới mỏng có chủ đích: mọi phép tính nằm ở trên, ở đây chỉ ĐI LẤY SỐ.

def _ky_ra_thang(ky: str) -> tuple[int, int]:
    y, m = ky.split("-")
    return int(y), int(m)


def doc_that(db) -> Callable[[str, str], float | None]:
    """Hàm đọc nối vào sổ thật. Trả một closure để `chuoi()` không phải biết gì về cơ sở dữ liệu.

    DÒNG CHẢY gọi ĐÚNG những hàm mà bảng điều hành đang gọi (`_month_tours` +
    `settlement_summary`, `income_statement`) — không viết công thức thứ hai ở đây. Hai nơi cùng
    tính một con số là hai nơi sớm muộn ra hai kết quả, và lúc lệch thì không ai biết tin bên nào.

    TỒN KHO đọc `bao_cao_luu` — kỳ nào chưa có bản lưu thì trả None, KHÔNG suy ra từ số hôm nay.
    """
    def doc(ma: str, ky: str) -> float | None:
        ct = CHI_TIEU[ma]
        y, m = _ky_ra_thang(ky)
        try:
            if ct.loai == DONG_CHAY:
                from app.services import dashboard as DB
                from app.services import rules as R
                if ma == "doanh_thu_thang":
                    tours = DB._month_tours(db, y, m)
                    if not tours:
                        return None            # không có chuyến nào ĐÃ XÁC NHẬN trong kỳ → chưa có số
                    return float(sum((R.settlement_summary(db, t)["revenue"] or 0) for t in tours))
                if ma == "ln_ke_toan_thang":
                    from app.services import reports as RP
                    pl = RP.income_statement(db, ky)
                    return float(dict((r[0], r[2]) for r in pl["rows"])["50"])
                return None
            # TỒN KHO: chỉ đọc bản đã chụp.
            return _doc_ban_luu(db, ma, ky)
        except Exception:
            # Một kỳ hỏng không được làm sập cả bảng điều hành: kỳ ấy thành ô trống, các kỳ khác
            # vẫn vẽ. Ô trống đọc ra là "chưa có số" — đúng điều đang xảy ra với kỳ ấy.
            return None
    return doc


# TC-39 · CỬA SỔ CHỤP HỢP LỆ cho chỉ tiêu TỒN KHO, tính bằng ngày sau ngày cuối kỳ.
#
# Ba ngày chứ không phải một: lịch tự động lỡ một hôm vì mạng hoặc vì máy chủ khởi động lại là
# chuyện bình thường, và chạy bù sáng hôm sau vẫn cho một con số đúng trên thực tế — trong hai
# ngày thì số tour đang bán gần như không đổi. Nhưng chụp bù sau vài tuần thì không: lúc ấy con số
# ghi vào ô "tháng 8" thực chất là con số của tháng 9.
HAN_CHUP_NGAY = 3

LY_DO_CHUP_MUON = (
    "Bản lưu của kỳ này được chụp quá muộn so với ngày cuối kỳ, nên con số tồn kho trong đó là "
    "con số của lúc chụp chứ không phải của cuối kỳ. Hệ thống bỏ qua, coi như kỳ này chưa có số."
)


def chup_kip_han(den, tao_luc, han_ngay: int = HAN_CHUP_NGAY) -> bool:
    """Bản lưu này có được chụp ĐÚNG LÚC không?

    ═══════════════════════════════════════════════════════════════════════════════════════════
    ĐÂY LÀ CHỐT CHẶN QUAN TRỌNG NHẤT CỦA CẢ VÒNG, và nó chặn một lỗi rất dễ xảy ra mà không ai
    nhìn ra được từ màn hình.

    `bao_cao_phong.luu(db, "thang", moc)` chạy lại cho một kỳ CŨ vẫn chạy trơn tru — nó tính lại
    mọi chỉ tiêu từ cơ sở dữ liệu HÔM NAY rồi ghi vào ô mang nhãn kỳ cũ. Với chỉ tiêu dòng chảy
    (doanh thu, lợi nhuận) thì đúng: cộng lại sổ quyết toán tháng 8 hôm nay vẫn ra đúng con số
    tháng 8. Với chỉ tiêu tồn kho thì SAI HOÀN TOÀN: số tour đang bán hôm nay bị dán nhãn "cuối
    tháng 8", và biểu đồ xu hướng sẽ vẽ ra một quá khứ chưa từng tồn tại.

    Cái nguy hiểm là nó trông hoàn toàn bình thường — có số, có nhãn kỳ, có cột trên biểu đồ. Nên
    chốt chặn phải nằm ở chỗ ĐỌC, không phải ở chỗ ghi: chỗ ghi thì ai cũng có thể chạy bù, còn
    chỗ đọc thì chỉ có một.

    Chụp SỚM cũng bị từ chối: chụp giữa tháng thì con số là số giữa tháng, dán nhãn cuối tháng.
    """
    from datetime import datetime as _dt
    if tao_luc is None or not den:
        return False
    if isinstance(den, str):
        try:
            den = date.fromisoformat(den)
        except ValueError:
            return False
    if isinstance(tao_luc, _dt):
        tao_luc = tao_luc.date()
    cach = (tao_luc - den).days
    return 0 <= cach <= han_ngay


def _doc_ban_luu(db, ma: str, ky: str) -> float | None:
    """Lấy một chỉ tiêu TỒN KHO ra khỏi bản lưu của kỳ. None khi chưa ai lưu, hoặc lưu quá muộn."""
    from sqlalchemy import select
    from app.models.bao_cao_luu import BaoCaoLuu
    ban = db.execute(select(BaoCaoLuu).where(
        BaoCaoLuu.kind == KY_THANG, BaoCaoLuu.ky == ky,
        BaoCaoLuu.pham_vi == PHAM_VI)).scalars().first()
    if ban is None:
        return None
    # Chụp muộn thì thà không có số còn hơn có một con số của tháng khác. Ô trống đọc ra là "chưa
    # ai chụp kỳ này" — đúng điều đã xảy ra; một con số sai thì không đọc ra được gì cả.
    if not chup_kip_han(ban.den, ban.tao_luc):
        return None
    khoa = CHI_TIEU[ma].khoa_luu
    for d in (ban.chi_tieu or []):
        if isinstance(d, dict) and d.get("ma") == khoa:
            gt = d.get("gia_tri")
            return float(gt) if isinstance(gt, (int, float)) else None
    return None


def cho_man_hinh(db, *, so_ky: int = 6, hom_nay: date | None = None) -> dict:
    """Gói xu hướng của cả bốn chỉ tiêu, dạng bảng điều hành đọc thẳng."""
    d = doc_that(db)
    return {ma: chuoi(ma, d, so_ky=so_ky, hom_nay=hom_nay) for ma in CHI_TIEU}
