const apiBase = "/api";

export function dadosDoFormulario(formulario) {
  return Object.fromEntries(new FormData(formulario).entries());
}

export async function enviarJson(caminho, corpo) {
  const resposta = await fetch(`${apiBase}${caminho}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });

  const dados = await resposta.json();
  if (!resposta.ok) {
    throw new Error(dados.detail || "Falha na requisicao.");
  }
  return dados;
}

export async function obterJson(caminho) {
  const resposta = await fetch(`${apiBase}${caminho}`);
  const dados = await resposta.json();
  if (!resposta.ok) {
    throw new Error(dados.detail || "Falha na requisicao.");
  }
  return dados;
}
