"""K11 – bộ kiểm độ dài dữ liệu và tính toàn vẹn của dữ liệu nạp mặc định.

Vì sao cần: phép thử chạy trên SQLite, máy chủ thật chạy PostgreSQL. SQLite không ép độ dài cột chuỗi –
gán 300 ký tự vào một cột khai String(120) thì nó nhận, xanh hết. PostgreSQL từ chối. Nghĩa là một hàm
nạp mặc định có giá trị quá dài sẽ xanh trên máy em và làm container không khởi động được trên máy chủ –
đúng loại lỗi chỉ lộ ra khi đã đẩy lên, lúc không còn ai nhìn màn hình.

Ba phép đo, tất cả ĐỌC GIỚI HẠN TỪ MÔ HÌNH, không chép con số vào phép thử:

  1. Chuỗi dài quá giới hạn cột.
  2. Khoá ngoại trỏ tới dòng không tồn tại. SQLite mặc định không bật ràng buộc khoá ngoại, nên một
     seed gán guide_id=99 vào bảng trống vẫn xanh; PostgreSQL chặn.
  3. Cột bắt buộc (không cho rỗng, không khai mặc định – tức mô hình nói "phải có người điền") mà lại
     mang chuỗi trống. Không sai kiểu, nhưng là dữ liệu vô nghĩa nằm im chờ hiện lên màn hình.

Bộ kiểm này chạy trên DỮ LIỆU ĐANG CÓ trong cơ sở dữ liệu, nên nó vừa gác dữ liệu nạp mặc định trong
phép thử, vừa gác dữ liệu thật trên máy chủ khi robot quét mỗi phút.
"""
from sqlalchemy import select, func, exists
from sqlalchemy.orm import Session

BO_QUA_BANG = ("alembic_version",)
# Chỉ nêu vài dòng làm ví dụ – nêu hết thì phát hiện dài bằng cả bảng và không ai đọc.
VI_DU_TOI_DA = 3


def _bang():
    """Đọc siêu dữ liệu bảng SAU KHI đã nạp toàn bộ mô hình.

    Không import app.main thì Base.metadata chỉ có những bảng tình cờ được nạp trước đó, và bộ kiểm sẽ
    báo "không có gì sai" chỉ vì nó chưa nhìn thấy gì.
    """
    import app.main  # noqa: F401  – nạp trọn mô hình
    from app.db.session import Base
    return {t: b for t, b in Base.metadata.tables.items() if t not in BO_QUA_BANG}


def gioi_han() -> dict[str, dict[str, int]]:
    """{bảng: {cột: độ dài tối đa}} – đọc thẳng từ mô hình, đây là nguồn duy nhất của con số."""
    ra: dict[str, dict[str, int]] = {}
    for ten, bang in _bang().items():
        for c in bang.columns:
            n = getattr(c.type, "length", None)
            if isinstance(n, int) and n > 0:
                ra.setdefault(ten, {})[c.name] = n
    return ra


def cot_bat_buoc() -> dict[str, list[str]]:
    """Cột chuỗi không cho rỗng và KHÔNG khai mặc định – mô hình đang nói "phải có người điền"."""
    ra: dict[str, list[str]] = {}
    for ten, bang in _bang().items():
        for c in bang.columns:
            if c.primary_key or c.nullable: continue
            if c.default is not None or c.server_default is not None: continue
            if getattr(c.type, "length", None) is None and c.type.__class__.__name__ != "Text": continue
            ra.setdefault(ten, []).append(c.name)
    return ra


def _dem(db: Session, cau) -> int:
    try:
        return int(db.execute(cau).scalar() or 0)
    except Exception:
        # Bảng chưa có trong cơ sở dữ liệu (mạch nâng cấp chưa chạy tới) – không phải phát hiện.
        db.rollback()
        return -1


def _chuoi_qua_dai(db: Session) -> list[dict]:
    ra = []
    bangs = _bang()
    for ten, cot_gh in gioi_han().items():
        bang = bangs[ten]
        for cot, n in cot_gh.items():
            c = bang.c[cot]
            dk = (c.isnot(None)) & (func.length(c) > n)
            so = _dem(db, select(func.count()).select_from(bang).where(dk))
            if so <= 0: continue
            vi_du = [str(x)[:80] for x in db.execute(
                select(c).select_from(bang).where(dk).limit(VI_DU_TOI_DA)).scalars()]
            dai_nhat = _dem(db, select(func.max(func.length(c))).select_from(bang).where(dk))
            ra.append({"ma": f"chuoi_qua_dai#{ten}.{cot}", "loai": "chuoi_qua_dai", "muc": "do",
                       "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt",
                       "doi_tuong": f"{ten}.{cot}",
                       "tom_tat": f"{so} dòng ở {ten}.{cot} dài hơn giới hạn {n} ký tự của cột "
                                  f"(dài nhất {dai_nhat}) – PostgreSQL sẽ từ chối",
                       "chi_tiet": {"gioi_han": n, "so_dong": so, "dai_nhat": dai_nhat, "vi_du": vi_du}})
    return ra


def _khoa_ngoai_treo(db: Session) -> list[dict]:
    ra = []
    for ten, bang in _bang().items():
        for c in bang.columns:
            for fk in c.foreign_keys:
                cha = fk.column
                if cha.table.name in BO_QUA_BANG: continue
                # LUÔN đặt bí danh cho bảng cha. Khoá ngoại tự trỏ về chính bảng mình (companies.parent_id
                # → companies.id) mà không có bí danh thì câu con thành "id = parent_id" trên cùng một
                # dòng – luôn sai, và bộ kiểm báo cả bảng là treo. Đây là bẫy đầu tiên nó rơi vào.
                cha_bd = cha.table.alias()
                dk = (c.isnot(None)) & ~exists(select(1).select_from(cha_bd).where(cha_bd.c[cha.name] == c))
                so = _dem(db, select(func.count()).select_from(bang).where(dk))
                if so <= 0: continue
                vi_du = [x for x in db.execute(
                    select(c).select_from(bang).where(dk).limit(VI_DU_TOI_DA)).scalars()]
                ra.append({"ma": f"khoa_ngoai_treo#{ten}.{c.name}", "loai": "khoa_ngoai_treo", "muc": "do",
                           "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt",
                           "doi_tuong": f"{ten}.{c.name}",
                           "tom_tat": f"{so} dòng ở {ten}.{c.name} trỏ tới dòng không tồn tại trong "
                                      f"{cha.table.name}",
                           "chi_tiet": {"tro_toi": f"{cha.table.name}.{cha.name}", "so_dong": so,
                                        "vi_du": [str(v) for v in vi_du]}})
    return ra


def _bat_buoc_de_trong(db: Session) -> list[dict]:
    ra = []
    bangs = _bang()
    for ten, cot in cot_bat_buoc().items():
        bang = bangs[ten]
        for ten_cot in cot:
            c = bang.c[ten_cot]
            so = _dem(db, select(func.count()).select_from(bang).where(
                (c.is_(None)) | (func.trim(c) == "")))
            if so <= 0: continue
            ra.append({"ma": f"bat_buoc_de_trong#{ten}.{ten_cot}", "loai": "bat_buoc_de_trong", "muc": "vang",
                       "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt",
                       "doi_tuong": f"{ten}.{ten_cot}",
                       "tom_tat": f"{so} dòng ở {ten}.{ten_cot} để trống, trong khi mô hình khai cột này "
                                  f"bắt buộc và không có giá trị mặc định",
                       "chi_tiet": {"so_dong": so}})
    return ra


def quet(db: Session) -> list[dict]:
    """Chạy cả ba phép đo. Trả về danh sách phát hiện theo đúng khuôn của robot Kiểm soát."""
    return _chuoi_qua_dai(db) + _khoa_ngoai_treo(db) + _bat_buoc_de_trong(db)


def _do_dai_du_lieu(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot."""
    return quet(db)


def bang(db: Session) -> dict:
    """Số liệu cho màn hình: đo được bao nhiêu cột, phát hiện bao nhiêu chỗ."""
    gh = gioi_han()
    thay = quet(db)
    return {"so_bang": len(_bang()), "so_cot_co_gioi_han": sum(len(v) for v in gh.values()),
            "so_cot_bat_buoc": sum(len(v) for v in cot_bat_buoc().values()),
            "phat_hien": thay}
