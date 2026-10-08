"""KÉO LEAD TỪ BIỂU MẪU QUẢNG CÁO ZALO (Zalo Ads Form) VỀ BẢNG DẤU NGUỒN QUẢNG CÁO.

────────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO VÒNG ZALO CHỈ KHÉP ĐƯỢC MỘT NỬA, VÀ ĐÓ KHÔNG PHẢI LỖI CỦA MÃ
────────────────────────────────────────────────────────────────────────────────────────────────
Google, Meta và TikTok đều có cửa nhận chuyển đổi gửi từ máy chủ, nên VTOS nói ngược lại được
"khách này đã mua tour, bằng này tiền" và nền tảng học theo. Đã tra tài liệu chính thức ngày
07/10/2026: **Zalo không có cửa như thế.** Zalo chỉ có hai thứ:

  • Zalo Ads Pixel – một đoạn JavaScript gắn lên website, đo chuyển đổi xảy ra TRÊN WEB. Không
    đo được khách chốt qua điện thoại hay tại văn phòng, và cần đội website gắn mã.
  • API này – KÉO dữ liệu khách điền biểu mẫu quảng cáo về.

Nên với Zalo, vòng tròn dừng ở nửa đầu: lấy được lead kèm nguồn quảng cáo, nhưng không nói
ngược lại được. Zalo sẽ KHÔNG tự học. Bù lại, VTOS tự tính được chi phí trên mỗi khách chốt của
kênh Zalo — tính trong nhà, không đẩy ra ngoài.

Viết điều này ra đây thay vì để nó thành một khoảng trống, vì sáu tháng nữa sẽ có người hỏi
"sao Zalo không có bộ gửi như Meta với TikTok" và câu trả lời phải đọc được ngay tại chỗ.

────────────────────────────────────────────────────────────────────────────────────────────────
BA RÀNG BUỘC CỦA CỬA ZALO, LẤY TỪ TÀI LIỆU
────────────────────────────────────────────────────────────────────────────────────────────────
  1. Mỗi lượt gọi chỉ lấy được khoảng thời gian TỐI ĐA 30 NGÀY.
  2. Mỗi trang TỐI ĐA 200 dòng, phải phân trang bằng `offset`.
  3. Cần **Quyền quản lý ads** trên OA — khác với quyền nhắn tin mà VTOS đang dùng. Có token OA
     rồi vẫn có thể bị từ chối nếu chưa cấp thêm quyền này, nên câu trả lời của Zalo được giữ
     NGUYÊN VĂN để lúc ấy đọc ra ngay là thiếu quyền chứ không phải thiếu dữ liệu.

PHẢI KHAI MÃ FORM BẰNG TAY. Cửa `oa/form/get` bắt buộc có `form_id`, và em không tìm thấy cửa
nào liệt kê danh sách form (đã thử, trả 404). Nên mã form khai trong `ZALO_FORM_IDS`.
HỆ QUẢ PHẢI BIẾT: Phòng MKT dựng một biểu mẫu MỚI mà quên khai vào đây thì lead của biểu mẫu ấy
KHÔNG được kéo về, và sẽ không có lỗi nào báo. Vì thế hàm `keo()` luôn trả về danh sách mã form
nó vừa đọc — để người xem đối chiếu với số form đang chạy, thay vì tin rằng im lặng là ổn.

────────────────────────────────────────────────────────────────────────────────────────────────
TÌM SỐ ĐIỆN THOẠI TRONG CÂU TRẢ LỜI – CHỖ MƠ HỒ DUY NHẤT, VÀ CÁCH XỬ LÝ
────────────────────────────────────────────────────────────────────────────────────────────────
Zalo trả câu hỏi dưới dạng `{questionId, title}` và câu trả lời dưới dạng
`{questionId, responses[]}`. **KHÔNG có trường nào nói câu hỏi nào là số điện thoại** — chỉ có
tiêu đề do người dựng biểu mẫu tự gõ. Nên không có cách nào chắc chắn tuyệt đối.

Cách ở đây, theo thứ tự:
  1. Ưu tiên câu hỏi có tiêu đề chứa từ khoá số điện thoại.
  2. Không thấy thì DÒ MẪU: quét mọi câu trả lời, lấy cái nào trông như số điện thoại Việt Nam.
  3. Vẫn không thấy thì ghi dấu KHÔNG có số, chứ không đoán bừa.

Và dù nhánh nào, **toàn bộ gói tin gốc được giữ nguyên văn** trong `than_nguyen_van`. Đó là điều
quan trọng nhất của tệp này: phép dò có thể sai, nhưng dữ liệu gốc thì không mất, nên sửa lại
luôn được mà không phải gọi lại Zalo.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import dau_quang_cao as DQ
from app.services import zalo as Z

API = "https://openapi.zalo.me/v2.0/oa/form/get"

# Ba con số dưới đây là RÀNG BUỘC CỦA ZALO, không phải lựa chọn của mình – xem đầu tệp.
HAN_CUA_SO_NGAY = 30
TOI_DA_MOI_TRANG = 200
# Chặn vòng lặp vô tận nếu Zalo trả `total` sai hoặc trang không bao giờ rỗng.
TOI_DA_SO_TRANG = 50

# Tiêu đề câu hỏi do người dựng biểu mẫu tự gõ, nên danh sách này là GỢI Ý, không phải hàng rào:
# không khớp từ nào thì còn bước dò mẫu phía sau.
TU_KHOA_SDT = ("dien thoai", "điện thoại", "phone", "sdt", "sđt", "so dt", "số đt",
               "mobile", "lien he", "liên hệ", "zalo")


def danh_sach_form() -> list[str]:
    return [x.strip() for x in (settings.ZALO_FORM_IDS or "").split(",") if x.strip()]


def cau_hinh(db: Session) -> dict:
    """Tình trạng cấu hình. KHÔNG trả token, chỉ trả có/không."""
    forms = danh_sach_form()
    thieu = []
    if not Z.token(db):
        thieu.append("token OA Zalo")
    if not forms:
        thieu.append("ZALO_FORM_IDS")
    return {
        "san_sang": not thieu,
        "thieu": thieu,
        "co_token": bool(Z.token(db)),
        "ma_form": forms,
        "so_form": len(forms),
        "han_cua_so_ngay": HAN_CUA_SO_NGAY,
        "toi_da_moi_trang": TOI_DA_MOI_TRANG,
        "huong_dan": "Cửa này cần QUYỀN QUẢN LÝ ADS trên OA – khác quyền nhắn tin VTOS đang "
                     "dùng. Có token rồi vẫn có thể bị từ chối nếu chưa cấp thêm quyền ấy. "
                     "ZALO_FORM_IDS là danh sách mã biểu mẫu, ngăn nhau bằng dấu phẩy; biểu mẫu "
                     "mới mà quên khai thì lead của nó không được kéo về và KHÔNG có lỗi nào báo.",
        "luu_y": "Zalo KHÔNG có cửa nhận chuyển đổi từ máy chủ như Meta và TikTok. Vòng Zalo chỉ "
                 "khép được nửa đầu: lấy lead kèm nguồn quảng cáo, không báo ngược được doanh thu.",
    }


def _goi_that(token: str, form_id: str, tu: int, den: int, offset: int, limit: int) -> dict:
    """Gọi cửa thật. Thay được bằng `dat_ham()` để phép thử không chạm Internet."""
    q = urllib.parse.urlencode({"form_id": form_id, "from_time": tu, "to_time": den,
                                "offset": offset, "limit": limit})
    # Token đi trong HEADER `access_token`, giống `services/zalo.py` đang làm – không đi trên
    # đường dẫn, nên nó không lọt vào nhật ký máy chủ.
    req = urllib.request.Request(f"{API}?{q}", headers={"access_token": token}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as ex:
        try:
            return {"error": ex.code, "message": ex.read().decode("utf-8", "replace")[:1000]}
        except Exception:                                      # noqa: BLE001
            return {"error": ex.code, "message": ""}
    except Exception as ex:                                    # noqa: BLE001
        return {"error": -1, "message": f"{type(ex).__name__}: {str(ex)[:300]}"}


_ham_goi = _goi_that


def dat_ham(f=None) -> None:
    """Thay tầng gọi mạng. Gọi không tham số để trả về hàm thật."""
    global _ham_goi
    _ham_goi = f or _goi_that


def _la_sdt(gia_tri: str) -> str:
    """Chuỗi này có phải số điện thoại Việt Nam không. Trả số đã chuẩn hoá, hoặc rỗng.

    Dùng lại `services/zalo.norm_phone` thay vì viết luật thứ hai – cùng lập luận với các bộ gửi.
    """
    s = str(gia_tri or "")
    if sum(ch.isdigit() for ch in s) < 9:
        return ""
    # Có chữ cái xen vào thì không phải số điện thoại mà là một câu trả lời có lẫn số.
    if any(ch.isalpha() for ch in s):
        return ""
    p = Z.norm_phone(s)
    return p if 9 <= len(p) <= 12 else ""


def sdt_tu_cau_tra_loi(questions: list, answers: list) -> str:
    """Tìm số điện thoại trong một lượt điền biểu mẫu. Xem phần cuối docstring đầu tệp."""
    tieu_de = {}
    for q in questions or []:
        if isinstance(q, dict) and q.get("questionId") is not None:
            tieu_de[str(q["questionId"])] = str(q.get("title") or "").lower()

    # Bước 1 – câu hỏi có tiêu đề nói rõ là số điện thoại.
    for a in answers or []:
        if not isinstance(a, dict):
            continue
        td = tieu_de.get(str(a.get("questionId")), "")
        if any(k in td for k in TU_KHOA_SDT):
            for v in (a.get("responses") or []):
                p = _la_sdt(v)
                if p:
                    return p

    # Bước 2 – dò mẫu trên mọi câu trả lời. Biểu mẫu đặt tiêu đề lạ thì vẫn vớt được.
    for a in answers or []:
        if not isinstance(a, dict):
            continue
        for v in (a.get("responses") or []):
            p = _la_sdt(v)
            if p:
                return p

    # Bước 3 – không đoán bừa. Gói tin gốc vẫn được giữ nguyên văn ở `than_nguyen_van`.
    return ""


def _mot_form(db: Session, token: str, form_id: str, tu: int, den: int) -> dict:
    moi = cu = khong_sdt = 0
    loi = ""
    offset = 0
    for _ in range(TOI_DA_SO_TRANG):
        j = _ham_goi(token, form_id, tu, den, offset, TOI_DA_MOI_TRANG)
        if not isinstance(j, dict) or j.get("error") not in (0, None):
            # Giữ NGUYÊN VĂN – thiếu quyền quản lý ads đọc ra ngay ở đây, chứ không bị tóm tắt
            # thành một câu chung chung rồi mất nửa ngày đi tìm.
            loi = json.dumps({"error": j.get("error"), "message": j.get("message")},
                             ensure_ascii=False)[:1000] if isinstance(j, dict) else str(j)[:1000]
            break
        data = j.get("data") or {}
        cau_hoi = data.get("questions") or []
        dong = data.get("responses") or []
        if not dong:
            break
        for r in dong:
            if not isinstance(r, dict):
                continue
            ma_lead = str(r.get("leadId") or "").strip()
            sdt = sdt_tu_cau_tra_loi(cau_hoi, r.get("answers") or [])
            if not sdt:
                khong_sdt += 1
            st = r.get("submitTime")
            cham = ""
            if isinstance(st, (int, float)) and st > 0:
                cham = f"{datetime.fromtimestamp(float(st)):%Y-%m-%d %H:%M:%S}"
            _, la_moi = DQ.ghi(db, {
                "nen_tang": "zalo",
                # leadId đổi theo TỪNG LẦN submit, nên nó là khoá chống trùng hoàn hảo: kéo lại
                # cùng khoảng thời gian không nhân đôi, mà hai lần khách điền vẫn là hai dòng.
                "loai_ma": "leadgen_id" if ma_lead else "khac",
                "ma": ma_lead,
                "ma_mau_qc": str(r.get("adId") or ""),
                "sdt": sdt,
                "cham_luc": cham,
                "nguon_ghi": "api_zalo_ads",
                "than_nguyen_van": json.dumps(r, ensure_ascii=False)[:20000],
                "ghi_chu": f"Biểu mẫu Zalo Ads {form_id}",
            }, boi="keo-zalo-form")
            moi += la_moi
            cu += (not la_moi)
        offset += len(dong)
        if len(dong) < TOI_DA_MOI_TRANG:
            break
    db.commit()
    return {"ma_form": form_id, "moi": moi, "da_co": cu, "khong_doc_duoc_sdt": khong_sdt,
            "loi": loi}


def keo(db: Session, so_ngay: int = 7, form_id: str = "") -> dict:
    """Kéo lead của `so_ngay` ngày gần nhất về bảng dấu.

    Chưa cấu hình thì quay về NGAY và không gọi mạng.
    """
    cfg = cau_hinh(db)
    if not cfg["san_sang"]:
        return {"san_sang": False, "thieu": cfg["thieu"], "ket_qua": [],
                "message": f"Chưa kéo được: thiếu {', '.join(cfg['thieu'])}."}

    n = max(1, min(int(so_ngay or 7), HAN_CUA_SO_NGAY))
    den = datetime.now()
    tu = den - timedelta(days=n)
    token = Z.token(db)
    forms = [form_id.strip()] if form_id.strip() else cfg["ma_form"]

    ket_qua = [_mot_form(db, token, f, int(tu.timestamp()), int(den.timestamp())) for f in forms]
    moi = sum(r["moi"] for r in ket_qua)
    co_loi = [r for r in ket_qua if r["loi"]]
    return {
        "san_sang": True, "so_ngay": n, "ma_form_da_doc": forms, "ket_qua": ket_qua,
        "moi": moi, "so_form_loi": len(co_loi),
        "message": f"Đọc {len(forms)} biểu mẫu trong {n} ngày, ghi {moi} dấu mới"
                   + (f", {len(co_loi)} biểu mẫu lỗi" if co_loi else ""),
        "luu_y": "Biểu mẫu mới mà chưa khai vào ZALO_FORM_IDS thì KHÔNG được đọc và không có "
                 "lỗi nào báo – đối chiếu 'ma_form_da_doc' với số biểu mẫu Phòng MKT đang chạy.",
    }
