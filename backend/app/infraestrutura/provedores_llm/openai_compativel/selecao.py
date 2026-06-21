from app.dominio.objetos_valor import EstadoModelosChat
from app.dominio.portas import CatalogoModelos
from app.nucleo.erros import ModeloNaoEncontrado

from .cliente import PROVEDOR


class SeletorModeloOpenAICompativel:
    def __init__(self, catalogo_modelos: CatalogoModelos) -> None:
        self._catalogo_modelos = catalogo_modelos

    def selecionar_modelo_chat(self, modelo_id: str) -> EstadoModelosChat:
        for modelo in self._catalogo_modelos.listar_modelos_chat():
            if modelo.id == modelo_id or modelo.modelo == modelo_id:
                return self._catalogo_modelos.obter_estado_modelos_chat()

        raise ModeloNaoEncontrado(
            "Modelo de chat OpenAI-compatible deve estar configurado em MODELO_CHAT.",
            provedor=PROVEDOR,
            modelo=modelo_id,
        )
