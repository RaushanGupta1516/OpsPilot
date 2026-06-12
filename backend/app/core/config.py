from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OpsPilot"
    app_env: str = "development"

    database_url: str
    redis_url: str = ""

    gemini_api_key: str = ""
    groq_api_key: str = ""
    langsmith_api_key: str = ""
    langsmith_project: str = "opspilot"
    langchain_tracing_v2: str = "false"

    monitor_interval_secs: int = 30
    baseline_observation_hours: int = 48
    dedup_window_mins: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()