from dataclasses import replace
from typing import Iterable

from app.dominio.objetos_valor import ContextoRAG, ContextosSelecionadosRAG


class PoliticaContextoRAG:
    def __init__(
        self,
        top_k_padrao: int = 5,
        distancia_maxima: float | None = None,
        pontuacao_minima: float | None = None,
        orcamento_caracteres: int | None = None,
    ) -> None:
        self._top_k_padrao = _exigir_inteiro_positivo(top_k_padrao, "top_k_padrao")
        self._distancia_maxima = distancia_maxima
        self._pontuacao_minima = pontuacao_minima
        self._orcamento_caracteres = (
            _exigir_inteiro_positivo(orcamento_caracteres, "orcamento_caracteres")
            if orcamento_caracteres is not None
            else None
        )

    def limite_busca(self, limite_solicitado: int | None = None) -> int:
        if limite_solicitado is None:
            return self._top_k_padrao
        return _exigir_inteiro_positivo(limite_solicitado, "limite_solicitado")

    def selecionar(
        self,
        contextos: Iterable[ContextoRAG],
        limite_solicitado: int | None = None,
    ) -> ContextosSelecionadosRAG:
        limite = self.limite_busca(limite_solicitado)
        filtrados: list[ContextoRAG] = []

        for contexto in contextos:
            if not contexto.documento.strip():
                continue
            if not self._passa_limiar_distancia(contexto):
                continue
            if not self._passa_limiar_pontuacao(contexto):
                continue
            filtrados.append(contexto)
            if len(filtrados) >= limite:
                break

        return ContextosSelecionadosRAG(self._aplicar_orcamento(filtrados))

    def _passa_limiar_distancia(self, contexto: ContextoRAG) -> bool:
        if self._distancia_maxima is None or contexto.distancia is None:
            return True
        return contexto.distancia <= self._distancia_maxima

    def _passa_limiar_pontuacao(self, contexto: ContextoRAG) -> bool:
        if self._pontuacao_minima is None or contexto.pontuacao is None:
            return True
        return contexto.pontuacao >= self._pontuacao_minima

    def _aplicar_orcamento(self, contextos: list[ContextoRAG]) -> tuple[ContextoRAG, ...]:
        if self._orcamento_caracteres is None:
            return tuple(contextos)

        restantes = self._orcamento_caracteres
        selecionados: list[ContextoRAG] = []

        for contexto in contextos:
            separador = len("\n\n---\n\n") if selecionados else 0
            disponivel = restantes - separador
            if disponivel <= 0:
                break

            documento = contexto.documento.strip()
            if len(documento) <= disponivel:
                selecionados.append(replace(contexto, documento=documento))
                restantes -= separador + len(documento)
                continue

            documento_cortado = documento[:disponivel].rstrip()
            if documento_cortado:
                selecionados.append(replace(contexto, documento=documento_cortado))
            break

        return tuple(selecionados)


def _exigir_inteiro_positivo(valor: int, nome: str) -> int:
    if valor < 1:
        raise ValueError(f"{nome} deve ser maior que zero.")
    return valor
