"""P10 – tra cứu ngược: chọn một người, hiện đủ họ làm được gì, và VÌ SAO.

Vì sao việc này không phải là tiện ích. Quyền trong VTOS đến từ bốn nguồn khác nhau – ma trận
MENU_ROLES, danh sách hẹp khai tay của bảy vai trò, ngoại lệ cấp riêng theo người có hạn, và bản đồ
màn hình → nhóm API – và không nguồn nào nhìn thấy ba nguồn kia. Người quản lý muốn biết một nhân
viên vào được những đâu thì hôm nay phải đọc mã, mà đọc mã thì trong tháng rà quyền sẽ không ai đọc.
Không đọc thì không rà, không rà thì quyền chỉ nở ra chứ không co lại.

Điều kiện nghiệm thu là một câu: chọn một nhân viên bất kỳ, trả lời được "vì sao người này vào được
màn hình đó" trong MỘT lần bấm. Vì vậy mỗi dòng trả về ở đây bắt buộc mang theo `vi_sao` – nguồn nào
cho phép, và dòng nào trong nguồn ấy. Một danh sách quyền không kèm lý do thì người rà chỉ có thể
gật hoặc lắc, không thể sửa.

Đọc, không ghi. Module này không cấp và không thu quyền của ai.
"""
from datetime import date

from app.models.core import ROLES, CAPABILITIES, User
from app.services import access as AC


def _nguon_man_hinh(u: User, path: str, menu_grants: dict) -> dict:
    """Đúng một lý do cho mỗi màn hình, xếp theo thứ tự nguồn nào thắng trong mã thật."""
    if path in menu_grants:
        g = menu_grants[path]
        return {"nguon": "ngoai_le_theo_nguoi",
                "cau": f"Ngoại lệ cấp riêng cho người này, hết hiệu lực {g}."
                       if g else "Ngoại lệ cấp riêng cho người này, KHÔNG có hạn.",
                "dong": f"user_grants: menu={path}"}
    if path in AC.MAN_HINH_KHONG_DUOC_AN:
        return {"nguon": "khong_duoc_an",
                "cau": "Màn hình không được phép ẩn khỏi menu của bất kỳ ai – đổi mật khẩu, cảnh báo, "
                       "và chỗ nộp báo cáo công việc hằng ngày.",
                "dong": f"MAN_HINH_KHONG_DUOC_AN: {path}"}
    if u.role in AC.RESTRICTED_ROLE_MENUS:
        return {"nguon": "danh_sach_hep_khai_tay",
                "cau": f"Vai trò {ROLES.get(u.role, u.role)} nằm trong nhóm hẹp – màn hình khai tay.",
                "dong": f"RESTRICTED_ROLE_MENUS[{u.role!r}]"}
    if path in AC.MAN_HINH_MOI_NGUOI:
        return {"nguon": "moi_nguoi", "cau": "Màn hình ai đăng nhập cũng có.",
                "dong": f"MAN_HINH_MOI_NGUOI: {path}"}
    vai = AC.MENU_ROLES.get(path, ())
    if u.role in vai:
        nen = u.role in AC.BASE_VIEW
        return {"nguon": "ma_tran_menu",
                "cau": ("Vai trò này nằm trong nền BASE_VIEW (Chủ tịch, TGĐ, Ban Kiểm soát) nên có "
                        "mặt ở mọi dòng của ma trận." if nen
                        else f"Ma trận MENU_ROLES mở {path} cho vai trò {ROLES.get(u.role, u.role)}."),
                "dong": f"MENU_ROLES[{path!r}] = ({', '.join(vai)})"}
    return {"nguon": "khong_ro", "cau": "Không tìm ra dòng nào cho phép – phải rà lại.",
            "dong": ""}


def _nguon_api(u: User, nhom: str) -> dict:
    """Nhóm API vào được là do màn hình NÀO kéo theo. Trả lời bằng tên màn hình, không bằng tên biến."""
    if nhom in AC.API_CHUNG:
        return {"nguon": "api_chung", "cau": "Nhóm API ai đăng nhập cũng chạm được.",
                "dong": f"API_CHUNG: {nhom}"}
    qua = []
    for man in AC.MAN_HINH_MOI_NGUOI:
        if nhom in AC.MAN_HINH_API.get(man, ()):
            qua.append(man)
    # Đọc CẢ HAI nguồn khai màn hình. Bản đầu chỉ duyệt ma trận menu, nên bảy vai trò hẹp – bốn của
    # người, ba của máy – lấy màn hình từ danh sách CHO PHÉP đều bị gắn nhãn "khai tay, cần rà rồi bỏ
    # dần". Nhãn ấy sai và nguy hiểm theo một kiểu cụ thể: nó mời người rà đi xoá đúng những dòng đang
    # giữ quyền cho các vai trò hẹp. Ngày 09/9 nó suýt làm em xoá /api/v1/xe-hdv của Giám đốc đội xe và
    # Trưởng phòng Hướng dẫn – hai người sẽ mất cả phân hệ xe & HDV mà bảng vẫn báo "đã dọn sạch".
    for man in AC.RESTRICTED_ROLE_MENUS.get(u.role, ()):
        if nhom in AC.MAN_HINH_API.get(man, ()):
            qua.append(man)
    for man, vai_cua_man in AC.MENU_ROLES.items():
        if u.role in vai_cua_man and nhom in AC.MAN_HINH_API.get(man, ()):
            qua.append(man)
    if qua:
        return {"nguon": "theo_man_hinh",
                "cau": "Vào được vì màn hình " + ", ".join(sorted(set(qua))) + " gọi tới nhóm này.",
                "dong": f"MAN_HINH_API[{sorted(set(qua))[0]!r}] có {nhom}"}
    if nhom in AC.RESTRICTED_API_PREFIXES.get(u.role, ()):
        return {"nguon": "khai_tay_con_lai",
                "cau": "Khai tay từ trước, KHÔNG suy được từ màn hình nào – dòng cần rà rồi bỏ dần.",
                "dong": f"RESTRICTED_API_PREFIXES[{u.role!r}] có {nhom}"}
    return {"nguon": "khong_ro", "cau": "Không tìm ra đường nào dẫn tới nhóm này.", "dong": ""}


def tra_cuu(db, t: User) -> dict:
    """Ba lớp quyền của MỘT tài khoản, mỗi dòng kèm lý do.

    Nhận đối tượng người dùng chứ không nhận id: chỗ gọi đã phải tìm ra người rồi mới hỏi được, và
    nhận id ở đây sẽ đẻ thêm một đường đọc bảng users không đi qua kiểm quyền.
    """
    grants = AC._grants(db, t)
    menu_grants = {g.value: (g.den_ngay.isoformat() if getattr(g, "den_ngay", None) else "")
                   for g in grants if g.kind == "menu"}

    man_hinh = []
    # Chỉ lấy đúng danh sách menus_for trả về. Trước đây chỗ này cộng thêm MAN_HINH_MOI_NGUOI cho
    # "đầy đủ", và cái cộng thêm ấy làm bảng THẤY và bảng BỊ ẨN nói hai điều trái ngược về cùng một
    # người – đúng lỗi mà bảng tra cứu này sinh ra để phát hiện.
    for path in sorted(AC.menus_for(t, db)):
        man_hinh.append({"path": path, **_nguon_man_hinh(t, path, menu_grants)})

    api = [{"nhom": n, **_nguon_api(t, n)} for n in AC.pham_vi_day_du(t.role)]

    nang_luc = []
    for ma, ten in CAPABILITIES.items():
        co = AC.co_quyen(db, t, ma)
        if not co:
            continue
        if t.role in AC.BASE_VIEW:
            ly = {"nguon": "vai_tro_nen", "cau": f"Vai trò {ROLES.get(t.role, t.role)} có sẵn mọi năng lực.",
                  "dong": f"BASE_VIEW chứa {t.role}"}
        else:
            g = next((x for x in grants if x.kind == "capability" and x.value == ma), None)
            han = g.den_ngay.isoformat() if (g and getattr(g, "den_ngay", None)) else ""
            ly = {"nguon": "ngoai_le_theo_nguoi",
                  "cau": f"Cấp riêng cho người này, hết hiệu lực {han}." if han
                         else "Cấp riêng cho người này, KHÔNG có hạn – phải rà mỗi kỳ.",
                  "dong": f"user_grants: capability={ma}"}
        nang_luc.append({"ma": ma, "ten": ten, **ly})

    from app.services import pham_vi_phap_nhan as PV
    canh_bao = []
    if any(x["nguon"] == "khong_ro" for x in man_hinh):
        canh_bao.append("Có màn hình không tìm ra dòng cho phép – ma trận và danh sách hẹp đang lệch nhau.")
    if any(x["nguon"] == "khai_tay_con_lai" for x in api):
        canh_bao.append("Còn nhóm API khai tay không suy được từ màn hình nào; mỗi dòng như vậy là "
                        "một quyền không ai nhìn thấy trên giao diện.")
    vo_han = [x for x in nang_luc if "KHÔNG có hạn" in x["cau"]] + \
             [x for x in man_hinh if "KHÔNG có hạn" in x["cau"]]
    if vo_han:
        canh_bao.append("Có ngoại lệ KHÔNG thời hạn – quyền duy nhất trong hệ thống không tự co lại.")
    if not t.active:
        canh_bao.append("Tài khoản đã khóa: bảng dưới là quyền họ SẼ có nếu mở lại, không phải quyền hiện hành.")

    return {
        "tai_khoan": {"id": t.id, "username": t.username, "full_name": t.full_name,
                      "role": t.role, "role_name": ROLES.get(t.role, t.role),
                      "department": t.department, "staff_code": t.staff_code,
                      "active": bool(t.active), "ngoai_bien_che": bool(t.ngoai_bien_che),
                      "last_login": t.last_login},
        "pham_vi_phap_nhan": PV.mo_ta(db, t),
        "man_hinh": man_hinh,
        "man_hinh_bi_an": sorted(AC.hidden_menus_for(t, db)),
        "api": api,
        "nang_luc": nang_luc,
        "tab_nhan_su": AC.hr_tabs_for(db, t),
        "canh_bao": canh_bao,
        "dem": {"man_hinh": len(man_hinh), "api": len(api), "nang_luc": len(nang_luc)},
        "ngay_tra_cuu": date.today().isoformat(),
    }
