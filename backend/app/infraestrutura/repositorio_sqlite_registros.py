from contextlib import closing
from datetime import date, datetime, timezone
from sqlite3 import Row

from app.dominio.entidades import RegistroServico
from app.infraestrutura.banco_sqlite import BancoSQLite


class RepositorioSQLiteRegistros:
    def __init__(self, banco: BancoSQLite) -> None:
        self._banco = banco

    def salvar(self, registro: RegistroServico) -> RegistroServico:
        criado_em = registro.criado_em or datetime.now(timezone.utc)

        with closing(self._banco.conectar()) as conexao:
            with conexao:
                cursor = conexao.execute(
                    """
                    insert into registros_servico (
                        funcionario,
                        cliente_local,
                        tipo_servico,
                        status,
                        descricao,
                        problemas,
                        observacoes,
                        data_servico,
                        criado_em,
                        indexado_em,
                        erro_indexacao,
                        modelo_embedding,
                        hash_conteudo_rag
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        registro.funcionario,
                        registro.cliente_local,
                        registro.tipo_servico,
                        registro.status,
                        registro.descricao,
                        registro.problemas,
                        registro.observacoes,
                        registro.data_servico.isoformat(),
                        criado_em.isoformat(),
                        registro.indexado_em.isoformat() if registro.indexado_em else None,
                        registro.erro_indexacao,
                        registro.modelo_embedding,
                        registro.hash_conteudo_rag,
                    ),
                )

        return RegistroServico(
            id=cursor.lastrowid,
            funcionario=registro.funcionario,
            cliente_local=registro.cliente_local,
            tipo_servico=registro.tipo_servico,
            status=registro.status,
            descricao=registro.descricao,
            problemas=registro.problemas,
            observacoes=registro.observacoes,
            data_servico=registro.data_servico,
            criado_em=criado_em,
            indexado_em=registro.indexado_em,
            erro_indexacao=registro.erro_indexacao,
            modelo_embedding=registro.modelo_embedding,
            hash_conteudo_rag=registro.hash_conteudo_rag,
        )

    def listar(self) -> list[RegistroServico]:
        with closing(self._banco.conectar()) as conexao:
            linhas = conexao.execute(
                """
                select
                    id,
                    funcionario,
                    cliente_local,
                    tipo_servico,
                    status,
                    descricao,
                    problemas,
                    observacoes,
                    data_servico,
                    criado_em,
                    indexado_em,
                    erro_indexacao,
                    modelo_embedding,
                    hash_conteudo_rag
                from registros_servico
                order by datetime(criado_em) desc
                """
            ).fetchall()

        return [self._mapear_linha(linha) for linha in linhas]

    def buscar_por_id(self, id_registro: int) -> RegistroServico | None:
        with closing(self._banco.conectar()) as conexao:
            linha = conexao.execute(
                """
                select
                    id,
                    funcionario,
                    cliente_local,
                    tipo_servico,
                    status,
                    descricao,
                    problemas,
                    observacoes,
                    data_servico,
                    criado_em,
                    indexado_em,
                    erro_indexacao,
                    modelo_embedding,
                    hash_conteudo_rag
                from registros_servico
                where id = ?
                """,
                (id_registro,),
            ).fetchone()

        if linha is None:
            return None
        return self._mapear_linha(linha)

    def listar_pendentes_indexacao(self, modelo_embedding: str | None = None) -> list[RegistroServico]:
        registros = self.listar()
        return [
            registro
            for registro in registros
            if self._precisa_indexar(registro, modelo_embedding)
        ]

    def marcar_indexado(
        self,
        id_registro: int,
        modelo_embedding: str,
        hash_conteudo_rag: str,
    ) -> RegistroServico:
        indexado_em = datetime.now(timezone.utc)

        with closing(self._banco.conectar()) as conexao:
            with conexao:
                cursor = conexao.execute(
                    """
                    update registros_servico
                    set
                        indexado_em = ?,
                        erro_indexacao = null,
                        modelo_embedding = ?,
                        hash_conteudo_rag = ?
                    where id = ?
                    """,
                    (indexado_em.isoformat(), modelo_embedding, hash_conteudo_rag, id_registro),
                )

        if cursor.rowcount == 0:
            raise ValueError(f"Registro {id_registro} nao encontrado para marcar indexacao.")
        return self._obter_registro_existente(id_registro)

    def marcar_erro_indexacao(
        self,
        id_registro: int,
        erro: str,
        modelo_embedding: str,
        hash_conteudo_rag: str,
    ) -> RegistroServico:
        with closing(self._banco.conectar()) as conexao:
            with conexao:
                cursor = conexao.execute(
                    """
                    update registros_servico
                    set
                        indexado_em = null,
                        erro_indexacao = ?,
                        modelo_embedding = ?,
                        hash_conteudo_rag = ?
                    where id = ?
                    """,
                    (erro, modelo_embedding, hash_conteudo_rag, id_registro),
                )

        if cursor.rowcount == 0:
            raise ValueError(f"Registro {id_registro} nao encontrado para marcar erro de indexacao.")
        return self._obter_registro_existente(id_registro)

    def _mapear_linha(self, linha: Row) -> RegistroServico:
        return RegistroServico(
            id=linha["id"],
            funcionario=linha["funcionario"],
            cliente_local=linha["cliente_local"],
            tipo_servico=linha["tipo_servico"],
            status=linha["status"],
            descricao=linha["descricao"],
            problemas=linha["problemas"],
            observacoes=linha["observacoes"],
            data_servico=date.fromisoformat(linha["data_servico"]),
            criado_em=datetime.fromisoformat(linha["criado_em"]),
            indexado_em=_parse_datetime_opcional(linha["indexado_em"]),
            erro_indexacao=linha["erro_indexacao"],
            modelo_embedding=linha["modelo_embedding"],
            hash_conteudo_rag=linha["hash_conteudo_rag"],
        )

    def _obter_registro_existente(self, id_registro: int) -> RegistroServico:
        registro = self.buscar_por_id(id_registro)
        if registro is None:
            raise ValueError(f"Registro {id_registro} nao encontrado.")
        return registro

    def _precisa_indexar(self, registro: RegistroServico, modelo_embedding: str | None) -> bool:
        if registro.indexado_em is None:
            return True
        if registro.erro_indexacao:
            return True
        if registro.hash_conteudo_rag != registro.calcular_hash_conteudo_rag():
            return True
        return modelo_embedding is not None and registro.modelo_embedding != modelo_embedding


def _parse_datetime_opcional(valor: str | None) -> datetime | None:
    if not valor:
        return None
    return datetime.fromisoformat(valor)
