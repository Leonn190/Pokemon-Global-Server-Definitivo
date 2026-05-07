from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

from Codigo.ModulosBatalha.IndicadorAtaque import IndicadorAtaque
from Codigo.ModulosGerais.PropriedadesAtaques import carregar_propriedades_ataques


class MontadorJogadas:
    TIPOS_GLOBAIS = {"arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"}
    TIPOS_LINHA = {"linha", "fileira", "row", "line"}
    TIPOS_COLUNA = {"coluna", "column"}

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
        self.area_alvo_previa = None
        self.alvo_previa_mundo = None
        self.alvos_config = []
        self.alvos_selecionados = []
        self.indice_grupo_alvo = 0
        self.indicadores_alvos_parciais = []
        self.estado_montagem = "ocioso"
        self.proximo_id_local = 1
        self.acao_selecionada_id = None
        self.previa_energia_por_pokemon = {}
        self.limite_acoes_jogada = 5
        self.limite_acoes_por_pokemon = 2
        self.multiplicador_segunda_acao = 1.10
        self.custo_movimento = 15
        self.custo_troca_posicao = 20
        self.custo_troca_reserva = 20

    def carregar_propriedades_ataques(self):
        ataques = carregar_propriedades_ataques()
        if ataques:
            return ataques
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
        code = str(ataque.get("ID") or ataque.get("Code") or ataque.get("code") or "").strip()
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

    def _alvo_fallback(self):
        return {
            "tipo": "area",
            "quantidade": 1,
            "lados_permitidos": ["lado_oposto"],
            "exige_area_ocupada": False,
            "inclui_reserva": False,
            "area_id": None,
        }

    @staticmethod
    def _bool_config_alvo(valor):
        if isinstance(valor, bool):
            return valor
        texto = str(valor or "").strip().lower()
        if texto in {"1", "true", "sim", "yes", "on"}:
            return True
        if texto in {"0", "false", "nao", "no", "off", ""}:
            return False
        return bool(valor)

    def _normalizar_config_alvo(self, config):
        base = self._alvo_fallback()
        if isinstance(config, dict):
            for chave in ("tipo", "quantidade", "lados_permitidos", "exige_area_ocupada", "inclui_reserva", "area_id"):
                if chave in config:
                    base[chave] = copy.deepcopy(config.get(chave))
        try:
            base["quantidade"] = max(1, int(float(base.get("quantidade") or 1)))
        except (TypeError, ValueError):
            base["quantidade"] = 1
        permitidos = base.get("lados_permitidos")
        if isinstance(permitidos, str):
            permitidos = [permitidos]
        if not isinstance(permitidos, (list, tuple, set)):
            permitidos = ["lado_oposto"]
        base["lados_permitidos"] = [str(item) for item in permitidos if str(item or "").strip()]
        if not base["lados_permitidos"]:
            base["lados_permitidos"] = ["lado_oposto"]
        base["tipo"] = str(base.get("tipo") or "area").strip().lower() or "area"
        base["exige_area_ocupada"] = self._bool_config_alvo(base.get("exige_area_ocupada"))
        base["inclui_reserva"] = self._bool_config_alvo(base.get("inclui_reserva"))
        if base.get("area_id"):
            base["area_id"] = str(base.get("area_id")).strip().upper()
        else:
            base["area_id"] = None
        return base

    def _normalizar_alvos_config(self, props):
        props = props if isinstance(props, dict) else {}
        alvificacao = props.get("alvificacao") if isinstance(props.get("alvificacao"), dict) else {}
        alvos = alvificacao.get("alvos") if isinstance(alvificacao, dict) else None
        if isinstance(alvos, list):
            configs = [self._normalizar_config_alvo(item) for item in alvos if isinstance(item, dict)]
            if configs:
                return configs
        if isinstance(alvificacao, dict) and any(chave in alvificacao for chave in ("tipo", "quantidade", "lados_permitidos", "exige_area_ocupada", "inclui_reserva", "area_id")):
            return [self._normalizar_config_alvo(alvificacao)]
        return [self._alvo_fallback()]

    def _area_ancora_por_config(self, area_id, config=None):
        alvo_cfg = self._normalizar_config_alvo(config or {})
        tipo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        if tipo == "fixa":
            return str(alvo_cfg.get("area_id") or area_id or "").upper()
        area_id = str(area_id or "").upper()
        if not area_id:
            return ""
        areas = self.areas_afetadas_por_config(area_id, alvo_cfg)
        if tipo in self.TIPOS_GLOBAIS:
            return self._area_central_areas(areas) or (areas[0] if areas else area_id)
        if tipo in self.TIPOS_LINHA or tipo in self.TIPOS_COLUNA:
            return areas[0] if areas else area_id
        return area_id

    @staticmethod
    def _area_central_areas(areas):
        areas = [str(area or "").upper() for area in list(areas or []) if str(area or "").strip()]
        if not areas:
            return ""
        for area_id in areas:
            if area_id[1:] == "5":
                return area_id
        return areas[len(areas) // 2]

    def _configs_apenas_fixas(self, configs):
        configs = list(configs or [])
        return bool(configs) and all(str(cfg.get("tipo") or "").strip().lower() == "fixa" and cfg.get("area_id") for cfg in configs)

    def _montar_selecoes_fixas(self):
        selecoes = []
        for grupo, config in enumerate(list(self.alvos_config or [])):
            alvo_cfg = self._normalizar_config_alvo(config)
            area_id = self._area_ancora_por_config(alvo_cfg.get("area_id"), alvo_cfg)
            if not area_id or not self.area_permitida_para_ataque(area_id, alvo_cfg):
                return []
            for ordem in range(int(alvo_cfg.get("quantidade") or 1)):
                selecoes.append(
                    {
                        "tipo": "area",
                        "area_id": area_id,
                        "grupo": grupo,
                        "ordem": ordem,
                        "config": copy.deepcopy(alvo_cfg),
                        "areas": self.areas_afetadas_por_config(area_id, alvo_cfg),
                    }
                )
        return selecoes

    def _config_grupo_alvo_atual(self):
        if not self.alvos_config:
            props = self.buscar_propriedades_ataque(self.ataque_selecionado) or {}
            self.alvos_config = self._normalizar_alvos_config(props)
        if self.indice_grupo_alvo < 0 or self.indice_grupo_alvo >= len(self.alvos_config):
            return None
        return self.alvos_config[self.indice_grupo_alvo]

    def _limpar_selecao_alvos(self):
        self.alvos_config = []
        self.alvos_selecionados = []
        self.indice_grupo_alvo = 0
        self.indicadores_alvos_parciais = []

    def iniciar_preparacao_ataque(self, pokemon, ataque):
        if pokemon is None or ataque is None:
            return False
        if self._acao_bloqueada_por_efeito(pokemon, "ataque"):
            return False
        props = self.buscar_propriedades_ataque(ataque)
        if not props:
            return False
        estilo = str(props.get("estilo_logico") or "").strip().lower()
        if estilo == "passivo":
            return False
        self.pokemon_origem = pokemon
        self.ataque_selecionado = dict(ataque)
        self.area_alvo_previa = None
        self.alvo_previa_mundo = None
        self.alvos_config = []
        self.alvos_selecionados = []
        self.indice_grupo_alvo = 0
        self.indicadores_alvos_parciais = []
        if estilo == "ativo":
            ok = self.adicionar_acao(self._criar_acao_ataque(pokemon, ataque, None))
            self.cancelar_previa()
            return ok
        self.alvos_config = self._normalizar_alvos_config(props)
        if self._configs_apenas_fixas(self.alvos_config):
            selecoes_fixas = self._montar_selecoes_fixas()
            if not selecoes_fixas or not self._selecoes_respeitam_provocando(selecoes_fixas):
                self.cancelar_previa()
                return False
            self.alvos_selecionados = selecoes_fixas
            ok = self.adicionar_acao(self._criar_acao_ataque(pokemon, ataque, None))
            self.cancelar_previa()
            return ok
        origem = self.arena.centro_area(self.area_prevista_pokemon(pokemon))
        self.indicador_previa = IndicadorAtaque().configurar(origem, origem, "ataque", coordenadas_mundo=True)
        self.estado_montagem = "preparando_ataque"
        self.recalcular_previsao_energia()
        return True

    def atualizar_preparacao(self, pos_mouse):
        if self.indicador_previa is not None:
            destino = self.controlador.camera.tela_para_mundo_tiles(pos_mouse)
            area_id = None
            alvo_mundo = None
            if self.estado_montagem == "preparando_ataque":
                hover = self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera)
                slot = self.arena.reserva_em_posicao_mouse(pos_mouse, self.controlador.camera)
                if hover and self.area_permitida_para_ataque(hover):
                    config = self._config_grupo_alvo_atual() or {}
                    area_ancora = self._area_ancora_por_config(hover, config)
                    centro = self.arena.centro_area(area_ancora)
                    if centro is not None:
                        destino = centro
                        area_id = area_ancora
                        alvo_mundo = centro
                elif slot is not None:
                    poke = self.controlador.pokemons_por_id.get(str(slot.get("pokemon_id") or ""))
                    if self.pokemon_permitido_para_ataque(poke):
                        centro = self.arena.centro_slot_reserva_mundo(slot.get("pokemon_id"))
                        if centro is not None:
                            destino = centro
                            alvo_mundo = centro
                            area_id = {"tipo": "pokemon", "pokemon_id": getattr(poke, "id_batalha", None), "reserva": True}
                if hover or slot is not None:
                    self.indicador_previa.definir_validade(area_id is not None)
                else:
                    self.indicador_previa.definir_validade(True)
            elif self.estado_montagem == "arrastando":
                alvo = self.alvo_movimento_em_posicao(pos_mouse)
                if alvo is not None:
                    destino = alvo["centro"]
                    alvo_mundo = destino
                    area_id = alvo.get("area_id")
                self.indicador_previa.definir_validade(alvo is not None or not self._mouse_sobre_alvo_movimento(pos_mouse))
            self.area_alvo_previa = area_id
            self.alvo_previa_mundo = alvo_mundo
            self.indicador_previa.atualizar(destino_atual=destino)

    def confirmar_alvo(self, area_id):
        if self.pokemon_origem is None or self.ataque_selecionado is None:
            return False
        config = self._config_grupo_alvo_atual()
        if config is None:
            return False
        if str(config.get("tipo") or "").strip().lower() == "pokemon":
            return self.confirmar_alvo_pokemon(self.arena.pokemon_na_area(area_id))
        if str(config.get("tipo") or "").strip().lower() == "fixa":
            area_id = config.get("area_id")
        if not self.area_permitida_para_ataque(area_id):
            return False
        selecao = self._montar_selecao_area(area_id, config)
        if not selecao:
            return False
        return self._registrar_selecao_alvo(selecao)

    def confirmar_alvo_pokemon(self, pokemon):
        if self.pokemon_origem is None or self.ataque_selecionado is None:
            return False
        config = self._config_grupo_alvo_atual()
        if config is None or str(config.get("tipo") or "").strip().lower() != "pokemon":
            return False
        if not self.pokemon_permitido_para_ataque(pokemon):
            return False
        selecao = self._montar_selecao_pokemon(pokemon, config)
        if not selecao:
            return False
        return self._registrar_selecao_alvo(selecao)

    def _montar_selecao_area(self, area_id, config):
        area_id = self._area_ancora_por_config(area_id, config)
        if not area_id:
            return None
        chave = self._chave_selecao_area(area_id, config)
        if self._selecao_alvo_existe(chave):
            return None
        return {
            "tipo": "area",
            "area_id": area_id,
            "grupo": int(self.indice_grupo_alvo),
            "ordem": self._quantidade_selecionada_no_grupo(self.indice_grupo_alvo),
            "config": copy.deepcopy(config),
            "areas": self.areas_afetadas_por_config(area_id, config),
            "_chave": chave,
        }

    def _montar_selecao_pokemon(self, pokemon, config):
        if pokemon is None:
            return None
        pid = str(getattr(pokemon, "id_batalha", "") or "")
        if not pid:
            return None
        chave = ("pokemon", pid)
        if self._selecao_alvo_existe(chave):
            return None
        area_id = str(getattr(pokemon, "AreaId", "") or "").upper()
        selecao = {
            "tipo": "pokemon",
            "pokemon_id": pid,
            "reserva": bool(pokemon.esta_na_reserva()),
            "grupo": int(self.indice_grupo_alvo),
            "ordem": self._quantidade_selecionada_no_grupo(self.indice_grupo_alvo),
            "config": copy.deepcopy(config),
            "_chave": chave,
        }
        if area_id:
            selecao["area_id"] = area_id
            selecao["areas"] = [area_id]
        return selecao

    def _registrar_selecao_alvo(self, selecao):
        if not isinstance(selecao, dict):
            return False
        config = self._config_grupo_alvo_atual() or {}
        selecoes_tentativas = [*self.alvos_selecionados, selecao]
        qtd_tentativa = sum(1 for alvo in selecoes_tentativas if int(alvo.get("grupo", -1)) == int(self.indice_grupo_alvo))
        proximo_indice = int(self.indice_grupo_alvo) + (1 if qtd_tentativa >= int(config.get("quantidade") or 1) else 0)
        if proximo_indice >= len(self.alvos_config) and not self._selecoes_respeitam_provocando(selecoes_tentativas):
            return False
        self.alvos_selecionados.append(selecao)
        self._adicionar_indicador_selecao_parcial(selecao)
        if self._quantidade_selecionada_no_grupo(self.indice_grupo_alvo) >= int(config.get("quantidade") or 1):
            self.indice_grupo_alvo += 1
        if self.indice_grupo_alvo < len(self.alvos_config):
            self.recalcular_previsao_energia()
            return False
        ok = self.adicionar_acao(self._criar_acao_ataque(self.pokemon_origem, self.ataque_selecionado, None))
        self.cancelar_previa()
        return ok

    def _quantidade_selecionada_no_grupo(self, indice):
        return sum(1 for alvo in self.alvos_selecionados if int(alvo.get("grupo", -1)) == int(indice))

    def _selecao_alvo_existe(self, chave):
        return any(alvo.get("_chave") == chave for alvo in self.alvos_selecionados)

    def _chave_selecao_area(self, area_id, config):
        area_id = self._area_ancora_por_config(area_id, config)
        areas = tuple(self.areas_afetadas_por_config(area_id, config))
        return ("area", str(config.get("tipo") or "area").strip().lower(), areas or (str(area_id or "").upper(),))

    def _adicionar_indicador_selecao_parcial(self, selecao):
        origem = self.arena.centro_area(self.area_prevista_pokemon(self.pokemon_origem))
        for destino in self._destinos_indicador_selecao(selecao):
            if origem and destino:
                self.indicadores_alvos_parciais.append(IndicadorAtaque().configurar(origem, destino, "ataque", estado="preparado", coordenadas_mundo=True))

    def iniciar_arraste_pokemon(self, pokemon, pos_mouse):
        if self._acao_bloqueada_por_efeito(pokemon, "movimento"):
            return False
        self.controlador.selecionar_pokemon(pokemon)
        self.pokemon_origem = pokemon
        self.ataque_selecionado = None
        self.area_alvo_previa = None
        self.alvo_previa_mundo = None
        origem = self.arena.centro_area(getattr(pokemon, "AreaId", None))
        destino = self.controlador.camera.tela_para_mundo_tiles(pos_mouse)
        self.indicador_previa = IndicadorAtaque().configurar(origem, destino, "movimento", coordenadas_mundo=True)
        self.estado_montagem = "arrastando"
        return True

    def atualizar_arraste(self, pos_mouse):
        self.atualizar_preparacao(pos_mouse)

    def soltar_arraste(self, pos_mouse):
        poke = self.pokemon_origem
        if poke is None:
            return False
        alvo = self.alvo_movimento_em_posicao(pos_mouse)
        if alvo is None:
            self.cancelar_previa()
            return False
        if alvo.get("tipo") == "reserva":
            destino = self.controlador.pokemons_por_id.get(alvo.get("pokemon_id"))
            ok = self.preparar_troca_reserva(poke, destino)
            self.cancelar_previa()
            return ok
        area_id = alvo.get("area_id")
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
        if self._acao_bloqueada_por_efeito(pokemon, "movimento"):
            return False
        if str(area_destino) == str(getattr(pokemon, "AreaId", "")):
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
        if self._acao_bloqueada_por_efeito(pokemon_origem, "troca_posicao"):
            return False
        if str(getattr(pokemon_origem, "id_batalha", "")) == str(getattr(pokemon_destino, "id_batalha", "")):
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
        if self._acao_bloqueada_por_efeito(pokemon_ativo, "troca_reserva"):
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

    def preparar_captura(self, alvo, slot_bola):
        if alvo is None or not self._captura_disponivel():
            return False
        if any(str(a.get("tipo") or "") == "captura" and int(a.get("lado_id", -1)) == int(getattr(self.controlador, "lado_jogador", -2)) for a in self.acoes_preparadas):
            return False
        if int(getattr(alvo, "lado_id", -1)) == int(getattr(self.controlador, "lado_jogador", -2)):
            return False
        if not alvo.esta_vivo() or not alvo.esta_ativo() or alvo.esta_na_reserva():
            return False
        lado_id = int(getattr(self.controlador, "lado_jogador", 50))
        item = dict((slot_bola or {}).get("item") or {})
        item_nome = str((slot_bola or {}).get("item_nome") or item.get("Nome") or item.get("nome") or "Pokeball")
        item_base_id = str((slot_bola or {}).get("item_base_id") or item.get("Code") or item.get("code") or "")
        bola = {
            "Nome": item_nome,
            "Code": item_base_id,
            "item_base_id": item_base_id,
            "quantidade": 1,
        }
        acao = {
            "tipo": "captura",
            "estilo": "captura",
            "pokemon_id": "",
            "capturador_tipo": "jogador",
            "jogador_nome": self.controlador.nome_jogador_batalha() if hasattr(self.controlador, "nome_jogador_batalha") else "Jogador",
            "lado_id": lado_id,
            "rodada": self.controlador.rodada_atual,
            "alvo": {"tipo": "pokemon", "pokemon_id": alvo.id_batalha},
            "bola": bola,
            "item_nome": item_nome,
            "item_base_id": item_base_id,
            "origem_tipo": (slot_bola or {}).get("chave"),
            "origem_slot_index": (slot_bola or {}).get("primeiro_indice"),
        }
        return self.adicionar_acao(acao)

    def _captura_disponivel(self):
        tipo = str(getattr(self.controlador, "tipo_batalha", "") or "").strip().lower()
        return tipo == "confronto" and not bool(getattr(self.controlador, "modo_teste", False))

    def _executor_captura(self):
        selecionado = getattr(self.controlador, "pokemon_selecionado", None)
        if (
            selecionado is not None
            and int(getattr(selecionado, "lado_id", -1)) == int(getattr(self.controlador, "lado_jogador", -2))
            and selecionado.esta_vivo()
            and selecionado.esta_ativo()
            and not selecionado.esta_na_reserva()
        ):
            return selecionado
        for pokemon in list(getattr(self.controlador, "pokemons", []) or []):
            if int(getattr(pokemon, "lado_id", -1)) != int(getattr(self.controlador, "lado_jogador", -2)):
                continue
            if pokemon.esta_vivo() and pokemon.esta_ativo() and not pokemon.esta_na_reserva():
                return pokemon
        return None

    def _criar_acao_ataque(self, pokemon, ataque, area_id):
        code = int(float(ataque.get("Code") or ataque.get("code") or 0))
        props = self.buscar_propriedades_ataque(ataque) or {}
        selecoes = []
        if self.alvos_selecionados:
            selecoes = [self._serializar_selecao_alvo(alvo) for alvo in self.alvos_selecionados]
        elif isinstance(area_id, dict):
            config = self._normalizar_alvos_config(props)[0]
            if str(area_id.get("tipo") or "").strip().lower() == "pokemon":
                selecao = dict(area_id)
                selecao["tipo"] = "pokemon"
                selecao["grupo"] = 0
                selecao["ordem"] = 0
                selecao["config"] = copy.deepcopy(config)
                selecoes = [self._serializar_selecao_alvo(selecao)]
        elif area_id:
            config = self._normalizar_alvos_config(props)[0]
            selecao = self._montar_selecao_area(area_id, config)
            if selecao:
                selecoes = [self._serializar_selecao_alvo(selecao)]
        alvo = {"tipo": "multi", "alvos": selecoes} if selecoes else None
        return {
            "tipo": "ataque",
            "estilo": str(props.get("estilo_logico") or "alvo"),
            "pokemon_id": pokemon.id_batalha,
            "lado_id": pokemon.lado_id,
            "rodada": self.controlador.rodada_atual,
            "ataque": {
                "ID": code,
                "Code": code,
                "nome": ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome"),
                "Tipo": ataque.get("Tipo") or ataque.get("tipo"),
            },
            "alvo": alvo,
        }

    def _serializar_selecao_alvo(self, alvo):
        saida = copy.deepcopy(alvo)
        saida.pop("_chave", None)
        return saida

    def adicionar_acao(self, acao):
        if not isinstance(acao, dict):
            return False
        lado = int(acao.get("lado_id", -1))
        acoes_lado = [a for a in self.acoes_preparadas if int(a.get("lado_id", -1)) == lado]
        if len(acoes_lado) >= self.limite_acoes_jogada:
            return False
        pid = str(acao.get("pokemon_id") or "")
        if any(self._chave_acao(a) == self._chave_acao(acao) for a in acoes_lado if str(a.get("pokemon_id") or "") == pid):
            return False
        if str(acao.get("tipo") or "") != "captura" and sum(1 for a in acoes_lado if str(a.get("pokemon_id") or "") == pid and str(a.get("tipo") or "") != "captura") >= self.limite_acoes_por_pokemon:
            return False
        poke = self.controlador.pokemons_por_id.get(pid)
        if self._acao_bloqueada_por_efeito(poke, acao.get("tipo")):
            return False
        custo = self.calcular_custo_acao(poke, acao, ordem_pokemon=sum(1 for a in acoes_lado if str(a.get("pokemon_id") or "") == pid) + 1)
        if str(acao.get("tipo") or "") != "captura" and (not self.controlador.modo_teste) and (not self.pode_pagar_acao(poke, custo)):
            return False
        acao = dict(acao)
        acao["id"] = self.proximo_id_local
        acao["id_local"] = self.proximo_id_local
        acao["ordem_local"] = len(acoes_lado)
        acao["custo_previsto"] = custo
        acao["modo_teste"] = bool(self.controlador.modo_teste)
        acao["executor"] = poke
        acao["alvo_visual"] = self._resolver_alvo_visual(acao)
        self.proximo_id_local += 1
        self.acoes_preparadas.append(acao)
        self._adicionar_indicador_para_acao(acao)
        self.recalcular_previsao_energia()
        return True

    def _adicionar_indicador_para_acao(self, acao):
        tipo = str(acao.get("tipo"))
        origem = destino = None
        if tipo == "ataque":
            origem = self.arena.centro_area(self.area_prevista_pokemon(self.controlador.pokemons_por_id[acao["pokemon_id"]]))
            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            if str(alvo.get("tipo") or "").lower() == "multi":
                for selecao in list(alvo.get("alvos") or []):
                    for destino in self._destinos_indicador_selecao(selecao):
                        if origem and destino:
                            self.indicadores_preparados.append(IndicadorAtaque().configurar(origem, destino, tipo, estado="preparado", id_acao=acao.get("id"), coordenadas_mundo=True))
                return
            if str(alvo.get("tipo") or "").lower() == "pokemon" and alvo.get("pokemon_id"):
                poke_alvo = self.controlador.pokemons_por_id.get(str(alvo.get("pokemon_id") or ""))
                destino = self._centro_visual_pokemon(poke_alvo)
                if origem and destino:
                    self.indicadores_preparados.append(IndicadorAtaque().configurar(origem, destino, tipo, estado="preparado", id_acao=acao.get("id"), coordenadas_mundo=True))
                return
            props = acao.get("propriedades") if isinstance(acao.get("propriedades"), dict) else self.buscar_propriedades_ataque(acao.get("ataque"))
            destinos = [self.arena.centro_area(aid) for aid in self.areas_afetadas_por_alvo(alvo.get("area_id"), props)]
            destinos = [d for d in destinos if d is not None] or [self.arena.centro_area(alvo.get("area_id")) or origem]
            for destino in destinos:
                if origem and destino:
                    self.indicadores_preparados.append(IndicadorAtaque().configurar(origem, destino, tipo, estado="preparado", id_acao=acao.get("id"), coordenadas_mundo=True))
            return
        elif tipo in {"movimento", "troca_posicao"}:
            origem = self.arena.centro_area((acao.get("origem") or {}).get("area_id", self.controlador.pokemons_por_id[acao["pokemon_id"]].AreaId))
            destino = self.arena.centro_area((acao.get("destino") or {}).get("area_id"))
        elif tipo == "troca_reserva":
            origem = self.arena.centro_area((acao.get("origem") or {}).get("area_id"))
            destino = self.arena.centro_slot_reserva_mundo((acao.get("destino") or {}).get("pokemon_id"))
        elif tipo == "captura":
            origem = self.controlador.posicao_captura_lado_mundo(acao.get("lado_id")) if hasattr(self.controlador, "posicao_captura_lado_mundo") else None
            if origem is None:
                origem = self.arena.centro_area(self.area_prevista_pokemon(self.controlador.pokemons_por_id.get(acao["pokemon_id"])))
            alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
            destino = self._centro_visual_pokemon(self.controlador.pokemons_por_id.get(str(alvo.get("pokemon_id") or "")))
        if origem and destino:
            self.indicadores_preparados.append(IndicadorAtaque().configurar(origem, destino, tipo, estado="preparado", id_acao=acao.get("id"), coordenadas_mundo=True))

    def _destinos_indicador_selecao(self, selecao):
        if not isinstance(selecao, dict):
            return []
        if str(selecao.get("tipo") or "").strip().lower() == "pokemon" and selecao.get("pokemon_id"):
            destino = self._centro_visual_pokemon(self.controlador.pokemons_por_id.get(str(selecao.get("pokemon_id") or "")))
            return [destino] if destino is not None else []
        config = selecao.get("config") if isinstance(selecao.get("config"), dict) else {}
        area_id = selecao.get("area_id")
        area_ancora = self._area_ancora_por_config(area_id, config)
        destino = self.arena.centro_area(area_ancora)
        return [destino] if destino is not None else []

    def area_prevista_pokemon(self, pokemon):
        if pokemon is None:
            return None
        pid = str(getattr(pokemon, "id_batalha", "") or "")
        area = getattr(pokemon, "AreaId", None)
        for acao in self.acoes_preparadas:
            if str(acao.get("pokemon_id") or "") != pid:
                continue
            tipo = str(acao.get("tipo") or "")
            if tipo == "movimento":
                destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
                area = destino.get("area_id", area)
            elif tipo == "troca_posicao":
                destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
                area = destino.get("area_id", area)
        return area

    def areas_afetadas_por_alvo(self, area_id, props=None):
        props = props if isinstance(props, dict) else {}
        if "tipo" in props and "alvificacao" not in props:
            return self.areas_afetadas_por_config(area_id, props)
        config = self._normalizar_alvos_config(props)[0]
        return self.areas_afetadas_por_config(area_id, config)

    def areas_afetadas_por_config(self, area_id, config=None):
        alvo_cfg = self._normalizar_config_alvo(config or {})
        tipo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        if tipo == "fixa":
            area_id = alvo_cfg.get("area_id") or area_id
        area_id = str(area_id or "").upper()
        if not area_id:
            return []
        if tipo in self.TIPOS_GLOBAIS:
            prefixo = area_id[:1].upper()
            return [f"{prefixo}{idx}" for idx in range(1, 10)]
        try:
            idx = int(area_id[1:]) - 1
        except (ValueError, IndexError):
            return [area_id]
        if idx < 0 or idx > 8:
            return [area_id]
        prefixo = area_id[:1]
        row, col = idx // 3, idx % 3
        if tipo in self.TIPOS_LINHA:
            return [f"{prefixo}{row * 3 + c + 1}" for c in range(3)]
        if tipo in self.TIPOS_COLUNA:
            return [f"{prefixo}{r * 3 + col + 1}" for r in range(3)]
        return [area_id]

    def _chave_acao(self, acao):
        tipo = str((acao or {}).get("tipo") or "")
        if tipo == "ataque":
            ataque = (acao or {}).get("ataque") if isinstance((acao or {}).get("ataque"), dict) else {}
            return ("ataque", str(ataque.get("Code") or ataque.get("ID") or ataque.get("nome") or ""))
        if tipo == "movimento":
            return ("movimento",)
        if tipo in {"troca_posicao", "troca_reserva"}:
            return ("troca",)
        if tipo == "captura":
            alvo = (acao or {}).get("alvo") if isinstance((acao or {}).get("alvo"), dict) else {}
            return ("captura", str(alvo.get("pokemon_id") or ""), str((acao or {}).get("item_base_id") or (acao or {}).get("item_nome") or ""))
        return (tipo,)

    def _resolver_alvo_visual(self, acao):
        tipo = str((acao or {}).get("tipo") or "")
        if tipo == "ataque":
            alvo = (acao or {}).get("alvo") if isinstance((acao or {}).get("alvo"), dict) else {}
            if str(alvo.get("tipo") or "").lower() == "multi":
                alvos = list(alvo.get("alvos") or [])
                primeiro = alvos[0] if alvos and isinstance(alvos[0], dict) else {}
                if str(primeiro.get("tipo") or "").lower() == "pokemon" and primeiro.get("pokemon_id"):
                    return {"pokemon": self.controlador.pokemons_por_id.get(str(primeiro.get("pokemon_id") or ""))}
                area_id = primeiro.get("area_id")
                if not area_id:
                    return {"pokemon": (acao or {}).get("executor")}
                poke = self.arena.pokemon_na_area(area_id)
                return {"area_id": area_id, "pokemon": poke}
            if str(alvo.get("tipo") or "").lower() == "pokemon" and alvo.get("pokemon_id"):
                return {"pokemon": self.controlador.pokemons_por_id.get(str(alvo.get("pokemon_id") or ""))}
            area_id = alvo.get("area_id")
            if not area_id:
                return {"pokemon": (acao or {}).get("executor")}
            poke = self.arena.pokemon_na_area(area_id)
            return {"area_id": area_id, "pokemon": poke}
        if tipo in {"movimento", "troca_posicao"}:
            destino = (acao or {}).get("destino") if isinstance((acao or {}).get("destino"), dict) else {}
            area_id = destino.get("area_id")
            poke = self.arena.pokemon_na_area(area_id)
            return {"area_id": area_id, "pokemon": poke}
        if tipo == "troca_reserva":
            destino = (acao or {}).get("destino") if isinstance((acao or {}).get("destino"), dict) else {}
            return {"pokemon": self.controlador.pokemons_por_id.get(str(destino.get("pokemon_id") or ""))}
        if tipo == "captura":
            alvo = (acao or {}).get("alvo") if isinstance((acao or {}).get("alvo"), dict) else {}
            return {"pokemon": self.controlador.pokemons_por_id.get(str(alvo.get("pokemon_id") or ""))}
        return {"pokemon": (acao or {}).get("executor")}

    def area_movimento_sob_mouse(self, pos_mouse):
        if self.pokemon_origem is None:
            return None
        area_id = self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if not area_id:
            return None
        area = self.arena.obter_area_por_id(area_id)
        if not area:
            return None
        if str(area_id) == str(getattr(self.pokemon_origem, "AreaId", "")):
            return None
        if int(area.get("lado_id", -1)) != int(getattr(self.pokemon_origem, "lado_id", -2)):
            return None
        return area_id

    def alvo_movimento_em_posicao(self, pos_mouse):
        area_id = self.area_movimento_sob_mouse(pos_mouse)
        if area_id:
            centro = self.arena.centro_area(area_id)
            if centro is not None:
                return {"tipo": "area", "area_id": area_id, "centro": centro}
        slot = self.arena.reserva_em_posicao_mouse(pos_mouse, self.controlador.camera)
        if slot is not None and self.slot_reserva_permitido(slot):
            centro = self.arena.centro_slot_reserva_mundo(slot.get("pokemon_id"))
            if centro is not None:
                return {"tipo": "reserva", "pokemon_id": slot.get("pokemon_id"), "centro": centro}
        return None

    def _mouse_sobre_alvo_movimento(self, pos_mouse):
        return self.arena.area_em_posicao_mouse(pos_mouse, self.controlador.camera) is not None or self.arena.reserva_em_posicao_mouse(pos_mouse, self.controlador.camera) is not None

    def slot_reserva_permitido(self, slot):
        if self.pokemon_origem is None or not isinstance(slot, dict):
            return False
        if str(slot.get("lado_visual") or "") != str(getattr(self.pokemon_origem, "Lado", "")):
            return False
        destino = self.controlador.pokemons_por_id.get(str(slot.get("pokemon_id") or ""))
        return destino is not None and int(getattr(destino, "lado_id", -1)) == int(getattr(self.pokemon_origem, "lado_id", -2))

    def area_permitida_para_ataque(self, area_id, alvo_cfg=None):
        if self.pokemon_origem is None or self.ataque_selecionado is None:
            return False
        alvo_cfg = self._normalizar_config_alvo(alvo_cfg or self._config_grupo_alvo_atual() or {})
        area_id = self._area_ancora_por_config(area_id, alvo_cfg)
        area = self.arena.obter_area_por_id(area_id)
        if area is None:
            return False
        tipo_alvo = str(alvo_cfg.get("tipo") or "area").strip().lower()
        if tipo_alvo == "pokemon":
            return self.pokemon_permitido_para_ataque(self.arena.pokemon_na_area(area_id))
        if bool(alvo_cfg.get("exige_area_ocupada")) and not self.arena.area_esta_ocupada(area_id):
            return False
        if self._selecao_alvo_existe(self._chave_selecao_area(area_id, alvo_cfg)):
            return False
        if tipo_alvo not in {"arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"} and not self._area_respeita_provocando(area_id, alvo_cfg):
            return False
        permitidos = alvo_cfg.get("lados_permitidos")
        if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
            return True
        lado_area = int(area.get("lado_id", -999))
        lado_origem = int(getattr(self.pokemon_origem, "lado_id", -998))
        area_origem = str(getattr(self.pokemon_origem, "AreaId", ""))
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

    def pokemon_permitido_para_ataque(self, pokemon):
        if self.pokemon_origem is None or self.ataque_selecionado is None or pokemon is None:
            return False
        if not self.controlador.pokemon_visivel(pokemon):
            return False
        alvo_cfg = self._config_grupo_alvo_atual() or {}
        if str(alvo_cfg.get("tipo") or "").strip().lower() != "pokemon":
            return False
        if pokemon.esta_na_reserva() and not bool(alvo_cfg.get("inclui_reserva", False)):
            return False
        if self._selecao_alvo_existe(("pokemon", str(getattr(pokemon, "id_batalha", "") or ""))):
            return False
        if not pokemon.esta_vivo():
            return False
        lado_alvo = int(getattr(pokemon, "lado_id", -999))
        lado_origem = int(getattr(self.pokemon_origem, "lado_id", -998))
        tipo_alvo = str(alvo_cfg.get("tipo") or "pokemon").strip().lower()
        if lado_alvo != lado_origem and tipo_alvo not in {"arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"}:
            provocadores = [
                p for p in self.controlador.pokemons
                if p.esta_vivo() and p.esta_ativo() and int(getattr(p, "lado_id", -1)) == lado_alvo and p.possui_efeito("Provocando")
            ]
            if provocadores:
                selecao = {
                    "tipo": "pokemon",
                    "pokemon_id": str(getattr(pokemon, "id_batalha", "") or ""),
                    "grupo": int(self.indice_grupo_alvo),
                    "ordem": self._quantidade_selecionada_no_grupo(self.indice_grupo_alvo),
                    "config": copy.deepcopy(alvo_cfg),
                }
                selecoes_tentativas = [*self.alvos_selecionados, selecao]
                qtd_tentativa = sum(1 for alvo in selecoes_tentativas if int(alvo.get("grupo", -1)) == int(self.indice_grupo_alvo))
                if qtd_tentativa >= int(alvo_cfg.get("quantidade") or 1) and not self._selecoes_respeitam_provocando(selecoes_tentativas):
                    return False
        permitidos = alvo_cfg.get("lados_permitidos")
        if not isinstance(permitidos, (list, tuple, set)) or not permitidos:
            return True
        for item in permitidos:
            token = str(item or "").strip().lower()
            if token in {"qualquer", "qualquer_lado", "todos", "ambos"}:
                return True
            if token in {"lado_oposto", "oposto", "inimigo", "inimigos", "adversario", "adversarios"} and lado_alvo != lado_origem:
                return True
            if token in {"mesmo_lado", "aliado", "aliados", "proprio_lado"} and lado_alvo == lado_origem:
                return True
            if token in {"usuario", "proprio", "si_mesmo"} and str(getattr(pokemon, "id_batalha", "")) == str(getattr(self.pokemon_origem, "id_batalha", "")):
                return True
        return False

    def _acao_bloqueada_por_efeito(self, pokemon, tipo):
        if pokemon is None or bool(self.controlador.modo_teste):
            return False
        tipo = str(tipo or "")
        dormindo = pokemon.possui_efeito("Dormindo")
        congelado = pokemon.possui_efeito("Congelado")
        if dormindo or congelado:
            return tipo in {"ataque", "movimento", "troca_posicao", "troca_reserva"}
        if tipo == "ataque" and pokemon.possui_efeito("Paralisado"):
            return True
        if tipo in {"movimento", "troca_posicao", "troca_reserva"} and pokemon.possui_efeito("Enraizado"):
            return True
        return False

    def _area_respeita_provocando(self, area_id, alvo_cfg=None):
        alvo_cfg = self._normalizar_config_alvo(alvo_cfg or {})
        selecao = {
            "tipo": "area",
            "area_id": self._area_ancora_por_config(area_id, alvo_cfg),
            "grupo": int(self.indice_grupo_alvo),
            "ordem": self._quantidade_selecionada_no_grupo(self.indice_grupo_alvo),
            "config": copy.deepcopy(alvo_cfg),
        }
        return self._selecoes_respeitam_provocando([selecao])

    def _selecoes_respeitam_provocando(self, selecoes):
        if self.pokemon_origem is None:
            return True
        lado_origem = int(getattr(self.pokemon_origem, "lado_id", -998))
        por_lado = {}
        for selecao in list(selecoes or []):
            if not isinstance(selecao, dict):
                continue
            config = self._normalizar_config_alvo(selecao.get("config") if isinstance(selecao.get("config"), dict) else {})
            tipo = str(config.get("tipo") or selecao.get("tipo") or "area").strip().lower()
            if tipo in self.TIPOS_GLOBAIS:
                continue
            if tipo == "pokemon":
                alvo = self.controlador.pokemons_por_id.get(str(selecao.get("pokemon_id") or ""))
                if alvo is None:
                    continue
                lado_alvo = int(getattr(alvo, "lado_id", -999))
                if lado_alvo == lado_origem:
                    continue
                dados = por_lado.setdefault(lado_alvo, {"pokemon_ids": set(), "areas": set()})
                dados["pokemon_ids"].add(str(getattr(alvo, "id_batalha", "") or ""))
                area_alvo = str(getattr(alvo, "AreaId", "") or "").upper()
                if area_alvo:
                    dados["areas"].add(area_alvo)
                continue
            area_id = self._area_ancora_por_config(selecao.get("area_id"), config)
            area = self.arena.obter_area_por_id(area_id)
            if area is None:
                continue
            lado_alvo = int(area.get("lado_id", -999))
            if lado_alvo == lado_origem:
                continue
            dados = por_lado.setdefault(lado_alvo, {"pokemon_ids": set(), "areas": set()})
            for area_afetada in self.areas_afetadas_por_config(area_id, config):
                area_afetada = str(area_afetada or "").upper()
                if not area_afetada:
                    continue
                dados["areas"].add(area_afetada)
                ocupante = self.arena.pokemon_na_area(area_afetada)
                if ocupante is not None:
                    dados["pokemon_ids"].add(str(getattr(ocupante, "id_batalha", "") or ""))
        for lado_alvo, dados in por_lado.items():
            provocadores = [
                p for p in self.controlador.pokemons
                if p.esta_vivo() and p.esta_ativo() and int(getattr(p, "lado_id", -1)) == int(lado_alvo) and p.possui_efeito("Provocando")
            ]
            if not provocadores:
                continue
            if any(str(getattr(p, "id_batalha", "") or "") in dados["pokemon_ids"] or str(getattr(p, "AreaId", "") or "").upper() in dados["areas"] for p in provocadores):
                continue
            return False
        return True

    def _centro_visual_pokemon(self, pokemon):
        if pokemon is None:
            return None
        if pokemon.esta_na_reserva():
            return self.arena.centro_slot_reserva_mundo(getattr(pokemon, "id_batalha", None))
        return self.arena.centro_area(getattr(pokemon, "AreaId", None))

    def areas_destacadas(self):
        if self.estado_montagem == "preparando_ataque" and self.ataque_selecionado is not None:
            config = self._config_grupo_alvo_atual() or {}
            if str(config.get("tipo") or "").strip().lower() == "fixa":
                area_id = config.get("area_id")
                return self.areas_afetadas_por_config(area_id, config) if self.area_permitida_para_ataque(area_id, config) else []
            return [str(a.get("id")) for a in getattr(self.arena, "_areas", []) if self.area_permitida_para_ataque(a.get("id"))]
        if self.estado_montagem == "arrastando" and self.pokemon_origem is not None:
            lado = int(getattr(self.pokemon_origem, "lado_id", -1))
            area_origem = str(getattr(self.pokemon_origem, "AreaId", ""))
            return [
                str(a.get("id"))
                for a in getattr(self.arena, "_areas", [])
                if int(a.get("lado_id", -2)) == lado and str(a.get("id")) != area_origem
            ]
        return []

    def reservas_destacadas(self):
        if self.estado_montagem == "preparando_ataque" and self.ataque_selecionado is not None:
            config = self._config_grupo_alvo_atual() or {}
            if str(config.get("tipo") or "").strip().lower() != "pokemon" or not bool(config.get("inclui_reserva")):
                return []
            saida = []
            for lado in ("jogador", "inimigo"):
                for slot in self.arena.obter_slots_reserva(lado):
                    poke = self.controlador.pokemons_por_id.get(str(slot.get("pokemon_id") or ""))
                    if self.pokemon_permitido_para_ataque(poke):
                        saida.append(str(slot.get("id_slot")))
            return saida
        if self.estado_montagem != "arrastando" or self.pokemon_origem is None:
            return []
        lado_visual = str(getattr(self.pokemon_origem, "Lado", ""))
        return [str(s.get("id_slot")) for s in self.arena.obter_slots_reserva(lado_visual)]

    def desenhar_pulso_previa(self, surface):
        if self.estado_montagem not in {"preparando_ataque", "arrastando"} or self.alvo_previa_mundo is None:
            return
        tile = max(1, int(getattr(self.controlador.camera, "TilePx", 40) or 40))
        props = self.buscar_propriedades_ataque(self.ataque_selecionado) if self.estado_montagem == "preparando_ataque" else None
        config = self._config_grupo_alvo_atual() if self.estado_montagem == "preparando_ataque" else None
        areas = [] if isinstance(self.area_alvo_previa, dict) else (self.areas_afetadas_por_config(self.area_alvo_previa, config) if props else [])
        centros = [self.arena.centro_area(aid) for aid in areas] if areas else [self.alvo_previa_mundo]
        for centro in [c for c in centros if c is not None]:
            pos = self.controlador.camera.mundo_para_tela_px(centro)
            IndicadorAtaque.desenhar_pulso(surface, pos, raio_base=max(18, int(tile * 0.95)))

    def desenhar_fantasmas_movimento(self, surface):
        for acao in self.acoes_preparadas:
            if str(acao.get("tipo") or "") != "movimento":
                continue
            destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
            area_id = destino.get("area_id")
            if not area_id or self.arena.pokemon_na_area(area_id) is not None:
                continue
            pokemon = self.controlador.pokemons_por_id.get(str(acao.get("pokemon_id") or ""))
            if pokemon is not None and hasattr(pokemon, "desenhar_fantasma"):
                pokemon.desenhar_fantasma(surface, self.controlador.camera, self.arena, area_id)

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
        self.area_alvo_previa = None
        self.alvo_previa_mundo = None
        self._limpar_selecao_alvos()
        self.acao_selecionada_id = None
        self.recalcular_previsao_energia()

    def cancelar_previa(self):
        self.indicador_previa = None
        self.pokemon_origem = None
        self.ataque_selecionado = None
        self.area_alvo_previa = None
        self.alvo_previa_mundo = None
        self._limpar_selecao_alvos()
        self.estado_montagem = "ocioso"
        self.recalcular_previsao_energia()

    def calcular_custo_acao(self, pokemon, acao_base, ordem_pokemon=1):
        tipo = str((acao_base or {}).get("tipo") or "")
        if tipo == "movimento":
            base = float(self.custo_movimento)
        elif tipo == "troca_posicao":
            base = float(self.custo_troca_posicao)
        elif tipo == "troca_reserva":
            base = float(self.custo_troca_reserva)
        elif tipo == "captura":
            return 0.0
        else:
            at = (acao_base or {}).get("ataque") if isinstance((acao_base or {}).get("ataque"), dict) else {}
            props = self.buscar_propriedades_ataque(at)
            base = float((props or {}).get("custo", at.get("Custo") or at.get("custo") or 0.0))
        if tipo == "ataque" and pokemon is not None and pokemon.possui_efeito("Encharcado"):
            base *= 1.20
        if tipo == "movimento" and str(getattr(self.controlador, "clima_atual", "") or "").lower() in {"gravidade_anomala", "gravidade anomala", "gravidade anômala"}:
            base *= 2.0
        mult = self.multiplicador_segunda_acao if int(ordem_pokemon) >= 2 else 1.0
        return round(base * mult, 2)

    def recalcular_previsao_energia(self):
        custos = {}
        por_pokemon = {}
        for a in self.acoes_preparadas:
            pid = str(a.get("pokemon_id") or "")
            if str(a.get("tipo") or "") != "captura":
                por_pokemon[pid] = por_pokemon.get(pid, 0) + 1
            a["custo_previsto"] = self.calcular_custo_acao(self.controlador.pokemons_por_id.get(pid), a, ordem_pokemon=por_pokemon.get(pid, 1))
            custos[pid] = custos.get(pid, 0.0) + float(a.get("custo_previsto") or 0.0)
        custos_preparados = dict(custos)
        if self.estado_montagem == "preparando_ataque" and self.pokemon_origem is not None and self.ataque_selecionado is not None:
            pid = str(getattr(self.pokemon_origem, "id_batalha", "") or "")
            ordem = por_pokemon.get(pid, 0) + 1
            custo_previa = self.calcular_custo_acao(self.pokemon_origem, self._criar_acao_ataque(self.pokemon_origem, self.ataque_selecionado, None), ordem_pokemon=ordem)
            custos[pid] = custos.get(pid, 0.0) + float(custo_previa)
        self.previa_energia_por_pokemon = custos_preparados
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
        pacote = {
            "id_partida": self.controlador.id_partida,
            "rodada": self.controlador.rodada_atual,
            "modo_teste": False,
            "lado_id": self.controlador.lado_jogador,
            "acoes": [self._serializar_acao(a) for a in self.acoes_preparadas if int(a.get("lado_id", -1)) == int(self.controlador.lado_jogador)],
        }
        if str(getattr(self.controlador, "tipo_batalha", "") or "").strip().lower() == "confronto" and hasattr(self.controlador, "inventario_local_serializado"):
            pacote["inventario_jogador"] = self.controlador.inventario_local_serializado()
            if hasattr(self.controlador, "nome_jogador_batalha"):
                pacote["jogador_nome"] = self.controlador.nome_jogador_batalha()
        return pacote

    def gerar_pacote_jogadas_modo_teste(self):
        por_lado = {}
        for a in self.acoes_preparadas:
            lado = int(a.get("lado_id", -1))
            por_lado.setdefault(lado, []).append(self._serializar_acao(a))
        for pokemon in self.controlador.pokemons:
            if pokemon.esta_vivo():
                por_lado.setdefault(int(getattr(pokemon, "lado_id", -1)), [])
        return {
            "id_partida": self.controlador.id_partida,
            "rodada": self.controlador.rodada_atual,
            "modo_teste": True,
            "jogadas": [{"lado_id": lado, "acoes": acoes} for lado, acoes in sorted(por_lado.items())],
        }

    def _serializar_acao(self, acao):
        out = {k: v for k, v in acao.items() if k not in {"executor", "alvo_visual"}}
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
                "nome": nome,
                "custo": int(float(row.get("Custo") or 0)),
                "estilo_logico": estilo,
                "animacao": {"modelo": "Avanço", "efeito_executor": None, "efeito_alvo": None},
                "execute_principal": f"ataque_{nome.lower().replace(' ', '_')}",
                "parametros": {"tipo": str(row.get("Tipo") or "normal").lower()},
            }
            if estilo == "alvo":
                base["alvificacao"] = {
                    "alvos": [
                        {
                            "tipo": "area",
                            "quantidade": 1,
                            "lados_permitidos": ["lado_oposto"],
                            "exige_area_ocupada": False,
                        }
                    ],
                }
            ataques[str(int(float(code)))] = base
    out = {"schema_version": 1, "ataques": ataques}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
