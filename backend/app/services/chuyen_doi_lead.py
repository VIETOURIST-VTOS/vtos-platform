"""Chuyển đổi và phối hợp Sales — nhóm 2.6. Marketing giao lead xong thì Sales xử lý tới đâu.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA CÂU HỎI, VÀ VÌ SAO KHÔNG CÂU NÀO TRẢ LỜI ĐƯỢC BẰNG BÁO CÁO CHUYỂN ĐỔI ĐÃ CÓ
═══════════════════════════════════════════════════════════════════════════════════════════════
`leads.conversion_report()` trả lời "kỳ lead X chốt được bao nhiêu phần trăm" — một bảng chéo kỳ
lead × tháng khởi hành. Ba câu của nhóm 2.6 khác hẳn, và cùng hỏi về QUÃNG GIỮA:

  2.6.1  Lead chốt SAU BAO LÂU — 30, 60 hay 90 ngày. Tỷ lệ chốt không nói được điều này: hai kỳ
         cùng 20% mà một kỳ chốt trong tuần đầu, kỳ kia lê ba tháng, là hai tình trạng khác nhau
         hoàn toàn đối với người phải xếp lịch chăm sóc.
  2.6.2  Lead nào đang NẰM IM và ai đang giữ. Báo cáo chuyển đổi nhìn về quá khứ đã khép; câu này
         nhìn vào việc đang dở, và nó là câu duy nhất còn sửa được bằng hành động hôm nay.
  2.6.3  MẤT VÌ LÝ DO GÌ. Tỷ lệ chốt 20% chỉ nói 80% kia không chốt; mất vì giá và mất vì không
         liên lạc được là hai bài toán khác nhau, một cái của Kinh doanh, một cái của Marketing.

DÙNG LẠI MÁY SẴN CÓ, KHÔNG DỰNG MÁY THỨ HAI. Toàn bộ phép tính hạn xử lý ở đây gọi
`services/leads.han_hieu_luc`, `qua_han`, `gio_han` — không có bản chép nào. Định nghĩa "quá hạn"
đã được dọn một lần ngày 18/9/2026 để chỗ đếm và chỗ đánh dấu dùng chung một luật; chép nó sang
đây là dựng lại đúng cái vừa dọn xong.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN CHỖ DỄ NÓI DỐI BẰNG SỐ, ĐÃ CHẶN SẴN
═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT — "ĐÃ CHỐT NHƯNG KHÔNG RÕ NGÀY" KHÔNG ĐƯỢC NHÉT VÀO MỐC NÀO. Phép đối chiếu theo số điện
thoại gắn `booking_id` cho lead, nhưng `converted_at` có thể rỗng ở dòng nạp cũ. Lúc ấy ta biết
lead đã chốt mà không biết chốt lúc nào. Nhét nó vào mốc ">90 ngày" cho gọn là bịa; xếp vào "≤30"
cho đẹp lại càng bịa. Nó có ngăn riêng `da_chot_khong_ro_ngay`, và ngăn ấy hiện lên màn hình.

HAI — LEAD CHƯA CHỐT KHÁC LEAD ĐÃ MẤT. Một lead còn đang chăm sóc mà chưa chốt thì mốc 90 ngày
của nó chưa kết thúc; gộp nó với lead đã đánh dấu "không chốt" là kết luận thay cho tương lai.
Hai ngăn riêng: `chua_chot_con_mo` và `da_mat`.

BA — TỶ LỆ CHỐT Ở ĐÂY KHÔNG PHẢI `ty_le_chot_overview`. Tệp này đếm theo KỲ PHÁT SINH LEAD và
chỉ nhìn dấu `booking_id`, nên con số cộng dồn theo mốc; quy tắc `overview-v1` mà Chủ tịch ký
14/9/2026 mới là tỷ lệ chính thức của phòng Marketing. Mọi bản trả về đều kèm `co_so` nói rõ điều
ấy, để không ai mang con số ở đây ra đối chọi với con số ở màn hình kia.

BỐN — CHƯA AI CHẠY ĐỐI CHIẾU THÌ KHÔNG XÁC ĐỊNH, KHÔNG PHẢI 0%. Cùng một lẽ đã ghi trong
`conversion_report`: 0% đọc là "chạy mà không ra khách", còn chưa xác định đọc là "chưa ai so sổ".
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.models.crm import Lead, LeadBanGiao
from app.services import leads as LD
from app.services import rules as R
from app.services.intake_marketing import LY_DO_MAT

# Mốc ngày của mục 2.6.1. Thứ tự trong tuple LÀ thứ tự cột trên màn hình; đổi ở đây thì màn hình
# đổi theo, không có bản chép thứ hai bên giao diện.
MOC_NGAY = (30, 60, 90)

# Ngăn của một lead trong bảng chuyển đổi. Sáu ngăn RỜI NHAU và cộng lại bằng toàn bộ lead của kỳ
# — `test_sau_ngan_roi_nhau_va_cong_du` canh đúng điều đó.
NGAN = ("trong_30", "trong_60", "trong_90", "tren_90",
        "da_chot_khong_ro_ngay", "chua_chot_con_mo", "da_mat")

VIEC_BAN_GIAO = {"giao": "Giao lần đầu", "giao_lai": "Chuyển người khác", "doi_han": "Đổi hạn xử lý"}


def _moc_cua(l: Lead) -> str:
    """Lead này rơi vào ngăn nào. Xem bốn chỗ dễ nói dối ở đầu tệp."""
    if not l.booking_id:
        return "da_mat" if l.status == "mat" else "chua_chot_con_mo"
    # Đã chốt. Biết chốt lúc nào không?
    # KHÔNG kiểm `received_at` rỗng ở đây, và đó là chủ ý: cột ấy NOT NULL ở cơ sở dữ liệu, nên
    # nhánh ấy là mã chết — mã chết làm người đọc sau tưởng trường hợp đó có thật và viết thêm một
    # tầng xử lý nữa quanh nó. Ràng buộc được canh bằng `test_ngay_vao_so_khong_duoc_rong`; nếu
    # một ngày ai đó nới cột ấy ra, phép thử gãy và người nới phải quyết lead không có ngày vào sổ
    # thì rơi vào ngăn nào.
    if not l.converted_at:
        return "da_chot_khong_ro_ngay"
    ngay = (l.converted_at - l.received_at).days
    if ngay < 0:
        # Chốt TRƯỚC khi lead vào sổ: dòng nạp ngược ngày. Không sửa hộ, không đoán — xếp vào ngăn
        # "không rõ ngày" để nó hiện ra và có người đi soát.
        return "da_chot_khong_ro_ngay"
    for m in MOC_NGAY:
        if ngay <= m:
            return f"trong_{m}"
    return "tren_90"


def chuyen_doi_theo_moc(db, ky: str, kenh: str = "") -> dict:
    """2.6.1 — lead của kỳ này chốt sau bao lâu.

    `ky` là KỲ PHÁT SINH LEAD (`Lead.lead_month`), không phải tháng khởi hành tour. Đây là điểm
    khác căn bản với bảng chéo của `conversion_report`, và là lý do hai bảng không so thẳng được
    với nhau.
    """
    q = select(Lead).where(Lead.lead_month == ky)
    if kenh:
        q = q.where(Lead.channel == kenh)
    ds = list(db.execute(q).scalars())

    dem = {k: 0 for k in NGAN}
    theo_kenh: dict[str, dict] = {}
    for l in ds:
        ngan = _moc_cua(l)
        dem[ngan] += 1
        k = theo_kenh.setdefault(l.channel or "(không ghi)",
                                 {"kenh": l.channel or "(không ghi)", "tong": 0,
                                  **{x: 0 for x in NGAN}})
        k["tong"] += 1; k[ngan] += 1

    tong = len(ds)
    da_chot = sum(dem[k] for k in ("trong_30", "trong_60", "trong_90", "tren_90",
                                   "da_chot_khong_ro_ngay"))
    # Chưa ai chạy đối chiếu thì KHÔNG XÁC ĐỊNH — xem chỗ dễ nói dối số BỐN ở đầu tệp.
    da_doi_chieu = any(l.booking_id or l.converted_at for l in ds)

    # Cộng dồn: "trong 60 ngày" nghĩa là gồm cả phần chốt trong 30. Đây là cách người đọc hiểu một
    # con số 60 ngày, nên tính sẵn ở đây chứ không để màn hình tự cộng — hai nơi cộng là hai nơi
    # cộng khác nhau.
    cong_don = {}
    chay = 0
    for m in MOC_NGAY:
        chay += dem[f"trong_{m}"]
        cong_don[f"den_{m}"] = chay

    return {
        "ky": ky, "kenh": kenh or "tat_ca",
        "tong_lead": tong,
        "theo_ngan": dem,
        "cong_don": cong_don,
        "da_chot": da_chot,
        "ty_le_chot": (da_chot / tong) if (tong and da_doi_chieu) else None,
        "da_doi_chieu": da_doi_chieu,
        "canh_bao_chua_doi_chieu": ("" if da_doi_chieu else
                                    "Kỳ này chưa ai chạy đối chiếu lead với booking, nên tỷ lệ là "
                                    "CHƯA XÁC ĐỊNH chứ không phải 0%. Chạy đối chiếu ở màn hình "
                                    "Khách hàng tiềm năng rồi xem lại."),
        "co_so": "Đếm theo KỲ PHÁT SINH LEAD, mốc ngày tính từ lúc lead vào sổ đến lúc chốt. "
                 "KHÁC tỷ lệ chốt chính thức của Marketing (quy tắc overview-v1 Chủ tịch ký "
                 "14/9/2026) — đừng mang hai con số ra đối chọi nhau.",
        "theo_kenh": sorted(theo_kenh.values(), key=lambda x: -x["tong"]),
        "ten_ngan": {
            "trong_30": "Chốt trong 30 ngày", "trong_60": "Chốt 31–60 ngày",
            "trong_90": "Chốt 61–90 ngày", "tren_90": "Chốt sau 90 ngày",
            "da_chot_khong_ro_ngay": "Đã chốt, không rõ ngày",
            "chua_chot_con_mo": "Chưa chốt, còn đang chăm sóc", "da_mat": "Đã đánh dấu không chốt"},
    }


def ton_dong(db, bay_gio: datetime | None = None) -> dict:
    """2.6.2 — lead đang nằm im, ai giữ, quá hạn bao lâu.

    Phép tính hạn gọi thẳng `services/leads`: `gio_han` đọc tham số P.TGĐ ký, `han_hieu_luc` chọn
    giữa hạn ĐÃ HẸN và hạn THEO LUẬT rồi nói ra đã chọn cái nào, `qua_han` quyết. Không có bản
    chép nào ở đây — định nghĩa quá hạn đã được dọn về một mối ngày 18/9/2026.
    """
    gio = LD.gio_han(db)
    now = bay_gio or datetime.now()
    ds = list(db.execute(select(Lead).where(Lead.status.in_(("moi", "dang_cham_soc")))).scalars())

    from app.models.core import User
    ten_nguoi = {u.id: u.full_name for u in db.execute(select(User)).scalars()}

    rows, theo_nguoi = [], {}
    for l in ds:
        han, nguon_han = LD.han_hieu_luc(l, gio)
        tre = LD.qua_han(l, gio, now)
        tuoi = (now - l.received_at).days
        nguoi = ten_nguoi.get(l.sales_id) or "(chưa giao ai)"
        rows.append({
            "lead_id": l.id, "ma_lead": l.ma_lead or "", "ten": l.name, "phone": l.phone,
            "kenh": l.channel, "trang_thai": l.status, "nguoi_giu": nguoi,
            "vao_so": l.received_at.isoformat(),
            "han": han.isoformat() if han else "",
            "nguon_han": nguon_han,        # da_hen | theo_quy_tac — xem leads.han_hieu_luc
            "qua_han": tre, "so_ngay_nam_im": tuoi,
            "cham_lan_cuoi": l.last_contact_at.isoformat() if l.last_contact_at else "",
        })
        o = theo_nguoi.setdefault(nguoi, {"nguoi": nguoi, "tong": 0, "qua_han": 0, "chua_cham": 0})
        o["tong"] += 1
        o["qua_han"] += 1 if tre else 0
        o["chua_cham"] += 0 if LD.da_xu_ly(l) else 1

    # Tuổi lead: chia theo cùng bộ mốc với 2.6.1, để hai màn hình không dùng hai bộ mốc khác nhau.
    tuoi_ngan = {f"den_{m}": 0 for m in MOC_NGAY}
    tuoi_ngan["tren_90"] = 0
    for r in rows:
        t = r["so_ngay_nam_im"]
        for m in MOC_NGAY:
            if t <= m:
                tuoi_ngan[f"den_{m}"] += 1
                break
        else:
            tuoi_ngan["tren_90"] += 1

    # DANH SÁCH NGƯỜI NHẬN TRẢ LUÔN TỪ CỬA NÀY, không để màn hình đi hỏi `/api/v1/users`.
    #
    # Gọi sang nhóm khác thì phép thử khai quyền bắt khai nhóm ấy, và khai là cấp CẢ nhóm tài
    # khoản cho mọi vai mở được màn hình này — trong đó có `nv_kd`. Bài học đã trả giá ở TC-73,
    # đúng cùng một chỗ và đúng cùng một cách.
    #
    # Chỉ trả ba ô cần cho một ô chọn: id, tên, tên đăng nhập. Không trả vai, không trả trạng
    # thái, không trả gì thêm — một danh sách tài khoản đầy đủ là một danh sách tài khoản.
    nguoi_nhan = [{"id": u.id, "ho_ten": u.full_name, "tai_khoan": u.username}
                  for u in db.execute(select(User)).scalars()
                  if u.active and u.role in ("nv_kd", "tn_kd", "tp_kd")]

    return {
        "tinh_den": now.isoformat(timespec="seconds"),
        "nguoi_nhan": sorted(nguoi_nhan, key=lambda x: x["ho_ten"] or ""),
        "gio_han_da_ky": gio,
        "tong_dang_mo": len(rows),
        "tong_qua_han": sum(1 for r in rows if r["qua_han"]),
        "theo_nguoi": sorted(theo_nguoi.values(), key=lambda x: (-x["qua_han"], -x["tong"])),
        "theo_tuoi": tuoi_ngan,
        "co_so": "Hạn xử lý lấy theo services/leads: lead có hạn ĐÃ HẸN thì so với hạn ấy, không "
                 "có thì lấy lúc vào sổ cộng số giờ P.TGĐ đã ký. Lead không biết vào sổ lúc nào "
                 "thì KHÔNG kết luận quá hạn.",
        "rows": sorted(rows, key=lambda x: (not x["qua_han"], -x["so_ngay_nam_im"]))[:300],
    }


def ly_do_mat(db, ky: str = "") -> dict:
    """2.6.3 — mất vì lý do gì, và bao nhiêu người quay lại sau khi đã đánh dấu mất."""
    q = select(Lead).where(Lead.status == "mat")
    if ky:
        q = q.where(Lead.lead_month == ky)
    ds = list(db.execute(q).scalars())

    dem: dict[str, int] = {}
    chua_ghi = []
    for l in ds:
        ma = (l.ly_do_mat or "").strip()
        if not ma:
            chua_ghi.append({"lead_id": l.id, "ma_lead": l.ma_lead or "", "ten": l.name,
                             "phone": l.phone, "kenh": l.channel})
            continue
        dem[ma] = dem.get(ma, 0) + 1

    # TÁI CHĂM SÓC: người đã đánh dấu mất mà SỐ ĐIỆN THOẠI ẤY sau đó chốt ở một dòng lead khác.
    # Đếm theo SỐ ĐIỆN THOẠI, đúng đơn vị "một người" đã chốt 14/9/2026 — và nói rõ ra, vì hai
    # người dùng chung một số sẽ đếm thành một, còn một người đổi số đếm thành hai.
    sdt_mat = {l.phone for l in ds if l.phone}
    quay_lai = set()
    if sdt_mat:
        for l in db.execute(select(Lead).where(Lead.phone.in_(list(sdt_mat)),
                                               Lead.booking_id.is_not(None))).scalars():
            quay_lai.add(l.phone)

    return {
        "ky": ky or "tat_ca",
        "tong_mat": len(ds),
        "theo_ly_do": sorted(
            [{"ma": k, "ten": LY_DO_MAT.get(k, k), "so_lead": v} for k, v in dem.items()],
            key=lambda x: -x["so_lead"]),
        "chua_ghi_ly_do": {"so_lead": len(chua_ghi), "rows": chua_ghi[:200]},
        "tai_cham_soc": {
            "so_sdt_quay_lai": len(quay_lai),
            "tren_tong_sdt_mat": len(sdt_mat),
            "co_so": "Đếm theo SỐ ĐIỆN THOẠI đã chuẩn hoá, không phải theo dòng lead: hai người "
                     "dùng chung một số đếm thành một, một người đổi số đếm thành hai.",
        },
        "danh_muc_ly_do": LY_DO_MAT,
    }


def lich_su_ban_giao(db, lead_id: int) -> list[dict]:
    """Sổ bàn giao của một lead. Bảng `lead_ban_giao` đã có dữ liệu từ đường nạp Marketing nhưng
    trước vòng này KHÔNG màn hình nào đọc nó — dữ liệu được ghi mà không ai xem được."""
    ds = db.execute(select(LeadBanGiao).where(LeadBanGiao.lead_id == lead_id)
                    .order_by(LeadBanGiao.luc)).scalars()
    return [{"id": x.id, "viec": x.viec, "viec_ten": VIEC_BAN_GIAO.get(x.viec, x.viec),
             "tu_nguoi": x.tu_nguoi or "", "den_nguoi": x.den_nguoi or "",
             "han_cu": x.han_cu.isoformat() if x.han_cu else "",
             "han_moi": x.han_moi.isoformat() if x.han_moi else "",
             "ly_do": x.ly_do or "", "boi": x.boi or "",
             "luc": x.luc.isoformat(timespec="seconds") if x.luc else ""} for x in ds]


def ban_giao(db, boi, lead_id: int, den_nguoi_id: int | None = None,
             han_moi: date | None = None, ly_do: str = "") -> dict:
    """CỬA GHI: chuyển lead sang người khác, hoặc đổi hạn xử lý.

    Hành động tự nhiên của màn hình "lead tồn đọng": nhìn thấy một lead nằm im hai tháng trong tay
    một người thì việc cần làm là chuyển nó đi hoặc hẹn lại hạn — ngay tại chỗ nhìn thấy nó, chứ
    không phải nhớ mã rồi đi sang màn hình khác.

    GHI VÀO `lead_ban_giao`, bảng đã có sẵn và đã có dữ liệu từ đường nạp tệp. Dựng một bảng nhật
    ký thứ hai cho cùng một việc là cách chắc chắn để sau này lịch sử của một lead nằm ở hai chỗ và
    không chỗ nào đủ.
    """
    from app.models.core import User

    l = db.get(Lead, lead_id)
    if l is None:
        raise ValueError(f"Không có lead id {lead_id}.")
    if not (ly_do or "").strip():
        raise ValueError("Chuyển lead hoặc đổi hạn thì phải ghi lý do — người nhận cần biết vì "
                         "sao nó đến tay mình, và cuối kỳ còn tra lại được.")
    if den_nguoi_id is None and han_moi is None:
        raise ValueError("Phải chọn người nhận mới hoặc hạn mới — không có cái nào thì không có "
                         "gì để bàn giao.")

    nguoi_cu = None
    if l.sales_id:
        u_cu = db.get(User, l.sales_id)
        nguoi_cu = u_cu.username if u_cu else None

    # CHỤP TRẠNG THÁI TRƯỚC KHI SỬA. Đọc `l.han_xu_ly` sau khi đã gán hạn mới thì cột "before" của
    # nhật ký ghi lại đúng trạng thái SAU — nhật ký nói dối còn tệ hơn không có nhật ký. Đây là lỗi
    # đã bắt được một lần ở cửa gộp tài khoản, nên ghi rõ ra đây.
    truoc = {"nguoi": nguoi_cu or "",
             "han": l.han_xu_ly.isoformat() if l.han_xu_ly else ""}

    ghi = []
    if den_nguoi_id is not None:
        moi = db.get(User, den_nguoi_id)
        if moi is None:
            raise ValueError(f"Không có tài khoản id {den_nguoi_id}.")
        if not moi.active:
            raise ValueError(f"Tài khoản {moi.username} đang bị khoá, không giao lead cho được.")
        if l.sales_id == den_nguoi_id:
            raise ValueError("Lead đang ở chính người này rồi.")
        db.add(LeadBanGiao(lead_id=l.id, viec=("giao_lai" if nguoi_cu else "giao"),
                           tu_nguoi=nguoi_cu, den_nguoi=moi.username,
                           ly_do=ly_do.strip(), boi=boi.username, luc=datetime.now()))
        l.sales_id = den_nguoi_id
        ghi.append("giao_lai" if nguoi_cu else "giao")

    if han_moi is not None:
        han_cu = l.han_xu_ly
        if han_cu == han_moi:
            raise ValueError("Hạn mới trùng hạn đang có.")
        db.add(LeadBanGiao(lead_id=l.id, viec="doi_han", tu_nguoi=nguoi_cu,
                           den_nguoi=nguoi_cu, han_cu=han_cu, han_moi=han_moi,
                           ly_do=ly_do.strip(), boi=boi.username, luc=datetime.now()))
        l.han_xu_ly = han_moi
        ghi.append("doi_han")

    R.audit(db, boi.username, boi.role, "ban_giao_lead", f"lead:{l.id}",
            before=truoc,
            after={"viec": ghi, "ly_do": ly_do.strip(),
                   "nguoi": (db.get(User, l.sales_id).username if l.sales_id else ""),
                   "han": l.han_xu_ly.isoformat() if l.han_xu_ly else ""})
    return {"da_ghi": True, "lead_id": l.id, "viec": ghi,
            "message": "Đã ghi " + ", ".join(VIEC_BAN_GIAO.get(v, v).lower() for v in ghi)}


def ghi_ly_do_mat(db, boi, lead_id: int, ma_ly_do: str, ghi_chu: str = "") -> dict:
    """CỬA GHI: điền lý do cho một lead đã đánh dấu không chốt mà chưa ai ghi vì sao.

    CHỈ ĐIỀN CHỖ TRỐNG, cùng một nếp với cửa gắn nguồn của nhóm 2.7: sửa một lý do ĐÃ GHI là đổi
    câu trả lời cũ của người khác, việc ấy phải đi qua màn hình Khách hàng tiềm năng nơi có nhật
    ký sửa đầy đủ.
    """
    l = db.get(Lead, lead_id)
    if l is None:
        raise ValueError(f"Không có lead id {lead_id}.")
    if l.status != "mat":
        raise ValueError("Chỉ ghi lý do cho lead đã đánh dấu không chốt. Lead còn đang chăm sóc "
                         "thì chưa có lý do nào để ghi.")
    if (l.ly_do_mat or "").strip():
        raise ValueError(f"Lead này đã có lý do ({LY_DO_MAT.get(l.ly_do_mat, l.ly_do_mat)}). Cửa "
                         "này chỉ điền chỗ TRỐNG; sửa lý do đã ghi phải làm ở màn hình Khách hàng "
                         "tiềm năng.")
    if ma_ly_do not in LY_DO_MAT:
        raise ValueError(f"Lý do không hợp lệ: {ma_ly_do!r}. Chỉ có {', '.join(LY_DO_MAT)}.")
    if ma_ly_do == "khac" and not (ghi_chu or "").strip():
        raise ValueError("Chọn 'Lý do khác' thì phải ghi rõ ở ghi chú — nếu không thì ô ấy sẽ "
                         "thành nơi chứa mọi thứ không ai phân loại nữa.")

    l.ly_do_mat = ma_ly_do
    if (ghi_chu or "").strip():
        l.note = ((l.note or "") + "\n" + ghi_chu.strip()).strip()
    R.audit(db, boi.username, boi.role, "ghi_ly_do_mat_lead", f"lead:{l.id}",
            before={"ly_do_mat": ""}, after={"ly_do_mat": ma_ly_do, "ghi_chu": ghi_chu.strip()})
    return {"da_ghi": True, "lead_id": l.id,
            "message": f"Đã ghi lý do: {LY_DO_MAT[ma_ly_do]}"}
