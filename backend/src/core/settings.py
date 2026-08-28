from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool

    DATABASE_URL: str

    OPENAI_API_KEY: str = ""

    # --- LLM provider ---
    # "groq"   -> fast, free-tier cloud inference of open-weight models
    #             (Llama 3.3, etc). Get a free key at console.groq.com.
    #             Document text and questions leave your server for this.
    # "ollama" -> fully local, private, but needs real CPU/RAM/GPU and is
    #             much slower without one. See README for the tradeoffs.
    LLM_PROVIDER: str = "groq"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_VISION_MODEL: str = "llama-3.2-90b-vision-preview"

    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_VISION_MODEL: str = "llama3.2-vision"

    SECRET_KEY: str
    REFRESH_SECRET_KEY: str = "change-me"
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Comma-separated list of allowed browser origins for CORS.
    CORS_ORIGINS: str = "http://localhost:5173"

    MAX_UPLOAD_MB: int = 25
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- Account lockout ---
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # --- Google Sign-In ---
    # Get a free OAuth Client ID at https://console.cloud.google.com/apis/credentials
    # (Web application type). Empty = Google Sign-In button is disabled.
    GOOGLE_CLIENT_ID: str = ""

    # --- Password reset ---
    # Without SMTP configured, reset links are logged to the server console
    # instead of emailed (fine for local/dev use, not for a real launch).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    FRONTEND_URL: str = "http://localhost:5173"

    # Optional: if set, and no admin user exists yet, one is created at
    # startup with these credentials. Leave unset in normal operation.
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
