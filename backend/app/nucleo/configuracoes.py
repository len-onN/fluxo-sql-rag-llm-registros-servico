from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    nome_aplicacao: str = "Registro Inteligente de Servicos"
    banco_sqlite: str = "dados/registros.db"
    diretorio_chroma: str = "dados/chroma"
    lm_studio_base_url: str = "http://localhost:1234/v1"
    modelo_embedding: str = "text-embedding-nomic-embed-text-v1.5"
    limite_contexto: int = 3
    max_tokens_resposta: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
