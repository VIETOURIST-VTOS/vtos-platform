"""Ma trận nhìn thấy dữ liệu theo vai trò.

NGUYÊN TẮC HIỆN HÀNH (chỉ đạo của anh Trần Tuấn ngày 07/9/2026, bảng phân quyền đã duyệt):
- Chủ tịch HĐQT và Tổng giám đốc: xem TẤT CẢ. Đúng hai người, không ai khác.
- Ban Kiểm soát: ĐỌC tất cả, bị chặn mọi thao tác ghi (nghĩa vụ Luật Doanh nghiệp với công ty đại chúng).
- Mọi vai trò còn lại: xem theo PHẠM VI CÔNG VIỆC, mỗi vai trò một danh sách màn hình.

Nhóm ALL_SEEING cũ – gồm bảy vai trò: Chủ tịch, TGĐ, hai Phó TGĐ, Kế toán, CNTT, Ban Kiểm soát – đã được
GIẢI THỂ. Nó là gốc của một lỗi lặp lại: mỗi lần thêm màn hình mới, viết "ALL_SEEING + ai đó" là xong,
nên bảy vai trò cứ tự động nhìn thấy mọi thứ mới mà không ai quyết định điều đó. Hai Phó TGĐ vì vậy đang
xem được dòng tiền, tài khoản ngân hàng, sổ kế toán và nhật ký nghiệp vụ.

Điều KHÔNG đổi trong bản này, để không ai hiểu nhầm là đã nới:
- Nhân viên kinh doanh vẫn chỉ thấy booking của mình, trưởng nhóm thấy nhóm mình (sales_ids_visible).
- Khối Kinh doanh vẫn không thấy cơ cấu chi phí nhà cung cấp (mask_product).
- Tài xế & HDV, Chuyên viên Visa vẫn dùng DANH SÁCH CHO PHÉP: màn hình mới thêm vào hệ thống sẽ không
  tự động mở cho họ.
"""
from fastapi import HTTPException
from app.models.core import User, ROLES

LEADERSHIP = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt")
CONTROL = ("ketoan", "cntt", "bks")
OPERATIONS = ("tp_dh", "nv_dh")
SALES = ("gd_kd", "tp_kd", "tn_kd", "nv_kd")
# Sale Admin phòng Đoàn (mở 24/9/2026 theo bản mô tả công việc hiệu lực 01/9/2026). CỐ Ý ĐỨNG RIÊNG,
# không gộp vào SALES: nhóm SALES là nguồn của REQUEST_CREATE_ROLES (gửi yêu cầu đặt dịch vụ) và của
# GIU_CHO_ROLES (giữ chỗ) — đúng hai việc Phần V bản mô tả cấm vị trí này làm. Gộp vào cho gọn là trao
# lại bằng mã đúng thứ văn bản vừa lấy đi, và tệ hơn: mọi quyền SALES nhận thêm về sau sẽ tự chảy sang
# đây mà không ai quyết định.
SALES_ADMIN = ("sales_admin",)
MARKETING = ("nv_mkt",)
# Người ở hiện trường, chỉ xem việc của chính mình. Hai vai chứ không một: tách 05/10/2026 vì tuyến ký
# của hai nghề khác nhau (tài xế → GĐ đội xe, HDV → TP Hướng dẫn). Nhóm FIELD giữ nguyên tên và vẫn
# dùng chung ở mọi dòng cũ, nên việc tách KHÔNG nới thêm màn hình nào cho ai.
FIELD = ("tai_xe", "hdv")
FLEET_MGR = ("gd_doi_xe",)                              # GĐ điều hành đội xe: toàn bộ phần đội xe, KHÔNG xem
                                                        # dữ liệu khách, booking, bảng lương hay ngân hàng
GUIDE_MGR = ("tp_hd",)                                  # Trưởng phòng Hướng dẫn: điều phối đội HDV cộng tác
                                                        # viên; KHÔNG xem khách, booking, bảng lương, ngân hàng
VISA_STAFF = ("nv_visa",)                               # chuyên viên visa: chỉ phân hệ Visa
ADMIN_STAFF = ("hanh_chinh",)                           # bảo vệ, pháp chế, quan hệ nhà đầu tư: thuộc HCNS
                                                        # nhưng KHÔNG xem bảng lương (chỉ đạo 07/9/2026)

FULL_VIEW = ("chutich", "tgd")                          # xem tất cả – đúng hai người
# robot_ks vào đây theo quyết định của Chủ tịch ngày 09/9/2026: robot làm việc Ban Kiểm soát thì phải
# nhìn được thứ Ban Kiểm soát nhìn, nếu không nó chỉ đọc lại kết quả vòng quét do chính máy chủ chạy –
# tức là kiểm tra chính báo cáo của mình. Đọc TẤT CẢ, ghi thì KHÔNG (nó nằm trong READ_ONLY_ROLES ngay
# dưới đây, cùng hàng rào với bks).
#
# Đây là một lần NỚI so với bản P8 hôm qua, và nó có giá: một tài khoản đọc được mọi số liệu công ty
# thì mất mật khẩu là lộ hết. Đổi lại được hai thứ – robot kiểm tra được toàn hệ thống, và nhật ký vẫn
# tách robot khỏi người, việc mà mượn thẳng tài khoản bks thì không làm được.
READ_ALL = ("bks", "robot_ks")                          # đọc tất cả, bị chặn mọi thao tác ghi
BASE_VIEW = FULL_VIEW + READ_ALL                        # nền của MỌI dòng trong ma trận dưới đây

# MỌI NGƯỜI LÀM VIỆC Ở ĐÂY – mở 08/10/2026 cho màn hình Đơn nghỉ phép của tôi.
#
# Đây là nhóm RỘNG NHẤT trong tệp, nên lý do phải viết ra: một đơn nghỉ phép là thứ mọi người làm thuê
# đều phải gửi được. Cửa máy chủ `POST /leaves` dùng `current_user` – tức nhận đơn của bất kỳ ai đăng
# nhập – nhưng ô bấm chỉ có trên màn hình /xe-hdv của tài xế và hướng dẫn viên, nên CHÍN PHÒNG CÒN LẠI
# không có đường vào. Cửa mở mà người không với tới thì cửa ấy chưa tồn tại. (Màn hình HCNS ở
# /hr?tab=cham_cong là màn hình của NGƯỜI CHẤM CÔNG – nó mở cho sáu vai, không phải cho người gửi đơn.)
#
# Khai THẲNG 22 tên chứ không viết `tuple(ROLES)`: ba vai robot (`robot_pq`, `robot_ks`, `robot_vpm`)
# KHÔNG có mặt, và sẽ không có mặt – robot không nghỉ phép, và một nhóm tự sinh từ danh sách vai thì
# ngày có vai robot thứ tư nó tự nhận thêm một tài khoản máy vào màn hình đơn từ mà không ai quyết định.
# Hàng rào `test_ns2` tính tập vai của người TẠI CHỖ từ `ROLES` và đòi khớp đúng, không đòi một con số.
MOI_NHAN_VIEN = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "nv_kd", "tn_kd", "tp_kd",
                 "gd_kd", "sales_admin", "nv_mkt", "ketoan", "hcns", "cntt", "bks", "tai_xe", "hdv",
                 "gd_doi_xe", "tp_hd", "nv_visa", "hanh_chinh", "ir_phapche")
# `ir_phapche` thêm 08/10/2026 chiều — và nó vào đây vì HÀNG RÀO REO, không vì ai nhớ ra. Vai ấy mở
# sáng cùng ngày ở Đợt D2 (PR #247); `test_ns2` tính tập vai của NGƯỜI tại chỗ từ `ROLES` và đỏ ngay
# với đúng một tên. Đây là lý do phép thử ấy cố ý KHÔNG viết con số 22 vào mã: viết số thì nó đỏ mà
# không nói được thiếu ai, và người sửa sẽ sửa con số.

# Màn hình Nhân sự tách quyền theo TAB (chỉ đạo 07/9/2026). Trước bản này, ai mở được màn hình là thấy cả
# ba tab – nên không có cách nào cho một người xem hồ sơ nhân sự mà không xem luôn bảng lương.
# Bảng lương chỉ còn HCNS theo vai trò; Kế toán trưởng xem toàn công ty bằng NGOẠI LỆ THEO NGƯỜI
# (năng lực "bang_luong"), vì vai trò "ketoan" có nhiều người mà quyền chỉ cấp cho một.
HR_TABS = {"payroll": "Bảng lương", "tong_quan": "Tổng quan HCNS",
           "employees": "Hồ sơ nhân sự", "cham_cong": "Chấm công & nghỉ phép",
           "incidents": "Đánh giá & sự vụ"}
HR_TAB_ROLES = {
    "payroll": BASE_VIEW + ("hcns",),
    "employees": BASE_VIEW + ("ptgd_doan", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt"),
    # Hai thẻ Đợt C DÙNG LẠI đúng bộ vai của thẻ Hồ sơ nhân sự, không khai bộ mới.
    # Cùng một tập người, cùng một loại dữ liệu: ai xem được hồ sơ nhân sự thì xem được
    # tổng quan nhân sự và bảng chấm công. Khai một bộ vai mới ở đây là LẦN VIẾT PHẦN MỀM
    # TỰ ĐẶT QUYỀN, mà quyền thì thuộc làn Phân quyền. Muốn hẹp hơn – ví dụ chỉ HCNS – thì
    # sửa hai dòng này, và đó là một quyết định có chữ ký chứ không phải một lần tinh chỉnh.
    #
    # Khối bảng lương trên Tổng quan KHÔNG đi theo bộ vai này: nó chỉ hiện khi người gọi
    # thật sự mở được thẻ Bảng lương (services/hcns_tong_quan.py). Không có vế ấy thì thẻ
    # Tổng quan mở bảng lương cho Kế toán và các Trưởng phòng bằng cửa sau.
    "tong_quan": BASE_VIEW + ("ptgd_doan", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt"),
    "cham_cong": BASE_VIEW + ("ptgd_doan", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt"),
    "incidents": BASE_VIEW + ("ptgd_doan", "tp_dh", "gd_kd", "hcns", "cntt"),
}
HR_TAB_CAPABILITY = {"payroll": "bang_luong"}     # tab mở thêm được bằng ngoại lệ theo người
# Cơ cấu chi phí NCC, quyết toán, dòng tiền tour. Phó TGĐ tour đoàn GIỮ quyền này vì phải duyệt dự toán
# đoàn; Phó TGĐ Marketing mất, vì duyệt chi marketing không cần nhìn giá vốn nhà cung cấp của tour.
#
# `sales_admin` vào đây ngày 24/9/2026 theo quyết định của Chủ tịch, và đây là một lần NỚI nên phải
# ghi lý do: bản mô tả công việc buộc vị trí này (mục 4.2) kiểm "hoa hồng và quà tặng dành cho khách
# đã được đưa vào dự toán ngay từ đầu và tính vào giá vốn của chính đoàn đó", và (Phần VI) báo cáo
# tháng lợi nhuận từng đoàn theo người chốt. Không thấy giá vốn thì không kiểm được cả hai, mà biên
# kế hoạch in ra sẽ đẹp hơn sự thật đúng bằng khoản bỏ sót — cổng biên 10% mở cho một đoàn lẽ ra
# phải đi đường hai chữ ký.
#
# Nới quyền ĐỌC giá vốn KHÔNG kéo theo quyền làm việc với nhà cung cấp: đặt dịch vụ và liên hệ NCC
# vẫn cấm (Phần V), và lệnh cấm ấy nằm ở chỗ khác — `sales_admin` không có trong REQUEST_CREATE_ROLES
# và không mở màn hình /nha-cung-cap. Xem giá vốn là để SOÁT, không phải để gọi.
COST_ROLES = BASE_VIEW + OPERATIONS + ("ptgd_doan", "ketoan", "cntt") + SALES_ADMIN
# Giao dịch ngân hàng và tổng hợp thu tiền toàn công ty: thu về Kế toán. Trưởng phòng Điều hành mất quyền
# này – điều hành cần dòng tiền TỪNG TOUR (COST_ROLES ở trên), không cần sổ tiền gửi của công ty.
FINANCE_ROLES = BASE_VIEW + ("ketoan",)
AUDIT_ROLES = BASE_VIEW + ("ketoan", "cntt")            # nhật ký kiểm toán
PARAM_ROLES = BASE_VIEW + ("ptgd_doan", "ptgd_mkt", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt")
# Dữ liệu booking (danh sách, phiếu thu, bảo lưu, dịch vụ lẻ). Rộng hơn từng màn hình một vì đây là lớp
# DỮ LIỆU; màn hình nào ai mở được thì xem ở MENU_ROLES.
BOOKING_ROLES = BASE_VIEW + OPERATIONS + SALES + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt")
# VPM-7 – ai gia hạn / khôi phục GIỮ CHỖ được. HẸP HƠN hẳn BOOKING_ROLES ở trên: xem booking là một
# việc, kéo dài một chỗ đang bị giữ là việc khác — mỗi lần gia hạn là một ghế không bán cho khách
# khác. Danh sách này từng nằm trong giu_cho.py và chỉ kiểm ở trong thân hàm, nên bộ kiểm KS-2 đọc
# chữ ký endpoint thì thấy "ai đăng nhập cũng gọi được", và người bị từ chối nhận 422 (sai dữ liệu)
# chứ không phải 403 (không có quyền). Đưa về đây để một chỗ khai, hai chỗ dùng.
GIU_CHO_ROLES = ("nv_dh", "tp_dh", "gd_kd", "tp_kd", "cntt", "tgd")
# KS-4 – ai NHẬN và ĐÓNG cảnh báo được. Trước 11/9/2026 cửa đóng cảnh báo không có chặn nào: bất kỳ
# tài khoản nào đăng nhập cũng đóng được cảnh báo đỏ của phòng khác. Danh sách này gồm các vai có
# trách nhiệm xử lý việc, cộng bốn nhóm giám sát toàn hệ thống. KHÔNG có vai chỉ-xem (bks, robot_ks
# nằm trong BASE_VIEW nhưng bị chặn ghi ở lớp READ_ONLY_ROLES, nên có mặt ở đây là vô hại).
CANH_BAO_ROLES = BASE_VIEW + OPERATIONS + SALES + FLEET_MGR + GUIDE_MGR + (
    "ketoan", "cntt", "hcns", "ptgd_doan", "ptgd_mkt", "hanh_chinh")
REQUEST_CREATE_ROLES = OPERATIONS + SALES               # được GỬI yêu cầu đặt dịch vụ: Điều hành + toàn khối Kinh doanh
                                                        # (nguồn duy nhất – máy chủ và giao diện dùng chung, tránh lệch vai trò)
PAYMENT_REQUEST_ROLES = (BASE_VIEW + OPERATIONS +
                         ("ptgd_doan", "ptgd_mkt", "gd_kd", "ketoan", "hcns", "hanh_chinh", "cntt"))
# hanh_chinh mới được thêm: nhóm chi "hành chính" là việc của họ, mà trước nay họ không có màn hình nào
READ_ONLY_ROLES = ("bks", "robot_ks")
# Chặn-mặc-định vẫn giữ nguyên: Ban Kiểm soát không ghi được gì trừ đúng những đường dẫn dưới đây.
#
# Ngày 07/9/2026 anh Trần Tuấn giao vị trí Kiểm soát cho AI: kiểm tra, thử, giám sát và báo cáo mọi
# phòng ban về Chủ tịch. Việc "mở ngoại lệ và yêu cầu phòng ban giải trình" là thao tác GHI, nên
# danh sách này phải nới – nhưng nới đúng ba cửa, không nới nguyên tắc:
#   /kiem-soat/quet     : chạy vòng quét (chỉ đọc dữ liệu nghiệp vụ, chỉ ghi bản ghi phát hiện của
#                         chính robot)
#   /kiem-soat/cham-diem: chấm điểm phòng ban – kết quả luôn ở trạng thái CHỜ HẬU KIỂM của Chủ tịch,
#                         không phải kết luận
#   /ngoai-le/ghi       : ghi giải trình vào ngoại lệ. KHÔNG có /ngoai-le/dong – robot mở việc ra
#                         được, nhưng đóng lại là quyền của người.
# Cố ý KHÔNG có: mọi đường dẫn nghiệp vụ. Robot kiểm soát không sửa được một con số nào của phòng ban
# mà nó đang giám sát – đó là điều làm cho báo cáo của nó có giá trị.
WRITE_ALLOWED_FOR_READ_ONLY = ("/api/v1/auth/password", "/api/v1/auth/login", "/api/v1/robot/r9",
                               "/api/v1/kiem-soat/quet", "/api/v1/kiem-soat/cham-diem",
                               "/api/v1/hach-toan/thieu-gia-von/quet",
                               "/api/v1/ngoai-le/ghi")


def require(u: User, roles: tuple, what: str = "dữ liệu này") -> None:
    from app.api.deps import toan_quyen
    if u.role not in roles and not toan_quyen(u):
        raise HTTPException(403, f"Vai trò của bạn không được xem {what}")


def sees_all_sales(u: User) -> bool:
    """True nếu người dùng thấy mọi booking/khách; NV kinh doanh chỉ thấy phần mình, trưởng nhóm thấy nhóm mình."""
    return u.role not in ("nv_kd", "tn_kd")


def own_only(u: User) -> bool:
    return u.role == "nv_kd"


def group_only(u: User) -> bool:
    return u.role == "tn_kd" and bool(u.sales_group)


def sales_ids_visible(db, u: User) -> list[int] | None:
    """None = thấy tất cả; danh sách id sale = chỉ thấy booking/phiếu thu của các sale này."""
    from sqlalchemy import select
    if u.role == "nv_kd": return [u.id]
    if u.role == "tn_kd":
        if not u.sales_group: return [u.id]
        return [x for x in db.execute(select(User.id).where(User.sales_group == u.sales_group)).scalars()] or [u.id]
    return None


def can_see_cost(u: User) -> bool:
    return u.role in COST_ROLES


def check_readonly_write(u: User, method: str, path: str) -> None:
    if u.role in READ_ONLY_ROLES and method not in ("GET", "HEAD", "OPTIONS") and path not in WRITE_ALLOWED_FOR_READ_ONLY:
        raise HTTPException(403, "Ban Kiểm soát chỉ có quyền đọc, không được thực hiện thao tác ghi")


# Đường dẫn API mà vai trò bị giới hạn được gọi. Chặn ở MỘT chỗ thay vì sửa từng endpoint: phần lớn endpoint
# chỉ yêu cầu "đã đăng nhập", nên mở một vai trò mới mà không có lớp này là vô tình cho họ đọc cả danh sách
# tour kèm dự toán. Đây là danh sách CHO PHÉP – endpoint mới mặc định nằm ngoài, không phải nằm trong.
RESTRICTED_API_PREFIXES = {
    # /incidents có mặt vì màn hình sự vụ lọc sẵn về đúng người đăng nhập: người ở hiện trường phải đọc
    # được sự vụ ghi cho CHÍNH MÌNH – bị ghi nhận một sự vụ mà không được xem nó là không đối chất được.
    # 09/9/2026 – dọn hai dòng thừa: "/api/v1/auth/" đã có sẵn cho MỌI vai trò qua API_CHUNG, và
    # "/api/v1/xe-hdv/" thì vai trò này đã suy được từ ma trận menu. Hàng rào so bằng startswith nên
    # tiền tố có dấu gạch cuối chỉ là bản sao hẹp hơn của tiền tố không dấu – giữ lại chỉ làm bảng dài
    # ra và làm bộ tra cứu ngược báo "còn dòng khai tay chưa rà".
    # /payment-requests mở 05/10/2026 để tài xế lập đề nghị tạm ứng của CHÍNH MÌNH. Mở tiền tố này
    # KHÔNG mở sổ chi toàn công ty: cửa đọc lọc theo `created_by` (xem ops.py::list_pr), và cửa ghi
    # chỉ nhận đúng loại `tam_ung_tai_xe` (xem ops.py::LOAI_CHI_TAI_XE_TU_LAP). Ba lớp, và cả ba đều
    # cần: bỏ lớp nào thì một tài xế đọc được hoặc lập được thứ không phải của mình.
    # /fleet/bao-hong thêm 06/10/2026: cửa báo hư hỏng. Khai ĐÚNG nhánh con, không khai cả
    # "/api/v1/fleet" — hàng rào so bằng startswith, nên khai tiền tố cha là mở luôn toàn bộ phân
    # hệ đội xe (hồ sơ xe, bảng giá, quyết toán chủ xe) cho một vai chỉ cần một cửa.
    # /leaves và /leave-balance thêm 07/10/2026: cửa nộp đơn nghỉ phép / ốm / vắng việc, nhóm việc
    # CON NGƯỜI Chủ tịch quyết 30/9. Hai cửa này ĐÃ CHẠY trên máy chủ từ trước mà không màn hình nào
    # gọi tới – tức là một bảng được khai "có cửa nhập tay" trong khi người phải dùng nó không với
    # tới cửa ấy. Mở tiền tố không mở sổ đơn công ty: `GET /leaves` lọc ba tầng theo người ký
    # (hrm.py::phong_minh_ky), và tài xế không nằm trong tầng nào ngoài tầng "đơn của chính mình".
    "tai_xe": ("/api/v1/incidents", "/api/v1/payment-requests", "/api/v1/fleet/bao-hong",
               "/api/v1/leaves", "/api/v1/leave-balance"),
    # HDV cũng nộp được đơn: cùng màn hình /xe-hdv, và người ký của phòng Hướng dẫn đã khai trong
    # hrm.TUYEN_KY_DON. Không mở /fleet/bao-hong cho vai này – hướng dẫn viên không đứng tên xe.
    "hdv": ("/api/v1/incidents", "/api/v1/leaves", "/api/v1/leave-balance"),
    # GĐ điều hành đội xe: cả phân hệ đội xe và lệnh điều xe, cộng danh mục xe để chọn trong form. Không có
    # /tours, /bookings, /banks, /payroll – phạm vi công việc của ông là chiếc xe, không phải khách hàng và
    # dòng tiền công ty.
    # /nap-du-lieu và /tep có mặt vì ma trận menu ĐÃ cho vai trò này hai màn hình đó (bộ nạp nhật trình
    # chuyến xe và kho chứng từ của xe). Thiếu hai prefix này thì menu hiện ra mà bấm vào là 403 – một
    # cánh cửa vẽ trên tường còn khó chịu hơn không có cửa.
    # "/api/v1/xe-hdv" ở đây KHÔNG thừa và không được bỏ: hai vai trò gd_doi_xe và tp_hd lấy màn hình
    # /xe-hdv từ danh sách CHO PHÉP chứ không từ ma trận menu, nên không suy ra được tiền tố ấy. Bỏ đi
    # là họ mất cả phân hệ xe & HDV – đúng kiểu siết đúng nguyên tắc mà sai hậu quả. Chỉ bỏ dấu gạch
    # cuối cho thống nhất; hàng rào so bằng startswith nên quyền không đổi.
    # "/api/v1/leaves" thêm 07/10/2026 cho CẢ HAI người ký, và phải khai TAY ở đây đúng vì lý do
    # ghi ngay phía trên: hai vai này lấy /xe-hdv từ danh sách CHO PHÉP, nên không suy được tiền tố
    # nào của màn hình ấy. Thiếu dòng này thì màn hình hiện nút Duyệt mà bấm vào là 403 – và tệ hơn
    # một cửa thiếu, vì bảng luồng công việc lúc ấy khai một người ký không ký được.
    "gd_doi_xe": ("/api/v1/fleet", "/api/v1/xe-hdv", "/api/v1/dispatch",
                  "/api/v1/vehicles", "/api/v1/nap-du-lieu", "/api/v1/tep",
                  "/api/v1/doc-chung-tu", "/api/v1/tai-xe", "/api/v1/leaves"),
    "nv_visa": ("/api/v1/visa",),
    # --- Ba vai trò máy (P8, 08/9/2026) ---
    # Danh sách của mỗi robot hẹp đúng bằng việc nó được giao, và HAI CHỖ TRỐNG dưới đây là chỗ trống
    # cố ý, mỗi chỗ là một điều cấm trong lệnh giao việc:
    #
    #   robot_vpm KHÔNG có /api/v1/ngoai-le → không tự đóng được ngoại lệ do chính mình gây ra. Người
    #   viết phần mềm mà đóng được việc của mình thì lớp kiểm soát chỉ còn là hình thức: mọi phát hiện
    #   đều có thể biến mất bằng một lần bấm của chính người bị phát hiện.
    #
    #   robot_pq KHÔNG có bất kỳ tiền tố nghiệp vụ nào (/tours, /bookings, /journal, /payment-requests,
    #   /receipts…) → không ghi được một con số nào vào sổ. Robot cầm chìa khoá quyền mà ghi được số
    #   tiền thì nó vừa mở cửa vừa đi qua cửa, và không còn ai đứng ngoài để đối chiếu.
    #
    # Cả ba đều KHÔNG nằm trong FULL_ACCESS, BASE_VIEW, AUDIT_ROLES. Các cửa GHI của màn hình phân quyền
    # (đổi vai trò, khoá/mở, gán pháp nhân) liệt kê vai trò đích danh nên robot_pq đọc được mà không ghi
    # được – hàng rào tiền tố lo phần thô, chữ ký từng đường dẫn lo phần tinh.
    "robot_pq": ("/api/v1/access", "/api/v1/ai", "/api/v1/kiem-soat"),
    "robot_vpm": ("/api/v1/kiem-soat", "/api/v1/he-thong"),
    # Trưởng phòng Hướng dẫn: phần hướng dẫn, chào chuyến, bảng giá tuyến, tệp đính kèm và bộ nạp dữ
    # liệu của phòng. Không có /bookings, /tours, /payroll, /banks – ông chọn người cho chuyến, không
    # quản khách và không quản tiền công ty.
    # "/api/v1/leaves" thêm 07/10/2026: Trưởng phòng Hướng dẫn là người ký đơn của hướng dẫn viên
    # (hrm.TUYEN_KY_DON), và cùng lý do như gd_doi_xe ở trên, tiền tố ấy không suy ra được.
    "tp_hd": ("/api/v1/huong-dan", "/api/v1/guide-assignments", "/api/v1/guide-rates",
              "/api/v1/incidents", "/api/v1/tep", "/api/v1/nap-du-lieu", "/api/v1/xe-hdv",
              "/api/v1/leaves"),
}


# ============================ P2 – DANH SÁCH CHO PHÉP CHO MỌI VAI TRÒ ============================
#
# Trước bản này chỉ 4 trong 20 vai trò có danh sách đường dẫn được phép; 16 vai trò còn lại đi theo kiểu
# chặn từng cửa. Nghĩa là thêm một endpoint mà quên khai quyền là endpoint đó mở cho mọi người đăng
# nhập – và không ai biết, vì không có gì báo.
#
# Cách làm: KHÔNG khai tay danh sách cho từng vai trò. Danh sách được SUY RA từ hai thứ đã có:
#   1. MENU_ROLES – vai trò nào mở được màn hình nào (bảng đã duyệt, là nguồn sự thật về quyền)
#   2. MAN_HINH_API – màn hình nào gọi những nhóm API nào
#
# Bản đồ ở (2) không phải phỏng đoán: nó đo từ chính mã giao diện – mọi lời gọi api("/...") trong
# web/app/<màn hình>/page.tsx và trong các thành phần dùng chung. Khai tay bản đồ này thì nó sẽ lệch
# với giao diện ngay lần sửa màn hình tiếp theo, nên có phép thử đối chiếu lại với mã giao diện.
#
# Đây là hàng rào NGOÀI, thô: nó nói vai trò được CHẠM vào nhóm API nào. Quyền chi tiết vẫn nằm ở chỗ
# cũ – require_roles ở chữ ký từng endpoint, chặn theo bộ nạp, cổng bảng lương. Hàng rào ngoài không
# thay chúng, nó chỉ đảm bảo một endpoint mới quên khai quyền thì cũng không lọt ra ngoài phạm vi công
# việc của vai trò.
# /incident-levels là DANH MỤC, không phải dữ liệu: nó trả về ý nghĩa ba mức sự vụ, các trạng thái, và
# mô tả quy trình – không có sự vụ của ai trong đó. Sau đợt siết P2, vai trò nào không mở màn hình /ops
# đều mất quyền đọc nó, và nhân viên kinh doanh mở màn hình sự vụ nhận 403 (phép thử test_hr bắt được).
#
# Đưa vào nhóm chung theo đúng lập luận đã ghi sẵn cho /api/v1/incidents ở phần vai trò hẹp: người có
# thể BỊ ghi nhận một sự vụ phải đọc được mức ấy nghĩa là gì – không đọc được thì không đối chất được.
# Giấu định nghĩa của chế tài khỏi người chịu chế tài không bảo vệ gì cả.
#
# Tiền tố này KHÔNG mở /api/v1/incidents (dữ liệu sự vụ thật): hai chuỗi khác nhau ngay sau chữ
# "incident", nên phép so tiền tố không trùng. Quyền đọc sự vụ vẫn nguyên như cũ.
# /incidents cũng vào nhóm chung, và đây là chỗ cần đọc kỹ trước khi ai đó rút nó ra:
#
#   - Endpoint TỰ LỌC: nhân viên (nv_kd, nv_dh, tai_xe, hdv) chỉ thấy sự vụ của CHÍNH MÌNH – lọc nằm ngay
#     trong hàm, không phải lời hứa ở đây.
#   - Endpoint đã có require_roles riêng ở chữ ký. Vai trò không nằm trong danh sách đó vẫn nhận 403
#     như trước, kể cả khi tiền tố này mở.
#   - Hàng rào ngoài sinh ra để "một endpoint QUÊN khai quyền thì cũng không lọt". Endpoint này không
#     quên: nó khai đủ và lọc đủ. Chặn nó ở vòng ngoài chỉ khóa mất quyền đối chất của người bị ghi
#     nhận sự vụ – họ không đọc được biên bản về mình, và không gửi được ý kiến hay khiếu nại.
API_CHUNG = ("/api/v1/auth", "/api/v1/health", "/api/v1/meta", "/api/v1/alerts", "/api/v1/dashboard",
             "/api/v1/incident-levels", "/api/v1/incidents",
             # P6: ai đăng nhập cũng phải đọc được phạm vi pháp nhân của CHÍNH phiên mình. Chặn
             # nó lại thì màn hình không có cách nào nói cho người dùng biết họ đang xem dữ liệu
             # của công ty nào – mà im lặng chính là thứ P6 sinh ra để chống.
             "/api/v1/pham-vi")
# Màn hình ai đăng nhập cũng có (giống danh sách phụ trong ALL_MENU_PATHS): trang chủ, đổi mật khẩu,
# cảnh báo, báo cáo công việc. Bảng lương cá nhân đi qua /payroll và tự lọc về đúng người.
# "/offline" thêm 13/9/2026 cùng đợt đưa VTOS thành app cài được: trang dự phòng service worker
# bật lên khi MÁY CHỦ KHÔNG VỚI TỚI. Nó không hỏi quyền được – lúc ấy không gọi được máy chủ –
# nên phải là màn hình mở cho mọi người. Trang không mang một con số nào, chỉ báo mất mạng.
MAN_HINH_MOI_NGUOI = ("/", "/doi-mat-khau", "/alerts", "/reports", "/payroll", "/phieu-luong",
                      "/offline")

# Màn hình → nhóm API nó gọi. Đo từ mã giao diện ngày 08/9/2026.
MAN_HINH_API = {
    "/": ("/api/v1/dashboard",),
    "/access": ("/api/v1/access", "/api/v1/users", "/api/v1/he-thong"),
    "/accounting": ("/api/v1/accounts", "/api/v1/collections", "/api/v1/invoices", "/api/v1/journal",
                    "/api/v1/ledger", "/api/v1/misa", "/api/v1/partners", "/api/v1/periods",
                    "/api/v1/reports", "/api/v1/tax", "/api/v1/trial-balance", "/api/v1/projects",
                    "/api/v1/books"),
    # /api/v1/periods có mặt vì màn hình kết sổ có luôn nút khóa kỳ – khóa kỳ là bước cuối của chính
    # việc kết sổ, tách sang màn hình khác thì người làm phải nhớ đi hai nơi.
    "/ket-so": ("/api/v1/ket-so", "/api/v1/accounting", "/api/v1/hach-toan", "/api/v1/periods"),
    "/ai-roles": ("/api/v1/ai",),
    "/alerts": ("/api/v1/alerts", "/api/v1/robot", "/api/v1/robots"),
    # Quyết toán tour (bộ nạp V3) chưa có mục menu riêng – gắn tạm vào hai màn hình đang dùng nó.
    # Khi có màn hình riêng thì chuyển sang đó; phép thử nhóm API mồ côi canh để không ai quên.
    "/audit": ("/api/v1/audit",),
    "/bank-accounts": ("/api/v1/bank-accounts",),
    "/bookings": ("/api/v1/bookings", "/api/v1/retentions", "/api/v1/receipts", "/api/v1/tours"),
    "/cham-soc": ("/api/v1/cham-soc", "/api/v1/cskh"),
    "/collections": ("/api/v1/bank-transactions", "/api/v1/collections", "/api/v1/receipts",
                     "/api/v1/sepay", "/api/v1/bookings"),
    "/companies": ("/api/v1/companies",),
    "/cong-no": ("/api/v1/cong-no", "/api/v1/cong-no-vietrip"),
    # 19/9/2026 – màn hình này nay còn là chỗ người tự nối Zalo của mình để nhận cảnh báo khủng
    # hoảng. Cùng một màn hình vì cùng một việc: những thứ thuộc về TÀI KHOẢN của chính mình, và
    # không vai trò nào làm hộ được cho ai.
    "/doi-mat-khau": ("/api/v1/auth", "/api/v1/zalo"),
    # Đơn nghỉ KHÔNG nằm ở đây. 07/10/2026 em đã định gắn hàng đợi ký vào màn hình này rồi bỏ:
    # /doi-xe là màn hình của CHIẾC XE (hồ sơ, bảo dưỡng, báo hỏng), còn đơn nghỉ là việc của NGƯỜI.
    # Và Trưởng phòng Hướng dẫn – người ký đơn của hướng dẫn viên – không có màn hình này. Cả hai
    # người ký cùng có /xe-hdv, nên hàng đợi nằm ở đó, cạnh chính những người làm đơn.
    "/doi-xe": ("/api/v1/fleet", "/api/v1/vehicles", "/api/v1/drivers"),
    "/expenses": ("/api/v1/cashflow", "/api/v1/payment-requests", "/api/v1/tours"),
    "/finance": ("/api/v1/fin", "/api/v1/cashflow"),
    "/hach-toan": ("/api/v1/hach-toan",),
    # V7 Đợt 3 (10/9/2026). Sự cố tour đọc thêm /tours, /bookings, /suppliers và /payment-requests: màn
    # hình phải chọn chuyến, chọn nhà cung cấp gây sự cố, và gắn số hiệu đề nghị chi lúc kết luận.
    # Màn hình này chỉ chạm ĐÚNG HAI nhóm API, và đó là chủ ý.
    #
    # Sự cố tour mở cho nhiều vai trò nhất trong các màn hình nghiệp vụ – từ Ban lãnh đạo tới nhân
    # viên kinh doanh, GĐ Đội xe và TP Hướng dẫn. Mỗi ô chọn gọi thẳng ra một nhóm API là mỗi lần
    # nhân danh sách vai trò ấy lên cho một phân hệ khác: gọi /api/v1/suppliers là mở cơ cấu chi phí
    # NCC cho khối Kinh doanh; gọi /api/v1/bookings và /api/v1/khieu-nai là trao danh sách khách cho
    # Đội xe và Phòng Hướng dẫn. Bản đầu 10/9/2026 làm đúng như thế và bộ kiểm phạm vi P2 bắt được.
    #
    # Nên bốn ô chọn đi qua chính phân hệ này, mỗi ô sau hàng rào của riêng nó:
    #   /su-co-tour/meta            – nhà cung cấp và chuyến, chỉ mã + tên
    #   /su-co-tour/chon/booking    – booking CỦA MỘT CHUYẾN; tên khách chỉ trả cho vai trò trong KHACH
    #   /su-co-tour/chon/ket-luan   – chứng từ chi và khiếu nại, sau hàng rào su_co_tour.DONG
    "/su-co-tour": ("/api/v1/su-co-tour", "/api/v1/tep"),
    # Hồ sơ kiểm toán đọc /companies (chọn pháp nhân) và /tep (đính kèm tài liệu cho từng mục).
    # KHÔNG có /journal: màn hình nhận SỐ HIỆU bút toán bằng ô gõ tay chứ không mở danh sách sổ cái để
    # chọn. Cố ý – gắn ô chọn ở đây là mở sổ kế toán cho mọi vai trò xem được hồ sơ kiểm toán.
    "/ho-so-kiem-toan": ("/api/v1/kiem-toan", "/api/v1/companies", "/api/v1/tep"),
    "/hieu-qua-doi-xe": ("/api/v1/fleet",),
    # Đơn nghỉ phép của tôi. ĐÚNG HAI tiền tố, và KHÔNG có "/api/v1/attendance": lưới chấm công đứng
    # ở thẻ Chấm công của màn hình /hr, nơi tiền tố ấy đã khai từ trước và người GHI được nó đã có mặt.
    # Khai thêm ở đây là cho cả 22 vai mang trong phạm vi một cửa máy chủ TỪ CHỐI họ (`GET /attendance`
    # đòi HR_READ, `POST` đòi HR_ADMIN) – phạm vi vai trò CỘNG RA từ bảng này, nên đó là một lần nới thật.
    # `/api/v1/danh-gia-cua-toi` vào đây 09/10/2026, KHÔNG vào /hr. Chủ tịch chốt 08/10 "nhân viên
    # được thấy của mình"; /hr chỉ mở cho sáu vai, nên đặt cửa ấy ở /hr thì hoặc phải nới /hr cho
    # cả công ty (mở luôn hồ sơ nhân sự và bảng lương), hoặc nhân viên không với tới. Màn hình này
    # đã mở cho MOI_NHAN_VIEN từ 08/10, nên 0 dòng đổi trong MENU_ROLES.
    "/cham-cong": ("/api/v1/leaves", "/api/v1/leave-balance", "/api/v1/danh-gia-cua-toi"),
    "/hop-dong-lao-dong": ("/api/v1/employees", "/api/v1/hrm", "/api/v1/labor-contracts",
                           "/api/v1/dependents", "/api/v1/leaves", "/api/v1/leave-balance"),
    "/hr": ("/api/v1/hr", "/api/v1/employees", "/api/v1/payroll", "/api/v1/payroll-runs",
            "/api/v1/incidents", "/api/v1/incident-levels", "/api/v1/companies", "/api/v1/users",
            "/api/v1/attendance", "/api/v1/bhxh", "/api/v1/staff", "/api/v1/doan-vien",
            # 5.6 Đánh giá nhân sự (09/10/2026). Đi theo thẻ "Đánh giá & sự vụ" của chính màn hình
            # này, dùng lại HR_TAB_ROLES["incidents"] — không khai bộ vai thứ hai. Cửa "bản của
            # tôi" KHÔNG ở đây: nó mở cho cả công ty, xem /cham-cong ngay dưới.
            "/api/v1/danh-gia-ns"),
    "/huong-dan": ("/api/v1/huong-dan", "/api/v1/guide-rates", "/api/v1/guide-assignments"),
    "/inbox": ("/api/v1/inbox", "/api/v1/facebook", "/api/v1/zalo"),
    "/khieu-nai": ("/api/v1/khieu-nai", "/api/v1/cskh", "/api/v1/bookings", "/api/v1/payment-requests"),
    # Nhật ký NGUYÊN VĂN sự kiện tổng đài về đây chứ không về /inbox, dù cuộc gọi rồi sẽ hiện ở hộp thư.
    # Lý do: gắn vào /inbox là mở tiền tố cho mười ba vai trò, trong khi chỉ bốn vai trò gọi được đường
    # dẫn ấy – phần dôi ra không dùng được nhưng vẫn là quyền đã cấp, và quyền đã cấp thì lần sau ai thêm
    # một đường dẫn cùng tiền tố là mười ba vai trò lặng lẽ có nó. Nhật ký này là bản ghi kỹ thuật thô,
    # có số điện thoại khách trong đó; đúng chỗ của nó là bàn Kiểm soát, cạnh nhật ký sự kiện kỹ thuật.
    # Khi phần diễn giải xong và cuộc gọi lên hộp thư thì đó là đường dẫn khác, mở có chủ đích.
    # Đầu NHẬN (/tong-dai/cuoc-goi/<chuỗi bí mật>) KHÔNG đi qua hàng rào này – tổng đài không có phiên
    # đăng nhập của VTOS, khoá của nó là chuỗi bí mật trong đường dẫn.
    # Robot A · GD-1 (11/9/2026). Khai TẠM do Robot A thêm, Chủ tịch đồng ý 11/9 – theo lệnh giao
    # việc thì tệp này thuộc Robot B, nhưng nhóm API mồ côi làm ĐỎ CI cho mọi làn, và chính mục F
    # của lệnh cảnh báo "đỏ mãi thì rồi không ai nhìn CI nữa". Đây là THÊM một khoá mới, không sửa
    # dòng của ai, nên không va chạm khi Robot B gộp nhánh.
    # Màn hình /dong-tien ĐÃ DỰNG (bản tạm của Robot A, Robot B thay theo TC-3), nên nó KHÔNG nằm
    # trong CHUA_CO_TRANG – khai ở đó là khai một màn hình đang chạy là chưa có.
    # ĐÚNG MỘT nhóm. Danh mục pháp nhân và tài khoản ngân hàng đi qua /dong-tien/meta của chính
    # phân hệ này, không gọi thẳng /companies hay /bank-accounts – gọi thẳng là nhân danh sách vai
    # trò của phân hệ khác lên (bài học vòng 1 Sự cố tour, 10/9/2026).
    "/dong-tien": ("/api/v1/dong-tien",),
    "/kiem-soat": ("/api/v1/kiem-soat", "/api/v1/tong-dai"),
    # Bàn quyết cột tiền K1/K2 – phạm vi API HẸP: chỉ nhánh /cot-tien và /the (để giao diện biết vẽ
    # thẻ nào). KHÔNG gồm kết quả quét, chấm điểm phòng ban hay hậu kiểm số nhập tay.
    "/ra-soat-cot-tien": ("/api/v1/ra-soat-cot-tien",),
    "/bang-gia": ("/api/v1/ban-hang",),
    "/bao-gia": ("/api/v1/ban-hang",),
    "/hop-dong-khach": ("/api/v1/ban-hang",),
    # V11 – Lịch tự động hóa. Phạm vi API HẸP: chỉ nhánh /tu-dong. Màn hình này chỉ đọc trạng thái
    # tác vụ; nó không cần chạm vào bất kỳ số liệu nghiệp vụ nào.
    "/tu-dong-hoa": ("/api/v1/tu-dong",),
    # Báo cáo tự động theo phòng ban. Phạm vi API hẹp: chỉ nhánh /bao-cao. Ai xem được BÁO CÁO NÀO
    # thì máy chủ quyết theo vai trò (bao_cao_phong.pham_vi_duoc_xem), không quyết ở cửa màn hình –
    # cửa màn hình chỉ có hai trạng thái mở/đóng, mà ở đây cần "mở đúng phần của mình".
    "/bao-cao": ("/api/v1/bao-cao",),
    # TC-41 – Kế hoạch tháng. Phạm vi API HẸP: chỉ nhánh /ke-hoach. Màn hình này KHÔNG đọc doanh thu
    # thực hiện: so kế hoạch với thực hiện là việc của màn hình 01, và mở thêm /dashboard ở đây là
    # cấp cho Kế toán một đường vòng vào bảng điều hành của Chủ tịch.
    "/ke-hoach-thang": ("/api/v1/ke-hoach",),
    "/lai-lo-doi-xe": ("/api/v1/fleet",),
    "/leads": ("/api/v1/leads", "/api/v1/zalo", "/api/v1/dau-quang-cao"),
    "/lenh-dieu-xe": ("/api/v1/fleet", "/api/v1/dispatch", "/api/v1/vehicles", "/api/v1/drivers"),
    # 18/9/2026 – THÊM "/api/v1/leads" VÀ "/api/v1/noi-dung", anh Tuấn chốt cùng ngày.
    #
    # Màn hình /marketing nay là KHÔNG GIAN LÀM VIỆC bảy màn hình theo bản vẽ V3.0, nên nó đọc cả
    # sổ lead (khách tiềm năng, chuyển đổi, đối soát) và sổ nội dung. Bản đồ này đo từ mã giao diện
    # chứ không khai bằng trí nhớ, nên gọi thêm nhóm nào là phải khai nhóm ấy —
    # test_p2_pham_vi_vai_tro::test_ban_do_man_hinh_api_khong_lech_voi_giao_dien canh đúng chỗ đó và
    # đã bắt được lần đẩy đầu tiên.
    #
    # HỆ QUẢ PHẢI NÓI RA, KHÔNG ĐƯỢC ĐỂ NÓ LẶNG LẼ: hàng rào NGOÀI suy từ MENU_ROLES × bảng này.
    # So ba dòng menu:
    #     "/marketing" = BASE_VIEW + MARKETING + (ptgd_mkt, gd_kd, ketoan, cntt)
    #     "/leads"     = BASE_VIEW + SALES + OPERATIONS + MARKETING + (ptgd_mkt, cntt)
    #     "/noi-dung"  = BASE_VIEW + MARKETING + (ptgd_mkt, hanh_chinh, cntt)
    # HAI vai được nới, không phải một — con số lấy từ chính phép thử, không nhẩm tay:
    #     ketoan  +2  — cả "/api/v1/leads" lẫn "/api/v1/noi-dung"
    #     gd_kd   +1  — chỉ "/api/v1/noi-dung"; "/api/v1/leads" ông đã có sẵn qua nhóm SALES
    # (Bản nháp đầu của chú thích này viết "vai DUY NHẤT được nới là ketoan" — sai, vì chỉ so
    # /marketing với /leads mà quên /noi-dung. test_p2 đếm ra gd_kd 56 → 57 và sửa lại lời mô tả.)
    #
    # Hàng rào TRONG vẫn chặn — mọi tuyến lead khai require_roles(*CRM_ROLES) và CRM_ROLES không có
    # ketoan; mọi tuyến nội dung khai ND_XEM và ND_XEM không có ketoan lẫn gd_kd — nên hôm nay KHÔNG
    # lọt một dòng dữ liệu khách nào. Cái mất là tấm lưới dự phòng: mai kia ai thêm một tuyến dưới
    # hai nhóm ấy mà quên khai quyền thì hai vai này vào được, còn trước bản này thì không.
    #
    # Đổi lại, màn hình TỰ ẨN bốn tab đọc dữ liệu khách với vai không mở được /leads/meta (xem
    # web/app/marketing/page.tsx) — Kế toán mở không gian Marketing chỉ thấy Ngân sách & chiến dịch,
    # không thấy bốn tab báo lỗi 403. Ẩn ở giao diện KHÔNG phải hàng rào; hàng rào vẫn là hai lớp
    # trên. Nó chỉ để người dùng không phải đoán vì sao màn hình đỏ.
    "/marketing": ("/api/v1/marketing", "/api/v1/products", "/api/v1/users",
                   "/api/v1/leads", "/api/v1/noi-dung"),
    "/doc-chung-tu": ("/api/v1/doc-chung-tu", "/api/v1/nap-du-lieu", "/api/v1/tep"),

    "/nap-du-lieu": ("/api/v1/nap-du-lieu", "/api/v1/quyet-toan-tour"),
    "/ngoai-le": ("/api/v1/ngoai-le",),
    "/nha-cung-cap": ("/api/v1/ncc", "/api/v1/tours"),
    "/noi-dung": ("/api/v1/noi-dung", "/api/v1/marketing"),
    # Đ-5 (13/9/2026): thêm tiền tố lớp 3 vì màn hình này gọi phép soát tháng của dịch vụ lẻ
    # (/quyet-toan-lop3/dich-vu-le/{nam}/{thang} – CHỈ ĐỌC, không có cửa ghi nào).
    #
    # Hàng rào trong vẫn nguyên: danh sách XEM của api/v1/quyet_toan_lop3.py không có vai Kinh
    # doanh nào, nên bốn vai Kinh doanh xem được màn hình này vẫn KHÔNG đọc được phần giá vốn.
    "/non-package": ("/api/v1/non-package", "/api/v1/bookings", "/api/v1/tours",
                     "/api/v1/quyet-toan-lop3"),
    # /ops dùng chung thành phần với /hr (HrScreens) nên chạm cùng nhóm API. Quyền chi tiết vẫn tách:
    # tab bảng lương có cổng riêng, nên chạm được nhóm /payroll không có nghĩa là đọc được bảng lương.
    "/ops": ("/api/v1/hr", "/api/v1/employees", "/api/v1/incidents", "/api/v1/incident-levels",
             "/api/v1/visa", "/api/v1/guide-assignments", "/api/v1/guide-rates", "/api/v1/fleet",
             "/api/v1/vehicles", "/api/v1/vehicle-rates", "/api/v1/dispatch", "/api/v1/tours",
             "/api/v1/companies", "/api/v1/users"),
    "/params": ("/api/v1/params",),
    "/ir-phap-che": ("/api/v1/ir-phap-che",),
    "/products": ("/api/v1/products",),
    "/reports": ("/api/v1/daily-reports", "/api/v1/page-shifts", "/api/v1/employees"),
    # Phiếu lương CỦA CHÍNH MÌNH – tiền tố riêng, chỉ chứa endpoint tự lọc về đúng người.
    # KHÔNG khai /api/v1/payroll-runs hay /api/v1/payroll ở đây: hai tiền tố đó chứa cả bảng lương TOÀN
    # CÔNG TY, mà hàng rào phạm vi ngoài chỉ phân biệt tới mức tiền tố – mở chúng cho mọi vai trò để
    # tài xế xem được phiếu của mình là hạ hàng rào ngoài của cả bảng lương công ty, chỉ còn hàng rào
    # trong đỡ.
    "/phieu-luong": ("/api/v1/phieu-luong",),
    # Bàn làm việc của Phó TGĐ tour đoàn — MỘT nhóm API riêng, cùng khuôn mẫu với /lai-lo-tour và
    # /so-con-no: gắn nhờ vào một nhóm có sẵn (ví dụ /api/v1/tours) là nới CẢ nhóm ấy cho mọi vai mở
    # được màn hình này, và phần dôi ra vẫn là quyền đã cấp dù hàng rào trong chưa cho dùng hôm nay.
    "/ptgd-doan": ("/api/v1/ptgd-doan",),
    # Bàn làm việc của Sale Admin phòng Đoàn — cùng khuôn mẫu và cùng lý do như dòng ngay trên.
    # MÀN HÌNH CHỈ ĐỌC: hai cửa GHI của vai này nằm trên chính chuyến
    # (`POST /tours/{id}/chuyen-dieu-hanh` và `.../tra-lai-kinh-doanh`), không nhân bản sang đây.
    "/sales-admin": ("/api/v1/sales-admin",),
    "/ban-tour-le": ("/api/v1/ban-tour-le",),
    "/danh-gia": ("/api/v1/danh-gia",),
    "/requests": ("/api/v1/requests", "/api/v1/bookings", "/api/v1/tours", "/api/v1/meta",
                  "/api/v1/mang"),
    "/lai-lo-tour": ("/api/v1/lai-lo-tour",),
    # TC-71 · Màn hình chỉ đọc, một nhóm API RIÊNG.
    #
    # Bản nháp đầu đặt cửa trong nhóm `/api/v1/bao-cao` cho tiện. Đo bằng bộ kiểm P2 thì `nv_dh`
    # và `cntt` được nới TOÀN BỘ nhóm báo cáo chỉ vì mở được màn hình này — đúng cái bẫy đã ghi ở
    # nhóm `/api/v1/tong-dai` ngày 09/9: "phần dôi ra vẫn là quyền đã cấp".
    #
    # KHÔNG khai `/api/v1/tours` dù mỗi dòng có đường dẫn sang chuyến: đường dẫn ấy là một liên
    # kết cho người bấm, không phải một lượt gọi máy chủ của màn hình này.
    "/so-con-no": ("/api/v1/so-con-no",),
    "/to-chuc-kd": ("/api/v1/to-chuc-kd",),
    "/nguoi-ban-hang": ("/api/v1/nguoi-ban-hang",),
    "/gop-tai-khoan": ("/api/v1/gop-tai-khoan",),
    # TC-81 - Bao chi, KOL & su kien (muc 2.2.2). HAI tien to, va da kiem ky truoc khi khai cai
    # thu hai: danh sach vai cua man hinh nay nam GON trong danh sach vai cua "/marketing", nen
    # khai "/api/v1/marketing" o day KHONG noi them nhom nao cho bat ky vai nao. So PR da co cua
    # doc va cua phat duoi tien to ay - dung cua san co thay vi dung cua doc thu hai cho cung mot
    # bang. Neu mot ngay danh sach vai cua man hinh nay rong ra thi phai kiem lai dung cho nay.
    "/bao-chi-kol": ("/api/v1/bao-chi-kol", "/api/v1/marketing"),
    "/kinh-doanh-le": ("/api/v1/kinh-doanh",),
    "/dong-gop-marketing": ("/api/v1/dong-gop-marketing",),
    "/chuyen-doi-lead": ("/api/v1/chuyen-doi-lead",),
    "/doi-soat-marketing": ("/api/v1/doi-soat-marketing",),
    "/robot-reports": ("/api/v1/auto-reports",),
    "/sales-reports": ("/api/v1/sales-reports",),
    # 5.9.3 Cấp phát tài sản (09/10/2026) ở lại đây: Chủ tịch chốt "cấp phát tài sản do HCNS làm",
    # và HCNS đã có màn hình này. 5.9.2 Đề nghị mua thì KHÔNG — xem màn hình /de-nghi-mua.
    "/tai-san": ("/api/v1/assets", "/api/v1/fixed-assets", "/api/v1/prepaid", "/api/v1/cap-phat"),
    # 5.9.2 Đề nghị mua — MÀN HÌNH MỚI 09/10/2026. Người đề nghị mua là người của MỌI phòng; gắn
    # cửa ấy vào /tai-san (chỉ Kế toán, CNTT, hành chính, HCNS mở được) thì chín phòng còn lại
    # không có đường gửi và họ sẽ nhắn Zalo như hôm nay. Mở MÀN HÌNH rộng không phải mở QUYỀN:
    # duyệt vẫn chỉ TGĐ/Chủ tịch, ghi đã chi vẫn chỉ Kế toán, chặn ở tầng dịch vụ.
    "/de-nghi-mua": ("/api/v1/de-nghi-mua",),
    # Hồ sơ tài xế: MỘT cửa và chỉ đọc. Sửa hồ sơ ở Nhân sự, nạp bằng lái ở bộ nạp tệp, gán xe
    # ở màn hình Đội xe – nên ở đây không mở thêm tiền tố nào của ba nơi ấy.
    "/tai-xe": ("/api/v1/tai-xe",),
    "/tep": ("/api/v1/tep",),
    # Robot A · 16/9/2026. Sổ tỷ giá. Kèm /api/v1/tep vì chính màn hình này đính ảnh bảng tỷ giá
    # ngân hàng làm chứng từ – tỷ giá không có chứng từ là con số không ai kiểm được.
    "/ty-gia": ("/api/v1/ty-gia", "/api/v1/tep"),
    # "/api/v1/su-co-tour" thêm 08/10/2026 cho tab "Phát sinh" của trang chuyến (mục 4.4.7). Khai được
    # vì `su_co_tour.XEM` nay PHỦ ĐỦ mọi vai mở được /tours — đã đối chiếu hai danh sách trước khi
    # thêm, và `test_dh1` canh đúng phép phủ ấy. Khai một tiền tố rộng hơn cái máy chủ nhận là nới
    # quyền thật, vì phạm vi vai trò CỘNG RA từ bảng này.
    "/tours": ("/api/v1/tours", "/api/v1/su-co-tour", "/api/v1/users", "/api/v1/products", "/api/v1/mang",
               "/api/v1/quyet-toan-tour",
               # Lớp 3 (11/9/2026): dòng khách, doanh thu, phương tiện, HDV chi, sổ dấu vết.
               #
               # KHÔNG dựng một màn hình mới cho nó. Menu đã có mục "Quyết toán tour" trỏ vào /tours,
               # và đây đúng là những cửa của chính màn hình ấy. Thêm một lối vào thứ hai cho cùng
               # một việc là cách chắc chắn để người dùng không biết nên bấm vào đâu.
               #
               # Hệ quả: bốn vai Kinh doanh cũng chạm được tiền tố này, vì họ xem được /tours. Phần
               # giá vốn thì họ VẪN KHÔNG xem được – hàng rào trong là danh sách XEM của chính
               # app/api/v1/quyet_toan_lop3.py, và danh sách ấy không có vai Kinh doanh nào.
               "/api/v1/quyet-toan-lop3"),
    "/vietrip": ("/api/v1/import",),
    "/visa": ("/api/v1/visa",),
    "/xe-hdv": ("/api/v1/xe-hdv", "/api/v1/incidents", "/api/v1/payment-requests",
                "/api/v1/fleet/bao-hong", "/api/v1/leaves", "/api/v1/leave-balance"),
}


_PHAM_VI: dict[str, tuple[str, ...]] = {}


def pham_vi_api(vai_tro: str = "") -> dict[str, tuple[str, ...]] | tuple[str, ...]:
    """Danh sách nhóm API một vai trò được chạm, suy từ MENU_ROLES + MAN_HINH_API.

    Tính một lần rồi nhớ: MENU_ROLES khai bằng hằng số trong mã, không đổi lúc chạy. Tính lười vì
    MENU_ROLES nằm phía dưới trong tệp này – tính lúc nạp mô-đun thì gặp tên chưa khai.
    """
    from app.models.core import ROLES as _ROLES
    if not _PHAM_VI:
        for vai in _ROLES:
            cho = set(API_CHUNG)
            for man_chung in MAN_HINH_MOI_NGUOI:
                cho |= set(MAN_HINH_API.get(man_chung, ()))
            for man, vai_tro_cua_man in MENU_ROLES.items():
                if vai in vai_tro_cua_man:
                    cho |= set(MAN_HINH_API.get(man, ()))
            _PHAM_VI[vai] = tuple(sorted(cho))
    return _PHAM_VI[vai_tro] if vai_tro else dict(_PHAM_VI)


def pham_vi_day_du(vai_tro: str) -> tuple[str, ...]:
    """Phạm vi thật của một vai trò = suy từ ma trận menu, CỘNG những prefix khai tay còn lại.

    Cộng chứ không thay: bốn vai trò hẹp đã có danh sách khai tay từ trước, và trong đó có vài prefix
    ma trận menu không suy ra được. Thay thẳng thì họ mất quyền đang dùng mà không ai báo – nên giữ
    phần khai tay làm phần BỔ SUNG, và mỗi dòng còn lại ở đó là một dòng cần rà rồi bỏ dần.
    """
    return tuple(sorted(set(pham_vi_api(vai_tro)) | set(RESTRICTED_API_PREFIXES.get(vai_tro, ()))))


_DUONG_TU_LOC: set[str] | None = None


def duong_tu_loc() -> set[str]:
    """Những endpoint TỰ LỌC dữ liệu theo người đăng nhập, đọc từ dấu hiệu trong mã chứ không khai tay.

    Có hai kiểu endpoint an toàn, và hàng rào ngoài chỉ hiểu một kiểu. Kiểu thứ nhất CHẶN theo vai trò:
    sai vai trò thì 403. Kiểu thứ hai LỌC theo người: ai gọi cũng được nhưng chỉ nhận phần của chính
    mình – phiếu lương của mình, khoản lương treo của mình, hồ sơ của mình. Kiểu thứ hai không thuộc
    màn hình của vai trò nào cả, nên hàng rào suy từ ma trận menu sẽ chặn đúng người mà endpoint sinh ra
    để phục vụ: một nhân viên kinh doanh không xem được khoản lương treo của chính anh ta.

    Danh sách này KHÔNG khai tay – nó đọc `deps.loc_theo_nguoi_dung` mà endpoint đã tự gắn. Khai tay thì
    thêm endpoint mới là quên, mà quên ở đây nghĩa là khóa người dùng khỏi tiền của họ.
    """
    global _DUONG_TU_LOC
    if _DUONG_TU_LOC is None:
        ra: set[str] = set()
        try:
            import app.main as _m
            for r in _m.app.routes:
                dep = getattr(r, "dependant", None)
                for d in (getattr(dep, "dependencies", None) or []):
                    if getattr(getattr(d, "call", None), "loc_theo_nguoi_dung", None):
                        ra.add(str(getattr(r, "path", "")))
        except Exception:
            return set()   # chưa nạp xong ứng dụng thì đừng nới hàng rào
        _DUONG_TU_LOC = ra
    return _DUONG_TU_LOC


def _khop_duong(path: str, mau: str) -> bool:
    """So khớp đường thật với đường khai của FastAPI, đoạn {…} khớp đúng một đoạn."""
    a, b = path.strip("/").split("/"), mau.strip("/").split("/")
    if len(a) != len(b): return False
    return all(y.startswith("{") or x == y for x, y in zip(a, b))


def check_restricted_scope(u: User, path: str) -> None:
    """Hàng rào ngoài: vai trò chỉ chạm được những nhóm API nằm sau màn hình của mình.

    Trước 08/9/2026 hàng rào này chỉ dựng cho 4 trong 20 vai trò; 16 vai trò còn lại không có hàng rào
    nào, nghĩa là thêm một endpoint mà quên khai quyền là endpoint đó mở cho mọi người đăng nhập. Đây
    là chặn MẶC ĐỊNH: nhóm API mới không nằm trong bản đồ thì không ai vào được, chứ không phải ai cũng
    vào được. Có phép thử liệt kê nhóm API chưa gắn màn hình nào, để không ai phải phát hiện bằng cách
    gặp lỗi 403 trên hệ thống thật.
    """
    cho_phep = pham_vi_day_du(u.role)
    if any(path.startswith(p) for p in cho_phep):
        return
    # Endpoint tự lọc theo người đăng nhập không nằm sau màn hình của vai trò nào – nó phục vụ CHÍNH
    # người gọi. Chặn nó bằng hàng rào suy từ ma trận menu là khóa người lao động khỏi phiếu lương và
    # khoản lương treo của chính họ.
    if any(_khop_duong(path, m) for m in duong_tu_loc()):
        return
    raise HTTPException(403, f"Vai trò {ROLES.get(u.role, u.role)} không có màn hình nào dùng tới "
                             f"dữ liệu này ({path})")


# Ma trận công bố cho giao diện / tài liệu (vai trò → nhóm màn hình được xem)


PRODUCT_COST_KEYS = ("cost_structure", "cost_lines", "fixed_cost", "var_cost_per_pax", "cost_items")


def mask_product(out: dict, u: User) -> dict:
    """Kinh doanh / HCNS thấy sản phẩm, giá bán, chương trình – không thấy cơ cấu chi phí NCC.

    CỐ Ý KHÔNG nới theo quyết định 24/9/2026 (xem `can_see_cost_tren_chuyen` ngay dưới): quyết định
    ấy mở giá vốn của MỘT CHUYẾN ĐOÀN cho người bán chuyến ấy, không mở bảng giá nhà cung cấp của
    cả danh mục sản phẩm. Hai thứ khác nhau: một bên là con số của đoàn đang thương lượng, bên kia
    là giá mua của công ty trên 313 mã sản phẩm.
    """
    if not can_see_cost(u):
        for k in PRODUCT_COST_KEYS: out[k] = None
    return out


def can_see_cost_tren_chuyen(u: User, tour) -> bool:
    """Người này xem được giá vốn CỦA CHUYẾN NÀY không?

    ── LẦN NỚI 24/9/2026, VÀ VÌ SAO NÓ HẸP ĐÚNG NHƯ THẾ NÀY ───────────────────────────────────
    Chủ tịch quyết: Kinh doanh Đoàn tự lập dự toán, kể cả phần giá vốn. Muốn lập được thì phải
    nhìn thấy — nên khối Kinh doanh được mở giá vốn.

    Nhưng mở ở ĐÂU thì quyết định cả hậu quả, và ba cách mở dưới đây khác nhau rất xa:

      a) Thêm SALES vào COST_ROLES  → khối Kinh doanh xem được giá vốn MỌI chuyến, cả tour lẻ,
         cộng cơ cấu chi phí của toàn bộ danh mục sản phẩm qua `mask_product`. Rộng nhất, và
         phần dôi ra không ai dùng tới nhưng vẫn là quyền đã cấp.
      b) Mở theo CHUYẾN, chỉ chuyến đoàn  → đúng bằng việc được giao. Đây là cách đang làm.
      c) Mở theo chuyến VÀ theo người phụ trách  → hẹp hơn nữa, nhưng nó khoá luôn Trưởng phòng
         và Giám đốc Kinh doanh khỏi dự toán của nhân viên mình, trong khi chính họ là người
         phải rà trước khi Sale Admin chuyển đi. Hẹp quá thành ra chặn nhầm người kiểm.

    Cái này KHÔNG mở: màn hình /nha-cung-cap, bảng giá NCC ngoài chuyến, và giá vốn tour LẺ.
    Người ngồi với khách đoàn nhìn thấy giá mua của đoàn ấy — không nhìn thấy giá mua của công ty.

    Hàm nhận `tour` chứ không nhận `tour_type`: phân mảng là luật đã có chủ ở `rules.is_doan`, và
    hỏi lại nó thì hàm này không bao giờ lệch với chỗ định tuyến duyệt.
    """
    if can_see_cost(u):
        return True
    if u.role not in SALES or tour is None:
        return False
    from app.services import rules as R
    return R.is_doan(tour)


def can_see_du_toan_ba_con_so(u: User, tour=None) -> bool:
    """BẬC HAI của cùng một câu hỏi: được nhìn BA CON SỐ DỰ TOÁN, nhưng không nhìn giá vốn thật.

    Chủ tịch quyết 25/9/2026: "Tour lẻ là do Phòng Điều hành tạo lịch khởi hành, sales lẻ chỉ việc
    bán." — và "sales lẻ chỉ nhìn thấy dự toán 3 con số như trong file quyết toán tour của Điều
    hành." Người bán cần biết chuyến còn lời bao nhiêu để trả lời khách xin giảm giá; họ không cần
    biết công ty mua của ai với giá nào.

    Ba bậc, không phải hai:

        can_see_cost                 → mọi thứ, mọi chuyến (Điều hành, Kế toán, Ban lãnh đạo…)
        can_see_cost_tren_chuyen     → thêm: Kinh doanh trên chuyến ĐOÀN của mình (24/9/2026)
        can_see_du_toan_ba_con_so    → thêm: Kinh doanh trên chuyến LẺ — CHỈ ba con số + số máy
                                       tính ra từ ba con số ấy (hoà vốn, lợi nhuận, biên)

    Bậc ba KHÔNG mở: dòng chi phí nhà cung cấp, tên và giá của NCC, đề nghị chi, bảng quyết toán,
    nhật ký sửa giá vốn. Đó là ranh giới "không liên quan giá vốn" của Chủ tịch — ba con số là một
    bản tóm tắt, giá vốn là danh sách mình mua của ai.
    """
    return can_see_cost_tren_chuyen(u, tour) or (u.role in SALES and tour is not None)


# Khoá thuộc GIÁ VỐN THẬT: dòng NCC, chứng từ, số quyết toán, nhật ký sửa giá vốn.
CHE_GIA_VON = ("settlement", "actual_cost", "promo_value", "justification",
               "cost_lines", "cost_total", "settlement_edit", "payment_requests", "audit")
# Khoá thuộc BA CON SỐ DỰ TOÁN và những số máy tính ra từ chúng.
CHE_BA_CON_SO = ("fixed_cost", "var_cost_per_pax", "calc", "hoa_hong_khach_bien")
# Trong `summary` của màn hình chi tiết: những ô dựng trên chi phí THỰC TẾ.
CHE_SUMMARY = ("cost_actual", "cost_paid", "profit", "profit_state", "cost_basis", "cost_lines", "warning")
# Rỗng kiểu nào: danh sách trả về [] để màn hình `.map` không nổ; còn lại trả None.
_RONG_LA_LIST = ("cost_lines", "payment_requests", "audit")


def che_gia_von(v: dict, u: User, tour, db=None) -> dict:
    """Che phần giá vốn của một bản `tour_view` theo đúng ba bậc trên. Sửa tại chỗ và trả lại `v`.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    VÌ SAO LÀ MỘT HÀM, VÀ VÌ SAO NÓ PHẢI CHẠY CUỐI CÙNG
    ═══════════════════════════════════════════════════════════════════════════════════════════
    `GET /tours/{id}` và `GET /tours/{id}/detail` đọc cùng một chuyến. Trước hôm nay mỗi cửa chép
    một khối che riêng — và hai bản chép đã lệch nhau một lần rồi (vòng 2 sửa cửa này, bỏ sót cửa
    kia). Một hàm thì không lệch được.

    CHẠY CUỐI CÙNG là phần quan trọng hơn. Khối che cũ của `tour_detail` nằm ở GIỮA hàm, còn
    `cost_lines`, `cost_total`, `settlement_edit`, `payment_requests` và `audit` được gắn vào SAU
    nó — nên chúng chưa từng bị che một lần nào. Màn hình không bày ra (tab bị ẩn khi `calc` rỗng),
    nhưng dữ liệu vẫn nằm nguyên trong phản hồi: tên nhà cung cấp, đơn giá mua, số tiền đã chi.
    Màn hình che không phải là cửa che.
    """
    # Hai lá cờ cho MÀN HÌNH. Trước nay màn hình đoán quyền bằng `calc != null` — suy quyền từ
    # hình dạng dữ liệu. Nay bậc ba trả `calc` CÓ mà giá vốn KHÔNG, nên phép đoán ấy sai: tab
    # "Chi NCC & quyết toán" sẽ hiện ra rỗng cho người không được xem. Máy chủ nói thẳng.
    v["xem_gia_von"] = can_see_cost_tren_chuyen(u, tour)
    v["xem_du_toan"] = can_see_du_toan_ba_con_so(u, tour)
    if v["xem_gia_von"]:
        return v
    for k in CHE_GIA_VON:
        if k in v: v[k] = [] if k in _RONG_LA_LIST else None
    if isinstance(v.get("summary"), dict):
        for k in CHE_SUMMARY: v["summary"].pop(k, None)
    if not can_see_du_toan_ba_con_so(u, tour):
        for k in CHE_BA_CON_SO:
            if k in v: v[k] = None
    if db is not None:
        vis = sales_ids_visible(db, u)
        if vis is not None:
            v["bookings"] = [b for b in v.get("bookings", []) if b.get("sales_id") in vis]
    return v


# Menu giao diện web theo vai trò (đường dẫn trang → vai trò được thấy). Trang không liệt kê = mọi vai trò đã đăng nhập.
MENU_ROLES = {
    # Mỗi dòng = BASE_VIEW (Chủ tịch, TGĐ, Ban Kiểm soát) + đúng những vai trò có việc trên màn hình đó.
    # Viết thẳng tên vai trò thay vì cộng các nhóm lớn: nhóm lớn là thứ đã làm bảy vai trò tự động nhìn
    # thấy mọi màn hình mới mà không ai quyết định. Dài hơn, nhưng đọc là biết ai xem được gì.

    # TC-41 – Kế hoạch tháng. Cùng danh sách với cửa màn hình ở MAN_HINH_API phía trên; lệch hai chỗ
    # này là có vai trò thấy mục menu rồi bấm vào nhận 403, hoặc mở được màn hình mà không có mục menu
    # để tới nó.
    "/ke-hoach-thang": BASE_VIEW + ("ketoan", "cntt"),

    # --- Kinh doanh & sản phẩm ---
    "/products": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt"),
    "/tours": BASE_VIEW + SALES + OPERATIONS + SALES_ADMIN + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt"),
    "/requests": BASE_VIEW + SALES + OPERATIONS + SALES_ADMIN + ("ptgd_doan", "cntt"),
    "/bookings": BASE_VIEW + SALES + OPERATIONS + SALES_ADMIN + ("ptgd_doan", "ptgd_mkt", "ketoan", "cntt"),
    "/non-package": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ketoan", "cntt"),
    "/sales-reports": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ptgd_mkt", "ketoan", "hcns", "cntt"),
    # Lãi lỗ theo tour: số quản trị. Sale KHÔNG có mặt – họ xem doanh thu và công nợ booking mình
    # phụ trách ở màn hình bán hàng, còn giá vốn của chuyến thì ngoài phạm vi của họ.
    # Bàn làm việc của Phó TGĐ tour đoàn (24/9/2026). HẸP NHẤT trong cả bảng, và cố ý: màn hình này
    # là HÀNG ĐỢI KÝ của đúng một người. Thêm một vai vào đây không phải là "cho xem thêm" mà là làm
    # cho hàng đợi của người ký trông như hàng đợi của nhiều người — rồi ai cũng tưởng có người khác
    # lo. Ai cần nhìn việc của cả phòng thì nhìn ở /so-con-no và /lai-lo-tour.
    # Điều hành KHÔNG có mặt: họ trình dự toán, không đứng cùng phía với người duyệt nó.
    "/ptgd-doan": BASE_VIEW + ("ptgd_doan", "cntt"),
    # Bàn làm việc của Sale Admin phòng Đoàn. `ptgd_doan` CÓ mặt — khác hẳn dòng trên, và có lý do:
    # đây không phải hàng đợi ký của một người, nó là danh sách việc tồn đọng của một phòng, và
    # người phụ trách mảng đoàn phải nhìn được phòng mình đang đọng ở đâu.
    # Khối Kinh doanh KHÔNG có mặt: màn hình này là chỗ SOÁT hồ sơ của chính họ; để người bị soát
    # đứng cùng chỗ với người soát thì cái cổng chỉ còn là một dòng chữ.
    "/sales-admin": BASE_VIEW + SALES_ADMIN + ("ptgd_doan", "cntt"),
    # Bàn bán tour lẻ — Chủ tịch quyết 25/9/2026. SALES chứ không phải SALES_ADMIN: đây là phòng
    # Kinh doanh LẺ. Phòng Đoàn không có tên ở đây ("ý là PKDL, còn PKDĐ vẫn giữ nguyên") —
    # bàn của họ là /sales-admin và /ptgd-doan, và chỗ ngồi tour lẻ không phải việc của họ.
    "/ban-tour-le": BASE_VIEW + SALES + ("cntt",),
    # Đánh giá sau tour (25/9/2026). MÀN HÌNH mở cho cả khối Kinh doanh, nhưng HAI KHỐI VIỆC
    # trên đó có hai danh sách vai khác nhau, và ranh giới nằm ở MÁY CHỦ chứ không ở màn hình:
    #   · danh sách "khách chưa chấm" + cửa ghi hộ → cả nv_kd, tn_kd (khách của chính họ)
    #   · BẢNG XẾP HẠNG HDV / tài xế            → không có nv_kd, tn_kd (xem api/v1/danh_gia.XEM)
    # Nhân viên mở màn hình này thì cửa bảng điểm trả 403 và màn hình không vẽ khối ấy. Che ở
    # màn hình là một tiện nghi; hàng rào thật nằm ở chữ ký của cửa.
    "/danh-gia": BASE_VIEW + OPERATIONS + SALES + ("ptgd_doan", "ptgd_mkt", "nv_mkt", "hcns", "cntt"),
    "/lai-lo-tour": BASE_VIEW + OPERATIONS + SALES_ADMIN + ("ptgd_doan", "ketoan", "cntt"),
    # TC-71 · Sổ chuyến còn nợ — anh Tuấn 18/9/2026 chọn ba nhóm: Chủ tịch/TGĐ, Điều hành, Kế toán.
    # ĐÚNG BẰNG `/lai-lo-tour` và cùng một lý do: cả hai màn hình nói về sổ quyết toán của chuyến,
    # nên hai danh sách vai khác nhau cho cùng một miền là hai danh sách sẽ lệch nhau về sau.
    # Kế toán CÓ mặt dù họ không đóng sổ chuyến: họ cần biết còn bao nhiêu chuyến chưa về sổ để
    # liệu việc ghi sổ tháng — không thấy thì đến cuối tháng mới biết còn 24 tỷ chưa vào.
    # Sale KHÔNG có mặt, y như /lai-lo-tour: giá vốn chuyến ngoài phạm vi của họ.
    "/so-con-no": BASE_VIEW + OPERATIONS + SALES_ADMIN + ("ptgd_doan", "ketoan", "cntt"),
    # TC-73 – so do to chuc khoi Kinh doanh. Ca khoi Kinh doanh XEM duoc: biet minh thuoc dau va ai
    # cung team khong phai bi mat. GHI thi hep hon nhieu, khai rieng o api/v1/to_chuc_kd.py – nguoi tu
    # ve duoc cay to chuc cua minh la nguoi tu cap duoc pham vi xem cua minh.
    "/to-chuc-kd": BASE_VIEW + SALES + SALES_ADMIN + ("hcns", "hanh_chinh", "ptgd_doan", "cntt"),
    # TC-74 - ai duoc ban hang. Ke toan co o day ma khong co o /to-chuc-kd: doi tac la ben thu ba
    # co cong no va hoa don nen Ke toan phai biet danh muc ay; so do to chuc noi bo thi khong.
    "/nguoi-ban-hang": BASE_VIEW + SALES + SALES_ADMIN + ("hcns", "hanh_chinh", "ptgd_doan", "ketoan", "cntt"),
    # TC-75 - gop tai khoan trung. HEP: khong co vai Kinh doanh nao. Doc bang cap trung thi HCNS
    # va Ke toan can (ho la nguoi phat hien ra trung), nhung nut gop thi chi cntt va Ban TGD -
    # khai rieng o api/v1/gop_tai_khoan.py. Gop la viec mot chieu: chuyen 290 booking sang nham
    # nguoi roi thi khong co nut tach ra lai.
    "/gop-tai-khoan": BASE_VIEW + ("hcns", "ketoan", "cntt"),
    # TC-81 - Bao chi, KOL & su kien. HEP HON "/marketing": khong co gd_kd va khong co ketoan.
    # Day la so thuong hieu va danh ba nguoi hop tac noi dung, khong phai so tien - phan tien cua
    # KOL di duong de nghi chi nhu moi khoan khac, va Ke toan doc no o man hinh Ngan sach.
    "/bao-chi-kol": BASE_VIEW + MARKETING + ("ptgd_mkt", "cntt"),
    # TC-76 - man hinh Kinh doanh Le. Dong da duoc cat o may chu theo phan cong
    # (to_chuc_kd.pham_vi_xem), nen rong o day khong co nghia la ai cung thay so cua nguoi khac.
    "/kinh-doanh-le": BASE_VIEW + SALES + ("hcns", "ketoan", "ptgd_doan", "cntt"),
    # TC-77 - dong gop doanh thu cua Marketing. Dung BANG danh sach vai cua "/marketing": ai lap
    # duoc ngan sach thi xem duoc ket qua cua ngan sach ay, khong rong hon mot vai nao.
    "/dong-gop-marketing": BASE_VIEW + MARKETING + ("ptgd_mkt", "gd_kd", "ketoan", "cntt"),
    # TC-78 - nhom 2.6. RONG HON /dong-gop-marketing, co y: ba cau cua nhom nay hoi ve QUANG
    # GIUA hai phong (Marketing giao lead, Sales xu ly), nen ca hai ben phai nhin cung mot bang.
    # Giau nua bang khoi mot ben la cach chac chan de moi phong tu giu mot con so rieng.
    "/chuyen-doi-lead": BASE_VIEW + MARKETING + SALES + ("ptgd_mkt", "ptgd_doan", "hcns", "cntt"),
    # TC-79 - nhom 2.8, ban can doi soat. BANG DUNG danh sach vai cua /dong-gop-marketing: day
    # la cau hoi ve so cua Marketing, khong phai ve viec cua tung nguoi ban.
    "/doi-soat-marketing": BASE_VIEW + MARKETING + ("ptgd_mkt", "gd_kd", "ketoan", "cntt"),

    # V7 Đợt 3 – Sự cố tour. Điều hành cầm việc; Kinh doanh có mặt vì sale thường là người khách gọi
    # đầu tiên khi chuyến trục trặc; Kế toán đọc để biết khoản chi phát sinh của chuyến từ đâu ra.
    # GHI và ĐÓNG hẹp hơn hẳn, và chặn đó nằm ở chữ ký từng đường dẫn (su_co_tour.GHI / .DONG).
    #
    # GĐ Đội xe và TP Hướng dẫn vào đây theo quyết định của anh Tuấn ngày 10/9/2026 – sự cố xe và sự
    # cố hướng dẫn viên đúng là việc của họ. Hai vai này dùng DANH SÁCH CHO PHÉP nên còn phải có tên
    # trong RESTRICTED_ROLE_MENUS bên dưới; thiếu chỗ đó thì dòng này chỉ nới quyền API mà họ vẫn
    # không thấy mục menu (đúng cái bẫy bản đầu của đợt này mắc phải).
    #
    # Mở màn hình KHÔNG mở dữ liệu khách: bản đầu để bốn ô chọn gọi thẳng /bookings, /khieu-nai,
    # /suppliers, /tours nên nới cho gd_doi_xe thêm chín nhóm API. Nay cả bốn ô đi qua chính phân hệ
    # này (xem MAN_HINH_API ở trên), và tên khách chỉ trả cho vai trò trong su_co_tour.KHACH – hai
    # vai này không có trong đó.
    "/su-co-tour": BASE_VIEW + OPERATIONS + SALES + FLEET_MGR + GUIDE_MGR + SALES_ADMIN + ("ptgd_doan", "ketoan", "cntt"),

    # --- Marketing & CSKH. Kế toán và CNTT KHÔNG có mặt: đây là dữ liệu khách của Marketing. ---
    "/inbox": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "cntt"),
    "/leads": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "cntt"),
    "/marketing": BASE_VIEW + MARKETING + ("ptgd_mkt", "gd_kd", "ketoan", "cntt"),   # chiến dịch: Marketing lập, Kế toán đối chiếu chi phí
    # Nội dung & thương hiệu là SỔ DUYỆT, không phải thư viện ảnh: hanh_chinh có mặt vì pháp chế nằm ở khối
    # đó và là người ký thứ hai cho nội dung có cam kết với khách hoặc có số liệu tài chính.
    "/noi-dung": BASE_VIEW + MARKETING + ("ptgd_mkt", "hanh_chinh", "cntt"),
    # Khiếu nại của KHÁCH. Mở cho cả Kinh doanh và Điều hành vì họ là người tiếp nhận và người xử lý;
    # Kế toán có mặt để đối chiếu chứng từ hoàn tiền gắn trên hồ sơ.
    "/khieu-nai": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "ptgd_doan", "ketoan", "cntt"),
    # Chăm sóc sau bán: phiếu tự sinh giao cho chính nhân viên đã bán, nên khối Kinh doanh phải mở được.
    "/cham-soc": BASE_VIEW + SALES + OPERATIONS + MARKETING + ("ptgd_mkt", "ptgd_doan", "cntt"),

    # --- Điều hành ---
    "/ops": BASE_VIEW + OPERATIONS + ("ptgd_doan", "ketoan", "hcns", "cntt"),
    # Khối Kinh doanh có mặt vì hồ sơ visa mang cột sales_user_id và có nút phân công người bán: bên
    # trong, visa.scope() chỉ cho họ thấy hồ sơ MÌNH ĐƯỢC GIAO, và cơ cấu giá vốn vẫn bị che
    # (/ho-so/{id}/thu-chi trả 403). Bỏ họ khỏi dòng này thì ô phân công thành ô chết, và nhân viên bán
    # hàng không trả lời được câu "hồ sơ visa của khách tôi tới đâu rồi" – trong khi máy chủ vẫn khai
    # nv_kd ở visa.READ. Hai cửa nói ngược nhau thì cửa nào cũng mất nghĩa.
    "/visa": BASE_VIEW + OPERATIONS + SALES + VISA_STAFF + ("ptgd_doan", "ketoan", "hcns", "cntt"),

    # --- Vận tải & Hướng dẫn viên ---
    "/xe-hdv": BASE_VIEW + OPERATIONS + FIELD + ("hcns", "cntt"),

    # --- Nhân sự – Hành chính ---
    # Đơn nghỉ phép của tôi (mục 5.4b cây phân hệ). MỞ CHO MỌI NGƯỜI LÀM VIỆC Ở ĐÂY. Màn hình chỉ có
    # MỘT khung – khung gửi đơn của chính mình – và cửa `/leaves` tầng dưới lọc ba tầng, nên người
    # thường thấy đơn của mình, còn người ký của một phòng thấy thêm đơn của phòng ấy.
    #
    # `+ READ_ALL` không phải cho gọn: `robot_ks` phải có mặt ở MỌI dòng của bảng này (hàng rào
    # `test_ma_tran_quyen` canh đúng điều đó) – robot Kiểm soát không soi được màn hình nó không thấy.
    # Nó KHÔNG lọt vào `MOI_NHAN_VIEN` vì nhóm ấy là nhóm của NGƯỜI; lớp `READ_ONLY_ROLES` chặn mọi
    # thao tác ghi của nó, nên có mặt ở đây là vô hại.
    "/cham-cong": MOI_NHAN_VIEN + READ_ALL,
    # Ba màn hình dưới trước 07/9/2026 KHÔNG khai quyền, nên theo quy ước "trang không liệt kê = ai đăng
    # nhập cũng thấy", một nhân viên kinh doanh vẫn mở được hồ sơ xe và bảng giá vốn – lợi nhuận đội xe.
    "/doi-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("ketoan", "hcns", "cntt"),
    "/lenh-dieu-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("hcns", "cntt"),
    "/hieu-qua-doi-xe": BASE_VIEW + FLEET_MGR + ("tp_dh", "ketoan", "hcns"),
    # Lãi lỗ đội xe gồm lãi vay và chi phí cố định của cả đội – đây là kết quả kinh doanh của một trung
    # tâm lợi nhuận, không phải bảng theo dõi vận hành. Điều hành và HCNS không xem.
    "/lai-lo-doi-xe": BASE_VIEW + FLEET_MGR + ("ketoan", "cntt"),

    # --- Tài chính & Kế toán. Ba màn hình tiền thu về Kế toán; hai Phó TGĐ và CNTT không còn xem. ---
    "/collections": BASE_VIEW + SALES + OPERATIONS + ("ptgd_doan", "ketoan", "cntt"),
    "/expenses": PAYMENT_REQUEST_ROLES,
    "/accounting": BASE_VIEW + ("ketoan", "tp_dh", "cntt"),
    "/finance": FINANCE_ROLES,
    "/bank-accounts": FINANCE_ROLES,
    # Sổ công nợ toàn hệ thống: phải thu của khách và phải trả nhà cung cấp là số tiền của cả công ty.
    # Nhân viên kinh doanh theo dõi booking của mình ở màn hình bán hàng, không mở sổ công nợ toàn công ty.
    "/cong-no": BASE_VIEW + SALES_ADMIN + ("ketoan", "ptgd_doan", "tp_dh", "cntt"),
    # Nhà cung cấp & đặt dịch vụ: Điều hành đặt dịch vụ, Kế toán xác nhận đổi tài khoản. Khối Kinh doanh
    # không xem – đây là cơ cấu chi phí nhà cung cấp.
    "/nha-cung-cap": BASE_VIEW + OPERATIONS + ("ptgd_doan", "ketoan", "cntt"),
    # Nạp dữ liệu: màn hình mở cho các phòng có dữ liệu để nạp, còn CHẶN THEO TỪNG BỘ NẠP nằm ở
    # app/services/intake.VAI_TRO – mở được trang không có nghĩa là nạp được sổ của phòng khác.
    #
    # Hai Phó TGĐ thêm 09/9/2026, sau khi bản rà cửa nhập chỉ ra một chỗ hai danh sách nói ngược nhau:
    # intake.VAI_TRO cho phép ptgd_doan nạp booking và quyết toán tour, cho phép ptgd_mkt nạp nguồn
    # khách và chi phí marketing theo kênh – nhưng menu của cả hai lại không có màn hình này. Hai phân
    # hệ độc lập cùng cấp quyền cho hai người mà cả hai menu cùng thiếu; Chủ tịch chốt ngày 09/9: hai
    # Phó TGĐ quản lý phòng của mình, nên menu là chỗ lạc hậu, không phải danh sách quyền.
    #
    # Mở màn hình KHÔNG nới quyền nạp: chặn theo từng bộ nạp vẫn nằm ở intake.VAI_TRO, nên mỗi ông chỉ
    # nạp được đúng những loại dữ liệu của phòng mình, và màn hình nói thẳng "chỉ xem" với loại của
    # phòng khác.
    "/nap-du-lieu": BASE_VIEW + OPERATIONS + SALES + FLEET_MGR + GUIDE_MGR + SALES_ADMIN + ("ketoan", "hcns", "cntt",
                                                                              "nv_mkt", "ptgd_doan",
                                                                              "ptgd_mkt"),
    # Đọc chứng từ ảnh (cửa 3). Mở cho phòng SỞ HỮU con số, cộng CNTT vì CNTT vận hành mô hình – nhưng
    # CNTT không bấm xác nhận được: chặn đó nằm ở intake.duoc_xac_nhan_anh, không nằm ở danh sách này.
    # KHÔNG mở cho HCNS: bốn loại chứng từ đang mở không có loại nào của HCNS, và bảng lương với bảng
    # bảo hiểm thì cấm đọc bằng máy (Nghị định 13/2023) – mở màn hình cho họ là mời hiểu nhầm.
    "/doc-chung-tu": BASE_VIEW + OPERATIONS + FLEET_MGR + ("ketoan", "ptgd_doan", "cntt"),
    # Tệp & hình ảnh: chứng từ đi kèm gần như mọi nghiệp vụ nên mở rộng; gỡ tệp thì hẹp hơn (xem API).
    "/tep": BASE_VIEW + OPERATIONS + SALES + FLEET_MGR + GUIDE_MGR + SALES_ADMIN + ("ketoan", "hcns", "cntt", "nv_mkt",
                                                                      "nv_visa", "hanh_chinh"),
    # Phòng Hướng dẫn: màn hình riêng của người điều phối. KHÔNG mở /ops cho vai trò này – màn hình đó
    # lấy danh sách người từ /employees, tức là kèm luôn lương của mọi phòng.
    "/huong-dan": BASE_VIEW + OPERATIONS + GUIDE_MGR + ("ptgd_doan", "hcns", "ketoan", "cntt"),

    # Hợp đồng lao động: hồ sơ cá nhân của từng người, kèm bản scan trong nhóm 06_Nhan_su. HCNS giữ hồ
    # sơ, Ban TGĐ và Chủ tịch điều hành, Ban Kiểm soát rà soát. Kế toán KHÔNG xem – lương lấy từ bảng
    # lương, không cần đọc hợp đồng của từng người.
    "/hop-dong-lao-dong": BASE_VIEW + ("hcns", "cntt"),
    # Tài sản & mua sắm: nguyên giá, khấu hao và ghi sổ – việc của Kế toán. Hành chính xem để theo dõi
    # tài sản đang ở bộ phận nào.
    # Hồ sơ tài xế: ĐÚNG BẰNG dòng "/doi-xe" ở trên. Hồ sơ xe và hồ sơ người lái xe là cùng một
    # tập hồ sơ đội xe; mở lệch nhau là mở một đường vòng vào thứ mình vừa đóng ở cửa kia.
    "/tai-xe": BASE_VIEW + OPERATIONS + FLEET_MGR + ("ketoan", "hcns", "cntt"),
    "/tai-san": BASE_VIEW + ("ketoan", "cntt", "hanh_chinh", "hcns"),
    # 5.9.2 Đề nghị mua — mở cho MỌI NGƯỜI LÀM VIỆC Ở ĐÂY, cùng khuôn với /cham-cong. `+ READ_ALL`
    # không phải cho gọn: `robot_ks` phải có mặt ở MỌI dòng của bảng này (test_ma_tran_quyen canh
    # đúng điều đó), và lớp READ_ONLY_ROLES chặn mọi thao tác ghi của nó nên có mặt là vô hại.
    "/de-nghi-mua": MOI_NHAN_VIEN + READ_ALL,

    # --- Hành chính & Nhân sự (tách quyền theo tab, xem HR_TAB_ROLES) ---
    "/hr": HR_TAB_ROLES["payroll"] + HR_TAB_ROLES["employees"] + HR_TAB_ROLES["incidents"]
           + HR_TAB_ROLES["tong_quan"] + HR_TAB_ROLES["cham_cong"],

    # --- Kiểm soát & Chính sách ---
    "/params": PARAM_ROLES,
    # IR – Pháp chế (Đợt D1, 08/10/2026). HẸP HƠN HẲN các màn hình nghiệp vụ, và có lý do:
    # văn bản HĐQT và hồ sơ công bố thông tin của một công ty niêm yết là chuyện của Ban
    # Tổng giám đốc, Pháp chế và Kiểm soát – không phải của phòng ban. Ban Kiểm soát và CNTT
    # ĐỌC mà không ghi; chữ ký ghi nằm ở api/v1/phap_che.py::GHI, không nằm ở đây.
    # Sửa 08/10/2026 chiều: dòng này khai TAY bốn tên thay vì cộng `BASE_VIEW`, nên thiếu `robot_ks` và
    # `test_ma_tran_quyen` đỏ — main đỏ thì mọi làn đỏ theo. KHÔNG nới cho ai: `BASE_VIEW` là
    # (chutich, tgd, bks, robot_ks), tức đúng danh sách cũ cộng robot Kiểm soát, vai chỉ-đọc mà lớp
    # `READ_ONLY_ROLES` chặn mọi thao tác ghi. Robot Kiểm soát không soi được màn hình nó không thấy.
    "/ir-phap-che": BASE_VIEW + ("ir_phapche", "cntt"),
    "/audit": AUDIT_ROLES,
    # Bàn làm việc của robot Kiểm soát. Nguyên tắc 07/9 giữ nguyên và không bị nới ở đây: PHÒNG BAN
    # KHÔNG ĐỌC KẾT QUẢ GIÁM SÁT CHÍNH MÌNH – việc phải làm thì hiện ở màn hình Ngoại lệ của họ.
    #
    # Kế toán có mặt trong dòng này, và điều đó KHÔNG trái nguyên tắc trên, vì hai thứ khác nhau đang
    # nằm chung một tiền tố đường dẫn:
    #   · /api/v1/kiem-soat            – bàn làm việc giám sát: phát hiện, ĐIỂM phòng ban, BÁO CÁO
    #   · /api/v1/kiem-soat/cot-tien…  – rà soát kỹ thuật của K1/K2: một cột là tiền hay không
    # Việc thứ hai là phán đoán KẾ TOÁN, và chính robot Kiểm soát chỉ định Kế toán trưởng làm người
    # quyết. Hàng rào phạm vi (P2) chỉ phân biệt được tới mức tiền tố, nên muốn Kế toán làm được việc
    # thứ hai thì phải cho họ chạm tiền tố – không có cách nào hẹp hơn ở lớp này.
    #
    # RANH GIỚI THẬT nằm ở lớp dưới, tại chữ ký từng đường dẫn: XEM của kiem_soat.py KHÔNG có ketoan,
    # nên Kế toán mở được màn hình mà KHÔNG đọc được phát hiện, điểm hay báo cáo. Phép thử
    # test_ketoan_ra_soat_duoc_nhung_khong_doc_duoc_giam_sat canh đúng chỗ đó – canh ở lớp API, không
    # canh ở dòng menu này, vì dòng menu không phải chỗ điều đó được bảo đảm.
    # Chủ tịch quyết 08/9/2026: KẾ TOÁN KHÔNG XEM MÀN HÌNH KIỂM SOÁT.
    #
    # Chặn ở tầng API vẫn giữ nguyên và vẫn là lớp thật (Kế toán gọi /api/v1/kiem-soat nhận 403).
    # Nhưng để mục menu ở đó rồi chặn từng đường dẫn là vẽ một cánh cửa mở ra chỉ để đóng lại – và
    # người dùng đọc cái MENU, không đọc bảng phân quyền.
    #
    # Kế toán trưởng vẫn là người QUYẾT một cột có phải tiền hay không (ks_ra_soat.QUYET). Việc đó
    # sang màn hình riêng dưới nhóm Tài chính & Kế toán: người bị chấm điểm không ngồi cùng bàn với
    # bảng chấm điểm, nhưng vẫn phải có bàn của mình.
    # Robot A · GD-1. Chủ tịch quyết 11/9/2026 về khối dòng tiền:
    #   · Chủ tịch, Kế toán, Ban Kiểm soát giữ TOÀN CẢNH – một bên lập số, một bên soát số.
    #   · Tổng giám đốc CHỈ xem tài chính hoạt động tour và xe; lọc theo TỪNG DÒNG là SEC-02 của làn
    #     Phân quyền, không phải việc của hàng rào ngoài này.
    #   · Hai Phó Tổng giám đốc KHÔNG thấy khối – cố ý không có mặt ở đây.
    #   · robot_ks có mặt theo luật chung đã có: robot Kiểm soát phải xem được MỌI màn hình, nếu
    #     không thì nó giám sát được mọi phòng trừ đúng phòng giữ tiền.
    "/dong-tien": ("chutich", "tgd", "ketoan", "bks", "robot_ks", "cntt"),
    "/kiem-soat": BASE_VIEW + ("cntt",),
    "/ra-soat-cot-tien": BASE_VIEW + ("ketoan", "cntt"),
    # V11 – "cái gì đang tự chạy" là câu hỏi của cả công ty, không riêng CNTT: một tác vụ im ba ngày
    # thì người phát hiện sớm nhất thường là phòng đang chờ số liệu đó. Nên XEM rộng. Khai báo tác vụ
    # thì hẹp, và chỗ chặn đó nằm ở API (tuple KHAI trong api/v1/tu_dong.py), không ở cửa màn hình.
    "/tu-dong-hoa": BASE_VIEW + ("cntt", "ketoan", "hcns", "tp_dh", "nv_dh", "gd_doi_xe",
                                 "tp_hd", "gd_kd", "tp_kd", "ptgd_mkt"),
    # CHỈ mở cho vai trò CÓ ít nhất một báo cáo. Vai trò không có báo cáo nào thì không thấy mục
    # menu này luôn – tốt hơn là thấy mục menu rồi bấm vào nhận thông báo "không có gì cho anh/chị",
    # vì mục menu chết làm người ta bấm lại mỗi tuần để xem đã có chưa.
    # Danh sách này phải khớp với bao_cao_phong.PHONG[*]["xem"]; lệch thì có vai trò mở được màn hình
    # mà không có báo cáo nào, hoặc ngược lại – có bộ kiểm canh chỗ đó.
    # CNTT KHÔNG có trong danh sách này, khác với hầu hết màn hình khác. Báo cáo ở đây là hiệu quả
    # kinh doanh của từng phòng, không phải tình trạng kỹ thuật; và quyết định của Chủ tịch nói rõ
    # người xem là trưởng phòng / giám đốc phòng đó và Ban lãnh đạo. Mở thêm cho CNTT "để hỗ trợ" là
    # cách một danh sách người xem lặng lẽ dài ra cho tới lúc không còn nghĩa gì.
    #
    # nv_visa RỜI danh sách ngày 10/9/2026. Bản 09/9 cho chuyên viên visa vào đây vì bộ phận Visa
    # chưa có người phụ trách – một chỗ vá tạm. Chủ tịch chốt Visa THUỘC Phòng Điều hành, nên người
    # chịu trách nhiệm về con số của Visa là Trưởng phòng Điều hành. Đây là SIẾT quyền: chuyên viên
    # vẫn làm và vẫn thấy hồ sơ của mình ở màn hình Visa, chỉ không còn cầm bản tổng hợp cả bộ phận.
    "/bao-cao": BASE_VIEW + ("tp_dh", "ptgd_doan", "gd_kd", "tp_kd", "ptgd_mkt", "gd_doi_xe",
                             "tp_hd", "ketoan", "hcns"),
    # TC-41 – Kế hoạch tháng. HẸP có chủ ý, và đây là chỗ dễ bị đòi nới nhất nên ghi lý do sẵn:
    # chỉ tiêu tháng là thước đo mà mọi phòng sẽ bị đo bằng nó. Trưởng phòng đọc được chỉ tiêu của
    # phòng mình ở báo cáo phòng; còn BẢNG CHỈ TIÊU CẢ NĂM của cả tập đoàn thì không phải thứ để mở
    # rộng "cho tiện". Ghi thì còn hẹp hơn nữa – chặn ở API (tuple GHI trong api/v1/ke_hoach.py),
    # không ở cửa màn hình, vì cửa màn hình chỉ có hai trạng thái mở/đóng.
    "/ke-hoach-thang": BASE_VIEW + ("ketoan", "cntt"),
    # V6 – chuỗi bán hàng. Bảng giá là CHÍNH SÁCH nên hẹp hơn báo giá: từng sale soạn báo giá
    # được, nhưng đặt giá niêm yết thì không.
    "/bang-gia": BASE_VIEW + ("gd_kd", "tp_kd", "ptgd_mkt", "ketoan", "cntt"),
    "/bao-gia": BASE_VIEW + SALES_ADMIN + ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "ptgd_mkt", "nv_mkt",
                             "tp_dh", "nv_dh", "ptgd_doan", "ketoan", "cntt"),
    # Hợp đồng là căn cứ ghi nhận doanh thu nên Kế toán phải xem được.
    "/hop-dong-khach": BASE_VIEW + SALES_ADMIN + ("gd_kd", "tp_kd", "tn_kd", "nv_kd", "ptgd_mkt",
                                    "ketoan", "cntt"),
    # Bảng quy ước hạch toán + cổng chặn giá vốn. Điều hành (tp_dh) xem được vì hàng đợi thiếu giá vốn
    # đứng tên phòng họ – bắt một phòng trả lời mà không cho họ nhìn thấy việc là cách chắc chắn để không ai trả lời.
    # Kết sổ một kỳ: sao kê vào sổ hàng loạt, kết chuyển, và trạng thái cả kỳ. Chỉ Kế toán GHI –
    # Chủ tịch, TGĐ và Ban Kiểm soát xem chứ không ghi thay (chặn nằm ở API, không ở menu).
    "/ket-so": BASE_VIEW + ("ketoan", "cntt"),
    # Sổ tỷ giá. Kế toán giữ sổ; Điều hành nhập tỷ giá của chuyến mình chi; Visa nhập tỷ giá phí
    # lãnh sự. Rộng hơn thế thì một con số NHÂN vào tiền có quá nhiều người sửa được.
    "/ty-gia": BASE_VIEW + OPERATIONS + ("ketoan", "nv_visa", "cntt"),
    # V7 Đợt 3 – Hồ sơ kiểm toán. Kế toán làm chủ hồ sơ; Ban Kiểm soát đọc theo nghĩa vụ Luật Doanh
    # nghiệp (đã nằm trong BASE_VIEW). HCNS, Hành chính, Điều hành có mặt vì họ CÓ MỤC phải nộp – hợp
    # đồng lao động là của HCNS, hồ sơ pháp lý và biên bản HĐQT là của Hành chính. Không mở cho họ thì
    # Kế toán thành người đưa thư, và mục nào chậm cũng thành lỗi Kế toán.
    #
    # GĐ Đội xe KHÔNG có mặt, dù danh mục mẫu có mục "hồ sơ đội xe: đăng kiểm, bảo hiểm, thế chấp".
    # Lý do giống dòng /su-co-tour ở trên: /ho-so-kiem-toan không nằm trong danh sách cho phép của
    # vai trò này nên mở cũng không thấy menu. Trong lúc chờ quyết định ấy, mục giấy tờ xe để phòng
    # ban "gd_doi_xe" và người phụ trách ghi tên – Kế toán vẫn đòi được đúng người, chỉ là đòi qua
    # kênh ngoài hệ thống.
    "/ho-so-kiem-toan": BASE_VIEW + ("ketoan", "cntt", "hcns", "hanh_chinh", "tp_dh", "ptgd_doan"),
    "/hach-toan": BASE_VIEW + ("ketoan", "cntt", "tp_dh"),
    # Ngoại lệ cần xử lý: nơi gom mọi lần một quy tắc bị bẻ. Mở cho những vai trò CÓ THỂ trả lời được
    # câu "vì sao lúc đó phải bẻ": Kế toán (tiền), Điều hành (chuyến), hai Phó TGĐ (duyệt), CNTT (tham số
    # và AI). Khối Kinh doanh không có mặt – họ là bên xin ngoại lệ, không phải bên rà.
    "/ngoai-le": BASE_VIEW + ("ketoan", "cntt", "tp_dh", "ptgd_doan", "ptgd_mkt"),

    # --- Điều hành Holdings & Hệ thống ---
    "/robot-reports": BASE_VIEW + ("ptgd_doan", "ptgd_mkt", "tp_dh", "gd_kd", "ketoan", "hcns", "cntt"),
    "/companies": BASE_VIEW + ("ketoan", "tp_dh", "hcns", "hanh_chinh", "cntt"),
    "/vietrip": BASE_VIEW + ("tp_dh", "ketoan", "cntt"),
    # Màn hình quản trị tài khoản: HCNS và CNTT thao tác, Chủ tịch và TGĐ quyết, Ban Kiểm soát chỉ đọc.
    "/access": BASE_VIEW + ("hcns", "cntt"),
    # Vị trí AI & quyền hạn: Phó TGĐ Marketing có mặt vì kiêm chỉ đạo CNTT và là người chủ quản hộp thư
    # đa kênh – nơi AI tiếp xúc khách hàng.
    "/ai-roles": BASE_VIEW + ("ptgd_mkt", "cntt"),
}

MATRIX = {
    "tours": MENU_ROLES["/tours"],
    "bookings": BOOKING_ROLES,
    "cost": COST_ROLES,
    "finance": FINANCE_ROLES,
    "audit": AUDIT_ROLES,
    "params": PARAM_ROLES,
    "payment_requests": PAYMENT_REQUEST_ROLES,
    "payroll": HR_TAB_ROLES["payroll"],
}

# Mọi trang có trong giao diện – kể cả trang không đặt điều kiện vai trò – để dựng danh sách ẩn cho vai trò bị giới hạn.
# "/phan-he/[khoa]" là TRANG MỤC LỤC của tám phân hệ (13/9/2026) – bấm thanh phân hệ trên menu
# dọc thì mở nó. Khai ở đây chứ không ở MENU_ROLES vì nó không phải màn hình nghiệp vụ: nó chỉ
# liệt kê lại những màn hình mà chính người dùng đã được thấy, và tự lọc theo hidden_menus của
# phiên. Có tên trong danh sách này thì vai trò bị giới hạn (tài xế, HDV, chuyên viên visa)
# cũng được quyết định có thấy hay không, thay vì mặc nhiên thấy vì chưa ai khai.
# "/dong-tien/nguon" thêm 14/9/2026 (TC-25) – TRANG CHI TIẾT của khối dòng tiền trên màn hình 01,
# đi tới bằng liên kết chứ không có mục menu. Khai ở đây chứ KHÔNG ở MENU_ROLES, đúng như
# "/phan-he/[khoa]" ở trên, vì hai lý do:
#   · MENU_ROLES đòi mỗi mục phải có một lối vào trong menu và một thư mục trang ở cấp một của
#     web/app; trang con không thoả cả hai, và ba phép thử canh đúng chỗ ấy (mt1, mt4, test_menu).
#   · Quyền của trang này KHÔNG cần khai riêng: nó chỉ gọi /api/v1/dong-tien, mà nhóm API ấy chỉ
#     mở cho vai có "/dong-tien" trong MENU_ROLES. Vai không có quyền gọi /dong-tien/meta sẽ nhận
#     403 và trang nói thẳng là không được xem — hàng rào nằm ở MÁY CHỦ, không nằm ở đường dẫn.
# Có tên ở đây thì vai trò bị giới hạn (tài xế, HDV, chuyên viên visa) vẫn được quyết định có thấy
# hay không, thay vì mặc nhiên thấy vì chưa ai khai.
ALL_MENU_PATHS = tuple(MENU_ROLES) + ("/", "/alerts", "/reports", "/payroll", "/phieu-luong",
                                      "/doi-mat-khau", "/phan-he/[khoa]", "/offline",
                                      "/dong-tien/nguon")


# Vai trò bị giới hạn: chỉ được thấy đúng những trang liệt kê ở đây.
# Quy ước mặc định "trang không liệt kê trong MENU_ROLES = mọi người đăng nhập đều thấy" là an toàn với nhân
# viên văn phòng, nhưng SAI với tài xế, HDV và chuyên viên visa: nó cho họ thấy cả Bảng lương và Tài khoản
# ngân hàng chỉ vì hai trang đó chưa được liệt kê. Với các vai trò dưới đây, danh sách là DANH SÁCH CHO PHÉP.
RESTRICTED_ROLE_MENUS = {
    # Màn hình đổi mật khẩu có mặt ở cả hai danh sách: đây là danh sách CHO PHÉP, mà tài xế, HDV và chuyên
    # viên visa cũng phải đổi được mật khẩu tạm của mình – thiếu dòng này là họ bị khóa ngoài hệ thống.
    # Hai vai cùng một danh sách màn hình: /xe-hdv là màn hình của người ở hiện trường, và nội dung
    # bên trong nó đi theo DỮ LIỆU của người đăng nhập (có xe đứng tên thì hiện khối xe, có thẻ HDV thì
    # hiện khối thẻ), không đi theo vai trò. Tách vai 05/10/2026 là để tách TUYẾN KÝ, không phải để
    # tách màn hình — nên hai dòng này giống nhau, và giống nhau ở đây là đúng.
    "tai_xe": ("/xe-hdv", "/doi-mat-khau"),
    "hdv": ("/xe-hdv", "/doi-mat-khau"),
    "nv_visa": ("/visa", "/doi-mat-khau"),
    # /su-co-tour thêm 10/9/2026 cho cả hai: xe hỏng giữa đèo là việc của GĐ Đội xe, hướng dẫn viên
    # bỏ đoàn là việc của TP Hướng dẫn – bắt họ nghe lại qua Điều hành là mất đúng mười lăm phút đầu.
    # Màn hình không mang theo dữ liệu khách: xem ghi chú ở dòng "/su-co-tour" của MENU_ROLES.
    "gd_doi_xe": ("/doi-xe", "/tai-xe", "/lenh-dieu-xe", "/hieu-qua-doi-xe", "/lai-lo-doi-xe",
                  "/xe-hdv", "/nap-du-lieu", "/tep", "/doc-chung-tu", "/su-co-tour",
                  "/doi-mat-khau"),
    "tp_hd": ("/huong-dan", "/xe-hdv", "/tep", "/nap-du-lieu", "/su-co-tour", "/doi-mat-khau"),
    # Ba vai trò máy: danh sách CHO PHÉP, giống bốn vai trò hẹp ở trên. Robot không có menu để bấm,
    # nhưng khai ở đây thì màn hình tra cứu ngược (P10) nói được nó chạm tới đâu, và bộ quét vai trò
    # đọc được phạm vi của nó mà không phải suy từ mã.
    # /doi-mat-khau có mặt ở cả ba vì tài khoản robot cũng được cấp mật khẩu tạm và cũng phải xoay
    # được mật khẩu của chính nó. Một tài khoản máy không đổi được mật khẩu là một mật khẩu đứng yên
    # vĩnh viễn trong hệ thống của công ty đại chúng.
    "robot_pq": ("/access", "/ai-roles", "/kiem-soat", "/doi-mat-khau"),
    "robot_vpm": ("/kiem-soat", "/doi-mat-khau"),
}

# Vai trò của MÁY, không phải của người. Tách ra thành một khái niệm riêng chứ không chỉ là quy ước đặt
# tên: nhiều bộ kiểm hỏi "vai trò này đã có ai chưa", "tài khoản này bỏ hoang chưa", "còn mật khẩu tạm
# không" – ba câu hỏi đúng với người và vô nghĩa với máy. Không tách thì hoặc bộ kiểm kêu suốt đời về ba
# vai trò không bao giờ có người, hoặc phải nới lỏng chính những bộ kiểm ấy cho cả người lẫn máy.
VAI_TRO_MAY = ("robot_pq", "robot_ks", "robot_vpm")


def la_vai_tro_may(vai_tro: str) -> bool:
    return vai_tro in VAI_TRO_MAY


# Hai điều cấm của P8, viết thành DỮ LIỆU để có thể canh bằng phép thử thay vì bằng trí nhớ.
# Mỗi dòng: vai trò máy → những tiền tố API nó KHÔNG được chạm, kèm lý do đọc được.
CAM_CUA_ROBOT: dict[str, dict[str, str]] = {
    "robot_vpm": {
        "/api/v1/ngoai-le": "Người viết phần mềm không được đóng ngoại lệ do chính mình gây ra – "
                            "đóng được thì mọi phát hiện đều biến mất bằng một lần bấm của người bị phát hiện.",
    },
    "robot_pq": {
        "/api/v1/tours": "Robot cầm chìa khoá quyền không được ghi số nghiệp vụ.",
        "/api/v1/bookings": "Robot cầm chìa khoá quyền không được ghi số nghiệp vụ.",
        "/api/v1/journal": "Robot cầm chìa khoá quyền không được ghi số nghiệp vụ.",
        "/api/v1/payment-requests": "Robot cầm chìa khoá quyền không được ghi số nghiệp vụ.",
        "/api/v1/receipts": "Robot cầm chìa khoá quyền không được ghi số nghiệp vụ.",
        "/api/v1/payroll-runs": "Robot cầm chìa khoá quyền không được chạm bảng lương.",
    },
    # robot_ks KHÔNG có dòng nào ở đây, và đó không phải sơ suất. Từ 09/9/2026 nó đọc toàn bộ như BKS,
    # nên điều cấm của nó không còn là "không được chạm tiền tố nào" mà là "KHÔNG ĐƯỢC GHI GÌ CẢ" –
    # một hàng rào rộng hơn và chặt hơn, thi hành bởi READ_ONLY_ROLES chứ không bởi bảng tiền tố.
    # Phép thử tương ứng thử GHI vào nhiều cửa khác nhau thay vì đọc bảng này.
}


def _grants(db, u: User) -> list:
    """Ngoại lệ còn hiệu lực của một người. db=None thì coi như không có – mọi chỗ gọi không có phiên
    cơ sở dữ liệu vẫn chạy đúng theo vai trò, chỉ là không thấy phần cấp lẻ."""
    if db is None: return []
    try:
        from sqlalchemy import select
        from app.models.core import UserGrant
        return [g for g in db.execute(select(UserGrant).where(UserGrant.user_id == u.id,
                                                              UserGrant.active == True)).scalars() if g.hieu_luc()]
    except Exception:      # noqa – bảng chưa có (cơ sở dữ liệu cũ) không được làm hỏng đăng nhập
        return []


def co_quyen(db, u: User, nang_luc: str) -> bool:
    """Năng lực cấp lẻ cho một người. Chủ tịch và TGĐ có sẵn mọi năng lực; Ban Kiểm soát ĐỌC được
    nhưng lớp chặn ghi chung vẫn giữ nguyên, nên ở đây không phải kể ra riêng."""
    if u.role in BASE_VIEW: return True
    return any(g.kind == "capability" and g.value == nang_luc for g in _grants(db, u))


def hr_tabs_for(db, u: User) -> list[str]:
    """Tab nào của màn hình Nhân sự người này mở được."""
    ra = []
    for tab, roles in HR_TAB_ROLES.items():
        cap = HR_TAB_CAPABILITY.get(tab)
        if u.role in roles or (cap and co_quyen(db, u, cap)): ra.append(tab)
    return ra


# Màn hình KHÔNG được phép biến mất khỏi menu của bất kỳ ai, kể cả bốn vai trò dùng danh sách CHO PHÉP.
# Danh sách này phải NGẮN, và mỗi dòng phải là việc mà một con người có tài khoản buộc phải tự làm được:
#   /doi-mat-khau  – mật khẩu tạm do HCNS đặt; không có lối đổi là bị khóa ngoài hệ thống.
#   /phieu-luong   – phiếu lương của chính mình; tài xế và HDV đều nằm trong bảng lương.
#
# ĐÍNH CHÍNH 08/9/2026. Bản trước của danh sách này có thêm "/", "/alerts" và "/reports", với lý do rằng
# tài xế, HDV và chuyên viên visa không có chỗ nộp báo cáo công việc hằng ngày. Lý do ấy SAI: bộ mẫu
# báo cáo ngày (ops.DEPT_FORMS) chỉ có bảy phòng văn phòng – kd_le, kd_doan, dieu_hanh, marketing,
# ketoan, hcns, cntt – không có đội xe, hướng dẫn hay visa. Ba vai trò đó KHÔNG phải nộp báo cáo ngày,
# nên ẩn /reports khỏi menu của họ là đúng, và ba phép thử vai trò nói vậy là ba phép thử đúng.
# Bài học ghi lại ở đây vì nó sẽ lặp: thấy một phép thử chặn điều mình cho là quyền lợi, phải đi tìm
# quyết định đằng sau nó trước, chứ không sửa phép thử cho khớp với suy đoán của mình.
# Trang mục lục phân hệ có mặt ở đây từ 13/9/2026: anh Tuấn chốt AI CŨNG THẤY ĐỦ TÁM PHÂN HỆ,
# kể cả tài xế, hướng dẫn viên và chuyên viên visa. Mục không có quyền thì KHOÁ lại chứ không
# giấu – giấu thì người ta không biết hệ thống có gì và không biết phải xin quyền ở đâu.
# Trang này không mang một con số nghiệp vụ nào, nó chỉ liệt kê TÊN màn hình.
MAN_HINH_KHONG_DUOC_AN = ("/doi-mat-khau", "/phieu-luong", "/phan-he/[khoa]")


def menus_for(u: User, db=None) -> list[str]:
    ra = (list(RESTRICTED_ROLE_MENUS[u.role]) if u.role in RESTRICTED_ROLE_MENUS
          else [path for path, roles in MENU_ROLES.items() if u.role in roles])
    ra += [p for p in MAN_HINH_KHONG_DUOC_AN if p not in ra]
    # Ngoại lệ cộng thêm cho CẢ vai trò bị giới hạn: nếu chỉ cộng ở một trong hai hàm thì danh sách hiện
    # và danh sách ẩn sẽ nói hai điều khác nhau về cùng một người.
    them = [g.value for g in _grants(db, u) if g.kind == "menu"]
    return ra + [p for p in them if p not in ra]


def hidden_menus_for(u: User, db=None) -> list[str]:
    if u.role in RESTRICTED_ROLE_MENUS:
        cho_phep = (set(RESTRICTED_ROLE_MENUS[u.role]) | set(MAN_HINH_KHONG_DUOC_AN)
                    | {g.value for g in _grants(db, u) if g.kind == "menu"})
        return [p for p in ALL_MENU_PATHS if p not in cho_phep]
    mo = set(menus_for(u, db))
    return [path for path in MENU_ROLES if path not in mo]
