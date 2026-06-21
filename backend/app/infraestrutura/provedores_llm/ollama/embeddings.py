from app.dominio.objetos_valor import RespostaEmbedding, SolicitacaoEmbedding
from app.nucleo.erros import RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteOllama


class GeradorEmbeddingsOllama:
    def __init__(self, cliente: ClienteOllama, modelo_embedding: str) -> None:
        self._cliente = cliente
        self._modelo_embedding = modelo_embedding

    def gerar_embedding(self, solicitacao: SolicitacaoEmbedding) -> RespostaEmbedding:
        return self.gerar_embeddings((solicitacao,))[0]

    def gerar_embeddings(self, solicitacoes: tuple[SolicitacaoEmbedding, ...]) -> tuple[RespostaEmbedding, ...]:
        if not solicitacoes:
            return ()

        modelos = tuple(solicitacao.modelo or self._modelo_embedding for solicitacao in solicitacoes)
        if len(set(modelos)) > 1:
            return tuple(self.gerar_embedding(solicitacao) for solicitacao in solicitacoes)

        modelo = modelos[0]
        entrada: str | list[str]
        if len(solicitacoes) == 1:
            entrada = solicitacoes[0].texto
        else:
            entrada = [solicitacao.texto for solicitacao in solicitacoes]

        dados = self._postar_embeddings(modelo, entrada)
        return self._extrair_respostas(dados, modelo, len(solicitacoes))

    def _postar_embeddings(self, modelo: str, entrada: str | list[str]) -> dict:
        return self._cliente.postar_json(
            "/api/embed",
            json={"model": modelo, "input": entrada},
            timeout=60,
            modelo=modelo,
            capacidade="embeddings",
        )

    def _extrair_respostas(self, dados: dict, modelo: str, quantidade: int) -> tuple[RespostaEmbedding, ...]:
        try:
            vetores = list(dados["embeddings"])
            if len(vetores) != quantidade:
                raise ValueError("Quantidade de embeddings diferente da solicitada.")

            modelo_resposta = str(dados.get("model") or modelo)
            return tuple(RespostaEmbedding(vetor=vetor, modelo=modelo_resposta) for vetor in vetores)
        except (KeyError, IndexError, TypeError, ValueError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de embeddings Ollama nao possui vetor esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
