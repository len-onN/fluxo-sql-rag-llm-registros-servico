from typing import Protocol


class ServicoLLM(Protocol):
    def responder(self, pergunta: str, contextos: list[str]) -> str:
        ...
