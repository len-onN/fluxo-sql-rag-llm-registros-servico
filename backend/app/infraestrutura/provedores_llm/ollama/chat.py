import re
from typing import Any

from app.dominio.objetos_valor import RespostaLLM, SolicitacaoLLM
from app.nucleo.erros import ModeloNaoEncontrado, RespostaInvalidaProvedor

from .catalogo import CatalogoModelosOllama
from .cliente import PROVEDOR, ClienteOllama
from .selecao import ResolvedorModeloChatOllama


INSTRUCOES_RESPOSTA = (
    "Voce responde apenas com base no contexto fornecido. "
    "Quando nao houver informacao suficiente, diga isso claramente. "
    "Responda exclusivamente em portugues do Brasil. "
    "Nao traduza nomes de campos para ingles. "
    "Use os termos exatamente como aparecem no contexto quando citar funcionario, cliente, status ou problema. "
    "Entregue a resposta final sem raciocinio interno. "
    "Comece a resposta final com 'Resposta:' e depois escreva a resposta em linguagem natural."
)


class GeradorRespostaOllama:
    def __init__(
        self,
        cliente: ClienteOllama,
        catalogo_modelos: CatalogoModelosOllama,
        resolvedor_modelo: ResolvedorModeloChatOllama,
        max_tokens_resposta: int,
        parser_resposta: "ParserRespostaOllama | None" = None,
    ) -> None:
        self._cliente = cliente
        self._catalogo_modelos = catalogo_modelos
        self._resolvedor_modelo = resolvedor_modelo
        self._max_tokens_resposta = max_tokens_resposta
        self._parser_resposta = parser_resposta or ParserRespostaOllama()

    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        contextos = list(solicitacao.contextos)
        contexto = "\n\n---\n\n".join(contextos) or "Nenhum contexto encontrado."
        prompt_usuario = solicitacao.prompt_usuario or f"Contexto:\n{contexto}\n\nPergunta:\n{solicitacao.pergunta}"
        modelo_chat = _normalizar_modelo(solicitacao.modelo) or self._resolver_modelo_chat()
        temperatura = solicitacao.temperatura if solicitacao.temperatura is not None else 0.1
        max_tokens = solicitacao.max_tokens if solicitacao.max_tokens is not None else self._max_tokens_resposta

        dados = self._cliente.postar_json(
            "/api/chat",
            json={
                "model": modelo_chat,
                "messages": [
                    {"role": "system", "content": INSTRUCOES_RESPOSTA},
                    {"role": "user", "content": prompt_usuario},
                ],
                "stream": False,
                "options": {
                    "temperature": temperatura,
                    "num_predict": max_tokens,
                },
            },
            timeout=300,
            modelo=modelo_chat,
            capacidade="chat",
        )
        texto_final = self._parser_resposta.extrair_texto_final(dados, modelo_chat)
        modelo_resposta = _normalizar_modelo(dados.get("model")) or modelo_chat
        return RespostaLLM(texto=texto_final, modelo=modelo_resposta)

    def _resolver_modelo_chat(self) -> str:
        modelos = self._catalogo_modelos.listar_modelos_chat()
        modelo = self._resolvedor_modelo.resolver(modelos, exigir_resolucao=True)
        if modelo:
            return modelo
        raise ModeloNaoEncontrado(
            "Nenhum modelo local de chat encontrado no Ollama.",
            provedor=PROVEDOR,
        )


class ParserRespostaOllama:
    def extrair_texto_final(self, dados: dict[str, Any], modelo: str | None = None) -> str:
        try:
            conteudo = dados["message"]["content"]
        except (KeyError, TypeError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de chat Ollama nao possui mensagem esperada.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

        texto = conteudo.strip() if isinstance(conteudo, str) else ""
        if not texto:
            raise RespostaInvalidaProvedor(
                "Resposta de chat Ollama nao possui texto final.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        return self._normalizar_resposta_final(texto)

    def _normalizar_resposta_final(self, texto: str) -> str:
        return re.sub(r"^\s*resposta\s*:\s*", "", texto.strip(), flags=re.IGNORECASE)


def _normalizar_modelo(valor: object) -> str | None:
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None
