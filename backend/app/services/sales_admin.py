"""Bàn làm việc của Sale Admin phòng Đoàn — vòng 3/3, 24/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
MÀN HÌNH NÀY KHÔNG THÊM MỘT QUYỀN GHI NÀO
═══════════════════════════════════════════════════════════════════════════════════════════════
Vòng 2 đã mở đúng hai cửa ghi cho vai này: `chuyen_dieu_hanh` và `tra_lai_kinh_doanh`. Vòng 3 chỉ
dựng chỗ ĐỌC quanh hai cửa ấy — sáu khối việc trong bản mô tả công việc hiệu lực 01/9/2026.

Bản mô tả cấm rõ (Phần V): không lập đề nghị dịch vụ, không giữ chỗ, không liên hệ nhà cung cấp,
không duyệt dự toán, không sửa số quyết toán. Mọi khối dưới đây vì thế chỉ TRẢ VỀ SỐ ĐỂ ĐỌC; nút
duy nhất trên màn hình là hai cửa của vòng 2.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ CỐ Ý KHÁC BẢN VẼ, MỖI CHỖ MỘT LÝ DO
═══════════════════════════════════════════════════════════════════════════════════════════════
1. KHÔNG CÓ EMAIL. Bản mô tả yêu cầu gửi báo cáo ngày qua thư trước 20:00. VTOS đã có đúng cơ chế
   ấy từ Điều 12 — `ops.DailyReport`, hạn 20:00, robot chấm điểm, thiếu 2 ngày thì cảnh báo đỏ về
   HCNS — và Chủ tịch đã quyết 09/9/2026 rằng báo cáo lập tự động trên màn hình, "không cần gửi
   mail hay Zalo". Nên khối 1 ở đây là một ĐƯỜNG DẪN tới màn hình báo cáo ngày đã có, cộng đồng
   hồ trạng thái hôm nay. Không dựng SMTP, không dựng hộp thư thứ hai.

2. CỘT "BIÊN NẾU TÍNH ĐỦ" SỐNG ĐƯỢC LÀ NHỜ MỘT Ô BẮT BUỘC, KHÔNG NHỜ MỘT PHÉP TÍNH KHÉO.
   Mục 4.2 bản mô tả buộc kiểm hoa hồng và quà tặng dành cho khách đã nằm trong giá vốn của chính
   đoàn ấy chưa. Rủi ro thật là: người bán hứa miệng 5% cho khách rồi không ghi vào dự toán, nên
   biên in ra đẹp hơn sự thật.
   VTOS KHÔNG nhìn thấy một lời hứa chưa ai viết ra — nên ngày 24/9/2026 Chủ tịch quyết thêm một ô
   BẮT BUỘC vào dự toán đoàn: hoa hồng khách có / không, có thì bao nhiêu. Bỏ trống thì không
   chuyển được. Có con số rồi thì `rules.bien_neu_hoa_hong_chua_vao` mới tính được biên thứ hai
   đặt cạnh biên đã nhập, và cột ấy mới là một con số thật chứ không phải một con số bịa.
   Cái ô KHÔNG tự cộng vào giá vốn: xem lý do trong chính hàm ấy.

3. QUÁ HẠN QUYẾT TOÁN DÙNG LẠI HÀM CỦA P.TGĐ, KHÔNG VIẾT BẢN THỨ HAI.
   `ptgd_doan.qua_han_quyet_toan` đã đọc hạn từ tham số `han_qt_doan`. Chép luật 7 ngày sang đây
   là dựng bản sao thứ hai: ngày Chủ tịch đổi tham số, một trong hai màn hình sẽ nói sai.

4. CỘT "HOA HỒNG ĐANG HOÃN CỦA AI" LẤY TỪ `luong.khoan_treo`, KHÔNG TỰ SUY.
   Đó là chỗ duy nhất trong hệ thống biết khoản treo là HOÃN chứ không phải CẮT. Tự suy lại ở đây
   thì sẽ có ngày màn hình đôn đốc nói "mất hoa hồng" trong khi bảng lương nói "chờ chốt".
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ban_hang import HopDongKhach
from app.models.core import Tour
from app.services import lich_thanh_toan as LTT
from app.services import ptgd_doan as PT
from app.services import rules as R
from app.services import settlement as ST
from app.services import tours as TS

# Loại dịch vụ dành cho hoa hồng trả cho khách. Khai ở đây để `soat_gia_von` và phép thử cùng nhìn
# vào một hằng số, thay vì rải chuỗi "COMMISSION" ở hai nơi.
DV_QUA_TANG = "GIFT"

# Năm loại giấy tờ bản mô tả buộc lưu theo từng mã đoàn (mục hồ sơ). Khóa trùng `LOAI_TEP` của
# `models/attachments.py`; thiếu khóa nào thì phải thêm ở đó trước, không tự đặt tên mới tại đây.
HO_SO_DOAN = (
    ("chuong_trinh", "Chương trình"),
    ("bao_gia", "Báo giá đã gửi"),
    ("hop_dong", "Hợp đồng"),
    ("phu_luc", "Phụ lục"),
    ("nghiem_thu", "Biên bản nghiệm thu"),
)


def _doan_dang_chay(db: Session, tu_ngay: date | None = None) -> list[Tour]:
    """Đoàn còn liên quan tới việc của Sale Admin: chưa khởi hành, hoặc vừa kết thúc chưa chốt sổ.

    Không lọc theo người phụ trách: bản mô tả giao cho vai này SOÁT cả phòng, và một danh sách chỉ
    có đoàn của riêng mình thì đúng chỗ cần soát nhất — đoàn của người khác — lại không ai nhìn.
    """
    ra = []
    for t in db.execute(select(Tour)).scalars():
        if not R.is_doan(t):
            continue
        if getattr(t, "closed_at", None):
            continue
        ra.append(t)
    ra.sort(key=lambda t: (t.start_date or date.max))
    return ra


# ───────────────────────────── khối 2 · dự toán chờ tôi chuyển ─────────────────────────────

def cho_toi_chuyen(db: Session) -> list[dict]:
    """Dự toán đoàn đang ở `nhap_kd` — chỗ duy nhất Sale Admin có nút.

    `thieu` tính lại bằng chính hàm bước chuyển dùng (`tours._thieu_truong_de_chuyen`), không chép
    tay: ngày cổng ấy siết thêm điều kiện, màn hình không được phép vẫn báo "đủ trường".
    """
    ra: list[dict] = []
    for t in db.execute(select(Tour).where(Tour.status == TS.NHAP_KD)).scalars():
        if not R.is_doan(t):
            continue
        thieu = TS._thieu_truong_de_chuyen(db, t)
        c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
        ra.append({
            "tour_id": t.id, "ma": t.code, "ten": t.name,
            "khoi_hanh": t.start_date.isoformat() if t.start_date else None,
            "con_bao_nhieu_ngay": (t.start_date - date.today()).days if t.start_date else None,
            "bien_ke_hoach": c["margin"],
            "duoi_bien": bool(c.get("below_margin")),
            "thieu": thieu,
            # Nói thẳng nút nào sáng, thay vì để màn hình tự suy từ `thieu` rồi suy lệch.
            "chuyen_duoc": not thieu,
        })
    ra.sort(key=lambda d: (d["con_bao_nhieu_ngay"] is None, d["con_bao_nhieu_ngay"]))
    return ra


# ───────────────────────────── khối 3 · soát giá vốn và chứng từ NCC ─────────────────────────────

def soat_gia_von(db: Session) -> list[dict]:
    """Chỗ Sale Admin ĐỌC giá vốn để soát — quyền xem Chủ tịch mở 24/9/2026.

    Ba điều được nói ra, không điều nào là con số hệ thống tự bịa:
      · ô hoa hồng khách CHƯA TRẢ LỜI, hoặc đã khai "có" kèm số tiền — và khi có số tiền thì kèm
        luôn BIÊN NẾU KHOẢN ẤY CHƯA NẰM TRONG GIÁ VỐN (`rules.bien_neu_hoa_hong_chua_vao`);
      · dòng chi phí chưa gắn chứng từ;
      · dòng ≥ 5 triệu mà nhà cung cấp chưa có mã số thuế.
    Hai cái sau dùng lại `settlement.checks`, không chấm lại bằng luật riêng.

    Cột "biên nếu tính đủ" của bản vẽ sống được CHÍNH VÌ có ô bắt buộc: trước khi có ô, con số ấy
    phải bịa ra từ một khoản hệ thống chưa từng được cho biết.
    """
    ra: list[dict] = []
    for t in _doan_dang_chay(db):
        c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
        hh = R.bien_neu_hoa_hong_chua_vao(t, c)
        khai = (getattr(t, "hoa_hong_khach", "") or "").strip()
        dong = ST.lines_of(db, t, active_only=True)
        canh = [x for x in ST.checks(db, t) if x["level"] in ("block", "warn")] if dong else []
        if khai in ("co", "khong") and not canh:
            continue
        ra.append({
            "tour_id": t.id, "ma": t.code, "ten": t.name,
            "khoi_hanh": t.start_date.isoformat() if t.start_date else None,
            "so_dong_chi_phi": len(dong),
            "hoa_hong_khach": khai,          # "" = chưa trả lời, không phải "không có"
            "da_tra_loi_hoa_hong": khai in ("co", "khong"),
            "hoa_hong_khach_tien": hh["tien"],
            "bien_ke_hoach": c["margin"],
            "bien_neu_hoa_hong_chua_vao": hh["bien_neu_chua_vao"],
            "co_dong_qua_tang": any(l.service_type == DV_QUA_TANG for l in dong),
            "canh_bao": canh,
        })
    return ra


# ───────────────────────────── khối 4 · hồ sơ đoàn ─────────────────────────────

def ho_so_doan(db: Session) -> list[dict]:
    """Năm loại giấy tờ trên từng mã đoàn — dựng bằng phép SUY trên kho tệp đã có.

    Không thêm bảng lưu: hồ sơ đã nằm ở `attachments` với `doi_tuong="tour"`. Cái thiếu trước đây
    là người tải lên không khai được ĐÂY LÀ LOẠI GÌ — nên checklist này chỉ đúng khi `LOAI_TEP` có
    đủ năm khóa ở `HO_SO_DOAN`. Thiếu khóa nào thì cột ấy luôn hiện "thiếu", và đó là lỗi cấu hình
    chứ không phải lỗi của người làm hồ sơ; hàm nói ra điều đó ở `khoa_chua_khai_bao`.
    """
    from app.models.attachments import LOAI_TEP
    from app.services import attachments as AT

    chua_khai = [k for k, _ in HO_SO_DOAN if k not in LOAI_TEP]
    ra: list[dict] = []
    for t in _doan_dang_chay(db):
        tep = AT.danh_sach(db, doi_tuong="tour", doi_tuong_id=str(t.id), limit=500)
        co = {x.get("loai") for x in tep}
        thieu = [ten for k, ten in HO_SO_DOAN if k not in co]
        ra.append({
            "tour_id": t.id, "ma": t.code, "ten": t.name,
            "khoi_hanh": t.start_date.isoformat() if t.start_date else None,
            "so_tep": len(tep),
            "du": {k: (k in co) for k, _ in HO_SO_DOAN},
            "thieu": thieu,
            "khoa_chua_khai_bao": chua_khai,
        })
    return ra


# ───────────────────────────── khối 5 · tiến độ thu tiền ─────────────────────────────

def tien_do_thu_tien(db: Session) -> dict:
    """Bảng thu theo mốc hợp đồng — gọi thẳng `lich_thanh_toan.bang`, không cộng lại bằng tay.

    Bản mô tả buộc NHẮC TRƯỚC mỗi mốc, không đợi quá hạn. Nên danh sách trả về hai nhóm: sắp tới
    hạn và đã quá hạn; gộp chung thì cái sắp tới hạn chìm dưới cái đã hỏng.
    """
    hom_nay = date.today()
    sap_toi: list[dict] = []
    for hd in db.execute(select(HopDongKhach).where(
            HopDongKhach.trang_thai.notin_(["huy", "thanh_ly"]))).scalars():
        b = LTT.bang(db, hd, hom_nay)
        for d in b["dot"]:
            if d["trang_thai"] != "cho_den_han" or not d["han"]:
                continue
            con = (d["han"] - hom_nay).days
            if con > 14:
                continue
            sap_toi.append({"hop_dong_id": hd.id, "so_hop_dong": hd.so_hop_dong,
                            "khach_ten": hd.khach_ten, "dot": d["dot"], "ten": d["ten"],
                            "han": d["han"].isoformat(), "so_tien": d["so_tien"],
                            "con_bao_nhieu_ngay": con})
    sap_toi.sort(key=lambda d: d["con_bao_nhieu_ngay"])
    qh = [{**d, "han": d["han"].isoformat() if d["han"] else None} for d in LTT.qua_han(db, hom_nay)]
    return {"sap_toi_han": sap_toi, "qua_han": qh,
            "ghi_chu": "Nhắc TRƯỚC mốc: danh sách 'sắp tới hạn' lấy 14 ngày tới, tách khỏi nhóm đã quá hạn."}


# ───────────────────────────── khối 6 · tiến độ quyết toán ─────────────────────────────

def tien_do_quyet_toan(db: Session) -> dict:
    """Đoàn quá hạn chốt sổ, kèm câu trả lời cho "ai đang chờ tiền vì chuyến này".

    Hai nguồn, không nguồn nào viết lại: `ptgd_doan.qua_han_quyet_toan` cho danh sách quá hạn,
    `luong.khoan_treo` cho khoản hoa hồng đang HOÃN (không phải cắt — xem ghi chú 4 đầu tệp).
    """
    from app.services import luong as LG

    qh = PT.qua_han_quyet_toan(db)
    treo = LG.khoan_treo(db)
    theo_ma: dict[str, list[dict]] = {}
    for r in treo.get("rows", []):
        theo_ma.setdefault(r["tour_code"], []).append(
            {"ma_nv": r["ma"], "ten": r["ten"], "vai_tro": r["vai_tro"], "ly_do": r["ly_do"]})
    for nhom in ("chua_dong_so", "dong_muon"):
        for d in qh[nhom]:
            d["dang_cho_tien"] = theo_ma.get(d["ma"], [])
    qh["ghi_chu"] = ("Hoa hồng của đoàn quá hạn là HOÃN tới khi chốt sổ, không phải cắt "
                     "— lấy nguyên câu từ bảng lương, không diễn giải lại.")
    return qh


# ───────────────────────────── khối 7 · dữ liệu khách đoàn ─────────────────────────────

def du_lieu_khach(db: Session) -> list[dict]:
    """Đủ dữ liệu khách trước khi đoàn chạy chưa.

    Đếm được: khách theo hợp đồng (`planned_pax`) so với chỗ đã đặt (`rules.booked_pax`), và nguồn
    khách đã ghi chưa (`Booking.source`).

    KHÔNG đếm được hôm nay: "thoả thuận chia data". Không có ô ấy ở bất kỳ đâu trong hệ thống, nên
    hàm trả về `thoa_thuan_chia_data=None` — nghĩa là CHƯA HỎI, không phải "chưa ghi". Để một màn
    hình in "Chưa ghi" cho một ô không tồn tại là nói với người dùng rằng có một việc họ quên làm,
    trong khi thật ra là một việc hệ thống chưa mở cửa cho họ làm.
    """
    ra: list[dict] = []
    for t in _doan_dang_chay(db):
        if not t.start_date or t.start_date < date.today():
            continue
        bs = [b for b in t.bookings if not b.cancelled]
        ra.append({
            "tour_id": t.id, "ma": t.code, "ten": t.name,
            "khoi_hanh": t.start_date.isoformat(),
            "khach_theo_hop_dong": t.planned_pax,
            "cho_da_dat": R.booked_pax(t),
            "so_booking": len(bs),
            "booking_chua_ghi_nguon": [b.code for b in bs if not (b.source or "").strip()],
            "thoa_thuan_chia_data": None,
        })
    return ra


# ───────────────────────────── bàn làm việc ─────────────────────────────

from app.services import ops as OPS_BC  # noqa: E402


def ban_lam_viec(db: Session) -> dict:
    chuyen = cho_toi_chuyen(db)
    gv = soat_gia_von(db)
    hs = ho_so_doan(db)
    thu = tien_do_thu_tien(db)
    qt = tien_do_quyet_toan(db)
    kh = du_lieu_khach(db)
    return {
        "cho_toi_chuyen": chuyen,
        "soat_gia_von": gv,
        "ho_so_doan": hs,
        "tien_do_thu_tien": thu,
        "tien_do_quyet_toan": qt,
        "du_lieu_khach": kh,
        "bao_cao_ngay": {
            "man_hinh": "/bao-cao-ngay",
            # BC-1: hạn đọc từ luật báo cáo ngày, không gõ lại ở đây.
            "han": OPS_BC.han_chu(db, OPS_BC.gio_vn().date()),
            "ghi_chu": ("Báo cáo ngày nộp trên VTOS (Điều 12), không gửi thư — Chủ tịch quyết "
                        "09/9/2026: báo cáo lập tự động trên màn hình."),
        },
        "dem": {
            "cho_toi_chuyen": len(chuyen),
            "chuyen_duoc_ngay": len([d for d in chuyen if d["chuyen_duoc"]]),
            "phai_tra_lai": len([d for d in chuyen if not d["chuyen_duoc"]]),
            "doan_chua_tra_loi_hoa_hong": len([d for d in gv if not d["da_tra_loi_hoa_hong"]]),
            "ho_so_con_thieu": len([d for d in hs if d["thieu"]]),
            "moc_thu_sap_toi_han": len(thu["sap_toi_han"]),
            "moc_thu_qua_han": len(thu["qua_han"]),
            "qua_han_chua_dong_so": len(qt["chua_dong_so"]),
            "dong_so_muon": len(qt["dong_muon"]),
            "doan_thieu_ten_khach": len([d for d in kh if d["cho_da_dat"] < (d["khach_theo_hop_dong"] or 0)]),
        },
    }
