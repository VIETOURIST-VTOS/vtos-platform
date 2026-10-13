# -*- coding: utf-8 -*-
"""HÓA ĐƠN PHÁT HÀNH ĐÚNG MỘT LẦN — Đợt E7, 13/10/2026. Chủ tịch chốt bốn điều, và duyệt hình
dáng ba màn hình qua một bản dựng thử trước khi em viết mã.

BỐN CHỖ HỎNG, ĐO ĐƯỢC TRÊN main NGÀY 13/10/2026

  1. `accounting.issue_invoice` ĐỌC RỒI GHI, KHÔNG KHOÁ: nó kiểm `inv.status != "nhap"` rồi mới
     làm tiếp. Hai lần bấm gần nhau cùng đọc thấy "nhap".
  2. Số hóa đơn cấp bằng `max(Invoice.number) + 1`, và cột `number` KHÔNG có chỉ mục duy nhất
     cùng `series`. Hai hóa đơn khác nhau phát hành cùng lúc đều nhận CÙNG MỘT SỐ.
  3. Nút "Phát hành" trên màn hình KHÔNG tự khoá sau khi bấm.
  4. Không có trạng thái nào cho "đã gửi mà chưa biết kết quả".

PHẢI NÓI CHO ĐÚNG MỨC. Hôm nay thiệt hại của ba chỗ đầu là MỘT LẦN 422 KHÓ HIỂU, không phải hai
hóa đơn thật đã gửi lên cơ quan thuế — vì khoá sự kiện của Đợt E3 (`invoice:<ký hiệu>-<số>` cộng
nghiệp vụ `phat_hanh_hoa_don`) chặn lần ghi sổ thứ hai, và vì `db.commit()` chưa chạy nên cả lượt
bị hoàn lại. Nhà cung cấp hiện tại cũng chỉ là bộ cấp số NỘI BỘ, không gọi ra ngoài.

NHƯNG `PROVIDER` LÀ MỘT Ô CẮM. Ngày ký hợp đồng HĐĐT và cắm adapter Viettel/VNPT/MISA vào đúng
dòng ấy, lần gọi thứ hai TIÊU MỘT SỐ HÓA ĐƠN THẬT ở cơ quan thuế — và hoàn lại một giao dịch cơ
sở dữ liệu KHÔNG gỡ được cái đã gửi đi. Đây là chỗ phải vá TRƯỚC khi cắm, không phải sau.

BỐN ĐIỀU CHỦ TỊCH CHỐT

  1. CHẶN Ở CẢ HAI ĐẦU. Màn hình sinh một mã việc cho một lần bấm và gửi kèm; bấm hai lần gửi
     CÙNG một mã, và lần hai nhận lại ĐÚNG kết quả lần một chứ không phát hành lại và cũng không
     báo lỗi. Cộng CHỈ MỤC DUY NHẤT (series, number) ở cơ sở dữ liệu, cho đường nào đi tắt: robot
     gọi thẳng API, hay một bản vá sau này viết sai, đều không đi qua mã việc ở màn hình — một
     hàng rào chỉ ở màn hình là không có hàng rào nào.
  2. SỐ CẤP TỪ BẢNG SỐ NHẢY, chỉ tăng, không bao giờ lùi. Xem `models/so_hoa_don.py`.
  3. TRẠNG THÁI THỨ TƯ `dang_phat_hanh` cộng CỬA DÒ LẠI. Mạng đứt giữa đường thì hệ thống biết
     mình đã gửi và không biết bên kia đã nhận — và hai điều ấy KHÁC NHAU. Coi "không biết" là
     "thất bại" chính là cách làm ra hóa đơn trùng, nên hệ thống KHÔNG TỰ QUYẾT: nó dừng ở trạng
     thái ấy và đưa ra một cửa để người ĐI HỎI.
  4. KHÔNG TỰ GỌI LẠI nhà cung cấp. Nếu lần gọi đầu thực sự đã tới đích mà chỉ câu trả lời bị
     mất, thì lần gọi lại là tờ thứ hai — trừ khi nhà cung cấp tôn trọng mã việc, và điều đó phụ
     thuộc một hợp đồng chưa ký. Đợi biết rồi mới làm.
"""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import Invoice
from app.models.core import User
from app.models.so_hoa_don import SoNhayHoaDon
from app.services import rules as R

# Ba câu trả lời có thể của một lần dò lại. ĐÚNG BA, và câu thứ ba không phải một dạng của hai
# câu đầu: "chưa biết" là một câu trả lời hợp lệ, và giữ nguyên trạng thái là việc đúng khi nhận
# được nó. Thà một tờ treo chờ hỏi lại còn hơn hai tờ đã gửi lên thuế.
DA_RA, CHUA_RA, CHUA_BIET = "da_ra", "chua_ra", "chua_biet"


class SaiPhatHanh(ValueError):
    """Không phát hành được, kèm câu nói ra vì sao."""


def ma_viec_moi() -> str:
    """Mã việc do MÁY CHỦ sinh, dùng khi người gọi không gửi mã.

    Một mã do máy chủ sinh KHÔNG chống được bấm hai lần — hai lần bấm ra hai mã khác nhau. Nó chỉ
    để mọi lần phát hành đều có một mã trong sổ. Chỗ chặn thật là mã do MÀN HÌNH sinh (một mã cho
    một lần bấm), cộng chỉ mục duy nhất trên (series, number).
    """
    return "sv:" + uuid.uuid4().hex


def tim_theo_ma_viec(db: Session, ma_viec: str) -> Invoice | None:
    """Hóa đơn đã nhận mã việc này chưa. Đây là phép CHỐNG GỌI HAI LẦN ở tầng ứng dụng."""
    if not ma_viec:
        return None
    return db.execute(select(Invoice).where(Invoice.issue_request_id == ma_viec)).scalars().first()


def cap_so(db: Session, series: str, boi: str) -> int:
    """Cấp số tiếp theo của một ký hiệu. KHOÁ HÀNG trước khi tăng.

    `with_for_update()` là chỗ sửa lỗi gốc: Postgres giữ hàng cho tới hết giao dịch nên lần gọi
    thứ hai ĐỢI chứ không đọc cùng một số. SQLite chạy một tiến trình nên không cần, và bỏ qua
    câu ấy — phép thử vì thế KHÔNG đo được chỗ khoá; thứ đo được là chỉ mục duy nhất, và đó chính
    là lý do đợt này đặt hàng rào thứ hai ở cơ sở dữ liệu thay vì tin vào một chỗ mà phép thử
    không soi tới.
    """
    d = db.execute(select(SoNhayHoaDon).where(SoNhayHoaDon.series == series)
                   .with_for_update()).scalars().first()
    if not d:
        # Ký hiệu mới. Bắt đầu từ số lớn nhất ĐÃ TIÊU trong sổ chứ không từ 0: nếu bản di trú
        # chưa nạp ký hiệu này (hóa đơn nhập từ sổ cũ sau ngày di trú) thì bắt đầu từ 0 là cấp
        # lại đúng những số đã in ra giấy.
        da_tieu = db.execute(select(func.max(Invoice.number))
                             .where(Invoice.series == series)).scalar() or 0
        d = SoNhayHoaDon(series=series, so_cuoi=da_tieu)
        db.add(d)
        db.flush()
    d.so_cuoi = (d.so_cuoi or 0) + 1
    d.cap_nhat_luc, d.cap_nhat_boi = datetime.now(), boi
    db.flush()
    return d.so_cuoi


def bang_so_nhay(db: Session) -> list[dict]:
    """Một dòng cho mỗi ký hiệu: số cuối đã cấp, đã phát hành, đã hủy, và DÃY SỐ CÓ LIÊN TỤC KHÔNG.

    Câu "có liên tục không" hỏi theo SỐ ĐÃ CẤP chứ không theo số hóa đơn đang có: một số đã cấp mà
    tờ của nó không bao giờ ra là đúng cái bất thường cần thấy, và đếm lại từ các hóa đơn thì nó
    biến mất khỏi phép đếm.
    """
    ra = []
    for d in db.execute(select(SoNhayHoaDon).order_by(SoNhayHoaDon.series)).scalars():
        so = {i.number: i.status for i in db.execute(
            select(Invoice).where(Invoice.series == d.series, Invoice.number > 0)).scalars()}
        thieu = [n for n in range(1, (d.so_cuoi or 0) + 1) if n not in so]
        ra.append({
            "series": d.series, "so_cuoi": d.so_cuoi or 0,
            "da_phat_hanh": sum(1 for s in so.values() if s == "da_phat_hanh"),
            "da_huy": sum(1 for s in so.values() if s == "huy"),
            "dang_phat_hanh": sum(1 for s in so.values() if s == "dang_phat_hanh"),
            "so_thieu": thieu[:20], "so_thieu_tong": len(thieu),
            "cap_nhat_luc": d.cap_nhat_luc, "cap_nhat_boi": d.cap_nhat_boi,
        })
    return ra


def do_lai(db: Session, u: User, inv: Invoice) -> dict:
    """Hỏi nhà cung cấp xem tờ đang treo đã ra chưa. KHÔNG gửi lại, chỉ HỎI.

    Gọi `PROVIDER.tra_cuu`. Ba câu trả lời, ba đường đi, và đường thứ ba là GIỮ NGUYÊN.
    """
    from app.services import accounting as ACC
    if inv.status != "dang_phat_hanh":
        raise SaiPhatHanh(f"Hóa đơn này không ở trạng thái đang phát hành (hiện {inv.status}).")

    kq, so, ref = ACC.PROVIDER.tra_cuu(db, inv)

    if kq == DA_RA:
        inv.number = so or inv.number
        inv.provider_ref = ref or inv.provider_ref
        inv.provider, inv.issue_date, inv.status = ACC.PROVIDER.name, inv.issue_date or datetime.now().date(), "da_phat_hanh"
        inv.issued_by = inv.issued_by or u.username
        inv.issued_at = inv.issued_at or datetime.now()
        db.flush()
        e = ACC.on_invoice_issued(db, inv)
        inv.entry_id = e.id
        R.audit(db, u.username, u.role, "do_lai_hoa_don_da_ra",
                f"invoice:{inv.series}-{inv.number}", after={"ma_tra_cuu": inv.provider_ref,
                                                            "chung_tu": e.code})
        db.commit()
        return {"ket_qua": DA_RA,
                "message": f"Nhà cung cấp xác nhận hóa đơn {inv.series}-{inv.number:07d} ĐÃ RA. "
                           f"Đã ghi sổ, không gửi lại lần nào."}

    if kq == CHUA_RA:
        # SỐ ĐÃ CẤP KHÔNG TRẢ LẠI. Số ấy đã tiêu, và một khoảng trống trong dãy số là điều có
        # thật, nhìn thấy được ở sổ số nhảy. Trả lại số là cách cấp một số cho hai tờ.
        so_cu = inv.number
        inv.status, inv.number, inv.provider_ref = "nhap", 0, ""
        inv.issue_sent_at = None
        R.audit(db, u.username, u.role, "do_lai_hoa_don_chua_ra", f"invoice_draft:{inv.id}",
                before={"so_da_cap": so_cu},
                after={"ly_do": "nhà cung cấp xác nhận chưa ra tờ nào — trả về nháp"})
        db.commit()
        return {"ket_qua": CHUA_RA,
                "message": f"Nhà cung cấp xác nhận CHƯA RA tờ nào. Hóa đơn trở về nháp, phát hành "
                           f"lại được. Số {so_cu} đã cấp thì KHÔNG cấp lại — nó là một khoảng "
                           f"trống có lý do trong dãy số, xem sổ số hóa đơn."}

    R.audit(db, u.username, u.role, "do_lai_hoa_don_chua_biet", f"invoice_draft:{inv.id}",
            after={"ly_do": "nhà cung cấp chưa trả lời dứt khoát — giữ nguyên đang phát hành"})
    db.commit()
    return {"ket_qua": CHUA_BIET,
            "message": "Nhà cung cấp CHƯA trả lời dứt khoát. Giữ nguyên trạng thái đang phát hành "
                       "— thà một tờ treo chờ hỏi lại còn hơn hai tờ đã gửi lên thuế. Dò lại sau."}
