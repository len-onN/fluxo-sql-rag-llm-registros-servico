import { dadosDoFormulario, enviarJson } from "./api.js";
import { carregarModelosChat, obterEstadoModelosChat } from "./modelos.js";
import { selecionar } from "./seletores.js";

export async function consultarRegistros(evento) {
  evento.preventDefault();
  const formulario = evento.currentTarget;
  const respostaConsulta = selecionar("#resposta-consulta");

  if (!obterEstadoModelosChat()) {
    await carregarModelosChat();
  }

  if (obterEstadoModelosChat()?.exige_selecao) {
    respostaConsulta.textContent = "Selecione o modelo LLM antes de consultar.";
    return;
  }

  respostaConsulta.textContent = "Consultando base RAG...";

  try {
    const dados = await enviarJson("/consulta", {
      ...dadosDoFormulario(formulario),
      limite: 3,
    });
    respostaConsulta.textContent = dados.aviso ? `${dados.resposta} (${dados.aviso})` : dados.resposta;
  } catch (erro) {
    respostaConsulta.textContent = `Erro: ${erro.message}`;
  }
}
