import { enviarJson, obterJson } from "./api.js";
import { selecionar } from "./seletores.js";

let estadoModelosChat = null;

export function obterEstadoModelosChat() {
  return estadoModelosChat;
}

export async function carregarModelosChat() {
  const seletorModelo = selecionar("#modelo-chat");
  const estadoModelo = selecionar("#estado-modelo-chat");
  estadoModelo.textContent = "Verificando modelos carregados...";
  seletorModelo.disabled = true;
  seletorModelo.replaceChildren();

  try {
    estadoModelosChat = await obterJson("/modelos/chat");
    renderizarModelosChat(estadoModelosChat);
  } catch (erro) {
    estadoModelosChat = null;
    estadoModelo.textContent = `Erro ao consultar LM Studio: ${erro.message}`;
  }
}

export function renderizarModelosChat(estado) {
  const seletorModelo = selecionar("#modelo-chat");
  const estadoModelo = selecionar("#estado-modelo-chat");
  seletorModelo.replaceChildren();

  if (!estado.modelos.length) {
    seletorModelo.append(new Option("Nenhum modelo carregado", ""));
    seletorModelo.disabled = true;
    estadoModelo.textContent = estado.aviso || "Nenhum modelo LLM carregado no LM Studio.";
    return;
  }

  if (estado.exige_selecao && !estado.modelo_ativo) {
    seletorModelo.append(new Option("Selecione um modelo", "", true, true));
  }

  estado.modelos.forEach((modelo) => {
    const rotulo = modelo.contexto ? `${modelo.nome} (${modelo.contexto} ctx)` : modelo.nome;
    const opcao = new Option(rotulo, modelo.id, false, modelo.selecionado);
    seletorModelo.append(opcao);
  });

  seletorModelo.disabled = estado.modelos.length <= 1;

  if (estado.modelo_ativo) {
    seletorModelo.value = estado.modelo_ativo;
    estadoModelo.textContent = `Usando ${estado.modelo_ativo}`;
    return;
  }

  estadoModelo.textContent = estado.aviso || "Selecione o modelo LLM.";
}

export async function selecionarModeloChat() {
  const seletorModelo = selecionar("#modelo-chat");
  const estadoModelo = selecionar("#estado-modelo-chat");
  if (!seletorModelo.value) {
    return;
  }

  estadoModelo.textContent = "Selecionando modelo...";
  try {
    estadoModelosChat = await enviarJson("/modelos/chat/selecionar", { modelo: seletorModelo.value });
    renderizarModelosChat(estadoModelosChat);
  } catch (erro) {
    estadoModelo.textContent = `Erro ao selecionar modelo: ${erro.message}`;
  }
}
