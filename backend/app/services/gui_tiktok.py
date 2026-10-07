"""BỘ GỬI CHUYỂN ĐỔI NGƯỢC VỀ TIKTOK (Events API 2.0, nguồn CRM).

Cùng việc với `gui_meta.py`, khác nền tảng: nói ngược lại cho TikTok biết khách nào thật sự
chốt tour và trị giá bao nhiêu.

Báo cáo Marketing tháng 9/2026 ghi về TikTok đúng một câu, và câu ấy là chẩn đoán sẵn cho vòng
này: "data nhiều nhưng tỷ lệ chốt thấp nhất". Đó không phải lỗi của TikTok — đó là cái xảy ra
khi nền tảng chỉ được cho biết "có người điền form". Nó đi mua thêm người điền form, rất giỏi và
rất rẻ, đúng như được dạy. Vòng này đổi bài học: TikTok sẽ biết ai trong số ấy mang tiền về.

────────────────────────────────────────────────────────────────────────────────────────────────
CÁI BẪY LỚN NHẤT CỦA TỆP NÀY: SỐ ĐIỆN THOẠI KHÁC META
────────────────────────────────────────────────────────────────────────────────────────────────
Hai nền tảng đòi hai cách viết KHÁC NHAU cho cùng một số, và băm xong thì ra hai chuỗi không
liên quan gì nhau:

    Meta    : "84909123456"      – bỏ ký hiệu, bỏ số 0 đầu, CÓ mã quốc gia, KHÔNG dấu cộng
    TikTok  : "+84909123456"     – chuẩn E.164, CÓ dấu cộng

Dùng nhầm hàm của nhau thì KHÔNG nền tảng nào báo lỗi: cả hai vẫn nhận gói, vẫn trả thành công,
và khớp được đúng 0%. Không có một dòng nhật ký nào trên đời nói ra chuyện đó — chỉ có báo cáo
quảng cáo trống trơn sau sáu tháng.

Vì thế tệp này có hàm băm số điện thoại RIÊNG, và phép thử của nó khẳng định thẳng rằng kết quả
KHÁC với hàm của Meta. Hai hàm trông gần giống nhau là chuyện có thật và nguy hiểm; phép thử là
thứ giữ cho ai đó sau này không "dọn dẹp" bằng cách gộp chúng lại.

Riêng EMAIL thì hai bên quy định y hệt nhau (cắt khoảng trắng, chữ thường, SHA-256 — đối chiếu
tài liệu hai bên ngày 07/10/2026), nên dùng chung hàm của `gui_meta`. Một quy tắc, một chỗ.

────────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO NGUỒN "CRM" CHỨ KHÔNG PHẢI "WEB" HAY "OFFLINE"
────────────────────────────────────────────────────────────────────────────────────────────────
TikTok chia nguồn sự kiện làm bốn: web (đo bằng Pixel), app, offline (đo bằng Offline Event Set),
và crm (đo bằng CRM Event Set). Việc của VTOS đúng là loại cuối: khách đến từ biểu mẫu quảng cáo
TikTok, rồi chốt tour trong hệ thống nội bộ. Chỉ nguồn `crm` mới nhận `lead.lead_id` — mã lead
do chính TikTok cấp, tức là phép khớp chắc nhất có thể có.

HỆ QUẢ PHẢI BIẾT TRƯỚC: tài liệu TikTok nói rõ "với sự kiện CRM, tên sự kiện CHỈ ĐƯỢC là sự kiện
tuỳ chỉnh" — không dùng được tên chuẩn như `Purchase` hay `CompletePayment`. Nên tên mặc định ở
đây là một tên tự đặt, và Phòng MKT PHẢI khai đúng tên ấy trong Trình quản lý sự kiện của TikTok
thì nó mới hiện ra để chạy tối ưu. Khai lệch một chữ là sự kiện vào hệ thống nhưng không gắn vào
chiến dịch nào — hỏng lặng lẽ, lại đúng kiểu ấy.

────────────────────────────────────────────────────────────────────────────────────────────────
NHỮNG CHỐT GIỮ NGUYÊN TỪ `gui_meta.py`, VÀ MỘT CHỖ KHÁC
────────────────────────────────────────────────────────────────────────────────────────────────
GIỮ NGUYÊN — chưa có token thì quay về NGAY, không gọi mạng và không đổi trạng thái dòng nào;
chỉ đụng vào dòng của nền tảng mình, dòng gclid và leadgen Facebook nằm yên chờ bộ gửi của
chúng; `event_id` lấy `khoa_chong_trung` nên ổn định qua mọi lần chạy lại; doanh thu gửi ĐẦY ĐỦ
không chia; gửi 0 đồng thì thà im lặng.

KHÁC — Meta từ chối thẳng sự kiện quá 7 ngày, nên `gui_meta` phải đánh dấu `qua_han`. Tài liệu
TikTok KHÔNG nêu một hạn nào cho sự kiện CRM. Em đã tìm và không thấy, nên ở đây KHÔNG dựng một
cái hạn tự nghĩ ra: đặt bừa 7 ngày là tự tay vứt đi những chuyển đổi TikTok vẫn nhận. Thay vào
đó mỗi dòng được ghi lại tuổi của nó khi gửi, và nguyên văn câu trả lời của TikTok. Khi nào
TikTok từ chối vì quá hạn thì chính câu trả lời ấy nói ra con số thật, và lúc đó mới khai nó vào
đây — một hằng số có bằng chứng, không phải một con số đoán.

Chống trùng: TikTok loại trùng theo bộ ba (`event_source_id`, `event_id`, `event`).
"""
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.crm import Lead
from app.models.quang_cao import DauQuangCao, ChuyenDoiGuiDi
from app.services import chuyen_doi_di as CD
# Quy tắc email của TikTok và của Meta giống hệt nhau – xem đầu tệp. Số điện thoại thì KHÔNG,
# nên nó có hàm riêng ngay dưới đây.
from app.services.gui_meta import bam_email
from app.services.zalo import intl as _sdt_quoc_te

NEN_TANG = "tiktok"
API = "https://business-api.tiktok.com/open_api/{ban}/event/track/"

# Nguồn CRM nhận mã lead của TikTok; các loại mã khác khớp bằng số điện thoại đã băm.
# `ttclid` KHÔNG có mặt ở đây: tài liệu TikTok xếp nó cho sự kiện WEB, không phải CRM.
KHOP_BANG_MA_LEAD = "leadgen_id"


def bam_sdt(sdt: str) -> str:
    """Số điện thoại về chuẩn E.164 **CÓ DẤU CỘNG** rồi băm SHA-256.

    ĐỪNG GỘP HÀM NÀY VỚI `gui_meta.bam_sdt`. Hai nền tảng đòi hai cách viết khác nhau và cả hai
    đều im lặng khi mình viết sai – xem phần đầu tệp. Phép thử `test_tc108` khẳng định hai hàm
    cho ra hai kết quả KHÁC nhau, cố ý, để lần dọn dẹp nào gộp chúng lại cũng làm đỏ phép thử.
    """
    q = _sdt_quoc_te(sdt)
    return hashlib.sha256(("+" + q).encode("utf-8")).hexdigest() if len(q) >= 10 else ""


def cau_hinh() -> dict:
    """Tình trạng cấu hình, KHÔNG kèm token. An toàn để in ra màn hình cho người xem."""
    thieu = []
    if not (settings.TT_EVENT_SET_ID or "").strip():
        thieu.append("TT_EVENT_SET_ID")
    if not (settings.TT_ACCESS_TOKEN or "").strip():
        thieu.append("TT_ACCESS_TOKEN")
    return {
        "san_sang": not thieu,
        "thieu": thieu,
        "event_set_id": (settings.TT_EVENT_SET_ID or "").strip(),
        "co_token": bool((settings.TT_ACCESS_TOKEN or "").strip()),
        "ban_api": settings.TT_API_VERSION,
        "ten_su_kien": settings.TT_EVENT_NAME,
        "huong_dan": "TT_EVENT_SET_ID là CRM Event Set ID, lấy bằng cửa /crm/list/ của TikTok "
                     "Business API. TT_ACCESS_TOKEN do CNTT dán trên máy chủ. Phòng MKT PHẢI "
                     f"khai sự kiện tuỳ chỉnh tên đúng '{settings.TT_EVENT_NAME}' trong Trình "
                     "quản lý sự kiện TikTok – sự kiện CRM không dùng được tên chuẩn.",
    }


def xet(cd: ChuyenDoiGuiDi, dau: DauQuangCao | None) -> dict:
    """Dòng này gửi được không, và nếu không thì vì sao. Hàm thuần, phép thử soi được từng nhánh."""
    if cd.nen_tang != NEN_TANG:
        return {"gui": False, "trang_thai": "", "ly_do": f"không phải TikTok ({cd.nen_tang})"}
    if cd.doanh_thu is None:
        return {"gui": False, "trang_thai": "thieu_doanh_thu",
                "ly_do": "chưa đọc được doanh thu – gửi 0 đồng là dạy TikTok rằng khách vô giá trị"}
    if cd.chot_luc is None:
        return {"gui": False, "trang_thai": "bo_qua",
                "ly_do": "không có mốc chốt – event_time là bắt buộc, và đoán một mốc là báo sai"}
    co_ma_lead = cd.loai_ma == KHOP_BANG_MA_LEAD and bool(cd.ma)
    co_sdt = bool(bam_sdt(getattr(dau, "sdt", "") or ""))
    if not co_ma_lead and not co_sdt:
        return {"gui": False, "trang_thai": "bo_qua",
                "ly_do": f"loại mã '{cd.loai_ma}' không có mã lead, và cũng không có số điện "
                         "thoại – TikTok cần ít nhất một thứ để khớp"}
    return {"gui": True, "trang_thai": "", "ly_do": ""}


def goi_tin(cd: ChuyenDoiGuiDi, dau: DauQuangCao | None, email: str = "") -> dict:
    """Dựng đúng gói JSON TikTok chờ. Hàm thuần – không chạm cơ sở dữ liệu, không chạm mạng."""
    su_kien: dict = {
        "event": settings.TT_EVENT_NAME,
        # Giây, múi giờ UTC+0 – tài liệu nói thẳng. `chot_luc` do máy chủ ghi bằng giờ của chính
        # nó, và `.timestamp()` đọc lại bằng đúng múi giờ ấy, nên hai đầu khớp nhau.
        "event_time": int(cd.chot_luc.timestamp()),
        # Ổn định qua mọi lần chạy lại. TikTok loại trùng theo bộ ba event_source_id + event_id
        # + event, nên mã này phải suy từ dữ liệu chứ không từ đồng hồ.
        "event_id": cd.khoa_chong_trung,
        "properties": {"currency": (cd.tien_te or "VND").upper()[:3],
                       "value": float(cd.doanh_thu),
                       "order_id": cd.ma_booking},
    }

    if cd.loai_ma == KHOP_BANG_MA_LEAD and cd.ma:
        # KHÔNG băm: mã này do TikTok cấp, TikTok đọc thẳng. `lead_event_source` là tên hệ CRM
        # của mình, để bên TikTok nhìn báo cáo biết dữ liệu từ đâu tới.
        su_kien["lead"] = {"lead_id": str(cd.ma).strip(), "lead_event_source": "VTOS"}

    nguoi: dict = {}
    h = bam_sdt(getattr(dau, "sdt", "") or "")
    if h:
        nguoi["phone"] = h
    e = bam_email(email)
    if e:
        nguoi["email"] = e
    if nguoi:
        su_kien["user"] = nguoi

    return {"event_source": "crm",
            "event_source_id": (settings.TT_EVENT_SET_ID or "").strip(),
            "data": [su_kien]}


def _bo_gui_that(goi: dict) -> dict:
    """Gọi Events API thật. Thay được bằng `dat_ham()` để phép thử không chạm Internet."""
    url = API.format(ban=settings.TT_API_VERSION)
    req = urllib.request.Request(
        url, data=json.dumps(goi).encode("utf-8"), method="POST",
        # Token đi trong HEADER, không đi trên đường dẫn – khác Meta. Nhờ vậy nó không lọt vào
        # nhật ký máy chủ hay vào ô `tra_loi` của bảng.
        headers={"Content-Type": "application/json",
                 "Access-Token": (settings.TT_ACCESS_TOKEN or "").strip()})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            than = r.read().decode("utf-8", "replace")[:4000]
    except urllib.error.HTTPError as ex:
        try:
            than = ex.read().decode("utf-8", "replace")[:4000]
        except Exception:                                      # noqa: BLE001
            than = ""
        return {"ok": False, "tra_loi": than, "loi": f"HTTP {ex.code}"}
    except Exception as ex:                                    # noqa: BLE001
        return {"ok": False, "tra_loi": "", "loi": f"{type(ex).__name__}: {str(ex)[:300]}"}

    # TIKTOK TRẢ 200 CẢ KHI HỎNG. Mã thật nằm trong thân, ở khoá `code`: 0 là được, khác 0 là
    # lỗi. Tin vào mã HTTP ở đây là đánh dấu "đã gửi" cho những dòng TikTok đã từ chối, và bảng
    # sẽ báo 100% thành công trong khi không có gì tới nơi.
    try:
        j = json.loads(than)
    except ValueError:
        return {"ok": False, "tra_loi": than, "loi": "TikTok trả về không phải JSON"}
    ma = j.get("code")
    if ma == 0:
        return {"ok": True, "tra_loi": than}
    return {"ok": False, "tra_loi": than,
            "loi": f"TikTok code {ma}: {str(j.get('message') or '')[:200]}"}


_ham_gui = _bo_gui_that


def dat_ham(f=None) -> None:
    """Thay tầng gửi mạng. Gọi không tham số để trả về hàm thật."""
    global _ham_gui
    _ham_gui = f or _bo_gui_that


def _email_cua(db: Session, cd: ChuyenDoiGuiDi) -> str:
    """Email của lead. Bảng `leads` hôm nay không có cột này – xem `gui_meta._email_cua`."""
    if not cd.lead_id:
        return ""
    l = db.get(Lead, cd.lead_id)
    return getattr(l, "email", "") or ""


def gui(db: Session, gioi_han: int = 100) -> dict:
    """Một lượt gửi. Chưa cấu hình thì quay về NGAY và không đổi trạng thái dòng nào."""
    cfg = cau_hinh()
    if not cfg["san_sang"]:
        cho = len(CD.cho_gui(db, gioi_han, nen_tang=NEN_TANG))
        return {"san_sang": False, "thieu": cfg["thieu"], "da_gui": 0, "loi": 0,
                "bo_qua": 0, "dang_cho": cho,
                "message": f"Chưa gửi được: thiếu {', '.join(cfg['thieu'])}. "
                           f"{cho} dòng TikTok đang chờ, chưa đụng tới dòng nào."}

    dem = {"da_gui": 0, "loi": 0, "bo_qua": 0, "thieu_doanh_thu": 0}
    chi_tiet: list[dict] = []
    bay_gio = datetime.now()

    for cd in CD.cho_gui(db, gioi_han, nen_tang=NEN_TANG):
        dau = db.get(DauQuangCao, cd.dau_id)
        xet_qua = xet(cd, dau)
        if not xet_qua["gui"]:
            tt = xet_qua["trang_thai"]
            if tt:
                cd.trang_thai = tt
                cd.loi_cuoi = xet_qua["ly_do"][:2000]
                dem[tt] = dem.get(tt, 0) + 1
                chi_tiet.append({"id": cd.id, "ma_booking": cd.ma_booking,
                                 "ket_qua": tt, "ly_do": xet_qua["ly_do"]})
            continue
        tuoi = (bay_gio - cd.chot_luc).days
        kq = _ham_gui(goi_tin(cd, dau, _email_cua(db, cd)))
        CD.ghi_ket_qua(db, cd, bool(kq.get("ok")), kq.get("tra_loi", ""), kq.get("loi", ""))
        if kq.get("ok"):
            dem["da_gui"] += 1
        else:
            dem["loi"] += 1
            # Tuổi của dòng đi kèm lỗi: nếu TikTok có một hạn không ghi trong tài liệu, nó sẽ lộ
            # ra ở đây dưới dạng "mọi dòng quá N ngày đều lỗi" – xem phần đầu tệp.
            chi_tiet.append({"id": cd.id, "ma_booking": cd.ma_booking, "ket_qua": "loi",
                             "tuoi_ngay": tuoi, "ly_do": kq.get("loi", "")})
    db.commit()

    return {"san_sang": True, "thieu": [], **dem, "chi_tiet": chi_tiet,
            "message": f"Gửi {dem['da_gui']} chuyển đổi lên TikTok, {dem['loi']} lỗi, "
                       f"{dem['bo_qua']} bỏ qua"}


def con_lai(db: Session) -> dict:
    """Còn bao nhiêu dòng TikTok đang chờ, và dòng chờ lâu nhất đã bao nhiêu ngày.

    Không có cột 'sắp quá hạn' như bên Meta, vì TikTok không công bố hạn nào. `cho_lau_nhat_ngay`
    là thứ thay thế: nó không nói dòng đó đã mất, nhưng nó nói hàng đợi đang ứ tới đâu.
    """
    hom_nay = datetime.now()
    con = 0
    lau_nhat = None
    for cd in db.execute(select(ChuyenDoiGuiDi)
                         .where(ChuyenDoiGuiDi.trang_thai == "cho_gui",
                                ChuyenDoiGuiDi.nen_tang == NEN_TANG)).scalars():
        con += 1
        if cd.chot_luc is not None:
            n = (hom_nay - cd.chot_luc).days
            lau_nhat = n if lau_nhat is None else max(lau_nhat, n)
    return {"dang_cho": con, "cho_lau_nhat_ngay": lau_nhat}
