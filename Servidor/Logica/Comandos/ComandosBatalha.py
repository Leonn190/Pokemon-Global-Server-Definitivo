from __future__ import annotations

import random

from Servidor.Batalha.GerenciadorPartidas import GERENCIADOR_PARTIDAS


_TIPOS_DANO = {"N": "normal", "E": "especial", "V": "verdadeiro"}


def _partida(meta):
    batalha_id = str((meta or {}).get("batalha_id") or "").strip()
    if not batalha_id:
        return None, "batalha_id obrigatório para comandos de batalha"
    partida = GERENCIADOR_PARTIDAS.obter_partida(batalha_id)
    if partida is None:
        return None, f"Partida não encontrada: {batalha_id}"
    return partida, ""


def _resultado(partida, mensagem, log_texto=None):
    resultado_log = partida.gerar_resultado_diff(partida.rodada_atual)
    atualizacao = {
        "resultado": resultado_log.get("resultado", {}),
        "estado_batalha": getattr(partida, "estado_partida", ""),
        "rodada_atual": int(getattr(partida, "rodada_atual", 1) or 1),
    }
    if log_texto:
        atualizacao["log"] = {"rodada": int(getattr(partida, "rodada_atual", 1) or 1), "historico": [{"tipo": "terminal", "texto": str(log_texto)}]}
    return {"feedback": mensagem, "batalha_atualizacao": atualizacao}


def _preparar_mutacao(partida, motivo):
    if hasattr(partida, "registrar_snapshot_reversao"):
        partida.registrar_snapshot_reversao(motivo)
    if getattr(partida, "construtor_log", None) is not None:
        partida.construtor_log.iniciar_log_rodada(partida.rodada_atual)


def _area_id(raw):
    s = str(raw or "").strip().upper()
    if len(s) >= 2 and s[0] in {"A", "I"} and s[1:].isdigit():
        return s
    return ""


def _pokemon_area(partida, raw):
    area = _area_id(raw)
    if not area:
        return None, f"Área inválida: {raw}"
    if not partida.area_existe(area):
        return None, f"Área inexistente: {area}"
    pokemon = partida.pokemon_na_area(area)
    if pokemon is None:
        return None, f"Não há Pokémon ativo em {area}"
    return pokemon, ""


def _pokemon_aleatorio(partida):
    vivos = [p for p in partida.pokemons_por_id.values() if p.esta_vivo() and p.ativo and not p.reserva and p.area_id]
    if not vivos:
        return None, "Não há Pokémon vivo/ativo para escolher"
    return random.choice(vivos), ""


def _finalizar_fluxo(partida):
    if hasattr(partida, "substituir_derrotados_por_reserva"):
        partida.substituir_derrotados_por_reserva()
    if hasattr(partida, "verificar_fim_batalha"):
        partida.verificar_fim_batalha()
    if getattr(partida, "finalizada", False):
        partida.estado_partida = "finalizada"


def _matar_pokemon(partida, pokemon, motivo, origem=None):
    pokemon.Morrer({"motivo": motivo, "origem_id": getattr(origem, "id_batalha", None), "origem": origem})


def comando_test(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    args = list(args or [])
    atual = bool(getattr(partida, "modo_teste", False))
    if not args:
        novo = not atual
    else:
        op = str(args[0]).strip().lower()
        if op == "status":
            return {"feedback": f"Modo teste {'ativo' if atual else 'inativo'}", "batalha_atualizacao": {"modo_teste": atual}}
        if op in {"on", "true", "1", "sim"}:
            novo = True
        elif op in {"off", "false", "0", "nao", "não"}:
            novo = False
        else:
            return "Erro no /test. Use /test, /test on, /test off ou /test status"
    partida.modo_teste = bool(novo)
    return {"feedback": f"Modo teste {'ativado' if novo else 'desativado'}", "batalha_atualizacao": {"modo_teste": bool(novo)}}


def comando_kill(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    args = list(args or [])
    if not args:
        return "Erro no /kill. Uso: /kill A1"
    pokemon, erro = _pokemon_area(partida, args[0])
    if erro:
        return erro
    _preparar_mutacao(partida, "/kill")
    _matar_pokemon(partida, pokemon, "comando_kill")
    _finalizar_fluxo(partida)
    return _resultado(partida, f"{pokemon.nome} em {args[0].upper()} foi derrotado")


def comando_heal(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    args = list(args or [])
    if not args:
        return "Erro no /heal. Uso: /heal valor [A1]"
    valor_raw = str(args[0]).strip().lower()
    alvo_raw = args[1] if len(args) > 1 else ""
    pokemon, erro = _pokemon_area(partida, alvo_raw) if alvo_raw else _pokemon_aleatorio(partida)
    if erro:
        return erro
    if valor_raw == "full":
        valor = max(0.0, pokemon.obter_atributo("Vida", 1.0) - pokemon.VidaAtual)
    else:
        try:
            valor = float(valor_raw.replace(",", "."))
        except ValueError:
            return "Erro no /heal. Valor deve ser número ou full"
    _preparar_mutacao(partida, "/heal")
    ret = pokemon.ReceberCura(valor, dados={"motivo": "comando_heal"})
    return _resultado(partida, f"{pokemon.nome} curado em {ret.get('cura', 0)}")


def comando_dmg(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    args = list(args or [])
    if not args:
        return "Erro no /dmg. Uso: /dmg valor [N|E|V] [A1]"
    try:
        valor = float(str(args[0]).replace(",", "."))
    except ValueError:
        return "Erro no /dmg. Valor inválido"
    tipo = "V"
    alvo_raw = ""
    for token in args[1:]:
        up = str(token).strip().upper()
        if up in _TIPOS_DANO:
            tipo = up
        elif _area_id(up):
            alvo_raw = up
    pokemon, erro = _pokemon_area(partida, alvo_raw) if alvo_raw else _pokemon_aleatorio(partida)
    if erro:
        return erro
    _preparar_mutacao(partida, "/dmg")
    ret = pokemon.ReceberDano(valor, dados={"tipo": _TIPOS_DANO[tipo], "categoria": _TIPOS_DANO[tipo], "ignorar_defensivos": tipo == "V", "motivo": "comando_dmg"})
    _finalizar_fluxo(partida)
    return _resultado(partida, f"{pokemon.nome} recebeu {ret.get('dano_vida', 0)} de dano ({tipo})")


def _lado_jogador(partida):
    return int(getattr(partida, "lado_jogador", 50) or 50)


def _lados_opostos(partida):
    jogador = _lado_jogador(partida)
    return [lado for lado in partida.pokemons_por_lado.keys() if int(lado) != jogador]


def _matar_lado(partida, lado_ids, motivo):
    mortos = 0
    for lado in list(lado_ids):
        for pokemon in list(partida.pokemons_por_lado.get(int(lado), []) or []):
            if pokemon.esta_vivo():
                _matar_pokemon(partida, pokemon, motivo)
                mortos += 1
    _finalizar_fluxo(partida)
    return mortos


def comando_win(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, args, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    _preparar_mutacao(partida, "/win")
    mortos = _matar_lado(partida, _lados_opostos(partida), "comando_win")
    return _resultado(partida, f"Vitória forçada. Pokémon adversários derrotados: {mortos}")


def comando_lose(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, args, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    _preparar_mutacao(partida, "/lose")
    mortos = _matar_lado(partida, [_lado_jogador(partida)], "comando_lose")
    return _resultado(partida, f"Derrota forçada. Pokémon aliados derrotados: {mortos}")


def comando_revert(autor, args, contexto=None, meta=None, catalogo=None):
    _ = (autor, args, contexto, catalogo)
    partida, erro = _partida(meta)
    if erro:
        return erro
    if not hasattr(partida, "reverter_snapshot"):
        return "Reversão indisponível nesta partida"
    snap = partida.reverter_snapshot()
    if snap is None:
        return "Nenhum turno disponível para reverter"
    return _resultado(partida, f"Turno revertido para rodada {partida.rodada_atual}")


CATALOGO_COMANDOS_BATALHA = [
    {"nome": "win", "aliases": ["vencer"], "funcao": comando_win, "contexto": "batalha", "nivel": 1, "uso": "/win", "descricao": "Força vitória matando todos os Pokémon adversários.", "argumentos": [], "exemplos": ["/win"]},
    {"nome": "lose", "aliases": ["loose", "perder"], "funcao": comando_lose, "contexto": "batalha", "nivel": 1, "uso": "/lose", "descricao": "Força derrota matando todos os Pokémon aliados.", "argumentos": [], "exemplos": ["/lose", "/loose"]},
    {"nome": "revert", "aliases": [], "funcao": comando_revert, "contexto": "batalha", "nivel": 1, "uso": "/revert", "descricao": "Restaura o snapshot anterior da batalha.", "argumentos": [], "exemplos": ["/revert"]},
    {"nome": "test", "aliases": [], "funcao": comando_test, "contexto": "batalha", "nivel": 1, "uso": "/test [on|off|status]", "descricao": "Alterna o modo teste existente da partida.", "argumentos": ["on/off/status opcionais"], "exemplos": ["/test", "/test on", "/test status"]},
    {"nome": "heal", "aliases": [], "funcao": comando_heal, "contexto": "batalha", "nivel": 1, "uso": "/heal valor [A1]", "descricao": "Cura alvo ou um Pokémon vivo aleatório.", "argumentos": ["valor: número ou full", "alvo: area_id opcional"], "exemplos": ["/heal 50 A1", "/heal full"]},
    {"nome": "dmg", "aliases": [], "funcao": comando_dmg, "contexto": "batalha", "nivel": 1, "uso": "/dmg valor [N|E|V] [A1]", "descricao": "Aplica dano normal, especial ou verdadeiro.", "argumentos": ["valor numérico", "tipo opcional: N/E/V", "alvo opcional"], "exemplos": ["/dmg 40 V I1", "/dmg 50"]},
    {"nome": "kill", "aliases": ["matar"], "funcao": comando_kill, "contexto": "batalha", "nivel": 1, "uso": "/kill A1", "descricao": "Mata o Pokémon ativo na área informada.", "argumentos": ["area_id: A1..A9 ou I1..I9"], "exemplos": ["/kill I1", "/matar a2"]},
]
