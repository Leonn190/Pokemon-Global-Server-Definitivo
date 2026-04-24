from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada


class Runner:
    def __init__(self) -> None:
        self.total = 0
        self.ok = 0
        self.falhou = 0

    def check(self, nome: str, esperado, obtido) -> None:
        self.total += 1
        passou = esperado == obtido
        self.ok += 1 if passou else 0
        self.falhou += 0 if passou else 1
        print(f"CASO: {nome}")
        print(f"  esperado: {esperado}")
        print(f"  obtido:   {obtido}")
        print(f"  resultado: {'OK' if passou else 'FALHOU'}")


class PokeFake:
    def __init__(self, uid, pos=(0.0, 0.0), energia=999, peso=80, reserva=False, vida=100):
        self.Uid = str(uid)
        self.Posicao = tuple(pos)
        self.Energia = float(energia)
        self.Peso = float(peso)
        self.EmReserva = bool(reserva)
        self.VidaAtual = float(vida)


def ataque(nome: str, estilo: str | None = None):
    d = {"Ataque": nome, "Nome": nome}
    if estilo:
        d["estilo"] = estilo
    return d


def main() -> int:
    t = Runner()
    m = MontadorJogada()
    p1, p2, p3 = PokeFake("001", (1, 1), energia=80), PokeFake("002", (2, 1), energia=80), PokeFake("003", (3, 1), energia=80)
    caminho_esperado = ROOT / "Outros" / "TestesBatalha" / "TesteFase02.py"
    t.check("0. caminho do arquivo está em Outros raiz", str(caminho_esperado), str(Path(__file__).resolve()))
    t.check("0. ROOT correto do projeto", str(ROOT), str(caminho_esperado.parents[2]))
    t.check("0. sem TesteFase02 duplicado em Codigo/Outros", False, (ROOT / "Codigo" / "Outros" / "TestesBatalha" / "TesteFase02.py").exists())

    # 1-4 limites
    for i in range(5):
        m.adicionar({"executor": p1 if i < 2 else p2 if i < 4 else p3, "executor_id": (p1 if i < 2 else p2 if i < 4 else p3).Uid, "ataque": ataque(f"A{i}"), "custo_base": 10})
    t.check("1. aceita até 5 ações", 5, len(m.listar()))
    item6, _ = m.adicionar({"executor": p3, "executor_id": p3.Uid, "ataque": ataque("A6"), "custo_base": 10})
    t.check("2. bloqueia 6ª", True, item6 is None)
    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("A"), "custo_base": 10})
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("B"), "custo_base": 10})
    t.check("3. aceita 2 por pokemon", 2, m.quantidade_executor(p1.Uid))
    item3, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("C"), "custo_base": 10})
    t.check("4. bloqueia 3ª por pokemon", True, item3 is None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Arranhar"), "custo_base": 10})
    same, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Arranhar"), "custo_base": 10})
    t.check("5. bloqueia repetir ataque", True, same is None)
    d2, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    t.check("6. permite duas ações diferentes", True, d2 is not None)

    m.limpar()
    mv, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (4, 4), "custo_base": 5})
    at, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    t.check("7. movimento + ataque permitido", True, mv is not None and at is not None)
    m.limpar()
    a1, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    a2, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Hiper Raio"), "custo_base": 10})
    t.check("8. ataque+ataque diferente permitido", True, a1 is not None and a2 is not None)
    m.limpar()
    m1, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (4, 4), "custo_base": 5})
    m2, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (5, 5), "custo_base": 5})
    t.check("9. movimento+movimento bloqueado", True, m1 is not None and m2 is None)

    m.limpar()
    tr, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "troca_reserva_id": "R1", "custo_base": 0})
    t.check("10. troca custa 0", 0.0, float((tr or {}).get("custo", -1)))
    aft, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    t.check("11. troca encerra cadeia", True, aft is None)
    pas, _ = m.adicionar({"executor": p2, "executor_id": p2.Uid, "ataque": ataque("Acumulador", "passiva"), "custo_base": 0})
    t.check("12. passiva não preparável", True, pas is None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    b, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Hiper Raio"), "custo_base": 10})
    t.check("13. 2ª ação +10%", 11.0, round(float((b or {}).get("custo", 0.0)), 1))
    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    mov2, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (5, 5), "custo_base": 10})
    t.check("14. movimento 2º sem +10%", 10.0, float((mov2 or {}).get("custo", -1)))
    t.check("15. energia reservada soma", 20.0, float(m.custo_reservado(p1.Uid)))

    m.limpar()
    expensive = {"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Hiper Raio"), "custo_base": 100}
    no_inf, _ = m.adicionar(expensive, energia_disponivel=20, ignorar_custo=False)
    yes_inf, _ = m.adicionar(expensive, energia_disponivel=20, ignorar_custo=True)
    t.check("16. energia infinita não bloqueia", True, no_inf is None and yes_inf is not None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (7, 7), "custo_base": 1})
    ghost = m.posicao_virtual_executor(p1.Uid, {p1.Uid: p1})
    t.check("17. posição fantasma após movimento", (7.0, 7.0), ghost)
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Arranhar", "area"), "destino_mundo": (9, 7), "estilo": "area", "custo_base": 1})
    v1, _ = m.resolver_visuais({p1.Uid: p1})
    origem2_antes = v1[1].get("origem_mundo")
    m.remover(v1[0]["id"])
    v2, _ = m.resolver_visuais({p1.Uid: p1})
    origem2_depois = v2[0].get("origem_mundo")
    t.check("18. fantasma recalcula ao remover", True, origem2_antes != origem2_depois)
    t.check("19. resolver visuais retorna origem correta", (1.0, 1.0), origem2_depois)

    estilos = {
        "20": m.estilo_ataque(ataque("Proteger")),
        "21": m.estilo_ataque(ataque("Arranhar")),
        "22": m.estilo_ataque(ataque("Bomba de lama")),
        "23": m.estilo_ataque(ataque("Energia")),
        "24": m.estilo_ataque(ataque("Hiper Raio")),
        "25": m.estilo_ataque(ataque("Chifrada")),
        "26": m.estilo_ataque(ataque("Investida")),
        "27a": m.estilo_ataque(ataque("Provocar")),
        "27b": m.estilo_ataque(ataque("Tankar")),
        "28": m.estilo_ataque(ataque("Parede")),
    }
    t.check("20. Proteger alvo", "alvo", estilos["20"])
    t.check("21. Arranhar area", "area", estilos["21"])
    t.check("22. Bomba de lama zona", "zona", estilos["22"])
    t.check("23. Energia projetil", "projetil", estilos["23"])
    t.check("24. Hiper Raio laser", "laser", estilos["24"])
    t.check("25. Chifrada dash", "dash", estilos["25"])
    t.check("26. Investida impulso", "impulso", estilos["26"])
    t.check("27. Provocar/Tankar status", True, estilos["27a"] == "status" and estilos["27b"] == "status")
    t.check("28. Parede irregular", "irregular", estilos["28"])
    t.check("29. Parede bloqueia ponto >4", False, m.validar_segundo_ponto_parede((0.0, 0.0), (5.2, 0.0), 4.0))

    # Simulação de arrasto (lógica real do montador)
    t.check("30. arrasto dentro arena gera payload movimento", True, isinstance(
        m.resolver_arrasto_para_jogada(
            executor=p1,
            executor_id=p1.Uid,
            origem_mundo=(1.0, 1.0),
            destino_mundo=(10.0, 10.0),
            dentro_arena=True,
            reserva_id=None,
            reserva_valida=False,
        ),
        dict,
    ))
    t.check("31. clique sem arrasto não cria movimento", False, m.atingiu_limiar_arrasto((100, 100), (106, 106), limiar_px=12.0))
    t.check("32. arrasto fora sem reserva não gera ação", None, m.resolver_arrasto_para_jogada(
        executor=p1,
        executor_id=p1.Uid,
        origem_mundo=(1.0, 1.0),
        destino_mundo=(55.0, 10.0),
        dentro_arena=False,
        reserva_id=None,
        reserva_valida=False,
    ))
    reserva_valida = PokeFake("R1", (2, 24), reserva=True, vida=100)
    reserva_invalida = PokeFake("R2", (3, 24), reserva=True, vida=0)
    troca_ok = m.resolver_arrasto_para_jogada(
        executor=p1,
        executor_id=p1.Uid,
        origem_mundo=(1.0, 1.0),
        destino_mundo=reserva_valida.Posicao,
        dentro_arena=False,
        reserva_id=reserva_valida.Uid,
        reserva_valida=bool(reserva_valida.VidaAtual > 0),
    )
    troca_fail = m.resolver_arrasto_para_jogada(
        executor=p1,
        executor_id=p1.Uid,
        origem_mundo=(1.0, 1.0),
        destino_mundo=reserva_invalida.Posicao,
        dentro_arena=False,
        reserva_id=reserva_invalida.Uid,
        reserva_valida=bool(reserva_invalida.VidaAtual > 0),
    )
    t.check("33. arrasto até reserva válida gera troca", "R1", (troca_ok or {}).get("troca_reserva_id"))
    t.check("34. arrasto até reserva inválida não gera troca", None, troca_fail)

    hud_text = (ROOT / "Codigo" / "ModulosBatalha" / "ElementosHudBatalha.py").read_text(encoding="utf-8")
    t.check("35. sem import obrigatório ControladorFluxos", False, "ControladorFluxos" in hud_text)
    t.check("36. sem import obrigatório PlayerControleBat", False, "PlayerControleBat" in hud_text)
    t.check("37. sem dependência central Fluxos.json", False, "Fluxos.json" in hud_text)
    t.check("38. painel bloqueado em interação travada", True, "if not interacao_bloqueada:" in hud_text and "_painel_jogada.processar_eventos" in hud_text)
    ctrl_text = (ROOT / "Codigo" / "ModulosBatalha" / "ControladorBatalha.py").read_text(encoding="utf-8")
    t.check("39. mapa_pokemons existe", True, "def mapa_pokemons" in ctrl_text)
    t.check("40. HUD usa mapa_pokemons sem crash", True, "self._controlador.mapa_pokemons()" in hud_text)
    t.check("40. impulso calcula intensidade", True, "elif estilo == \"impulso\":" in hud_text and "prev[\"intensidade\"]" in hud_text)
    t.check("40. dash/impulso limitam distancia_max", True, "if distancia > max_dist:" in hud_text and "fator = max_dist / distancia" in hud_text)
    fase1_path = ROOT / "Outros" / "TestesBatalha" / "TesteFase01.py"
    importavel = False
    if fase1_path.exists():
        spec = importlib.util.spec_from_file_location("TesteFase01", str(fase1_path))
        mod = importlib.util.module_from_spec(spec) if spec is not None else None
        if spec is not None and spec.loader is not None and mod is not None:
            spec.loader.exec_module(mod)
            importavel = True
    t.check("41. TesteFase01 importável", True, importavel)

    prop_path = ROOT / "Dados" / "Pokemon Global Server - PropriedadesAtaque.json"
    ok_json = False
    if prop_path.exists():
        try:
            obj = json.loads(prop_path.read_text(encoding="utf-8"))
            ok_json = isinstance(obj.get("ataques"), dict)
        except Exception:
            ok_json = False
    t.check("42. PropriedadesAtaque válido", True, ok_json)

    print("\nRESUMO FINAL")
    print(f"  total de testes: {t.total}")
    print(f"  total OK: {t.ok}")
    print(f"  total FALHOU: {t.falhou}")
    return 0 if t.falhou == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
