# -*- coding: utf-8 -*-
"""TC-51 · CHUYẾN NHẬP TỪ VIETRIP ĐƯỢC GẮN PHÁP NHÂN MẸ.

    "em vao vietrip de lay so lieu dua vao cho VTOS"        — anh Tuấn, 17/9/2026

Hoá ra số liệu Vietrip ĐÃ nằm trong VTOS: 1.244 chuyến, 10.303 booking, 5.948 phiếu thu, 4.815 chi
NCC, 837 bảng quyết toán — nạp ngày 05/9/2026. Mà màn hình Chủ tịch vẫn hiện Doanh thu "—".

Lý do: `ket_qua_that.thang()` lọc theo pháp nhân mẹ (TC-47, anh Tuấn chốt "chỉ Vietourist mẹ"), còn
`vietrip.apply_tours` chưa bao giờ đặt `tours.company_id` — cả 1.743 chuyến đều rỗng. Hai luật đều
đúng khi đứng một mình; đặt cạnh nhau thì chúng triệt tiêu nhau và không ai thấy vì màn hình chỉ
hiện một dấu gạch.

Anh Tuấn chốt 17/9/2026: **tất cả tour Vietrip → Vietourist mẹ**.

══════════════════════════════════════════════════════════════════════════════════════════════
NĂM CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. GẮN LAN SANG CHUYẾN DỰNG TAY. Luật chung của `tours.company_id` vẫn là "rỗng nghĩa là CHƯA XÁC
   ĐỊNH, không mặc định về mẹ". Vòng này chỉ mở ngoại lệ cho chuyến NGUỒN VIETRIP. Gắn luôn cả
   chuyến người ta dựng tay trong VTOS là lặng lẽ xoá mất câu hỏi "chuyến này của ai".
2. GHI ĐÈ PHÁP NHÂN NGƯỜI TA GẮN TAY. Ai đó gán một chuyến Vietrip cho công ty con là đã có chủ ý.
   Robot chạy đêm ghi đè về mẹ thì sáng ra số đã đổi mà không ai biết — và lần sau lại đổi tiếp.
3. BỊA PHÁP NHÂN KHI DANH MỤC CHƯA CÓ MẸ. Lùi về "công ty đầu tiên trong bảng" là gắn 1.743 chuyến
   vào một công ty bất kỳ. Thà để rỗng — rỗng thì còn nhìn ra, gắn nhầm thì không.
4. VÁ MỘT LẦN RỒI CHẠY LẠI THÀNH NHÂN ĐÔI. Cửa vá phải bấm lại được mà không sinh hậu quả.
5. VÁ XONG MÀ MÀN HÌNH VẪN TRỐNG. Đây là phép thử ĐẦU–CUỐI, và là lý do cả vòng tồn tại: gắn pháp
   nhân xong thì `ket_qua_that.thang()` phải ĐẾM ĐƯỢC chuyến ấy. Bốn phép thử trên đều xanh mà
   phép này đỏ thì vòng này vô nghĩa.
"""
import datetime as dt
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.core import Company, Tour, User
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
    """Kho rỗng trong bộ nhớ, dựng ĐÚNG những bảng khai được — cùng cách với TC-44/45/46/47."""
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _so_gia(co_me: bool = True):
    """Bốn chuyến, mỗi chuyến canh một chỗ hỏng ở đầu tệp."""
    db = _db()
    me = Company(code="VTD", name="Vietourist Holdings", kind="me", active=True)
    con = Company(code="VTR", name="Vận tải Vietrip", kind="con", active=True)
    db.add_all(([me] if co_me else []) + [con])
    db.commit()
    u = User(username="dh", full_name="Điều hành", role="nv_dh", password_hash="x")
    db.add(u)
    db.commit()

    def them(code, imported, cid, rev=100.0, cost=60.0, status="da_dong_so"):
        db.add(Tour(code=code, name=code, tour_type="package",
                    start_date=dt.date(2026, 8, 1), end_date=dt.date(2026, 8, 3),
                    operator_id=u.id, status=status, actual_revenue=rev, actual_cost=cost,
                    closed_at=dt.datetime(2026, 8, 10), company_id=cid, imported=imported))

    them("VT-RONG", True, None)          # chuyến Vietrip chưa gán → phải được gắn
    them("VT-DA-GAN", True, con.id)      # chuyến Vietrip đã gắn tay cho con → PHẢI ĐỂ YÊN
    them("TAY-RONG", False, None)        # chuyến dựng tay chưa gán → PHẢI ĐỂ YÊN
    db.commit()
    return db, (me.id if co_me else None), con.id


# ═════════════════ 1 · CHỈ CHUYẾN NGUỒN VIETRIP ═════════════════

def test_chi_gan_chuyen_nhap_tu_vietrip_khong_dung_den_chuyen_dung_tay():
    """Chỗ hỏng số 1."""
    db, me, _ = _so_gia()
    VT.gan_phap_nhan_vietrip(db)
    assert db.query(Tour).filter_by(code="VT-RONG").one().company_id == me
    assert db.query(Tour).filter_by(code="TAY-RONG").one().company_id is None, (
        "Chuyến dựng tay trong VTOS vẫn phải do NGƯỜI chọn pháp nhân. Luật 'tất cả tour Vietrip → "
        "mẹ' chỉ áp cho chuyến nguồn Vietrip; gắn lan sang chuyến dựng tay là lặng lẽ xoá mất câu "
        "hỏi 'chuyến này của ai'."
    )


# ═════════════════ 2 · KHÔNG GHI ĐÈ ═════════════════

def test_khong_ghi_de_phap_nhan_ai_da_gan_tay_du_khac_cong_ty_me():
    """Chỗ hỏng số 2."""
    db, me, con = _so_gia()
    VT.gan_phap_nhan_vietrip(db)
    assert db.query(Tour).filter_by(code="VT-DA-GAN").one().company_id == con, (
        "Chuyến Vietrip đã được gắn tay cho công ty con phải GIỮ NGUYÊN. Robot ghi đè về mẹ thì "
        "sáng ra số đã đổi mà không ai biết, và đêm sau lại đổi tiếp."
    )


def test_ma_nguon_kiem_rong_bang_is_none_chu_khong_bang_tinh_dung_sai():
    """Canh HÀNH VI: chỗ gắn pháp nhân phải kiểm `is None`.

    `not t.company_id` đúng với mọi id hiện có, nhưng nó cũng đúng với id 0 — ngày nào đó có một
    công ty id 0 thì robot ghi đè mất pháp nhân người ta gắn tay, và phép thử trên vẫn xanh vì số
    giả không bao giờ dùng id 0. Cấm cái biểu thức, đừng đợi tình huống ấy xảy ra.
    """
    ma = _ma_py(_doc(DICH_VU))
    assert not re.search(r"not\s+t\.company_id", ma), (
        "`not t.company_id` đọc id 0 thành rỗng. Dùng `t.company_id is None`."
    )
    assert re.search(r"t\.company_id\s+is\s+None", ma), (
        "Chỗ gắn pháp nhân phải kiểm rỗng bằng `is None`."
    )


# ═════════════════ 3 · KHÔNG BỊA ═════════════════

def test_danh_muc_chua_co_phap_nhan_me_thi_khong_gan_gi_ca():
    """Chỗ hỏng số 3."""
    db, me, _ = _so_gia(co_me=False)
    assert me is None
    assert VT.phap_nhan_mac_dinh(db) is None
    kq = VT.gan_phap_nhan_vietrip(db)
    assert kq["da_gan"] == 0 and kq["cong_ty_me"] is None
    assert db.query(Tour).filter_by(code="VT-RONG").one().company_id is None, (
        "Không có dòng kind='me' thì để rỗng. Lùi về 'công ty đầu tiên trong bảng' là gắn cả nghìn "
        "chuyến vào một công ty bất kỳ — rỗng thì còn nhìn ra, gắn nhầm thì không."
    )


# ═════════════════ 4 · BẤM LẠI VÔ HẠI ═════════════════

def test_bam_cua_va_lan_hai_khong_gan_them_gi():
    """Chỗ hỏng số 4."""
    db, me, _ = _so_gia()
    lan1 = VT.gan_phap_nhan_vietrip(db)
    lan2 = VT.gan_phap_nhan_vietrip(db)
    assert lan1["da_gan"] == 1 and lan2["da_gan"] == 0
    assert lan1["con_rong"] == 0 and lan2["con_rong"] == 0


def test_cua_va_co_that_trong_api_va_chi_mo_cho_vai_tro_dong_bo():
    """Cửa vá phải TỒN TẠI — không thì luật này chỉ áp cho chuyến nhập từ mai trở đi.

    1.743 chuyến đã nhập đều `applied = True`, nên vòng đồng bộ kế tiếp không đi qua chúng nữa.
    """
    ma = _doc(CUA)
    assert "repair-phap-nhan" in ma, "Thiếu cửa vá một lần POST /import/vietrip/repair-phap-nhan."
    khoi = ma[ma.index("repair-phap-nhan"):]
    khoi = khoi[:khoi.index("@router", 10)] if "@router" in khoi[10:] else khoi
    assert "require_roles" in khoi, "Cửa vá phải có gác vai trò, không để mở cho mọi người dùng."


# ═════════════════ 5 · PHÉP THỬ ĐẦU–CUỐI ═════════════════

def test_gan_phap_nhan_xong_thi_man_hinh_chu_tich_dem_duoc_chuyen_ay():
    """Chỗ hỏng số 5 — lý do cả vòng này tồn tại.

    Trước khi vá, `thang()` đếm 0 đồng dù chuyến đã đóng số và có đủ doanh thu/giá vốn: nó bị lọc
    ra vì chưa thuộc pháp nhân nào. Sau khi vá, đúng chuyến ấy phải hiện lên.
    """
    db, me, _ = _so_gia()
    truoc = KQ.thang(db, "2026-08")
    assert (truoc["doanh_thu"] or 0) == 0, (
        "Dựng sai số giả: chuyến phải BỊ LỌC RA trước khi vá, không thì phép thử này không chứng "
        "minh được gì."
    )
    assert truoc["chua_gan_phap_nhan"] >= 1, (
        "Chuyến chưa gán pháp nhân phải được ĐẾM RIÊNG chứ không biến mất — luật pham_vi_phap_nhan "
        "số 2: không gộp im lặng, cũng không giấu."
    )

    VT.gan_phap_nhan_vietrip(db)

    sau = KQ.thang(db, "2026-08")
    assert sau["doanh_thu"] == 100.0, (
        "Vá xong mà màn hình Chủ tịch vẫn trống thì cả vòng này vô nghĩa."
    )
    assert sau["lai_tour"] == 40.0
