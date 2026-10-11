# -*- coding: utf-8 -*-
"""DT-1 + DT-3 · Bốn mốc thời gian, tiền được phép sử dụng, mức dự phòng tối thiểu.

Nguồn: đề xuất giao diện v1.1 mục III.1–III.3, ĐÃ SỬA theo phản biện và chốt của Chủ tịch
ngày 13/9/2026.

────────────────────────────────────────────────────────────────────────────────────────────────
SỬA LỚN NHẤT 13/9/2026 — LỖI TRỪ LỆNH CHI HAI LẦN
────────────────────────────────────────────────────────────────────────────────────────────────
Bản đầu của tệp này (11/9) làm đúng theo công thức viết trong v1.1 mục III.1:

    tiền khả dụng = số dư đối soát + tiền mặt − thu hộ − ký quỹ − LỆNH CHI ĐÃ DUYỆT CHƯA CHUYỂN

rồi lấy chính con số ấy làm SỐ ĐẦU KỲ của bảng dự báo. Nhưng bảng dự báo đọc nhu cầu tiền từ sổ
nghĩa vụ, nơi các lệnh chi ấy VẪN NẰM ĐÓ ở trạng thái "đã duyệt, chờ chuyển". Cùng một khoản bị
trừ hai lần:

    số dư 100  →  trừ lệnh chi 20 ở đầu kỳ  →  80  →  dự báo lại trừ 20 nữa  →  60

Con số cuối THẤP HƠN sự thật 20 triệu. Sai theo chiều này dẫn tới đi vay một khoản không cần vay.

Chủ tịch chốt 13/9: TÁCH LÀM HAI CHỈ TIÊU.

    A · TIỀN ĐƯỢC PHÉP SỬ DỤNG   ← SỐ ĐẦU KỲ của bảng dự báo. CHƯA trừ lệnh chi.
    B · TIỀN CÒN CÓ THỂ BỐ TRÍ MỚI = A − lệnh chi đã duyệt chưa chuyển.
        Là một Ô CHỈ TIÊU RIÊNG, không phải một dòng của bảng lũy kế.

Dự báo bắt đầu từ A, rồi trừ mỗi dòng chi tương lai ĐÚNG MỘT LẦN – và lệnh chi đã duyệt chưa
chuyển chính là một trong các dòng chi tương lai ấy.

Vì sao giữ cả B: A trả lời "công ty có bao nhiêu tiền". B trả lời "tôi còn duyệt chi được bao
nhiêu nữa hôm nay" – câu người điều hành hỏi khi cầm bút. Bỏ B thì người ta tự nhẩm, và nhẩm sai.

────────────────────────────────────────────────────────────────────────────────────────────────
BA SỬA KHÁC CÙNG NGÀY
────────────────────────────────────────────────────────────────────────────────────────────────
· Khoản HẠN CHẾ chỉ được trừ khi nó THỰC SỰ NẰM TRONG số dư đã đếm. Ký quỹ ở một tài khoản phong
  toả không có trong tập tài khoản chốt số dư thì trừ nó là trừ một khoản chưa từng được cộng.
  Không biết nó có nằm trong hay không thì KHÔNG ĐOÁN – trả "Chưa xác minh".
· MỐC CHỐT SỐ DƯ: dự báo chỉ lấy nghĩa vụ SAU mốc. Nghĩa vụ nằm đúng tại mốc là chỗ dễ đếm hai
  lần nhất, nên nó có quy tắc riêng và có phép thử riêng.
· NGÀY ĐẦU TIÊN THIẾU TIỀN phải tính THEO TỪNG NGÀY, không tính ở bốn mốc lũy kế. Một ngày hụt
  tiền nằm GIỮA khoảng sẽ biến mất nếu chỉ nhìn điểm cuối – mà ô cảnh báo ấy tồn tại đúng để bắt
  cái hụt giữa khoảng.

Nguyên tắc bao trùm: CHƯA CÓ SỐ THÌ GHI "Chưa xác minh", KHÔNG mặc định 0. Số 0 và "chưa ai điền"
trông giống hệt nhau trên màn hình, và cái giống nhau ấy là cách một bảng thiếu dữ liệu biến thành
một bảng nói rằng mọi thứ đều ổn.
"""
from calendar import monthrange
from datetime import date, datetime, timedelta

from app.services.lam_tron_tien import hien, lam_tron

CHUA_XAC_MINH = "Chưa xác minh"
CHUA_CO_NGUONG = "Chưa có ngưỡng"


# =============================================================================================
# DT-3 · Bốn mốc thời gian
# =============================================================================================
# v1.1 mục III.2: bốn cột LŨY KẾ từ ngày xem – 7 ngày, 14 ngày, 1 tháng lịch, 2 tháng lịch.
# Lũy kế nghĩa là cột 2 CHỨA cột 1, không phải nối tiếp sau cột 1. Hiểu nhầm thì cột "2 tháng"
# luôn nhỏ hơn cột "1 tháng", và người đọc kết luận ngược hẳn về tình hình tiền.
#
# "1 tháng lịch" KHÔNG phải 30 ngày: 31/01 cộng một tháng ra 28/02. Dùng 30 ngày thì mọi kỳ trả
# gốc rơi vào ngày 29–31 sẽ nhảy qua nhảy lại giữa hai cột tuỳ tháng, không ai truy ra vì sao.
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

    Ngày đầu luôn là chính ngày xem. Một nghĩa vụ đến hạn ĐÚNG HÔM NAY vẫn phải nằm trong cột
    1 tuần: nó là khoản gấp nhất trong bảng.
    """
    for m, _nhan, kieu, n in MOC:
        if m != ma:
            continue
        # trừ 1 vì cả hai đầu đều tính: 7 ngày kể từ hôm nay là hôm nay + 6 ngày nữa.
        return (ngay_xem, ngay_xem + timedelta(days=n - 1) if kieu == "ngay"
                else _cong_thang(ngay_xem, n))
    raise ValueError(f"Không có mốc '{ma}'. Bốn mốc hợp lệ: {', '.join(MA_MOC)}.")


def cac_khoang(ngay_xem: date) -> list[dict]:
    """Bốn mốc kèm ngày đầu/cuối viết sẵn theo DD-MM-YYYY – màn hình không phải tự định dạng."""
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


# Hai rổ đặc biệt. Không có chúng thì khoản quá hạn và khoản thiếu ngày RƠI RA NGOÀI bảng mà
# không ai biết – v1.1 mục III.2 viết thẳng là không được bỏ qua âm thầm.
QUA_HAN = "qua_han"
CHUA_DU_DU_LIEU = "chua_du_du_lieu_du_bao"

THU, CHI = "thu", "chi"


def xep_moc(ngay_den_han: date | None, ngay_xem: date) -> str:
    """Xếp một nghĩa vụ vào mốc sớm nhất chứa nó, hoặc vào hai rổ đặc biệt.

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


def luy_ke(ma: str, huong: str = CHI) -> list[str]:
    """Các mốc mà một nghĩa vụ xếp vào `ma` được cộng vào. THU và CHI KHÔNG đối xứng.

    · CHI quá hạn  → cộng vào MỌI cột. v1.1: "khoản quá hạn hiển thị riêng VÀ tính vào nhu cầu
      thanh toán". Nó là tiền đang phải trả, không thuộc cột nào cả.
    · THU quá hạn  → KHÔNG cộng vào cột nào. Đây là chỗ bản đầu của tệp này sai: nó xử thu và chi
      đối xứng nhau. Nhưng tiền RA thì mình quyết, tiền VÀO thì không – mặc định rằng một khoản
      phải thu quá hạn sẽ thu được ngay là cách làm bảng dòng tiền đẹp hơn sự thật. Muốn đưa vào
      thì phải có NGÀY DỰ KIẾN THU riêng, và lúc đó nó không còn nằm ở rổ quá hạn nữa.
    """
    if ma == QUA_HAN:
        return list(MA_MOC) if huong == CHI else []
    if ma not in MA_MOC:
        return []
    return MA_MOC[MA_MOC.index(ma):]


def con_phai_tra(tong_nghia_vu, da_tra) -> float | None:
    """Phần CÒN LẠI của một nghĩa vụ. Rỗng ở `tong_nghia_vu` là chưa ai nhập – không phải 0.

    Bản đầu của tệp này loại nghĩa vụ theo TRẠNG THÁI ("đã trả" thì bỏ). Thiếu: một nghĩa vụ trả
    một phần vẫn ở trạng thái dự kiến, và nếu cộng cả số gốc thì nhu cầu tiền bị phóng đại đúng
    bằng phần đã trả.
    """
    if tong_nghia_vu is None:
        return None
    return float(tong_nghia_vu) - float(da_tra or 0)


def sau_moc_chot(luc, moc_chot) -> bool:
    """Nghĩa vụ này có được tính vào dự báo không, xét theo mốc chốt số dư.

    Chỉ lấy giao dịch SAU mốc. Giao dịch nằm ĐÚNG TẠI mốc đã nằm trong số dư đầu kỳ rồi – tính
    tiếp là đếm hai lần. Không có mốc thì không chặn gì (và `tien_duoc_phep_su_dung` đã cảnh báo).
    """
    if moc_chot is None or luc is None:
        return True
    return luc > moc_chot


# =============================================================================================
# DT-1 · A · TIỀN ĐƯỢC PHÉP SỬ DỤNG  (số đầu kỳ của bảng dự báo)
# =============================================================================================
# Khoản HẠN CHẾ chỉ trừ khi nó THỰC SỰ nằm trong số dư đã đếm. Mỗi khoản hạn chế vì thế phải khai
# `nam_trong_so_du`: True (có, trừ), False (không, bỏ qua), None (CHƯA BIẾT – không đoán).
CONG = [
    ("so_du_ngan_hang", "Số dư tài khoản ngân hàng đã đối soát",
     "chưa đối soát thì đó là số máy đọc được, không phải số hai bên đã nhận"),
    ("tien_mat", "Tiền mặt tồn quỹ đã kiểm kê",
     "tồn quỹ trên sổ mà chưa kiểm kê thì là số dư sổ sách, không phải tiền cầm được"),
]
HAN_CHE = [
    ("thu_ho_khach", "Trừ: tiền thu hộ khách",
     "tiền của khách nằm nhờ trong tài khoản; tiêu vào là tiêu tiền người khác"),
    ("ky_quy_lu_hanh", "Trừ: tiền ký quỹ giấy phép lữ hành",
     "khoản bị ngân hàng phong toả theo giấy phép; rút ra là mất điều kiện kinh doanh"),
]
TEN = {ma: t for ma, t, _ in CONG + HAN_CHE}


def tien_duoc_phep_su_dung(gia_tri: dict, han_che_nam_trong: dict | None = None,
                           doi_soat_den: date | None = None,
                           moc_chot: datetime | None = None,
                           tai_khoan_da_dem: list | None = None) -> dict:
    """A · Tiền được phép sử dụng. Đây là SỐ ĐẦU KỲ của bảng dự báo – CHƯA trừ lệnh chi.

    `han_che_nam_trong[ma]` = True / False / None cho từng khoản hạn chế:
        True  – khoản ấy nằm trong số dư đã đếm  → TRỪ
        False – nằm ở tài khoản khác, chưa từng được cộng → KHÔNG trừ
        None  – chưa biết → KHÔNG RA SỐ. Đoán "có" thì trừ thừa, đoán "không" thì trừ thiếu; cả
                hai đều cho ra một con số không ai kiểm được.

    THIẾU MỘT THÀNH PHẦN LÀ KHÔNG RA SỐ, và hàm không trả khoá "so" khi thiếu – trả None thì nơi
    nhận rất dễ viết `so or 0`, và cả đoạn đề phòng tan thành số không đúng nghĩa đen.
    """
    han_che_nam_trong = han_che_nam_trong or {}
    thieu = [ma for ma, _t, _l in CONG if gia_tri.get(ma) is None]
    thieu += [ma for ma, _t, _l in HAN_CHE if gia_tri.get(ma) is None]
    chua_ro_vi_tri = [ma for ma, _t, _l in HAN_CHE
                      if gia_tri.get(ma) is not None and han_che_nam_trong.get(ma) is None]

    chi_tiet = []
    for ma, ten, _l in CONG:
        chi_tiet.append({"ma": ma, "ten": ten, "dau": +1, "so": gia_tri.get(ma),
                         "hien": hien(gia_tri.get(ma))})
    for ma, ten, _l in HAN_CHE:
        trong = han_che_nam_trong.get(ma)
        chi_tiet.append({"ma": ma, "ten": ten, "dau": -1, "so": gia_tri.get(ma),
                         "hien": hien(gia_tri.get(ma)), "nam_trong_so_du": trong,
                         "co_tru": bool(trong)})

    ra = {
        "chi_tieu": "tien_duoc_phep_su_dung",
        "nhan": "Tiền được phép sử dụng",
        "chi_tiet": chi_tiet,
        "thieu": thieu,
        "chua_ro_vi_tri": chua_ro_vi_tri,
        "du_du_lieu": not thieu and not chua_ro_vi_tri,
        "doi_soat_den": doi_soat_den,
        "doi_soat_den_hien": doi_soat_den.strftime("%d-%m-%Y") if doi_soat_den else "",
        "moc_chot": moc_chot,
        "tai_khoan_da_dem": list(tai_khoan_da_dem or []),
    }
    if thieu or chua_ro_vi_tri:
        ra["hien"] = CHUA_XAC_MINH
        cau = []
        if thieu:
            cau.append("còn thiếu số: "
                       + ", ".join(TEN[m].replace("Trừ: ", "") for m in thieu))
        if chua_ro_vi_tri:
            cau.append("chưa rõ khoản này có nằm trong số dư đã đếm hay không: "
                       + ", ".join(TEN[m].replace("Trừ: ", "") for m in chua_ro_vi_tri))
        ra["cau_thieu"] = "Chưa tính được tiền được phép sử dụng vì " + "; ".join(cau) + "."
        return ra

    tong = sum(lam_tron(gia_tri[ma]) for ma, _t, _l in CONG)
    tong -= sum(lam_tron(gia_tri[ma]) for ma, _t, _l in HAN_CHE
                if han_che_nam_trong.get(ma))
    ra["so"] = tong
    ra["hien"] = hien(tong)
    canh = []
    if not doi_soat_den:
        canh.append("Chưa ghi mốc đối soát – chưa biết con số này chốt đến ngày nào.")
    if moc_chot is None:
        canh.append("Chưa ghi mốc giờ chốt – không chặn được nghĩa vụ đã nằm trong số đầu kỳ.")
    if not tai_khoan_da_dem:
        canh.append("Chưa ghi danh sách tài khoản đã đếm – không kiểm được khoản hạn chế nào "
                    "thật sự nằm trong số dư.")
    if canh:
        ra["canh_bao"] = " ".join(canh)
    return ra


def tien_con_bo_tri_moi(a: dict, lenh_chi_chua_chuyen) -> dict:
    """B · Tiền còn có thể bố trí mới = A − lệnh chi đã duyệt chưa chuyển.

    Ô CHỈ TIÊU RIÊNG, KHÔNG phải một dòng của bảng lũy kế và KHÔNG phải số đầu kỳ của dự báo.
    Đây chính là chỗ bản 11/9 làm sai: lấy con số này làm đầu kỳ rồi để dự báo trừ lệnh chi lần
    nữa. Hàm này cố tình trả về một khoá tên khác ("so") kèm cờ `dung_lam_dau_ky=False` để chỗ
    nào lỡ đem nó đi làm đầu kỳ thì đọc ra ngay là sai.
    """
    if not a.get("du_du_lieu"):
        return {"chi_tieu": "tien_con_bo_tri_moi", "nhan": "Tiền còn có thể bố trí mới",
                "tinh_duoc": False, "hien": CHUA_XAC_MINH, "dung_lam_dau_ky": False,
                "cau": a.get("cau_thieu", "")}
    if lenh_chi_chua_chuyen is None:
        return {"chi_tieu": "tien_con_bo_tri_moi", "nhan": "Tiền còn có thể bố trí mới",
                "tinh_duoc": False, "hien": CHUA_XAC_MINH, "dung_lam_dau_ky": False,
                "cau": "Chưa có số lệnh chi đã duyệt nhưng chưa chuyển."}
    so = a["so"] - lam_tron(lenh_chi_chua_chuyen)
    return {"chi_tieu": "tien_con_bo_tri_moi", "nhan": "Tiền còn có thể bố trí mới",
            "tinh_duoc": True, "so": so, "hien": hien(so), "dung_lam_dau_ky": False,
            "da_tru_lenh_chi": lam_tron(lenh_chi_chua_chuyen),
            "cau": "Không dùng làm số đầu kỳ của bảng dự báo – lệnh chi đã duyệt chưa chuyển "
                   "còn được trừ một lần nữa ở các dòng chi tương lai."}


# =============================================================================================
# DT-3 · Chuỗi số dư THEO TỪNG NGÀY, và ngày đầu tiên thiếu tiền
# =============================================================================================
def chuoi_so_du_theo_ngay(dau_ky, dong_tien_theo_ngay: dict, ngay_xem: date,
                          so_ngay: int | None = None) -> list[dict]:
    """Số dư cuối mỗi ngày, từ ngày xem tới hết mốc xa nhất.

    `dong_tien_theo_ngay[ngày]` = số dương (thu) hoặc âm (chi) của riêng ngày ấy.

    Vì sao phải có hàm này: ô "ngày đầu tiên dự kiến thiếu tiền" mà tính ở bốn mốc lũy kế thì một
    ngày hụt tiền nằm GIỮA khoảng sẽ biến mất – đến cuối khoảng tiền đã về. Ô ấy tồn tại đúng để
    bắt cái hụt giữa khoảng, nên tính ở điểm cuối là làm nó mù đúng chỗ nó phải nhìn.
    """
    if so_ngay is None:
        so_ngay = (khoang(ngay_xem, MA_MOC[-1])[1] - ngay_xem).days + 1
    ra, sd = [], lam_tron(dau_ky)
    for i in range(so_ngay):
        d = ngay_xem + timedelta(days=i)
        sd += lam_tron(dong_tien_theo_ngay.get(d, 0) or 0)
        ra.append({"ngay": d, "ngay_hien": d.strftime("%d-%m-%Y"), "so_du": sd,
                   "hien": hien(sd)})
    return ra


def ngay_dau_thieu_tien(chuoi: list[dict], nguong: int = 0) -> dict:
    """Ngày đầu tiên số dư tụt dưới ngưỡng, và mức thiếu SÂU NHẤT trong cả chuỗi.

    Hai con số này khác nhau và không thay nhau được: ngày đầu tiên trả lời "khi nào", mức sâu
    nhất trả lời "cần xoay bao nhiêu". Ngày thiếu đầu tiên có thể chỉ hụt vài đồng.
    """
    dau = next((d for d in chuoi if d["so_du"] < nguong), None)
    if dau is None:
        return {"co_thieu": False, "hien": "Không có ngày nào thiếu trong khoảng dự báo."}
    sau = min(chuoi, key=lambda d: d["so_du"])
    return {"co_thieu": True, "ngay": dau["ngay"], "ngay_hien": dau["ngay_hien"],
            "so_du_hom_do": dau["so_du"], "so_du_hom_do_hien": hien(dau["so_du"]),
            "muc_thieu_lon_nhat": nguong - sau["so_du"],
            "muc_thieu_lon_nhat_hien": hien(nguong - sau["so_du"]),
            "ngay_thieu_nhieu_nhat": sau["ngay"],
            "ngay_thieu_nhieu_nhat_hien": sau["ngay_hien"]}


def ro_chua_du_du_lieu(cac_nghia_vu: list[dict]) -> dict:
    """Rổ "Chưa đủ dữ liệu dự báo" – và TỔNG GIÁ TRỊ của nó.

    Bản đầu có rổ nhưng không hiện tổng. Một rổ không có số đọc như một rổ rỗng, và khi đó quy tắc
    "không bỏ qua âm thầm" chỉ đúng trên giấy.
    """
    tong = sum(lam_tron(n.get("con_phai_tra") or 0) for n in cac_nghia_vu)
    return {"so_dong": len(cac_nghia_vu), "tong": tong, "hien": hien(tong),
            "cau": (f"{len(cac_nghia_vu)} khoản chưa có ngày đến hạn, tổng {hien(tong)} đồng – "
                    "chưa xếp được vào mốc nào." if cac_nghia_vu else
                    "Không có khoản nào thiếu ngày đến hạn.")}


# =============================================================================================
# Mức dự phòng tối thiểu – tham số hai chữ ký, theo TỪNG pháp nhân
# =============================================================================================
# v1.1 mục III.1: tham số theo từng pháp nhân, Tổng giám đốc chốt, PHẢI ĐỦ HAI CHỮ KÝ mới có hiệu
# lực. Chủ tịch chốt 11/9: hai chữ ký ấy là TỔNG GIÁM ĐỐC + CHỦ TỊCH.
KHOA_THAM_SO = "muc_du_phong_toi_thieu"

# CHỮ KÝ CỦA THAM SỐ: HỎI BẢNG LUẬT, ĐỪNG KHAI LẠI — sửa ở Đợt LG3, và đây là một LỖI THẬT.
#
# Chỗ này từng là `HAI_CHU_KY = ("signed_tgd", "signed_chutich")`, một hằng số ở mức mô-đun,
# ngoài mọi hàm. Đợt LG2 (11/10/2026) hạ tham số chính sách xuống MỘT chữ ký Chủ tịch — và hằng
# số này không biết, nên mọi mức dự phòng chốt từ sau LG2 sẽ KHÔNG BAO GIỜ có hiệu lực: tham số
# `active` với một chữ ký, còn chỗ này vẫn đòi đủ hai cột, và màn hình dòng tiền báo "đã đề xuất
# nhưng chưa đủ hai chữ ký" mãi mãi.
#
# Hàng rào của LG2 không thấy vì nó chỉ quét hàm ĐẶT chữ ký. `test_lg3` quét cả nơi ĐỌC, và quét
# riêng kiểu hằng số mức mô-đun như dòng cũ ở đây.
LOAI_CHU_KY = "tham_so"


def _du_chu_ky(p) -> bool:
    from app.services import chu_ky as _CK
    return _CK.du_chu_ky_cua(LOAI_CHU_KY, _CK.da_ky_cua(p))


def _khoa_theo_phap_nhan(company_id: int | None) -> str:
    """Một ngưỡng chung cho cả nhóm sai hai chiều cùng lúc: công ty nhỏ bị báo thiếu suốt, công ty
    lớn thì không bao giờ được báo."""
    return KHOA_THAM_SO if company_id is None else f"{KHOA_THAM_SO}:{company_id}"


def muc_du_phong(db, company_id: int | None, hom_nay: date | None = None) -> dict:
    """Ngưỡng đang có hiệu lực, hoặc "Chưa có ngưỡng".

    CHƯA CÓ và BẰNG KHÔNG là hai chuyện khác nhau: "chưa ai chốt" nghĩa là dòng THIẾU SO VỚI MỨC
    DỰ PHÒNG không tính được; "ngưỡng bằng 0" nghĩa là đã có người quyết rằng công ty không cần
    giữ đồng nào. Hàm này không bao giờ biến cái thứ nhất thành cái thứ hai.
    """
    from sqlalchemy import select

    from app.models.core import Param

    d = hom_nay or date.today()
    khoa = _khoa_theo_phap_nhan(company_id)
    rows = db.execute(select(Param).where(Param.key == khoa)).scalars().all()
    hieu_luc = [p for p in rows
                if p.effective_from and p.effective_from <= d
                and _du_chu_ky(p)
                and (p.value or "").strip() != ""]
    if not hieu_luc:
        from app.services import chu_ky as _CK
        from app.models.core import ROLES as _ROLES
        thieu_chu_ky = [p for p in rows if not _du_chu_ky(p)]
        _ai = " và ".join(_ROLES.get(v, v) for v in _CK.can_ky(LOAI_CHU_KY))
        return {"co_nguong": False, "hien": CHUA_CO_NGUONG, "khoa": khoa,
                "cau": (f"Mức dự phòng cho pháp nhân này đã đề xuất nhưng chưa đủ chữ ký của {_ai}."
                        if thieu_chu_ky else
                        "Chưa ai chốt mức dự phòng tối thiểu cho pháp nhân này.")}
    p = max(hieu_luc, key=lambda x: x.effective_from)
    so = lam_tron(float(p.value))
    return {"co_nguong": True, "so": so, "hien": hien(so), "khoa": khoa,
            "hieu_luc_tu": p.effective_from,
            "hieu_luc_tu_hien": p.effective_from.strftime("%d-%m-%Y")}


def thieu_so_voi_du_phong(so_du_cuoi, nguong: dict) -> dict:
    """Dòng THIẾU SO VỚI MỨC DỰ PHÒNG. Không có ngưỡng thì KHÔNG có số, không phải số 0.

    Trả số DƯƠNG khi đang thiếu – dòng tên "thiếu" mang số âm là thứ người đọc phải dừng lại nửa
    giây để dịch.
    """
    if not nguong.get("co_nguong"):
        return {"tinh_duoc": False, "hien": CHUA_CO_NGUONG, "cau": nguong.get("cau", "")}
    if so_du_cuoi is None:
        return {"tinh_duoc": False, "hien": CHUA_XAC_MINH,
                "cau": "Chưa tính được số dư dự kiến cuối khoảng nên chưa so được với ngưỡng."}
    thieu = lam_tron(nguong["so"]) - lam_tron(so_du_cuoi)
    if thieu <= 0:
        return {"tinh_duoc": True, "so": 0, "hien": "0", "du": True, "cau": "Đủ mức dự phòng."}
    return {"tinh_duoc": True, "so": thieu, "hien": hien(thieu), "du": False,
            "cau": f"Thiếu {hien(thieu)} đồng so với mức dự phòng {nguong['hien']} đồng."}


# =============================================================================================
# Hai góc nhìn cùng cấu trúc bảng – v1.1 mục III.3
# =============================================================================================
CAM_KET, THUC_HIEN = "cam_ket", "thuc_hien"
CO_SO_NGAY = {
    CAM_KET: {"nhan": "Nghĩa vụ đến hạn",
              "cot_ngay": "ngay_cam_ket",
              "nhan_so_du": "Số dư dự kiến – nếu thanh toán đúng hạn",
              "giai_thich": "Dùng ngày cam kết trên hợp đồng và khế ước."},
    THUC_HIEN: {"nhan": "Kế hoạch thực thu – chi",
                "cot_ngay": "ngay_du_kien_tra",
                "nhan_so_du": "Số dư dự kiến – theo kế hoạch thực hiện",
                "giai_thich": "Dùng ngày dự kiến thực trả do người phụ trách xác nhận."},
}


def nhan_so_du(co_so: str) -> str:
    """Nhãn dòng số dư PHẢI nói rõ nó dựa trên cơ sở ngày nào.

    Hai tab cho hai con số khác nhau cho cùng một khoảng – chuyện bình thường. Cái không bình
    thường là hai con số ấy cùng mang một cái nhãn: khi đó người đọc kết luận là số liệu chạy lung
    tung, rồi thôi không tin bảng nữa.
    """
    if co_so not in CO_SO_NGAY:
        raise ValueError(f"Cơ sở ngày phải là '{CAM_KET}' hoặc '{THUC_HIEN}'.")
    return CO_SO_NGAY[co_so]["nhan_so_du"]


def con_qua_han_sau_khi_doi_lich(nghia_vu: dict, ngay_xem: date) -> bool:
    """Dời ngày dự kiến trả KHÔNG xoá dấu quá hạn theo cam kết – v1.1 mục IV.4 cấm thẳng.

    Ở tab "kế hoạch thực thu–chi", khoản này xếp theo ngày dự kiến mới; nhưng nhãn quá hạn vẫn
    phải còn, vì nó nói về lời đã hứa với bên kia chứ không nói về kế hoạch của mình.
    """
    ck = nghia_vu.get("ngay_cam_ket")
    return bool(ck and ck < ngay_xem)
