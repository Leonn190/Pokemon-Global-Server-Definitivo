from __future__ import annotations

import copy
from typing import Any

from .ContextoIA import ContextoIA, fnum
from .GeradorAcoesIA import CandidatoIA


class MicroSimulador:
    """Simula uma ação individual usando o fluxo real do servidor.

    A ação é executada em uma cópia da Partida, usando ColetorAcoes/RodadorTurno
    reais. O critério previsao não decide se o execute real será usado; ele decide
    quais camadas do resultado entram no score posteriormente.
    """

    def simular(self, contexto: ContextoIA, candidato: CandidatoIA) -> dict[str, Any]:
        real = self._simular_com_servidor_real(contexto, candidato)
        if real:
            return real
        return self._simular_resumido(contexto, candidato, origem="micro_resumido_fallback")

    def _simular_resumido(self, contexto: ContextoIA, candidato: CandidatoIA, origem: str = "micro_resumido") -> dict[str, Any]:
        est = dict(candidato.estimativa or {})
        resultado: dict[str, Any] = {
            "tipo": candidato.tipo,
            "pokemon_id": candidato.pokemon_id,
            "score_base": float(candidato.score or 0.0),
            "dano_causado": 0.0,
            "dano_aliado": 0.0,
            "cura_feita": 0.0,
            "cura_inimigo": 0.0,
            "barreira_gerada": 0.0,
            "energia_recuperada": 0.0,
            "energia_gasta": float(candidato.custo_base or 0.0),
            "alvos_mortos": [],
            "aliados_mortos": [],
            "aliados_salvos": [],
            "efeitos_positivos": 0,
            "efeitos_negativos": 0,
            "efeitos_removidos": 0,
            "risco_usuario": 0.0,
            "overkill": 0.0,
            "posicionamento_melhor": False,
            "origem": origem,
            "previsao": float(contexto.config.dificuldade.previsao or 0.0),
            "camadas_consideradas": self._camadas_consideradas(contexto),
        }

        if candidato.categoria == "dano":
            dano = float(est.get("melhor_dano") or est.get("dano_total") or 0.0)
            resultado["dano_causado"] = dano
            alvo_id = est.get("alvo_principal_id")
            alvo = contexto.obter_pokemon(alvo_id) if alvo_id else (candidato.alvos[0] if candidato.alvos else None)
            if alvo is not None:
                vida = contexto.vida_atual(alvo)
                if dano >= vida and vida > 0:
                    if contexto.lado(alvo) == contexto.lado_id:
                        resultado["aliados_mortos"].append(contexto.pid(alvo))
                    else:
                        resultado["alvos_mortos"].append(contexto.pid(alvo))
                resultado["overkill"] = max(0.0, dano - vida)
        elif candidato.categoria == "cura":
            cura = float(est.get("cura_total") or 0.0)
            resultado["cura_feita"] = cura
            for alvo in candidato.alvos or [candidato.pokemon]:
                falta = max(0.0, contexto.vida_max(alvo) - contexto.vida_atual(alvo))
                ameaca = contexto.ameacas_por_pokemon.get(contexto.pid(alvo), 0.0)
                if cura >= falta * 0.55 or ameaca > 0:
                    resultado["aliados_salvos"].append(contexto.pid(alvo))
        elif candidato.categoria == "defesa":
            resultado["barreira_gerada"] = float(est.get("barreira_total") or est.get("protecao") or 10.0)
            resultado["efeitos_positivos"] = 1
        elif candidato.categoria == "buff":
            resultado["efeitos_positivos"] = 1
        elif candidato.categoria == "controle":
            resultado["efeitos_negativos"] = 1
        elif candidato.tipo == "troca_reserva":
            resultado["aliados_salvos"] = [candidato.pokemon_id] if contexto.vida_pct(candidato.pokemon) <= 0.35 else []
        elif candidato.tipo == "movimento":
            area = candidato.area_id or ((candidato.acao.get("destino") or {}).get("area_id") if isinstance(candidato.acao.get("destino"), dict) else None)
            if area:
                memoria = getattr(contexto, "memoria_ia", None)
                perigo = float(getattr(memoria, "areas_player", {}).get(str(area), 0) or 0) if memoria is not None else 0.0
                resultado["posicionamento_melhor"] = str(area) not in contexto.areas_miradas and perigo <= 0

        meta = candidato.metadados if isinstance(candidato.metadados, dict) else {}
        riscos = meta.get("riscos") if isinstance(meta.get("riscos"), dict) else {}
        risco_usuario = str(riscos.get("usuario") or "").lower()
        if risco_usuario == "alto":
            resultado["risco_usuario"] = 18.0
        elif risco_usuario in {"medio", "médio"}:
            resultado["risco_usuario"] = 9.0
        elif risco_usuario == "baixo":
            resultado["risco_usuario"] = 3.0
        return resultado

    def _simular_com_servidor_real(self, contexto: ContextoIA, candidato: CandidatoIA) -> dict[str, Any] | None:
        try:
            partida = self._clonar_partida_silenciosa(contexto.partida)
            antes = self._snapshot(partida)
            jogadas = {
                int(contexto.lado_id): {
                    "lado_id": int(contexto.lado_id),
                    "acoes": [candidato.copia_acao()],
                    "modo_teste": False,
                }
            }
            for lado in self._lados_vivos(partida):
                jogadas.setdefault(int(lado), {"lado_id": int(lado), "acoes": [], "modo_teste": False})
            acoes, invalidas = partida.coletor_acoes.coletar(jogadas)
            partida.rodador_turno.rodar(acoes, invalidas)
            depois = self._snapshot(partida)
            return self._resumir_diff(contexto, candidato, antes, depois, invalidas)
        except Exception as exc:
            return {
                **self._simular_resumido(contexto, candidato, origem="micro_real_falhou"),
                "erro": str(exc),
            }

    def _clonar_partida_silenciosa(self, partida):
        clone = copy.deepcopy(partida)
        try:
            clone.registrar_evento_log = lambda *args, **kwargs: None
        except Exception:
            pass
        try:
            clone.avisos = []
        except Exception:
            pass
        return clone

    def _snapshot(self, partida) -> dict[str, dict[str, Any]]:
        saida: dict[str, dict[str, Any]] = {}
        pokemons = list(getattr(partida, "pokemons", []) or [])
        if not pokemons and hasattr(partida, "pokemons_por_id"):
            pokemons = list(getattr(partida, "pokemons_por_id", {}).values())
        for p in pokemons:
            pid = str(getattr(p, "id_batalha", "") or "")
            if not pid:
                continue
            vida_max = fnum(p.obter_atributo("Vida", 1.0), 1.0) if hasattr(p, "obter_atributo") else 1.0
            energia_max = fnum(p.obter_atributo("EneM", 1.0), 1.0) if hasattr(p, "obter_atributo") else 1.0
            saida[pid] = {
                "vida": fnum(getattr(p, "VidaAtual", 0.0), 0.0),
                "vida_max": max(1.0, vida_max),
                "energia": fnum(getattr(p, "EnergiaAtual", 0.0), 0.0),
                "energia_max": max(1.0, energia_max),
                "barreira": fnum(getattr(p, "BarreiraAtual", 0.0), 0.0),
                "vivo": 1.0 if bool(p.esta_vivo() if hasattr(p, "esta_vivo") else getattr(p, "vivo", False)) else 0.0,
                "lado_id": int(getattr(p, "lado_id", 0) or 0),
                "area_id": str(getattr(p, "area_id", "") or ""),
                "ativo": bool(getattr(p, "ativo", False)),
                "reserva": bool(getattr(p, "reserva", False)),
                "efeitos": self._assinatura_efeitos(p),
                "variacoes": dict(getattr(p, "variacoes_permanentes", {}) or {}),
            }
        return saida

    @staticmethod
    def _assinatura_efeitos(pokemon) -> set[str]:
        efeitos = []
        for e in list(getattr(pokemon, "efeitos_formais", []) or []):
            if isinstance(e, dict):
                efeitos.append(str(e.get("code") or e.get("nome") or ""))
        return set(efeitos)

    def _resumir_diff(self, contexto: ContextoIA, candidato: CandidatoIA, antes: dict, depois: dict, invalidas=None) -> dict[str, Any]:
        resultado = self._simular_resumido(contexto, candidato, origem="micro_real")
        resultado.update({
            "dano_causado": 0.0,
            "dano_aliado": 0.0,
            "cura_feita": 0.0,
            "cura_inimigo": 0.0,
            "barreira_gerada": 0.0,
            "energia_recuperada": 0.0,
            "energia_gasta": 0.0,
            "alvos_mortos": [],
            "aliados_mortos": [],
            "efeitos_positivos": 0,
            "efeitos_negativos": 0,
            "efeitos_removidos": 0,
            "overkill": 0.0,
            "acao_invalida": bool(invalidas),
            "invalidas": list(invalidas or []),
        })

        usuario_id = candidato.pokemon_id
        for pid, a in antes.items():
            d = depois.get(pid, a)
            lado = int(a.get("lado_id", -999))
            delta_vida = float(d.get("vida", 0.0)) - float(a.get("vida", 0.0))
            if delta_vida < 0:
                if lado == contexto.lado_id:
                    resultado["dano_aliado"] += abs(delta_vida)
                else:
                    resultado["dano_causado"] += abs(delta_vida)
            elif delta_vida > 0:
                if lado == contexto.lado_id:
                    resultado["cura_feita"] += delta_vida
                else:
                    resultado["cura_inimigo"] += delta_vida

            delta_barreira = float(d.get("barreira", 0.0)) - float(a.get("barreira", 0.0))
            if delta_barreira > 0 and lado == contexto.lado_id:
                resultado["barreira_gerada"] += delta_barreira

            delta_energia = float(d.get("energia", 0.0)) - float(a.get("energia", 0.0))
            if pid == usuario_id and delta_energia < 0:
                resultado["energia_gasta"] += abs(delta_energia)
            elif lado == contexto.lado_id and delta_energia > 0:
                resultado["energia_recuperada"] += delta_energia

            if float(a.get("vivo", 0.0)) > 0 and float(d.get("vivo", 0.0)) <= 0:
                if lado == contexto.lado_id:
                    resultado["aliados_mortos"].append(pid)
                else:
                    resultado["alvos_mortos"].append(pid)

            efeitos_antes = set(a.get("efeitos") or set())
            efeitos_depois = set(d.get("efeitos") or set())
            novos = efeitos_depois - efeitos_antes
            removidos = efeitos_antes - efeitos_depois
            if novos:
                if lado == contexto.lado_id:
                    resultado["efeitos_positivos"] += len(novos)
                else:
                    resultado["efeitos_negativos"] += len(novos)
            resultado["efeitos_removidos"] += len(removidos)

            if str(a.get("area_id") or "") != str(d.get("area_id") or "") and pid == usuario_id:
                destino = str(d.get("area_id") or "")
                memoria = getattr(contexto, "memoria_ia", None)
                perigo = float(getattr(memoria, "areas_player", {}).get(destino, 0) or 0) if memoria is not None else 0.0
                resultado["posicionamento_melhor"] = destino and destino not in contexto.areas_miradas and perigo <= 0

        alvo_id = (candidato.estimativa or {}).get("alvo_principal_id")
        if alvo_id and alvo_id in antes:
            vida_alvo = float(antes[alvo_id].get("vida", 0.0))
            resultado["overkill"] = max(0.0, resultado["dano_causado"] - vida_alvo)
        return resultado

    def _camadas_consideradas(self, contexto: ContextoIA) -> list[str]:
        p = float(contexto.config.dificuldade.previsao or 0.0)
        camadas = ["vida", "dano", "cura"]
        if p >= 0.25:
            camadas.extend(["morte", "overkill"])
        if p >= 0.35:
            camadas.append("energia")
        if p >= 0.45:
            camadas.extend(["barreira", "efeitos"])
        if p >= 0.60:
            camadas.extend(["movimento", "posicionamento"])
        if p >= 0.80:
            camadas.extend(["ordem_real", "estado_completo"])
        return camadas

    def _lados_vivos(self, partida) -> set[int]:
        lados: set[int] = set()
        pokemons = list(getattr(partida, "pokemons", []) or [])
        if not pokemons and hasattr(partida, "pokemons_por_id"):
            pokemons = list(getattr(partida, "pokemons_por_id", {}).values())
        for p in pokemons:
            try:
                vivo = bool(p.esta_vivo()) if hasattr(p, "esta_vivo") else bool(getattr(p, "vivo", False))
                if vivo:
                    lados.add(int(getattr(p, "lado_id", 0) or 0))
            except Exception:
                pass
        return lados
