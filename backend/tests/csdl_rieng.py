# -*- coding: utf-8 -*-
"""MỘT CHỖ KHAI "SỔ RIÊNG CỦA TỆP NÀY" — Đợt DỌN-MISA 01/11/2026.

VÌ SAO CẦN. `app/db/session.py` dựng `engine` và `SessionLocal` MỘT LẦN lúc import, từ
`settings.DATABASE_URL`. Hàng rào gộp chạy nhiều tệp phép thử trong MỘT tiến trình. Nên tệp nào
import `app.main` TRƯỚC thì cơ sở dữ liệu của tệp ấy THẮNG, và mọi tệp sau đó IM LẶNG dùng chung
sổ của nó — đặt `os.environ["DATABASE_URL"]` ở dòng 3 cũng vô ích, vì lúc ấy engine đã dựng xong.

Đo được 24/10/2026: `test_ky2_tk627_va_ten_tt99` ghi bút toán kỳ 2026-05 (10.000.000 · 16.000.000
· 6.000.000); `test_misa` hỏi BCTC từ 2026-01-01 — tức ôm cả tháng 5 ấy — và lệch đúng từng đồng:
chỉ tiêu 311 chờ 2.000 nhận 11.002.000; chỉ tiêu 20 chờ 3.000 nhận -9.997.000. Không phép tính
nào sai. Đó là TIỀN CỦA TỆP KHÁC chảy sang.

Hàm này GẮN LẠI engine và SessionLocal ngay trên mô-đun `app.db.session`, nên nó có tác dụng kể
cả khi `app.main` đã import xong — miễn là gọi TRƯỚC khi `TestClient(app)` chạy vòng đời (chính
vòng đời mới là nơi tạo bảng và gieo dữ liệu).

ĐIỀU KIỆN để hàm này có tác dụng: `app/main.py` phải NHẬP MÔ-ĐUN (`from app.db import session as
_db`) chứ không nhập TÊN. Nhập tên thì tên bị buộc lúc import và gắn lại không tới được nó.
`test_donmisa_2` canh đúng chỗ ấy.
"""
import os
import tempfile


def dung_csdl_rieng(ten: str, trong_bo_nho: bool = False) -> str:
    """Cho tệp phép thử đang gọi một cơ sở dữ liệu RIÊNG. Trả về đường dẫn đã dùng.

    `ten` là tên ngắn của tệp (ví dụ "misa", "ky2"). `trong_bo_nho=True` thì dùng SQLite trong bộ
    nhớ — nhanh hơn, nhưng mỗi kết nối là một cơ sở dữ liệu khác nhau, nên chỉ hợp với tệp KHÔNG
    chạy qua `TestClient`.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db import session as S

    if trong_bo_nho:
        url = "sqlite://"
    else:
        duong = os.path.join(tempfile.gettempdir(), f"vtos_rieng_{ten}.db")
        for x in (duong, duong + "-journal"):
            try:
                if os.path.exists(x):
                    os.remove(x)
            except OSError:
                pass
        url = f"sqlite:///{duong}"

    # Giữ cho mọi nơi đọc lại về sau cũng thấy đúng một đường dẫn — nhưng KHÔNG dựa vào nó:
    # thứ thật sự có tác dụng là hai dòng gắn lại ở dưới.
    os.environ["DATABASE_URL"] = url
    try:
        from app.core.config import settings
        settings.DATABASE_URL = url
    except Exception:
        pass

    S.engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False})
    S.SessionLocal = sessionmaker(bind=S.engine, autoflush=False, expire_on_commit=False)
    return url
