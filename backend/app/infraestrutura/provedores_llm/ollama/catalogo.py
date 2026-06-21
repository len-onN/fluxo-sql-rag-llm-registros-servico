from typing import Any

from app.dominio.objetos_valor import EstadoModelosChat, ModeloChat
from app.nucleo.erros import RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteOllama
from .selecao import ResolvedorModeloChatOllama


class CatalogoModelosOllama:
    def __init__(self, cliente: ClienteOllama, resolvedor: ResolvedorModeloChatOllama) -> None:
        self._cliente = cliente
        self._resolvedor = resolvedor

    def listar_modelos_chat(self) -> list[ModeloChat]:
        dados = self._cliente.obter_json("/api/tags", timeout=20)
        modelos: list[ModeloChat] = []

        for modelo in _exigir_lista(dados.get("models", []), "models"):
            if not isinstance(modelo, dict):
                continue

            modelo_id = str(modelo.get("model") or modelo.get("name") or "").strip()
            if not modelo_id:
                continue

            modelos.append(
                ModeloChat(
                    id=modelo_id,
                    modelo=modelo_id,
                    nome=str(modelo.get("name") or modelo_id),
                    contexto=None,
                )
            )

        return modelos

    def obter_estado_modelos_chat(self) -> EstadoModelosChat:
        try:
            modelos = self.listar_modelos_chat()
        except Exception as erro:
            return EstadoModelosChat(
                modelos=(),
                modelo_ativo=None,
                exige_selecao=False,
                aviso=f"Nao foi possivel consultar o Ollama: {erro}",
            )

        modelo_ativo = self._resolvedor.resolver(modelos, exigir_resolucao=False)
        exige_selecao = len(modelos) > 1 and modelo_ativo is None
        aviso = None
        if not modelos:
            aviso = "Nenhum modelo local encontrado no Ollama."
        elif exige_selecao:
            aviso = "Mais de um modelo local encontrado no Ollama. Selecione qual sera usado nas consultas."

        return EstadoModelosChat(
            modelos=tuple(modelo.com_selecao(modelo.id == modelo_ativo) for modelo in modelos),
            modelo_ativo=modelo_ativo,
            exige_selecao=exige_selecao,
            aviso=aviso,
        )


def _exigir_lista(valor: object, campo: str) -> list[Any]:
    if isinstance(valor, list):
        return valor
    raise RespostaInvalidaProvedor(
        f"Resposta do Ollama nao possui lista esperada em '{campo}'.",
        provedor=PROVEDOR,
    )
