from typing import Protocol

from app.dominio.objetos_valor import RespostaLLM, SolicitacaoLLM


class GeradorResposta(Protocol):
    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        ...
