from app.dominio.objetos_valor import RespostaEmbedding, SolicitacaoEmbedding
from app.nucleo.erros import RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteOllama


class GeradorEmbeddingsOllama:
    def __init__(self, cliente: ClienteOllama, modelo_embedding: str) -> None:
        self._cliente = cliente
        self._modelo_embedding = modelo_embedding

    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        modelo = solicitacao.modelo or self._modelo_embedding
        dados = self._cliente.postar_json(
            "/api/embed",
            json={"model": modelo, "input": solicitacao.texto},
            timeout=60,
            modelo=modelo,
            capacidade="embeddings",
        )

        try:
            vetor = dados["embeddings"][0]
            modelo_resposta = str(dados.get("model") or modelo)
            return RespostaEmbedding(vetor=vetor, modelo=modelo_resposta)
        except (KeyError, IndexError, TypeError, ValueError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de embeddings Ollama nao possui vetor esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
