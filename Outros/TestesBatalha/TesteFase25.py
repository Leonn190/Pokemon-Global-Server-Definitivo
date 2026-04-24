from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def _walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _ataque_por_code(ataques: dict, code: str) -> dict:
    return next((a for a in ataques.values() if isinstance(a, dict) and str(a.get("code")) == code), {})


def main() -> int:
    t = Runner()
    prop_path = ROOT / "Dados" / "Pokemon Global Server - PropriedadesAtaque.json"
    dados = json.loads(prop_path.read_text(encoding="utf-8"))
    ataques = dados.get("ataques") if isinstance(dados, dict) else {}

    proibidos = {
        "schema_version", "fonte_csv", "nivel_considerado", "observacao", "estilos_validos",
        "estilo_original_csv", "descricao_nivel_1", "implementacao", "fase_planejada",
        "logica_real_implementada", "pendencias", "tipo_dano", "fonte_dano",
    }
    chaves = {k for k, _ in _walk(dados)}
    t.check("1. JSON sem campos proibidos", set(), proibidos & chaves)
    t.check("1b. JSON sem status/condicoes autouso", False, any(k == "autouso" for k, _ in _walk(dados)))

    parede = _ataque_por_code(ataques, "parede")
    t.check("2. Parede usa estilo parede", "parede", parede.get("estilo"))

    csv_text = (ROOT / "Dados" / "Pokemon Global Server - Ataques.csv").read_text(encoding="utf-8-sig")
    bola_existe = "Bola Climática" in csv_text or "Bola Clim" in csv_text
    bola = _ataque_por_code(ataques, "bola_climatica")
    t.check("3. Bola Climática existe quando CSV tem", bola_existe, bool(bola))
    if bola_existe:
        t.check("3b. Explosivo catalogado", True, bola.get("estilo") == "explosivo" and isinstance(bola.get("projetil"), dict) and isinstance(bola.get("explosivo"), dict) and isinstance((bola.get("explosivo") or {}).get("zona"), dict))

    code = f"import sys; sys.path.insert(0, {str(ROOT)!r}); from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada; m=MontadorJogada(); print(m.estilo_ataque({{'Ataque':'Parede'}}))"
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT / "Outros"), text=True, capture_output=True)
    t.check("4. Montador carrega JSON fora do cwd raiz", "parede", proc.stdout.strip())

    ctrl_text = (ROOT / "Codigo" / "ModulosBatalha" / "ControladorBatalha.py").read_text(encoding="utf-8")
    inicio = ctrl_text.index("    def ponto_dentro_arena")
    fim = ctrl_text.index("    def definir_provedor_reservas", inicio)
    fonte_ponto = ctrl_text[inicio:fim]
    t.check("5. ponto_dentro_arena sem pygame.Rect/collidepoint", True, "collidepoint" not in fonte_ponto and "limites_arena_float" in fonte_ponto)

    ind_text = (ROOT / "Codigo" / "ModulosBatalha" / "IndicadoresAcoes.py").read_text(encoding="utf-8")
    t.check("6. Indicadores sem seta generica", False, "def _seta" in ind_text or "_seta(" in ind_text)
    t.check("7. Impulso concentra a unica seta visual", True, "def _desenhar_seta_impulso" in ind_text and "estilo == \"impulso\"" in ind_text)
    for estilo in ["area", "zona", "laser", "projetil", "parede", "dash", "movimento"]:
        trecho_estilo = (
            f'estilo == "{estilo}"' in ind_text
            or (estilo == "projetil" and '{"projetil", "explosivo"}' in ind_text)
            or (estilo == "movimento" and '{"movimento", "troca"}' in ind_text)
        )
        t.check(f"6.{estilo}. indicador especifico sem seta", True, trecho_estilo and f'{estilo}"' in ind_text)

    hud_text = (ROOT / "Codigo" / "ModulosBatalha" / "ElementosHudBatalha.py").read_text(encoding="utf-8")
    t.check("8. HUD sem blocos pesados por estilo", False, any(f'elif estilo == "{e}"' in hud_text for e in ["projetil", "laser", "area", "zona", "parede"]))
    t.check("9. HUD sem legado antigo", True, all(x not in hud_text for x in ["ControladorFluxos", "LeitorFluxos", "PlayerControleBat", "PainelJogada", "Fluxos.json"]))

    bt_text = (ROOT / "Outros" / "BatalhaTeste.py").read_text(encoding="utf-8")
    lista_fixa = all(nome not in bt_text for nome in ["Bulbasaur", "Charmander", "Squirtle", "Pikachu", "Rattata", "Spearow"])
    t.check("10. BatalhaTeste sem lista fixa preferida", True, lista_fixa and "sortear_especies" in bt_text)
    t.check("11. BatalhaTeste/HUD tem rodada fake", True, "batalha_teste_local" in bt_text and "finalizar_rodada_fake" in hud_text)
    t.check("12. Clique simples no selecionado desseleciona", True, "ja_selecionado" in hud_text and "limpar_selecao" in hud_text and "atingiu_limiar_arrasto" in hud_text)

    construtor = ROOT / "SimuladorServerJogo" / "Batalha" / "ConstrutorAtaquesIrregulares.py"
    construtor_text = construtor.read_text(encoding="utf-8")
    t.check("13. Construtor irregular criado", True, construtor.exists() and all(x in construtor_text for x in ["construir_parede", "construir_explosivo", "normalizar_irregular"]))

    ficha_text = (ROOT / "Codigo" / "Paineis" / "FichaPokemonBatalha.py").read_text(encoding="utf-8")
    t.check("14. Ficha carrega JSON robusto", True, "Path(__file__).resolve().parents[2]" in ficha_text)

    cena_text = (ROOT / "Codigo" / "Cenas" / "CenaCombate.py").read_text(encoding="utf-8")
    bt_text = (ROOT / "Outros" / "BatalhaTeste.py").read_text(encoding="utf-8")
    ordem_cena = cena_text.find("renderizar_arena") < cena_text.find("desenhar_indicadores_campo") < cena_text.find("renderizar_pokemons")
    ordem_teste = bt_text.find("renderizar_arena") < bt_text.find("desenhar_indicadores_campo") < bt_text.find("renderizar_pokemons")
    t.check("15. Indicadores desenham atras dos pokemons", True, ordem_cena and ordem_teste)

    t.check("16. Alvo mostra alcance e status sem circulo", True, 'if estilo == "alvo":\n            self._circulo' in ind_text and 'elif estilo == "status":\n            return' in ind_text)
    montador_text = (ROOT / "Codigo" / "ModulosBatalha" / "MontadorJogada.py").read_text(encoding="utf-8")
    t.check("17. Area preparada preserva forma", True, all(x in montador_text for x in ['"forma": preview.get("forma")', '"base": preview.get("base")', '"teto": preview.get("teto")']))
    t.check("18. Explosivo so mostra zona ao detonar", True, "tipo_impacto in detonadores" in montador_text)
    t.check("19. Parede tem alcance do primeiro ponto", True, '"alcance_primeiro_ponto"' in prop_path.read_text(encoding="utf-8") and "alcance_primeiro" in montador_text)
    areas = [a for a in ataques.values() if isinstance(a, dict) and a.get("estilo") == "area"]
    t.check("20. Areas configuram atravessar parede", True, bool(areas) and all(isinstance(a.get("area"), dict) and a["area"].get("atravessa_parede") is False for a in areas))
    from Codigo.ModulosBatalha.MontadorJogada import MontadorJogada
    rota_multi = MontadorJogada()._simular_rotas_projeteis(
        origem=(0.0, 0.0),
        destino=(8.0, 0.0),
        props={"estilo": "projetil", "projetil": {"raio": 0.2, "alcance": 4.0, "quantidade": 3, "angulo_entre_projeteis": 20}},
    )
    fins_y = {round(float(s["fim"][1]), 3) for s in rota_multi.get("segmentos", []) if isinstance(s, dict)}
    t.check("21. Projetil usa quantidade e angulo", True, len(rota_multi.get("segmentos", [])) == 3 and len(fins_y) == 3)

    print("\nRESUMO FINAL")
    print(f"  total de testes: {t.total}")
    print(f"  total OK: {t.ok}")
    print(f"  total FALHOU: {t.falhou}")
    return 0 if t.falhou == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
