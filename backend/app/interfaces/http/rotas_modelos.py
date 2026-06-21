from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.infraestrutura.container import ContainerAplicacao
from app.interfaces.http.dependencias import obter_container
from app.nucleo.erros import ErroProvedor, ModeloNaoEncontrado

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


class EstadoProvedoresSaida(BaseModel):
    provedor_chat: str
    provedor_embeddings: str
    modelo_chat: str | None = None
    modelo_embedding: str


class SelecaoModeloEntrada(BaseModel):
    modelo: str = Field(min_length=1)


@roteador.get("/provedor", response_model=EstadoProvedoresSaida)
def obter_provedor_ativo(container: ContainerAplicacao = Depends(obter_container)) -> dict:
    return container.estado_provedores.como_dict()


@roteador.get("/chat", response_model=EstadoModelosChatSaida)
def obter_modelos_chat(container: ContainerAplicacao = Depends(obter_container)) -> dict:
    return container.catalogo_modelos.obter_estado_modelos_chat().como_dict()


@roteador.post("/chat/selecionar", response_model=EstadoModelosChatSaida)
def selecionar_modelo_chat(
    entrada: SelecaoModeloEntrada,
    container: ContainerAplicacao = Depends(obter_container),
) -> dict:
    try:
        return container.seletor_modelo.selecionar_modelo_chat(entrada.modelo).como_dict()
    except ModeloNaoEncontrado as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except ErroProvedor as erro:
        raise HTTPException(status_code=503, detail=str(erro)) from erro
