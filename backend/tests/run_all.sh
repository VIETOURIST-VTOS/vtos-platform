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

# CI-4 · 08/11/2026 — CHIA PHẦN. CI chạy bốn máy song song, mỗi máy đặt VTOS_PHAN (0..3) và
# VTOS_SO_PHAN (4); tệp thứ i (theo thứ tự tên) thuộc phần i % VTOS_SO_PHAN. Không đặt hai biến ấy
# (máy người, hộp cát) thì chạy HẾT như cũ. Cách chia theo thứ tự tên nên mỗi tệp thuộc đúng một
# phần — không tệp nào bị bỏ, không tệp nào chạy hai lần.
SO_PHAN="${VTOS_SO_PHAN:-1}"
PHAN="${VTOS_PHAN:-0}"
TEP=()
i=0
for f in tests/test_*.py; do
  if [ $((i % SO_PHAN)) -eq "$PHAN" ]; then TEP+=("$f"); fi
  i=$((i + 1))
done
echo "--- phần $PHAN / $SO_PHAN: ${#TEP[@]} trên $i tệp ---"

DO=()
for f in "${TEP[@]}"; do
  if ! python -m pytest -q "$f"; then
    DO+=("$f")
  fi
done
rm -f test_*.db

echo
echo "=============================================================================="
if [ ${#DO[@]} -eq 0 ]; then
  echo "TẤT CẢ ${#TEP[@]} TỆP PHÉP THỬ CỦA PHẦN $PHAN / $SO_PHAN XANH (tổng $i tệp)"
  exit 0
fi
echo "${#DO[@]} TỆP ĐỎ trên ${#TEP[@]} tệp của phần $PHAN / $SO_PHAN (tổng $i tệp):"
for f in "${DO[@]}"; do echo "  · $f"; done
echo "Cuộn lên để đọc chi tiết từng tệp."
echo "=============================================================================="
exit 1
