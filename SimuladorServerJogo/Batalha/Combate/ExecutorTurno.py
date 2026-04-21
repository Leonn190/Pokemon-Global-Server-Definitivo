from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from SimuladorServerJogo.Batalha.Combate.AplicadorEfeitos import AplicadorEfeitos
from SimuladorServerJogo.Batalha.Combate.CalculadorDano import calcular_dano_colisao, calcular_dano_por_efeito
from SimuladorServerJogo.Batalha.Combate.CatalogoAtaques import carregar_catalogo_ataques
from SimuladorServerJogo.Batalha.Combate.FormasAtaque import ResolvedorFormasAtaque
from SimuladorServerJogo.Batalha.Combate.LogCombate import LogCombate, comparar_snapshots, snapshot_batalha
from SimuladorServerJogo.Batalha.Combate.ObjetosCombate import criar_corpos_de_pokemons
from SimuladorServerJogo.Batalha.Combate.OrdenadorJogadas import OrdenadorJogadas
from SimuladorServerJogo.Batalha.Combate.ResolvedorCondicoes import (
    ContextoResolucao,
    MOMENTO_AO_APLICAR_EFEITO,
    MOMENTO_AO_FALHAR,
    MOMENTO_AO_TENTAR_AGIR,
    MOMENTO_AO_TENTAR_EXECUTAR,
    MOMENTO_AO_TENTAR_MOVER,
    MOMENTO_AO_TENTAR_PREPARAR,
    avaliar_condicao,
    avaliar_condicoes,
    pode_agir,
    pode_executar_ataques_preparados,
    pode_mover,
    pode_preparar_ataque,
    pode_ser_atacado,
)


class ExecutorTurno:
    def __init__(self, catalogo=None, ordenador=None, resolvedor_formas=None, aplicador_efeitos=None):
        self.catalogo = catalogo or carregar_catalogo_ataques()
        self.ordenador = ordenador or OrdenadorJogadas()
        self.resolvedor_formas = resolvedor_formas or ResolvedorFormasAtaque()
        self.aplicador_efeitos = aplicador_efeitos or AplicadorEfeitos()

    def executar_turno(self, sistema, client_id=None, jogadas=None) -> dict:
        recebidas = [dict(item) for item in list(jogadas or []) if isinstance(item, dict)]
        sistema.adicionar_jogadas(str(client_id or ""), recebidas)
        status_coleta, jogadas_turno = sistema.coletar_jogadas_pendentes_turno(str(client_id or ""))
        if status_coleta != "pronto":
            return {"status": status_coleta, "mensagem": "Aguardando jogadas dos outros participantes"}

        log = LogCombate(rodada=int(getattr(sistema, "TurnoAtual", 1)), tick=int(getattr(sistema, "TickGlobal", 0)))
        pokemons_ativos = self.obter_pokemons_ativos(sistema)
        mapa = self.mapear_pokemons_por_id(sistema)
        contexto_batalha = self.obter_contexto_batalha(sistema)
        antes = snapshot_batalha(pokemons_ativos)

        normalizadas = self._normalizar_jogadas(jogadas_turno, mapa, log)
        ordenadas = self.ordenador.ordenar(normalizadas, contexto=contexto_batalha)
        for item in ordenadas:
            log.adicionar_sumario("jogada_ordenada", **dict(item.get("dados_ordenacao") or {}), ataque=str(item.get("ataque_nome") or ""), custo=float(item.get("custo", 0.0)))

        eventos: list[dict[str, Any]] = []
        for jogada in ordenadas:
            executor = mapa.get(str(jogada.get("executor_id") or ""))
            if executor is None:
                continue
            bloqueada, motivo = self._validar_bloqueios(executor, jogada)
            if bloqueada:
                log.adicionar_sumario("jogada_cancelada", executor_id=executor.Uid, motivo=motivo)
                log.adicionar_historico("acao_cancelada", executor_id=executor.Uid, ataque=jogada.get("ataque_nome"), motivo=motivo)
                continue
            self._gastar_energia(executor, jogada, log)
            log.adicionar_historico("acao_iniciada", executor_id=executor.Uid, ataque=jogada.get("ataque_nome"), forma=jogada.get("forma"))

            corpos = criar_corpos_de_pokemons(pokemons_ativos)
            spec = jogada.get("spec") if isinstance(jogada.get("spec"), dict) else {}
            resultado_forma = self.resolvedor_formas.resolver(spec, jogada, executor, corpos, contexto=contexto_batalha)
            log.adicionar_historico("forma_resolvida", executor_id=executor.Uid, ataque=jogada.get("ataque_nome"), forma=jogada.get("forma"), impactos=len(resultado_forma.impactos), eventos_colisao=len(resultado_forma.eventos))

            alvos = self._resolver_alvos(jogada, resultado_forma, mapa)
            houve_dano_tentado = False
            houve_dano_com_acerto = False
            for alvo in alvos:
                log.adicionar_historico("alvo_detectado", executor_id=executor.Uid, alvo_id=alvo.Uid, ataque=jogada.get("ataque_nome"))

                eventos_colisao = [e for e in resultado_forma.eventos if str(getattr(e, "alvo_id", "") or "") == alvo.Uid]
                for colisao in eventos_colisao:
                    log.adicionar_historico("colisao_detectada", executor_id=executor.Uid, alvo_id=alvo.Uid, tipo=str(getattr(colisao, "tipo", "")))
                    dano_colisao = calcular_dano_colisao(executor, alvo, colisao, contexto=contexto_batalha)
                    aplicacao_colisao = self.aplicador_efeitos.aplicar_resultado_dano(dano_colisao, {"atacante": executor, "alvo": alvo})
                    eventos.append({"tipo": "dano_colisao", "executor_id": executor.Uid, "alvo_id": alvo.Uid, "valor": float(dano_colisao.dano_vida)})
                    log.adicionar_historico("dano_colisao_aplicado", executor_id=executor.Uid, alvo_id=alvo.Uid, dano=float(dano_colisao.dano_vida), aplicado=bool(aplicacao_colisao.aplicado))

                resumo_alvo = self._aplicar_efeitos_da_jogada(executor, alvo, jogada, resultado_forma, contexto_batalha, log, eventos)
                houve_dano_tentado = houve_dano_tentado or bool(resumo_alvo.get("houve_dano_tentado"))
                houve_dano_com_acerto = houve_dano_com_acerto or bool(resumo_alvo.get("houve_dano_com_acerto"))

            if not alvos:
                self._aplicar_efeitos_falha(executor, jogada, resultado_forma, contexto_batalha, log, eventos, motivo="sem_alvo")
            elif houve_dano_tentado and not houve_dano_com_acerto:
                self._aplicar_efeitos_falha(executor, jogada, resultado_forma, contexto_batalha, log, eventos, motivo="dano_errou")

        eventos_tick = self.aplicador_efeitos.atualizar_efeitos_por_tick(pokemons_ativos, contexto=contexto_batalha, ticks=1)
        for evento_tick in eventos_tick:
            log.adicionar_historico("efeito_por_tick", **dict(evento_tick))
            eventos.append(dict(evento_tick))

        for pokemon in pokemons_ativos:
            if float(getattr(pokemon, "VidaAtual", 0.0) or 0.0) <= 0.0:
                setattr(pokemon, "ForaDeCombate", True)
        estado_encerramento = sistema.detectar_encerramento()
        if bool(estado_encerramento.get("encerrada")):
            sistema.finalizar_batalha(rodadas_totais=int(getattr(sistema, "TurnoAtual", 1)))

        depois = snapshot_batalha(pokemons_ativos)
        diff = comparar_snapshots(antes, depois)
        log.adicionar_resultado("snapshot", antes=antes, depois=depois, diferencas=diff)
        for pokemon_id, delta in dict(diff.get("pokemons") or {}).items():
            log.adicionar_resultado("pokemon", pokemon_id=pokemon_id, **delta)

        ultimo_tick = int(getattr(sistema, "TickGlobal", 0)) + 1
        sistema.avancar_turno(log.como_dict(), tick_global_final=ultimo_tick)
        return {
            "status": "finalizada" if bool(getattr(sistema, "Encerrada", False)) else "ok",
            "rodada": int(getattr(sistema, "TurnoAtual", 1)) - (0 if bool(getattr(sistema, "Encerrada", False)) else 1),
            "tick": ultimo_tick,
            "log": log.como_dict(),
            "eventos": eventos,
            "batalha": sistema.snapshot(),
        }

    def obter_pokemons_ativos(self, sistema) -> list:
        return [p for p in list(sistema.listar_ativos()) if p is not None and not bool(getattr(p, "ForaDeCombate", False))]

    def mapear_pokemons_por_id(self, sistema) -> dict[str, Any]:
        return {str(getattr(p, "Uid", "") or ""): p for p in list(sistema.listar_pokemons())}

    def obter_contexto_batalha(self, sistema) -> dict[str, Any]:
        return {
            "turno": int(getattr(sistema, "TurnoAtual", 1)),
            "tick": int(getattr(sistema, "TickGlobal", 0)),
            "clima": str(getattr(sistema, "ClimaAtual", "") or ""),
            "rng": getattr(sistema, "Rng", None),
        }

    def _normalizar_jogadas(self, jogadas, mapa_pokemons, log: LogCombate) -> list[dict[str, Any]]:
        saida: list[dict[str, Any]] = []
        for indice, bruto in enumerate(list(jogadas or [])):
            executor_id = str(bruto.get("executor_id") or bruto.get("executor") or "")
            executor = mapa_pokemons.get(executor_id)
            if executor is None:
                log.adicionar_alerta("jogada_sem_executor", indice=indice, executor_id=executor_id)
                continue
            ataque_nome = self._extrair_nome_ataque(bruto)
            spec_obj = self.catalogo.obter(ataque_nome)
            if spec_obj is None:
                log.adicionar_sumario("jogada_ignorada", executor_id=executor_id, ataque=ataque_nome, motivo="ataque_nao_encontrado")
                continue
            spec = self._spec_em_dict(spec_obj)
            custo_base = float(bruto.get("custo") or bruto.get("custo_base") or spec.get("custo", 0.0) or 0.0)
            if self._tem_efeito(executor, "Encharcado"):
                custo_base *= 1.2
            jogada = {
                "id": bruto.get("id", indice),
                "indice_entrada": indice,
                "executor_id": executor.Uid,
                "ataque_nome": str(spec.get("nome") or ataque_nome),
                "ataque_id": str(bruto.get("ataque_id") or spec.get("id") or ""),
                "tipo_preparo": str(bruto.get("tipo_preparo") or self._obter(spec, "preparo", "tipo") or ""),
                "forma": str(bruto.get("forma") or self._obter(spec, "execucao", "forma") or ""),
                "origem_mundo": bruto.get("origem_mundo") or list(getattr(executor, "Posicao", (0.0, 0.0))),
                "destino_mundo": bruto.get("destino_mundo") or bruto.get("alvo_mundo") or bruto.get("origem_mundo"),
                "alvo_ids": [str(v) for v in list(bruto.get("alvo_ids") or bruto.get("alvos") or [])],
                "intensidade": float(bruto.get("intensidade") or 1.0),
                "custo": float(custo_base),
                "prioridade": int(float(bruto.get("prioridade") or 0)),
                "inteligencia": float(getattr(executor, "obter_atributo")("Int") if hasattr(executor, "obter_atributo") else 0.0),
                "velocidade": float(getattr(executor, "obter_atributo")("Vel") if hasattr(executor, "obter_atributo") else 0.0),
                "spec": spec,
            }
            if float(getattr(executor, "Energia", 0.0) or 0.0) < float(jogada["custo"]):
                log.adicionar_sumario("jogada_ignorada", executor_id=executor.Uid, ataque=jogada["ataque_nome"], motivo="energia_insuficiente", custo=jogada["custo"], energia=float(getattr(executor, "Energia", 0.0)))
                continue
            saida.append(jogada)
        return saida

    def _validar_bloqueios(self, executor, jogada: dict[str, Any]) -> tuple[bool, str | None]:
        checks = [
            (MOMENTO_AO_TENTAR_AGIR, pode_agir),
            (MOMENTO_AO_TENTAR_PREPARAR, pode_preparar_ataque),
            (MOMENTO_AO_TENTAR_EXECUTAR, pode_executar_ataques_preparados),
        ]
        forma = str(jogada.get("forma") or "")
        if forma in {"dash", "impulso"}:
            checks.append((MOMENTO_AO_TENTAR_MOVER, pode_mover))
        for momento, fn in checks:
            ok, motivo = fn(executor)
            if not ok:
                return True, f"{momento}:{motivo}"
        return False, None

    def _resolver_alvos(self, jogada: dict[str, Any], resultado_forma, mapa) -> list:
        forma = str(jogada.get("forma") or "")
        executor_id = str(jogada.get("executor_id") or "")
        alvo_ids: list[str] = []
        if forma == "self":
            alvo_ids = [executor_id]
        elif forma == "alvo" and jogada.get("alvo_ids"):
            alvo_ids = [str(v) for v in list(jogada.get("alvo_ids") or [])]
        else:
            alvo_ids = [str(getattr(e, "alvo_id", "") or "") for e in list(getattr(resultado_forma, "eventos", []) or []) if str(getattr(e, "alvo_id", "") or "")]
        unicos = []
        vistos = set()
        for alvo_id in alvo_ids:
            permitir_self = forma == "self"
            if alvo_id and alvo_id not in vistos and alvo_id in mapa and (permitir_self or alvo_id != executor_id):
                vistos.add(alvo_id)
                unicos.append(mapa[alvo_id])
        return unicos

    def _aplicar_efeitos_da_jogada(self, executor, alvo, jogada, resultado_forma, contexto_batalha, log, eventos):
        houve_dano_tentado = False
        houve_dano_com_acerto = False
        dano_causado_total = 0.0
        efeitos = list(self._obter(jogada.get("spec") or {}, "efeitos_ao_acertar") or [])
        for efeito in efeitos:
            efeito_dict = self._obj_para_dict(efeito)
            contexto = ContextoResolucao(
                usuario=executor,
                alvo=alvo,
                ataque_spec=dict(jogada.get("spec") or {}),
                jogada=dict(jogada),
                resultado_forma=resultado_forma,
                momento=MOMENTO_AO_APLICAR_EFEITO,
                contexto_batalha=contexto_batalha,
                dados={"colisao_pokemon": True},
            )
            if efeito_dict.get("momento") and str(efeito_dict.get("momento")) != MOMENTO_AO_APLICAR_EFEITO:
                continue
            if efeito_dict.get("condicao") and not avaliar_condicao(efeito_dict.get("condicao"), contexto):
                continue
            if efeito_dict.get("condicoes") and not avaliar_condicoes(efeito_dict.get("condicoes"), contexto):
                continue

            alvo_efeito = str(efeito_dict.get("alvo") or "alvo")
            if alvo_efeito in {"self", "usuario"}:
                alvo_aplicacao = executor
            elif alvo_efeito in {"todos", "ambos"}:
                alvo_aplicacao = alvo
            else:
                alvo_aplicacao = alvo

            if self._efeito_eh_hostil(efeito_dict, executor=executor, alvo=alvo_aplicacao):
                pode_receber, motivo_receber = pode_ser_atacado(alvo_aplicacao, contexto_batalha)
                if not pode_receber:
                    log.adicionar_historico("status_bloqueado", executor_id=executor.Uid, alvo_id=getattr(alvo_aplicacao, "Uid", ""), tipo_efeito=str(efeito_dict.get("tipo") or ""), motivo=motivo_receber)
                    continue

            contexto_aplicacao = {
                "atacante": executor,
                "aplicador": executor,
                "usuario": executor,
                "alvo": alvo_aplicacao,
                "defensor": alvo_aplicacao,
                "ataque_spec": dict(jogada.get("spec") or {}),
                "jogada": dict(jogada),
                "contexto_batalha": contexto_batalha,
                "momento": MOMENTO_AO_APLICAR_EFEITO,
                "resultado_forma": resultado_forma,
                "dano_causado": float(dano_causado_total),
                "acertou": True,
            }

            tipo_efeito = str(efeito_dict.get("tipo") or "").strip().casefold()
            if tipo_efeito == "dano":
                houve_dano_tentado = True
                resultado_dano = calcular_dano_por_efeito(
                    atacante=executor,
                    defensor=alvo_aplicacao,
                    efeito=efeito_dict,
                    ataque_spec=dict(jogada.get("spec") or {}),
                    contexto=contexto_aplicacao,
                )
                resultado = self.aplicador_efeitos.aplicar_resultado_dano(resultado_dano, contexto_aplicacao)
                contexto_aplicacao["acertou"] = bool(getattr(resultado_dano, "acertou", True))
                dano_causado = float((resultado.dados or {}).get("dano_aplicado", getattr(resultado_dano, "dano_vida", 0.0)) or 0.0)
                dano_causado_total += dano_causado
                contexto_aplicacao["dano_causado"] = dano_causado
                houve_dano_com_acerto = houve_dano_com_acerto or bool(getattr(resultado_dano, "acertou", True))
                log.adicionar_historico(
                    "dano_aplicado",
                    executor_id=executor.Uid,
                    alvo_id=getattr(alvo_aplicacao, "Uid", ""),
                    dano_base=float(getattr(resultado_dano, "dano_base", 0.0) or 0.0),
                    dano_final=float(getattr(resultado_dano, "dano_final", 0.0) or 0.0),
                    dano_vida=float(getattr(resultado_dano, "dano_vida", 0.0) or 0.0),
                    dano_barreira=float(getattr(resultado_dano, "dano_barreira", 0.0) or 0.0),
                    critico=bool(getattr(resultado_dano, "foi_critico", False)),
                    bloqueado_por_barreira=bool(getattr(resultado_dano, "bloqueado_por_barreira", False)),
                    multiplicador_critico=float(getattr(resultado_dano, "multiplicador_critico", 1.0) or 1.0),
                )
            else:
                resultado = self.aplicador_efeitos.aplicar_efeito(efeito_dict, contexto_aplicacao)

            log.adicionar_historico(
                "impacto_resolvido",
                executor_id=executor.Uid,
                alvo_id=getattr(alvo_aplicacao, "Uid", ""),
                tipo_efeito=str(efeito_dict.get("tipo") or ""),
                aplicado=bool(resultado.aplicado),
                motivo=resultado.motivo,
            )
            if bool(resultado.aplicado):
                eventos.append(
                    {
                        "tipo": "efeito_aplicado",
                        "executor_id": executor.Uid,
                        "alvo_id": getattr(alvo_aplicacao, "Uid", ""),
                        "efeito": str(efeito_dict.get("tipo") or ""),
                    }
                )
            else:
                log.adicionar_historico("efeito_falhou", executor_id=executor.Uid, alvo_id=getattr(alvo_aplicacao, "Uid", ""), tipo_efeito=str(efeito_dict.get("tipo") or ""), momento=MOMENTO_AO_FALHAR, motivo=resultado.motivo)
            self._registrar_eventos_aplicacao(log, eventos, executor, alvo_aplicacao, efeito_dict, resultado)
        return {"houve_dano_tentado": houve_dano_tentado, "houve_dano_com_acerto": houve_dano_com_acerto}

    def _aplicar_efeitos_falha(self, executor, jogada, resultado_forma, contexto_batalha, log, eventos, motivo: str) -> None:
        efeitos_falha = list(self._obter(jogada.get("spec") or {}, "efeitos_ao_falhar") or [])
        if not efeitos_falha:
            return
        log.adicionar_historico("acao_falhou", executor_id=executor.Uid, ataque=jogada.get("ataque_nome"), motivo=motivo)
        for efeito in efeitos_falha:
            efeito_dict = self._obj_para_dict(efeito)
            resultado = self.aplicador_efeitos.aplicar_efeito(
                efeito_dict,
                {
                    "atacante": executor,
                    "aplicador": executor,
                    "usuario": executor,
                    "alvo": executor,
                    "defensor": executor,
                    "ataque_spec": dict(jogada.get("spec") or {}),
                    "jogada": dict(jogada),
                    "contexto_batalha": contexto_batalha,
                    "momento": MOMENTO_AO_FALHAR,
                    "resultado_forma": resultado_forma,
                    "acertou": False,
                    "dano_causado": 0.0,
                },
            )
            log.adicionar_historico("efeito_falha_aplicado", executor_id=executor.Uid, tipo_efeito=str(efeito_dict.get("tipo") or ""), aplicado=bool(resultado.aplicado), motivo_resultado=resultado.motivo)
            self._registrar_eventos_aplicacao(log, eventos, executor, executor, efeito_dict, resultado)

    def _gastar_energia(self, executor, jogada, log: LogCombate) -> None:
        custo = float(jogada.get("custo") or 0.0)
        energia = float(getattr(executor, "Energia", 0.0) or 0.0)
        nova = max(0.0, energia - custo)
        setattr(executor, "Energia", nova)
        log.adicionar_historico("energia_gasta", executor_id=executor.Uid, custo=custo, energia_antes=energia, energia_depois=nova)

    @staticmethod
    def _spec_em_dict(spec) -> dict[str, Any]:
        bruto = getattr(spec, "bruto", None)
        if isinstance(bruto, dict) and bruto:
            return dict(bruto)
        if is_dataclass(spec):
            return asdict(spec)
        if isinstance(spec, dict):
            return dict(spec)
        return {}

    @staticmethod
    def _obj_para_dict(valor: object) -> dict[str, Any]:
        if isinstance(valor, dict):
            return dict(valor)
        if is_dataclass(valor):
            return asdict(valor)
        return {}

    @staticmethod
    def _obter(dados: dict[str, Any], secao: str, chave: str | None = None) -> Any:
        bloco = dados.get(secao) if isinstance(dados.get(secao), dict) else {}
        if chave is None:
            return bloco
        return bloco.get(chave)

    @staticmethod
    def _tem_efeito(pokemon, nome: str) -> bool:
        alvo = str(nome or "").strip().casefold()
        for efeito in list(getattr(pokemon, "Efeitos", []) or []):
            if str((efeito or {}).get("nome") or "").strip().casefold() == alvo:
                return True
        return False

    @staticmethod
    def _extrair_nome_ataque(bruto: dict[str, Any]) -> str:
        ataque_bruto = bruto.get("ataque")
        if isinstance(ataque_bruto, dict):
            for chave in ("Ataque", "Nome", "nome", "ataque"):
                nome = str(ataque_bruto.get(chave) or "").strip()
                if nome:
                    return nome
        if isinstance(ataque_bruto, str) and ataque_bruto.strip():
            return ataque_bruto.strip()
        for chave in ("ataque_id", "habilidade"):
            nome = str(bruto.get(chave) or "").strip()
            if nome:
                return nome
        return ""

    def _efeito_eh_hostil(self, efeito_dict: dict[str, Any], executor=None, alvo=None) -> bool:
        tipo = str(efeito_dict.get("tipo") or "").strip().casefold()
        if tipo in {"dano", "execucao"}:
            return True
        if tipo == "recoil" and executor is not None and alvo is not None and str(getattr(executor, "Lado", "")) != str(getattr(alvo, "Lado", "")):
            return True
        if tipo in {"status", "stack"} and executor is not None and alvo is not None:
            status_nome = str(efeito_dict.get("status") or efeito_dict.get("nome") or "").strip()
            positivo = bool((self.aplicador_efeitos.definicoes.get(status_nome, {}) or {}).get("positivo", False))
            lados_diferentes = str(getattr(executor, "Lado", "")) != str(getattr(alvo, "Lado", ""))
            return lados_diferentes and not positivo
        return False

    @staticmethod
    def _registrar_eventos_aplicacao(log: LogCombate, eventos: list[dict[str, Any]], executor, alvo, efeito_dict: dict[str, Any], resultado) -> None:
        for evento in list(getattr(resultado, "eventos", []) or []):
            evento_dict = dict(evento) if isinstance(evento, dict) else {"valor": str(evento)}
            tipo_evento = str(evento_dict.get("tipo") or "evento_efeito")
            dados = {
                "executor_id": getattr(executor, "Uid", ""),
                "alvo_id": getattr(alvo, "Uid", ""),
                "tipo_efeito": str(efeito_dict.get("tipo") or ""),
                **evento_dict,
            }
            log.adicionar_historico(tipo_evento, **dados)
            eventos.append(dados)
