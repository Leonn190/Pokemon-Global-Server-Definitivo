from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List

from Codigo.Server.ServerBatalha import iniciar_batalha_server


class SistemaBatalha:
    """Controla o estado físico/espacial básico do campo de batalha."""

    def __init__(self, contexto: Dict[str, object] | None = None) -> None:
        self.Contexto = dict(contexto or {})
        self.PokemonsAliados: List[object] = []
        self.PokemonsInimigos: List[object] = []
        self.BatalhaId = str(self.Contexto.get("batalha_id_servidor") or "")
        self.Tipo = str(self.Contexto.get("tipo") or "confronto")
        self.TurnoAtual = 1
        self.TickGlobal = 0
        self.ClimaAtual = ""
        self.ArenaAtual: Dict[str, object] = {}
        self.UltimoLogTurno: Dict[str, object] = {}
        self.HistoricoRecebido: object = []
        self.ResultadoRecebido: Dict[str, object] = {}
        self._thread_inicio_server: threading.Thread | None = None
        self._ultima_chave_log_salva = ""

    def _salvar_log_debug(self, dados_servidor: Dict[str, object], log_servidor: Dict[str, object]) -> None:
        batalha_id = str(log_servidor.get("batalha_id") or dados_servidor.get("batalha_id") or self.BatalhaId or "batalha")
        turno = int(log_servidor.get("turno_atual", dados_servidor.get("turno_atual", self.TurnoAtual)) or self.TurnoAtual)
        chave = f"{batalha_id}:{turno}"
        if chave == self._ultima_chave_log_salva:
            return
        raiz_repo = Path(__file__).resolve().parents[2]
        pasta_logs = raiz_repo / "logs"
        pasta_logs.mkdir(parents=True, exist_ok=True)
        nome_arquivo = f"rodada_{batalha_id}_turno_{turno:03d}.json"
        (pasta_logs / nome_arquivo).write_text(json.dumps(dict(log_servidor or {}), ensure_ascii=False, indent=2), encoding="utf-8")
        self._ultima_chave_log_salva = chave

    def definir_lados(self, aliados: List[object], inimigos: List[object]) -> None:
        self.PokemonsAliados = list(aliados or [])
        self.PokemonsInimigos = list(inimigos or [])

    def iniciar_batalha_server_async(self, contexto_batalha: Dict[str, object]) -> None:
        if self._thread_inicio_server is not None and self._thread_inicio_server.is_alive():
            return
        ip = str(self.Contexto.get("server_ip") or "")
        client_id = str(self.Contexto.get("client_id") or "")
        if not ip or not client_id:
            return
        contexto_rede = dict(contexto_batalha or {})

        def _worker() -> None:
            resposta = iniciar_batalha_server(ip=ip, client_id=client_id, contexto_batalha=contexto_rede)
            if not isinstance(resposta, dict):
                return
            self.Contexto["batalha_servidor_inicio"] = resposta
            batalha = resposta.get("batalha") if isinstance(resposta.get("batalha"), dict) else {}
            batalha_id = str(batalha.get("batalha_id") or "")
            if batalha_id:
                self.Contexto["batalha_id_servidor"] = batalha_id

        self._thread_inicio_server = threading.Thread(target=_worker, name="BatalhaInicioServidor", daemon=True)
        self._thread_inicio_server.start()

    @classmethod
    def _mesclar_lista_pokemon(cls, base: object, diff: Dict[str, object]) -> List[Dict[str, object]]:
        atuais = [dict(item) for item in list(base or []) if isinstance(item, dict)]
        por_uid = {str(item.get("uid") or item.get("id") or item.get("ID") or ""): dict(item) for item in atuais}
        ordem = [str(item.get("uid") or item.get("id") or item.get("ID") or "") for item in atuais if str(item.get("uid") or item.get("id") or item.get("ID") or "")]
        for removido in [str(uid) for uid in list(diff.get("removidos") or []) if str(uid)]:
            por_uid.pop(removido, None)
            ordem = [uid for uid in ordem if uid != removido]
        for item_diff in [dict(item) for item in list(diff.get("itens") or []) if isinstance(item, dict)]:
            uid = str(item_diff.get("uid") or item_diff.get("id") or item_diff.get("ID") or "")
            if not uid:
                continue
            base_item = por_uid.get(uid, {"uid": uid})
            por_uid[uid] = cls._aplicar_diff_estado(base_item, item_diff)
            if uid not in ordem:
                ordem.append(uid)
        if isinstance(diff.get("ordem"), list):
            ordem = [str(uid) for uid in list(diff.get("ordem") or []) if str(uid)]
        return [dict(por_uid[uid]) for uid in ordem if uid in por_uid]

    @classmethod
    def _aplicar_diff_estado(cls, base: object, diff: object) -> object:
        if isinstance(diff, dict):
            if str(diff.get("__tipo__") or "") == "lista_pokemon":
                return cls._mesclar_lista_pokemon(base, diff)
            origem = dict(base) if isinstance(base, dict) else {}
            for chave, valor in diff.items():
                if str(chave) == "__tipo__":
                    continue
                origem[str(chave)] = cls._aplicar_diff_estado(origem.get(str(chave)), valor)
            return origem
        if isinstance(diff, list):
            return [cls._aplicar_diff_estado(None, item) if isinstance(item, dict) else item for item in diff]
        return diff

    def resolver_estado_recebido(self, retorno: Dict[str, object] | None = None, log_servidor: Dict[str, object] | None = None) -> Dict[str, object]:
        retorno = retorno if isinstance(retorno, dict) else {}
        log = log_servidor if isinstance(log_servidor, dict) else {}
        resultado_log = log.get("resultado") if isinstance(log.get("resultado"), dict) else {}
        batalha = retorno.get("batalha") if isinstance(retorno.get("batalha"), dict) else {}
        if resultado_log:
            base = dict(self.ResultadoRecebido or {})
            if not base and batalha:
                base = dict(batalha)
            mesclado = self._aplicar_diff_estado(base, resultado_log)
            return mesclado if isinstance(mesclado, dict) else {}
        return dict(batalha)

    def atualizar(self, _eventos=None, _dt: float = 0.0, *, dados_servidor: Dict[str, object] | None = None, log_servidor: Dict[str, object] | None = None) -> None:
        if isinstance(dados_servidor, dict):
            self.BatalhaId = str(dados_servidor.get("batalha_id") or self.BatalhaId or "")
            self.Tipo = str(dados_servidor.get("tipo") or self.Tipo or "confronto")
            self.TurnoAtual = max(1, int(dados_servidor.get("turno_atual", self.TurnoAtual) or self.TurnoAtual))
            self.TickGlobal = max(0, int(dados_servidor.get("tick_global", self.TickGlobal) or self.TickGlobal))
            self.ClimaAtual = str(dados_servidor.get("clima") or self.ClimaAtual or "")
            self.ArenaAtual = dict(dados_servidor.get("arena") or self.ArenaAtual or {})
            self.ResultadoRecebido = dict(dados_servidor)
            self.Contexto["batalha_id_servidor"] = self.BatalhaId
            self.Contexto["batalha_servidor_resultado"] = dict(dados_servidor)
        if isinstance(log_servidor, dict):
            self.UltimoLogTurno = dict(log_servidor)
            historico = log_servidor.get("historico")
            if isinstance(historico, list):
                self.HistoricoRecebido = [dict(item) for item in historico if isinstance(item, dict)]
            elif isinstance(historico, dict):
                self.HistoricoRecebido = dict(historico)
            else:
                self.HistoricoRecebido = []
            self.Contexto["batalha_servidor_log"] = dict(log_servidor)
            self._salvar_log_debug(self.ResultadoRecebido if isinstance(self.ResultadoRecebido, dict) else {}, log_servidor)
        return
