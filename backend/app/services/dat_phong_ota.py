# -*- coding: utf-8 -*-
"""KS-10 · Cửa vào cơ sở dữ liệu cho đơn khách sạn — lớp nằm giữa LUẬT và MÁY CHỦ.

KS-6 viết LUẬT sáu bước Agoda và cố ý không nhận `db`: luật phải đọc được, chạy thử được mà
không cần cơ sở dữ liệu. Tệp này là nửa còn lại — dựng đơn, ghi từng bước, ghi nhật ký.

CHƯA CÓ ĐƯỜNG NỐI SANG AGODA. Địa chỉ Demand API nằm sau đăng nhập đối tác, Vietourist chưa
có. Nên mỗi con số của nguồn vào hệ thống bằng đúng MỘT TRONG HAI cách, không có cách thứ ba:

  · Môi trường «Thử»       — máy tự sinh mã giả để chạy hết sáu bước mà không cần Agoda. Đơn
    thử KHÔNG BAO GIỜ vào báo cáo tiền; KS-6 `vao_bao_cao_tien` đã chặn sẵn ở tầng luật.
  · Môi trường «Chạy thật» — Điều hành DÁN kết quả tra cứu từ Agoda vào cửa nhập. Máy không bịa
    một con số nào: thiếu ô nào thì gọi đúng tên ô ấy ra và dừng.

Tệp này KHÔNG gọi mạng. Khi có đường nối thật, chỗ nối vào đúng một nơi: `nhan_so_nguon`.

VÌ SAO CHƯA PHẢI CỬA CHO KHÁCH: bảng đơn của KS-6 không có cột nào ghi NGƯỜI ĐẶT — không tên
khách, không liên hệ, không tài khoản cổng ngoài. Mở cửa đặt phòng cho khách lúc này nghĩa là
ai biết thẻ tham chiếu cũng đọc được đơn của người khác. Vòng này vì thế là cửa cho ĐIỀU HÀNH;
cửa cho khách cần thêm cột và là một vòng riêng.
"""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.don_khach_san_ota import (BUOC_DON, DON_DONG, KIEU_THANH_TOAN, LY_DO_HUY,
                                          TRANG_THAI_DON, TRANG_THAI_NGUON, BuocDonOta,
                                          DonKhachSanOta)
from app.models.khach_san_ota import MOI_TRUONG_OTA, DoiTacOta
from app.services import don_khach_san_ota as D
from app.services.khach_san_ota import LoiOta, co_quyen

# Ai được xem đơn, ai được thao tác. Điều hành là người trực tiếp làm việc với nguồn.
VAI_XEM = ("chutich", "tgd", "bks", "tp_dh", "robot_ks")
VAI_LAM = ("chutich", "tp_dh")

# Những ô mà NGUỒN trả về, không phải mình nghĩ ra. Ở «Chạy thật» thiếu ô nào là dừng ô ấy.
SO_CUA_NGUON = ("ma_tim", "ma_khoi", "ma_khach_san", "ma_phong", "ma_goi_gia", "gia_gom_thue")
TEN_O = {
    "ma_tim": "mã tìm (searchId)",
    "ma_khoi": "mã khối phòng (blockId)",
    "ma_khach_san": "mã khách sạn (propertyId)",
    "ma_phong": "mã phòng (roomId)",
    "ma_goi_gia": "mã gói giá (ratePlanId)",
    "gia_gom_thue": "giá đã gồm thuế (rate.inclusive)",
}

# Những ô người đặt khai, phải giữ y nguyên qua cả ba bước.
O_DIEU_KIEN = ("ngay_nhan", "ngay_tra", "so_phong", "nguoi_lon", "tre_em", "tuoi_tre_em",
               "nuoc_khach", "ngon_ngu", "tien_te")

# Tên tiếng Việt của sáu bước. BUOC_DON giữ tên Agoda để tra tài liệu; màn hình cần tên tiếng
# Việt, và nơi khai là ĐÂY chứ không phải trong mã giao diện — gõ lại ở màn thì ngày đổi tên,
# màn lệch mà không ai biết.
BUOC_VI = {
    "tim": "Hỏi giá",
    "soat_truoc": "Soát trước",
    "dat": "Đặt",
    "tra_don": "Tra đơn",
    "xem_huy": "Xem huỷ",
    "huy": "Chốt huỷ",
}

GIOI_HAN_DS = 200


# ---------------------------------------------------------------- thẻ tham chiếu

def the_tham_chieu_moi() -> str:
    """`tag` của Agoda — số của MÌNH, và là cách duy nhất tra lại một lần gọi quá hạn.

    Phải duy nhất tuyệt đối. Không dùng số đếm: hai tiến trình đếm cùng lúc ra cùng một số, và
    chỗ hỏng chỉ lộ ra lúc tra Booking List thấy hai đơn cùng thẻ.
    """
    return "VTD" + uuid.uuid4().hex[:24].upper()


# ---------------------------------------------------------------- số của nguồn

def thieu_de_hoi_gia(ota: DoiTacOta, d: dict) -> list[str]:
    """Chưa đủ cái gì thì chưa dựng được đơn."""
    t = []
    if not co_quyen(ota, "SEARCH"):
        t.append("chưa ghi nhận nguồn cấp quyền SEARCH")
    if getattr(ota, "moi_truong", "tat") == "tat":
        t.append("môi trường đang Tắt — bật Thử hoặc Chạy thật ở màn Khách sạn OTA")
    if not d.get("ngay_nhan") or not d.get("ngay_tra"):
        t.append("chưa có ngày nhận / ngày trả phòng")
    elif str(d["ngay_tra"]) <= str(d["ngay_nhan"]):
        t.append("ngày trả phải sau ngày nhận")
    if int(d.get("so_phong") or 0) < 1:
        t.append("số phòng phải từ 1")
    if int(d.get("nguoi_lon") or 0) < 1:
        t.append("số người lớn phải từ 1")
    return t


def thieu_so_nguon(moi_truong: str, d: dict) -> list[str]:
    """Ở «Chạy thật», sáu con số này phải do Điều hành dán từ Agoda sang. Máy không bịa."""
    if moi_truong != "that":
        return []
    t = []
    for k in SO_CUA_NGUON:
        v = d.get(k)
        if v is None or str(v).strip() == "" or (k != "ma_khoi" and float(v or 0) <= 0):
            t.append("chưa dán " + TEN_O[k])
    return t


def sinh_so_thu() -> dict:
    """Mã giả cho môi trường «Thử».

    Mã của Agoda là số 64 bit — `searchId` mẫu trong tài liệu là 633141408144250000. Sinh số
    nhỏ ở đây thì phép thử không bao giờ chạm vào chỗ tràn số, và chỗ ấy sẽ nổ ở ngày chạy thật.
    """
    r = uuid.uuid4().int
    return {
        "ma_tim": 633_000_000_000_000_000 + (r % 999_999_999_999_999),
        "ma_khoi": "THU-" + uuid.uuid4().hex[:20],
        "ma_khach_san": 7_000_000_000 + (r >> 17) % 999_999_999,
        "ma_phong": 9_000_000_000 + (r >> 29) % 999_999_999,
        "ma_goi_gia": 11_000_000_000 + (r >> 41) % 999_999_999,
        "gia_gom_thue": 1_000_000 + (r >> 53) % 9_000_000,
        "kieu_thanh_toan": "merchant",
    }


def nhan_so_nguon(don: DonKhachSanOta, d: dict, now: datetime | None = None) -> None:
    """Chép số của nguồn vào đơn. Đây là CHỖ DUY NHẤT sẽ nối vào Agoda khi có đường."""
    don.ma_tim = int(d.get("ma_tim") or 0)
    don.ma_khoi = str(d.get("ma_khoi") or "")[:500]
    don.the_chao = str(d.get("the_chao") or "")[:500]
    don.ma_khach_san = int(d.get("ma_khach_san") or 0)
    don.ma_phong = int(d.get("ma_phong") or 0)
    don.ma_goi_gia = int(d.get("ma_goi_gia") or 0)
    don.gia_gom_thue = float(d.get("gia_gom_thue") or 0)
    kt = str(d.get("kieu_thanh_toan") or "").strip()
    don.kieu_thanh_toan = kt if kt in KIEU_THANH_TOAN else ""
    don.phu_thu = str(d.get("phu_thu") or "")
    don.tim_luc = now or datetime.utcnow()
    don.trang_thai = "da_hoi_gia"


# ---------------------------------------------------------------- lấy và ghi

def _lay_ota(db: Session, ota_id: int) -> DoiTacOta:
    o = db.get(DoiTacOta, int(ota_id or 0))
    if o is None:
        raise LoiOta("Không thấy nguồn OTA này", 404)
    return o


def lay_don(db: Session, don_id: int) -> DonKhachSanOta:
    d = db.get(DonKhachSanOta, int(don_id or 0))
    if d is None:
        raise LoiOta("Không thấy đơn này", 404)
    return d


def ghi_buoc(db: Session, don: DonKhachSanOta, buoc: str, ma_tra_ve: int = 0,
             qua_han: bool = False, tom_tat: str = "", boi: str = "",
             now: datetime | None = None) -> None:
    """Một dòng cho MỖI lần gọi, kể cả lần quá hạn.

    Không có nhật ký thì câu «Agoda đã nhận đơn chưa» không có chỗ nào trả lời được, và người
    trực đêm sẽ trả lời bằng cách bấm đặt lại.
    """
    if buoc not in BUOC_DON:
        raise LoiOta("Bước lạ: " + str(buoc)[:30])
    db.add(BuocDonOta(don_id=don.id, buoc=buoc, luc=now or datetime.utcnow(),
                      ma_tra_ve=int(ma_tra_ve or 0), qua_han=bool(qua_han),
                      tom_tat=str(tom_tat or "")[:2000], boi=str(boi or "")[:80]))


def _dong_dau(don: DonKhachSanOta, boi: str, now: datetime | None = None) -> None:
    don.sua_boi = str(boi or "")[:80]
    don.sua_luc = now or datetime.utcnow()


# ---------------------------------------------------------------- sáu bước

def hoi_gia(db: Session, boi: str, d: dict, now: datetime | None = None) -> DonKhachSanOta:
    """Bước 1 · Search. Dựng đơn và đóng dấu môi trường."""
    ota = _lay_ota(db, d.get("ota_id"))
    thieu = thieu_de_hoi_gia(ota, d)
    if thieu:
        raise LoiOta("Chưa hỏi giá được: " + "; ".join(thieu))
    moi_truong = getattr(ota, "moi_truong", "tat")
    thieu_so = thieu_so_nguon(moi_truong, d)
    if thieu_so:
        raise LoiOta("Chưa hỏi giá được: " + "; ".join(thieu_so))

    don = DonKhachSanOta(the_tham_chieu=the_tham_chieu_moi(), ota_id=ota.id,
                         moi_truong=moi_truong, trang_thai="moi", trang_thai_nguon="")
    for k in O_DIEU_KIEN:
        if k in d and d[k] is not None:
            setattr(don, k, d[k])
    nhan_so_nguon(don, sinh_so_thu() if moi_truong == "thu" else d, now)
    don.ghi_chu = str(d.get("ghi_chu") or "")
    _dong_dau(don, boi, now)
    db.add(don)
    db.flush()
    ghi_buoc(db, don, "tim", 200, False,
             "môi trường %s · mã tìm %s" % (moi_truong, don.ma_tim), boi, now)
    db.commit()
    return don


def soat_truoc(db: Session, boi: str, don_id: int, gui: dict,
               now: datetime | None = None) -> dict:
    """Bước 2 · Precheck. Trả về những ô lệch so với lúc hỏi giá, KHÔNG tự sửa đơn."""
    don = lay_don(db, don_id)
    lech = D.lech_ba_buoc(don, gui or {})
    con_han = D.con_han_ma_tim(don, now)
    ghi_buoc(db, don, "soat_truoc", 200 if (not lech and con_han) else 501, False,
             "; ".join(lech) if lech else ("mã tìm quá hạn" if not con_han else "khớp"),
             boi, now)
    db.commit()
    return {"lech": lech, "con_han_ma_tim": con_han, "don": D.tom_tat(don)}


def dat(db: Session, boi: str, don_id: int, d: dict, now: datetime | None = None) -> dict:
    """Bước 3 · Book.

    Hai lối ra, và lối thứ hai mới là lối quan trọng: QUÁ HẠN. Tài liệu nói thẳng «should not
    immediately resend the same booking request» — nên quá hạn thì đơn chuyển sang «chờ tra
    cứu», và không ai gửi lại được cho tới khi tra Booking List bằng thẻ tham chiếu.
    """
    don = lay_don(db, don_id)
    ota = _lay_ota(db, don.ota_id)
    thieu = D.thieu_de_dat(don, ota, now)
    if thieu:
        raise LoiOta("Chưa đặt được: " + "; ".join(thieu))
    if not D.dat_lai_duoc(don):
        raise LoiOta("Đơn đang chờ tra cứu — phải tra Booking List bằng thẻ tham chiếu trước, "
                     "không được gửi lại")

    if d.get("qua_han"):
        D.ghi_qua_han_dat(don)
        _dong_dau(don, boi, now)
        ghi_buoc(db, don, "dat", 0, True, "quá %d giây, chưa có trả lời" % D.HAN_DAT_GIAY,
                 boi, now)
        db.commit()
        return {"qua_han": True, "don": D.tom_tat(don)}

    tra_loi = d.get("tra_loi") or {}
    if don.moi_truong == "thu" and not tra_loi.get("id"):
        r = uuid.uuid4().int
        tra_loi = {"id": 80_000_000_000 + r % 999_999_999,
                   "itineraryId": 90_000_000_000 + (r >> 23) % 999_999_999,
                   "processing": False}
    D.ghi_dat_xong(don, tra_loi, now)
    _dong_dau(don, boi, now)
    ghi_buoc(db, don, "dat", 200, False,
             "mã đơn nguồn %s%s" % (don.ma_don_nguon, " · đang xử lý" if don.dang_xu_ly else ""),
             boi, now)
    db.commit()
    return {"qua_han": False, "don": D.tom_tat(don)}


def nhan_trang_thai(db: Session, boi: str, don_id: int, d: dict,
                    now: datetime | None = None) -> dict:
    """Bước 4 · Booking Detail. Điều hành chép trạng thái và số xác nhận của nguồn vào."""
    don = lay_don(db, don_id)
    tt = str(d.get("trang_thai_nguon") or "").strip()
    if tt:
        D.nhan_trang_thai_nguon(don, tt)
    if "so_xac_nhan_ks" in d:
        don.so_xac_nhan_ks = str(d.get("so_xac_nhan_ks") or "")[:64]
    if "tham_chieu_nguon" in d:
        don.tham_chieu_nguon = str(d.get("tham_chieu_nguon") or "")[:64]
    _dong_dau(don, boi, now)
    ghi_buoc(db, don, "tra_don", 200, False,
             "%s · số đối chiếu %s" % (tt or "(không đổi)", D.so_de_doi_chieu(don) or "—"),
             boi, now)
    db.commit()
    return {"don": D.tom_tat(don), "so_doi_chieu": D.so_de_doi_chieu(don)}


def xem_huy(db: Session, boi: str, don_id: int, now: datetime | None = None) -> dict:
    """Bước 5 · Cancel preview. Chỉ soi điều kiện, chưa huỷ gì."""
    don = lay_don(db, don_id)
    ota = _lay_ota(db, don.ota_id)
    thieu = D.thieu_de_huy(don, ota, now.date() if now else None)
    ghi_buoc(db, don, "xem_huy", 200 if not thieu else 400, False,
             "; ".join(thieu) if thieu else "huỷ được", boi, now)
    db.commit()
    return {"thieu": thieu, "huy_duoc": not thieu, "ly_do_huy": LY_DO_HUY,
            "don": D.tom_tat(don)}


def huy(db: Session, boi: str, don_id: int, xem: dict, gui: dict,
        now: datetime | None = None) -> dict:
    """Bước 6 · Confirm cancel. Ba con số phải khớp bản xem trước, lệch là lỗi 914."""
    don = lay_don(db, don_id)
    ota = _lay_ota(db, don.ota_id)
    thieu = D.thieu_de_huy(don, ota, now.date() if now else None)
    if thieu:
        raise LoiOta("Chưa huỷ được: " + "; ".join(thieu))
    lech = D.lech_xac_nhan_huy(don, xem or {}, gui or {})
    if lech:
        ghi_buoc(db, don, "huy", 914, False, "; ".join(lech), boi, now)
        db.commit()
        raise LoiOta("Không khớp bản xem trước (lỗi 914): " + "; ".join(lech))

    don.tham_chieu_huy = int(gui.get("reference") or 0)
    don.ly_do_huy = int(gui.get("cancelReason") or 0)
    don.hoan_gom_thue = float(gui.get("refundInclusive") or 0)
    don.huy_luc = now or datetime.utcnow()
    don.trang_thai = "da_huy"
    don.trang_thai_nguon = "BookingCancelled"
    _dong_dau(don, boi, now)
    ghi_buoc(db, don, "huy", 200, False,
             "hoàn %s · lý do %s" % (don.hoan_gom_thue, LY_DO_HUY.get(don.ly_do_huy, "?")),
             boi, now)
    db.commit()
    return {"don": D.tom_tat(don)}


# ---------------------------------------------------------------- xem

def nhat_ky(db: Session, don_id: int) -> list[dict]:
    don = lay_don(db, don_id)
    ds = db.execute(select(BuocDonOta).where(BuocDonOta.don_id == don.id)
                    .order_by(BuocDonOta.id)).scalars().all()
    return [{"buoc": b.buoc, "buoc_ten": BUOC_DON.get(b.buoc, b.buoc),
             "luc": b.luc.isoformat() if b.luc else None, "ma_tra_ve": b.ma_tra_ve,
             "qua_han": bool(b.qua_han), "tom_tat": b.tom_tat, "boi": b.boi} for b in ds]


def ds(db: Session, trang_thai: str = "", moi_truong: str = "") -> dict:
    q = select(DonKhachSanOta).order_by(DonKhachSanOta.id.desc()).limit(GIOI_HAN_DS)
    if trang_thai:
        q = q.where(DonKhachSanOta.trang_thai == trang_thai)
    if moi_truong:
        q = q.where(DonKhachSanOta.moi_truong == moi_truong)
    don = db.execute(q).scalars().all()
    nguon = db.execute(select(DoiTacOta).where(DoiTacOta.bat)).scalars().all()
    return {
        "don": [D.tom_tat(x) for x in don],
        # Nguồn đang bật, kèm môi trường — màn hình đọc môi trường ở đây để biết hiện hay giấu
        # khối sáu con số dán tay. Không để màn tự đoán.
        "ota": [{"id": o.id, "ten": o.ten, "moi_truong": o.moi_truong,
                 "moi_truong_ten": MOI_TRUONG_OTA.get(o.moi_truong, o.moi_truong)}
                for o in nguon if (getattr(o, "san_pham", "khach_san") or "khach_san") == "khach_san"],
        **tham_so(),
    }


def tham_so() -> dict:
    """Mọi bảng mã cho màn hình — để màn không gõ lại bảng của Agoda một lần nữa."""
    return {
        "buoc": BUOC_DON,
        "buoc_vi": BUOC_VI,
        "trang_thai": TRANG_THAI_DON,
        "trang_thai_nguon": list(TRANG_THAI_NGUON),
        "ly_do_huy": LY_DO_HUY,
        "kieu_thanh_toan": KIEU_THANH_TOAN,
        "don_dong": list(DON_DONG),
        "han_ma_tim_giay": D.HAN_MA_TIM_GIAY,
        "han_dat_giay": D.HAN_DAT_GIAY,
        "ngay_chot_huy": D.NGAY_CHOT_HUY,
        "o_dieu_kien": list(O_DIEU_KIEN),
        "so_cua_nguon": {k: TEN_O[k] for k in SO_CUA_NGUON},
    }
# ---------------------------------------------------------------- KS-11 · cửa cho khách
# Chủ tịch chốt 29-10-2026: khách GỬI YÊU CẦU, Điều hành chạy sáu bước.
#
# Khách không tự chạy sáu bước, và lý do không phải là ngại: sáu con số của Agoda chỉ tra được
# từ tài khoản đối tác của Vietourist, còn tiền thì theo Fulfill Assisted «Agoda will directly
# charge your customers» — Vietourist không chạm vào. Nên khách khai NƠI ĐẾN và NGÀY; mọi con
# số của nguồn vẫn vào hệ thống bằng đúng hai cách cũ, không có cách thứ ba.

# Ô khách được khai. Danh sách này là MỘT HÀNG RÀO, không phải một ghi chú: `gui_yeu_cau` chỉ
# đọc đúng những khoá ở đây, nên một trình duyệt bị sửa cũng không nhét được `ma_tim` hay
# `gia_gom_thue` vào đơn.
O_KHACH_KHAI = ("noi_den", "ngay_nhan", "ngay_tra", "so_phong", "nguoi_lon", "tre_em",
                "nguoi_nhan_phong", "lien_he", "yeu_cau_them")

# Tài khoản ở hai trạng thái này không gửi yêu cầu được.
TK_KHONG_GUI = ("khoa", "tu_choi")

GIOI_HAN_DON_KHACH = 50


def trang_thai_khach(don) -> str:
    """Trạng thái bên mình → điều khách nhìn thấy. Khoá lạ thì trả «da_gui», không nổ."""
    return DON_SANG_KHACH.get(getattr(don, "trang_thai", "") or "", "da_gui")


def la_chu_don(don, tk) -> bool:
    """Một câu hỏi, một câu trả lời, và KHÔNG có đường vòng nào qua thẻ tham chiếu.

    Đơn không có chủ (Điều hành tự dựng) thì KHÔNG ai ở cổng ngoài đọc được — trả False, chứ
    không trả True vì «không có ai cấm».
    """
    chu = getattr(don, "tai_khoan_ngoai_id", None)
    if chu is None or tk is None:
        return False
    return int(chu) == int(getattr(tk, "id", 0) or 0)


def thieu_de_gui_yeu_cau(tk, d: dict) -> list[str]:
    """Chưa đủ cái gì thì chưa nhận yêu cầu. Gọi đúng tên ô còn thiếu, đừng nói «dữ liệu sai»."""
    t = []
    if tk is None or getattr(tk, "id", None) is None:
        t.append("chưa đăng nhập cổng")
        return t
    if str(getattr(tk, "trang_thai", "") or "") in TK_KHONG_GUI:
        t.append("tài khoản đang bị khoá hoặc đã bị từ chối")
    if str(getattr(tk, "loai", "") or "") not in CONG_GUI:
        t.append("cổng này chưa mở đặt phòng")
    if not str(d.get("noi_den") or "").strip():
        t.append("chưa ghi nơi đến")
    if not d.get("ngay_nhan") or not d.get("ngay_tra"):
        t.append("chưa có ngày nhận / ngày trả phòng")
    elif str(d["ngay_tra"]) <= str(d["ngay_nhan"]):
        t.append("ngày trả phải sau ngày nhận")
    if int(d.get("so_phong") or 0) < 1:
        t.append("số phòng phải từ 1")
    if int(d.get("nguoi_lon") or 0) < 1:
        t.append("số người lớn phải từ 1")
    if not str(d.get("nguoi_nhan_phong") or "").strip():
        t.append("chưa ghi tên người nhận phòng")
    if not str(d.get("lien_he") or "").strip():
        t.append("chưa ghi số điện thoại hoặc email để Vietourist báo giá")
    return t


def tom_tat_khach(don) -> dict:
    """Những gì khách được thấy — và CHỈ những gì khách được thấy.

    Không có `ma_tim`, `ma_khoi`, `the_chao`, `ma_goi_gia`: đó là mã phiên tra giá của tài
    khoản đối tác Vietourist, đưa ra ngoài là đưa chìa khoá kho giá cho người lạ. Phép thử
    KS-11 đọc chính hàm này và bắt nếu có khoá nào trong số ấy lọt ra.
    """
    k = trang_thai_khach(don)
    return {
        "id": don.id,
        "the_tham_chieu": don.the_tham_chieu,
        "trang_thai": k,
        "trang_thai_ten": TRANG_THAI_KHACH.get(k, k),
        "noi_den": don.noi_den,
        "ngay_nhan": don.ngay_nhan.isoformat() if don.ngay_nhan else None,
        "ngay_tra": don.ngay_tra.isoformat() if don.ngay_tra else None,
        "so_phong": don.so_phong,
        "nguoi_lon": don.nguoi_lon,
        "tre_em": don.tre_em,
        "nguoi_nhan_phong": don.nguoi_nhan_phong,
        "yeu_cau_them": don.yeu_cau_them,
        # Giá chỉ hiện khi ĐÃ có giá. Hiện số 0 lúc chưa tra xong là nói dối khách một con số.
        "gia_gom_thue": float(don.gia_gom_thue or 0) if k in ("co_gia", "da_dat") else None,
        "tien_te": don.tien_te,
        "so_xac_nhan_ks": don.so_xac_nhan_ks or "",
        "gui_luc": don.gui_luc.isoformat() if don.gui_luc else None,
    }


def gui_yeu_cau(db: Session, tk, d: dict, now: datetime | None = None) -> DonKhachSanOta:
    """Khách gửi yêu cầu. Dựng một đơn CHƯA CÓ NGUỒN và chưa có một con số nào của Agoda."""
    thieu = thieu_de_gui_yeu_cau(tk, d)
    if thieu:
        raise LoiOta("Chưa gửi được yêu cầu: " + "; ".join(thieu))

    don = DonKhachSanOta(the_tham_chieu=the_tham_chieu_moi(), ota_id=None,
                         moi_truong="tat", trang_thai="moi", trang_thai_nguon="")
    don.tai_khoan_ngoai_id = int(tk.id)
    don.cong = str(getattr(tk, "loai", "") or "")[:20]
    # CHỈ những khoá trong O_KHACH_KHAI. Đây là chỗ chặn, không phải chỗ tin.
    don.noi_den = str(d.get("noi_den") or "").strip()[:160]
    don.ngay_nhan = d.get("ngay_nhan")
    don.ngay_tra = d.get("ngay_tra")
    don.so_phong = int(d.get("so_phong") or 1)
    don.nguoi_lon = int(d.get("nguoi_lon") or 1)
    don.tre_em = int(d.get("tre_em") or 0)
    don.nguoi_nhan_phong = str(d.get("nguoi_nhan_phong") or "").strip()[:160]
    don.lien_he = str(d.get("lien_he") or "").strip()[:160]
    don.yeu_cau_them = str(d.get("yeu_cau_them") or "")[:2000]
    don.gui_luc = now or datetime.utcnow()
    _dong_dau(don, "cổng:" + str(getattr(tk, "loai", "") or ""), now)
    db.add(don)
    db.flush()
    db.commit()
    return don


def don_cua_toi(db: Session, tk) -> list[dict]:
    """Đơn CỦA CHÍNH tài khoản ấy. Lọc ở câu truy vấn, không lọc ở màn hình."""
    if tk is None or getattr(tk, "id", None) is None:
        return []
    q = (select(DonKhachSanOta)
         .where(DonKhachSanOta.tai_khoan_ngoai_id == int(tk.id))
         .order_by(DonKhachSanOta.id.desc()).limit(GIOI_HAN_DON_KHACH))
    return [tom_tat_khach(x) for x in db.execute(q).scalars().all()]


def mot_don_cua_toi(db: Session, tk, don_id: int) -> dict:
    """Một đơn — và 404 nếu không phải của mình.

    Trả 404 chứ không 403: 403 xác nhận «đơn này có thật», tức là đếm được đơn của người khác.
    """
    don = db.get(DonKhachSanOta, int(don_id or 0))
    if don is None or not la_chu_don(don, tk):
        raise LoiOta("Không thấy đơn này", 404)
    return tom_tat_khach(don)


def tham_so_khach() -> dict:
    """Bảng chữ cho màn của khách — để màn không gõ lại một bảng nào."""
    return {"trang_thai": TRANG_THAI_KHACH, "o_khach_khai": list(O_KHACH_KHAI)}


def hoi_gia_yeu_cau(db: Session, boi: str, don_id: int, d: dict,
                    now: datetime | None = None) -> DonKhachSanOta:
    """Điều hành nhận một YÊU CẦU của khách: gắn nguồn vào và chạy bước 1 TRÊN CHÍNH ĐƠN ẤY.

    Không dựng đơn mới. Dựng đơn mới thì khách theo dõi một đơn, Điều hành chạy một đơn khác,
    và hai cái ấy không bao giờ gặp nhau.
    """
    don = lay_don(db, don_id)
    if don.trang_thai != "moi":
        raise LoiOta("Đơn này đã qua bước hỏi giá — xem nhật ký bước")
    ota = _lay_ota(db, d.get("ota_id"))
    dk = {k: getattr(don, k) for k in O_DIEU_KIEN}
    dk.update({k: v for k, v in (d or {}).items() if k in O_DIEU_KIEN and v is not None})
    thieu = thieu_de_hoi_gia(ota, dk)
    if thieu:
        raise LoiOta("Chưa hỏi giá được: " + "; ".join(thieu))
    moi_truong = getattr(ota, "moi_truong", "tat")
    thieu_so = thieu_so_nguon(moi_truong, d)
    if thieu_so:
        raise LoiOta("Chưa hỏi giá được: " + "; ".join(thieu_so))

    don.ota_id = ota.id
    don.moi_truong = moi_truong
    for k in O_DIEU_KIEN:
        if k in (d or {}) and d[k] is not None:
            setattr(don, k, d[k])
    nhan_so_nguon(don, sinh_so_thu() if moi_truong == "thu" else d, now)
    _dong_dau(don, boi, now)
    ghi_buoc(db, don, "tim", 200, False,
             "yêu cầu của khách · môi trường %s · mã tìm %s" % (moi_truong, don.ma_tim),
             boi, now)
    db.commit()
    return don
