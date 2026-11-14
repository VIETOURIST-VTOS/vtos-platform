# -*- coding: utf-8 -*-
"""TR-18 · HAI VÒNG GỌI MÁY CHỦ KHÔNG AI CẦN, VÀ MỘT CỬA TR-17 BỎ SÓT.

TR-17 lên bản chạy và ăn thật — đo lại bằng cách gọi lặp, đọc «x-vercel-cache»:

    san-pham/6613     1.481 ms  ->  59–70 ms   HIT
    lich-trinh/1980     545 ms  ->  63–82 ms   HIT
    tim               1.791 ms  ->  81–98 ms   HIT
    lịch trình hiện ra 3.241 ms ->  1.012 ms

Dọn xong lớp dưới thì lộ ra hai thứ trước đây bị che vì mọi cửa đều chậm như nhau.

  (A) CỬA «tim» CHẠY TRÊN TRANG CHI TIẾT, 2.611 ms, VÀ KHÔNG AI DÙNG.
      Khách mở thẳng một tour thì màn chi tiết không hiện danh sách ở đâu cả — đếm trên bản
      chạy: ĐÚNG 0 đường dẫn sang tour khác, không có mục «tour tương tự». Nó chậm vì trang
      gọi với bộ lọc riêng nên là một địa chỉ khác, chưa ấm ở biên. Bỏ hẳn, không cần đệm.
      Bấm quay lại vẫn đủ danh sách: veDs() đã sẵn «if (!ds) tim()» từ trước.

  (B) VÒNG GỌI LẠI LỊCH TRÌNH SAU KHI ĐÃ CÓ LỊCH TRÌNH.
      chi_tiet() đã trả lich_trinh của chuyến đầu ngay trong cùng một lần. Xong trang đặt
      setChon(chuyến đầu), và useEffect([chon]) gọi lich-trinh/{chon} — thường là gọi lại
      đúng bản vừa nhận. Mà chỉ nhánh «chuyen» mới đổi theo chuyến; bốn nhánh còn lại (web,
      san_pham, web_gioi_thieu_ngay, van_ban) đọc từ sản phẩm nên MỌI chuyến ra một kết quả.
      HC001 là nhánh «web_gioi_thieu_ngay» — vòng 545 ms ấy xưa nay không đổi được gì.

  (C) TR-17 BỎ SÓT CỬA ĐÁNH GIÁ. Em viết TR-17 trên một bản cong_mo.py CŨ (7.852 byte) trong
      khi bản trên main là 14.035 byte — bản vá vẫn ráp sạch vì ba khối sửa không chạm chỗ
      khác, nên không ai thấy. Hậu quả: /tour-online/san-pham/{pid}/danh-gia không được dán
      nhãn, đo được 1.516 ms lúc tải trang và 509 ms khi gọi lại, thành thứ chậm thứ hai.
      Bài học: lấy tệp gốc từ origin/main TRƯỚC KHI viết, không dùng bản trong cây làm việc.
"""
import ast
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
TEP_CUA = GOC / "backend" / "app" / "api" / "v1" / "cong_mo.py"
TEP_DV = GOC / "backend" / "app" / "services" / "tour_online.py"
TEP_GD = GOC / "web" / "components" / "cong" / "ToursAgoda.tsx"


def than(s: str, ten: str) -> str:
    i = s.index(f"def {ten}(")
    j = s.find("\ndef ", i + 1)
    k = s.find("\n@router", i + 1)
    return s[i:min(x for x in (j, k, len(s)) if x > 0)]


# ══ C · CỬA ĐÁNH GIÁ ĐƯỢC DÁN NHÃN ══════════════════════════════════════════════════════════

def test_tr18_1_cua_danh_gia_duoc_dan_nhan():
    s = TEP_CUA.read_text(encoding="utf-8")
    assert "_dem(resp, DEM_LICH_TRINH)" in than(s, "tr_danh_gia")


def test_tr18_2_moi_cua_chi_doc_cua_tour_deu_da_co_nhan():
    """Phép thử này mới là cái canh lỗi «đọc nhầm bản cũ»: nó đi hết các cửa tour-online và
    đòi mỗi cửa hoặc có nhãn, hoặc nằm trong danh sách cấm đệm. Thêm cửa mới mà quên là đỏ.

    Nó tìm ra ngay cửa ảnh `/tour-online/anh/{aid}/{co}` — cửa ấy KHÔNG sót, nó tự dựng sẵn
    «Cache-Control: public, max-age=86400» trong chính bản trả về ảnh từ TR-8, nên chấp nhận
    cả hai lối khai: gọi _dem, hoặc tự đặt nhãn có hạn giữ."""
    s = TEP_CUA.read_text(encoding="utf-8")
    cam = re.search(r"KHONG_DEM\s*=\s*\(([^)]*)\)", s, re.S).group(1)
    thieu = []
    for duong, ten in re.findall(r'@router\.get\("(/tour-online[^"]*)"\)\s*\ndef (\w+)\(', s):
        if duong in cam:
            continue
        t = than(s, ten)
        tu_dat = re.search(r'"Cache-Control":\s*"[^"]*(?:s-)?max-age=[1-9]', t)
        if "_dem(resp" not in t and not tu_dat:
            thieu.append(f"{duong} ({ten})")
    assert not thieu, "cửa chỉ đọc chưa dán nhãn đệm, cũng không nằm trong KHONG_DEM: " + ", ".join(thieu)


# ══ B · MÁY CHỦ NÓI RÕ LỊCH TRÌNH NÀY CỦA CHUYẾN NÀO ════════════════════════════════════════

def test_tr18_3_moi_nhanh_lich_trinh_deu_khai_theo_chuyen():
    """Thiếu khoá ở MỘT nhánh thôi là trang khách đọc ra «không rõ» rồi gọi lại — mất đúng cái
    vòng mà vòng này vừa bỏ."""
    s = TEP_DV.read_text(encoding="utf-8")
    t = than(s, "lich_trinh")
    nhanh = re.findall(r'"nguon":\s*"(\w+)"', t)
    assert set(nhanh) == {"chuyen", "web", "san_pham", "web_gioi_thieu_ngay", "web_gioi_thieu", "van_ban"}, nhanh
    assert t.count('"theo_chuyen"') == len(nhanh), "có nhánh trả về mà quên khoá theo_chuyen"
    assert '"nguon": "chuyen", "theo_chuyen": tour_id' in t, "nhánh chuyên phải khai đúng chuyến của nó"
    for n in ("web", "san_pham", "web_gioi_thieu_ngay", "web_gioi_thieu", "van_ban"):
        assert f'"nguon": "{n}", "theo_chuyen": None' in t, f"nhánh {n} không đổi theo chuyến nên phải là None"


def test_tr18_4_chi_tiet_tra_ve_danh_sach_chuyen_co_chuong_trinh_rieng():
    s = TEP_DV.read_text(encoding="utf-8")
    assert '"ct_rieng": chuyen_co_ct_rieng(db, [c["tour_id"] for c in chuyen])' in s


def test_tr18_5_hoi_mot_lan_cho_ca_danh_sach_khong_hoi_tung_chuyen():
    """Một tour có thể mở vài chục ngày khởi hành. Hỏi từng chuyến là đổi một vòng gọi mạng
    lấy vài chục vòng truy vấn — chữa chỗ này làm hỏng chỗ kia."""
    t = than(TEP_DV.read_text(encoding="utf-8"), "chuyen_co_ct_rieng")
    assert t.count("db.execute(") == 1, "phải đúng MỘT truy vấn cho cả danh sách"
    assert "tour_id.in_(ids)" in t
    assert "if not ids:" in t and "return []" in t, "danh sách rỗng thì đừng chạm vào kho dữ liệu"
    assert '((td or "") + (nd or "")).strip()' in t, \
        "chuyến có dòng chương trình nhưng rỗng chữ thì KHÔNG tính là có chương trình riêng"


def test_tr18_6_chay_that_chuyen_co_ct_rieng_tren_du_lieu_gia():
    """Gọi CHÍNH hàm ấy, không dựng lại phép lọc trong phép thử — dựng lại thì phép thử chỉ
    chứng minh chính nó đúng. Kho dữ liệu thay bằng một vật giả chỉ biết trả về mấy dòng."""
    from app.services.tour_online import chuyen_co_ct_rieng

    class KhoGia:
        def __init__(self, hang):
            self.hang, self.so_lan = hang, 0

        def execute(self, _cau):
            self.so_lan += 1
            return type("KQ", (), {"all": lambda _s: self.hang})()

    kho = KhoGia([(7, "NGÀY 1", ""), (7, "", "đi"), (9, "", ""), (9, "   ", "\n"), (11, None, "Về")])
    assert chuyen_co_ct_rieng(kho, [7, 9, 11]) == [7, 11], "chuyến 9 chỉ có dòng rỗng — không được tính"
    assert kho.so_lan == 1, "hỏi kho đúng một lần cho cả danh sách"

    rong = KhoGia([])
    assert chuyen_co_ct_rieng(rong, []) == [] and rong.so_lan == 0, "danh sách rỗng thì đừng chạm vào kho"
    assert chuyen_co_ct_rieng(rong, [None, 0]) == [] and rong.so_lan == 0


# ══ A + B · TRANG KHÁCH BỎ HAI VÒNG GỌI ═════════════════════════════════════════════════════

def gd() -> str:
    return TEP_GD.read_text(encoding="utf-8")


def test_tr18_7_mo_thang_mot_tour_thi_khong_tai_danh_sach():
    s = gd()
    assert "if (moId) moSp(moId); else tim();" in s
    assert "tim(); if (moId) moSp(moId);" not in s, "vẫn tải danh sách trước rồi mới mở tour"


def test_tr18_8_khoi_phuc_phien_cu_cung_khong_tai_danh_sach_thua():
    """Nhánh «vừa đăng nhập giữa chừng, trả lại chỗ cũ» cũng phải theo cùng một luật."""
    s = gd()
    assert "setQ(nho.q); tim(nho.q);" not in s, "nhánh khôi phục vẫn gọi tim() vô điều kiện"
    assert "if (nho.spId) { moSp(nho.spId).then(" in s


def test_tr18_9_duong_lui_quay_lai_danh_sach_con_nguyen():
    """Bỏ lượt tải sớm chỉ an toàn vì nút quay lại tự tải khi chưa có. Mất dòng này là khách
    bấm quay lại và thấy trang trắng."""
    assert "if (!ds) tim();" in gd()


def test_tr18_10_chi_goi_lai_lich_trinh_khi_that_su_doi():
    s = gd()
    assert "const can = (sp.ct_rieng || []).includes(chon) ? chon : null;" in s
    assert "if (can === ((lt && lt.theo_chuyen) ?? null)) return;" in s


def test_tr18_11_van_con_goi_lai_khi_chuyen_co_chuong_trinh_rieng():
    """Không được bỏ luôn vòng gọi: tour nào có soạn chương trình riêng cho từng ngày khởi
    hành thì đổi ngày VẪN phải lấy đúng chương trình của ngày ấy."""
    s = gd()
    i = s.index("const can = (sp.ct_rieng")
    khoi = s[i:i + 700]
    assert "goiCong(`/mo/tour-online/san-pham/${sp.id}/lich-trinh/${chon}`)" in khoi


# ══ KHÔNG LÀM HỎNG THỨ ĐANG CHẠY ════════════════════════════════════════════════════════════

def test_tr18_12_cac_vong_truoc_con_nguyen():
    s = gd()
    for can in ['className="tra-moc"', 'className="tra-gio"', "BA_BUA.map", "tra-dnoi",
                "#vtd-access .tra a.ksv-btn", "#vtd-access .ksv.tra input[type=checkbox]"]:
        assert can in s, f"vòng này làm mất {can}"
    assert s.count("<h1") == 2 and s.count('<main className="ksv tra">') == 2
    assert s.count("onClick={moDat}") == 1


def test_tr18_13_cua_tinh_tien_van_khong_duoc_dem():
    s = TEP_CUA.read_text(encoding="utf-8")
    assert "_dem(" not in than(s, "tr_tinh")
    assert "_dem(" not in than(s, "ttd_xem")
