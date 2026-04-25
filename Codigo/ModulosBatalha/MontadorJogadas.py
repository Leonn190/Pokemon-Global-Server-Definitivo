from __future__ import annotations

import csv
import json
from pathlib import Path

from Codigo.ModulosBatalha.IndicadorAtaque import IndicadorAtaque


class MontadorJogadas:
    def __init__(self, controlador):
        self.controlador = controlador
        self.arena = controlador.arena
        self.hud = controlador.hud
        self.propriedades_ataques = self.carregar_propriedades_ataques()
        self.acoes_preparadas = []
        self.indicadores_preparados = []
        self.indicador_previa = None
        self.pokemon_origem = None
        self.ataque_selecionado = None
        self.estado_montagem = "ocioso"
        self.proximo_id_local = 1
        self.acao_selecionada_id = None
        self.previa_energia_por_pokemon = {}
        self.limite_acoes_jogada = 5
        self.limite_acoes_por_pokemon = 2
        self.multiplicador_segunda_acao = 1.10
        self.custo_movimento = 10
        self.custo_troca_reserva = 15
        self._areas_invalidas_preview: set[str] = set()
        self._slots_destacados: set[str] = set()

    def carregar_propriedades_ataques(self):
        caminho = Path(__file__).resolve().parents[2] / "Dados" / "Pokemon Global Server - PropriedadesAtaques.json"
        if not caminho.exists():
            return {}
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except Exception:
            return {}
        ataques = dados.get("ataques") if isinstance(dados, dict) else {}
        return ataques if isinstance(ataques, dict) else {}

    @staticmethod
    def normalizar_estilo_logico(valor) -> str:
        bruto = str(valor or "").strip().casefold()
        if bruto in {"passivo", "passiva"}:
            return "passivo"
        if bruto in {"ativo", "ativa"}:
            return "ativo"
        if bruto == "alvo":
            return "alvo"
        return ""

    def obter_props_ataque(self, ataque):
        if not isinstance(ataque, dict):
            return None
        code = str(ataque.get("Code") or ataque.get("code") or "").strip()
        if code and code in self.propriedades_ataques:
            return self.propriedades_ataques.get(code)
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip().casefold()
        for item in self.propriedades_ataques.values():
            if str(item.get("nome") or "").strip().casefold() == nome:
                return item
        return None

    def buscar_propriedades_ataque(self, ataque):
        return self.obter_props_ataque(ataque)

    def ataque_esta_disponivel(self, ataque):
        props = self.obter_props_ataque(ataque)
        if not isinstance(props, dict):
            return False
        return self.normalizar_estilo_logico(props.get("estilo_logico")) != "passivo"

    def pokemon_pode_ser_controlado(self, pokemon):
        if pokemon is None:
            return False
        if not bool(getattr(pokemon, "Vivo", True)):
            return False
        if bool(self.controlador.modo_teste):
            return True
        return int(getattr(pokemon, "lado_id", -1)) == int(self.controlador.lado_jogador)

    def iniciar_preparacao_ataque(self, pokemon, ataque):
        if pokemon is None or ataque is None:
            return False
        if not self.pokemon_pode_ser_controlado(pokemon) or not pokemon.esta_ativo() or pokemon.esta_na_reserva():
            return False
        props = self.obter_props_ataque(ataque)
        if not isinstance(props, dict):
            return False
        estilo = self.normalizar_estilo_logico(props.get("estilo_logico"))
        if estilo == "passivo" or not estilo:
            return False
        self.cancelar_previa()
        self.pokemon_origem = pokemon
        self.ataque_selecionado = dict(ataque)
        if estilo == "ativo":
            ok = self.adicionar_acao(self._criar_acao_ataque(pokemon, ataque, None))
            self.cancelar_previa()
            return ok
        origem = self.arena.centro_area_tela(getattr(pokemon, "AreaId", None), self.controlador.camera)
        self.indicador_previa = IndicadorAtaque().configurar(origem, origem, "ataque")
        self.estado_montagem = "preparando_ataque"
        self._areas_invalidas_preview = set()
        self.atualizar_preparacao(origem)
        return True

    def _lados_permitidos(self, props):
        cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        lados = cfg.get("lados_permitidos")
        if isinstance(lados, str):
            lados = [lados]
        normalizados = {str(v or "").strip().casefold() for v in (lados or ["lado_oposto"])}
        if "todos" in normalizados:
            normalizados.add("qualquer_lado")
        return normalizados

    def area_valida_para_ataque(self, pokemon, ataque, area_id):
        props = self.obter_props_ataque(ataque)
        if not isinstance(props, dict):
            return False
        if self.normalizar_estilo_logico(props.get("estilo_logico")) != "alvo":
            return False
        area = self.arena.obter_area_por_id(area_id)
        if area is None:
            return False
        if not self.pokemon_pode_ser_controlado(pokemon) or not pokemon.esta_ativo() or pokemon.esta_na_reserva():
            return False
        area_usuario = str(getattr(pokemon, "AreaId", "") or "")
        lado_usuario = int(getattr(pokemon, "lado_id", -1))
        lado_destino = int(area.get("lado_id", -2))
        lados = self._lados_permitidos(props)
        if "qualquer_lado" not in lados:
            permitido = False
            if "self" in lados and str(area_id) == area_usuario:
                permitido = True
            if "mesmo_lado" in lados and lado_destino == lado_usuario:
                permitido = True
            if "lado_oposto" in lados and lado_destino != lado_usuario:
                permitido = True
            if not permitido:
                return False
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        if bool(alvo_cfg.get("exige_area_ocupada")) and not self.arena.area_esta_ocupada(area_id):
            return False
        return True

    def listar_areas_validas_ataque(self, pokemon, ataque):
        return [a.get("id") for a in self.arena._areas if self.area_valida_para_ataque(pokemon, ataque, a.get("id"))]

    def area_valida_para_movimento(self, pokemon, area_id):
        if pokemon is None or not pokemon.esta_vivo() or not pokemon.esta_ativo() or pokemon.esta_na_reserva():
            return False
        if str(area_id) == str(getattr(pokemon, "AreaId", "")):
            return False
        area = self.arena.obter_area_por_id(area_id)
        if area is None:
            return False
        if int(area.get("lado_id", -1)) != int(getattr(pokemon, "lado_id", -2)):
            return False
        return self.arena.pokemon_na_area(area_id) is None

    def area_valida_para_troca_posicao(self, pokemon, area_id):
        destino = self.arena.pokemon_na_area(area_id)
        if destino is None or pokemon is None:
            return False
        if str(destino.id_batalha) == str(pokemon.id_batalha):
            return False
        if not destino.esta_ativo() or destino.esta_na_reserva() or not destino.esta_vivo():
            return False
        return int(getattr(destino, "lado_id", -1)) == int(getattr(pokemon, "lado_id", -2))

    def slot_valido_para_troca_reserva(self, pokemon, slot):
        if pokemon is None or slot is None:
            return False
        if not pokemon.esta_vivo() or not pokemon.esta_ativo() or pokemon.esta_na_reserva():
            return False
        destino = self.controlador.pokemons_por_id.get(str(slot.get("pokemon_id") or ""))
        if destino is None:
            return False
        if not destino.esta_na_reserva() or not destino.esta_vivo():
            return False
        if int(getattr(destino, "lado_id", -1)) != int(getattr(pokemon, "lado_id", -2)):
            return False
        return True

    def atualizar_preparacao(self, pos_mouse):
        if self.indicador_previa is None:
            return
        self._areas_invalidas_preview = set()
        self._slots_destacados = set()
        if self.estado_montagem == "preparando_ataque":
            area_hover = self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera)
            if area_hover:
                valido = self.area_valida_para_ataque(self.pokemon_origem, self.ataque_selecionado, area_hover)
                destino = self.arena.centro_area_tela(area_hover, self.controlador.camera) or pos_mouse
                self.indicador_previa.definir_validade(valido)
                self.indicador_previa.definir_destino_snap(area_id=area_hover, pos=destino, valido=valido)
                if not valido:
                    self._areas_invalidas_preview.add(str(area_hover))
            else:
                self.indicador_previa.definir_validade(True)
                self.indicador_previa.definir_destino_snap(pos=pos_mouse, valido=True)
            self.indicador_previa.atualizar(destino_atual=self.indicador_previa.destino)
            return

        if self.estado_montagem != "arrastando":
            return
        poke = self.pokemon_origem
        slot = self.arena.reserva_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if self.slot_valido_para_troca_reserva(poke, slot):
            destino = self.arena.centro_slot_reserva(slot.get("pokemon_id"), self.controlador.camera) or pos_mouse
            self.indicador_previa.tipo_acao = "troca_reserva"
            self.indicador_previa.definir_validade(True)
            self.indicador_previa.definir_destino_snap(slot_id=slot.get("id_slot"), pos=destino, valido=True)
            self._slots_destacados.add(str(slot.get("id_slot")))
            self.indicador_previa.atualizar(destino_atual=destino)
            return

        area_hover = self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if area_hover:
            if self.area_valida_para_movimento(poke, area_hover):
                self.indicador_previa.tipo_acao = "movimento"
                self.indicador_previa.definir_validade(True)
                destino = self.arena.centro_area_tela(area_hover, self.controlador.camera) or pos_mouse
                self.indicador_previa.definir_destino_snap(area_id=area_hover, pos=destino, valido=True)
                self.indicador_previa.atualizar(destino_atual=destino)
                return
            if self.area_valida_para_troca_posicao(poke, area_hover):
                self.indicador_previa.tipo_acao = "troca_posicao"
                self.indicador_previa.definir_validade(True)
                destino = self.arena.centro_area_tela(area_hover, self.controlador.camera) or pos_mouse
                self.indicador_previa.definir_destino_snap(area_id=area_hover, pos=destino, valido=True)
                self.indicador_previa.atualizar(destino_atual=destino)
                return
            self._areas_invalidas_preview.add(str(area_hover))
            self.indicador_previa.definir_destino_snap(area_id=area_hover, pos=self.arena.centro_area_tela(area_hover, self.controlador.camera) or pos_mouse, valido=False)
        else:
            self.indicador_previa.definir_destino_snap(pos=pos_mouse, valido=False)
        self.indicador_previa.definir_validade(False)
        self.indicador_previa.atualizar(destino_atual=self.indicador_previa.destino)

    def confirmar_alvo(self, area_id):
        pokemon = self.pokemon_origem
        ataque = self.ataque_selecionado
        if pokemon is None or ataque is None:
            return False
        props = self.obter_props_ataque(ataque)
        if not isinstance(props, dict):
            return False
        if self.normalizar_estilo_logico(props.get("estilo_logico")) != "alvo":
            return False
        if not self.area_valida_para_ataque(pokemon, ataque, area_id):
            self._areas_invalidas_preview = {str(area_id)} if area_id else set()
            if self.indicador_previa is not None:
                self.indicador_previa.definir_validade(False)
            return False
        ok = self.adicionar_acao(self._criar_acao_ataque(pokemon, ataque, area_id))
        if ok:
            self.cancelar_previa()
        return ok

    def iniciar_arraste_pokemon(self, pokemon, pos_mouse):
        if pokemon is None or not self.pokemon_pode_ser_controlado(pokemon) or not pokemon.esta_ativo() or pokemon.esta_na_reserva():
            return False
        self.cancelar_previa()
        self.pokemon_origem = pokemon
        origem = self.arena.centro_area_tela(getattr(pokemon, "AreaId", None), self.controlador.camera)
        self.indicador_previa = IndicadorAtaque().configurar(origem, pos_mouse, "movimento")
        self.estado_montagem = "arrastando"
        return True

    def atualizar_arraste(self, pos_mouse):
        self.atualizar_preparacao(pos_mouse)

    def soltar_arraste(self, pos_mouse):
        poke = self.pokemon_origem
        if poke is None:
            return False
        slot = self.arena.reserva_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if self.slot_valido_para_troca_reserva(poke, slot):
            ok = self.preparar_troca_reserva(poke, self.controlador.pokemons_por_id.get(slot.get("pokemon_id")))
            self.cancelar_previa()
            return ok
        area_id = self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if not area_id or str(area_id) == str(getattr(poke, "AreaId", "")):
            self.cancelar_previa()
            return False
        destino = self.arena.pokemon_na_area(area_id)
        ok = self.preparar_movimento(poke, area_id) if destino is None else self.preparar_troca_posicao(poke, destino)
        self.cancelar_previa()
        return ok

    def preparar_movimento(self, pokemon, area_destino):
        if not self.area_valida_para_movimento(pokemon, area_destino):
            return False
        acao = {
            "tipo": "movimento",
            "estilo": "movimento",
            "pokemon_id": pokemon.id_batalha,
            "lado_id": pokemon.lado_id,
            "rodada": self.controlador.rodada_atual,
            "origem": {"tipo": "area", "area_id": pokemon.AreaId},
            "destino": {"tipo": "area", "area_id": area_destino},
        }
        return self.adicionar_acao(acao)

    def preparar_troca_posicao(self, pokemon_origem, pokemon_destino):
        if pokemon_origem is None or pokemon_destino is None:
            return False
        if str(getattr(pokemon_origem, "id_batalha", "")) == str(getattr(pokemon_destino, "id_batalha", "")):
            return False
        if not self.area_valida_para_troca_posicao(pokemon_origem, getattr(pokemon_destino, "AreaId", None)):
            return False
        acao = {
            "tipo": "troca_posicao",
            "estilo": "movimento",
            "pokemon_id": pokemon_origem.id_batalha,
            "pokemon_destino_id": pokemon_destino.id_batalha,
            "lado_id": pokemon_origem.lado_id,
            "rodada": self.controlador.rodada_atual,
            "origem": {"tipo": "area", "area_id": pokemon_origem.AreaId},
            "destino": {"tipo": "area", "area_id": pokemon_destino.AreaId},
        }
        return self.adicionar_acao(acao)

    def preparar_troca_reserva(self, pokemon_ativo, pokemon_reserva):
        slot_valido = self.slot_valido_para_troca_reserva(pokemon_ativo, {"pokemon_id": getattr(pokemon_reserva, "id_batalha", None)})
        if not slot_valido:
            return False
        acao = {
            "tipo": "troca_reserva",
            "estilo": "movimento",
            "pokemon_id": pokemon_ativo.id_batalha,
            "pokemon_reserva_id": pokemon_reserva.id_batalha,
            "troca_reserva_id": pokemon_reserva.id_batalha,
            "lado_id": pokemon_ativo.lado_id,
            "rodada": self.controlador.rodada_atual,
            "origem": {"tipo": "area", "area_id": pokemon_ativo.AreaId},
            "destino": {"tipo": "reserva", "pokemon_id": pokemon_reserva.id_batalha},
        }
        return self.adicionar_acao(acao)

    def obter_areas_destacadas(self):
        if self.estado_montagem == "preparando_ataque" and self.pokemon_origem is not None and self.ataque_selecionado is not None:
            return self.listar_areas_validas_ataque(self.pokemon_origem, self.ataque_selecionado)
        if self.estado_montagem != "arrastando" or self.pokemon_origem is None:
            return []
        poke = self.pokemon_origem
        retorno = []
        for area in self.arena._areas:
            aid = str(area.get("id"))
            if self.area_valida_para_movimento(poke, aid) or self.area_valida_para_troca_posicao(poke, aid):
                retorno.append(aid)
        return retorno

    def obter_slots_reserva_destacados(self):
        if self.estado_montagem != "arrastando" or self.pokemon_origem is None:
            return []
        validos = []
        for lado in ("jogador", "inimigo"):
            for slot in self.arena.obter_slots_reserva(lado):
                if self.slot_valido_para_troca_reserva(self.pokemon_origem, slot):
                    validos.append(slot.get("id_slot"))
        return validos

    def obter_areas_invalidas_preview(self):
        return list(self._areas_invalidas_preview)

    def area_valida_para_preparacao(self, area_id):
        return str(area_id) in set(self.obter_areas_destacadas())

    def _criar_acao_ataque(self, pokemon, ataque, area_id):
        code = int(float(ataque.get("Code") or ataque.get("code") or 0))
        estilo = self.normalizar_estilo_logico((self.obter_props_ataque(ataque) or {}).get("estilo_logico")) or "alvo"
        return {
            "tipo": "ataque",
            "estilo": estilo,
            "pokemon_id": pokemon.id_batalha,
            "lado_id": pokemon.lado_id,
            "rodada": self.controlador.rodada_atual,
            "ataque": {"ID": code, "Code": code, "nome": ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome")},
            "alvo": {"tipo": "area", "area_id": area_id} if area_id else None,
        }

    def adicionar_acao(self, acao):
        if not isinstance(acao, dict):
            return False
        lado = int(acao.get("lado_id", -1))
        acoes_lado = [a for a in self.acoes_preparadas if int(a.get("lado_id", -1)) == lado]
        if len(acoes_lado) >= self.limite_acoes_jogada:
            return False
        pid = str(acao.get("pokemon_id") or "")
        if sum(1 for a in acoes_lado if str(a.get("pokemon_id") or "") == pid) >= self.limite_acoes_por_pokemon:
            return False
        poke = self.controlador.pokemons_por_id.get(pid)
        custo = self.calcular_custo_acao(poke, acao, ordem_pokemon=sum(1 for a in acoes_lado if str(a.get("pokemon_id") or "") == pid) + 1)
        if (not self.controlador.modo_teste) and (not self.pode_pagar_acao(poke, custo)):
            return False
        acao = dict(acao)
        acao["id"] = self.proximo_id_local
        acao["id_local"] = self.proximo_id_local
        acao["ordem_local"] = len(acoes_lado)
        acao["custo_previsto"] = custo
        acao["modo_teste"] = bool(self.controlador.modo_teste)
        acao["executor"] = poke
        self.proximo_id_local += 1
        self.acoes_preparadas.append(acao)
        self._adicionar_indicador_para_acao(acao)
        self.recalcular_previsao_energia()
        return True

    def _adicionar_indicador_para_acao(self, acao):
        tipo = str(acao.get("tipo"))
        origem = destino = None
        if tipo == "ataque":
            origem = self.arena.centro_area_tela(self.controlador.pokemons_por_id[acao["pokemon_id"]].AreaId, self.controlador.camera)
            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            destino = self.arena.centro_area_tela(alvo.get("area_id"), self.controlador.camera)
        elif tipo in {"movimento", "troca_posicao"}:
            origem = self.arena.centro_area_tela((acao.get("origem") or {}).get("area_id", self.controlador.pokemons_por_id[acao["pokemon_id"]].AreaId), self.controlador.camera)
            destino = self.arena.centro_area_tela((acao.get("destino") or {}).get("area_id"), self.controlador.camera)
        elif tipo == "troca_reserva":
            origem = self.arena.centro_area_tela((acao.get("origem") or {}).get("area_id"), self.controlador.camera)
            destino = self.arena.centro_slot_reserva((acao.get("destino") or {}).get("pokemon_id"), self.controlador.camera)
        if origem and destino:
            self.indicadores_preparados.append(IndicadorAtaque().configurar(origem, destino, tipo, estado="preparado", id_acao=acao.get("id")))

    def remover_acao(self, id_local):
        alvo = int(id_local)
        self.acoes_preparadas = [a for a in self.acoes_preparadas if int(a.get("id") or 0) != alvo]
        self.indicadores_preparados = [i for i in self.indicadores_preparados if int(i.id_acao or 0) != alvo]
        if self.acao_selecionada_id == alvo:
            self.acao_selecionada_id = None
        self.recalcular_previsao_energia()

    def selecionar_acao(self, id_local):
        self.acao_selecionada_id = int(id_local) if id_local is not None else None

    def limpar_jogada(self):
        self.acoes_preparadas = []
        self.indicadores_preparados = []
        self.indicador_previa = None
        self.acao_selecionada_id = None
        self.cancelar_previa()
        self.recalcular_previsao_energia()

    def cancelar_previa(self):
        self.indicador_previa = None
        self.pokemon_origem = None
        self.ataque_selecionado = None
        self.estado_montagem = "ocioso"
        self._areas_invalidas_preview = set()
        self._slots_destacados = set()

    def calcular_custo_acao(self, pokemon, acao_base, ordem_pokemon=1):
        tipo = str((acao_base or {}).get("tipo") or "")
        if tipo == "movimento" or tipo == "troca_posicao":
            base = float(self.custo_movimento)
        elif tipo == "troca_reserva":
            base = float(self.custo_troca_reserva)
        else:
            at = (acao_base or {}).get("ataque") if isinstance((acao_base or {}).get("ataque"), dict) else {}
            props = self.obter_props_ataque(at)
            base = float((props or {}).get("custo", at.get("Custo") or at.get("custo") or 0.0))
        mult = self.multiplicador_segunda_acao if int(ordem_pokemon) >= 2 else 1.0
        return round(base * mult, 2)

    def recalcular_previsao_energia(self):
        custos = {}
        por_pokemon = {}
        for a in self.acoes_preparadas:
            pid = str(a.get("pokemon_id") or "")
            por_pokemon[pid] = por_pokemon.get(pid, 0) + 1
            a["custo_previsto"] = self.calcular_custo_acao(self.controlador.pokemons_por_id.get(pid), a, ordem_pokemon=por_pokemon[pid])
            custos[pid] = custos.get(pid, 0.0) + float(a.get("custo_previsto") or 0.0)
        self.previa_energia_por_pokemon = custos
        for p in self.controlador.pokemons:
            custo = float(custos.get(p.id_batalha, 0.0))
            p.CustoPrevistoPendente = custo
            p.EnergiaPrevista = float(getattr(p, "Energia", 0.0)) - custo
            p.PodePagarPrevisao = bool(self.controlador.modo_teste or p.EnergiaPrevista >= 0.0)

    def energia_prevista_pokemon(self, pokemon_id):
        poke = self.controlador.pokemons_por_id.get(str(pokemon_id or ""))
        if poke is None:
            return 0.0
        return float(getattr(poke, "EnergiaPrevista", getattr(poke, "Energia", 0.0)))

    def pode_pagar_acao(self, pokemon, custo):
        if pokemon is None:
            return False
        return float(getattr(pokemon, "Energia", 0.0)) - float(self.previa_energia_por_pokemon.get(pokemon.id_batalha, 0.0)) - float(custo) >= 0.0

    def gerar_pacote_jogada(self):
        return {
            "id_partida": self.controlador.id_partida,
            "rodada": self.controlador.rodada_atual,
            "modo_teste": False,
            "lado_id": self.controlador.lado_jogador,
            "acoes": [self._serializar_acao(a) for a in self.acoes_preparadas if int(a.get("lado_id", -1)) == int(self.controlador.lado_jogador)],
        }

    def gerar_pacote_jogadas_modo_teste(self):
        por_lado = {}
        for a in self.acoes_preparadas:
            lado = int(a.get("lado_id", -1))
            por_lado.setdefault(lado, []).append(self._serializar_acao(a))
        return {
            "id_partida": self.controlador.id_partida,
            "rodada": self.controlador.rodada_atual,
            "modo_teste": True,
            "jogadas": [{"lado_id": lado, "acoes": acoes} for lado, acoes in sorted(por_lado.items())],
        }

    def _serializar_acao(self, acao):
        out = {k: v for k, v in acao.items() if k not in {"executor"}}
        return out


def gerar_propriedades_ataques_json(csv_path: Path, out_path: Path):
    ataques = {}
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            code = str(row.get("Code") or idx)
            nome = str(row.get("Ataque") or "").strip()
            if not nome:
                continue
            estilo_csv = str(row.get("Estilo") or "alvo").strip().lower()
            estilo = "passivo" if estilo_csv in {"passivo", "passiva"} else "ativo" if estilo_csv in {"ativo", "ativa"} else "alvo"
            base = {
                "ID": int(float(code)),
                "Code": int(float(code)),
                "nome": nome,
                "custo": int(float(row.get("Custo") or 0)),
                "estilo_logico": estilo,
                "animacao": {"contato": "avanco", "projetil": None},
                "execute_principal": f"ataque_{nome.lower().replace(' ', '_')}",
                "parametros": {"tipo": str(row.get("Tipo") or "normal").lower()},
            }
            if estilo == "alvo":
                base["alvificacao"] = {
                    "tipo": "area",
                    "quantidade": 1,
                    "lados_permitidos": ["lado_oposto"],
                    "exige_area_ocupada": False,
                }
            ataques[str(int(float(code)))] = base
    out = {"schema_version": 1, "ataques": ataques}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
