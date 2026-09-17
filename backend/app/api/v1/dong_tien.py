"""Cửa của khối dòng tiền – Robot A, GD-1 (11/9/2026).

Theo ranh giới công việc 09/9/2026: mỗi con số hệ thống cần MỘT CỬA cho người dùng đưa vào. Bảng
`chot_so_du` sinh ra hôm nay ở bản nâng cấp a1e4d7c2f8b93 – tệp này là cửa ấy, và là cửa nhập số 1
của cả bảng dòng tiền (DT-2).

BA ĐIỀU MỌI CỬA Ở ĐÂY GIỮ

1. RỖNG KHÁC KHÔNG. Thiếu đầu vào thì trả `null` kèm `vi_sao` đọc được bằng tiếng Việt, không lấy 0
   thay cho "chưa ai chốt". Giao diện hiện "Chưa có nguồn – …", không hiện "0 đ".

2. KHÔNG BÙ TRỪ GIỮA HAI PHÁP NHÂN. Mọi đường ở đây nhận ĐÚNG MỘT `company_id` và đi qua hàng rào
   phạm vi `PV.loc`. Toàn cảnh là một DANH SÁCH từng pháp nhân, cố ý không có dòng tổng.

3. QUYỀN KHAI Ở CHỮ KÝ HÀM, để bộ kiểm KS-2 đọc được bằng máy. Danh sách vai trò dưới đây là bản
   khai TẠM của Robot A: theo lệnh giao việc, `app/services/access.py` CHỈ Robot B được sửa, nên
   Robot A gửi khai báo sang Robot B để gom thành nhóm có tên (xem bản bàn giao), không tự sửa tệp ấy.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.dong_tien import NGUON_TIEN, ChotSoDu
from app.services import dong_tien as DT
from app.services import han_dong_tien as HAN
from app.services import khung_dong_tien as KHUNG
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R
from app.services import xuat_dong_tien_excel as XL

router = APIRouter(prefix="/api/v1/dong-tien", tags=["dong-tien"])

# Ai XEM khối dòng tiền. Chủ tịch, Kế toán và Ban Kiểm soát giữ TOÀN CẢNH – một bên lập số, một bên
# soát số, không nhìn đủ thì không làm được việc. Tổng giám đốc có mặt ở đây nhưng CHỈ xem phần
# trong phạm vi: việc lọc theo từng dòng là SEC-02 của làn Phân quyền, không phải việc của cửa này.
XEM = ("chutich", "tgd", "ketoan", "bks", "robot_ks", "cntt")
# Ai CHỐT số dư. Kế toán là người đối soát với sao kê và sổ quỹ; CNTT có mặt để vận hành, không để
# thay Kế toán ký.
CHOT = ("ketoan", "cntt")


class ChotIn(BaseModel):
    company_id: int
    nguon: str
    tai_khoan_id: int | None = None
    den_ngay: date
    so_du: float
    ly_do_lech: str = ""
    ghi_chu: str = ""


def _ra(b: ChotSoDu) -> dict:
    return {"id": b.id, "company_id": b.company_id, "nguon": b.nguon,
            "nguon_mo_ta": NGUON_TIEN.get(b.nguon, b.nguon),
            "tai_khoan_id": b.tai_khoan_id, "den_ngay": b.den_ngay,
            "so_du": float(b.so_du),
            "so_may_cong": None if b.so_may_cong is None else float(b.so_may_cong),
            "lech": None if b.lech is None else float(b.lech),
            "ly_do_lech": b.ly_do_lech, "trang_thai": b.trang_thai,
            "thay_the_id": b.thay_the_id, "boi": b.boi, "luc": b.luc, "ghi_chu": b.ghi_chu}


@router.get("/chot-so-du")
def danh_sach_chot(company_id: int | None = None, limit: int = 200, offset: int = 0,
                   u: User = Depends(require_roles(*XEM, mo_ta="xem chốt số dư")),
                   db: Session = Depends(get_db)):
    """Sổ chốt số dư. CÓ TRẦN và lọc theo phạm vi pháp nhân của phiên đăng nhập.

    Trần đặt ngay từ đầu, không đợi bảng dài ra mới thêm: KS-5 đã đo một cửa đọc cả 1.703 dòng rồi
    mới lọc bằng Python, và cửa ấy chỉ trở thành vấn đề sau khi dữ liệu đã nhiều.
    """
    qs = select(ChotSoDu).order_by(ChotSoDu.den_ngay.desc(), ChotSoDu.id.desc())
    qs = PV.loc(qs, ChotSoDu, u)          # hàng rào phạm vi pháp nhân – khai ở PHAI_LOC
    if company_id:
        qs = qs.where(ChotSoDu.company_id == company_id)
    tong = len(db.execute(qs).scalars().all())
    tran = max(1, min(limit, 500))
    dong = db.execute(qs.offset(offset).limit(tran)).scalars().all()
    return {"rows": [_ra(b) for b in dong], "tong": tong, "offset": offset, "limit": tran,
            "cham_tran": offset + len(dong) < tong}


@router.post("/chot-so-du", status_code=201)
def chot_so_du(data: ChotIn,
               u: User = Depends(require_roles(*CHOT, mo_ta="chốt số dư đã đối soát")),
               db: Session = Depends(get_db)):
    """Kế toán chốt: đến hết ngày này, nguồn tiền này của pháp nhân này còn ngần này.

    Chốt lại cùng một ngày thì bản cũ bị THAY THẾ, không bị xoá – ai chốt nhầm và ai sửa là câu kiểm
    toán sẽ hỏi.
    """
    try:
        b = DT.chot(db, u.username, data.company_id, data.nguon, data.tai_khoan_id,
                    data.den_ngay, data.so_du, data.ly_do_lech, data.ghi_chu)
    except DT.LoiChot as e:
        raise HTTPException(422, str(e))
    R.audit(db, u.username, u.role, "chot_so_du", f"chot_so_du:{b.id}",
            after={"company_id": b.company_id, "nguon": b.nguon, "den_ngay": str(b.den_ngay),
                   "so_du": float(b.so_du), "lech": None if b.lech is None else float(b.lech)})
    db.commit()
    return {**_ra(b), "message": f"Đã chốt số dư đến hết {b.den_ngay:%d/%m/%Y}"}


@router.get("/tien-kha-dung/{company_id}")
def xem_tien_kha_dung(company_id: int, den_ngay: date | None = None,
                      u: User = Depends(require_roles(*XEM, mo_ta="xem tiền khả dụng")),
                      db: Session = Depends(get_db)):
    """DT-1. Thiếu đầu vào thì `tien_kha_dung` là null kèm `vi_sao` – KHÔNG phải 0."""
    try:
        return DT.tien_kha_dung(db, company_id, den_ngay)
    except DT.LoiChot as e:
        raise HTTPException(404, str(e))


@router.get("/bang/{company_id}")
def xem_bang(company_id: int, den_ngay: date | None = None,
             u: User = Depends(require_roles(*XEM, mo_ta="xem bảng dòng tiền bốn mốc")),
             db: Session = Depends(get_db)):
    """DT-3. Bốn cột LŨY KẾ từ cùng một ngày – chúng chồng lên nhau, không được cộng."""
    try:
        return DT.bang_bon_moc(db, company_id, den_ngay)
    except DT.LoiChot as e:
        raise HTTPException(404, str(e))


@router.get("/khung/{company_id}")
def xem_khung(company_id: int, den_ngay: date | None = None,
              u: User = Depends(require_roles(*XEM, mo_ta="xem khối dòng tiền theo vai")),
              db: Session = Depends(get_db)):
    """TC-8 · Màn hình 01 — khung theo VAI đã điền số. MÁY CHỦ CẮT TẬP DÒNG, không phải trình duyệt.

    Vì sao đường dẫn này nằm ở tệp của làn Robot A: hai nửa của màn hình 01 đã có sẵn ở hai làn —
    `dong_tien_pham_vi` (ai xem dòng nào, ai nhập dòng nào) và `bang_bon_moc` (số của bốn mốc) —
    nhưng không có chỗ nào ghép chúng, nên màn hình chỉ còn hai lối đi đều sai: hiện toàn cảnh cho
    mọi vai, hoặc tự lọc ở trình duyệt. Chủ tịch cho phép làn giao diện bắc cầu ngày 12/9/2026.
    Phép tính của làn A giữ nguyên, tệp này chỉ GỌI `bang_bon_moc` chứ không sửa nó.

    `/bang/{company_id}` ở trên GIỮ NGUYÊN cho màn hình cũ và cho Kế toán đối chiếu toàn cảnh.
    """
    try:
        bang = DT.bang_bon_moc(db, company_id, den_ngay)
        sdn = DT.so_du_tung_ngay(db, company_id, den_ngay)
    except DT.LoiChot as e:
        raise HTTPException(404, str(e))
    # Hạn xử lý gắn SAU khi đã cắt theo vai: vai nào không nhận dòng ấy thì cũng không nhận hạn của
    # nó. `gan_han` chỉ ĐỌC — cửa GET không được đẻ cảnh báo, nếu không số cảnh báo tăng theo số lần
    # người dùng bấm F5.
    return HAN.gan_han(db, company_id, KHUNG.ghep(u.role, bang, sdn))


@router.get("/khung/{company_id}/excel")
def xuat_khung_excel(company_id: int, den_ngay: date | None = None,
                     u: User = Depends(require_roles(*XEM, mo_ta="xuất Excel khối dòng tiền")),
                     db: Session = Depends(get_db)):
    """Xuất khối dòng tiền ra Excel — nút "Xuất Excel" trên màn hình 01 (14/9/2026).

    DÙNG LẠI ĐÚNG ĐƯỜNG CỦA MÀN HÌNH: gọi cùng `bang_bon_moc` + `so_du_tung_ngay` + `KHUNG.ghep`,
    rồi mới dựng tệp. Nhờ vậy Excel không thể nói khác màn hình — nếu tách ra truy vấn riêng thì
    hai nơi lấy số ở hai thời điểm, và lệch nhau là chuyện sớm muộn.

    SEC-02 giữ nguyên: `ghep(u.role, ...)` đã cắt tập dòng theo vai, tệp Excel chỉ ghi lại những
    dòng nhận được. Bộ dựng tệp KHÔNG biết vai là gì và không được biết.

    CÓ NHẬT KÝ (v1.1 §IV.3 đòi "nút xuất Excel có nhật ký"). Một tệp dòng tiền rời khỏi hệ thống là
    một việc phải trả lời được câu "ai lấy, lúc nào, của pháp nhân nào" — nên ghi một dòng vào sổ
    nhật ký có xâu chuỗi băm, cùng chỗ với mọi thao tác ghi khác.
    """
    try:
        bang = DT.bang_bon_moc(db, company_id, den_ngay)
        sdn = DT.so_du_tung_ngay(db, company_id, den_ngay)
    except DT.LoiChot as e:
        raise HTTPException(404, str(e))
    k = HAN.gan_han(db, company_id, KHUNG.ghep(u.role, bang, sdn))
    try:
        noi_dung = XL.dung_tep(k)
    except ValueError as e:
        raise HTTPException(403, str(e))

    ten = XL.ten_tep(k)
    R.audit(db, u.username, u.role, "xuat_excel_dong_tien", f"dong_tien:{company_id}",
            after={"company_id": company_id, "den_ngay": str(den_ngay or ""), "ten_tep": ten,
                   "so_dong": len(k.get("dong") or []), "muc_xem": k.get("muc_xem")})
    db.commit()
    # filename* theo RFC 5987: tên tệp không dấu nên ASCII là đủ, vẫn khai UTF-8 để trình duyệt
    # nào cũng hiểu một cách.
    return Response(
        content=noi_dung,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{ten}"; filename*=UTF-8\'\'{ten}'},
    )


@router.get("/so-du-tung-ngay/{company_id}")
def xem_so_du_tung_ngay(company_id: int, den_ngay: date | None = None,
                        u: User = Depends(require_roles(*XEM, mo_ta="xem số dư từng ngày")),
                        db: Session = Depends(get_db)):
    """DT-4. Bắt thiếu tiền GIỮA KỲ – kỳ kết thúc dương mà vẫn có ngày hụt ở giữa."""
    try:
        return DT.so_du_tung_ngay(db, company_id, den_ngay)
    except DT.LoiChot as e:
        raise HTTPException(404, str(e))


# --------------------------------------------------- DT-5 · hai cơ sở ngày · DT-6 · chống trùng
#
# KHÔNG CÓ ĐƯỜNG DẪN Ở ĐÂY. Sổ nghĩa vụ thuộc lằn VPM-11, và nó đã có cửa riêng trong nhóm `/fin`
# đã được cấp quyền từ trước:
#     GET  /api/v1/fin/nghia-vu            – cộng theo nhóm trên hai cơ sở ngày
#     GET  /api/v1/fin/nghia-vu/chi-tiet   – danh sách chứng từ đứng sau một con số
#     POST /api/v1/fin/nghia-vu/dong-bo    – dựng lại sổ từ sáu bảng chứng từ gốc
#
# Bản đầu của tệp này có POST /nghia-vu và GET /nghia-vu/{company_id} đi cùng bảng `nghia_vu_tien`
# của Robot A. Bỏ cả hai ngày 11/9/2026 khi gộp: hai đường dẫn trả hai con số nợ phải trả cho cùng
# một công ty là chỗ để người đọc chọn con số dễ nghe hơn.


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM, mo_ta="danh mục cho màn hình dòng tiền")),
         db: Session = Depends(get_db)):
    """Danh mục cho màn hình: pháp nhân và tài khoản ngân hàng, ĐI QUA CHÍNH PHÂN HỆ NÀY.

    Vì sao không để màn hình gọi thẳng /api/v1/companies và /api/v1/bank-accounts: gọi thẳng là nhân
    danh sách vai trò của phân hệ khác lên cho mọi ai mở được màn hình này – bài học vòng 1 của Sự cố
    tour ngày 10/9/2026, đã ghi sẵn trong bảng chốt phạm vi P2. Một cửa danh mục của riêng mình thì
    phạm vi dừng đúng ở đây.

    Danh sách pháp nhân đi qua hàng rào phạm vi: người chỉ phụ trách một pháp nhân không thấy tên các
    pháp nhân khác trong ô chọn – thấy tên cũng đã là biết công ty có những pháp nhân nào.
    """
    from app.models.banks import BankAccount
    from app.models.core import Company

    qs = PV.loc(select(Company).where(Company.active == True), Company, u)   # noqa: E712
    cty = [{"id": c.id, "code": c.code, "name": c.name}
           for c in db.execute(qs.order_by(Company.code)).scalars()]
    tk = [{"id": t.id, "code": t.code, "bank_name": t.bank_name}
          for t in db.execute(select(BankAccount).where(BankAccount.active == True)   # noqa: E712
                              .order_by(BankAccount.code)).scalars()]
    return {"phap_nhan": cty, "tai_khoan": tk,
            "nguon_tien": NGUON_TIEN,
            "ghi_chu": ("Danh mục tài khoản ngân hàng CHƯA có cột pháp nhân (đo 11/9/2026), nên danh "
                        "sách này chưa lọc được theo pháp nhân – việc của làn Kế toán, đã ghi trong "
                        "bản bàn giao.")}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# TC-58 (17/9/2026) · CỬA DỰNG LẠI SỔ NGHĨA VỤ THANH TOÁN
# ═══════════════════════════════════════════════════════════════════════════════════════════════
# Anh Tuấn 17/9: "em đọc hướng dẫn này vào Vietrip cập nhật nợ phải thu - phải trả".
#
# Đi soát thì số Vietrip ĐÃ về đủ: 12.198 phiếu đặt nằm trong `bookings`, 4.815 chứng từ chi NCC nằm
# trong `payment_requests`. Hàm dựng sổ nghĩa vụ từ hai bảng ấy cũng đã có sẵn và chạy-lại-được
# (`services/nghia_vu.dong_bo`). Thứ DUY NHẤT thiếu là một cửa để bấm chạy nó — nên hai khối Phải thu
# · Phải trả của màn hình Chủ tịch đọc một cuốn sổ chưa ai dựng, và trả rỗng kèm đúng lý do.
#
# Đây chính là cái mà ranh giới công việc 09/9/2026 gọi là VIỆC CÒN THIẾU: "mỗi con số hệ thống cần
# phải có một cửa nhập hoặc cửa tải cho người dùng; không có cửa thì đó là việc còn thiếu". Vòng này
# mở cửa ấy, không nhập hộ một con số nào.
#
# VÌ SAO KHÔNG TỰ CHẠY THEO LỊCH Ở VÒNG NÀY: dựng lại sổ là một phép quét toàn bộ sáu nguồn, và việc
# chạy nền bị cắt giữa chừng ĐÃ xảy ra với robot Vietrip hôm 17/9 — nhưng CHƯA AI BIẾT VÌ SAO.
#
# Bản viết đầu của chú thích này ghi nguyên nhân là "gói Render miễn phí ngủ sau 15 phút". Đo lại
# cùng ngày trên chính bảng Render: vtos-api đang ở gói TRẢ TIỀN 0,5 CPU / 512 MB (7 USD/tháng), và
# máy trả tiền thì KHÔNG ngủ. Câu ấy sai, nên gỡ — một nguyên nhân đoán mà ghi vào mã thì vòng sau
# sẽ đi sửa nhầm chỗ, và không có lỗi nào báo.
#
# Nghi vấn còn lại, chưa đo: 512 MB bộ nhớ cho một lượt quét 12.198 phiếu đặt. Phải ĐẾM trước khi
# kết luận. Cửa bấm tay chạy đồng bộ và thấy kết quả ngay, nên đặt lịch chờ được tới lúc biết thật.
DUNG_SO = ("ketoan", "cntt")


@router.post("/nghia-vu/dong-bo")
def dong_bo_nghia_vu(u: User = Depends(require_roles(*DUNG_SO, mo_ta="dựng lại sổ nghĩa vụ thanh toán")),
                     db: Session = Depends(get_db)):
    """Dựng lại sổ nghĩa vụ từ sáu nguồn chứng từ. Bấm bao nhiêu lần cũng ra cùng một sổ.

    Trả về số dòng mỗi nguồn sinh ra, để người bấm ĐỐI CHIẾU ĐƯỢC chứ không phải tin lời: `bookings`
    phải xấp xỉ số phiếu đặt còn nợ, `payment_requests` phải xấp xỉ số chứng từ chi chưa trả. Lệch
    nhiều là dấu hiệu một lô Vietrip chưa ánh xạ xong — bấm `POST /import/vietrip/apply` trước.
    """
    from app.services import nghia_vu as NV
    try:
        ra = NV.dong_bo(db)
    except Exception as e:      # noqa: BLE001 — trả lỗi có nội dung để CNTT chẩn đoán
        db.rollback()
        raise HTTPException(500, f"Dựng sổ lỗi: {type(e).__name__}: {str(e)[:600]}")
    R.audit(db, u.username, u.role, "dong_bo_nghia_vu", "nghia_vu_thanh_toan", after=ra)
    db.commit()
    return {**ra, "message": f"Đã dựng lại sổ nghĩa vụ — {ra['tong_dong']} dòng"}
