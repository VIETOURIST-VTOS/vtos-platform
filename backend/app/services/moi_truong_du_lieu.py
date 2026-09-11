# -*- coding: utf-8 -*-
"""PQ-4 · Quy tắc phân biệt DỮ LIỆU THỬ NGHIỆM với DỮ LIỆU THẬT.

VÌ SAO, VÀ VÌ SAO LÀ BÂY GIỜ

Bản đề xuất hoàn thiện VTOS mở đầu bằng câu "Dữ liệu hiện tại là dữ liệu thử nghiệm". Đo ngày
10/9/2026 trên 78 bảng đọc được: KHÔNG bảng nào có chỗ ghi câu ấy xuống. Trong khi hệ thống đang
giữ 1.258 chuyến, 10.074 booking và 25.728 bút toán đều là số thử.

Đây là việc rẻ nhất hôm nay và đắt nhất sau ba tháng. Hôm nay chỉ cần một cột và một mốc ngày:
mọi thứ đang có đều là thử, nên đóng dấu hàng loạt không thể sai. Sau ngày số thật đầu tiên vào mà
vẫn chưa có cột, hai loại dữ liệu trộn vào nhau và KHÔNG TÁCH LẠI ĐƯỢC bằng máy – chỉ còn cách hỏi
từng người xem dòng này ai nhập, để làm gì. Khi ấy mọi báo cáo đều phải kèm một câu giải thích
bằng miệng, mà câu giải thích bằng miệng thì không đi vào biên bản kiểm toán được.

BA QUYẾT ĐỊNH TRONG TỆP NÀY, VÀ LÝ DO CỦA TỪNG CÁI

1. Cờ ĐÓNG DẤU LÚC TẠO, KHÔNG SỬA ĐƯỢC VỀ SAU.
   Nếu sửa được thì sớm muộn có người "dọn dẹp" bằng cách đổi nhãn dữ liệu thử thành thật – và
   khi ấy trong sổ có những con số chưa bao giờ được ai nhập đúng quy trình, mang nhãn nói rằng
   đã. Đó tệ hơn hẳn tình trạng hiện nay, vì hiện nay ít nhất ai cũng biết cả kho là số thử.

2. KHÔNG PHẢI BẢNG NÀO CŨNG MANG CỜ. Ba nhóm, ba cách xử lý khác nhau – xem ba danh sách bên dưới.
   Đóng dấu tràn lan sẽ làm hỏng danh mục: một nhà cung cấp khai trong lúc chạy thử vẫn là một nhà
   cung cấp có thật, gắn nhãn "thử nghiệm" cho nó là tự tay làm dữ liệu danh mục thành vô dụng.

3. MỐC NGÀY VẬN HÀNH THẬT LÀ MỘT THAM SỐ CHÍNH SÁCH, KHÔNG PHẢI HẰNG SỐ TRONG MÃ.
   Đi qua đúng cửa tham số đã có: hiệu lực theo ngày và phải đủ HAI CHỮ KÝ. Viết cứng vào mã thì
   mốc ấy mang chữ ký của người viết mã chứ không của người có thẩm quyền.

RANH GIỚI

Tệp này chỉ KHAI LUẬT. Việc thêm cột vào bảng và đóng dấu cho dữ liệu đang có là VPM-1, thuộc làn
Viết phần mềm. Việc lọc báo cáo theo cờ đi cùng VPM-1.
"""
from __future__ import annotations

from datetime import date, datetime

THU_NGHIEM = "thu_nghiem"
THAT = "that"

NHAN = {THU_NGHIEM: "Dữ liệu thử nghiệm", THAT: "Dữ liệu vận hành thật"}

# ---------------------------------------------------------------------------------------------
# HAI MỐC, KHÔNG PHẢI MỘT – quyết định của Chủ tịch ngày 11/9/2026
# ---------------------------------------------------------------------------------------------
# Bản đầu của tệp này (10/9) chỉ có MỘT mốc và một chế độ cho cả hệ thống: trước mốc là thử, từ
# mốc là thật. Quyết định của Chủ tịch làm bản ấy sai, và sai theo đúng chiều nguy hiểm nhất:
#
#     mốc vận hành thật      01/12/2026
#     nhưng từ 01/10/2026    đổ dữ liệu THẬT từ Vietrip về hàng ngày
#
# Với một mốc duy nhất, hai tháng dữ liệu Vietrip có thật – booking thật, tiền thật của khách
# thật – sẽ bị đóng dấu "thử nghiệm" và bị loại khỏi mọi báo cáo. Đó chính là cái hỏng mà quy tắc
# này sinh ra để chặn, chỉ là hỏng theo chiều ngược lại.
#
# Nên cờ KHÔNG do ngày quyết định một mình. Nó do cặp (NGUỒN, NGÀY) quyết định, và mỗi nguồn có
# mốc riêng: Vietrip đang là hệ thống vận hành thật của công ty, số kéo từ đó về là số thật kể từ
# ngày bật đồng bộ; còn số do nhân viên gõ trong VTOS thì vẫn là tập dượt cho tới ngày vận hành
# thật. Hai câu ấy đều đúng cùng lúc, và một cột cờ duy nhất chỉ ghi được một câu.
THAM_SO_MOC = "ngay_van_hanh_that"                 # áp cho số do NGƯỜI nhập trong VTOS
THAM_SO_MOC_NGUON = {"vietrip": "ngay_du_lieu_that_vietrip"}

# Nguồn do MÁY kéo về từ một hệ thống đang vận hành thật. Khác hẳn nguồn do người gõ: người gõ thì
# đang tập, máy kéo thì đang chép lại việc đã xảy ra thật ngoài đời.
NGUON_MAY_DONG_BO = ("vietrip",)

# Giá trị Chủ tịch nêu ngày 11/9/2026. CỐ Ý chỉ ghi lại ở đây làm tài liệu, KHÔNG dùng làm giá trị
# mặc định: nếu mã tự lấy hai ngày này thì chúng có hiệu lực mà chưa qua cửa hai chữ ký, tức là
# mang chữ ký của người viết mã. Muốn hiệu lực thì chốt qua màn hình tham số chính sách.
DE_XUAT_MOC = {
    THAM_SO_MOC: "2026-12-01",
    THAM_SO_MOC_NGUON["vietrip"]: "2026-10-01",
}


# ---------------------------------------------------------------------------------------------
# Nhóm 1 – BẢNG MANG CỜ
# ---------------------------------------------------------------------------------------------
# Tiêu chí: bảng mà một dòng của nó xuất hiện thành MỘT SỐ ĐẾM hoặc MỘT KHOẢN TIỀN trên báo cáo
# quản trị. Đó đúng là chỗ trộn dữ liệu thử vào sẽ làm sai một con số người ta đem đi họp.
BANG_MANG_CO: tuple[tuple[str, str], ...] = (
    ("tours",            "mỗi dòng là một chuyến – đếm chuyến, doanh thu, giá vốn đều từ đây"),
    ("bookings",         "đếm booking, số khách, tiền bán"),
    ("service_requests", "yêu cầu dịch vụ – đầu vào của phễu bán hàng"),
    ("leads",            "đếm lead và tỷ lệ chuyển đổi của Marketing"),
    ("bao_gia",          "báo giá đã gửi – vào tỷ lệ chốt và vào cam kết với khách"),
    ("hop_dong_khach",   "hợp đồng khách – giá trị hợp đồng vào báo cáo"),
    ("receipts",         "phiếu thu – tiền vào"),
    ("payment_requests", "đề nghị chi – tiền ra"),
    ("bank_transactions", "giao dịch ngân hàng – đối soát dòng tiền"),
    ("journal_entries",  "bút toán ghi sổ; riêng bảng này hiện có 25.728 dòng thử"),
    ("invoices",         "hoá đơn – vào doanh thu và vào tờ khai thuế"),
    ("tour_settlements", "quyết toán chuyến – doanh thu, giá vốn, lợi nhuận"),
    ("retentions",       "bảo lưu tiền khách – là nghĩa vụ phải trả"),
    ("daily_reports",    "báo cáo ngày nhân sự – vào đánh giá người thật"),
    ("care_tickets",     "phiếu chăm sóc – vào chỉ số CSKH"),
    ("complaints",       "khiếu nại – vào chỉ số CSKH và vào tiền bồi thường"),
)

# ---------------------------------------------------------------------------------------------
# Nhóm 2 – BẢNG THỪA KẾ CỜ TỪ BẢNG CHA
# ---------------------------------------------------------------------------------------------
# Không thêm cột. Một dòng chi tiết không thể "thật" khi chứng từ mẹ của nó là thử, nên để cột
# riêng là mở đường cho hai dòng nói ngược nhau – và khi chúng ngược nhau thì không ai biết tin
# cái nào.
BANG_THUA_KE: tuple[tuple[str, str, str], ...] = (
    ("journal_lines",             "journal_entries", "dòng của một bút toán"),
    ("tour_cost_lines",           "tours",           "dòng giá vốn của một chuyến"),
    ("bao_gia_ban",               "bao_gia",         "một lần gửi của báo giá"),
    ("bao_gia_dong",              "bao_gia",         "dòng chi tiết của báo giá"),
    ("tour_settlement_lines",     "tour_settlements", "dòng khách của bản quyết toán"),
    ("tour_settlement_costs",     "tour_settlements", "ô chi của một dòng khách"),
    ("tour_settlement_cost_lines", "tour_settlements", "dòng chiết tính"),
    ("tour_guide_advances",       "tour_settlements", "tiền ứng và chi của hướng dẫn viên"),
    ("tour_settlement_bookings",  "tour_settlements", "doanh thu theo booking của bản quyết toán"),
    ("tour_events",               "tours",           "nhật ký sự kiện của một chuyến"),
)

# ---------------------------------------------------------------------------------------------
# Nhóm 3 – BẢNG LỌC THEO HỒ SƠ NGUỒN
# ---------------------------------------------------------------------------------------------
# Bản thân bản ghi không thử cũng không thật – nó nói VỀ một hồ sơ khác. Một cảnh báo quá hạn
# quyết toán của chuyến thử là cảnh báo thử; cùng cảnh báo ấy cho chuyến thật là việc thật. Nên
# lọc theo hồ sơ nguồn thay vì tự mang cờ, để không phải đồng bộ hai cờ suốt đời.
BANG_LOC_THEO_NGUON: tuple[tuple[str, str], ...] = (
    ("alerts",        "cảnh báo trỏ về hồ sơ nào thì mang tính chất của hồ sơ ấy"),
    ("ngoai_le_xu_ly", "ngoại lệ đọc ra từ nơi xảy ra, không chép sang bảng riêng"),
    ("attachments",   "tệp đính kèm thuộc về hồ sơ nó gắn vào"),
)

# ---------------------------------------------------------------------------------------------
# Nhóm 4 – BẢNG KHÔNG MANG CỜ
# ---------------------------------------------------------------------------------------------
BANG_KHONG_MANG_CO: tuple[tuple[str, str], ...] = (
    ("companies",   "danh mục pháp nhân – pháp nhân có thật bất kể hệ thống đang chạy thử"),
    ("users",       "tài khoản là tài khoản thật của người thật"),
    ("employees",   "hồ sơ nhân sự của người thật"),
    ("suppliers",   "nhà cung cấp khai trong lúc chạy thử vẫn là nhà cung cấp có thật; gắn nhãn "
                    "thử nghiệm là tự tay làm hỏng danh mục"),
    ("products",    "sản phẩm tour là KHUÔN chứ không phải giao dịch; chuyến mở ra từ nó mới mang cờ"),
    ("vehicles",    "xe của công ty có thật, biển số thật, giấy tờ thật – không có xe thử nghiệm"),
    ("partners",    "danh mục đối tác, cùng lý do với nhà cung cấp: khai lúc chạy thử vẫn là đối tác thật"),
    ("params",      "tham số chính sách – chính nó giữ mốc ngày vận hành thật"),
    ("quy_tac_hach_toan", "quy ước hạch toán áp cho cả hai loại dữ liệu"),
    ("audit_log",   "nhật ký nối chuỗi băm ghi MỌI việc, kể cả việc chuyển sang vận hành thật"),
    ("ai_runs",     "nhật ký AI – ghi cả lượt chạy thử lẫn lượt thật, phân biệt bằng hồ sơ nó chạm"),
    ("intake_runs", "nhật ký nạp – ghi mọi lần nạp"),
    ("khoa_ghi",    "khoá chống chạy lại trùng, thuần kỹ thuật"),
    ("lan_chay_tac_vu", "lịch sử chạy tác vụ nền, thuần kỹ thuật"),
)


# ---------------------------------------------------------------------------------------------
# Chế độ đang chạy
# ---------------------------------------------------------------------------------------------
# Định dạng ngày người Việt gõ: DD-MM-YYYY (Chủ tịch chốt 11/9/2026). Nhận cả dấu gạch và dấu
# chéo, vì người ta gõ 01/12/2026 nhiều hơn 01-12-2026 và bắt gõ đúng một dấu là bắt sai chỗ.
#
# Vẫn nhận thêm YYYY-MM-DD, và hai dạng này KHÔNG THỂ lẫn nhau: nhóm bốn chữ số đứng đầu là năm,
# đứng cuối là năm. Nhận cả hai để những chỗ đã ghi theo dạng cũ không lặng lẽ thành "chưa chốt".
DINH_DANG_NGAY = "DD-MM-YYYY"
_VI_DU_NGAY = "01-12-2026"


def doc_ngay(v: str) -> date | None:
    """Đọc một ngày người nhập. None nghĩa là KHÔNG ĐỌC ĐƯỢC – gọi ở đâu cũng phải xử lý None.

    Không đoán: '05-06-2026' luôn là ngày 5 tháng 6, không bao giờ là ngày 6 tháng 5. Chính vì
    không đoán nên chỉ nhận đúng hai dạng trên; mọi thứ khác trả None để người nhập gõ lại, chứ
    không tự hiểu theo một cách rồi im lặng.
    """
    v = (v or "").strip().replace("/", "-")
    if not v:
        return None
    phan = v.split("-")
    if len(phan) == 3 and len(phan[0]) == 4:          # YYYY-MM-DD
        try: return date.fromisoformat("-".join(phan)[:10])
        except ValueError: return None
    if len(phan) == 3 and len(phan[2]) == 4:          # DD-MM-YYYY
        try: return date(int(phan[2]), int(phan[1]), int(phan[0]))
        except ValueError: return None
    return None


def ghi_ngay(d: date | None) -> str:
    """Viết ngày ra màn hình theo đúng dạng người ta gõ vào. Một chỗ nhập DD-MM-YYYY mà chỗ hiện
    lại ra YYYY-MM-DD thì người dùng tưởng hệ thống đã sửa số của mình."""
    return d.strftime("%d-%m-%Y") if d else ""


def _doc_moc(db, khoa: str) -> date | None:
    """Đọc một mốc qua cửa tham số chính sách. None nghĩa là CHƯA CHỐT, không phải là hôm nay."""
    from app.services.rules import get_param_text
    try:
        v = (get_param_text(db, khoa) or "").strip()
    except Exception:
        return None
    # Gõ sai định dạng thì coi như CHƯA CHỐT. Hỏng thì đóng: đoán bừa một ngày ở đây là đóng
    # dấu "thật" lên dữ liệu thử, và dấu ấy không gỡ được.
    return doc_ngay(v)


def moc_van_hanh_that(db) -> date | None:
    """Mốc cho số do NGƯỜI nhập trong VTOS."""
    return _doc_moc(db, THAM_SO_MOC)


def moc_cua_nguon(db, nguon: str) -> date | None:
    """Mốc riêng của một nguồn máy đồng bộ; nguồn không có mốc riêng thì theo mốc chung."""
    khoa = THAM_SO_MOC_NGUON.get((nguon or "").strip().lower())
    return _doc_moc(db, khoa) if khoa else moc_van_hanh_that(db)


def che_do_cua_nguon(db, nguon: str, luc: datetime | date | None = None) -> str:
    """Bản ghi đến từ nguồn này, lúc này, là thật hay thử."""
    hom_nay = (luc.date() if isinstance(luc, datetime) else luc) or date.today()
    moc = moc_cua_nguon(db, nguon)
    return THAT if (moc and hom_nay >= moc) else THU_NGHIEM


def che_do(db, luc: datetime | date | None = None) -> str:
    """Chế độ của phần NGƯỜI NHẬP – tức chế độ chung của hệ thống dưới mắt nhân viên.

    Giữ nguyên tên vì màn hình và báo cáo đang gọi tới, nhưng nghĩa nay hẹp lại: nó KHÔNG còn nói
    thay cho dữ liệu máy đồng bộ về.
    """
    return che_do_cua_nguon(db, "", luc)


def co_cua_ban_ghi_moi(db, nguon: str = "", luc: datetime | date | None = None) -> str:
    """Giá trị đóng dấu cho một bản ghi vừa tạo – theo cặp (nguồn, ngày).

    `nguon` lấy đúng giá trị hệ thống đang ghi sẵn: bộ đồng bộ Vietrip ghi source="vietrip", còn
    cửa nạp ghi "nguoi_nhap" / "nap_tep" / "ocr". Bỏ trống thì coi như người nhập – hỏng thì đóng.
    """
    return che_do_cua_nguon(db, nguon, luc)


def dang_o_giai_doan_tron(db, luc: datetime | date | None = None) -> bool:
    """Có đang ở quãng mà một nguồn đã thật còn nguồn khác chưa không.

    Từ 01/10 tới 01/12/2026 là đúng quãng ấy. Đây là quãng dễ ra báo cáo sai nhất trong cả vòng
    đời hệ thống, vì mọi con số tổng đều đang cộng hai loại dữ liệu vào một ô.
    """
    cac = {che_do_cua_nguon(db, n, luc) for n in NGUON_MAY_DONG_BO} | {che_do(db, luc)}
    return len(cac) > 1


def muc_do_that(cac_co) -> str:
    """Một con số TỔNG HỢP chỉ là THẬT khi MỌI hồ sơ cấu thành nó đều thật.

    Ví dụ có thật sẽ xảy ra trong quãng 10–11/2026: một chuyến kéo từ Vietrip về (thật) nhưng bản
    quyết toán do điều hành viên gõ tay trong VTOS để tập (thử). Lãi lỗ của chuyến ấy KHÔNG phải
    số thật – nó là số trộn. Gọi nó là thật thì sai; gọi nó là thử thì cũng sai, vì doanh thu có
    thật. Nên phải có tên riêng cho nó, và báo cáo phải hiện đúng cái tên ấy.
    """
    bo = {c for c in cac_co if c}
    if not bo:
        return THU_NGHIEM
    if bo == {THAT}:
        return THAT
    if bo == {THU_NGHIEM}:
        return THU_NGHIEM
    return "tron"


def co_cua_du_lieu_dang_co() -> str:
    """Giá trị đóng dấu hàng loạt cho toàn bộ dữ liệu đang có trong kho.

    Là THU_NGHIEM, và câu này kiểm được chứ không phải niềm tin: chưa mốc nào được chốt lần nào,
    nên tính tới lúc đóng dấu thì chưa có một bản ghi nào ra đời trong chế độ thật.

    ĐIỀU KIỆN CỦA VIỆC ĐÓNG DẤU HÀNG LOẠT: phải chạy TRƯỚC ngày 01/10/2026. Từ ngày ấy bộ đồng bộ
    Vietrip bắt đầu kéo số thật về, và một lệnh UPDATE quét cả bảng sẽ đóng dấu "thử nghiệm" lên
    chúng. Nên VPM-1 có một hạn chót thật, không phải "làm sớm thì tốt".
    """
    return THU_NGHIEM


HAN_CHOT_DONG_DAU_HANG_LOAT = date(2026, 10, 1)


# ---------------------------------------------------------------------------------------------
# Ai được đổi cờ
# ---------------------------------------------------------------------------------------------
# Không ai, ở đợt này. Xem lý do 1 ở đầu tệp.
AI_DUOC_DOI_CO: tuple[str, ...] = ()


def doi_co_duoc_khong(vai_tro: str) -> tuple[bool, str]:
    """Luôn là không, và luôn kèm lý do cùng đường đi đúng.

    Từ chối mà không chỉ ra đường khác thì người ta sẽ đi tìm đường vòng – sửa thẳng cơ sở dữ
    liệu chẳng hạn, và đó là con đường không có nhật ký.
    """
    return False, (
        "Cờ dữ liệu được đóng dấu lúc tạo bản ghi và không sửa được về sau, kể cả Chủ tịch. "
        "Muốn hệ thống bắt đầu sinh dữ liệu thật thì chốt tham số "
        f"'{THAM_SO_MOC}' – hiệu lực theo ngày, cần đủ hai chữ ký. "
        "Bản ghi tạo trước mốc ấy giữ nhãn thử nghiệm vĩnh viễn.")


# ---------------------------------------------------------------------------------------------
# Báo cáo phải nói ra mình đang đếm gì
# ---------------------------------------------------------------------------------------------
def nhan_bao_cao(db, luc: datetime | date | None = None) -> dict:
    """Câu mà mọi báo cáo phải hiện, kèm dữ kiện để màn hình tự dựng câu khác nếu cần.

    Một báo cáo lặng lẽ đếm dữ liệu thử rồi trình ra như số thật là đúng thứ quy tắc này sinh ra
    để chặn. Nên khi chưa chốt mốc, báo cáo KHÔNG được im lặng.
    """
    moc = moc_van_hanh_that(db)
    cd = che_do(db, luc)
    moc_nguon = {n: moc_cua_nguon(db, n) for n in NGUON_MAY_DONG_BO}

    if dang_o_giai_doan_tron(db, luc):
        # Quãng trộn có HAI hình dạng, và câu mô tả phải đúng hình dạng đang xảy ra. Bản đầu chỉ
        # viết cho hình dạng thứ nhất rồi lấy phần tử [0] của một danh sách có thể rỗng – phép thử
        # đỏ ngay ở hình dạng thứ hai. Ghi lại vì đây là kiểu sai chỉ lộ ra ở một cấu hình mốc cụ
        # thể, mà cấu hình ấy thì hoàn toàn có thể xảy ra thật.
        da_that = [n for n in NGUON_MAY_DONG_BO if che_do_cua_nguon(db, n, luc) == THAT]
        chua_that = [n for n in NGUON_MAY_DONG_BO if che_do_cua_nguon(db, n, luc) != THAT]
        cuoi = " Mỗi dòng phải tự nói nó thuộc loại nào."
        if da_that:
            cau = (f"Báo cáo này đang TRỘN hai loại dữ liệu. Số đồng bộ từ {', '.join(da_that)} là "
                   f"DỮ LIỆU THẬT (từ {moc_nguon[da_that[0]].isoformat()}); số do nhân viên nhập "
                   f"trong VTOS vẫn là DỮ LIỆU THỬ NGHIỆM"
                   + (f" cho tới {moc.isoformat()}." if moc else ", chưa chốt mốc vận hành thật."))
        else:
            cau = (f"Báo cáo này đang TRỘN hai loại dữ liệu. Số do nhân viên nhập trong VTOS là "
                   f"DỮ LIỆU THẬT (từ {moc.isoformat()}); số đồng bộ từ "
                   f"{', '.join(chua_that)} vẫn là DỮ LIỆU THỬ NGHIỆM vì chưa chốt mốc cho nguồn đó.")
        return {
            "che_do": "tron", "moc": moc, "moc_nguon": moc_nguon, "phai_hien": True,
            "cau": cau + cuoi,
        }

    if cd == THU_NGHIEM:
        return {
            "che_do": cd, "moc": moc, "moc_nguon": moc_nguon, "phai_hien": True,
            "cau": ("Toàn bộ số liệu trên báo cáo này là DỮ LIỆU THỬ NGHIỆM. "
                    "Hệ thống chưa chốt mốc ngày vận hành thật."
                    if moc is None else
                    f"Số liệu trên báo cáo này là DỮ LIỆU THỬ NGHIỆM. "
                    f"Mốc vận hành thật đã chốt: {moc.isoformat()}, chưa tới."),
        }
    return {
        "che_do": cd, "moc": moc, "moc_nguon": moc_nguon, "phai_hien": True,
        "cau": (f"Báo cáo đếm dữ liệu vận hành thật, từ {moc.isoformat()}. "
                "Dữ liệu thử nghiệm trước mốc này không tính vào."),
    }


# ---------------------------------------------------------------------------------------------
# Tự soi khai báo
# ---------------------------------------------------------------------------------------------
def moi_bang_da_khai() -> dict[str, str]:
    """Bảng -> nhóm. Dùng cho bộ kiểm của làn Kiểm soát: bảng nghiệp vụ nào chưa khai thì đỏ."""
    ra: dict[str, str] = {}
    for t, _ in BANG_MANG_CO:
        ra[t] = "mang_co"
    for t, _cha, _ly in BANG_THUA_KE:
        ra[t] = "thua_ke"
    for t, _ in BANG_LOC_THEO_NGUON:
        ra[t] = "loc_theo_nguon"
    for t, _ in BANG_KHONG_MANG_CO:
        ra[t] = "khong_mang_co"
    return ra


def bang_cha(ten_bang: str) -> str:
    for t, cha, _ in BANG_THUA_KE:
        if t == ten_bang:
            return cha
    return ""
