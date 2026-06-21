from enum import Enum


class EstadoIndexacao(str, Enum):
    PENDENTE = "pendente"
    INDEXADO = "indexado"
    ERRO = "erro"
