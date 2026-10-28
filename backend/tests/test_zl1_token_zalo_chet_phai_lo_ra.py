# -*- coding: utf-8 -*-
"""ZL-1 · Token Zalo chết thì phải LỘ RA — ở cả ba chỗ.

Đợt này sinh ra từ một ca có thật, 28/10/2026: khách bấm nhận mã qua Zalo, Zalo trả
«Access token invalid», màn hình báo «thử lại sau ít phút» — và cùng lúc cửa công khai
`/api/v1/cong/kenh` vẫn nói `zalo: ok=true`, còn bảng cảnh báo thì trống.

Ba phép dưới đây ghim ba chỗ ấy.

VÌ SAO KHÔNG ĐỤNG CƠ SỞ DỮ LIỆU: ba hàm được soi (`_gui`, `send_zns`, `configured`) nhận `db`
rồi đưa thẳng cho `kho(db)`. Thay `kho` bằng một dòng token giả là soi được đúng phần cần soi,
không cần phiên thật, không cần `conftest`, và chạy trong một phần nghìn giây. Máy chủ Zalo cũng
là giả (thay `_post`), nên không gọi ra ngoài và không tiêu một tin ZNS thật nào.
"""
from app.models.core import Alert
from app.services import zalo as Z


class _Kho:
    """Dòng token giả — đúng những cột mà ba hàm trên đọc tới."""

    def __init__(self, access_token="tk-cu", refresh_token="rf-cu"):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.het_han_luc = None
        self.loi_cuoi = ""


class _Rong:
    def scalars(self):
        return self

    def first(self):
        return None


class _Db:
    """Phiên giả — chỉ đủ cho `_bao_hong`: tra một lần, thêm một dòng, chốt."""

    def __init__(self):
        self.them = []

    def add(self, x):
        self.them.append(x)

    def commit(self):
        pass

    def flush(self):
        pass

    def execute(self, *a, **k):
        return _Rong()


def _dung(monkeypatch, **kw):
    k = _Kho(**kw)
    monkeypatch.setattr(Z, "kho", lambda db_: k)
    return _Db(), k


def test_zl1_1_token_chet_thi_bao_do_chu_khong_im(monkeypatch):
    """Zalo từ chối vì token, làm mới cũng không xong — phải sinh cảnh báo đỏ. Im lặng là hỏng."""
    db, k = _dung(monkeypatch)
    monkeypatch.setattr(Z, "_post", lambda *a, **kw: {"error": -216, "message": "Access token invalid"})
    monkeypatch.setattr(Z, "refresh_token", lambda db_: "")

    r = Z.send_zns(db, "0987133383", "657312", {"otp": "123456"})

    assert r.get("error") == -216
    do = [x for x in db.them if isinstance(x, Alert) and x.kind == "zalo_token_hong"]
    assert do, ("Token Zalo chết mà KHÔNG sinh cảnh báo nào. Đây đúng là ca đã xảy ra 28/10/2026: "
                "mã đăng nhập của khách không gửi được suốt nhiều giờ và không ai được báo.")
    assert k.loi_cuoi, "Vết hỏng phải ghi lại trong kho token, để cửa `/cong/kenh` đọc được."


def test_zl1_2_het_han_thi_lam_moi_va_gui_lai_DUNG_MOT_LAN(monkeypatch):
    """Phép cứu phải nằm trong CHÍNH hàm gửi, không nằm riêng ở đường hàng chờ CRM.

    Và làm mới ĐÚNG MỘT LẦN: refresh token của Zalo dùng một lần là mất, gọi hai lần trong một
    lượt gửi là tự đốt chuỗi uỷ quyền vừa dựng.
    """
    db, k = _dung(monkeypatch)
    luot, lam_moi = {"n": 0}, {"n": 0}

    def gia_post(*a, **kw):
        luot["n"] += 1
        return {"error": -216, "message": "Access token invalid"} if luot["n"] == 1 else {"error": 0}

    def gia_lam_moi(db_):
        lam_moi["n"] += 1
        k.access_token = "tk-moi"
        return "tk-moi"

    monkeypatch.setattr(Z, "_post", gia_post)
    monkeypatch.setattr(Z, "refresh_token", gia_lam_moi)

    r = Z.send_zns(db, "0987133383", "657312", {"otp": "123456"})

    assert r.get("error") == 0, "Làm mới token xong thì phải gửi lại, và lượt ấy phải đi được"
    assert luot["n"] == 2, f"Phải gửi đúng 2 lượt (hỏng, rồi lại) — thấy {luot['n']}"
    assert lam_moi["n"] == 1, f"Phải làm mới ĐÚNG 1 lần — thấy {lam_moi['n']}"
    assert not [x for x in db.them if isinstance(x, Alert)], "Cứu được rồi thì đừng báo đỏ"


def test_zl1_3_tin_nhan_cham_soc_cung_duoc_cuu_nhu_ZNS(monkeypatch):
    """Không chỉ ZNS. Tin OA cũng phải đi qua đúng một phép cứu ấy."""
    db, k = _dung(monkeypatch)
    luot = {"n": 0}

    def gia_post(*a, **kw):
        luot["n"] += 1
        return {"error": -124} if luot["n"] == 1 else {"error": 0}

    monkeypatch.setattr(Z, "_post", gia_post)
    monkeypatch.setattr(Z, "refresh_token", lambda db_: "tk-moi")

    r = Z.send_oa_text(db, "uid-1", "xin chào")

    assert r.get("error") == 0
    assert luot["n"] == 2, "Tin OA mà không được gửi lại sau khi làm mới thì phép cứu còn thủng một nửa"


def test_zl1_4_trang_thai_oa_la_TOKEN_CON_DUNG_DUOC(monkeypatch):
    """`configured()["oa"]` không được chỉ hỏi «có một chuỗi token không».

    Đây là chỗ làm màn đăng nhập của khách nói dối: nút Zalo sáng trong khi Zalo từ chối mọi tin.
    """
    db, k = _dung(monkeypatch)
    assert Z.configured(db)["oa"] is True, "Token lành thì phải bật"

    k.loi_cuoi = "Zalo từ chối: Access token invalid"
    assert Z.configured(db)["oa"] is False, (
        "Token đã biết là hỏng mà vẫn báo oa=true — đây đúng là câu nói dối của ngày 28/10/2026.")

    monkeypatch.setattr(Z, "_post", lambda *a, **kw: {"error": 0})
    Z.send_zns(db, "0987133383", "657312", {"otp": "1"})
    assert Z.configured(db)["oa"] is True, (
        "Gửi được một tin rồi thì vết hỏng cũ phải xoá — nếu không, trạng thái kẹt ở đỏ vĩnh viễn.")
