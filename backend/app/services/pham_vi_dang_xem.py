# -*- coding: utf-8 -*-
"""PQ-10 · Tách PHẠM VI ĐƯỢC PHÉP khỏi PHẠM VI ĐANG XEM (làn Phân quyền, 11/9/2026).

Hệ thống hôm nay chỉ có MỘT khái niệm: `pham_vi_phap_nhan.pham_vi(u)` – suy từ users.company_id,
trả None cho năm vai trò toàn tập đoàn. Đó là HÀNG RÀO CỨNG. Nó không phải nút chọn, và vì chỉ có
một khái niệm nên hai chuyện khác hẳn nhau bị ép vào cùng một con số:

  PHẠM VI ĐƯỢC PHÉP   vai trò và users.company_id quyết định. Người dùng KHÔNG nới rộng được.
  PHẠM VI ĐANG XEM    người dùng chọn. LUÔN là tập con của cái trên.

Thiếu khái niệm thứ hai thì hỏng hai chiều, và cả hai chiều đều đang hỏng thật:

  · Chủ tịch, Tổng giám đốc, Ban kiểm soát, Kế toán, CNTT nhìn thấy toàn tập đoàn và KHÔNG thu hẹp
    lại được. Muốn xem riêng một pháp nhân thì phải tự nhẩm trừ trong đầu – nghĩa là không xem được.
  · Người phụ trách một công ty MẸ chỉ thấy đúng công ty ấy, không thấy đơn vị trực thuộc, vì
    `loc()` so sánh `company_id == cid` chứ không đi xuống theo parent_id. "Toàn công ty gồm đơn vị
    trực thuộc" hôm nay CHƯA TỒN TẠI trong mã, dù màn hình vẫn nói như thể có.

Ba quy tắc của PQ-6 (không gộp im lặng · không giấu · không khoá cửa bằng cột chưa ai điền) giữ
nguyên hiệu lực. Tệp này KHÔNG sửa `pham_vi_phap_nhan.py`: năm chỗ đang gọi `loc()` không đổi hành
vi một chút nào. Muốn dùng luật mới thì gọi hàm ở đây và truyền lựa chọn vào.

MỘT KHÁC BIỆT PHẢI ĐỌC KỸ – hồ sơ chưa gán pháp nhân
----------------------------------------------------
`loc()` cũ luôn giữ dòng company_id rỗng trong mọi danh sách (quy tắc 2: không giấu). Ở đây, khi
người dùng đã CHỌN một đơn vị cụ thể, dòng chưa gán KHÔNG nằm trong danh sách ấy – nó có mục riêng
"Chưa xác định" trong chính nút chọn. Đó không phải giấu, mà là ngược lại: trước đây nó lẫn vào mọi
đơn vị nên không ai đếm được nó; nay nó là một mục có tên, có số đếm, bấm vào xem được. Quy tắc 2
đòi hồ sơ chưa gán phải còn người nhìn thấy, và một mục đứng riêng thì nhìn thấy rõ hơn hẳn.

Khi người dùng chưa chọn gì (kiểu "toan_pham_vi"), hành vi trùng khít `loc()` cũ – dòng chưa gán
vẫn nằm trong danh sách.
"""
from sqlalchemy import or_, select

from app.models.core import Company, User
from app.services import pham_vi_phap_nhan as PV

# Ba kiểu lựa chọn, không có kiểu thứ tư.
TOAN_PHAM_VI = "toan_pham_vi"      # toàn bộ phần ĐƯỢC PHÉP, company_id = None
DON_VI = "don_vi"                  # đúng một đơn vị và cây con của nó
CHUA_XAC_DINH = "chua_xac_dinh"    # riêng hồ sơ chưa gán pháp nhân
CAC_KIEU = (TOAN_PHAM_VI, DON_VI, CHUA_XAC_DINH)

MAC_DINH = {"kieu": TOAN_PHAM_VI, "company_id": None}

# Lựa chọn phải LƯU THEO NGƯỜI DÙNG Ở MÁY CHỦ (hợp đồng API mục III): đăng nhập máy khác vẫn thấy
# đúng đơn vị chọn lần trước. Bảng lưu là PQ-10b, đi kèm một bước chuyển cơ sở dữ liệu riêng –
# tách ra vì gộp một bước chuyển vào cùng lần gộp này là đúng kiểu hỏng đã làm chết hai lần triển
# khai ngày 11/9. Cho tới khi có bảng ấy, `doc_chon()` trả về mặc định KÈM CỜ NÓI THẲNG rằng chưa
# lưu được – màn hình đọc cờ này để không hứa với người dùng một thứ máy chủ chưa giữ được.
KHO_LUU = None


# =============================================================================================
# 1. Phạm vi ĐƯỢC PHÉP
# =============================================================================================

def hau_due(db, cid: int) -> set[int]:
    """Đơn vị `cid` và TOÀN BỘ cây con của nó theo parent_id.

    Có khóa chống vòng lặp. parent_id do người nhập, và một lần nhập nhầm A là cha của B trong khi
    B là cha của A sẽ làm hàm này chạy mãi – tức là một ô nhập sai trên màn hình danh mục treo
    được máy chủ. Gặp vòng thì dừng ở đó và bỏ qua, không báo lỗi: người đang xem báo cáo không
    phải người sửa được danh mục, chặn họ lại chẳng giúp gì.
    """
    ra: set[int] = set()
    hang = [cid]
    while hang:
        i = hang.pop()
        if i in ra:
            continue
        ra.add(i)
        hang.extend(db.execute(select(Company.id).where(Company.parent_id == i)).scalars().all())
    return ra


def duoc_phep(db, u: User) -> set[int] | None:
    """Tập đơn vị phiên này ĐƯỢC PHÉP xem. None = không giới hạn (toàn danh mục).

    None ở đây mang đúng nghĩa của `PV.pham_vi()` trả None, và `PV.ly_do_khong_gioi_han()` vẫn là
    chỗ phân biệt "vai trò toàn tập đoàn" với "tài khoản chưa gán" – hai chuyện khác hẳn nhau.
    """
    cid = PV.pham_vi(u)
    if cid is None:
        return None
    return hau_due(db, cid)


def duoc_chon(db, u: User, company_id: int) -> bool:
    """Đơn vị này có nằm trong phạm vi được phép của phiên không.

    Đây là cửa duy nhất trả lời câu ấy. Không ở đâu khác được tự so sánh company_id, vì mỗi chỗ tự
    so sánh là một chỗ quên mất cây con.
    """
    dp = duoc_phep(db, u)
    return True if dp is None else company_id in dp


# =============================================================================================
# 2. Cây đơn vị để vẽ nút chọn
# =============================================================================================

def cay(db, u: User) -> list[dict]:
    """Cây đơn vị người này được phép chọn, lồng theo parent_id.

    Đơn vị đã NGỪNG hoạt động vẫn có mặt. Lịch sử phải xem được: một chi nhánh đóng cửa tháng 6 vẫn
    còn số liệu sáu tháng đầu năm, và cắt nó khỏi nút chọn là làm sáu tháng ấy biến mất khỏi mọi
    báo cáo mà không có dòng nào nói rằng chúng từng tồn tại.
    """
    dp = duoc_phep(db, u)
    tat_ca = db.execute(select(Company)).scalars().all()
    if dp is not None:
        tat_ca = [c for c in tat_ca if c.id in dp]
    co = {c.id for c in tat_ca}
    nut = {c.id: {"company_id": c.id, "ten": c.name, "ma": c.code, "loai": c.kind,
                  "hoat_dong": bool(c.active), "cap": 0, "con": []} for c in tat_ca}
    goc = []
    for c in sorted(tat_ca, key=lambda x: (x.parent_id or 0, x.code or "", x.id)):
        # Cha nằm ngoài phạm vi được phép thì nút này là GỐC của cây người ấy nhìn thấy – không
        # được kéo cha vào cho đủ hình, vì kéo vào là để lộ đúng thứ phạm vi đang chặn.
        if c.parent_id and c.parent_id in co:
            nut[c.parent_id]["con"].append(nut[c.id])
        else:
            goc.append(nut[c.id])

    def _cap(ds, muc=0):
        for n in ds:
            n["cap"] = muc
            _cap(n["con"], muc + 1)

    _cap(goc)
    return goc


def so_don_vi(cay_ds: list[dict]) -> int:
    return sum(1 + so_don_vi(n["con"]) for n in cay_ds)


def co_the_thu_hep(db, u: User) -> bool:
    """Có đáng hiện nút chọn không. Một đơn vị duy nhất thì nút chọn chỉ là một ô bấm không đổi gì."""
    return so_don_vi(cay(db, u)) > 1


# =============================================================================================
# 3. Lựa chọn: đọc, kiểm, ghi
# =============================================================================================

def doc_chon(db, u: User) -> dict:
    """Lựa chọn đang có hiệu lực cho phiên này.

    `luu_tru` nói thẳng kho lưu đã có chưa. "chua_co" nghĩa là mỗi lần đăng nhập lại sẽ về mặc
    định – màn hình phải biết điều đó để không hiện dòng "đã ghi nhớ lựa chọn của bạn".
    """
    if KHO_LUU is None:
        return dict(MAC_DINH, luu_tru="chua_co")
    chon = KHO_LUU.doc(db, u) or dict(MAC_DINH)
    # Phạm vi được phép có thể đã BỊ THU HẸP sau lần chọn trước (đổi vai trò, đổi pháp nhân). Lựa
    # chọn cũ khi ấy không còn hợp lệ, và im lặng giữ nó là để một người vừa bị thu quyền vẫn xem
    # tiếp đơn vị cũ. Rơi về mặc định, kèm lý do.
    if chon.get("kieu") == DON_VI and not duoc_chon(db, u, chon.get("company_id")):
        return dict(MAC_DINH, luu_tru="co", ve_mac_dinh="lua_chon_cu_ngoai_pham_vi")
    return dict(chon, luu_tru="co")


def kiem_chon(db, u: User, kieu: str, company_id: int | None = None) -> dict:
    """Kiểm một lựa chọn trước khi ghi. Trả {"ok": True} hoặc {"ok": False, "ma": 403|422, "ly_do": …}.

    Lý do viết sẵn bằng TIẾNG VIỆT ĐỦ CÂU để màn hình hiện thẳng. Trả về mã lỗi trống rỗng thì bên
    kia sẽ tự nghĩ ra một câu, và câu ấy sẽ nói sai chuyện gì vừa xảy ra.
    """
    if kieu not in CAC_KIEU:
        return {"ok": False, "ma": 422,
                "ly_do": f"Kiểu phạm vi '{kieu}' không có trong hệ thống."}
    if kieu != DON_VI:
        return {"ok": True}
    if company_id is None:
        return {"ok": False, "ma": 422, "ly_do": "Chọn một đơn vị thì phải kèm mã đơn vị."}
    if db.get(Company, company_id) is None:
        return {"ok": False, "ma": 422,
                "ly_do": f"Không có đơn vị số {company_id} trong danh mục pháp nhân."}
    if not duoc_chon(db, u, company_id):
        c = db.get(Company, company_id)
        return {"ok": False, "ma": 403,
                "ly_do": (f"Tài khoản của bạn không được xem dữ liệu của {c.name}. "
                          "Phạm vi xem do vai trò và pháp nhân của tài khoản quyết định, "
                          "nút chọn không mở rộng được nó.")}
    return {"ok": True}


def dat_chon(db, u: User, kieu: str, company_id: int | None = None) -> dict:
    """Ghi lựa chọn. Kiểm trước, và KHÔNG ghi khi kiểm trượt.

    Chưa có kho lưu thì trả về lựa chọn kèm `luu_tru="chua_co"` – đúng thật là chưa lưu. Không giả
    vờ đã lưu: một nút bấm nói "đã lưu" mà không lưu là thứ người dùng chỉ phát hiện ra vào hôm sau.
    """
    kq = kiem_chon(db, u, kieu, company_id)
    if not kq["ok"]:
        return kq
    chon = {"kieu": kieu, "company_id": company_id if kieu == DON_VI else None}
    if KHO_LUU is None:
        return dict(chon, ok=True, luu_tru="chua_co")
    KHO_LUU.ghi(db, u, chon)
    return dict(chon, ok=True, luu_tru="co")


# =============================================================================================
# 4. Lọc theo lựa chọn
# =============================================================================================

def loc_dang_xem(q, model, u: User, db, chon: dict | None = None):
    """Lọc một truy vấn danh sách theo phạm vi ĐANG XEM.

    Luật: giao của ĐƯỢC PHÉP với ĐANG XEM. Lựa chọn không bao giờ nới rộng được phạm vi – dòng
    `duoc_chon()` ở dưới là chỗ duy nhất giữ điều đó, nên không được bỏ qua nó khi "chỉ đọc thôi".

    Bảng không có cột company_id thì trả nguyên truy vấn, y như `loc()` cũ: ép mọi bảng phải có
    pháp nhân sẽ làm hỏng các danh mục dùng chung (ngân hàng, tài khoản kế toán, tham số).
    """
    col = getattr(model, "company_id", None)
    if col is None:
        return q
    chon = chon or doc_chon(db, u)
    kieu = chon.get("kieu", TOAN_PHAM_VI)
    dp = duoc_phep(db, u)

    if kieu == CHUA_XAC_DINH:
        return q.where(col.is_(None))

    if kieu == DON_VI:
        cid = chon.get("company_id")
        if cid is None or not duoc_chon(db, u, cid):
            # Lựa chọn ngoài phạm vi: KHÔNG âm thầm mở rộng về toàn phạm vi, cũng không tin nó.
            # Trả rỗng là kết quả đúng, và `doc_chon()` đã đưa người dùng về mặc định kèm lý do.
            from sqlalchemy import false
            return q.where(false())
        return q.where(col.in_(sorted(hau_due(db, cid))))

    # TOAN_PHAM_VI – toàn bộ phần được phép. Giữ dòng chưa gán như `loc()` cũ (quy tắc 2).
    if dp is None:
        return q
    return q.where(or_(col.in_(sorted(dp)), col.is_(None)))


def mo_ta(db, u: User, chon: dict | None = None) -> dict:
    """Câu hiện lên thanh ngang, để người dùng luôn đọc được mình đang xem phần nào.

    Không có câu này thì đổi đơn vị xong, đi họp về, nhìn một con số nhỏ hơn bình thường và tưởng
    công ty vừa sụt doanh thu.
    """
    chon = chon or doc_chon(db, u)
    kieu = chon.get("kieu", TOAN_PHAM_VI)
    if kieu == CHUA_XAC_DINH:
        cau = "Bạn đang xem các hồ sơ CHƯA gán pháp nhân."
    elif kieu == DON_VI:
        c = db.get(Company, chon.get("company_id"))
        ten = c.name if c else f"đơn vị #{chon.get('company_id')}"
        n = len(hau_due(db, chon["company_id"])) if c else 1
        cau = (f"Bạn đang xem {ten} và {n - 1} đơn vị trực thuộc." if n > 1
               else f"Bạn đang xem {ten}.")
    else:
        cau = PV.mo_ta(db, u)["cau_hien_thi"]
    return {"kieu": kieu, "company_id": chon.get("company_id"), "cau_hien_thi": cau,
            "luu_tru": chon.get("luu_tru", "chua_co")}
