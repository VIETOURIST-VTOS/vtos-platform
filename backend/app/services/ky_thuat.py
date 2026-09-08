"""K6 – ghi và đọc SỰ KIỆN KỸ THUẬT. Chỗ robot Kiểm soát nhìn thấy sức khỏe của chính máy chủ.

Trước tệp này robot giám sát được số liệu của các phòng ban nhưng mù hoàn toàn với máy chủ: ngày
07/9/2026 endpoint /meta trả 500 cho mọi vai trò trên hệ thống thật, và thứ tìm ra nó là bộ quét vai
trò chứ không phải bộ theo dõi lỗi. Tức là tìm ra do may.

Hai điều tệp này phải giữ bằng mọi giá:
  1. GHI KHÔNG ĐƯỢC LÀM HỎNG YÊU CẦU. Mọi lỗi khi ghi đều bị nuốt. Một bộ theo dõi lỗi mà tự nó làm
     sập yêu cầu của người dùng thì tệ hơn là không có.
  2. KHÔNG GHI DỮ LIỆU NGHIỆP VỤ. Bảng này có quyền xem rộng hơn nhiều bảng nó theo dõi, nên không
     bao giờ chứa thân yêu cầu, tham số truy vấn hay nội dung bản ghi – chỉ đường dẫn, mã lỗi và
     phần cuối của dấu vết.
"""
import re
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.ky_thuat import SuKienKyThuat, LOAI_SU_KIEN, MUC_SU_KIEN

# Ngưỡng "chậm bất thường", mili giây. Giá trị này được vòng lặp robot nạp lại từ tham số chính sách
# mỗi phút; giữ ở biến mô-đun để lớp giữa KHÔNG phải mở một phiên cơ sở dữ liệu cho mỗi yêu cầu chỉ
# để đọc một con số.
NGUONG_CHAM_MS = 5000
# Đường dẫn không theo dõi độ chậm: bản thân chúng vốn chậm hoặc do người dùng chủ động chờ.
BO_QUA_CHAM = ("/api/v1/nap-du-lieu", "/api/v1/import", "/api/v1/vietrip/sync", "/api/v1/robot",
               "/api/v1/kiem-soat/quet", "/api/v1/kiem-soat/cham-diem", "/docs", "/openapi.json")
# Số đứng riêng trong đường dẫn (mã bản ghi) gom về {id}: không gom thì mỗi booking một dòng lỗi.
_SO = re.compile(r"/\d+(?=/|$)")


def gom_duong_dan(p: str) -> str:
    return _SO.sub("/{id}", p or "")


def _ma(loai: str, duong_dan: str, thong_bao: str) -> str:
    return f"{loai}#{gom_duong_dan(duong_dan)}#{(thong_bao or '')[:60]}"[:200]


def ghi(db: Session, loai: str, *, muc: str = "vang", duong_dan: str = "", phuong_thuc: str = "",
        ma_trang_thai: int = 0, mili_giay: int = 0, vai_tro: str = "", thong_bao: str = "",
        dau_vet: str = "", chi_tiet: dict | None = None) -> None:
    """Ghi một sự kiện, gom theo mã ổn định. Nuốt mọi lỗi – xem điều 1 ở đầu tệp."""
    try:
        if loai not in LOAI_SU_KIEN: return
        ma = _ma(loai, duong_dan, thong_bao)
        now = datetime.now()
        r = db.execute(select(SuKienKyThuat).where(SuKienKyThuat.ma == ma)).scalars().first()
        if r is None:
            db.add(SuKienKyThuat(ma=ma, loai=loai, muc=muc, duong_dan=gom_duong_dan(duong_dan),
                                 phuong_thuc=phuong_thuc, ma_trang_thai=ma_trang_thai,
                                 mili_giay=mili_giay, vai_tro=vai_tro, thong_bao=(thong_bao or "")[:2000],
                                 dau_vet=(dau_vet or "")[-2000:], chi_tiet=chi_tiet,
                                 lan_dau=now, lan_cuoi=now, so_lan=1, da_bao=False))
        else:
            r.so_lan += 1; r.lan_cuoi = now
            r.mili_giay = max(r.mili_giay or 0, mili_giay or 0)   # giữ lần chậm nhất, không phải lần cuối
            if ma_trang_thai: r.ma_trang_thai = ma_trang_thai
            if dau_vet: r.dau_vet = dau_vet[-2000:]
            # Tái phát sau khi robot đã báo thì phải được báo lại: một lỗi đã sửa mà quay lại là một
            # tin khác với lần đầu.
            r.da_bao = False
        db.commit()
    except Exception:      # noqa – ghi nhật ký không bao giờ được làm hỏng việc đang chạy
        try: db.rollback()
        except Exception: pass


def ghi_moi_phien(loai: str, **kw) -> None:
    """Ghi bằng một phiên cơ sở dữ liệu riêng – dùng ở lớp giữa, nơi phiên của yêu cầu có thể đã hỏng
    vì chính ngoại lệ mà ta đang ghi lại."""
    from app.db.session import SessionLocal
    db = None
    try:
        db = SessionLocal(); ghi(db, loai, **kw)
    except Exception:      # noqa
        pass
    finally:
        if db is not None:
            try: db.close()
            except Exception: pass


def nap_nguong(db: Session) -> int:
    """Đọc lại ngưỡng chậm từ tham số chính sách. Gọi từ vòng lặp robot, không gọi từ lớp giữa."""
    global NGUONG_CHAM_MS
    try:
        from app.services import rules as R
        v = int(R.get_param(db, "ky_thuat_cham_ms") or 0)
        if v > 0: NGUONG_CHAM_MS = v
    except Exception:      # noqa
        pass
    return NGUONG_CHAM_MS


def ghi_khoi_dong(db: Session) -> None:
    """Một dòng mỗi lần máy chủ lên, kèm trạng thái mạch nâng cấp.

    Lệnh nâng cấp chạy trong lệnh khởi động của container chứ không trong tiến trình này, nên máy chủ
    không đọc được kết quả của nó. Thứ ghi được – và cũng là thứ đã ba lần làm container không lên –
    là mạch nâng cấp có mấy đầu.
    """
    try:
        from app.services.ks_robot import _mach_migration
        loi = _mach_migration()
        ghi(db, "khoi_dong", muc="do" if loi else "xanh", duong_dan="/",
            thong_bao=("Máy chủ khởi động NHƯNG mạch nâng cấp có nhiều hơn một đầu"
                       if loi else "Máy chủ khởi động, mạch nâng cấp một đầu"),
            chi_tiet={"luc": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "nhieu_dau": bool(loi)})
    except Exception:      # noqa
        pass


# ============================== BỘ KIỂM CHO VÒNG QUÉT ==============================
NGAY_NHIN_LAI = 7


def _su_kien_ky_thuat(db: Session) -> list[dict]:
    """Đưa sự kiện kỹ thuật chưa báo vào danh sách phát hiện của robot.

    Chỉ nhìn lại `NGAY_NHIN_LAI` ngày: một lỗi 5xx của tháng trước đã sửa xong thì không nên còn nằm
    trong bảng việc hôm nay.
    """
    tu = datetime.now() - timedelta(days=NGAY_NHIN_LAI)
    ds = list(db.execute(select(SuKienKyThuat).where(SuKienKyThuat.da_bao == False,   # noqa: E712
                                                     SuKienKyThuat.lan_cuoi >= tu)).scalars())
    if not ds: return []
    ra = []
    loi = [r for r in ds if r.loai == "loi_5xx"]
    if loi:
        tong = sum(r.so_lan for r in loi)
        ra.append({"ma": "may_chu_loi#5xx", "loai": "may_chu_loi", "muc": "do",
                   "phong_ban": "Công nghệ thông tin", "doi_tuong": "may_chu",
                   "tom_tat": f"{len(loi)} đường dẫn trả lỗi máy chủ trong {NGAY_NHIN_LAI} ngày gần đây "
                              f"({tong} lượt). Đường dẫn hỏng nhiều nhất: "
                              + ", ".join(f"{r.phuong_thuc} {r.duong_dan} ×{r.so_lan}"
                                          for r in sorted(loi, key=lambda x: -x.so_lan)[:3]),
                   "chi_tiet": {"so_duong_dan": len(loi), "so_luot": tong,
                                "duong_dan": [f"{r.phuong_thuc} {r.duong_dan}" for r in loi[:40]]}})
    nen = [r for r in ds if r.loai == "tac_vu_nen"]
    if nen:
        ra.append({"ma": "may_chu_loi#tac_vu_nen", "loai": "may_chu_loi", "muc": "do",
                   "phong_ban": "Công nghệ thông tin", "doi_tuong": "tac_vu_nen",
                   "tom_tat": f"{len(nen)} tác vụ nền thất bại ({sum(r.so_lan for r in nen)} lượt). "
                              f"Tác vụ nền hỏng thì không ai thấy trên màn hình nào – cảnh báo, phiếu "
                              f"chăm sóc và bảng điều khiển dựng sẵn đều dừng lặng lẽ.",
                   "chi_tiet": {"tac_vu": [f"{r.duong_dan or r.thong_bao[:60]} ×{r.so_lan}" for r in nen[:20]]}})
    cham = [r for r in ds if r.loai == "cham"]
    if cham:
        ra.append({"ma": "may_chu_loi#cham", "loai": "may_chu_loi", "muc": "vang",
                   "phong_ban": "Công nghệ thông tin", "doi_tuong": "hieu_nang",
                   "tom_tat": f"{len(cham)} đường dẫn chạy quá {NGUONG_CHAM_MS} mili giây. Chậm nhất: "
                              + ", ".join(f"{r.duong_dan} {r.mili_giay}ms"
                                          for r in sorted(cham, key=lambda x: -(x.mili_giay or 0))[:3]),
                   "chi_tiet": {"duong_dan": [{"duong_dan": r.duong_dan, "ms": r.mili_giay,
                                               "so_lan": r.so_lan} for r in
                                              sorted(cham, key=lambda x: -(x.mili_giay or 0))[:20]]}})
    kd = [r for r in ds if r.loai == "khoi_dong" and r.muc == "do"]
    if kd:
        ra.append({"ma": "may_chu_loi#khoi_dong", "loai": "may_chu_loi", "muc": "do",
                   "phong_ban": "Công nghệ thông tin", "doi_tuong": "khoi_dong",
                   "tom_tat": "Máy chủ khởi động khi mạch nâng cấp cơ sở dữ liệu có nhiều hơn một đầu – "
                              "lần phát hành tới sẽ không lên được.",
                   "chi_tiet": {}})
    for r in ds: r.da_bao = True
    db.commit()
    return ra


def bang(db: Session, ngay: int = 7) -> dict:
    tu = datetime.now() - timedelta(days=max(1, ngay))
    ds = list(db.execute(select(SuKienKyThuat).where(SuKienKyThuat.lan_cuoi >= tu)
                         .order_by(SuKienKyThuat.lan_cuoi.desc())).scalars())
    return {"nguong_cham_ms": NGUONG_CHAM_MS, "so_ngay": ngay,
            "loai": LOAI_SU_KIEN, "muc": MUC_SU_KIEN,
            "dem": {k: sum(r.so_lan for r in ds if r.loai == k) for k in LOAI_SU_KIEN},
            "rows": [{"id": r.id, "loai": r.loai, "loai_ten": LOAI_SU_KIEN.get(r.loai, r.loai),
                      "muc": r.muc, "duong_dan": r.duong_dan, "phuong_thuc": r.phuong_thuc,
                      "ma_trang_thai": r.ma_trang_thai, "mili_giay": r.mili_giay,
                      "vai_tro": r.vai_tro, "thong_bao": r.thong_bao, "dau_vet": r.dau_vet,
                      "so_lan": r.so_lan, "lan_dau": r.lan_dau, "lan_cuoi": r.lan_cuoi}
                     for r in ds[:300]]}
