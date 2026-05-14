from __future__ import annotations

import random
import unicodedata
from Servidor.Gerais.LoaderTabelas import carregar_csv_dict

from Servidor.Mundo.BancoDados import BANCO_DADOS
from Servidor.Gerais.EstadoServidor import snapshot_estado, atualizar_inventario_personagem, atualizar_perfil_personagem, atualizar_posicao_personagem
from Servidor.Mundo.ObjetosMundoServer import BauServer
from Servidor.Mundo.ServicoInventario import ServicoInventario
from Servidor.Gerais.Geradores.GeradorBaus import gerar_bau_server
from Servidor.Gerais.Geradores.GeradorPokemon import gerar_pokemon_server
from Servidor.Gerais.Rotas.Ativador import registrar_diff
from Servidor.Mundo.Cerebros.CerebroCentral import CEREBRO


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
    pos = payload.get("posicao", [0.0, 0.0]) if isinstance(payload, dict) else [0.0, 0.0]
    obj = BANCO_DADOS.garantir_player(usuario, str(payload.get("skin", "S1")), tuple(pos))
    try:
        px, py = float(pos[0]), float(pos[1])
    except Exception:
        px, py = float(obj.posicao[0]), float(obj.posicao[1])
    registrar_diff(
        "update",
        payload=payload,
        escopo={"centro": [px, py], "raio": 780.0},
        objeto_id=obj.Id,
        autor="server",
        categoria="player",
        extras={"cliente_alvo": str(usuario)},
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
    mapa = {
        "vida": "Vida", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "vel": "Vel",
        "mag": "Mag", "per": "Per", "ene": "Ene", "int": "Int",
    }
    variaveis = [k for k in stats_base.keys() if str(k) not in {"CrC", "CrD"}]

    if "iv" in nomeados:
        ivg = _clamp_i(nomeados.get("iv", 0))
        for k in variaveis:
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

    for chave_curta, chave_longa in (("crc", "CrC"), ("crd", "CrD")):
        if chave_curta in nomeados:
            stats[chave_longa] = max(0.0, float(_to_float(nomeados.get(chave_curta)) or 0.0))

    for skey, base in list(stats_base.items()):
        if skey not in subivs:
            continue
        sv = _clamp_i(subivs.get(skey, 0))
        subivs[skey] = sv
        stats[skey] = round(float(base) * (0.8 + (sv / 100.0) * 0.4), 2)

    estado["subivs"] = subivs
    estado["stats"] = stats
    vals = [int(v) for v in subivs.values()]
    estado["iv"] = _clamp_i(round(sum(vals) / max(1, len(vals))))


_CHAVES_AJUSTE_SPAWN = {
    "iv", "ivvida", "ivatk", "ivdef", "ivspa", "ivspd", "ivvel", "ivmag", "ivper", "ivene", "ivint",
    "vida", "atk", "def", "spa", "spd", "vel", "mag", "per", "ene", "int", "crc", "crd",
}


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
    for row in carregar_csv_dict("Pokemon Global Server - Itens.csv", encoding="utf-8"):
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
    for row in carregar_csv_dict("Pokemon Global Server - Pokemons.csv", encoding="utf-8"):
            nome = str(row.get("Nome", "")).strip()
            code = str(row.get("Code", "")).strip()
            estagio = str(row.get("Estagio", "")).strip()
            raridade = str(row.get("Raridade", "")).strip()
            if not nome:
                continue
            d = {"Nome": nome, "Code": code, "Estagio": estagio, "Raridade": raridade}
            pokes.append(d)
            if code:
                by_code[code] = d
            by_nome[nome.lower()] = d
    return pokes, by_code, by_nome


_ITENS, _ITENS_CODE, _ITENS_NOME = _carregar_itens()
_POKES, _POKE_CODE, _POKE_NOME = _carregar_pokemons()


_AJUDA_COMANDOS = {
    "give": {
        "uso": "/give alvo item quantidade",
        "descricao": "Entrega item para um jogador específico, para você mesmo (y), aleatório (r) ou todos.",
        "detalhes": [
            "alvo: y, r, todos, ou nome do jogador.",
            "item: code ou nome do item (se vazio, escolhe um item válido).",
            "quantidade: inteiro maior que 0.",
            "Também aceita argumentos nomeados: alvo=, item=, qtd=.",
        ],
    },
    "tp": {
        "uso": "/tp alvo posx posy | /tp destino (nomes compostos com _)",
        "descricao": "Teleporta jogador(es) para coordenadas ou teleporta você para player/NPC/estádio por nome.",
        "detalhes": [
            "alvo: y, r, todos, ou nome do jogador.",
            "posx/posy: coordenadas em tiles; a posição é normalizada nos limites do mundo.",
            "destino: nome exato (case-insensitive) de player, NPC ou estádio (ex.: Edward_Newgate, EstadioPlanta).",
            "Nomes compostos devem usar _ no lugar de espaço.",
            "Se houver mais de um destino com o mesmo nome, o comando falha por ambiguidade.",
            "Também aceita argumentos nomeados: alvo=, x=, y=.",
        ],
    },
    "locate": {
        "uso": "/locate nome | /locate dungeon <code>",
        "descricao": "Retorna coordenadas por nome e também portas de dungeon por code.",
        "detalhes": [
            "nome: nome exato (case-insensitive), como Edward_Newgate, Josefa ou EstadioPlanta.",
            "Nomes compostos devem usar _ no lugar de espaço.",
            "Se houver mais de um resultado com o mesmo nome, o comando falha por ambiguidade.",
        ],
    },
    "spawn": {
        "uso": "/spawn pokemon posx posy",
        "descricao": "Cria um Pokémon no mundo usando espécie do CSV (com estágio, tamanho e stats).",
        "detalhes": [
            "pokemon: code ou nome do Pokémon.",
            "posx/posy são opcionais; se faltar, spawn acontece perto do autor.",
            "Não permite estágio FF.",
            "Não permite raridade fora de 1..10.",
            "Aceita ajustes de stats/iv no spawn (ex.: iv=80 atk=30 ivatk=50).",
        ],
    },
    "chest": {
        "uso": "/chest tipo posx posy",
        "descricao": "Cria um baú de raridade específica no mundo.",
        "detalhes": [
            "tipo: 1..6 ou nome (comum, incomum, raro, epico, lendario, mitico).",
            "posx/posy são opcionais; se faltar, cria perto do autor.",
        ],
    },
    "count": {
        "uso": "/count chunks|chests|pokemons",
        "descricao": "Mostra contagens rápidas do estado atual do servidor.",
        "detalhes": [
            "chunks: carregados/simulados/total.",
            "chests: total de baús no banco e no cérebro.",
            "pokemons: total de pokémons no banco e no cérebro.",
        ],
    },
    "xp": {
        "uso": "/xp quantidade_xp [nome_do_jogador]",
        "descricao": "Adiciona XP para você ou para um jogador alvo.",
        "detalhes": [
            "quantidade_xp precisa ser maior que 0.",
            "Se nome_do_jogador não for informado, aplica no autor do comando.",
        ],
    },
    "chuva": {
        "uso": "/chuva [intensidade]",
        "descricao": "Alterna a chuva global ou define a chuva alvo (0..100).",
        "detalhes": [
            "Sem argumento: alterna chuva global entre ativa/desativada (persistente).",
            "Com número: define chuva alvo para convergência (0..100).",
            "Com número só funciona se a chuva estiver ativa.",
        ],
    },
    "help": {
        "uso": "/help [comando]",
        "descricao": "Lista todos os comandos ou explica um comando específico.",
        "detalhes": [
            "Sem argumento: lista comandos disponíveis.",
            "Com argumento: exibe uso e detalhes completos do comando.",
        ],
    },
}


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


def _resolver_dungeon_csv(raw):
    alvo = str(raw or "").strip().lower()
    if not alvo:
        return None
    for row in carregar_csv_dict("Pokemon Global Server - Dungeons.csv"):
        if str(row.get("Code") or "").strip().lower() == alvo:
            return row
    return None


def _normalizar_nome_busca(raw):
    bruto = unicodedata.normalize("NFKD", str(raw or "").strip().casefold().replace("_", " "))
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return " ".join(sem_acento.split())


def _locais_nomeados():
    locais = []
    npc_ids_adicionados = set()
    npc_chaves_adicionadas = set()
    players = _estado_players()
    for nome, dados in players.items():
        if not isinstance(dados, dict):
            continue
        pos = dados.get("posicao", [0.0, 0.0]) if isinstance(dados.get("posicao"), (list, tuple)) else [0.0, 0.0]
        try:
            px, py = float(pos[0]), float(pos[1])
        except Exception:
            px, py = 0.0, 0.0
        locais.append({"categoria": "player", "nome": str(nome), "nome_busca": _normalizar_nome_busca(nome), "posicao": [px, py]})

    for obj in BANCO_DADOS.listar_objetos():
        estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
        categoria, nome = "", ""
        subtipo = str(estado.get("subtipo") or "").strip().lower()
        if subtipo in {"npc_vendedor", "npc_combatente"}:
            categoria = "npc"
            nome = str(estado.get("nome") or "").strip()
        elif str(getattr(obj, "tipo_classe", "")).strip().lower() == "entidade_estadio":
            categoria = "estadio"
            nome = str(estado.get("dimensao_destino") or "").strip()
            if not nome:
                tipo_estadio = str(estado.get("tipo_estadio") or "normal").strip().title()
                nome = f"Estadio{tipo_estadio}"
        if not nome:
            continue
        if categoria == "npc":
            oid = int(getattr(obj, "Id", 0) or 0)
            npc_ids_adicionados.add(oid)
            npc_chaves_adicionadas.add((_normalizar_nome_busca(nome), int(round(float(obj.posicao[0]))), int(round(float(obj.posicao[1])))))
        locais.append(
            {"categoria": categoria, "nome": nome, "nome_busca": _normalizar_nome_busca(nome), "posicao": [float(obj.posicao[0]), float(obj.posicao[1])]}
        )
    try:
        npcs = CEREBRO._cerebro_npcs.listar_locais_nomeados()
    except Exception:
        npcs = []
    for npc in npcs:
        npc_id = int(npc.get("id", 0) or 0)
        nome = str(npc.get("nome") or "").strip()
        pos = npc.get("posicao")
        if not nome or not isinstance(pos, (list, tuple)) or len(pos) != 2:
            continue
        chave = (_normalizar_nome_busca(nome), int(round(float(pos[0]))), int(round(float(pos[1]))))
        if (npc_id > 0 and npc_id in npc_ids_adicionados) or chave in npc_chaves_adicionadas:
            continue
        locais.append({"categoria": "npc", "nome": nome, "nome_busca": _normalizar_nome_busca(nome), "posicao": [float(pos[0]), float(pos[1])]})
    return locais


def _buscar_locais_por_nome(raw):
    termo = _normalizar_nome_busca(raw)
    if not termo:
        return []
    return [loc for loc in _locais_nomeados() if loc.get("nome_busca") == termo]


def _erro_ambiguo(prefixo, termo, destinos):
    opcoes = []
    for loc in destinos[:8]:
        pos = loc.get("posicao") or [0, 0]
        opcoes.append(f"{loc.get('categoria')} {loc.get('nome')} ({int(pos[0])},{int(pos[1])})")
    extra = "..." if len(destinos) > 8 else ""
    return f"Erro no {prefixo}. Nome ambíguo: {termo}. Opções: " + "; ".join(opcoes) + extra


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
    servico = getattr(CEREBRO, "_servico_inventario", None) or ServicoInventario()
    item = servico.normalizar_item({"Code": item.get("Code"), "Nome": item.get("Nome"), "quantidade": 1})
    qtd = max(1, _to_int(qtd_raw, 1))
    entregues = 0
    cheios = []
    for alvo in alvos:
        players = _estado_players()
        dados_personagem = players.get(alvo, {}) if isinstance(players.get(alvo, {}), dict) else {}
        inv = dict(dados_personagem.get("inventario", {})) if isinstance(dados_personagem.get("inventario"), dict) else {}
        adicionado, sobra = servico.adicionar_item(inv, item, qtd, dados_personagem=dados_personagem)
        if adicionado <= 0:
            cheios.append(alvo)
            continue
        atualizar_inventario_personagem(alvo, inv)
        payload = _payload_player(alvo)
        payload["inventario"] = inv
        _registrar_update_player(alvo, payload)
        entregues += 1
        if sobra > 0:
            cheios.append(f"{alvo} (sobrou {sobra})")
    if entregues == 0 and cheios:
        return f"Inventário cheio para: {', '.join(cheios)}"
    alvo_txt = "todos" if len(alvos) > 1 else alvos[0]
    msg = f"Item {item.get('Code') or item.get('Nome')} x{qtd} enviado para {alvo_txt}"
    if cheios:
        msg += f" | sem espaço: {', '.join(cheios)}"
    return msg


def _cmd_tp(autor, args):
    nomeados, livres = _split_args(args)
    if len(livres) == 1 and _to_float(livres[0]) is None and "x" not in nomeados and "y" not in nomeados:
        destinos = _buscar_locais_por_nome(livres[0])
        if not destinos:
            return f"Destino não encontrado: {livres[0]}"
        if len(destinos) > 1:
            return _erro_ambiguo("/tp", livres[0], destinos)
        destino = destinos[0]
        px, py = _normalizar_xy(destino["posicao"][0], destino["posicao"][1])
        atualizar_posicao_personagem(autor, [px, py])
        BANCO_DADOS.garantir_player(autor, str(_estado_players().get(autor, {}).get("skin", "S1")), (px, py))
        payload = _payload_player(autor)
        payload["posicao"] = [px, py]
        payload["teleporte"] = True
        _registrar_update_player(autor, payload)
        return f"Teleportado {autor} para {destino.get('categoria')} {destino.get('nome')} em ({int(px)}, {int(py)})"

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
        return "Erro no /tp. Ordem base: /tp alvo posx posy | /tp destino (nomes compostos com _)"
    alvos = _resolver_alvos(alvo_raw, autor, aceitar_todos=True)
    if not alvos:
        return "Erro no /tp. Ordem base: /tp alvo posx posy | /tp destino (nomes compostos com _)"
    px, py = _normalizar_xy(x, y)
    for alvo in alvos:
        atualizar_posicao_personagem(alvo, [px, py])
        BANCO_DADOS.garantir_player(alvo, str(_estado_players().get(alvo, {}).get("skin", "S1")), (px, py))
        payload = _payload_player(alvo)
        payload["posicao"] = [px, py]
        payload["teleporte"] = True
        _registrar_update_player(alvo, payload)
    alvo_txt = "todos" if len(alvos) > 1 else alvos[0]
    return f"Teleportado {alvo_txt} para ({int(px)}, {int(py)})"


def _cmd_locate(args):
    _, livres = _split_args(args)
    if not livres:
        return "Erro no /locate. Ordem base: /locate nome | /locate dungeon <code>"
    if len(livres) >= 2 and str(livres[0]).lower() == "dungeon":
        code = str(livres[1]).strip()
        code_busca = code.lower()
        row_dungeon = _resolver_dungeon_csv(code)
        if row_dungeon is None:
            return f"Dungeon não encontrada no CSV: {code}"
        portas = []
        chaves = set()
        nome = str(row_dungeon.get("Nome") or code)
        for obj in BANCO_DADOS.listar_objetos():
            estado = getattr(obj, "estado_extra", {}) if isinstance(getattr(obj, "estado_extra", {}), dict) else {}
            if str(estado.get("subtipo") or "").lower() != "dungeon":
                continue
            if str(estado.get("dungeon_code") or "").strip().lower() != code_busca:
                continue
            nome = str(estado.get("dungeon_nome") or nome)
            porta = (int(estado.get("porta_idx", len(portas)+1) or len(portas)+1), int(obj.posicao[0]), int(obj.posicao[1]))
            portas.append(porta)
            chaves.add((porta[0], porta[1], porta[2]))
        for item in BANCO_DADOS.listar_dungeons_registradas():
            if str(item.get("dungeon_code") or "").strip().lower() != code_busca:
                continue
            pos = item.get("posicao") if isinstance(item.get("posicao"), list) else [0, 0]
            porta = (int(item.get("porta_idx", len(portas)+1) or len(portas)+1), int(float(pos[0])), int(float(pos[1])))
            if (porta[0], porta[1], porta[2]) in chaves:
                continue
            nome = str(item.get("dungeon_nome") or nome)
            portas.append(porta)
            chaves.add((porta[0], porta[1], porta[2]))
        if not portas:
            return f"Dungeon {code} existe no CSV, mas nenhuma pedra/porta foi registrada no mundo."
        portas.sort(key=lambda x: x[0])
        return f"Dungeon {nome}: " + ", ".join([f"porta {i} em ({x},{y})" for i,x,y in portas])
    nome_raw = " ".join(livres).strip()
    destinos = _buscar_locais_por_nome(nome_raw)
    if not destinos:
        return f"Destino não encontrado: {nome_raw}"
    if len(destinos) > 1:
        return _erro_ambiguo("/locate", nome_raw, destinos)
    destino = destinos[0]
    px, py = destino["posicao"][0], destino["posicao"][1]
    return f"{destino.get('categoria').upper()} {destino.get('nome')} está em ({int(px)}, {int(py)})"


def _cmd_spawn(autor, args):
    nomeados, livres = _split_args(args)
    poke_raw = nomeados.get("pokemon") or (livres.pop(0) if livres else "")
    poke = _resolver_pokemon(poke_raw)
    if not poke:
        return "Erro no /spawn. Ordem base: /spawn pokemon posx posy"
    if str(poke.get("Estagio", "")).strip().upper() == "FF":
        return "Não é permitido spawnar Pokémon de estágio FF"
    raridade = _to_float(poke.get("Raridade"))
    if raridade is None or raridade < 1.0 or raridade > 10.0:
        return "Não é permitido spawnar Pokémon com raridade fora de 1..10"
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
    if any(chave in nomeados for chave in _CHAVES_AJUSTE_SPAWN):
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
    bau = BauServer(
        id_objeto=novo_id,
        tipo_bau=tipo,
        itens=list(dados.get("itens", [])),
        posicao=(x, y),
        raio_colisao=float(dados.get("raio_colisao", 0.42) or 0.42),
        raio_interacao=float(dados.get("raio_interacao", 0.85) or 0.85),
        quantidade_itens=int(dados.get("quantidade_itens", len(list(dados.get("itens", []))) or 1) or 1),
        tamanho_tiles=float(dados.get("tamanho_tiles", 1.10) or 1.10),
        aberto=False,
    )
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


def _cmd_xp(autor, args):
    _, livres = _split_args(args)
    if not livres:
        return "Erro no /xp. Ordem base: /xp quantidade_xp [nome_do_jogador]"
    qtd_xp = _to_int(livres.pop(0), -1)
    if qtd_xp <= 0:
        return "Erro no /xp. Quantidade de XP inválida"

    alvo = autor
    if livres:
        alvo = str(" ".join(livres)).strip()
    players = _estado_players()
    if alvo not in players:
        for nome in players.keys():
            if str(nome).lower() == str(alvo).lower():
                alvo = nome
                break
    if alvo not in players:
        return f"Jogador não encontrado: {alvo}"

    p = players.get(alvo, {}) if isinstance(players.get(alvo, {}), dict) else {}
    pos = p.get("posicao", [0.0, 0.0]) if isinstance(p.get("posicao", [0.0, 0.0]), (list, tuple)) else [0.0, 0.0]
    ator = BANCO_DADOS.garantir_player(alvo, str(p.get("skin", "S1")), (float(pos[0]), float(pos[1])))
    if not isinstance(ator.estado_extra.get("perfil"), dict):
        ator.estado_extra["perfil"] = {}
    ator.estado_extra["perfil"].update({k: v for k, v in p.items() if k != "inventario"})
    retorno = ator.GanharXP(qtd_xp)
    atualizar_perfil_personagem(alvo, dict(ator.estado_extra.get("perfil", {})))

    payload = _payload_player(alvo)
    payload["perfil"] = dict(ator.estado_extra.get("perfil", {}))
    _registrar_update_player(alvo, payload)

    return (
        f"XP aplicado em {alvo}: +{qtd_xp} | "
        f"nível={retorno.get('nivel_atual', 0)} | xp={retorno.get('xp_atual', 0)}/{retorno.get('xp_alvo', 0)}"
    )


def _cmd_help(args):
    _, livres = _split_args(args)
    if not livres:
        comandos = sorted(_AJUDA_COMANDOS.keys())
        return "Comandos disponíveis: " + ", ".join(f"/{c}" for c in comandos)
    alvo = str(livres[0] or "").strip().lower().lstrip("/")
    info = _AJUDA_COMANDOS.get(alvo)
    if not isinstance(info, dict):
        return f"Comando não encontrado: /{alvo}"
    uso = str(info.get("uso") or f"/{alvo}")
    descricao = str(info.get("descricao") or "")
    detalhes = [str(d).strip() for d in list(info.get("detalhes") or []) if str(d).strip()]
    msg = [f"Comando /{alvo}", f"Uso: {uso}"]
    if descricao:
        msg.append(descricao)
    for det in detalhes:
        msg.append(f"- {det}")
    return " | ".join(msg)


def _cmd_chuva(args):
    _, livres = _split_args(args)
    if not livres:
        ativo = CEREBRO.alternar_chuva_global()
        return "Chuva global ativada" if ativo else "Chuva global desativada"
    alvo = _to_int(livres[0], -1)
    if alvo < 0 or alvo > 100:
        return "Erro no /chuva. Intensidade deve estar entre 0 e 100"
    if not CEREBRO.chuva_habilitada():
        return "Erro no /chuva. A chuva está desativada no servidor"
    if not CEREBRO.definir_chuva_alvo_global(alvo):
        return "Erro no /chuva. Não foi possível atualizar a chuva alvo"
    return f"Chuva alvo ajustada para {alvo}%"


def comando_give(autor, args, contexto=None, meta=None, catalogo=None):
    return _cmd_give(autor, list(args or []))


def comando_tp(autor, args, contexto=None, meta=None, catalogo=None):
    return _cmd_tp(autor, list(args or []))


def comando_locate(autor, args, contexto=None, meta=None, catalogo=None):
    _ = autor
    return _cmd_locate(list(args or []))


def comando_spawn(autor, args, contexto=None, meta=None, catalogo=None):
    return _cmd_spawn(autor, list(args or []))


def comando_chest(autor, args, contexto=None, meta=None, catalogo=None):
    return _cmd_chest(autor, list(args or []))


def comando_count(autor, args, contexto=None, meta=None, catalogo=None):
    _ = autor
    return _cmd_count(list(args or []))


def comando_xp(autor, args, contexto=None, meta=None, catalogo=None):
    return _cmd_xp(autor, list(args or []))


def comando_chuva(autor, args, contexto=None, meta=None, catalogo=None):
    _ = autor
    return _cmd_chuva(list(args or []))


CATALOGO_COMANDOS_MUNDO = [
    {
        "nome": "give",
        "aliases": [],
        "funcao": comando_give,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/give [alvo] item quantidade | /give item quantidade | /give alvo=y item=1 qtd=5",
        "descricao": "Entrega item respeitando regras de inventário, stacks e slots.",
        "argumentos": ["alvo: y, r, todos ou jogador", "item: code ou nome", "quantidade/qtd: inteiro"],
        "exemplos": ["/give y 1 5", "/give item=Potion qtd=3", "/give alvo=todos item=1 quantidade=2"],
    },
    {
        "nome": "tp",
        "aliases": [],
        "funcao": comando_tp,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/tp alvo x y | /tp destino",
        "descricao": "Teleporta jogador(es) para coordenadas ou o autor para player/NPC/estádio.",
        "argumentos": ["alvo: y, r, todos ou jogador", "destino aceita acento, espaço, _ e case-insensitive"],
        "exemplos": ["/tp y 50 80", "/tp Edward Newgate", "/tp Estadio_Planta"],
    },
    {
        "nome": "locate",
        "aliases": [],
        "funcao": comando_locate,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/locate nome | /locate dungeon code",
        "descricao": "Mostra coordenadas de player, NPC, estádio ou porta de dungeon.",
        "argumentos": ["nome aceita acento, espaço, _ e case-insensitive"],
        "exemplos": ["/locate Josefa", "/locate dungeon D1"],
    },
    {
        "nome": "spawn",
        "aliases": ["summon"],
        "funcao": comando_spawn,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/spawn pokemon [x y] [iv=80|atk=30|ivatk=50]",
        "descricao": "Cria Pokémon no mundo usando o gerador oficial.",
        "argumentos": ["pokemon: code ou nome", "não permite estágio FF nem raridade fora de 1..10"],
        "exemplos": ["/spawn Pikachu", "/spawn Pikachu iv=80", "/spawn 25 40 60"],
    },
    {
        "nome": "chest",
        "aliases": ["bau", "baú"],
        "funcao": comando_chest,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/chest tipo [x y]",
        "descricao": "Cria baú usando os dados sorteados pelo gerador oficial.",
        "argumentos": ["tipo: 1..6, comum, incomum, raro, epico, lendario ou mitico"],
        "exemplos": ["/chest raro", "/bau 3 40 50"],
    },
    {
        "nome": "count",
        "aliases": ["contar"],
        "funcao": comando_count,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/count chunks|chests|pokemons",
        "descricao": "Mostra contagens rápidas do servidor.",
        "argumentos": ["alvo: chunks, chests ou pokemons"],
        "exemplos": ["/count pokemons", "/contar chunks"],
    },
    {
        "nome": "xp",
        "aliases": [],
        "funcao": comando_xp,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/xp quantidade [jogador]",
        "descricao": "Adiciona XP ao autor ou jogador informado.",
        "argumentos": ["quantidade: inteiro maior que 0"],
        "exemplos": ["/xp 100", "/xp 250 Leon19"],
    },
    {
        "nome": "chuva",
        "aliases": [],
        "funcao": comando_chuva,
        "contexto": "mundo",
        "nivel": 1,
        "uso": "/chuva [intensidade]",
        "descricao": "Alterna a chuva global ou define intensidade alvo.",
        "argumentos": ["intensidade opcional: 0..100"],
        "exemplos": ["/chuva", "/chuva 60"],
    },
]
