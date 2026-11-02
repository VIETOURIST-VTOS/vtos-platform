# -*- coding: utf-8 -*-
"""MỌI CỬA NẠP HÀNG LOẠT PHẢI ĐỂ LẠI MỘT DÒNG SỔ.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO CÓ TỆP NÀY
──────────────────────────────────────────────────────────────────────────────────────────────

K5 dựng bộ đối chiếu lô nạp ngày 09/9/2026 và tự nói ra vùng mù của nó: hệ thống có MƯỜI MỘT cửa
nạp hàng loạt, đúng MỘT cửa ghi nhật ký lô. Sổ `intake_runs` có một dòng (11 bằng lái xe) trong khi
cùng tháng ấy 25.728 bút toán vào sổ qua bộ nạp MISA. Lô lớn nhất hệ thống từng có là lô mà bộ đối
chiếu lô không biết là có tồn tại.

Vòng này bịt mười cửa. `fleet.nhap_chuyen_hang_loat` để lại CỐ Ý: một làn khác đang giữ
`services/fleet.py` trong bảng giữ chỗ, và hai làn cùng sửa một tệp là đúng cái đã xoá mất việc của
nhau ngày 19/9 và 23/9.

Ba thứ tệp này canh, và thứ thứ nhất là thứ dễ mục nhất:

  1. SỔ ĐĂNG KÝ KHÔNG ĐƯỢC NÓI DỐI THEO CHIỀU NGƯỢC LẠI. `NL7` canh chiều "có cửa chưa khai"; không
     ai canh chiều "khai là CÓ ghi sổ mà thật ra không ghi". Chiều ấy nguy hơn, vì nó làm bộ đối
     chiếu im lặng đúng chỗ nó phải kêu. Ở đây đọc mã nguồn của từng cửa khai `ghi=True` và đòi
     thấy một lời gọi `ghi_lo` thật.

  2. MỘT TỆP = MỘT DÒNG SỔ. `leads.import_xlsx` gọi `import_rows`; nếu cả hai cùng ghi thì một tệp
     để lại hai dòng và bộ đối chiếu đếm đôi mọi thứ — kiểu hỏng khó thấy nhất, vì từng con số
     riêng lẻ đều đúng.

  3. GHI SỔ KHÔNG ĐƯỢC LÀM HỎNG LẦN NẠP. Nạp là việc chính, ghi sổ là việc quan sát. Một lỗi ở
     phần quan sát mà làm đổ cả lô nạp là đánh đổi sai.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import inspect                                                  # noqa: E402

from sqlalchemy import create_engine, select                    # noqa: E402
from sqlalchemy.orm import sessionmaker                         # noqa: E402

from app.db.session import Base                                 # noqa: E402
from app.models.intake import IntakeRun                         # noqa: E402
from app.services import ks_nap_lo as KNL                       # noqa: E402
from app.services import so_lo_nap as SLN                       # noqa: E402


def _db():
    co = set(Base.metadata.tables)
    dung = [t for t in Base.metadata.tables.values()
            if all(fk.target_fullname.split(".")[0] in co for fk in t.foreign_keys)]
    e = create_engine("sqlite://")
    Base.metadata.create_all(e, tables=dung)
    return sessionmaker(bind=e)()


def _lo(db) -> list[IntakeRun]:
    return list(db.execute(select(IntakeRun).order_by(IntakeRun.id)).scalars())


# ============================== 1. SỔ ĐĂNG KÝ KHÔNG NÓI DỐI ==============================
def test_nl9_cua_khai_co_ghi_so_thi_phai_that_su_ghi():
    """PHÉP THỬ QUAN TRỌNG NHẤT CỦA TỆP NÀY.

    Một dòng `True` trong sổ đăng ký là một LỜI KHAI rằng cửa ấy nằm trong tầm nhìn của bộ đối
    chiếu. Khai sai theo chiều này thì K5 thôi mở phát hiện cho cửa ấy — nó im lặng đúng chỗ phải
    kêu, và im lặng đọc giống hệt "mọi thứ ổn".
    """
    import ast
    import importlib

    def co_ghi_so(m, ham: str, sau: int = 2, da_xet=None) -> bool:
        """Cửa ghi sổ THẲNG, hoặc gọi một hàm trong cùng mô-đun ghi hộ, hoặc đi qua bộ nạp chung.

        Đi sâu HAI bậc chứ không chỉ một: hai bộ nạp danh mục MISA gọi chung `_ghi_so_danh_muc`, và
        `quyet_toan_chi_tiet.nap_lo` đi qua `intake.nap` — cả hai đều là ghi sổ thật. Không đi sâu
        thì phép thử bắt oan và người sau sẽ nới nó ra, mà một hàng rào bị nới là hàng rào đã hỏng.
        """
        da_xet = da_xet if da_xet is not None else set()
        f = getattr(m, ham, None)
        if f is None or (m.__name__, ham) in da_xet or sau < 0:
            return False
        da_xet.add((m.__name__, ham))
        ma = inspect.getsource(f)
        if "ghi_lo(" in ma or "IntakeRun(" in ma:
            return True
        cay = ast.parse(ma.lstrip())
        for n in ast.walk(cay):
            if not isinstance(n, ast.Call):
                continue
            g = n.func
            ten_goi = g.id if isinstance(g, ast.Name) else (g.attr if isinstance(g, ast.Attribute) else "")
            if not ten_goi:
                continue
            if hasattr(m, ten_goi) and co_ghi_so(m, ten_goi, sau - 1, da_xet):
                return True
            if ten_goi == "nap":            # bộ nạp chung app.services.intake
                import app.services.intake as _IN
                if co_ghi_so(_IN, "nap", sau - 1, da_xet):
                    return True
        return False

    thieu = []
    for ten, mo_dun, ghi, _ in KNL.CUA_NAP:
        if not ghi:
            continue
        ham = ten.split(".")[-1]
        m = importlib.import_module(mo_dun)
        assert getattr(m, ham, None) is not None, f"Sổ đăng ký khai {ten} nhưng {mo_dun} không có hàm ấy"
        if not co_ghi_so(m, ham):
            thieu.append(ten)
    assert not thieu, (
        f"Sổ đăng ký khai những cửa này CÓ ghi nhật ký lô nhưng mã nguồn không gọi ghi_lo: {thieu}. "
        f"Khai sai theo chiều này làm bộ đối chiếu K5 thôi kêu ở đúng chỗ nó phải kêu.")


def test_nl9_chi_con_dung_mot_cua_ngoai_so_va_no_duoc_goi_ten():
    """Cửa còn lại phải được gọi tên, không để một con số trần.

    Nếu ngày mai ai đó bịt nốt cửa đội xe thì phép thử này đỏ và người ấy sửa một dòng — rẻ. Còn
    nếu có ai lặng lẽ thêm một cửa mới KHÔNG ghi sổ thì nó cũng đỏ, và đó mới là lý do chính.
    """
    con = [c["cua"] for c in KNL.cua_khong_ghi_so()]
    # `nha_hang.hien_hang_loat` (SUA-3, 02/11/2026): NL7 bắt nó theo tên `*_hang_loat`, nhưng nó KHÔNG nạp số
    # liệu — chỉ bật/tắt cờ hiện trên cổng của nhiều nhà hàng; mỗi nhà hàng đi qua bat_hien, có nhật ký
    # từng dòng. Không có lô nào để ghi sổ, nên đứng ngoài sổ là đúng chứ không phải chưa bịt.
    assert con == ["fleet.nhap_chuyen_hang_loat", "nha_hang.hien_hang_loat"], (
        f"Danh sách cửa ngoài sổ đã đổi: {con}. Thêm cửa mới thì bịt nó, hoặc ghi rõ vì sao chưa.")


# ============================== 2. BỐN CON SỐ PHẢI CỘNG LẠI ĐƯỢC ==============================
def test_nl9_ghi_lo_tu_khai_khi_bon_con_so_khong_cong_lai_duoc():
    """Đẳng thức `so_dong = da_nap + bo_qua + loi` chính là phép K5 sẽ chạy.

    Nói ra ngay tại chỗ ghi thì người sửa biết CỬA NÀO khai thiếu; để K5 phát hiện sau thì nó chỉ
    biết là lô số mấy lệch.
    """
    db = _db()
    SLN.ghi_lo(db, loai="thu", so_dong=10, da_nap=4, bo_qua_da_co=2, dong_loi=1)
    r = _lo(db)[0]
    assert "canh_bao_dang_thuc" in r.ket_qua, "Bốn con số lệch mà sổ không nói gì"
    db2 = _db()
    SLN.ghi_lo(db2, loai="thu", so_dong=7, da_nap=4, bo_qua_da_co=2, dong_loi=1)
    assert "canh_bao_dang_thuc" not in _lo(db2)[0].ket_qua, "Cộng đúng mà vẫn bị cảnh báo"


def test_nl9_o_tien_de_trong_khac_han_so_khong():
    """RỖNG = không đo được. 0 = đo được và bằng không.

    `ks_nap_lo.bon_so_tien` phân biệt đúng hai thứ đó, nên điền 0 cho một cửa không đo được tiền sẽ
    làm nó báo thiếu tiền ở MỌI lô đi qua cửa ấy — và một bảng ngoại lệ toàn báo sai là bảng không
    ai đọc nữa.
    """
    db = _db()
    SLN.ghi_lo(db, loai="khong_co_tien", so_dong=3, da_nap=3)
    SLN.ghi_lo(db, loai="co_tien", so_dong=3, da_nap=3, tong_tien_tep=0,
               tong_tien_da_nap=0, tong_tien_bo_qua=0, tong_tien_loi=0)
    a, b = _lo(db)
    assert a.tong_tien_tep is None and KNL.bon_so_tien(a) is None
    assert b.tong_tien_tep is not None and KNL.bon_so_tien(b) is not None


# ============================== 3. GHI SỔ KHÔNG LÀM HỎNG LẦN NẠP ==============================
def test_nl9_ghi_so_hong_thi_nuot_loi_chu_khong_do_ca_lo_nap():
    db = _db()
    class KhongJsonHoaDuoc:
        def __repr__(self): raise RuntimeError("no")
    # đầu vào bẩn đủ kiểu: loại quá dài, số không phải số, vật thể không json hoá được
    assert SLN.ghi_lo(db, loai="x" * 200, so_dong="ba", da_nap=1) is None
    assert SLN.ghi_lo(db, loai="y", so_dong=1, da_nap=1, ket_qua={"x": KhongJsonHoaDuoc()}) is None


def test_nl9_bam_noi_dung_de_tra_loi_duoc_dung_tep_nao():
    """Mã băm trả lời “lần nạp hôm đó đúng là tệp này chứ không phải tệp đã sửa sau đó”."""
    import hashlib
    db = _db()
    SLN.ghi_lo(db, loai="a", so_dong=1, da_nap=1, dau_vao=b"noi dung tep")
    SLN.ghi_lo(db, loai="a2", so_dong=1, da_nap=1, dau_vao=b"noi dung tep DA SUA")
    SLN.ghi_lo(db, loai="b", so_dong=1, da_nap=1, dau_vao=[{"x": 1}])
    SLN.ghi_lo(db, loai="c", so_dong=1, da_nap=1)
    a, a2, b, c = _lo(db)
    # Băm phải phụ thuộc NỘI DUNG, không chỉ "có sinh ra 64 ký tự". Băm hằng một chuỗi rỗng cũng
    # dài 64 ký tự và cũng khác nhau giữa hai kiểu đầu vào — nên phải so đúng hai tệp KHÁC NỘI DUNG.
    assert a.dau_vao_hash == hashlib.sha256(b"noi dung tep").hexdigest()
    assert a.dau_vao_hash != a2.dau_vao_hash, "Sửa tệp mà mã băm không đổi thì nó không trả lời được gì"
    assert len(b.dau_vao_hash) == 64 and b.dau_vao_hash != a.dau_vao_hash
    assert c.dau_vao_hash == "", "Không có đầu vào thì để trống, đừng băm chuỗi rỗng cho có"


# ============================== 4. CHẠY THẬT MỘT CỬA ==============================
def test_nl9_nap_lead_de_lai_dung_mot_dong_so_dung_bon_con_so():
    from app.services import leads as LD
    db = _db()
    rows = [{"phone": "0900000001", "name": "A", "channel": "Zalo"},
            {"phone": "0900000002", "name": "B", "channel": "Zalo"},
            {"phone": "", "name": "Thiếu số", "channel": "Zalo"}]
    kq = LD.import_rows(db, "kt", rows)
    ds = _lo(db)
    assert len(ds) == 1, f"Một lượt nạp phải để lại đúng một dòng sổ, có {len(ds)}"
    r = ds[0]
    assert r.so_dong == 3
    assert r.da_nap == kq["new"] + kq["updated"]
    assert r.dong_loi == kq["n_errors"]
    assert r.so_dong == r.da_nap + r.bo_qua_da_co + r.dong_loi, "Bốn con số không cộng lại được"
    assert r.tong_tien_tep is None, "Lead không mang tiền – ô tiền phải để TRỐNG"


def test_nl9_mot_tep_lead_chi_de_lai_MOT_dong_so_du_di_qua_hai_ham():
    """`import_xlsx` gọi `import_rows`. Hai chỗ cùng ghi thì một tệp thành hai lô."""
    from io import BytesIO
    from openpyxl import Workbook
    from app.services import leads as LD
    wb = Workbook(); ws = wb.active
    ws.append(["SĐT", "Tên khách", "Kênh"])
    ws.append(["0900000011", "A", "Zalo"])
    ws.append(["0900000012", "B", "Facebook"])
    buf = BytesIO(); wb.save(buf)

    db = _db()
    LD.import_xlsx(db, "kt", buf.getvalue())
    ds = _lo(db)
    assert len(ds) == 1, f"Một tệp phải để lại đúng MỘT dòng sổ, có {len(ds)}: {[x.loai for x in ds]}"
    assert ds[0].loai == "lead_nhap_excel"
    assert ds[0].so_dong == 2 and ds[0].da_nap == 2


def test_nl9_goi_thang_import_rows_thi_van_ghi_so():
    """Nửa còn lại của phép trên: `ghi_so=False` chỉ dành cho lời gọi từ `import_xlsx`. Nếu ai đó
    đặt mặc định thành False thì cửa API nạp lead lại rơi ra ngoài sổ trong im lặng."""
    from app.services import leads as LD
    db = _db()
    LD.import_rows(db, "kt", [{"phone": "0900000021", "name": "A", "channel": "Zalo"}])
    assert len(_lo(db)) == 1
