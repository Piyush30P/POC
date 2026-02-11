from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Source DB (read-only)
    source_db_host: str = "localhost"
    source_db_port: int = 5432
    source_db_name: str = "clearsight"
    source_db_schema: str = "public"
    source_db_user: str = "readonly_user"
    source_db_password: SecretStr = SecretStr("changeme")

    # Reporting DB (read-write)
    reporting_db_host: str = "localhost"
    reporting_db_port: int = 5432
    reporting_db_name: str = "clearsight"
    reporting_db_schema: str = "rpt"
    reporting_db_user: str = "reporting_user"
    reporting_db_password: SecretStr = SecretStr("changeme")

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: SecretStr = SecretStr("dev-api-key-change-in-production")
    api_workers: int = 4
    api_log_level: str = "info"

    # ETL
    etl_batch_size: int = 5000
    etl_schedule_minutes: int = 15
    etl_log_level: str = "info"

    # Seed
    seed_profile: str = "standard"
    seed_random_seed: int = 42

    @property
    def source_db_url(self) -> str:
        pwd = self.source_db_password.get_secret_value()
        return (
            f"postgresql://{self.source_db_user}:{pwd}"
            f"@{self.source_db_host}:{self.source_db_port}"
            f"/{self.source_db_name}"
        )

    @property
    def source_db_url_sync(self) -> str:
        pwd = self.source_db_password.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.source_db_user}:{pwd}"
            f"@{self.source_db_host}:{self.source_db_port}"
            f"/{self.source_db_name}"
        )

    @property
    def reporting_db_url_async(self) -> str:
        pwd = self.reporting_db_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.reporting_db_user}:{pwd}"
            f"@{self.reporting_db_host}:{self.reporting_db_port}"
            f"/{self.reporting_db_name}"
        )

    @property
    def reporting_db_url_sync(self) -> str:
        pwd = self.reporting_db_password.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.reporting_db_user}:{pwd}"
            f"@{self.reporting_db_host}:{self.reporting_db_port}"
            f"/{self.reporting_db_name}"
        )


settings = Settings()
