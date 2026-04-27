from __future__ import annotations

import unicodedata
from typing import Any, Iterable, Mapping


def normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def fnum(valor: object, default: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


def inteiro(valor: object, default: int = 0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


EFEITOS_BLOQUEIO_ACAO = {"dormindo", "congelado"}
EFEITOS_NEGATIVOS = {
    "queimado", "dormindo", "envenenado", "intoxicado", "paralisado", "encharcado",
    "quebrado", "enfraquecido", "confuso", "congelado", "atordoado", "cauterizado",
    "enraizado", "recuado", "descarregado",
}
EFEITOS_POSITIVOS = {
    "amplificado", "aprimorado", "fortificado", "energizado", "provocando", "protegido",
}


class ContextoIA:
    def __init__(self, partida, lado_id: int, config, rng, propriedades_ataques: Mapping[str, dict] | None = None, usar_leitura_player: bool = False):
        self.partida = partida
        self.lado_id = int(lado_id or 0)
        self.config = config
        self.rng = rng
        self.propriedades_ataques = dict(propriedades_ataques or {})
        self.usar_leitura_player = bool(usar_leitura_player)
        self.rodada = int(getattr(partida, "rodada_atual", 1) or 1)
        self.id_partida = str(getattr(partida, "id_partida", "") or "")
        self.pokemons = self._listar_pokemons()
        self.aliados = [p for p in self.pokemons if self.lado(p) == self.lado_id]
        self.inimigos = [p for p in self.pokemons if self.lado(p) != self.lado_id]
        self.aliados_ativos = [p for p in self.aliados if self.vivo(p) and self.ativo(p) and not self.reserva(p)]
        self.inimigos_ativos = [p for p in self.inimigos if self.vivo(p) and self.ativo(p) and not self.reserva(p)]
        self.reservas_aliadas = [p for p in self.aliados if self.vivo(p) and self.reserva(p)]
        self.reservas_inimigas = [p for p in self.inimigos if self.vivo(p) and self.reserva(p)]
        self.jogadas_recebidas = getattr(partida, "jogadas_recebidas", {}) if isinstance(getattr(partida, "jogadas_recebidas", {}), dict) else {}
        self.jogadas_player = self._extrair_jogadas_player() if self.usar_leitura_player else []
        self.jogadas_visiveis_para_memoria = self._extrair_jogadas_player()
        self.ameacas_por_pokemon, self.areas_miradas = self._mapear_ameacas_player(self.jogadas_player)

    def _listar_pokemons(self) -> list:
        if hasattr(self.partida, "pokemons"):
            return list(getattr(self.partida, "pokemons", []) or [])
        if hasattr(self.partida, "pokemons_por_id"):
            return list(getattr(self.partida, "pokemons_por_id", {}).values())
        return []

    def _extrair_jogadas_player(self) -> list[dict]:
        saida: list[dict] = []
        for lado, jogada in list((self.jogadas_recebidas or {}).items()):
            if inteiro(lado, -999) == self.lado_id:
                continue
            if not isinstance(jogada, dict):
                continue
            for acao in list(jogada.get("acoes") or []):
                if isinstance(acao, dict):
                    saida.append(acao)
        return saida

    def _mapear_ameacas_player(self, acoes_player: Iterable[dict]) -> tuple[dict[str, float], set[str]]:
        ameacas: dict[str, float] = {}
        areas: set[str] = set()
        for acao in list(acoes_player or []):
            if str(acao.get("tipo") or "").lower() != "ataque":
                continue
            ataque = acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {}
            props = self.buscar_propriedades_ataque(ataque) or {}
            custo = fnum(props.get("custo", ataque.get("custo", ataque.get("Custo", 0.0))), 0.0)
            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            if alvo.get("pokemon_id"):
                pid = str(alvo.get("pokemon_id"))
                ameacas[pid] = ameacas.get(pid, 0.0) + max(10.0, custo)
            area_id = alvo.get("area_id")
            if area_id:
                for aid in self.areas_afetadas(area_id, props):
                    areas.add(str(aid))
                    poke = self.pokemon_na_area(aid)
                    if poke is not None and self.lado(poke) == self.lado_id:
                        pid = self.pid(poke)
                        ameacas[pid] = ameacas.get(pid, 0.0) + max(10.0, custo)
        return ameacas, areas

    def buscar_propriedades_ataque(self, ataque: Mapping[str, Any] | None) -> dict | None:
        if not isinstance(ataque, Mapping):
            return None
        code = str(ataque.get("Code") or ataque.get("ID") or ataque.get("code") or "").strip()
        if code:
            try:
                code = str(int(float(code)))
            except (TypeError, ValueError):
                pass
            if code in self.propriedades_ataques:
                return self.propriedades_ataques.get(code)
        nome = normalizar(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome"))
        if nome:
            for item in self.propriedades_ataques.values():
                if normalizar(item.get("nome")) == nome:
                    return item
        return None

    def props_por_code_ou_nome(self, code_ou_nome: object) -> dict | None:
        chave = str(code_ou_nome or "").strip()
        if chave:
            try:
                chave_int = str(int(float(chave)))
            except (TypeError, ValueError):
                chave_int = chave
            if chave_int in self.propriedades_ataques:
                return self.propriedades_ataques.get(chave_int)
        nome = normalizar(code_ou_nome)
        for item in self.propriedades_ataques.values():
            if normalizar(item.get("nome")) == nome:
                return item
        return None

    def area_por_id(self, area_id: object) -> dict | None:
        areas = getattr(self.partida, "areas", {})
        if isinstance(areas, dict):
            return areas.get(str(area_id or ""))
        return None

    def todas_areas(self) -> list[dict]:
        areas = getattr(self.partida, "areas", {})
        if isinstance(areas, dict):
            return list(areas.values())
        return []

    def area_existe(self, area_id: object) -> bool:
        if hasattr(self.partida, "area_existe"):
            return bool(self.partida.area_existe(area_id))
        return self.area_por_id(area_id) is not None

    def pokemon_na_area(self, area_id: object):
        if hasattr(self.partida, "pokemon_na_area"):
            return self.partida.pokemon_na_area(area_id)
        area = self.area_por_id(area_id)
        pid = area.get("ocupante_id") if isinstance(area, dict) else None
        return self.obter_pokemon(pid)

    def obter_pokemon(self, id_pokemon: object):
        if hasattr(self.partida, "obter_pokemon"):
            return self.partida.obter_pokemon(id_pokemon)
        return getattr(self.partida, "pokemons_por_id", {}).get(str(id_pokemon or ""))

    def areas_do_lado(self, lado_id: int) -> list[str]:
        return [str(a.get("id")) for a in self.todas_areas() if inteiro(a.get("lado_id"), -999) == int(lado_id)]

    def area_lado(self, area_id: object) -> int:
        area = self.area_por_id(area_id)
        return inteiro((area or {}).get("lado_id"), -999) if isinstance(area, dict) else -999

    def area_ocupada(self, area_id: object) -> bool:
        return self.pokemon_na_area(area_id) is not None

    def areas_afetadas(self, area_id: object, props: Mapping[str, Any] | None) -> list[str]:
        area_id = str(area_id or "")
        if not area_id:
            return []
        alvo_cfg = props.get("alvificacao") if isinstance(props, Mapping) and isinstance(props.get("alvificacao"), Mapping) else {}
        tipo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        coords = self.coords_area(area_id)
        if coords is None:
            return [area_id]
        prefixo, row, col = coords
        if tipo in {"linha", "fileira", "row", "line"}:
            return [self.area_por_coords(prefixo, row, c) for c in range(3) if self.area_por_coords(prefixo, row, c)]
        if tipo in {"coluna", "column"}:
            return [self.area_por_coords(prefixo, r, col) for r in range(3) if self.area_por_coords(prefixo, r, col)]
        return [area_id]

    def alvos_por_area(self, area_id: object, props: Mapping[str, Any] | None) -> list:
        alvos = []
        for aid in self.areas_afetadas(area_id, props):
            poke = self.pokemon_na_area(aid)
            if poke is not None and self.vivo(poke):
                alvos.append(poke)
        return alvos

    def area_permitida_para_ataque(self, pokemon, area_id: object, props: Mapping[str, Any] | None) -> bool:
        area = self.area_por_id(area_id)
        if not isinstance(area, dict):
            return False
        alvo_cfg = props.get("alvificacao") if isinstance(props, Mapping) and isinstance(props.get("alvificacao"), Mapping) else {}
        if bool(alvo_cfg.get("exige_area_ocupada")) and self.pokemon_na_area(area_id) is None:
            return False
        if not self._area_respeita_provocando(pokemon, area_id):
            return False
        permitidos = alvo_cfg.get("lados_permitidos")
        if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
            return True
        lado_area = self.area_lado(area_id)
        lado_origem = self.lado(pokemon)
        area_origem = str(self.area_id(pokemon) or "")
        for item in permitidos:
            token = str(item or "").strip().lower()
            if token in {"qualquer", "qualquer_lado", "todos", "ambos"}:
                return True
            if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"} and lado_area != lado_origem:
                return True
            if token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"} and lado_area == lado_origem:
                return True
            if token in {"usuario", "proprio", "si_mesmo"} and str(area_id) == area_origem:
                return True
        return False

    def pokemon_permitido_para_ataque(self, pokemon, alvo, props: Mapping[str, Any] | None) -> bool:
        if alvo is None or not self.vivo(alvo):
            return False
        if self.lado(alvo) != self.lado(pokemon) and self.possui_efeito(alvo, "Furtivo") and not bool(getattr(self.partida, "modo_teste", False)):
            return False
        alvo_cfg = props.get("alvificacao") if isinstance(props, Mapping) and isinstance(props.get("alvificacao"), Mapping) else {}
        if self.reserva(alvo) and not bool(alvo_cfg.get("inclui_reserva", False)):
            return False
        permitidos = alvo_cfg.get("lados_permitidos")
        if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
            return True
        lado_alvo = self.lado(alvo)
        lado_origem = self.lado(pokemon)
        for item in permitidos:
            token = str(item or "").strip().lower()
            if token in {"qualquer", "qualquer_lado", "todos", "ambos"}:
                return True
            if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"} and lado_alvo != lado_origem:
                return True
            if token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"} and lado_alvo == lado_origem:
                return True
            if token in {"usuario", "proprio", "si_mesmo"} and self.pid(alvo) == self.pid(pokemon):
                return True
        return False

    def _area_respeita_provocando(self, pokemon, area_id: object) -> bool:
        lado_area = self.area_lado(area_id)
        lado_origem = self.lado(pokemon)
        if lado_area == lado_origem:
            return True
        provocadores = [p for p in self.inimigos_ativos if self.possui_efeito(p, "Provocando")]
        if not provocadores:
            return True
        return any(str(self.area_id(p)) == str(area_id) for p in provocadores)

    @staticmethod
    def coords_area(area_id: object) -> tuple[str, int, int] | None:
        texto = str(area_id or "")
        if len(texto) < 2:
            return None
        try:
            idx = int(texto[1:]) - 1
        except (TypeError, ValueError):
            return None
        return texto[0], idx // 3, idx % 3

    @staticmethod
    def area_por_coords(prefixo: str, row: int, col: int) -> str | None:
        if row < 0 or row > 2 or col < 0 or col > 2:
            return None
        return f"{prefixo}{row * 3 + col + 1}"

    @staticmethod
    def pid(pokemon) -> str:
        return str(getattr(pokemon, "id_batalha", "") or "")

    @staticmethod
    def nome(pokemon) -> str:
        return str(getattr(pokemon, "nome", "Pokemon") or "Pokemon")

    @staticmethod
    def lado(pokemon) -> int:
        return inteiro(getattr(pokemon, "lado_id", getattr(pokemon, "LadoId", 0)), 0)

    @staticmethod
    def ativo(pokemon) -> bool:
        return bool(getattr(pokemon, "ativo", getattr(pokemon, "Ativo", False)))

    @staticmethod
    def reserva(pokemon) -> bool:
        return bool(getattr(pokemon, "reserva", getattr(pokemon, "EmReserva", False)))

    @staticmethod
    def vivo(pokemon) -> bool:
        if pokemon is None:
            return False
        if hasattr(pokemon, "esta_vivo"):
            return bool(pokemon.esta_vivo())
        return bool(getattr(pokemon, "vivo", getattr(pokemon, "Vivo", False))) and fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0) > 0

    @staticmethod
    def atributo(pokemon, chave: str, default: float = 0.0) -> float:
        if pokemon is not None and hasattr(pokemon, "obter_atributo"):
            try:
                return fnum(pokemon.obter_atributo(chave, default), default)
            except TypeError:
                return fnum(pokemon.obter_atributo(chave), default)
        attrs = getattr(pokemon, "atributos_finais", None)
        if isinstance(attrs, Mapping) and chave in attrs:
            return fnum(attrs.get(chave), default)
        return fnum(getattr(pokemon, chave, default), default)

    def vida_max(self, pokemon) -> float:
        return max(1.0, self.atributo(pokemon, "Vida", fnum(getattr(pokemon, "VidaMax", 1.0), 1.0)))

    def vida_atual(self, pokemon) -> float:
        return max(0.0, fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0))

    def vida_pct(self, pokemon) -> float:
        return self.vida_atual(pokemon) / self.vida_max(pokemon)

    def energia_atual(self, pokemon) -> float:
        return max(0.0, fnum(getattr(pokemon, "EnergiaAtual", getattr(pokemon, "Energia", 0.0)), 0.0))

    def energia_max(self, pokemon) -> float:
        return max(1.0, self.atributo(pokemon, "EneM", fnum(getattr(pokemon, "EnergiaMax", 1.0), 1.0)))

    def energia_pct(self, pokemon) -> float:
        return self.energia_atual(pokemon) / self.energia_max(pokemon)

    @staticmethod
    def barreira(pokemon) -> float:
        return max(0.0, fnum(getattr(pokemon, "BarreiraAtual", 0.0), 0.0))

    @staticmethod
    def area_id(pokemon):
        return getattr(pokemon, "area_id", getattr(pokemon, "AreaId", None))

    @staticmethod
    def ataques(pokemon) -> list[dict]:
        return list(getattr(pokemon, "ataques", getattr(pokemon, "ListaAtaques", [])) or [])

    @staticmethod
    def tipos(pokemon) -> set[str]:
        return {normalizar(t) for t in list(getattr(pokemon, "tipos", getattr(pokemon, "Tipos", [])) or [])}

    @staticmethod
    def efeitos(pokemon) -> list[dict]:
        return list(getattr(pokemon, "efeitos_formais", getattr(pokemon, "efeitos", [])) or [])

    def possui_efeito(self, pokemon, nome: object) -> bool:
        alvo = normalizar(nome)
        return any(normalizar((e or {}).get("nome") or (e or {}).get("code")) == alvo for e in self.efeitos(pokemon))

    def qtd_efeitos_negativos(self, pokemon) -> int:
        return sum(1 for e in self.efeitos(pokemon) if normalizar((e or {}).get("nome") or (e or {}).get("code")) in EFEITOS_NEGATIVOS)

    def qtd_efeitos_positivos(self, pokemon) -> int:
        return sum(1 for e in self.efeitos(pokemon) if normalizar((e or {}).get("nome") or (e or {}).get("code")) in EFEITOS_POSITIVOS)

    def apto_para_acao(self, pokemon, tipo: str = "ataque") -> bool:
        if not self.vivo(pokemon) or not self.ativo(pokemon) or self.reserva(pokemon):
            return False
        if any(self.possui_efeito(pokemon, nome) for nome in EFEITOS_BLOQUEIO_ACAO):
            return False
        if tipo == "ataque" and self.possui_efeito(pokemon, "Paralisado"):
            return False
        if tipo in {"movimento", "troca_posicao", "troca_reserva"} and self.possui_efeito(pokemon, "Enraizado"):
            return False
        return True

    @staticmethod
    def code_ataque(ataque: Mapping[str, Any] | None, props: Mapping[str, Any] | None = None) -> int:
        ataque = ataque if isinstance(ataque, Mapping) else {}
        props = props if isinstance(props, Mapping) else {}
        valor = ataque.get("Code") or ataque.get("ID") or ataque.get("code") or props.get("Code") or props.get("ID") or 0
        return inteiro(valor, 0)
