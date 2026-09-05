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
    FB_APP_SECRET: str = ""                # xác thực chữ ký webhook (X-Hub-Signature-256)
    FB_VERIFY_TOKEN: str = "vtos-fb-verify"  # chuỗi xác minh khi đăng ký webhook trên Meta for Developers           # "nhac_coc:1234,xac_nhan_booking:2345" – mẫu ZNS đã duyệt             # MST pháp nhân – điền trong .env / Render env


settings = Settings()
# Render/Heroku cấp DATABASE_URL dạng postgres:// – SQLAlchemy cần postgresql+psycopg2://
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
