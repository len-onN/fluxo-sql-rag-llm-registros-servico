from app.dominio.objetos_valor import RespostaEmbedding, SolicitacaoEmbedding
from app.nucleo.erros import RespostaInvalidaProvedor

from .cliente import PROVEDOR, ClienteLMStudio


class GeradorEmbeddingsLMStudio:
    def __init__(self, cliente: ClienteLMStudio, modelo_embedding: str) -> None:
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
            self._cliente.url_api("/embeddings"),
            json={"model": modelo, "input": entrada},
            timeout=60,
            modelo=modelo,
        )

    def _extrair_respostas(self, dados: dict, modelo: str, quantidade: int) -> tuple[RespostaEmbedding, ...]:
        try:
            itens = list(dados["data"])
            if len(itens) != quantidade:
                raise ValueError("Quantidade de embeddings diferente da solicitada.")

            if all(isinstance(item, dict) and "index" in item for item in itens):
                itens = sorted(itens, key=lambda item: item["index"])

            return tuple(RespostaEmbedding(vetor=item["embedding"], modelo=modelo) for item in itens)
        except (KeyError, IndexError, TypeError, ValueError) as erro:
            raise RespostaInvalidaProvedor(
                "Resposta de embeddings do LM Studio nao possui vetor esperado.",
                provedor=PROVEDOR,
                modelo=modelo,
            ) from erro
