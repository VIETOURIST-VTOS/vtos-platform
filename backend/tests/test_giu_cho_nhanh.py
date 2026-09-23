# -*- coding: utf-8 -*-
"""ĐẨY MÃ LÊN MÀ KHÔNG GHI SỔ GIỮ CHỖ THÌ ĐỎ — 23/9/2026.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

`test_giu_cho_lan.py` đã canh sổ `docs/DANG-LAM.md` từ 11/9/2026, và nó canh đúng MỘT điều: hai
dòng `đang làm` cùng khai một tệp thì đỏ.

Ngày 23/9/2026 đo lại thì thấy hàng rào ấy **chưa bao giờ nổ được một lần nào**. Lý do đơn giản
đến khó chịu: trong 40 dòng của sổ, **không có dòng nào ở trạng thái `đang làm`**. Mọi làn ghi
thẳng `xong` ngay lúc đẩy. Mà luật cũ chỉ so các dòng `đang làm` với nhau — nên một sổ toàn `xong`
là một sổ không giữ chỗ cho ai, và phép thử soi nó thì luôn xanh.

Hôm ấy hỏng hai lần trong một ngày, cùng một hình:

    14:51  làn Vòng (TC-76) đè lên models/__init__.py, ks_cua_nhap.py, Shell.tsx của làn R1
    16:10  làn TC-77      đè lên marketing.py, Shell.tsx, page.tsx của làn R1 — xoá sạch 4 cửa

Cả hai lần **CI đều xanh**, vì xoá phần của làn khác không làm phép thử nào đỏ. Thứ bắt được là
một phép đo chạy bằng tay ngay trước khi bấm nút đẩy:

    git diff --numstat origin/main -- <các tệp sẽ đẩy>     rồi chất vấn từng dòng BỊ BỎ

Một phép đo chạy bằng tay không phải hàng rào. Tệp này là phần làm cho nó thành hàng rào.

──────────────────────────────────────────────────────────────────────────────────────────────
BA LUẬT
──────────────────────────────────────────────────────────────────────────────────────────────

N1. Danh sách tệp nhánh này đổi phải ĐỌC ĐƯỢC. Trên pull request mà không đọc được thì ĐỎ —
    không có danh sách thì hai luật dưới không đo được gì, và một hàng rào không đo được gì mà
    vẫn xanh nguy hiểm hơn không có hàng rào.

N2. Đẩy MÃ lên thì phải kèm một dòng trong sổ. Cụ thể: nhánh có đụng tệp mã thì `docs/DANG-LAM.md`
    phải nằm trong chính danh sách tệp nhánh ấy đổi. Không ép được điều này thì một làn vẫn đi
    nhờ dòng của làn khác mà không tự khai gì — đúng chỗ hở của bản 11/9.

N3. Mọi tệp mã nhánh này đụng phải được một dòng `đang làm` gọi tên. `xong` KHÔNG giữ chỗ — đó là
    nghĩa của chữ `xong`, và cũng là lý do sổ toàn `xong` chưa bao giờ giữ được gì.

CỘNG với luật cũ ở `test_giu_cho_lan.py` (hai làn `đang làm` cùng một tệp thì đỏ), ba luật này
khép kín chuyện đã xảy ra: làn R1 mở dòng `đang làm` cho marketing.py → làn TC-77 muốn đụng cùng
tệp ấy thì buộc phải khai (N2, N3) → khai xong là hai dòng `đang làm` trùng tệp → ĐỎ trên PR của
họ, trước khi gộp, trước khi ai mất gì.

──────────────────────────────────────────────────────────────────────────────────────────────
BỐN ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM
──────────────────────────────────────────────────────────────────────────────────────────────

1. KHÔNG đoán làn từ TÊN NHÁNH. Đọc 60 lần gộp gần nhất thì tên nhánh trong kho này có đủ kiểu:
   `r1-…`, `tc76b-…`, `pq-…`, và cả `so-ty-gia`, `nap-lai-hom-sau`, `bon-tep-la-chuyen-that`. Một
   bảng tiền tố → làn sẽ đỏ oan cho mọi làn đặt tên tự do, mà đỏ oan là cách nhanh nhất để người
   ta thôi nhìn CI. Ba luật trên KHÔNG cần biết nhánh thuộc làn nào.

2. KHÔNG đỏ theo thời gian. Giữ đúng điều `test_giu_cho_lan.py` đã chốt ngày 11/9: không có luật
   "dòng `đang làm` quá N ngày thì đỏ". Một phép thử tự đỏ mà không ai sửa mã là thứ làm người ta
   thôi nhìn CI.

3. KHÔNG bắt tệp khai phải tồn tại. Khai TRƯỚC khi viết thì phần lớn đường dẫn còn chưa có.

4. KHÔNG canh `docs/` ngoài chính quyển sổ. Hai làn viết đè một tệp tài liệu thì gỡ bằng mắt trong
   một phút; hai làn viết đè một tệp mã thì mất nửa ngày. Hàng rào đặt ở chỗ đắt.

LỖ CÒN LẠI, NÓI THẲNG: một làn vẫn có thể đi nhờ dòng `đang làm` của làn khác — N3 chỉ hỏi "có
dòng nào giữ tệp này không", không hỏi "có phải dòng của CHÍNH anh không", vì điều 1 ở trên. N2
bắt anh phải sửa quyển sổ, nhưng không bắt được anh phải sửa ĐÚNG dòng của mình. Bịt nốt lỗ ấy
cần thêm một cột `Nhánh` vào sổ và viết lại cả 40 dòng cũ — để dành, và ghi ra đây để người sau
không tưởng là đã kín.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[2]
SO = "docs/DANG-LAM.md"

# Thư mục MÃ — chỗ một lần đụng độ là nửa ngày. `docs/` cố ý không có mặt (xem điều 4 ở trên).
GOC_MA = ("backend/", "web/", "mobile/", "infra/", "scripts/", ".github/")

DANG_LAM = "đang làm"
BIEN_TEP_DOI = "VTOS_TEP_DOI"


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Phần đọc — tách riêng khỏi phần xét, để phần xét kiểm được bằng số liệu bịa (xem cuối tệp).
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _dong_dang_lam() -> list[dict]:
    """Các dòng `đang làm` của sổ. Dùng chính bộ đọc của test_giu_cho_lan để hai tệp không lệch."""
    from test_giu_cho_lan import _doc_bang
    return [d for d in _doc_bang() if d["trang_thai"] == DANG_LAM]


def _tep_doi() -> list[str] | None:
    """Danh sách tệp nhánh này đổi, do ci.yml tính sẵn và trỏ vào bằng biến VTOS_TEP_DOI.

    KHÔNG tự gọi `git` ở đây. Hộp phép thử chạy trên nhiều chỗ — máy của người, hộp cát giải nén
    từ `git archive` (không có thư mục .git), và CI. Một phép thử tự gọi git sẽ im lặng bỏ qua ở
    hai chỗ đầu và người viết sẽ không biết là nó đang không chạy. Để CI tính rồi ĐƯA cho phép
    thử, thì chỗ nào không có danh sách là biết ngay.
    """
    p = os.environ.get(BIEN_TEP_DOI, "").strip()
    if not p or not Path(p).exists():
        return None
    ds = []
    for d in Path(p).read_text(encoding="utf-8").splitlines():
        d = d.strip().replace("\\", "/")
        if d:
            ds.append(d)
    return ds


def la_tep_ma(t: str) -> bool:
    return t.startswith(GOC_MA)


def phu(tep: str, khai: str) -> bool:
    """Một dòng khai có phủ một tệp không.

    Ba kiểu khai đều nhận: đúng tên tệp, một thư mục kết bằng `/`, và mẫu sao kiểu
    `backend/tests/*.py` (sổ đã có dòng viết kiểu ấy từ 14/9). Nhận mẫu sao là cố ý: một vòng sửa
    chín mươi tệp phép thử mà bắt liệt kê đủ chín mươi dòng thì người ta sẽ khai dối cho xong.
    """
    khai = khai.strip()
    if not khai:
        return False
    if tep == khai:
        return True
    if khai.endswith("/") and tep.startswith(khai):
        return True
    return fnmatch.fnmatch(tep, khai)


def tep_khong_ai_giu(tep_doi: list[str], dong: list[dict]) -> list[str]:
    """Tệp MÃ nào nhánh đụng mà không dòng `đang làm` nào gọi tên.

    Lọc trạng thái NGAY TRONG ĐÂY chứ không tin người gọi đã lọc. Nếu để người gọi lọc thì một
    ngày nào đó ai đó truyền cả bảng vào, các dòng `xong` thành ra cũng giữ chỗ, và hàng rào tắt
    mà vẫn xanh — đúng kiểu hỏng tệp này sinh ra để bịt.
    """
    khai = [k for d in dong if d["trang_thai"] == DANG_LAM for k in d["tep"]]
    return [t for t in tep_doi if la_tep_ma(t) and not any(phu(t, k) for k in khai)]


# ─────────────────────────────────────────────────────────────────────────────────────────────
# BA LUẬT
# ─────────────────────────────────────────────────────────────────────────────────────────────
def test_gn1_tren_pull_request_phai_doc_duoc_danh_sach_tep_doi():
    """N1. Không có danh sách thì N2 và N3 không đo được gì — mà vẫn xanh. Đó là kiểu hỏng tệ nhất.

    Nên trên pull request, thiếu danh sách là ĐỎ, và lời báo chỉ thẳng vào bước đã mất trong
    ci.yml. `test_ci_hang_rao_main.py` canh thêm một lượt để bước ấy không bị gỡ lặng lẽ.
    """
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        pytest.skip("Chỉ bắt buộc trên pull request — ở đây không có danh sách là chuyện bình thường")
    assert _tep_doi() is not None, (
        f"Không đọc được danh sách tệp nhánh này đổi. Biến {BIEN_TEP_DOI} đang là "
        f"“{os.environ.get(BIEN_TEP_DOI, '')}”.\n\n"
        "Bước “Tep nhanh nay doi” trong .github/workflows/ci.yml là chỗ tính danh sách ấy. Mất "
        "bước đó thì hai hàng rào dưới đây lặng lẽ không chạy nữa, và CI vẫn xanh."
    )


def test_gn2_day_ma_len_thi_phai_kem_mot_dong_trong_so():
    """N2. Nhánh đụng tệp mã thì chính quyển sổ phải nằm trong danh sách tệp nhánh ấy đổi.

    Không có luật này thì một làn cứ đẩy mã mà không viết gì vào sổ, rồi dựa vào dòng của làn
    khác cho qua N3. Đúng chỗ hở đã để TC-76 và TC-77 đi lọt ngày 23/9/2026.
    """
    tep = _tep_doi()
    if tep is None:
        pytest.skip("Không có danh sách tệp đổi — test_gn1 lo phần bắt buộc trên pull request")
    ma = [t for t in tep if la_tep_ma(t)]
    if not ma:
        return                                    # vòng chỉ sửa tài liệu: không giữ chỗ gì cả
    assert SO in tep, (
        f"Nhánh này đụng {len(ma)} tệp mã nhưng KHÔNG sửa {SO}.\n\n"
        "Mỗi vòng đẩy lên phải tự ghi một dòng vào sổ giữ chỗ — trước khi viết dòng mã đầu tiên "
        "thì tốt nhất, nhưng chậm nhất là trong chính lần đẩy này.\n\n"
        "Mẫu một dòng:\n"
        "| <Làn> | <mã việc> | " + ", ".join(ma[:3]) + (", …" if len(ma) > 3 else "") +
        " | DD-MM-YYYY HH:MM | đang làm |\n\n"
        f"Vài tệp nhánh này đụng: {ma[:8]}"
    )


def test_gn3_moi_tep_ma_deu_phai_co_mot_dong_dang_lam_giu_cho():
    """N3. LUẬT CHÍNH. `xong` không giữ chỗ — nên sổ toàn `xong` là sổ trống.

    Đỏ ở đây KHÔNG có nghĩa là mã sai. Nó có nghĩa là nhánh này đang đụng những tệp mà không ai
    tuyên bố đang giữ, nên làn kế tiếp không có cách nào biết mà tránh.
    """
    tep = _tep_doi()
    if tep is None:
        pytest.skip("Không có danh sách tệp đổi — test_gn1 lo phần bắt buộc trên pull request")
    thieu = tep_khong_ai_giu(tep, _dong_dang_lam())
    assert not thieu, (
        "CÓ TỆP MÃ KHÔNG DÒNG `đang làm` NÀO GIỮ CHỖ:\n"
        + "\n".join(f"  · {t}" for t in thieu)
        + "\n\nCách xử: mở " + SO + ", thêm (hoặc mở lại) một dòng `đang làm` của làn mình gọi đủ "
          "tên các tệp trên. Đường dẫn viết từ gốc kho; mẫu sao kiểu `backend/tests/*.py` cũng "
          "nhận.\n\nĐỪNG sửa phép thử này cho hết đỏ — sổ không ai giữ chỗ đã làm hỏng hai lần "
          "trong ngày 23/9/2026, và cả hai lần CI đều xanh."
    )


# ─────────────────────────────────────────────────────────────────────────────────────────────
# PHÉP THỬ CHÍNH PHẦN XÉT — chạy trên số liệu BỊA, nên chạy được ở mọi chỗ.
#
# Ba luật ở trên chỉ đo được khi có danh sách tệp đổi, nghĩa là ngoài CI chúng nằm im. Phần dưới
# đây là chỗ chứng minh phần xét THẬT SỰ bắt được cái nó hứa — không cần CI, không cần git, và
# không đợi tới lần hỏng sau mới biết.
# ─────────────────────────────────────────────────────────────────────────────────────────────
def _dong(lan: str, tep: list[str], trang_thai: str = DANG_LAM) -> dict:
    return {"so_dong": 1, "lan": lan, "ma_viec": "X-1", "tep": tep,
            "bat_dau": "23-09-2026 10:00", "trang_thai": trang_thai}


def test_gn4_bat_duoc_dung_chuyen_da_xay_ra_ngay_23_9():
    """Dựng lại đúng 16:10 ngày 23/9: làn khác đụng marketing.py trong khi R1 đang giữ nó.

    Ở đây tệp ĐƯỢC giữ chỗ nên N3 xanh — và đó là đúng: chỗ bắt là luật "hai làn cùng một tệp"
    của test_giu_cho_lan. Điều N3 bắt là trường hợp **không ai khai gì cả**, dựng ngay dưới.
    """
    dang = [_dong("Phân quyền", ["backend/app/api/v1/marketing.py", "web/components/Shell.tsx"])]
    assert tep_khong_ai_giu(["backend/app/api/v1/marketing.py"], dang) == []
    # Không ai khai gì: đúng tình trạng thật của sổ ngày 23/9 — 40 dòng, không dòng nào `đang làm`.
    assert tep_khong_ai_giu(["backend/app/api/v1/marketing.py"], []) == \
        ["backend/app/api/v1/marketing.py"]


def test_gn5_dong_xong_khong_giu_cho():
    """Nếu `xong` cũng giữ chỗ thì hàng rào này vô nghĩa — sổ đang có 40 dòng `xong`."""
    xong = [_dong("Vòng", ["web/components/Shell.tsx"], "xong")]
    assert tep_khong_ai_giu(["web/components/Shell.tsx"], xong) == ["web/components/Shell.tsx"]
    assert _dong("Vòng", ["web/components/Shell.tsx"])["trang_thai"] == DANG_LAM


def test_gn6_tai_lieu_khong_bi_canh_nhung_ma_thi_co():
    """Điều 4: `docs/` ngoài quyển sổ thì không canh. Hàng rào đặt ở chỗ đắt."""
    assert tep_khong_ai_giu(["docs/Bao-cao-thang-9.md", "docs/DANG-LAM.md"], []) == []
    assert tep_khong_ai_giu(["backend/app/services/rules.py"], []) == \
        ["backend/app/services/rules.py"]
    assert tep_khong_ai_giu([".github/workflows/ci.yml"], []) == [".github/workflows/ci.yml"]


def test_gn7_ba_kieu_khai_deu_phu_duoc():
    """Đúng tên · thư mục kết bằng `/` · mẫu sao. Sổ đã có dòng viết kiểu mẫu sao từ 14/9."""
    assert phu("backend/app/services/rules.py", "backend/app/services/rules.py")
    assert phu("backend/app/services/rules.py", "backend/app/services/")
    assert phu("backend/tests/test_abc.py", "backend/tests/*.py")
    assert not phu("backend/app/services/rules.py", "backend/app/services/rule.py")
    assert not phu("web/components/Shell.tsx", "backend/")
    assert not phu("backend/app/services/rules.py", "")


def test_gn8_khai_mot_tep_khong_phu_ca_vong():
    """Khai một tệp rồi đụng mười tệp thì chín tệp còn lại vẫn phải đỏ.

    Nếu không có phép thử này thì một dòng khai lấy lệ đủ để đi qua cả ba luật, và hàng rào trở
    thành thủ tục.
    """
    dang = [_dong("Vòng", ["web/components/Shell.tsx"])]
    thieu = tep_khong_ai_giu(
        ["web/components/Shell.tsx", "web/app/marketing/page.tsx",
         "backend/app/api/v1/marketing.py"], dang)
    assert thieu == ["web/app/marketing/page.tsx", "backend/app/api/v1/marketing.py"]


def test_gn9_so_that_hien_nay_doc_duoc_va_dem_duoc_dong_dang_lam():
    """Đọc SỔ THẬT, không phải số bịa: bộ đọc còn chạy, và nói ra sổ đang giữ chỗ cho bao nhiêu tệp.

    Không khẳng định con số phải lớn hơn 0 — một ngày mọi làn đều rảnh là chuyện có thật. Khẳng
    định là bộ đọc KHÔNG vỡ, vì ba luật trên đều đứng trên nó.
    """
    dang = _dong_dang_lam()
    assert isinstance(dang, list)
    for d in dang:
        assert d["lan"] and d["tep"], f"Dòng {d['so_dong']} của {SO} khai thiếu"
