from typing import Any, Mapping

import httpx

from app.nucleo.erros import (
    AutenticacaoProvedor,
    LimiteTaxaProvedor,
    ModeloNaoEncontrado,
    ProvedorIndisponivel,
    RespostaInvalidaProvedor,
    TimeoutProvedor,
)


PROVEDOR = "openai_compativel"


class ClienteOpenAICompativel:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        cliente_http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = _normalizar_api_key(api_key)
        self._cliente_http = cliente_http or httpx.Client()

    def url(self, caminho: str) -> str:
        return f"{self._base_url}{self._normalizar_caminho(caminho)}"

    def postar_json(
        self,
        caminho: str,
        *,
        json: Mapping[str, object],
        timeout: int | float,
        modelo: str | None = None,
    ) -> dict[str, Any]:
        try:
            resposta = self._cliente_http.post(
                self.url(caminho),
                json=dict(json),
                headers=self._montar_headers(),
                timeout=timeout,
            )
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor(
                "Tempo limite ao consultar o provedor OpenAI-compatible.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel(
                "Nao foi possivel conectar ao provedor OpenAI-compatible.",
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
                "Resposta do provedor OpenAI-compatible nao e JSON valido.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro

        if not isinstance(dados, dict):
            raise RespostaInvalidaProvedor(
                "Resposta do provedor OpenAI-compatible nao possui objeto JSON esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        return dados

    def _converter_erro_http(self, erro: httpx.HTTPStatusError, modelo: str | None) -> Exception:
        status_code = erro.response.status_code
        detalhe = _resumir_resposta_http(erro.response)

        if status_code in (401, 403):
            return AutenticacaoProvedor(
                "Autenticacao recusada pelo provedor OpenAI-compatible.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        if status_code == 404 or (status_code == 400 and _parece_modelo_inexistente(detalhe)):
            return ModeloNaoEncontrado(
                "Modelo nao encontrado no provedor OpenAI-compatible.",
                provedor=PROVEDOR,
                modelo=modelo,
            )
        if status_code == 429:
            return LimiteTaxaProvedor(
                "Limite de uso atingido no provedor OpenAI-compatible.",
                provedor=PROVEDOR,
                modelo=modelo,
            )

        return ProvedorIndisponivel(
            f"Provedor OpenAI-compatible retornou HTTP {status_code}: {detalhe}",
            provedor=PROVEDOR,
            modelo=modelo,
        )

    def _montar_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _normalizar_caminho(self, caminho: str) -> str:
        if caminho.startswith("/"):
            return caminho
        return f"/{caminho}"


def _normalizar_api_key(api_key: str | None) -> str | None:
    if api_key is None:
        return None
    api_key = api_key.strip()
    return api_key or None


def _resumir_resposta_http(resposta: httpx.Response) -> str:
    texto = resposta.text.strip()
    if len(texto) > 180:
        return f"{texto[:177]}..."
    return texto


def _parece_modelo_inexistente(detalhe: str) -> bool:
    detalhe = detalhe.lower()
    return "model" in detalhe and ("not found" in detalhe or "does not exist" in detalhe)
