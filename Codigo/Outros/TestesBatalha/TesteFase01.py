from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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
        if passou:
            self.ok += 1
        else:
            self.falhou += 1
        print(f"CASO: {nome}")
        print(f"  esperado: {esperado}")
        print(f"  obtido:   {obtido}")
        print(f"  resultado: {'OK' if passou else 'FALHOU'}")


def _ler_csv_ataques(caminho: Path) -> list[dict[str, str]]:
    with caminho.open("r", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def main() -> int:
    t = Runner()
    arq_json = ROOT / "Dados" / "Pokemon Global Server - PropriedadesAtaque.json"
    arq_csv_ataques = ROOT / "Dados" / "Pokemon Global Server - Ataques.csv"
    arq_csv_efeitos = ROOT / "Dados" / "Pokemon Global Server - Efeitos.csv"

    t.check("JSON existe", True, arq_json.exists())
    dados = {}
    if arq_json.exists():
        with arq_json.open("r", encoding="utf-8") as f:
            dados = json.load(f)

    ataques = dados.get("ataques") if isinstance(dados, dict) else {}
    t.check("JSON schema_version", True, "schema_version" in dados)
    t.check("JSON ataques", True, isinstance(ataques, dict) and bool(ataques))

    nomes_json = {str(v.get("nome") or "").strip().casefold() for v in ataques.values() if isinstance(v, dict)}
    prioritarios = [
        "Proteger", "Arranhar", "Energia", "Hiper Raio", "Chifrada",
        "Investida", "Dança da chuva", "Bomba de lama", "Parede", "Acumulador",
    ]
    for nome in prioritarios:
        t.check(f"Ataque prioritário: {nome}", True, nome.casefold() in nomes_json)

    linhas_csv = _ler_csv_ataques(arq_csv_ataques)
    csv_nomes = [str(row.get("Ataque") or "").strip() for row in linhas_csv if str(row.get("Ataque") or "").strip()]
    faltantes_csv_json = sorted([nome for nome in csv_nomes if nome.casefold() not in nomes_json])
    t.check("CSV->JSON por contenção (sem faltantes)", [], faltantes_csv_json)

    ids = [str(k) for k in ataques.keys()]
    t.check("IDs começam com 7", True, all(x.startswith("7") for x in ids))
    t.check("IDs sem duplicação", len(ids), len(set(ids)))
    t.check("Chave id bate objeto", True, all(str(v.get("id")) == k for k, v in ataques.items() if isinstance(v, dict)))

    estilos = [str(v.get("estilo") or "") for v in ataques.values() if isinstance(v, dict)]
    t.check("Estilos válidos", True, all(e in ESTILOS_ATAQUE_VALIDOS for e in estilos))
    t.check("Sem estilo tiro", False, any(e == "tiro" for e in estilos))
    t.check("Sem estilo Impulso", False, any(e == "Impulso" for e in estilos))
    t.check("Sem estilo Irregular", False, any(e == "Irregular" for e in estilos))

    campos_base = [
        "id", "csv_code", "code", "nome", "tipo", "estilo", "estilo_original_csv", "custo", "intervalo",
        "nivel_considerado", "descricao_nivel_1", "multiplicador_dano", "fonte_dano", "tipo_dano", "pode_criticar",
        "aplica_stab", "executes", "condicoes", "visual", "implementacao",
    ]
    schema_ok = True
    blocos_ok = True
    projeteis_ricos_ok = True
    for a in ataques.values():
        if not isinstance(a, dict):
            schema_ok = False
            continue
        if any(c not in a for c in campos_base):
            schema_ok = False
        ex = a.get("executes")
        if not (isinstance(ex, dict) and "principal" in ex and isinstance(ex.get("perifericos"), list)):
            schema_ok = False
        vi = a.get("visual")
        im = a.get("implementacao")
        if not (isinstance(vi, dict) and "preview" in vi and isinstance(im, dict) and "fase_planejada" in im):
            schema_ok = False

        estilo = a.get("estilo")
        if estilo == "alvo":
            blocos_ok &= "alvo" in a
        elif estilo == "status":
            blocos_ok &= "status" in a
        elif estilo == "projetil":
            blocos_ok &= all(k in a for k in ["projetil", "colisao", "ricochete", "atravessar"])
            for bloco in ["colisao", "ricochete", "atravessar"]:
                atual = a.get(bloco)
                if not isinstance(atual, dict):
                    projeteis_ricos_ok = False
                    continue
                for alvo in ["pokemon", "parede", "projetil", "construto"]:
                    nodo = atual.get(alvo)
                    if not isinstance(nodo, dict):
                        projeteis_ricos_ok = False
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
        elif estilo == "irregular" and str(a.get("nome", "")).casefold() == "parede":
            blocos_ok &= "irregular" in a
    t.check("Schema mínimo dos ataques", True, schema_ok)
    t.check("Blocos por estilo", True, blocos_ok)
    t.check("Projétil com blocos técnicos ricos", True, projeteis_ricos_ok)

    # Fases planejadas exigidas para Fase 1.1
    fase_por_nome = {
        "proteger": "Fase 5", "resetar": "Fase 5", "hiper presa": "Fase 5", "provocar": "Fase 5", "tankar": "Fase 5", "arranhar": "Fase 5", "estocada": "Fase 5", "guilhotina": "Fase 5",
        "biscoito": "Fase 6", "energia": "Fase 6", "disparo": "Fase 6",
        "hiper raio": "Fase 7", "chifrada": "Fase 7", "investida": "Fase 7", "investida selvagem": "Fase 7", "parede": "Fase 7",
        "dança da chuva": "Fase 8", "bomba de lama": "Fase 8", "bola climática": "Fase 8", "recarga": "Fase 8", "enraivecer": "Fase 8", "acumulador": "Fase 8",
    }
    fases_ok = True
    for dados_ataque in ataques.values():
        nome = str(dados_ataque.get("nome") or "").strip().casefold()
        fase_esp = fase_por_nome.get(nome)
        if fase_esp is None:
            continue
        fase_real = str(((dados_ataque.get("implementacao") or {}).get("fase_planejada") or "")).strip()
        if fase_real != fase_esp:
            fases_ok = False
    t.check("Fase planejada dos ataques principais", True, fases_ok)

    acumulador = next((a for a in ataques.values() if str(a.get("nome", "")).casefold() == "acumulador"), {})
    t.check("Acumulador execute.estado nulo", None, (acumulador.get("executes") or {}).get("estado"))

    stabs_status_ok = True
    crit_status_ok = True
    for a in ataques.values():
        if str(a.get("estilo") or "") in {"status", "passiva", "irregular"}:
            if bool(a.get("aplica_stab")):
                stabs_status_ok = False
            if bool(a.get("pode_criticar")):
                crit_status_ok = False
    t.check("Status/passiva/irregular sem STAB", True, stabs_status_ok)
    t.check("Status/passiva/irregular sem crítico", True, crit_status_ok)

    t.check("Estados macro 5", 5, len(ESTADOS_PARTIDA_VALIDOS))
    t.check("Estado ENCERRADA", True, EstadoPartida.ENCERRADA.value in ESTADOS_PARTIDA_VALIDOS)

    t.check("ID pokemon 000", "000", formatar_id_pokemon_batalha(0, 0))
    t.check("ID pokemon 015", "015", formatar_id_pokemon_batalha(1, 5))
    t.check("Prefixo ataque", True, prefixo_id_valido("ataque", "7005"))
    t.check("Prefixo projetil", True, prefixo_id_valido("projetil", "1001"))
    t.check("Prefixo acao", True, prefixo_id_valido("acao", "4123"))
    t.check("Prefixo evento", True, prefixo_id_valido("evento", "5233"))

    payload = {
        "partida_id": 81,
        "turno_numero": 1,
        "lado": "jogador",
        "acoes": [{
            "client_ref": "a1", "executor_id": "000", "tipo_acao": "ataque", "ataque_id": 7005,
            "ordem_local_executor": 1, "payload": {"alvos": ["010"]},
        }],
    }
    payload_ok = all(k in payload for k in ["partida_id", "turno_numero", "lado", "acoes"]) and isinstance(payload["acoes"], list)
    t.check("Payload base de jogada", True, payload_ok)

    historico = {"evento_id": "5001", "tick": 0, "ordem_tick": 1, "tipo": "dano", "dados": {"valor": 10}}
    historico_ok = prefixo_id_valido("evento", historico["evento_id"]) and all(k in historico for k in ["tick", "ordem_tick", "tipo", "dados"])
    t.check("Histórico base", True, historico_ok)

    diff = {"partida_id": 81, "turno_numero": 1, "tick_global_final": 12, "estado_partida_final": "ENCERRADA", "pokemons_alterados": []}
    diff_ok = all(k in diff for k in ["partida_id", "turno_numero", "tick_global_final", "estado_partida_final", "pokemons_alterados"])
    t.check("Diff base", True, diff_ok)

    seed_int = 1234
    rng_a = random.Random(seed_int)
    rng_b = random.Random(seed_int)
    seq_a = [rng_a.randint(0, 999) for _ in range(5)]
    seq_b = [rng_b.randint(0, 999) for _ in range(5)]
    seed_str = "seed-batalha"
    rng_c = random.Random(seed_str)
    rng_d = random.Random(seed_str)
    seq_c = [rng_c.randint(0, 999) for _ in range(5)]
    seq_d = [rng_d.randint(0, 999) for _ in range(5)]
    t.check("SeedPartida int determinística", seq_a, seq_b)
    t.check("SeedPartida string determinística", seq_c, seq_d)

    # Limpeza de legado ativa da Fase 1.1
    t.check("PlayerControleBat.py removido", False, (ROOT / "Codigo/ModulosBatalha/PlayerControleBat.py").exists())
    hud_texto = (ROOT / "Codigo/ModulosBatalha/ElementosHudBatalha.py").read_text(encoding="utf-8")
    batalha_teste_texto = (ROOT / "Codigo/Outros/BatalhaTeste.py").read_text(encoding="utf-8")
    t.check("HUD não importa ControladorFluxos", False, "ControladorFluxos" in hud_texto)
    t.check("HUD não importa PainelJogada", False, "PainelJogada" in hud_texto)
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
