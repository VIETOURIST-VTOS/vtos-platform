"""Màn hình nào cũng phải có cửa nhập, hoặc phải nói rõ nó là tấm gương soi cái gì.

Ranh giới Chủ tịch đặt 09/9/2026: phần mềm viết cấu trúc, phép tính và hệ điều hành; SỐ LIỆU do
nhân viên các bộ phận tự nhập – gõ biểu, tải tệp, tải ảnh. Hệ quả trực tiếp: mỗi con số trên màn
hình phải lần ngược được về MỘT CỬA có người đứng.

Bản rà 09/9 đi qua 83 mục menu và tìm được ba chỗ hỏng, cả ba cùng một dạng: cửa có tồn tại nhưng
người phải dùng nó không với tới, hoặc cửa chưa bao giờ được dựng dù máy chủ đã mở đường.

  · Lệnh điều xe – người duy nhất được chốt lệnh không thấy màn hình nào chứa mẫu.
  · Nạp dữ liệu – 26 bộ nạp chỉ có cửa tệp, dù máy chủ có sẵn đường gõ tay một dòng.
  · Đính kèm – bảy loại hồ sơ khai gắn được tệp mà không màn hình nào dựng ô gắn.

Rà tay chỉ đúng tại thời điểm rà. Màn hình thứ 84 thêm vào tuần sau sẽ không có ai rà lại, và nó
lặng lẽ nằm đó không cửa. Nên chuyển bản rà thành một phép kiểm chạy cùng bộ phép thử.

Phép thử này KHÔNG đòi mọi màn hình đều ghi được. Màn hình chỉ xem là chuyện bình thường và đúng –
báo cáo, nhật ký, bảng tổng hợp. Nó đòi một điều khác: màn hình chỉ xem phải NÓI RA nó soi cái gì,
và đường đọc ấy phải còn đó. Thêm một con số mới từ một nguồn khác vào một tấm gương là lúc phải
dừng lại hỏi con số ấy vào hệ thống bằng cửa nào – phép thử này là chỗ dừng ấy.
"""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
SHELL = WEB / "components" / "Shell.tsx"

# Lời gọi GHI. Bắt cả ba lối viết đang dùng: api(p,{method:"POST"}) · fetch(...,{method}) ·
# hàm bọc kiểu const post = async (path, json?, method = "POST") => api(path, {method, json}).
RE_API = re.compile(r'\bapi(?:<[^>]*>)?\(([^;]{0,300}?)\)\s*[;,.\)\}]', re.S)
RE_FETCH = re.compile(r'\bfetch\(([^;]{0,300}?)\)\s*[;,.\)\}]', re.S)

# Màn hình CHỈ XEM, kèm lý do và những đường nó đọc. Thêm tên vào đây phải kèm cả hai – lý do trống
# hoặc đường đọc trống thì phép thử không còn canh được gì.
CHI_XEM = {
    "/": ("Bảng tổng quan: gộp lại con số của các phân hệ khác, không sở hữu con số nào của riêng "
          "mình. Số vào hệ thống ở màn hình của từng phân hệ.", ("/dashboard",)),
    "/sales-reports": ("Báo cáo bán hàng: tính từ booking và tour đã có. Cửa nhập nằm ở màn hình "
                       "Booking và Tour, không phải ở đây.", ("/sales-reports",)),
    "/cong-no": ("Công nợ: suy ra từ booking, phiếu thu và đề nghị chi. Sửa công nợ bằng cách sửa "
                 "chứng từ gốc, không phải bằng cách gõ đè lên bảng tổng hợp.", ("/cong-no",)),
    "/hieu-qua-doi-xe": ("Chi phí & hiệu quả đội xe: tính từ nhật trình chuyến, nhiên liệu, phí cầu "
                         "đường, bảo dưỡng – tất cả đều có bộ nạp riêng ở màn hình Nạp dữ liệu.",
                         ("/fleet/ban-tin-sang", "/fleet/hieu-qua")),
    "/audit": ("Nhật ký nghiệp vụ: mọi thao tác ghi ở màn hình khác đều để lại một dòng ở đây. Màn "
               "hình này mà ghi được thì nhật ký thôi là nhật ký.", ("/audit",)),
    "/phieu-luong": ("Phiếu lương của tôi: kỳ lương do HCNS chốt ở màn hình Lương, thưởng & hoa "
                     "hồng. Người xem phiếu không sửa được phiếu của chính mình.",
                     ("/phieu-luong/ky-cua-toi",)),
    # Thêm 09/9/2026 cùng đợt gộp nhánh Đợt 2. Ba màn hình bị bộ kiểm này bắt, và CHỈ MỘT trong ba là
    # chỉ-xem thật – hai cái kia là cửa còn thiếu và đã dựng cửa, không khai vòng cho qua.
    "/bao-cao": ("Báo cáo tự động theo phòng ban: mọi con số tính TẠI CHỖ từ dữ liệu của các phân hệ "
                 "khác, không sở hữu con số nào của riêng mình. Cửa nhập nằm ở màn hình của từng "
                 "phòng. Màn hình này mà ghi được thì nó thôi là báo cáo.", ("/bao-cao",)),
}


def _ma(src: str) -> str:
    """Bỏ chú thích, chỉ giữ mã chạy – chú thích nhắc tên một đường không tính là màn hình gọi nó."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


def _man_hinh() -> list:
    """Đường dẫn màn hình lấy từ menu thật (GROUPS trong Shell.tsx), không chép tay danh sách."""
    if not SHELL.exists():
        return []
    blk = _ma(SHELL.read_text(encoding="utf-8"))
    i = blk.index("export const GROUPS")
    # Mốc kết thúc là MÃ THẬT (`export const CA_NHAN`), không phải chú thích: hàm _ma() ở trên
    # xoá sạch chú thích trước khi tìm mốc. Trước 11/9/2026 mốc là tên hằng ROADMAP_ROLES; TC-2
    # bỏ hằng ấy đi và phép thử này vỡ bằng ValueError không nói gì về nguyên nhân.
    blk = blk[i: blk.index("export const CA_NHAN")]
    ra = []
    for _, href in re.findall(r'\["([^"]*)",\s*"([^"]*)"\]', blk):
        if href:
            ra.append("/" + href.split("?")[0].strip("/"))
    return sorted(set(ra))


def _so_cua_ghi(duong: str) -> int:
    """Đếm lời gọi ghi của một màn hình, tính cả mã của thành phần dùng chung mà nó nhập."""
    p = WEB / "app" / duong.strip("/") / "page.tsx" if duong != "/" else WEB / "app" / "page.tsx"
    if not p.exists():
        return -1
    src = _ma(p.read_text(encoding="utf-8"))
    tep = [src]
    for m in re.findall(r'from "@/components/(\w+)"', src):
        if m == "Shell":
            continue
        q = WEB / "components" / (m + ".tsx")
        if q.exists():
            tep.append(_ma(q.read_text(encoding="utf-8")))
    n = 0
    for t in tep:
        for rx in (RE_API, RE_FETCH):
            for m in rx.finditer(t):
                if re.search(r"\bmethod\b|\bjson\s*[:,}]|\bbody\b", m.group(1)):
                    n += 1
        ten = set(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*method\s*=\s*"(?:POST|PUT|PATCH|DELETE)"', t))
        ten |= set(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]{0,200}?\)\s*=>\s*\{?[^;]{0,250}?method:\s*"(?:POST|PUT|PATCH|DELETE)"', t))
        for x in ten:
            n += max(len(re.findall(r"(?<![\w.])" + re.escape(x) + r"\(", t)) - 1, 0)
    return n


def test_doc_duoc_menu_that_chu_khong_pass_suong():
    """Phép thử đọc menu bằng biểu thức chính quy; biểu thức hỏng thì nó tìm ra 0 màn hình và xanh
    suốt. Chốt một sàn để chỗ ấy không im lặng."""
    if not SHELL.exists():
        return
    mh = _man_hinh()
    assert len(mh) >= 40, f"Chỉ đọc được {len(mh)} màn hình từ GROUPS – nhiều khả năng cách đọc đã hỏng"


def test_moi_man_hinh_hoac_co_cua_ghi_hoac_khai_la_chi_xem():
    if not SHELL.exists():
        return
    thieu = []
    for d in _man_hinh():
        n = _so_cua_ghi(d)
        if n <= 0 and d not in CHI_XEM:
            thieu.append((d, "không có tệp màn hình" if n < 0 else "không có lời gọi ghi nào"))
    assert not thieu, (
        "Màn hình không có cửa nhập nào và cũng không khai là chỉ xem: "
        + "; ".join(f"{d} ({vi})" for d, vi in thieu) +
        ". Ranh giới 09/9/2026: mỗi con số phải có một cửa cho người dùng. Dựng cửa, hoặc thêm vào "
        "CHI_XEM kèm lý do và những đường màn hình ấy đọc.")


def test_man_hinh_chi_xem_van_dung_la_chi_xem():
    """Chiều ngược lại: một màn hình đã khai chỉ xem mà nay ghi được thì lời khai thành sai.

    Không phải để cấm – thêm cửa nhập là việc tốt. Nhưng lời khai ở trên nói "số vào hệ thống ở chỗ
    khác", và câu ấy không còn đúng nữa thì phải sửa lời khai, không để nó nằm đó dẫn người đọc sai.
    """
    if not SHELL.exists():
        return
    sai = [d for d in CHI_XEM if _so_cua_ghi(d) > 0]
    assert not sai, (
        f"Màn hình khai là chỉ xem nhưng đã có cửa ghi: {sai}. Bỏ khỏi CHI_XEM.")


def test_duong_doc_da_khai_van_con_tren_man_hinh():
    """Đường đọc đã khai phải còn đó.

    Đây là chỗ phép thử thật sự làm việc. Một tấm gương chỉ vô hại khi biết nó soi cái gì. Thêm một
    con số mới từ một nguồn khác vào màn hình chỉ xem là lúc phải dừng lại hỏi: con số ấy vào hệ
    thống bằng cửa nào, ai gõ nó. Không có chỗ dừng thì màn hình báo cáo lớn dần lên bằng những con
    số không ai nhập – và đó đúng là hình dạng của một hệ thống trông như đang chạy.
    """
    if not SHELL.exists():
        return
    hong = []
    for d, (ly_do, duong) in CHI_XEM.items():
        assert len(ly_do) > 60, f"Lý do chỉ xem của {d} quá ngắn để là một lý do thật"
        assert duong, f"{d} khai là chỉ xem mà không nói đọc từ đâu"
        p = WEB / "app" / d.strip("/") / "page.tsx" if d != "/" else WEB / "app" / "page.tsx"
        if not p.exists():
            hong.append((d, "mất tệp màn hình")); continue
        src = _ma(p.read_text(encoding="utf-8"))
        mat = [x for x in duong if x not in src]
        if mat:
            hong.append((d, f"không còn đọc {mat}"))
    assert not hong, (
        "Lời khai của màn hình chỉ xem không còn khớp với mã: "
        + "; ".join(f"{d} – {vi}" for d, vi in hong) +
        ". Nếu màn hình đổi nguồn số liệu thì sửa lời khai, và nhân thể trả lời câu: con số mới ấy "
        "vào hệ thống bằng cửa nào?")


def test_danh_sach_chi_xem_co_tran():
    """Danh sách ngoại lệ không trần là cách một phép thử tự tắt mình."""
    assert len(CHI_XEM) <= 8, (
        f"Đang khai {len(CHI_XEM)} màn hình chỉ xem. Ngày 09/9/2026 là 6. Con số này to lên nghĩa là "
        "mỗi lần đỏ lại thêm một dòng thay vì hỏi con số kia vào hệ thống bằng cửa nào.")
