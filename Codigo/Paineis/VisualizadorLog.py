from __future__ import annotations

from typing import Dict, List

import pygame

from Codigo.ModulosGerais.Auxiliares import criar_botao_expandir, renderizar_botao_expandir
from Codigo.Prefabs.Botao import Botao
from Codigo.Prefabs.Painel import PainelRolavel
from Codigo.Prefabs.Texto import Texto, TextoRegistroLog
from Codigo.Prefabs.Tooltip import Tooltip


class _ListaRegistrosLog(PainelRolavel):
    def __init__(self, rect):
        super().__init__(
            rect,
            area_real=(0, 0, rect[2], rect[3]),
            cor_fundo=(0, 0, 0, 0),
            cor_borda=(0, 0, 0, 0),
            borda=0,
            raio=14,
            velocidade_scroll=34,
        )
        self.Padding = 10
        self.Gap = 10
        self.Registros: list[dict[str, object]] = []
        self._assinatura_registros = None
        self._layout_registros: list[dict[str, object]] = []
        self._areas_tooltip: list[dict[str, object]] = []
        self._texto_medidor = TextoRegistroLog(
            rect=(0, 0, 10, 10),
            linhas=10,
            caracteres_por_linha=120,
            style={
                "size": 16,
                "color": (234, 240, 250),
                "outline": True,
                "outline_color": (7, 10, 18),
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self._texto_fase = Texto(
            "",
            style={
                "size": 12,
                "align": "topleft",
                "color": (165, 185, 214),
                "outline": True,
                "outline_color": (7, 10, 18),
                "outline_thickness": 1,
                "shadow": False,
            },
        )

    def configurar_rect(self, rect):
        novo = pygame.Rect(rect)
        if self.rect == novo:
            return
        self.rect = novo
        self.atualizar_area_real()
        self.marcar_sujo()

    def definir_registros(self, registros: List[Dict[str, object]]):
        novos = [dict(item) for item in list(registros or []) if isinstance(item, dict)]
        assinatura = self._assinar_registros(novos)
        if self._assinatura_registros == assinatura:
            return
        self.Registros = novos
        self._assinatura_registros = assinatura
        self.atualizar_area_real()
        self.marcar_sujo()

    @staticmethod
    def _assinar_registros(registros: list[dict[str, object]]) -> tuple:
        assinatura = []
        for registro in registros:
            assinatura.append(
                (
                    str(registro.get("tipo") or ""),
                    int(registro.get("tick", 0) or 0),
                    str(registro.get("fase_label") or ""),
                    tuple(
                        (
                            str(segmento.get("texto") or ""),
                            str(segmento.get("atributo") or ""),
                            str(segmento.get("titulo_tooltip") or ""),
                            str(segmento.get("descricao_tooltip") or ""),
                        )
                        for segmento in list(registro.get("segmentos") or [])
                        if isinstance(segmento, dict)
                    ),
                )
            )
        return tuple(assinatura)

    def atualizar_area_real(self):
        largura = max(160, self.rect.width)
        altura = self.Padding
        self._layout_registros = []
        y = self.Padding
        for registro in self.Registros:
            altura_registro = self._altura_registro(registro)
            self._layout_registros.append({"registro": registro, "y": y, "altura": altura_registro})
            altura += altura_registro + self.Gap
            y += altura_registro + self.Gap
        altura = max(self.rect.height, altura + self.Padding - self.Gap)
        self.definir_area_real(largura, altura)

    def _largura_cartao(self) -> int:
        return max(120, self.rect.width - self.Padding * 2 - 8)

    def _altura_registro(self, registro: Dict[str, object]) -> int:
        largura = self._largura_cartao() - 28
        self._texto_medidor.Rect = pygame.Rect(0, 0, largura, 10)
        self._texto_medidor.set_segmentos([dict(item) for item in list(registro.get("segmentos") or []) if isinstance(item, dict)])
        altura_texto = max(20, self._texto_medidor.medir_altura())
        altura = 18 + altura_texto + 18
        return max(58, altura)

    def draw(self, tela):
        tela.fill((0, 0, 0, 0))
        self._areas_tooltip = []

        largura_cartao = self._largura_cartao()
        topo_visivel = max(0, int(self.ScrollY) - 80)
        base_visivel = max(0, int(self.ScrollY) + int(self.rect.height) + 80)

        for item_layout in self._layout_registros:
            registro = dict(item_layout.get("registro") or {})
            y = int(item_layout.get("y", 0) or 0)
            altura = int(item_layout.get("altura", 0) or 0)
            if (y + altura) < topo_visivel or y > base_visivel:
                continue
            rect = pygame.Rect(self.Padding, y, largura_cartao, altura)

            fundo = tuple(registro.get("cor_fundo") or (19, 28, 46, 228))
            borda = tuple(registro.get("cor_borda") or (96, 124, 176))
            faixa = tuple(registro.get("cor_faixa") or borda)

            cartao = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(cartao, fundo, cartao.get_rect(), border_radius=14)
            pygame.draw.rect(cartao, borda, cartao.get_rect(), 2, border_radius=14)
            pygame.draw.rect(cartao, faixa, pygame.Rect(0, 0, 6, rect.height), border_radius=14)
            tela.blit(cartao, rect.topleft)

            fase = ""
            tick = int(registro.get("tick", 0) or 0)
            if fase:
                self._texto_fase.set_text(f"{fase}  •  Tick {tick}")
                self._texto_fase.set_pos((rect.x + 16, rect.y + 10))
                self._texto_fase.draw(tela)

            self._texto_medidor.Rect = pygame.Rect(rect.x + 16, rect.y + 14, rect.width - 32, rect.height - 26)
            self._texto_medidor.set_segmentos([dict(item) for item in list(registro.get("segmentos") or []) if isinstance(item, dict)])
            self._texto_medidor.draw(tela)
            for area in self._texto_medidor.obter_areas_tooltip():
                rect_area = area.get("rect")
                if not isinstance(rect_area, pygame.Rect):
                    continue
                self._areas_tooltip.append(
                    {
                        "rect": pygame.Rect(rect_area),
                        "tooltip": str(area.get("tooltip") or ""),
                        "titulo": str(area.get("titulo") or ""),
                        "descricao": str(area.get("descricao") or ""),
                    }
                )

    def tooltip_no_mouse(self, mouse_pos) -> dict[str, object] | None:
        if not self.rect.collidepoint(mouse_pos):
            return None
        for area in reversed(self._areas_tooltip):
            rect_local = area.get("rect")
            if not isinstance(rect_local, pygame.Rect):
                continue
            rect_tela = pygame.Rect(
                self.rect.x + rect_local.x - self.ScrollX,
                self.rect.y + rect_local.y - self.ScrollY,
                rect_local.width,
                rect_local.height,
            )
            if rect_tela.collidepoint(mouse_pos) and rect_tela.colliderect(self.rect):
                saida = dict(area)
                saida["rect_tela"] = rect_tela
                return saida
        return None


class VisualizadorLog:
    _FASES_LABEL = {
        "inicializacao": "Abertura",
        "segmentacao": "Execução",
        "passiva": "Passiva",
        "finalizacao": "Fechamento",
    }
    _CORES_TIPO = {
        "acao": ((22, 32, 56, 235), (96, 151, 230), (126, 179, 255)),
        "movimento": ((18, 38, 50, 235), (81, 174, 196), (114, 210, 230)),
        "objeto": ((28, 32, 58, 235), (144, 126, 216), (176, 153, 248)),
        "dano": ((58, 26, 30, 238), (212, 96, 96), (243, 132, 132)),
        "cura": ((20, 50, 36, 238), (92, 196, 124), (130, 224, 156)),
        "barreira": ((22, 40, 60, 238), (92, 158, 224), (132, 188, 255)),
        "energia": ((18, 34, 62, 238), (78, 128, 226), (108, 156, 245)),
        "efeito": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "fim_turno": ((36, 36, 46, 238), (154, 164, 184), (190, 198, 216)),
        "troca": ((36, 44, 54, 238), (154, 184, 212), (191, 220, 250)),
        "ataque_usado": ((22, 32, 56, 235), (96, 151, 230), (126, 179, 255)),
        "pokemon_sofreu_dano": ((58, 26, 30, 238), (212, 96, 96), (243, 132, 132)),
        "pokemon_recebeu_cura": ((20, 50, 36, 238), (92, 196, 124), (130, 224, 156)),
        "pokemon_gastou_energia": ((18, 34, 62, 238), (78, 128, 226), (108, 156, 245)),
        "pokemon_ganhou_energia": ((18, 34, 62, 238), (78, 128, 226), (108, 156, 245)),
        "barreira_absorveu": ((22, 40, 60, 238), (92, 158, 224), (132, 188, 255)),
        "pokemon_ganhou_barreira": ((22, 40, 60, 238), (92, 158, 224), (132, 188, 255)),
        "pokemon_recebeu_efeito": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "efeito_tickou": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "efeito_expirou": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "pokemon_moveu": ((18, 38, 50, 235), (81, 174, 196), (114, 210, 230)),
        "pokemon_trocou_posicao": ((36, 44, 54, 238), (154, 184, 212), (191, 220, 250)),
        "pokemon_trocou_reserva": ((36, 44, 54, 238), (154, 184, 212), (191, 220, 250)),
        "pokemon_morreu": ((58, 26, 30, 238), (212, 96, 96), (243, 132, 132)),
        "captura_batalha_resultado": ((44, 31, 64, 238), (168, 126, 224), (214, 170, 255)),
    }

    def __init__(self, controlador=None) -> None:
        self._controlador = controlador
        self._aberto = False
        self._animacao = 0.0
        self._cache_tamanho = None
        self._rect_painel = pygame.Rect(0, 0, 0, 0)
        self._rect_tab = pygame.Rect(0, 0, 0, 0)
        self._rodada_selecionada = 1
        self._rodada_manual = False
        self._estado_logs: Dict[str, object] = {}

        self._texto_titulo = Texto(
            "Rodada 1",
            style={
                "size": 21,
                "align": "midleft",
                "color": (244, 248, 255),
                "outline": True,
                "outline_color": (6, 10, 18),
                "outline_thickness": 2,
                "shadow": False,
            },
        )
        self._texto_subtitulo = Texto(
            "",
            style={
                "size": 13,
                "align": "topleft",
                "color": (172, 188, 214),
                "outline": True,
                "outline_color": (6, 10, 18),
                "outline_thickness": 1,
                "shadow": False,
            },
        )
        self._tooltip = Tooltip("", largura_max=360, padding=10, raio=12, style={"size": 14})
        self._lista = _ListaRegistrosLog((0, 0, 10, 10))

        estilo_seta = {
            "radius": 9,
            "border_width": 2,
            "bg": (25, 38, 60),
            "bg_hover": (39, 58, 88),
            "bg_pressed": (16, 26, 42),
            "border": (126, 156, 208),
            "border_hover": (220, 236, 255),
            "hover_scale": 1.02,
            "press_scale": 0.98,
            "text_style": {
                "size": 20,
                "color": (245, 248, 255),
                "align": "center",
                "outline": True,
                "outline_color": (6, 10, 18),
                "outline_thickness": 2,
                "shadow": False,
            },
        }
        self._botao_prev = Botao(pygame.Rect(0, 0, 34, 34), "<", execute=lambda _jogo, _botao: self._navegar(-1), style=estilo_seta)
        self._botao_next = Botao(pygame.Rect(0, 0, 34, 34), ">", execute=lambda _jogo, _botao: self._navegar(1), style=estilo_seta)
        self._botao_tab = criar_botao_expandir(execute=lambda _jogo, _botao: self._alternar(), rect=(0, 0, 44, 118), style={"radius": 12, "hover_scale": 1.01})

    @staticmethod
    def _aprox(a: float, b: float, tolerancia: float = 0.001) -> bool:
        return abs(float(a) - float(b)) <= float(tolerancia)

    @staticmethod
    def _numero(valor, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @classmethod
    def _formatar_numero(cls, valor: object) -> str:
        numero = cls._numero(valor, 0.0)
        if cls._aprox(numero, round(numero)):
            return str(int(round(numero)))
        return f"{numero:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _nome_pokemon(evento: Dict[str, object], chave_nome: str, chave_id: str, fallback: str = "Combatente") -> str:
        nome = str(evento.get(chave_nome) or "").strip()
        if nome:
            return nome
        bruto = str(evento.get(chave_id) or "").strip()
        return bruto or fallback

    @staticmethod
    def _formatar_posicao(posicao) -> str:
        if isinstance(posicao, (list, tuple)) and len(posicao) == 2:
            try:
                return f"({float(posicao[0]):.1f}, {float(posicao[1]):.1f})"
            except (TypeError, ValueError):
                return str(tuple(posicao))
        return "posição desconhecida"

    def _segmento(self, texto: object, *, atributo: str | None = None, titulo: str = "", descricao: str = "", tooltip: str = "") -> dict[str, object]:
        return {
            "texto": str(texto or ""),
            "atributo": str(atributo or ""),
            "titulo_tooltip": str(titulo or ""),
            "descricao_tooltip": str(descricao or ""),
            "tooltip": str(tooltip or ""),
        }

    def _atributo_dano(self, evento: Dict[str, object]) -> str:
        dano_tipo = str(evento.get("dano_tipo") or evento.get("categoria") or "").strip().casefold()
        if dano_tipo in {"especial", "spa", "magico"}:
            return "spa"
        return "atk"

    def _tooltip_valor_simples(self, titulo: str, linhas: list[str]) -> tuple[str, str]:
        descricao = "\n".join([str(linha) for linha in linhas if str(linha or "").strip()])
        return (titulo, descricao)

    def _tooltip_calculo(self, titulo: str, evento: Dict[str, object], fallback: list[str]) -> tuple[str, str]:
        calculo = [str(linha) for linha in list(evento.get("calculo") or []) if str(linha or "").strip()]
        return self._tooltip_valor_simples(titulo, calculo or fallback)

    def _tooltip_dano(self, evento: Dict[str, object]) -> tuple[str, str]:
        if isinstance(evento.get("calculo"), list) and evento.get("calculo"):
            return self._tooltip_valor_simples("Detalhes do dano", [str(linha) for linha in evento.get("calculo")])
        detalhes = dict(evento.get("detalhes") or {})
        linhas: list[str] = []

        def adicionar(label: str, chave: str, *, sempre: bool = False, esconder_zero: bool = False, esconder_identidade: bool = False):
            if chave not in detalhes:
                return
            valor = self._numero(detalhes.get(chave), 0.0)
            if esconder_zero and self._aprox(valor, 0.0):
                return
            if esconder_identidade and self._aprox(valor, 1.0):
                return
            if (not sempre) and esconder_zero and self._aprox(valor, 0.0):
                return
            linhas.append(f"{label}: {self._formatar_numero(valor)}")

        adicionar("Dano Bruto", "dano_bruto", esconder_zero=True)
        adicionar("Bônus de Intensidade", "bonus_intensidade", esconder_identidade=True)
        adicionar("Multiplicador de Dano Causado", "multiplicador_dano_causado", esconder_identidade=True)
        adicionar("Multiplicador Crítico", "multiplicador_critico", esconder_identidade=True)
        adicionar("Defesa Bruta", "defesa_base", sempre=True)
        adicionar("Perfuração", "perfuracao", esconder_zero=True)
        adicionar("Defesa Reduzida", "defesa_reduzida_por_perfuracao", esconder_zero=True)
        adicionar("Defesa Aplicada", "defesa_aplicada", sempre=True)
        adicionar("Dano Pós Defesa", "dano_pos_defesa", sempre=True)
        adicionar("Multiplicador de Tipo", "multiplicador_tipo", esconder_identidade=True)
        adicionar("Dano Pós Tipo", "dano_pos_tipo", sempre=True)
        adicionar("Multiplicador de Hook", "multiplicador_hook", esconder_identidade=True)
        adicionar("Delta de Hook", "delta_hook", esconder_zero=True)
        adicionar("Multiplicador de Dano Recebido", "multiplicador_dano_recebido", esconder_identidade=True)
        linhas.append(f"Dano Final: {self._formatar_numero(evento.get('dano', 0.0))}")
        return self._tooltip_valor_simples("Detalhes do dano", linhas)

    def _tooltip_vida(self, titulo: str, valor: object, antes: object, depois: object) -> tuple[str, str]:
        return self._tooltip_valor_simples(
            titulo,
            [
                f"Valor aplicado: {self._formatar_numero(valor)}",
                f"Antes: {self._formatar_numero(antes)}",
                f"Depois: {self._formatar_numero(depois)}",
            ],
        )

    def _tooltip_variacao_atributo(self, evento: Dict[str, object]) -> tuple[str, str]:
        atributo = str(evento.get("atributo") or evento.get("stat") or evento.get("chave") or "Atributo")
        calculo = [str(linha) for linha in list(evento.get("calculo") or []) if str(linha or "").strip()]
        if not calculo:
            calculo = [
                f"Valor inicial = {self._formatar_numero(evento.get('valor_antes', 0.0))}",
                f"Variacao = {self._formatar_numero(evento.get('valor', evento.get('variacao', 0.0)))}",
                f"Valor final = {self._formatar_numero(evento.get('valor_depois', 0.0))}",
            ]
        return self._tooltip_valor_simples(f"Detalhes de {atributo}", calculo)

    def _tooltip_barreira(self, valor: object, total: object) -> tuple[str, str]:
        return self._tooltip_valor_simples(
            "Detalhes da barreira",
            [
                f"Barreira ganha: {self._formatar_numero(valor)}",
                f"Barreira total: {self._formatar_numero(total)}",
            ],
        )

    def _tooltip_energia(self, valor: object, total: object, motivo: str = "") -> tuple[str, str]:
        linhas = [
            f"Variação de energia: {self._formatar_numero(valor)}",
            f"Energia atual: {self._formatar_numero(total)}",
        ]
        if motivo:
            linhas.append(f"Motivo: {motivo}")
        return self._tooltip_valor_simples("Detalhes da energia", linhas)

    def _tooltip_captura(self, evento: Dict[str, object]) -> tuple[str, str]:
        checks = ["OK" if bool(v) else "falha" for v in list(evento.get("checagens") or [])]
        return self._tooltip_valor_simples(
            "Detalhes da captura",
            [
                f"Chance por check: {self._formatar_numero(evento.get('chance_check', 0.0))}%",
                f"Chance real em 3 checks: {self._formatar_numero(evento.get('chance_real_3_checks', 0.0))}%",
                f"Dificuldade de batalha: {self._formatar_numero(evento.get('dificuldade_batalha', 0.0))}",
                f"Poder total: {self._formatar_numero(evento.get('poder_total', 0.0))}",
                f"Checks: {', '.join(checks) if checks else 'sem checks'}",
            ],
        )

    def _registro_placeholder(self, mensagem: str, subtitulo: str = "Sem registros") -> dict[str, object]:
        return {
            "tipo": "placeholder",
            "tick": 0,
            "fase_label": subtitulo,
            "cor_fundo": (20, 28, 44, 220),
            "cor_borda": (90, 112, 152),
            "cor_faixa": (126, 154, 204),
            "segmentos": [self._segmento(mensagem)],
        }

    def _cores_evento(self, tipo: str, evento: Dict[str, object]):
        cores = {
            "laranja": ((82, 43, 18, 238), (232, 126, 46), (255, 158, 76)),
            "roxo": ((48, 28, 70, 238), (168, 104, 224), (206, 150, 255)),
            "azul": ((18, 42, 68, 238), (74, 156, 235), (122, 202, 255)),
            "verde": ((18, 58, 36, 238), (72, 190, 104), (124, 230, 152)),
            "amarelo": ((72, 60, 22, 238), (218, 184, 70), (255, 222, 112)),
            "vermelho": ((82, 26, 30, 238), (226, 70, 78), (255, 126, 132)),
            "rosa": ((72, 32, 58, 238), (224, 104, 172), (255, 158, 210)),
            "marrom": ((58, 42, 30, 238), (166, 118, 78), (210, 158, 112)),
            "cinza": ((42, 46, 54, 238), (132, 142, 156), (176, 186, 202)),
        }
        if tipo == "ataque_resumo":
            impactos = [dict(item) for item in list(evento.get("impactos") or []) if isinstance(item, dict)]
            danos = [i for i in impactos if str(i.get("tipo") or "") in {"pokemon_sofreu_dano", "barreira_absorveu"}]
            if any(bool(i.get("critico", False)) for i in danos):
                return cores["vermelho"]
            if any(str(i.get("tipo") or "") == "pokemon_recebeu_efeito" and str(i.get("tipo_efeito") or i.get("tipo") or "").lower() == "negativo" for i in impactos):
                return cores["roxo"]
            if danos:
                if any(str(i.get("categoria") or "").lower() in {"especial", "spa", "magico"} for i in danos):
                    return cores["roxo"]
                return cores["laranja"]
            if any(str(i.get("tipo") or "") in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"} for i in impactos):
                return cores["verde"] if any(not bool(i.get("negativo", False)) for i in impactos) else cores["roxo"]
            if any(str(i.get("tipo") or "") in {"pokemon_recebeu_cura", "pokemon_ganhou_barreira", "pokemon_recebeu_efeito"} for i in impactos):
                return cores["rosa"]
            return cores["cinza"]
        if tipo in {"pokemon_moveu", "movimento"}:
            return cores["azul"]
        if tipo in {"pokemon_trocou_posicao", "pokemon_trocou_reserva", "troca"}:
            return cores["verde"]
        if tipo in {"efeito_expirou", "clima_expirou"}:
            return cores["amarelo"]
        if tipo in {"passiva", "passivo"}:
            return cores["marrom"]
        if tipo == "pokemon_morreu":
            return cores["vermelho"]
        if tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            return cores["roxo"] if bool(evento.get("negativo", False)) else cores["verde"]
        if tipo in {"acao_falhou", "ataque_errou", "ataque_sem_alvo_real"}:
            return cores["cinza"]
        if tipo == "captura_batalha_resultado":
            return cores["verde"] if bool(evento.get("capturado", False)) else cores["roxo"]
        return self._CORES_TIPO.get(tipo, cores["cinza"])

    def _registro_evento(self, evento: Dict[str, object], tick: int, fase: str) -> dict[str, object]:
        if isinstance(evento.get("dados"), dict):
            dados = dict(evento.get("dados") or {})
            if isinstance(dados.get("dados"), dict):
                for chave, valor in dict(dados.get("dados") or {}).items():
                    dados.setdefault(chave, valor)
            for chave, valor in dados.items():
                evento.setdefault(chave, valor)
        tipo = str(evento.get("tipo") or "").strip().casefold()
        executor = self._nome_pokemon(evento, "executor_nome", "executor_id")
        alvo = self._nome_pokemon(evento, "alvo_nome", "alvo_id")
        pokemon = self._nome_pokemon(evento, "pokemon_nome", "pokemon_id")

        if tipo == "ataque_resumo":
            base = dict(evento.get("base") or {})
            usuario = str(base.get("usuario_nome") or pokemon)
            ataque = str(base.get("ataque_nome") or "Ataque")
            area = str(base.get("area_alvo") or base.get("area_alvo_real") or "").strip()
            segmentos = [self._segmento(usuario), self._segmento(" usou "), self._segmento(ataque)]
            impactos = [dict(item) for item in list(evento.get("impactos") or []) if isinstance(item, dict)]
            falhas = [dict(item) for item in list(evento.get("falhas") or []) if isinstance(item, dict)]
            if impactos:
                tipos_attr = {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}
                if all(str(impacto.get("tipo") or "").strip().casefold() in tipos_attr for impacto in impactos):
                    for idx, impacto in enumerate(impactos):
                        atributo = str(impacto.get("atributo") or "Atributo")
                        valor = self._numero(impacto.get("valor", impacto.get("variacao", 0.0)), 0.0)
                        verbo = "aumentou" if valor >= 0 else "diminuiu"
                        mesmo_alvo = str(impacto.get("origem_id") or impacto.get("usuario_id") or base.get("usuario_id") or "") == str(impacto.get("alvo_id") or impacto.get("pokemon_id") or "")
                        alvo_nome = str(impacto.get("alvo_nome") or impacto.get("pokemon_nome") or "alvo")
                        alvo_txt = f"sua propria {atributo}" if mesmo_alvo else f"{atributo} de {alvo_nome}"
                        titulo, descricao = self._tooltip_variacao_atributo(impacto)
                        segmentos.append(self._segmento(" e " if idx == 0 else ", e "))
                        segmentos.append(self._segmento(f"{verbo} {alvo_txt} para "))
                        segmentos.append(self._segmento(self._formatar_numero(impacto.get("valor_depois", 0.0)), atributo=atributo, titulo=titulo, descricao=descricao))
                else:
                    segmentos.append(self._segmento(" e atingiu "))
                    partes = []
                    for impacto in impactos:
                        alvo_nome = str(impacto.get("alvo_nome") or impacto.get("pokemon_nome") or impacto.get("efeito_nome") or "alvo")
                        itipo = str(impacto.get("tipo") or "").strip().casefold()
                        if itipo == "pokemon_sofreu_dano":
                            titulo, descricao = self._tooltip_dano(impacto)
                            partes.append([self._segmento(alvo_nome), self._segmento(" causando "), self._segmento(self._formatar_numero(impacto.get("valor", 0)), atributo=self._atributo_dano(impacto), titulo=titulo, descricao=descricao), self._segmento(" de dano")])
                        elif itipo == "barreira_absorveu":
                            titulo, descricao = self._tooltip_calculo("Detalhes da barreira", impacto, [f"Barreira absorveu: {self._formatar_numero(impacto.get('dano_barreira', 0))}"])
                            partes.append([self._segmento(alvo_nome), self._segmento(" absorvendo "), self._segmento(self._formatar_numero(impacto.get("dano_barreira", 0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" na barreira")])
                        elif itipo == "pokemon_recebeu_cura":
                            titulo, descricao = self._tooltip_calculo("Detalhes da cura", impacto, [f"Cura final = {self._formatar_numero(impacto.get('valor', 0))}"])
                            partes.append([self._segmento(alvo_nome), self._segmento(" curando "), self._segmento(self._formatar_numero(impacto.get("valor", 0)), atributo="vida", titulo=titulo, descricao=descricao), self._segmento(" de vida")])
                        elif itipo == "pokemon_ganhou_barreira":
                            titulo, descricao = self._tooltip_calculo("Detalhes da barreira", impacto, [f"Barreira final = {self._formatar_numero(impacto.get('valor', 0))}"])
                            partes.append([self._segmento(alvo_nome), self._segmento(" ganhando "), self._segmento(self._formatar_numero(impacto.get("valor", 0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" de barreira")])
                        elif itipo == "pokemon_recebeu_efeito":
                            efeito = str(impacto.get("efeito_nome") or "efeito")
                            passos = impacto.get("passos_restantes", "?")
                            partes.append([self._segmento(alvo_nome), self._segmento(" recebendo "), self._segmento(efeito), self._segmento(f" por {passos} passos")])
                        elif itipo in tipos_attr:
                            atributo = str(impacto.get("atributo") or "Atributo")
                            valor = self._numero(impacto.get("valor", impacto.get("variacao", 0.0)), 0.0)
                            acao_txt = "aumentando" if valor >= 0 else "diminuindo"
                            titulo, descricao = self._tooltip_variacao_atributo(impacto)
                            partes.append([
                                self._segmento(alvo_nome),
                                self._segmento(f" {acao_txt} {atributo} para "),
                                self._segmento(self._formatar_numero(impacto.get("valor_depois", 0.0)), atributo=atributo, titulo=titulo, descricao=descricao),
                            ])
                    for idx, parte in enumerate(partes):
                        if idx > 0:
                            segmentos.append(self._segmento(", "))
                        segmentos.extend(parte)
            elif bool(evento.get("sem_alvo", False)):
                segmentos.extend([self._segmento(" em "), self._segmento(f"Area {area}" if area else "uma area"), self._segmento(", mas nao encontrou alvo")])
            elif falhas:
                alvo_falha = str(falhas[0].get("alvo_nome") or falhas[0].get("alvo_id") or area or "o alvo")
                segmentos.extend([self._segmento(" em "), self._segmento(alvo_falha), self._segmento(", mas errou")])
            elif area:
                segmentos.extend([self._segmento(" em "), self._segmento(f"Area {area}")])
            if any(str(i.get("tipo") or "").strip().casefold() in {"pokemon_sofreu_dano", "barreira_absorveu"} and bool(i.get("critico", False)) for i in impactos):
                segmentos.append(self._segmento(" (critico)"))
            segmentos.append(self._segmento("."))
        elif tipo == "rodada_iniciada":
            segmentos = [self._segmento(f"Rodada {evento.get('rodada')} iniciada.")]
        elif tipo == "rodada_finalizada":
            segmentos = [self._segmento(f"Rodada {evento.get('rodada')} finalizada.")]
        elif tipo == "batalha_finalizada":
            segmentos = [self._segmento("A batalha foi finalizada.")]
        elif tipo == "acao_iniciada":
            segmentos = [self._segmento(pokemon), self._segmento(" preparou "), self._segmento(str(evento.get("tipo_acao") or evento.get("tipo") or "acao")), self._segmento(".")]
        elif tipo == "acao_falhou":
            motivo = str(evento.get("motivo") or evento.get("motivo_invalidacao") or "motivo nao informado")
            segmentos = [self._segmento(pokemon), self._segmento(f" tentou agir, mas falhou: {motivo}.")]
        elif tipo == "pokemon_gastou_energia":
            titulo, descricao = self._tooltip_energia(-self._numero(evento.get("valor"), 0.0), evento.get("energia_depois", 0.0), "acao")
            segmentos = [self._segmento(pokemon), self._segmento(" gastou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="ene", titulo=titulo, descricao=descricao), self._segmento(" de energia.")]
        elif tipo == "pokemon_ganhou_energia":
            titulo, descricao = self._tooltip_energia(evento.get("valor", 0.0), evento.get("energia_depois", 0.0), str(evento.get("motivo") or ""))
            segmentos = [self._segmento(pokemon), self._segmento(" recuperou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="ene", titulo=titulo, descricao=descricao), self._segmento(" de energia.")]
        elif tipo == "ataque_usado":
            alvo_txt = str(evento.get("area_alvo") or evento.get("area_alvo_real") or "").strip()
            segmentos = [self._segmento(str(evento.get("usuario_nome") or pokemon)), self._segmento(" usou "), self._segmento(str(evento.get("ataque_nome") or "ataque"))]
            if alvo_txt:
                segmentos.extend([self._segmento(" em "), self._segmento(alvo_txt)])
            segmentos.append(self._segmento("."))
        elif tipo == "ataque_sem_alvo_real":
            segmentos = [self._segmento(str(evento.get("ataque_nome") or "Ataque")), self._segmento(" nao encontrou alvo real.")]
        elif tipo == "ataque_errou":
            segmentos = [self._segmento(str(evento.get("usuario_nome") or pokemon)), self._segmento(" errou "), self._segmento(str(evento.get("alvo_nome") or "o alvo")), self._segmento(".")]
        elif tipo == "ataque_acertou":
            segmentos = [self._segmento(str(evento.get("usuario_nome") or pokemon)), self._segmento(" acertou "), self._segmento(str(evento.get("alvo_nome") or "o alvo")), self._segmento(".")]
        elif tipo == "pokemon_sofreu_dano":
            titulo, descricao = self._tooltip_calculo("Detalhes do dano", evento, [f"Valor aplicado: {self._formatar_numero(evento.get('valor', 0.0))}", f"Antes: {self._formatar_numero(evento.get('vida_antes', 0.0))}", f"Depois: {self._formatar_numero(evento.get('vida_depois', 0.0))}"])
            segmentos = [self._segmento(str(evento.get("alvo_nome") or pokemon)), self._segmento(" sofreu "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="atk", titulo=titulo, descricao=descricao), self._segmento(" de dano.")]
            if bool(evento.get("critico", False)):
                segmentos.append(self._segmento(" Foi critico."))
        elif tipo == "barreira_absorveu":
            titulo, descricao = self._tooltip_valor_simples("Detalhes da barreira", [f"Antes: {self._formatar_numero(evento.get('barreira_antes', 0))}", f"Depois: {self._formatar_numero(evento.get('barreira_depois', 0))}"])
            segmentos = [self._segmento("A barreira de "), self._segmento(str(evento.get("alvo_nome") or alvo)), self._segmento(" absorveu "), self._segmento(self._formatar_numero(evento.get("dano_barreira", 0.0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" de dano.")]
        elif tipo == "pokemon_recebeu_cura":
            titulo, descricao = self._tooltip_calculo("Detalhes da cura", evento, [f"Valor aplicado: {self._formatar_numero(evento.get('valor', 0.0))}", f"Antes: {self._formatar_numero(evento.get('vida_antes', 0.0))}", f"Depois: {self._formatar_numero(evento.get('vida_depois', 0.0))}"])
            segmentos = [self._segmento(str(evento.get("alvo_nome") or pokemon)), self._segmento(" recuperou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="vida", titulo=titulo, descricao=descricao), self._segmento(" de vida.")]
        elif tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            alvo_nome = str(evento.get("alvo_nome") or evento.get("pokemon_nome") or pokemon)
            origem_nome = str(evento.get("origem_nome") or evento.get("usuario_nome") or executor)
            ataque = str(evento.get("ataque_nome") or "ataque")
            atributo = str(evento.get("atributo") or "Atributo")
            valor = self._numero(evento.get("valor", evento.get("variacao", 0.0)), 0.0)
            verbo = "aumentou" if valor >= 0 else "diminuiu"
            alvo_txt = "sua propria" if str(evento.get("origem_id") or evento.get("usuario_id") or "") == str(evento.get("alvo_id") or evento.get("pokemon_id") or "") else f"de {alvo_nome}"
            titulo, descricao = self._tooltip_variacao_atributo(evento)
            segmentos = [
                self._segmento(origem_nome),
                self._segmento(" usou "),
                self._segmento(ataque),
                self._segmento(f" e {verbo} {alvo_txt} {atributo} para "),
                self._segmento(self._formatar_numero(evento.get("valor_depois", 0.0)), atributo=atributo, titulo=titulo, descricao=descricao),
                self._segmento("."),
            ]
        elif tipo == "pokemon_ganhou_barreira":
            titulo, descricao = self._tooltip_calculo("Detalhes da barreira", evento, [f"Barreira ganha: {self._formatar_numero(evento.get('valor', 0.0))}", f"Barreira total: {self._formatar_numero(evento.get('barreira_depois', 0.0))}"])
            segmentos = [self._segmento(str(evento.get("alvo_nome") or pokemon)), self._segmento(" ganhou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" de barreira.")]
        elif tipo == "pokemon_recebeu_efeito":
            segmentos = [self._segmento(pokemon), self._segmento(" recebeu "), self._segmento(str(evento.get("efeito_nome") or "efeito")), self._segmento(f" por {evento.get('passos_restantes', '?')} passos.")]
        elif tipo == "efeito_bloqueado_por_limite":
            segmentos = [self._segmento(pokemon), self._segmento(" nao recebeu "), self._segmento(str(evento.get("efeito_nome") or "efeito")), self._segmento(": limite de efeitos.")]
        elif tipo == "efeito_tickou":
            segmentos = [self._segmento(str(evento.get("efeito_nome") or "Efeito")), self._segmento(" tickou em "), self._segmento(pokemon), self._segmento(f": {evento.get('passos_antes', '?')} -> {evento.get('passos_depois', '?')}.")]
        elif tipo == "efeito_expirou":
            segmentos = [self._segmento(str(evento.get("efeito_nome") or "Efeito")), self._segmento(" expirou em "), self._segmento(pokemon), self._segmento(".")]
        elif tipo == "clima_expirou":
            segmentos = [self._segmento("Clima "), self._segmento(str(evento.get("clima") or evento.get("clima_nome") or "ativo")), self._segmento(" expirou.")]
        elif tipo == "pokemon_moveu":
            segmentos = [self._segmento(pokemon), self._segmento(" moveu-se de "), self._segmento(str(evento.get("area_origem") or "?")), self._segmento(" para "), self._segmento(str(evento.get("area_destino") or "?")), self._segmento(".")]
        elif tipo == "pokemon_trocou_posicao":
            segmentos = [self._segmento(str(evento.get("pokemon_a_nome") or "Pokemon")), self._segmento(" trocou de posicao com "), self._segmento(str(evento.get("pokemon_b_nome") or "Pokemon")), self._segmento(".")]
        elif tipo == "pokemon_trocou_reserva":
            segmentos = [self._segmento(str(evento.get("pokemon_entrou_nome") or "Pokemon")), self._segmento(" entrou no lugar de "), self._segmento(str(evento.get("pokemon_saiu_nome") or "Pokemon")), self._segmento(".")]
        elif tipo == "pokemon_entrou":
            segmentos = [self._segmento(pokemon), self._segmento(" entrou em campo.")]
        elif tipo == "pokemon_saiu":
            segmentos = [self._segmento(pokemon), self._segmento(" saiu de campo.")]
        elif tipo == "pokemon_morreu":
            segmentos = [self._segmento(pokemon), self._segmento(" desmaiou.")]
        elif tipo == "captura_batalha_resultado":
            usuario = str(evento.get("usuario_nome") or executor)
            alvo_nome = str(evento.get("alvo_nome") or alvo)
            bola = str(evento.get("bola_nome") or "Pokeball")
            titulo, descricao = self._tooltip_captura(evento)
            chance = self._formatar_numero(evento.get("chance_real_3_checks", 0.0))
            if bool(evento.get("capturado", False)):
                segmentos = [self._segmento(usuario), self._segmento(" capturou "), self._segmento(alvo_nome), self._segmento(" com "), self._segmento(bola), self._segmento(" ("), self._segmento(f"{chance}%", atributo="per", titulo=titulo, descricao=descricao), self._segmento(").")]
            else:
                segmentos = [self._segmento(usuario), self._segmento(" tentou capturar "), self._segmento(alvo_nome), self._segmento(" com "), self._segmento(bola), self._segmento(", mas falhou ("), self._segmento(f"{chance}%", atributo="per", titulo=titulo, descricao=descricao), self._segmento(").")]
        elif tipo in {"passiva", "passivo"}:
            nome_passiva = str(evento.get("passiva") or evento.get("nome") or "Passiva")
            segmentos = [self._segmento("Passiva "), self._segmento(nome_passiva), self._segmento(" ativou em "), self._segmento(pokemon)]
            atributos = []
            for chave in ("Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Amp", "Dur"):
                if chave in evento:
                    atributos.append(f"{chave} {self._formatar_numero(evento.get(chave))}")
            if atributos:
                segmentos.extend([self._segmento(": "), self._segmento(", ".join(atributos))])
            segmentos.append(self._segmento("."))
        elif tipo == "acao":
            ataque = str(evento.get("ataque") or "ação")
            destino = evento.get("destino")
            if str(evento.get("estilo") or "").strip().casefold() == "movimento" and destino is not None:
                segmentos = [
                    self._segmento(executor),
                    self._segmento(" começou a se mover em direção a "),
                    self._segmento(self._formatar_posicao(destino)),
                    self._segmento("."),
                ]
            else:
                segmentos = [
                    self._segmento(executor),
                    self._segmento(" usou "),
                    self._segmento(ataque),
                    self._segmento("."),
                ]
        elif tipo == "movimento":
            segmentos = [
                self._segmento(pokemon),
                self._segmento(" moveu-se até "),
                self._segmento(self._formatar_posicao(evento.get("posicao"))),
                self._segmento("."),
            ]
            if bool(evento.get("interrompido_por_colisao", False)):
                segmentos.append(self._segmento(" O deslocamento foi interrompido por colisão."))
        elif tipo == "objeto":
            fase_objeto = str(evento.get("fase_objeto") or "").strip().casefold()
            subtipo = str(evento.get("subtipo") or "objeto").strip()
            if fase_objeto == "criado":
                segmentos = [
                    self._segmento(executor),
                    self._segmento(" iniciou "),
                    self._segmento(subtipo),
                    self._segmento(" a partir de "),
                    self._segmento(self._formatar_posicao(evento.get("origem") or evento.get("posicao"))),
                    self._segmento("."),
                ]
            elif fase_objeto == "finalizado":
                segmentos = [
                    self._segmento(subtipo),
                    self._segmento(" terminou em "),
                    self._segmento(self._formatar_posicao(evento.get("destino") or evento.get("posicao"))),
                    self._segmento("."),
                ]
            else:
                segmentos = [
                    self._segmento(subtipo),
                    self._segmento(" avançou para "),
                    self._segmento(self._formatar_posicao(evento.get("destino") or evento.get("posicao"))),
                    self._segmento("."),
                ]
        elif tipo == "dano":
            titulo, descricao = self._tooltip_dano(evento)
            segmentos = [
                self._segmento(executor),
                self._segmento(" causou "),
                self._segmento(self._formatar_numero(evento.get("dano", 0.0)), atributo=self._atributo_dano(evento), titulo=titulo, descricao=descricao),
                self._segmento(" de dano em "),
                self._segmento(alvo),
                self._segmento("."),
            ]
            if self._numero(evento.get("dano_barreira"), 0.0) > 0.0:
                segmentos.extend(
                    [
                        self._segmento(" "),
                        self._segmento(self._formatar_numero(evento.get("dano_barreira", 0.0)), atributo="def", titulo=titulo, descricao=descricao),
                        self._segmento(" atingiram a barreira."),
                    ]
                )
            if bool(evento.get("critico", False)):
                segmentos.append(self._segmento(" Foi um acerto crítico."))
        elif tipo == "cura":
            titulo, descricao = self._tooltip_vida("Detalhes da cura", evento.get("valor", 0.0), evento.get("vida_antes", 0.0), evento.get("vida_depois", 0.0))
            segmentos = [
                self._segmento(executor),
                self._segmento(" curou "),
                self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="vida", titulo=titulo, descricao=descricao),
                self._segmento(" de Vida em "),
                self._segmento(alvo),
                self._segmento("."),
            ]
        elif tipo == "barreira":
            titulo, descricao = self._tooltip_barreira(evento.get("valor", 0.0), evento.get("barreira_total", 0.0))
            segmentos = [
                self._segmento(executor),
                self._segmento(" concedeu "),
                self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="def", titulo=titulo, descricao=descricao),
                self._segmento(" de barreira para "),
                self._segmento(alvo),
                self._segmento("."),
            ]
        elif tipo == "energia":
            titulo, descricao = self._tooltip_energia(evento.get("valor", 0.0), evento.get("energia", 0.0), str(evento.get("motivo") or ""))
            segmentos = [
                self._segmento(pokemon),
                self._segmento(" alterou "),
                self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="ene", titulo=titulo, descricao=descricao),
                self._segmento(" de energia."),
            ]
        elif tipo == "efeito":
            efeito = str(evento.get("efeito") or "efeito")
            if str(evento.get("fase_efeito") or "").strip().casefold() == "expirado":
                segmentos = [self._segmento(efeito), self._segmento(" expirou em "), self._segmento(alvo), self._segmento(".")]
            else:
                alvo_real = alvo if alvo != "Combatente" else executor
                executor_real = executor if executor != "Combatente" else alvo_real
                segmentos = [self._segmento(executor_real), self._segmento(" aplicou "), self._segmento(efeito), self._segmento(" em "), self._segmento(alvo_real), self._segmento(".")]
        elif tipo == "troca":
            saiu = str(evento.get("saiu_nome") or evento.get("saiu") or "alguém")
            entrou = str(evento.get("entrou_nome") or evento.get("entrou") or "alguém")
            segmentos = [self._segmento(executor), self._segmento(" trocou "), self._segmento(saiu), self._segmento(" por "), self._segmento(entrou), self._segmento(".")]
        elif tipo == "fim_turno":
            motivo = str(evento.get("motivo") or "efeito de rodada")
            segmentos = [self._segmento(pokemon), self._segmento(f" sofreu {motivo}: ")]
            if "dano" in evento:
                titulo, descricao = self._tooltip_vida("Detalhes do dano passivo", evento.get("dano", 0.0), evento.get("vida_antes", 0.0), evento.get("vida_depois", 0.0))
                segmentos.extend([self._segmento(self._formatar_numero(evento.get("dano", 0.0)), atributo="atk", titulo=titulo, descricao=descricao), self._segmento(" de dano.")])
            elif "cura" in evento:
                titulo, descricao = self._tooltip_vida("Detalhes da cura passiva", evento.get("cura", 0.0), evento.get("vida_antes", 0.0), evento.get("vida_depois", 0.0))
                segmentos.extend([self._segmento(self._formatar_numero(evento.get("cura", 0.0)), atributo="vida", titulo=titulo, descricao=descricao), self._segmento(" de cura.")])
            elif "energia" in evento:
                titulo, descricao = self._tooltip_energia(evento.get("energia", 0.0), evento.get("energia_total", 0.0), motivo)
                segmentos.extend([self._segmento(self._formatar_numero(evento.get("energia", 0.0)), atributo="ene", titulo=titulo, descricao=descricao), self._segmento(" de energia.")])
            else:
                segmentos.append(self._segmento("sem alterações numéricas."))
        elif tipo == "recoil":
            titulo, descricao = self._tooltip_vida("Detalhes do recuo", evento.get("valor", 0.0), evento.get("valor", 0.0), 0.0)
            segmentos = [self._segmento(executor), self._segmento(" recebeu "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="atk", titulo=titulo, descricao=descricao), self._segmento(" de recuo.")]
        elif tipo == "execucao":
            segmentos = [self._segmento(executor), self._segmento(" executou "), self._segmento(alvo), self._segmento(".")]
        elif tipo == "jogada_descartada":
            ataque = str(evento.get("ataque") or "a jogada")
            motivo = str(evento.get("motivo") or "motivo não informado")
            segmentos = [self._segmento(executor), self._segmento(" teve "), self._segmento(ataque), self._segmento(f" descartado: {motivo}.")]
        elif tipo in {"acao_bloqueada", "impacto_cancelado", "acao_finalizada"}:
            ataque = str(evento.get("ataque") or "ação")
            motivo = str(evento.get("motivo") or "")
            segmentos = [self._segmento(executor), self._segmento(" encerrou "), self._segmento(ataque)]
            if motivo:
                segmentos.append(self._segmento(f" por {motivo}"))
            segmentos.append(self._segmento("."))
        elif tipo == "reset_variacoes":
            segmentos = [self._segmento(executor), self._segmento(" zerou as variações de "), self._segmento(alvo), self._segmento(".")]
        else:
            segmentos = [self._segmento(f"{executor}: evento {tipo or 'desconhecido'}.")]

        cor_fundo, cor_borda, cor_faixa = self._cores_evento(tipo, evento)
        return {
            "tipo": tipo,
            "tick": int(tick),
            "fase_label": self._FASES_LABEL.get(fase, fase.title()),
            "cor_fundo": cor_fundo,
            "cor_borda": cor_borda,
            "cor_faixa": cor_faixa,
            "segmentos": segmentos,
        }

    def _achatar_eventos(self, log: Dict[str, object] | None) -> list[dict[str, object]]:
        saida: list[dict[str, object]] = []
        movimentos_finais: dict[str, dict[str, object]] = {}

        def flush_movimentos():
            nonlocal saida
            if not movimentos_finais:
                return
            for chave in sorted(movimentos_finais.keys(), key=lambda item: (movimentos_finais[item]["tick"], item)):
                saida.append(dict(movimentos_finais[chave]))
            movimentos_finais.clear()

        historico = [dict(item) for item in list((log or {}).get("historico") or []) if isinstance(item, dict)]
        if historico and any("tipo" in item for item in historico):
            atual = None
            for idx, evento in enumerate(historico, start=1):
                evento = self._evento_plano(evento)
                if not self._evento_deve_aparecer(evento):
                    continue
                tipo = str(evento.get("tipo") or "").strip().casefold()
                tick = int(evento.get("ordem") or idx)
                if tipo == "ataque_usado":
                    atual = {"tipo": "ataque_resumo", "base": dict(evento), "impactos": [], "falhas": [], "sem_alvo": False, "critico": False}
                    saida.append({"tick": tick, "fase": "segmentacao", "evento": atual})
                    continue
                if atual is not None and tipo in {"pokemon_sofreu_dano", "barreira_absorveu", "pokemon_recebeu_cura", "pokemon_ganhou_barreira", "pokemon_recebeu_efeito", "pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
                    impacto = dict(evento)
                    if tipo == "pokemon_recebeu_efeito":
                        impacto["tipo_efeito"] = str(evento.get("tipo_efeito") or evento.get("tipo_status") or evento.get("efeito_tipo") or evento.get("tipo") or "")
                        if not impacto["tipo_efeito"] and isinstance(evento.get("efeito"), dict):
                            impacto["tipo_efeito"] = str(evento["efeito"].get("tipo") or "")
                    atual["impactos"].append(impacto)
                    if bool(evento.get("critico", False)):
                        atual["critico"] = True
                    continue
                if atual is not None and tipo == "ataque_errou":
                    atual["falhas"].append(dict(evento))
                    continue
                if atual is not None and tipo == "ataque_sem_alvo_real":
                    atual["sem_alvo"] = True
                    continue
                if atual is not None and tipo == "acao_falhou":
                    atual["falhas"].append(dict(evento))
                    continue
                if tipo in {"ataque_acertou", "acao_iniciada", "pokemon_gastou_energia", "pokemon_ganhou_energia", "efeito_tickou", "pokemon_entrou", "pokemon_saiu"}:
                    continue
                if atual is not None and tipo in {"passiva", "passivo", "pokemon_morreu"}:
                    saida.append({"tick": tick, "fase": "segmentacao", "evento": evento})
                    continue
                atual = None
                saida.append({"tick": tick, "fase": "segmentacao", "evento": evento})
            return saida
        for bloco in historico:
            tick = int(bloco.get("tick", 0) or 0)
            for fase in ("inicializacao", "segmentacao", "passiva", "finalizacao"):
                for evento in [dict(item) for item in list(bloco.get(fase) or []) if isinstance(item, dict)]:
                    if not self._evento_deve_aparecer(evento):
                        continue
                    tipo = str(evento.get("tipo") or "").strip().casefold()
                    if tipo == "movimento":
                        pokemon_id = str(evento.get("pokemon_id") or "")
                        if pokemon_id:
                            movimentos_finais[pokemon_id] = {"tick": tick, "fase": fase, "evento": evento}
                        continue
                    if tipo == "objeto" and str(evento.get("fase_objeto") or "").strip().casefold() == "movimento":
                        continue
                    flush_movimentos()
                    saida.append({"tick": tick, "fase": fase, "evento": evento})
        flush_movimentos()
        return saida

    @staticmethod
    def _evento_plano(evento: Dict[str, object]) -> Dict[str, object]:
        out = dict(evento or {})
        dados = out.get("dados") if isinstance(out.get("dados"), dict) else {}
        if isinstance(dados.get("dados"), dict):
            for chave, valor in dict(dados.get("dados") or {}).items():
                dados.setdefault(chave, valor)
        for chave, valor in dados.items():
            if chave == "tipo" and "tipo" in out:
                out.setdefault("tipo_efeito", valor)
            else:
                out.setdefault(chave, valor)
        return out

    def _evento_deve_aparecer(self, evento: Dict[str, object]) -> bool:
        evento = self._evento_plano(evento)
        tipo = str(evento.get("tipo") or "").strip().casefold()
        ocultos = {
            "rodada_iniciada",
            "rodada_finalizada",
            "batalha_finalizada",
            "acao_iniciada",
            "pokemon_gastou_energia",
            "pokemon_ganhou_energia",
            "efeito_tickou",
            "ataque_acertou",
            "pokemon_entrou",
            "pokemon_saiu",
            "captura_batalha_lancada",
            "inventario_atualizado_batalha",
        }
        if tipo in ocultos:
            return False
        if tipo != "dano":
            return True
        detalhes = dict(evento.get("detalhes") or {})
        dano_bruto = self._numero(detalhes.get("dano_bruto"), self._numero(evento.get("dano"), 0.0))
        dano_final = self._numero(evento.get("dano"), 0.0)
        dano_barreira = self._numero(evento.get("dano_barreira"), 0.0)
        return not (self._aprox(dano_bruto, 0.0) and self._aprox(dano_final, 0.0) and self._aprox(dano_barreira, 0.0))

    def _registros_rodada(self, rodada: int, log: Dict[str, object] | None, replay: Dict[str, object]) -> list[dict[str, object]]:
        if not isinstance(log, dict):
            if int(rodada) <= 1:
                return [
                    self._registro_placeholder(
                        "Os registros da rodada 1 aparecerão aqui assim que a primeira resolução do combate chegar.",
                        subtitulo="Aguardando primeira rodada",
                    )
                ]
            return [self._registro_placeholder("Ainda não existe um log salvo para esta rodada.", subtitulo="Rodada indisponível")]

        eventos = self._achatar_eventos(log)
        replay_ativo = bool(replay.get("ativo", False))
        turno_replay = int(replay.get("turno_atual", replay.get("rodada_atual", 0)) or 0)
        if replay_ativo and turno_replay == int(rodada):
            tick_atual = max(0, int(replay.get("tick_atual", 0) or 0))
            eventos = eventos[:tick_atual]
            if not eventos:
                return [
                    self._registro_placeholder(
                        "As acoes vao surgir em ordem conforme a animacao do combate avanca.",
                        subtitulo="Reproduzindo rodada",
                    )
                ]

        registros = [self._registro_evento(dict(item.get("evento") or {}), int(item.get("tick", 0) or 0), str(item.get("fase") or "")) for item in eventos]
        if not registros:
            return [self._registro_placeholder("Esta rodada não trouxe registros visíveis para o jogador.", subtitulo="Rodada vazia")]
        return registros

    def _alternar(self):
        self._aberto = not self._aberto

    def _navegar(self, delta: int):
        max_rodada = max(1, int(self._estado_logs.get("ultimo_turno_com_log", 0) or 0))
        self._rodada_selecionada = max(1, min(max_rodada, int(self._rodada_selecionada) + int(delta)))
        self._rodada_manual = True

    def _sincronizar_estado(self):
        if self._controlador is None or not hasattr(self._controlador, "estado_visualizador_logs"):
            self._estado_logs = {"ultimo_turno_com_log": 0, "replay": {}}
            return
        self._estado_logs = dict(self._controlador.estado_visualizador_logs() or {})
        replay = dict(self._estado_logs.get("replay") or {})
        turno_replay = int(replay.get("turno_atual", 0) or 0)
        ultimo_turno = max(1, int(self._estado_logs.get("ultimo_turno_com_log", 0) or 0))
        rodada_atual = max(1, int(self._estado_logs.get("rodada_atual", ultimo_turno) or ultimo_turno))
        if bool(replay.get("ativo", False)) and turno_replay > 0:
            self._rodada_selecionada = turno_replay
            self._rodada_manual = False
        elif not self._rodada_manual or int(self._rodada_selecionada or 1) > ultimo_turno:
            self._rodada_selecionada = max(1, min(ultimo_turno, rodada_atual - 1 if rodada_atual > 1 else 1))

        log = self._controlador.obter_log_publico(self._rodada_selecionada) if hasattr(self._controlador, "obter_log_publico") else None
        registros = self._registros_rodada(self._rodada_selecionada, log, replay)
        self._lista.definir_registros(registros)

    def _atualizar_layout(self, tela: pygame.Surface, dt: float):
        w, h = tela.get_size()
        alvo = 1.0 if self._aberto else 0.0
        self._animacao += (alvo - self._animacao) * min(1.0, max(0.0, float(dt)) * 11.0)
        if abs(self._animacao - alvo) <= 0.002:
            self._animacao = alvo

        largura = max(277, min(356, int(w * 0.225)) - 5)
        altura = max(330, min(int(h * 0.65), h - 40) - 12)
        margem = 16
        y = max(18, (h - altura) // 2)
        x_aberto = w - largura - margem
        x_fechado = w + 8
        x = int(x_fechado + (x_aberto - x_fechado) * self._animacao)

        self._rect_painel = pygame.Rect(x, y, largura, altura)
        tab_largura = 44
        tab_altura = 116
        tab_x = self._rect_painel.x - tab_largura + 3
        tab_y = y + 28
        self._rect_tab = pygame.Rect(tab_x, tab_y, tab_largura, tab_altura)

        self._botao_prev.base_rect = pygame.Rect(self._rect_painel.right - 90, self._rect_painel.y + 14, 34, 34)
        self._botao_prev.rect = pygame.Rect(self._botao_prev.base_rect)
        self._botao_next.base_rect = pygame.Rect(self._rect_painel.right - 48, self._rect_painel.y + 14, 34, 34)
        self._botao_next.rect = pygame.Rect(self._botao_next.base_rect)

        conteudo_rect = pygame.Rect(self._rect_painel.x + 12, self._rect_painel.y + 64, self._rect_painel.width - 24, self._rect_painel.height - 78)
        self._lista.configurar_rect(conteudo_rect)

        ultimo_turno = max(1, int(self._estado_logs.get("ultimo_turno_com_log", 0) or 0))
        self._botao_prev.set_habilitado(self._rodada_selecionada > 1)
        self._botao_next.set_habilitado(self._rodada_selecionada < ultimo_turno)

    def retangulos_interativos(self) -> List[pygame.Rect]:
        saida = [pygame.Rect(self._rect_tab)] if self._rect_tab.width > 0 else []
        if self._animacao > 0.04:
            saida.extend([
                pygame.Rect(self._rect_painel),
                pygame.Rect(self._botao_prev.rect),
                pygame.Rect(self._botao_next.rect),
                pygame.Rect(self._lista.rect),
            ])
        return saida

    def captura_scroll(self, mouse_pos) -> bool:
        if not isinstance(mouse_pos, (tuple, list)) or len(mouse_pos) < 2:
            return False
        ponto = (int(mouse_pos[0]), int(mouse_pos[1]))
        if self._rect_tab.collidepoint(ponto):
            return True
        if self._animacao > 0.04 and self._rect_painel.collidepoint(ponto):
            return True
        return False

    def preparar(self, tela: pygame.Surface, dt: float = 0.0) -> None:
        self._sincronizar_estado()
        self._atualizar_layout(tela, dt)

    def desenhar(self, tela: pygame.Surface, eventos, dt: float = 0.0) -> None:
        self.preparar(tela, dt)

        renderizar_botao_expandir(self._botao_tab, tela, eventos or [], dt, self._rect_tab, self._aberto, None)

        if self._animacao <= 0.02:
            return

        alpha = int(242 * max(0.0, min(1.0, self._animacao)))
        painel = pygame.Surface(self._rect_painel.size, pygame.SRCALPHA)
        pygame.draw.rect(painel, (10, 16, 28, alpha), painel.get_rect(), border_radius=18)
        pygame.draw.rect(painel, (114, 144, 196, alpha), painel.get_rect(), 2, border_radius=18)
        pygame.draw.line(painel, (52, 74, 110, alpha), (12, 60), (self._rect_painel.width - 12, 60), 1)
        tela.blit(painel, self._rect_painel.topleft)

        self._texto_titulo.set_text(f"Rodada {int(self._rodada_selecionada or 1)}")
        self._texto_titulo.set_pos((self._rect_painel.x + 16, self._rect_painel.y + 31))
        self._texto_titulo.draw(tela)

        replay = dict(self._estado_logs.get("replay") or {})
        if bool(replay.get("ativo", False)) and int(replay.get("turno_atual", 0) or 0) == int(self._rodada_selecionada):
            tick_atual = max(0, int(replay.get("tick_atual", 0) or 0))
            tick_final = max(0, int(replay.get("tick_final", 0) or 0))
            self._texto_subtitulo.set_text(f"Reproduzindo ações: {tick_atual}/{tick_final}")
        else:
            self._texto_subtitulo.set_text("Histórico da batalha")
        self._texto_subtitulo.set_pos((self._rect_painel.x + 16, self._rect_painel.y + 44))
        self._texto_subtitulo.draw(tela)

        self._botao_prev.render(tela, eventos or [], dt, None)
        self._botao_next.render(tela, eventos or [], dt, None)
        self._lista.render(tela, eventos or [], dt, None)

        tooltip = self._lista.tooltip_no_mouse(pygame.mouse.get_pos())
        if tooltip:
            titulo = str(tooltip.get("titulo") or "").strip()
            descricao = str(tooltip.get("descricao") or tooltip.get("tooltip") or "").strip()
            self._tooltip.definir_conteudo(titulo=titulo, descricao=descricao)
            rect_tela = tooltip.get("rect_tela")
            if isinstance(rect_tela, pygame.Rect):
                self._tooltip.definir_area(rect_tela)
                self._tooltip.definir_posicao_fixa((rect_tela.right + 10, rect_tela.top - 6))
            self._tooltip.render(tela, mouse_pos=pygame.mouse.get_pos(), forcar=True)
