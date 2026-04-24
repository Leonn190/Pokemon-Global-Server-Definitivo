"""Funil de comunicação de batalha (cliente -> simulador de servidor)."""

from __future__ import annotations

import json
from typing import Dict, List

from SimuladorServerJogo.Gerais.Rotas.Atualizador import processar_atualizador_json


