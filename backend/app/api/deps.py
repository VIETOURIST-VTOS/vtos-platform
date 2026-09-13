"""Phụ thuộc chung: CSDL, người dùng hiện tại, kiểm tra vai trò."""
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.core.config import settings
from app.models.core import User, ROLES

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def current_user(request: Request, token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    data = decode_token(token)
    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập hết hạn hoặc không hợp lệ")
    u = db.execute(select(User).where(User.username == data["sub"], User.active == True)).scalars().first()
    if not u:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã khóa")
    from app.services.access import check_readonly_write, check_restricted_scope
    check_readonly_write(u, request.method, request.url.path)   # Ban Kiểm soát chỉ đọc
    check_restricted_scope(u, request.url.path)                 # tài xế / HDV / chuyên viên visa: chỉ màn hình của mình
    check_must_change_password(u, request.url.path)             # còn mật khẩu tạm thì chưa vào được dữ liệu
    return u


# Tài khoản còn mật khẩu tạm chỉ đi được đúng ba đường: xem mình là ai, đổi mật khẩu, và đăng xuất.
# Mật khẩu mặc định là mã nhân viên – thứ nằm công khai trên bảng lương – nên trước khi đổi, phiên đăng
# nhập này chưa chứng minh được người ngồi trước máy đúng là chủ tài khoản.
PASSWORD_CHANGE_ALLOWED = ("/api/v1/auth/me", "/api/v1/auth/password", "/api/v1/auth/login", "/api/v1/health")


def check_must_change_password(u: User, path: str) -> None:
    if getattr(u, "must_change_password", False) and path not in PASSWORD_CHANGE_ALLOWED:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"gate": "DOI_MAT_KHAU", "message": "Tài khoản đang dùng mật khẩu tạm – đổi mật khẩu rồi mới vào được hệ thống"})


# Chủ tịch HĐQT có toàn quyền trên mọi phân hệ (quyết định của Chủ tịch ngày 06/9/2026).
# Đặt ở ĐÚNG MỘT CHỖ này thay vì thêm "chutich" vào từng endpoint, để về sau không có endpoint nào bị bỏ sót
# và cũng không ai phải nhớ sửa hai nơi. Các chốt an toàn khác KHÔNG bị nới theo: kỳ đã khóa vẫn không ghi
# được, chứng từ đã ghi sổ vẫn bất biến (sai thì lập bút toán đảo), Ban Kiểm soát vẫn chỉ đọc, và mọi thao
# tác vẫn ghi nhật ký kiểm toán kèm tên người thực hiện nên vẫn truy được trách nhiệm.
FULL_ACCESS = ("chutich",)


def toan_quyen(u) -> bool:
    """Người này có toàn quyền CHỨC NĂNG không (Chủ tịch, quyết định 06/9/2026)?

    ĐẶT RA THÀNH HÀM VÌ MỘT LỖI THẬT, 13/9/2026. Câu trên nói FULL_ACCESS đặt ở "đúng một chỗ" để không
    endpoint nào bị sót – nhưng nó chỉ đúng với endpoint khai quyền bằng require_roles. Còn 43 chỗ trong
    kho tự viết `if u.role not in X: raise 403`, và không chỗ nào trong 43 chỗ ấy nhìn thấy FULL_ACCESS.

    Chủ tịch phát hiện ra khi mở tab Quyết toán chi tiết: màn hình báo "Vai trò của anh/chị không khai
    được hình thức". Cửa ghi thật sự VẪN MỞ cho ông – require_roles(*NHAP) cho qua nhờ FULL_ACCESS –
    nhưng cái CỜ mà màn hình đọc để vẽ nút lại tự kiểm `u.role in NHAP` bằng tay. Cửa mở, biển đề đóng.

    Một hằng số thì người ta quên nhập; một HÀM có tên thì bộ kiểm đọc được và phép thử canh được. Đó là
    toàn bộ lý do tệp này có thêm bốn dòng. Danh sách chỗ CỐ Ý không gọi hàm này – tách bạch trách
    nhiệm, không phải phân quyền – nằm ở app/services/ks_toan_quyen.py, mỗi dòng kèm lý do.
    """
    return getattr(u, "role", None) in FULL_ACCESS


# Tên tham số bật/tắt việc Chủ tịch đi qua được cả cửa TÁCH BẠCH TRÁCH NHIỆM. Để ở đây, cạnh
# FULL_ACCESS, vì hai thứ này phải đọc cùng nhau mới hiểu được.
KHOA_MO_HET_CUA = "chu_tich_mo_het_cua"


def toan_quyen_ke_ca_tach_bach(u, db) -> bool:
    """Chủ tịch đi qua được cả những cửa vốn đóng với MỌI vai trò?

    Có hai loại cửa, và trộn chúng làm một là cách hỏng âm thầm nhất:

      PHÂN QUYỀN – ai được làm việc gì. `toan_quyen()` ở trên mở hết, đúng quyết định 06/9/2026.
      TÁCH BẠCH TRÁCH NHIỆM – việc này và việc kia phải do HAI NGƯỜI làm, bất kể hai người ấy to
      đến đâu. Người ký lệnh chi và người bấm ĐÃ CHI là ví dụ kinh điển: gộp vào một người thì công
      ty mất lớp chống gian lận, và Ban Kiểm soát mất chỗ đối chiếu.

    Chủ tịch chốt 13/9/2026 MỞ CẢ LOẠI THỨ HAI để chạy thử và trình diễn hệ thống. Đặt sau một THAM
    SỐ chứ không viết cứng vào sáu chỗ, vì đây là quyết định của giai đoạn chạy thử: đến ngày vận
    hành thật, đóng lại là đổi một dòng trong bảng tham số, không phải đi sửa lại sáu tệp mã và đẩy
    một bản nâng cấp. Tham số còn có mặt tốt thứ hai: nó là một con số ĐỌC ĐƯỢC, nên robot Kiểm soát
    nêu được thành một phát hiện, và Ban Kiểm soát nhìn thấy hệ thống đang ở chế độ nào thay vì phải
    đi đọc mã nguồn.

    Rỗng/lỗi thì trả False – cửa tách bạch đóng lại. Một công tắc an toàn hỏng phải hỏng về phía
    ĐÓNG, không phải phía mở.
    """
    if not toan_quyen(u):
        return False
    try:
        from app.services.rules import get_param
        return bool(get_param(db, KHOA_MO_HET_CUA))
    except Exception:      # noqa – bảng tham số chưa có, hoặc phiên hỏng: đóng, không mở
        return False


def require_roles(*roles: str, mo_ta: str = ""):
    """Khai quyền cho MỘT endpoint, ở chữ ký hàm.

    Đây là cách duy nhất được dùng trong kho (chỉ đạo P1, 08/9/2026). Trước đó tồn tại song song một
    kiểu thứ hai – gọi AC.require(...) trong thân hàm – và hậu quả không phải lý thuyết: bộ kiểm quyền
    của robot Kiểm soát chỉ nhìn thấy kiểu thứ nhất nên lần chạy đầu trên hệ thống thật nó báo oan 26
    việc, trong đó có GET /audit vốn chặn đúng. Một robot giám sát kêu oan 26 lần ngay ngày đầu thì
    lần sau không ai đọc nó nữa.

    Khai ở chữ ký còn một cái lợi mà khai trong thân hàm không bao giờ có: máy ĐỌC ĐƯỢC danh sách vai
    trò mà không phải phân tích mã nguồn hàm, nên bộ kiểm luôn thấy đúng những gì thực sự đang chặn.

    mo_ta là tên màn hình / dữ liệu, để người bị chặn đọc được mình đang thiếu quyền gì thay vì một câu
    chung chung.
    """
    def dep(u: User = Depends(current_user)) -> User:
        if roles and u.role not in roles and not toan_quyen(u):
            ten = ROLES.get(u.role, u.role)
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Vai trò {ten} không được xem {mo_ta}" if mo_ta
                                else f"Vai trò {ten} không có quyền thực hiện thao tác này")
        return u
    dep.vai_tro_yeu_cau = tuple(roles)      # để bộ kiểm đọc được, không phải đoán từ mã nguồn
    return dep


def cong_chan_quyen(f):
    """Đánh dấu một hàm phụ thuộc là CỔNG CHẶN QUYỀN, dù nó không nhận danh sách vai trò.

    Có những cửa mà quyền phụ thuộc dữ liệu chứ không phụ thuộc vai trò – bảng lương là ví dụ: theo vai
    trò chỉ HCNS và lãnh đạo xem được, còn Kế toán trưởng xem được bằng ngoại lệ cấp riêng cho MỘT người.
    require_roles không diễn tả nổi việc đó. Nhưng cửa vẫn phải khai ở CHỮ KÝ để máy đọc được, nếu không
    bộ kiểm quyền lại phải đi phân tích mã nguồn – đúng cái đã khiến robot báo oan 26 việc ngày 07/9.
    """
    f.la_cong_chan_quyen = True
    return f


def loc_theo_nguoi_dung(mo_ta: str = ""):
    """Đánh dấu endpoint KHÔNG chặn theo vai trò mà LỌC dữ liệu theo người đăng nhập.

    Khác nhau ở chỗ nào và vì sao phải nói rõ: một endpoint chặn thì người sai vai trò nhận 403; một
    endpoint lọc thì ai gọi cũng được nhưng chỉ thấy phần của mình. Cả hai đều an toàn, nhưng nhìn từ
    ngoài chúng giống hệt "không khai quyền gì cả". Không đánh dấu thì bộ kiểm hoặc phải đọc mã nguồn,
    hoặc phải báo oan. Ví dụ: /auth/me chỉ trả về chính người gọi; khoản lương treo lọc về đúng mã
    nhân viên của người đăng nhập.
    """
    def dep(u: User = Depends(current_user)) -> User:
        return u
    dep.la_cong_chan_quyen = True
    dep.loc_theo_nguoi_dung = mo_ta or True
    return dep


def robot_auth(x_robot_token: str | None = Header(default=None)):
    if not settings.ROBOT_TOKEN or not x_robot_token or x_robot_token != settings.ROBOT_TOKEN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sai ROBOT_TOKEN")


class Gate(HTTPException):
    """Cổng chặn nghiệp vụ – trả 422 kèm mã cổng để giao diện hiển thị."""
    def __init__(self, code: str, detail: str):
        super().__init__(422, {"gate": code, "message": detail})
