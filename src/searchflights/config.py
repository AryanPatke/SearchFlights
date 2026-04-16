"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from functools import cached_property

from pydantic_settings import BaseSettings

_DEFAULT_DESTS = "BKK,CMB,KUL,SIN,DXB,HKT,SGN,GOI,DEL,CCU,DOH,IST,CDG,LHR,FRA,NRT"


class Settings(BaseSettings):
    model_config = {"env_prefix": "SF_", "env_file": ".env", "extra": "ignore"}

    default_destinations_csv: str = _DEFAULT_DESTS

    min_delay: float = 2.0
    max_delay: float = 5.0

    gl: str = "IN"
    hl: str = "en"

    proxy_url: str | None = None
    headless: bool = True

    date_step_days: int = 7

    @cached_property
    def default_destinations(self) -> list[str]:
        return [s.strip() for s in self.default_destinations_csv.split(",") if s.strip()]


settings = Settings()
