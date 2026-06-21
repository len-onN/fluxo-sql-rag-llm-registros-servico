from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.infraestrutura.container import ContainerAplicacao
from app.interfaces.http.dependencias import obter_container

roteador = APIRouter(prefix="/api/modelos", tags=["modelos"])


class ModeloChatSaida(BaseModel):
    id: str
    modelo: str
    nome: str
    contexto: int | None = None
    selecionado: bool


class EstadoModelosChatSaida(BaseModel):
    modelos: list[ModeloChatSaida]
    modelo_ativo: str | None = None
    exige_selecao: bool
    aviso: str | None = None


class SelecaoModeloEntrada(BaseModel):
    modelo: str = Field(min_length=1)


@roteador.get("/chat", response_model=EstadoModelosChatSaida)
def obter_modelos_chat(container: ContainerAplicacao = Depends(obter_container)) -> dict:
    return container.servico_lm_studio.obter_estado_modelos_chat()


@roteador.post("/chat/selecionar", response_model=EstadoModelosChatSaida)
def selecionar_modelo_chat(
    entrada: SelecaoModeloEntrada,
    container: ContainerAplicacao = Depends(obter_container),
) -> dict:
    try:
        return container.servico_lm_studio.selecionar_modelo_chat(entrada.modelo)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
