from __future__ import annotations

import copy
import importlib
import math

import pygame

from Codigo.ModulosGerais.LoaderTabelas import carregar_csv_dict

from Codigo.Geradores.PokemonInventario import PokemonInventario
from Codigo.Geradores.ItemInventario import ItemInventario
from Codigo.Geradores.Doce import Doce
from Codigo.ModulosGerais.Sonoridades import tocar
from Codigo.Paineis.Container import Container
from Codigo.Paineis.PainelAuxiliarPoke import PainelAuxiliarPoke
from Codigo.Paineis.FichaPokemon import FichaPokemon
from Codigo.Paineis.PainelTimes import PainelTimes
from Codigo.Prefabs.Arrastavel import Arrastavel
from Codigo.Prefabs.BarraPesquisa import BarraPesquisa
from Codigo.Prefabs.Botao import BotaoAlavanca
from Codigo.Prefabs.Opcoes import Opções
from Codigo.Prefabs.Painel import Painel
from Codigo.Prefabs.Texto import Texto
from Codigo.Telas.Telas.TelasGenericas import SubtelaConfirmacao, SubtelaTexto

_EXEC_POCAO = importlib.import_module("Codigo.ModulosMundo.ExecutaveisPoção")


class InventarioPokemons:
    def __init__(self, ator=None, abrir_modal=None, possui_modal=None):
        self.Ator = ator
        self.Inventario = getattr(ator, 'Inventario', None)
        self.Perfil = getattr(ator, 'Perfil', None)

        self._container = None
        self._painel_times = None
        self._arrastavel = Arrastavel()
        self._pokemon_hover = None
        self._estava_ativo = False
        self._layout_montado = False
        self._ultima_chave_layout = None

        self._area_grid = pygame.Rect(0, 0, 0, 0)
        self._area_ficha = pygame.Rect(0, 0, 0, 0)
        self._area_info = pygame.Rect(0, 0, 0, 0)
        self._area_abas = pygame.Rect(0, 0, 0, 0)
        self._area_times = pygame.Rect(0, 0, 0, 0)
        self._area_total = pygame.Rect(0, 0, 0, 0)

        estilo = {'outline': True, 'outline_thickness': 2, 'outline_color': (8, 12, 20)}
        self.TxtResumo = Texto('', style={**estilo, 'size': 22, 'color': (239, 243, 255), 'align': 'midleft'})
        self.TxtHover = Texto('', style={**estilo, 'size': 15, 'color': (174, 190, 224), 'align': 'midleft'})
        self._painel_info = Painel((0, 0, 0, 0), cor_fundo=(18, 26, 44, 242), cor_borda=(66, 88, 136), borda=2, raio=16)
        self._barra_pesquisa = None
        self._botao_toggle_poder = None
        self._mostrar_poder_slots = False
        self._opcoes = Opções()
        self._abrir_modal = abrir_modal
        self._possui_modal = possui_modal
        self._ficha_pokemon = FichaPokemon()
        self._pokemon_analisado = None
        self._painel_auxiliar = None
        self._csv_itens = None
        self._csv_equipaveis = None

    def on_open(self):
        PokemonInventario.definir_mostrar_poder_slots(self._mostrar_poder_slots)
        self._estava_ativo = True

    def on_close(self):
        self._arrastavel.cancelar()
        self._pokemon_hover = None
        self._pokemon_analisado = None
        self._opcoes.fechar()
        if self._barra_pesquisa is not None:
            self._barra_pesquisa.resetar_filtro()
        PokemonInventario.definir_mostrar_poder_slots(False)
        self._mostrar_poder_slots = False
        self._estava_ativo = False

    def bloqueia_toggle_inventario(self):
        return (
            (self._barra_pesquisa is not None and self._barra_pesquisa.esta_editando())
            or (callable(self._possui_modal) and self._possui_modal())
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

    def _painel_times_ativo(self, analisando=None):
        if analisando is None:
            analisando = self._pokemon_analisado is not None
        if not analisando:
            return True
        return self._painel_auxiliar is not None and self._painel_auxiliar.aba_ativa == 'times'

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

        analisando = self._pokemon_analisado is not None
        altura_esquerda = area.height - (20 if analisando else 112)
        area_esquerda = pygame.Rect(area.x + margem, area.y + topo, largura_esquerda, altura_esquerda)
        self._area_grid = pygame.Rect(area_esquerda)
        if analisando:
            self._area_ficha = pygame.Rect(area_esquerda)
            self._area_info = pygame.Rect(0, 0, 0, 0)
        else:
            self._area_ficha = pygame.Rect(0, 0, 0, 0)
            self._area_info = pygame.Rect(area.x + margem, self._area_grid.bottom + 14, largura_esquerda, 72)
        if analisando:
            lateral_x = self._area_ficha.right + margem
            altura_abas = 34
            gap_abas_conteudo = 8
            self._area_abas = pygame.Rect(lateral_x, self._area_ficha.y, largura_direita, altura_abas)
            conteudo_y = self._area_abas.bottom + gap_abas_conteudo
            conteudo_h = max(60, self._area_ficha.bottom - conteudo_y)
            self._area_times = pygame.Rect(lateral_x, conteudo_y, largura_direita, conteudo_h)
        else:
            self._area_abas = pygame.Rect(0, 0, 0, 0)
            self._area_times = pygame.Rect(self._area_grid.right + margem, area.y + topo, largura_direita, area.height - 20)

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
                ('Favoritos', None, self._favoritos_primeiro),
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

        def _toggle_poder(_jogo, ativo, _botao):
            self._mostrar_poder_slots = bool(ativo)
            PokemonInventario.definir_mostrar_poder_slots(self._mostrar_poder_slots)
            self._sincronizar_visual_toggle_poder()
            if self._container is not None:
                self._container.marcar_sujo()
            if self._painel_times is not None:
                self._painel_times.marcar_sujo()

        botao_lado = 30
        botao_x = self._area_grid.right - 10 - botao_lado
        botao_y = self._area_grid.y + 17
        if self._botao_toggle_poder is None:
            self._botao_toggle_poder = BotaoAlavanca(
                pygame.Rect(botao_x, botao_y, botao_lado, botao_lado),
                nome='P',
                estado_inicial=self._mostrar_poder_slots,
                execute=_toggle_poder,
                style={
                    'radius': 999,
                    'border_width': 2,
                    'hover_scale': 1.02,
                    'press_scale': 0.98,
                    'text_style': {'size': 16, 'outline': True, 'shadow': False},
                },
            )
        else:
            self._botao_toggle_poder.base_rect = pygame.Rect(botao_x, botao_y, botao_lado, botao_lado)
            self._botao_toggle_poder.rect = pygame.Rect(self._botao_toggle_poder.base_rect)
            self._botao_toggle_poder.set_execute(_toggle_poder)
            self._botao_toggle_poder.set_estado(self._mostrar_poder_slots)
        self._sincronizar_visual_toggle_poder()

        if self._painel_auxiliar is None:
            self._painel_auxiliar = PainelAuxiliarPoke(self._area_times)
            self._painel_auxiliar.configurar_rects(self._area_abas, self._area_times)
        else:
            self._painel_auxiliar.configurar_rects(self._area_abas, self._area_times)
        self._painel_auxiliar.definir_pokemon_analisado(self._pokemon_analisado)

        if self._painel_times is None:
            self._painel_times = PainelTimes(self._area_times, times, slots_por_time=self._slots_por_time())
        else:
            self._painel_times.definir_times(times)
            self._painel_times.definir_slots_por_time(self._slots_por_time())
            self._painel_times.configurar_rect(self._area_times)
        if self._painel_times_ativo(analisando):
            self._painel_times.garantir_minimo_times(self._quantidade_times())
        self._painel_info.rect = pygame.Rect(self._area_info)
        self._layout_montado = True

    def _chave_layout(self, area):
        area = pygame.Rect(area)
        return (
            area.x, area.y, area.width, area.height,
            bool(self._pokemon_analisado is not None),
            self._limite_slots(),
            self._linhas_grid_visiveis(),
            self._quantidade_times(),
            len(self._lista_pokemons()),
            len(self._times_pokemons()),
        )

    def _alvo_no_mouse(self, mouse_pos):
        if self._botao_toggle_poder is not None and self._botao_toggle_poder.rect.collidepoint(mouse_pos):
            return None
        analisando = self._pokemon_analisado is not None
        if analisando and not self._painel_times_ativo(analisando):
            return self._painel_auxiliar.alvo_no_mouse(mouse_pos) if self._painel_auxiliar is not None else None
        alvo_time = self._painel_times.alvo_no_mouse(mouse_pos) if self._painel_times is not None and self._painel_times_ativo(analisando) else None
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
        if alvo[0] == 'aux' and alvo[1] == 'pokemons':
            return self._painel_auxiliar.item_por_visual(alvo[2]) if self._painel_auxiliar is not None else None
        return None

    def _nome_pokemon(self, pokemon):
        if pokemon is None:
            return ''
        nome = PokemonInventario.nome_pokemon(pokemon)
        especie = str(pokemon.get('Especie') or pokemon.get('especie') or nome) if isinstance(pokemon, dict) else nome
        nivel = PokemonInventario.nivel_pokemon(pokemon)
        poder = int(round(PokemonInventario.poder_total(pokemon)))
        if nivel in (None, ''):
            return f'Nome: {nome} | {especie} | Poder {poder}'
        return f'Nome: {nome} | {especie} Lv {nivel} | Poder {poder}'

    def _base_itens(self):
        if self._csv_itens is not None:
            return self._csv_itens
        self._csv_itens = {}
        try:
            linhas = carregar_csv_dict('Pokemon Global Server - Itens.csv')
        except OSError:
            return self._csv_itens
        for linha in linhas:
                nome = str(linha.get('Nome') or '').strip().lower()
                code = str(linha.get('Code') or '').strip()
                if nome:
                    self._csv_itens[('nome', nome)] = dict(linha)
                if code:
                    self._csv_itens[('code', code)] = dict(linha)
        return self._csv_itens

    def _base_equipaveis(self):
        if self._csv_equipaveis is not None:
            return self._csv_equipaveis
        self._csv_equipaveis = {}
        try:
            linhas = carregar_csv_dict('Pokemon Global Server - Equipaveis.csv')
        except OSError:
            return self._csv_equipaveis
        for linha in linhas:
                nome = str(linha.get('Nome') or '').strip().lower()
                if nome:
                    self._csv_equipaveis[nome] = dict(linha)
        return self._csv_equipaveis

    def _info_item(self, item):
        if not isinstance(item, dict):
            return None
        base = self._base_itens()
        nome = str(item.get('Nome') or item.get('nome') or '').strip().lower()
        code = str(item.get('Code') or item.get('code') or '').strip()
        return base.get(('code', code)) or base.get(('nome', nome))

    def _estilo_item(self, item):
        info = self._info_item(item)
        return str((info or item).get('Estilo') or (info or item).get('estilo') or '').strip().lower()

    def _equipavel_para_build(self, item):
        if self._estilo_item(item) != 'equipavel':
            return None
        nome = str(item.get('Nome') or item.get('nome') or '').strip().lower()
        registro = self._base_equipaveis().get(nome)
        if registro is None:
            return None
        saida = dict(registro)
        saida['Nome'] = str(registro.get('Nome') or item.get('Nome') or '').strip()
        return saida

    def _build_para_item(self, equipavel):
        if not isinstance(equipavel, dict):
            return None
        nome = str(equipavel.get('Nome') or '').strip().lower()
        registro = self._base_itens().get(('nome', nome))
        return dict(registro) if registro is not None else None

    def _desenhar_tipos_hover(self, tela, pokemon):
        tipos = PokemonInventario.tipos_pokemon(pokemon)
        if not tipos:
            return
        lado = 26
        gap = 6
        x = self._area_info.right - 18 - (len(tipos) * (lado + gap))
        y = self._area_info.centery - (lado // 2)
        for tipo in tipos:
            fundo = pygame.Rect(x, y, lado, lado)
            icone = PokemonInventario.icone_tipo(tipo, lado + 1)
            if icone is not None:
                tela.blit(icone, icone.get_rect(center=fundo.center))
            x += lado + gap

    def _favoritos_primeiro(self):
        if self._barra_pesquisa is None or self._container is None:
            return
        prefixo = max(0, min(getattr(self._barra_pesquisa, '_indices_fixos_imutaveis', 0), len(self._container.Itens)))
        itens = self._container.Itens
        base = [item for item in itens[prefixo:] if item is not None]
        favoritos = [item for item in base if PokemonInventario.favorito(item)]
        comuns = [item for item in base if not PokemonInventario.favorito(item)]
        for i, item in enumerate(favoritos + comuns, start=prefixo):
            itens[i] = item
        for i in range(prefixo + len(base), len(itens)):
            itens[i] = None
        self._barra_pesquisa._projecao_suja = True
        self._barra_pesquisa._mudou_entrada = True
        self._container.marcar_sujo()

    def _chave(self, pokemon):
        return PokemonInventario.chave_pokemon(pokemon) if pokemon is not None else None

    def _sincronizar_pokemon_analisado(self):
        if self._pokemon_analisado is None:
            return
        chave = self._chave(self._pokemon_analisado)
        if chave is None:
            return
        for pokemon in self._lista_pokemons():
            if pokemon is not None and self._chave(pokemon) == chave:
                self._pokemon_analisado = pokemon
                return

    def _abrir_renomear_time(self, indice_time):
        nome_atual = self._painel_times.nome_time(indice_time)

        def _confirmar(novo_nome):
            novo = str(novo_nome or '').strip()
            if not novo:
                return False
            self._painel_times.Times[indice_time]['Nome'] = novo
            self._painel_times.marcar_sujo()
            tocar("Salvou")
            return True

        if callable(self._abrir_modal):
            self._abrir_modal(SubtelaTexto(
            pygame.display.get_surface().get_size(),
            'Renomear time',
            nome_atual,
            enviar_callback=_confirmar,
            placeholders='Nome do time...',
            max_chars=24,
            ))

    def _abrir_confirmacao_doacao(self, pokemon, remover_time=None):
        nome = PokemonInventario.nome_pokemon(pokemon) or 'este pokémon'

        def _confirmar():
            self._doar_pokemon(pokemon)

        if callable(self._abrir_modal):
            self._abrir_modal(SubtelaConfirmacao(
            pygame.display.get_surface().get_size(),
            f'Tem certeza que deseja doar o "{nome}"?',
            confirmar_callback=_confirmar,
            titulo='Confirmar doação',
            ))

    def _abrir_renomear_pokemon(self, pokemon):
        if not isinstance(pokemon, dict):
            return
        atual = str(pokemon.get('Nome') or pokemon.get('nome') or pokemon.get('Especie') or pokemon.get('especie') or '').strip()
        if not atual:
            atual = PokemonInventario.nome_pokemon(pokemon)

        def _confirmar(novo_nome):
            novo = str(novo_nome or '').strip()
            if not novo:
                return False
            pokemon['Nome'] = novo
            pokemon['nome'] = novo
            if self._container is not None:
                self._container.marcar_sujo()
            if self._painel_times is not None:
                self._painel_times.marcar_sujo()
            tocar("Salvou")
            return True

        if callable(self._abrir_modal):
            self._abrir_modal(SubtelaTexto(
            pygame.display.get_surface().get_size(),
            'Renomear pokémon',
            atual,
            enviar_callback=_confirmar,
            placeholders='Novo nome...',
            max_chars=24,
            ))

    def _evoluir_pokemon_analisado(self):
        pokemon = self._pokemon_analisado
        if not isinstance(pokemon, dict):
            return
        fonte = pokemon.get('estado') if isinstance(pokemon.get('estado'), dict) else pokemon
        if not bool(fonte.get('PodeEvoluir', fonte.get('pode_evoluir', False))):
            return
        controle = getattr(self.Ator, 'Controle', None)
        chave = self._chave(pokemon)
        if controle is not None and hasattr(controle, 'solicitar_evoluir_pokemon'):
            controle.solicitar_evoluir_pokemon(chave)
        if self._container is not None:
            self._container.marcar_sujo()
        if self._painel_times is not None:
            self._painel_times.marcar_sujo()

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
        tocar("Apagou")

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
        favorito = bool(pokemon.get('favorito', False)) if isinstance(pokemon, dict) else False

        def _toggle_favorito(p=pokemon):
            if not isinstance(p, dict):
                return
            p['favorito'] = not bool(p.get('favorito', False))
            if self._container is not None:
                self._container.marcar_sujo()
            if self._painel_times is not None:
                self._painel_times.marcar_sujo()

        opcoes = [
            {'texto': 'Analisar', 'acao': lambda p=pokemon: self._abrir_analise_pokemon(p)},
            {'texto': 'Renomear', 'acao': lambda p=pokemon: self._abrir_renomear_pokemon(p)},
            {'texto': 'Desfavoritar' if favorito else 'Favoritar', 'acao': _toggle_favorito},
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
        if self._barra_pesquisa is None or (callable(self._possui_modal) and self._possui_modal()) or self._opcoes.Ativa:
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

    def _iniciar_arrasto_aux_item(self, alvo, mouse_pos):
        if alvo is None or alvo[0] != 'aux' or alvo[1] not in {'pocoes', 'equipaveis'}:
            return
        indice_visual = int(alvo[2])
        slot_inventario = self._painel_auxiliar.slot_inventario_por_visual(indice_visual) if self._painel_auxiliar is not None else None
        if self.Inventario is None:
            return
        if slot_inventario is None:
            item_origem = self._painel_auxiliar.item_por_visual(indice_visual) if self._painel_auxiliar is not None else None
            if not isinstance(item_origem, dict):
                return
            if str(item_origem.get("Estilo") or "").strip().lower() != "doce":
                return
            grupo = str(item_origem.get("Grupo") or "").strip()
            qtd_doces = int(getattr(self.Inventario, "Doces", {}).get(grupo, 0) or 0)
            if qtd_doces <= 0:
                return
            self.Inventario.Doces[grupo] = qtd_doces - 1
            item_drag = copy.deepcopy(item_origem)
            item_drag["quantidade"] = 1
            origem = ("aux_doce", grupo)
        else:
            if not (0 <= slot_inventario < len(self.Inventario.Itens)):
                return
            item_origem = self.Inventario.Itens[slot_inventario]
            if not isinstance(item_origem, dict):
                return
            item_drag = copy.deepcopy(item_origem)
            item_drag['quantidade'] = 1
            qtd = int(item_origem.get('quantidade', 1) or 1)
            if qtd <= 1:
                self.Inventario.Itens[slot_inventario] = None
            else:
                item_origem['quantidade'] = qtd - 1
            origem = ('aux_item', slot_inventario)
        if self._painel_auxiliar is not None:
            self._painel_auxiliar.marcar_sujo()
        rect_slot = self._painel_auxiliar._container.slot_rect(indice_visual) if self._painel_auxiliar and self._painel_auxiliar._container else pygame.Rect(mouse_pos[0], mouse_pos[1], 42, 42)
        self._arrastavel.iniciar(item_drag, origem, rect_slot.inflate(-8, -8), mouse_pos, botao=1)

    def _iniciar_arrasto_build(self, indice_slot, mouse_pos):
        if self._pokemon_analisado is None:
            return
        equip = self._ficha_pokemon.retirar_equipavel_slot(self._pokemon_analisado, indice_slot)
        if not isinstance(equip, dict):
            return
        rect = self._ficha_pokemon._slots_build.get(indice_slot)
        if rect is None:
            return
        item = self._build_para_item(equip)
        if not isinstance(item, dict):
            item = {'Nome': str(equip.get('Nome') or 'Equipável'), 'Estilo': 'equipavel', 'quantidade': 1}
        item['quantidade'] = 1
        self._arrastavel.iniciar(item, ('build', indice_slot, equip), rect.inflate(-8, -8), mouse_pos, botao=1)

    def _restaurar_origem_aux(self):
        origem = self._arrastavel.Origem or ()
        item = self._arrastavel.Item
        if not origem or origem[0] != 'aux_item' or not isinstance(item, dict) or self.Inventario is None:
            return
        idx = int(origem[1])
        if 0 <= idx < len(self.Inventario.Itens):
            atual = self.Inventario.Itens[idx]
            if isinstance(atual, dict) and str(atual.get('Nome')) == str(item.get('Nome')):
                atual['quantidade'] = int(atual.get('quantidade', 1) or 1) + int(item.get('quantidade', 1) or 1)
            elif atual is None:
                self.Inventario.Itens[idx] = copy.deepcopy(item)
        if self._painel_auxiliar is not None:
            self._painel_auxiliar.marcar_sujo()

    def _retornar_item_build(self, indice_slot, item):
        equip = self._equipavel_para_build(item)
        if equip is not None and self._pokemon_analisado is not None:
            self._ficha_pokemon.definir_equipavel_slot(self._pokemon_analisado, indice_slot, equip)

    def _devolver_build_para_inventario_ou_drop(self, equipavel):
        item = self._build_para_item(equipavel)
        if not isinstance(item, dict):
            return False
        item['quantidade'] = int(item.get('quantidade', 1) or 1)
        if self.Inventario is not None and self.Inventario.adicionar_item(item):
            if int(item.get('quantidade', 0) or 0) <= 0:
                return True
            return self._dropar_item_mundo(item)
        return self._dropar_item_mundo(item)

    def _adicionar_item_inventario_ou_dropar_sobra(self, item):
        if not isinstance(item, dict):
            return False
        item['quantidade'] = int(item.get('quantidade', 1) or 1)
        if self.Inventario is not None and self.Inventario.adicionar_item(item):
            if int(item.get('quantidade', 0) or 0) <= 0:
                return True
            return self._dropar_item_mundo(item)
        return self._dropar_item_mundo(item)

    def _dropar_item_mundo(self, item):
        controle = getattr(self.Ator, 'Controle', None)
        if controle is None:
            return False
        controle._acao_drop_item_mundo_pendente = {
            'item': copy.deepcopy(item),
            'origem': tuple(getattr(self.Ator, 'Posicao', (0, 0))),
        }
        tocar("Dropar")
        return True

    def _retornar_para_origem(self):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return
        origem = self._arrastavel.Origem or ()
        if origem and origem[0] == 'aux_item':
            self._restaurar_origem_aux()
            self._arrastavel.cancelar()
            return
        if origem and origem[0] == 'aux_doce':
            grupo = str(origem[1])
            if not hasattr(self.Inventario, "Doces"):
                self.Inventario.Doces = {}
            self.Inventario.Doces[grupo] = int(self.Inventario.Doces.get(grupo, 0) or 0) + 1
            if self._painel_auxiliar is not None:
                self._painel_auxiliar.marcar_sujo()
            self._arrastavel.cancelar()
            return
        if origem and origem[0] == 'build':
            self._retornar_item_build(origem[1], self._arrastavel.Item)
            self._arrastavel.cancelar()
            return
        if origem and origem[0] == 'time':
            self._painel_times.definir_slot(origem[1], origem[2], self._arrastavel.Item)
            self._arrastavel.cancelar()
            return
        if origem and origem[0] == 'grid':
            rect = self._container.slot_rect(origem[1])
            self._arrastavel.iniciar_retorno(self._container.item_rect_no_slot(rect).topleft)
            return
        self._arrastavel.cancelar()

    def _soltar_no_alvo(self, alvo):
        if not self._arrastavel.Ativo or self._arrastavel.Item is None:
            return

        origem = self._arrastavel.Origem or ()
        if alvo is None and (not origem or origem[0] not in {'aux_item', 'aux_doce', 'build'}):
            return
        pokemon_arrastado = self._arrastavel.Item

        if origem[0] in {'aux_item', 'aux_doce', 'build'}:
            if self._pokemon_analisado is None:
                self._retornar_para_origem()
                return
            item = self._arrastavel.Item
            idx_build = self._ficha_pokemon.slot_build_no_mouse(pygame.mouse.get_pos())
            if idx_build is not None and self._estilo_item(item) == 'equipavel':
                equip = self._equipavel_para_build(item)
                if equip is None:
                    self._retornar_para_origem()
                    return
                anterior = self._ficha_pokemon.definir_equipavel_slot(self._pokemon_analisado, idx_build, equip)
                if isinstance(anterior, dict):
                    item_anterior = self._build_para_item(anterior)
                    if isinstance(item_anterior, dict):
                        self._adicionar_item_inventario_ou_dropar_sobra(item_anterior)
                self._arrastavel.cancelar()
                return

            if self._ficha_pokemon.area_animacao_rect().collidepoint(pygame.mouse.get_pos()) and self._estilo_item(item) == 'poção':
                resultado = _EXEC_POCAO.executar_pocao(str(item.get('Nome') or ''), self._pokemon_analisado)
                if not bool(resultado.get('ok', False)):
                    self._retornar_para_origem()
                    return
                self._arrastavel.cancelar()
                return
            if self._ficha_pokemon.area_animacao_rect().collidepoint(pygame.mouse.get_pos()) and self._estilo_item(item) == 'doce':
                resultado = _EXEC_POCAO.executar_doce(item, self._pokemon_analisado)
                if not bool(resultado.get('ok', False)):
                    self._retornar_para_origem()
                    return
                self._arrastavel.cancelar()
                return
            self._retornar_para_origem()
            return

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

        chave_layout = self._chave_layout(area)
        if not self._layout_montado or chave_layout != self._ultima_chave_layout:
            self._reconstruir(area)
            self._ultima_chave_layout = chave_layout
        if not ativo:
            if self._estava_ativo:
                self.on_close()
            return
        if not self._estava_ativo:
            self.on_open()

        chave_layout = self._chave_layout(area)
        if chave_layout != self._ultima_chave_layout:
            self._reconstruir(area)
            self._ultima_chave_layout = chave_layout
        self._sincronizar_pokemon_analisado()
        if callable(self._possui_modal) and self._possui_modal():
            return

        analisando = self._pokemon_analisado is not None
        if not analisando:
            self._container._normalizar_tamanho()
            self._container._processar_scroll(eventos)
        elif self._painel_auxiliar is not None:
            self._painel_auxiliar.sincronizar(self.Inventario, self._area_times, self._area_abas)
            self._painel_auxiliar.processar_eventos(eventos)
        painel_times_ativo = self._painel_times_ativo(analisando)
        if painel_times_ativo:
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
            alvo_mouse = self._alvo_no_mouse(pygame.mouse.get_pos())
            self._pokemon_hover = self._pokemon_do_alvo(alvo_mouse) or self._pokemon_analisado

        for evento in eventos:
            if evento.type == pygame.MOUSEMOTION and self._arrastavel.Ativo and self._arrastavel.PosAlvo is None:
                self._arrastavel.atualizar(evento.pos)

            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if analisando and self._area_ficha.collidepoint(evento.pos):
                    if self._arrastavel.Ativo:
                        alvo = self._alvo_no_mouse(evento.pos)
                        if alvo is None and (self._arrastavel.Origem or (None,))[0] not in {'aux_item', 'aux_doce', 'build'}:
                            if (self._arrastavel.Origem or (None,))[0] == 'build':
                                if self._devolver_build_para_inventario_ou_drop((self._arrastavel.Origem or (None, None, None))[2]):
                                    self._arrastavel.cancelar()
                                else:
                                    self._retornar_para_origem()
                            else:
                                self._retornar_para_origem()
                        else:
                            self._soltar_no_alvo(alvo)
                    else:
                        idx_build = self._ficha_pokemon.slot_build_no_mouse(evento.pos)
                        if idx_build is not None and self._ficha_pokemon.equipavel_no_slot(self._pokemon_analisado, idx_build) is not None:
                            self._iniciar_arrasto_build(idx_build, evento.pos)
                    continue
                if analisando:
                    alvo_aux = self._alvo_no_mouse(evento.pos)
                    if self._arrastavel.Ativo:
                        if alvo_aux is None:
                            if (self._arrastavel.Origem or (None,))[0] == 'build':
                                if self._devolver_build_para_inventario_ou_drop((self._arrastavel.Origem or (None, None, None))[2]):
                                    self._arrastavel.cancelar()
                                else:
                                    self._retornar_para_origem()
                            else:
                                self._retornar_para_origem()
                        else:
                            self._soltar_no_alvo(alvo_aux)
                    elif alvo_aux is not None and alvo_aux[0] == 'aux':
                        if alvo_aux[1] == 'pokemons':
                            if getattr(evento, 'clicks', 1) >= 2:
                                self._abrir_analise_pokemon(alvo_aux[3])
                            else:
                                self._pokemon_analisado = alvo_aux[3]
                                self._pokemon_hover = alvo_aux[3]
                                self._layout_montado = False
                        else:
                            self._iniciar_arrasto_aux_item(alvo_aux, evento.pos)
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
                    if getattr(evento, 'clicks', 1) >= 2:
                        self._abrir_analise_pokemon(self._pokemon_do_alvo(alvo))
                        continue
                    self._iniciar_arrasto(alvo, evento.pos)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 3:
                if analisando and self._painel_auxiliar is not None and self._painel_auxiliar.aba_ativa == 'pokemons':
                    alvo_aux = self._alvo_no_mouse(evento.pos)
                    if alvo_aux is not None and alvo_aux[0] == 'aux' and alvo_aux[1] == 'pokemons':
                        self._abrir_opcoes_pokemon(evento.pos, alvo_aux[3])
                        continue
                pode_contexto_time = self._painel_times_ativo(analisando)
                alvo_ctx = self._painel_times.alvo_contexto_no_mouse(evento.pos) if self._painel_times is not None and pode_contexto_time else None
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
                if analisando and self._area_ficha.collidepoint(evento.pos):
                    continue
                if analisando:
                    continue

                alvo = self._alvo_no_mouse(evento.pos)
                if alvo is not None and alvo[0] == 'grid':
                    pokemon = None
                    if self._container is not None:
                        indice_real = self._container.indice_real_por_visual(alvo[1], exigir_item=True)
                        if indice_real is not None and 0 <= indice_real < len(self._container.Itens):
                            pokemon = self._container.Itens[indice_real]
                    if pokemon is not None:
                        self._abrir_opcoes_pokemon(evento.pos, pokemon)

    def renderizar(self, tela, area, eventos, dt, ativo=True):
        self.atualizar(eventos, dt, area, ativo=ativo)
        if not ativo:
            return

        highlight = None if ((callable(self._possui_modal) and self._possui_modal()) or self._opcoes.Ativa) else self._alvo_no_mouse(pygame.mouse.get_pos())
        item_oculto_grid = None
        item_oculto_time = None
        if self._arrastavel.Ativo and self._arrastavel.Origem:
            if self._arrastavel.Origem[0] == 'grid':
                item_oculto_grid = self._arrastavel.Origem[1]
            elif self._arrastavel.Origem[0] == 'time':
                item_oculto_time = (self._arrastavel.Origem[1], self._arrastavel.Origem[2])

        analisando = self._pokemon_analisado is not None
        if analisando and self._area_ficha.width > 0:
            self._ficha_pokemon.renderizar(tela, self._area_ficha, self._pokemon_analisado, eventos=eventos, dt=dt, desenhar_arrastavel=False)
            if self._ficha_pokemon.FecharSolicitado:
                self._pokemon_analisado = None
                self._layout_montado = False
            elif self._ficha_pokemon.DoarSolicitado and self._pokemon_analisado is not None:
                self._abrir_confirmacao_doacao(self._pokemon_analisado)
            elif self._ficha_pokemon.UparNivelSolicitado and self._pokemon_analisado is not None:
                self._evoluir_pokemon_analisado()

        if not analisando:
            self._container.desenhar(
                tela,
                item_oculto=item_oculto_grid,
                highlight=highlight[1] if highlight and highlight[0] == 'grid' else None,
                eventos=eventos,
                dt=dt,
            )
        if analisando and self._painel_auxiliar is not None:
            if self._painel_auxiliar.aba_ativa == 'times':
                self._painel_times.desenhar(
                    tela,
                    highlight=highlight if highlight and highlight[0] == 'time' else None,
                    item_oculto=item_oculto_time,
                )
            self._painel_auxiliar.desenhar(tela, eventos=eventos, dt=dt)
        else:
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

            self.TxtHover.set_text(self._nome_pokemon(self._pokemon_hover) or '')
            self.TxtHover.set_pos((self._area_info.x + 232, self._area_info.centery))
            self.TxtHover.draw(tela)
            self._desenhar_tipos_hover(tela, self._pokemon_hover)
            if self._botao_toggle_poder is not None:
                self._botao_toggle_poder.render(tela, eventos, dt, None)
        if self._arrastavel.Ativo and self._arrastavel.Item is not None:
            rect_drag = self._arrastavel.Rect.inflate(int(self._arrastavel.Rect.width * 0.1), int(self._arrastavel.Rect.height * 0.1))
            item_drag = self._arrastavel.Item
            if isinstance(item_drag, dict) and self._estilo_item(item_drag) == 'doce':
                Doce.desenhar_item_no_rect(tela, item_drag, rect_drag)
            elif isinstance(item_drag, dict) and self._estilo_item(item_drag) in {'equipavel', 'poção'}:
                ItemInventario.desenhar_item_no_rect(tela, item_drag, rect_drag)
            else:
                PokemonInventario.desenhar_item_no_rect(tela, item_drag, rect_drag, escala_sprite=0.86)
        if analisando:
            self._ficha_pokemon._desenhar_arrastavel(tela)
        self._opcoes.render(tela, eventos, dt)
    def _estilo_toggle_poder(self, ligado):
        if ligado:
            return {
                'bg': (92, 130, 210),
                'bg_hover': (112, 154, 232),
                'bg_pressed': (76, 114, 188),
                'border': (255, 252, 210),
                'border_hover': (255, 255, 235),
            }
        return {
            'bg': (52, 74, 132),
            'bg_hover': (80, 112, 188),
            'bg_pressed': (40, 58, 108),
            'border': (235, 242, 255),
            'border_hover': (255, 255, 255),
        }

    def _sincronizar_visual_toggle_poder(self):
        if self._botao_toggle_poder is None:
            return
        self._botao_toggle_poder.set_style(**self._estilo_toggle_poder(self._mostrar_poder_slots))
        self._botao_toggle_poder.set_text('P')
