"""KS-2 · Mọi đường dẫn GHI phải khai quyền ở chỗ máy đọc được — hoặc khai vào bảng ngoại lệ.

Đo trên cây làm việc 11/9/2026: 648 đường dẫn, 340 đường GHI, 289 khai được bằng máy, 51 thì không.
51 chỗ ấy không phải 51 lỗ hổng — phần lớn có chặn thật, chỉ là chặn nằm trong thân hàm dịch vụ hoặc
là cổng "một cửa" theo người phụ trách. Nhưng bộ kiểm IM LẶNG ở 51 chỗ, mà im lặng thì không ai đếm
được. Tệp này biến 51 chỗ im lặng thành 51 dòng khai có tên, có lý do, và có người kiểm lại lời khai.

Nguyên tắc của tệp: KHÔNG TIN LỜI KHAI. Khai "chặn ở tours:create" thì phép thử mở đúng hàm ấy ra
đọc; ai gỡ chặn đi mà quên sửa lời khai là đỏ ngay.

  Q1  mọi đường ghi phải khai được ở một trong các chỗ máy đọc được, hoặc có tên trong bảng ngoại lệ
  Q2  lời khai "chặn ở tầng dịch vụ" phải đúng — mở hàm ra kiểm
  Q3  lời khai "kiểm token viết tay" phải đúng — thân hàm phải thật sự đọc ROBOT_TOKEN
  Q4  bảng ngoại lệ không được phình, lý do phải đủ dài
  Q5  chỗ HỞ THẬT phải đỏ cho tới khi lane chịu trách nhiệm đóng
  Q6  nghiệm thu: thêm một đường ghi mới mà quên khai thì đỏ NGAY

Q5 đỏ là có chủ đích và là sản phẩm của lệnh này, không phải phép thử hỏng. Kiểm soát mở ngoại lệ;
Kiểm soát không tự đóng ngoại lệ của mình.
"""
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_ks2_khaiquyen.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_ks2_khaiquyen.db", "test_ks2_khaiquyen.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import inspect  # noqa: E402

import pytest  # noqa: E402
from fastapi import APIRouter, Depends  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

from app.main import app  # noqa: E402
from tools import ks2_khai_quyen as K  # noqa: E402

GOC_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICH_VU = os.path.join(GOC_BACKEND, "app", "services")


def _cay_phu_thuoc(d):
    yield d
    for s in d.dependencies:
        yield from _cay_phu_thuoc(s)


def duong_ghi(ung_dung=app) -> list[tuple[str, APIRoute]]:
    """[(khoá, route)] cho mọi đường GHI. Khoá = 'POST /api/v1/...' — đúng dạng dùng trong bảng khai."""
    ra = []
    for r in ung_dung.routes:
        if not isinstance(r, APIRoute):
            continue
        m = sorted(set(r.methods) & set(K.PHUONG_THUC_GHI))
        if not m:
            continue
        ra.append((f"{m[0]} {r.path}", r))
    return ra


def khai_bang_may(r: APIRoute) -> str | None:
    """Tên cửa máy đọc được, hoặc None. Không phân biệt khai ở chữ ký hay ở decorator: FastAPI gộp cả
    hai thành cùng một cây phụ thuộc, và cả hai đều đọc được mà không phải phân tích mã nguồn."""
    for d in _cay_phu_thuoc(r.dependant):
        goi = getattr(d, "call", None)
        if getattr(goi, "vai_tro_yeu_cau", None):
            return "vai_tro_yeu_cau"
        ten = getattr(goi, "__name__", "")
        if ten in K.CUA_KHONG_THEO_VAI_TRO:
            return ten
    return None


def _than_ham_dich_vu(mo_ta: str) -> str | None:
    tep, _, ham = mo_ta.partition(":")
    duong = os.path.join(DICH_VU, tep + ".py")
    if not os.path.exists(duong):
        return None
    src = open(duong, encoding="utf-8").read()
    m = re.search(r"^def %s\(.*?(?=^def |\Z)" % re.escape(ham), src, re.S | re.M)
    return m.group(0) if m else None


# ------------------------------------------------------------------ Q1

def test_q1_moi_duong_ghi_deu_khai_duoc_hoac_co_ten_trong_bang_ngoai_le():
    """Phép thử NGHIỆM THU của lệnh KS-2: thêm một đường ghi mới mà quên khai thì đỏ ngay.

    Không có đường lọt nào: hoặc quyền đọc được bằng máy, hoặc đường dẫn có tên trong một bảng khai
    kèm lý do. Không có ô 'chắc là ổn'.
    """
    khai = K.moi_khai()
    thieu = []
    for k, r in duong_ghi():
        if khai_bang_may(r):
            continue
        if k in khai:
            continue
        thieu.append(f"{k}  ({r.endpoint.__module__}.{r.endpoint.__name__})")
    assert not thieu, (
        f"{len(thieu)} đường GHI không khai quyền ở chỗ máy đọc được và cũng không có tên trong bảng "
        f"ngoại lệ nào:\n" + "\n".join("  · " + t for t in sorted(thieu))
        + "\n\n  Ba chỗ khai hợp lệ: chữ ký hàm · dependencies=[...] ở decorator · bảng LUONG_VIEC.\n"
          "  Cách đúng và rẻ nhất: thêm Depends(require_roles(...)) — nó tự gắn vai_tro_yeu_cau.\n"
          "  Nếu chỗ này chặn theo NGƯỜI chứ không theo vai trò thì khai vào tools/ks2_khai_quyen.py\n"
          "  kèm lý do, để nó thành một dòng đếm được thay vì một chỗ im lặng.")


def test_q1b_khong_khai_thua_cho_duong_da_bien_mat():
    """Dòng khai cho đường dẫn không còn tồn tại thì báo, để bảng ngoại lệ không nuôi dòng chết.

    Dòng chết nguy hiểm hơn vẻ ngoài của nó: nó làm bảng ngoại lệ dài ra, và bảng dài thì không ai
    đọc lại, mà không đọc lại thì trần ở dưới mất tác dụng.
    """
    co = {k for k, _ in duong_ghi()}
    thua = sorted(k for k in K.moi_khai() if k not in co)
    assert not thua, (
        f"khai ngoại lệ cho đường dẫn không còn trong ứng dụng: {thua} — xoá khỏi "
        f"tools/ks2_khai_quyen.py")


# ------------------------------------------------------------------ Q2, Q3

def test_q2_loi_khai_chan_o_tang_dich_vu_phai_dung():
    """Mở đúng hàm được khai ra đọc. Đây là chỗ phép thử khác hẳn một bản rà tay.

    Rà tay đúng tại thời điểm rà. Ai đó gỡ `if u.role not in (...)` ra khỏi tours:approve tháng sau
    thì bản rà tay vẫn nói 'có chặn', còn phép thử này đỏ.
    """
    sai = []
    for duong, mo_ta in sorted(K.CHAN_TANG_DICH_VU.items()):
        than = _than_ham_dich_vu(mo_ta)
        if than is None:
            sai.append(f"{duong} → khai chặn ở {mo_ta} nhưng không tìm thấy hàm ấy")
        elif not any(d in than for d in K.DAU_HIEU_CHAN):
            sai.append(f"{duong} → {mo_ta} tồn tại nhưng KHÔNG còn dấu hiệu chặn nào trong thân hàm")
    assert not sai, (
        "lời khai 'chặn ở tầng dịch vụ' không đúng với mã đang có:\n"
        + "\n".join("  · " + s for s in sai)
        + f"\n\n  Dấu hiệu chặn được nhận: {K.DAU_HIEU_CHAN}\n"
          "  Chặn thật sự bị gỡ thì đây là hở quyền — chuyển dòng ấy sang bảng HO_QUYEN.")


def test_q3_loi_khai_token_viet_tay_phai_dung():
    """Ba đường robot kiểm ROBOT_TOKEN viết tay thay vì Depends(robot_auth).

    Cùng mức bảo vệ, khác chỗ khai. Đây là việc sửa nhỏ nhất trong cả lệnh KS-2 và nên sửa trước:
    đổi sang dependencies=[Depends(robot_auth)] là máy đọc được ngay, không đụng nghiệp vụ.
    """
    theo_khoa = dict(duong_ghi())
    sai = []
    for duong in sorted(K.TOKEN_VIET_TAY):
        r = theo_khoa.get(duong)
        if r is None:
            continue                      # Q1b đã lo dòng chết
        try:
            src = inspect.getsource(r.endpoint)
        except OSError:
            src = ""
        if "ROBOT_TOKEN" not in src:
            sai.append(f"{duong} → khai 'kiểm token viết tay' nhưng thân hàm không đọc ROBOT_TOKEN")
    assert not sai, "\n".join(sai) + "\n  Không có token mà cũng không có vai trò thì đó là hở quyền."


# ------------------------------------------------------------------ Q4

def test_q4_bang_ngoai_le_khong_duoc_phinh_va_ly_do_phai_du_dai():
    """Ngoại lệ phải tốn công hơn việc làm đúng, nếu không thì ai cũng đi đường ngoại lệ."""
    bang = {
        "CONG_KHAI": K.CONG_KHAI, "TOKEN_VIET_TAY": K.TOKEN_VIET_TAY,
        "CHAN_TAI_CHO": K.CHAN_TAI_CHO, "TU_PHUC_VU": K.TU_PHUC_VU, "HO_QUYEN": K.HO_QUYEN,
    }
    for ten, b in bang.items():
        tran = K.TRAN[ten]
        assert len(b) <= tran, (
            f"{ten} có {len(b)} dòng, trần {tran}. Quá trần nghĩa là cái đang được coi là ngoại lệ đã "
            f"thành quy tắc — và quy tắc thì phải nói ra, không lớn dần trong bảng ngoại lệ.")

    # TOKEN_VIET_TAY chỉ ghi vắn tắt cách chặn, Q3 đã kiểm bằng mã nên không đòi lý do dài.
    for ten in ("CONG_KHAI", "CHAN_TAI_CHO", "TU_PHUC_VU", "HO_QUYEN"):
        ngan = {k: v for k, v in bang[ten].items() if len(v.strip()) < K.MIN_LY_DO}
        assert not ngan, (
            f"{ten}: lý do dưới {K.MIN_LY_DO} ký tự ở {sorted(ngan)} — viết đủ để người duyệt phải nghĩ.")


# ------------------------------------------------------------------ Q5

def test_q5_cho_ho_quyen_that_phai_do_cho_toi_khi_co_nguoi_dong():
    """ĐỎ CÓ CHỦ ĐÍCH. Đây là sản phẩm của lệnh KS-2, không phải phép thử hỏng.

    Rà 51 đường ghi tìm ra một chỗ KHÔNG có chặn nào. Kiểm soát mở ngoại lệ và KHÔNG tự đóng ngoại
    lệ của mình — đóng dòng này là việc của lane được nêu tên trong lý do, sau khi đã có chặn thật.
    """
    assert not K.HO_QUYEN, (
        f"{len(K.HO_QUYEN)} đường GHI không có chặn nào:\n"
        + "\n".join(f"  · {k}\n      {v}" for k, v in sorted(K.HO_QUYEN.items()))
        + "\n\n  Xoá dòng khai đi KHÔNG làm hết hở — nó chỉ làm hết đếm được.")


# ------------------------------------------------------------------ Q6

def test_q6_nghiem_thu_them_duong_ghi_moi_ma_quen_khai_thi_do_ngay():
    """Nghiệm thu đúng như lệnh KS-2 yêu cầu, chạy trên một ứng dụng dựng riêng trong bộ nhớ.

    Không đụng tới ứng dụng thật: dựng một FastAPI con, gắn một đường POST không khai quyền, rồi
    soi bằng chính bộ soi ở trên. Nếu bộ soi bỏ qua nó thì phép thử này đỏ — tức là KS-2 hỏng chứ
    không phải kho hỏng.
    """
    from fastapi import FastAPI
    from app.api.deps import require_roles, robot_auth

    phu = FastAPI()
    r = APIRouter()

    @r.post("/thu/quen-khai")
    def quen_khai():
        return {}

    @r.post("/thu/khai-o-chu-ky")
    def khai_chu_ky(u=Depends(require_roles("ketoan"))):
        return {}

    @r.post("/thu/khai-o-decorator", dependencies=[Depends(require_roles("ketoan"))])
    def khai_decorator():
        return {}

    @r.post("/thu/cua-token", dependencies=[Depends(robot_auth)])
    def cua_token():
        return {}

    @r.get("/thu/chi-doc")
    def chi_doc():
        return {}

    phu.include_router(r)
    thay = {k: khai_bang_may(rt) for k, rt in duong_ghi(phu)}

    assert "GET /thu/chi-doc" not in thay, "đường chỉ ĐỌC không được tính vào phạm vi KS-2"
    assert thay.get("POST /thu/quen-khai") is None, (
        "bộ soi KS-2 KHÔNG bắt được đường ghi quên khai — phép thử Q1 đang xanh giả")
    assert thay.get("POST /thu/khai-o-chu-ky") == "vai_tro_yeu_cau", "khai ở chữ ký phải đọc được"
    assert thay.get("POST /thu/khai-o-decorator") == "vai_tro_yeu_cau", (
        "khai ở dependencies=[...] của decorator phải đọc được — đây là chỗ khai hợp lệ thứ hai")
    assert thay.get("POST /thu/cua-token") == "robot_auth", (
        "cửa token robot phải được nhận là chỗ khai máy đọc được")


# ------------------------------------------------------------------ số liệu để chấm điểm

def test_q7_in_so_lieu_de_cham_diem():
    """Không khẳng định gì — in ra để báo cáo có số, chạy với -s để xem."""
    tong = sum(1 for r in app.routes if isinstance(r, APIRoute))
    ghi = duong_ghi()
    may_doc = [k for k, r in ghi if khai_bang_may(r)]
    khai = K.moi_khai()
    print(f"\nKS-2 · {tong} đường dẫn · {len(ghi)} đường GHI · {len(may_doc)} khai bằng máy "
          f"· {len(ghi) - len(may_doc)} khai bằng bảng")
    for ten in ("CONG_KHAI", "TOKEN_VIET_TAY", "CHAN_TANG_DICH_VU", "CHAN_TAI_CHO", "TU_PHUC_VU", "HO_QUYEN"):
        print(f"    {ten:20} {sum(1 for v in khai.values() if v == ten)}")
    assert True
