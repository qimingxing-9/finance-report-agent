from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 大模型
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # 向量库
    milvus_uri: str = "http://localhost:19530"
    embedding_model: str = "BAAI/bge-m3"

    # 数据库
    mysql_url: str = "mysql+aiomysql://root:123456@localhost:3306/finance"
    redis_url: str = "redis://localhost:6379/0"

    # 会话
    session_ttl_days: int = 7
    off_peak_window: str = "00:30-08:30"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
