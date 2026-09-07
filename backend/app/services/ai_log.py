"""Nhật ký AI thống nhất (chỉ đạo 07/9/2026).

Một chỗ duy nhất để ghi vết mọi lần phần mềm dùng mô hình ngôn ngữ. Đặt riêng ra khỏi từng phân hệ vì
nếu để mỗi nơi tự ghi theo cách của mình thì ba tháng nữa sẽ có ba định dạng khác nhau và không cộng
được thành một báo cáo.

Nguyên tắc: ghi cả khi mô hình TRẢ LỜI ĐƯỢC và khi KHÔNG – một lần gọi hỏng, hoặc một lần rơi về câu
trả lời theo quy tắc, cũng là việc phần mềm đã làm thay người và phải truy được.
"""
import hashlib
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models.core import AiRun

MAX_KET_QUA = 2000            # cắt ngắn: nhật ký để truy trách nhiệm, không phải nơi lưu trữ nội dung


def bam(*phan: str) -> str:
    """Mã băm dữ liệu đầu vào – không lưu nguyên văn vì trong đó có tên và số điện thoại khách."""
    h = hashlib.sha256()
    for p in phan:
        h.update((p or "").encode("utf-8")); h.update(b"\x00")
    return h.hexdigest()


def ghi(db: Session, *, tac_vu: str, muc: int, dau_vao: str = "", ket_qua: str = "", nguon: str = "",
        mo_hinh: str = "", ref: str = "", vai_tro: str = "", nguoi: str = "", so_ban_ghi: int = 0,
        tokens_vao: int = 0, tokens_ra: int = 0, trang_thai: str = "khong_can", loi: str = "") -> AiRun:
    r = AiRun(tac_vu=tac_vu, muc=muc, ref=ref, phuc_vu_vai_tro=vai_tro, phuc_vu_nguoi=nguoi,
              mo_hinh=mo_hinh, nguon=nguon, dau_vao_hash=bam(dau_vao) if dau_vao else "",
              so_ban_ghi=so_ban_ghi, ket_qua=(ket_qua or "")[:MAX_KET_QUA],
              tokens_vao=tokens_vao, tokens_ra=tokens_ra, trang_thai=trang_thai, loi=(loi or "")[:300])
    db.add(r)
    return r


def cho_hau_kiem(db: Session, gio: int = 24) -> list[AiRun]:
    """Nội dung AI tự gửi ra ngoài mà chưa ai đọc lại. Hạn hậu kiểm 24 giờ theo đặc tả mục C7."""
    return list(db.execute(select(AiRun).where(AiRun.trang_thai == "cho_hau_kiem").order_by(AiRun.ts)).scalars())


def tong_hop(db: Session, tu: datetime | None = None) -> dict:
    """Ba con số của báo cáo AI: đã làm bao nhiêu, bị người sửa bao nhiêu, bị thu hồi bao nhiêu.

    Tỷ lệ bị sửa tính trên phần ĐÃ hậu kiểm, không tính trên tổng: nội dung chưa ai đọc lại thì chưa biết
    đúng hay sai, gộp vào mẫu số sẽ làm tỷ lệ sai đẹp lên theo đúng tốc độ người ta quên hậu kiểm.
    """
    q = select(AiRun)
    if tu is not None:
        q = q.where(AiRun.ts >= tu)
    rows = list(db.execute(q).scalars())
    da_hau_kiem = [r for r in rows if r.trang_thai in ("chap_nhan", "da_sua", "thu_hoi")]
    sua_hoac_thu = [r for r in da_hau_kiem if r.trang_thai in ("da_sua", "thu_hoi")]
    theo_tac_vu: dict[str, int] = {}
    for r in rows:
        theo_tac_vu[r.tac_vu] = theo_tac_vu.get(r.tac_vu, 0) + 1
    return {
        "tong": len(rows),
        "theo_tac_vu": theo_tac_vu,
        "cho_hau_kiem": len([r for r in rows if r.trang_thai == "cho_hau_kiem"]),
        "da_hau_kiem": len(da_hau_kiem),
        "bi_sua_hoac_thu_hoi": len(sua_hoac_thu),
        # chưa hậu kiểm cái nào thì KHÔNG có tỷ lệ – trả None chứ không trả 0, vì 0 đọc ra là "không sai lần nào"
        "ty_le_bi_sua": (len(sua_hoac_thu) / len(da_hau_kiem)) if da_hau_kiem else None,
        "loi_goi_mo_hinh": len([r for r in rows if r.loi]),
    }
