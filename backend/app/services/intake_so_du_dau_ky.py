# -*- coding: utf-8 -*-
"""CỬA TẢI TỆP SỐ DƯ ĐẦU KỲ — Đợt R6b-1, 23/10/2026. Tám cửa: một cửa chốt, bảy sổ phụ.

Ranh giới 09/9/2026: mỗi con số phải có một cửa cho người nhập. Số dư đầu kỳ là con số NỀN của
cả sổ kế toán — không có cửa thì mọi báo cáo đứng trên số 0, và số 0 ấy không phải sự thật.

HAI CỬA CHO MỖI SỔ, không phải một: tải tệp (ở đây) và nhập tay từng dòng (màn hình, Đợt R6b-2).
Chủ tịch chốt 23/10/2026: "tải tệp ok, kế toán tải, nhập tay". Lý do thật: số dư đầu kỳ xuất từ
MISA ra Excel được, nên cửa tệp là đường chính; nhưng ba dòng sửa lại sau khi đối chiếu thì
không ai xuất lại cả tệp, nên cửa tay phải có.

MÃ ĐỐI TƯỢNG: CẢNH BÁO, KHÔNG CHẶN — và đây là chỗ dễ làm sai nhất của đợt này.

Mã đối tượng là BẮT BUỘC (giống MISA) ở nghĩa: dòng thiếu mã không được cộng vào tổng đối chiếu.
Nhưng cửa nạp KHÔNG từ chối dòng ấy, vì từ chối là đánh đổi sai: tệp MISA xuất ra thường có vài
dòng tổng hợp chưa gắn mã, và chặn cả tệp vì mấy dòng ấy nghĩa là người nhập phải sửa tệp ngoài
hệ thống — tức số liệu nằm ngoài hệ lâu hơn, và lần sửa ấy không ai ghi lại.

Nên: dòng vào sổ, hiện màu khác, không vào tổng, chờ gán mã trên màn hình. Xem
`services/so_du_dau_ky` cho ba luật đầy đủ.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting import Account
from app.models.so_du_dau_ky import SoDuDauKy
from app.services.so_du_dau_ky import SO_PHU, SO_PHU_THEO_MA

# Dạng kỳ gốc: "2026-01", ĐÚNG khuôn `kieu="thang"` mà services/nhap_lieu.py đã đặt cho cả ba
# cửa. KHÔNG tự nới ra nhận thêm "01/2026": bộ kiểm cột chung chạy TRƯỚC bộ kiểm của cửa này và
# đã từ chối dạng ấy, nên nới ở đây chỉ tạo ra một nguồn thứ hai nói về cùng một định dạng — và
# lúc hai nguồn lệch thì không ai biết nguồn nào đúng.
def _ky(v) -> str | None:
    s = str(v or "").strip()
    if len(s) != 7 or s[4] != "-":
        return None
    nam, thang = s[:4], s[5:]
    if not (nam.isdigit() and thang.isdigit() and 1 <= int(thang) <= 12):
        return None
    return f"{int(nam):04d}-{int(thang):02d}"


def _so(v):
    """QUY TAC 4 cua nhap_lieu: o trong la CHUA CO SO, tra ve None chu KHONG phai 0.

    Ban dau ham nay tra 0.0 cho o trong, va hau qua khong nho: moi o tien de trong bi ghi thanh
    mot con so 0 that trong so, nen "chua nhap khau hao" va "chua trich dong nao" doc giong het
    nhau. `test_kt12` cua Dot K2 bat duoc dung hai cot, va luat thi ap cho ca tam bang.
    """
    s = str(v or "").strip().replace(" ", "")
    if not s:
        return None
    # Tệp MISA xuất ra dùng dấu chấm phân nhóm nghìn và dấu phẩy thập phân. Đọc sai một lần là
    # lệch 1000 lần, và một con số lệch 1000 lần trên số dư đầu kỳ thì mọi kỳ sau lệch theo.
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) != 3 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[-1]) == 3):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _kiem_chung(db: Session, r: dict) -> tuple[list, list, str]:
    """Phần kiểm giống nhau của tám cửa: kỳ gốc, tài khoản, và con số."""
    loi, cb = [], []
    ky = _ky(r.get("ky"))
    if not ky:
        loi.append("Kỳ gốc phải có dạng 2026-01")
    tk = str(r.get("tk") or "").strip()
    if not tk:
        loi.append("Thiếu tài khoản")
    elif not db.get(Account, tk):
        loi.append(f"Tài khoản '{tk}' không có trong danh mục tài khoản")
    else:
        a = db.get(Account, tk)
        if not a.is_detail:
            loi.append(f"TK {tk} là tài khoản TỔNG HỢP — chỉ tài khoản chi tiết được ghi số dư")
        if a.ngung_su_dung:
            cb.append(f"TK {tk} đã đánh dấu ngừng sử dụng — kiểm lại xem có đúng tài khoản này")
    return loi, cb, ky or ""


def _kiem_so_phu(ma: str):
    s = SO_PHU_THEO_MA[ma]

    def kiem(db: Session, r: dict) -> tuple[list, list, str | None]:
        loi, cb, ky = _kiem_chung(db, r)
        mdt = str(r.get("ma_doi_tuong") or "").strip()
        if not mdt:
            # CẢNH BÁO, KHÔNG CHẶN. Xem đầu tệp — đây là quyết định, không phải chỗ bỏ sót.
            cb.append(f"Chưa có {s['doi_tuong'].lower()}. Dòng VẪN được nhận và không bị bỏ đi, "
                      f"nhưng KHÔNG cộng vào tổng đối chiếu cho tới khi gán mã")
        tk = str(r.get("tk") or "").strip()
        a = db.get(Account, tk) if tk else None
        if a is not None and not (a.td_doi_tuong or a.td_cong_trinh):
            cb.append(f"TK {tk} chưa khai “theo dõi chi tiết theo đối tượng” ở danh mục tài khoản "
                      f"(Đợt E1). Sổ phụ vẫn nhận, nhưng phép đối chiếu sẽ không đòi tài khoản này "
                      f"phải có sổ phụ — khai cờ ấy trước thì đối chiếu mới đủ nghĩa")
        # Khoá chống trùng chỉ dựng được khi CÓ mã: ba dòng chưa gán mã trên cùng tài khoản là ba
        # dòng hợp lệ, nên chúng cố ý không có khoá. Đó là một lý do nữa để gán mã sớm.
        return loi, cb, f"{ky}|{tk}|{mdt}" if mdt else None

    return kiem


def _nap_so_phu(ma: str):
    s = SO_PHU_THEO_MA[ma]
    lop = s["lop"]
    # Cột tiền của chính sổ này — khai từ SO_PHU chứ không gõ lại, để cửa nạp và bộ đối chiếu
    # không bao giờ nói hai điều khác nhau về việc cột nào là cột cộng.
    cot_tien = tuple(c for c in (s["cot_no"], s["cot_co"]) if c)

    def nap(db: Session, r: dict, boi: str):
        ky = _ky(r.get("ky")) or ""
        tk = str(r.get("tk") or "").strip()
        mdt = str(r.get("ma_doi_tuong") or "").strip()
        cu = None
        if mdt:
            cu = db.execute(select(lop).where(lop.ky == ky, lop.tk == tk,
                                              lop.ma_doi_tuong == mdt)).scalars().first()
        o = cu or lop(ky=ky, tk=tk, ma_doi_tuong=mdt)
        o.ten = str(r.get("ten") or o.ten or "").strip()
        for c in cot_tien:
            if str(r.get(c) or "").strip():
                setattr(o, c, _so(r.get(c)))
        for c in ("so_tai_khoan", "ngan_hang", "loai_tien", "so_nguyen_te", "ty_gia",
                  "khau_hao_luy_ke", "gia_tri_con_lai", "so_ky_con", "bo_phan",
                  "gia_tri_ban_dau", "da_phan_bo", "khoan_muc"):
            if hasattr(o, c) and r.get(c) not in (None, ""):
                v = r.get(c)
                setattr(o, c, _so(v) if c not in ("so_tai_khoan", "ngan_hang", "loai_tien",
                                                  "bo_phan", "khoan_muc") else str(v).strip())
        if hasattr(o, "so_ky_con") and str(r.get("so_ky_con") or "").strip():
            n = _so(r.get("so_ky_con"))
            o.so_ky_con = int(n) if n is not None else None
        o.nguon = "nap_tep"
        o.ghi_boi = boi
        o.ghi_luc = datetime.now()
        if cu is None:
            db.add(o)
        db.flush()
        return o, ("cap_nhat" if cu is not None else "moi")

    return nap


def _kiem_chot(db: Session, r: dict) -> tuple[list, list, str | None]:
    loi, cb, ky = _kiem_chung(db, r)
    no, co = _so(r.get("du_no")) or 0, _so(r.get("du_co")) or 0
    if no and co:
        # Cảnh báo chứ không chặn: tài khoản lưỡng tính (1388, 3388) dư hai chiều là chuyện
        # thật trên sổ MISA. Chặn ở đây là buộc người nhập bù trừ tay — và bù trừ tay là xoá
        # mất đúng cái mà phép kiểm số dư ngược chiều của Đợt R2-KC đi tìm.
        cb.append("Dòng này dư CẢ Nợ và Có. Đúng với tài khoản lưỡng tính; nếu không phải thì "
                  "kiểm lại — bù trừ hai chiều thành một số là mất dấu một trong hai")
    if not no and not co:
        cb.append("Cả hai ô số dư đều trống — dòng này vào sổ với số dư CHƯA CÓ, không phải 0. "
                  "Muốn nói số dư đúng bằng không thì gõ số 0 vào ô")
    tk = str(r.get("tk") or "").strip()
    return loi, cb, f"{ky}|{tk}" if ky and tk else None


def _nap_chot(db: Session, r: dict, boi: str):
    ky = _ky(r.get("ky")) or ""
    tk = str(r.get("tk") or "").strip()
    cu = db.get(SoDuDauKy, (ky, tk))
    o = cu or SoDuDauKy(ky=ky, tk=tk)
    # O trong de RONG, khong ghi 0: xem quy tac 4 o _so() va o app/models/so_du_dau_ky.py
    o.du_no, o.du_co = _so(r.get("du_no")), _so(r.get("du_co"))
    o.nguon, o.ghi_boi, o.ghi_luc = "nap_tep", boi, datetime.now()
    if cu is None:
        db.add(o)
    db.flush()
    return o, ("cap_nhat" if cu is not None else "moi")


_CHUNG_TA = "ô này do người nhập khai; để trống thì dòng vẫn vào sổ"

# Cột riêng của ba sổ cuối — khai ở đây để nhà máy dựng cột không phải biết về từng sổ.
_COT_RIENG = {
    "ngan_hang": lambda _c: [
        _c("so_tai_khoan", "Số tài khoản", vi_du="0071000123456"),
        _c("ngan_hang", "Ngân hàng", vi_du="Vietcombank"),
        _c("loai_tien", "Loại tiền", vi_du="VND", ghi_chu="để trống nghĩa là VND"),
        _c("so_nguyen_te", "Số nguyên tệ", kieu="tien",
           ghi_chu="chỉ khai với tài khoản ngoại tệ. Để trống KHÁC HẲN 0: trống là tài khoản "
                   "VND, 0 là tài khoản ngoại tệ hết tiền"),
        _c("ty_gia", "Tỷ giá đầu kỳ", kieu="tien"),
    ],
    "tai_san": lambda _c: [
        _c("nguyen_gia", "Nguyên giá", True, kieu="tien",
           ghi_chu="đây là con số cộng về cửa chốt TK 211 / 153 — không phải giá trị còn lại"),
        _c("khau_hao_luy_ke", "Khấu hao lũy kế", kieu="tien",
           ghi_chu="cộng về cửa chốt TK 214. Thiếu ô này thì bộ khấu hao kỳ đầu sẽ trích lại "
                   "từ đầu trên một tài sản đã dùng nhiều năm"),
        _c("gia_tri_con_lai", "Giá trị còn lại", kieu="tien"),
        _c("so_ky_con", "Số kỳ còn phải trích", kieu="so", vi_du="24"),
        _c("bo_phan", "Bộ phận sử dụng", vi_du="DIEU_HANH"),
    ],
    "tra_truoc": lambda _c: [
        _c("gia_tri_ban_dau", "Giá trị ban đầu", kieu="tien"),
        _c("da_phan_bo", "Đã phân bổ", kieu="tien"),
        _c("con_lai", "Còn lại", True, kieu="tien",
           ghi_chu="đây là con số cộng về cửa chốt TK 242"),
        _c("so_ky_con", "Số kỳ còn phân bổ", kieu="so", vi_du="18"),
        _c("khoan_muc", "Khoản mục chi phí", vi_du="KM_THUE_VP"),
    ],
    "do_dang": lambda _c: [
        _c("so_tien", "Số tiền dở dang", True, kieu="tien"),
    ],
}

_COT_NO_CO = lambda _c: [          # noqa: E731 — bảng khai, không phải logic
    _c("du_no", "Dư Nợ", kieu="tien"),
    _c("du_co", "Dư Có", kieu="tien",
       ghi_chu="một tài khoản lưỡng tính dư cả hai chiều là chuyện thật — không bù trừ tay"),
]


def bo_nap(_c) -> dict:
    ra = {
        "so_du_dau_ky": {
            "bang_dich": "so_du_dau_ky",
            "phong_ban": "ketoan",
            "ten": "Số dư đầu kỳ — CỬA CHỐT theo tài khoản",
            "mo_ta":
                "Số dư đầu kỳ của từng tài khoản ở KỲ GỐC. Đây là cửa CHỐT: bảy sổ phụ "
                "(ngân hàng, khách hàng, nhà cung cấp, nhân viên, tài sản, chi phí trả trước, "
                "chi phí dở dang) phải cộng về đúng các con số nhập ở đây.\n\n"
                "LỆCH THÌ HỆ THỐNG NÓI TO VÀ KHÔNG TỰ SỬA BÊN NÀO. Lệch giữa cửa chốt và sổ phụ "
                "là một câu hỏi về số liệu, và người trả lời là Kế toán — phần mềm làm cho nó "
                "hiện ra, không làm cho nó mất đi.\n\n"
                "Chỉ nhập TÀI KHOẢN CHI TIẾT. Tài khoản tổng hợp có số dư là tổng của các tài "
                "khoản con, nhập cả hai là cộng hai lần.\n\n"
                "Nạp lại cùng một tệp thì GHI ĐÈ theo (kỳ + tài khoản), không sinh dòng thứ hai.",
            "khoa_chong_trung": "Kỳ gốc + Tài khoản",
            "cot": [_c("ky", "Kỳ gốc", True, kieu="thang", vi_du="2026-01",
                       ghi_chu="tháng mở sổ trên VTOS, dạng 2026-01"),
                    _c("tk", "Tài khoản", True, vi_du="1121",
                       ghi_chu="phải có trong danh mục tài khoản và phải là tài khoản chi tiết")]
                   + _COT_NO_CO(_c),
            "kiem": _kiem_chot, "nap": _nap_chot,
        },
    }
    for s in SO_PHU:
        ma = s["ma"]
        rieng = _COT_RIENG.get(ma)
        cot = [_c("ky", "Kỳ gốc", True, kieu="thang", vi_du="2026-01"),
               _c("tk", "Tài khoản", True,
                  vi_du={"ngan_hang": "1121", "khach_hang": "131", "nha_cung_cap": "331",
                         "nhan_vien": "141", "tai_san": "211", "tra_truoc": "242",
                         "do_dang": "154"}[ma]),
               _c("ma_doi_tuong", s["doi_tuong"], False, vi_du="0312345678",
                  ghi_chu="BẮT BUỘC, giống MISA. Để trống thì dòng VẪN vào sổ và KHÔNG bị bỏ đi, "
                          "nhưng KHÔNG được cộng vào tổng đối chiếu cho tới khi gán mã — vì một "
                          "khoản chưa biết thuộc về ai thì không đối chiếu được với ai"),
               _c("ten", "Tên đối tượng", vi_du="CTY TNHH PHÁT HOÀNG LONG",
                  ghi_chu=_CHUNG_TA)]
        cot += rieng(_c) if rieng else _COT_NO_CO(_c)
        ra[f"so_du_dau_ky_{ma}"] = {
            "bang_dich": f"so_du_dau_ky_{ma}",
            "phong_ban": "ketoan",
            "ten": f"Số dư đầu kỳ — sổ phụ {s['ten'].lower()}",
            "mo_ta":
                f"Chi tiết số dư đầu kỳ của {s['ten'].lower()} theo từng đối tượng. Tổng sổ này "
                f"phải bằng đúng dòng cửa chốt của cùng tài khoản.\n\n"
                f"MÃ ĐỐI TƯỢNG LÀ BẮT BUỘC, GIỐNG MISA (Chủ tịch chốt 23/10/2026). Dòng thiếu mã "
                f"KHÔNG được cộng vào tổng — nếu cộng thì cửa chốt trông như đã khớp trong khi "
                f"một phần tiền chưa biết thuộc về ai. Nhưng dòng ấy cũng KHÔNG bị xoá: nó là số "
                f"liệu thật, hiện màu khác trên màn hình, và chờ gán mã.\n\n"
                f"Nạp lại ghi đè theo (kỳ + tài khoản + mã đối tượng). Dòng CHƯA có mã thì không "
                f"có khoá chống trùng — nạp lại tệp sẽ sinh thêm dòng, nên gán mã trước khi nạp lại.",
            "khoa_chong_trung": "Kỳ gốc + Tài khoản + Mã đối tượng (dòng chưa có mã: không có khoá)",
            "cot": cot,
            "kiem": _kiem_so_phu(ma), "nap": _nap_so_phu(ma),
        }
    return ra


# Mọi cửa của đợt này đều CHẠM TIỀN theo đúng nghĩa P4: một tệp vào là cả số dư nền của sổ kế
# toán đổi, và theo quyết định "nhập là dùng luôn" thì nó dùng ngay. Nên nhân viên không nạp tệp.
CHAM_TIEN = ("so_du_dau_ky",) + tuple(f"so_du_dau_ky_{s['ma']}" for s in SO_PHU)

PHONG_BAN = {k: "ketoan" for k in CHAM_TIEN}


def vai_tro(quan_tri: tuple) -> dict:
    """ĐÚNG MỘT VAI NGHIỆP VỤ: Kế toán. Chủ tịch chốt 23/10/2026 bằng đúng hai chữ "kế toán tải".

    KHÔNG mở cho vai nào khác, và cố ý KHÔNG mở cho Kế toán trưởng — đúng hình với `/ket-so`,
    nơi quy ước là "chỉ Kế toán ghi; Chủ tịch, TGĐ và Ban Kiểm soát xem chứ không ghi thay".

    Bản đầu của tệp này mở thêm cho Kế toán trưởng, và đó là một lần tự cấp quyền: ba vai mới
    (Đợt E2b) có một BẢNG KÝ, `test_le2b_ba_vai_ke_toan::test_f1_dot_nay_chi_mo_dung_nhung_cho_
    da_khai`, quét mọi dòng mã dưới app/ tìm tên ba vai ấy và đòi khớp đúng danh sách đã ký.
    Thêm một vai ở đây là đòi một chữ ký mới — mà Chủ tịch không nói câu ấy. Kế toán trưởng vẫn
    THẤY màn hình (suy từ `ketoan` theo Đợt LG1), chỉ không phải người nạp tệp.

    Số dư đầu kỳ là con số nền của toàn sổ: một dòng sai ở đây đi theo mọi kỳ về sau, và không
    phép kiểm kỳ nào bắt được vì sổ vẫn cân. Hẹp là đúng chỗ này.
    """
    return {k: quan_tri + ("ketoan",) for k in CHAM_TIEN}
