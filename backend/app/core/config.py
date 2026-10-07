"""Cấu hình từ biến môi trường (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    APP_NAME: str = "VTOS API"
    APP_VERSION: str = "0.2.0"
    ENV: str = "dev"                       # dev | prod
    DATABASE_URL: str = "sqlite:///./vtos.db"
    SECRET_KEY: str = "doi-khoa-nay-truoc-khi-chay-that"
    ACCESS_TOKEN_MINUTES: int = 12 * 60
    ROBOT_TOKEN: str = "doi-robot-token"
    SEED_DEMO: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    TZ: str = "Asia/Ho_Chi_Minh"
    # Lưu tài liệu hồ sơ Visa. Ổ đĩa của Render là TẠM – deploy lại là mất, nên tài liệu thật của khách phải
    # nằm trên kho đối tượng (Cloudflare R2 / Amazon S3). Quyết định của Chủ tịch ngày 06/9/2026.
    #   VISA_STORAGE = auto  -> có đủ bucket + khóa thì dùng S3, không thì dùng thư mục (máy lập trình, test)
    #   VISA_STORAGE = s3    -> BẮT BUỘC dùng S3, thiếu cấu hình là báo lỗi ngay thay vì âm thầm ghi vào ổ tạm
    VISA_STORAGE: str = "auto"                 # auto | s3 | local
    VISA_DOC_DIR: str = ""                     # chỉ dùng cho nền "local"
    S3_BUCKET: str = ""
    S3_ENDPOINT_URL: str = ""                  # R2: https://<account_id>.r2.cloudflarestorage.com
    S3_REGION: str = "auto"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    # Nơi lưu tài liệu hồ sơ Visa. Ổ đĩa Render là TẠM (mất khi deploy lại) – trước khi dùng thật phải trỏ
    # vào Render Disk gắn kèm hoặc thay bằng S3. Hệ thống lưu sha256 nên phát hiện được tệp mất/đổi.
    VISA_DOC_DIR: str = ""
    SEPAY_WEBHOOK_KEY: str = ""            # khóa đặt trong SePay → Webhook → Authorization: Apikey <key>
    SEPAY_API_TOKEN: str = ""              # token User API (my.sepay.vn → Cấu hình → API Access) để VTOS kéo giao dịch
    SEPAY_ACCOUNT_NUMBER: str = ""
    VIETRIP_PHONE: str = ""                # tài khoản robot Vietrip (chỉ đọc – Kế toán/Giám đốc) để đồng bộ tự động
    VIETRIP_PASSWORD: str = ""         # số TK ngân hàng mặc định khi kéo (trống = mọi TK trong SePay)
    COMPANY_NAME: str = "CÔNG TY CỔ PHẦN DU LỊCH VIETOURIST"
    COMPANY_TAX_CODE: str = ""
    ANTHROPIC_API_KEY: str = ""            # robot R7 viết nhận xét báo cáo (không có → nhận xét theo quy tắc)
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    ZALO_OA_ACCESS_TOKEN: str = ""         # Zalo Official Account – access token (developers.zalo.me); anh tự dán vào Render env
    ZALO_OA_REFRESH_TOKEN: str = ""
    ZALO_APP_ID: str = ""
    ZALO_APP_SECRET: str = ""
    ZALO_OA_SECRET_KEY: str = ""           # khóa xác thực webhook OA (X-ZEvent-Signature)
    ZALO_ZNS_TEMPLATES: str = ""
    FB_PAGE_ACCESS_TOKEN: str = ""         # Facebook Page (Messenger Platform) – token trang, anh tự dán vào Render
    FB_PAGE_ID: str = ""
    FB_APP_SECRET: str = ""
    FB_APP_ID: str = ""                # xác thực chữ ký webhook (X-Hub-Signature-256)
    FB_VERIFY_TOKEN: str = "vtos-fb-verify"  # chuỗi xác minh khi đăng ký webhook trên Meta for Developers           # "nhac_coc:1234,xac_nhan_booking:2345" – mẫu ZNS đã duyệt             # MST pháp nhân – điền trong .env / Render env

    # ---- Conversions API: bao nguoc doanh thu that len Meta. Xem app/services/gui_meta.py ----
    # KHONG dung lai FB_PAGE_ACCESS_TOKEN o tren: token Trang la cho Messenger, token duoi day
    # phai co quyen ads_management tren Dataset. Lay nham thi Meta tra loi QUYEN, ma loi quyen
    # doc rat giong loi du lieu - mat nua ngay moi lan ra.
    FB_DATASET_ID: str = ""                  # ID Dataset / Pixel cua Vietourist (Trinh quan ly su kien)
    FB_CAPI_TOKEN: str = ""                  # token co quyen ads_management - anh hoac CNTT dan vao Render
    FB_CAPI_VERSION: str = "v25.0"           # ban Graph API dang hieu luc (tra 07/10/2026)
    FB_CAPI_EVENT_NAME: str = "Purchase"     # khach da mua tour va co so tien - doi duoc neu MKT dung pheu nhieu bac
    FB_CAPI_ACTION_SOURCE: str = ""          # de rong = tu suy (xem gui_meta._nguon_hanh_dong)
    FB_CAPI_TEST_EVENT_CODE: str = ""        # bat len de thu tren Trinh kiem tra su kien, KHONG tinh vao bao cao

    # ---- TikTok Events API 2.0, nguon CRM. Xem app/services/gui_tiktok.py ----
    # CANH BAO cho nguoi doc ma: TikTok doi so dien thoai dang "+84..." con Meta doi
    # "84..." khong dau cong. Hai ham bam nam o hai tep va PHAI giu rieng.
    TT_EVENT_SET_ID: str = ""                # CRM Event Set ID - lay bang cua /crm/list/
    TT_ACCESS_TOKEN: str = ""                # token TikTok Business API - CNTT dan vao Render
    TT_API_VERSION: str = "v1.3"             # ban Events API (tra 07/10/2026)
    TT_EVENT_NAME: str = "VTOS_ChotTour"     # su kien CRM BAT BUOC la ten tuy chinh - khong
                                             # dung duoc "Purchase". MKT phai khai DUNG ten nay
                                             # trong Trinh quan ly su kien TikTok.


settings = Settings()
# Render/Heroku cấp DATABASE_URL dạng postgres:// – SQLAlchemy cần postgresql+psycopg2://
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
