from collections.abc import Callable
from dataclasses import dataclass

from app.dominio.portas import CatalogoModelos, GeradorEmbeddings, GeradorResposta, SeletorModelo
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
from app.infraestrutura.provedores_llm.lm_studio.cliente import PROVEDOR as PROVEDOR_LM_STUDIO
from app.nucleo.configuracoes import Configuracoes
from app.nucleo.erros import ProvedorNaoSuportado


@dataclass(frozen=True, slots=True)
class EstadoProvedoresAtivos:
    provedor_chat: str
    provedor_embeddings: str
    modelo_chat: str | None
    modelo_embedding: str

    def como_dict(self) -> dict[str, object]:
        return {
            "provedor_chat": self.provedor_chat,
            "provedor_embeddings": self.provedor_embeddings,
            "modelo_chat": self.modelo_chat,
            "modelo_embedding": self.modelo_embedding,
        }


@dataclass(slots=True)
class ComponentesChat:
    gerador_resposta: GeradorResposta
    catalogo_modelos: CatalogoModelos
    seletor_modelo: SeletorModelo


@dataclass(slots=True)
class ComponentesEmbeddings:
    gerador_embeddings: GeradorEmbeddings


@dataclass(slots=True)
class ComponentesProvedores:
    gerador_embeddings: GeradorEmbeddings
    gerador_resposta: GeradorResposta
    catalogo_modelos: CatalogoModelos
    seletor_modelo: SeletorModelo
    estado: EstadoProvedoresAtivos


@dataclass(slots=True)
class _ComponentesLMStudio:
    cliente: ClienteLMStudio
    resolvedor_modelo_chat: ResolvedorModeloChatLMStudio
    catalogo_modelos: CatalogoModelosLMStudio


ConstrutorChat = Callable[[], ComponentesChat]
ConstrutorEmbeddings = Callable[[], ComponentesEmbeddings]


class RegistroProvedores:
    def __init__(self, configuracoes: Configuracoes) -> None:
        self._configuracoes = configuracoes
        self._lm_studio: _ComponentesLMStudio | None = None
        self._provedores_chat: dict[str, ConstrutorChat] = {
            PROVEDOR_LM_STUDIO: self._criar_chat_lm_studio,
        }
        self._provedores_embeddings: dict[str, ConstrutorEmbeddings] = {
            PROVEDOR_LM_STUDIO: self._criar_embeddings_lm_studio,
        }

    def criar(self) -> ComponentesProvedores:
        provedor_chat = _normalizar_identificador(self._configuracoes.provedor_chat)
        provedor_embeddings = _normalizar_identificador(self._configuracoes.provedor_embeddings)
        construtor_chat = self._obter_construtor("chat", provedor_chat, self._provedores_chat)
        construtor_embeddings = self._obter_construtor(
            "embeddings",
            provedor_embeddings,
            self._provedores_embeddings,
        )

        componentes_chat = construtor_chat()
        componentes_embeddings = construtor_embeddings()

        return ComponentesProvedores(
            gerador_embeddings=componentes_embeddings.gerador_embeddings,
            gerador_resposta=componentes_chat.gerador_resposta,
            catalogo_modelos=componentes_chat.catalogo_modelos,
            seletor_modelo=componentes_chat.seletor_modelo,
            estado=EstadoProvedoresAtivos(
                provedor_chat=provedor_chat,
                provedor_embeddings=provedor_embeddings,
                modelo_chat=_normalizar_modelo(self._configuracoes.modelo_chat),
                modelo_embedding=self._configuracoes.modelo_embedding,
            ),
        )

    def _obter_construtor(
        self,
        capacidade: str,
        provedor: str,
        registro: dict[str, Callable],
    ) -> Callable:
        if provedor not in registro:
            raise ProvedorNaoSuportado(capacidade, provedor, tuple(registro))
        return registro[provedor]

    def _criar_chat_lm_studio(self) -> ComponentesChat:
        componentes = self._obter_lm_studio()
        gerador_resposta = GeradorRespostaLMStudio(
            cliente=componentes.cliente,
            catalogo_modelos=componentes.catalogo_modelos,
            resolvedor_modelo=componentes.resolvedor_modelo_chat,
            parser_resposta=ParserRespostaLMStudio(),
            politica_fallback=PoliticaFallbackRespostaLMStudio(),
            max_tokens_resposta=self._configuracoes.max_tokens_resposta,
        )
        return ComponentesChat(
            gerador_resposta=gerador_resposta,
            catalogo_modelos=componentes.catalogo_modelos,
            seletor_modelo=SeletorModeloLMStudio(
                componentes.catalogo_modelos,
                componentes.resolvedor_modelo_chat,
            ),
        )

    def _criar_embeddings_lm_studio(self) -> ComponentesEmbeddings:
        componentes = self._obter_lm_studio()
        return ComponentesEmbeddings(
            gerador_embeddings=GeradorEmbeddingsLMStudio(
                componentes.cliente,
                self._configuracoes.modelo_embedding,
            ),
        )

    def _obter_lm_studio(self) -> _ComponentesLMStudio:
        if self._lm_studio is None:
            cliente = ClienteLMStudio(self._configuracoes.lm_studio_base_url)
            resolvedor = ResolvedorModeloChatLMStudio(_normalizar_modelo(self._configuracoes.modelo_chat))
            self._lm_studio = _ComponentesLMStudio(
                cliente=cliente,
                resolvedor_modelo_chat=resolvedor,
                catalogo_modelos=CatalogoModelosLMStudio(cliente, resolvedor),
            )
        return self._lm_studio


def criar_componentes_provedores(configuracoes: Configuracoes) -> ComponentesProvedores:
    return RegistroProvedores(configuracoes).criar()


def _normalizar_identificador(valor: str) -> str:
    return valor.strip().lower().replace("-", "_")


def _normalizar_modelo(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor_normalizado = valor.strip()
    return valor_normalizado or None
