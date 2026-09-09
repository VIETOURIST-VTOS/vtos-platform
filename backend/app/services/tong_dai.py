"""Tổng đài: NGHE TRƯỚC, hiểu sau.

P.A Việt Nam công bố bốn API tổng đài (lịch sử cuộc gọi, file ghi âm, CallNow, webhook cuộc gọi đến)
nhưng không công bố đặc tả. Bài hướng dẫn duy nhất có nội dung nêu đúng bốn cái tên tham số và một URL
ví dụ `callback_url.php` – không địa chỉ, không xác thực, không kiểu dữ liệu, không chữ ký.

Tệp này KHÔNG đoán. Nó mở một đầu nhận, ghi nguyên văn những gì tổng đài gửi sang, và dừng ở đó. Phần
diễn giải – số nào của khách, cuộc gọi này thuộc lead nào – viết SAU, khi đã nhìn thấy dữ liệu thật.

Ba điều phải giữ ở một đầu nhận công khai, vì nó không có đăng nhập:

  1. CHUỖI BÍ MẬT TRONG ĐƯỜNG DẪN. Không có nó thì bất kỳ ai trên internet cũng bơm được dòng vào nhật
     ký của công ty. So sánh bằng `secrets.compare_digest` để thời gian trả lời không tiết lộ dần chuỗi
     đúng. Chưa khai chuỗi thì đầu nhận ĐÓNG – mở sẵn một cửa không khoá để chờ cấu hình là cách quên
     mất nó đang mở.
  2. TRẦN LƯU. Một đầu nhận công khai là một đầu nhận có thể bị dội. Cắt thân yêu cầu ở 20 KB và dọn
     dòng cũ khi quá số trần – đĩa đầy thì cả hệ thống dừng, không riêng tổng đài.
  3. KHÔNG GHI THỨ KHÔNG CẦN. Đầu mục HTTP chứa cookie và chuỗi uỷ quyền của bên gọi; giữ lại là tự tạo
     ra một kho bí mật của người khác trong cơ sở dữ liệu của mình. Chỉ giữ những đầu mục nói về ĐỊNH
     DẠNG và NGUỒN GỌI.
"""
import os, json, secrets
from datetime import datetime
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from app.models.crm import TongDaiSuKien

THAN_TOI_DA = 20_000        # ký tự, cắt phần thừa
TRAN_DONG = 2_000           # giữ lại chừng này dòng gần nhất
# Chỉ những đầu mục nói về định dạng và nguồn gọi. Cố ý KHÔNG có cookie / authorization.
DAU_MUC_GIU = ("content-type", "user-agent", "x-forwarded-for", "x-real-ip", "referer", "host")


def ma_bi_mat() -> str:
    return (os.getenv("TONG_DAI_WEBHOOK_MA") or "").strip()


def duong_dan_webhook() -> str:
    """Địa chỉ đưa cho P.A khai. Trả rỗng khi chưa khai chuỗi bí mật – để màn hình nói 'chưa mở' thay vì
    đưa ra một địa chỉ không hoạt động rồi mọi người tưởng đã xong."""
    ma = ma_bi_mat()
    return f"https://vtos.infinitytours.org/api/v1/tong-dai/cuoc-goi/{ma}" if ma else ""


def kiem_ma(ma: str) -> bool:
    that = ma_bi_mat()
    if not that: return False       # chưa cấu hình thì ĐÓNG, không phải mở
    return secrets.compare_digest(ma or "", that)


def _loc_dau_muc(h: dict) -> dict:
    return {k: str(v)[:200] for k, v in (h or {}).items() if k.lower() in DAU_MUC_GIU}


def ghi(db: Session, *, nguon: str, phuong_thuc: str, duong_dan: str, chuoi_truy_van: str,
        than: str, dau_muc: dict, ip: str) -> TongDaiSuKien:
    sk = TongDaiSuKien(
        nguon=(nguon or "")[:20], phuong_thuc=(phuong_thuc or "")[:10], duong_dan=(duong_dan or "")[:300],
        chuoi_truy_van=(chuoi_truy_van or "")[:THAN_TOI_DA], than=(than or "")[:THAN_TOI_DA],
        dau_muc=_loc_dau_muc(dau_muc), ip_goi=(ip or "")[:60], nhan_luc=datetime.now())
    db.add(sk); db.flush()
    _don(db)
    return sk


def _don(db: Session) -> int:
    """Giữ TRAN_DONG dòng gần nhất. Nhật ký kiểu này chỉ để đọc mà hiểu giao thức, không phải để lưu trữ
    lâu dài – khi đã hiểu thì phần diễn giải mới là chỗ giữ dữ liệu."""
    tong = int(db.execute(select(func.count()).select_from(TongDaiSuKien.__table__)).scalar() or 0)
    if tong <= TRAN_DONG: return 0
    moc = db.execute(select(TongDaiSuKien.id).order_by(TongDaiSuKien.id.desc())
                     .offset(TRAN_DONG).limit(1)).scalar()
    if not moc: return 0
    n = db.execute(delete(TongDaiSuKien.__table__).where(TongDaiSuKien.id <= moc)).rowcount or 0
    return int(n)


def _thu_doc_json(s: str):
    try:
        v = json.loads(s)
        return v if isinstance(v, (dict, list)) else None
    except Exception:
        return None


def bang(db: Session, limit: int = 50, nguon: str = "") -> dict:
    """Bảng cho màn hình CNTT: xem tổng đài THẬT SỰ gửi gì sang, để viết phần diễn giải từ bằng chứng.

    `khoa_thay` gom tên trường đã gặp qua các lần gọi – đó chính là đặc tả mà nhà cung cấp không đưa,
    dựng lại từ quan sát.
    """
    q = select(TongDaiSuKien).order_by(TongDaiSuKien.id.desc())
    if nguon: q = q.where(TongDaiSuKien.nguon == nguon)
    ds = list(db.execute(q.limit(min(limit, 200))).scalars())
    khoa: dict[str, int] = {}
    for sk in ds:
        for nguon_khoa in (_thu_doc_json(sk.than), None):
            if isinstance(nguon_khoa, dict):
                for k in nguon_khoa: khoa[k] = khoa.get(k, 0) + 1
        for cap in (sk.chuoi_truy_van or "").split("&"):
            if "=" in cap:
                k = cap.split("=", 1)[0]
                if k: khoa[k] = khoa.get(k, 0) + 1
    return {
        "da_mo": bool(ma_bi_mat()),
        "duong_dan_webhook": duong_dan_webhook(),
        "tong": int(db.execute(select(func.count()).select_from(TongDaiSuKien.__table__)).scalar() or 0),
        # Tên trường đã gặp, nhiều lần nhất trước – đây là thứ để viết phần diễn giải.
        "khoa_thay": sorted(khoa.items(), key=lambda x: -x[1])[:40],
        "dong": [{"id": s.id, "nguon": s.nguon, "phuong_thuc": s.phuong_thuc, "duong_dan": s.duong_dan,
                  "chuoi_truy_van": s.chuoi_truy_van, "than": s.than, "dau_muc": s.dau_muc,
                  "ip_goi": s.ip_goi, "da_doc": s.da_doc,
                  "nhan_luc": s.nhan_luc.isoformat() if s.nhan_luc else ""} for s in ds],
    }
