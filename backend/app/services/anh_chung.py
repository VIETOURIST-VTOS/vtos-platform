# -*- coding: utf-8 -*-
"""TR-8 (13/11/2026) · LÕI XỬ LÝ ẢNH DÙNG CHUNG CHO MỌI CỔNG KHÁCH.

VÌ SAO TÁCH TỆP NÀY RA. Album ảnh nhà hàng (AT-2a, 29/10/2026) đã giải xong những bài khó của
việc đưa ảnh ra internet: thu nhỏ hai cỡ, xoay theo EXIF rồi XOÁ EXIF, giải mã tiết kiệm bộ nhớ
cho máy 512 MB, chặn tệp không phải ảnh. Khi cổng tour cần đúng những thứ ấy, có hai đường:
chép 100 dòng sang một tệp mới, hay tách phần lõi ra dùng chung.

Chép thì công ty có HAI bộ xử lý ảnh. Sáu tháng sau sửa một lỗi ở một bên, bên kia vẫn sai, và
không ai nhớ là có hai bên. Nên tách.

ĐIỀU QUAN TRỌNG NHẤT TRONG TỆP NÀY — XOÁ EXIF. Ảnh chụp bằng điện thoại mang theo toạ độ GPS,
giờ chụp, số máy. Đưa thẳng ra `kh.vietourist.vn` là công bố những thứ ấy cho bất kỳ ai tải ảnh
về. `ImageOps.exif_transpose` xoay ảnh cho đúng chiều rồi bản WEBP ghi ra KHÔNG mang EXIF nữa.

Tệp này KHÔNG biết gì về nhà hàng hay tour — không chạm cơ sở dữ liệu, không kiểm quyền. Nó
nhận bytes, trả bytes. Luật nghiệp vụ nằm ở `nha_hang.py` và `anh_tour.py`.
"""

KIEU_ANH = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
CANH_HIEN, CANH_NHO = 1600, 480
TOI_DA_MB = 10

# Căn cứ quyền dùng ảnh — dùng chung mọi cổng. Khác nhau ở chỗ CHỦ THỂ cấp quyền, nên mỗi cổng
# tự đặt nhãn cho dòng đầu (nhà hàng cấp / đối tác cấp), còn ba dòng sau giống nhau.
CAN_CU_CHUNG = {"vtd_chup": "VTD tự chụp", "ben_thu_ba": "Bên thứ ba cấp phép",
                "chua_xac_minh": "Chưa xác minh"}
TRANG_THAI_CHUNG = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "da_duyet": "Đã duyệt", "an": "Ẩn"}


def co_pil() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def duoi_anh(ten_tep: str) -> str:
    """Đuôi tệp viết thường, rỗng nếu không có. KHÔNG tin đuôi là thật — chỉ dùng để chọn kiểu."""
    t = ten_tep or ""
    return t.rsplit(".", 1)[-1].lower() if "." in t else ""


def loi_kiem_tep(ten_tep: str, data: bytes) -> str:
    """Trả CÂU LỖI nếu tệp không nhận được, rỗng nếu được.

    Trả chuỗi chứ không ném lỗi, vì mỗi cổng có lớp lỗi riêng (LoiNhaHang / LoiTour) và câu lỗi
    phải đi ra đúng lớp ấy để giao diện bắt được.
    """
    if not data:
        return "Chọn tệp ảnh"
    if duoi_anh(ten_tep) not in KIEU_ANH:
        return "Chỉ nhận ảnh JPG / PNG / WEBP (ảnh HEIC của iPhone: xuất lại JPG)"
    mb = len(data) / 1024 / 1024
    if mb > TOI_DA_MB:
        return f"Ảnh nặng {mb:.1f} MB, quá {TOI_DA_MB} MB — xuất lại ảnh nhẹ hơn"
    return ""


def lam_nhe(data: bytes) -> tuple[bytes | None, bytes | None, int, int]:
    """Bản hiển thị (≤1600px) và ảnh nhỏ (≤480px), WEBP, xoay theo EXIF rồi BỎ EXIF (vị trí GPS…).
    Không có thư viện ảnh / ảnh lỗi → (None, None, 0, 0): bên gọi giữ bản gốc hoặc báo lỗi."""
    try:
        from io import BytesIO
        from PIL import Image, ImageOps
    except Exception:
        return None, None, 0, 0
    try:
        im = Image.open(BytesIO(data))
        if (im.format or "").upper() == "JPEG":
            im.draft("RGB", (CANH_HIEN * 2, CANH_HIEN * 2))        # giải mã thu nhỏ: đỡ bộ nhớ máy chủ 512 MB
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
        rong, cao = im.size
        ra = []
        for canh, q in ((CANH_HIEN, 82), (CANH_NHO, 76)):
            b = im.copy()
            b.thumbnail((canh, canh))
            o = BytesIO()
            b.save(o, "WEBP", quality=q, method=4)
            ra.append(o.getvalue())
        return ra[0], ra[1], rong, cao
    except Exception:
        return None, None, 0, 0
