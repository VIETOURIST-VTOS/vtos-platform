# -*- coding: utf-8 -*-
"""VAI KẾ THỪA — một phép suy có tên, và chỗ duy nhất khai nó.

VÌ SAO TỆP NÀY TỒN TẠI. Đợt E2b (10/10/2026) thêm ba vai kế toán mới và suy bảng MÀN HÌNH từ vai
`ketoan` bằng một vòng lặp viết tại chỗ trong `access.py`:

    if "ketoan" in v and "ketoan_truong" not in v: v = v + ("ketoan_truong",)

Phép suy ấy đúng về ý và sai về phạm vi: nó chỉ suy MỘT BÊN. Bảng CỬA — thứ quyết định bấm vào có
chạy không — không biết gì về vai mới. Đo trên main ngày 11/10: **29 cặp (màn hình, vai) mở được
menu mà bấm vào là 403**, và chỉ 4 cặp có hàng rào bắt được. Đúng hình "cửa mở, biển đề đóng" đã
ghi hai lần trong sổ (13/9 và 10/10) — lần này do chính người viết về nó gây ra.

Nên chỗ sửa không phải là bỏ phép suy, mà là ĐẶT NÓ MỘT CHỖ và bắt mọi nơi cùng đọc. Ba nơi:

  · `services/access.py`            dựng bảng MÀN HÌNH
  · `api/deps.py::require_roles`    mở CỬA, và ghi tập ĐÃ NỚI vào `vai_tro_yeu_cau`
  · `tests/test_lg1_...py`          SO hai bảng cho mọi màn hình × mọi vai

Hai bảng suy từ cùng một luật thì không lệch nhau được. Đó là toàn bộ lý do tệp này có mặt.
"""

# ══════════════════════════════════════════════════════════════════════════════════════════════
# BẢNG KẾ THỪA — vai con thấy mọi thứ vai cha thấy
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# CHỈ CÓ MỘT DÒNG, và đừng thêm dòng thứ hai mà không có người ký. Kế thừa quyền là thứ nhìn thì
# gọn mà hệ quả thì rộng: một dòng ở đây mở THÊM 514 cửa — Kế toán trưởng từ 13 cửa lên 527,
# tức thấy hết những gì `ketoan` thấy (đo 11/10/2026 trên cả cây trước và cây sau bản vá).
#
# `ketoan_tt` và `thu_quy` CỐ Ý KHÔNG kế thừa — chúng là vai HẸP, khai đúng màn hình của mình ở
# `access.MAN_HINH_KETOAN_TT` / `MAN_HINH_THU_QUY`. Kế toán thanh toán xử chuyển khoản, Thủ quỹ xử
# tiền mặt; cho chúng thấy hết những gì Kế toán thấy là xoá mất chính việc tách vai của Đợt E2b.
VAI_KE_THUA = {
    "ketoan_truong": "ketoan",
}


def vai_va_cha(vai: str) -> tuple[str, ...]:
    """`("ketoan_truong", "ketoan")` — vai ấy cộng chuỗi vai cha của nó.

    Dùng ở nơi ĐỌC: những hàm hỏi "vai này có trong danh sách kia không". Trả về cả vai con để
    một quyền cấp RIÊNG cho vai con vẫn còn tác dụng — kế thừa là CỘNG THÊM, không phải thay thế.
    """
    ra, v = [vai], vai
    while v in VAI_KE_THUA:
        v = VAI_KE_THUA[v]
        if v in ra:          # vòng tròn trong bảng khai: dừng, đừng quay mãi
            break
        ra.append(v)
    return tuple(ra)


def mo_rong(vai_tro) -> tuple[str, ...]:
    """Thêm vai CON vào một danh sách đã có vai CHA. Giữ nguyên thứ tự, không trùng.

    Dùng ở nơi KHAI: bảng màn hình và `require_roles`. Danh sách RỖNG trả về rỗng — `require_roles()`
    không tham số nghĩa là "mọi người đã đăng nhập", và nới một danh sách rỗng là biến nó thành
    một danh sách có hạn, tức SIẾT chứ không nới.
    """
    v = tuple(vai_tro)
    if not v:
        return v
    ra = list(v)
    for con, cha in VAI_KE_THUA.items():
        if cha in ra and con not in ra:
            ra.append(con)
    return tuple(ra)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MƯỜI TÁM CỬA LƯƠNG VÀ NHÂN SỰ — Chủ tịch chốt 11/10/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Một dòng `VAI_KE_THUA` ở trên mở THÊM 514 cửa cho Kế toán trưởng (13 → 527). 18 trong số
# đó chạm DỮ LIỆU CÁ NHÂN
# — bảng lương, hồ sơ nhân sự, BHXH, giảm trừ gia cảnh — và một trong 18 là `POST /payroll-runs/
# {ky}/chi`, tức NÚT CHI LƯƠNG THẬT, không phải xem.
#
# Chủ tịch được nêu rõ cả con số 514 lẫn cái nút chi lương, và chốt nới hết.
#
# ĐIỀU ĐÃ NÊU VÀ GIỮ NGUYÊN Ý, ghi ở đây để Pháp chế đọc được: bảng lương là dữ liệu cá nhân theo
# Luật 91/2025 và Nghị định 356/2025 — chính kho mã đã khóa không cho MÁY đọc bảng lương vì lẽ ấy
# (`models/doc_chung_tu.py::CAM_DOC_BANG_MAY`). Và trước quyết định này, Kế toán trưởng xem được
# lương bằng một NGOẠI LỆ CẤP RIÊNG CHO MỘT NGƯỜI, không bằng vai trò (xem `deps.cong_chan_quyen`).
# Quyết định 11/10 đảo lại chốt ấy.
#
# VÌ SAO KHAI THÀNH DANH SÁCH THAY VÌ ĐỂ PHÉP SUY TỰ LO: một quyền mở ra do hệ quả của một dòng
# suy là một quyền không ai rà được. Khai ra thì Pháp chế đọc được đúng danh sách ấy, từng dòng
# một, và thêm một cửa lương mới mà không khai là phép thử ĐỎ — phải có người ký lại chứ không lọt vào im
# lặng. Đảo lại quyết định: xoá `"ketoan_truong"` khỏi `VAI_KE_THUA`, đúng một dòng.
#
# CON SỐ NÀY TỪNG LÀ 17, VÀ HÀNG RÀO SỬA NÓ. Lượt quét đầu của em dùng một mẫu tìm hẹp hơn và bỏ
# sót `GET /api/v1/cap-phat` — sổ cấp phát tài sản cho nhân viên. `test_lg5` đỏ ngay lần chạy đầu
# và chỉ đúng cửa bị thiếu. Ghi lại vì nó chứng minh điều danh sách này sinh ra để làm: một con số
# đếm tay thì sai được, một con số có hàng rào đếm thì không sai lâu.
CAN_CU_CUA_LUONG = "Chủ tịch chốt 11/10/2026 – nới hết quyền Kế toán trưởng, kể cả cửa lương"

CUA_LUONG_DA_KY = (
    ("GET", "/api/v1/payroll"),
    ("GET", "/api/v1/employees"),
    ("GET", "/api/v1/employees/{eid}/profile"),
    ("GET", "/api/v1/employees/{eid}/pit-deduction"),
    ("PUT", "/api/v1/employees/{eid}/company"),
    ("GET", "/api/v1/payroll-runs/{period}/lech-cong"),
    ("GET", "/api/v1/payroll-runs/{period}/tncn-con-thieu"),
    ("POST", "/api/v1/payroll-runs/{period}/chi"),
    ("PUT", "/api/v1/payroll-runs/{period}/chi/{lan}"),
    ("POST", "/api/v1/payroll-runs/{period}/chi/{lan}/doi-chieu"),
    ("POST", "/api/v1/payroll-runs/{period}/chi/{lan}/phu-luc"),
    ("POST", "/api/v1/payroll-runs/{period}/chi/{lan}/unc"),
    ("POST", "/api/v1/bhxh/nap"),
    ("GET", "/api/v1/hrm/profile-gaps"),
    ("GET", "/api/v1/cap-phat"),
    ("GET", "/api/v1/cap-phat/dang-giu/{employee_id}"),
    ("GET", "/api/v1/doc-chung-tu/chat-luong"),
    ("GET", "/api/v1/he-thong/dung-luong"),
    # Lan doi xe mo 16/10/2026 (PR #370): doi chieu BHXH phan cong ty dong cua doi xe.
    # `test_lg5` do ngay va chi dung ten cua nay — dung viec danh sach sinh ra de lam.
    # Anh Tuan quyet 16/10/2026: khai ra, theo dung chot 11/10 cua Chu tich.
    ("GET", "/api/v1/fleet/bhxh-doi-xe"),
)
