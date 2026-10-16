# -*- coding: utf-8 -*-
"""ĐỒNG Ý CÔNG KHAI NHẬN XÉT — Đợt HD-DG3. Chủ tịch chốt sáu nút ngày 16/10/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
LUẬT GỐC: ĐỦ CẢ HAI MỚI HIỆN
═══════════════════════════════════════════════════════════════════════════════════════════════
Một nhận xét lên hồ sơ hướng dẫn viên công khai khi khách ĐÃ ĐỒNG Ý **và** người có thẩm quyền
ĐÃ DUYỆT. Thiếu một trong hai thì `cong_khai_duoc()` trả False, và cửa công khai không có đường
nào khác để hỏi — kể cả Chủ tịch cũng không mở được một nhận xét chưa có đồng ý.

Đồng ý của khách KHÔNG phải lệnh đăng. Nó là một trong hai điều kiện.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO KHÔNG DÙNG LẠI Ô `dong_y_dung_danh_gia` ĐÃ CÓ — ĐỌC KỸ CHỖ NÀY
═══════════════════════════════════════════════════════════════════════════════════════════════
`care_tickets.dong_y_dung_danh_gia` có từ Đợt 4 và hỏi: *"anh/chị có đồng ý cho công ty DÙNG lời
nhận xét này không"*. Câu Chủ tịch chốt 16/10 hỏi: *"anh/chị có đồng ý ĐĂNG CÔNG KHAI nhận xét
này TRÊN HỒ SƠ HƯỚNG DẪN VIÊN TẠI VTOS, KHÔNG KÈM TÊN và thông tin liên hệ của anh/chị không"*.

Hai câu khác nhau thật, không phải hai cách nói một điều: câu mới nói RÕ ĐĂNG Ở ĐÂU và nói rõ
cái gì KHÔNG bị đăng kèm. Lấy chữ "co" của câu cũ dùng cho việc mới là đăng lời của một người ở
nơi họ chưa từng được hỏi, rồi gọi đó là đã xin phép. Nên bảng này ghi RIÊNG, và ghi luôn NGUYÊN
VĂN câu đã hỏi (`cau_hoi`) — sáu tháng sau còn chứng minh được khách đã đồng ý với điều gì, chứ
không phải với điều hôm nay ta nhớ là đã hỏi.

HỆ QUẢ, nói trước chứ không giấu: mọi nhận xét thu trước đợt này KHÔNG có đồng ý mới, nên ngày
đầu hàng đợi duyệt RỖNG. Rỗng ở đây là đúng, không phải hỏng.

═══════════════════════════════════════════════════════════════════════════════════════════════
NHÃN NGƯỜI VIẾT, VÀ MỘT VIỆC CÒN NỢ GHI THẲNG RA ĐÂY
═══════════════════════════════════════════════════════════════════════════════════════════════
Chủ tịch chọn nhãn có tên tuyến: «Khách đi tour Đà Nẵng 9/2026». Hôm nay VTOS CHƯA CÓ trường
tuyến — `tours.name` là chữ tự do, nên "Đà Nẵng 3N2Đ", "ĐN-Hội An" và "Da Nang VIP" là ba chuỗi
khác nhau cho cùng một tuyến. Gom theo chuỗi ấy thì ngưỡng dưới đây đếm một tập khác với tập nó
mang tên: hai cách viết mỗi cái tám khách, cả hai cùng tụt xuống dưới ngưỡng, và máy tưởng mình
đang che trong khi thật ra nó che nhầm chỗ.

Nên `nhan_nguoi_viet()` hôm nay in NHÃN CHỈ CÓ THÁNG. Trường tuyến là việc của Đợt HD-13 (địa
bàn); ngày đợt ấy xong thì sửa ĐÚNG hàm này, một chỗ, và bật `CO_TRUONG_TUYEN` lên.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM
═══════════════════════════════════════════════════════════════════════════════════════════════
1. KHÔNG tự tạo một bản ghi đồng ý nào, cho bất kỳ khách nào, trong bất kỳ hoàn cảnh nào. Hàm
   `ghi_tra_loi` chỉ chạy từ cửa khảo sát, với mã của chính khách. Đồng ý là việc của khách;
   hệ thống chỉ ghi lại việc ấy đã xảy ra, do ai hỏi, lúc nào, với phạm vi nào.
2. KHÔNG in tên hay số điện thoại người nhận xét ở bất cứ đâu trong nhóm hàm công khai. Hai chữ
   "không kèm tên" trong câu đã hỏi là một hàng rào trong mã, không phải một lời hứa trong tài
   liệu — `test_dg3` canh điều đó.
3. KHÔNG xoá khi khách rút. Rút là NGỪNG CÔNG KHAI. Lời nhận xét vẫn ở sổ nội bộ và vẫn tính vào
   điểm hướng dẫn viên, theo thời hạn lưu nhóm «11 · Phản hồi khách hàng». Cùng một lẽ với luật
   giữ chỗ Chủ tịch chốt 11/9/2026: hết hạn không phải là huỷ.
"""
from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai

# ── CÂU HỎI, NGUYÊN VĂN CHỦ TỊCH ĐƯA 16/10/2026 ───────────────────────────────────────────────
# Không sửa một chữ. Mỗi bản ghi đồng ý chép lại chính chuỗi này vào cột `cau_hoi`, nên ngày câu
# hỏi đổi thì các bản ghi cũ vẫn giữ câu đã hỏi lúc ấy — không bị viết lại theo câu mới.
CAU_HOI = ("Anh/chị có đồng ý đăng công khai nhận xét này trên hồ sơ hướng dẫn viên tại VTOS, "
           "không kèm tên và thông tin liên hệ của anh/chị không?")

PHAM_VI = "ho_so_hdv_cong_khai"     # đồng ý cho ĐÚNG chỗ này, không suy rộng ra chỗ khác

# Hạn của đường rút tự phục vụ. Dài hơn hẳn mã khảo sát: khách rút lúc nào cũng được trong suốt
# thời gian lời nhận xét còn hiện, chứ không chỉ trong tuần họ vừa đi tour.
RUT_SONG_NGAY = 730

# ── NGƯỠNG CHE DANH TÍNH ──────────────────────────────────────────────────────────────────────
# Chỉ in tên tuyến khi tháng ấy tuyến ấy đủ đông để một cái tên không chỉ ra được ai. Hôm nay
# nhãn chỉ có tháng vì chưa có trường tuyến (xem đầu tệp). Bật `CO_TRUONG_TUYEN` mà chưa có
# trường tuyến là bật một phép đếm trên một tập sai.
NGUONG_KHACH = 30
CO_TRUONG_TUYEN = False             # HD-13 bật lên


def _thang(d: date) -> str:
    return f"{d.month}/{d.year}"


def _moc_ngay(db: Session, dg: DanhGiaSauTour) -> date:
    from app.models.core import Tour
    t = db.get(Tour, dg.tour_id)
    if t is not None and t.start_date:
        return t.start_date
    return dg.tao_luc.date() if dg.tao_luc else date.today()


def nhan_nguoi_viet(db: Session, dg: DanhGiaSauTour) -> str:
    """Nhãn in thay cho tên người viết trên hồ sơ công khai.

    Trả về «Khách đi tour tháng 9/2026», hoặc «Khách đi tour Đà Nẵng 9/2026» khi đã có trường
    tuyến VÀ tháng ấy tuyến ấy đạt `NGUONG_KHACH`. Dưới ngưỡng thì tự lùi về nhãn chỉ có tháng —
    lùi là mặc định, không phải ngoại lệ.
    """
    moc = _moc_ngay(db, dg)
    if not CO_TRUONG_TUYEN:
        return f"Khách đi tour tháng {_thang(moc)}"
    tuyen, so_khach = _tuyen_va_so_khach(db, dg)          # HD-13 dựng
    if not tuyen or so_khach < NGUONG_KHACH:
        return f"Khách đi tour tháng {_thang(moc)}"
    return f"Khách đi tour {tuyen} {_thang(moc)}"


def ly_do_lui_nhan(db: Session, dg: DanhGiaSauTour) -> str:
    """Vì sao nhãn không có tên tuyến — in THẲNG trên màn hình duyệt.

    Máy che thì người duyệt phải thấy nó đang che chỗ nào. Che lén là cách chắc nhất để một ngày
    ai đó gỡ hàng rào đi mà không ai nhận ra.
    """
    if not CO_TRUONG_TUYEN:
        return ("Chưa in tên tuyến: VTOS chưa có trường tuyến (Đợt HD-13 dựng). Gom theo tên "
                "chuyến là chữ tự do nên ngưỡng 30 khách sẽ đếm nhầm tập.")
    return ""


# ── GHI ĐỒNG Ý ────────────────────────────────────────────────────────────────────────────────
def ghi_tra_loi(db: Session, dg: DanhGiaSauTour, tra_loi: str, nguon: str = "khao_sat") -> DongYCongKhai:
    """Ghi câu trả lời của khách cho MỘT nhận xét. Gọi từ cửa khảo sát, không gọi từ đâu khác.

    `tra_loi` chỉ nhận "co" hoặc "khong" — KHÔNG có giá trị mặc định và không có đường nào bỏ
    trống. Im lặng không phải là đồng ý.
    """
    if tra_loi not in ("co", "khong"):
        raise ValueError("tra_loi phải là 'co' hoặc 'khong' — không có mặc định")
    r = db.execute(select(DongYCongKhai)
                   .where(DongYCongKhai.danh_gia_id == dg.id)).scalars().first()
    if r is not None:
        return r                                  # một nhận xét một bản ghi; hỏi lại không ghi đè
    r = DongYCongKhai(
        danh_gia_id=dg.id, care_id=dg.care_id, tour_id=dg.tour_id,
        pham_vi=PHAM_VI, cau_hoi=CAU_HOI, tra_loi=tra_loi,
        hoi_luc=datetime.now(), nguon=nguon,
        ma_rut=secrets.token_urlsafe(24) if tra_loi == "co" else "",
        ma_rut_het_han=(datetime.now() + timedelta(days=RUT_SONG_NGAY)) if tra_loi == "co" else None,
    )
    db.add(r)
    db.flush()
    return r


# ── RÚT ĐỒNG Ý ────────────────────────────────────────────────────────────────────────────────
def rut(db: Session, ma: str, ly_do: str = "") -> dict:
    """Khách bấm đường dẫn rút. KHÔNG cần đăng nhập, và KHÔNG trả về một chữ nào về dữ liệu.

    Trả đúng một câu xác nhận. Một cửa không cần đăng nhập mà đọc được thì nó là cửa đọc, không
    phải cửa rút — nên hàm này không in nhận xét, không in tên hướng dẫn viên, không in gì hết.

    MÃ DÙNG MỘT LẦN, NHƯNG KHÔNG XOÁ MÃ — và chỗ này đã sửa một lần, ghi lại vì sao.

    Bản đầu xoá `ma_rut` ngay sau khi rút, nghĩ thế mới là "dùng một lần". Phép đo cho thấy nó
    làm nhánh ngay trên thành MÃ CHẾT: khách bấm lại đường dẫn cũ thì không tra ra dòng nào và
    nhận về câu "đường dẫn không đúng" — đúng cái câu chú thích này nói là không được trả.

    Một lần là nói về HIỆU LỰC, không phải về sự tồn tại của chuỗi: `rut_luc` đã có giá trị thì
    mọi lần bấm sau chỉ còn đọc ra một câu xác nhận, không đổi được gì nữa. Mã còn tra được mà
    trơ ra thì an toàn không kém, vì cửa này không trả về một chữ nào về dữ liệu — người lạ cầm
    được đường dẫn cũng chỉ thấy đúng câu "đã gỡ rồi".
    """
    if not ma:
        return {"xong": False, "loi": "Đường dẫn không đúng hoặc đã hết hiệu lực."}
    r = db.execute(select(DongYCongKhai).where(DongYCongKhai.ma_rut == ma)).scalars().first()
    if r is None:
        return {"xong": False, "loi": "Đường dẫn không đúng hoặc đã hết hiệu lực."}
    if r.ma_rut_het_han and r.ma_rut_het_han < datetime.now():
        return {"xong": False, "loi": "Đường dẫn đã hết hiệu lực."}
    if r.rut_luc is not None:
        # Đã rút rồi thì nói đã rút rồi — KHÔNG báo lỗi. Khách bấm hai lần không phải là khách sai,
        # và một thông báo lỗi ở đây làm người ta tưởng việc rút chưa ăn.
        return {"xong": True, "loi": "", "da_rut_tu_truoc": True,
                "loi_nhan": "Nhận xét của anh/chị đã được gỡ khỏi hồ sơ công khai."}
    r.rut_luc = datetime.now()
    r.rut_ly_do = (ly_do or "").strip()[:500]
    db.flush()
    return {"xong": True, "loi": "", "da_rut_tu_truoc": False,
            "loi_nhan": "Đã gỡ nhận xét của anh/chị khỏi hồ sơ công khai. Cảm ơn anh/chị đã báo."}


# ── DUYỆT CÔNG BỐ ─────────────────────────────────────────────────────────────────────────────
VAI_DUYET = ("chutich", "tgd")       # hai vai; anh Thắng cấp đích danh qua user_grants
# Quyền cấp đích danh TỐI ĐA 90 NGÀY — `core.GRANT_MAX_DAYS`, và cửa cấp ở routes.py từ chối dài
# hơn thế. Chủ tịch chọn 12 tháng ngày 16/10; đo ra trần 90 ngày nên chốt lại: cấp 90 ngày rồi
# gia hạn, giữ nguyên luật của kho. Chỉ Chủ tịch hoặc TGĐ cấp được (require_roles ở cửa ấy), nên
# mỗi lần gia hạn đều có chữ ký của một trong hai người.
QUYEN_DUYET = "duyet_cong_bo_nhan_xet"


# BASE_VIEW NHƯNG KHÔNG DUYỆT — kể tên ra đây chứ không để `co_quyen` quyết hộ.
#
# `access.co_quyen` trả True cho MỌI vai trong BASE_VIEW (Chủ tịch, TGĐ, Ban Kiểm soát, robot Kiểm
# soát) trước khi nhìn tới quyền cấp lẻ. Với phần lớn năng lực thì đúng: Ban Kiểm soát phải xem
# được mọi thứ. Nhưng ĐĂNG một lời khách lên mạng không phải việc xem — nó là việc công bố, và
# cơ quan kiểm soát mà tự công bố nội dung thì không còn kiểm soát được việc công bố nữa. Robot
# thì càng không: một con robot bấm nút đăng là nội dung ra ngoài không ai ký.
KHONG_DUYET_DU_LA_BASE_VIEW = ("bks", "robot_ks")


def ai_duyet_duoc(db: Session, u) -> tuple[bool, str]:
    """(duyệt được không, bằng quyền nào). Quyền nào cũng phải nói ra được — xem cột duyet_bang_quyen."""
    vai = getattr(u, "role", "")
    if vai in VAI_DUYET:
        return True, "vai"
    if vai in KHONG_DUYET_DU_LA_BASE_VIEW:
        return False, ""
    from app.services import access as AC
    if AC.co_quyen(db, u, QUYEN_DUYET):
        return True, "cap_dich_danh"
    return False, ""


# KN_TRANG_THAI: moi · dang_xu_ly · cho_khach · da_dong · tai_mo. Chỉ "da_dong" là đóng.
KN_DA_DONG = ("da_dong",)


def vuong_chong_vai(db: Session, u, dg: DanhGiaSauTour) -> str:
    """Người này có đang giữ một khiếu nại chưa đóng về CHÍNH hướng dẫn viên bị chấm không?

    Chủ tịch chốt 16/10: quyền xem, xử lý khiếu nại, công bố và gỡ nội dung phải TÁCH RIÊNG. Anh
    Nguyễn Tất Thắng giữ việc xác minh khiếu nại về HDV và cũng được cấp quyền duyệt đăng. Hàng
    rào này hẹp đúng chỗ chồng nhau: anh ấy duyệt bình thường mọi nhận xét, TRỪ nhận xét về một
    HDV mà chính anh ấy đang giữ một khiếu nại chưa đóng. Khiếu nại đóng lại là nút tự mở.

    Không phải chuyện tin hay không tin. Cùng một người vừa kết luận một khiếu nại về HDV X vừa
    quyết lời khen về HDV X có lên hồ sơ hay không thì về sau không ai tách được hai quyết định
    ấy ra — kể cả chính người ấy.

    ĐI VÒNG QUA CHUYẾN, VÌ KHIẾU NẠI KHÔNG CÓ CỘT HDV — và đó là thiết kế cũ chứ không phải
    thiếu sót: chú thích ở `models/cskh.py` ghi rõ nhóm "hdv" BẮT BUỘC có booking, vì "không có
    chuyến thì không quy được trách nhiệm về hướng dẫn viên nào". Nên dây nối là
    khiếu nại → tour_id → `guide_assignments` → hướng dẫn viên.

    HỆ QUẢ PHẢI NÓI RA: một chuyến có hai hướng dẫn viên thì khiếu nại về chuyến ấy vướng CẢ HAI,
    kể cả người không bị than. Chặn rộng hơn mức cần. Chấp nhận, vì chặn rộng ở đây chỉ làm một
    nhận xét phải chuyển lên Chủ tịch, còn chặn hụt là đúng cái hàng rào này sinh ra để tránh.
    """
    if dg.doi_tuong != "hdv" or not dg.doi_tuong_id:
        return ""
    if getattr(u, "role", "") in VAI_DUYET:
        return ""                                  # Chủ tịch và TGĐ không giữ việc xác minh
    from app.models.cskh import Complaint
    from app.models.hr import GuideAssignment
    tour_cua_hdv = select(GuideAssignment.tour_id).where(GuideAssignment.guide_id == dg.doi_tuong_id)
    kn = db.execute(
        select(Complaint).where(
            Complaint.handler == u.username,
            Complaint.nhom == "hdv",
            Complaint.status.notin_(KN_DA_DONG),
            Complaint.tour_id.in_(tour_cua_hdv),
        )
    ).scalars().first()
    if kn is None:
        return ""
    return (f"Chuyển Chủ tịch hoặc TGĐ: người đang mở màn hình này giữ một khiếu nại chưa đóng "
            f"về chuyến có chính hướng dẫn viên này ({kn.code}). Khiếu nại đóng lại là nút mở ra.")


def duyet(db: Session, u, dg: DanhGiaSauTour, dong_y: bool, ly_do: str = "") -> dict:
    """Một trong ba người bấm. MỘT chữ ký là đủ — Chủ tịch chốt 16/10/2026.

    Luật hai chữ ký của VTOS sinh ra cho TIỀN (một người chuẩn chi, một người xác nhận đã chi).
    Một lời nhận xét của khách không thuộc loại ấy, và bắt ba người cùng ký cho mỗi nhận xét thì
    hàng đợi đứng, rồi sẽ không ai duyệt cái nào.

    `dong_y=True` là ĐĂNG, `False` là KHÔNG ĐĂNG kèm lý do bắt buộc. Lý do vào sổ, không hiện cho
    khách.
    """
    duyet_duoc, bang_quyen = ai_duyet_duoc(db, u)
    if not duyet_duoc:
        return {"xong": False, "loi": "Không có quyền duyệt công bố."}
    vuong = vuong_chong_vai(db, u, dg)
    if vuong:
        return {"xong": False, "loi": vuong}
    r = db.execute(select(DongYCongKhai)
                   .where(DongYCongKhai.danh_gia_id == dg.id)).scalars().first()
    if r is None or r.tra_loi != "co":
        return {"xong": False, "loi": "Khách chưa đồng ý đăng công khai — cửa này không mở."}
    if r.rut_luc is not None:
        return {"xong": False, "loi": "Khách đã rút đồng ý."}
    if not dong_y and not (ly_do or "").strip():
        return {"xong": False, "loi": "Không đăng thì phải ghi lý do."}
    r.duyet_boi = u.username
    r.duyet_luc = datetime.now()
    r.duyet_bang_quyen = bang_quyen
    r.duyet_ket_qua = "dang" if dong_y else "khong_dang"
    r.duyet_ly_do = (ly_do or "").strip()[:1000]
    db.flush()
    return {"xong": True, "loi": "", "ket_qua": r.duyet_ket_qua, "bang_quyen": bang_quyen}


def go(db: Session, u, dg: DanhGiaSauTour, ly_do: str = "") -> dict:
    """GỠ khỏi hồ sơ công khai. LỆCH CHIỀU CÓ CHỦ Ý so với đăng.

    Đăng cần một trong ba người; gỡ thì BẤT KỲ AI trong ba cũng gỡ được ngay, không phải hỏi
    người đã đăng, và hàng rào chồng vai KHÔNG chặn ở đây. Lý do: đăng nhầm thì sửa được bằng
    cách gỡ; không gỡ được mới là cái kẹt. Một hàng rào ngăn người ta gỡ một thứ đang hiển thị
    sai là hàng rào đặt ngược chiều.
    """
    duyet_duoc, bang_quyen = ai_duyet_duoc(db, u)
    if not duyet_duoc:
        return {"xong": False, "loi": "Không có quyền gỡ."}
    r = db.execute(select(DongYCongKhai)
                   .where(DongYCongKhai.danh_gia_id == dg.id)).scalars().first()
    if r is None:
        return {"xong": False, "loi": "Nhận xét này chưa từng được đăng."}
    r.duyet_ket_qua = "khong_dang"
    r.go_boi = u.username
    r.go_luc = datetime.now()
    r.go_ly_do = (ly_do or "").strip()[:1000]
    db.flush()
    return {"xong": True, "loi": "", "bang_quyen": bang_quyen}


# ── CỬA ĐỌC CÔNG KHAI ─────────────────────────────────────────────────────────────────────────
def cong_khai_duoc(r: DongYCongKhai | None) -> bool:
    """ĐÚNG MỘT chỗ trả lời câu «nhận xét này có được hiện công khai không».

    Mọi cửa công khai hỏi hàm này. Dựng câu điều kiện thứ hai ở nơi khác là ngày hai câu lệch
    nhau thì một lời nhận xét khách đã rút vẫn nằm trên mạng, và không ai biết vì sao.
    """
    if r is None:
        return False
    return (r.tra_loi == "co"
            and r.rut_luc is None
            and r.duyet_luc is not None
            and r.duyet_ket_qua == "dang")


def hang_doi(db: Session, u) -> dict:
    """Hàng đợi duyệt + ba ô đếm. Ô đếm để Chủ tịch quyết có cần thêm người duyệt hay không.

    `cho_lau_nhat_ngay` tính từ lúc KHÁCH ĐỒNG Ý, không phải từ lúc nhận xét được viết: con số
    cần đo là «người có quyền để nó nằm đấy bao lâu», không phải «nhận xét này cũ bao nhiêu».
    """
    rows = list(db.execute(
        select(DongYCongKhai).where(DongYCongKhai.tra_loi == "co",
                                    DongYCongKhai.rut_luc.is_(None),
                                    DongYCongKhai.duyet_luc.is_(None))
        .order_by(DongYCongKhai.hoi_luc)
    ).scalars())

    bay_gio = datetime.now()
    ds = []
    for r in rows:
        dg = db.get(DanhGiaSauTour, r.danh_gia_id)
        if dg is None:
            continue
        ds.append({
            "danh_gia_id": dg.id,
            "hdv_ten": dg.doi_tuong_ten, "doi_tuong": dg.doi_tuong,
            "diem": dg.diem, "nhan_xet": dg.nhan_xet,
            "dong_y_luc": r.hoi_luc.strftime("%d/%m/%Y") if r.hoi_luc else "",
            "cho_ngay": (bay_gio - r.hoi_luc).days if r.hoi_luc else None,
            "nhan_nguoi_viet": nhan_nguoi_viet(db, dg),
            "ly_do_lui_nhan": ly_do_lui_nhan(db, dg),
            "vuong_chong_vai": vuong_chong_vai(db, u, dg),
        })

    da_dang = db.execute(select(func.count()).select_from(DongYCongKhai)
                         .where(DongYCongKhai.duyet_ket_qua == "dang")).scalar() or 0
    da_rut = db.execute(select(func.count()).select_from(DongYCongKhai)
                        .where(DongYCongKhai.rut_luc.is_not(None))).scalar() or 0
    duyet_duoc, bang_quyen = ai_duyet_duoc(db, u)
    return {
        "rows": ds,
        "dang_cho": len(ds),
        "cho_lau_nhat_ngay": max([d["cho_ngay"] or 0 for d in ds], default=0),
        "da_dang": da_dang, "da_rut": da_rut,
        "ban_duyet_duoc": duyet_duoc, "ban_duyet_bang": bang_quyen,
        "cau_hoi": CAU_HOI,
        "luu_y": ("Hàng đợi chỉ chứa nhận xét có đồng ý MỚI của Đợt HD-DG3. Nhận xét thu trước "
                  "đợt này không có đồng ý ấy nên không nằm đây — rỗng không có nghĩa là không "
                  "ai khen."),
    }
