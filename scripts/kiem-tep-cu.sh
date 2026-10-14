#!/usr/bin/env bash
# ============================================================================
# VG-1 · CHẶN ĐẨY MỘT TỆP CŨ ĐÈ LÊN BẢN MỚI
#
# VÌ SAO CÓ TỆP NÀY. Vòng đẩy commit NGUYÊN TỆP từ đĩa lên một gốc vừa fetch.
# Nên nếu tệp trên đĩa là bản cũ của chính nó, lần đẩy ấy XOÁ SẠCH mọi sửa đổi
# của làn khác trên tệp đó — âm thầm, vì đẩy nguyên tệp thì không có xung đột
# nào để git báo. Đã xảy ra 19/9, 23/9/2026, và suýt nữa 14/10/2026.
#
# HÀNG RÀO ĐÃ CÓ VÀ CHỖ NÓ CÒN HỞ. `VONG_DAY.bat` đếm số dòng bị xoá và bắt
# khai trước trong `VONG_XOA.txt`. Chú thích của chính nó gọi con số ấy là
# "một LỜI HỨA". Lời hứa thì khai bao nhiêu cũng qua: một làn tính VONG_XOA
# TỪ CHÍNH tệp cũ sẽ khai đúng số lớn ấy rồi đi thẳng qua cửa.
#
# TỆP NÀY HỎI MỘT CÂU KHÔNG CẦN LỜI HỨA: bản trên đĩa có phải là một bản CŨ
# NGUYÊN SI của chính tệp ấy không? Trùng từng byte với một bản trong lịch sử
# của đúng đường dẫn đó thì gần như chắc chắn là tệp cũ, không phải trùng hợp.
#
# KHÔNG thay hàng rào đếm dòng — hai cái hỏi hai câu khác nhau:
#   · đếm dòng : "vòng này xoá bao nhiêu, có khai không"
#   · tệp này  : "cái anh sắp đẩy có phải bản cũ của chính nó không"
# Sửa cố ý một tệp MỚI NHẤT thì tệp này im; lấy nhầm bản cũ thì nó kêu, dù
# VONG_XOA có khai đúng số đến đâu.
#
# DÙNG:
#   scripts/kiem-tep-cu.sh [GOC] [tệp...]
#   GOC mặc định origin/main. Không truyền tệp thì đọc VONG_TEP.txt ở thư mục
#   đang chạy (bỏ dòng trống và dòng bắt đầu bằng #).
#
# TRẢ VỀ: 0 = sạch · 1 = có tệp cũ (ĐỪNG ĐẨY) · 2 = gọi sai
# ============================================================================
set -u

GOC="${1:-origin/main}"; shift || true

if [ "$#" -gt 0 ]; then
  TEP=("$@")
elif [ -f VONG_TEP.txt ]; then
  mapfile -t TEP < <(grep -v '^[[:space:]]*#' VONG_TEP.txt | grep -v '^[[:space:]]*$')
else
  echo "kiem-tep-cu: không có tệp nào để kiểm (truyền đường dẫn, hoặc đặt VONG_TEP.txt cạnh đây)" >&2
  exit 2
fi

git rev-parse --verify --quiet "$GOC" >/dev/null || {
  echo "kiem-tep-cu: không đọc được gốc '$GOC'" >&2; exit 2; }

CU=0
for f in "${TEP[@]}"; do
  [ -f "$f" ] || { echo "  ? $f — không có trên đĩa (vòng đẩy sẽ tự dừng)"; continue; }

  dia=$(git hash-object "$f")
  moi=$(git rev-parse --verify --quiet "$GOC:$f" || true)

  if [ -z "$moi" ]; then
    echo "  + $f — tệp mới, chưa có trên $GOC"; continue
  fi
  if [ "$dia" = "$moi" ]; then
    echo "  = $f — đúng bản $GOC"; continue
  fi

  # Khác bản mới. Nó có trùng nguyên si một bản CŨ của chính đường dẫn này không?
  trung=""
  while read -r sha; do
    [ -n "$sha" ] || continue
    [ "$(git rev-parse --verify --quiet "$sha:$f" || true)" = "$dia" ] && { trung="$sha"; break; }
  done < <(git log --format=%H "$GOC" -- "$f")

  if [ -n "$trung" ]; then
    ngay=$(git show -s --format=%ad --date=short "$trung")
    echo "  ✗ $f — LÀ BẢN CŨ NGUYÊN SI, của commit $(git rev-parse --short "$trung") ngày $ngay"
    CU=$((CU+1))
  else
    echo "  ~ $f — đã sửa trên nền nào đó, không trùng bản cũ nào (được)"
  fi
done

if [ "$CU" -gt 0 ]; then
  cat >&2 <<MSG

================== DỪNG LẠI — $CU TỆP TRÊN ĐĨA LÀ BẢN CŨ ==================
Đẩy nguyên tệp những bản này lên là XOÁ SẠCH phần làn khác đã sửa trên chúng
kể từ ngày ghi ở trên, và git sẽ KHÔNG báo một chữ xung đột nào.

Cách xử, cho từng tệp ✗ ở trên:
    git show $GOC:<tệp> > <tệp>      # lấy bản mới về đĩa
rồi vá lại phần của mình LÊN TRÊN bản ấy, và chạy lại lệnh kiểm này.

Nếu thật sự CỐ Ý quay một tệp về bản cũ, ghi rõ lý do vào dòng sổ của làn rồi
chạy lại với biến môi trường  VG1_CO_Y=1  — và chỉ làm vậy khi đã nhìn
`git diff $GOC -- <tệp>` từng dòng một.
MSG
  [ "${VG1_CO_Y:-}" = "1" ] && { echo "(VG1_CO_Y=1 — bỏ qua theo khai báo cố ý)" >&2; exit 0; }
  exit 1
fi

echo "kiem-tep-cu: sạch — không tệp nào là bản cũ."
exit 0
