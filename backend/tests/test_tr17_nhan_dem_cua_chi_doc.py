# -*- coding: utf-8 -*-
"""TR-17 · TRANG TOUR ĐỢI 3,2 GIÂY VÌ KHÔNG CÓ CHỖ NÀO ĐỆM LẠI BẢN TRẢ VỀ.

Chủ tịch hỏi còn cách nào giảm thời gian tải nữa không. Đo trang HC001 trên bản chạy
14-11-2026, đọc thẳng đồng hồ của trình duyệt chứ không ước:

    HTML về (23 KB, KHÔNG có tên tour, không có giá)          487 ms
    JS chạy xong, gọi cửa đầu tiên                          1.155 ms
    san-pham/6613 xong                                      2.641 ms
    lich-trinh/1980 xong (phải chờ cửa trên)                3.241 ms
    ảnh                                                     1.155 KB

Hỏi lại từng cửa thì ra nguyên nhân rẻ nhất: MỌI cửa đều trả

    Cache-Control: public, max-age=0, must-revalidate
    x-vercel-cache: MISS          ← ở MỌI lượt gọi, kể cả gọi lại ngay

Không có một tầng nào giữ lại bản trả về. Mỗi khách mở trang là Render chạy lại truy vấn từ
đầu. Gọi lần đầu 1.481–1.791 ms, gọi lại khi máy đã ấm còn 280–674 ms — chênh lệch ấy là
cold start, và đệm biên chữa luôn cả phần đó vì khách không chạm tới máy chủ nữa.

VÌ SAO ĐƯỢC PHÉP ĐỆM. Router này chỉ có GET, không đọc phiên, không trả gì gắn với một tài
khoản — chính lời mở tệp cong_mo.py nói vậy, và điểm VTD Rewards ở đây luôn «chưa bật». Bản
trả về giống hệt nhau cho mọi khách, nên chia chung được. Đây là điều kiện BẮT BUỘC: đệm
chung một bản trả về có đọc phiên là phát bản của người này cho người khác.

BA CỬA KHÔNG ĐƯỢC ĐỆM, và phép thử 4-5-6 canh đúng chỗ đó:
    /tour-online/tinh    giá của chính đơn khách đang đặt — sai một lượt là sai tiền
    /ks-vtd/tim          còn phòng theo ngày, đổi từng phút
    /tt-doan/{ma}        link thanh toán riêng của MỘT khách

VÒNG NÀY CHƯA CHỨNG MINH ĐƯỢC ĐIỀU GÌ VỀ TỐC ĐỘ. Đặt nhãn là một chuyện, biên Vercel có chịu
giữ bản trả về của một cửa ĐƯỢC CHUYỂN TIẾP sang Render hay không lại là chuyện khác — phép
thử trong tệp này không trả lời được, chỉ bản chạy mới trả lời. Sau khi gộp phải đo lại
«x-vercel-cache» trên trang thật: ra HIT thì nhãn ăn, vẫn MISS thì phải đệm ở tầng khác.
"""
import re
from pathlib import Path

TEP = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "cong_mo.py"


def doc() -> str:
    return TEP.read_text(encoding="utf-8")


def than(ten: str) -> str:
    """Thân một hàm cửa, cắt từ «def <ten>(» tới «def » kế tiếp ở cột 0."""
    s = doc()
    i = s.index(f"def {ten}(")
    j = s.find("\ndef ", i + 1)
    k = s.find("\n@router", i + 1)
    het = min(x for x in (j, k, len(s)) if x > 0)
    return s[i:het]


def tach_nhan(nhan: str) -> dict:
    return {k.strip(): v for k, v in
            (p.split("=", 1) if "=" in p else (p, "") for p in (x.strip() for x in nhan.split(",")))}


# ══ 1 · HÌNH DẠNG NHÃN ══════════════════════════════════════════════════════════════════════

def test_tr17_1_hai_nhan_deu_dung_hinh():
    import importlib.util
    s = doc()
    for ten in ("DEM_DANH_SACH", "DEM_LICH_TRINH"):
        nhan = re.search(rf'{ten}\s*=\s*"([^"]+)"', s).group(1)
        p = tach_nhan(nhan)
        assert "public" in p, f"{ten}: thiếu public thì tầng đệm chung không được phép giữ"
        assert p.get("max-age") == "0", f"{ten}: trình duyệt của khách KHÔNG được giữ bản cũ"
        assert int(p["s-maxage"]) >= 60, f"{ten}: s-maxage quá ngắn thì đệm gần như vô nghĩa"
        assert int(p["stale-while-revalidate"]) > int(p["s-maxage"]), \
            f"{ten}: cửa sổ trả-bản-cũ phải DÀI HƠN hạn, nếu không khách vẫn phải đứng đợi lượt làm mới"


def test_tr17_2_danh_sach_tuoi_hon_lich_trinh():
    """Danh sách mang giá và chỗ trống nên phải tươi hơn; chữ chương trình tour thì cả tháng
    mới sửa một lần, giữ lâu hơn được."""
    s = doc()
    ds = int(re.search(r'DEM_DANH_SACH\s*=\s*"[^"]*s-maxage=(\d+)', s).group(1))
    lt = int(re.search(r'DEM_LICH_TRINH\s*=\s*"[^"]*s-maxage=(\d+)', s).group(1))
    assert ds <= 120, "giá và chỗ trống cũ quá hai phút là bắt đầu khó giải thích với khách"
    assert lt > ds


# ══ 2 · DÁN ĐÚNG BA CỬA ═════════════════════════════════════════════════════════════════════

def test_tr17_3_ba_cua_chi_doc_deu_duoc_dan_nhan():
    assert "_dem(resp, DEM_DANH_SACH)" in than("tr_tim")
    assert "_dem(resp, DEM_DANH_SACH)" in than("tr_mot")
    assert "_dem(resp, DEM_LICH_TRINH)" in than("tr_lich")


# ══ 3 · VÀ TUYỆT ĐỐI KHÔNG DÁN BA CỬA KIA ═══════════════════════════════════════════════════

def test_tr17_4_cua_tinh_gia_khong_bao_gio_duoc_dem():
    """Giá đặt của chính đơn khách đang xem. Đệm lại là phát số của đơn này cho đơn khác."""
    t = than("tr_tinh")
    assert "_dem(" not in t and "Cache-Control" not in t


def test_tr17_5_cua_thanh_toan_rieng_khong_bao_gio_duoc_dem():
    """Mã link là thứ Sale Admin gửi riêng cho MỘT khách — chia chung là lộ đơn người khác."""
    for ten in ("ttd_xem", "ttd_hoa_don"):
        t = than(ten)
        assert "_dem(" not in t, f"{ten} bị dán nhãn đệm"


def test_tr17_6_cua_tim_phong_khach_san_khong_duoc_dem():
    """Còn phòng theo ngày, đổi từng phút; đệm lại là bán phòng đã hết."""
    assert "_dem(" not in than("ks_tim")


def test_tr17_7_danh_sach_cam_duoc_ghi_ra_trong_ma():
    """Ghi hẳn ra để vòng sau không ai thêm nhầm — và phép thử này canh chính danh sách ấy."""
    s = doc()
    for cua in ("/tour-online/tinh", "/ks-vtd/tim", "/tt-doan/{ma}"):
        assert cua in re.search(r"KHONG_DEM\s*=\s*\(([^)]*)\)", s, re.S).group(1)


# ══ 4 · KHÔNG LÀM HỎNG THỨ ĐANG CHẠY ════════════════════════════════════════════════════════

def test_tr17_8_phanh_chong_cao_du_lieu_con_nguyen():
    s = doc()
    assert "dependencies=[Depends(_phanh)]" in s, "mất phanh là mở cửa cho máy cào dữ liệu tour"
    assert re.search(r"CUA_SO_GIAY,\s*TOI_DA_TRONG_CUA_SO\s*=\s*600,\s*240", s)


def test_tr17_9_hen_doc_lai_bai_web_con_nguyen():
    t = than("tr_mot")
    assert "background.add_task(_lam_moi_nen, p.id)" in t
    assert "TR.lam_moi(db, p)" in t


def test_tr17_10_khong_cua_nao_o_router_nay_doc_phien():
    """Điều kiện sống còn của cả vòng: đệm chung chỉ an toàn khi không cửa nào gắn với một
    tài khoản. Cửa nào kéo phiên vào đây thì nhãn đệm thành lỗ hổng, không còn là tối ưu.

    Soi bằng cây cú pháp chứ không tìm chuỗi: lời chú thích có quyền NHẮC TỚI «tai_khoan_ngoai»
    để giải thích vì sao router này không dùng nó, và một phép thử tìm chuỗi sẽ báo động giả
    đúng vào câu giải thích ấy."""
    import ast
    cay = ast.parse(doc())
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten |= {a.arg for n in ast.walk(cay) if isinstance(n, ast.arguments) for a in n.args + n.kwonlyargs}
    for cam in ("tai_khoan_ngoai", "phien_cong", "current_user", "nguoi_dung_hien_tai", "get_current_user"):
        assert cam not in ten, f"router công khai đã kéo «{cam}» vào — gỡ nhãn đệm trước khi gộp"
