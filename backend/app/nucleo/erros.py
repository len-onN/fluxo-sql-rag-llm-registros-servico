class ErroProvedor(RuntimeError):
    def __init__(
        self,
        mensagem: str,
        *,
        provedor: str | None = None,
        modelo: str | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.provedor = provedor
        self.modelo = modelo


class TimeoutProvedor(ErroProvedor):
    pass


class ProvedorIndisponivel(ErroProvedor):
    pass


class AutenticacaoProvedor(ErroProvedor):
    pass


class LimiteTaxaProvedor(ErroProvedor):
    pass


class ModeloNaoEncontrado(ErroProvedor):
    pass


class RespostaInvalidaProvedor(ErroProvedor):
    pass


class CapacidadeNaoSuportada(ErroProvedor):
    pass
