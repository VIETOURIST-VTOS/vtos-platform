# -*- coding: utf-8 -*-
"""KS-4 · Gieo id bằng tay thì phải kèm đặt lại bộ đếm.

ĐO ĐƯỢC 29/10/2026 00:25, cửa `POST /api/v1/khach-san-ota/phap-nhan` (Chủ tịch thêm pháp nhân
Vietourist Holdings vào danh mục):

    sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation)
    duplicate key value violates unique constraint "phap_nhan_hop_dong_pkey"

Đuôi `_pkey` là KHOÁ CHÍNH (cột `id`), không phải cột `ma`. Gốc nằm ở bản di trú
`ks1b4d6f8a2c37_khach_san_ota.py`:

    op.bulk_insert(pn, [{"id": 1, "ma": "INFINIS_CA", ...}])

Gieo một dòng bằng id GÁN TAY thì PostgreSQL không đẩy bộ đếm của bảng theo. Lần ghi đầu tiên
của người thật xin id = 1, đụng dòng đã gieo, và ngã 500. Chính cú ngã ấy đẩy bộ đếm lên một,
nên lần thứ hai vào được — tức lỗi TỰ LÀNH sau khi đã làm hỏng việc của một người đúng một lần,
và không để lại dấu nào ngoài một dòng «duplicate key» trong nhật ký.

Năm dòng OTA trong cùng bản di trú ấy gieo KHÔNG gán id (số thứ ba là `thu_tu`, không phải
`id`), nên bảng `doi_tac_ota` không dính. Chỉ một bảng dính.

VÌ SAO PHÉP THỬ NÀY KHÔNG ĐỤNG CƠ SỞ DỮ LIỆU: bộ kiểm của kho chạy trên SQLite, nơi bộ đếm cư
xử khác hẳn PostgreSQL — soi hành vi cơ sở dữ liệu ở đây là soi nhầm thứ, và sẽ xanh trong khi
hệ thật vẫn hỏng. Nó soi NGUỒN, và soi một bất biến: hễ có bản di trú nào gieo id bằng tay thì
phải có một bản khác đặt lại bộ đếm cho đúng bảng ấy. Bất biến ấy bắt được cả những bảng chưa
ai gieo hôm nay.
"""
import re
from pathlib import Path

GOC_DI_TRU = Path(__file__).resolve().parents[1] / "alembic" / "versions"

# var = op.create_table("ten", ...)   hoặc   var = sa.table("ten", ...)
_GAN_BANG = re.compile(r'(\w+)\s*=\s*(?:op\.create_table|sa\.table)\(\s*["\']([^"\']+)["\']')
# op.bulk_insert(var, ... ) — lấy 600 ký tự đầu phần dữ liệu để dò khoá "id"
_GIEO = re.compile(r"op\.bulk_insert\(\s*(\w+)\s*,\s*(.{0,600})", re.S)
_CO_ID = re.compile(r"""["']id["']\s*:""")

# Dấu hiệu một bản di trú CÓ đặt lại bộ đếm. Soi theo CẢ TỆP chứ không theo từng dòng: trong
# `8a1c2f3d4e5f_fix_vt_id_sequence.py` tên bảng nằm ở dòng `for t in (...)` còn `setval` nằm ở
# dòng sau — soi từng dòng là trượt đúng cái khuôn mình đang chép.
_DAT_LAI = re.compile(r"setval\(|_id_seq|pg_get_serial_sequence\(")
_TEN_BANG = re.compile(r"""["']([a-z_][a-z0-9_]{2,})["']""")


def _doc_het() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(GOC_DI_TRU.glob("*.py")) if p.name != "__init__.py"}


def _bang_gieo_id_tay(ma: str) -> set[str]:
    bien = dict(_GAN_BANG.findall(ma))
    ra = set()
    for var, phan in _GIEO.findall(ma):
        if var in bien and _CO_ID.search(phan):
            ra.add(bien[var])
    return ra


def _bang_duoc_dat_lai(ma: str) -> set[str]:
    """Tên bảng trong một bản di trú CÓ đặt lại bộ đếm. Tệp không đặt lại thì trả rỗng."""
    if not _DAT_LAI.search(ma):
        return set()
    return {m.removesuffix("_id_seq") for m in _TEN_BANG.findall(ma)}


def test_ks4_bo_do_that_su_bat_duoc_cai_gi():
    """Phép dưới chỉ đáng tin nếu bộ dò này đúng. Dựng lại cả ca hỏng lẫn ca lành."""
    hong = ('    pn = op.create_table("bang_gieo_tay", sa.Column("id", sa.Integer()))\n'
            '    op.bulk_insert(pn, [{"id": 1, "ten": "x"}])\n')
    assert _bang_gieo_id_tay(hong) == {"bang_gieo_tay"}

    lanh = ('    ota = op.create_table("bang_khong_gieo_id", sa.Column("id", sa.Integer()))\n'
            '    op.bulk_insert(ota, [{"ma": m, "ten": t} for m, t in DS])\n')
    assert _bang_gieo_id_tay(lanh) == set(), (
        "Gieo mà KHÔNG gán id thì bộ đếm vẫn đúng — báo nhầm ca này là cả kho đỏ oan.")

    # Đúng khuôn đã có trong kho: tên bảng một dòng, setval dòng khác.
    khuon_cu = ('    for t in ("vt_records", "tour_cost_lines"):\n'
                '        op.execute(f"SELECT setval({t}_id_seq, ...)")\n')
    assert {"vt_records", "tour_cost_lines"} <= _bang_duoc_dat_lai(khuon_cu), (
        "Bộ dò phải nhận ra khuôn sẵn có, nếu không nó báo nhầm chính bản vá cũ.")
    assert _bang_duoc_dat_lai('    op.create_table("khong_lien_quan")\n') == set()


def test_ks4_moi_bang_gieo_id_tay_deu_phai_co_dat_lai_bo_dem():
    """Gieo id bằng tay mà không đặt lại bộ đếm = người đầu tiên ghi vào bảng ấy ăn lỗi 500."""
    tep = _doc_het()
    assert tep, f"không thấy bản di trú nào ở {GOC_DI_TRU}"

    gieo: dict[str, str] = {}
    for ten, ma in tep.items():
        for b in _bang_gieo_id_tay(ma):
            gieo.setdefault(b, ten)

    dat_lai: set[str] = set()
    for ma in tep.values():
        dat_lai |= _bang_duoc_dat_lai(ma)

    thieu = {b: t for b, t in gieo.items() if b not in dat_lai}
    assert not thieu, (
        "Bảng được gieo id BẰNG TAY nhưng không bản di trú nào đặt lại bộ đếm:\n    "
        + "\n    ".join(f"{b}  (gieo ở {t})" for b, t in sorted(thieu.items()))
        + "\n\nHậu quả đã xảy ra thật 29/10/2026: Chủ tịch thêm một pháp nhân, máy chủ trả 500 "
          "«duplicate key value violates unique constraint ..._pkey». Cách vá: thêm một dòng "
          "setval như `8a1c2f3d4e5f_fix_vt_id_sequence.py` đã làm."
    )
