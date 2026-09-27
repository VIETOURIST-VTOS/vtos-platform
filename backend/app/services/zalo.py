"""Kết nối Zalo: (1) OA – nhắn khách đã quan tâm OA (user_id) qua Open API v3; (2) ZNS – gửi mẫu đã duyệt theo SĐT (84…);
(3) webhook OA nhận follow / tin nhắn / chia sẻ SĐT → tạo lead kênh 'Zalo OA'. Không có token → tin xếp 'chờ cấu hình' để gửi tay/sau."""
import json, hmac, hashlib, urllib.request, urllib.parse
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.crm import Lead, ZaloMessage, ZaloOaToken
from app.models.core import Alert
from app.services import rules as R

OA_API = "https://openapi.zalo.me/v3.0/oa"
ZNS_API = "https://business.openapi.zalo.me/message/template"
OAUTH = "https://oauth.zaloapp.com/v4/oa/access_token"


def norm_phone(p: str) -> str:
    d = "".join(ch for ch in str(p or "") if ch.isdigit())
    if d.startswith("84") and len(d) >= 11: d = "0" + d[2:]
    if len(d) == 9 and not d.startswith("0"): d = "0" + d
    return d[:15]


def intl(p: str) -> str:
    d = norm_phone(p)
    return "84" + d[1:] if d.startswith("0") else d


# ============================== KHO TOKEN ==============================
# Token sống trong cơ sở dữ liệu, KHÔNG phải trong biến môi trường. Lý do đầy đủ ghi ở docstring của
# models.crm.ZaloOaToken; tóm tắt: refresh token của Zalo đổi mới sau mỗi lần dùng, giữ trong bộ nhớ thì
# lần khởi động lại kế tiếp là mất.

def kho(db: Session) -> ZaloOaToken:
    """Dòng token duy nhất; chưa có thì tạo, và nạp sẵn từ biến môi trường nếu lần đầu."""
    r = db.execute(select(ZaloOaToken).order_by(ZaloOaToken.id.desc())).scalars().first()
    if r is None:
        r = ZaloOaToken(access_token=settings.ZALO_OA_ACCESS_TOKEN or "",
                        refresh_token=settings.ZALO_OA_REFRESH_TOKEN or "", cap_boi="bien_moi_truong")
        db.add(r); db.flush()
    return r


def token(db: Session) -> str:
    """Access token đang dùng. Ưu tiên cơ sở dữ liệu; biến môi trường chỉ là mồi cho lần chạy đầu."""
    return kho(db).access_token or settings.ZALO_OA_ACCESS_TOKEN or ""


def _luu(db: Session, j: dict, boi: str) -> str:
    """Ghi cặp token mới. Zalo trả refresh token MỚI mỗi lần – ghi đè, đừng giữ cái cũ."""
    r = kho(db)
    if not j.get("access_token"): return ""
    r.access_token = j["access_token"]
    if j.get("refresh_token"): r.refresh_token = j["refresh_token"]
    try: r.het_han_luc = datetime.now() + timedelta(seconds=int(j.get("expires_in") or 90000))
    except (TypeError, ValueError): r.het_han_luc = datetime.now() + timedelta(hours=25)
    r.lan_lam_moi = datetime.now(); r.so_lan_lam_moi += 1; r.loi_cuoi = ""; r.cap_boi = boi
    # giữ cho lần gửi ngay sau đó trong cùng tiến trình không phải đọc lại
    settings.ZALO_OA_ACCESS_TOKEN = r.access_token
    settings.ZALO_OA_REFRESH_TOKEN = r.refresh_token
    db.commit()
    return r.access_token


def _bao_hong(db: Session, ly_do: str) -> None:
    """Token chết thì PHẢI có người biết. Không có dòng này thì Zalo OA ngừng chạy trong im lặng."""
    r = kho(db); r.loi_cuoi = ly_do[:500]
    co = db.execute(select(Alert).where(Alert.kind == "zalo_token_hong", Alert.resolved == False)).scalars().first()
    if co is None:
        db.add(Alert(kind="zalo_token_hong", level="red", ref="zalo_oa",
                     message=f"Zalo OA mất quyền gửi/nhận tin: {ly_do[:200]}. Cần vào Zalo Developers uỷ quyền lại cho ứng dụng VTOS.",
                     to_roles="cntt,ptgd_mkt,tgd,chutich"))
    db.commit()


def configured(db: Session | None = None) -> dict:
    tk = token(db) if db is not None else settings.ZALO_OA_ACCESS_TOKEN
    rf = (kho(db).refresh_token if db is not None else settings.ZALO_OA_REFRESH_TOKEN)
    return {"oa": bool(tk), "zns_templates": dict(x.split(":", 1) for x in settings.ZALO_ZNS_TEMPLATES.split(",") if ":" in x), "webhook": bool(settings.ZALO_OA_SECRET_KEY),
            "refresh": bool(rf and settings.ZALO_APP_SECRET)}


def _post(url: str, body: dict, token: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "access_token": token}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _goi_oauth(body: dict) -> dict:
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(OAUTH, data=data, headers={"Content-Type": "application/x-www-form-urlencoded",
                                                            "secret_key": settings.ZALO_APP_SECRET}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


PERMISSION = "https://oauth.zaloapp.com/v4/oa/permission"
# Đường Zalo gọi ngược về sau khi người quản trị bấm Đồng ý. Phải nằm trong domain ĐÃ XÁC THỰC ở
# Zalo Developers, nếu không Zalo từ chối ngay ở bước mở trang.
TRA_VE = "https://vtos.infinitytours.org/api/v1/zalo/uy-quyen/tra-ve"


def duong_uy_quyen(db: Session, boi: str = "") -> tuple[str, str]:
    """Dựng đường cấp quyền kèm mã chống giả mạo dùng một lần."""
    import secrets
    if not settings.ZALO_APP_ID:
        raise ValueError("Chưa khai ZALO_APP_ID trên máy chủ")
    ma = secrets.token_urlsafe(24)
    r = kho(db); r.ma_chong_gia = ma; r.cap_boi = boi or r.cap_boi
    db.commit()
    q = urllib.parse.urlencode({"app_id": settings.ZALO_APP_ID, "redirect_uri": TRA_VE, "state": ma})
    return f"{PERMISSION}?{q}", ma


def kiem_ma_chong_gia(db: Session, ma: str) -> bool:
    """Đúng một lần: khớp thì xoá ngay, để một mã không dùng lại được."""
    r = kho(db)
    if not r.ma_chong_gia or not ma or ma != r.ma_chong_gia: return False
    r.ma_chong_gia = ""; db.commit()
    return True


def doi_ma_uy_quyen(db: Session, ma: str, boi: str = "") -> dict:
    """Đổi mã uỷ quyền (oauth_code) lấy cặp token đầu tiên. Chạy đúng một lần, sau khi người có quyền
    quản trị OA bấm Đồng ý trên trang cấp quyền của Zalo. Mã sống vài phút và dùng một lần."""
    if not (settings.ZALO_APP_ID and settings.ZALO_APP_SECRET):
        raise ValueError("Chưa khai ZALO_APP_ID / ZALO_APP_SECRET trên máy chủ")
    j = _goi_oauth({"code": ma, "app_id": settings.ZALO_APP_ID, "grant_type": "authorization_code"})
    if not j.get("access_token"):
        _bao_hong(db, f"Đổi mã uỷ quyền thất bại: {json.dumps(j, ensure_ascii=False)[:300]}")
        raise ValueError(f"Zalo từ chối mã uỷ quyền: {j.get('error_name') or j.get('error') or j}")
    _luu(db, j, boi or "uy_quyen")
    return {"ok": True, "het_han_luc": str(kho(db).het_han_luc), "co_refresh": bool(kho(db).refresh_token)}


def refresh_token(db: Session) -> str:
    """Đổi refresh token lấy access token mới (access sống 25 giờ). Trả access token mới hoặc ''.

    Token mới ghi thẳng xuống cơ sở dữ liệu. Zalo trả về refresh token MỚI và vô hiệu hoá cái vừa dùng,
    nên không ghi lại là lần khởi động sau hệ thống cầm một chuỗi đã chết.
    """
    r = kho(db)
    rf = r.refresh_token or settings.ZALO_OA_REFRESH_TOKEN
    if not (rf and settings.ZALO_APP_ID and settings.ZALO_APP_SECRET):
        _bao_hong(db, "Không có refresh token hoặc chưa khai app_id/app_secret"); return ""
    try:
        j = _goi_oauth({"refresh_token": rf, "app_id": settings.ZALO_APP_ID, "grant_type": "refresh_token"})
    except Exception as ex:
        _bao_hong(db, f"Gọi Zalo để làm mới token lỗi: {str(ex)[:200]}"); return ""
    if not j.get("access_token"):
        _bao_hong(db, f"Zalo từ chối làm mới token: {json.dumps(j, ensure_ascii=False)[:300]}"); return ""
    return _luu(db, j, "tu_lam_moi")


def send_oa_text(db: Session, uid: str, text: str) -> dict:
    return _post(f"{OA_API}/message/cs", {"recipient": {"user_id": uid}, "message": {"text": text[:2000]}}, token(db))


def send_zns(db: Session, phone: str, template_id: str, params: dict) -> dict:
    return _post(ZNS_API, {"phone": intl(phone), "template_id": str(template_id), "template_data": params, "tracking_id": f"vtos-{datetime.now():%Y%m%d%H%M%S}"}, token(db))


def uid_theo_sdt(db: Session, phone: str) -> str:
    """UID Zalo OA của một số điện thoại — rỗng nếu chưa ai từng nhắn vào OA từ số ấy.

    MỘT CHỖ TRA DUY NHẤT. Trước 27/9/2026 phép tra này nằm trong `api/v1/crm.py::zalo_send` và chỉ
    ở đó, nên mọi đường gửi TỰ ĐỘNG (robot chăm sóc) không hề tra uid: chúng gọi `queue` không kèm
    `zalo_uid`, mà `queue` chọn kênh theo đúng ô ấy — nên mọi tin robot đều rơi xuống ZNS, kể cả
    gửi cho khách ĐÃ quan tâm OA. Đo ngày 27/9: 200 tin mời chấm điểm nằm chờ mẫu ZNS trong khi
    token OA vẫn sống.

    Đưa ra đây để đường tay và đường robot dùng chung một luật. Hai luật tra uid ở hai nơi thì rồi
    sẽ lệch, và chỗ lệch ấy im lặng: tin vẫn đi, chỉ là đi sai kênh.
    """
    p = norm_phone(phone or "")
    if not p:
        return ""
    r = db.execute(select(Lead).where(Lead.phone == p, Lead.zalo_uid != "")).scalars().first()
    return r.zalo_uid if r else ""


def queue(db: Session, actor: str, *, phone: str = "", zalo_uid: str = "", text: str = "", purpose: str = "", template: str = "", params: dict | None = None, lead_id: int | None = None, booking_id: int | None = None, send_now: bool = True, gui_tu_luc: datetime | None = None) -> ZaloMessage:
    """Tạo tin và gửi ngay nếu có cấu hình: có uid → OA text; không có uid nhưng có mẫu ZNS cho mục đích → ZNS theo SĐT; còn lại → chờ cấu hình.

    `gui_tu_luc` là GIỜ HẸN: tin nằm im trong hàng đợi cho tới lúc ấy. Rỗng = gửi ngay, đúng như
    trước, nên mọi lời gọi cũ không đổi hành vi. Hẹn giờ thì `send_now` tự tắt — hẹn mà vẫn gửi
    ngay là một cái hẹn không có tác dụng, và loại lỗi ấy chỉ lộ ra khi khách nhận tin lúc 2 giờ
    sáng.
    """
    cfg = configured(db); kind = "oa" if zalo_uid else "zns"
    tid = template or cfg["zns_templates"].get(purpose, "")
    m = ZaloMessage(kind=kind, phone=norm_phone(phone), zalo_uid=zalo_uid, lead_id=lead_id, booking_id=booking_id, template_id=tid, params=params or {}, text=text, purpose=purpose, created_by=actor,
                    gui_tu_luc=gui_tu_luc,
                    status="cho_gui" if (cfg["oa"] and (zalo_uid or tid)) else "cho_cau_hinh")
    db.add(m); db.flush()
    if gui_tu_luc: send_now = False
    if send_now and m.status == "cho_gui": _send(db, m)
    return m


def _send(db: Session, m: ZaloMessage) -> None:
    def gui():
        return send_oa_text(db, m.zalo_uid, m.text) if m.kind == "oa" else send_zns(db, m.phone, m.template_id, m.params)
    try:
        r = gui()
        m.response = json.dumps(r, ensure_ascii=False)[:2000]
        ok = (r.get("error") in (0, None)) and not r.get("error_name")
        if not ok and r.get("error") in (-216, -124) and refresh_token(db):   # token hết hạn → làm mới và gửi lại 1 lần
            r = gui(); ok = (r.get("error") in (0, None)) and not r.get("error_name"); m.response = json.dumps(r, ensure_ascii=False)[:2000]
        m.status, m.sent_at = ("da_gui" if ok else "loi"), datetime.now()
    except Exception as ex:
        m.status, m.response = "loi", str(ex)[:500]


def send_pending(db: Session, limit: int = 100) -> dict:
    cfg = configured(db); n = 0
    bay_gio = datetime.now()
    for m in db.execute(select(ZaloMessage).where(
            ZaloMessage.status.in_(["cho_gui", "cho_cau_hinh"]),
            # Tin có giờ hẹn thì nằm im cho tới lúc ấy. `is_(None)` phải đứng trong phép HOẶC chứ
            # không lọc riêng: tin cũ đều có cột này rỗng, lọc sai là chúng tắc trong hàng đợi.
            (ZaloMessage.gui_tu_luc.is_(None)) | (ZaloMessage.gui_tu_luc <= bay_gio),
    ).order_by(ZaloMessage.id).limit(limit)).scalars():
        if not cfg["oa"]: break
        if m.kind == "zns" and not m.template_id: m.template_id = cfg["zns_templates"].get(m.purpose, "")
        if m.kind == "zns" and not m.template_id: continue
        _send(db, m); n += 1
    db.commit(); return {"sent": n}


def verify_signature(body: bytes, sig: str, ts: str) -> bool:
    if not settings.ZALO_OA_SECRET_KEY: return True
    mac = hashlib.sha256((settings.ZALO_APP_ID + body.decode() + ts + settings.ZALO_OA_SECRET_KEY).encode()).hexdigest()
    return hmac.compare_digest("mac=" + mac, sig or "") or hmac.compare_digest(mac, sig or "")


def on_webhook(db: Session, ev: dict) -> dict:
    """Sự kiện OA: follow → lead kênh Zalo OA (chưa có SĐT); user_send_text → cập nhật last_contact; user_submit_info (chia sẻ SĐT) → gắn SĐT vào lead."""
    name = ev.get("event_name") or ""; uid = str((ev.get("follower") or ev.get("sender") or {}).get("id") or ev.get("user_id") or "")
    if not uid: return {"ignored": True}

    # ---- NỐI TÀI KHOẢN & CHẶN LEAD GIẢ (19/9/2026) — xem app/services/zalo_nguoi_dung.py ----
    #
    # Hai chốt, đặt TRƯỚC mọi thứ khác trong hàm này, vì cả hai đều phải chặn được việc tạo lead:
    #
    #   1. Tin khách nhắn vào có thể là MỘT MÃ NỐI. Nối xong thì dừng hẳn — một mã nối không phải
    #      một câu hỏi của khách, không vào hộp thư, không thành lead.
    #   2. UID đã nối với tài khoản nhân viên thì KHÔNG tạo lead và KHÔNG vào hộp thư khách. Chủ
    #      tịch bấm "Quan tâm" OA để nhận cảnh báo, chứ không phải để thành một khách hàng tiềm
    #      năng trong mẫu số tỷ lệ chốt lead của Sales.
    from app.services import zalo_nguoi_dung as ZN
    if name == "user_send_text":
        kq = ZN.thu_ma(db, uid, (ev.get("message") or {}).get("text") or "")
        if kq.get("noi"):
            db.commit()
            try: send_oa_text(db, uid, f"Đã nối Zalo này với tài khoản VTOS {kq['username']}. Từ nay cảnh báo của hệ thống sẽ gửi về đây.")
            except Exception: pass
            return {"event": name, "uid": uid, "noi_tai_khoan": kq["username"]}
    if ZN.la_nhan_vien(db, uid):
        # Vẫn ghi nhận sự kiện để đếm được, nhưng không chạm vào sổ lead và hộp thư khách.
        return {"event": name, "uid": uid, "la_nhan_vien": True, "bo_qua_lead": True}

    if name in ("user_send_text", "user_send_image", "user_send_sticker"):
        try:
            from app.services import inbox as IB
            IB.inbound(db, "zalo", uid, (ev.get("message") or {}).get("text") or f"[{name}]", ext_msg_id=str((ev.get("message") or {}).get("msg_id") or ""))
        except Exception as ex: return {"inbox_error": str(ex)[:200]}
    lead = db.execute(select(Lead).where(Lead.zalo_uid == uid).order_by(Lead.id.desc())).scalars().first()
    month = f"{datetime.now():%Y-%m}"; out = {"event": name, "uid": uid}
    if name == "follow":
        if not lead:
            lead = Lead(phone=f"zalo{uid[-9:]}", name="", channel="Zalo OA", lead_month=month, zalo_uid=uid, zalo_follow=True, created_by="zalo"); db.add(lead); out["lead"] = "new"
        else: lead.zalo_follow = True
    elif name == "unfollow" and lead: lead.zalo_follow = False
    elif name in ("user_send_text", "user_send_image", "user_send_sticker"):
        if not lead:
            lead = Lead(phone=f"zalo{uid[-9:]}", channel="Zalo OA", lead_month=month, zalo_uid=uid, created_by="zalo"); db.add(lead); out["lead"] = "new"
        lead.last_contact_at = datetime.now()
        txt = (ev.get("message") or {}).get("text") or ""
        if txt: lead.note = (lead.note + "\n" if lead.note else "") + f"[{datetime.now():%d/%m %H:%M}] {txt[:300]}"
        ph = norm_phone("".join(ch for ch in txt if ch.isdigit()))
        if len(ph) == 10 and ph.startswith("0"): _attach_phone(db, lead, ph)
    elif name == "user_submit_info":
        info = ev.get("info") or {}; ph = norm_phone(info.get("phone") or "")
        if not lead:
            lead = Lead(phone=ph or f"zalo{uid[-9:]}", name=info.get("name") or "", channel="Zalo OA", lead_month=month, zalo_uid=uid, created_by="zalo"); db.add(lead); out["lead"] = "new"
        if ph: _attach_phone(db, lead, ph)
        if info.get("name") and not lead.name: lead.name = info["name"][:120]
    db.commit(); return out


def _attach_phone(db: Session, lead: Lead, ph: str) -> None:
    for other in db.execute(select(Lead).where(Lead.phone == ph, Lead.id != lead.id).order_by(Lead.id.desc())).scalars():
        if not other.zalo_uid: other.zalo_uid, other.zalo_follow = lead.zalo_uid, lead.zalo_follow
    dup = db.execute(select(Lead).where(Lead.phone == ph, Lead.lead_month == lead.lead_month, Lead.channel == lead.channel, Lead.id != lead.id)).scalars().first()
    if not dup: lead.phone = ph
