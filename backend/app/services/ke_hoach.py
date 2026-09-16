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

LY_DO_THIEU = (f"Tháng này đã khép. Sửa kế hoạch của một tháng đã qua phải kèm lý do ít nhất "
               f"{DAI_TOI_THIEU_LY_DO} ký tự – lý do được lưu ngay trên dòng và vào nhật ký.")


def ky_cua(d: date) -> str:
    """Ngày → mã kỳ tháng, ví dụ 2026-09-14 → '2026-09'."""
    return f"{d.year:04d}-{d.month:02d}"


def hop_le_ky(ky: str) -> bool:
    """Đúng dạng YYYY-MM và tháng nằm trong 1..12.

    Kiểm ở đây chứ không để cơ sở dữ liệu tự chịu: cột là chuỗi, nên '2026-13' hay 'thang sau' lưu
    được hết, và một dòng như thế thì mọi phép so sánh kỳ sau đó âm thầm trả về sai.
    """
    phan = str(ky).split("-")
    if len(phan) != 2 or len(phan[0]) != 4 or len(phan[1]) != 2:
        return False
    if not phan[0].isdigit() or not phan[1].isdigit():
        return False
    return 1 <= int(phan[1]) <= 12


def da_khep(ky: str, hom_nay: date | None = None) -> bool:
    """Kỳ này đã qua chưa. Xem LUẬT 2 ở đầu tệp về việc vì sao dùng mốc lịch."""
    return ky < ky_cua(hom_nay or date.today())


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

    q = select(KeHoachThang).where(KeHoachThang.ky.startswith(f"{nam:04d}-"))
    q = PV.loc(q, KeHoachThang, u)
    rows = list(db.execute(q).scalars())
    tra = {(r.ky, r.company_id, r.chi_tieu): r for r in rows}

    hom_nay = date.today()
    thang = []
    for m in range(1, 13):
        ky = f"{nam:04d}-{m:02d}"
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
        thang.append({"ky": ky, "da_khep": da_khep(ky, hom_nay), "o": o})

    return {
        "nam": nam,
        "chi_tieu": [{"ma": k, "ten": v} for k, v in CHI_TIEU.items()],
        "phap_nhan": [{"id": c.id, "ma": c.code, "ten": c.name} for c in cty],
        "thang": thang,
        "pham_vi": PV.mo_ta(db, u),
        "dai_toi_thieu_ly_do": DAI_TOI_THIEU_LY_DO,
    }


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


def hop_nhat(db: Session, ky: str) -> dict:
    """Kế hoạch HỢP NHẤT của một tháng – hoặc `None` kèm danh sách pháp nhân còn thiếu.

    Đây là hàm màn hình Chủ tịch gọi. Xem LUẬT 1 ở đầu tệp: thiếu một pháp nhân là chưa có kế hoạch,
    không phải là kế hoạch nhỏ hơn.

    Không cắt theo phạm vi người dùng – hàm này trả về con số HỢP NHẤT, và ai gọi được nó thì cửa
    gọi đã chặn theo vai trò rồi (màn hình 01 chỉ mở cho Ban lãnh đạo). Cắt phạm vi ở đây sẽ cho ra
    một "số hợp nhất" chỉ gồm một pháp nhân, đúng cái bẫy mà LUẬT 1 đang chặn.
    """
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
