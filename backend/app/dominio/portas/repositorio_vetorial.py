from typing import Protocol

from app.dominio.entidades import RegistroServico
from app.dominio.objetos_valor import ContextoRAG, RespostaEmbedding


class RepositorioVetorial(Protocol):
    def indexar(self, registro: RegistroServico, embedding: RespostaEmbedding) -> None:
        ...

    def buscar_similares(self, embedding: RespostaEmbedding, limite: int) -> list[ContextoRAG]:
        ...
