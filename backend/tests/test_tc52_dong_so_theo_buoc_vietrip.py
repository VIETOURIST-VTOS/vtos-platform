# -*- coding: utf-8 -*-
"""TC-52 · ĐÓNG SỐ THEO BƯỚC QUY TRÌNH VIETRIP, VÀ ĐỪNG XOÁ SỐ QUYẾT TOÁN MỖI ĐÊM.

    "co số liệu em dieu chinh giao dien cho giống màn hình thử 01"     — anh Tuấn, 17/9/2026

Đếm trên bản chạy thật ngày 17/9/2026, sau khi robot kéo đủ tới hôm nay:
  · 1.363/1.363 chuyến và 12.198/12.198 booking đã ánh xạ;
  · 558/837 bảng quyết toán có thực chi, cộng lại **57,9 tỷ giá vốn**;
  · chuyến `TH001.05010626`: doanh thu 85.190.000, giá vốn 76.890.000, pháp nhân mẹ, imported —
    **đủ cả**, mà `status = "ket_thuc"`, `closed_at = None`.
Màn hình Chủ tịch đếm 0 đồng, vì `ket_qua_that.thang()` chỉ nhận chuyến ĐÃ ĐÓNG SỐ.

Tiền đã nằm đúng chỗ, đúng pháp nhân. Thiếu đúng hai trường.

══════════════════════════════════════════════════════════════════════════════════════════════
HAI CÁI SAI CỦA VÒNG TRƯỚC, GHI LẠI ĐỂ KHÔNG LẶP
══════════════════════════════════════════════════════════════════════════════════════════════
TC-51 đoán pháp nhân là chỗ nghẽn — đọc mã rồi kết luận, không đếm số thật. Bấm cửa vá ra "0
chuyến": 984/1.000 chuyến đã có pháp nhân mẹ từ trước. Rồi lại báo "giá vốn không về được" sau khi
bốc đúng MỘT chuyến chưa nhập chi. Cả hai lần đều là kết luận cho cả tập từ một mẫu.
Bài học đã thành phép thử ở đây: mỗi luật phải nói rõ nó ĐẾM ĐƯỢC BAO NHIÊU, và số bị bỏ lại phải
hiện ra kèm lý do chứ không im lặng biến mất.

══════════════════════════════════════════════════════════════════════════════════════════════
NĂM CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. LẤY DỰ TOÁN LÀM SỐ THỰC. Bước 1–3 là dự toán, cột thực chi ở đó cộng lại vẫn ra 2,89 tỷ "lãi"
   rất đẹp. Đếm chúng là đúng cái bẫy B2/B3 của Ý kiến thẩm định 06/9/2026.
2. HẠ CẤP CHUYẾN ĐÃ QUA TAY KẾ TOÁN. `kt_xac_nhan`/`khoa` kéo ngược về `da_dong_so` là xoá một chữ ký.
3. ĐÓNG SỐ CHUYẾN CHƯA CHẠY XONG. Bảng quyết toán lập sớm được; chuyến chưa tới ngày kết thúc mà
   tính vào kết quả tháng là ghi nhận doanh thu trước khi nó tồn tại.
4. MỐC LÀ NGÀY ROBOT CHẠY. Lấy `datetime.now()` thì doanh thu tháng 6 rơi vào tháng 9 chỉ vì hôm
   nay mới đồng bộ — bài học TC-47 số 4, lần này ở phía nhập liệu.
5. **CHỖ RÒ RỈ LẶNG LẼ NHẤT** — `apply_tours` xoá trắng số quyết toán. Nhánh `else` của nó đặt
   `actual_revenue = actual_cost = 0.0` khi `settled_vietrip` false, mà hai cờ `quyetToan`/
   `duyetChi` của Vietrip false ở CẢ 1.363 bản ghi. Tour được nạp lại thì `apply_tours` chạy một
   mình (bản ghi quyết toán vẫn `applied = True`), và mỗi đêm nó lại quét sạch hai cột tiền. Không
   lỗi, không audit — chỉ là màn hình về 0 mà không ai biết vì sao.
"""
import datetime as dt
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Company, Tour, User
from app.models.vietrip import VtRecord
from app.services import ket_qua_that as KQ
from app.services import vietrip as VT

GOC = Path(__file__).resolve().parents[2]
DICH_VU = GOC / "backend" / "app" / "services" / "vietrip.py"
CUA = GOC / "backend" / "app" / "api" / "v1" / "vietrip.py"


def _doc(p: Path) -> str:
    assert p.exists(), f"Thiếu tệp {p.relative_to(GOC)}"
    return p.read_text(encoding="utf-8")


def _ma_py(s: str) -> str:
    """Bỏ chuỗi tài liệu và chú thích — canh HÀNH VI, không canh chữ trong lời giải thích (TC-41)."""
    s = re.sub(r'"""(?:.|\n)*?"""', " ", s)
    return re.sub(r"^\s*#.*$", " ", s, flags=re.M)


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


HOM_QUA = dt.date.today() - dt.timedelta(days=30)
MAI_SAU = dt.date.today() + dt.timedelta(days=30)


def _so_gia():
    """Sáu chuyến + sáu bảng quyết toán, mỗi cặp canh một chỗ hỏng ở đầu tệp."""
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    db.add(me); db.commit()
    u = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x")
    db.add(u); db.commit()

    def tour(code, status, end, rev=100.0, cost=60.0):
        t = Tour(code=code, name=code, tour_type="package", start_date=end - dt.timedelta(days=2),
                 end_date=end, operator_id=u.id, status=status, actual_revenue=rev,
                 actual_cost=cost, closed_at=None, company_id=me.id, imported=True)
        db.add(t); return t

    def bang(code, buoc):
        db.add(VtRecord(entity="settlement", vietrip_id=code, ref=code, applied=True,
                        raw={"tourcode": code, "step": f"Bước {buoc}: mô tả bước", "lines": []}))

    tour("B5", "ket_thuc", HOM_QUA);   bang("B5", 5)   # đủ bước → phải đóng số
    tour("B8", "ket_thuc", HOM_QUA);   bang("B8", 8)   # đủ bước → phải đóng số
    tour("B3", "ket_thuc", HOM_QUA);   bang("B3", 3)   # dự toán → KHÔNG đóng
    tour("KHOA", "khoa", HOM_QUA);     bang("KHOA", 8) # đã khoá → KHÔNG hạ cấp
    tour("CHUA_XONG", "da_duyet", MAI_SAU); bang("CHUA_XONG", 8)  # chưa kết thúc → KHÔNG đóng
    db.commit()
    return db, me, u


# ═════════════════ 1 · DỰ TOÁN KHÔNG PHẢI SỐ THỰC ═════════════════

def test_chi_dem_tu_buoc_5_tro_len_khong_dem_ba_buoc_du_toan():
    """Chỗ hỏng số 1."""
    assert VT.BUOC_DA_QUYET_TOAN == 5
    for b in (1, 2, 3):
        assert not VT.da_quyet_toan_tren_vietrip({"step": f"Bước {b}: Lập dự toán"}), (
            f"Bước {b} là DỰ TOÁN. Lấy dự toán làm giá vốn thì biên kế hoạch bằng biên thực tế và "
            "cảnh báo vượt dự toán không bao giờ kích hoạt (Ý kiến thẩm định 06/9/2026, B2/B3)."
        )
    for b in (5, 6, 7, 8, 9):
        assert VT.da_quyet_toan_tren_vietrip({"step": f"Bước {b}: x"}), f"Bước {b} phải tính là đã quyết toán."


def test_khong_doc_duoc_buoc_thi_tra_false_chu_khong_doan_la_xong():
    """Đoán 'chắc xong rồi' là đưa một chuyến chưa quyết toán vào kết quả của Chủ tịch."""
    for xau in (None, "", "không có số nào", "Buoc 7 không dấu"):
        assert VT.da_quyet_toan_tren_vietrip({"step": xau}) is False
    assert VT.buoc_vietrip("Bước 7: Phê duyệt Quyết toán") == 7


# ═════════════════ 2 · CHỈ NÂNG, KHÔNG HẠ ═════════════════

def test_khong_ha_cap_chuyen_da_qua_tay_ke_toan():
    """Chỗ hỏng số 2."""
    db, me, u = _so_gia()
    VT.dong_so_theo_buoc_vietrip(db)
    assert db.query(Tour).filter_by(code="KHOA").one().status == "khoa", (
        "Chuyến đã `khoa` là đã qua tay Kế toán — kéo ngược về `da_dong_so` là xoá một chữ ký."
    )


# ═════════════════ 3 · CHƯA CHẠY XONG THÌ CHƯA ĐÓNG ═════════════════

def test_khong_dong_so_chuyen_chua_toi_ngay_ket_thuc():
    """Chỗ hỏng số 3."""
    db, me, u = _so_gia()
    ra = VT.dong_so_theo_buoc_vietrip(db)
    t = db.query(Tour).filter_by(code="CHUA_XONG").one()
    assert t.status != "da_dong_so" and t.closed_at is None, (
        "Bảng quyết toán lập sớm được; chuyến chưa tới ngày kết thúc mà tính vào kết quả tháng là "
        "ghi nhận doanh thu trước khi nó tồn tại."
    )
    assert ra["bo_qua_chua_ket_thuc"] == 1


# ═════════════════ 4 · MỐC LÀ NGÀY CHUYẾN KẾT THÚC ═════════════════

def test_moc_dong_so_la_ngay_chuyen_ket_thuc_khong_phai_ngay_robot_chay():
    """Chỗ hỏng số 4."""
    db, me, u = _so_gia()
    VT.dong_so_theo_buoc_vietrip(db)
    t = db.query(Tour).filter_by(code="B5").one()
    assert t.status == "da_dong_so"
    assert t.closed_at.date() == HOM_QUA, (
        "Lấy ngày robot chạy thì doanh thu tháng 6 rơi vào tháng 9 chỉ vì hôm nay mới đồng bộ."
    )


def test_ma_nguon_khong_dat_ngay_dong_so_bang_gio_hien_tai():
    """Canh HÀNH VI: chỗ đóng số không được dùng `datetime.now()`."""
    ma = _ma_py(_doc(DICH_VU))
    khoi = ma[ma.index("def dong_so_theo_buoc_vietrip"):]
    khoi = khoi[:khoi.index("\ndef ", 10)]
    assert "datetime.now()" not in khoi, "Mốc đóng số phải là ngày chuyến kết thúc, không phải giờ chạy."


# ═════════════════ 5 · ĐỪNG XOÁ SỐ QUYẾT TOÁN MỖI ĐÊM ═════════════════

def test_apply_tours_khong_xoa_trang_doanh_thu_gia_von_cua_chuyen_da_dong_so():
    """Chỗ hỏng số 5 — chỗ rò rỉ lặng lẽ nhất của cả vòng.

    Dựng đúng tình huống thật: chuyến ĐÃ đóng số với đủ hai vế tiền, rồi Vietrip gửi lại bản ghi
    tour với `quyetToan = false` (như cả 1.363 bản ghi ngoài đời). `apply_tours` chạy một mình.
    """
    db, me, u = _so_gia()
    VT.dong_so_theo_buoc_vietrip(db)
    t = db.query(Tour).filter_by(code="B5").one()
    assert (t.status, t.actual_revenue, t.actual_cost) == ("da_dong_so", 100.0, 60.0)

    db.add(VtRecord(entity="tour", vietrip_id="9001", ref="B5", applied=False, raw={
        "recID": 9001, "tourcode": "B5", "ngayKhoiHanh": str(HOM_QUA - dt.timedelta(days=2)),
        "ngayKetThuc": str(HOM_QUA), "quyetToan": False, "duyetChi": False,
        "doanhThu": 0, "tongChiPhi": 0, "tenSanPham": "B5", "fstUser": "dh"}))
    db.commit()
    VT.apply_tours(db)

    t = db.query(Tour).filter_by(code="B5").one()
    assert t.actual_revenue == 100.0 and t.actual_cost == 60.0, (
        "apply_tours vừa quét sạch doanh thu và giá vốn lấy từ bảng quyết toán. Ngoài đời việc này "
        "lặp lại MỖI ĐÊM, không lỗi, không audit — màn hình Chủ tịch về 0 mà không ai biết vì sao."
    )
    assert t.status == "da_dong_so", "apply_tours không được hạ cấp chuyến đã đóng số về `ket_thuc`."


def test_ma_nguon_khong_con_nhanh_else_tron_xoa_hai_cot_tien():
    """Canh HÀNH VI, không canh chữ: nhánh xoá hai cột tiền phải có điều kiện trạng thái."""
    ma = _ma_py(_doc(DICH_VU))
    m = re.search(r"([^\n]*)\n\s*t\.actual_revenue = t\.actual_cost = 0\.0", ma)
    assert m, "Không tìm thấy chỗ đặt hai cột tiền về 0 — nếu đã bỏ hẳn thì sửa phép thử này."
    assert "DA_DONG_SO" in m.group(1), (
        "Nhánh đặt `actual_revenue = actual_cost = 0.0` phải loại trừ chuyến đã đóng số, "
        "không được là một `else` trơn."
    )


# ═════════════════ HAI BẢN DA_DONG_SO PHẢI KHỚP NHAU ═════════════════

def test_hai_ban_danh_sach_trang_thai_dong_so_khong_duoc_lech_nhau():
    """`vietrip.DA_DONG_SO` chép từ `ket_qua_that.DA_DONG_SO` để tránh vòng nhập khẩu.

    Chép thì phải có người canh: lệch nhau một chữ là hai nơi hiểu "đã đóng số" khác nhau, và con
    số trên màn hình khác con số trong luật đồng bộ mà không chỗ nào báo.
    """
    assert tuple(VT.DA_DONG_SO) == tuple(KQ.DA_DONG_SO)


# ═════════════════ SỐ BỊ BỎ LẠI PHẢI NHÌN THẤY ═════════════════

def test_cua_va_bao_ca_phan_dong_duoc_lan_phan_bo_lai_kem_ly_do():
    """Bài học của TC-51: đừng kết luận cho cả tập từ một mẫu — bắt cửa vá tự khai con số."""
    db, me, u = _so_gia()
    ra = VT.dong_so_theo_buoc_vietrip(db)
    assert ra["da_dong_so"] == 2                 # B5, B8
    assert ra["bo_qua_chua_du_buoc"] == 1        # B3
    assert ra["bo_qua_da_dong_roi"] == 1         # KHOA
    assert ra["bo_qua_chua_ket_thuc"] == 1       # CHUA_XONG
    assert ra["doanh_thu"] == 200.0 and ra["gia_von"] == 120.0
    lan_hai = VT.dong_so_theo_buoc_vietrip(db)
    assert lan_hai["da_dong_so"] == 0, "Bấm lại lần hai phải vô hại."


def test_cua_va_co_that_trong_api_va_co_gac_vai_tro():
    ma = _doc(CUA)
    assert "dong-so-theo-buoc" in ma, "Thiếu cửa vá POST /import/vietrip/dong-so-theo-buoc."
    khoi = ma[ma.index("dong-so-theo-buoc"):]
    khoi = khoi[:khoi.index("@router", 10)] if "@router" in khoi[10:] else khoi
    assert "require_roles" in khoi, "Cửa vá phải có gác vai trò."


# ═════════════════ PHÉP THỬ ĐẦU–CUỐI ═════════════════

def test_dong_so_xong_thi_man_hinh_chu_tich_dem_duoc_ca_hai_chuyen():
    """Lý do cả vòng này tồn tại."""
    db, me, u = _so_gia()
    ky = f"{HOM_QUA:%Y-%m}"
    truoc = KQ.thang(db, ky)
    assert (truoc["doanh_thu"] or 0) == 0, "Dựng sai số giả: trước khi vá phải chưa đếm được gì."

    VT.dong_so_theo_buoc_vietrip(db)

    sau = KQ.thang(db, ky)
    assert sau["doanh_thu"] == 200.0, "Vá xong mà màn hình vẫn trống thì cả vòng này vô nghĩa."
    assert sau["lai_tour"] == 80.0
