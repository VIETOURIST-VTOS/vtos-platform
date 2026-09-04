# VTOS – Vietourist Operating System

Hệ thống quản trị nội bộ Vietourist Holdings, lập trình theo **bộ chính sách 27/8/2026** và **Văn bản đính chính** (tài liệu thiết kế VTOS v1.7). Một mã nguồn cho ba mặt: **Web** (PWA, cài được trên điện thoại), **App** (vỏ Android/iOS bọc web), **API** (FastAPI) trên **PostgreSQL**.

```
vtos-platform/
├── backend/        API FastAPI · SQLAlchemy 2 · Alembic · JWT · pytest        → http://localhost:8000/api/docs
├── web/            Next.js 14 (TypeScript) · PWA (manifest + service worker)  → http://localhost:3000
├── mobile/         Capacitor (Android/iOS) trỏ tới bản web – build khi có tên miền
├── infra/          Caddy (HTTPS tự động theo DOMAIN) · n8n workflow robot · sao lưu
├── docs/           kiến trúc, ảnh màn hình
├── docker-compose.yml        chạy thử trên máy
├── docker-compose.prod.yml   chạy thật trên VPS với tên miền
└── .github/workflows/ci.yml  kiểm thử tự động khi đẩy lên GitHub
```

## 1. Chạy thử trên máy

```bash
cp .env.example .env
docker compose up -d --build      # db + api + web (thêm --profile auto để có n8n)
# Web: http://localhost:3000 · API docs: http://localhost:8000/api/docs
```
Tài khoản mẫu (mật khẩu `123456`): `chutich`, `tgd`, `ptgd.doan`, `ptgd.mkt`, `tp.dieuhanh`, `dh.lan`, `dh.minh`, `gd.kd`, `kd.hoa`, `kd.tuan`, `ketoan`, `hcns`, `cntt`, `bks`. Đặt `SEED_DEMO=0` khi bắt đầu dùng dữ liệu thật.

Phát triển không dùng Docker: `cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload` và `cd web && npm install && npm run dev`.

## 2. Đưa lên GitHub và chạy thật với tên miền

```bash
git init && git add . && git commit -m "VTOS 0.2 – web + app + api + db"
git remote add origin git@github.com:<org>/vtos-platform.git && git push -u origin main
```
Trên VPS (Ubuntu, đã cài Docker, trỏ DNS `A` của `<domain>` và `n8n.<domain>` về IP máy chủ):
```bash
git clone git@github.com:<org>/vtos-platform.git && cd vtos-platform
cp .env.example .env    # điền DOMAIN, ACME_EMAIL, DB_PASSWORD, SECRET_KEY, ROBOT_TOKEN, SEED_DEMO=0
docker compose -f docker-compose.prod.yml up -d --build          # Caddy tự lấy HTTPS
docker compose -f docker-compose.prod.yml --profile auto up -d   # thêm n8n + sao lưu hằng ngày
```
Cập nhật phiên bản: `git pull && docker compose -f docker-compose.prod.yml up -d --build` (API tự chạy `alembic upgrade head`).

## 3. Những gì đã lập trình (giai đoạn 1 – lõi nghiệp vụ)

| Cổng / quy tắc | Nguồn chính sách | Nơi thực thi |
|---|---|---|
| Ba con số dự toán, điểm dừng nghỉ | ĐH Điều 2, 11 | `backend/app/services/rules.py::calc`, `tours.py::submit` |
| Biên 10% – dưới ngưỡng chặn, giải trình 4 mục, 2 chữ ký Chủ tịch + TGĐ | MHQT Điều 10; ĐC Điều 4 | `tours.py::submit/approve` |
| Lẻ → TGĐ duyệt; đoàn → PTGĐ tour đoàn | ĐC Điều 4 | `rules.py::approver_role` |
| Mã KM làm biên tụt <10% → chặn – treo | MKT 7; ĐC Điều 2–3 | `tours.py::create_booking` |
| Bốn trường bắt buộc; booking do Điều hành tạo ≤ 2 giờ | KD Lẻ 2; ĐH 2 | `tours.py::create_request/create_booking` |
| Hạn quyết toán đoàn 7 / lẻ 3 ngày; một cửa; KT xác nhận; CNTT đối chiếu và khóa | MHQT 10; ĐC Điều 1 | `tours.py::close/kt_confirm/cntt_check` |
| D-7 chuyến dưới hòa vốn; chạy tiếp cần Chủ tịch | ĐH 13 | `rules.py::run_robots`, `tours.py::d7` |
| Đoàn: chặn dự toán vẫn áp, thưởng không phụ thuộc biên; quá hạn mất thưởng | ĐC Điều 7–8 | `rules.py::settlement_summary` |
| Tham số hiệu lực theo ngày, đổi phải đủ 2 chữ ký | MHQT Điều 1, 15 | `routes.py` (params) |
| Nhật ký bất biến hash-chain, kiểm tra toàn vẹn | MHQT 10 | `rules.py::audit/verify_chain` |
| Bảng lương nháp (quỹ ĐH 2/1/1% chia 70/30; hoa hồng đoàn 10% × (LN − 20tr)) | ĐH 5–6; Đoàn 7 | `rules.py::monthly_payroll_draft` |

Giai đoạn 2 (chưa có): kế toán TT99 + hóa đơn điện tử, SePay/thu tiền, thang f – thang giảm lương – visa – HDV – Đội xe, báo cáo ngày, ca trực page, thông báo đẩy.

## 4. Kiểm thử

```bash
cd backend && pytest -q          # 9 kịch bản cổng chặn qua API
cd web && npm run build          # kiểm tra TypeScript + build
```
CI trên GitHub chạy cả hai và build Docker mỗi lần đẩy mã.

## 5. API cho robot / n8n

`POST /api/v1/robot/run`, `GET /api/v1/robot/alerts`, `GET /api/v1/robot/tours` với header `X-Robot-Token`. Workflow mẫu: `infra/n8n/robot_canh_bao.json`. Tài liệu đầy đủ tại `/api/docs`.

## 6. Bảo mật tối thiểu trước khi chạy thật

Đổi `SECRET_KEY`, `ROBOT_TOKEN`, `DB_PASSWORD`; `SEED_DEMO=0`; đổi mật khẩu mọi tài khoản (`POST /api/v1/auth/password`); chỉ mở cổng 80/443 trên VPS; bật profile `auto` để sao lưu hằng ngày vào `infra/backups/`.
