from dataclasses import dataclass

from app.aplicacao.casos_de_uso import (
    CriarRegistroServico,
    ConsultarRegistros,
    ListarRegistrosServico,
    ReindexarRegistrosPendentes,
)
from app.aplicacao.servicos import MontadorPromptRAG, PoliticaContextoRAG
from app.dominio.portas import CatalogoModelos, GeradorEmbeddings, GeradorResposta, SeletorModelo
from app.infraestrutura.banco_sqlite import BancoSQLite
from app.infraestrutura.provedores_llm import EstadoProvedoresAtivos, criar_componentes_provedores
from app.infraestrutura.repositorio_sqlite_registros import RepositorioSQLiteRegistros
from app.infraestrutura.repositorio_vetorial_chroma import RepositorioVetorialChroma
from app.nucleo.configuracoes import Configuracoes
from app.nucleo.observabilidade import MetadadosConsultaRAG, ObservadorConsultaRAG


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
    estado_provedores: EstadoProvedoresAtivos


def criar_container(configuracoes: Configuracoes) -> ContainerAplicacao:
    banco = BancoSQLite(configuracoes.banco_sqlite)
    repositorio_registros = RepositorioSQLiteRegistros(banco)
    repositorio_vetorial = RepositorioVetorialChroma(configuracoes.diretorio_chroma)
    provedores = criar_componentes_provedores(configuracoes)
    observador_consulta = ObservadorConsultaRAG()
    politica_contexto = PoliticaContextoRAG(
        top_k_padrao=configuracoes.limite_contexto,
        distancia_maxima=configuracoes.limiar_distancia_contexto,
        pontuacao_minima=configuracoes.limiar_pontuacao_contexto,
        orcamento_caracteres=configuracoes.orcamento_contexto_caracteres,
    )
    montador_prompt = MontadorPromptRAG()

    return ContainerAplicacao(
        criar_registro_servico=CriarRegistroServico(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=provedores.gerador_embeddings,
            modelo_embedding=configuracoes.modelo_embedding,
        ),
        listar_registros_servico=ListarRegistrosServico(repositorio_registros),
        reindexar_registros_pendentes=ReindexarRegistrosPendentes(
            repositorio_registros=repositorio_registros,
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=provedores.gerador_embeddings,
            modelo_embedding=configuracoes.modelo_embedding,
        ),
        consultar_registros=ConsultarRegistros(
            repositorio_vetorial=repositorio_vetorial,
            gerador_embeddings=provedores.gerador_embeddings,
            gerador_resposta=provedores.gerador_resposta,
            politica_contexto=politica_contexto,
            montador_prompt=montador_prompt,
            observador=observador_consulta,
            metadados_observabilidade=MetadadosConsultaRAG(
                provedor_chat=provedores.estado.provedor_chat,
                provedor_embeddings=provedores.estado.provedor_embeddings,
                modelo_chat=provedores.estado.modelo_chat,
                modelo_embedding=provedores.estado.modelo_embedding,
            ),
        ),
        gerador_embeddings=provedores.gerador_embeddings,
        gerador_resposta=provedores.gerador_resposta,
        catalogo_modelos=provedores.catalogo_modelos,
        seletor_modelo=provedores.seletor_modelo,
        estado_provedores=provedores.estado,
    )
