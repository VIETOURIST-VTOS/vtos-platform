# -*- coding: utf-8 -*-
"""TC-51 · CHUYẾN NHẬP TỪ VIETRIP ĐƯỢC GẮN PHÁP NHÂN MẸ.

    "em vao vietrip de lay so lieu dua vao cho VTOS"        — anh Tuấn, 17/9/2026

Hoá ra số liệu Vietrip ĐÃ nằm trong VTOS: 1.244 chuyến, 10.303 booking, 5.948 phiếu thu, 4.815 chi
NCC, 837 bảng quyết toán — nạp ngày 05/9/2026. Mà màn hình Chủ tịch vẫn hiện Doanh thu "—".

Lý do: `ket_qua_that.thang()` lọc theo pháp nhân mẹ (TC-47, anh Tuấn chốt "chỉ Vietourist mẹ"), còn
`vietrip.apply_tours` chưa bao giờ đặt `tours.company_id` — cả 1.743 chuyến đều rỗng. Hai luật đều
đúng khi đứng một mình; đặt cạnh nhau thì chúng triệt tiêu nhau và không ai thấy vì màn hình chỉ
hiện một dấu gạch.

Anh Tuấn chốt 17/9/2026 (sáng): **tất cả tour Vietrip → Vietourist mẹ**.
Anh Tuấn chốt 17/9/2026 (chiều, TC-56): **"1 gán hết cho Vietourist Holdings, ok"** — sau khi kho
cũ nạp về và lộ ra 477/765 chuyến H1 không có pháp nhân, rơi khỏi màn hình mà không ai thấy.

══════════════════════════════════════════════════════════════════════════════════════════════
NĂM CHỖ DỄ HỎNG — MỖI PHÉP THỬ CANH ĐÚNG MỘT CHỖ
══════════════════════════════════════════════════════════════════════════════════════════════
1. CHUYẾN KHÔNG RÕ NGUỒN BỊ BỎ LẠI. (Vế cũ của chỗ này là ngược lại — xem chuỗi tài liệu của phép
   thử số 1 để đọc cả hai vế và vì sao đảo.) Kho cũ không phải Vietrip, cũng không phải ai dựng
   tay; để rỗng là để nó rơi khỏi màn hình Chủ tịch mà không ai biết.
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


# ═════════════════ 1 · GẮN HẾT, KHÔNG PHÂN BIỆT NGUỒN (TC-56 đảo luật TC-51) ═════════════════

def test_gan_het_chuyen_con_rong_ve_cong_ty_me_du_nguon_nao():
    """TC-56 · anh Tuấn chốt 17/9/2026: "1 gán hết cho Vietourist Holdings, ok".

    ══════════════════════════════════════════════════════════════════════════════════════════
    LUẬT TC-51 BỊ ĐẢO — GHI LẠI CẢ HAI VẾ
    ══════════════════════════════════════════════════════════════════════════════════════════
    TC-51 (sáng cùng ngày) cố ý chỉ gắn cho chuyến `imported = True`, lý lẽ: chuyến dựng tay trong
    VTOS phải do NGƯỜI chọn pháp nhân, gắn thay là lặng lẽ xoá mất câu hỏi "chuyến này của ai".

    Lý lẽ ấy bỏ sót trường hợp thứ ba, và nó lộ ra ngay chiều hôm đó: **kho cũ**. Chuyến nạp từ kho
    lịch sử không phải nguồn Vietrip, cũng không phải ai dựng tay — rơi đúng vào khe giữa hai
    nhánh. Đếm 17/9: 477/765 chuyến H1 không có pháp nhân, và màn hình Chủ tịch lọc theo Vietourist
    mẹ nên chúng bị lọc ra sạch, dù đã đóng số hay chưa.

    Hai ranh giới còn lại (không ghi đè · không bịa) giữ nguyên — và chúng mới là chỗ bảo vệ thật.
    """
    db, me, _ = _so_gia()
    VT.gan_phap_nhan_con_rong(db)
    assert db.query(Tour).filter_by(code="VT-RONG").one().company_id == me
    assert db.query(Tour).filter_by(code="TAY-RONG").one().company_id == me, (
        "Chuyến không rõ nguồn cũng phải về công ty mẹ. Để rỗng là để nó rơi khỏi màn hình Chủ "
        "tịch mà không ai biết — đúng chỗ 477 chuyến H1 đã rơi."
    )


# ═════════════════ 2 · KHÔNG GHI ĐÈ ═════════════════

def test_khong_ghi_de_phap_nhan_ai_da_gan_tay_du_khac_cong_ty_me():
    """Chỗ hỏng số 2."""
    db, me, con = _so_gia()
    VT.gan_phap_nhan_con_rong(db)
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
    kq = VT.gan_phap_nhan_con_rong(db)
    assert kq["da_gan"] == 0 and kq["cong_ty_me"] is None
    assert db.query(Tour).filter_by(code="VT-RONG").one().company_id is None, (
        "Không có dòng kind='me' thì để rỗng. Lùi về 'công ty đầu tiên trong bảng' là gắn cả nghìn "
        "chuyến vào một công ty bất kỳ — rỗng thì còn nhìn ra, gắn nhầm thì không."
    )


# ═════════════════ 4 · BẤM LẠI VÔ HẠI ═════════════════

def test_bam_cua_va_lan_hai_khong_gan_them_gi():
    """Chỗ hỏng số 4."""
    db, me, _ = _so_gia()
    lan1 = VT.gan_phap_nhan_con_rong(db)
    lan2 = VT.gan_phap_nhan_con_rong(db)
    assert lan1["da_gan"] == 2 and lan2["da_gan"] == 0   # VT-RONG + TAY-RONG
    assert lan1["con_rong"] == 0 and lan2["con_rong"] == 0
    # Đếm riêng theo nguồn: gắn hết KHÔNG có nghĩa là thôi không biết chuyến nào từ đâu. Con số
    # "nguồn khác" chính là thứ cho thấy kho cũ đã vào — bỏ nó đi là mất dấu vết của cả vòng này.
    assert lan1["tu_vietrip"] == 1 and lan1["nguon_khac"] == 1


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

    ══ TC-71 · 19/9/2026 — TIỀN ĐỀ ĐỔI, LUẬT GIỮ NGUYÊN ═════════════════════════════════════════
    BÊN CŨ: chuyến chưa gán pháp nhân BỊ LỌC RA khỏi con số của mẹ, nên "trước khi vá" là 0 đồng.
      Lý do cũ vẫn đáng nhớ: đoán sai pháp nhân thì mọi con số tiền là của một công ty khác, mà
      nhìn thì không khác gì số đúng.
    BÊN MỚI: anh Tuấn chốt 18/9 — "7,26 tỷ em tự gắn pháp nhân cố định cho vietourist luôn". Nên
      chuyến pháp nhân rỗng nay ĐÃ cộng vào Vietourist bằng quy tắc mặc định, và "trước khi vá"
      không còn bằng 0.

    LUẬT PHÉP THỬ NÀY CANH VẪN Y NGUYÊN, và nay chặt hơn: chuyến KHÔNG ĐƯỢC vô hình. Trước TC-71
    nó vô hình cho tới khi Hành chính gắn tay; nay nó hiện ngay, mang dấu "vào bằng quy tắc mặc
    định", và gắn tay xong thì dấu ấy MẤT ĐI. Cả hai chặng đều canh ở dưới.
    """
    db, me, _ = _so_gia()
    truoc = KQ.thang(db, "2026-08")
    assert truoc["doanh_thu"] == 200.0, (
        "TC-71: chuyến pháp nhân rỗng nay ĐÃ cộng vào Vietourist bằng quy tắc mặc định — không "
        "còn phải chờ Hành chính gắn tay mới hiện lên."
    )
    assert truoc["chua_gan_phap_nhan"] >= 1, (
        "…nhưng vẫn phải ĐẾM RIÊNG được phần vào bằng quy tắc mặc định. Một quy tắc mặc định "
        "không đếm được là quy tắc không ai kiểm tra lại được."
    )

    VT.gan_phap_nhan_con_rong(db)

    sau = KQ.thang(db, "2026-08")
    # 200 chứ không phải 100: từ TC-56 cả VT-RONG (nguồn Vietrip) lẫn TAY-RONG (nguồn khác) đều
    # được gắn về mẹ, nên cả hai cùng lên màn hình. Chính con số này là thứ TC-56 sinh ra để có.
    assert sau["doanh_thu"] == 200.0, (
        "Vá xong mà màn hình Chủ tịch vẫn trống thì cả vòng này vô nghĩa."
    )
    assert sau["lai_tour"] == 80.0
    # TC-71 · và ĐÂY mới là điều gắn pháp nhân thật sự đổi từ 19/9: con số không nhúc nhích (nó đã
    # đúng từ trước nhờ quy tắc mặc định), nhưng DẤU "vào bằng mặc định" biến mất. Đó là cách biết
    # Hành chính đã làm xong việc — nếu dấu ấy không mất thì quy tắc mặc định đang che mất phần
    # việc còn nợ, và không ai còn lý do đi gắn nữa.
    assert sau["chua_gan_phap_nhan"] == 0, (
        "Gắn pháp nhân xong thì phần 'vào bằng quy tắc mặc định' phải về 0 — quy tắc mặc định "
        "không được che mất phần việc của Hành chính."
    )
