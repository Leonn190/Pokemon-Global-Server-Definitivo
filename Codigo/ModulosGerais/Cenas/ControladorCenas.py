from Codigo.ModulosGerais.Cenas.CenaMenu import CenaMenu
from Codigo.ModulosGerais.Cenas.CenaMundo import CenaMundo
from Codigo.ModulosGerais.Cenas.CenaCombate import CenaCombate
from Codigo.ModulosGerais.Cenas.CenaCarregamento import CenaCarregamento
from Codigo.ModulosGerais.Cenas.CenaLogin import CenaLogin
import pygame
import re
import time
import threading
import shutil
from pathlib import Path

from Codigo.ModulosGerais.Auxiliares import bioma_por_tile
from Codigo.ModulosGerais.Sonoridades import SISTEMA_MUSICAS, tile_mundo_atual
from Codigo.ModulosGerais.EfeitosTela import aplicar_claridade, Escurecer
from Codigo.Prefabs.Texto import Texto
from Codigo.ModulosGerais.Discord import DiscordPresence
from Codigo.Telas.Subtelas.Subtela import GerenciadorSubtelas
from Codigo.Telas.Subtelas.SubtelaDialogo import SubtelaDialogo
from Codigo.ModulosGerais.PipelineGrafica import PipelineGrafica

class ControladorCenas:
    def __init__(self, TELA, RELOGIO, CONFIG, tela_display=None, janela_opengl=False):
        self.TELA = TELA
        self.TelaDisplay = tela_display if tela_display is not None else TELA
        self.JanelaOpenGL = bool(janela_opengl)
        self.RELOGIO = RELOGIO
        self.CONFIG = CONFIG
        self.INFO = {
        }
        self.FilaMensagensTecnicas = []

        self.Cenas = {
            "Carregamento": CenaCarregamento(),
            "Login": CenaLogin(),
            "Menu": CenaMenu(),
            "Mundo": CenaMundo(),
            "Combate": CenaCombate(),
        }

        self.Escuro = 100
        self.CenaAlvo = None
        self.Cena = None
        self.Rodando = True
        self.Saindo = False
        self._encerrado = False
        self._preparacao_alvo = None
        self._preparacao_thread = None

        self.Discord = DiscordPresence()
        self.GerenciadorSubtelas = GerenciadorSubtelas()
        self.PipelineGrafica = PipelineGrafica(self.TELA, tela_display=self.TelaDisplay)
        if self.JanelaOpenGL and not self.PipelineGrafica.shader_disponivel():
            self.TelaDisplay = pygame.display.set_mode(self.TELA.get_size(), pygame.NOFRAME)
            self.JanelaOpenGL = False
            self.PipelineGrafica = PipelineGrafica(self.TELA, tela_display=self.TelaDisplay)
        self.INFO["ShaderSuportado"] = self.PipelineGrafica.shader_disponivel()
        self.INFO["ShaderFallback"] = self.PipelineGrafica.motivo_fallback()

        self.TextoFPS = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 12),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoPing = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 44),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoCoords = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 76),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self.TextoHorario = Texto(
            "",
            pos=(self.TELA.get_width() - 16, 108),
            style={
                "size": 24,
                "align": "topright",
                "outline": True,
                "outline_thickness": 1,
                "shadow": False,
            },
        )

    def DefinirCena(self):
        
        if self.Cena is not None:
            self.INFO.update({"UltimaCena": self.Cena.ID})
            preservando_mundo = self.Cena.ID == "Mundo" and self.CenaAlvo == "Menu" and self.INFO.get("MundoTelaSobreposta")
            retornando_para_mundo = self.Cena.ID == "Menu" and self.CenaAlvo == "Mundo"
            if not preservando_mundo and not retornando_para_mundo:
                self.Cena.Finalizar(self)
        self.GerenciadorSubtelas.limpar()
        
        alvo = self.CenaAlvo
        cena_anterior = self.Cena
        self.Cena = self.Cenas[alvo]
        self.CenaAlvo = None
        self._preparacao_alvo = None
        self._preparacao_thread = None
        if not (alvo == "Menu" and cena_anterior is not None and cena_anterior.ID == "Login"):
            self.Escuro = 100
        self.Cena.Inicializar(self)
        self._atualizar_discord_presenca()

    def _garantir_preparacao_transicao(self):
        alvo = self.CenaAlvo
        if alvo is None:
            self._preparacao_alvo = None
            self._preparacao_thread = None
            return
        if self._preparacao_alvo == alvo:
            return
        if alvo == "Mundo" and isinstance(self.INFO.get("MundoPreparadoTransicao"), dict):
            self._preparacao_alvo = alvo
            self._preparacao_thread = None
            return
        self._preparacao_alvo = alvo
        self._preparacao_thread = None
        cena_alvo = self.Cenas.get(str(alvo))
        preparar = getattr(cena_alvo, "PrepararTransicaoAssincrona", None) if cena_alvo is not None else None
        if not callable(preparar):
            return

        def _worker():
            try:
                preparar(self)
            except Exception as exc:
                self.INFO["UltimoErroPreparacaoCena"] = str(exc)

        self._preparacao_thread = threading.Thread(target=_worker, name=f"PreparacaoCena{alvo}", daemon=True)
        self._preparacao_thread.start()

    def _preparacao_transicao_concluida(self) -> bool:
        if self.CenaAlvo is None:
            return False
        if self._preparacao_alvo != self.CenaAlvo:
            return False
        return self._preparacao_thread is None or (not self._preparacao_thread.is_alive())

    def Rodar(self):

        while self.Rodando:
            dt = self.RELOGIO.tick(self.CONFIG["FPS"]) / 1000.0

            EVENTOS = pygame.event.get()
            for e in EVENTOS:
                if e.type == pygame.QUIT:
                    self.SolicitarSair()

            if self.CenaAlvo is not None and self.Escuro == 100:
                self._garantir_preparacao_transicao()
            if self.CenaAlvo is not None and self.Escuro == 100 and self._preparacao_transicao_concluida():
                self.DefinirCena()

            eventos_cena = self.GerenciadorSubtelas.filtrar_eventos_fundo(EVENTOS)
            eventos_render = eventos_cena
            if callable(getattr(self.Cena, "atualizar_cena", None)):
                retorno_atualizacao = self.Cena.atualizar_cena(self, eventos_cena, dt)
                if isinstance(retorno_atualizacao, list):
                    eventos_render = retorno_atualizacao
            self.GerenciadorSubtelas.atualizar(self, EVENTOS, dt)
            self._atualizar_discord_presenca()

            efeito_transicao = None
            if self.Saindo:
                efeito_transicao = Escurecer
            else:
                if self.CenaAlvo is None and self.Escuro != 0:
                    efeito_transicao = self.Cena.Abertura

                if self.CenaAlvo is not None:
                    efeito_transicao = self.Cena.Fechamento


            self.PipelineGrafica.renderizar_frame(
                jogo=self,
                cena=self.Cena,
                eventos=eventos_render,
                dt=dt,
                render_subtelas_scene=lambda surface: self.GerenciadorSubtelas.render(surface, EVENTOS, dt, JOGO=self, camada="scene"),
                render_subtelas_hud=lambda surface: self.GerenciadorSubtelas.render(surface, EVENTOS, dt, JOGO=self, camada="hud"),
                render_adicionais=self.DesenharInfosAdicionais,
                aplicar_claridade=self.AplicarClaridadeGlobal,
                render_transicao=(lambda _surface: efeito_transicao(self, dt)) if callable(efeito_transicao) else None,
            )
            if self.Saindo and self.Escuro >= 100:
                self.Rodando = False
            SISTEMA_MUSICAS.atualizar_musica(self)
            pygame.display.flip()
            time.sleep(0)

        self.Encerrar()

    @staticmethod
    def _texto_limpo(valor, fallback=""):
        texto = str(valor or "").strip()
        texto = " ".join(texto.replace("\n", " ").replace("\r", " ").split())
        return texto or str(fallback or "").strip()

    @staticmethod
    def _titulo_simples(valor):
        texto = ControladorCenas._texto_limpo(valor)
        if not texto:
            return ""
        texto = re.sub(r"[_\-]+", " ", texto)
        texto = re.sub(r"(?<=[a-záàâãéêíóôõúç])(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])", " ", texto)
        texto = " ".join(texto.split())
        return texto[:1].upper() + texto[1:].lower() if texto else ""

    @staticmethod
    def _primeiro_valor_dict(dados, chaves):
        if not isinstance(dados, dict):
            return ""
        for chave in chaves:
            valor = dados.get(chave)
            texto = ControladorCenas._texto_limpo(valor)
            if texto and not texto.isdigit():
                return texto
        mapa = {str(k or "").strip().lower(): v for k, v in dados.items()}
        for chave in chaves:
            valor = mapa.get(str(chave or "").strip().lower())
            texto = ControladorCenas._texto_limpo(valor)
            if texto and not texto.isdigit():
                return texto
        return ""

    @staticmethod
    def _inteiro_seguro(valor, fallback=0):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return int(fallback or 0)

    @staticmethod
    def _nome_pokemon_payload(payload):
        if not isinstance(payload, dict):
            return ""
        estado = payload.get("estado") if isinstance(payload.get("estado"), dict) else {}
        return (
            ControladorCenas._primeiro_valor_dict(payload, ("pokemon_boss", "nome", "Nome", "especie", "Especie"))
            or ControladorCenas._primeiro_valor_dict(estado, ("pokemon_boss", "nome", "Nome", "especie", "Especie"))
        )

    @staticmethod
    def _nome_npc_dialogo(subtela):
        return ControladorCenas._texto_limpo(getattr(subtela, "_npc_nome", ""), "")

    @staticmethod
    def _descricao_bioma(tile):
        bioma = bioma_por_tile(tile)
        return {
            "AguaFunda": "Água",
            "AguaRasa": "Água",
            "Magico": "Mágico",
            "Pantano": "Pântano",
        }.get(bioma, bioma or "Vale")

    @staticmethod
    def _texto_confronto_bioma(tile):
        bioma = bioma_por_tile(tile)
        return {
            "Floresta": "Confronto na floresta",
            "Praia": "Confronto na praia",
            "Neve": "Confronto na neve",
            "Deserto": "Confronto no deserto",
            "Vale": "Confronto no vale",
            "Vulcão": "Confronto no vulcão",
            "Pantano": "Confronto no pântano",
            "Magico": "Confronto no bioma mágico",
            "AguaFunda": "Confronto na água",
            "AguaRasa": "Confronto na água",
        }.get(bioma, "Confronto selvagem")

    @staticmethod
    def _tipo_estadio_formatado(valor):
        texto = ControladorCenas._texto_limpo(valor)
        if not texto:
            return ""
        chave = texto.strip().lower().replace("_", " ").replace("-", " ")
        chave = " ".join(chave.split())
        return {
            "agua": "Água",
            "cosmico": "Cósmico",
            "dragao": "Dragão",
            "eletrico": "Elétrico",
            "fada": "Fada",
            "fantasma": "Fantasma",
            "fogo": "Fogo",
            "gelo": "Gelo",
            "inseto": "Inseto",
            "lutador": "Lutador",
            "metal": "Metal",
            "normal": "Normal",
            "pedra": "Pedra",
            "planta": "Planta",
            "psiquico": "Psíquico",
            "sombrio": "Sombrio",
            "sonoro": "Sonoro",
            "terrestre": "Terrestre",
            "terra": "Terrestre",
            "venenoso": "Venenoso",
            "voador": "Voador",
        }.get(chave, ControladorCenas._titulo_simples(texto))

    def _resolver_discord_menu(self):
        tela = str(getattr(self.Cena, "TelaAtual", "MenuPrincipal") or "MenuPrincipal")
        estados = {
            "MenuPrincipal": "Menu principal",
            "Servers": "Tela de servidores",
            "Config": "Configurações",
            "Operador": "Painel do operador",
        }
        return {
            "details": "No menu",
            "state": estados.get(tela, f"Tela {self._titulo_simples(tela) or 'do menu'}"),
            "local": "menu",
        }

    def _resolver_discord_dungeon(self, objetos):
        controlador = getattr(self.Cena, "ControladorMundo", None)
        leitor = getattr(controlador, "Leitor", None)
        meta = getattr(leitor, "MetaMundo", {}) if leitor is not None else {}
        layout_meta = meta.get("layout_dungeon") if isinstance(meta, dict) else {}
        layout_objetos = getattr(objetos, "LayoutDungeonAtual", {}) if objetos is not None else {}
        chaves_nome = ("nome", "nome_dungeon", "dungeon_nome", "titulo")
        chaves_id = ("id", "dungeon_id")
        layout_meta = layout_meta if isinstance(layout_meta, dict) else {}
        layout_objetos = layout_objetos if isinstance(layout_objetos, dict) else {}
        nome = (
            self._primeiro_valor_dict(layout_meta, chaves_nome)
            or self._primeiro_valor_dict(layout_objetos, chaves_nome)
        )
        if not nome:
            dungeon_id = self._texto_limpo(next((layout.get(chave) for layout in (layout_meta, layout_objetos) for chave in chaves_id if self._texto_limpo(layout.get(chave))), ""))
            if dungeon_id.isdigit():
                nome = f"#{dungeon_id}"
        return f"Explorando a dungeon {nome}" if nome else "Explorando uma dungeon"

    def _resolver_discord_estadio(self, objetos):
        player = getattr(getattr(self.Cena, "ControladorMundo", None), "player_local", None)
        id_player = 0
        if objetos is not None and callable(getattr(objetos, "id_player_local", None)):
            id_player = self._inteiro_seguro(objetos.id_player_local())
        if id_player <= 0:
            id_player = self._inteiro_seguro(getattr(player, "Id", 0))

        payload_player = objetos.ObjetosPorId.get(id_player, {}) if objetos is not None and isinstance(getattr(objetos, "ObjetosPorId", None), dict) else {}
        estado_player = payload_player.get("estado") if isinstance(payload_player.get("estado"), dict) else {}
        estadio_id = self._inteiro_seguro(estado_player.get("estadio_atual_id", payload_player.get("estadio_atual_id", 0)))
        estadio = objetos.EstadiosPorId.get(estadio_id, {}) if objetos is not None and isinstance(getattr(objetos, "EstadiosPorId", None), dict) else {}
        estado_estadio = estadio.get("estado") if isinstance(estadio.get("estado"), dict) else {}

        nome = (
            self._primeiro_valor_dict(estadio, ("nome", "nome_estadio"))
            or self._primeiro_valor_dict(estado_estadio, ("nome", "nome_estadio"))
        )
        if nome:
            return f"Explorando o estádio {nome}"

        tipo = (
            self._primeiro_valor_dict(estadio, ("tipo_estadio", "estadio_tipo", "tipo"))
            or self._primeiro_valor_dict(estado_estadio, ("tipo_estadio", "estadio_tipo", "tipo"))
        )
        tipo = self._tipo_estadio_formatado(tipo)
        return f"Explorando o estádio de {tipo}" if tipo else "Explorando um estádio"

    def _resolver_discord_mundo(self):
        dialogo = self.GerenciadorSubtelas.obter_por_tipo(SubtelaDialogo)
        nome_dialogo = self._nome_npc_dialogo(dialogo) if dialogo is not None else ""
        if nome_dialogo:
            return {"details": "Explorando mundo", "state": f"Conversando com {nome_dialogo}", "local": "mundo"}

        controlador = getattr(self.Cena, "ControladorMundo", None)
        objetos = getattr(controlador, "Objetos", None) if controlador is not None else None
        dimensao = str(objetos.dimensao_atual_client() or "Mundo") if objetos is not None and callable(getattr(objetos, "dimensao_atual_client", None)) else "Mundo"

        if dimensao.startswith("Dungeon_"):
            state = self._resolver_discord_dungeon(objetos)
        elif dimensao.startswith("Estadio"):
            state = self._resolver_discord_estadio(objetos)
        elif getattr(self.Cena, "TelaAtual", None) == "Config":
            state = "Configurações"
        elif getattr(self.Cena, "TelaAtual", None) == "Mapa":
            state = "Vendo o mapa"
        else:
            tile = tile_mundo_atual(self.Cena)
            state = f"Explorando o bioma {self._descricao_bioma(tile)}" if tile is not None else "Explorando o mundo"

        return {"details": "Explorando mundo", "state": state, "local": "mundo"}

    def _resolver_discord_combate(self):
        contexto = self.INFO.get("CombateContexto") if isinstance(self.INFO.get("CombateContexto"), dict) else {}
        tipo = str(contexto.get("tipo_batalha") or contexto.get("tipo") or "").strip().lower()
        npc = contexto.get("npc_contexto") if isinstance(contexto.get("npc_contexto"), dict) else {}

        if tipo in {"treinador", "trainer"} or npc:
            nome = (
                self._primeiro_valor_dict(npc, ("npc_nome", "nome", "Nome"))
                or self._primeiro_valor_dict(contexto, ("npc_nome", "nome_treinador", "treinador_nome"))
            )
            state = f"Lutando com {nome}" if nome else "Batalha contra treinador"
        elif tipo in {"boss", "servo"}:
            nome = self._nome_pokemon_payload(contexto.get("pokemon_colisao") if isinstance(contexto.get("pokemon_colisao"), dict) else {})
            if not nome:
                for pokemon in list(contexto.get("pokemons_inimigo") or []):
                    nome = self._nome_pokemon_payload(pokemon)
                    if nome:
                        break
            if tipo == "boss":
                state = f"Lutando com {nome}" if nome else "Batalha contra boss"
            else:
                state = f"Lutando com {nome}" if nome else "Confronto de dungeon"
        else:
            tile_bioma = contexto.get("tile_bioma")
            state = self._texto_confronto_bioma(tile_bioma) if tile_bioma not in (None, "") else "Confronto selvagem"

        return {"details": "Em combate", "state": state, "local": "combate"}

    def _resolver_discord_presenca(self):
        cena_id = str(getattr(self.Cena, "ID", "Menu") or "Menu")
        if cena_id == "Login":
            return {"details": "Fazendo login", "state": "Tela de login", "local": "login"}
        if cena_id == "Carregamento":
            return {"details": "Carregando", "state": "Preparando o jogo", "local": "carregamento"}
        if cena_id == "Menu":
            return self._resolver_discord_menu()
        if cena_id == "Mundo":
            return self._resolver_discord_mundo()
        if cena_id == "Combate":
            return self._resolver_discord_combate()
        return {"details": "No menu", "state": f"Tela {self._titulo_simples(cena_id) or 'do jogo'}", "local": "menu"}

    def _atualizar_discord_presenca(self):
        if self.Saindo or self.Cena is None:
            self.Discord.desconectar()
            return

        try:
            presenca = self._resolver_discord_presenca()
        except Exception:
            presenca = {"details": "No menu", "state": "Menu principal", "local": "menu"}
        self.Discord.atualizar(**presenca)

    def AplicarClaridadeGlobal(self, tela=None):
        bloquear = getattr(self.Cena, "bloquear_claridade_global", None)
        if callable(bloquear) and bool(bloquear()):
            return
        aplicar_claridade(self.TELA if tela is None else tela, self.CONFIG.get("Claridade", 75))

    def SolicitarSair(self):
        self.CenaAlvo = None
        self.Saindo = True
        self.Discord.desconectar()

    def Encerrar(self):
        if self._encerrado:
            return
        if self.Cena is not None:
            self.Cena.Finalizar(self)
        self.Discord.desconectar()
        self.PipelineGrafica.liberar()
        try:
            shutil.rmtree(Path("RAM") / "ImagensMapa", ignore_errors=True)
        except Exception:
            pass
        self._encerrado = True

    def DesenharInfosAdicionais(self, tela=None):
        if isinstance(getattr(self, "INFO", None), dict) and self.INFO.get("CreditosAtivos"):
            return
        destino = self.TELA if tela is None else tela
        largura_tela = destino.get_width()
        deslocamento_direita = 0
        cena_id = str(getattr(self.Cena, "ID", "") or "")
        somente_fps = cena_id == "Menu"
        if bool(self.CONFIG.get("MostrarMinimapa", False)) and cena_id == "Mundo":
            deslocamento_direita = 210
        itens_hud = []

        if self.CONFIG.get("FPS Visivel", False):
            self.TextoFPS.set_text(f"FPS: {int(self.RELOGIO.get_fps())}")
            itens_hud.append(self.TextoFPS)

        if not somente_fps and self.CONFIG.get("Ping Visivel", False):
            self.TextoPing.set_text("Ping: 5")
            itens_hud.append(self.TextoPing)

        if not somente_fps and self.CONFIG.get("Cords Visiveis", False):
            entidade_main = getattr(self.Cena, "EntidadeMain", None)
            if entidade_main is not None and hasattr(entidade_main, "Posicao"):
                x, y = entidade_main.Posicao
                self.TextoCoords.set_text(f"X {x:.2f} | Y {y:.2f}")
            else:
                self.TextoCoords.set_text("--")
            itens_hud.append(self.TextoCoords)

        if not somente_fps and self.CONFIG.get("MostrarHorario", False):
            if hasattr(self.Cena, "ControladorMundo") and getattr(self.Cena, "ControladorMundo", None) is not None:
                tempo = self.Cena.ControladorMundo.tempo_mundo_atual()
                if "dia" in tempo and "hora" in tempo and "minuto" in tempo:
                    dia = int(tempo.get("dia", 0) or 0)
                    hora = int(tempo.get("hora", 0) or 0)
                    minuto = int(tempo.get("minuto", 0) or 0)
                    self.TextoHorario.set_text(f"Dia {dia} | {hora:02d}:{minuto:02d}")
                else:
                    self.TextoHorario.set_text("Dia -- | --:--")
            else:
                self.TextoHorario.set_text("Dia -- | --:--")
            itens_hud.append(self.TextoHorario)

        y_base = 12
        espaco = 32
        for idx, texto in enumerate(itens_hud):
            texto.set_pos((largura_tela - 16 - deslocamento_direita, y_base + idx * espaco))
            texto.draw(destino)


    def DesenhosAdicionais(self):
        self.DesenharInfosAdicionais()
