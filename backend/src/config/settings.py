"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "jobnorm"
    app_title: str = "jobnorm · 招聘岗位采集与薪资口径归一工坊"
    version: str = "1.0.0"

    # MySQL
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "jobnorm"
    db_user: str = "jobnorm"
    db_password: str = "jobnorm_pw_2026"

    # 安全
    jwt_secret: str = "jobnorm-jwt-secret-2026-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 720

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    seed_demo: bool = True
    rate_limit_per_minute: int = 900
    default_rule_version: str = "v1"
    title_dict_version: str = "title-dict-v2"
    # 薪资合理区间（元/月）
    salary_floor: int = 3000
    salary_ceiling: int = 300000
    # 单位折算常数
    work_days_per_month: int = 22
    work_hours_per_day: int = 8

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
