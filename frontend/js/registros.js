import { dadosDoFormulario, enviarJson, obterJson } from "./api.js";
import { selecionar } from "./seletores.js";

export async function criarRegistro(evento) {
  evento.preventDefault();
  const formulario = evento.currentTarget;
  const feedback = selecionar("#feedback-registro");
  feedback.textContent = "Salvando registro...";

  try {
    const dados = await enviarJson("/registros", dadosDoFormulario(formulario));
    feedback.textContent = dados.indexado
      ? "Registro salvo no SQL e indexado no RAG."
      : dados.aviso || "Registro salvo, mas ainda nao indexado.";
  } catch (erro) {
    feedback.textContent = `Erro: ${erro.message}`;
  }
}

export async function carregarRegistros() {
  const lista = selecionar("#lista-registros");
  lista.textContent = "Carregando registros...";

  try {
    const registros = await obterJson("/registros");

    if (!registros.length) {
      lista.textContent = "Nenhum registro salvo ainda.";
      return;
    }

    lista.replaceChildren(...registros.map(criarItemRegistro));
  } catch (erro) {
    lista.textContent = `Erro ao carregar registros: ${erro.message}`;
  }
}

function criarItemRegistro(registro) {
  const item = document.createElement("article");
  const titulo = document.createElement("strong");
  const tipoServico = document.createElement("p");
  const descricao = document.createElement("p");

  item.className = "registro-item";
  titulo.textContent = `${registro.cliente_local} - ${registro.status}`;
  tipoServico.textContent = `${registro.tipo_servico} por ${registro.funcionario}`;
  descricao.textContent = registro.descricao;

  item.append(titulo, tipoServico, descricao);
  return item;
}
