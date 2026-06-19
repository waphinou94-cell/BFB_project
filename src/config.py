from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider sélectionné : "vertexai" | "openai"
    llm_provider: str = "vertexai"
    embedding_provider: str = "vertexai"

    # Modèles
    llm_model: str = "gemini-3.1-flash-lite"
    embedding_model: str = "text-multilingual-embedding-002"

    # Vertex AI
    vertex_project: str = ""
    vertex_location: str = "global"

    # OpenAI (endpoint compatible OpenAI, utilisé si provider=openai)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""

    # Base de données
    database_url: str = "postgresql+psycopg://bforbank:bforbank@localhost:5432/bforbank"

    # Langfuse (optionnel — désactivé si public_key est vide)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


settings = Settings()
