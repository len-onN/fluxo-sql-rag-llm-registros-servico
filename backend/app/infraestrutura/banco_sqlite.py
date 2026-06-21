import sqlite3
from contextlib import closing
from pathlib import Path


COLUNAS_INDEXACAO = {
    "indexado_em": "text",
    "erro_indexacao": "text",
    "modelo_embedding": "text",
    "hash_conteudo_rag": "text",
}


class BancoSQLite:
    def __init__(self, caminho_banco: str) -> None:
        self._caminho_banco = Path(caminho_banco)
        self._caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self._preparar()

    def conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self._caminho_banco)
        conexao.row_factory = sqlite3.Row
        return conexao

    def _preparar(self) -> None:
        with closing(self.conectar()) as conexao:
            with conexao:
                conexao.execute(
                    """
                    create table if not exists registros_servico (
                        id integer primary key autoincrement,
                        funcionario text not null,
                        cliente_local text not null,
                        tipo_servico text not null,
                        status text not null,
                        descricao text not null,
                        problemas text not null,
                        observacoes text not null,
                        data_servico text not null,
                        criado_em text not null
                    )
                    """
                )
                self._migrar_registros_servico(conexao)

    def _migrar_registros_servico(self, conexao: sqlite3.Connection) -> None:
        colunas_existentes = {
            linha["name"]
            for linha in conexao.execute("pragma table_info(registros_servico)").fetchall()
        }

        for nome_coluna, definicao in COLUNAS_INDEXACAO.items():
            if nome_coluna not in colunas_existentes:
                conexao.execute(f"alter table registros_servico add column {nome_coluna} {definicao}")
