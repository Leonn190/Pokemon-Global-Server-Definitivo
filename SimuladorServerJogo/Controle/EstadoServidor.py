import threading
import time

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



def _estado_mundo_vazio():
    return {
        "meta": {},
        "grid": [],
        "grid_biomas": [],
        "grid_estruturas_naturais": [],
        "players": {},
        "spawn": [0.0, 0.0],
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
    dados["nivel_mochila"] = int(dados.get("nivel_mochila", regras.get("NivelMochila", 1)))
    dados["limite_slots_inventario"] = int(max(1, dados.get("limite_slots_inventario", regras.get("LimiteSlotsInventario", 32))))
    dados["limite_pokemons"] = int(max(1, dados.get("limite_pokemons", regras.get("LimitePokemons", 64))))
    dados["limite_times_pokemon"] = int(max(1, dados.get("limite_times_pokemon", regras.get("LimiteTimesPokemon", 6))))
    dados["batalhas_pvp_vencidas"] = int(dados.get("batalhas_pvp_vencidas", 0))
    dados["batalhas_bot_vencidas"] = int(dados.get("batalhas_bot_vencidas", 0))
    dados["ouro"] = int(dados.get("ouro", regras.get("Ouro", 0)))
    dados["passos_caminhados"] = int(dados.get("passos_caminhados", 0))
    dados["insignias"] = list(dados.get("insignias", []))
    dados["maestria"] = int(dados.get("maestria", regras.get("Maestria", 0)))
    dados["skins_liberadas"] = list(dados.get("skins_liberadas", []))

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
        "nivel_mochila",
        "batalhas_pvp_vencidas",
        "batalhas_bot_vencidas",
        "ouro",
        "passos_caminhados",
        "maestria",
        "limite_slots_inventario",
        "limite_pokemons",
        "limite_times_pokemon",
    )
    for campo in campos_int:
        if campo in payload:
            base[campo] = int(payload.get(campo, base[campo]))

    if "insignias" in payload:
        base["insignias"] = list(payload.get("insignias", []))
    if "skins_liberadas" in payload:
        base["skins_liberadas"] = list(payload.get("skins_liberadas", []))

    stamina_max = float(base.get("stamina_max", 100.0))
    if "stamina_max" in payload:
        stamina_max = max(1.0, float(payload.get("stamina_max", stamina_max)))

    stamina = float(base.get("stamina", stamina_max))
    if "stamina" in payload:
        stamina = float(payload.get("stamina", stamina))

    base["stamina_max"] = stamina_max
    base["stamina"] = max(0.0, min(stamina_max, stamina))
    return base


def _recarregar_mundo():
    global _ESTADO_MUNDO
    _ESTADO_MUNDO = carregar_estado_mundo()


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
            _set_geracao(em_andamento=True, progresso=1, mensagem="Apagando mundo", erro="", operacao="remocao")
        with _LOCK:
            _set_geracao(progresso=55, mensagem="Removendo arquivos do mundo")
        _apagar_mundo()
        with _LOCK:
            _ESTADO["mundo_existente"] = False
            _ESTADO["ligado"] = False
            _set_geracao(em_andamento=False, progresso=100, mensagem="Finalizando remoção", erro="", operacao="nenhuma")
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
        }


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

        _ESTADO["personagens"][usuario] = _normalizar_perfil(
            {
                "nome": usuario,
                "skin": skin,
                "pokemon_inicial": pokemon_inicial,
                "posicao": [spawn[0], spawn[1]],
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


def atualizar_posicao_personagem(usuario, posicao):
    if not usuario:
        return

    with _LOCK:
        personagem = _ESTADO["personagens"].get(usuario)
        if personagem is None:
            return

        x, y = _clamp_posicao(posicao)
        personagem["posicao"] = [x, y]
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
