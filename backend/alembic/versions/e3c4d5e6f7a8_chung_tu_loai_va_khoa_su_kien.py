"""Dot E3: ngay chung tu, loai chung tu, loai nghiep vu, va khoa chong ghi so hai lan.

BON COT MOI tren `journal_entries`:
  · ngay_chung_tu  - ngay tren to chung tu, tach khoi ngay ghi so. Chung tu cu chep tu `entry_date`
                     (Chu tich chon 12/10/2026): truoc dot nay mot ngay ganh ca hai viec, nen hai
                     ngay ay dang bang nhau THAT. Chep sang khong bia ra con so nao.
  · loai_chung_tu  - PT/PC/BC/BN/HDB/HDM/PKT
  · loai_nghiep_vu - viec gi da xay ra
  · khoa_su_kien   - nguon|ma nguon|nghiep vu, CHI MUC DUY NHAT. NULL = su kien khong dinh danh
                     duoc; NULL khong va nhau trong ca SQLite lan PostgreSQL.

NAP LAI CHO DU LIEU CU - VA VI SAO NO THAN TRONG.

Neu nap khoa cho moi dong cu roi moi dung chi muc duy nhat, thi mot cap trung co san trong kho se
lam `alembic upgrade head` CHET LUC KHOI DONG HOP CHUA - dung kieu hong ma Dot LG2 da phai tra gia
mot lan voi `sa.text("0")` tren cot boolean. Nen buoc nay lam nguoc lai:

  1. chi suy nghiep vu cho 13 nguon MOT-MOT (mot su kien = mot chung tu). Ba nguon nhieu-chung-tu
     (luong, ket_chuyen, quyet_toan) KHONG suy duoc tu `source_type`, de trong.
  2. tinh khoa ung vien, roi CHI nap nhung khoa XUAT HIEN DUNG MOT LAN. Khoa trung van de NULL.
  3. dung chi muc duy nhat sau cung.

HE QUA PHAI NOI RA, khong giau: chung tu cu cua ba nguon nhieu-chung-tu va chung tu cu dang trung
nhau se khong co khoa, nen ghi lai dung su kien ay mot lan nua se KHONG bi chan. Hang rao nay chan
tu hom nay tro di. Ra soat so cu la viec rieng, co nguoi doc va co nguoi ky.

BANG NGHIEP VU CHEP VAO DAY MOT BAN, CO Y: ban di tru phai DONG BANG theo thoi diem no chay. Doc
`chung_tu_loai.NGHIEP_VU` tu day thi mot lan doi bang trong tuong lai se lam ban di tru nay chay ra
ket qua khac - va mot ban di tru doi ket qua theo thoi gian la thu khong ai do lai duoc.

Revision ID: e3c4d5e6f7a8
Revises: dl2a7c4e9b1f36
"""
from alembic import op
import sqlalchemy as sa

revision = "e3c4d5e6f7a8"
down_revision = "dl2a7c4e9b1f36"
branch_labels = None
depends_on = None

# nguon -> (nghiep vu, loai chung tu). CHI 13 nguon MOT-MOT. Dong bang 12/10/2026.
MOT_MOT = {
    "thu_tien":     ("thu_tien_khach",       "PT"),
    "bao_luu":      ("huy_bao_luu",          "PKT"),
    "hoa_don":      ("phat_hanh_hoa_don",    "HDB"),
    "de_nghi_chi":  ("de_nghi_chi",          "PKT"),
    "lenh_chi":     ("chi_tien",             "PC"),
    "khau_hao":     ("khau_hao_tscd",        "PKT"),
    "phan_bo":      ("phan_bo_tra_truoc",    "PKT"),
    "tai_chinh":    ("khe_uoc_tai_chinh",    "PKT"),
    "khe_uoc_vay":  ("khe_uoc_vay",          "PKT"),
    "so_du_dau_ky": ("so_du_dau_ky",         "PKT"),
    "kiem_toan":    ("dieu_chinh_kiem_toan", "PKT"),
    "misa":         ("chung_tu_misa",        "PKT"),
    "dao":          ("but_toan_dao",         "PKT"),
}


def upgrade() -> None:
    with op.batch_alter_table("journal_entries") as b:
        b.add_column(sa.Column("ngay_chung_tu", sa.Date(), nullable=True))
        b.add_column(sa.Column("loai_chung_tu", sa.String(length=10), nullable=False, server_default=""))
        b.add_column(sa.Column("loai_nghiep_vu", sa.String(length=40), nullable=False, server_default=""))
        b.add_column(sa.Column("khoa_su_kien", sa.String(length=200), nullable=True))

    c = op.get_bind()
    c.execute(sa.text("UPDATE journal_entries SET ngay_chung_tu = entry_date WHERE ngay_chung_tu IS NULL"))
    with op.batch_alter_table("journal_entries") as b:
        b.alter_column("ngay_chung_tu", existing_type=sa.Date(), nullable=False)

    for nguon, (nv, lct) in MOT_MOT.items():
        c.execute(sa.text("UPDATE journal_entries SET loai_nghiep_vu = :nv, loai_chung_tu = :lct "
                          "WHERE source_type = :n AND loai_nghiep_vu = ''"),
                  {"nv": nv, "lct": lct, "n": nguon})

    # Chi nap khoa cho ung vien DUY NHAT. Dung mot cau SQL thuan de chay duoc tren ca hai he.
    c.execute(sa.text("""
        UPDATE journal_entries SET khoa_su_kien =
            source_type || '|' || source_ref || '|' || loai_nghiep_vu
        WHERE loai_nghiep_vu <> ''
          AND source_ref <> ''
          AND source_ref NOT LIKE 'quy_tac:%'
          AND (source_type || '|' || source_ref || '|' || loai_nghiep_vu) IN (
                SELECT source_type || '|' || source_ref || '|' || loai_nghiep_vu
                FROM journal_entries
                WHERE loai_nghiep_vu <> '' AND source_ref <> '' AND source_ref NOT LIKE 'quy_tac:%'
                GROUP BY source_type || '|' || source_ref || '|' || loai_nghiep_vu
                HAVING COUNT(*) = 1)
    """))

    op.create_index("uq_journal_entries_khoa_su_kien", "journal_entries", ["khoa_su_kien"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_journal_entries_khoa_su_kien", table_name="journal_entries")
    with op.batch_alter_table("journal_entries") as b:
        b.drop_column("khoa_su_kien")
        b.drop_column("loai_nghiep_vu")
        b.drop_column("loai_chung_tu")
        b.drop_column("ngay_chung_tu")
