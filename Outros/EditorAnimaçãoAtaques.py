from __future__ import annotations

"""
Editor visual de animações de ataques.

Coloque este arquivo em Outros/EditorAnimaçãoAtaques.py e rode pela raiz:

    python Outros/EditorAnimaçãoAtaques.py

Este editor usa o SimuladorBatalha.py real como base:
- ControladorBatalha real;
- Arena real;
- CameraBatalha real;
- PipelineGrafica/ModernGL real;
- MontadorJogadas real para alvificação/indicadores;
- ControladorAnimacoes real para tocar Projetil/Raio/Laser/Jato/Explosão.

A diferença é que ele injeta um único ataque editável em todos os Pokémon.
O usuário usa o fluxo normal do jogo: seleciona o Pokémon, clica no único ataque
da ficha, escolhe o alvo pela alvificação normal e aperta Pronto. O botão Pronto
é interceptado localmente para gerar/reproduzir um log visual sem conexão com
servidor externo.
"""

import copy
import json
import math
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pygame

# ---------------------------------------------------------------------------
# Bootstrap de paths
# ---------------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parents[1]
OUTROS = Path(__file__).resolve().parent
for p in (RAIZ, OUTROS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from SimuladorBatalha import (  # type: ignore
        ControladorBatalha,
        CameraBatalha,
        PipelineGrafica,
        JogoSimulador,
        criar_janela,
        montar_estado_inicial,
    )
except Exception as exc:  # pragma: no cover - erro exibido em runtime
    raise SystemExit(
        "EditorAnimaçãoAtaques depende do arquivo Outros/SimuladorBatalha.py.\n"
        "Coloque este arquivo na mesma pasta Outros do simulador real e rode novamente.\n"
        f"Erro original: {exc!r}"
    )

try:
    from Codigo.Visual.AuxiliaresVisuais import EFEITOS_ATAQUE_FPS, CORES_TIPOS_ATAQUE
except Exception:
    EFEITOS_ATAQUE_FPS = {}
    CORES_TIPOS_ATAQUE = {
        "normal": (187, 176, 151),
        "fogo": (219, 106, 72),
        "agua": (80, 130, 219),
        "planta": (86, 171, 90),
        "eletrico": (224, 199, 61),
    }

try:
    from Codigo.Paineis.FichaPokemonBatalha import FichaPokemonBatalha
except Exception:  # pragma: no cover
    FichaPokemonBatalha = None


EDITOR_ATTACK_CODE = 999001
EDITOR_ATTACK_NAME = "Ataque Editor"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalizar(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def parse_bool(valor: object, default: bool = False) -> bool:
    if isinstance(valor, bool):
        return valor
    texto = str(valor or "").strip().lower()
    if texto in {"1", "true", "sim", "yes", "on", "ligado"}:
        return True
    if texto in {"0", "false", "nao", "não", "no", "off", "desligado"}:
        return False
    return bool(default)


def parse_num(valor: object, default: float = 0.0) -> float:
    try:
        return float(str(valor).replace(",", "."))
    except Exception:
        return float(default)


def parse_int(valor: object, default: int = 0) -> int:
    try:
        return int(float(str(valor).replace(",", ".")))
    except Exception:
        return int(default)


def parse_cor(valor: object, default=(255, 230, 80)) -> list[int]:
    if isinstance(valor, (list, tuple)) and len(valor) >= 3:
        vals = valor[:3]
    else:
        texto = str(valor or "").replace(";", ",").replace(" ", ",")
        vals = [p for p in texto.split(",") if p != ""]
    try:
        rgb = [max(0, min(255, int(float(v)))) for v in vals[:3]]
        while len(rgb) < 3:
            rgb.append(default[len(rgb)])
        return rgb
    except Exception:
        return list(default)


def fmt_bool(v: bool) -> str:
    return "true" if bool(v) else "false"


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def copiar_ataque_editor(tipo: str, nome: str = EDITOR_ATTACK_NAME, custo: int = 0) -> dict[str, Any]:
    return {
        "ID": EDITOR_ATTACK_CODE,
        "Code": EDITOR_ATTACK_CODE,
        "code": str(EDITOR_ATTACK_CODE),
        "Ataque": nome,
        "Nome": nome,
        "nome": nome,
        "Tipo": tipo,
        "tipo": tipo,
        "Custo": int(custo),
        "custo": int(custo),
        "Estilo": "Ativa",
        "estilo": "Ativa",
        "Descrição Nivel 1": "Ataque editável do EditorAnimaçãoAtaques.",
    }


# ---------------------------------------------------------------------------
# Estado editável
# ---------------------------------------------------------------------------


class EstadoEditorAtaque:
    MODELOS = ["EfeitoProprio", "EfeitoAlvo", "Avanço", "Salto", "Raio", "Laser", "Jato", "Projetil", "Explosão"]
    TIPOS = [
        "normal", "fogo", "agua", "planta", "eletrico", "gelo", "lutador", "venenoso", "terrestre", "voador",
        "psiquico", "inseto", "pedra", "fantasma", "dragao", "sombrio", "metal", "fada", "cosmico", "sonoro",
    ]
    ALVOS = ["area", "pokemon", "linha", "coluna", "arena", "campo", "arena_inimiga", "campo_inimigo", "todos_inimigos"]
    LADOS = ["lado_oposto", "mesmo_lado", "qualquer", "usuario"]
    CONTATOS_EXPLOSAO = ["Projetil", "Avanço", "Salto", "Raio", "Jato"]

    def __init__(self) -> None:
        self.campos: dict[str, Any] = {
            "nome": EDITOR_ATTACK_NAME,
            "tipo": "normal",
            "modelo": "Projetil",
            "estilo_logico": "alvo",
            "alv_tipo": "area",
            "lados_permitidos": "lado_oposto",
            "exige_area_ocupada": "false",
            "quantidade": "1",
            "efeito_executor": "",
            "efeito_alvo": "ImpactoRochoso",
            "efeito_alvo2": "",
            "efeito_alvo3": "",
            "simultaneo": "false",
            "intervalo": "Ao Acabar",
            "velocidade": "8",
            "altura": "1.25",
            "distancia_parada": "contato",
            "retornar": "true",
            "cor": "255,230,80",
            "duracao": "0.6",
            "largura": "12",
            "projetil": "Generico",
            "tamanho": "16",
            "contato": "Projetil",
            "efeito_impacto_secundario": "Explosao",
            "raio_explosao": "1.5",
            "duracao_onda": "0.45",
            "cor_onda": "255,230,80",
            "largura_onda": "1.0",
            "mostrar_cartucho": "true",
            "valor_cartucho": "35",
        }
        self.alvos_config: list[dict[str, Any]] = [
            {
                "tipo": "area",
                "lados_permitidos": "lado_oposto",
                "exige_area_ocupada": "false",
                "inclui_reserva": "false",
                "quantidade": "1",
            }
        ]
        self._json_cache = ""

    @property
    def modelo(self) -> str:
        return str(self.campos.get("modelo") or "Projetil")

    @property
    def tipo(self) -> str:
        return str(self.campos.get("tipo") or "normal")

    def setar(self, chave: str, valor: Any) -> None:
        alvo_chave = self._parse_chave_alvo(chave)
        if alvo_chave is not None:
            idx, campo = alvo_chave
            if 0 <= idx < len(self.alvos_config):
                self.alvos_config[idx][campo] = valor
            return
        self.campos[chave] = valor

    def valor(self, chave: str) -> Any:
        alvo_chave = self._parse_chave_alvo(chave)
        if alvo_chave is not None:
            idx, campo = alvo_chave
            if 0 <= idx < len(self.alvos_config):
                return self.alvos_config[idx].get(campo, "")
            return ""
        return self.campos.get(chave, "")

    @staticmethod
    def _parse_chave_alvo(chave: str):
        partes = str(chave or "").split(".")
        if len(partes) != 3 or partes[0] != "alvos":
            return None
        try:
            return int(partes[1]), partes[2]
        except ValueError:
            return None

    def adicionar_grupo_alvo(self) -> None:
        self.alvos_config.append({
            "tipo": "area",
            "lados_permitidos": "lado_oposto",
            "exige_area_ocupada": "false",
            "inclui_reserva": "false",
            "quantidade": "1",
        })

    def remover_grupo_alvo(self, idx: int) -> None:
        if len(self.alvos_config) <= 1:
            return
        if 0 <= idx < len(self.alvos_config):
            self.alvos_config.pop(idx)

    def alternar_bool(self, chave: str) -> None:
        self.campos[chave] = "false" if parse_bool(self.campos.get(chave)) else "true"

    def ciclo(self, chave: str, opcoes: list[str], delta: int = 1) -> None:
        atual = str(self.campos.get(chave) or "")
        try:
            idx = opcoes.index(atual)
        except ValueError:
            idx = 0
        self.campos[chave] = opcoes[(idx + delta) % len(opcoes)]

    def _efeito(self, chave: str) -> str | None:
        valor = str(self.campos.get(chave) or "").strip()
        return valor if valor and normalizar(valor) not in {"none", "null", "nulo", "vazio"} else None

    def _intervalo(self) -> str | float:
        raw = str(self.campos.get("intervalo") or "").strip()
        if normalizar(raw) == "aoacabar":
            return "Ao Acabar"
        return parse_num(raw, 0.15)

    def animacao(self) -> dict[str, Any]:
        modelo = self.modelo
        anim: dict[str, Any] = {
            "modelo": modelo,
            "efeito_executor": self._efeito("efeito_executor"),
            "efeito_alvo": self._efeito("efeito_alvo"),
        }

        for k in ("efeito_alvo2", "efeito_alvo3", "efeito_alvo4"):
            if self._efeito(k) is not None:
                anim[k] = self._efeito(k)

        if modelo not in {"EfeitoProprio", "Laser"}:
            anim["simultaneo"] = parse_bool(self.campos.get("simultaneo"))
        if modelo not in {"EfeitoProprio"}:
            anim["intervalo"] = self._intervalo()

        if modelo in {"Avanço", "Salto"}:
            anim["velocidade"] = parse_num(self.campos.get("velocidade"), 8 if modelo == "Avanço" else 7)
            anim["distancia_parada"] = str(self.campos.get("distancia_parada") or "contato")
            anim["retornar"] = parse_bool(self.campos.get("retornar"), True)
            if modelo == "Salto":
                anim["altura"] = parse_num(self.campos.get("altura"), 1.25)

        if modelo in {"Raio", "Laser", "Jato"}:
            anim["cor"] = parse_cor(self.campos.get("cor"), CORES_TIPOS_ATAQUE.get(self.tipo, (255, 230, 80)))
            anim["duracao"] = parse_num(self.campos.get("duracao"), 0.6)
            anim["largura"] = parse_num(self.campos.get("largura"), 12 if modelo == "Laser" else 1.2)

        if modelo == "Projetil":
            anim["projetil"] = str(self.campos.get("projetil") or "Generico")
            anim["velocidade"] = parse_num(self.campos.get("velocidade"), 8)
            anim["tamanho"] = parse_num(self.campos.get("tamanho"), 16)
            if normalizar(anim["projetil"]) == "generico":
                anim["cor"] = parse_cor(self.campos.get("cor"), CORES_TIPOS_ATAQUE.get(self.tipo, (255, 230, 80)))

        if modelo == "Explosão":
            contato = str(self.campos.get("contato") or "Projetil")
            if normalizar(contato) == "laser":
                contato = "Projetil"
            anim["contato"] = contato
            anim["efeito_impacto_secundario"] = self._efeito("efeito_impacto_secundario")
            anim["raio_explosao"] = parse_num(self.campos.get("raio_explosao"), 1.5)
            anim["duracao_onda"] = parse_num(self.campos.get("duracao_onda"), 0.45)
            anim["cor_onda"] = parse_cor(self.campos.get("cor_onda"), CORES_TIPOS_ATAQUE.get(self.tipo, (255, 230, 80)))
            anim["largura_onda"] = parse_num(self.campos.get("largura_onda"), 1.0)
            if contato in {"Projetil"}:
                anim["projetil"] = str(self.campos.get("projetil") or "Generico")
                anim["velocidade"] = parse_num(self.campos.get("velocidade"), 8)
                anim["tamanho"] = parse_num(self.campos.get("tamanho"), 16)
                if normalizar(anim["projetil"]) == "generico":
                    anim["cor"] = parse_cor(self.campos.get("cor"), CORES_TIPOS_ATAQUE.get(self.tipo, (255, 230, 80)))
            elif contato in {"Avanço", "Salto"}:
                anim["velocidade"] = parse_num(self.campos.get("velocidade"), 8)
                anim["distancia_parada"] = str(self.campos.get("distancia_parada") or "contato")
                anim["retornar"] = parse_bool(self.campos.get("retornar"), True)
                if contato == "Salto":
                    anim["altura"] = parse_num(self.campos.get("altura"), 1.25)
            elif contato in {"Raio", "Jato"}:
                anim["cor"] = parse_cor(self.campos.get("cor"), CORES_TIPOS_ATAQUE.get(self.tipo, (255, 230, 80)))
                anim["duracao"] = parse_num(self.campos.get("duracao"), 0.6)
                anim["largura"] = parse_num(self.campos.get("largura"), 1.2)

        return anim

    def alvificacao(self) -> dict[str, Any]:
        alvos = []
        for grupo in self.alvos_config:
            lados = str(grupo.get("lados_permitidos") or "lado_oposto")
            alvos.append({
                "tipo": str(grupo.get("tipo") or "area"),
                "quantidade": max(1, parse_int(grupo.get("quantidade"), 1)),
                "lados_permitidos": [lados],
                "exige_area_ocupada": parse_bool(grupo.get("exige_area_ocupada")),
                "inclui_reserva": parse_bool(grupo.get("inclui_reserva")),
            })
        return {"alvos": alvos or [{"tipo": "area", "quantidade": 1, "lados_permitidos": ["lado_oposto"], "exige_area_ocupada": False, "inclui_reserva": False}]}

    def props(self) -> dict[str, Any]:
        return {
            "ID": EDITOR_ATTACK_CODE,
            "nome": str(self.campos.get("nome") or EDITOR_ATTACK_NAME),
            "custo": 0,
            "estilo_logico": str(self.campos.get("estilo_logico") or "alvo"),
            "animacao": self.animacao(),
            "execute_principal": "ataque_editor_animacao",
            "parametros": {"tipo": self.tipo, "categoria": "especial", "acuracia": 100},
            "alvificacao": self.alvificacao(),
        }

    def ataque(self) -> dict[str, Any]:
        return copiar_ataque_editor(self.tipo, str(self.campos.get("nome") or EDITOR_ATTACK_NAME), 0)

    def json_texto(self) -> str:
        payload = {"animacao": self.animacao(), "alvificacao": self.alvificacao()}
        self._json_cache = json.dumps(payload, ensure_ascii=False, indent=2)
        return self._json_cache


# ---------------------------------------------------------------------------
# Painel pygame simples
# ---------------------------------------------------------------------------


class PainelEditorAtaque:
    def __init__(self, estado: EstadoEditorAtaque) -> None:
        self.estado = estado
        self.largura = 430
        self.scroll = 0
        self.rows: list[dict[str, Any]] = []
        self.campo_ativo: str | None = None
        self.fonte = pygame.font.SysFont("consolas", 16)
        self.fonte_bold = pygame.font.SysFont("consolas", 17, bold=True)
        self.fonte_titulo = pygame.font.SysFont("consolas", 22, bold=True)
        self.dropdown_aberto: dict[str, Any] | None = None
        self.mensagem = "Edite as propriedades. Teste pelo fluxo normal: Pokémon → ataque → alvo → Pronto."

    def rect(self, surface: pygame.Surface) -> pygame.Rect:
        # Deixa a área inferior direita livre para o botão Pronto/HUD real da batalha.
        altura = max(360, surface.get_height() - 210)
        return pygame.Rect(surface.get_width() - self.largura, 0, self.largura, altura)

    def consumir_evento(self, evento: pygame.event.Event, surface: pygame.Surface, editor: "EditorIntegracaoBatalha") -> bool:
        painel = self.rect(surface)
        if evento.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if painel.collidepoint((mx, my)):
                self.scroll = max(0, self.scroll - evento.y * 34)
                return True
        if evento.type == pygame.KEYDOWN and self.campo_ativo:
            if evento.key == pygame.K_ESCAPE:
                self.campo_ativo = None
                return True
            if evento.key == pygame.K_RETURN:
                self.campo_ativo = None
                editor.aplicar_em_todos()
                return True
            if evento.key == pygame.K_BACKSPACE:
                atual = str(self.estado.valor(self.campo_ativo))
                self.estado.setar(self.campo_ativo, atual[:-1])
                editor.aplicar_em_todos()
                return True
            if evento.unicode:
                atual = str(self.estado.valor(self.campo_ativo))
                self.estado.setar(self.campo_ativo, atual + evento.unicode)
                editor.aplicar_em_todos()
                return True
            return True
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.dropdown_aberto:
                if self._click_dropdown(evento.pos, editor):
                    return True
                self.dropdown_aberto = None
            if not painel.collidepoint(evento.pos):
                return False
            self._click(evento.pos, editor)
            return True
        return False

    def _click_dropdown(self, pos, editor: "EditorIntegracaoBatalha") -> bool:
        dd = self.dropdown_aberto or {}
        for item in dd.get("itens", []):
            if item["rect"].collidepoint(pos):
                self.estado.setar(dd["chave"], item["valor"])
                self.dropdown_aberto = None
                self.campo_ativo = None
                editor.aplicar_em_todos()
                return True
        return False

    def _click(self, pos, editor: "EditorIntegracaoBatalha") -> None:
        self.campo_ativo = None
        for row in self.rows:
            if not row["rect"].collidepoint(pos):
                continue
            chave = row["chave"]
            tipo = row["tipo"]
            if tipo in {"select", "bool"}:
                opcoes = list(row.get("opcoes") or [])
                if tipo == "bool":
                    opcoes = ["false", "true"]
                self.dropdown_aberto = {"chave": chave, "rect": row["rect"], "opcoes": opcoes, "itens": []}
            elif tipo == "input":
                self.dropdown_aberto = None
                self.campo_ativo = chave
            elif tipo == "acao":
                acao = str(row.get("acao") or "")
                if acao == "adicionar_alvo":
                    self.estado.adicionar_grupo_alvo()
                elif acao.startswith("remover_alvo:"):
                    self.estado.remover_grupo_alvo(parse_int(acao.split(":", 1)[1], -1))
                self.dropdown_aberto = None
            editor.aplicar_em_todos()
            return
        self.dropdown_aberto = None

    def desenhar(self, surface: pygame.Surface, editor: "EditorIntegracaoBatalha") -> None:
        painel = self.rect(surface)
        overlay = pygame.Surface(painel.size, pygame.SRCALPHA)
        overlay.fill((13, 18, 28, 244))
        surface.blit(overlay, painel.topleft)
        pygame.draw.line(surface, (98, 122, 170), (painel.x, 0), (painel.x, painel.h), 2)

        x = painel.x + 16
        y = 14 - self.scroll
        self.rows = []

        def texto(txt, pos, fonte=None, cor=(238, 242, 255)):
            img = (fonte or self.fonte).render(str(txt), True, cor)
            surface.blit(img, pos)
            return img.get_height()

        # Cabeçalho fixo
        head_rect = pygame.Rect(painel.x, 0, painel.w, 86)
        pygame.draw.rect(surface, (18, 26, 42), head_rect)
        texto("Propriedades do Ataque", (painel.x + 16, 10), self.fonte_titulo, (255, 242, 166))
        sel = getattr(editor.controlador, "pokemon_selecionado", None)
        nome_sel = getattr(sel, "Nome", "nenhum") if sel is not None else "nenhum"
        texto(f"Selecionado: {nome_sel}", (painel.x + 16, 42), self.fonte, (215, 225, 245))
        texto("Teste normal: ataque da ficha → alvo → Pronto", (painel.x + 16, 64), self.fonte, (160, 196, 255))

        y = max(y, 104)
        y = self._secao(surface, x, y, "Ataque")
        y = self._row(surface, x, y, "Nome", "nome", "input")
        y = self._row(surface, x, y, "Tipo", "tipo", "select", EstadoEditorAtaque.TIPOS)
        y = self._row(surface, x, y, "Modelo", "modelo", "select", EstadoEditorAtaque.MODELOS)
        y = self._row(surface, x, y, "Estilo lógico", "estilo_logico", "select", ["alvo", "ativo"])

        y = self._secao(surface, x, y, "Alvificação real")
        for idx, _grupo in enumerate(self.estado.alvos_config):
            y = self._secao(surface, x, y, f"Grupo {idx + 1}")
            prefixo = f"alvos.{idx}"
            y = self._row(surface, x, y, "Tipo alvo", f"{prefixo}.tipo", "select", EstadoEditorAtaque.ALVOS)
            y = self._row(surface, x, y, "Lados", f"{prefixo}.lados_permitidos", "select", EstadoEditorAtaque.LADOS)
            y = self._row(surface, x, y, "Exige ocupado", f"{prefixo}.exige_area_ocupada", "bool")
            y = self._row(surface, x, y, "Inclui reserva", f"{prefixo}.inclui_reserva", "bool")
            y = self._row(surface, x, y, "Quantidade", f"{prefixo}.quantidade", "input")
            if len(self.estado.alvos_config) > 1:
                y = self._row_acao(surface, x, y, "Remover grupo", f"remover_alvo:{idx}")
        y = self._row_acao(surface, x, y, "Adicionar grupo", "adicionar_alvo")

        y = self._secao(surface, x, y, "Efeitos")
        y = self._row(surface, x, y, "Efeito executor", "efeito_executor", "input")
        y = self._row(surface, x, y, "Efeito alvo 1", "efeito_alvo", "input")
        y = self._row(surface, x, y, "Efeito alvo 2", "efeito_alvo2", "input")
        y = self._row(surface, x, y, "Efeito alvo 3", "efeito_alvo3", "input")

        modelo = self.estado.modelo
        if modelo not in {"EfeitoProprio", "Laser"}:
            y = self._row(surface, x, y, "Simultâneo", "simultaneo", "bool")
        if modelo != "EfeitoProprio":
            y = self._row(surface, x, y, "Intervalo", "intervalo", "input")

        y = self._secao(surface, x, y, f"Campos do modelo: {modelo}")
        campos = self._campos_modelo(modelo)
        for item in campos:
            if len(item) == 2:
                label, chave = item
                y = self._row(surface, x, y, label, chave, "input")
            else:
                label, chave, tipo, opcoes = item
                y = self._row(surface, x, y, label, chave, tipo, opcoes)

        y += 8
        msg = self._quebrar(self.mensagem, 42)
        for linha in msg:
            texto(linha, (x, y), self.fonte, (255, 220, 150))
            y += 20

        self._desenhar_dropdown(surface, painel)

        # sombra superior fixa por cima do scroll
        pygame.draw.rect(surface, (18, 26, 42), head_rect, 1)

    def _campos_modelo(self, modelo: str) -> list[tuple]:
        base: list[tuple] = []
        if modelo in {"Avanço", "Salto"}:
            base.extend([("Velocidade", "velocidade"), ("Dist. parada", "distancia_parada"), ("Retornar", "retornar", "bool", [])])
            if modelo == "Salto":
                base.append(("Altura", "altura"))
        elif modelo in {"Raio", "Laser", "Jato"}:
            base.extend([("Cor RGB", "cor"), ("Duração", "duracao"), ("Largura/tamanho", "largura")])
        elif modelo == "Projetil":
            base.extend([("Projétil", "projetil"), ("Velocidade", "velocidade"), ("Tamanho", "tamanho"), ("Cor genérico", "cor")])
        elif modelo == "Explosão":
            base.extend([
                ("Contato", "contato", "select", EstadoEditorAtaque.CONTATOS_EXPLOSAO),
                ("Efeito secund.", "efeito_impacto_secundario"),
                ("Raio explosão", "raio_explosao"),
                ("Duração onda", "duracao_onda"),
                ("Cor onda", "cor_onda"),
                ("Largura onda", "largura_onda"),
            ])
            contato = str(self.estado.campos.get("contato") or "Projetil")
            if contato == "Projetil":
                base.extend([("Projétil", "projetil"), ("Velocidade", "velocidade"), ("Tamanho", "tamanho"), ("Cor contato", "cor")])
            elif contato in {"Avanço", "Salto"}:
                base.extend([("Velocidade", "velocidade"), ("Dist. parada", "distancia_parada"), ("Retornar", "retornar", "bool", [])])
                if contato == "Salto":
                    base.append(("Altura", "altura"))
            elif contato in {"Raio", "Jato"}:
                base.extend([("Cor contato", "cor"), ("Duração", "duracao"), ("Largura/tamanho", "largura")])
        elif modelo in {"EfeitoProprio", "EfeitoAlvo"}:
            base.extend([("Duração efeito", "duracao"), ("Escala", "escala"), ("Opacidade", "opacidade")])
        return base

    def _secao(self, surface, x, y, titulo) -> int:
        y += 10
        pygame.draw.line(surface, (70, 88, 128), (x, y + 13), (surface.get_width() - 18, y + 13), 1)
        img = self.fonte_bold.render(str(titulo), True, (255, 242, 166))
        surface.blit(img, (x, y))
        return y + 28

    def _row(self, surface, x, y, label, chave, tipo, opcoes=None) -> int:
        h = 28
        label_rect = pygame.Rect(x, y, 150, h)
        value_rect = pygame.Rect(x + 156, y, self.largura - 188, h)
        cor_label = (214, 222, 240)
        surface.blit(self.fonte.render(str(label), True, cor_label), (label_rect.x, label_rect.y + 6))
        ativo = self.campo_ativo == chave
        bg = (28, 38, 58) if not ativo else (42, 58, 86)
        pygame.draw.rect(surface, bg, value_rect, border_radius=6)
        pygame.draw.rect(surface, (90, 110, 150), value_rect, 1, border_radius=6)
        valor = str(self.estado.valor(chave))
        if tipo == "bool":
            valor = "true" if parse_bool(valor) else "false"
        txt_cor = (250, 250, 255) if valor else (126, 136, 160)
        surface.blit(self.fonte.render(valor or "null", True, txt_cor), (value_rect.x + 8, value_rect.y + 6))
        if tipo in {"select", "bool"}:
            surface.blit(self.fonte.render("▼", True, (175, 190, 220)), (value_rect.right - 20, value_rect.y + 6))
        self.rows.append({"rect": value_rect, "chave": chave, "tipo": tipo, "opcoes": opcoes or []})
        return y + h + 4

    def _row_acao(self, surface, x, y, label, acao) -> int:
        h = 28
        rect = pygame.Rect(x + 156, y, self.largura - 188, h)
        surface.blit(self.fonte.render(str(label), True, (214, 222, 240)), (x, y + 6))
        pygame.draw.rect(surface, (43, 58, 88), rect, border_radius=6)
        pygame.draw.rect(surface, (116, 146, 205), rect, 1, border_radius=6)
        surface.blit(self.fonte_bold.render(str(label), True, (250, 250, 255)), (rect.x + 8, rect.y + 6))
        self.rows.append({"rect": rect, "chave": str(acao), "tipo": "acao", "acao": str(acao)})
        return y + h + 4

    def _desenhar_dropdown(self, surface: pygame.Surface, painel: pygame.Rect) -> None:
        if not self.dropdown_aberto:
            return
        rect = pygame.Rect(self.dropdown_aberto.get("rect") or pygame.Rect(0, 0, 0, 0))
        opcoes = list(self.dropdown_aberto.get("opcoes") or [])
        if not opcoes:
            return
        item_h = 26
        max_h = min(len(opcoes) * item_h, max(120, painel.height - 40))
        altura = min(len(opcoes) * item_h, max_h)
        abrir_baixo = rect.bottom + altura <= painel.bottom - 8
        y = rect.bottom + 4 if abrir_baixo else max(painel.y + 8, rect.top - altura - 4)
        drop = pygame.Rect(rect.x, y, rect.w, altura)
        pygame.draw.rect(surface, (18, 27, 44), drop, border_radius=6)
        pygame.draw.rect(surface, (130, 154, 205), drop, 2, border_radius=6)
        self.dropdown_aberto["itens"] = []
        for i, valor in enumerate(opcoes):
            item_rect = pygame.Rect(drop.x, drop.y + i * item_h, drop.w, item_h)
            if item_rect.bottom > drop.bottom:
                break
            if item_rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(surface, (44, 63, 96), item_rect)
            atual = str(self.estado.valor(self.dropdown_aberto.get("chave")))
            cor = (255, 242, 166) if str(valor) == atual else (238, 242, 255)
            img = self.fonte.render(str(valor), True, cor)
            surface.blit(img, (item_rect.x + 8, item_rect.y + 5))
            self.dropdown_aberto["itens"].append({"rect": item_rect, "valor": valor})

    def _botao(self, surface, rect, texto, cor):
        # Mantido apenas para compatibilidade interna; o painel não usa botões próprios.
        pygame.draw.rect(surface, cor, rect, border_radius=8)
        pygame.draw.rect(surface, (220, 230, 255), rect, 1, border_radius=8)
        img = self.fonte_bold.render(texto, True, (255, 255, 255))
        surface.blit(img, img.get_rect(center=rect.center))

    @staticmethod
    def _quebrar(texto: str, n: int) -> list[str]:
        palavras = str(texto or "").split()
        linhas, atual = [], ""
        for p in palavras:
            if len(atual) + len(p) + 1 > n:
                linhas.append(atual)
                atual = p
            else:
                atual = f"{atual} {p}".strip()
        if atual:
            linhas.append(atual)
        return linhas or [""]


# ---------------------------------------------------------------------------
# Integração com ControladorBatalha real
# ---------------------------------------------------------------------------


class EditorIntegracaoBatalha:
    def __init__(self, controlador: ControladorBatalha, estado: EstadoEditorAtaque, painel: PainelEditorAtaque):
        self.controlador = controlador
        self.estado = estado
        self.painel = painel
        self._ultimo_total_acoes = 0
        self._executando_log = False
        self.aplicar_em_todos()
        self._instalar_botao_pronto_local()


    def _instalar_botao_pronto_local(self) -> None:
        # O HUD real chama controlador.enviar_jogada_pronta(). Aqui mantemos o botão
        # Pronto oficial, mas trocamos a saída de rede por um log visual local.
        self.controlador.enviar_jogada_pronta = self.enviar_jogada_pronta_local  # type: ignore[method-assign]
        self.controlador.timer_rodada_max = 999999.0
        self.controlador.timer_rodada = 999999.0

    def aplicar_em_todos(self) -> None:
        props = self.estado.props()
        ataque = self.estado.ataque()
        self._registrar_ataque_na_ficha(props, ataque)
        montador = getattr(self.controlador, "montador_jogadas", None)
        if montador is not None:
            # Fonte oficial que o MontadorJogadas consulta ao iniciar a preparação.
            montador.propriedades_ataques[str(EDITOR_ATTACK_CODE)] = copy.deepcopy(props)
            montador.propriedades_ataques[int(EDITOR_ATTACK_CODE)] = copy.deepcopy(props)
            # Alguns caminhos procuram por nome; manter uma entrada nomeada evita falha se o code mudar de tipo.
            montador.propriedades_ataques[str(ataque.get("Nome") or ataque.get("Ataque"))] = copy.deepcopy(props)
            if getattr(montador, "estado_montagem", "") == "preparando_ataque" and hasattr(montador, "_normalizar_alvos_config"):
                montador.alvos_config = montador._normalizar_alvos_config(props)
        for pokemon in list(getattr(self.controlador, "pokemons", []) or []):
            pokemon.ListaAtaques = [copy.deepcopy(ataque)]
            # Editor é visual: deixa qualquer Pokémon capaz de pagar o ataque.
            pokemon.Energia = max(float(getattr(pokemon, "Energia", 0.0) or 0.0), 999.0)
            pokemon.EnergiaMax = max(float(getattr(pokemon, "EnergiaMax", 0.0) or 0.0), 999.0)
            pokemon.EnergiaPrevista = pokemon.Energia
            pokemon.CustoPrevistoPendente = 0.0
            pokemon.PodePagarPrevisao = True
        try:
            self.controlador.modo_teste = True
            if hasattr(self.controlador, "definir_modo_teste"):
                self.controlador.definir_modo_teste(True)
        except Exception:
            pass

    def _registrar_ataque_na_ficha(self, props: dict[str, Any], ataque: dict[str, Any]) -> None:
        # A FichaPokemonBatalha só permite clicar no ataque se o estilo técnico existir
        # no cache interno carregado por carregar_propriedades_ataques(). Como o ataque
        # do editor é sintético, precisamos registrá-lo ali também. Sem isso, o botão
        # da ficha aparece, mas o clique não seleciona nada.
        if FichaPokemonBatalha is None:
            return
        try:
            if FichaPokemonBatalha._CACHE_ESTILO_ATAQUES is None:
                FichaPokemonBatalha._CACHE_ESTILO_ATAQUES = {}
            cache = FichaPokemonBatalha._CACHE_ESTILO_ATAQUES
            estilo = str(props.get("estilo_logico") or "alvo").strip().casefold() or "alvo"
            nomes = {
                EDITOR_ATTACK_NAME,
                str(ataque.get("Ataque") or ""),
                str(ataque.get("Nome") or ""),
                str(props.get("nome") or ""),
            }
            for nome in nomes:
                nome = str(nome or "").strip()
                if nome:
                    cache[nome.casefold()] = estilo
        except Exception:
            pass

    def pokemon_executor(self):
        sel = getattr(self.controlador, "pokemon_selecionado", None)
        if sel is not None and sel.esta_vivo() and sel.esta_ativo() and not sel.esta_na_reserva():
            return sel
        for p in list(getattr(self.controlador, "pokemons", []) or []):
            if p.esta_vivo() and p.esta_ativo() and not p.esta_na_reserva():
                return p
        return None

    def atualizar(self) -> None:
        # Mantém o ataque único sincronizado com o painel e impede passagem automática por tempo.
        self.aplicar_em_todos()
        self.controlador.timer_rodada_max = 999999.0
        self.controlador.timer_rodada = 999999.0

    def enviar_jogada_pronta_local(self) -> None:
        ctrl = self.controlador
        montador = getattr(ctrl, "montador_jogadas", None)
        if montador is None or str(getattr(ctrl, "estado_batalha", "")) != "montando_jogada":
            return
        acoes = [dict(a) for a in list(getattr(montador, "acoes_preparadas", []) or []) if str(a.get("tipo") or "") == "ataque"]
        if not acoes:
            self.painel.mensagem = "Prepare o ataque pelo fluxo normal antes de apertar Pronto."
            return
        try:
            ctrl._ocultar_montagem_visual()
        except Exception:
            pass
        log = self._montar_log_visual_multi(acoes)
        self.painel.mensagem = "Rodando animação preparada pelo botão Pronto."
        ctrl.receber_log(log)

    def _montar_log_visual_multi(self, acoes: list[dict[str, Any]]) -> dict[str, Any]:
        historico: list[dict[str, Any]] = []
        ordem = 1
        passo = 1
        for acao in acoes:
            log = self._montar_log_visual(acao)
            for evento in list(log.get("historico") or []):
                ev = copy.deepcopy(evento)
                ev["passo"] = passo
                ev["ordem"] = ordem
                ev["id_evento"] = f"editor_{ordem:03d}"
                historico.append(ev)
                ordem += 1
            passo += 1
        return {
            "rodada": int(getattr(self.controlador, "rodada_atual", 1) or 1),
            "historico": historico,
            "resultado": {
                "rodada_atual": int(getattr(self.controlador, "rodada_atual", 1) or 1),
                "estado_batalha": "montando_jogada",
                "pokemons": {},
                "finalizada": False,
            },
        }

    def _montar_log_visual(self, acao: dict[str, Any]) -> dict[str, Any]:
        ctrl = self.controlador
        props = self.estado.props()
        animacao = props["animacao"]
        ataque = self.estado.ataque()
        executor = ctrl.pokemons_por_id.get(str(acao.get("pokemon_id") or ""))
        alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
        alvos_selecionados = self._alvos_selecionados(acao)
        area_alvo = self._area_alvo_visual(acao)
        alvos = self._resolver_alvos_da_acao(acao, props)
        alvo_principal = alvos[0] if alvos else None

        alvos_secundarios: list[Any] = []
        if normalizar(animacao.get("modelo")) == "explosao" and alvo_principal is not None:
            alvos_secundarios = self._secundarios_explosao(alvo_principal, executor)

        alvos_visuais = list(alvos)
        if normalizar(animacao.get("modelo")) == "explosao" and alvo_principal is not None:
            alvos_visuais = [alvo_principal, *alvos_secundarios]

        alvos_ids = [str(getattr(p, "id_batalha", "")) for p in alvos_visuais if getattr(p, "id_batalha", None)]
        alvo_principal_id = str(getattr(alvo_principal, "id_batalha", "")) if alvo_principal is not None else None
        secundarios_ids = [str(getattr(p, "id_batalha", "")) for p in alvos_secundarios if getattr(p, "id_batalha", None)]

        dados_base = {
            "id_acao": acao.get("id_acao") or acao.get("id") or 1,
            "ataque_id": EDITOR_ATTACK_CODE,
            "ataque_nome": ataque["Nome"],
            "tipo_ataque": self.estado.tipo,
            "usuario_id": getattr(executor, "id_batalha", None),
            "usuario_nome": getattr(executor, "Nome", None),
            "pokemon_id": getattr(executor, "id_batalha", None),
            "pokemon_nome": getattr(executor, "Nome", None),
            "area_origem": getattr(executor, "AreaId", None),
            "area_alvo": area_alvo,
            "alvos_ids": alvos_ids,
            "alvo_principal_id": alvo_principal_id,
            "alvos_secundarios_ids": secundarios_ids,
            "alvos_selecionados": alvos_selecionados,
            "animacao": copy.deepcopy(animacao),
        }
        if alvo_principal is not None:
            dados_base.update({
                "alvo_id": alvo_principal_id,
                "alvo_nome": getattr(alvo_principal, "Nome", None),
                "area_alvo_real": getattr(alvo_principal, "AreaId", area_alvo),
            })

        historico: list[dict[str, Any]] = []
        ordem = 1

        def ev(tipo: str, dados: dict[str, Any]) -> None:
            nonlocal ordem
            historico.append({
                "tipo": tipo,
                "passo": 1,
                "ordem": ordem,
                "id_evento": f"editor_{ordem:03d}",
                "dados": dados,
            })
            ordem += 1

        ev("ataque_usado", dict(dados_base))

        if alvo_principal is not None:
            ev("ataque_acertou", {**dados_base, "alvo_id": alvo_principal_id, "alvo_nome": alvo_principal.Nome, "area_alvo_real": alvo_principal.AreaId})
        elif area_alvo:
            ev("ataque_acertou", dict(dados_base))

        if parse_bool(self.estado.campos.get("mostrar_cartucho"), True):
            valor = parse_num(self.estado.campos.get("valor_cartucho"), 35)
            for alvo_poke in alvos:
                if alvo_poke is None:
                    continue
                ev("pokemon_sofreu_dano", {
                    **dados_base,
                    "alvo_id": alvo_poke.id_batalha,
                    "pokemon_id": alvo_poke.id_batalha,
                    "alvo_nome": alvo_poke.Nome,
                    "pokemon_nome": alvo_poke.Nome,
                    "valor": valor,
                    "critico": False,
                    "impacto_principal": str(alvo_poke.id_batalha) == str(alvo_principal_id),
                    "impacto_secundario": False,
                })
            if normalizar(animacao.get("modelo")) == "explosao":
                for alvo_poke in alvos_secundarios:
                    ev("pokemon_sofreu_dano", {
                        **dados_base,
                        "alvo_id": alvo_poke.id_batalha,
                        "pokemon_id": alvo_poke.id_batalha,
                        "alvo_nome": alvo_poke.Nome,
                        "pokemon_nome": alvo_poke.Nome,
                        "valor": max(1, valor * 0.5),
                        "critico": False,
                        "impacto_principal": False,
                        "impacto_secundario": True,
                    })

        return {
            "rodada": int(getattr(ctrl, "rodada_atual", 1) or 1),
            "historico": historico,
            "resultado": {
                "rodada_atual": int(getattr(ctrl, "rodada_atual", 1) or 1),
                "estado_batalha": "montando_jogada",
                "pokemons": {},
                "finalizada": False,
            },
        }

    def _resolver_alvos_da_acao(self, acao: dict[str, Any], props: dict[str, Any]) -> list[Any]:
        ctrl = self.controlador
        alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
        if str(alvo.get("tipo") or "").lower() == "multi":
            saida = []
            vistos = set()
            for selecao in list(alvo.get("alvos") or []):
                if not isinstance(selecao, dict):
                    continue
                if str(selecao.get("tipo") or "").lower() == "pokemon" and selecao.get("pokemon_id"):
                    poke = ctrl.pokemons_por_id.get(str(selecao.get("pokemon_id")))
                    if poke is not None and poke.id_batalha not in vistos:
                        vistos.add(poke.id_batalha)
                        saida.append(poke)
                    continue
                area_id = selecao.get("area_id")
                if not area_id:
                    continue
                config = selecao.get("config") if isinstance(selecao.get("config"), dict) else {}
                try:
                    areas = ctrl.montador_jogadas.areas_afetadas_por_config(area_id, config)
                except Exception:
                    areas = list(selecao.get("areas") or [area_id])
                for aid in areas or [area_id]:
                    poke = ctrl.arena.pokemon_na_area(aid)
                    if poke is not None and poke.id_batalha not in vistos:
                        vistos.add(poke.id_batalha)
                        saida.append(poke)
            return saida
        if str(alvo.get("tipo") or "").lower() == "pokemon" and alvo.get("pokemon_id"):
            poke = ctrl.pokemons_por_id.get(str(alvo.get("pokemon_id")))
            return [poke] if poke is not None else []
        area_id = alvo.get("area_id")
        if not area_id:
            executor = ctrl.pokemons_por_id.get(str(acao.get("pokemon_id") or ""))
            return [executor] if props.get("estilo_logico") == "ativo" and executor is not None else []
        areas = []
        try:
            areas = ctrl.montador_jogadas.areas_afetadas_por_alvo(area_id, props)
        except Exception:
            areas = [area_id]
        saida = []
        vistos = set()
        for aid in areas or [area_id]:
            poke = ctrl.arena.pokemon_na_area(aid)
            if poke is not None and poke.id_batalha not in vistos:
                vistos.add(poke.id_batalha)
                saida.append(poke)
        if saida:
            return saida
        return []

    @staticmethod
    def _alvos_selecionados(acao: dict[str, Any]) -> list[dict[str, Any]]:
        alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
        if str(alvo.get("tipo") or "").lower() == "multi":
            return [copy.deepcopy(item) for item in list(alvo.get("alvos") or []) if isinstance(item, dict)]
        return [copy.deepcopy(alvo)] if alvo else []

    @staticmethod
    def _area_alvo_visual(acao: dict[str, Any]):
        alvo = acao.get("alvo") if isinstance(acao.get("alvo"), dict) else {}
        if str(alvo.get("tipo") or "").lower() == "multi":
            for selecao in list(alvo.get("alvos") or []):
                if isinstance(selecao, dict) and selecao.get("area_id"):
                    return selecao.get("area_id")
            return None
        return alvo.get("area_id")

    def _secundarios_explosao(self, alvo_principal, executor) -> list[Any]:
        if alvo_principal is None:
            return []
        area = str(getattr(alvo_principal, "AreaId", "") or "")
        if len(area) < 2:
            return []
        prefixo = area[0].upper()
        try:
            idx = int(area[1:]) - 1
        except Exception:
            return []
        row, col = idx // 3, idx % 3
        saida = []
        for r in range(max(0, row - 1), min(2, row + 1) + 1):
            for c in range(max(0, col - 1), min(2, col + 1) + 1):
                aid = f"{prefixo}{r * 3 + c + 1}"
                if aid == area:
                    continue
                poke = self.controlador.arena.pokemon_na_area(aid)
                if poke is None or not poke.esta_vivo():
                    continue
                if executor is not None and int(getattr(poke, "lado_id", -1)) == int(getattr(executor, "lado_id", -2)):
                    continue
                saida.append(poke)
        return saida


# ---------------------------------------------------------------------------
# Cena + main
# ---------------------------------------------------------------------------


class CenaEditorAnimacaoAtaques:
    def __init__(self, controlador, painel: PainelEditorAtaque, editor: EditorIntegracaoBatalha, clock):
        self.controlador = controlador
        self.painel = painel
        self.editor = editor
        self.clock = clock

    def tela_atual_eh_complexa(self):
        return True

    def render_base(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        surface.fill((8, 12, 18))
        self.controlador.desenhar(surface)

    def render_hud(self, surface, JOGO, EVENTOS, dt):
        _ = (JOGO, EVENTOS, dt)
        self.painel.desenhar(surface, self.editor)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Editor Animação Ataques - Batalha Real Local")
    janela, janela_opengl = criar_janela()
    tela = pygame.Surface(janela.get_size()).convert()
    pipeline = PipelineGrafica(tela, tela_display=janela)
    if janela_opengl and not pipeline.shader_disponivel():
        janela = pygame.display.set_mode(tela.get_size(), pygame.RESIZABLE)
        tela = pygame.Surface(janela.get_size()).convert()
        pipeline = PipelineGrafica(tela, tela_display=janela)
    clock = pygame.time.Clock()

    estado_inicial = montar_estado_inicial()
    estado_inicial["modo_teste"] = True
    estado_inicial["tipo_batalha"] = "simulador"
    camera = CameraBatalha(tela.get_size(), posicao_inicial_tiles=(0, 0), tile_px=40)
    controlador = ControladorBatalha(camera=camera)
    controlador.iniciar(estado_inicial)
    controlador.modo_teste = True
    controlador.estado_batalha = "montando_jogada"

    estado_editor = EstadoEditorAtaque()
    painel = PainelEditorAtaque(estado_editor)
    editor = EditorIntegracaoBatalha(controlador, estado_editor, painel)

    jogo = JogoSimulador()
    cena = CenaEditorAnimacaoAtaques(controlador, painel, editor, clock)

    rodando = True
    while rodando:
        dt = clock.tick(180) / 1000.0
        eventos = pygame.event.get()
        eventos_jogo = []
        for evento in eventos:
            if evento.type == pygame.QUIT:
                rodando = False
                continue
            if evento.type == pygame.VIDEORESIZE:
                pipeline.liberar()
                janela, janela_opengl = criar_janela((max(960, evento.w), max(540, evento.h)))
                tela = pygame.Surface(janela.get_size()).convert()
                pipeline = PipelineGrafica(tela, tela_display=janela)
                if janela_opengl and not pipeline.shader_disponivel():
                    janela = pygame.display.set_mode(tela.get_size(), pygame.RESIZABLE)
                    tela = pygame.Surface(janela.get_size()).convert()
                    pipeline = PipelineGrafica(tela, tela_display=janela)
                controlador.camera.TamanhoTelaPx = (float(tela.get_width()), float(tela.get_height()))
                continue
            if painel.consumir_evento(evento, tela, editor):
                continue
            eventos_jogo.append(evento)

        controlador.timer_rodada_max = 999999.0
        controlador.timer_rodada = 999999.0
        controlador.atualizar(dt, eventos_jogo)
        editor.atualizar()

        if controlador.solicitou_encerrar_batalha:
            rodando = False
            continue

        pipeline.renderizar_frame(jogo=jogo, cena=cena, eventos=eventos_jogo, dt=dt)
        pygame.display.flip()

    pipeline.liberar()
    pygame.quit()


if __name__ == "__main__":
    main()
