-- =====================================================================
-- V9 ĐỢT 3 – ĐẾM PHẦN LẺ DƯỚI ĐỒNG, CHẠY TRƯỚC KHI ĐỔI KIỂU CỘT
-- Soạn 09/9/2026. Chỉ ĐỌC, không ghi gì – chạy được lúc hệ thống đang phục vụ.
--
-- VÌ SAO PHẢI CHẠY TRƯỚC:
--   numeric(18,2) giữ đúng hai chữ số thập phân. Giá trị đang có chữ số thứ ba
--   trở đi sẽ bị LÀM TRÒN lúc đổi kiểu, và đó là thay đổi KHÔNG QUAY LẠI ĐƯỢC:
--   hạ cấp khôi phục KIỂU, không khôi phục SỐ.
--   Đếm sau khi đã đổi thì luôn ra 0 – vì cột mới không giữ nổi chữ số thứ ba –
--   nên nó không chứng minh được gì. Cửa sổ chỉ mở MỘT LẦN, trước khi đổi.
--
-- CÁCH ĐỌC KẾT QUẢ:
--   so_dong_co_le = 0 ở mọi dòng  → đổi kiểu là phép biến đổi không mất gì.
--   khác 0         → đúng số dòng ấy sẽ bị làm tròn. Phải xem từng cột và
--                    quyết trước, không đổi rồi mới xem.
--
-- Truy vấn tự tìm MỌI cột số thực nhị phân trong cơ sở dữ liệu, không đọc từ
-- một danh sách chép tay: danh sách chép tay thì cột thêm sau sẽ lọt.
-- =====================================================================

SELECT c.table_name || '.' || c.column_name AS cot,
       (xpath('/row/c/text()', query_to_xml(
          format('SELECT COUNT(*) AS c FROM public.%I WHERE %I IS NOT NULL AND %I*100 <> ROUND(%I::numeric*100)',
                 c.table_name, c.column_name, c.column_name, c.column_name),
          false, true, '')))[1]::text::bigint AS so_dong_co_le
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema
 AND t.table_name  = c.table_name
 AND t.table_type  = 'BASE TABLE'
WHERE c.table_schema = 'public'
  AND c.data_type IN ('double precision', 'real')
ORDER BY 2 DESC, 1;


-- ---------------------------------------------------------------------
-- BẢN RÚT GỌN – chỉ trả về MỘT con số: tổng số dòng sẽ bị làm tròn.
-- Ra 0 nghĩa là toàn bộ cơ sở dữ liệu không có dòng nào mất số khi đổi kiểu.
-- ---------------------------------------------------------------------

SELECT COALESCE(SUM(n), 0) AS tong_so_dong_se_bi_lam_tron
FROM (
  SELECT (xpath('/row/c/text()', query_to_xml(
            format('SELECT COUNT(*) AS c FROM public.%I WHERE %I IS NOT NULL AND %I*100 <> ROUND(%I::numeric*100)',
                   c.table_name, c.column_name, c.column_name, c.column_name),
            false, true, '')))[1]::text::bigint AS n
  FROM information_schema.columns c
  JOIN information_schema.tables t
    ON t.table_schema = c.table_schema
   AND t.table_name  = c.table_name
   AND t.table_type  = 'BASE TABLE'
  WHERE c.table_schema = 'public'
    AND c.data_type IN ('double precision', 'real')
) x;
