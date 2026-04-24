from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SimuladorServerJogo.Batalha.EstadosPartida import (
    ESTILOS_ATAQUE_VALIDOS,
    ESTADOS_PARTIDA_VALIDOS,
    EstadoPartida,
    formatar_id_pokemon_batalha,
    prefixo_id_valido,
)


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


def _ler_csv_ataques(caminho: Path) -> list[dict[str, str]]:
    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def main() -> int:
    t = Runner()
    arq_json = ROOT / "Dados" / "Pokemon Global Server - PropriedadesAtaque.json"
    arq_csv_ataques = ROOT / "Dados" / "Pokemon Global Server - Ataques.csv"
    arq_csv_efeitos = ROOT / "Dados" / "Pokemon Global Server - Efeitos.csv"

    t.check("JSON existe", True, arq_json.exists())
    dados = json.loads(arq_json.read_text(encoding="utf-8")) if arq_json.exists() else {}
    ataques = dados.get("ataques") if isinstance(dados, dict) else {}
    t.check("JSON top-level enxuto", ["ataques"], sorted(dados.keys()))
    t.check("JSON ataques", True, isinstance(ataques, dict) and bool(ataques))

    nomes_json = {str(v.get("nome") or "").strip().casefold() for v in ataques.values() if isinstance(v, dict)}
    prioritarios = [
        "Proteger", "Arranhar", "Energia", "Hiper Raio", "Chifrada",
        "Investida", "Dança da chuva", "Bomba de lama", "Parede", "Acumulador",
    ]
    for nome in prioritarios:
        t.check(f"Ataque prioritario: {nome}", True, nome.casefold() in nomes_json)

    linhas_csv = _ler_csv_ataques(arq_csv_ataques)
    csv_nomes = [str(row.get("Ataque") or "").strip() for row in linhas_csv if str(row.get("Ataque") or "").strip()]
    faltantes_csv_json = sorted([nome for nome in csv_nomes if nome.casefold() not in nomes_json])
    t.check("CSV->JSON por contencao", [], faltantes_csv_json)

    ids = [str(k) for k in ataques.keys()]
    t.check("IDs com prefixo ataque", True, all(x.startswith("7") for x in ids))
    t.check("IDs sem duplicacao", len(ids), len(set(ids)))
    t.check("Chave id bate objeto", True, all(str(v.get("id")) == k for k, v in ataques.items() if isinstance(v, dict)))

    estilos = [str(v.get("estilo") or "") for v in ataques.values() if isinstance(v, dict)]
    t.check("Estilos validos", True, all(e in ESTILOS_ATAQUE_VALIDOS for e in estilos))
    t.check("Sem estilo tiro", False, any(e == "tiro" for e in estilos))
    t.check("Parede usa estilo parede", "parede", next((a.get("estilo") for a in ataques.values() if str(a.get("nome", "")).casefold() == "parede"), None))

    proibidos = {
        "schema_version", "fonte_csv", "nivel_considerado", "observacao", "estilos_validos",
        "estilo_original_csv", "descricao_nivel_1", "implementacao", "fase_planejada",
        "logica_real_implementada", "pendencias", "tipo_dano", "fonte_dano",
    }
    texto_json = arq_json.read_text(encoding="utf-8")
    t.check("Sem metadados proibidos", True, all(p not in texto_json for p in proibidos))
    t.check("Sem status.autouso", False, '"autouso"' in texto_json)

    blocos_ok = True
    for a in ataques.values():
        estilo = str(a.get("estilo") or "")
        if not isinstance(a.get("executes"), dict):
            blocos_ok = False
        if estilo == "alvo":
            blocos_ok &= "alvo" in a
        elif estilo == "status":
            blocos_ok &= "status" in a and "autouso" not in dict(a.get("status") or {})
        elif estilo == "projetil":
            blocos_ok &= "projetil" in a
        elif estilo == "explosivo":
            blocos_ok &= all(k in a for k in ["projetil", "explosivo"]) and isinstance((a.get("explosivo") or {}).get("zona"), dict)
        elif estilo == "area":
            blocos_ok &= "area" in a
        elif estilo == "zona":
            blocos_ok &= "zona" in a
        elif estilo == "laser":
            blocos_ok &= "laser" in a
        elif estilo in {"dash", "impulso"}:
            blocos_ok &= "movimento_ofensivo" in a
        elif estilo == "passiva":
            blocos_ok &= "passiva" in a
        elif estilo == "parede":
            blocos_ok &= "parede" in a
    t.check("Blocos por estilo", True, bool(blocos_ok))

    acumulador = next((a for a in ataques.values() if str(a.get("nome", "")).casefold() == "acumulador"), {})
    t.check("Acumulador execute.estado nulo", None, (acumulador.get("executes") or {}).get("estado"))

    t.check("Estados macro 5", 5, len(ESTADOS_PARTIDA_VALIDOS))
    t.check("Estado ENCERRADA", True, EstadoPartida.ENCERRADA.value in ESTADOS_PARTIDA_VALIDOS)
    t.check("ID pokemon 000", "000", formatar_id_pokemon_batalha(0, 0))
    t.check("ID pokemon 015", "015", formatar_id_pokemon_batalha(1, 5))
    t.check("Prefixo ataque", True, prefixo_id_valido("ataque", "7005"))
    t.check("Prefixo projetil", True, prefixo_id_valido("projetil", "1001"))
    t.check("Prefixo acao", True, prefixo_id_valido("acao", "4123"))
    t.check("Prefixo evento", True, prefixo_id_valido("evento", "5233"))

    rng_a = random.Random("seed-batalha")
    rng_b = random.Random("seed-batalha")
    t.check("SeedPartida deterministica", [rng_a.randint(0, 999) for _ in range(5)], [rng_b.randint(0, 999) for _ in range(5)])

    hud_texto = (ROOT / "Codigo/ModulosBatalha/ElementosHudBatalha.py").read_text(encoding="utf-8")
    batalha_teste_texto = (ROOT / "Outros/BatalhaTeste.py").read_text(encoding="utf-8")
    t.check("PlayerControleBat.py removido", False, (ROOT / "Codigo/ModulosBatalha/PlayerControleBat.py").exists())
    t.check("HUD nao importa ControladorFluxos", False, "ControladorFluxos" in hud_texto)
    t.check("HUD nao importa PainelJogada", False, "PainelJogada" in hud_texto)
    t.check("BatalhaTeste sem Fluxos.json", False, "Fluxos.json" in batalha_teste_texto)
    t.check("BatalhaTeste sem LeitorFluxos", False, "LeitorFluxos" in batalha_teste_texto)
    t.check("BatalhaTeste sem ControladorFluxos", False, "ControladorFluxos" in batalha_teste_texto)
    t.check("CSV ataques preservado", True, arq_csv_ataques.exists())
    t.check("CSV efeitos preservado", True, arq_csv_efeitos.exists())

    print("\nRESUMO FINAL")
    print(f"  total de testes: {t.total}")
    print(f"  total OK: {t.ok}")
    print(f"  total FALHOU: {t.falhou}")
    return 0 if t.falhou == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
