"""Người được phép làm một việc phải có một màn hình để làm việc ấy.

Chỗ hỏng đo được ngày 09/9/2026, và nó hỏng theo kiểu không ai nhìn thấy:

  · Tham số chính sách `xe_nguoi_lap_lenh` chỉ định Giám đốc điều hành đội xe là người DUY NHẤT được
    tạo và chốt lệnh điều xe (chỉ đạo Chủ tịch 07/9/2026). POST /api/v1/dispatch chặn đúng như thế.
  · Mẫu lập lệnh duy nhất trong giao diện nằm ở /ops?tab=fleet.
  · Danh sách màn hình của vai trò gd_doi_xe KHÔNG có /ops.

Ba câu trên, mỗi câu đọc riêng đều đúng và đều hợp lý. Ghép lại thì phân hệ lệnh điều xe đứng hẳn:
người được phép không thấy mẫu, người thấy mẫu thì máy chủ trả 403. Không có lỗi nào được ghi ra,
không có cảnh báo nào bật lên – chỉ là bảng "Lệnh đã lập" mãi không dài thêm, và ai nhìn cũng nghĩ
hôm nay không có chuyến.

Đó là dạng hỏng mà phép thử theo từng tầng không bắt được: phép thử phân quyền hỏi "gd_doi_xe có gọi
được POST /dispatch không" – có. Phép thử giao diện hỏi "màn hình /ops có mẫu lập lệnh không" – có.
Phải hỏi bắc qua hai tầng mới thấy: người được phép có màn hình nào chứa mẫu ấy không.
"""
import re
from pathlib import Path

from app.services import access as AC

WEB = Path(__file__).resolve().parents[2] / "web" / "app"

# Nhận diện mẫu lập lệnh trong mã giao diện: một lời gọi GHI tới /dispatch. Bắt cả hai lối viết đang
# dùng trong dự án – api()/hàm bọc post("/dispatch"...) và fetch("/api/v1/dispatch", {method:"POST"}).
GOI_LAP_LENH = re.compile(r'(post\(\s*["\`]/dispatch["\`])|(["\`]/api/v1/dispatch["\`][^;]{0,120}?method)', re.S)


class _nguoi:
    """Đủ để menus_for() đọc: nó chỉ cần vai trò và thẻ nhân sự."""
    def __init__(self, vai): self.role = vai; self.hr_tabs = None; self.id = 0


def _man_hinh_co_mau_lap_lenh() -> set:
    """Tên màn hình (đường dẫn kiểu /lenh-dieu-xe) có mẫu lập lệnh, đọc thẳng từ mã giao diện."""
    if not WEB.exists():
        return set()
    ra = set()
    # Thành phần dùng chung: màn hình nào nhập nó thì coi như mang theo mẫu bên trong.
    comp = WEB.parent / "components"
    mang_mau = {c.stem for c in comp.glob("*.tsx")
                if GOI_LAP_LENH.search(_ma(c.read_text(encoding="utf-8")))} if comp.exists() else set()
    # Quét CẢ trang con (17/10/2026, tách màn /lenh-dieu-xe): mẫu lập lệnh nay nằm ở trang con
    # /lenh-dieu-xe/lap-lenh. Trang con được tính cho MÀN CẤP MỘT chứa nó, vì trang con không có mục
    # menu và không có quyền riêng — ai vào được màn cấp một thì vào được trang con. Chỉ quét cấp một
    # như trước thì phép thử này đỏ oan, hoặc tệ hơn: ai đó dời mẫu về lại một trang 13 khối cho xanh.
    for p in sorted(WEB.glob("**/page.tsx")):
        src = _ma(p.read_text(encoding="utf-8"))
        nhap = set(re.findall(r'from "@/components/(\w+)"', src))
        if GOI_LAP_LENH.search(src) or (nhap & mang_mau):
            ra.add("/" + p.relative_to(WEB).parts[0])
    return ra


def _ma(src: str) -> str:
    """Bỏ chú thích, chỉ giữ mã chạy.

    Phép thử đọc mã giao diện luôn phải bóc chú thích trước. Bài học lấy từ bộ phép thử cửa nhập tay
    cùng ngày: ở đó hai đột biến lọt qua vì chính đoạn chú thích giải thích chỗ hỏng lại nhắc đúng tên
    cái đường đã bị gỡ – phép thử hóa ra đang canh "tệp có nhắc tới cửa này không", câu vẫn đúng sau
    khi cửa đã mất."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


def _nguon_cua(ten: str) -> list:
    """Mã của màn hình, và mã của từng thành phần dùng chung mà nó nhập – trả RIÊNG từng tệp.

    Trả riêng chứ không nối lại thành một chuỗi: nối lại thì một trường nằm ở tệp này có thể che chỗ
    thiếu ở tệp kia.
    """
    ra = []
    # Trang của màn cấp một và mọi trang con của nó — cùng lẽ với `_man_hinh_co_mau_lap_lenh`.
    for p in sorted((WEB / ten.lstrip("/")).glob("**/page.tsx")):
        src = p.read_text(encoding="utf-8")
        ra.append(_ma(src))
        for m in re.findall(r'from "@/components/(\w+)"', src):
            q = WEB.parent / "components" / (m + ".tsx")
            if q.exists():
                ra.append(_ma(q.read_text(encoding="utf-8")))
    return ra


def test_vai_tro_duoc_lap_lenh_phai_co_man_hinh_de_lap():
    """gd_doi_xe – vai trò mà tham số chính sách chỉ định là người chốt lệnh – phải thấy một mẫu lập lệnh.

    Phép thử này KHÔNG kiểm tra ông có quyền gọi API (chỗ ấy đã đúng từ 07/9). Nó kiểm tra chỗ còn lại:
    quyền mà không có cửa thì bằng không có quyền.
    """
    if not WEB.exists():
        return          # chỉ chạy khi có mã giao diện cạnh mã máy chủ
    co_mau = _man_hinh_co_mau_lap_lenh()
    # 17/10/2026: trước đây dòng trên là `if not co_mau: return` — tức là MẤT HẲN mẫu lập lệnh
    # thì phép thử này XANH. Đo được khi tách màn: đổi đường gửi của mẫu sang chỗ khác, cả tệp vẫn
    # 5/5 xanh. Có mã giao diện mà không màn nào có mẫu thì đó chính là chỗ hỏng phải bắt.
    assert co_mau, ("Có mã giao diện nhưng không màn hình nào có mẫu lập lệnh (lời gọi ghi tới "
                    "/dispatch). Người được chốt lệnh không còn chỗ nào để chốt.")
    thay = set(AC.menus_for(_nguoi("gd_doi_xe")))
    assert co_mau & thay, (
        f"Vai trò gd_doi_xe được máy chủ cho phép POST /api/v1/dispatch, nhưng không màn hình nào ông "
        f"thấy có mẫu lập lệnh. Màn hình có mẫu: {sorted(co_mau)}; màn hình ông thấy: {sorted(thay)}")


def test_moi_mau_lap_lenh_deu_gui_du_ba_truong_ghi_vet():
    """Mẫu lập lệnh phải GỬI ĐI so_khach, km_du_kien và ly_do_khac_goi_y.

    Ba trường này không phải trang trí:
      · so_khach và km_du_kien là đầu vào của bộ xếp hạng. Không gửi thì mặc định 0, và máy chấm điểm
        cho một chuyến 0 khách 0 km – tức chấm cho một chuyến không có thật, rồi lấy kết quả ấy để
        quyết định có bắt người chốt lệnh giải trình hay không.
      · ly_do_khac_goi_y là trường máy chủ ĐÒI (422) khi xe được chọn điểm thấp hơn nhóm đề xuất. Mẫu
        không gửi được trường ấy thì người dùng gặp một lỗi 422 không có cách nào giải – cụt đường
        thật sự, không phải bất tiện.

    Đọc trong KHỐI GỬI ĐI chứ không đọc cả tệp. Bản đầu của phép thử này tìm chữ trong cả tệp và vì
    thế đã bỏ lọt một đột biến: bỏ ly_do_khac_goi_y khỏi phần gửi đi mà phép thử vẫn xanh, chỉ vì
    cùng tên ấy còn nằm ở cột hiển thị "Ghi vết gợi ý" phía dưới. Một phép thử đọc cả tệp thì cái nó
    canh là "tệp có nhắc tới trường này không", chứ không phải "mẫu có gửi trường này đi không".
    """
    if not WEB.exists():
        return
    thieu = []
    for ten in sorted(_man_hinh_co_mau_lap_lenh()):
        for src in _nguon_cua(ten):
            m = GOI_LAP_LENH.search(src)
            if not m:
                continue
            khoi = src[m.start(): m.start() + 900]     # thân lời gọi ghi, đủ dài để trùm hết phần thân gửi đi
            van = [t for t in ("so_khach", "km_du_kien", "ly_do_khac_goi_y") if t not in khoi]
            if van:
                thieu.append((ten, van))
    assert not thieu, (
        "Mẫu lập lệnh không gửi đi: " + "; ".join(f"{t} thiếu {v}" for t, v in thieu) +
        ". Thiếu so_khach/km_du_kien thì bộ gợi ý chấm điểm cho một chuyến không có thật; thiếu "
        "ly_do_khac_goi_y thì gặp 422 là cụt đường.")


def test_duong_de_lap_lenh_nam_trong_hang_rao_doi_xe():
    """Đường lấy tour để lập lệnh phải nằm dưới /api/v1/fleet, không phải mở /api/v1/tours cho đội xe.

    Cách chữa dễ nhất cho chỗ hỏng trên là thêm /api/v1/tours vào phạm vi của gd_doi_xe. Không làm thế:
    phân hệ tour mang giá bán, dự toán, biên lợi nhuận và giải trình dưới biên – mở cả cụm để lấy bốn
    cột lịch trình là nới hàng rào rộng gấp nhiều lần việc cần làm. Phép thử này canh để lần sau không
    ai chữa theo lối ấy cho nhanh.
    """
    pham_vi = set(AC.pham_vi_day_du("gd_doi_xe"))
    assert "/api/v1/fleet" in pham_vi
    assert "/api/v1/tours" not in pham_vi, (
        "Phạm vi của gd_doi_xe vừa được mở tới cả phân hệ tour. Nếu đó là quyết định thật thì sửa phép "
        "thử này kèm lý do; nếu chỉ để lấy mã tour cho lệnh điều xe thì dùng "
        "GET /api/v1/fleet/de-lap-lenh – đường ấy trả lịch trình và số khách, không trả một con số tiền nào.")


def test_mau_lap_lenh_hien_ngay_khi_mo_trang():
    """Ô chọn tour phải có mặt lúc MỞ trang, không đợi người dùng bấm đúng một nút mới hiện ra.

    Bản đầu ngày 09/9 nạp danh sách tour bên trong hàm "Xem phương án", vì mẫu chốt lệnh dùng chung
    khoảng ngày với bảng gợi ý. Nghe hợp lý, và soi trên web thật thì hậu quả đúng bằng chỗ hỏng mà cả
    bản ấy sinh ra để chữa: người phụ trách mở trang lên, chỉ thấy ô tìm ngày và bảng lệnh cũ, rồi kết
    luận màn hình này chỉ để xem.

    Một cái cửa chỉ hiện ra sau khi người ta đoán đúng phải bấm nút nào thì cũng gần bằng không có cửa
    – và đó là dạng thiếu KHÔNG phép thử cũ nào bắt được, vì mã có đủ mọi thứ, chỉ sai chỗ đặt.

    Cách canh: đường lấy tour phải nằm trong một hàm được useEffect gọi, chứ không nằm trong thân hàm
    xử lý nút bấm.
    """
    if not WEB.exists():
        return
    # Tách màn 17/10/2026: mẫu lập lệnh nay là trang con /lenh-dieu-xe/lap-lenh.
    p = WEB / "lenh-dieu-xe" / "lap-lenh" / "page.tsx"
    src = _ma(p.read_text(encoding="utf-8"))

    ten = re.findall(r'const\s+(\w+)\s*=\s*useCallback\([^;]{0,400}?de-lap-lenh', src, re.S)
    assert ten, ("Đường /fleet/de-lap-lenh không nằm trong một useCallback nào – nhiều khả năng nó lại "
                 "nằm thẳng trong thân hàm của một nút bấm, tức là ô chọn tour chỉ hiện sau khi bấm.")

    goi_trong_effect = any(re.search(r'useEffect\([^;]{0,300}?(?<![\w.])' + re.escape(t) + r'\(', src, re.S)
                           for t in ten)
    assert goi_trong_effect, (
        f"Hàm nạp tour ({ten}) không được useEffect gọi. Ô chọn tour sẽ chỉ hiện sau khi người dùng "
        "bấm một nút nào đó – và người mở trang lần đầu không biết phải bấm nút nào.")


def test_man_hinh_noi_bang_chu_rang_lenh_duoc_chot_o_day():
    """Nói ra bằng lời, không để người dùng suy ra từ việc có một cái nút.

    Người phụ trách vào màn hình này lần đầu cần đọc được ngay đây là chỗ LẬP lệnh, chứ không phải một
    bảng tra cứu. Câu ấy rẻ, và nó là thứ phân biệt "màn hình có cửa" với "màn hình trông như chỉ xem".
    """
    if not WEB.exists():
        return
    # Tách màn 17/10/2026: câu ấy phải nằm ở màn có mẫu — trang con /lenh-dieu-xe/lap-lenh.
    src = _ma((WEB / "lenh-dieu-xe" / "lap-lenh" / "page.tsx").read_text(encoding="utf-8"))
    assert re.search(r"lập và chốt lệnh|nơi lập lệnh|chốt lệnh điều xe", src), (
        "Màn hình không có câu nào nói rằng lệnh được lập và chốt ở đây.")
