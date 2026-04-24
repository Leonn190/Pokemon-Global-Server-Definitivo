from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MontadorJogada:
    MAX_MOVIMENTOS = 5
    MAX_MOVIMENTOS_POR_POKEMON = 2

    def __init__(self, regras_batalha: Dict[str, object] | None = None) -> None:
        self._jogadas: List[Dict[str, object]] = []
        self._selecionado_id: Optional[int] = None
        self._proximo_id = 1
        self._regras_batalha = dict(regras_batalha or {})
        self._ataques_por_nome = self._carregar_propriedades_ataque()

    @classmethod
    def _carregar_propriedades_ataque(cls) -> Dict[str, Dict[str, object]]:
        caminho = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - PropriedadesAtaque.json"
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ataques = dados.get("ataques") if isinstance(dados, dict) else {}
        if not isinstance(ataques, dict):
            return {}
        saida: Dict[str, Dict[str, object]] = {}
        for ataque in ataques.values():
            if not isinstance(ataque, dict):
                continue
            nome = str(ataque.get("nome") or ataque.get("Ataque") or "").strip()
            if not nome:
                continue
            saida[nome.casefold()] = dict(ataque)
        return saida

    @staticmethod
    def _ponto2(valor, default: tuple[float, float] = (0.0, 0.0)) -> tuple[float, float]:
        if isinstance(valor, (tuple, list)) and len(valor) == 2:
            try:
                return float(valor[0]), float(valor[1])
            except (TypeError, ValueError):
                return default
        return default

    @staticmethod
    def _destino_por_alcance(origem: tuple[float, float], destino: tuple[float, float], alcance: float) -> tuple[float, float]:
        dx = float(destino[0]) - float(origem[0])
        dy = float(destino[1]) - float(origem[1])
        dist = math.hypot(dx, dy)
        if dist <= 1e-6:
            return float(origem[0]) + float(alcance), float(origem[1])
        escala = min(float(alcance), dist) / dist
        return float(origem[0]) + dx * escala, float(origem[1]) + dy * escala

    @staticmethod
    def _direcao(origem: tuple[float, float], destino: tuple[float, float]) -> tuple[float, float, float]:
        dx = float(destino[0]) - float(origem[0])
        dy = float(destino[1]) - float(origem[1])
        dist = math.hypot(dx, dy)
        if dist <= 1e-6:
            return 1.0, 0.0, 0.0
        return dx / dist, dy / dist, dist

    @staticmethod
    def _limites_arena_float(controlador) -> tuple[float, float, float, float] | None:
        if controlador is None:
            return None
        if hasattr(controlador, "limites_arena_float"):
            limites = controlador.limites_arena_float()
            if isinstance(limites, (tuple, list)) and len(limites) == 4:
                return tuple(float(v) for v in limites)
        if hasattr(controlador, "limites_arena"):
            rect = controlador.limites_arena()
            return float(rect.left), float(rect.top), float(rect.right), float(rect.bottom)
        return None

    @classmethod
    def _colisao_parede_raio(
        cls,
        origem: tuple[float, float],
        direcao: tuple[float, float],
        alcance: float,
        limites: tuple[float, float, float, float] | None,
        raio: float,
    ) -> tuple[float, str] | None:
        if limites is None:
            return None
        min_x, min_y, max_x, max_y = limites
        x, y = origem
        dx, dy = direcao
        candidatos: list[tuple[float, str]] = []
        if abs(dx) > 1e-6:
            candidatos.append(((min_x + raio - x) / dx, "vertical"))
            candidatos.append(((max_x - raio - x) / dx, "vertical"))
        if abs(dy) > 1e-6:
            candidatos.append(((min_y + raio - y) / dy, "horizontal"))
            candidatos.append(((max_y - raio - y) / dy, "horizontal"))
        validos = [(t, eixo) for t, eixo in candidatos if 1e-6 < t <= alcance + 1e-6]
        if not validos:
            return None
        return min(validos, key=lambda item: item[0])

    @classmethod
    def _colisao_circulo_raio(
        cls,
        origem: tuple[float, float],
        direcao: tuple[float, float],
        alcance: float,
        centro: tuple[float, float],
        raio_total: float,
    ) -> float | None:
        ox, oy = origem
        dx, dy = direcao
        cx, cy = centro
        fx = ox - cx
        fy = oy - cy
        b = 2.0 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - float(raio_total) * float(raio_total)
        disc = b * b - 4.0 * c
        if disc < 0.0:
            return None
        raiz = math.sqrt(disc)
        candidatos = [(-b - raiz) / 2.0, (-b + raiz) / 2.0]
        validos = [t for t in candidatos if 1e-6 < t <= alcance + 1e-6]
        return min(validos) if validos else None

    @staticmethod
    def _comportamento_colisao(props: Dict[str, object], tipo: str) -> str:
        colisao = props.get("colisao") if isinstance(props, dict) else {}
        if isinstance(colisao, dict):
            nodo = colisao.get(tipo)
            if isinstance(nodo, dict):
                comportamento = str(nodo.get("comportamento_fim") or "").strip().casefold()
                if comportamento:
                    return comportamento
        return "destruir"

    @staticmethod
    def _limite_colisao(props: Dict[str, object], bloco: str, tipo: str) -> int:
        dados = props.get(bloco) if isinstance(props, dict) else {}
        if isinstance(dados, dict):
            nodo = dados.get(tipo)
            if isinstance(nodo, dict):
                if not bool(nodo.get("permite", False)):
                    return 0
                try:
                    return max(0, int(nodo.get("max", 0) or 0))
                except (TypeError, ValueError):
                    return 0
        return 0

    @staticmethod
    def _alvo_permitido(controlador, executor, alvo, grupo: str) -> bool:
        grupo = str(grupo or "inimigo").strip().casefold()
        if alvo is None:
            return False
        if grupo in {"ambos", "qualquer"}:
            return not bool(getattr(alvo, "EmReserva", False))
        if grupo in {"si mesmo", "si_mesmo", "self"}:
            return alvo is executor
        if grupo == "reserva":
            return bool(getattr(alvo, "EmReserva", False))
        aliado = bool(getattr(controlador, "pokemon_eh_aliado", lambda _p: False)(alvo))
        executor_aliado = bool(getattr(controlador, "pokemon_eh_aliado", lambda _p: False)(executor))
        if grupo == "aliado":
            return aliado == executor_aliado and not bool(getattr(alvo, "EmReserva", False))
        if grupo == "inimigo":
            return aliado != executor_aliado and not bool(getattr(alvo, "EmReserva", False))
        return False

    def _simular_rota_projetil(
        self,
        *,
        origem: tuple[float, float],
        destino: tuple[float, float],
        props: Dict[str, object],
        controlador=None,
        executor=None,
        angulo_offset_graus: float = 0.0,
    ) -> Dict[str, object]:
        projetil = props.get("projetil") if isinstance(props.get("projetil"), dict) else {}
        raio = max(0.05, float((projetil or {}).get("raio", 0.3) or 0.3))
        alcance_total = max(0.01, float((projetil or {}).get("alcance", 8.0) or 8.0))
        ux, uy, _ = self._direcao(origem, destino)
        if abs(float(angulo_offset_graus or 0.0)) > 1e-6:
            ang = math.radians(float(angulo_offset_graus))
            cos_a, sin_a = math.cos(ang), math.sin(ang)
            ux, uy = ux * cos_a - uy * sin_a, ux * sin_a + uy * cos_a
        atual = tuple(origem)
        direcao = (ux, uy)
        restante = alcance_total
        segmentos: list[dict[str, object]] = []
        impacto = None
        tipo_impacto = None
        atravessadas = 0
        ricochetes = 0
        max_atravessar = max(
            self._limite_colisao(props, "atravessar", "pokemon"),
            int((projetil or {}).get("max_atravessadas", 0) or 0),
        )
        max_ricochetes = max(
            self._limite_colisao(props, "ricochete", "parede"),
            int((projetil or {}).get("max_ricochetes", 0) or 0),
        )
        limites = self._limites_arena_float(controlador)
        pokemons = []
        if controlador is not None and hasattr(controlador, "mapa_pokemons"):
            vistos = set()
            for poke in controlador.mapa_pokemons().values():
                uid = getattr(poke, "Uid", id(poke))
                if uid in vistos or poke is executor or bool(getattr(poke, "EmReserva", False)):
                    continue
                vistos.add(uid)
                pokemons.append(poke)

        for _ in range(1 + max_ricochetes + max_atravessar + 2):
            if restante <= 1e-6:
                break
            fim = (atual[0] + direcao[0] * restante, atual[1] + direcao[1] * restante)
            colisao_t = None
            colisao_tipo = ""
            colisao_eixo = ""

            parede = self._colisao_parede_raio(atual, direcao, restante, limites, raio)
            if parede is not None:
                colisao_t, colisao_tipo, colisao_eixo = float(parede[0]), "parede", str(parede[1])

            for poke in pokemons:
                pos = self._ponto2(getattr(poke, "Posicao", None), None)  # type: ignore[arg-type]
                if pos is None:
                    continue
                raio_poke = float(getattr(poke, "RaioColisao", 0.5) or 0.5)
                t = self._colisao_circulo_raio(atual, direcao, restante, pos, raio + raio_poke)
                if t is not None and (colisao_t is None or t < colisao_t):
                    colisao_t = t
                    colisao_tipo = "pokemon"
                    colisao_eixo = ""

            if colisao_t is None:
                segmentos.append({"inicio": atual, "fim": fim, "colisao": None})
                impacto = fim
                break

            ponto = (atual[0] + direcao[0] * colisao_t, atual[1] + direcao[1] * colisao_t)
            segmentos.append({"inicio": atual, "fim": ponto, "colisao": colisao_tipo})
            impacto = ponto
            tipo_impacto = colisao_tipo
            restante -= colisao_t
            comportamento = self._comportamento_colisao(props, colisao_tipo)
            if comportamento == "atravessar" and colisao_tipo == "pokemon" and atravessadas < max_atravessar:
                atravessadas += 1
                atual = (ponto[0] + direcao[0] * 0.04, ponto[1] + direcao[1] * 0.04)
                restante = max(0.0, restante - 0.04)
                continue
            if comportamento == "ricochetear" and colisao_tipo == "parede" and ricochetes < max_ricochetes:
                ricochetes += 1
                if colisao_eixo == "vertical":
                    direcao = (-direcao[0], direcao[1])
                else:
                    direcao = (direcao[0], -direcao[1])
                atual = (ponto[0] + direcao[0] * 0.04, ponto[1] + direcao[1] * 0.04)
                restante = max(0.0, restante - 0.04)
                continue
            break

        dados: Dict[str, object] = {
            "segmentos": segmentos,
            "impacto_mundo": impacto,
            "alcance": alcance_total,
            "raio": raio,
            "tipo_impacto": tipo_impacto,
        }
        if str(props.get("estilo") or "").casefold() == "explosivo" and isinstance(props.get("explosivo"), dict):
            explosivo = props.get("explosivo") or {}
            detonadores = {str(item).casefold() for item in list(explosivo.get("detona_ao_colidir_com") or [])}
            if tipo_impacto in detonadores:
                zona = explosivo.get("zona") if isinstance(explosivo.get("zona"), dict) else {}
                dados["zona_explosao"] = {
                    "centro": impacto,
                    "raio": float((zona or {}).get("raio", 1.5) or 1.5),
                }
        return dados

    def _simular_rotas_projeteis(
        self,
        *,
        origem: tuple[float, float],
        destino: tuple[float, float],
        props: Dict[str, object],
        controlador=None,
        executor=None,
    ) -> Dict[str, object]:
        projetil = props.get("projetil") if isinstance(props.get("projetil"), dict) else {}
        quantidade = max(1, int((projetil or {}).get("quantidade", 1) or 1))
        angulo = float((projetil or {}).get("angulo_entre_projeteis", 0) or 0)
        if quantidade == 1:
            return self._simular_rota_projetil(origem=origem, destino=destino, props=props, controlador=controlador, executor=executor)

        combinado: Dict[str, object] = {"segmentos": [], "zonas_explosao": []}
        primeiro_impacto = None
        primeiro_alcance = None
        primeiro_raio = None
        primeiro_tipo = None
        for i in range(quantidade):
            offset = (i - (quantidade - 1) / 2.0) * angulo
            rota = self._simular_rota_projetil(
                origem=origem,
                destino=destino,
                props=props,
                controlador=controlador,
                executor=executor,
                angulo_offset_graus=offset,
            )
            for segmento in list(rota.get("segmentos") or []):
                if isinstance(segmento, dict):
                    segmento = dict(segmento)
                    segmento["indice_projetil"] = i
                    combinado["segmentos"].append(segmento)
            zona = rota.get("zona_explosao") if isinstance(rota.get("zona_explosao"), dict) else None
            if zona:
                combinado["zonas_explosao"].append(zona)
            if primeiro_impacto is None:
                primeiro_impacto = rota.get("impacto_mundo")
                primeiro_alcance = rota.get("alcance")
                primeiro_raio = rota.get("raio")
                primeiro_tipo = rota.get("tipo_impacto")

        combinado["impacto_mundo"] = primeiro_impacto
        combinado["alcance"] = primeiro_alcance
        combinado["raio"] = primeiro_raio
        combinado["tipo_impacto"] = primeiro_tipo
        if combinado["zonas_explosao"]:
            combinado["zona_explosao"] = combinado["zonas_explosao"][0]
        return combinado

    @staticmethod
    def _normalizar_id(executor_id: object) -> str:
        return str(executor_id or "")

    @staticmethod
    def _nome_ataque(ataque: Dict[str, object] | None) -> str:
        if not isinstance(ataque, dict):
            return ""
        return str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()

    def estilo_ataque(self, ataque: Dict[str, object] | None) -> str:
        prop = self.obter_propriedades_ataque(ataque)
        nome = self._nome_ataque(ataque).casefold()
        if not nome:
            return "movimento"
        estilo = str(prop.get("estilo") or ataque.get("estilo") or "").strip().casefold()
        if estilo:
            return "projetil" if estilo == "tiro" else estilo
        return "ataque"

    def obter_propriedades_ataque(self, ataque: Dict[str, object] | None) -> Dict[str, object]:
        nome = self._nome_ataque(ataque).casefold()
        base = dict(self._ataques_por_nome.get(nome, {}))
        if isinstance(ataque, dict):
            for chave, valor in ataque.items():
                if chave not in base:
                    base[chave] = valor
        return base

    def origem_virtual(self, pokemon, pokemons_por_id: Dict[str, object]) -> tuple[float, float]:
        return self.posicao_virtual_executor(getattr(pokemon, "Uid", ""), pokemons_por_id) or self._ponto2(getattr(pokemon, "Posicao", None))

    def construir_preview_ataque(self, *, pokemon, ataque, mouse_pos_px, camera, controlador=None, parede_ponto_a=None) -> Dict[str, object]:
        origem = self.origem_virtual(pokemon, getattr(controlador, "mapa_pokemons", lambda: {})())
        destino = self._ponto2(camera.tela_para_batalha_tiles(mouse_pos_px))
        props = self.obter_propriedades_ataque(ataque if isinstance(ataque, dict) else None)
        estilo = self.estilo_ataque(props)
        prev: Dict[str, object] = {
            "executor": pokemon,
            "executor_id": getattr(pokemon, "Uid", ""),
            "ataque": props,
            "estilo": estilo,
            "origem_mundo": origem,
            "destino_mundo": destino,
            "invalido": False,
        }

        if estilo == "alvo":
            alvo_cfg = props.get("alvo") if isinstance(props.get("alvo"), dict) else {}
            alcance = float((alvo_cfg or {}).get("alcance", 3.0) or 3.0)
            grupo = str((alvo_cfg or {}).get("grupo_permitido", "inimigo") or "inimigo")
            prev["alcance"] = alcance
            prev["grupo_permitido"] = grupo
            alvo = getattr(controlador, "pokemon_no_ponto", lambda *_: None)(mouse_pos_px, camera)
            if alvo is None:
                prev["invalido"] = True
            else:
                prev["alvo_ids"] = [getattr(alvo, "Uid", "")]
                fora_alcance = math.dist(self._ponto2(getattr(alvo, "Posicao", None)), origem) > alcance
                prev["invalido"] = fora_alcance or not self._alvo_permitido(controlador, pokemon, alvo, grupo)
        elif estilo == "status":
            prev["autouso"] = True
            prev["alvo_ids"] = [getattr(pokemon, "Uid", "")]
            prev["invalido"] = getattr(controlador, "pokemon_no_ponto", lambda *_: None)(mouse_pos_px, camera) is not pokemon
        elif estilo == "zona":
            zona = props.get("zona") if isinstance(props.get("zona"), dict) else {}
            prev["raio"] = float((zona or {}).get("raio", 1.0) or 1.0)
            alcance = float((zona or {}).get("alcance_max_centro", (zona or {}).get("alcance", 6.0)) or 6.0)
            prev["alcance"] = alcance
            if math.dist(origem, destino) > alcance:
                destino = self._destino_por_alcance(origem, destino, alcance)
                prev["destino_mundo"] = destino
        elif estilo == "laser":
            laser = props.get("laser") if isinstance(props.get("laser"), dict) else {}
            alcance = float((laser or {}).get("alcance", 8.0) or 8.0)
            prev["alcance"] = alcance
            prev["grossura"] = float((laser or {}).get("grossura", 0.8) or 0.8)
            prev["destino_mundo"] = self._destino_por_alcance(origem, destino, alcance)
        elif estilo in {"projetil", "explosivo"}:
            rota = self._simular_rotas_projeteis(origem=origem, destino=destino, props=props, controlador=controlador, executor=pokemon)
            prev.update(rota)
            prev["destino_mundo"] = rota.get("impacto_mundo") or self._destino_por_alcance(origem, destino, float(rota.get("alcance", 8.0)))
        elif estilo == "area":
            area = props.get("area") if isinstance(props.get("area"), dict) else {}
            alcance = float((area or {}).get("alcance", 2.0) or 2.0)
            prev["alcance"] = alcance
            prev["forma"] = str((area or {}).get("forma", "cone") or "cone").casefold()
            prev["abertura_graus"] = float((area or {}).get("abertura_graus", 70.0) or 70.0)
            prev["base"] = float((area or {}).get("base", 0.8) or 0.8)
            prev["teto"] = float((area or {}).get("teto", 2.2) or 2.2)
            prev["atravessa_parede"] = bool((area or {}).get("atravessa_parede", False))
            prev["destino_mundo"] = self._destino_por_alcance(origem, destino, alcance)
        elif estilo in {"dash", "impulso"}:
            mov = props.get("movimento_ofensivo") if isinstance(props.get("movimento_ofensivo"), dict) else {}
            prev["distancia_min"] = float((mov or {}).get("distancia_min", 0.0) or 0.0)
            prev["distancia_max"] = float((mov or {}).get("distancia_max", 6.0) or 6.0)
            max_dist = max(0.01, float(prev["distancia_max"]))
            destino = self._destino_por_alcance(origem, destino, max_dist)
            prev["destino_mundo"] = destino
            if estilo == "impulso":
                prev["intensidade"] = max(0.0, min(1.0, math.dist(origem, destino) / max_dist))
            else:
                prev["largura"] = max(0.5, float(getattr(pokemon, "DiametroTiles", getattr(pokemon, "TamanhoTiles", 1.0)) or 1.0))
        elif estilo == "parede":
            parede = props.get("parede") if isinstance(props.get("parede"), dict) else {}
            alcance_primeiro = float((parede or {}).get("alcance_primeiro_ponto", 6.0) or 6.0)
            distancia_max = float((parede or {}).get("distancia_max_entre_pontos", 4.0) or 4.0)
            prev["alcance"] = alcance_primeiro
            prev["distancia_max_entre_pontos"] = distancia_max
            prev["largura"] = float((parede or {}).get("largura", 0.25) or 0.25)
            if parede_ponto_a is None:
                prev["ponto_a"] = destino
                prev["invalido"] = math.dist(origem, destino) > alcance_primeiro
            else:
                prev["ponto_a"] = parede_ponto_a
                prev["ponto_b"] = destino
                prev["invalido"] = not self.validar_segundo_ponto_parede(parede_ponto_a, destino, distancia_max)
        return prev

    def montar_jogada_de_preview(self, preview: Dict[str, object]) -> Dict[str, object]:
        ataque = preview.get("ataque")
        executor = preview.get("executor")
        estilo = str(preview.get("estilo") or "")
        payload_chaves = [
            "alvo_ids",
            "autouso",
            "ponto_a",
            "ponto_b",
            "segmentos",
            "impacto_mundo",
            "zona_explosao",
            "zonas_explosao",
        ]
        return {
            "executor": executor,
            "executor_id": getattr(executor, "Uid", ""),
            "ataque": ataque,
            "estilo": estilo,
            "destino_mundo": preview.get("destino_mundo"),
            "tipo_movimento": estilo in {"dash", "impulso"},
            "custo_base": self.custo_base_ataque(ataque, 0.0),
            "alcance": preview.get("alcance"),
            "raio": preview.get("raio"),
            "grossura": preview.get("grossura"),
            "largura": preview.get("largura"),
            "forma": preview.get("forma"),
            "abertura_graus": preview.get("abertura_graus"),
            "base": preview.get("base"),
            "teto": preview.get("teto"),
            "atravessa_parede": preview.get("atravessa_parede"),
            "distancia_max_entre_pontos": preview.get("distancia_max_entre_pontos"),
            "payload": {k: preview.get(k) for k in payload_chaves if k in preview},
        }

    def ataque_eh_passiva(self, ataque: Dict[str, object] | None) -> bool:
        return self.estilo_ataque(ataque) == "passiva"

    def custo_base_ataque(self, ataque: Dict[str, object] | None, fallback: float = 0.0) -> float:
        prop = self.obter_propriedades_ataque(ataque)
        try:
            return max(0.0, float(prop.get("custo", ataque.get("custo", fallback) if isinstance(ataque, dict) else fallback) or 0.0))
        except (TypeError, ValueError):
            return max(0.0, float(fallback or 0.0))

    @staticmethod
    def validar_segundo_ponto_parede(ponto_a: tuple[float, float], ponto_b: tuple[float, float], distancia_max: float) -> bool:
        if not (isinstance(ponto_a, (tuple, list)) and len(ponto_a) == 2 and isinstance(ponto_b, (tuple, list)) and len(ponto_b) == 2):
            return False
        return math.dist((float(ponto_a[0]), float(ponto_a[1])), (float(ponto_b[0]), float(ponto_b[1]))) <= float(distancia_max)

    @staticmethod
    def atingiu_limiar_arrasto(inicio_px: tuple[float, float], fim_px: tuple[float, float], limiar_px: float = 12.0) -> bool:
        if not (isinstance(inicio_px, (tuple, list)) and len(inicio_px) == 2 and isinstance(fim_px, (tuple, list)) and len(fim_px) == 2):
            return False
        return math.dist((float(inicio_px[0]), float(inicio_px[1])), (float(fim_px[0]), float(fim_px[1]))) >= float(limiar_px)

    def resolver_arrasto_para_jogada(
        self,
        *,
        executor,
        executor_id: object,
        origem_mundo: tuple[float, float],
        destino_mundo: tuple[float, float],
        dentro_arena: bool,
        reserva_id: object | None,
        reserva_valida: bool,
    ) -> Dict[str, object] | None:
        if reserva_id is not None:
            if not bool(reserva_valida):
                return None
            return {
                "executor": executor,
                "executor_id": self._normalizar_id(executor_id),
                "troca_reserva_id": str(reserva_id),
                "destino_mundo": tuple(destino_mundo),
                "custo_base": 0.0,
                "estilo": "troca",
                "tipo_movimento": False,
                "largura": max(0.5, float(getattr(executor, "DiametroTiles", getattr(executor, "TamanhoTiles", 1.0)) or 1.0)),
            }
        if not bool(dentro_arena):
            return None
        return {
            "executor": executor,
            "executor_id": self._normalizar_id(executor_id),
            "destino_mundo": tuple(destino_mundo),
            "custo_base": self.custo_movimento(executor, origem_mundo, destino_mundo),
            "estilo": "movimento",
            "tipo_movimento": True,
            "largura": max(0.5, float(getattr(executor, "DiametroTiles", getattr(executor, "TamanhoTiles", 1.0)) or 1.0)),
        }

    @staticmethod
    def _nome_acao(jogada: Dict[str, object]) -> str:
        nome_manual = str(jogada.get("acao_chave_manual") or "").strip()
        if nome_manual:
            return nome_manual.casefold()
        if jogada.get("troca_reserva_id"):
            return "__troca__"
        ataque = jogada.get("ataque") if isinstance(jogada, dict) else None
        if isinstance(ataque, dict):
            nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
            if nome:
                return nome.casefold()
        return "__movimento_nativo__"

    def _jogadas_executor(self, executor_id: object) -> List[Dict[str, object]]:
        chave = self._normalizar_id(executor_id)
        return [item for item in self._jogadas if self._normalizar_id(item.get("executor_id")) == chave]

    def _custo_total_para_executor(self, quantidade_previa: int, custo_base: float, jogada: Dict[str, object]) -> float:
        if quantidade_previa <= 0:
            return max(0.0, float(custo_base))
        if bool(jogada.get("tipo_movimento")) and not bool(jogada.get("ataque")):
            return max(0.0, float(custo_base))
        return max(0.0, float(custo_base) * 1.1)

    def _executor_bloqueado_por_troca(self, executor_id: object) -> bool:
        return any(item.get("troca_reserva_id") for item in self._jogadas_executor(executor_id))

    def pode_adicionar(self, jogada: Dict[str, object], energia_disponivel: float | None = None, ignorar_custo: bool = False) -> Tuple[bool, str, float]:
        if not isinstance(jogada, dict):
            return False, "Jogada inválida.", 0.0
        executor_id = self._normalizar_id(jogada.get("executor_id"))
        if not executor_id:
            return False, "Sem executor.", 0.0
        if self._executor_bloqueado_por_troca(executor_id):
            return False, "Pokémon já preparou troca.", 0.0
        if len(self._jogadas) >= self.MAX_MOVIMENTOS:
            return False, "A jogada já está cheia.", 0.0
        jogadas_executor = self._jogadas_executor(executor_id)
        if len(jogadas_executor) >= self.MAX_MOVIMENTOS_POR_POKEMON:
            return False, "Esse Pokémon já tem 2 movimentos.", 0.0

        nome_acao = self._nome_acao(jogada)
        if any(self._nome_acao(item) == nome_acao for item in jogadas_executor):
            return False, "Esse movimento já foi usado por esse Pokémon.", 0.0

        if bool(jogada.get("tipo_movimento")) and not bool(jogada.get("ataque")):
            if any(bool(item.get("tipo_movimento")) and not bool(item.get("ataque")) for item in jogadas_executor):
                return False, "Movimento já preparado para esse Pokémon.", 0.0

        ataque = jogada.get("ataque")
        if self.ataque_eh_passiva(ataque):
            return False, "Ataque passivo não pode ser preparado manualmente.", 0.0

        custo_base = float(jogada.get("custo_base") or jogada.get("custo") or 0.0)
        custo_total = self._custo_total_para_executor(len(jogadas_executor), custo_base, jogada)
        if energia_disponivel is not None and not bool(ignorar_custo):
            ja_reservado = self.custo_reservado(executor_id)
            if ja_reservado + custo_total > float(energia_disponivel) + 1e-6:
                return False, "Energia insuficiente.", custo_total
        return True, "", custo_total

    def adicionar(self, jogada: Dict[str, object], energia_disponivel: float | None = None, ignorar_custo: bool = False) -> Tuple[Optional[Dict[str, object]], str]:
        permitido, motivo, custo_total = self.pode_adicionar(jogada, energia_disponivel=energia_disponivel, ignorar_custo=ignorar_custo)
        if not permitido:
            return None, motivo

        item = dict(jogada)
        item["id"] = self._proximo_id
        item["executor_id"] = self._normalizar_id(item.get("executor_id"))
        item["acao_chave"] = self._nome_acao(item)
        item["custo_base"] = float(item.get("custo_base") or item.get("custo") or 0.0)
        item["custo"] = float(custo_total)

        self._proximo_id += 1
        self._jogadas.append(item)
        self._selecionado_id = None
        return dict(item), ""

    def calcular_previsao(self, executor_id: object, jogada: Dict[str, object], energia_disponivel: float | None, ignorar_custo: bool = False) -> Tuple[float, bool]:
        teste = dict(jogada)
        teste["executor_id"] = self._normalizar_id(executor_id)
        permitido, _, custo = self.pode_adicionar(teste, energia_disponivel=energia_disponivel, ignorar_custo=ignorar_custo)
        return float(custo), bool(permitido)

    @staticmethod
    def custo_movimento(pokemon, origem: tuple[float, float], destino: tuple[float, float]) -> float:
        try:
            peso = float(getattr(pokemon, "Peso", 0.0) or 0.0)
        except (TypeError, ValueError):
            peso = 0.0
        custo_por_tile = min(30, round(peso / 20.0)) + 5
        dist = math.dist((float(origem[0]), float(origem[1])), (float(destino[0]), float(destino[1])))
        return max(0.0, float(custo_por_tile) * float(dist))

    def listar(self) -> List[Dict[str, object]]:
        return [dict(item) for item in self._jogadas]

    def listar_referencias(self) -> List[Dict[str, object]]:
        return list(self._jogadas)

    def limpar(self) -> None:
        self._jogadas.clear()
        self._selecionado_id = None

    def remover(self, jogada_id: object) -> Optional[Dict[str, object]]:
        try:
            alvo = int(jogada_id)
        except (TypeError, ValueError):
            return None
        for indice, item in enumerate(self._jogadas):
            if int(item.get("id") or 0) != alvo:
                continue
            removido = self._jogadas.pop(indice)
            if self._selecionado_id == alvo:
                self._selecionado_id = None
            self._recalcular_custos()
            return dict(removido)
        return None

    def _recalcular_custos(self) -> None:
        por_executor: Dict[str, int] = {}
        for item in self._jogadas:
            ex = self._normalizar_id(item.get("executor_id"))
            qnt = por_executor.get(ex, 0)
            item["custo"] = self._custo_total_para_executor(qnt, float(item.get("custo_base") or 0.0), item)
            por_executor[ex] = qnt + 1

    def selecionar(self, jogada_id: object | None) -> Optional[int]:
        if jogada_id in (None, "", 0):
            self._selecionado_id = None
            return None
        try:
            alvo = int(jogada_id)
        except (TypeError, ValueError):
            return self._selecionado_id
        if any(int(item.get("id") or 0) == alvo for item in self._jogadas):
            self._selecionado_id = alvo
        return self._selecionado_id

    def selecionado_id(self) -> Optional[int]:
        return self._selecionado_id

    def custo_reservado(self, combatente_id: object) -> float:
        chave = self._normalizar_id(combatente_id)
        total = 0.0
        for item in self._jogadas:
            if self._normalizar_id(item.get("executor_id")) != chave:
                continue
            try:
                total += float(item.get("custo") or 0.0)
            except (TypeError, ValueError):
                continue
        return total

    def quantidade_executor(self, combatente_id: object) -> int:
        return len(self._jogadas_executor(combatente_id))

    def possui_acao_executor(self, combatente_id: object, nome_acao: str) -> bool:
        chave = self._normalizar_id(combatente_id)
        nome = str(nome_acao or "").casefold()
        return any(
            self._normalizar_id(item.get("executor_id")) == chave and str(item.get("acao_chave") or "").casefold() == nome
            for item in self._jogadas
        )

    def posicao_virtual_executor(self, executor_id: object, pokemons_por_id: Dict[str, object]) -> Optional[tuple[float, float]]:
        _, construtos = self.resolver_visuais(pokemons_por_id)
        chave = self._normalizar_id(executor_id)
        if chave in construtos:
            return tuple(construtos[chave])
        pokemon = pokemons_por_id.get(chave)
        if pokemon is None:
            return None
        posicao = getattr(pokemon, "Posicao", None)
        if isinstance(posicao, (tuple, list)) and len(posicao) == 2:
            return float(posicao[0]), float(posicao[1])
        return None

    def resolver_visuais(self, pokemons_por_id: Dict[str, object]) -> Tuple[List[Dict[str, object]], Dict[str, tuple[float, float]]]:
        posicoes: Dict[str, tuple[float, float]] = {}
        for chave, pokemon in (pokemons_por_id or {}).items():
            pos = getattr(pokemon, "Posicao", None)
            if isinstance(pos, (tuple, list)) and len(pos) == 2:
                posicoes[str(chave)] = (float(pos[0]), float(pos[1]))

        jogadas_visuais: List[Dict[str, object]] = []
        construtos: Dict[str, tuple[float, float]] = {}
        for item in self._jogadas:
            chave = self._normalizar_id(item.get("executor_id"))
            origem = posicoes.get(chave)
            if origem is None:
                continue
            visual = dict(item)
            visual["origem_mundo"] = origem
            payload = visual.get("payload") if isinstance(visual.get("payload"), dict) else {}
            for payload_chave in ("ponto_a", "ponto_b", "segmentos", "impacto_mundo", "zona_explosao", "zonas_explosao", "alvo_ids"):
                if payload_chave in payload and payload_chave not in visual:
                    visual[payload_chave] = payload[payload_chave]
            jogadas_visuais.append(visual)

            estilo = str(item.get("estilo") or "").casefold()
            if (
                (item.get("tipo_movimento") and not item.get("troca_reserva_id"))
                or estilo in {"dash", "impulso"}
            ) and isinstance(item.get("destino_mundo"), (tuple, list)) and len(item.get("destino_mundo")) == 2:
                destino = item.get("destino_mundo")
                posicoes[chave] = (float(destino[0]), float(destino[1]))
                construtos[chave] = posicoes[chave]

        return jogadas_visuais, construtos
