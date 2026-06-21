class PoliticaFallbackRespostaLMStudio:
    MARCADORES_INGLES = (
        "functionary",
        "client ",
        "service data",
        "service ",
        "status completed",
        "problems found",
        "network",
        "beginning",
        "recordo",
    )

    def deve_aplicar(self, texto: str) -> bool:
        return (
            len(texto) < 4
            or texto == "<texto final>"
            or self._tem_marcador_ingles(texto)
            or self._parece_truncada(texto)
        )

    def montar_resposta(self, contextos: list[str]) -> str:
        if not contextos:
            return "Nao foram encontrados registros relacionados a pergunta."

        campos = self._mapear_campos_contexto(contextos[0])
        cliente = campos.get("Cliente ou local", "cliente/local nao informado")
        data_servico = campos.get("Data do servico", "data nao informada")
        problemas = campos.get("Problemas encontrados", "sem problemas informados")

        return (
            f"Encontrei um registro relacionado ao cliente/local {cliente}, "
            f"na data {data_servico}. Problemas encontrados: {problemas}"
        )

    def _tem_marcador_ingles(self, texto: str) -> bool:
        texto_baixo = texto.lower()
        return any(marcador in texto_baixo for marcador in self.MARCADORES_INGLES)

    def _parece_truncada(self, texto: str) -> bool:
        texto_limpo = texto.strip()
        if not texto_limpo:
            return True
        return not texto_limpo.endswith((".", "!", "?"))

    def _mapear_campos_contexto(self, contexto: str) -> dict[str, str]:
        campos: dict[str, str] = {}
        for linha in contexto.splitlines():
            if ":" not in linha:
                continue
            chave, valor = linha.split(":", 1)
            campos[chave.strip()] = valor.strip()
        return campos
