# -*- coding: utf-8 -*-
"""TX-6 · Ngả của chi phí nguồn ngoài, và hai cửa tính lại — 07/10/2026.

Vòng này sinh ra từ một lần BẤM THỬ trên hệ thật, không từ đọc mã. Ba số đo, đặt cạnh nhau:

    /doi-xe › Đối soát nguồn ngoài : tổng chi phí      1.121.825.494 đ
                                     chưa quy về xe    1.121.825.494 đ   (100%, cả 36 dòng)
    /lai-lo-doi-xe kỳ 08/2026      : LỢI NHUẬN ĐỘI XE       50,3%
                                     chi phí của xe             0 đ
                                     chi phí của đội            0 đ

Ba tầng chi phí của báo cáo lãi lỗ đọc `fleet_trip_costs`, `fleet_maintenance` và
`fleet_period_costs`. Nó KHÔNG đọc `fleet_external_txns`. Nên một tỷ hai nằm ngoài sổ — và không
màn hình nào nói ra là nó nằm ngoài. Người đọc thấy 50,3% và tin đó là kết quả của đội xe. Chỗ hỏng
không phải việc tiền chưa vào sổ; chỗ hỏng là KHÔNG AI BIẾT nó chưa vào.

PHẢN XẠ ĐẦU TIÊN LÀ SAI, và bộ hàng rào này canh đúng chỗ ấy. Phép thử cũ nói "chưa quy được về
xe", nên việc đầu tiên nghĩ ra là tra cho ra xe. Bản khảo sát Vietrip 05/9/2026 ghi bộ trường của
phiếu đề xuất chi: *tour · nhà cung cấp · hình thức thanh toán · loại tiền · dòng dịch vụ*. KHÔNG CÓ
Ô XE, và sẽ không có — phiếu ấy gắn vào TOUR. Hỏi "của xe nào" là hỏi sai câu; hỏi mãi câu sai thì
tháng nào cũng một nắm dòng không ai trả lời được.

Nên vòng này đổi CÂU HỎI: khoản này chạy về NGẢ nào — của xe, của đội, của chủ xe, của tour, hay
không phải chi phí. Và thêm hai cửa tính lại cho hai con số trước nay tính một lần rồi mắc kẹt:
`vehicle_id` của giao dịch, và cờ của chuyến.

Một điều nữa vòng này KHÔNG làm, cố ý: ghi ngả không tự cộng tiền vào báo cáo. Khoản của đội vẫn
phải nạp qua cửa "Chi phí kỳ của đội xe" — cửa ấy ĐÃ CÓ từ trước. Cộng ở hai đường là tính hai lần
đúng một khoản, và đó là kiểu sai không ai nhìn ra vì tổng vẫn trông hợp lý.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.models.fleet import NGA_CHI_PHI, NGA_CUA_DOI_XE, ExternalTxn   # noqa: E402
from app.services import fleet as FL                                    # noqa: E402
from app.services import fleet_lai_lo as LL                             # noqa: E402


GOC_KHO = os.path.dirname(GOC)          # thư mục kho, để đọc được cả phần web/


def _doc(*phan):
    goc = GOC_KHO if phan and phan[0] == "web" else GOC
    with open(os.path.join(goc, *phan), encoding="utf-8") as f:
        return f.read()


# ───────────────────── bảng luật: ngả ─────────────────────
def test_nga_la_danh_sach_dong_khong_phai_chu_tu_do():
    """Ngả phải là danh mục đóng, vì nó quyết định tiền vào sổ của ai.

    Cột `nhom` ngay cạnh là chữ tự do (`/giao-dich/phan-loai` nhận gì cũng ghi), và đó chính là lý do
    không suy được ngả từ nó: ba tháng sau có 'doi', 'đội', 'Đội xe' cùng một cột."""
    assert set(NGA_CHI_PHI) == {"xe", "doi", "chu_xe", "tour", "khong_phai_chi_phi"}, (
        "NGA_CHI_PHI đổi hình. Năm ngả này là năm chỗ tiền đội xe thật sự chạy về, rút ra từ 36 dòng "
        f"đo trên hệ thật 07/10/2026. Hiện có: {sorted(NGA_CHI_PHI)}")
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert "data.nga not in NGA_CHI_PHI" in nguon, (
        "Cửa định tuyến phải kiểm ngả theo danh mục. Nhận chữ tự do là dựng lại đúng chỗ hỏng của "
        "cột `nhom` mà vòng này đi vòng qua.")


def test_chi_hai_nga_la_chi_phi_doi_xe():
    """`chu_xe` KHÔNG được nằm trong hai ngả của đội xe."""
    assert NGA_CUA_DOI_XE == ("xe", "doi"), (
        f"NGA_CUA_DOI_XE phải đúng hai ngả ('xe', 'doi'), đang là {NGA_CUA_DOI_XE}.")
    assert "chu_xe" not in NGA_CUA_DOI_XE, (
        "Khoản của CHỦ XE đi qua khối quyết toán chủ xe. Thêm nó vào đây là cộng cùng một khoản ở hai "
        "nơi – tổng vẫn trông hợp lý nên không ai nhìn ra.")
    assert "tour" not in NGA_CUA_DOI_XE, (
        "Khoản của TOUR không phải chi phí đội xe. Phiếu đề xuất chi Vietrip gắn vào tour; gộp nó vào "
        "đội xe là lý do con số 'chưa quy được về xe' từng bằng 100% tổng chi phí.")


def test_mac_dinh_la_chua_dinh_tuyen_khong_phai_mot_nga_cho_du_form():
    """Cột `nga` mặc định RỖNG. Rỗng là một trạng thái tử tế: đếm được, nói ra được, sửa được."""
    assert ExternalTxn.nga.default.arg == "", (
        "Mặc định của `nga` phải là chuỗi rỗng = chưa định tuyến. Đặt sẵn 'doi' cho đủ form là đẩy "
        "một tỷ hai vào chi phí đội xe mà chưa ai đọc chứng từ – sai theo chiều ngược lại, và khó "
        "phát hiện hơn vì lúc ấy báo cáo trông đã đầy đủ.")


def test_dinh_tuyen_bat_buoc_ly_do_va_ghi_ten_nguoi():
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert "Phải ghi lý do chọn ngả này" in nguon, (
        "Cửa định tuyến phải bắt buộc lý do. Đây là phán xét của người đọc chứng từ, không phải phép "
        "tính; ba tháng sau có người hỏi 'vì sao khoản này của đội' thì phải có câu trả lời tại chỗ.")
    assert "t.nga_boi = u.username" in nguon and "t.nga_luc = datetime.now()" in nguon, (
        "Phải ghi ai định tuyến và lúc nào. Ngả quyết định tiền vào sổ của ai, nên nó phải có dấu vết.")


def test_nga_xe_phai_quy_ve_mot_chiec():
    nguon = _doc("app", "api", "v1", "fleet.py")
    assert "mà không nói xe nào" in nguon, (
        "Ngả 'của một chiếc xe cụ thể' phải kèm biển số và tra ra được xe. Nói 'của xe' mà không nói "
        "xe nào thì chưa trả lời câu hỏi, chỉ đổi một ô trống thành một ô trống khác.")


def test_ghi_nga_khong_tu_cong_tien_vao_bao_cao():
    """Cửa định tuyến chỉ ghi ngả. Khoản của đội vẫn phải đi qua cửa chi phí kỳ đã có."""
    nguon = _doc("app", "api", "v1", "fleet.py")
    i = nguon.index("def dinh_tuyen_giao_dich")
    than = nguon[i:nguon.index("def tra_lai_xe_giao_dich")]
    assert "FleetPeriodCost" not in than, (
        "Cửa định tuyến KHÔNG được tự tạo dòng chi phí kỳ. Một khoản phải vào sổ qua đúng một cửa; "
        "cộng ở hai đường là tính hai lần đúng một khoản.")
    assert "Chi phí kỳ của đội xe" in than, (
        "Giữ câu dặn trong mã: khoản của đội muốn vào ba tầng thì nạp qua cửa chi phí kỳ.")


# ───────────────────── nói ra phần nằm ngoài sổ ─────────────────────
def test_bao_cao_lai_lo_noi_ra_phan_nam_ngoai_ba_tang():
    """Báo cáo phải in ra số nằm ngoài ba tầng, không để người đọc tự biết."""
    nguon = _doc("app", "services", "fleet_lai_lo.py")
    assert "def ngoai_so(" in nguon, (
        "fleet_lai_lo phải có phép đếm phần nằm NGOÀI ba tầng. Ba tầng không đọc bảng giao dịch nguồn "
        "ngoài, nên nếu không đếm thì 1,12 tỷ biến mất khỏi báo cáo mà không ai biết.")
    assert '"ngoai_so": ngoai_so(db, d1, d2)' in nguon, (
        "Phải gắn kết quả vào báo cáo. Tính mà không trả ra thì vẫn là người đọc không biết.")
    assert '"chua_dinh_tuyen"' in nguon and '"cua_doi_xe"' in nguon, (
        "Phải TÁCH phần đã biết là của đội xe (số phải trừ thêm) khỏi phần chưa định tuyến (chưa biết "
        "của ai). Gộp một con số thì mỗi tháng báo động một tỷ hai mà không ai làm được gì.")


def test_dem_ngoai_so_loai_dung_ba_thu_khong_duoc_tinh():
    """Bản lặp, khoản điều chuyển, và dòng đã khớp chuyến đều KHÔNG được đếm là nằm ngoài sổ."""
    nguon = _doc("app", "services", "fleet_lai_lo.py")
    i = nguon.index("def ngoai_so(")
    than = nguon[i:nguon.index("def bao_cao(")]
    assert "ExternalTxn.trung == False" in than, "Bản ghi lặp không được cộng vào số nằm ngoài sổ."
    assert "ExternalTxn.khong_phai_chi_phi == False" in than, (
        "Khoản điều chuyển tiền nội bộ không phải chi phí – đếm nó là báo động một số không tồn tại.")
    assert 'ExternalTxn.khop != "da_khop"' in than, (
        "Dòng ĐÃ KHỚP chuyến đã thành chi phí chuyến, tức đã nằm TRONG tầng 1. Đếm lại là báo động "
        "trùng, và lần sau không ai tin con số ấy nữa.")


def test_man_hinh_lai_lo_in_ra_khoi_ngoai_so():
    nguon = _doc("web", "app", "lai-lo-doi-xe", "page.tsx")
    assert "d.ngoai_so" in nguon and "nằm NGOÀI ba tầng chi phí" in nguon, (
        "Màn hình Lãi lỗ đội xe phải in khối 'nằm ngoài ba tầng'. Máy chủ tính mà màn hình không in "
        "thì người đọc vẫn chỉ thấy 50,3%.")


def test_man_hinh_khong_go_lai_danh_sach_nga():
    """Màn hình dựng ô chọn và cờ 'của đội xe' từ máy chủ, không gõ lại danh sách trong TypeScript."""
    nguon = _doc("web", "app", "doi-xe", "page.tsx")
    assert "gd?.nga_chi_phi" in nguon, (
        "Ô chọn ngả phải dựng từ danh mục máy chủ trả về. Gõ lại danh sách ở màn hình là ngày nào đó "
        "hai bên lệch nhau mà không ai biết bên nào đúng.")
    assert 'n.cua_doi_xe' in nguon, (
        "Cờ 'của đội xe' phải lấy từ máy chủ, không tự suy ở màn hình.")


# ───────────────────── hai cửa tính lại ─────────────────────
def test_co_cua_tra_lai_xe_va_no_khong_doan():
    assert hasattr(FL, "tra_lai_xe"), (
        "Phải có cửa tra lại xe. `vehicle_id` được tra đúng MỘT LẦN lúc nạp; cửa phân loại cố ý không "
        "sửa nó, và nạp lại tệp thì khoá chống trùng đánh dấu bản thứ hai là 'trùng' chứ không cập "
        "nhật bản cũ. Không có cửa này thì 7 khoản có biển số đúng nằm mãi ở nhóm 'chưa tra được xe'.")
    nguon = _doc("app", "services", "fleet.py")
    i = nguon.index("def tra_lai_xe(")
    than = nguon[i:nguon.index("def tinh_lai_co_chuyen(")]
    assert "xe_theo_bien" in than, "Phải chạy lại đúng phép tra cũ, theo lịch sử biển số."
    assert "da_gan" in than, "Cửa phải báo đổi bao nhiêu dòng – cửa im lặng thì lần sau không ai biết nó có chạy."
    assert "if v is None" in than, "Không tra ra xe thì BỎ QUA, không đoán."


def test_co_cua_tinh_lai_co_chuyen_va_no_khong_doi_so():
    assert hasattr(FL, "tinh_lai_co_chuyen"), (
        "Phải có cửa tính lại cờ chuyến. Cờ được tính lúc GHI rồi lưu vào dòng, nên mỗi lần luật kiểm "
        "đổi là các dòng cũ mang cờ của luật cũ. Đo trên hệ thật 07/10/2026: cả 24 chuyến in 'chưa có "
        "số GPS' ở cột km mà cột Cờ vẫn XANH.")
    nguon = _doc("app", "services", "fleet.py")
    i = nguon.index("def tinh_lai_co_chuyen(")
    than = nguon[i:nguon.index("def nhap_giao_dich(")]
    for cam in ("t.status", "t.km_dau", "t.km_cuoi", "t.doanh_thu"):
        assert f"{cam} =" not in than, (
            f"Cửa tính lại cờ không được đổi `{cam}`. Nó chỉ tính lại cờ và lý do cờ: đổi một con số "
            "đã chốt ở đây là sửa số liệu mà không ai yêu cầu.")
    assert "da_tinh_lai" in than, "Cửa phải báo tính lại bao nhiêu chuyến."


def test_hai_cua_tinh_lai_co_duong_vao_tu_man_hinh():
    """Cửa máy chủ mà không màn hình nào gọi tới thì vẫn là việc còn thiếu."""
    nguon = _doc("web", "app", "doi-xe", "page.tsx")
    assert "/fleet/giao-dich/tra-lai-xe" in nguon, "Thiếu nút gọi cửa tra lại xe trên màn hình."
    assert "/fleet/chuyen/tinh-lai-co" in nguon, "Thiếu nút gọi cửa tính lại cờ trên màn hình."
    assert "/fleet/giao-dich/dinh-tuyen" in nguon, "Thiếu ô định tuyến trên màn hình."


# ───────────────────── mục lục không được nói sai ─────────────────────
def test_muc_luc_khong_khai_tab_la_chua_dung():
    """Bảy mục 4.4.x và 4.9.7 là TAB có thật, không phải việc còn nợ.

    Trang mục lục đếm mục không có `href` là "Chưa dựng". Trước 07/10/2026 nó nói Điều hành tour
    "11/20 màn hình" trong khi sự thật là 11 màn hình + 7 tab + 2 mục thiếu. Đây là trang Chủ tịch
    mở ra để biết hệ thống còn nợ gì, nên nói sai ở đây là làm lệch mọi quyết định đọc từ nó – và
    lệch theo chiều làm người ta dựng lại cái đã có."""
    nguon = _doc("web", "lib", "cay_phan_he.ts")
    # 4.4.7 vào danh sách này từ 09/10/2026 — PR DH-1 dựng tab thật, xem phép thử ngay dưới.
    for ma, dau in (("4.4.1", "Thông tin & quy trình"), ("4.4.3", "Booking & thu tiền"),
                    ("4.4.4", "Chi NCC & quyết toán"), ("4.4.5", "HDV & xe"),
                    ("4.4.6", "Dự toán 3 con số"), ("4.4.7", "Phát sinh & sự cố"),
                    ("4.4.8", "Quyết toán chi tiết"),
                    ("4.4.9", "Quy trình & lịch sử"), ("4.9.7", "Chủ xe & quyết toán")):
        i = nguon.index(f'ma: "{ma}"')
        dong = nguon[i:i + 260]
        assert "tab: true" in dong, (f"Mục {ma} phải khai `tab: true` – nó là tab có thật, "
                                     "không phải mục chưa dựng.")
        assert dau in dong, (f"Mục {ma} phải nói rõ nó nằm ở tab nào ('{dau}'), không thì người đọc "
                             "biết là 'có' mà không biết tìm ở đâu.")


def test_hai_muc_tung_thieu_nay_khai_co_thi_phai_co_that():
    """Hai mục này ĐÃ TRẢ XONG ngày 08/10/2026, nên bản cũ của phép thử nói sai — và phải đổi.

    SỬA NGÀY 09/10/2026, cùng một ca với mục 5.4 hôm qua. Bản cũ tên là
    `test_hai_muc_thieu_that_van_phai_khai_la_thieu` và đòi 4.4.7 cùng 4.9.1 KHÔNG được khai là có.
    Lý do ghi thẳng trong lời báo: "trang chi tiết chuyến không có một chữ 'sự cố' nào". Lý do ấy
    hết hiệu lực từ PR DH-1 (7d128bc) cùng ngày: tab «Phát sinh & sự cố» dựng thật trên
    `web/app/tours/[id]/page.tsx`, gọi thẳng `GET /su-co-tour?tour_id=` chứ không dựng cửa đọc thứ
    hai, và năm phép thử của `test_dh1_phat_sinh_cua_chuyen.py` canh nó. Mục 4.9.1 thì Chủ tịch
    chọn 08/10 là TRỎ VỀ /doi-xe thay vì dựng trang thứ hai đọc cùng nguồn số.

    Giữ nguyên bản cũ là ép mục lục khai thiếu một thứ đã có — bắt cây nói sai, đúng cái phép thử
    này sinh ra để chặn, chỉ là sai theo chiều ngược lại.

    HÀNG RÀO KHÔNG YẾU ĐI, CHỈ ĐỔI CHỖ CẮN. Thứ đáng sợ vẫn là KHAI KHỐNG cho con số mục lục đẹp
    hơn. Nên thay vì đòi hai mục khai là thiếu, nay đòi: khai có thì màn hình phải CÓ THẬT. Khai
    khống bây giờ đỏ ngay, mà trả xong thật thì không phải sửa lại phép thử lần nữa.
    """
    nguon = _doc("web", "lib", "cay_phan_he.ts")
    def _dong(ma: str) -> str:
        """Chỉ lấy ĐÚNG dòng khai mục ấy. Cắt theo số ký tự thì cửa sổ tràn sang mục kế tiếp, và
        phép thử đọc `tab: true` của mục sau rồi báo sai – đúng một lần đã xảy ra khi viết tệp này."""
        i = nguon.index(f'ma: "{ma}"')
        return nguon[i:nguon.index("\n", i)]

    # 4.4.7 — khai là tab thì trang chi tiết chuyến phải thật sự đọc sổ sự cố của ĐÚNG chuyến ấy.
    if "tab: true" in _dong("4.4.7"):
        chuyen = _doc("web", "app", "tours", "[id]", "page.tsx")
        assert "/su-co-tour?tour_id=" in chuyen, (
            "4.4.7 khai `tab: true` mà trang chi tiết chuyến không gọi `GET /su-co-tour?tour_id=`. "
            "Khai một tab chưa dựng để con số mục lục đẹp hơn là đúng chuyện phép thử này chặn.")
        assert "sự cố" in chuyen, (
            "4.4.7 khai là tab mà trang chi tiết chuyến không có một chữ 'sự cố' nào cho người đọc.")
    else:
        assert "href" not in _dong("4.4.7"), (
            "4.4.7 không khai tab thì cũng không được khai `href` — nó là một TAB của trang chi "
            "tiết chuyến, không phải một màn hình riêng.")

    # 4.9.1 — Chủ tịch chọn 08/10: trỏ về /doi-xe, KHÔNG dựng trang thứ hai đọc cùng nguồn số.
    d91 = _dong("4.9.1")
    assert 'href: "/doi-xe"' in d91, (
        "4.9.1 Tổng quan đội xe trỏ về /doi-xe theo quyết định của Chủ tịch 08/10/2026. Một trang "
        f"tổng quan riêng là màn hình THỨ HAI đọc cùng nguồn số. Đang khai: {d91.strip()}")
    import os
    assert os.path.exists(os.path.join(GOC_KHO, "web", "app", "doi-xe", "page.tsx")), (
        "4.9.1 trỏ vào /doi-xe mà màn hình ấy không có trên đĩa.")


def test_ba_man_hinh_da_chay_phai_co_duong_vao_tu_cay():
    """Báo hỏng, đơn nghỉ, hợp đồng thuê xe: chạy thật từ 06–07/10 mà cây không có lối vào."""
    nguon = _doc("web", "lib", "cay_phan_he.ts")
    assert "Báo hư hỏng xe" in nguon and "tab=bao-hong" in nguon, (
        "Cửa báo hư hỏng xe chạy thật từ PR #200 mà không có mục nào trong cây – không ai tìm ra nó "
        "từ mục lục.")
    assert "Hợp đồng thuê xe riêng" in nguon, (
        "Hợp đồng thuê xe riêng chạy thật từ PR #211 mà cây không có lối vào.")
    # SỬA NGÀY 08/10/2026 – phép thử này nói một điều KHÔNG CÒN ĐÚNG, nên nó phải đổi, không
    # phải cây phân hệ. Bản cũ đòi tên mục 5.4 mang chữ "tài xế & HDV", với lý do ghi thẳng trong
    # lời báo: "chín phòng còn lại chưa có màn hình". Lý do ấy hết hiệu lực từ PR #244 (NS-2):
    # màn hình /cham-cong "Đơn nghỉ phép của tôi" nay mở cho cả 22 vai, và thẻ chấm công trên /hr
    # thì GHI được chứ không chỉ đọc. Giữ nguyên bản cũ là ép mục lục dán một cái nhãn thu hẹp lên
    # một màn hình đã mở rộng – tức là bắt cây nói sai, đúng cái phép thử này sinh ra để chặn.
    # Thứ cần canh vẫn còn nguyên và nay canh ĐÚNG CHỖ: cả hai mục phải có lối vào, và 5.4b phải
    # trỏ vào /cham-cong – mất nó thì chín phòng không có thẻ HCNS lại không tìm ra đường gửi đơn.
    i = nguon.index('ma: "5.4"')
    dong = nguon[i:i + 200]
    assert "href" in dong, (
        "5.4 Chấm công & nghỉ phép phải có lối vào từ cây: thẻ chấm công trên /hr ghi được từ "
        "PR #244, một mục chạy thật mà khai 'Chưa dựng' thì không ai tìm ra nó từ mục lục.")
    j = nguon.index('ma: "5.4b"')
    dong_b = nguon[j:j + 200]
    assert "href" in dong_b and "/cham-cong" in dong_b, (
        "5.4b Đơn nghỉ phép của tôi phải trỏ vào /cham-cong. Thẻ chấm công của HCNS chỉ mở cho "
        "sáu vai, còn gửi đơn nghỉ là việc của cả 22 vai – mất mục này thì chín phòng không có "
        "đường vào, đúng chỗ hở mà NS-2 vừa bịt ở PR #244.")
