# -*- coding: utf-8 -*-
"""TC-32 · Khối 04c bản vẽ V1.4 — TỒN ĐỌNG THEO BỘ PHẬN.

Anh Tuấn hỏi 14/9/2026: bốn khối còn "Chưa kết nối", cái nào thiếu SỐ THẬT, cái nào chỉ thiếu một
BẢNG KHAI. Khối này là cái rẻ nhất — nhưng chỉ rẻ nếu làm đúng ba chỗ dưới đây. Làm sai bất kỳ chỗ
nào thì nó ra một con số to, trông hợp lý, và sai.

════════════════════════════════════════════════════════════════════════════════════════════════
BA CHỖ DỄ SAI, VÀ VÌ SAO
════════════════════════════════════════════════════════════════════════════════════════════════

1 · KHÔNG PHẢI CẢNH BÁO NÀO CŨNG LÀ "HỒ SƠ QUÁ HẠN"

   Đo bản chạy thật sáng 14/9: 1.476 cảnh báo đang mở, và 60/60 dòng máy chủ gửi kèm màn hình đều
   là `dt_thieu_nguon` — loại do vòng TC-29 sinh ra, nghĩa là "dòng dòng tiền này chưa có nguồn
   số". Đó là MỘT Ô BẢNG CHƯA AI NẠP, không phải một hồ sơ nằm quá hạn ở phòng nào.

   Bản vẽ ghi cột "Hồ sơ quá hạn". Đếm thẳng bảng cảnh báo thì màn hình Chủ tịch báo ~1.476 hồ sơ
   quá hạn, trong khi số hồ sơ quá hạn thật nhỏ hơn rất nhiều. Đúng kiểu con số nhìn hợp lý mà sai
   — thứ Chủ tịch sẽ dùng để quyết.

   `dt_thieu_nguon` đã có chỗ của nó: khối 06 Dòng tiền, cột "Nguồn số", kèm bộ phận phải nạp. Đưa
   nó sang đây là đếm cùng một việc hai lần ở hai khối cạnh nhau.

2 · LOẠI TRỪ BẰNG DANH SÁCH ĐEN, KHÔNG PHẢI DANH SÁCH TRẮNG

   `canh_bao_trinh_bay.py` đã ĐO và ghi lại: bộ mã loại cảnh báo là BỘ MỞ — có chỗ sinh cảnh báo
   truyền `kind` bằng biến, nên không tồn tại danh sách tĩnh nào đọc ra đủ mọi mã.

   Hệ quả bắt buộc: nếu ở đây khai "chỉ những loại này mới tính", thì mỗi loại mới sinh ra sau này
   sẽ ÂM THẦM BIẾN MẤT khỏi khối 04c, và không ai biết vì màn hình vẫn có số. Danh sách đen thì
   ngược lại: loại mới hiện ra ngay, ai đó nhìn thấy và quyết định nó thuộc đâu.

   Mỗi dòng trong danh sách đen BẮT BUỘC có lý do viết ra. "Loại này không tính" là lối thoát dễ
   nhất cho một loại chưa ai nghĩ tới.

3 · MỖI HỒ SƠ CHỈ TÍNH MỘT LẦN — VÀ CHỈ THUỘC MỘT BỘ PHẬN

   Bản vẽ nhấn mạnh điều thứ nhất: một hồ sơ phát ba cảnh báo vẫn là một hồ sơ. Nên đếm theo `ref`
   (hồ sơ mà cảnh báo trỏ tới), không đếm theo dòng cảnh báo.

   Điều thứ hai bản vẽ không nói nhưng suy ra từ nó: cùng một hồ sơ có thể có hai cảnh báo giao
   cho hai người ở hai phòng. Đếm cả hai thì hồ sơ ấy tính hai lần ở cấp công ty — vừa phá đúng
   luật vừa viết ra. Nên một hồ sơ thuộc bộ phận của CẢNH BÁO MỞ SỚM NHẤT của nó: cái bắt đầu
   việc. Cộng các bộ phận ra đúng tổng số hồ sơ.

════════════════════════════════════════════════════════════════════════════════════════════════
BỘ PHẬN LẤY TỪ ĐÂU — VÀ VÌ SAO KHÔNG KHAI BẢNG "LOẠI → BỘ PHẬN"

Vòng PQ-9 (11/9) đã dựng sẵn chuỗi: cảnh báo → người phụ trách → `users.department`. Không cần
thêm bảng nào, không cần ai nhập gì — đúng ranh giới 09/9.

Chuỗi này hỏng CÓ TIẾNG: suy không ra chủ thì ô để trống, và ô trống được ĐẾM thành một dòng
riêng. Một bảng khai loại → bộ phận thì hỏng IM LẶNG: loại thiếu một dòng là hồ sơ biến mất.

HAI CỘT CHỦ, VÀ ĐÂY LÀ MỘT CHỖ NỢ CỦA KHO. `alerts` có `nguoi_nhan_id` (KS-4, "người CỤ THỂ phải
làm") và `nguoi_phu_trach` (PQ-9, cùng ý). Hai vòng khác nhau thêm hai cột cùng nghĩa. Ở đây đọc
KS-4 trước rồi mới tới PQ-9, và ĐẾM riêng số hồ sơ mà hai cột không khớp — không gộp im lặng, vì
lệch là dấu hiệu một trong hai vòng đang ghi vào cột không ai đọc.

════════════════════════════════════════════════════════════════════════════════════════════════
SEC-02 · HÀNG RÀO LỌC NGAY TRONG CÂU TRUY VẤN

`bo_phan_duoc_xem=None` nghĩa là xem hết (Chủ tịch, TGĐ, BKS). Vai khác truyền vào tập bộ phận
của mình. Lọc đặt TRONG câu truy vấn, không lọc sau khi đã cộng — cộng xong mới cắt là đã đọc số
của phòng khác một lần rồi.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Alert, User
from app.models.hr import DEPARTMENTS

# ────────────────────────────── DANH SÁCH ĐEN, KÈM LÝ DO ──────────────────────────────
# Mỗi khoá là một mã loại cảnh báo KHÔNG được tính là "hồ sơ quá hạn của một bộ phận".
# Lý do là bắt buộc và sẽ hiện lên màn hình, để người đọc kiểm được quyết định này.
KHONG_TINH: dict[str, str] = {
    "dt_thieu_nguon":
        "là một dòng dòng tiền chưa có nguồn số, không phải một hồ sơ quá hạn. Đã có chỗ riêng ở "
        "khối 06 Dòng tiền, cột Nguồn số, kèm bộ phận phải nạp — đưa sang đây là đếm hai lần.",
    "r9_chay_duoi_hoa_von":
        "là quyết định của Ban lãnh đạo, không phải việc một phòng xử lý xong rồi đóng lại "
        "(chu_canh_bao.CO_Y_KHONG_CHU).",
    "r9_gd_cho_khop":
        "gửi cả tuyến kiểm soát, cần nhiều mắt nhìn; gán cho một phòng là tạo ra một phòng chịu "
        "trách nhiệm giả (chu_canh_bao.CO_Y_KHONG_CHU).",
}

# Lý do sổ rỗng — đi kèm số rỗng, vì một ô gạch ngang không lời là một ô nằm đó mãi.
LY_DO_RONG = ("Không có cảnh báo nào đang mở thuộc diện hồ sơ quá hạn. Đây là số thật, "
              "không phải thiếu nguồn.")
LY_DO_CHUA_CO_CHU = ("Cảnh báo chưa được giao cho ai nên chưa suy ra được bộ phận. Chạy lượt giao "
                     "chủ (PQ-9) ở trang Cảnh báo, hoặc khai cách suy chủ cho loại còn thiếu.")
# Phạm vi rỗng KHÁC sổ rỗng, và trộn hai cái là nói dối người đọc. Tài khoản chưa khai bộ phận
# nhìn thấy bảng trống — nếu ô ấy ghi "đây là số thật" thì họ kết luận công ty không tồn đọng gì,
# trong khi sự thật là họ không được phép thấy. Câu chữ phải nói đúng cái đang xảy ra.
LY_DO_NGOAI_PHAM_VI = ("Tài khoản này chưa khai bộ phận nên chưa có phạm vi để xem. Đây KHÔNG phải "
                       "là 'không có hồ sơ quá hạn' — nhờ HCNS khai bộ phận cho tài khoản.")

# Nhãn cho dòng gom các hồ sơ chưa suy ra được bộ phận. KHÔNG phải tên một phòng có thật, và
# không được trộn vào phòng nào.
CHUA_RO = "(chưa rõ bộ phận)"


def ten_bo_phan(ma: str) -> str:
    """Mã chưa khai thì trả NGUYÊN MÃ, không đặt tên bừa.

    Một cái tên tiếng Việt trông như đã có người xét, nên sẽ không ai đi xét nữa. Để nguyên mã thì
    xấu, nhưng xấu ở đúng chỗ cần sửa.
    """
    return DEPARTMENTS.get(ma, ma)


def _tuoi(mo_luc: datetime, hom_nay: date) -> int:
    """Số ngày hồ sơ đã nằm đó. Âm là không thể xảy ra ở dữ liệu đúng, nhưng cắt về 0 cho chắc:
    một con số âm trên màn hình lãnh đạo còn khó giải thích hơn một con số 0."""
    return max(0, (hom_nay - mo_luc.date()).days)


def _chu(a: Alert) -> int | None:
    """KS-4 trước, PQ-9 sau. Xem chú thích đầu tệp về chỗ nợ hai cột."""
    return a.nguoi_nhan_id if a.nguoi_nhan_id is not None else a.nguoi_phu_trach


def _loc(db: Session, bo_phan_duoc_xem: set[str] | None):
    """Câu truy vấn gốc. HÀNG RÀO SEC-02 NẰM Ở ĐÂY, trong câu truy vấn — không lọc sau khi cộng.

    Nối trái sang `users` vì cảnh báo CHƯA CÓ CHỦ vẫn phải lấy về: chúng là dòng "chưa rõ bộ phận"
    đếm được, không phải dòng được bỏ đi. Nối trong thì chúng biến mất và tổng bị hụt mà không ai
    thấy.
    """
    # Nối theo ĐÚNG cột mà `_chu()` đọc: KS-4 trước, PQ-9 sau. Nối chỉ vào `nguoi_nhan_id` thì mọi
    # cảnh báo được PQ-9 giao (và chỉ PQ-9) sẽ rơi vào "chưa rõ bộ phận" dù đã có chủ hẳn hoi —
    # một dòng đếm được nhưng đếm sai chỗ, loại lỗi im lặng nhất của khối này.
    q = (select(Alert, User.department, User.full_name)
         .select_from(Alert)
         .outerjoin(User, User.id == func.coalesce(Alert.nguoi_nhan_id, Alert.nguoi_phu_trach))
         .where(Alert.resolved == False))                       # noqa: E712
    if KHONG_TINH:
        q = q.where(Alert.kind.notin_(tuple(KHONG_TINH)))
    if bo_phan_duoc_xem is not None:
        # Vai bị giới hạn chỉ thấy phòng mình, và KHÔNG thấy dòng "chưa rõ bộ phận" — dòng ấy là
        # việc của cấp điều phối, không phải của một phòng.
        q = q.where(User.department.in_(tuple(bo_phan_duoc_xem)))
    return q


def theo_bo_phan(db: Session, *, bo_phan_duoc_xem: set[str] | None = None,
                 hom_nay: date | None = None) -> dict:
    """Bảng 04c. Trả về `dong` (mỗi bộ phận một dòng) + phần đã loại + phần chưa rõ bộ phận.

    Sổ rỗng trả `dong=[]` kèm `vi_sao`, KHÔNG trả một hàng số 0: năm số 0 đọc y hệt "không phòng
    nào tồn đọng", trong khi sự thật có thể là "chưa ai giao cảnh báo cho ai".
    """
    hom_nay = hom_nay or date.today()

    # Một hồ sơ = một `ref`. Giữ CẢNH BÁO MỞ SỚM NHẤT của mỗi ref: nó quyết định bộ phận, tuổi hồ
    # sơ, và người chịu trách nhiệm. Duyệt theo thứ tự thời gian rồi chỉ nhận cái đầu tiên.
    dau_tien: dict[str, dict] = {}
    lech_hai_cot = 0
    for a, phong, ten_nguoi in db.execute(_loc(db, bo_phan_duoc_xem)
                                          .order_by(Alert.created_at, Alert.id)).all():
        if a.nguoi_nhan_id is not None and a.nguoi_phu_trach is not None \
                and a.nguoi_nhan_id != a.nguoi_phu_trach:
            lech_hai_cot += 1
        khoa = a.ref or f"#alert:{a.id}"     # ref rỗng: coi mỗi cảnh báo là một hồ sơ riêng
        if khoa in dau_tien:
            # Hồ sơ đã tính rồi. Chỉ kéo hạn khắc phục sớm nhất về, vì hạn gần nhất mới là hạn.
            cu = dau_tien[khoa]
            if a.han_xu_ly and (cu["han"] is None or a.han_xu_ly < cu["han"]):
                cu["han"] = a.han_xu_ly
            continue
        dau_tien[khoa] = {
            "ref": khoa,
            "phong": phong or "",
            "nguoi": ten_nguoi or "",
            "mo_luc": a.created_at,
            "han": a.han_xu_ly,
            "muc": a.level or "",
        }

    if not dau_tien:
        # Bảng trống vì KHÔNG CÓ GÌ, hay vì NGƯỜI NÀY KHÔNG ĐƯỢC THẤY GÌ? Hai câu trả lời khác hẳn
        # nhau và chỉ chỗ này phân biệt được.
        ngoai = bo_phan_duoc_xem is not None and not bo_phan_duoc_xem
        return {"dong": [], "chua_ro_bo_phan": None, "da_loai": _da_loai(db, bo_phan_duoc_xem),
                "lech_hai_cot_chu": 0,
                "vi_sao": LY_DO_NGOAI_PHAM_VI if ngoai else LY_DO_RONG}

    # Gom theo phòng. Phòng rỗng → dòng "chưa rõ bộ phận", đếm riêng, không nhét vào ai.
    gom: dict[str, list[dict]] = {}
    for h in dau_tien.values():
        gom.setdefault(h["phong"] or CHUA_RO, []).append(h)

    dong = []
    for ma, ds in gom.items():
        if ma == CHUA_RO:
            continue
        lau = min(ds, key=lambda h: h["mo_luc"])
        hans = [h["han"] for h in ds if h["han"] is not None]
        # Người chịu trách nhiệm: người đang giữ NHIỀU hồ sơ nhất của phòng. Bản vẽ để một ô, mà
        # một phòng có nhiều người — nên ghi rõ còn bao nhiêu người nữa, chứ không giấu đi.
        dem_nguoi: dict[str, int] = {}
        for h in ds:
            if h["nguoi"]:
                dem_nguoi[h["nguoi"]] = dem_nguoi.get(h["nguoi"], 0) + 1
        nguoi = ""
        if dem_nguoi:
            top = max(dem_nguoi.items(), key=lambda kv: (kv[1], kv[0]))[0]
            nguoi = top if len(dem_nguoi) == 1 else f"{top} +{len(dem_nguoi) - 1} người"
        dong.append({
            "bo_phan": ten_bo_phan(ma),
            "ma_bo_phan": ma,
            "ho_so_qua_han": len(ds),
            "ho_so_lau_nhat": f"{_tuoi(lau['mo_luc'], hom_nay)} ngày · {lau['ref']}",
            "nguoi_chiu_trach_nhiem": nguoi or None,
            # KHÔNG bịa hạn. Chưa ai đặt hạn thì để rỗng — màn hình tự ghi "chưa đặt".
            "han_khac_phuc": min(hans).strftime("%d/%m/%Y") if hans else None,
        })
    dong.sort(key=lambda r: (-r["ho_so_qua_han"], r["bo_phan"]))

    chua_ro = gom.get(CHUA_RO) or []
    return {
        "dong": dong,
        "chua_ro_bo_phan": ({"so": len(chua_ro), "vi_sao": LY_DO_CHUA_CO_CHU} if chua_ro else None),
        "da_loai": _da_loai(db, bo_phan_duoc_xem),
        "lech_hai_cot_chu": lech_hai_cot,
        "vi_sao": "",
    }


def _da_loai(db: Session, bo_phan_duoc_xem: set[str] | None) -> list[dict]:
    """Đếm phần đã loại, kèm lý do. Loại mà không nói là giấu — người đọc thấy tổng 1.476 ở khối
    bên cạnh và 12 ở đây thì phải hiểu được vì sao lệch, ngay trên màn hình."""
    if bo_phan_duoc_xem is not None:
        return []          # vai bị giới hạn không cần biết phần ngoài phạm vi mình
    ra = []
    for ma, ly_do in KHONG_TINH.items():
        so = len(set(
            r[0] for r in db.execute(
                select(Alert.ref).where(Alert.resolved == False,  # noqa: E712
                                        Alert.kind == ma)).all()))
        if so:
            ra.append({"loai": ma, "so_ho_so": so, "ly_do": ly_do})
    return sorted(ra, key=lambda r: -r["so_ho_so"])
