"""Lịch chạy bên TRONG VTOS – các việc theo giờ mà vòng lặp đếm phút không làm đúng được.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY (09/9/2026)
────────────────────────────────────────────────────────────────────────────────

Tài liệu kiến trúc ghi "lịch chạy nằm ở n8n". Mở n8n ra kiểm ngày 09/9: workspace TRỐNG, 0 lần
chạy, chưa từng có luồng nào. Bốn việc lẽ ra chạy theo lịch thật ra chưa bao giờ chạy:

    · kéo bù giao dịch SePay (webhook trượt giao dịch nào thì không có ai bù)
    · báo cáo ngày / tuần / tháng
    · gửi các tin Zalo đang nằm chờ trong hàng đợi
    · quét tác vụ im lặng (V11, vừa viết)

Chủ tịch quyết đưa vào trong VTOS. Vòng lặp robot sẵn có (app/main.robot_loop) chạy mỗi phút và
đếm số phút từ lúc máy chủ khởi động – đủ cho việc "mỗi 10 phút", nhưng KHÔNG đủ cho việc theo giờ:

    Đếm phút từ lúc khởi động thì mỗi lần deploy là bộ đếm về 0. Máy chủ khởi động lại lúc 20:29 thì
    báo cáo 20:30 hôm đó không bao giờ chạy, và không ai biết – vì việc không chạy thì không sinh ra
    dòng nào. Đúng cái bệnh mà V11 sinh ra để chữa.

────────────────────────────────────────────────────────────────────────────────
CÁCH LÀM: KHÓA THEO KỲ, KHÔNG ĐẾM PHÚT
────────────────────────────────────────────────────────────────────────────────

Mỗi lần chạy mang một MÃ KỲ suy từ đồng hồ tường, không suy từ bộ đếm:

    vtos_bao_cao_ngay:2026-09-09        (mỗi ngày một mã)
    vtos_sepay_bu:2026-09-09T14:30      (mỗi 30 phút một mã)

Mã đó chính là `ma_lan` trong sổ lần chạy của V11, mà cột đó DUY NHẤT. Nên hai điều tự đúng, không
cần viết thêm dòng nào để canh:

    · Chạy hai lần trong cùng một kỳ là không thể – kể cả khi có hai tiến trình máy chủ cùng chạy.
    · Máy chủ tắt lúc 20:30 và lên lại lúc 21:10 thì báo cáo VẪN CHẠY, vì mã kỳ hôm đó chưa dùng.
      Đây là chỗ khác nhau lớn nhất với đếm phút: việc bị lỡ được làm bù, không bị bỏ luôn.

Và các việc trong này tự khai vào bảng tác vụ V11, nên chúng hiện trên màn hình Lịch tự động hóa
y như việc chạy ở n8n – cùng một chỗ nhìn, cùng một cách phát hiện im lặng.

    Chỗ này KHÔNG mâu thuẫn với điều luật "tác vụ do người khai, máy không tự sinh". Điều luật đó
    nói về tác vụ chạy ở hệ thống NGOÀI: máy tự sinh thì luồng bị xóa bên ngoài sẽ biến mất khỏi
    màn hình cùng lịch sử của nó. Với việc chạy bên TRONG, mã nguồn này chính là bản khai – nó
    không thể biến mất mà không ai sửa mã. Một chỗ khai, không phải hai.
"""
from datetime import datetime, timedelta, date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.tu_dong import TacVuTuDong
from app.services import tu_dong as TD


# ────────────────────────────── CÁC VIỆC ──────────────────────────────
def _sepay_bu(db: Session) -> tuple[int | None, str]:
    """Kéo lại giao dịch 3 ngày gần nhất để bù giao dịch webhook trượt."""
    from app.core.config import settings
    from app.services import sepay as SP
    if not settings.SEPAY_API_TOKEN:
        return None, "Chưa đặt SEPAY_API_TOKEN – không kéo được, webhook vẫn chạy bình thường"
    hom_nay = date.today()
    kq = SP.pull(db, hom_nay - timedelta(days=3), hom_nay, settings.SEPAY_ACCOUNT_NUMBER)
    n = kq.get("new") if isinstance(kq, dict) else None
    return n, (f"Kéo bù 3 ngày: đọc {kq.get('fetched')} giao dịch, thêm mới {kq.get('new')}, "
               f"khớp tự động {kq.get('matched')}, chờ kế toán {kq.get('pending')}")


def _bao_cao(kind: str):
    """Chụp bản lưu của báo cáo theo lịch – TỪ CHÍNH cấu trúc chỉ tiêu mà màn hình đang đọc.

    Trước 10/9/2026 hàm này gọi `dashboard.run_report` – bản của robot R7, một bài viết dựng từ phép
    tính riêng. Nghĩa là màn hình và bản lưu là hai phép tính khác nhau cho cùng một câu hỏi: sớm
    muộn ra hai con số, và lúc lệch thì không ai biết bản nào đúng.

    Bản R7 VẪN được lập, và cố ý giữ lại: nó có phần nhận xét bằng lời mà bảng chỉ tiêu không có.
    Nhưng nó không còn là bản lưu duy nhất, và nó không còn là chỗ ai đó đi tra con số.

    R7 hỏng thì KHÔNG được kéo theo bản lưu chỉ tiêu – nó gọi ra ngoài (mô hình ngôn ngữ) nên hỏng
    là chuyện thường, còn bản lưu chỉ tiêu thì đọc thẳng cơ sở dữ liệu. Buộc hai thứ vào nhau là lấy
    cái hay hỏng làm điều kiện cho cái không hỏng.
    """
    def chay(db: Session) -> tuple[int | None, str]:
        from app.services import bao_cao_phong as BP
        kq = BP.luu(db, kind)
        loi_r7 = ""
        try:
            from app.services import dashboard as DB_
            DB_.run_report(db, kind)
        except Exception as e:      # noqa
            loi_r7 = f" · bản nhận xét R7 lỗi: {type(e).__name__}"
        hong = f" · KHÔNG lưu được: {'; '.join(kq['hong'])}" if kq["hong"] else ""
        return len(kq["da_luu"]), (f"Lưu báo cáo {kind} kỳ {kq['ky']}: "
                                   f"{len(kq['da_luu'])} phạm vi{hong}{loi_r7}")
    return chay


def _zalo_gui_cho(db: Session) -> tuple[int | None, str]:
    """Tin Zalo nằm trong hàng đợi thì phải có ai đó đẩy đi.

    Trước 09/9 KHÔNG ai gọi hàm này ngoài một nút bấm tay và một đường robot chưa ai gọi – tức là
    tin xếp hàng vô thời hạn mà màn hình vẫn báo 'chờ gửi', trông y như đang chờ tới lượt.
    """
    from app.services import zalo as Z
    kq = Z.send_pending(db)
    return kq.get("sent", 0), f"Đã gửi {kq.get('sent', 0)} tin đang chờ"


def _quet_im_lang(db: Session) -> tuple[int | None, str]:
    n = TD.quet_im_lang(db)
    return n, f"{n} tác vụ đang quá hạn" if n else "Không có tác vụ nào quá hạn"


# ────────────────────────────── BẢN KHAI ──────────────────────────────
# `kieu` quyết định mã kỳ:
#   ("moi_phut", n)      – mốc tròn n phút trong ngày
#   ("hang_ngay", "HH:MM")
#   ("hang_tuan", thu, "HH:MM")   thu: 0=Thứ Hai … 5=Thứ Bảy, 6=Chủ nhật
#   ("hang_thang", ngay, "HH:MM")
LICH = [
    {"ma": "vtos_sepay_bu", "ten": "Kéo bù giao dịch SePay",
     "mo_ta": "Kéo lại 3 ngày gần nhất từ SePay để bù giao dịch webhook trượt. Không thay webhook – "
              "webhook vẫn là đường chính, đây là lưới hứng.",
     "kieu": ("moi_phut", 30), "han_toi_da_phut": 90, "quan_trong": True,
     "phong_ban": "ketoan", "chay": _sepay_bu},

    {"ma": "vtos_zalo_gui_cho", "ten": "Gửi tin Zalo đang chờ",
     "mo_ta": "Đẩy các tin trong hàng đợi đi. Không có việc này thì tin xếp hàng vô thời hạn mà màn "
              "hình vẫn báo 'chờ gửi'.",
     "kieu": ("moi_phut", 5), "han_toi_da_phut": 20, "quan_trong": True,
     "phong_ban": "kd_le", "chay": _zalo_gui_cho},

    {"ma": "vtos_quet_im_lang", "ten": "Quét tác vụ tự động đã im lặng",
     "mo_ta": "So lần chạy thành công gần nhất với hạn khai báo; tác vụ quá hạn thì ghi vào sổ sự "
              "kiện kỹ thuật cho robot Kiểm soát.",
     "kieu": ("moi_phut", 10), "han_toi_da_phut": 40, "quan_trong": False,
     "phong_ban": "cntt", "chay": _quet_im_lang},

    {"ma": "vtos_bao_cao_ngay", "ten": "Báo cáo ngày",
     "mo_ta": "Lập báo cáo ngày, lưu vào kho báo cáo tự động.",
     "kieu": ("hang_ngay", "20:30"), "han_toi_da_phut": 1560, "quan_trong": False,
     "phong_ban": "ban_tgd", "chay": _bao_cao("ngay")},

    {"ma": "vtos_bao_cao_tuan", "ten": "Báo cáo tuần",
     "mo_ta": "Lập báo cáo tuần vào chiều thứ Bảy.",
     "kieu": ("hang_tuan", 5, "17:00"), "han_toi_da_phut": 10_500, "quan_trong": False,
     "phong_ban": "ban_tgd", "chay": _bao_cao("tuan")},

    {"ma": "vtos_bao_cao_thang", "ten": "Báo cáo tháng",
     "mo_ta": "Lập báo cáo tháng vào ngày 10.",
     "kieu": ("hang_thang", 10, "09:00"), "han_toi_da_phut": 46_000, "quan_trong": False,
     "phong_ban": "ban_tgd", "chay": _bao_cao("thang")},
]
THEO_MA = {x["ma"]: x for x in LICH}


# ────────────────────────────── MÃ KỲ ──────────────────────────────
def ma_ky(dinh_nghia: dict, now: datetime) -> str | None:
    """Mã kỳ hiện tại, hoặc None nếu chưa tới giờ của kỳ này.

    Trả None nghĩa là 'chưa tới lượt', KHÁC với 'tới lượt nhưng đã chạy rồi' – cái thứ hai do khóa
    duy nhất trên ma_lan chặn, không phải hàm này.
    """
    kieu = dinh_nghia["kieu"]
    if kieu[0] == "moi_phut":
        n = kieu[1]
        moc = now.replace(minute=(now.minute // n) * n, second=0, microsecond=0)
        return f"{dinh_nghia['ma']}:{moc:%Y-%m-%dT%H:%M}"
    if kieu[0] == "hang_ngay":
        gio, phut = (int(x) for x in kieu[1].split(":"))
        if (now.hour, now.minute) < (gio, phut):
            return None
        return f"{dinh_nghia['ma']}:{now:%Y-%m-%d}"
    if kieu[0] == "hang_tuan":
        thu, hm = kieu[1], kieu[2]
        gio, phut = (int(x) for x in hm.split(":"))
        # Chỉ chạy ĐÚNG ngày trong tuần đó. Không làm bù sang ngày hôm sau: một báo cáo tuần gửi
        # vào Chủ nhật thì số liệu đã khác, và người nhận đọc nó như báo cáo của tuần mới.
        if now.weekday() != thu or (now.hour, now.minute) < (gio, phut):
            return None
        return f"{dinh_nghia['ma']}:{now:%G-W%V}"
    if kieu[0] == "hang_thang":
        ngay, hm = kieu[1], kieu[2]
        gio, phut = (int(x) for x in hm.split(":"))
        if now.day != ngay or (now.hour, now.minute) < (gio, phut):
            return None
        return f"{dinh_nghia['ma']}:{now:%Y-%m}"
    return None


# ────────────────────────────── KHAI BÁO ──────────────────────────────
def dam_bao_khai_bao(db: Session) -> int:
    """Khai các việc trong bản LICH vào bảng tác vụ V11. Đã có mã nào thì CẬP NHẬT phần mô tả và
    hạn, KHÔNG đụng vào cờ bật/tắt: tắt một việc là quyết định của người, mã nguồn không bật lại hộ.
    """
    them = 0
    for d in LICH:
        t = db.execute(select(TacVuTuDong).where(TacVuTuDong.ma == d["ma"])).scalars().first()
        if t is None:
            t = TacVuTuDong(ma=d["ma"], bat=True, tao_boi="he_thong"); db.add(t); them += 1
        t.ten = d["ten"]; t.mo_ta = d["mo_ta"]
        t.he_thong = "vtos"; t.lich_doc = mo_ta_lich(d)
        t.phong_ban = d.get("phong_ban", "")
        t.han_toi_da_phut = d["han_toi_da_phut"]; t.quan_trong = d["quan_trong"]
        t.sua_luc = datetime.now()
    db.commit()
    return them


def mo_ta_lich(d: dict) -> str:
    k = d["kieu"]
    if k[0] == "moi_phut": return f"mỗi {k[1]} phút"
    if k[0] == "hang_ngay": return f"mỗi ngày {k[1]}"
    if k[0] == "hang_tuan":
        ten = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"][k[1]]
        return f"{ten} hằng tuần {k[2]}"
    if k[0] == "hang_thang": return f"ngày {k[1]} hằng tháng {k[2]}"
    return ""


# ────────────────────────────── CHẠY ──────────────────────────────
def den_luot(db: Session, now: datetime | None = None) -> int:
    """Chạy những việc tới lượt. Gọi mỗi phút từ vòng lặp robot.

    Một việc hỏng KHÔNG được làm chết các việc còn lại: bắt lỗi từng việc, ghi lần chạy thất bại
    (từ đó sinh sự kiện kỹ thuật cho robot Kiểm soát), rồi đi tiếp.
    """
    now = now or datetime.now()
    da_chay = 0
    for d in LICH:
        ma_lan = ma_ky(d, now)
        if not ma_lan:
            continue
        t = db.execute(select(TacVuTuDong).where(TacVuTuDong.ma == d["ma"])).scalars().first()
        if t is None or not t.bat:
            continue
        # Kỳ này đã chạy chưa – hỏi bằng khóa duy nhất, không giữ trạng thái trong bộ nhớ tiến trình.
        from app.models.tu_dong import LanChayTacVu
        if db.execute(select(LanChayTacVu.id)
                      .where(LanChayTacVu.ma_lan == ma_lan)).scalars().first():
            continue

        bat_dau = datetime.now()
        # Đặt chỗ TRƯỚC khi chạy: hai tiến trình cùng tới lượt thì tiến trình thứ hai đâm vào khóa
        # duy nhất và bỏ qua, thay vì cả hai cùng chạy rồi mới phát hiện.
        try:
            TD.ghi_lan_chay(db, d["ma"], ma_lan, "dang_chay", bat_dau=bat_dau, boi="vtos")
            db.commit()
        except Exception:      # noqa – đụng khóa duy nhất: tiến trình khác đã nhận việc này
            db.rollback()
            continue

        try:
            so, thong_bao = d["chay"](db)
            _, _, sk = TD.ghi_lan_chay(db, d["ma"], ma_lan, "thanh_cong", bat_dau=bat_dau,
                                       ket_thuc=datetime.now(), so_ban_ghi=so,
                                       thong_bao=thong_bao, boi="vtos")
            db.commit()
            da_chay += 1
        except Exception as e:      # noqa
            db.rollback()
            _, _, sk = TD.ghi_lan_chay(db, d["ma"], ma_lan, "that_bai", bat_dau=bat_dau,
                                       ket_thuc=datetime.now(),
                                       thong_bao=f"{type(e).__name__}: {str(e)[:500]}", boi="vtos")
            db.commit()
        TD.day_su_kien(sk)          # ghi SAU commit – xem chú thích trong tu_dong.ghi_lan_chay
    return da_chay
