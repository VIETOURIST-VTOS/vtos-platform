"""KS-DG (08/11/2026) — gọi máy chủ qua `api()` thì KHÔNG viết lại tiền tố `/api/v1`.

`lib/api.ts` tự ghép `/api/v1` vào trước mọi đường dẫn. Chủ tịch cho rà 75 màn hình của bốn phân hệ
Marketing, Kinh doanh, Điều hành, HCNS (08/11/2026): thẻ «Đánh giá & sự vụ» ở trang Nhân sự gọi
`api("/api/v1/danh-gia-ns…")` → thành `/api/v1/api/v1/danh-gia-ns` → 404, bảng đánh giá nhân viên
không bao giờ tải được. Phép thử này quét cả giao diện để lỗi ấy không quay lại ở chỗ khác.
"""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
MAU = re.compile(r"""\bapi(?:<[^>]*>)?\(\s*[`"']/api/v1""")


def test_ks_dg_1_khong_cho_nao_goi_api_voi_tien_to_lap():
    sai = []
    for thu_muc in ("app", "components", "lib"):
        for p in (WEB / thu_muc).rglob("*.ts*"):
            src = p.read_text(encoding="utf-8")
            for m in MAU.finditer(src):
                sai.append(f"{p.relative_to(WEB)}:{src[:m.start()].count(chr(10)) + 1}")
    assert not sai, f"Gọi api() với '/api/v1' viết lại — thành /api/v1/api/v1/… và 404: {sai}"


def test_ks_dg_2_the_danh_gia_goi_dung_duong():
    src = (WEB / "components" / "DanhGiaNhanSu.tsx").read_text(encoding="utf-8")
    assert "`/danh-gia-ns?ky_loai=" in src and "/api/v1/danh-gia-ns" not in src
