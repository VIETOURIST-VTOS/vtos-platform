"""KS-19 (Chủ tịch duyệt bản xem trước v1.3, 05/11/2026): giá đã gồm 8% VAT, chỉ hiện khách sạn còn phòng,
«Phù hợp cho» + tiện nghi phòng cho bộ lọc, máy tính km tới trung tâm từ tọa độ."""
import pytest

from tests.test_at1_am_thuc import db, _u  # noqa: F401
from tests.test_ks13_khach_san_vtd import HN, RA, VAO, _ks, _mo_ban  # noqa: F401


def test_ks19_1_phu_hop_tien_nghi_va_km(db):
    from app.services import khach_san_vtd as S
    k = _ks(db, "Khách sạn Biển Xanh")
    lp, g, _x = _mo_ban(db, k)
    lp.tien_nghi = ["Ban công", "Hướng biển"]
    S.luu_ks(db, _u(db, "dh"), {"ten": k.ten, "tinh_thanh": "Đà Nẵng", "sao": 4, "mo_ta": k.mo_ta,
                                "phu_hop": ["gia_dinh", "cap_doi"], "thue_phi_pt": 10, "thue_phi_xac_nhan": True}, k.id)
    with pytest.raises(S.LoiKhachSan, match="Phù hợp"):
        S.luu_ks(db, _u(db, "dh"), {"ten": k.ten, "tinh_thanh": "Đà Nẵng", "sao": 4, "mo_ta": k.mo_ta, "phu_hop": ["xx"]}, k.id)
    k.vi_do, k.kinh_do, k.km_trung_tam = 16.0678, 108.2408, None      # ~2 km phía đông tâm Đà Nẵng
    db.commit()
    o = S.tim(db, "Đà Nẵng", VAO, RA, 2, 0, 1, hom_nay=HN)["khach_san"][0]
    assert o["phu_hop"] == ["Gia đình có trẻ nhỏ", "Cặp đôi"] and o["tien_nghi_phong"] == ["Ban công", "Hướng biển"]
    assert o["vat_pt"] == 8 and o["thue_phi_pt"] == 0 and 1.8 <= o["km_trung_tam"] <= 2.4
    k.km_trung_tam = 5.0; db.commit()                                  # Điều hành ghi tay thì dùng số ghi tay
    assert S.tim(db, "Đà Nẵng", VAO, RA, 2, 0, 1, hom_nay=HN)["khach_san"][0]["km_trung_tam"] == 5.0


def test_ks19_2_vat_nam_trong_gia(db):
    from app.services import khach_san_vtd as S
    assert S.vat_trong(8_470_000) == 627_407 and S.vat_trong(0) == 0


def test_ks19b_goi_ban_cung_mot_offer_va_du_phong_moi_dem(db):
    from app.services import khach_san_vtd as S
    k = _ks(db, "Khách sạn Biển Xanh")
    lp, g, _x = _mo_ban(db, k)                                          # 3 phòng, gói có bữa sáng + hủy miễn phí
    lp.tien_nghi = ["Ban công", "Không hút thuốc"]; db.commit()
    o = S.tim(db, "Đà Nẵng", VAO, RA, 2, 0, 1, hom_nay=HN)["khach_san"][0]
    gb = o["goi_ban"]
    assert len(gb) == 1 and gb[0]["goi"] == g.id and gb[0]["bua_sang"] and gb[0]["mien_phi_huy"] and gb[0]["khong_hut"]
    assert gb[0]["tong"] == 3_800_000 and gb[0]["dem_gia"] == round(3_800_000 / 3)
    o2 = S.tim(db, "Đà Nẵng", VAO, RA, 4, 0, 2, hom_nay=HN)["khach_san"][0]["goi_ban"][0]
    assert o2["tong"] == 7_600_000 and o2["dem_gia"] == round(3_800_000 / 3)     # giá lọc tính trên 1 phòng / 1 đêm
    # cần 4 phòng mà loại phòng chỉ còn 3 ở các đêm → không có offer → khách sạn không hiện
    assert S.tim(db, "Đà Nẵng", VAO, RA, 4, 0, 4, hom_nay=HN)["khach_san"] == []
