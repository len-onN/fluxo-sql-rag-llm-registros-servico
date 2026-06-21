import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


CAMINHO_DATASET = Path(__file__).resolve().parent / "fixtures" / "dataset_regressao_rag.json"


class DatasetRegressaoRAGTest(unittest.TestCase):
    def test_dataset_tem_casos_minimos_para_comparacao_de_qualidade(self) -> None:
        dados = json.loads(CAMINHO_DATASET.read_text(encoding="utf-8"))

        self.assertEqual(dados["versao"], 1)
        self.assertGreaterEqual(len(dados["registros"]), 3)
        self.assertGreaterEqual(len(dados["casos"]), 3)

        ids_registros = {registro["id"] for registro in dados["registros"]}
        self.assertEqual(len(ids_registros), len(dados["registros"]))

        ids_casos: set[str] = set()
        for caso in dados["casos"]:
            ids_casos.add(caso["id"])
            self.assertGreaterEqual(len(caso["pergunta"]), 10)
            self.assertTrue(set(caso["ids_registros_esperados"]).issubset(ids_registros))
            self.assertTrue(caso["termos_resposta_esperados"])
            for termo in caso["termos_resposta_esperados"]:
                self.assertGreaterEqual(len(termo), 3)

        self.assertEqual(len(ids_casos), len(dados["casos"]))


if __name__ == "__main__":
    unittest.main()
