from dataclasses import dataclass, field

ValorMetadado = str | int | float | bool


@dataclass(frozen=True, slots=True)
class ContextoRAG:
    id_registro: int | None
    documento: str
    metadados: dict[str, ValorMetadado] = field(default_factory=dict)
    distancia: float | None = None
    pontuacao: float | None = None
    fonte: str = "desconhecida"


@dataclass(frozen=True, slots=True)
class FonteContextoRAG:
    id_registro: int | None
    fonte: str
    metadados: dict[str, ValorMetadado] = field(default_factory=dict)
    distancia: float | None = None
    pontuacao: float | None = None

    def como_dict(self) -> dict[str, object]:
        return {
            "id_registro": self.id_registro,
            "fonte": self.fonte,
            "metadados": dict(self.metadados),
            "distancia": self.distancia,
            "pontuacao": self.pontuacao,
        }


@dataclass(frozen=True, slots=True)
class ContextosSelecionadosRAG:
    contextos: tuple[ContextoRAG, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "contextos", tuple(self.contextos))

    @property
    def documentos(self) -> tuple[str, ...]:
        return tuple(contexto.documento for contexto in self.contextos)

    @property
    def fontes(self) -> tuple[FonteContextoRAG, ...]:
        return tuple(
            FonteContextoRAG(
                id_registro=contexto.id_registro,
                fonte=contexto.fonte,
                metadados=contexto.metadados,
                distancia=contexto.distancia,
                pontuacao=contexto.pontuacao,
            )
            for contexto in self.contextos
        )
