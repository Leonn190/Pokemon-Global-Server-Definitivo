from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

Vector2 = Tuple[float, float]

EFEITOS_ATAQUE_FPS: Dict[str, float] = {
    'LabaredaMultipla': 31.25,
    'Corte': 10.2,
    'BolhasVerdes': 20,
    'CorteDourado': 10.87,
    'ChuvaVermelha': 31.25,
    'ChuvaBrilhante': 33.33,
    'Agua': 23.81,
    'AtemporalRosa': 40,
    'BarreiraCelular': 12.5,
    'ChicoteMultiplo': 13.89,
    'CorteDuploRoxo': 33.33,
    'CorteMagico': 25,
    'CorteRicocheteadoRoxo': 8.93,
    'CorteRosa': 25,
    'DomoVerde': 11.76,
    'EnergiaAzul': 15.38,
    'Engrenagem': 8.7,
    'EspiralAzul': 22.22,
    'Estouro': 10.31,
    'EstouroMagico': 20,
    'EstouroVermelho': 21.74,
    'Explosao': 22.22,
    'ExplosaoPedra': 10.87,
    'ExplosaoVerde': 8.93,
    'ExplosaoVermelha': 33.33,
    'ExplosaoRoxa': 9.52,
    'FacasAzuis': 35.71,
    'FacasBrancas': 26.32,
    'FacasColoridas': 31.25,
    'FacasRosas': 40,
    'FeixeMagenta': 23.81,
    'FeixeRoxo': 10.42,
    'FluxoAzul': 15.38,
    'Fogo': 10.53,
    'Fumaça': 28.57,
    'GasRoxo': 12.82,
    'Garra': 12.5,
    'HexagonoLaminas': 27.78,
    'ImpactoRochoso': 8.7,
    'Karate': 11.11,
    'LuaAmarela': 55.56,
    'MagiaAzul': 38.46,
    'MagiaMagenta': 20.83,
    'MarcaBrilhosa': 26.32,
    'MarcaAmarela': 19.23,
    'MarcaAzul': 26.32,
    'Mordida': 8.7,
    'MultiplasFacas': 27.78,
    'OrbesRoxos': 35.71,
    'PedaçoColorido': 26.32,
    'RaioAzul': 83.33,
    'RajadaAmarela': 28.57,
    'RasgoMagenta': 38.46,
    'RasgosRosa': 35.71,
    'RedemoinhoAzul': 26.32,
    'RedemoinhoCosmico': 10.53,
    'SuperDescarga': 12.2,
    'SuperNova': 31.25,
    'TirosAmarelos': 40,
    'TornadoAgua': 25.64
}


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, float(valor)))


def _ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)


def _normalizar_nome_efeito(nome: str) -> str:
    texto = unicodedata.normalize('NFKD', str(nome or '').strip().casefold())
    texto = ''.join(caractere for caractere in texto if unicodedata.category(caractere) != 'Mn')
    texto = ''.join(caractere for caractere in texto if caractere.isalnum())
    for sufixo in ('frames', 'frame'):
        if texto.endswith(sufixo) and len(texto) > len(sufixo):
            texto = texto[:-len(sufixo)]
            break
    return texto


def _batalha_para_tela_px(camera, posicao: Vector2) -> Vector2:
    if hasattr(camera, 'batalha_para_tela_px'):
        return camera.batalha_para_tela_px((float(posicao[0]), float(posicao[1])))
    return camera.mundo_para_tela_px((float(posicao[0]), float(posicao[1])))


class PokemonAnimator:
    _PASTA_EFEITOS_ATAQUE: Path | None = None
    _INDICE_EFEITOS_ATAQUE: Dict[str, Path] = {}
    _CACHE_FRAMES_EFEITO: Dict[str, List[pygame.Surface]] = {}
    _CACHE_FRAMES_ESCALADOS: Dict[Tuple[str, int], List[pygame.Surface]] = {}

    def __init__(self, pokemon) -> None:
        self.Pokemon = pokemon
        self._ultimo_tick = pygame.time.get_ticks()
        self._flashes: List[Dict[str, object]] = []
        self._cartuchos: List[Dict[str, object]] = []
        self._setas: List[Dict[str, object]] = []
        self._efeitos_ataque: List[Dict[str, object]] = []
        self._fluxos: List[Dict[str, object]] = []
        self._projeteis: List[Dict[str, object]] = []
        self._marcacoes_selecionaveis: List[Dict[str, object]] = []
        self._movimento: Dict[str, object] | None = None
        self._morte: Dict[str, object] | None = None
        self._corpo_oculto = False

    def atualizar(self) -> None:
        agora = pygame.time.get_ticks()
        dt = max(0.0, min(0.05, (agora - self._ultimo_tick) / 1000.0))
        self._ultimo_tick = agora

        self._atualizar_flashes(dt)
        self._atualizar_cartuchos(dt)
        self._atualizar_setas(dt)
        self._atualizar_efeitos_ataque(dt)
        self._atualizar_fluxos(dt)
        self._atualizar_projeteis(dt)
        self._atualizar_marcacoes_selecionaveis(dt)
        self._atualizar_movimento(dt)
        self._atualizar_morte(dt)

    def renderizar(self, tela: pygame.Surface, camera) -> None:
        self._desenhar_fluxos(tela, camera)
        self._desenhar_projeteis(tela, camera)
        self._desenhar_marcacoes_selecionaveis(tela, camera)
        self._desenhar_efeitos_ataque(tela, camera)
        self._desenhar_flash(tela, camera)
        self._desenhar_setas(tela, camera)
        self._desenhar_cartuchos(tela, camera)

    def tomar_dano(self, valor: float = 0.0, critico: bool = False) -> None:
        self._adicionar_flash((255, 72, 72), 0.24)
        if valor:
            self.cartucho(valor, tipo='dano', critico=critico)

    def tomar_cura(self, valor: float = 0.0) -> None:
        self._adicionar_flash((72, 235, 120), 0.24)
        if valor:
            self.cartucho(valor, tipo='cura', critico=False)

    def cartucho(self, valor: float, tipo: str = 'dano', critico: bool = False) -> None:
        valor_num = float(valor)
        cor = (230, 74, 74) if tipo == 'dano' else (72, 214, 110)
        prefixo = '-' if tipo == 'dano' else '+'
        magnitude = abs(valor_num)
        self._cartuchos.append(
            {
                'valor': magnitude,
                'texto': f"{prefixo}{int(round(magnitude))}",
                'tipo': tipo,
                'critico': bool(critico),
                'cor': cor,
                'tempo': 0.0,
                'duracao': 0.72 if critico else 0.62,
                'offset_x_tiles': 0.0,
            }
        )

    def buffar(self, intensidade: int = 1) -> None:
        self._gerar_setas(subindo=True, intensidade=intensidade)

    def nerfar(self, intensidade: int = 1) -> None:
        self._gerar_setas(subindo=False, intensidade=intensidade)

    def mover(self, destino: Vector2, velocidade_tiles_por_seg: float) -> None:
        inicio = (float(self.Pokemon.Posicao[0]), float(self.Pokemon.Posicao[1]))
        destino = (float(destino[0]), float(destino[1]))
        velocidade = max(0.01, float(velocidade_tiles_por_seg))
        self._movimento = {
            'inicio': inicio,
            'destino': destino,
            'velocidade': velocidade,
        }

    def animar_morte(self) -> None:
        if self._morte is not None:
            return
        self._morte = {
            'tempo': 0.0,
            'duracao': 0.6,
        }
        self._corpo_oculto = False

    def marcar_selecionavel(self, *, cor: Tuple[int, int, int] = (255, 86, 86), duracao_s: float = 0.18) -> None:
        self._marcacoes_selecionaveis.append(
            {
                'cor': tuple(cor),
                'tempo': 0.0,
                'duracao': max(0.05, float(duracao_s)),
            }
        )

    def restaurar_visual_corpo(self) -> None:
        self._morte = None
        self._corpo_oculto = False

    def aplicar_fluxo(
        self,
        origem: Vector2,
        destino: Vector2,
        *,
        alcance_tiles: float = 0.0,
        raio_tiles: float = 0.0,
        largura_graus: float = 60.0,
        duracao_s: float = 0.35,
        modo: str = 'area',
    ) -> None:
        self._fluxos.append(
            {
                'origem': (float(origem[0]), float(origem[1])),
                'destino': (float(destino[0]), float(destino[1])),
                'alcance_tiles': max(0.0, float(alcance_tiles)),
                'raio_tiles': max(0.0, float(raio_tiles)),
                'largura_graus': max(1.0, float(largura_graus)),
                'duracao': max(0.08, float(duracao_s)),
                'tempo': 0.0,
                'modo': str(modo or 'area').casefold(),
            }
        )

    def lancar_projetil(
        self,
        origem: Vector2,
        destino: Vector2,
        velocidade_tiles_por_seg: float,
        *,
        raio_tiles: float = 0.22,
    ) -> None:
        origem_t = (float(origem[0]), float(origem[1]))
        destino_t = (float(destino[0]), float(destino[1]))
        distancia = math.hypot(destino_t[0] - origem_t[0], destino_t[1] - origem_t[1])
        velocidade = max(0.05, float(velocidade_tiles_por_seg))
        self._projeteis.append(
            {
                'origem': origem_t,
                'destino': destino_t,
                'raio_tiles': max(0.08, float(raio_tiles)),
                'duracao': max(0.08, distancia / velocidade if velocidade > 0.0 else 0.18),
                'tempo': 0.0,
            }
        )

    def sofrer_ataque_efeito(
        self,
        nome_efeito: str,
        *,
        escala: float = 1.35,
        loops: int = 1,
        offset_tiles: Vector2 = (0.0, 0.0),
    ) -> bool:
        frames = self._obter_frames_efeito(nome_efeito)
        if not frames:
            return False

        fps = float(EFEITOS_ATAQUE_FPS.get(nome_efeito, EFEITOS_ATAQUE_FPS.get(str(nome_efeito).strip(), 24.0)))
        self._efeitos_ataque.append(
            {
                'nome': str(nome_efeito),
                'tempo': 0.0,
                'fps': max(1.0, fps),
                'duracao': (len(frames) / max(1.0, fps)) * max(1, int(loops)),
                'escala': max(0.05, float(escala)),
                'offset_tiles': (float(offset_tiles[0]), float(offset_tiles[1])),
            }
        )
        return True

    def SofrerAtaqueEfeito(
        self,
        nome_efeito: str,
        *,
        escala: float = 1.35,
        loops: int = 1,
        offset_tiles: Vector2 = (0.0, 0.0),
    ) -> bool:
        return self.sofrer_ataque_efeito(
            nome_efeito,
            escala=escala,
            loops=loops,
            offset_tiles=offset_tiles,
        )

    def esta_movendo(self) -> bool:
        return self._movimento is not None

    def preparar_corpo_visual(self, camada: pygame.Surface, camera) -> tuple[pygame.Surface, tuple[int, int], bool]:
        if self._corpo_oculto:
            return camada, (0, 0), True

        superficie = camada
        offset_tiles = (0.0, 0.0)
        alpha = 255
        angulo = 0.0
        escala = 1.0
        if self._morte is not None:
            duracao = max(0.01, float(self._morte.get('duracao', 0.6)))
            t = _clamp(float(self._morte.get('tempo', 0.0)) / duracao, 0.0, 1.0)
            angulo = -900.0 * t
            alpha = max(0, min(255, int(255 * (1.0 - t))))
            escala = max(0.85, 1.0 - t * 0.08)
            offset_tiles = (0.0, -0.05 * t)

        if alpha < 255:
            superficie = superficie.copy()
            superficie.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        if abs(angulo) > 0.01 or abs(escala - 1.0) > 0.01:
            superficie = pygame.transform.rotozoom(superficie, angulo, escala)

        tile_px = max(1, int(getattr(camera, 'TilePx', 40) or 40))
        offset_px = (
            int(offset_tiles[0] * tile_px),
            int(offset_tiles[1] * tile_px),
        )
        return superficie, offset_px, False

    def _adicionar_flash(self, cor: Tuple[int, int, int], duracao: float) -> None:
        self._flashes.append({'cor': tuple(cor), 'tempo': 0.0, 'duracao': float(duracao)})

    def _atualizar_flashes(self, dt: float) -> None:
        novos = []
        for efeito in self._flashes:
            efeito['tempo'] = float(efeito['tempo']) + dt
            if float(efeito['tempo']) < float(efeito['duracao']):
                novos.append(efeito)
        self._flashes = novos

    def _atualizar_cartuchos(self, dt: float) -> None:
        novos = []
        for cartucho in self._cartuchos:
            cartucho['tempo'] = float(cartucho['tempo']) + dt
            if float(cartucho['tempo']) < float(cartucho['duracao']):
                novos.append(cartucho)
        self._cartuchos = novos

    def _atualizar_setas(self, dt: float) -> None:
        novos = []
        for seta in self._setas:
            seta['tempo'] = float(seta['tempo']) + dt
            if float(seta['tempo']) < float(seta['duracao']):
                novos.append(seta)
        self._setas = novos

    def _atualizar_efeitos_ataque(self, dt: float) -> None:
        novos = []
        for efeito in self._efeitos_ataque:
            efeito['tempo'] = float(efeito['tempo']) + dt
            if float(efeito['tempo']) < float(efeito['duracao']):
                novos.append(efeito)
        self._efeitos_ataque = novos

    def _atualizar_fluxos(self, dt: float) -> None:
        novos = []
        for fluxo in self._fluxos:
            fluxo['tempo'] = float(fluxo['tempo']) + dt
            if float(fluxo['tempo']) < float(fluxo['duracao']):
                novos.append(fluxo)
        self._fluxos = novos

    def _atualizar_projeteis(self, dt: float) -> None:
        novos = []
        for projetil in self._projeteis:
            projetil['tempo'] = float(projetil['tempo']) + dt
            if float(projetil['tempo']) < float(projetil['duracao']):
                novos.append(projetil)
        self._projeteis = novos

    def _atualizar_marcacoes_selecionaveis(self, dt: float) -> None:
        novos = []
        for marca in self._marcacoes_selecionaveis:
            marca['tempo'] = float(marca['tempo']) + dt
            if float(marca['tempo']) < float(marca['duracao']):
                novos.append(marca)
        self._marcacoes_selecionaveis = novos

    def _atualizar_movimento(self, dt: float) -> None:
        if self._movimento is None:
            return

        atual_x, atual_y = float(self.Pokemon.Posicao[0]), float(self.Pokemon.Posicao[1])
        destino_x, destino_y = self._movimento['destino']
        delta_x = destino_x - atual_x
        delta_y = destino_y - atual_y
        distancia = math.hypot(delta_x, delta_y)
        if distancia <= 0.0001:
            self.Pokemon.Posicao = (destino_x, destino_y)
            self._movimento = None
            return

        passo = float(self._movimento['velocidade']) * dt
        if passo >= distancia:
            self.Pokemon.Posicao = (destino_x, destino_y)
            self._movimento = None
            return

        nx = delta_x / distancia
        ny = delta_y / distancia
        self.Pokemon.Posicao = (atual_x + nx * passo, atual_y + ny * passo)

    def _atualizar_morte(self, dt: float) -> None:
        if self._morte is None:
            return
        self._morte['tempo'] = float(self._morte.get('tempo', 0.0)) + dt
        if float(self._morte.get('tempo', 0.0)) >= float(self._morte.get('duracao', 0.6)):
            self._corpo_oculto = True
            self._morte = None

    def _gerar_setas(self, *, subindo: bool, intensidade: int = 1) -> None:
        total = max(1, min(6, int(intensidade) + 2))
        offsets = []
        if total == 1:
            offsets = [0.0]
        else:
            largura = 0.78
            offsets = [
                (-largura * 0.5) + (largura * (indice / (total - 1)))
                for indice in range(total)
            ]
        for indice, offset in enumerate(offsets):
            self._setas.append(
                {
                    'subindo': bool(subindo),
                    'tempo': -(indice * 0.045),
                    'duracao': 0.52,
                    'offset_x_tiles': offset,
                }
            )

    @classmethod
    def _resolver_pasta_efeitos_ataque(cls) -> Path | None:
        if cls._PASTA_EFEITOS_ATAQUE is not None and cls._PASTA_EFEITOS_ATAQUE.exists():
            return cls._PASTA_EFEITOS_ATAQUE

        arquivo_atual = Path(__file__).resolve()
        candidatos = []
        for base in [arquivo_atual.parent, *arquivo_atual.parents]:
            candidatos.append(base / 'Recursos' / 'Visual' / 'AtaquesGifs')
        candidatos.append(Path(r'C:\Users\euleo\OneDrive\Documentos\GitHub\Pokemon-Global-Server-Definitivo\Recursos\Visual\AtaquesGifs'))

        for candidato in candidatos:
            if candidato.exists():
                cls._PASTA_EFEITOS_ATAQUE = candidato
                return candidato
        return None

    @staticmethod
    def _chave_ordenacao_frame(caminho: Path) -> tuple:
        partes = re.split(r'(\d+)', caminho.stem.casefold())
        chave = []
        for parte in partes:
            if parte.isdigit():
                chave.append((0, int(parte)))
            else:
                chave.append((1, parte))
        return tuple(chave)

    @classmethod
    def _obter_pasta_efeito(cls, nome_efeito: str) -> Path | None:
        pasta = cls._resolver_pasta_efeitos_ataque()
        if pasta is None:
            return None

        if not cls._INDICE_EFEITOS_ATAQUE:
            for subpasta in pasta.iterdir():
                if subpasta.is_dir():
                    cls._INDICE_EFEITOS_ATAQUE[_normalizar_nome_efeito(subpasta.name)] = subpasta

        return cls._INDICE_EFEITOS_ATAQUE.get(_normalizar_nome_efeito(nome_efeito))

    @classmethod
    def _carregar_frames_efeito(cls, nome_efeito: str) -> List[pygame.Surface]:
        chave = _normalizar_nome_efeito(nome_efeito)
        if chave in cls._CACHE_FRAMES_EFEITO:
            return cls._CACHE_FRAMES_EFEITO[chave]

        pasta_efeito = cls._obter_pasta_efeito(nome_efeito)
        if pasta_efeito is None:
            cls._CACHE_FRAMES_EFEITO[chave] = []
            return []

        extensoes_validas = {'.png', '.webp', '.jpg', '.jpeg', '.bmp', '.gif'}
        arquivos_frame = [
            arquivo
            for arquivo in pasta_efeito.iterdir()
            if arquivo.is_file() and arquivo.suffix.casefold() in extensoes_validas
        ]
        arquivos_frame.sort(key=cls._chave_ordenacao_frame)

        frames: List[pygame.Surface] = []
        for arquivo in arquivos_frame:
            try:
                frames.append(pygame.image.load(str(arquivo)).convert_alpha())
            except pygame.error:
                continue

        cls._CACHE_FRAMES_EFEITO[chave] = frames
        return frames

    @classmethod
    def _obter_frames_efeito(cls, nome_efeito: str) -> List[pygame.Surface]:
        return cls._carregar_frames_efeito(nome_efeito)

    @classmethod
    def _obter_frames_efeito_escalados(
        cls,
        nome_efeito: str,
        tamanho_alvo_px: int,
    ) -> List[pygame.Surface]:
        chave_nome = _normalizar_nome_efeito(nome_efeito)
        chave_cache = (chave_nome, int(tamanho_alvo_px))
        if chave_cache in cls._CACHE_FRAMES_ESCALADOS:
            return cls._CACHE_FRAMES_ESCALADOS[chave_cache]

        frames_originais = cls._obter_frames_efeito(nome_efeito)
        if not frames_originais:
            cls._CACHE_FRAMES_ESCALADOS[chave_cache] = []
            return []

        frames_escalados: List[pygame.Surface] = []
        tamanho_alvo_px = max(8, int(tamanho_alvo_px))
        for frame in frames_originais:
            largura, altura = frame.get_size()
            maior_dimensao = max(1, largura, altura)
            fator = tamanho_alvo_px / float(maior_dimensao)
            nova_largura = max(1, int(round(largura * fator)))
            nova_altura = max(1, int(round(altura * fator)))
            frames_escalados.append(pygame.transform.smoothscale(frame, (nova_largura, nova_altura)))

        cls._CACHE_FRAMES_ESCALADOS[chave_cache] = frames_escalados
        return frames_escalados

    def _desenhar_efeitos_ataque(self, tela: pygame.Surface, camera) -> None:
        if not self._efeitos_ataque:
            return

        centro_x, centro_y = self.Pokemon.centro_tela(camera)
        diametro_px = max(8, int(round(self.Pokemon.raio_px(camera) * 2)))

        for efeito in self._efeitos_ataque:
            nome = str(efeito['nome'])
            fps = max(1.0, float(efeito['fps']))
            tempo = float(efeito['tempo'])
            escala = max(0.05, float(efeito['escala']))
            offset_x_tiles, offset_y_tiles = efeito['offset_tiles']
            tamanho_alvo_px = max(8, int(round(diametro_px * escala)))
            frames = self._obter_frames_efeito_escalados(nome, tamanho_alvo_px)
            if not frames:
                continue

            indice_frame = min(len(frames) - 1, int(tempo * fps) % len(frames))
            frame = frames[indice_frame]
            x = centro_x + int(float(offset_x_tiles) * getattr(camera, 'TilePx', 40))
            y = centro_y + int(float(offset_y_tiles) * getattr(camera, 'TilePx', 40))
            tela.blit(frame, frame.get_rect(center=(x, y)))

    def _desenhar_fluxos(self, tela: pygame.Surface, camera) -> None:
        if not self._fluxos:
            return
        tile_px = max(1, int(getattr(camera, 'TilePx', 40) or 40))
        for fluxo in self._fluxos:
            duracao = max(0.01, float(fluxo['duracao']))
            t = _clamp(float(fluxo['tempo']) / duracao, 0.0, 1.0)
            alpha = int(145 * (1.0 - t))
            if alpha <= 0:
                continue

            origem = fluxo['origem']
            destino = fluxo['destino']
            modo = str(fluxo.get('modo') or 'area').casefold()
            if modo == 'zona':
                centro = _batalha_para_tela_px(camera, destino)
                raio_atual_px = max(4, int(float(fluxo.get('raio_tiles', 0.0)) * tile_px * max(0.05, t)))
                camada = pygame.Surface((raio_atual_px * 4, raio_atual_px * 4), pygame.SRCALPHA)
                centro_local = (camada.get_width() // 2, camada.get_height() // 2)
                pygame.draw.circle(camada, (122, 232, 255, int(alpha * 0.28)), centro_local, raio_atual_px)
                pygame.draw.circle(camada, (235, 248, 255, alpha), centro_local, raio_atual_px, max(2, raio_atual_px // 8))
                tela.blit(camada, camada.get_rect(center=(int(centro[0]), int(centro[1]))))
                continue

            origem_px = _batalha_para_tela_px(camera, origem)
            destino_px = _batalha_para_tela_px(camera, destino)
            dx = float(destino_px[0] - origem_px[0])
            dy = float(destino_px[1] - origem_px[1])
            distancia_px = math.hypot(dx, dy)
            if distancia_px <= 1e-6:
                continue
            nx = dx / distancia_px
            ny = dy / distancia_px
            alcance_tiles = max(float(fluxo.get('alcance_tiles', 0.0)), math.hypot(destino[0] - origem[0], destino[1] - origem[1]))
            alcance_px = max(2.0, alcance_tiles * tile_px * max(0.05, t))
            largura = math.tan(math.radians(max(1.0, float(fluxo.get('largura_graus', 60.0))) * 0.5)) * alcance_px
            ponta = (origem_px[0] + nx * alcance_px, origem_px[1] + ny * alcance_px)
            perp = (-ny, nx)
            pontos = [
                (origem_px[0], origem_px[1]),
                (ponta[0] + perp[0] * largura, ponta[1] + perp[1] * largura),
                (ponta[0] - perp[0] * largura, ponta[1] - perp[1] * largura),
            ]
            camada = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(camada, (112, 225, 255, int(alpha * 0.22)), pontos)
            pygame.draw.polygon(camada, (236, 248, 255, alpha), pontos, 2)
            tela.blit(camada, (0, 0))

    def _desenhar_projeteis(self, tela: pygame.Surface, camera) -> None:
        if not self._projeteis:
            return
        tile_px = max(1, int(getattr(camera, 'TilePx', 40) or 40))
        for projetil in self._projeteis:
            duracao = max(0.01, float(projetil['duracao']))
            t = _clamp(float(projetil['tempo']) / duracao, 0.0, 1.0)
            alpha = int(255 * (1.0 - t * 0.25))
            origem = projetil['origem']
            destino = projetil['destino']
            atual = (
                origem[0] + (destino[0] - origem[0]) * t,
                origem[1] + (destino[1] - origem[1]) * t,
            )
            origem_px = _batalha_para_tela_px(camera, origem)
            atual_px = _batalha_para_tela_px(camera, atual)
            raio_px = max(3, int(float(projetil.get('raio_tiles', 0.22)) * tile_px))
            camada = pygame.Surface((raio_px * 7, raio_px * 7), pygame.SRCALPHA)
            centro_local = (camada.get_width() // 2, camada.get_height() // 2)
            pygame.draw.circle(camada, (255, 249, 221, max(28, int(alpha * 0.28))), centro_local, max(2, int(raio_px * 1.5)))
            pygame.draw.circle(camada, (255, 224, 120, alpha), centro_local, raio_px)
            pygame.draw.circle(camada, (255, 255, 255, alpha), centro_local, max(1, int(raio_px * 0.4)))
            pygame.draw.line(
                tela,
                (255, 224, 120, max(18, int(alpha * 0.3))),
                (int(origem_px[0]), int(origem_px[1])),
                (int(atual_px[0]), int(atual_px[1])),
                max(1, int(raio_px * 0.6)),
            )
            tela.blit(camada, camada.get_rect(center=(int(atual_px[0]), int(atual_px[1]))))

    def _desenhar_marcacoes_selecionaveis(self, tela: pygame.Surface, camera) -> None:
        if not self._marcacoes_selecionaveis:
            return
        centro = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)
        pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 115.0)
        for marca in self._marcacoes_selecionaveis[-2:]:
            cor = tuple(marca.get('cor') or (255, 86, 86))
            alpha = int(90 + 120 * pulso)
            largura = max(3, int(raio * (0.10 + 0.04 * pulso)))
            camada = pygame.Surface((raio * 4, raio * 4), pygame.SRCALPHA)
            pygame.draw.circle(
                camada,
                (int(cor[0]), int(cor[1]), int(cor[2]), alpha),
                (camada.get_width() // 2, camada.get_height() // 2),
                int(raio * (1.05 + 0.08 * pulso)),
                largura,
            )
            tela.blit(camada, camada.get_rect(center=centro))

    def _desenhar_flash(self, tela: pygame.Surface, camera) -> None:
        if not self._flashes:
            return
        centro = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)
        tamanho = max(8, raio * 4)
        camada = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
        centro_local = (tamanho // 2, tamanho // 2)

        for efeito in self._flashes:
            t = _clamp(float(efeito['tempo']) / float(efeito['duracao']), 0.0, 1.0)
            envelope = math.sin(t * math.pi)
            alpha = int(140 * envelope)
            if alpha <= 0:
                continue
            cor = efeito['cor']
            pygame.draw.circle(camada, (cor[0], cor[1], cor[2], alpha), centro_local, raio)
            pygame.draw.circle(camada, (255, 255, 255, int(alpha * 0.45)), centro_local, max(2, int(raio * 0.92)), max(2, int(raio * 0.12)))

        tela.blit(camada, camada.get_rect(center=centro))

    def _desenhar_cartuchos(self, tela: pygame.Surface, camera) -> None:
        if not self._cartuchos:
            return
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        centro_x, centro_y = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)

        for cartucho in self._cartuchos:
            t = _clamp(float(cartucho['tempo']) / float(cartucho['duracao']), 0.0, 1.0)
            alpha = int(255 * (1.0 - t))
            if alpha <= 0:
                continue

            valor = float(cartucho['valor'])
            fator_valor = min(1.0, valor / 250.0)
            escala_base = 0.58 + (0.42 * _ease_out_back(t))
            escala = escala_base * (1.0 + fator_valor * 0.38)
            tamanho_fonte = max(16, int(tile_px * (0.42 + fator_valor * 0.24) * escala))
            fonte = pygame.font.SysFont("arial", tamanho_fonte, bold=True)
            texto = fonte.render(str(cartucho['texto']), True, (255, 255, 255))
            largura = texto.get_width() + max(18, int(tile_px * 0.36))
            altura = texto.get_height() + max(10, int(tile_px * 0.18))

            y = centro_y - raio - int(tile_px * (0.28 + t * 0.95))
            x = centro_x + int(float(cartucho['offset_x_tiles']) * tile_px)
            rect = pygame.Rect(0, 0, largura, altura)
            rect.center = (x, y)

            camada = pygame.Surface((largura + 18, altura + 18), pygame.SRCALPHA)
            rect_local = pygame.Rect(9, 9, largura, altura)
            cor = cartucho['cor']
            pygame.draw.rect(camada, (0, 0, 0, int(alpha * 0.78)), rect_local.inflate(4, 4), border_radius=max(8, altura // 2))
            pygame.draw.rect(camada, (cor[0], cor[1], cor[2], alpha), rect_local, border_radius=max(8, altura // 2))
            pygame.draw.rect(camada, (255, 255, 255, int(alpha * 0.85)), rect_local, 2, border_radius=max(8, altura // 2))

            if bool(cartucho['critico']):
                self._desenhar_espinhos(camada, rect_local, alpha)

            texto_sombra = fonte.render(str(cartucho['texto']), True, (0, 0, 0))
            texto_sombra.set_alpha(int(alpha * 0.6))
            texto_alpha = texto.copy()
            texto_alpha.set_alpha(alpha)
            camada.blit(texto_sombra, texto_sombra.get_rect(center=(rect_local.centerx + 1, rect_local.centery + 1)))
            camada.blit(texto_alpha, texto_alpha.get_rect(center=rect_local.center))

            tela.blit(camada, camada.get_rect(center=rect.center))

    def _desenhar_espinhos(self, camada: pygame.Surface, rect: pygame.Rect, alpha: int) -> None:
        centro = pygame.Vector2(rect.center)
        raio_x = rect.width * 0.62
        raio_y = rect.height * 0.9
        pontos = []
        total = 16
        for indice in range(total):
            ang = (math.tau * indice) / total
            externo = (indice % 2) == 0
            fator_x = 1.26 if externo else 1.04
            fator_y = 1.36 if externo else 1.08
            pontos.append(
                (
                    centro.x + math.cos(ang) * raio_x * fator_x,
                    centro.y + math.sin(ang) * raio_y * fator_y,
                )
            )
        pygame.draw.polygon(camada, (255, 230, 120, int(alpha * 0.5)), pontos)

    def _desenhar_setas(self, tela: pygame.Surface, camera) -> None:
        if not self._setas:
            return
        tile_px = max(16, int(getattr(camera, 'TilePx', 40) or 40))
        centro_x, centro_y = self.Pokemon.centro_tela(camera)
        raio = self.Pokemon.raio_px(camera)

        for seta in self._setas:
            if float(seta['tempo']) < 0.0:
                continue
            t = _clamp(float(seta['tempo']) / float(seta['duracao']), 0.0, 1.0)
            alpha = int(210 * (1.0 - t))
            if alpha <= 0:
                continue

            deslocamento = (t * tile_px * 0.95)
            direcao = -1 if bool(seta['subindo']) else 1
            x = centro_x + int(float(seta['offset_x_tiles']) * tile_px)
            y = centro_y + int(direcao * (-raio * 0.15 + deslocamento))

            self._desenhar_seta_unica(
                tela,
                (x, y),
                altura=max(18, int(tile_px * 0.55)),
                largura=max(12, int(tile_px * 0.28)),
                alpha=alpha,
                subindo=bool(seta['subindo']),
            )

    @staticmethod
    def _desenhar_seta_unica(
        tela: pygame.Surface,
        centro: Tuple[int, int],
        *,
        altura: int,
        largura: int,
        alpha: int,
        subindo: bool,
    ) -> None:
        camada = pygame.Surface((largura * 3, altura * 3), pygame.SRCALPHA)
        cx, cy = camada.get_width() // 2, camada.get_height() // 2
        corpo_altura = max(6, int(altura * 0.44))
        corpo_largura = max(4, int(largura * 0.36))
        cabeca_altura = max(8, int(altura * 0.42))
        cor = (100, 215, 255, alpha) if subindo else (255, 175, 90, alpha)

        if subindo:
            rect_corpo = pygame.Rect(cx - corpo_largura // 2, cy - corpo_altura // 2 + 3, corpo_largura, corpo_altura)
            ponta = [(cx, cy - corpo_altura // 2 - cabeca_altura), (cx - largura // 2, cy - corpo_altura // 2), (cx + largura // 2, cy - corpo_altura // 2)]
        else:
            rect_corpo = pygame.Rect(cx - corpo_largura // 2, cy - corpo_altura // 2 - 3, corpo_largura, corpo_altura)
            ponta = [(cx, cy + corpo_altura // 2 + cabeca_altura), (cx - largura // 2, cy + corpo_altura // 2), (cx + largura // 2, cy + corpo_altura // 2)]

        pygame.draw.rect(camada, cor, rect_corpo, border_radius=max(2, corpo_largura // 2))
        pygame.draw.polygon(camada, cor, ponta)
        pygame.draw.rect(camada, (255, 255, 255, int(alpha * 0.55)), rect_corpo, 1, border_radius=max(2, corpo_largura // 2))
        pygame.draw.lines(camada, (255, 255, 255, int(alpha * 0.55)), True, ponta, 1)
        tela.blit(camada, camada.get_rect(center=centro))
