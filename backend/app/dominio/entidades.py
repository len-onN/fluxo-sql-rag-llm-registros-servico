import hashlib
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone

from app.dominio.objetos_valor import EstadoIndexacao


@dataclass(slots=True)
class RegistroServico:
    funcionario: str
    cliente_local: str
    tipo_servico: str
    status: str
    descricao: str
    problemas: str
    observacoes: str
    data_servico: date
    id: int | None = None
    criado_em: datetime | None = None
    indexado_em: datetime | None = None
    erro_indexacao: str | None = None
    modelo_embedding: str | None = None
    hash_conteudo_rag: str | None = None

    def com_id(self, id_registro: int) -> "RegistroServico":
        return replace(self, id=id_registro, criado_em=self.criado_em or datetime.now(timezone.utc))

    @property
    def estado_indexacao(self) -> EstadoIndexacao:
        if self.erro_indexacao:
            return EstadoIndexacao.ERRO
        if self.indexado_em is not None:
            return EstadoIndexacao.INDEXADO
        return EstadoIndexacao.PENDENTE

    def texto_para_rag(self) -> str:
        return montar_texto_registro_para_rag(
            funcionario=self.funcionario,
            cliente_local=self.cliente_local,
            data_servico=self.data_servico,
            tipo_servico=self.tipo_servico,
            status=self.status,
            descricao=self.descricao,
            problemas=self.problemas,
            observacoes=self.observacoes,
        )

    def calcular_hash_conteudo_rag(self) -> str:
        return calcular_hash_texto_rag(self.texto_para_rag())


def montar_texto_registro_para_rag(
    *,
    funcionario: str,
    cliente_local: str,
    data_servico: date | str,
    tipo_servico: str,
    status: str,
    descricao: str,
    problemas: str | None,
    observacoes: str | None,
) -> str:
    data_servico_texto = data_servico.isoformat() if isinstance(data_servico, date) else data_servico

    return "\n".join(
        [
            f"Funcionario: {funcionario}",
            f"Cliente ou local: {cliente_local}",
            f"Data do servico: {data_servico_texto}",
            f"Tipo de servico: {tipo_servico}",
            f"Status: {status}",
            f"Descricao: {descricao}",
            f"Problemas encontrados: {problemas or 'Nao informado'}",
            f"Observacoes importantes: {observacoes or 'Nao informado'}",
        ]
    )


def calcular_hash_texto_rag(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def calcular_hash_conteudo_rag_campos(
    funcionario: str,
    cliente_local: str,
    data_servico: date | str,
    tipo_servico: str,
    status: str,
    descricao: str,
    problemas: str | None,
    observacoes: str | None,
) -> str:
    return calcular_hash_texto_rag(
        montar_texto_registro_para_rag(
            funcionario=funcionario,
            cliente_local=cliente_local,
            data_servico=data_servico,
            tipo_servico=tipo_servico,
            status=status,
            descricao=descricao,
            problemas=problemas,
            observacoes=observacoes,
        )
    )
