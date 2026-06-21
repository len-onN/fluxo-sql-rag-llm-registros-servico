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
        return "\n".join(
            [
                f"Funcionario: {self.funcionario}",
                f"Cliente ou local: {self.cliente_local}",
                f"Data do servico: {self.data_servico.isoformat()}",
                f"Tipo de servico: {self.tipo_servico}",
                f"Status: {self.status}",
                f"Descricao: {self.descricao}",
                f"Problemas encontrados: {self.problemas or 'Nao informado'}",
                f"Observacoes importantes: {self.observacoes or 'Nao informado'}",
            ]
        )

    def calcular_hash_conteudo_rag(self) -> str:
        conteudo = self.texto_para_rag().encode("utf-8")
        return hashlib.sha256(conteudo).hexdigest()
