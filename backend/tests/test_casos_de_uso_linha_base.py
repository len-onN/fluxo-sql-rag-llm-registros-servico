import sqlite3
import sys
import unittest
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.aplicacao.casos_de_uso import CriarRegistroServico, ConsultarRegistros, ReindexarRegistrosPendentes
from app.aplicacao.servicos import PoliticaContextoRAG
from app.dominio.entidades import RegistroServico
from app.dominio.objetos_valor import (
    ContextoRAG,
    EstadoIndexacao,
    RespostaEmbedding,
    RespostaLLM,
    SolicitacaoEmbedding,
    SolicitacaoLLM,
)
from app.infraestrutura.banco_sqlite import BancoSQLite
from app.infraestrutura.repositorio_sqlite_registros import RepositorioSQLiteRegistros
from app.infraestrutura.repositorio_vetorial_chroma import RepositorioVetorialChroma
from app.nucleo.erros import ErroProvedor, ModeloNaoEncontrado


def criar_registro() -> RegistroServico:
    return RegistroServico(
        funcionario="Ana Silva",
        cliente_local="Cliente Centro",
        tipo_servico="Manutencao preventiva",
        status="Concluido",
        descricao="Verificacao geral dos equipamentos de rede.",
        problemas="Sem falhas criticas.",
        observacoes="Retornar em 30 dias.",
        data_servico=date(2026, 6, 18),
    )


class RepositorioRegistrosFake:
    def __init__(self, eventos: list[str]) -> None:
        self.eventos = eventos
        self.registros: list[RegistroServico] = []

    def salvar(self, registro: RegistroServico) -> RegistroServico:
        self.eventos.append("salvar_sql")
        registro_salvo = registro.com_id(len(self.registros) + 1)
        self.registros.append(registro_salvo)
        return registro_salvo

    def listar(self) -> list[RegistroServico]:
        return list(self.registros)

    def buscar_por_id(self, id_registro: int) -> RegistroServico | None:
        for registro in self.registros:
            if registro.id == id_registro:
                return registro
        return None

    def listar_pendentes_indexacao(self, modelo_embedding: str | None = None) -> list[RegistroServico]:
        self.eventos.append("listar_pendentes_sql")
        return [
            registro
            for registro in self.registros
            if registro.indexado_em is None
            or registro.erro_indexacao
            or registro.hash_conteudo_rag != registro.calcular_hash_conteudo_rag()
            or (modelo_embedding is not None and registro.modelo_embedding != modelo_embedding)
        ]

    def marcar_indexado(
        self,
        id_registro: int,
        modelo_embedding: str,
        hash_conteudo_rag: str,
    ) -> RegistroServico:
        self.eventos.append("marcar_indexado_sql")
        registro = self._obter_registro(id_registro)
        atualizado = replace(
            registro,
            indexado_em=datetime.now(timezone.utc),
            erro_indexacao=None,
            modelo_embedding=modelo_embedding,
            hash_conteudo_rag=hash_conteudo_rag,
        )
        self._substituir(atualizado)
        return atualizado

    def marcar_erro_indexacao(
        self,
        id_registro: int,
        erro: str,
        modelo_embedding: str,
        hash_conteudo_rag: str,
    ) -> RegistroServico:
        self.eventos.append("marcar_erro_indexacao_sql")
        registro = self._obter_registro(id_registro)
        atualizado = replace(
            registro,
            indexado_em=None,
            erro_indexacao=erro,
            modelo_embedding=modelo_embedding,
            hash_conteudo_rag=hash_conteudo_rag,
        )
        self._substituir(atualizado)
        return atualizado

    def _obter_registro(self, id_registro: int) -> RegistroServico:
        registro = self.buscar_por_id(id_registro)
        if registro is None:
            raise ValueError(f"Registro {id_registro} nao encontrado.")
        return registro

    def _substituir(self, registro_atualizado: RegistroServico) -> None:
        self.registros = [
            registro_atualizado if registro.id == registro_atualizado.id else registro
            for registro in self.registros
        ]


class RepositorioVetorialFake:
    def __init__(self, eventos: list[str], contextos: list[ContextoRAG] | None = None) -> None:
        self.eventos = eventos
        self.contextos = contextos or []
        self.indexados: list[tuple[RegistroServico, RespostaEmbedding]] = []
        self.buscas: list[tuple[RespostaEmbedding, int]] = []

    def indexar(self, registro: RegistroServico, embedding: RespostaEmbedding) -> None:
        self.eventos.append("indexar_chroma")
        self.indexados.append((registro, embedding))

    def buscar_similares(self, embedding: RespostaEmbedding, limite: int) -> list[ContextoRAG]:
        self.eventos.append("buscar_chroma")
        self.buscas.append((embedding, limite))
        return list(self.contextos)


class GeradorEmbeddingsFake:
    def __init__(self, eventos: list[str], falhar: bool = False) -> None:
        self.eventos = eventos
        self.falhar = falhar
        self.textos: list[str] = []

    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        self.eventos.append("gerar_embedding")
        self.textos.append(solicitacao.texto)
        if self.falhar:
            raise RuntimeError("LM Studio indisponivel")
        return RespostaEmbedding(vetor=(0.1, 0.2, 0.3), modelo=solicitacao.modelo)


class GeradorRespostaFake:
    def __init__(self, eventos: list[str]) -> None:
        self.eventos = eventos
        self.chamadas: list[tuple[str, list[str]]] = []
        self.prompts: list[str | None] = []

    def responder(self, solicitacao: SolicitacaoLLM) -> RespostaLLM:
        self.eventos.append("responder_llm")
        self.chamadas.append((solicitacao.pergunta, list(solicitacao.contextos)))
        self.prompts.append(solicitacao.prompt_usuario)
        return RespostaLLM(texto="Resposta baseada nos registros recuperados.")


class ColecaoChromaFake:
    def __init__(self) -> None:
        self.consultas: list[dict] = []

    def query(self, **argumentos: object) -> dict:
        self.consultas.append(argumentos)
        return {
            "ids": [["42"]],
            "documents": [["Funcionario: Ana Silva\nCliente ou local: Cliente Centro"]],
            "metadatas": [
                [
                    {
                        "id_registro": 42,
                        "cliente_local": "Cliente Centro",
                        "ativo": True,
                        "ignorado": None,
                    }
                ]
            ],
            "distances": [[0.25]],
        }


class ContratosLLMTest(unittest.TestCase):
    def test_resposta_embedding_normaliza_vetor_e_expoe_dimensoes(self) -> None:
        resposta = RespostaEmbedding(vetor=[1, 2.5, "3"])

        self.assertEqual(resposta.vetor, (1.0, 2.5, 3.0))
        self.assertEqual(resposta.como_lista(), [1.0, 2.5, 3.0])
        self.assertEqual(resposta.dimensoes, 3)


class ErrosProvedorTest(unittest.TestCase):
    def test_erro_tipado_preserva_contexto_do_provedor(self) -> None:
        erro = ModeloNaoEncontrado("Modelo ausente.", provedor="lm_studio", modelo="modelo-b")

        self.assertIsInstance(erro, ErroProvedor)
        self.assertEqual(str(erro), "Modelo ausente.")
        self.assertEqual(erro.provedor, "lm_studio")
        self.assertEqual(erro.modelo, "modelo-b")


class RegistroServicoLinhaBaseTest(unittest.TestCase):
    def test_texto_para_rag_preserva_campos_publicos_do_contexto(self) -> None:
        registro = criar_registro()

        self.assertEqual(
            registro.texto_para_rag(),
            "\n".join(
                [
                    "Funcionario: Ana Silva",
                    "Cliente ou local: Cliente Centro",
                    "Data do servico: 2026-06-18",
                    "Tipo de servico: Manutencao preventiva",
                    "Status: Concluido",
                    "Descricao: Verificacao geral dos equipamentos de rede.",
                    "Problemas encontrados: Sem falhas criticas.",
                    "Observacoes importantes: Retornar em 30 dias.",
                ]
            ),
        )

    def test_criacao_salva_no_sql_antes_de_indexar_no_chroma(self) -> None:
        eventos: list[str] = []
        repositorio_registros = RepositorioRegistrosFake(eventos)
        repositorio_vetorial = RepositorioVetorialFake(eventos)
        gerador_embeddings = GeradorEmbeddingsFake(eventos)
        caso_de_uso = CriarRegistroServico(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            modelo_embedding="modelo-teste",
        )

        resultado = caso_de_uso.executar(criar_registro())

        self.assertTrue(resultado.indexado)
        self.assertIsNone(resultado.aviso)
        self.assertEqual(eventos, ["salvar_sql", "gerar_embedding", "indexar_chroma", "marcar_indexado_sql"])
        self.assertEqual(resultado.registro.id, 1)
        self.assertEqual(resultado.registro.estado_indexacao, EstadoIndexacao.INDEXADO)
        self.assertIsNotNone(resultado.registro.indexado_em)
        self.assertIsNone(resultado.registro.erro_indexacao)
        self.assertEqual(resultado.registro.modelo_embedding, "modelo-teste")
        self.assertEqual(resultado.registro.hash_conteudo_rag, resultado.registro.calcular_hash_conteudo_rag())
        self.assertEqual(repositorio_vetorial.indexados[0][0].id, 1)

    def test_criacao_mantem_registro_sql_quando_embedding_falha(self) -> None:
        eventos: list[str] = []
        repositorio_registros = RepositorioRegistrosFake(eventos)
        repositorio_vetorial = RepositorioVetorialFake(eventos)
        gerador_embeddings = GeradorEmbeddingsFake(eventos, falhar=True)
        caso_de_uso = CriarRegistroServico(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            modelo_embedding="modelo-teste",
        )

        resultado = caso_de_uso.executar(criar_registro())

        self.assertFalse(resultado.indexado)
        self.assertIn("Registro salvo no SQL", resultado.aviso or "")
        self.assertEqual(eventos, ["salvar_sql", "gerar_embedding", "marcar_erro_indexacao_sql"])
        self.assertEqual(len(repositorio_registros.registros), 1)
        self.assertEqual(resultado.registro.estado_indexacao, EstadoIndexacao.ERRO)
        self.assertIn("LM Studio indisponivel", resultado.registro.erro_indexacao or "")
        self.assertEqual(resultado.registro.modelo_embedding, "modelo-teste")
        self.assertEqual(resultado.registro.hash_conteudo_rag, resultado.registro.calcular_hash_conteudo_rag())
        self.assertEqual(repositorio_vetorial.indexados, [])


class ReindexarRegistrosPendentesTest(unittest.TestCase):
    def test_reindexacao_processa_pendentes_e_marca_sucesso(self) -> None:
        eventos: list[str] = []
        repositorio_registros = RepositorioRegistrosFake(eventos)
        registro_pendente = criar_registro().com_id(1)
        repositorio_registros.registros.append(registro_pendente)
        repositorio_vetorial = RepositorioVetorialFake(eventos)
        gerador_embeddings = GeradorEmbeddingsFake(eventos)
        caso_de_uso = ReindexarRegistrosPendentes(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            modelo_embedding="modelo-teste",
        )

        resultado = caso_de_uso.executar()

        self.assertEqual(
            eventos,
            ["listar_pendentes_sql", "gerar_embedding", "indexar_chroma", "marcar_indexado_sql"],
        )
        self.assertEqual(resultado.total_pendentes, 1)
        self.assertEqual(resultado.indexados, 1)
        self.assertEqual(resultado.erros, 0)
        self.assertEqual(resultado.modelo_embedding, "modelo-teste")
        self.assertEqual(resultado.ids_indexados, [1])
        self.assertEqual(resultado.ids_com_erro, [])
        self.assertEqual(resultado.avisos, [])
        self.assertEqual(repositorio_registros.registros[0].estado_indexacao, EstadoIndexacao.INDEXADO)

    def test_reindexacao_marca_erro_e_continua_controlada(self) -> None:
        eventos: list[str] = []
        repositorio_registros = RepositorioRegistrosFake(eventos)
        repositorio_registros.registros.append(criar_registro().com_id(1))
        caso_de_uso = ReindexarRegistrosPendentes(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=RepositorioVetorialFake(eventos),
            gerador_embeddings=GeradorEmbeddingsFake(eventos, falhar=True),
            modelo_embedding="modelo-teste",
        )

        resultado = caso_de_uso.executar()

        self.assertEqual(eventos, ["listar_pendentes_sql", "gerar_embedding", "marcar_erro_indexacao_sql"])
        self.assertEqual(resultado.total_pendentes, 1)
        self.assertEqual(resultado.indexados, 0)
        self.assertEqual(resultado.erros, 1)
        self.assertEqual(resultado.modelo_embedding, "modelo-teste")
        self.assertEqual(resultado.ids_indexados, [])
        self.assertEqual(resultado.ids_com_erro, [1])
        self.assertIn("Registro 1 nao indexado", resultado.avisos[0])
        self.assertEqual(repositorio_registros.registros[0].estado_indexacao, EstadoIndexacao.ERRO)


class RepositorioSQLiteIndexacaoTest(unittest.TestCase):
    def test_migracao_adiciona_colunas_de_indexacao_em_banco_existente(self) -> None:
        with TemporaryDirectory() as diretorio:
            caminho_banco = Path(diretorio) / "registros.db"
            with closing(sqlite3.connect(caminho_banco)) as conexao:
                with conexao:
                    conexao.execute(
                        """
                        create table registros_servico (
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

            BancoSQLite(str(caminho_banco))
            BancoSQLite(str(caminho_banco))

            with closing(sqlite3.connect(caminho_banco)) as conexao:
                colunas = {linha[1] for linha in conexao.execute("pragma table_info(registros_servico)")}
                indices = {linha[1] for linha in conexao.execute("pragma index_list(registros_servico)")}

        self.assertIn("indexado_em", colunas)
        self.assertIn("erro_indexacao", colunas)
        self.assertIn("modelo_embedding", colunas)
        self.assertIn("hash_conteudo_rag", colunas)
        self.assertIn("idx_registros_servico_criado_em", indices)
        self.assertIn("idx_registros_servico_indexacao_estado", indices)
        self.assertIn("idx_registros_servico_indexacao_hash", indices)

    def test_repositorio_marca_indexacao_e_lista_pendentes(self) -> None:
        with TemporaryDirectory() as diretorio:
            repositorio = RepositorioSQLiteRegistros(BancoSQLite(str(Path(diretorio) / "registros.db")))
            registro = repositorio.salvar(criar_registro())
            id_registro = registro.id or 0
            hash_conteudo = registro.calcular_hash_conteudo_rag()

            self.assertEqual(registro.estado_indexacao, EstadoIndexacao.PENDENTE)
            self.assertEqual([pendente.id for pendente in repositorio.listar_pendentes_indexacao("modelo-teste")], [1])

            com_erro = repositorio.marcar_erro_indexacao(
                id_registro=id_registro,
                erro="LM Studio indisponivel",
                modelo_embedding="modelo-teste",
                hash_conteudo_rag=hash_conteudo,
            )

            self.assertEqual(com_erro.estado_indexacao, EstadoIndexacao.ERRO)
            self.assertEqual([pendente.id for pendente in repositorio.listar_pendentes_indexacao("modelo-teste")], [1])

            indexado = repositorio.marcar_indexado(
                id_registro=id_registro,
                modelo_embedding="modelo-teste",
                hash_conteudo_rag=hash_conteudo,
            )

            self.assertEqual(indexado.estado_indexacao, EstadoIndexacao.INDEXADO)
            self.assertEqual(repositorio.listar_pendentes_indexacao("modelo-teste"), [])
            self.assertEqual([pendente.id for pendente in repositorio.listar_pendentes_indexacao("outro-modelo")], [1])

    def test_repositorio_filtra_pendentes_sem_usar_listagem_completa(self) -> None:
        with TemporaryDirectory() as diretorio:
            caminho_banco = Path(diretorio) / "registros.db"
            repositorio = RepositorioSQLiteRegistros(BancoSQLite(str(caminho_banco)))
            registro = repositorio.salvar(criar_registro())
            id_registro = registro.id or 0
            repositorio.marcar_indexado(
                id_registro=id_registro,
                modelo_embedding="modelo-teste",
                hash_conteudo_rag=registro.calcular_hash_conteudo_rag(),
            )

            with closing(sqlite3.connect(caminho_banco)) as conexao:
                with conexao:
                    conexao.execute(
                        "update registros_servico set descricao = ? where id = ?",
                        ("Descricao alterada depois da indexacao.", id_registro),
                    )

            def falhar_listar() -> list[RegistroServico]:
                raise AssertionError("listar() nao deve ser chamado para encontrar pendentes.")

            repositorio.listar = falhar_listar  # type: ignore[method-assign]

            self.assertEqual([pendente.id for pendente in repositorio.listar_pendentes_indexacao("modelo-teste")], [1])


class ConsultarRegistrosLinhaBaseTest(unittest.TestCase):
    def test_consulta_usa_embedding_busca_vetorial_e_llm_em_ordem(self) -> None:
        eventos: list[str] = []
        contexto_textual = "Funcionario: Ana Silva\nCliente ou local: Cliente Centro"
        contextos_rag = [
            ContextoRAG(
                id_registro=1,
                documento=contexto_textual,
                metadados={"cliente_local": "Cliente Centro"},
                fonte="fake",
            )
        ]
        repositorio_vetorial = RepositorioVetorialFake(eventos, contextos=contextos_rag)
        gerador_embeddings = GeradorEmbeddingsFake(eventos)
        gerador_resposta = GeradorRespostaFake(eventos)
        caso_de_uso = ConsultarRegistros(
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            gerador_resposta=gerador_resposta,
        )

        resultado = caso_de_uso.executar("Quais servicos foram concluidos?", limite=3)

        self.assertEqual(eventos, ["gerar_embedding", "buscar_chroma", "responder_llm"])
        self.assertEqual(len(repositorio_vetorial.buscas), 1)
        self.assertEqual(repositorio_vetorial.buscas[0][0].como_lista(), [0.1, 0.2, 0.3])
        self.assertEqual(repositorio_vetorial.buscas[0][1], 3)
        self.assertEqual(gerador_resposta.chamadas, [("Quais servicos foram concluidos?", [contexto_textual])])
        self.assertEqual(
            gerador_resposta.prompts,
            [f"Contexto:\n{contexto_textual}\n\nPergunta:\nQuais servicos foram concluidos?"],
        )
        self.assertEqual(resultado.contextos, [contexto_textual])
        self.assertEqual(
            resultado.fontes,
            [
                {
                    "id_registro": 1,
                    "fonte": "fake",
                    "metadados": {"cliente_local": "Cliente Centro"},
                    "distancia": None,
                    "pontuacao": None,
                }
            ],
        )
        self.assertEqual(resultado.resposta, "Resposta baseada nos registros recuperados.")
        self.assertIsNone(resultado.aviso)

    def test_consulta_aplica_politica_de_contexto_antes_da_llm(self) -> None:
        eventos: list[str] = []
        contextos_rag = [
            ContextoRAG(id_registro=1, documento="Contexto forte", distancia=0.2, fonte="fake"),
            ContextoRAG(id_registro=2, documento="Contexto fraco", distancia=0.9, fonte="fake"),
        ]
        repositorio_vetorial = RepositorioVetorialFake(eventos, contextos=contextos_rag)
        gerador_resposta = GeradorRespostaFake(eventos)
        caso_de_uso = ConsultarRegistros(
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=GeradorEmbeddingsFake(eventos),
            gerador_resposta=gerador_resposta,
            politica_contexto=PoliticaContextoRAG(distancia_maxima=0.5),
        )

        resultado = caso_de_uso.executar("Qual contexto entra?", limite=5)

        self.assertEqual(repositorio_vetorial.buscas[0][1], 5)
        self.assertEqual(gerador_resposta.chamadas, [("Qual contexto entra?", ["Contexto forte"])])
        self.assertEqual(resultado.contextos, ["Contexto forte"])
        self.assertEqual(resultado.fontes[0]["id_registro"], 1)

    def test_consulta_retorna_aviso_quando_fluxo_rag_falha(self) -> None:
        eventos: list[str] = []
        caso_de_uso = ConsultarRegistros(
            repositorio_vetorial=RepositorioVetorialFake(eventos),
            gerador_embeddings=GeradorEmbeddingsFake(eventos, falhar=True),
            gerador_resposta=GeradorRespostaFake(eventos),
        )

        resultado = caso_de_uso.executar("Quais registros existem?", limite=3)

        self.assertEqual(resultado.resposta, "Nao foi possivel consultar a base RAG neste momento.")
        self.assertEqual(resultado.contextos, [])
        self.assertIn("LM Studio indisponivel", resultado.aviso or "")


class RepositorioVetorialChromaLinhaBaseTest(unittest.TestCase):
    def test_busca_similar_retorna_contexto_rag_estruturado(self) -> None:
        colecao = ColecaoChromaFake()
        repositorio = object.__new__(RepositorioVetorialChroma)
        repositorio._colecao = colecao

        contextos = repositorio.buscar_similares(RespostaEmbedding(vetor=(0.1, 0.2, 0.3)), limite=2)

        self.assertEqual(
            colecao.consultas,
            [
                {
                    "query_embeddings": [[0.1, 0.2, 0.3]],
                    "n_results": 2,
                    "include": ["documents", "metadatas", "distances"],
                }
            ],
        )
        self.assertEqual(len(contextos), 1)
        self.assertEqual(contextos[0].id_registro, 42)
        self.assertEqual(contextos[0].documento, "Funcionario: Ana Silva\nCliente ou local: Cliente Centro")
        self.assertEqual(contextos[0].distancia, 0.25)
        self.assertEqual(contextos[0].fonte, "chroma:registros_servico")
        self.assertEqual(
            contextos[0].metadados,
            {
                "id_registro": 42,
                "cliente_local": "Cliente Centro",
                "ativo": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
