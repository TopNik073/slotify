from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from src.core.models import GoogleCredentialsModel


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore',
    )

    SENSITIVE_DATA: list[str] = [
        'password',
        'code',
    ]

    APP_NAME: str = 'Slotify'
    APP_VERSION: str = '0.1.0'
    APP_HOST: str = '0.0.0.0'
    APP_PORT: int = 8000
    DEBUG: bool = False

    SECURE: bool = False

    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    SQLALCHEMY_ECHO: bool = False

    @property
    def POSTGRES_URL(self) -> str:
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    DEFAULT_CACHE_TTL: int | None = 30
    AUTH_CACHE_TTL: int | None = 600

    @property
    def REDIS_URL(self) -> str:
        auth = f':{self.REDIS_PASSWORD}@' if self.REDIS_PASSWORD else ''
        return f'redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'

    YC_POSTBOX_ACCESS_KEY: str
    YC_POSTBOX_SECRET_KEY: SecretStr
    YC_POSTBOX_REGION: str = 'ru-central1'
    YC_POSTBOX_ENDPOINT: str = 'https://postbox.cloud.yandex.net'

    MAIL_FROM: str

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    LOG_TO_FILE: bool = False
    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '%(asctime)s | %(levelname)-8s | %(name)s | [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s'
    LOG_DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S.%f'

    _LOGS_DIR: Path = BASE_DIR / 'logs'

    @property
    def LOGS_DIR(self) -> Path:
        Path.mkdir(self._LOGS_DIR, parents=True, exist_ok=True)
        return self._LOGS_DIR

    JWT_SECRET: SecretStr
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXP: int = 60 * 30
    REFRESH_TOKEN_EXP: int = 60 * 30 * 24 * 60

    # Fernet key used to encrypt third-party OAuth tokens at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    TOKEN_ENCRYPTION_KEY: SecretStr

    google_credentials: GoogleCredentialsModel

    FRONTEND_DIR: Path = BASE_DIR / 'frontend'
    SERVE_FRONTEND: bool = True

    # Used to build links sent by email; must match how users actually reach the app.
    PUBLIC_BASE_URL: str = 'http://localhost:8000'

    # Defaults applied to a newly created office; each office can override them.
    DEFAULT_SLOT_MINUTES: int = 30
    DEFAULT_MIN_BOOKING_MINUTES: int = 30
    DEFAULT_MAX_BOOKING_MINUTES: int = 60 * 8
    DEFAULT_BOOKING_HORIZON_DAYS: int = 90
    MAX_SERIES_OCCURRENCES: int = 52


config = Config()
