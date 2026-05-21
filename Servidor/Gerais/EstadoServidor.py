import copy
import json
import random
import threading
import time
import re
import unicodedata
from pathlib import Path

from Servidor.Gerais import ContextoServidor
import Servidor.Gerais.Geradores.GeradorMundo as GERADOR_MUNDO
from Servidor.Gerais.Geradores.GeradorMundo import (
    carregar_estado_mundo,
    gerar_novo_estado_mundo,
    limpar_arquivos_mundo,
    obter_posicao_spawn,
    salvar_estado_mundo,
)
from Servidor.Mundo.BancoDados import BANCO_DADOS
from Servidor.Mundo.PacotesTick import PACOTES_TICK
from Servidor.Mundo.TiqueServidor import TIQUE_SERVIDOR
from Servidor.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado
from Servidor.Gerais.Geradores.AplicadorConfigMundo import BIOMAS_CONFIGURAVEIS, TAMANHOS_MUNDO
from Servidor.Gerais.LoaderRegras import (
    carregar_regras_cliente_mundo,
    carregar_regras_dungeons,
    carregar_regras_estruturas_naturais,
    carregar_regras_mundo,
    carregar_regras_player,
    carregar_regras_server,
    carregar_regras_skils,
)

_CHAVE_SEGURANCA = ""
_SERVIDOR_ATIVO_ATUAL = None
_ESTADO_MUNDO = {
    "meta": {},
    "grid": [],
    "grid_biomas": [],
    "grid_estruturas_naturais": [],
    "estruturas_naturais_tocadas": {},
    "players": {},
    "npcs_vendedores": {},
    "spawn": [0.0, 0.0],
    "tempo_mundo": {},
}

_ESTADO = {
    "nome": "",
    "ligado": False,
    "mundo_existente": False,
    "banidos": set(),
    "ops": {},
    "regras_servidor": {},
    "jogadores_com_personagem": set(),
    "personagens": {},
}

_ESTADO_GERACAO = {
    "em_andamento": False,
    "progresso": 0,
    "mensagem": "Aguardando operação",
    "erro": "",
    "operacao": "nenhuma",
}

_LOCK = threading.RLock()
_INTERVALO_PERSISTENCIA_SEGUNDOS = 1.0
_ultimo_persistencia_ts = 0.0
_PERSISTENCIA_LOCK = threading.Lock()
_persistencia_thread = None
_persistencia_snapshot_pendente = {}
_persistencia_secoes_pendentes: set[str] = set()
_NIVEL_MAXIMO_JOGADOR = 100
_COMANDOS_DEFAULT_NIVEL_FALLBACK = 1
_SECOES_PERSISTENCIA = ("players", "npcs_vendedores", "estruturas_naturais_tocadas", "tempo_mundo")
_TIPOS_ESTADIO_RESPEITO = (
    "normal", "fogo", "agua", "planta", "eletrico", "gelo", "lutador", "venenoso", "terrestre", "voador",
    "psiquico", "inseto", "pedra", "fantasma", "dragao", "sombrio", "metal", "fada", "cosmico", "sonoro", "geral",
)
_CATEGORIAS_CONHECIMENTO = ("Efeitos", "Ataques", "Pokemons", "Itens", "Musicas")
_RECURSOS_CONFIG_MUNDO = ("arvores", "pedras_minerios", "plantas_decorativas", "recursos_raros")


def _valor_regra(regras: dict, chave: str, padrao):
    valor = regras.get(chave, padrao) if isinstance(regras, dict) else padrao
    return padrao if valor in (None, "") else valor


def _bool_cfg(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in ("1", "true", "sim", "yes", "on")
    return bool(valor)



class _EstadoServidorCtx:
    def estado(self):
        return _ESTADO

    def estado_mundo(self):
        return _ESTADO_MUNDO

    def set_estado_mundo(self, novo):
        global _ESTADO_MUNDO
        _ESTADO_MUNDO = novo

    def estado_geracao(self):
        return _ESTADO_GERACAO

    def lock(self):
        return _LOCK

    def garantir_estado_ativo(self):
        return _garantir_estado_ativo()

    def salvar_json_servidor_ativo_locked(self):
        return _salvar_json_servidor_ativo_locked()

    def set_geracao(self, **kwargs):
        return _set_geracao(**kwargs)

    def agendar_persistencia_locked(self, force=False, secoes=None):
        return _agendar_persistencia_locked(force=force, secoes=secoes)

    def recarregar_cerebro_mundo(self):
        return _recarregar_cerebro_mundo()

    def estado_mundo_vazio(self):
        return _estado_mundo_vazio()

    def clamp_posicao(self, posicao):
        return _clamp_posicao(posicao)

    def valor_regra(self, regras, chave, padrao):
        return _valor_regra(regras, chave, padrao)

    def bool_cfg(self, valor):
        return _bool_cfg(valor)

    def config_mundo_padrao(self):
        return _config_mundo_padrao()

    def normalizar_config_mundo(self, config):
        return normalizar_config_mundo(config)

    def tempo_mundo_padrao(self):
        return _tempo_mundo_padrao()

    def normalizar_tempo_mundo(self, tempo):
        return _normalizar_tempo_mundo(tempo)

    def persistir_personagens(self, force=False):
        return _PERSONAGENS._persistir_personagens(force=force)

    def normalizar_exploracao_chunks(self, valor):
        return _MUNDO._normalizar_exploracao_chunks(valor)

    def fingerprint_mundo_atual(self):
        return _MUNDO._fingerprint_mundo_atual()

    def limites_mundo_atuais(self):
        return _MUNDO._limites_mundo_atuais()

    def recarregar_mundo(self):
        return _MUNDO._recarregar_mundo()


from Servidor.Gerais.EstadoServidorMundo import EstadoServidorMundo
from Servidor.Gerais.EstadoServidorPersonagens import EstadoServidorPersonagens

_CTX = _EstadoServidorCtx()
_MUNDO = EstadoServidorMundo(_CTX)
_PERSONAGENS = EstadoServidorPersonagens(_CTX)


def _skins_liberadas_padrao() -> list[str]:
    return _PERSONAGENS._skins_liberadas_padrao()

def _normalizar_skins_liberadas(skins: list[str] | None) -> list[str]:
    return _PERSONAGENS._normalizar_skins_liberadas(skins)

def _normalizar_conhecimento(conhecimento: dict | None) -> dict:
    return _PERSONAGENS._normalizar_conhecimento(conhecimento)

def _normalizar_lista_ids(valor) -> list[str]:
    return _PERSONAGENS._normalizar_lista_ids(valor)

def _normalizar_dict_lista_ids(valor) -> dict[str, list[str]]:
    return _PERSONAGENS._normalizar_dict_lista_ids(valor)

def _percentual_config(valor, padrao: int = 50) -> int:
    try:
        numero = int(round(float(valor)))
    except (TypeError, ValueError):
        numero = int(padrao)
    return max(0, min(100, numero))


def _config_mundo_padrao() -> dict:
    return {
        "versao": 1,
        "tamanho_mundo": dict(TAMANHOS_MUNDO["regular"]),
        "agua": 50,
        "rios": {
            "quantidade": 50,
            "comprimento": 50,
            "largura": 50,
        },
        "lagos": 50,
        "biomas": {bioma: 50 for bioma in BIOMAS_CONFIGURAVEIS},
        "recursos": {recurso: 50 for recurso in _RECURSOS_CONFIG_MUNDO},
        "vilas": 50,
    }


def normalizar_config_mundo(config) -> dict:
    base = _config_mundo_padrao()
    bruto = config if isinstance(config, dict) else {}

    tamanho = bruto.get("tamanho_mundo")
    tamanho_id = "regular"
    if isinstance(tamanho, dict):
        tamanho_id = str(tamanho.get("id") or tamanho.get("opcao") or "regular").strip().lower()
    elif isinstance(tamanho, str):
        tamanho_id = tamanho.strip().lower()
    base["tamanho_mundo"] = dict(TAMANHOS_MUNDO.get(tamanho_id, TAMANHOS_MUNDO["regular"]))

    base["agua"] = _percentual_config(bruto.get("agua"), 50)
    base["lagos"] = _percentual_config(bruto.get("lagos"), 50)
    base["vilas"] = _percentual_config(bruto.get("vilas"), 50)

    rios = bruto.get("rios") if isinstance(bruto.get("rios"), dict) else {}
    base["rios"] = {
        "quantidade": _percentual_config(rios.get("quantidade"), 50),
        "comprimento": _percentual_config(rios.get("comprimento"), 50),
        "largura": _percentual_config(rios.get("largura"), 50),
    }

    biomas = bruto.get("biomas") if isinstance(bruto.get("biomas"), dict) else {}
    base["biomas"] = {bioma: _percentual_config(biomas.get(bioma), 50) for bioma in BIOMAS_CONFIGURAVEIS}

    recursos = bruto.get("recursos") if isinstance(bruto.get("recursos"), dict) else {}
    base["recursos"] = {recurso: _percentual_config(recursos.get(recurso), 50) for recurso in _RECURSOS_CONFIG_MUNDO}
    return base


def _contar_recursos_miticos_inventario(inventario: dict | None) -> int:
    return _PERSONAGENS._contar_recursos_miticos_inventario(inventario)

def _tempo_mundo_padrao() -> dict:
    total_segundos = int(8 * 3600)
    return {
        "total_segundos_mundo": total_segundos,
        "dia": 0,
        "hora": 8,
        "minuto": 0,
        "chuva_intensidade": 0,
        "chuva_alvo": 0,
        "chuva_estado": "seco",
        "chuva_habilitada": True,
    }


def _normalizar_tempo_mundo(tempo: dict | None) -> dict:
    base = _tempo_mundo_padrao()
    bruto = dict(tempo) if isinstance(tempo, dict) else {}
    total = int(bruto.get("total_segundos_mundo", base["total_segundos_mundo"]) or base["total_segundos_mundo"])
    total = max(0, total)
    dia = int(total // 86400)
    segundos_dia = int(total % 86400)
    hora = int(segundos_dia // 3600)
    minuto = int((segundos_dia % 3600) // 60)
    base.update(
        {
            "total_segundos_mundo": total,
            "dia": dia,
            "hora": hora,
            "minuto": minuto,
            "chuva_intensidade": int(max(0, min(100, int(bruto.get("chuva_intensidade", 0) or 0)))),
            "chuva_alvo": int(max(0, min(100, int(bruto.get("chuva_alvo", 0) or 0)))),
            "chuva_estado": str(bruto.get("chuva_estado", "seco") or "seco"),
            "chuva_habilitada": bool(bruto.get("chuva_habilitada", True)),
        }
    )
    return base


if isinstance(_ESTADO_MUNDO, dict):
    _ESTADO_MUNDO["tempo_mundo"] = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))


def _calcular_xp_alvo_por_nivel(nivel: int) -> int:
    return _PERSONAGENS._calcular_xp_alvo_por_nivel(nivel)

def _normalizar_progresso_xp(dados: dict) -> None:
    return _PERSONAGENS._normalizar_progresso_xp(dados)

def _estado_mundo_vazio():
    return {
        "meta": {},
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
        "estruturas_naturais_tocadas": {},
        "players": {},
        "npcs_vendedores": {},
        "spawn": [0.0, 0.0],
        "tempo_mundo": _tempo_mundo_padrao(),
    }


def _agora_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _carregar_json_servidor_ativo() -> dict:
    arquivo = ContextoServidor.obter_arquivo_estado_servidor()
    if not arquivo.exists():
        raise RuntimeError(f"EstadoServidor.json não encontrado: {arquivo}")
    try:
        with arquivo.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"EstadoServidor.json inválido: {arquivo}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"EstadoServidor.json inválido: {arquivo}")
    if str(payload.get("tipo", "local")).lower() != "local":
        raise RuntimeError("Servidor online ainda não implementado.")
    return payload


def _salvar_json_servidor_ativo_locked() -> None:
    try:
        arquivo = ContextoServidor.obter_arquivo_estado_servidor()
    except RuntimeError:
        return
    try:
        payload = _carregar_json_servidor_ativo()
    except RuntimeError:
        return
    payload["ligado"] = bool(_ESTADO.get("ligado", False))
    payload["mundo_existente"] = bool(_ESTADO.get("mundo_existente", False))
    payload["banidos"] = sorted(str(x) for x in _ESTADO.get("banidos", set()))
    payload["ops"] = {str(k): int(v) for k, v in dict(_ESTADO.get("ops", {})).items()}
    payload["regras_servidor"] = dict(_ESTADO.get("regras_servidor", {}))
    payload["atualizado_em"] = _agora_iso()
    with arquivo.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _recarregar_cerebro_mundo() -> None:
    try:
        from Servidor.Mundo.Cerebros.CerebroCentral import CEREBRO
        CEREBRO.recarregar_contexto_mundo()
    except Exception:
        pass


def _garantir_estado_ativo() -> None:
    global _SERVIDOR_ATIVO_ATUAL, _ESTADO_MUNDO, _CHAVE_SEGURANCA

    pasta = ContextoServidor.obter_pasta_servidor_ativo()
    if pasta is None:
        raise RuntimeError("Nenhum servidor local ativo definido")
    pasta = str(Path(pasta).resolve())
    if _SERVIDOR_ATIVO_ATUAL == pasta:
        return

    servidor = _carregar_json_servidor_ativo()
    _CHAVE_SEGURANCA = str(servidor.get("chave_acesso", "")).strip()
    _ESTADO_MUNDO = carregar_estado_mundo()
    _ESTADO_MUNDO["tempo_mundo"] = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))
    personagens = dict(_ESTADO_MUNDO.get("players", {})) if isinstance(_ESTADO_MUNDO.get("players"), dict) else {}
    mundo_existente = bool(servidor.get("mundo_existente", bool(_ESTADO_MUNDO.get("meta"))))
    _ESTADO.update(
        {
            "nome": str(servidor.get("nome", "")),
            "ligado": bool(servidor.get("ligado", False)) and mundo_existente,
            "mundo_existente": mundo_existente,
            "banidos": set(servidor.get("banidos", []) or []),
            "ops": {str(k): max(0, min(2, int(v or 0))) for k, v in dict(servidor.get("ops", {}) or {}).items()},
            "regras_servidor": dict(servidor.get("regras_servidor", {}) or {}),
            "jogadores_com_personagem": set(personagens.keys()),
            "personagens": personagens,
        }
    )
    _ESTADO_GERACAO.update(
        {
            "em_andamento": False,
            "progresso": 0,
            "mensagem": "Aguardando operação",
            "erro": "",
            "operacao": "nenhuma",
        }
    )
    servidor_ativo_anterior = _SERVIDOR_ATIVO_ATUAL
    _SERVIDOR_ATIVO_ATUAL = pasta
    try:
        BANCO_DADOS.recarregar_mundo(_ESTADO_MUNDO, limpar_objetos=True)
        PACOTES_TICK.resetar()
        _recarregar_cerebro_mundo()
    except Exception:
        _SERVIDOR_ATIVO_ATUAL = servidor_ativo_anterior
        raise


def _worker_persistencia_estado_mundo() -> None:
    global _persistencia_thread, _persistencia_snapshot_pendente, _persistencia_secoes_pendentes
    while True:
        with _PERSISTENCIA_LOCK:
            snapshot = dict(_persistencia_snapshot_pendente) if _persistencia_snapshot_pendente else None
            secoes = tuple(sorted(_persistencia_secoes_pendentes))
            _persistencia_snapshot_pendente = {}
            _persistencia_secoes_pendentes.clear()
        if snapshot is None or not secoes:
            with _PERSISTENCIA_LOCK:
                if not _persistencia_snapshot_pendente and not _persistencia_secoes_pendentes:
                    _persistencia_thread = None
                    return
            continue
        try:
            salvar_estado_mundo(snapshot, secoes_mutaveis=secoes)
        except Exception as exc:
            print(f"[EstadoServidor] falha ao persistir MundoEstado.json: {exc}")


def _agendar_snapshot_persistencia(snapshot: dict | None, secoes: set[str]) -> None:
    global _persistencia_thread, _persistencia_snapshot_pendente, _persistencia_secoes_pendentes
    if not isinstance(snapshot, dict) or not snapshot or not secoes:
        return
    with _PERSISTENCIA_LOCK:
        _persistencia_snapshot_pendente.update(snapshot)
        _persistencia_secoes_pendentes.update(set(secoes))
        if _persistencia_thread is not None and _persistencia_thread.is_alive():
            return
        _persistencia_thread = threading.Thread(target=_worker_persistencia_estado_mundo, name="PersistenciaEstadoMundo", daemon=True)
        _persistencia_thread.start()


def _snapshot_estado_mundo_para_persistencia_locked(secoes: set[str] | None = None) -> dict | None:
    if not isinstance(_ESTADO_MUNDO, dict) or not _ESTADO_MUNDO.get("meta"):
        return None
    secoes_norm = set(secoes or _SECOES_PERSISTENCIA)
    snapshot: dict = {}
    if "players" in secoes_norm:
        snapshot["players"] = copy.deepcopy(_ESTADO.get("personagens", {}))
    if "npcs_vendedores" in secoes_norm:
        snapshot["npcs_vendedores"] = copy.deepcopy(_ESTADO_MUNDO.get("npcs_vendedores", {}))
    if "estruturas_naturais_tocadas" in secoes_norm:
        snapshot["estruturas_naturais_tocadas"] = BANCO_DADOS.exportar_estruturas_tocadas()
    if "tempo_mundo" in secoes_norm:
        snapshot["tempo_mundo"] = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))
    return snapshot or None


def _agendar_persistencia_locked(force: bool = False, secoes: set[str] | None = None) -> None:
    global _ultimo_persistencia_ts
    secoes_norm = set(secoes or _SECOES_PERSISTENCIA)
    if not secoes_norm:
        return
    agora = time.monotonic()
    if not force and (agora - _ultimo_persistencia_ts) < _INTERVALO_PERSISTENCIA_SEGUNDOS:
        return
    snapshot = _snapshot_estado_mundo_para_persistencia_locked(secoes_norm)
    if snapshot is None:
        return
    _ultimo_persistencia_ts = agora
    _agendar_snapshot_persistencia(snapshot, secoes_norm)


def _set_geracao(em_andamento=None, progresso=None, mensagem=None, erro=None, operacao=None):
    if em_andamento is not None:
        _ESTADO_GERACAO["em_andamento"] = bool(em_andamento)
    if progresso is not None:
        _ESTADO_GERACAO["progresso"] = max(0, min(100, int(progresso)))
    if mensagem is not None:
        _ESTADO_GERACAO["mensagem"] = str(mensagem)
    if erro is not None:
        _ESTADO_GERACAO["erro"] = str(erro)
    if operacao is not None:
        _ESTADO_GERACAO["operacao"] = str(operacao)


def _clamp_posicao(posicao):
    try:
        x = float(posicao[0])
        y = float(posicao[1])
    except (TypeError, ValueError, IndexError):
        return (0.0, 0.0)

    largura = max(1.0, float(GERADOR_MUNDO.LARGURA_BLOCOS))
    altura = max(1.0, float(GERADOR_MUNDO.ALTURA_BLOCOS))
    x = x % largura
    y = y % altura
    return (x, y)


def _normalizar_perfil(personagem: dict) -> dict:
    return _PERSONAGENS._normalizar_perfil(personagem)

def _normalizar_exploracao_chunks(valor: dict | None) -> dict:
    return _MUNDO._normalizar_exploracao_chunks(valor)

def _fingerprint_mundo_atual() -> str:
    return _MUNDO._fingerprint_mundo_atual()

def _sincronizar_exploracao_mundo_atual(personagem: dict) -> bool:
    return _MUNDO._sincronizar_exploracao_mundo_atual(personagem)

def obter_exploracao_chunks(usuario: str) -> dict:
    return _MUNDO.obter_exploracao_chunks(usuario)

def registrar_chunks_explorados(usuario: str, chunks: list[tuple[int, int]] | set[tuple[int, int]], dimensao: str = "Mundo") -> None:
    return _MUNDO.registrar_chunks_explorados(usuario, chunks, dimensao)

def _normalizar_inventario(payload: dict) -> dict:
    return _PERSONAGENS._normalizar_inventario(payload)

def _inventario_tem_conteudo(inventario: dict | None) -> bool:
    return _PERSONAGENS._inventario_tem_conteudo(inventario)

def _mesclar_perfil_atualizacao(personagem_atual: dict, atualizacao: dict) -> dict:
    return _PERSONAGENS._mesclar_perfil_atualizacao(personagem_atual, atualizacao)

def _recarregar_mundo():
    return _MUNDO._recarregar_mundo()

def _limites_mundo_atuais() -> tuple[float, float]:
    return _MUNDO._limites_mundo_atuais()

def _criar_novo_mundo_sync():
    return _MUNDO._criar_novo_mundo_sync()

def _worker_criacao_mundo():
    return _MUNDO._worker_criacao_mundo()

def _apagar_mundo():
    return _MUNDO._apagar_mundo()

def _worker_apagar_mundo():
    return _MUNDO._worker_apagar_mundo()

def _sync_personagens_mundo():
    return _PERSONAGENS._sync_personagens_mundo()

def _persistir_personagens(force: bool = False) -> None:
    return _PERSONAGENS._persistir_personagens(force)

def _slug_id(valor) -> str:
    return _PERSONAGENS._slug_id(valor)

def _adicionar_unico(lista: list[str], valor: str) -> bool:
    return _PERSONAGENS._adicionar_unico(lista, valor)

def _sincronizar_perfil_player_ativo_locked(usuario: str, perfil: dict) -> None:
    return _PERSONAGENS._sincronizar_perfil_player_ativo_locked(usuario, perfil)

def _player_venceu_partida(partida) -> bool:
    return _PERSONAGENS._player_venceu_partida(partida)

def registrar_recompensas_batalha_finalizada(partida) -> bool:
    return _PERSONAGENS.registrar_recompensas_batalha_finalizada(partida)

def registrar_boss_dungeon_derrotado(client_id: str, dungeon_id: str, boss_id: str, bosses_dungeon, medalhao_id: str | None = None) -> bool:
    return _PERSONAGENS.registrar_boss_dungeon_derrotado(client_id, dungeon_id, boss_id, bosses_dungeon, medalhao_id)

def obter_regras_cliente() -> dict:
    _garantir_estado_ativo()
    regras = carregar_regras_cliente_mundo()
    meta = _ESTADO_MUNDO.get("meta", {}) if isinstance(_ESTADO_MUNDO.get("meta"), dict) else {}
    seed_mundo = int(meta.get("seed", 0) or 0)
    regras_estruturas = carregar_regras_estruturas_naturais()
    variacao = regras_estruturas.get("variacao", {})
    escala_min = float(variacao.get("escala_min", 0.85) or 0.85) if isinstance(variacao, dict) else 0.85
    escala_max = float(variacao.get("escala_max", 1.15) or 1.15) if isinstance(variacao, dict) else 1.15
    tipos_estrutura = regras_estruturas.get("tipos", {}) if isinstance(regras_estruturas.get("tipos"), dict) else {}
    escala_base_max = max((float(cfg.get("escala_base", 1.0) or 1.0) for cfg in tipos_estrutura.values() if isinstance(cfg, dict)), default=1.0)
    escala_max *= max(1.0, escala_base_max)
    if escala_min > escala_max:
        escala_min, escala_max = escala_max, escala_min
    regras["player"] = dict(carregar_regras_player())
    regras["skils"] = carregar_regras_skils()
    regras["mundo"] = {
        "chunk_tiles": int(_valor_regra(carregar_regras_mundo(), "ChunkTiles", 10)),
        "seed": int(seed_mundo),
        "transicao_apenas_um_lado": True,
        "escala_estrutura_min": float(escala_min),
        "escala_estrutura_max": float(escala_max),
    }
    return regras


def _normalizar_usuario_chave(usuario: str) -> str:
    return str(usuario or "").strip()


def listar_ops() -> dict:
    _garantir_estado_ativo()
    with _LOCK:
        return {str(k): int(v) for k, v in dict(_ESTADO.get("ops", {})).items()}


def existe_op_nivel_2() -> bool:
    return any(int(v or 0) >= 2 for v in listar_ops().values())


def _obter_nivel_padrao_comandos() -> int:
    # Regra explicita para jogador sem entrada em ops. O valor base atual e 1
    # para manter compatibilidade, mas pode ser sobrescrito em runtime.comandos_default_nivel.
    try:
        regras = carregar_regras_server()
        nivel = int(_valor_regra(regras, "comandos_default_nivel", _COMANDOS_DEFAULT_NIVEL_FALLBACK))
    except Exception:
        nivel = _COMANDOS_DEFAULT_NIVEL_FALLBACK
    return max(0, min(2, nivel))


def obter_nivel_op(usuario: str) -> int:
    _garantir_estado_ativo()
    nome = _normalizar_usuario_chave(usuario)
    with _LOCK:
        ops = dict(_ESTADO.get("ops", {}))
        if nome in ops:
            return max(0, min(2, int(ops.get(nome, 0) or 0)))
        for chave, nivel in ops.items():
            if str(chave).strip().lower() == nome.lower():
                return max(0, min(2, int(nivel or 0)))
    return _obter_nivel_padrao_comandos()


def definir_nivel_op(usuario: str, nivel: int) -> bool:
    _garantir_estado_ativo()
    nome = _normalizar_usuario_chave(usuario)
    if not nome:
        return False
    nivel_norm = max(0, min(2, int(nivel or 0)))
    with _LOCK:
        ops = dict(_ESTADO.get("ops", {}))
        chave_real = next((k for k in ops.keys() if str(k).strip().lower() == nome.lower()), nome)
        niveis_futuros = dict(ops)
        niveis_futuros[chave_real] = nivel_norm
        if not any(int(v or 0) >= 2 for v in niveis_futuros.values()):
            return False
        _ESTADO["ops"] = niveis_futuros
        _salvar_json_servidor_ativo_locked()
    return True


def garantir_bootstrap_op(usuario: str) -> bool:
    _garantir_estado_ativo()
    nome = _normalizar_usuario_chave(usuario)
    if not nome:
        return False
    with _LOCK:
        ops = dict(_ESTADO.get("ops", {}))
        if any(int(v or 0) >= 2 for v in ops.values()):
            return False
        ops[nome] = 2
        _ESTADO["ops"] = ops
        _salvar_json_servidor_ativo_locked()
    return True


def banir_usuario(usuario: str) -> bool:
    _garantir_estado_ativo()
    nome = _normalizar_usuario_chave(usuario)
    if not nome:
        return False
    with _LOCK:
        _ESTADO.setdefault("banidos", set()).add(nome)
        _salvar_json_servidor_ativo_locked()
    expulsar_usuario(nome)
    return True


def desbanir_usuario(usuario: str) -> bool:
    _garantir_estado_ativo()
    nome = _normalizar_usuario_chave(usuario)
    if not nome:
        return False
    with _LOCK:
        banidos = set(_ESTADO.get("banidos", set()))
        antes = len(banidos)
        banidos = {u for u in banidos if str(u).strip().lower() != nome.lower()}
        _ESTADO["banidos"] = banidos
        _salvar_json_servidor_ativo_locked()
    return len(banidos) != antes


def usuario_banido(usuario: str) -> bool:
    _garantir_estado_ativo()
    nome = _normalizar_usuario_chave(usuario)
    with _LOCK:
        return any(str(u).strip().lower() == nome.lower() for u in set(_ESTADO.get("banidos", set())))


def expulsar_usuario(usuario: str) -> bool:
    nome = _normalizar_usuario_chave(usuario)
    if not nome:
        return False
    try:
        from Servidor.Gerais.Rotas.Ativador import desconectar_client

        desconectar_client(nome)
        return True
    except Exception:
        return False


def obter_regras_servidor() -> dict:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return {}
    with _LOCK:
        return dict(_ESTADO.get("regras_servidor", {}) or {})


def obter_config_mundo() -> dict:
    return _MUNDO.obter_config_mundo()

def definir_config_mundo(config) -> dict:
    return _MUNDO.definir_config_mundo(config)

def definir_regra_servidor(nome: str, valor) -> bool:
    _garantir_estado_ativo()
    chave = str(nome or "").strip()
    if not chave:
        return False
    with _LOCK:
        regras = dict(_ESTADO.get("regras_servidor", {}) or {})
        regras[chave] = valor
        _ESTADO["regras_servidor"] = regras
        _salvar_json_servidor_ativo_locked()
    return True


def resetar_regra_servidor(nome: str) -> bool:
    _garantir_estado_ativo()
    chave = str(nome or "").strip()
    with _LOCK:
        regras = dict(_ESTADO.get("regras_servidor", {}) or {})
        existia = chave in regras
        regras.pop(chave, None)
        _ESTADO["regras_servidor"] = regras
        _salvar_json_servidor_ativo_locked()
    return existia


def listar_regras_servidor() -> dict:
    return obter_regras_servidor()

def chave_seguranca():
    _garantir_estado_ativo()
    return _CHAVE_SEGURANCA


def snapshot_estado():
    _garantir_estado_ativo()
    with _LOCK:
        return {
            "nome": _ESTADO["nome"],
            "ligado": _ESTADO["ligado"],
            "mundo_existente": _ESTADO["mundo_existente"],
            "banidos": set(_ESTADO["banidos"]),
            "ops": {k: int(v) for k, v in dict(_ESTADO.get("ops", {})).items()},
            "regras_servidor": dict(_ESTADO.get("regras_servidor", {}) or {}),
            "jogadores_com_personagem": set(_ESTADO["jogadores_com_personagem"]),
            "personagens": {k: dict(v) for k, v in _ESTADO["personagens"].items()},
            "mundo_em_geracao": bool(_ESTADO_GERACAO["em_andamento"]),
            "progresso_mundo": int(_ESTADO_GERACAO["progresso"]),
            "mensagem_geracao": str(_ESTADO_GERACAO["mensagem"]),
            "erro_geracao": str(_ESTADO_GERACAO["erro"]),
            "operacao_geracao": str(_ESTADO_GERACAO.get("operacao", "nenhuma")),
            "tempo_mundo": dict(_normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))),
        }


def obter_tempo_mundo_estado() -> dict:
    return _MUNDO.obter_tempo_mundo_estado()

def atualizar_tempo_mundo_estado(tempo: dict, force: bool = False) -> None:
    return _MUNDO.atualizar_tempo_mundo_estado(tempo, force)

def registrar_estrutura_natural_tocada_estado(estrutura_id: int, quantidade_restante: int, force: bool = False) -> None:
    return _MUNDO.registrar_estrutura_natural_tocada_estado(estrutura_id, quantidade_restante, force)

def carregar_npcs_vendedores_estado() -> dict:
    return _MUNDO.carregar_npcs_vendedores_estado()

def salvar_npcs_vendedores_estado(npcs: dict, force: bool = False) -> None:
    return _MUNDO.salvar_npcs_vendedores_estado(npcs, force)

def definir_ligado(ativo):
    _garantir_estado_ativo()
    from Servidor.Mundo.Cerebros.CerebroCentral import CEREBRO
    with _LOCK:
        desejado = bool(ativo)
        if desejado and not _ESTADO["mundo_existente"]:
            _ESTADO["ligado"] = False
            _salvar_json_servidor_ativo_locked()
            return False, "Não é possível ligar o servidor sem mundo"
        _ESTADO["ligado"] = desejado
        _salvar_json_servidor_ativo_locked()
        TIQUE_SERVIDOR.definir_ativo(_ESTADO["ligado"])
        if not _ESTADO["ligado"]:
            CEREBRO.desligar_servidor()
            TIQUE_SERVIDOR.parar()
        return True, "Estado do servidor atualizado"


def definir_mundo_existente(ativo):
    return _MUNDO.definir_mundo_existente(ativo)

def adicionar_personagem(usuario, skin, pokemon_inicial):
    return _PERSONAGENS.adicionar_personagem(usuario, skin, pokemon_inicial)

def obter_personagem_para_entrada(usuario):
    return _PERSONAGENS.obter_personagem_para_entrada(usuario)

def atualizar_posicao_personagem(usuario, posicao, dimensao: str = "Mundo"):
    return _PERSONAGENS.atualizar_posicao_personagem(usuario, posicao, dimensao)

def _posicao_mundo_valida(posicao) -> bool:
    return _PERSONAGENS._posicao_mundo_valida(posicao)

def _tile_mundo_seguro(posicao) -> bool:
    return _PERSONAGENS._tile_mundo_seguro(posicao)

def _tick_servidor_atual() -> int:
    return _PERSONAGENS._tick_servidor_atual()

def _vida_player(player) -> dict:
    return _PERSONAGENS._vida_player(player)

def player_invulneravel(player, tick: int | None = None) -> bool:
    return _PERSONAGENS.player_invulneravel(player, tick)

def aplicar_invulnerabilidade_player(player, ticks: int | None = None, motivo: str = "") -> bool:
    return _PERSONAGENS.aplicar_invulnerabilidade_player(player, ticks, motivo)

def matar_player(player, motivo: str = "", registrar_diff=None) -> bool:
    return _PERSONAGENS.matar_player(player, motivo, registrar_diff)

def aplicar_dano_player(player, quantidade: int = 1, motivo: str = "", registrar_diff=None, ignorar_invulnerabilidade: bool = False) -> bool:
    return _PERSONAGENS.aplicar_dano_player(player, quantidade, motivo, registrar_diff, ignorar_invulnerabilidade)

def registrar_checkpoint_mundo_seguro(usuario, player) -> bool:
    return _PERSONAGENS.registrar_checkpoint_mundo_seguro(usuario, player)

def registrar_checkpoint_mundo_chunk_seguro(usuario, player, chunk, posicao=None) -> bool:
    return _PERSONAGENS.registrar_checkpoint_mundo_chunk_seguro(usuario, player, chunk, posicao)

def _posicao_segura_no_chunk(chunk, aleatoria: bool = False) -> list[float] | None:
    return _PERSONAGENS._posicao_segura_no_chunk(chunk, aleatoria)

def _posicao_segura_perto_spawn() -> list[float] | None:
    return _PERSONAGENS._posicao_segura_perto_spawn()

def resolver_respawn_mundo_seguro(usuario, player) -> list[float]:
    return _PERSONAGENS.resolver_respawn_mundo_seguro(usuario, player)

def aplicar_respawn_mundo(usuario, player, motivo="respawn", registrar_diff=None):
    return _PERSONAGENS.aplicar_respawn_mundo(usuario, player, motivo, registrar_diff)

def _restaurar_inventario_player_persistido(usuario: str, player) -> bool:
    return _PERSONAGENS._restaurar_inventario_player_persistido(usuario, player)

def atualizar_inventario_personagem(usuario, inventario):
    return _PERSONAGENS.atualizar_inventario_personagem(usuario, inventario)

def atualizar_perfil_personagem(usuario, perfil):
    return _PERSONAGENS.atualizar_perfil_personagem(usuario, perfil)
