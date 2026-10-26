"""V11 – Lịch tự động hóa: khai báo tác vụ, và nhận báo cáo lần chạy từ n8n.

Hai cửa vào, hai kiểu xác thực khác nhau, có chủ ý:

  · Người khai tác vụ → đăng nhập như mọi màn hình khác.
  · n8n báo lần chạy → ROBOT_TOKEN, y hệt các đường robot đã có (/robot/inbox/check,
    /robot/zalo/send-pending). KHÔNG dựng thêm một cách xác thực thứ ba cho riêng phân hệ này: mỗi
    kiểu xác thực là một chỗ phải canh, và cái yếu nhất quyết định mức an toàn của cả hệ thống.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_roles, robot_auth
from app.db.session import get_db
from app.models.core import User
from app.models.tu_dong import TacVuTuDong, HE_THONG
from app.services import tu_dong as TD
from app.services import rules as R

router = APIRouter(prefix="/api/v1/tu-dong", tags=["tu-dong-hoa"])

# Xem rộng: "cái gì đang tự chạy" là câu hỏi của cả công ty, không riêng CNTT. Một tác vụ im ba ngày
# thì người phát hiện sớm nhất thường là người của phòng đang chờ số liệu đó, không phải kỹ thuật.
XEM = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "bks", "cntt", "ketoan", "hcns",
       "tp_dh", "nv_dh", "gd_doi_xe", "tp_hd", "gd_kd", "tp_kd")
# Khai báo hẹp: mã tác vụ ở đây phải khớp với mã bên n8n, sai một chữ là lần chạy báo về không tìm
# thấy chỗ đậu.
KHAI = ("cntt", "chutich", "tgd")


class TacVuIn(BaseModel):
    ma: str
    ten: str
    mo_ta: str = ""
    he_thong: str = "n8n"
    lich_doc: str = ""
    lich_cron: str = ""
    phong_ban: str = ""
    nguoi_phu_trach: str = ""
    han_toi_da_phut: int = 0
    quan_trong: bool = False
    bat: bool = True
    ly_do_tat: str = ""


@router.get("")
def bang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return TD.bang(db)


@router.get("/im-lang")
def im_lang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Chỉ những tác vụ đang quá hạn – dùng cho báo cáo sáng và cho robot Kiểm soát."""
    return {"tac_vu": TD.im_lang(db)}


@router.post("/tac-vu", status_code=201)
def khai_bao(data: TacVuIn, u: User = Depends(require_roles(*KHAI)), db: Session = Depends(get_db)):
    if data.he_thong not in HE_THONG:
        raise HTTPException(422, f"Hệ thống phải là một trong {list(HE_THONG)}")
    ma = data.ma.strip()
    if not ma:
        raise HTTPException(422, "Thiếu mã tác vụ")
    if db.execute(select(TacVuTuDong).where(TacVuTuDong.ma == ma)).scalars().first():
        raise HTTPException(422, f"Đã có tác vụ mã '{ma}'")
    t = TacVuTuDong(**{**data.model_dump(), "ma": ma}, tao_boi=u.username)
    db.add(t); db.flush()
    R.audit(db, u.username, u.role, "khai_tac_vu_tu_dong", f"tac_vu:{ma}",
            after={"ten": t.ten, "han_toi_da_phut": t.han_toi_da_phut})
    db.commit()
    return {**TD.ra(db, t), "message": f"Đã khai tác vụ {ma}. "
            "Cấu hình luồng bên ngoài gửi mã này về mỗi lần chạy thì màn hình mới có số liệu."}


@router.put("/tac-vu/{tid}")
def sua(tid: int, data: TacVuIn, u: User = Depends(require_roles(*KHAI)),
        db: Session = Depends(get_db)):
    t = db.get(TacVuTuDong, tid)
    if t is None: raise HTTPException(404, "Không có tác vụ này")
    truoc = {"ma": t.ma, "bat": t.bat, "han_toi_da_phut": t.han_toi_da_phut}
    # Tắt phải ghi lý do. Không bắt buộc thì ô này luôn trống, và một tác vụ bị tắt trông giống hệt
    # một tác vụ bị quên – hai cái cần hai cách xử lý ngược nhau.
    if not data.bat and not (data.ly_do_tat or "").strip():
        raise HTTPException(422, "Tắt một tác vụ phải ghi lý do – để sau này phân biệt được 'tắt có "
                                 "chủ ý' với 'quên bật lại'.")
    for k, v in data.model_dump().items():
        if k == "ma":
            continue          # đổi mã là cắt đứt nối với luồng bên ngoài; muốn đổi thì khai tác vụ mới
        setattr(t, k, v)
    t.sua_luc = datetime.now()
    R.audit(db, u.username, u.role, "sua_tac_vu_tu_dong", f"tac_vu:{t.ma}",
            before=truoc, after={"bat": t.bat, "han_toi_da_phut": t.han_toi_da_phut})
    db.commit()
    return TD.ra(db, t)


@router.get("/tac-vu/{tid}/lan-chay")
def lan_chay(tid: int, limit: int = 50, u: User = Depends(require_roles(*XEM)),
             db: Session = Depends(get_db)):
    from app.models.tu_dong import LanChayTacVu
    t = db.get(TacVuTuDong, tid)
    if t is None: raise HTTPException(404, "Không có tác vụ này")
    q = (select(LanChayTacVu).where(LanChayTacVu.tac_vu_id == tid)
         .order_by(LanChayTacVu.bat_dau.desc()).limit(min(limit, 300)))
    return {"tac_vu": t.ma, "lan_chay": [TD._lan_ra(l) for l in db.execute(q).scalars()]}


class BaoCaoIn(BaseModel):
    ma_tac_vu: str
    ma_lan: str
    trang_thai: str                       # dang_chay / thanh_cong / that_bai / mot_phan
    bat_dau: datetime | None = None
    ket_thuc: datetime | None = None
    so_ban_ghi: int | None = None         # None = không đếm được; 0 = chạy xong, không có gì để làm
    thong_bao: str = ""
    chi_tiet: dict | None = None
    boi: str = "n8n"


@router.post("/bao-cao", status_code=201, dependencies=[Depends(robot_auth)])
def bao_cao(data: BaoCaoIn, db: Session = Depends(get_db)):
    """n8n gọi vào đây mỗi lần chạy – cả lúc bắt đầu lẫn lúc xong.

    Gọi lại cùng ma_lan thì cập nhật dòng cũ, không tạo dòng thứ hai: n8n thử lại khi mạng chập, và
    một lần chạy đếm thành hai làm hỏng đúng con số mà màn hình này sinh ra để cho người ta tin.
    """
    try:
        l, moi, su_kien = TD.ghi_lan_chay(db, data.ma_tac_vu, data.ma_lan, data.trang_thai,
                                          bat_dau=data.bat_dau, ket_thuc=data.ket_thuc,
                                          so_ban_ghi=data.so_ban_ghi, thong_bao=data.thong_bao,
                                          chi_tiet=data.chi_tiet, boi=data.boi)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    # Ghi sự kiện SAU khi commit: một sự kiện nói "vừa nhận một lần chạy hỏng" không được nhìn thấy
    # trước bản ghi mà nó nói tới. Xem chú thích trong services/tu_dong.ghi_lan_chay.
    TD.day_su_kien(su_kien)
    return {**TD._lan_ra(l), "moi": moi,
            "message": "Đã ghi lần chạy" if moi else "Đã cập nhật lần chạy đã có (cùng mã lần)"}


@router.post("/quet-im-lang", dependencies=[Depends(robot_auth)])
def quet_im_lang(db: Session = Depends(get_db)):
    """Đẩy các tác vụ đang quá hạn vào sổ sự kiện kỹ thuật để robot Kiểm soát đọc (K6).

    Đứng riêng thành một đường gọi theo lịch, KHÔNG chạy khi ai đó mở màn hình: một hàm đọc mà lại
    ghi thì mở màn hình mười lần sẽ đếm thành mười sự kiện.
    """
    n = TD.quet_im_lang(db)
    return {"so_tac_vu_im": n,
            "message": f"{n} tác vụ đang quá hạn – đã ghi vào sổ sự kiện kỹ thuật" if n
                       else "Không có tác vụ nào quá hạn"}


# ── BG-1 · Cửa nhận báo cáo ngày từ hệ Google ─────────────────────────────────────────────────
# Đậu ở phân hệ này chứ không ở `ops.py` vì hai lý do, và lý do thứ hai mới là lý do thật:
#   · đây đúng là một cửa ROBOT báo số về — cùng kiểu xác thực ROBOT_TOKEN với cửa n8n ngay trên;
#   · `api/v1/ops.py` và `services/ops.py` đang được làn Phân quyền giữ cho BC-1 và BC-2, và hai
#     làn cùng viết một tệp là đúng thứ hàng rào giữ chỗ sinh ra để chặn.
# Toàn bộ phép tính nằm ở `services/bao_cao_google.py`; ở đây chỉ có hình của lời gọi.
from datetime import date as _date   # noqa: E402
from app.services import bao_cao_google as BG   # noqa: E402


class GoogleItemIn(BaseModel):
    maNV: str = ""
    ngay: _date | None = None
    hoTen: str = ""
    chucDanh: str = ""
    phong: str = ""
    phongGoogle: str = ""
    nopLuc: str = ""
    lanGui: int = 1
    email: str = ""
    nghiPhep: str = ""
    phan1: str = ""
    phan3: str = ""
    phan4: str = ""
    soLieu: list[list[str]] = []
    fileDinhKem: str = ""
    diemRobot: float | None = None
    xepLoaiRobot: str = ""
    canhBao: list[str] = []
    nguonDiem: str = ""


class GoogleBatchIn(BaseModel):
    nguon: str = ""
    phienBan: int = 1
    loai: str = "baocao"
    guiLuc: str = ""
    baoCao: list[GoogleItemIn] = []


@router.post("/bao-cao-ngay/nhan-tu-google", dependencies=[Depends(robot_auth)])
def nhan_bao_cao_ngay_tu_google(data: GoogleBatchIn, db: Session = Depends(get_db)):
    """Nhận báo cáo ngày hệ Google đẩy sang. Khoá (mã nhân viên, ngày) – gửi lại là ĐÈ.

    `loai`: `baocao` nội dung năm phần · `diem` điểm robot của hệ Google · `thu` gọi thử, không ghi gì.
    """
    if data.loai == "thu":
        return {"ok": True, "nhan": 0, "loi": [], "ghi_chu": "gọi thử – không ghi gì"}
    if data.loai not in ("baocao", "diem"):
        raise HTTPException(422, "loai phải là baocao, diem hoặc thu")
    if len(data.baoCao) > 100:
        raise HTTPException(413, "Mỗi lần gửi tối đa 100 bản ghi")
    return BG.nhan(db, [x.model_dump() for x in data.baoCao], data.loai)
