"""V9 đợt 1 – tám cột tiền chạm sổ kế toán đổi sang số thập phân.

Nghiệm thu V9 đòi hai điều, và bộ test này canh cả hai:

    "bộ kiểm K1 giảm ĐÚNG số cột đã sửa"           – không nhiều hơn, không ít hơn
    "tổng phát sinh mọi tài khoản trước–sau KHÔNG LỆCH MỘT ĐỒNG"

Điều thứ hai có một cái bẫy mà bộ test phải tránh: một hàm so sánh luôn trả về "khớp" cũng làm mọi
phép thử xanh. Nên ở đây có phép thử NGƯỢC – dựng một chênh lệch đúng một đồng và đòi bộ đối chiếu
phải kêu lên. Một bộ đối chiếu không phát hiện được cái sai thì việc nó nói "khớp" chẳng chứng minh
điều gì.

Và một điều nữa phải nói thẳng trong chính bộ test, vì nó dễ bị đọc nhầm thành "V9 đã xong": đợt này
đổi CỘT TRONG CƠ SỞ DỮ LIỆU, Python vẫn nhận float. Có phép thử ghi rõ điều đó để người sau không
tưởng số học phía Python đã thành số thập phân.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v9.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, Float, Numeric
from app.main import app

# Tám cột của đợt 1, viết thẳng ra ở đây LẦN THỨ BA (mô hình, bản nâng cấp, bộ test). Cố ý lặp: ba
# chỗ cùng liệt kê thì lệch nhau là phép thử đỏ ngay, còn một chỗ khai chung thì cả ba cùng sai theo.
DOT1 = {
    ("journal_lines", "debit"), ("journal_lines", "credit"),
    ("invoices", "pre_tax"), ("invoices", "vat"), ("invoices", "total"),
    ("receipts", "amount"), ("bank_transactions", "amount"), ("payment_requests", "amount"),
}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def _cot(bang: str, cot: str):
    from app.db.session import Base
    return Base.metadata.tables[bang].columns[cot]


# ====================== 1. ĐÚNG TÁM CỘT, KHÔNG THỪA KHÔNG THIẾU ======================
def test_dung_tam_cot_da_doi_sang_so_thap_phan():
    for bang, cot in DOT1:
        assert isinstance(_cot(bang, cot).type, Numeric), f"{bang}.{cot} chưa đổi"
        assert not isinstance(_cot(bang, cot).type, Float), f"{bang}.{cot} vẫn là số thực nhị phân"


def test_khong_doi_nham_cot_khong_phai_tien():
    """vat_rate là TỶ LỆ (0,08), không phải tiền. Đổi nhầm một cột không phải tiền cũng tốn đúng một
    lần nâng cấp cơ sở dữ liệu."""
    assert isinstance(_cot("invoices", "vat_rate").type, Float)


def test_moi_cot_tien_doi_dung_18_2():
    for bang, cot in DOT1:
        t = _cot(bang, cot).type
        assert (t.precision, t.scale) == (18, 2), f"{bang}.{cot} = {t.precision},{t.scale}"


def test_python_van_nhan_float_va_dieu_do_la_co_y():
    """Đợt này đổi chỗ SỐ NẰM, chưa đổi số học phía Python. Ghi thành phép thử để người sau không
    tưởng V9 đã xong – nửa thứ hai (bật Decimal theo từng phân hệ) CÒN NỢ."""
    from app.models.kieu_tien import TIEN
    assert TIEN.asdecimal is False
    for bang, cot in DOT1:
        assert _cot(bang, cot).type.asdecimal is False


def _mig(ten: str):
    import importlib.util, pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / ten
    spec = importlib.util.spec_from_file_location(ten, p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_mo_hinh_va_ban_nang_cap_khong_duoc_lech_nhau():
    """Mô hình và bản nâng cấp cùng liệt kê danh sách cột. Lệch nhau là bản nâng cấp đổi một tập, mô
    hình khai một tập khác – và cơ sở dữ liệu THẬT sẽ không giống mô hình mà không ai biết. Đây là
    kiểu sai chỉ lộ ra khi có người đi tìm một con số không khớp, tức là quá muộn."""
    from app.db.session import Base
    from sqlalchemy import Numeric, Float
    d1 = _mig("v9a1d6b4f8c02_v9_dot1_cot_tien_so_ke_toan.py")
    d2 = _mig("v9b2e7c3a91d5_v9_dot2_tour_va_doi_xe.py")
    assert {(b, c) for b, c, _ in d1.COT} == DOT1
    for m in (d1, d2):
        assert (m.TIEN.precision, m.TIEN.scale) == (18, 2)
    # Hợp của MỌI bản nâng cấp phải bằng đúng tập cột đã khai kiểu số thập phân trong mô hình.
    #
    # Kể cả bản SINH MỚI cột, không chỉ hai bản CHUYỂN KIỂU của V9. Ngày 09/9/2026 làn Kiểm soát thêm
    # bốn cột tiền cho lô nạp (intake_runs) và khai thẳng kiểu Numeric(18,2) – đúng chuẩn V9, không
    # phải chuyển kiểu vì sinh ra đã đúng. Phép thử khi ấy đọc là "mô hình đã đổi mà không có bản
    # nâng cấp", một câu báo động sai.
    #
    # Chỗ này lộ ra một điều đáng nhớ hơn cả bản vá: phép thử đỏ từ hôm qua mà không ai thấy, vì cây
    # làm việc trên máy Chủ tịch thiếu đúng tệp mô hình ấy nên mọi lần chạy đều dùng bản cũ. Một cây
    # làm việc lùi sau commit thì bộ phép thử vẫn xanh – và cái xanh ấy không nói gì về mã đang chạy.
    #
    # Ngay 09/9/2026, dot K1 chuyen tiep 47 cot tien con kieu Float sang Numeric(18,2). Phep thu nay lai
    # do - lan nay DUNG: no dang noi "mo hinh da doi 47 cot ma ban nang cap khong co trong danh sach".
    # Ban nang cap CO, chi la cho nay chua doc toi. Bai hoc lap lai lan hai: danh sach ban nang cap phai
    # noi theo moi dot, neu khong phep thu canh cua lai thanh phep thu canh chinh no.
    # LẦN THỨ TƯ phép thử này đỏ vì cùng một lý do, và lần này sửa theo đúng việc còn tồn đã ghi ở
    # trên: KHÔNG liệt kê tay từng bản nâng cấp nữa. Hàm `cot_tien_trong_moi_ban_nang_cap()` đọc cả
    # thư mục versions và tự tìm mọi cột kiểu tiền, nên thêm bảng mới không còn làm phép thử đỏ oan.
    #
    # Ba lần trước đều đỏ vì người thêm cột quên nới danh sách. Nhắc nhau "nhớ nới" đã chứng minh là
    # không có tác dụng – ba lần trong hai ngày. Việc phải làm là bỏ hẳn cái danh sách phải nới.
    trong_mig = cot_tien_trong_moi_ban_nang_cap()
    # CHỈ cột TIỀN, tức Numeric(18,2). Cột Numeric khác độ chính xác KHÔNG phải tiền và cố ý như vậy –
    # tỷ giá là Numeric(18,4) vì bốn chữ số lẻ là độ chính xác ngân hàng công bố. Chính
    # app/models/kieu_tien.py đã dặn: "Không dùng cho tỷ lệ, hệ số, số lượng, hay số đo". Gộp chúng
    # vào đây là kéo phép thử canh cột tiền đi canh cả những cột không phải tiền.
    trong_mo_hinh = {(t.name, c.name) for t in Base.metadata.tables.values() for c in t.columns
                     if isinstance(c.type, Numeric) and not isinstance(c.type, Float)
                     and (c.type.precision, c.type.scale) == (18, 2)}
    assert trong_mig >= trong_mo_hinh, {
        "mo hinh da doi ma khong co ban nang cap": sorted(trong_mo_hinh - trong_mig)}


def cot_tien_trong_moi_ban_nang_cap() -> set[tuple[str, str]]:
    """Đọc THƯ MỤC versions và trả về mọi (bảng, cột) mang kiểu tiền do bản nâng cấp tạo hoặc đổi.

    Vì sao đọc bằng cây cú pháp chứ không nhập tệp: nhập 80 bản nâng cấp là chạy mã của chúng, và
    nhiều bản gọi tới `op` vốn chỉ có nghĩa trong ngữ cảnh alembic đang chạy thật.

    Bốn hình dạng khai cột tiền có thật trong kho này, và hàm bắt cả bốn:

        op.create_table("t", sa.Column("c", TIEN), ...)
        op.add_column("t", sa.Column("c", TIEN))
        for ten, kieu in DANH_SACH: op.add_column("t", sa.Column(ten, kieu))   <- w1a2b3c4d5e6
        COT = [("t", "c", ...), ...]                                            <- các bản V9/K1
        with op.batch_alter_table("t") as b: b.add_column(sa.Column("c", TIEN))  <- nt1c4f7b2e8a

    Kiểu được coi là TIỀN khi nó viết là `TIEN` hoặc `sa.Numeric(18, 2)` / `Numeric(18, 2)`. Đây là
    quy ước đã dùng suốt kho, xem app/models/kieu_tien.py.
    """
    import ast
    from pathlib import Path

    thu_muc = Path(__file__).resolve().parent.parent / "alembic" / "versions"

    def la_tien(nut) -> bool:
        if isinstance(nut, ast.Name):
            return nut.id == "TIEN"
        if isinstance(nut, ast.Attribute):
            return nut.attr == "TIEN"
        if isinstance(nut, ast.Call):
            f = nut.func
            ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if ten != "Numeric":
                return False
            so = [a.value for a in nut.args if isinstance(a, ast.Constant)]
            return so[:2] == [18, 2]
        return False

    def chu(nut):
        return nut.value if isinstance(nut, ast.Constant) and isinstance(nut.value, str) else None

    kq: set[tuple[str, str]] = set()
    for tep in thu_muc.glob("*.py"):
        try:
            cay = ast.parse(tep.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        # Hằng số cấp mô-đun, để giải được vòng lặp `for ten, kieu in DANH_SACH`.
        hang: dict[str, ast.AST] = {}
        for n in cay.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                hang[n.targets[0].id] = n.value

        def ten_tu_danh_sach_chuoi(nut):
            """("a", "b", ...) -> ["a", "b", ...]. Rỗng nếu không phải danh sách chuỗi thuần."""
            if isinstance(nut, ast.Name):
                nut = hang.get(nut.id)
            if not isinstance(nut, (ast.List, ast.Tuple)):
                return []
            ten = [chu(x) for x in nut.elts]
            return ten if ten and all(ten) else []

        def cap_tu_danh_sach(nut):
            """[(ten, kieu), ...] -> những tên cột mang kiểu tiền."""
            if isinstance(nut, ast.Name):
                nut = hang.get(nut.id)
            if not isinstance(nut, (ast.List, ast.Tuple)):
                return []
            ra = []
            for phan_tu in nut.elts:
                if isinstance(phan_tu, ast.Tuple) and len(phan_tu.elts) >= 2:
                    ten = chu(phan_tu.elts[0])
                    if ten and la_tien(phan_tu.elts[1]):
                        ra.append(ten)
            return ra

        for nut in ast.walk(cay):
            # Hình 1 và 2: gọi thẳng op.create_table / op.add_column với tên bảng là chuỗi.
            if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute) \
                    and nut.func.attr in ("create_table", "add_column") and nut.args:
                bang = chu(nut.args[0])
                if not bang:
                    continue
                for tham_so in nut.args[1:]:
                    if isinstance(tham_so, ast.Call) and getattr(tham_so.func, "attr", "") == "Column" \
                            and len(tham_so.args) >= 2:
                        ten = chu(tham_so.args[0])
                        if ten and la_tien(tham_so.args[1]):
                            kq.add((bang, ten))

            # Hình 3: vòng lặp trên một danh sách (ten, kieu), thân gọi add_column với bảng là chuỗi.
            if isinstance(nut, ast.For):
                cot = cap_tu_danh_sach(nut.iter)
                if cot:
                    for con in ast.walk(nut):
                        if isinstance(con, ast.Call) and con.args:
                            bang = chu(con.args[0])
                            if bang:
                                kq.update((bang, c) for c in cot)
                    continue

                # Hình 3b: vòng lặp trên danh sách CHUỖI thuần – tên cột ở danh sách, kiểu nằm trong
                # thân vòng lặp: `for c in COT: op.add_column("t", sa.Column(c, sa.Numeric(18,2)))`.
                ten_cot = ten_tu_danh_sach_chuoi(nut.iter)
                if not ten_cot:
                    continue
                for con in ast.walk(nut):
                    if isinstance(con, ast.Call) and isinstance(con.func, ast.Attribute) \
                            and con.func.attr in ("create_table", "add_column") and con.args:
                        bang = chu(con.args[0])
                        if not bang:
                            continue
                        for tham_so in con.args[1:]:
                            if isinstance(tham_so, ast.Call) \
                                    and getattr(tham_so.func, "attr", "") == "Column" \
                                    and len(tham_so.args) >= 2 and la_tien(tham_so.args[1]):
                                kq.update((bang, c) for c in ten_cot)

            # Hình 5: `with op.batch_alter_table("t") as b: b.add_column(sa.Column("c", TIEN))`.
            #
            # Thêm 27/9/2026, khi hàng rào này báo đỏ cho bản nâng cấp `nt1c4f7b2e8a` (bốn ô ngoại
            # tệ của đề nghị chi). Bản ấy KHÔNG sai: `batch_alter_table` là cách đúng để bảng đã tạo
            # chịu được cả SQLite (máy lập trình) lẫn PostgreSQL (máy chạy thật) — chính bản
            # `ch1f5a8d3e6b` trước đó cũng dùng, chỉ là nó không thêm cột TIỀN nào nên hàng rào
            # chưa gặp hình này bao giờ.
            #
            # Cách sửa SAI mà người sau dễ chọn: đổi bản nâng cấp sang `op.add_column` thẳng cho
            # hàng rào im. Làm thế là để cái LỖ y nguyên — bản nâng cấp sau dùng batch sẽ lại đỏ, và
            # lần ấy người ta nới danh sách bỏ qua. Dạy hàng rào ĐỌC ĐƯỢC hình thứ năm không phải là
            # nới: nó nhìn thấy NHIỀU hơn trước, không phải ít hơn.
            #
            # Tên bảng nằm ở `batch_alter_table("t")`, còn `add_column` bên trong KHÔNG mang tên
            # bảng — nên hình 1/2 ở trên (đọc `nut.args[0]` làm tên bảng) không bắt được.
            if isinstance(nut, ast.With):
                bang = None
                for muc in nut.items:
                    g = muc.context_expr
                    if isinstance(g, ast.Call) and getattr(g.func, "attr", "") == "batch_alter_table" \
                            and g.args:
                        bang = chu(g.args[0])
                if not bang:
                    continue
                for con in ast.walk(nut):
                    if isinstance(con, ast.Call) and getattr(con.func, "attr", "") == "add_column" \
                            and con.args:
                        for tham_so in con.args:
                            if isinstance(tham_so, ast.Call) \
                                    and getattr(tham_so.func, "attr", "") == "Column" \
                                    and len(tham_so.args) >= 2:
                                ten = chu(tham_so.args[0])
                                if ten and la_tien(tham_so.args[1]):
                                    kq.add((bang, ten))

        # Hình 4: hằng số COT = [(bang, cot, kieu), ...] của các đợt chuyển kiểu V9/K1.
        for ten_hang, gia_tri in hang.items():
            if not ten_hang.startswith("COT"):
                continue
            if not isinstance(gia_tri, (ast.List, ast.Tuple)):
                continue
            for phan_tu in gia_tri.elts:
                if isinstance(phan_tu, ast.Tuple) and len(phan_tu.elts) >= 2:
                    a, b = chu(phan_tu.elts[0]), chu(phan_tu.elts[1])
                    if a and b:
                        kq.add((a, b))
    return kq


def test_hai_ban_nang_cap_khong_doi_trung_mot_cot():
    """Đổi hai lần một cột thì lần sau chạy trên kiểu đã đổi – không hỏng, nhưng là dấu hiệu hai đợt
    đang chồng lấn, và đợt sau sẽ khó nói mình đã đổi bao nhiêu cột."""
    d1 = _mig("v9a1d6b4f8c02_v9_dot1_cot_tien_so_ke_toan.py")
    d2 = _mig("v9b2e7c3a91d5_v9_dot2_tour_va_doi_xe.py")
    a = {(b, c) for b, c, _ in d1.COT}
    b_ = {(b, c) for b, c, _ in d2.COT}
    assert not (a & b_), f"trùng giữa hai đợt: {sorted(a & b_)}"


def test_dot2_lay_dung_nhom_tour_va_doi_xe():
    """Đợt 2 lấy nhóm SINH RA con số của sổ: giá bán, giá vốn, tiền booking, quyết toán, và toàn bộ
    tiền của đội xe. Không lấy lan sang nhóm khác – lan là đợt sau không còn đo được mình làm gì."""
    d2 = _mig("v9b2e7c3a91d5_v9_dot2_tour_va_doi_xe.py")
    KHOI = ("tour", "booking", "product", "service_", "fleet_", "vehicle_", "dispatch_")
    la = [f"{b}.{c}" for b, c, _ in d2.COT if not b.startswith(KHOI)]
    assert not la, f"cột ngoài nhóm tour/đội xe: {la}"
    assert len(d2.COT) == 48


def test_khong_doi_nham_so_do_va_ty_le_cua_doi_xe():
    """Lít dầu, ki lô mét, ngày công, tỷ lệ – không phải tiền. K1 đã tách riêng, và đổi nhầm chúng
    cũng tốn đúng một lần nâng cấp cơ sở dữ liệu."""
    from sqlalchemy import Float
    for bang, cot in (("fleet_trip_costs", "lit"), ("tour_cost_lines", "qty"),
                      ("tour_cost_lines", "coef"), ("companies", "ownership_pct")):
        assert isinstance(_cot(bang, cot).type, Float), f"{bang}.{cot} bị đổi nhầm"


# ====================== 2. BỘ KIỂM K1 GIẢM ĐÚNG TÁM ======================
def test_K1_giam_dung_so_cot_da_sua(db):
    """Nghiệm thu V9: "bộ kiểm K1 giảm ĐÚNG số cột đã sửa" – không nhiều hơn, không ít hơn.

    Đếm theo tập hợp chứ không theo con số: một phép thử đòi "K1 còn đúng 40" thì mỗi lần thêm một
    bảng mới có cột tiền là nó đỏ, và cách nhanh nhất để làm xanh là sửa con số 40 thành 41 mà không
    ai nhìn cột mới đó là gì."""
    from app.services import ks_cot_tien as CT
    from app.db.session import Base
    from sqlalchemy import Numeric, Float
    CT.dong_bo(db); CT.nap_quyet_dinh(db); db.flush()
    rows = CT._hieu_luc(db)
    da_doi_mo_hinh = {(t.name, c.name) for t in Base.metadata.tables.values() for c in t.columns
                      if isinstance(c.type, Numeric) and not isinstance(c.type, Float)}
    con_float = {(r.bang, r.cot) for r in rows if r.xep() == "tien" and r.kieu == "Float"}
    assert not (con_float & da_doi_mo_hinh), \
        f"K1 vẫn coi là Float những cột đã đổi: {sorted(con_float & da_doi_mo_hinh)[:5]}"
    # Và các cột đã đổi phải CÒN trong sổ rà soát với kiểu mới – không phải biến mất khỏi sổ, vì
    # biến mất là hết đo được và người đọc tưởng đã xong.
    trong_so = {(r.bang, r.cot) for r in rows if r.kieu == "Numeric"}
    assert da_doi_mo_hinh <= trong_so, f"thiếu khỏi sổ rà soát: {sorted(da_doi_mo_hinh - trong_so)[:5]}"
    assert DOT1 <= da_doi_mo_hinh


# ====================== 3. TỔNG TRƯỚC – SAU ======================
def _but_toan(db, ngay, lines):
    from app.services import accounting as ACC
    from app.models.core import User
    u = db.execute(select(User).where(User.role == "ketoan")).scalars().first()
    for l in lines:
        l.setdefault("partner_code", "DT-V9"); l.setdefault("partner", "Đối tượng thử")
        l.setdefault("project_code", "TOUR-V9")
    return ACC.post_entry(db, u.username, u.role, date.fromisoformat(ngay), "thử V9", lines,
                          "thu_cong", f"v9:{ngay}:{lines[0]['account']}:{lines[0].get('debit', 0)}")


def test_tong_theo_tai_khoan_khop_tuyet_doi_qua_mot_vong_ghi_doc(db):
    """Ghi vào rồi đọc ra, tổng phải khớp tuyệt đối – kể cả với số lẻ hàng đồng."""
    from app.services import v9_doi_chieu as DC
    _but_toan(db, "2026-02-10", [{"account": "131", "debit": 12_345_678},
                                 {"account": "5113", "credit": 12_345_678}])
    _but_toan(db, "2026-02-11", [{"account": "632", "debit": 7_654_321},
                                 {"account": "331", "credit": 7_654_321}])
    db.flush()
    a = DC.chup(db)
    tk = a["theo_tai_khoan"]
    assert tk["131"]["no"] == 12_345_678, tk["131"]
    assert tk["632"]["no"] == 7_654_321, tk["632"]
    # Sổ phải cân: tổng Nợ = tổng Có trên toàn bộ tài khoản.
    assert round(sum(v["no"] for v in tk.values()) - sum(v["co"] for v in tk.values()), 2) == 0


def test_bo_doi_chieu_PHAT_HIEN_DUOC_lech_mot_dong(db):
    """Phép thử ngược, và là phép thử quan trọng nhất của tệp này.

    Một hàm so sánh luôn trả 'khớp' cũng làm mọi phép thử khác xanh. Nếu bộ đối chiếu không kêu lên
    được khi lệch đúng một đồng thì việc nó nói 'khớp' chẳng chứng minh điều gì."""
    from app.services import v9_doi_chieu as DC
    truoc = {"cot": {"journal_lines.debit": {"tong": 1_000_000.0, "so_dong": 10,
                                             "so_dong_co_le_duoi_dong": 0}},
             "theo_tai_khoan": {"131": {"no": 1_000_000.0, "co": 0.0, "so_dong": 10}}}
    sau = {"cot": {"journal_lines.debit": {"tong": 1_000_001.0, "so_dong": 10,
                                           "so_dong_co_le_duoi_dong": 0}},
           "theo_tai_khoan": {"131": {"no": 1_000_001.0, "co": 0.0, "so_dong": 10}}}
    kq = DC.so_sanh(truoc, sau)
    assert kq["khop"] is False
    assert kq["lech_theo_cot"][0]["lech"] == 1.0
    assert kq["lech_theo_tai_khoan"][0]["lech_no"] == 1.0
    assert "Không đóng đợt nâng cấp" in kq["ket_luan"]


def test_bo_doi_chieu_phat_hien_duoc_mat_dong(db):
    """Mất dòng mà tổng vẫn bằng nhau vẫn là mất dữ liệu – phải kêu lên."""
    from app.services import v9_doi_chieu as DC
    truoc = {"cot": {"receipts.amount": {"tong": 500.0, "so_dong": 5, "so_dong_co_le_duoi_dong": 0}},
             "theo_tai_khoan": {}}
    sau = {"cot": {"receipts.amount": {"tong": 500.0, "so_dong": 4, "so_dong_co_le_duoi_dong": 0}},
           "theo_tai_khoan": {}}
    assert DC.so_sanh(truoc, sau)["khop"] is False


def test_hai_anh_chup_giong_nhau_thi_khop(db):
    from app.services import v9_doi_chieu as DC
    a = DC.chup(db)
    assert DC.so_sanh(a, a)["khop"] is True


# ====================== 4. CẢNH BÁO LÀM TRÒN ======================
def test_canh_bao_lam_tron_keu_len_khi_co_le_duoi_dong():
    """Đổi sang numeric(18,2) là thay đổi KHÔNG QUAY LẠI ĐƯỢC với phần lẻ thứ ba trở đi. Phải đếm
    trước khi nâng cấp, không phải phát hiện sau."""
    from app.services import v9_doi_chieu as DC
    ds = DC.canh_bao_lam_tron({"cot": {
        "journal_lines.debit": {"tong": 1.0, "so_dong": 1, "so_dong_co_le_duoi_dong": 3},
        "receipts.amount": {"tong": 1.0, "so_dong": 1, "so_dong_co_le_duoi_dong": 0},
    }})
    assert len(ds) == 1 and "journal_lines.debit" in ds[0] and "LÀM TRÒN" in ds[0]


def test_khong_dem_duoc_thi_noi_KHONG_BIET_chu_khong_noi_khong():
    from app.services import v9_doi_chieu as DC
    ds = DC.canh_bao_lam_tron({"cot": {
        "invoices.total": {"tong": 0.0, "so_dong": 0, "so_dong_co_le_duoi_dong": None}}})
    assert len(ds) == 1 and "KHÔNG ĐẾM ĐƯỢC" in ds[0]


def test_chup_that_tren_csdl_dem_duoc_phan_le(db):
    """Trên cơ sở dữ liệu thật, phép đếm phần lẻ phải chạy được – trả None nghĩa là câu lệnh hỏng và
    người vận hành sẽ đi nâng cấp mà không biết mình mất gì."""
    from app.services import v9_doi_chieu as DC
    a = DC.chup(db)
    for k, v in a["cot"].items():
        assert "loi" not in v, f"{k}: {v.get('loi')}"
        assert v["so_dong_co_le_duoi_dong"] is not None, k
