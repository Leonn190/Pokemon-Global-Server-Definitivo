from __future__ import annotations

import copy

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.ControladorExecutes import executar_alvificacao, executar_execute_principal, obter_executes_reativos
from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import inimigos_vivos_adjacentes_ao_alvo, normalizar
from SimuladorServerJogo.Mundo.AutoridadeCaptura import resolver_captura_batalha


class RodadorTurno:
    def __init__(self, partida):
        self.partida = partida
        self.avisos = []
        self.erros_acoes = []
        self.acoes_falhas = []
        self._ataques_executados = 0

    def rodar(self, acoes_ordenadas, acoes_invalidas=None):
        self.avisos = []
        self.erros_acoes = list(acoes_invalidas or [])
        self.acoes_falhas = []
        self._ataques_executados = 0
        acoes = list(acoes_ordenadas or [])
        if not acoes:
            self.partida.passo_atual += 1
            self._fim_passo()
        for acao in acoes:
            self.partida.passo_atual += 1
            self.executar_passo(acao)
        return {
            "avisos": list(self.avisos),
            "erros_acoes": list(self.erros_acoes),
            "acoes_falhas": list(self.acoes_falhas),
        }

    def executar_passo(self, acao):
        tipo = str((acao or {}).get("tipo") or "")
        if tipo == "captura":
            self._registrar_acao_iniciada(acao, None)
            self._executar_captura(None, acao)
            self._fim_passo()
            return
        pokemon = self.partida.obter_pokemon((acao or {}).get("pokemon_id"))
        self._registrar_acao_iniciada(acao, pokemon)
        motivo = self._validar_estado_atual(pokemon, acao)
        if motivo:
            self._falhar(acao, motivo)
            self._fim_passo()
            return
        custo = float((acao or {}).get("custo_real") or 0.0)
        if pokemon.EnergiaAtual < custo:
            self._falhar(acao, "energia_insuficiente_execucao")
            self._fim_passo()
            return
        gasto = pokemon.GastarEnergia(custo, dados={"acao_id": acao.get("id_acao")}) if custo > 0 else {"aplicado": False}
        if custo > 0 and isinstance(gasto, dict) and gasto.get("aplicado"):
            self.partida.registrar_evento_log(
                "pokemon_gastou_energia",
                {
                    "pokemon_id": pokemon.id_batalha,
                    "pokemon_nome": pokemon.nome,
                    "valor": gasto.get("valor", custo),
                    "energia_antes": gasto.get("energia_antes"),
                    "energia_depois": gasto.get("energia_depois"),
                    "id_acao": acao.get("id_acao"),
                },
            )
        if tipo == "movimento":
            self._executar_movimento(pokemon, acao)
        elif tipo == "troca_posicao":
            self._executar_troca_posicao(pokemon, acao)
        elif tipo == "troca_reserva":
            self._executar_troca_reserva(pokemon, acao)
        elif tipo == "ataque":
            self._executar_ataque(pokemon, acao)
        elif tipo == "captura":
            self._executar_captura(pokemon, acao)
        else:
            self._falhar(acao, "tipo_sem_executor")
        self._fim_passo()

    def _validar_estado_atual(self, pokemon, acao):
        if pokemon is None:
            return "pokemon_inexistente_execucao"
        if not pokemon.esta_vivo():
            return "pokemon_morto_execucao"
        if int(pokemon.lado_id) != int((acao or {}).get("lado_id", -1)):
            return "lado_divergente_execucao"
        if pokemon.estados_transitorios.get("entrou_na_rodada"):
            return "pokemon_entrou_na_rodada"
        if pokemon.estados_transitorios.get("recuado"):
            return "pokemon_recuado"
        tipo = str((acao or {}).get("tipo") or "")
        if tipo != "captura" and (pokemon.possui_efeito("Dormindo") or pokemon.possui_efeito("Congelado")):
            return "pokemon_inapto"
        if tipo == "ataque" and pokemon.possui_efeito("Paralisado"):
            return "ataque_bloqueado_por_paralisia"
        if tipo in {"movimento", "troca_posicao", "troca_reserva"} and pokemon.possui_efeito("Enraizado"):
            return "movimento_bloqueado_por_enraizado"
        if str((acao or {}).get("tipo")) in {"ataque", "movimento", "troca_posicao", "troca_reserva", "captura"} and (not pokemon.ativo or pokemon.reserva):
            return "pokemon_nao_ativo_execucao"
        return None

    def _executar_movimento(self, pokemon, acao):
        if pokemon.possui_efeito("Enraizado") or pokemon.possui_efeito("Congelado") or pokemon.possui_efeito("Dormindo"):
            self._falhar(acao, "movimento_bloqueado_por_efeito")
            return
        destino = acao.get("destino") if isinstance(acao.get("destino"), dict) else {}
        area_id = destino.get("area_id")
        ocupante = self.partida.pokemon_na_area(area_id)
        if ocupante is None:
            if not self.partida.mover_pokemon_para_area(pokemon, area_id, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
                self._falhar(acao, "movimento_falhou")
            return
        if int(ocupante.lado_id) == int(pokemon.lado_id):
            if not self.partida.trocar_posicao(pokemon, ocupante, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
                self._falhar(acao, "troca_posicao_convertida_falhou")
            return
        self._falhar(acao, "area_ocupada_por_oponente")

    def _executar_troca_posicao(self, pokemon, acao):
        outro = self.partida.obter_pokemon(acao.get("pokemon_destino_id"))
        if outro is None or not outro.esta_vivo():
            self._falhar(acao, "troca_posicao_alvo_morto")
            return
        if not self.partida.trocar_posicao(pokemon, outro, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
            self._falhar(acao, "troca_posicao_falhou")

    def _executar_troca_reserva(self, pokemon, acao):
        reserva = self.partida.obter_pokemon(acao.get("pokemon_reserva_id") or acao.get("troca_reserva_id"))
        if reserva is None or not reserva.esta_vivo():
            self._falhar(acao, "reserva_morta_ou_inexistente")
            return
        if not self.partida.trocar_reserva(pokemon, reserva, dados={"reativos_acao": (acao or {}).get("reativos_acao")}):
            self._falhar(acao, "troca_reserva_falhou")

    def _executar_ataque(self, pokemon, acao):
        props = acao.get("propriedades") if isinstance(acao.get("propriedades"), dict) else None
        if not props:
            self._falhar(acao, "ataque_sem_propriedades")
            return
        animacao = self._dados_animacao(props)
        contexto = {
            "partida": self.partida,
            "usuario": pokemon,
            "acao": acao,
            "propriedades": props,
            "ataque": acao.get("ataque") if isinstance(acao.get("ataque"), dict) else {},
            "custo_real": float(acao.get("custo_real") or 0.0),
            "passo": self.partida.passo_atual,
            "rng": self.partida.rng,
            "alvos": [],
            "primeiro_ataque_da_rodada": self._ataques_executados == 0,
        }
        chave_ataque = props.get("ID") or (contexto["ataque"] or {}).get("ID") or (contexto["ataque"] or {}).get("Code") or props.get("nome")
        contexto["reativos_acao"] = obter_executes_reativos(chave_ataque)
        alvos = executar_alvificacao(chave_ataque, contexto)
        contexto["alvos"] = list(alvos or [])
        alvo_ids = [alvo.id_batalha for alvo in contexto["alvos"] if alvo is not None]
        alvo_principal_id = alvo_ids[0] if alvo_ids else None
        alvos_secundarios_ids = []
        if normalizar(animacao.get("modelo")) == "explosao" and contexto["alvos"]:
            secundarios = inimigos_vivos_adjacentes_ao_alvo(contexto, contexto["alvos"][0])
            alvos_secundarios_ids = [alvo.id_batalha for alvo in secundarios if alvo is not None]
            alvo_ids = [alvo_principal_id, *alvos_secundarios_ids]
        self.partida.registrar_evento_log("ataque_usado", self._dados_ataque(pokemon, acao, props, alvo_ids=alvo_ids, animacao=animacao, alvo_principal_id=alvo_principal_id, alvos_secundarios_ids=alvos_secundarios_ids))
        if not contexto["alvos"] and str(props.get("estilo_logico") or "").lower() != "ativo":
            self.partida.registrar_evento_log("ataque_sem_alvo_real", self._dados_ataque(pokemon, acao, props, alvo_ids=[], animacao=animacao))
            self._falhar(acao, "sem_alvo_real")
            return
        atingiu = False
        if str(props.get("estilo_logico") or "").lower() == "ativo":
            retorno = executar_execute_principal(chave_ataque, contexto, alvo=None)
            if retorno.get("falha"):
                self._falhar(acao, str(retorno.get("motivo") or "execute_falhou"))
            else:
                self.partida.registrar_evento_log("ataque_acertou", self._dados_ataque(pokemon, acao, props, alvo_ids=[pokemon.id_batalha], alvo=pokemon, animacao=animacao, alvo_principal_id=pokemon.id_batalha))
                atingiu = True
        else:
            for alvo in contexto["alvos"]:
                if alvo is None or not alvo.esta_vivo():
                    continue
                ctx_alvo = dict(contexto)
                ctx_alvo["alvo"] = alvo
                ctx_flag = {
                    "partida": self.partida,
                    "usuario": pokemon,
                    "alvo": alvo,
                    "pokemon_evento": alvo,
                    "acao": acao,
                    "ataque": contexto.get("ataque"),
                    "propriedades": props,
                    "reativos_acao": contexto.get("reativos_acao"),
                }
                self.partida.disparar_flag("AntesReceberAtaque", ctx_flag, reativos=contexto.get("reativos_acao"))
                acerto = self._calcular_acerto(pokemon, alvo, props)
                ctx_alvo["bonus_critico_acerto"] = acerto.get("bonus_critico_acerto", 0.0)
                if not acerto.get("acertou"):
                    self.partida.registrar_evento_log("ataque_errou", {**self._dados_ataque(pokemon, acao, props, alvo_ids=[alvo.id_batalha], alvo=alvo, animacao=animacao, alvo_principal_id=alvo_principal_id), "acerto": acerto})
                    self._falhar(acao, "ataque_errou", alvo_id=alvo.id_batalha)
                    continue
                self.partida.registrar_evento_log("ataque_acertou", {**self._dados_ataque(pokemon, acao, props, alvo_ids=[alvo.id_batalha], alvo=alvo, animacao=animacao, alvo_principal_id=alvo_principal_id), "acerto": acerto})
                retorno = executar_execute_principal(chave_ataque, ctx_alvo, alvo=alvo)
                if retorno.get("falha"):
                    self._falhar(acao, str(retorno.get("motivo") or "execute_falhou"), alvo_id=alvo.id_batalha)
                else:
                    atingiu = True
        if atingiu:
            self._ataques_executados += 1

    def _executar_captura(self, pokemon, acao):
        tipo_batalha = str(getattr(self.partida, "tipo_batalha", "") or "").strip().lower()
        if tipo_batalha != "confronto":
            self._falhar(acao, "captura_bloqueada_tipo_batalha" if tipo_batalha in {"servo", "boss"} else "captura_fora_de_confronto")
            return
        lado_id = int((acao or {}).get("lado_id", getattr(self.partida, "lado_jogador", 50)) or getattr(self.partida, "lado_jogador", 50))
        jogador_nome = str((acao or {}).get("jogador_nome") or "Jogador").strip() or "Jogador"
        usuario_id = str((acao or {}).get("usuario_id") or f"jogador_{lado_id}")
        alvo = self.partida.obter_pokemon(((acao or {}).get("alvo") or {}).get("pokemon_id") if isinstance((acao or {}).get("alvo"), dict) else None)
        if alvo is None:
            self._falhar(acao, "captura_alvo_inexistente")
            return
        if int(getattr(alvo, "lado_id", -1)) == int(lado_id):
            self._falhar(acao, "captura_alvo_aliado", alvo_id=alvo.id_batalha)
            return
        if not alvo.esta_vivo() or not bool(getattr(alvo, "ativo", False)) or bool(getattr(alvo, "reserva", False)):
            self._falhar(acao, "captura_alvo_invalido", alvo_id=alvo.id_batalha)
            return
        item_base_id = str((acao or {}).get("item_base_id") or ((acao or {}).get("bola") or {}).get("item_base_id") or ((acao or {}).get("bola") or {}).get("Code") or "").strip()
        item_nome = str((acao or {}).get("item_nome") or ((acao or {}).get("bola") or {}).get("Nome") or "Pokeball").strip()
        if not self.partida.consumir_pokebola_batalha(lado_id, item_base_id, item_nome):
            self._falhar(acao, "pokebola_indisponivel", alvo_id=alvo.id_batalha)
            return
        self.partida.registrar_evento_log(
            "captura_batalha_lancada",
            {
                "id_acao": acao.get("id_acao"),
                "usuario_id": usuario_id,
                "usuario_nome": jogador_nome,
                "capturador_tipo": "jogador",
                "lado_id": lado_id,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "bola_nome": item_nome,
                "item_base_id": item_base_id,
            },
        )
        resultado = resolver_captura_batalha(
            alvo,
            item_nome,
            contexto={
                "rng": self.partida.rng,
                "regras": getattr(self.partida, "regras_mundo", {}) or getattr(self.partida, "regras", {}),
                "em_batalha": True,
                "captura_critica_cliente": False,
                "captura_chance_checks_necessarios": 3,
            },
        )
        sucesso = bool(resultado.get("sucesso", False))
        snapshot = None
        if sucesso:
            snapshot = self.partida.snapshot_pokemon_capturado_batalha(alvo, efeitos_bola=resultado.get("efeitos_bola") if isinstance(resultado.get("efeitos_bola"), dict) else {})
            self.partida.adicionar_pokemon_capturado_batalha(lado_id, snapshot)
            self.partida.remover_pokemon_capturado_batalha(alvo)
        self.partida.registrar_evento_log(
            "captura_batalha_resultado",
            {
                "id_acao": acao.get("id_acao"),
                "usuario_id": usuario_id,
                "usuario_nome": jogador_nome,
                "capturador_tipo": "jogador",
                "lado_id": lado_id,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "bola_nome": item_nome,
                "item_base_id": item_base_id,
                "checagens": list(resultado.get("checagens") or []),
                "resultado": "sucesso" if sucesso else "falha",
                "capturado": sucesso,
                "chance_check": resultado.get("chance_check"),
                "chance_real_3_checks": resultado.get("chance_real_3_checks"),
                "dificuldade_batalha": resultado.get("dificuldade_batalha"),
                "poder_total": resultado.get("poder_total"),
                "pokemon_capturado": snapshot if sucesso else None,
                "inventario_jogador": copy.deepcopy(self.partida.inventarios_lado.get(int(self.partida.lado_jogador), {})),
            },
        )
        self.partida.registrar_evento_log(
            "inventario_atualizado_batalha",
            {
                "lado_id": int(lado_id),
                "inventario": copy.deepcopy(self.partida.inventarios_lado.get(int(lado_id), {})),
            },
        )

    def _acertou(self, usuario, alvo):
        return bool(self._calcular_acerto(usuario, alvo).get("acertou"))

    def _calcular_acerto(self, usuario, alvo, props=None):
        props = props if isinstance(props, dict) else {}
        parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
        acuracia_ataque = float(parametros.get("acuracia", props.get("acuracia", 100.0)) or 100.0) / 100.0
        acuracia = (usuario.obter_atributo("Acuracia", 100.0) / 100.0) * acuracia_ataque
        assertividade = alvo.obter_atributo("Assertividade", 100.0) / 100.0
        chance = acuracia * assertividade
        vel_usuario = usuario.obter_atributo("Vel", 0.0)
        vel_alvo = alvo.obter_atributo("Vel", 0.0)
        media = (vel_usuario + vel_alvo) / 2.0
        escudo = 10.0
        if vel_usuario > media + escudo:
            chance += (vel_usuario - media - escudo) / 100.0
        elif vel_usuario < media - escudo:
            chance -= (media - escudo - vel_usuario) / 100.0
        if vel_alvo > media + escudo:
            chance -= (vel_alvo - media - escudo) / 100.0
        elif vel_alvo < media - escudo:
            chance += (media - escudo - vel_alvo) / 100.0
        tipo_ataque = parametros.get("tipo") or props.get("tipo") or "normal"
        if alvo.possui_efeito("Flutuando") and str(tipo_ataque or "").strip().lower() == "normal":
            chance -= 0.40
        chance_percentual = max(0.0, chance * 100.0)
        chance_real = min(100.0, chance_percentual)
        bonus_critico = max(0.0, chance_percentual - 100.0) / 2.0
        sorte = self.partida.rng.random() * 100.0
        return {
            "acertou": sorte <= chance_real,
            "chance_final": round(chance_percentual, 4),
            "chance_real": round(chance_real, 4),
            "bonus_critico_acerto": round(bonus_critico, 4),
            "rolagem": round(sorte, 4),
        }

    def _fim_passo(self):
        for pokemon in list(self.partida.pokemons_por_id.values()):
            pokemon.Verificar()
        for pokemon in list(self.partida.pokemons_por_id.values()):
            if pokemon.esta_vivo():
                pokemon.aplicar_efeitos_por_passo()
        if hasattr(self.partida, "processar_clima_por_passo"):
            self.partida.processar_clima_por_passo()
        for pokemon in list(self.partida.pokemons_por_id.values()):
            if pokemon.esta_vivo():
                pokemon.decrementar_efeitos(self.partida.passo_atual)
        self.partida.verificar_fim_batalha()
        self.partida.disparar_flag("AoFimDoPasso", {"partida": self.partida, "passo_atual": self.partida.passo_atual})

    def _falhar(self, acao, motivo, alvo_id=None):
        falha = {
            "id_acao": (acao or {}).get("id_acao"),
            "pokemon_id": (acao or {}).get("pokemon_id"),
            "tipo": (acao or {}).get("tipo"),
            "motivo": str(motivo),
        }
        if alvo_id is not None:
            falha["alvo_id"] = alvo_id
        self.acoes_falhas.append(falha)
        self.partida.registrar_evento_log("acao_falhou", falha)

    def _registrar_acao_iniciada(self, acao, pokemon):
        dados = {
            "id_acao": (acao or {}).get("id_acao"),
            "tipo": (acao or {}).get("tipo"),
            "tipo_acao": (acao or {}).get("tipo"),
            "pokemon_id": (acao or {}).get("pokemon_id"),
            "pokemon_nome": getattr(pokemon, "nome", None),
            "jogador_nome": (acao or {}).get("jogador_nome") if str((acao or {}).get("tipo") or "") == "captura" else None,
            "lado_id": (acao or {}).get("lado_id"),
            "ordem_local": (acao or {}).get("ordem_local"),
            "custo_real": (acao or {}).get("custo_real"),
        }
        ataque = (acao or {}).get("ataque") if isinstance((acao or {}).get("ataque"), dict) else None
        alvo = (acao or {}).get("alvo") if isinstance((acao or {}).get("alvo"), dict) else None
        destino = (acao or {}).get("destino") if isinstance((acao or {}).get("destino"), dict) else None
        if ataque:
            dados["ataque"] = copy.deepcopy(ataque)
        if alvo:
            dados["alvo"] = copy.deepcopy(alvo)
        if destino:
            dados["destino"] = copy.deepcopy(destino)
        self.partida.registrar_evento_log("acao_iniciada", dados)

    def _dados_animacao(self, props):
        animacao = copy.deepcopy(props.get("animacao") if isinstance(props.get("animacao"), dict) else {})
        visual = props.get("visual") if isinstance(props.get("visual"), dict) else {}
        if visual:
            animacao.setdefault("visual", copy.deepcopy(visual))
        for chave in ("modelo", "projetil", "efeito_alvo", "efeito_executor"):
            if chave in props and chave not in animacao:
                animacao[chave] = copy.deepcopy(props.get(chave))
        animacao.setdefault("modelo", "EfeitoAlvo")
        animacao.setdefault("efeito_executor", None)
        animacao.setdefault("efeito_alvo", None)
        return animacao

    def _dados_ataque(self, pokemon, acao, props, alvo_ids=None, alvo=None, animacao=None, alvo_principal_id=None, alvos_secundarios_ids=None):
        ataque = (acao or {}).get("ataque") if isinstance((acao or {}).get("ataque"), dict) else {}
        alvo_dict = (acao or {}).get("alvo") if isinstance((acao or {}).get("alvo"), dict) else {}
        parametros = props.get("parametros") if isinstance(props.get("parametros"), dict) else {}
        tipo_ataque = parametros.get("tipo") or props.get("tipo") or ataque.get("Tipo") or ataque.get("tipo") or "normal"
        dados = {
            "id_acao": (acao or {}).get("id_acao"),
            "ataque_id": ataque.get("ID") or ataque.get("Code") or props.get("ID"),
            "ataque_nome": ataque.get("nome") or ataque.get("Nome") or props.get("nome"),
            "tipo_ataque": tipo_ataque,
            "usuario_id": pokemon.id_batalha,
            "usuario_nome": pokemon.nome,
            "pokemon_id": pokemon.id_batalha,
            "pokemon_nome": pokemon.nome,
            "area_origem": pokemon.area_id,
            "area_alvo": alvo_dict.get("area_id"),
            "alvos_ids": list(alvo_ids or []),
            "alvo_principal_id": alvo_principal_id,
            "alvos_secundarios_ids": list(alvos_secundarios_ids or []),
            "animacao": copy.deepcopy(animacao or self._dados_animacao(props)),
            "visual": copy.deepcopy(props.get("visual") if isinstance(props.get("visual"), dict) else {}),
            "modelo": (animacao or {}).get("modelo") if isinstance(animacao, dict) else None,
        }
        if alvo is not None:
            dados.update({"alvo_id": alvo.id_batalha, "alvo_nome": alvo.nome, "area_alvo_real": alvo.area_id})
        return dados
