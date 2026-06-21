from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.infraestrutura.container import criar_container
from app.interfaces.http.rotas_consulta import roteador as roteador_consulta
from app.interfaces.http.rotas_modelos import roteador as roteador_modelos
from app.interfaces.http.rotas_registros import roteador as roteador_registros
from app.nucleo.configuracoes import Configuracoes


def criar_aplicacao() -> FastAPI:
    configuracoes = Configuracoes()
    aplicacao = FastAPI(title=configuracoes.nome_aplicacao)
    aplicacao.state.container = criar_container(configuracoes)

    aplicacao.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    aplicacao.include_router(roteador_registros)
    aplicacao.include_router(roteador_consulta)
    aplicacao.include_router(roteador_modelos)

    @aplicacao.get("/api/saude")
    def verificar_saude() -> dict[str, str]:
        return {"status": "ok"}

    caminho_frontend = Path(__file__).resolve().parents[2] / "frontend"
    if caminho_frontend.exists():
        aplicacao.mount("/", StaticFiles(directory=caminho_frontend, html=True), name="frontend")

    return aplicacao


aplicacao_api = criar_aplicacao()
