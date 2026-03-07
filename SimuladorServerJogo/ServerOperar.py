import json
import time

from SimuladorServerJogo.EstadoServidor import (
    chave_seguranca,
    definir_ligado,
    definir_mundo_existente,
    snapshot_estado,
)


# --------------------- Funções auxiliares ---------------------
def _resposta(status, mensagem, **extras):
    pacote = {"status": status, "mensagem": mensagem}
    pacote.update(extras)
    return pacote


def _validar_chave(chave):
    chave = str(chave).strip()
    if len(chave) != 4 or not chave.isdigit():
        return False, "A chave de segurança deve ter 4 dígitos"
    if chave != chave_seguranca():
        return False, "Chave de segurança incorreta"
    return True, "Chave validada"


# ============================= ROTA =============================
# ROTA: processa operações administrativas do servidor.
def processar_operacao_json(requisicao_json):
    time.sleep(0.25)

    try:
        pacote = json.loads(requisicao_json)
    except json.JSONDecodeError:
        return json.dumps(_resposta("erro", "JSON inválido"), ensure_ascii=False)

    acao = pacote.get("acao")
    dados = pacote.get("dados", {})

    # ROTA: operar_server
    if acao == "operar_server":
        valido, mensagem = _validar_chave(dados.get("chave", ""))
        status = "ok" if valido else "negado"
        return json.dumps(_resposta(status, mensagem), ensure_ascii=False)

    # ROTA: status_operacao
    if acao == "status_operacao":
        estado = snapshot_estado()
        return json.dumps(
            _resposta(
                "ok",
                "Status carregado",
                ligado=estado["ligado"],
                mundo_existente=estado["mundo_existente"],
            ),
            ensure_ascii=False,
        )

    # ROTA: definir_ligado
    if acao == "definir_ligado":
        definir_ligado(dados.get("ligado", False))
        estado = snapshot_estado()
        return json.dumps(
            _resposta("ok", "Estado do servidor atualizado", ligado=estado["ligado"]),
            ensure_ascii=False,
        )

    # ROTA: definir_mundo
    if acao == "definir_mundo":
        definir_mundo_existente(dados.get("mundo_existente", False))
        estado = snapshot_estado()
        return json.dumps(
            _resposta("ok", "Estado do mundo atualizado", mundo_existente=estado["mundo_existente"]),
            ensure_ascii=False,
        )

    return json.dumps(_resposta("erro", "Ação de operação não suportada"), ensure_ascii=False)
