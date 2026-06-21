from app.dominio.objetos_valor import (
    EstadoModelosChat,
    ModeloChat,
    RespostaEmbedding,
    RespostaLLM,
    SolicitacaoEmbedding,
    SolicitacaoLLM,
)
from app.infraestrutura.provedores_llm.lm_studio import (
    CatalogoModelosLMStudio,
    ClienteLMStudio,
    GeradorEmbeddingsLMStudio,
    GeradorRespostaLMStudio,
    ParserRespostaLMStudio,
    PoliticaFallbackRespostaLMStudio,
    ResolvedorModeloChatLMStudio,
    SeletorModeloLMStudio,
)
from app.infraestrutura.provedores_llm.lm_studio.cliente import PROVEDOR


class ServicoLMStudio:
    def __init__(self, base_url: str, modelo_embedding: str, max_tokens_resposta: int) -> None:
        cliente = ClienteLMStudio(base_url)
        resolvedor = ResolvedorModeloChatLMStudio()
        catalogo = CatalogoModelosLMStudio(cliente, resolvedor)

        self._catalogo_modelos = catalogo
        self._seletor_modelo = SeletorModeloLMStudio(catalogo, resolvedor)
        self._gerador_embeddings = GeradorEmbeddingsLMStudio(cliente, modelo_embedding)
        self._gerador_resposta = GeradorRespostaLMStudio(
            cliente=cliente,
            catalogo_modelos=catalogo,
            resolvedor_modelo=resolvedor,
            parser_resposta=ParserRespostaLMStudio(),
            politica_fallback=PoliticaFallbackRespostaLMStudio(),
            max_tokens_resposta=max_tokens_resposta,
        )

    def listar_modelos_chat(self) -> list[ModeloChat]:
        return self._catalogo_modelos.listar_modelos_chat()

    def listar_modelos_chat_carregados(self) -> list[ModeloChat]:
        return self._catalogo_modelos.listar_modelos_chat_carregados()

    def obter_estado_modelos_chat(self) -> EstadoModelosChat:
        return self._catalogo_modelos.obter_estado_modelos_chat()

    def selecionar_modelo_chat(self, modelo_id: str) -> EstadoModelosChat:
        return self._seletor_modelo.selecionar_modelo_chat(modelo_id)

    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        return self._gerador_embeddings.gerar_embedding(solicitacao)

    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        return self._gerador_resposta.responder(solicitacao)
