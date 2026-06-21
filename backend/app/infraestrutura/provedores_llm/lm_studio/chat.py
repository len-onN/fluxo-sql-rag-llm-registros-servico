from app.dominio.objetos_valor import RespostaLLM, SolicitacaoLLM
from app.dominio.portas import CatalogoModelos
from app.nucleo.erros import ModeloNaoEncontrado

from .cliente import PROVEDOR, ClienteLMStudio
from .parser_resposta import ParserRespostaLMStudio
from .politica_fallback import PoliticaFallbackRespostaLMStudio
from .selecao import ResolvedorModeloChatLMStudio


INSTRUCOES_RESPOSTA = (
    "Voce responde apenas com base no contexto fornecido. "
    "Quando nao houver informacao suficiente, diga isso claramente. "
    "Responda exclusivamente em portugues do Brasil. "
    "Nao traduza nomes de campos para ingles. "
    "Use os termos exatamente como aparecem no contexto quando citar funcionario, cliente, status ou problema. "
    "Entregue a resposta final sem raciocinio interno. "
    "Comece a resposta final com 'Resposta:' e depois escreva a resposta em linguagem natural."
)


class GeradorRespostaLMStudio:
    def __init__(
        self,
        cliente: ClienteLMStudio,
        catalogo_modelos: CatalogoModelos,
        resolvedor_modelo: ResolvedorModeloChatLMStudio,
        parser_resposta: ParserRespostaLMStudio,
        politica_fallback: PoliticaFallbackRespostaLMStudio,
        max_tokens_resposta: int,
    ) -> None:
        self._cliente = cliente
        self._catalogo_modelos = catalogo_modelos
        self._resolvedor_modelo = resolvedor_modelo
        self._parser_resposta = parser_resposta
        self._politica_fallback = politica_fallback
        self._max_tokens_resposta = max_tokens_resposta

    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        contextos = list(solicitacao.contextos)
        contexto = "\n\n---\n\n".join(contextos) or "Nenhum contexto encontrado."
        modelo_chat = solicitacao.modelo or self._resolver_modelo_chat()
        temperatura = solicitacao.temperatura if solicitacao.temperatura is not None else 0.1
        max_tokens = solicitacao.max_tokens if solicitacao.max_tokens is not None else self._max_tokens_resposta

        dados = self._cliente.postar_json(
            self._cliente.url_api("/responses"),
            json={
                "model": modelo_chat,
                "instructions": INSTRUCOES_RESPOSTA,
                "input": f"Contexto:\n{contexto}\n\nPergunta:\n{solicitacao.pergunta}",
                "temperature": temperatura,
                "max_output_tokens": max_tokens,
                "reasoning": {"effort": "minimal"},
            },
            timeout=300,
            modelo=modelo_chat,
        )
        texto_final = self._parser_resposta.extrair_texto_final(dados)
        if self._politica_fallback.deve_aplicar(texto_final):
            texto_final = self._politica_fallback.montar_resposta(contextos)

        return RespostaLLM(texto=texto_final, modelo=modelo_chat)

    def _resolver_modelo_chat(self) -> str:
        modelos = self._catalogo_modelos.listar_modelos_chat()
        modelo_resolvido = self._resolvedor_modelo.resolver(modelos, exigir_resolucao=True)
        if modelo_resolvido is None:
            raise ModeloNaoEncontrado("Nenhum modelo LLM carregado no LM Studio.", provedor=PROVEDOR)
        return modelo_resolvido
