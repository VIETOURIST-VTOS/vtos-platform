"""BG-1 · Nhận báo cáo ngày do hệ Google Apps Script đẩy sang (Điều 12) — anh Tuấn chốt 25/10/2026.

Hệ báo cáo ngày trên Google Apps Script là nơi 86 người ĐANG nộp thật từ 01/9/2026. Màn hình
/reports dựng xong trước khi có dữ liệu, nên ngày 24/10 bảng hiện **0/86 đã nộp** và cả 86 người
xếp D — trong khi 24 người trong số đó đã nộp thật sáng hôm ấy. Một bảng nói sai về người thật thì
người đọc thôi tin nó, kể cả sau khi dữ liệu về. Và bắt 86 người nộp hai nơi là cách chắc chắn
nhất để cả hai nơi cùng thiếu.

CỬA NÀY KHÔNG CÓ LUẬT RIÊNG — và đây là chỗ đáng ghi nhất của vòng. Bản viết đầu tiên tự tính
`on_time` bằng `REPORT_DEADLINE` và tự dựng dòng `DailyReport`; nó chạy đúng trên bản mã lúc ấy,
nhưng bản ấy cũ hơn main 465 dòng và không biết BC-1 vừa đặt mốc hạn 0 giờ CÓ NGÀY HIỆU LỰC và
không hồi tố, cũng không biết BC-2 vừa thêm bản chụp `daily_report_versions`. Đẩy bản ấy lên thì
cửa nhận chấm sai hạn mọi ngày sau mốc và không sinh bản chụp nào — mà KHÔNG phép thử nào đỏ, vì
luật mới nằm trong hàm mà cửa nhận không gọi tới.

Nay cửa dựng lại tham số rồi gọi ĐÚNG `ops.submit_report`, cùng đường người nộp thẳng trên VTOS đi
qua. Hạn nộp, bản chụp, đường BC-2 «cần bổ sung», điểm nháp robot và nhật ký kiểm toán vì thế
không thể lệch — nếu lệch thì lệch cả hai phía cùng lúc, chứ không phải một phía âm thầm.

TỆP RIÊNG, KHÔNG VIẾT VÀO `services/ops.py`: làn Phân quyền đang giữ tệp ấy cho BC-1 và BC-2. Hai
làn cùng viết một tệp là đúng thứ hàng rào giữ chỗ sinh ra để chặn.

KHỚP NGƯỜI BẰNG MÃ FILE LƯƠNG (`employees.code`). Không khớp tên: danh sách thật có hai người
trùng tên khác mã, khớp nhầm thì điểm người này rơi vào hồ sơ người kia và không ai nhìn ra. Mã lạ
thì BÁO trong `loi`, KHÔNG tự tạo người — một cửa nhận dữ liệu tự đẻ ra tài khoản là lúc danh sách
nhân sự có hai nguồn sự thật.
"""
import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.hr import Employee
from app.models.ops import DailyReport
from app.services import ops as O
from app.services import rules as R


def doc_gio(raw: str):
    """Chuỗi ISO '2026-10-24T17:42:00+07:00' thành giờ VN dạng naive, cùng hệ với `ops.gio_vn()`."""
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d.replace(tzinfo=None)


def _nguoi(db: Session, ma: str):
    e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
    if e is None:
        return None, "không có mã này trong VTOS"
    if not e.user_id:
        return None, "mã chưa nối với tài khoản đăng nhập"
    u = db.get(User, e.user_id)
    return (u, "") if u is not None else (None, "tài khoản đã bị xoá")


def _phan_2(it: dict) -> str:
    p2 = {}
    for cap in (it.get("soLieu") or []):
        if isinstance(cap, (list, tuple)) and len(cap) >= 2 and str(cap[0]).strip():
            p2[str(cap[0]).strip()] = str(cap[1] if cap[1] is not None else "").strip()
    if str(it.get("nghiPhep") or "").strip():
        p2["Nghỉ phép / công tác / lễ"] = str(it["nghiPhep"]).strip()
    if str(it.get("fileDinhKem") or "").strip():
        p2["File đính kèm"] = str(it["fileDinhKem"]).strip()
    return json.dumps(p2, ensure_ascii=False)


def nhan(db: Session, items: list, loai: str = "baocao") -> dict:
    """Nhận một lô bản ghi. Trả về số nhận được và danh sách KHÔNG nhận được kèm lý do.

    Bên gửi xếp hàng đợi và đẩy lại, nên lý do phải nói đúng chỗ hỏng chứ không chỉ nói thất bại.
    """
    nhan_duoc, loi = 0, []
    for it in items:
        ma = str(it.get("maNV") or "").strip()
        ngay_raw = it.get("ngay")
        if not ma or not ngay_raw:
            loi.append({"maNV": ma, "ngay": str(ngay_raw or ""), "vi_sao": "thiếu mã nhân viên hoặc ngày"})
            continue
        ngay = ngay_raw if isinstance(ngay_raw, date) else date.fromisoformat(str(ngay_raw)[:10])
        u, vi_sao = _nguoi(db, ma)
        if u is None:
            loi.append({"maNV": ma, "ngay": str(ngay), "vi_sao": vi_sao})
            continue

        if loai == "diem":
            # Điểm KHÔNG ĐỨNG MỘT MÌNH: chỉ gắn lên báo cáo đã có. Một cột điểm không có bài đằng
            # sau thì người bị chấm không đối chất được, và trưởng phòng không có gì để đọc lại.
            r = db.execute(select(DailyReport).where(DailyReport.user_id == u.id,
                                                     DailyReport.report_date == ngay)).scalars().first()
            if r is None:
                loi.append({"maNV": ma, "ngay": str(ngay), "vi_sao": "chưa có báo cáo của ngày này để gắn điểm"})
                continue
            diem = it.get("diemRobot")
            if diem is None:
                loi.append({"maNV": ma, "ngay": str(ngay), "vi_sao": "thiếu điểm"})
                continue
            canh = [str(c) for c in (it.get("canhBao") or []) if str(c).strip()]
            xl = str(it.get("xepLoaiRobot") or "").strip()
            r.robot_score = max(0.0, min(10.0, float(diem)))
            r.robot_note = ("Google chấm" + (" – xếp loại " + xl if xl else "")
                            + ("; " + "; ".join(canh) if canh else ""))
            nhan_duoc += 1
            continue

        try:
            # Phần 3 của form Google là VIỆC NGÀY MAI (tham số p4); Phần 4 là VƯỚNG MẮC (tham số
            # p3). Đổi chỗ hai cái này là lỗi im lặng — không có gì báo, chỉ có hai cột đọc ngược.
            O.submit_report(db, u, ngay, str(it.get("phan1") or ""), _phan_2(it),
                            str(it.get("phan4") or ""), str(it.get("phan3") or ""),
                            now=doc_gio(it.get("nopLuc") or "") or O.gio_vn())
        except ValueError as ex:
            loi.append({"maNV": ma, "ngay": str(ngay), "vi_sao": str(ex)})
            continue
        nhan_duoc += 1

    db.flush()
    R.audit(db, "robot_google", "cntt", "nhan_bao_cao_google", "google:%s:%d" % (loai, len(items)),
            after={"nhan": nhan_duoc, "loi": len(loi)})
    db.commit()
    return {"ok": True, "nhan": nhan_duoc, "loi": loi}
