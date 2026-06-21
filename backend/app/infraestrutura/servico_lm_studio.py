import re
from typing import Any

import httpx

from app.dominio.objetos_valor import (
    EstadoModelosChat,
    ModeloChat,
    RespostaEmbedding,
    RespostaLLM,
    SolicitacaoEmbedding,
    SolicitacaoLLM,
)
from app.nucleo.erros import (
    AutenticacaoProvedor,
    LimiteTaxaProvedor,
    ModeloNaoEncontrado,
    ProvedorIndisponivel,
    RespostaInvalidaProvedor,
    TimeoutProvedor,
)


PROVEDOR = "lm_studio"


class ServicoLMStudio:
    def __init__(self, base_url: str, modelo_embedding: str, max_tokens_resposta: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._base_url_nativa = self._base_url.removesuffix("/v1")
        self._modelo_chat_selecionado: str | None = None
        self._modelo_embedding = modelo_embedding
        self._max_tokens_resposta = max_tokens_resposta

    def listar_modelos_chat(self) -> list[ModeloChat]:
        dados = self._get_json(f"{self._base_url_nativa}/api/v1/models", timeout=20)
        modelos: list[ModeloChat] = []

        for modelo in _exigir_lista(dados.get("models", []), "models"):
            if not isinstance(modelo, dict) or modelo.get("type") != "llm":
                continue

            for instancia in _exigir_lista(modelo.get("loaded_instances", []), "loaded_instances"):
                if not isinstance(instancia, dict):
                    continue

                configuracao = instancia.get("config") or {}
                contexto = configuracao.get("context_length") if isinstance(configuracao, dict) else None
                modelo_id = str(instancia.get("id") or modelo.get("key") or "")
                if not modelo_id:
                    continue

                modelos.append(
                    ModeloChat(
                        id=modelo_id,
                        modelo=str(modelo.get("key", "")),
                        nome=str(modelo.get("display_name") or modelo.get("key", "")),
                        contexto=contexto if isinstance(contexto, int) else None,
                    )
                )

        return modelos

    def listar_modelos_chat_carregados(self) -> list[ModeloChat]:
        return self.listar_modelos_chat()

    def obter_estado_modelos_chat(self) -> EstadoModelosChat:
        try:
            modelos = self.listar_modelos_chat()
        except Exception as erro:
            return EstadoModelosChat(
                modelos=(),
                modelo_ativo=None,
                exige_selecao=False,
                aviso=f"Nao foi possivel consultar o LM Studio: {erro}",
            )

        modelo_ativo = self._resolver_modelo_chat_carregado(modelos, exigir_resolucao=False)
        exige_selecao = len(modelos) > 1 and modelo_ativo is None
        aviso = None
        if not modelos:
            aviso = "Nenhum modelo LLM carregado no LM Studio."
        elif exige_selecao:
            aviso = "Mais de um modelo LLM carregado. Selecione qual sera usado nas consultas."

        return EstadoModelosChat(
            modelos=tuple(modelo.com_selecao(modelo.id == modelo_ativo) for modelo in modelos),
            modelo_ativo=modelo_ativo,
            exige_selecao=exige_selecao,
            aviso=aviso,
        )

    def selecionar_modelo_chat(self, modelo_id: str) -> EstadoModelosChat:
        modelos = self.listar_modelos_chat()
        for modelo in modelos:
            if modelo.id == modelo_id:
                self._modelo_chat_selecionado = modelo.id
                return self.obter_estado_modelos_chat()

        raise ModeloNaoEncontrado(
            "Modelo informado nao esta carregado no LM Studio.",
            provedor=PROVEDOR,
            modelo=modelo_id,
        )

    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        modelo = solicitacao.modelo or self._modelo_embedding
        dados = self._post_json(
            f"{self._base_url}/embeddings",
            json={"model": modelo, "input": solicitacao.texto},
            timeout=60,
            modelo=modelo,
        )

        try:
            vetor = dados["data"][0]["embedding"]
            return RespostaEmbedding(vetor=vetor, modelo=modelo)
        except (KeyError, IndexError, TypeError, ValueError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de embeddings do LM Studio nao possui vetor esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        contextos = list(solicitacao.contextos)
        contexto = "\n\n---\n\n".join(contextos) or "Nenhum contexto encontrado."
        modelo_chat = solicitacao.modelo or self._resolver_modelo_chat()
        temperatura = solicitacao.temperatura if solicitacao.temperatura is not None else 0.1
        max_tokens = solicitacao.max_tokens if solicitacao.max_tokens is not None else self._max_tokens_resposta

        dados = self._post_json(
            f"{self._base_url}/responses",
            json={
                "model": modelo_chat,
                "instructions": (
                    "Voce responde apenas com base no contexto fornecido. "
                    "Quando nao houver informacao suficiente, diga isso claramente. "
                    "Responda exclusivamente em portugues do Brasil. "
                    "Nao traduza nomes de campos para ingles. "
                    "Use os termos exatamente como aparecem no contexto quando citar funcionario, cliente, status ou problema. "
                    "Entregue a resposta final sem raciocinio interno. "
                    "Comece a resposta final com 'Resposta:' e depois escreva a resposta em linguagem natural."
                ),
                "input": f"Contexto:\n{contexto}\n\nPergunta:\n{solicitacao.pergunta}",
                "temperature": temperatura,
                "max_output_tokens": max_tokens,
                "reasoning": {"effort": "minimal"},
            },
            timeout=300,
            modelo=modelo_chat,
        )
        texto_final = self._extrair_texto_resposta(dados)
        texto_final = self._normalizar_resposta_final(texto_final)
        if (
            len(texto_final) < 4
            or texto_final == "<texto final>"
            or self._precisa_resposta_fallback(texto_final)
            or self._parece_truncada(texto_final)
        ):
            texto_final = self._montar_resposta_fallback(contextos)

        return RespostaLLM(texto=texto_final, modelo=modelo_chat)

    def _resolver_modelo_chat(self) -> str:
        modelos = self.listar_modelos_chat()
        modelo_resolvido = self._resolver_modelo_chat_carregado(modelos, exigir_resolucao=True)
        if modelo_resolvido is None:
            raise ModeloNaoEncontrado("Nenhum modelo LLM carregado no LM Studio.", provedor=PROVEDOR)
        return modelo_resolvido

    def _resolver_modelo_chat_carregado(
        self,
        modelos: list[ModeloChat],
        exigir_resolucao: bool,
    ) -> str | None:
        ids_carregados = {modelo.id for modelo in modelos}

        if self._modelo_chat_selecionado and self._modelo_chat_selecionado in ids_carregados:
            return self._modelo_chat_selecionado

        if self._modelo_chat_selecionado and self._modelo_chat_selecionado not in ids_carregados:
            self._modelo_chat_selecionado = None

        if len(modelos) == 1:
            return modelos[0].id

        if exigir_resolucao and len(modelos) > 1:
            raise ModeloNaoEncontrado(
                "Mais de um modelo LLM carregado. Selecione o modelo desejado antes da consulta.",
                provedor=PROVEDOR,
            )

        return None

    def _get_json(self, url: str, timeout: int | float, modelo: str | None = None) -> dict[str, Any]:
        try:
            resposta = httpx.get(url, timeout=timeout)
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor("Tempo limite ao consultar o LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel("Nao foi possivel conectar ao LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro

    def _post_json(
        self,
        url: str,
        *,
        json: dict[str, object],
        timeout: int | float,
        modelo: str | None = None,
    ) -> dict[str, Any]:
        try:
            resposta = httpx.post(url, json=json, timeout=timeout)
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor("Tempo limite ao consultar o LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel("Nao foi possivel conectar ao LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro

    def _extrair_json(self, resposta: httpx.Response, modelo: str | None) -> dict[str, Any]:
        try:
            dados = resposta.json()
        except ValueError as erro:
            raise RespostaInvalidaProvedor(
                "Resposta do LM Studio nao e JSON valido.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

        if not isinstance(dados, dict):
            raise RespostaInvalidaProvedor(
                "Resposta do LM Studio nao possui objeto JSON esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        return dados

    def _converter_erro_http(self, erro: httpx.HTTPStatusError, modelo: str | None) -> Exception:
        status_code = erro.response.status_code
        detalhe = _resumir_resposta_http(erro.response)

        if status_code in (401, 403):
            return AutenticacaoProvedor("Autenticacao recusada pelo LM Studio.", provedor=PROVEDOR, modelo=modelo)
        if status_code == 404:
            return ModeloNaoEncontrado("Recurso ou modelo nao encontrado no LM Studio.", provedor=PROVEDOR, modelo=modelo)
        if status_code == 429:
            return LimiteTaxaProvedor("Limite de uso atingido no LM Studio.", provedor=PROVEDOR, modelo=modelo)

        return ProvedorIndisponivel(
            f"LM Studio retornou HTTP {status_code}: {detalhe}",
            provedor=PROVEDOR,
            modelo=modelo,
        )

    def _extrair_texto_resposta(self, dados: dict[str, Any]) -> str:
        textos: list[str] = []
        raciocinios: list[str] = []
        for item in dados.get("output", []):
            if not isinstance(item, dict):
                continue
            conteudos = item.get("content", [])
            if not isinstance(conteudos, list):
                continue
            for conteudo in conteudos:
                if not isinstance(conteudo, dict):
                    continue
                if item.get("type") == "message" and conteudo.get("type") == "output_text":
                    textos.append(conteudo.get("text", ""))
                if item.get("type") == "reasoning" and conteudo.get("type") == "reasoning_text":
                    raciocinios.append(conteudo.get("text", ""))

        texto_final = "\n".join(texto.strip() for texto in textos if texto.strip())
        if not texto_final:
            texto_final = self._extrair_resposta_do_raciocinio(raciocinios)
        return texto_final

    def _normalizar_resposta_final(self, texto: str) -> str:
        return re.sub(r"^\s*resposta\s*:\s*", "", texto.strip(), flags=re.IGNORECASE)

    def _precisa_resposta_fallback(self, texto: str) -> bool:
        marcadores_ingles = [
            "functionary",
            "client ",
            "service data",
            "service ",
            "status completed",
            "problems found",
            "network",
            "beginning",
            "recordo",
        ]
        texto_baixo = texto.lower()
        return any(marcador in texto_baixo for marcador in marcadores_ingles)

    def _parece_truncada(self, texto: str) -> bool:
        texto_limpo = texto.strip()
        if not texto_limpo:
            return True
        return not texto_limpo.endswith((".", "!", "?"))

    def _extrair_resposta_do_raciocinio(self, raciocinios: list[str]) -> str:
        linhas = "\n".join(raciocinios).splitlines()
        padroes = [
            r"(?:resposta final|resposta|answer|final answer)\s*:\s*(.+)",
            r"(?:final decision|final output)\s*:\s*(.+)",
        ]

        for linha in reversed(linhas):
            texto = linha.strip().strip("*- ")
            for padrao in padroes:
                encontrado = re.search(padrao, texto, flags=re.IGNORECASE)
                if encontrado:
                    candidato = encontrado.group(1).strip().strip("\"' .")
                    if len(candidato) >= 4:
                        return candidato

        return ""

    def _montar_resposta_fallback(self, contextos: list[str]) -> str:
        if not contextos:
            return "Nao foram encontrados registros relacionados a pergunta."

        campos = self._mapear_campos_contexto(contextos[0])
        cliente = campos.get("Cliente ou local", "cliente/local nao informado")
        data_servico = campos.get("Data do servico", "data nao informada")
        problemas = campos.get("Problemas encontrados", "sem problemas informados")

        return (
            f"Encontrei um registro relacionado ao cliente/local {cliente}, "
            f"na data {data_servico}. Problemas encontrados: {problemas}"
        )

    def _mapear_campos_contexto(self, contexto: str) -> dict[str, str]:
        campos: dict[str, str] = {}
        for linha in contexto.splitlines():
            if ":" not in linha:
                continue
            chave, valor = linha.split(":", 1)
            campos[chave.strip()] = valor.strip()
        return campos


def _exigir_lista(valor: object, campo: str) -> list[Any]:
    if isinstance(valor, list):
        return valor
    raise RespostaInvalidaProvedor(
        f"Resposta do LM Studio nao possui lista esperada em '{campo}'.",
        provedor=PROVEDOR,
    )


def _resumir_resposta_http(resposta: httpx.Response) -> str:
    texto = resposta.text.strip()
    if len(texto) > 180:
        return f"{texto[:177]}..."
    return texto
