from __future__ import annotations

import copy
import json
import random
import uuid

from SimuladorServerJogo.Batalha.ColetorAcoes import ColetorAcoes
from SimuladorServerJogo.Batalha.ConstrutorLog import ConstrutorLog
from SimuladorServerJogo.Batalha.PokemonBatalha import PokemonBatalha
from SimuladorServerJogo.Batalha.RodadorTurno import RodadorTurno


def _jsonavel(dados):
    return json.loads(json.dumps(dados, ensure_ascii=False))


def _i(valor, default=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


class Partida:
    def __init__(self, id_partida: str | None = None, dados_inicializacao: dict | None = None):
        dados = dict(dados_inicializacao or {})
        self.id_partida = str(id_partida or dados.get("id_partida") or uuid.uuid4().hex)
        self.tipo_batalha = str(dados.get("tipo_batalha") or dados.get("tipo") or "simulador")
        self.seed_partida = int(dados.get("seed_partida") or dados.get("seed") or random.SystemRandom().randint(1, 999999999))
        self.rng = random.Random(self.seed_partida)
        self.rodada_atual = int(dados.get("rodada_atual", dados.get("rodada", 1)) or 1)
        self.passo_atual = 0
        self.estado_partida = "montando_jogada"
        self.lado_jogador = int(dados.get("lado_jogador", 50) or 50)
        self.arena_contexto = dict(dados.get("arena") or {})
        self.regras = copy.deepcopy(dados.get("regras") or {}) if isinstance(dados.get("regras"), dict) else {}
        self.regras_mundo = copy.deepcopy(dados.get("regras_mundo") or {}) if isinstance(dados.get("regras_mundo"), dict) else {}
        for chave in ("centro", "largura", "altura", "arena_largura", "arena_altura", "origem", "tiles", "estruturas"):
            if chave in dados and chave not in self.arena_contexto:
                self.arena_contexto[chave] = copy.deepcopy(dados.get(chave))
        self.lados: dict[int, dict] = {}
        self.pokemons_por_id = {}
        self.pokemons_por_lado: dict[int, list[PokemonBatalha]] = {}
        self.areas = self._montar_areas()
        self.ocupacao_areas = {area_id: None for area_id in self.areas}
        self.jogadas_recebidas = {}
        self.clima_atual = dados.get("clima_atual")
        self.efeitos_area = copy.deepcopy(dados.get("efeitos_area") or {})
        self.construtos = {}
        self.finalizada = False
        self.vencedor = None
        self.perdedor = None
        self.avisos = []
        self.coletor_acoes = ColetorAcoes(self)
        self.rodador_turno = RodadorTurno(self)
        self.construtor_log = ConstrutorLog(self)
        self._inicializar_lados(dados)
        self._inicializar_pokemons(dados)
        self.verificar_fim_batalha()

    def _montar_areas(self):
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

    def _inicializar_lados(self, dados):
        lados = dados.get("lados")
        if isinstance(lados, dict):
            for chave, valor in lados.items():
                lid = _i(chave, _i((valor or {}).get("lado_id"), 0))
                if lid:
                    self.lados[lid] = {"lado_id": lid, **(dict(valor) if isinstance(valor, dict) else {})}
        elif isinstance(lados, list):
            for item in lados:
                if isinstance(item, dict):
                    lid = _i(item.get("lado_id"), 0)
                else:
                    lid = _i(item, 0)
                    item = {"lado_id": lid}
                if lid:
                    self.lados[lid] = dict(item)
        if not self.lados:
            self.lados = {
                50: {"lado_id": 50, "lado_visual": "jogador"},
                51: {"lado_id": 51, "lado_visual": "inimigo"},
            }

    def _coletar_pokemons_iniciais(self, dados):
        if isinstance(dados.get("pokemons"), dict):
            return list(dados["pokemons"].values())
        if isinstance(dados.get("pokemons"), list):
            return list(dados["pokemons"])
        saida = []
        fontes = [
            (50, dados.get("pokemons_jogador")),
            (51, dados.get("pokemons_inimigo") or dados.get("pokemons_adversario")),
            (50, (dados.get("time_jogador") or {}).get("Slots") if isinstance(dados.get("time_jogador"), dict) else None),
            (51, (dados.get("time_inimigo") or dados.get("time_adversario") or {}).get("Slots") if isinstance(dados.get("time_inimigo") or dados.get("time_adversario"), dict) else None),
        ]
        for lado_id, lista in fontes:
            for idx, pokemon in enumerate(list(lista or []), start=1):
                if not isinstance(pokemon, dict):
                    continue
                item = copy.deepcopy(pokemon)
                item.setdefault("lado_id", lado_id)
                item.setdefault("ativo", idx <= 3)
                item.setdefault("em_reserva", idx > 3)
                if idx <= 3 and not item.get("area_id"):
                    item["area_id"] = ("A" if int(lado_id) == 50 else "I") + str(idx)
                saida.append(item)
        return saida

    def _inicializar_pokemons(self, dados):
        pokemons = self._coletar_pokemons_iniciais(dados)
        por_lado_ativos = {}
        for indice, bruto in enumerate(pokemons, start=1):
            if not isinstance(bruto, dict):
                continue
            lado_id = _i(bruto.get("lado_id"), 50 if indice <= 6 else 51)
            self.lados.setdefault(lado_id, {"lado_id": lado_id})
            pokemon = PokemonBatalha(bruto, partida=self, lado_id=lado_id, indice=indice)
            self.pokemons_por_id[pokemon.id_batalha] = pokemon
            self.pokemons_por_lado.setdefault(lado_id, []).append(pokemon)
            if pokemon.ativo and not pokemon.reserva:
                por_lado_ativos[lado_id] = por_lado_ativos.get(lado_id, 0) + 1
                if not pokemon.area_id:
                    prefixo = "A" if lado_id == 50 else "I"
                    pokemon.area_id = f"{prefixo}{min(9, por_lado_ativos[lado_id])}"
                if not self.area_existe(pokemon.area_id):
                    self.avisos.append({"pokemon_id": pokemon.id_batalha, "motivo": "area_invalida_reserva", "area_id": pokemon.area_id})
                    pokemon.area_id = None
                    pokemon.ativo = False
                    pokemon.reserva = True
                    continue
                if self.ocupacao_areas.get(pokemon.area_id):
                    self.avisos.append({"pokemon_id": pokemon.id_batalha, "motivo": "ocupacao_duplicada_reserva", "area_id": pokemon.area_id})
                    pokemon.area_id = None
                    pokemon.ativo = False
                    pokemon.reserva = True
                    continue
                self.ocupacao_areas[pokemon.area_id] = pokemon.id_batalha
                self.areas[pokemon.area_id]["ocupante_id"] = pokemon.id_batalha
            else:
                pokemon.area_id = None
                pokemon.ativo = False
                pokemon.reserva = True

    def serializar_estado_inicial(self):
        return self.serializar_estado()

    def serializar_estado(self):
        estado = {
            "id_partida": self.id_partida,
            "tipo_batalha": self.tipo_batalha,
            "seed_partida": self.seed_partida,
            "rodada_atual": self.rodada_atual,
            "estado_batalha": self.estado_partida,
            "lado_jogador": self.lado_jogador,
            "lados": [dict(v) for v in self.lados.values()],
            "arena": {**copy.deepcopy(self.arena_contexto), "areas": list(self.areas.values())},
            "areas": copy.deepcopy(self.areas),
            "ocupacao_areas": dict(self.ocupacao_areas),
            "pokemons": [pokemon.serializar() for pokemon in self.pokemons_por_id.values()],
            "clima_atual": self.clima_atual,
            "efeitos_area": copy.deepcopy(self.efeitos_area),
            "finalizada": bool(self.finalizada),
            "vencedor": self.vencedor,
            "perdedor": self.perdedor,
        }
        if self.regras:
            estado["regras"] = copy.deepcopy(self.regras)
        if self.regras_mundo:
            estado["regras_mundo"] = copy.deepcopy(self.regras_mundo)
        return _jsonavel(estado)

    def receber_jogada(self, lado_id, jogada):
        if self.finalizada:
            resultado = self.gerar_resultado_diff(self.rodada_atual)
            return {
                "status": "ok",
                "mensagem": "Batalha finalizada",
                "id_partida": self.id_partida,
                "estado_batalha": "finalizada",
                "resultado": resultado["resultado"],
                "log": resultado,
                "avisos": [],
                "erros": [],
            }
        lado = _i(lado_id, -1)
        if lado not in self.lados:
            return {"status": "erro", "mensagem": "Lado inexistente", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": [], "erros": ["lado_inexistente"]}
        try:
            self.jogadas_recebidas[lado] = _jsonavel(jogada if isinstance(jogada, dict) else {})
        except Exception as exc:
            return {"status": "erro", "mensagem": "Jogada invalida", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": [], "erros": [str(exc)]}
        if bool((jogada or {}).get("resolver_lados_ausentes")):
            self._completar_lados_ausentes_com_jogadas_vazias(modo_teste=False)
        if not self.todos_lados_prontos():
            self.estado_partida = "aguardando"
            return {"status": "ok", "mensagem": "Jogada recebida", "id_partida": self.id_partida, "estado_batalha": "aguardando", "avisos": [], "erros": []}
        return self.resolver_rodada()

    def receber_jogadas_modo_teste(self, jogadas):
        if not isinstance(jogadas, list):
            return {"status": "erro", "mensagem": "Jogadas invalidas", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": [], "erros": ["jogadas_modo_teste_devem_ser_lista"]}
        for item in jogadas:
            if not isinstance(item, dict):
                self.avisos.append({"motivo": "jogada_modo_teste_ignorada"})
                continue
            lado = _i(item.get("lado_id"), -1)
            if lado in self.lados:
                self.jogadas_recebidas[lado] = _jsonavel(item)
        self._completar_lados_ausentes_com_jogadas_vazias(modo_teste=True)
        if not self.todos_lados_prontos():
            self.estado_partida = "aguardando"
            return {"status": "ok", "mensagem": "Jogada recebida", "id_partida": self.id_partida, "estado_batalha": "aguardando", "avisos": list(self.avisos), "erros": []}
        return self.resolver_rodada()

    def todos_lados_prontos(self):
        lados_com_pokemon = self._lados_com_pokemon_vivo()
        lados_necessarios = lados_com_pokemon or set(self.lados.keys())
        return all(lado in self.jogadas_recebidas for lado in lados_necessarios)

    def _lados_com_pokemon_vivo(self):
        return {lado for lado, pokes in self.pokemons_por_lado.items() if any(p.esta_vivo() for p in pokes)}

    def _completar_lados_ausentes_com_jogadas_vazias(self, modo_teste=False):
        for lado in self._lados_com_pokemon_vivo():
            self.jogadas_recebidas.setdefault(lado, {"lado_id": lado, "acoes": [], "modo_teste": bool(modo_teste)})

    def resolver_rodada(self):
        rodada_anterior = self.rodada_atual
        self.estado_partida = "resolvendo"
        self.avisos = list(self.avisos)
        acoes, invalidas = self.coletor_acoes.coletar(self.jogadas_recebidas)
        resumo = self.rodador_turno.rodar(acoes, invalidas)
        self.aplicar_fim_de_rodada()
        resultado = self.gerar_resultado_diff(rodada_anterior, resumo)
        return {
            "status": "ok",
            "mensagem": "Rodada resolvida",
            "id_partida": self.id_partida,
            "estado_batalha": self.estado_partida,
            "resultado": resultado["resultado"],
            "log": resultado,
            "avisos": list(resultado["resultado"].get("avisos") or []),
            "erros": [],
        }

    def aplicar_fim_de_rodada(self):
        for pokemon in self.pokemons_por_id.values():
            if not pokemon.esta_vivo():
                continue
            ganho = pokemon.obter_atributo("Ene", 0.0)
            if pokemon.possui_efeito("Energizado"):
                ganho *= 1.25
            if pokemon.possui_efeito("Descarregado"):
                ganho *= 0.75
            pokemon.GanharEnergia(ganho, dados={"fim_rodada": True})
            pokemon.limpar_transitorios_fim_rodada()
        self.verificar_fim_batalha()
        self.jogadas_recebidas = {}
        if not self.finalizada:
            self.rodada_atual += 1
            self.estado_partida = "montando_jogada"
        else:
            self.estado_partida = "finalizada"

    def verificar_fim_batalha(self):
        vivos_por_lado = {
            lado: any(p.esta_vivo() for p in pokemons)
            for lado, pokemons in self.pokemons_por_lado.items()
        }
        if len(vivos_por_lado) < 2:
            return False
        derrotados = [lado for lado, tem_vivo in vivos_por_lado.items() if not tem_vivo]
        if derrotados:
            vencedores = [lado for lado, tem_vivo in vivos_por_lado.items() if tem_vivo]
            self.finalizada = True
            self.perdedor = derrotados[0] if len(derrotados) == 1 else derrotados
            self.vencedor = vencedores[0] if len(vencedores) == 1 else vencedores
            self.estado_partida = "finalizada"
            return True
        return False

    def gerar_resultado_diff(self, rodada_anterior=None, resumo=None):
        resumo = dict(resumo or {})
        avisos = list(self.avisos) + list(resumo.get("avisos") or [])
        return self.construtor_log.construir_resultado(
            rodada_anterior=int(rodada_anterior or self.rodada_atual),
            avisos=avisos,
            erros_acoes=resumo.get("erros_acoes") or [],
            acoes_falhas=resumo.get("acoes_falhas") or [],
        )

    def obter_pokemon(self, id_pokemon):
        return self.pokemons_por_id.get(str(id_pokemon or ""))

    def pokemon_na_area(self, area_id):
        pid = self.ocupacao_areas.get(str(area_id or ""))
        return self.obter_pokemon(pid)

    def area_existe(self, area_id):
        return str(area_id or "") in self.areas

    def mover_pokemon_para_area(self, pokemon, area_id):
        area_id = str(area_id or "")
        if pokemon is None or not self.area_existe(area_id):
            return False
        ocupante_id = self.ocupacao_areas.get(area_id)
        if ocupante_id and ocupante_id != pokemon.id_batalha:
            return False
        if pokemon.area_id in self.ocupacao_areas and self.ocupacao_areas.get(pokemon.area_id) == pokemon.id_batalha:
            self.ocupacao_areas[pokemon.area_id] = None
            self.areas[pokemon.area_id]["ocupante_id"] = None
        pokemon.area_id = area_id
        pokemon.ativo = True
        pokemon.reserva = False
        self.ocupacao_areas[area_id] = pokemon.id_batalha
        self.areas[area_id]["ocupante_id"] = pokemon.id_batalha
        return True

    def trocar_posicao(self, pokemon_a, pokemon_b):
        if pokemon_a is None or pokemon_b is None:
            return False
        if not pokemon_a.ativo or not pokemon_b.ativo or pokemon_a.reserva or pokemon_b.reserva:
            return False
        if int(pokemon_a.lado_id) != int(pokemon_b.lado_id):
            return False
        area_a, area_b = pokemon_a.area_id, pokemon_b.area_id
        if not self.area_existe(area_a) or not self.area_existe(area_b):
            return False
        pokemon_a.area_id, pokemon_b.area_id = area_b, area_a
        self.ocupacao_areas[area_a] = pokemon_b.id_batalha
        self.ocupacao_areas[area_b] = pokemon_a.id_batalha
        self.areas[area_a]["ocupante_id"] = pokemon_b.id_batalha
        self.areas[area_b]["ocupante_id"] = pokemon_a.id_batalha
        return True

    def trocar_reserva(self, pokemon_ativo, pokemon_reserva):
        if pokemon_ativo is None or pokemon_reserva is None:
            return False
        if int(pokemon_ativo.lado_id) != int(pokemon_reserva.lado_id):
            return False
        if not pokemon_ativo.ativo or pokemon_ativo.reserva or not pokemon_reserva.reserva:
            return False
        area = pokemon_ativo.area_id
        if not self.area_existe(area):
            return False
        self.ocupacao_areas[area] = pokemon_reserva.id_batalha
        self.areas[area]["ocupante_id"] = pokemon_reserva.id_batalha
        pokemon_ativo.ativo = False
        pokemon_ativo.reserva = True
        pokemon_ativo.area_id = None
        pokemon_reserva.ativo = True
        pokemon_reserva.reserva = False
        pokemon_reserva.area_id = area
        pokemon_reserva.adicionar_estado_transitorio("entrou_na_rodada", {"rodada": self.rodada_atual})
        return True

    def finalizar(self, motivo=None):
        self.finalizada = True
        self.estado_partida = "finalizada"
        return {
            "status": "ok",
            "mensagem": f"Partida finalizada: {motivo or 'sem motivo'}",
            "id_partida": self.id_partida,
            "estado_finalizacao": self.estado_partida,
            "avisos": [],
            "erros": [],
            "resultado": self.gerar_resultado_diff(self.rodada_atual)["resultado"],
        }
