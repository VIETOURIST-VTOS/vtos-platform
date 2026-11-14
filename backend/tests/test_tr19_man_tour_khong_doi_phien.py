# -*- coding: utf-8 -*-
"""TR-19 · MÀN TOUR NGỒI ĐỢI MỘT CÂU HỎI KHÔNG LIÊN QUAN GÌ TỚI TOUR.

TR-18 lên bản chạy và ăn. Đo lại trang HC001, tải lại khi máy đã ấm:

    số cửa gọi máy chủ   5    ->  3
    HTML về            487 ms ->  225 ms
    lịch trình hiện ra 3.241 ms -> 793 ms
    xong toàn bộ       3.422 ms -> 875 ms

Nhưng nhìn kỹ mạch thời gian thì chỗ chậm nhất không còn là tour nữa:

    cong/toi                       339 ms  ->  710 ms      (371 ms)
    tour-online/san-pham/6613      724 ms  ->  793 ms      ( 69 ms)
    .../danh-gia                   796 ms  ->  875 ms      ( 79 ms)

Tour chỉ tốn 69 ms. Gần một nửa thời gian còn lại là ngồi đợi /cong/toi — câu hỏi «ai đang
đăng nhập». Tìm ra chỗ chặn: TrangRieng.tsx dựng «Đang tải…» cho tới khi câu hỏi ấy trả lời
xong, nên ToursAgoda còn chưa được dựng, chưa gọi được cửa nào.

MÀ XEM TOUR VỐN KHÔNG CẦN ĐĂNG NHẬP — chính KS-16q đặt ra như vậy, và cả router cong_mo là
để phục vụ điều đó. Vòng này dựng màn tour ngay; phiên về lúc nào thì điền lúc ấy.

CHỖ PHẢI CẨN THẬN, và là lý do có phép thử 3-4-5: ba ô liên hệ của bước đặt tour khởi tạo
MỘT LẦN từ `toi`. Dựng sớm nghĩa là lúc ấy `toi` còn rỗng, và nếu không điền bù thì khách đã
đăng nhập vẫn phải gõ lại tên, số điện thoại, email — đổi một lỗi chậm lấy một lỗi phiền.
Điền bù phải chỉ chạm ô CÒN TRỐNG: khách gõ tên khác tên trong tài khoản (đặt hộ người nhà
là chuyện thường) thì tuyệt đối không được đè lên.

KHÔNG mở cho màn khách sạn và nhà hàng trong vòng này, nói rõ để không ai tưởng đã xong:
hai màn ấy nhận `ten` và `lienHe` dưới dạng chuỗi dựng sẵn, chưa có đường điền bù. Đo xong
từng màn rồi mở tiếp, không mở cả ba theo cảm giác.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TEP_TRANG = GOC / "web" / "components" / "cong" / "TrangRieng.tsx"
TEP_TOUR = GOC / "web" / "components" / "cong" / "ToursAgoda.tsx"


def trang() -> str:
    return TEP_TRANG.read_text(encoding="utf-8")


def tour() -> str:
    return TEP_TOUR.read_text(encoding="utf-8")


# ══ 1 · MÀN TOUR DỰNG NGAY ══════════════════════════════════════════════════════════════════

def test_tr19_1_man_tour_dung_truoc_cau_hoi_phien():
    s = trang()
    assert '{dang === "tours" ? <ToursAgoda toi={toi} moId={so} moDon={don} />' in s, \
        "nhánh tour phải đứng TRƯỚC phép thử !xong, nếu không nó vẫn đợi"
    i, j = s.index('dang === "tours"'), s.index("!xong ?")
    assert i < j, "nhánh tour vẫn nằm sau «Đang tải…» — chưa sửa được gì"


def test_tr19_2_hai_man_kia_giu_nguyen_loi_cu():
    """Chưa có đường điền bù cho khách sạn và nhà hàng thì chưa mở — mở mò là làm mất ô liên
    hệ đã điền sẵn của khách."""
    s = trang()
    assert "!xong ? <p style={{ padding: 24 }}>Đang tải…</p>" in s
    for can in ("<KhachSanVtd rieng moId={so} ten={ten} lienHe={lienHe} />",
                "coSdt={!!toi?.dien_thoai}", 'sdtCho={toi?.dien_thoai || ""}'):
        assert can in s, f"vòng này làm hỏng màn khác: mất {can}"


def test_tr19_3_khung_trang_va_cau_hoi_phien_con_nguyen():
    s = trang()
    assert "const { toi, xong } = useToiRieng();" in s
    assert "<KhungRieng dang={dang} toi={toi} xong={xong}>" in s, \
        "đầu trang vẫn cần «xong» để biết hiện «Đăng nhập» hay tên khách"


# ══ 2 · PHIÊN VỀ MUỘN THÌ ĐIỀN BÙ ═══════════════════════════════════════════════════════════

def test_tr19_4_co_dieu_dien_bu_khi_phien_ve_muon():
    s = tour()
    assert "useEffect(() => {\n    if (!toi) return;\n    setKh(" in s, "thiếu điều điền bù"
    assert re.search(r"\}, \[toi\]\);", s), "phải chạy lại đúng khi `toi` đổi"


def test_tr19_5_chi_dien_o_con_trong_khong_de_len_chu_khach_da_go():
    """Đây là phép thử quan trọng nhất của vòng: đè lên ô khách đã gõ là sửa sai tên người đi
    tour, và chỉ lộ ra sau khi đoàn đã khởi hành."""
    s = tour()
    i = s.index("if (!toi) return;")
    khoi = s[i:i + 400]
    for o in ("ho_ten", "dien_thoai", "email"):
        assert f"{o}: k.{o} ||" in khoi, f"ô {o} không có phép «còn trống thì mới điền»"
    assert "k.email || emailThat(toi.email)" in khoi, \
        "email phải qua emailThat — /cong/toi trả bản CHE (vi•••@gmail.com), điền bản che vào ô nhập là gửi đơn sai"


def test_tr19_6_khong_dong_vao_cach_khoi_tao_ban_dau():
    """Khách đã có phiên sẵn từ trước thì ba ô vẫn phải đầy ngay từ lượt dựng đầu tiên."""
    s = tour()
    assert 'const [kh, setKh] = useState<any>({ ho_ten: toi?.ho_ten || "", dien_thoai: toi?.dien_thoai || "", email: emailThat(toi?.email)' in s


# ══ 3 · KHÔNG LÀM HỎNG THỨ ĐANG CHẠY ════════════════════════════════════════════════════════

def test_tr19_7_bon_vong_truoc_con_nguyen():
    s = tour()
    for can in ["if (moId) moSp(moId); else tim();", "if (!ds) tim();",
                "const can = (sp.ct_rieng || []).includes(chon) ? chon : null;",
                'className="tra-moc"', 'className="tra-gio"', "BA_BUA.map", "tra-dnoi",
                "#vtd-access .tra a.ksv-btn", "#vtd-access .ksv.tra input[type=checkbox]"]:
        assert can in s, f"vòng này làm mất {can}"
    assert s.count("<h1") == 2 and s.count('<main className="ksv tra">') == 2
    assert s.count("onClick={moDat}") == 1


def test_tr19_8_duong_dat_tour_con_nguyen():
    s = tour()
    for can in ['id="tra-ngay"', "sp.mo_thanh_toan", 'className="tra-dates"', "setChon(c.tour_id)", "csMuc"]:
        assert can in s, f"vòng này làm mất {can}"
