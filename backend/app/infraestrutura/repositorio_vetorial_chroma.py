from pathlib import Path

from app.dominio.entidades import RegistroServico
from app.dominio.objetos_valor import ContextoRAG, ValorMetadado


NOME_COLECAO = "registros_servico"


class RepositorioVetorialChroma:
    def __init__(self, diretorio_chroma: str) -> None:
        import chromadb

        Path(diretorio_chroma).mkdir(parents=True, exist_ok=True)
        cliente = chromadb.PersistentClient(path=diretorio_chroma)
        self._colecao = cliente.get_or_create_collection(name=NOME_COLECAO)

    def indexar(self, registro: RegistroServico, embedding: list[float]) -> None:
        if registro.id is None:
            raise ValueError("Registro precisa estar salvo antes da indexacao vetorial.")

        self._colecao.upsert(
            ids=[str(registro.id)],
            embeddings=[embedding],
            documents=[registro.texto_para_rag()],
            metadatas=[
                {
                    "funcionario": registro.funcionario,
                    "id_registro": registro.id,
                    "cliente_local": registro.cliente_local,
                    "tipo_servico": registro.tipo_servico,
                    "status": registro.status,
                    "data_servico": registro.data_servico.isoformat(),
                }
            ],
        )

    def buscar_similares(self, embedding: list[float], limite: int) -> list[ContextoRAG]:
        resultado = self._colecao.query(
            query_embeddings=[embedding],
            n_results=limite,
            include=["documents", "metadatas", "distances"],
        )

        ids = resultado.get("ids") or [[]]
        documentos = resultado.get("documents") or [[]]
        metadados = resultado.get("metadatas") or [[]]
        distancias = resultado.get("distances") or [[]]

        contextos: list[ContextoRAG] = []
        for indice, documento in enumerate(documentos[0]):
            metadados_contexto = self._normalizar_metadados(_obter_item(metadados[0], indice, {}))
            id_documento = _obter_item(ids[0], indice)
            distancia = _obter_item(distancias[0], indice)
            contextos.append(
                ContextoRAG(
                    id_registro=self._resolver_id_registro(metadados_contexto, id_documento),
                    documento=documento,
                    metadados=metadados_contexto,
                    distancia=float(distancia) if distancia is not None else None,
                    fonte=f"chroma:{NOME_COLECAO}",
                )
            )

        return contextos

    def _normalizar_metadados(self, metadados: object) -> dict[str, ValorMetadado]:
        if not isinstance(metadados, dict):
            return {}

        return {
            str(chave): valor
            for chave, valor in metadados.items()
            if isinstance(valor, str | int | float | bool)
        }

    def _resolver_id_registro(self, metadados: dict[str, ValorMetadado], id_documento: object) -> int | None:
        id_metadado = metadados.get("id_registro")
        if isinstance(id_metadado, int):
            return id_metadado

        try:
            return int(str(id_documento))
        except (TypeError, ValueError):
            return None


def _obter_item(lista: list, indice: int, padrao: object = None) -> object:
    if indice >= len(lista):
        return padrao
    return lista[indice]
