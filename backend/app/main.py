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
from app.api.v1.ks_ra_soat import router as ks_ra_soat_router
from app.api.v1.ks_ra_soat import rst as rst_router
from app.services import rules as R
from app.services import accounting as ACC
from app.services.seed import seed_all


async def robot_loop():
    i = 0
    while True:
        await asyncio.sleep(60); i += 1
        try:
            db = SessionLocal()
            from app.services import inbox as IB
            IB.robot_check(db)                      # R12 mỗi phút: AI trả lời thay khi sale trễ SLA
            from app.services import ky_thuat as KT
            KT.nap_nguong(db)       # ngưỡng "chậm bất thường" nằm ở tham số chính sách, không viết cứng
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
            db.close()
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


@app.get("/", include_in_schema=False)
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/api/docs"}
