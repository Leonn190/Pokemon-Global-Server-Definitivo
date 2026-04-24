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


