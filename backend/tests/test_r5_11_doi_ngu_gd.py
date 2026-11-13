"""R5-11 · Chủ tịch duyệt 14/11/2026: «bổ sung 2 khung này (Đội ngũ, Theo nhóm) vào bàn làm việc của GĐ KD».
Bàn GĐ đọc CẢ phòng Lẻ, cùng hàm dòng với bàn Trưởng phòng; chưa khai cơ cấu thì đọc ô nhóm bán hàng (KD1–KD5,
VPCT, chưa có nhóm) — người nhóm khác (VPHN, DOAN_*) không vào. Hai khung cao bằng nhau, khung trái kéo trượt."""
import pathlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import User
from app.services import ban_kd_le as GD
from app.services import ban_kd_vai as V

GOC = pathlib.Path(__file__).resolve().parents[2]


def _db():
    e = create_engine("sqlite://", future=True)
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e, future=True)()
    for ten, vai, nhom in (("a", "nv_kd", "KD1"), ("b", "nv_kd", "KD1"), ("c", "tn_kd", "KD2"),
                           ("d", "tp_kd", "VPCT"), ("e", "nv_kd", ""), ("x", "nv_kd", "VPHN"),
                           ("y", "nv_kd", "DOAN_OB"), ("z", "nv_dh", "KD1")):
        s.add(User(username=ten, full_name=ten.upper(), role=vai, password_hash="x", sales_group=nhom))
    s.commit()
    return s


def test_gd_doc_ca_phong_le_theo_o_nhom_ban_hang():
    s = _db()
    kq = V.doi_ngu_ca_phong(s)
    ten = {x["ho_ten"] for x in kq["doi_ngu"]}
    assert kq["nguon"] == "nhom_ban_hang"
    assert ten == {"A", "B", "C", "D", "E"}, "chỉ phòng Lẻ: KD1–KD5, VPCT, chưa có nhóm; không VPHN/Đoàn/điều hành"
    nhom = {g["ma"]: g for g in kq["theo_nhom"]}
    assert nhom["KD1"]["so_nguoi"] == 2 and "Chưa có nhóm" in nhom
    assert kq["theo_nhom"][-1]["ma"] == "Chưa có nhóm"
    # chỉ tiêu nhóm chưa giao = cộng chỉ tiêu cá nhân mặc định (R5-10)
    assert nhom["KD1"]["chi_tieu"] == sum(x["chi_tieu"] for x in kq["doi_ngu"] if x["don_vi"] == "KD1")


def test_tong_quan_gd_tra_hai_khoi():
    s = _db()
    tq = GD.tong_quan(s)
    assert {"doi_ngu", "theo_nhom", "nguon_doi_ngu"} <= set(tq)
    assert all(not x["la_toi"] for x in tq["doi_ngu"])


def test_giao_dien_hai_khung_bang_nhau_va_gd_co_khoi():
    k = (GOC / "web/components/BanKdKhung.tsx").read_text(encoding="utf-8")
    assert "export function DoiNguVaNhom" in k and ".dn-khoi{display:flex;flex-direction:column;height:520px}" in k
    assert ".dn-cuon{flex:1;min-height:0;overflow:auto" in k, "khung trái phải có thanh kéo trượt"
    assert "<DoiNguVaNhom" in (GOC / "web/components/BanGdKdLe.tsx").read_text(encoding="utf-8")
    assert "<DoiNguVaNhom" in (GOC / "web/components/BanTpKd.tsx").read_text(encoding="utf-8")
