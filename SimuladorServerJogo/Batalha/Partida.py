from __future__ import annotations

import copy
import json
import math
import random
import unicodedata
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from SimuladorServerJogo.Batalha.ColetorAcoes import ColetorAcoes
from SimuladorServerJogo.Batalha.ConstrutorLog import ConstrutorLog
from SimuladorServerJogo.Batalha.IDsBatalha import IDsBatalha
from SimuladorServerJogo.Batalha.ResolvedorFlags import ResolvedorFlags
from SimuladorServerJogo.Batalha.BatalhaIA.ControladorIABoss import ControladorIABoss
from SimuladorServerJogo.Batalha.BatalhaIA.ControladorIA import ControladorIA
from SimuladorServerJogo.Batalha.PokemonBatalha import PokemonBatalha
from SimuladorServerJogo.Batalha.RodadorTurno import RodadorTurno
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import materializar_pokemon
from SimuladorServerJogo.Mundo.ServicoInventario import ServicoInventario


TERRENO_DANO_INCENDIADA_PCT_VIDA = 0.02
TERRENO_DANO_CONTAMINADA_PCT_VIDA = 0.02
TERRENO_CURA_ABENCOADA_PCT_VIDA = 0.03


def _jsonavel(dados):
    return json.loads(json.dumps(dados, ensure_ascii=False))


def _i(valor, default=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _normalizar(valor):
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


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
        self.modo_teste = bool(dados.get("modo_teste", False))
        self.lado_jogador = int(dados.get("lado_jogador", 50) or 50)
        self.arena_contexto = dict(dados.get("arena") or {})
        self.regras = copy.deepcopy(dados.get("regras") or {}) if isinstance(dados.get("regras"), dict) else {}
        self.regras_mundo = copy.deepcopy(dados.get("regras_mundo") or {}) if isinstance(dados.get("regras_mundo"), dict) else {}
        for chave in ("centro", "largura", "altura", "arena_largura", "arena_altura", "origem", "tiles", "estruturas", "contexto_estadio", "tipo_estadio"):
            if chave in dados and chave not in self.arena_contexto:
                self.arena_contexto[chave] = copy.deepcopy(dados.get(chave))
        self.lados: dict[int, dict] = {}
        self.inventarios_lado: dict[int, dict] = {}
        self.pokemons_capturados_lado: dict[int, list[dict]] = {}
        self._servico_inventario = ServicoInventario()
        self.ids_batalha = IDsBatalha()
        self.resolvedor_flags = ResolvedorFlags()
        self.pokemons_por_id = {}
        self.pokemons_por_lado: dict[int, list[PokemonBatalha]] = {}
        self.areas = self._montar_areas()
        self.ocupacao_areas = {area_id: None for area_id in self.areas}
        self.jogadas_recebidas = {}
        self.clima_atual = dados.get("clima_atual")
        self.clima_turnos_ativo = int(dados.get("clima_turnos_ativo", 0) or 0)
        self._ultimo_passo_raios = 0
        self.efeitos_area = copy.deepcopy(dados.get("efeitos_area") or {})
        self.construtos = {}
        self.finalizada = False
        self.vencedor = None
        self.perdedor = None
        self.motivo_finalizacao = None
        self.avisos = []
        self.coletor_acoes = ColetorAcoes(self)
        self.controlador_ia = self._criar_controlador_ia() if self.batalha_usa_ia() else None
        self.rodador_turno = RodadorTurno(self)
        self.construtor_log = ConstrutorLog(self)
        self._ia_executor = None
        self._ia_futures = {}
        self._desabilitar_thread_ia = False
        self._inicializar_lados(dados)
        self._inicializar_inventarios(dados)
        self._inicializar_pokemons(dados)
        self._registrar_passivas_pokemon()
        self.verificar_fim_batalha()
        self._iniciar_planejamento_ia_background()

    def _registrar_passivas_pokemon(self):
        try:
            from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ControladorExecutes import obter_passivas_ataque
        except Exception:
            return
        passivas = list(obter_passivas_ataque() or [])
        if not passivas:
            return
        for pokemon in self.pokemons_por_id.values():
            for passiva in passivas:
                code = str(passiva.get("code") or "")
                if code and not any(str((a or {}).get("Code") or (a or {}).get("ID") or "") == code for a in list(getattr(pokemon, "ataques", []) or [])):
                    continue
                self.resolvedor_flags.registrar_passiva(
                    nome=passiva.get("nome"),
                    flag=passiva.get("flag"),
                    grupo=passiva.get("grupo"),
                    func=passiva.get("func"),
                    origem=passiva.get("origem"),
                    dono=pokemon,
                    code=passiva.get("code"),
                )
        for pokemon in self.pokemons_por_id.values():
            self.disparar_flag("AoRegistrarPassiva", {"partida": self, "pokemon_evento": pokemon, "usuario": pokemon, "alvo": pokemon})

    def __getstate__(self):
        estado = dict(self.__dict__)
        estado["_ia_executor"] = None
        estado["_ia_futures"] = {}
        estado["_desabilitar_thread_ia"] = True
        return estado

    def __setstate__(self, estado):
        self.__dict__.update(estado)
        self._ia_executor = None
        self._ia_futures = {}
        self._desabilitar_thread_ia = True

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
                50: {"lado_id": self.ids_batalha.novo_id_lado(0), "lado_visual": "jogador"},
                51: {"lado_id": self.ids_batalha.novo_id_lado(1), "lado_visual": "inimigo"},
            }

    def _inicializar_inventarios(self, dados):
        inv = dados.get("inventario_jogador") if isinstance(dados.get("inventario_jogador"), dict) else dados.get("inventario")
        if isinstance(inv, dict):
            self.inventarios_lado[int(self.lado_jogador)] = copy.deepcopy(inv)
        inventarios = dados.get("inventarios_lado") if isinstance(dados.get("inventarios_lado"), dict) else {}
        for lado, inventario in inventarios.items():
            if isinstance(inventario, dict):
                self.inventarios_lado[_i(lado, 0)] = copy.deepcopy(inventario)

    def novo_id_pokemon(self, lado_id):
        return self.ids_batalha.novo_id_pokemon(lado_id)

    def novo_id_ataque(self, lado_id=None):
        return self.ids_batalha.novo_id_ataque(lado_id)

    def novo_id_acao(self, lado_id=None):
        return self.ids_batalha.novo_id_acao(lado_id)

    def novo_id_evento(self):
        return self.ids_batalha.novo_id_evento(self.rodada_atual)

    def novo_id_log(self):
        return self.ids_batalha.novo_id_log(self.rodada_atual)

    def disparar_flag(self, flag, contexto, reativos=None):
        eventos = self.resolvedor_flags.disparar(flag, contexto, reativos=reativos)
        for evento in list(eventos or []):
            self.registrar_evento_log(evento.get("tipo"), evento)
        return eventos

    def _coletar_pokemons_iniciais(self, dados):
        if isinstance(dados.get("pokemons"), dict):
            pokemons = list(dados["pokemons"].values())
            return self._randomizar_posicoes_teste(pokemons) if self.modo_teste else pokemons
        if isinstance(dados.get("pokemons"), list):
            pokemons = list(dados["pokemons"])
            return self._randomizar_posicoes_teste(pokemons) if self.modo_teste else pokemons
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
            self.rng.shuffle(areas)
        areas_teste = [f"{prefixo}{i}" for prefixo in ("A", "I") for i in range(1, 10)]
        if self.modo_teste:
            self.rng.shuffle(areas_teste)
        for lado_id, lista in fontes:
            for idx, pokemon in enumerate(list(lista or []), start=1):
                if not isinstance(pokemon, dict):
                    continue
                item = copy.deepcopy(pokemon)
                item.setdefault("lado_id", lado_id)
                item.setdefault("ativo", idx <= 3)
                item.setdefault("em_reserva", idx > 3)
                if idx <= 3:
                    if self.modo_teste:
                        item["area_id"] = areas_teste.pop(0) if areas_teste else (("A" if int(lado_id) == 50 else "I") + str(idx))
                    elif not item.get("area_id"):
                        areas_lado = areas_por_lado.get(int(lado_id), [])
                        item["area_id"] = areas_lado.pop(0) if areas_lado else (("A" if int(lado_id) == 50 else "I") + str(idx))
                saida.append(item)
        return saida

    def _randomizar_posicoes_teste(self, pokemons):
        areas = [f"{prefixo}{i}" for prefixo in ("A", "I") for i in range(1, 10)]
        self.rng.shuffle(areas)
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
            "clima_turnos_ativo": self.clima_turnos_ativo,
            "efeitos_area": copy.deepcopy(self.efeitos_area),
            "finalizada": bool(self.finalizada),
            "vencedor": self.vencedor,
            "perdedor": self.perdedor,
        }
        inv_jogador = self.inventarios_lado.get(int(self.lado_jogador))
        if isinstance(inv_jogador, dict):
            estado["inventario_jogador"] = copy.deepcopy(inv_jogador)
        if self.regras:
            estado["regras"] = copy.deepcopy(self.regras)
        if self.regras_mundo:
            estado["regras_mundo"] = copy.deepcopy(self.regras_mundo)
        return _jsonavel(estado)

    def mudar_clima(self, nome, origem=None, dados=None):
        antes = self.clima_atual
        self.clima_atual = nome
        self.clima_turnos_ativo = 0
        self.registrar_evento_log(
            "clima_alterado",
            {
                "clima_antes": antes,
                "clima_depois": nome,
                "clima": nome,
                "origem_id": getattr(origem, "id_batalha", None),
                "origem_nome": getattr(origem, "nome", None),
                **(dict(dados or {})),
            },
        )
        self.disparar_flag("AoMudarClima", {"partida": self, "usuario": origem, "pokemon_evento": origem, "clima_antes": antes, "clima_depois": nome})
        return {"aplicado": True, "clima_antes": antes, "clima_depois": nome}

    def limpar_clima(self, motivo=None):
        antes = self.clima_atual
        if not antes:
            return False
        self.clima_atual = None
        self.clima_turnos_ativo = 0
        self.registrar_evento_log("clima_expirou", {"clima": antes, "motivo": motivo or "expirou"})
        return True

    def aplicar_variacoes_temporarias_clima(self, pokemon):
        clima = _normalizar(self.clima_atual)
        if pokemon is None or not pokemon.esta_vivo():
            return
        tipos = {_normalizar(t) for t in getattr(pokemon, "tipos", [])}
        if clima == "nevasca" and "gelo" in tipos:
            pokemon.aplicar_variacao_temporaria("Def", pokemon.atributos_base.get("Def", 0.0) * 0.30)
            pokemon.aplicar_variacao_temporaria("SpD", pokemon.atributos_base.get("SpD", 0.0) * 0.30)
        elif clima in {"tempestadedeareia", "tempestadeareia"}:
            if "terra" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
        elif clima == "nevoa":
            pokemon.aplicar_variacao_temporaria("Assertividade", -30.0)
            if "fantasma" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
        elif clima == "gravidadeanomala":
            if "cosmico" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
            bonus = min(32, math.floor(float(getattr(pokemon, "dados_originais", {}).get("Peso", getattr(pokemon, "dados_originais", {}).get("peso", 0)) or 0) / 50.0) * 4)
            if bonus > 0:
                pokemon.aplicar_variacao_temporaria("Def", pokemon.atributos_base.get("Def", 0.0) * bonus / 100.0)
                pokemon.aplicar_variacao_temporaria("SpD", pokemon.atributos_base.get("SpD", 0.0) * bonus / 100.0)
        elif clima in {"tempestadederaios", "tempestaderaios"} and "eletrico" in tipos:
            pokemon.aplicar_variacao_temporaria("Ene", max(1.0, pokemon.atributos_base.get("Ene", 1.0)) * 0.50)
        elif clima == "noitedensa":
            if "sombrio" in tipos:
                pokemon.aplicar_variacao_temporaria("Vel", pokemon.atributos_base.get("Vel", 0.0) * 0.25)
            else:
                pokemon.aplicar_variacao_temporaria("Acuracia", -pokemon.atributos_base.get("Acuracia", 100.0) * 0.25)

    def aplicar_clima_em_pokemon_por_passo(self, pokemon):
        clima = _normalizar(self.clima_atual)
        if pokemon is None or not pokemon.esta_vivo():
            return
        tipos = {_normalizar(t) for t in getattr(pokemon, "tipos", [])}
        vida = pokemon.obter_atributo("Vida", 1.0)
        if clima == "chuva" and "gelo" in tipos:
            pokemon.ReceberCura(vida * 0.01, dados={"efeito": "Chuva"})
        elif clima == "solforte" and "gelo" in tipos:
            pokemon.ReceberDano(vida * 0.01, dados={"efeito": "Sol Forte", "ignorar_defensivos": True})
        elif clima in {"tempestadedeareia", "tempestadeareia"} and not (tipos & {"terra", "metal", "pedra"}):
            pokemon.ReceberDano(vida * 0.02, dados={"efeito": "Tempestade de Areia", "ignorar_defensivos": True})
        elif clima == "gravidadeanomala" and pokemon.possui_efeito("Voando"):
            pokemon.ReceberDano(vida * 0.02, dados={"efeito": "Gravidade Anomala", "ignorar_defensivos": True})
        elif clima == "chuvaacida":
            if "venenoso" in tipos or "veneno" in tipos:
                pokemon.ReceberCura(vida * 0.01, dados={"efeito": "Chuva Acida"})
            else:
                pokemon.ReceberDano(vida * 0.01, dados={"efeito": "Chuva Acida", "ignorar_defensivos": True})

    def aplicar_modificadores_dano_clima(self, tipo_ataque, dano):
        clima = _normalizar(self.clima_atual)
        tipo = _normalizar(tipo_ataque)
        mult = 1.0
        if clima == "chuva":
            mult = 1.25 if tipo == "agua" else 0.75 if tipo == "fogo" else 1.0
        elif clima == "solforte":
            mult = 0.75 if tipo == "agua" else 1.25 if tipo == "fogo" else 1.0
        return max(0.0, float(dano or 0.0)) * mult, mult

    def processar_fim_de_turno_clima(self):
        if not self.clima_atual:
            return False
        self.clima_turnos_ativo += 1
        chance = min(100.0, 10.0 + max(0, self.clima_turnos_ativo - 1) * 5.0)
        if self.rng.random() * 100.0 <= chance:
            return self.limpar_clima(motivo="rng_fim_turno")
        return False

    def processar_clima_por_passo(self):
        if _normalizar(self.clima_atual) not in {"tempestadederaios", "tempestaderaios"}:
            return
        if self.passo_atual <= 0 or self.passo_atual % 2 != 0 or self._ultimo_passo_raios == self.passo_atual:
            return
        self._ultimo_passo_raios = self.passo_atual
        por_lado = {}
        for area_id, area in self.areas.items():
            por_lado.setdefault(int(area.get("lado_id", 0)), []).append(area_id)
        for lado_id, areas in por_lado.items():
            area_id = self.rng.choice(list(areas))
            self.registrar_evento_log("clima_raio_area", {"clima": self.clima_atual, "lado_id": lado_id, "area_id": area_id})
            alvo = self.pokemon_na_area(area_id)
            if alvo is not None and alvo.esta_vivo():
                dano = alvo.obter_atributo("Vida", 1.0) * 0.35
                alvo.ReceberDano(dano, dados={"efeito": "Tempestade de Raios", "ignorar_defensivos": True})

    def mudar_terreno(self, area_id, terreno, origem=None, dados=None):
        area_id = str(area_id or "").upper()
        if not self.area_existe(area_id):
            return False
        antes = self.efeitos_area.get(area_id)
        self.efeitos_area[area_id] = {"terreno": terreno, "nome": terreno, **(dict(dados or {}))}
        self.registrar_evento_log("terreno_alterado", {"area_id": area_id, "terreno_antes": antes, "terreno": terreno, "origem_id": getattr(origem, "id_batalha", None)})
        ocupante = self.pokemon_na_area(area_id)
        if ocupante is not None:
            self.aplicar_terreno_ao_entrar(ocupante, area_id, dados=dados)
        return True

    def limpar_terreno(self, area_id, motivo=None):
        area_id = str(area_id or "").upper()
        terreno = self.efeitos_area.pop(area_id, None)
        if terreno is None:
            return False
        self.registrar_evento_log("terreno_removido", {"area_id": area_id, "terreno": terreno, "motivo": motivo})
        return True

    def obter_terreno_area(self, area_id):
        dado = self.efeitos_area.get(str(area_id or "").upper())
        if isinstance(dado, dict):
            return dado.get("terreno") or dado.get("nome") or dado.get("efeito")
        return dado

    def aplicar_terreno_ao_entrar(self, pokemon, area_id, dados=None):
        dados = dict(dados or {})
        terreno_bruto = self.obter_terreno_area(area_id)
        terreno = _normalizar(terreno_bruto)
        if pokemon is None or not pokemon.esta_vivo():
            return
        if terreno:
            self.disparar_flag(
                "AoEntrarEmTerreno",
                {
                    "partida": self,
                    "pokemon_evento": pokemon,
                    "alvo": pokemon,
                    "area_id": str(area_id or "").upper(),
                    "terreno": terreno_bruto,
                    "dados": dict(dados),
                    "reativos_acao": dados.get("reativos_acao"),
                },
                reativos=dados.get("reativos_acao"),
            )
        if terreno == "contaminada":
            pokemon.ReceberEfeito({"nome": "Envenenado", "duracao": 3, "negativo": True}, origem=pokemon, dados={"terreno": "Contaminada"})
            self.registrar_evento_log("terreno_aplicou_efeito", {"area_id": area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Contaminada", "efeito": "Envenenado"})

    def aplicar_terreno_por_passo(self, pokemon):
        terreno = _normalizar(self.obter_terreno_area(getattr(pokemon, "area_id", None)))
        if pokemon is None or not pokemon.esta_vivo():
            return
        vida = pokemon.obter_atributo("Vida", 1.0)
        if terreno == "incendiada":
            pokemon.ReceberDano(vida * TERRENO_DANO_INCENDIADA_PCT_VIDA, dados={"efeito": "Terreno Incendiada", "ignorar_defensivos": True})
            self.registrar_evento_log("terreno_tickou", {"area_id": pokemon.area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Incendiada"})
        elif terreno == "contaminada":
            pokemon.ReceberDano(vida * TERRENO_DANO_CONTAMINADA_PCT_VIDA, dados={"efeito": "Terreno Contaminada", "ignorar_defensivos": True})
            self.registrar_evento_log("terreno_tickou", {"area_id": pokemon.area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Contaminada"})
        elif terreno == "abencoada":
            pokemon.ReceberCura(vida * TERRENO_CURA_ABENCOADA_PCT_VIDA, dados={"efeito": "Terreno Abencoada"})
            self.registrar_evento_log("terreno_tickou", {"area_id": pokemon.area_id, "pokemon_id": pokemon.id_batalha, "terreno": "Abencoada"})

    def aplicar_variacoes_temporarias_terreno(self, pokemon):
        terreno = _normalizar(self.obter_terreno_area(getattr(pokemon, "area_id", None)))
        if pokemon is None or not pokemon.esta_vivo():
            return
        if terreno == "destruida":
            pokemon.aplicar_variacao_temporaria("Amp", -15.0)
            pokemon.aplicar_variacao_temporaria("Dur", -15.0)
        elif terreno == "energizada":
            pokemon.aplicar_variacao_temporaria("Ene", pokemon.atributos_base.get("Ene", 1.0))
        elif terreno == "sagrada":
            pokemon.aplicar_variacao_temporaria("Amp", 30.0)
        elif terreno == "elevada":
            pokemon.aplicar_variacao_temporaria("Acuracia", 35.0)
            pokemon.aplicar_variacao_temporaria("Assertividade", -15.0)

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
            self._atualizar_inventario_por_jogada(lado, jogada)
        except Exception as exc:
            return {"status": "erro", "mensagem": "Jogada invalida", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": [], "erros": [str(exc)]}
        if bool((jogada or {}).get("resolver_lados_ausentes")):
            self._completar_lados_ausentes_com_jogadas_vazias(modo_teste=False)
        self._completar_lados_ia()
        if not self.todos_lados_prontos():
            self.estado_partida = "aguardando"
            return {"status": "ok", "mensagem": "Jogada recebida", "id_partida": self.id_partida, "estado_batalha": "aguardando", "avisos": [], "erros": []}
        return self.resolver_rodada()

    def _atualizar_inventario_por_jogada(self, lado, jogada):
        if not isinstance(jogada, dict):
            return
        inv = jogada.get("inventario_jogador") if isinstance(jogada.get("inventario_jogador"), dict) else jogada.get("inventario")
        if isinstance(inv, dict):
            self.inventarios_lado[int(lado)] = copy.deepcopy(inv)

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

    def batalha_usa_ia(self):
        tipo = str(self.tipo_batalha or "").strip().lower()
        return tipo in {"confronto", "treinador", "trainer", "servo", "boss"} and not bool(self.modo_teste)

    def _criar_controlador_ia(self):
        return ControladorIABoss() if str(self.tipo_batalha or "").strip().lower() == "boss" else ControladorIA()

    def _completar_lados_ia(self):
        if not self.batalha_usa_ia():
            return
        if self.controlador_ia is None:
            self.controlador_ia = self._criar_controlador_ia()
        for lado in sorted(self._lados_com_pokemon_vivo()):
            if int(lado) == int(self.lado_jogador) or lado in self.jogadas_recebidas:
                continue
            self.jogadas_recebidas[int(lado)] = _jsonavel(self._obter_jogada_ia_final(int(lado)))

    def _iniciar_planejamento_ia_background(self):
        if not self.batalha_usa_ia() or self.finalizada or self.estado_partida != "montando_jogada":
            return
        if bool(getattr(self, "_desabilitar_thread_ia", False)):
            return
        if self.controlador_ia is None:
            self.controlador_ia = self._criar_controlador_ia()
        if self._ia_executor is None:
            self._ia_executor = ThreadPoolExecutor(max_workers=1)
        rodada = int(self.rodada_atual or 1)
        for lado in sorted(self._lados_com_pokemon_vivo()):
            lado = int(lado)
            if lado == int(self.lado_jogador) or lado in self.jogadas_recebidas:
                continue
            chave = (rodada, lado)
            futuro = self._ia_futures.get(chave)
            if futuro is not None and not futuro.cancelled():
                continue
            self._ia_futures[chave] = self._ia_executor.submit(self.controlador_ia.gerar_jogada_base, self, lado)

    def _obter_jogada_ia_final(self, lado):
        lado = int(lado)
        rodada = int(self.rodada_atual or 1)
        chave = (rodada, lado)
        futuro = self._ia_futures.get(chave)
        jogada_base = None
        if futuro is not None:
            try:
                jogada_base = futuro.result(timeout=0)
            except TimeoutError:
                self.avisos.append({"motivo": "ia_base_nao_pronta_usou_fallback", "lado_id": lado, "rodada": rodada})
            except Exception as exc:
                self.avisos.append({"motivo": "ia_base_falhou_usou_fallback", "lado_id": lado, "rodada": rodada, "erro": str(exc)})
        else:
            self.avisos.append({"motivo": "ia_base_sem_future_usou_fallback", "lado_id": lado, "rodada": rodada})
        if jogada_base is None:
            jogada_base = self.controlador_ia.gerar_jogada_fallback(self, lado, motivo="ia_base_nao_pronta_usou_fallback")
        return self.controlador_ia.finalizar_jogada_com_hacker(self, lado, jogada_base)

    def resolver_rodada(self):
        rodada_anterior = self.rodada_atual
        self.estado_partida = "resolvendo"
        self.avisos = list(self.avisos)
        self.construtor_log.iniciar_log_rodada(rodada_anterior)
        self.registrar_evento_log("rodada_iniciada", {"rodada": rodada_anterior}, passo=0)
        acoes, invalidas = self.coletor_acoes.coletar(self.jogadas_recebidas)
        for invalida in list(invalidas or []):
            self.registrar_evento_log("acao_falhou", dict(invalida), passo=0)
        resumo = self.rodador_turno.rodar(acoes, invalidas)
        self.aplicar_fim_de_rodada()
        self.registrar_evento_log("rodada_finalizada", {"rodada": rodada_anterior, "rodada_atual": self.rodada_atual}, passo=self.passo_atual)
        if self.finalizada:
            self.registrar_evento_log(
                "batalha_finalizada",
                {"vencedor": self.vencedor, "perdedor": self.perdedor, "estado_batalha": self.estado_partida},
                passo=self.passo_atual,
            )
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
        self.processar_fim_de_turno_clima()
        self.substituir_derrotados_por_reserva()
        self.verificar_fim_batalha()
        self.jogadas_recebidas = {}
        if not self.finalizada:
            self.rodada_atual += 1
            self.estado_partida = "montando_jogada"
            self._iniciar_planejamento_ia_background()
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
            self.motivo_finalizacao = self.motivo_finalizacao or "fim_normal"
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

    def registrar_evento_log(self, tipo, dados=None, passo=None, ordem=None):
        if getattr(self, "construtor_log", None) is None:
            return None
        return self.construtor_log.registrar_evento(tipo, dados=dados or {}, passo=passo, ordem=ordem)

    def obter_pokemon(self, id_pokemon):
        return self.pokemons_por_id.get(str(id_pokemon or ""))

    def obter_inventario_lado(self, lado_id):
        return self.inventarios_lado.setdefault(int(lado_id), {"itens": [], "pokemons": []})

    def tem_pokebola_batalha(self, lado_id, item_base_id=None, item_nome=None):
        inv = self.obter_inventario_lado(lado_id)
        alvo_code = str(item_base_id or "").strip().lower()
        alvo_nome = str(item_nome or "").strip().lower()
        for item in list(inv.get("itens") or []):
            if not isinstance(item, dict):
                continue
            code = str(item.get("Code") or item.get("code") or "").strip().lower()
            nome = str(item.get("Nome") or item.get("nome") or "").strip().lower()
            if alvo_code and code != alvo_code:
                continue
            if not alvo_code and alvo_nome and nome != alvo_nome:
                continue
            try:
                if int(item.get("quantidade", 1) or 1) > 0:
                    return True
            except (TypeError, ValueError):
                return True
        return False

    def consumir_pokebola_batalha(self, lado_id, item_base_id=None, item_nome=None):
        inv = self.obter_inventario_lado(lado_id)
        return self._servico_inventario.consumir_um(inv, str(item_base_id or ""), str(item_nome or ""))

    def adicionar_pokemon_capturado_batalha(self, lado_id, pokemon_snapshot):
        inv = self.obter_inventario_lado(lado_id)
        ok = self._servico_inventario.adicionar_pokemon_capturado(inv, dict(pokemon_snapshot or {}), {})
        if ok:
            self.pokemons_capturados_lado.setdefault(int(lado_id), []).append(copy.deepcopy(pokemon_snapshot))
        return ok

    def snapshot_pokemon_capturado_batalha(self, pokemon, efeitos_bola=None):
        dados = copy.deepcopy(getattr(pokemon, "dados_originais", {}) or {})
        estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else dados
        campos_batalha = (
            "id_batalha",
            "lado_id",
            "lado_visual",
            "ativo",
            "Ativo",
            "reserva",
            "em_reserva",
            "EmReserva",
            "area_id",
            "AreaId",
            "Energia",
            "EnergiaAtual",
            "BarreiraAtual",
            "efeitos",
            "efeitos_formais",
            "estados_transitorios",
            "contadores_especiais",
            "estatisticas_batalha",
        )
        for campo in campos_batalha:
            dados.pop(campo, None)
            estado.pop(campo, None)
        estado.setdefault("especie", getattr(pokemon, "especie", getattr(pokemon, "nome", "Pokemon")))
        estado.setdefault("nome", getattr(pokemon, "nome", estado.get("especie", "Pokemon")))
        estado.setdefault("nivel", getattr(pokemon, "nivel", 1))
        estado.setdefault("stats", copy.deepcopy(getattr(pokemon, "atributos_finais", {}) or {}))
        estado.setdefault("stats_base", copy.deepcopy(getattr(pokemon, "atributos_base", {}) or {}))
        tipos = list(getattr(pokemon, "tipos", []) or estado.get("tipos") or dados.get("tipos") or dados.get("Tipos") or [])
        ataques = copy.deepcopy(getattr(pokemon, "ataques", []) or estado.get("habilidades") or estado.get("ataques") or dados.get("ataques") or dados.get("ListaAtaques") or [])
        if tipos:
            estado["tipos"] = list(tipos)
            dados["tipos"] = list(tipos)
            dados["Tipos"] = list(tipos)
        if ataques:
            estado["habilidades"] = copy.deepcopy(ataques)
            estado["ataques"] = copy.deepcopy(ataques)
            dados["habilidades"] = copy.deepcopy(ataques)
            dados["ataques"] = copy.deepcopy(ataques)
            dados["ListaAtaques"] = copy.deepcopy(ataques)
        materializado = materializar_pokemon(dados, efeitos_captura=efeitos_bola if isinstance(efeitos_bola, dict) else None)
        saida_estado = materializado.get("estado") if isinstance(materializado.get("estado"), dict) else materializado
        for campo in campos_batalha:
            materializado.pop(campo, None)
            saida_estado.pop(campo, None)
        if tipos:
            saida_estado["tipos"] = list(tipos)
            materializado["tipos"] = list(tipos)
            materializado["Tipos"] = list(tipos)
        if ataques:
            saida_estado["habilidades"] = copy.deepcopy(ataques)
            saida_estado["ataques"] = copy.deepcopy(ataques)
            materializado["habilidades"] = copy.deepcopy(ataques)
            materializado["ataques"] = copy.deepcopy(ataques)
            materializado["ListaAtaques"] = copy.deepcopy(ataques)
        return materializado

    def remover_pokemon_capturado_batalha(self, pokemon):
        if pokemon is None:
            return False
        area = pokemon.area_id
        if self.area_existe(area) and self.ocupacao_areas.get(area) == pokemon.id_batalha:
            self.ocupacao_areas[area] = None
            self.areas[area]["ocupante_id"] = None
        pokemon.ativo = False
        pokemon.reserva = False
        pokemon.area_id = None
        pokemon.vivo = False
        pokemon.estados_transitorios["capturado"] = {"rodada": self.rodada_atual}
        return True

    def pokemon_na_area(self, area_id):
        pid = self.ocupacao_areas.get(str(area_id or ""))
        return self.obter_pokemon(pid)

    def area_existe(self, area_id):
        return str(area_id or "") in self.areas

    def mover_pokemon_para_area(self, pokemon, area_id, dados=None):
        area_id = str(area_id or "")
        dados = dict(dados or {})
        if pokemon is None or not self.area_existe(area_id):
            return False
        ocupante_id = self.ocupacao_areas.get(area_id)
        if ocupante_id and ocupante_id != pokemon.id_batalha:
            return False
        if pokemon.area_id in self.ocupacao_areas and self.ocupacao_areas.get(pokemon.area_id) == pokemon.id_batalha:
            self.ocupacao_areas[pokemon.area_id] = None
            self.areas[pokemon.area_id]["ocupante_id"] = None
        area_origem = pokemon.area_id
        pokemon.area_id = area_id
        pokemon.ativo = True
        pokemon.reserva = False
        self.ocupacao_areas[area_id] = pokemon.id_batalha
        self.areas[area_id]["ocupante_id"] = pokemon.id_batalha
        self.registrar_evento_log(
            "pokemon_moveu",
            {
                "pokemon_id": pokemon.id_batalha,
                "pokemon_nome": pokemon.nome,
                "area_origem": area_origem,
                "area_destino": area_id,
            },
        )
        self.disparar_flag(
            "AoMover",
            {
                "partida": self,
                "pokemon_evento": pokemon,
                "pokemon": pokemon,
                "area_antes": area_origem,
                "area_depois": area_id,
                "origem": dados.get("origem"),
                "dados": dict(dados),
                "reativos_acao": dados.get("reativos_acao"),
            },
            reativos=dados.get("reativos_acao"),
        )
        self.aplicar_terreno_ao_entrar(pokemon, area_id, dados=dados)
        return True

    def trocar_posicao(self, pokemon_a, pokemon_b, dados=None):
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
        self.registrar_evento_log(
            "pokemon_trocou_posicao",
            {
                "pokemon_a_id": pokemon_a.id_batalha,
                "pokemon_a_nome": pokemon_a.nome,
                "pokemon_b_id": pokemon_b.id_batalha,
                "pokemon_b_nome": pokemon_b.nome,
                "area_a_antes": area_a,
                "area_a_depois": area_b,
                "area_b_antes": area_b,
                "area_b_depois": area_a,
            },
        )
        dados = dict(dados or {})
        for pokemon, antes, depois in ((pokemon_a, area_a, area_b), (pokemon_b, area_b, area_a)):
            self.disparar_flag(
                "AoMover",
                {
                    "partida": self,
                    "pokemon_evento": pokemon,
                    "pokemon": pokemon,
                    "area_antes": antes,
                    "area_depois": depois,
                    "origem": dados.get("origem"),
                    "dados": dict(dados),
                    "reativos_acao": dados.get("reativos_acao"),
                },
                reativos=dados.get("reativos_acao"),
            )
        self.disparar_flag("AoTrocar", {"partida": self, "pokemon_evento": pokemon_a, "pokemon": pokemon_a, "pokemon_outro": pokemon_b, "reativos_acao": dados.get("reativos_acao")}, reativos=dados.get("reativos_acao"))
        self.aplicar_terreno_ao_entrar(pokemon_a, pokemon_a.area_id, dados=dados)
        self.aplicar_terreno_ao_entrar(pokemon_b, pokemon_b.area_id, dados=dados)
        return True

    def trocar_reserva(self, pokemon_ativo, pokemon_reserva, dados=None):
        if pokemon_ativo is None or pokemon_reserva is None:
            return False
        if int(pokemon_ativo.lado_id) != int(pokemon_reserva.lado_id):
            return False
        if not pokemon_ativo.ativo or pokemon_ativo.reserva or not pokemon_reserva.reserva:
            return False
        area = pokemon_ativo.area_id
        if not self.area_existe(area):
            return False
        reserva_slot_id = pokemon_reserva.id_batalha
        self.ocupacao_areas[area] = pokemon_reserva.id_batalha
        self.areas[area]["ocupante_id"] = pokemon_reserva.id_batalha
        pokemon_ativo.ativo = False
        pokemon_ativo.reserva = True
        pokemon_ativo.area_id = None
        pokemon_reserva.ativo = True
        pokemon_reserva.reserva = False
        pokemon_reserva.area_id = area
        pokemon_reserva.adicionar_estado_transitorio("entrou_na_rodada", {"rodada": self.rodada_atual})
        dados_troca = {
            "pokemon_saiu_id": pokemon_ativo.id_batalha,
            "pokemon_saiu_nome": pokemon_ativo.nome,
            "pokemon_entrou_id": pokemon_reserva.id_batalha,
            "pokemon_entrou_nome": pokemon_reserva.nome,
            "area_id": area,
            "slot_reserva_id": reserva_slot_id,
            "lado_id": pokemon_ativo.lado_id,
        }
        self.registrar_evento_log("pokemon_trocou_reserva", dados_troca)
        self.registrar_evento_log("pokemon_saiu", {"pokemon_id": pokemon_ativo.id_batalha, "pokemon_nome": pokemon_ativo.nome, "area_id": area, "slot_reserva_id": reserva_slot_id})
        self.registrar_evento_log("pokemon_entrou", {"pokemon_id": pokemon_reserva.id_batalha, "pokemon_nome": pokemon_reserva.nome, "area_id": area, "slot_reserva_id": reserva_slot_id})
        dados = dict(dados or {})
        self.disparar_flag(
            "AoMover",
            {
                "partida": self,
                "pokemon_evento": pokemon_reserva,
                "pokemon": pokemon_reserva,
                "area_antes": None,
                "area_depois": area,
                "origem": dados.get("origem"),
                "dados": dict(dados),
                "reativos_acao": dados.get("reativos_acao"),
            },
            reativos=dados.get("reativos_acao"),
        )
        self.disparar_flag("AoTrocar", {"partida": self, "pokemon_evento": pokemon_reserva, "pokemon": pokemon_reserva, "pokemon_outro": pokemon_ativo, "reativos_acao": dados.get("reativos_acao")}, reativos=dados.get("reativos_acao"))
        self.aplicar_terreno_ao_entrar(pokemon_reserva, area, dados=dados)
        return True

    def substituir_derrotados_por_reserva(self):
        for pokemon in list(self.pokemons_por_id.values()):
            if pokemon.esta_vivo() or pokemon.reserva or not pokemon.ativo:
                continue
            area = pokemon.area_id
            if self.area_existe(area) and self.ocupacao_areas.get(area) == pokemon.id_batalha:
                self.ocupacao_areas[area] = None
                self.areas[area]["ocupante_id"] = None
            pokemon.ativo = False
            pokemon.reserva = False
            pokemon.area_id = None
            reserva = next((p for p in self.pokemons_por_lado.get(int(pokemon.lado_id), []) if p.reserva and p.esta_vivo()), None)
            if reserva is None or not self.area_existe(area):
                continue
            reserva.ativo = True
            reserva.reserva = False
            reserva.area_id = area
            self.ocupacao_areas[area] = reserva.id_batalha
            self.areas[area]["ocupante_id"] = reserva.id_batalha
            self.registrar_evento_log(
                "pokemon_entrou",
                {"pokemon_id": reserva.id_batalha, "pokemon_nome": reserva.nome, "area_id": area, "motivo": "substituicao_derrotado"},
            )
            self.disparar_flag("AoMover", {"partida": self, "pokemon_evento": reserva, "pokemon": reserva, "area_antes": None, "area_depois": area, "origem": pokemon, "dados": {"motivo": "substituicao_derrotado"}})
            self.aplicar_terreno_ao_entrar(reserva, area)

    def finalizar(self, motivo=None, lado_id=None):
        motivo = str(motivo or "fim_normal")
        tipo_batalha = str(self.tipo_batalha or "").strip().lower()
        if motivo == "fuga" and (tipo_batalha == "boss" or (tipo_batalha == "servo" and int(self.rodada_atual or 1) <= 5)):
            return {"status": "erro", "mensagem": "Fuga bloqueada neste tipo de batalha", "id_partida": self.id_partida, "estado_finalizacao": self.estado_partida, "avisos": [], "erros": ["fuga_bloqueada_tipo_batalha"], "resultado": self.gerar_resultado_diff(self.rodada_atual)["resultado"]}
        self.finalizada = True
        self.motivo_finalizacao = motivo
        if motivo == "fuga":
            perdedor = _i(lado_id, self.lado_jogador)
            vencedores = [lado for lado in self._lados_com_pokemon_vivo() if int(lado) != int(perdedor)]
            self.perdedor = perdedor
            self.vencedor = vencedores[0] if len(vencedores) == 1 else vencedores
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
