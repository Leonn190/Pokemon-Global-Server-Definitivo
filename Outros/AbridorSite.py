from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


URL_SITE = "http://localhost:4321/"
NODE_DIR = r"C:\Program Files\nodejs"


def achar_pasta_site() -> Path:
    """
    Este arquivo pode ficar em:
    - Pokemon-Global-Server-Definitivo/AbrirSite.py
    - Pokemon-Global-Server-Definitivo/Outros/AbrirSite.py
    - Pokemon-Global-Server-Definitivo/Site/AbrirSite.py
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
    env = os.environ.copy()

    # Resolve o problema do Node instalado mas fora do PATH.
    if Path(NODE_DIR).exists():
        env["PATH"] = NODE_DIR + os.pathsep + env.get("PATH", "")

    return env


def testar_comando(comando: list[str], env: dict[str, str]) -> bool:
    try:
        subprocess.run(
            comando,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False


def instalar_dependencias_se_precisar(pasta_site: Path, env: dict[str, str]) -> None:
    astro_cmd = pasta_site / "node_modules" / ".bin" / "astro.cmd"

    if astro_cmd.exists():
        return

    print("Dependências do site não encontradas. Rodando npm.cmd install...")
    print("Isso pode demorar um pouco na primeira vez.\n")

    resultado = subprocess.run(
        ["npm.cmd", "install"],
        cwd=pasta_site,
        env=env,
        shell=False,
    )

    if resultado.returncode != 0:
        print("\nERRO: npm.cmd install falhou.")
        print("Tente fechar VS Code/terminais que estejam usando a pasta Site e rode novamente.")
        input("\nPressione Enter para sair...")
        sys.exit(resultado.returncode)


def servidor_respondendo() -> bool:
    try:
        with urllib.request.urlopen(URL_SITE, timeout=1):
            return True
    except Exception:
        return False


def abrir_servidor_astro(pasta_site: Path, env: dict[str, str]) -> None:
    """
    Abre o Astro em uma janela separada de terminal.
    A janela fica aberta mantendo o site rodando.
    """
    comando = (
        f'cd /d "{pasta_site}" && '
        f'set "PATH={NODE_DIR};%PATH%" && '
        f'npm.cmd run dev'
    )

    subprocess.Popen(
        ["cmd.exe", "/k", comando],
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def abrir_navegador() -> None:
    # Abre no navegador padrão do Windows.
    # Se ele já estiver aberto, normalmente abre uma nova aba nele.
    webbrowser.open(URL_SITE, new=2)


def main() -> None:
    pasta_site = achar_pasta_site()
    env = preparar_ambiente()

    if not testar_comando(["node", "-v"], env):
        print("ERRO: Node.js não foi encontrado.")
        print(f"Verifique se existe: {NODE_DIR}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    if not testar_comando(["npm.cmd", "-v"], env):
        print("ERRO: npm.cmd não foi encontrado.")
        print(f"Verifique se existe: {NODE_DIR}\\npm.cmd")
        input("\nPressione Enter para sair...")
        sys.exit(1)

    instalar_dependencias_se_precisar(pasta_site, env)

    if not servidor_respondendo():
        print("Abrindo servidor Astro...")
        abrir_servidor_astro(pasta_site, env)

        print("Esperando o site subir...")
        for _ in range(30):
            if servidor_respondendo():
                break
            time.sleep(1)

    print(f"Abrindo navegador em: {URL_SITE}")
    abrir_navegador()


if __name__ == "__main__":
    main()
