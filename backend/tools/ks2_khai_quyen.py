"""KS-2 · Đường dẫn GHI phải khai quyền ở chỗ MÁY ĐỌC ĐƯỢC.

Đo trên cây làm việc 11/9/2026: 648 đường dẫn, 340 trong đó là đường GHI (POST/PUT/PATCH/DELETE).
289 đường ghi khai quyền ở chỗ máy đọc được (require_roles gắn `vai_tro_yeu_cau` lên hàm phụ thuộc,
dù đặt ở chữ ký hay ở `dependencies=[...]` của decorator). 51 đường ghi còn lại thì KHÔNG.

51 chỗ ấy KHÔNG phải 51 lỗ hổng. Rà từng chỗ thì phần lớn có chặn thật, chỉ là chặn nằm nơi máy
không đọc được: trong thân hàm dịch vụ dưới dạng `if u.role not in (...)`, hoặc cổng "một cửa" theo
người phụ trách (`if u.id != t.operator_id`), hoặc kiểm token robot viết tay. Bảng dưới đây khai
từng chỗ một, VÀ phép thử đi kiểm lại lời khai chứ không tin lời khai.

Vì sao việc "có chặn nhưng máy không đọc được" vẫn là việc phải sửa:

  Ngày 07/9/2026 robot Kiểm soát chạy vòng quét đầu tiên và báo 26 việc nghiêm trọng. Cả 26 đều sai,
  vì có hai kiểu khai quyền song song mà bộ kiểm chỉ nhìn thấy một kiểu. Sai sót của người canh gác
  đắt hơn sai sót của người bị canh: robot kêu oan 26 lần trong ngày đầu thì lần sau không ai đọc
  nó nữa, và đúng lúc nó báo thật thì lời báo đã mất giá trị.

  Việc lần này là dạng thứ hai của đúng vấn đề ấy: bộ kiểm không kêu oan nữa, nhưng nó IM LẶNG ở 51
  chỗ. Im lặng nguy hiểm hơn kêu oan, vì không ai đếm được sự im lặng.

Một chỗ thật sự hở quyền đã tìm ra khi rà: xem bảng HO_QUYEN cuối tệp.

Ba chỗ khai hợp lệ theo lệnh KS-2 — chữ ký hàm · `dependencies=[...]` ở decorator · bảng LUONG_VIEC
của Phân quyền. Hai chỗ đầu hôm nay trùng nhau về mặt máy đọc (cả hai đều thành một hàm phụ thuộc
mang `vai_tro_yeu_cau`), nên bộ kiểm nhận cả hai như nhau. Bảng LUONG_VIEC chưa được lane Phân quyền
dựng; khi nào có thì khai tên bảng vào BANG_LUONG_VIEC ở dưới và bộ kiểm tự đọc thêm chỗ đó.
"""
from __future__ import annotations

PHUONG_THUC_GHI = ("POST", "PUT", "PATCH", "DELETE")

MIN_LY_DO = 60

# Tên bảng khai quyền của lane Phân quyền, khi nào lane ấy dựng xong thì điền vào đây (dạng
# "app.services.access:LUONG_VIEC"). Để rỗng nghĩa là chỗ khai thứ ba chưa tồn tại.
BANG_LUONG_VIEC = ""

# Hàm phụ thuộc KHÔNG mang danh sách vai trò nhưng vẫn là cửa máy đọc được.
CUA_KHONG_THEO_VAI_TRO: dict[str, str] = {
    "robot_auth": (
        "Cửa token robot: khai ở dependencies=[Depends(robot_auth)] nên máy đọc được. Người dùng "
        "không đi qua cửa này, chỉ n8n và GitHub Actions gọi bằng X-Robot-Token."),
}


# --------------------------------------------------------------------------- công khai có chủ đích

# Đường ghi KHÔNG cần đăng nhập, vì bên gọi là máy của đối tác. Mỗi dòng phải nói rõ cái gì thay cho
# đăng nhập. Giữ danh sách này ngắn: đây là mặt ngoài của hệ thống.
CONG_KHAI: dict[str, str] = {
    "POST /api/v1/auth/login": (
        "Cửa đăng nhập. Đòi đăng nhập ở đây thì không ai đăng nhập được bao giờ. Chặn bằng mật khẩu "
        "và khoá tài khoản, không bằng vai trò."),
    "POST /api/v1/sepay/webhook": (
        "SePay gọi vào, xác thực bằng header Authorization: Apikey <SEPAY_WEBHOOK_KEY>. Không có "
        "người dùng nào ở đầu kia nên không có vai trò để khai."),
    "POST /api/v1/zalo/webhook": (
        "Zalo OA gọi vào, xác thực bằng chữ ký X-ZEvent-Signature kiểm trong Z.verify_signature. "
        "Không có người dùng ở đầu kia nên không có vai trò để khai."),
    "POST /api/v1/facebook/webhook": (
        "Facebook gọi vào, xác thực bằng chữ ký X-Hub-Signature-256 kiểm trong IB.fb_verify_signature. "
        "Không có người dùng ở đầu kia nên không có vai trò để khai."),
    "POST /api/v1/tong-dai/cuoc-goi/{ma}": (
        "Tổng đài gọi vào khi có cuộc gọi tới, xác thực bằng mã đường dẫn bí mật cấp riêng cho nhà "
        "cung cấp tổng đài. Không có người dùng ở đầu kia nên không có vai trò để khai."),
}

# --------------------------------------------------------------------------- token robot viết tay

# Cùng mức bảo vệ với robot_auth nhưng viết tay trong thân hàm nên máy không đọc được. Đây là việc
# sửa NHỎ và nên sửa: đổi sang dependencies=[Depends(robot_auth)] là xong, không đụng nghiệp vụ.
TOKEN_VIET_TAY: dict[str, str] = {
    "POST /api/v1/robot/sepay/pull": "kiểm settings.ROBOT_TOKEN viết tay trong thân hàm",
    "POST /api/v1/robot/vietrip/sync": "kiểm settings.ROBOT_TOKEN viết tay trong thân hàm",
    "POST /api/v1/robot/incidents/finalize": "kiểm settings.ROBOT_TOKEN viết tay trong thân hàm",
}

# --------------------------------------------------------------------------- chặn ở tầng dịch vụ

# {đường dẫn: "tệp_dịch_vụ:tên_hàm"} — hàm ấy PHẢI có chặn vai trò hoặc cổng một cửa. Phép thử mở
# đúng hàm ấy ra đọc; khai sai hoặc ai đó gỡ chặn đi thì đỏ.
CHAN_TANG_DICH_VU: dict[str, str] = {
    "POST /api/v1/tours": "tours:create",
    "PUT /api/v1/tours/{tid}": "tours:edit",
    "POST /api/v1/tours/{tid}/submit": "tours:submit",
    "POST /api/v1/tours/{tid}/confirm": "tours:confirm",
    "POST /api/v1/tours/{tid}/approve": "tours:approve",
    "POST /api/v1/tours/{tid}/d7": "tours:d7",
    "POST /api/v1/tours/{tid}/close": "tours:close",
    "POST /api/v1/tours/{tid}/kt-confirm": "tours:kt_confirm",
    "POST /api/v1/tours/{tid}/cntt-check": "tours:cntt_check",
    "POST /api/v1/tours/{tid}/kt-return": "settlement:kt_return",
    "POST /api/v1/tours/{tid}/settlement/lines": "settlement:add_line",
    "PUT /api/v1/tours/{tid}/settlement/lines/{lid}": "settlement:update_line",
    "POST /api/v1/tours/{tid}/settlement/lines/{lid}/cancel": "settlement:cancel_line",
    "POST /api/v1/tours/{tid}/settlement/lines/{lid}/doc": "settlement:set_doc",
    "POST /api/v1/requests": "tours:create_request",
    "POST /api/v1/requests/{rid}/booking": "tours:create_booking",
    "PUT /api/v1/bookings/{bid}": "bookings:update_customer",
    "POST /api/v1/bookings/{bid}/cancel": "bookings:cancel",
    "POST /api/v1/bookings/{bid}/unlock": "bookings:unlock",
    "POST /api/v1/retentions/{rid}/apply": "bookings:apply_retention",
    "POST /api/v1/retentions/{rid}/refund": "bookings:refund_retention",
    "POST /api/v1/retentions/{rid}/cancel": "bookings:cancel_retention",
    "POST /api/v1/non-package": "nonpackage:create",
    "PUT /api/v1/non-package/{bid}": "nonpackage:update",
    "POST /api/v1/products/{pid}/open-tour": "products:open_tour",
    "POST /api/v1/payment-requests/{rid}/step": "ops:step",
}

# Dấu hiệu "có chặn" khi đọc thân hàm. Cố ý nhận cả cổng MỘT CỬA theo người phụ trách
# (`u.id != t.operator_id`) — đó là chặn thật, chặt hơn chặn theo vai trò.
DAU_HIEU_CHAN = (
    "u.role not in", "u.role in", "role not in", "AC.require", "require_roles",
    "u.id != ", "u.id not in", "_assert", "HTTPException(403", 'Gate("CONG_6"',
)

# --------------------------------------------------------------------------- chặn viết ngay tại chỗ

CHAN_TAI_CHO: dict[str, str] = {
    "POST /api/v1/tours/{tid}/settlement/match-paid": (
        "Chặn viết ngay trong thân hàm endpoint. Cùng cổng một cửa với các thao tác quyết toán khác "
        "trên chính chuyến ấy."),
    "POST /api/v1/doc-chung-tu/{bid}/xac-nhan": (
        "Chặn viết ngay trong thân hàm endpoint theo người phụ trách bộ chứng từ, không theo vai trò."),
    "POST /api/v1/incidents/{iid}/opinion": (
        "Chỉ chính người bị lập sự vụ mới được gửi ý kiến, kiểm ngay trong thân hàm. Đây là quyền "
        "theo NGƯỜI chứ không theo vai trò nên không khai được bằng require_roles."),
    "POST /api/v1/leaves": (
        "Hai đường trong một cửa: HCNS nhập hộ cho người khác, còn lại chỉ nhập cho chính mình. "
        "Nhánh rẽ nằm trong thân hàm nên máy không đọc được từ chữ ký."),
}

# --------------------------------------------------------------------------- người tự làm việc của mình

TU_PHUC_VU: dict[str, str] = {
    "POST /api/v1/auth/password": (
        "Người đổi mật khẩu của chính mình. Không có vai trò nào để khai vì mọi vai trò đều được, và "
        "phạm vi ghi đã khoá vào chính tài khoản đang đăng nhập."),
    "POST /api/v1/daily-reports": (
        "Người nộp báo cáo ngày của chính mình; phòng ban suy từ hồ sơ nhân sự của tài khoản đang "
        "đăng nhập chứ không nhận từ người gọi."),
    "POST /api/v1/daily-reports/preview": (
        "Chỉ tính thử điểm cho nội dung người dùng vừa gõ, không ghi gì vào cơ sở dữ liệu. Là POST "
        "vì nội dung dài, không phải vì nó ghi."),
    "POST /api/v1/page-shifts/{sid}/respond": (
        "Người trực trả lời ca trực của chính mình; ca trực đã gắn với tài khoản nên phạm vi ghi "
        "khoá sẵn theo người đăng nhập."),
    # TC-67 · 18/9/2026. Hai cửa chọn nền và cỡ chữ, anh Tuấn giao.
    "PUT /api/v1/auth/giao-dien": (
        "Người đặt nền và cỡ chữ cho chính mình. Không có vai trò nào để khai vì mọi vai trò đều "
        "được, và phạm vi ghi khoá vào chính tài khoản đang đăng nhập: cửa KHÔNG nhận mã người "
        "dùng, nó ghi thẳng vào bản ghi của người đang cầm phiếu đăng nhập. Không có tham số nào "
        "để trỏ sang người khác, nên hàng rào nằm ở HÌNH DẠNG của cửa chứ không ở một phép kiểm "
        "có thể bị sửa hỏng về sau. Giá trị nhận vào vẫn kiểm ở máy chủ theo hằng số GIAO_DIEN_* "
        "của models/core.py, không tin màn hình."),
    "DELETE /api/v1/auth/giao-dien": (
        "Cùng cửa với PUT ở trên, chiều ngược lại: XOÁ lựa chọn giao diện của chính mình để trở "
        "về mặc định. Xoá chứ không ghi đè bằng giá trị mặc định, vì rỗng nghĩa là CHƯA CHỌN và "
        "khác với ĐÃ CHỌN đúng giá trị mặc định. Cũng không nhận mã người dùng, nên cũng không có "
        "đường nào xoá lựa chọn của người khác."),
}

# --------------------------------------------------------------------------- HỞ THẬT

# Không phải "khai ở chỗ khác" — là KHÔNG CÓ CHẶN. Phép thử để ĐỎ cho tới khi lane chịu trách nhiệm
# đóng. Kiểm soát mở ngoại lệ, Kiểm soát KHÔNG tự đóng ngoại lệ của mình.
HO_QUYEN: dict[str, str] = {}

# Hở đã đóng — giữ lại lời khai cũ để còn truy được vì sao từng đỏ và cái gì đã đóng nó. Bảng này
# KHÔNG được bộ kiểm đọc: một chỗ chỉ rời HO_QUYEN khi chặn thật đã nằm ở chữ ký hàm, và lúc ấy
# chính bộ kiểm Q1 nhìn thấy chặn ấy chứ không cần lời khai nào.
DA_DONG: dict[str, str] = {
    "POST /api/v1/alerts/{aid}/resolve": (
        "Mở 11/9/2026 bởi KS-2: KHÔNG có chặn nào — bất kỳ tài khoản nào đăng nhập được đều đóng "
        "được BẤT KỲ cảnh báo nào, kể cả cảnh báo đỏ của phòng khác; thân hàm chỉ đặt resolved=True "
        "rồi ghi nhật ký, và bảng alerts không có cột ai-đóng nên sau khi đóng thì không truy lại "
        "được ai bấm và dựa vào đâu. "
        "ĐÓNG 11/9/2026: chữ ký hàm mang require_roles(*AC.CANH_BAO_ROLES) — 18 vai trò khai ở "
        "app/services/access.py, máy đọc được từ chữ ký nên Q1 tự nhìn thấy; KS-4 thêm dong_boi_id, "
        "dong_luc và bang_chung (bắt buộc ≥10 ký tự) nên đóng xong vẫn truy lại được ai bấm, lúc "
        "nào, dựa vào đâu."),
}

# Trần cho từng bảng. Quá trần nghĩa là cái được coi là ngoại lệ đã thành quy tắc, và quy tắc thì
# phải nói ra chứ không lớn dần trong một bảng ngoại lệ.
TRAN = {
    "CONG_KHAI": 8,
    "TOKEN_VIET_TAY": 6,
    "CHAN_TAI_CHO": 10,
    "TU_PHUC_VU": 10,
    "HO_QUYEN": 3,
}


def moi_khai() -> dict[str, str]:
    """{đường dẫn: tên bảng đã khai} — dùng để tìm chỗ khai hai lần hoặc chưa khai."""
    ra: dict[str, str] = {}
    for ten, bang in (("CONG_KHAI", CONG_KHAI), ("TOKEN_VIET_TAY", TOKEN_VIET_TAY),
                      ("CHAN_TANG_DICH_VU", CHAN_TANG_DICH_VU), ("CHAN_TAI_CHO", CHAN_TAI_CHO),
                      ("TU_PHUC_VU", TU_PHUC_VU), ("HO_QUYEN", HO_QUYEN)):
        for k in bang:
            if k in ra:
                raise AssertionError(f"{k} khai ở cả {ra[k]} và {ten} — mỗi đường dẫn một chỗ khai")
            ra[k] = ten
    return ra
