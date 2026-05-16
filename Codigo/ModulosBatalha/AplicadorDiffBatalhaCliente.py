from __future__ import annotations


class AplicadorDiffBatalhaCliente:
    def __init__(self, controlador):
        self.controlador = controlador

    def aplicar(self, evento):
        dados = self._dados(evento)
        tipo = str((evento or {}).get("tipo") or "")
        ctrl = self.controlador
        perfil = ctrl.perfil_local() if hasattr(ctrl, "perfil_local") else getattr(getattr(ctrl, "ator", None), "Perfil", None)
        if perfil is not None and hasattr(perfil, "registrar_conhecimento"):
            if tipo in {"acao_iniciada", "ataque_usado", "ataque_acertou", "ataque_errou", "ataque_sem_alvo_real"}:
                perfil.registrar_conhecimento("Ataques", dados.get("ataque_id") or dados.get("ataque_nome") or dados.get("ataque"))
        if perfil is not None and hasattr(perfil, "registrar_conhecimento_efeito"):
            if tipo in {"pokemon_recebeu_efeito", "efeito_tickou", "efeito_expirou"}:
                perfil.registrar_conhecimento_efeito(dados.get("efeito_code") or dados.get("efeito_nome"))
            elif tipo in {"efeito_bloqueado_por_limite", "efeito_bloqueado_por_imunidade", "efeito_bloqueado_por_bloqueado"}:
                perfil.registrar_conhecimento_efeito(dados.get("efeito_code") or dados.get("efeito_nome") or dados.get("efeito"))
                perfil.registrar_conhecimento_efeito(dados.get("bloqueador_code") or dados.get("bloqueador_nome"))
            elif tipo in {"clima_aplicado", "clima_alterado", "clima_iniciado", "clima_mudou"}:
                perfil.registrar_conhecimento_efeito(dados.get("clima_code") or dados.get("clima") or dados.get("clima_nome") or dados.get("nome"))
            elif tipo in {"efeito_area_aplicado", "efeito_area_tickou", "efeito_area_expirou", "terreno_alterado", "terreno_expirou", "terreno_removido", "terreno_aplicou_efeito", "terreno_tickou"}:
                perfil.registrar_conhecimento_efeito(dados.get("efeito_code") or dados.get("efeito_nome"))
        if perfil is not None and hasattr(ctrl, "sincronizar_perfil_local"):
            ctrl.sincronizar_perfil_local()
        if tipo == "pokemon_gastou_energia":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("energia_depois") is not None:
                poke.Energia = float(dados.get("energia_depois") or poke.Energia)
        elif tipo == "pokemon_ganhou_energia":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("energia_depois") is not None:
                poke.Energia = float(dados.get("energia_depois") or poke.Energia)
        elif tipo == "pokemon_sofreu_dano":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            if poke is not None:
                if dados.get("vida_depois") is not None:
                    poke.VidaAtual = max(0.0, float(dados.get("vida_depois") or 0.0))
                if dados.get("barreira_depois") is not None:
                    poke.BarreiraAtual = max(0.0, float(dados.get("barreira_depois") or 0.0))
        elif tipo == "barreira_absorveu":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or ""))
            if poke is not None and dados.get("barreira_depois") is not None:
                poke.BarreiraAtual = max(0.0, float(dados.get("barreira_depois") or 0.0))
        elif tipo == "pokemon_recebeu_cura":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("vida_depois") is not None:
                poke.VidaAtual = max(0.0, float(dados.get("vida_depois") or poke.VidaAtual))
        elif tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or dados.get("alvo_id") or ""))
            atributo = str(dados.get("atributo") or dados.get("stat") or dados.get("chave") or "")
            if poke is not None and atributo:
                if dados.get("valor_depois") is not None and hasattr(poke, "Atributos"):
                    poke.Atributos[atributo] = float(dados.get("valor_depois") or 0.0)
                    if atributo == "Vida" and hasattr(poke, "VidaMax"):
                        poke.VidaMax = max(1.0, float(dados.get("valor_depois") or poke.VidaMax))
                    elif atributo == "EneM" and hasattr(poke, "EnergiaMax"):
                        poke.EnergiaMax = max(1.0, float(dados.get("valor_depois") or poke.EnergiaMax))
                if dados.get("variacao_total") is not None and hasattr(poke, "Variacoes"):
                    poke.Variacoes[atributo] = float(dados.get("variacao_total") or 0.0)
                if hasattr(poke, "_sincronizar_alias_atributos"):
                    poke._sincronizar_alias_atributos()
        elif tipo == "pokemon_ganhou_barreira":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("barreira_depois") is not None:
                poke.BarreiraAtual = max(0.0, float(dados.get("barreira_depois") or 0.0))
        elif tipo == "pokemon_recebeu_efeito":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            efeito = dados.get("efeito") if isinstance(dados.get("efeito"), dict) else {}
            if poke is not None:
                poke.aplicar_efeito_visual(efeito or {"nome": dados.get("efeito_nome"), "code": dados.get("efeito_code"), "passos_restantes": dados.get("passos_restantes"), "tipo": dados.get("tipo")})
        elif tipo == "efeito_tickou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None:
                poke.atualizar_timer_efeito(dados.get("efeito_code"), dados.get("efeito_nome"), dados.get("passos_depois"))
        elif tipo == "efeito_expirou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None:
                poke.expirar_efeito_visual(dados.get("efeito_code"), dados.get("efeito_nome"))
        elif tipo == "pokemon_entrou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and dados.get("area_id"):
                poke.Ativo = True
                poke.EmReserva = False
                poke.AreaId = dados.get("area_id")
        elif tipo == "captura_batalha_resultado":
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or ""))
            if poke is not None and bool(dados.get("capturado")):
                poke.Ativo = False
                poke.EmReserva = False
                poke.Vivo = False
                poke.AreaId = None
            if isinstance(dados.get("inventario_jogador"), dict):
                ctrl.aplicar_inventario_batalha(dados.get("inventario_jogador"))
        elif tipo == "inventario_atualizado_batalha":
            if int(dados.get("lado_id", getattr(ctrl, "lado_jogador", 50)) or 0) == int(getattr(ctrl, "lado_jogador", 50)) and isinstance(dados.get("inventario"), dict):
                ctrl.aplicar_inventario_batalha(dados.get("inventario"))
        elif tipo in {"clima_aplicado", "clima_alterado", "clima_iniciado", "clima_mudou"}:
            ctrl.clima_atual = dados.get("clima_depois") or dados.get("clima") or dados.get("clima_nome") or dados.get("nome") or dados
        elif tipo == "clima_expirou":
            ctrl.clima_atual = None
        elif tipo == "terreno_alterado":
            if not hasattr(ctrl, "terrenos_area") or not isinstance(getattr(ctrl, "terrenos_area", None), dict):
                ctrl.terrenos_area = {}
            if dados.get("area_id"):
                ctrl.terrenos_area[str(dados.get("area_id"))] = dados.get("terreno")
        elif tipo in {"terreno_expirou", "terreno_removido"}:
            if hasattr(ctrl, "terrenos_area") and isinstance(getattr(ctrl, "terrenos_area", None), dict):
                ctrl.terrenos_area.pop(str(dados.get("area_id") or ""), None)
        ctrl.arena.atualizar_ocupacao(ctrl.pokemons)

    @staticmethod
    def _dados(evento):
        dados = dict((evento or {}).get("dados") or {})
        for chave, valor in dict(evento or {}).items():
            if chave != "dados" and chave not in dados:
                dados[chave] = valor
        return dados
