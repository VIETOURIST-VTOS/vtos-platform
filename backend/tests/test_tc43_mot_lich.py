# -*- coding: utf-8 -*-
"""TC-43 · MỘT LỊCH DUY NHẤT thay cho ba lịch.

Anh Tuấn 16/9/2026 hỏi có dùng Google Calendar thay n8n được không. Câu trả lời là không — Calendar
là lời nhắc cho NGƯỜI, nó không gọi được máy chủ, và ai quên bấm là mất kỳ ấy vĩnh viễn. Nhưng câu
hỏi ấy làm lộ ra một chỗ yếu thật của bản TC-39, và vòng này chữa chỗ ấy.

══════════════════════════════════════════════════════════════════════════════════════════════
CHỖ YẾU: PHẦN DỄ SAI NHẤT ĐANG NẰM Ở NƠI KHÔNG BỘ KIỂM NÀO CANH
══════════════════════════════════════════════════════════════════════════════════════════════
TC-39 để lịch tự truyền `kind` và `ngay`, và chú thích của chính nó cảnh báo: gõ sai ô ngày là
"hỏng vĩnh viễn số liệu của kỳ ấy". Cảnh báo đúng — nhưng ô cấu hình lịch nằm NGOÀI kho mã: không
bộ kiểm nào chạy qua nó, không ai soát lại, và sai thì im lặng. Ba lịch là ba ô như thế, mỗi ô một
biểu thức ngày viết tay.

Nay lịch chỉ còn phải biết MỘT việc: gọi mỗi ngày một lần, không tham số. Phần "hôm nay là kỳ gì,
mốc ngày nào" chuyển vào `services/lich_chup.ky_den_han` — và tệp này canh từng trường hợp biên.

══════════════════════════════════════════════════════════════════════════════════════════════
BỐN TRƯỜNG HỢP BIÊN, VÀ CẢ BỐN ĐỀU TỪNG LÀ CHỖ NGƯỜI TA GÕ SAI TRONG CRON
══════════════════════════════════════════════════════════════════════════════════════════════
1. Mốc là HÔM QUA, không phải hôm nay — chụp 00:30 ngày 1/10 là chụp cho tháng 9.
2. Mùng 1 rơi đúng thứ Hai thì chụp CẢ BA kỳ, không phải chọn một.
3. Mốc qua đầu năm: 1/1 chụp tháng 12 năm trước.
4. Ngày thường thì đúng một kỳ — không lặng lẽ chụp thừa kỳ tuần hay tháng, vì chụp thừa là ĐÈ lên
   ô của kỳ chưa đóng.
"""
import datetime as dt
import re
from pathlib import Path

import pytest

from app.services import lich_chup as LC

GOC = Path(__file__).resolve().parents[2]
ROUTER = GOC / "backend" / "app" / "api" / "v1" / "bao_cao.py"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma(s: str) -> str:
    s = re.sub(r'^\s*"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


# ═════════════════ 1 · KỲ NÀO ĐẾN HẠN HÔM NAY ═════════════════

def test_ngay_thuong_chi_chup_ky_ngay():
    # Thứ Tư 16/9/2026, không phải mùng 1.
    ds = LC.ky_den_han(dt.date(2026, 9, 16))
    assert ds == [("ngay", dt.date(2026, 9, 15))], (
        "Ngày thường chụp thừa kỳ tuần hay tháng là ĐÈ lên ô của một kỳ CHƯA ĐÓNG — con số nửa kỳ "
        "mang nhãn kỳ đủ, và không có gì trông giống lỗi."
    )


def test_thu_hai_chup_them_ky_tuan():
    # Thứ Hai 14/9/2026 → tuần vừa đóng kết thúc Chủ nhật 13/9.
    ds = LC.ky_den_han(dt.date(2026, 9, 14))
    assert ds == [("ngay", dt.date(2026, 9, 13)), ("tuan", dt.date(2026, 9, 13))]


def test_mung_mot_chup_them_ky_thang():
    # 1/10/2026 là thứ Năm → tháng vừa đóng kết thúc 30/9.
    ds = LC.ky_den_han(dt.date(2026, 10, 1))
    assert ds == [("ngay", dt.date(2026, 9, 30)), ("thang", dt.date(2026, 9, 30))]


def test_mung_mot_roi_dung_thu_hai_thi_chup_ca_ba():
    """Ba kỳ là BA CÂU HỎI khác nhau về cùng một ngày cuối, không phải ba mức của một thang.

    Bỏ bớt kỳ nào hôm ấy là mất kỳ ấy vĩnh viễn — chỉ tiêu tồn kho không tính lại được.
    """
    # 1/6/2026 là thứ Hai.
    hom_nay = dt.date(2026, 6, 1)
    assert hom_nay.weekday() == 0 and hom_nay.day == 1
    ds = LC.ky_den_han(hom_nay)
    assert [k for k, _ in ds] == ["ngay", "tuan", "thang"]
    assert {m for _, m in ds} == {dt.date(2026, 5, 31)}, (
        "Cả ba kỳ phải dùng CHUNG một mốc hôm qua — ba mốc rời nhau là ba chỗ có thể lệch."
    )


def test_moc_qua_dau_nam():
    ds = LC.ky_den_han(dt.date(2027, 1, 1))
    assert ("thang", dt.date(2026, 12, 31)) in ds, "1/1 phải chụp tháng 12 NĂM TRƯỚC."


@pytest.mark.parametrize("ngay", [dt.date(2026, 9, d) for d in range(1, 31)])
def test_moc_luon_la_hom_qua_va_khong_bao_gio_la_hom_nay(ngay):
    for kind, moc in LC.ky_den_han(ngay):
        assert moc == ngay - dt.timedelta(days=1), (
            f"Kỳ {kind} lấy mốc {moc} trong khi hôm nay là {ngay}. Lấy hôm nay là dán nhãn kỳ vừa "
            f"đóng lên con số của kỳ mới khi nó mới đi được nửa tiếng."
        )


def test_moi_ngay_deu_co_it_nhat_mot_ky():
    """Một ngày không có kỳ nào là một ngày lịch chạy mà không chụp gì — và không ai biết."""
    d = dt.date(2026, 1, 1)
    while d < dt.date(2027, 1, 1):
        assert LC.ky_den_han(d), f"{d} không có kỳ nào đến hạn"
        d += dt.timedelta(days=1)


def test_mot_nam_co_dung_12_ky_thang_va_52_hoac_53_ky_tuan():
    """Đếm cả năm — một luật sai lệch một ngày thì con số này lộ ra ngay."""
    dem = {"ngay": 0, "tuan": 0, "thang": 0}
    d = dt.date(2026, 1, 1)
    while d < dt.date(2027, 1, 1):
        for kind, _ in LC.ky_den_han(d):
            dem[kind] += 1
        d += dt.timedelta(days=1)
    assert dem["ngay"] == 365
    assert dem["thang"] == 12
    assert dem["tuan"] in (52, 53)


# ═════════════════ 2 · CỬA CHO LỊCH: MỘT LẦN MỖI NGÀY, KHÔNG THAM SỐ ═════════════════

def test_cua_khong_doi_tham_so_nao():
    """Cả điểm của vòng này: lịch không còn ô nào để gõ sai."""
    ma = _ma(_doc(ROUTER))
    m = re.search(r"def chup_hom_nay\(([^)]*)\)", ma)
    assert m, "Thiếu cửa /chup-hom-nay"
    tham_so = m.group(1)
    assert "kind" not in tham_so and "ngay" not in tham_so, (
        "Cửa cho lịch KHÔNG được nhận kind hay ngay — đó chính là hai ô mà bản ba lịch để lộ ra "
        "ngoài kho mã, nơi không bộ kiểm nào canh."
    )
    assert 'dependencies=[Depends(robot_auth)]' in ma[ma.index("chup-hom-nay") - 200:
                                                      ma.index("chup-hom-nay") + 200], (
        "Cửa robot phải xác thực bằng ROBOT_TOKEN, cùng kiểu với mọi đường robot đã có."
    )


def test_cua_cu_van_con_de_chay_bu_thu_cong():
    ma = _ma(_doc(ROUTER))
    assert '@router.post("/chup"' in ma, (
        "Cửa /chup cũ là cửa CHẠY BÙ THỦ CÔNG cho một kỳ cũ — việc ấy phải nói rõ kỳ nào, nên nó "
        "đúng là chỗ để người gọi tự truyền ngày. Gỡ nó đi là mất đường chạy bù."
    )


def test_mot_ky_hong_khong_keo_theo_ky_khac():
    """Ngày 1 rơi đúng thứ Hai có BA kỳ phải chụp. Một kỳ ném lỗi mà làm chết hai kỳ kia là mất
    vĩnh viễn hai kỳ ấy."""
    ma = _ma(_doc(ROUTER))
    than = ma[ma.index("def chup_hom_nay"):]
    than = than[:than.index("\n@") if "\n@" in than else len(than)]
    assert "for kind, moc in" in than and "try:" in than and "except" in than, (
        "Mỗi kỳ phải bọc try riêng trong vòng lặp, không bọc chung cả mẻ."
    )
    assert "hong.append" in than, "Kỳ hỏng phải hiện ra trong kết quả trả về."
    assert "so_ky_hong" in than, (
        "Lịch tự động chỉ đọc vài trường; phải có một con số nói thẳng có kỳ nào hỏng không."
    )
    assert "raise" not in than, (
        "KHÔNG ném lỗi ra ngoài: n8n báo đỏ thì người ta chạy lại cả mẻ, ghi đè lên những kỳ VỪA "
        "chụp đúng — lấy một kỳ hỏng đổi lấy ba kỳ hỏng."
    )


def test_cau_giai_thich_di_kem_ket_qua():
    """Nhật ký chỉ ghi "đã chụp 3 kỳ" thì sáu tháng sau không ai nhớ vì sao hôm ấy ba kỳ."""
    assert "hôm nay là thứ Hai" in _doc(GOC / "backend" / "app" / "services" / "lich_chup.py")
    assert "vi_sao" in _ma(_doc(ROUTER))
    mo = LC.mo_ta(dt.date(2026, 6, 1))
    assert "3 kỳ" in mo and "thứ Hai" in mo and "ngày 1" in mo
