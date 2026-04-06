import threading
import time
import re
from pathlib import Path

import SimuladorServerJogo.Geradores.GeradorMundo as GERADOR_MUNDO
from SimuladorServerJogo.Geradores.GeradorMundo import (
    carregar_estado_mundo,
    gerar_novo_estado_mundo,
    limpar_arquivos_mundo,
    obter_posicao_spawn,
    salvar_estado_mundo,
)
from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.TiqueServidor import TIQUE_SERVIDOR
from SimuladorServerJogo.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado
from SimuladorServerJogo.Regras.Loader import carregar_regras_player, carregar_regras_mundo

_CHAVE_SEGURANCA = "1900"
_ESTADO_MUNDO = carregar_estado_mundo()

_ESTADO = {
    "nome": "Servidor Indigo",
    "ip": "203.0.113.77:8123",
    "ligado": bool(_ESTADO_MUNDO.get("meta")),
    "mundo_existente": bool(_ESTADO_MUNDO.get("meta")),
    "banidos": {"JogadorBanido"},
    "jogadores_com_personagem": set(_ESTADO_MUNDO.get("players", {}).keys()),
    "personagens": dict(_ESTADO_MUNDO.get("players", {})),
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
_NIVEL_MAXIMO_JOGADOR = 50
_TIPOS_ESTADIO_RESPEITO = (
    "normal", "fogo", "agua", "planta", "eletrico", "gelo", "lutador", "venenoso", "terrestre", "voador",
    "psiquico", "inseto", "pedra", "fantasma", "dragao", "sombrio", "metal", "fada", "cosmico", "sonoro",
)


def _skins_liberadas_padrao() -> list[str]:
    regras = carregar_regras_player()
    minimo = int(regras.get("SkinInicialMin", 1) or 1)
    maximo = int(regras.get("SkinInicialMax", 12) or 12)
    minimo, maximo = sorted((max(1, minimo), max(1, maximo)))
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
    minimo = int(regras.get("SkinInicialMin", 1) or 1)
    maximo = int(regras.get("SkinInicialMax", 12) or 12)
    minimo, maximo = sorted((max(1, minimo), max(1, maximo)))
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
    dados["nivel_mochila"] = int(dados.get("nivel_mochila", regras.get("NivelMochila", 1)))
    dados["limite_slots_inventario"] = int(max(1, dados.get("limite_slots_inventario", regras.get("LimiteSlotsInventario", 32))))
    dados["limite_pokemons"] = int(max(1, dados.get("limite_pokemons", regras.get("LimitePokemons", 64))))
    dados["limite_times_pokemon"] = int(max(1, dados.get("limite_times_pokemon", regras.get("LimiteTimesPokemon", 6))))
    dados["batalhas_pvp_vencidas"] = int(dados.get("batalhas_pvp_vencidas", 0))
    dados["batalhas_bot_vencidas"] = int(dados.get("batalhas_bot_vencidas", 0))
    dados["baus_abertos"] = int(max(0, dados.get("baus_abertos", 0)))
    dados["metros_andados"] = float(max(0.0, dados.get("metros_andados", 0.0)))
    dados["tempo_jogo_segundos"] = float(max(0.0, dados.get("tempo_jogo_segundos", 0.0)))
    dados["dinheiro"] = int(dados.get("dinheiro", regras.get("Dinheiro", 20)))
    dados["insignias"] = list(dados.get("insignias", []))
    dados["maestria"] = int(dados.get("maestria", regras.get("Maestria", 0)))
    dados["skins_liberadas"] = _normalizar_skins_liberadas(dados.get("skins_liberadas"))
    dados["habilidades_aprendidas"] = list(dados.get("habilidades_aprendidas", []))
    for tipo in _TIPOS_ESTADIO_RESPEITO:
        chave = f"respeito_estadio_{tipo}"
        dados[chave] = int(max(0, min(4, dados.get(chave, 0))))

    stamina_max = max(1.0, float(dados.get("stamina_max", regras.get("StaminaMax", 100.0))))
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
    limite_pokemons = int(max(1, inv.get("limite_pokemons", dados.get("limite_pokemons", regras.get("LimitePokemons", 64)))))
    limite_times_pokemon = int(max(1, inv.get("limite_times_pokemon", dados.get("limite_times_pokemon", regras.get("LimiteTimesPokemon", 6)))))
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
    if "Mundo" not in pos_dim_norm:
        pos_dim_norm["Mundo"] = [float(dados.get("posicao", [0.0, 0.0])[0]), float(dados.get("posicao", [0.0, 0.0])[1])]
    dados["dimensao_atual"] = dimensao_atual
    dados["posicoes_por_dimensao"] = pos_dim_norm
    return dados


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
        "limite_itens": int(max(1, base.get("limite_itens", 100))),
        "limite_slots": int(max(1, base.get("limite_slots", 32))),
        "limite_pokemons": limite_pokemons,
        "limite_times_pokemon": limite_times_pokemon,
        "slot_selecionado": int(base.get("slot_selecionado", 0)),
    }


def _mesclar_perfil_atualizacao(personagem_atual: dict, atualizacao: dict) -> dict:
    base = _normalizar_perfil(personagem_atual)
    payload = dict(atualizacao) if isinstance(atualizacao, dict) else {}

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
        "limite_slots_inventario",
        "limite_pokemons",
        "limite_times_pokemon",
        *[f"respeito_estadio_{tipo}" for tipo in _TIPOS_ESTADIO_RESPEITO],
    )
    for campo in campos_int:
        if campo in payload:
            base[campo] = int(payload.get(campo, base[campo]))
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
    from SimuladorServerJogo.Rotas.Ativador import resetar_estado_clientes

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
    resetar_estado_clientes()
    _set_geracao(progresso=100, mensagem="Mundo pronto")


def _worker_criacao_mundo():
    try:
        _criar_novo_mundo_sync()
        with _LOCK:
            _ESTADO["mundo_existente"] = True
            _set_geracao(em_andamento=False, progresso=100, mensagem="Mundo pronto", erro="", operacao="nenhuma")
    except Exception as exc:
        with _LOCK:
            _ESTADO_MUNDO.clear()
            _ESTADO_MUNDO.update(_estado_mundo_vazio())
            _ESTADO["mundo_existente"] = False
            _set_geracao(em_andamento=False, progresso=0, mensagem="Falha ao criar mundo", erro=str(exc), operacao="nenhuma")


def _apagar_mundo():
    global _ESTADO_MUNDO
    from SimuladorServerJogo.Rotas.Ativador import resetar_estado_clientes
    limpar_arquivos_mundo()
    _ESTADO_MUNDO = _estado_mundo_vazio()
    _ESTADO["personagens"].clear()
    _ESTADO["jogadores_com_personagem"].clear()
    BANCO_DADOS.recarregar_mundo(_ESTADO_MUNDO, limpar_objetos=True)
    resetar_estado_clientes()




def _worker_apagar_mundo():
    from SimuladorServerJogo.Controle.Cerebros.CerebroCentral import CEREBRO
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
            _set_geracao(em_andamento=False, progresso=0, mensagem="Falha ao apagar mundo", erro=str(exc), operacao="nenhuma")
            CEREBRO.desligar_servidor()

def _sync_personagens_mundo():
    if not _ESTADO_MUNDO.get("meta"):
        return
    _ESTADO_MUNDO["players"] = _ESTADO["personagens"]
    _ESTADO_MUNDO.setdefault("npcs_vendedores", {})
    _ESTADO_MUNDO["tempo_mundo"] = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))
    _ESTADO_MUNDO["estruturas_naturais_tocadas"] = BANCO_DADOS.exportar_estruturas_tocadas()
    salvar_estado_mundo(_ESTADO_MUNDO)


def _persistir_personagens(force: bool = False) -> None:
    global _ultimo_persistencia_ts
    agora = time.monotonic()
    if not force and (agora - _ultimo_persistencia_ts) < _INTERVALO_PERSISTENCIA_SEGUNDOS:
        return
    _sync_personagens_mundo()
    _ultimo_persistencia_ts = agora




def obter_regras_cliente() -> dict:
    regras_player = carregar_regras_player()
    regras_mundo = carregar_regras_mundo()
    return {
        "player": dict(regras_player),
        "mundo": {"chunk_tiles": int(regras_mundo.get("ChunkTiles", 10))},
    }

def chave_seguranca():
    return _CHAVE_SEGURANCA


def snapshot_estado():
    with _LOCK:
        return {
            "nome": _ESTADO["nome"],
            "ip": _ESTADO["ip"],
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
    with _LOCK:
        tempo = _normalizar_tempo_mundo(_ESTADO_MUNDO.get("tempo_mundo"))
        _ESTADO_MUNDO["tempo_mundo"] = tempo
        return dict(tempo)


def atualizar_tempo_mundo_estado(tempo: dict, force: bool = False) -> None:
    with _LOCK:
        _ESTADO_MUNDO["tempo_mundo"] = _normalizar_tempo_mundo(tempo)
        _persistir_personagens(force=force)


def carregar_npcs_vendedores_estado() -> dict:
    with _LOCK:
        bruto = _ESTADO_MUNDO.get("npcs_vendedores", {}) if isinstance(_ESTADO_MUNDO, dict) else {}
        return {str(k): dict(v) for k, v in bruto.items()} if isinstance(bruto, dict) else {}


def salvar_npcs_vendedores_estado(npcs: dict, force: bool = False) -> None:
    with _LOCK:
        _ESTADO_MUNDO["npcs_vendedores"] = {str(k): dict(v) for k, v in (npcs or {}).items() if isinstance(v, dict)}
        _persistir_personagens(force=force)


def definir_ligado(ativo):
    from SimuladorServerJogo.Controle.Cerebros.CerebroCentral import CEREBRO
    with _LOCK:
        desejado = bool(ativo)
        if desejado and not _ESTADO["mundo_existente"]:
            _ESTADO["ligado"] = False
            return False, "Não é possível ligar o servidor sem mundo"
        _ESTADO["ligado"] = desejado
        TIQUE_SERVIDOR.definir_ativo(_ESTADO["ligado"])
        if not _ESTADO["ligado"]:
            CEREBRO.desligar_servidor()
            TIQUE_SERVIDOR.parar()
        return True, "Estado do servidor atualizado"


def definir_mundo_existente(ativo):
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




def atualizar_inventario_personagem(usuario, inventario):
    if not usuario or not isinstance(inventario, dict):
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return
        personagem["inventario"] = _normalizar_inventario(inventario)
        _persistir_personagens()


def atualizar_perfil_personagem(usuario, perfil):
    if not usuario or not isinstance(perfil, dict):
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return
        personagem.update(_mesclar_perfil_atualizacao(personagem, perfil))
        _persistir_personagens()
