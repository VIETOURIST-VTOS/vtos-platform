"""Tách bạch trách nhiệm theo NGƯỜI, không theo vai — Đợt E2a, 09/10/2026.

VÌ SAO TỆP NÀY TỒN TẠI

Kho mã đã có một lớp tách bạch trách nhiệm, và nó đúng về ý: `ks_toan_quyen.py` ghi rõ *"người
KÝ lệnh chi và người bấm ĐÃ CHI phải là hai người"*. Nhưng thứ mã thật sự kiểm là hai VAI
(`u.role != "ketoan"`), không phải hai NGƯỜI. Hai thứ ấy chỉ trùng nhau khi mỗi người đúng một
tài khoản.

ĐO ĐƯỢC, 19/9/2026, trên máy thật (xem `services/gop_tai_khoan.py`): 220 tài khoản, **6 người có
từ hai tài khoản trở lên**, tổng 24 dòng, bốn cặp đang mở cả hai. Nghĩa là lớp chống gian lận cổ
điển nhất công ty đang có đã có sẵn một lối đi vòng — không phải giả thiết, là số đếm được.

Tách `ketoan` thành ba vai (Đợt E2b) KHÔNG bịt lối ấy: nó vẫn so vai với vai. Phải so người với
người, và muốn so người thì phải có hai thứ dưới đây.

HAI BẢNG, VÀ VÌ SAO LÀ HAI

  `buoc_da_lam` — DẤU CHÂN. Mỗi bước nghiệp vụ hoàn thành để lại một dòng: chứng từ nào, bước gì,
  người nào. GHI THÊM, KHÔNG SỬA, KHÔNG XOÁ: làm lại một bước là một dòng nữa, nên nhìn vào là
  thấy nó đã bị làm lại và ai làm. Ghi đè thì mất đúng cái cần nhìn.

  `cap_tach_nhiem` — CẶP XUNG ĐỘT. Hai bước nào không được chung một người. **BẢNG NÀY BẮT ĐẦU
  RỖNG VÀ PHẢI RỖNG.** Một cặp là một quy chế kiểm soát nội bộ; máy nạp sẵn một dòng là máy tự
  đặt quy chế hộ người. Đây đúng nguyên tắc đã dùng cho `muc_do_chan` ở Đợt E1, và đúng ranh giới
  Chủ tịch đặt 09/9/2026: robot viết bộ kiểm, không tự khai luật.

AI LÀ MỘT NGƯỜI — và chỗ dễ sai nhất của cả tệp này

Mã nhận dạng người là MÃ NHÂN VIÊN (`users.staff_code`), vì đó là thứ hai tài khoản của cùng một
người cùng mang. Tài khoản KHÔNG có mã nhân viên thì mỗi tài khoản là một người riêng
(`u:<id>`) — **không gộp chúng lại**. Gộp mọi tài khoản rỗng mã thành "một người" là biến tất cả
tài khoản chưa khai mã thành cùng một người và chặn oan hàng loạt ngay ngày đầu; đúng nguyên tắc
K2: RỖNG khác với BẰNG NHAU. Hệ quả phải nói thẳng: người có hai tài khoản mà cả hai đều rỗng mã
thì bộ kiểm này KHÔNG bắt được — bịt chỗ ấy là việc của mã nhân viên, không phải việc của đây.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# ══════════════════════════════════════════════════════════════════════════════════════════
# MÃ BƯỚC — tên của từng bước nghiệp vụ để lại dấu chân.
#
# Viết ra một chỗ thay vì gõ chuỗi tại nơi gọi: gõ tay thì một ngày nào đó có người viết
# "da_chi " thừa dấu cách, cặp xung đột không khớp nữa, và cửa im lặng mở ra.
# ══════════════════════════════════════════════════════════════════════════════════════════
BUOC = {
    # Đề nghị chi (services/ops.py::step) — đúng năm bước của luồng đang chạy
    "lap_de_nghi_chi": "Lập đề nghị chi",
    "xac_nhan_bo_phan": "Người phụ trách bộ phận xác nhận",
    "ke_toan_kiem": "Kế toán kiểm chứng từ",
    "duyet_lenh_chi": "Ký duyệt lệnh chi",
    "da_chi": "Bấm ĐÃ CHI — tiền ra khỏi tài khoản",
    # Sổ kế toán (api/v1/accounting.py)
    "lap_but_toan": "Lập bút toán",
    "ghi_so": "Ghi sổ bút toán",
    "khoa_so_ky": "Khóa sổ kỳ kế toán",
    # Báo cáo sau tour (api/v1/hr.py) — Đợt HD-8, 13/10/2026. Phạm vi khoá theo PHÂN CÔNG
    # (`pc:<id>`), vì cả hai bước đều xảy ra trên đúng một phân công.
    "nop_bao_cao_tour": "Nộp báo cáo sau tour",
    "kiem_bao_cao_tour": "Xác nhận báo cáo sau tour",
}

# ══════════════════════════════════════════════════════════════════════════════════════════
# HAI CẶP CHỦ TỊCH KÝ 09/10/2026 — và vì sao chúng nằm trong mã nguồn chứ không nằm trong
# một lần gõ tay vào cơ sở dữ liệu.
#
# Nguyên tắc của bảng này là "máy không tự đặt quy chế". Nguyên tắc ấy KHÔNG nói là bảng phải
# rỗng mãi — nó nói MỌI DÒNG PHẢI CÓ NGƯỜI KÝ. Hai dòng dưới đây có tên người ký và ngày ký
# ghi thẳng trong mã, nên ai đọc lại cũng tra được quyền ấy từ đâu mà có; một dòng gõ tay vào
# cơ sở dữ liệu thì không để lại dấu vết nào như thế. Phép thử canh đúng bất biến ấy: không
# dòng nào trong bảng được thiếu `nguoi_ky` và `can_cu`.
#
# MỨC ĐỘ ĐỂ TRỐNG, CÓ CHỦ Ý. Chủ tịch ký SỰ TỒN TẠI của hai cặp, chưa ký MỨC. Trống = chưa ai
# đặt → chạy ở "cảnh báo nhưng cho qua" và BỊ ĐẾM LÊN. Tự đặt "chặn" hộ là đúng cái sai đã
# phải sửa ở bản v1.0 ngày 09/10 (bốn bước bốn người đưa thẳng vào hàng rào CI, không chữ ký).
# Và nó sẽ mâu thuẫn với tham số `chu_tich_mo_het_cua` đang BẬT cho giai đoạn chạy thử.
# ══════════════════════════════════════════════════════════════════════════════════════════
CAP_DA_KY = (
    {
        "ma_cap": "duyet-chi-vs-da-chi",
        "buoc_a": "duyet_lenh_chi",
        "buoc_b": "da_chi",
        "ten": "Người ký lệnh chi ≠ người bấm ĐÃ CHI",
        "mo_ta": "Lớp chống gian lận cổ điển nhất công ty đang có. Trước bản này hệ thống so "
                 "hai VAI; đo được 19/9/2026 có 6 người giữ từ hai tài khoản trở lên, nên so "
                 "vai là chưa đủ.",
        "nguoi_ky": "chutich",
        "can_cu": "Chủ tịch ký 09/10/2026 — cặp xung đột đầu tiên của sổ tách bạch trách nhiệm.",
    },
    {
        "ma_cap": "ghi-so-vs-khoa-so",
        "buoc_a": "ghi_so",
        "buoc_b": "khoa_so_ky",
        "ten": "Người ghi sổ ≠ người khóa sổ kỳ",
        "mo_ta": "Khóa sổ là bước làm cho con số không sửa được nữa. Người vừa ghi bút toán "
                 "vào kỳ mà tự khóa kỳ ấy là tự niêm phong việc của chính mình.",
        "nguoi_ky": "chutich",
        "can_cu": "Chủ tịch ký 09/10/2026 — cặp xung đột thứ hai.",
    },
    {
        "ma_cap": "nop-bao-cao-tour-vs-kiem",
        "buoc_a": "nop_bao_cao_tour",
        "buoc_b": "kiem_bao_cao_tour",
        "ten": "Người nộp báo cáo sau tour ≠ người xác nhận",
        "mo_ta": "Trưởng phòng Hướng dẫn vừa quản lý vừa đi dẫn tour — có thật ở Vietourist. Tự "
                 "nộp rồi tự xác nhận thì cái kiểm ấy không kiểm gì cả. Cửa `bc_kiem` đã có một "
                 "phép chặn theo HỒ SƠ từ Đợt HD-7, nhưng phép ấy chỉ thấy MỘT tài khoản; cặp này "
                 "thấy cả hai tài khoản của cùng một người, vì nó so theo mã nhân viên.",
        "nguoi_ky": "chutich",
        "can_cu": "Chủ tịch chốt 13/10/2026 — cặp xung đột thứ ba, phương án (a). MỨC ĐỂ TRỐNG "
                  "như hai cặp ký 09/10: chạy ở 'cảnh báo nhưng cho qua' và BỊ ĐẾM LÊN, tới khi "
                  "Chủ tịch đặt mức.",
    },
)

# ══════════════════════════════════════════════════════════════════════════════════════════
# VAI TIỀN — những vai mà bước của họ phải so được là ai, nên tài khoản BẮT BUỘC có mã nhân
# viên (Chủ tịch quyết 09/10/2026).
#
# Ba mã `ketoan_truong` / `ketoan_tt` / `thu_quy` chưa tồn tại trong ROLES hôm nay; để sẵn ở
# đây là cố ý, để ngày Đợt E2b mở ba vai ấy thì không ai phải nhớ quay lại sửa tệp này.
# ══════════════════════════════════════════════════════════════════════════════════════════
VAI_TIEN = ("ketoan", "ketoan_truong", "ketoan_tt", "thu_quy", "chutich", "tgd")

# ══════════════════════════════════════════════════════════════════════════════════════════
# VAI NGOÀI TIỀN CŨNG PHẢI CÓ MÃ — Đợt HD-9, Chủ tịch chốt 13/10/2026 (câu D1 = phương án A).
#
# `VAI_TIEN` là danh sách vai BỊ CHẶN khi thiếu mã. Đợt E2a cố ý KHÔNG nới nó, và lý do còn
# nguyên giá trị: nới ra là chặn `hcns` ở những bước họ không hề làm — xem
# `vai_can_ma_de_phep_do_thay`.
#
# `tp_hd` KHÁC `hcns` ở đúng một điểm, và điểm ấy quyết định: Trưởng phòng Hướng dẫn LÀM CẢ HAI
# BƯỚC của một cặp xung đột có thật — vừa dẫn tour nên nộp báo cáo, vừa là người xác nhận báo
# cáo (cặp `nop-bao-cao-tour-vs-kiem`, Chủ tịch ký 13/10/2026). Thiếu mã thì hai tài khoản của
# cùng một người thành hai người, và cặp ấy không bắt được gì. Chặn đúng người làm cả hai bước
# không phải là chặn oan — đó chính là việc của luật này.
#
# KHÔNG KHÓA AI HÔM NAY. Danh sách này đi qua cùng một công tắc theo ngày
# (`KHOA_BAT_BUOC_MA_NV`) như vai tiền: tham số rỗng thì chỉ ĐẾM và liệt kê cho HCNS đi điền,
# chưa chặn. Chủ tịch đặt ngày khi dữ liệu đã đủ.
VAI_BAO_CAO_TOUR = ("tp_hd",)

# Danh sách CHẶN đầy đủ. Giữ `VAI_TIEN` nguyên nghĩa thay vì nhét `tp_hd` vào đó: tên biến ấy
# được nhắc trong năm tệp khác, và một cái tên nói sai là một cái bẫy cho người đọc sau.
VAI_PHAI_CO_MA_NV = VAI_TIEN + VAI_BAO_CAO_TOUR

# Tên tham số bật ngày hiệu lực của luật "vai tiền phải có mã nhân viên".
# RỖNG = CHƯA TỚI NGÀY: đếm và liệt kê, chưa chặn ai. Lý do phải có tham số chứ không bật
# thẳng: đo trên bộ dữ liệu mẫu, KHÔNG tài khoản nào có mã nhân viên — bật thẳng hôm nay là
# khóa cả Chủ tịch ra ngoài đúng cửa ĐÃ CHI. HCNS điền mã xong thì Chủ tịch đặt ngày.
KHOA_BAT_BUOC_MA_NV = "tach_nhiem_bat_buoc_ma_nv_tu"


def ma_nguoi(u) -> str:
    """Khoá định danh NGƯỜI của một tài khoản. Xem đoạn cuối docstring đầu tệp."""
    ma = (getattr(u, "staff_code", "") or "").strip()
    return ma if ma else f"u:{getattr(u, 'id', 0)}"


class BuocDaLam(Base):
    """Dấu chân: chứng từ này, bước này, người này, lúc này. Ghi thêm, không sửa."""
    __tablename__ = "buoc_da_lam"
    id: Mapped[int] = mapped_column(primary_key=True)
    # PHẠM VI — thứ mà CẢ HAI bước của một cặp cùng nói về. Một chuỗi chứ không phải một
    # (bảng, id) số, vì hai bước xung đột KHÔNG phải lúc nào cũng nằm trên cùng một bản ghi:
    # "ghi sổ" xảy ra trên một bút toán, "khóa sổ" xảy ra trên một KỲ — thứ chung của chúng là
    # cái kỳ ấy. Khóa theo id bút toán thì cặp ấy không bao giờ khớp, tức là một hàng rào trông
    # như đang chạy mà thật ra tắt. Quy ước: `dc:<id đề nghị chi>`, `ky:<kỳ kế toán>`.
    pham_vi: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    ma_buoc: Mapped[str] = mapped_column(String(40), nullable=False)
    # Lưu CẢ BA: mã người để so sánh, tên đăng nhập và vai để người đọc nhật ký hiểu ngay mà không
    # phải tra bảng tài khoản — tài khoản có thể bị khoá hoặc đổi vai sau, dòng này thì không đổi.
    ma_nguoi: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), default="")
    vai: Mapped[str] = mapped_column(String(30), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


Index("ix_buoc_da_lam_pham_vi_buoc", BuocDaLam.pham_vi, BuocDaLam.ma_buoc)


class CapTachNhiem(Base):
    """Hai bước không được chung một người. Mỗi dòng là một quy chế, phải có người ký."""
    __tablename__ = "cap_tach_nhiem"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma_cap: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    buoc_a: Mapped[str] = mapped_column(String(40), nullable=False)
    buoc_b: Mapped[str] = mapped_column(String(40), nullable=False)
    ten: Mapped[str] = mapped_column(String(160), default="")
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    # RỖNG = CHƯA AI ĐẶT MỨC, không phải "không chặn". Đọc qua ks_tach_nhiem.muc_do().
    muc_do: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nguoi_ky: Mapped[str] = mapped_column(String(50), default="")
    can_cu: Mapped[str] = mapped_column(Text, default="")
    ngay_hieu_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dang_ap_dung: Mapped[bool] = mapped_column(Boolean, default=True)
    boi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
