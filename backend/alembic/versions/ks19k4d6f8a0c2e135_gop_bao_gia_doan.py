"""KS-19k — gộp báo giá đoàn (TK-2) vào bảng báo giá CHUNG (Chủ tịch chọn 06/11/2026).

V6: «một bảng cho cả lẻ và đoàn, lọc bằng cột mang». TK-2 đã tách riêng bảng bao_gia_doan → phép thử V6 đỏ.
Chủ tịch chọn «đầu chung + bảng phụ» và «quy về tên trạng thái chung»:
  · đầu báo giá (mã, mảng kd_doan, khách, trạng thái, người lập / duyệt) → bao_gia, cột mới nguon = 'thiet_ke';
  · phần riêng (dòng tạm tính + giá vốn, hệ số trẻ em, số NL/TE/EB, giá từng hạng, hạn 24 giờ, mã băm) → bảng phụ
    bao_gia_thiet_ke, khóa chính = id dòng đầu;
  · da_duyet → da_gui, khach_dong_y → khach_chot;
  · hợp đồng nháp khách đồng ý đã tạo được nối bao_gia_id về dòng đầu (trước để trống).
Dữ liệu cũ chép sang trọn, giữ nguyên mã BGD-…; rồi bỏ bảng bao_gia_doan.

Revision ID: ks19k4d6f8a0c2e135
Revises: ks19a2c4e6f8b0d135
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op

revision = "ks19k4d6f8a0c2e135"
down_revision = "ks19a2c4e6f8b0d135"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)
DOI = {"da_duyet": "da_gui", "khach_dong_y": "khach_chot"}
DOI_NGUOC = {v: k for k, v in DOI.items()}
PHU = ("thiet_ke_id", "thiet_ke_ma", "tai_khoan_id", "dong", "bien_pt", "he_so_te", "so_nl", "so_te", "so_eb",
       "tong_von", "tong_ban", "gia_nl", "gia_te", "bao_gom", "khong_bao_gom", "ghi_chu", "cap_duyet", "ly_do_bien",
       "gui_duyet_luc", "ly_do_tra", "han_luc", "ma_bam", "khach_dong_y_luc", "hop_dong_id")


def _cot_phu():
    return [
        sa.Column("thiet_ke_id", sa.Integer(), sa.ForeignKey("thiet_ke_doan.id"), nullable=False),
        sa.Column("thiet_ke_ma", sa.String(20), nullable=False),
        sa.Column("tai_khoan_id", sa.Integer(), sa.ForeignKey("tai_khoan_ngoai.id"), nullable=False),
        sa.Column("dong", sa.JSON(), nullable=False),
        sa.Column("bien_pt", TIEN, nullable=False, server_default="10"),
        sa.Column("he_so_te", TIEN, nullable=False, server_default="0.75"),
        sa.Column("so_nl", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_te", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("so_eb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tong_von", TIEN, nullable=True),
        sa.Column("tong_ban", TIEN, nullable=True),
        sa.Column("gia_nl", TIEN, nullable=True),
        sa.Column("gia_te", TIEN, nullable=True),
        sa.Column("bao_gom", sa.JSON(), nullable=False),
        sa.Column("khong_bao_gom", sa.JSON(), nullable=False),
        sa.Column("ghi_chu", sa.Text(), nullable=False, server_default=""),
        sa.Column("cap_duyet", sa.String(10), nullable=False, server_default=""),
        sa.Column("ly_do_bien", sa.String(300), nullable=False, server_default=""),
        sa.Column("gui_duyet_luc", sa.DateTime(), nullable=True),
        sa.Column("ly_do_tra", sa.String(300), nullable=False, server_default=""),
        sa.Column("han_luc", sa.DateTime(), nullable=True),
        sa.Column("ma_bam", sa.String(64), nullable=False, server_default=""),
        sa.Column("khach_dong_y_luc", sa.DateTime(), nullable=True),
        sa.Column("hop_dong_id", sa.Integer(), sa.ForeignKey("hop_dong_khach.id"), nullable=True),
    ]


def upgrade() -> None:
    op.add_column("bao_gia", sa.Column("nguon", sa.String(20), nullable=False, server_default="ban_hang"))
    op.create_index("ix_bao_gia_nguon", "bao_gia", ["nguon"])
    op.create_table("bao_gia_thiet_ke",
                    sa.Column("id", sa.Integer(), sa.ForeignKey("bao_gia.id"), primary_key=True), *_cot_phu())
    for c in ("thiet_ke_id", "thiet_ke_ma", "tai_khoan_id"):
        op.create_index(f"ix_bao_gia_thiet_ke_{c}", "bao_gia_thiet_ke", [c])

    bind = op.get_bind()
    md = sa.MetaData()
    cu = sa.Table("bao_gia_doan", md, autoload_with=bind)
    dau = sa.Table("bao_gia", md, autoload_with=bind)
    phu = sa.Table("bao_gia_thiet_ke", md, autoload_with=bind)
    tkn = sa.Table("tai_khoan_ngoai", md, autoload_with=bind)
    tkd = sa.Table("thiet_ke_doan", md, autoload_with=bind)
    hd = sa.Table("hop_dong_khach", md, autoload_with=bind)
    for r in bind.execute(sa.select(cu).order_by(cu.c.id)).mappings().all():
        k = bind.execute(sa.select(tkn).where(tkn.c.id == r["tai_khoan_id"])).mappings().first() or {}
        t = bind.execute(sa.select(tkd.c.ngay_di).where(tkd.c.id == r["thiet_ke_id"])).first()
        ten = (k.get("ho_ten") or k.get("dien_thoai") or f"Khách cổng #{r['tai_khoan_id']}")[:200]
        nguong = 0.10
        bien = None
        if r["tong_ban"]:
            bien = (float(r["tong_ban"]) - float(r["tong_von"] or 0)) / float(r["tong_ban"])
        moi = bind.execute(dau.insert().values(
            ma=r["ma"], mang="kd_doan", nguon="thiet_ke", khach_ten=ten,
            khach_dien_thoai=(k.get("dien_thoai") or "")[:30], khach_email=(k.get("email") or "")[:120],
            ngay_khoi_hanh=t[0] if t else None, so_khach=int(r["so_nl"] or 0) + int(r["so_te"] or 0) + int(r["so_eb"] or 0),
            han_hieu_luc=r["han_luc"].date() if r["han_luc"] else None, trang_thai=DOI.get(r["trang_thai"], r["trang_thai"]),
            bien_luc_gui=bien if r["duyet_luc"] else None, nguong_luc_gui=nguong if r["duyet_luc"] else None,
            duoi_bien=r["cap_duyet"] == "ct_tgd", giai_trinh=r["ly_do_bien"] or "", duyet_boi=r["duyet_boi"] or "",
            duyet_luc=r["duyet_luc"], ly_do_tu_choi=r["ly_do_tra"] or "", tao_boi=r["tao_boi"] or "",
            tao_luc=r["tao_luc"], phien_ban=1))
        bid = moi.inserted_primary_key[0]
        bind.execute(phu.insert().values(id=bid, **{c: r[c] for c in PHU}))
        if r["hop_dong_id"]:
            bind.execute(hd.update().where(hd.c.id == r["hop_dong_id"], hd.c.bao_gia_id.is_(None)).values(bao_gia_id=bid))
    op.drop_table("bao_gia_doan")


def downgrade() -> None:
    op.create_table(
        "bao_gia_doan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ma", sa.String(24), nullable=False),
        *_cot_phu(),
        sa.Column("trang_thai", sa.String(14), nullable=False, server_default="nhap"),
        sa.Column("tao_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("tao_luc", sa.DateTime(), nullable=False),
        sa.Column("duyet_boi", sa.String(50), nullable=False, server_default=""),
        sa.Column("duyet_luc", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_bao_gia_doan_ma", "bao_gia_doan", ["ma"], unique=True)
    for c in ("thiet_ke_id", "thiet_ke_ma", "tai_khoan_id", "trang_thai"):
        op.create_index(f"ix_bao_gia_doan_{c}", "bao_gia_doan", [c])
    bind = op.get_bind()
    md = sa.MetaData()
    cu = sa.Table("bao_gia_doan", md, autoload_with=bind)
    dau = sa.Table("bao_gia", md, autoload_with=bind)
    phu = sa.Table("bao_gia_thiet_ke", md, autoload_with=bind)
    hd = sa.Table("hop_dong_khach", md, autoload_with=bind)
    q = sa.select(phu, dau.c.ma, dau.c.trang_thai, dau.c.tao_boi, dau.c.tao_luc, dau.c.duyet_boi,
                  dau.c.duyet_luc).join(dau, dau.c.id == phu.c.id).order_by(phu.c.id)
    for r in bind.execute(q).mappings().all():
        bind.execute(cu.insert().values(
            ma=r["ma"], trang_thai=DOI_NGUOC.get(r["trang_thai"], r["trang_thai"]), tao_boi=r["tao_boi"],
            tao_luc=r["tao_luc"], duyet_boi=r["duyet_boi"], duyet_luc=r["duyet_luc"], **{c: r[c] for c in PHU}))
        bind.execute(hd.update().where(hd.c.bao_gia_id == r["id"]).values(bao_gia_id=None))
    ids = [r[0] for r in bind.execute(sa.select(phu.c.id)).all()]
    op.drop_table("bao_gia_thiet_ke")
    if ids:
        bind.execute(dau.delete().where(dau.c.id.in_(ids)))
    op.drop_index("ix_bao_gia_nguon", table_name="bao_gia")
    with op.batch_alter_table("bao_gia") as b:
        b.drop_column("nguon")
