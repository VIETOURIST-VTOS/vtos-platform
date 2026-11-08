# Sổ giữ chỗ — làn Phân quyền · Đợt CI-4

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **CI-4 — VIỆC BACKEND CHIA BỐN MÁY CHẠY SONG SONG** (Chủ tịch 08/11/2026 chọn «Chia 4 máy chạy song song»). Việc `backend` chạy lần lượt 619 tệp trên một máy: 1 giờ 8 phút (sau #726) → 1 giờ 28 phút (sau #728) → vượt hạn 90 phút, bị huỷ (PR #731) — không báo được xanh hay đỏ. Sửa: `strategy.matrix.phan: [0,1,2,3]`, `run_all.sh` chọn tệp thứ i khi i % 4 == phần; không đặt biến thì chạy hết như cũ. Phép thử canh bốn phần phủ đủ, không trùng, đều nhau. | .github/workflows/ci.yml, backend/tests/run_all.sh, backend/tests/test_ci4_chia_bon_phan.py, docs/dang-lam/phan-quyen/CI-4.md | 08-11-2026 09:40 | đang làm |
