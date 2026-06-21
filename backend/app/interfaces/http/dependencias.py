from fastapi import Request

from app.infraestrutura.container import ContainerAplicacao


def obter_container(request: Request) -> ContainerAplicacao:
    return request.app.state.container
