# -*- coding: utf-8 -*-
"""SỔ TÀI SẢN THƯƠNG HIỆU — logo, phông chữ, bộ màu, mẫu ấn phẩm, đồng phục, biển hiệu.

Chủ tịch chốt 18/9/2026, ba điều:

    1. DÙNG CHUNG bảng `fixed_assets` của Kế toán, không dựng bảng riêng cho Marketing.
    2. Dòng thương hiệu chỉ hiện trong danh sách và báo cáo TSCĐ của Kế toán KHI CÓ HOÁ ĐƠN.
    3. Một bộ nhận diện mới phải có HAI CHỮ KÝ: Chủ tịch và P.TGĐ Marketing.

──────────────────────────────────────────────────────────────────────────────────────────────
ĐIỀU 2 VIẾT THÀNH LUẬT GÌ — và vì sao phải nói rõ chỗ này
──────────────────────────────────────────────────────────────────────────────────────────────

"Có hoá đơn" và "có nguyên giá" không phải một câu. Bảng `fixed_assets` KHÔNG có cột hoá đơn; nó
có nhà cung cấp và nguyên giá. Nên luật chạy được là:

    Dòng thương hiệu vào sổ Kế toán KHI VÀ CHỈ KHI nguyên giá đã được khai.

Thực tế hai câu ấy trùng nhau — cái gì mua ngoài mới có nguyên giá để khai. Nhưng chúng KHÔNG
đồng nghĩa, và ghi lại chỗ lệch ấy ở đây rẻ hơn nhiều so với việc ba tháng sau có người đọc mã rồi
tưởng hệ thống đang kiểm chứng từ.

VÌ SAO CẦN LUẬT NÀY: nhãn hiệu do nội bộ tự tạo thì kế toán không được ghi nhận là tài sản
(VAS 04). Logo team tự vẽ có thật và Marketing phải quản nó, nhưng nó không phải một thẻ TSCĐ có
giá trị trên sổ. Để lẫn vào danh sách thẻ TSCĐ thì hồ sơ kiểm kê tài sản cuối năm có mấy chục dòng
logo — tiền không sai (nguyên giá rỗng nên không có gì để cộng), nhưng DANH SÁCH thì sai.

Luật viết MỘT CHỖ, ở `hien_o_so_ke_toan` và `loc_so_ke_toan`. Mọi nơi liệt kê thẻ TSCĐ đều gọi
một trong hai hàm ấy — không nơi nào tự viết lại điều kiện. Hai bản của cùng một luật là hai bản
sẽ lệch nhau đúng vào hôm có một thẻ lạ.

──────────────────────────────────────────────────────────────────────────────────────────────
HAI CHỮ KÝ: KHUÔN ĐÃ CÓ, DÙNG LẠI
──────────────────────────────────────────────────────────────────────────────────────────────

`vehicle_rates` và `guide_rates` đã chạy khuôn này từ 06/5/2026: hai ô cờ + một trạng thái, đủ hai
cờ thì trạng thái chuyển. Ở đây là `th_ky_chutich` + `th_ky_ptgd_mkt`.

MỘT NGƯỜI KHÔNG KÝ THAY CẢ HAI VAI. Chủ tịch đi qua được gần hết các cửa trong hệ (tham số
`chu_tich_mo_het_cua`), nhưng KHÔNG đi qua cửa này — vì thứ nó chặn không phải là quyền, mà là
việc sổ ghi một chữ ký P.TGĐ mà P.TGĐ chưa hề bấm. Đó là ghi sai sổ, và con số sai ấy không ai đọc
lại mà biết được.
"""
from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assets import TH_LOAI, TH_TRANG_THAI, FixedAsset  # noqa: F401  (tái xuất cho màn hình)

# Ai ký. Đọc từ đây chứ không viết thẳng chuỗi vào chỗ kiểm: hai chỗ viết cùng một danh sách là
# hai chỗ sẽ lệch nhau khi có người đổi.
VAI_KY = {"chutich": "th_ky_chutich", "ptgd_mkt": "th_ky_ptgd_mkt"}
# Tham số mang chữ ký của quyết định (services/rules.DEFAULT_PARAMS). Đọc SỐNG, không chép số.
THAM_SO_HAI_CHU_KY = "thuong_hieu_vai_ky"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# LUẬT: dòng nào của sổ thương hiệu được vào sổ Kế toán
# ══════════════════════════════════════════════════════════════════════════════════════════════

def hien_o_so_ke_toan(a: FixedAsset) -> bool:
    """Thẻ này có hiện trong danh sách / báo cáo TSCĐ của Kế toán không.

    Thẻ TSCĐ thường: LUÔN hiện. Thẻ thương hiệu: chỉ hiện khi nguyên giá đã khai.

    `cost` rỗng KHÁC `cost` bằng 0, và khác biệt ấy là cả luật này. Rỗng = chưa ai khai nguyên giá
    (nội bộ tự tạo). 0 = có người khai rằng nó bằng không — một câu trả lời, và thẻ có câu trả lời
    thì thuộc về sổ Kế toán. Quy ước "rỗng khác 0" là quy ước chung của lược đồ VTOS từ đợt K2.
    """
    if not a.th_so:
        return True
    return a.cost is not None


def loc_so_ke_toan(q):
    """Cùng LUẬT ấy, viết bằng SQL, cho các chỗ liệt kê đọc thẳng từ cơ sở dữ liệu.

    Hai bản của một luật là chỗ dễ lệch nhất trong cả tệp này, nên có một phép thử chéo bắt buộc
    `hien_o_so_ke_toan` và `loc_so_ke_toan` ra CÙNG một tập thẻ trên cùng một sổ.
    """
    return q.where(sa.or_(FixedAsset.th_so.is_(False), FixedAsset.cost.is_not(None)))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HAI CHỮ KÝ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def du_hai_chu_ky(a: FixedAsset) -> bool:
    return bool(a.th_ky_chutich and a.th_ky_ptgd_mkt)


def con_thieu_chu_ky(a: FixedAsset) -> list[str]:
    """Còn thiếu chữ ký của ai. Nói ra tên vai, không nói "chưa đủ" – người đọc phải biết đi hỏi ai."""
    return [v for v, cot in VAI_KY.items() if not getattr(a, cot)]


def ky(db: Session, a: FixedAsset, vai: str, boi: str) -> dict:
    """Một vai ký một thẻ. Đủ hai chữ ký thì thẻ chuyển sang `dang_dung`.

    `vai` là VAI TRÒ CỦA NGƯỜI ĐANG BẤM, do lớp API đọc từ tài khoản – KHÔNG nhận từ thân yêu cầu.
    Nhận từ thân yêu cầu thì ai cũng tự khai mình là Chủ tịch.
    """
    if vai not in VAI_KY:
        raise ValueError(f"Vai trò {vai!r} không nằm trong danh sách được ký bộ nhận diện "
                         f"({', '.join(VAI_KY)})")
    if not a.th_so:
        raise ValueError("Thẻ này không thuộc sổ tài sản thương hiệu – không có việc ký ở đây")
    setattr(a, VAI_KY[vai], True)

    chuyen = False
    if du_hai_chu_ky(a) and a.th_trang_thai == "nhap":
        # Đủ chữ ký thì chuyển sang ĐANG DÙNG – nhưng phải có ngày hiệu lực, nếu không thì không ai
        # biết từ hôm nào phải in theo bản mới. Chưa khai ngày thì lấy hôm nay và NÓI RA.
        if a.th_hieu_luc_tu is None:
            a.th_hieu_luc_tu = date.today()
        a.th_trang_thai = "dang_dung"
        chuyen = True

    from app.services import rules as R
    R.audit(db, boi, "", "ky_tai_san_thuong_hieu", f"fixed_assets:{a.id}",
            after={"vai": vai, "du_hai_chu_ky": du_hai_chu_ky(a), "trang_thai": a.th_trang_thai})
    db.flush()
    return {"id": a.id, "da_ky": vai, "du_hai_chu_ky": du_hai_chu_ky(a),
            "con_thieu": con_thieu_chu_ky(a), "trang_thai": a.th_trang_thai,
            "chuyen_sang_dang_dung": chuyen,
            "message": ("Đã đủ hai chữ ký – bản này là bản ĐANG DÙNG từ "
                        f"{a.th_hieu_luc_tu:%d/%m/%Y}." if chuyen else
                        f"Đã ghi chữ ký {vai}. Còn thiếu: {', '.join(con_thieu_chu_ky(a)) or 'không'}.")}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỌC SỔ
# ══════════════════════════════════════════════════════════════════════════════════════════════

def mot_dong(a: FixedAsset) -> dict:
    return {
        "id": a.id, "ma": a.code, "ten": a.name,
        "loai": a.th_loai, "loai_ten": TH_LOAI.get(a.th_loai, a.th_loai or ""),
        "phien_ban": a.th_phien_ban,
        "hieu_luc_tu": a.th_hieu_luc_tu, "hieu_luc_den": a.th_hieu_luc_den,
        "trang_thai": a.th_trang_thai,
        "trang_thai_ten": TH_TRANG_THAI.get(a.th_trang_thai, a.th_trang_thai or ""),
        "noi_su_dung": a.th_noi_su_dung,
        "ky_chutich": a.th_ky_chutich, "ky_ptgd_mkt": a.th_ky_ptgd_mkt,
        "con_thieu_chu_ky": con_thieu_chu_ky(a),
        # Nguyên giá là chỗ quyết định thẻ có vào sổ Kế toán hay không, nên nó phải HIỆN RA ở đây,
        # kèm câu trả lời sẵn – để người của Marketing không phải đi đoán vì sao thẻ của mình
        # không thấy trong danh sách TSCĐ.
        "nguyen_gia": a.cost,
        "vao_so_ke_toan": hien_o_so_ke_toan(a),
        "vi_sao": ("có nguyên giá – vào sổ TSCĐ như TSCĐ vô hình" if a.cost is not None
                   else "chưa khai nguyên giá – nội bộ tự tạo, chỉ Marketing thấy"),
        "phap_nhan": a.project_code, "bo_phan": a.department,
    }


def bang(db: Session, loai: str = "", trang_thai: str = "") -> dict:
    q = select(FixedAsset).where(FixedAsset.th_so.is_(True)).order_by(
        FixedAsset.th_loai, FixedAsset.code)
    if loai:
        q = q.where(FixedAsset.th_loai == loai)
    if trang_thai:
        q = q.where(FixedAsset.th_trang_thai == trang_thai)
    rows = [mot_dong(a) for a in db.execute(q).scalars()]
    return {
        "rows": rows,
        "dem": {
            "tong": len(rows),
            "dang_dung": sum(1 for r in rows if r["trang_thai"] == "dang_dung"),
            "cho_chu_ky": sum(1 for r in rows if r["con_thieu_chu_ky"]),
            "vao_so_ke_toan": sum(1 for r in rows if r["vao_so_ke_toan"]),
        },
        "loai": TH_LOAI, "trang_thai_ds": TH_TRANG_THAI,
    }


def ban_dang_dung(db: Session, loai: str, ngay: date | None = None) -> FixedAsset | None:
    """Bản nào của loại này đang có hiệu lực vào một ngày. Câu hỏi thật của người đi in ấn phẩm.

    Không lấy `th_trang_thai == "dang_dung"` làm câu trả lời duy nhất: trạng thái là thứ người ta
    quên đổi. Ngày hiệu lực là thứ đã ký, nên nó là căn cứ; trạng thái chỉ để lọc bản nháp ra.
    """
    d = ngay or date.today()
    q = (select(FixedAsset)
         .where(FixedAsset.th_so.is_(True), FixedAsset.th_loai == loai,
                FixedAsset.th_trang_thai != "nhap",
                FixedAsset.th_hieu_luc_tu.is_not(None), FixedAsset.th_hieu_luc_tu <= d,
                sa.or_(FixedAsset.th_hieu_luc_den.is_(None), FixedAsset.th_hieu_luc_den >= d))
         .order_by(FixedAsset.th_hieu_luc_tu.desc(), FixedAsset.id.desc()))
    return db.execute(q).scalars().first()
