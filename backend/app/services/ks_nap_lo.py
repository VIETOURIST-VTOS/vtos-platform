"""K5 – ĐỐI CHIẾU TỆP ĐÃ TẢI VỚI SỐ ĐÃ VÀO SỔ.

Mục tiêu một câu: không có lô nạp nào mất dòng giữa đường mà không ai biết.

Nạp hàng loạt là lúc dữ liệu vào hệ thống nhanh nhất và ít người nhìn nhất. Một dòng gõ tay sai thì
người gõ thấy ngay; năm trăm dòng vào sổ trong một giây thì không ai thấy gì cả – và với quyết định
"nhập là dùng luôn" của Chủ tịch (08/9/2026) thì số đó lên báo cáo mà không qua ai duyệt.

BA PHÉP ĐỐI CHIẾU, và mỗi phép bắt một kiểu mất khác nhau:

  1. ĐẾM DÒNG.  số dòng trong tệp = đã nạp + bỏ qua vì trùng + dòng lỗi.
     Bắt: dòng bốc hơi giữa đường. Không khớp nghĩa là có dòng không nằm trong ô nào cả.

  2. ĐẾM TIỀN.  tổng tiền tệp = tiền đã nạp + tiền bỏ qua + tiền lỗi.
     Bắt: dòng vào đủ nhưng mang sai số tiền. Phép 1 mù hoàn toàn trước chuyện này – đếm dòng vẫn
     khớp hoàn hảo trong khi vài trăm triệu bốc hơi.

  3. CỬA NẠP KHÔNG GHI SỔ LÔ.  cửa nạp hàng loạt nào ghi thẳng vào bảng mà không để lại một dòng
     IntakeRun thì hai phép trên KHÔNG NHÌN THẤY nó.
     Bắt: chỗ đi vòng qua chính bộ đối chiếu này.

Phép 3 là phép quan trọng nhất, và nó sinh ra từ một quan sát trên hệ thống thật ngày 09/9/2026: sổ
nhật ký nạp có ĐÚNG MỘT dòng (11 dòng bằng lái xe), trong khi cùng tháng đó 25.728 bút toán đã vào sổ
qua bộ nạp MISA – một bộ nạp không ghi IntakeRun. Lô nạp lớn nhất hệ thống từng có là lô mà bộ đối
chiếu lô không hề biết là có tồn tại.

Đếm hết thì hệ thống có MƯỜI MỘT cửa nạp hàng loạt và đúng MỘT cửa ghi nhật ký lô.

Một bộ đối chiếu chỉ kiểm những lô tự giác đăng ký là một bộ đối chiếu đi vòng được. Nên nó phải tự
nói ra phần nó không nhìn thấy – đó là lý do có SO_DANG_KY dưới đây, và có một phép thử soi mã nguồn
để bảng ấy không lạc hậu trong im lặng.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.intake import IntakeRun

# Sai số cho phép khi so tiền. Không phải 0: tệp người dùng ghi "1.200.000,50" và nhiều bộ nạp làm
# tròn về đồng, nên lệch dưới một đồng là chuyện của phép làm tròn, không phải chuyện mất tiền.
SAI_SO_TIEN = 1.0
# Chỉ soi lô mới. Lô cũ đã có người xem hoặc đã trôi qua – mở lại ngoại lệ cho chúng chỉ làm ngập bảng.
SO_NGAY = 45

# ---------------------------------------------------------------------------------------------
# SỔ ĐĂNG KÝ CỬA NẠP HÀNG LOẠT.
#
# Mỗi dòng: (tên hàm/cửa, mô-đun, có ghi IntakeRun không, mô tả ngắn).
# Khai TAY, cố ý: một bộ kiểm soát đi quét mã nguồn lúc chạy trên máy chủ là một bộ kiểm soát hỏng
# theo cách khó hiểu khi đường dẫn tệp đổi. Chỗ chống lạc hậu nằm ở PHÉP THỬ – nó soi mã nguồn trong
# lúc chạy thử, nơi hỏng thì thấy ngay, và bắt bổ sung vào bảng này khi có cửa mới.
CUA_NAP = (
    ("intake.nap", "app.services.intake", True,
     "Cửa nạp chung – người nhập, tải tệp, AI đọc ảnh đều đi qua đây"),
    ("misa.import_journal", "app.services.misa", False,
     "Nạp sổ nhật ký từ MISA – lô lớn nhất hệ thống"),
    ("misa.import_opening_balance", "app.services.misa", False, "Nạp số dư đầu kỳ từ MISA"),
    ("misa.import_audited_checkpoint", "app.services.misa", False, "Nạp mốc kiểm toán từ MISA"),
    ("misa.import_partners", "app.services.misa", False, "Nạp danh mục đối tượng từ MISA"),
    ("misa.import_projects", "app.services.misa", False, "Nạp danh mục công trình từ MISA"),
    ("fleet.nhap_chuyen_hang_loat", "app.services.fleet", False,
     "Nạp nhật trình chuyến xe hàng loạt (báo cáo VieTrip)"),
    # Năm cửa dưới đây do PHÉP THỬ NL7 soi mã nguồn tìm ra, không phải do đọc mà nhớ ra. Đó đúng là
    # lý do phép thử ấy tồn tại: bảng khai tay nào cũng thiếu, chỉ khác nhau ở chỗ có ai phát hiện không.
    ("banks.import_bank_book", "app.services.banks", False,
     "Nạp sổ tiền gửi ngân hàng – dựng bản đồ chứng từ, mở tài khoản 112 còn thiếu"),
    ("leads.import_xlsx", "app.services.leads", False, "Nạp lead từ workbook nhiều sheet"),
    ("leads.import_rows", "app.services.leads", False,
     "Phần ghi lead của import_xlsx – cũng là cửa của API nạp lead"),
    ("staff.import_master", "app.services.staff", False,
     "Nạp danh sách nhân sự gốc, kèm mở/đóng tài khoản đăng nhập"),
    ("visa_finance.import_portal", "app.services.visa_finance", False,
     "Nạp hồ sơ từ Visa Portal"),
)


def cua_khong_ghi_so() -> list[dict]:
    return [{"cua": c, "mo_dun": m, "mo_ta": d} for c, m, ghi, d in CUA_NAP if not ghi]


# ---------------------------------------------------------------------------------------------
def _lo_gan_day(db: Session) -> list[IntakeRun]:
    tu = datetime.now() - timedelta(days=SO_NGAY)
    return list(db.execute(select(IntakeRun).where(IntakeRun.luc >= tu)
                           .order_by(IntakeRun.id.desc())).scalars())


def bon_so_dong(r: IntakeRun) -> dict:
    tong = int(r.da_nap or 0) + int(r.bo_qua_da_co or 0) + int(r.dong_loi or 0)
    return {"trong_tep": int(r.so_dong or 0), "da_nap": int(r.da_nap or 0),
            "bo_qua_da_co": int(r.bo_qua_da_co or 0), "dong_loi": int(r.dong_loi or 0),
            "cong_lai": tong, "lech": int(r.so_dong or 0) - tong}


def bon_so_tien(r: IntakeRun) -> dict | None:
    """None khi lô này KHÔNG đo được tiền – khác hẳn với đo được và bằng không.

    Bộ nạp theo lô tự lo phần ghi nên không trả về kết quả từng dòng; ép nó thành 0 thì mọi lô chạy
    qua đường đó đều bị báo thiếu tiền, và một bảng ngoại lệ toàn báo sai là bảng không ai đọc.
    """
    if r.tong_tien_tep is None: return None
    if r.tong_tien_da_nap is None and r.tong_tien_bo_qua is None and r.tong_tien_loi is None:
        return None
    f = lambda v: float(v or 0)     # noqa: E731
    tong = f((r.tong_tien_da_nap or 0)) + f((r.tong_tien_bo_qua or 0)) + f((r.tong_tien_loi or 0))  # k2-doc-an-toan: f tu ep rong thanh 0
    return {"trong_tep": f(r.tong_tien_tep), "da_nap": f(r.tong_tien_da_nap),
            "bo_qua_da_co": f(r.tong_tien_bo_qua), "dong_loi": f(r.tong_tien_loi),
            "cong_lai": round(tong, 2), "lech": round(f((r.tong_tien_tep or 0)) - tong, 2),  # k2-doc-an-toan: f tu ep rong thanh 0
            "cot_da_cong": list(r.cot_tien or [])}


def _nhan(r: IntakeRun) -> str:
    return f"lô #{r.id} ({r.loai}) – tệp “{r.ten_tep or 'không tên'}”, {r.boi or r.tac_nhan or '?'} nạp " \
           f"lúc {r.luc:%d/%m/%Y %H:%M}" if r.luc else f"lô #{r.id} ({r.loai})"


def quet(db: Session) -> list[dict]:
    ra: list[dict] = []
    for r in _lo_gan_day(db):
        d = bon_so_dong(r)
        if d["lech"] != 0:
            ra.append({"ma": f"nap_lo_lech_dong#{r.id}", "loai": "nap_lo_lech", "muc": "do",
                       "phong_ban": "", "vai_tro": "", "doi_tuong": f"lô nạp #{r.id}",
                       "tom_tat": f"{_nhan(r)}: tệp có {d['trong_tep']} dòng nhưng cộng lại chỉ ra "
                                  f"{d['cong_lai']} ({d['da_nap']} đã nạp + {d['bo_qua_da_co']} trùng + "
                                  f"{d['dong_loi']} lỗi) – lệch {d['lech']} dòng không nằm trong ô nào",
                       "chi_tiet": {"lo": r.id, "loai_nap": r.loai, "dong": d}})
        t = bon_so_tien(r)
        if t and abs(t["lech"]) > SAI_SO_TIEN:
            ra.append({"ma": f"nap_lo_lech_tien#{r.id}", "loai": "nap_lo_lech", "muc": "do",
                       "phong_ban": "", "vai_tro": "", "doi_tuong": f"lô nạp #{r.id}",
                       "tom_tat": f"{_nhan(r)}: tổng tiền trong tệp {t['trong_tep']:,.0f}đ nhưng cộng "
                                  f"lại chỉ ra {t['cong_lai']:,.0f}đ – lệch {t['lech']:,.0f}đ. Số dòng "
                                  f"vẫn khớp, nên đây là tiền sai giá trị chứ không phải mất dòng",
                       "chi_tiet": {"lo": r.id, "loai_nap": r.loai, "tien": t}})

    for c in cua_khong_ghi_so():
        ra.append({"ma": f"nap_lo_khong_so#{c['cua']}", "loai": "nap_lo_ngoai_so", "muc": "vang",
                   "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt", "doi_tuong": c["cua"],
                   "tom_tat": f"{c['cua']} nạp hàng loạt nhưng KHÔNG ghi nhật ký lô – bộ đối chiếu lô "
                              f"không nhìn thấy gì ở cửa này ({c['mo_ta']})",
                   "chi_tiet": c})
    return ra


def bang(db: Session, limit: int = 100) -> dict:
    """Bảng cho màn hình: từng lô với bốn số dòng và bốn số tiền, kèm phần bộ đối chiếu KHÔNG che được."""
    ds = _lo_gan_day(db)[:limit]
    return {
        "so_ngay": SO_NGAY, "sai_so_tien": SAI_SO_TIEN,
        "lo": [{"id": r.id, "loai": r.loai, "ten_tep": r.ten_tep, "boi": r.boi or r.tac_nhan,
                "luc": r.luc.isoformat() if r.luc else "",
                "dong": bon_so_dong(r), "tien": bon_so_tien(r)} for r in ds],
        # Nói thẳng phần không che được. Một bộ đối chiếu im lặng về vùng mù của nó là một bộ đối chiếu
        # khiến người đọc yên tâm sai chỗ.
        "cua_khong_ghi_so": cua_khong_ghi_so(),
        "tong_lo": int(db.execute(select(func.count()).select_from(IntakeRun.__table__)).scalar() or 0),
    }


def _doi_chieu_lo_nap(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot."""
    return quet(db)
