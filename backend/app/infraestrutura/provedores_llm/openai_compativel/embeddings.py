from app.dominio.objetos_valor import RespostaEmbedding, SolicitacaoEmbedding
from app.nucleo.erros import RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteOpenAICompativel


class GeradorEmbeddingsOpenAICompativel:
    def __init__(self, cliente: ClienteOpenAICompativel, modelo_embedding: str) -> None:
        self._cliente = cliente
        self._modelo_embedding = modelo_embedding

    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        modelo = solicitacao.modelo or self._modelo_embedding
        dados = self._cliente.postar_json(
            "/embeddings",
            json={"model": modelo, "input": solicitacao.texto},
            timeout=60,
            modelo=modelo,
        )

        try:
            vetor = dados["data"][0]["embedding"]
            return RespostaEmbedding(vetor=vetor, modelo=modelo)
        except (KeyError, IndexError, TypeError, ValueError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de embeddings OpenAI-compatible nao possui vetor esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
