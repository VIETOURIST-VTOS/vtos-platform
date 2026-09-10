"""V6 – bảng giá → báo giá → hợp đồng khách → booking, và cổng biên ở bước cam kết.

Lệnh Đợt 2, việc V6. Nghiệm thu: "một khách đi trọn đường: bảng giá → báo giá có phiên bản → hợp
đồng → booking, và cổng biên chặn được ở bước báo giá."

────────────────────────────────────────────────────────────────────────────────
CỔNG BIÊN Ở ĐÂY GIỮ NGUYÊN MỘT ĐIỀU LUẬT ĐÃ HỌC ĐƯỢC BẰNG GIÁ ĐẮT
────────────────────────────────────────────────────────────────────────────────

Ý kiến thẩm định 06/9/2026 mục B1: THIẾU GIÁ VỐN KHÔNG PHẢI LÀ GIÁ VỐN BẰNG 0. Trước đó, dự toán
không nhập giá vốn cho biên 100% và cổng biên luôn báo ĐẠT – tức là cổng chặn số một bị vô hiệu hóa
đúng ở những chuyến ít dữ liệu nhất, những chuyến đáng lo nhất.

Cổng của báo giá đi theo đúng luật đó: dòng nào chưa có giá vốn thì báo giá KHÔNG ĐỦ CƠ SỞ TÍNH BIÊN,
và trạng thái là "chưa đủ cơ sở" chứ không phải "đạt". Không đủ cơ sở thì không gửi khách được, trừ
khi có người ký giải trình – giống hệt trường hợp biên mỏng, vì hậu quả giống nhau.

Vì sao đặt ở BƯỚC GỬI chứ không ở bước lưu nháp: nháp là chỗ để thử con số. Chặn ở nháp thì sale
không ước lượng được gì, và cách lách rõ ràng nhất là ghi một giá vốn bịa cho qua cổng. Cam kết xảy
ra lúc GỬI, nên cổng đứng ở đó.
"""
from datetime import datetime, date
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.ban_hang import (BangGia, BangGiaDong, BaoGia, BaoGiaDong, BaoGiaBan,
                                 HopDongKhach, MANG)
from app.services import rules as R
from app.services import ghi_mot_lan as GML


class CongBaoGia(HTTPException):
    """Cổng chặn ở bước gửi báo giá. Dùng cùng hình dạng với Gate của dự toán tour để màn hình xử lý
    một kiểu, không phải học hai kiểu lỗi cho hai cổng làm cùng một việc."""

    def __init__(self, ma: str, thong_diep: str, **them):
        super().__init__(422, {"gate": ma, "message": thong_diep, **them})


# ────────────────────────────── BẢNG GIÁ ──────────────────────────────
def bang_gia_hieu_luc(db: Session, product_id: int, ngay: date | None = None) -> BangGia | None:
    """Bảng giá đang hiệu lực cho một sản phẩm vào một ngày.

    hieu_luc_den RỖNG = còn hiệu lực. Viết điều kiện này ra thay vì so với ngày hôm nay là chỗ dễ làm
    mọi bảng giá tự tắt sau một đêm.
    """
    ngay = ngay or date.today()
    q = (select(BangGia)
         .where(BangGia.product_id == product_id,
                BangGia.trang_thai == "hieu_luc",
                BangGia.hieu_luc_tu <= ngay,
                (BangGia.hieu_luc_den.is_(None)) | (BangGia.hieu_luc_den >= ngay))
         .order_by(BangGia.hieu_luc_tu.desc()))
    return db.execute(q).scalars().first()


def sinh_ma(db: Session, model, cot, tien_to: str) -> str:
    n = db.execute(select(func.count()).select_from(model)).scalar() or 0
    while True:
        ma = f"{tien_to}{n + 1:05d}"
        if db.execute(select(model).where(cot == ma)).scalars().first() is None:
            return ma
        n += 1


# ────────────────────────────── TÍNH BIÊN ──────────────────────────────
def tinh_bien(dong: list[BaoGiaDong], nguong: float) -> dict:
    """Ba con số của một báo giá, và trạng thái cổng.

    Trả về `du_co_so=False` khi CÓ dòng chưa ghi giá vốn. Không gộp im lặng dòng thiếu thành 0 – xem
    chú thích đầu tệp; đó là cách cổng biên từng bị vô hiệu hóa.
    """
    tong_ban = sum(float(d.don_gia or 0) * int(d.so_luong or 0) - float(d.chiet_khau or 0) for d in dong)
    thieu = [d for d in dong if d.gia_von_don_vi is None]
    if not dong:
        return {"tong_ban": 0.0, "tong_von": None, "bien": None, "nguong": nguong,
                "du_co_so": False, "dat": False, "vi_sao": "Báo giá chưa có dòng nào",
                "dong_thieu_gia_von": []}
    if thieu:
        return {"tong_ban": tong_ban, "tong_von": None, "bien": None, "nguong": nguong,
                "du_co_so": False, "dat": False,
                "vi_sao": (f"{len(thieu)} dòng chưa ghi giá vốn. Thiếu giá vốn KHÔNG phải giá vốn "
                           "bằng 0 – không có giá vốn thì không tính được biên, và cổng không thể ĐẠT."),
                "dong_thieu_gia_von": [d.mo_ta or d.hang_khach for d in thieu]}
    tong_von = sum(float(d.gia_von_don_vi or 0) * int(d.so_luong or 0) for d in dong)
    bien = (tong_ban - tong_von) / tong_ban if tong_ban else 0.0
    dat = bien >= nguong
    return {"tong_ban": tong_ban, "tong_von": tong_von, "bien": bien, "nguong": nguong,
            "du_co_so": True, "dat": dat,
            "vi_sao": ("" if dat else
                       f"Biên {bien * 100:.1f}% dưới ngưỡng {nguong * 100:.0f}%"),
            "dong_thieu_gia_von": []}


def xem_bien(db: Session, bg: BaoGia) -> dict:
    dong = db.execute(select(BaoGiaDong).where(BaoGiaDong.bao_gia_id == bg.id)
                      .order_by(BaoGiaDong.thu_tu, BaoGiaDong.id)).scalars().all()
    return tinh_bien(list(dong), R.get_param(db, "nguong_bien", bg.ngay_khoi_hanh))


# ────────────────────────────── GỬI KHÁCH ──────────────────────────────
DAI_GIAI_TRINH = 30


def gui_khach(db: Session, bg: BaoGia, boi: str, giai_trinh: str = "") -> BaoGiaBan:
    """Cổng biên đứng ở đây. Qua được thì sinh một bản ĐÓNG BĂNG.

    Ba lối ra, và chỉ ba:
      · đủ cơ sở và đạt ngưỡng            → gửi
      · đủ cơ sở, dưới ngưỡng             → phải có giải trình ≥ 30 ký tự
      · chưa đủ cơ sở (thiếu giá vốn)     → phải có giải trình, KHÔNG tự cho qua

    Trường hợp thứ ba cố ý không nhẹ hơn trường hợp thứ hai. Bán mà không biết lãi lỗ ít nhất cũng
    đáng lo bằng bán mà biết là mỏng.
    """
    if bg.trang_thai not in ("nhap", "cho_duyet_bien", "da_gui"):
        raise CongBaoGia("TRANG_THAI", f"Báo giá đang ở trạng thái '{bg.trang_thai}', không gửi được")
    kq = xem_bien(db, bg)
    if not kq["du_co_so"] or not kq["dat"]:
        if len((giai_trinh or "").strip()) < DAI_GIAI_TRINH:
            raise CongBaoGia(
                "CONG_BIEN_BAO_GIA",
                kq["vi_sao"] + f". Muốn gửi thì phải có giải trình ít nhất {DAI_GIAI_TRINH} ký tự: "
                               "vì sao chấp nhận, khoản nào làm mỏng biên, bù bằng gì.",
                **{k: kq[k] for k in ("tong_ban", "tong_von", "bien", "nguong", "du_co_so",
                                      "dong_thieu_gia_von")})
        bg.giai_trinh = giai_trinh.strip()
        bg.duoi_bien = True
    else:
        bg.duoi_bien = False
    lan = (db.execute(select(func.max(BaoGiaBan.lan))
                      .where(BaoGiaBan.bao_gia_id == bg.id)).scalar() or 0) + 1
    dong = db.execute(select(BaoGiaDong).where(BaoGiaDong.bao_gia_id == bg.id)
                      .order_by(BaoGiaDong.thu_tu, BaoGiaDong.id)).scalars().all()
    ban = BaoGiaBan(
        bao_gia_id=bg.id, lan=lan, tong_ban=kq["tong_ban"], tong_von=kq["tong_von"],
        bien=kq["bien"], nguong=kq["nguong"], du_co_so=kq["du_co_so"], gui_boi=boi,
        noi_dung=[{"hang_khach": d.hang_khach, "mo_ta": d.mo_ta, "so_luong": d.so_luong,
                   "don_gia": float(d.don_gia or 0),
                   "gia_von_don_vi": None if d.gia_von_don_vi is None else float(d.gia_von_don_vi),
                   "chiet_khau": float(d.chiet_khau or 0)} for d in dong])
    db.add(ban)
    bg.trang_thai = "da_gui"
    bg.bien_luc_gui = kq["bien"]
    bg.nguong_luc_gui = kq["nguong"]
    GML.tang_phien_ban(bg)
    db.flush()
    return ban


def khach_chot(db: Session, bg: BaoGia, boi: str) -> None:
    if bg.trang_thai != "da_gui":
        raise CongBaoGia("TRANG_THAI", "Chỉ báo giá ĐÃ GỬI mới chốt được – khách không chốt được cái "
                                       "chưa nhìn thấy")
    bg.trang_thai = "khach_chot"
    GML.tang_phien_ban(bg)
    db.flush()


# ────────────────────────────── HỢP ĐỒNG ──────────────────────────────
def lap_hop_dong(db: Session, bg: BaoGia, boi: str, **data) -> HopDongKhach:
    """Hợp đồng CHỈ lập từ báo giá khách đã chốt, và giá trị lấy từ BẢN ĐÃ GỬI gần nhất.

    Lấy từ bảng bao_gia đang soạn thì hợp đồng mang con số hôm nay, còn khách chốt con số hôm ấy –
    và chênh lệch đó chỉ lộ ra lúc đối chiếu doanh thu, thường là vài tháng sau.
    """
    if bg.trang_thai != "khach_chot":
        raise CongBaoGia("TRANG_THAI",
                         "Chỉ lập hợp đồng từ báo giá KHÁCH ĐÃ CHỐT. Trạng thái hiện tại: "
                         f"'{bg.trang_thai}'")
    ban = db.execute(select(BaoGiaBan).where(BaoGiaBan.bao_gia_id == bg.id)
                     .order_by(BaoGiaBan.lan.desc())).scalars().first()
    if ban is None:
        raise CongBaoGia("THIEU_BAN_GUI", "Báo giá chốt mà không có bản nào đã gửi – dữ liệu không "
                                          "nhất quán, không lập hợp đồng được")
    cu = db.execute(select(HopDongKhach).where(HopDongKhach.bao_gia_id == bg.id,
                                               HopDongKhach.trang_thai != "huy")).scalars().first()
    if cu is not None:
        raise CongBaoGia("DA_CO_HOP_DONG",
                         f"Báo giá này đã có hợp đồng {cu.so_hop_dong}", so_hop_dong=cu.so_hop_dong)
    hd = HopDongKhach(
        so_hop_dong=data.get("so_hop_dong") or sinh_ma(db, HopDongKhach, HopDongKhach.so_hop_dong, "HD"),
        bao_gia_id=bg.id, bao_gia_ban_id=ban.id, company_id=bg.company_id,
        khach_ten=data.get("khach_ten") or bg.khach_ten,
        khach_dai_dien=data.get("khach_dai_dien", ""), khach_ma_so_thue=data.get("khach_ma_so_thue", ""),
        khach_dia_chi=data.get("khach_dia_chi", ""), ngay_ky=data.get("ngay_ky"),
        gia_tri=float(ban.tong_ban or 0), dat_coc=None if data.get("dat_coc") in (None, "") else float(data["dat_coc"]),
        han_thanh_toan=data.get("han_thanh_toan"), ghi_chu=data.get("ghi_chu", ""), tao_boi=boi)
    db.add(hd); db.flush()
    return hd


def noi_booking(db: Session, hd: HopDongKhach, booking_id: int) -> None:
    """Nối hợp đồng với booking. Một hợp đồng nối đúng MỘT booking."""
    from app.models.core import Booking
    if db.get(Booking, booking_id) is None:
        raise CongBaoGia("KHONG_CO_BOOKING", f"Không có booking id {booking_id}")
    trung = db.execute(select(HopDongKhach).where(HopDongKhach.booking_id == booking_id,
                                                  HopDongKhach.id != hd.id)).scalars().first()
    if trung is not None:
        raise CongBaoGia("BOOKING_DA_CO_HOP_DONG",
                         f"Booking này đã nối với hợp đồng {trung.so_hop_dong}")
    hd.booking_id = booking_id
    GML.tang_phien_ban(hd)
    db.flush()


def chuoi_ban_hang(db: Session, hd: HopDongKhach) -> dict:
    """Trọn đường của một khách, đọc ngược từ hợp đồng. Dùng cho nghiệm thu và cho màn hình."""
    bg = db.get(BaoGia, hd.bao_gia_id) if hd.bao_gia_id else None
    ban = db.get(BaoGiaBan, hd.bao_gia_ban_id) if hd.bao_gia_ban_id else None
    bang = db.get(BangGia, bg.bang_gia_id) if bg is not None and bg.bang_gia_id else None
    return {
        "bang_gia": None if bang is None else {"id": bang.id, "ma": bang.ma, "ten": bang.ten},
        "bao_gia": None if bg is None else {"id": bg.id, "ma": bg.ma, "mang": bg.mang,
                                            "trang_thai": bg.trang_thai, "duoi_bien": bg.duoi_bien,
                                            "bien_luc_gui": bg.bien_luc_gui},
        "ban_da_gui": None if ban is None else {"id": ban.id, "lan": ban.lan,
                                                "tong_ban": float(ban.tong_ban or 0),
                                                "bien": ban.bien, "du_co_so": ban.du_co_so},
        "hop_dong": {"id": hd.id, "so_hop_dong": hd.so_hop_dong, "gia_tri": float(hd.gia_tri or 0),
                     "trang_thai": hd.trang_thai},
        "booking_id": hd.booking_id,
        "day_du": all([bang is not None, bg is not None, ban is not None, hd.booking_id is not None]),
    }


# ──────────────────── NỐI BÁO GIÁ VỚI DỰ TOÁN TOUR ────────────────────
# Việc thứ tư trong bảng rà soát 09/9. Trước đây giá vốn trong báo giá gõ tay, còn dự toán tour nằm ở
# một chỗ khác – hai nơi cùng giữ một con số thì sớm muộn lệch nhau, và lúc lệch thì biên trên báo giá
# là con số sai mà không ai biết là sai.
#
# Hàm này CHỈ trả về một con số tổng và mấy con số để giải thích nó. KHÔNG trả dòng chi tiết, không
# trả tên nhà cung cấp: người soạn báo giá không nằm trong COST_ROLES, và mở cả cơ cấu chi phí tour
# cho họ là một quyết định về quyền – việc của robot Phân quyền, không phải việc lén mở ở đây.
#
# Và nó KHÔNG tự điền vào dòng nào. Chia giá vốn cho các hạng khách (người lớn, trẻ em, em bé) là việc
# có phán đoán; máy chia hộ một con số nhìn rất gọn rồi người ký duyệt tin theo là cách hỏng đắt nhất.
def gia_von_tu_du_toan(db: Session, tour_id: int, so_khach: int = 1) -> dict:
    """Giá vốn một khách suy từ dự toán tour. Không có dòng dự toán thì trả RỖNG, không trả 0."""
    from app.models.vietrip import TourCostLine
    from app.models.core import Tour
    t = db.get(Tour, tour_id)
    if t is None:
        raise CongBaoGia("KHONG_CO_TOUR", f"Không có tour số {tour_id}")
    dong = db.execute(select(TourCostLine).where(TourCostLine.tour_id == tour_id,
                                                 TourCostLine.status == "hd")).scalars().all()
    if not dong:
        # Thiếu dự toán KHÔNG PHẢI dự toán bằng 0 (Ý kiến thẩm định 06/9 mục B1).
        return {"tour": t.code, "co_du_toan": False, "so_dong": 0, "gia_von_moi_khach": None,
                "co_dinh": None, "theo_khach_moi_khach": None, "so_khach": so_khach,
                "message": f"Tour {t.code} chưa có dòng dự toán nào – không suy ra được giá vốn."}

    def _tien(l) -> float:
        # Dự toán trước, thực chi sau: lúc soạn báo giá thì tour chưa chạy nên thực chi thường bằng 0,
        # và lấy 0 làm giá vốn là đúng cái lỗi đang muốn tránh.
        if l.budget:
            return float(l.budget)
        return float(l.unit_price or 0) * float(l.qty or 0) * float(l.coef or 1)

    co_dinh = sum(_tien(l) for l in dong if l.cost_kind != "theo_khach")
    # Dòng theo khách: đơn giá đã là của MỘT khách, nhân số lượng vào là nhân hai lần.
    theo_khach = sum(float(l.unit_price or 0) * float(l.coef or 1)
                     for l in dong if l.cost_kind == "theo_khach")
    n = max(int(so_khach or 1), 1)
    thieu = [l.description for l in dong if _tien(l) == 0 and l.cost_kind != "theo_khach"]
    return {"tour": t.code, "co_du_toan": True, "so_dong": len(dong), "so_khach": n,
            "co_dinh": round(co_dinh, 2), "theo_khach_moi_khach": round(theo_khach, 2),
            "gia_von_moi_khach": round(theo_khach + co_dinh / n, 2),
            "dong_chua_co_so_tien": thieu,
            "message": (f"{len(dong)} dòng dự toán · cố định {co_dinh:,.0f}đ chia cho {n} khách, "
                        f"cộng {theo_khach:,.0f}đ mỗi khách."
                        + (f" Còn {len(thieu)} dòng chưa có số tiền – con số này đang thiếu phần đó."
                           if thieu else ""))}
