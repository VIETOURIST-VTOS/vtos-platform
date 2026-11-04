# -*- coding: utf-8 -*-
"""Cửa TẢI LÔ sổ quỹ tiền mặt — Đợt QUY-2 04/11/2026.

Chủ tịch chốt 02/11/2026: *"tiền mặt vào sổ bằng CẢ HAI CỬA: thủ quỹ nhập tay từng phiếu VÀ tải
lô sổ quỹ"*. Đợt QUY-1 làm cửa thứ nhất; đây là cửa thứ hai.

CỬA TẢI LÔ ĐI QUA ĐÚNG MỘT ĐƯỜNG VỚI CỬA NHẬP TAY — và đây là điều đáng giữ nhất của tệp này.

Nó gọi `phieu_quy.lap()`, cùng hàm mà nút «Lập phiếu» trên màn hình gọi. Nghĩa là nó chịu đúng
những hàng rào ấy: lý do phải nằm trong từ vựng của bảng quy ước; bảng quy ước chọn cặp tài
khoản; không khớp thì TỪ CHỐI. Một cửa tải lô tự dựng bút toán lấy là một đường vòng quanh bảng
quy ước — và đường vòng ấy sẽ lặng lẽ ghi khác cửa nhập tay cho tới ngày có người đối chiếu.

KHÔNG MỘT CẶP TÀI KHOẢN NÀO GÕ CỨNG Ở ĐÂY. Tìm `"111` hay `"112` trong tệp này sẽ không thấy gì,
và `test_quy2_4` canh đúng điều đó.

SỐ PHIẾU GỐC LÀ KHOÁ CHỐNG TRÙNG, VÀ NÓ PHẢI CÓ THẬT

Sổ quỹ giấy đánh số từng phiếu. Lấy số ấy làm khoá nghĩa là nạp lại cùng một tệp KHÔNG lập phiếu
thứ hai. Không có khoá thì mỗi lần bấm nhầm là quỹ phình thêm một lần — với tiền thì đó không
phải phiền toái, đó là sổ sai.
"""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payments import PhieuQuy
from app.services import phieu_quy as PQ

CHIEU_CHU = {"thu": "thu", "chi": "chi", "thu quỹ": "thu", "chi quỹ": "chi",
             "phiếu thu": "thu", "phiếu chi": "chi", "pt": "thu", "pc": "chi"}


def _chieu(v) -> str:
    return CHIEU_CHU.get(" ".join(str(v or "").strip().lower().split()), "")


def _ngay(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    for mau in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, mau).date()
        except ValueError:
            pass
    return None


def _tien(v) -> float:
    if v is None or str(v).strip() == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = "".join(ch for ch in str(v) if ch.isdigit() or ch in ".,-")
    if s.count(",") and s.count("."):
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    else:
        s = s.replace(".", "").replace(",", "")
    try:
        return float(s or 0)
    except ValueError:
        return 0.0


def _kiem(db: Session, r: dict):
    """Trả (lỗi, cảnh báo, số phiếu gốc đã có hay None).

    KIỂM TRƯỚC KHI GHI, và kiểm bằng CHÍNH bảng quy ước: gọi `HT.xem_truoc` thử. Nhờ vậy một tệp
    sai lý do bị báo ở bước xem trước — lúc người nạp còn sửa được tệp — chứ không nổ giữa chừng
    khi đã ghi mất nửa số dòng.
    """
    from app.services import hach_toan as HT

    loi, cb = [], []
    so_goc = str(r.get("so_goc") or "").strip()
    if not so_goc:
        loi.append("Thiếu Số phiếu gốc — đây là khoá chống trùng, không có nó thì nạp lại tệp sẽ "
                   "lập thêm một phiếu nữa cho cùng một khoản tiền")
    chieu = _chieu(r.get("chieu"))
    if not chieu:
        loi.append(f"Chiều phiếu phải là «thu» hoặc «chi», đang là {r.get('chieu')!r}")
    ngay = _ngay(r.get("ngay"))
    if ngay is None:
        loi.append(f"Ngày không đọc được: {r.get('ngay')!r} (dạng 31/12/2026 hoặc 2026-12-31)")
    elif ngay > date.today():
        loi.append(f"Ngày {ngay} ở tương lai — sổ quỹ ghi việc đã xảy ra")
    so_tien = _tien(r.get("so_tien"))
    if so_tien <= 0:
        loi.append("Số tiền phải lớn hơn 0")

    ly_do = str(r.get("ly_do") or "").strip()
    if chieu and ly_do:
        tu_vung = {g["gia_tri"] for g in PQ.ly_do_nhan_duoc(db, chieu)}
        if ly_do not in tu_vung:
            loi.append(f"Lý do `{ly_do}` không có trong bảng quy ước cho phiếu {chieu}. "
                       f"Đang nhận: {', '.join(sorted(tu_vung)) or '(chưa có lý do nào)'}")

    if not loi:
        nguon = PQ.CHIEU[chieu][0]
        bc = PQ._boi_canh("(xem trước)", ngay, chieu, ly_do, str(r.get("noi_dung") or ""),
                          str(r.get("ten_doi_tuong") or ""), str(r.get("ma_doi_tuong") or ""),
                          None, str(r.get("khoan_muc") or ""))
        bt = HT.xem_truoc(db, nguon, so_tien, bc, on=ngay)
        if not bt.get("khop"):
            loi.append("Không có quy tắc hạch toán nào khớp dòng này — "
                       + str(bt.get("ly_do", "")))

    cu = db.execute(select(PhieuQuy).where(PhieuQuy.so_goc == so_goc)).scalars().first() if so_goc else None
    return loi, cb, (cu.so_goc if cu is not None else None)


def _nap(db: Session, r: dict, boi: str):
    """Lập phiếu qua ĐÚNG hàm của cửa nhập tay — `phieu_quy.lap`, không một đường nào khác.

    KHÔNG CÓ CỜ «đừng chốt giao dịch», và đó là chủ ý. Mỗi phiếu quỹ là MỘT tờ chứng từ độc lập,
    đã ghi sổ bằng bút toán riêng của nó; hoàn lại phiếu thứ ba vì phiếu thứ bảy sai thì không có
    nghĩa gì về nghiệp vụ. Và khung nạp đã chạy `kiem` cho CẢ LÔ trước khi gọi `nap` dòng đầu tiên,
    nên tới đây mọi dòng còn lại đều đã qua bảng quy ước — cái hỏng nửa đường mà một giao dịch
    duy nhất sinh ra để chống thì ở đây gần như không có chỗ xảy ra.

    Đổi lại, `lap` giữ nguyên đúng một cách chốt sổ cho cả hai cửa. Một tham số `luu=False` sẽ
    thành một đường chạy thứ hai chỉ cửa này đi, mà không ai đo được là nó còn giống đường kia.
    """
    from app.models.core import User

    u = db.execute(select(User).where(User.username == boi)).scalars().first()
    if u is None:
        raise ValueError(f"Không tìm thấy người nạp {boi!r}")
    p, _bt = PQ.lap(db, u, chieu=_chieu(r.get("chieu")), ngay=_ngay(r.get("ngay")),
                    so_tien=_tien(r.get("so_tien")), ly_do=str(r.get("ly_do") or ""),
                    noi_dung=str(r.get("noi_dung") or ""),
                    ten_doi_tuong=str(r.get("ten_doi_tuong") or ""),
                    ma_doi_tuong=str(r.get("ma_doi_tuong") or ""),
                    khoan_muc=str(r.get("khoan_muc") or ""),
                    so_goc=str(r.get("so_goc") or "").strip())
    return p, "moi"


def bo_nap(_c) -> dict:
    return {
        "so_quy": {
            "ten": "Sổ quỹ tiền mặt",
            "bang_dich": "phieu_quy",
            "phong_ban": "ketoan",
            "mo_ta":
                "Sổ quỹ tiền mặt của thủ quỹ — tải cả sổ một lần thay vì gõ từng phiếu. "
                "Chủ tịch chốt 02/11/2026: tiền mặt vào sổ bằng CẢ HAI cửa, nhập tay và tải lô.\n\n"
                "MỖI DÒNG ĐI QUA ĐÚNG BẢNG QUY ƯỚC như khi gõ tay: cột «Lý do» là KHOÁ để bảng quy "
                "ước chọn cặp tài khoản, không phải ô ghi chú. Lý do không có trong bảng thì dòng "
                "ấy BÁO LỖI ở bước xem trước và CẢ TỆP không ghi gì — sửa tệp rồi nạp lại.\n\n"
                "Để TRỐNG lý do được: khi ấy bảng quy ước khớp theo việc dòng tiền có gắn đơn hay "
                "không, đúng như phiếu thu tiền mặt tại quầy.\n\n"
                "Nạp lại cùng một tệp KHÔNG lập phiếu thứ hai: khoá chống trùng là Số phiếu gốc.",
            "khoa_chong_trung": "Số phiếu gốc",
            "cot": [
                _c("so_goc", "Số phiếu gốc", True, vi_du="PT-2026-0145",
                   ghi_chu="số trên sổ quỹ giấy. Đây là khoá chống trùng — nạp lại cùng tệp thì "
                           "dòng nào đã có số này sẽ bị bỏ qua, không lập phiếu thứ hai"),
                _c("ngay", "Ngày", True, kieu="ngay", vi_du="04/11/2026",
                   khoa_ky=True, khong_tuong_lai=True),
                _c("chieu", "Thu hay chi", True, vi_du="thu",
                   ghi_chu="gõ «thu» hoặc «chi» (cũng nhận «phiếu thu» / «phiếu chi» / PT / PC)"),
                _c("so_tien", "Số tiền", True, kieu="so", vi_du="2000000"),
                _c("ly_do", "Lý do", vi_du="tra_ncc",
                   ghi_chu="mã lý do trong bảng quy ước. Để TRỐNG nếu là thu/chi tiền mặt thẳng "
                           "với khách. Xem danh sách đang nhận ở màn Sổ quỹ"),
                _c("noi_dung", "Nội dung", vi_du="Trả tiền mặt landtour Đà Lạt"),
                _c("ten_doi_tuong", "Tên đối tượng", vi_du="Khách sạn Mường Thanh",
                   ghi_chu="khách / nhà cung cấp / nhân viên / ngân hàng — bảng quy ước tự biết "
                           "dòng này cần loại nào"),
                _c("ma_doi_tuong", "Mã đối tượng", vi_du="NCC001",
                   ghi_chu="một số tài khoản BẮT BUỘC có mã đối tượng (131, 331, 3388, 141, 341). "
                           "Thiếu thì dòng ấy không ghi được"),
                _c("khoan_muc", "Khoản mục chi phí", vi_du="KM_LANDTOUR",
                   ghi_chu="chỉ cần với những quy tắc bắt buộc khoản mục"),
            ],
            "kiem": _kiem, "nap": _nap,
        },
    }
# ĐO ĐƯỢC TRÊN MAIN 04/11/2026, và đây là chỗ bản vá đầu của đợt này THIẾU HẲN:
# `intake.py` giữ một bảng `VAI_TRO` riêng, và `duoc_nap()` rơi về `QUAN_TRI` cho bất kỳ bộ nạp nào
# không khai. Nghĩa là một cửa khai đủ cột nhưng quên bảng này thì Kế toán và thủ quỹ KHÔNG bấm được
# — cửa có trên giấy mà người cần dùng thì không mở nổi.
#
# Hai vai đúng bằng hai vai của cửa nhập tay (`require_roles("ketoan", "thu_quy")` ở Đợt QUY-1), nên
# đợt này không nới một quyền nào ra ngoài quyết định 02/11 của Chủ tịch: *"thủ quỹ nhập tay từng
# phiếu VÀ tải lô sổ quỹ"*.
def vai_tro(QUAN_TRI):
    return {"so_quy": QUAN_TRI + ("ketoan", "thu_quy")}


# Dòng dữ liệu ở đây chạm THẲNG vào tiền — đúng tiêu chí của `BO_NAP_CHAM_TIEN` (xem ghi chú P4
# trong `intake.py`: siết cửa tải tệp theo DỮ LIỆU ĐI ĐÂU, không theo cấp bậc). Khai ra dù hôm nay
# nó chưa đổi gì: `thu_quy` không nằm trong `NHAN_VIEN`, nên không vai nào bị gạt. Khai để ngày mai
# có người thêm một vai nhân viên vào cửa này thì bảng tự siết, chứ không phải nhớ ra mà siết tay.
CHAM_TIEN = ("so_quy",)
