import copy
import json
import random
import threading
import time
import re
from pathlib import Path

from SimuladorServerJogo.Gerais import ContextoServidor
import SimuladorServerJogo.Gerais.Geradores.GeradorMundo as GERADOR_MUNDO
from SimuladorServerJogo.Gerais.Geradores.GeradorMundo import (
    carregar_estado_mundo,
    gerar_novo_estado_mundo,
    limpar_arquivos_mundo,
    obter_posicao_spawn,
    salvar_estado_mundo,
)
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.PacotesTick import PACOTES_TICK
from SimuladorServerJogo.Mundo.TiqueServidor import TIQUE_SERVIDOR
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado
from SimuladorServerJogo.Gerais.LoaderRegras import (
    carregar_regras_cliente_mundo,
    carregar_regras_dungeons,
    carregar_regras_estruturas_naturais,
    carregar_regras_mundo,
    carregar_regras_player,
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

_LOCK = threading.Lock()
_INTERVALO_PERSISTENCIA_SEGUNDOS = 1.0
_ultimo_persistencia_ts = 0.0
_PERSISTENCIA_LOCK = threading.Lock()
_persistencia_thread = None
_persistencia_snapshot_pendente = {}
_persistencia_secoes_pendentes: set[str] = set()
_NIVEL_MAXIMO_JOGADOR = 50
_SECOES_PERSISTENCIA = ("players", "npcs_vendedores", "estruturas_naturais_tocadas", "tempo_mundo")
_TIPOS_ESTADIO_RESPEITO = (
    "normal", "fogo", "agua", "planta", "eletrico", "gelo", "lutador", "venenoso", "terrestre", "voador",
    "psiquico", "inseto", "pedra", "fantasma", "dragao", "sombrio", "metal", "fada", "cosmico", "sonoro",
)
_CATEGORIAS_CONHECIMENTO = ("Efeitos", "Ataques", "Pokemons", "Itens", "Musicas")


def _valor_regra(regras: dict, chave: str, padrao):
    valor = regras.get(chave, padrao) if isinstance(regras, dict) else padrao
    return padrao if valor in (None, "") else valor


def _skins_liberadas_padrao() -> list[str]:
    regras = carregar_regras_player()
    minimo = int(_valor_regra(regras, "SkinInicialMin", 1))
    maximo = int(_valor_regra(regras, "SkinInicialMax", 12))
    minimo, maximo = sorted((minimo, maximo))
    pasta = Path("Recursos") / "Visual" / "Skins"
    if not pasta.exists():
        return ["1.png"]
    skins = sorted({p.name for p in pasta.glob("*.png") if p.is_file()})
    if not skins:
        return ["1.png"]

    def _indice_skin(nome: str) -> int | None:
        m = re.search(r"(\d+)", Path(nome).stem)
        return int(m.group(1)) if m else None

    filtradas = [s for s in skins if (_indice_skin(s) is not None and minimo <= int(_indice_skin(s)) <= maximo)]
    return filtradas or skins[: min(12, len(skins))]


def _normalizar_skins_liberadas(skins: list[str] | None) -> list[str]:
    regras = carregar_regras_player()
    minimo = int(_valor_regra(regras, "SkinInicialMin", 1))
    maximo = int(_valor_regra(regras, "SkinInicialMax", 12))
    minimo, maximo = sorted((minimo, maximo))
    padrao = _skins_liberadas_padrao()
    bruto = list(skins or [])
    if not bruto:
        return padrao
    normalizadas: list[str] = []
    for skin in bruto:
        nome = str(skin or "").strip()
        if not nome:
            continue
        if nome.lower().startswith("s") and nome[1:].isdigit():
            nome = nome[1:]
        if not nome.lower().endswith(".png"):
            nome = f"{nome}.png"
        m = re.search(r"(\d+)", Path(nome).stem)
        if m is None:
            continue
        idx = int(m.group(1))
        if idx < minimo or idx > maximo:
            continue
        normalizadas.append(f"{idx}.png")
    out = sorted(dict.fromkeys(normalizadas), key=lambda s: int(re.search(r"(\d+)", Path(s).stem).group(1)))
    return out or padrao


def _normalizar_conhecimento(conhecimento: dict | None) -> dict:
    bruto = conhecimento if isinstance(conhecimento, dict) else {}
    normalizado = {categoria: [] for categoria in _CATEGORIAS_CONHECIMENTO}
    aliases = {categoria.lower(): categoria for categoria in _CATEGORIAS_CONHECIMENTO}
    for chave, valores in bruto.items():
        categoria = aliases.get(str(chave or "").strip().lower())
        if categoria is None or not isinstance(valores, (list, tuple, set)):
            continue
        unicos = []
        for valor in valores:
            if valor is None:
                continue
            valor_norm = int(valor) if isinstance(valor, (int, float)) else str(valor).strip()
            if valor_norm == "":
                continue
            unicos.append(valor_norm)
        normalizado[categoria] = list(dict.fromkeys(unicos))
    return normalizado


def _contar_recursos_miticos_inventario(inventario: dict | None) -> int:
    itens = inventario.get("itens", []) if isinstance(inventario, dict) else []
    total = 0
    for item in list(itens or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("Estilo") or item.get("estilo") or "").strip().lower() != "recurso":
            continue
        raridade = item.get("Raridade", item.get("raridade", 0))
        try:
            eh_mitico = int(float(raridade or 0)) >= 6
        except (TypeError, ValueError):
            eh_mitico = "mitic" in str(raridade or "").strip().lower()
        if eh_mitico:
            try:
                total += max(1, int(item.get("quantidade", item.get("Quantidade", 1)) or 1))
            except (TypeError, ValueError):
                total += 1
    return total


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
    nivel_atual = max(0, int(nivel))
    if nivel_atual >= _NIVEL_MAXIMO_JOGADOR:
        return 0
    faixa = nivel_atual // 10
    incremento = (faixa + 1) * 100
    base_faixa = 100 + (500 * faixa * faixa) + (600 * faixa)
    return int(base_faixa + (nivel_atual - (faixa * 10)) * incremento)


def _normalizar_progresso_xp(dados: dict) -> None:
    nivel = max(0, min(_NIVEL_MAXIMO_JOGADOR, int(dados.get("nivel", 0) or 0)))
    xp = max(0, int(dados.get("xp", 0) or 0))
    while nivel < _NIVEL_MAXIMO_JOGADOR:
        alvo = _calcular_xp_alvo_por_nivel(nivel)
        if xp < alvo:
            dados["nivel"] = int(nivel)
            dados["xp"] = int(xp)
            dados["xp_alvo"] = int(alvo)
            return
        xp -= alvo
        nivel += 1
    dados["nivel"] = _NIVEL_MAXIMO_JOGADOR
    dados["xp"] = 0
    dados["xp_alvo"] = 0



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
    payload["atualizado_em"] = _agora_iso()
    with arquivo.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _recarregar_cerebro_mundo() -> None:
    try:
        from SimuladorServerJogo.Mundo.Cerebros.CerebroCentral import CEREBRO
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
    BANCO_DADOS.recarregar_mundo(_ESTADO_MUNDO, limpar_objetos=True)
    PACOTES_TICK.resetar()
    _SERVIDOR_ATIVO_ATUAL = pasta
    _recarregar_cerebro_mundo()


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
    regras = carregar_regras_player()
    dados = dict(personagem) if isinstance(personagem, dict) else {}
    dados["nivel"] = int(max(0, dados.get("nivel", 0)))
    dados["xp"] = int(max(0, dados.get("xp", 0)))
    dados["xp_alvo"] = int(max(0, dados.get("xp_alvo", _calcular_xp_alvo_por_nivel(dados["nivel"]))))
    dados["batalhas_totais"] = int(max(0, dados.get("batalhas_totais", 0)))
    dados["nivel_mochila"] = int(dados.get("nivel_mochila", _valor_regra(regras, "NivelMochila", 1)))
    dados["limite_slots_inventario"] = int(dados.get("limite_slots_inventario", _valor_regra(regras, "LimiteSlotsInventario", 32)))
    dados["limite_pokemons"] = int(dados.get("limite_pokemons", _valor_regra(regras, "LimitePokemons", 64)))
    dados["limite_times_pokemon"] = int(dados.get("limite_times_pokemon", _valor_regra(regras, "LimiteTimesPokemon", 6)))
    dados["batalhas_pvp_vencidas"] = int(dados.get("batalhas_pvp_vencidas", 0))
    dados["batalhas_bot_vencidas"] = int(dados.get("batalhas_bot_vencidas", 0))
    dados["baus_abertos"] = int(max(0, dados.get("baus_abertos", 0)))
    dados["metros_andados"] = float(max(0.0, dados.get("metros_andados", 0.0)))
    dados["tempo_jogo_segundos"] = float(max(0.0, dados.get("tempo_jogo_segundos", 0.0)))
    dados["dinheiro"] = int(dados.get("dinheiro", _valor_regra(regras, "Dinheiro", 20)))
    dados["insignias"] = list(dados.get("insignias", []))
    dados["maestria"] = int(dados.get("maestria", _valor_regra(regras, "Maestria", 0)))
    dados["limite_conhecimento"] = int(max(0, dados.get("limite_conhecimento", dados.get("LimiteConhecimento", 300))))
    dados["conhecimento"] = _normalizar_conhecimento(dados.get("conhecimento", dados.get("Conhecimento")))
    dados["eternidade_derrotada"] = bool(dados.get("eternidade_derrotada", dados.get("EternidadeDerrotada", False)))
    dados["grande_campeao_derrotado"] = bool(dados.get("grande_campeao_derrotado", dados.get("GrandeCampeaoDerrotado", False)))
    dados["estadios_liderados"] = list(dict.fromkeys(dados.get("estadios_liderados", dados.get("EstadiosLiderados", [])) or []))
    dados["moedas_maximas"] = int(max(0, dados.get("moedas_maximas", dados.get("MoedasMaximas", 0))))
    dados["recursos_miticos_maximos"] = int(max(0, dados.get("recursos_miticos_maximos", dados.get("RecursosMiticosMaximos", 0))))
    dados["skins_liberadas"] = _normalizar_skins_liberadas(dados.get("skins_liberadas"))
    dados["habilidades_aprendidas"] = list(dados.get("habilidades_aprendidas", []))
    for tipo in _TIPOS_ESTADIO_RESPEITO:
        chave = f"respeito_estadio_{tipo}"
        dados[chave] = int(max(0, min(4, dados.get(chave, 0))))

    stamina_max = float(dados.get("stamina_max", _valor_regra(regras, "StaminaMax", 100.0)))
    stamina = max(0.0, min(stamina_max, float(dados.get("stamina", stamina_max))))
    dados["stamina_max"] = stamina_max
    dados["stamina"] = stamina

    mapa_regras = {
        "velocidade_base_tiles": "VelocidadeBaseTiles",
        "bonus_velocidade_corrida_min": "BonusVelocidadeCorridaMin",
        "bonus_velocidade_corrida_max": "BonusVelocidadeCorridaMax",
        "tempo_aceleracao_corrida": "TempoAceleracaoCorrida",
        "tempo_desaceleracao_corrida": "TempoDesaceleracaoCorrida",
        "atraso_regeneracao_stamina": "AtrasoRegeneracaoStamina",
        "regeneracao_stamina_parado": "RegeneracaoStaminaParado",
        "regeneracao_stamina_andando": "RegeneracaoStaminaAndando",
        "custo_stamina_corrida": "CustoStaminaCorrida",
        "custo_stamina_corrida_max": "CustoStaminaCorridaMax",
        "custo_stamina_agua_rasa": "CustoStaminaAguaRasa",
        "custo_stamina_agua_funda": "CustoStaminaAguaFunda",
        "tapa_por_segundo": "TapaPorSegundo",
        "raio_tapa": "RaioTapa",
        "multiplicador_ferramenta_tapa": "MultiplicadorFerramentaTapa",
    }
    for campo, chave_regra in mapa_regras.items():
        dados[campo] = float(dados.get(campo, regras.get(chave_regra)))

    inv = dados.get("inventario") if isinstance(dados.get("inventario"), dict) else {}
    limite_pokemons = int(inv.get("limite_pokemons", dados.get("limite_pokemons", _valor_regra(regras, "LimitePokemons", 64))))
    limite_times_pokemon = int(inv.get("limite_times_pokemon", dados.get("limite_times_pokemon", _valor_regra(regras, "LimiteTimesPokemon", 6))))
    pokemons = list(inv.get("pokemons", []))[:limite_pokemons]
    times_pokemon = list(inv.get("times_pokemon", []))
    dados["inventario"] = {
        "itens": list(inv.get("itens", [])),
        "pokemons": pokemons,
        "times_pokemon": times_pokemon,
        "limite_itens": int(max(1, inv.get("limite_itens", 100))),
        "limite_slots": int(max(1, inv.get("limite_slots", dados.get("limite_slots_inventario", 32)))),
        "limite_pokemons": limite_pokemons,
        "limite_times_pokemon": limite_times_pokemon,
        "slot_selecionado": int(inv.get("slot_selecionado", 0)),
    }
    _normalizar_progresso_xp(dados)
    dimensao_atual = str(dados.get("dimensao_atual") or "Mundo")
    pos_dim = dados.get("posicoes_por_dimensao") if isinstance(dados.get("posicoes_por_dimensao"), dict) else {}
    pos_dim_norm = {}
    for chave, valor in pos_dim.items():
        if isinstance(valor, (list, tuple)) and len(valor) == 2:
            try:
                pos_dim_norm[str(chave)] = [float(valor[0]), float(valor[1])]
            except (TypeError, ValueError):
                continue
    if "Mundo" not in pos_dim_norm and dimensao_atual == "Mundo":
        pos_dim_norm["Mundo"] = [float(dados.get("posicao", [0.0, 0.0])[0]), float(dados.get("posicao", [0.0, 0.0])[1])]
    dados["dimensao_atual"] = dimensao_atual
    dados["posicoes_por_dimensao"] = pos_dim_norm
    dados["exploracao_chunks"] = _normalizar_exploracao_chunks(dados.get("exploracao_chunks"))
    fingerprint_mundo = _fingerprint_mundo_atual()
    if fingerprint_mundo:
        if str(dados.get("exploracao_chunks_world_id") or "") != fingerprint_mundo:
            dados["exploracao_chunks"] = {"Mundo": {}}
        dados["exploracao_chunks_world_id"] = fingerprint_mundo
    dados["dungeons"] = copy.deepcopy(dados.get("dungeons")) if isinstance(dados.get("dungeons"), dict) else {}
    return dados




def _normalizar_exploracao_chunks(valor: dict | None) -> dict:
    bruto = valor if isinstance(valor, dict) else {}
    mundo = bruto.get("Mundo") if isinstance(bruto.get("Mundo"), dict) else {}
    out_mundo: dict[str, list[int]] = {}
    for sx, ys in mundo.items():
        try:
            x = int(sx)
        except (TypeError, ValueError):
            continue
        conjunto: set[int] = set()
        if isinstance(ys, (list, tuple, set)):
            for y in ys:
                try:
                    conjunto.add(int(y))
                except (TypeError, ValueError):
                    continue
        if conjunto:
            out_mundo[str(x)] = sorted(conjunto)
    return {"Mundo": out_mundo}


def _fingerprint_mundo_atual() -> str:
    meta = _ESTADO_MUNDO.get("meta", {}) if isinstance(_ESTADO_MUNDO.get("meta"), dict) else {}
    if not meta:
        return ""
    seed = int(meta.get("seed", 0) or 0)
    largura = int(meta.get("largura_blocos", 0) or 0)
    altura = int(meta.get("altura_blocos", 0) or 0)
    chunks_x = int(meta.get("chunks_x", 0) or 0)
    chunks_y = int(meta.get("chunks_y", 0) or 0)
    chunk_blocos = int(meta.get("chunk_blocos", meta.get("chunk_blocos_disco", 10)) or 10)
    if largura <= 0 or altura <= 0:
        return ""
    return f"{seed}:{largura}:{altura}:{chunks_x}:{chunks_y}:{chunk_blocos}"


def _sincronizar_exploracao_mundo_atual(personagem: dict) -> bool:
    if not isinstance(personagem, dict):
        return False
    fingerprint = _fingerprint_mundo_atual()
    if not fingerprint:
        personagem["exploracao_chunks"] = _normalizar_exploracao_chunks(personagem.get("exploracao_chunks"))
        return False
    if str(personagem.get("exploracao_chunks_world_id") or "") != fingerprint:
        personagem["exploracao_chunks"] = {"Mundo": {}}
        personagem["exploracao_chunks_world_id"] = fingerprint
        return True
    personagem["exploracao_chunks"] = _normalizar_exploracao_chunks(personagem.get("exploracao_chunks"))
    return False


def obter_exploracao_chunks(usuario: str) -> dict:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return {"Mundo": {}}
    if not usuario:
        return {"Mundo": {}}
    with _LOCK:
        personagem = _ESTADO.get("personagens", {}).get(usuario)
        if not isinstance(personagem, dict):
            return {"Mundo": {}}
        if _sincronizar_exploracao_mundo_atual(personagem):
            _persistir_personagens()
        return _normalizar_exploracao_chunks(personagem.get("exploracao_chunks"))


def registrar_chunks_explorados(usuario: str, chunks: list[tuple[int, int]] | set[tuple[int, int]], dimensao: str = "Mundo") -> None:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return
    if not usuario or str(dimensao or "Mundo") != "Mundo" or not chunks:
        return
    with _LOCK:
        personagem = _ESTADO.get("personagens", {}).get(usuario)
        if not isinstance(personagem, dict):
            return
        _sincronizar_exploracao_mundo_atual(personagem)
        explor = _normalizar_exploracao_chunks(personagem.get("exploracao_chunks"))
        mundo = explor.setdefault("Mundo", {})
        alterou = False
        for cx, cy in chunks:
            sx = str(int(cx))
            y = int(cy)
            arr = set(mundo.get(sx, []))
            if y not in arr:
                arr.add(y)
                mundo[sx] = sorted(arr)
                alterou = True
        if alterou:
            personagem["exploracao_chunks"] = explor
            _persistir_personagens()


def _normalizar_inventario(payload: dict) -> dict:
    base = payload if isinstance(payload, dict) else {}
    itens = list(base.get("itens", []))
    itens_norm = []
    for item in itens:
        if isinstance(item, dict):
            d = dict(item)
            d["quantidade"] = int(max(1, d.get("quantidade", 1)))
            itens_norm.append({str(k): d[k] for k in sorted(d.keys())})
        else:
            itens_norm.append(item)
    limite_pokemons = int(max(1, base.get("limite_pokemons", 64)))
    limite_times_pokemon = int(max(1, base.get("limite_times_pokemon", 6)))
    return {
        "itens": itens_norm,
        "pokemons": list(base.get("pokemons", []))[:limite_pokemons],
        "times_pokemon": list(base.get("times_pokemon", [])),
        "doces": {str(k): int(max(0, v or 0)) for k, v in (base.get("doces", {}).items() if isinstance(base.get("doces"), dict) else [])},
        "limite_itens": int(max(1, base.get("limite_itens", 100))),
        "limite_slots": int(max(1, base.get("limite_slots", 32))),
        "limite_pokemons": limite_pokemons,
        "limite_times_pokemon": limite_times_pokemon,
        "slot_selecionado": int(base.get("slot_selecionado", 0)),
    }


def _inventario_tem_conteudo(inventario: dict | None) -> bool:
    if not isinstance(inventario, dict):
        return False
    return bool(inventario.get("itens") or inventario.get("pokemons") or inventario.get("times_pokemon") or inventario.get("doces"))


def _mesclar_perfil_atualizacao(personagem_atual: dict, atualizacao: dict) -> dict:
    base = _normalizar_perfil(personagem_atual)
    payload = dict(atualizacao) if isinstance(atualizacao, dict) else {}
    dinheiro_antes = int(base.get("dinheiro", 0) or 0)

    campos_int = (
        "nivel",
        "xp",
        "xp_alvo",
        "batalhas_totais",
        "nivel_mochila",
        "batalhas_pvp_vencidas",
        "batalhas_bot_vencidas",
        "baus_abertos",
        "dinheiro",
        "maestria",
        "limite_conhecimento",
        "limite_slots_inventario",
        "limite_pokemons",
        "limite_times_pokemon",
        *[f"respeito_estadio_{tipo}" for tipo in _TIPOS_ESTADIO_RESPEITO],
    )
    for campo in campos_int:
        if campo in payload:
            base[campo] = int(payload.get(campo, base[campo]))
    if "moedas_maximas" in payload:
        base["moedas_maximas"] = max(int(base.get("moedas_maximas", 0) or 0), int(payload.get("moedas_maximas", 0) or 0))
    if "recursos_miticos_maximos" in payload:
        base["recursos_miticos_maximos"] = max(int(base.get("recursos_miticos_maximos", 0) or 0), int(payload.get("recursos_miticos_maximos", 0) or 0))
    if int(base.get("dinheiro", 0) or 0) > dinheiro_antes:
        base["moedas_maximas"] = max(int(base.get("moedas_maximas", 0) or 0), int(base.get("dinheiro", 0) or 0))
    if "LimiteConhecimento" in payload:
        base["limite_conhecimento"] = int(payload.get("LimiteConhecimento", base.get("limite_conhecimento", 300)))
    base["nivel"] = max(0, int(base.get("nivel", 0)))
    base["xp"] = max(0, int(base.get("xp", 0)))
    base["xp_alvo"] = max(0, int(base.get("xp_alvo", _calcular_xp_alvo_por_nivel(base["nivel"]))))
    base["batalhas_totais"] = max(0, int(base.get("batalhas_totais", 0)))
    base["baus_abertos"] = max(0, int(base.get("baus_abertos", 0)))
    if "metros_andados" in payload:
        base["metros_andados"] = float(payload.get("metros_andados", base.get("metros_andados", 0.0)))
    if "tempo_jogo_segundos" in payload:
        base["tempo_jogo_segundos"] = float(payload.get("tempo_jogo_segundos", base.get("tempo_jogo_segundos", 0.0)))
    base["metros_andados"] = max(0.0, float(base.get("metros_andados", 0.0)))
    base["tempo_jogo_segundos"] = max(0.0, float(base.get("tempo_jogo_segundos", 0.0)))

    if "insignias" in payload:
        base["insignias"] = list(payload.get("insignias", []))
    if "skins_liberadas" in payload:
        base["skins_liberadas"] = _normalizar_skins_liberadas(payload.get("skins_liberadas", []))
    if "habilidades_aprendidas" in payload:
        base["habilidades_aprendidas"] = list(payload.get("habilidades_aprendidas", []))
    if "eternidade_derrotada" in payload:
        base["eternidade_derrotada"] = bool(payload.get("eternidade_derrotada"))
    if "grande_campeao_derrotado" in payload:
        base["grande_campeao_derrotado"] = bool(payload.get("grande_campeao_derrotado"))
    if "estadios_liderados" in payload:
        base["estadios_liderados"] = list(dict.fromkeys(payload.get("estadios_liderados") or []))
    conhecimento_payload = payload.get("conhecimento", payload.get("Conhecimento"))
    if isinstance(conhecimento_payload, dict):
        base["conhecimento"] = _normalizar_conhecimento(conhecimento_payload)
    if "exploracao_chunks" in payload:
        base["exploracao_chunks"] = _normalizar_exploracao_chunks(payload.get("exploracao_chunks"))
    if isinstance(payload.get("dungeons"), dict):
        base["dungeons"] = copy.deepcopy(payload.get("dungeons"))

    stamina_max = float(base.get("stamina_max", 100.0))
    if "stamina_max" in payload:
        stamina_max = max(1.0, float(payload.get("stamina_max", stamina_max)))

    stamina = float(base.get("stamina", stamina_max))
    if "stamina" in payload:
        stamina = float(payload.get("stamina", stamina))

    base["stamina_max"] = stamina_max
    base["stamina"] = max(0.0, min(stamina_max, stamina))
    if "tapa_por_segundo" in payload:
        base["tapa_por_segundo"] = max(0.1, float(payload.get("tapa_por_segundo", base.get("tapa_por_segundo", 2.0))))
    if "raio_tapa" in payload:
        base["raio_tapa"] = max(0.05, float(payload.get("raio_tapa", base.get("raio_tapa", 0.36))))
    if "multiplicador_ferramenta_tapa" in payload:
        base["multiplicador_ferramenta_tapa"] = max(1.0, float(payload.get("multiplicador_ferramenta_tapa", base.get("multiplicador_ferramenta_tapa", 1.5))))
    _normalizar_progresso_xp(base)
    return base


def _recarregar_mundo():
    global _ESTADO_MUNDO
    _garantir_estado_ativo()
    _ESTADO_MUNDO = carregar_estado_mundo()
    _ESTADO_MUNDO["tempo_mundo"] = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))


def _limites_mundo_atuais() -> tuple[float, float]:
    meta = _ESTADO_MUNDO.get("meta", {}) if isinstance(_ESTADO_MUNDO, dict) else {}
    largura_meta = float(meta.get("largura_blocos", 0)) if isinstance(meta, dict) else 0.0
    altura_meta = float(meta.get("altura_blocos", 0)) if isinstance(meta, dict) else 0.0
    largura = largura_meta if largura_meta > 0 else float(GERADOR_MUNDO.LARGURA_BLOCOS)
    altura = altura_meta if altura_meta > 0 else float(GERADOR_MUNDO.ALTURA_BLOCOS)
    return (max(1.0, largura), max(1.0, altura))


def _criar_novo_mundo_sync():
    global _ESTADO_MUNDO
    _garantir_estado_ativo()
    from SimuladorServerJogo.Gerais.Rotas.Ativador import resetar_estado_clientes

    def _callback_progresso(percentual: int, mensagem: str):
        with _LOCK:
            _set_geracao(progresso=percentual, mensagem=mensagem)

    players = dict(_ESTADO.get("personagens", {}))
    _set_geracao(em_andamento=True, progresso=1, mensagem="Preparando geração do mundo", erro="", operacao="criacao")
    _ESTADO_MUNDO = gerar_novo_estado_mundo(players=players, callback_progresso=_callback_progresso)
    _ESTADO_MUNDO["tempo_mundo"] = _tempo_mundo_padrao()
    _set_geracao(progresso=98, mensagem="Salvando estado do mundo")
    salvar_estado_mundo(_ESTADO_MUNDO)
    _set_geracao(progresso=99, mensagem="Carregando mundo no servidor")
    BANCO_DADOS.recarregar_mundo(_ESTADO_MUNDO, limpar_objetos=True)
    PACOTES_TICK.resetar()
    resetar_estado_clientes()
    _recarregar_cerebro_mundo()
    _set_geracao(progresso=100, mensagem="Mundo pronto")


def _worker_criacao_mundo():
    try:
        _criar_novo_mundo_sync()
        with _LOCK:
            _ESTADO["mundo_existente"] = True
            _salvar_json_servidor_ativo_locked()
            _set_geracao(em_andamento=False, progresso=100, mensagem="Mundo pronto", erro="", operacao="nenhuma")
    except Exception as exc:
        with _LOCK:
            _ESTADO_MUNDO.clear()
            _ESTADO_MUNDO.update(_estado_mundo_vazio())
            _ESTADO["mundo_existente"] = False
            _ESTADO["ligado"] = False
            _salvar_json_servidor_ativo_locked()
            _set_geracao(em_andamento=False, progresso=0, mensagem="Falha ao criar mundo", erro=str(exc), operacao="nenhuma")


def _apagar_mundo():
    global _ESTADO_MUNDO
    _garantir_estado_ativo()
    from SimuladorServerJogo.Gerais.Rotas.Ativador import resetar_estado_clientes
    limpar_arquivos_mundo()
    _ESTADO_MUNDO = _estado_mundo_vazio()
    _ESTADO["personagens"].clear()
    _ESTADO["jogadores_com_personagem"].clear()
    BANCO_DADOS.recarregar_mundo(_ESTADO_MUNDO, limpar_objetos=True)
    resetar_estado_clientes()
    _recarregar_cerebro_mundo()




def _worker_apagar_mundo():
    from SimuladorServerJogo.Mundo.Cerebros.CerebroCentral import CEREBRO
    try:
        with _LOCK:
            _set_geracao(em_andamento=True, progresso=3, mensagem="Apagando mundo", erro="", operacao="remocao")
        with _LOCK:
            _set_geracao(progresso=18, mensagem="Preparando limpeza do estado do mundo")
        with _LOCK:
            _set_geracao(progresso=37, mensagem="Removendo arquivos do mundo")
        _apagar_mundo()
        with _LOCK:
            _ESTADO["mundo_existente"] = False
            _ESTADO["ligado"] = False
            _salvar_json_servidor_ativo_locked()
            _set_geracao(progresso=62, mensagem="Recarregando banco de dados")
        with _LOCK:
            _set_geracao(progresso=79, mensagem="Sincronizando clientes")
        with _LOCK:
            _set_geracao(progresso=94, mensagem="Finalizando remoção")
        with _LOCK:
            _set_geracao(em_andamento=False, progresso=100, mensagem="Mundo removido", erro="", operacao="nenhuma")
            CEREBRO.desligar_servidor()
    except Exception as exc:
        with _LOCK:
            _ESTADO["mundo_existente"] = False
            _ESTADO["ligado"] = False
            _salvar_json_servidor_ativo_locked()
            _set_geracao(em_andamento=False, progresso=0, mensagem="Falha ao apagar mundo", erro=str(exc), operacao="nenhuma")
            CEREBRO.desligar_servidor()

def _sync_personagens_mundo():
    _agendar_persistencia_locked(force=True, secoes={"players"})


def _persistir_personagens(force: bool = False) -> None:
    _agendar_persistencia_locked(force=force, secoes={"players"})




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
    regras["mundo"] = {
        "chunk_tiles": int(_valor_regra(carregar_regras_mundo(), "ChunkTiles", 10)),
        "seed": int(seed_mundo),
        "transicao_apenas_um_lado": True,
        "escala_estrutura_min": float(escala_min),
        "escala_estrutura_max": float(escala_max),
    }
    return regras

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
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return _tempo_mundo_padrao()
    with _LOCK:
        tempo = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))
        _ESTADO_MUNDO["tempo_mundo"] = tempo
        return dict(tempo)


def atualizar_tempo_mundo_estado(tempo: dict, force: bool = False) -> None:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return
    with _LOCK:
        _ESTADO_MUNDO["tempo_mundo"] = _normalizar_tempo_mundo(tempo)
        _agendar_persistencia_locked(force=force, secoes={"tempo_mundo"})


def registrar_estrutura_natural_tocada_estado(estrutura_id: int, quantidade_restante: int, force: bool = False) -> None:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return
    with _LOCK:
        tocadas = _ESTADO_MUNDO.get("estruturas_naturais_tocadas")
        if not isinstance(tocadas, dict):
            tocadas = {}
            _ESTADO_MUNDO["estruturas_naturais_tocadas"] = tocadas
        tocadas[str(int(estrutura_id))] = max(0, int(quantidade_restante or 0))
        _agendar_persistencia_locked(force=force, secoes={"estruturas_naturais_tocadas"})


def carregar_npcs_vendedores_estado() -> dict:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return {}
    with _LOCK:
        bruto = _ESTADO_MUNDO.get("npcs_vendedores", {}) if isinstance(_ESTADO_MUNDO, dict) else {}
        return {str(k): dict(v) for k, v in bruto.items()} if isinstance(bruto, dict) else {}


def salvar_npcs_vendedores_estado(npcs: dict, force: bool = False) -> None:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return
    with _LOCK:
        _ESTADO_MUNDO["npcs_vendedores"] = {str(k): dict(v) for k, v in (npcs or {}).items() if isinstance(v, dict)}
        _agendar_persistencia_locked(force=force, secoes={"npcs_vendedores"})


def definir_ligado(ativo):
    _garantir_estado_ativo()
    from SimuladorServerJogo.Mundo.Cerebros.CerebroCentral import CEREBRO
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
    _garantir_estado_ativo()
    with _LOCK:
        ativo = bool(ativo)
        if ativo:
            if _ESTADO_GERACAO["em_andamento"]:
                return False, "A geração de mundo já está em andamento"
            _ESTADO["mundo_existente"] = False
            _set_geracao(em_andamento=True, progresso=1, mensagem="Preparando criação do mundo...", erro="", operacao="criacao")
            thread = threading.Thread(target=_worker_criacao_mundo, daemon=True)
            thread.start()
            return True, "Criação de mundo iniciada"

        if _ESTADO_GERACAO["em_andamento"]:
            return False, "Não é possível apagar o mundo enquanto a geração está em andamento"

        _set_geracao(em_andamento=True, progresso=1, mensagem="Apagando mundo", erro="", operacao="remocao")
        thread = threading.Thread(target=_worker_apagar_mundo, daemon=True)
        thread.start()
        return True, "Remoção de mundo iniciada"


def adicionar_personagem(usuario, skin, pokemon_inicial):
    _garantir_estado_ativo()
    with _LOCK:
        if _ESTADO_GERACAO["em_andamento"]:
            return False, "Aguarde a criação do mundo terminar"
        if not _ESTADO["mundo_existente"]:
            return False, "Este servidor ainda não possui mundo"
        if usuario in _ESTADO["jogadores_com_personagem"]:
            return False, "Sua conta já possui personagem neste servidor"

        _ESTADO["jogadores_com_personagem"].add(usuario)
        _recarregar_mundo()
        spawn = obter_posicao_spawn(_ESTADO_MUNDO)
        pokemon_inicial_materializado = criar_pokemon_inicial_materializado(pokemon_inicial)

        _ESTADO["personagens"][usuario] = _normalizar_perfil(
            {
                "nome": usuario,
                "skin": skin,
                "pokemon_inicial": pokemon_inicial,
                "posicao": [spawn[0], spawn[1]],
                "inventario": {
                    "pokemons": [pokemon_inicial_materializado],
                },
            }
        )
        _persistir_personagens(force=True)

    return True, "Personagem criado com sucesso"


def obter_personagem_para_entrada(usuario):
    _garantir_estado_ativo()
    if not usuario:
        return None

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return None

        dados = _normalizar_perfil(personagem)
        posicao = dados.get("posicao")
        posicao_valida = isinstance(posicao, (list, tuple)) and len(posicao) == 2
        if posicao_valida:
            try:
                x = float(posicao[0])
                y = float(posicao[1])
                largura, altura = _limites_mundo_atuais()
                if x < 0.0 or y < 0.0 or x >= largura or y >= altura:
                    posicao_valida = False
            except (TypeError, ValueError):
                posicao_valida = False

        if not posicao_valida:
            spawn = obter_posicao_spawn(_ESTADO_MUNDO)
            x, y = _clamp_posicao(spawn)
            dados["posicao"] = [x, y]
            _ESTADO["personagens"][usuario] = dados
            _persistir_personagens(force=True)
        else:
            x, y = _clamp_posicao(posicao)
            dados["posicao"] = [x, y]
            _ESTADO["personagens"][usuario] = dados

        return dict(dados)


def atualizar_posicao_personagem(usuario, posicao, dimensao: str = "Mundo"):
    _garantir_estado_ativo()
    if not usuario:
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return

        x, y = _clamp_posicao(posicao)
        dim = str(dimensao or "Mundo")
        personagem["posicao"] = [x, y]
        personagem["dimensao_atual"] = dim
        pos_dim = personagem.get("posicoes_por_dimensao") if isinstance(personagem.get("posicoes_por_dimensao"), dict) else {}
        pos_dim[dim] = [x, y]
        personagem["posicoes_por_dimensao"] = pos_dim
        _persistir_personagens()


def _posicao_mundo_valida(posicao) -> bool:
    try:
        x = float(posicao[0])
        y = float(posicao[1])
    except (TypeError, ValueError, IndexError):
        return False
    largura, altura = BANCO_DADOS.limites_mundo()
    return 0.0 <= x < float(largura) and 0.0 <= y < float(altura)


def _tile_mundo_seguro(posicao) -> bool:
    if not _posicao_mundo_valida(posicao):
        return False
    try:
        return int(BANCO_DADOS.tile_em(int(float(posicao[0])), int(float(posicao[1])))) != 0
    except (TypeError, ValueError):
        return False


def _tick_servidor_atual() -> int:
    return max(0, int(PACOTES_TICK.tick_atual()))


def _vida_player(player) -> dict:
    estado = getattr(player, "estado_extra", {}) if player is not None and isinstance(getattr(player, "estado_extra", {}), dict) else {}
    vida = estado.get("vida_player") if isinstance(estado.get("vida_player"), dict) else {}
    regras = carregar_regras_dungeons()
    coracoes_max = int(vida.get("coracoes_max", regras.get("coracoes_maximos", regras.get("coracoes_iniciais", 3))) or 3)
    coracoes_max = max(1, coracoes_max)
    coracoes = int(vida.get("coracoes", coracoes_max) or coracoes_max)
    vida = {"coracoes": max(0, min(coracoes_max, coracoes)), "coracoes_max": coracoes_max}
    estado["vida_player"] = vida
    estado_dungeon = estado.get("estado_dungeon") if isinstance(estado.get("estado_dungeon"), dict) else None
    if estado_dungeon is not None:
        estado_dungeon["coracoes"] = int(vida["coracoes"])
        estado_dungeon["coracoes_max"] = int(vida["coracoes_max"])
    return vida


def player_invulneravel(player, tick: int | None = None) -> bool:
    estado = getattr(player, "estado_extra", {}) if player is not None and isinstance(getattr(player, "estado_extra", {}), dict) else {}
    atual = _tick_servidor_atual() if tick is None else int(tick)
    return atual < int(estado.get("invulneravel_ate_tick", 0) or 0)


def aplicar_invulnerabilidade_player(player, ticks: int = 90, motivo: str = "") -> bool:
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False
    ate = _tick_servidor_atual() + max(1, int(ticks or 90))
    player.estado_extra["invulneravel_ate_tick"] = max(int(player.estado_extra.get("invulneravel_ate_tick", 0) or 0), ate)
    player.estado_extra["invulneravel_motivo"] = str(motivo or "")
    estado_dungeon = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else None
    if estado_dungeon is not None:
        estado_dungeon["invulneravel_dungeon_ate_tick"] = int(player.estado_extra["invulneravel_ate_tick"])
    return True


def matar_player(player, motivo: str = "", registrar_diff=None) -> bool:
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False
    estado = player.estado_extra
    _restaurar_inventario_player_persistido(str(estado.get("usuario") or ""), player)
    if bool(estado.get("morto", False) and estado.get("game_over", False)):
        return False
    estado["morto"] = True
    estado["game_over"] = True
    estado["motivo_morte"] = str(motivo or "morte")
    BANCO_DADOS.atualizar_objeto(int(player.Id), {"estado": estado})
    if callable(registrar_diff) and hasattr(player, "serializar"):
        registrar_diff("update", payload=player.serializar(), escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 999999.0}, objeto_id=int(player.Id), autor="server", categoria="player")
    return True


def aplicar_dano_player(player, quantidade: int = 1, motivo: str = "", registrar_diff=None, ignorar_invulnerabilidade: bool = False) -> bool:
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False
    estado = player.estado_extra
    if bool(estado.get("morto", False) or estado.get("game_over", False) or estado.get("queda_buraco", False)):
        return False
    if not bool(ignorar_invulnerabilidade) and player_invulneravel(player):
        return False
    vida = _vida_player(player)
    vida["coracoes"] = max(0, int(vida["coracoes"]) - max(1, int(quantidade or 1)))
    _vida_player(player)
    estado["ultimo_dano_motivo"] = str(motivo or "")
    aplicar_invulnerabilidade_player(player, 90, motivo)
    if int(vida["coracoes"]) <= 0:
        matar_player(player, str(motivo or "sem_coracoes"), registrar_diff=registrar_diff)
        return True
    BANCO_DADOS.atualizar_objeto(int(player.Id), {"estado": estado})
    if callable(registrar_diff) and hasattr(player, "serializar"):
        registrar_diff("update", payload=player.serializar(), escopo={"centro": [player.posicao[0], player.posicao[1]], "raio": 120}, objeto_id=int(player.Id), autor="server", categoria="player")
    return True


def registrar_checkpoint_mundo_seguro(usuario, player) -> bool:
    if not usuario or player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False
    if str(player.estado_extra.get("dimensao") or "Mundo") != "Mundo":
        return False
    pos = [float(player.posicao[0]), float(player.posicao[1])]
    if not _tile_mundo_seguro(pos):
        return False
    chunk = BANCO_DADOS.chunk_da_posicao(pos)
    checkpoint = {"chunk": [int(chunk[0]), int(chunk[1])], "posicao": pos}
    anterior = player.estado_extra.get("checkpoint_mundo") if isinstance(player.estado_extra.get("checkpoint_mundo"), dict) else None
    if isinstance(anterior, dict) and anterior.get("chunk") != checkpoint["chunk"]:
        player.estado_extra["checkpoint_mundo_anterior"] = dict(anterior)
    player.estado_extra["checkpoint_mundo"] = dict(checkpoint)
    with _LOCK:
        personagem = _ESTADO["personagens"].get(str(usuario))
        if isinstance(personagem, dict):
            if isinstance(anterior, dict) and anterior.get("chunk") != checkpoint["chunk"]:
                personagem["checkpoint_mundo_anterior"] = dict(anterior)
            personagem["checkpoint_mundo"] = dict(checkpoint)
            _persistir_personagens()
    return True


def registrar_checkpoint_mundo_chunk_seguro(usuario, player, chunk, posicao=None) -> bool:
    if not usuario or player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False
    try:
        chunk_norm = BANCO_DADOS.normalizar_chunk((int(chunk[0]), int(chunk[1])))
    except (TypeError, ValueError, IndexError):
        return False
    pos = None
    if isinstance(posicao, (list, tuple)) and len(posicao) == 2 and _tile_mundo_seguro(posicao):
        if BANCO_DADOS.chunk_da_posicao(posicao) == chunk_norm:
            pos = [float(posicao[0]), float(posicao[1])]
    if pos is None:
        pos = _posicao_segura_no_chunk(chunk_norm, aleatoria=True)
    if pos is None:
        return False
    checkpoint = {"chunk": [int(chunk_norm[0]), int(chunk_norm[1])], "posicao": pos}
    anterior = player.estado_extra.get("checkpoint_mundo") if isinstance(player.estado_extra.get("checkpoint_mundo"), dict) else None
    if isinstance(anterior, dict) and anterior.get("chunk") != checkpoint["chunk"]:
        player.estado_extra["checkpoint_mundo_anterior"] = dict(anterior)
    player.estado_extra["checkpoint_mundo"] = dict(checkpoint)
    with _LOCK:
        personagem = _ESTADO["personagens"].get(str(usuario))
        if isinstance(personagem, dict):
            if isinstance(anterior, dict) and anterior.get("chunk") != checkpoint["chunk"]:
                personagem["checkpoint_mundo_anterior"] = dict(anterior)
            personagem["checkpoint_mundo"] = dict(checkpoint)
            _persistir_personagens()
    return True


def _posicao_segura_no_chunk(chunk, aleatoria: bool = False) -> list[float] | None:
    try:
        cx, cy = int(chunk[0]), int(chunk[1])
    except (TypeError, ValueError, IndexError):
        return None
    tx, ty = BANCO_DADOS.total_chunks()
    if cx < 0 or cy < 0 or cx >= int(tx) or cy >= int(ty):
        return None
    grid = BANCO_DADOS.chunk_em_grade((cx, cy))
    tamanho = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
    candidatos: list[list[float]] = []
    for y, linha in enumerate(grid):
        if not isinstance(linha, list):
            continue
        for x, tile in enumerate(linha):
            try:
                if int(tile) != 0:
                    candidatos.append([float(cx * tamanho + x) + 0.5, float(cy * tamanho + y) + 0.5])
            except (TypeError, ValueError):
                continue
    if not candidatos:
        return None
    return random.choice(candidatos) if bool(aleatoria) else candidatos[0]


def _posicao_segura_perto_spawn() -> list[float] | None:
    spawn = obter_posicao_spawn(_ESTADO_MUNDO)
    sx, sy = _clamp_posicao(spawn)
    if _tile_mundo_seguro((sx, sy)):
        return [float(sx), float(sy)]
    largura, altura = BANCO_DADOS.limites_mundo()
    for raio in range(1, 49):
        x0, x1 = int(sx) - raio, int(sx) + raio
        y0, y1 = int(sy) - raio, int(sy) + raio
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                if 0 <= x < largura and 0 <= y < altura and _tile_mundo_seguro((x + 0.5, y + 0.5)):
                    return [float(x) + 0.5, float(y) + 0.5]
        for y in range(y0 + 1, y1):
            for x in (x0, x1):
                if 0 <= x < largura and 0 <= y < altura and _tile_mundo_seguro((x + 0.5, y + 0.5)):
                    return [float(x) + 0.5, float(y) + 0.5]
    return None


def resolver_respawn_mundo_seguro(usuario, player) -> list[float]:
    estado = getattr(player, "estado_extra", {}) if player is not None and isinstance(getattr(player, "estado_extra", {}), dict) else {}
    checkpoint = estado.get("checkpoint_mundo") if isinstance(estado.get("checkpoint_mundo"), dict) else None
    if checkpoint is None and usuario:
        with _LOCK:
            personagem = _ESTADO["personagens"].get(str(usuario))
            checkpoint = personagem.get("checkpoint_mundo") if isinstance(personagem, dict) and isinstance(personagem.get("checkpoint_mundo"), dict) else None
    if isinstance(checkpoint, dict) and player is not None and not _tile_mundo_seguro(getattr(player, "posicao", [])):
        chunk_morte = BANCO_DADOS.chunk_da_posicao(getattr(player, "posicao", [0.0, 0.0]))
        if checkpoint.get("chunk") == [int(chunk_morte[0]), int(chunk_morte[1])]:
            anterior = estado.get("checkpoint_mundo_anterior") if isinstance(estado.get("checkpoint_mundo_anterior"), dict) else None
            if anterior is None and usuario:
                with _LOCK:
                    personagem = _ESTADO["personagens"].get(str(usuario))
                    anterior = personagem.get("checkpoint_mundo_anterior") if isinstance(personagem, dict) and isinstance(personagem.get("checkpoint_mundo_anterior"), dict) else None
            if isinstance(anterior, dict):
                checkpoint = anterior
                estado["checkpoint_mundo"] = dict(anterior)
            else:
                checkpoint = None
    if isinstance(checkpoint, dict):
        pos = checkpoint.get("posicao")
        chunk_pos = checkpoint.get("chunk")
        if isinstance(pos, (list, tuple)) and len(pos) == 2 and _tile_mundo_seguro(pos):
            chunk_pos = chunk_pos if isinstance(chunk_pos, (list, tuple)) and len(chunk_pos) == 2 else BANCO_DADOS.chunk_da_posicao(pos)
            pos_chunk = _posicao_segura_no_chunk(chunk_pos, aleatoria=True)
            return pos_chunk or [float(pos[0]), float(pos[1])]
        pos_chunk = _posicao_segura_no_chunk(chunk_pos, aleatoria=True) if isinstance(chunk_pos, (list, tuple)) and len(chunk_pos) == 2 else None
        if pos_chunk is not None:
            return pos_chunk
    perto_spawn = _posicao_segura_perto_spawn()
    if perto_spawn is not None:
        return perto_spawn
    sx, sy = _clamp_posicao(obter_posicao_spawn(_ESTADO_MUNDO))
    return [float(sx), float(sy)]


def aplicar_respawn_mundo(usuario, player, motivo="respawn", registrar_diff=None):
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return None
    _restaurar_inventario_player_persistido(str(usuario or player.estado_extra.get("usuario") or ""), player)
    pos = resolver_respawn_mundo_seguro(usuario, player)
    estado = player.estado_extra
    estado["dimensao"] = "Mundo"
    estado["morto"] = False
    estado["game_over"] = False
    estado["queda_buraco"] = False
    estado["motivo_respawn"] = str(motivo or "respawn")
    for chave in ("motivo_morte", "estado_dungeon", "queda_buraco_pendente", "queda_buraco_pendente_ate_tick", "queda_buraco_inicio_tick", "queda_buraco_morte_tick", "animacao_queda_tick"):
        estado.pop(chave, None)
    vida = _vida_player(player)
    vida["coracoes"] = int(vida["coracoes_max"])
    pos_dim = estado.get("posicoes_por_dimensao") if isinstance(estado.get("posicoes_por_dimensao"), dict) else {}
    pos_dim["Mundo"] = [float(pos[0]), float(pos[1])]
    estado["posicoes_por_dimensao"] = pos_dim
    perfil = estado.get("perfil") if isinstance(estado.get("perfil"), dict) else {}
    if perfil:
        perfil["stamina"] = float(perfil.get("stamina_max", perfil.get("stamina", 100.0)) or 100.0)
        estado["perfil"] = perfil
    aplicar_invulnerabilidade_player(player, 90, str(motivo or "respawn"))
    BANCO_DADOS.atualizar_objeto(int(player.Id), {"posicao": pos, "estado": estado, "perfil": perfil})
    atualizar_posicao_personagem(str(usuario or estado.get("usuario") or ""), pos, dimensao="Mundo")
    if perfil:
        atualizar_perfil_personagem(str(usuario or estado.get("usuario") or ""), perfil)
    registrar_checkpoint_mundo_seguro(str(usuario or estado.get("usuario") or ""), player)
    if callable(registrar_diff) and hasattr(player, "serializar"):
        registrar_diff(
            "update",
            payload=player.serializar(),
            escopo={"centro": [float(pos[0]), float(pos[1])], "raio": 999999.0},
            objeto_id=int(player.Id),
            autor="server",
            categoria="player",
        )
    return player


def _restaurar_inventario_player_persistido(usuario: str, player) -> bool:
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict) or not str(usuario or "").strip():
        return False
    atual = player.estado_extra.get("inventario") if isinstance(player.estado_extra.get("inventario"), dict) else {}
    if _inventario_tem_conteudo(atual):
        return False
    with _LOCK:
        personagem = _ESTADO["personagens"].get(str(usuario))
        persistido = copy.deepcopy(personagem.get("inventario")) if isinstance(personagem, dict) and isinstance(personagem.get("inventario"), dict) else None
    if not _inventario_tem_conteudo(persistido):
        return False
    player.estado_extra["inventario"] = _normalizar_inventario(persistido)
    return True




def atualizar_inventario_personagem(usuario, inventario):
    _garantir_estado_ativo()
    if not usuario or not isinstance(inventario, dict):
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return
        personagem["inventario"] = _normalizar_inventario(inventario)
        personagem["recursos_miticos_maximos"] = max(int(personagem.get("recursos_miticos_maximos", 0) or 0), _contar_recursos_miticos_inventario(personagem["inventario"]))
        _persistir_personagens()


def atualizar_perfil_personagem(usuario, perfil):
    _garantir_estado_ativo()
    if not usuario or not isinstance(perfil, dict):
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return
        personagem.update(_mesclar_perfil_atualizacao(personagem, perfil))
        _persistir_personagens()
