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

    def buscar_propriedades_ataque(self, ataque):
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

    def ataque_esta_disponivel(self, ataque):
        props = self.buscar_propriedades_ataque(ataque)
        if not isinstance(props, dict):
            return False
        return str(props.get("estilo_logico") or "").strip().lower() != "passivo"

    def iniciar_preparacao_ataque(self, pokemon, ataque):
        if pokemon is None or ataque is None:
            return False
        props = self.buscar_propriedades_ataque(ataque)
        if not props:
            return False
        estilo = str(props.get("estilo_logico") or "").strip().lower()
        if estilo == "passivo":
            return False
        self.pokemon_origem = pokemon
        self.ataque_selecionado = dict(ataque)
        if estilo == "ativo":
            return self.adicionar_acao(self._criar_acao_ataque(pokemon, ataque, None))
        origem = self.arena.centro_area_tela(getattr(pokemon, "AreaId", None), self.controlador.camera)
        self.indicador_previa = IndicadorAtaque().configurar(origem, origem, "ataque")
        self.estado_montagem = "preparando_ataque"
        return True

    def atualizar_preparacao(self, pos_mouse):
        if self.indicador_previa is not None:
            self.indicador_previa.atualizar(destino_atual=pos_mouse)

    def confirmar_alvo(self, area_id):
        if self.pokemon_origem is None or self.ataque_selecionado is None:
            return False
        props = self.buscar_propriedades_ataque(self.ataque_selecionado) or {}
        alvo_cfg = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        if bool(alvo_cfg.get("exige_area_ocupada")) and not self.arena.area_esta_ocupada(area_id):
            return False
        ok = self.adicionar_acao(self._criar_acao_ataque(self.pokemon_origem, self.ataque_selecionado, area_id))
        self.cancelar_previa()
        return ok

    def iniciar_arraste_pokemon(self, pokemon, pos_mouse):
        self.pokemon_origem = pokemon
        origem = self.arena.centro_area_tela(getattr(pokemon, "AreaId", None), self.controlador.camera)
        self.indicador_previa = IndicadorAtaque().configurar(origem, pos_mouse, "movimento")
        self.estado_montagem = "arrastando"

    def atualizar_arraste(self, pos_mouse):
        self.atualizar_preparacao(pos_mouse)

    def soltar_arraste(self, pos_mouse):
        poke = self.pokemon_origem
        if poke is None:
            return False
        slot = self.arena.reserva_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if slot is not None:
            destino = self.controlador.pokemons_por_id.get(slot.get("pokemon_id"))
            ok = self.preparar_troca_reserva(poke, destino)
            self.cancelar_previa()
            return ok
        area_id = self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if not area_id:
            self.cancelar_previa()
            return False
        destino = self.arena.pokemon_na_area(area_id)
        if destino is None:
            ok = self.preparar_movimento(poke, area_id)
        else:
            ok = self.preparar_troca_posicao(poke, destino)
        self.cancelar_previa()
        return ok

    def preparar_movimento(self, pokemon, area_destino):
        if pokemon is None or not pokemon.esta_ativo() or not pokemon.esta_vivo():
            return False
        area = self.arena.obter_area_por_id(area_destino)
        if not area or int(area.get("lado_id", -1)) != int(getattr(pokemon, "lado_id", -2)):
            return False
        acao = {
            "tipo": "movimento",
            "estilo": "movimento",
            "pokemon_id": pokemon.id_batalha,
            "lado_id": pokemon.lado_id,
            "rodada": self.controlador.rodada_atual,
            "destino": {"tipo": "area", "area_id": area_destino},
        }
        return self.adicionar_acao(acao)

    def preparar_troca_posicao(self, pokemon_origem, pokemon_destino):
        if pokemon_origem is None or pokemon_destino is None:
            return False
        if int(getattr(pokemon_origem, "lado_id", -1)) != int(getattr(pokemon_destino, "lado_id", -2)):
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
        if pokemon_ativo is None or pokemon_reserva is None:
            return False
        if not pokemon_ativo.esta_ativo() or pokemon_ativo.esta_na_reserva() or not pokemon_reserva.esta_na_reserva():
            return False
        if int(getattr(pokemon_ativo, "lado_id", -1)) != int(getattr(pokemon_reserva, "lado_id", -2)):
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

    def _criar_acao_ataque(self, pokemon, ataque, area_id):
        code = int(float(ataque.get("Code") or ataque.get("code") or 0))
        return {
            "tipo": "ataque",
            "estilo": str((self.buscar_propriedades_ataque(ataque) or {}).get("estilo_logico") or "alvo"),
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
        self.recalcular_previsao_energia()

    def cancelar_previa(self):
        self.indicador_previa = None
        self.pokemon_origem = None
        self.ataque_selecionado = None
        self.estado_montagem = "ocioso"

    def calcular_custo_acao(self, pokemon, acao_base, ordem_pokemon=1):
        tipo = str((acao_base or {}).get("tipo") or "")
        if tipo == "movimento" or tipo == "troca_posicao":
            base = float(self.custo_movimento)
        elif tipo == "troca_reserva":
            base = float(self.custo_troca_reserva)
        else:
            at = (acao_base or {}).get("ataque") if isinstance((acao_base or {}).get("ataque"), dict) else {}
            props = self.buscar_propriedades_ataque(at)
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
            estilo = "passivo" if estilo_csv == "passivo" else "ativo" if estilo_csv == "ativa" else "alvo"
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
