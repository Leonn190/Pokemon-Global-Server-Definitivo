# GameTestFPS.py
# Coloque este arquivo em Outros/GameTestFPS.py e rode pela raiz do repo:
# python Outros/GameTestFPS.py

from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import textwrap
import time
import traceback
from datetime import datetime
from pathlib import Path
from statistics import mean, median


NOME_APP = "Pokemon Global Server"
ENV_CHILD = "PGS_FPS_TEST_CHILD"
ENV_REPORT_DIR = "PGS_FPS_REPORT_DIR"
ENV_PYSPY_RATE = "PGS_PYSPY_RATE"
ENV_PYSPY_NATIVE = "PGS_PYSPY_NATIVE"

ARQUIVO_ATUAL = Path(__file__).resolve()
PASTA_OUTROS = ARQUIVO_ATUAL.parent
PASTA_RAIZ = PASTA_OUTROS.parent

# Garante que imports como Codigo.* e Outros.* funcionem mesmo com o arquivo dentro de Outros.
if str(PASTA_RAIZ) not in sys.path:
    sys.path.insert(0, str(PASTA_RAIZ))

PASTA_RELATORIOS = PASTA_RAIZ / "RelatoriosFPS"


def _agora_nome_pasta() -> str:
    return datetime.now().strftime("FPS_%Y-%m-%d_%H-%M-%S")


def _abrir_pasta_no_sistema(pasta: Path) -> None:
    """Tenta abrir a pasta do relatório sem travar caso o SO não permita."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(pasta))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(pasta)])
        else:
            subprocess.Popen(["xdg-open", str(pasta)])
    except Exception:
        pass


def _escrever_texto(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")


def _montar_comando_pyspy(pyspy: str, pasta_relatorio: Path) -> list[str]:
    saida_svg = pasta_relatorio / "perfil_maiores_gastos_fps.svg"
    taxa = os.environ.get(ENV_PYSPY_RATE, "250")

    comando = [
        pyspy,
        "record",
        "--rate",
        taxa,
        "--full-filenames",
        "--output",
        str(saida_svg),
    ]

    # Opcional. Pode ajudar a enxergar chamadas C/nativas de pygame/SDL/OpenGL,
    # mas também pode deixar o perfil mais pesado/ruidoso.
    # Para ativar no terminal: set PGS_PYSPY_NATIVE=1
    if os.environ.get(ENV_PYSPY_NATIVE, "0") == "1":
        comando.append("--native")

    comando.extend([
        "--",
        sys.executable,
        str(ARQUIVO_ATUAL),
        "--child",
    ])
    return comando


def iniciar_com_pyspy() -> int:
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)
    pasta_relatorio = PASTA_RELATORIOS / _agora_nome_pasta()
    pasta_relatorio.mkdir(parents=True, exist_ok=True)

    pyspy = shutil.which("py-spy")
    env = os.environ.copy()
    env[ENV_CHILD] = "1"
    env[ENV_REPORT_DIR] = str(pasta_relatorio)
    env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    env.setdefault("PYTHONUTF8", "1")

    readme_inicial = f"""
Relatório de FPS - {NOME_APP}
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Arquivos esperados:
- perfil_maiores_gastos_fps.svg: flamegraph do py-spy, bom para achar gasto contínuo de CPU Python.
- frames_todos.csv: tempo de cada frame medido pelo Clock do pygame.
- travadinhas.csv: apenas frames acima do limite de travadinha.
- travadinhas_resumo.txt: resumo dos piores frames, percentis e contagens.
- saida_pyspy.txt: saída do py-spy no terminal.

Observação:
O flamegraph mostra o que mais consumiu tempo no total.
O relatório de travadinhas mostra picos de frame time, inclusive quando o gargalo não aparece como gasto contínuo.
""".strip()
    _escrever_texto(pasta_relatorio / "README.txt", readme_inicial + "\n")

    if pyspy is None:
        aviso = """
py-spy não foi encontrado no PATH.
Instale com:
    pip install py-spy

O jogo será aberto mesmo assim, mas só serão gerados os relatórios de frame time/travadinhas.
O SVG de maiores gastos não será gerado nesta execução.
""".strip()
        print(aviso)
        _escrever_texto(pasta_relatorio / "saida_pyspy.txt", aviso + "\n")
        retorno = subprocess.run(
            [sys.executable, str(ARQUIVO_ATUAL), "--child"],
            cwd=str(PASTA_RAIZ),
            env=env,
        ).returncode
        _abrir_pasta_no_sistema(pasta_relatorio)
        print(f"\nRelatórios gerados em: {pasta_relatorio}")
        return retorno

    comando = _montar_comando_pyspy(pyspy, pasta_relatorio)
    _escrever_texto(
        pasta_relatorio / "comando_usado.txt",
        " ".join(f'"{p}"' if " " in p else p for p in comando) + "\n",
    )

    print("Abrindo jogo com py-spy...")
    print(f"Pasta do relatório: {pasta_relatorio}")
    print("Feche o jogo normalmente para finalizar e liberar os arquivos.\n")

    processo = subprocess.run(
        comando,
        cwd=str(PASTA_RAIZ),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    saida = processo.stdout or ""
    _escrever_texto(pasta_relatorio / "saida_pyspy.txt", saida)

    resumo_existe = (pasta_relatorio / "travadinhas_resumo.txt").exists()
    svg_existe = (pasta_relatorio / "perfil_maiores_gastos_fps.svg").exists()

    # Se o py-spy falhou antes de abrir o jogo, roda sem py-spy para ao menos gerar travadinhas.
    if processo.returncode != 0 and not resumo_existe:
        aviso_fallback = f"""
O py-spy retornou erro antes de o jogo terminar.
Código de retorno: {processo.returncode}

Saída do py-spy:
{saida}

Vou abrir o jogo sem py-spy para gerar pelo menos o relatório de travadinhas.
Se quiser o SVG, rode o terminal como administrador ou confira se o py-spy está instalado corretamente.
""".strip()
        print(aviso_fallback)
        _escrever_texto(pasta_relatorio / "saida_pyspy.txt", aviso_fallback + "\n")
        processo_direto = subprocess.run(
            [sys.executable, str(ARQUIVO_ATUAL), "--child"],
            cwd=str(PASTA_RAIZ),
            env=env,
        )
        retorno = processo_direto.returncode
    else:
        retorno = processo.returncode

    _abrir_pasta_no_sistema(pasta_relatorio)

    print("\nFinalizado.")
    print(f"Pasta do relatório: {pasta_relatorio}")
    if svg_existe:
        print("SVG gerado: perfil_maiores_gastos_fps.svg")
    else:
        print("SVG não foi gerado. Veja saida_pyspy.txt.")
    if (pasta_relatorio / "travadinhas_resumo.txt").exists():
        print("Relatório de travadinhas gerado: travadinhas_resumo.txt")

    return retorno


class RelogioComRelatorioFPS:
    """
    Wrapper leve do pygame.time.Clock.

    Ele se comporta como Clock normal, mas registra o tempo de cada tick para detectar
    picos de frame time. Isso ajuda a encontrar travadinhas que às vezes não aparecem
    como maior gasto acumulado no flamegraph.
    """

    def __init__(self, report_dir: Path | None = None, fps_alvo: int = 200) -> None:
        import pygame

        self._clock = pygame.time.Clock()
        self.report_dir = report_dir
        self.fps_alvo = max(1, int(fps_alvo or 200))
        self.frame = 0
        self.inicio = time.perf_counter()
        self.frames: list[dict[str, float | int | str]] = []
        self.travadinhas: list[dict[str, float | int | str]] = []

        self.limite_aviso_ms = self._calcular_limite_aviso()
        self.limite_travadinha_ms = self._calcular_limite_travadinha()

    def configurar_alvo(self, fps_alvo: int | float | None) -> None:
        if fps_alvo:
            self.fps_alvo = max(1, int(fps_alvo))
            self.limite_aviso_ms = self._calcular_limite_aviso()
            self.limite_travadinha_ms = self._calcular_limite_travadinha()

    def _ms_alvo(self) -> float:
        return 1000.0 / max(1, self.fps_alvo)

    def _calcular_limite_aviso(self) -> float:
        # Queda perceptível: abaixo de 60 FPS ou muito acima do alvo do jogo.
        return max(1000.0 / 60.0, self._ms_alvo() * 2.5)

    def _calcular_limite_travadinha(self) -> float:
        # Travadinha forte: abaixo de 30 FPS ou pico 4x maior que o frame alvo.
        return max(1000.0 / 30.0, self._ms_alvo() * 4.0)

    def tick(self, framerate: int = 0) -> int:
        dt_ms = self._clock.tick(framerate)
        self._registrar_frame(dt_ms, self._clock.get_rawtime(), "tick", framerate)
        return dt_ms

    def tick_busy_loop(self, framerate: int = 0) -> int:
        dt_ms = self._clock.tick_busy_loop(framerate)
        self._registrar_frame(dt_ms, self._clock.get_rawtime(), "tick_busy_loop", framerate)
        return dt_ms

    def get_time(self) -> int:
        return self._clock.get_time()

    def get_rawtime(self) -> int:
        return self._clock.get_rawtime()

    def get_fps(self) -> float:
        return self._clock.get_fps()

    def __getattr__(self, nome: str):
        return getattr(self._clock, nome)

    def _registrar_frame(self, dt_ms: int, raw_ms: int, metodo: str, framerate: int) -> None:
        self.frame += 1
        t = time.perf_counter() - self.inicio
        fps_medio_clock = float(self._clock.get_fps())

        registro = {
            "frame": self.frame,
            "tempo_s": round(t, 6),
            "dt_ms": int(dt_ms),
            "raw_ms": int(raw_ms),
            "fps_clock": round(fps_medio_clock, 3),
            "metodo": metodo,
            "framerate_param": int(framerate or 0),
        }
        self.frames.append(registro)

        if dt_ms >= self.limite_travadinha_ms:
            registro_spike = dict(registro)
            registro_spike["tipo"] = "TRAVADINHA"
            self.travadinhas.append(registro_spike)
        elif dt_ms >= self.limite_aviso_ms:
            registro_spike = dict(registro)
            registro_spike["tipo"] = "AVISO"
            self.travadinhas.append(registro_spike)

    def salvar_relatorios(self) -> None:
        if self.report_dir is None:
            return

        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._salvar_frames_csv()
        self._salvar_travadinhas_csv()
        self._salvar_resumo_txt()

    def _salvar_frames_csv(self) -> None:
        caminho = self.report_dir / "frames_todos.csv"
        campos = ["frame", "tempo_s", "dt_ms", "raw_ms", "fps_clock", "metodo", "framerate_param"]
        with caminho.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(self.frames)

    def _salvar_travadinhas_csv(self) -> None:
        caminho = self.report_dir / "travadinhas.csv"
        campos = ["tipo", "frame", "tempo_s", "dt_ms", "raw_ms", "fps_clock", "metodo", "framerate_param"]
        with caminho.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(self.travadinhas)

    @staticmethod
    def _percentil(valores: list[int], p: float) -> float:
        if not valores:
            return 0.0
        valores_ordenados = sorted(valores)
        pos = (len(valores_ordenados) - 1) * p
        baixo = int(pos)
        alto = min(baixo + 1, len(valores_ordenados) - 1)
        peso = pos - baixo
        return valores_ordenados[baixo] * (1 - peso) + valores_ordenados[alto] * peso

    def _salvar_resumo_txt(self) -> None:
        caminho = self.report_dir / "travadinhas_resumo.txt"

        dts = [int(f["dt_ms"]) for f in self.frames]
        raw = [int(f["raw_ms"]) for f in self.frames]
        duracao = time.perf_counter() - self.inicio
        piores = sorted(self.frames, key=lambda item: int(item["dt_ms"]), reverse=True)[:30]

        if dts:
            fps_real_medio = 1000.0 / mean(dts) if mean(dts) else 0.0
            maior_dt = max(dts)
            media_dt = mean(dts)
            mediana_dt = median(dts)
            p95 = self._percentil(dts, 0.95)
            p99 = self._percentil(dts, 0.99)
            raw_medio = mean(raw) if raw else 0.0
        else:
            fps_real_medio = 0.0
            maior_dt = 0
            media_dt = 0.0
            mediana_dt = 0.0
            p95 = 0.0
            p99 = 0.0
            raw_medio = 0.0

        acima_60 = sum(1 for x in dts if x >= 1000.0 / 60.0)
        acima_30 = sum(1 for x in dts if x >= 1000.0 / 30.0)
        acima_20 = sum(1 for x in dts if x >= 50.0)
        acima_10 = sum(1 for x in dts if x >= 100.0)
        total = len(dts)

        linhas_piores = []
        for item in piores:
            linhas_piores.append(
                f"- frame {item['frame']} | t={item['tempo_s']}s | "
                f"dt={item['dt_ms']}ms | raw={item['raw_ms']}ms | fps_clock={item['fps_clock']}"
            )

        texto = f"""
RELATÓRIO DE TRAVADINHAS / FRAME TIME

FPS alvo configurado: {self.fps_alvo}
Frame ideal no alvo: {self._ms_alvo():.2f} ms
Limite de aviso: {self.limite_aviso_ms:.2f} ms
Limite de travadinha forte: {self.limite_travadinha_ms:.2f} ms

Duração aproximada da sessão: {duracao:.2f} s
Frames medidos: {total}
FPS médio real aproximado: {fps_real_medio:.2f}
Tempo médio por frame: {media_dt:.2f} ms
Mediana: {mediana_dt:.2f} ms
P95: {p95:.2f} ms
P99: {p99:.2f} ms
Pior frame: {maior_dt} ms
Raw médio do pygame Clock: {raw_medio:.2f} ms

Contagens úteis:
- Frames acima de 16.67 ms, abaixo de 60 FPS: {acima_60}
- Frames acima de 33.33 ms, abaixo de 30 FPS: {acima_30}
- Frames acima de 50 ms: {acima_20}
- Frames acima de 100 ms: {acima_10}
- Registros em travadinhas.csv: {len(self.travadinhas)}

Como interpretar:
- perfil_maiores_gastos_fps.svg mostra gasto acumulado: bom para achar funções que pesam sempre.
- travadinhas.csv mostra picos isolados: bom para achar engasgos que acontecem às vezes.
- dt_ms é o intervalo total entre ticks; raw_ms é o tempo bruto medido pelo pygame antes do limitador de FPS.

30 piores frames:
{chr(10).join(linhas_piores) if linhas_piores else '- nenhum frame registrado'}
""".strip()

        _escrever_texto(caminho, texto + "\n")


def rodar_jogo_instrumentado() -> int:
    # A partir daqui é basicamente o seu Game.py, mas com RELOGIO instrumentado.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    import ctypes
    import pygame

    try:
        import moderngl  # noqa: F401
    except ImportError:
        moderngl = None

    from Codigo.Cenas.ControladorCenas import ControladorCenas
    from Codigo.ModulosGerais.Sonoridades import VerificaSonoridade

    if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shell32"):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pokemon.global.server")

    pygame.init()
    pygame.mixer.init()

    def _criar_janela():
        flags = pygame.NOFRAME
        if moderngl is not None:
            try:
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
                pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
                try:
                    return pygame.display.set_mode(
                        (1920, 1080),
                        flags | pygame.OPENGL | pygame.DOUBLEBUF,
                        vsync=0,
                    ), True
                except TypeError:
                    return pygame.display.set_mode(
                        (1920, 1080),
                        flags | pygame.OPENGL | pygame.DOUBLEBUF,
                    ), True
            except pygame.error:
                pass
        return pygame.display.set_mode((1920, 1080), flags), False

    report_dir_env = os.environ.get(ENV_REPORT_DIR)
    report_dir = Path(report_dir_env) if report_dir_env else None

    JANELA, JANELA_OPENGL = _criar_janela()
    TELA = pygame.Surface(JANELA.get_size()).convert()
    pygame.display.set_caption("Pokemon Global Server")

    icone = pygame.image.load("Recursos/Visual/Icones/GlobalServer/Icone.png").convert_alpha()
    pygame.display.set_icon(icone)

    RELOGIO = RelogioComRelatorioFPS(report_dir=report_dir, fps_alvo=200)

    CONFIG = {
        "FPS": 200,
        "Volume": 0.5,
        "Claridade": 75,
        "Mudo": False,
        "FPS Visivel": True,
        "Cords Visiveis": False,
        "Ping Visivel": False,
        "MostrarHorario": False,
        "MostrarMinimapa": False,
        "Shader": True,
        "Usuario": None,
    }

    from Outros.ConfigFixa import ConfigFixa

    if ConfigFixa is not None:
        CONFIG = ConfigFixa

    CONFIG.update({"VERSÃO": 1.0})
    CONFIG.setdefault("FPS Visivel", True)
    CONFIG.setdefault("Ping Visivel", False)
    CONFIG.setdefault("Cords Visiveis", False)
    CONFIG.setdefault("MostrarHorario", False)
    CONFIG.setdefault("MostrarMinimapa", False)
    CONFIG.setdefault("Shader", True)

    RELOGIO.configurar_alvo(CONFIG.get("FPS", 200))
    VerificaSonoridade(CONFIG)

    game = None
    erro: BaseException | None = None

    try:
        game = ControladorCenas(
            TELA,
            RELOGIO,
            CONFIG,
            tela_display=JANELA,
            janela_opengl=JANELA_OPENGL,
        )
        game.CenaAlvo = "Menu" if CONFIG.get("Usuario") else "Login"
        game.DefinirCena()
        game.Rodar()
        return 0
    except BaseException as exc:
        erro = exc
        if report_dir is not None:
            _escrever_texto(
                report_dir / "erro_execucao_jogo.txt",
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            )
        raise
    finally:
        try:
            if game is not None:
                game.Encerrar()
        finally:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.stop()
            finally:
                RELOGIO.salvar_relatorios()
                pygame.quit()

        if erro is not None:
            print(f"Erro durante execução do jogo. Veja erro_execucao_jogo.txt em: {report_dir}")


def main() -> int:
    if os.environ.get(ENV_CHILD) == "1" or "--child" in sys.argv:
        return rodar_jogo_instrumentado()
    return iniciar_com_pyspy()


if __name__ == "__main__":
    raise SystemExit(main())
