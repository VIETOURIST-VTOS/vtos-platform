#!/usr/bin/env bash
# ============================================================================
# KS-10 · CỔNG CHỐNG ĐO TRÊN MỘT BẢN SAO ĐÃ CŨ
#
# VÌ SAO CÓ TỆP NÀY. Ngày 17/10/2026 cùng một kiểu sai xảy ra HAI LẦN trong
# một ngày, và cả hai đều do đọc `origin/main` trong bản sao trên máy mà
# không biết bản sao ấy đã đứng yên từ bao giờ:
#
#   · lần 1 — báo "bộ hàng rào có 3–4 đỏ sẵn có trên main". Sai. Cây làm việc
#     chung đã cũ; xuất sạch từ main ra thì cả bộ xanh.
#   · lần 2 — báo "hệ thật đang chạy mã CHƯA DUYỆT", vì quét 379 nhánh trong
#     bản sao và thấy trường `code` chỉ có trên nhánh chưa gộp của mình. Nhánh
#     ấy đã được Chủ tịch gộp (#382) một giờ trước; bản sao không nhìn thấy.
#
# Cả hai lần công cụ lấy main ĐÃ CÓ SẴN (`ZZ-LAY-MAIN.bat`). Thiếu không phải
# là công cụ — thiếu là một tiếng kêu. Bản sao cũ trả lời mọi câu hỏi bằng một
# giọng y hệt bản sao mới, nên người đo không có cách nào biết mình đang đo
# trên cái gì.
#
# NÊN CỔNG NẰM BÊN TRONG LỆNH ĐO, KHÔNG ĐỨNG CẠNH NÓ. Một lệnh soát riêng là
# thứ quên bấm được — đúng cái đã hỏng hai lần. Lệnh này vừa chặn vừa in số:
# muốn có con số "thêm bao nhiêu / xoá bao nhiêu so với main" thì phải đi qua
# cổng, không có đường vòng.
#
# HAI CÁCH BẢN SAO NÓI DỐI, VÀ CẢ HAI ĐỀU BỊ CHẶN Ở ĐÂY
#
# (1) LẤY MAIN ĐÃ LÂU. `.git/FETCH_HEAD` mang giờ của lần fetch gần nhất.
#     Quá ngưỡng thì từ chối.
#
# (2) LẦN LẤY MAIN GẦN NHẤT THẤT BẠI — và đây là chỗ nguy hiểm hơn hẳn. ĐO
#     ĐƯỢC 17/10/2026: gọi `git fetch` từ máy ảo cầu nối (không có giấy phép
#     đăng nhập) báo lỗi `could not read Username for 'https://github.com'`,
#     NHƯNG VẪN CẮT `FETCH_HEAD` VỀ 0 BYTE và đặt lại giờ sửa tệp. Tức là một
#     lần fetch HỎNG làm bản sao TRÔNG NHƯ VỪA MỚI LẤY. Chỉ xét giờ thôi là
#     hàng rào này tự thủng đúng ở trường hợp tệ nhất. Nên phải xét cả KÍCH
#     THƯỚC: fetch chạy được thì ghi ít nhất một dòng vào FETCH_HEAD.
#
# (3) TỆP CHƯA ĐƯỢC GIT THEO DÕI. `git diff origin/main -- <tệp>` bỏ qua tệp
#     chưa theo dõi và báo nó như ĐÃ BỊ XOÁ SẠCH — sáng 17/10 nó báo sổ giữ
#     chỗ "0 thêm / 21 xoá" trong khi tệp nằm nguyên trên đĩa với 23 dòng.
#     Nên ở đây so bằng `git diff --no-index` giữa bản của main và bản trên
#     đĩa, và cách ấy đúng cho cả ba loại: đã theo dõi, chưa theo dõi, và tệp
#     mới chưa từng có trên main.
#
# CÁCH DÙNG
#     bash cong-cu/so-voi-main.sh                      # chỉ soát độ mới
#     bash cong-cu/so-voi-main.sh tệp1 tệp2 ...        # soát rồi in số
#
# MÃ THOÁT: 0 qua cổng · 2 bản sao cũ hoặc lần lấy main hỏng · 3 gọi sai.
#
# NGƯỠNG: 20 phút (Chủ tịch chốt 17/10/2026). Các làn gộp PR vài chục phút một
# lần; chính ngày hôm ấy main đổi hai lần trong một giờ, nên ngưỡng 60 phút sẽ
# KHÔNG bắt được lần sai thứ hai. Đổi ngưỡng thì đổi ở đây, và `GIAY_TOI_DA`
# đọc được từ môi trường chỉ để phép thử dựng được cảnh cũ — không phải cửa
# cho người đo tự nới.
# ============================================================================
set -u

GIAY_TOI_DA="${SO_VOI_MAIN_NGUONG_GIAY:-1200}"

goc="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "KHÔNG PHẢI KHO GIT: chạy lệnh này từ trong kho vtos-platform." >&2
    exit 3
}
cd "$goc" || exit 3

chung="$(git rev-parse --git-common-dir)"
case "$chung" in /*) ;; *) chung="$goc/$chung" ;; esac
FH="$chung/FETCH_HEAD"

# ─── CỔNG ───────────────────────────────────────────────────────────────────
if [ ! -f "$FH" ]; then
    echo "CHƯA LẤY MAIN LẦN NÀO trong bản sao này ($FH không có)." >&2
    echo "Bấm ZZ-LAY-MAIN.bat ở gốc kho rồi chạy lại." >&2
    exit 2
fi

nay="$(date +%s)"
luc="$(date -r "$FH" +%s 2>/dev/null || stat -c %Y "$FH")"
tuoi=$(( nay - luc ))
phut=$(( tuoi / 60 ))

if [ ! -s "$FH" ]; then
    echo "LẦN LẤY MAIN GẦN NHẤT THẤT BẠI — và nó đã làm bản sao TRÔNG NHƯ MỚI." >&2
    echo "  $FH rỗng (0 byte), sửa lần cuối ${phut} phút trước." >&2
    echo "  Một lần fetch hỏng vẫn đặt lại giờ của tệp này, nên giờ ấy KHÔNG" >&2
    echo "  nói lên điều gì. Thường là gọi git fetch từ máy ảo cầu nối, nơi" >&2
    echo "  không có giấy phép đăng nhập GitHub." >&2
    echo "  Bấm ZZ-LAY-MAIN.bat trên máy thật rồi chạy lại." >&2
    exit 2
fi

if [ "$tuoi" -gt "$GIAY_TOI_DA" ]; then
    echo "BẢN SAO ĐÃ CŨ: lấy main lần cuối ${phut} phút trước (ngưỡng $(( GIAY_TOI_DA / 60 )) phút)." >&2
    echo "  origin/main trong bản sao này: $(git rev-parse --short origin/main 2>/dev/null || echo 'không có')" >&2
    echo "  Con số đo ra lúc này KHÔNG dùng để báo cáo được." >&2
    echo "  Bấm ZZ-LAY-MAIN.bat ở gốc kho rồi chạy lại." >&2
    exit 2
fi

echo "=== ĐỘ MỚI CỦA BẢN SAO ==="
echo "lấy main lần cuối : ${phut} phút trước"
echo "origin/main       : $(git log --oneline -1 origin/main)"

[ "$#" -eq 0 ] && exit 0

# ─── ĐO ─────────────────────────────────────────────────────────────────────
tam="$(mktemp -d)"
trap 'rm -rf "$tam"' EXIT
tong_xoa=0
echo
echo "=== THÊM / XOÁ TỪNG TỆP (so với origin/main) ==="
for t in "$@"; do
    if [ ! -e "$t" ]; then
        echo "  THIẾU TRÊN ĐĨA: $t" >&2
        continue
    fi
    cu="$tam/cu"
    if git cat-file -e "origin/main:$t" 2>/dev/null; then
        git show "origin/main:$t" > "$cu"
    else
        : > "$cu"                      # tệp mới, chưa từng có trên main
    fi
    so="$(git diff --no-index --numstat "$cu" "$t" 2>/dev/null | head -1)"
    them="$(printf '%s' "$so" | awk '{print $1}')"; them="${them:-0}"
    xoa="$(printf '%s' "$so" | awk '{print $2}')"; xoa="${xoa:-0}"
    printf '  thêm %-6s xoá %-6s %s\n' "$them" "$xoa" "$t"
    tong_xoa=$(( tong_xoa + xoa ))
done
echo "TỔNG DÒNG BỊ XOÁ : $tong_xoa   ← con số khai vào VONG_XOA.txt"
echo
echo "ĐỌC TỪNG DÒNG BỊ XOÁ TRƯỚC KHI KHAI. Con số khớp không có nghĩa là xoá đúng."
