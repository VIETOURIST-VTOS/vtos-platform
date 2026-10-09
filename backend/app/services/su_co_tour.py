"""Sự cố tour – luật nghiệp vụ (V7 Đợt 3, 10/9/2026).

Bốn chốt chặn của tệp này, viết ra để lần sau không ai gỡ nhầm:

1. KHÔNG có ô số tiền. Hồ sơ chỉ gắn SỐ HIỆU Đề nghị chi; số tiền thật nằm ở chứng từ đó và đi đúng cấp
   duyệt theo ngưỡng. Xem thêm ghi chú đầu app/models/su_co_tour.py.
2. Hạn xử lý lấy từ THAM SỐ CHÍNH SÁCH theo mức, không viết cứng, và mức càng nặng hạn càng NGẮN.
3. Đóng hồ sơ phải có nguyên nhân và kết quả. Không cho đóng một sự cố mà không ai biết vì sao nó xảy
   ra – đóng kiểu đó thì cuối quý bảng thống kê nguyên nhân rỗng, và không rút được kinh nghiệm gì.
4. Quy lỗi cho NGƯỜI thì phải lập Sự vụ (bảng incidents) – ở đây chỉ giữ số hiệu. Chế tài, thời hiệu và
   quyền khiếu nại của người bị lập biên bản nằm ở phân hệ Nhân sự, không nhân bản sang đây.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.core import User, Tour, Booking, Alert
from app.models.ops import PaymentRequest
from app.models.cskh import Complaint
from app.models.hr import Incident
from app.models.suppliers import Supplier
from app.models.su_co_tour import (SuCoTour, SuCoTourXuLy, SC_NHOM, SC_MUC, SC_TRANG_THAI, SC_CHUYEN,
                                   SC_NGUYEN_NHAN, SC_HAN_THAM_SO, SC_HAN_MAC_DINH)
from app.services import rules as R

# Ai GHI được. Điều hành là chủ nhà; Kinh doanh có mặt vì sale thường là người khách gọi đầu tiên khi
# chuyến trục trặc, và bắt họ chuyển lời qua Điều hành rồi mới ghi được là mất mười lăm phút đầu tiên –
# đúng mười lăm phút quyết định.
GHI = ("tp_dh", "nv_dh", "ptgd_doan", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "tp_hd", "gd_doi_xe",
       "tgd", "chutich", "cntt")
# Ai ĐÓNG được. Hẹp hơn hẳn: đóng hồ sơ là kết luận nguyên nhân, và kết luận "do nhà cung cấp" kéo theo
# việc đòi bồi hoàn, "do ta" kéo theo Sự vụ. Không để người vừa gây ra sự cố tự kết luận về nó.
DONG = ("tp_dh", "ptgd_doan", "tgd", "chutich")


def next_code(db: Session) -> str:
    # Số lấy theo SỐ LỚN NHẤT đã cấp cho đúng tiền tố này, không phải số dòng cả bảng —
    # xem `services/ma_tu_sinh.py` cho ba chỗ hỏng của lối đếm cũ.
    from app.services.ma_tu_sinh import tiep_theo
    return tiep_theo(db, SuCoTour, f"SC{date.today():%y%m}-", 3)


def han_theo_muc(db: Session, muc: int, tu: datetime | None = None) -> datetime:
    """Hạn xử lý. Mức 3 gấp nhất, nên số giờ NHỎ nhất – xem SC_HAN_MAC_DINH."""
    mac_dinh = SC_HAN_MAC_DINH.get(muc, 24.0)
    try:
        gio = float(R.get_param(db, SC_HAN_THAM_SO.get(muc, "sc_han_muc1_gio")))
    except (KeyError, TypeError, ValueError):
        gio = mac_dinh
    return (tu or datetime.now()) + timedelta(hours=gio or mac_dinh)


def kiem_du_lieu(db: Session, d: dict) -> None:
    if d.get("nhom") not in SC_NHOM:
        raise ValueError(f"Nhóm sự cố không hợp lệ. Chỉ nhận: {', '.join(SC_NHOM)}")
    if int(d.get("muc") or 0) not in SC_MUC:
        raise ValueError("Mức sự cố phải là 1, 2 hoặc 3")
    if not d.get("tour_id"):
        raise ValueError("Phải chọn chuyến tour – sự cố không gắn chuyến thì không quy được về nhà cung "
                         "cấp nào và không vào được quyết toán chuyến nào")
    if not db.get(Tour, d["tour_id"]):
        raise ValueError("Không có chuyến tour này")
    if d.get("booking_id") and not db.get(Booking, d["booking_id"]):
        raise ValueError("Không có booking này")
    if d.get("supplier_id") and not db.get(Supplier, d["supplier_id"]):
        raise ValueError("Không có nhà cung cấp này")
    if not (d.get("mo_ta") or "").strip():
        raise ValueError("Phải ghi nguyên văn lời người báo – tóm tắt lại theo ý mình là mất chứng cứ")
    if int(d.get("so_khach_anh_huong") or 0) < 0:
        raise ValueError("Số khách ảnh hưởng không âm được")


def tao(db: Session, u: User, data: dict) -> SuCoTour:
    kiem_du_lieu(db, data)
    muc = int(data.get("muc") or 1)
    xr = data.get("xay_ra_luc") or datetime.now()
    if isinstance(xr, str):
        xr = datetime.fromisoformat(xr)
    # Hạn tính từ LÚC XẢY RA chứ không từ lúc ghi vào hệ thống. Tính từ lúc ghi thì báo muộn ba tiếng
    # là tự dời hạn thêm ba tiếng – đúng chiều khuyến khích ngược.
    sc = SuCoTour(
        code=next_code(db), tour_id=int(data["tour_id"]),
        booking_id=int(data["booking_id"]) if data.get("booking_id") else None,
        nhom=data["nhom"], muc=muc, xay_ra_luc=xr,
        noi_xay_ra=(data.get("noi_xay_ra") or "").strip(),
        so_khach_anh_huong=int(data.get("so_khach_anh_huong") or 0),
        mo_ta=data["mo_ta"].strip(), nguoi_bao=(data.get("nguoi_bao") or "").strip(),
        nguoi_bao_id=int(data["nguoi_bao_id"]) if data.get("nguoi_bao_id") else None,
        supplier_id=int(data["supplier_id"]) if data.get("supplier_id") else None,
        trang_thai="moi", han_xu_ly=han_theo_muc(db, muc, xr),
        company_id=data.get("company_id"), created_by=u.username)
    db.add(sc)
    db.flush()
    R.audit(db, u.username, u.role, "tao_su_co_tour", f"su_co_tour:{sc.code}",
            after={"tour_id": sc.tour_id, "nhom": sc.nhom, "muc": sc.muc})
    # Mức 3 báo ngay cho Ban TGĐ. Không chờ ai mở màn hình: khách mất chuyến hoặc phải đi cấp cứu thì
    # người quyết định phải biết trong vài phút, không phải sáng hôm sau.
    if muc == 3:
        db.add(Alert(kind="su_co_tour_muc3", level="red", ref=sc.code,
                     message=f"Sự cố mức 3 chuyến {db.get(Tour, sc.tour_id).code}: {sc.mo_ta[:120]}",
                     to_roles=",".join(("tgd", "chutich", "ptgd_doan", "tp_dh"))))
    return sc


def them_xu_ly(db: Session, u: User, sc: SuCoTour, noi_dung: str, luc: datetime | None = None) -> SuCoTourXuLy:
    if not (noi_dung or "").strip():
        raise ValueError("Phải ghi đã làm gì – một dòng trống trong nhật ký xử lý không nói được gì")
    if sc.trang_thai == "dong":
        raise ValueError("Hồ sơ đã đóng. Có tình tiết mới thì mở lại hồ sơ trước, đừng ghi thêm vào hồ "
                         "sơ đã kết luận")
    d = SuCoTourXuLy(su_co_id=sc.id, luc=luc or datetime.now(), nguoi=u.username,
                     noi_dung=noi_dung.strip())
    db.add(d)
    # Dòng xử lý ĐẦU TIÊN chính là lúc có người nhận việc. Suy ra từ dữ liệu đã có thay vì bắt người
    # dùng bấm thêm một nút "nhận việc" mà ai cũng quên bấm.
    if not sc.nhan_luc:
        sc.nhan_luc = d.luc
        sc.nguoi_xu_ly = u.username
    if sc.trang_thai == "moi":
        sc.trang_thai = "dang_xu_ly"
    db.flush()
    R.audit(db, u.username, u.role, "xu_ly_su_co_tour", f"su_co_tour:{sc.code}",
            after={"noi_dung": d.noi_dung[:200]})
    return d


def chuyen_trang_thai(db: Session, u: User, sc: SuCoTour, moi: str) -> SuCoTour:
    if moi not in SC_TRANG_THAI:
        raise ValueError("Trạng thái không hợp lệ")
    if moi not in SC_CHUYEN.get(sc.trang_thai, ()):
        raise ValueError(f"Không chuyển từ '{SC_TRANG_THAI[sc.trang_thai]}' sang '{SC_TRANG_THAI[moi]}' được")
    if moi == "dong":
        raise ValueError("Đóng hồ sơ đi qua đường riêng vì phải có nguyên nhân và kết quả")
    cu = sc.trang_thai
    sc.trang_thai = moi
    if moi == "dang_xu_ly" and not sc.nhan_luc:
        sc.nhan_luc, sc.nguoi_xu_ly = datetime.now(), u.username
    db.flush()
    R.audit(db, u.username, u.role, "chuyen_su_co_tour", f"su_co_tour:{sc.code}",
            before={"trang_thai": cu}, after={"trang_thai": moi})
    return sc


def _kiem_chung_tu(db: Session, pr_id: int | None) -> None:
    if not pr_id:
        return
    pr = db.get(PaymentRequest, pr_id)
    if not pr:
        raise ValueError("Không có đề nghị chi này")
    # Chi phí sự cố là chi phí CỦA CHUYẾN, nên phải là đề nghị chi nhóm chi_tour. Gắn một khoản chi
    # hành chính vào đây là làm giá vốn chuyến sai mà không ai thấy.
    if pr.category != "chi_tour":
        raise ValueError("Chứng từ chi phí sự cố phải là Đề nghị chi nhóm 'Chi phí tour' – khoản chi "
                         "khác nhóm không vào giá vốn chuyến")


def dong(db: Session, u: User, sc: SuCoTour, data: dict) -> SuCoTour:
    """Kết luận và đóng hồ sơ.

    Đòi ba thứ: nguyên nhân nhóm, nguyên nhân viết ra, và kết quả xử lý. Ba câu hỏi này là toàn bộ giá
    trị của việc ghi sự cố – bỏ qua chúng thì bảng sự cố chỉ còn là một danh sách chuyện đã xảy ra.
    """
    if sc.trang_thai == "dong":
        raise ValueError("Hồ sơ đã đóng")
    if sc.trang_thai not in ("da_xu_ly", "dang_xu_ly"):
        raise ValueError("Phải xử lý xong rồi mới đóng được hồ sơ")
    nn = (data.get("nguyen_nhan_nhom") or "").strip()
    if nn not in SC_NGUYEN_NHAN:
        raise ValueError(f"Phải chọn nhóm nguyên nhân. Chỉ nhận: {', '.join(SC_NGUYEN_NHAN)}")
    if len((data.get("nguyen_nhan") or "").strip()) < 20:
        raise ValueError("Phải viết nguyên nhân rõ ràng (ít nhất 20 ký tự) – 'do khách quan' không phải "
                         "là một nguyên nhân, và cuối quý nó không rút ra được bài học nào")
    if not (data.get("ket_qua") or "").strip():
        raise ValueError("Phải ghi kết quả xử lý cuối cùng cho khách")
    _kiem_chung_tu(db, data.get("payment_request_id"))
    # Kết luận "do ta" mà không lập Sự vụ thì phải nói rõ vì sao. Không chặn cứng: phần lớn lỗi của ta
    # là lỗi quy trình chứ không phải lỗi một người, mà Sự vụ là hồ sơ kỷ luật CỦA MỘT NGƯỜI.
    if data.get("incident_id") and not db.get(Incident, data["incident_id"]):
        raise ValueError("Không có sự vụ này")
    if data.get("complaint_id") and not db.get(Complaint, data["complaint_id"]):
        raise ValueError("Không có hồ sơ khiếu nại này")

    truoc = {"trang_thai": sc.trang_thai}
    sc.nguyen_nhan_nhom = nn
    sc.nguyen_nhan = data["nguyen_nhan"].strip()
    sc.ket_qua = data["ket_qua"].strip()
    sc.huong_xu_ly = (data.get("huong_xu_ly") or sc.huong_xu_ly or "").strip()
    sc.payment_request_id = data.get("payment_request_id") or None
    sc.complaint_id = data.get("complaint_id") or None
    sc.incident_id = data.get("incident_id") or None
    sc.trang_thai = "dong"
    sc.closed_by, sc.closed_at = u.username, datetime.now()
    db.flush()
    R.audit(db, u.username, u.role, "dong_su_co_tour", f"su_co_tour:{sc.code}", before=truoc,
            after={"nguyen_nhan_nhom": nn, "incident_id": sc.incident_id,
                   "payment_request_id": sc.payment_request_id})
    return sc


def mo_lai(db: Session, u: User, sc: SuCoTour, ly_do: str) -> SuCoTour:
    if sc.trang_thai != "dong":
        raise ValueError("Hồ sơ chưa đóng")
    if len((ly_do or "").strip()) < 20:
        raise ValueError("Mở lại hồ sơ đã kết luận phải có lý do rõ ràng (ít nhất 20 ký tự)")
    sc.trang_thai = "dang_xu_ly"
    sc.closed_by, sc.closed_at = "", None
    db.flush()
    them_xu_ly(db, u, sc, f"MỞ LẠI HỒ SƠ: {ly_do.strip()}")
    R.audit(db, u.username, u.role, "mo_lai_su_co_tour", f"su_co_tour:{sc.code}",
            after={"ly_do": ly_do.strip()[:200]})
    return sc


def qua_han(sc: SuCoTour, bay_gio: datetime | None = None) -> bool:
    """Quá hạn là một SỰ KIỆN tính tại chỗ, không phải cột lưu sẵn.

    Lưu sẵn thì đúng lúc quá hạn không có ai chạy mã để ghi lại, và cờ mãi mãi là 'chưa'. Cùng cách làm
    với hồ sơ khiếu nại khách.
    """
    if sc.trang_thai == "dong" or not sc.han_xu_ly:
        return False
    return (bay_gio or datetime.now()) > sc.han_xu_ly and not sc.nhan_luc


def chi_so(db: Session) -> dict:
    rows = list(db.execute(select(SuCoTour)).scalars())
    bay_gio = datetime.now()
    theo_muc, theo_nhom, theo_nguyen_nhan = {}, {}, {}
    dang_mo = qh = 0
    for sc in rows:
        theo_muc[str(sc.muc)] = theo_muc.get(str(sc.muc), 0) + 1
        theo_nhom[sc.nhom] = theo_nhom.get(sc.nhom, 0) + 1
        if sc.nguyen_nhan_nhom:
            theo_nguyen_nhan[sc.nguyen_nhan_nhom] = theo_nguyen_nhan.get(sc.nguyen_nhan_nhom, 0) + 1
        if sc.trang_thai != "dong":
            dang_mo += 1
        if qua_han(sc, bay_gio):
            qh += 1
    return {"tong": len(rows), "dang_mo": dang_mo, "qua_han_chua_nhan": qh, "theo_muc": theo_muc,
            "theo_nhom": theo_nhom, "theo_nguyen_nhan": theo_nguyen_nhan}


def robot_su_co(db: Session) -> int:
    """Vòng quét: sự cố quá hạn mà chưa ai nhận thì đẩy cảnh báo lên một bậc.

    Chỉ cảnh báo sự cố CHƯA CÓ NGƯỜI NHẬN. Sự cố đang được xử lý mà lâu là chuyện bình thường – một
    chuyến hỏng xe giữa đèo không xong trong hai tiếng. Thứ không bình thường là không ai cầm.
    """
    n = 0
    bay_gio = datetime.now()
    for sc in db.execute(select(SuCoTour).where(SuCoTour.trang_thai != "dong")).scalars():
        if not qua_han(sc, bay_gio):
            continue
        if db.execute(select(Alert).where(Alert.kind == "su_co_tour_qua_han", Alert.ref == sc.code,
                                          Alert.resolved == False)).scalars().first():
            continue
        db.add(Alert(kind="su_co_tour_qua_han", level="red" if sc.muc == 3 else "warn", ref=sc.code,
                     message=f"Sự cố {sc.code} quá hạn xử lý mà chưa có người nhận",
                     to_roles=",".join(("tp_dh", "ptgd_doan", "tgd"))))
        n += 1
    return n
