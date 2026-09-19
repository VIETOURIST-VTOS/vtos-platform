# -*- coding: utf-8 -*-
"""LK-1 · Cửa lọc tin khủng hoảng — bộ lọc XẾP HÀNG, người QUYẾT ĐỊNH.

Cái hỏng LẶNG ở đây không phải là bộ lọc chấm sai. Bộ lọc nào cũng chấm sai, và chấm sai thì sửa
được. Cái hỏng lặng là BỘ LỌC GIÀNH LẤY QUYẾT ĐỊNH: hôm nào đó một người thấy hàng đợi đúng nhiều
quá và thêm một dòng "điểm ≥ 4 thì tự đánh dấu khủng hoảng cho nhanh". Từ hôm ấy:

  · một tin bộ lọc bỏ sót là một tin KHÔNG CÒN AI NHÌN NỮA;
  · đồng hồ hai giờ vẫn xanh trên màn hình, vì nó chỉ đếm những vụ bộ lọc đã nhận ra;
  · và phép đo cũng đọc từ chính bộ lọc ấy, nên không con số nào trong hệ thống kêu lên.

Vì vậy tệp này gác bốn chỗ, theo đúng thứ tự quan trọng:

  A. KHÔNG CHỖ NÀO trong mã đặt `la_khung_hoang` từ điểm của bộ lọc.
  B. Không vứt tin nào đi: dưới ngưỡng là xếp sau, hạ ngưỡng là thấy lại.
  C. Chấm điểm đúng như đã ký, kể cả khi người ta gõ không dấu.
  D. Phép đo chính bộ lọc nói ra cả phần nó KHÔNG đo được.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_lk1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_lk1.db", "test_lk1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import inspect  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.core import Param  # noqa: E402
from app.models.crm import Conversation, Message  # noqa: E402
from app.models.marketing import HopThuXuLy, PrHoatDong  # noqa: E402
from app.services import loc_khung_hoang as LK  # noqa: E402
from app.services import rules as R  # noqa: E402

Base.metadata.create_all(engine)
BAY_GIO = datetime(2026, 9, 19, 12, 0, 0)


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(HopThuXuLy).delete()
    s.query(PrHoatDong).delete()
    s.query(Message).delete()
    s.query(Conversation).delete()
    s.query(Param).delete()
    s.commit()
    R.clear_param_cache()
    yield s
    s.query(Param).delete()
    s.commit()
    R.clear_param_cache()
    s.close()


def dat_tham_so(db, key, value):
    """Ghi đè một tham số cho một phép thử.

    Viết thẳng vào bảng Param rồi xoá đệm — đúng đường mà màn hình Tham số đi, trừ phần duyệt.
    Không xoá đệm thì phép thử đọc lại giá trị cũ trong tối đa 60 giây và đỏ một cách khó hiểu.
    """
    db.add(Param(key=key, value=str(value), label=key, unit="", effective_from=date(2026, 9, 1),
                 source="test", status="active", signed_chutich=True, signed_tgd=True,
                 proposed_by="test"))
    db.commit()
    R.clear_param_cache()


def hoi_thoai(db, kenh="facebook", ten="Khách A", chua_tra_loi=False, han=None):
    c = Conversation(channel=kenh, external_id=f"x{datetime.now().timestamp()}{ten}",
                     customer_name=ten, unanswered=chua_tra_loi, sla_due_at=han)
    db.add(c)
    db.flush()
    return c


def tin(db, c, text, luc=None):
    m = Message(conversation_id=c.id, direction="in", text=text, at=luc or BAY_GIO)
    db.add(m)
    db.flush()
    return m


# =============================================================================================
# A. BỘ LỌC KHÔNG ĐƯỢC QUYẾT ĐỊNH
# =============================================================================================
def test_A_khong_cho_nao_dat_la_khung_hoang_tu_diem_cua_bo_loc():
    """Phép thử ĐỌC MÃ, và nó là phép thử quan trọng nhất tệp này.

    Một phép thử hành vi chỉ chứng minh được rằng HÔM NAY bộ lọc không tự quyết. Phép thử này
    chặn cái cách người ta sẽ làm hỏng nó vào một buổi chiều bận: nối thẳng `diem` vào
    `la_khung_hoang`. Ở `loc_khung_hoang`, `la_khung_hoang` chỉ được phép lấy từ `r.get(...)` —
    tức là từ ô người tích.
    """
    src = inspect.getsource(LK)
    for dong in src.splitlines():
        if "la_khung_hoang" not in dong or dong.strip().startswith("#"):
            continue
        assert "diem" not in dong, (
            f"dòng nối điểm bộ lọc vào la_khung_hoang – đây đúng là chỗ bộ lọc giành quyết định: {dong.strip()!r}")
    # Và chỗ duy nhất ĐẶT nó – lời gọi PR.tao trong lap_pr – phải đọc từ ô người gửi lên.
    assert '"la_khung_hoang": bool(r.get("la_khung_hoang"))' in inspect.getsource(LK.lap_pr), \
        "lap_pr không còn lấy la_khung_hoang thẳng từ ô người tích"


def test_A_cua_loc_khong_dat_moc_dem_hai_gio():
    """`ghi_nhan_luc` là mốc bắt đầu đếm, và chỉ `pr_hoat_dong.tao` được đặt nó.

    ĐỌC được thì không sao – `do_bo_loc` phải lọc vụ theo kỳ. GÁN mới là chỗ hỏng: cửa lọc tự đặt
    mốc nghĩa là đồng hồ hai giờ bắt đầu chạy từ lúc TIN ĐẾN chứ không từ lúc người quyết, và mọi
    vụ nạp bù đều quá hạn ngay khi vừa lập.
    """
    src = pathlib.Path(LK.__file__).read_text(encoding="utf-8")
    for dong in src.splitlines():
        if dong.strip().startswith("#") or "ghi_nhan_luc" not in dong:
            continue
        assert not re.search(r"ghi_nhan_luc\s*=[^=]", dong), \
            f"cửa lọc GÁN mốc đếm hai giờ: {dong.strip()!r}"


def test_A_lap_pr_tich_o_nao_thi_ra_o_ay(db):
    c = hoi_thoai(db)
    m1 = tin(db, c, "Tôi sẽ kiện công ty này")      # điểm cao
    m2 = tin(db, c, "Tôi sẽ kiện công ty này lần nữa")
    db.commit()
    a = LK.lap_pr(db, m1.id, "nv1", {"la_khung_hoang": True})
    b = LK.lap_pr(db, m2.id, "nv1", {"la_khung_hoang": False})
    assert a["la_khung_hoang"] is True
    # Cùng một điểm, cùng một từ đỏ — nhưng người tích khác thì kết quả khác. Đó là toàn bộ điểm.
    assert b["la_khung_hoang"] is False


def test_A_dong_ho_bat_dau_luc_NGUOI_tich_chu_khong_luc_tin_den(db):
    c = hoi_thoai(db)
    m = tin(db, c, "lừa đảo", luc=BAY_GIO - timedelta(days=3))
    db.commit()
    kq = LK.lap_pr(db, m.id, "nv1", {"la_khung_hoang": True})
    h = db.get(PrHoatDong, kq["pr_id"])
    # Tin đến từ ba hôm trước, nhưng đồng hồ không được tính là đã chạy ba hôm: mốc đếm là lúc
    # việc VÀO SỔ. Nếu lấy giờ của tin thì mọi vụ nạp bù đều quá hạn ngay khi vừa lập.
    assert (datetime.now() - h.ghi_nhan_luc).total_seconds() < 120


# =============================================================================================
# B. KHÔNG VỨT TIN NÀO ĐI
# =============================================================================================
def test_B_duoi_nguong_la_xep_sau_khong_phai_bi_bo(db):
    c = hoi_thoai(db)
    tin(db, c, "cho em hỏi giá tour Phú Quốc")     # 0 điểm
    db.commit()
    cao = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)
    assert cao["dem"]["cho_xem"] == 0
    # Hạ ngưỡng xuống 0 thì tin ấy hiện lại — nó chưa bao giờ bị xoá.
    thap = LK.canh_bao(db, ngay=7, nguong_tuy=0, bay_gio=BAY_GIO)
    assert thap["dem"]["cho_xem"] == 1


def test_B_ha_nguong_khong_doi_tham_so_da_ky(db):
    c = hoi_thoai(db)
    tin(db, c, "xin chào")
    db.commit()
    truoc = LK.nguong(db)
    kq = LK.canh_bao(db, ngay=7, nguong_tuy=0, bay_gio=BAY_GIO)
    assert kq["nguong"] == 0 and kq["nguong_ky"] == truoc
    assert LK.nguong(db) == truoc, "xem lại ở ngưỡng thấp đã sửa luôn tham số đã ký"


def test_B_cua_loc_tho_khong_duoc_lam_mat_dong_khi_nguong_thap(db):
    """Cửa lọc thô ở máy chủ là tối ưu tốc độ, và tối ưu tốc độ là chỗ hay làm mất dòng nhất."""
    c = hoi_thoai(db)
    for i in range(6):                              # đủ để thành một DỐC (+1), không có từ đỏ
        tin(db, c, f"alo alo {i}", luc=BAY_GIO - timedelta(minutes=i))
    db.commit()
    kq = LK.canh_bao(db, ngay=7, nguong_tuy=1, bay_gio=BAY_GIO)
    assert kq["dem"]["cho_xem"] == 6, \
        "ngưỡng 1: tin chỉ có điểm DỐC phải vào hàng đợi, cửa lọc thô đang cắt mất chúng"


# =============================================================================================
# C. CHẤM ĐIỂM
# =============================================================================================
def test_C_bo_dau_va_khong_dau_la_mot():
    ds = ["lua dao"]
    assert LK.cham_diem("Công ty này LỪA ĐẢO", ds)[0] == LK.DIEM_TU_DO
    assert LK.cham_diem("cong ty nay lua dao", ds)[0] == LK.DIEM_TU_DO
    assert LK.cham_diem("Lừa Đảo!", ds)[0] == LK.DIEM_TU_DO


def test_C_khop_theo_ranh_gioi_tu_khong_khop_giua_chu():
    """"tố" nằm giữa "tối nay" không phải là tố cáo. Khớp lỏng sinh ra hàng đợi toàn tin vô hại,
    và một hàng đợi toàn tin vô hại là một hàng đợi không ai mở."""
    assert LK.cham_diem("tối nay em đi được không", ["to"])[0] == 0
    assert LK.cham_diem("tôi sẽ tố công ty", ["to"])[0] == LK.DIEM_TU_DO


def test_C_nhieu_tu_do_van_cong_hai_diem_mot_lan():
    ds = ["lua dao", "kien", "cong an"]
    assert LK.cham_diem("lừa đảo, tôi sẽ kiện, gọi công an", ds)[0] == LK.DIEM_TU_DO


def test_C_ly_do_noi_ra_tu_nao_da_khop():
    _d, ly = LK.cham_diem("các anh lừa đảo", ["lua dao", "kien"])
    assert any("lua dao" in x for x in ly), f"lý do không nêu từ đã khớp: {ly}"


def test_C_ba_dau_hieu_cong_don():
    ds = ["lua dao"]
    assert LK.cham_diem("lừa đảo", ds, True, True)[0] == LK.DIEM_TU_DO + LK.DIEM_DOC + LK.DIEM_QUA_HAN
    assert LK.cham_diem("bình thường", ds, True, True)[0] == LK.DIEM_DOC + LK.DIEM_QUA_HAN


def test_C_doc_dem_theo_HOI_THOAI_khong_theo_ca_hop_thu(db):
    """Cả hộp thư đông lên chủ nhật là chuyện bình thường của công ty lữ hành; một người nhắn sáu
    tin trong một giờ thì không."""
    a = hoi_thoai(db, ten="A")
    for i in range(6):
        tin(db, a, f"hỏi {i}", luc=BAY_GIO - timedelta(minutes=i))
    for j in range(6):                               # sáu người khác nhau, mỗi người một tin
        b = hoi_thoai(db, ten=f"B{j}")
        tin(db, b, "hỏi giá", luc=BAY_GIO - timedelta(minutes=j))
    db.commit()
    kq = LK.canh_bao(db, ngay=7, nguong_tuy=1, bay_gio=BAY_GIO)
    khach = {r["khach"] for r in kq["rows"]}
    assert khach == {"A"}, f"dốc phải đếm theo hội thoại, không theo cả hộp thư: {khach}"


def test_C_qua_han_tra_loi_chi_tinh_khi_that_su_qua(db):
    chua = hoi_thoai(db, ten="Trễ", chua_tra_loi=True, han=BAY_GIO - timedelta(minutes=5))
    tin(db, chua, "alo")
    con_han = hoi_thoai(db, ten="Còn hạn", chua_tra_loi=True, han=BAY_GIO + timedelta(minutes=5))
    tin(db, con_han, "alo")
    db.commit()
    kq = LK.canh_bao(db, ngay=7, nguong_tuy=1, bay_gio=BAY_GIO)
    assert {r["khach"] for r in kq["rows"]} == {"Trễ"}


def test_C_chi_doc_tin_KHACH_gui_vao(db):
    c = hoi_thoai(db)
    m = Message(conversation_id=c.id, direction="out", sender="sale",
                text="Dạ công ty em không lừa đảo đâu ạ", at=BAY_GIO)
    db.add(m)
    db.commit()
    kq = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)
    assert kq["dem"]["cho_xem"] == 0, "câu trả lời của sale bị chấm như tin khách"


def test_C_khong_tra_ve_so_dien_thoai_cua_khach(db):
    c = hoi_thoai(db)
    c.phone = "0901234567"
    tin(db, c, "lừa đảo")
    db.commit()
    kq = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)
    assert "0901234567" not in str(kq), "hàng đợi để lộ số điện thoại khách ra một màn hình cả phòng đọc"


def test_C_danh_sach_tu_do_doc_SONG_tu_tham_so(db):
    c = hoi_thoai(db)
    tin(db, c, "món này dở tệ")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 0
    dat_tham_so(db, LK.THAM_SO_TU_DO, R.get_param_chu(db, LK.THAM_SO_TU_DO) + ",do te")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 1, \
        "thêm một từ vào tham số mà hàng đợi không đổi – danh sách đang bị nhớ cứng ở đâu đó"


# =============================================================================================
# D. KẾT LUẬN CỦA NGƯỜI, VÀ PHÉP ĐO CHÍNH BỘ LỌC
# =============================================================================================
def test_D_bo_qua_bat_buoc_co_ly_do(db):
    c = hoi_thoai(db)
    m = tin(db, c, "lừa đảo")
    db.commit()
    with pytest.raises(ValueError):
        LK.bo_qua(db, m.id, "nv1", "   ")
    LK.bo_qua(db, m.id, "nv1", "khách nhầm công ty khác")
    x = db.execute(select(HopThuXuLy).where(HopThuXuLy.message_id == m.id)).scalars().first()
    assert x.ket_luan == "bo_qua" and "nhầm công ty" in x.ghi_chu


def test_D_da_xu_ly_thi_roi_khoi_hang_doi(db):
    c = hoi_thoai(db)
    m = tin(db, c, "lừa đảo")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 1
    LK.bo_qua(db, m.id, "nv1", "khách nhầm")
    sau = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)
    assert sau["dem"]["cho_xem"] == 0
    # ĐO CẢ SỐ DÒNG, không chỉ con số đếm. Bẻ mã 19/9/2026 (M17) thoát ra ở đúng khe này: bỏ phép
    # loại dòng đã xử lý thì `cho_xem` vẫn bằng 0 – vì nó đếm theo `ket_luan` rỗng – trong khi
    # bảng trước mắt người trực đầy lại những dòng họ vừa xử lý xong.
    assert len(sau["rows"]) == 0, "dòng đã xử lý vẫn nằm lại trong hàng đợi"
    # Nhưng vẫn tra lại được — bỏ qua không phải là xoá.
    assert len(LK.canh_bao(db, ngay=7, ke_ca_da_xu_ly=True, bay_gio=BAY_GIO)["rows"]) == 1


def test_D_mot_tin_khong_lap_hai_dong_PR(db):
    """Hai người cùng mở hàng đợi rồi cùng bấm là chuyện xảy ra ĐÚNG LÚC đang có khủng hoảng thật,
    và bảng quá hạn đếm đôi thì con số sai ngay ở vụ đầu tiên."""
    c = hoi_thoai(db)
    m = tin(db, c, "lừa đảo")
    db.commit()
    LK.lap_pr(db, m.id, "nv1", {"la_khung_hoang": True})
    with pytest.raises(ValueError):
        LK.lap_pr(db, m.id, "nv2", {"la_khung_hoang": True})
    assert db.query(PrHoatDong).count() == 1


def test_D_dong_PR_giu_duong_di_nguoc_ve_tin_nguon(db):
    c = hoi_thoai(db)
    m = tin(db, c, "lừa đảo")
    db.commit()
    kq = LK.lap_pr(db, m.id, "nv1", {"la_khung_hoang": True})
    assert db.get(PrHoatDong, kq["pr_id"]).nguon_message_id == m.id


def test_D_do_bo_loc_dem_bat_dung_bao_nham_bo_sot(db):
    trung = hoi_thoai(db, ten="Trúng")
    m1 = tin(db, trung, "lừa đảo")
    nham = hoi_thoai(db, ten="Nhầm")
    m2 = tin(db, nham, "tôi sẽ kiện")
    db.commit()
    LK.lap_pr(db, m1.id, "nv1", {"la_khung_hoang": True})
    LK.bo_qua(db, m2.id, "nv1", "khách nói đùa")
    d = LK.do_bo_loc(db)
    assert d["bat_dung"] == 1 and d["bao_nham"] == 1 and d["bo_sot"] == 0


def test_D_bo_sot_cham_LAI_bang_bo_loc_HIEN_TAI(db):
    """Câu hỏi cần trả lời không phải "hồi đó bộ lọc thế nào" mà "bộ lọc BÂY GIỜ có bắt được vụ ấy
    không" — đó mới là con số dùng để quyết có sửa danh sách từ đỏ hay không."""
    c = hoi_thoai(db, ten="Sót")
    m = tin(db, c, "các anh làm ăn như vậy là không được")   # 0 điểm hôm nay
    db.commit()
    # Người trực vẫn thấy đây là khủng hoảng và lập dòng — bộ lọc đã không nêu nó.
    LK.lap_pr(db, m.id, "nv1", {"la_khung_hoang": True})
    d = LK.do_bo_loc(db)
    assert d["bo_sot"] == 1, "vụ bộ lọc không nêu mà người vẫn lập phải được đếm là BỎ SÓT"
    # Thêm đúng cái từ ấy vào danh sách: lần đo sau nó hết là bỏ sót.
    dat_tham_so(db, LK.THAM_SO_TU_DO, R.get_param_chu(db, LK.THAM_SO_TU_DO) + ",lam an nhu vay")
    db.commit()
    assert LK.do_bo_loc(db)["bo_sot"] == 0


def test_D_vu_khong_co_tin_nguon_duoc_dem_RIENG_khong_roi_khoi_mau_so(db):
    """Một vụ nổ trên báo không có tin nào trong hộp thư để đối chiếu. Để nó rơi khỏi mẫu số là
    cách làm tỷ lệ đẹp lên mà không ai nhận ra."""
    from app.services import pr_hoat_dong as PR
    PR.tao(db, {"loai": "khung_hoang", "tieu_de": "Báo Thanh Niên đăng bài", "la_khung_hoang": True}, "nv1")
    db.commit()
    d = LK.do_bo_loc(db)
    assert d["khong_co_tin_nguon"] == 1
    assert d["bo_sot"] == 0, "vụ không có tin nguồn bị đếm nhầm thành bỏ sót của bộ lọc"
    assert "khong_co_tin_nguon" in d["ghi_chu"] or d["ghi_chu"], "phép đo không nói ra phần nó không đo được"


def test_D_diem_luu_lai_la_diem_cham_LUC_BAM(db):
    """Tham số có thể đổi giữa lúc màn hình tải và lúc người bấm. Con số được lưu phải là con số
    bộ lọc thật sự nói ra lúc ấy, nếu không thì phép đo đo một bộ lọc không còn tồn tại."""
    c = hoi_thoai(db)
    m = tin(db, c, "món này dở tệ")
    db.commit()
    dat_tham_so(db, LK.THAM_SO_TU_DO, R.get_param_chu(db, LK.THAM_SO_TU_DO) + ",do te")
    db.commit()
    LK.bo_qua(db, m.id, "nv1", "khách chê món ăn thôi")
    x = db.execute(select(HopThuXuLy).where(HopThuXuLy.message_id == m.id)).scalars().first()
    assert x.diem_luc_do == LK.DIEM_TU_DO and x.co_tu_do is True


# =============================================================================================
# E. BỐN THAM SỐ PHẢI CÓ CHỮ KÝ, VÀ MÃ PHẢI ĐỌC TỪ CHÚNG
# =============================================================================================
def test_E_bon_tham_so_deu_co_trong_so_luat_da_ky():
    ten = {p[0] for p in R.DEFAULT_PARAMS}
    for t in (LK.THAM_SO_TU_DO, LK.THAM_SO_NGUONG, LK.THAM_SO_CUM_PHUT, LK.THAM_SO_CUM_SO_TIN):
        assert t in ten, f"{t} chưa được khai trong sổ luật – một luật không ai ký"


def test_E_moi_tham_so_deu_ghi_AI_KY():
    ky = {p[0]: p[4] for p in R.DEFAULT_PARAMS if len(p) > 4}
    for t in (LK.THAM_SO_TU_DO, LK.THAM_SO_NGUONG, LK.THAM_SO_CUM_PHUT, LK.THAM_SO_CUM_SO_TIN):
        assert ky.get(t, "").strip(), f"{t} không ghi ai chốt – sáu tháng sau không tra được"


def test_E_nguong_doc_song_khong_nho_cung(db):
    c = hoi_thoai(db)
    for i in range(6):
        tin(db, c, f"alo {i}", luc=BAY_GIO - timedelta(minutes=i))   # chỉ có DỐC = 1 điểm
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 0
    dat_tham_so(db, LK.THAM_SO_NGUONG, "1")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 6


def test_E_so_tin_cua_mot_cum_doc_song(db):
    c = hoi_thoai(db)
    for i in range(3):
        tin(db, c, f"alo {i}", luc=BAY_GIO - timedelta(minutes=i))
    db.commit()
    assert LK.canh_bao(db, ngay=7, nguong_tuy=1, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 0
    dat_tham_so(db, LK.THAM_SO_CUM_SO_TIN, "3")
    db.commit()
    assert LK.canh_bao(db, ngay=7, nguong_tuy=1, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 3


def test_E_cham_tran_thi_NOI_RA_chu_khong_im_lang(db, monkeypatch):
    """Một hàng đợi thiếu dòng mà im lặng tệ hơn hẳn một hàng đợi chậm.

    Hạ trần xuống 3 rồi nạp 5 tin: kết quả phải mang cờ `cat_bot` để màn hình nói với người trực
    rằng họ đang nhìn một phần, chứ không để họ tưởng đã nhìn hết.
    """
    monkeypatch.setattr(LK, "TRAN_DONG", 3)
    c = hoi_thoai(db)
    for i in range(5):
        tin(db, c, f"lừa đảo lần {i}", luc=BAY_GIO - timedelta(minutes=i))
    db.commit()
    kq = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)
    assert kq["cat_bot"] is True, "cắt bớt dòng mà không nói ra"
    assert len(kq["rows"]) == 3


def test_E_khong_cham_tran_thi_khong_bao_dong_gia(db):
    c = hoi_thoai(db)
    tin(db, c, "lừa đảo")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["cat_bot"] is False


def test_E_man_hinh_phai_hien_co_cat_bot():
    """Cờ `cat_bot` chỉ có nghĩa nếu màn hình đọc nó. Một cờ không ai hiện là một cờ không tồn tại."""
    src = pathlib.Path(LK.__file__).resolve().parents[3].joinpath(
        "web", "app", "marketing", "page.tsx").read_text(encoding="utf-8")
    assert "cat_bot" in src, "màn hình Marketing không hiện cảnh báo cắt bớt dòng của hàng đợi"
