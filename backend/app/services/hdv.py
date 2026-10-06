"""Phòng Hướng dẫn viên — phép chặn hai chuyến chồng giờ, và phép đếm phần còn thiếu.

Chủ tịch chốt 06/10/2026: KHÔNG xếp một hướng dẫn viên vào hai chuyến chồng giờ. Không phải "cảnh
báo rồi vẫn cho qua" — cấm.

────────────────────────────────── CHỒNG GIỜ LÀ GÌ ──────────────────────────────────

Hai khoảng [a1,a2) và [b1,b2) chồng nhau khi:  a1 < b2  VÀ  b1 < a2

Viết nửa mở — đầu đóng, cuối mở — là điều phải nói rõ, vì nó quyết định một ca có thật và hay gặp:
chuyến A kết thúc ĐÚNG 18h, chuyến B bắt đầu ĐÚNG 18h. Với nửa mở thì a1 < b2 đúng nhưng b1 < a2 sai
(18h < 18h là sai), nên KHÔNG chồng — và đó là điều đúng về mặt nghiệp vụ: giao đoàn xong là hết
việc. Nếu viết <= thì mọi lần nối tiếp liền mạch đều bị chặn, và người xếp lịch sẽ học cách lùi giờ
một phút để lách — tức là hệ thống dạy người dùng ghi sai giờ.

Phần đệm đi lại KHÔNG cộng ở đây mà nằm trong chính hai mốc giờ của phân công: "khoảng cần người"
tính cả chuẩn bị và di chuyển (xem app/models/hdv.py). Cộng thêm một khoảng đệm cứng ở tầng phép
tính thì con số ấy không ai nhìn thấy, không ai sửa được, và sẽ đúng cho tuyến này sai cho tuyến kia.

──────────────────────── RỖNG KHÔNG PHẢI LÀ KHÔNG CHỒNG ────────────────────────

Phân công thiếu giờ thì KHÔNG so được — và `khong_so_duoc` nói đúng điều đó thay vì trả về "không
chồng". Hai chuyện khác nhau: "đã kiểm, không chồng" là một kết luận; "chưa đủ dữ liệu để kiểm" là
một việc còn thiếu. Gộp hai thứ ấy làm một thì hàng trăm phân công cũ không có giờ sẽ lặng lẽ được
coi là đã kiểm xong, và cái cấm mà Chủ tịch vừa chốt thành ra chỉ áp cho dữ liệu mới.

Cửa lập phân công vì thế ĐÒI đủ hai mốc giờ — không có giờ thì không chặn được, mà không chặn được
thì không được phép ghi. Bản ghi CŨ thiếu giờ vẫn giữ nguyên, hiện ở danh sách việc còn thiếu.

──────────────────────────── CHẶN THẬT, KHÔNG CHỈ HỎI TRƯỚC ────────────────────────────

Hỏi trước khi ghi ("có ai trùng không?" rồi mới ghi) KHÔNG đủ: hai phiên cùng hỏi lúc chưa ai ghi,
cả hai cùng thấy trống, cả hai cùng ghi. Nên ở đây làm hai lớp:

  1. Trước khi ghi: khoá hàng hướng dẫn viên trong `employees` bằng SELECT ... FOR UPDATE. Postgres
     xếp hàng hai phiên tại đúng chỗ này. SQLite không có FOR UPDATE và cũng không cần — nó khoá
     toàn tệp.
  2. SAU khi ghi, TRƯỚC khi chốt giao dịch: đếm lại số phân công chồng giờ của chính người ấy. Nếu
     còn ai khác ngoài bản vừa ghi thì có người đã chen vào giữa — lùi lại và từ chối.

Lớp 2 là lớp thật sự bảo đảm, và nó chạy đúng trên cả hai loại máy chủ. Lớp 1 chỉ để hai phiên không
phải cùng làm rồi cùng hỏng.
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hdv import TRANG_THAI_DONG as YC_DONG
from app.models.hdv import YeuCauHdv
from app.models.hr import GuideAssignment

# Phân công ở hai trạng thái này KHÔNG chiếm lịch nữa: người ta đã từ chối, hoặc lời chào đã hết hạn.
# Nhưng bản ghi vẫn còn — giữ dấu vết là điều kiện để sau này trả lời được "ai đã từ chối chuyến nào".
KHONG_CHIEM_LICH = ("tu_choi", "huy", "het_han")


def chong_gio(a1: datetime | None, a2: datetime | None,
              b1: datetime | None, b2: datetime | None) -> bool:
    """Hai khoảng nửa mở có chồng nhau không. Thiếu bất kỳ mốc nào thì trả về False – nhưng người
    gọi KHÔNG được coi đó là 'đã kiểm, không chồng': dùng `khong_so_duoc` để phân biệt."""
    if khong_so_duoc(a1, a2) or khong_so_duoc(b1, b2):
        return False
    return a1 < b2 and b1 < a2


def khong_so_duoc(t1: datetime | None, t2: datetime | None) -> bool:
    """Thiếu mốc, hoặc hai mốc ngược chiều nhau. Ngược chiều cũng là không so được chứ không phải
    'khoảng rỗng': kết thúc trước bắt đầu là một lần gõ nhầm, phải nói ra."""
    return t1 is None or t2 is None or t2 <= t1


def dang_chiem_lich(db: Session, guide_id: int, bat_dau: datetime, ket_thuc: datetime,
                    bo_qua_id: int | None = None) -> list[GuideAssignment]:
    """Những phân công còn hiệu lực của người này chồng giờ với khoảng đưa vào.

    Lọc theo trạng thái Ở TRONG PYTHON chứ không nhét vào câu truy vấn: danh sách phân công của một
    người trong một kỳ là vài chục dòng, và viết ra ngoài thì người đọc thấy ngay quy tắc nào đang
    áp – quy tắc "từ chối thì không chiếm lịch" là quy tắc nghiệp vụ, không nên chôn trong SQL.
    """
    q = select(GuideAssignment).where(GuideAssignment.guide_id == guide_id)
    if bo_qua_id is not None:
        q = q.where(GuideAssignment.id != bo_qua_id)
    ds = []
    for a in db.execute(q).scalars():
        if a.status in KHONG_CHIEM_LICH:
            continue
        if chong_gio(bat_dau, ket_thuc, a.bat_dau, a.ket_thuc):
            ds.append(a)
    return ds


def khoa_hdv(db: Session, guide_id: int) -> None:
    """Lớp 1 – xếp hàng hai phiên cùng xếp một người. Trên Postgres là khoá hàng thật; trên SQLite
    câu này chạy không lỗi và không làm gì, vì SQLite đã khoá ở mức tệp."""
    from app.models.hr import Employee
    try:
        db.execute(select(Employee).where(Employee.id == guide_id).with_for_update())
    except Exception:
        # Máy chủ không hỗ trợ FOR UPDATE (SQLite). KHÔNG phải lý do để dừng, và cũng KHÔNG được
        # nuốt im lặng thành "đã khoá": lớp 2 mới là lớp bảo đảm, và nó chạy ở mọi máy chủ.
        pass


def canh_trung_sau_khi_ghi(db: Session, a: GuideAssignment) -> None:
    """Lớp 2 – gọi SAU db.flush() và TRƯỚC db.commit().

    Nếu giữa lúc kiểm và lúc ghi có người chen vào thì đến đây sẽ thấy. Ném 422 kèm TÊN CHUYẾN đang
    chồng, không chỉ ném chữ 'trùng lịch': người xếp lịch cần biết phải gỡ chuyến nào.
    """
    if khong_so_duoc(a.bat_dau, a.ket_thuc):
        return
    trung = dang_chiem_lich(db, a.guide_id, a.bat_dau, a.ket_thuc, bo_qua_id=a.id)
    if not trung:
        return
    from app.models.core import Tour
    ten = []
    for k in trung[:3]:
        t = db.get(Tour, k.tour_id)
        nhan = t.code if t else f"tour {k.tour_id}"
        if k.bat_dau and k.ket_thuc:
            nhan += f" ({k.bat_dau:%d/%m %H:%M}–{k.ket_thuc:%d/%m %H:%M})"
        ten.append(nhan)
    db.rollback()
    raise HTTPException(422, {
        "gate": "TRUNG_GIO_HDV",
        "message": "Hướng dẫn viên này đã có chuyến chồng giờ: " + "; ".join(ten)
                   + ". Gỡ phân công cũ hoặc chọn người khác.",
        "trung_voi": [k.id for k in trung],
    })


def con_thieu(db: Session, yc: YeuCauHdv) -> int:
    """QUY ƯỚC CHUNG cho chữ 'chuyến chưa đủ nguồn lực' – phần xe phải có một hàm cùng nghĩa.

    Đếm số người CÒN PHẢI TÌM: số yêu cầu trừ đi số phân công còn hiệu lực đang trỏ về yêu cầu này.
    Người đã từ chối không tính là đã có – đó chính là chỗ một màn hình đếm sai sẽ báo "đã đủ" cho
    một chuyến không còn ai.
    """
    if yc.trang_thai in YC_DONG:
        return 0
    da_co = 0
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.yeu_cau_id == yc.id)).scalars():
        if a.status not in KHONG_CHIEM_LICH:
            da_co += 1
    return max(0, (yc.so_hdv or 0) - da_co)


def cap_nhat_trang_thai(db: Session, yc: YeuCauHdv) -> None:
    """Trạng thái yêu cầu suy từ phần còn thiếu, KHÔNG do người bấm tay – trừ huỷ. Để người bấm tay
    thì sẽ có yêu cầu mang nhãn 'đã đủ' mà không còn ai, ngay sau một lần từ chối."""
    if yc.trang_thai == "huy":
        return
    thieu = con_thieu(db, yc)
    if thieu == 0:
        yc.trang_thai = "da_du"
    elif thieu < (yc.so_hdv or 0):
        yc.trang_thai = "dang_xep"
    else:
        yc.trang_thai = "moi"


# ═══════════════════════════ Đợt 2 · BÁO CÁO SAU TOUR (06/10/2026) ═══════════════════════════
#
# Hai điều cần nói trước khi đọc mã:
#
# 1. CỘT CŨ `report_submitted` KHÔNG BỊ BỎ. Nó đang gánh hai quyết định thật — treo chào chuyến mới
#    sau 3 ngày (app/api/v1/huong_dan.py) và treo thù lao (app/services/luong.py). Bỏ nó thì hai chỗ
#    ấy im lặng ngừng hoạt động. Thay vào đó, từ Đợt 2 nó thành TẤM GƯƠNG của bảng mới: bật khi báo
#    cáo được XÁC NHẬN, tắt khi bị trả lại. Hai chỗ kia không phải sửa một dòng nào.
#
# 2. GỬI KHÔNG BẰNG XONG. Chỉ bản `da_xac_nhan` mới gỡ treo. Nếu "đã gửi" là đủ thì gửi một tờ trống
#    cũng hết bị treo, và cái treo ấy mất hết tác dụng ngay ngày đầu.
from datetime import date, timedelta

from app.models.hdv import BC_DA_XONG, HAN_NOP_NGAY, BaoCaoSauTour


def han_nop_cua(ngay_ket_thuc: date | None) -> date | None:
    """Hạn nộp = ngày tour kết thúc + 3 ngày. Chuyến chưa có ngày kết thúc thì KHÔNG đoán hạn: một
    hạn bịa ra sẽ sinh cảnh báo trễ cho người chưa hề trễ, và cảnh báo sai vài lần thì người dùng
    thôi đọc cảnh báo."""
    if ngay_ket_thuc is None:
        return None
    return ngay_ket_thuc + timedelta(days=HAN_NOP_NGAY)


def ban_dang_xet(db: Session, assignment_id: int) -> BaoCaoSauTour | None:
    """Bản còn hiệu lực của một phân công: bản mới nhất chưa bị thay. Trả None khi chưa có bản nào —
    và 'chưa có bản nào' KHÁC 'có bản chưa xong', nên người gọi phải phân biệt hai cái."""
    ds = db.execute(
        select(BaoCaoSauTour)
        .where(BaoCaoSauTour.assignment_id == assignment_id, BaoCaoSauTour.bi_thay == False)  # noqa: E712
        .order_by(BaoCaoSauTour.ban_so.desc())
    ).scalars().all()
    return ds[0] if ds else None


def dong_bo_co_bao_cao(db: Session, a: GuideAssignment) -> None:
    """Chép trạng thái báo cáo sang cột cũ `report_submitted`.

    Gọi sau MỖI lần trạng thái báo cáo đổi. Không gọi thì hai quyết định đang dựa vào cột cũ sẽ nói
    một đằng, bảng mới nói một nẻo — và người dùng tin cái nào cũng sai một nửa.
    """
    bc = ban_dang_xet(db, a.id)
    a.report_submitted = bool(bc and bc.trang_thai in BC_DA_XONG)


def thieu_bao_cao_cua_tour(db: Session, tour_id: int) -> list[dict]:
    """Những hướng dẫn viên của chuyến này còn nợ báo cáo đã xác nhận.

    Đây là CĂN CỨ để màn hình quyết toán không gọi một tờ là "hoàn tất" khi phần hướng dẫn viên chưa
    xong — Chủ tịch chốt 06/10/2026. Hàm trả về DANH SÁCH NGƯỜI chứ không trả về đúng/sai: người làm
    quyết toán cần biết phải gọi ai, không cần biết thêm một ô đỏ.

    Phân công đã từ chối / huỷ / hết hạn KHÔNG tính: người ta không đi thì không có gì để báo cáo.
    """
    from app.models.hr import Employee
    thieu = []
    for a in db.execute(select(GuideAssignment).where(GuideAssignment.tour_id == tour_id)).scalars():
        if a.status in KHONG_CHIEM_LICH:
            continue
        bc = ban_dang_xet(db, a.id)
        if bc is not None and bc.trang_thai in BC_DA_XONG:
            continue
        e = db.get(Employee, a.guide_id)
        thieu.append({
            "assignment_id": a.id,
            "guide_id": a.guide_id,
            "hdv": e.full_name if e else f"nhân sự {a.guide_id}",
            # Ba tình trạng khác nhau, KHÔNG gộp thành một chữ "thiếu": chưa nộp gì, đã nộp đang chờ
            # kiểm, và đã bị trả lại. Ba cái ấy gọi ba người khác nhau để xử lý.
            "tinh_trang": "chua_nop" if bc is None else bc.trang_thai,
            "ban_so": bc.ban_so if bc else 0,
            "han_nop": bc.han_nop if bc else None,
            "tre_han": bool(bc and bc.tre_han()),
        })
    return thieu


# ═════════════════════ Đợt 3 · TIỀN CỦA HƯỚNG DẪN VIÊN (07/10/2026) ═════════════════════

from app.models.hdv import UNG_DANG_MO, TamUngHdv
from app.models.hr import GuideRate


def tra_don_gia(db: Session, route: str, loai_tour: str, ngay: date | None) -> GuideRate | None:
    """Đơn giá đang hiệu lực cho một tuyến và một loại tour.

    Chủ tịch chốt 06/10/2026: thù lao = số ngày của tour × đơn giá(tuyến, loại tour).

    HAI BẬC, bậc sau chỉ chạy khi bậc trước không có:
      1. Bản giá khai ĐÚNG loại tour ấy.
      2. Bản giá CHUNG (`loai_tour` rỗng).

    Làm ngược thứ tự thì một bản chung mới ký sẽ che mất bản riêng đã có, và không ai thấy vì cả hai
    đều đang hiệu lực.

    Thiếu ngày thì lấy bản mới nhất đang hiệu lực – KHÔNG trả None, vì "chưa biết ngày áp dụng" là
    chuyện của người gọi, còn ở đây câu hỏi là "tuyến này đang có giá nào".
    """
    def _lay(lt: str) -> GuideRate | None:
        q = select(GuideRate).where(GuideRate.route == route,
                                    GuideRate.loai_tour == lt,
                                    GuideRate.status == "active")
        ds = [r for r in db.execute(q).scalars()
              if ngay is None or (r.effective_from is not None and r.effective_from <= ngay)]
        if not ds:
            return None
        return sorted(ds, key=lambda r: (r.effective_from, r.id))[-1]

    return _lay(loai_tour or "") or (_lay("") if loai_tour else None)


def thu_lao(so_ngay: int | float | None, don_gia: float | None, le_tet: bool = False) -> float | None:
    """số ngày × đơn giá, lễ Tết nhân đôi.

    Trả về None khi THIẾU đơn giá – và đó là điều cố ý: "chưa có bảng giá cho tuyến này" phải hiện ra
    thành ô trống chứ không thành số 0. Một bảng thù lao toàn số 0 trông như đã tính xong và trả đủ.
    Thiếu số ngày thì coi là 0 ngày, vì 0 ngày là một con số có thật (phân công vừa lập, chưa đi).
    """
    if don_gia is None:
        return None
    return float(so_ngay or 0) * float(don_gia) * (2 if le_tet else 1)


def so_du_ung(db: Session, guide_id: int) -> list[dict]:
    """Số dư tạm ứng của một hướng dẫn viên, TÁCH THEO TỪNG TÚI.

    Trả về danh sách chứ không trả một con số, và đó là điểm chính của hàm này. Đặc tả v1.0 §06:
    "không tự gộp khác pháp nhân/ngoại tệ". Một người có thể cầm 5 triệu đồng của Vietourist và 300
    đô của một đối tác; cộng lại thành "5.3" là một con số không có thật và không ai trả được.

    Túi = (chủ tiền, loại tiền). Tiền thu hộ khách là một túi RIÊNG và không bao giờ bù trừ sang túi
    của công ty – trộn vào là lấy tiền khách che một khoản công ty nợ.

    Số âm nghĩa là công ty nợ lại người ấy. Không phải lỗi, và hệ thống không tự trả.
    """
    tui: dict[tuple[str, str], dict] = {}
    for u in db.execute(select(TamUngHdv).where(TamUngHdv.guide_id == guide_id)).scalars():
        if u.trang_thai == "huy":
            continue
        k = (u.chu_tien, u.loai_tien)
        t = tui.setdefault(k, {"chu_tien": u.chu_tien, "loai_tien": u.loai_tien,
                               "da_nhan": 0.0, "chi_ho_duyet": 0.0, "da_nop_lai": 0.0,
                               "so_du": 0.0, "so_khoan_dang_mo": 0})
        t["da_nhan"] += float(u.da_nhan or 0)
        t["chi_ho_duyet"] += float(u.chi_ho_duyet or 0)
        t["da_nop_lai"] += float(u.da_nop_lai or 0)
        t["so_du"] += u.so_du()
        if u.dang_mo():
            t["so_khoan_dang_mo"] += 1
    for t in tui.values():
        t["cong_ty_no_lai"] = t["so_du"] < 0
        t["khong_bu_tru"] = t["chu_tien"] == "khach"
    return sorted(tui.values(), key=lambda t: (t["chu_tien"], t["loai_tien"]))


# ══════════════ Đợt 4 · BƯỚC DUYỆT CÓ CẤP (07/10/2026) ══════════════

from fastapi import HTTPException as _HTTP

from app.models.hdv import BuocDuyetHdv, CauHinhDuyetHdv, DeXuatHdv


def tra_cau_hinh(db: Session, loai: str, so_tien: float | None, ngay: date | None = None) -> CauHinhDuyetHdv:
    """Dòng cấu hình áp cho một đề xuất. KHÔNG tìm thấy thì NÉM LỖI, không tự chọn một đường đi.

    Đặc tả v1.0 §10: "Thiếu cấu hình thì chặn trình; không cho TP tự bỏ cấp." Lý do: nếu hệ thống tự
    chọn khi thiếu cấu hình thì đường nó chọn sẽ thành tiền lệ — không ai ký mà vẫn thành luật, và
    phát hiện ra thì đã có hàng chục hồ sơ đi theo đường ấy.

    `den_so_tien` rỗng = không có trần. Thiếu quy ước ấy thì hồ sơ lớn hơn mức cao nhất đã khai sẽ
    không khớp dòng nào — mà đó đúng là những hồ sơ cần cấp cao nhất.
    """
    t = float(so_tien or 0)
    hom_nay = ngay or date.today()
    hop = []
    for c in db.execute(select(CauHinhDuyetHdv).where(CauHinhDuyetHdv.loai == loai)).scalars():
        if c.trang_thai != "hieu_luc":
            continue
        if c.hieu_luc_tu is not None and c.hieu_luc_tu > hom_nay:
            continue
        if t < float(c.tu_so_tien or 0):
            continue
        if c.den_so_tien is not None and t > float(c.den_so_tien):
            continue
        if not c.danh_sach_cap():
            continue
        hop.append(c)
    if not hop:
        raise _HTTP(422, {
            "gate": "THIEU_CAU_HINH_DUYET",
            "message": f"Chưa có cấu hình cấp duyệt cho loại '{loai}' ở mức tiền {t:,.0f}. "
                       f"Hồ sơ bị CHẶN TRÌNH — hệ thống không tự chọn cấp duyệt, vì đường nó tự chọn "
                       f"sẽ thành tiền lệ mà không ai ký. Cần người có thẩm quyền khai cấu hình trước.",
            "loai": loai, "so_tien": t})
    # Nhiều dòng cùng khớp thì lấy dòng có hiệu lực MUỘN NHẤT, rồi tới dòng có cận dưới CAO NHẤT —
    # tức dòng hẹp nhất và mới nhất. Lấy dòng rộng nhất thì một khoảng mới khai cho mức cao sẽ bị một
    # dòng cũ "từ 0 trở lên" nuốt mất.
    return sorted(hop, key=lambda c: (c.hieu_luc_tu or date.min, float(c.tu_so_tien or 0), c.id))[-1]


def lap_cac_buoc(db: Session, dx: DeXuatHdv, ch: CauHinhDuyetHdv) -> list[BuocDuyetHdv]:
    """Lập ĐỦ các bước ngay lúc trình, không sinh dần. Xem chú thích ở BuocDuyetHdv."""
    cu = db.execute(select(BuocDuyetHdv).where(BuocDuyetHdv.de_xuat_id == dx.id)).scalars().all()
    for b in cu:
        db.delete(b)
    db.flush()
    ds = []
    for i, vai in enumerate(ch.danh_sach_cap(), start=1):
        b = BuocDuyetHdv(de_xuat_id=dx.id, thu_tu=i, vai_tro=vai)
        db.add(b)
        ds.append(b)
    db.flush()
    return ds


def buoc_dang_cho(db: Session, dx: DeXuatHdv) -> BuocDuyetHdv | None:
    for b in db.execute(select(BuocDuyetHdv).where(BuocDuyetHdv.de_xuat_id == dx.id)
                        .order_by(BuocDuyetHdv.thu_tu)).scalars():
        if b.trang_thai == "cho":
            return b
    return None


def kiem_nguoi_quyet(dx: DeXuatHdv, b: BuocDuyetHdv, username: str, vai_tro: str) -> None:
    """Ba hàng rào, và cả ba đều cần:

      1. Đúng VAI TRÒ của bước đang chờ — không phải vai nào cũng ký được mọi bước. Một bước có thể
         nhận nhiều vai trò thay thế nhau (`chutich|tgd`): khi đó MỘT trong các vai ấy là đủ, và đủ
         rồi thì bước xong — không chờ nốt những vai còn lại.
      2. Không phải NGƯỜI TRÌNH — tự trình rồi tự duyệt thì cái duyệt ấy không kiểm gì cả.
      3. Chưa ai quyết bước này — chống bấm hai lần, và chống hai người cùng quyết một bước.
    """
    if b.trang_thai != "cho":
        raise _HTTP(422, f"Bước {b.thu_tu} đã được quyết rồi ({b.trang_thai}) – không quyết lại")
    vai_hop = b.cac_vai()
    if vai_tro not in vai_hop:
        cho = " hoặc ".join(f"'{v}'" for v in vai_hop) or "(chưa khai vai trò)"
        raise _HTTP(403, f"Bước {b.thu_tu} chờ chữ ký của {cho}, không phải '{vai_tro}'")
    if dx.nguoi_lap and username == dx.nguoi_lap:
        raise _HTTP(422, "Người trình hồ sơ không được tự duyệt hồ sơ mình trình")
