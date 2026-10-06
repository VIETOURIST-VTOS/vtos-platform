# -*- coding: utf-8 -*-
"""TX-1 · Tách vai `xe_hdv` thành `tai_xe` và `hdv` — Chủ tịch quyết 05/10/2026.

Bộ hàng rào này canh đúng BA điều, và cố ý không canh gì thêm:

  1. Vai gộp đã nghỉ hưu và không sống lại ở bất cứ đâu trong mã đang chạy.
  2. Tách vai KHÔNG nới quyền: hai vai mới có phạm vi BẰNG NHAU và bằng đúng phạm vi vai cũ.
  3. Phép đổi vai của bản trích nhân sự đọc theo CHỨC DANH, và dòng nào chức danh không nói rõ thì
     rơi về vai hiện trường của đúng phòng ấy — KHÔNG tự nâng lên vai quản lý.

Vì sao điều 2 đáng một phép thử riêng: tách một vai là lúc dễ nhất để lặng lẽ cho một bên thêm cửa,
vì người đọc bản sửa đang bận so hai cái tên chứ không bận đếm cửa.
"""
import os, sys, io, re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.models.core import ROLES            # noqa: E402
from app.services import access as AC        # noqa: E402
from app.services import staff as ST         # noqa: E402


def _doc(duong_dan: str) -> str:
    return io.open(os.path.join(GOC, duong_dan), encoding="utf-8").read()


def test_tx1_1_hai_vai_co_trong_danh_muc_va_vai_gop_da_nghi_huu():
    assert ROLES.get("tai_xe") == "Tài xế"
    assert ROLES.get("hdv") == "Hướng dẫn viên"
    assert "xe_hdv" not in ROLES, "vai gộp phải biến mất khỏi danh mục, không chỉ bị đổi nhãn"


def test_tx1_2_khong_con_ma_dang_chay_nao_nhac_vai_gop():
    """Chỉ chú thích và bảng dịch vai nghỉ hưu được phép nhắc tên cũ. Một chuỗi `"xe_hdv"` còn sót
    trong require_roles hay trong một tuple quyền là một cánh cửa khóa im lặng: không ai báo lỗi,
    người mang vai mới chỉ đơn giản là không vào được."""
    con_sot = []
    for thu_muc in ("app/services", "app/api/v1", "app/models"):
        goc = os.path.join(GOC, thu_muc)
        for ten in sorted(os.listdir(goc)):
            if not ten.endswith(".py"):
                continue
            for i, dong in enumerate(io.open(os.path.join(goc, ten), encoding="utf-8"), 1):
                if '"xe_hdv"' not in dong:
                    continue
                # Bảng dịch vai nghỉ hưu trong staff.py là chỗ DUY NHẤT được cầm tên cũ như dữ liệu.
                if ten == "staff.py" and "VAI_NGHI_HUU" in _doc(f"{thu_muc}/{ten}"):
                    if dong.strip().startswith('"xe_hdv":'):
                        continue
                con_sot.append(f"{thu_muc}/{ten}:{i}")
    assert not con_sot, "còn mã đang chạy cầm tên vai đã nghỉ hưu: " + ", ".join(con_sot)


def test_tx1_3_tach_vai_khong_noi_quyen_cho_ai():
    """Hai vai mới phải thấy ĐÚNG những màn hình vai cũ thấy, và thấy GIỐNG NHAU."""
    mh_tai_xe = AC.menus_for(type("U", (), {"role": "tai_xe"})())
    mh_hdv = AC.menus_for(type("U", (), {"role": "hdv"})())
    assert mh_tai_xe == mh_hdv, f"hai vai lệch nhau: {mh_tai_xe} ≠ {mh_hdv}"
    assert "/xe-hdv" in mh_tai_xe and "/doi-mat-khau" in mh_tai_xe

    pv_tai_xe = AC.pham_vi_day_du("tai_xe")
    pv_hdv = AC.pham_vi_day_du("hdv")
    assert set(pv_tai_xe) == set(pv_hdv), (
        "phạm vi API của hai vai phải bằng nhau — lệch nghĩa là lần tách này đã nới cho một bên: "
        f"chỉ tài xế có {sorted(set(pv_tai_xe) - set(pv_hdv))}, "
        f"chỉ HDV có {sorted(set(pv_hdv) - set(pv_tai_xe))}")

    # Và vẫn phải hẹp: người ở hiện trường không chạm bảng lương, ngân hàng, hồ sơ khách.
    for cam in ("/api/v1/payroll", "/api/v1/banks", "/api/v1/bookings", "/api/v1/tours"):
        for vai, pv in (("tai_xe", pv_tai_xe), ("hdv", pv_hdv)):
            assert not any(p.startswith(cam) for p in pv), f"{vai} chạm được {cam}"


def test_tx1_4_hai_vai_deu_phai_khai_trong_ba_bang_quyen():
    """Thiếu một bảng là một kiểu hỏng riêng: thiếu RESTRICTED_ROLE_MENUS thì vai mới rơi về quy ước
    'trang không liệt kê = ai cũng thấy' và mở toang; thiếu RESTRICTED_API_PREFIXES thì mất đúng cửa
    sự vụ của chính mình; thiếu bảng hạn mức AI thì màn hình khai quyền AI không nói được gì về họ."""
    from app.services.ai_quyen import MAC_DINH
    for vai in ("tai_xe", "hdv"):
        assert vai in AC.RESTRICTED_ROLE_MENUS, f"{vai} chưa khai trong RESTRICTED_ROLE_MENUS"
        assert vai in AC.RESTRICTED_API_PREFIXES, f"{vai} chưa khai trong RESTRICTED_API_PREFIXES"
        assert vai in MAC_DINH, f"{vai} chưa khai hạn mức AI"
    assert AC.FIELD == ("tai_xe", "hdv")


def test_tx1_5_phep_doi_vai_doc_theo_chuc_danh_khong_tu_nang_quyen():
    """Bản trích nhân sự HCNS còn ghi mã cũ cho tới kỳ xuất tiếp theo, nên phép đổi nằm trong mã."""
    assert ST.vai_tro_cua({"vai_tro": "xe_hdv", "vi_tri": "tai_xe", "phong": "doi_xe"}) == "tai_xe"
    assert ST.vai_tro_cua({"vai_tro": "xe_hdv", "vi_tri": "hdv", "phong": "huong_dan"}) == "hdv"
    # Chức danh không nói rõ → vai HIỆN TRƯỜNG của phòng ấy, giữ nguyên phạm vi hôm nay.
    assert ST.vai_tro_cua({"vai_tro": "xe_hdv", "vi_tri": "tp", "phong": "doi_xe"}) == "tai_xe"
    assert ST.vai_tro_cua({"vai_tro": "xe_hdv", "vi_tri": "tp", "phong": "huong_dan"}) == "hdv"
    # KHÔNG được tự nâng lên vai quản lý: nâng quyền một tài khoản đang chạy phải có người ký.
    for phong in ("doi_xe", "huong_dan"):
        assert ST.vai_tro_cua({"vai_tro": "xe_hdv", "vi_tri": "tp", "phong": phong}) not in ("gd_doi_xe", "tp_hd")
    # Vai trò khác đi qua không bị đụng tới.
    assert ST.vai_tro_cua({"vai_tro": "nv_kd", "vi_tri": "nv", "phong": "kd_le"}) == "nv_kd"


def test_tx1_6_moi_vai_trong_ban_trich_nhan_su_deu_doi_duoc_sang_vai_dang_song():
    """Nếu bản trích còn một dòng không đổi được sang vai đang sống, người ấy mất tài khoản im lặng."""
    hong = []
    for r in ST.load_master():
        vai = ST.vai_tro_cua(r)
        if vai and vai not in ROLES:
            hong.append(f"{r.get('ma', '?')} · phòng {r.get('phong', '?')} · vị trí {r.get('vi_tri', '?')} → {vai}")
    assert not hong, "bản trích nhân sự có dòng không đổi được sang vai đang sống: " + "; ".join(hong)


def test_tx1_7_migration_tach_vai_co_mat_va_noi_dung_mach():
    """Đổi mã mà không đổi dữ liệu thì mọi tài khoản đang mang vai cũ bị khóa ngoài sau lần triển khai
    kế tiếp — không báo lỗi, chỉ là đăng nhập xong không thấy gì."""
    goc = os.path.join(GOC, "alembic", "versions")
    tep = [t for t in os.listdir(goc) if "tach_vai" in t]
    assert tep, "chưa có migration đổi vai của tài khoản đang dùng"
    s = io.open(os.path.join(goc, tep[0]), encoding="utf-8").read()
    assert "UPDATE users SET role" in s
    assert "employees" in s and "position" in s, "migration phải chia theo chức danh, không đoán"

    # Một đầu mạch: mọi down_revision phải có bản tương ứng, và chỉ được đúng một bản không ai nối vào.
    ban, noi_vao = {}, set()
    for t in os.listdir(goc):
        if not t.endswith(".py"):
            continue
        d = io.open(os.path.join(goc, t), encoding="utf-8").read()
        r = re.search(r'^revision\s*=\s*["\']([^"\']+)', d, re.M)
        v = re.search(r'^down_revision\s*=\s*["\']([^"\']+)', d, re.M)
        if r:
            ban[r.group(1)] = t
        if v:
            noi_vao.add(v.group(1))
    dau = [k for k in ban if k not in noi_vao]
    assert len(dau) == 1, "mạch migration có nhiều hơn một đầu, triển khai sẽ hỏng: " + str([ban[d] for d in dau])
