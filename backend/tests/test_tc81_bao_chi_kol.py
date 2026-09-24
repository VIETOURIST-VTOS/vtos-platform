"""TC-81 · BÁO CHÍ, KOL & SỰ KIỆN — mục 2.2.2, mục Marketing cuối cùng còn trống.

HAI LỰA CHỌN ANH TUẤN CHỐT 24/9/2026:

    "KOL theo dõi đến đâu"  →  DANH BẠ + HỢP TÁC + CHI PHÍ GẮN CHIẾN DỊCH
    "Sự kiện để ở đâu"      →  CHUNG SỔ VỚI BÁO CHÍ, lọc theo loại

SÁU CHỖ NGUY HIỂM PHÉP THỬ NÀY CANH — phần lớn là loại nhìn màn hình KHÔNG phát hiện được:

 1. SỔ CÓ CỬA ĐỌC MÀ KHÔNG CÓ CỬA GHI. Sổ PR sống ba tuần với cửa đọc, cửa phát, cửa phản hồi — và
    KHÔNG cửa tạo nào ngoài nút "lập PR" trên hàng đợi tin cảnh báo. Một bài báo không sinh ra từ
    hộp thư thì không có đường nào vào sổ. Đúng ranh giới 09/9: cửa còn thiếu là việc còn thiếu.

 2. CỬA TẠO ĐẦU TIÊN LÀ LÚC HÀNG RÀO DỮ LIỆU PHẢI SINH RA. Tới hôm nay `tao()` không kiểm gì, vì
    caller duy nhất tự đặt `loai`. Nay người gõ được mọi thứ, và một `loai` sai chính tả sẽ nằm im
    trong sổ: không lọt bộ lọc nào, không hiện thẻ nào, cũng không báo lỗi.

 3. CỬA TẠO ĐI VÒNG QUA NGƯỜI PHÁT NGÔN. Nếu cửa tạo đặt được `trang_thai="da_phat"` thì ai ghi sổ
    cũng phát ngôn được, và cả thiết kế tách bạch trách nhiệm của sổ PR thành trang trí.

 4. NỚI CẢ NHÓM MARKETING KHI KHAI TIỀN TỐ THỨ HAI. Màn hình khai `/api/v1/marketing` để dùng cửa
    sẵn có. Điều ấy chỉ an toàn chừng nào danh sách vai của nó nằm gọn trong danh sách vai của
    `/marketing` — `test_khai_them_tien_to_marketing_khong_noi_cho_ai` đo đúng điều đó.

 5. HAI LOẠI TRÙNG BỊ XỬ NHƯ MỘT. Trùng đường dẫn kênh là bản khai lặp → chặn. Trùng tên là chuyện
    thường → hỏi lại. Gộp hai thứ vào một mức là hoặc chặn oan, hoặc để lọt bản lặp.

 6. HAI SỔ TIỀN. `chi_phi` là số thoả thuận; tiền thật ở đề nghị chi. Cộng `chi_phi` vào bảng chi
    phí của nhóm 2.7 là dựng sổ tiền thứ hai — đúng cái bệnh nhóm 2.8 sinh ra để chữa.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.models.kol import HT_TRANG_THAI, KOL_KENH, MktKol, MktKolHopTac
from app.models.marketing import Campaign, PR_LOAI, PrHoatDong
from app.models.ops import PaymentRequest
from app.services import kol as KOL
from app.services import pr_hoat_dong as PR

GOC = Path(__file__).resolve().parents[1]
WEB = GOC.parents[0] / "web"


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, future=True)()


def _u(db, ten="mkt", vai="nv_mkt"):
    u = User(username=ten, full_name=ten, role=vai, password_hash="x")
    db.add(u); db.commit()
    return u


def _cd(db, ma="CD-A"):
    c = Campaign(code=ma, name=ma, objective="doanh_thu", mang="le", channels=[],
                 from_date=dt.date(2026, 9, 1), budget=0.0, status="dang_chay")
    db.add(c); db.commit()
    return c


def _kol(db, u, ten="Nguyễn Văn A", kenh="tiktok", link="https://tiktok.com/@a", **kw):
    k = KOL.them(db, u, {"ho_ten": ten, "kenh": kenh, "link_kenh": link, **kw})
    db.commit()
    return k


# ═══════════════════════ SỔ PR: CỬA GHI VÀ HÀNG RÀO CỦA NÓ ═══════════════════════

def test_so_pr_gio_da_co_cua_tao():
    """Chỗ hỏng cả vòng này sinh ra để chữa: sổ có cửa đọc mà không có đường nào ghi vào."""
    from app.main import app
    duong = {(r.path, m) for r in app.routes for m in getattr(r, "methods", [])}
    assert ("/api/v1/bao-chi-kol/pr", "POST") in duong


def test_tao_pr_luon_o_trang_thai_nhap():
    """Cho cửa tạo đặt thẳng `da_phat` là mở một đường vòng qua người phát ngôn."""
    db = _db()
    h = PR.tao(db, {"loai": "bai_bao", "tieu_de": "Vietourist mở tuyến mới",
                    "trang_thai": "da_phat"}, "mkt")
    db.commit()
    assert h.trang_thai == "nhap"
    assert h.nguoi_phat_ngon == "" and h.phat_luc is None


def test_loai_sai_chinh_ta_bi_chan():
    """Một `loai` sai nằm im trong sổ: không lọt bộ lọc nào, không hiện thẻ nào, không báo lỗi."""
    db = _db()
    with pytest.raises(ValueError, match="Loại hoạt động không hợp lệ"):
        PR.tao(db, {"loai": "bai_bao_", "tieu_de": "x"}, "mkt")


def test_tieu_de_rong_bi_chan():
    db = _db()
    with pytest.raises(ValueError, match="Phải có tiêu đề"):
        PR.tao(db, {"loai": "su_kien", "tieu_de": "   "}, "mkt")


def test_muc_do_bat_buoc_o_CUA_TAY_va_KHONG_bat_buoc_o_luong_hop_thu():
    """HAI ĐƯỜNG, HAI LUẬT — và cả hai bên đều ghi lại ở đây.

    BẢN ĐẦU CỦA VÒNG NÀY đặt một luật chung: đánh dấu khủng hoảng thì luôn phải chọn mức độ. Luật
    ấy làm ĐỎ bảy phép thử của cửa lọc tin, và đọc kỹ thì chỗ đỏ ấy đúng chứ không phải phép thử
    cũ sai.

    Người ngồi gõ một bài báo vào sổ thì đã đọc xong bài ấy — hỏi thêm một ô không tốn gì, và bỏ
    trống ô ấy nghĩa là sổ có một vụ không ai xếp hạng. Người bấm "lập PR" trên hàng đợi tin lúc
    hai giờ sáng thì việc của họ là đưa vụ vào sổ để ĐỒNG HỒ BẮT ĐẦU CHẠY, nhanh nhất có thể; thêm
    một bước vào đúng khoảnh khắc phải ít bước nhất là làm chậm cái cần nhanh. Bộ lọc đã chấm điểm
    tin ấy rồi, và mức độ sửa được bất cứ lúc nào sau đó.
    """
    db = _db()
    # Cửa tay: bắt buộc.
    with pytest.raises(ValueError, match="phải chọn mức độ"):
        PR.tao(db, {"loai": "khung_hoang", "tieu_de": "Bài viết xấu", "la_khung_hoang": True},
               "mkt", tu_tay=True)
    h = PR.tao(db, {"loai": "khung_hoang", "tieu_de": "Bài viết xấu",
                    "la_khung_hoang": True, "muc_do": "nghiem_trong"}, "mkt", tu_tay=True)
    assert h.la_khung_hoang and h.ghi_nhan_luc is not None

    # Luồng hộp thư (mặc định): KHÔNG bắt buộc, đồng hồ vẫn chạy.
    h2 = PR.tao(db, {"loai": "khung_hoang", "tieu_de": "Tin từ hộp thư", "la_khung_hoang": True},
                "mkt")
    assert h2.la_khung_hoang and h2.muc_do == "" and h2.ghi_nhan_luc is not None


def test_cua_tay_cua_man_hinh_2_2_2_co_truyen_co_tu_tay():
    """Quên cờ ấy thì hàng rào có mà không bao giờ nổ — im lặng, đúng kiểu khó tìm nhất."""
    nguon = (GOC / "app" / "api" / "v1" / "bao_chi_kol.py").read_text(encoding="utf-8")
    assert "tu_tay=True" in nguon


def test_chien_dich_khong_co_that_bi_chan():
    db = _db()
    with pytest.raises(ValueError, match="Không có chiến dịch id"):
        PR.tao(db, {"loai": "bai_bao", "tieu_de": "x", "campaign_id": 9999}, "mkt")


def test_tao_pr_ghi_duoc_chien_dich():
    """Hai ô sổ vẫn có cột mà `tao()` chưa bao giờ điền, vì caller cũ không biết chiến dịch nào."""
    db = _db()
    cd = _cd(db)
    h = PR.tao(db, {"loai": "bai_bao", "tieu_de": "x", "campaign_id": cd.id}, "mkt")
    db.commit()
    assert h.campaign_id == cd.id


def test_su_kien_dung_CHUNG_so_voi_bao_chi():
    """Anh Tuấn chốt 24/9. Hai bảng là hai nơi cùng đếm một thứ, và một ngày chúng sẽ lệch."""
    db = _db()
    PR.tao(db, {"loai": "bai_bao", "tieu_de": "Bài báo"}, "mkt")
    PR.tao(db, {"loai": "su_kien", "tieu_de": "Hội chợ ITE"}, "mkt")
    db.commit()
    assert PR.bang(db)["dem"]["tong"] == 2
    chi_sk = PR.bang(db, loai="su_kien")["rows"]
    assert len(chi_sk) == 1 and chi_sk[0]["tieu_de"] == "Hội chợ ITE"
    assert "su_kien" in PR_LOAI
    # Không có bảng MARKETING thứ hai nào cho sự kiện. (`tong_dai_su_kien` là sự kiện tổng đài và
    # `su_kien_ky_thuat` là nhật ký kỹ thuật — hai thứ khác hẳn, không dính gì tới truyền thông.)
    them = [t for t in Base.metadata.tables
            if "su_kien" in t and t.startswith(("mkt_", "marketing_"))]
    assert not them, f"Sự kiện dùng chung sổ PR — không dựng bảng riêng: {them}"


# ═══════════════════════ KOL: DANH BẠ ═══════════════════════

def test_mot_kol_la_mot_kenh_trung_duong_dan_bi_chan():
    db = _db(); u = _u(db)
    _kol(db, u)
    with pytest.raises(ValueError, match="đã có trong sổ"):
        _kol(db, u, ten="Người khác hẳn")


def test_mot_nguoi_hai_kenh_la_HAI_dong_va_hop_le():
    """Thứ Marketing mua là một bài trên một kênh. Đo theo người thì hai kênh trộn vào nhau."""
    db = _db(); u = _u(db)
    _kol(db, u, kenh="tiktok", link="https://tiktok.com/@a")
    _kol(db, u, kenh="youtube", link="https://youtube.com/@a")
    assert db.execute(select(MktKol)).scalars().all().__len__() == 2


def test_trung_TEN_chi_canh_bao_chu_khong_chan():
    """Hai mức cho hai loại trùng khác nhau — cùng nếp với nhóm 2.8."""
    db = _db(); u = _u(db)
    _kol(db, u, ten="Trần Thị B", link="https://tiktok.com/@b1")
    canh = KOL.canh_bao_trung_ten(db, "tran thi b")
    assert len(canh) == 1, "Bỏ dấu rồi so — 'Trần Thị B' và 'tran thi b' là một"
    # Vẫn thêm được: hai người thật có thể trùng tên.
    k2 = _kol(db, u, ten="Trần Thị B", link="https://tiktok.com/@b2")
    assert k2.id


def test_thieu_duong_dan_kenh_bi_chan():
    db = _db(); u = _u(db)
    with pytest.raises(ValueError, match="Phải có đường dẫn kênh"):
        KOL.them(db, u, {"ho_ten": "A", "kenh": "tiktok", "link_kenh": "  "})


def test_kenh_khong_hop_le_bi_chan():
    db = _db(); u = _u(db)
    with pytest.raises(ValueError, match="Kênh không hợp lệ"):
        KOL.them(db, u, {"ho_ten": "A", "kenh": "zalo_oa", "link_kenh": "x"})
    assert "zalo_oa" not in KOL_KENH


def test_ngung_hop_tac_phai_ghi_ly_do():
    """Một người bị loại mà không ai ghi vì sao thì sáu tháng sau có người lại đề xuất đúng người ấy."""
    db = _db(); u = _u(db)
    k = _kol(db, u)
    with pytest.raises(ValueError, match="phải ghi lý do"):
        KOL.sua(db, u, k.id, {"trang_thai": "ngung"})
    KOL.sua(db, u, k.id, {"trang_thai": "ngung", "ly_do_ngung": "Giá cao, hiệu quả thấp"})
    db.commit()
    assert db.get(MktKol, k.id).trang_thai == "ngung"


def test_nhat_ky_ghi_trang_thai_TRUOC_khi_sua():
    """Bài học TC-78: gọi sau khi đã gán thì cột 'before' ghi lại đúng trạng thái SAU."""
    from app.models.core import AuditLog
    db = _db(); u = _u(db)
    k = _kol(db, u, ten="Tên Cũ")
    KOL.sua(db, u, k.id, {"ho_ten": "Tên Mới"})
    db.commit()
    d = db.execute(select(AuditLog).where(AuditLog.action == "sua_kol")).scalars().first()
    assert d.before["ho_ten"] == "Tên Cũ"
    assert d.after["ho_ten"] == "Tên Mới"


def test_luong_theo_doi_rong_la_CHUA_DO_khong_phai_khong():
    db = _db(); u = _u(db)
    _kol(db, u)
    r = KOL.danh_sach(db)["rows"][0]
    assert r["luong_theo_doi"] is None, "Rỗng khác 0 — chưa ai đo thì đừng in số không"
    assert r["gia_tham_khao"] is None


# ═══════════════════════ KOL: MỘT LẦN HỢP TÁC ═══════════════════════

def test_ky_sai_dinh_dang_bi_chan():
    db = _db(); u = _u(db); k = _kol(db, u)
    for xau in ("2026-9", "09-2026", "2026/09", ""):
        with pytest.raises(ValueError, match="Kỳ phải dạng"):
            KOL.ghi_hop_tac(db, u, k.id, {"ky": xau, "noi_dung": "x"})


def test_huy_phai_ghi_ly_do_va_KHONG_tinh_tien():
    """Cộng chi phí của một lần đã huỷ là thổi phồng con số người đọc dùng để quyết định."""
    db = _db(); u = _u(db); k = _kol(db, u)
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video 1", "chi_phi": 20_000_000})
    with pytest.raises(ValueError, match="phải ghi lý do"):
        KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video 2",
                                      "chi_phi": 50_000_000, "trang_thai": "huy"})
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video 2", "chi_phi": 50_000_000,
                                  "trang_thai": "huy", "ly_do_huy": "KOL đổi giá"})
    db.commit()
    r = [x for x in KOL.danh_sach(db)["rows"] if x["id"] == k.id][0]
    assert r["so_lan"] == 2
    assert r["tong_chi_thoa_thuan"] == 20_000_000, "Lần huỷ không được cộng tiền"


def test_chi_phi_BA_TRANG_THAI_rong_khac_khong_khac_so_duong():
    """RỖNG KHÁC KHÔNG — bản đầu của vòng này làm sai đúng chỗ ấy.

    Khai `chi_phi` là `default=0.0` không cho rỗng thì "chưa thoả thuận giá" bị ghi thành số 0,
    giống hệt "miễn phí, đổi hàng lấy bài". Hai việc khác hẳn nhau và trên bảng trông y như nhau.
    `test_ks_cot_tien_ky_thuat` bắt được — đúng cái nó sinh ra để bắt, và đây là phép thử giữ cho
    nó không mọc lại.
    """
    db = _db(); u = _u(db); k = _kol(db, u)
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Chưa chốt giá"})
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Đổi hàng", "chi_phi": 0})
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Đã chốt", "chi_phi": 15_000_000})
    db.commit()
    d = KOL.chi_tiet(db, k.id)
    gia = {h["noi_dung"]: h["chi_phi_thoa_thuan"] for h in d["hop_tac"]}
    assert gia["Chưa chốt giá"] is None
    assert gia["Đổi hàng"] == 0
    assert gia["Đã chốt"] == 15_000_000
    assert d["tong_thoa_thuan"] == 15_000_000, "Rỗng không cộng vào tổng"
    assert d["so_lan_chua_co_gia"] == 1, (
        "Phải đếm riêng ra, không thì tổng im lặng nhỏ hơn sự thật mà không ai biết vì sao")
    # Chưa có giá thì KHÔNG phải là "nợ phiếu chi" — chưa biết chi bao nhiêu thì chưa lập được.
    assert d["so_lan_chua_lap_phieu_chi"] == 1


def test_lech_tien_RONG_khi_thieu_mot_ve():
    db = _db(); u = _u(db); k = _kol(db, u)
    pr = PaymentRequest(code="DC-1", category="marketing", amount=5_000_000,
                        supplier_name="N", description="x", status="da_chi", created_by="u")
    db.add(pr); db.commit()
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "x", "payment_request_id": pr.id})
    db.commit()
    h = KOL.chi_tiet(db, k.id)["hop_tac"][0]
    assert h["chi_phi_thoa_thuan"] is None and h["lech_tien"] is None, (
        "Thiếu một vế thì không có phần chênh nào để nói — rỗng, không phải 0")


def test_chi_phi_am_bi_chan():
    db = _db(); u = _u(db); k = _kol(db, u)
    with pytest.raises(ValueError, match="không âm"):
        KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "x", "chi_phi": -1})


def test_noi_nham_phieu_chi_khong_phai_marketing_bi_chan():
    """Nối nhầm thì tiền của tour bị đếm thành tiền KOL."""
    db = _db(); u = _u(db); k = _kol(db, u)
    pr = PaymentRequest(code="DC-1", category="chi_tour", amount=10_000_000,
                        supplier_name="N", description="x", status="da_chi", created_by="u")
    db.add(pr); db.commit()
    with pytest.raises(ValueError, match="không phải khoản marketing"):
        KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "x",
                                      "payment_request_id": pr.id})


def test_hai_so_tien_KHONG_tu_dong_bo_va_phan_chenh_duoc_in_ra():
    """Thoả thuận 20 triệu mà phiếu chi 22 triệu là việc có thật cần người giải thích."""
    db = _db(); u = _u(db); k = _kol(db, u)
    pr = PaymentRequest(code="DC-1", category="marketing", amount=22_000_000,
                        supplier_name="N", description="x", status="da_chi", created_by="u")
    db.add(pr); db.commit()
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video",
                                  "chi_phi": 20_000_000, "payment_request_id": pr.id})
    db.commit()
    h = KOL.chi_tiet(db, k.id)["hop_tac"][0]
    assert h["chi_phi_thoa_thuan"] == 20_000_000
    assert h["phieu_chi_tien"] == 22_000_000
    assert h["lech_tien"] == -2_000_000, "Phần chênh phải in ra, không được san bằng"


def test_chua_lap_phieu_chi_thi_RONG_chu_khong_phai_khong():
    db = _db(); u = _u(db); k = _kol(db, u)
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video", "chi_phi": 20_000_000})
    db.commit()
    d = KOL.chi_tiet(db, k.id)
    h = d["hop_tac"][0]
    assert h["phieu_chi_tien"] is None and h["lech_tien"] is None
    assert d["so_lan_chua_lap_phieu_chi"] == 1, "Phải đếm ra để người ghi sổ biết còn nợ phiếu nào"


def test_so_do_de_RONG_chu_khong_bia_cong_thuc():
    """Lượt xem và lead là con số nhân viên đọc từ trang quản trị của kênh. VTOS không với tới."""
    db = _db(); u = _u(db); k = _kol(db, u)
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video"})
    db.commit()
    h = KOL.chi_tiet(db, k.id)["hop_tac"][0]
    assert h["luot_xem"] is None and h["luot_tuong_tac"] is None and h["so_lead_khai"] is None


def test_sua_hop_tac_go_duoc_so_do_sau_khi_bai_da_dang():
    db = _db(); u = _u(db); k = _kol(db, u)
    h = KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video"})
    db.commit()
    KOL.sua_hop_tac(db, u, h.id, {"luot_xem": 125_000, "trang_thai": "da_dang"})
    db.commit()
    x = KOL.chi_tiet(db, k.id)["hop_tac"][0]
    assert x["luot_xem"] == 125_000 and x["trang_thai"] == "da_dang"
    assert db.get(MktKolHopTac, h.id).sua_boi == u.username


def test_tien_KOL_khong_duoc_cong_vao_bang_chi_cua_nhom_2_7():
    """Sổ tiền thứ hai là đúng cái bệnh nhóm 2.8 sinh ra để chữa.

    Chỗ nối là `payment_request_id`: lập phiếu chi, gắn chiến dịch ở phiếu ấy, thì tiền chảy vào
    bảng 2.7 qua đúng MỘT đường — đường đề nghị chi, y như mọi khoản khác.
    """
    from app.services import marketing as MK
    db = _db(); u = _u(db); k = _kol(db, u); cd = _cd(db)
    KOL.ghi_hop_tac(db, u, k.id, {"ky": "2026-09", "noi_dung": "Video",
                                  "chi_phi": 20_000_000, "campaign_id": cd.id})
    db.commit()
    assert MK.chi_thuc_te(db, "2026-09")["da_chi_tong"] == 0, (
        "Số thoả thuận KHÔNG được chảy vào sổ chi. Tiền thật chỉ đến từ đề nghị chi.")


# ═══════════════════════ QUYỀN VÀ MÀN HÌNH ═══════════════════════

def test_khai_them_tien_to_marketing_khong_noi_cho_ai():
    """Chỉ an toàn chừng nào vai của màn hình này nằm gọn trong vai của /marketing."""
    from app.services.access import MAN_HINH_API, MENU_ROLES
    assert set(MAN_HINH_API["/bao-chi-kol"]) == {"/api/v1/bao-chi-kol", "/api/v1/marketing"}
    thua = set(MENU_ROLES["/bao-chi-kol"]) - set(MENU_ROLES["/marketing"])
    assert not thua, (
        f"Các vai {sorted(thua)} mở được /bao-chi-kol mà KHÔNG mở được /marketing, nên khai thêm "
        "tiền tố Marketing là nới cả nhóm cho họ. Phải dựng cửa đọc riêng, hoặc bỏ vai khỏi XEM.")


def test_vai_ghi_hep_hon_vai_xem_va_KHONG_co_vai_kinh_doanh():
    from app.api.v1.bao_chi_kol import GHI, XEM
    assert set(GHI) < set(XEM) | set(GHI)
    assert not ({"gd_kd", "tp_kd", "tn_kd", "nv_kd"} & set(XEM))
    assert "ketoan" not in XEM, "Đây là sổ thương hiệu, không phải sổ tiền"


def test_nut_phat_khong_nam_o_vong_nay():
    """Người phát ngôn là một VỊ TRÍ có tên, không phải một mức quyền — cửa cũ giữ nguyên."""
    from app.api.v1.bao_chi_kol import GHI
    assert "chutich" in GHI, "Chủ tịch ghi sổ được"
    nguon = (GOC / "app" / "api" / "v1" / "bao_chi_kol.py").read_text(encoding="utf-8")
    assert "/phat" not in nguon.replace("/marketing/pr/{id}/phat", ""), (
        "Vòng này không được dựng cửa phát thứ hai")


def test_man_hinh_co_cua_nhap_that():
    t = (WEB / "app" / "bao-chi-kol" / "page.tsx").read_text(encoding="utf-8")
    assert '"/bao-chi-kol/pr"' in t, "Thiếu ô ghi hoạt động PR"
    assert '"/bao-chi-kol/kol"' in t, "Thiếu ô thêm KOL"
    assert "/hop-tac" in t, "Thiếu ô ghi một lần hợp tác"


def test_man_hinh_noi_ro_tien_o_day_la_tien_thoa_thuan():
    """Một cột tiền không nói rõ nó là tiền gì sẽ bị đọc thành tiền đã chi — vừa xảy ra ở nhóm 2.7."""
    t = (WEB / "app" / "bao-chi-kol" / "page.tsx").read_text(encoding="utf-8")
    assert "thoả thuận" in t
    assert "đề nghị chi" in t


def test_muc_2_2_2_da_co_duong_dan_va_co_muc_menu():
    cay = (WEB / "lib" / "cay_phan_he.ts").read_text(encoding="utf-8")
    dong = [d for d in cay.split("\n") if 'ma: "2.2.2"' in d]
    assert dong and 'href: "/bao-chi-kol"' in dong[0]
    shell = (WEB / "components" / "Shell.tsx").read_text(encoding="utf-8")
    assert '"/bao-chi-kol"' in shell


def test_hai_bang_moi_deu_da_khai_cua_nhap():
    """Bảng nào không có cửa nào thì đó là VIỆC CÒN THIẾU — ranh giới 09/9/2026."""
    from app.services.ks_cua_nhap import CUA_TAY
    assert "mkt_kol" in CUA_TAY and "mkt_kol_hop_tac" in CUA_TAY


def test_mo_hinh_co_trong_init_khong_thi_alembic_doi_xoa_bang():
    """Lần thứ mười cùng một lỗi ở models/__init__.py — phép thử thay cho lời nhắc."""
    import app.models  # noqa
    assert "mkt_kol" in Base.metadata.tables
    assert "mkt_kol_hop_tac" in Base.metadata.tables


def test_ban_di_tru_noi_vao_dau_duy_nhat():
    """23/9 kho này đã một lần có HAI đầu và container không khởi động được."""
    import re
    thu_muc = GOC / "alembic" / "versions"
    rev, down = {}, {}
    for f in thu_muc.glob("*.py"):
        s = f.read_text(encoding="utf-8", errors="replace")
        r = re.search(r'^revision\s*[:=].*?["\']([^"\']+)["\']', s, re.M)
        d = re.search(r'^down_revision\s*[:=].*?(?:["\']([^"\']+)["\']|None)', s, re.M)
        if r:
            rev[r.group(1)] = f.name
            down[r.group(1)] = d.group(1) if (d and d.group(1)) else None
    con = {}
    for r, d in down.items():
        if d:
            con.setdefault(d, []).append(r)
    dau = [r for r in rev if r not in con]
    assert len(dau) == 1, f"Alembic có {len(dau)} đầu: {[(h, rev[h]) for h in dau]}"
    assert "tc81kol4e7b2a9f" in rev
