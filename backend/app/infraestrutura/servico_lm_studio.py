import re
from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class ModeloChatCarregado:
    id: str
    modelo: str
    nome: str
    contexto: int | None


class ServicoLMStudio:
    def __init__(self, base_url: str, modelo_embedding: str, max_tokens_resposta: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._base_url_nativa = self._base_url.removesuffix("/v1")
        self._modelo_chat_selecionado: str | None = None
        self._modelo_embedding = modelo_embedding
        self._max_tokens_resposta = max_tokens_resposta

    def listar_modelos_chat_carregados(self) -> list[ModeloChatCarregado]:
        resposta = httpx.get(f"{self._base_url_nativa}/api/v1/models", timeout=20)
        resposta.raise_for_status()
        dados = resposta.json()
        modelos: list[ModeloChatCarregado] = []

        for modelo in dados.get("models", []):
            if modelo.get("type") != "llm":
                continue

            for instancia in modelo.get("loaded_instances", []):
                configuracao = instancia.get("config") or {}
                modelos.append(
                    ModeloChatCarregado(
                        id=instancia.get("id") or modelo.get("key"),
                        modelo=modelo.get("key", ""),
                        nome=modelo.get("display_name") or modelo.get("key", ""),
                        contexto=configuracao.get("context_length"),
                    )
                )

        return modelos

    def obter_estado_modelos_chat(self) -> dict:
        try:
            modelos = self.listar_modelos_chat_carregados()
        except Exception as erro:
            return {
                "modelos": [],
                "modelo_ativo": None,
                "exige_selecao": False,
                "aviso": f"Nao foi possivel consultar o LM Studio: {erro}",
            }

        modelo_ativo = self._resolver_modelo_chat_carregado(modelos, exigir_resolucao=False)
        exige_selecao = len(modelos) > 1 and modelo_ativo is None
        aviso = None
        if not modelos:
            aviso = "Nenhum modelo LLM carregado no LM Studio."
        elif exige_selecao:
            aviso = "Mais de um modelo LLM carregado. Selecione qual sera usado nas consultas."

        return {
            "modelos": [
                {
                    "id": modelo.id,
                    "modelo": modelo.modelo,
                    "nome": modelo.nome,
                    "contexto": modelo.contexto,
                    "selecionado": modelo.id == modelo_ativo,
                }
                for modelo in modelos
            ],
            "modelo_ativo": modelo_ativo,
            "exige_selecao": exige_selecao,
            "aviso": aviso,
        }

    def selecionar_modelo_chat(self, modelo_id: str) -> dict:
        modelos = self.listar_modelos_chat_carregados()
        for modelo in modelos:
            if modelo.id == modelo_id:
                self._modelo_chat_selecionado = modelo.id
                return self.obter_estado_modelos_chat()

        raise ValueError("Modelo informado nao esta carregado no LM Studio.")

    def gerar_embedding(self, texto: str) -> list[float]:
        resposta = httpx.post(
            f"{self._base_url}/embeddings",
            json={"model": self._modelo_embedding, "input": texto},
            timeout=60,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        return dados["data"][0]["embedding"]

    def responder(self, pergunta: str, contextos: list[str]) -> str:
        contexto = "\n\n---\n\n".join(contextos) or "Nenhum contexto encontrado."
        modelo_chat = self._resolver_modelo_chat()

        resposta = httpx.post(
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
                "input": f"Contexto:\n{contexto}\n\nPergunta:\n{pergunta}",
                "temperature": 0.1,
                "max_output_tokens": self._max_tokens_resposta,
                "reasoning": {"effort": "minimal"},
            },
            timeout=300,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        texto_final = self._extrair_texto_resposta(dados)
        texto_final = self._normalizar_resposta_final(texto_final)
        if (
            len(texto_final) < 4
            or texto_final == "<texto final>"
            or self._precisa_resposta_fallback(texto_final)
            or self._parece_truncada(texto_final)
        ):
            return self._montar_resposta_fallback(contextos)
        return texto_final

    def _resolver_modelo_chat(self) -> str:
        modelos = self.listar_modelos_chat_carregados()
        modelo_resolvido = self._resolver_modelo_chat_carregado(modelos, exigir_resolucao=True)
        if modelo_resolvido is None:
            raise ValueError("Nenhum modelo LLM carregado no LM Studio.")
        return modelo_resolvido

    def _resolver_modelo_chat_carregado(
        self,
        modelos: list[ModeloChatCarregado],
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
            raise ValueError("Mais de um modelo LLM carregado. Selecione o modelo desejado antes da consulta.")

        return None

    def _extrair_texto_resposta(self, dados: dict) -> str:
        textos: list[str] = []
        raciocinios: list[str] = []
        for item in dados.get("output", []):
            for conteudo in item.get("content", []):
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
