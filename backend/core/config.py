from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: SecretStr
    fmp_api_key: SecretStr
    alpha_vantage_api_key: SecretStr
    fred_api_key: SecretStr
    coingecko_api_key: SecretStr = SecretStr("")
    obsidian_vault_path: Path
    daily_budget_alarm_usd: float = 5.0


settings = Settings()
