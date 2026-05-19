from Codigo.ModulosGerais.EfeitosTela import FecharIris, AbrirIris
from Codigo.ModulosGerais.Camera import CameraBatalha
from Codigo.ModulosBatalha.Arena import Arena
from Codigo.ModulosBatalha.ClimaBatalha import ClimaBatalha
from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha
from Codigo.Telas.Subtelas.SubtelaOpcoes import SubtelaOpcoes
from Codigo.ModulosGerais.Server.ServerMundo import finalizar_interacao_npc_mundo, solicitar_contexto_batalha_mundo
from Codigo.ModulosGerais.Server.ServerTerminal import buscar_mensagens_terminal, enviar_mensagem_terminal
from Codigo.Telas.Telas.TelaConfig import TelaConfig, ResetTelaConfig
from Codigo.Telas.Telas.TelaCreditos import TelaCreditos
from Codigo.Prefabs.Terminal import Terminal
import pygame
from copy import deepcopy
import random
import unicodedata


class CenaCombate:
    def PrepararTransicaoAssincrona(self, JOGO) -> None:
        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        if str(contexto.get("tipo") or "confronto").strip().lower() not in {"confronto", "treinador", "trainer", "servo", "boss"}:
            return
        tiles = contexto.get("tiles")
        if isinstance(tiles, list) and tiles:
            return
        pokemon_colisao = contexto.get("pokemon_colisao") if isinstance(contexto.get("pokemon_colisao"), dict) else {}
        server_ip = str(contexto.get("server_ip") or "")
        client_id = str(contexto.get("client_id") or JOGO.INFO.get("UsuarioLogado", "anon"))
        pokemon_id = int(pokemon_colisao.get("id", pokemon_colisao.get("Id", pokemon_colisao.get("ID", 0))) or 0)
        centro = contexto.get("posicao_referencia_mundo")
        if not isinstance(centro, (list, tuple)) or len(centro) != 2:
            centro = pokemon_colisao.get("posicao")
        if not isinstance(centro, (list, tuple)) or len(centro) != 2:
            centro = contexto.get("centro")
        if not isinstance(centro, (list, tuple)) or len(centro) != 2:
            centro = [40.0, 20.0]
        if not server_ip:
            return
        ret = solicitar_contexto_batalha_mundo(server_ip, client_id, pokemon_id, centro)
        contexto_servidor = ret.get("contexto_batalha") if isinstance(ret, dict) and isinstance(ret.get("contexto_batalha"), dict) else {}
        if not contexto_servidor:
            return
        inimigos_servidor = contexto_servidor.get("pokemons_inimigo") if isinstance(contexto_servidor.get("pokemons_inimigo"), list) else None
        JOGO.INFO["CombateContexto"] = {
            **dict(contexto),
            **dict(contexto_servidor),
            "pokemon_colisao": dict(pokemon_colisao),
            "pokemons_inimigo": list(inimigos_servidor if inimigos_servidor is not None else contexto.get("pokemons_inimigo") or []),
            "time_jogador": dict(contexto.get("time_jogador") or {}),
            "times_jogador": list(contexto.get("times_jogador") or []),
            "pokemons_jogador": list(contexto.get("pokemons_jogador") or []),
        }

    def Inicializar(self, JOGO):
        self._jogo_ref = JOGO
        self.Abertura = AbrirIris
        self.Fechamento = FecharIris
        self.ID = "Combate"
        self.TelaAtual = "Combate"

        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        regras_mundo = JOGO.INFO.get("RegrasMundo") if isinstance(JOGO.INFO.get("RegrasMundo"), dict) else {}
        gerais = regras_mundo.get("gerais") if isinstance(regras_mundo.get("gerais"), dict) else {}
        tile_px = int(gerais.get("combate_camera_px_por_tile", 40))
        largura = float(contexto.get("largura", 80) or 80)
        altura = float(contexto.get("altura", 40) or 40)
        centro = contexto.get("centro") if isinstance(contexto.get("centro"), (list, tuple)) and len(contexto.get("centro")) == 2 else [largura * 0.5, altura * 0.5]
        arena_w = float(contexto.get("arena_largura", 40) or 40)
        arena_h = float(contexto.get("arena_altura", 20) or 20)
        half_w = (float(JOGO.TELA.get_size()[0]) / float(tile_px)) * 0.5
        half_h = (float(JOGO.TELA.get_size()[1]) / float(tile_px)) * 0.5
        pos_inicial = (float(centro[0]) - half_w, float(centro[1]) - half_h)

        self.Camera = CameraBatalha(JOGO.TELA.get_size(), posicao_inicial_tiles=pos_inicial, tile_px=tile_px)
        self.Camera.definir_limites_mundo(largura, altura)
        self.Camera.definir_referencia_arena(
            (float(centro[0]) - (arena_w * 0.5), float(centro[1]) - (arena_h * 0.5)),
            (arena_w, arena_h),
        )
        self.Camera.atualizar(0.0)
        self.Arena = Arena(contexto)
        self.ControladorBatalha = ControladorBatalha(self.Camera, jogo=JOGO)
        self.ControladorBatalha.iniciar(self._estado_inicial_batalha(JOGO, contexto))
        self.ClimaBatalha = ClimaBatalha()
        self._tela_creditos = TelaCreditos()

        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        usuario = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        self.Terminal = Terminal(
            pygame.Rect(14, 14, 520, 220),
            callback_enviar=lambda texto: self._enviar_terminal_batalha(link, usuario, texto),
            callback_buscar=lambda ultimo_id: buscar_mensagens_terminal(link, ultimo_id=ultimo_id, contexto="batalha", meta=self._meta_terminal_batalha(JOGO)) if link else {"status": "ok", "mensagens": []},
            autor_local=usuario,
            tecla_abrir=pygame.K_t,
        )
        self.Terminal.iniciar()
        self._eventos_ui_atual = []

    def _estado_inicial_batalha(self, JOGO, contexto):
        estado = deepcopy(contexto or {})
        estado.setdefault("tipo_batalha", estado.get("tipo") or "confronto")
        estado.setdefault("lado_jogador", 50)
        estado.setdefault("modo_teste", False)
        if isinstance(JOGO.INFO.get("RegrasMundo"), dict):
            estado.setdefault("regras_mundo", deepcopy(JOGO.INFO.get("RegrasMundo") or {}))
        if isinstance(estado.get("batalha"), dict):
            estado.setdefault("regras", deepcopy(estado.get("batalha") or {}))
        if not estado.get("pokemons_inimigo") and not estado.get("pokemons_adversario"):
            pokemon_colisao = estado.get("pokemon_colisao") if isinstance(estado.get("pokemon_colisao"), dict) else None
            if pokemon_colisao is not None:
                estado["pokemons_inimigo"] = [deepcopy(pokemon_colisao)]
        self._definir_posicoes_iniciais_cliente(estado)
        return estado

    def _definir_posicoes_iniciais_cliente(self, estado: dict) -> None:
        def _slots_time(chave_time, chave_lista):
            time = estado.get(chave_time)
            if isinstance(time, dict) and isinstance(time.get("Slots"), list):
                return time.get("Slots")
            if isinstance(estado.get(chave_lista), list):
                return estado.get(chave_lista)
            return None

        def _aplicar(lista, lado_id, prefixo):
            if not isinstance(lista, list):
                return
            indices_validos = [i for i, p in enumerate(lista) if isinstance(p, dict)]
            areas = [f"{prefixo}{i}" for i in range(1, 10)]
            random.shuffle(areas)
            ativos = set(indices_validos[:3])
            for ordem, idx in enumerate(indices_validos):
                pokemon = lista[idx]
                pokemon["lado_id"] = int(lado_id)
                if idx in ativos:
                    pokemon["ativo"] = True
                    pokemon["Ativo"] = True
                    pokemon["em_reserva"] = False
                    pokemon["EmReserva"] = False
                    pokemon["area_id"] = areas.pop(0) if areas else f"{prefixo}{ordem + 1}"
                    pokemon["AreaId"] = pokemon["area_id"]
                else:
                    pokemon["ativo"] = False
                    pokemon["Ativo"] = False
                    pokemon["em_reserva"] = True
                    pokemon["EmReserva"] = True
                    pokemon.pop("area_id", None)
                    pokemon.pop("AreaId", None)

        _aplicar(_slots_time("time_jogador", "pokemons_jogador"), 50, "A")
        inimigos = _slots_time("time_inimigo", "pokemons_inimigo")
        if inimigos is None:
            inimigos = _slots_time("time_adversario", "pokemons_adversario")
        _aplicar(inimigos, 51, "I")

    def _meta_terminal_batalha(self, jogo) -> dict:
        contexto = jogo.INFO.get("CombateContexto") if isinstance(jogo.INFO.get("CombateContexto"), dict) else {}
        controlador = getattr(self, "ControladorBatalha", None)
        meta = {
            "batalha_id": str(contexto.get("batalha_id_servidor") or getattr(controlador, "id_partida", "") or ""),
            "client_id": str(contexto.get("client_id") or jogo.INFO.get("UsuarioLogado", "anon")),
        }
        return meta

    def _enviar_terminal_batalha(self, link: str, usuario: str, texto: str) -> dict:
        if not link:
            return {"status": "erro", "mensagem": "Servidor indisponível"}
        resposta = enviar_mensagem_terminal(link, usuario, texto, contexto="batalha", meta=self._meta_terminal_batalha(self._jogo_ref))
        self._aplicar_atualizacao_terminal_batalha(resposta)
        return resposta

    def _aplicar_atualizacao_terminal_batalha(self, resposta: dict) -> None:
        if not isinstance(resposta, dict):
            return
        atualizacao = resposta.get("batalha_atualizacao") if isinstance(resposta.get("batalha_atualizacao"), dict) else {}
        if not atualizacao:
            return
        controlador = getattr(self, "ControladorBatalha", None)
        if controlador is None:
            return
        if "modo_teste" in atualizacao:
            controlador.definir_modo_teste(bool(atualizacao.get("modo_teste")))
        log = atualizacao.get("log")
        if isinstance(log, dict) and list(log.get("historico") or []):
            controlador.receber_log(log)
        resultado = atualizacao.get("resultado") if isinstance(atualizacao.get("resultado"), dict) else None
        if isinstance(resultado, dict):
            controlador.aplicar_resultado_final(resultado)
            if bool(resultado.get("finalizada")) and getattr(controlador, "finalizador", None) is not None:
                controlador.finalizador.finalizar_por_resultado(resultado)

    def _fugir_combate(self, jogo) -> None:
        jogo.INFO["ImuneCombatePendenteMundo"] = True
        jogo.CenaAlvo = "Mundo"

    def _cancelar_batalha_com_esc(self) -> bool:
        controlador = getattr(self, "ControladorBatalha", None)
        montador = getattr(controlador, "montador_jogadas", None)
        if montador is not None and str(getattr(montador, "estado_montagem", "")) in {"preparando_ataque", "arrastando"}:
            montador.cancelar_previa()
            if controlador is not None:
                controlador.limpar_ataque()
            return True
        return False

    def DefinirTela(self, tela):
        if tela == "Config":
            ResetTelaConfig()
        self.TelaAtual = str(tela)

    def atualizar_cena(self, JOGO, EVENTOS, dt):
        if self._tela_creditos.ativa:
            self._tela_creditos.atualizar(EVENTOS, dt, JOGO)
            self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()
            self.Camera.atualizar(dt)
            self._eventos_ui_atual = []
            return
        if self.TelaAtual == "Config":
            return
        self.Camera.TamanhoTelaPx = JOGO.TELA.get_size()
        eventos_ui = list(EVENTOS or [])
        if self.Terminal is not None:
            eventos_ui = self.Terminal.processar_eventos(eventos_ui)
        opcoes_modal = JOGO.GerenciadorSubtelas.obter_por_tipo(SubtelaOpcoes)
        if opcoes_modal is None and self.TelaAtual != "Config":
            for ev in eventos_ui:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    if self._cancelar_batalha_com_esc():
                        break
                    opcoes_modal = SubtelaOpcoes()
                    opcoes_modal.toggle(JOGO)
                    JOGO.GerenciadorSubtelas.abrir(opcoes_modal)
                    break
        terminal_digitando = bool(self.Terminal is not None and self.Terminal.esta_digitando)
        bloqueado = opcoes_modal is not None or terminal_digitando
        eventos_batalha = [] if bloqueado else list(eventos_ui)
        self._eventos_ui_atual = list(eventos_ui)
        if self.ControladorBatalha is not None and self.TelaAtual != "Config":
            self.ControladorBatalha.atualizar(dt, eventos_batalha)

    def tela_atual_eh_complexa(self) -> bool:
        return self.TelaAtual != "Config"

    def render_tela(self, surface, JOGO, EVENTOS, dt):
        if self.TelaAtual == "Config":
            TelaConfig(self, JOGO, EVENTOS, dt, tela_destino=surface)

    def render_base(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        if self.ControladorBatalha is not None:
            self.ControladorBatalha.desenhar(surface)
        else:
            surface.fill((20, 20, 28))
            self.Arena.renderizar(surface, self.Camera)

    def render_post(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS)
        clima = getattr(self.ControladorBatalha, "clima_atual", None) if self.ControladorBatalha is not None else None
        if getattr(self, "ClimaBatalha", None) is not None:
            self.ClimaBatalha.coletar_uniformes(surface.get_size(), clima, dt)
            self.ClimaBatalha.desenhar_base(surface)

    def coletar_efeito_shader(self, JOGO, dt, tamanho_tela):
        _ = (JOGO, dt)
        if getattr(self, "_tela_creditos", None) is not None and self._tela_creditos.ativa:
            return self._tela_creditos.coletar_efeito_shader() or {}
        if self.TelaAtual == "Config":
            return None
        efeito = {}
        if getattr(self, "ClimaBatalha", None) is not None:
            efeito = dict(self.ClimaBatalha.uniformes_atuais() or {})
        estados = self._coletar_estados_shader_batalha(tamanho_tela)
        if estados:
            efeito["tipo"] = "batalha"
            efeito["battle_status_targets"] = estados
            efeito["ativo"] = True
        ataques = []
        controlador_animacoes = getattr(getattr(self, "ControladorBatalha", None), "controlador_animacoes", None)
        if controlador_animacoes is not None and hasattr(controlador_animacoes, "coletar_ataques_shader_batalha"):
            ataques = controlador_animacoes.coletar_ataques_shader_batalha(tamanho_tela)
        if ataques:
            efeito["tipo"] = "batalha"
            efeito["battle_attack_fx"] = ataques
            efeito["ativo"] = True
        return efeito or None

    @staticmethod
    def _normalizar_estado_shader(valor):
        bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
        sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
        return "".join(ch for ch in sem_acento if ch.isalnum())

    @staticmethod
    def _codigo_estado_shader(nome_normalizado):
        # Apenas estados que mudam visual/cor do Pokemon de forma persistente.
        # Nao entram aqui estados puramente mecanicos/movimento, como dormindo,
        # confuso, flutuando, voando, furtivo, provocado etc.
        codigos = {
            "envenenado": 1,
            "queimado": 2,
            "cauterizado": 2,
            "energizado": 3,
            "intoxicado": 4,
            "encharcado": 5,
            "abencoado": 6,
            "congelado": 7,
            "amaldicoado": 8,
            "encantado": 9,
        }
        return codigos.get(str(nome_normalizado or ""), 0)

    @staticmethod
    def _prioridade_estado_shader(codigo):
        prioridades = {
            2: 100,  # queimado/cauterizado precisa ser bem perceptivel
            7: 96,   # congelado muda a leitura do alvo
            4: 94,   # intoxicado e mais pesado que veneno comum
            1: 88,
            5: 82,
            3: 80,
            8: 78,
            6: 74,
            9: 70,
        }
        return prioridades.get(int(codigo or 0), 0)

    def _coletar_estados_shader_batalha(self, tamanho_tela):
        controlador = getattr(self, "ControladorBatalha", None)
        pokemons = list(getattr(controlador, "pokemons", []) or []) if controlador is not None else []
        if not pokemons:
            return []
        try:
            largura = max(1, int(tamanho_tela[0]))
            altura = max(1, int(tamanho_tela[1]))
        except Exception:
            largura, altura = 1, 1

        saida = []
        max_estados_shader = 12
        for pokemon in pokemons:
            if len(saida) >= max_estados_shader:
                break
            if not bool(getattr(pokemon, "Ativo", False)) or bool(getattr(pokemon, "EmReserva", False)):
                continue
            if controlador is not None and hasattr(controlador, "pokemon_visivel") and not controlador.pokemon_visivel(pokemon):
                continue
            rect = getattr(pokemon, "RectAtual", None)
            if rect is None or int(getattr(rect, "width", 0) or 0) <= 0 or int(getattr(rect, "height", 0) or 0) <= 0:
                continue
            cx = float(rect.centerx) / float(largura)
            cy = float(rect.centery) / float(altura)
            if cx < -0.10 or cx > 1.10 or cy < -0.10 or cy > 1.10:
                continue

            # Raio em UV vertical. Usa a altura para manter a escala consistente
            # mesmo em telas wide. O shader corrige aspect no eixo X.
            raio = max(float(rect.width), float(rect.height)) / float(altura) * 0.76
            raio = max(0.030, min(0.165, raio))

            animacoes_entrada = getattr(pokemon, "AnimacoesEfeitos", {}) if isinstance(getattr(pokemon, "AnimacoesEfeitos", {}), dict) else {}
            animacoes_saida = getattr(pokemon, "EfeitosSaindo", {}) if isinstance(getattr(pokemon, "EfeitosSaindo", {}), dict) else {}
            efeitos_preparados = []
            for efeito in list(getattr(pokemon, "EfeitosFormais", []) or []):
                if not isinstance(efeito, dict):
                    continue
                nome_norm = self._normalizar_estado_shader(efeito.get("code") or efeito.get("nome"))
                codigo = self._codigo_estado_shader(nome_norm)
                if codigo <= 0:
                    continue
                entrada = max(0.0, min(1.0, float(animacoes_entrada.get(nome_norm, 1.0) or 0.0)))
                saida_anim = max(0.0, min(1.0, float(animacoes_saida.get(nome_norm, 0.0) or 0.0)))
                power = (0.54 + 0.46 * entrada) * (1.0 - saida_anim)
                if codigo in (2, 4, 7):
                    power *= 1.12
                elif codigo in (5, 6, 9):
                    power *= 0.92
                power = max(0.0, min(1.0, power * 0.96))
                if power <= 0.001:
                    continue
                efeitos_preparados.append((self._prioridade_estado_shader(codigo), codigo, power, nome_norm))

            efeitos_preparados.sort(reverse=True)
            for _, codigo, power, _nome_norm in efeitos_preparados:
                if len(saida) >= max_estados_shader:
                    break
                saida.append({"pos_uv": (cx, cy), "radius": raio, "tipo": codigo, "power": power})
        return saida

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        eventos_ui = list(getattr(self, "_eventos_ui_atual", EVENTOS) or [])
        if self.Terminal is not None:
            self.Terminal.desenhar(surface, eventos_ui, dt)
        self._tela_creditos.desenhar(surface, EVENTOS, dt, JOGO)

    def abrir_creditos_pos_batalha(self, JOGO):
        self._abrir_creditos(JOGO)

    def _abrir_creditos(self, JOGO):
        gerenciador = getattr(JOGO, "GerenciadorSubtelas", None)
        if gerenciador is not None:
            gerenciador.limpar()
        JOGO.INFO["CreditosAtivos"] = True
        self._tela_creditos.abrir(JOGO.TELA.get_size(), ao_finalizar=lambda: self._finalizar_creditos(JOGO))

    def _finalizar_creditos(self, JOGO):
        JOGO.INFO.pop("CreditosAtivos", None)
        JOGO.INFO.pop("CombateContextoTemporario", None)
        JOGO.Escuro = 100
        JOGO.CenaAlvo = "Menu"

    def Tela(self, JOGO, EVENTOS, dt):
        self.atualizar_cena(JOGO, EVENTOS, dt)
        if self.tela_atual_eh_complexa():
            self.render_base(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_post(JOGO.TELA, JOGO, EVENTOS, dt)
            self.render_hud(JOGO.TELA, JOGO, EVENTOS, dt)
        else:
            self.render_tela(JOGO.TELA, JOGO, EVENTOS, dt)

    def Finalizar(self, JOGO):
        if getattr(self, "ControladorBatalha", None) is not None:
            self.ControladorBatalha.sincronizar_perfil_local()
        if self.Terminal is not None:
            self.Terminal.parar()
        contexto = JOGO.INFO.get("CombateContexto") if isinstance(JOGO.INFO.get("CombateContexto"), dict) else {}
        npc_ctx = contexto.get("npc_contexto") if isinstance(contexto.get("npc_contexto"), dict) else {}
        npc_id = int(npc_ctx.get("npc_id", 0) or 0)
        if npc_id <= 0:
            return
        server = JOGO.INFO.get("ServerSelecionado") if isinstance(JOGO.INFO.get("ServerSelecionado"), dict) else {}
        link = server.get("ip")
        client_id = str(JOGO.INFO.get("UsuarioLogado", "anon"))
        if link:
            finalizar_interacao_npc_mundo(link, client_id, npc_id)
