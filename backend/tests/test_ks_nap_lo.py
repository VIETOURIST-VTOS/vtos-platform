"""K5 – đối chiếu tệp đã tải với số đã vào sổ. Lệnh Robot Kiểm soát 08/9/2026.

Nghiệm thu theo lệnh: "nạp thử một tệp có dòng lỗi và dòng trùng, phép đối chiếu ra đúng bốn con số
và khớp". NL3 làm đúng việc đó bằng một tệp thật đi qua cửa nạp thật, không dựng sẵn dòng IntakeRun.

  NL1  bốn con số DÒNG phải cộng lại bằng số dòng trong tệp; lệch thì mở ngoại lệ ĐỎ kèm mã lô
  NL2  bốn con số TIỀN cũng vậy – bắt được cái mà đếm dòng mù: dòng vào đủ nhưng sai số tiền
  NL3  nghiệm thu: tệp thật có dòng lỗi + dòng trùng → bốn số dòng và bốn số tiền đều khớp
  NL4  lô KHÔNG đo được tiền trả None, không trả 0 – "chưa đo" khác "đo được và bằng không"
  NL5  chỉ cộng cột CHẮC CHẮN là tiền; số lít, km không được lọt vào tổng tiền
  NL6  cửa nạp hàng loạt không ghi nhật ký lô thì bộ đối chiếu phải TỰ NÓI RA vùng mù của mình
  NL7  sổ đăng ký cửa nạp không được lạc hậu trong im lặng – soi mã nguồn tìm cửa mới chưa khai
  NL8  đã gắn vào vòng quét của robot
"""
import os, sys, io, csv
from datetime import datetime, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_ksnaplo.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_ksnaplo.db", "test_ksnaplo.db-journal"):
    if os.path.exists(f): os.remove(f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        yield


def _lo(**kw):
    """Dựng một dòng nhật ký lô. Dùng cho NL1/NL2/NL4 – nơi cần dựng đúng một tình huống lệch."""
    from app.db.session import SessionLocal
    from app.models.intake import IntakeRun
    db = SessionLocal()
    r = IntakeRun(loai=kw.pop("loai", "nha_cung_cap"), ten_tep="thu.csv", boi="chutich",
                  luc=datetime.now(), **kw)
    db.add(r); db.commit(); db.refresh(r); rid = r.id; db.close()
    return rid


def _tim(ds, ma_dau):
    return [x for x in ds if x["ma"].startswith(ma_dau)]


def test_nl1_bon_so_dong_khong_cong_lai_dung_thi_mo_ngoai_le_do():
    """Lệch nghĩa là có dòng không nằm trong ô nào cả – nó không vào bảng, không bị đánh lỗi, không bị
    coi là trùng. Đó đúng là 'mất dòng giữa đường mà không ai biết'."""
    from app.services import ks_nap_lo as NL
    from app.db.session import SessionLocal
    rid = _lo(so_dong=100, da_nap=90, bo_qua_da_co=5, dong_loi=2)   # thiếu 3
    db = SessionLocal()
    ds = _tim(NL.quet(db), f"nap_lo_lech_dong#{rid}")
    assert len(ds) == 1, "lệch số dòng phải mở đúng một ngoại lệ"
    assert ds[0]["muc"] == "do", "mất dòng trong lô nạp là mức ĐỎ"
    assert str(rid) in ds[0]["tom_tat"], "phải kèm mã lô, nếu không thì không ai tra ngược được"
    assert ds[0]["chi_tiet"]["dong"]["lech"] == 3
    db.close()

    khop = _lo(so_dong=100, da_nap=90, bo_qua_da_co=8, dong_loi=2)  # đủ 100
    db = SessionLocal()
    assert not _tim(NL.quet(db), f"nap_lo_lech_dong#{khop}"), "cộng lại đúng thì không được báo gì"
    db.close()


def test_nl2_bon_so_tien_bat_duoc_cai_ma_dem_dong_mu():
    """Số dòng khớp hoàn hảo, tiền thì bốc hơi. Đây chính là lý do phải đếm cả tiền."""
    from app.services import ks_nap_lo as NL
    from app.db.session import SessionLocal
    rid = _lo(so_dong=10, da_nap=10, bo_qua_da_co=0, dong_loi=0,
              tong_tien_tep=500_000_000, tong_tien_da_nap=300_000_000,
              tong_tien_bo_qua=0, tong_tien_loi=0, cot_tien=["thanh_tien"])
    db = SessionLocal()
    ds = NL.quet(db)
    assert not _tim(ds, f"nap_lo_lech_dong#{rid}"), "số dòng khớp thì không báo lệch dòng"
    t = _tim(ds, f"nap_lo_lech_tien#{rid}")
    assert len(t) == 1 and t[0]["muc"] == "do"
    assert t[0]["chi_tiet"]["tien"]["lech"] == 200_000_000
    db.close()


def test_nl3_nghiem_thu_tep_that_co_dong_loi_va_dong_trung():
    """Tiêu chí nghiệm thu của lệnh giao việc, chạy qua CỬA NẠP THẬT chứ không dựng sẵn dòng nhật ký.

    Tệp bốn dòng: hai dòng hợp lệ, một dòng trùng dòng đầu, một dòng thiếu tên (lỗi).
    """
    from app.services import intake as I, ks_nap_lo as NL
    from app.db.session import SessionLocal
    db = SessionLocal()
    rows = [
        {"ten": "KS Nghiệm Thu K5 A", "loai": "khach_san", "ma_so_thue": "0311111111"},
        {"ten": "KS Nghiệm Thu K5 B", "loai": "khach_san", "ma_so_thue": "0322222222"},
        {"ten": "KS Nghiệm Thu K5 A", "loai": "khach_san", "ma_so_thue": "0311111111"},  # trùng dòng 1
        {"ten": "", "loai": "khach_san"},                                               # lỗi: thiếu tên
    ]
    kq = I.nap(db, "nha_cung_cap", rows, "chutich", bo_qua_dong_loi=True, ten_tep="nghiem_thu_k5.csv")
    db.commit()
    from app.models.intake import IntakeRun
    r = db.get(IntakeRun, kq["run_id"])

    d = NL.bon_so_dong(r)
    assert d["trong_tep"] == 4
    assert d["da_nap"] == 2, f"hai dòng hợp lệ phải vào sổ: {d}"
    assert d["lech"] == 0, f"bốn con số phải cộng lại bằng số dòng trong tệp: {d}"
    assert not _tim(NL.quet(db), f"nap_lo_lech_dong#{r.id}")

    # Dòng trùng NẰM TRONG CÙNG MỘT TỆP được xếp là dòng lỗi, không phải "đã có". Bộ kiểm trước khi
    # ghi chỉ đối chiếu với CƠ SỞ DỮ LIỆU, nên hai dòng giống nhau trong cùng tệp đều qua được; dòng
    # thứ hai bị chặn lúc ghi.
    #
    # Đã cân nhắc coi đây là lỗi và sửa lại thành "đã có". Không sửa, vì hai lý do: đẳng thức đối chiếu
    # vẫn đúng (dòng không biến mất – đó là điều K5 gác), và người nạp CẦN thấy dòng ấy. "Bỏ qua vì
    # trùng" là chuyện bình thường không ai đọc; "tệp của bạn có hai dòng cùng một nhà cung cấp" là
    # chuyện họ nên biết, vì thường là dấu hiệu tệp nguồn sai chứ không phải nạp lại.
    #
    # Điều PHẢI đúng là nó không được biến mất trong im lặng – nên chốt lại ở đây.
    loi = [k for k in kq["dong"] if k["loi"]]
    assert len(loi) == 2, f"dòng trùng và dòng thiếu tên đều phải hiện ra: {loi}"
    assert any("Đã có nhà cung cấp" in " ".join(k["loi"]) for k in loi), \
        "dòng trùng phải nói rõ trùng với ai, không được chỉ báo 'ghi không thành công'"
    db.close()


def test_nl4_lo_khong_do_duoc_tien_tra_none_chu_khong_tra_0():
    """Ép 'chưa đo' thành 0 thì mọi lô đi qua đường nạp theo lô đều bị báo thiếu tiền, và một bảng
    ngoại lệ toàn báo sai là bảng không ai đọc."""
    from app.services import ks_nap_lo as NL
    from app.db.session import SessionLocal
    from app.models.intake import IntakeRun
    rid = _lo(so_dong=5, da_nap=5, tong_tien_tep=90_000_000)   # chỉ biết tổng tệp
    db = SessionLocal()
    r = db.get(IntakeRun, rid)
    assert NL.bon_so_tien(r) is None, "không đủ dữ kiện thì trả None, không suy ra 0"
    assert not _tim(NL.quet(db), f"nap_lo_lech_tien#{rid}"), "không đo được thì KHÔNG được báo lệch"
    # còn lô hoàn toàn không có số tiền nào cũng vậy
    rid2 = _lo(so_dong=3, da_nap=3)
    assert NL.bon_so_tien(db.get(IntakeRun, rid2)) is None
    db.close()


def test_nl5_chi_cong_cot_chac_chan_la_tien_khong_cong_so_lit_va_km():
    """Cộng nhầm số lít vào tổng tiền thì con số đối chiếu vô nghĩa – và vô nghĩa một cách âm thầm."""
    from app.services import intake as I
    tien, chua_ro = I.cot_tien_cua_bo("chuyen_xe")
    assert "tien_dau" in tien and "doanh_thu" in tien and "cong_tac_phi" in tien
    for x in ("so_lit", "km_dau", "km_cuoi"):
        assert x not in tien, f"“{x}” không phải tiền mà lại được cộng vào tổng tiền"
    # cột chưa rõ phải được NÊU RA, không im lặng bỏ qua
    assert set(chua_ro) & {"so_lit", "km_dau", "km_cuoi", "cau_duong", "giu_xe"}, \
        "cột số chưa xếp loại phải hiện ra để người quyết, thay vì biến mất"


def test_nl6_bo_doi_chieu_phai_tu_noi_ra_vung_mu_cua_no():
    """Một bộ đối chiếu chỉ kiểm những lô tự giác đăng ký là một bộ đối chiếu đi vòng được.

    Trên hệ thống thật ngày 09/9/2026: nhật ký lô có ĐÚNG MỘT dòng (11 dòng bằng lái xe), trong khi
    cùng tháng 25.728 bút toán đã vào sổ qua bộ nạp MISA – một cửa không ghi nhật ký lô.

    SỬA NGÀY 30/9/2026, và ghi ra vì sao: bản đầu của phép thử này đòi đích danh
    `misa.import_journal` phải nằm trong danh sách vùng mù. Ngày ấy đòi thế là đúng – nó là lô lớn
    nhất và đang thật sự ngoài sổ. Nhưng một phép thử khoá cứng vào TÌNH TRẠNG HÔM ẤY thì đến ngày
    người ta SỬA được nó, phép thử đỏ lên như thể việc sửa là một lỗi. Nay phép thử đòi đúng cái
    luật nó sinh ra để giữ: mỗi cửa còn ngoài sổ PHẢI được gọi tên, và danh sách trên màn hình phải
    khớp từng chữ với sổ đăng ký. Còn bao nhiêu cửa ngoài sổ là việc của `test_nl9`.
    """
    from app.services import ks_nap_lo as NL
    from app.db.session import SessionLocal
    db = SessionLocal()
    ds = _tim(NL.quet(db), "nap_lo_khong_so#")
    cua = {x["doi_tuong"] for x in ds}
    ngoai_so = {c["cua"] for c in NL.cua_khong_ghi_so()}
    assert cua == ngoai_so, (
        f"Ngoại lệ mở ra không khớp sổ đăng ký: quét ra {cua}, sổ khai {ngoai_so}. Lệch nghĩa là "
        f"có cửa ngoài sổ mà robot không mở việc cho nó – đúng vùng mù mà bộ kiểm này sinh ra để nói.")
    b = NL.bang(db)
    assert b["cua_khong_ghi_so"], "màn hình cũng phải thấy phần không che được, không chỉ ngoại lệ"
    db.close()


def test_nl7_so_dang_ky_cua_nap_khong_duoc_lac_hau_trong_im_lang():
    """Soi mã nguồn tìm cửa nạp hàng loạt CHƯA khai trong sổ đăng ký.

    Việc soi đặt ở phép thử chứ không ở máy chủ: một bộ kiểm soát đi quét mã nguồn lúc chạy thật là
    thứ hỏng theo cách khó hiểu khi đường dẫn tệp đổi. Ở đây thì hỏng là thấy ngay.
    """
    import re, pathlib
    from app.services.ks_nap_lo import CUA_NAP
    goc = pathlib.Path(__file__).resolve().parents[1] / "app" / "services"
    da_khai = {c.split(".")[-1] for c, _, _, _ in CUA_NAP}
    # tên hàm gợi ý nạp hàng loạt: import_*, *_hang_loat, nap_lo*
    moi = []
    for f in goc.glob("*.py"):
        if f.name.startswith("ks_"): continue
        for ten in re.findall(r'^def (import_[a-z_]+|[a-z_]*hang_loat|nap_lo[a-z_]*)\(',
                              f.read_text(encoding="utf-8"), re.M):
            if ten not in da_khai: moi.append(f"{f.stem}.{ten}")
    assert not moi, ("Có cửa nạp hàng loạt chưa khai trong CUA_NAP của ks_nap_lo.py. Khai vào đó kèm "
                     f"việc nó CÓ ghi nhật ký lô hay không, để bộ đối chiếu biết vùng mù của mình: {moi}")


def test_nl8_da_gan_vao_vong_quet_cua_robot():
    from app.services.ks_robot import BO_KIEM
    from app.services.ks_nap_lo import _doi_chieu_lo_nap
    assert _doi_chieu_lo_nap in BO_KIEM, "bộ kiểm không nằm trong vòng quét thì nó không tồn tại"
    from app.models.kiem_soat import LOAI_PHAT_HIEN
    for k in ("nap_lo_lech", "nap_lo_ngoai_so"):
        assert k in LOAI_PHAT_HIEN, f"loại phát hiện “{k}” chưa khai – màn hình sẽ hiện mã thô"
