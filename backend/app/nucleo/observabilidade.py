import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class MetadadosConsultaRAG:
    provedor_chat: str = "desconhecido"
    provedor_embeddings: str = "desconhecido"
    modelo_chat: str | None = None
    modelo_embedding: str = "desconhecido"

    def como_dict(self) -> dict[str, object]:
        return {
            "provedor_chat": self.provedor_chat,
            "provedor_embeddings": self.provedor_embeddings,
            "modelo_chat": self.modelo_chat,
            "modelo_embedding": self.modelo_embedding,
        }


@dataclass(frozen=True, slots=True)
class MetricaEtapa:
    nome: str
    duracao_ms: float

    def como_dict(self) -> dict[str, object]:
        return {"nome": self.nome, "duracao_ms": self.duracao_ms}


@dataclass(frozen=True, slots=True)
class ResumoConsultaRAG:
    id_execucao: str
    sucesso: bool
    duracao_ms: float
    etapas: tuple[MetricaEtapa, ...]
    metadados: MetadadosConsultaRAG
    total_contextos_recuperados: int = 0
    total_contextos_usados: int = 0
    caracteres_contexto: int = 0
    modelo_chat_resposta: str | None = None
    modelo_embedding_resposta: str | None = None
    erro_tipo: str | None = None

    def como_dict(self) -> dict[str, object]:
        dados = {
            "evento": "consulta_rag",
            "caso_de_uso": "consultar_registros",
            "id_execucao": self.id_execucao,
            "sucesso": self.sucesso,
            "duracao_ms": self.duracao_ms,
            "etapas": [etapa.como_dict() for etapa in self.etapas],
            "total_contextos_recuperados": self.total_contextos_recuperados,
            "total_contextos_usados": self.total_contextos_usados,
            "caracteres_contexto": self.caracteres_contexto,
            **self.metadados.como_dict(),
        }
        if self.modelo_chat_resposta:
            dados["modelo_chat_resposta"] = self.modelo_chat_resposta
        if self.modelo_embedding_resposta:
            dados["modelo_embedding_resposta"] = self.modelo_embedding_resposta
        if self.erro_tipo:
            dados["erro_tipo"] = self.erro_tipo
        return dados


class ExecucaoConsultaRAG:
    def __init__(self, metadados: MetadadosConsultaRAG) -> None:
        self.id_execucao = str(uuid4())
        self._inicio = perf_counter()
        self._metadados = metadados
        self._etapas: list[MetricaEtapa] = []

    @contextmanager
    def medir(self, nome: str):
        inicio = perf_counter()
        try:
            yield
        finally:
            self._etapas.append(MetricaEtapa(nome=nome, duracao_ms=_milissegundos_desde(inicio)))

    def resumo_sucesso(
        self,
        *,
        total_contextos_recuperados: int,
        total_contextos_usados: int,
        caracteres_contexto: int,
        modelo_chat_resposta: str | None = None,
        modelo_embedding_resposta: str | None = None,
    ) -> ResumoConsultaRAG:
        return ResumoConsultaRAG(
            id_execucao=self.id_execucao,
            sucesso=True,
            duracao_ms=_milissegundos_desde(self._inicio),
            etapas=tuple(self._etapas),
            metadados=self._metadados,
            total_contextos_recuperados=total_contextos_recuperados,
            total_contextos_usados=total_contextos_usados,
            caracteres_contexto=caracteres_contexto,
            modelo_chat_resposta=modelo_chat_resposta,
            modelo_embedding_resposta=modelo_embedding_resposta,
        )

    def resumo_falha(self, erro: Exception) -> ResumoConsultaRAG:
        return ResumoConsultaRAG(
            id_execucao=self.id_execucao,
            sucesso=False,
            duracao_ms=_milissegundos_desde(self._inicio),
            etapas=tuple(self._etapas),
            metadados=self._metadados,
            erro_tipo=type(erro).__name__,
        )


class ObservadorConsultaRAG:
    def __init__(self, logger: logging.Logger | None = None, guardar_resumos: bool = False) -> None:
        self._logger = logger or logging.getLogger("app.observabilidade.rag")
        self._guardar_resumos = guardar_resumos
        self.resumos_emitidos: list[ResumoConsultaRAG] = []

    def iniciar(self, metadados: MetadadosConsultaRAG | None = None) -> ExecucaoConsultaRAG:
        return ExecucaoConsultaRAG(metadados or MetadadosConsultaRAG())

    def emitir(self, resumo: ResumoConsultaRAG) -> None:
        if self._guardar_resumos:
            self.resumos_emitidos.append(resumo)
        self._logger.info(json.dumps(resumo.como_dict(), ensure_ascii=True, sort_keys=True))


def _milissegundos_desde(inicio: float) -> float:
    return round((perf_counter() - inicio) * 1000, 3)
