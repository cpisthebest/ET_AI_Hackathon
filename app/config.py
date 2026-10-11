from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://compliance:compliance_dev_password@localhost:5432/compliance"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 900
    chunk_overlap: int = 120
    top_k: int = 8
    hybrid_vector_weight: float = 0.65
    hybrid_text_weight: float = 0.35
    app_env: str = "development"
    log_level: str = "INFO"

settings = Settings()
