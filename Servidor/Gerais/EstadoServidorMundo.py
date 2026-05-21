import threading

import Servidor.Gerais.Geradores.GeradorMundo as GERADOR_MUNDO
from Servidor.Gerais.Geradores.GeradorMundo import carregar_estado_mundo, gerar_novo_estado_mundo, limpar_arquivos_mundo, salvar_estado_mundo
from Servidor.Mundo.BancoDados import BANCO_DADOS
from Servidor.Mundo.PacotesTick import PACOTES_TICK


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

def _persistir_personagens(force: bool = False) -> None:
    return _CTX.persistir_personagens(force=force)


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


def _recarregar_mundo():
    _garantir_estado_ativo()
    novo_mundo = carregar_estado_mundo()
    novo_mundo["tempo_mundo"] = _normalizar_tempo_mundo(novo_mundo.get("tempo_mundo"))
    _CTX.set_estado_mundo(novo_mundo)


def _limites_mundo_atuais() -> tuple[float, float]:
    meta = _ESTADO_MUNDO.get("meta", {}) if isinstance(_ESTADO_MUNDO, dict) else {}
    largura_meta = float(meta.get("largura_blocos", 0)) if isinstance(meta, dict) else 0.0
    altura_meta = float(meta.get("altura_blocos", 0)) if isinstance(meta, dict) else 0.0
    largura = largura_meta if largura_meta > 0 else float(GERADOR_MUNDO.LARGURA_BLOCOS)
    altura = altura_meta if altura_meta > 0 else float(GERADOR_MUNDO.ALTURA_BLOCOS)
    return (max(1.0, largura), max(1.0, altura))


def _criar_novo_mundo_sync():
    _garantir_estado_ativo()
    from Servidor.Gerais.Rotas.Ativador import resetar_estado_clientes

    def _callback_progresso(percentual: int, mensagem: str):
        with _LOCK:
            _set_geracao(progresso=percentual, mensagem=mensagem)

    players = dict(_ESTADO.get("personagens", {}))
    config_mundo = obter_config_mundo()
    _set_geracao(em_andamento=True, progresso=1, mensagem="Preparando geração do mundo", erro="", operacao="criacao")
    novo_mundo = gerar_novo_estado_mundo(players=players, callback_progresso=_callback_progresso, config_mundo=config_mundo)
    novo_mundo["tempo_mundo"] = _tempo_mundo_padrao()
    _CTX.set_estado_mundo(novo_mundo)
    _set_geracao(progresso=98, mensagem="Salvando estado do mundo")
    salvar_estado_mundo(_CTX.estado_mundo())
    _set_geracao(progresso=99, mensagem="Carregando mundo no servidor")
    BANCO_DADOS.recarregar_mundo(_CTX.estado_mundo(), limpar_objetos=True)
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
    _garantir_estado_ativo()
    from Servidor.Gerais.Rotas.Ativador import resetar_estado_clientes
    limpar_arquivos_mundo()
    _CTX.set_estado_mundo(_estado_mundo_vazio())
    _ESTADO["personagens"].clear()
    _ESTADO["jogadores_com_personagem"].clear()
    BANCO_DADOS.recarregar_mundo(_ESTADO_MUNDO, limpar_objetos=True)
    resetar_estado_clientes()
    _recarregar_cerebro_mundo()


def _worker_apagar_mundo():
    from Servidor.Mundo.Cerebros.CerebroCentral import CEREBRO
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


def obter_config_mundo() -> dict:
    try:
        _garantir_estado_ativo()
    except RuntimeError:
        return _config_mundo_padrao()
    with _LOCK:
        regras = dict(_ESTADO.get("regras_servidor", {}) or {})
        return normalizar_config_mundo(regras.get("mundo_configuracao"))


def definir_config_mundo(config) -> dict:
    _garantir_estado_ativo()
    normalizada = normalizar_config_mundo(config)
    with _LOCK:
        regras = dict(_ESTADO.get("regras_servidor", {}) or {})
        regras["mundo_configuracao"] = normalizada
        _ESTADO["regras_servidor"] = regras
        _salvar_json_servidor_ativo_locked()
    return dict(normalizada)


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


class EstadoServidorMundo:
    def __init__(self, ctx):
        global _CTX
        _CTX = ctx

    def _normalizar_exploracao_chunks(self, *args, **kwargs):
        return _normalizar_exploracao_chunks(*args, **kwargs)

    def _fingerprint_mundo_atual(self, *args, **kwargs):
        return _fingerprint_mundo_atual(*args, **kwargs)

    def _sincronizar_exploracao_mundo_atual(self, *args, **kwargs):
        return _sincronizar_exploracao_mundo_atual(*args, **kwargs)

    def obter_exploracao_chunks(self, *args, **kwargs):
        return obter_exploracao_chunks(*args, **kwargs)

    def registrar_chunks_explorados(self, *args, **kwargs):
        return registrar_chunks_explorados(*args, **kwargs)

    def _recarregar_mundo(self, *args, **kwargs):
        return _recarregar_mundo(*args, **kwargs)

    def _limites_mundo_atuais(self, *args, **kwargs):
        return _limites_mundo_atuais(*args, **kwargs)

    def _criar_novo_mundo_sync(self, *args, **kwargs):
        return _criar_novo_mundo_sync(*args, **kwargs)

    def _worker_criacao_mundo(self, *args, **kwargs):
        return _worker_criacao_mundo(*args, **kwargs)

    def _apagar_mundo(self, *args, **kwargs):
        return _apagar_mundo(*args, **kwargs)

    def _worker_apagar_mundo(self, *args, **kwargs):
        return _worker_apagar_mundo(*args, **kwargs)

    def obter_config_mundo(self, *args, **kwargs):
        return obter_config_mundo(*args, **kwargs)

    def definir_config_mundo(self, *args, **kwargs):
        return definir_config_mundo(*args, **kwargs)

    def obter_tempo_mundo_estado(self, *args, **kwargs):
        return obter_tempo_mundo_estado(*args, **kwargs)

    def atualizar_tempo_mundo_estado(self, *args, **kwargs):
        return atualizar_tempo_mundo_estado(*args, **kwargs)

    def registrar_estrutura_natural_tocada_estado(self, *args, **kwargs):
        return registrar_estrutura_natural_tocada_estado(*args, **kwargs)

    def carregar_npcs_vendedores_estado(self, *args, **kwargs):
        return carregar_npcs_vendedores_estado(*args, **kwargs)

    def salvar_npcs_vendedores_estado(self, *args, **kwargs):
        return salvar_npcs_vendedores_estado(*args, **kwargs)

    def definir_mundo_existente(self, *args, **kwargs):
        return definir_mundo_existente(*args, **kwargs)
