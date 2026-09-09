"""Hai đường tiền vào phải cùng sống. Phép thử sinh ra từ một chỗ hỏng có thật (09/9/2026).

Token đường kéo bù được tạo sẵn bên SePay, tác vụ n8n gọi 7 phút/lần cũng dựng xong, nhưng biến
SEPAY_API_TOKEN chưa bao giờ khai trên máy chủ. Đường kéo bù CHƯA TỪNG chạy – và không ai thấy, vì
webhook vẫn tốt. Chuyện lộ ra nhờ bộ đếm lỗi 5xx, tức là nhờ n8n kêu hộ.

  TV1  thiếu đường kéo bù là mức ĐỎ, dù webhook đang chạy tốt và chẳng có gì hỏng hôm nay
  TV2  thiếu đường webhook cũng ĐỎ
  TV3  đủ cả hai đường thì IM – không báo gì
  TV4  lâu không có giao dịch nào thì VÀNG, và chỉ vàng
  TV5  chưa có giao dịch nào thì KHÔNG báo im lặng (hệ thống mới dựng, không phải hỏng)
  TV6  phép kiểm KHÔNG gọi ra SePay – vòng quét chạy mỗi phút, gọi ra ngoài mỗi phút là tự tạo nguồn hỏng
  TV7  đã gắn vào vòng quét và khai đúng loại phát hiện
"""
import os, sys
from datetime import datetime, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_tienvao.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tienvao.db", "test_tienvao.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest


@pytest.fixture
def db():
    from app.db.session import SessionLocal, Base, engine
    import app.main  # noqa
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()


def _khai(webhook: str, token: str):
    from app.core.config import settings
    settings.SEPAY_WEBHOOK_KEY = webhook
    settings.SEPAY_API_TOKEN = token


def _ma(ds): return {x["ma"] for x in ds}


def test_tv1_thieu_duong_keo_bu_la_muc_do_du_webhook_van_tot(db):
    """Đây là ca đã xảy ra thật. Webhook chạy tốt, không gì hỏng, mà vẫn phải ĐỎ – vì một lớp đỡ chưa
    cấu hình là một chốt chặn đang thiếu, không phải một tính năng chưa làm."""
    from app.services import ks_tien_vao as TV
    _khai("co-webhook-key", "")
    ds = TV.quet(db)
    x = [d for d in ds if d["ma"] == "tien_vao#keo_bu_chua_khai"]
    assert x, "thiếu đường kéo bù mà không báo thì phép kiểm này vô nghĩa"
    assert x[0]["muc"] == "do", "phải ĐỎ – vàng thì không ai xử, và nó nằm im thêm mấy tháng nữa"
    assert "LƯỚI ĐỠ" in x[0]["tom_tat"].upper() or "lưới đỡ" in x[0]["tom_tat"]
    assert "tien_vao#webhook_chua_khai" not in _ma(ds), "webhook đang tốt thì không báo webhook"


def test_tv2_thieu_duong_webhook_cung_do(db):
    from app.services import ks_tien_vao as TV
    _khai("", "co-api-token")
    assert "tien_vao#webhook_chua_khai" in _ma(TV.quet(db))


def test_tv3_du_ca_hai_duong_thi_im(db):
    """Bộ kiểm báo cả lúc không có gì để báo là bộ kiểm người ta tắt đi."""
    from app.services import ks_tien_vao as TV
    _khai("co-webhook-key", "co-api-token")
    assert not [d for d in TV.quet(db) if d["loai"] == "tien_vao_thieu_duong"]


def test_tv4_lau_khong_co_giao_dich_thi_vang_va_chi_vang(db):
    """Im lặng có thể là kỳ nghỉ, cũng có thể là đường nhận tiền đã đứt. Chưa đủ chắc để ĐỎ."""
    from app.services import ks_tien_vao as TV
    from app.models.payments import BankTransaction
    _khai("co-webhook-key", "co-api-token")
    db.add(BankTransaction(sepay_id="thu-1", transaction_date=datetime.now() - timedelta(hours=TV.GIO_IM_LANG + 10),
                           amount=1_000_000, transfer_type="in", content="thu", gateway="TPBank"))
    db.commit()
    x = [d for d in TV.quet(db) if d["ma"] == "tien_vao#im_lang"]
    assert x and x[0]["muc"] == "vang"

    # giao dịch mới thì im
    db.add(BankTransaction(sepay_id="thu-2", transaction_date=datetime.now() - timedelta(hours=1),
                           amount=2_000_000, transfer_type="in", content="thu", gateway="TPBank"))
    db.commit()
    assert "tien_vao#im_lang" not in _ma(TV.quet(db))


def test_tv5_chua_co_giao_dich_nao_thi_khong_bao_im_lang(db):
    """Hệ thống mới dựng chưa có đồng nào là chuyện bình thường, không phải hỏng. Báo ở đây là dạy
    người dùng bỏ qua cảnh báo ngay từ ngày đầu."""
    from app.services import ks_tien_vao as TV
    from app.models.payments import BankTransaction
    _khai("co-webhook-key", "co-api-token")
    db.query(BankTransaction).delete(); db.commit()
    assert "tien_vao#im_lang" not in _ma(TV.quet(db))


def test_tv6_khong_goi_ra_sepay(db):
    """Vòng quét robot chạy mỗi phút. Gọi ra ngoài mỗi phút là tự tạo một nguồn hỏng mới và tự làm
    chậm chính vòng quét. Việc gọi thật để thử đường truyền nằm ở màn hình có người bấm."""
    from app.services import ks_tien_vao as TV
    from app.services import sepay as SP
    goi = []
    for ten in ("list_transactions", "bank_accounts"):
        if hasattr(SP, ten):
            setattr(SP, ten, lambda *a, _t=ten, **k: goi.append(_t))
    _khai("co-webhook-key", "co-api-token")
    TV.quet(db)
    assert not goi, f"phép kiểm đã gọi ra SePay: {goi}"


def test_tv7_da_gan_vao_vong_quet_va_khai_dung_loai():
    from app.services.ks_robot import BO_KIEM
    from app.services.ks_tien_vao import _hai_duong_tien_vao
    from app.models.kiem_soat import LOAI_PHAT_HIEN
    assert _hai_duong_tien_vao in BO_KIEM
    for k in ("tien_vao_thieu_duong", "tien_vao_im_lang"):
        assert k in LOAI_PHAT_HIEN
