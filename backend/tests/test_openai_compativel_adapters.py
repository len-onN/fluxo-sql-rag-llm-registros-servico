import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dominio.objetos_valor import SolicitacaoEmbedding, SolicitacaoLLM
from app.infraestrutura.provedores_llm.openai_compativel import (
    CatalogoModelosOpenAICompativel,
    ClienteOpenAICompativel,
    GeradorEmbeddingsOpenAICompativel,
    GeradorRespostaOpenAICompativel,
)
from app.nucleo.erros import AutenticacaoProvedor, RespostaInvalidaProvedor


def cliente_com_transporte(handler: httpx.MockTransport, api_key: str | None = "token-teste") -> ClienteOpenAICompativel:
    return ClienteOpenAICompativel(
        "https://openai.compat/v1/",
        api_key=api_key,
        cliente_http=httpx.Client(transport=handler),
    )


class CatalogoModelosOpenAICompativelTest(unittest.TestCase):
    def test_catalogo_expoe_modelo_chat_configurado(self) -> None:
        catalogo = CatalogoModelosOpenAICompativel(" modelo-chat ")

        estado = catalogo.obter_estado_modelos_chat()

        self.assertEqual(estado.modelo_ativo, "modelo-chat")
        self.assertFalse(estado.exige_selecao)
        self.assertIsNone(estado.aviso)
        self.assertEqual([(modelo.id, modelo.selecionado) for modelo in estado.modelos], [("modelo-chat", True)])

    def test_catalogo_avisa_quando_modelo_chat_nao_esta_configurado(self) -> None:
        estado = CatalogoModelosOpenAICompativel(None).obter_estado_modelos_chat()

        self.assertEqual(estado.modelos, ())
        self.assertIsNone(estado.modelo_ativo)
        self.assertIn("MODELO_CHAT", estado.aviso or "")


class GeradorRespostaOpenAICompativelTest(unittest.TestCase):
    def test_chat_envia_payload_compativel_e_normaliza_resposta(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://openai.compat/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer token-teste")
            payloads.append(json.loads(request.content.decode()))
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Resposta: Servico concluido."}}]},
            )

        gerador = GeradorRespostaOpenAICompativel(
            cliente=cliente_com_transporte(httpx.MockTransport(handler)),
            modelo_chat="modelo-chat",
            max_tokens_resposta=123,
        )

        resposta = gerador.responder(
            SolicitacaoLLM(
                pergunta="Qual foi o resultado?",
                contextos=("Cliente ou local: Centro",),
                temperatura=0.2,
            )
        )

        self.assertEqual(payloads[0]["model"], "modelo-chat")
        self.assertEqual(payloads[0]["temperature"], 0.2)
        self.assertEqual(payloads[0]["max_tokens"], 123)
        self.assertEqual(payloads[0]["messages"][0]["role"], "system")
        self.assertEqual(payloads[0]["messages"][1]["role"], "user")
        self.assertIn("Contexto:\nCliente ou local: Centro", payloads[0]["messages"][1]["content"])
        self.assertIn("Pergunta:\nQual foi o resultado?", payloads[0]["messages"][1]["content"])
        self.assertEqual(resposta.texto, "Servico concluido.")
        self.assertEqual(resposta.modelo, "modelo-chat")

    def test_chat_converte_erro_de_autenticacao(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": {"message": "invalid api key"}},
                request=request,
            )

        gerador = GeradorRespostaOpenAICompativel(
            cliente=cliente_com_transporte(httpx.MockTransport(handler), api_key=""),
            modelo_chat="modelo-chat",
            max_tokens_resposta=123,
        )

        with self.assertRaises(AutenticacaoProvedor) as contexto:
            gerador.responder(SolicitacaoLLM(pergunta="Pergunta"))

        self.assertEqual(contexto.exception.provedor, "openai_compativel")
        self.assertEqual(contexto.exception.modelo, "modelo-chat")

    def test_chat_rejeita_resposta_sem_texto(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

        gerador = GeradorRespostaOpenAICompativel(
            cliente=cliente_com_transporte(httpx.MockTransport(handler)),
            modelo_chat="modelo-chat",
            max_tokens_resposta=123,
        )

        with self.assertRaises(RespostaInvalidaProvedor):
            gerador.responder(SolicitacaoLLM(pergunta="Pergunta"))


class GeradorEmbeddingsOpenAICompativelTest(unittest.TestCase):
    def test_embeddings_envia_payload_e_normaliza_vetor(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://openai.compat/v1/embeddings")
            self.assertEqual(request.headers["authorization"], "Bearer token-teste")
            payloads.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"data": [{"embedding": [1, "2", 3.5]}]})

        gerador = GeradorEmbeddingsOpenAICompativel(
            cliente=cliente_com_transporte(httpx.MockTransport(handler)),
            modelo_embedding="embedding-padrao",
        )

        resposta = gerador.gerar_embedding(SolicitacaoEmbedding(texto="texto para vetor"))

        self.assertEqual(payloads, [{"model": "embedding-padrao", "input": "texto para vetor"}])
        self.assertEqual(resposta.vetor, (1.0, 2.0, 3.5))
        self.assertEqual(resposta.modelo, "embedding-padrao")


if __name__ == "__main__":
    unittest.main()
