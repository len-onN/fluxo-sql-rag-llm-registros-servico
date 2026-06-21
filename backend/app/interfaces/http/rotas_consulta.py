from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.infraestrutura.container import ContainerAplicacao
from app.interfaces.http.dependencias import obter_container

roteador = APIRouter(prefix="/api/consulta", tags=["consulta-rag"])


class ConsultaEntrada(BaseModel):
    pergunta: str = Field(min_length=5)
    limite: int = Field(default=5, ge=1, le=10)


class ConsultaSaida(BaseModel):
    resposta: str
    contextos: list[str]
    aviso: str | None = None


@roteador.post("", response_model=ConsultaSaida)
def consultar(
    entrada: ConsultaEntrada,
    container: ContainerAplicacao = Depends(obter_container),
) -> ConsultaSaida:
    resultado = container.consultar_registros.executar(entrada.pergunta, entrada.limite)
    return ConsultaSaida(
        resposta=resultado.resposta,
        contextos=resultado.contextos,
        aviso=resultado.aviso,
    )
