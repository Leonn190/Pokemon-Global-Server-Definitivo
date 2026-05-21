import copy
import random
import re
import unicodedata
from pathlib import Path

from Servidor.Gerais.Geradores.GeradorMundo import obter_posicao_spawn
from Servidor.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado
from Servidor.Gerais.LoaderRegras import carregar_regras_dungeons, carregar_regras_player
from Servidor.Mundo.BancoDados import BANCO_DADOS
from Servidor.Mundo.PacotesTick import PACOTES_TICK

_NIVEL_MAXIMO_JOGADOR = 100
_TIPOS_ESTADIO_RESPEITO = (
    "normal", "fogo", "agua", "planta", "eletrico", "gelo", "lutador", "venenoso", "terrestre", "voador",
    "psiquico", "inseto", "pedra", "fantasma", "dragao", "sombrio", "metal", "fada", "cosmico", "sonoro", "geral",
)
_CATEGORIAS_CONHECIMENTO = ("Efeitos", "Ataques", "Pokemons", "Itens", "Musicas")


class _CtxDict(dict):
    def __init__(self, getter):
        super().__init__()
        self._getter = getter

    def _dados(self):
        return self._getter()

    def __getitem__(self, chave):
        return self._dados()[chave]

    def __setitem__(self, chave, valor):
        self._dados()[chave] = valor

    def __delitem__(self, chave):
        del self._dados()[chave]

    def __iter__(self):
        return iter(self._dados())

    def __len__(self):
        return len(self._dados())

    def __contains__(self, chave):
        return chave in self._dados()

    def __bool__(self):
        return bool(self._dados())

    def get(self, *args, **kwargs):
        return self._dados().get(*args, **kwargs)

    def setdefault(self, *args, **kwargs):
        return self._dados().setdefault(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self._dados().update(*args, **kwargs)

    def clear(self):
        return self._dados().clear()

    def items(self):
        return self._dados().items()

    def values(self):
        return self._dados().values()

    def keys(self):
        return self._dados().keys()

    def pop(self, *args, **kwargs):
        return self._dados().pop(*args, **kwargs)


class _CtxLock:
    def __enter__(self):
        return _CTX.lock().__enter__()

    def __exit__(self, exc_type, exc, tb):
        return _CTX.lock().__exit__(exc_type, exc, tb)


_CTX = None
_ESTADO = _CtxDict(lambda: _CTX.estado())
_ESTADO_MUNDO = _CtxDict(lambda: _CTX.estado_mundo())
_ESTADO_GERACAO = _CtxDict(lambda: _CTX.estado_geracao())
_LOCK = _CtxLock()


def _valor_regra(regras: dict, chave: str, padrao):
    return _CTX.valor_regra(regras, chave, padrao)


def _bool_cfg(valor) -> bool:
    return _CTX.bool_cfg(valor)


def _config_mundo_padrao() -> dict:
    return _CTX.config_mundo_padrao()


def normalizar_config_mundo(config) -> dict:
    return _CTX.normalizar_config_mundo(config)


def _tempo_mundo_padrao() -> dict:
    return _CTX.tempo_mundo_padrao()


def _normalizar_tempo_mundo(tempo: dict | None) -> dict:
    return _CTX.normalizar_tempo_mundo(tempo)


def _estado_mundo_vazio():
    return _CTX.estado_mundo_vazio()


def _garantir_estado_ativo() -> None:
    return _CTX.garantir_estado_ativo()


def _salvar_json_servidor_ativo_locked() -> None:
    return _CTX.salvar_json_servidor_ativo_locked()


def _recarregar_cerebro_mundo() -> None:
    return _CTX.recarregar_cerebro_mundo()


def _agendar_persistencia_locked(force: bool = False, secoes: set[str] | None = None) -> None:
    return _CTX.agendar_persistencia_locked(force=force, secoes=secoes)


def _set_geracao(em_andamento=None, progresso=None, mensagem=None, erro=None, operacao=None):
    return _CTX.set_geracao(em_andamento=em_andamento, progresso=progresso, mensagem=mensagem, erro=erro, operacao=operacao)


def _clamp_posicao(posicao):
    return _CTX.clamp_posicao(posicao)

def _normalizar_exploracao_chunks(valor: dict | None) -> dict:
    return _CTX.normalizar_exploracao_chunks(valor)


def _fingerprint_mundo_atual() -> str:
    return _CTX.fingerprint_mundo_atual()


def _limites_mundo_atuais() -> tuple[float, float]:
    return _CTX.limites_mundo_atuais()


def _recarregar_mundo():
    return _CTX.recarregar_mundo()


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


def _normalizar_lista_ids(valor) -> list[str]:
    if isinstance(valor, dict):
        bruto = list(valor.keys())
    elif isinstance(valor, (list, tuple, set)):
        bruto = list(valor)
    elif valor in (None, ""):
        bruto = []
    else:
        bruto = [valor]
    saida: list[str] = []
    vistos: set[str] = set()
    for item in bruto:
        if item is None:
            continue
        texto = str(item).strip()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        saida.append(texto)
    return saida


def _normalizar_dict_lista_ids(valor) -> dict[str, list[str]]:
    if not isinstance(valor, dict):
        return {}
    saida: dict[str, list[str]] = {}
    for chave, itens in valor.items():
        dungeon_id = str(chave or "").strip()
        if not dungeon_id:
            continue
        lista = _normalizar_lista_ids(itens)
        if lista:
            saida[dungeon_id] = lista
    return saida


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
    dados["insignias"] = _normalizar_lista_ids(dados.get("insignias", dados.get("Insignias")))
    dados["medalhoes"] = _normalizar_lista_ids(dados.get("medalhoes", dados.get("Medalhoes")))
    dados["bosses_dungeon_derrotados"] = _normalizar_dict_lista_ids(dados.get("bosses_dungeon_derrotados", dados.get("BossesDungeonDerrotados")))
    dados["dungeons_concluidas"] = _normalizar_lista_ids(dados.get("dungeons_concluidas", dados.get("DungeonsConcluidas")))
    dados["dungeons_terminadas"] = max(
        int(dados.get("dungeons_terminadas", dados.get("DungeonsTerminadas", 0)) or 0),
        len(dados["dungeons_concluidas"]),
    )
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

    defaults_int = {
        "coracoes_dungeon_max": 3,
        "bonus_limite_frutas_captura": 0,
        "renda_passiva_xp_taxa": 0,
        "renda_passiva_xp_acumulado": 0,
        "bonus_raio_exploracao_chunks": 0,
        "invulnerabilidade_padrao_ticks": int(_valor_regra(regras, "InvulnerabilidadePadraoTicks", 90)),
        "bonus_invulnerabilidade_dungeon_segundos": 0,
        "chave_inicial_dungeon_nova": 0,
        "capacidade_mochila": 100,
        "nivel_acumulador": 0,
    }
    for campo, padrao in defaults_int.items():
        dados[campo] = int(max(0, dados.get(campo, dados.get("".join(p.capitalize() for p in campo.split("_")), padrao)) or 0))
    if "invulnerabilidade_padrao_ticks" not in personagem and "InvulnerabilidadePadraoTicks" not in personagem:
        bonus = int(dados.get("bonus_invulnerabilidade_dungeon_segundos", 0) or 0)
        if bonus > 0:
            dados["invulnerabilidade_padrao_ticks"] = int(_valor_regra(regras, "InvulnerabilidadePadraoTicks", 90)) + bonus * int(_valor_regra(regras, "InvulnerabilidadeTicksPorSegundo", 30))

    defaults_float = {
        "multiplicador_penalidade_agua_rasa": 1.0,
        "multiplicador_penalidade_agua_funda": 1.0,
        "energia_inicial_pokemon_percent": 0.50,
        "multiplicador_alcance_projetil": 1.0,
        "multiplicador_xp_recebido": 1.0,
        "desconto_lojas_percent": 0.0,
        "multiplicador_velocidade_projetil": 1.0,
    }
    for campo, padrao in defaults_float.items():
        dados[campo] = float(dados.get(campo, dados.get("".join(p.capitalize() for p in campo.split("_")), padrao)) or padrao)

    defaults_bool = {
        "visao_expandida_mundo": False,
        "rastreador_pokemons": False,
        "rastreador_baus": False,
        "teleportador_ativo": False,
        "mochila_sem_limite": False,
    }
    for campo, padrao in defaults_bool.items():
        dados[campo] = _bool_cfg(dados.get(campo, dados.get("".join(p.capitalize() for p in campo.split("_")), padrao)))

    inv = dados.get("inventario") if isinstance(dados.get("inventario"), dict) else {}
    limite_pokemons = int(inv.get("limite_pokemons", dados.get("limite_pokemons", _valor_regra(regras, "LimitePokemons", 64))))
    limite_times_pokemon = int(inv.get("limite_times_pokemon", dados.get("limite_times_pokemon", _valor_regra(regras, "LimiteTimesPokemon", 6))))
    pokemons = list(inv.get("pokemons", []))[:limite_pokemons]
    times_pokemon = list(inv.get("times_pokemon", []))
    dados["inventario"] = {
        "itens": list(inv.get("itens", [])),
        "pokemons": pokemons,
        "times_pokemon": times_pokemon,
        "limite_itens": 0 if bool(dados.get("mochila_sem_limite", False)) else int(max(1, inv.get("limite_itens", dados.get("capacidade_mochila", 100)) or dados.get("capacidade_mochila", 100))),
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
        "limite_itens": 0 if int(base.get("limite_itens", 100) or 0) <= 0 else int(max(1, base.get("limite_itens", 100))),
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
        "dungeons_terminadas",
        "dinheiro",
        "maestria",
        "limite_conhecimento",
        "limite_slots_inventario",
        "limite_pokemons",
        "limite_times_pokemon",
        "coracoes_dungeon_max",
        "bonus_limite_frutas_captura",
        "renda_passiva_xp_taxa",
        "renda_passiva_xp_acumulado",
        "bonus_raio_exploracao_chunks",
        "invulnerabilidade_padrao_ticks",
        "bonus_invulnerabilidade_dungeon_segundos",
        "chave_inicial_dungeon_nova",
        "capacidade_mochila",
        "nivel_acumulador",
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

    if "insignias" in payload or "Insignias" in payload:
        atuais = _normalizar_lista_ids(base.get("insignias", []))
        vistos = set(atuais)
        for item in _normalizar_lista_ids(payload.get("insignias", payload.get("Insignias"))):
            if item not in vistos:
                atuais.append(item)
                vistos.add(item)
        base["insignias"] = atuais
    if "medalhoes" in payload or "Medalhoes" in payload:
        atuais = _normalizar_lista_ids(base.get("medalhoes", []))
        vistos = set(atuais)
        for item in _normalizar_lista_ids(payload.get("medalhoes", payload.get("Medalhoes"))):
            if item not in vistos:
                atuais.append(item)
                vistos.add(item)
        base["medalhoes"] = atuais
    if "bosses_dungeon_derrotados" in payload or "BossesDungeonDerrotados" in payload:
        bosses = _normalizar_dict_lista_ids(base.get("bosses_dungeon_derrotados", {}))
        for dungeon_id, lista in _normalizar_dict_lista_ids(payload.get("bosses_dungeon_derrotados", payload.get("BossesDungeonDerrotados"))).items():
            atuais = bosses.setdefault(dungeon_id, [])
            vistos = set(atuais)
            for item in lista:
                if item not in vistos:
                    atuais.append(item)
                    vistos.add(item)
        base["bosses_dungeon_derrotados"] = bosses
    if "dungeons_concluidas" in payload or "DungeonsConcluidas" in payload:
        atuais = _normalizar_lista_ids(base.get("dungeons_concluidas", []))
        vistos = set(atuais)
        for item in _normalizar_lista_ids(payload.get("dungeons_concluidas", payload.get("DungeonsConcluidas"))):
            if item not in vistos:
                atuais.append(item)
                vistos.add(item)
        base["dungeons_concluidas"] = atuais
        base["dungeons_terminadas"] = max(int(base.get("dungeons_terminadas", 0) or 0), len(base["dungeons_concluidas"]))
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
    for campo in (
        "velocidade_base_tiles",
        "bonus_velocidade_corrida_min",
        "bonus_velocidade_corrida_max",
        "tempo_aceleracao_corrida",
        "tempo_desaceleracao_corrida",
        "regeneracao_stamina_parado",
        "regeneracao_stamina_andando",
        "custo_stamina_agua_funda",
        "multiplicador_penalidade_agua_rasa",
        "multiplicador_penalidade_agua_funda",
        "energia_inicial_pokemon_percent",
        "multiplicador_alcance_projetil",
        "multiplicador_xp_recebido",
        "desconto_lojas_percent",
        "multiplicador_velocidade_projetil",
    ):
        if campo in payload:
            base[campo] = float(payload.get(campo, base.get(campo, 0.0)))
    for campo in ("visao_expandida_mundo", "rastreador_pokemons", "rastreador_baus", "teleportador_ativo", "mochila_sem_limite"):
        if campo in payload:
            base[campo] = _bool_cfg(payload.get(campo))
    base["insignias"] = _normalizar_lista_ids(base.get("insignias", []))
    base["medalhoes"] = _normalizar_lista_ids(base.get("medalhoes", []))
    base["bosses_dungeon_derrotados"] = _normalizar_dict_lista_ids(base.get("bosses_dungeon_derrotados", {}))
    base["dungeons_concluidas"] = _normalizar_lista_ids(base.get("dungeons_concluidas", []))
    base["dungeons_terminadas"] = max(int(base.get("dungeons_terminadas", 0) or 0), len(base["dungeons_concluidas"]))
    _normalizar_progresso_xp(base)
    return base


def _sync_personagens_mundo():
    _agendar_persistencia_locked(force=True, secoes={"players"})


def _persistir_personagens(force: bool = False) -> None:
    _agendar_persistencia_locked(force=force, secoes={"players"})


def _slug_id(valor) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return "".join(ch if ch.isalnum() else "_" for ch in sem_acento).strip("_")


def _adicionar_unico(lista: list[str], valor: str) -> bool:
    texto = str(valor or "").strip()
    if not texto or texto in lista:
        return False
    lista.append(texto)
    return True


def _sincronizar_perfil_player_ativo_locked(usuario: str, perfil: dict) -> None:
    from Servidor.Mundo.ObjetosMundoServer import AtorServer

    obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(usuario)) or 0)
    if obj_id <= 0:
        return
    obj = BANCO_DADOS.obter_objeto(obj_id)
    if not isinstance(obj, AtorServer) or not isinstance(getattr(obj, "estado_extra", None), dict):
        return
    obj.estado_extra["perfil"] = copy.deepcopy(perfil)
    BANCO_DADOS.atualizar_objeto(int(obj.Id), {"estado": obj.estado_extra, "perfil": perfil})


def _player_venceu_partida(partida) -> bool:
    lado = int(getattr(partida, "lado_jogador", 50) or 50)
    vencedor = getattr(partida, "vencedor", None)
    if isinstance(vencedor, (list, tuple, set)):
        for v in vencedor:
            try:
                if int(v) == lado:
                    return True
            except (TypeError, ValueError):
                continue
        return False
    try:
        return int(vencedor) == lado
    except (TypeError, ValueError):
        return False


def registrar_recompensas_batalha_finalizada(partida) -> bool:
    if partida is None or not _player_venceu_partida(partida):
        return False
    client_id = str(getattr(partida, "client_id", "") or "").strip()
    npc_ctx = getattr(partida, "npc_contexto", {}) if isinstance(getattr(partida, "npc_contexto", {}), dict) else {}
    if not client_id or str(npc_ctx.get("npc_cargo") or "").strip().lower() != "lider":
        return False
    try:
        batalha_numero = int(npc_ctx.get("batalha_numero", 1) or 1)
    except (TypeError, ValueError):
        batalha_numero = 1
    if batalha_numero != 2:
        return False
    npc_id = int(npc_ctx.get("npc_id", 0) or 0)
    npc_obj = BANCO_DADOS.obter_objeto(npc_id) if npc_id > 0 else None
    estado_npc = getattr(npc_obj, "estado_extra", {}) if npc_obj is not None and isinstance(getattr(npc_obj, "estado_extra", {}), dict) else {}
    if str(estado_npc.get("cargo") or "").strip().lower() != "lider":
        return False
    tipo_estadio = _slug_id(estado_npc.get("estadio_tipo") or npc_ctx.get("npc_estadio"))
    if not tipo_estadio:
        return False
    with _LOCK:
        personagem = _ESTADO["personagens"].get(client_id)
        if not isinstance(personagem, dict):
            return False
        dados = _normalizar_perfil(personagem)
        if not _adicionar_unico(dados["insignias"], tipo_estadio):
            return False
        _ESTADO["personagens"][client_id] = dados
        _sincronizar_perfil_player_ativo_locked(client_id, dados)
        _persistir_personagens(force=True)
    return True


def registrar_boss_dungeon_derrotado(client_id: str, dungeon_id: str, boss_id: str, bosses_dungeon, medalhao_id: str | None = None) -> bool:
    usuario = str(client_id or "").strip()
    dungeon = str(dungeon_id or "").strip()
    boss = str(boss_id or "").strip()
    bosses = _normalizar_lista_ids(bosses_dungeon)
    if not usuario or not dungeon or not boss or not bosses:
        return False
    medalhao = str(medalhao_id or dungeon).strip()
    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if not isinstance(personagem, dict):
            return False
        dados = _normalizar_perfil(personagem)
        mudou = False
        derrotados = dados["bosses_dungeon_derrotados"].setdefault(dungeon, [])
        if _adicionar_unico(derrotados, boss):
            mudou = True
        if set(bosses).issubset(set(derrotados)):
            if _adicionar_unico(dados["dungeons_concluidas"], dungeon):
                mudou = True
            novo_total = max(int(dados.get("dungeons_terminadas", 0) or 0), len(dados["dungeons_concluidas"]))
            if novo_total != int(dados.get("dungeons_terminadas", 0) or 0):
                dados["dungeons_terminadas"] = novo_total
                mudou = True
            if _adicionar_unico(dados["medalhoes"], medalhao):
                mudou = True
        if not mudou:
            return False
        _ESTADO["personagens"][usuario] = dados
        _sincronizar_perfil_player_ativo_locked(usuario, dados)
        _persistir_personagens(force=True)
    return True


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
    perfil = estado.get("perfil") if isinstance(estado.get("perfil"), dict) else {}
    coracoes_padrao = int(perfil.get("coracoes_dungeon_max", regras.get("coracoes_maximos", regras.get("coracoes_iniciais", 3))) or 3)
    coracoes_max = max(coracoes_padrao, int(vida.get("coracoes_max", coracoes_padrao) or coracoes_padrao))
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


def aplicar_invulnerabilidade_player(player, ticks: int | None = None, motivo: str = "") -> bool:
    if player is None or not isinstance(getattr(player, "estado_extra", None), dict):
        return False
    perfil = player.estado_extra.get("perfil") if isinstance(player.estado_extra.get("perfil"), dict) else {}
    if ticks is None or int(ticks or 0) <= 0:
        regras = carregar_regras_player()
        ticks = perfil.get("invulnerabilidade_padrao_ticks", perfil.get("InvulnerabilidadePadraoTicks", _valor_regra(regras, "InvulnerabilidadePadraoTicks", 90)))
    total_ticks = max(1, int(ticks or 90))
    ate = _tick_servidor_atual() + total_ticks
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
    aplicar_invulnerabilidade_player(player, None, motivo)
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
    aplicar_invulnerabilidade_player(player, None, str(motivo or "respawn"))
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


class EstadoServidorPersonagens:
    def __init__(self, ctx):
        global _CTX
        _CTX = ctx

    def _calcular_xp_alvo_por_nivel(self, *args, **kwargs):
        return _calcular_xp_alvo_por_nivel(*args, **kwargs)

    def _normalizar_progresso_xp(self, *args, **kwargs):
        return _normalizar_progresso_xp(*args, **kwargs)

    def _normalizar_conhecimento(self, *args, **kwargs):
        return _normalizar_conhecimento(*args, **kwargs)

    def _normalizar_lista_ids(self, *args, **kwargs):
        return _normalizar_lista_ids(*args, **kwargs)

    def _normalizar_dict_lista_ids(self, *args, **kwargs):
        return _normalizar_dict_lista_ids(*args, **kwargs)

    def _skins_liberadas_padrao(self, *args, **kwargs):
        return _skins_liberadas_padrao(*args, **kwargs)

    def _normalizar_skins_liberadas(self, *args, **kwargs):
        return _normalizar_skins_liberadas(*args, **kwargs)

    def _contar_recursos_miticos_inventario(self, *args, **kwargs):
        return _contar_recursos_miticos_inventario(*args, **kwargs)

    def _normalizar_perfil(self, *args, **kwargs):
        return _normalizar_perfil(*args, **kwargs)

    def _normalizar_inventario(self, *args, **kwargs):
        return _normalizar_inventario(*args, **kwargs)

    def _inventario_tem_conteudo(self, *args, **kwargs):
        return _inventario_tem_conteudo(*args, **kwargs)

    def _mesclar_perfil_atualizacao(self, *args, **kwargs):
        return _mesclar_perfil_atualizacao(*args, **kwargs)

    def _sync_personagens_mundo(self, *args, **kwargs):
        return _sync_personagens_mundo(*args, **kwargs)

    def _persistir_personagens(self, *args, **kwargs):
        return _persistir_personagens(*args, **kwargs)

    def _slug_id(self, *args, **kwargs):
        return _slug_id(*args, **kwargs)

    def _adicionar_unico(self, *args, **kwargs):
        return _adicionar_unico(*args, **kwargs)

    def _sincronizar_perfil_player_ativo_locked(self, *args, **kwargs):
        return _sincronizar_perfil_player_ativo_locked(*args, **kwargs)

    def _player_venceu_partida(self, *args, **kwargs):
        return _player_venceu_partida(*args, **kwargs)

    def registrar_recompensas_batalha_finalizada(self, *args, **kwargs):
        return registrar_recompensas_batalha_finalizada(*args, **kwargs)

    def registrar_boss_dungeon_derrotado(self, *args, **kwargs):
        return registrar_boss_dungeon_derrotado(*args, **kwargs)

    def adicionar_personagem(self, *args, **kwargs):
        return adicionar_personagem(*args, **kwargs)

    def obter_personagem_para_entrada(self, *args, **kwargs):
        return obter_personagem_para_entrada(*args, **kwargs)

    def atualizar_posicao_personagem(self, *args, **kwargs):
        return atualizar_posicao_personagem(*args, **kwargs)

    def _posicao_mundo_valida(self, *args, **kwargs):
        return _posicao_mundo_valida(*args, **kwargs)

    def _tile_mundo_seguro(self, *args, **kwargs):
        return _tile_mundo_seguro(*args, **kwargs)

    def _tick_servidor_atual(self, *args, **kwargs):
        return _tick_servidor_atual(*args, **kwargs)

    def _vida_player(self, *args, **kwargs):
        return _vida_player(*args, **kwargs)

    def player_invulneravel(self, *args, **kwargs):
        return player_invulneravel(*args, **kwargs)

    def aplicar_invulnerabilidade_player(self, *args, **kwargs):
        return aplicar_invulnerabilidade_player(*args, **kwargs)

    def matar_player(self, *args, **kwargs):
        return matar_player(*args, **kwargs)

    def aplicar_dano_player(self, *args, **kwargs):
        return aplicar_dano_player(*args, **kwargs)

    def registrar_checkpoint_mundo_seguro(self, *args, **kwargs):
        return registrar_checkpoint_mundo_seguro(*args, **kwargs)

    def registrar_checkpoint_mundo_chunk_seguro(self, *args, **kwargs):
        return registrar_checkpoint_mundo_chunk_seguro(*args, **kwargs)

    def _posicao_segura_no_chunk(self, *args, **kwargs):
        return _posicao_segura_no_chunk(*args, **kwargs)

    def _posicao_segura_perto_spawn(self, *args, **kwargs):
        return _posicao_segura_perto_spawn(*args, **kwargs)

    def resolver_respawn_mundo_seguro(self, *args, **kwargs):
        return resolver_respawn_mundo_seguro(*args, **kwargs)

    def aplicar_respawn_mundo(self, *args, **kwargs):
        return aplicar_respawn_mundo(*args, **kwargs)

    def _restaurar_inventario_player_persistido(self, *args, **kwargs):
        return _restaurar_inventario_player_persistido(*args, **kwargs)

    def atualizar_inventario_personagem(self, *args, **kwargs):
        return atualizar_inventario_personagem(*args, **kwargs)

    def atualizar_perfil_personagem(self, *args, **kwargs):
        return atualizar_perfil_personagem(*args, **kwargs)
