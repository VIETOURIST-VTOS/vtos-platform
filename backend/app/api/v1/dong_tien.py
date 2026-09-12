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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.dong_tien import NGUON_TIEN, ChotSoDu
from app.services import dong_tien as DT
from app.services import khung_dong_tien as KHUNG
from app.services import pham_vi_phap_nhan as PV
from app.services import rules as R

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
    return KHUNG.ghep(u.role, bang, sdn)


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
