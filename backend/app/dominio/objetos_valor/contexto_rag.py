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
