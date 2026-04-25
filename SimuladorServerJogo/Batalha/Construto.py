from __future__ import annotations


class Construto:
    def __init__(self, id_construto: str, lado_id: int, area_id: str | None = None, duracao: int = 1):
        self.id_construto = str(id_construto)
        self.lado_id = int(lado_id)
        self.area_id = area_id
        self.vivo = True
        self.duracao = int(duracao)

    def Verificar(self):
        if self.duracao <= 0:
            self.vivo = False
        return self.vivo

    def serializar(self):
        return {
            "id_construto": self.id_construto,
            "lado_id": self.lado_id,
            "area_id": self.area_id,
            "vivo": bool(self.vivo),
            "duracao": int(self.duracao),
        }
