from typing import Any

from app.dominio.objetos_valor import EstadoModelosChat, ModeloChat
from app.nucleo.erros import RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteLMStudio
from .selecao import ResolvedorModeloChatLMStudio


class CatalogoModelosLMStudio:
    def __init__(self, cliente: ClienteLMStudio, resolvedor: ResolvedorModeloChatLMStudio) -> None:
        self._cliente = cliente
        self._resolvedor = resolvedor

    def listar_modelos_chat(self) -> list[ModeloChat]:
        dados = self._cliente.obter_json(self._cliente.url_nativa("/api/v1/models"), timeout=20)
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

        modelo_ativo = self._resolvedor.resolver(modelos, exigir_resolucao=False)
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


def _exigir_lista(valor: object, campo: str) -> list[Any]:
    if isinstance(valor, list):
        return valor
    raise RespostaInvalidaProvedor(
        f"Resposta do LM Studio nao possui lista esperada em '{campo}'.",
        provedor=PROVEDOR,
    )
