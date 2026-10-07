"""BỘ GỬI CHUYỂN ĐỔI NGƯỢC VỀ META (Conversions API).

Đây là mắt xích CUỐI của vòng tròn Facebook: dấu chạm đã bắt được (`dau_quang_cao`), lead đã
chốt tour đã xếp hàng (`chuyen_doi_gui_di`), và tệp này là cái miệng nói ngược lại cho Meta
"người bạn mang tới đã mua tour, trị giá bằng này tiền".

VÌ SAO MẮT XÍCH NÀY ĐÁNG GIÁ. Không nói thì Meta chỉ học được "có người điền form" và sẽ rất
giỏi mua thêm người điền form – loại khách rẻ nhất và không chốt. Tháng 9/2026 Facebook là kênh
doanh thu lớn nhất của Vietourist: 3,24 tỷ. Toàn bộ số ấy Meta không biết.

────────────────────────────────────────────────────────────────────────────────────────────────
MỘT HẠN CHÓT CÓ THẬT, ĐỌC TRƯỚC KHI SỬA TỆP NÀY
────────────────────────────────────────────────────────────────────────────────────────────────
Meta chỉ nhận `event_time` TỐI ĐA 7 NGÀY về trước (tài liệu Server Event Parameters, đọc
07/10/2026). Không phải "gửi trễ thì kém chính xác" – mà là Meta TỪ CHỐI.

Hệ quả, viết thẳng ra để không ai phải tự phát hiện:
  • Chừng nào chưa có token, mỗi ngày trôi qua là một ngày doanh thu VĨNH VIỄN không gửi được.
  • Doanh thu Facebook tháng 9 đã quá hạn từ lâu. Phần ấy không cứu được bằng mã, chỉ còn giá
    trị đối chiếu bằng tay.
  • Vì thế bộ gửi phải chạy HẰNG NGÀY, không phải hằng tuần. Lỡ một tuần là mất một tuần.
Dòng quá hạn được đánh dấu `qua_han` chứ KHÔNG gửi: gửi để Meta từ chối thì chỉ tổ làm bẩn bảng
lỗi và che mất những lỗi thật.

────────────────────────────────────────────────────────────────────────────────────────────────
CHƯA CÓ TOKEN THÌ KHÔNG ĐỤNG VÀO GÌ HẾT
────────────────────────────────────────────────────────────────────────────────────────────────
Thiếu `FB_DATASET_ID` hoặc `FB_CAPI_TOKEN` thì hàm gửi quay về NGAY, không gọi mạng, và KHÔNG
đổi trạng thái một dòng nào. Cố tình không đặt các dòng ấy sang một trạng thái "chờ cấu hình":
đổi trạng thái thì lúc token về lại phải có một lượt đảo ngược, và lượt đảo ngược nào cũng là
một chỗ để sót. Để yên ở `cho_gui` thì ngày token về, lượt chạy kế tiếp cuốn hết – không cần nhớ
gì thêm.

HAI GIÁ TRỊ ẤY LÀ HAI GIÁ TRỊ KHÁC NHAU, VÀ KHÔNG LẤY TẠM CỦA NHAU:
  FB_PAGE_ACCESS_TOKEN  – token Trang, cho Messenger. ĐÃ có, đang dùng ở `services/inbox.py`.
  FB_CAPI_TOKEN         – token có quyền `ads_management` trên Dataset. CHƯA có.
Lấy token Trang dùng tạm cho CAPI thì Meta trả lỗi quyền, và lỗi quyền đọc rất giống lỗi dữ
liệu – mất nửa ngày mới lần ra. Thà đứng im và nói thiếu cái gì.

────────────────────────────────────────────────────────────────────────────────────────────────
CHỈ GỬI NHỮNG DÒNG META THẬT SỰ KHỚP ĐƯỢC
────────────────────────────────────────────────────────────────────────────────────────────────
Bộ gửi này CHỈ nhận dòng `nen_tang == "facebook"`. Dòng gclid của Google, ttclid của TikTok nằm
yên chờ bộ gửi của chúng – đụng vào là cướp việc của bộ gửi khác và dòng ấy không bao giờ được
gửi đi đâu cả.

Trong số dòng Facebook, độ chính xác của phép khớp xếp hạng rõ ràng:
  leadgen_id  – mã lead do chính Meta cấp. Khớp TUYỆT ĐỐI, đúng tới từng mẫu quảng cáo. Đây là
                đường tốt nhất và là lý do TC-106 đi bắt `leadgen` từ webhook trước.
  ad_referral – khách bấm quảng cáo rồi nhắn tin. Không có mã lead, khớp bằng số điện thoại đã
                băm. Kém chắc hơn nhưng vẫn là dữ liệu thật.
  còn lại     – `bo_qua`, kèm lý do ghi vào `loi_cuoi` để đếm được. Bỏ qua CÓ GHI LÝ DO khác hẳn
                bỏ qua im lặng: cái sau thì sáu tháng nữa không ai biết vì sao thiếu.

────────────────────────────────────────────────────────────────────────────────────────────────
NHỮNG CHỖ KHÔNG ĐƯỢC ĐOÁN
────────────────────────────────────────────────────────────────────────────────────────────────
`action_source` – Meta hỏi "chuyển đổi xảy ra ở đâu". Với một booking chốt trong VTOS, sự thật
là KHÔNG AI BIẾT: có thể sale gọi điện, có thể khách nhắn tin, có thể khách tới văn phòng. VTOS
hôm nay không ghi điều đó ở đâu cả. Meta có sẵn một giá trị cho đúng tình huống này và tên nó là
`other` – nên mặc định là `other`, không phải một giá trị nghe hay hơn mà sai. Riêng
`ad_referral` thì biết chắc là qua tin nhắn nên dùng `chat`. Khi nào VTOS ghi được cách chốt thì
đổi ở một chỗ, hoặc Phòng MKT đặt `FB_CAPI_ACTION_SOURCE` nếu họ biết rõ hơn.

`event_name` – mặc định `Purchase`, vì đó là sự thật: khách đã mua tour và có số tiền. Đổi được
bằng `FB_CAPI_EVENT_NAME` nếu Phòng MKT dựng phễu nhiều bậc trên Trình quản lý sự kiện.

────────────────────────────────────────────────────────────────────────────────────────────────
CHỐNG TRÙNG
────────────────────────────────────────────────────────────────────────────────────────────────
`event_id` lấy đúng `khoa_chong_trung` của dòng – một chuỗi ỔN ĐỊNH, chạy lại bao nhiêu lần cũng
ra cùng giá trị. Meta loại trùng theo cặp (`event_id`, `event_name`) trong cửa sổ 48 GIỜ. Nghĩa
là gửi lại trong 48 giờ thì an toàn; gửi lại sau đó thì Meta đếm hai lần. Nên vòng gửi lại khi
lỗi phải nằm trong 48 giờ, và `lan_thu` ở bảng là để nhìn ra điều đó.

KHÔNG DÙNG thời gian hiện tại làm `event_id`: mỗi lần chạy lại ra một mã mới, Meta không loại
trùng được, và một booking đếm thành năm.

────────────────────────────────────────────────────────────────────────────────────────────────
VỀ KỸ THUẬT
────────────────────────────────────────────────────────────────────────────────────────────────
Dùng `urllib` của thư viện chuẩn, giống `services/inbox.py` và `services/zalo.py`, chứ không
thêm gói mới: thêm một gói vào máy chủ tiền thật chỉ để gọi một cửa là không đáng.

Chuẩn hoá số điện thoại GỌI LẠI `services/zalo.intl()` thay vì viết hàm thứ hai. Meta đòi "bỏ ký
hiệu, bỏ số 0 đầu, có mã quốc gia" – đúng bằng những gì `intl()` đã làm và đã chạy thật. Viết
hàm thứ hai là dựng con số thứ hai cho cùng câu hỏi, và ngày hai cái lệch nhau thì không ai biết
tin cái nào.

Hàm gửi mạng tiêm được vào (`dat_ham`), nên phép thử chạy bằng máy chủ GIẢ và KHÔNG BAO GIỜ gọi
ra Internet. Phép thử gọi mạng thật là phép thử hỏng theo đường truyền, và tệ hơn: nó bắn dữ
liệu thử lên tài khoản quảng cáo thật.

TOKEN KHÔNG BAO GIỜ ĐI RA NGOÀI TỆP NÀY. `cau_hinh()` trả `co_token: True/False`, không trả giá
trị; `tra_loi` lưu lại cũng được cắt và không chứa đường dẫn có token.
"""
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.crm import Lead
from app.models.quang_cao import DauQuangCao, ChuyenDoiGuiDi
from app.services import chuyen_doi_di as CD
from app.services.zalo import intl as _sdt_quoc_te

# Meta nhận event_time tối đa 7 ngày – xem phần "MỘT HẠN CHÓT CÓ THẬT" ở đầu tệp.
HAN_EVENT_TIME_NGAY = 7

# Cửa sổ Meta loại trùng theo (event_id, event_name). Để ở đây thành hằng số đọc được, vì nó
# quyết định vòng gửi lại được phép chậm tới đâu.
CUA_SO_CHONG_TRUNG_GIO = 48

NEN_TANG = "facebook"

# Loại mã nào khớp được với Meta, và khớp bằng đường nào.
KHOP_DUOC = {"leadgen_id", "ad_referral"}


def _bam(s: str) -> str:
    """SHA-256, chữ thường, dạng hex – đúng cái Meta đòi cho mọi trường cá nhân."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def bam_email(email: str) -> str:
    """Cắt khoảng trắng, chuyển chữ thường, rồi băm. Rỗng vào thì rỗng ra."""
    e = str(email or "").strip().lower()
    return _bam(e) if ("@" in e and "." in e.split("@")[-1]) else ""


def bam_sdt(sdt: str) -> str:
    """Số điện thoại về dạng quốc tế KHÔNG dấu cộng rồi băm.

    Meta: "bỏ ký hiệu, bỏ chữ, bỏ số 0 đứng đầu; số phải có mã quốc gia". Với số Việt Nam,
    `0909123456` phải thành `84909123456` – KHÔNG phải `909123456`. Bỏ số 0 mà quên gắn `84` là
    lỗi im lặng tệ nhất ở đây: Meta vẫn nhận, vẫn trả 200, và khớp được 0%.
    """
    q = _sdt_quoc_te(sdt)
    return _bam(q) if len(q) >= 10 else ""


def cau_hinh() -> dict:
    """Tình trạng cấu hình, KHÔNG kèm token. An toàn để in ra màn hình cho người xem."""
    thieu = []
    if not (settings.FB_DATASET_ID or "").strip():
        thieu.append("FB_DATASET_ID")
    if not (settings.FB_CAPI_TOKEN or "").strip():
        thieu.append("FB_CAPI_TOKEN")
    return {
        "san_sang": not thieu,
        "thieu": thieu,
        "dataset_id": (settings.FB_DATASET_ID or "").strip(),
        "co_token": bool((settings.FB_CAPI_TOKEN or "").strip()),
        "phien_ban_graph": settings.FB_CAPI_VERSION,
        "ten_su_kien": settings.FB_CAPI_EVENT_NAME,
        "action_source_mac_dinh": settings.FB_CAPI_ACTION_SOURCE,
        "che_do_thu": bool((settings.FB_CAPI_TEST_EVENT_CODE or "").strip()),
        "han_event_time_ngay": HAN_EVENT_TIME_NGAY,
        "cua_so_chong_trung_gio": CUA_SO_CHONG_TRUNG_GIO,
        "huong_dan": "Thiếu giá trị nào thì CNTT dán vào biến môi trường trên máy chủ. "
                     "FB_CAPI_TOKEN phải là token có quyền ads_management trên Dataset – "
                     "KHÔNG dùng lại FB_PAGE_ACCESS_TOKEN của Messenger.",
    }


def _nguon_hanh_dong(loai_ma: str) -> str:
    """Xem phần 'NHỮNG CHỖ KHÔNG ĐƯỢC ĐOÁN' ở đầu tệp."""
    dat = (settings.FB_CAPI_ACTION_SOURCE or "").strip()
    if dat:
        return dat
    return "chat" if loai_ma == "ad_referral" else "other"


def xet(cd: ChuyenDoiGuiDi, dau: DauQuangCao | None, bay_gio: datetime | None = None) -> dict:
    """Dòng này gửi được không, và nếu không thì vì sao.

    Tách riêng khỏi hàm gửi để phép thử soi được từng nhánh mà không cần cơ sở dữ liệu lẫn mạng.
    Trả `{"gui": bool, "trang_thai": str, "ly_do": str}`.
    """
    bay_gio = bay_gio or datetime.now()
    if cd.nen_tang != NEN_TANG:
        return {"gui": False, "trang_thai": "", "ly_do": f"không phải Facebook ({cd.nen_tang})"}
    if cd.doanh_thu is None:
        return {"gui": False, "trang_thai": "thieu_doanh_thu",
                "ly_do": "chưa đọc được doanh thu – gửi 0 đồng là dạy Meta rằng khách vô giá trị"}
    if cd.loai_ma not in KHOP_DUOC:
        return {"gui": False, "trang_thai": "bo_qua",
                "ly_do": f"loại mã '{cd.loai_ma}' Meta không khớp ngược được"}
    if cd.chot_luc is None:
        return {"gui": False, "trang_thai": "bo_qua",
                "ly_do": "không có mốc chốt – Meta bắt buộc event_time, và đoán một mốc là báo sai"}
    tuoi = bay_gio - cd.chot_luc
    if tuoi > timedelta(days=HAN_EVENT_TIME_NGAY):
        return {"gui": False, "trang_thai": "qua_han",
                "ly_do": f"chốt {tuoi.days} ngày trước, Meta chỉ nhận trong "
                         f"{HAN_EVENT_TIME_NGAY} ngày – gửi đi cũng bị từ chối"}
    ma_lead = cd.ma if cd.loai_ma == "leadgen_id" else ""
    co_sdt = bool(bam_sdt(getattr(dau, "sdt", "") or ""))
    if not ma_lead and not co_sdt:
        return {"gui": False, "trang_thai": "bo_qua",
                "ly_do": "không có mã lead lẫn số điện thoại – Meta đòi ít nhất một thứ để khớp"}
    return {"gui": True, "trang_thai": "", "ly_do": ""}


def goi_tin(cd: ChuyenDoiGuiDi, dau: DauQuangCao | None, email: str = "") -> dict:
    """Dựng đúng gói JSON Meta chờ. Hàm thuần – không chạm cơ sở dữ liệu, không chạm mạng."""
    nguoi: dict = {}
    if cd.loai_ma == "leadgen_id" and cd.ma:
        # KHÔNG băm. Meta cấp mã này, Meta đọc thẳng. Băm nó là khớp 0% mà vẫn trả 200.
        try:
            nguoi["lead_id"] = int(str(cd.ma).strip())
        except (TypeError, ValueError):
            pass
    h = bam_sdt(getattr(dau, "sdt", "") or "")
    if h:
        nguoi["ph"] = [h]
    e = bam_email(email)
    if e:
        nguoi["em"] = [e]

    su_kien = {
        "event_name": settings.FB_CAPI_EVENT_NAME,
        "event_time": int(cd.chot_luc.timestamp()),
        "action_source": _nguon_hanh_dong(cd.loai_ma),
        # Ổn định qua mọi lần chạy lại – xem phần CHỐNG TRÙNG ở đầu tệp.
        "event_id": cd.khoa_chong_trung,
        "user_data": nguoi,
        "custom_data": {"currency": (cd.tien_te or "VND").upper()[:3],
                        "value": float(cd.doanh_thu),
                        "order_id": cd.ma_booking},
    }
    goi: dict = {"data": [su_kien]}
    # `test_event_code` là tham số NGANG HÀNG với `data`, không nằm trong từng sự kiện. Đặt sai
    # chỗ thì Meta vẫn nhận gói nhưng Trình kiểm tra sự kiện không thấy gì, và CNTT sẽ đi tìm lỗi
    # ở chỗ không có lỗi.
    ma_thu = (settings.FB_CAPI_TEST_EVENT_CODE or "").strip()
    if ma_thu:
        goi["test_event_code"] = ma_thu
    return goi


def _bo_gui_that(goi: dict) -> dict:
    """Gọi Graph API thật. Thay được bằng `dat_ham()` để phép thử không chạm Internet."""
    ds = (settings.FB_DATASET_ID or "").strip()
    tk = (settings.FB_CAPI_TOKEN or "").strip()
    url = (f"https://graph.facebook.com/{settings.FB_CAPI_VERSION}/{urllib.parse.quote(ds)}"
           f"/events?access_token={urllib.parse.quote(tk)}")
    req = urllib.request.Request(url, data=json.dumps(goi).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"ok": True, "tra_loi": r.read().decode("utf-8", "replace")[:4000]}
    except urllib.error.HTTPError as ex:
        # Thân lỗi của Meta nói rõ sai ở trường nào – giữ nguyên văn, đừng tóm tắt. Đường dẫn
        # KHÔNG ghi vào đây vì nó mang token.
        try:
            than = ex.read().decode("utf-8", "replace")[:4000]
        except Exception:                                      # noqa: BLE001
            than = ""
        return {"ok": False, "tra_loi": than, "loi": f"HTTP {ex.code}"}
    except Exception as ex:                                    # noqa: BLE001
        return {"ok": False, "tra_loi": "", "loi": f"{type(ex).__name__}: {str(ex)[:300]}"}


_ham_gui = _bo_gui_that


def dat_ham(f=None) -> None:
    """Thay tầng gửi mạng. Gọi không tham số để trả về hàm thật."""
    global _ham_gui
    _ham_gui = f or _bo_gui_that


def _email_cua(db: Session, cd: ChuyenDoiGuiDi) -> str:
    """Email của lead, nếu VTOS có.

    HÔM NAY VTOS KHÔNG CÓ: bảng `leads` không có cột email (quét 07/10/2026). Nên hàm này luôn
    trả rỗng và gói gửi đi không mang trường `em`. Viết ra ở đây thay vì bỏ hẳn, vì hai lẽ:
    thứ nhất, ngày nào bảng lead có cột email thì tỷ lệ khớp của Meta tăng ngay mà không cần
    sửa chỗ nào khác; thứ hai, một dòng nói rõ "chưa có" đọc được hơn một chỗ trống mà sáu
    tháng sau không ai biết là cố ý hay bỏ sót.
    """
    if not cd.lead_id:
        return ""
    l = db.get(Lead, cd.lead_id)
    return getattr(l, "email", "") or ""


def gui(db: Session, gioi_han: int = 100, bay_gio: datetime | None = None) -> dict:
    """Một lượt gửi. Gọi hằng ngày – xem hạn 7 ngày ở đầu tệp.

    Chưa cấu hình thì quay về NGAY và không đổi trạng thái dòng nào.
    """
    cfg = cau_hinh()
    if not cfg["san_sang"]:
        cho = len(CD.cho_gui(db, gioi_han, nen_tang=NEN_TANG))
        return {"san_sang": False, "thieu": cfg["thieu"], "da_gui": 0, "loi": 0,
                "bo_qua": 0, "qua_han": 0, "dang_cho": cho,
                "message": f"Chưa gửi được: thiếu {', '.join(cfg['thieu'])}. "
                           f"{cho} dòng Facebook đang chờ, chưa đụng tới dòng nào. "
                           f"Lưu ý: Meta chỉ nhận chuyển đổi trong {HAN_EVENT_TIME_NGAY} ngày "
                           f"kể từ lúc chốt."}

    bay_gio = bay_gio or datetime.now()
    dem = {"da_gui": 0, "loi": 0, "bo_qua": 0, "qua_han": 0, "thieu_doanh_thu": 0}
    chi_tiet: list[dict] = []

    for cd in CD.cho_gui(db, gioi_han, nen_tang=NEN_TANG):
        dau = db.get(DauQuangCao, cd.dau_id)
        xet_qua = xet(cd, dau, bay_gio)
        if not xet_qua["gui"]:
            tt = xet_qua["trang_thai"]
            if tt:
                cd.trang_thai = tt
                cd.loi_cuoi = xet_qua["ly_do"][:2000]
                dem[tt] = dem.get(tt, 0) + 1
                chi_tiet.append({"id": cd.id, "ma_booking": cd.ma_booking,
                                 "ket_qua": tt, "ly_do": xet_qua["ly_do"]})
            continue
        kq = _ham_gui(goi_tin(cd, dau, _email_cua(db, cd)))
        CD.ghi_ket_qua(db, cd, bool(kq.get("ok")), kq.get("tra_loi", ""), kq.get("loi", ""))
        if kq.get("ok"):
            dem["da_gui"] += 1
        else:
            dem["loi"] += 1
            chi_tiet.append({"id": cd.id, "ma_booking": cd.ma_booking,
                             "ket_qua": "loi", "ly_do": kq.get("loi", "")})
    db.commit()

    return {"san_sang": True, "thieu": [], **dem, "chi_tiet": chi_tiet,
            "message": f"Gửi {dem['da_gui']} chuyển đổi lên Meta, {dem['loi']} lỗi, "
                       f"{dem['bo_qua']} bỏ qua, {dem['qua_han']} quá hạn "
                       f"{HAN_EVENT_TIME_NGAY} ngày"}


def con_lai(db: Session) -> dict:
    """Còn bao nhiêu dòng Facebook chờ, và bao nhiêu trong số đó SẮP quá hạn.

    Con số 'sap_qua_han' là thứ phải đặt lên màn hình: nó đếm ngược số tiền sắp không gửi được
    nữa, và nó là lý do duy nhất đủ nặng để ai đó đi dán token hôm nay thay vì tuần sau.
    """
    hom_nay = datetime.now()
    sap = qua = con = 0
    for cd in db.execute(select(ChuyenDoiGuiDi)
                         .where(ChuyenDoiGuiDi.trang_thai == "cho_gui",
                                ChuyenDoiGuiDi.nen_tang == NEN_TANG)).scalars():
        con += 1
        if cd.chot_luc is None:
            continue
        tuoi = (hom_nay - cd.chot_luc).days
        if tuoi > HAN_EVENT_TIME_NGAY:
            qua += 1
        elif tuoi >= HAN_EVENT_TIME_NGAY - 2:
            sap += 1
    return {"dang_cho": con, "sap_qua_han": sap, "da_qua_han": qua,
            "han_ngay": HAN_EVENT_TIME_NGAY}
