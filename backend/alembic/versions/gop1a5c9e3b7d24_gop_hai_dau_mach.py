"""GOP HAI DAU MACH - QT-1 va E5 cung moc vao e4a1b2c3d4e5

VI SAO CO BAN VA NAY. Hai lan viet song song, moi lan dat `down_revision = "e4a1b2c3d4e5"`, va ca
hai da merge vao main. Tu luc do chuoi ban va co HAI head:

    e4a1b2c3d4e5
      |-- qt1f3a8c6e2b94   (QT-1 - quyet toan chuyen Mau 2)
      '-- e5b1c2d3e4f5     (E5  - phan bo tien ra)

Container khoi dong chay `alembic upgrade head`. Co hai head thi lenh ay BAO LOI va dung:
"Multiple head revisions are present". Nghia la ban dung tiep theo khong len duoc, va khong lan nao
tu thay vi tren cay cua rieng minh van chi co mot head.

VI SAO GOP CHU KHONG DOI SO HIEU MOT BEN. Doi `down_revision` cua mot trong hai ban de xep noi
duoi ban kia thi nghe gon hon, nhung may chu that CO THE DA CHAY mot trong hai - va luc ay bang
alembic_version dang giu so hieu ay. Doi chuoi duoi chan mot ban DA CHAY la lam cho alembic khong
con tim thay duong di tu diem no dang dung. Ban gop thi an toan du may chu dang o dau: khong so
hieu nao bi doi, chi them mot diem hoi tu.

BAN NAY KHONG DUNG VAO DU LIEU. Khong tao bang, khong them cot, khong sua dong nao. No chi la mot
cai nut noi hai nhanh lai.

Revision ID: gop1a5c9e3b7d24
Revises: qt1f3a8c6e2b94, e5b1c2d3e4f5
"""

revision = "gop1a5c9e3b7d24"
down_revision = ("qt1f3a8c6e2b94", "e5b1c2d3e4f5")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Khong lam gi: day la diem hoi tu, khong phai mot thay doi luoc do."""


def downgrade() -> None:
    """Khong lam gi - go nut noi thi hai nhanh tu tach lai nhu cu."""
