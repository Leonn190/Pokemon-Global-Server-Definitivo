from __future__ import annotations

from dataclasses import dataclass

_GRUPOS_ORDEM = {
    "self": 0,
    "mesmo_lado": 1,
    "lado_oposto": 2,
    "qualquer_lado": 3,
    "todos": 4,
}


@dataclass
class PassivaRegistrada:
    nome: str
    flag: str
    grupo: str
    func: object
    origem: str
    code: str | None = None
    dono: object = None
    ordem: int = 0


@dataclass
class ExecuteReativo:
    nome: str
    flag: str
    func: object
    origem_ataque: str | None = None
    code: str | None = None
    grupo: str | None = None
    ordem: int = 0


class ResolvedorFlags:
    def __init__(self):
        self._passivas_por_flag: dict[str, list[PassivaRegistrada]] = {}
        self._ordem = 0

    def registrar_passiva(self, nome, flag, grupo, func, origem, dono=None, code=None):
        if not callable(func) or not flag:
            return None
        self._ordem += 1
        item = PassivaRegistrada(
            nome=str(nome or "passiva"),
            flag=str(flag),
            grupo=str(grupo or "todos"),
            func=func,
            origem=str(origem or "desconhecido"),
            code=str(code) if code is not None else None,
            dono=dono,
            ordem=self._ordem,
        )
        self._passivas_por_flag.setdefault(item.flag, []).append(item)
        return item

    def _grupo_compativel(self, grupo, dono, pokemon_evento):
        if pokemon_evento is None:
            return grupo in {"todos", "qualquer_lado"}
        if dono is None:
            return True
        if grupo == "self":
            return str(getattr(dono, "id_batalha", "")) == str(getattr(pokemon_evento, "id_batalha", ""))
        if grupo == "mesmo_lado":
            return int(getattr(dono, "lado_id", -1)) == int(getattr(pokemon_evento, "lado_id", -2))
        if grupo == "lado_oposto":
            return int(getattr(dono, "lado_id", -1)) != int(getattr(pokemon_evento, "lado_id", -2))
        return grupo in {"qualquer_lado", "todos"}

    def coletar_testaveis(self, flag, contexto, reativos=None):
        contexto = dict(contexto or {})
        pokemon_evento = contexto.get("pokemon_evento")
        saida = []
        for passiva in list(self._passivas_por_flag.get(str(flag), [])):
            origem = str(getattr(passiva, "origem", "") or "").strip().lower()
            dono = getattr(passiva, "dono", None)
            if origem in {"habilidade", "item"} and dono is not None and hasattr(dono, "possui_efeito") and dono.possui_efeito("Atordoado"):
                continue
            if self._grupo_compativel(passiva.grupo, passiva.dono, pokemon_evento):
                saida.append(("passiva", passiva))
        for reativo in list(reativos or []):
            if str(getattr(reativo, "flag", "")) == str(flag):
                saida.append(("execute_reativo", reativo))
        saida.sort(
            key=lambda item: (
                str(flag),
                _GRUPOS_ORDEM.get(str(getattr(item[1], "grupo", "todos")), 99),
                str(getattr(getattr(item[1], "dono", None), "id_batalha", "")),
                int(getattr(item[1], "ordem", 0)),
            )
        )
        return saida

    def disparar(self, flag, contexto, reativos=None):
        contexto = dict(contexto or {})
        eventos = []
        for tipo, item in self.coletar_testaveis(flag, contexto, reativos=reativos):
            ctx_exec = dict(contexto)
            if tipo == "passiva":
                ctx_exec["dono_passiva"] = getattr(item, "dono", None)
                ctx_exec["passiva"] = item
                ctx_exec["tipo_testavel"] = "passiva"
            else:
                ctx_exec["execute_reativo"] = item
                ctx_exec["tipo_testavel"] = "execute_reativo"
            try:
                retorno = item.func(ctx_exec)
            except Exception as exc:
                retorno = {"erro": str(exc), "nome": getattr(item, "nome", tipo)}
            if isinstance(retorno, dict) and retorno:
                eventos.append({
                    "tipo": tipo,
                    "flag": str(flag),
                    "nome": getattr(item, "nome", None),
                    "origem": getattr(item, "origem", getattr(item, "origem_ataque", None)),
                    "code": getattr(item, "code", None),
                    "dados": retorno,
                })
        return eventos
