from __future__ import annotations

from SimuladorServerJogo.Logica.Executes.ExecutesAtaques.UtilitariosExecutes import (
    aplicar_efeito,
    dano_generico,
    fnum,
)


_DEF_AREAS = {
    "A1": (0, 0), "A2": (0, 1), "A3": (0, 2),
    "A4": (1, 0), "A5": (1, 1), "A6": (1, 2),
    "A7": (2, 0), "A8": (2, 1), "A9": (2, 2),
    "I1": (0, 0), "I2": (0, 1), "I3": (0, 2),
    "I4": (1, 0), "I5": (1, 1), "I6": (1, 2),
    "I7": (2, 0), "I8": (2, 1), "I9": (2, 2),
}


def _adjacentes_mesmo_lado(area_id):
    area = str(area_id or "").upper()
    if area not in _DEF_AREAS:
        return []
    prefixo = area[0]
    r0, c0 = _DEF_AREAS[area]
    saida = []
    for idx in range(1, 10):
        chave = f"{prefixo}{idx}"
        if chave == area or chave not in _DEF_AREAS:
            continue
        r, c = _DEF_AREAS[chave]
        if abs(r - r0) <= 1 and abs(c - c0) <= 1:
            saida.append(chave)
    return saida


def _linha_ordenada_por_direcao(area_id, lado_usuario):
    area = str(area_id or "").upper()
    if area not in _DEF_AREAS:
        return [area] if area else []
    prefixo = area[0]
    r0, _ = _DEF_AREAS[area]
    linha = [f"{prefixo}{idx}" for idx in range(1, 10) if f"{prefixo}{idx}" in _DEF_AREAS and _DEF_AREAS[f"{prefixo}{idx}"][0] == r0]
    # Regra explícita e estável de profundidade: jogador(50) avança 0->2; inimigo(51) avança 2->0.
    if int(lado_usuario) == 51:
        linha.sort(key=lambda a: _DEF_AREAS[a][1], reverse=True)
    else:
        linha.sort(key=lambda a: _DEF_AREAS[a][1])
    return linha


def _inimigos_vivos_adj_alvo(ctx, alvo):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    if partida is None or alvo is None or usuario is None:
        return []
    saida = []
    for area_id in _adjacentes_mesmo_lado(getattr(alvo, "area_id", None)):
        poke = partida.pokemon_na_area(area_id)
        if poke is None or poke is alvo or not poke.esta_vivo():
            continue
        if int(getattr(poke, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        saida.append(poke)
    return saida


def _alvos_linha_inimigos(ctx, alvo_inicial):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    if partida is None or usuario is None or alvo_inicial is None:
        return []
    linha = _linha_ordenada_por_direcao(getattr(alvo_inicial, "area_id", None), getattr(usuario, "lado_id", 50))
    if not linha:
        return [alvo_inicial] if alvo_inicial is not None else []
    try:
        idx_inicial = linha.index(str(getattr(alvo_inicial, "area_id", "")).upper())
    except ValueError:
        idx_inicial = 0
    linha_apos_alvo = linha[idx_inicial:]
    saida = []
    for area_id in linha_apos_alvo:
        poke = partida.pokemon_na_area(area_id)
        if poke is None or not poke.esta_vivo():
            continue
        if int(getattr(poke, "lado_id", -1)) == int(getattr(usuario, "lado_id", -2)):
            continue
        saida.append(poke)
    return saida


def _aplicar_status(ctx, alvo, nome, duracao=6, negativo=True):
    usuario = ctx.get("usuario")
    return aplicar_efeito(usuario, alvo, nome, duracao=duracao, negativo=negativo, dados={"origem_ataque": ((ctx.get("propriedades") or {}).get("nome"))})


def _aplicar_mod_atributo(ctx, alvo, nome_efeito, atributo, valor, duracao=6, negativo=False):
    usuario = ctx.get("usuario")
    dados = {"tipo": "mod_atributo", "mod_atributo": True, "atributo": atributo, "origem_ataque": nome_efeito}
    return aplicar_efeito(usuario, alvo, nome_efeito, duracao=duracao, valor=valor, negativo=negativo, dados=dados)


def _executar_bola(ctx, alvo, tipo):
    usuario = ctx.get("usuario")
    ret = dano_generico(ctx, alvo, usuario.obter_atributo("SpA") * 1.05, "especial", tipo=tipo)
    dano_vida = fnum(ret.get("dano_vida"), 0.0)
    if dano_vida <= 0:
        return ret
    dano_sec = max(0.0, dano_vida * 0.5)
    for adj in _inimigos_vivos_adj_alvo(ctx, alvo):
        dano_generico(ctx, adj, dano_sec, "especial", tipo=tipo)
    return ret


def _executar_raio(ctx, alvo, escala_inicial, reducao_spa, tipo, escala_sol_forte=None):
    usuario = ctx.get("usuario")
    partida = ctx.get("partida")
    spa = usuario.obter_atributo("SpA")
    base = spa * escala_inicial
    if escala_sol_forte is not None and str(getattr(partida, "clima_atual", "")) == "Sol Forte":
        base = spa * escala_sol_forte
    alvos = _alvos_linha_inimigos(ctx, alvo)
    if not alvos:
        alvos = [alvo] if alvo is not None else []
    ultimo = {}
    for i, alvo_linha in enumerate(alvos):
        bruto = max(0.0, base - (spa * reducao_spa * i))
        ultimo = dano_generico(ctx, alvo_linha, bruto, "especial", tipo=tipo)
    return ultimo


def _executar_danca_clima(ctx, clima):
    partida = ctx.get("partida")
    usuario = ctx.get("usuario")
    props = (ctx.get("propriedades") or {}) if isinstance(ctx.get("propriedades"), dict) else {}
    if partida is None:
        return {"falha": True, "motivo": "partida_invalida"}
    antes = getattr(partida, "clima_atual", None)
    partida.clima_atual = clima
    if hasattr(partida, "registrar_evento_log"):
        partida.registrar_evento_log("clima_mudou", {
            "clima_antes": antes,
            "clima_depois": clima,
            "usuario_id": getattr(usuario, "id_batalha", None),
            "usuario_nome": getattr(usuario, "nome", None),
            "ataque_nome": props.get("nome"),
        })
    if hasattr(partida, "disparar_flag"):
        partida.disparar_flag("AoMudarClima", {"partida": partida, "usuario": usuario, "pokemon_evento": usuario, "alvo": usuario, "clima_antes": antes, "clima_depois": clima})
    return {"aplicado": True, "clima_antes": antes, "clima_depois": clima}


def execute_bola_de_fogo(ctx, alvo): return _executar_bola(ctx, alvo, "fogo")
def execute_bola_de_agua(ctx, alvo): return _executar_bola(ctx, alvo, "agua")
def execute_bola_eletrica(ctx, alvo): return _executar_bola(ctx, alvo, "eletrico")
def execute_bola_sombria(ctx, alvo): return _executar_bola(ctx, alvo, "sombrio")
def execute_nas_sombras(ctx, alvo): return _aplicar_status(ctx, ctx.get("usuario"), "Furtivo", duracao=6, negativo=False)
def execute_gota_pesada(ctx, alvo): return _aplicar_status(ctx, alvo, "Encharcado", duracao=6, negativo=True)
def execute_queimar(ctx, alvo): return _aplicar_status(ctx, alvo, "Queimado", duracao=6, negativo=True)
def execute_envenenar(ctx, alvo): return _aplicar_status(ctx, alvo, "Envenenado", duracao=6, negativo=True)
def execute_energizar(ctx, alvo): return _aplicar_status(ctx, alvo, "Energizado", duracao=6, negativo=False)
def execute_confusao(ctx, alvo): return _aplicar_status(ctx, alvo, "Confuso", duracao=6, negativo=True)
def execute_regeneracao(ctx, alvo): return _aplicar_status(ctx, alvo, "Regeneração", duracao=6, negativo=False)
def execute_voar(ctx, alvo): return _aplicar_status(ctx, ctx.get("usuario"), "Voando", duracao=6, negativo=False)
def execute_flutuar(ctx, alvo): return _aplicar_status(ctx, ctx.get("usuario"), "Flutuando", duracao=6, negativo=False)
def execute_bencao(ctx, alvo): return _aplicar_status(ctx, alvo, "Abençoado", duracao=6, negativo=False)
def execute_som_atordoante(ctx, alvo): return _aplicar_status(ctx, alvo, "Atordoado", duracao=6, negativo=True)
def execute_raizes(ctx, alvo): return _aplicar_status(ctx, alvo, "Enraizado", duracao=6, negativo=True)
def execute_grito_de_guerra(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Grito de Guerra', 'Atk', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_rugido(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Rugido', 'Atk', -alvo.obter_atributo('Atk') * 0.08, 6, True)
def execute_chama_interior(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Chama Interior', 'SpA', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_nevoa_fria(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Névoa Fria', 'SpA', -alvo.obter_atributo('SpA') * 0.08, 6, True)
def execute_casca_de_pedra(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Casca de Pedra', 'Def', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_ferrugem(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Ferrugem', 'Def', -alvo.obter_atributo('Def') * 0.08, 6, True)
def execute_escama_mistica(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Escama Mística', 'SpD', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_sussurro_sombrio(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Sussurro Sombrio', 'SpD', -alvo.obter_atributo('SpD') * 0.08, 6, True)
def execute_canalizar(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Canalizar', 'Mag', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_selar_arcano(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Selar Arcano', 'Mag', -alvo.obter_atributo('Mag') * 0.07, 6, True)
def execute_afiar(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Afiar', 'Per', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_armadura_mole(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Armadura Mole', 'Per', -alvo.obter_atributo('Per') * 0.07, 6, True)
def execute_correnteza(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Correnteza', 'Vel', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_teia_pegajosa(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Teia Pegajosa', 'Vel', -alvo.obter_atributo('Vel') * 0.08, 6, True)
def execute_instinto(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Instinto', 'Int', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_desorientar(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Desorientar', 'Int', -alvo.obter_atributo('Int') * 0.07, 6, True)
def execute_sede_de_sangue(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Sede de Sangue', 'Vamp', ctx.get('usuario').obter_atributo('Mag') * 0.08, 6, False)
def execute_sangue_frio(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Sangue Frio', 'CrC', ctx.get('usuario').obter_atributo('Mag') * 0.06, 6, False)
def execute_azar(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Azar', 'CrC', -alvo.obter_atributo('CrC') * 0.06, 6, True)
def execute_golpe_letal(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Golpe Letal', 'CrD', ctx.get('usuario').obter_atributo('Mag') * 0.10, 6, False)
def execute_amolecer(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Amolecer', 'CrD', -alvo.obter_atributo('CrD') * 0.06, 6, True)
def execute_casco_vivo(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Casco Vivo', 'Dur', ctx.get('usuario').obter_atributo('Mag') * 0.12, 6, False)
def execute_rachar_terra(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Rachar Terra', 'Dur', -alvo.obter_atributo('Dur') * 0.06, 6, True)
def execute_amplificar(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Amplificar', 'Amp', ctx.get('usuario').obter_atributo('Mag') * 0.08, 6, False)
def execute_silenciar(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Silenciar', 'Amp', -alvo.obter_atributo('Amp') * 0.06, 6, True)
def execute_inflar(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Inflar', 'Vida', ctx.get('usuario').obter_atributo('Mag') * 0.20, 6, False)
def execute_murchar(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Murchar', 'Vida', -alvo.obter_atributo('Vida') * 0.06, 6, True)
def execute_postura_firme(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Postura Firme', 'Assertividade', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_intimidar(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Intimidar', 'Assertividade', -alvo.obter_atributo('Assertividade') * 0.08, 6, True)
def execute_olho_de_aguia(ctx, alvo): return _aplicar_mod_atributo(ctx, ctx.get('usuario'), 'Olho de Águia', 'Acuracia', ctx.get('usuario').obter_atributo('Mag') * 0.15, 6, False)
def execute_poeira_nos_olhos(ctx, alvo): return _aplicar_mod_atributo(ctx, alvo, 'Poeira nos Olhos', 'Acuracia', -alvo.obter_atributo('Acuracia') * 0.08, 6, True)
def execute_raio_de_fogo(ctx, alvo): return _executar_raio(ctx, alvo, 1.30, 0.15, 'fogo')
def execute_raio_de_gelo(ctx, alvo): return _executar_raio(ctx, alvo, 1.30, 0.15, 'gelo')
def execute_raio_solar(ctx, alvo): return _executar_raio(ctx, alvo, 1.30, 0.15, 'planta', escala_sol_forte=1.60)
def execute_raio_psiquico(ctx, alvo): return _executar_raio(ctx, alvo, 1.30, 0.15, 'psiquico')
def execute_raio_cosmico(ctx, alvo): return _executar_raio(ctx, alvo, 1.45, 0.12, 'cosmico')
def execute_danca_da_chuva(ctx, alvo): return _executar_danca_clima(ctx, 'Chuva')
def execute_danca_do_sol(ctx, alvo): return _executar_danca_clima(ctx, 'Sol Forte')
def execute_danca_eletrica(ctx, alvo): return _executar_danca_clima(ctx, 'Tempestade de Raios')
def execute_voador(ctx, alvo): return {"falha": True, "motivo": "passiva_nao_manual"}
def execute_flutuante(ctx, alvo): return {"falha": True, "motivo": "passiva_nao_manual"}
def execute_implacavel(ctx, alvo): return {"falha": True, "motivo": "passiva_nao_manual"}
def execute_imunizado(ctx, alvo): return {"falha": True, "motivo": "passiva_nao_manual"}


def _passiva_voador(ctx):
    alvo = ctx.get('dono_passiva') or ctx.get('pokemon_evento')
    return alvo.ReceberEfeito({'nome': 'Voando', 'permanente': True, 'dados': {'permanente': True}}, origem=alvo, dados={'permanente': True}) if alvo is not None else {}


def _passiva_flutuante(ctx):
    alvo = ctx.get('dono_passiva') or ctx.get('pokemon_evento')
    return alvo.ReceberEfeito({'nome': 'Flutuando', 'permanente': True, 'dados': {'permanente': True}}, origem=alvo, dados={'permanente': True}) if alvo is not None else {}


def _passiva_implacavel(ctx):
    alvo = ctx.get('dono_passiva') or ctx.get('pokemon_evento')
    return alvo.ReceberEfeito({'nome': 'Imparavel', 'permanente': True, 'dados': {'permanente': True}}, origem=alvo, dados={'permanente': True}) if alvo is not None else {}


def _passiva_imunizado(ctx):
    alvo = ctx.get('dono_passiva') or ctx.get('pokemon_evento')
    return alvo.ReceberEfeito({'nome': 'Imunizado', 'permanente': True, 'dados': {'permanente': True}}, origem=alvo, dados={'permanente': True}) if alvo is not None else {}


_EXECUTES_NOVOS = {
    "boladefogo": execute_bola_de_fogo, "boladeagua": execute_bola_de_agua, "bolaeletrica": execute_bola_eletrica, "bolasombria": execute_bola_sombria,
    "nassombras": execute_nas_sombras, "gotapesada": execute_gota_pesada, "queimar": execute_queimar, "envenenar": execute_envenenar,
    "energizar": execute_energizar, "confusao": execute_confusao, "regeneracao": execute_regeneracao, "voar": execute_voar, "flutuar": execute_flutuar,
    "bencao": execute_bencao, "somatordoante": execute_som_atordoante, "raizes": execute_raizes,
    "gritodeguerra": execute_grito_de_guerra, "rugido": execute_rugido, "chamainterior": execute_chama_interior, "nevoafria": execute_nevoa_fria,
    "cascadepedra": execute_casca_de_pedra, "ferrugem": execute_ferrugem, "escamamistica": execute_escama_mistica, "sussurrosombrio": execute_sussurro_sombrio,
    "canalizar": execute_canalizar, "selararcano": execute_selar_arcano, "afiar": execute_afiar, "armaduramole": execute_armadura_mole,
    "correnteza": execute_correnteza, "teiapegajosa": execute_teia_pegajosa, "instinto": execute_instinto, "desorientar": execute_desorientar,
    "sededesangue": execute_sede_de_sangue, "sanguefrio": execute_sangue_frio, "azar": execute_azar, "golpeletal": execute_golpe_letal,
    "amolecer": execute_amolecer, "cascovivo": execute_casco_vivo, "racharterra": execute_rachar_terra, "amplificar": execute_amplificar,
    "silenciar": execute_silenciar, "inflar": execute_inflar, "murchar": execute_murchar, "posturafirme": execute_postura_firme,
    "intimidar": execute_intimidar, "olhodeaguia": execute_olho_de_aguia, "poeiranosolhos": execute_poeira_nos_olhos,
    "raiodefogo": execute_raio_de_fogo, "raiodegelo": execute_raio_de_gelo, "raiosolar": execute_raio_solar, "raiopsiquico": execute_raio_psiquico, "raiocosmico": execute_raio_cosmico,
    "dancadachuva": execute_danca_da_chuva, "dancadosol": execute_danca_do_sol, "dancaeletrica": execute_danca_eletrica,
    "voador": execute_voador, "flutuante": execute_flutuante, "implacavel": execute_implacavel, "imunizado": execute_imunizado,
}

_PASSIVAS_NOVAS = [
    {"nome": "Voador", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_voador, "origem": "ataque", "code": "74"},
    {"nome": "Flutuante", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_flutuante, "origem": "ataque", "code": "75"},
    {"nome": "Implacável", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_implacavel, "origem": "ataque", "code": "76"},
    {"nome": "Imunizado", "flag": "AoRegistrarPassiva", "grupo": "self", "func": _passiva_imunizado, "origem": "ataque", "code": "77"},
]

_ALIASES_NOVOS = {
    "19": "boladefogo", "20": "boladeagua", "21": "bolaeletrica", "22": "bolasombria", "23": "nassombras", "24": "gotapesada", "25": "queimar", "26": "envenenar",
    "27": "energizar", "28": "confusao", "29": "regeneracao", "30": "voar", "31": "flutuar", "32": "bencao", "33": "somatordoante", "34": "raizes", "35": "gritodeguerra", "36": "rugido",
    "37": "chamainterior", "38": "nevoafria", "39": "cascadepedra", "40": "ferrugem", "41": "escamamistica", "42": "sussurrosombrio", "43": "canalizar", "44": "selararcano", "45": "afiar", "46": "armaduramole",
    "47": "correnteza", "48": "teiapegajosa", "49": "instinto", "50": "desorientar", "51": "sededesangue", "52": "sanguefrio", "53": "azar", "54": "golpeletal", "55": "amolecer", "56": "cascovivo",
    "57": "racharterra", "58": "amplificar", "59": "silenciar", "60": "inflar", "61": "murchar", "62": "posturafirme", "63": "intimidar", "64": "olhodeaguia", "65": "poeiranosolhos",
    "66": "raiodefogo", "67": "raiodegelo", "68": "raiosolar", "69": "raiopsiquico", "70": "raiocosmico", "71": "dancadachuva", "72": "dancadosol", "73": "dancaeletrica", "74": "voador", "75": "flutuante", "76": "implacavel", "77": "imunizado",
}


def obter_executes_novos():
    return dict(_EXECUTES_NOVOS)


def obter_passivas_ataques_novas():
    return list(_PASSIVAS_NOVAS)


def obter_aliases_executes_novos():
    return dict(_ALIASES_NOVOS)
