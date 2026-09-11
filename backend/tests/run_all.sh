#!/usr/bin/env bash
# Mỗi file test dùng một CSDL SQLite riêng → chạy từng tiến trình để không lẫn dữ liệu demo.
#
# CHẠY HẾT RỒI MỚI BÁO, KHÔNG DỪNG Ở TỆP ĐỎ ĐẦU TIÊN (sửa 11/9/2026)
#
# Bản trước dùng `set -e`, nên đỏ một tệp là cả vòng lặp dừng ngay tại đó. Với 156 tệp và bốn làn
# cùng viết, cái đó gây ra một kiểu hỏng khó thấy: ngày 11/9 CI đứng ở `test_lop2_quyet_toan_tour.py`,
# và khoảng bảy mươi tệp xếp sau nó theo bảng chữ cái KHÔNG hề được chạy — nhiều ngày liền. Làn nào
# viết phép thử mới mà tên tệp xếp sau chữ "lop2" thì phép thử ấy chưa bao giờ chạy trên CI, còn
# người đọc bảng CI thì chỉ thấy MỘT dòng đỏ và tưởng chỉ có một chỗ hỏng.
#
# Sửa một tệp rồi đẩy lại để lộ ra tệp đỏ tiếp theo là mỗi vòng mất một lần chạy CI. Nay chạy hết,
# gom mọi tệp đỏ, in ra một lượt ở cuối, rồi mới thoát khác 0. Hàng rào KHÔNG hề nới: đỏ một tệp là
# CI vẫn đỏ.
cd "$(dirname "$0")/.."
rm -f test_*.db

DO=()
for f in tests/test_*.py; do
  if ! python -m pytest -q "$f"; then
    DO+=("$f")
  fi
done
rm -f test_*.db

echo
echo "=============================================================================="
if [ ${#DO[@]} -eq 0 ]; then
  echo "TẤT CẢ $(ls tests/test_*.py | wc -l) TỆP PHÉP THỬ XANH"
  exit 0
fi
echo "${#DO[@]} TỆP ĐỎ trên tổng $(ls tests/test_*.py | wc -l) tệp:"
for f in "${DO[@]}"; do echo "  · $f"; done
echo "Cuộn lên để đọc chi tiết từng tệp."
echo "=============================================================================="
exit 1
