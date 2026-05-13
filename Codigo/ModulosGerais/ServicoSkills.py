from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from Codigo.ModulosGerais.ModuladorRegras import obter_regras_skils


_CACHE_SKILLS: tuple[dict[str, Any], dict[str, "SkillDef"]] | None = None


@dataclass(frozen=True)
class SkillDef:
    id: str
    nome: str
    ramo: str
    grupo: str
    sigla: str
    pais: tuple[str, ...]
    descricao: str
    efeitos: dict[str, Any]
    custo: int = 1


def _normalizar_skill(skill_id: str, dados: dict[str, Any]) -> SkillDef:
    efeitos = dados.get("efeitos") if isinstance(dados.get("efeitos"), dict) else {}
    pais = dados.get("pais") if isinstance(dados.get("pais"), list) else []
    return SkillDef(
        id=str(skill_id),
        nome=str(dados.get("nome") or skill_id),
        ramo=str(dados.get("ramo") or ""),
        grupo=str(dados.get("grupo") or ""),
        sigla=str(dados.get("sigla") or skill_id[:3].upper()),
        pais=tuple(str(p) for p in pais if str(p or "").strip()),
        descricao=str(dados.get("descricao") or ""),
        efeitos=dict(efeitos),
        custo=max(1, int(dados.get("custo", 1) or 1)),
    )


def carregar_definicoes_skills(forcar: bool = False) -> dict[str, SkillDef]:
    global _CACHE_SKILLS
    bruto = obter_regras_skils()
    if _CACHE_SKILLS is None or forcar or _CACHE_SKILLS[0] != bruto:
        skills_raw = bruto.get("skills") if isinstance(bruto.get("skills"), dict) else {}
        skills = {str(sid): _normalizar_skill(str(sid), dados) for sid, dados in skills_raw.items() if isinstance(dados, dict)}
        _CACHE_SKILLS = (bruto, skills)
    return dict(_CACHE_SKILLS[1])


def carregar_regras_skils_brutas() -> dict[str, Any]:
    global _CACHE_SKILLS
    bruto = obter_regras_skils()
    if _CACHE_SKILLS is None or _CACHE_SKILLS[0] != bruto:
        carregar_definicoes_skills()
    return dict(_CACHE_SKILLS[0]) if _CACHE_SKILLS is not None else {}


def listar_skills() -> list[SkillDef]:
    return list(carregar_definicoes_skills().values())


def buscar_skill(skill_id: str) -> SkillDef | None:
    return carregar_definicoes_skills().get(str(skill_id or ""))


def _lista_aprendidas(perfil) -> list[str]:
    if perfil is None:
        return []
    aprendidas = getattr(perfil, "HabilidadesAprendidas", None)
    if isinstance(perfil, dict):
        aprendidas = perfil.get("habilidades_aprendidas", perfil.get("HabilidadesAprendidas", aprendidas))
    if not isinstance(aprendidas, list):
        aprendidas = list(aprendidas or [])
        if not isinstance(perfil, dict):
            setattr(perfil, "HabilidadesAprendidas", aprendidas)
    return [str(v) for v in aprendidas]


def pontos_gastos(perfil) -> int:
    skills = carregar_definicoes_skills()
    return sum(max(1, int(skills.get(sid, SkillDef(sid, sid, "", "", sid, (), "", {})).custo)) for sid in _lista_aprendidas(perfil))


def pontos_disponiveis(perfil) -> int:
    if perfil is None:
        return 0
    nivel = perfil.get("nivel", perfil.get("Nivel", 0)) if isinstance(perfil, dict) else getattr(perfil, "Nivel", 0)
    return max(0, int(nivel or 0) - pontos_gastos(perfil))


def status_skill(perfil, skill_id: str) -> str:
    skill = buscar_skill(skill_id)
    if skill is None:
        return "trancada"
    aprendidas = set(_lista_aprendidas(perfil))
    if skill.id in aprendidas:
        return "aprendida"
    if skill.pais and not any(pai == "root" or pai in aprendidas for pai in skill.pais):
        return "trancada"
    if pontos_disponiveis(perfil) < skill.custo:
        return "sem_ponto"
    return "disponivel"


def _set_perfil(perfil, campo: str, valor: Any) -> None:
    if isinstance(perfil, dict):
        perfil[campo] = valor
        return
    setattr(perfil, campo, valor)


def _get_perfil(perfil, campo: str, padrao: Any = None) -> Any:
    if isinstance(perfil, dict):
        return perfil.get(campo, perfil.get(_camel_para_snake(campo), padrao))
    return getattr(perfil, campo, padrao)


def _camel_para_snake(nome: str) -> str:
    out = []
    for i, ch in enumerate(str(nome or "")):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def aplicar_efeitos_perfil(perfil, skill: SkillDef | str) -> bool:
    skill_def = buscar_skill(skill) if isinstance(skill, str) else skill
    if perfil is None or skill_def is None:
        return False
    stamina_max_anterior = float(_get_perfil(perfil, "StaminaMax", _get_perfil(perfil, "stamina_max", 100.0)) or 100.0)
    for campo, valor in skill_def.efeitos.items():
        _set_perfil(perfil, str(campo), valor)
        snake = _camel_para_snake(str(campo))
        if isinstance(perfil, dict):
            perfil[snake] = valor
    if "StaminaMax" in skill_def.efeitos or "stamina_max" in skill_def.efeitos:
        stamina_max_nova = float(_get_perfil(perfil, "StaminaMax", _get_perfil(perfil, "stamina_max", stamina_max_anterior)) or stamina_max_anterior)
        stamina_atual = float(_get_perfil(perfil, "Stamina", _get_perfil(perfil, "stamina", stamina_max_anterior)) or 0.0)
        ganho = max(0.0, stamina_max_nova - stamina_max_anterior)
        stamina_final = min(stamina_max_nova, max(0.0, stamina_atual + ganho))
        _set_perfil(perfil, "Stamina", stamina_final)
        if isinstance(perfil, dict):
            perfil["stamina"] = stamina_final
    return True


def capacidade_mochila(perfil) -> int | None:
    if bool(_get_perfil(perfil, "MochilaSemLimite", _get_perfil(perfil, "mochila_sem_limite", False))):
        return None
    capacidade = _get_perfil(perfil, "CapacidadeMochila", _get_perfil(perfil, "capacidade_mochila", None))
    if capacidade not in (None, ""):
        return max(1, int(capacidade))
    nivel = max(1, int(_get_perfil(perfil, "NivelMochila", _get_perfil(perfil, "nivel_mochila", 1)) or 1))
    return nivel * 100


def atualizar_sistemas_imediatos(ator) -> None:
    perfil = getattr(ator, "Perfil", None) if ator is not None else None
    inventario = getattr(ator, "Inventario", None) if ator is not None else None
    controle = getattr(ator, "Controle", None) if ator is not None else None
    if perfil is None:
        return
    if inventario is not None:
        capacidade = capacidade_mochila(perfil)
        slots = max(1, int(getattr(perfil, "LimiteSlotsInventario", 32) or 32))
        limite_itens = 0 if capacidade is None else int(capacidade)
        if hasattr(inventario, "definir_limite_itens"):
            inventario.definir_limite_itens(limite_itens)
        else:
            inventario.LimiteItens = limite_itens
        if hasattr(inventario, "definir_limite_slots"):
            inventario.definir_limite_slots(slots)
        else:
            inventario.LimiteSlots = slots
            if hasattr(inventario, "Itens") and isinstance(inventario.Itens, list) and len(inventario.Itens) < slots:
                inventario.Itens.extend([None] * (slots - len(inventario.Itens)))
        inventario.LimitePokemons = int(getattr(perfil, "LimitePokemons", 64) or 64)
        inventario.LimiteTimesPokemon = int(getattr(perfil, "LimiteTimesPokemon", 6) or 6)
        for nome_times in ("TimesPokemon", "TimesPokemons"):
            times = getattr(inventario, nome_times, None)
            if isinstance(times, list):
                while len(times) < inventario.LimiteTimesPokemon:
                    times.append({"Nome": f"Time {len(times) + 1}", "Slots": [None] * 6})
    if controle is not None:
        controle.VelocidadeTiles = float(getattr(perfil, "VelocidadeBaseTiles", getattr(controle, "VelocidadeTiles", 5.0)) or 5.0)


def aprender_skill(perfil, skill_id: str, ator=None) -> bool:
    skill = buscar_skill(skill_id)
    if skill is None or status_skill(perfil, skill_id) != "disponivel":
        return False
    if not aplicar_efeitos_perfil(perfil, skill):
        return False
    if isinstance(perfil, dict):
        aprendidas = [str(v) for v in list(perfil.get("habilidades_aprendidas", perfil.get("HabilidadesAprendidas", [])) or [])]
    else:
        aprendidas = [str(v) for v in list(getattr(perfil, "HabilidadesAprendidas", []) or [])]
    if skill.id not in aprendidas:
        aprendidas.append(skill.id)
    if isinstance(perfil, dict):
        perfil["habilidades_aprendidas"] = aprendidas
        perfil["HabilidadesAprendidas"] = aprendidas
    elif perfil is not None:
        setattr(perfil, "HabilidadesAprendidas", aprendidas)
    if perfil is not None:
        if isinstance(perfil, dict):
            perfil["_habilidades_aprendidas_dirty"] = True
            perfil["_perfil_dirty"] = True
        else:
            setattr(perfil, "_habilidades_aprendidas_dirty", True)
            setattr(perfil, "_perfil_dirty", True)
    if ator is not None:
        atualizar_sistemas_imediatos(ator)
    return True


def stack_efetivo(stack_base: int, nivel_acumulador: int = 0) -> int:
    base = max(1, int(stack_base or 1))
    nivel = max(0, min(2, int(nivel_acumulador or 0)))
    if base == 50:
        return (50, 55, 60)[nivel]
    if base == 10:
        return (10, 12, 15)[nivel]
    return base


def aplicar_ganho_xp_perfil(perfil, quantidade_xp: int) -> int:
    ganho_base = max(0, int(quantidade_xp or 0))
    if perfil is None or ganho_base <= 0:
        return 0
    mult = float(_get_perfil(perfil, "MultiplicadorXpRecebido", _get_perfil(perfil, "multiplicador_xp_recebido", 1.0)) or 1.0)
    ganho = max(0, int(round(ganho_base * max(0.0, mult))))
    taxa = int(_get_perfil(perfil, "RendaPassivaXpTaxa", _get_perfil(perfil, "renda_passiva_xp_taxa", 0)) or 0)
    if taxa > 0 and ganho > 0:
        acumulado = int(_get_perfil(perfil, "RendaPassivaXpAcumulado", _get_perfil(perfil, "renda_passiva_xp_acumulado", 0)) or 0) + ganho
        moedas = 0
        while acumulado >= taxa:
            acumulado -= taxa
            moedas += 1
        _set_perfil(perfil, "RendaPassivaXpAcumulado", acumulado)
        if isinstance(perfil, dict):
            perfil["renda_passiva_xp_acumulado"] = acumulado
            perfil["dinheiro"] = int(perfil.get("dinheiro", perfil.get("Dinheiro", 0)) or 0) + moedas
        else:
            perfil.Dinheiro = int(getattr(perfil, "Dinheiro", 0) or 0) + moedas
    return ganho
