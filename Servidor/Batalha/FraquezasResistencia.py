from __future__ import annotations

import unicodedata
from Servidor.Gerais.LoaderTabelas import carregar_csv_lista


def _normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


_TIPOS_ALIAS = {
    "veneno": "venenoso",
    "rocha": "pedra",
}


def _normalizar_tipo(valor: object) -> str:
    tipo = _normalizar(valor)
    return _TIPOS_ALIAS.get(tipo, tipo)


def _numero(valor: object, default: float = 1.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


class FraquezasResistencia:
    def __init__(self):
        self._matriz: dict[str, dict[str, float]] = {}
        self._carregado = False

    def carregar(self) -> None:
        if self._carregado:
            return
        self._carregado = True
        try:
            linhas = carregar_csv_lista("Pokemon Global Server - Sistema FR.csv")
        except Exception:
            return
        if not linhas:
            return
        cabecalho = [_normalizar(c) for c in linhas[0][1:]]
        for linha in linhas[1:]:
            if not linha:
                continue
            tipo_ataque = _normalizar_tipo(linha[0])
            if not tipo_ataque:
                continue
            self._matriz[tipo_ataque] = {}
            for tipo_defesa, valor in zip(cabecalho, linha[1:]):
                if tipo_defesa:
                    self._matriz[tipo_ataque][tipo_defesa] = _numero(valor, 1.0)

    def obter_multiplicador(self, tipo_ataque: object, tipos_defensor: object) -> float:
        self.carregar()
        tipo = _normalizar_tipo(tipo_ataque)
        if not tipo:
            return 1.0
        if isinstance(tipos_defensor, str):
            tipos = [tipos_defensor]
        else:
            tipos = list(tipos_defensor or [])
        multiplicador = 1.0
        linha = self._matriz.get(tipo, {})
        for tipo_def in tipos:
            chave = _normalizar_tipo(tipo_def)
            if not chave:
                continue
            multiplicador *= float(linha.get(chave, 1.0))
        return multiplicador

    def eh_fraco(self, tipo_ataque: object, tipos_defensor: object) -> bool:
        return self.obter_multiplicador(tipo_ataque, tipos_defensor) > 1.0

    def resiste(self, tipo_ataque: object, tipos_defensor: object) -> bool:
        mult = self.obter_multiplicador(tipo_ataque, tipos_defensor)
        return 0.0 < mult < 1.0

    def eh_imune(self, tipo_ataque: object, tipos_defensor: object) -> bool:
        return self.obter_multiplicador(tipo_ataque, tipos_defensor) == 0.0


TABELA_FR = FraquezasResistencia()


def obter_multiplicador(tipo_ataque: object, tipos_defensor: object) -> float:
    return TABELA_FR.obter_multiplicador(tipo_ataque, tipos_defensor)
