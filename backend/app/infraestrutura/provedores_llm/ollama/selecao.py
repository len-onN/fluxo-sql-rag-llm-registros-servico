from collections.abc import Sequence

from app.dominio.objetos_valor import EstadoModelosChat, ModeloChat
from app.dominio.portas import CatalogoModelos
from app.nucleo.erros import ModeloNaoEncontrado

from .cliente import PROVEDOR


class ResolvedorModeloChatOllama:
    def __init__(self, modelo_chat_inicial: str | None = None) -> None:
        self._modelo_chat_selecionado = _normalizar_modelo(modelo_chat_inicial)

    def selecionar(self, modelo_id: str) -> None:
        self._modelo_chat_selecionado = modelo_id

    def resolver(self, modelos: Sequence[ModeloChat], exigir_resolucao: bool) -> str | None:
        if self._modelo_chat_selecionado:
            modelo_resolvido = self._resolver_modelo_configurado(modelos, self._modelo_chat_selecionado)
            if modelo_resolvido is not None:
                return modelo_resolvido
            self._modelo_chat_selecionado = None

        if len(modelos) == 1:
            return modelos[0].id

        if exigir_resolucao and len(modelos) > 1:
            raise ModeloNaoEncontrado(
                "Mais de um modelo local encontrado no Ollama. Selecione o modelo desejado antes da consulta.",
                provedor=PROVEDOR,
            )

        return None

    def _resolver_modelo_configurado(self, modelos: Sequence[ModeloChat], modelo_configurado: str) -> str | None:
        for modelo in modelos:
            if modelo.id == modelo_configurado or modelo.modelo == modelo_configurado:
                return modelo.id
        return None


class SeletorModeloOllama:
    def __init__(self, catalogo_modelos: CatalogoModelos, resolvedor: ResolvedorModeloChatOllama) -> None:
        self._catalogo_modelos = catalogo_modelos
        self._resolvedor = resolvedor

    def selecionar_modelo_chat(self, modelo_id: str) -> EstadoModelosChat:
        modelos = self._catalogo_modelos.listar_modelos_chat()
        for modelo in modelos:
            if modelo.id == modelo_id or modelo.modelo == modelo_id:
                self._resolvedor.selecionar(modelo.id)
                return self._catalogo_modelos.obter_estado_modelos_chat()

        raise ModeloNaoEncontrado(
            "Modelo informado nao esta disponivel no Ollama.",
            provedor=PROVEDOR,
            modelo=modelo_id,
        )


def _normalizar_modelo(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None
