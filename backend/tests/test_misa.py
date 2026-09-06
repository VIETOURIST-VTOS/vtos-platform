"""Cầu nối MISA: nạp TK theo cấu trúc MISA + ánh xạ TT99, số dư đầu kỳ theo đối tượng, sổ nhật ký chung, đối chiếu, BCTC TT99, xuất ngược mẫu Import."""
import os, sys, io
os.environ["DATABASE_URL"] = "sqlite:///./test_misa.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_misa.db"): os.remove("test_misa.db")
import pytest
from openpyxl import Workbook, load_workbook
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK: TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def xlsx(rows, title="S"):
    wb = Workbook(); ws = wb.active; ws.title = title
    for r in rows: ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def tb_file():
    # đúng bố cục "Bảng cân đối tài khoản (mẫu quản trị)" MISA
    rows = [["CHI NHÁNH PHAN THIẾT - CÔNG TY CỔ PHẦN VIETOURIST HOLDINGS"], ["BẢNG CÂN ĐỐI TÀI KHOẢN (MẪU QUẢN TRỊ)"], ["Từ ngày 01/01/2026 đến ngày 30/06/2026"],
            ["Số tài khoản", "Tên tài khoản", "Đầu kỳ", None, "Phát sinh", None, "Cuối kỳ", None], [None, None, "Nợ", "Có", "Nợ", "Có", "Nợ", "Có"],
            ["111", "Tiền mặt", 1000, 0, 0, 0, 1000, 0], ["1111", "Tiền Việt Nam", 1000, 0, 0, 0, 1000, 0],
            ["131", "Phải thu của khách hàng", 5000, 0, 0, 0, 5000, 0],
            ["331", "Phải trả cho người bán", 0, 2000, 0, 0, 0, 2000],
            ["341", "Vay và nợ thuê tài chính", 0, 1500, 0, 0, 0, 1500], ["3411", "Các khoản đi vay", 0, 1500, 0, 0, 0, 1500], ["34112", "Các khoản đi vay dài hạn", 0, 1500, 0, 0, 0, 1500],
            ["411", "Vốn đầu tư của chủ sở hữu", 0, 2500, 0, 0, 0, 2500], ["4111", "Vốn góp của chủ sở hữu", 0, 2500, 0, 0, 0, 2500],
            ["Tổng cộng", None, 6000, 6000, 0, 0, 6000, 6000]]
    return xlsx(rows)


def obj_file():
    rows = [["TỔNG HỢP CÔNG NỢ THEO ĐỐI TƯỢNG"], ["Loại tiền: VND, Từ ngày 01/01/2026 đến ngày 30/06/2026"],
            ["Mã đối tượng", "Tên đối tượng", "TK Công nợ", "Số dư đầu kỳ", None, "Phát sinh", None, "Số dư cuối kỳ", None], [None, None, None, "Nợ", "Có", "Nợ", "Có", "Nợ", "Có"],
            ["00000", "Khách lẻ", "131", 5000, 0, 0, 0, 4000, 0], ["0301234567", "CÔNG TY A", "131", 0, 0, 0, 0, 2000, 0],
            ["0309999999", "CÔNG TY B", "131", 0, 0, 0, 0, 0, 1000], ["4500272030", "Hòn Cò Resort", "331", 0, 2000, 0, 0, 0, 2000]]
    return xlsx(rows)


def test_chart_misa_and_mapping():
    acc = client.get("/api/v1/accounts", headers=login("ketoan")).json()
    by = {a["code"]: a for a in acc}
    assert len([a for a in acc if a["misa"]]) >= 120
    assert by["34112"]["bs_credit"] == "339" and by["34111"]["bs_credit"] == "321" and by["131"]["bs_debit"] == "131" and by["131"]["bs_credit"] == "312"
    assert by["6351"]["pl_code"] == "23" and by["51137"]["pl_code"] == "01" and by["3411"]["is_detail"] is False and by["1111"]["is_detail"] is True


def test_opening_balance_by_object_and_bctc():
    h = login("ketoan")
    r = client.post("/api/v1/misa/trial-balance/preview", files={"file": ("tb.xlsx", tb_file())}, headers=h).json()
    assert r["detail_accounts"] == 5 and r["close_debit"] == 6000
    r = client.post("/api/v1/misa/opening-balance", files={"file": ("tb.xlsx", tb_file()), "objects": ("cn.xlsx", obj_file())}, data={"as_of": "2026-06-30", "column": "close"}, headers=h)
    assert r.status_code == 200, r.text
    r = r.json(); assert r["object_lines"] == 4 and r["total"] == 7000 and not r["warnings"]
    # nhập lần 2 không replace → chặn; replace → đảo và ghi lại
    assert client.post("/api/v1/misa/opening-balance", files={"file": ("tb.xlsx", tb_file())}, data={"as_of": "2026-06-30"}, headers=h).status_code == 422
    assert client.post("/api/v1/misa/opening-balance", files={"file": ("tb.xlsx", tb_file()), "objects": ("cn.xlsx", obj_file())}, data={"as_of": "2026-06-30", "replace": "true"}, headers=h).status_code == 200
    # BCTC TT99: 131 tách theo đối tượng → 131 = 6000 (khách lẻ 4000 + A 2000), 312 = 1000 (B dư Có), 339 = 1500, cân
    rep = client.get("/api/v1/reports/bctc?upto=2026-06-30&since=2026-01-01", headers=h).json()
    v = {x["code"]: x["now"] for x in rep["thtc"] if x["code"]}
    assert v["131"] == 6000 and v["312"] == 1000 and v["339"] == 1500 and v["311"] == 2000 and v["411"] == 2500 and v["111"] == 1000
    assert v["280"] == v["440"] == 7000 and rep["balanced"]
    x = client.get("/api/v1/reports/bctc.xlsx?upto=2026-06-30", headers=h)
    assert x.status_code == 200 and x.headers["content-type"].startswith("application/vnd.openxmlformats")
    wb = load_workbook(io.BytesIO(x.content)); assert wb.sheetnames[:2] == ["THTC - RIENG", "KQKD - RIENG"]
    # đối chiếu: VTOS == MISA sau khi nạp (tính theo tổng TK cha)
    rc = client.post("/api/v1/misa/reconcile", files={"file": ("tb.xlsx", tb_file())}, headers=h).json()
    assert rc["diff_count"] == 0, rc


def test_journal_import_and_partners_projects():
    h = login("ketoan")
    nkc = xlsx([["SỔ NHẬT KÝ CHUNG"], ["Từ ngày 01/07/2026 đến ngày 31/07/2026"],
                ["Ngày hạch toán", "Ngày chứng từ", "Số chứng từ", "Diễn giải", "Tài khoản", "TK đối ứng", "Phát sinh Nợ", "Phát sinh Có", "Mã đối tượng", "Tên đối tượng"],
                ["05/07/2026", "05/07/2026", "MDV26000900", "Landtour Đà Lạt", "1541", "331", 800, 0, "4500272030", "Hòn Cò Resort"],
                ["05/07/2026", "05/07/2026", "MDV26000900", "Landtour Đà Lạt", "331", "1541", 0, 800, "4500272030", "Hòn Cò Resort"],
                ["06/07/2026", "06/07/2026", "BH0007", "Doanh thu tour", "131", "51131", 3000, 0, "0301234567", "CÔNG TY A"],
                ["06/07/2026", "06/07/2026", "BH0007", "Doanh thu tour", "51131", "131", 0, 3000, "0301234567", "CÔNG TY A"],
                ["07/07/2026", "07/07/2026", "KC01", "Kết chuyển giá vốn", "6321", "1541", 0, 800, "", ""]])   # lệch → bỏ qua
    r = client.post("/api/v1/misa/journal", files={"file": ("nkc.xlsx", nkc)}, data={"dry_run": "true"}, headers=h).json()
    assert r["docs"] == 3 and r["imported"] == 2 and r["unbalanced"] == 1
    r = client.post("/api/v1/misa/journal", files={"file": ("nkc.xlsx", nkc)}, headers=h).json()
    assert r["imported"] == 2 and r["amount"] == 3800
    r2 = client.post("/api/v1/misa/journal", files={"file": ("nkc.xlsx", nkc)}, headers=h).json()
    assert r2["imported"] == 0 and r2["skipped_existing"] == 2   # không nạp trùng
    js = client.get("/api/v1/journal?period=2026-07", headers=h).json()
    e = next(x for x in js if x["source_ref"].startswith("misa:BH0007"))
    assert e["status"] == "da_ghi_so" and e["lines"][0]["partner_code"] == "0301234567"
    # KQKD tháng 7: doanh thu 3000
    rep = client.get("/api/v1/reports/bctc?upto=2026-07-31&since=2026-07-01", headers=h).json()
    k = {x["code"]: x["now"] for x in rep["kqkd"]}; assert k["01"] == 3000 and k["10"] == 3000 and k["20"] == 3000
    # danh mục
    kh = xlsx([["Danh sách khách hàng"], ["STT", "Mã khách hàng", "Tên khách hàng", "Địa chỉ", "Công nợ", "Mã số thuế/CCCD chủ hộ", "Điện thoại", "ĐT di động NLH", "Là Đối tượng nội bộ", "Chi nhánh"],
               [1, "0301234567", "CÔNG TY A", "Q1", 0, "0301234567", "", "", "", "CN"], [2, "00000", "Khách lẻ", "", 0, "", "", "", "", "CN"]])
    assert client.post("/api/v1/misa/partners", files={"file": ("kh.xlsx", kh)}, headers=h).json()["created"] == 2
    ncc = xlsx([["STT", "Tên NCC", "MST", "Tên pháp nhân (người đại diện)", "Địa chỉ"], [1, "RESORT VĨNH HY", "4500485670", "CTY TNHH PHÁT HOÀNG LONG", "Vĩnh Hải"]])
    assert client.post("/api/v1/misa/partners", files={"file": ("DataNCC.xlsx", ncc)}, headers=h).json()["created"] == 1
    ps = client.get("/api/v1/partners?q=4500485670", headers=h).json(); assert ps and ps[0]["trade_name"] == "RESORT VĨNH HY" and ps[0]["is_supplier"]
    tour_code = client.get("/api/v1/tours?limit=1", headers=h).json()[0]["code"]
    ct = xlsx([["DANH SÁCH CÔNG TRÌNH"], ["STT", "Mã công trình", "Tên công trình", "Loại công trình", "Tình trạng", "Ngày bắt đầu", "Ngày kết thúc", "Dự toán", "Chủ đầu tư", "Trạng thái"],
               [1, "0000", "Tour bổ sung", "", "Đang thực hiện", "", "", 0, "", ""], [2, "EU0014.09.170626", "Châu Âu 17/06/2026", "", "Đang thực hiện", "17/06/2026", "25/06/2026", 0, "", ""],
               [3, tour_code, "Tour VTOS", "", "Đang thực hiện", "", "", 0, "", ""]])
    r = client.post("/api/v1/misa/projects", files={"file": ("ct.xlsx", ct)}, headers=h).json()
    assert r["created"] >= 2 and r["technical"] == 1 and r["standard"] == 1 and r["linked"] == 1
    st = client.get("/api/v1/partners/stats", headers=h).json(); assert st["projects_linked"] >= 1 and st["misa_entries"] == 2


def test_dimension_rules_and_exports():
    h = login("ketoan")
    # bút toán tay: 131 không có đối tượng → chặn; có mã đối tượng → được
    bad = client.post("/api/v1/journal", json={"entry_date": "2026-07-10", "description": "x", "lines": [{"account": "131", "debit": 100}, {"account": "5113", "credit": 100}]}, headers=h)
    assert bad.status_code == 422 and "đối tượng" in bad.text
    ok = client.post("/api/v1/journal", json={"entry_date": "2026-07-10", "description": "x", "lines": [{"account": "131", "debit": 100, "partner_code": "0301234567"}, {"account": "51131", "credit": 100, "project_code": "EU0014.09.170626"}]}, headers=h)
    assert ok.status_code == 201, ok.text
    # xuất ngược MISA
    x = client.get("/api/v1/misa/export/purchases.xlsx?date_from=2026-01-01&date_to=2026-12-31", headers=h); assert x.status_code == 200
    ws = load_workbook(io.BytesIO(x.content)).active; assert ws.max_column == 57 and ws.cell(1, 1).value == "Phương thức thanh toán"
    x = client.get("/api/v1/misa/export/projects.xlsx", headers=h); ws = load_workbook(io.BytesIO(x.content)).active
    assert ws.cell(1, 1).value == "Mã công trình (*)" and ws.max_row > 1
    x = client.get("/api/v1/misa/export/entries.xlsx?date_from=2026-01-01&date_to=2026-12-31", headers=h); assert x.status_code == 200
    # tour mới → công trình cùng mã
    t = client.get("/api/v1/tours?limit=1", headers=h).json()[0]
    assert any(p["code"] == t["code"] for p in client.get(f"/api/v1/projects?q={t['code']}", headers=h).json())
    # NV kinh doanh không được nạp
    assert client.post("/api/v1/misa/partners", files={"file": ("a.xlsx", b"x")}, headers=login("kd.hoa")).status_code == 403


def test_kiem_toan_checkpoint():
    h = login("ketoan")
    # có doanh thu/chi phí thật còn treo trong kỳ (chưa kết chuyển 911) trước khi chốt sổ – mô phỏng
    # đúng tình huống production (bug cộng dồn cũ chỉ lộ ra khi có số dư P&L thật ở kỳ chốt sổ)
    ok = client.post("/api/v1/journal", json={"entry_date": "2026-03-15", "description": "DT test", "lines": [
        {"account": "131", "debit": 500000, "partner_code": "0301234567"}, {"account": "51131", "credit": 500000, "project_code": "EU0014.09.170626"}]}, headers=h)
    assert ok.status_code == 201, ok.text
    ok2 = client.post("/api/v1/journal", json={"entry_date": "2026-03-16", "description": "CP test", "lines": [
        {"account": "6421", "debit": 120000}, {"account": "1111", "credit": 120000}]}, headers=h)
    assert ok2.status_code == 201, ok2.text
    r = client.post("/api/v1/misa/kiem-toan-checkpoint", data={"column": "close"}, headers=h)
    assert r.status_code == 200, r.text
    js = r.json(); assert js["total"] > 0 and js["accounts"] > 0
    # trùng lần 2 không replace → lỗi
    assert client.post("/api/v1/misa/kiem-toan-checkpoint", data={"column": "close"}, headers=h).status_code == 422
    # replace=True → ghi lại được
    r2 = client.post("/api/v1/misa/kiem-toan-checkpoint", data={"column": "close", "replace": "true"}, headers=h)
    assert r2.status_code == 200
    # BCTC tại 30/6/2026 vẫn phải cân đối (280 == 440) sau khi chốt sổ kiểm toán
    rep = client.get("/api/v1/reports/bctc?upto=2026-06-30&since=2026-01-01", headers=h).json()
    assert rep["balanced"]
    v = {x["code"]: x["now"] for x in rep["thtc"]}
    # điều chỉnh theo CHÊNH LỆCH nên phải khớp tuyệt đối số kiểm toán dù sổ đã có bút toán khác từ trước
    # cho phép sai số nhỏ do các bút toán thử nghiệm khác trong cùng phiên test (không liên quan chốt sổ)
    assert abs(v["280"] - 348712228082) < 10000 and abs(v["440"] - 348712228082) < 10000
    assert abs(v["411"] - 240000000000) < 1
    assert abs(v["420"] - 14037369907) < 10000
    # TK xét theo đối tượng (131 có số dư cũ từ "DT test" ở trên, mã đối tượng khác mã kiểm toán) không được
    # cộng dồn hai chiều: 130/311/312 phải khớp sát số kiểm toán, không phồng lên do đối tượng cũ + mới
    assert abs(v["130"] - 168818037699) < 10000
    assert abs(v["311"] - 13459932467) < 10000
    assert abs(v["132"] - 73783036624) < 10000
    # ---- LCTT gián tiếp: dòng 70 (tiền cuối kỳ) phải khớp đúng tiền mặt+tiền gửi thực tế 30/06/2026 ----
    assert "lctt" in rep and rep["lctt"]
    lv = {x["code"]: x["now"] for x in rep["lctt"]}
    cash_end = v.get("110", 0.0)  # 110 = tiền và tương đương tiền (THTC)
    assert abs(lv["70"] - cash_end) < 10000, f"LCTT dòng 70 ({lv['70']:,.0f}) phải khớp tiền cuối kỳ THTC ({cash_end:,.0f})"
    assert abs(lv["50"] - (lv["20"] + lv["30"] + lv["40"])) < 1
    assert abs(lv["70"] - (lv["50"] + lv["60"] + lv["61"])) < 1
    # residual_plug trừ đi phần TÁC ĐỘNG TIỀN đã biết trước của bút toán chốt sổ kiểm toán (bình thường, vì
    # LCTT loại bút toán này khỏi các chỉ tiêu HĐKD/đầu tư/tài chính – xem cash_flow_indirect_tt99) phải nhỏ;
    # nếu còn lớn bất thường nghĩa là có nhóm tài khoản khác chưa phân loại đúng theo chỉ tiêu BCTC (như lỗi
    # 3411→34111/34112/34113 đã gặp trên dữ liệu thật)
    unexplained = rep["lctt_residual_plug"] - rep["lctt_kiem_toan_restatement_cash_effect"]
    assert abs(unexplained) < 5_000_000_000, f"LCTT residual chưa lý giải được bất thường lớn ({unexplained:,.0f})"
    # ---- Chi tiết vay 341 theo ngân hàng: tổng dư cuối kỳ phải khớp đúng tổng 3 tiểu khoản kiểm toán ----
    vay = client.get("/api/v1/reports/vay-341?upto=2026-06-30&since=2026-01-01", headers=h).json()
    assert abs(vay["total"]["close"] - (57378198822 + 11833359977 + 5203246120)) < 10000
