# -*- coding: utf-8 -*-
"""DT-1 + DT-3 · Bốn mốc thời gian, tiền khả dụng, và mức dự phòng tối thiểu.

Nguồn: đề xuất giao diện v1.1 mục III.1 (định nghĩa) và III.2 (quy ước thời gian).

Nguyên tắc bao trùm cả tệp, lấy thẳng từ v1.1 và từ ranh giới công việc chốt ngày 09/9/2026:
CHƯA CÓ SỐ THÌ GHI "Chưa có" HOẶC "Chưa xác minh" — KHÔNG mặc định 0. Số 0 và "chưa ai điền" là
hai chuyện khác hẳn nhau, nhưng trên màn hình chúng trông giống hệt nhau, và cái giống nhau ấy là
cách một bảng dòng tiền thiếu dữ liệu biến thành một bảng dòng tiền nói rằng mọi thứ đều ổn.
"""
from calendar import monthrange
from datetime import date, timedelta

from app.services.lam_tron_tien import hien, lam_tron

CHUA_XAC_MINH = "Chưa xác minh"
CHUA_CO_NGUONG = "Chưa có ngưỡng"


# =============================================================================================
# DT-3 · Bốn mốc thời gian
# =============================================================================================
# v1.1 mục III.2: "Bốn cột là LŨY KẾ từ ngày xem: 7 ngày, 14 ngày, 1 tháng lịch và 2 tháng lịch.
# Hiển thị chính xác ngày đầu/cuối và dùng cùng quy tắc bao gồm ngày để tránh lệch một ngày.
# KHÔNG cộng bốn cột. Tiền đầu kỳ là cùng một mốc, không cộng lặp."
#
# Lũy kế nghĩa là cột 2 CHỨA cột 1, không phải nối tiếp sau cột 1. Hiểu nhầm chỗ này thì cột "2
# tháng" chỉ còn nghĩa vụ của tháng thứ hai, và nó luôn nhỏ hơn cột "1 tháng" – một bảng mà cột
# xa hơn lại nhẹ hơn thì người đọc kết luận ngược hẳn về tình hình tiền.
#
# "1 tháng lịch" KHÔNG phải 30 ngày. Ngày 31/01 cộng một tháng lịch ra 28/02 (hoặc 29/02), vì
# tháng Hai không có ngày 31. Dùng 30 ngày cho gọn thì mọi kỳ trả gốc rơi vào ngày 29–31 hàng
# tháng sẽ nhảy qua nhảy lại giữa hai cột tùy tháng, và không ai truy ra được vì sao.
MOC = [
    ("7n", "1 tuần", "ngay", 7),
    ("14n", "2 tuần", "ngay", 14),
    ("1t", "1 tháng", "thang", 1),
    ("2t", "2 tháng", "thang", 2),
]
MA_MOC = [m[0] for m in MOC]


def _cong_thang(d: date, n: int) -> date:
    """Cộng n tháng LỊCH, kẹp về ngày cuối tháng khi tháng đích ngắn hơn."""
    thang = d.month - 1 + n
    nam = d.year + thang // 12
    thang = thang % 12 + 1
    return date(nam, thang, min(d.day, monthrange(nam, thang)[1]))


def khoang(ngay_xem: date, ma: str) -> tuple[date, date]:
    """Khoảng của một mốc: (ngày đầu, ngày cuối), BAO GỒM CẢ HAI ĐẦU.

    Ngày đầu luôn là chính ngày xem – đây là quy tắc "cùng quy tắc bao gồm ngày" của v1.1. Một
    nghĩa vụ đến hạn ĐÚNG HÔM NAY vẫn phải nằm trong cột 1 tuần: nó là khoản gấp nhất trong bảng.
    """
    for m, _nhan, kieu, n in MOC:
        if m != ma:
            continue
        # trừ 1 vì cả hai đầu đều tính: 7 ngày kể từ hôm nay là hôm nay + 6 ngày nữa.
        return (ngay_xem, ngay_xem + timedelta(days=n - 1) if kieu == "ngay"
                else _cong_thang(ngay_xem, n))
    raise ValueError(f"Không có mốc '{ma}'. Bốn mốc hợp lệ: {', '.join(MA_MOC)}.")


def cac_khoang(ngay_xem: date) -> list[dict]:
    """Bốn mốc kèm ngày đầu và ngày cuối viết sẵn theo DD-MM-YYYY.

    Trả cả chuỗi ngày để màn hình KHÔNG phải tự định dạng: quy ước ngày của hệ thống là
    DD-MM-YYYY, và mỗi nơi tự định dạng là một nơi có thể quên.
    """
    ra = []
    for ma, nhan, _kieu, _n in MOC:
        d, c = khoang(ngay_xem, ma)
        ra.append({"ma": ma, "nhan": nhan, "tu": d, "den": c,
                   "tu_hien": d.strftime("%d-%m-%Y"), "den_hien": c.strftime("%d-%m-%Y"),
                   "so_ngay": (c - d).days + 1})
    return ra


def trong_khoang(ngay_den_han: date, ngay_xem: date, ma: str) -> bool:
    d, c = khoang(ngay_xem, ma)
    return d <= ngay_den_han <= c


# Khoản QUÁ HẠN và khoản KHÔNG CÓ NGÀY ĐẾN HẠN – v1.1 mục III.2.
QUA_HAN = "qua_han"
CHUA_DU_DU_LIEU = "chua_du_du_lieu_du_bao"


def xep_moc(ngay_den_han: date | None, ngay_xem: date) -> str:
    """Xếp một nghĩa vụ vào mốc sớm nhất chứa nó, hoặc vào hai rổ đặc biệt.

    Hai rổ ấy tồn tại vì nếu không có chúng thì khoản quá hạn và khoản thiếu ngày sẽ RƠI RA NGOÀI
    bảng mà không ai biết. v1.1 viết thẳng: khoản không có ngày đến hạn vào danh sách "Chưa đủ dữ
    liệu dự báo", KHÔNG bị bỏ qua âm thầm.

    Quá hạn tách riêng chứ không nhét vào cột 1 tuần: "phải trả trong tuần này" và "lẽ ra phải trả
    từ tháng trước" là hai tình trạng khác nhau, và gộp lại thì cái thứ hai biến mất.
    """
    if ngay_den_han is None:
        return CHUA_DU_DU_LIEU
    if ngay_den_han < ngay_xem:
        return QUA_HAN
    for ma in MA_MOC:
        if trong_khoang(ngay_den_han, ngay_xem, ma):
            return ma
    return ""      # xa hơn hai tháng: chưa vào bảng, nhưng KHÔNG mất – nó ở kỳ sau


def luy_ke(ma: str) -> list[str]:
    """Các mốc mà một nghĩa vụ xếp vào `ma` cũng phải được cộng vào. Đây là chỗ "lũy kế" thành thật.

    Khoản quá hạn được cộng vào MỌI cột: v1.1 ghi "khoản quá hạn chưa trả hiển thị riêng VÀ tính
    vào nhu cầu thanh toán". Nó là tiền đang phải trả, không phải tiền của một cột nào.
    """
    if ma == QUA_HAN:
        return list(MA_MOC)
    if ma not in MA_MOC:
        return []
    return MA_MOC[MA_MOC.index(ma):]


# =============================================================================================
# DT-1 · Tiền khả dụng
# =============================================================================================
# v1.1 mục III.1, nguyên văn:
#   Tiền khả dụng = số dư các tài khoản ngân hàng ĐÃ ĐỐI SOÁT
#                 + tiền mặt tồn quỹ ĐÃ KIỂM KÊ
#                 − tiền thu hộ khách (tiền của khách, không phải tiền công ty)
#                 − tiền ký quỹ giấy phép lữ hành
#                 − các lệnh chi ĐÃ DUYỆT NHƯNG CHƯA CHUYỂN
#   Luôn hiển thị kèm mốc "đối soát đến ngày …".
#   Tiền của pháp nhân này không mặc định dùng được cho pháp nhân khác.
THANH_PHAN = [
    ("so_du_ngan_hang", +1, "Số dư tài khoản ngân hàng đã đối soát",
     "chưa đối soát thì con số ấy là số máy đọc được, không phải số hai bên đã nhận"),
    ("tien_mat", +1, "Tiền mặt tồn quỹ đã kiểm kê",
     "tồn quỹ trên sổ mà chưa kiểm kê thì đó là số dư sổ sách, không phải tiền cầm được"),
    ("thu_ho_khach", -1, "Trừ: tiền thu hộ khách",
     "tiền của khách nằm nhờ trong tài khoản; tiêu vào là tiêu tiền người khác"),
    ("ky_quy_lu_hanh", -1, "Trừ: tiền ký quỹ giấy phép lữ hành",
     "khoản bị ngân hàng phong toả theo giấy phép, rút ra là mất điều kiện kinh doanh"),
    ("lenh_chi_chua_chuyen", -1, "Trừ: lệnh chi đã duyệt nhưng chưa chuyển",
     "đã có người ký duyệt nên tiền ấy đã có chủ; đếm nó là khả dụng là đếm hai lần"),
]
DAU = {ma: dau for ma, dau, _t, _l in THANH_PHAN}
TEN_THANH_PHAN = {ma: t for ma, _d, t, _l in THANH_PHAN}


def tien_kha_dung(gia_tri: dict, doi_soat_den: date | None = None) -> dict:
    """Tính tiền khả dụng từ năm thành phần. THIẾU MỘT THÀNH PHẦN LÀ KHÔNG RA SỐ.

    Đây là quyết định quan trọng nhất của hàm này, và nó cố tình khó chịu: nếu một thành phần chưa
    có số thì kết quả là "Chưa xác minh", không phải một con số tính từ bốn thành phần còn lại.

    Vì sao không cho qua: bốn thành phần đầu đều là số DƯƠNG hoặc số TRỪ nhỏ; thành phần dễ thiếu
    nhất – lệnh chi đã duyệt chưa chuyển – là số TRỪ. Bỏ nó đi thì tiền khả dụng LUÔN CAO HƠN sự
    thật, đúng theo chiều làm người ta yên tâm chi. Một con số sai theo chiều an toàn thì còn cãi
    được; sai theo chiều này thì không.

    `gia_tri` là số do bộ phận nghiệp vụ nhập qua cửa nhập của họ (xem CUA_NHAP ở
    dong_tien_pham_vi.py). Hàm này KHÔNG đi tìm số ở đâu cả – nó chỉ cộng trừ và nói thật về chỗ
    còn thiếu.
    """
    thieu = [ma for ma, _d, _t, _l in THANH_PHAN if gia_tri.get(ma) is None]
    chi_tiet = [{"ma": ma, "ten": TEN_THANH_PHAN[ma], "dau": DAU[ma],
                 "so": gia_tri.get(ma), "hien": hien(gia_tri.get(ma))}
                for ma, _d, _t, _l in THANH_PHAN]
    ra = {
        "chi_tiet": chi_tiet,
        "thieu": thieu,
        "du_du_lieu": not thieu,
        "doi_soat_den": doi_soat_den,
        "doi_soat_den_hien": doi_soat_den.strftime("%d-%m-%Y") if doi_soat_den else "",
    }
    if thieu:
        # Không trả khoá "so" khi thiếu. Trả "so": None thì nơi nhận rất dễ viết `so or 0`, và
        # cả đoạn đề phòng ở trên tan thành số không đúng nghĩa đen.
        ra["hien"] = CHUA_XAC_MINH
        ra["cau_thieu"] = ("Chưa tính được tiền khả dụng vì còn thiếu: "
                           + ", ".join(TEN_THANH_PHAN[m].replace("Trừ: ", "") for m in thieu) + ".")
        return ra
    tong = sum(DAU[ma] * lam_tron(gia_tri[ma]) for ma, _d, _t, _l in THANH_PHAN)
    ra["so"] = tong
    ra["hien"] = hien(tong)
    if not doi_soat_den:
        # v1.1: "Luôn hiển thị kèm mốc đối soát đến ngày…". Một con số tiền khả dụng không kèm
        # ngày đối soát là một con số không biết mình cũ bao nhiêu.
        ra["canh_bao"] = "Chưa ghi mốc đối soát – chưa biết con số này chốt đến ngày nào."
    return ra


# =============================================================================================
# Mức dự phòng tối thiểu – tham số hai chữ ký, theo TỪNG pháp nhân
# =============================================================================================
# v1.1 mục III.1: "Mức dự phòng tối thiểu là một tham số theo từng pháp nhân, do Tổng giám đốc chốt
# và lưu trong Chính sách & định mức, PHẢI ĐỦ HAI CHỮ KÝ mới có hiệu lực. Không viết cố định trong
# giao diện. Dòng 'Thiếu so với mức dự phòng' chỉ tính được khi tham số này đã có hiệu lực; chưa có
# thì ghi 'Chưa có ngưỡng'."
#
# Chủ tịch chốt ngày 11/9/2026: hai chữ ký ấy là TỔNG GIÁM ĐỐC + CHỦ TỊCH, không phải Kế toán
# trưởng – mọi vấn đề tài chính do Chủ tịch và Tổng giám đốc quyết.
KHOA_THAM_SO = "muc_du_phong_toi_thieu"
HAI_CHU_KY = ("signed_tgd", "signed_chutich")


def _khoa_theo_phap_nhan(company_id: int | None) -> str:
    """Tham số theo TỪNG pháp nhân. Một ngưỡng chung cho cả nhóm là sai hai chiều cùng lúc: công ty
    nhỏ bị báo thiếu suốt, công ty lớn thì không bao giờ được báo."""
    return KHOA_THAM_SO if company_id is None else f"{KHOA_THAM_SO}:{company_id}"


def muc_du_phong(db, company_id: int | None, hom_nay: date | None = None) -> dict:
    """Ngưỡng dự phòng đang có hiệu lực cho một pháp nhân, hoặc "Chưa có ngưỡng".

    CHƯA CÓ và BẰNG KHÔNG là hai chuyện khác nhau: "chưa ai chốt ngưỡng" nghĩa là dòng THIẾU SO VỚI
    MỨC DỰ PHÒNG không tính được; "ngưỡng bằng 0" nghĩa là đã có người quyết rằng công ty không cần
    giữ đồng nào. Hàm này không bao giờ biến cái thứ nhất thành cái thứ hai.
    """
    from app.models.core import Param
    from sqlalchemy import select

    d = hom_nay or date.today()
    khoa = _khoa_theo_phap_nhan(company_id)
    rows = db.execute(select(Param).where(Param.key == khoa)).scalars().all()
    hieu_luc = [p for p in rows
                if p.effective_from and p.effective_from <= d
                and all(getattr(p, c, False) for c in HAI_CHU_KY)
                and (p.value or "").strip() != ""]
    if not hieu_luc:
        thieu_chu_ky = [p for p in rows if not all(getattr(p, c, False) for c in HAI_CHU_KY)]
        return {"co_nguong": False, "hien": CHUA_CO_NGUONG, "khoa": khoa,
                "cau": ("Mức dự phòng cho pháp nhân này đã đề xuất nhưng chưa đủ hai chữ ký của "
                        "Tổng giám đốc và Chủ tịch." if thieu_chu_ky else
                        "Chưa ai chốt mức dự phòng tối thiểu cho pháp nhân này.")}
    # Bản có hiệu lực từ ngày GẦN NHẤT mà không vượt quá hôm nay.
    p = max(hieu_luc, key=lambda x: x.effective_from)
    so = lam_tron(float(p.value))
    return {"co_nguong": True, "so": so, "hien": hien(so), "khoa": khoa,
            "hieu_luc_tu": p.effective_from, "hieu_luc_tu_hien": p.effective_from.strftime("%d-%m-%Y")}


def thieu_so_voi_du_phong(so_du_cuoi, nguong: dict) -> dict:
    """Dòng THIẾU SO VỚI MỨC DỰ PHÒNG. Không có ngưỡng thì KHÔNG có số, không phải số 0.

    Trả số DƯƠNG khi đang thiếu – vì dòng ấy tên là "thiếu", và một dòng tên "thiếu" mang số âm là
    thứ người đọc phải dừng lại nửa giây để dịch. Đủ hoặc dư thì trả 0 kèm nhãn rõ.
    """
    if not nguong.get("co_nguong"):
        return {"tinh_duoc": False, "hien": CHUA_CO_NGUONG, "cau": nguong.get("cau", "")}
    if so_du_cuoi is None:
        return {"tinh_duoc": False, "hien": CHUA_XAC_MINH,
                "cau": "Chưa tính được số dư dự kiến cuối khoảng nên chưa so được với ngưỡng."}
    thieu = lam_tron(nguong["so"]) - lam_tron(so_du_cuoi)
    if thieu <= 0:
        return {"tinh_duoc": True, "so": 0, "hien": "0", "du": True,
                "cau": "Đủ mức dự phòng."}
    return {"tinh_duoc": True, "so": thieu, "hien": hien(thieu), "du": False,
            "cau": f"Thiếu {hien(thieu)} đồng so với mức dự phòng {nguong['hien']} đồng."}


# =============================================================================================
# Hai góc nhìn cùng cấu trúc bảng – v1.1 mục III.3
# =============================================================================================
# "Tab Nghĩa vụ đến hạn dùng LỊCH CAM KẾT; số dư mang nhãn 'nếu thanh toán đúng hạn'. Tab Kế hoạch
# thực thu–chi dùng LỊCH THỰC HIỆN DỰ KIẾN. Không trộn hai cơ sở ngày trong cùng một bảng mà không
# giải thích."
CAM_KET, THUC_HIEN = "cam_ket", "thuc_hien"
CO_SO_NGAY = {
    CAM_KET: {"nhan": "Nghĩa vụ đến hạn",
              "nhan_so_du": "Số dư dự kiến – nếu thanh toán đúng hạn",
              "giai_thich": "Dùng ngày cam kết trên hợp đồng và khế ước."},
    THUC_HIEN: {"nhan": "Kế hoạch thực thu – chi",
                "nhan_so_du": "Số dư dự kiến – theo kế hoạch thực hiện",
                "giai_thich": "Dùng ngày dự kiến thực trả do người phụ trách xác nhận."},
}


def nhan_so_du(co_so: str) -> str:
    """Nhãn dòng số dư PHẢI nói rõ nó dựa trên cơ sở ngày nào.

    Hai tab cho ra hai con số khác nhau cho cùng một khoảng thời gian, và đó là chuyện bình thường.
    Cái không bình thường là hai con số ấy cùng mang một cái nhãn "số dư dự kiến cuối khoảng" –
    khi đó người đọc kết luận là số liệu chạy lung tung, rồi thôi không tin bảng nữa.
    """
    if co_so not in CO_SO_NGAY:
        raise ValueError(f"Cơ sở ngày phải là '{CAM_KET}' hoặc '{THUC_HIEN}'.")
    return CO_SO_NGAY[co_so]["nhan_so_du"]
