from __future__ import annotations

import ctypes
import os
import platform


def _memoria_total_gb() -> float | None:
    """Retorna a memória física total em GB sem depender de bibliotecas externas."""
    try:
        if os.name == "nt":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return float(status.ullTotalPhys) / (1024 ** 3)

        if hasattr(os, "sysconf"):
            paginas = os.sysconf("SC_PHYS_PAGES")
            tamanho_pagina = os.sysconf("SC_PAGE_SIZE")
            return float(paginas * tamanho_pagina) / (1024 ** 3)
    except Exception:
        return None
    return None


def _texto_processador() -> str:
    partes = [
        platform.processor(),
        platform.machine(),
        platform.platform(),
    ]
    return " ".join(str(parte or "") for parte in partes).lower()


def computador_apto_para_opengl(moderngl_disponivel: bool = True) -> bool:
    """Decide se o jogo deve tentar abrir a janela com OpenGL no modo automático.

    A detecção é propositalmente conservadora e leve: ela evita OpenGL quando
    encontra sinais claros de máquina fraca, mas deixa OpenGL ativo quando não há
    evidência suficiente. Isso evita bloquear computadores bons por engano.

    Para forçar o modo em testes sem alterar o código:
    - POKEMON_RENDERIZADOR=pygame
    - POKEMON_RENDERIZADOR=opengl
    """

    if not moderngl_disponivel:
        return False

    renderizador_forcado = str(os.environ.get("POKEMON_RENDERIZADOR", "")).strip().lower()
    if renderizador_forcado in ("pygame", "pygame_puro", "compatibilidade", "sem_opengl"):
        return False
    if renderizador_forcado in ("opengl", "modern_gl", "moderngl", "gl"):
        return True

    pontos_fracos = 0

    nucleos = os.cpu_count() or 0
    if 0 < nucleos <= 2:
        pontos_fracos += 2
    elif 0 < nucleos <= 4:
        pontos_fracos += 1

    memoria_gb = _memoria_total_gb()
    if memoria_gb is not None:
        if memoria_gb < 4.0:
            pontos_fracos += 2
        elif memoria_gb < 6.0:
            pontos_fracos += 1

    processador = _texto_processador()
    marcadores_fracos = (
        "atom",
        "celeron",
        "pentium",
        "sempron",
        "athlon silver",
        "athlon 3000",
        "e1-",
        "e2-",
        "a4-",
        "a6-",
        "n3050",
        "n3060",
        "n3350",
        "n4000",
        "n4020",
        "n4120",
        "j1800",
        "j1900",
        "j3060",
        "j3160",
        "j3455",
    )
    if any(marcador in processador for marcador in marcadores_fracos):
        pontos_fracos += 2

    marcadores_bons = (
        " ryzen 5",
        " ryzen 7",
        " ryzen 9",
        " i5-",
        " i7-",
        " i9-",
        "core(tm) i5",
        "core(tm) i7",
        "core(tm) i9",
    )
    if any(marcador in processador for marcador in marcadores_bons):
        pontos_fracos -= 1

    return pontos_fracos < 2
