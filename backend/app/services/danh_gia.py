"""Đánh giá sau tour — khách tự chấm qua một mã khảo sát dùng một lần.

Đề xuất tự động hoá CSKH ngày 25/9/2026, bước 2–5. Tệp này giữ BA việc và không giữ việc thứ tư:

    1. Sinh mã khảo sát cho một phiếu chăm sóc.
    2. Đọc phiếu cho trang công khai — CHỈ những gì khách đã biết.
    3. Ghi đánh giá khách gửi lên, rồi gọi lại đúng luật cũ của `cskh.ghi_ket_qua`.

Việc KHÔNG giữ: gửi tin Zalo. Đó là việc của `cskh.robot_cskh` gọi `zalo.queue`. Tệp này không
biết tin đi bằng đường nào, và đó là cố ý — ngày mai đổi sang SMS hay email thì nó không đổi.

═══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT CŨ KHÔNG ĐƯỢC DỰNG LẠI Ở ĐÂY
═══════════════════════════════════════════════════════════════════════════════════════════════
Điểm thấp thì tự mở hồ sơ khiếu nại; khách muốn đi tiếp thì tự tạo lead khách cũ. Hai luật ấy đã
có trong `cskh.ghi_ket_qua` từ Đợt 4 và đã chạy thật. Chép lại chúng vào đây là tạo bản sao thứ
hai của một luật, và bản sao nào rồi cũng lệch — lần này lệch ở chỗ nguy hiểm nhất: ngưỡng mở
khiếu nại. Nên `ghi_danh_gia` gọi thẳng `cskh.ghi_ket_qua`, chỉ khác ở chỗ người gọi là MÁY.
"""
import secrets
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.core import Booking, Tour, User
from app.models.cskh import CS_DIEM, CareTicket
from app.models.danh_gia import DG_CO_KHOA, DG_DOI_TUONG, DanhGiaSauTour, MaKhaoSat
from app.models.hr import Employee, GuideAssignment
from app.services import rules as R

# Mã sống bao lâu. Đủ dài để khách đi công tác về vẫn chấm được, đủ ngắn để không thành một cửa
# mở mãi. Tham số hoá để đổi không cần sửa mã.
MA_HAN_NGAY_MAC_DINH = 14

# Tài khoản MÁY đứng tên khi khách tự chấm. Không mượn tên người thật: hồ sơ khiếu nại mở từ một
# lần khách chấm điểm phải đọc ra là "máy mở", không phải "chị A mở" — chị A không làm gì cả.
MAY_USERNAME = "robot_cskh"


class Gate(HTTPException):
    def __init__(self, code: str, msg: str): super().__init__(422, {"gate": code, "message": msg})


def _may(db: Session) -> User:
    """Tài khoản máy. Không có thì dựng một cái — nó không có mật khẩu dùng được."""
    u = db.execute(select(User).where(User.username == MAY_USERNAME)).scalars().first()
    if not u:
        u = User(username=MAY_USERNAME, full_name="Robot chăm sóc khách", role="cntt",
                 password_hash="!", active=False)
        db.add(u); db.flush()
    return u


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · MÃ KHẢO SÁT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def sinh_ma(db: Session, care: CareTicket) -> MaKhaoSat:
    """Một phiếu một mã — MỘT mã còn sống tại một thời điểm. Gọi lại trên phiếu đã có mã thì trả
    lại mã cũ, không sinh mã thứ hai: hai mã sống cùng lúc cho một phiếu nghĩa là khách chấm được
    hai lần.

    TC-95 thêm đúng một ngoại lệ: mã đã HẾT HẠN mà chưa ai chạm vào thì được cấp lại — cùng dòng,
    mã mới, hạn mới. Xem lời khai trong thân hàm; ngoại lệ ấy không mở thêm cửa nào, vì mã cũ lúc
    ấy đã không mở được nữa."""
    ngay = int(R.get_param(db, "khao_sat_han_ngay") or MA_HAN_NGAY_MAC_DINH)
    co = db.execute(select(MaKhaoSat).where(MaKhaoSat.care_id == care.id)).scalars().first()
    if co:
        # CẤP LẠI khi mã cũ đã chết mà CHƯA AI CHẠM VÀO — TC-95, 29/9/2026.
        #
        # Vì sao cần: `care_id` là khoá duy nhất, một phiếu một mã, đời đời. Đo ngày 29/9 có 401
        # lời mời chưa bao giờ gửi được (chưa có mẫu ZNS, khách chưa quan tâm OA); mã của chúng cứ
        # thế hết hạn. Không có đường cấp lại thì 401 khách ấy VĨNH VIỄN không được mời — hệ thống
        # im lặng bỏ rơi họ, và không dòng nào trên màn hình nói ra điều đó.
        #
        # Ba điều kiện, và cả ba đều cần:
        #   · `het_han` đã qua   – mã còn sống thì dùng tiếp, cấp mã mới là mở hai cửa cho một phiếu;
        #   · `dung_luc` rỗng    – khách đã chấm rồi thì thôi, hỏi lại là làm phiền;
        #   · `so_lan_mo` = 0    – khách ĐÃ MỞ mà không chấm là một câu trả lời, dù không thành lời.
        #                          Đuổi theo người đã cố tình bỏ qua là cách mất một khách hàng.
        con_song = co.het_han and co.het_han > datetime.now()
        ai_do_da_cham = co.dung_luc is not None or (co.so_lan_mo or 0) > 0
        if con_song or ai_do_da_cham:
            return co
        co.ma = secrets.token_urlsafe(24)
        co.het_han = datetime.now() + timedelta(days=ngay)
        co.tao_luc = datetime.now()
        db.flush()
        return co
    m = MaKhaoSat(ma=secrets.token_urlsafe(24), care_id=care.id,
                  het_han=datetime.now() + timedelta(days=ngay))
    db.add(m); db.flush()
    return m


def _tim_ma(db: Session, ma: str) -> MaKhaoSat:
    m = db.execute(select(MaKhaoSat).where(MaKhaoSat.ma == (ma or "").strip())).scalars().first()
    # Cùng một lời từ chối cho "không có mã" và "mã sai": nói khác nhau là chỉ cho người dò biết
    # mã nào tồn tại.
    if not m: raise Gate("KHAO_SAT", "Liên kết không đúng hoặc đã hết hiệu lực.")
    return m


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · ĐỌC PHIẾU CHO TRANG CÔNG KHAI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _nguoi_cua_chuyen(db: Session, t: Tour) -> list[dict]:
    """Hướng dẫn viên của chuyến, lấy từ LỆNH ĐIỀU ĐỘNG đã xác nhận.

    Phải hiện TÊN TỪNG NGƯỜI chứ không phải một ô "HDV" chung: chuyến hai hướng dẫn viên mà chỉ có
    một ô thì bảng điểm HDV không bao giờ cộng đúng — và người bị chấm oan không có cách nào cãi.
    """
    ra = []
    for a in db.execute(select(GuideAssignment).where(
            GuideAssignment.tour_id == t.id,
            GuideAssignment.status.in_(["da_xac_nhan", "cho_xac_nhan"]))).scalars():
        e = db.get(Employee, a.guide_id)
        if e: ra.append({"doi_tuong": "hdv", "id": e.id, "ten": e.full_name})
    return ra


def mo_phieu(db: Session, ma: str, ghi_lan_mo: bool = True) -> dict:
    """Nội dung trang khách mở ra.

    CHỈ những gì khách đã biết: tên chuyến, ngày đi, tên người phục vụ họ. KHÔNG số điện thoại,
    KHÔNG giá, KHÔNG tên khách khác cùng đoàn, KHÔNG mã booking. Cửa này ra đường — mọi thứ in ra
    đây là in cho bất kỳ ai cầm được đường dẫn.
    """
    m = _tim_ma(db, ma)
    if m.dung_luc:
        raise Gate("KHAO_SAT_DA_DUNG", "Cảm ơn anh/chị, đánh giá đã được ghi nhận rồi. "
                                       "Muốn sửa thì xin gọi tổng đài giúp em.")
    if m.het_han < datetime.now():
        raise Gate("KHAO_SAT_HET_HAN", "Liên kết đã hết hiệu lực. Xin gọi tổng đài nếu anh/chị "
                                       "vẫn muốn gửi đánh giá.")
    care = db.get(CareTicket, m.care_id)
    if not care: raise Gate("KHAO_SAT", "Liên kết không đúng hoặc đã hết hiệu lực.")
    t = db.get(Tour, care.tour_id)
    if ghi_lan_mo:
        m.so_lan_mo += 1
        if not m.mo_lan_dau: m.mo_lan_dau = datetime.now()
        db.commit()

    muc = [{"doi_tuong": "tour", "id": None, "ten": (t.name if t else "")}]
    muc += _nguoi_cua_chuyen(db, t) if t else []
    # Khách sạn và ăn uống chấm theo mảng, không theo nhà cung cấp cụ thể: khách không biết tên
    # công ty cung cấp, họ chỉ biết bữa ăn ngon hay không.
    muc += [{"doi_tuong": "khach_san", "id": None, "ten": "Khách sạn / nơi nghỉ"},
            {"doi_tuong": "an_uong", "id": None, "ten": "Ăn uống"}]
    return {
        "ten_khach": care.customer_name,          # họ tự biết tên mình
        "tour_ten": t.name if t else "",
        "ngay_di": t.start_date.isoformat() if t else None,
        "ngay_ve": t.end_date.isoformat() if t else None,
        "muc": muc,
        "diem_chua_hai_long": CS_DIEM,
        "doi_tuong_ten": DG_DOI_TUONG,
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · GHI ĐÁNH GIÁ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def ten_doi_tuong(db: Session, doi_tuong: str, doi_tuong_id, ten_goi_y: str = "") -> str:
    """Tên hiện lên của một mục được chấm — Đợt HD-DG2, 15/10/2026.

    MỘT CHỖ DUY NHẤT, và cả hai cửa ghi đều phải đi qua đây. Trước đợt này `ghi_danh_gia` tra tên
    từ hồ sơ nhân sự còn `ghi_ho` thì không, nên cùng một hướng dẫn viên có lượt mang tên thật và
    lượt mang nhãn chung "Hướng dẫn viên" — rồi bảng điểm gộp theo tên và tách người ấy làm hai
    dòng, mỗi dòng một điểm trung bình, không dòng nào đúng. Hai bản sao của một luật thì bản nào
    rồi cũng lệch.

    Loại CÓ khoá (`DG_CO_KHOA`) thì tên luôn lấy từ hồ sơ, KHÔNG nhận tên người gọi đưa vào: tên
    do màn hình gửi lên là thứ sửa được ở phía trình duyệt, và một bảng điểm nhận tên từ bên ngoài
    là một bảng điểm ai cũng gắn điểm cho ai được.
    """
    if doi_tuong in DG_CO_KHOA and doi_tuong_id:
        e = db.get(Employee, int(doi_tuong_id))
        if e:
            return e.full_name[:120]
    return ((ten_goi_y or "").strip() or DG_DOI_TUONG.get(doi_tuong, ""))[:120]


def ghi_danh_gia(db: Session, ma: str, data: dict) -> dict:
    """Khách bấm gửi. Một mã một lần.

    `data`:
        diem        [{doi_tuong, doi_tuong_id, diem, nhan_xet}]  — thiếu mục nào thì bỏ qua mục ấy
        nhu_cau_tiep   "co" | "khong"       (bắt buộc)
        dong_y_dung_danh_gia "co" | "khong" (bắt buộc — xem dưới)
        gop_y       lời tự do chung cho cả chuyến
    """
    m = _tim_ma(db, ma)
    if m.dung_luc: raise Gate("KHAO_SAT_DA_DUNG", "Đánh giá đã được ghi nhận rồi.")
    if m.het_han < datetime.now(): raise Gate("KHAO_SAT_HET_HAN", "Liên kết đã hết hiệu lực.")
    care = db.get(CareTicket, m.care_id)
    if not care: raise Gate("KHAO_SAT", "Liên kết không đúng hoặc đã hết hiệu lực.")

    dong = data.get("diem") or []
    if not isinstance(dong, list) or not dong:
        raise Gate("KHAO_SAT_NHAP", "Xin anh/chị chấm ít nhất một mục.")
    if data.get("nhu_cau_tiep") not in ("co", "khong"):
        raise Gate("KHAO_SAT_NHAP", "Xin cho biết anh/chị có muốn đi tour tiếp hay không.")
    # Hỏi lại câu xin phép, KHÔNG mặc định là đồng ý. Ô `dong_y_dung_danh_gia` đã có trên phiếu từ
    # Đợt 4 với đúng lý do ấy: chưa đồng ý thì tuyệt đối không đưa lời khách lên kênh truyền thông.
    # Một form tự động mà bỏ câu này đi là lấy mất một quyền của khách bằng cách im lặng.
    if data.get("dong_y_dung_danh_gia") not in ("co", "khong"):
        raise Gate("KHAO_SAT_NHAP", "Xin cho biết anh/chị có đồng ý cho công ty dùng lời nhận xét "
                                    "này hay không.")

    ghi, diem_tour = [], None
    for d in dong:
        dt = (d.get("doi_tuong") or "").strip()
        if dt not in DG_DOI_TUONG: raise Gate("KHAO_SAT_NHAP", f"Mục không hợp lệ: {dt}")
        did = d.get("doi_tuong_id")
        if dt in DG_CO_KHOA and not did:
            raise Gate("KHAO_SAT_NHAP", f"Mục {DG_DOI_TUONG[dt]} phải chấm cho một người cụ thể")
        if dt not in DG_CO_KHOA: did = None
        sao = d.get("diem")
        if sao in (None, ""):        # khách bỏ qua mục này — RỖNG, không phải 0
            if not (d.get("nhan_xet") or "").strip(): continue
            sao = None
        else:
            sao = int(sao)
            if sao < 1 or sao > 5: raise Gate("KHAO_SAT_NHAP", "Điểm chỉ từ 1 đến 5 sao")
        ten = ten_doi_tuong(db, dt, did, d.get("doi_tuong_ten") or "")
        ghi.append(DanhGiaSauTour(care_id=care.id, booking_id=care.booking_id, tour_id=care.tour_id,
                                  doi_tuong=dt, doi_tuong_id=did, doi_tuong_ten=ten,
                                  diem=sao, nhan_xet=(d.get("nhan_xet") or "").strip()[:2000],
                                  nguon="khach", nguoi_ghi=""))
        if dt == "tour" and sao: diem_tour = sao

    if not ghi: raise Gate("KHAO_SAT_NHAP", "Xin anh/chị chấm ít nhất một mục.")
    for x in ghi: db.add(x)

    # Điểm chung của phiếu = điểm chuyến nếu có; không có thì trung bình các mục đã chấm, LÀM TRÒN
    # XUỐNG. Làm tròn lên thì 2,5 thành 3 và vượt ngưỡng mở khiếu nại — một khách không hài lòng
    # biến mất khỏi sổ vì một phép làm tròn.
    if diem_tour is None:
        co_diem = [x.diem for x in ghi if x.diem]
        diem_tour = int(sum(co_diem) / len(co_diem)) if co_diem else 0

    # Điểm chưa hài lòng suy từ các mục bị chấm thấp, để luật cũ phân loại nhóm khiếu nại đúng.
    thap = {"hdv": "hdv", "tai_xe": "xe", "khach_san": "khach_san", "an_uong": "an_uong"}
    chua_hl = sorted({thap[x.doi_tuong] for x in ghi
                      if x.doi_tuong in thap and x.diem and x.diem <= 3})

    m.dung_luc = datetime.now()
    db.flush()

    # Gọi lại ĐÚNG luật cũ. Xem chú thích đầu tệp: không dựng bản sao thứ hai của ngưỡng mở khiếu
    # nại và của luật tạo lead khách cũ.
    from app.services import cskh as CS
    care, sinh = CS.ghi_ket_qua(db, _may(db), care, {
        "lien_he_duoc": "co", "hinh_thuc": "zalo", "hai_long": max(1, min(5, diem_tour)),
        "nhu_cau_tiep": data["nhu_cau_tiep"],
        "dong_y_dung_danh_gia": data["dong_y_dung_danh_gia"],
        "diem_chua_hai_long": chua_hl,
        "ghi_chu": (data.get("gop_y") or "").strip()[:2000],
    })
    # ─────────────────────────────────────────────────────────────────────────────────────────
    # KHÁCH 4–5 SAO: MỜI ĐÁNH GIÁ GOOGLE MAPS — đề xuất CSKH 25/9, bước 3
    # ─────────────────────────────────────────────────────────────────────────────────────────
    # CHỈ MỜI NGƯỜI ĐÃ HÀI LÒNG, và chỉ mời SAU KHI họ đã chấm xong trong sổ của mình. Hai điều
    # kiện ấy không phải để lọc lấy điểm đẹp ngoài kia — mà vì mời một khách vừa chấm 2 sao đi
    # viết đánh giá công khai là mời họ viết đúng điều họ vừa nói, ở chỗ ta không sửa được.
    #
    # LINK LÀ THAM SỐ, không viết cứng: hồ sơ Google của công ty đổi được, và một đường dẫn chết
    # nằm trong mã thì ba tháng sau không ai biết nó chết.
    #
    # KHÔNG gửi tin thứ hai qua Zalo cho việc này. Khách vừa bấm gửi xong đang ở trên trang —
    # hiện lời mời ngay tại đó là chỗ duy nhất họ còn đang chú ý, và không tốn thêm một phí tin.
    ra = {"hai_long": care.hai_long, "so_muc": len(ghi), "sinh_them": sinh,
          "loi_cam_on": "Cảm ơn anh/chị đã dành thời gian. Đánh giá đã được ghi nhận."}
    if (diem_tour or 0) >= 4:
        # `get_param` ép về float và nổ với thứ không phải số — đường dẫn phải đi qua
        # `get_param_text`, cửa dành cho tham số dạng chữ (xem chú thích ở rules.py).
        link = (R.get_param_text(db, "link_danh_gia_google") or "").strip()
        if link:
            ra["link_danh_gia_google"] = link
            ra["loi_moi_danh_gia"] = ("Anh/chị dành thêm một phút viết vài dòng trên Google giúp "
                                      "Vietourist nhé — điều đó giúp khách sau chọn được đúng tour.")
    return ra


def ghi_ho(db: Session, u: User, care: CareTicket, data: dict) -> dict:
    """Nhân viên ghi hộ — khách không dùng Zalo, hoặc gọi điện xin sửa.

    Cùng một cửa, khác đúng một chỗ: `nguon = "nhan_vien"`. Đó là cột để báo cáo gửi Ban lãnh đạo
    tách được hai loại số ra. Mục 6 của đề xuất giao nhóm khách không dùng Zalo cho sale đã bán —
    nên cửa này phải tồn tại, và phải để lại dấu vết là nó đã được dùng.
    """
    ra = []
    for d in (data.get("diem") or []):
        dt = (d.get("doi_tuong") or "").strip()
        if dt not in DG_DOI_TUONG: raise Gate("KHAO_SAT_NHAP", f"Mục không hợp lệ: {dt}")
        sao = d.get("diem")
        sao = int(sao) if sao not in (None, "") else None
        if sao is not None and (sao < 1 or sao > 5):
            raise Gate("KHAO_SAT_NHAP", "Điểm chỉ từ 1 đến 5 sao")
        did = d.get("doi_tuong_id") if dt in DG_CO_KHOA else None
        ten = ten_doi_tuong(db, dt, did, d.get("doi_tuong_ten") or "")
        x = DanhGiaSauTour(care_id=care.id, booking_id=care.booking_id, tour_id=care.tour_id,
                           doi_tuong=dt, doi_tuong_id=did, doi_tuong_ten=ten, diem=sao,
                           nhan_xet=(d.get("nhan_xet") or "").strip()[:2000],
                           nguon="nhan_vien", nguoi_ghi=u.username)
        db.add(x); ra.append(x)
    db.flush()
    R.audit(db, u.username, u.role, "ghi_danh_gia_ho", f"care:{care.id}",
            after={"so_muc": len(ra)})
    db.commit()
    return {"so_muc": len(ra)}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · BẢNG ĐIỂM
# ══════════════════════════════════════════════════════════════════════════════════════════════

def chua_tra_loi(db: Session, tu: date, den: date, vis: set | None = None) -> list[dict]:
    """Khách ĐÃ được mời mà chưa chấm — danh sách việc của mục 6 trong đề xuất.

    "Khách không dùng Zalo hoặc sai số điện thoại sẽ không nhận được tin. Nhóm này do sale đã bán
    tour hỏi thăm." Câu ấy chỉ thành việc làm được khi có một danh sách; không có danh sách thì nó
    là một câu trong tài liệu.

    Hai nhóm, và màn hình phải phân biệt được:
        · tin KHÔNG gửi được  → khách chưa từng biết là có ai hỏi
        · tin đã gửi mà chưa ai chấm → khách biết nhưng chưa trả lời

    `vis` là phạm vi người xem (từ `access.sales_ids_visible`): nhân viên chỉ thấy khách của mình.
    """
    from app.models.crm import ZaloMessage
    q = select(MaKhaoSat, CareTicket).join(CareTicket, CareTicket.id == MaKhaoSat.care_id).where(
        MaKhaoSat.dung_luc.is_(None),
        func.date(MaKhaoSat.tao_luc) >= tu, func.date(MaKhaoSat.tao_luc) <= den)
    ra = []
    for m, c in db.execute(q.order_by(MaKhaoSat.id.desc())).all():
        if vis is not None and c.owner_id not in vis: continue
        loi = db.execute(select(func.count()).select_from(ZaloMessage).where(
            ZaloMessage.booking_id == c.booking_id, ZaloMessage.purpose.in_(["cham_soc", "cham_soc_nhac"]),
            ZaloMessage.status == "loi")).scalar() or 0
        gui = db.execute(select(func.count()).select_from(ZaloMessage).where(
            ZaloMessage.booking_id == c.booking_id, ZaloMessage.purpose.in_(["cham_soc", "cham_soc_nhac"]),
            ZaloMessage.status == "da_gui")).scalar() or 0
        t = db.get(Tour, c.tour_id)
        nguoi = db.get(User, c.owner_id) if c.owner_id else None
        ra.append({"care_id": c.id, "khach": c.customer_name, "tour_ma": t.code if t else "",
                   "tour_ten": t.name if t else "", "nguoi_ban": nguoi.full_name if nguoi else "",
                   "moi_luc": m.tao_luc.isoformat(), "het_han": m.het_han.isoformat(),
                   "so_lan_mo": m.so_lan_mo, "tin_da_gui": gui, "tin_loi": loi,
                   # Chữ, không phải cờ: người đọc danh sách phải biết NGAY phải làm gì khác nhau
                   # với hai nhóm này, chứ không phải suy từ hai con số.
                   "tinh_trang": ("Không gửi được tin – khách chưa biết" if loi and not gui
                                  else "Đã gửi, khách chưa mở" if not m.so_lan_mo
                                  else "Khách đã mở nhưng chưa chấm")})
    return ra


def bang_diem(db: Session, doi_tuong: str, tu: date, den: date, chi_khach: bool = True) -> dict:
    """Cộng điểm theo từng đối tượng trong khoảng ngày.

    `chi_khach = True` (mặc định) chỉ cộng phần khách TỰ chấm. Đây là mặc định có chủ ý: khi không
    còn bộ phận chăm sóc riêng, người ghi hộ chính là người bị chấm — trộn hai loại số vào nhau
    thì bảng điểm không đo được ai. Màn hình vẫn mở được cả hai để so, nhưng phải bấm.
    """
    if doi_tuong not in DG_DOI_TUONG:
        raise Gate("BANG_DIEM", f"Không có loại đối tượng {doi_tuong}")
    # KHOÁ GỘP LÀ NGƯỜI, KHÔNG PHẢI TÊN — Đợt HD-DG2, 15/10/2026.
    #
    # Tên là ảnh chụp lúc ghi: hướng dẫn viên đổi tên trong hồ sơ thì mọi lượt chấm cũ vẫn mang
    # tên cũ, và gộp theo tên là tách một người làm hai dòng. Loại KHÔNG có khoá (`tour`,
    # `khach_san`, `an_uong`) thì `doi_tuong_id` luôn rỗng, nên chúng PHẢI gộp theo tên — gộp
    # theo id sẽ dồn mọi chuyến vào đúng một dòng.
    co_khoa = doi_tuong in DG_CO_KHOA
    khoa = DanhGiaSauTour.doi_tuong_id if co_khoa else DanhGiaSauTour.doi_tuong_ten
    # BA CON SỐ TRONG MỘT CÂU TRUY VẤN. Trước đợt này `so_luot_thap` chạy một câu RIÊNG lọc theo
    # một mình `doi_tuong_id`, trong khi `so_luot` gộp theo cặp (id, tên) — nên cùng một dòng nói
    # "2 lượt, trong đó 2 lượt thấp" khi nó chỉ có một lượt thấp. Gộp vào một câu không phải để
    # chạy nhanh hơn: để hai con số KHÔNG THỂ đếm theo hai khoá khác nhau được nữa.
    q = select(khoa, func.max(DanhGiaSauTour.tao_luc), func.count(DanhGiaSauTour.id),
               func.avg(DanhGiaSauTour.diem),
               func.sum(case((DanhGiaSauTour.diem <= 3, 1), else_=0))).where(
        DanhGiaSauTour.doi_tuong == doi_tuong,
        DanhGiaSauTour.diem.is_not(None),
        func.date(DanhGiaSauTour.tao_luc) >= tu,
        func.date(DanhGiaSauTour.tao_luc) <= den)
    if chi_khach: q = q.where(DanhGiaSauTour.nguon == "khach")
    rows = []
    for gt, _moi_nhat, so, tb, thap in db.execute(q.group_by(khoa)).all():
        did = gt if co_khoa else None
        # TÊN LẤY LÚC ĐỌC. Nhờ vậy những lượt chấm CŨ đã lỡ ghi nhãn chung tự hiện đúng tên người,
        # không cần một lệnh vá dữ liệu nào. Hồ sơ đã xoá thì lùi về tên ghi trong lượt gần nhất
        # chứ không bỏ trống — một dòng điểm không tên là một dòng không ai đối chiếu được.
        if co_khoa:
            lui = db.execute(select(DanhGiaSauTour.doi_tuong_ten).where(
                DanhGiaSauTour.doi_tuong == doi_tuong,
                DanhGiaSauTour.doi_tuong_id == did).order_by(
                DanhGiaSauTour.tao_luc.desc())).scalars().first() or ""
            ten = ten_doi_tuong(db, doi_tuong, did, lui)
        else:
            ten = gt or DG_DOI_TUONG[doi_tuong]
        rows.append({"id": did, "ten": ten, "so_luot": so,
                     "diem_tb": round(float(tb), 2) if tb is not None else None,
                     "so_luot_thap": int(thap or 0)})
    rows.sort(key=lambda r: (-(r["diem_tb"] or 0), -r["so_luot"]))
    return {"doi_tuong": doi_tuong, "ten_loai": DG_DOI_TUONG[doi_tuong],
            "tu": tu.isoformat(), "den": den.isoformat(), "chi_khach": chi_khach, "rows": rows,
            # In ra ngay cạnh bảng, không giấu trong mã: một bảng xếp hạng dựng trên mười lượt chấm
            # không phải là một bảng xếp hạng.
            "luu_y": "Điểm trung bình chỉ có nghĩa khi số lượt đủ lớn. Cột 'số lượt' đứng cạnh cột "
                     "điểm là để đọc hai con số cùng lúc, không phải để trang trí."}


def chi_so(db: Session, tu: date, den: date) -> dict:
    """Ba con số phải đứng cạnh nhau trong báo cáo tuần: ĐÃ GỬI · ĐÃ TRẢ LỜI · KHÔNG GỬI ĐƯỢC.

    Gọi điện thì "không nghe máy" là một kết quả có người ghi lại. Tin nhắn tự động thì "không trả
    lời" chỉ là một dòng trống — và một bảng chỉ in "điểm trung bình 4,6" là điểm của những người
    chịu trả lời, trong khi người bực nhất thường là người không buồn trả lời.
    """
    from app.models.crm import ZaloMessage
    def dem(q): return db.execute(q).scalar() or 0
    ky = (func.date(ZaloMessage.created_at) >= tu, func.date(ZaloMessage.created_at) <= den,
          ZaloMessage.purpose == "cham_soc")
    da_gui = dem(select(func.count()).select_from(ZaloMessage).where(*ky, ZaloMessage.status == "da_gui"))
    loi = dem(select(func.count()).select_from(ZaloMessage).where(*ky, ZaloMessage.status == "loi"))
    cho = dem(select(func.count()).select_from(ZaloMessage).where(*ky, ZaloMessage.status.in_(["cho_gui", "cho_cau_hinh"])))
    mo = dem(select(func.count()).select_from(MaKhaoSat).where(
        func.date(MaKhaoSat.tao_luc) >= tu, func.date(MaKhaoSat.tao_luc) <= den,
        MaKhaoSat.so_lan_mo > 0))
    xong = dem(select(func.count()).select_from(MaKhaoSat).where(
        func.date(MaKhaoSat.tao_luc) >= tu, func.date(MaKhaoSat.tao_luc) <= den,
        MaKhaoSat.dung_luc.is_not(None)))
    return {"tu": tu.isoformat(), "den": den.isoformat(),
            "tin_da_gui": da_gui, "tin_loi": loi, "tin_cho": cho,
            "khach_mo": mo, "khach_tra_loi": xong,
            # Mẫu số là TIN ĐÃ GỬI, không phải tin đã tạo: tin không gửi được thì khách không có
            # cơ hội trả lời, và tính họ vào mẫu số là tự hạ điểm mình bằng một lỗi kỹ thuật.
            "ty_le_tra_loi": round(xong / da_gui, 3) if da_gui else None,
            "luu_y": "Tỷ lệ trả lời tính trên số tin ĐÃ GỬI THÀNH CÔNG. Số tin lỗi đứng riêng — đó "
                     "là nhóm khách không nhận được tin, và nhóm ấy phải có người gọi."}
