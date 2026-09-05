# Triển khai VTOS trên tên miền infinitytours.org

## Địa chỉ dự kiến
| Dịch vụ | Địa chỉ | Ghi chú |
|---|---|---|
| Web + API | https://vtos.infinitytours.org | Caddy tự cấp HTTPS; `/api/*` → FastAPI |
| n8n (robot) | https://n8n.vtos.infinitytours.org | chỉ bật profile `auto`; nên chặn IP |
| App Android/iOS | mở https://vtos.infinitytours.org | `mobile/capacitor.config.ts` |

Tên miền gốc `infinitytours.org` để trống cho website bán hàng sau này (không đụng tới VTOS).

## Bản ghi DNS cần tạo tại halink.vn (mục Quản lý DNS của tên miền)
| Loại | Tên (host) | Giá trị | TTL |
|---|---|---|---|
| A | `vtos` | IP máy chủ VPS | 300 |
| A | `n8n.vtos` | IP máy chủ VPS | 300 |

Chưa có VPS thì chưa tạo được bản ghi. Gợi ý VPS trong nước (độ trễ thấp, xuất hóa đơn VAT): 2 vCPU · 4 GB RAM · 60 GB SSD · Ubuntu 22.04 – đủ cho ~110 người dùng.

## Các bước trên VPS (10 phút)
```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/<org>/vtos-platform.git && cd vtos-platform
cp .env.example .env
#   ENV=prod · SEED_DEMO=0 · DOMAIN=vtos.infinitytours.org
#   SECRET_KEY=$(openssl rand -hex 32) · ROBOT_TOKEN=$(openssl rand -hex 16) · DB_PASSWORD=<mật khẩu mạnh>
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml --profile auto up -d     # n8n + sao lưu hằng ngày
```
Sau 1–2 phút mở https://vtos.infinitytours.org. Tạo tài khoản thật: `SEED_DEMO=0` rồi thêm người dùng qua API `/api/docs` (giai đoạn 2 sẽ có màn hình quản lý người dùng).

## GitHub
Repo đề xuất: `vietourist/vtos-platform` (private). Sau khi tạo repo trống trên GitHub:
```bash
git remote add origin git@github.com:vietourist/vtos-platform.git
git push -u origin main
```
CI (`.github/workflows/ci.yml`) tự chạy pytest, build web, build Docker ở mỗi lần push.

## Bản demo đang chạy trên web (05/9/2026 – gói miễn phí)
| Thành phần | Địa chỉ | Nền tảng |
|---|---|---|
| Web | https://vtos-platform.vercel.app | Vercel (team infinis-pathway, root `web`, env `API_INTERNAL_URL`) |
| API | https://vtos-api.onrender.com/api/docs | Render (Blueprint `render.yaml`, Docker, Singapore) |
| PostgreSQL | vtos-db (Render free, hết hạn sau 90 ngày) | Render |

Tự động: mỗi lần push `main` lên GitHub, Vercel và Render đều build lại. Gói free của Render ngủ sau 15 phút không dùng → lần mở đầu chậm ~30–50 giây. Muốn gắn `vtos.infinitytours.org` ngay: Vercel → Project → Domains → thêm domain, rồi tạo bản ghi CNAME `vtos` → `cname.vercel-dns.com` tại halink.
