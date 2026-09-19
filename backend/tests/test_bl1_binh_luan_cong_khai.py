# -*- coding: utf-8 -*-
"""BL-1 · Bình luận công khai Fanpage — luồng webhook KHÁC, bảng KHÁC, và một điểm cộng KHÁC.

Ba chỗ hỏng lặng mà tệp này gác:

  1. KHÔNG ĐĂNG KÝ TRƯỜNG `feed`. Hộp thư đang chạy tốt với trường `messages`, nên mọi thứ trông
     như đã nối xong — trong khi Fanpage vẫn nhận bình luận và VTOS không thấy dòng nào. Đây đúng
     là tình trạng trước 19/9/2026, và nó không phát ra một lỗi nào cả.

  2. ĐỔ BÌNH LUẬN VÀO HỘP THƯ cho tiện. `inbox.get_or_create` tạo một Lead cho mỗi hội thoại mới,
     nên mỗi người bình luận "đẹp quá" thành một lead giả, và TỶ LỆ CHỐT LEAD của Sales bị pha
     loãng bằng thứ không phải lead. Không ai phát hiện ra; người ta chỉ thấy "dạo này chốt kém".

  3. CHẤM CẢ BÌNH LUẬN CỦA CHÍNH PAGE. Mình trả lời một vụ khủng hoảng, câu trả lời mang đầy từ đỏ,
     và nó nhảy lên đầu hàng đợi như một vụ mới. Hàng đợi tự nuôi chính nó.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_bl1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_bl1.db", "test_bl1.db-journal"):
    if os.path.exists(f):
        os.remove(f)

import inspect  # noqa: E402
import pathlib  # noqa: E402
from datetime import date, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.core import Param  # noqa: E402
from app.models.crm import Conversation, Message  # noqa: E402
from app.models.marketing import FbBinhLuan, HopThuXuLy, PrHoatDong  # noqa: E402
from app.services import fb_binh_luan as BL  # noqa: E402
from app.services import inbox as IB  # noqa: E402
from app.services import loc_khung_hoang as LK  # noqa: E402
from app.services import rules as R  # noqa: E402

Base.metadata.create_all(engine)
BAY_GIO = datetime(2026, 9, 19, 12, 0, 0)
PAGE = "100011112222"


@pytest.fixture()
def db():
    s = SessionLocal()
    for M in (HopThuXuLy, PrHoatDong, FbBinhLuan, Message, Conversation, Param):
        s.query(M).delete()
    s.commit()
    R.clear_param_cache()
    yield s
    for M in (HopThuXuLy, PrHoatDong, FbBinhLuan, Message, Conversation, Param):
        s.query(M).delete()
    s.commit()
    R.clear_param_cache()
    s.close()


def dat_tham_so(db, key, value):
    db.add(Param(key=key, value=str(value), label=key, unit="", effective_from=date(2026, 9, 1),
                 source="test", status="active", signed_chutich=True, signed_tgd=True,
                 proposed_by="test"))
    db.commit()
    R.clear_param_cache()


def gt(cid="c1", msg="bình thường", tu="u1", ten="Khách A", verb="add", post="p1",
       luc=None, item="comment", **kw):
    v = {"item": item, "verb": verb, "comment_id": cid, "post_id": post,
         "from": {"id": tu, "name": ten}, "message": msg,
         "created_time": int((luc or BAY_GIO).timestamp())}
    v.update(kw)
    return v


def entry(*values):
    return {"id": PAGE, "changes": [{"field": "feed", "value": v} for v in values]}


def binh_luan(db, **kw):
    bl, _ = BL.ghi(db, gt(**kw), PAGE)
    db.commit()
    return bl


# =============================================================================================
# A. NHẬN
# =============================================================================================
def test_A_dang_ky_truong_feed_neu_khong_facebook_khong_bao_gio_gui():
    """Phép thử một dòng, và nó là dòng chặn đúng cái đã hỏng suốt thời gian qua.

    Trường `messages` và trường `feed` là hai đăng ký RỜI NHAU. Có cái này không tự có cái kia, và
    khi thiếu `feed` thì không có lỗi nào phát ra — Fanpage vẫn nhận bình luận, VTOS vẫn im.
    """
    assert "feed" in IB.FB_FIELDS.split(","), \
        "chưa đăng ký trường webhook `feed` – Facebook sẽ không bao giờ gửi bình luận sang"


def test_A_webhook_hop_thu_co_goi_sang_nhanh_binh_luan():
    """Đăng ký trường thôi chưa đủ: sự kiện về tới `entry[].changes[]` mà không ai đọc thì cũng thế."""
    src = inspect.getsource(IB.fb_webhook)
    assert "nhan_changes" in src, "webhook Facebook không đọc nhánh changes[] – bình luận về rồi rơi"


def test_A_mot_binh_luan_thanh_mot_dong(db):
    d = BL.nhan_changes(db, entry(gt(msg="Tour này thế nào ạ")))
    db.commit()
    assert d["moi"] == 1
    b = db.execute(select(FbBinhLuan)).scalars().one()
    assert b.noi_dung == "Tour này thế nào ạ" and b.post_id == "p1" and b.page_id == PAGE


def test_A_gui_lai_cung_su_kien_khong_sinh_dong_thu_hai(db):
    """Webhook của Facebook gửi lại là chuyện bình thường. Không có khoá chống trùng thì một bình
    luận thành ba dòng, và con số 'bao nhiêu bình luận đáng đọc' sai ngay."""
    BL.nhan_changes(db, entry(gt(cid="x9")))
    BL.nhan_changes(db, entry(gt(cid="x9")))
    db.commit()
    assert db.query(FbBinhLuan).count() == 1


def test_A_khong_phai_binh_luan_thi_khong_ghi_dong(db):
    d = BL.nhan_changes(db, entry(gt(item="reaction"), gt(item="post", cid="c2")))
    db.commit()
    assert db.query(FbBinhLuan).count() == 0 and d["bo_qua"] == 2


def test_A_truong_khac_feed_thi_bo_qua(db):
    e = {"id": PAGE, "changes": [{"field": "ratings", "value": gt()}]}
    BL.nhan_changes(db, e)
    db.commit()
    assert db.query(FbBinhLuan).count() == 0


def test_A_binh_luan_bi_XOA_thi_giu_lai_dong_va_giu_lai_chu(db):
    """Một bình luận bị xoá là bằng chứng nó đã TỪNG có, và nó thường bị xoá đúng vào lúc đáng giữ
    nhất — kể cả khi người xoá là người của mình.

    Facebook KHÔNG gửi kèm nội dung ở sự kiện remove, nên nếu đè theo payload thì chữ biến mất.
    """
    binh_luan(db, cid="k1", msg="các anh lừa đảo")
    BL.nhan_changes(db, entry({"item": "comment", "verb": "remove", "comment_id": "k1",
                               "from": {"id": "u1"}, "post_id": "p1"}))
    db.commit()
    b = db.execute(select(FbBinhLuan).where(FbBinhLuan.comment_id == "k1")).scalars().one()
    assert b.da_xoa is True
    assert b.noi_dung == "các anh lừa đảo", "xoá xong mất luôn chữ – mất đúng thứ cần giữ"


def test_A_xoa_mot_binh_luan_chua_tung_thay_van_ghi_lai_dau_vet(db):
    """Sự kiện `add` có thể rớt (webhook lỗi, máy chủ đang khởi động lại). Biết rằng ĐÃ CÓ một bình
    luận bị gỡ vẫn hơn không biết gì."""
    BL.nhan_changes(db, entry({"item": "comment", "verb": "remove", "comment_id": "z9",
                               "from": {"id": "u7"}, "post_id": "p1"}))
    db.commit()
    b = db.execute(select(FbBinhLuan).where(FbBinhLuan.comment_id == "z9")).scalars().one()
    assert b.da_xoa is True and b.noi_dung == ""


def test_A_sua_binh_luan_thi_GIU_LAI_ban_cu(db):
    """Người ta sửa một bình luận gắt thành một bình luận nhẹ rồi bảo 'tôi có nói gì đâu'. Đè mất
    bản cũ là mất đúng chỗ ấy."""
    binh_luan(db, cid="s1", msg="các anh lừa đảo")
    BL.nhan_changes(db, entry(gt(cid="s1", verb="edited", msg="mình hỏi chút thôi")))
    db.commit()
    b = db.execute(select(FbBinhLuan).where(FbBinhLuan.comment_id == "s1")).scalars().one()
    assert "lừa đảo" in b.noi_dung and "mình hỏi chút thôi" in b.noi_dung and b.da_sua is True


def test_A_binh_luan_cua_chinh_PAGE_duoc_danh_dau(db):
    b = binh_luan(db, cid="pg1", tu=PAGE, ten="Vietourist", msg="Dạ công ty em xin lỗi anh ạ")
    assert b.la_cua_page is True


def test_A_gio_doc_duoc_ca_epoch_lan_ISO_va_rac_thi_khong_bo_dong(db):
    BL.ghi(db, {"item": "comment", "comment_id": "g1", "from": {"id": "u1"},
                "created_time": "2026-09-19T08:30:00Z", "message": "a"}, PAGE)
    BL.ghi(db, {"item": "comment", "comment_id": "g2", "from": {"id": "u1"},
                "created_time": "khong-phai-ngay", "message": "b"}, PAGE)
    db.commit()
    assert db.query(FbBinhLuan).count() == 2, \
        "một định dạng ngày lạ làm mất hẳn một bình luận – nhà cung cấp đổi định dạng là mất dòng"


# =============================================================================================
# B. VÀO HÀNG ĐỢI
# =============================================================================================
def test_B_cong_khai_duoc_cong_diem(db):
    ds = ["lua dao"]
    rieng = LK.cham_diem("các anh lừa đảo", ds)[0]
    cong_khai = LK.cham_diem("các anh lừa đảo", ds, cong_khai=True)[0]
    assert cong_khai == rieng + LK.DIEM_CONG_KHAI, \
        "cùng một câu, viết công khai và viết riêng, đang được coi là ngang nhau"


def test_B_binh_luan_dung_TREN_tin_nhan_cung_noi_dung(db):
    c = Conversation(channel="facebook", external_id="e1", customer_name="Khách A")
    db.add(c)
    db.flush()
    db.add(Message(conversation_id=c.id, direction="in", text="các anh lừa đảo", at=BAY_GIO))
    binh_luan(db, cid="b1", msg="các anh lừa đảo")
    db.commit()
    rows = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["rows"]
    assert len(rows) == 2
    assert rows[0]["nguon"] == "binh_luan", "bình luận công khai phải đứng trên tin nhắn riêng"


def test_B_binh_luan_cua_PAGE_khong_vao_hang_doi(db):
    binh_luan(db, cid="pg2", tu=PAGE, msg="Dạ công ty em không lừa đảo đâu ạ")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 0, \
        "câu trả lời của chính mình đang nhảy lên hàng đợi – hàng đợi tự nuôi chính nó"


def test_B_binh_luan_rong_chu_khong_vao_hang_doi(db):
    binh_luan(db, cid="r1", msg="")
    db.commit()
    assert LK.canh_bao(db, ngay=7, nguong_tuy=0, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 0


def test_B_doc_cua_binh_luan_dem_theo_BAI_DANG_khong_theo_nguoi(db):
    """Một vụ thật trên Fanpage là NHIỀU NGƯỜI cùng đổ vào MỘT BÀI, không phải một người nói nhiều
    lần. Khác hẳn hình của tin nhắn riêng — nên hai chỗ đếm hai kiểu, cố ý."""
    for i in range(6):
        binh_luan(db, cid=f"d{i}", tu=f"u{i}", post="pHot", msg=f"sao vậy {i}",
                  luc=BAY_GIO - timedelta(minutes=i))
    binh_luan(db, cid="le1", tu="uX", post="pYen", msg="đẹp quá")
    db.commit()
    # Ngưỡng 2: công khai (+1) một mình chưa đủ, phải cộng thêm DỐC (+1). Bài đang dốc thì đủ,
    # bài yên thì không — đó đúng là phép phân biệt cần đo ở đây.
    rows = LK.canh_bao(db, ngay=7, nguong_tuy=2, bay_gio=BAY_GIO)["rows"]
    assert len(rows) == 6, f"phải đúng 6 dòng của bài đang dốc, đang có {len(rows)}"
    assert all("đẹp quá" not in (r.get("trich") or "") for r in rows), \
        "bình luận lẻ ở một bài yên cũng được tính là dốc"


def test_B_binh_luan_DA_XOA_van_nam_trong_hang_doi_co_dau(db):
    binh_luan(db, cid="x1", msg="các anh lừa đảo")
    BL.nhan_changes(db, entry({"item": "comment", "verb": "remove", "comment_id": "x1",
                               "from": {"id": "u1"}, "post_id": "p1"}))
    db.commit()
    rows = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["rows"]
    assert len(rows) == 1 and rows[0]["da_xoa"] is True, \
        "xoá bình luận là cách rẻ nhất để một vụ biến mất khỏi hàng đợi"


def test_B_dem_rieng_so_dong_cong_khai(db):
    binh_luan(db, cid="ck1", msg="các anh lừa đảo")
    db.commit()
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cong_khai"] == 1


# =============================================================================================
# C. KẾT LUẬN CỦA NGƯỜI
# =============================================================================================
def test_C_bo_qua_mot_binh_luan_ghi_dung_nguon(db):
    b = binh_luan(db, cid="q1", msg="các anh lừa đảo")
    LK.bo_qua(db, b.id, "nv1", "khách nhầm công ty khác", nguon="binh_luan")
    x = db.execute(select(HopThuXuLy)).scalars().one()
    assert x.nguon == "binh_luan" and x.binh_luan_id == b.id and x.message_id is None
    assert LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["dem"]["cho_xem"] == 0


def test_C_lap_PR_tu_binh_luan_giu_duong_ve_va_ghi_dung_noi_dang(db):
    b = binh_luan(db, cid="q2", msg="các anh lừa đảo", permalink_url="https://fb.com/x")
    kq = LK.lap_pr(db, b.id, "nv1", {"la_khung_hoang": True}, nguon="binh_luan")
    h = db.get(PrHoatDong, kq["pr_id"])
    assert h.nguon_binh_luan_id == b.id and h.nguon_message_id is None
    assert h.noi_dang == "Bình luận công khai Fanpage"
    assert h.link == "https://fb.com/x", "mất đường dẫn công khai thì không ai mở lại được vụ ấy"


def test_C_mot_binh_luan_khong_lap_hai_dong_PR(db):
    b = binh_luan(db, cid="q3", msg="các anh lừa đảo")
    LK.lap_pr(db, b.id, "nv1", {"la_khung_hoang": True}, nguon="binh_luan")
    with pytest.raises(ValueError):
        LK.lap_pr(db, b.id, "nv2", {"la_khung_hoang": True}, nguon="binh_luan")
    assert db.query(PrHoatDong).count() == 1


def test_C_la_khung_hoang_van_doc_tu_o_NGUOI_tich(db):
    b1 = binh_luan(db, cid="w1", msg="các anh lừa đảo")
    b2 = binh_luan(db, cid="w2", msg="các anh lừa đảo thật đấy")
    a = LK.lap_pr(db, b1.id, "nv1", {"la_khung_hoang": True}, nguon="binh_luan")
    c = LK.lap_pr(db, b2.id, "nv1", {"la_khung_hoang": False}, nguon="binh_luan")
    assert a["la_khung_hoang"] is True and c["la_khung_hoang"] is False


def test_C_do_bo_loc_dem_duoc_bo_sot_tu_nguon_binh_luan(db):
    b = binh_luan(db, cid="s9", msg="các anh làm ăn như vậy là không được")   # dưới ngưỡng
    LK.lap_pr(db, b.id, "nv1", {"la_khung_hoang": True}, nguon="binh_luan")
    assert LK.do_bo_loc(db)["bo_sot"] == 1
    dat_tham_so(db, LK.THAM_SO_TU_DO, R.get_param_chu(db, LK.THAM_SO_TU_DO) + ",lam an nhu vay")
    assert LK.do_bo_loc(db)["bo_sot"] == 0


# =============================================================================================
# D. NHỮNG CỬA CỐ Ý KHÔNG MỞ
# =============================================================================================
def test_D_khong_dung_nut_AN_binh_luan():
    """Ẩn một bình luận chê là cách nhanh nhất biến một khách bực thành bài 'Vietourist xoá bình
    luận của tôi' — thứ lan xa hơn hẳn bình luận gốc. Công cụ nào dễ bấm thì sẽ được bấm lúc 11 giờ
    đêm bởi người đang hoảng."""
    api = pathlib.Path(BL.__file__).resolve().parents[1].joinpath(
        "api", "v1", "marketing.py").read_text(encoding="utf-8")
    for xau in ("/an", "hide", "/xoa-binh-luan"):
        assert xau not in api, f"có cửa {xau!r} cho bình luận – xem lý do ở đầu services/fb_binh_luan.py"


def test_D_tep_binh_luan_khong_gui_gi_ra_ngoai():
    """Trả lời công khai là PHÁT NGÔN, và phát ngôn đã có một cửa với một vai đã ký (P.TGĐ
    Marketing). Mở cửa thứ hai ở đây là đi vòng qua chữ ký ấy."""
    src = pathlib.Path(BL.__file__).read_text(encoding="utf-8")
    for xau in ("urllib", "requests", "_graph", "access_token"):
        assert xau not in src.replace("`" + xau + "`", ""), \
            f"tệp nhận bình luận đang gọi ra ngoài ({xau}) – nó chỉ được NHẬN"


def test_B_page_tra_loi_nhieu_khong_duoc_day_binh_luan_that_ra_khoi_cua_so(db, monkeypatch):
    """Bỏ phép loại bình luận của Page ở CỬA SỔ ĐỌC thì phép chấm vẫn loại đúng — nên nhìn qua
    tưởng thừa. Nó không thừa: cửa sổ có TRẦN, và bình luận của chính mình sẽ ăn hết trần rồi đẩy
    bình luận thật của khách ra ngoài. Một Page trả lời chăm chỉ tự làm mình mù.

    Bẻ mã 19/9/2026 (N11) thoát ra ở đúng khe này.
    """
    monkeypatch.setattr(LK, "TRAN_DONG", 3)
    for i in range(5):
        binh_luan(db, cid=f"pg{i}", tu=PAGE, msg=f"Dạ công ty em ghi nhận ạ {i}",
                  luc=BAY_GIO - timedelta(minutes=i))
    binh_luan(db, cid="that", tu="uKhach", msg="các anh lừa đảo",
              luc=BAY_GIO - timedelta(minutes=30))
    db.commit()
    rows = LK.canh_bao(db, ngay=7, bay_gio=BAY_GIO)["rows"]
    assert len(rows) == 1 and "lừa đảo" in rows[0]["trich"], \
        "bình luận thật bị chính câu trả lời của Page đẩy ra khỏi cửa sổ đọc"


def test_C_doi_ket_luan_thi_SUA_dong_cu_chu_khong_sinh_dong_thu_hai(db):
    """Người trực bỏ qua rồi nghĩ lại và lập dòng PR — chuyện thường. Phải SỬA bản ghi cũ.

    Sinh thêm một dòng thứ hai thì phép đo bộ lọc đếm cùng một việc hai lần: một lần vào "báo nhầm",
    một lần vào "bắt đúng". Bẻ mã 19/9/2026 (N17) thoát ra ở đúng khe này.
    """
    b = binh_luan(db, cid="đ1", msg="các anh lừa đảo")
    LK.bo_qua(db, b.id, "nv1", "tưởng khách nhầm", nguon="binh_luan")
    LK.lap_pr(db, b.id, "nv1", {"la_khung_hoang": True}, nguon="binh_luan")
    assert db.query(HopThuXuLy).count() == 1, "đổi kết luận đang sinh ra một dòng thứ hai"
    x = db.execute(select(HopThuXuLy)).scalars().one()
    assert x.ket_luan == "lap_pr" and x.binh_luan_id == b.id
    d = LK.do_bo_loc(db)
    assert d["bat_dung"] == 1 and d["bao_nham"] == 0, \
        "cùng một việc đang được đếm cả ở bắt đúng lẫn báo nhầm"


def test_D_man_hinh_phai_phan_biet_CONG_KHAI_voi_TIN_RIENG():
    """Một bình luận công khai và một tin nhắn riêng nằm chung một bảng là đúng — người trực chỉ có
    một buổi sáng. Nhưng nếu nhìn vào không phân biệt được cái nào là cái nào thì việc gộp bảng trở
    thành việc giấu mất cái khác biệt quyết định mức độ khẩn.
    """
    src = pathlib.Path(BL.__file__).resolve().parents[3].joinpath(
        "web", "app", "marketing", "page.tsx").read_text(encoding="utf-8")
    assert 'r.nguon === "binh_luan"' in src, "màn hình không phân biệt bình luận công khai với tin riêng"
    assert "công khai" in src, "không có nhãn nào nói dòng này là công khai"
    assert "r.da_xoa" in src, "bình luận đã bị gỡ hiện y như bình luận còn nguyên"
