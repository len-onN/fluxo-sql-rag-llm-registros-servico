from dataclasses import dataclass

from app.aplicacao.casos_de_uso import (
    CriarRegistroServico,
    ConsultarRegistros,
    ListarRegistrosServico,
    ReindexarRegistrosPendentes,
)
from app.infraestrutura.banco_sqlite import BancoSQLite
from app.infraestrutura.repositorio_sqlite_registros import RepositorioSQLiteRegistros
from app.infraestrutura.repositorio_vetorial_chroma import RepositorioVetorialChroma
from app.infraestrutura.servico_lm_studio import ServicoLMStudio
from app.nucleo.configuracoes import Configuracoes


@dataclass(slots=True)
class ContainerAplicacao:
    criar_registro_servico: CriarRegistroServico
    listar_registros_servico: ListarRegistrosServico
    reindexar_registros_pendentes: ReindexarRegistrosPendentes
    consultar_registros: ConsultarRegistros
    servico_lm_studio: ServicoLMStudio


def criar_container(configuracoes: Configuracoes) -> ContainerAplicacao:
    banco = BancoSQLite(configuracoes.banco_sqlite)
    repositorio_registros = RepositorioSQLiteRegistros(banco)
    repositorio_vetorial = RepositorioVetorialChroma(configuracoes.diretorio_chroma)
    servico_lm_studio = ServicoLMStudio(
        base_url=configuracoes.lm_studio_base_url,
        modelo_embedding=configuracoes.modelo_embedding,
        max_tokens_resposta=configuracoes.max_tokens_resposta,
    )

    return ContainerAplicacao(
        criar_registro_servico=CriarRegistroServico(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            servico_embeddings=servico_lm_studio,
            modelo_embedding=configuracoes.modelo_embedding,
        ),
        listar_registros_servico=ListarRegistrosServico(repositorio_registros),
        reindexar_registros_pendentes=ReindexarRegistrosPendentes(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            servico_embeddings=servico_lm_studio,
            modelo_embedding=configuracoes.modelo_embedding,
        ),
        consultar_registros=ConsultarRegistros(
            repositorio_vetorial=repositorio_vetorial,
            servico_embeddings=servico_lm_studio,
            servico_llm=servico_lm_studio,
        ),
        servico_lm_studio=servico_lm_studio,
    )
