import re
from typing import Any


class ParserRespostaLMStudio:
    def extrair_texto_final(self, dados: dict[str, Any]) -> str:
        textos: list[str] = []
        raciocinios: list[str] = []
        for item in dados.get("output", []):
            if not isinstance(item, dict):
                continue
            conteudos = item.get("content", [])
            if not isinstance(conteudos, list):
                continue
            for conteudo in conteudos:
                if not isinstance(conteudo, dict):
                    continue
                if item.get("type") == "message" and conteudo.get("type") == "output_text":
                    textos.append(conteudo.get("text", ""))
                if item.get("type") == "reasoning" and conteudo.get("type") == "reasoning_text":
                    raciocinios.append(conteudo.get("text", ""))

        texto_final = "\n".join(texto.strip() for texto in textos if texto.strip())
        if not texto_final:
            texto_final = self._extrair_resposta_do_raciocinio(raciocinios)
        return self._normalizar_resposta_final(texto_final)

    def _normalizar_resposta_final(self, texto: str) -> str:
        return re.sub(r"^\s*resposta\s*:\s*", "", texto.strip(), flags=re.IGNORECASE)

    def _extrair_resposta_do_raciocinio(self, raciocinios: list[str]) -> str:
        linhas = "\n".join(raciocinios).splitlines()
        padroes = [
            r"(?:resposta final|resposta|answer|final answer)\s*:\s*(.+)",
            r"(?:final decision|final output)\s*:\s*(.+)",
        ]

        for linha in reversed(linhas):
            texto = linha.strip().strip("*- ")
            for padrao in padroes:
                encontrado = re.search(padrao, texto, flags=re.IGNORECASE)
                if encontrado:
                    candidato = encontrado.group(1).strip().strip("\"' .")
                    if len(candidato) >= 4:
                        return candidato

        return ""
