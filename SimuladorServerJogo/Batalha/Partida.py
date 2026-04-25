from __future__ import annotations

import json
import random

from SimuladorServerJogo.Batalha.ColetorAcoes import ColetorAcoes
from SimuladorServerJogo.Batalha.ConstrutorLog import ConstrutorLog
from SimuladorServerJogo.Batalha.FraquezasResistencia import FraquezasResistencia
from SimuladorServerJogo.Batalha.PokemonBatalha import PokemonBatalha
from SimuladorServerJogo.Batalha.RodadorTurno import RodadorTurno


def _i(v, d=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


class Partida:
    def __init__(self, id_partida: str, dados_inicializacao: dict | None = None):
        dados = dict(dados_inicializacao or {})
        self.id_partida = str(id_partida)
        self.tipo_batalha = str(dados.get("tipo_batalha") or "simulador")
        self.seed_partida = int(dados.get("seed_partida") or random.randint(1, 999_999_999))
        self.rng = random.Random(self.seed_partida)
        self.rodada_atual = max(1, _i(dados.get("rodada_atual", dados.get("rodada", 1)), 1))
        self.passo_atual = 0
        self.estado_partida = "montando_jogada"
        self.lados = [int(l.get("lado_id", l)) if isinstance(l, dict) else int(l) for l in list(dados.get("lados") or [50, 51])]
        if not self.lados:
            self.lados = [50, 51]
        self.pokemons_por_id: dict[str, PokemonBatalha] = {}
        self.pokemons_por_lado = {int(l): [] for l in self.lados}
        self.areas = self._montar_areas(dados)
        self.ocupacao_areas = {aid: None for aid in self.areas}
        self.jogadas_recebidas = {}
        self.clima_atual = None
        self.efeitos_area = []
        self.construtos = []
        self.fr = FraquezasResistencia()
        self.coletor_acoes = ColetorAcoes(self)
        self.rodador_turno = RodadorTurno(self)
        self.construtor_log = ConstrutorLog(self)
        self.log_corrente = None
        self.finalizada = False
        self.vencedor = None
        self.perdedor = None
        self.avisos_inicializacao = []
        self._carregar_pokemons(dados)

    def _normalizar_serializavel(self, dados):
        try:
            return json.loads(json.dumps(dados, ensure_ascii=False)), []
        except Exception as exc:
            return None, [f"Pacote não serializável: {exc}"]

    def _montar_areas(self, dados):
        areas = {}
        entrada = list((dados.get("arena") or {}).get("areas") or [])
        if entrada:
            for a in entrada:
                aid = str(a.get("id") or "")
                if aid:
                    areas[aid] = {"id": aid, "lado_id": int(a.get("lado_id", 50 if aid.startswith("A") else 51))}
        for i in range(1, 10):
            areas.setdefault(f"A{i}", {"id": f"A{i}", "lado_id": 50})
            areas.setdefault(f"I{i}", {"id": f"I{i}", "lado_id": 51})
        return areas

    def _carregar_pokemons(self, dados):
        for item in list(dados.get("pokemons") or []):
            poke = PokemonBatalha(item, partida=self)
            if not poke.id_batalha:
                poke.id_batalha = f"p{len(self.pokemons_por_id)+1:04d}"
            self.pokemons_por_id[poke.id_batalha] = poke
            self.pokemons_por_lado.setdefault(poke.lado_id, []).append(poke.id_batalha)
            if poke.ativo and poke.area_id in self.ocupacao_areas and self.ocupacao_areas[poke.area_id] is None:
                self.ocupacao_areas[poke.area_id] = poke.id_batalha
            else:
                if poke.area_id and poke.area_id not in self.ocupacao_areas:
                    self.avisos_inicializacao.append(f"area_id inválida para {poke.id_batalha}; movido para reserva")
                elif poke.area_id and self.ocupacao_areas.get(poke.area_id):
                    self.avisos_inicializacao.append(f"ocupação duplicada em {poke.area_id}; {poke.id_batalha} movido para reserva")
                poke.area_id = None
                poke.ativo = False
                poke.reserva = True

    def serializar_estado_inicial(self):
        return self.serializar_estado()

    def serializar_estado(self):
        return {
            "id_partida": self.id_partida,
            "tipo_batalha": self.tipo_batalha,
            "seed_partida": self.seed_partida,
            "rodada_atual": self.rodada_atual,
            "lado_jogador": int(self.lados[0]) if self.lados else 50,
            "passo_atual": self.passo_atual,
            "estado_partida": self.estado_partida,
            "lados": [{"lado_id": l} for l in self.lados],
            "areas": {k: v["id"] for k, v in self.areas.items()},
            "ocupacao_areas": dict(self.ocupacao_areas),
            "pokemons": [p.serializar() for p in self.pokemons_por_id.values()],
            "arena": {"areas": [{"id": a, "lado_id": v.get("lado_id")} for a, v in self.areas.items()]},
        }

    def receber_jogada(self, lado_id, jogada):
        lado = int(lado_id)
        if lado not in self.lados:
            return {"status": "erro", "mensagem": "lado_id inválido", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": [], "erros": ["lado_invalido"]}
        normalizado, falhas = self._normalizar_serializavel(jogada)
        if falhas:
            return {"status": "erro", "mensagem": "Jogada inválida", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "avisos": [], "erros": falhas}
        self.jogadas_recebidas[lado] = normalizado
        if not self.todos_lados_prontos():
            self.estado_partida = "aguardando"
            return {"status": "ok", "mensagem": "Jogada recebida", "id_partida": self.id_partida, "estado_batalha": "aguardando", "avisos": [], "erros": []}
        return self.resolver_rodada()

    def receber_jogadas_modo_teste(self, jogadas):
        itens = list(jogadas or [])
        for item in itens:
            if not isinstance(item, dict):
                continue
            lado = int(item.get("lado_id", -1))
            if lado in self.lados:
                self.jogadas_recebidas[lado] = item
        if len({l for l in self.jogadas_recebidas if l in self.lados}) < len(self.lados):
            self.estado_partida = "aguardando"
            return {"status": "ok", "mensagem": "Aguardando outros lados", "id_partida": self.id_partida, "estado_batalha": "aguardando", "avisos": [], "erros": []}
        return self.resolver_rodada()

    def todos_lados_prontos(self):
        return all(lado in self.jogadas_recebidas for lado in self.lados)

    def resolver_rodada(self):
        acoes_validas, acoes_invalidas = self.coletor_acoes.coletar()
        log = self.rodador_turno.rodar(acoes_validas, acoes_invalidas=acoes_invalidas)
        self.rodada_atual += 1
        self.estado_partida = "finalizada" if self.finalizada else "montando_jogada"
        self.jogadas_recebidas = {}
        return {"status": "ok", "mensagem": "Rodada resolvida", "id_partida": self.id_partida, "estado_batalha": self.estado_partida, "log": log, "avisos": [], "erros": []}

    def aplicar_fim_de_rodada(self):
        for p in self.pokemons_por_id.values():
            regen = p.atributos_finais.get("Ene", 0.0)
            if p.possui_efeito("Descarregado"):
                regen *= 0.5
            if p.possui_efeito("Energizado"):
                regen *= 1.5
            p.GanharEnergia(regen)
            p.limpar_transitorios_fim_rodada()
            p.Verificar()

    def verificar_fim_batalha(self):
        vivos_por_lado = {}
        for lado, ids in self.pokemons_por_lado.items():
            vivos_por_lado[lado] = any(self.pokemons_por_id[p].esta_vivo() for p in ids if p in self.pokemons_por_id)
        lados_vivos = [lado for lado, vivo in vivos_por_lado.items() if vivo]
        if len(lados_vivos) <= 1:
            self.finalizada = True
            self.vencedor = lados_vivos[0] if lados_vivos else None
            self.perdedor = next((l for l in self.lados if l != self.vencedor), None)

    def gerar_resultado_diff(self):
        return {
            "rodada_anterior": self.rodada_atual - 1,
            "rodada_atual": self.rodada_atual,
            "lado_jogador": int(self.lados[0]) if self.lados else 50,
            "estado_batalha": "finalizada" if self.finalizada else "montando_jogada",
            "finalizada": self.finalizada,
            "vencedor": self.vencedor,
            "perdedor": self.perdedor,
            "pokemons": {pid: p.serializar() for pid, p in self.pokemons_por_id.items()},
            "areas": dict(self.ocupacao_areas),
            "lados": [{"lado_id": l} for l in self.lados],
            "avisos": [],
        }

    def obter_pokemon(self, id_pokemon):
        return self.pokemons_por_id.get(str(id_pokemon or ""))

    def pokemon_na_area(self, area_id):
        pid = self.ocupacao_areas.get(str(area_id))
        return self.obter_pokemon(pid)

    def mover_pokemon_para_area(self, pokemon, area_id):
        area = str(area_id or "")
        if area not in self.areas:
            return False
        if pokemon.area_id in self.ocupacao_areas and self.ocupacao_areas[pokemon.area_id] == pokemon.id_batalha:
            self.ocupacao_areas[pokemon.area_id] = None
        self.ocupacao_areas[area] = pokemon.id_batalha
        pokemon.area_id = area
        pokemon.ativo = True
        pokemon.reserva = False
        return True

    def trocar_posicao(self, pokemon_a, pokemon_b):
        area_a, area_b = pokemon_a.area_id, pokemon_b.area_id
        if area_a not in self.areas or area_b not in self.areas:
            return False
        self.ocupacao_areas[area_a], self.ocupacao_areas[area_b] = pokemon_b.id_batalha, pokemon_a.id_batalha
        pokemon_a.area_id, pokemon_b.area_id = area_b, area_a
        return True

    def trocar_reserva(self, pokemon_ativo, pokemon_reserva):
        area = pokemon_ativo.area_id
        if area not in self.areas:
            return False
        self.ocupacao_areas[area] = pokemon_reserva.id_batalha
        pokemon_reserva.area_id = area
        pokemon_reserva.ativo = True
        pokemon_reserva.reserva = False
        pokemon_ativo.area_id = None
        pokemon_ativo.ativo = False
        pokemon_ativo.reserva = True
        return True

    def obter_linha_area(self, area_id):
        aid = str(area_id or "")
        if len(aid) < 2:
            return [aid]
        prefixo = aid[0]
        try:
            n = int(aid[1:])
        except ValueError:
            return [aid]
        row = ((n - 1) // 3) + 1
        return [f"{prefixo}{(row-1)*3 + c}" for c in (1, 2, 3)]

    def obter_adjacentes_mesmo_lado(self, area_id):
        aid = str(area_id or "")
        if len(aid) < 2:
            return []
        prefixo = aid[0]
        n = int(aid[1:])
        r, c = (n - 1) // 3, (n - 1) % 3
        saida = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < 3 and 0 <= cc < 3:
                    saida.append(f"{prefixo}{rr*3+cc+1}")
        return saida

    def finalizar(self, motivo=None):
        self.finalizada = True
        self.estado_partida = "finalizada"
        return {"status": "ok", "mensagem": f"Partida finalizada: {motivo or 'sem motivo'}", "id_partida": self.id_partida, "estado_finalizacao": self.estado_partida, "avisos": [], "erros": []}
