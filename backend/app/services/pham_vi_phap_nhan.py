"""Phạm vi pháp nhân của phiên đăng nhập (Đợt 2 – Robot Phân quyền, mục P6).

Vấn đề phải giải: Vietourist Holdings có nhiều pháp nhân trong phạm vi hợp nhất. Một người của
công ty vận tải không có việc gì phải nhìn thấy danh sách tour của công ty lữ hành, và ngược lại.
Nhưng cái nguy hiểm hơn quyền xem là **báo cáo**: nếu một hồ sơ chưa xác định pháp nhân mà hệ thống
tự gộp về công ty mẹ cho gọn màn hình, thì một khoản của công ty này chạy sang báo cáo của công ty
kia, và không có cách nào phát hiện lại về sau vì không còn dấu vết nào nói rằng nó từng "chưa biết".

Vì vậy module này có đúng ba quy tắc, và cả ba đều nói "không":

1. **Không gộp im lặng.** Hồ sơ company_id rỗng là CHƯA XÁC ĐỊNH. Nó không thuộc công ty mẹ, không
   thuộc công ty của người đang xem. `dem()` luôn trả về HAI con số tách rời; không có hàm nào trong
   file này cộng chúng lại.

2. **Không giấu.** Hồ sơ chưa xác định vẫn nằm trong danh sách người dùng nhìn thấy, có nhãn
   `chua_gan`. Lọc nó ra khỏi màn hình nghe có vẻ "an toàn" nhưng thực chất là làm nó biến mất khỏi
   mọi con mắt, và người duy nhất còn có thể gán nó thì không còn nhìn thấy nó để mà gán.

   ĐÍNH CHÍNH 08/9/2026: bản đầu của đoạn này viết "1.200 tour nhập từ Vietrip đều chưa có pháp
   nhân". ĐO trên hệ thống thật sau khi phát hành: 0 hồ sơ chưa gán trên cả năm loại – 1.258 tour,
   10.074 booking, 5.664 phiếu thu, 4.659 đề nghị chi, 25.728 chứng từ ghi sổ đều đã có pháp nhân.
   Con số kia là suy đoán chưa đo, và nó sai. Quy tắc thì vẫn giữ: nó không tốn gì khi danh sách
   rỗng, và đúng vào ngày có hồ sơ đầu tiên chưa gán thì nó đã đứng sẵn ở đó.

3. **Không khoá cửa bằng một cột chưa ai điền.** `users.company_id` được thêm ngày 07/9/2026,
   nullable, không có bước điền sẵn. Nếu bật lọc cứng ngay thì mọi tài khoản chưa gán sẽ thấy màn
   hình trống trơn và cả công ty đứng lại trong một buổi sáng. Tài khoản chưa gán pháp nhân vì thế
   vẫn thấy toàn bộ – NHƯNG nó không được im lặng: `/access/gaps` đã đếm sẵn nhóm "chưa gán pháp
   nhân", và `/auth/me` nay trả `pham_vi` để màn hình nói thẳng ra rằng phiên này chưa bị giới hạn.
   Siết được hay không là việc của người quản trị đi gán, không phải việc của đoạn mã này đoán.
"""
from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.models.core import User, Company

# Vai trò làm việc trên phạm vi hợp nhất: chủ tịch, tổng giám đốc, ban kiểm soát, kế toán, CNTT.
# Kế toán nằm ở đây vì báo cáo hợp nhất và loại trừ giao dịch nội bộ đòi hỏi nhìn cả hai bên của
# một giao dịch nội bộ; cắt một bên đi thì không loại trừ được, mà không loại trừ được thì doanh thu
# hợp nhất bị thổi lên đúng bằng phần giao dịch giữa các công ty trong nhà.
TOAN_TAP_DOAN = ("chutich", "tgd", "bks", "ketoan", "cntt")

CHUA_GAN = "chua_gan"


def pham_vi(u: User) -> int | None:
    """Pháp nhân mà phiên đăng nhập này bị giới hạn vào. None = không bị giới hạn.

    None xảy ra trong hai trường hợp khác hẳn nhau về ý nghĩa, và `ly_do_khong_gioi_han()` phân biệt
    chúng: vai trò làm việc toàn tập đoàn (đúng thiết kế), và tài khoản chưa được gán pháp nhân
    (chưa làm xong, phải đi gán).
    """
    if getattr(u, "role", "") in TOAN_TAP_DOAN:
        return None
    return getattr(u, "company_id", None)


def ly_do_khong_gioi_han(u: User) -> str:
    if pham_vi(u) is not None:
        return ""
    if getattr(u, "role", "") in TOAN_TAP_DOAN:
        return "vai_tro_toan_tap_doan"
    return "tai_khoan_chua_gan_phap_nhan"


def bi_gioi_han(u: User) -> bool:
    return pham_vi(u) is not None


def loc(q, model, u: User):
    """Thêm điều kiện phạm vi pháp nhân vào một truy vấn danh sách.

    Giữ lại hồ sơ CHƯA XÁC ĐỊNH – xem quy tắc 2 ở đầu file. Model không có cột company_id thì trả về
    nguyên truy vấn: im lặng bỏ qua ở đây là đúng, vì ép mọi bảng phải có pháp nhân sẽ làm hỏng các
    bảng danh mục dùng chung (ngân hàng, tài khoản kế toán, tham số) vốn không thuộc pháp nhân nào.
    """
    cid = pham_vi(u)
    if cid is None:
        return q
    col = getattr(model, "company_id", None)
    if col is None:
        return q
    return q.where(or_(col == cid, col.is_(None)))


def nhan(company_id: int | None, u: User) -> str:
    """Nhãn dán lên từng dòng để màn hình không phải đoán: '' hoặc 'chua_gan'."""
    return CHUA_GAN if company_id is None else ""


def dem(db: Session, model, u: User) -> dict:
    """Đếm theo phạm vi, trả về HAI con số tách rời – không có tổng.

    Cố tình không trả về khoá "tong". Ai cần tổng thì phải tự cộng, và lúc gõ phép cộng đó người ta
    buộc phải nhìn thấy mình đang cộng số của pháp nhân với số chưa biết thuộc về ai.
    """
    col = getattr(model, "company_id", None)
    if col is None:
        return {"cua_phap_nhan": db.execute(select(func.count()).select_from(model)).scalar() or 0,
                "chua_gan": 0, "co_cot_phap_nhan": False}
    cid = pham_vi(u)
    chua = db.execute(select(func.count()).select_from(model).where(col.is_(None))).scalar() or 0
    if cid is None:
        cua = db.execute(select(func.count()).select_from(model).where(col.is_not(None))).scalar() or 0
    else:
        cua = db.execute(select(func.count()).select_from(model).where(col == cid)).scalar() or 0
    return {"cua_phap_nhan": cua, "chua_gan": chua, "co_cot_phap_nhan": True}


def mo_ta(db: Session, u: User) -> dict:
    """Phạm vi của phiên đăng nhập, để /auth/me trả xuống và màn hình nói thẳng cho người dùng biết.

    Người dùng phải đọc được một trong ba câu, không câu nào mơ hồ:
      – "Bạn đang xem dữ liệu của <tên pháp nhân>."
      – "Bạn đang xem dữ liệu của toàn tập đoàn." (vai trò lãnh đạo/kế toán/CNTT)
      – "Tài khoản của bạn chưa được gán pháp nhân nên đang xem toàn bộ." (trạng thái phải sửa)
    """
    cid = pham_vi(u)
    ten = ""
    if cid is not None:
        c = db.get(Company, cid)
        ten = c.name if c else f"pháp nhân #{cid}"
    ly_do = ly_do_khong_gioi_han(u)
    if cid is not None:
        cau = f"Bạn đang xem dữ liệu của {ten}."
    elif ly_do == "vai_tro_toan_tap_doan":
        cau = "Bạn đang xem dữ liệu của toàn tập đoàn."
    else:
        cau = "Tài khoản của bạn chưa được gán pháp nhân nên đang xem toàn bộ dữ liệu."
    return {"company_id": cid, "company_name": ten, "bi_gioi_han": cid is not None,
            "ly_do_khong_gioi_han": ly_do, "cau_hien_thi": cau}


def bang_co_cot_phap_nhan() -> list:
    """MỌI bảng trong hệ thống có cột company_id, đọc thẳng từ mô hình.

    Vì sao phải quét từ mô hình chứ không viết tay một danh sách: bảng đối chiếu pháp nhân
    (company_scope.KINDS) chỉ kể tên NĂM loại hồ sơ – tour, booking, phiếu thu, đề nghị chi, chứng từ
    ghi sổ. Đo ngày 09/9/2026 thì hệ thống có HAI MƯƠI bảng mang cột ấy. Nghĩa là câu "không còn hồ sơ
    nào chưa gán pháp nhân" chỉ đúng cho năm bảng, và mười lăm bảng còn lại không ai nhìn tới.

    Một cột pháp nhân không ai nhìn tới thì hoặc luôn rỗng, hoặc mang giá trị do mã tự đặt mà không ai
    kiểm – và cả hai đều dẫn tới cùng một chỗ: đến kỳ hợp nhất, phần dữ liệu ấy không thuộc công ty
    nào cả. Danh sách viết tay sẽ lạc hậu ngay lần thêm bảng sau; quét từ mô hình thì không.
    """
    from app.models.core import Base
    import pkgutil, importlib
    import app.models as M
    for _, ten, _ in pkgutil.iter_modules(M.__path__):
        importlib.import_module(f"app.models.{ten}")
    ra = []
    for m in Base.registry.mappers:
        cls = m.class_
        if "company_id" in cls.__table__.c:
            ra.append(cls)
    return sorted(ra, key=lambda c: c.__tablename__)


def do_phu_kin(db: Session) -> dict:
    """Mỗi bảng có cột pháp nhân: bao nhiêu dòng đã gán, bao nhiêu chưa – ĐO trên dữ liệu thật.

    Trả về ba nhóm tách rời, vì ba nhóm là ba loại việc khác nhau:
      – da_gan_het   : không còn gì phải làm
      – con_chua_gan : có người phải đi gán, và bảng nói rõ còn bao nhiêu dòng
      – rong         : bảng chưa có dòng nào, chưa kết luận được gì

    KHÔNG cộng ba nhóm thành một tỷ lệ phần trăm: một con số 95% làm người đọc yên tâm đúng vào lúc
    5% còn lại là toàn bộ một phân hệ.
    """
    from sqlalchemy import func as F
    da_gan_het, con_chua_gan, rong = [], [], []
    for cls in bang_co_cot_phap_nhan():
        col = cls.__table__.c["company_id"]
        tong = db.execute(select(F.count()).select_from(cls)).scalar() or 0
        chua = db.execute(select(F.count()).select_from(cls).where(col.is_(None))).scalar() or 0
        dong = {"bang": cls.__tablename__, "lop": cls.__name__, "tong": tong, "chua_gan": chua,
                "da_gan": tong - chua}
        (rong if tong == 0 else (con_chua_gan if chua else da_gan_het)).append(dong)
    return {
        "da_gan_het": da_gan_het,
        "con_chua_gan": sorted(con_chua_gan, key=lambda d: -d["chua_gan"]),
        "rong": rong,
        "dem": {"so_bang": len(da_gan_het) + len(con_chua_gan) + len(rong),
                "bang_da_xong": len(da_gan_het), "bang_con_viec": len(con_chua_gan),
                "bang_rong": len(rong),
                "dong_chua_gan": sum(d["chua_gan"] for d in con_chua_gan)},
        "ghi_chu": ("Quét từ mô hình nên không lạc hậu khi thêm bảng. Bảng đối chiếu pháp nhân ở màn "
                    "hình Công ty chỉ theo dõi năm loại hồ sơ chính; danh sách này cho thấy phần còn "
                    "lại. Dòng chưa gán KHÔNG thuộc công ty mẹ – nó là 'chưa xác định', và đến kỳ hợp "
                    "nhất thì nó không thuộc công ty nào cả."),
    }


# =============================================================================================
# PQ-6 (11/9/2026) · Khai chỗ nào PHẢI lọc, và siết tài khoản chưa gán kể từ ngày vận hành thật
# =============================================================================================
# Ba quy tắc ở đầu tệp viết ngày 08/9 vẫn đúng nguyên. Phần này bổ sung hai thứ chúng còn thiếu,
# và cả hai đều bắt nguồn từ một phép đo ngày 11/9/2026:
#
#     22 mô hình mang cột company_id.  PV.loc() được gọi ĐÚNG 5 LẦN trong toàn bộ api/v1.
#
# Nghĩa là mười bảy mô hình có cột pháp nhân mà không truy vấn danh sách nào lọc theo phiên. Hàm
# loc() viết xong từ 08/9 và đúng; nó chỉ không được gọi. Một hàng rào chưa bật thì bằng không có
# hàng rào, và tệ hơn ở chỗ: nhìn vào mã thấy có hàng rào nên không ai đi dựng cái thứ hai.
#
# ĐÍNH CHÍNH con số: bản đầu của khối này ghi "16 mô hình", và 16 là con số SAI. Nó đếm trên một
# bản sao kho mã chỉ có 6/34 tệp trong app/models – bang_co_cot_phap_nhan() quét mô hình đã nạp,
# nên tệp không có mặt thì mô hình trong đó vô hình chứ không báo lỗi. Đếm lại trên đủ 34 tệp:
# 22 mô hình. Sáu mô hình lọt khỏi bản khai đầu tiên – DebtPayment, PartnerOwner, Settlement,
# SharedInvoice, VisaCase, VisaFamilyGroup – đều thuộc hai phân hệ nặng tiền và nặng định danh
# nhất (đội xe và visa). Chính phép thử "mỗi mô hình có cột pháp nhân đều phải được khai một lần"
# đã bắt được chỗ này ngay khi kho mã đủ tệp; đó là lý do phép thử ấy tồn tại.

# Mô hình PHẢI lọc theo phiên, kèm lý do. Việc NỐI loc() vào từng truy vấn là VPM-C2, thuộc làn
# Viết phần mềm; khai ra chỗ nào phải nối là việc của làn Phân quyền.
PHAI_LOC = {
    "Tour":           "chuyến của pháp nhân nào thì doanh thu và giá vốn của pháp nhân ấy",
    "Booking":        "booking mang tiền khách – nền của mọi báo cáo bán hàng",
    "Receipt":        "phiếu thu là tiền vào của một pháp nhân cụ thể",
    "PaymentRequest": "đề nghị chi là tiền ra của một pháp nhân cụ thể",
    "JournalEntry":   "bút toán ghi sổ – vào thẳng báo cáo tài chính từng pháp nhân",
    "BaoGia":         "báo giá là cam kết với khách, và cam kết do một pháp nhân đứng tên",
    "HopDongKhach":   "hợp đồng khách mang giá trị hợp đồng vào báo cáo",
    "FinContract":    "khế ước vay là nghĩa vụ nợ của đúng một pháp nhân",
    "Campaign":       "chiến dịch tiêu ngân sách của một pháp nhân",
    "MarketingBudget": "ngân sách marketing được duyệt theo pháp nhân",
    "CareTicket":     "phiếu chăm sóc gắn với khách của một pháp nhân",
    "Complaint":      "khiếu nại có thể dẫn tới tiền bồi thường",
    # V7 Đợt 3, khai khi gộp lên nhánh chính 11/9/2026. Hai bảng này mang cột pháp nhân từ lúc sinh
    # ra nhưng chưa ai khai, nên hàng rào phạm vi KHÔNG lọc chúng: một người chỉ được xem pháp nhân
    # mình vẫn đọc được sự cố và hồ sơ kiểm toán của mọi pháp nhân khác trong nhóm.
    "SuCoTour":       "sự cố của chuyến nào thì thuộc pháp nhân đứng tên chuyến ấy; kết luận sự cố "
                      "kéo theo đòi bồi hoàn nhà cung cấp hoặc mở Sự vụ với nhân viên",
    "HoSoKiemToan":   "hồ sơ kiểm toán lập cho ĐÚNG MỘT pháp nhân một kỳ – chỉ mục duy nhất của bảng "
                      "là (company_id, ky, loai); ý kiến kiểm toán của pháp nhân này không phải việc "
                      "của người phụ trách pháp nhân khác",
    # Robot A · DT-2, khai ngay khi thêm bảng (11/9/2026). Đây là bảng mà việc lọc theo pháp nhân
    # KHÔNG phải chuyện riêng tư mà là chuyện ĐÚNG–SAI: luật gốc của cả phân hệ dòng tiền là "không
    # bù trừ giữa hai pháp nhân". Một bản chốt số dư của pháp nhân A lọt sang truy vấn của người phụ
    # trách pháp nhân B là tiền của A đi trả nợ cho B ngay trên màn hình.
    "ChotSoDu":       "bản chốt số dư đã đối soát của ĐÚNG MỘT pháp nhân – nền của hàm tiền khả "
                      "dụng; lọt sang pháp nhân khác là bù trừ tiền giữa hai pháp nhân",
    "ContentItem":    "nội dung đăng dưới thương hiệu của một pháp nhân",
    # Sổ hoạt động PR (18/9/2026). Cùng lý do với ContentItem: một bài báo, một sự kiện, một vụ
    # khủng hoảng đều xảy ra DƯỚI THƯƠNG HIỆU của một pháp nhân cụ thể, và người chỉ phụ trách một
    # pháp nhân không có việc gì phải đọc vụ của pháp nhân khác.
    "PrHoatDong":     "hoạt động PR diễn ra dưới thương hiệu của một pháp nhân",
    # VPM-11, 11/9/2026. Sổ nghĩa vụ thanh toán là NỀN của bảng dòng tiền bốn mốc, và đề xuất
    # 11/9 nói thẳng: "Không mặc định tiền công ty này dùng được cho công ty khác". Không lọc ở
    # đây thì người phụ trách một pháp nhân mở bảng dòng tiền ra sẽ thấy nghĩa vụ của cả nhóm —
    # và tệ hơn con số sai, đó là một con số TRÔNG NHƯ ĐÚNG.
    "NghiaVuThanhToan": "nghĩa vụ phải trả và khoản sắp thu của ĐÚNG MỘT pháp nhân; nền của bảng "
                        "dòng tiền bốn mốc, nơi lộ chéo pháp nhân thành quyết định điều tiền sai",
    # Phòng HDV Đợt 1 · 06/10/2026. Yêu cầu HDV mang pháp nhân của chuyến, GIỮ LẠI lúc gửi chứ không
    # tra lại mỗi lần đọc. Không lọc ở đây thì người phụ trách một pháp nhân mở danh sách "chuyến
    # chưa có hướng dẫn viên" ra sẽ thấy chuyến của cả nhóm — và sẽ đi xếp người cho một chuyến không
    # phải của mình, tức là điều phối nhân sự chéo pháp nhân mà không ai quyết.
    "YeuCauHdv":      "yêu cầu hướng dẫn viên của ĐÚNG MỘT pháp nhân; nền của danh sách chuyến còn "
                      "thiếu người, nơi lộ chéo pháp nhân thành một lần điều người sai công ty",
    # Đợt 2 · 06/10/2026. Báo cáo sau tour mang pháp nhân của chuyến. Không lọc thì người phụ trách
    # một pháp nhân đọc được báo cáo chuyến của pháp nhân khác – trong đó có đánh giá nhà cung cấp,
    # sự cố và khoản chi hộ, tức là đọc được chỗ yếu của một đơn vị không phải việc của mình.
    "BaoCaoSauTour":  "báo cáo sau tour của chuyến thuộc ĐÚNG MỘT pháp nhân; bên trong có đánh giá "
                      "nhà cung cấp, sự cố và khoản chi hộ của đơn vị ấy",
    # Đợt 3 · 07/10/2026. Sổ tạm ứng mang TIỀN THẬT của một pháp nhân. Không lọc thì người phụ trách
    # một pháp nhân thấy số dư ứng của pháp nhân khác, và tệ hơn là có thể cấn trừ chéo – đúng cái
    # luật gốc "không bù trừ giữa hai pháp nhân" cấm.
    "TamUngHdv":      "khoản ứng do ĐÚNG MỘT pháp nhân chi ra; lộ chéo là mở đường cho một lần cấn "
                      "trừ tiền giữa hai pháp nhân",
    "Vehicle":        "xe thuộc sở hữu của công ty vận tải, không phải của lữ hành",

    # Sáu dòng dưới thêm ngày 11/9/2026 sau khi đếm lại trên đủ 34 tệp mô hình (xem đính chính ở
    # trên). Cả sáu nằm ở đội xe và visa – hai phân hệ mà lộ chéo pháp nhân là tốn tiền thật hoặc
    # lộ giấy tờ tùy thân thật, chứ không phải lộ một danh sách xem cho biết.
    "PartnerOwner":    "chủ xe hợp tác ký với ĐÚNG MỘT pháp nhân; nhìn nhầm danh sách đối tác của "
                       "pháp nhân khác là bước đầu của một lần cấn trừ sai công ty",
    "Settlement":      "kỳ quyết toán chủ xe là con số hai bên đã thỏa thuận và đã đóng kỳ – xem "
                       "được kỳ của pháp nhân khác là xem được giá mua dịch vụ của họ",
    "DebtPayment":     "một lần tiền đi hoặc tiền về trên công nợ đội xe, có khóa chống trả hai lần; "
                       "sổ công nợ trộn pháp nhân thì khóa ấy canh nhầm sổ",
    "SharedInvoice":   "hóa đơn dùng chung chỉ được chia cho xe có tên trên chính hóa đơn đó và "
                       "tuyệt đối không chia chéo hai pháp nhân – quy tắc sinh từ lỗi tháng 8/2026",
    "VisaCase":        "hồ sơ visa mang tên thật, ngày sinh và giấy tờ tùy thân của đương đơn; đây "
                       "là bảng mà lọc sai pháp nhân là lộ dữ liệu cá nhân, không chỉ lộ số liệu",
    "VisaFamilyGroup": "nhóm gia đình gom nhiều đương đơn và nối tới booking; thấy được nhóm là "
                       "thấy được cả quan hệ nhân thân của khách pháp nhân khác",
    "KeHoachThang":   "chỉ tiêu doanh thu và lợi nhuận tháng của MỘT pháp nhân; thấy được chỉ tiêu "
                      "của pháp nhân khác là biết trước họ cam kết gì với Hội đồng quản trị",
}

# Mô hình CÓ cột pháp nhân nhưng CỐ Ý không lọc theo phiên. Phải viết ra lý do: "cố ý không lọc" là
# lối thoát dễ nhất cho một chỗ quên nối, nên không viết được lý do nghĩa là chưa chắc đã cố ý.
CO_Y_KHONG_LOC = {
    "User":     "danh sách tài khoản chỉ mở cho quản trị (/access); lọc ở đây là giấu tài khoản "
                "khỏi đúng người có nhiệm vụ đi gán pháp nhân cho chúng",
    "Employee": "hồ sơ nhân sự do HCNS quản lý tập trung; HCNS làm việc trên cả tập đoàn",
    # TC-73 – cùng họ với User và Employee ngay trên: đây là SỔ CƠ CẤU, không phải chứng từ mang tiền.
    #
    # Cột `company_id` trên đơn vị có nghĩa thật (chi nhánh thuộc pháp nhân nào) và sẽ dùng khi cộng
    # doanh thu theo pháp nhân. Nhưng LỌC DANH MỤC theo pháp nhân đang xem thì hỏng đúng việc màn
    # hình sinh ra để làm: một nhân viên mở sơ đồ để biết team mình gồm những ai, mà cây lại bị cắt
    # theo pháp nhân đang chọn thì họ thấy một cái cây cụt và không hiểu vì sao. Tệ hơn: HC-NS là
    # người đi GÁN pháp nhân cho các đơn vị, lọc ở đây là giấu khỏi họ đúng những đơn vị chưa gán —
    # cùng cái bẫy đã ghi ở dòng User ngay trên.
    #
    # Phạm vi của người xem vẫn được cắt, nhưng cắt theo ĐƠN VỊ ĐƯỢC PHÂN CÔNG
    # (to_chuc_kd.pham_vi_xem), không theo pháp nhân. Hai trục khác nhau, cố ý không trộn.
    "DonViKD":  "sổ cơ cấu tổ chức khối Kinh doanh; cắt phạm vi theo đơn vị được phân công, "
                "không theo pháp nhân — xem to_chuc_kd.pham_vi_xem",
    # TC-81 – cùng họ với ba dòng trên: đây là DANH BẠ, không phải chứng từ mang tiền.
    #
    # Cột `company_id` có nghĩa thật (pháp nhân ký hợp đồng chính với người này) và sẽ dùng khi
    # cộng chi phí KOL theo pháp nhân. Nhưng LỌC DANH BẠ theo pháp nhân đang xem thì hỏng đúng việc
    # nó sinh ra để làm: một KOL từng chạy cho Vietourist mà lần này chạy cho pháp nhân khác vẫn là
    # cùng một người, cùng một giá tham khảo, cùng một người liên hệ. Cắt đi là buộc phòng khai lại
    # người ấy dưới pháp nhân thứ hai — tức là tự tay dựng bản trùng, đúng thứ sổ này chống.
    #
    # TIỀN THÌ VẪN CẮT. Chi phí thật đi đường đề nghị chi, và `PaymentRequest` nằm trong PHAI_LOC.
    "MktKol":   "danh bạ người hợp tác nội dung; một KOL chạy cho nhiều pháp nhân vẫn là một "
                "người — cắt danh bạ là buộc phòng khai trùng. Tiền vẫn cắt ở đề nghị chi.",
}


def mo_hinh_thieu_loc(goc_api: str = "") -> list[str]:
    """Mô hình đã khai PHẢI LỌC mà KHÔNG chỗ nào ở máy chủ gọi PV.loc cho nó.

    Đây là phép đo cho bộ kiểm của làn Kiểm soát và cho phép thử: danh sách rỗng nghĩa là đã nối
    xong; còn tên nào trong đó thì chừng ấy phân hệ đang để lộ dữ liệu chéo pháp nhân.

    SỬA 16/9/2026 (TC-41): quét CẢ `api/v1` LẪN `services`, chứ không chỉ `api/v1`.

    Bản cũ chỉ nhìn vào thư mục cửa HTTP, nên một phân hệ đặt truy vấn ở lớp dịch vụ — đúng chỗ của
    nó — bị đếm là "chưa nối" dù nó lọc đầy đủ. Đó là một BÁO SAI, và báo sai theo hướng nguy hiểm
    nhất: người đọc bảng đo sẽ đi "sửa" bằng cách nhân bản phép lọc lên tầng cửa, và từ đó có hai
    chỗ cùng quyết một hàng rào. SEC-02 đòi phép cắt dòng nằm TRONG TRUY VẤN Ở MÁY CHỦ; nó không
    đòi truy vấn ấy phải nằm trong tệp nào.

    Vẫn không quét cả kho: chỉ hai thư mục ấy mới có truy vấn phục vụ một phiên đăng nhập.
    """
    import pathlib, re
    if goc_api:
        thu_muc = [pathlib.Path(goc_api)]
    else:
        nen = pathlib.Path(__file__).resolve().parents[1]
        thu_muc = [nen / "api" / "v1", nen / "services"]
    tep = [p for d in thu_muc if d.exists() for p in d.glob("*.py")]
    if not tep:
        return []
    ma = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in tep)
    da_noi = set(re.findall(r"PV\.loc\(\s*[\w\.]+\s*,\s*(\w+)", ma))
    return sorted(t for t in PHAI_LOC if t not in da_noi)


# ---------------------------------------------------------------------------------------------
# Siết tài khoản chưa gán pháp nhân, kể từ ngày vận hành thật
# ---------------------------------------------------------------------------------------------
# Quy tắc 3 ở đầu tệp – "tài khoản chưa gán vẫn thấy toàn bộ" – đúng cho giai đoạn chạy thử: bật lọc
# cứng lúc chưa ai kịp gán thì cả công ty đứng lại trong một buổi sáng.
#
# Nhưng nó chỉ đúng CHO TỚI ngày vận hành thật. Sau ngày ấy, "chưa gán thì thấy tất" không còn là
# sự nhường nhịn nữa, nó là một lỗ hổng: mở một tài khoản mới mà quên gán pháp nhân là vô tình trao
# quyền xem toàn tập đoàn, và không có gì kêu lên.
#
# Nên quy tắc 3 có hạn dùng. Từ mốc vận hành thật (tham số ngay_van_hanh_that, hai chữ ký), tài
# khoản chưa gán KHÔNG còn thấy toàn bộ – nó thấy rỗng, kèm câu nói rõ ai gán được cho mình. Thấy
# rỗng mà biết vì sao thì người ta đi hỏi; thấy tất mà không biết thì không ai hỏi gì cả.
SIET_TU_MOC_VAN_HANH_THAT = True


def sau_moc_van_hanh_that(db) -> bool:
    from app.services.moi_truong_du_lieu import che_do, THAT
    return che_do(db) == THAT


def pham_vi_theo_phien(db, u: User) -> dict:
    """Phạm vi có tính tới mốc vận hành thật. Dùng cho truy vấn danh sách và cho /auth/me.

    Trả `chan_het=True` khi tài khoản chưa gán pháp nhân và đã qua mốc vận hành thật – khi ấy màn
    hình phải hiện RỖNG kèm lý do, không hiện toàn bộ.
    """
    cid = pham_vi(u)
    ly_do = ly_do_khong_gioi_han(u)
    chan = bool(SIET_TU_MOC_VAN_HANH_THAT and cid is None
                and ly_do == "tai_khoan_chua_gan_phap_nhan" and sau_moc_van_hanh_that(db))
    return {
        "company_id": cid, "ly_do_khong_gioi_han": ly_do, "chan_het": chan,
        "cau_hien_thi": ("Tài khoản của bạn chưa được gán pháp nhân nên chưa xem được dữ liệu nào. "
                         "Hành chính Nhân sự hoặc CNTT gán giúp bạn ở màn hình Tài khoản & phân quyền."
                         if chan else mo_ta(db, u)["cau_hien_thi"]),
    }


def loc_theo_phien(q, model, u: User, db=None):
    """Như loc(), nhưng biết tới mốc vận hành thật.

    Không đổi hành vi của loc() cũ – năm chỗ đang gọi nó giữ nguyên. Chỗ nào muốn siết đúng luật
    mới thì gọi hàm này và truyền db vào; không truyền db thì hệ quả đúng bằng loc().
    """
    if db is not None and pham_vi_theo_phien(db, u)["chan_het"]:
        # Chặn bằng false() của SQLAlchemy chứ không bằng một điều kiện tự mâu thuẫn: điều kiện
        # kiểu `col IS NULL AND col IS NOT NULL` tuy cũng ra rỗng nhưng đọc như một lỗi gõ nhầm,
        # và người đọc sau sẽ "sửa" nó.
        from sqlalchemy import false
        return q.where(false())
    return loc(q, model, u)


def tai_khoan_chua_gan(db) -> list[dict]:
    """Tài khoản đang hoạt động, không thuộc vai trò toàn tập đoàn, mà chưa gán pháp nhân.

    Đây là danh sách phải làm cạn TRƯỚC mốc vận hành thật. Sau mốc, mỗi dòng còn lại trong danh
    sách này là một người sáng ra không mở được màn hình nào.
    """
    rows = db.execute(select(User).where(User.active == True)).scalars().all()  # noqa: E712
    return [{"id": r.id, "username": r.username, "ho_ten": r.full_name, "vai_tro": r.role}
            for r in rows
            if getattr(r, "role", "") not in TOAN_TAP_DOAN and getattr(r, "company_id", None) is None]
