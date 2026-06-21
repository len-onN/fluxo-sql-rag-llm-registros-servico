from typing import Protocol

from app.dominio.objetos_valor import EstadoModelosChat


class SeletorModelo(Protocol):
    def selecionar_modelo_chat(self, modelo_id: str) -> EstadoModelosChat:
        ...
