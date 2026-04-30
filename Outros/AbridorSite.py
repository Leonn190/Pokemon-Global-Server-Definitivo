from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


URL_SITE = "http://localhost:4321/"
NODE_DIR = Path(r"C:\Program Files\nodejs")
NODE_EXE = NODE_DIR / "node.exe"
NPM_CMD = NODE_DIR / "npm.cmd"


def achar_pasta_site() -> Path:
    """
    Este arquivo pode ficar em:
    - Pokemon-Global-Server-Definitivo/AbridorSite.py
    - Pokemon-Global-Server-Definitivo/Outros/AbridorSite.py
    - Pokemon-Global-Server-Definitivo/Site/AbridorSite.py
    """
    pasta_atual = Path(__file__).resolve().parent

    candidatos = [
        pasta_atual / "Site",          # se o .py estiver na raiz
        pasta_atual.parent / "Site",   # se o .py estiver em Outros
        pasta_atual,                   # se o .py estiver dentro de Site
    ]

    for candidato in candidatos:
        if candidato.exists() and candidato.is_dir() and (candidato / "package.json").exists():
            return candidato

    print("ERRO: não encontrei a pasta Site com package.json.")
    print("Locais testados:")
    for candidato in candidatos:
        print(f"- {candidato}")

    input("\nPressione Enter para sair...")
    sys.exit(1)


def preparar_ambiente() -> dict[str, str]:
    """
    Corrige o PATH dentro deste processo Python.

    No Windows, às vezes existe 'Path' e não 'PATH'. Se criarmos outro
    'PATH', alguns processos podem ignorar. Por isso removemos qualquer
    variação e recriamos só 'Path'.
    """
    env_original = os.environ.copy()

    caminho_antigo = ""
    for chave, valor in env_original.items():
        if chave.lower() == "path":
            caminho_antigo = valor
            break

    env = {
        chave: valor
        for chave, valor in env_original.items()
        if chave.lower() != "path"
    }

    env["Path"] = str(NODE_DIR) + os.pathsep + caminho_antigo
    return env


def rodar(comando: list[str], pasta: Path | None, env: dict[str, str]) -> int:
    return subprocess.run(
        comando,
        cwd=pasta,
        env=env,
        shell=False,
    ).returncode


def testar_node(env: dict[str, str]) -> None:
    if not NODE_EXE.exists():
        print("ERRO: node.exe não foi encontrado no caminho esperado.")
        print(f"Caminho esperado: {NODE_EXE}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    if not NPM_CMD.exists():
        print("ERRO: npm.cmd não foi encontrado no caminho esperado.")
        print(f"Caminho esperado: {NPM_CMD}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    print("Node encontrado:")
    subprocess.run([str(NODE_EXE), "-v"], env=env, shell=False)

    print("npm encontrado:")
    subprocess.run([str(NPM_CMD), "-v"], env=env, shell=False)


def remover_node_modules(pasta_site: Path, env: dict[str, str]) -> None:
    node_modules = pasta_site / "node_modules"
    if not node_modules.exists():
        return

    print("\nRemovendo node_modules quebrado...")
    subprocess.run(
        ["cmd.exe", "/c", "rmdir", "/s", "/q", str(node_modules)],
        env=env,
        shell=False,
    )


def instalar_dependencias_se_precisar(pasta_site: Path, env: dict[str, str]) -> None:
    astro_cmd = pasta_site / "node_modules" / ".bin" / "astro.cmd"

    if astro_cmd.exists():
        return

    print("\nDependências do site não encontradas. Rodando npm.cmd install...")
    print("Isso pode demorar um pouco na primeira vez.\n")

    codigo = rodar([str(NPM_CMD), "install"], pasta_site, env)

    if codigo == 0:
        return

    print("\nA instalação falhou. Vou tentar limpar node_modules e instalar de novo.")
    remover_node_modules(pasta_site, env)

    print("\nRodando npm.cmd install novamente...\n")
    codigo = rodar([str(NPM_CMD), "install"], pasta_site, env)

    if codigo != 0:
        print("\nERRO: npm.cmd install falhou de novo.")
        print("Feche VS Code, terminais e qualquer janela rodando Astro/site, depois rode este arquivo novamente.")
        input("\nPressione Enter para sair...")
        sys.exit(codigo)


def servidor_respondendo() -> bool:
    try:
        with urllib.request.urlopen(URL_SITE, timeout=1):
            return True
    except Exception:
        return False


def abrir_servidor_astro(pasta_site: Path) -> None:
    """
    Abre o Astro em uma janela separada de terminal.
    A janela fica aberta mantendo o site rodando.
    """
    comando = (
        f'cd /d "{pasta_site}" && '
        f'set "PATH={NODE_DIR};%PATH%" && '
        f'"{NPM_CMD}" run dev'
    )

    subprocess.Popen(
        ["cmd.exe", "/k", comando],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def abrir_navegador() -> None:
    # Abre no navegador padrão do Windows.
    # Se ele já estiver aberto, normalmente abre uma nova aba nele.
    webbrowser.open(URL_SITE, new=2)


def main() -> None:
    pasta_site = achar_pasta_site()
    env = preparar_ambiente()

    print(f"Pasta do site: {pasta_site}")
    testar_node(env)

    instalar_dependencias_se_precisar(pasta_site, env)

    if not servidor_respondendo():
        print("\nAbrindo servidor Astro...")
        abrir_servidor_astro(pasta_site)

        print("Esperando o site subir...")
        for _ in range(40):
            if servidor_respondendo():
                break
            time.sleep(1)

    print(f"\nAbrindo navegador em: {URL_SITE}")
    abrir_navegador()


if __name__ == "__main__":
    main()
