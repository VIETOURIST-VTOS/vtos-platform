# -*- coding: utf-8 -*-
"""CỬA TẢI cho KHO QUYẾT TOÁN CŨ – 604 tệp tháng 1–6/2026.

VÌ SAO CÓ TỆP NÀY: BỘ MÁY ĐÃ CÓ ĐỦ, CHỈ THIẾU CÁI CỬA

Rà ngày 11/9/2026 thấy ba thứ đã viết xong và đều có phép thử:

    app/services/nap_kho_cu.py            bộ đọc – một bộ cho cả 108 bố cục sheet khác nhau
    app/services/chong_trung_quyet_toan.py bộ chống trùng – vân tay tệp, vân tay chuyến, đối chiếu
    scripts/nap_kho_cu.py                 phần ghi – xoá-rồi-ghi theo nguồn, mặc định XEM TRƯỚC

Nhưng cả ba **chỉ chạy được bằng dòng lệnh**, và đầu vào là một tệp `du_lieu_nap.json` mà ai đó phải
tạo ra trước. Nhân viên Điều hành không dùng được. Theo ranh giới Chủ tịch chốt 09/9/2026 – *"mỗi
con số cần một cửa nhập hoặc cửa tải cho người dùng; không có cửa thì đó là việc còn thiếu"* – chỗ
ấy là THIẾU CỬA, không phải thiếu mã.

Tệp này là cái cửa. Nó KHÔNG viết lại phép đọc hay phép chống trùng – nó gọi đúng hai tệp trên.

BA CỬA, VÀ CHÚNG LÀ BA BƯỚC RIÊNG – KHÔNG PHẢI MỘT NÚT

    1. TẢI    POST /api/v1/intake/kiem-tra-tep   nhân viên kéo thả tệp, máy đọc, KHÔNG ghi gì
    2. SOÁT   kết quả của bước 1                  bảng cho người duyệt nhìn trước khi quyết
    3. GHI    POST /api/v1/intake/nap             người có quyền bấm; nhật ký ghi AI bấm, LÚC NÀO

Hai bước đầu không chạm vào cơ sở dữ liệu. Bước ba ghi một dòng `IntakeRun` mang tên người bấm, số
tệp, và vân tay nội dung – nên "ai chịu trách nhiệm về 604 tệp này" là một câu tra được, không phải
một câu phải nhớ.

CHỖ NGUY HIỂM NHẤT, VÀ CÁCH TỆP NÀY TRÁNH

`chong_trung_quyet_toan` đo trên 594 tệp khớp được tên: **bộ đọc rút ra 90,7% doanh thu và 71,1%
giá vốn** so với bản đối chiếu H1 mà Kế toán đã chốt. Phần lệch nằm gần hết ở tour châu Âu – sheet
land ghi bằng EUR/GBP. Cho nên tài liệu của chính bộ chống trùng viết thẳng: *"TIỀN thì lấy theo bản
đã chốt, còn bộ đọc làm phép kiểm."*

Nên cửa này **KHÔNG ghi doanh thu và giá vốn mức chuyến** từ số bộ đọc rút ra. Nó chỉ ghi phần mà
kho cũ thật sự bổ sung: dòng khách, dòng chi phí, dòng HDV. Ô `actual_revenue` / `actual_cost` của
chuyến để nguyên. Ghi vào đó bằng một con số kém 29% là làm hỏng đúng thứ người ta định sửa.

PHIẾU ĐẶT THEO NGƯỜI BÁN – THÊM 13/9/2026

Chủ tịch hỏi: "đẩy lên quyết toán thì số có chạy về các phòng ban không, doanh thu cho sales đoàn và
sales lẻ?" Câu trả lời lúc ấy là KHÔNG, và lý do nằm gọn ở một chỗ: cửa tạo chuyến sinh chuyến mà
không sinh phiếu đặt, `booking_khach.booking_id` lại là cột bắt buộc – nên cửa này lặng lẽ bỏ TOÀN BỘ
dòng khách của mọi chuyến mới. Chỉ chi phí vào được, và hậu quả dây chuyền là bảng lãi lỗ thấy giá vốn
mà không thấy doanh thu: mỗi chuyến thành một khoản lỗ bằng đúng chi phí.

Nay `phieu_dat_kho_cu` dựng phiếu từ chính cột SALES của tệp, **mỗi người bán một phiếu**, và dòng
khách treo vào đúng phiếu của người đã bán ra khách ấy. Tên chưa khớp được tài khoản thì vào phiếu
đứng tên tài khoản điều hành khoá với `counts_for_target=False` – doanh thu công ty đúng ngay, mà
không nhân viên thật nào bị cộng nhầm chỉ tiêu.

VÀ VÌ THIẾU BẢN ĐỐI CHIẾU H1, MỌI TỆP ĐỀU LÀ "CẦN NGƯỜI XÁC NHẬN"

Bản đối chiếu H1 (`VTOS_Kho_quyet_toan_T1-T6-2026.xlsx`) chưa có cửa tải riêng, nên ở đây `ref` luôn
rỗng. `doi_chieu_ban_tong_hop` gặp `ref=None` thì trả về một cảnh báo mức HỎI cho MỌI tệp: *"không
có số thứ hai để soát – phải có người xác nhận trước khi nạp."*

Đó không phải chỗ hỏng, đó là hàng rào đang làm đúng việc: **mặc định thì không tệp nào được ghi**,
người duyệt phải bấm rõ "nạp cả tệp có cảnh báo" thì mới ghi, và lần bấm ấy vào nhật ký mang tên họ.
Dựng cửa tải cho bản đối chiếu H1 là việc tiếp theo, và nó sẽ biến cảnh báo này thành phép so số.
"""
from __future__ import annotations

from datetime import datetime

from app.services import chong_trung_quyet_toan as CT
from app.services import khop_nguoi_ban as KN
from app.services import phieu_dat_kho_cu as PD
from app.services import nap_kho_cu as KHO

# Mọi dòng do cửa này ghi mang nguồn riêng. Nạp lại thì XOÁ đúng phần mang nguồn ấy rồi ghi lại –
# nạp bao nhiêu lần cũng ra một kết quả, và KHÔNG đụng tới dòng do Vietrip hay do người nhập tay tạo.
NGUON = "kho_cu_h1_2026"

# Bộ nạp chạm thẳng vào tiền -> cửa tải hẹp hơn cửa nhập tay đúng một bậc (quy tắc P4).
CHAM_TIEN = ("kho_quyet_toan_cu",)

PHONG_BAN = {"kho_quyet_toan_cu": "dieu_hanh"}


# =============================================================================================
# Đọc
# =============================================================================================

def doc_tep_lo(noi_dung: bytes, ten_tep: str = "") -> list[dict]:
    """Một tệp = MỘT chuyến = một dòng. Khung nạp theo lô đòi danh sách, nên trả danh sách một phần tử.

    Bộ đọc `nap_kho_cu.doc_tep` tự nó KHÔNG ghi gì và KHÔNG đoán gì: không tìm thấy 'Mã tour:' thì
    trả rỗng chứ không suy từ tên tệp, và mọi tổng cộng lại từ dòng chứ không đọc ô tổng.
    """
    return [KHO.doc_tep(noi_dung, ten_tep)]


# =============================================================================================
# Soát – KHÔNG ghi gì
# =============================================================================================

def _tim_chuyen(db, ma_tour: str):
    """Tìm chuyến theo mã, KHÔNG phân biệt hoa thường. Không có mã thì không tìm – không đoán."""
    if not (ma_tour or "").strip():
        return None
    from sqlalchemy import func, select

    from app.models.core import Tour
    return db.scalars(
        select(Tour).where(func.upper(Tour.code) == ma_tour.strip().upper())).first()


def _soat_mot(db, d: dict) -> dict:
    """Soát một tệp: tìm chuyến, chạy bộ chống trùng, xếp vào một trong bốn rổ.

    Bốn rổ, và chúng phải TÁCH NHAU vì bốn cách xử khác nhau:
      · khong_thay_chuyen – mã tour không có trong VTOS. Không phải lỗi tệp; là chuyến chưa nhập.
      · chan              – có va chạm mức NẶNG. Không nạp, kể cả khi người duyệt bỏ qua cảnh báo.
      · can_xac_nhan      – có cảnh báo mức HỎI. Chỉ nạp khi người duyệt bấm rõ.
      · nap_duoc          – sạch.
    """
    t = _tim_chuyen(db, d.get("ma_tour") or "")
    kq = CT.kiem_mot(d, None, db=db, tour_id=(t.id if t else None))
    ro = ("khong_thay_chuyen" if t is None
          else "chan" if kq["nang"]
          else "can_xac_nhan" if kq["hoi"]
          else "nap_duoc")
    return {
        "ten_tep": d.get("ten_tep"), "ma_tour": d.get("ma_tour"),
        "tour_id": (t.id if t else None),
        "ro": ro,
        "so_dong_khach": len(d.get("khach") or []),
        "so_dong_chi": len(d.get("chi") or []),
        "so_dong_hdv": len((d.get("hdv") or {}).get("dong") or []),
        # Hai con số này để NGƯỜI ĐỌC đối chiếu, KHÔNG để ghi vào chuyến – xem phần đầu tệp.
        "tong_thu_bo_doc": d.get("tong_thu"),
        "tong_chi_bo_doc": d.get("tong_chi"),
        "chan": [x["noi"] for x in kq["nang"]],
        "can_xac_nhan": [x["noi"] for x in kq["hoi"]],
        "doc_thieu": list(d.get("thieu") or []),
    }


def kiem_lo(db, rows: list[dict]) -> dict:
    """CỬA SOÁT. Trả về đúng thứ người duyệt cần nhìn trước khi quyết. KHÔNG ghi một dòng nào."""
    chi_tiet = [_soat_mot(db, d) for d in rows]
    dem = {r: sum(1 for x in chi_tiet if x["ro"] == r)
           for r in ("nap_duoc", "can_xac_nhan", "chan", "khong_thay_chuyen")}
    return {
        "so_dong": len(chi_tiet),
        # Khung nạp đọc ba khoá này. Ánh xạ sang ngôn ngữ của khung:
        #   da_nap   – sẽ nạp được nếu bấm nạp ngay bây giờ (chỉ rổ sạch)
        #   da_co    – bỏ qua vì đã có dữ liệu / cần xác nhận
        #   dong_loi – chặn hẳn, gồm cả tệp không tìm thấy chuyến
        "da_nap": dem["nap_duoc"],
        "da_co": dem["can_xac_nhan"],
        "dong_loi": dem["chan"] + dem["khong_thay_chuyen"],
        "dem": dem,
        "chi_tiet": chi_tiet,
        "ghi_chu": (
            f"XEM TRƯỚC – chưa ghi gì. {dem['nap_duoc']} tệp sạch · "
            f"{dem['can_xac_nhan']} tệp cần người xác nhận · {dem['chan']} tệp bị chặn · "
            f"{dem['khong_thay_chuyen']} tệp không tìm thấy chuyến trong VTOS. "
            "Doanh thu và giá vốn MỨC CHUYẾN sẽ KHÔNG bị ghi đè – bộ đọc chỉ rút được 90,7% doanh "
            "thu và 71,1% giá vốn so với bản đối chiếu H1, nên tiền mức chuyến phải lấy theo bản đã "
            "chốt, không lấy theo tệp."),
    }


# =============================================================================================
# Ghi
# =============================================================================================

def _xoa_phan_cua_nguon(db, tour_id: int) -> None:
    """XOÁ ĐÚNG PHẦN CỦA NGUỒN NÀY, không đụng nguồn khác.

    Mỗi bảng ghi nguồn ở MỘT CỘT KHÁC NHAU, nên phải khai từng bảng một. Viết một vòng lặp chung
    rồi đoán tên cột là cách chắc chắn để hoặc nổ, hoặc tệ hơn: xoá nhầm dòng của nguồn khác vì
    điều kiện lọc không áp được.
    """
    from app.models.lop3_tour import BookingKhach, TourHdvChi
    from app.models.vietrip import TourCostLine

    db.query(TourCostLine).filter(
        TourCostLine.tour_id == tour_id,
        TourCostLine.source == NGUON).delete(synchronize_session=False)
    db.query(BookingKhach).filter(
        BookingKhach.tour_id == tour_id,
        BookingKhach.nguoi_sua == NGUON).delete(synchronize_session=False)
    db.query(TourHdvChi).filter(
        TourHdvChi.tour_id == tour_id,
        TourHdvChi.nguoi_nhap == NGUON).delete(synchronize_session=False)
    # Phiếu đặt do lô này dựng (một phiếu một người bán) – bảng thứ tư, thêm 13/9/2026. Phải xoá ở
    # ĐÂY chứ không chỉ trong `phieu_dat_kho_cu.sinh`: nạp lại một tệp nay không còn dòng khách nào
    # thì `sinh` không được gọi, và phiếu cũ ở lại với doanh thu của lần nạp trước.
    PD.xoa_phieu_cua_lo(db, tour_id)
    db.flush()


def _ghi_mot(db, d: dict, tour_id: int, boi: str) -> dict:
    """Ghi một tệp. Trả về những thứ KHÔNG ghi được – để chúng vào báo cáo chứ không biến mất."""
    from app.models.lop3_tour import BookingKhach, TourHdvChi
    from app.models.vietrip import TourCostLine

    _xoa_phan_cua_nguon(db, tour_id)
    bao = {"mat_dong_khach": 0}

    khach = d.get("khach") or []
    # PHIẾU ĐẶT THEO NGƯỜI BÁN. Trước 13/9/2026 chỗ này chỉ đi tìm một phiếu có sẵn, và chuyến do
    # cửa tạo chuyến sinh ra thì KHÔNG có phiếu nào – nên toàn bộ dòng khách rơi, chỉ chi phí vào
    # được. Hệ quả: bảng lãi lỗ thấy giá vốn mà không thấy doanh thu, mỗi chuyến thành một khoản lỗ
    # bằng đúng chi phí; và mọi báo cáo doanh số đọc `bookings.sales_id` nên không có gì để đọc.
    # Nay dựng phiếu từ chính cột SALES của tệp: mỗi người bán một phiếu.
    theo_ten: dict[str, int] = {}
    if khach:
        kq_p = PD.sinh(db, tour_id, khach, boi)
        if kq_p.get("loi"):
            bao["mat_dong_khach"] = len(khach)
            bao["vi_sao_mat"] = kq_p["loi"]
        else:
            theo_ten = kq_p["theo_ten_nguoi_ban"]
            bao["so_phieu_dat"] = kq_p["so_phieu"]
            bao["chua_gan_nguoi_ban"] = kq_p["chua_gan_dong"]

    if theo_ten:
        for i, x in enumerate(khach, start=1):
            bid = theo_ten.get((x.get("sale") or "").strip())
            if bid is None:      # không thể xảy ra – phiếu dựng từ chính tập tên này
                bao["mat_dong_khach"] += 1
                continue
            db.add(BookingKhach(tour_id=tour_id, booking_id=bid, stt=i,
                                ho_ten=(x.get("ho_ten") or "")[:200],
                                gia_ban=x.get("gia_ban"),
                                ma_dat_cho=(x.get("ma_dat_cho") or "")[:30] or None,
                                nguoi_sua=NGUON, sua_luc=datetime.now()))

    for i, x in enumerate(d.get("chi") or [], start=1):
        db.add(TourCostLine(tour_id=tour_id, line_no=i,
                            description=(x.get("noi_dung") or "(không ghi)")[:200],
                            nhom=(x.get("nhom") or "")[:80] or None,
                            ngay=(x.get("ngay") or "")[:60] or None,
                            supplier_name=(x.get("doi_tac") or "")[:200],
                            supplier_tax_code=(x.get("mst") or "")[:20],
                            unit_price=x.get("don_gia"), qty=x.get("so_luong") or 0,
                            coef=x.get("he_so") or 1, actual=x.get("thanh_tien"),
                            hinh_thuc_tt=(x.get("hinh_thuc_tt") or "")[:20] or None,
                            note=(x.get("ghi_chu") or "")[:200],
                            source=NGUON, status="hd", updated_by=boi[:50] or NGUON))

    hdv = d.get("hdv") or {}
    for x in hdv.get("dong") or []:
        db.add(TourHdvChi(tour_id=tour_id, noi_dung=(x.get("noi_dung") or "")[:200] or None,
                          don_gia=x.get("don_gia"), so_luong=x.get("so_luong"),
                          thanh_tien=x.get("thanh_tien"), tien_ung=hdv.get("tien_ung"),
                          trang_thai_duyet="da_duyet",
                          nguoi_nhap=NGUON, nhap_luc=datetime.now()))
    return bao


def nap_lo(db, rows: list[dict], boi: str, ten_tep: str = "",
           bo_qua_dong_loi: bool = False) -> dict:
    """CỬA GHI. Mặc định chỉ ghi tệp SẠCH.

    `bo_qua_dong_loi` ở đây mang nghĩa "nạp CẢ tệp có cảnh báo" – đúng bằng cờ `--ke-ca-canh-bao`
    của kịch bản dòng lệnh. Vì bản đối chiếu H1 chưa có cửa tải nên MỌI tệp đều mang một cảnh báo
    ("không có số thứ hai để soát"), tức là **mặc định không tệp nào được ghi** cho tới khi người
    duyệt bấm rõ. Đó là hàng rào, không phải chỗ hỏng.

    Tệp bị CHẶN (va chạm mức NẶNG) thì không ghi kể cả khi bấm bỏ qua cảnh báo. Hôm nay chỉ có ĐÚNG
    MỘT thứ ở mức nặng: **không có chuyến mang mã ấy trong VTOS**. Quyết toán phải gắn vào một chuyến
    đã có – tạo chuyến trước rồi nạp lại. Không có chỗ nào cho phép bỏ qua điều đó.

    Chuyến ĐÃ CÓ giá vốn từ nguồn khác thì ở mức HỎI, không phải mức nặng – và đó là chủ ý của bộ
    chống trùng: nạp thêm vào là chuyến có HAI lần giá vốn, lợi nhuận âm, mà mọi bảng vẫn cân vì tổng
    nào cũng cộng từ dòng nên không ai nhìn ra. Máy KHÔNG tự chọn giữa "giữ nguồn đang có" và "xoá
    nguồn đang có rồi nạp"; nó đưa câu ấy cho người bấm, và người bấm tự chịu trách nhiệm.
    """
    soat = kiem_lo(db, rows)
    theo_ten = {x["ten_tep"]: x for x in soat["chi_tiet"]}
    da_nap, bo_qua, mat_khach = [], [], []

    # Ghi SỔ GÁN NGƯỜI BÁN trước khi ghi bất cứ dòng nào. Phải trước, vì `phieu_dat_kho_cu` tra sổ
    # ấy để biết một cái tên trong tệp thuộc tài khoản nào – và vì lựa chọn tay của người đã gán từ
    # lần trước phải có mặt ở đây thì mới thắng được bộ khớp máy.
    so_gan = KN.ghi_so(db, PD.dem_nguoi_ban(rows))

    for d in rows:
        s = theo_ten.get(d.get("ten_tep")) or {}
        ro = s.get("ro")
        if ro == "nap_duoc" or (ro == "can_xac_nhan" and bo_qua_dong_loi):
            bao = _ghi_mot(db, d, s["tour_id"], boi)
            if bao["mat_dong_khach"]:
                mat_khach.append({"ten_tep": d.get("ten_tep"), "ma_tour": s.get("ma_tour"),
                                  "so_dong_khach": bao["mat_dong_khach"]})
            da_nap.append({"ten_tep": d.get("ten_tep"), "ma_tour": s.get("ma_tour"),
                           "tour_id": s["tour_id"], "co_canh_bao": ro == "can_xac_nhan"})
        else:
            bo_qua.append({"ten_tep": d.get("ten_tep"), "ma_tour": s.get("ma_tour"), "ro": ro,
                           "vi_sao": (s.get("chan") or []) + (s.get("can_xac_nhan") or [])})

    ra = {
        "so_dong": len(rows),
        "da_nap": len(da_nap),
        "da_co": sum(1 for x in bo_qua if x["ro"] == "can_xac_nhan"),
        "dong_loi": sum(1 for x in bo_qua if x["ro"] in ("chan", "khong_thay_chuyen")),
        "nguon": NGUON,
        "so_gan_nguoi_ban": so_gan,
        "chi_tiet_da_nap": da_nap,
        "chi_tiet_bo_qua": bo_qua,
        "khong_ghi_tien_muc_chuyen": (
            "Doanh thu và giá vốn MỨC CHUYẾN của các chuyến này KHÔNG bị đụng tới. Bộ đọc chỉ rút "
            "được 90,7% doanh thu và 71,1% giá vốn so với bản đối chiếu H1 (đo trên 594 tệp), phần "
            "lệch gần hết ở tour châu Âu ghi bằng EUR/GBP. Ghi tiền mức chuyến bằng số bộ đọc là "
            "làm hỏng đúng thứ đang định sửa."),
    }
    # Dòng khách không ghi được vì chuyến chưa có phiếu đặt: NÓI RA, không để nó biến mất trong một
    # con số "đã nạp" trông đẹp.
    if mat_khach:
        ra["mat_dong_khach_vi_chua_co_phieu_dat"] = mat_khach
        ra["canh_bao"] = (
            f"{len(mat_khach)} chuyến chưa có phiếu đặt nên "
            f"{sum(x['so_dong_khach'] for x in mat_khach)} dòng khách KHÔNG được ghi.")
    return ra


# =============================================================================================
# Khai vào khung nạp
# =============================================================================================

def bo_nap(_c) -> dict:
    return {
        "kho_quyet_toan_cu": {
            # Ba bảng cửa này thật sự ghi vào. `bang_dich` giữ bảng chính để màn hình và nhật ký
            # gọi tên được; `bang_phu` là phần còn lại. Khai đủ ở đây không phải cho đẹp: phép kiểm
            # "mọi bảng phải có một cửa" (ks_cua_nhap) đọc sống từ chỗ này.
            "bang_dich": "tour_cost_lines",
            "bang_phu": ("booking_khach", "tour_hdv_chi", "bookings", "kho_cu_nguoi_ban"),
            "phong_ban": "dieu_hanh",
            "lo": True,          # một tệp = một chuyến, kiểm và nạp cả tệp một lần
            "ten": "Kho quyết toán CŨ T1–T6/2026 (Excel tự do của Điều hành)",
            "mo_ta": (
                "Tệp quyết toán Điều hành lập bằng Excel TỰ DO trước khi có mẫu chuẩn VTOS – 604 tệp "
                "tháng 1 đến tháng 6/2026. Đo trên tệp thật: 108 bộ sheet khác nhau, bộ phổ biến "
                "nhất chỉ phủ 16%, 46 tệp chỉ có một sheet. Bộ đọc không hỏi 'sheet tên gì' mà hỏi "
                "'nhãn nằm ở đâu', nên một bộ đọc cho cả 108 bố cục.\n\n"
                "BA ĐIỀU BỘ ĐỌC TỰ CẤM MÌNH: không đoán mã tour từ tên tệp; không đọc ô tổng (mọi "
                "tổng cộng lại từ dòng — trên tệp Nha Trang, ô tổng một nhóm ghi 3.990.000 trong khi "
                "năm dòng của chính nhóm ấy cộng ra 4.200.000); và không ghi gì — phần quyết định "
                "nạp hay không nằm ở bước sau.\n\n"
                "CỬA NÀY KHÔNG GHI DOANH THU VÀ GIÁ VỐN MỨC CHUYẾN. Bộ đọc chỉ rút được 90,7% doanh "
                "thu và 71,1% giá vốn so với bản đối chiếu H1 mà Kế toán đã chốt; phần lệch gần hết "
                "ở tour châu Âu ghi bằng EUR/GBP. Cửa này chỉ bổ sung dòng khách, dòng chi phí và "
                "dòng HDV.\n\n"
                "Bản đối chiếu H1 chưa có cửa tải riêng, nên MỌI tệp đều mang một cảnh báo 'không có "
                "số thứ hai để soát'. Nghĩa là mặc định không tệp nào được ghi cho tới khi người "
                "duyệt bấm rõ 'nạp cả tệp có cảnh báo' — và lần bấm ấy vào nhật ký mang tên họ.\n\n"
                "Nạp lại cùng một tệp KHÔNG nhân đôi: mọi dòng mang nguồn riêng 'kho_cu_h1_2026', "
                "nạp lại thì xoá đúng phần mang nguồn ấy rồi ghi lại. Dòng do Vietrip hay do người "
                "nhập tay tạo ra không bị đụng tới."),
            "khoa_chong_trung": "Mã tour (đọc từ nhãn 'Mã tour:' trong tệp, KHÔNG suy từ tên tệp)",
            # Bảng cột này để MÀN HÌNH cho người tải biết tệp cần có gì. Bộ đọc thật không dùng nó –
            # nó dò theo nhãn, vì 108 bố cục không phẳng thành cột được.
            "cot": [
                _c("ma_tour", "Mã tour", True, vi_du="NT001.03100726",
                   ghi_chu="nhãn 'Mã tour:' ở đầu sheet quyết toán. KHÔNG có nhãn này thì tệp bị "
                           "chặn – bộ đọc không suy mã từ tên tệp, vì tên tệp đặt bằng tay"),
                _c("ten_tour", "Tên tour", vi_du="NHA TRANG"),
                _c("so_khach", "Số khách", kieu="so", ghi_chu="nhãn 'Số khách:' hoặc 'Số lượng:'"),
                _c("ngay_di", "Ngày đi", kieu="ngay", vi_du="10/07/2026",
                   ghi_chu="nhãn 'Ngày đi:' hoặc 'Khởi hành:'"),
                _c("ngay_ve", "Ngày về", kieu="ngay", vi_du="12/07/2026"),
                _c("hdv", "Hướng dẫn viên", ghi_chu="nhãn 'Hướng dẫn viên:', 'HDV:' hoặc 'TL:'"),
                _c("khach", "Bảng khách", ghi_chu="hàng tiêu đề có 'TÊN KHÁCH HÀNG' – mỗi dòng một "
                                                  "khách kèm giá bán"),
                _c("chi", "Bảng chi phí", ghi_chu="hàng tiêu đề có NGÀY | NỘI DUNG | ĐỐI TÁC | ĐƠN "
                                                  "GIÁ | SL | THÀNH TIỀN"),
                _c("hdv_chi", "Sheet HDV chi", ghi_chu="sheet tên 'HDV CHI', 'ỨNG' hoặc 'CTP' – có "
                                                       "'Tổng chi', 'ỨNG', 'HOÀN ỨNG'"),
            ],
            # Chế độ LÔ chỉ gọi kiem_lo / nap_lo / doc_tep. Vẫn khai kiem/nap cho đủ khung ba cửa:
            # khai_bao_du() tra đúng hai khoá này, thiếu chúng thì bộ nạp bị báo là khai thiếu.
            "kiem": kiem_lo, "nap": nap_lo,
            "kiem_lo": kiem_lo, "nap_lo": nap_lo, "doc_tep": doc_tep_lo,
        },
    }


def vai_tro(QUAN_TRI: tuple) -> dict:
    """Ai bấm được nút ghi.

    HẸP HƠN bộ nạp quyết toán thường, và có lý do: cửa này ghi vào 604 chuyến của sáu tháng đã khép
    sổ. Nhân viên Điều hành gõ tay một tờ quyết toán của chính mình thì được; đổ một lượt vào lịch
    sử nửa năm thì không.

    Kế toán có mặt vì họ là người giữ bản đối chiếu H1 – người duy nhất soát được số này với MISA.
    """
    return {"kho_quyet_toan_cu": QUAN_TRI + ("tp_dh", "ketoan")}
