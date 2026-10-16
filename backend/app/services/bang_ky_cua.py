# -*- coding: utf-8 -*-
"""BẢNG KÝ CỬA — những lần NỚI QUYỀN có chữ ký, và mỗi lần nới ấy mở ra bao nhiêu cửa.

Đợt E12, 13/10/2026. Chủ tịch chốt chỗ đặt: nối vào hàng việc chờ quyết trên bàn làm việc, bấm vào
xổ ra chi tiết.

VÌ SAO CÓ TỆP NÀY

Ngày 11/10/2026 Chủ tịch ký một dòng — `VAI_KE_THUA = {"ketoan_truong": "ketoan"}` — và một dòng
ấy mở THÊM 514 cửa cho Kế toán trưởng, từ 13 lên 527. Con số 514 không nằm trong dòng ký; nó là
HỆ QUẢ của dòng ấy, và phải đo mới biết. Hôm ký thì em đo tay rồi báo miệng; sau đó không chỗ nào
trong hệ thống còn nói ra con số đó nữa.

Đó là chỗ hỏng: một quyết định nới quyền mà hệ quả của nó chỉ tồn tại trong một tin nhắn. Sáu
tháng sau, người rà soát đọc `VAI_KE_THUA` thấy đúng một dòng ba chữ, và không có cách nào biết
dòng ấy đang mở bao nhiêu cửa — trừ khi họ tự viết lại đúng phép đo này.

BẢNG NÀY ĐẾM LẠI MỖI LẦN MỞ MÀN HÌNH, không chép lại con số đã đo. Chép thì con số đóng băng ở
ngày đo, còn cửa thì mỗi đợt lại thêm; một con số cũ trông y hệt một con số đúng.

ĐIỀU TỆP NÀY KHÔNG LÀM: không cấp, không thu, không đổi một quyền nào. Nó chỉ ĐỌC và ĐẾM.
"""
from app.models.core import ROLES
from app.services import vai_ke_thua as VKT


def _cua() -> list[tuple[str, str, set | None]]:
    """(đường dẫn, phương thức, tập vai) của mọi cửa API.

    Đọc TỪ CHỮ KÝ hàm qua `vai_tro_yeu_cau` chứ không phân tích mã nguồn — cùng cách `test_lg1`
    và `test_ks2` đang đọc. Phân tích mã thì luôn có một cách viết khác lọt qua; đọc chữ ký thì
    thấy đúng những gì thật sự đang chặn.

    `None` nghĩa là cửa KHÔNG khai vai: mọi người đã đăng nhập đều gọi được. Rỗng khác không —
    một cửa không khai vai không phải một cửa đóng, nó là một cửa mở cho tất cả.
    """
    from app.main import app
    ra = []
    for r in app.routes:
        p = getattr(r, "path", "")
        if not p.startswith("/api/v1"):
            continue
        vai = None
        for d in (getattr(getattr(r, "dependant", None), "dependencies", None) or []):
            v = getattr(getattr(d, "call", None), "vai_tro_yeu_cau", None)
            if v:
                vai = set(v)
        ra.append((p, sorted(getattr(r, "methods", {"?"}))[0], vai))
    return ra


def dem_cua(vai: str) -> dict:
    """Vai này mở được bao nhiêu cửa, tách ra cửa khai đích danh và cửa mở cho mọi người."""
    dich_danh = mo_het = 0
    for _p, _m, v in _cua():
        if v is None:
            mo_het += 1
        elif vai in v:
            dich_danh += 1
    return {"dich_danh": dich_danh, "mo_het": mo_het, "tong": dich_danh + mo_het}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NHỮNG LẦN NỚI QUYỀN CÓ CHỮ KÝ
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Mỗi dòng phải có: ký cái gì, ai ký, ngày nào, và MỘT PHÉP ĐO nói ra hệ quả. Dòng không đo được
# hệ quả thì không thuộc bảng này — bảng này tồn tại để trả lời câu "dòng ấy mở ra bao nhiêu", và
# một dòng không trả lời được câu ấy chỉ làm bảng dài ra.
#
# KHÔNG CHÉP CON SỐ VÀO ĐÂY. Con số do `bang_ky()` đếm lại lúc đọc.
QUYET_DINH = (
    {
        "ma": "ke-thua-ketoan-truong",
        "ten": "Kế toán trưởng thấy mọi cửa Kế toán thấy",
        "nguoi_ky": "chutich",
        "ngay_ky": "11/10/2026",
        "can_cu": "Chủ tịch chốt 11/10/2026 — nới hết quyền Kế toán trưởng, kể cả cửa lương.",
        "khai_o": "services/vai_ke_thua.py :: VAI_KE_THUA",
        "dao_lai": "Xoá dòng `ketoan_truong` khỏi `VAI_KE_THUA` — đúng một dòng.",
        "vai": "ketoan_truong",
        "vai_cha": "ketoan",
    },
)


def bang_ky() -> list[dict]:
    """Một dòng cho mỗi quyết định nới quyền, kèm con số ĐẾM LẠI lúc này."""
    ra = []
    for q in QUYET_DINH:
        vai, cha = q["vai"], q.get("vai_cha") or ""
        d = dem_cua(vai)
        # CỬA VAI CON THẤY **VÌ** VAI CHA THẤY.
        #
        # Bản đầu của phép đếm này viết `vai not in tuple(v)` để loại ra những cửa khai đích danh
        # cho vai con, và nó trả về **0**. Lý do: `api/deps.py::require_roles` gọi `VKT.mo_rong`
        # NGAY LÚC KHAI rồi mới ghi vào `vai_tro_yeu_cau` — nên tới lúc đọc, vai con ĐÃ nằm sẵn
        # trong mọi cửa của vai cha. Phép suy chạy trước, phép đo chạy sau.
        #
        # Hệ quả, và phải nói thẳng chứ không giấu sau một con số: tại thời điểm ĐỌC, hệ thống
        # KHÔNG phân biệt được "cửa này mở ra nhờ dòng kế thừa" với "cửa này dù sao cũng khai cho
        # vai con". Nên con số dưới đây là **cửa vai con thấy VÌ vai cha thấy** — và đó cũng đúng
        # là con số cần cho việc rà soát: xoá dòng kế thừa thì mất đúng ngần ấy cửa.
        nho_ke_thua = 0
        if cha:
            for _p, _m, v in _cua():
                if v and cha in v and vai in v:
                    nho_ke_thua += 1
        ra.append({
            **{k: v for k, v in q.items() if k not in ("vai", "vai_cha")},
            "vai": vai, "ten_vai": ROLES.get(vai, vai),
            "vai_cha": cha, "ten_vai_cha": ROLES.get(cha, cha) if cha else "",
            "cua_dich_danh": d["dich_danh"], "cua_mo_het": d["mo_het"], "cua_tong": d["tong"],
            "cua_nho_ke_thua": nho_ke_thua,
            "cua_luong_da_ky": [{"phuong_thuc": m, "duong_dan": p} for m, p in VKT.CUA_LUONG_DA_KY],
            "can_cu_cua_luong": VKT.CAN_CU_CUA_LUONG,
        })
    return ra


def dong_ban_lam_viec() -> list[dict]:
    """Dòng cho bàn làm việc Chủ tịch. Mang theo CHI TIẾT để bấm vào là xổ ra, không phải đi trang khác.

    Vì sao mang cả chi tiết thay vì một đường dẫn: bảng này KHÔNG phải một việc chờ bấm — nó là
    một điều cần ĐỌC LẠI. Dẫn sang một màn hình khác thì phải mở một khoá menu mới, tức xin thêm
    quyền cho một loạt vai mà chưa ai ký — đúng cái việc bảng này sinh ra để canh.
    """
    ra = []
    for d in bang_ky():
        ra.append({
            "label": f"Bảng ký quyền — {d['ten_vai']}: {d['cua_tong']} cửa "
                     f"({d['cua_nho_ke_thua']} cửa nhờ một dòng ký)",
            "href": "", "chi_tiet": d,
        })
    return ra
