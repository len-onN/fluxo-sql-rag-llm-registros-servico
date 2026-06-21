from typing import Protocol

from app.dominio.entidades import RegistroServico
from app.dominio.objetos_valor import ContextoRAG


class RepositorioVetorial(Protocol):
    def indexar(self, registro: RegistroServico, embedding: list[float]) -> None:
        ...

    def buscar_similares(self, embedding: list[float], limite: int) -> list[ContextoRAG]:
        ...
