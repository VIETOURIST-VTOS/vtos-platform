# Đợt TSCD-1 — TK nguyên giá tài sản cố định có chỗ chọn (08/11/2026)

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | TSCD-1 — ô TK nguyên giá + nói ra loại tài sản thiếu tài khoản | backend/app/services/assets.py, backend/app/api/v1/assets.py, backend/app/services/intake_phong_ban_2.py, backend/tests/test_tscd1_tk_nguyen_gia_tai_san.py, backend/tests/test_assets.py, web/app/tai-san/page.tsx, backend/tests/test_ci_hang_rao_main.py, .github/workflows/ci.yml, docs/dang-lam/tc-kt/TSCD-1.md | 08-11-2026 06:40 | xong |

Đo trên hệ thống thật: `ASSET_KINDS` mời chọn BỐN loại tài sản mà chỉ MỘT lưu được — `211` là
tài khoản cha, còn `2143` / `212` / `217` không có trong danh mục. Đợt này thêm ô TK nguyên giá
(bắt buộc), nói ra loại nào thiếu tài khoản kèm đúng số hiệu cần mở, và cho hai đường nhập dùng
chung một bộ luật. KHÔNG ghi sổ gì, KHÔNG đụng bảng quyền, KHÔNG tự mở thêm tài khoản.
