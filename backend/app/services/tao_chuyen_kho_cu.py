# -*- coding: utf-8 -*-
"""ĐỀ XUẤT TẠO CHUYẾN còn thiếu, đọc từ chính kho quyết toán cũ T1–T6/2026.

VÌ SAO PHẢI CÓ BƯỚC NÀY, VÀ VÌ SAO NÓ PHẢI LÀ MỘT BƯỚC RIÊNG

Chủ tịch duyệt cấu trúc ngày 13/9/2026 và giao nạp kho cũ lên để hệ thống chạy trên số thật của sáu
tháng đầu năm. Đo ngay sau đó thì lộ ra chốt chặn:

    VTOS có 1.150 chuyến, nhưng chỉ 47 / 436 mã của kho cũ khớp được. Thiếu 389.
    Đếm theo tháng khởi hành trong VTOS: T1 = 0 · T2 = 1 · T3 = 1 · T4 = 2 · T5 = 5 · T6 = 279.

Tức là bản nạp từ Vietrip chỉ mang về từ tháng 6 trở đi. Tháng 1–5/2026 gần như trống. Nên "nạp
quyết toán" không đủ: **không có chuyến thì dòng quyết toán không có chỗ treo vào**, và cửa nạp kho
cũ chặn cứng đúng ở đấy.

Việc tạo chuyến KHÔNG được gộp làm một với việc nạp quyết toán, dù gộp thì tiện hơn. Cửa nạp ngày
12/9 cố ý để "không có chuyến mang mã ấy" là chặn cứng mà cái tick bỏ-qua-cảnh-báo không cứu được —
vì tạo chuyến là GHI LẠI LỊCH SỬ VẬN HÀNH của công ty, không phải một hệ quả phụ của việc đọc tệp.
Biến nó thành hệ quả phụ thì ngày nào đó một lần bấm nhầm sẽ đẻ ra vài trăm chuyến mà không ai kịp
nhìn. Nên tệp này CHỈ ĐỀ XUẤT; phần ghi nằm ở cửa riêng, có người bấm và có nhật ký mang tên họ.

604 TỆP KHÔNG PHẢI 604 CHUYẾN — ĐÂY LÀ ĐIỀU QUAN TRỌNG NHẤT PHẢI PHÂN BIỆT

Đo trên kho ngày 13/9/2026:

    556  quyết toán MỘT CHUYẾN                  -> đề xuất tạo chuyến
     21  quyết toán VISA theo tháng             -> KHÔNG phải chuyến
     13  quyết toán LAND của đối tác            -> treo vào chuyến đã có, không tạo chuyến mới
     11  outbound GHÉP LẺ theo tháng            -> KHÔNG phải chuyến
      3  dịch vụ lẻ theo tháng                  -> KHÔNG phải chuyến

Và 37 tệp không đọc được 'Mã tour' thì 34 trong số đó thuộc đúng bốn loại "không phải chuyến" trên.
Chúng không hỏng — chúng KHÔNG CÓ mã tour vì chúng không phải một chuyến. Bộ đọc từ chối đoán mã từ
tên tệp, và chính sự từ chối ấy làm cho điều này lộ ra thay vì bị lấp đi bằng 37 chuyến ma.

Bốn loại kia có chỗ của chúng trong hệ: visa ở phân hệ visa, ghép lẻ và dịch vụ lẻ ở màn hình
/non-package (Đ-5 đọc từ đấy), land treo vào chuyến qua Đ-4 bên bán. Đề xuất tạo chuyến phải để
chúng ra ngoài, và phải NÓI RA là đã để ra ngoài — bỏ im lặng thì người duyệt tưởng đã nạp hết.

BA THỨ TỆP NÀY KHÔNG TỰ QUYẾT

1. NGƯỜI ĐIỀU HÀNH. Chuyến nào cũng bắt buộc có operator_id, mà con số ấy quyết định thưởng chuyến
   thuộc về ai. Gán bừa một nhân viên vào 556 chuyến lịch sử là đụng vào tiền của người thật. Tệp
   này ĐỌC RA tên điều hành ghi trong tệp để người duyệt nhìn, và để người duyệt chọn MỘT tài khoản
   nhận cả lô; sửa lại từng chuyến là việc của Điều hành sau.

2. HÌNH THỨC (trong nước / nước ngoài). Suy từ tên là suy được, nhưng suy ngầm rồi tính tiền theo
   cái suy ấy là chỗ sinh lỗi lặng — đúng lời chú thích ở `tours.hinh_thuc`. Để RỖNG, và biểu quyết
   toán sẽ hỏi người khai đúng như với mọi chuyến khác.

3. MÃ TẠM. 19 mã trong kho không phải mã mà là TÊN người lập gõ vào ô 'Mã tour': 'CÔNG TY DƯỢC',
   'CẢNG SÀI GÒN', 'MIỀN TÂY 5N4Đ'… Tạo chuyến mang mã ấy thì nó nằm trong danh sách tour mãi mãi.
   Tệp này sinh mã tạm có tiền tố KHOCU- kèm ngày lấy từ TÊN TỆP, đánh dấu rõ là máy đặt, và liệt kê
   riêng ra để Điều hành sửa dần — đúng chỉ đạo 13/9: chuyển hết lên rồi sửa dần.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

# Nguồn của mọi chuyến do cửa này tạo. Cùng quy ước với `intake_kho_cu.NGUON` để gỡ lại được.
NGUON = "kho_cu_h1_2026"

# Tiền tố mã tạm. Nhìn vào mã là biết ngay chuyến này máy đặt tên, chưa ai xác nhận.
TIEN_TO_TAM = "KHOCU-"

# Bốn loại tệp KHÔNG phải một chuyến, và chỗ đúng của chúng trong hệ.
KHONG_PHAI_CHUYEN = {
    "visa_thang": "Quyết toán visa theo tháng – thuộc phân hệ visa, không phải một chuyến",
    "ghep_le_thang": "Outbound ghép lẻ theo tháng – gom nhiều khách lẻ, xem ở /non-package (Đ-5)",
    "dich_vu_le_thang": "Dịch vụ lẻ theo tháng – xem ở /non-package (Đ-5)",
    "land_doi_tac": "Quyết toán LAND của đối tác – treo vào chuyến đã có qua Đ-4 bên bán",
}


def _khong_dau(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").upper()


def khoa_tep(ten_tep: str) -> str:
    """Khoá ghép theo TÊN TỆP: bỏ đuôi, bỏ dấu, bỏ mọi ký tự không phải chữ/số, hạ chữ thường.

    Đây là cầu nối duy nhất sang bản đối chiếu H1 mà Kế toán đã chốt – chỗ duy nhất có tổng thu và
    tổng chi đúng ở mức chuyến. Bản ấy gọi tên chuyến bằng tên tệp chứ không bằng mã tour: đo ngày
    13/9/2026 trên 624 dòng, chỉ 10 dòng mang mã tour đúng dạng.

    Phải chuẩn hoá mạnh tay, vì cùng một tệp được gõ ra ba kiểu ở ba chỗ: khoảng trắng thừa, dấu
    tiếng Việt bị mã hoá thành "#U1ec0" khi giải nén, và đuôi ".xlsx" khi có khi không. Bỏ hết những
    thứ ấy thì còn lại phần ổn định.
    """
    t = re.sub(r"\.(xlsx|xlsm|xls)$", "", (ten_tep or "").strip(), flags=re.I)
    # Tên giải nén từ tệp nén có thể mang "#U1ec0" thay cho ký tự tiếng Việt – trả lại trước khi bỏ dấu.
    t = re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)
    return re.sub(r"[^a-z0-9]", "", _khong_dau(t).lower())


def phan_loai(ten_tep: str, ma_tour: str = "") -> str:
    """Tệp này là một CHUYẾN, hay là một trong bốn loại không phải chuyến?

    Phân loại theo TÊN TỆP chứ không theo nội dung, và đó là lựa chọn có lý do: bốn loại kia đều là
    bảng gom nhiều việc lẻ trong một tháng, nên bên trong chúng trông y hệt một bảng chi bình
    thường. Thứ phân biệt được chúng là cái tên mà người lập đặt — 'QUYẾT TOÁN VISA MỸ THÁNG 4',
    'QT OUTBOUND GHÉP LẺ T01.26'. Đo trên 604 tệp: cách này xếp đúng 34/37 tệp không có mã tour.

    NGOẠI LỆ CỦA LAND — đo lại ngày 16/9/2026 trên 13 tệp LAND trong kho:

        11 tệp là BẢNG THÁNG của đối tác  – 'LAND PHU QUOC THANG 01.2026', 'LAND TOUR MIỀN BẮC
                                            THÁNG 5.2026'. Đúng là không phải chuyến.
         2 tệp là QUYẾT TOÁN MỘT ĐOÀN     – 'QTT LAND VĨNH HY 03.03.2026' (mã DOANVH030326, 1 khách,
                                            7 dòng chi), 'QTT ĐOÀN LAND PT 04.06.2026'
                                            (mã DOANPT040626, 3 khách, 17 dòng chi).

    Hai tệp sau có ĐỦ ba thứ mà một chuyến cần: mã thật, ngày đi, và dòng chi phí của chính đoàn ấy.
    Xếp chúng vào 'không phải chuyến' chỉ vì chữ LAND trong tên là bỏ rơi 49,7 triệu chi phí có
    chứng từ. Phân biệt bằng thứ đo được: tên có THÁNG / T<số> là bảng tháng; tên có NGÀY đầy đủ
    (dd.mm.yyyy) là một đoàn. Luật này tách đúng 11/2 trên cả 13 tệp, không sót và không bắt oan.
    """
    T = _khong_dau(ten_tep)
    if "LAND" in T and not re.search(r"THANG|\bT\d", T) and ngay_tu_ten_tep(ten_tep):
        return "mot_chuyen"
    if "VISA" in T:
        return "visa_thang"
    if re.search(r"(OUTBOUND|\bOB\b).{0,6}GHEP\s*LE", T) or "GHEP LE" in T:
        return "ghep_le_thang"
    if re.search(r"\bLE\s*T\s*\d", T) or re.search(r"LE\s+THANG", T):
        return "dich_vu_le_thang"
    if "LAND" in T:
        return "land_doi_tac"
    return "mot_chuyen"


_RE_NGAY_TEN = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})")


def ngay_tu_ten_tep(ten_tep: str) -> date | None:
    """Ngày khởi hành đọc từ TÊN TỆP – CHỈ dùng cho mã tạm, không dùng thay ngày trong tệp.

    Bộ đọc `nap_kho_cu` cố ý không suy gì từ tên tệp, và luật ấy giữ nguyên cho mọi con số. Ở đây
    tên tệp chỉ dùng để ĐẶT TÊN cho một chuyến mà chính tệp không khai nổi mã — tức là dùng để tạo
    một cái nhãn, không phải để tạo một con số. Hai việc khác hẳn nhau.
    """
    m = _RE_NGAY_TEN.search(ten_tep or "")
    if not m:
        return None
    d, t, n = (int(x) for x in m.groups())
    if n < 100:
        n += 2000
    if not (1 <= d <= 31 and 1 <= t <= 12 and 2020 <= n <= 2030):
        return None
    try:
        return date(n, t, d)
    except ValueError:
        return None


_RE_NGAY_MA = re.compile(r"(\d{6})$")


def ngay_tu_ma(ma: str) -> date | None:
    """Ngày khởi hành đọc từ SÁU CHỮ SỐ CUỐI của mã – quy ước đặt mã của chính công ty (DDMMYY).

    Đây KHÔNG phải suy đoán, mà là đọc một quy ước đã đo được. Trên 388 tệp có đủ cả ngày ghi trong
    tệp lẫn một mã kết thúc bằng sáu chữ số: **368 khớp nhau trong vòng 3 ngày (94%)**, 20 lệch.

    Vì có 6% lệch nên đây chỉ là ĐƯỜNG LUI CUỐI CÙNG: ngày ghi trong tệp luôn thắng, rồi đến ngày
    trên tên tệp, cuối cùng mới đến đây. Nó cứu được 19 tệp mà cả hai nguồn trên đều câm — phần lớn
    là tệp đặt tên bằng chính mã ("SM000.05120326.xlsx"), không có chỗ nào khác ghi ngày.
    """
    g = _RE_NGAY_MA.search((ma or "").strip())
    if not g:
        return None
    s = g.group(1)
    try:
        return date(2000 + int(s[4:6]), int(s[2:4]), int(s[0:2]))
    except ValueError:
        return None


def ngay_tu_duoi_ten_tep(ten_tep: str) -> date | None:
    """Ngày đọc từ SÁU CHỮ SỐ CUỐI CỦA TÊN TỆP – cùng quy ước DDMMYY của công ty, chỗ khác.

    VÌ SAO CẦN THÊM ĐƯỜNG NÀY

    `ngay_tu_ten_tep` đòi ngày có dấu ngăn ('03.03.2026'). `ngay_tu_ma` đọc sáu chữ số cuối, nhưng
    đọc ở Ô 'Mã tour' – mà có tệp đặt TÊN bằng chính mã và bỏ trống ô ấy. Hai đường cùng câm, dù
    ngày nằm ngay trên tên tệp.

    Đo ngày 16/9/2026 trên 604 tệp: đúng 2 tệp rơi vào khe này – 'SM001.04090126.xlsx' (40 khách,
    160,3 triệu) và 'SMI.05090126.xlsx' (20 khách, 101,9 triệu). Cả hai ghi 'Mã tour' là '3VSV' –
    bốn ký tự, không qua nổi `la_ma_that` – nên trước đây bị xếp 'thiếu ngày' và bỏ hẳn ra ngoài.
    262,2 triệu doanh thu của khách có tên tuổi nằm ngoài hệ vì một dấu chấm thiếu trong tên tệp.

    Vẫn là ĐƯỜNG LUI CUỐI, sau cả ngày trong tệp, ngày trên tên tệp và ngày trong mã: quy ước DDMMYY
    đo được 94% khớp, tức 6% lệch, nên nó chỉ được dùng khi mọi nguồn đáng tin hơn đều câm.
    """
    t = re.sub(r"\.(xlsx|xlsm|xls)$", "", (ten_tep or "").strip(), flags=re.I)
    return ngay_tu_ma(t)


# Lệch quá ngần này thì phần đầu tệp là VỎ MẪU CŨ, không phải thông tin của chuyến này.
LECH_LA_VO_CU = 60


def vo_mau_cu(d: dict) -> bool:
    """Phần đầu tệp (mã, ngày) có phải là vỏ của một tệp mẫu chưa xoá không?

    Dấu hiệu: ngày ghi TRONG TỆP lệch quá 60 ngày so với ngày trên TÊN TỆP. Người lập đặt tên tệp
    theo chuyến mình đang làm, nên tên tệp là thứ đáng tin về NGÀY; còn ô 'Mã tour' và 'Ngày đi' thì
    nằm sẵn trong mẫu và rất dễ quên sửa.

    Đo trên 604 tệp: luật này bắt đúng 106 tệp, và CẢ 106 đều mang mã 'PT14012022' – tức là đúng
    một ổ, không bắt oan tệp nào. Đó là 112 tệp 'QT NAM CÁT TIÊN' của 112 ngày khác nhau trong
    2025–2026, tất cả chép từ một tệp Phan Thiết ngày 14/01/2022 và đều còn nguyên mã cũ, ngày cũ,
    và cùng một danh sách 22 khách.

    Gặp vỏ cũ thì BỎ cả mã lẫn ngày trong tệp, lấy ngày từ tên tệp và đặt mã tạm. Phần chi phí vẫn
    dùng được – đo trên chính các tệp ấy thì số dòng chi và số tiền khác nhau từng tệp, tức là nội
    dung có thật, chỉ cái vỏ là cũ.
    """
    nt = ngay_tu_ten_tep(d.get("ten_tep") or d.get("_tep") or "")
    nd = d.get("ngay_di")
    if not nt or not nd:
        return False
    if isinstance(nd, str):
        try:
            nd = date.fromisoformat(nd[:10])
        except ValueError:
            return False
    return abs((nd - nt).days) > LECH_LA_VO_CU


def la_ma_that(ma: str) -> bool:
    """Chuỗi này trông như một MÃ, hay là một cái TÊN gõ nhầm vào ô mã?

    Ba dấu hiệu, rút từ 436 mã có thật trong kho: mã không có dấu cách, mã có ít nhất một chữ số,
    và mã dài 6–24 ký tự. Đo lại trên chính kho ấy: 417 chuỗi qua được cả ba, 19 chuỗi không —
    và 19 chuỗi ấy đọc lên đều là tên ('CÔNG TY DƯỢC', 'BẾN TRE 1 NGÀY'), không sót cái nào là mã.
    """
    m = (ma or "").strip()
    return bool(m) and " " not in m and bool(re.search(r"\d", m)) and 6 <= len(m) <= 24


def _ma_tam(ten_tep: str, ngay: date | None) -> str:
    """KHOCU-DDMMYY-<vài chữ đầu của tên tệp>. Đủ để không trùng, và nhìn là biết máy đặt."""
    goc = re.sub(r"[^A-Z0-9]+", "", _khong_dau(ten_tep).replace(".XLSX", ""))[:8] or "X"
    ns = ngay.strftime("%d%m%y") if ngay else "000000"
    return f"{TIEN_TO_TAM}{ns}-{goc}"[:30]


def _ten_chuyen(d: dict, vo_cu: bool = False) -> str:
    """Tên chuyến: ưu tiên thứ người lập đã viết ra, cuối cùng mới lấy tên tệp.

    VỎ MẪU CŨ thì lấy thẳng TÊN TỆP. Ô 'Tên tour' nằm trong vỏ nên cũng là tên của chuyến khác —
    đo được: 112 tệp 'QT NAM CÁT TIÊN' đều có ô tên ghi 'PHAN THIẾT'. Tạo 112 chuyến Nam Cát Tiên
    mang tên Phan Thiết thì không ai tra ra được cái gì.
    """
    if not vo_cu:
        for k in ("ten_tour", "ten_doan"):
            v = (d.get(k) or "").strip()
            if v and len(v) > 2:
                return v[:200]
    t = (d.get("ten_tep") or d.get("_tep") or "").rsplit(".", 1)[0]
    return (t or "Chuyến kho cũ")[:200]


def de_xuat(d: dict, ma_da_co: set[str], ma_vo_cu: set[str] | None = None) -> dict:
    """Một tệp -> một dòng đề xuất. KHÔNG ghi gì, KHÔNG chạm cơ sở dữ liệu.

    `ma_da_co` là tập mã chuyến đang có trong VTOS, viết HOA. Người gọi truyền vào, để hàm này thuần
    tính toán và phép thử chạy được không cần cơ sở dữ liệu.
    """
    tep = d.get("ten_tep") or d.get("_tep") or ""
    loai = phan_loai(tep)
    ma_goc = (d.get("ma_tour") or "").strip()

    ra = {
        "tep": tep, "loai": loai, "ma_goc": ma_goc,
        "viec": "", "ma": "", "ten": "", "ngay_di": None, "ngay_ve": None,
        "so_khach": d.get("so_khach"), "dieu_hanh_ghi_trong_tep": (d.get("hdv") or {}).get("ten", "")
        if isinstance(d.get("hdv"), dict) else "",
        "ma_la_may_dat": False, "vi_sao": "",
    }

    if loai != "mot_chuyen":
        ra["viec"] = "bo_qua"
        ra["vi_sao"] = KHONG_PHAI_CHUYEN[loai]
        return ra

    # VỎ MẪU CŨ được xét TRƯỚC cả việc đối chiếu mã: mã trong vỏ cũ là mã của chuyến KHÁC, nên khớp
    # được với VTOS cũng không có nghĩa gì – khớp vào đúng chuyến sai.
    # VỎ CŨ LÂY LAN THEO MÃ, và phải thế. Luật ngày-lệch chỉ bắt được tệp mà TÊN TỆP có ngày đọc
    # được; 6 tệp mang mã 'PT14012022' có tên không đọc ra ngày nên thoát lưới, rồi giữ nguyên cái mã
    # đã bị 106 tệp khác chứng minh là của chuyến năm 2022. Một mã đã bị chứng minh là vỏ cũ thì nó
    # là vỏ cũ ở MỌI tệp mang nó – không có lý do gì để nó thật ở tệp này và giả ở tệp kia.
    vo_cu = vo_mau_cu(d) or (bool(ma_goc) and ma_goc.upper() in (ma_vo_cu or set()))
    ra["vo_mau_cu"] = vo_cu

    if not vo_cu and ma_goc and ma_goc.upper() in ma_da_co:
        ra.update(viec="da_co", ma=ma_goc, vi_sao="Chuyến đã có trong VTOS – chỉ nạp quyết toán")
        return ra

    # Thứ tự nguồn NGÀY, đáng tin giảm dần. Vỏ cũ thì bỏ hẳn ngày trong tệp.
    ngay = None if vo_cu else d.get("ngay_di")
    if isinstance(ngay, str):
        try:
            ngay = date.fromisoformat(ngay[:10])
        except ValueError:
            ngay = None
    if not isinstance(ngay, date):
        ngay = ngay_tu_ten_tep(tep) or ngay_tu_ma(ma_goc) or ngay_tu_duoi_ten_tep(tep)

    if vo_cu:
        ra["ma"] = _ma_tam(tep, ngay)
        ra["ma_la_may_dat"] = True
        ra["vi_sao"] = (f"Phần đầu tệp là VỎ MẪU CŨ: ngày ghi trong tệp lệch quá {LECH_LA_VO_CU} "
                        f"ngày so với ngày trên tên tệp, nên mã {ma_goc!r} là mã của chuyến khác")
    elif ma_goc and la_ma_that(ma_goc):
        ra["ma"] = ma_goc
    else:
        ra["ma"] = _ma_tam(tep, ngay)
        ra["ma_la_may_dat"] = True
        ra["vi_sao"] = (f"Ô 'Mã tour' ghi {ma_goc!r} – đây là TÊN, không phải mã" if ma_goc
                        else "Tệp không khai 'Mã tour'")

    if ngay is None:
        ra["viec"] = "thieu_ngay"
        ra["vi_sao"] = ("Không đọc được ngày đi trong tệp, và tên tệp cũng không có ngày. "
                        "Chuyến bắt buộc có ngày đi và ngày về – phải có người điền.")
        return ra

    ngay_ve = d.get("ngay_ve")
    if isinstance(ngay_ve, str):
        try:
            ngay_ve = date.fromisoformat(ngay_ve[:10])
        except ValueError:
            ngay_ve = None
    # Không đọc được ngày về thì lấy đúng ngày đi – một ngày. KHÔNG đoán số đêm từ tên ("3N2Đ"):
    # đoán sai thì mọi phép tính theo đêm sai theo, mà sửa một ô ngày thì rẻ.
    ra["ngay_di"] = ngay
    ra["ngay_ve"] = ngay_ve if isinstance(ngay_ve, date) and ngay_ve >= ngay else ngay
    ra["ten"] = _ten_chuyen(d, vo_cu)
    ra["viec"] = "tao_moi"
    return ra


def bang(ds: list[dict], ma_da_co: set[str]) -> dict:
    """Bảng XEM TRƯỚC cho người duyệt. Đây là toàn bộ những gì cửa ghi sẽ làm, nói ra trước."""
    # LƯỢT 1 – tìm những mã bị chứng minh là vỏ mẫu cũ, để lượt 2 áp cho mọi tệp mang mã ấy.
    ma_vo_cu = {(d.get("ma_tour") or "").strip().upper()
                for d in ds if vo_mau_cu(d) and (d.get("ma_tour") or "").strip()}
    hang = [de_xuat(d, ma_da_co, ma_vo_cu) for d in ds]

    # MÃ TẠM PHẢI DUY NHẤT. Mã tạm dựng từ ngày + vài chữ đầu tên tệp, nên hai tệp khác nhau vẫn có
    # thể ra cùng một chuỗi ("QUYẾT TOÁN …" và "QUYẾT TOÁN …"). Trùng mã thì cửa ghi sẽ gộp hai
    # chuyến khác nhau làm một, và không ai thấy vì cả hai đều có dòng. Thêm đuôi -2, -3 theo thứ tự.
    dem: dict[str, int] = {}
    for h in hang:
        if not h.get("ma_la_may_dat") or not h.get("ma"):
            continue
        k = h["ma"].upper()
        dem[k] = dem.get(k, 0) + 1
        if dem[k] > 1:
            h["ma"] = f"{h['ma']}-{dem[k]}"[:30]
    nhom: dict[str, list] = {}
    for h in hang:
        nhom.setdefault(h["viec"], []).append(h)

    tao = nhom.get("tao_moi", [])
    trung = {}
    for h in tao:
        trung.setdefault(h["ma"].upper(), []).append(h["tep"])
    trung = {k: v for k, v in trung.items() if len(v) > 1}

    return {
        "tong_tep": len(hang),
        "tao_moi": len(tao),
        "da_co": len(nhom.get("da_co", [])),
        "bo_qua": len(nhom.get("bo_qua", [])),
        "thieu_ngay": len(nhom.get("thieu_ngay", [])),
        "ma_may_dat": sum(1 for h in tao if h["ma_la_may_dat"]),
        # Nhiều tệp cùng ra một mã: hoặc là nhiều đợt của một chuyến, hoặc là mã sót từ tệp mẫu.
        # Không tự gộp và cũng không tự tách – nêu ra để người duyệt quyết.
        "ma_trung_nhau": trung,
        "bo_qua_theo_loai": {k: sum(1 for h in nhom.get("bo_qua", []) if h["loai"] == k)
                             for k in KHONG_PHAI_CHUYEN},
        "hang": hang,
    }
