from __future__ import annotations

from typing import Any

from .ContextoIA import fnum


class FallbackIA:
    """Jogada segura caso a IA principal falhe.

    Prioridade:
    1. ataque simples válido;
    2. troca se o ativo estiver crítico;
    3. ação vazia mínima para não travar a rodada.
    """

    def __init__(self, propriedades_ataques: dict[str, dict] | None = None):
        self.propriedades_ataques = dict(propriedades_ataques or {})

    def gerar(self, partida, lado_id: int, rodada: int, rng, motivo: str = "fallback_ia") -> list[dict[str, Any]]:
        acoes: list[dict[str, Any]] = []
        ativos = [p for p in self._pokemons(partida) if self._lado(p) == lado_id and self._vivo(p) and self._ativo(p) and not self._reserva(p)]
        inimigos = [p for p in self._pokemons(partida) if self._lado(p) != lado_id and self._vivo(p) and self._ativo(p) and not self._reserva(p)]
        inimigos.sort(key=lambda p: (self._vida_percentual(p), str(self._pid(p))))

        for pokemon in ativos:
            if len(acoes) >= 5:
                break
            acao = self._fallback_ataque(partida, pokemon, inimigos, rodada, rng, motivo)
            if acao is not None:
                acoes.append(acao)
                continue
            acao = self._fallback_troca(partida, pokemon, lado_id, rodada, motivo)
            if acao is not None:
                acoes.append(acao)

        return acoes

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

    def _fallback_ataque(self, partida, pokemon, inimigos, rodada, rng, motivo):
        candidatos = []
        for ataque in self._ataques(pokemon):
            props = self.buscar_propriedades_ataque(ataque)
            if not isinstance(props, dict):
                continue
            estilo = str(props.get("estilo_logico") or "").strip().lower()
            if estilo == "passivo" or estilo not in {"alvo", "ativo"}:
                continue
            if self._energia(pokemon) < fnum(props.get("custo"), 0.0):
                continue
            if estilo == "ativo":
                candidatos.append((ataque, props, None))
                continue
            area_id = self._fallback_area_alvo(partida, pokemon, props, inimigos, rng)
            if area_id is not None:
                candidatos.append((ataque, props, area_id))
        if not candidatos:
            return None

        # Fallback também tenta matar com custo menor antes de qualquer coisa.
        candidatos.sort(key=lambda item: (fnum(item[1].get("custo"), 0.0), str(item[1].get("nome") or "")))
        ataque, props, area_id = candidatos[0]
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
            "origem_ia": True,
            "fallback_ia": True,
            "motivo_fallback": motivo,
        }

    def _fallback_troca(self, partida, pokemon, lado_id, rodada, motivo):
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
            "origem_ia": True,
            "fallback_ia": True,
            "motivo_fallback": motivo,
        }

    def _fallback_area_alvo(self, partida, pokemon, props, inimigos, rng):
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        exige_ocupada = bool(alvo_cfg.get("exige_area_ocupada"))
        permitidos = alvo_cfg.get("lados_permitidos") if isinstance(alvo_cfg.get("lados_permitidos"), (list, tuple, set)) else []
        quer_aliado = any(str(x).lower() in {"mesmo_lado", "aliado", "aliados", "proprio_lado", "usuario"} for x in permitidos)
        alvos = [p for p in self._pokemons(partida) if self._lado(p) == self._lado(pokemon) and self._vivo(p) and self._ativo(p) and not self._reserva(p)] if quer_aliado else inimigos
        alvos.sort(key=lambda p: (self._vida_percentual(p), str(self._pid(p))))
        for alvo in alvos:
            area_id = self._area_id(alvo)
            if area_id and self._area_permitida(partida, pokemon, area_id, props):
                return area_id
        if exige_ocupada:
            return None
        areas = [str(a.get("id")) for a in self._areas(partida) if self._area_permitida(partida, pokemon, a.get("id"), props)]
        return rng.choice(areas) if areas else None

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
        return []

    @staticmethod
    def _area_por_id(partida, area_id):
        areas = getattr(partida, "areas", {})
        if isinstance(areas, dict):
            return areas.get(str(area_id or ""))
        return None

    @staticmethod
    def _area_esta_ocupada(partida, area_id):
        if hasattr(partida, "pokemon_na_area"):
            return partida.pokemon_na_area(area_id) is not None
        area = FallbackIA._area_por_id(partida, area_id)
        return bool(area and area.get("ocupante_id"))

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

    @staticmethod
    def _pid(pokemon):
        return str(getattr(pokemon, "id_batalha", "") or "")

    @staticmethod
    def _lado(pokemon):
        try:
            return int(getattr(pokemon, "lado_id", getattr(pokemon, "LadoId", 0)) or 0)
        except (TypeError, ValueError):
            return 0

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
        return bool(getattr(pokemon, "vivo", getattr(pokemon, "Vivo", False))) and fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0) > 0

    @staticmethod
    def _energia(pokemon):
        return fnum(getattr(pokemon, "EnergiaAtual", getattr(pokemon, "Energia", 0.0)), 0.0)

    @staticmethod
    def _vida_percentual(pokemon):
        vida_max = getattr(pokemon, "VidaMax", None)
        if vida_max is None and hasattr(pokemon, "obter_atributo"):
            vida_max = pokemon.obter_atributo("Vida", 1.0)
        return fnum(getattr(pokemon, "VidaAtual", 0.0), 0.0) / max(1.0, fnum(vida_max, 1.0))

    @staticmethod
    def _area_id(pokemon):
        return getattr(pokemon, "area_id", getattr(pokemon, "AreaId", None))

    @staticmethod
    def _ataques(pokemon):
        return list(getattr(pokemon, "ataques", getattr(pokemon, "ListaAtaques", [])) or [])

    @staticmethod
    def _code_ataque(ataque, props):
        valor = ataque.get("ID") or ataque.get("Code") or ataque.get("code") or props.get("ID") or 0
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
