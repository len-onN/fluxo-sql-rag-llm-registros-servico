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


PROVEDOR = "lm_studio"


class ClienteLMStudio:
    def __init__(self, base_url: str, cliente_http: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._base_url_nativa = self._base_url.removesuffix("/v1")
        self._cliente_http = cliente_http or httpx.Client()

    def url_api(self, caminho: str) -> str:
        return f"{self._base_url}{self._normalizar_caminho(caminho)}"

    def url_nativa(self, caminho: str) -> str:
        return f"{self._base_url_nativa}{self._normalizar_caminho(caminho)}"

    def obter_json(self, url: str, timeout: int | float, modelo: str | None = None) -> dict[str, Any]:
        try:
            resposta = self._cliente_http.get(url, timeout=timeout)
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor("Tempo limite ao consultar o LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel("Nao foi possivel conectar ao LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro

    def postar_json(
        self,
        url: str,
        *,
        json: Mapping[str, object],
        timeout: int | float,
        modelo: str | None = None,
    ) -> dict[str, Any]:
        try:
            resposta = self._cliente_http.post(url, json=dict(json), timeout=timeout)
            resposta.raise_for_status()
            return self._extrair_json(resposta, modelo)
        except httpx.TimeoutException as erro:
            raise TimeoutProvedor("Tempo limite ao consultar o LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro
        except httpx.HTTPStatusError as erro:
            raise self._converter_erro_http(erro, modelo) from erro
        except httpx.RequestError as erro:
            raise ProvedorIndisponivel("Nao foi possivel conectar ao LM Studio.", provedor=PROVEDOR, modelo=modelo) from erro

    def fechar(self) -> None:
        self._cliente_http.close()

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

    def _normalizar_caminho(self, caminho: str) -> str:
        if caminho.startswith("/"):
            return caminho
        return f"/{caminho}"


def _resumir_resposta_http(resposta: httpx.Response) -> str:
    texto = resposta.text.strip()
    if len(texto) > 180:
        return f"{texto[:177]}..."
    return texto
