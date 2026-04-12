from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Dict, List

from SimuladorServerJogo.Batalha.IA.BotBatalha import BotBatalha
from SimuladorServerJogo.Batalha.PokemonBatalha import PokemonBatalha


_BASE_DADOS = Path(__file__).resolve().parents[2] / "Dados"


class SistemaBatalha:
    _CACHE_ATAQUES: Dict[str, Dict[str, object]] | None = None
    _CACHE_EFEITOS: Dict[str, Dict[str, object]] | None = None
    _CACHE_EQUIPAVEIS: Dict[str, Dict[str, object]] | None = None
    _CACHE_FLUXOS: Dict[str, Dict[str, object]] | None = None

    def __init__(self, batalha_id: str, client_id: str, contexto: Dict[str, object] | None = None) -> None:
        self.BatalhaId = str(batalha_id)
        self.ClienteDono = str(client_id)
        self.Contexto = dict(contexto or {})
        self.Tipo = str(self.Contexto.get("tipo") or "confronto").strip().lower()
        self.TurnoAtual = 1
        self.TickGlobal = 0
        self.ClimaAtual = str(self.Contexto.get("clima") or "")
        self.ArenaAtual: Dict[str, object] = {}
        self.Rng = random.Random(f"{self.BatalhaId}:{self.ClienteDono}")

        self.PokemonsPorId: Dict[str, PokemonBatalha] = {}
        self.Lados: Dict[str, Dict[str, object]] = {
            "jogador": {"todos": [], "ativos": [], "reservas": [], "cliente_id": str(client_id)},
            "inimigo": {"todos": [], "ativos": [], "reservas": [], "cliente_id": str(self.Contexto.get("client_id_inimigo") or "ia")},
        }
        self.HistoricoJogadas: List[Dict[str, object]] = []
        self.JogadasPendentes: Dict[str, List[Dict[str, object]]] = {}
        self.LogsTurnos: List[Dict[str, object]] = []
        self.UltimoLogTurno: Dict[str, object] = {}
        self.BotsIA: Dict[str, BotBatalha] = {}

        self.BibliotecaAtaques = self._carregar_ataques()
        self.BibliotecaEfeitos = self._carregar_efeitos()
        self.BibliotecaEquipaveis = self._carregar_equipaveis()
        self.BibliotecaFluxos = self._carregar_fluxos()

        self._inicializar_pokemons()

    @staticmethod
    def _norm(valor: object) -> str:
        return str(valor or "").strip().casefold()

    @staticmethod
    def _fnum(valor, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @classmethod
    def _ler_csv(cls, nome_arquivo: str) -> List[Dict[str, object]]:
        caminho = _BASE_DADOS / nome_arquivo
        if not caminho.exists():
            return []
        with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
            return [dict(row) for row in csv.DictReader(arquivo)]

    @classmethod
    def _carregar_ataques(cls) -> Dict[str, Dict[str, object]]:
        if cls._CACHE_ATAQUES is not None:
            return cls._CACHE_ATAQUES
        saida: Dict[str, Dict[str, object]] = {}
        for row in cls._ler_csv("Pokemon Global Server - Ataques.csv"):
            nome = str(row.get("Ataque") or row.get("Nome") or "").strip()
            if not nome:
                continue
            dados = dict(row)
            try:
                dados["Custo"] = float(dados.get("Custo", 0) or 0)
            except (TypeError, ValueError):
                dados["Custo"] = 0.0
            try:
                dados["Nivel"] = int(float(dados.get("Nivel", 1) or 1))
            except (TypeError, ValueError):
                dados["Nivel"] = 1
            saida[cls._norm(nome)] = dados
        cls._CACHE_ATAQUES = saida
        return saida

    @classmethod
    def _carregar_efeitos(cls) -> Dict[str, Dict[str, object]]:
        if cls._CACHE_EFEITOS is not None:
            return cls._CACHE_EFEITOS
        saida: Dict[str, Dict[str, object]] = {}
        for row in cls._ler_csv("Pokemon Global Server - Efeitos.csv"):
            nome = str(row.get("Efeito") or row.get("Nome") or "").strip()
            if not nome:
                continue
            saida[cls._norm(nome)] = dict(row)
        cls._CACHE_EFEITOS = saida
        return saida

    @classmethod
    def _carregar_equipaveis(cls) -> Dict[str, Dict[str, object]]:
        if cls._CACHE_EQUIPAVEIS is not None:
            return cls._CACHE_EQUIPAVEIS
        saida: Dict[str, Dict[str, object]] = {}
        for row in cls._ler_csv("Pokemon Global Server - Equipaveis.csv"):
            nome = str(row.get("Nome") or row.get("Equipavel") or row.get("Equipável") or "").strip()
            if not nome:
                continue
            saida[cls._norm(nome)] = dict(row)
        cls._CACHE_EQUIPAVEIS = saida
        return saida

    @classmethod
    def _normalizar_fluxo(cls, fluxo: Dict[str, object]) -> Dict[str, object]:
        dado = dict(fluxo or {})
        if "ricocheteia_objetos" not in dado:
            dado["ricocheteia_objetos"] = bool(dado.get("ricocheteia_paredes", False))
        if "atravessa_objetos" not in dado:
            dado["atravessa_objetos"] = bool(dado.get("atravessa_paredes", False))
        return dado

    @classmethod
    def _carregar_fluxos(cls) -> Dict[str, Dict[str, object]]:
        if cls._CACHE_FLUXOS is not None:
            return cls._CACHE_FLUXOS
        caminho = _BASE_DADOS / "Pokemon Global Server - Fluxos.json"
        saida: Dict[str, Dict[str, object]] = {}
        if caminho.exists():
            bruto = json.loads(caminho.read_text(encoding="utf-8-sig"))
            for nome, dados in dict(bruto.get("fluxos") or {}).items():
                if not isinstance(dados, dict):
                    continue
                pacote = dict(dados)
                pacote["fluxos"] = [cls._normalizar_fluxo(item) for item in list(pacote.get("fluxos") or []) if isinstance(item, dict)]
                saida[cls._norm(nome)] = pacote
        cls._CACHE_FLUXOS = saida
        return saida

    def _enriquecer_ataque(self, ataque: Dict[str, object] | None) -> Dict[str, object]:
        if not isinstance(ataque, dict):
            return {}
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
        base = dict(self.BibliotecaAtaques.get(self._norm(nome), {}))
        base.update(dict(ataque))
        if nome:
            base.setdefault("Ataque", nome)
            base.setdefault("Nome", nome)
        return base

    def _copiar_pokemon_dict(self, bruto: Dict[str, object]) -> Dict[str, object]:
        pokemon = dict(bruto or {})
        estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
        habilidades = []
        for ataque in list(estado.get("habilidades") or pokemon.get("habilidades") or pokemon.get("ataques") or []):
            if not ataque:
                continue
            if isinstance(ataque, dict):
                habilidades.append(self._enriquecer_ataque(ataque))
            else:
                habilidades.append(self._enriquecer_ataque({"Ataque": str(ataque)}))
        if habilidades:
            estado["habilidades"] = habilidades
        build = []
        for item in list(estado.get("build") or estado.get("itens_build") or pokemon.get("build") or pokemon.get("itens_build") or []):
            if isinstance(item, dict):
                nome_item = str(item.get("Nome") or item.get("nome") or item.get("Equipavel") or item.get("equipavel") or "").strip()
                base_item = dict(self.BibliotecaEquipaveis.get(self._norm(nome_item), {}))
                base_item.update(dict(item))
                build.append(base_item if base_item else dict(item))
            elif str(item).strip():
                build.append(dict(self.BibliotecaEquipaveis.get(self._norm(item), {"Nome": str(item)})))
        if build:
            estado["build"] = build
        return pokemon

    def _pontos_lado_arena(self, lado: str, total: int) -> List[tuple[float, float]]:
        centro = self.Contexto.get("centro") if isinstance(self.Contexto.get("centro"), (list, tuple)) and len(self.Contexto.get("centro")) == 2 else [40.0, 20.0]
        largura = float(self.Contexto.get("arena_largura", 40) or 40)
        altura = float(self.Contexto.get("arena_altura", 20) or 20)
        cx, cy = float(centro[0]), float(centro[1])
        margem_x = largura * 0.18
        margem_y = altura * 0.34
        x = cx - margem_x if lado == "jogador" else cx + margem_x
        if total <= 1:
            return [(x, cy)] if total == 1 else []
        passo = (margem_y * 2.0) / max(1, total - 1)
        return [(x, cy - margem_y + (indice * passo)) for indice in range(total)]

    def _inicializar_pokemons(self) -> None:
        for lado in ("jogador", "inimigo"):
            todos_brutos = [self._copiar_pokemon_dict(item) for item in list(self.Contexto.get(lado) or []) if isinstance(item, dict)]
            ativos_brutos = todos_brutos[:3]
            reservas_brutas = todos_brutos[3:]
            posicoes_ativos = self._pontos_lado_arena(lado, len(ativos_brutos))

            lado_estado = self.Lados[lado]
            for indice, bruto in enumerate(ativos_brutos):
                pokemon = PokemonBatalha(
                    bruto,
                    lado=lado,
                    posicao=posicoes_ativos[indice] if indice < len(posicoes_ativos) else (0.0, 0.0),
                    ativo=True,
                    slot_time=indice,
                    slot_ativo=indice,
                )
                self.PokemonsPorId[pokemon.Uid] = pokemon
                lado_estado["todos"].append(pokemon.Uid)
                lado_estado["ativos"].append(pokemon.Uid)

            for indice, bruto in enumerate(reservas_brutas, start=len(ativos_brutos)):
                pokemon = PokemonBatalha(
                    bruto,
                    lado=lado,
                    posicao=(-10.0, -10.0),
                    ativo=False,
                    slot_time=indice,
                    slot_ativo=-1,
                )
                self.PokemonsPorId[pokemon.Uid] = pokemon
                lado_estado["todos"].append(pokemon.Uid)
                lado_estado["reservas"].append(pokemon.Uid)

    def listar_pokemons(self) -> List[PokemonBatalha]:
        return list(self.PokemonsPorId.values())

    def listar_ativos(self, lado: str | None = None) -> List[PokemonBatalha]:
        if lado is not None:
            return [self.PokemonsPorId[uid] for uid in list(self.Lados.get(str(lado), {}).get("ativos") or []) if uid in self.PokemonsPorId]
        saida: List[PokemonBatalha] = []
        for nome_lado in ("jogador", "inimigo"):
            saida.extend(self.listar_ativos(nome_lado))
        return saida

    def obter_pokemon(self, pokemon_id: object) -> PokemonBatalha | None:
        return self.PokemonsPorId.get(str(pokemon_id or ""))

    def lado_do_cliente(self, client_id: str) -> str:
        client = str(client_id or "")
        for lado, dados in self.Lados.items():
            if str(dados.get("cliente_id") or "") == client:
                return lado
        return "jogador"

    def adicionar_jogadas(self, client_id: str, jogadas: List[Dict[str, object]]) -> None:
        client = str(client_id or "")
        lista = [dict(item) for item in list(jogadas or []) if isinstance(item, dict)]
        self.JogadasPendentes[client] = lista
        self.HistoricoJogadas.append(
            {
                "client_id": client,
                "turno": int(self.TurnoAtual),
                "tick_global": int(self.TickGlobal),
                "jogadas": [dict(item) for item in lista],
            }
        )

    def coletar_jogadas_pendentes_turno(self, client_id: str) -> tuple[str, List[Dict[str, object]]]:
        lado_cliente = self.lado_do_cliente(client_id)
        jogadas_cliente = [dict(item) for item in list(self.JogadasPendentes.get(str(client_id), []))]
        if self.Tipo in {"player", "pvp"}:
            outros = [uid for uid in self.JogadasPendentes.keys() if uid != str(client_id)]
            if not outros:
                return ("aguardando", jogadas_cliente)
            jogadas = []
            for valor in self.JogadasPendentes.values():
                jogadas.extend([dict(item) for item in list(valor or []) if isinstance(item, dict)])
            return ("pronto", jogadas)

        jogadas = list(jogadas_cliente)
        if lado_cliente == "jogador":
            jogadas.extend(self._gerar_jogadas_ia("inimigo"))
        else:
            jogadas.extend(self._gerar_jogadas_ia("jogador"))
        return ("pronto", jogadas)

    def _gerar_jogadas_ia(self, lado: str) -> List[Dict[str, object]]:
        bot = self.BotsIA.get(str(lado))
        if bot is None:
            bot = BotBatalha(rng=self.Rng)
            self.BotsIA[str(lado)] = bot
        return bot.escolher_jogadas(self, lado_controlado=lado)

    def substituir_ativo_por_reserva(self, executor_id: str, reserva_id: str) -> Dict[str, object]:
        executor = self.obter_pokemon(executor_id)
        reserva = self.obter_pokemon(reserva_id)
        if executor is None or reserva is None:
            return {"status": "erro", "mensagem": "Troca invalida"}
        if executor.Lado != reserva.Lado:
            return {"status": "erro", "mensagem": "Lados diferentes"}
        lado = self.Lados.get(executor.Lado, {})
        ativos = list(lado.get("ativos") or [])
        reservas = list(lado.get("reservas") or [])
        if executor.Uid not in ativos or reserva.Uid not in reservas:
            return {"status": "erro", "mensagem": "Troca indisponivel"}
        indice = ativos.index(executor.Uid)
        ativos[indice] = reserva.Uid
        reservas[reservas.index(reserva.Uid)] = executor.Uid
        lado["ativos"] = ativos
        lado["reservas"] = reservas
        executor.Ativo = False
        executor.SlotAtivo = -1
        reserva.Ativo = True
        reserva.SlotAtivo = indice
        posicoes = self._pontos_lado_arena(executor.Lado, len(ativos))
        if indice < len(posicoes):
            reserva.Posicao = posicoes[indice]
        return {"status": "ok", "saiu": executor.Uid, "entrou": reserva.Uid, "slot": indice}

    def avancar_turno(self, ultimo_log: Dict[str, object] | None = None) -> None:
        if isinstance(ultimo_log, dict):
            self.UltimoLogTurno = dict(ultimo_log)
            self.LogsTurnos.append(dict(ultimo_log))
            self.TickGlobal = max(int(self.TickGlobal), int(ultimo_log.get("tick_final", self.TickGlobal)))
        self.TurnoAtual += 1
        self.JogadasPendentes.clear()

    def estado_lado(self, lado: str) -> Dict[str, object]:
        dados = self.Lados.get(lado, {})
        return {
            "cliente_id": str(dados.get("cliente_id") or ""),
            "ativos": [self.PokemonsPorId[uid].serializar() for uid in list(dados.get("ativos") or []) if uid in self.PokemonsPorId],
            "reservas": [self.PokemonsPorId[uid].serializar() for uid in list(dados.get("reservas") or []) if uid in self.PokemonsPorId],
            "todos_ids": [str(uid) for uid in list(dados.get("todos") or [])],
        }

    def snapshot(self) -> Dict[str, object]:
        return {
            "batalha_id": self.BatalhaId,
            "tipo": self.Tipo,
            "turno_atual": int(self.TurnoAtual),
            "tick_global": int(self.TickGlobal),
            "clima": self.ClimaAtual,
            "arena": dict(self.ArenaAtual),
            "jogador": self.estado_lado("jogador"),
            "inimigo": self.estado_lado("inimigo"),
            "historico_tamanho": len(self.HistoricoJogadas),
            "ultimo_log_turno": dict(self.UltimoLogTurno or {}),
        }
