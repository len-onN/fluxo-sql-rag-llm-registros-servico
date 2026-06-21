from typing import Iterable


class MontadorPromptRAG:
    def __init__(
        self,
        separador_contextos: str = "\n\n---\n\n",
        contexto_vazio: str = "Nenhum contexto encontrado.",
    ) -> None:
        self._separador_contextos = separador_contextos
        self._contexto_vazio = contexto_vazio

    def montar_contexto(self, contextos: Iterable[str]) -> str:
        partes = [contexto.strip() for contexto in contextos if contexto.strip()]
        return self._separador_contextos.join(partes) or self._contexto_vazio

    def montar_prompt_usuario(self, pergunta: str, contextos: Iterable[str]) -> str:
        contexto = self.montar_contexto(contextos)
        return f"Contexto:\n{contexto}\n\nPergunta:\n{pergunta}"
