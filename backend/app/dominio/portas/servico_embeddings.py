from typing import Protocol


class ServicoEmbeddings(Protocol):
    def gerar_embedding(self, texto: str) -> list[float]:
        ...
