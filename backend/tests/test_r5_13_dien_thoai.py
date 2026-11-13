"""R5-13 · Chủ tịch 14/11/2026: «kiểm tra và sửa giao diện trên điện thoại cho chuẩn» — duyệt bản xem trước
6 mục. Đo 390 px: tên người dùng tràn thân trang lên 433 px; 6 tab phải vuốt; bảng Đội ngũ và Chuyến cần thúc
bán bị cắt cột; biểu đồ nhịp tràn khung (khe nhãn ngày 10 px × 29); nút chạm 25–30 px. Sửa CHỈ dưới 600 px."""
import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[2]
CSS = (GOC / "web/app/globals.css").read_text(encoding="utf-8")


def _khoi_r5_13() -> str:
    i = CSS.index("R5-13 · BÀN KINH DOANH TRÊN ĐIỆN THOẠI")
    return CSS[i:]


def test_chi_sua_duoi_600px():
    k = _khoi_r5_13()
    assert k.count("@media (max-width:600px)") == 1
    assert "R5-13 · THANH ĐẦU TRÊN ĐIỆN THOẠI" in CSS


def test_sau_muc_da_duyet():
    k = _khoi_r5_13()
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in k and "min-height:42px" in k      # 2 · tab 3 × 2
    assert "min-height:40px" in k                                                               # 6 · nút chạm
    assert ".dn-bang thead{display:none}" in k and "grid-template-areas" in k                   # 3 · thẻ người
    assert ".g5-bang thead{display:none}" in k                                                  # 5 · thẻ chuyến
    assert ".bd-duong-nhanx{gap:0" in k and ".nh-khoi .bd-cham{display:none}" in k              # 4 · biểu đồ
    assert ".top .bar .who-ten{display:none}" in CSS                                            # 1 · thanh đầu


def test_o_bang_co_nhan_de_doc_tren_the():
    for f in ("BanKdKhung", "BanGdKdLe"):
        t = (GOC / f"web/components/{f}.tsx").read_text(encoding="utf-8")
        for n in ("Đã bán / chỗ mở", "Giá bán", "Hòa vốn", "Lãi mục tiêu", "Bán đủ khách"):
            assert f'data-n="{n}"' in t, (f, n)
    k = (GOC / "web/components/BanKdKhung.tsx").read_text(encoding="utf-8")
    assert re.search(r'className="c-dt" data-n="Doanh thu"', k)
