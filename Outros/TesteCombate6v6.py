from __future__ import annotations

"""
Teste manual 6v6 para o pipeline novo de combate.

Como rodar:
- Modo visual (Pygame 1920x1080 @ 180 FPS):
    python Outros/TesteCombate6v6.py
- Smoke test sem interface:
    python Outros/TesteCombate6v6.py --smoke

Controles:
- Tab: alterna lado selecionado (aliados/inimigos)
- 1..6: seleciona pokemon do lado atual
- F1..F6: seleciona pokemon aliado direto
- F7..F12: seleciona pokemon inimigo direto
- A/D ou setas esquerda/direita: troca ataque
- Shift+1..9 / Ctrl+1..9: seleciona ataque por indice (1-based)
- Mouse move: mira/destino
- Clique esquerdo: prepara jogada do pokemon selecionado
- Clique direito ou Esc: cancela preparo atual
- Enter: executa turno
- Backspace: remove ultima jogada preparada
- R: resetar batalha fabricada
- L: alterna painel de log
- H: alterna ajuda
- Espaco: pausa/despausa visual
"""

import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SimuladorServerJogo.Batalha.LeitorJogadas import LeitorJogadas
from SimuladorServerJogo.Batalha.Combate.CatalogoAtaques import carregar_catalogo_ataques
from SimuladorServerJogo.Batalha.Combate.ValidadorAtaques import validar_arquivo

ARQUIVO_ATAQUES = Path("Dados") / "Pokemon Global Server - AtaquesCombate.json"
ARQUIVO_ULTIMO_LOG = Path("Outros") / "ultimo_log_teste_combate.json"

ATAQUES_OBRIGATORIOS = [
    "Investida",
    "Biscoito",
    "Enraivecer",
    "Provocar",
    "Proteger",
    "Arranhar",
    "Recarga",
    "Energia",
    "Hiper Raio",
    "Guilhotina",
    "Disparo",
    "Chifrada",
    "Resetar",
    "Tankar",
    "Estocada",
    "Bola Climática",
    "Hiper Presa",
    "Investida Selvagem",
]

FORMAS_ESPERADAS = {
    "Investida": "impulso",
    "Investida Selvagem": "impulso",
    "Biscoito": "projetil",
    "Enraivecer": "self",
    "Provocar": "self",
    "Proteger": "alvo",
    "Arranhar": "cone",
    "Recarga": "self",
    "Energia": "projetil",
    "Hiper Raio": "laser",
    "Guilhotina": "cone",
    "Disparo": "projetil",
    "Chifrada": "dash",
    "Resetar": "alvo",
    "Tankar": "self",
    "Estocada": "cone_invertido",
    "Bola Climática": "projetil_explosivo",
    "Hiper Presa": "alvo",
}

FORMAS_ALVO = {"alvo"}
FORMAS_SELF = {"self"}


@dataclass
class PokemonTesteBatalha:
    Uid: str
    Nome: str
    Lado: str
    Posicao: list[float]
    Vida: float
    VidaAtual: float
    EnergiaMax: float
    Energia: float
    Barreira: float
    Efeitos: list[dict[str, Any]] = field(default_factory=list)
    Atk: float = 90.0
    SpA: float = 90.0
    Def: float = 80.0
    SpD: float = 80.0
    Per: float = 70.0
    Mag: float = 65.0
    Vel: float = 80.0
    Massa: float = 1.2
    RaioColisao: float = 0.55
    Int: float = 55.0
    Durabilidade: float = 40.0
    Amplificacao: float = 0.0
    CrC: float = 0.1
    CrD: float = 1.5
    Assertividade: float = 0.85
    Tipos: list[str] = field(default_factory=lambda: ["Normal"])
    VariacoesFixas: dict[str, float] = field(default_factory=dict)
    VariacoesTemporarias: dict[str, float] = field(default_factory=dict)
    ForaDeCombate: bool = False
    Velocidade: list[float] = field(default_factory=lambda: [0.0, 0.0])

    def obter_atributo(self, nome: str) -> float:
        valor = getattr(self, str(nome), 0.0)
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0


class SistemaBatalhaTeste:
    """Este adaptador existe apenas para teste manual 6v6 e não deve ser usado no servidor real."""

    def __init__(self) -> None:
        self.TurnoAtual = 1
        self.TickGlobal = 0
        self.ClimaAtual = "limpo"
        self.Rng = random.Random("teste-combate-6v6")
        self.Encerrada = False

        self._pokemons = self._criar_pokemons()
        self._pendentes: dict[str, list[dict[str, Any]]] = {}
        self._ultimo_log: dict[str, Any] = {}

    def _criar_pokemons(self) -> list[PokemonTesteBatalha]:
        pokemons: list[PokemonTesteBatalha] = []
        ys = [2.5, 5.5, 8.5, 11.5, 14.5, 17.5]
        for i in range(6):
            pokemons.append(
                PokemonTesteBatalha(
                    Uid=f"ally-{i+1}",
                    Nome=f"Aliado {i+1}",
                    Lado="jogador",
                    Posicao=[7.0, ys[i]],
                    Vida=100.0,
                    VidaAtual=100.0,
                    EnergiaMax=100.0,
                    Energia=100.0,
                    Barreira=0.0,
                    Atk=90 + i * 4,
                    SpA=80 + i * 3,
                    Def=75 + i * 2,
                    SpD=70 + i * 2,
                    Per=70 + i,
                    Mag=65 + i,
                    Vel=80 + i * 2,
                    Massa=1.1 + i * 0.05,
                    Int=55 + i,
                )
            )
            pokemons.append(
                PokemonTesteBatalha(
                    Uid=f"enemy-{i+1}",
                    Nome=f"Inimigo {i+1}",
                    Lado="inimigo",
                    Posicao=[33.0, ys[i]],
                    Vida=100.0,
                    VidaAtual=100.0,
                    EnergiaMax=100.0,
                    Energia=100.0,
                    Barreira=0.0,
                    Atk=88 + i * 4,
                    SpA=82 + i * 3,
                    Def=78 + i * 2,
                    SpD=72 + i * 2,
                    Per=71 + i,
                    Mag=66 + i,
                    Vel=79 + i * 2,
                    Massa=1.1 + i * 0.05,
                    Int=56 + i,
                )
            )
        return pokemons

    def adicionar_jogadas(self, client_id: str, jogadas: list[dict[str, Any]]) -> None:
        self._pendentes[str(client_id)] = [dict(item) for item in jogadas if isinstance(item, dict)]

    def coletar_jogadas_pendentes_turno(self, client_id: str) -> tuple[str, list[dict[str, Any]]]:
        return "pronto", [dict(item) for item in self._pendentes.get(str(client_id), [])]

    def listar_ativos(self) -> list[PokemonTesteBatalha]:
        return [p for p in self._pokemons if not p.ForaDeCombate]

    def listar_pokemons(self) -> list[PokemonTesteBatalha]:
        return list(self._pokemons)

    def detectar_encerramento(self) -> dict[str, Any]:
        vivos_jogador = any(p.VidaAtual > 0 and p.Lado == "jogador" for p in self._pokemons)
        vivos_inimigo = any(p.VidaAtual > 0 and p.Lado == "inimigo" for p in self._pokemons)
        encerrada = (not vivos_jogador) or (not vivos_inimigo)
        return {"encerrada": encerrada, "vencedor": "jogador" if vivos_jogador and not vivos_inimigo else "inimigo" if vivos_inimigo and not vivos_jogador else ""}

    def finalizar_batalha(self, rodadas_totais: int) -> dict[str, Any]:
        self.Encerrada = True
        return {"encerrada": True, "rodadas_totais": int(rodadas_totais)}

    def avancar_turno(self, ultimo_log: dict[str, Any] | None = None, tick_global_final: int | None = None) -> None:
        if isinstance(ultimo_log, dict):
            self._ultimo_log = dict(ultimo_log)
        if tick_global_final is not None:
            self.TickGlobal = int(tick_global_final)
        if not self.Encerrada:
            self.TurnoAtual += 1
        self._pendentes.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "turno": self.TurnoAtual,
            "tick": self.TickGlobal,
            "clima": self.ClimaAtual,
            "encerrada": self.Encerrada,
            "pokemons": [
                {
                    "id": p.Uid,
                    "nome": p.Nome,
                    "lado": p.Lado,
                    "vida": p.VidaAtual,
                    "energia": p.Energia,
                    "barreira": p.Barreira,
                    "efeitos": list(p.Efeitos),
                    "posicao": list(p.Posicao),
                }
                for p in self._pokemons
            ],
        }


def _carregar_catalogo_validado():
    erros = validar_arquivo(ARQUIVO_ATAQUES)
    if erros:
        raise RuntimeError("Falha de validação do catálogo: " + " | ".join(erros[:5]))

    catalogo = carregar_catalogo_ataques(ARQUIVO_ATAQUES)
    faltando = [nome for nome in ATAQUES_OBRIGATORIOS if catalogo.obter(nome) is None]
    if faltando:
        raise RuntimeError(f"Ataques obrigatórios ausentes: {faltando}")

    err_forma = []
    for nome, forma_esperada in FORMAS_ESPERADAS.items():
        spec = catalogo.obter(nome)
        forma_real = str((spec.bruto.get("execucao") or {}).get("forma") if spec else "")
        if forma_real != forma_esperada:
            err_forma.append((nome, forma_real, forma_esperada))
    if err_forma:
        raise RuntimeError(f"Formas divergentes: {err_forma}")
    return catalogo


def _montar_jogada(pokemon: PokemonTesteBatalha, spec: Any, destino: list[float], alvo_ids: list[str]) -> dict[str, Any]:
    bruto = dict(spec.bruto)
    forma = str((bruto.get("execucao") or {}).get("forma") or "")
    ataque_id = str(bruto.get("id") or "")
    custo = float(bruto.get("custo") or 10.0)
    return {
        "id": f"{pokemon.Uid}:{ataque_id}:{random.randint(1, 999999)}",
        "executor_id": pokemon.Uid,
        "ataque": bruto,
        "ataque_id": ataque_id,
        "tipo_preparo": str((bruto.get("preparo") or {}).get("tipo") or ""),
        "forma": forma,
        "origem_mundo": [float(pokemon.Posicao[0]), float(pokemon.Posicao[1])],
        "destino_mundo": [float(destino[0]), float(destino[1])],
        "alvo_ids": list(alvo_ids),
        "intensidade": 1.0,
        "custo_base": custo,
        "custo": custo,
    }


def rodar_smoke_tests() -> int:
    catalogo = _carregar_catalogo_validado()
    sistema = SistemaBatalhaTeste()
    leitor = LeitorJogadas()

    pokemons = sistema.listar_pokemons()
    atacante = next(p for p in pokemons if p.Lado == "jogador")
    alvo = next(p for p in pokemons if p.Lado == "inimigo")

    jogadas = []
    for nome in ATAQUES_OBRIGATORIOS:
        spec = catalogo.obter(nome)
        forma = str((spec.bruto.get("execucao") or {}).get("forma") or "")
        alvo_ids = [alvo.Uid] if forma in FORMAS_ALVO else []
        destino = alvo.Posicao if forma not in FORMAS_SELF else atacante.Posicao
        jogadas.append(_montar_jogada(atacante, spec, destino, alvo_ids))

    resultado = leitor.executar_turno(sistema, client_id="teste", jogadas=jogadas[:6])

    campos_obrigatorios = ["status", "rodada", "tick", "log", "eventos", "batalha"]
    faltando = [c for c in campos_obrigatorios if c not in resultado]
    if faltando:
        raise RuntimeError(f"Retorno sem campos obrigatórios: {faltando}")

    log = resultado.get("log") if isinstance(resultado.get("log"), dict) else {}
    for campo in ["sumario", "historico", "resultados"]:
        if campo not in log:
            raise RuntimeError(f"Log sem campo obrigatório: {campo}")

    print("SMOKE OK")
    print(f"- ataques validados: {len(ATAQUES_OBRIGATORIOS)}")
    print(f"- status: {resultado.get('status')}")
    print(f"- eventos: {len(resultado.get('eventos') or [])}")
    return 0


def _mundo_para_tela(pos: list[float], arena: tuple[int, int, int, int], tamanho_mundo: tuple[float, float]) -> tuple[int, int]:
    ax, ay, aw, ah = arena
    mx, my = tamanho_mundo
    x = ax + int((pos[0] / mx) * aw)
    y = ay + int((pos[1] / my) * ah)
    return x, y


def executar_visual() -> int:
    import importlib

    if importlib.util.find_spec("pygame") is None:
        print("ERRO: pygame não está instalado. Rode o modo smoke: python Outros/TesteCombate6v6.py --smoke")
        return 2

    pygame = importlib.import_module("pygame")
    pygame.init()

    tela = pygame.display.set_mode((1920, 1080))
    pygame.display.set_caption("Teste Combate 6v6 - Fase 6")
    relogio = pygame.time.Clock()
    fonte = pygame.font.SysFont("consolas", 18)
    fonte_titulo = pygame.font.SysFont("consolas", 24, bold=True)

    catalogo = _carregar_catalogo_validado()
    leitor = LeitorJogadas()

    tamanho_mundo = (40.0, 20.0)
    arena = (30, 30, 1300, 1020)

    sistema = SistemaBatalhaTeste()
    jogadas_preparadas: list[dict[str, Any]] = []
    log_visivel = True
    ajuda_visivel = True
    pausado = False
    lado_sel = "jogador"
    idx_sel_lado = 0
    idx_ataque = 0
    ultimo_resultado: dict[str, Any] = {}
    historico_curto: list[str] = []

    def pokemons_lado(lado: str) -> list[PokemonTesteBatalha]:
        return [p for p in sistema.listar_pokemons() if p.Lado == lado]

    def pokemon_selecionado() -> PokemonTesteBatalha:
        lista = pokemons_lado(lado_sel)
        return lista[max(0, min(idx_sel_lado, len(lista) - 1))]

    def ataque_selecionado_nome() -> str:
        return ATAQUES_OBRIGATORIOS[idx_ataque % len(ATAQUES_OBRIGATORIOS)]

    def alvo_por_clique(mouse_pos: tuple[int, int]) -> PokemonTesteBatalha | None:
        for p in sistema.listar_pokemons():
            px, py = _mundo_para_tela(p.Posicao, arena, tamanho_mundo)
            if math.hypot(mouse_pos[0] - px, mouse_pos[1] - py) <= 22:
                return p
        return None

    rodando = True
    while rodando:
        mouse = pygame.mouse.get_pos()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_TAB:
                    lado_sel = "inimigo" if lado_sel == "jogador" else "jogador"
                    idx_sel_lado = 0
                elif evento.key in (pygame.K_a, pygame.K_LEFT):
                    idx_ataque = (idx_ataque - 1) % len(ATAQUES_OBRIGATORIOS)
                elif evento.key in (pygame.K_d, pygame.K_RIGHT):
                    idx_ataque = (idx_ataque + 1) % len(ATAQUES_OBRIGATORIOS)
                elif evento.key == pygame.K_RETURN:
                    resultado = leitor.executar_turno(sistema, client_id="teste", jogadas=jogadas_preparadas)
                    ultimo_resultado = dict(resultado)
                    log = resultado.get("log") if isinstance(resultado.get("log"), dict) else {}
                    historico_curto = [json.dumps(item, ensure_ascii=False) for item in list(log.get("historico") or [])[-8:]]
                    ARQUIVO_ULTIMO_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
                    print("Turno executado:", resultado.get("status"), "eventos=", len(resultado.get("eventos") or []))
                    jogadas_preparadas.clear()
                elif evento.key == pygame.K_BACKSPACE:
                    if jogadas_preparadas:
                        jogadas_preparadas.pop()
                elif evento.key == pygame.K_r:
                    sistema = SistemaBatalhaTeste()
                    jogadas_preparadas.clear()
                    ultimo_resultado = {}
                    historico_curto = []
                elif evento.key == pygame.K_l:
                    log_visivel = not log_visivel
                elif evento.key == pygame.K_h:
                    ajuda_visivel = not ajuda_visivel
                elif evento.key == pygame.K_SPACE:
                    pausado = not pausado
                elif evento.key == pygame.K_ESCAPE:
                    pass
                elif pygame.K_1 <= evento.key <= pygame.K_6:
                    idx_sel_lado = int(evento.key - pygame.K_1)
                elif pygame.K_F1 <= evento.key <= pygame.K_F6:
                    lado_sel = "jogador"
                    idx_sel_lado = int(evento.key - pygame.K_F1)
                elif pygame.K_F7 <= evento.key <= pygame.K_F12:
                    lado_sel = "inimigo"
                    idx_sel_lado = int(evento.key - pygame.K_F7)
                elif (evento.mod & (pygame.KMOD_SHIFT | pygame.KMOD_CTRL)) and (pygame.K_1 <= evento.key <= pygame.K_9):
                    idx = int(evento.key - pygame.K_1)
                    if idx < len(ATAQUES_OBRIGATORIOS):
                        idx_ataque = idx
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 3:
                    pass
                elif evento.button == 1:
                    executor = pokemon_selecionado()
                    nome = ataque_selecionado_nome()
                    spec = catalogo.obter(nome)
                    forma = str((spec.bruto.get("execucao") or {}).get("forma") if spec else "")
                    alvo = alvo_por_clique(mouse)
                    alvo_ids = [alvo.Uid] if (forma in FORMAS_ALVO and alvo is not None) else []
                    destino = list(executor.Posicao)
                    if forma not in FORMAS_SELF:
                        mx = ((mouse[0] - arena[0]) / max(1, arena[2])) * tamanho_mundo[0]
                        my = ((mouse[1] - arena[1]) / max(1, arena[3])) * tamanho_mundo[1]
                        destino = [max(0.0, min(tamanho_mundo[0], mx)), max(0.0, min(tamanho_mundo[1], my))]
                    jogadas_preparadas.append(_montar_jogada(executor, spec, destino, alvo_ids))

        tela.fill((22, 24, 30))
        pygame.draw.rect(tela, (35, 55, 40), arena, border_radius=8)
        pygame.draw.rect(tela, (90, 120, 95), arena, width=2, border_radius=8)

        for p in sistema.listar_pokemons():
            x, y = _mundo_para_tela(p.Posicao, arena, tamanho_mundo)
            cor = (90, 180, 255) if p.Lado == "jogador" else (255, 130, 130)
            if p.Uid == pokemon_selecionado().Uid:
                pygame.draw.circle(tela, (255, 255, 90), (x, y), 26, width=3)
            pygame.draw.circle(tela, cor, (x, y), 20)
            nome = fonte.render(f"{p.Nome} ({p.Uid})", True, (235, 235, 235))
            tela.blit(nome, (x - 70, y - 42))
            barra_larg = 70
            vida_pct = max(0.0, min(1.0, p.VidaAtual / max(1.0, p.Vida)))
            ener_pct = max(0.0, min(1.0, p.Energia / max(1.0, p.EnergiaMax)))
            pygame.draw.rect(tela, (70, 30, 30), (x - 35, y + 24, barra_larg, 6))
            pygame.draw.rect(tela, (220, 70, 70), (x - 35, y + 24, int(barra_larg * vida_pct), 6))
            pygame.draw.rect(tela, (30, 45, 75), (x - 35, y + 33, barra_larg, 6))
            pygame.draw.rect(tela, (70, 160, 255), (x - 35, y + 33, int(barra_larg * ener_pct), 6))
            info = fonte.render(f"B:{p.Barreira:.0f} Ef:{len(p.Efeitos)}", True, (220, 220, 220))
            tela.blit(info, (x - 35, y + 42))

        sel = pokemon_selecionado()
        sx, sy = _mundo_para_tela(sel.Posicao, arena, tamanho_mundo)
        pygame.draw.line(tela, (255, 255, 100), (sx, sy), mouse, 2)

        painel_x = 1360
        pygame.draw.rect(tela, (18, 20, 26), (painel_x, 20, 540, 1040), border_radius=8)
        titulo = fonte_titulo.render("Teste Combate 6v6", True, (240, 240, 240))
        tela.blit(titulo, (painel_x + 16, 30))
        linhas = [
            f"Turno: {sistema.TurnoAtual} Tick: {sistema.TickGlobal} Pausado:{pausado}",
            f"Selecionado: {sel.Uid} ({sel.Lado})",
            f"Ataque: {ataque_selecionado_nome()} [{idx_ataque+1}/{len(ATAQUES_OBRIGATORIOS)}]",
            f"Jogadas preparadas: {len(jogadas_preparadas)}",
            f"Ultimo status: {ultimo_resultado.get('status', '-')}",
            "",
            "Ataques obrigatórios:",
        ]
        linhas.extend([f"- {nome}" for nome in ATAQUES_OBRIGATORIOS])

        if log_visivel:
            linhas.append("")
            linhas.append("Último histórico:")
            linhas.extend(historico_curto[-8:] or ["(vazio)"])

        if ajuda_visivel:
            linhas.append("")
            linhas.extend(
                [
                    "Ajuda: Tab,1-6,F1-F12,A/D,Click,Enter,Backspace,R,L,H,Espaço",
                    "Clique esquerdo prepara jogada, Enter executa turno.",
                ]
            )

        ytxt = 70
        for linha in linhas[:50]:
            surf = fonte.render(linha[:75], True, (220, 220, 220))
            tela.blit(surf, (painel_x + 16, ytxt))
            ytxt += 20

        pygame.display.flip()
        relogio.tick(180)

    pygame.quit()
    return 0


def main() -> int:
    if "--smoke" in sys.argv:
        return rodar_smoke_tests()
    return executar_visual()


if __name__ == "__main__":
    raise SystemExit(main())
