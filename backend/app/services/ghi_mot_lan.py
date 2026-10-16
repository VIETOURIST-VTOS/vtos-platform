"""V10 – hai việc: người sau biết mình đang đè lên người trước, và bấm hai lần không thành hai lô.

Lệnh Đợt 2, việc V10. Hai việc này đi cùng nhau vì cùng một gốc: quyết định "nhập là dùng luôn" bỏ
khâu duyệt từng dòng, nên mọi va chạm giữa hai người bây giờ xảy ra thẳng trên dữ liệu thật.

────────────────────────────────────────────────────────────────────────────────
VIỆC 1 – KIỂM PHIÊN BẢN
────────────────────────────────────────────────────────────────────────────────

Hai người mở cùng một bản ghi lúc 9h. Người A sửa số tiền lúc 9h05, người B sửa diễn giải lúc 9h07.
Không kiểm phiên bản thì bản lưu của B mang số tiền CŨ – sửa của A biến mất, và không ai thấy gì bất
thường: màn hình B hiện đúng cái B vừa gõ.

Cách chặn: mỗi bản ghi mang một số phiên bản, tăng sau mỗi lần sửa. Người gọi gửi kèm số phiên bản
mình đang cầm; lệch thì máy chủ TỪ CHỐI.

Và từ chối phải kèm NỘI DUNG MỚI. Câu "bản ghi đã đổi, tải lại đi" đẩy việc so sánh về phía người dùng
đúng lúc họ vừa mất công gõ xong – phần lớn sẽ tải lại rồi gõ đè lên, tức là ta chặn được cái mất dữ
liệu âm thầm và đổi lấy cái mất dữ liệu cố ý. Trả về nội dung mới thì màn hình chỉ được ra chỗ nào
khác nhau, và người quyết là người biết việc.

VÌ SAO KHÔNG DÙNG updated_at THAY CHO MỘT CỘT SỐ: hai lần ghi trong cùng một mili-giây thì dấu thời
gian bằng nhau, và ở đây chuyện đó không hiếm – lô nạp MISA ghi 25.728 bút toán cùng thời điểm. Số
đếm thì không có chỗ để hòa.

────────────────────────────────────────────────────────────────────────────────
VIỆC 2 – KHÓA CHỐNG GHI TRÙNG
────────────────────────────────────────────────────────────────────────────────

Xem chú thích ở app/models/ghi_mot_lan.py. Điều đáng nói ở đây là chỗ ĐẶT khóa: phải nhớ kết quả
TRƯỚC khi trả về, trong CÙNG một giao dịch với việc ghi. Nhớ sau khi trả về thì đúng khe hở giữa hai
bước là lúc lần gọi thứ hai đi qua – và đó chính là lúc mạng đang chập, tức là lúc hay xảy ra nhất.
"""
import hashlib
import json
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.ghi_mot_lan import KhoaGhi

# Cửa sổ suy khóa từ nội dung khi người gọi không gửi khóa riêng. Mười phút: đủ dài cho một lần mạng
# chập và người dùng bấm lại, đủ ngắn để không cản việc nạp lại thật sự vào hôm sau.
CUA_SO_SUY_KHOA = timedelta(minutes=10)

# Bảng mang cột phiên bản. VIẾT THẲNG RA từng bảng chứ không thành quy tắc "bảng nào có sửa thì thêm":
# quy tắc thì bảng thêm sau cũng mang cột này mà không ai cân nhắc bảng đó có thật sự bị hai người sửa
# cùng lúc không, và mỗi cột thừa là một lần nâng cấp cơ sở dữ liệu.
#
# Tiêu chí chọn: bản ghi mà NHIỀU NGƯỜI cùng sửa trong một kỳ, và sửa đè mất thì mất tiền hoặc mất
# dấu vết. Bảng chỉ một người sửa (tham số hệ thống, danh mục ít đổi) không có trong danh sách.
BANG_CO_PHIEN_BAN = [
    "tours",                 # điều hành và kinh doanh cùng sửa một tour
    "bookings",              # sale sửa khách, kế toán sửa số tiền
    "tour_settlements",      # quyết toán: điều hành nhập, kế toán chỉnh
    "tour_cost_lines",       # dòng giá vốn – chỗ lệch một dòng là lệch biên
    "employees",             # HCNS và kế toán cùng chạm hồ sơ lương
    "vehicles",              # đội xe và kế toán cùng chạm hồ sơ xe
    "fleet_trips",           # nhật trình chuyến – tài xế báo, điều hành sửa
    "dispatch_orders",       # lệnh điều xe
    "products",              # bảng giá dịch vụ
    "suppliers",             # số tài khoản nhà cung cấp – sửa đè là chuyển tiền nhầm chỗ
    "visa_cases",            # hồ sơ visa qua nhiều người
    "leads",                 # nguồn khách, nhiều sale cùng chạm
]
# Danh sách trên là danh sách của BẢN NÂNG CẤP V10 – đúng những bảng mà bản ấy thêm cột, và phép thử
# test_v10 canh cho nó khớp với bản nâng cấp. VPM-8 KHÔNG nới nó ra: bốn bảng của chuỗi bán hàng
# (bao_gia, bang_gia, hop_dong_khach) sinh ra đã mang cột phiên bản từ V6, không đi qua bản nâng cấp
# V10, nên thêm chúng vào đây sẽ làm hai danh sách lệch nhau vì một lý do không có thật.
# Bức tranh đầy đủ nằm ở ba bảng khai bên dưới, và test_vpm8 đọc chính chúng.


# ────────────────────────────── VPM-8: CỬA SỬA CỦA TỪNG BẢNG ──────────────────────────────
# Một cột phiên bản không tự chặn ai. Nó chỉ có tác dụng khi CỬA SỬA của bảng ấy thật sự gọi
# `kiem_phien_ban` trước khi ghi và `tang_phien_ban` sau khi ghi.
#
# Ngày 11/9/2026 đo lại: 20 bảng mang cột `phien_ban`, nhưng chỉ 2 cửa sửa gọi `kiem_phien_ban` —
# dự toán tour và báo giá. Nghĩa là mười tám bảng còn lại mang một cột KHÔNG AI ĐỌC: hai người sửa
# một hồ sơ xe, một hồ sơ nhân sự, một số tài khoản nhà cung cấp vẫn đè lên nhau lặng lẽ y như
# trước V10. Cột có mà không có cửa gọi thì tệ hơn không có cột, vì nó làm người đọc mã tin rằng
# chỗ ấy đã được canh.
#
# Bảng dưới đây KHAI cửa sửa của từng bảng, và phép thử test_vpm8_khoa_phien_ban đọc chính nó để
# hỏi một câu: bảng nào đã khai là có cột phiên bản mà cửa sửa chưa gọi khoá?
CUA_SUA_CO_KHOA = {
    "tours":            ("app/services/tours.py",    "edit"),
    "bookings":         ("app/services/bookings.py", "update_customer"),
    "products":         ("app/api/v1/products.py",   "edit_product"),
    "employees":        ("app/api/v1/hr.py",         "update_employee"),
    "vehicles":         ("app/api/v1/fleet.py",      "cap_nhat_ho_so"),
    "fleet_trips":      ("app/api/v1/fleet.py",      "sua_chuyen"),
    "suppliers":        ("app/api/v1/suppliers.py",  "sua_ncc"),
    "leads":            ("app/api/v1/crm.py",        "patch_lead"),
    "tour_cost_lines":  ("app/services/settlement.py", "update_line"),
    # Phòng HDV Đợt 1 · 06/10/2026. Hai bảng này có cửa sửa THẬT ngay từ lúc sinh ra, nên vào thẳng
    # đây chứ không qua CHUA_CO_CUA_SUA: giờ của phân công là thứ thương lượng lại được (đoàn đổi giờ
    # bay là chuyện thường), và số người của yêu cầu đổi khi đoàn tăng khách.
    "guide_assignments": ("app/api/v1/hr.py",         "assign_gio"),
    "yeu_cau_hdv":       ("app/api/v1/hr.py",         "yeu_cau_huy"),
    # Đợt 2 · báo cáo sau tour. Cửa sửa là cửa KIỂM: Trưởng phòng xác nhận hoặc trả lại, và đó là lúc
    # hai người dễ chạm nhau nhất – người nộp đang gửi bản mới trong khi người kiểm đang xác nhận bản cũ.
    "bao_cao_sau_tour":  ("app/api/v1/hr.py",         "bc_kiem"),
    # Đợt 3 · sổ tạm ứng. Cửa sửa là cửa GHI TIỀN của Kế toán – chỗ hai người dễ chạm nhau nhất:
    # phòng HDV đang xin thêm ứng trong khi Kế toán đang ghi khoản vừa chi.
    "tam_ung_hdv":       ("app/api/v1/hr.py",         "ung_ghi_tien"),
    # Đợt 4 · đề xuất của phòng HDV. Cửa sửa là cửa QUYẾT ĐỊNH: hai cấp cùng mở một hồ sơ, một người
    # bấm đồng ý trong khi người kia đang bấm trả lại.
    "de_xuat_hdv":       ("app/api/v1/hr.py",         "dx_quyet"),
    # DL-5 · 15/10/2026. Lệnh điều xe có cửa SỬA thật từ hôm nay: đổi xe và đổi tài xế. Trước đó
    # dòng này nằm ở CHUA_CO_CUA_SUA với lý do "mới có tạo và huỷ". Đây đúng là chỗ hai người dễ
    # chạm nhau nhất của phân hệ điều hành: Điều hành đang đổi xe vì xe hỏng, trong khi Giám đốc
    # đội xe đang chốt lệnh ở màn hình bên cạnh.
    # Khai `_doi` chứ không khai `dispatch_doi_xe`: cả hai cửa ghi (đổi xe, đổi tài xế) đều đi
    # qua `_doi`, và khoá nằm ở đó. Khai một trong hai cửa thì phép thử A3 đọc nhầm một hàm không
    # mang khoá, rồi hoặc báo thiếu oan, hoặc tệ hơn là xanh nhờ một lần chép tay thứ hai.
    "dispatch_orders":  ("app/api/v1/hr.py",         "_doi"),
    "bao_gia":          ("app/api/v1/ban_hang.py",   "sua_bao_gia"),
    "hop_dong_khach":   ("app/api/v1/ban_hang.py",   "dat_lich"),
    "booking_khach":    ("app/api/v1/quyet_toan_lop3.py", "sua_khach"),
}

# visa_cases KHÔNG nằm ở trên vì nó đã có khoá riêng TỪ TRƯỚC, bằng một cột tên khác: `row_version`
# (app/models/visa.py), kiểm ngay trong `edit_case` và trả 409. Cùng một ý niệm, hai cái tên — ghi ra
# đây để người sau không đi gắn thêm một khoá thứ hai lên cùng một bảng, và để biết rằng nếu muốn
# gộp về một tên thì đó là một việc dọn riêng, có nâng cấp cơ sở dữ liệu, không làm lẫn vào VPM-8.
KHOA_TEN_KHAC = {"visa_cases": ("row_version", "app/api/v1/visa.py", "edit_case")}

CHUA_CO_CUA_SUA = {
    "tour_settlements": "sửa qua nhiều đường, chưa có một cửa sửa tờ quyết toán duy nhất",
    "bang_gia": "sửa qua dòng giá, không sửa thẳng đầu bảng",
    # Lớp 3 quyết toán tour. Bốn bảng này mới có cửa THÊM và cửa ĐỌC, chưa có cửa sửa từng dòng: quy
    # trình hiện tại là xoá dòng sai rồi nhập lại, vì tờ quyết toán còn đang lập thì chưa ai cầm bản
    # in của nó. Khi nào có cửa sửa thì chuyển lên CUA_SUA_CO_KHOA – cột phien_ban đã sẵn sàng.
    "khach_chi_phi": "mới có cửa thêm và cửa đọc, chưa có cửa sửa từng dòng chi phí của khách",
    "tour_doanh_thu_dong": "mới có cửa thêm và cửa đọc, sửa bằng cách xoá dòng rồi nhập lại",
    "tour_phuong_tien": "mới có cửa thêm và cửa đọc, sửa bằng cách xoá chặng rồi nhập lại",
    "tour_hdv_chi": "mới có cửa thêm, cửa đọc và cửa duyệt; chưa có cửa sửa số đã ghi",
    # VPM-11. Sổ nghĩa vụ là LỚP ĐỌC do phép đồng bộ dựng lại từ sáu bảng chứng từ gốc; người sửa ở
    # chứng từ gốc, không sửa ở đây. Cột `phien_ban` vẫn khai sẵn vì màn hình chi tiết dòng tiền
    # (VPM-13) sẽ cần một cửa sửa TAY cho đúng hai ô: ngày dự kiến trả và trạng thái tranh chấp.
    "nghia_vu_thanh_toan": "lớp đọc dựng lại từ chứng từ gốc; cửa sửa tay cho ngày dự kiến trả và "
                           "trạng thái tranh chấp thuộc VPM-13, chưa dựng",
}


class LechPhienBan(HTTPException):
    """409 – bản ghi đã đổi kể từ lúc người này mở nó ra."""

    def __init__(self, ten: str, dang_co: int, gui_len: int, noi_dung_moi):
        # VPM-8 – ép về kiểu JSON được TRƯỚC khi dựng câu trả lời. Nội dung mới lấy thẳng từ hàm hiển
        # thị của từng phân hệ, và các hàm ấy trả về ngày tháng, Decimal, đối tượng ORM. Không ép ở
        # đây thì mỗi cửa sửa mới gắn khoá sẽ đổ 500 ĐÚNG LÚC có va chạm thật – tức là lỗi chỉ lộ ra
        # vào đúng ngày hai người sửa cùng lúc, và lộ ra thành "hệ thống sập" chứ không thành "bạn
        # đang cầm bản cũ". Chỗ ép phải nằm ở đây, một lần, chứ không phải nhắc từng người gọi nhớ.
        from fastapi.encoders import jsonable_encoder
        try:
            noi_dung_moi = jsonable_encoder(noi_dung_moi)
        except Exception:
            noi_dung_moi = {"ghi_chu": "không dựng được bản xem trước của nội dung mới – tải lại màn hình"}
        super().__init__(409, {
            "gate": "LECH_PHIEN_BAN",
            "message": f"{ten} đã được người khác sửa trong lúc bạn đang mở "
                       f"(bản trên hệ thống: {dang_co}, bản bạn cầm: {gui_len}). "
                       "Nội dung mới nằm ở 'noi_dung_moi' – đối chiếu rồi gửi lại.",
            "dang_co": dang_co, "gui_len": gui_len, "noi_dung_moi": noi_dung_moi,
        })


def kiem_phien_ban(doi_tuong, gui_len, ten: str, noi_dung_moi) -> None:
    """Gọi TRƯỚC khi gán giá trị mới. gui_len rỗng = người gọi chưa gửi phiên bản.

    Chưa gửi thì CHO QUA, có chủ ý: màn hình cũ chưa kịp sửa vẫn phải dùng được, và bắt lỗi toàn bộ
    giao diện trong một lần nâng cấp là cách chắc chắn để có một buổi sáng không ai làm việc được.
    Chỗ này là nơi sẽ siết lại khi mọi màn hình đã gửi phiên bản – ghi ra đây để người sau biết còn nợ.
    """
    if gui_len is None or gui_len == "":
        return
    dang_co = int(getattr(doi_tuong, "phien_ban", 1) or 1)
    if int(gui_len) != dang_co:
        raise LechPhienBan(ten, dang_co, int(gui_len),
                           noi_dung_moi() if callable(noi_dung_moi) else noi_dung_moi)


def tang_phien_ban(doi_tuong) -> int:
    """Gọi SAU khi gán giá trị mới, trước khi commit."""
    moi = int(getattr(doi_tuong, "phien_ban", 1) or 1) + 1
    doi_tuong.phien_ban = moi
    return moi


def suy_khoa(duong_dan: str, boi: str, than) -> str:
    """Khóa suy từ nội dung, dùng khi người gọi không gửi khóa riêng."""
    noi_dung = json.dumps(than, ensure_ascii=False, sort_keys=True, default=str)
    return "suy:" + hashlib.sha256(f"{duong_dan}|{boi}|{noi_dung}".encode("utf-8")).hexdigest()[:60]


def da_ghi_roi(db: Session, khoa: str, tu_suy: bool = False):
    """Trả kết quả lần ghi trước nếu khóa này đã dùng. None nghĩa là chưa ghi lần nào."""
    if not khoa:
        return None
    cu = db.execute(select(KhoaGhi).where(KhoaGhi.khoa == khoa)).scalars().first()
    if cu is None:
        return None
    if tu_suy and (datetime.now() - cu.luc) > CUA_SO_SUY_KHOA:
        return None                       # ngoài cửa sổ: coi như lần ghi mới, xem chú thích đầu tệp
    try:
        ra = json.loads(cu.tra_ve) if cu.tra_ve else {}
    except ValueError:
        ra = {}
    ra = dict(ra) if isinstance(ra, dict) else {"ket_qua": ra}
    ra["lap_lai"] = True
    ra["lan_dau_luc"] = cu.luc.isoformat(timespec="seconds")
    ra["message"] = ("Lô này đã nạp lúc " + cu.luc.strftime("%H:%M %d/%m/%Y")
                     + " – không nạp lại. Kết quả bên dưới là của lần nạp đó.")
    return ra


def nho_ket_qua(db: Session, khoa: str, duong_dan: str, boi: str, tra_ve: dict,
                phuong_thuc: str = "POST") -> None:
    """Ghi nhớ TRONG CÙNG giao dịch với việc ghi dữ liệu – xem chú thích đầu tệp.

    PHẢI GHI ĐÈ, KHÔNG ĐƯỢC THÊM DÒNG MỚI – cánh cửa 10 phút mở ra một bức tường.

    Đo trên bản chạy thật 16/9/2026: nạp lại 67 tệp kho cũ T1 (đã nạp buổi sáng) thì bước kiểm
    tra trả 200 bình thường, còn bước ghi trả 500 Internal Server Error. Dựng lại được:

        suy_khoa()   = băm THUẦN của (đường dẫn | người | {loại, rows, cờ bỏ dòng lỗi})
                       -> cùng tệp, cùng người, cùng cờ thì RA CÙNG MỘT KHÓA, mãi mãi
        da_ghi_roi() sau CUA_SO_SUY_KHOA (10 phút) cố ý trả None – "coi như lần ghi mới",
                       đúng như chú thích đầu tệp: "đủ ngắn để không cản việc nạp lại thật sự
                       vào hôm sau"
        nho_ket_qua() rồi THÊM lại đúng khóa ấy -> `khoa_ghi.khoa` là cột unique
                       -> IntegrityError -> 500

    Tức là chính cái trường hợp mà cửa sổ 10 phút sinh ra để cho phép — nạp lại vào hôm sau —
    lại là trường hợp làm nổ. Trong 10 phút thì không nổ, vì `da_ghi_roi` trả kết quả cũ và
    không bao giờ tới đây. Đó cũng là lý do chạy thử tại máy không thấy: hai lần nạp cách nhau
    vài giây.

    Và lỗi này KHÔNG RIÊNG kho cũ: mọi bộ nạp, hễ nạp lại đúng một nội dung sau 10 phút, đều nổ.

    Sửa: có dòng rồi thì cập nhật chính dòng ấy (kèm mốc thời gian mới) chứ không thêm dòng thứ
    hai. Giữ nguyên cả hai hành vi đang đúng — trong cửa sổ thì trả kết quả cũ, ngoài cửa sổ thì
    nạp thật.
    """
    if not khoa:
        return
    k = khoa[:80]
    tv = json.dumps(tra_ve, ensure_ascii=False, default=str)[:200000]
    cu = db.execute(select(KhoaGhi).where(KhoaGhi.khoa == k)).scalars().first()
    if cu is not None:
        cu.duong_dan = duong_dan[:200]
        cu.phuong_thuc = phuong_thuc
        cu.boi = boi[:50]
        cu.trang_thai = 200
        cu.tra_ve = tv
        cu.luc = datetime.now()          # mốc mới: cửa sổ 10 phút tính từ lần nạp NÀY
    else:
        db.add(KhoaGhi(khoa=k, duong_dan=duong_dan[:200], phuong_thuc=phuong_thuc,
                       boi=boi[:50], trang_thai=200, tra_ve=tv))
    db.flush()
