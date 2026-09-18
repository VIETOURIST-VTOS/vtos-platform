"""PHÉP TÍNH CỦA KẾ HOẠCH THÁNG – đọc, ghi, và ba luật không được nới.

Anh Tuấn duyệt mở cửa nhập ngày 15/9/2026. Bảng nằm ở models/ke_hoach.py; cửa HTTP ở
api/v1/ke_hoach.py; phép tính và luật nằm ở đây.

═══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT 1 · KẾ HOẠCH HỢP NHẤT CHỈ TỒN TẠI KHI ĐỦ MỌI PHÁP NHÂN – THIẾU MỘT LÀ KHÔNG CÓ
═══════════════════════════════════════════════════════════════════════════════════════════════
Đây là luật dễ bị nới nhất, nên nói kỹ. Tập đoàn có nhiều pháp nhân trong phạm vi hợp nhất. Kế toán
nhập kế hoạch cho từng pháp nhân, và chuyện bình thường là hôm nay nhập xong ba, còn hai để mai.

Cộng ba pháp nhân đã nhập rồi gọi kết quả là "kế hoạch tháng của tập đoàn" là chỗ hỏng: con số ấy
NHỎ HƠN kế hoạch thật, nhưng trông không khác gì một con số đầy đủ. Màn hình Chủ tịch sẽ lấy doanh
thu thực hiện của CẢ NĂM pháp nhân chia cho kế hoạch của BA – và báo về một tỉ lệ đạt kế hoạch cao
vọt. Không ai phát hiện, vì không có gì trông giống lỗi cả.

Nên: thiếu một pháp nhân thì kế hoạch hợp nhất là `None`, kèm DANH SÁCH TÊN những pháp nhân còn
thiếu. Chưa có thì nói chưa có, và nói luôn còn thiếu ai – đó mới là câu dùng được.

═══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT 2 · THÁNG ĐÃ KHÉP SỬA ĐƯỢC, NHƯNG PHẢI ĐỂ LẠI LÝ DO
═══════════════════════════════════════════════════════════════════════════════════════════════
Kế hoạch là thước đo. Một thước đo sửa được sau khi đã đo xong thì không còn là thước – ai không
đạt chỉ tiêu chỉ việc hạ chỉ tiêu xuống.

Nhưng KHOÁ CỨNG cũng sai, và sai theo kiểu tệ hơn: Hội đồng quản trị điều chỉnh chỉ tiêu giữa năm là
chuyện có thật, gõ nhầm một số 0 cũng là chuyện có thật. Khoá cứng thì người ta không sửa được trong
hệ thống, nên họ sửa ở ngoài – và bảng kế hoạch trong VTOS lặng lẽ thành bảng không ai dùng.

Nên: sửa được, nhưng mỗi lần sửa tháng đã khép phải kèm lý do đủ dài để đọc ra được chuyện gì, lý do
nằm ngay trên dòng, và số lần sửa được đếm. Một dòng sửa bảy lần thì con số bảy đã là câu hỏi.

MỐC KHÉP TẠM THỜI LÀ MỐC LỊCH, không phải mốc kết sổ kế toán. Nghĩa là tháng 8 khép từ 00:00 ngày
1/9, dù Kế toán còn đang hạch toán tháng 8. Đây là chỗ CÒN NỢ, ghi ra để vòng sau không phải đoán:
khi phân hệ Kết sổ mở đường hỏi "kỳ này đã kết sổ chưa", `da_khep()` phải chuyển sang hỏi nó. Chọn
mốc lịch trước vì nó không bao giờ sai theo hướng nguy hiểm – nó khoá SỚM hơn mốc kết sổ, tức là
đòi lý do ở vài ngày đáng ra chưa cần đòi, chứ không thả lỏng những ngày đáng ra phải đòi.

═══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT 3 · KHÔNG NỘI SUY, KHÔNG LẤY THÁNG TRƯỚC LÀM LỐI LUI
═══════════════════════════════════════════════════════════════════════════════════════════════
Tháng nào không ai nhập thì tháng ấy TRỐNG. Không lấy tháng trước, không chia đều kế hoạch năm cho
12, không suy từ thực hiện cùng kỳ năm ngoái. Cả ba phép ấy đều ra một con số trông rất hợp lý, và
cả ba đều biến "chưa ai lập kế hoạch" thành "đã có kế hoạch" mà không ai biết.
"""
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User, Company
from app.models.ke_hoach import KeHoachThang
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R

# Danh sách ĐÓNG. Thêm một chỉ tiêu là sửa ở đây, và sửa ở đây thì màn hình nhập tự có thêm cột –
# không phải sửa hai chỗ. Khoá là mã lưu trong cơ sở dữ liệu, giá trị là tên người đọc thấy.
CHI_TIEU = {
    "doanh_thu": "Doanh thu",
    "loi_nhuan_truoc_thue": "Lợi nhuận trước thuế",
}

# Pháp nhân NẰM TRONG phạm vi hợp nhất. Công ty liên kết áp dụng phương pháp vốn chủ sở hữu nên
# doanh thu của nó không cộng vào doanh thu hợp nhất – lập kế hoạch cho nó rồi cộng vào là thổi
# doanh thu tập đoàn lên đúng bằng phần không được hợp nhất.
KIND_HOP_NHAT = ("me", "con", "chi_nhanh")

# Độ dài tối thiểu của lý do sửa tháng đã khép. Không phải để làm khó: một ô lý do cho phép gõ "ok"
# thì trong vòng một tháng mọi lý do trong bảng đều là "ok", và cột lý do thành cột trang trí.
DAI_TOI_THIEU_LY_DO = 10

LY_DO_THIEU = (f"Kỳ này đã khép. Sửa kế hoạch của một kỳ đã qua phải kèm lý do ít nhất "
               f"{DAI_TOI_THIEU_LY_DO} ký tự – lý do được lưu ngay trên dòng và vào nhật ký.")


def ky_cua(d: date) -> str:
    """Ngày → mã kỳ tháng, ví dụ 2026-09-14 → '2026-09'."""
    return f"{d.year:04d}-{d.month:02d}"


def hop_le_ky(ky: str) -> bool:
    """Đúng dạng YYYY-MM và tháng nằm trong 1..12.

    Kiểm ở đây chứ không để cơ sở dữ liệu tự chịu: cột là chuỗi, nên '2026-13' hay 'thang sau' lưu
    được hết, và một dòng như thế thì mọi phép so sánh kỳ sau đó âm thầm trả về sai.
    """
    return be_rong(ky) is not None


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# TC-44 · KẾ HOẠCH CÓ BA BỀ RỘNG: THÁNG · QUÝ · NĂM
# ═══════════════════════════════════════════════════════════════════════════════════════════════
# Anh Tuấn chốt 16/9/2026, khi chọn giữa hai cách lấy mục tiêu năm:
#
#     "HĐQT nhập riêng một ô mục tiêu năm và quý."
#
# Đây là lần BÁC một đề xuất của em, và bác đúng — nên ghi lại cả hai vế để vòng sau không lặng lẽ
# đổi lại. Em đề xuất cộng 12 tháng kế hoạch thành mục tiêu năm, vì như thế Kế toán chỉ nhập một
# chỗ. Nhưng chỉ tiêu năm là điều HỘI ĐỒNG QUẢN TRỊ quyết, và nó KHÔNG nhất thiết bằng tổng 12
# tháng: hội đồng có thể đặt 230 tỷ trong khi phân bổ tháng cộng lại ra 226 — phần chênh là dư địa
# cố ý. Cộng ngược lại là xoá mất một quyết định quản trị và thay bằng một phép cộng.
#
# HỆ QUẢ PHẢI CHỊU, và phải nói ra: Kế toán nay nhập ở BA chỗ (12 tháng + 4 quý + 1 năm cho mỗi
# pháp nhân, mỗi chỉ tiêu). Ba chỗ thì sớm muộn lệch nhau — tổng 12 tháng không bằng ô năm. Hệ
# thống KHÔNG tự sửa chỗ lệch ấy: nó HIỆN RA (xem `doi_chieu_be_rong`), vì chênh lệch giữa chỉ
# tiêu hội đồng giao và phân bổ tháng của Kế toán là một câu hỏi quản trị, không phải một lỗi nhập.
#
# Mã kỳ dùng ĐÚNG quy ước của services/xu_huong: "2026-09" · "2026-Q3" · "2026". Một quy ước cho
# cả kho — hai quy ước là hai chỗ phải nhớ, và chỗ nối giữa chúng là chỗ sinh lỗi.

BE_RONG_THANG = "thang"
BE_RONG_QUY = "quy"
BE_RONG_NAM = "nam"
TEN_BE_RONG = {BE_RONG_THANG: "Tháng", BE_RONG_QUY: "Quý", BE_RONG_NAM: "Năm"}

# VTOS không có sổ trước 2026. Một ô chọn bày ra năm 2025 chỉ để ai bấm vào cũng gặp một hình rỗng.
NAM_DAU = 2026


def be_rong(ky: str) -> str | None:
    """Bề rộng của một mã kỳ, hoặc None nếu mã sai dạng.

    Kiểm ở đây chứ không để cơ sở dữ liệu tự chịu: cột `ky` là chuỗi, nên '2026-13' hay 'thang sau'
    lưu được hết, và một dòng như thế thì mọi phép so sánh kỳ sau đó âm thầm trả về sai.
    """
    s = str(ky)
    if "-Q" in s:
        y, q = s.split("-Q", 1)
        return BE_RONG_QUY if (len(y) == 4 and y.isdigit() and q.isdigit()
                               and 1 <= int(q) <= 4) else None
    if "-" in s:
        phan = s.split("-")
        if len(phan) != 2 or len(phan[0]) != 4 or len(phan[1]) != 2:
            return None
        if not phan[0].isdigit() or not phan[1].isdigit():
            return None
        return BE_RONG_THANG if 1 <= int(phan[1]) <= 12 else None
    return BE_RONG_NAM if (len(s) == 4 and s.isdigit()) else None


def _cuoi_ky(ky: str) -> tuple[int, int]:
    """(năm, tháng) của tháng CUỐI trong kỳ — dùng để biết kỳ đã khép chưa."""
    loai = be_rong(ky)
    if loai == BE_RONG_THANG:
        y, m = str(ky).split("-")
        return int(y), int(m)
    if loai == BE_RONG_QUY:
        y, q = str(ky).split("-Q")
        return int(y), int(q) * 3
    return int(ky), 12


def da_khep(ky: str, hom_nay: date | None = None) -> bool:
    """Kỳ này đã qua chưa. Xem LUẬT 2 ở đầu tệp về việc vì sao dùng mốc lịch.

    So bằng THÁNG CUỐI của kỳ, không so chuỗi: '2026' < '2026-09' theo phép so chuỗi, nên so chuỗi
    sẽ kết luận cả năm 2026 đã khép ngay từ tháng 1 — và Kế toán không sửa được chỉ tiêu năm của
    chính năm đang chạy mà không phải viết lý do.
    """
    hom_nay = hom_nay or date.today()
    y, m = _cuoi_ky(ky)
    return (y, m) < (hom_nay.year, hom_nay.month)


def phap_nhan_hop_nhat(db: Session) -> list[Company]:
    """Các pháp nhân ĐANG HOẠT ĐỘNG trong phạm vi hợp nhất, theo mã.

    Sắp theo mã chứ không theo id: màn hình nhập bày các cột theo thứ tự này, và thứ tự theo id thì
    đổi mỗi lần ai đó thêm một pháp nhân – người nhập quen tay sẽ gõ nhầm cột.
    """
    q = select(Company).where(Company.active == True,  # noqa: E712 – SQLAlchemy cần so sánh, không dùng `is`
                              Company.kind.in_(KIND_HOP_NHAT)).order_by(Company.code)
    return list(db.execute(q).scalars())


def _dong(db: Session, ky: str, company_id: int, chi_tieu: str) -> KeHoachThang | None:
    return db.execute(select(KeHoachThang).where(
        KeHoachThang.ky == ky, KeHoachThang.company_id == company_id,
        KeHoachThang.chi_tieu == chi_tieu)).scalars().first()


def doc_nam(db: Session, nam: int, u: User) -> dict:
    """Bảng kế hoạch của cả một năm, ĐÃ CẮT theo phạm vi pháp nhân của người đăng nhập.

    CẮT DÒNG NẰM TRONG TRUY VẤN (SEC-02). Trả về cả bảng rồi để giao diện lọc là cách một người mở
    công cụ nhà phát triển đọc được kế hoạch của pháp nhân mình không có quyền xem – giao diện lọc
    chỉ giấu, không chặn.
    """
    cty = phap_nhan_hop_nhat(db)
    cid = PV.pham_vi(u)
    if cid is not None:
        cty = [c for c in cty if c.id == cid]

    # startswith("2026") bắt CẢ ba bề rộng: "2026-09", "2026-Q3" và "2026". Bản TC-41 dùng
    # startswith("2026-") nên ô NĂM (mã đúng bốn chữ số, không có gạch) lọt ra ngoài — một dòng có
    # thật trong sổ mà bảng không hiện, và người nhập sẽ gõ lại rồi tưởng mình chưa nhập.
    q = select(KeHoachThang).where(KeHoachThang.ky.startswith(f"{nam:04d}"))
    q = PV.loc(q, KeHoachThang, u)
    rows = list(db.execute(q).scalars())
    tra = {(r.ky, r.company_id, r.chi_tieu): r for r in rows}

    hom_nay = date.today()

    def _dong_ky(ky: str, ten: str) -> dict:
        o = []
        for c in cty:
            for ma in CHI_TIEU:
                r = tra.get((ky, c.id, ma))
                o.append({
                    "company_id": c.id, "company_ma": c.code, "company_ten": c.name,
                    "chi_tieu": ma, "chi_tieu_ten": CHI_TIEU[ma],
                    # Chưa nhập thì KHÔNG CÓ DÒNG, và ở đây nó là None – không phải 0.
                    "gia_tri": None if r is None else float(r.gia_tri),
                    "ly_do_sua": "" if r is None else r.ly_do_sua,
                    "nguoi_nhap": "" if r is None else r.nguoi_nhap,
                    "sua_luc": None if r is None else r.sua_luc,
                    "so_lan_sua_muon": 0 if r is None else r.so_lan_sua_muon,
                })
        return {"ky": ky, "ten": ten, "be_rong": be_rong(ky),
                "da_khep": da_khep(ky, hom_nay), "o": o}

    # THỨ TỰ BÀY: năm → bốn quý → mười hai tháng. Rộng trước hẹp sau, vì đó là thứ tự lập kế
    # hoạch thật: Hội đồng giao chỉ tiêu năm, rồi Kế toán phân bổ xuống quý và tháng. Bày ngược
    # lại thì người nhập gõ 12 ô tháng xong mới gặp ô năm và phải cộng lại bằng tay.
    ky_nam = f"{nam:04d}"
    ds = [_dong_ky(ky_nam, f"Năm {nam}")]
    ds += [_dong_ky(f"{nam:04d}-Q{q}", f"Quý {q}") for q in range(1, 5)]
    ds += [_dong_ky(f"{nam:04d}-{m:02d}", f"Tháng {m}") for m in range(1, 13)]

    return {
        "nam": nam,
        "chi_tieu": [{"ma": k, "ten": v} for k, v in CHI_TIEU.items()],
        "phap_nhan": [{"id": c.id, "ma": c.code, "ten": c.name} for c in cty],
        "ky": ds,
        # Giữ khoá `thang` cho đúng hợp đồng cũ với màn hình: chỉ 12 dòng tháng.
        "thang": [d for d in ds if d["be_rong"] == BE_RONG_THANG],
        "doi_chieu": doi_chieu_be_rong(db, nam, u),
        "pham_vi": PV.mo_ta(db, u),
        "dai_toi_thieu_ly_do": DAI_TOI_THIEU_LY_DO,
        "nam_chon_duoc": cac_nam(hom_nay),
    }


def cac_nam(hom_nay: date | None = None) -> list[int]:
    """Các năm ô chọn bày ra: từ NAM_DAU tới năm hiện tại.

    Anh Tuấn chốt 16/9/2026: "từ 2026 đến năm hiện tại". VTOS không có sổ trước 2026, nên bày năm
    2025 ra chỉ để ai bấm vào cũng gặp một hình rỗng — và một ô chọn dẫn tới chỗ trống thì lần sau
    người ta thôi bấm.
    """
    nay = (hom_nay or date.today()).year
    return list(range(NAM_DAU, max(NAM_DAU, nay) + 1))


def doi_chieu_be_rong(db: Session, nam: int, u: User) -> list[dict]:
    """Chỉ tiêu NĂM so với TỔNG 12 THÁNG, và mỗi QUÝ so với ba tháng của nó.

    KHÔNG TỰ SỬA CHỖ LỆCH — chỉ hiện ra. Hội đồng giao 230 tỷ trong khi Kế toán phân bổ tháng cộng
    lại ra 226 thì phần chênh 4 tỷ là dư địa CỐ Ý, không phải lỗi nhập. Tự cộng ngược hay tự chia
    đều là xoá mất một quyết định quản trị và thay bằng một phép tính.

    Nhưng lệch mà KHÔNG AI THẤY thì mới là chỗ hỏng: sáu tháng sau không ai nhớ 4 tỷ ấy là dư địa
    hay là một ô gõ thiếu số 0. Nên dòng đối chiếu đứng ngay trên bảng nhập.

    Bỏ qua phần chưa đủ: thiếu một tháng thì tổng 12 tháng chưa tồn tại (LUẬT 1), và so một con số
    với một con số chưa tồn tại là so với chỗ trống.
    """
    ra = []
    for ma, ten in CHI_TIEU.items():
        for ky_rong, cac_hep, nhan in (
            (f"{nam:04d}", [f"{nam:04d}-{m:02d}" for m in range(1, 13)], "12 tháng"),
            *[(f"{nam:04d}-Q{q}",
               [f"{nam:04d}-{m:02d}" for m in range((q - 1) * 3 + 1, (q - 1) * 3 + 4)],
               "3 tháng") for q in range(1, 5)],
        ):
            rong = hop_nhat(db, ky_rong)[ma]
            hep = [hop_nhat(db, k)[ma] for k in cac_hep]
            if not rong["du"] or any(not h["du"] for h in hep):
                continue
            tong = sum(float(h["gia_tri"]) for h in hep)
            chenh = float(rong["gia_tri"]) - tong
            if chenh:
                ra.append({"ky": ky_rong, "chi_tieu": ma, "chi_tieu_ten": ten,
                           "chi_tieu_giao": float(rong["gia_tri"]), "tong_hep": tong,
                           "chenh": chenh, "nhan_hep": nhan})
    return ra


def ghi(db: Session, ky: str, company_id: int, chi_tieu: str, gia_tri: float | None,
        ly_do: str, u: User) -> dict:
    """Lưu MỘT ô kế hoạch. `gia_tri=None` nghĩa là XOÁ ô ấy, không phải đặt nó bằng 0.

    Trả về {"trang_thai": "them"|"sua"|"xoa"|"khong_doi", ...}. Gọi hàm này với đúng giá trị đang có
    thì nó KHÔNG ghi gì và KHÔNG tính là một lần sửa muộn – nếu không, mỗi lần người dùng bấm Lưu cả
    bảng là mọi dòng tăng thêm một lần sửa, và cột đếm ấy lập tức vô nghĩa.

    Ném ValueError kèm câu tiếng Việt cho mọi trường hợp từ chối; cửa HTTP đổi nó thành 422.
    """
    if not hop_le_ky(ky):
        raise ValueError(f"Kỳ '{ky}' không đúng dạng YYYY-MM.")
    if chi_tieu not in CHI_TIEU:
        raise ValueError(f"Chỉ tiêu '{chi_tieu}' không nằm trong danh sách "
                         f"{list(CHI_TIEU)}.")
    if gia_tri is not None and gia_tri < 0:
        # Lợi nhuận kế hoạch ÂM thì đã chặn ở đây, và đó là có chủ ý: lập kế hoạch lỗ là một quyết
        # định của Hội đồng quản trị, không phải con số Kế toán gõ vào một mình. Khi nào có nghiệp
        # vụ ấy thì mở, kèm cửa duyệt riêng.
        raise ValueError("Giá trị kế hoạch không được âm.")

    cty = db.get(Company, company_id)
    if cty is None or not cty.active or cty.kind not in KIND_HOP_NHAT:
        raise ValueError("Pháp nhân không tồn tại, đã ngừng hoạt động, hoặc không nằm trong "
                         "phạm vi hợp nhất.")
    cid = PV.pham_vi(u)
    if cid is not None and cid != company_id:
        raise ValueError("Phiên đăng nhập này chỉ lập kế hoạch cho pháp nhân của mình.")

    khep = da_khep(ky)
    ly_do = (ly_do or "").strip()
    r = _dong(db, ky, company_id, chi_tieu)
    cu = None if r is None else float(r.gia_tri)

    if cu == gia_tri:
        return {"trang_thai": "khong_doi", "ky": ky, "company_id": company_id,
                "chi_tieu": chi_tieu, "gia_tri": gia_tri}

    if khep and len(ly_do) < DAI_TOI_THIEU_LY_DO:
        raise ValueError(LY_DO_THIEU)

    ten = getattr(u, "username", "") or getattr(u, "email", "") or ""
    luc = datetime.now()

    if gia_tri is None:
        db.delete(r)
        trang_thai = "xoa"
    elif r is None:
        db.add(KeHoachThang(ky=ky, company_id=company_id, chi_tieu=chi_tieu, gia_tri=gia_tri,
                            ly_do_sua=ly_do if khep else "", nguoi_nhap=ten,
                            sua_luc=luc, tao_luc=luc,
                            so_lan_sua_muon=1 if khep else 0))
        trang_thai = "them"
    else:
        r.gia_tri = gia_tri
        r.nguoi_nhap = ten
        r.sua_luc = luc
        if khep:
            r.ly_do_sua = ly_do
            r.so_lan_sua_muon = (r.so_lan_sua_muon or 0) + 1
        trang_thai = "sua"

    # Nhật ký bất biến ghi CẢ giá trị cũ lẫn mới. Chỉ ghi giá trị mới thì đọc nhật ký ba tháng sau
    # biết được ai sửa mà không biết sửa từ bao nhiêu – tức là không biết sửa nhiều hay ít.
    R.audit(db, actor=ten, role=getattr(u, "role", ""),
            action=f"ke_hoach_thang.{trang_thai}",
            entity=f"ke_hoach_thang:{ky}:{cty.code}:{chi_tieu}",
            before={"gia_tri": cu}, after={"gia_tri": gia_tri, "ly_do": ly_do,
                                           "thang_da_khep": khep})
    return {"trang_thai": trang_thai, "ky": ky, "company_id": company_id,
            "chi_tieu": chi_tieu, "gia_tri": gia_tri, "thang_da_khep": khep}


def hop_nhat(db: Session, ky: str, nho: dict | None = None) -> dict:
    """Kế hoạch HỢP NHẤT của một tháng – hoặc `None` kèm danh sách pháp nhân còn thiếu.

    TC-64 · `nho` là chỗ nhớ của MỘT lần dựng bảng (xem `ket_qua_kinh_doanh.bang`). Bảng Kết quả
    kinh doanh hỏi lại cùng một tháng cho từng chỉ tiêu có kế hoạch; có `nho` thì hỏi một lần.
    Không truyền `nho` thì hàm chạy y như trước.

    Đây là hàm màn hình Chủ tịch gọi. Xem LUẬT 1 ở đầu tệp: thiếu một pháp nhân là chưa có kế hoạch,
    không phải là kế hoạch nhỏ hơn.

    Không cắt theo phạm vi người dùng – hàm này trả về con số HỢP NHẤT, và ai gọi được nó thì cửa
    gọi đã chặn theo vai trò rồi (màn hình 01 chỉ mở cho Ban lãnh đạo). Cắt phạm vi ở đây sẽ cho ra
    một "số hợp nhất" chỉ gồm một pháp nhân, đúng cái bẫy mà LUẬT 1 đang chặn.
    """
    khoa = ("kh.hop_nhat", ky)
    if nho is not None and khoa in nho:
        return nho[khoa]
    cty = phap_nhan_hop_nhat(db)
    ra: dict = {"ky": ky, "so_phap_nhan": len(cty)}
    for ma in CHI_TIEU:
        thieu, tong = [], 0.0
        for c in cty:
            r = _dong(db, ky, c.id, ma)
            if r is None:
                thieu.append(c.name)
            else:
                tong += float(r.gia_tri)
        du = len(cty) > 0 and not thieu
        ra[ma] = {"gia_tri": tong if du else None, "du": du, "thieu": thieu}
    if nho is not None:
        nho[khoa] = ra
    return ra


def ty_le_dat(thuc_hien: float | None, ke_hoach: float | None) -> float | None:
    """Tỉ lệ đạt kế hoạch. `None` khi thiếu một trong hai vế, hoặc khi kế hoạch bằng 0.

    Kế hoạch bằng 0 trả về None chứ không trả về vô cùng hay 0: "đạt bao nhiêu phần trăm của 0" là
    một câu không có nghĩa, và mọi con số trả ra cho câu ấy đều gây hiểu nhầm.
    """
    if thuc_hien is None or ke_hoach is None or ke_hoach == 0:
        return None
    return thuc_hien / ke_hoach


def theo_thang(db: Session, nam: int) -> list[dict]:
    """Mười hai tháng: kế hoạch hợp nhất của từng tháng, cho biểu đồ trên màn hình nhập.

    Chỉ trả kế hoạch, KHÔNG trả thực hiện. Thực hiện nằm ở sổ quyết toán và ở báo cáo kết quả kinh
    doanh – hai nguồn khác nhau cho doanh thu và cho lợi nhuận – nên ghép chúng ở đây là dựng một
    phép tính thứ hai cho câu hỏi mà màn hình 01 đã có phép tính. Một câu hỏi, một phép tính.
    """
    ra = []
    for m in range(1, 13):
        ky = f"{nam:04d}-{m:02d}"
        h = hop_nhat(db, ky)
        ra.append({"ky": ky, **{ma: h[ma] for ma in CHI_TIEU}})
    return ra
