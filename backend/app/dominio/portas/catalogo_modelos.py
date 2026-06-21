from typing import Protocol

from app.dominio.objetos_valor import EstadoModelosChat, ModeloChat


class CatalogoModelos(Protocol):
    def listar_modelos_chat(self) -> list[ModeloChat]:
        ...

    def obter_estado_modelos_chat(self) -> EstadoModelosChat:
        ...
