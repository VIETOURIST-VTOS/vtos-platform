"""Khai được gắn tệp mà không màn hình nào có ô gắn thì cũng bằng không gắn được.

Máy chủ khai danh sách đối tượng gắn tệp trong DOI_TUONG_DAY_DU: chuyến xe, hồ sơ xe, tour, booking,
nhà cung cấp, đơn đặt dịch vụ, hồ sơ nhân sự… Khai xong là có API, có kho lưu, có phân quyền, có quy
tắc chống trùng. Nhưng người dùng chỉ gắn được tệp ở nơi có Ô GẮN TỆP trên màn hình của mình.

Đo ngày 09/9/2026: mười bốn loại được khai, bảy loại có ô tại chỗ. Bảy loại còn lại chỉ gắn được qua
màn hình Tệp & hình ảnh, nơi phải tự gõ mã hồ sơ – đó là cửa sau chứ không phải cửa. Người đang mở hồ
sơ một chiếc xe, thấy dòng đăng kiểm hết hạn, không có nút nào để đưa bản chụp vào; muốn gắn thì phải
nhớ mã xe, sang màn hình khác, gõ lại mã. Việc ấy sẽ không ai làm, và bản chụp ở lại trong điện thoại.

Phép thử này bắc qua hai tầng: khai báo ở máy chủ và ô gắn trên giao diện. Nó KHÔNG kiểm tra API chạy
đúng (chỗ ấy đã có phép thử riêng), nó kiểm tra chỗ còn lại – khai rồi thì phải có cửa, hoặc phải nói
ra vì sao chưa có.
"""
import re
from pathlib import Path

from app.models.attachments import DOI_TUONG_DAY_DU

WEB = Path(__file__).resolve().parents[2] / "web"

# Loại được khai nhưng CHƯA có ô tại chỗ, kèm lý do thật. Thêm tên vào đây phải kèm lý do – danh sách
# này là chỗ để nói "chưa làm", không phải chỗ để làm im đi.
CHUA_CO_CUA = {
    "van_ban": "Màn hình Văn bản chưa xây (mục để trống trong menu Hành chính & Nhân sự). Dựng ô gắn "
               "tệp trước khi có màn hình thì tệp gắn vào một hồ sơ chưa tồn tại.",
    "visa": "Hồ sơ visa đã có cửa tải tệp RIÊNG theo từng mục hồ sơ (checklist) ngay trên màn hình "
            "/visa. Bằng chứng vào được hệ thống; việc còn lại là gộp hai kho làm một, và đó là quyết "
            "định về cấu trúc kho chứ không phải chỗ thiếu cửa.",
    "khach_hang": "Chưa quyết: hồ sơ khách hàng lưu ở nguồn khách (/leads) hay ở booking. Gắn nhầm chỗ "
                  "thì dữ liệu cá nhân của khách nằm trong nhóm hồ sơ 05_Tour, thời hạn lưu 10 năm.",
    "sao_ke": "Sao kê vào hệ thống bằng đường NẠP DỮ LIỆU (đọc số từ tệp), chưa quyết có giữ lại bản "
              "gốc như một chứng từ đính kèm hay không – giữ thì kho phình theo tháng, không giữ thì "
              "lúc đối chiếu lệch phải xin lại ngân hàng.",
}


# Loại có CỬA GẮN RIÊNG thay cho thẻ <DinhKem> — và phép thử ĐỌC tệp màn hình ấy để chắc cửa có thật,
# không tin lời khai. PC-1 (19/10/2026): trưởng phòng tự gửi yêu cầu Pháp chế; <DinhKem> đi qua
# /api/v1/tep mà cửa ghi ấy không mở cho TP Kinh doanh, TP Hướng dẫn, Kế toán trưởng… nên màn này
# gắn tệp qua cửa riêng `POST /api/v1/gui-phap-che/{id}/tep`, chỉ cho chính người gửi.
CUA_GAN_RIENG = {
    "yeu_cau_phap_che": ("app/gui-phap-che/page.tsx", "/tep`"),
    # BC-1 (26/10/2026): Phần 5 của báo cáo ngày gắn tệp qua cửa riêng /daily-reports/{id}/tep, vì quyền
    # theo HỒ SƠ (tác giả + người quản lý), không theo vai như cửa /tep chung.
    "bao_cao_ngay": ("app/reports/page.tsx", "/tep`"),
    # AT-1c (28/10/2026): ảnh món / nhà hàng / thành phố gắn qua cửa riêng /nha-hang/anh/{doi}/{id} — bắt buộc
    # ghi nguồn ảnh, và Marketing / Điều hành không cần quyền cửa /tep chung.
    "am_thuc": ("app/nha-hang/page.tsx", "/nha-hang/anh/${doi}/${id}`"),
    # Ảnh khách sạn web VTD gắn qua album riêng /khach-san-vtd/{kid}/anh: máy làm nhẹ ảnh, ghi nguồn,
    # gửi duyệt rồi mới hiện; <DinhKem> chung sẽ đi vòng qua các bước ấy.
    "khach_san_vtd": ("app/khach-san-vtd/page.tsx", "/khach-san-vtd/${kid}/anh`"),
}


def _ma(src: str) -> str:
    """Bỏ chú thích, chỉ giữ mã chạy – chú thích có nhắc tên đối tượng cũng không tính là có cửa."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


def _loai_co_o_gan() -> set:
    """Đọc thẳng thuộc tính doiTuong của mọi thẻ <DinhKem> trong mã giao diện."""
    ra = set()
    if not WEB.exists():
        return ra
    # KS-64 · 09/11/2026 — quét CẢ THƯ MỤC CON của components/.
    #
    # Trước hôm nay chỗ này là `components/*.tsx`: một bậc, không đệ quy. Nên mọi ô đính kèm
    # nằm trong components/doixe/, components/cong/, components/nha-hang/… đều VÔ HÌNH với phép
    # thử — nó báo "không màn hình nào có ô gắn" cho một loại hồ sơ đã có ô gắn hẳn hoi.
    #
    # Đó là loại hỏng tệ hơn cả không có phép thử: nó đẩy người sửa về phía thêm một dòng vào
    # CHUA_CO_CUA (danh sách hoãn) cho một việc đã làm xong rồi.
    for p in list(WEB.glob("app/**/*.tsx")) + list(WEB.glob("components/**/*.tsx")):
        if p.name == "DinhKem.tsx":
            continue                                  # chính thành phần ấy, không phải nơi dùng
        for m in re.findall(r'<DinhKem[^>]*?doiTuong=\{?"([a-z_0-9]+)"', _ma(p.read_text(encoding="utf-8"))):
            ra.add(m)
    for loai, (tep, dau) in CUA_GAN_RIENG.items():
        f = WEB / tep
        if f.exists() and "FormData" in (m := _ma(f.read_text(encoding="utf-8"))) and dau in m:
            ra.add(loai)
    return ra


def test_moi_loai_ho_so_khai_gan_duoc_tep_deu_co_o_gan_tai_cho():
    if not WEB.exists():
        return
    co = _loai_co_o_gan()
    thieu = sorted(set(DOI_TUONG_DAY_DU) - co - set(CHUA_CO_CUA))
    assert not thieu, (
        f"Loại hồ sơ được khai gắn được tệp nhưng không màn hình nào có ô gắn: {thieu}. "
        "Người dùng sẽ phải sang màn hình Tệp & hình ảnh và tự gõ mã hồ sơ – việc ấy sẽ không ai làm. "
        "Dựng ô tại chỗ, hoặc thêm vào CHUA_CO_CUA KÈM LÝ DO.")


def test_danh_sach_chua_co_cua_khong_duoc_phinh_ra_lang_le():
    """Danh sách hoãn phải nhỏ và phải cũ đi, không được to lên.

    Một danh sách ngoại lệ không có trần là cách một phép thử tự tắt mình: mỗi lần đỏ thì thêm một
    dòng, và sau mười lần thì nó không còn canh gì nữa.
    """
    assert len(CHUA_CO_CUA) <= 4, (
        f"Đang hoãn {len(CHUA_CO_CUA)} loại hồ sơ. Ngày 09/9/2026 là 4. Danh sách này phải ngắn đi "
        "theo thời gian; dài ra nghĩa là mỗi lần đỏ lại thêm một dòng thay vì dựng một ô.")
    for k, ly_do in CHUA_CO_CUA.items():
        assert k in DOI_TUONG_DAY_DU, f"'{k}' không còn được khai – bỏ khỏi danh sách hoãn"
        assert len(ly_do) > 60, f"Lý do hoãn cho '{k}' quá ngắn để là một lý do thật"


def test_o_gan_khong_tro_vao_loai_khong_duoc_khai():
    """Chiều ngược lại: màn hình gắn vào một mã không có trong khai báo thì máy chủ nhận tệp nhưng
    không biết xếp vào nhóm hồ sơ nào – và tệp ấy rơi ra ngoài cấu trúc thư mục kiểm toán."""
    if not WEB.exists():
        return
    la = sorted(_loai_co_o_gan() - set(DOI_TUONG_DAY_DU))
    assert not la, (
        f"Màn hình đang gắn tệp vào loại không được khai ở máy chủ: {la}")
