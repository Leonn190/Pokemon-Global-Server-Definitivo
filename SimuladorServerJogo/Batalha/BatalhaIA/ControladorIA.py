from __future__ import annotations

import json
import random
from pathlib import Path


def _f(valor, default=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


class ControladorIA:
    def __init__(self, seed_base=None):
        self.seed_base = seed_base
        self.propriedades_ataques = self._carregar_propriedades_ataques()

    def gerar_jogada(self, partida, lado_id):
        lado_id = int(lado_id or 0)
        rodada = int(getattr(partida, "rodada_atual", 1) or 1)
        rng = random.Random(self._seed_rodada(partida, rodada, lado_id))
        acoes = []
        ativos = [p for p in self._pokemons(partida) if self._lado(p) == lado_id and self._vivo(p) and self._ativo(p) and not self._reserva(p)]
        inimigos = [p for p in self._pokemons(partida) if self._lado(p) != lado_id and self._vivo(p) and self._ativo(p) and not self._reserva(p)]
        inimigos.sort(key=lambda p: (self._vida_percentual(p), str(self._pid(p))))

        for pokemon in ativos:
            if len(acoes) >= 5:
                break
            acao = self._acao_ataque(partida, pokemon, inimigos, rodada, rng)
            if acao is not None:
                acoes.append(acao)
                continue
            acao = self._acao_troca_simples(partida, pokemon, lado_id, rodada)
            if acao is not None:
                acoes.append(acao)

        return {
            "id_partida": str(getattr(partida, "id_partida", "") or ""),
            "rodada": rodada,
            "modo_teste": False,
            "lado_id": lado_id,
            "acoes": acoes[:5],
        }

    def _acao_ataque(self, partida, pokemon, inimigos, rodada, rng):
        ataques = self._ataques(pokemon)
        candidatos = []
        for ataque in ataques:
            props = self.buscar_propriedades_ataque(ataque)
            if not isinstance(props, dict):
                continue
            estilo = str(props.get("estilo_logico") or "").strip().lower()
            if estilo == "passivo" or estilo not in {"alvo", "ativo"}:
                continue
            if self._energia(pokemon) < _f(props.get("custo"), 0.0):
                continue
            if estilo == "ativo":
                candidatos.append((ataque, props, None))
                continue
            area_id = self._melhor_area_alvo(partida, pokemon, props, inimigos, rng)
            if area_id is not None:
                candidatos.append((ataque, props, area_id))
        if not candidatos:
            return None
        ataque, props, area_id = rng.choice(candidatos[:3])
        code = self._code_ataque(ataque, props)
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        alvo = None
        if area_id:
            alvo = {"tipo": str(alvo_cfg.get("tipo") or "area"), "area_id": area_id, "areas": self._areas_afetadas(area_id, props)}
        return {
            "tipo": "ataque",
            "estilo": str(props.get("estilo_logico") or "alvo"),
            "pokemon_id": self._pid(pokemon),
            "lado_id": self._lado(pokemon),
            "rodada": rodada,
            "ataque": {
                "ID": code,
                "Code": code,
                "nome": ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or props.get("nome"),
                "Tipo": ataque.get("Tipo") or ataque.get("tipo") or (props.get("parametros") or {}).get("tipo"),
            },
            "alvo": alvo,
        }

    def _acao_troca_simples(self, partida, pokemon, lado_id, rodada):
        if self._vida_percentual(pokemon) > 0.25:
            return None
        reserva = next((p for p in self._pokemons(partida) if self._lado(p) == lado_id and self._vivo(p) and self._reserva(p)), None)
        if reserva is None:
            return None
        return {
            "tipo": "troca_reserva",
            "estilo": "movimento",
            "pokemon_id": self._pid(pokemon),
            "pokemon_reserva_id": self._pid(reserva),
            "troca_reserva_id": self._pid(reserva),
            "lado_id": lado_id,
            "rodada": rodada,
            "origem": {"tipo": "area", "area_id": self._area_id(pokemon)},
            "destino": {"tipo": "reserva", "pokemon_id": self._pid(reserva)},
        }

    def _melhor_area_alvo(self, partida, pokemon, props, inimigos, rng):
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        exige_ocupada = bool(alvo_cfg.get("exige_area_ocupada"))
        for inimigo in inimigos:
            area_id = self._area_id(inimigo)
            if area_id and self._area_permitida(partida, pokemon, area_id, props):
                return area_id
        if exige_ocupada:
            return None
        areas = [
            str(a.get("id"))
            for a in self._areas(partida)
            if int(a.get("lado_id", -999)) != self._lado(pokemon)
            and self._area_permitida(partida, pokemon, a.get("id"), props)
        ]
        return rng.choice(areas) if areas else None

    def _area_permitida(self, partida, pokemon, area_id, props):
        area = self._area_por_id(partida, area_id)
        if not isinstance(area, dict):
            return False
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        if bool(alvo_cfg.get("exige_area_ocupada")) and not self._area_esta_ocupada(partida, area_id):
            return False
        permitidos = alvo_cfg.get("lados_permitidos")
        if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
            return True
        lado_area = int(area.get("lado_id", -999))
        lado_origem = self._lado(pokemon)
        area_origem = str(self._area_id(pokemon) or "")
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

    def buscar_propriedades_ataque(self, ataque):
        if not isinstance(ataque, dict):
            return None
        code = str(ataque.get("Code") or ataque.get("ID") or ataque.get("code") or "").strip()
        if code:
            try:
                code = str(int(float(code)))
            except (TypeError, ValueError):
                pass
            if code in self.propriedades_ataques:
                return self.propriedades_ataques.get(code)
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip().casefold()
        if nome:
            for item in self.propriedades_ataques.values():
                if str(item.get("nome") or "").strip().casefold() == nome:
                    return item
        return None

    def _carregar_propriedades_ataques(self):
        caminho = Path(__file__).resolve().parents[3] / "Dados" / "Pokemon Global Server - PropriedadesAtaques.json"
        if not caminho.exists():
            return {}
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ataques = dados.get("ataques") if isinstance(dados, dict) else {}
        return ataques if isinstance(ataques, dict) else {}

    def _seed_rodada(self, partida, rodada, lado_id):
        seed = self.seed_base if self.seed_base is not None else getattr(partida, "seed_partida", 0)
        return f"{seed}:{rodada}:{lado_id}"

    @staticmethod
    def _pokemons(partida):
        if hasattr(partida, "pokemons"):
            return list(getattr(partida, "pokemons", []) or [])
        if hasattr(partida, "pokemons_por_id"):
            return list(getattr(partida, "pokemons_por_id", {}).values())
        return []

    @staticmethod
    def _areas(partida):
        areas = getattr(partida, "areas", {})
        if isinstance(areas, dict):
            return list(areas.values())
        arena = getattr(partida, "arena", None)
        return list(getattr(arena, "_areas", []) or [])

    @staticmethod
    def _area_por_id(partida, area_id):
        areas = getattr(partida, "areas", {})
        if isinstance(areas, dict):
            return areas.get(str(area_id or ""))
        arena = getattr(partida, "arena", None)
        return arena.obter_area_por_id(area_id) if arena is not None and hasattr(arena, "obter_area_por_id") else None

    @staticmethod
    def _area_esta_ocupada(partida, area_id):
        if hasattr(partida, "pokemon_na_area"):
            return partida.pokemon_na_area(area_id) is not None
        arena = getattr(partida, "arena", None)
        return bool(arena.area_esta_ocupada(area_id)) if arena is not None and hasattr(arena, "area_esta_ocupada") else False

    @staticmethod
    def _pid(pokemon):
        return str(getattr(pokemon, "id_batalha", "") or "")

    @staticmethod
    def _lado(pokemon):
        return int(getattr(pokemon, "lado_id", getattr(pokemon, "LadoId", 0)) or 0)

    @staticmethod
    def _ativo(pokemon):
        return bool(getattr(pokemon, "ativo", getattr(pokemon, "Ativo", False)))

    @staticmethod
    def _reserva(pokemon):
        return bool(getattr(pokemon, "reserva", getattr(pokemon, "EmReserva", False)))

    @staticmethod
    def _vivo(pokemon):
        if hasattr(pokemon, "esta_vivo"):
            return bool(pokemon.esta_vivo())
        return bool(getattr(pokemon, "vivo", getattr(pokemon, "Vivo", False))) and _f(getattr(pokemon, "VidaAtual", 0.0), 0.0) > 0

    @staticmethod
    def _energia(pokemon):
        return _f(getattr(pokemon, "EnergiaAtual", getattr(pokemon, "Energia", 0.0)), 0.0)

    @staticmethod
    def _vida_percentual(pokemon):
        vida_max = getattr(pokemon, "VidaMax", None)
        if vida_max is None and hasattr(pokemon, "obter_atributo"):
            vida_max = pokemon.obter_atributo("Vida", 1.0)
        return _f(getattr(pokemon, "VidaAtual", 0.0), 0.0) / max(1.0, _f(vida_max, 1.0))

    @staticmethod
    def _area_id(pokemon):
        return getattr(pokemon, "area_id", getattr(pokemon, "AreaId", None))

    @staticmethod
    def _ataques(pokemon):
        return list(getattr(pokemon, "ataques", getattr(pokemon, "ListaAtaques", [])) or [])

    @staticmethod
    def _code_ataque(ataque, props):
        valor = ataque.get("Code") or ataque.get("ID") or ataque.get("code") or props.get("Code") or props.get("ID") or 0
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _areas_afetadas(area_id, props):
        area_id = str(area_id or "")
        if not area_id:
            return []
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        tipo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        try:
            idx = int(area_id[1:]) - 1
        except (ValueError, IndexError):
            return [area_id]
        prefixo = area_id[:1]
        row, col = idx // 3, idx % 3
        if tipo in {"linha", "fileira", "row", "line"}:
            return [f"{prefixo}{row * 3 + c + 1}" for c in range(3)]
        if tipo in {"coluna", "column"}:
            return [f"{prefixo}{r * 3 + col + 1}" for r in range(3)]
        return [area_id]