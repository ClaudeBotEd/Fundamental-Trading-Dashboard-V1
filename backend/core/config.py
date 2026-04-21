from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str
    fmp_api_key: str
    alpha_vantage_api_key: str
    fred_api_key: str
    obsidian_vault_path: Path
    coingecko_api_key: str = ""
    daily_budget_alarm_usd: float = 5.0


settings = Settings()
