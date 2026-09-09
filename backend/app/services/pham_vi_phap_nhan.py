"""Phạm vi pháp nhân của phiên đăng nhập (Đợt 2 – Robot Phân quyền, mục P6).

Vấn đề phải giải: Vietourist Holdings có nhiều pháp nhân trong phạm vi hợp nhất. Một người của
công ty vận tải không có việc gì phải nhìn thấy danh sách tour của công ty lữ hành, và ngược lại.
Nhưng cái nguy hiểm hơn quyền xem là **báo cáo**: nếu một hồ sơ chưa xác định pháp nhân mà hệ thống
tự gộp về công ty mẹ cho gọn màn hình, thì một khoản của công ty này chạy sang báo cáo của công ty
kia, và không có cách nào phát hiện lại về sau vì không còn dấu vết nào nói rằng nó từng "chưa biết".

Vì vậy module này có đúng ba quy tắc, và cả ba đều nói "không":

1. **Không gộp im lặng.** Hồ sơ company_id rỗng là CHƯA XÁC ĐỊNH. Nó không thuộc công ty mẹ, không
   thuộc công ty của người đang xem. `dem()` luôn trả về HAI con số tách rời; không có hàm nào trong
   file này cộng chúng lại.

2. **Không giấu.** Hồ sơ chưa xác định vẫn nằm trong danh sách người dùng nhìn thấy, có nhãn
   `chua_gan`. Lọc nó ra khỏi màn hình nghe có vẻ "an toàn" nhưng thực chất là làm nó biến mất khỏi
   mọi con mắt, và người duy nhất còn có thể gán nó thì không còn nhìn thấy nó để mà gán.

   ĐÍNH CHÍNH 08/9/2026: bản đầu của đoạn này viết "1.200 tour nhập từ Vietrip đều chưa có pháp
   nhân". ĐO trên hệ thống thật sau khi phát hành: 0 hồ sơ chưa gán trên cả năm loại – 1.258 tour,
   10.074 booking, 5.664 phiếu thu, 4.659 đề nghị chi, 25.728 chứng từ ghi sổ đều đã có pháp nhân.
   Con số kia là suy đoán chưa đo, và nó sai. Quy tắc thì vẫn giữ: nó không tốn gì khi danh sách
   rỗng, và đúng vào ngày có hồ sơ đầu tiên chưa gán thì nó đã đứng sẵn ở đó.

3. **Không khoá cửa bằng một cột chưa ai điền.** `users.company_id` được thêm ngày 07/9/2026,
   nullable, không có bước điền sẵn. Nếu bật lọc cứng ngay thì mọi tài khoản chưa gán sẽ thấy màn
   hình trống trơn và cả công ty đứng lại trong một buổi sáng. Tài khoản chưa gán pháp nhân vì thế
   vẫn thấy toàn bộ – NHƯNG nó không được im lặng: `/access/gaps` đã đếm sẵn nhóm "chưa gán pháp
   nhân", và `/auth/me` nay trả `pham_vi` để màn hình nói thẳng ra rằng phiên này chưa bị giới hạn.
   Siết được hay không là việc của người quản trị đi gán, không phải việc của đoạn mã này đoán.
"""
from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.models.core import User, Company

# Vai trò làm việc trên phạm vi hợp nhất: chủ tịch, tổng giám đốc, ban kiểm soát, kế toán, CNTT.
# Kế toán nằm ở đây vì báo cáo hợp nhất và loại trừ giao dịch nội bộ đòi hỏi nhìn cả hai bên của
# một giao dịch nội bộ; cắt một bên đi thì không loại trừ được, mà không loại trừ được thì doanh thu
# hợp nhất bị thổi lên đúng bằng phần giao dịch giữa các công ty trong nhà.
TOAN_TAP_DOAN = ("chutich", "tgd", "bks", "ketoan", "cntt")

CHUA_GAN = "chua_gan"


def pham_vi(u: User) -> int | None:
    """Pháp nhân mà phiên đăng nhập này bị giới hạn vào. None = không bị giới hạn.

    None xảy ra trong hai trường hợp khác hẳn nhau về ý nghĩa, và `ly_do_khong_gioi_han()` phân biệt
    chúng: vai trò làm việc toàn tập đoàn (đúng thiết kế), và tài khoản chưa được gán pháp nhân
    (chưa làm xong, phải đi gán).
    """
    if getattr(u, "role", "") in TOAN_TAP_DOAN:
        return None
    return getattr(u, "company_id", None)


def ly_do_khong_gioi_han(u: User) -> str:
    if pham_vi(u) is not None:
        return ""
    if getattr(u, "role", "") in TOAN_TAP_DOAN:
        return "vai_tro_toan_tap_doan"
    return "tai_khoan_chua_gan_phap_nhan"


def bi_gioi_han(u: User) -> bool:
    return pham_vi(u) is not None


def loc(q, model, u: User):
    """Thêm điều kiện phạm vi pháp nhân vào một truy vấn danh sách.

    Giữ lại hồ sơ CHƯA XÁC ĐỊNH – xem quy tắc 2 ở đầu file. Model không có cột company_id thì trả về
    nguyên truy vấn: im lặng bỏ qua ở đây là đúng, vì ép mọi bảng phải có pháp nhân sẽ làm hỏng các
    bảng danh mục dùng chung (ngân hàng, tài khoản kế toán, tham số) vốn không thuộc pháp nhân nào.
    """
    cid = pham_vi(u)
    if cid is None:
        return q
    col = getattr(model, "company_id", None)
    if col is None:
        return q
    return q.where(or_(col == cid, col.is_(None)))


def nhan(company_id: int | None, u: User) -> str:
    """Nhãn dán lên từng dòng để màn hình không phải đoán: '' hoặc 'chua_gan'."""
    return CHUA_GAN if company_id is None else ""


def dem(db: Session, model, u: User) -> dict:
    """Đếm theo phạm vi, trả về HAI con số tách rời – không có tổng.

    Cố tình không trả về khoá "tong". Ai cần tổng thì phải tự cộng, và lúc gõ phép cộng đó người ta
    buộc phải nhìn thấy mình đang cộng số của pháp nhân với số chưa biết thuộc về ai.
    """
    col = getattr(model, "company_id", None)
    if col is None:
        return {"cua_phap_nhan": db.execute(select(func.count()).select_from(model)).scalar() or 0,
                "chua_gan": 0, "co_cot_phap_nhan": False}
    cid = pham_vi(u)
    chua = db.execute(select(func.count()).select_from(model).where(col.is_(None))).scalar() or 0
    if cid is None:
        cua = db.execute(select(func.count()).select_from(model).where(col.is_not(None))).scalar() or 0
    else:
        cua = db.execute(select(func.count()).select_from(model).where(col == cid)).scalar() or 0
    return {"cua_phap_nhan": cua, "chua_gan": chua, "co_cot_phap_nhan": True}


def mo_ta(db: Session, u: User) -> dict:
    """Phạm vi của phiên đăng nhập, để /auth/me trả xuống và màn hình nói thẳng cho người dùng biết.

    Người dùng phải đọc được một trong ba câu, không câu nào mơ hồ:
      – "Bạn đang xem dữ liệu của <tên pháp nhân>."
      – "Bạn đang xem dữ liệu của toàn tập đoàn." (vai trò lãnh đạo/kế toán/CNTT)
      – "Tài khoản của bạn chưa được gán pháp nhân nên đang xem toàn bộ." (trạng thái phải sửa)
    """
    cid = pham_vi(u)
    ten = ""
    if cid is not None:
        c = db.get(Company, cid)
        ten = c.name if c else f"pháp nhân #{cid}"
    ly_do = ly_do_khong_gioi_han(u)
    if cid is not None:
        cau = f"Bạn đang xem dữ liệu của {ten}."
    elif ly_do == "vai_tro_toan_tap_doan":
        cau = "Bạn đang xem dữ liệu của toàn tập đoàn."
    else:
        cau = "Tài khoản của bạn chưa được gán pháp nhân nên đang xem toàn bộ dữ liệu."
    return {"company_id": cid, "company_name": ten, "bi_gioi_han": cid is not None,
            "ly_do_khong_gioi_han": ly_do, "cau_hien_thi": cau}


def bang_co_cot_phap_nhan() -> list:
    """MỌI bảng trong hệ thống có cột company_id, đọc thẳng từ mô hình.

    Vì sao phải quét từ mô hình chứ không viết tay một danh sách: bảng đối chiếu pháp nhân
    (company_scope.KINDS) chỉ kể tên NĂM loại hồ sơ – tour, booking, phiếu thu, đề nghị chi, chứng từ
    ghi sổ. Đo ngày 09/9/2026 thì hệ thống có HAI MƯƠI bảng mang cột ấy. Nghĩa là câu "không còn hồ sơ
    nào chưa gán pháp nhân" chỉ đúng cho năm bảng, và mười lăm bảng còn lại không ai nhìn tới.

    Một cột pháp nhân không ai nhìn tới thì hoặc luôn rỗng, hoặc mang giá trị do mã tự đặt mà không ai
    kiểm – và cả hai đều dẫn tới cùng một chỗ: đến kỳ hợp nhất, phần dữ liệu ấy không thuộc công ty
    nào cả. Danh sách viết tay sẽ lạc hậu ngay lần thêm bảng sau; quét từ mô hình thì không.
    """
    from app.models.core import Base
    import pkgutil, importlib
    import app.models as M
    for _, ten, _ in pkgutil.iter_modules(M.__path__):
        importlib.import_module(f"app.models.{ten}")
    ra = []
    for m in Base.registry.mappers:
        cls = m.class_
        if "company_id" in cls.__table__.c:
            ra.append(cls)
    return sorted(ra, key=lambda c: c.__tablename__)


def do_phu_kin(db: Session) -> dict:
    """Mỗi bảng có cột pháp nhân: bao nhiêu dòng đã gán, bao nhiêu chưa – ĐO trên dữ liệu thật.

    Trả về ba nhóm tách rời, vì ba nhóm là ba loại việc khác nhau:
      – da_gan_het   : không còn gì phải làm
      – con_chua_gan : có người phải đi gán, và bảng nói rõ còn bao nhiêu dòng
      – rong         : bảng chưa có dòng nào, chưa kết luận được gì

    KHÔNG cộng ba nhóm thành một tỷ lệ phần trăm: một con số 95% làm người đọc yên tâm đúng vào lúc
    5% còn lại là toàn bộ một phân hệ.
    """
    from sqlalchemy import func as F
    da_gan_het, con_chua_gan, rong = [], [], []
    for cls in bang_co_cot_phap_nhan():
        col = cls.__table__.c["company_id"]
        tong = db.execute(select(F.count()).select_from(cls)).scalar() or 0
        chua = db.execute(select(F.count()).select_from(cls).where(col.is_(None))).scalar() or 0
        dong = {"bang": cls.__tablename__, "lop": cls.__name__, "tong": tong, "chua_gan": chua,
                "da_gan": tong - chua}
        (rong if tong == 0 else (con_chua_gan if chua else da_gan_het)).append(dong)
    return {
        "da_gan_het": da_gan_het,
        "con_chua_gan": sorted(con_chua_gan, key=lambda d: -d["chua_gan"]),
        "rong": rong,
        "dem": {"so_bang": len(da_gan_het) + len(con_chua_gan) + len(rong),
                "bang_da_xong": len(da_gan_het), "bang_con_viec": len(con_chua_gan),
                "bang_rong": len(rong),
                "dong_chua_gan": sum(d["chua_gan"] for d in con_chua_gan)},
        "ghi_chu": ("Quét từ mô hình nên không lạc hậu khi thêm bảng. Bảng đối chiếu pháp nhân ở màn "
                    "hình Công ty chỉ theo dõi năm loại hồ sơ chính; danh sách này cho thấy phần còn "
                    "lại. Dòng chưa gán KHÔNG thuộc công ty mẹ – nó là 'chưa xác định', và đến kỳ hợp "
                    "nhất thì nó không thuộc công ty nào cả."),
    }
