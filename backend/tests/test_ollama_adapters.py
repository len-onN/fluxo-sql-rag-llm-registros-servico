import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dominio.objetos_valor import SolicitacaoEmbedding, SolicitacaoLLM
from app.infraestrutura.provedores_llm.ollama import (
    CatalogoModelosOllama,
    ClienteOllama,
    GeradorEmbeddingsOllama,
    GeradorRespostaOllama,
    ResolvedorModeloChatOllama,
)
from app.nucleo.erros import CapacidadeNaoSuportada, RespostaInvalidaProvedor


def cliente_com_transporte(handler: httpx.MockTransport) -> ClienteOllama:
    return ClienteOllama(
        "http://ollama.local:11434/",
        cliente_http=httpx.Client(transport=handler),
    )


def componentes_chat(handler: httpx.MockTransport) -> tuple[ClienteOllama, CatalogoModelosOllama, ResolvedorModeloChatOllama]:
    cliente = cliente_com_transporte(handler)
    resolvedor = ResolvedorModeloChatOllama("llama3.2")
    catalogo = CatalogoModelosOllama(cliente, resolvedor)
    return cliente, catalogo, resolvedor


class CatalogoModelosOllamaTest(unittest.TestCase):
    def test_catalogo_lista_modelos_locais_e_marca_modelo_configurado(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://ollama.local:11434/api/tags")
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "llama3.2:latest", "model": "llama3.2:latest"},
                        {"name": "mistral:latest", "model": "mistral:latest"},
                    ]
                },
            )

        cliente = cliente_com_transporte(httpx.MockTransport(handler))
        resolvedor = ResolvedorModeloChatOllama("mistral:latest")
        catalogo = CatalogoModelosOllama(cliente, resolvedor)

        estado = catalogo.obter_estado_modelos_chat()

        self.assertEqual([modelo.id for modelo in estado.modelos], ["llama3.2:latest", "mistral:latest"])
        self.assertEqual(estado.modelo_ativo, "mistral:latest")
        self.assertEqual([modelo.selecionado for modelo in estado.modelos], [False, True])
        self.assertFalse(estado.exige_selecao)

    def test_catalogo_avisa_quando_ha_multiplos_modelos_sem_selecao(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"models": [{"name": "llama3.2"}, {"name": "mistral"}]},
            )

        estado = CatalogoModelosOllama(
            cliente_com_transporte(httpx.MockTransport(handler)),
            ResolvedorModeloChatOllama(None),
        ).obter_estado_modelos_chat()

        self.assertIsNone(estado.modelo_ativo)
        self.assertTrue(estado.exige_selecao)
        self.assertIn("Mais de um modelo", estado.aviso or "")


class GeradorRespostaOllamaTest(unittest.TestCase):
    def test_chat_envia_payload_nativo_e_normaliza_resposta(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://ollama.local:11434/api/chat")
            payloads.append(json.loads(request.content.decode()))
            return httpx.Response(
                200,
                json={"model": "llama3.2", "message": {"role": "assistant", "content": "Resposta: Servico concluido."}},
            )

        cliente, catalogo, resolvedor = componentes_chat(httpx.MockTransport(handler))
        gerador = GeradorRespostaOllama(
            cliente=cliente,
            catalogo_modelos=catalogo,
            resolvedor_modelo=resolvedor,
            max_tokens_resposta=123,
        )

        resposta = gerador.responder(
            SolicitacaoLLM(
                pergunta="Qual foi o resultado?",
                contextos=("Cliente ou local: Centro",),
                modelo="llama3.2",
                temperatura=0.2,
            )
        )

        self.assertEqual(payloads[0]["model"], "llama3.2")
        self.assertFalse(payloads[0]["stream"])
        self.assertEqual(payloads[0]["options"], {"temperature": 0.2, "num_predict": 123})
        self.assertEqual(payloads[0]["messages"][0]["role"], "system")
        self.assertEqual(payloads[0]["messages"][1]["role"], "user")
        self.assertIn("Contexto:\nCliente ou local: Centro", payloads[0]["messages"][1]["content"])
        self.assertIn("Pergunta:\nQual foi o resultado?", payloads[0]["messages"][1]["content"])
        self.assertEqual(resposta.texto, "Servico concluido.")
        self.assertEqual(resposta.modelo, "llama3.2")

    def test_chat_rejeita_resposta_sem_texto(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": {"content": ""}})

        cliente, catalogo, resolvedor = componentes_chat(httpx.MockTransport(handler))
        gerador = GeradorRespostaOllama(
            cliente=cliente,
            catalogo_modelos=catalogo,
            resolvedor_modelo=resolvedor,
            max_tokens_resposta=123,
        )

        with self.assertRaises(RespostaInvalidaProvedor):
            gerador.responder(SolicitacaoLLM(pergunta="Pergunta", modelo="llama3.2"))


class GeradorEmbeddingsOllamaTest(unittest.TestCase):
    def test_embeddings_envia_payload_e_normaliza_vetor(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://ollama.local:11434/api/embed")
            payloads.append(json.loads(request.content.decode()))
            return httpx.Response(
                200,
                json={"model": "nomic-embed-text", "embeddings": [[1, "2", 3.5]]},
            )

        gerador = GeradorEmbeddingsOllama(
            cliente_com_transporte(httpx.MockTransport(handler)),
            modelo_embedding="nomic-embed-text",
        )

        resposta = gerador.gerar_embedding(SolicitacaoEmbedding(texto="texto para vetor"))

        self.assertEqual(payloads, [{"model": "nomic-embed-text", "input": "texto para vetor"}])
        self.assertEqual(resposta.vetor, (1.0, 2.0, 3.5))
        self.assertEqual(resposta.modelo, "nomic-embed-text")

    def test_embeddings_converte_modelo_sem_capacidade(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "model llama3.2 does not support embeddings"},
                request=request,
            )

        gerador = GeradorEmbeddingsOllama(
            cliente_com_transporte(httpx.MockTransport(handler)),
            modelo_embedding="llama3.2",
        )

        with self.assertRaises(CapacidadeNaoSuportada) as contexto:
            gerador.gerar_embedding(SolicitacaoEmbedding(texto="texto para vetor"))

        self.assertEqual(contexto.exception.provedor, "ollama")
        self.assertEqual(contexto.exception.modelo, "llama3.2")


if __name__ == "__main__":
    unittest.main()
