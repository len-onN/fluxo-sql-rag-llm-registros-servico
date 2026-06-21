from dataclasses import dataclass, field, replace

MetadadoProvedor = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class SolicitacaoEmbedding:
    texto: str
    modelo: str | None = None
    metadados: dict[str, MetadadoProvedor] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RespostaEmbedding:
    vetor: tuple[float, ...]
    modelo: str | None = None
    metadados: dict[str, MetadadoProvedor] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "vetor", tuple(float(valor) for valor in self.vetor))

    @property
    def dimensoes(self) -> int:
        return len(self.vetor)

    def como_lista(self) -> list[float]:
        return list(self.vetor)


@dataclass(frozen=True, slots=True)
class SolicitacaoLLM:
    pergunta: str
    contextos: tuple[str, ...] = ()
    prompt_usuario: str | None = None
    modelo: str | None = None
    temperatura: float | None = None
    max_tokens: int | None = None
    metadados: dict[str, MetadadoProvedor] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "contextos", tuple(str(contexto) for contexto in self.contextos))
        if self.prompt_usuario is not None:
            object.__setattr__(self, "prompt_usuario", str(self.prompt_usuario))


@dataclass(frozen=True, slots=True)
class RespostaLLM:
    texto: str
    modelo: str | None = None
    metadados: dict[str, MetadadoProvedor] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModeloChat:
    id: str
    modelo: str
    nome: str
    contexto: int | None = None
    selecionado: bool = False

    def com_selecao(self, selecionado: bool) -> "ModeloChat":
        return replace(self, selecionado=selecionado)


@dataclass(frozen=True, slots=True)
class EstadoModelosChat:
    modelos: tuple[ModeloChat, ...]
    modelo_ativo: str | None = None
    exige_selecao: bool = False
    aviso: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "modelos", tuple(self.modelos))

    def como_dict(self) -> dict[str, object]:
        return {
            "modelos": [
                {
                    "id": modelo.id,
                    "modelo": modelo.modelo,
                    "nome": modelo.nome,
                    "contexto": modelo.contexto,
                    "selecionado": modelo.selecionado,
                }
                for modelo in self.modelos
            ],
            "modelo_ativo": self.modelo_ativo,
            "exige_selecao": self.exige_selecao,
            "aviso": self.aviso,
        }
