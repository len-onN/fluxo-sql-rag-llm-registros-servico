from dataclasses import dataclass

from app.aplicacao.casos_de_uso import (
    CriarRegistroServico,
    ConsultarRegistros,
    ListarRegistrosServico,
    ReindexarRegistrosPendentes,
)
from app.dominio.portas import CatalogoModelos, GeradorEmbeddings, GeradorResposta, SeletorModelo
from app.infraestrutura.banco_sqlite import BancoSQLite
from app.infraestrutura.provedores_llm.lm_studio import (
    CatalogoModelosLMStudio,
    ClienteLMStudio,
    GeradorEmbeddingsLMStudio,
    GeradorRespostaLMStudio,
    ParserRespostaLMStudio,
    PoliticaFallbackRespostaLMStudio,
    ResolvedorModeloChatLMStudio,
    SeletorModeloLMStudio,
)
from app.infraestrutura.repositorio_sqlite_registros import RepositorioSQLiteRegistros
from app.infraestrutura.repositorio_vetorial_chroma import RepositorioVetorialChroma
from app.nucleo.configuracoes import Configuracoes


@dataclass(slots=True)
class ContainerAplicacao:
    criar_registro_servico: CriarRegistroServico
    listar_registros_servico: ListarRegistrosServico
    reindexar_registros_pendentes: ReindexarRegistrosPendentes
    consultar_registros: ConsultarRegistros
    gerador_embeddings: GeradorEmbeddings
    gerador_resposta: GeradorResposta
    catalogo_modelos: CatalogoModelos
    seletor_modelo: SeletorModelo


def criar_container(configuracoes: Configuracoes) -> ContainerAplicacao:
    banco = BancoSQLite(configuracoes.banco_sqlite)
    repositorio_registros = RepositorioSQLiteRegistros(banco)
    repositorio_vetorial = RepositorioVetorialChroma(configuracoes.diretorio_chroma)
    cliente_lm_studio = ClienteLMStudio(configuracoes.lm_studio_base_url)
    resolvedor_modelo_chat = ResolvedorModeloChatLMStudio()
    catalogo_modelos = CatalogoModelosLMStudio(cliente_lm_studio, resolvedor_modelo_chat)
    seletor_modelo = SeletorModeloLMStudio(catalogo_modelos, resolvedor_modelo_chat)
    gerador_embeddings = GeradorEmbeddingsLMStudio(cliente_lm_studio, configuracoes.modelo_embedding)
    gerador_resposta = GeradorRespostaLMStudio(
        cliente=cliente_lm_studio,
        catalogo_modelos=catalogo_modelos,
        resolvedor_modelo=resolvedor_modelo_chat,
        parser_resposta=ParserRespostaLMStudio(),
        politica_fallback=PoliticaFallbackRespostaLMStudio(),
        max_tokens_resposta=configuracoes.max_tokens_resposta,
    )

    return ContainerAplicacao(
        criar_registro_servico=CriarRegistroServico(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            modelo_embedding=configuracoes.modelo_embedding,
        ),
        listar_registros_servico=ListarRegistrosServico(repositorio_registros),
        reindexar_registros_pendentes=ReindexarRegistrosPendentes(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            modelo_embedding=configuracoes.modelo_embedding,
        ),
        consultar_registros=ConsultarRegistros(
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=gerador_embeddings,
            gerador_resposta=gerador_resposta,
        ),
        gerador_embeddings=gerador_embeddings,
        gerador_resposta=gerador_resposta,
        catalogo_modelos=catalogo_modelos,
        seletor_modelo=seletor_modelo,
    )
