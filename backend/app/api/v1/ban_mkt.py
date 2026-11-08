# -*- coding: utf-8 -*-
"""MKT-1 · Hai cửa đọc bàn làm việc của phòng Marketing — 09/11/2026.

KHÔNG DỰNG TIỀN TỐ API MỚI, và đây là một lần CỐ Ý ĐI NGƯỢC khuôn `/api/v1/ptgd-doan`.

Khuôn ấy dựng tiền tố riêng vì lý do ghi ở `ptgd_doan.py`: gắn nhờ vào một nhóm API có sẵn là nới
CẢ nhóm ấy cho mọi vai mở được màn hình mới. Lý do đó ĐÚNG, nhưng nó chỉ đúng khi các vai mở màn
hình mới CHƯA có nhóm ấy. Ở đây ngược lại: cả năm vai mở được hai bàn này —
`chutich · tgd · bks · robot_ks · ptgd_mkt · nv_mkt · cntt` — đều đã nằm trong dòng `"/marketing"`
của `MENU_ROLES`, tức đã gọi được `/api/v1/marketing` từ trước. Gắn vào đó thì KHÔNG một vai nào
được nới thêm một đường nào.

Còn dựng tiền tố mới thì phải khai thêm một nhóm trong `RESTRICTED_API_PREFIXES`, và điều ấy
—đúng như chú thích ở `api/v1/huong_dan.py` đã ghi— ĐỔI CON SỐ PHẠM VI CỦA MỌI VAI, nên
`test_p2_pham_vi_vai_tro` phải được đếm lại và ký lại. Nới quyền phải là một quyết định có người
ký, không phải tác dụng phụ của việc thêm hai màn hình chỉ đọc.

CÓ TIỀN LỆ TRONG CHÍNH TỆP `access.py`: dòng chú thích ở nhóm Báo chí – KOL đã nêu đúng phép thử
này — "danh sách vai của màn hình này nằm GỌN trong danh sách vai của `/marketing`".

CHỈ ĐỌC. Không cửa ghi nào ở đây. Duyệt nội dung, cho chiến dịch chạy, phát ngôn, chốt số kỳ —
bốn việc ấy đều đã có cửa riêng trên bảy tab của màn `/marketing`, với hàng rào của chúng.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ban_mkt as S

# Hẹp đúng bằng dòng "/ptgd-mkt" của MENU_ROLES. Hai chỗ lệch nhau là có vai thấy mục menu rồi bấm
# vào nhận 403, hoặc mở được cửa mà không có mục menu để tới. Phép thử đối chiếu hai bảng này.
XEM_PTGD = ("chutich", "tgd", "bks", "robot_ks", "ptgd_mkt", "cntt")

# Bàn nhân viên: thêm `nv_mkt`. `ptgd_mkt` GIỮ LẠI vì Chủ tịch chốt 09/11/2026 — người quản thấy
# cả bàn của nhân viên; giấu bàn ấy đi là lấy mất của trưởng phòng lối nhìn vào việc đang treo của
# chính phòng mình.
XEM_NV = ("chutich", "tgd", "bks", "robot_ks", "ptgd_mkt", "nv_mkt", "cntt")

router = APIRouter(prefix="/api/v1/marketing", tags=["ban-mkt"])


@router.get("/ban-ptgd")
def ban_ptgd(u: User = Depends(require_roles(*XEM_PTGD, mo_ta="bàn làm việc Phó TGĐ Marketing")),
             db: Session = Depends(get_db)):
    """Không nhận tham số kỳ: bốn ô đều là việc ĐANG TREO hôm nay, không phải báo cáo một tháng đã
    qua. Một ô chọn kỳ trên hàng đợi việc là lời mời đọc việc quá hạn của tháng trước như thể nó
    vẫn còn làm được."""
    return S.ban_ptgd(db)


@router.get("/ban-nhan-vien")
def ban_nhan_vien(u: User = Depends(require_roles(*XEM_NV, mo_ta="bàn làm việc nhân viên Marketing")),
                  db: Session = Depends(get_db)):
    """Ô lead cắt theo NGƯỜI ĐANG ĐĂNG NHẬP, không nhận tham số người.

    Nhận `nguoi_id` từ ngoài vào là mở một cửa đọc bàn của người khác mà hàng rào vai trò không
    nhìn thấy — một nhân viên gõ thêm một tham số vào đường dẫn là đọc được việc của đồng nghiệp.
    Ai cần nhìn cả phòng thì mở bảng lead của phòng ở `/marketing?tab=khach`, nơi quyền đã có chủ.
    """
    return S.ban_nhan_vien(db, u)
