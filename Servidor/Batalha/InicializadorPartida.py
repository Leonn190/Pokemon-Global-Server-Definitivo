from __future__ import annotations

import copy

from Servidor.Batalha.PokemonBatalha import PokemonBatalha


def _i(valor, default=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


class InicializadorPartida:
    def __init__(self, partida):
        self.partida = partida

    def montar_areas(self):
        areas = {}
        for prefixo, lado_id, lado_visual in (("A", 50, "jogador"), ("I", 51, "inimigo")):
            for idx in range(1, 10):
                area_id = f"{prefixo}{idx}"
                areas[area_id] = {
                    "id": area_id,
                    "lado_id": lado_id,
                    "lado_visual": lado_visual,
                    "ocupante_id": None,
                }
        return areas

    def inicializar_lados(self, dados):
        lados = dados.get("lados")
        if isinstance(lados, dict):
            for chave, valor in lados.items():
                lid = _i(chave, _i((valor or {}).get("lado_id"), 0))
                if lid:
                    self.partida.lados[lid] = {"lado_id": lid, **(dict(valor) if isinstance(valor, dict) else {})}
        elif isinstance(lados, list):
            for item in lados:
                if isinstance(item, dict):
                    lid = _i(item.get("lado_id"), 0)
                else:
                    lid = _i(item, 0)
                    item = {"lado_id": lid}
                if lid:
                    self.partida.lados[lid] = dict(item)
        if not self.partida.lados:
            self.partida.lados = {
                50: {"lado_id": self.partida.ids_batalha.novo_id_lado(0), "lado_visual": "jogador"},
                51: {"lado_id": self.partida.ids_batalha.novo_id_lado(1), "lado_visual": "inimigo"},
            }

    def inicializar_inventarios(self, dados):
        inv = dados.get("inventario_jogador") if isinstance(dados.get("inventario_jogador"), dict) else dados.get("inventario")
        if isinstance(inv, dict):
            self.partida.inventarios_lado[int(self.partida.lado_jogador)] = copy.deepcopy(inv)
        inventarios = dados.get("inventarios_lado") if isinstance(dados.get("inventarios_lado"), dict) else {}
        for lado, inventario in inventarios.items():
            if isinstance(inventario, dict):
                self.partida.inventarios_lado[_i(lado, 0)] = copy.deepcopy(inventario)

    def coletar_pokemons_iniciais(self, dados):
        if isinstance(dados.get("pokemons"), dict):
            pokemons = list(dados["pokemons"].values())
            return self.randomizar_posicoes_teste(pokemons) if self.partida.modo_teste else pokemons
        if isinstance(dados.get("pokemons"), list):
            pokemons = list(dados["pokemons"])
            return self.randomizar_posicoes_teste(pokemons) if self.partida.modo_teste else pokemons
        time_jogador_slots = (dados.get("time_jogador") or {}).get("Slots") if isinstance(dados.get("time_jogador"), dict) else None
        time_inimigo = dados.get("time_inimigo") or dados.get("time_adversario")
        time_inimigo_slots = (time_inimigo or {}).get("Slots") if isinstance(time_inimigo, dict) else None
        saida = []
        fontes = [
            (50, time_jogador_slots if time_jogador_slots is not None else dados.get("pokemons_jogador")),
            (51, time_inimigo_slots if time_inimigo_slots is not None else (dados.get("pokemons_inimigo") or dados.get("pokemons_adversario"))),
        ]
        areas_por_lado = {50: [f"A{i}" for i in range(1, 10)], 51: [f"I{i}" for i in range(1, 10)]}
        for areas in areas_por_lado.values():
            self.partida.rng.shuffle(areas)
        areas_teste = [f"{prefixo}{i}" for prefixo in ("A", "I") for i in range(1, 10)]
        if self.partida.modo_teste:
            self.partida.rng.shuffle(areas_teste)
        for lado_id, lista in fontes:
            for idx, pokemon in enumerate(list(lista or []), start=1):
                if not isinstance(pokemon, dict):
                    continue
                item = copy.deepcopy(pokemon)
                item.setdefault("lado_id", lado_id)
                item.setdefault("ativo", idx <= 3)
                item.setdefault("em_reserva", idx > 3)
                if idx <= 3:
                    if self.partida.modo_teste:
                        item["area_id"] = areas_teste.pop(0) if areas_teste else (("A" if int(lado_id) == 50 else "I") + str(idx))
                    elif not item.get("area_id"):
                        areas_lado = areas_por_lado.get(int(lado_id), [])
                        item["area_id"] = areas_lado.pop(0) if areas_lado else (("A" if int(lado_id) == 50 else "I") + str(idx))
                saida.append(item)
        return saida

    def randomizar_posicoes_teste(self, pokemons):
        areas = [f"{prefixo}{i}" for prefixo in ("A", "I") for i in range(1, 10)]
        self.partida.rng.shuffle(areas)
        saida = []
        for bruto in list(pokemons or []):
            if not isinstance(bruto, dict):
                saida.append(bruto)
                continue
            item = copy.deepcopy(bruto)
            ativo = bool(item.get("ativo", item.get("Ativo", False)))
            reserva = bool(item.get("em_reserva", item.get("reserva", item.get("EmReserva", False))))
            if ativo and not reserva and areas:
                item["area_id"] = areas.pop(0)
            saida.append(item)
        return saida

    def inicializar_pokemons(self, dados):
        pokemons = self.coletar_pokemons_iniciais(dados)
        por_lado_ativos = {}
        for indice, bruto in enumerate(pokemons, start=1):
            if not isinstance(bruto, dict):
                continue
            lado_id = _i(bruto.get("lado_id"), 50 if indice <= 6 else 51)
            self.partida.lados.setdefault(lado_id, {"lado_id": lado_id})
            pokemon = PokemonBatalha(bruto, partida=self.partida, lado_id=lado_id, indice=indice)
            if int(lado_id) == int(self.partida.lado_jogador):
                pct = float(self.partida.perfil_jogador.get("energia_inicial_pokemon_percent", self.partida.perfil_jogador.get("EnergiaInicialPokemonPercent", 0.50)) or 0.50)
                energia_max = max(1.0, float(pokemon.obter_atributo("EneM", 1.0) if hasattr(pokemon, "obter_atributo") else getattr(pokemon, "EnergiaMax", 1.0)))
                pokemon.EnergiaAtual = max(0.0, min(energia_max, energia_max * max(0.0, pct)))
            self.partida.pokemons_por_id[pokemon.id_batalha] = pokemon
            self.partida.pokemons_por_lado.setdefault(lado_id, []).append(pokemon)
            if pokemon.ativo and not pokemon.reserva:
                por_lado_ativos[lado_id] = por_lado_ativos.get(lado_id, 0) + 1
                if not pokemon.area_id:
                    prefixo = "A" if lado_id == 50 else "I"
                    pokemon.area_id = f"{prefixo}{min(9, por_lado_ativos[lado_id])}"
                if not self.partida.area_existe(pokemon.area_id):
                    self.partida.avisos.append({"pokemon_id": pokemon.id_batalha, "motivo": "area_invalida_reserva", "area_id": pokemon.area_id})
                    pokemon.area_id = None
                    pokemon.ativo = False
                    pokemon.reserva = True
                    continue
                if self.partida.ocupacao_areas.get(pokemon.area_id):
                    self.partida.avisos.append({"pokemon_id": pokemon.id_batalha, "motivo": "ocupacao_duplicada_reserva", "area_id": pokemon.area_id})
                    pokemon.area_id = None
                    pokemon.ativo = False
                    pokemon.reserva = True
                    continue
                self.partida.ocupacao_areas[pokemon.area_id] = pokemon.id_batalha
                self.partida.areas[pokemon.area_id]["ocupante_id"] = pokemon.id_batalha
            else:
                pokemon.area_id = None
                pokemon.ativo = False
                pokemon.reserva = True
