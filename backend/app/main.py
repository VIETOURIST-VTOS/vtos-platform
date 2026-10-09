"""VTOS API – điểm vào FastAPI."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import SessionLocal, engine, Base
from app.api.v1.routes import router
from app.api.v1.payments import router as payments_router
from app.api.v1.accounting import router as accounting_router
from app.api.v1.assets import router as assets_router
from app.api.v1.books import router as books_router
from app.api.v1.banks import router as banks_router
from app.api.v1.hr import router as hr_router
from app.api.v1.companies import router as companies_router
from app.api.v1.hrm import router as hrm_router
from app.api.v1.phap_che import router as phap_che_router
from app.api.v1.phap_che_viec import router as phap_che_viec_router
from app.api.v1.nha_dau_tu import router as nha_dau_tu_router
from app.api.v1.ops import router as ops_router
from app.api.v1.finance import router as finance_router
from app.api.v1.vietrip import router as vietrip_router
from app.api.v1.products import router as products_router
from app.api.v1.settlement import router as settlement_router
from app.api.v1.nonpackage import router as nonpackage_router
from app.api.v1.sales_reports import router as sales_reports_router
from app.api.v1.crm import router as crm_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.visa import router as visa_router
from app.api.v1.fleet import router as fleet_router
from app.api.v1.access import router as access_router
from app.api.v1.ai_roles import router as ai_roles_router
from app.api.v1.debts import router as debts_router
from app.api.v1.marketing import router as marketing_router
from app.api.v1.suppliers import router as ncc_router
from app.api.v1.intake import router as intake_router
from app.api.v1.attachments import router as tep_router
from app.api.v1.huong_dan import router as hd_router
from app.api.v1.quyet_toan_tour import router as qtt_router
from app.api.v1.doc_chung_tu import router as dct_router
from app.api.v1.ket_so import router as ks_router
from app.api.v1.ngoai_le import router as ngoai_le_router
from app.api.v1.kiem_soat import router as kiem_soat_router
from app.api.v1.hach_toan import router as hach_toan_router
from app.api.v1.cskh import router as cskh_router
from app.api.v1.dau_quang_cao import router as dau_quang_cao_router
from app.api.v1.ban_hang import router as ban_hang_router
from app.api.v1.tu_dong import router as tu_dong_router
from app.api.v1.bao_cao import router as bao_cao_router
# TC-71 · Sổ chuyến còn nợ có TIỀN TỐ RIÊNG, không nằm trong /api/v1/bao-cao — lý do ghi ở đầu
# app/api/v1/so_con_no.py (gắn vào nhóm báo cáo là nới cả nhóm cho hai vai chỉ cần một cửa).
from app.api.v1.so_con_no import router as so_con_no_router
from app.api.v1.ks_ra_soat import router as ks_ra_soat_router
from app.api.v1.ks_ra_soat import rst as rst_router
from app.api.v1.lai_lo_tour import router as ll_router
from app.api.v1.dong_tien import router as dong_tien_router
from app.api.v1.quyet_toan_lop3 import router as qt_lop3_router
# V7 Đợt 3 (10/9/2026)
from app.api.v1.su_co_tour import router as su_co_router
from app.api.v1.kiem_toan import router as kiem_toan_router
from app.api.v1.ty_gia import router as ty_gia_router
# Ba bang HCNS mo cung mot migration 09/10/2026. BON router cho BA bang: 5.6 tach lam hai duong
# (nguoi cham di theo man hinh /hr, ban-cua-toi di theo /cham-cong da mo cho moi nguoi), vi nhet
# chung mot tien to thi hoac phai noi /hr cho ca cong ty hoac nhan vien khong voi toi cua ay.
from app.api.v1.danh_gia_ns import router as danh_gia_ns_router, router_toi as danh_gia_toi_router
from app.api.v1.mua_sam import router_mua as de_nghi_mua_router, router_cap as cap_phat_router
# TC-41 (16/9/2026) – cửa nhập kế hoạch tháng, anh Tuấn duyệt 15/9.
from app.api.v1.ke_hoach import router as ke_hoach_router
# TC-73 – co cau to chuc khoi Kinh doanh. Tien to RIENG `/api/v1/to-chuc-kd`, cung ly do da ghi o
# dong so_con_no.py ngay tren: gan vao mot nhom co san la noi CA NHOM cho moi vai dang co nhom ay.
from app.api.v1.to_chuc_kd import router as to_chuc_kd_router
# TC-74 - nguoi ban hang: doi tac ngoai cong ty va quyen ban cua nhan vien ngoai khoi.
from app.api.v1.nguoi_ban_hang import router as nguoi_ban_hang_router
from app.api.v1.gop_tai_khoan import router as gop_tai_khoan_router
from app.api.v1.bao_chi_kol import router as bao_chi_kol_router
from app.api.v1.kinh_doanh import router as kinh_doanh_router
from app.api.v1.dong_gop_marketing import router as dong_gop_marketing_router
from app.api.v1.chuyen_doi_lead import router as chuyen_doi_lead_router
from app.api.v1.doi_soat_marketing import router as doi_soat_marketing_router
# 24/9/2026 - ban lam viec cua Pho TGD tour doan. Tien to RIENG, cung ly do da ghi o so_con_no.py.
from app.api.v1.ptgd_doan import router as ptgd_doan_router
from app.api.v1.ban_tour_le import router as ban_tour_le_router
from app.api.v1.danh_gia import router as danh_gia_router
from app.api.v1.tai_xe import router as tai_xe_router
from app.api.v1.khao_sat_cong_khai import router as khao_sat_cong_khai_router
from app.api.v1.sales_admin import router as sales_admin_router
from app.services import rules as R
from app.services import accounting as ACC
from app.services.seed import seed_all


# ══════════════════════════════════════════════════════════════════════════════════════════════
# VIỆC NỀN CHẠY Ở LUỒNG RIÊNG — TC-94, 28/9/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# ĐO ĐƯỢC TRÊN MÁY CHỦ THẬT, không phải suy đoán. Render báo "HTTP health check failed (timed out
# after 5 seconds)" đều đặn mỗi 12–13 phút suốt ngày 28/9 (08:38 · 08:50 · 09:03 · 09:34 · 09:47 ·
# 09:59 · 10:14 · 10:26 · 10:39 · … · 22:07). Nhật ký ứng dụng ghi lời chào health check mỗi ~5
# giây; lúc 20:14:12 → 20:14:34 KHÔNG CÓ DÒNG NÀO — một khoảng câm **22 giây**.
#
# Vì sao 12–13 phút chứ không phải 10: chu kỳ thật của vòng này là 60 giây CỘNG thời gian làm việc,
# nên nhánh `i % 10` trôi dần. 10 lượt × (60 + ~15) giây ≈ 12,5 phút — khớp đúng khoảng cách đo được.
#
# Hậu quả người dùng KHÔNG báo vì nó tự khỏi: cứ ~12 phút, mọi người đang mở VTOS bị đứng máy vài
# giây. Render chờ 5 giây rồi kêu; người thì bấm lại và cho qua.
#
# NGUYÊN NHÂN là hình dạng của mã, không phải một phép tính nào sai: `robot_loop` là hàm `async`,
# nhưng thân nó gọi THẲNG các việc cơ sở dữ liệu — mà chúng đồng bộ. Trong lúc chúng chạy, vòng lặp
# sự kiện của uvicorn không quay được, nên máy chủ không trả lời một ai. Việc nền không có lỗi; chỗ
# nó đứng mới có lỗi.
#
# CÁCH SỬA: một lượt việc nền nằm gọn trong một hàm ĐỒNG BỘ (`_mot_luot_robot`), và vòng `async`
# đẩy nó sang luồng khác bằng `asyncio.to_thread`. Vòng lặp sự kiện rảnh ngay.
#
# Ba điều CỐ Ý GIỮ NGUYÊN, để bản vá này không lặng lẽ đổi hành vi nào khác:
#   · vẫn MỘT lượt một lúc — `await` chặn tới khi luồng xong, nên không có hai lượt chồng nhau;
#   · vẫn đúng nhịp cũ: mỗi phút, `i % 10`, `i % 2`;
#   · phiên cơ sở dữ liệu mở và đóng BÊN TRONG luồng ấy, không dùng chung với luồng chính.
def _mot_luot_robot(i: int) -> None:
    """MỘT lượt việc nền. Hàm ĐỒNG BỘ, cố ý — nó được gọi trong một luồng riêng, không trên vòng
    lặp sự kiện. Đừng biến nó thành `async`, và đừng gọi thẳng nó từ `robot_loop`."""
    db = SessionLocal()
    try:
        from app.services import inbox as IB
        IB.robot_check(db)                      # R12 mỗi phút: AI trả lời thay khi sale trễ SLA
        from app.services import ky_thuat as KT
        KT.nap_nguong(db)       # ngưỡng "chậm bất thường" nằm ở tham số chính sách, không viết cứng
        # Lịch theo GIỜ (09/9/2026). Vòng lặp này đếm phút từ lúc khởi động nên không làm đúng
        # được việc "20:30 mỗi ngày": mỗi lần deploy là bộ đếm về 0, và báo cáo của hôm đó bị bỏ
        # luôn mà không ai biết. app/services/lich_trong.py khóa theo MÃ KỲ suy từ đồng hồ tường,
        # nên việc bị lỡ được làm bù và không bao giờ chạy hai lần trong một kỳ.
        #
        # Gọi mỗi phút, KHÔNG kèm điều kiện i % n: bản thân mã kỳ đã là điều kiện, và đặt thêm
        # một điều kiện thứ hai ở đây là dựng hai chỗ quyết định cho cùng một việc.
        try:
            from app.services import lich_trong as LT
            LT.den_luot(db)
        except Exception as e:  # noqa
            print("lich trong error", e)
        if i % 10 == 0: R.run_robots(db)         # các robot khác mỗi 10 phút
        if i % 10 == 0:
            # Sinh phiếu chăm sóc cho tour vừa kết thúc và cảnh báo khiếu nại quá hạn phản hồi.
            # Tách khỏi run_robots để một lỗi ở đây không làm chết cả cụm robot cũ.
            try:
                from app.services import cskh as CS
                CS.robot_cskh(db)
            except Exception as e:  # noqa
                print("robot cskh error", e)
        # Dựng sẵn bảng điều khiển mỗi 2 phút khi có thay đổi: người mở trang không phải là
        # người trả giá cho lần dựng đầu (4 giây trên dữ liệu thật).
        from app.api.v1 import routes as _r
        if i % 2 == 0 and getattr(_r, "_DASH_DIRTY", True):
            _r._DASH_DIRTY = False
            _r.lam_moi_cache_nen(db)
    finally:
        # `finally` chứ không phải dòng cuối thân hàm: trước TC-94, một lỗi giữa chừng làm
        # `db.close()` không bao giờ chạy, và mỗi lượt hỏng bỏ lại một kết nối treo.
        db.close()


async def robot_loop():
    i = 0
    while True:
        await asyncio.sleep(60); i += 1
        try:
            # ĐẨY SANG LUỒNG KHÁC. Đây là cả nội dung của bản vá TC-94; đừng đổi lại thành gọi
            # thẳng `_mot_luot_robot(i)` — xem lời khai dài ở trên, và phép thử
            # `test_tc94_viec_nen_khong_chan_may_chu.py` canh đúng dòng này.
            await asyncio.to_thread(_mot_luot_robot, i)
        except Exception as e:  # noqa
            print("robot error", e)
            # Tác vụ nền hỏng thì không hiện trên màn hình nào – phải ghi lại, nếu không nó dừng lặng lẽ.
            try:
                import traceback
                from app.services import ky_thuat as KT
                KT.ghi_moi_phien("tac_vu_nen", muc="do", duong_dan="robot_loop",
                                 thong_bao=f"{type(e).__name__}: {str(e)[:300]}",
                                 dau_vet=traceback.format_exc())
            except Exception:  # noqa
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENV == "dev":
        Base.metadata.create_all(engine)          # prod dùng alembic upgrade head
    db = SessionLocal()
    try:
        R.seed_params(db)
        ACC.seed_accounts(db)
        from app.services.visa import seed_visa
        seed_visa(db)          # thị trường UK + mẫu checklist UK (phạm vi đầu tiên của phân hệ Visa)
        # Bảng quyền AI phải có mặt từ lúc khởi động, không đợi ai mở màn hình: robot hộp thư đọc bảng
        # này trước mỗi lần định gửi, nên bảng rỗng nghĩa là sau một lần triển khai mới, AI im lặng mà
        # không ai biết vì sao. Hàm chỉ thêm dòng còn thiếu, không đụng tới mức lãnh đạo đã sửa.
        from app.services.ai_quyen import nap_mac_dinh as nap_quyen_ai
        nap_quyen_ai(db); db.commit()
        # Bộ quy ước hạch toán cũng phải có mặt từ lúc khởi động: bảng rỗng thì mọi nghiệp vụ đều rơi
        # vào "không có quy tắc khớp" và kế toán lại định khoản tay – đúng cái việc bảng này thay thế.
        from app.services.hach_toan import nap_mac_dinh as nap_quy_tac
        nap_quy_tac(db)
        # Các việc chạy theo lịch bên trong VTOS tự khai vào bảng tác vụ V11, để chúng hiện trên màn
        # hình Lịch tự động hóa cùng chỗ với việc chạy ở hệ thống ngoài – một chỗ nhìn, không phải hai.
        # Chỉ thêm dòng còn thiếu và cập nhật mô tả; KHÔNG bật lại việc mà người đã tắt.
        from app.services.lich_trong import dam_bao_khai_bao
        dam_bao_khai_bao(db)
        if settings.SEED_DEMO:
            seed_all(db)
        # K6 – một dòng mỗi lần máy chủ lên, kèm trạng thái mạch nâng cấp. Đây là dữ kiện duy nhất
        # về lần khởi động mà tiến trình này quan sát được, vì lệnh nâng cấp chạy trước nó.
        try:
            from app.services import ky_thuat as KT
            KT.nap_nguong(db); KT.ghi_khoi_dong(db)
            # K1/K2 – quyết định của Chủ tịch ngày 08/9/2026 về xếp loại cột tiền và hướng xử lý
            # "thiếu ≠ 0". Nạp ở đây để lần triển khai nào cũng có mặt; hàm chỉ điền ô còn trống,
            # không đè lên quyết định ghi sau đó.
            from app.services import ks_cot_tien as CT
            CT.nap_quyet_dinh(db)
        except Exception as e:  # noqa
            print("ghi khoi dong error", e)
    finally:
        db.close()
    task = asyncio.create_task(robot_loop())
    yield
    task.cancel()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan,
              docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")
@app.middleware("http")
async def _danh_dau_dashboard_cu(request, call_next):
    """Thao tác ghi làm bảng điều khiển CŨ ĐI, nhưng không xoá trắng cache.

    Bản trước xoá sạch cache sau MỌI lần POST/PUT/DELETE. Trên hệ thống thật, nhân viên tạo booking,
    ghi phiếu thu, gửi đề nghị chi suốt cả ngày – nghĩa là cache gần như luôn trống, và gần như ai mở
    trang chủ cũng phải trả giá cho một lần dựng lại từ đầu. Đó là lý do trang "lúc nào cũng chậm".

    Nay chỉ đánh dấu cũ. Robot nền dựng lại mỗi 2 phút, người mở trang luôn nhận bản có sẵn – chậm
    nhất là cũ vài phút, đúng bản chất của một bảng điều khiển tổng hợp.
    """
    resp = await call_next(request)
    if request.method != "GET":
        from app.api.v1 import routes as _r
        _r._DASH_DIRTY = True
    return resp


@app.middleware("http")
async def _ghi_su_kien_ky_thuat(request, call_next):
    """K6 – ghi lỗi máy chủ và đường dẫn chậm bất thường để robot Kiểm soát đọc được.

    Trước lớp này robot mù hoàn toàn với sức khỏe máy chủ: ngày 07/9/2026 endpoint /meta trả 500 cho
    mọi vai trò trên hệ thống thật, và thứ tìm ra nó là bộ quét vai trò chứ không phải bộ theo dõi lỗi.

    Lớp này KHÔNG được làm hỏng yêu cầu nào. Ngoại lệ của người dùng vẫn ném lên như cũ; việc ghi nằm
    trong try riêng và nuốt mọi lỗi của chính nó.
    """
    import time as _t
    from app.services import ky_thuat as KT
    t0 = _t.perf_counter()
    try:
        resp = await call_next(request)
    except Exception as ex:      # noqa
        import traceback
        KT.ghi_moi_phien("loi_5xx", muc="do", duong_dan=request.url.path,
                         phuong_thuc=request.method, ma_trang_thai=500,
                         mili_giay=int((_t.perf_counter() - t0) * 1000),
                         thong_bao=f"{type(ex).__name__}: {str(ex)[:300]}",
                         dau_vet=traceback.format_exc())
        raise
    ms = int((_t.perf_counter() - t0) * 1000)
    try:
        p = request.url.path
        if resp.status_code >= 500:
            KT.ghi_moi_phien("loi_5xx", muc="do", duong_dan=p, phuong_thuc=request.method,
                             ma_trang_thai=resp.status_code, mili_giay=ms,
                             thong_bao=f"Máy chủ trả {resp.status_code}")
        elif ms > KT.NGUONG_CHAM_MS and not any(p.startswith(x) for x in KT.BO_QUA_CHAM):
            KT.ghi_moi_phien("cham", muc="vang", duong_dan=p, phuong_thuc=request.method,
                             ma_trang_thai=resp.status_code, mili_giay=ms,
                             thong_bao=f"Chạy {ms} mili giây, quá ngưỡng {KT.NGUONG_CHAM_MS}")
    except Exception:      # noqa
        pass
    return resp


app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(products_router)
app.include_router(settlement_router)
app.include_router(nonpackage_router)
app.include_router(sales_reports_router)
app.include_router(crm_router)
app.include_router(inbox_router)
app.include_router(payments_router)
app.include_router(accounting_router)
app.include_router(assets_router)
app.include_router(books_router)
app.include_router(banks_router)
app.include_router(hr_router)
app.include_router(companies_router)
app.include_router(hrm_router)
app.include_router(phap_che_router)
app.include_router(phap_che_viec_router)
app.include_router(nha_dau_tu_router)
app.include_router(marketing_router)
app.include_router(ops_router)
app.include_router(finance_router)
app.include_router(vietrip_router)
app.include_router(visa_router)
app.include_router(fleet_router)
app.include_router(access_router)
app.include_router(ai_roles_router)
app.include_router(ngoai_le_router)
app.include_router(kiem_soat_router)
app.include_router(hach_toan_router)
app.include_router(cskh_router)
app.include_router(dau_quang_cao_router)
app.include_router(ban_hang_router)
app.include_router(tu_dong_router)
app.include_router(bao_cao_router)
app.include_router(so_con_no_router)
app.include_router(ks_ra_soat_router)
app.include_router(rst_router)
app.include_router(debts_router)
app.include_router(ncc_router)
app.include_router(intake_router)
app.include_router(tep_router)
app.include_router(hd_router)
app.include_router(qtt_router)
app.include_router(dct_router)
app.include_router(ks_router)
app.include_router(ll_router)
app.include_router(qt_lop3_router)
# Robot A · GD-1. Ba lần trong tuần này một phân hệ viết xong mà quên dòng đăng ký router:
# mã có đủ, đường dẫn trả 404, và không phép thử nào kêu vì không ai gọi thử.
app.include_router(dong_tien_router)
app.include_router(su_co_router)
app.include_router(kiem_toan_router)
# Robot A · 16/9/2026. Cửa tỷ giá – Chủ tịch chốt nhân viên tự nhập tại từng thời điểm.
app.include_router(ty_gia_router)
app.include_router(danh_gia_ns_router)
app.include_router(danh_gia_toi_router)
app.include_router(de_nghi_mua_router)
app.include_router(cap_phat_router)
app.include_router(ke_hoach_router)
app.include_router(to_chuc_kd_router)
app.include_router(nguoi_ban_hang_router)
app.include_router(gop_tai_khoan_router)
app.include_router(bao_chi_kol_router)
app.include_router(kinh_doanh_router)
app.include_router(dong_gop_marketing_router)
app.include_router(chuyen_doi_lead_router)
app.include_router(doi_soat_marketing_router)
app.include_router(ptgd_doan_router)
app.include_router(sales_admin_router)
app.include_router(ban_tour_le_router)
app.include_router(danh_gia_router)
app.include_router(tai_xe_router)
# Công nợ Vietrip hằng ngày (phải thu + phải trả theo dự toán tour). Gắn lại 29/9/2026: lượt gộp
# TC-94 ghi đè hai dòng này nên cả /api/v1/cong-no-vietrip trả 404. Phép thử
# test_cong_no_vietrip.test_cua_cong_no_vietrip_duoc_gan_vao_app canh không để mất lần nữa.
from app.api.v1.cong_no_vietrip import router as cong_no_vietrip_router  # noqa: E402
app.include_router(cong_no_vietrip_router)
# CỬA CÔNG KHAI — cửa DUY NHẤT của VTOS không cần đăng nhập. Để cuối danh sách và có dòng chú
# thích này để ai đọc app/main.py cũng nhìn thấy nó, thay vì phát hiện ra khi đọc tệp thứ tám.
app.include_router(khao_sat_cong_khai_router)


@app.get("/", include_in_schema=False)
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/api/docs"}
