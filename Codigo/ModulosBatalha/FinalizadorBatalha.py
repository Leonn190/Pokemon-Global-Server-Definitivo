from __future__ import annotations

from copy import deepcopy

import pygame

from Codigo.ModulosGerais.Sonoridades import tocar_musica_resultado_batalha
from Codigo.Telas.Subtelas.SubtelaFinalizacao import SubtelaFinalizacao
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import ganhar_xp_pokemon


def _i(valor, default=0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _f(valor, default=0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(default)


class FinalizadorBatalha:
    def __init__(self, controlador):
        self.controlador = controlador
        self._finalizacao_aberta = False

    def finalizar_por_resultado(self, resultado):
        if self._finalizacao_aberta:
            return
        resultado = dict(resultado or {})
        self._ultimo_resultado = dict(resultado)
        self._registrar_resultado_perfil(resultado)
        self.aplicar_persistencia(resultado)
        self._notificar_servidor_finalizacao(resultado)
        self.abrir_subtela_resultados(resultado)

    def finalizar_por_fuga(self):
        ctrl = self.controlador
        perfil = ctrl.perfil_local() if hasattr(ctrl, "perfil_local") else getattr(getattr(ctrl, "ator", None), "Perfil", None)
        if perfil is None:
            jogo = getattr(ctrl, "jogo", None)
            perfil = getattr(getattr(jogo, "Ator", None), "Perfil", None)
        if perfil is not None and hasattr(perfil, "registrar_fuga"):
            perfil.registrar_fuga()
            if hasattr(ctrl, "sincronizar_perfil_local"):
                ctrl.sincronizar_perfil_local()
        self._registrar_resultado_perfil({}, fuga=True)
        resposta = ctrl.server_batalha.finalizar_batalha(ctrl.id_partida, ctrl.lado_jogador, motivo="fuga")
        resultado = resposta.get("resultado") if isinstance(resposta, dict) and isinstance(resposta.get("resultado"), dict) else {}
        self._ultimo_resultado = dict(resultado)
        self.aplicar_persistencia(resultado)
        self.voltar_ao_mundo()

    def _registrar_resultado_perfil(self, resultado, fuga=False):
        ctrl = self.controlador
        perfil = ctrl.perfil_local() if hasattr(ctrl, "perfil_local") else getattr(getattr(ctrl, "ator", None), "Perfil", None)
        if perfil is None or not hasattr(perfil, "registrar_batalha"):
            return
        if bool(getattr(self, "_perfil_resultado_registrado", False)):
            return
        vencedor = False if fuga else self._vencedor_visual(resultado) == "jogador"
        tipo = str(getattr(ctrl, "tipo_batalha", "") or "").strip().lower()
        contra_bot = tipo in {"confronto", "treinador", "trainer", "simulador"}
        perfil.registrar_batalha(vencedor=vencedor, contra_bot=contra_bot)
        if hasattr(ctrl, "sincronizar_perfil_local"):
            ctrl.sincronizar_perfil_local()
        self._perfil_resultado_registrado = True

    def montar_itens_resultado(self, resultado):
        resultado = dict(resultado or {})
        estatisticas = resultado.get("estatisticas") if isinstance(resultado.get("estatisticas"), dict) else {}
        xp = resultado.get("xp") if isinstance(resultado.get("xp"), dict) else {}
        pokemons_resultado = resultado.get("pokemons") if isinstance(resultado.get("pokemons"), dict) else {}
        itens = []
        lado_jogador = int(getattr(self.controlador, "lado_jogador", 50) or 50)
        for pokemon in list(getattr(self.controlador, "pokemons", []) or []):
            if int(getattr(pokemon, "lado_id", -1) or -1) != lado_jogador:
                continue
            pid = str(getattr(pokemon, "id_batalha", "") or "")
            stats = estatisticas.get(pid) if isinstance(estatisticas.get(pid), dict) else {}
            xp_item = xp.get(pid) if isinstance(xp.get(pid), dict) else {}
            diff = pokemons_resultado.get(pid) if isinstance(pokemons_resultado.get(pid), dict) else {}
            itens.append(
                {
                    "nome": getattr(pokemon, "Nome", None) or diff.get("nome") or "Pokemon",
                    "visual": pokemon,
                    "xp_batalha": _i(xp_item.get("xp_final"), 0),
                    "dano": _f(stats.get("dano_causado"), 0.0),
                    "abates": _i(stats.get("abates"), 0),
                    "energia_gasta": _f(stats.get("energia_gasta"), 0.0),
                    "morto": not bool(diff.get("Vivo", diff.get("vivo", getattr(pokemon, "Vivo", True)))),
                }
            )
        return itens

    def aplicar_persistencia(self, resultado):
        jogo = getattr(self.controlador, "jogo", None)
        if jogo is None or not isinstance(getattr(jogo, "INFO", None), dict):
            return
        persistencia = resultado.get("persistencia") if isinstance(resultado, dict) and isinstance(resultado.get("persistencia"), dict) else {}
        pokemons = persistencia.get("pokemons") if isinstance(persistencia.get("pokemons"), dict) else {}
        inventario_resultado = resultado.get("inventario_jogador") if isinstance(resultado.get("inventario_jogador"), dict) else {}
        if not pokemons and not inventario_resultado:
            return
        contexto = jogo.INFO.get("CombateContexto") if isinstance(jogo.INFO.get("CombateContexto"), dict) else {}
        avisos = []
        for dados in pokemons.values():
            if not isinstance(dados, dict):
                continue
            id_original = dados.get("id_original")
            if id_original is None:
                continue
            alvos = self._localizar_pokemons_contexto(contexto, id_original)
            if not alvos:
                avisos.append({"id_original": id_original, "motivo": "pokemon_original_nao_encontrado"})
                continue
            for alvo in alvos:
                vida = self._vida_pos_batalha(alvo, dados.get("VidaAtual"))
                self._aplicar_vida(alvo, vida)
                self._aplicar_xp(alvo, dados.get("xp_ganho"))
        if avisos:
            contexto.setdefault("avisos_persistencia_batalha", []).extend(avisos)
        inventario = self._inventario_atualizado_pos_batalha(jogo, contexto) or deepcopy(inventario_resultado)
        if inventario_resultado:
            for chave in ("itens", "doces", "limite_itens", "limite_slots", "limite_pokemons", "limite_times_pokemon", "slot_selecionado"):
                if chave in inventario_resultado:
                    inventario[chave] = deepcopy(inventario_resultado.get(chave))
            capturados = resultado.get("pokemons_capturados") if isinstance(resultado.get("pokemons_capturados"), list) else []
            if capturados:
                inventario.setdefault("pokemons", [])
                existentes = {str((p or {}).get("id") or (p or {}).get("id_original") or "") for p in inventario.get("pokemons", []) if isinstance(p, dict)}
                for capturado in capturados:
                    if not isinstance(capturado, dict):
                        continue
                    chave = str(capturado.get("id") or capturado.get("id_original") or "")
                    if chave and chave in existentes:
                        continue
                    inventario["pokemons"].append(deepcopy(capturado))
                    if chave:
                        existentes.add(chave)
        if inventario:
            jogo.INFO.setdefault("PlayerDadosServer", {})["inventario"] = inventario
            jogo.INFO["SincronizacaoPosBatalhaMundo"] = {
                "inventario": inventario,
                "pokemon_mundo_id": int(contexto.get("pokemon_mundo_id", 0) or 0) if bool(resultado.get("finalizada")) and self._vencedor_visual(resultado) == "jogador" else 0,
            }

    def abrir_subtela_resultados(self, resultado):
        self._finalizacao_aberta = True
        ctrl = self.controlador
        vencedor = self._vencedor_visual(resultado)
        itens = self.montar_itens_resultado(resultado)
        rodadas = _i(resultado.get("rodadas_totais", resultado.get("rodada_atual", ctrl.rodada_atual)), ctrl.rodada_atual)
        jogo = getattr(ctrl, "jogo", None)
        gerenciador = getattr(jogo, "GerenciadorSubtelas", None) if jogo is not None else None
        if gerenciador is None:
            self.voltar_ao_mundo()
            return
        tocar_musica_resultado_batalha(vencedor)
        gerenciador.abrir(SubtelaFinalizacao(itens, rodadas_totais=rodadas, vencedor=vencedor, ao_continuar=self.voltar_ao_mundo))

    def voltar_ao_mundo(self):
        ctrl = self.controlador
        jogo = getattr(ctrl, "jogo", None)
        if jogo is not None and isinstance(getattr(jogo, "INFO", None), dict):
            if hasattr(ctrl, "sincronizar_perfil_local"):
                ctrl.sincronizar_perfil_local()
            player_dados = jogo.INFO.get("PlayerDadosServer") if isinstance(jogo.INFO.get("PlayerDadosServer"), dict) else {}
            perfil = player_dados.get("perfil") if isinstance(player_dados.get("perfil"), dict) else None
            if perfil is not None:
                jogo.INFO.setdefault("SincronizacaoPosBatalhaMundo", {})["perfil"] = deepcopy(perfil)
            self._preparar_dialogo_pos_batalha(jogo)
            jogo.INFO["ImuneCombateAteMs"] = int(pygame.time.get_ticks()) + 3000
            jogo.INFO.pop("CombateContextoTemporario", None)
            jogo.CenaAlvo = "Mundo"
        ctrl.solicitou_encerrar_batalha = True
        ctrl.estado_batalha = "finalizada"

    def _preparar_dialogo_pos_batalha(self, jogo):
        contexto = jogo.INFO.get("CombateContexto") if isinstance(jogo.INFO.get("CombateContexto"), dict) else {}
        if str(contexto.get("tipo") or "").strip().lower() not in {"treinador", "trainer"}:
            return
        npc_ctx = contexto.get("npc_contexto") if isinstance(contexto.get("npc_contexto"), dict) else {}
        npc_id = _i(npc_ctx.get("npc_id"), 0)
        if npc_id <= 0:
            return
        vencedor = self._vencedor_visual(getattr(self, "_ultimo_resultado", {}) or {})
        pos = npc_ctx.get("pos_batalha") if isinstance(npc_ctx.get("pos_batalha"), dict) else {}
        chave = "vitoria" if vencedor == "jogador" else "derrota"
        destino = str(pos.get(chave) or pos.get("padrao") or f"pos_batalha_{chave}").strip()
        jogo.INFO["DialogoPosBatalha"] = {
            "npc_id": npc_id,
            "inicio_dialogo": destino,
            "resultado_batalha": chave,
        }

    def _notificar_servidor_finalizacao(self, resultado):
        ctrl = self.controlador
        motivo = str((resultado or {}).get("motivo_finalizacao") or "fim_normal")
        try:
            ctrl.server_batalha.finalizar_batalha(ctrl.id_partida, ctrl.lado_jogador, motivo=motivo)
        except Exception:
            return

    def _vencedor_visual(self, resultado):
        vencedor = resultado.get("vencedor") if isinstance(resultado, dict) else None
        lado = int(getattr(self.controlador, "lado_jogador", 50) or 50)
        if isinstance(vencedor, list):
            return "jogador" if lado in [_i(v) for v in vencedor] else "inimigo"
        return "jogador" if _i(vencedor, -999) == lado else "inimigo"

    def _localizar_pokemons_contexto(self, contexto, id_original):
        alvo_id = str(id_original)
        encontrados = []
        vistos = set()
        for pokemon in self._iter_pokemons_prioritarios(contexto):
            if self._id_pokemon(pokemon) != alvo_id:
                continue
            marcador = id(pokemon)
            if marcador in vistos:
                continue
            vistos.add(marcador)
            encontrados.append(pokemon)
        return encontrados

    def _iter_pokemons_prioritarios(self, contexto):
        time_jogador = contexto.get("time_jogador")
        if isinstance(time_jogador, dict):
            for pokemon in list(time_jogador.get("Slots") or time_jogador.get("slots") or []):
                if isinstance(pokemon, dict):
                    yield pokemon
        for time in list(contexto.get("times_jogador") or []):
            if not isinstance(time, dict):
                continue
            for pokemon in list(time.get("Slots") or time.get("slots") or []):
                if isinstance(pokemon, dict):
                    yield pokemon
        for pokemon in list(contexto.get("pokemons_jogador") or []):
            if isinstance(pokemon, dict):
                yield pokemon

    def _id_pokemon(self, pokemon):
        for chave in ("id", "ID", "Id", "id_original"):
            if pokemon.get(chave) is not None:
                return str(pokemon.get(chave))
        for chave in ("dados", "Dados"):
            dados = pokemon.get(chave) if isinstance(pokemon.get(chave), dict) else {}
            for sub in ("id", "ID", "Id"):
                if dados.get(sub) is not None:
                    return str(dados.get(sub))
        return ""

    def _aplicar_vida(self, pokemon, vida):
        vida = max(0.0, _f(vida, 0.0))
        aplicado = False
        for chave in ("VidaAtual", "vida_atual", "HP", "hp"):
            if chave in pokemon:
                pokemon[chave] = vida
                aplicado = True
        estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else None
        if estado is not None:
            for chave in ("VidaAtual", "vida_atual", "HP", "hp"):
                if chave in estado:
                    estado[chave] = vida
                    aplicado = True
            if not aplicado:
                estado["VidaAtual"] = vida
                aplicado = True
        dados = pokemon.get("dados") if isinstance(pokemon.get("dados"), dict) else pokemon.get("Dados") if isinstance(pokemon.get("Dados"), dict) else None
        if dados is not None:
            estado_dados = dados.get("estado") if isinstance(dados.get("estado"), dict) else None
            if estado_dados is not None:
                estado_dados["VidaAtual"] = vida
                aplicado = True
        if not aplicado:
            pokemon["VidaAtual"] = vida

    def _vida_pos_batalha(self, pokemon, vida_persistida):
        if self._tem_pocao_suprema(pokemon):
            return self._vida_maxima(pokemon, vida_persistida)
        return vida_persistida

    def _tem_pocao_suprema(self, pokemon):
        for fonte in self._fontes_pokemon(pokemon):
            for chave in ("pocao_suprema", "PocaoSuprema"):
                if bool(fonte.get(chave)):
                    return True
        return False

    def _vida_maxima(self, pokemon, default=1.0):
        for fonte in self._fontes_pokemon(pokemon):
            for chave in ("VidaMax", "vida_max", "Vida", "vida"):
                if chave in fonte:
                    valor = _f(fonte.get(chave), 0.0)
                    if valor > 0:
                        return valor
            stats = fonte.get("stats") if isinstance(fonte.get("stats"), dict) else fonte.get("Stats") if isinstance(fonte.get("Stats"), dict) else None
            if stats is not None:
                valor = _f(stats.get("Vida"), 0.0)
                if valor > 0:
                    return valor
        return max(1.0, _f(default, 1.0))

    def _fontes_pokemon(self, pokemon):
        if not isinstance(pokemon, dict):
            return []
        fontes = [pokemon]
        for chave in ("estado", "dados", "Dados"):
            valor = pokemon.get(chave)
            if isinstance(valor, dict):
                fontes.append(valor)
                estado = valor.get("estado") if isinstance(valor.get("estado"), dict) else None
                if estado is not None:
                    fontes.append(estado)
        return fontes

    def _aplicar_xp(self, pokemon, xp_ganho):
        ganho = _i(xp_ganho, 0)
        if ganho <= 0:
            return
        alvo = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
        if isinstance(alvo, dict):
            ganhar_xp_pokemon(alvo, ganho)
            return
        dados = pokemon.get("dados") if isinstance(pokemon.get("dados"), dict) else pokemon.get("Dados") if isinstance(pokemon.get("Dados"), dict) else None
        if dados is not None:
            alvo = dados.get("estado") if isinstance(dados.get("estado"), dict) else dados
            if isinstance(alvo, dict):
                ganhar_xp_pokemon(alvo, ganho)

    def _inventario_atualizado_pos_batalha(self, jogo, contexto):
        player_dados = jogo.INFO.get("PlayerDadosServer") if isinstance(jogo.INFO.get("PlayerDadosServer"), dict) else {}
        inventario = deepcopy(player_dados.get("inventario") if isinstance(player_dados.get("inventario"), dict) else {})
        if not inventario:
            return {}
        pokemons_jogador = contexto.get("pokemons_jogador")
        if isinstance(pokemons_jogador, list) and pokemons_jogador:
            inventario["pokemons"] = deepcopy(pokemons_jogador)
        times = contexto.get("times_jogador") if isinstance(contexto.get("times_jogador"), list) else None
        if times is not None:
            inventario["times_pokemon"] = deepcopy(times)
        indice = _i(contexto.get("time_jogador_indice"), -1)
        if indice >= 0 and isinstance(contexto.get("time_jogador"), dict):
            inventario.setdefault("times_pokemon", [])
            while len(inventario["times_pokemon"]) <= indice:
                inventario["times_pokemon"].append({"Nome": f"Time {len(inventario['times_pokemon']) + 1}", "Slots": [None] * 6})
            inventario["times_pokemon"][indice] = deepcopy(contexto.get("time_jogador") or {})
        return inventario
