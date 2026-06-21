import re
from typing import Any

from app.dominio.objetos_valor import RespostaLLM, SolicitacaoLLM
from app.nucleo.erros import ModeloNaoEncontrado, RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteOpenAICompativel


INSTRUCOES_RESPOSTA = (
    "Voce responde apenas com base no contexto fornecido. "
    "Quando nao houver informacao suficiente, diga isso claramente. "
    "Responda exclusivamente em portugues do Brasil. "
    "Nao traduza nomes de campos para ingles. "
    "Use os termos exatamente como aparecem no contexto quando citar funcionario, cliente, status ou problema. "
    "Entregue a resposta final sem raciocinio interno. "
    "Comece a resposta final com 'Resposta:' e depois escreva a resposta em linguagem natural."
)


class GeradorRespostaOpenAICompativel:
    def __init__(
        self,
        cliente: ClienteOpenAICompativel,
        modelo_chat: str | None,
        max_tokens_resposta: int,
        parser_resposta: "ParserRespostaOpenAICompativel | None" = None,
    ) -> None:
        self._cliente = cliente
        self._modelo_chat = _normalizar_modelo(modelo_chat)
        self._max_tokens_resposta = max_tokens_resposta
        self._parser_resposta = parser_resposta or ParserRespostaOpenAICompativel()

    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        contextos = list(solicitacao.contextos)
        contexto = "\n\n---\n\n".join(contextos) or "Nenhum contexto encontrado."
        prompt_usuario = solicitacao.prompt_usuario or f"Contexto:\n{contexto}\n\nPergunta:\n{solicitacao.pergunta}"
        modelo_chat = _normalizar_modelo(solicitacao.modelo) or self._resolver_modelo_chat()
        temperatura = solicitacao.temperatura if solicitacao.temperatura is not None else 0.1
        max_tokens = solicitacao.max_tokens if solicitacao.max_tokens is not None else self._max_tokens_resposta

        dados = self._cliente.postar_json(
            "/chat/completions",
            json={
                "model": modelo_chat,
                "messages": [
                    {"role": "system", "content": INSTRUCOES_RESPOSTA},
                    {"role": "user", "content": prompt_usuario},
                ],
                "temperature": temperatura,
                "max_tokens": max_tokens,
            },
            timeout=300,
            modelo=modelo_chat,
        )
        texto_final = self._parser_resposta.extrair_texto_final(dados, modelo_chat)
        return RespostaLLM(texto=texto_final, modelo=modelo_chat)

    def _resolver_modelo_chat(self) -> str:
        if self._modelo_chat:
            return self._modelo_chat
        raise ModeloNaoEncontrado(
            "Configure MODELO_CHAT para usar o provedor OpenAI-compatible.",
            provedor=PROVEDOR,
        )


class ParserRespostaOpenAICompativel:
    def extrair_texto_final(self, dados: dict[str, Any], modelo: str | None = None) -> str:
        try:
            escolha = dados["choices"][0]
            mensagem = escolha["message"]
            conteudo = mensagem["content"]
        except (KeyError, IndexError, TypeError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de chat OpenAI-compatible nao possui mensagem esperada.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

        texto = self._extrair_texto(conteudo)
        if not texto:
            raise RespostaInvalidaProvedor(
                "Resposta de chat OpenAI-compatible nao possui texto final.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        return self._normalizar_resposta_final(texto)

    def _extrair_texto(self, conteudo: object) -> str:
        if isinstance(conteudo, str):
            return conteudo.strip()

        if isinstance(conteudo, list):
            partes: list[str] = []
            for parte in conteudo:
                if isinstance(parte, dict) and isinstance(parte.get("text"), str):
                    partes.append(parte["text"])
            return "\n".join(parte.strip() for parte in partes if parte.strip())

        return ""

    def _normalizar_resposta_final(self, texto: str) -> str:
        return re.sub(r"^\s*resposta\s*:\s*", "", texto.strip(), flags=re.IGNORECASE)


def _normalizar_modelo(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None
