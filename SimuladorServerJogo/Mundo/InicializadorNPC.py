from __future__ import annotations

import csv
import math
import random
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado, subir_nivel_pokemon

Vector2 = Tuple[float, float]


class InicializadorNPC:
    VERSAO = 2

    def __init__(self, estado_mundo: Dict[str, object], velocidade_base: float = 4.5) -> None:
        self.estado_mundo = estado_mundo if isinstance(estado_mundo, dict) else {}
        self.meta = self.estado_mundo.get("meta", {}) if isinstance(self.estado_mundo.get("meta"), dict) else {}
        self.velocidade_base = float(velocidade_base)
        self.vilas = self._carregar_vilas()
        self.estadios = self._carregar_estadios()
        self.rotas = self._carregar_rotas()
        self.rotas_por_local = self._indexar_rotas()
        self.itens = self._carregar_itens()

    @staticmethod
    def slug(valor: object) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
        texto = "".join(ch if ch.isalnum() else "_" for ch in texto.strip().lower())
        while "__" in texto:
            texto = texto.replace("__", "_")
        return texto.strip("_")

    @staticmethod
    def normalizar_tipo_estadio(valor: str) -> str:
        base = InicializadorNPC.slug(valor)
        alias = {"terrestre": "terra", "eletrico": "eletrico", "psiquico": "psiquico", "agua": "agua", "dragao": "dragao"}
        return alias.get(base, base or "normal")

    @staticmethod
    def normalizar_skin(valor: object) -> str:
        skin = str(valor or "1").strip() or "1"
        if skin.lower().endswith(".png"):
            return skin
        if skin.lower().startswith("s") and skin[1:].isdigit():
            return f"{skin[1:]}.png"
        return f"{skin}.png"

    @staticmethod
    def inteiro(valor: object, padrao: int = 0) -> int:
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            return int(padrao)

    @staticmethod
    def numero(valor: object, padrao: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    def _carregar_vilas(self) -> List[Dict[str, object]]:
        bruto = self.meta.get("vilas", []) if isinstance(self.meta.get("vilas"), list) else []
        out: List[Dict[str, object]] = []
        for idx, item in enumerate(bruto):
            if not isinstance(item, dict):
                continue
            pos = item.get("posicao") if isinstance(item.get("posicao"), (list, tuple)) and len(item.get("posicao")) == 2 else None
            if pos is None:
                continue
            nome = str(item.get("nome") or f"Vila {idx + 1}").strip() or f"Vila {idx + 1}"
            out.append(
                {
                    "nome": nome,
                    "slug": self.slug(nome),
                    "tipo": "vila",
                    "posicao": [float(pos[0]), float(pos[1])],
                    "dimensao": "Mundo",
                    "regiao_id": int(item.get("regiao_id", 0) or 0),
                }
            )
        return out

    def _carregar_estadios(self) -> List[Dict[str, object]]:
        bruto = self.meta.get("estadios", []) if isinstance(self.meta.get("estadios"), list) else []
        out: List[Dict[str, object]] = []
        for idx, item in enumerate(bruto):
            if not isinstance(item, dict):
                continue
            pos = item.get("posicao") if isinstance(item.get("posicao"), (list, tuple)) and len(item.get("posicao")) == 2 else None
            if pos is None:
                continue
            tipo = self.normalizar_tipo_estadio(str(item.get("tipo") or "normal"))
            nome = str(item.get("nome") or f"Estadio {str(item.get('tipo') or tipo).strip()}").strip()
            out.append(
                {
                    "nome": nome,
                    "slug": self.slug(nome),
                    "tipo": "estadio",
                    "tipo_estadio": tipo,
                    "posicao": [float(pos[0]), float(pos[1])],
                    "dimensao": str(item.get("dimensao") or f"Estadio{str(item.get('tipo') or tipo).title()}"),
                    "estadio_id": int(item.get("estadio_id", item.get("id", 0)) or (1_900_000_000 + idx)),
                    "regiao_id": int(item.get("regiao_id", 0) or 0),
                }
            )
        return out

    def _local_por_nome(self, nome: str, tipo: str = "") -> Dict[str, object] | None:
        alvo = self.slug(nome)
        candidatos = self.vilas + self.estadios
        for local in candidatos:
            if tipo and str(local.get("tipo")) != tipo:
                continue
            if str(local.get("slug")) == alvo:
                return local
        if tipo == "estadio" and alvo.startswith("estadio_"):
            alvo_tipo = alvo.replace("estadio_", "", 1)
            for local in self.estadios:
                if str(local.get("tipo_estadio")) == self.normalizar_tipo_estadio(alvo_tipo):
                    return local
        return None

    def _carregar_rotas(self) -> List[Dict[str, object]]:
        bruto = self.meta.get("rotas", []) if isinstance(self.meta.get("rotas"), list) else []
        out: List[Dict[str, object]] = []
        for idx, item in enumerate(bruto):
            if not isinstance(item, dict):
                continue
            pontos_raw = item.get("pontos") if isinstance(item.get("pontos"), list) else []
            pontos = []
            for p in pontos_raw:
                if isinstance(p, (list, tuple)) and len(p) == 2:
                    pontos.append([float(p[0]), float(p[1])])
            if len(pontos) < 2:
                continue
            tipo_a = str(item.get("tipo_origem") or "vila").strip().lower()
            tipo_b = str(item.get("tipo_destino") or "vila").strip().lower()
            origem = self._local_por_nome(str(item.get("origem") or ""), tipo_a)
            destino = self._local_por_nome(str(item.get("destino") or ""), tipo_b)
            if origem is None or destino is None:
                continue
            out.append({"id": int(item.get("id", idx) or idx), "origem": origem, "destino": destino, "pontos": pontos})
        return out

    def _indexar_rotas(self) -> Dict[str, List[Dict[str, object]]]:
        out: Dict[str, List[Dict[str, object]]] = {}
        for rota in self.rotas:
            origem = rota.get("origem") if isinstance(rota.get("origem"), dict) else {}
            destino = rota.get("destino") if isinstance(rota.get("destino"), dict) else {}
            so = str(origem.get("slug") or "")
            sd = str(destino.get("slug") or "")
            if not so or not sd:
                continue
            out.setdefault(so, []).append(rota)
            out.setdefault(sd, []).append(rota)
        return out

    def rotas_do_local(self, local_slug: str) -> List[Dict[str, object]]:
        return list(self.rotas_por_local.get(str(local_slug or ""), []))

    def outro_lado_rota(self, rota: Dict[str, object], local_slug: str) -> Dict[str, object] | None:
        origem = rota.get("origem") if isinstance(rota.get("origem"), dict) else {}
        destino = rota.get("destino") if isinstance(rota.get("destino"), dict) else {}
        if str(origem.get("slug") or "") == str(local_slug):
            return destino
        if str(destino.get("slug") or "") == str(local_slug):
            return origem
        return None

    def pontos_rota_a_partir(self, rota: Dict[str, object], local_slug: str) -> List[List[float]]:
        pontos = list(rota.get("pontos", [])) if isinstance(rota.get("pontos"), list) else []
        origem = rota.get("origem") if isinstance(rota.get("origem"), dict) else {}
        if str(origem.get("slug") or "") == str(local_slug):
            return [[float(p[0]), float(p[1])] for p in pontos if isinstance(p, (list, tuple)) and len(p) == 2]
        return [[float(p[0]), float(p[1])] for p in reversed(pontos) if isinstance(p, (list, tuple)) and len(p) == 2]

    def _carregar_itens(self) -> List[Dict[str, object]]:
        arquivo = Path("Dados") / "Pokemon Global Server - Itens.csv"
        if not arquivo.exists():
            return []
        out: List[Dict[str, object]] = []
        with arquivo.open("r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                nome = str(row.get("Nome") or "").strip()
                if not nome:
                    continue
                venda = str(row.get("Venda", row.get("venda", row.get("Bau", ""))) or "").strip().lower()
                out.append({**dict(row), "Nome": nome, "Valor": self.inteiro(row.get("Valor"), 0), "venda": venda})
        return out

    def _preco_variado(self, valor: int, rnd: random.Random, minimo_pct: float, maximo_pct: float) -> int:
        return max(1, int(round(float(valor) * (1.0 + rnd.uniform(float(minimo_pct), float(maximo_pct))))))

    def _item_pode_venda_normal(self, item: Dict[str, object]) -> bool:
        return str(item.get("venda") or "").strip().lower() == "s"

    def _item_pode_loja_secreta(self, item: Dict[str, object], npc_nome: str) -> bool:
        nome = str(item.get("Nome") or "").strip().casefold()
        dono = str(npc_nome or "").strip().casefold()
        if nome == "poção suprema".casefold():
            return dono == "mirela"
        if nome == "masterball".casefold():
            return dono == "edward newgate"
        return str(item.get("venda") or "").strip().lower() == "ss"

    def _escolher_itens_por_nivel(self, candidatos: List[Dict[str, object]], nivel: int, quantidade: int, rnd: random.Random) -> List[Dict[str, object]]:
        if not candidatos or quantidade <= 0:
            return []
        nivel = max(0, min(100, int(nivel)))
        alvo = 5.0 + (nivel * 1.05)
        teto = max(10.0, alvo * 1.45)
        piso = max(0.0, alvo * 0.18)
        pool = [i for i in candidatos if piso <= float(i.get("Valor", 0) or 0) <= teto]
        if len(pool) < quantidade:
            pool = list(candidatos)
        escolhidos: List[Dict[str, object]] = []
        restantes = list(pool)
        while restantes and len(escolhidos) < quantidade:
            pesos = [1.0 / (1.0 + abs(float(item.get("Valor", 0) or 0) - alvo)) for item in restantes]
            item = rnd.choices(restantes, weights=pesos, k=1)[0]
            escolhidos.append(item)
            restantes = [x for x in restantes if str(x.get("Nome")) != str(item.get("Nome"))]
        return escolhidos

    def montar_loja(self, row: Dict[str, object]) -> Dict[str, List[Dict[str, object]]]:
        nome = str(row.get("Nome") or "Vendedor").strip()
        nivel = self.inteiro(row.get("Nivel"), 1)
        code = str(row.get("Code") or nome).strip()
        rnd = random.Random(51_000 + self.inteiro(code, sum(ord(c) for c in nome)))
        normais = [item for item in self.itens if self._item_pode_venda_normal(item)]
        secretos = [item for item in self.itens if self._item_pode_loja_secreta(item, nome)]
        qtd_secretos = 1 if nivel <= 30 else 2 if nivel <= 60 else 3
        itens_normais = self._escolher_itens_por_nivel(normais, nivel, 6, rnd)
        itens_secretos = self._escolher_itens_por_nivel(secretos, nivel, qtd_secretos, rnd)
        if len(itens_secretos) < qtd_secretos:
            nomes_usados = {str(item.get("Nome") or "").casefold() for item in itens_normais + itens_secretos}
            fallback = [item for item in normais if str(item.get("Nome") or "").casefold() not in nomes_usados]
            itens_secretos.extend(self._escolher_itens_por_nivel(fallback, nivel, qtd_secretos - len(itens_secretos), rnd))

        def oferta(item: Dict[str, object], idx: int, secreta: bool) -> Dict[str, object]:
            valor = max(1, int(item.get("Valor", 1) or 1))
            preco = self._preco_variado(valor, rnd, -0.20, -0.10) if secreta else self._preco_variado(valor, rnd, -0.07, 0.07)
            return {"id": ("secreta_" if secreta else "padrao_") + str(idx), "tipo": "item", "item_nome": str(item.get("Nome") or ""), "quantidade": 1, "preco": int(preco)}

        return {
            "padrao": [oferta(item, i + 1, False) for i, item in enumerate(itens_normais)],
            "secreta": [oferta(item, i + 1, True) for i, item in enumerate(itens_secretos)],
        }

    def _nivel_pokemon_treinador(self, nivel_treinador: int, rnd: random.Random) -> int:
        return max(0, min(100, int(nivel_treinador) + rnd.randint(-10, 10)))

    def _pokemon_treinador(self, nome: str, nivel_treinador: int, rnd: random.Random) -> Dict[str, object] | None:
        nome = str(nome or "").strip()
        if not nome:
            return None
        try:
            poke = criar_pokemon_inicial_materializado(nome)
            nivel = self._nivel_pokemon_treinador(nivel_treinador, rnd)
            subir_nivel_pokemon(poke, vezes=nivel)
            estado = poke.get("estado") if isinstance(poke.get("estado"), dict) else poke
            stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
            vida = float(stats.get("Vida", 0.0) or 0.0)
            estado["VidaAtual"] = vida
            estado["vida_atual"] = vida
            estado["npc_pokemon"] = True
            return poke
        except Exception:
            return None

    def _pokemons_treinador(self, nomes: List[str], nivel_treinador: int, rnd: random.Random) -> List[Dict[str, object] | None]:
        return [self._pokemon_treinador(nome, nivel_treinador, rnd) if nome else None for nome in nomes]

    @staticmethod
    def colunas_pokemon(row: Dict[str, object]) -> List[str]:
        cols: List[Tuple[int, str]] = []
        for chave in row.keys():
            texto = str(chave or "").strip()
            if not texto.lower().startswith("pokemon"):
                continue
            try:
                idx = int(texto[7:])
            except Exception:
                continue
            cols.append((idx, texto))
        cols.sort(key=lambda x: x[0])
        return [c for _, c in cols]

    def montar_times_combatente(self, row: Dict[str, object]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
        nome_npc = str(row.get("Nome") or "NPC").strip()
        cargo = self.slug(row.get("Cargo"))
        nivel = self.inteiro(row.get("Nivel"), 1)
        code = self.inteiro(row.get("Code"), sum(ord(c) for c in nome_npc))
        rnd = random.Random(72_000 + code)
        nomes = [str(row.get(col) or "").strip() for col in self.colunas_pokemon(row)]
        pokes: List[Dict[str, object] | None] = []

        def compact(indices: List[int], fonte: List[Dict[str, object] | None] | None = None) -> List[Dict[str, object]]:
            base = fonte if fonte is not None else pokes
            return [base[i] for i in indices if 0 <= i < len(base) and isinstance(base[i], dict)]

        times: List[Dict[str, object]] = []
        if cargo == "lider" and len(nomes) >= 12:
            meio = list(range(3, 9))
            sorteados = rnd.sample(meio, k=3)
            sobraram = [i for i in meio if i not in sorteados]
            indices_time1 = [0, 1, 2] + sorteados
            indices_time2 = sobraram + [9, 10, 11]
            pokes_time1 = self._pokemons_treinador(nomes, max(0, nivel - 50), rnd)
            pokes_time2 = self._pokemons_treinador(nomes, nivel, rnd)
            time1 = compact(indices_time1, pokes_time1)
            time2 = compact(indices_time2, pokes_time2)
            pokes = [p for p in pokes_time1 + pokes_time2 if isinstance(p, dict)]
            times.append({"Nome": "Time 1", "Slots": time1[:6]})
            times.append({"Nome": "Time 2", "Slots": time2[:6]})
        else:
            pokes = self._pokemons_treinador(nomes, nivel, rnd)
            times.append({"Nome": "Time 1", "Slots": compact(list(range(0, 6)))[:6]})
        todos = [p for time in times for p in time.get("Slots", []) if isinstance(p, dict)]
        return todos, times

    def _local_inicial(self, code: object) -> Dict[str, object]:
        if not self.vilas:
            return {"nome": "Mundo", "slug": "mundo", "tipo": "vila", "posicao": [0.0, 0.0], "dimensao": "Mundo"}
        idx = self.inteiro(code, 0) % len(self.vilas)
        return self.vilas[idx]

    def posicao_em_local(self, local: Dict[str, object], code: object, raio_min: float = 1.5, raio_max: float = 14.0) -> List[float]:
        pos = local.get("posicao") if isinstance(local.get("posicao"), (list, tuple)) and len(local.get("posicao")) == 2 else [0.0, 0.0]
        if str(local.get("tipo")) == "estadio" and str(local.get("dimensao") or "Mundo") != "Mundo":
            rnd = random.Random(13_000 + self.inteiro(code, 0))
            return [rnd.uniform(10.0, 50.0), rnd.uniform(8.0, 32.0)]
        rnd = random.Random(11_000 + self.inteiro(code, 0))
        dist = rnd.uniform(float(raio_min), float(raio_max))
        ang = rnd.uniform(0.0, math.tau)
        return [float(pos[0]) + math.cos(ang) * dist, float(pos[1]) + math.sin(ang) * dist]

    def permanencia_ticks(self, code: object, tick_atual: int = 0) -> int:
        rnd = random.Random(88_000 + self.inteiro(code, 0) + int(tick_atual))
        minutos_jogo = rnd.randint(12, 45)
        return int(tick_atual) + int(minutos_jogo * 30)

    def base_movel(self, *, chave: str, row: Dict[str, object], estilo: str, cargo: str, id_base: int) -> Dict[str, object]:
        code = str(row.get("Code") or chave).strip() or str(chave)
        local = self._local_inicial(code)
        pos = self.posicao_em_local(local, code)
        modo = "ambulante" if (self.inteiro(code, 0) % 2 == 0) else "parado"
        return {
            "id": int(id_base + self.inteiro(code, 0)),
            "code": code,
            "nome": str(row.get("Nome") or chave).strip() or str(chave),
            "skin": self.normalizar_skin(row.get("Skin")),
            "nivel": self.inteiro(row.get("Nivel"), 1),
            "velocidade": self.velocidade_base,
            "estilo": estilo,
            "cargo": cargo,
            "fixado": False,
            "estatico": modo == "parado",
            "dimensao": str(local.get("dimensao") or "Mundo"),
            "local_atual": str(local.get("slug") or ""),
            "local_tipo": str(local.get("tipo") or "vila"),
            "posicao": [float(pos[0]), float(pos[1])],
            "rota": [],
            "rota_idx": 0,
            "fase": "permanencia",
            "modo_local": modo,
            "permanencia_ate_tick": self.permanencia_ticks(code, 0),
            "espera_ate_tick": 0,
            "interacao": {"ativa": False, "cliente": ""},
            "angulo": 0.0,
            "inicializador_npc_versao": self.VERSAO,
        }

    def criar_estado(self) -> Dict[str, Dict[str, object]]:
        base: Dict[str, Dict[str, object]] = {}
        arq_vendedores = Path("Dados") / "Pokemon Global Server - NPC Vendedor.csv"
        if arq_vendedores.exists():
            with arq_vendedores.open("r", encoding="utf-8-sig") as f:
                for idx, row in enumerate(csv.DictReader(f), start=1):
                    code = str(row.get("Code") or idx).strip() or str(idx)
                    npc = self.base_movel(chave=f"vendedor:{code}", row=row, estilo="vendedor", cargo="vendedor", id_base=900000)
                    npc["loja"] = self.montar_loja(row)
                    base[f"vendedor:{code}"] = npc

        arq_combatentes = Path("Dados") / "Pokemon Global Server - NPC Combatente.csv"
        if arq_combatentes.exists():
            with arq_combatentes.open("r", encoding="utf-8-sig") as f:
                for idx, row in enumerate(csv.DictReader(f), start=1):
                    code = str(row.get("Code") or idx).strip() or str(idx)
                    cargo = self.slug(row.get("Cargo") or "dissociado")
                    pokemons, times = self.montar_times_combatente(row)
                    if cargo in {"lider", "desafiante"}:
                        tipo = self.normalizar_tipo_estadio(str(row.get("Estadio") or "normal"))
                        estadio = next((e for e in self.estadios if str(e.get("tipo_estadio")) == tipo), None)
                        dimensao = str((estadio or {}).get("dimensao") or f"Estadio{tipo.title()}")
                        pos = [30.0, 20.0] if cargo == "lider" else self.posicao_em_local({"tipo": "estadio", "dimensao": dimensao, "posicao": [30.0, 20.0]}, int(code) + 400)
                        npc = {
                            "id": int(910000 + self.inteiro(code, idx)),
                            "code": code,
                            "nome": str(row.get("Nome") or f"Combatente {idx}").strip(),
                            "skin": self.normalizar_skin(row.get("Skin")),
                            "nivel": self.inteiro(row.get("Nivel"), 1),
                            "velocidade": 0.0,
                            "estilo": "combatente",
                            "cargo": cargo,
                            "fixado": True,
                            "estatico": True,
                            "dimensao": dimensao,
                            "estadio_tipo": tipo,
                            "local_atual": str((estadio or {}).get("slug") or self.slug(f"Estadio {tipo}")),
                            "local_tipo": "estadio",
                            "posicao": [float(pos[0]), float(pos[1])],
                            "rota": [],
                            "rota_idx": 0,
                            "fase": "fixado",
                            "espera_ate_tick": 0,
                            "interacao": {"ativa": False, "cliente": ""},
                            "angulo": 0.0,
                            "pokemons": pokemons,
                            "times_pokemon": times,
                            "inicializador_npc_versao": self.VERSAO,
                        }
                    else:
                        npc = self.base_movel(chave=f"combatente:{code}", row=row, estilo="combatente", cargo=cargo or "dissociado", id_base=910000)
                        npc["estadio_tipo"] = self.normalizar_tipo_estadio(str(row.get("Estadio") or ""))
                        npc["pokemons"] = pokemons
                        npc["times_pokemon"] = times
                    base[f"combatente:{code}"] = npc
        return base

    def reconciliar(self, salvo: Dict[str, Dict[str, object]]) -> tuple[Dict[str, Dict[str, object]], bool]:
        novo = self.criar_estado()
        mudou = False
        saida: Dict[str, Dict[str, object]] = {}
        for chave, base in novo.items():
            atual = salvo.get(chave) if isinstance(salvo.get(chave), dict) else None
            if atual is None:
                saida[chave] = dict(base)
                mudou = True
                continue
            preservado = dict(base)
            preservado["interacao"] = dict(atual.get("interacao", {"ativa": False, "cliente": ""})) if isinstance(atual.get("interacao"), dict) else {"ativa": False, "cliente": ""}
            preservado["angulo"] = float(atual.get("angulo", base.get("angulo", 0.0)) or 0.0)
            pode_preservar_movimento = int(atual.get("inicializador_npc_versao", 0) or 0) >= self.VERSAO and bool(atual.get("local_atual"))
            if pode_preservar_movimento and not bool(base.get("fixado", False)):
                for campo in ("posicao", "dimensao", "local_atual", "local_tipo", "fase", "modo_local", "permanencia_ate_tick", "rota", "rota_idx", "destino_local", "espera_ate_tick", "estatico"):
                    if campo in atual:
                        preservado[campo] = atual[campo]
            if preservado != atual:
                mudou = True
            saida[chave] = preservado
        if set(salvo.keys()) != set(saida.keys()):
            mudou = True
        return saida, mudou
