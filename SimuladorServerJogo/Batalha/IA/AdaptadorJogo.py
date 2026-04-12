from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from SimuladorServerJogo.Batalha.IA.EstadoIA import (
    AcaoCandidata,
    ArenaIA,
    CombatenteIA,
    EstadoBatalhaIA,
    HabilidadeIA,
    PosicaoIA,
)

if TYPE_CHECKING:
    from SimuladorServerJogo.Batalha.PokemonBatalha import PokemonBatalha
    from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha


class AdaptadorJogo:
    def criar_estado(
        self,
        sistema: "SistemaBatalha",
        lado_controlado: str,
        dificuldade: Dict[str, float] | None = None,
    ) -> EstadoBatalhaIA:
        lado_aliado = str(lado_controlado or "inimigo")
        lado_inimigo = "jogador" if lado_aliado == "inimigo" else "inimigo"
        arena = self._adaptar_arena(sistema)
        return EstadoBatalhaIA(
            batalha_id=str(sistema.BatalhaId),
            turno_atual=int(sistema.TurnoAtual),
            tick_global=int(sistema.TickGlobal),
            lado_controlado=lado_aliado,
            clima=str(sistema.ClimaAtual or ""),
            arena=arena,
            aliados_ativos=[self._adaptar_combatente(pokemon) for pokemon in sistema.listar_ativos(lado_aliado)],
            aliados_reserva=[self._adaptar_combatente(pokemon) for pokemon in self._listar_reservas(sistema, lado_aliado)],
            inimigos_ativos=[self._adaptar_combatente(pokemon) for pokemon in sistema.listar_ativos(lado_inimigo)],
            inimigos_reserva=[self._adaptar_combatente(pokemon) for pokemon in self._listar_reservas(sistema, lado_inimigo)],
            preparacoes_inimigas=[],
            dificuldade=dict(dificuldade or {}),
        )

    def traduzir_acao(self, acao: AcaoCandidata) -> Dict[str, object]:
        if acao.tipo_acao == "trocar":
            return {
                "executor_id": str(acao.executor_id),
                "estilo": "troca",
                "tipo_movimento": False,
                "destino_mundo": None,
                "troca_reserva_id": str(acao.troca_reserva_id),
                "alvo_ids": [],
                "custo_base": 0.0,
                "custo": 0.0,
                "acao_chave": "troca",
                "ataque": {},
            }

        if acao.tipo_acao == "esperar":
            return {
                "executor_id": str(acao.executor_id),
                "estilo": "esperar",
                "tipo_movimento": False,
                "destino_mundo": None,
                "troca_reserva_id": "",
                "alvo_ids": [],
                "custo_base": 0.0,
                "custo": 0.0,
                "acao_chave": "esperar",
                "ataque": {},
            }

        estilo = str(acao.estilo or acao.dados_extras.get("estilo") or "status").strip().casefold()
        destino = acao.destino_posicao.como_lista() if isinstance(acao.destino_posicao, PosicaoIA) else None
        return {
            "executor_id": str(acao.executor_id),
            "estilo": estilo,
            "tipo_movimento": estilo == "movimento",
            "destino_mundo": destino if estilo in {"movimento", "area", "tiro", "zona"} else None,
            "troca_reserva_id": str(acao.troca_reserva_id or ""),
            "alvo_ids": [str(item) for item in list(acao.alvo_ids or [])] if estilo == "alvo" else [],
            "custo_base": float(acao.custo_energia or 0.0),
            "custo": float(acao.custo_energia or 0.0),
            "acao_chave": str(acao.acao_chave or ""),
            "ataque": dict(acao.habilidade_bruta or {}),
        }

    def traduzir_acoes(self, acoes: List[AcaoCandidata]) -> List[Dict[str, object]]:
        return [self.traduzir_acao(acao) for acao in list(acoes or [])]

    def _adaptar_arena(self, sistema: "SistemaBatalha") -> ArenaIA:
        bruto = dict(sistema.ArenaAtual or {})
        largura = self._fnum(bruto.get("largura", sistema.Contexto.get("arena_largura", 40.0)), 40.0)
        altura = self._fnum(bruto.get("altura", sistema.Contexto.get("arena_altura", 20.0)), 20.0)
        centro_bruto = bruto.get("centro", sistema.Contexto.get("centro", [largura * 0.5, altura * 0.5]))
        centro = self._posicao(centro_bruto, [largura * 0.5, altura * 0.5])
        return ArenaIA(largura=largura, altura=altura, centro=centro, tiles_bloqueados=[])

    def _listar_reservas(self, sistema: "SistemaBatalha", lado: str) -> list["PokemonBatalha"]:
        uids = list(sistema.Lados.get(lado, {}).get("reservas") or [])
        saida: list["PokemonBatalha"] = []
        for uid in uids:
            pokemon = sistema.obter_pokemon(uid)
            if pokemon is not None:
                saida.append(pokemon)
        return saida

    def _adaptar_combatente(self, pokemon: "PokemonBatalha") -> CombatenteIA:
        serializado = pokemon.serializar()
        return CombatenteIA(
            uid=str(serializado.get("uid") or pokemon.Uid),
            nome=str(serializado.get("nome") or pokemon.Nome),
            lado=str(serializado.get("lado") or pokemon.Lado),
            ativo=bool(serializado.get("ativo", pokemon.Ativo)),
            fora_de_combate=bool(serializado.get("fora_de_combate", pokemon.ForaDeCombate)),
            posicao=self._posicao(serializado.get("posicao"), pokemon.Posicao),
            vida_atual=self._fnum(serializado.get("vida_atual"), pokemon.VidaAtual),
            vida_max=self._fnum(serializado.get("vida_max"), pokemon.obter_atributo("Vida")),
            energia=self._fnum(serializado.get("energia"), pokemon.Energia),
            energia_max=self._fnum(serializado.get("energia_max"), pokemon.EnergiaMax),
            barreira=self._fnum(serializado.get("barreira"), pokemon.Barreira),
            tipos=[str(item).strip().casefold() for item in list(serializado.get("tipos") or pokemon.Tipos) if str(item).strip()],
            atributos={str(chave): self._fnum(valor) for chave, valor in dict(serializado.get("atributos") or {}).items()},
            efeitos=[str(item.get("nome") or item).strip().casefold() for item in list(serializado.get("efeitos") or []) if str(item.get("nome") if isinstance(item, dict) else item).strip()],
            flags={str(chave): bool(valor) for chave, valor in dict(serializado.get("flags") or {}).items()},
            habilidades=[self._adaptar_habilidade(item) for item in list(serializado.get("habilidades") or []) if item],
        )

    def _adaptar_habilidade(self, ataque: Dict[str, object]) -> HabilidadeIA:
        nome = str(ataque.get("Ataque") or ataque.get("Nome") or ataque.get("nome") or "").strip()
        estilo = str(ataque.get("Estilo") or ataque.get("estilo") or "status").strip().casefold() or "status"
        tipo = str(ataque.get("Tipo") or ataque.get("tipo") or "normal").strip().casefold() or "normal"
        descricao = self._descricao_ataque(ataque)
        efeito_principal = self._efeito_principal(estilo, descricao)
        alvo_preferencial = "inimigo"
        if efeito_principal in {"cura", "protecao"}:
            alvo_preferencial = "aliado"
        elif efeito_principal == "mobilidade":
            alvo_preferencial = "posicao"
        usa_atributo = "SpA" if "especial" in descricao.casefold() else "Atk"
        return HabilidadeIA(
            nome=nome,
            chave=self._norm(nome),
            estilo=estilo,
            tipo=tipo,
            custo_energia=self._fnum(ataque.get("Custo"), 0.0),
            alcance=self._alcance_estimado(estilo, ataque),
            raio=self._raio_estimado(estilo, ataque),
            usa_atributo=usa_atributo,
            efeito_principal=efeito_principal,
            alvo_preferencial=alvo_preferencial,
            descricao=descricao,
            dados_brutos=dict(ataque),
        )

    @staticmethod
    def _fnum(valor, default: float = 0.0) -> float:
        try:
            if isinstance(valor, str):
                return float(valor.replace(",", "."))
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _norm(valor: object) -> str:
        return str(valor or "").strip().casefold()

    def _posicao(self, valor: object, default: object) -> PosicaoIA:
        bruto = valor if isinstance(valor, (list, tuple)) and len(valor) >= 2 else default
        if not isinstance(bruto, (list, tuple)) or len(bruto) < 2:
            bruto = [0.0, 0.0]
        return PosicaoIA(self._fnum(bruto[0], 0.0), self._fnum(bruto[1], 0.0))

    def _descricao_ataque(self, ataque: Dict[str, object]) -> str:
        for chave in (
            "Descricao",
            "DescriÃ§Ã£o",
            "descricao",
            "descriÃ§Ã£o",
            "DescriÃ§Ã£o Nivel 1",
            "Descricao Nivel 1",
        ):
            if str(ataque.get(chave) or "").strip():
                return str(ataque.get(chave) or "").strip()
        return ""

    def _efeito_principal(self, estilo: str, descricao: str) -> str:
        texto = str(descricao or "").casefold()
        if "cura" in texto or "recupera vida" in texto:
            return "cura"
        if "barreira" in texto or "proteg" in texto or "escudo" in texto:
            return "protecao"
        if estilo == "movimento":
            return "mobilidade"
        if estilo in {"area", "tiro", "alvo", "zona"}:
            return "dano"
        return "utilidade"

    def _alcance_estimado(self, estilo: str, ataque: Dict[str, object]) -> float:
        if self._fnum(ataque.get("Alcance"), 0.0) > 0:
            return self._fnum(ataque.get("Alcance"), 0.0)
        if estilo == "alvo":
            return 4.0
        if estilo in {"area", "tiro", "zona"}:
            return 5.0
        if estilo == "movimento":
            return 3.0
        return 0.0

    def _raio_estimado(self, estilo: str, ataque: Dict[str, object]) -> float:
        if self._fnum(ataque.get("Raio"), 0.0) > 0:
            return self._fnum(ataque.get("Raio"), 0.0)
        if estilo in {"area", "zona"}:
            return 1.5
        return 0.0

    # TODO: carregar ocupacao real de tiles e objetos da arena quando a malha final estiver definida.
    # TODO: preencher preparacoes_inimigas quando o jogo expor leitura parcial das jogadas preparadas.
