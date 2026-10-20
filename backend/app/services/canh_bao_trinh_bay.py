# -*- coding: utf-8 -*-
"""GD-1 · Trình bày cảnh báo cho màn hình điều hành (hợp đồng API mục V, giao Robot B 11/9/2026).

Thay cho việc trình duyệt tự dịch mã loại cảnh báo và tự gom. Máy chủ trả về danh sách ĐÃ dịch
tiếng Việt và ĐÃ tách hai nhóm; Robot B vẽ thẳng, không dịch lại.

KHÔNG đụng vào dashboard.py – tệp ấy chưa giao cho làn nào, và một tệp chưa có chủ mà bốn làn cùng
sửa là chỗ hỏng chắc chắn nhất trong kho.

Ba quy tắc của mục V, và mỗi quy tắc sinh ra từ một cách đọc sai cụ thể:

  (1) GOM THEO NGUYÊN NHÂN, không gom theo mức. Gom theo mức cho ra "23 việc đỏ" – một con số
      không nói được phải làm gì. Gom theo nguyên nhân cho ra "23 booking quá hạn thu tiền", và
      câu ấy có người xử lý được.

  (2) "ĐÃ TỰ XỬ LÝ" TÁCH KHỎI "CHƯA GIẢI QUYẾT". Trộn hai thứ làm con số đỏ trên màn hình lãnh đạo
      TO HƠN SỰ THẬT. Người ta nhìn một con số to rồi hoặc hoảng, hoặc – nguy hơn – quen với nó.

  (3) CHƯA CÓ CHỦ LÀ MỘT DÒNG ĐƯỢC ĐẾM, không phải một ô trống bị bỏ qua. Đây là quy tắc PQ-9 viết
      ra sau khi đo: 1.557 trên 1.703 cảnh báo chưa xử lý, vì một cảnh báo gửi cho bốn vai trò là
      gửi cho không ai.

────────────────────────────────────────────────────────────────────────────────────────────────
BỘ MÃ LOẠI CẢNH BÁO LÀ BỘ MỞ – VÀ ĐÓ LÀ LÝ DO TỆP NÀY KHÔNG DÁM CÓ MỘT BẢNG DỊCH "ĐẦY ĐỦ"

Đo ngày 11/9/2026: cảnh báo được sinh ra ở nhiều nơi, và có chỗ truyền `kind` bằng BIẾN
(`Alert(kind=kind ...)`, `Alert(kind=it["kind"] ...)`) chứ không bằng chuỗi viết sẵn. Nghĩa là
không tồn tại một danh sách tĩnh nào đọc ra được đủ mọi mã loại – ai viết một bảng dịch rồi tuyên
bố "đã đủ" là đang tuyên bố về một thứ không đo được.

Nên tệp này làm ngược lại: khai những mã ĐỌC ĐƯỢC TỪ MÃ NGUỒN, và ĐO trên dữ liệu thật xem còn mã
nào chưa có nhãn. Mã chưa có nhãn KHÔNG bị giấu và KHÔNG được đặt tên bừa – nó hiện nguyên mã kèm
cờ `can_dat_ten`, để người nhìn màn hình biết ngay là còn một loại chưa ai đặt tên tiếng Việt.

Đặt tên bừa nguy hơn để nguyên mã: một cái nhãn tiếng Việt trông như đã có người xét, nên sẽ không
ai đi xét nữa.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Alert, User

# Mức hiển thị. Alert.level dùng info/warn/red; màn hình dùng ba chữ Việt.
MUC = {"red": "do", "warn": "vang", "info": "xam"}
MUC_MAC_DINH = "xam"


class Loai:
    """Một loại cảnh báo: nhãn tiếng Việt, và nó có tự lành hay không.

    `robot_tu_xu_ly=True` nghĩa là hệ thống tự đóng được loại này mà không cần người – khi đóng, nó
    thuộc nhóm "đã tự xử lý", không thuộc nhóm việc còn nợ.
    """

    def __init__(self, nhan: str, robot_tu_xu_ly: bool = False, nguon_khai: str = ""):
        self.nhan, self.robot_tu_xu_ly, self.nguon_khai = nhan, robot_tu_xu_ly, nguon_khai


# Chỉ khai những mã ĐỌC ĐƯỢC từ mã nguồn, kèm chỗ đọc ra. Mã nào không dẫn được nguồn thì KHÔNG
# khai – để nó rơi vào danh sách đo được ở dưới, hơn là đặt cho nó một cái tên đoán.
NHAN = {
    "d7": Loai("Chuyến sắp khởi hành chưa đủ khách hòa vốn",
               nguon_khai="rules.py – add('d7', …) mốc D-7, so booked_pax với breakeven_pax"),
    "qua_han_qt": Loai("Chuyến quá hạn quyết toán",
                       nguon_khai="rules.py add('qua_han_qt', …); chu_canh_bao: ref = mã chuyến"),
    "sla_booking": Loai("Booking quá hạn xử lý theo cam kết",
                        nguon_khai="rules.py – add('sla_booking', …)"),
    "qua_deadline_thu": Loai("Quá hạn thu tiền khách",
                             nguon_khai="chu_canh_bao.py – ref = booking:<mã>, chủ là sale. Từ "
                                        "25/9/2026 chủ ĐI LÊN theo thang bậc đòi nợ ba cấp "
                                        "(thang_doi_no.py::quet), khác nhau giữa mảng Đoàn và Lẻ"),
    "bc_ngay_1": Loai("Thiếu báo cáo ngày (lần nhắc 1)",
                      nguon_khai="chu_canh_bao.py – ref = <mã NV>:<ngày>"),
    "bc_ngay_2": Loai("Thiếu báo cáo ngày (lần nhắc 2)",
                      nguon_khai="chu_canh_bao.py – ref = <mã NV>:<ngày>"),
    "cham_soc_qua_han": Loai("Phiếu chăm sóc khách quá hạn",
                             nguon_khai="chu_canh_bao.py – ref = cs:<id>, chủ là người giữ phiếu"),
    "sale_tra_loi_cham": Loai("Sale trả lời khách chậm",
                              nguon_khai="chu_canh_bao.py – ref = conv:<id>"),
    "r9_chay_duoi_hoa_von": Loai("Chuyến chạy dưới hòa vốn – chờ Ban lãnh đạo quyết",
                                 nguon_khai="chu_canh_bao.CO_Y_KHONG_CHU"),
    "r9_gd_cho_khop": Loai("Giao dịch ngân hàng chờ khớp",
                           nguon_khai="chu_canh_bao.CO_Y_KHONG_CHU"),
    "thieu_du_toan": Loai("Chuyến chưa có dự toán", nguon_khai="Alert(kind='thieu_du_toan')"),
    "zalo_token_hong": Loai("Khoá kết nối Zalo OA hỏng",
                            nguon_khai="Alert(kind='zalo_token_hong')"),
    "qt_tra_lai": Loai("Kế toán trả lại quyết toán – cần sửa",
                       nguon_khai="tra_lai_quyet_toan.CHUONG_TRA_LAI (PC-1)"),
    "phap_che_yc_moi": Loai("Yêu cầu Pháp chế mới từ phòng ban",
                            nguon_khai="phap_che_viec.CHUONG_YC_MOI (PC-1)"),
    "het_han_giu_cho": Loai("Hết hạn giữ chỗ – hệ thống đã trả chỗ về chuyến",
                            robot_tu_xu_ly=True,
                            nguon_khai="Alert(kind='het_han_giu_cho'); giữ chỗ có thời hạn (VPM-7)"),
}


def nhan_cua(ma: str) -> dict:
    """Nhãn để vẽ thẳng. Mã chưa khai thì trả nguyên mã kèm cờ – KHÔNG đặt tên bừa.

    Một cái nhãn tiếng Việt trông như đã có người xét, nên sẽ không ai đi xét nữa. Để nguyên mã thì
    xấu, nhưng xấu ở đúng chỗ cần sửa.
    """
    lo = NHAN.get(ma)
    if lo is None:
        return {"nhan": ma or "(không có mã loại)", "can_dat_ten": True, "robot_tu_xu_ly": False}
    return {"nhan": lo.nhan, "can_dat_ten": False, "robot_tu_xu_ly": lo.robot_tu_xu_ly}


def _muc(level: str) -> str:
    return MUC.get((level or "").strip(), MUC_MAC_DINH)


# Thứ tự nặng dần, để chọn mức đại diện cho cả nhóm.
NANG_DAN = ["xam", "vang", "do"]


def loai_chua_co_nhan(db: Session) -> list[dict]:
    """Mã loại CÓ THẬT trong bảng cảnh báo mà chưa ai đặt tên tiếng Việt.

    Danh sách VIỆC, không phải danh sách lỗi – và nó phải được đo trên dữ liệu thật, vì bộ mã là bộ
    mở: có chỗ truyền kind bằng biến nên không đọc tĩnh ra hết được.
    """
    rows = db.execute(select(Alert.kind, func.count(Alert.id)).group_by(Alert.kind)).all()
    return sorted(({"ma": k or "", "so": int(n)} for k, n in rows if (k or "") not in NHAN),
                  key=lambda x: -x["so"])


def _da_tu_xu_ly(a: Alert) -> bool:
    """Đã đóng mà KHÔNG có người nào đóng nó → hệ thống tự đóng.

    Dùng `dong_boi_id` rỗng chứ không dùng danh sách loại: một loại hôm nay robot tự xử được, mai
    người ta tắt cái robot ấy đi, thì danh sách loại nói sai còn cột `dong_boi_id` vẫn nói đúng.
    Bảng khai NHAN chỉ dùng để đặt tên, không dùng để phán ai đã đóng.
    """
    return bool(a.resolved) and getattr(a, "dong_boi_id", None) is None


def trinh_bay(db: Session, gioi_han_vi_du: int = 2) -> dict:
    """Hai nhóm tách rời, gom theo NGUYÊN NHÂN, nhãn đã là tiếng Việt.

    Cảnh báo KHÔNG có cột pháp nhân, nên ở đây không lọc theo phạm vi đang xem. Ghi thẳng ra trong
    kết quả để màn hình không ngầm hiểu là đã lọc – một bảng tưởng đã lọc mà chưa lọc còn tệ hơn
    một bảng nói rõ là chưa.
    """
    tat_ca = list(db.execute(select(Alert)).scalars())
    ten = {u.id: u.full_name for u in db.execute(select(User)).scalars()}

    chua: dict[str, dict] = {}
    xong: dict[str, dict] = {}

    for a in tat_ca:
        ma = (a.kind or "").strip()
        n = nhan_cua(ma)
        if _da_tu_xu_ly(a):
            o = xong.setdefault(ma, {"khoa_gom": ma, "nhan": n["nhan"],
                                     "can_dat_ten": n["can_dat_ten"], "so_viec": 0})
            o["so_viec"] += 1
            continue
        if a.resolved:
            continue        # người đã xử lý xong: không phải việc còn nợ, cũng không phải "tự xử lý"
        o = chua.setdefault(ma, {"khoa_gom": ma, "nhan": n["nhan"], "can_dat_ten": n["can_dat_ten"],
                                 "muc": "xam", "so_viec": 0, "chua_co_chu": 0,
                                 "_nguoi": {}, "vi_du": []})
        o["so_viec"] += 1
        m = _muc(a.level)
        if NANG_DAN.index(m) > NANG_DAN.index(o["muc"]):
            o["muc"] = m
        # Người PHẢI LÀM, không phải danh sách được báo tin. to_roles trả lời câu khác.
        uid = getattr(a, "nguoi_phu_trach", None) or getattr(a, "nguoi_nhan_id", None)
        if uid:
            o["_nguoi"][int(uid)] = o["_nguoi"].get(int(uid), 0) + 1
        else:
            o["chua_co_chu"] += 1
        if len(o["vi_du"]) < gioi_han_vi_du:
            o["vi_du"].append((a.message or "").strip()[:120])

    for o in chua.values():
        o["nguoi_phu_trach"] = sorted(
            ({"id": i, "ten": ten.get(i, f"#{i}"), "so": s} for i, s in o.pop("_nguoi").items()),
            key=lambda x: -x["so"])

    ds_chua = sorted(chua.values(), key=lambda o: (-NANG_DAN.index(o["muc"]), -o["so_viec"]))
    ds_xong = sorted(xong.values(), key=lambda o: -o["so_viec"])
    return {
        "chua_giai_quyet": ds_chua,
        "da_tu_xu_ly": ds_xong,
        "tong_chua_co_chu": sum(o["chua_co_chu"] for o in ds_chua),
        "loai_chua_co_nhan": loai_chua_co_nhan(db),
        "co_loc_pham_vi": False,
        "ghi_chu": ("Cảnh báo chưa có cột pháp nhân nên danh sách này CHƯA lọc theo đơn vị đang "
                    "xem. Nhóm 'đã tự xử lý' tách khỏi 'chưa giải quyết' – gộp lại làm con số đỏ "
                    "to hơn sự thật. 'Chưa có chủ' là một dòng được đếm, không phải ô trống."),
    }
