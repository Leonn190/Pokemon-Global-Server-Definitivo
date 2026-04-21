from __future__ import annotations

import json
from pathlib import Path
import unicodedata

CAMINHO_PADRAO = Path(__file__).resolve().parents[3] / "Dados" / "Pokemon Global Server - AtaquesCombate.json"

FORMAS_PERMITIDAS = {
    "self",
    "alvo",
    "impulso",
    "dash",
    "projetil",
    "projetil_explosivo",
    "cone",
    "cone_invertido",
    "area",
    "laser",
}

TIPOS_PREPARO_PERMITIDOS = {
    "self",
    "alvo",
    "direcao",
    "direcao_intensidade",
    "cone",
    "area",
    "linha",
    "laser",
}

INDICADORES_PREPARO_PERMITIDOS = {
    "self",
    "alvo",
    "direcao",
    "direcao_intensidade",
    "cone",
    "area",
    "linha",
    "laser",
}

EFEITOS_PERMITIDOS = {
    "dano",
    "cura",
    "status",
    "stack",
    "recoil",
    "recoil_se_errar",
    "execucao",
    "remover_variacoes_atributos",
    "recuperar_energia_gasta",
    "barreira",
    "buff_menor_defesa",
    "status_condicional_maior_atributo",
    "adaptar_tipo_clima",
    "bonus_se_clima_ativo",
    "bonus_primeiro_ataque_turno",
    "recuo_se_critico",
    "limite_crc",
}

ATRIBUTOS_PERMITIDOS = {"Atk", "SpA", "Per", "Mag"}
CATEGORIAS_DANO_PERMITIDAS = {"normal", "especial"}
ALVOS_PERMITIDOS = {"usuario", "alvo", "aliados", "inimigos", "ataque"}


_NUMERICOS_COMUNS = {
    "alcance",
    "alcance_max",
    "largura",
    "raio",
    "angulo",
    "intensidade_min",
    "intensidade_max",
    "velocidade_pct",
    "velocidade_tiles_tick",
    "desaceleracao",
    "valor",
    "escala",
    "queda_dano_por_alvo",
    "limite",
    "threshold",
    "percentual",
}


def _normalizar_nome(valor: object) -> str:
    texto = str(valor or "").strip().casefold()
    sem_acentos = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sem_acentos if unicodedata.category(c) != "Mn")


def _is_numero(valor: object) -> bool:
    if isinstance(valor, bool):
        return False
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, str):
        try:
            float(valor)
            return True
        except ValueError:
            return False
    return False


def _validar_numericos(mapa: dict, contexto: str, erros: list[str]) -> None:
    for chave, valor in mapa.items():
        if chave not in _NUMERICOS_COMUNS:
            continue
        if valor is None:
            continue
        if not _is_numero(valor):
            erros.append(f"{contexto}: campo '{chave}' deve ser numérico, recebido {type(valor).__name__}")


def _validar_efeito(efeito: dict, contexto: str, erros: list[str]) -> None:
    tipo = str(efeito.get("tipo") or "").strip()
    if not tipo:
        erros.append(f"{contexto}: efeito sem 'tipo'")
        return
    if tipo not in EFEITOS_PERMITIDOS:
        erros.append(f"{contexto}: tipo de efeito inválido '{tipo}'")

    alvo = efeito.get("alvo")
    if alvo is not None and str(alvo).strip() and str(alvo).strip() not in ALVOS_PERMITIDOS:
        erros.append(f"{contexto}: alvo inválido '{alvo}'")

    _validar_numericos(efeito, contexto, erros)

    if tipo == "dano":
        componentes = efeito.get("componentes")
        if not isinstance(componentes, list) or not componentes:
            erros.append(f"{contexto}: efeito de dano precisa de lista 'componentes'")
            return
        for indice, comp in enumerate(componentes):
            if not isinstance(comp, dict):
                erros.append(f"{contexto}: componente[{indice}] de dano precisa ser objeto")
                continue
            atributo = str(comp.get("atributo") or "").strip()
            categoria = str(comp.get("categoria") or "").strip()
            escala = comp.get("escala")
            if atributo not in ATRIBUTOS_PERMITIDOS:
                erros.append(f"{contexto}: atributo inválido em componente[{indice}] '{atributo}'")
            if categoria not in CATEGORIAS_DANO_PERMITIDAS:
                erros.append(f"{contexto}: categoria inválida em componente[{indice}] '{categoria}'")
            if not _is_numero(escala):
                erros.append(f"{contexto}: escala inválida em componente[{indice}] '{escala}'")


def validar_dados(dados: dict) -> list[str]:
    erros: list[str] = []

    if not isinstance(dados, dict):
        return ["Raiz do arquivo deve ser um objeto JSON."]

    ataques = dados.get("ataques")
    if not isinstance(ataques, dict):
        return ["Campo 'ataques' ausente ou inválido."]

    nomes_normalizados: dict[str, str] = {}

    for nome_chave, ataque in ataques.items():
        contexto = f"Ataque '{nome_chave}'"
        if not isinstance(ataque, dict):
            erros.append(f"{contexto}: definição deve ser objeto")
            continue

        nome = str(ataque.get("nome") or nome_chave or "").strip()
        if not nome:
            erros.append(f"{contexto}: ataque sem nome")
            continue

        nome_norm = _normalizar_nome(nome)
        duplicado = nomes_normalizados.get(nome_norm)
        if duplicado and duplicado != nome:
            erros.append(f"Ataques duplicados após normalização: '{duplicado}' e '{nome}'")
        nomes_normalizados[nome_norm] = nome

        preparo = ataque.get("preparo")
        if not isinstance(preparo, dict):
            erros.append(f"{contexto}: campo 'preparo' ausente ou inválido")
        else:
            tipo_preparo = str(preparo.get("tipo") or "").strip()
            if tipo_preparo and tipo_preparo not in TIPOS_PREPARO_PERMITIDOS:
                erros.append(f"{contexto}: tipo de preparo inválido '{tipo_preparo}'")

            indicador = str(preparo.get("indicador") or "").strip()
            if indicador and indicador not in INDICADORES_PREPARO_PERMITIDOS:
                erros.append(f"{contexto}: indicador de preparo inválido '{indicador}'")
            _validar_numericos(preparo, f"{contexto}.preparo", erros)

        execucao = ataque.get("execucao")
        if not isinstance(execucao, dict):
            erros.append(f"{contexto}: campo 'execucao' ausente ou inválido")
        else:
            forma = str(execucao.get("forma") or "").strip()
            if not forma:
                erros.append(f"{contexto}: execução sem 'forma'")
            elif forma not in FORMAS_PERMITIDAS:
                erros.append(f"{contexto}: forma inválida '{forma}'")
            atinge = execucao.get("atinge")
            if atinge is not None and str(atinge).strip() and str(atinge).strip() not in ALVOS_PERMITIDOS:
                erros.append(f"{contexto}: execução com 'atinge' inválido '{atinge}'")
            _validar_numericos(execucao, f"{contexto}.execucao", erros)

        for campo in ("efeitos_ao_acertar", "efeitos_ao_falhar"):
            efeitos = ataque.get(campo)
            if efeitos is None:
                continue
            if not isinstance(efeitos, list):
                erros.append(f"{contexto}: campo '{campo}' deve ser lista")
                continue
            for indice, efeito in enumerate(efeitos):
                if not isinstance(efeito, dict):
                    erros.append(f"{contexto}: {campo}[{indice}] deve ser objeto")
                    continue
                _validar_efeito(efeito, f"{contexto}.{campo}[{indice}]", erros)

    return erros


def validar_arquivo(caminho: str | Path | None = None) -> list[str]:
    caminho_arquivo = Path(caminho) if caminho else CAMINHO_PADRAO
    try:
        dados = json.loads(caminho_arquivo.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return [f"Arquivo não encontrado: {caminho_arquivo}"]
    except json.JSONDecodeError as exc:
        return [f"JSON inválido em {caminho_arquivo}: {exc}"]

    return validar_dados(dados)
