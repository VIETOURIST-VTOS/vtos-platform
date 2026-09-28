"""VPM-11 – dựng và đọc SỔ NGHĨA VỤ. Một nghĩa vụ, một dòng, một mã gốc.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO ĐỒNG BỘ CHỨ KHÔNG GHI THẲNG TỪ BẢY DỊCH VỤ
────────────────────────────────────────────────────────────────────────────────

Cách hiển nhiên là sửa bảy dịch vụ đang có (đề nghị chi, đơn đặt dịch vụ, lịch vay, lịch thu hợp
đồng, booking, kế hoạch tiền, bảng lương) để mỗi khi chúng ghi thì ghi luôn một dòng vào sổ nghĩa vụ.
KHÔNG LÀM THẾ, có lý do:

  1. Bảy tệp ấy là nơi ba phiên robot khác đang viết cùng lúc. Chạm vào bảy chỗ là bảy cơ hội làm
     vỡ việc của người khác, trên những nhánh mà phiên này không đọc được.
  2. Ghi thẳng chỉ đúng cho dữ liệu SINH RA TỪ NAY. Hệ thống đang có sẵn hàng nghìn đề nghị chi và
     booking cũ; chúng sẽ không bao giờ vào sổ, và bảng dòng tiền sẽ thiếu đúng phần quá khứ.
  3. Ghi thẳng thì một lỗi phân loại phải sửa bằng một bản vá dữ liệu. Đồng bộ thì sửa hàm rồi chạy
     lại – sổ tự đúng.

Giá phải trả: sổ trễ hơn chứng từ gốc đúng một nhịp đồng bộ. Chấp nhận được, vì bảng dòng tiền là
bảng DỰ BÁO theo ngày, không phải sổ quỹ theo giây. Nhịp chạy do V11 (lịch tự động hoá) đặt.

────────────────────────────────────────────────────────────────────────────────
CHẠY LẠI ĐƯỢC – ĐIỀU KIỆN SỐNG CÒN
────────────────────────────────────────────────────────────────────────────────

Mỗi dòng khoá theo cặp (`nguon_bang`, `nguon_id`), có ràng buộc duy nhất ở tầng cơ sở dữ liệu. Chạy
đồng bộ mười lần ra đúng một dòng. Không có tính chất này thì lần chạy thứ hai nhân đôi toàn bộ nhu
cầu tiền của công ty, và không ai nhìn ra ngay vì con số vẫn "trông hợp lý".

────────────────────────────────────────────────────────────────────────────────
BA CHỖ CHỐNG TRÙNG, VÀ MỘT CHỖ KHÔNG DÁM TỰ QUYẾT
────────────────────────────────────────────────────────────────────────────────

MỘT — THU KHÁCH. Hợp đồng khách thu tiền QUA phiếu thu của booking (xem lich_thanh_toan.da_thu).
Nên booking có lịch hợp đồng thì LẤY LỊCH (có ngày đến hạn thật), booking không có lịch thì mới lấy
phần còn phải thu của booking với ngày ước D-7. Cộng cả hai là đếm hai lần cùng một khoản tiền của
cùng một người khách.

HAI — CHI TOUR. Đơn đặt dịch vụ đã có đề nghị chi thì đề nghị chi là chứng từ sau, sổ lấy đề nghị
chi. Đơn chưa có đề nghị chi vẫn vào sổ – đó chính là "nghĩa vụ chưa lập đề nghị chi" mà mục III.4
của đề xuất đòi phải có.

BA — CHỖ KHÔNG DÁM TỰ QUYẾT. Cột `service_orders.payment_request_id` CÓ trong mô hình nhưng KHÔNG
CÓ CHỖ NÀO TRONG MÃ ĐANG CHẠY GÁN GIÁ TRỊ CHO NÓ (đã soát toàn bộ app/ ngày 11/9/2026). Nghĩa là
quy tắc HAI ở trên hôm nay gần như không bắt được cặp nào. Nên phép đồng bộ tự dò thêm: cùng tour,
cùng đối tượng, cùng số tiền → đánh dấu `nghi_trung_voi`, KHÔNG tự gộp, KHÔNG tự trừ. Gộp hai chứng
từ của hai phòng khác nhau là một quy tắc kế toán, và quy tắc kế toán phải có người ký.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ban_hang import HopDongKhach, LichThanhToanHD
from app.models.core import Booking, Tour, User
from app.models.finance import CashPlanItem, FinContract, FinSchedule
from app.models.nghia_vu import (GHI_NHO, NHOM, TRANG_THAI_DONG, NghiaVuThanhToan,
                                nhom_duoc_xem)
from app.models.ops import PaymentRequest
from app.models.suppliers import ServiceOrder, Supplier
from app.models.nghia_vu import NHOM_NGOAI_TAM_TGD as NGOAI_TAM
from app.services import payments as PAY

# Đề nghị chi chưa chuyển tiền. Lấy đúng danh sách mà finance.forecast_13w đang dùng để không có hai
# định nghĩa "đang chờ chi" trong cùng một hệ thống.
PR_CHUA_CHI = ("cho_tp", "cho_kt", "cho_duyet", "cho_chi")
# Đề nghị chi ĐÃ DUYỆT nhưng CHƯA CHUYỂN – khoản này bị TRỪ khỏi tiền khả dụng (mục III.1 của đề
# xuất), nên phải nhận diện riêng, không lẫn với khoản còn đang trình ký.
PR_DA_DUYET_CHUA_CHUYEN = ("cho_chi",)

# Đơn đặt dịch vụ đã thành nghĩa vụ thật: nhà cung cấp đã xác nhận hoặc dịch vụ đã dùng. Đơn còn
# "nhap"/"da_gui" là dự định, chưa ai nợ ai; đưa vào sổ là thổi phồng nhu cầu tiền.
SO_THANH_NGHIA_VU = ("da_xac_nhan", "da_su_dung")

# Sáu bảng mà phép đồng bộ dựng lại được. Dòng nào trong sổ mang một trong sáu tên này mà lần chạy
# hiện tại không dựng lại được thì bị ĐÓNG – xem _thu_hoi_dong_khong_con_can_cu.
NGUON_DONG_BO = ("lich_thanh_toan_hd", "bookings", "payment_requests", "service_orders",
                 "fin_schedules", "cash_plan_items", "cong_no_vietrip", "phai_tra_vietrip")

# Trạng thái lịch vay còn là nhu cầu tiền.
FS_CON_HAN = ("ke_hoach", "qua_han")

# Số ngày trước khởi hành mà tiền tour được coi là phải thu xong. Lấy đúng mốc D-7 mà
# finance.forecast_13w đang dùng – hai màn hình cùng nói về một khoản tiền thì phải cùng một mốc.
D_TRUOC_KHOI_HANH = 7

# Nhóm suy từ loại dòng lịch vay.
NHOM_THEO_FS = {"tra_goc": "tra_goc_vay", "tra_lai": "lai_phi_vay",
                "nhan_vay": "giai_ngan_vay", "giai_ngan": None, "thu_hoi": None}

# Nhóm suy từ loại đề nghị chi.
NHOM_THEO_PR = {"hoan_tien": "hoan_khach", "chi_tour": "tra_ncc",
                "marketing": "van_hanh_khac", "hanh_chinh": "van_hanh_khac"}

# Nhóm suy từ loại kế hoạch tiền do kế toán nhập tay.
NHOM_THEO_CASHPLAN = {"luong": "luong_bh", "thue": "thue"}


def _ma_goc(db: Session, stt: int) -> str:
    return f"NV{date.today():%y%m}-{stt:05d}"


def _dat(db: Session, ghi: dict, dem: list[int],
         cham: set[tuple[str, int]] | None = None) -> NghiaVuThanhToan:
    """Ghi hoặc cập nhật MỘT dòng theo khoá (nguon_bang, nguon_id). Đây là chỗ làm nên tính chạy-lại-được.

    Cập nhật chứ không xoá-rồi-tạo: xoá rồi tạo thì `ma_goc` đổi sau mỗi lần đồng bộ, mà mã gốc là
    DANH TÍNH của nghĩa vụ – thứ người ta dán vào chứng từ và gọi nhau qua điện thoại. Mã gốc phải
    đứng yên suốt đời của nghĩa vụ.
    """
    nv = db.execute(select(NghiaVuThanhToan).where(
        NghiaVuThanhToan.nguon_bang == ghi["nguon_bang"],
        NghiaVuThanhToan.nguon_id == ghi["nguon_id"])).scalars().first()
    if nv is None:
        dem[0] += 1
        nv = NghiaVuThanhToan(ma_goc=_ma_goc(db, dem[0]), boi="robot_vpm11")
        db.add(nv)
    for k, v in ghi.items():
        setattr(nv, k, v)
    nv.ghi_nho = ghi["nhom"] in GHI_NHO
    nv.huong = NHOM[ghi["nhom"]][0]
    nv.luc = datetime.now()
    if cham is not None:
        cham.add((ghi["nguon_bang"], ghi["nguon_id"]))
    return nv


def _trang_thai(con_lai: float, ngay: date | None, hom_nay: date, dong: bool = False) -> str:
    if dong or con_lai <= 0:
        return "da_tra"
    if ngay is not None and ngay < hom_nay:
        return "qua_han"
    return "du_kien"


# ══════════════════════════════════════════════════════════════════════════════
# BẢY BỘ NẠP
# ══════════════════════════════════════════════════════════════════════════════

def _nap_de_nghi_chi(db: Session, dem: list[int], hom_nay: date, cham: set) -> int:
    """payment_requests → trả NCC / hoàn khách / vận hành khác.

    NGÀY ĐẾN HẠN lấy từ cột `payment_requests.ngay_den_han` – cửa nhập do VPM-17 dựng, người lập đề
    nghị hoặc Kế toán gõ vào. Gõ rồi thì khoản ấy rời rổ "Chưa đủ dữ liệu dự báo" và xếp vào đúng cột
    của bảng bốn mốc. Cột ấy là NGÀY CAM KẾT: một người đã ký vào nó.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    TC-58 (17/9/2026) · MỐC SUY RA CHO CHỨNG TỪ VIETRIP — VÀ VÌ SAO NÓ KHÔNG PHẢI NGÀY CAM KẾT
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Vietrip KHÔNG có ô ngày đến hạn cho đề nghị chi NCC. 4.815 chứng từ chi chảy từ Vietrip về đều
    mang `ngay_den_han` rỗng, nên trước vòng này toàn bộ khối Phải trả rơi vào ô "Chưa có hạn" và
    bảy ô hạn đứng trống — màn hình Chủ tịch không đọc ra được câu "tuần này phải trả bao nhiêu".

    Anh Tuấn chốt 17/9/2026: "sau khi tour về gọi là quá hạn, và trước khi đi tour cũng theo mốc
    thời gian set của VTOS". Nên mốc suy ra là NGÀY KẾT THÚC TOUR: tour đã về mà chưa trả NCC thì
    đó là quá hạn, đúng chữ anh dùng.

    VÀ NÓ ĐI VÀO `ngay_du_kien_tra`, KHÔNG vào `ngay_cam_ket`. Lý lẽ cũ của tệp này — "không đoán
    một ngày thay người dùng" — vẫn đứng nguyên ở chỗ nó sinh ra để đứng: cột cam kết là nơi ghi
    ngày ĐÃ CÓ NGƯỜI KÝ, và không ai ký ngày kết thúc tour với nhà cung cấp cả. Ghi mốc suy ra vào
    cột ấy là lặng lẽ xoá mất khả năng trả lời "khoản này quá hạn theo cam kết hay theo suy đoán".
    Hai cột tách ra từ đầu chính là để có chỗ cho một mốc như thế này mà không nói dối.

    Chứng từ nào Kế toán đã gõ ngày thật thì ngày gõ THẮNG mốc suy ra, ở cả hai cột.
    """
    n = 0
    tours = {t.id: t for t in db.execute(select(Tour)).scalars()}
    n_suy_ra = 0
    # 29/9/2026: có ảnh phải trả theo dự toán Vietrip thì phần TRẢ NCC lấy từ ảnh ấy
    # (_nap_phai_tra_vietrip); đề nghị chi tour ở đây bỏ qua để một khoản không bị đếm hai lần.
    co_anh_tra = _anh_phai_tra_vietrip_moi_nhat(db) is not None
    for pr in db.execute(select(PaymentRequest).where(
            PaymentRequest.status.in_(PR_CHUA_CHI))).scalars():
        nhom = NHOM_THEO_PR.get(pr.category, "van_hanh_khac")
        if co_anh_tra and nhom == "tra_ncc":
            continue
        tong = float(pr.amount or 0)
        t = tours.get(pr.tour_id) if pr.tour_id else None
        du_kien = pr.ngay_den_han
        ghi_chu = ""
        if du_kien is None and t is not None and t.end_date:
            du_kien = t.end_date
            ghi_chu = ("Mốc SUY RA theo ngày kết thúc tour (chốt 17/9/2026) — Vietrip không có ô "
                       "ngày đến hạn. Kế toán gõ ngày thật vào thì ngày gõ thay mốc này.")
            n_suy_ra += 1
        _dat(db, {
            "nhom": nhom, "nguon_bang": "payment_requests", "nguon_id": pr.id, "nguon_ma": pr.code,
            "company_id": pr.company_id, "tour_id": pr.tour_id,
            "doi_tuong": pr.supplier_name, "noi_dung": pr.description,
            "tong_nghia_vu": tong, "da_tra": None,
            "ngay_cam_ket": pr.ngay_den_han, "ngay_du_kien_tra": du_kien,
            "trang_thai": ("da_duyet" if pr.status in PR_DA_DUYET_CHUA_CHUYEN
                           else _trang_thai(tong, du_kien, hom_nay)),
            "ghi_chu": ghi_chu,
        }, dem, cham)
        n += 1
    return n


def _nap_don_dat_dich_vu(db: Session, dem: list[int], hom_nay: date, cham: set) -> int:
    """service_orders → trả NCC, phần CHƯA lập đề nghị chi.

    Đề xuất mục III.4 đòi đúng chữ: lịch thanh toán NCC "gồm cả nghĩa vụ chưa lập đề nghị chi". Đây
    là bộ nạp trả lời câu đó.

    Ngày lấy từ `service_orders.ngay_den_han` (cửa nhập VPM-17), KHÔNG lấy `ngay_su_dung`: ngày dùng
    dịch vụ là ngày khách lên xe, ngày đến hạn là ngày tiền rời tài khoản – hai ngày có thể cách nhau
    hàng tháng, và lấy nhầm là xếp sai cột.
    """
    n = 0
    ncc = {s.id: s.ten for s in db.execute(select(Supplier)).scalars()}
    for so in db.execute(select(ServiceOrder).where(
            ServiceOrder.status.in_(SO_THANH_NGHIA_VU))).scalars():
        if so.payment_request_id:
            continue          # đã có chứng từ sau, để bộ nạp đề nghị chi lo – xem quy tắc HAI đầu tệp
        _dat(db, {
            "nhom": "tra_ncc", "nguon_bang": "service_orders", "nguon_id": so.id, "nguon_ma": so.code,
            "company_id": None, "tour_id": so.tour_id,
            "doi_tuong": ncc.get(so.supplier_id, ""), "noi_dung": so.noi_dung,
            "tong_nghia_vu": float(so.thanh_tien) if so.thanh_tien is not None else None,
            "da_tra": None,
            "ngay_cam_ket": so.ngay_den_han, "ngay_du_kien_tra": so.ngay_den_han,
            "trang_thai": _trang_thai(float(so.thanh_tien or 0), so.ngay_den_han, hom_nay),
            "ghi_chu": "Nghĩa vụ với nhà cung cấp CHƯA lập đề nghị chi",
        }, dem, cham)
        n += 1
    return n


def _nap_lich_vay(db: Session, dem: list[int], hom_nay: date, cham: set) -> int:
    """fin_schedules → gốc vay / lãi phí / giải ngân. Nguồn DUY NHẤT trong hệ có ngày đến hạn thật sẵn."""
    n = 0
    hd = {c.id: c for c in db.execute(select(FinContract)).scalars()}
    for s in db.execute(select(FinSchedule).where(FinSchedule.status.in_(FS_CON_HAN))).scalars():
        nhom = NHOM_THEO_FS.get(s.kind)
        if nhom is None:
            continue          # giải ngân đầu tư / thu hồi đầu tư: không thuộc dòng nào của bảng dòng tiền
        c = hd.get(s.contract_id)
        tong = float(s.amount or 0)
        _dat(db, {
            "nhom": nhom, "nguon_bang": "fin_schedules", "nguon_id": s.id,
            "nguon_ma": f"{c.code if c else ''}/kỳ {s.ky or '-'}",
            "company_id": c.company_id if c else None, "tour_id": None,
            "doi_tuong": c.partner if c else "", "noi_dung": f"{s.kind} – {c.contract_no if c else ''}",
            "tong_nghia_vu": tong, "da_tra": None,
            "ngay_cam_ket": s.due_date, "ngay_du_kien_tra": s.due_date,
            "trang_thai": _trang_thai(tong, s.due_date, hom_nay),
        }, dem, cham)
        n += 1
    return n


def _nap_lich_thu_hop_dong(db: Session, dem: list[int], hom_nay: date, cham: set) -> set[int]:
    """lich_thanh_toan_hd → thu khách, theo ĐỢT có hạn thật. Trả về tập booking đã có lịch.

    Tập trả về chính là cơ chế chống trùng quy tắc MỘT: bộ nạp booking ở dưới sẽ bỏ qua đúng những
    booking này.
    """
    da_co_lich: set[int] = set()
    hds = {h.id: h for h in db.execute(select(HopDongKhach)).scalars()}
    # Đã thu của cả hợp đồng, phân bổ theo thứ tự đợt: đợt sớm coi như được trả trước. Đây là cách
    # người thu công nợ vẫn làm, và không có cách nào khác vì phiếu thu không ghi nó trả cho đợt nào.
    for hid, hd in hds.items():
        dot = list(db.execute(select(LichThanhToanHD).where(
            LichThanhToanHD.hop_dong_id == hid).order_by(LichThanhToanHD.dot)).scalars())
        if not dot:
            continue
        if hd.booking_id:
            da_co_lich.add(hd.booking_id)
        con_tien_da_thu = float(PAY.paid_amount(db, hd.booking_id) or 0) if hd.booking_id else 0.0
        for d in dot:
            tong = float(d.so_tien) if d.so_tien is not None else None
            gan = min(con_tien_da_thu, tong or 0.0)
            con_tien_da_thu -= gan
            con = max(0.0, (tong or 0.0) - gan)
            _dat(db, {
                "nhom": "thu_khach", "nguon_bang": "lich_thanh_toan_hd", "nguon_id": d.id,
                "nguon_ma": f"{hd.so_hop_dong}/đợt {d.dot}",
                "company_id": hd.company_id, "tour_id": None,
                "doi_tuong": hd.khach_ten, "noi_dung": d.ten or f"Đợt {d.dot}",
                "tong_nghia_vu": tong, "da_tra": gan,
                # Hạn đã báo cho khách là CAM KẾT; hạn gốc giữ riêng ở bảng nguồn để thấy đã dời bao nhiêu.
                "ngay_cam_ket": d.han, "ngay_du_kien_tra": d.han,
                "trang_thai": _trang_thai(con, d.han, hom_nay),
            }, dem, cham)
    return da_co_lich


def _nap_booking(db: Session, dem: list[int], hom_nay: date, bo_qua: set[int], cham: set) -> int:
    """bookings → thu khách, cho booking KHÔNG có lịch hợp đồng. Ngày ước theo D-7 trước khởi hành.

    Ngày ở đây là ƯỚC, không phải cam kết – nên chỉ điền `ngay_du_kien_tra`, để `ngay_cam_ket` rỗng.
    Tab "Nghĩa vụ đến hạn" (dùng ngày cam kết) sẽ không thấy những khoản này, và đúng ra là không nên
    thấy: không ai ký một ngày nào cho chúng cả.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    TC-58 (17/9/2026) · BỎ PHÉP KÉO NGÀY QUÁ KHỨ VỀ HÔM NAY — GHI LẠI CẢ HAI VẾ
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Vế cũ: `uoc = max(hom_nay, khởi_hành − 7)`. Lý lẽ: ngày Kế toán ĐỊNH THU THẬT không thể nằm
    trong quá khứ, nên kéo về hôm nay cho bảng dự báo khỏi có cột âm thời gian.

    Cái giá của phép kéo ấy chỉ lộ ra khi sổ có số thật: một khách đã đi tour tháng 6 mà còn nợ thì
    D-7 của nó là tháng 6, bị kéo về hôm nay, và khoản ấy nằm ở ô "1 tuần" — đọc ra là "sắp tới hạn"
    trong khi sự thật là "đi tour xong hai tháng rồi vẫn chưa trả". Ô "Quá hạn" phía Phải thu vì thế
    KHÔNG BAO GIỜ có số, dù đó là ô cần gọi điện nhất.

    Anh Tuấn 17/9 gửi bản hướng dẫn tự viết, định nghĩa nhóm 1 nguyên văn: "Quá hạn — đã qua hoặc
    hôm nay — Gọi ngay, khách đi tour mà chưa trả đủ". Nên ngày giữ NGUYÊN giá trị thật của nó.

    Bảng dự báo không mất gì: `ba_ro()` đã có sẵn rổ "qua_han" dựng ra đúng để hiện các khoản ngày
    quá khứ RIÊNG mà vẫn cộng vào nhu cầu tiền ("Không tự ẩn" — ghi ở chính hàm ấy). Phép kéo cũ
    thực ra đang VÔ HIỆU HOÁ cái rổ đó.
    """
    anh = _anh_cong_no_vietrip_moi_nhat(db)
    if anh is not None:
        return _nap_tu_anh_vietrip(db, anh, dem, hom_nay, bo_qua, cham)
    n = 0
    tours = {t.id: t for t in db.execute(select(Tour)).scalars()}
    con_thu = (func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0)
               - func.coalesce(Booking.paid, 0))
    for b in db.execute(select(Booking).where(
            Booking.cancelled == False, con_thu > 0)).scalars():          # noqa: E712
        if b.id in bo_qua:
            continue
        t = tours.get(b.tour_id)
        if t is not None and t.status in ("huy", "khoa", "kt_xac_nhan", "da_dong_so"):
            continue
        uoc = (t.start_date - timedelta(days=D_TRUOC_KHOI_HANH)
               if t is not None and t.start_date else None)
        _dat(db, {
            "nhom": "thu_khach", "nguon_bang": "bookings", "nguon_id": b.id, "nguon_ma": b.code,
            "company_id": getattr(b, "company_id", None), "tour_id": b.tour_id,
            "doi_tuong": b.customer_name, "noi_dung": t.name if t else "",
            "tong_nghia_vu": float((b.amount or 0) - (b.discount or 0)), "da_tra": float(b.paid or 0),
            "ngay_cam_ket": None, "ngay_du_kien_tra": uoc,
            # TC-58: trạng thái tính bằng CHÍNH hàm mọi bộ nạp khác dùng, thay cho chuỗi "du_kien"
            # gõ cứng. Gõ cứng nghĩa là một khoản khách đã đi tour từ tháng 6 mà chưa trả vẫn mang
            # nhãn "Dự kiến" suốt đời — và nhãn ấy là thứ người đọc tin trước cả con số.
            "trang_thai": _trang_thai(
                float((b.amount or 0) - (b.discount or 0) - (b.paid or 0)), uoc, hom_nay),
            "ghi_chu": "Ngày là ƯỚC theo D-7 trước khởi hành, chưa có lịch thu ký với khách",
        }, dem, cham)
        n += 1
    return n


# ══════════════════════════════════════════════════════════════════════════════
# 28/9/2026 · PHẢI THU LẤY ĐÚNG THEO VIETRIP
# ══════════════════════════════════════════════════════════════════════════════
# Anh Tuấn: "lấy đúng theo Vietrip · sửa lại VTOS cho khớp với Vietrip".
#
# Đo ngày 28/9: khối Phải thu dựng từ bảng `bookings` ra ~18 tỷ, còn báo cáo công nợ Vietrip cùng
# ngày là 7,6 tỷ. Lệch vì `bookings.paid` chỉ cộng những phiếu thu đã đồng bộ về (phiếu trước
# 01/6/2026 và phiếu chưa ánh xạ được thì thiếu), nên booking khách đã trả đủ vẫn hiện còn nợ;
# thêm vào đó báo cáo đã loại các booking trừ lương sale / khuyến mãi / booking test.
#
# Nên khi đã có ẢNH CÔNG NỢ VIETRIP (POST /api/v1/cong-no-vietrip/nap, nạp mỗi sáng 8h), phía THU
# KHÁCH đọc thẳng ảnh mới nhất: Tổng = totalOrderValue, Đã thu = totalPaidAmount của chính Vietrip,
# đã qua danh sách loại trừ; bảo lưu không tính nợ. Chưa có ảnh nào thì giữ đường cũ từ `bookings`.
#
# Khoá dòng: booking có trong VTOS thì dùng ("bookings", booking.id) — mã gốc giữ nguyên với sổ
# đã dựng; booking chưa về VTOS thì ("cong_no_vietrip", recID Vietrip).
# Ngày hạn vẫn là D-7 trước khởi hành như mọi khoản thu khách khác.
def _anh_cong_no_vietrip_moi_nhat(db: Session):
    from sqlalchemy import inspect
    from app.models.cong_no_vietrip import CongNoVietripAnh
    # Bảng chưa có (kho chưa chạy migration) thì đi đường cũ. Hỏi trước chứ không bắt lỗi rồi
    # rollback: rollback giữa phép dựng sổ là xoá mất các dòng vừa ghi của những bộ nạp trước.
    if not inspect(db.connection()).has_table(CongNoVietripAnh.__tablename__):
        return None
    return db.execute(select(CongNoVietripAnh).order_by(CongNoVietripAnh.ngay.desc())
                      .limit(1)).scalars().first()


def _nap_tu_anh_vietrip(db: Session, anh, dem: list[int], hom_nay: date, bo_qua: set[int],
                        cham: set) -> int:
    from app.models.cong_no_vietrip import CongNoVietripDong
    theo_vt = {b.vietrip_id: b for b in db.execute(
        select(Booking).where(Booking.vietrip_id.is_not(None))).scalars()}
    n = 0
    for d in db.execute(select(CongNoVietripDong).where(
            CongNoVietripDong.anh_id == anh.id, CongNoVietripDong.bao_luu == False)).scalars():  # noqa: E712
        tong, da = float(d.tong or 0), float(d.da_thu or 0)
        if tong - da <= 0:
            continue
        try:
            vt_id = int(str(d.booking_id).strip())
        except ValueError:
            continue
        b = theo_vt.get(vt_id)
        if b is not None and b.id in bo_qua:
            continue
        uoc = d.khoi_hanh - timedelta(days=D_TRUOC_KHOI_HANH) if d.khoi_hanh else None
        _dat(db, {
            "nhom": "thu_khach",
            "nguon_bang": "bookings" if b is not None else "cong_no_vietrip",
            "nguon_id": b.id if b is not None else vt_id,
            "nguon_ma": b.code if b is not None else f"VT{vt_id}",
            "company_id": getattr(b, "company_id", None) if b is not None else None,
            "tour_id": b.tour_id if b is not None else None,
            "doi_tuong": d.khach or (b.customer_name if b is not None else ""),
            "noi_dung": d.ten_tour or d.ma_tour or "",
            "tong_nghia_vu": tong, "da_tra": da,
            "ngay_cam_ket": None, "ngay_du_kien_tra": uoc,
            "trang_thai": _trang_thai(tong - da, uoc, hom_nay),
            "ghi_chu": (f"Theo công nợ Vietrip ngày {anh.ngay:%d/%m/%Y}; ngày là ƯỚC D-7 trước khởi hành"
                        + (f" · {d.ghi_chu}" if d.ghi_chu else "")),
        }, dem, cham)
        n += 1
    return n


# ══════════════════════════════════════════════════════════════════════════════
# 29/9/2026 · PHẢI TRẢ NCC LẤY ĐÚNG THEO DỰ TOÁN TOUR TRÊN VIETRIP
# ══════════════════════════════════════════════════════════════════════════════
# Anh Tuấn: "dựa vào dự toán tour để xác định số phải trả và sửa lại VTOS đúng theo Vietrip".
# Mỗi tour một dòng nhóm `tra_ncc`: Tổng = Tổng chi dự toán, Đã trả = Thực tế đã chi (Quyết toán
# tour → Thống kê thu chi). Hạn = ngày kết thúc tour — chốt 17/9: "sau khi tour về gọi là quá hạn".
# Chưa có ảnh nào thì giữ đường cũ từ đề nghị chi.
def _anh_phai_tra_vietrip_moi_nhat(db: Session):
    from sqlalchemy import inspect
    from app.models.cong_no_vietrip import PhaiTraVietripAnh
    if not inspect(db.connection()).has_table(PhaiTraVietripAnh.__tablename__):
        return None
    return db.execute(select(PhaiTraVietripAnh).order_by(PhaiTraVietripAnh.ngay.desc())
                      .limit(1)).scalars().first()


def _nap_phai_tra_vietrip(db: Session, dem: list[int], hom_nay: date, cham: set) -> int:
    anh = _anh_phai_tra_vietrip_moi_nhat(db)
    if anh is None:
        return 0
    from app.models.cong_no_vietrip import PhaiTraVietripDong
    theo_ma = {t.code: t for t in db.execute(select(Tour)).scalars()}
    n = 0
    for d in db.execute(select(PhaiTraVietripDong).where(PhaiTraVietripDong.anh_id == anh.id)).scalars():
        tong, da = float(d.tong_chi or 0), float(d.da_chi or 0)
        if tong - da <= 0:
            continue
        t = theo_ma.get(d.ma_tour or "")
        han = d.ket_thuc or d.khoi_hanh
        _dat(db, {
            "nhom": "tra_ncc", "nguon_bang": "phai_tra_vietrip", "nguon_id": int(d.tour_id),
            "nguon_ma": d.ma_tour, "company_id": t.company_id if t is not None else None,
            "tour_id": t.id if t is not None else None,
            "doi_tuong": f"NCC tour {d.ma_tour}", "noi_dung": d.ten_tour or d.ma_tour or "",
            "tong_nghia_vu": tong, "da_tra": da,
            "ngay_cam_ket": None, "ngay_du_kien_tra": han,
            "trang_thai": _trang_thai(tong - da, han, hom_nay),
            "ghi_chu": f"Theo dự toán tour Vietrip ngày {anh.ngay:%d/%m/%Y}; hạn = ngày kết thúc tour",
        }, dem, cham)
        n += 1
    return n


def _nap_ke_hoach_tien(db: Session, dem: list[int], hom_nay: date, cham: set) -> int:
    """cash_plan_items → lương / thuế / vận hành khác. Kế toán nhập tay, có ngày đến hạn thật.

    Dòng lặp hằng tháng: bảng nguồn chỉ giữ MỘT dòng và một cờ lặp. Sổ nghĩa vụ phải trải nó ra thành
    từng kỳ – nhưng khoá duy nhất là (nguồn bảng, nguồn id), một dòng nguồn chỉ sinh được một dòng sổ.
    Nên ở đợt này chỉ lấy KỲ SẮP TỚI, và ghi rõ trong ghi chú. Trải nhiều kỳ cần một khoá nguồn có
    thêm phần kỳ – việc của VPM-17 khi dựng màn hình lịch nghĩa vụ thật, không vá tạm ở đây.
    """
    n = 0
    for it in db.execute(select(CashPlanItem)).scalars():
        if it.due_date < hom_nay and not it.recurring_monthly:
            continue
        nhom = NHOM_THEO_CASHPLAN.get(it.category, "van_hanh_khac")
        if it.direction == "in":
            nhom = "thu_cong_no_khac"
        _dat(db, {
            "nhom": nhom, "nguon_bang": "cash_plan_items", "nguon_id": it.id, "nguon_ma": "",
            "company_id": getattr(it, "company_id", None), "tour_id": None,
            "doi_tuong": "", "noi_dung": it.description,
            "tong_nghia_vu": float(it.amount or 0), "da_tra": None,
            "ngay_cam_ket": it.due_date, "ngay_du_kien_tra": it.due_date,
            "trang_thai": _trang_thai(float(it.amount or 0), it.due_date, hom_nay),
            "ghi_chu": "Kỳ gần nhất; dòng lặp hằng tháng chưa trải nhiều kỳ (VPM-17)"
                       if it.recurring_monthly else "",
        }, dem, cham)
        n += 1
    return n


def _danh_dau_nghi_trung(db: Session) -> int:
    """Dò các cặp NGHI trùng và đánh dấu. KHÔNG gộp, KHÔNG trừ – xem quy tắc BA đầu tệp.

    Dấu hiệu: cùng tour, cùng đối tượng, cùng số tiền, khác bảng nguồn. Ba điều kiện trùng một lúc thì
    xác suất là hai chứng từ của một nghĩa vụ đủ cao để BÁO, và vẫn thấp hơn mức đủ để TỰ GỘP.
    """
    db.flush()
    theo_khoa: dict[tuple, list[NghiaVuThanhToan]] = {}
    for nv in db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.huong == "chi",
            NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG))).scalars():
        if nv.tour_id is None or nv.tong_nghia_vu is None:
            continue
        theo_khoa.setdefault((nv.tour_id, nv.doi_tuong.strip().lower(),
                              round(float(nv.tong_nghia_vu or 0), 2)), []).append(nv)
    n = 0
    for nhom_nv in theo_khoa.values():
        if len(nhom_nv) < 2 or len({x.nguon_bang for x in nhom_nv}) < 2:
            continue
        for nv in nhom_nv:
            khac = [x.ma_goc for x in nhom_nv if x.id != nv.id or x is not nv]
            nv.nghi_trung_voi = ",".join(sorted(set(khac))[:3])
            n += 1
    return n


def _thu_hoi_dong_khong_con_can_cu(db: Session, da_cham: set[tuple[str, int]]) -> int:
    """Đóng những dòng mà lần chạy này KHÔNG còn dựng lại được. Nửa sau của tính chạy-lại-được.

    Nạp lại thôi chưa đủ. Một chứng từ hôm qua còn là nghĩa vụ, hôm nay thì không – đề nghị chi đã
    chuyển tiền, đơn dịch vụ bị huỷ, hoặc booking vừa được nối vào một hợp đồng có lịch thu nên phần
    thu của nó chuyển sang các đợt của lịch. Dòng cũ nằm lại trong sổ là một khoản tiền KHÔNG CÒN CĂN
    CỨ NÀO, và nó cộng vào bảng dòng tiền y như một khoản thật. Phép thử b6 bắt được đúng chỗ này.

    ĐÓNG chứ không XOÁ: mã gốc là danh tính, người ta đã gọi nhau qua nó; xoá đi thì một mã từng có
    thật biến mất không dấu vết. Dòng đóng không được cộng (`TRANG_THAI_DONG`), và nếu chứng từ gốc
    trở lại đủ điều kiện thì lần đồng bộ sau mở nó ra lại, giữ nguyên mã cũ.

    Chỉ quét sáu bảng nguồn của phép đồng bộ. Dòng do người hoặc phân hệ khác tạo không bị chạm tới.
    """
    n = 0
    for nv in db.execute(select(NghiaVuThanhToan).where(
            NghiaVuThanhToan.nguon_bang.in_(NGUON_DONG_BO),
            NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG))).scalars():
        if (nv.nguon_bang, nv.nguon_id) in da_cham:
            continue
        nv.trang_thai = "huy"
        nv.ghi_chu = ("Chứng từ gốc không còn là nghĩa vụ khi đồng bộ ngày "
                      f"{date.today():%d/%m/%Y} – đã chi xong, bị huỷ, hoặc chuyển sang chứng từ khác")
        n += 1
    return n


def dong_bo(db: Session, hom_nay: date | None = None) -> dict:
    """Dựng lại sổ nghĩa vụ từ sáu nguồn. CHẠY LẠI ĐƯỢC – gọi bao nhiêu lần cũng ra cùng một sổ."""
    hom_nay = hom_nay or date.today()
    dem = [int(db.execute(select(func.count()).select_from(NghiaVuThanhToan)).scalar() or 0)]
    cham: set[tuple[str, int]] = set()

    da_co_lich = _nap_lich_thu_hop_dong(db, dem, hom_nay, cham)
    ra = {
        "lich_thanh_toan_hd": len([k for k in cham if k[0] == "lich_thanh_toan_hd"]),
        "bookings": _nap_booking(db, dem, hom_nay, da_co_lich, cham),
        "payment_requests": _nap_de_nghi_chi(db, dem, hom_nay, cham),
        "phai_tra_vietrip": _nap_phai_tra_vietrip(db, dem, hom_nay, cham),
        "service_orders": _nap_don_dat_dich_vu(db, dem, hom_nay, cham),
        "fin_schedules": _nap_lich_vay(db, dem, hom_nay, cham),
        "cash_plan_items": _nap_ke_hoach_tien(db, dem, hom_nay, cham),
    }
    ra["da_dong"] = _thu_hoi_dong_khong_con_can_cu(db, cham)
    ra["nghi_trung"] = _danh_dau_nghi_trung(db)
    db.flush()
    ra["tong_dong"] = int(db.execute(select(func.count()).select_from(NghiaVuThanhToan)).scalar() or 0)
    return ra


# ══════════════════════════════════════════════════════════════════════════════
# ĐỌC SỔ – phép cộng mà bảng dòng tiền (VPM-13) sẽ gọi
# ══════════════════════════════════════════════════════════════════════════════

def _loc(q, company_id: int | None, loai_tien: str, vai_tro: str | None = None):
    """Ba hàng rào đi cùng nhau, và cái thứ ba KHÔNG được quên ở bất kỳ cửa nào.

    `vai_tro` rỗng nghĩa là người gọi ở trong máy chủ, không phải một phiên đăng nhập (phép đồng bộ,
    phép thử, robot). Rỗng thì KHÔNG lọc theo nhóm – nhưng mọi cửa API đều phải truyền vai trò vào,
    và phép thử e5/e6 canh đúng chỗ ấy.
    """
    if company_id is not None:
        q = q.where(NghiaVuThanhToan.company_id == company_id)
    if vai_tro is not None:
        q = q.where(NghiaVuThanhToan.nhom.in_(sorted(nhom_duoc_xem(vai_tro))))
    return q.where(NghiaVuThanhToan.loai_tien == loai_tien)


def cot_ngay(co_so_ngay: str):
    """Cột ngày ứng với một cơ sở. BA cơ sở, và cái thứ ba là của TC-58.

      · "cam_ket"  – ngày đã có người ký. Tab Nghĩa vụ đến hạn.
      · "du_kien"  – ngày kế toán định trả thật. Tab Kế hoạch thực thu–chi.
      · "han"      – cam kết NẾU CÓ, không thì dự kiến. Khối Phải thu · Phải trả của màn hình 01.

    Vì sao cơ sở thứ ba tồn tại: hai khối công nợ trên màn hình Chủ tịch hỏi một câu khác hai tab
    kia. Chúng không hỏi "ai đã ký ngày nào" mà hỏi "tiền này tới hạn lúc nào, theo chỗ tốt nhất
    mình biết". Ép chúng dùng riêng cột cam kết thì 12.198 phiếu đặt Vietrip và 4.815 chứng từ chi
    — không cái nào có ngày ký — dồn hết vào một ô "Chưa có hạn", và bảy ô hạn đứng trống trong khi
    hệ thống THỪA BIẾT tour nào đi ngày nào.

    Cái phải giữ là không để cơ sở này lẫn sang hai tab kia: trộn vào tab cam kết là xoá mất câu
    "quá hạn theo cam kết", đúng điều mục IV.4 của đề xuất cấm. Nên đây là một cơ sở THỨ BA, gọi
    tên riêng, chứ không phải nới lỏng cơ sở cũ.
    """
    if co_so_ngay == "cam_ket":
        return NghiaVuThanhToan.ngay_cam_ket
    if co_so_ngay == "han":
        return func.coalesce(NghiaVuThanhToan.ngay_cam_ket, NghiaVuThanhToan.ngay_du_kien_tra)
    return NghiaVuThanhToan.ngay_du_kien_tra


def cong(db: Session, tu: date, den: date, *, co_so_ngay: str = "cam_ket",
         company_id: int | None = None, loai_tien: str = "VND",
         vai_tro: str | None = None) -> dict:
    """Cộng phần CÒN LẠI theo nhóm, trong khoảng [tu, den] BAO GỒM CẢ HAI ĐẦU.

    `co_so_ngay`: "cam_ket" cho tab Nghĩa vụ đến hạn, "du_kien" cho tab Kế hoạch thực thu–chi, "han"
    cho hai khối công nợ của màn hình 01 — xem `cot_ngay()`. Ba cơ sở KHÔNG được trộn; đó là lý do
    tham số này bắt buộc phải chọn, không có giá trị "cả ba".

    Mỗi nghĩa vụ là MỘT DÒNG nên phép cộng này không thể đếm trùng: không có chỗ nào để một khoản tiền
    xuất hiện hai lần. Đó là toàn bộ lý do bảng nghĩa vụ tồn tại.
    """
    cot = cot_ngay(co_so_ngay)
    q = _loc(select(NghiaVuThanhToan).where(
        NghiaVuThanhToan.ghi_nho == False,                                  # noqa: E712
        NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG),
        cot.is_not(None), cot >= tu, cot <= den), company_id, loai_tien, vai_tro)
    theo_nhom: dict[str, float] = {}
    for nv in db.execute(q).scalars():
        con = nv.con_lai()
        if con <= 0:
            continue
        theo_nhom[nv.nhom] = theo_nhom.get(nv.nhom, 0.0) + con
    # Làm tròn MỘT LẦN ở đầu ra, sau khi đã cộng xong – không làm tròn từng dòng rồi mới cộng.
    return {k: round(v) for k, v in sorted(theo_nhom.items())}


def ba_ro(db: Session, den: date, *, co_so_ngay: str = "cam_ket",
          company_id: int | None = None, loai_tien: str = "VND",
          hom_nay: date | None = None, vai_tro: str | None = None) -> dict:
    """Ba rổ KHÔNG ĐƯỢC bỏ im lặng (CF-05 và mục IV.2 của đề xuất).

    Hàm dự báo cũ (`finance.forecast_13w`) bỏ lặng cả ba: khoản quá hạn lẫn vào số chung, khoản không
    có ngày đến hạn không bao giờ đi qua `put()`, khoản ngoài tầm nhìn bị `return` sớm. Bảng dòng tiền
    vì thế trông gọn hơn sự thật. Hàm này trả cả ba ra để màn hình BUỘC phải hiển thị chúng.
    """
    hom_nay = hom_nay or date.today()
    cot = cot_ngay(co_so_ngay)
    nen = _loc(select(NghiaVuThanhToan).where(
        NghiaVuThanhToan.ghi_nho == False,                                  # noqa: E712
        NghiaVuThanhToan.trang_thai.not_in(TRANG_THAI_DONG)), company_id, loai_tien, vai_tro)

    def gom(q) -> dict:
        ds = [nv for nv in db.execute(q).scalars() if nv.con_lai() > 0]
        return {"so_khoan": len(ds), "tong": round(sum(nv.con_lai() for nv in ds)),
                "chi_tiet": [dong(nv) for nv in sorted(ds, key=lambda x: -x.con_lai())[:200]]}

    return {
        # Quá hạn: hiện RIÊNG, nhưng VẪN tính vào nhu cầu thanh toán (mục III.2). Không tự ẩn.
        "qua_han": gom(nen.where(cot.is_not(None), cot < hom_nay)),
        # Không có ngày: danh sách "Chưa đủ dữ liệu dự báo". Đây là danh sách ép người đi nhập ngày.
        "chua_du_du_lieu": gom(nen.where(cot.is_(None))),
        # Ngoài tầm nhìn: đếm và nêu tổng, không im lặng.
        "ngoai_tam_nhin": gom(nen.where(cot.is_not(None), cot > den)),
    }


def dong(nv: NghiaVuThanhToan) -> dict:
    """Một dòng cho màn hình chi tiết (mục IV.2 của đề xuất – đủ 11 cột nó liệt kê)."""
    return {
        "ma_goc": nv.ma_goc, "nhom": nv.nhom, "nhom_ten": NHOM[nv.nhom][1], "huong": nv.huong,
        "doi_tuong": nv.doi_tuong, "noi_dung": nv.noi_dung, "tour_id": nv.tour_id,
        "tong_nghia_vu": nv.tong_nghia_vu, "da_tra": nv.da_tra, "con_lai": nv.con_lai(),
        "ngay_cam_ket": nv.ngay_cam_ket, "ngay_du_kien_tra": nv.ngay_du_kien_tra,
        "trang_thai": nv.trang_thai, "company_id": nv.company_id,
        "loai_tien": nv.loai_tien, "ty_gia": nv.ty_gia,
        "chung_tu_nguon": {"bang": nv.nguon_bang, "id": nv.nguon_id, "ma": nv.nguon_ma},
        "nghi_trung_voi": nv.nghi_trung_voi, "ghi_chu": nv.ghi_chu,
        "phien_ban": nv.phien_ban,
    }


def bang(db: Session, *, company_id: int | None = None, loai_tien: str = "VND",
         hom_nay: date | None = None, vai_tro: str | None = None) -> dict:
    """Tổng hợp sổ – cửa đọc cho màn hình và cho VPM-13."""
    hom_nay = hom_nay or date.today()
    cuoi = date(hom_nay.year + (hom_nay.month == 12), hom_nay.month % 12 + 1, 1) - timedelta(days=1)
    return {
        "hom_nay": hom_nay,
        "den_ngay": cuoi,
        "cam_ket": cong(db, hom_nay, cuoi, co_so_ngay="cam_ket",
                        company_id=company_id, loai_tien=loai_tien, vai_tro=vai_tro),
        "du_kien": cong(db, hom_nay, cuoi, co_so_ngay="du_kien",
                        company_id=company_id, loai_tien=loai_tien, vai_tro=vai_tro),
        "ba_ro": ba_ro(db, cuoi, company_id=company_id, loai_tien=loai_tien, hom_nay=hom_nay,
                       vai_tro=vai_tro),
        # Nói thẳng ra cho màn hình: người này KHÔNG thấy những nhóm nào, và vì sao. Một bảng thiếu
        # dòng mà không giải thích thì người đọc tưởng công ty không có khoản ấy.
        "nhom_ngoai_tam": ([{"nhom": k, "ten": NHOM[k][1], "ly_do": v}
                            for k, v in sorted(NGOAI_TAM.items())
                            if vai_tro is not None and k not in nhom_duoc_xem(vai_tro)]),
    }


def _nghia_vu_thieu_ngay(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot Kiểm soát: nghĩa vụ chưa có ngày đến hạn là việc CÒN THIẾU."""
    ro = ba_ro(db, date.today())["chua_du_du_lieu"]
    return [{"ma": f"nghia_vu_thieu_ngay#{d['ma_goc']}", "loai": "nghia_vu_thieu_ngay", "muc": "vang",
             "phong_ban": "Kế toán", "vai_tro": "ketoan", "doi_tuong": d["ma_goc"],
             "tom_tat": f"Nghĩa vụ {d['ma_goc']} ({NHOM[d['nhom']][1]}, {d['doi_tuong']}) còn "
                        f"{d['con_lai']:,.0f} đ nhưng CHƯA CÓ NGÀY ĐẾN HẠN – không xếp được vào cột "
                        f"nào của bảng dòng tiền, đang nằm ở rổ Chưa đủ dữ liệu dự báo",
             "chi_tiet": {"ma_goc": d["ma_goc"], "chung_tu": d["chung_tu_nguon"]}}
            for d in ro["chi_tiet"]]
