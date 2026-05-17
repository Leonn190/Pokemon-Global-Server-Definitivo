"""Integração simples com Discord Rich Presence via pypresence."""

from __future__ import annotations

import atexit
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
        self._atexit_registrado = False

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
            if not self._atexit_registrado:
                atexit.register(self.desconectar)
                self._atexit_registrado = True
            return True
        except Exception:
            self._rpc = None
            self._conectado = False
            return False

    @staticmethod
    def _texto(valor, fallback="Jogando"):
        texto = str(valor or "").strip()
        return texto or str(fallback or "Jogando")

    @staticmethod
    def _details_padrao(local):
        return {
            "menu": "No menu",
            "mundo": "Explorando mundo",
            "combate": "Em combate",
            "login": "Fazendo login",
            "carregamento": "Carregando",
        }.get(local, "Jogando")

    @staticmethod
    def _state_padrao(local):
        return {
            "menu": "Menu principal",
            "mundo": "Explorando o bioma Vale",
            "combate": "Confronto selvagem",
            "login": "Tela de login",
            "carregamento": "Preparando o jogo",
        }.get(local, "Jogando")

    @staticmethod
    def _small_text(local):
        return {
            "menu": "Menu",
            "mundo": "Mundo",
            "combate": "Combate",
            "login": "Login",
            "carregamento": "Carregamento",
        }.get(local, "Jogo")

    @staticmethod
    def _acao_legada(local, acao):
        if acao is None:
            return DiscordPresence._state_padrao(local)
        texto = DiscordPresence._texto(acao, "Jogando")
        if local == "menu" and texto.startswith("No menu (") and texto.endswith(")"):
            tela = texto[len("No menu ("):-1].strip()
            mapa = {
                "MenuPrincipal": "Menu principal",
                "Servers": "Tela de servidores",
                "Config": "Configurações",
                "Operador": "Painel do operador",
            }
            return mapa.get(tela, tela or "Menu principal")
        if texto == DiscordPresence._details_padrao(local):
            return DiscordPresence._state_padrao(local)
        if local == "mundo" and texto == "Explorando o mundo":
            return "Explorando o bioma Vale"
        return texto

    def atualizar(self, local="menu", acao=None, details=None, state=None):
        local = str(local or "menu").strip().lower()
        details = self._texto(details, self._details_padrao(local))
        state = self._texto(state if state is not None else self._acao_legada(local, acao), "Jogando")

        if not self.conectar():
            return False

        large_text = "Pokemon Global Server"
        small_text = self._small_text(local)
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
                self._rpc.clear()
            except Exception:
                pass
            try:
                self._rpc.close()
            except Exception:
                pass
        self._rpc = None
        self._conectado = False
        self._ultimo_payload = None
