# -*- coding: utf-8 -*-
"""P1-03 · gói nhà hàng có điều kiện cấu trúc (Chủ tịch duyệt bản xem trước 09/11/2026).

  1. Khung giờ áp dụng + số khách tối đa: ngoài khung / quá số thì máy chặn gửi.
  2. Tuổi tính giá trẻ em: dưới mốc miễn phí, trên mốc tính người lớn; gói có khung tuổi thì bắt ghi tuổi.
  3. Phụ thu có số (theo khách / theo bàn, theo ngày, «khách tự chọn") cộng vào tạm tính; cọc 10% / 50% tính
     trên tạm tính đã gồm phụ thu.
  4. Gói gọi món: cọc cố định mỗi khách, không có «trả đủ»; gọi món không có phụ thu theo đầu khách.
  5. Hạn nhà hàng trả lời: đơn ghi hạn; quá hạn mà chưa nhận thì báo quá hạn (đơn KHÔNG tự hủy).
  6. Ô trống = không kiểm (gói cũ bán như trước).
"""
import datetime as dt

import pytest

from tests.test_dt2_dat_ban import NAY, NGAY, _dat, _td, _u, db  # noqa: F401


def _sua(s, loai="set", **f):
    from app.services import nha_hang as N
    td = _td(s, loai)
    goc = {"ten": td.ten, "loai": td.loai, "gia_nguoi_lon": td.gia_nguoi_lon, "gia_tre_em": td.gia_tre_em}
    N.luu_thuc_don(s, _u(s, "nvdh"), td.nha_hang_id, {**goc, **f}, td.id)
    # sửa gói làm nhà hàng tự tắt → bật lại như TP Điều hành
    from app.models.nha_hang import NhaHang
    n = s.get(NhaHang, td.nha_hang_id)
    n.hien_cong, n.tat_ly_do = True, ""
    s.commit()
    return td


def test_o_trong_ban_nhu_cu(db):
    d = _dat(db, nl=2, te=1)
    assert int(d.tam_tinh) == 450000 * 2 + 225000 and d.phu_thu is None and d.han_phan_hoi is None


def test_khung_gio_va_toi_da(db):
    from app.services import dat_ban as S
    _sua(db, gio_tu="11:00", gio_den="14:00", so_khach_toi_da=6)
    with pytest.raises(S.LoiDatBan, match="11:00–14:00"):
        _dat(db, gio="18:30")
    with pytest.raises(S.LoiDatBan, match="tối đa 6"):
        _dat(db, nl=5, te=2, gio="12:00", tuoi_tre=[5, 6])
    assert _dat(db, nl=4, gio="14:00").trang_thai == "cho_nhan"


def test_tuoi_tre_em(db):
    from app.services import dat_ban as S
    _sua(db, tuoi_te_tu=4, tuoi_te_den=11)
    with pytest.raises(S.LoiDatBan, match="tuổi từng trẻ"):
        _dat(db, nl=2, te=3)
    d = _dat(db, nl=2, te=3, tuoi_tre=[2, 8, 13])          # 1 miễn phí · 1 trẻ em · 1 tính người lớn
    assert int(d.tam_tinh) == 450000 * 3 + 225000 and d.tuoi_tre == [2, 8, 13]


def test_phu_thu_cong_vao_tam_tinh_va_coc(db):
    le = NGAY.isoformat()
    _sua(db, phu_thu=[{"ten": "Lễ", "so_tien": 100000, "theo": "khach", "tu_ngay": le, "den_ngay": le},
                      {"ten": "Phòng riêng", "so_tien": 500000, "theo": "ban", "tu_chon": True},
                      {"ten": "Ngày khác", "so_tien": 999000, "theo": "ban", "tu_ngay": "2020-01-01", "den_ngay": "2020-01-02"}])
    d = _dat(db, nl=2)
    assert int(d.tam_tinh) == 900000 + 200000 and [x["ten"] for x in d.phu_thu] == ["Lễ"]
    assert int(d.phai_tra_truoc) == 110000                  # cọc 10% trên tạm tính đã gồm phụ thu
    d2 = _dat(db, tk="0901000002", nl=2, phu_thu_chon=[1])
    assert int(d2.tam_tinh) == 900000 + 200000 + 500000


def test_goi_mon_coc_co_dinh(db):
    from app.services import nha_hang as N
    _sua(db, "goi_mon", gia_nguoi_lon=None, coc_moi_khach=100000,
         phu_thu=[{"ten": "Phòng riêng", "so_tien": 300000, "theo": "ban", "tu_chon": True}])
    d = _dat(db, loai="goi_mon", nl=4, te=2, cach="du", phu_thu_chon=[0])
    assert d.cach_tt == "coc" and int(d.phai_tra_truoc) == 100000 * 6 + 300000
    with pytest.raises(N.LoiNhaHang, match="chỉ có phụ thu theo bàn"):
        _sua(db, "goi_mon", coc_moi_khach=100000, phu_thu=[{"ten": "Lễ", "so_tien": 50000, "theo": "khach"}])
    with pytest.raises(N.LoiNhaHang, match="chỉ dùng cho gói gọi món"):
        _sua(db, coc_moi_khach=100000)


def test_han_phan_hoi_qua_han_khong_tu_huy(db):
    from app.services import dat_ban as S
    _sua(db, han_phan_hoi_gio=4)
    d = _dat(db)
    assert d.han_phan_hoi == NAY + dt.timedelta(hours=4)
    assert not S.ra(db, d, NAY + dt.timedelta(hours=3), noi_bo=True)["qua_han_phan_hoi"]
    r = S.ra(db, d, NAY + dt.timedelta(hours=5), noi_bo=True)
    assert r["qua_han_phan_hoi"] and r["trang_thai"] == "cho_nhan"


def test_kiem_o_nhap_crm(db):
    from app.services import nha_hang as N
    with pytest.raises(N.LoiNhaHang, match="giờ kết thúc phải sau"):
        _sua(db, gio_tu="14:00", gio_den="11:00")
    with pytest.raises(N.LoiNhaHang, match="ghi đủ «từ» và «đến»"):
        _sua(db, tuoi_te_tu=4)
    td = _sua(db, gio_tu="11:00", gio_den="14:00", so_khach_toi_da=30)
    td = _sua(db, gio_tu="", gio_den="", so_khach_toi_da=None)   # Điều hành xóa ô → bỏ kiểm
    db.refresh(td)
    assert td.gio_tu == "" and td.so_khach_toi_da is None


# ── giao diện: luồng 4 bước như trang đặt khách sạn ─────────────────────────────────────────────
def _web(*p):
    import os
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return open(os.path.join(goc, "web", *p), encoding="utf-8").read()


def test_cong_bon_buoc():
    s = _web("components", "cong", "NhaHangAgoda.tsx")
    assert '["Chọn bàn", "Thông tin", "Thanh toán", "Xác nhận"]' in s
    for toi in (2, 3, 4):
        assert f"<BuocDat toi={{{toi}}} />" in s
    assert "Thông tin đã điền sẵn từ tài khoản của bạn" in s                  # lời chào điền sẵn
    assert "Yêu cầu đặc biệt" in s and "Ghế trẻ em" in s                        # ô chọn
    assert "QR chuyển khoản ngân hàng" in s and "VISA" in s                     # phương thức
    assert "Quyền lợi của bạn" in s and "Tích điểm VTD" in s
    assert "tuoi_tre:" in s and "phu_thu_chon:" in s                            # gửi tuổi trẻ + phụ thu tự chọn
    assert "Hôm nay chưa trừ tiền" in s                                         # vẫn: nhà hàng nhận rồi mới trả


def test_crm_o_nhap_va_qua_han():
    s = _web("app", "nha-hang", "page.tsx")
    for k in ("gio_tu", "so_khach_toi_da", "tuoi_te_tu", "han_phan_hoi_gio", "coc_moi_khach", "+ Thêm phụ thu", "Khách tự chọn"):
        assert k in s, k
    assert "Quá hạn nhà hàng trả lời" in _web("app", "dat-ban-nha-hang", "page.tsx")
