from __future__ import annotations

import math
from pathlib import Path
import unicodedata

import pygame

from Codigo.ModulosGerais.Auxiliares import carregar_frames

try:
    from Codigo.Prefabs.Texto import Texto as _TextoPrefab
except Exception:
    try:
        from Prefabs.Texto import Texto as _TextoPrefab
    except Exception:
        _TextoPrefab = None


def _i(valor, default=0) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return int(default)


def _normalizar_nome(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


ESTILOS_VISUAIS_EFEITOS: dict[str, dict[str, object]] = {
    "envenenado": {"cor": (150, 70, 190), "intensidade": 0.55, "particulas": "sobe", "densidade": 0.65, "vel": 0.85},
    "queimado": {"cor": (245, 116, 42), "intensidade": 0.68, "particulas": "sobe", "densidade": 1.35, "vel": 1.45},
    "encharcado": {"cor": (34, 86, 170), "intensidade": 0.55, "particulas": "desce", "densidade": 0.75, "vel": 1.05, "idle": "lento"},
    "encantado": {"cor": (238, 104, 185), "intensidade": 0.50, "particulas": "sobe", "densidade": 0.75, "vel": 0.92},
    "intoxicado": {"cor": (150, 52, 194), "intensidade": 0.82, "particulas": "sobe", "densidade": 1.15, "vel": 1.10},
    "congelado": {"cor": (145, 220, 255), "intensidade": 0.64, "particulas": None, "idle": "trava"},
    "amaldicoado": {"cor": (8, 8, 12), "intensidade": 0.62, "particulas": None},
    "amaldiçoado": {"cor": (8, 8, 12), "intensidade": 0.62, "particulas": None},
    "abencoado": {"cor": (250, 250, 245), "intensidade": 0.48, "particulas": None},
    "abençoado": {"cor": (250, 250, 245), "intensidade": 0.48, "particulas": None},
    "energizado": {"cor": (245, 212, 54), "intensidade": 0.54, "particulas": None, "idle": "rapido"},
}

EFEITOS_TRAVAM_FRAME = {"congelado", "dormindo", "paralisado"}
EFEITOS_IDLE_LENTO = {"encharcado"}
EFEITOS_IDLE_RAPIDO = {"energizado"}
EFEITO_VISUAL_INTENSIDADE_MULT = 0.45


class PokemonBatalhaEstado:
    def __init__(self, pokemon) -> None:
        self.pokemon = pokemon

    def __getattr__(self, nome):
        pokemon = object.__getattribute__(self, "pokemon")
        return object.__getattribute__(pokemon, nome)

    def __setattr__(self, nome, valor):
        if nome == "pokemon":
            object.__setattr__(self, nome, valor)
        else:
            setattr(self.pokemon, nome, valor)

    def definir_intervalo_frame_ms(self, intervalo_ms: float | int | None):
        try:
            ms = float(intervalo_ms)
        except (TypeError, ValueError):
            return
        if ms <= 0:
            return
        self.pokemon.TempoFrame = max(0.01, ms / 1000.0)

    def carregar_animacao(self):
        p = self.pokemon
        if p._carregamento_frames_tentado:
            return
        p._carregamento_frames_tentado = True

        info = p.Dados if isinstance(p.Dados, dict) else {}
        frames = []

        especie = str(p.Especie or info.get("especie") or info.get("Especie") or p.Nome or "").strip()
        base_anim = Path("Recursos") / "Visual" / "Pokemons" / "Animação"
        especie_candidatos = [
            especie,
            especie.lower(),
            especie.replace("_", " "),
            especie.replace("_", " ").lower(),
            especie.replace(" ", "-").lower(),
            especie.replace("-", " ").lower(),
        ]
        for nome_especie in especie_candidatos:
            if not nome_especie:
                continue
            pasta_anim = base_anim / nome_especie
            if not pasta_anim.exists() or not pasta_anim.is_dir():
                continue
            try:
                frames = carregar_frames(pasta_anim)
            except Exception:
                frames = []
            if frames:
                break

        if not frames:
            pistas = [
                info.get("CaminhoFrames"),
                info.get("caminho_frames"),
                info.get("FramesPath"),
                info.get("frames_path"),
                info.get("SpriteFrames"),
                info.get("sprite_frames"),
            ]
            for pista in pistas:
                if not pista:
                    continue
                pasta = Path(str(pista))
                if pasta.exists() and pasta.is_dir():
                    try:
                        frames = carregar_frames(pasta)
                    except Exception:
                        frames = []
                if frames:
                    break
        p.Frames = [f for f in frames if isinstance(f, pygame.Surface)]
        p._cache_frames_escalados = {}

    def atualizar_animacao(self, dt: float):
        p = self.pokemon
        dt = max(0.0, float(dt or 0.0))
        self.atualizar_efeitos_visuais(dt)
        if not p.Frames:
            return
        if self._animacao_idle_travada():
            p.TimerAnimacao = 0.0
            return
        multiplicador = self._multiplicador_velocidade_idle()
        p.TimerAnimacao += dt * multiplicador
        tempo_frame = max(0.01, float(p.TempoFrame or 0.01))
        while p.TimerAnimacao >= tempo_frame:
            p.TimerAnimacao -= tempo_frame
            p.FrameAtual = (p.FrameAtual + 1) % len(p.Frames)

    def frame_atual_escalado(self, camera):
        p = self.pokemon
        if not p.Frames:
            return None
        tile_px = max(1, int(getattr(camera, "TilePx", 40) or 40)) if camera is not None else 40
        if tile_px not in p._cache_frames_escalados:
            fator_zoom = float(tile_px) / 40.0
            fator = max(0.1, 1.10 * fator_zoom)
            escalados = []
            for frame in p.Frames:
                fw = max(1, int(round(frame.get_width() * fator)))
                fh = max(1, int(round(frame.get_height() * fator)))
                escalado = pygame.transform.smoothscale(frame, (fw, fh)).convert_alpha()
                escalados.append(escalado)
            p._cache_frames_escalados[tile_px] = escalados
        frames = p._cache_frames_escalados.get(tile_px) or []
        if not frames:
            return None
        idx = p.FrameAtual % len(frames)
        return frames[idx]

    def _efeitos_normalizados(self):
        return {_normalizar_nome((e or {}).get("code") or (e or {}).get("nome")) for e in self.EfeitosFormais or []}

    def _possui_efeito_norm(self, nome):
        return _normalizar_nome(nome) in self._efeitos_normalizados()

    def _animacao_idle_travada(self):
        efeitos = self._efeitos_normalizados()
        return any(e in efeitos for e in EFEITOS_TRAVAM_FRAME)

    def _multiplicador_velocidade_idle(self):
        efeitos = self._efeitos_normalizados()
        mult = 1.0
        if any(e in efeitos for e in EFEITOS_IDLE_LENTO):
            mult *= 0.72
        if any(e in efeitos for e in EFEITOS_IDLE_RAPIDO):
            mult *= 1.28
        return mult

    def _furtivo_inimigo_oculto(self):
        if not self._possui_efeito_norm("furtivo"):
            return False
        lado = str(self.Lado or "").strip().lower()
        return lado == "inimigo" or _i(getattr(self, "lado_id", 50), 50) != 50

    def _multiplicador_alpha_efeitos(self):
        if self._possui_efeito_norm("furtivo") and not self._furtivo_inimigo_oculto():
            return 0.48
        return 1.0

    def _offset_efeitos_dinamicos(self, camera=None):
        escala = max(0.75, min(1.8, float(getattr(camera, "TilePx", 40) or 40) / 40.0)) if camera is not None else 1.0
        t = float(self.TempoVisualEfeitos or 0.0)
        ox = 0.0
        oy = 0.0
        if self._possui_efeito_norm("flutuando"):
            oy -= 7.0 * escala + math.sin(t * 2.8) * 2.0 * escala
        if self._possui_efeito_norm("voando"):
            oy -= 10.0 * escala
        if self._possui_efeito_norm("paralisado"):
            ox += math.sin(t * 55.0) * 2.0 * escala
            oy += math.sin(t * 73.0) * 1.0 * escala
        return ox, oy

    def _rotacao_efeitos_dinamicos(self):
        if self._possui_efeito_norm("confuso"):
            return math.sin(float(self.TempoVisualEfeitos or 0.0) * 4.2) * 5.0
        return 0.0

    def _escala_efeitos_dinamicos(self):
        return 1.10 if self._possui_efeito_norm("provocando") else 1.0

    def _estilo_visual_principal(self):
        melhor = None
        melhor_intensidade = -1.0
        for efeito in self.EfeitosFormais or []:
            chave = _normalizar_nome((efeito or {}).get("code") or (efeito or {}).get("nome"))
            estilo = ESTILOS_VISUAIS_EFEITOS.get(chave)
            if not estilo:
                continue
            intensidade = float(estilo.get("intensidade", 0.0) or 0.0)
            if intensidade > melhor_intensidade:
                melhor = estilo
                melhor_intensidade = intensidade
        return melhor

    def _aplicar_filtros_efeitos(self, img):
        estilo = self._estilo_visual_principal()
        if not estilo or not isinstance(img, pygame.Surface):
            return img
        cor = tuple(estilo.get("cor") or (255, 255, 255))
        intensidade = max(0.0, min(1.0, float(estilo.get("intensidade", 0.5) or 0.5) * EFEITO_VISUAL_INTENSIDADE_MULT))
        t = float(self.TempoVisualEfeitos or 0.0)
        out = img.copy()
        w, h = out.get_size()
        pulso = 0.78 + 0.22 * math.sin(t * 3.4)
        alpha = int(68 * intensidade * pulso)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*cor[:3], alpha))
        if sum(cor[:3]) < 48:
            out.blit(overlay, (0, 0))
        else:
            out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self._desenhar_pixels_pulsantes(out, cor[:3], intensidade, t)
        movimento = estilo.get("particulas")
        if movimento:
            self._desenhar_particulas_de_estado(out, cor[:3], str(movimento), intensidade, float(estilo.get("densidade", 1.0) or 1.0), float(estilo.get("vel", 1.0) or 1.0), t)
        self._preservar_alpha_original(out, img)
        return out

    @staticmethod
    def _preservar_alpha_original(destino, origem):
        try:
            alpha_dest = pygame.surfarray.pixels_alpha(destino)
            alpha_orig = pygame.surfarray.pixels_alpha(origem)
            alpha_dest[:] = alpha_orig
            del alpha_dest, alpha_orig
            return
        except Exception:
            pass
        mascara = pygame.mask.from_surface(origem, threshold=1).to_surface(
            setcolor=(255, 255, 255, 255),
            unsetcolor=(255, 255, 255, 0),
        )
        destino.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    @staticmethod
    def _hash_visual(seed):
        return abs(math.sin(seed * 12.9898) * 43758.5453) % 1.0

    def _desenhar_pixels_pulsantes(self, surface, cor, intensidade, tempo):
        w, h = surface.get_size()
        quantidade = max(3, min(24, int((w * h) / 4200)))
        for i in range(quantidade):
            x = int(self._hash_visual(i + len(self.id_batalha) * 7) * max(1, w - 2))
            y = int(self._hash_visual(i * 3 + len(self.Nome) * 11) * max(1, h - 2))
            fase = self._hash_visual(i * 9 + 3) * math.tau
            alpha = int((22 + 62 * (0.5 + 0.5 * math.sin(tempo * 4.6 + fase))) * intensidade)
            tam = 1 + int(self._hash_visual(i * 17 + 5) > 0.62)
            pygame.draw.rect(surface, (*cor, alpha), pygame.Rect(x, y, tam, tam))

    def _desenhar_particulas_de_estado(self, surface, cor, movimento, intensidade, densidade, velocidade, tempo):
        w, h = surface.get_size()
        quantidade = max(2, min(26, int((w * h) / 3200 * densidade)))
        for i in range(quantidade):
            fase = self._hash_visual(i * 13 + len(self.id_batalha))
            progresso = (tempo * velocidade * (0.35 + fase * 0.45) + fase) % 1.0
            x = int(self._hash_visual(i * 5 + 19) * max(1, w - 2))
            if movimento == "sobe":
                y = int(h - progresso * h)
            else:
                y = int(progresso * h)
            osc = math.sin(tempo * 3.2 + i) * 2.0
            alpha = int((52 + 86 * (1.0 - abs(progresso - 0.5) * 1.4)) * intensidade)
            tam = 1 + int(densidade > 1.0 and i % 3 == 0)
            pygame.draw.rect(surface, (*cor, max(0, min(210, alpha))), pygame.Rect(int(x + osc), y, tam, max(1, tam + (1 if movimento == "desce" else 0))))

    def _desenhar_sono(self, surface, camera=None):
        if self.RectAtual.width <= 0 or not self._possui_efeito_norm("dormindo"):
            return
        escala = self._escala_mundo_ui(camera)
        t = float(self.TempoVisualEfeitos or 0.0)
        for i in range(3):
            fase = (t * 0.7 + i * 0.33) % 1.0
            curva = math.sin(fase * math.pi * 2.0 + i) * 13 * escala
            x = self.RectAtual.centerx + self.RectAtual.width * 0.25 + curva
            y = self.RectAtual.top + self.RectAtual.height * 0.15 - fase * 48 * escala
            alpha = int(255 * (1.0 - fase))
            tamanho = max(12, int((13 + fase * 14) * escala))
            self._desenhar_texto(surface, "Z", (x, y), tamanho, (230, 236, 255, alpha), centro=True, negrito=True)

    def _desenhar_flash(self, surface):
        alpha = max(0, min(255, int(self.FlashVisualAlpha or 0)))
        if alpha <= 0 or self.RectAtual.width <= 0:
            return
        overlay = pygame.Surface(self.RectAtual.size, pygame.SRCALPHA)
        pygame.draw.ellipse(overlay, (*tuple(self.FlashVisualCor or (255, 255, 255)), alpha), overlay.get_rect())
        surface.blit(overlay, self.RectAtual.topleft)


    def _sincronizar_efeitos(self, efeitos):
        novos_por_chave = {}
        for efeito in [dict(e) for e in list(efeitos or []) if isinstance(e, dict)]:
            chave = self._chave_efeito(efeito)
            if not chave:
                continue
            if chave in novos_por_chave:
                atual = novos_por_chave[chave]
                atuais = max(0, _i(atual.get("passos_restantes"), 0))
                novos = max(0, _i(efeito.get("passos_restantes"), 0))
                atual["stacks"] = 1
                atual["passos_restantes"] = atuais + novos
                atual["passos_totais"] = max(_i(atual.get("passos_totais"), atuais), atuais) + novos
            else:
                efeito["stacks"] = 1
                novos_por_chave[chave] = efeito
        novos = list(novos_por_chave.values())
        chaves_atuais = {self._chave_efeito(e) for e in self.EfeitosFormais}
        chaves_novas = {self._chave_efeito(e) for e in novos}
        for chave in chaves_novas - chaves_atuais:
            self.AnimacoesEfeitos[chave] = 0.0
        for chave in chaves_atuais - chaves_novas:
            self.EfeitosSaindo[chave] = 0.0
        self.EfeitosFormais = novos[:4]

    def aplicar_efeito_visual(self, efeito):
        if not isinstance(efeito, dict):
            return
        chave = self._chave_efeito(efeito)
        novo = dict(efeito)
        existente = next((e for e in self.EfeitosFormais if self._chave_efeito(e) == chave), None)
        if existente is not None:
            passos_anteriores = max(0, _i(existente.get("passos_restantes"), 0))
            passos_novos = max(0, _i(novo.get("passos_restantes"), 0))
            existente.update(novo)
            existente["stacks"] = 1
            if passos_novos > 0:
                existente["passos_restantes"] = passos_anteriores + passos_novos
                existente["passos_totais"] = max(_i(existente.get("passos_totais"), passos_anteriores), passos_anteriores) + passos_novos
        else:
            novo["stacks"] = 1
            self.EfeitosFormais.append(novo)
        self.EfeitosFormais = self.EfeitosFormais[:4]
        self.AnimacoesEfeitos[chave] = 0.0
        self.EfeitosSaindo.pop(chave, None)

    def atualizar_timer_efeito(self, efeito_code=None, efeito_nome=None, passos_restantes=None):
        alvo = _normalizar_nome(efeito_code or efeito_nome)
        for efeito in self.EfeitosFormais:
            if _normalizar_nome(efeito.get("code") or efeito.get("nome")) == alvo:
                efeito["passos_restantes"] = passos_restantes
                efeito["passos_totais"] = max(_i(efeito.get("passos_totais"), 0), _i(passos_restantes, 0))
                break

    def expirar_efeito_visual(self, efeito_code=None, efeito_nome=None):
        alvo = _normalizar_nome(efeito_code or efeito_nome)
        for efeito in list(self.EfeitosFormais):
            if _normalizar_nome(efeito.get("code") or efeito.get("nome")) == alvo:
                self.EfeitosSaindo[self._chave_efeito(efeito)] = 0.0

    def atualizar_efeitos_visuais(self, dt):
        dt = max(0.0, float(dt or 0.0))
        self.TempoVisualEfeitos = (float(self.TempoVisualEfeitos or 0.0) + dt) % 100000.0
        for chave in list(self.AnimacoesEfeitos):
            self.AnimacoesEfeitos[chave] = min(1.0, float(self.AnimacoesEfeitos.get(chave, 0.0)) + dt * 5.5)
            if self.AnimacoesEfeitos[chave] >= 1.0:
                self.AnimacoesEfeitos.pop(chave, None)
        for chave in list(self.EfeitosSaindo):
            self.EfeitosSaindo[chave] = min(1.0, float(self.EfeitosSaindo.get(chave, 0.0)) + dt * 5.5)
            if self.EfeitosSaindo[chave] >= 1.0:
                self.EfeitosSaindo.pop(chave, None)
                self.EfeitosFormais = [e for e in self.EfeitosFormais if self._chave_efeito(e) != chave]
        restantes = []
        for anim in self.AnimacoesStatus:
            anim["tempo"] = float(anim.get("tempo", 0.0)) + dt
            if float(anim.get("tempo", 0.0)) < float(anim.get("duracao", 0.8)):
                restantes.append(anim)
        self.AnimacoesStatus = restantes

    def animar_variacao_status(self, positivo=True, atributo=None, valor=None):
        self.AnimacoesStatus.append({"positivo": bool(positivo), "atributo": atributo, "valor": valor, "tempo": 0.0, "duracao": 0.8})

    def desenhar_efeitos(self, surface, camera=None):
        if self.RectAtual.width <= 0:
            return
        efeitos = list(self.EfeitosFormais or [])[:4]
        if not efeitos:
            return
        escala_ui = self._escala_mundo_ui(camera)
        raio = max(7, int(round(16 * escala_ui)))
        gap = max(3, int(round(8 * escala_ui)))
        total_w = len(efeitos) * raio * 2 + (len(efeitos) - 1) * gap
        x0 = self.RectAtual.centerx - total_w // 2 + raio
        y = self.RectAtual.bottom + max(8, int(round(18 * escala_ui)))
        fonte_fallback = pygame.font.SysFont("arial", max(7, int(round(11 * escala_ui))), bold=True)
        fonte_stack = pygame.font.SysFont("arial", max(7, int(round(11 * escala_ui))), bold=True)
        fonte_tooltip = pygame.font.SysFont("arial", max(9, int(round(13 * escala_ui))), bold=True)
        mouse = pygame.mouse.get_pos()
        tooltip = None
        for idx, efeito in enumerate(efeitos):
            chave = self._chave_efeito(efeito)
            t_entrada = float(self.AnimacoesEfeitos.get(chave, 1.0))
            t_saida = float(self.EfeitosSaindo.get(chave, 0.0))
            escala = max(0.0, min(1.0, t_entrada)) * (1.0 - max(0.0, min(1.0, t_saida)))
            if escala <= 0.02:
                continue
            cx = x0 + idx * (raio * 2 + gap)
            r = max(2, int(raio * escala))
            negativo = bool(efeito.get("negativo")) or str(efeito.get("tipo") or "").lower() == "negativo"
            cor = (224, 70, 70, 220) if negativo else (72, 190, 104, 220)
            pygame.draw.circle(surface, cor, (cx, y), r)
            self._desenhar_borda_efeito(surface, cx, y, r, efeito, escala_ui)
            icone = self._icone_efeito(efeito.get("nome") or efeito.get("code"))
            if icone is not None and r > 6:
                margem_icone = max(3, int(round(4 * escala_ui)))
                img = pygame.transform.smoothscale(icone, (max(4, r * 2 - margem_icone * 2), max(4, r * 2 - margem_icone * 2)))
                surface.blit(img, img.get_rect(center=(cx, y)))
            else:
                nome = str(efeito.get("nome") or efeito.get("code") or "?")
                txt = fonte_fallback.render(nome[:2].upper(), True, (18, 24, 30))
                surface.blit(txt, txt.get_rect(center=(cx, y)))
            area = pygame.Rect(cx - r, y - r, r * 2, r * 2)
            if area.collidepoint(mouse):
                tooltip = (str(efeito.get("nome") or efeito.get("code") or "Efeito"), negativo, cx, y + r + max(4, int(round(6 * escala_ui))))
        if tooltip is not None:
            nome, negativo, cx, ty = tooltip
            cor_txt = (132, 218, 255) if not negativo else (190, 126, 255)
            txt = fonte_tooltip.render(nome, True, cor_txt)
            fundo = pygame.Rect(0, 0, txt.get_width() + max(6, int(round(10 * escala_ui))), txt.get_height() + max(4, int(round(6 * escala_ui))))
            fundo.midtop = (int(cx), int(ty))
            raio_tooltip = max(4, int(round(6 * escala_ui)))
            pygame.draw.rect(surface, (13, 16, 24, 232), fundo, border_radius=raio_tooltip)
            pygame.draw.rect(surface, cor_txt, fundo, max(1, int(round(escala_ui))), border_radius=raio_tooltip)
            surface.blit(txt, txt.get_rect(center=fundo.center))

    def _desenhar_borda_efeito(self, surface, cx, y, r, efeito, escala_ui=1.0):
        rect = pygame.Rect(cx - r, y - r, r * 2, r * 2)
        largura = max(1, int(round(2 * escala_ui)))
        pygame.draw.ellipse(surface, (245, 250, 255, 235), rect, largura)
        pygame.draw.ellipse(surface, (12, 14, 22, 120), rect.inflate(-largura * 2, -largura * 2), max(1, largura // 2))
        restantes = max(0, _i(efeito.get("passos_restantes"), 0))
        if restantes > 0:
            texto = str(restantes)
            tamanho = max(8, int(round(11 * escala_ui)))
            pos = (cx, y + r - max(1, int(round(2 * escala_ui))))
            self._desenhar_texto(surface, texto, pos, tamanho, (255, 255, 255, 245), centro=True, negrito=True, contorno=(12, 14, 22, 235))

    def desenhar_animacoes_status(self, surface, camera=None, arena=None):
        if self.RectAtual.width <= 0 or not self.AnimacoesStatus:
            return
        base_x, base_y = self.RectAtual.center
        if camera is not None and arena is not None and self.CentroTelaOverride is None and self.CentroMundoOverride is None:
            centro = arena.centro_area(self.AreaId)
            if centro is not None:
                base_x, base_y = camera.mundo_para_tela_px(centro)
        escala = max(0.75, min(1.8, float(getattr(camera, "TilePx", 40) or 40) / 40.0)) if camera is not None else 1.0
        for anim in list(self.AnimacoesStatus):
            t = max(0.0, min(1.0, float(anim.get("tempo", 0.0)) / max(0.001, float(anim.get("duracao", 0.8)))))
            positivo = bool(anim.get("positivo", True))
            cor = (72, 190, 104, int(220 * (1.0 - t))) if positivo else (224, 70, 70, int(220 * (1.0 - t)))
            direcao = -1 if positivo else 1
            y_base = float(base_y) - 22 * escala + direcao * 26 * escala * t
            for i in range(3):
                x = float(base_x) + (i - 1) * 18 * escala
                y = y_base + (i % 2) * 7 * escala
                if positivo:
                    pts = [(x, y - 11 * escala), (x - 8 * escala, y + 5 * escala), (x - 3 * escala, y + 5 * escala), (x - 3 * escala, y + 14 * escala), (x + 3 * escala, y + 14 * escala), (x + 3 * escala, y + 5 * escala), (x + 8 * escala, y + 5 * escala)]
                else:
                    pts = [(x, y + 11 * escala), (x - 8 * escala, y - 5 * escala), (x - 3 * escala, y - 5 * escala), (x - 3 * escala, y - 14 * escala), (x + 3 * escala, y - 14 * escala), (x + 3 * escala, y - 5 * escala), (x + 8 * escala, y - 5 * escala)]
                pygame.draw.polygon(surface, cor, pts)
            self._desenhar_cartucho_variacao_status(surface, anim, base_x, y_base - 30 * escala, escala, t)

    def _desenhar_cartucho_variacao_status(self, surface, anim, base_x, base_y, escala, t):
        atributo = anim.get("atributo")
        valor = anim.get("valor")
        if not atributo and valor is None:
            return
        positivo = bool(anim.get("positivo", True))
        alpha = int(255 * max(0.0, min(1.0, 1.0 - max(0.0, t - 0.60) / 0.40)))
        texto = self._formatar_variacao(valor, positivo=positivo)
        cor_fundo = (55, 136, 232, alpha) if positivo else (126, 68, 190, alpha)
        tamanho = max(12, int(round(16 * escala)))
        fonte = pygame.font.SysFont("arial", tamanho, bold=True)
        txt = fonte.render(texto, True, (255, 255, 255))
        txt.set_alpha(alpha)
        icone = self._icone_atributo(atributo)
        icon_lado = max(16, int(round(22 * escala))) if icone is not None else 0
        pad_x = max(7, int(round(9 * escala)))
        pad_y = max(3, int(round(4 * escala)))
        gap = max(3, int(round(5 * escala))) if icone is not None else 0
        rect = pygame.Rect(0, 0, txt.get_width() + icon_lado + gap + pad_x * 2, max(txt.get_height(), icon_lado) + pad_y * 2)
        rect.center = (int(base_x), int(base_y))
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, cor_fundo, surf.get_rect(), border_radius=max(6, int(8 * escala)))
        pygame.draw.rect(surf, (255, 255, 255, alpha), surf.get_rect(), max(1, int(2 * escala)), border_radius=max(6, int(8 * escala)))
        x = pad_x
        if icone is not None:
            icon = pygame.transform.smoothscale(icone, (icon_lado, icon_lado)).convert_alpha()
            icon.set_alpha(alpha)
            surf.blit(icon, icon.get_rect(midleft=(x, surf.get_height() // 2)))
            x += icon_lado + gap
        surf.blit(txt, (x, (surf.get_height() - txt.get_height()) // 2))
        surface.blit(surf, rect.topleft)

    @staticmethod
    def _formatar_variacao(valor, positivo=True):
        try:
            num = float(valor)
        except (TypeError, ValueError):
            bruto = str(valor or "")
            if bruto.startswith(("+", "-")):
                return bruto
            return ("+" if positivo else "-") + bruto
        sinal = "+" if num >= 0 else "-"
        valor_abs = abs(num)
        corpo = str(int(round(valor_abs))) if abs(valor_abs - round(valor_abs)) < 0.001 else f"{valor_abs:.1f}".rstrip("0").rstrip(".")
        return f"{sinal}{corpo}"

    def _desenhar_texto(self, surface, texto, pos, tamanho, cor, centro=True, negrito=True, contorno=None):
        x, y = pos
        if _TextoPrefab is not None:
            tentativas = [
                ((str(texto), int(x), int(y), int(tamanho)), {"cor": cor}),
                ((str(texto), int(x), int(y)), {"tamanho": int(tamanho), "cor": cor}),
                ((str(texto),), {"x": int(x), "y": int(y), "tamanho": int(tamanho), "cor": cor}),
            ]
            for args, kwargs in tentativas:
                try:
                    obj = _TextoPrefab(*args, **kwargs)
                    if hasattr(obj, "desenhar"):
                        obj.desenhar(surface)
                        return
                    if hasattr(obj, "draw"):
                        obj.draw(surface)
                        return
                except Exception:
                    continue
        fonte = pygame.font.SysFont("arial", int(tamanho), bold=bool(negrito))
        txt = fonte.render(str(texto), True, tuple(cor[:3]))
        if len(cor) >= 4:
            txt.set_alpha(max(0, min(255, int(cor[3]))))
        rect = txt.get_rect(center=(int(x), int(y))) if centro else txt.get_rect(topleft=(int(x), int(y)))
        if contorno:
            sombra = fonte.render(str(texto), True, tuple(contorno[:3]))
            if len(contorno) >= 4:
                sombra.set_alpha(max(0, min(255, int(contorno[3]))))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                surface.blit(sombra, rect.move(dx, dy))
        surface.blit(txt, rect)

    @classmethod
    def _icone_atributo(cls, nome):
        chave = _normalizar_nome(nome)
        if not chave:
            return None
        aliases = {"amp": "amplificacao", "amplificacao": "amplificacao", "dur": "durabilidade", "durabilidade": "durabilidade"}
        busca = aliases.get(chave, chave)
        cache = getattr(cls, "_icones_atributos_cache", None)
        if cache is None:
            cache = {}
            setattr(cls, "_icones_atributos_cache", cache)
        if busca in cache:
            return cache[busca]
        base = Path("Recursos") / "Visual" / "Icones" / "Atributos"
        escolhido = None
        try:
            for caminho in base.iterdir():
                if caminho.is_file() and _normalizar_nome(caminho.stem) == busca:
                    escolhido = caminho
                    break
        except Exception:
            escolhido = None
        if escolhido is not None:
            try:
                cache[busca] = pygame.image.load(str(escolhido)).convert_alpha()
            except Exception:
                cache[busca] = None
        else:
            cache[busca] = None
        return cache[busca]

    @staticmethod
    def _chave_efeito(efeito):
        return _normalizar_nome((efeito or {}).get("code") or (efeito or {}).get("nome"))

    @classmethod
    def _icone_efeito(cls, nome):
        chave = _normalizar_nome(nome)
        if not chave:
            return None
        cache = getattr(cls, "_icones_cache_real", None)
        if cache is None:
            cache = {}
            setattr(cls, "_icones_cache_real", cache)
        if chave in cache:
            return cache[chave]
        base = Path("Recursos") / "Visual" / "Icones" / "Efeitos"
        escolhido = None
        try:
            for caminho in base.iterdir():
                if caminho.is_file() and _normalizar_nome(caminho.stem) == chave:
                    escolhido = caminho
                    break
        except Exception:
            escolhido = None
        if escolhido is not None:
            try:
                cache[chave] = pygame.image.load(str(escolhido)).convert_alpha()
            except Exception:
                cache[chave] = None
        else:
            cache[chave] = None
        return cache[chave]

