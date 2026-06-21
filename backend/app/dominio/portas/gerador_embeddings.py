from typing import Protocol

from app.dominio.objetos_valor import RespostaEmbedding, SolicitacaoEmbedding


class GeradorEmbeddings(Protocol):
    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        ...
