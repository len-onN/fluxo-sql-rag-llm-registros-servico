import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dominio.objetos_valor import ModeloChat
from app.infraestrutura.provedores_llm import criar_componentes_provedores
from app.infraestrutura.provedores_llm.lm_studio import (
    CatalogoModelosLMStudio,
    GeradorEmbeddingsLMStudio,
    GeradorRespostaLMStudio,
    ResolvedorModeloChatLMStudio,
    SeletorModeloLMStudio,
)
from app.nucleo.configuracoes import Configuracoes
from app.nucleo.erros import ProvedorNaoSuportado


def configuracoes_teste(**sobrescritas: object) -> Configuracoes:
    return Configuracoes(_env_file=None, **sobrescritas)


class FactoryProvedoresTest(unittest.TestCase):
    def test_monta_componentes_lm_studio_por_configuracao(self) -> None:
        componentes = criar_componentes_provedores(
            configuracoes_teste(
                modelo_chat=" chat-configurado ",
                modelo_embedding="embedding-configurado",
            )
        )

        self.assertIsInstance(componentes.gerador_embeddings, GeradorEmbeddingsLMStudio)
        self.assertIsInstance(componentes.gerador_resposta, GeradorRespostaLMStudio)
        self.assertIsInstance(componentes.catalogo_modelos, CatalogoModelosLMStudio)
        self.assertIsInstance(componentes.seletor_modelo, SeletorModeloLMStudio)
        self.assertEqual(
            componentes.estado.como_dict(),
            {
                "provedor_chat": "lm_studio",
                "provedor_embeddings": "lm_studio",
                "modelo_chat": "chat-configurado",
                "modelo_embedding": "embedding-configurado",
            },
        )

    def test_rejeita_provedor_chat_desconhecido_com_erro_amigavel(self) -> None:
        with self.assertRaises(ProvedorNaoSuportado) as contexto:
            criar_componentes_provedores(configuracoes_teste(provedor_chat="openai_compativel"))

        self.assertEqual(contexto.exception.capacidade, "chat")
        self.assertEqual(contexto.exception.provedor, "openai_compativel")
        self.assertIn("lm_studio", str(contexto.exception))

    def test_rejeita_provedor_embeddings_desconhecido_com_erro_amigavel(self) -> None:
        with self.assertRaises(ProvedorNaoSuportado) as contexto:
            criar_componentes_provedores(configuracoes_teste(provedor_embeddings="ollama"))

        self.assertEqual(contexto.exception.capacidade, "embeddings")
        self.assertEqual(contexto.exception.provedor, "ollama")
        self.assertIn("lm_studio", str(contexto.exception))


class ResolvedorModeloChatLMStudioTest(unittest.TestCase):
    def test_modelo_chat_inicial_pode_usar_id_ou_modelo(self) -> None:
        modelos = (
            ModeloChat(id="instancia-a", modelo="modelo-a", nome="Modelo A"),
            ModeloChat(id="instancia-b", modelo="modelo-b", nome="Modelo B"),
        )

        self.assertEqual(ResolvedorModeloChatLMStudio("instancia-b").resolver(modelos, True), "instancia-b")
        self.assertEqual(ResolvedorModeloChatLMStudio("modelo-b").resolver(modelos, True), "instancia-b")


if __name__ == "__main__":
    unittest.main()
