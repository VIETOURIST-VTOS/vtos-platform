"""V11 – tính trạng thái của từng tác vụ tự động, và ghi lần chạy do n8n báo về.

Toàn bộ giá trị của phân hệ này nằm ở một hàm: `trang_thai()`. Phần còn lại chỉ là ghi chép.

Vì sao: sổ lần chạy trả lời được "lần trước chạy ra sao", nhưng câu hỏi người ta thật sự cần trả lời
lúc 8 giờ sáng là "có cái gì lẽ ra phải chạy mà chưa chạy không". Câu thứ hai không nằm trong bất kỳ
dòng nào của sổ – nó nằm ở chỗ TRỐNG giữa hai dòng. Hàm dưới đây đọc chỗ trống đó.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.tu_dong import TacVuTuDong, LanChayTacVu, TRANG_THAI_LAN_CHAY, HE_THONG
from app.services import ky_thuat as KT

# Cho trễ một chút trước khi kêu: một luồng hẹn 06:00 chạy xong lúc 06:04 hôm nay và 06:11 hôm sau là
# chuyện bình thường của mọi bộ hẹn giờ. Không có khoảng dung sai thì màn hình kêu mỗi sáng, và một
# màn hình kêu mỗi sáng là một màn hình không ai đọc nữa.
DUNG_SAI = 1.25          # quá 125% hạn khai báo mới coi là im
DUNG_SAI_TOI_THIEU = timedelta(minutes=10)

TRANG_THAI_TAC_VU = {
    "chua_chay": "Chưa chạy lần nào",
    "binh_thuong": "Bình thường",
    "that_bai": "Lần gần nhất thất bại",
    "im_lang": "Quá hạn – không thấy chạy",
    "tat": "Đã tắt",
}


def _lan_gan_nhat(db: Session, tac_vu_id: int) -> LanChayTacVu | None:
    return db.execute(select(LanChayTacVu).where(LanChayTacVu.tac_vu_id == tac_vu_id)
                      .order_by(LanChayTacVu.bat_dau.desc()).limit(1)).scalars().first()


def _lan_thanh_cong_gan_nhat(db: Session, tac_vu_id: int) -> LanChayTacVu | None:
    return db.execute(select(LanChayTacVu).where(LanChayTacVu.tac_vu_id == tac_vu_id,
                                                 LanChayTacVu.trang_thai == "thanh_cong")
                      .order_by(LanChayTacVu.bat_dau.desc()).limit(1)).scalars().first()


def han(t: TacVuTuDong) -> timedelta | None:
    """Khoảng thời gian tối đa được phép im. None = tác vụ không canh im lặng."""
    if not t.han_toi_da_phut:
        return None
    return max(timedelta(minutes=t.han_toi_da_phut) * DUNG_SAI, DUNG_SAI_TOI_THIEU)


def trang_thai(db: Session, t: TacVuTuDong, bay_gio: datetime | None = None) -> dict:
    """Trạng thái hiện tại của một tác vụ – ĐỌC CHỖ TRỐNG, không chỉ đọc dòng cuối.

    Thứ tự xét có chủ ý: TẮT trước tiên (tắt có chủ ý thì im lặng là đúng, không phải lỗi), rồi mới
    tới im lặng, rồi mới tới thất bại. Xét thất bại trước im lặng là sai: một tác vụ thất bại lúc 6h
    sáng rồi im luôn ba ngày sẽ mãi hiện 'lần gần nhất thất bại' – đúng chữ nhưng che mất chuyện lớn
    hơn nhiều là nó đã ngừng chạy.
    """
    now = bay_gio or datetime.now()
    cuoi = _lan_gan_nhat(db, t.id)
    tc = _lan_thanh_cong_gan_nhat(db, t.id)
    h = han(t)

    if not t.bat:
        ma = "tat"
        vi_sao = f"Đã tắt{': ' + t.ly_do_tat if t.ly_do_tat else ' – KHÔNG ghi lý do'}"
    elif cuoi is None:
        ma = "chua_chay"
        vi_sao = ("Đã khai báo nhưng chưa nhận được lần chạy nào. Hoặc luồng chưa bật, hoặc nó chạy "
                  "mà chưa báo về – hai cái đó nhìn từ đây giống hệt nhau.")
    elif h is not None and (now - (tc.bat_dau if tc else cuoi.bat_dau)) > h:
        moc = tc.bat_dau if tc else cuoi.bat_dau
        so_gio = (now - moc).total_seconds() / 3600
        ma = "im_lang"
        vi_sao = (f"Lần chạy thành công gần nhất cách đây {so_gio:.1f} giờ, quá hạn khai báo "
                  f"{t.han_toi_da_phut} phút. Tác vụ ngừng chạy KHÔNG sinh ra dòng lỗi nào – "
                  "chỗ này là chỗ duy nhất nhìn thấy nó.")
    elif cuoi.trang_thai == "that_bai":
        ma = "that_bai"
        vi_sao = cuoi.thong_bao or "Lần chạy gần nhất báo thất bại."
    elif cuoi.trang_thai == "mot_phan":
        ma = "that_bai"
        vi_sao = "Lần gần nhất chỉ xong một phần: " + (cuoi.thong_bao or "không ghi rõ phần nào thiếu.")
    else:
        ma = "binh_thuong"
        vi_sao = ""

    return {"ma": ma, "ten": TRANG_THAI_TAC_VU[ma], "vi_sao": vi_sao,
            "canh_im_lang": h is not None,
            "lan_cuoi": None if cuoi is None else _lan_ra(cuoi),
            "thanh_cong_gan_nhat": None if tc is None else tc.bat_dau}


def _lan_ra(l: LanChayTacVu) -> dict:
    return {"id": l.id, "ma_lan": l.ma_lan, "trang_thai": l.trang_thai,
            "trang_thai_ten": TRANG_THAI_LAN_CHAY.get(l.trang_thai, l.trang_thai),
            "bat_dau": l.bat_dau, "ket_thuc": l.ket_thuc, "giay": l.giay,
            "so_ban_ghi": l.so_ban_ghi, "thong_bao": l.thong_bao, "boi": l.boi}


def ra(db: Session, t: TacVuTuDong, bay_gio: datetime | None = None) -> dict:
    return {"id": t.id, "ma": t.ma, "ten": t.ten, "mo_ta": t.mo_ta,
            "he_thong": t.he_thong, "he_thong_ten": HE_THONG.get(t.he_thong, t.he_thong),
            "lich_doc": t.lich_doc, "lich_cron": t.lich_cron, "phong_ban": t.phong_ban,
            "nguoi_phu_trach": t.nguoi_phu_trach, "han_toi_da_phut": t.han_toi_da_phut,
            "quan_trong": t.quan_trong, "bat": t.bat, "ly_do_tat": t.ly_do_tat,
            "tao_boi": t.tao_boi, "tao_luc": t.tao_luc,
            **{"trang_thai": trang_thai(db, t, bay_gio)}}


def bang(db: Session, bay_gio: datetime | None = None) -> dict:
    ds = db.execute(select(TacVuTuDong).order_by(TacVuTuDong.bat.desc(), TacVuTuDong.ma)).scalars().all()
    rows = [ra(db, t, bay_gio) for t in ds]
    dem = {k: 0 for k in TRANG_THAI_TAC_VU}
    for r in rows:
        dem[r["trang_thai"]["ma"]] += 1
    return {"tac_vu": rows, "dem": dem, "he_thong": HE_THONG,
            "trang_thai_tac_vu": TRANG_THAI_TAC_VU, "trang_thai_lan_chay": TRANG_THAI_LAN_CHAY,
            "chu_thich": [
                "Tác vụ do NGƯỜI khai, không phải máy tự sinh khi thấy lần chạy đầu tiên: luồng bị "
                "xóa bên n8n thì tác vụ vẫn ở lại đây và chuyển sang quá hạn, thay vì biến mất cùng "
                "lịch sử của nó đúng lúc cần nhìn nhất.",
                "Hạn tối đa để 0 nghĩa là KHÔNG canh im lặng – dùng cho tác vụ chạy theo sự kiện. "
                "Tác vụ chạy theo lịch mà để 0 là một lỗ hổng: nó ngừng chạy sẽ không ai biết.",
                "Lần chạy chỉ do hệ thống bên ngoài báo về; VTOS không tự sinh dòng nào ở sổ này.",
            ]}


def ghi_lan_chay(db: Session, ma_tac_vu: str, ma_lan: str, trang_thai_moi: str, *,
                 bat_dau: datetime | None = None, ket_thuc: datetime | None = None,
                 so_ban_ghi: int | None = None, thong_bao: str = "", chi_tiet: dict | None = None,
                 boi: str = "n8n") -> tuple[LanChayTacVu, bool, dict | None]:
    """Nhận một lần chạy. Trả (bản ghi, có phải lần đầu không, sự kiện cần ghi SAU KHI commit).

    Cùng `ma_lan` gửi lại thì CẬP NHẬT chứ không tạo dòng thứ hai – n8n thử lại khi mạng chập, và
    một lần chạy đếm thành hai làm hỏng đúng con số mà màn hình này sinh ra để cho người ta tin.

    VÌ SAO SỰ KIỆN KỸ THUẬT KHÔNG GHI Ở ĐÂY MÀ TRẢ RA CHO NGƯỜI GỌI GHI SAU:

      Hai lý do, và lý do thứ hai mới là lý do thật.

      1. Sổ sự kiện ghi bằng một phiên riêng (nó phải sống sót cả khi phiên đang chạy đã hỏng). Trên
         SQLite – môi trường máy lập trình – phiên riêng đó đâm vào chính giao dịch đang mở ở đây và
         bị khóa; KT nuốt lỗi nên KHÔNG có gì được ghi và cũng không có gì báo ra. Bộ kiểm T4 bắt
         được đúng chỗ này.
      2. Quan trọng hơn: một sự kiện báo "vừa ghi nhận một lần chạy hỏng" không được phép nhìn thấy
         TRƯỚC bản ghi mà nó nói tới. Ghi trong giao dịch chưa commit là mở ra đúng khe hở đó – và
         nếu giao dịch sau đó thất bại thì còn tệ hơn: robot Kiểm soát báo một lần chạy không tồn tại.
    """
    if trang_thai_moi not in TRANG_THAI_LAN_CHAY:
        raise ValueError(f"Trạng thái không hợp lệ: {trang_thai_moi}")
    t = db.execute(select(TacVuTuDong).where(TacVuTuDong.ma == ma_tac_vu)).scalars().first()
    if t is None:
        # KHÔNG tự tạo tác vụ. Xem chú thích đầu app/models/tu_dong.py: máy tự tạo thì bảng khai báo
        # thành bản sao của sổ lần chạy, và mất luôn khả năng phát hiện im lặng.
        raise ValueError(f"Chưa khai báo tác vụ '{ma_tac_vu}' trong VTOS. "
                         "Khai ở màn hình Lịch tự động hóa trước, rồi luồng mới báo về được.")

    cu = db.execute(select(LanChayTacVu).where(LanChayTacVu.ma_lan == ma_lan)).scalars().first()
    bd = bat_dau or datetime.now()
    l = cu or LanChayTacVu(tac_vu_id=t.id, ma_lan=ma_lan[:80], bat_dau=bd)
    l.trang_thai = trang_thai_moi
    if bat_dau: l.bat_dau = bat_dau
    l.ket_thuc = ket_thuc
    l.giay = round((ket_thuc - l.bat_dau).total_seconds(), 3) if ket_thuc else 0
    l.so_ban_ghi = so_ban_ghi          # None giữ nguyên là None: "không biết" khác "không có gì"
    l.thong_bao = (thong_bao or "")[:4000]
    l.chi_tiet = chi_tiet
    l.boi = boi[:50]
    if cu is None:
        db.add(l)
    db.flush()

    su_kien = None
    if trang_thai_moi in ("that_bai", "mot_phan"):
        # Nối vào K6 đúng như lệnh V11 yêu cầu: tác vụ thất bại phải sinh sự kiện kỹ thuật để robot
        # Kiểm soát đọc, chứ không nằm im trong một bảng chỉ người mở màn hình mới thấy.
        su_kien = {"muc": "do" if t.quan_trong else "vang",
                   "duong_dan": f"tac-vu/{t.ma}", "vai_tro": boi,
                   "thong_bao": f"{t.ten}: {thong_bao or trang_thai_moi}",
                   "chi_tiet": {"ma_tac_vu": t.ma, "ma_lan": ma_lan, "trang_thai": trang_thai_moi}}
    return l, cu is None, su_kien


def day_su_kien(su_kien: dict | None) -> None:
    """Gọi SAU khi commit. Xem chú thích trong ghi_lan_chay."""
    if su_kien:
        KT.ghi_moi_phien("tac_vu_nen", **su_kien)


def im_lang(db: Session, bay_gio: datetime | None = None) -> list[dict]:
    """Các tác vụ đang quá hạn. Dùng cho vòng quét của robot Kiểm soát và cho báo cáo sáng."""
    ra_ds = []
    for t in db.execute(select(TacVuTuDong).where(TacVuTuDong.bat == True)).scalars():  # noqa: E712
        tt = trang_thai(db, t, bay_gio)
        if tt["ma"] == "im_lang":
            ra_ds.append({"ma": t.ma, "ten": t.ten, "quan_trong": t.quan_trong,
                          "han_toi_da_phut": t.han_toi_da_phut,
                          "thanh_cong_gan_nhat": tt["thanh_cong_gan_nhat"], "vi_sao": tt["vi_sao"]})
    return ra_ds


def quet_im_lang(db: Session, bay_gio: datetime | None = None) -> int:
    """Đẩy các tác vụ đang im vào sổ sự kiện kỹ thuật. Gọi từ vòng quét, không gọi khi mở màn hình.

    Ghi ở đây chứ không ghi trong `trang_thai()`: `trang_thai()` chạy mỗi lần ai đó mở màn hình, và
    một hàm ĐỌC mà lại GHI thì mở màn hình mười lần sẽ đếm thành mười sự kiện.
    """
    ds = im_lang(db, bay_gio)
    for x in ds:
        KT.ghi_moi_phien("tac_vu_nen", muc="do" if x["quan_trong"] else "vang",
                         duong_dan=f"tac-vu/{x['ma']}", vai_tro="he_thong",
                         thong_bao=f"{x['ten']}: quá hạn, không thấy chạy",
                         chi_tiet={"ma_tac_vu": x["ma"],
                                   "han_toi_da_phut": x["han_toi_da_phut"]})
    return len(ds)
