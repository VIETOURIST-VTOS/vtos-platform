"""Suy pháp nhân chủ quản cho TÀI KHOẢN từ hồ sơ nhân sự (08/9/2026).

Vì sao có tệp này. Đo trên hệ thống thật sau khi P6 lên: 109 trong 110 nhân sự đang làm việc đã có
pháp nhân chủ quản, nhưng chỉ 1 trong 116 tài khoản đang hoạt động có. Nghĩa là phạm vi pháp nhân
theo phiên đăng nhập – thứ vừa xây xong – hôm nay chỉ thật sự giới hạn đúng một người, và 115 người
còn lại vẫn thấy toàn bộ dữ liệu của cả tập đoàn.

Chỗ trống ấy KHÔNG phải chỗ trống của quyết định: người quản trị đã quyết rồi, quyết ở hồ sơ nhân
sự. Nó chỉ chưa được chép sang tài khoản. Bắt ai đó ngồi gán tay 115 lần trên màn hình là cách chắc
chắn để việc này không bao giờ xong – và một hàng rào chưa bật thì bằng không có hàng rào.

BỐN ĐIỀU MODULE NÀY KHÔNG LÀM, và mỗi điều là một cách hỏng thật:

1. **Không đoán.** Chỉ suy khi tài khoản nối được với MỘT hồ sơ nhân sự và hồ sơ ấy CÓ pháp nhân.
   Không suy từ phòng ban, không suy từ vai trò, không mặc định về công ty mẹ. Tài khoản không suy
   được thì nằm nguyên trong danh sách "phải gán tay", kèm lý do vì sao không suy được.

2. **Không đè.** Tài khoản đã có pháp nhân thì không đụng tới, kể cả khi hồ sơ nói khác. Gán tay là
   quyết định của con người; suy tự động là phỏng theo dữ liệu. Cái sau không được ghi đè cái trước.
   Chỗ hai bên nói khác nhau được BÁO RA thành một mục riêng để người quản trị xem, chứ không tự xử.

3. **Không ghi khi chưa ai nhìn.** Hàm này chạy hai lượt: xem trước rồi mới ghi. Ghi 115 dòng vào
   bảng tài khoản mà không ai nhìn trước danh sách là đúng loại việc mà lúc sai thì không ai biết
   sai ở đâu.

4. **Không im lặng.** Mỗi lần ghi để lại một dòng nhật ký kèm số lượng và danh sách mã nhân viên.

Nối tài khoản với hồ sơ theo ĐÚNG thứ tự mà phần còn lại của hệ thống đang dùng (xem hr.phieu_luong):
user_id trước, mã nhân viên sau. Hai đường này lệch nhau ở vài tài khoản là chuyện có thật, nên nối
sai thứ tự là gán pháp nhân của người khác cho một người.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User, Company, ROLES
from app.models.hr import Employee
from app.services import rules as R

# QUY TẮC PHÁP NHÂN – Chủ tịch chốt ngày 09/9/2026.
#
#   "Tài xế và GĐ Huấn là pháp nhân Công ty TNHH Vận tải Vietrip, còn lại là Vietourist Holdings."
#
# Viết theo PHÒNG BAN chứ không theo vai trò, và đó là chỗ phải đọc kỹ: vai trò xe_hdv gộp CẢ tài xế
# lẫn hướng dẫn viên vào một tên. Chốt theo vai trò thì toàn bộ HDV bị kéo sang công ty vận tải – điều
# Chủ tịch không nói, và là điều sai: HDV nay là cộng tác viên của phòng Hướng dẫn, không phải người
# của đội xe. Phòng ban phân biệt được hai nhóm ấy; vai trò thì không.
#
# Mã pháp nhân chứ không phải số thứ tự: số thứ tự đổi theo từng cơ sở dữ liệu, mã thì không.
PHONG_THEO_PHAP_NHAN = {
    "doi_xe": "VTRIP-VT",      # tài xế và Giám đốc điều hành đội xe
}
PHAP_NHAN_MAC_DINH = "VTD"     # Vietourist Holdings – mọi phòng còn lại


def _theo_quy_tac(theo_ma: dict, e) -> tuple[int | None, str]:
    """Pháp nhân mà QUY TẮC nói, kèm mã. (None, mã) khi danh mục chưa có pháp nhân ấy.

    Nhận sẵn bảng tra mã → id thay vì tự truy vấn. Bản đầu gọi một câu lệnh SELECT cho MỖI nhân sự –
    110 lượt đọc danh mục pháp nhân để lấy đúng hai con số, và xem_truoc() bị gọi hai lần trong một
    lần bấm nút. Trên máy chủ 0,5 CPU thì đó đúng loại việc đã làm cổng trả 502 hôm 08/9: không sai
    kết quả, chỉ trả giá nhiều lần cho cùng một câu trả lời.
    """
    ma = PHONG_THEO_PHAP_NHAN.get(getattr(e, "department", "") or "", PHAP_NHAN_MAC_DINH)
    return theo_ma.get(ma), ma


def _ho_so_cua(db: Session) -> tuple[dict, dict]:
    """Hai bảng tra: theo user_id, và theo mã nhân viên. Chỉ lấy hồ sơ ĐANG LÀM VIỆC.

    Hồ sơ đã nghỉ vẫn giữ pháp nhân cũ; suy từ nó là gán pháp nhân theo một quan hệ đã chấm dứt.
    """
    theo_uid, theo_ma = {}, {}
    for e in db.execute(select(Employee)).scalars():
        if not e.active:
            continue
        if e.user_id:
            theo_uid[e.user_id] = e
        if e.code:
            theo_ma.setdefault(e.code, e)
    return theo_uid, theo_ma


def _noi(u: User, theo_uid: dict, theo_ma: dict):
    """Hồ sơ của một tài khoản, và cách nối được ra nó."""
    e = theo_uid.get(u.id)
    if e is not None:
        return e, "user_id"
    if u.staff_code:
        e = theo_ma.get(u.staff_code)
        if e is not None:
            return e, "ma_nhan_vien"
    return None, ""


def xem_truoc(db: Session) -> dict:
    """Suy được những gì, và không suy được cái gì vì lý do gì. KHÔNG ghi một dòng nào.

    Trả về bốn nhóm tách rời, cố ý không gộp thành một con số "tiến độ": ba nhóm sau là ba loại việc
    khác nhau, cần ba người khác nhau xử lý.
    """
    # Đọc danh mục pháp nhân MỘT lần, dùng cho cả hai chiều tra.
    cty = list(db.execute(select(Company)).scalars())
    ten_cty = {c.id: c.code for c in cty}
    ma_cty = {c.code: c.id for c in cty}
    theo_uid, theo_ma = _ho_so_cua(db)

    suy_duoc, khong_suy_duoc, da_co, lech = [], [], [], []
    for u in db.execute(select(User).order_by(User.username)).scalars():
        if not u.active:
            continue
        e, cach = _noi(u, theo_uid, theo_ma)
        dong = {"user_id": u.id, "username": u.username, "full_name": u.full_name,
                "role_name": ROLES.get(u.role, u.role), "department": u.department,
                "staff_code": u.staff_code, "ho_so": e.code if e else "", "noi_bang": cach}

        if u.company_id:
            dong["company_id"] = u.company_id
            dong["company"] = ten_cty.get(u.company_id, "")
            if e is not None and e.company_id and e.company_id != u.company_id:
                dong["ho_so_company"] = ten_cty.get(e.company_id, "")
                lech.append(dong)          # người xem quyết, module này không tự xử
            else:
                da_co.append(dong)
            continue

        if e is None:
            dong["ly_do"] = ("Tài khoản không nối được với hồ sơ nhân sự nào đang làm việc"
                             + (f" (mã {u.staff_code} không có trong danh sách)" if u.staff_code
                                else " và không có mã nhân viên"))
            khong_suy_duoc.append(dong)
            continue

        # Từ 09/9/2026 nguồn quyết định là QUY TẮC của Chủ tịch, không phải cột company_id của hồ sơ:
        # quy tắc vừa được chốt, còn cột kia là số liệu cũ nhập rải rác từ trước và chưa chắc theo kịp.
        # Hồ sơ vẫn được đọc, nhưng để ĐỐI CHIẾU – chỗ nào lệch thì nêu ra cho HCNS sửa hồ sơ, chứ
        # không im lặng lấy bên nào.
        qt_id, qt_ma = _theo_quy_tac(ma_cty, e)
        if qt_id is None:
            dong["ly_do"] = (f"Quy tắc nói pháp nhân {qt_ma} nhưng danh mục pháp nhân chưa có mã này – "
                             f"thêm vào danh mục trước")
            khong_suy_duoc.append(dong)
            continue
        dong["company_id"] = qt_id
        dong["company"] = qt_ma
        dong["phong"] = getattr(e, "department", "") or ""
        if e.company_id and e.company_id != qt_id:
            dong["ho_so_company"] = ten_cty.get(e.company_id, "")
            dong["ly_do_quy_tac"] = (f"Phòng {dong['phong'] or '(trống)'} → {qt_ma} theo quy tắc 09/9; "
                                     f"hồ sơ nhân sự đang ghi {dong['ho_so_company']}")
        suy_duoc.append(dong)

    return {
        "suy_duoc": suy_duoc,
        "khong_suy_duoc": khong_suy_duoc,
        "da_co": da_co,
        "lech_voi_ho_so": lech,
        "dem": {"suy_duoc": len(suy_duoc), "khong_suy_duoc": len(khong_suy_duoc),
                "da_co": len(da_co), "lech_voi_ho_so": len(lech)},
        "quy_tac": {"theo_phong": dict(PHONG_THEO_PHAP_NHAN), "mac_dinh": PHAP_NHAN_MAC_DINH,
                    "cau": "Phòng Đội xe (tài xế và Giám đốc điều hành đội xe) thuộc Công ty TNHH Vận "
                           "tải Vietrip; mọi phòng còn lại thuộc Vietourist Holdings. Chủ tịch chốt "
                           "09/9/2026."},
        "ghi_chu": ("Chỉ suy cho tài khoản nối được với một hồ sơ nhân sự ĐANG LÀM VIỆC – pháp nhân lấy "
                    "theo PHÒNG BAN của hồ sơ đó, theo quy tắc trên. Tài khoản đã có pháp nhân thì "
                    "không bị ghi đè; chỗ lệch được liệt kê riêng để người quản trị xem, không tự sửa. "
                    "Dòng nào có 'ly_do_quy_tac' là chỗ hồ sơ nhân sự ghi khác quy tắc – nên báo HCNS "
                    "sửa hồ sơ, vì hồ sơ mới là nơi con số ấy được dùng để chia bút toán lương."),
    }


def ap_dung(db: Session, u: User, chi_nhung_id: list[int] | None = None) -> dict:
    """Ghi pháp nhân đã suy vào tài khoản. Chạy lại nhiều lần vẫn ra cùng kết quả.

    chi_nhung_id: chỉ ghi cho những tài khoản này (khi người quản trị bỏ tick vài dòng ở bảng xem
    trước). Bỏ trống là ghi cho toàn bộ nhóm suy được.
    """
    xem = xem_truoc(db)
    can = xem["suy_duoc"]
    if chi_nhung_id is not None:
        cho_phep = set(chi_nhung_id)
        can = [d for d in can if d["user_id"] in cho_phep]
    if not can:
        return {"da_ghi": 0, "rows": [], "message": "Không có tài khoản nào suy được pháp nhân từ hồ sơ."}

    for d in can:
        t = db.get(User, d["user_id"])
        if t is None or t.company_id:      # đọc lại ngay trước khi ghi: giữa lúc xem và lúc bấm có
            continue                       # thể đã có người gán tay, và gán tay thắng
        t.company_id = d["company_id"]

    R.audit(db, u.username, u.role, "suy_phap_nhan_tai_khoan_tu_ho_so", f"user:{len(can)}",
            after={"so_tai_khoan": len(can),
                   "ma_nhan_vien": [d["ho_so"] for d in can],
                   "theo_phap_nhan": {d["company"]: sum(1 for x in can if x["company"] == d["company"])
                                      for d in can}})
    db.commit()
    return {"da_ghi": len(can), "rows": can,
            "message": f"Đã gán pháp nhân cho {len(can)} tài khoản, suy từ hồ sơ nhân sự",
            "con_lai": xem["dem"]["khong_suy_duoc"]}
