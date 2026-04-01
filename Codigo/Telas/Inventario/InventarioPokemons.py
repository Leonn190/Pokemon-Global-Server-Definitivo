from __future__ import annotations

import math

import pygame

from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Paineis.Container import Container
from Codigo.Paineis.FichaPokemon import FichaPokemon
from Codigo.Paineis.PainelTimes import PainelTimes
from Codigo.Prefabs.Arrastavel import Arrastavel
from Codigo.Prefabs.BarraPesquisa import BarraPesquisa
from Codigo.Prefabs.Opcoes import Opções
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto
from Codigo.Telas.TelasGenericas import SubtelaConfirmacao, SubtelaTexto


class InventarioPokemons:
    def __init__(self, ator=None):
        self.Ator = ator
        self.Inventario = getattr(ator, 'Inventario', None)
        self.Perfil = getattr(ator, 'Perfil', None)

        self._container = None
        self._painel_times = None
        self._arrastavel = Arrastavel()
        self._pokemon_hover = None
        self._estava_ativo = False
        self._layout_montado = False

        self._area_grid = pygame.Rect(0, 0, 0, 0)
        self._area_ficha = pygame.Rect(0, 0, 0, 0)
        self._area_info = pygame.Rect(0, 0, 0, 0)
        self._area_times = pygame.Rect(0, 0, 0, 0)
        self._area_total = pygame.Rect(0, 0, 0, 0)

        estilo = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtResumo = Texto('', style={**estilo, 'size': 22, 'color': (239, 243, 255), 'align': 'midleft'})
        self.TxtHover = Texto('', style={**estilo, 'size': 15, 'color': (174, 190, 224), 'align': 'midright'})
        self._painel_info = Painel((0, 0, 0, 0), cor_fundo=(18, 26, 44, 242), cor_borda=(66, 88, 136), borda=2, raio=16)
        self._barra_pesquisa = None
        self._opcoes = Opções()
        self._subtela_ativa = None
        self._ficha_pokemon = FichaPokemon()
        self._pokemon_analisado = None

    def on_open(self):
        self._estava_ativo = True

    def on_close(self):
        self._arrastavel.cancelar()
        self._pokemon_hover = None
        self._pokemon_analisado = None
        self._opcoes.fechar()
        self._subtela_ativa = None
        if self._barra_pesquisa is not None:
            self._barra_pesquisa.resetar_filtro()
        self._estava_ativo = False

    def bloqueia_toggle_inventario(self):
        return (
            (self._barra_pesquisa is not None and self._barra_pesquisa.esta_editando())
            or self._subtela_ativa is not None
            or self._opcoes.Ativa
        )

    def _ler_limite(self, nomes, padrao):
        for origem in (self.Inventario, self.Perfil):
            if origem is None:
                continue
            for nome in nomes:
                valor = getattr(origem, nome, None)
                if valor is None:
                    continue
                try:
                    return max(1, int(valor))
                except (TypeError, ValueError):
                    continue
        return padrao

    def _lista_pokemons(self):
        if self.Inventario is None:
            return []
        for nome in ('Pokemons', 'ListaPokemons', 'InventarioPokemons', 'CaixaPokemons'):
            valor = getattr(self.Inventario, nome, None)
            if isinstance(valor, list):
                return valor
        lista = []
        setattr(self.Inventario, 'Pokemons', lista)
        return lista

    def _times_pokemons(self):
        if self.Inventario is None:
            return []
        for nome in ('TimesPokemons', 'TimesPokemon', 'EquipesPokemons', 'EquipesPokemon'):
            valor = getattr(self.Inventario, nome, None)
            if isinstance(valor, list):
                return valor
        times = []
        setattr(self.Inventario, 'TimesPokemons', times)
        return times

    def _limite_slots(self):
        base = self._ler_limite(('LimitePokemons', 'LimiteSlotsPokemons', 'SlotsPokemons', 'CapacidadePokemons'), 64)
        return max(base, len(self._lista_pokemons()))

    def _quantidade_times(self):
        base = self._ler_limite(('LimiteTimesPokemon', 'LimiteTimesPokemons', 'TimesPokemonsLiberados', 'SlotsTimesPokemons'), 6)
        return max(base, len(self._times_pokemons()))

    def _slots_por_time(self):
        return 6

    def _linhas_grid_totais(self):
        return max(1, math.ceil(self._limite_slots() / 8))

    def _linhas_grid_visiveis(self):
        return min(8, self._linhas_grid_totais())

    def _slot_px_grid(self, area_grid):
        colunas = 8
        gap = 10
        padding = 18
        max_por_largura = (area_grid.width - padding * 2 - gap * (colunas - 1)) // colunas
        return max(42, min(70, int(max_por_largura)))

    def _reconstruir(self, area):
        self._area_total = pygame.Rect(area)
        margem = 14
        topo = 10
        largura_esquerda = min(int(area.width * 0.64), 760)
        largura_direita = area.width - largura_esquerda - margem * 3

        area_esquerda = pygame.Rect(area.x + margem, area.y + topo, largura_esquerda, area.height - 112)
        self._area_ficha = pygame.Rect(0, 0, 0, 0)
        self._area_grid = pygame.Rect(area_esquerda)
        if self._pokemon_analisado is not None:
            gap_ficha = 12
            largura_ficha = int(max(340, min(530, area_esquerda.width * 0.46)))
            largura_grid = area_esquerda.width - largura_ficha - gap_ficha
            if largura_grid >= 250:
                self._area_ficha = pygame.Rect(area_esquerda.x, area_esquerda.y, largura_ficha, area_esquerda.height)
                self._area_grid = pygame.Rect(self._area_ficha.right + gap_ficha, area_esquerda.y, largura_grid, area_esquerda.height)
        self._area_info = pygame.Rect(area.x + margem, self._area_grid.bottom + 14, largura_esquerda, 72)
        self._area_times = pygame.Rect(self._area_grid.right + margem, area.y + topo, largura_direita, area.height - 20)
        self._area_ficha = pygame.Rect(self._area_grid.x, self._area_grid.y, self._area_grid.width, self._area_info.bottom - self._area_grid.y)

        pokemons = self._lista_pokemons()
        times = self._times_pokemons()
        slot_px = self._slot_px_grid(self._area_grid)

        if self._container is None:
            self._container = Container(
                self._area_grid,
                pokemons,
                slots_total=self._limite_slots(),
                colunas=8,
                linhas_visiveis=self._linhas_grid_visiveis(),
                slot_px=slot_px,
                gap=10,
                cor_fundo=(18, 26, 44, 242),
                cor_borda=(66, 88, 136),
                borda=2,
                raio=16,
                stackable=False,
                renderizador_item=PokemonInventario,
            )
            self._barra_pesquisa = BarraPesquisa(pygame.Rect(0, 0, 10, 10), placeholder='Buscar pokémon...')
            self._barra_pesquisa.definir_acessor_nome(PokemonInventario.nome_pokemon)
            self._barra_pesquisa.definir_ordenacoes([
                ('Alfabética', PokemonInventario.nome_pokemon),
                ('Poder', lambda p: -PokemonInventario.poder_total(p)),
                ('Tipo', PokemonInventario.tipo_principal),
            ])
            self._container.configurar_barra_pesquisa(self._barra_pesquisa)
        else:
            self._container.Itens = pokemons
            self._container.SlotsTotal = self._limite_slots()
            self._container.SlotPx = slot_px
            self._container.Gap = 10
            self._container.Colunas = 8
            self._container.LinhasVisiveis = self._linhas_grid_visiveis()
            self._container.RenderizadorItem = PokemonInventario
            self._container.configurar_rect(self._area_grid)
            self._container.configurar_barra_pesquisa(self._barra_pesquisa)

        if self._painel_times is None:
            self._painel_times = PainelTimes(self._area_times, times, slots_por_time=self._slots_por_time())
        else:
            self._painel_times.definir_times(times)
            self._painel_times.definir_slots_por_time(self._slots_por_time())
            self._painel_times.configurar_rect(self._area_times)

        self._painel_times.garantir_minimo_times(self._quantidade_times())
        self._painel_info.rect = pygame.Rect(self._area_info)
        self._layout_montado = True

    def _alvo_no_mouse(self, mouse_pos):
        alvo_time = self._painel_times.alvo_no_mouse(mouse_pos) if self._painel_times is not None else None
        if alvo_time is not None:
            return alvo_time
        indice = self._container.indice_no_mouse(mouse_pos) if self._container is not None else None
        if indice is not None:
            return ('grid', indice)
        return None

    def _pokemon_do_alvo(self, alvo):
        if alvo is None:
            return None
        if alvo[0] == 'grid':
            return self._container.item_por_slot_visual(alvo[1])
        if alvo[0] == 'time':
            return self._painel_times.pokemon_no_slot(alvo[1], alvo[2])
        return None

    def _nome_pokemon(self, pokemon):
        if pokemon is None:
            return ''
        nome = PokemonInventario.nome_pokemon(pokemon)
        nivel = PokemonInventario.nivel_pokemon(pokemon)
        if nivel not in (None, ''):
            return f'{nome}  •  Lv {nivel}'
        return nome

    def _chave(self, pokemon):
        return PokemonInventario.chave_pokemon(pokemon) if pokemon is not None else None

    def _abrir_renomear_time(self, indice_time):
        nome_atual = self._painel_times.nome_time(indice_time)

        def _confirmar(novo_nome):
            novo = str(novo_nome or '').strip()
            if not novo:
                return False
            self._painel_times.Times[indice_time]['Nome'] = novo
            self._painel_times.marcar_sujo()
            return True

        self._subtela_ativa = SubtelaTexto(
            pygame.display.get_surface().get_size(),
            'Renomear time',
            nome_atual,
            enviar_callback=_confirmar,
            placeholders='Nome do time...',
            max_chars=24,
        )

    def _abrir_confirmacao_doacao(self, pokemon, remover_time=None):
        nome = self._nome_pokemon(pokemon) or 'este pokémon'

        def _confirmar():
            self._doar_pokemon(pokemon)

        self._subtela_ativa = SubtelaConfirmacao(
            pygame.display.get_surface().get_size(),
            f'Tem certeza que deseja doar {nome}?',
            confirmar_callback=_confirmar,
            titulo='Confirmar doação',
        )

    def _doar_pokemon(self, pokemon):
        if pokemon is None or self._container is None:
            return
        chave = self._chave(pokemon)
        for i in range(len(self._container.Itens)):
            atual = self._container.Itens[i]
            if atual is not None and self._chave(atual) == chave:
                self._container.Itens[i] = None
                break
        for i in range(len(self._painel_times.Times)):
            slots = self._painel_times.slots_time(i)
            for j, atual in enumerate(slots):
                if atual is not None and self._chave(atual) == chave:
                    slots[j] = None
        if self._pokemon_analisado is not None and self._chave(self._pokemon_analisado) == chave:
            self._pokemon_analisado = None
            self._layout_montado = False
        self._container.marcar_sujo()
        self._painel_times.marcar_sujo()

    def _abrir_opcoes_time(self, pos, indice_time):
        def _limpar_time():
            slots = self._painel_times.slots_time(indice_time)
            for i in range(len(slots)):
                slots[i] = None
            self._painel_times.marcar_sujo()

        self._opcoes.abrir(
            pos,
            [
                {'texto': 'Limpar', 'acao': _limpar_time},
                {'texto': 'Renomear', 'acao': lambda: self._abrir_renomear_time(indice_time)},
            ],
            tela_rect=pygame.display.get_surface().get_rect(),
        )

    def _abrir_opcoes_pokemon(self, pos, pokemon, alvo_time=None):
        if pokemon is None:
            return
        opcoes = [
            {'texto': 'Analisar', 'acao': lambda p=pokemon: self._abrir_analise_pokemon(p)},
            {'texto': 'Doar', 'acao': lambda: self._abrir_confirmacao_doacao(pokemon)},
        ]
        if alvo_time is not None:
            opcoes.append({'texto': 'Remover', 'acao': lambda: self._painel_times.retirar_do_slot(alvo_time[0], alvo_time[1])})
        self._opcoes.abrir(pos, opcoes, tela_rect=pygame.display.get_surface().get_rect())

    def _abrir_analise_pokemon(self, pokemon):
        self._pokemon_analisado = pokemon
        self._opcoes.fechar()
        self._layout_montado = False

    def _processar_atalho_enter_pesquisa(self, eventos):
        if self._barra_pesquisa is None or self._subtela_ativa is not None or self._opcoes.Ativa:
            return
        for evento in eventos:
            if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._barra_pesquisa.selecionada = not self._barra_pesquisa.selecionada
                break

    def _iniciar_arrasto(self, alvo, mouse_pos):
        pokemon = self._pokemon_do_alvo(alvo)
        if pokemon is None:
            return

        if alvo[0] == 'grid':
            indice_real = self._container.indice_real_por_visual(alvo[1], exigir_item=True)
            if indice_real is None:
                return
            rect_base = self._container.slot_rect(alvo[1])
            self._arrastavel.iniciar(
                pokemon,
                ('grid', alvo[1], indice_real),
                self._container.item_rect_no_slot(rect_base),
                mouse_pos,
                botao=1,
            )
        else:
            indice_time, indice_slot = alvo[1], alvo[2]
            rect_base = self._painel_times.slot_rect(indice_time, indice_slot)
            pokemon_retirado = self._painel_times.retirar_do_slot(indice_time, indice_slot)
            if pokemon_retirado is None:
                return
            self._arrastavel.iniciar(
                pokemon_retirado,
                ('time', indice_time, indice_slot),
                pygame.Rect(rect_base.x + 5, rect_base.y + 5, rect_base.width - 10, rect_base.height - 10),
                mouse_pos,
                botao=1,
            )
        self._pokemon_hover = pokemon

    def _retornar_para_origem(self):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return
        origem = self._arrastavel.Origem or ()
        if origem and origem[0] == 'time':
            rect = self._painel_times.slot_rect(origem[1], origem[2])
            alvo = pygame.Rect(rect.x + 5, rect.y + 5, rect.width - 10, rect.height - 10)
            def _finalizar():
                self._painel_times.definir_slot(origem[1], origem[2], self._arrastavel.Item)
                self._arrastavel.cancelar()
            self._arrastavel.definir_pos_alvo(alvo.topleft, ao_final=_finalizar)
            return
        if origem and origem[0] == 'grid':
            rect = self._container.slot_rect(origem[1])
            self._arrastavel.definir_pos_alvo(self._container.item_rect_no_slot(rect).topleft, ao_final=self._arrastavel.cancelar)
            return
        self._arrastavel.cancelar()

    def _soltar_no_alvo(self, alvo):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None or alvo is None:
            return

        origem = self._arrastavel.Origem or ()
        pokemon_arrastado = self._arrastavel.Item

        if origem[0] == 'grid':
            indice_origem = origem[2]
            if alvo[0] == 'grid':
                if not self._container.permite_interacao_por_slot():
                    self._retornar_para_origem()
                    return
                indice_destino = self._container.indice_real_por_visual(alvo[1], exigir_item=False)
                if indice_destino is None:
                    self._retornar_para_origem()
                    return
                if indice_destino != indice_origem:
                    itens = self._container.Itens
                    itens[indice_origem], itens[indice_destino] = itens[indice_destino], itens[indice_origem]
                self._arrastavel.cancelar()
                return

            if alvo[0] == 'time':
                self._painel_times.definir_slot(alvo[1], alvo[2], pokemon_arrastado, limpar_duplicados=True)
                self._arrastavel.cancelar()
                return

        if origem[0] == 'time':
            indice_time_origem, indice_slot_origem = origem[1], origem[2]

            if alvo[0] == 'time':
                indice_time_destino, indice_slot_destino = alvo[1], alvo[2]
                pokemon_destino = self._painel_times.pokemon_no_slot(indice_time_destino, indice_slot_destino)
                self._painel_times.definir_slot(indice_time_destino, indice_slot_destino, pokemon_arrastado, limpar_duplicados=True)
                if indice_time_origem == indice_time_destino and indice_slot_origem == indice_slot_destino:
                    self._painel_times.definir_slot(indice_time_destino, indice_slot_destino, pokemon_arrastado, limpar_duplicados=True)
                else:
                    self._painel_times.definir_slot(indice_time_origem, indice_slot_origem, pokemon_destino)
                self._arrastavel.cancelar()
                return

            if alvo[0] == 'grid':
                if not self._container.permite_interacao_por_slot():
                    self._retornar_para_origem()
                    return
                pokemon_grid = self._pokemon_do_alvo(alvo)
                if pokemon_grid is not None and self._chave(pokemon_grid) != self._chave(pokemon_arrastado):
                    self._painel_times.definir_slot(indice_time_origem, indice_slot_origem, pokemon_grid, limpar_duplicados=True)
                self._arrastavel.cancelar()
                return

    def atualizar(self, eventos, dt, area, ativo=True):
        if self.Inventario is None and self.Ator is not None:
            self.Inventario = getattr(self.Ator, 'Inventario', None)
            self.Perfil = getattr(self.Ator, 'Perfil', None)

        if not self._layout_montado:
            self._reconstruir(area)
        if not ativo:
            if self._estava_ativo:
                self.on_close()
            return
        if not self._estava_ativo:
            self.on_open()

        self._reconstruir(area)
        if self._subtela_ativa is not None:
            if getattr(self._subtela_ativa, 'encerrada', False):
                self._subtela_ativa = None
            else:
                return

        analisando = self._pokemon_analisado is not None
        if not analisando:
            self._container._normalizar_tamanho()
            self._container._processar_scroll(eventos)
        self._painel_times._processar_scroll(eventos)
        self._arrastavel.animar(dt)
        self._opcoes.processar_eventos(eventos)
        if not analisando:
            self._processar_atalho_enter_pesquisa(eventos)

        if self._opcoes.Ativa:
            self._pokemon_hover = None
            return

        if not analisando:
            mouse = pygame.mouse.get_pos()
            alvo_mouse = self._alvo_no_mouse(mouse)
            self._pokemon_hover = self._pokemon_do_alvo(alvo_mouse)
            if self._arrastavel.Ativo and self._arrastavel.Item is not None:
                self._pokemon_hover = self._arrastavel.Item
        else:
            self._pokemon_hover = self._pokemon_analisado

        for evento in eventos:
            if evento.type == pygame.MOUSEMOTION and self._arrastavel.Ativo and self._arrastavel.PosAlvo is None:
                self._arrastavel.atualizar(evento.pos)

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self._area_ficha.collidepoint(evento.pos):
                    continue
                if analisando:
                    continue
                alvo = self._alvo_no_mouse(evento.pos)
                if self._arrastavel.Ativo:
                    if self._arrastavel.PosAlvo is not None:
                        continue
                    if alvo is None:
                        self._retornar_para_origem()
                    else:
                        self._soltar_no_alvo(alvo)
                    continue

                if alvo is not None and self._pokemon_do_alvo(alvo) is not None:
                    self._iniciar_arrasto(alvo, evento.pos)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 3:
                if self._area_ficha.collidepoint(evento.pos):
                    continue
                if analisando:
                    continue
                alvo_ctx = self._painel_times.alvo_contexto_no_mouse(evento.pos) if self._painel_times is not None else None
                if alvo_ctx is not None:
                    if alvo_ctx[0] == 'time_card':
                        self._abrir_opcoes_time(evento.pos, alvo_ctx[1])
                    elif alvo_ctx[0] == 'time_slot':
                        pokemon_time = self._painel_times.pokemon_no_slot(alvo_ctx[1], alvo_ctx[2])
                        if pokemon_time is not None:
                            self._abrir_opcoes_pokemon(evento.pos, pokemon_time, alvo_time=(alvo_ctx[1], alvo_ctx[2]))
                        else:
                            self._abrir_opcoes_time(evento.pos, alvo_ctx[1])
                    continue

                alvo = self._alvo_no_mouse(evento.pos)
                if alvo is not None and alvo[0] == 'grid':
                    pokemon = self._pokemon_do_alvo(alvo)
                    if pokemon is not None:
                        self._abrir_opcoes_pokemon(evento.pos, pokemon)

    def renderizar(self, tela, area, eventos, dt, ativo=True):
        self.atualizar(eventos, dt, area, ativo=ativo)
        if not ativo:
            return

        highlight = None if (self._subtela_ativa is not None or self._opcoes.Ativa) else self._alvo_no_mouse(pygame.mouse.get_pos())
        item_oculto_grid = None
        item_oculto_time = None
        if self._arrastavel.Ativo and self._arrastavel.Origem:
            if self._arrastavel.Origem[0] == 'grid':
                item_oculto_grid = self._arrastavel.Origem[1]
            elif self._arrastavel.Origem[0] == 'time':
                item_oculto_time = (self._arrastavel.Origem[1], self._arrastavel.Origem[2])

        analisando = self._pokemon_analisado is not None
        if analisando and self._area_ficha.width > 0:
            self._ficha_pokemon.renderizar(tela, self._area_ficha, self._pokemon_analisado, eventos=eventos, dt=dt)
            if self._ficha_pokemon.FecharSolicitado:
                self._pokemon_analisado = None
                self._layout_montado = False

        if not analisando:
            self._container.desenhar(
                tela,
                item_oculto=item_oculto_grid,
                highlight=highlight[1] if highlight and highlight[0] == 'grid' else None,
                eventos=eventos,
                dt=dt,
            )
        self._painel_times.desenhar(
            tela,
            highlight=highlight if highlight and highlight[0] == 'time' else None,
            item_oculto=item_oculto_time,
        )

        if not analisando:
            self._painel_info.render(tela, [], 0)
            ocupados = sum(1 for pokemon in self._container.Itens if pokemon is not None)
            self.TxtResumo.set_text(f'{ocupados} / {self._limite_slots()} pokémons')
            self.TxtResumo.set_pos((self._area_info.x + 18, self._area_info.centery))
            self.TxtResumo.draw(tela)

            self.TxtHover.set_text(self._nome_pokemon(self._pokemon_hover) or 'Arraste pokémons para montar seus times')
            self.TxtHover.set_pos((self._area_info.right - 18, self._area_info.centery))
            self.TxtHover.draw(tela)

            if self._arrastavel.Ativo and self._arrastavel.Item is not None:
                rect_drag = self._arrastavel.Rect.inflate(int(self._arrastavel.Rect.width * 0.1), int(self._arrastavel.Rect.height * 0.1))
                PokemonInventario.desenhar_item_no_rect(tela, self._arrastavel.Item, rect_drag, escala_sprite=0.86)
        self._opcoes.render(tela, eventos, dt)
        if self._subtela_ativa is not None:
            self._subtela_ativa.render(tela, eventos, dt)
