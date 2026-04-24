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
        self.DiametroTiles = 1.0
        self.RaioColisao = 0.5


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
    t.check("0. caminho do arquivo esta em Outros raiz", str(caminho_esperado), str(Path(__file__).resolve()))
    t.check("0. ROOT correto do projeto", str(ROOT), str(caminho_esperado.parents[2]))
    t.check("0. sem TesteFase02 duplicado em Codigo/Outros", False, (ROOT / "Codigo" / "Outros" / "TestesBatalha" / "TesteFase02.py").exists())

    for i in range(5):
        poke = p1 if i < 2 else p2 if i < 4 else p3
        m.adicionar({"executor": poke, "executor_id": poke.Uid, "ataque": ataque(f"A{i}"), "custo_base": 10})
    t.check("1. aceita ate 5 acoes", 5, len(m.listar()))
    item6, _ = m.adicionar({"executor": p3, "executor_id": p3.Uid, "ataque": ataque("A6"), "custo_base": 10})
    t.check("2. bloqueia 6a", True, item6 is None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("A"), "custo_base": 10})
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("B"), "custo_base": 10})
    item3, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("C"), "custo_base": 10})
    t.check("3. bloqueia terceira por pokemon", True, item3 is None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Arranhar"), "custo_base": 10})
    same, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Arranhar"), "custo_base": 10})
    d2, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    t.check("4. bloqueia repetir ataque", True, same is None)
    t.check("5. permite duas acoes diferentes", True, d2 is not None)

    m.limpar()
    mv, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (4, 4), "custo_base": 5})
    at, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    t.check("6. movimento + ataque permitido", True, mv is not None and at is not None)
    m.limpar()
    m1, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (4, 4), "custo_base": 5})
    m2, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (5, 5), "custo_base": 5})
    t.check("7. movimento+movimento bloqueado", True, m1 is not None and m2 is None)

    m.limpar()
    tr, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "troca_reserva_id": "R1", "custo_base": 0})
    aft, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    pas, _ = m.adicionar({"executor": p2, "executor_id": p2.Uid, "ataque": ataque("Acumulador", "passiva"), "custo_base": 0})
    t.check("8. troca custa 0", 0.0, float((tr or {}).get("custo", -1)))
    t.check("9. troca encerra cadeia", True, aft is None)
    t.check("10. passiva nao preparavel", True, pas is None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Energia"), "custo_base": 10})
    b, _ = m.adicionar({"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Hiper Raio"), "custo_base": 10})
    t.check("11. segunda acao +10%", 11.0, round(float((b or {}).get("custo", 0.0)), 1))
    t.check("12. custo movimento formula oficial", 27.0, round(MontadorJogada.custo_movimento(PokeFake("p", peso=80), (0, 0), (3, 0)), 1))

    m.limpar()
    expensive = {"executor": p1, "executor_id": p1.Uid, "ataque": ataque("Hiper Raio"), "custo_base": 100}
    no_inf, _ = m.adicionar(expensive, energia_disponivel=20, ignorar_custo=False)
    yes_inf, _ = m.adicionar(expensive, energia_disponivel=20, ignorar_custo=True)
    t.check("13. energia infinita nao bloqueia", True, no_inf is None and yes_inf is not None)

    m.limpar()
    m.adicionar({"executor": p1, "executor_id": p1.Uid, "tipo_movimento": True, "destino_mundo": (7, 7), "custo_base": 1})
    ghost = m.posicao_virtual_executor(p1.Uid, {p1.Uid: p1})
    t.check("14. posicao fantasma apos movimento", (7.0, 7.0), ghost)

    estilos = {
        "Proteger": m.estilo_ataque(ataque("Proteger")),
        "Arranhar": m.estilo_ataque(ataque("Arranhar")),
        "Bomba de lama": m.estilo_ataque(ataque("Bomba de lama")),
        "Energia": m.estilo_ataque(ataque("Energia")),
        "Hiper Raio": m.estilo_ataque(ataque("Hiper Raio")),
        "Chifrada": m.estilo_ataque(ataque("Chifrada")),
        "Investida": m.estilo_ataque(ataque("Investida")),
        "Provocar": m.estilo_ataque(ataque("Provocar")),
        "Tankar": m.estilo_ataque(ataque("Tankar")),
        "Parede": m.estilo_ataque(ataque("Parede")),
        "Bola Climática": m.estilo_ataque(ataque("Bola Climática")),
    }
    t.check("15. estilos tecnicos principais", True, estilos == {
        "Proteger": "alvo",
        "Arranhar": "area",
        "Bomba de lama": "zona",
        "Energia": "projetil",
        "Hiper Raio": "laser",
        "Chifrada": "dash",
        "Investida": "impulso",
        "Provocar": "status",
        "Tankar": "status",
        "Parede": "parede",
        "Bola Climática": "explosivo",
    })
    t.check("16. Parede bloqueia ponto >4", False, m.validar_segundo_ponto_parede((0.0, 0.0), (5.2, 0.0), 4.0))

    troca_ok = m.resolver_arrasto_para_jogada(
        executor=p1,
        executor_id=p1.Uid,
        origem_mundo=(1.0, 1.0),
        destino_mundo=(2.0, 24.0),
        dentro_arena=False,
        reserva_id="R1",
        reserva_valida=True,
    )
    t.check("17. arrasto ate reserva valida gera troca", "R1", (troca_ok or {}).get("troca_reserva_id"))
    t.check("18. clique sem arrasto nao cria movimento", False, m.atingiu_limiar_arrasto((100, 100), (106, 106), limiar_px=12.0))

    hud_text = (ROOT / "Codigo" / "ModulosBatalha" / "ElementosHudBatalha.py").read_text(encoding="utf-8")
    t.check("19. HUD sem legado de fluxo", True, all(x not in hud_text for x in ["ControladorFluxos", "PlayerControleBat", "Fluxos.json", "PainelJogada"]))
    t.check("20. HUD delega preview ao montador", True, "construir_preview_ataque" in hud_text and "montar_jogada_de_preview" in hud_text)
    t.check("21. HUD tem rodada fake local", True, "finalizar_rodada_fake" in hud_text and "_contexto_teste_local" in hud_text)

    prop_path = ROOT / "Dados" / "Pokemon Global Server - PropriedadesAtaque.json"
    obj = json.loads(prop_path.read_text(encoding="utf-8"))
    t.check("22. PropriedadesAtaque valido", True, isinstance(obj.get("ataques"), dict))

    fase1_path = ROOT / "Outros" / "TestesBatalha" / "TesteFase01.py"
    spec = importlib.util.spec_from_file_location("TesteFase01", str(fase1_path))
    mod = importlib.util.module_from_spec(spec) if spec is not None else None
    importavel = False
    if spec is not None and spec.loader is not None and mod is not None:
        spec.loader.exec_module(mod)
        importavel = True
    t.check("23. TesteFase01 importavel", True, importavel)

    print("\nRESUMO FINAL")
    print(f"  total de testes: {t.total}")
    print(f"  total OK: {t.ok}")
    print(f"  total FALHOU: {t.falhou}")
    return 0 if t.falhou == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
