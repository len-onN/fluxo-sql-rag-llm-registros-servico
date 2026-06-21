from datetime import date, datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.dominio.entidades import RegistroServico
from app.dominio.objetos_valor import EstadoIndexacao
from app.infraestrutura.container import ContainerAplicacao
from app.interfaces.http.dependencias import obter_container

roteador = APIRouter(prefix="/api/registros", tags=["registros"])


class RegistroServicoEntrada(BaseModel):
    funcionario: str = Field(min_length=2)
    cliente_local: str = Field(min_length=2)
    tipo_servico: str = Field(min_length=2)
    status: str = Field(min_length=2)
    descricao: str = Field(min_length=5)
    problemas: str = ""
    observacoes: str = ""
    data_servico: date


class RegistroServicoSaida(BaseModel):
    id: int
    funcionario: str
    cliente_local: str
    tipo_servico: str
    status: str
    descricao: str
    problemas: str
    observacoes: str
    data_servico: date
    criado_em: datetime
    indexado: bool | None = None
    estado_indexacao: EstadoIndexacao
    indexado_em: datetime | None = None
    erro_indexacao: str | None = None
    modelo_embedding: str | None = None
    hash_conteudo_rag: str | None = None
    aviso: str | None = None


@roteador.post("", response_model=RegistroServicoSaida, status_code=status.HTTP_201_CREATED)
def criar_registro(
    entrada: RegistroServicoEntrada,
    container: ContainerAplicacao = Depends(obter_container),
) -> RegistroServicoSaida:
    resultado = container.criar_registro_servico.executar(
        RegistroServico(
            funcionario=entrada.funcionario,
            cliente_local=entrada.cliente_local,
            tipo_servico=entrada.tipo_servico,
            status=entrada.status,
            descricao=entrada.descricao,
            problemas=entrada.problemas,
            observacoes=entrada.observacoes,
            data_servico=entrada.data_servico,
        )
    )
    return _mapear_saida(resultado.registro, resultado.indexado, resultado.aviso)


@roteador.get("", response_model=list[RegistroServicoSaida])
def listar_registros(container: ContainerAplicacao = Depends(obter_container)) -> list[RegistroServicoSaida]:
    registros = container.listar_registros_servico.executar()
    return [_mapear_saida(registro) for registro in registros]


def _mapear_saida(
    registro: RegistroServico,
    indexado: bool | None = None,
    aviso: str | None = None,
) -> RegistroServicoSaida:
    if registro.id is None or registro.criado_em is None:
        raise ValueError("Registro sem identificador ou data de criacao.")

    return RegistroServicoSaida(
        id=registro.id,
        funcionario=registro.funcionario,
        cliente_local=registro.cliente_local,
        tipo_servico=registro.tipo_servico,
        status=registro.status,
        descricao=registro.descricao,
        problemas=registro.problemas,
        observacoes=registro.observacoes,
        data_servico=registro.data_servico,
        criado_em=registro.criado_em,
        indexado=indexado if indexado is not None else registro.estado_indexacao == EstadoIndexacao.INDEXADO,
        estado_indexacao=registro.estado_indexacao,
        indexado_em=registro.indexado_em,
        erro_indexacao=registro.erro_indexacao,
        modelo_embedding=registro.modelo_embedding,
        hash_conteudo_rag=registro.hash_conteudo_rag,
        aviso=aviso,
    )
