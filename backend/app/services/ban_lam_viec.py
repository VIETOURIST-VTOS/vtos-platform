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

    VÀ BẢN ĐẦU (BD-1) ĐÃ GỘP ĐÚNG NHƯ THẾ — sửa 12/10/2026, giữ lại vết. Đoạn chú thích ngay
    trên viết ra điều cấm, rồi dòng `return` ngay dưới lại trả `len(cho_dong) + len(cho_kt)`.
    Hai dòng mẫu thì tách đúng, nhưng CON SỐ TO — thứ người ta liếc một cái là thấy, và thứ cộng
    vào tổng "đang chờ" của cả bàn — thì gộp. Đo trên dữ liệu thật ngày 12/10: ô hiện **1663**
    trong khi việc của riêng Điều hành là **638**; 1025 chuyến còn lại đã nằm trên bàn Kế toán và
    phòng này không làm gì thêm được. Trưởng phòng mở máy buổi sáng thấy một núi việc gấp hai
    lần rưỡi sự thật.

    Nay con số của ô là `len(cho_dong)` — ĐÚNG việc của phòng này. Chặng Kế toán vẫn hiện, vì bỏ
    đi là mất chỗ duy nhất phòng này theo dõi hồ sơ của mình sau khi giao đi; nó hiện thành một
    DÒNG có ghi rõ "không tính vào ô này". Tên ô đổi theo cho khớp: "Chuyến chờ Điều hành đóng
    số", không còn là "Quyết toán tour đang chờ" — một cái tên rộng hơn con số nó mang cũng là
    một cách nói sai, chỉ êm hơn.

    BÀI HỌC GHI LẠI: chú thích nói một đằng, mã làm một nẻo, và không hàng rào nào kêu suốt từ
    12/10 tới 12/10 vì mọi phép thử đều soi hai DÒNG MẪU chứ không soi CON SỐ của ô. Phép thử
    `test_bd1_o_quyet_toan_dem_dung_viec_cua_phong_nay` nay soi đúng con số ấy.

    DÒNG "KẾ TOÁN TRẢ LẠI, CẦN SỬA" (bản dựng thử 12/10) có từ 19/10/2026. Không có trạng thái
    riêng — `TOUR_STATUS` vẫn đi ket_thuc → da_dong_so → kt_xac_nhan → khoa, và nút trả lại
    (`settlement.kt_return`) đưa chuyến về ket_thuc. Máy nhận ra chuyến bị trả lại bằng lịch sử
    chuyến (`services/tra_lai_quyet_toan.py`), và dòng ấy là MỘT PHẦN của con số ô.
    """
    from app.models.core import Tour
    from app.services import rules as R

    cho_dong = list(db.execute(select(Tour).where(Tour.status == "ket_thuc")).scalars())
    cho_kt = db.execute(select(Tour).where(Tour.status == "da_dong_so")).scalars().all()
    hom_nay = date.today()
    qua_han = [t for t in cho_dong if hom_nay > R.settlement_deadline(db, t)]
    dong = [_dong("Chờ Điều hành đóng số", "", str(len(cho_dong)), "chuyến",
                  "do" if qua_han else ""),
            # KHÔNG tính vào con số của ô, và nói ra bằng CHỮ chứ không để người đọc tự suy.
            _dong("Đã đóng số, đang ở bàn Kế toán", "không tính vào ô này",
                  str(len(cho_kt)), "chuyến")]
    # 19/10/2026 — dòng "Kế toán trả lại, cần sửa" mà bản dựng thử 12/10 đã vẽ. Nhận ra bằng lịch
    # sử chuyến (`tra_lai_quyet_toan`), không bằng một trạng thái mới; là MỘT PHẦN của con số ô.
    from app.services import tra_lai_quyet_toan as TLQ
    ids = [i for i in (getattr(t, "id", None) for t in cho_dong) if i is not None]
    tra_lai = TLQ.dang_bi_tra_lai(db, ids) if ids else {}
    if tra_lai:
        dong.append(_dong("Trong đó Kế toán trả lại, cần sửa", "", str(len(tra_lai)), "chuyến", "vang"))
    if qua_han:
        dong.append(_dong("Trong đó đã quá hạn quyết toán", "", str(len(qua_han)), "chuyến", "do"))
    return _o("quyet_toan", "Chuyến chờ Điều hành đóng số", len(cho_dong), "chuyến",
              "/so-con-no",
              "tours.status = ket_thuc — CHỈ chuyến chờ chính phòng này đóng số. "
              "da_dong_so là dòng theo dõi, KHÔNG cộng vào con số của ô. "
              "Hạn quyết toán từ tham số chính sách",
              muc="do" if qua_han else ("vang" if cho_dong else "xanh"),
              nhan_muc=("Có chuyến quá hạn" if qua_han
                        else "Cần hoàn thiện hồ sơ" if cho_dong else "Không còn chuyến chờ"),
              ghi_chu="Đếm chuyến chờ CHÍNH phòng này đóng số", dong=dong)


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


# ══════════════════════════ HÀNG ĐỢI CỦA PHÒNG HƯỚNG DẪN — Đợt HD-BH1 ══════════════════════════
#
# Năm ô việc và một mẫu số. KHÔNG ô nào tự nghĩ ra phép lọc: cả năm gọi hàm trong
# `services/hdv.py`, nơi phép lọc của các cửa API đã được rút về. Xem chú thích ở đó.

def _hdv_chao_qua_han(db: Session) -> dict:
    """Lời chào đã quá hạn trả lời mà VẪN đang giữ lịch của người ta — Đợt HD-12.

    Quá hạn KHÔNG phải là từ chối: bản ghi vẫn `cho_xac_nhan`, vì không ai trả lời cả. Ô này là
    chỗ người điều phối thấy chúng để đi chào người khác, chứ không phải chỗ máy tự đóng.
    """
    from app.services import hdv as HDV
    rows = HDV.loi_chao_qua_han(db)
    dong = []
    for a in sorted(rows, key=lambda x: x.han_tra_loi)[:SO_DONG_MAU]:
        from app.models.core import Tour
        from app.models.hr import Employee
        t = db.get(Tour, a.tour_id); e = db.get(Employee, a.guide_id)
        qua = (datetime.now() - a.han_tra_loi).days
        dong.append(_dong(t.code if t else f"#{a.tour_id}", e.full_name if e else "",
                          f"Quá {qua} ngày" if qua >= 1 else "Vừa quá hạn", "Hạn trả lời", "do"))
    return _o("hdv_chao_qua_han", "Lời chào quá hạn trả lời", len(rows), "lời chào",
              "/huong-dan",
              "guide_assignments còn cho_xac_nhan và đã quá han_tra_loi (hdv.loi_chao_qua_han)",
              muc="do" if rows else "xanh",
              nhan_muc="Cần chào người khác" if rows else "Không có lời chào nào quá hạn",
              ghi_chu="Quá hạn KHÔNG phải là từ chối, và KHÔNG tự nhả lịch – công tắc nhả lịch "
                      "mặc định TẮT, chờ Chủ tịch bật.", dong=dong)


def _hdv_chuyen_chua_co_nguoi(db: Session) -> dict:
    """Chuyến khởi hành trong 30 ngày tới mà chưa ai nhận."""
    from app.services import hdv as HDV
    rows = HDV.chuyen_chua_co_nguoi(db, 30)
    hom_nay = date.today()
    dong, gap = [], 0
    for t in rows:
        con = (t.start_date - hom_nay).days
        if con <= 7:
            gap += 1
        if len(dong) < SO_DONG_MAU:
            dong.append(_dong(t.code, t.name or "",
                              f"Đi sau {con} ngày" if con > 0 else "Đi hôm nay", "",
                              "do" if con <= 3 else ("vang" if con <= 7 else "")))
    return _o("hdv_chuyen_chua_co_nguoi", "Chuyến chưa có hướng dẫn viên", len(rows), "chuyến",
              "/huong-dan",
              "tours khởi hành trong 30 ngày, chưa có lượt chào nào ngoài huỷ "
              "(hdv.chuyen_chua_co_nguoi)",
              muc="do" if gap else ("vang" if rows else "xanh"),
              nhan_muc=(f"{gap} chuyến đi trong 7 ngày tới" if gap
                        else ("Còn thời gian xếp người" if rows else "Mọi chuyến đều có người")),
              ghi_chu="Lượt chào đã HUỶ không tính là đã có người; từ chối và hết hạn thì vẫn "
                      "tính – đây là hành vi đang chạy của màn hình nguồn, không đổi ở đây.",
              dong=dong)


def _hdv_the_sap_het_han(db: Session) -> dict:
    """Thẻ hành nghề đã hết hạn hoặc sắp hết trong 60 ngày."""
    from app.services import hdv as HDV
    rows = HDV.the_sap_het_han(db)
    hom_nay = date.today()
    het, dong = 0, []
    for e in rows:
        con = (e.card_expiry - hom_nay).days
        if con < 0:
            het += 1
        if len(dong) < SO_DONG_MAU:
            dong.append(_dong(e.full_name, e.code,
                              f"Hết hạn {-con} ngày trước" if con < 0 else f"Còn {con} ngày",
                              "Thẻ hành nghề", "do" if con < 0 else "vang"))
    return _o("hdv_the_sap_het_han", "Thẻ hành nghề hết hạn hoặc sắp hết", len(rows), "người",
              "/huong-dan",
              f"employees phòng hướng dẫn, card_expiry trong {HDV.SAP_HET_HAN_NGAY} ngày "
              "(hdv.the_sap_het_han)",
              muc="do" if het else ("vang" if rows else "xanh"),
              nhan_muc=(f"{het} người ĐÃ hết hạn, không chào chuyến được" if het
                        else ("Cần giục gia hạn" if rows else "Mọi thẻ đều còn hạn")),
              ghi_chu="Đã hết hạn thì cổng 13 chặn chào chuyến ngay hôm nay; sắp hết hạn thì vẫn "
                      "chào được – mỗi dòng nói rõ nó thuộc loại nào. Con số này LỚN HƠN ô "
                      "«thẻ sắp hết hạn» trên màn hình /huong-dan, vì ô ấy chỉ đếm người CHƯA "
                      "hết hạn. Hai câu hỏi khác nhau, không phải một trong hai sai.",
              dong=dong)


def _hdv_phan_cong_thieu_gio(db: Session) -> dict:
    """Phân công chưa có mốc giờ – chưa kiểm trùng lịch được."""
    from app.models.core import Tour
    from app.models.hr import Employee
    from app.services import hdv as HDV
    rows = HDV.phan_cong_thieu_gio(db)
    dong = []
    for a in rows[:SO_DONG_MAU]:
        t = db.get(Tour, a.tour_id); e = db.get(Employee, a.guide_id)
        dong.append(_dong(t.code if t else f"#{a.tour_id}", e.full_name if e else "",
                          "Chưa có giờ", "Không kiểm được trùng", "vang"))
    return _o("hdv_phan_cong_thieu_gio", "Phân công chưa có mốc giờ", len(rows), "phân công",
              "/huong-dan",
              "guide_assignments còn chiếm lịch mà thiếu bat_dau hoặc ket_thuc "
              "(hdv.phan_cong_thieu_gio)",
              muc="vang" if rows else "xanh",
              nhan_muc="Cần nhập giờ đón và giờ trả" if rows else "Mọi phân công đều có giờ",
              ghi_chu="Thiếu giờ thì KHÔNG kiểm được trùng lịch – đây là việc còn THIẾU DỮ LIỆU, "
                      "không phải đã kiểm và không trùng.", dong=dong)


def _hdv_pham_vi_lech(db: Session) -> dict:
    """Loại thẻ không nhận được loại chuyến – Đợt HD-PV1."""
    from app.services import hdv as HDV
    rows = HDV.pham_vi_lech(db)
    dong = []
    for r in rows[:SO_DONG_MAU]:
        dong.append(_dong(r["hdv"], f"{r['ma_nv']} · thẻ {r['the_loai'] or 'chưa khai'}",
                          r["tour_code"], r["loai_chuyen"], "do"))
    return _o("hdv_pham_vi_lech", "Phạm vi hành nghề không đạt", len(rows), "phân công",
              "/huong-dan",
              "guide_assignments còn chiếm lịch mà loại thẻ không nhận loại chuyến "
              "(hdv.pham_vi_lech, bảng PHAM_VI_THE theo Điều 58 Luật Du lịch 2017)",
              muc="do" if rows else "xanh",
              nhan_muc="Sai phạm vi hành nghề" if rows else "Không có phân công nào sai phạm vi",
              ghi_chu="Ô này CHỈ đếm nhóm «không đạt». Hồ sơ chưa khai loại thẻ là việc phải NHẬP "
                      "của HCNS, nằm ở cửa /huong-dan/pham-vi-the/lech, không đưa lên bàn này.",
              dong=dong)


def _hdv_du_dieu_kien(db: Session) -> dict:
    """Mẫu số. «3 thẻ sắp hết hạn» đứng một mình không nói được gì: 3 trên 40 là chuyện thường,
    3 trên 5 là cả phòng sắp không ai chào chuyến được. Ô này KHÔNG phải việc phải làm."""
    from app.models.hr import Employee
    from app.services.hr import guide_eligible
    hom_nay = date.today()
    ds = [e for e in db.execute(
        select(Employee).where(Employee.department == "huong_dan")).scalars() if e.active]
    du = sum(1 for e in ds if guide_eligible(e, hom_nay)[0])
    return _o("hdv_du_dieu_kien", "Hướng dẫn viên đủ điều kiện hành nghề", du, "người",
              "/huong-dan",
              "employees phòng hướng dẫn còn active, qua guide_eligible (cổng 13)",
              muc="xanh", nhan_muc=f"Trên tổng {len(ds)} người của phòng",
              ghi_chu="Không phải việc phải làm – đây là mẫu số để đọc bốn ô trên.")


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
    "hdv_chao_qua_han": lambda db, cfg: _hdv_chao_qua_han(db),
    "hdv_chuyen_chua_co_nguoi": lambda db, cfg: _hdv_chuyen_chua_co_nguoi(db),
    "hdv_the_sap_het_han": lambda db, cfg: _hdv_the_sap_het_han(db),
    "hdv_phan_cong_thieu_gio": lambda db, cfg: _hdv_phan_cong_thieu_gio(db),
    "hdv_pham_vi_lech": lambda db, cfg: _hdv_pham_vi_lech(db),
    "hdv_du_dieu_kien": lambda db, cfg: _hdv_du_dieu_kien(db),
}

# Ô là MẪU SỐ để đọc ô khác, không phải việc phải làm. Không cộng vào tổng đang chờ.
MAU_SO = ("lenh_da_nhan_trong_tuan", "hdv_du_dieu_kien")

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
    # HD-BH1 (15/10/2026) — BÀN PHÒNG HƯỚNG DẪN. Chủ tịch chốt sau khi đo được rằng Trưởng phòng
    # Hướng dẫn mở màn hình ra chỉ nhận đúng câu "Phòng này chưa khai bàn làm việc".
    #
    # KHÔNG dựng cơ chế mới, đúng như dòng `doi_xe` đã làm: `PHONG["huong_dan"]` có sẵn trong
    # `bao_cao_phong` với `xem: ("tp_hd",)`, và cửa `/bao-cao/ban-lam-viec` đã chặn theo
    # `pham_vi_cho_nguoi`. Đo thật: `tp_hd` vào được `phong=huong_dan`, bị chặn 403 ở
    # `phong=doi_xe`, và `gd_doi_xe` bị chặn ngược lại. Khai thêm một dòng ở đây là đủ.
    "huong_dan": {
        "ten": "Bàn làm việc Hướng dẫn",
        "o": ("hdv_chao_qua_han", "hdv_chuyen_chua_co_nguoi", "hdv_the_sap_het_han",
              "hdv_phan_cong_thieu_gio", "hdv_pham_vi_lech", "hdv_du_dieu_kien"),
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
