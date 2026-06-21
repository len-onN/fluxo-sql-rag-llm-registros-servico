import { ativarAba } from "./abas.js";
import { consultarRegistros } from "./consulta.js";
import { carregarModelosChat, selecionarModeloChat } from "./modelos.js";
import { criarRegistro } from "./registros.js";
import { selecionar, selecionarTodos } from "./seletores.js";

function prepararTela() {
  selecionar("[name='data_servico']").valueAsDate = new Date();
  selecionarTodos(".tab").forEach((botao) => {
    botao.addEventListener("click", () => ativarAba(botao.dataset.tab));
  });
  selecionar("#form-registro").addEventListener("submit", criarRegistro);
  selecionar("#form-consulta").addEventListener("submit", consultarRegistros);
  selecionar("#modelo-chat").addEventListener("change", selecionarModeloChat);
  selecionar("#botao-atualizar-modelos").addEventListener("click", carregarModelosChat);
  carregarModelosChat();
}

prepararTela();
