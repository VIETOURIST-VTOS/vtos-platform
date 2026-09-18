# -*- coding: utf-8 -*-
"""TC-44 · KẾT QUẢ KINH DOANH — hai biểu đồ cùng kỳ, theo bản vẽ anh Tuấn gửi 16/9/2026.

Anh Tuấn gửi bản vẽ hai thẻ cạnh nhau (Doanh thu · Lợi nhuận trước thuế), một bộ chọn kỳ dùng
chung, và chốt ba điều:

  · chọn "Năm" thì biểu đồ chia thành 12 tháng của năm ấy;
  · chọn "Tháng" hay "Quý" thì VẪN mười hai cột ấy, chỉ TÔ ĐẬM phần đang chọn;
  · ô chọn năm liệt kê từ 2026 tới năm hiện tại.

═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT HÌNH CHO CẢ BA KỲ — VÌ SAO ĐÓ LÀ LỰA CHỌN ĐÚNG, KHÔNG PHẢI LỰA CHỌN LƯỜI
═══════════════════════════════════════════════════════════════════════════════════════════════
Cách hiển nhiên là mỗi bề rộng một hình: Tháng vẽ các ngày, Quý vẽ ba tháng, Năm vẽ mười hai
tháng. Ba nút ra ba hình khác nhau, và người đọc phải học ba cách đọc trên cùng một màn hình.

Bản này giữ MỘT hình mười hai cột cho cả ba, và chỉ đổi phần được tô đậm. Cái được là điều mà ba
hình riêng không cho: tháng 9 luôn nằm đúng chỗ của nó trong cả năm, nên nhìn một cái là thấy
tháng ấy so với mười một tháng còn lại — chứ không phải nhìn một cột đứng một mình rồi tự nhớ
mười một cột kia cao bao nhiêu.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CON SỐ Ở ĐẦU THẺ, VÀ CHÚNG PHẢI CÙNG MỘT KỲ
═══════════════════════════════════════════════════════════════════════════════════════════════
Hình trên (Doanh thu): tổng doanh thu kỳ · mục tiêu kỳ · tỉ lệ đạt.
Hình dưới (Lợi nhuận tour · Lợi nhuận trước thuế): tổng lợi nhuận kỳ · biên lợi nhuận.

BIÊN LỢI NHUẬN TÍNH TRÊN LỢI NHUẬN TRƯỚC THUẾ, không trên lợi nhuận tour, và giữ nguyên như vậy
sau TC-47: "biên" mà người đọc bảng điều hành hỏi là biên của công ty, đã gánh đủ chi phí chung.
Lấy lãi tour chia doanh thu ra một con số cao hơn hẳn và trông vẫn hợp lý — đó là chỗ dễ nhầm nhất
khi hình dưới có hai cột.

Cả bốn đều tính trên ĐÚNG kỳ đang chọn, không phải trên cả năm. Trộn một con số của năm vào một
thẻ đang hiện quý là lỗi không ai nhìn ra — mọi con số đều có thật, chỉ là của hai kỳ khác nhau.

BIÊN LỢI NHUẬN = LỢI NHUẬN ÷ DOANH THU, CỦA CÙNG KỲ, và trả None khi doanh thu chưa có hoặc bằng
0. "Biên lợi nhuận trên doanh thu 0" là một câu không có nghĩa, và mọi con số trả ra cho nó đều
gây hiểu nhầm.

═══════════════════════════════════════════════════════════════════════════════════════════════
KHÔNG CÓ PHÉP TÍNH DOANH THU THỨ HAI Ở ĐÂY
═══════════════════════════════════════════════════════════════════════════════════════════════
Từng tháng gọi đúng hàm mà bảng điều hành và biểu đồ xu hướng đang gọi
(`xu_huong.doc_that` → `ket_qua_that.thang`, `reports.income_statement` có lọc pháp nhân).
Viết một truy vấn riêng ở đây là để kho có hai công thức cho cùng một câu hỏi, và ngày chúng lệch
nhau thì không ai biết tin bên nào.

TC-47 (16/9/2026) ĐỔI CHÍNH PHÉP TÍNH ẤY, không đổi khối này: mốc là ngày Điều hành đóng số chứ
không phải ngày Kế toán xác nhận, phạm vi là Vietourist mẹ chứ không phải cả tập đoàn, và giá vốn
rỗng không còn đọc thành 0. Lý do từng điều nằm ở đầu services/ket_qua_that.py. Hệ quả nhìn thấy
được: con số doanh thu và lợi nhuận trên thẻ này ĐỔI so với bản trước — không phải mất số.

MỤC TIÊU KỲ ĐỌC THẲNG Ô KỲ ẤY, KHÔNG CỘNG TỪ THÁNG. Anh Tuấn chốt 16/9: chỉ tiêu năm và quý do
Hội đồng quản trị nhập riêng. Cộng 12 tháng lại để ra mục tiêu năm là xoá mất một quyết định quản
trị và thay bằng một phép cộng — xem chú thích TC-44 trong services/ke_hoach.py.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.services import ke_hoach as KH
from app.services import xu_huong as XH

# Hai chỉ tiêu của khối, và cặp khoá nối chúng lại: chuỗi xu hướng ở xu_huong dùng một mã, bảng kế
# hoạch dùng một mã. Khai cặp ấy ở ĐÚNG MỘT chỗ — hai chỗ thì ngày một bên đổi tên là ngày biểu đồ
# và mục tiêu nói về hai thứ khác nhau mà vẫn vẽ chồng lên nhau.
CHI_TIEU = (
    {"ma": "doanh_thu", "ma_xu_huong": "doanh_thu_thang", "ten": "Doanh thu",
     "co_ke_hoach": True, "hinh": "tren"},
    # TC-47 · HAI CỘT ĐI CÙNG NHAU Ở HÌNH DƯỚI — anh Tuấn 16/9/2026: "1 cột là lợi nhuận tour,
    # 1 cột là LN trước thuế". Chúng ở CÙNG một hình vì cùng đơn vị tiền và cùng đáng so trực tiếp;
    # doanh thu ở hình TRÊN vì lớn hơn chúng cả một bậc, vẽ chung thì hai cột lãi bẹp xuống thành
    # hai vạch không đọc được.
    #
    # HAI HÌNH, MỘT TRỤC NGANG — anh chốt "hai hình, chung trục ngang". Mỗi hình có trục tung riêng
    # của nó, và ĐÓ MỚI LÀ ĐIỂM: luật MỘT TRỤC TUNG cấm vẽ hai thang đo chồng lên nhau trong cùng
    # một khung, chứ không cấm hai khung xếp dọc. Tháng 9 của hình trên nằm đúng trên tháng 9 của
    # hình dưới, nên mắt đọc được "doanh thu tháng ấy cao mà lãi thì không" — điều mà một hình hai
    # trục tung cũng bày ra, nhưng bày kèm một phép so sai giữa hai thang đo.
    {"ma": "loi_nhuan_tour", "ma_xu_huong": "lai_tour_thang", "ten": "Lợi nhuận tour",
     "co_ke_hoach": False, "hinh": "duoi"},
    {"ma": "loi_nhuan_truoc_thue", "ma_xu_huong": "ln_ke_toan_thang",
     "ten": "Lợi nhuận trước thuế", "co_ke_hoach": False, "hinh": "duoi"},
)


def ky_mac_dinh(kind: str, hom_nay: date | None = None) -> str:
    """Kỳ mở sẵn khi vào màn hình: kỳ ĐANG CHẠY của bề rộng ấy.

    Không mở sẵn kỳ đã đóng gần nhất: người mở bảng điều hành hỏi "công ty đang thế nào", không
    hỏi "tháng trước thế nào".
    """
    d = hom_nay or date.today()
    if kind == XH.KY_THANG:
        return f"{d.year:04d}-{d.month:02d}"
    if kind == XH.KY_QUY:
        return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"
    return f"{d.year:04d}"


def bien_loi_nhuan(loi_nhuan: float | None, doanh_thu: float | None) -> float | None:
    """Lợi nhuận ÷ doanh thu của CÙNG kỳ. None khi thiếu một vế hoặc doanh thu bằng 0."""
    if loi_nhuan is None or doanh_thu is None or doanh_thu == 0:
        return None
    return loi_nhuan / doanh_thu


def _tong(phan: list[float | None]) -> float | None:
    """Tổng của một dãy tháng — None nếu THIẾU một tháng.

    Cùng luật với `xu_huong.doc_theo_ky` và với kế hoạch hợp nhất: cộng phần đã có rồi gọi đó là
    tổng kỳ cho ra một con số nhỏ hơn thật mà nhìn không khác gì con số đầy đủ.
    """
    if any(p is None for p in phan):
        return None
    return float(sum(phan))


def bang(db: Session, kind: str = XH.KY_NAM, ky: str = "",
         hom_nay: date | None = None) -> dict:
    """Số liệu cho cả khối Kết quả kinh doanh: 12 cột tháng + bốn con số của kỳ đang chọn."""
    hom_nay = hom_nay or date.today()
    if kind not in XH.TEN_KY:
        raise ValueError(f"bề rộng kỳ chưa khai: {kind!r}")
    ky = ky or ky_mac_dinh(kind, hom_nay)
    if KH.be_rong(ky) != kind:
        raise ValueError(f"mã kỳ {ky!r} không phải bề rộng {kind!r}")

    nam = int(str(ky)[:4])
    cac_thang = [f"{nam:04d}-{m:02d}" for m in range(1, 13)]
    trong_ky = set(XH.thang_cua_ky(ky))

    # ══════════════════════════════════════════════════════════════════════════════════════════
    # TC-64 · HỎI MỘT LẦN CHO MỘT THÁNG, KHÔNG PHẢI BA LẦN — anh Tuấn 18/9/2026: "kiểm tra lý do
    # load rất chậm".
    # ══════════════════════════════════════════════════════════════════════════════════════════
    # Đo trên bản chạy thật: cửa này mất 1,7–2,3 giây MỖI LẦN gọi, không có lần nào nhanh hơn.
    # Đếm ra thì với mỗi tháng trong mười hai tháng, `ket_qua_that.thang()` bị gọi BA lượt riêng
    # biệt — một lượt cho `thieu_thang` ở dưới, một cho chỉ tiêu doanh thu, một cho lợi nhuận tour
    # — và cả ba hỏi CÙNG một câu về CÙNG một tháng. `ke_hoach.hop_nhat()` cũng bị gọi lại cho
    # từng chỉ tiêu có kế hoạch.
    #
    # `nho` là chỗ nhớ của ĐÚNG MỘT LẦN GỌI hàm này, không phải chỗ nhớ sống qua nhiều lần: nó
    # sinh ra ở đây và chết khi hàm trả về. Nhờ vậy nó không thể trả số cũ cho lần bấm sau — thứ
    # duy nhất nó bỏ đi là những lượt hỏi TRÙNG bên trong một lần dựng bảng.
    #
    # Truyền tường minh chứ KHÔNG gắn ngầm vào phiên `db`: một chỗ nhớ nấp trong đối tượng phiên
    # là thứ sẽ trả số cũ cho một cửa GHI nào đó trong tương lai mà không ai ngờ tới.
    nho: dict = {}
    doc = XH.doc_that(db, nho=nho)

    # KỲ ĐANG CHẠY: chỉ cộng những tháng ĐÃ TRÔI, và nói rõ "đến hôm nay".
    #
    # Không có nhánh này thì cả năm 2026 hiện "—" cho tới hết tháng 12, vì tháng 10–11–12 chưa có
    # số và luật "thiếu một tháng thì cả kỳ chưa có số" bắt trả None. Luật ấy đúng cho kỳ ĐÃ ĐÓNG —
    # ở đó một tháng trống nghĩa là ai đó chưa nộp sổ. Với kỳ ĐANG CHẠY thì tháng 12 trống không
    # phải chỗ thiếu, nó là tháng chưa xảy ra; đòi nó có số là đòi một điều vô lý.
    #
    # Cùng cách đặt vấn đề đã dùng ở TC-42 (`xu_huong.ky_dang_chay`): con số vẫn hiện, nhưng đi kèm
    # chữ "đến hôm nay" và KHÔNG bao giờ đứng cạnh một kỳ đủ ngày mà không có nhãn ấy.
    moc_nay = f"{hom_nay.year:04d}-{hom_nay.month:02d}"
    dang_chay = max(trong_ky) >= moc_nay
    de_cong = {t for t in trong_ky if t <= moc_nay} if dang_chay else trong_ky

    # TC-47 · Những gì CÒN THIẾU của từng tháng, đọc một lần cho cả khối. Đây không phải số phụ:
    # cột chính chỉ gồm chuyến đủ số, nên nếu không nói ra phần thiếu thì người đọc tưởng cột ấy là
    # toàn bộ tháng. Đọc qua ĐÚNG hàm mà `xu_huong` đang gọi — không truy vấn riêng ở đây.
    from app.services import ket_qua_that as KQ
    thieu_thang = {t: KQ.thang(db, t, nho=nho) for t in cac_thang}

    ra_ct = []
    so = {}
    for ct in CHI_TIEU:
        # Từng tháng đọc qua ĐÚNG hàm mà biểu đồ xu hướng dùng. `None` giữ nguyên là None: tháng
        # chưa có số là ô trống đúng vị trí, không phải cột cao 0.
        gt = [doc(ct["ma_xu_huong"], t) for t in cac_thang]
        so[ct["ma"]] = _tong([g for t, g in zip(cac_thang, gt) if t in de_cong])

        cot = [{"ky": t, "thang": i + 1,
                "gia_tri": None if g is None else float(g),
                "trong_ky": t in trong_ky}
               for i, (t, g) in enumerate(zip(cac_thang, gt))]

        # TC-47 · KHÚC MỜ: doanh thu của chuyến ĐÃ đóng số mà CHƯA có giá vốn. Chỉ gắn vào cột
        # doanh thu, vì đúng những chuyến ấy bị bỏ ra khỏi cả doanh thu lẫn lãi (xem chú thích
        # "vì sao doanh thu cũng phải bỏ chuyến thiếu giá vốn ra" ở đầu services/ket_qua_that.py).
        # Không có khúc này thì phần doanh thu ấy biến mất khỏi màn hình mà không ai biết.
        if ct["ma"] == "doanh_thu":
            for o, t in zip(cot, cac_thang):
                o["cho"] = float(thieu_thang[t]["dt_thieu_gia_von"])

        ke_hoach = None
        if ct["co_ke_hoach"]:
            # VẠCH KẾ HOẠCH CHẠY THEO TỪNG THÁNG, không phải một vạch ngang: chỉ tiêu tháng 1 khác
            # tháng 12, và một vạch ngang duy nhất là nói dối về cả mười một tháng còn lại.
            kh_thang = [KH.hop_nhat(db, t, nho=nho)[ct["ma"]] for t in cac_thang]
            ke_hoach = [None if not h["du"] else float(h["gia_tri"]) for h in kh_thang]

        ra_ct.append({**{k: ct[k] for k in ("ma", "ten", "hinh")},
                      "cot": cot, "ke_hoach": ke_hoach})

    # PHẦN CÒN THIẾU CỦA ĐÚNG KỲ ĐANG CHỌN — cộng trên `de_cong`, cùng tập tháng với bốn con số ở
    # đầu thẻ. Cộng trên cả 12 tháng thì dòng chân thẻ nói về một kỳ khác với các con số ngay trên
    # nó, và đó đúng là loại lỗi "mọi con số đều có thật, chỉ là của hai kỳ khác nhau".
    #
    # ĐẶT TRƯỚC dòng đọc mục tiêu là CỐ Ý: sau dòng ấy không được còn phép cộng nào, để không ai
    # lỡ tay chen một `sum(...)` vào giữa mục tiêu và giá trị trả ra — xem phép thử TC-44
    # "muc_tieu_ky_khong_bao_gio_cong_tu_thang".
    trong = [thieu_thang[t] for t in sorted(de_cong)]
    con_thieu = {
        "chuyen_thieu_gia_von": sum(x["thieu_gia_von"] for x in trong),
        "tien_thieu_gia_von": float(sum(x["dt_thieu_gia_von"] for x in trong)),
        "chuyen_chua_gan_phap_nhan": sum(x["chua_gan_phap_nhan"] for x in trong),
        "tien_chua_gan_phap_nhan": float(sum(x["dt_chua_gan_phap_nhan"] for x in trong)),
        # Ai đi nhập, ghi thẳng ở đây: màn hình chỉ bày, không tự đoán tên bộ phận (ranh giới 09/9).
        "ai_nhap_gia_von": "Điều hành",
        "ai_gan_phap_nhan": "Hành chính",
        "co_nguon": all(x["co_nguon"] for x in trong) if trong else False,
    }

    # 17/9/2026 · SỐ VÀO BẰNG CỬA ĐÓNG SỐ BÙ (Chủ tịch ký thay các phòng ban cho lô kho quyết toán
    # cũ T1–T6/2026). Không phải "còn thiếu" nên KHÔNG nằm trong `con_thieu`: số đã đủ, chỉ là nó
    # vào hệ bằng một chữ ký khác chữ ký vận hành. Nhưng người đọc bảng phải biết — một tháng mà
    # gần như toàn bộ là số bù thì nó là số nhập lại từ Excel, chưa qua vòng duyệt của Điều hành và
    # Kế toán, và mức tin vào nó khác hẳn tháng vận hành thật.
    so_bu = sum(x.get("dong_so_bu", 0) for x in trong)
    du_so = sum(x["du_so"] for x in trong)
    ky_bu = {
        "so_chuyen": so_bu,
        "tren_tong_du_so": du_so,
        "ty_le": round(so_bu / du_so, 4) if du_so else None,
        "ai_ky": "Chủ tịch ký thay các phòng ban (chốt 17/9/2026)",
        "ghi_chu": ("Số của lô kho quyết toán cũ được nhập lại từ tệp Excel của Điều hành và đóng "
                    "số bù; mốc kỳ lấy theo ngày kết thúc chuyến. Khi vào vận hành chính thức, "
                    "phòng nào ký phòng đó theo đúng vai trò thiết lập."),
    }

    # MỤC TIÊU ĐỌC THẲNG Ô KỲ ẤY — xem chú thích đầu tệp.
    muc_tieu = KH.hop_nhat(db, ky)
    mt_doanh_thu = muc_tieu["doanh_thu"]
    dt = so.get("doanh_thu")
    ln = so.get("loi_nhuan_truoc_thue")

    return {
        "kind": kind, "kind_ten": XH.TEN_KY[kind], "ky": ky, "nam": nam,
        "nam_chon_duoc": KH.cac_nam(hom_nay),
        # KỲ ĐANG CHẠY CỦA BỀ RỘNG NÀY, để màn hình biết đâu là mốc "hôm nay" mà KHÔNG phải tự đọc
        # đồng hồ của máy người dùng. Máy người dùng có thể sai ngày, sai múi giờ, hoặc đơn giản là
        # đang ở nửa kia quả đất; lúc ấy ô chọn kỳ bày ra những tháng chưa xảy ra còn máy chủ thì
        # không có số cho chúng — người đọc thấy một biểu đồ rỗng và tưởng là mất số.
        "ky_hien_tai": ky_mac_dinh(kind, hom_nay),
        "chi_tieu": ra_ct,
        "con_thieu": con_thieu,
        "ky_bu": ky_bu,
        "tong_ky": {"doanh_thu": dt,
                    "loi_nhuan_tour": so.get("loi_nhuan_tour"),
                    "loi_nhuan_truoc_thue": ln},
        "muc_tieu": {
            "gia_tri": mt_doanh_thu["gia_tri"],
            "du": mt_doanh_thu["du"],
            "thieu": mt_doanh_thu["thieu"],
        },
        "ty_le_dat": KH.ty_le_dat(dt, mt_doanh_thu["gia_tri"]),
        "bien_loi_nhuan": bien_loi_nhuan(ln, dt),
        "so_thang_trong_ky": len(trong_ky),
        "dang_chay": dang_chay,
        "so_thang_da_troi": len(de_cong),
    }
