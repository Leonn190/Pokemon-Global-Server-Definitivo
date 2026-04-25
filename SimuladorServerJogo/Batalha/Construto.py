from __future__ import annotations


class Construto:
    def __init__(self, id_construto: str, dados: dict | None = None):
        self.id_construto = str(id_construto)
        self.dados = dict(dados or {})
        self.vivo = bool(self.dados.get("vivo", True))

    def Verificar(self):
        return self.vivo

    def serializar(self):
        return {
            "id_construto": self.id_construto,
            "dados": dict(self.dados),
            "vivo": bool(self.vivo),
        }

