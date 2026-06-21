import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.aplicacao.servicos import MontadorPromptRAG, PoliticaContextoRAG
from app.dominio.objetos_valor import ContextoRAG


def contexto(
    documento: str,
    distancia: float | None = None,
    pontuacao: float | None = None,
    id_registro: int | None = None,
) -> ContextoRAG:
    return ContextoRAG(
        id_registro=id_registro,
        documento=documento,
        distancia=distancia,
        pontuacao=pontuacao,
        fonte="teste",
    )


class PoliticaContextoRAGTest(unittest.TestCase):
    def test_filtra_por_limiares_e_respeita_top_k(self) -> None:
        politica = PoliticaContextoRAG(
            top_k_padrao=3,
            distancia_maxima=0.4,
            pontuacao_minima=0.7,
        )

        selecionados = politica.selecionar(
            [
                contexto("A", distancia=0.2, pontuacao=0.9, id_registro=1),
                contexto("B", distancia=0.8, pontuacao=0.9, id_registro=2),
                contexto("C", distancia=0.1, pontuacao=0.4, id_registro=3),
                contexto("D", distancia=0.3, pontuacao=0.8, id_registro=4),
                contexto("E", distancia=0.2, pontuacao=0.9, id_registro=5),
            ],
            limite_solicitado=2,
        )

        self.assertEqual(selecionados.documentos, ("A", "D"))
        self.assertEqual([fonte.id_registro for fonte in selecionados.fontes], [1, 4])

    def test_aplica_orcamento_de_contexto_preservando_fonte(self) -> None:
        politica = PoliticaContextoRAG(orcamento_caracteres=12)

        selecionados = politica.selecionar(
            [contexto("Cliente Centro com manutencao preventiva", id_registro=42)],
            limite_solicitado=1,
        )

        self.assertEqual(selecionados.documentos, ("Cliente Cent",))
        self.assertEqual(selecionados.fontes[0].id_registro, 42)


class MontadorPromptRAGTest(unittest.TestCase):
    def test_monta_prompt_rag_sem_chamar_provedor(self) -> None:
        montador = MontadorPromptRAG()

        prompt = montador.montar_prompt_usuario("Qual foi o status?", ["Status: Concluido", "Cliente: Centro"])

        self.assertEqual(
            prompt,
            "Contexto:\nStatus: Concluido\n\n---\n\nCliente: Centro\n\nPergunta:\nQual foi o status?",
        )

    def test_monta_prompt_com_contexto_vazio(self) -> None:
        montador = MontadorPromptRAG()

        prompt = montador.montar_prompt_usuario("Quais registros existem?", [])

        self.assertEqual(prompt, "Contexto:\nNenhum contexto encontrado.\n\nPergunta:\nQuais registros existem?")


if __name__ == "__main__":
    unittest.main()
