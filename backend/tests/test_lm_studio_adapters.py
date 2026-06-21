import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dominio.objetos_valor import SolicitacaoEmbedding, SolicitacaoLLM
from app.infraestrutura.provedores_llm.lm_studio import (
    CatalogoModelosLMStudio,
    ClienteLMStudio,
    GeradorEmbeddingsLMStudio,
    GeradorRespostaLMStudio,
    ParserRespostaLMStudio,
    PoliticaFallbackRespostaLMStudio,
    ResolvedorModeloChatLMStudio,
    SeletorModeloLMStudio,
)


def cliente_com_transporte(handler: httpx.MockTransport) -> ClienteLMStudio:
    return ClienteLMStudio("http://lmstudio.local/v1", httpx.Client(transport=handler))


def resposta_modelos(*modelos: dict) -> httpx.Response:
    return httpx.Response(200, json={"models": list(modelos)})


def modelo_llm(chave: str, instancia: str, nome: str, contexto: int = 4096) -> dict:
    return {
        "type": "llm",
        "key": chave,
        "display_name": nome,
        "loaded_instances": [{"id": instancia, "config": {"context_length": contexto}}],
    }


class CatalogoModelosLMStudioTest(unittest.TestCase):
    def test_catalogo_e_seletor_compartilham_estado_do_modelo_ativo(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://lmstudio.local/api/v1/models")
            return resposta_modelos(
                modelo_llm("modelo-a", "instancia-a", "Modelo A"),
                modelo_llm("modelo-b", "instancia-b", "Modelo B", contexto=8192),
            )

        resolvedor = ResolvedorModeloChatLMStudio()
        catalogo = CatalogoModelosLMStudio(cliente_com_transporte(httpx.MockTransport(handler)), resolvedor)
        seletor = SeletorModeloLMStudio(catalogo, resolvedor)

        estado_inicial = catalogo.obter_estado_modelos_chat()
        estado_selecionado = seletor.selecionar_modelo_chat("instancia-b")

        self.assertTrue(estado_inicial.exige_selecao)
        self.assertIsNone(estado_inicial.modelo_ativo)
        self.assertEqual(estado_selecionado.modelo_ativo, "instancia-b")
        self.assertEqual(
            [(modelo.id, modelo.selecionado, modelo.contexto) for modelo in estado_selecionado.modelos],
            [("instancia-a", False, 4096), ("instancia-b", True, 8192)],
        )


class GeradorEmbeddingsLMStudioTest(unittest.TestCase):
    def test_gerador_embeddings_envia_payload_e_normaliza_vetor(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://lmstudio.local/v1/embeddings")
            payloads.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"data": [{"embedding": [1, "2", 3.5]}]})

        gerador = GeradorEmbeddingsLMStudio(
            cliente_com_transporte(httpx.MockTransport(handler)),
            modelo_embedding="embedding-padrao",
        )

        resposta = gerador.gerar_embedding(SolicitacaoEmbedding(texto="texto para vetor"))

        self.assertEqual(payloads, [{"model": "embedding-padrao", "input": "texto para vetor"}])
        self.assertEqual(resposta.vetor, (1.0, 2.0, 3.5))
        self.assertEqual(resposta.modelo, "embedding-padrao")


class ParserRespostaLMStudioTest(unittest.TestCase):
    def test_parser_extrai_texto_final_de_mensagem(self) -> None:
        parser = ParserRespostaLMStudio()
        dados = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Resposta: Servico concluido."}],
                }
            ]
        }

        self.assertEqual(parser.extrair_texto_final(dados), "Servico concluido.")

    def test_parser_recupera_resposta_final_do_raciocinio(self) -> None:
        parser = ParserRespostaLMStudio()
        dados = {
            "output": [
                {
                    "type": "reasoning",
                    "content": [{"type": "reasoning_text", "text": "analise\nResposta final: Cliente Centro."}],
                }
            ]
        }

        self.assertEqual(parser.extrair_texto_final(dados), "Cliente Centro")


class GeradorRespostaLMStudioTest(unittest.TestCase):
    def test_chat_usa_modelo_resolvido_e_aplica_fallback_quando_resposta_vem_ruim(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/v1/models":
                return resposta_modelos(modelo_llm("modelo-chat", "chat-1", "Modelo Chat"))
            if request.url.path == "/v1/responses":
                payloads.append(json.loads(request.content.decode()))
                return httpx.Response(
                    200,
                    json={
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": "service data"}],
                            }
                        ]
                    },
                )
            return httpx.Response(404)

        resolvedor = ResolvedorModeloChatLMStudio()
        cliente = cliente_com_transporte(httpx.MockTransport(handler))
        catalogo = CatalogoModelosLMStudio(cliente, resolvedor)
        gerador = GeradorRespostaLMStudio(
            cliente=cliente,
            catalogo_modelos=catalogo,
            resolvedor_modelo=resolvedor,
            parser_resposta=ParserRespostaLMStudio(),
            politica_fallback=PoliticaFallbackRespostaLMStudio(),
            max_tokens_resposta=12,
        )
        contexto = "\n".join(
            [
                "Cliente ou local: Cliente Centro",
                "Data do servico: 2026-06-18",
                "Problemas encontrados: Sem falhas criticas.",
            ]
        )

        resposta = gerador.responder(SolicitacaoLLM(pergunta="Qual foi o problema?", contextos=(contexto,)))

        self.assertEqual(payloads[0]["model"], "chat-1")
        self.assertEqual(payloads[0]["temperature"], 0.1)
        self.assertEqual(payloads[0]["max_output_tokens"], 12)
        self.assertIn("Pergunta:\nQual foi o problema?", payloads[0]["input"])
        self.assertEqual(
            resposta.texto,
            (
                "Encontrei um registro relacionado ao cliente/local Cliente Centro, "
                "na data 2026-06-18. Problemas encontrados: Sem falhas criticas."
            ),
        )
        self.assertEqual(resposta.modelo, "chat-1")


if __name__ == "__main__":
    unittest.main()
