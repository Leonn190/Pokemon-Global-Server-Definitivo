from __future__ import annotations

import csv
import random
import time
from pathlib import Path

from SimuladorServerJogo.Controle.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Controle.EstadoServidor import snapshot_estado, atualizar_inventario_personagem, atualizar_posicao_personagem
from SimuladorServerJogo.Controle.ObjetosMundoServer import BauServer
from SimuladorServerJogo.Geradores.GeradorBaus import gerar_bau_server
from SimuladorServerJogo.Geradores.GeradorPokemon import gerar_pokemon_server
from SimuladorServerJogo.Rotas.Ativador import registrar_diff
from SimuladorServerJogo.Controle.CerebroCentral import CEREBRO

_RAIZ = Path(__file__).resolve().parents[2]


def _split_args(tokens):
    nomeados, livres = {}, []
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            nomeados[str(k).strip().lower()] = str(v).strip()
        else:
            livres.append(t)
    return nomeados, livres


def _estado_players():
    estado = snapshot_estado() or {}
    return estado.get("personagens", {}) if isinstance(estado.get("personagens", {}), dict) else {}


def _resolver_alvos(raw, autor, aceitar_todos=False):
    players = _estado_players()
    nomes = list(players.keys())
    if not nomes:
        return []
    alvo = (str(raw or "").strip() or "y").lower()
    if alvo == "y":
        return [autor] if autor in players else [nomes[0]]
    if alvo == "r":
        return [random.choice(nomes)]
    if aceitar_todos and alvo == "todos":
        return nomes
    for n in nomes:
        if n.lower() == alvo:
            return [n]
    return []


def _to_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _to_int(v, default=1):
    try:
        return int(v)
    except Exception:
        return int(default)


def _clamp_i(v, mn=0, mx=100):
    return max(int(mn), min(int(mx), _to_int(v, mn)))


def _registrar_update_player(usuario, payload):
    obj = BANCO_DADOS.garantir_player(usuario, str(payload.get("skin", "S1")), tuple(payload.get("posicao", [0.0, 0.0])))
    registrar_diff(
        "update",
        payload=payload,
        escopo={"centro": [float(obj.posicao[0]), float(obj.posicao[1])], "raio": 780.0},
        objeto_id=obj.Id,
        autor="server",
        categoria="player",
    )


def _payload_player(usuario):
    players = _estado_players()
    p = players.get(usuario, {}) if isinstance(players.get(usuario, {}), dict) else {}
    pos = p.get("posicao", [0.0, 0.0]) if isinstance(p.get("posicao", [0.0, 0.0]), (list, tuple)) else [0.0, 0.0]
    return {
        "tipo": "entidade_player",
        "nome": usuario,
        "skin": str(p.get("skin", "S1")),
        "posicao": [float(pos[0]), float(pos[1])],
        "perfil": {k: v for k, v in p.items() if k != "inventario"},
        "inventario": dict(p.get("inventario", {})) if isinstance(p.get("inventario"), dict) else {},
    }


def _ajustar_stats_spawn(estado, nomeados):
    if not isinstance(estado, dict):
        return
    subivs = estado.get("subivs") if isinstance(estado.get("subivs"), dict) else {}
    stats_base = estado.get("stats_base") if isinstance(estado.get("stats_base"), dict) else {}
    stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
    mapa = {"vida": "Vida", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "vel": "Vel"}

    if "iv" in nomeados:
        ivg = _clamp_i(nomeados.get("iv", 0))
        for k in list(subivs.keys()):
            subivs[k] = ivg

    for kcurto, klongo in mapa.items():
        kiv = f"iv{kcurto}"
        if kiv in nomeados:
            subivs[klongo] = _clamp_i(nomeados.get(kiv, 0))

    for kcurto, klongo in mapa.items():
        if kcurto not in nomeados:
            continue
        alvo = max(0.0, float(_to_float(nomeados.get(kcurto)) or 0.0))
        base = max(0.0001, float(stats_base.get(klongo, stats.get(klongo, 1.0))))
        subivs[klongo] = _clamp_i(round(((alvo / base) - 0.8) / 0.4 * 100.0))

    for skey, base in list(stats_base.items()):
        sv = _clamp_i(subivs.get(skey, 0))
        subivs[skey] = sv
        stats[skey] = round(float(base) * (0.8 + (sv / 100.0) * 0.4), 2)

    estado["subivs"] = subivs
    estado["stats"] = stats
    vals = [int(v) for v in subivs.values()]
    estado["iv"] = _clamp_i(round(sum(vals) / max(1, len(vals))))


def _pos_aleatoria_perto(autor):
    players = _estado_players()
    base = players.get(autor, {}) if isinstance(players.get(autor, {}), dict) else {}
    pos = base.get("posicao", [0, 0]) if isinstance(base.get("posicao", [0, 0]), (list, tuple)) else [0, 0]
    x = float(pos[0]) + random.uniform(-10, 10)
    y = float(pos[1]) + random.uniform(-10, 10)
    largura, altura = BANCO_DADOS.limites_mundo()
    return (x % max(1.0, float(largura)), y % max(1.0, float(altura)))


def _normalizar_xy(x, y):
    largura, altura = BANCO_DADOS.limites_mundo()
    return (float(x) % max(1.0, float(largura)), float(y) % max(1.0, float(altura)))


def _carregar_itens():
    itens, by_code, by_nome = [], {}, {}
    with (_RAIZ / "Dados" / "Global server - Itens.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nome = str(row.get("Nome", "")).strip()
            code = str(row.get("Code", "")).strip()
            if not nome:
                continue
            raridade_raw = str(row.get("Raridade", "")).strip()
            d = {
                "Nome": nome,
                "Descrição": str(row.get("Descrição", "")).strip(),
                "Raridade": int(raridade_raw) if raridade_raw.isdigit() else raridade_raw,
                "Estilo": str(row.get("Estilo", "")).strip(),
                "Code": code,
            }
            itens.append(d)
            if code:
                by_code[code] = d
            by_nome[nome.lower()] = d
    return itens, by_code, by_nome


def _carregar_pokemons():
    pokes, by_code, by_nome = [], {}, {}
    with (_RAIZ / "Dados" / "Global server - Pokemons.csv").open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nome = str(row.get("Nome", "")).strip()
            code = str(row.get("Code", "")).strip()
            estagio = str(row.get("Estagio", "")).strip()
            if not nome:
                continue
            d = {"Nome": nome, "Code": code, "Estagio": estagio}
            pokes.append(d)
            if code:
                by_code[code] = d
            by_nome[nome.lower()] = d
    return pokes, by_code, by_nome


_ITENS, _ITENS_CODE, _ITENS_NOME = _carregar_itens()
_POKES, _POKE_CODE, _POKE_NOME = _carregar_pokemons()


def _resolver_item(raw):
    if not raw:
        return random.choice(_ITENS) if _ITENS else None
    s = str(raw).strip()
    return _ITENS_CODE.get(s) or _ITENS_NOME.get(s.lower())


def _resolver_pokemon(raw):
    if not raw:
        return None
    s = str(raw).strip()
    return _POKE_CODE.get(s) or _POKE_NOME.get(s.lower())


def _cmd_give(autor, args):
    nomeados, livres = _split_args(args)
    alvo_raw = nomeados.get("alvo")
    if not alvo_raw and livres and (livres[0].lower() in {"y", "r", "todos"} or _resolver_alvos(livres[0], autor, True)):
        alvo_raw = livres.pop(0)
    item_raw = nomeados.get("item") or (livres.pop(0) if livres else "")
    qtd_raw = nomeados.get("qtd") or nomeados.get("quantidade") or (livres.pop(0) if livres else "1")
    alvos = _resolver_alvos(alvo_raw, autor, aceitar_todos=True)
    if not alvos:
        return "Erro no /give. Ordem base: /give alvo item quantidade"
    item = _resolver_item(item_raw) or _resolver_item("")
    if item is None:
        return "Erro no /give. Item inválido"
    item = CEREBRO._servico_inventario.normalizar_item({"Code": item.get("Code"), "Nome": item.get("Nome"), "quantidade": 1})
    qtd = max(1, _to_int(qtd_raw, 1))
    entregues = 0
    cheios = []
    for alvo in alvos:
        players = _estado_players()
        inv = dict((players.get(alvo, {}) if isinstance(players.get(alvo, {}), dict) else {}).get("inventario", {}))
        itens = list(inv.get("itens", []))
        limite_slots = int(max(1, _to_int(inv.get("limite_slots", 32), 32)))

        if len(itens) < limite_slots:
            itens.extend([None] * (limite_slots - len(itens)))
        elif len(itens) > limite_slots:
            itens = itens[:limite_slots]

        achou = False
        for it in itens:
            if not isinstance(it, dict):
                continue
            if str(it.get("Code", "")) == str(item.get("Code", "")) or str(it.get("Nome", "")).lower() == str(item.get("Nome", "")).lower():
                nova_qtd = int(max(1, _to_int(it.get("quantidade", 1), 1) + qtd))
                it.clear(); it.update(item); it["quantidade"] = nova_qtd
                achou = True
                break
        if not achou:
            idx_livre = None
            for i, it in enumerate(itens):
                if not isinstance(it, dict):
                    idx_livre = i
                    break
            if idx_livre is None:
                cheios.append(alvo)
                continue
            itens[idx_livre] = dict(item); itens[idx_livre]["quantidade"] = qtd
        inv["itens"] = itens
        atualizar_inventario_personagem(alvo, inv)
        payload = _payload_player(alvo)
        payload["inventario"] = inv
        _registrar_update_player(alvo, payload)
        entregues += 1
    if entregues == 0 and cheios:
        return f"Inventário cheio para: {', '.join(cheios)}"
    alvo_txt = "todos" if len(alvos) > 1 else alvos[0]
    msg = f"Item {item.get('Code') or item.get('Nome')} x{qtd} enviado para {alvo_txt}"
    if cheios:
        msg += f" | sem espaço: {', '.join(cheios)}"
    return msg


def _cmd_tp(autor, args):
    nomeados, livres = _split_args(args)
    alvo_raw = nomeados.get("alvo")
    if not alvo_raw and livres and not _to_float(livres[0]):
        alvo_raw = livres.pop(0)
    x = _to_float(nomeados.get("x"))
    y = _to_float(nomeados.get("y"))
    if x is None and livres:
        x = _to_float(livres.pop(0))
    if y is None and livres:
        y = _to_float(livres.pop(0))
    if x is None or y is None:
        return "Erro no /tp. Ordem base: /tp alvo posx posy"
    alvos = _resolver_alvos(alvo_raw, autor, aceitar_todos=True)
    if not alvos:
        return "Erro no /tp. Ordem base: /tp alvo posx posy"
    px, py = _normalizar_xy(x, y)
    for alvo in alvos:
        atualizar_posicao_personagem(alvo, [px, py])
        BANCO_DADOS.garantir_player(alvo, str(_estado_players().get(alvo, {}).get("skin", "S1")), (px, py))
        payload = _payload_player(alvo)
        payload["posicao"] = [px, py]
        _registrar_update_player(alvo, payload)
    alvo_txt = "todos" if len(alvos) > 1 else alvos[0]
    return f"Teleportado {alvo_txt} para ({int(px)}, {int(py)})"


def _cmd_spawn(autor, args):
    nomeados, livres = _split_args(args)
    poke_raw = nomeados.get("pokemon") or (livres.pop(0) if livres else "")
    poke = _resolver_pokemon(poke_raw)
    if not poke:
        return "Erro no /spawn. Ordem base: /spawn pokemon posx posy"
    if str(poke.get("Estagio", "")).strip().upper() == "FF":
        return "Não é permitido spawnar Pokémon de estágio FF"
    x = _to_float(nomeados.get("x"))
    y = _to_float(nomeados.get("y"))
    if x is None and livres:
        x = _to_float(livres.pop(0))
    if y is None and livres:
        y = _to_float(livres.pop(0))
    if x is None or y is None:
        x, y = _pos_aleatoria_perto(autor)
    x, y = _normalizar_xy(x, y)
    novo_id = BANCO_DADOS.gerar_id()
    chunk = BANCO_DADOS.chunk_da_posicao((x, y))
    especie_ref = str(poke.get("Code") or poke.get("Nome") or "").strip()
    obj = gerar_pokemon_server(novo_id=novo_id, posicao=(x, y), chunk_xy=chunk, especie=especie_ref)
    _ajustar_stats_spawn(obj.estado_extra, nomeados)
    BANCO_DADOS.inserir_objeto(obj)
    CEREBRO.registrar_spawn_manual(obj)
    registrar_diff("spawn", payload=obj.serializar(), escopo={"centro": [x, y], "raio": 80}, objeto_id=obj.Id, autor="server", categoria="pokemon")
    return f"Pokémon {poke.get('Nome')} spawnado em ({int(x)}, {int(y)})"


def _cmd_chest(autor, args):
    nomeados, livres = _split_args(args)
    tipo_raw = nomeados.get("tipo") or (livres.pop(0) if livres else "")
    mapa = {"1": "Comum", "2": "Incomum", "3": "Raro", "4": "Epico", "5": "Lendario", "6": "Mitico", "comum": "Comum", "incomum": "Incomum", "raro": "Raro", "epico": "Epico", "lendario": "Lendario", "mitico": "Mitico"}
    tipo = mapa.get(str(tipo_raw).strip().lower())
    if not tipo:
        return "Erro no /chest. Ordem base: /chest tipo posx posy"
    x = _to_float(nomeados.get("x"))
    y = _to_float(nomeados.get("y"))
    if x is None and livres:
        x = _to_float(livres.pop(0))
    if y is None and livres:
        y = _to_float(livres.pop(0))
    if x is None or y is None:
        x, y = _pos_aleatoria_perto(autor)
    x, y = _normalizar_xy(x, y)
    dados = gerar_bau_server(random, tipo_forcado=tipo)
    novo_id = BANCO_DADOS.gerar_id()
    bau = BauServer(id_objeto=novo_id, tipo_bau=tipo, itens=list(dados.get("itens", [])), posicao=(x, y), raio_colisao=0.42, raio_interacao=0.85, aberto=False)
    BANCO_DADOS.inserir_objeto(bau)
    CEREBRO.registrar_spawn_manual(bau)
    registrar_diff("spawn", payload=bau.serializar(), escopo={"centro": [x, y], "raio": 80}, objeto_id=bau.Id, autor="server", categoria="bau")
    return f"Baú {tipo} criado em ({int(x)}, {int(y)})"


def _cmd_count(args):
    _, livres = _split_args(args)
    alvo = str(livres[0] if livres else "").strip().lower()
    if alvo == "chunks":
        chunks_visiveis, chunks_simulados = CEREBRO._calcular_chunks_carregados()
        total = len(chunks_visiveis | chunks_simulados)
        return f"Chunks: carregados={len(chunks_visiveis)} | simulados={len(chunks_simulados)} | total={total}"
    if alvo == "chests":
        banco = BANCO_DADOS.contar_subtipo_entidade("bau")
        cerebro = CEREBRO.contagem_baus_registrados()
        return f"Baús existentes: banco={banco} | cerebro={cerebro}"
    if alvo == "pokemons":
        banco = BANCO_DADOS.contar_subtipo_entidade("pokemon")
        cerebro = CEREBRO.contagem_pokemons_registrados()
        return f"Pokémons existentes: banco={banco} | cerebro={cerebro}"
    return "Erro no /count. Ordem base: /count chunks|chests|pokemons"


def executar_comando_terminal(autor: str, texto: str) -> dict:
    bruto = str(texto or "").strip()
    if not bruto.startswith("/"):
        return {"ok": False, "feedback": ""}
    partes = bruto[1:].split()
    if not partes:
        return {"ok": True, "feedback": "Comando inexistente: /"}
    cmd = partes[0].lower()
    args = partes[1:]
    if cmd in {"give_args", "tp_args", "spawn_args", "chest_args", "count_args"}:
        base = {
            "give_args": "/give alvo item quantidade",
            "tp_args": "/tp alvo posx posy",
            "spawn_args": "/spawn pokemon posx posy",
            "chest_args": "/chest tipo posx posy",
            "count_args": "/count chunks|chests|pokemons",
        }
        retorno = base[cmd]
    else:
        try:
            if cmd == "give":
                retorno = _cmd_give(autor, args)
            elif cmd == "tp":
                retorno = _cmd_tp(autor, args)
            elif cmd == "spawn":
                retorno = _cmd_spawn(autor, args)
            elif cmd == "chest":
                retorno = _cmd_chest(autor, args)
            elif cmd == "count":
                retorno = _cmd_count(args)
            else:
                retorno = f"Comando inexistente: /{cmd}"
        except Exception:
            ordem = {"give": "/give alvo item quantidade", "tp": "/tp alvo posx posy", "spawn": "/spawn pokemon posx posy", "chest": "/chest tipo posx posy", "count": "/count chunks|chests|pokemons"}.get(cmd, f"/{cmd}")
            retorno = f"Erro no /{cmd}. Ordem base: {ordem}"
    return {"ok": True, "feedback": str(retorno).strip()[:220] or "Comando processado", "autor": "Servidor", "timestamp": time.time()}
