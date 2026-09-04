# Kiến trúc VTOS 0.2

```
Điện thoại / máy tính ──HTTPS──▶ Caddy (domain, TLS) ──┬─▶ web  (Next.js, PWA)  /
                                                        └─▶ api  (FastAPI)       /api/*
App Android/iOS (Capacitor) ──▶ cùng địa chỉ web            │
n8n (robot, lịch 30 phút) ──X-Robot-Token──▶ /api/v1/robot/* │
                                                     PostgreSQL 16 ◀─┘  (Alembic quản lý schema)
```

Lớp trong API: `api/v1/routes.py` (HTTP) → `services/tours.py` (nghiệp vụ, cổng chặn) → `services/rules.py` (rules engine, hash-chain, robot) → `models/core.py` (bảng). Mọi thao tác nghiệp vụ ghi `audit_log` (SHA-256 nối chuỗi); tham số chính sách đọc theo ngày hiệu lực (`get_param(key, on)`), không hard-code trong mã.

Bảng: users · tours · service_requests · bookings · params · alerts · audit_log.
