# -*- coding: utf-8 -*-
"""TR-20 · BA BỮA LÊN ĐẦU NGÀY, THEO BA MÀU LOGO — VÀ HAI CHỖ TƯƠNG PHẢN TR-16 LÀM SAI.

Chủ tịch chọn: giữ cả hai chỗ, nhưng chip trên đầu ngày đổi thành ba bữa ✓/✕. Lý do thực tế:
đầu ngày là chỗ DUY NHẤT khách thấy khi ngày còn gập, mà trước đây nó chỉ in bữa CÓ — nên
chưa mở ngày ra thì không thể biết bữa còn lại phải tự trả.

BA MÀU LOGO (Chủ tịch chốt 14-11-2026). Không ước bằng mắt: đọc thẳng tệp logo đang chạy
trên cổng, khoachu-holdings-nen-trong.svg, trong đó đúng ba màu —

    navy sáng  #5A9BD4   màu chính
    hồng       #FF6F96   cảnh báo, thay đỏ
    xanh lá    #5FAE66   điểm nhấn

Nhưng #5FAE66 làm CHỮ chỉ được 2,72:1 trên nền trắng, không đọc được. Nên giữ đúng sắc xanh
ấy rồi pha ba độ — trắng 90% ra nền viên, trắng 70% ra viền, đen 42% ra chữ. Cùng một màu
logo, ba độ đậm, và chữ đạt 6,23:1 trên nền của chính nó.

BỮA KHÔNG BAO GỒM GIỮ MÀU XÁM, cố ý: nó là một sự VẮNG MẶT, không phải cảnh báo. Đem hồng
logo dùng cho mọi thứ «không có» là làm nhạt chính tín hiệu cảnh báo khi cần nó thật.

HAI CHỖ TR-16 LÀM SAI, tìm ra lúc dựng bản xem thử và đo lại bằng số:
    · viên «bữa KHÔNG bao gồm» ở chân ngày: #8A8F96 trên #F4F5F7 = 2,98:1 — dưới 4,5:1. Tức
      chính cái dấu ✕ đặt ra để khách khỏi hiểu lầm lại là chữ khó đọc nhất trên màn.
    · xanh cũ #1C6B4A không phải màu logo, đổi sang #37653B.

ĐỘ ƯU TIÊN CỐ Ý LỚN HƠN HẲN CHỨ KHÔNG HOÀ — bài học TR-15b: hoà điểm thì phải trông vào thứ
tự dòng, mà thứ tự dòng đổi lúc nào không ai biết khi hai tệp kiểu được nối lại.
"""
import re
from pathlib import Path

TEP = Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "ToursAgoda.tsx"

LUC_CHU, LUC_NEN, LUC_VIEN = "#2f7d3b", "#ecf7ee", "#a7d2ab"   # đúng bộ của làn R5 (R5-22)
XAM_CHU, XAM_NEN = "#5f6b77", "#f4f5f7"


def doc() -> str:
    return TEP.read_text(encoding="utf-8")


def luat(pc: str) -> str:
    s = doc()
    i = s.index(pc + "{")
    return s[i:s.index("}", i)]


def diem(pc: str) -> tuple[int, int, int]:
    """Độ ưu tiên: (số ID, số lớp/thuộc tính, số thẻ)."""
    a = len(re.findall(r"#[\w-]+", pc))
    b = len(re.findall(r"\.[\w-]+", pc)) + len(re.findall(r"\[[^\]]+\]", pc))
    c = len(re.findall(r"(?:^|[\s>+~])([a-z][\w-]*)", pc))
    return (a, b, c)


# ══ 1 · ĐẦU NGÀY HIỆN ĐỦ BA BỮA ═════════════════════════════════════════════════════════════

def test_tr20_1_dau_ngay_duyet_het_ba_bua_khong_chi_bua_co():
    s = doc()
    assert '<span className="tra-chips2">{BA_BUA.map(([ma, ten]) => {' in s
    assert 'className={co ? "b co" : "b"}' in s
    assert '{co ? "✓" : "✕"}' in s


def test_tr20_2_khoi_chip_khong_con_bi_an_khi_thieu_du_lieu():
    """Trước đây cả cụm chip chỉ hiện khi CÓ bữa hoặc CÓ nơi nghỉ — ngày thiếu dữ liệu thì
    khách không thấy gì, không phân biệt được «không bao gồm» với «chưa cập nhật»."""
    s = doc()
    assert "{(n.bua?.length > 0 || n.khach_san) && <span className=\"tra-chips2\">" not in s


def test_tr20_3_chip_noi_nghi_van_con():
    assert "{n.khach_san && <em>Nghỉ: {n.khach_san}</em>}" in doc()


def test_tr20_4_bo_hang_khong_ai_goi_nua():
    s = doc()
    assert "const BUA: Record<string, string>" not in s, "bảng BUA hết chỗ dùng mà vẫn còn"
    assert "const BA_BUA: [string, string][]" in s


# ══ 2 · BỐN Ô MÀU, LẤY TỪ LOGO ══════════════════════════════════════════════════════════════

def test_tr20_5_dau_ngay_dong_dung_xanh_la_logo_va_xam():
    assert all(x in luat(".tra-chips2 em.b.co") for x in (LUC_CHU, LUC_NEN, LUC_VIEN))
    t = luat(".tra-chips2 em.b")
    assert XAM_CHU in t and XAM_NEN in t


def test_tr20_6_dau_ngay_mo_tren_nen_navy():
    """Nền navy nên phải có bộ màu riêng; dùng lại bộ nền sáng là chữ xanh nhạt trên navy."""
    assert LUC_CHU in luat(".tra-day.on .tra-chips2 em.b.co")
    assert "background:#fff;" in luat(".tra-day.on .tra-chips2 em.b.co") + ";", \
        "trắng .92 trên đầu navy sẫm nhất chỉ còn 4,39:1 — phải trắng ĐẶC"
    t = luat(".tra-day.on .tra-chips2 em.b")
    assert "color:#fff" in t and "rgba(0,0,0,.22)" in t


def test_tr20_7_chan_ngay_doi_sang_mau_logo_va_het_chu_kho_doc():
    s = doc()
    assert "#8a8f96" not in luat(".tra-bua em"), "xám cũ chỉ được 2,98:1 — dưới ngưỡng WCAG"
    assert XAM_CHU in luat(".tra-bua em")
    assert all(x in luat(".tra-bua em.co") for x in (LUC_CHU, LUC_NEN, LUC_VIEN))
    # Màu xanh cũ phải biến khỏi MỌI luật kiểu. Bỏ chú thích ra trước khi soi: chú thích có
    # quyền nhắc «xanh cũ #1C6B4A đổi sang…», và tìm cả tệp sẽ bắt nhầm đúng câu ấy.
    khong_chu_thich = re.sub(r"/\*.*?\*/|//[^\n]*", "", s, flags=re.S).lower()
    for cu in ("#1c6b4a", "#eaf5ef", "#bfe0cd", "#8a8f96", "#5b82c4"):
        assert cu not in khong_chu_thich, f"còn sót màu cũ {cu} trong mã"


def test_tr20_8_khong_dung_hong_logo_cho_bua_khong_bao_gom():
    """Hồng logo dành cho CẢNH BÁO. «Bữa không bao gồm» là một sự vắng mặt, không phải cảnh
    báo — dùng hồng ở đây là làm nhạt tín hiệu cảnh báo khi cần nó thật.

    Soi trong THÂN từng luật chứ không tìm cả tệp: lời chú thích có quyền nhắc tới #FF6F96 để
    nói rõ vì sao KHÔNG dùng nó, và tìm cả tệp sẽ báo động giả đúng vào câu giải thích ấy."""
    for pc in (".tra-chips2 em.b", ".tra-chips2 em.b.co", ".tra-bua em", ".tra-bua em.co",
               ".tra-day.on .tra-chips2 em.b", ".tra-day.on .tra-chips2 em.b.co"):
        t = luat(pc).lower()
        assert "#ff6f96" not in t, f"{pc} dùng hồng logo — hồng để dành cho cảnh báo"


# ══ 3 · PHẢI THẮNG CHẮC, KHÔNG HOÀ RỒI TRÔNG VÀO THỨ TỰ DÒNG ════════════════════════════════

def test_tr20_9_do_uu_tien_lon_hon_han_luat_chung():
    chung_dong = diem(".tra-chips2 em")
    chung_mo = diem(".tra-day.on .tra-chips2 em")
    bua_dong = diem(".tra-chips2 em.b.co")
    bua_mo = diem(".tra-day.on .tra-chips2 em.b.co")
    assert chung_dong == (0, 1, 1) and chung_mo == (0, 3, 1), (chung_dong, chung_mo)
    assert bua_dong == (0, 3, 1) and bua_mo == (0, 5, 1), (bua_dong, bua_mo)
    assert bua_dong > chung_dong and bua_mo > chung_mo
    assert diem(".tra-chips2 em.b") > chung_dong
    assert diem(".tra-day.on .tra-chips2 em.b") > chung_mo


# ══ 4 · KHÔNG LÀM HỎNG THỨ ĐANG CHẠY ════════════════════════════════════════════════════════

def test_tr20_10_sau_vong_truoc_con_nguyen():
    s = doc()
    for can in ['className="tra-moc"', 'className="tra-gio"', "tra-dnoi", "tra-dfoot",
                "if (moId) moSp(moId); else tim();", "if (!ds) tim();",
                "const can = (sp.ct_rieng || []).includes(chon) ? chon : null;",
                "#vtd-access .tra a.ksv-btn", "#vtd-access .ksv.tra input[type=checkbox]"]:
        assert can in s, f"vòng này làm mất {can}"
    assert s.count("<h1") == 2 and s.count('<main className="ksv tra">') == 2
    assert s.count("onClick={moDat}") == 1


def test_tr20_11_chan_ngay_van_hien_du_ba_bua():
    """Vòng này thêm ba viên ở ĐẦU ngày, không được nhân thể bỏ ba viên ở CHÂN ngày."""
    s = doc()
    assert s.count("BA_BUA.map") == 2, "phải có đúng hai chỗ: đầu ngày và chân ngày"


# ══ 5 · NHÃN NHỎ IN HOA ĐỌC ĐƯỢC ════════════════════════════════════════════════════════════

def test_tr20_12_mau_nhan_nho_doi_sang_dam_va_gom_ve_mot_token():
    """Quét tương phản cả trang tour trên bản chạy: 9 chỗ không đạt, 7 trong số đó là đúng
    một màu #5B82C4 ở 3,86:1. Gom về một token để lần sau đổi một chỗ, không đổi năm chỗ."""
    s = doc()
    assert "--tra-nhan:#4b6ba1" in s
    assert s.count("var(--tra-nhan)") >= 5, "còn chỗ nhãn chưa chuyển sang token"
    khong_chu_thich = re.sub(r"/\*.*?\*/|//[^\n]*", "", s, flags=re.S).lower()
    assert "#5b82c4" not in khong_chu_thich


# ══ 6 · KHÔNG KÉO TOKEN HỆ THỐNG VÀO TRANG KHÁCH ════════════════════════════════════════════

def test_tr20_13_khong_goi_token_vtos_trong_trang_khach():
    """Đo trên chính trang tour đang chạy: --vtos-success ra #53C49A và --vtos-success-bg ra
    #14392F, tức gốc trang đang ở BẢN TỐI trong khi nội dung trang khách là nền sáng. Gọi
    token vào đây là chữ bạc hà trên nền xanh nhạt — 1,96:1. Chép giá trị bản sáng ra chữ
    thật, đúng cách mọi luật .tra- khác vẫn làm."""
    s = doc()
    khong_chu_thich = re.sub(r"/\*.*?\*/|//[^\n]*", "", s, flags=re.S)
    assert "var(--vtos-" not in khong_chu_thich, \
        "kéo token hệ thống vào trang khách: gốc trang đang ở bản tối, đo lại trước khi dùng"
