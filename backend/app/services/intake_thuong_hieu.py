# -*- coding: utf-8 -*-
"""CỬA NHẬP SỔ TÀI SẢN THƯƠNG HIỆU — logo, phông chữ, bộ màu, mẫu ấn phẩm, đồng phục, biển hiệu.

Ranh giới Chủ tịch đặt 09/9/2026: phần mềm viết cấu trúc và phép tính; SỐ LIỆU do người của phòng
tự nhập. Hệ quả trực tiếp cho tệp này: sổ tài sản thương hiệu không có cửa thì nó là VIỆC CÒN
THIẾU, không phải chỗ để ai đó đổ sẵn một danh sách logo vào cơ sở dữ liệu.

──────────────────────────────────────────────────────────────────────────────────────────────
CỬA NÀY GHI VÀO BẢNG CỦA KẾ TOÁN, NÊN NÓ PHẢI TỰ CHẶN MÌNH
──────────────────────────────────────────────────────────────────────────────────────────────

`bang_dich` là `fixed_assets` — đúng bảng mà Kế toán ghi thẻ TSCĐ. Hai cửa cùng ghi một bảng là
chuyện bình thường trong khuôn này, nhưng ở đây có một chỗ phải khoá lại:

    Cửa này CHỈ được tạo thẻ có `th_so = True`, và KHÔNG được khai nguyên giá.

Vì sao không cho khai nguyên giá: nguyên giá là con số quyết định thẻ có vào sổ Kế toán hay không
(xem `tai_san_thuong_hieu.hien_o_so_ke_toan`). Để nhân viên Marketing gõ nguyên giá ở đây là để
một người ngoài phòng Kế toán tự đẩy một thẻ vào bảng cân đối. Bộ nhận diện MUA NGOÀI có hoá đơn
thì Kế toán ghi tăng bằng cửa của họ ở màn hình Tài sản, rồi bật `th_so` — hai việc, hai người,
đúng như ngoài đời.

──────────────────────────────────────────────────────────────────────────────────────────────
KHOÁ CHỐNG TRÙNG: LOẠI + PHIÊN BẢN
──────────────────────────────────────────────────────────────────────────────────────────────

Không lấy mã thẻ làm khoá, vì mã do hệ thống cấp. Một bộ nhận diện được nhận ra bằng "logo bản
v3", và nạp lại cùng một tệp thì phải THAY bản cũ chứ không đẻ ra logo v3 thứ hai.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assets import TH_LOAI, TH_TRANG_THAI, FixedAsset

# Tiền tố mã thẻ của cửa này. Nhìn mã là biết thẻ đến từ sổ thương hiệu chứ không từ Kế toán ghi
# tăng — phân biệt bằng MÃ cho người đọc, còn máy thì đọc cột `th_so`.
TIEN_TO = "TH-"


def _ngay(v):
    from app.services.intake import _ngay as n
    return n(v)


def _ma_moi(db: Session, loai: str) -> str:
    """TH-LOGO-0001. Đếm theo LOẠI để mã nói được cái gì, thay vì một dãy số chạy chung."""
    # Lọc theo tiền tố là ĐÚNG RỒI, nhưng ĐẾM số dòng khớp thì vẫn hỏng khi có dòng bị xoá:
    # số lùi một bước và mã kế tiếp đụng một mã đang còn sống. Lấy số LỚN NHẤT thì không.
    from app.services.ma_tu_sinh import tiep_theo
    dau = f"{TIEN_TO}{(loai or 'KHAC').upper()[:8]}-"
    return tiep_theo(db, FixedAsset, dau, 4)


def _tim(db: Session, loai: str, phien_ban: str) -> FixedAsset | None:
    if not loai or not phien_ban:
        return None
    return db.execute(select(FixedAsset).where(
        FixedAsset.th_so.is_(True),
        FixedAsset.th_loai == loai,
        func.upper(FixedAsset.th_phien_ban) == phien_ban.strip().upper())).scalars().first()


def kiem(db: Session, r: dict) -> tuple[list, list, str | None]:
    """Kiểm một dòng. Trả (lỗi, cảnh báo, khoá trùng). KHÔNG ghi gì.

    Ranh giới lỗi / cảnh báo giữ đúng quy ước của khuôn: chỉ báo LỖI khi dòng ấy sẽ làm SAI một
    con số hoặc làm hỏng một quyết định; thiếu thông tin thì cảnh báo.
    """
    loi, cb = [], []

    loai = str(r.get("loai") or "").strip()
    pb = str(r.get("phien_ban") or "").strip()
    if loai and loai not in TH_LOAI:
        loi.append(f"Loại '{loai}' không có trong danh mục ({', '.join(list(TH_LOAI)[:6])}…)")

    tt = str(r.get("trang_thai") or "").strip()
    if tt and tt not in TH_TRANG_THAI:
        loi.append(f"Trạng thái '{tt}' không hợp lệ ({', '.join(TH_TRANG_THAI)})")
    if tt == "dang_dung":
        # Đây là chỗ cửa tự chặn mình. "Đang dùng" là kết quả của HAI CHỮ KÝ, không phải một ô để
        # gõ vào. Cho gõ thì một bộ nhận diện có hiệu lực mà không ai ký — và đúng cái ô chữ ký ấy
        # là thứ Chủ tịch chốt ngày 18/9.
        loi.append("Không đặt thẳng trạng thái 'Đang dùng' ở cửa nhập: bản mới chỉ có hiệu lực khi "
                   "đủ HAI chữ ký (Chủ tịch và P.TGĐ Marketing). Để trống hoặc ghi 'nhap'")

    tu, den = None, None
    for o, ten in (("hieu_luc_tu", "Hiệu lực từ"), ("hieu_luc_den", "Hiệu lực đến")):
        try:
            d = _ngay(r.get(o))
        except ValueError as ex:
            loi.append(f"{ten}: {ex}")
            continue
        if o == "hieu_luc_tu":
            tu = d
        else:
            den = d
    if tu and den and den < tu:
        loi.append(f"Hiệu lực đến ({den:%d/%m/%Y}) đứng trước hiệu lực từ ({tu:%d/%m/%Y})")

    if r.get("nguyen_gia") not in (None, ""):
        # Xem ghi chú đầu tệp: nguyên giá là cửa vào sổ Kế toán, không mở ở đây.
        loi.append("Nguyên giá KHÔNG khai ở cửa này. Bộ nhận diện mua ngoài có hoá đơn thì Kế toán "
                   "ghi tăng ở màn hình Tài sản; cửa này chỉ quản phần nhận diện")

    if not pb:
        cb.append("Chưa ghi phiên bản. Không có phiên bản thì ba tháng sau không ai trả lời được "
                  "'bản nào đang dùng' – dòng vẫn được nhận, nhưng nên điền")
    if not str(r.get("noi_su_dung") or "").strip():
        cb.append("Chưa ghi nơi đang dùng (biển hiệu, đồng phục, website, ấn phẩm). Đổi bộ nhận "
                  "diện mà không biết nó đang dán ở đâu thì không lên được danh sách việc phải thay")

    cu = _tim(db, loai, pb)
    return loi, cb, (cu.code if cu else None)


def nap(db: Session, r: dict, boi: str) -> tuple[FixedAsset, str]:
    """Ghi một dòng. Nạp lại cùng loại + cùng phiên bản thì THAY, không đẻ thẻ thứ hai."""
    from app.services import rules as R

    loai = str(r.get("loai") or "").strip()
    pb = str(r.get("phien_ban") or "").strip()
    a = _tim(db, loai, pb)
    moi = a is None
    if moi:
        a = FixedAsset(
            code=_ma_moi(db, loai),
            # `start_date` là cột NOT NULL của bảng Kế toán (ngày bắt đầu tính khấu hao). Thẻ nhận
            # diện không trích khấu hao, nhưng cột vẫn phải có giá trị – lấy ngày hiệu lực nếu có,
            # không thì hôm nay. `depr_months = 0` nghĩa là KHÔNG trích, đúng quy ước của bảng.
            start_date=_ngay(r.get("hieu_luc_tu")) or date.today(),
            depr_months=0, kind="vo_hinh", asset_account="213", depr_account="2143",
            th_so=True, created_by=(boi or "")[:50])
        db.add(a)

    a.name = (str(r.get("ten") or "").strip() or TH_LOAI.get(loai, "Tài sản thương hiệu"))[:200]
    a.th_loai = loai[:20]
    a.th_phien_ban = pb[:30]
    a.th_hieu_luc_tu = _ngay(r.get("hieu_luc_tu"))
    a.th_hieu_luc_den = _ngay(r.get("hieu_luc_den"))
    a.th_noi_su_dung = str(r.get("noi_su_dung") or "").strip()[:200]
    a.department = str(r.get("bo_phan") or "marketing").strip()[:20]
    a.project_code = str(r.get("phap_nhan") or "").strip()[:40]
    a.note = str(r.get("ghi_chu") or "").strip()[:300]
    # Trạng thái KHÔNG nhận từ người nhập (xem `kiem`). Thẻ mới luôn là nháp; thẻ đã có thì giữ
    # nguyên trạng thái đang chạy – nạp lại một bản đã ký không được làm mất hai chữ ký ấy.
    if moi:
        a.th_trang_thai = "nhap"
    db.flush()

    R.audit(db, boi, "", "nap_tai_san_thuong_hieu", f"fixed_assets:{a.id}",
            after={"ma": a.code, "loai": a.th_loai, "phien_ban": a.th_phien_ban,
                   "trang_thai": a.th_trang_thai, "moi": moi})
    return a, ("moi" if moi else "thay_ban_cu")


def bo_nap(_c) -> dict:
    """Khai cửa. `_c` là hàm khai cột CỦA KHUNG – nhận từ intake.py, không tự viết lại."""
    return {
        "tai_san_thuong_hieu": {
            "bang_dich": "fixed_assets",
            "phong_ban": "marketing",
            "ten": "Tài sản thương hiệu (logo, phông chữ, bộ màu, ấn phẩm, đồng phục, biển hiệu)",
            "mo_ta":
                "Sổ nhận diện của Vietourist. Chủ tịch chốt 18/9/2026: sổ này DÙNG CHUNG bảng tài "
                "sản cố định của Kế toán chứ không dựng bảng riêng — vì một bộ nhận diện mua "
                "ngoài có hoá đơn đúng là TSCĐ vô hình, nó vốn thuộc về đó.\n\n"
                "CỬA NÀY KHÔNG KHAI NGUYÊN GIÁ. Nguyên giá là con số quyết định thẻ có vào danh "
                "sách TSCĐ của Kế toán hay không: khai rồi thì thẻ vào sổ như TSCĐ vô hình; để "
                "trống thì đó là nhận diện nội bộ tự tạo, chỉ Marketing thấy. Bộ nhận diện mua "
                "ngoài thì Kế toán ghi tăng ở màn hình Tài sản — hai việc, hai người.\n\n"
                "TRẠNG THÁI 'ĐANG DÙNG' KHÔNG GÕ ĐƯỢC Ở ĐÂY. Một bản mới chỉ có hiệu lực khi đủ "
                "HAI chữ ký: Chủ tịch và P.TGĐ Marketing. Nhập xong, thẻ nằm ở trạng thái nháp và "
                "chờ ký ở màn hình Marketing.\n\n"
                "Nạp lại cùng một loại và cùng một phiên bản thì THAY bản cũ, không đẻ ra bản thứ "
                "hai — và không làm mất chữ ký đã có.",
            "khoa_chong_trung": "Loại + phiên bản (ví dụ: Logo + v3)",
            "cot": [
                _c("loai", "Loại", True, kieu="chon", vi_du="logo", chon=TH_LOAI),
                _c("ten", "Tên gọi", vi_du="Logo Vietourist bản kỷ niệm 15 năm",
                   ghi_chu="để trống thì lấy tên của loại"),
                _c("phien_ban", "Phiên bản", vi_du="v3",
                   ghi_chu="thứ người ta gọi nhau hằng ngày: v3, 2027, bản Tết. Cùng loại + cùng "
                           "phiên bản là CÙNG MỘT bản – nạp lại sẽ thay"),
                _c("hieu_luc_tu", "Hiệu lực từ", kieu="ngay", vi_du="2027-01-01",
                   ghi_chu="từ ngày này thì in ấn phẩm theo bản này. Chưa ký thì chưa có hiệu lực "
                           "dù ngày đã tới"),
                _c("hieu_luc_den", "Hiệu lực đến", kieu="ngay",
                   ghi_chu="để trống nghĩa là chưa có bản thay – đó là trạng thái bình thường"),
                _c("noi_su_dung", "Đang dùng ở đâu", vi_du="Biển hiệu văn phòng, đồng phục, website",
                   ghi_chu="đổi bộ nhận diện thì đây chính là danh sách việc phải thay"),
                _c("phap_nhan", "Pháp nhân áp dụng", vi_du="VTD",
                   ghi_chu="để trống nghĩa là áp dụng cho cả nhóm"),
                _c("bo_phan", "Bộ phận giữ", vi_du="marketing"),
                _c("trang_thai", "Trạng thái", kieu="chon", chon=TH_TRANG_THAI,
                   ghi_chu="chỉ để trống hoặc 'nhap'. 'Đang dùng' là KẾT QUẢ của hai chữ ký, "
                           "không phải một ô để gõ"),
                _c("ghi_chu", "Ghi chú"),
            ],
            "kiem": kiem, "nap": nap,
        },
    }


def vai_tro(quan_tri: tuple) -> dict:
    """Ai bấm được nút nạp.

    Marketing giữ sổ này, nên Marketing nhập. KHÔNG mở cho Kế toán ở cửa này — không phải vì
    không tin, mà vì cửa của Kế toán với bảng ấy là màn hình Tài sản, nơi có ô nguyên giá và có
    định khoản. Hai cửa cùng ghi một bảng thì mỗi cửa phải giữ đúng phần việc của mình, nếu không
    thì sáu tháng sau không ai trả lời được "thẻ này vào hệ bằng đường nào".
    """
    return {"tai_san_thuong_hieu": quan_tri + ("nv_mkt", "ptgd_mkt")}
