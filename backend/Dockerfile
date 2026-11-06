FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# `tzdata` KHÔNG phải tuỳ chọn — Đợt KS-18, 21/10/2026.
# `render.yaml` khai `TZ: Asia/Ho_Chi_Minh`, nhưng ảnh `slim` của Debian không mang
# `/usr/share/zoneinfo`. Thiếu tệp ấy thì thư viện C đọc `Asia/Ho_Chi_Minh` thành lệch 0 giờ
# và KHÔNG báo lỗi, nên máy chủ lặng lẽ chạy theo UTC: mỗi ngày từ 00h tới 07h giờ Việt Nam,
# mọi chữ "hôm nay" trong hệ thống lùi lại một ngày. Phép thử `test_ks18` canh dòng này.
# `fonts-dejavu-core` — Đợt KS-20e, 07/11/2026: phông có đủ dấu tiếng Việt để in phiếu xác nhận / hóa đơn
# đặt phòng VTD ra PDF (app/services/phieu_ks_vtd.py). Thiếu thì máy báo 503 «thiếu phông chữ», không in chữ vỡ.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 tzdata fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
