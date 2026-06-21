from typing import Any, Mapping

import httpx

from app.nucleo.erros import (
    AutenticacaoProvedor,
    CapacidadeNaoSuportada,
    LimiteTaxaProvedor,
    ModeloNaoEncontrado,
    ProvedorIndisponivel,
    RespostaInvalidaProvedor,
    TimeoutProvedor,
)


PROVEDOR = "ollama"


class ClienteOllama:
    def __init__(
        self,
        base_url: str,
        cliente_http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cliente_http = cliente_http or httpx.Client()

    def url(self, caminho: str) -> str:
        return f"{self._base_url}{self._normalizar_caminho(caminho)}"

    def obter_json(
        self,
        caminho: str,
        *,
        timeout: int | float,
        modelo: str | None = None,
        capacidade: str | None = None,
    ) -> dict[str, Any]:
        try:
            resposta = self._cliente_http.get(self.url(caminho), timeout=timeout)
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor(
                "Tempo limite ao consultar o Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo, capacidade) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel(
                "Nao foi possivel conectar ao Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

    def postar_json(
        self,
        caminho: str,
        *,
        json: Mapping[str, object],
        timeout: int | float,
        modelo: str | None = None,
        capacidade: str | None = None,
    ) -> dict[str, Any]:
        try:
            resposta = self._cliente_http.post(
                self.url(caminho),
                json=dict(json),
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor(
                "Tempo limite ao consultar o Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo, capacidade) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel(
                "Nao foi possivel conectar ao Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

    def fechar(self) -> None:
        self._cliente_http.close()

    def _extrair_json(self, resposta: httpx.Response, modelo: str | None) -> dict[str, Any]:
        try:
            dados = resposta.json()
        except ValueError as erro:
            raise RespostaInvalidaProvedor(
                "Resposta do Ollama nao e JSON valido.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

        if not isinstance(dados, dict):
            raise RespostaInvalidaProvedor(
                "Resposta do Ollama nao possui objeto JSON esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        return dados

    def _converter_erro_http(
        self,
        erro: httpx.HTTPStatusError,
        modelo: str | None,
        capacidade: str | None,
    ) -> Exception:
        status_code = erro.response.status_code
        detalhe = _resumir_resposta_http(erro.response)

        if status_code in (401, 403):
            return AutenticacaoProvedor(
                "Autenticacao recusada pelo Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        if _parece_capacidade_nao_suportada(detalhe, capacidade):
            return CapacidadeNaoSuportada(
                f"Modelo Ollama nao suporta a capacidade de {capacidade}.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        if status_code == 404 or (status_code == 400 and _parece_modelo_inexistente(detalhe)):
            return ModeloNaoEncontrado(
                "Modelo nao encontrado no Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        if status_code == 429:
            return LimiteTaxaProvedor(
                "Limite de uso atingido no Ollama.",
                provedor=PROVEDOR,
                modelo=modelo,
            )

        return ProvedorIndisponivel(
            f"Ollama retornou HTTP {status_code}: {detalhe}",
            provedor=PROVEDOR,
            modelo=modelo,
        )

    def _normalizar_caminho(self, caminho: str) -> str:
        if caminho.startswith("/"):
            return caminho
        return f"/{caminho}"


def _resumir_resposta_http(resposta: httpx.Response) -> str:
    detalhe_json = _extrair_detalhe_json(resposta)
    texto = detalhe_json or resposta.text.strip()
    if len(texto) > 180:
        return f"{texto[:177]}..."
    return texto


def _extrair_detalhe_json(resposta: httpx.Response) -> str | None:
    try:
        dados = resposta.json()
    except ValueError:
        return None
    if not isinstance(dados, dict):
        return None

    erro = dados.get("error") or dados.get("message")
    if erro is None:
        return None
    return str(erro).strip() or None


def _parece_modelo_inexistente(detalhe: str) -> bool:
    detalhe = detalhe.lower()
    return "model" in detalhe and ("not found" in detalhe or "does not exist" in detalhe)


def _parece_capacidade_nao_suportada(detalhe: str, capacidade: str | None) -> bool:
    if not capacidade:
        return False

    detalhe = detalhe.lower()
    capacidade = capacidade.lower()
    termos_negacao = ("does not support", "doesn't support", "not support", "unsupported")
    return capacidade in detalhe and any(termo in detalhe for termo in termos_negacao)
