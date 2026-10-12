# -*- coding: utf-8 -*-
"""BD-1 · BÀN LÀM VIỆC CỦA MỘT PHÒNG — gom hàng đợi việc, không đẻ ra con số mới.

    "em trien khai viet code cau truc va giao dien ban lam viec cho dieu hanh tour"
                                                        — Chủ tịch, 12/10/2026

═══════════════════════════════════════════════════════════════════════════════════════════════
MÀN HÌNH NÀY TRẢ LỜI CÂU GÌ, VÀ VÌ SAO BẢNG CHỈ TIÊU KHÔNG TRẢ LỜI ĐƯỢC
═══════════════════════════════════════════════════════════════════════════════════════════════
Từ 11/10/2026 (PH-1) `/phan-he/<khoa>` mở ra bảng chỉ tiêu của phòng. Bảng ấy trả lời **"kỳ này
phòng đang ở đâu"**: nó đếm theo kỳ, so với kỳ trước, và mỗi dòng có cách tính.

Nó KHÔNG trả lời được **"sáng nay tôi phải làm gì, hồ sơ nào trước"**. Hai câu khác nhau ở chỗ
đơn vị: chỉ tiêu là một CON SỐ của một KỲ, còn việc cần làm là một DANH SÁCH HỒ SƠ có tên, có hạn,
và có chỗ bấm vào. Đo ngày 12/10/2026: năm hàng đợi của Phòng Điều hành đều đã có dữ liệu và đều
có màn hình riêng — nhưng không có chỗ nào gom lại, nên trưởng phòng phải tự nhớ mà đi vào từng
màn hình một. Việc còn thiếu là MỘT CHỖ GOM, không phải một bảng số mới.

═══════════════════════════════════════════════════════════════════════════════════════════════
RANH GIỚI 09/9/2026 — TỆP NÀY KHÔNG TÍNH MỘT CON SỐ NÀO CỦA RIÊNG NÓ
═══════════════════════════════════════════════════════════════════════════════════════════════
Mỗi hàng đợi đọc ĐÚNG phép lọc mà màn hình nguồn và cảnh báo đang dùng, và mỗi ô đều mang theo
tên nguồn (`nguon`) để người đọc dò ngược được. Chỗ nào tệp này tự nghĩ ra một phép lọc mới là
chỗ ấy sẽ lệch với màn hình nguồn, và lúc hai con số khác nhau thì người dùng tin con số dễ đọc
hơn chứ không tin con số đúng.

Hệ quả cố ý: bàn này KHÔNG có nút duyệt, nút xác nhận, nút đóng sổ. Mọi ô chỉ dẫn SANG màn hình
nguồn, nơi quyền và quy trình đã có chủ. Duyệt hàng loạt từ một bảng tổng là thứ khó lùi nhất.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA ĐIỀU ÉP TRONG CẤU TRÚC
═══════════════════════════════════════════════════════════════════════════════════════════════
(a) **SỐ 0 KHÔNG ĐƯỢC LẪN VỚI LỖI.** Mỗi ô mang `trang_thai`: `san_sang` (đã đọc được nguồn),
    `thieu_nguon` (phòng này chưa khai hàng đợi ấy), `loi` (đọc hỏng). Một ô đọc hỏng mà hiện
    "0 việc" là nói với trưởng phòng rằng hôm nay không có gì phải làm — lời nói dối tệ nhất mà
    một bàn làm việc có thể nói.

(b) **MỘT Ô HỎNG KHÔNG ĐƯỢC KÉO SẬP CẢ BÀN.** Mỗi hàng đợi bọc `try` riêng. Bàn mất một ô vẫn còn
    bốn ô dùng được; bàn trắng trơn thì trưởng phòng quay về cách cũ và không bao giờ mở lại.

(c) **TỔNG CHỈ HIỆN KHI CẢ NĂM Ô SẴN SÀNG.** `tong_dang_cho` để `None` nếu có ô nào chưa đọc
    được. Cộng bốn ô rồi gọi là "tổng việc đang chờ" là một con số thiếu mà trông như đủ.

KHÔNG CỘNG CHỈ TIÊU VÀO HÀNG ĐỢI: bảng chỉ tiêu và bàn làm việc là hai nguồn riêng, đếm hai thứ
khác nhau trên hai khoảng thời gian khác nhau. Ba việc phải xử lý của bảng chỉ tiêu KHÔNG phải ba
hồ sơ trong hàng đợi.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

# Số dòng hồ sơ bày sẵn trong mỗi ô. Chủ tịch chốt BA ngày 12/10/2026 sau khi xem bản dựng thử:
# ba dòng thì cả năm ô nằm gọn một màn hình, không phải cuộn. Muốn xem hết thì bấm sang màn hình
# nguồn — chỗ duy nhất có đủ bộ lọc và đủ quyền.
SO_DONG_MAU = 3

SAN_SANG = "san_sang"
THIEU_NGUON = "thieu_nguon"
LOI = "loi"


def _o(khoa: str, ten: str, so_luong, don_vi: str, den: str, nguon: str,
       muc: str = "", nhan_muc: str = "", ghi_chu: str = "", dong: list | None = None,
       trang_thai: str = SAN_SANG, ly_do: str = "") -> dict:
    """Một ô hàng đợi. `so_luong = None` nghĩa là CHƯA ĐỌC ĐƯỢC, không phải bằng 0."""
    return {"khoa": khoa, "ten": ten, "so_luong": so_luong, "don_vi": don_vi,
            "muc": muc, "nhan_muc": nhan_muc, "ghi_chu": ghi_chu, "den": den,
            "nguon": nguon, "dong": dong or [], "trang_thai": trang_thai, "ly_do": ly_do}


def _dong(chinh: str, phu: str = "", phai: str = "", phai_phu: str = "", kieu: str = "") -> dict:
    """Một dòng hồ sơ mẫu. `kieu` chỉ đổi MÀU chữ bên phải, không mang thêm nghĩa nào khác:
    "do" = đã quá hạn, "vang" = sắp đến hạn, rỗng = một con số bình thường."""
    return {"chinh": chinh, "phu": phu, "phai": phai, "phai_phu": phai_phu, "kieu": kieu}


def _trieu(x: float) -> str:
    """Số tiền rút về đơn vị triệu để dòng mẫu đọc được trong một ô hẹp.

    CHỈ ĐỂ HIỂN THỊ. Số gốc không đi kèm, và không chỗ nào được tính nghiệp vụ từ chuỗi này —
    đúng điều tài liệu bàn giao IT ngày 12/10 đã ghi ra.
    """
    return f"{x / 1_000_000:,.1f}".replace(",", " ").replace(".", ",")


# ══════════════════════════════ NĂM HÀNG ĐỢI CỦA PHÒNG ĐIỀU HÀNH ══════════════════════════════

def _yeu_cau_cho_booking(db: Session) -> dict:
    """Yêu cầu Kinh doanh đã gửi mà Điều hành chưa tạo booking.

    ĐỌC ĐÚNG PHÉP LỌC CỦA CHỈ TIÊU `yeu_cau_cho` (bao_cao_phong) và của cảnh báo `sla_booking`
    (rules.robot_quet): `service_requests.booking_id` rỗng. Hạn tính bằng ĐỒNG HỒ THẬT kể từ
    `created_at`, y như cảnh báo — tham số tên là "phút làm việc" nhưng chỗ bắn cảnh báo đang đo
    giờ thật, và hai chỗ đo hai kiểu thì một hồ sơ sẽ quá hạn ở ô này mà chưa quá hạn ở ô kia.
    """
    from app.models.core import ServiceRequest
    from app.services import rules as R

    rows = list(db.execute(select(ServiceRequest).where(ServiceRequest.booking_id == None)  # noqa: E711
                           .order_by(ServiceRequest.created_at)).scalars())
    sla = float(R.get_param(db, "sla_booking_phut"))
    bay_gio = datetime.now()
    dong, qua = [], 0
    for r in rows:
        phut = (bay_gio - r.created_at).total_seconds() / 60 if r.created_at else 0
        if phut > sla:
            qua += 1
            tre = phut - sla
            phai, kieu = (f"Quá {int(tre // 60)} giờ {int(tre % 60):02d}" if tre >= 60
                          else f"Quá {int(tre)} phút"), "do"
            phai_phu = "Hạn tạo booking"
        else:
            con = sla - phut
            phai = f"Còn {int(con // 60)} giờ {int(con % 60):02d}" if con >= 60 else f"Còn {int(con)} phút"
            kieu, phai_phu = "vang", "Sắp đến hạn"
        if len(dong) < SO_DONG_MAU:
            dong.append(_dong(r.customer_name or f"Yêu cầu #{r.id}",
                              f"{r.pax} khách" if r.pax else "", phai, phai_phu, kieu))
    return _o("yeu_cau_booking", "Yêu cầu chờ tạo booking", len(rows), "yêu cầu",
              "/requests", "service_requests.booking_id rỗng; hạn từ tham số sla_booking_phut",
              muc="do" if qua else ("vang" if rows else "xanh"),
              nhan_muc="Có việc quá hạn" if qua else ("Đang trong hạn" if rows else "Không còn việc chờ"),
              ghi_chu=f"Hạn {sla / 60:.0f} giờ từ khi nhận yêu cầu", dong=dong)


def _su_co_qua_han(db: Session) -> dict:
    """Sự cố tour quá hạn mà CHƯA CÓ NGƯỜI NHẬN.

    Dùng lại `su_co_tour.qua_han()` — đúng hàm mà robot cảnh báo gọi. Quá hạn là một sự kiện tính
    tại chỗ chứ không phải cột lưu sẵn (xem chú thích của chính hàm ấy), nên gõ lại phép so sánh ở
    đây là dựng chỗ thứ hai có thể lệch.
    """
    from app.models.su_co_tour import SuCoTour, SC_NHOM
    from app.services import su_co_tour as SC

    bay_gio = datetime.now()
    rows = [sc for sc in db.execute(select(SuCoTour).where(SuCoTour.trang_thai != "dong")
                                    .order_by(SuCoTour.han_xu_ly)).scalars()
            if SC.qua_han(sc, bay_gio)]
    dong = []
    for sc in rows[:SO_DONG_MAU]:
        tre = (bay_gio - sc.han_xu_ly).total_seconds() / 3600 if sc.han_xu_ly else 0
        dong.append(_dong(f"{SC_NHOM.get(sc.nhom, sc.nhom)} · Mức {sc.muc}", sc.code,
                          f"Quá {int(tre // 24)} ngày" if tre >= 24 else f"Quá {int(tre)} giờ",
                          "", "do"))
    return _o("su_co_qua_han", "Sự cố tour quá hạn", len(rows), "hồ sơ",
              "/su-co-tour?qua_han=1",
              "su_co_tour chưa đóng, quá hạn xử lý và chưa ai nhận (su_co_tour.qua_han)",
              muc="do" if rows else "xanh",
              nhan_muc="Cần xử lý ngay" if rows else "Không có sự cố quá hạn",
              ghi_chu="Hạn xử lý theo mức sự cố", dong=dong)


def _de_nghi_chi_cho_xac_nhan(db: Session, vai_xac_nhan: tuple[str, ...]) -> dict:
    """Đề nghị chi đang chờ BỘ PHẬN xác nhận — bước trước khi trình duyệt.

    Loại chi nào thuộc bộ phận nào đọc từ `ops.CATEGORY_CONFIRMER`, đúng bảng mà bước xác nhận
    dùng. Khai tay một danh sách loại chi ở đây là mở đường cho bàn làm việc đếm một tập, còn
    người bấm xác nhận lại thấy một tập khác.
    """
    from app.models.ops import PaymentRequest
    from app.services import ops as OPS

    loai = [k for k, v in OPS.CATEGORY_CONFIRMER.items() if any(r in v for r in vai_xac_nhan)]
    if not loai:
        return _o("de_nghi_chi", "Đề nghị chi chờ xác nhận", None, "đề nghị", "/expenses",
                  "payment_requests.status = cho_tp, lọc theo ops.CATEGORY_CONFIRMER",
                  trang_thai=THIEU_NGUON,
                  ly_do="Phòng này chưa được khai là bộ phận xác nhận của loại chi nào.")
    rows = list(db.execute(select(PaymentRequest)
                           .where(PaymentRequest.status == "cho_tp",
                                  PaymentRequest.category.in_(loai))
                           .order_by(PaymentRequest.amount.desc())).scalars())
    dong = []
    for p in rows[:SO_DONG_MAU - 1]:
        dong.append(_dong(p.supplier_name or p.code, "Nhà cung cấp", _trieu(p.amount or 0), "triệu"))
    # Dòng thứ ba là PHẦN CÒN LẠI, không phải một hồ sơ. Nói rõ bằng chữ "N khoản còn lại": một
    # con số gộp trông y hệt một con số lẻ, và người đọc sẽ tưởng đó là giá trị của một đề nghị.
    con = rows[SO_DONG_MAU - 1:]
    if con:
        dong.append(_dong(f"{len(con)} khoản còn lại", "",
                          _trieu(sum(p.amount or 0 for p in con)), "triệu"))
    return _o("de_nghi_chi", "Đề nghị chi chờ xác nhận", len(rows), "đề nghị", "/expenses",
              "payment_requests.status = cho_tp, loại chi theo ops.CATEGORY_CONFIRMER",
              muc="vang" if rows else "xanh",
              nhan_muc="Chờ bộ phận" if rows else "Không còn đề nghị chờ",
              ghi_chu="Xác nhận trước khi trình duyệt", dong=dong)


def _quyet_toan_cho(db: Session) -> dict:
    """Chuyến đã kết thúc mà hồ sơ quyết toán chưa đi hết đường.

    HAI CHẶNG, KHÔNG GỘP: `ket_thuc` là chuyến chờ CHÍNH ĐIỀU HÀNH đóng số — việc của phòng này;
    `da_dong_so` là chuyến đã đóng, đang chờ Kế toán — phòng này chỉ theo dõi, không làm gì thêm.
    Gộp hai con số thành một là nói với trưởng phòng rằng anh đang nợ chín bộ hồ sơ trong khi ba
    bộ đã nằm trên bàn người khác.

    MỘT ĐIỀU CÒN THIẾU, GHI RA CHỨ KHÔNG BỊA: bản dựng thử ngày 12/10 có dòng "Kế toán trả lại,
    cần sửa". VTOS hôm nay KHÔNG có trạng thái ấy — `TOUR_STATUS` đi một chiều
    ket_thuc → da_dong_so → kt_xac_nhan → khoa, không có đường lùi nào mang tên "trả lại". Nên ô
    này chỉ có hai dòng thật, và việc dựng cửa trả lại là một việc còn thiếu của hệ thống, không
    phải một dòng để màn hình này vẽ ra cho đủ hình.
    """
    from app.models.core import Tour
    from app.services import rules as R

    cho_dong = list(db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars())
    cho_kt = db.execute(select(Tour).where(Tour.status == "da_dong_so")).scalars().all()
    hom_nay = date.today()
    qua_han = [t for t in cho_dong if hom_nay > R.settlement_deadline(db, t)]
    dong = [_dong("Chờ Điều hành đóng số", "", str(len(cho_dong)), "chuyến",
                  "do" if qua_han else ""),
            _dong("Đã đóng số, chờ Kế toán", "", str(len(cho_kt)), "chuyến")]
    if qua_han:
        dong.append(_dong("Trong đó đã quá hạn quyết toán", "", str(len(qua_han)), "chuyến", "do"))
    return _o("quyet_toan", "Quyết toán tour đang chờ", len(cho_dong) + len(cho_kt), "chuyến",
              "/so-con-no",
              "tours.status = ket_thuc (chờ Điều hành) và da_dong_so (chờ Kế toán); "
              "hạn quyết toán từ tham số chính sách",
              muc="do" if qua_han else ("vang" if cho_dong else "xanh"),
              nhan_muc=("Có chuyến quá hạn" if qua_han
                        else "Cần hoàn thiện hồ sơ" if cho_dong else "Không còn chuyến chờ"),
              ghi_chu="Theo dõi đến khi hoàn thiện hồ sơ", dong=dong)


def _bao_cao_ngay_chua_cham(db: Session, phong_ks: tuple[str, ...]) -> dict:
    """Báo cáo ngày của NHÂN VIÊN PHÒNG NÀY mà trưởng phòng chưa chấm.

    CẮT THEO PHÒNG, và đây là chỗ khác với bảng điều hành `/`. Ô "báo cáo ngày chưa chấm" trên
    màn hình 01 đếm báo cáo của MỌI phòng rồi hiện cho bảy vai — một trưởng phòng Điều hành nhìn
    thấy cả báo cáo của Marketing lẫn Kinh doanh trong con số của mình. Ở bàn làm việc của một
    phòng thì con số ấy phải là của phòng ấy, nếu không bấm vào sẽ ra một danh sách không phải
    việc của mình.

    Phòng của một người suy từ VAI TRÒ qua `ks_robot.PHONG_CUA_VAI_TRO` — bảng đã có và đang được
    robot kiểm soát dùng để gán việc. Không khai bảng vai→phòng thứ hai ở đây: hai bảng thì ngày
    có vai mới, một bảng được cập nhật còn bảng kia im lặng đếm thiếu.
    """
    from app.models.core import User
    from app.models.ops import DailyReport
    from app.services.ks_robot import PHONG_CUA_VAI_TRO

    if not phong_ks:
        return _o("bao_cao_ngay", "Báo cáo ngày chưa chấm", None, "báo cáo", "/reports",
                  "daily_reports.reviewed_by rỗng, lọc theo phòng của người báo cáo",
                  trang_thai=THIEU_NGUON,
                  ly_do="Chưa khai phòng này trong bảng vai trò → phòng ban.")
    nguoi = {u.id: u for u in db.execute(select(User)).scalars()
             if PHONG_CUA_VAI_TRO.get(u.role, "") in phong_ks}
    rows = [r for r in db.execute(select(DailyReport).where(DailyReport.reviewed_by == "")
                                  .order_by(DailyReport.report_date)).scalars()
            if r.user_id in nguoi]
    dong = []
    for r in rows[:SO_DONG_MAU]:
        u = nguoi[r.user_id]
        dong.append(_dong(u.full_name or u.username, f"Báo cáo ngày {r.report_date:%d/%m}",
                          "Chưa chấm", "", "vang"))
    return _o("bao_cao_ngay", "Báo cáo ngày chưa chấm", len(rows), "báo cáo", "/reports",
              "daily_reports.reviewed_by rỗng, người báo cáo thuộc phòng này "
              "(ks_robot.PHONG_CUA_VAI_TRO)",
              muc="vang" if rows else "xanh",
              nhan_muc="Chờ chấm điểm" if rows else "Đã chấm hết",
              ghi_chu="Chấm trong ngày để điểm tháng không bị treo", dong=dong)


# ══════════════════════════════════ ĐĂNG KÝ THEO PHÒNG ══════════════════════════════════
#
# MỘT PHÒNG, KHÔNG PHẢI TÁM. Vòng này là vòng THỬ của Phòng Điều hành (Chủ tịch chọn 12/10/2026).
# Phòng chưa khai thì trả về danh sách RỖNG và màn hình không vẽ bàn nào — chứ không vẽ một cái
# bàn trống, vì bàn trống trông y hệt "hôm nay không có việc gì".
#
# `phong_ks` nối khoá phòng của `bao_cao_phong` sang tên phòng của `ks_robot.PHONG_CUA_VAI_TRO`:
# hai bảng đã có sẵn, mỗi bảng có chủ, và đây là chỗ DUY NHẤT nối chúng. Visa đi cùng Điều hành vì
# `bao_cao_phong.PHONG["visa"]["thuoc"] == "dieu_hanh"`.
def _de_nghi_xe_cho_lap_lenh(db: Session) -> dict:
    """Đề nghị xe Điều hành đã gửi mà Giám đốc đội xe chưa lập lệnh (mắt 1 → mắt 2)."""
    from app.models.core import Tour
    from app.models.de_nghi_xe import DeNghiXe
    rows = list(db.execute(select(DeNghiXe).where(DeNghiXe.trang_thai == "cho_lap_lenh")
                           .order_by(DeNghiXe.ngay_di)).scalars())
    dong = []
    for d in rows[:SO_DONG_MAU]:
        t = db.get(Tour, d.tour_id)
        con = (d.ngay_di - date.today()).days
        dong.append(_dong(t.code if t else f"#{d.id}", f"{d.so_khach} khách · cần {d.so_xe_can} xe",
                          f"Đi sau {con} ngày" if con > 0 else "Đi hôm nay",
                          "", "do" if con <= 1 else ("vang" if con <= 3 else "")))
    return _o("de_nghi_xe_cho_lap_lenh", "Đề nghị xe chờ lập lệnh", len(rows), "đề nghị",
              "/lenh-dieu-xe",
              "fleet_vehicle_requests đang ở trạng thái cho_lap_lenh (de_nghi_xe.danh_sach)",
              muc="do" if rows else "xanh",
              nhan_muc="Có đề nghị đang chờ" if rows else "Không còn đề nghị nào chờ",
              ghi_chu="Điều hành đề nghị → Giám đốc đội xe lập lệnh → tài xế nhận", dong=dong)


def _lenh_tai_xe_chua_nhan(db: Session) -> dict:
    """Lệnh QUÁ HẠN mà tài xế chưa bấm nhận, cộng lệnh tài xế đã báo không nhận được (mắt 3).

    Gộp hai nhóm vào MỘT ô chứ không hai: với Giám đốc đội xe cả hai là một việc — "chuyến này
    chưa chắc có người lái". Tách ra là bắt ông mở hai chỗ để trả lời một câu hỏi.

    Dùng lại `nhan_lenh.can_giam_doc_xe_biet()` — đúng hàm màn hình lệnh điều xe gọi. Gõ lại phép
    so sánh quá hạn ở đây là dựng chỗ thứ hai có thể lệch, đúng lý do đã ghi ở `_su_co_qua_han`.
    """
    from app.services import nhan_lenh as NL
    kq = NL.can_giam_doc_xe_biet(db)
    rows = kq["qua_han"] + kq["tu_choi"]
    dong = []
    for r in rows[:SO_DONG_MAU]:
        dong.append(_dong(f"{r['xe']} · {r['tai_xe']}",
                          f"đi {r['ngay_di']}",
                          ("Báo không nhận được" if r["trang_thai_nhan"] == NL.TU_CHOI
                           else "Quá hạn, chưa bấm"), "", "do"))
    return _o("lenh_tai_xe_chua_nhan", "Lệnh tài xế chưa nhận", len(rows), "lệnh",
              "/lenh-dieu-xe",
              "dispatch_orders còn hiệu lực, quá hạn nhận hoặc tài xế đã từ chối "
              "(nhan_lenh.can_giam_doc_xe_biet)",
              muc="do" if rows else "xanh",
              nhan_muc="Cần đổi người hoặc đổi xe" if rows else "Mọi lệnh đều có người nhận",
              ghi_chu=f"Hạn nhận {kq['han_gio']} giờ trước ngày đi. Quá hạn KHÔNG huỷ lệnh – "
                      "lệnh vẫn hiệu lực, đây chỉ là chỗ thấy sớm.", dong=dong)


def _lenh_da_nhan_trong_tuan(db: Session) -> dict:
    """Mẫu số cho ô trên.

    Có mặt vì một lý do: "2 lệnh quá hạn" đứng một mình không nói được gì. 2 trên 13 là chuyện
    thường; 2 trên 3 là đội xe đang có vấn đề. Ô này KHÔNG phải việc phải làm — nó là con số để
    đọc ô kia, nên `muc` luôn xanh và không có dòng mẫu nào.
    """
    from app.services import nhan_lenh as NL
    n = NL.da_nhan_trong_tuan(db)
    return _o("lenh_da_nhan_trong_tuan", "Lệnh tài xế đã nhận (7 ngày)", n, "lệnh",
              "/lenh-dieu-xe",
              "dispatch_orders có nhan_luc trong 7 ngày gần nhất (nhan_lenh.da_nhan_trong_tuan)",
              muc="xanh", nhan_muc="Để đọc con số ở ô trên",
              ghi_chu="Không phải việc phải làm – đây là mẫu số")


# Ô nào dựng bằng hàm nào. Một bảng, một nơi khai — để thêm bàn là thêm một dòng trong `BAN`
# chứ không phải sửa thân hàm `ban()`.
O_HAM = {
    "yeu_cau_booking": lambda db, cfg: _yeu_cau_cho_booking(db),
    "su_co_qua_han": lambda db, cfg: _su_co_qua_han(db),
    "de_nghi_chi": lambda db, cfg: _de_nghi_chi_cho_xac_nhan(db, cfg["vai_xac_nhan"]),
    "quyet_toan": lambda db, cfg: _quyet_toan_cho(db),
    "bao_cao_ngay": lambda db, cfg: _bao_cao_ngay_chua_cham(db, cfg["phong_ks"]),
    "de_nghi_xe_cho_lap_lenh": lambda db, cfg: _de_nghi_xe_cho_lap_lenh(db),
    "lenh_tai_xe_chua_nhan": lambda db, cfg: _lenh_tai_xe_chua_nhan(db),
    "lenh_da_nhan_trong_tuan": lambda db, cfg: _lenh_da_nhan_trong_tuan(db),
}

# Ô là MẪU SỐ để đọc ô khác, không phải việc phải làm. Không cộng vào tổng đang chờ.
MAU_SO = ("lenh_da_nhan_trong_tuan",)

BAN = {
    "dieu_hanh": {
        "ten": "Bàn làm việc Điều hành",
        "vai_xac_nhan": ("tp_dh",),
        "phong_ks": ("Điều hành", "Visa"),
        "o": ("yeu_cau_booking", "su_co_qua_han", "de_nghi_chi", "quyet_toan", "bao_cao_ngay"),
    },
    # DL-1b (12/10/2026) — BÀN ĐỘI XE. Chủ tịch chốt: Giám đốc đội xe thấy "ai đã nhận, ai chưa"
    # ngay trên bàn làm việc của ông, không phải tự đi tìm trong bảng lệnh.
    #
    # KHÔNG dựng cơ chế mới: `PHONG["doi_xe"]` đã có sẵn trong `bao_cao_phong` với `xem:
    # ("gd_doi_xe",)`, và cửa `/bao-cao/ban-lam-viec` đã chặn theo `pham_vi_cho_nguoi`. Khai thêm
    # một dòng ở đây là đủ — khai lại danh sách phòng hay dựng cửa riêng là dựng chỗ thứ hai để
    # hai bảng lệch nhau.
    "doi_xe": {
        "ten": "Bàn làm việc Đội xe",
        "o": ("de_nghi_xe_cho_lap_lenh", "lenh_tai_xe_chua_nhan",
              "lenh_da_nhan_trong_tuan"),
    },
}


def co_ban(phong: str) -> bool:
    return phong in BAN


def ban(db: Session, phong: str) -> dict:
    """Bàn làm việc của một phòng. Chỉ đọc; không ghi, không duyệt, không đóng sổ."""
    cfg = BAN.get(phong)
    if cfg is None:
        return {"phong": phong, "co_ban": False, "o": [], "tong_dang_cho": None,
                "vi_sao": "Phòng này chưa khai bàn làm việc. Bảng chỉ tiêu vẫn hiện như cũ."}

    def _chay(ten_o: str, ham) -> dict:
        # Một ô hỏng không được kéo sập cả bàn — xem điều (b) ở đầu tệp. Lỗi hiện ra thành một ô
        # màu riêng kèm lý do, chứ không biến thành số 0.
        try:
            return ham()
        except Exception as ex:                                   # noqa: BLE001 – xem trên
            return _o(ten_o, ten_o, None, "", "", "", trang_thai=LOI, ly_do=str(ex)[:200])

    # MỘT ĐƯỜNG CHẠY CHO MỌI PHÒNG. Bản đầu (BD-1) gọi thẳng năm ô của Điều hành ở đây, nên bàn
    # thứ hai không thể có ô khác. DL-1b (12/10/2026) đổi sang: mỗi bàn KHAI danh sách ô của mình
    # trong `BAN`, và vòng lặp dưới đây dựng đúng những ô ấy. Thêm bàn thứ ba sau này là thêm một
    # dòng khai, không phải sửa hàm này nữa.
    o = [_chay(k, (lambda f=O_HAM[k]: f(db, cfg))) for k in cfg["o"] if k in O_HAM]
    # Ô "mẫu số" không phải việc phải làm, nên không cộng vào tổng đang chờ — cộng vào thì con số
    # trên bàn nói sai, và một con số nói sai thì lần sau không ai tin con số trên bàn mình nữa.
    dem = [x for x in o if x["khoa"] not in MAU_SO]
    du = all(x["trang_thai"] == SAN_SANG for x in dem)
    return {"phong": phong, "co_ban": True, "ten": cfg["ten"], "o": o,
            # Điều (c) ở đầu tệp: thiếu một ô thì KHÔNG có tổng. `None` để màn hình nói
            # "chưa đủ dữ liệu", chứ không in một con số thiếu mà trông như đủ.
            "tong_dang_cho": sum(x["so_luong"] for x in dem) if du else None,
            "doc_luc": datetime.now()}
