# -*- coding: utf-8 -*-
"""TR-16 · ĐƯỜNG THỜI GIAN TRONG THÂN NGÀY, VÀ BA BỮA LUÔN HIỆN ĐỦ.

Chủ tịch xem màn khách trên bản chạy và nói thẳng: lịch trình chưa đẹp. Soi lại thì đúng —
TR-14 tách được ngày ra khỏi bài web, có bữa ăn, có nơi nghỉ, dải «Đêm 1» hiện; nhưng THÂN mỗi
ngày vẫn là MỘT KHỐI CHỮ XÁM LIỀN hơn hai mươi dòng. Bài gốc trên web gói cả ngày vào một dòng
duy nhất, không ký tự xuống dòng nào, nên sau khi cắt tiêu đề ra thì phần còn lại đổ nguyên một
cục. Bản xem thử Chủ tịch duyệt có đường thời gian với viên giờ; bản chạy không có.

Mà chính khối chữ ấy CÓ SẴN mốc giờ bên trong, đây là chữ thật của HC001:

    «07h15: Xe và hướng dẫn viên Vietourist đón Quý khách tại điểm hẹn… Trưa: Quý khách dùng
     cơm tại nhà hàng địa phương… Chiều: Tham quan Khu du lịch Tanyoli… Tối: Đoàn dùng bữa…»

Chỉ là chưa ai cắt. Vòng này cắt, và cắt ở MÁY CHỦ — cùng chỗ với các bộ đọc khác, nơi đã có
phép thử trên chữ thật — chứ không cắt ở giao diện.

BA BỮA LUÔN HIỆN ĐỦ (Chủ tịch chốt 14-11-2026, học cách Tours4Fun ghi «B: Included, L: Excluded,
D: Excluded»). Chỉ in bữa CÓ thì khách không biết bữa còn lại phải tự trả — HC001 ghi rõ «Ăn
sáng ngày 01» nằm trong mục KHÔNG bao gồm, và đó đúng là chỗ sinh khiếu nại sau khi đoàn đã đi.
"""
import re
from pathlib import Path

from app.services import tour_online as T

GOC = Path(__file__).resolve().parents[2]
TEP_GD = GOC / "web" / "components" / "cong" / "ToursAgoda.tsx"

# chữ thật, chép từ bài HC001 trên vietourist.com.vn
NGAY1 = ("07h15: Xe và hướng dẫn viên Vietourist đón Quý khách tại điểm hẹn. Đoàn khởi hành "
         "theo tuyến cao tốc Sài Gòn – Dầu Giây – Phan Thiết – Vĩnh Hảo. Trưa: Quý khách dùng "
         "cơm tại nhà hàng địa phương. Nhận phòng tại Hòn Cò Resort. Tự do tắm biển. Chiều: "
         "Tham quan Khu du lịch Tanyoli. Tối: Đoàn dùng bữa tối tại nhà hàng.")
NGAY2 = ("Sáng: Dùng điểm tâm tại khách sạn, trả phòng. Trưa: cơm tại Phan Thiết. "
         "Chiều: về đến TP.HCM, kết thúc chuyến đi.")


# ══ 1 · CẮT ĐÚNG MỐC GIỜ CÓ THẬT ════════════════════════════════════════════════════════════

def test_tr16_1_ca_that_hc001_ngay_1_cat_thanh_bon_doan():
    ds = T.tach_doan(NGAY1)
    assert [d["luc"] for d in ds] == ["07h15", "Trưa", "Chiều", "Tối"]
    assert ds[0]["chu"].startswith("Xe và hướng dẫn viên")
    assert "Tanyoli" in ds[2]["chu"]


def test_tr16_2_ca_that_hc001_ngay_2():
    assert [d["luc"] for d in T.tach_doan(NGAY2)] == ["Sáng", "Trưa", "Chiều"]


def test_tr16_3_moc_gio_khong_con_lap_lai_trong_than():
    """Giờ đã thành viên riêng; để nguyên trong câu nữa là in hai lần cùng một thứ."""
    for d in T.tach_doan(NGAY1):
        assert not d["chu"].lower().startswith(d["luc"].lower())
        assert not re.match(r"^\s*[:.\-–—]", d["chu"])


# ══ 2 · KHI NÀO KHÔNG ĐƯỢC CẮT ══════════════════════════════════════════════════════════════

def test_tr16_4_duoi_hai_moc_thi_de_nguyen_khoi_chu():
    """Một đường thời gian chỉ có một chặng trông còn tệ hơn khối chữ ban đầu."""
    assert T.tach_doan("Sáng: Quý khách tự do nghỉ ngơi tại resort.") == []
    assert T.tach_doan("Đoàn tham quan Thiền viện Trúc Lâm rồi về khách sạn.") == []
    assert T.tach_doan("") == []


def test_tr16_5_chu_sang_trua_toi_giua_cau_khong_bi_cat():
    """«… nghỉ trưa tại resort» không phải mốc giờ. Mốc phải có dấu hai chấm theo sau."""
    t = "Đoàn ăn trưa tại nhà hàng rồi nghỉ trưa tại resort, buổi tối tự do."
    assert T.tach_doan(t) == []


# ══ 3 · ĐẮP VÀO TỪNG NGÀY ═══════════════════════════════════════════════════════════════════

def test_tr16_6_ngay_day_du_co_them_doan():
    ds = [{"ngay": 1, "tieu_de": "TP.HCM - HÒN CÒ RESORT (Ăn trưa,tối)", "noi_dung": NGAY1},
          {"ngay": 2, "tieu_de": "CÀ NÁ - TP.HCM (Ăn sáng, trưa)", "noi_dung": NGAY2}]
    ra = T.ngay_day_du(ds)
    assert len(ra[0]["doan"]) == 4 and len(ra[1]["doan"]) == 3
    # những thứ TR-14 làm phải còn nguyên
    assert ra[0]["bua"] == ["trưa", "tối"] and ra[0]["khach_san"] == "HÒN CÒ RESORT"
    assert ra[1]["khach_san"] == ""


def test_tr16_7_ngay_khong_cat_duoc_van_giu_noi_dung_cu():
    ds = [{"ngay": 1, "tieu_de": "ĐÀ LẠT", "noi_dung": "Đoàn tham quan Thiền viện Trúc Lâm."}]
    ra = T.ngay_day_du(ds)
    assert ra[0]["doan"] == []
    assert ra[0]["noi_dung"] == "Đoàn tham quan Thiền viện Trúc Lâm.", "không được làm mất chữ"


# ══ 4 · GIAO DIỆN ═══════════════════════════════════════════════════════════════════════════

def gd() -> str:
    return TEP_GD.read_text(encoding="utf-8")


def test_tr16_8_giao_dien_dung_duong_thoi_gian_khi_co_doan():
    s = gd()
    assert 'className="tra-moc"' in s and 'className="tra-gio"' in s
    assert "n.doan?.length ?" in s, "có đoạn thì vẽ đường thời gian, không có thì giữ khối chữ"
    assert "n.noi_dung ? <p>{n.noi_dung}</p>" in s, "đường lui phải còn, nếu không ngày nào không cắt được sẽ trắng"


def test_tr16_9_ba_bua_luon_hien_du_ba():
    s = gd()
    assert 'const BA_BUA: [string, string][] = [["sáng", "Sáng"], ["trưa", "Trưa"], ["tối", "Tối"]];' in s
    assert "BA_BUA.map" in s
    assert '{co ? "✓" : "✕"}' in s, "bữa không bao gồm cũng phải hiện, kèm dấu ✕"


def test_tr16_10_khoi_chan_ngay_khong_con_bi_an_di():
    """Trước đây cả khối «Nghỉ đêm / Bữa ăn» chỉ hiện khi CÓ dữ liệu — tức ngày nào thiếu thì
    khách không thấy gì, không phân biệt được «không bao gồm» với «chưa cập nhật»."""
    s = gd()
    assert '{(n.khach_san || n.bua?.length > 0) && <div className="tra-dfoot">' not in s
    assert '<div className="tra-dfoot">' in s


def test_tr16_11_khong_dong_vao_thu_cac_vong_truoc_da_lam_dung():
    s = gd()
    for can in ["#vtd-access .tra a.ksv-btn", "#vtd-access .ksv.tra input[type=checkbox]",
                "tra-dnoi", "onClick={moDat}", 'className="tra-days"']:
        assert can in s, f"vòng này làm mất {can}"
    assert s.count("<h1") == 2 and s.count('<main className="ksv tra">') == 2
