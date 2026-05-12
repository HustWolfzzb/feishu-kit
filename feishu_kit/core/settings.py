"""Configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Feishu API credentials and basic settings.

    All fields can be set via environment variables or a .env file.
    """

    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_bot2_app_id: str = ""
    feishu_bot2_app_secret: str = ""
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
