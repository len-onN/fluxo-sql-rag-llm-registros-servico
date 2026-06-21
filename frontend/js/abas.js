import { carregarModelosChat } from "./modelos.js";
import { carregarRegistros } from "./registros.js";
import { selecionarTodos } from "./seletores.js";

export function ativarAba(nomeAba) {
  selecionarTodos(".tab").forEach((botao) => {
    botao.classList.toggle("active", botao.dataset.tab === nomeAba);
  });

  selecionarTodos(".tab-panel").forEach((painel) => {
    painel.classList.toggle("active", painel.dataset.panel === nomeAba);
  });

  if (nomeAba === "registros") {
    carregarRegistros();
  }

  if (nomeAba === "consulta") {
    carregarModelosChat();
  }
}
