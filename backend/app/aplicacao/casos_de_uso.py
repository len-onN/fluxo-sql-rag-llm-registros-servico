from dataclasses import dataclass, field

from app.dominio.entidades import RegistroServico
from app.dominio.portas import RepositorioRegistros, RepositorioVetorial, ServicoEmbeddings, ServicoLLM


@dataclass(slots=True)
class ResultadoCriacao:
    registro: RegistroServico
    indexado: bool
    aviso: str | None = None


@dataclass(slots=True)
class ResultadoConsulta:
    resposta: str
    contextos: list[str]
    aviso: str | None = None


@dataclass(slots=True)
class ResultadoReindexacao:
    total_pendentes: int
    indexados: int
    erros: int
    avisos: list[str] = field(default_factory=list)


class CriarRegistroServico:
    def __init__(
        self,
        repositorio_registros: RepositorioRegistros,
        repositorio_vetorial: RepositorioVetorial,
        servico_embeddings: ServicoEmbeddings,
        modelo_embedding: str = "desconhecido",
    ) -> None:
        self._repositorio_registros = repositorio_registros
        self._repositorio_vetorial = repositorio_vetorial
        self._servico_embeddings = servico_embeddings
        self._modelo_embedding = modelo_embedding

    def executar(self, registro: RegistroServico) -> ResultadoCriacao:
        registro_salvo = self._repositorio_registros.salvar(registro)
        hash_conteudo_rag = registro_salvo.calcular_hash_conteudo_rag()
        id_registro = _exigir_id_registro(registro_salvo)

        try:
            embedding = self._servico_embeddings.gerar_embedding(registro_salvo.texto_para_rag())
            self._repositorio_vetorial.indexar(registro_salvo, embedding)
            registro_indexado = self._repositorio_registros.marcar_indexado(
                id_registro=id_registro,
                modelo_embedding=self._modelo_embedding,
                hash_conteudo_rag=hash_conteudo_rag,
            )
            return ResultadoCriacao(registro=registro_indexado, indexado=True)
        except Exception as erro:
            registro_com_erro = self._repositorio_registros.marcar_erro_indexacao(
                id_registro=id_registro,
                erro=str(erro),
                modelo_embedding=self._modelo_embedding,
                hash_conteudo_rag=hash_conteudo_rag,
            )
            return ResultadoCriacao(
                registro=registro_com_erro,
                indexado=False,
                aviso=f"Registro salvo no SQL, mas ainda nao indexado: {erro}",
            )


class ListarRegistrosServico:
    def __init__(self, repositorio_registros: RepositorioRegistros) -> None:
        self._repositorio_registros = repositorio_registros

    def executar(self) -> list[RegistroServico]:
        return self._repositorio_registros.listar()


class ReindexarRegistrosPendentes:
    def __init__(
        self,
        repositorio_registros: RepositorioRegistros,
        repositorio_vetorial: RepositorioVetorial,
        servico_embeddings: ServicoEmbeddings,
        modelo_embedding: str = "desconhecido",
    ) -> None:
        self._repositorio_registros = repositorio_registros
        self._repositorio_vetorial = repositorio_vetorial
        self._servico_embeddings = servico_embeddings
        self._modelo_embedding = modelo_embedding

    def executar(self) -> ResultadoReindexacao:
        pendentes = self._repositorio_registros.listar_pendentes_indexacao(self._modelo_embedding)
        indexados = 0
        erros = 0
        avisos: list[str] = []

        for registro in pendentes:
            id_registro = _exigir_id_registro(registro)
            hash_conteudo_rag = registro.calcular_hash_conteudo_rag()

            try:
                embedding = self._servico_embeddings.gerar_embedding(registro.texto_para_rag())
                self._repositorio_vetorial.indexar(registro, embedding)
                self._repositorio_registros.marcar_indexado(
                    id_registro=id_registro,
                    modelo_embedding=self._modelo_embedding,
                    hash_conteudo_rag=hash_conteudo_rag,
                )
                indexados += 1
            except Exception as erro:
                self._repositorio_registros.marcar_erro_indexacao(
                    id_registro=id_registro,
                    erro=str(erro),
                    modelo_embedding=self._modelo_embedding,
                    hash_conteudo_rag=hash_conteudo_rag,
                )
                erros += 1
                avisos.append(f"Registro {id_registro} nao indexado: {erro}")

        return ResultadoReindexacao(
            total_pendentes=len(pendentes),
            indexados=indexados,
            erros=erros,
            avisos=avisos,
        )


class ConsultarRegistros:
    def __init__(
        self,
        repositorio_vetorial: RepositorioVetorial,
        servico_embeddings: ServicoEmbeddings,
        servico_llm: ServicoLLM,
    ) -> None:
        self._repositorio_vetorial = repositorio_vetorial
        self._servico_embeddings = servico_embeddings
        self._servico_llm = servico_llm

    def executar(self, pergunta: str, limite: int) -> ResultadoConsulta:
        try:
            embedding = self._servico_embeddings.gerar_embedding(pergunta)
            contextos_rag = self._repositorio_vetorial.buscar_similares(embedding, limite)
            contextos = [contexto.documento for contexto in contextos_rag]
            resposta = self._servico_llm.responder(pergunta, contextos)
            return ResultadoConsulta(resposta=resposta, contextos=contextos)
        except Exception as erro:
            return ResultadoConsulta(
                resposta="Nao foi possivel consultar a base RAG neste momento.",
                contextos=[],
                aviso=str(erro),
            )


def _exigir_id_registro(registro: RegistroServico) -> int:
    if registro.id is None:
        raise ValueError("Registro precisa estar salvo antes da indexacao.")
    return registro.id
