#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Đồng bộ CSDL DEV trên máy với các bảng/cột mới – dùng THAY CHO alembic ở máy cá nhân.

    python scripts/dong_bo_csdl_dev.py            # xem trước, KHÔNG sửa gì
    python scripts/dong_bo_csdl_dev.py --ghi      # sửa thật

VÌ SAO KHÔNG DÙNG `alembic upgrade head` Ở MÁY

Đo trên máy thật (11/9/2026): tệp backend/vtos.db có 103 bảng nhưng KHÔNG có bảng `alembic_version`.
Nghĩa là nó chưa bao giờ đi qua alembic – nó do `Base.metadata.create_all(engine)` sinh ra, câu lệnh
mà app tự chạy lúc khởi động khi ENV=dev (xem app/main.py, hàm lifespan).

Chạy `alembic upgrade head` lên một CSDL như thế là bảo alembic dựng lại từ con số không trên một
CSDL đã có đủ 103 bảng: nó đổ ngay ở bản đầu tiên với "table already exists". Và kể cả nếu bỏ qua
được, chuỗi nâng cấp còn vấp một chỗ nữa trên SQLite – bản f1a2b3c4d5e6 (danh mục pháp nhân) thêm
cột kèm KHOÁ NGOẠI, việc mà SQLite không làm được nếu không dùng chế độ batch:

    NotImplementedError: No support for ALTER of constraints in SQLite dialect

Hai điều ấy đều KHÔNG phải lỗi của alembic hay của bản nâng cấp nào: chúng chỉ nói rằng CSDL dev ở
máy và CSDL production đi hai đường khác nhau. Production (PostgreSQL trên Render) đi bằng alembic –
Dockerfile chạy `alembic upgrade head` lúc khởi động container, và ở PostgreSQL thì thêm cột kèm
khoá ngoại là chuyện bình thường.

CÁI SCRIPT NÀY LÀM GÌ

So khai báo model với CSDL đang có, rồi:

    * bảng có trong model mà chưa có trong CSDL  ->  tạo (create_all)
    * cột  có trong model mà chưa có trong bảng  ->  ALTER TABLE ... ADD COLUMN

VÀ KHÔNG LÀM GÌ KHÁC. Không xoá bảng, không xoá cột, không đổi kiểu, không sửa dữ liệu. Cột thêm
vào luôn cho phép rỗng – đúng quy ước K2: rỗng nghĩa là CHƯA NHẬP, và mọi dòng cũ đương nhiên chưa
nhập những cột vừa sinh ra.

CHỈ CHẠY Ở DEV

Gặp ENV khác 'dev' là dừng. Trên production, đường duy nhất là alembic, vì ở đó cần thứ script này
cố ý không có: thứ tự, khả năng quay lui, và một dấu vết nói CSDL đang ở bản nào.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Kiểu cột -> câu SQL. Giữ hẹp và tường minh: gặp kiểu lạ thì BÁO RA chứ không đoán, vì đoán sai
# kiểu cột tiền là hỏng đúng chỗ khó thấy nhất.
def _kieu_sql(cot, dialect) -> str | None:
    try:
        return cot.type.compile(dialect=dialect)
    except Exception:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description="Đồng bộ CSDL dev với model (KHÔNG dùng cho production)")
    p.add_argument("--ghi", action="store_true", help="sửa thật (mặc định chỉ xem trước)")
    a = p.parse_args()

    from sqlalchemy import inspect, text
    from app.core.config import settings
    from app.db.session import Base, engine
    import app.models  # noqa: F401  – nạp hết model để Base biết đủ bảng

    if settings.ENV != "dev":
        print(f"ENV={settings.ENV} – script này CHỈ chạy ở dev. Production dùng alembic.")
        return 2

    print(f"CSDL: {settings.DATABASE_URL}")
    ins = inspect(engine)
    co_bang = set(ins.get_table_names())

    thieu_bang = [t for t in Base.metadata.sorted_tables if t.name not in co_bang]
    thieu_cot: list[tuple[str, str, str]] = []
    for t in Base.metadata.sorted_tables:
        if t.name not in co_bang:
            continue
        co_cot = {c["name"] for c in ins.get_columns(t.name)}
        for c in t.columns:
            if c.name in co_cot:
                continue
            kieu = _kieu_sql(c, engine.dialect)
            if kieu is None:
                print(f"  ! bỏ qua {t.name}.{c.name} – không dựng được kiểu SQL, phải thêm tay")
                continue
            thieu_cot.append((t.name, c.name, kieu))

    print(f"\nBẢNG THIẾU: {len(thieu_bang)}")
    for t in thieu_bang:
        print(f"   + {t.name}")
    print(f"\nCỘT THIẾU: {len(thieu_cot)}")
    for ten, cot, kieu in thieu_cot:
        print(f"   + {ten}.{cot}  ({kieu})")

    if not thieu_bang and not thieu_cot:
        print("\nCSDL đã khớp model – không có gì phải làm.")
        return 0

    if not a.ghi:
        print("\nĐÂY LÀ XEM TRƯỚC – chưa sửa gì. Thêm --ghi để sửa thật.")
        return 0

    # Tạo bảng thiếu. create_all chỉ tạo bảng CHƯA CÓ, không đụng bảng đã có.
    Base.metadata.create_all(engine)
    print(f"\nĐã tạo {len(thieu_bang)} bảng.")

    # Thêm cột thiếu. LUÔN cho phép rỗng: dòng cũ chưa từng có cột này nên chúng CHƯA NHẬP, và
    # nhồi một giá trị mặc định vào là bịa dữ liệu cho quá khứ.
    xong, hong = 0, []
    with engine.begin() as conn:
        for ten, cot, kieu in thieu_cot:
            try:
                conn.execute(text(f'ALTER TABLE "{ten}" ADD COLUMN "{cot}" {kieu}'))
                xong += 1
            except Exception as ex:
                hong.append((ten, cot, f"{type(ex).__name__}: {ex}"[:160]))
    print(f"Đã thêm {xong}/{len(thieu_cot)} cột.")
    for ten, cot, loi in hong:
        print(f"   ! {ten}.{cot}: {loi}")

    n_bang, n_cot = _noi_bat_buoc(engine, Base, ins_moi=inspect(engine))
    if n_cot:
        print(f"Đã dựng lại {n_bang} bảng để nới {n_cot} cột tiền về CHO PHÉP RỖNG.")
    return 1 if hong else 0


def _noi_bat_buoc(engine, Base, ins_moi) -> tuple[int, int]:
    """Nới những cột mà CSDL bắt buộc phải có giá trị trong khi model cho phép rỗng.

    VÌ SAO VIỆC NÀY CẦN, VÀ VÌ SAO NÓ PHẢI DỰNG LẠI BẢNG

    Đo trên CSDL dev thật (11/9/2026): 91 cột đang NOT NULL trong khi model khai nullable. Đúng bằng
    số cột tiền mà đợt K2 đã nới – CSDL ấy được create_all sinh ra TRƯỚC K2 và từ đó không ai đụng
    vào, vì create_all chỉ tạo bảng thiếu chứ không sửa bảng đã có.

    Hệ quả không phải lý thuyết: ghi một dòng chi mà không khai 'paid' thì SQLite từ chối thẳng
    (NOT NULL constraint failed: tour_cost_lines.paid). Mà 'để trống' chính là điều K2 sinh ra để
    cho phép – rỗng nghĩa là CHƯA NHẬP, khác hẳn số 0.

    SQLite không có ALTER COLUMN. Cách duy nhất là dựng lại bảng: đổi tên bảng cũ, tạo bảng mới đúng
    theo model, chép dữ liệu sang theo những cột CÓ Ở CẢ HAI BÊN, rồi xoá bảng cũ. Đây đúng là việc
    mà chế độ batch của alembic làm.

    legacy_alter_table=ON là bắt buộc: không bật thì SQLite đời mới tự sửa mọi khoá ngoại đang trỏ
    tới bảng này thành trỏ vào cái tên tạm, và sau khi xoá bảng tạm thì chúng trỏ vào hư không.
    """
    from sqlalchemy import inspect, text
    can: dict[str, list[str]] = {}
    for t in Base.metadata.sorted_tables:
        if t.name not in set(ins_moi.get_table_names()):
            continue
        db_cot = {c["name"]: c for c in ins_moi.get_columns(t.name)}
        for c in t.columns:
            d = db_cot.get(c.name)
            if d and (not d["nullable"]) and c.nullable and not c.primary_key:
                can.setdefault(t.name, []).append(c.name)
    if not can:
        return 0, 0

    print(f"\nCỘT BỊ BẮT BUỘC SAI: {sum(len(v) for v in can.values())} cột ở {len(can)} bảng")
    for ten, cols in list(can.items())[:8]:
        print(f"   ~ {ten}: {', '.join(cols[:6])}{' …' if len(cols) > 6 else ''}")
    if len(can) > 8:
        print(f"   … và {len(can) - 8} bảng nữa")

    theo_ten = {t.name: t for t in Base.metadata.sorted_tables}
    n_bang = 0
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("PRAGMA foreign_keys=OFF")
        cur.execute("PRAGMA legacy_alter_table=ON")
        for ten in can:
            t = theo_ten[ten]
            cu = {c["name"] for c in ins_moi.get_columns(ten)}
            chung = [c.name for c in t.columns if c.name in cu]
            tam = f"_cu_{ten}"
            cur.execute(f'DROP TABLE IF EXISTS "{tam}"')
            cur.execute(f'ALTER TABLE "{ten}" RENAME TO "{tam}"')
            # CHỈ MỤC ĐI THEO BẢNG KHI ĐỔI TÊN, VÀ GIỮ NGUYÊN TÊN CŨ.
            #
            # Nên khi dựng lại bảng mới, câu CREATE INDEX của nó đụng đúng cái tên đang còn sống trên
            # bảng tạm: "index ix_bank_accounts_cat_code already exists". Phải xoá chỉ mục của bảng
            # tạm trước – chúng sẽ được tạo lại nguyên vẹn cùng bảng mới, vì cùng một khai báo model.
            cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? "
                        "AND name NOT LIKE 'sqlite_autoindex%'", (tam,))
            for (ten_cm,) in cur.fetchall():
                cur.execute(f'DROP INDEX IF EXISTS "{ten_cm}"')
            raw.commit()
            try:
                t.create(bind=engine)      # tạo lại ĐÚNG theo model, kèm chỉ mục
                cols = ", ".join(f'"{c}"' for c in chung)
                # LẤY GÌ SANG: cột nào model bắt buộc mà dòng cũ đang rỗng thì ĐIỀN MẶC ĐỊNH.
                #
                # Cột như 'phien_ban' vừa được thêm ở bước trên bằng ALTER TABLE ADD COLUMN, mà câu
                # lệnh ấy không đặt được NOT NULL – nên mọi dòng cũ đang mang NULL. Bảng dựng lại
                # theo model thì cột ấy NOT NULL, và phép chép đổ ngay:
                #     NOT NULL constraint failed: employees.phien_ban
                # Điền mặc định của chính model là đúng nghĩa: dòng cũ có phiên bản 1.
                #
                # CHỈ điền cho cột model khai NOT NULL VÀ có mặc định. Cột tiền cho phép rỗng vẫn
                # sang nguyên dạng rỗng – rỗng là CHƯA NHẬP, không được biến thành 0.
                lay = []
                for c in chung:
                    mc = t.columns[c]
                    md = None
                    if not mc.nullable and not mc.primary_key:
                        if mc.server_default is not None:
                            md = str(getattr(mc.server_default, "arg", "")).strip("'\"") or None
                        elif mc.default is not None and getattr(mc.default, "is_scalar", False):
                            md = mc.default.arg
                    if md is None:
                        lay.append(f'"{c}"')
                    elif isinstance(md, str) and not md.replace(".", "", 1).isdigit():
                        lay.append(f"""COALESCE("{c}", '{md}')""")
                    else:
                        lay.append(f'COALESCE("{c}", {md})')
                cur.execute(f'INSERT INTO "{ten}" ({cols}) SELECT {", ".join(lay)} FROM "{tam}"')
                cur.execute(f'DROP TABLE "{tam}"')
                raw.commit()
                n_bang += 1
            except Exception as ex:
                # VỠ GIỮA CHỪNG THÌ TRẢ BẢNG VỀ NHƯ CŨ, không để lại một cái tên _cu_ nằm đó.
                # Bảng tạm còn sót là dữ liệu thật nằm dưới một cái tên không ai biết là gì, và lần
                # chạy sau sẽ xoá nó bằng câu DROP TABLE IF EXISTS ở đầu vòng lặp.
                raw.rollback()
                cur.execute(f'DROP TABLE IF EXISTS "{ten}"')
                cur.execute(f'ALTER TABLE "{tam}" RENAME TO "{ten}"')
                raw.commit()
                print(f"   ! {ten}: KHÔNG dựng lại được, đã trả về nguyên trạng "
                      f"({type(ex).__name__}: {str(ex)[:90]})")
        cur.execute("PRAGMA foreign_keys=ON")
        raw.commit()
    finally:
        raw.close()
    return n_bang, sum(len(v) for v in can.values())


if __name__ == "__main__":
    raise SystemExit(main())
