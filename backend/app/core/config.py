from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "OUTZAAR"
    APP_ENV: str = "development"

    DATABASE_URL: str = "sqlite:///./data/outzaar.db"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:4b"

    # WhatsApp Cloud API (Meta)
    WHATSAPP_VERIFY_TOKEN: str = ""      # any secret string you also paste into Meta's webhook config
    WHATSAPP_APP_SECRET: str = ""        # Meta App > Settings > Basic > App Secret (signs webhooks)
    WHATSAPP_ACCESS_TOKEN: str = ""      # System User permanent token
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_API_VERSION: str = "v23.0"  # set to the Graph API version shown in your Meta app

    # Email (inbound webhook + outbound SMTP)
    EMAIL_WEBHOOK_SECRET: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()