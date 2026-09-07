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
from app.api.v1.ngoai_le import router as ngoai_le_router
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
            if i % 10 == 0: R.run_robots(db)         # các robot khác mỗi 10 phút
            # Dựng sẵn bảng điều khiển mỗi 2 phút khi có thay đổi: người mở trang không phải là
            # người trả giá cho lần dựng đầu (4 giây trên dữ liệu thật).
            from app.api.v1 import routes as _r
            if i % 2 == 0 and getattr(_r, "_DASH_DIRTY", True):
                _r._DASH_DIRTY = False
                _r.lam_moi_cache_nen(db)
            db.close()
        except Exception as e:  # noqa
            print("robot error", e)


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
        if settings.SEED_DEMO:
            seed_all(db)
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
app.include_router(debts_router)
app.include_router(ncc_router)
app.include_router(intake_router)
app.include_router(tep_router)
app.include_router(hd_router)


@app.get("/", include_in_schema=False)
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/api/docs"}
