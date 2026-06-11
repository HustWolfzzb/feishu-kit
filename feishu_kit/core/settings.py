"""Configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Feishu API credentials and deployment settings.

    All fields can be set via environment variables or a .env file.
    Fields with defaults are optional — the library works without them.
    """

    # -- Feishu credentials --
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_bot2_app_id: str = ""
    feishu_bot2_app_secret: str = ""
    log_level: str = "INFO"

    # -- Server --
    host: str = "0.0.0.0"
    port: int = 8000
    enabled_modules: list[str] = []
    modules_dir: str = "server/routers"

    # -- LLM --
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.7
    llm_timeout: float = 30.0

    # -- Chat behavior --
    chat_history_max_turns: int = 10
    chat_system_prompt: str = "你是一个飞书智能助手，帮助用户完成各种任务。"
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""

    # -- RAG --
    rag_wiki_space_id: str = ""
    rag_max_context_length: int = 3000

    # -- Butler --
    butler_db_path: str = "data/butler.db"
    butler_default_space_id: str = ""
    butler_timezone: str = "Asia/Shanghai"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
