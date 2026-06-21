from app.dominio.objetos_valor import EstadoModelosChat, ModeloChat


class CatalogoModelosOpenAICompativel:
    def __init__(self, modelo_chat: str | None) -> None:
        self._modelo_chat = _normalizar_modelo(modelo_chat)

    def listar_modelos_chat(self) -> list[ModeloChat]:
        if self._modelo_chat is None:
            return []
        return [
            ModeloChat(
                id=self._modelo_chat,
                modelo=self._modelo_chat,
                nome=self._modelo_chat,
                contexto=None,
                selecionado=True,
            )
        ]

    def obter_estado_modelos_chat(self) -> EstadoModelosChat:
        modelos = self.listar_modelos_chat()
        if not modelos:
            return EstadoModelosChat(
                modelos=(),
                modelo_ativo=None,
                exige_selecao=False,
                aviso="Configure MODELO_CHAT para usar o provedor OpenAI-compatible.",
            )

        return EstadoModelosChat(
            modelos=tuple(modelos),
            modelo_ativo=modelos[0].id,
            exige_selecao=False,
            aviso=None,
        )


def _normalizar_modelo(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None
