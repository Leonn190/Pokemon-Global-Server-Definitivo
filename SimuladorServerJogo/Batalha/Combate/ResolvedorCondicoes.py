from __future__ import annotations

from dataclasses import dataclass, field
import unicodedata
from typing import Any


MOMENTO_ANTES_VALIDACAO = "antes_validacao"
MOMENTO_ANTES_ACERTO = "antes_acerto"
MOMENTO_DEPOIS_ACERTO = "depois_acerto"
MOMENTO_ANTES_CRITICO = "antes_critico"
MOMENTO_DEPOIS_CRITICO = "depois_critico"
MOMENTO_ANTES_DANO_BASE = "antes_dano_base"
MOMENTO_DEPOIS_DANO_BASE = "depois_dano_base"
MOMENTO_ANTES_DEFESA = "antes_defesa"
MOMENTO_DEPOIS_DEFESA = "depois_defesa"
MOMENTO_ANTES_DURABILIDADE = "antes_durabilidade"
MOMENTO_DEPOIS_DURABILIDADE = "depois_durabilidade"
MOMENTO_ANTES_BARREIRA = "antes_barreira"
MOMENTO_DEPOIS_BARREIRA = "depois_barreira"
MOMENTO_DEPOIS_DANO_FINAL = "depois_dano_final"
MOMENTO_AO_CAUSAR_DANO = "ao_causar_dano"
MOMENTO_AO_RECEBER_DANO = "ao_receber_dano"
MOMENTO_AO_ERRAR = "ao_errar"
MOMENTO_AO_FALHAR = "ao_falhar"
MOMENTO_AO_APLICAR_EFEITO = "ao_aplicar_efeito"
MOMENTO_AO_TICK = "ao_tick"
MOMENTO_AO_EXPIRAR = "ao_expirar"
MOMENTO_AO_TENTAR_AGIR = "ao_tentar_agir"
MOMENTO_AO_TENTAR_PREPARAR = "ao_tentar_preparar"
MOMENTO_AO_TENTAR_EXECUTAR = "ao_tentar_executar"
MOMENTO_AO_TENTAR_MOVER = "ao_tentar_mover"
MOMENTO_AO_USAR_PASSIVA = "ao_usar_passiva"


@dataclass(slots=True)
class ContextoResolucao:
    usuario: object | None = None
    alvo: object | None = None
    ataque_spec: dict = field(default_factory=dict)
    jogada: dict = field(default_factory=dict)
    resultado_forma: object | None = None
    resultado_dano: object | None = None
    momento: str = ""
    tick: int = 0
    contexto_batalha: dict = field(default_factory=dict)
    dados: dict = field(default_factory=dict)


@dataclass(slots=True)
class Intervencao:
    origem: str = ""
    tipo_origem: str = "passiva"
    momento: str = ""
    prioridade: int = 0
    inteligencia: float = 0.0
    efeito: dict = field(default_factory=dict)
    dados: dict = field(default_factory=dict)


def _norm(valor: object) -> str:
    return str(valor or "").strip().casefold()

def _norm_condicao_tipo(valor: object) -> str:
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _fnum(valor: object, padrao: float = 0.0) -> float:
    try:
        if isinstance(valor, str):
            return float(valor.replace(",", "."))
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


def _obter(obj: object, nome: str, padrao=None):
    if obj is None:
        return padrao
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def atributo(entidade, nome: str, padrao: float = 0.0) -> float:
    if entidade is None:
        return float(padrao)
    if hasattr(entidade, "obter_atributo"):
        try:
            return _fnum(entidade.obter_atributo(nome), padrao)
        except Exception:
            pass
    alias = [nome, nome.upper(), nome.lower(), nome.capitalize(), "Int"]
    if _norm(nome) == "inteligencia":
        alias.extend(["Int", "INT", "inteligencia", "Inteligencia"])
    for chave in alias:
        valor = _obter(entidade, chave, None)
        if valor is not None:
            return _fnum(valor, padrao)
    dados = _obter(entidade, "Dados", {})
    if isinstance(dados, dict):
        for chave in alias:
            if chave in dados:
                return _fnum(dados.get(chave), padrao)
    return float(padrao)


def vida_percentual(entidade) -> float:
    vida = _fnum(_obter(entidade, "VidaAtual", _obter(entidade, "vida_atual", 0.0)), 0.0)
    vida_max = atributo(entidade, "Vida", 1.0)
    return 0.0 if vida_max <= 0 else max(0.0, min(1.0, vida / vida_max))


def efeitos_ativos(entidade) -> list:
    efeitos = _obter(entidade, "Efeitos", _obter(entidade, "efeitos", []))
    return list(efeitos or []) if isinstance(efeitos, (list, tuple)) else []


def possui_efeito(entidade, nome_efeito: str) -> bool:
    alvo = _norm(nome_efeito)
    for efeito in efeitos_ativos(entidade):
        if _norm(_obter(efeito, "nome", "")) == alvo:
            return True
    return False


def normalizar_condicao(condicao) -> dict:
    if condicao is None:
        return {"tipo": "sempre"}
    if isinstance(condicao, str):
        return {"tipo": condicao}
    if isinstance(condicao, dict):
        if "tipo" in condicao:
            return dict(condicao)
        if len(condicao) == 1:
            chave = next(iter(condicao.keys()))
            return {"tipo": chave, "valor": condicao.get(chave)}
        return {"tipo": "composta", **dict(condicao)}
    return {"tipo": "nunca"}


def avaliar_condicao(condicao, contexto: ContextoResolucao) -> bool:
    c = normalizar_condicao(condicao)
    tipo = _norm_condicao_tipo(c.get("tipo"))
    valor = c.get("valor")
    usuario = contexto.usuario
    alvo = contexto.alvo
    dano = contexto.resultado_dano
    jogada = contexto.jogada if isinstance(contexto.jogada, dict) else {}
    clima = _norm((contexto.contexto_batalha or {}).get("clima"))
    ataque_spec = contexto.ataque_spec if isinstance(contexto.ataque_spec, dict) else {}

    if tipo == "sempre":
        return True
    if tipo == "nunca":
        return False
    if tipo == "foicritico":
        return bool(_obter(dano, "foi_critico", False))
    if tipo == "errou":
        return not bool(_obter(dano, "acertou", False))
    if tipo == "acertou":
        return bool(_obter(dano, "acertou", False))
    if tipo == "climaativo":
        alvo_clima = _norm(valor or c.get("clima") or c.get("igual_a"))
        return bool(alvo_clima) and clima == alvo_clima
    if tipo == "primeiroataqueturno":
        return bool(jogada.get("primeiro_ataque_turno", False))
    if tipo in {"vidausuariomenorque", "vidapctmenorque"}:
        return vida_percentual(usuario) < _fnum(valor, _fnum(c.get("limite"), 0.0))
    if tipo == "vidaalvomenorque":
        return vida_percentual(alvo) < _fnum(valor, _fnum(c.get("limite"), 0.0))
    if tipo == "atributousuariomaiorque":
        return atributo(usuario, str(c.get("atributo") or "")) > _fnum(valor, _fnum(c.get("limite"), 0.0))
    if tipo == "atributoalvomaiorque":
        return atributo(alvo, str(c.get("atributo") or "")) > _fnum(valor, _fnum(c.get("limite"), 0.0))
    if tipo == "maioratributousuario":
        a = str(c.get("atributo_a") or "")
        b = str(c.get("atributo_b") or "")
        return atributo(usuario, a) > atributo(usuario, b)
    if tipo == "alvotemefeito":
        return possui_efeito(alvo, str(valor or c.get("efeito") or ""))
    if tipo == "usuariotemefeito":
        return possui_efeito(usuario, str(valor or c.get("efeito") or ""))
    if tipo == "tipoataqueigualtipousuario":
        tipo_ataque = _norm(ataque_spec.get("tipo") or ataque_spec.get("categoria"))
        tipos_usuario = _obter(usuario, "Tipos", _obter(usuario, "tipos", []))
        return tipo_ataque in {_norm(t) for t in list(tipos_usuario or [])}
    if tipo == "danomaiorquezero":
        return _fnum(_obter(dano, "dano_final", 0.0), 0.0) > 0.0
    if tipo == "colisao":
        return bool(contexto.resultado_forma)
    if tipo == "colisaoparede":
        return bool((contexto.dados or {}).get("colisao_parede", False))
    if tipo == "colisaopokemon":
        return bool((contexto.dados or {}).get("colisao_pokemon", False))
    return False


def avaliar_condicoes(condicoes, contexto: ContextoResolucao) -> bool:
    lista = list(condicoes or [])
    if not lista:
        return True
    return all(avaliar_condicao(c, contexto) for c in lista)


def ordenar_intervencoes(intervencoes) -> list[Intervencao]:
    itens: list[Intervencao] = []
    for item in list(intervencoes or []):
        if isinstance(item, Intervencao):
            itens.append(item)
        elif isinstance(item, dict):
            itens.append(Intervencao(**{k: v for k, v in item.items() if k in Intervencao.__dataclass_fields__}))
    return sorted(itens, key=lambda i: (-int(i.prioridade), -float(i.inteligencia), str(i.origem)))


def coletar_intervencoes_passivas(entidade, momento: str, contexto: ContextoResolucao | None = None) -> list[Intervencao]:
    _ = entidade, momento, contexto
    return []


def _pode_por_efeito(pokemon, bloqueios: dict[str, str]) -> tuple[bool, str | None]:
    for efeito, motivo in bloqueios.items():
        if possui_efeito(pokemon, efeito):
            return False, motivo
    return True, None


def pode_agir(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Dormindo": "dormindo", "Congelado": "congelado"})


def pode_preparar_ataque(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Paralisado": "paralisado"})


def pode_executar_ataques_preparados(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Recuo": "recuo"})


def pode_mover(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Enraizado": "enraizado"})


def pode_usar_passivas(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Atordoado": "atordoado"})


def pode_receber_efeito_positivo(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Bloqueado": "bloqueado"})


def pode_receber_efeito_negativo(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Imune": "imune"})


def pode_ser_atacado(pokemon, contexto=None) -> tuple[bool, str | None]:
    _ = contexto
    return _pode_por_efeito(pokemon, {"Protegido": "protegido"})


def efeito_imparavel(pokemon) -> bool:
    return possui_efeito(pokemon, "Imparavel")
