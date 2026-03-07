"""Integração simples com Discord Rich Presence via pypresence."""

from __future__ import annotations

import time
from typing import Optional

try:
    from pypresence import Presence
except Exception:
    Presence = None


# Coloque aqui o seu Application ID do Discord Developer Portal.
APP_ID = "1479683650697166848"


class DiscordPresence:
    def __init__(self, client_id: Optional[str] = None):
        self.client_id = str(client_id or APP_ID).strip()
        self._rpc = None
        self._conectado = False
        self._inicio_jogo = int(time.time())
        self._ultimo_payload = None

    def set_client_id(self, client_id: Optional[str]):
        novo = str(client_id or "").strip()
        if novo == self.client_id:
            return
        self.desconectar()
        self.client_id = novo

    @property
    def ativo(self) -> bool:
        return bool(self._conectado and self._rpc is not None)

    def conectar(self):
        if self._conectado:
            return True
        if Presence is None or not self.client_id:
            return False
        try:
            self._rpc = Presence(self.client_id)
            self._rpc.connect()
            self._conectado = True
            return True
        except Exception:
            self._rpc = None
            self._conectado = False
            return False

    def atualizar(self, local="menu", acao="No menu"):
        local = str(local or "menu").strip().lower()
        acao = str(acao or "Jogando")

        if not self.conectar():
            return False

        details = "No menu" if local == "menu" else "No mundo"
        state = acao
        large_text = "Pokemon Global Server"
        small_text = "Menu" if local == "menu" else "Mundo"
        payload = {
            "details": details,
            "state": state,
            "start": self._inicio_jogo,
            "large_image": "pokemon_global_server",
            "large_text": large_text,
            "small_text": small_text,
        }

        if payload == self._ultimo_payload:
            return True

        try:
            self._rpc.update(**payload)
            self._ultimo_payload = payload
            return True
        except Exception:
            self._conectado = False
            self._rpc = None
            return False

    def desconectar(self):
        if self._rpc is not None:
            try:
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None
        self._conectado = False
        self._ultimo_payload = None
