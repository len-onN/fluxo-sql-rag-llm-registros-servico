from typing import Protocol

from app.dominio.entidades import RegistroServico


class RepositorioRegistros(Protocol):
    def salvar(self, registro: RegistroServico) -> RegistroServico:
        ...

    def listar(self) -> list[RegistroServico]:
        ...

    def buscar_por_id(self, id_registro: int) -> RegistroServico | None:
        ...

    def listar_pendentes_indexacao(self, modelo_embedding: str | None = None) -> list[RegistroServico]:
        ...

    def marcar_indexado(
        self,
        id_registro: int,
        modelo_embedding: str,
        hash_conteudo_rag: str,
    ) -> RegistroServico:
        ...

    def marcar_erro_indexacao(
        self,
        id_registro: int,
        erro: str,
        modelo_embedding: str,
        hash_conteudo_rag: str,
    ) -> RegistroServico:
        ...
