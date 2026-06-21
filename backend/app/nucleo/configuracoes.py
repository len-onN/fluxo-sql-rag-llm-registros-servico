from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracoes(BaseSettings):
    nome_aplicacao: str = "Registro Inteligente de Servicos"
    banco_sqlite: str = "dados/registros.db"
    diretorio_chroma: str = "dados/chroma"
    provedor_chat: str = "lm_studio"
    provedor_embeddings: str = "lm_studio"
    lm_studio_base_url: str = "http://localhost:1234/v1"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    modelo_chat: str | None = None
    modelo_embedding: str = "text-embedding-nomic-embed-text-v1.5"
    limite_contexto: int = 3
    limiar_distancia_contexto: float | None = None
    limiar_pontuacao_contexto: float | None = None
    orcamento_contexto_caracteres: int | None = None
    max_tokens_resposta: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
