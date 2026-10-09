# -*- coding: utf-8 -*-
"""CANH CHÍNH TỆP CI — để cửa hẹp trên main không lặng lẽ chạy thiếu (19/9/2026).

──────────────────────────────────────────────────────────────────────────────────────────────
VIỆC NÀY CANH CÁI GÌ
──────────────────────────────────────────────────────────────────────────────────────────────

`.github/workflows/ci.yml` nay chạy hai hình: ĐỦ BỘ trên PR (cửa chặn), và một CỬA HẸP 12 giây
trên main (cửa báo, soi chuyện hai làn đụng nhau). Cửa hẹp ấy gọi tên từng tệp phép thử bằng tay.

Gọi tên bằng tay có một chỗ hỏng không ai thấy: `pytest tests/khong_co_tep_nay.py` **thoát 4**, và
GitHub Actions coi mã thoát khác 0 là đỏ — nên đổi tên tệp thì CI đỏ, tốt. NHƯNG nếu ai đó xoá một
tệp khỏi dòng lệnh ấy (vì nó đang đỏ, vì cho nhanh), CI **vẫn xanh** và cửa hẹp từ đó soi thiếu một
hàng rào. Một cửa kiểm chạy thiếu mà vẫn xanh nguy hiểm hơn không có cửa nào: người ta tin nó.

Nên phép thử này giữ danh sách ở HAI CHỖ và bắt hai chỗ phải khớp nhau.

VÌ SAO ĐỌC TỆP YAML BẰNG TAY, KHÔNG DÙNG `import yaml`

PyYAML không có trong `requirements-dev.txt` — máy nào cũng đang có nó vì một gói khác kéo theo.
Dựa vào một gói không khai là cách để một ngày nào đó CI đỏ vì `ModuleNotFoundError` ở đúng cái
phép thử sinh ra để canh CI. Đọc bằng chuỗi thì không nợ ai cả.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
CI = GOC / ".github" / "workflows" / "ci.yml"

# Danh sách hàng rào — CHÉP TAY, và đó là chủ ý.
#
# Không suy ra được từ mã: "tệp nào là hàng rào chống hai làn đụng nhau" là một phán đoán của
# người, không phải một tính chất máy đo được. Nên nó nằm đây, có tên, và lệch với ci.yml là đỏ.
#
# THÊM MỘT HÀNG RÀO MỚI thì sửa CẢ HAI chỗ: dòng `pytest` trong ci.yml và danh sách này.
HANG_RAO = (
    "tests/test_mach_migration.py",
    "tests/test_menu.py",
    "tests/test_p11_khai_quyen_phai_co_man_hinh.py",
    "tests/test_ks_ma_tran.py",
    "tests/test_p2_pham_vi_vai_tro.py",
    "tests/test_giu_cho_lan.py",
    # 23/9/2026. Gọi tên ở đây KHÔNG phải để chạy ba luật của nó — ba luật ấy chỉ đo được trên PR,
    # nơi có danh sách tệp nhánh đổi. Gọi tên là để XOÁ TỆP NÀY THÌ ĐỎ: `pytest` gặp đường dẫn
    # không tồn tại thì thoát 4, và Actions coi mã thoát khác 0 là đỏ. Không có dây ấy thì gỡ hàng
    # rào chỉ cần xoá một tệp, vì run_all.sh quét theo mẫu tên chứ không theo danh sách.
    "tests/test_giu_cho_nhanh.py",
    "tests/test_ks_do_dai.py",
    "tests/test_ks2_khai_quyen_may_doc_duoc.py",
    "tests/test_ks_cua_nhap.py",
    "tests/test_man_hinh_co_cua_nhap.py",
)


def _dong_lenh() -> list[str]:
    """Các dòng LỆNH của ci.yml — bỏ hết dòng chú thích.

    Bỏ dòng chú thích không phải cho gọn. Đầu tệp ci.yml có hẳn một đoạn giải thích nhắc tên
    `workflow_dispatch` và tên từng tệp hàng rào; tìm chuỗi trên cả tệp thì LỜI CHÚ làm phép thử
    xanh trong khi phần LỆNH đã mất thứ ấy rồi. Đo bằng phép thử đột biến ngày 19/9/2026: bỏ hẳn
    `workflow_dispatch:` khỏi khối `on:` mà bản đầu của tệp này vẫn xanh — đúng cái bẫy ấy.
    """
    return [d for d in CI.read_text(encoding="utf-8").splitlines() if not d.lstrip().startswith("#")]


def _khoi_viec() -> dict[str, list[str]]:
    """Cắt phần `jobs:` của ci.yml ra thành từng VIỆC, chỉ lấy dòng lệnh.

    VÌ SAO CẦN CẮT. Mấy phép thử đầu tiên của tệp này tìm chuỗi trên CẢ khối lệnh gộp lại. Cách ấy
    đủ cho câu hỏi "chuỗi này còn không", nhưng SAI cho câu hỏi "việc NÀO có điều kiện gì": cả
    `backend`, `web` và `docker` đều khai `if: github.event_name != 'push'`, nên chỉ cần một trong
    ba việc còn khai là phép thử tìm-chuỗi vẫn xanh dù hai việc kia đã mất điều kiện. Từ 09/10/2026
    còn một câu hỏi nữa chỉ trả lời được theo từng việc: cửa hẹp `hang-rao-gop` phải KHÔNG có `if:`.

    Cắt theo thụt lề hai khoảng trắng dưới `jobs:` — đúng hình tệp ci.yml đang viết. Phép thử
    `test_ci7` đỏ nếu không cắt ra được việc `hang-rao-gop`, nên đổi hình tệp mà quên sửa đây thì
    biết ngay, không lặng lẽ cắt ra một bảng rỗng rồi xanh.
    """
    khoi: dict[str, list[str]] = {}
    ten = None
    trong_jobs = False
    for d in _dong_lenh():
        if d.rstrip() == "jobs:":
            trong_jobs = True
            continue
        if not trong_jobs or not d.strip():
            continue
        if not d.startswith(" "):          # ra khỏi khối jobs:
            trong_jobs = False
            continue
        if re.fullmatch(r"  [A-Za-z0-9_-]+:", d.rstrip()):
            ten = d.strip().rstrip(":")
            khoi[ten] = []
            continue
        if ten is not None:
            khoi[ten].append(d)
    return khoi


def _dong_pytest() -> str:
    dong = [d for d in _dong_lenh() if "python -m pytest" in d and "tests/" in d]
    assert len(dong) == 1, (
        "Phải có ĐÚNG MỘT dòng `python -m pytest tests/...` trong ci.yml — thấy "
        f"{len(dong)}. Nhiều dòng thì phép thử này không biết canh dòng nào."
    )
    return dong[0]


def test_ci1_moi_tep_hang_rao_deu_co_that():
    """Tệp kể tên trong ci.yml mà không tồn tại thì CI trên main sẽ đỏ mỗi lần gộp."""
    thieu = [t for t in HANG_RAO if not (GOC / "backend" / t).exists()]
    assert not thieu, (
        f"Các tệp hàng rào sau được ci.yml gọi tên nhưng KHÔNG CÓ trong kho: {thieu}. "
        "Đổi tên một tệp phép thử thì phải sửa cả dòng `pytest` trong .github/workflows/ci.yml."
    )


def test_ci2_ci_yml_goi_du_danh_sach_hang_rao():
    """Ai bớt một tệp khỏi dòng lệnh cho nhanh thì phép thử này đỏ ngay, không đợi tới lúc mất."""
    dong = _dong_pytest()
    thieu = [t for t in HANG_RAO if t not in dong]
    assert not thieu, (
        f"ci.yml KHÔNG gọi các hàng rào sau khi đẩy vào main: {thieu}. "
        "Bớt một hàng rào khỏi cửa hẹp là mở lại đúng chỗ hở mà cửa ấy sinh ra để bịt."
    )


def test_ci3_khong_goi_thua_tep_ngoai_danh_sach():
    """Chiều ngược lại: thêm tệp vào ci.yml mà quên khai ở đây thì danh sách này thành nói dối."""
    trong_ci = set(re.findall(r"tests/[A-Za-z0-9_]+\.py", _dong_pytest()))
    thua = sorted(trong_ci - set(HANG_RAO))
    assert not thua, (
        f"ci.yml gọi thêm {thua} mà danh sách HANG_RAO ở tệp này chưa có. "
        "Khai vào đây kèm một dòng nói vì sao nó là hàng rào chống đụng độ."
    )


def test_ci4_bo_do_du_khong_chay_lai_tren_main():
    """Chỗ rò tiền: nếu ai bỏ hai điều kiện này thì bộ 24 phút lại chạy hai lần cho một việc.

    Ngày 19/9/2026 trần chi tiêu Actions chạm đáy lúc 13 giờ và GitHub dừng hẳn mọi việc của bốn
    làn. Nguyên nhân là bộ đủ chạy cả trên PR lẫn trên main — lần thứ hai không chặn được gì vì mã
    đã vào kho rồi. Phép thử này để lần sau không ai lặng lẽ bật lại.
    """
    lenh = "\n".join(_dong_lenh())
    assert "if: github.event_name != 'push'" in lenh, (
        "Việc `backend` (bộ đủ ~24 phút) phải có `if: github.event_name != 'push'` — không có thì "
        "nó chạy lại trên main sau mỗi lần gộp, tốn gấp đôi mà không chặn được gì."
    )
    assert "hang-rao-gop" in _khoi_viec(), (
        "Phải còn cửa hẹp `hang-rao-gop`. Bỏ hẳn nó thì hai PR cùng xanh riêng lẻ mà gộp lại hỏng "
        "sẽ không ai biết — đúng chuyện suýt xảy ra hai lần ngày 19/9/2026. Việc nó chạy trên những "
        "sự kiện nào thì `test_ci7` canh."
    )


def test_ci6_buoc_tinh_danh_sach_tep_doi_con_nguyen():
    """Hàng rào giữ chỗ làn đứng trên MỘT bước của ci.yml — gỡ bước ấy là nó tắt mà vẫn xanh.

    `backend/tests/test_giu_cho_nhanh.py` không tự gọi `git`: nó đọc danh sách tệp nhánh đổi từ
    biến `VTOS_TEP_DOI` do ci.yml tính sẵn. Cách ấy tốt hơn (bộ phép thử còn chạy ở hai chỗ không
    có thư mục .git), nhưng đổi lại nó nợ ci.yml một bước — và một món nợ không ai canh thì có
    ngày mất.

    Phép thử `test_gn1` bên kia đỏ khi CHẠY trên PR mà không thấy danh sách. Phép thử này đỏ sớm
    hơn một nhịp: khi bước ấy biến khỏi tệp cấu hình, kể cả lúc đang chạy ở chỗ khác.
    """
    lenh = "\n".join(_dong_lenh())
    assert "VTOS_TEP_DOI" in lenh, (
        "ci.yml không còn đặt biến `VTOS_TEP_DOI`. Không có nó thì hàng rào “đẩy mã lên phải có "
        "dòng đang làm trong docs/DANG-LAM.md” lặng lẽ không chạy nữa — đúng kiểu hỏng đã để "
        "TC-76 và TC-77 đè lên làn khác hai lần trong ngày 23/9/2026, cả hai lần CI đều xanh."
    )
    assert "git diff --name-only" in lenh, (
        "Mất dòng `git diff --name-only` thì tệp danh sách rỗng, và một danh sách rỗng làm hàng "
        "rào giữ chỗ làn xanh với mọi nhánh."
    )
    assert "if: github.event_name == 'pull_request'" in lenh, (
        "Bước tính danh sách phải giới hạn ở pull request. Trên push vào main, HEAD là một lần "
        "gộp và phép so với nhánh gốc không còn nghĩa như trên PR."
    )
    # 09/10/2026: từ khi cửa hẹp chạy cả trên PR, có HAI việc cùng chạy hàng rào giữ chỗ nhánh, ở
    # hai máy khác nhau. Mỗi máy phải tự tính danh sách. Không đếm "phải có hai bản" — đếm thì
    # thêm việc thứ ba là phải sửa phép thử. Hỏi theo luật: việc nào chạy hàng rào ấy thì việc ấy
    # phải đặt VTOS_TEP_DOI. Thiếu thì cửa hẹp đỏ trên MỌI PR vì thiếu môi trường, không vì có lỗi.
    thieu_bien = []
    for ten, dong in _khoi_viec().items():
        than = "\n".join(dong)
        if "test_giu_cho_nhanh.py" not in than and "run_all.sh" not in than:
            continue
        if "VTOS_TEP_DOI" not in than:
            thieu_bien.append(ten)
    assert not thieu_bien, (
        f"Việc {thieu_bien} chạy hàng rào giữ chỗ nhánh nhưng KHÔNG đặt `VTOS_TEP_DOI`. Luật `gn1` "
        "của test_giu_cho_nhanh BẮT BUỘC thấy danh sách tệp nhánh đổi khi chạy trên pull request, "
        "nên việc ấy sẽ đỏ trên mọi PR — đỏ vì thiếu môi trường chứ không vì có lỗi thật, và đó là "
        "kiểu đỏ làm người ta tắt hàng rào. Mỗi việc chạy ở một máy riêng nên phải tự tính danh sách."
    )


def test_ci7_cua_hep_phai_chay_ca_tren_pr_va_tren_main():
    """LUẬT MỚI 09/10/2026: cửa hẹp phải CHẶN được, nên nó phải chạy cả trên PR.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    CHUYỆN ĐÃ XẢY RA
    ─────────────────────────────────────────────────────────────────────────────────────────────

    Trước ngày này, `hang-rao-gop` khai `if: github.event_name == 'push'` — chỉ chạy SAU khi mã đã
    vào kho. Nó BÁO, không CHẶN. Và ngày 09/10/2026 main đỏ đúng vì thế: hai làn cùng giữ
    `backend/app/services/access.py` (VB-1 của làn Phân quyền và PD-1 của làn Vòng đều còn
    `đang làm`), `test_giu_cho_lan` đỏ — nhưng đỏ trên main, lúc đã muộn.

    Chỗ đau không phải là thiếu cửa chặn. Cửa chặn ĐÃ CÓ: bộ đủ trên PR cũng chạy
    `test_giu_cho_lan`. Nhưng bộ đủ mất ~37 phút, PR được gộp vài phút sau khi mở, và đến lúc main
    đã đỏ thì lượt ấy vẫn còn trạng thái "In progress". **Một cửa chặn mà không ai chờ nổi thì
    trên thực tế là không có cửa nào.** Nên cái phải sửa là THỜI GIAN CHỜ, không phải thêm phép thử.

    ─────────────────────────────────────────────────────────────────────────────────────────────
    LUẬT
    ─────────────────────────────────────────────────────────────────────────────────────────────

    `hang-rao-gop` KHÔNG được khai `if:`. Bỏ trống thì nó chạy trên push, pull_request và cả
    workflow_dispatch — tức là chặn được trên PR (12 giây, chờ được) mà vẫn báo được trên main
    (chống chuyện hai PR cùng xanh riêng lẻ, gộp lại hỏng).

    Phép thử này KHÔNG canh việc "Require status checks" đã bật trong Settings của kho hay chưa:
    thứ ấy không nằm trong mã nên không đo được từ đây. Nó chỉ canh điều đo được — rằng cửa hẹp
    còn chạy trên PR. Ai bật ô ấy ở Settings thì từ đó mọi lần gộp bị chặn 12 giây.

    Và KHÔNG được chữa chỗ này bằng cách thêm một việc thứ hai chạy lại cùng dòng `pytest`:
    `_dong_pytest` bắt ci.yml có ĐÚNG MỘT dòng ấy, vì hai bản danh sách hàng rào là hai bản để
    lệch nhau.
    """
    khoi = _khoi_viec()
    assert "hang-rao-gop" in khoi, (
        "Không cắt ra được việc `hang-rao-gop` từ khối `jobs:` của ci.yml. Hoặc việc ấy đã bị xoá, "
        "hoặc hình thụt lề của tệp đã đổi và `_khoi_viec` cắt sai — cả hai đều phải sửa bằng tay, "
        "đừng sửa phép thử cho hết đỏ."
    )
    # Chỉ lấy `if:` CỦA VIỆC (thụt lề 4), không lấy `if:` của một BƯỚC (thụt lề 8). Hai thứ khác
    # nhau hẳn: `if:` của việc quyết việc có chạy hay không; `if:` của bước chỉ bỏ qua một bước —
    # và cửa hẹp CÓ một bước như thế, bước tính danh sách tệp đổi, chỉ chạy trên PR. Bản đầu của
    # phép thử này gom cả hai nên tự đỏ ngay lần chạy đầu; chỗ ấy là lỗi của phép thử, không phải
    # của ci.yml, nên sửa phép thử mới đúng — ghi lại đây để người sau không gom lại lần nữa.
    dieu_kien = [d.strip() for d in khoi["hang-rao-gop"] if re.fullmatch(r"    if:\s.*", d.rstrip())]
    assert not dieu_kien, (
        "Việc `hang-rao-gop` lại có điều kiện: " + "; ".join(dieu_kien) + "\n\n"
        "Cửa hẹp phải chạy trên CẢ pull_request VÀ push, nên nó không khai `if:` nào cả. Khai lại "
        "`== 'push'` là trả nó về đúng chỗ hở đã làm main đỏ ngày 09/10/2026: nó chỉ báo sau khi "
        "gộp, trong khi cửa chặn thật nặng ~37 phút nên không ai chờ. Khai `== 'pull_request'` thì "
        "mất chiều ngược lại: hai PR cùng xanh riêng lẻ mà gộp lại hỏng sẽ không ai biết.\n\n"
        "Nếu muốn cắt bớt tiền Actions thì cắt ở chỗ khác — việc này tốn ~50 giây một lượt."
    )


def test_ci5_bo_du_van_chay_khi_bam_tay():
    """`workflow_dispatch` là lối chạy đủ bộ trên main trước khi ra bản thật. Mất nó là mất lối ấy."""
    assert any(d.strip() == "workflow_dispatch:" for d in _dong_lenh()), (
        "ci.yml phải giữ `workflow_dispatch`: sau khi cắt bộ đủ khỏi main, đây là cách duy nhất "
        "chạy lại 251 tệp trên main mà không phải mở một PR giả."
    )
