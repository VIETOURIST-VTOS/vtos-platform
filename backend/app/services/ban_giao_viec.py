# -*- coding: utf-8 -*-
"""HS-7 — BÀN GIAO VIỆC ĐANG MỞ khi một người nghỉ việc. Chủ tịch chốt 16/10/2026.

VÌ SAO CẦN. `ghi_nghi_viec` đóng hồ sơ nhân sự và đưa người ấy ra khỏi bảng lương, nhưng KHÔNG
chạm một tour, booking hay hồ sơ visa nào. Hệ quả đo được: người nghỉ rồi mà khách của họ vẫn
nằm dưới tên họ, không ai thấy trong danh sách của mình, và chỉ lộ ra khi khách gọi hỏi.

HAI THỨ KHÁC NHAU, ĐỪNG GỘP:

  · GỘP TÀI KHOẢN (`gop_tai_khoan.py`) chuyển MỌI dòng trỏ tới một tài khoản sang tài khoản khác,
    kể cả lịch sử. Nó dành cho "hai tài khoản này là MỘT người" — trùng lặp.
  · BÀN GIAO (tệp này) chuyển ĐÚNG VIỆC ĐANG MỞ sang một người KHÁC, và GIỮ NGUYÊN lịch sử dưới
    tên người cũ. Nó dành cho "người này nghỉ, ai gánh tiếp".

Dùng nhầm cái thứ nhất cho việc thứ hai là viết lại quá khứ: doanh số tháng trước của người đã
nghỉ biến thành của người nhận, và báo cáo kỳ đã chốt đổi số. Chủ tịch đã bác cách ấy.

BA LUẬT, mỗi luật vá một cách hỏng khác nhau.

  1. CHỈ VIỆC ĐANG MỞ. Mỗi bảng có một điều kiện "còn mở" riêng, khai thẳng ở `CHUYEN` dưới đây.
     Tour đã kết thúc, booking đã huỷ, lead đã chốt — ở lại với tên người cũ.

  2. MỌI CỘT TRỎ TỚI `users.id` PHẢI ĐƯỢC PHÂN LOẠI. 28 cặp (bảng, cột), mỗi cặp nằm đúng một
     trong ba nhóm: `CHUYEN` · `GIU` · `KHONG_PHAI_VIEC`. Thêm một bảng mới mà quên phân loại thì
     `test_hs7_1` đỏ. Không có hàng rào ấy thì bảng mới lặng lẽ KHÔNG được bàn giao, và chỗ sót
     chỉ lộ ra khi có người đi tìm việc của người đã nghỉ.

  3. PHÂN CÔNG KINH DOANH ĐÓNG CHẶNG CŨ, MỞ CHẶNG MỚI — không sửa tên trên dòng cũ. Bảng
     `phan_cong_kd` có `tu_ngay`/`den_ngay`, và báo cáo kỳ cũ đọc đúng hai cột ấy. Sửa thẳng tên
     thì doanh số của THÁNG TRƯỚC cũng đổi chủ. Đóng–mở thì kỳ đã chốt giữ nguyên số và kỳ sau
     tính cho người nhận, tự đúng mà không cần một luật riêng.

LEAD ĐI QUA CỬA ĐÃ CÓ. `chuyen_doi_lead.ban_giao` ghi vào `lead_ban_giao` — lịch sử giao–nhận của
một lead. Viết một đường gán `sales_id` thứ hai ở đây là lịch sử lead nằm hai chỗ và không chỗ nào
đủ, đúng điều tệp ấy đã cảnh báo.

XEM TRƯỚC LÀ BẮT BUỘC, và nó phải kê cả phần Ở LẠI. Một bản xem trước chỉ liệt kê thứ sắp chuyển
sẽ khiến người bấm tin rằng mọi thứ khác không tồn tại.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import Booking, ServiceRequest, Tour, User
from app.models.crm import Conversation, Lead
from app.models.cskh import CareTicket
from app.models.ban_hang import BaoGia
from app.models.to_chuc_kd import PhanCongKD
from app.models.visa import VisaCase, VisaTask
from app.models.ops import DailyReportFollowUp
from app.models.cham_soc_khach import HoTroKhach
from app.services import rules as R

# Tour đã qua những trạng thái này thì mọi thứ treo dưới nó là LỊCH SỬ, không bàn giao.
TOUR_DA_DONG = ("ket_thuc", "da_dong_so", "kt_xac_nhan", "khoa", "huy")


def _tour_con_mo(q, cot_tour_id):
    """Booking / yêu cầu dịch vụ chỉ còn mở khi TOUR của nó còn mở."""
    return q.join(Tour, Tour.id == cot_tour_id).where(Tour.status.notin_(TOUR_DA_DONG))


# ---------------------------------------------------------------------------------------------
# NHÓM 1 — CHUYỂN. Mỗi dòng: (bảng, cột, tên tiếng Việt, hàm lọc "còn mở").
# ---------------------------------------------------------------------------------------------
CHUYEN = [
    ("tours", "operator_id", "Tour đang điều hành",
     lambda q: q.where(Tour.status.notin_(TOUR_DA_DONG))),
    ("tours", "chu_ho_so_id", "Tour đang giữ hồ sơ",
     lambda q: q.where(Tour.status.notin_(TOUR_DA_DONG))),
    ("bookings", "sales_id", "Booking chưa đóng",
     lambda q: _tour_con_mo(q.where(Booking.cancelled == False), Booking.tour_id)),
    ("visa_cases", "visa_owner_user_id", "Hồ sơ visa đang xử lý",
     lambda q: q.where(VisaCase.lifecycle_status.in_(("DRAFT", "ACTIVE", "ON_HOLD")))),
    ("visa_cases", "sales_user_id", "Hồ sơ visa — người bán",
     lambda q: q.where(VisaCase.lifecycle_status.in_(("DRAFT", "ACTIVE", "ON_HOLD")))),
    ("visa_cases", "supervisor_user_id", "Hồ sơ visa — người giám sát",
     lambda q: q.where(VisaCase.lifecycle_status.in_(("DRAFT", "ACTIVE", "ON_HOLD")))),
    ("visa_tasks", "assignee_user_id", "Việc visa chưa xong",
     lambda q: q.where(VisaTask.status.notin_(("done", "cancelled")))),
    ("leads", "sales_id", "Khách tiềm năng chưa chốt",
     lambda q: q.where(Lead.status.in_(("moi", "dang_cham_soc")))),
    ("bao_gia", "sales_id", "Báo giá còn hiệu lực",
     lambda q: q.where(BaoGia.trang_thai.in_(("nhap", "cho_duyet_bien", "da_gui")))),
    ("care_tickets", "owner_id", "Phiếu chăm sóc chưa đóng",
     lambda q: q.where(CareTicket.status.in_(("moi", "hen_lai")))),
    ("conversations", "sales_id", "Hội thoại khách chưa đóng",
     lambda q: q.where(Conversation.status != "dong")),
    ("service_requests", "sales_id", "Yêu cầu dịch vụ chưa thành booking",
     lambda q: q.where(ServiceRequest.booking_id.is_(None))),
    # SUA-5 (02/11/2026): hai loại việc mới sinh sau HS-7, đều là việc GIAO CHO MỘT NGƯỜI và còn mở thì
    # người kế nhiệm phải nhận — để lại thì việc treo dưới tên người đã nghỉ, không ai thấy.
    ("daily_report_follow_ups", "nguoi_nhan_id", "Việc hỗ trợ từ báo cáo ngày chưa xong",
     lambda q: q.where(DailyReportFollowUp.trang_thai.notin_(("da_xong", "rut")))),
    ("ho_tro_khach", "giao_cho_id", "Yêu cầu hỗ trợ của khách chưa trả lời",
     lambda q: q.where(HoTroKhach.trang_thai.notin_(("da_tra_loi", "dong")))),
    # Đóng chặng cũ, mở chặng mới — xử riêng trong `_chuyen_phan_cong`, không gán thẳng.
    ("phan_cong_kd", "user_id", "Phân công kinh doanh đang hiệu lực", None),
]

MO_HINH = {"tours": Tour, "bookings": Booking, "visa_cases": VisaCase, "visa_tasks": VisaTask,
           "leads": Lead, "bao_gia": BaoGia, "care_tickets": CareTicket,
           "conversations": Conversation, "service_requests": ServiceRequest,
           "phan_cong_kd": PhanCongKD, "daily_report_follow_ups": DailyReportFollowUp,
           "ho_tro_khach": HoTroKhach}

# ---------------------------------------------------------------------------------------------
# NHÓM 2 — GIỮ NGUYÊN TÊN NGƯỜI CŨ. Lịch sử đã phát sinh là thứ không bàn giao được.
# ---------------------------------------------------------------------------------------------
GIU = {
    ("bookings", "created_by"): "ai TẠO booking là một sự kiện đã xảy ra, không đổi chủ được",
    ("alerts", "dong_boi_id"): "ai đóng cảnh báo — sự kiện đã xảy ra",
    ("alerts", "nguoi_nhan_id"): "cảnh báo đã gửi cho ai — sự kiện đã xảy ra",
    ("alerts", "nguoi_phu_trach"): "cảnh báo tự sinh lại theo vai mỗi lượt robot; chuyển tay ở đây "
                                   "là đẻ ra hai nguồn giao việc cho cùng một cảnh báo",
    ("daily_reports", "user_id"): "báo cáo ngày là lời của chính người ấy",
    ("tour_settlements", "operator_id"): "quyết toán đã lập — chứng từ mang tên người lập",
    ("chi_tieu_kd", "user_id"): "chỉ tiêu giao cho MỘT người; chuyển sang người ở lại là làm hỏng "
                                "đánh giá của cả hai (Chủ tịch chốt 16/10)",
    ("kho_cu_nguoi_ban", "user_id"): "số liệu lịch sử của người bán",
    ("canh_bao_gui", "user_id"): "đã gửi cho ai — sự kiện đã xảy ra",
    ("campaigns", "owner_id"): "chiến dịch marketing có ngân sách và kỳ riêng; đổi chủ là việc của "
                               "Marketing quyết, không phải hệ quả của một lần nghỉ việc",
    ("products", "operator_id"): "điều hành mặc định của một mã sản phẩm — thuộc danh mục, không "
                                 "phải việc đang gánh của một người",
}

# ---------------------------------------------------------------------------------------------
# NHÓM 3 — KHÔNG PHẢI VIỆC. Những cột này nói "tài khoản này LÀ ai", không nói "đang gánh gì".
# ---------------------------------------------------------------------------------------------
KHONG_PHAI_VIEC = {
    ("employees", "user_id"): "khoá nối hồ sơ nhân sự với tài khoản",
    ("user_grants", "user_id"): "ngoại lệ quyền — thu hồi ở màn Tài khoản, không bàn giao",
    ("zalo_ma_noi", "user_id"): "định danh Zalo nội bộ của chính người ấy",
    ("zalo_noi_tai_khoan", "user_id"): "định danh Zalo nội bộ của chính người ấy",
}


def _kiem(db: Session, tu_id: int, den_id: int) -> tuple[User, User]:
    if tu_id == den_id:
        raise ValueError("Người giao và người nhận phải khác nhau.")
    tu, den = db.get(User, tu_id), db.get(User, den_id)
    if tu is None:
        raise ValueError("Không có tài khoản người giao.")
    if den is None:
        raise ValueError("Không có tài khoản người nhận.")
    if not den.active:
        raise ValueError(
            f"Tài khoản người nhận ({den.username}) đang bị khoá. Bàn giao vào một tài khoản "
            "không ai mở được là giấu việc đi chứ không phải giao việc.")
    return tu, den


def _dem(db: Session, tu_id: int) -> list[dict]:
    """Đếm việc đang mở của một người, theo từng loại. KHÔNG ghi gì."""
    ra = []
    for bang, cot, ten, loc in CHUYEN:
        M = MO_HINH[bang]
        q = select(M).where(getattr(M, cot) == tu_id)
        if bang == "phan_cong_kd":
            q = q.where(PhanCongKD.den_ngay.is_(None))
        elif loc is not None:
            q = loc(q)
        so = len(db.execute(q).scalars().all())
        if so:
            ra.append({"bang": bang, "cot": cot, "ten": ten, "so_dong": so})
    return ra


def _o_lai(db: Session, tu_id: int) -> list[dict]:
    """Những gì Ở LẠI dưới tên người cũ, kèm LÝ DO. Bản xem trước chỉ kê phần chuyển đi sẽ khiến
    người bấm tin rằng mọi thứ khác không tồn tại."""
    ra = []
    for (bang, cot), vi_sao in sorted({**GIU}.items()):
        t = Base.metadata.tables.get(bang)
        if t is None:
            continue
        so = db.execute(select(t).where(t.c[cot] == tu_id)).fetchall()
        if so:
            ra.append({"bang": bang, "cot": cot, "so_dong": len(so), "vi_sao": vi_sao})
    return ra


def xem_truoc(db: Session, tu_id: int, den_id: int) -> dict:
    tu, den = _kiem(db, tu_id, den_id)
    chuyen = _dem(db, tu_id)
    return {
        "tu": {"id": tu.id, "tai_khoan": tu.username, "ho_ten": tu.full_name},
        "den": {"id": den.id, "tai_khoan": den.username, "ho_ten": den.full_name},
        "se_chuyen": chuyen,
        "tong_chuyen": sum(x["so_dong"] for x in chuyen),
        "o_lai": _o_lai(db, tu_id),
        "ghi_chu": ("Chỉ VIỆC ĐANG MỞ đổi người. Lịch sử đã phát sinh — booking đã huỷ, tour đã "
                    "kết thúc, báo cáo, quyết toán, chỉ tiêu — giữ nguyên tên người cũ. Báo cáo "
                    "kỳ ĐÃ CHỐT không đổi số; kỳ sau tính cho người nhận."),
    }


def _chuyen_phan_cong(db: Session, boi: User, tu: User, den: User, ly_do: str, hom_nay: date) -> int:
    """Đóng chặng cũ hôm nay, mở chặng mới từ ngày mai.

    KHÔNG sửa tên trên dòng cũ: báo cáo kỳ cũ đọc `tu_ngay`/`den_ngay`, nên sửa thẳng là doanh số
    tháng trước cũng đổi chủ.
    """
    dong = db.execute(select(PhanCongKD).where(PhanCongKD.user_id == tu.id,
                                               PhanCongKD.den_ngay.is_(None))).scalars().all()
    for pc in dong:
        pc.den_ngay = hom_nay
        db.add(PhanCongKD(user_id=den.id, don_vi_id=pc.don_vi_id, vai=pc.vai,
                          tu_ngay=hom_nay + timedelta(days=1), den_ngay=None,
                          ly_do=f"Nhận bàn giao từ {tu.username}: {ly_do}"[:500],
                          boi=boi.username))
    return len(dong)


def ban_giao(db: Session, boi: User, tu_id: int, den_id: int, ly_do: str,
             xac_nhan: bool = False) -> dict:
    """Chuyển việc đang mở sang người nhận. `xac_nhan=False` chỉ trả bản xem trước và KHÔNG ghi."""
    if not (ly_do or "").strip():
        raise ValueError("Bàn giao phải ghi lý do — người nhận cần biết vì sao việc đến tay mình, "
                         "và cuối kỳ còn tra lại được ai đã quyết.")
    tu, den = _kiem(db, tu_id, den_id)
    kq = xem_truoc(db, tu_id, den_id)
    if not xac_nhan:
        return {**kq, "da_chuyen": False,
                "ghi_chu_them": "Đây là bản xem trước. Bấm xác nhận thì việc mới đổi người."}

    hom_nay = date.today()
    da = []
    for bang, cot, ten, loc in CHUYEN:
        M = MO_HINH[bang]
        if bang == "phan_cong_kd":
            n = _chuyen_phan_cong(db, boi, tu, den, ly_do, hom_nay)
            if n:
                da.append({"bang": bang, "cot": cot, "ten": ten, "so_dong": n,
                           "cach": "đóng chặng cũ, mở chặng mới"})
            continue
        q = select(M).where(getattr(M, cot) == tu_id)
        if loc is not None:
            q = loc(q)
        dong = db.execute(q).scalars().all()
        if not dong:
            continue
        if bang == "leads":
            # Đi qua cửa đã có để lịch sử lead chỉ nằm MỘT chỗ.
            from app.services import chuyen_doi_lead as CDL
            for l in dong:
                CDL.ban_giao(db, boi, l.id, den_nguoi_id=den_id,
                             ly_do=f"Bàn giao khi {tu.username} nghỉ việc: {ly_do}"[:200])
        else:
            for r in dong:
                setattr(r, cot, den_id)
        da.append({"bang": bang, "cot": cot, "ten": ten, "so_dong": len(dong), "cach": "đổi người"})

    R.audit(db, boi.username, boi.role, "ban_giao_viec", f"user:{tu.username}",
            before={"nguoi_giao": tu.username},
            after={"nguoi_nhan": den.username, "ly_do": ly_do.strip()[:300],
                   "da_chuyen": da, "ngay": hom_nay.isoformat()})
    db.flush()
    return {**xem_truoc(db, tu_id, den_id), "da_chuyen": True, "chi_tiet": da,
            "message": f"Đã bàn giao {sum(x['so_dong'] for x in da)} việc đang mở từ "
                       f"{tu.full_name} sang {den.full_name}."}
