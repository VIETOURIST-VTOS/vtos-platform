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
    # TC-71 · 19/9/2026 — Sổ chuyến còn nợ. Đây là chỉ-xem THẬT, không phải khai vòng cho qua:
    # màn hình không sở hữu con số nào của riêng nó, mà liệt kê chuyến chưa đóng sổ và đưa đường
    # dẫn sang đúng chuyến để người có quyền đóng ở CỬA THẬT (`services/tours.close`).
    #
    # VÀ VIỆC KHÔNG CÓ CỬA GHI Ở ĐÂY LÀ MỘT LỰA CHỌN, không phải chỗ còn thiếu. Em đã hỏi và anh
    # Tuấn chốt 18/9: "Danh sách + đường dẫn sang chuyến", không đóng sổ hàng loạt. Lý do: đóng sổ
    # là việc khó lùi — làm hàng loạt từ một màn hình tổng thì một cú bấm nhầm đi xa hơn nhiều so
    # với cái lợi về tốc độ, và ở màn hình tổng người bấm không nhìn thấy dòng quyết toán của
    # chuyến để mà biết mình đang chốt cái gì.
    "/so-con-no": ("Sổ chuyến còn nợ: liệt kê chuyến đã chạy mà chưa đóng sổ. Không sở hữu con số "
                   "nào của riêng mình — mọi số lấy từ sổ quyết toán của chính chuyến. Cửa đóng sổ "
                   "nằm ở từng chuyến (/tours/<id>), và anh Tuấn chốt 18/9/2026 là KHÔNG dựng cửa "
                   "đóng hàng loạt ở đây vì đóng sổ là việc khó lùi.",
                   ("/so-con-no",)),
}

# ── BÀN LÀM VIỆC THEO VAI — nhóm ĐẾM RIÊNG, mở ngày 24/9/2026 ───────────────────────────────────
#
# ĐÂY LÀ VIỆC CHÍNH PHÉP THỬ NÀY ĐÃ DẶN PHẢI LÀM. Dòng cảnh giác viết ngày 24/9/2026 ở
# `test_danh_sach_chi_xem_co_tran` nói rõ: ba vai của phòng Đoàn thì còn hai vai chưa dựng, và
# "nếu vòng sau lại nâng trần thêm hai lần với cùng một lý do, thì lý do ấy đã thành thói quen chứ
# không còn là lý do — lúc ấy việc phải làm là ĐỔI CÁCH ĐẾM (tách riêng nhóm bàn làm việc), không
# phải nâng tiếp."
#
# Vòng 3/3 tới đúng chỗ ấy. Nên nâng trần lên 10 là làm đúng cái đã tự dặn mình đừng làm; tách
# nhóm thì trần của CHI_XEM tụt về 8 (đúng con số ngày 19/9, trước khi bàn làm việc đầu tiên ra
# đời) và nhóm mới mang trần riêng cùng một câu hỏi riêng.
#
# CÂU HỎI CỦA NHÓM NÀY KHÁC câu hỏi của CHI_XEM. CHI_XEM hỏi "con số này vào hệ thống bằng cửa
# nào". Bàn làm việc hỏi thêm một câu nữa: "cửa GHI của chính vai này nằm ở đâu, và vì sao nó
# không nằm ở đây" — vì một bàn làm việc không có cửa ghi nào mà cũng không chỉ được cửa ghi của
# mình thì nó là một bảng tin, không phải một bàn làm việc.
BAN_LAM_VIEC = {
    "/ptgd-doan": ("Bàn làm việc Phó TGĐ tour đoàn: hàng đợi dự toán đoàn chờ ký, sổ quá hạn quyết "
                   "toán và bảng lãi lỗ đã chốt. Không sở hữu con số nào của riêng mình.",
                   ("/ptgd-doan/ban-lam-viec",),
                   # Cửa ghi của vai này, và vì sao nó không nằm trên màn hình:
                   # ký dự toán đã có cửa thật với cổng biên, luật hai chữ ký và nhật ký. Dựng cửa
                   # ký thứ hai ở đây là tạo bản sao thứ hai của một luật, và bản sao nào rồi cũng
                   # lệch. Ký hàng loạt thì người bấm không nhìn thấy dòng dự toán để biết mình vừa
                   # duyệt cái gì — duyệt là việc phải ĐỌC, không phải việc phải bấm.
                   "POST /api/v1/tours/{id}/approve"),
    "/sales-admin": ("Bàn làm việc Sale Admin phòng Đoàn: dự toán chờ chuyển, soát giá vốn và chứng "
                     "từ NCC, hồ sơ đoàn, tiến độ thu tiền, tiến độ quyết toán, dữ liệu khách. "
                     "Không sở hữu con số nào của riêng mình.",
                     ("/sales-admin/ban-lam-viec",),
                     # Hai cửa ghi của vai này nằm trên CHÍNH CHUYẾN, và cùng một lý do như trên:
                     # chuyển một dự toán là việc phải đọc dự toán ấy. Một nút "chuyển" cạnh một
                     # dòng tóm tắt là lời mời chuyển mà chưa mở ra xem — và cổng chặn duy nhất của
                     # vị trí này mất hết ý nghĩa đúng vào lúc nó trở nên tiện tay.
                     "POST /api/v1/tours/{id}/chuyen-dieu-hanh · .../tra-lai-kinh-doanh"),
    "/ban-tour-le": ("Bàn bán tour lẻ của Phòng Kinh doanh Lẻ: chuyến lẻ đang bán, mỗi dòng kèm "
                     "thông tin chuyến và ba con số dự toán cùng biên. Không sở hữu con số nào của "
                     "riêng mình — mọi số tính từ dự toán do Điều hành lập.",
                     ("/ban-tour-le/ban-lam-viec",),
                     # Cửa ghi của vai này là cửa BÁN, và nó đã có từ đầu. Vì sao không đặt ở đây:
                     # bán một chỗ là việc phải mở chuyến ra đọc trước — chương trình, điểm dừng
                     # nghỉ, hạn huỷ. Một nút "đặt" cạnh một dòng tóm tắt là lời mời đặt mà chưa
                     # xem, và người nhận hậu quả là khách. Thêm nữa, chỗ ngồi có hàng rào sức
                     # chứa (25/9/2026) nằm trong `tours.create_booking`; một cửa đặt thứ hai ở
                     # đây là một chỗ nữa phải nhớ gọi hàng rào ấy.
                     "POST /api/v1/requests"),
}

# Hai nhóm gộp lại mới là toàn bộ màn hình không có cửa ghi. Khoá tên riêng để không nhóm nào lặng
# lẽ nuốt nhóm kia.
KHONG_CUA_GHI = {**{k: v[:2] for k, v in BAN_LAM_VIEC.items()}, **CHI_XEM}
assert len(KHONG_CUA_GHI) == len(CHI_XEM) + len(BAN_LAM_VIEC), "hai nhóm không được trùng tên màn hình"


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
        if n <= 0 and d not in KHONG_CUA_GHI:
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
    sai = [d for d in KHONG_CUA_GHI if _so_cua_ghi(d) > 0]
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
    for d, (ly_do, duong) in KHONG_CUA_GHI.items():
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
    """Danh sách ngoại lệ không trần là cách một phép thử tự tắt mình.

    6 (09/9/2026) → 8 (19/9/2026) → 9 (24/9/2026, bàn làm việc P.TGĐ tour đoàn) → 8 (24/9/2026,
    vòng 3/3: bàn làm việc tách sang nhóm riêng).

    LẦN NÀY TRẦN ĐI XUỐNG, và đó là chuyện đáng ghi. Dòng cảnh giác viết cùng ngày ở bản trước đã
    dặn: nếu lại nâng trần với cùng một lý do thì lý do ấy đã thành thói quen, và việc phải làm là
    ĐỔI CÁCH ĐẾM chứ không phải nâng tiếp. Vòng 3/3 tới đúng chỗ ấy nên đã tách `BAN_LAM_VIEC`
    thành nhóm riêng, có trần riêng và có thêm một câu hỏi riêng phải trả lời.

    CHI_XEM trở lại đúng con số ngày 19/9/2026 — trước khi bàn làm việc đầu tiên ra đời.
    """
    assert len(CHI_XEM) <= 8, (
        f"Đang khai {len(CHI_XEM)} màn hình chỉ xem. Ngày 09/9/2026 là 6, ngày 19/9 là 8. Con số này "
        "to lên nghĩa là mỗi lần đỏ lại thêm một dòng thay vì hỏi con số kia vào hệ thống bằng cửa "
        "nào. Bàn làm việc theo vai KHÔNG khai ở đây – nhóm ấy là BAN_LAM_VIEC.")


def test_ban_lam_viec_co_tran_rieng_va_chi_duoc_cua_ghi_cua_minh():
    """Nhóm bàn làm việc có trần RIÊNG và phải trả lời thêm MỘT CÂU nữa.

    Câu ấy là: cửa GHI của chính vai này nằm ở đâu. Một bàn làm việc không có cửa ghi nào mà cũng
    không chỉ ra được cửa ghi của mình thì nó là một bảng tin, không phải một bàn làm việc — và
    người mở nó hằng ngày sẽ dần đọc nó như đọc báo.

    Trần 3: phòng Kinh doanh Đoàn có ba vai (P.TGĐ, Sale Admin, NV Sales đoàn). Vai thứ ba lập dự
    toán nên màn hình của họ CÓ cửa ghi thật và sẽ không vào nhóm này — nhưng để trần ở 3 thì dòng
    thứ tư phải dừng lại giải thích vì sao lại có thêm một vai chỉ đọc nữa, thay vì trôi qua.
    """
    assert len(BAN_LAM_VIEC) <= 3, (
        f"Đang khai {len(BAN_LAM_VIEC)} bàn làm việc chỉ đọc. Mỗi dòng thêm vào đây là một vai được "
        "cho một màn hình mà không có việc nào bấm được trên đó – hỏi lại xem vai ấy làm gì.")
    thieu = [d for d, x in BAN_LAM_VIEC.items() if len(x) < 3 or not str(x[2]).strip()]
    assert not thieu, (
        f"Bàn làm việc khai thiếu CỬA GHI của vai: {thieu}. Phải ghi rõ cửa ghi nằm ở đâu, và chú "
        "thích ngay trên dòng ấy phải nói vì sao nó không nằm trên màn hình này.")
