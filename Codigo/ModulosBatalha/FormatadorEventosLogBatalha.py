from __future__ import annotations

from typing import Dict


class FormatadorEventosLogBatalha:
    _FASES_LABEL = {
        "inicializacao": "Abertura",
        "segmentacao": "Execução",
        "passiva": "Passiva",
        "finalizacao": "Fechamento",
    }
    _CORES_TIPO = {
        "acao": ((22, 32, 56, 235), (96, 151, 230), (126, 179, 255)),
        "movimento": ((18, 38, 50, 235), (81, 174, 196), (114, 210, 230)),
        "objeto": ((28, 32, 58, 235), (144, 126, 216), (176, 153, 248)),
        "dano": ((58, 26, 30, 238), (212, 96, 96), (243, 132, 132)),
        "cura": ((20, 50, 36, 238), (92, 196, 124), (130, 224, 156)),
        "barreira": ((22, 40, 60, 238), (92, 158, 224), (132, 188, 255)),
        "energia": ((18, 34, 62, 238), (78, 128, 226), (108, 156, 245)),
        "efeito": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "fim_turno": ((36, 36, 46, 238), (154, 164, 184), (190, 198, 216)),
        "troca": ((36, 44, 54, 238), (154, 184, 212), (191, 220, 250)),
        "ataque_usado": ((22, 32, 56, 235), (96, 151, 230), (126, 179, 255)),
        "pokemon_sofreu_dano": ((58, 26, 30, 238), (212, 96, 96), (243, 132, 132)),
        "pokemon_recebeu_cura": ((20, 50, 36, 238), (92, 196, 124), (130, 224, 156)),
        "pokemon_gastou_energia": ((18, 34, 62, 238), (78, 128, 226), (108, 156, 245)),
        "pokemon_ganhou_energia": ((18, 34, 62, 238), (78, 128, 226), (108, 156, 245)),
        "barreira_absorveu": ((22, 40, 60, 238), (92, 158, 224), (132, 188, 255)),
        "pokemon_ganhou_barreira": ((22, 40, 60, 238), (92, 158, 224), (132, 188, 255)),
        "pokemon_recebeu_efeito": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "efeito_tickou": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "efeito_expirou": ((36, 24, 62, 238), (168, 114, 232), (202, 147, 255)),
        "pokemon_moveu": ((18, 38, 50, 235), (81, 174, 196), (114, 210, 230)),
        "pokemon_trocou_posicao": ((36, 44, 54, 238), (154, 184, 212), (191, 220, 250)),
        "pokemon_trocou_reserva": ((36, 44, 54, 238), (154, 184, 212), (191, 220, 250)),
        "pokemon_morreu": ((58, 26, 30, 238), (212, 96, 96), (243, 132, 132)),
        "captura_batalha_resultado": ((44, 31, 64, 238), (168, 126, 224), (214, 170, 255)),
    }
    _MOTIVOS_FALHA = {
        "pokemon_inexistente_execucao": "o Pokémon não foi encontrado.",
        "pokemon_morto_execucao": "o Pokémon já estava derrotado.",
        "lado_divergente_execucao": "a ação pertencia a outro lado da batalha.",
        "pokemon_entrou_na_rodada": "o Pokémon entrou nesta rodada e ainda não podia agir.",
        "pokemon_recuado": "o Pokémon estava recuado.",
        "pokemon_inapto": "o Pokémon estava incapacitado.",
        "ataque_bloqueado_por_paralisia": "o ataque foi bloqueado pela paralisia.",
        "movimento_bloqueado_por_enraizado": "o movimento foi bloqueado por Enraizado.",
        "pokemon_nao_ativo_execucao": "o Pokémon não estava ativo em campo.",
        "energia_insuficiente_execucao": "não havia energia suficiente.",
        "movimento_bloqueado_por_efeito": "o movimento foi bloqueado por efeito ativo.",
        "movimento_falhou": "o movimento não pôde ser concluído.",
        "troca_posicao_convertida_falhou": "a troca de posição não pôde ser concluída.",
        "area_ocupada_por_oponente": "a área estava ocupada por um oponente.",
        "troca_posicao_alvo_morto": "o alvo da troca não estava disponível.",
        "troca_posicao_falhou": "a troca de posição falhou.",
        "reserva_morta_ou_inexistente": "o Pokémon da reserva não estava disponível.",
        "troca_reserva_falhou": "a troca com a reserva falhou.",
        "ataque_sem_propriedades": "o ataque não tinha propriedades configuradas.",
        "sem_alvo_real": "nenhum alvo válido foi encontrado.",
        "ataque_errou": "o ataque não acertou o alvo.",
        "execute_falhou": "o efeito principal do ataque falhou.",
        "tipo_sem_executor": "esse tipo de ação ainda não tem executor.",
        "captura_bloqueada_tipo_batalha": "captura bloqueada neste tipo de batalha.",
        "captura_fora_de_confronto": "captura disponível apenas em confronto.",
        "captura_alvo_inexistente": "o alvo da captura não foi encontrado.",
        "captura_alvo_aliado": "não é possível capturar um aliado.",
        "captura_alvo_invalido": "o alvo da captura não estava válido.",
        "pokebola_indisponivel": "não havia Pokébola disponível.",
    }

    @staticmethod
    def _aprox(a: float, b: float, tolerancia: float = 0.001) -> bool:
        return abs(float(a) - float(b)) <= float(tolerancia)

    @staticmethod
    def _numero(valor, default: float = 0.0) -> float:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(default)

    @classmethod
    def _formatar_numero(cls, valor: object) -> str:
        numero = cls._numero(valor, 0.0)
        if cls._aprox(numero, round(numero)):
            return str(int(round(numero)))
        return f"{numero:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _nome_pokemon(evento: Dict[str, object], chave_nome: str, chave_id: str, fallback: str = "Combatente") -> str:
        nome = str(evento.get(chave_nome) or "").strip()
        if nome:
            return nome
        bruto = str(evento.get(chave_id) or "").strip()
        return bruto or fallback

    @staticmethod
    def _formatar_posicao(posicao) -> str:
        if isinstance(posicao, (list, tuple)) and len(posicao) == 2:
            try:
                return f"({float(posicao[0]):.1f}, {float(posicao[1]):.1f})"
            except (TypeError, ValueError):
                return str(tuple(posicao))
        return "posição desconhecida"

    def _segmento(self, texto: object, *, atributo: str | None = None, titulo: str = "", descricao: str = "", tooltip: str = "") -> dict[str, object]:
        return {
            "texto": str(texto or ""),
            "atributo": str(atributo or ""),
            "titulo_tooltip": str(titulo or ""),
            "descricao_tooltip": str(descricao or ""),
            "tooltip": str(tooltip or ""),
        }

    def _atributo_dano(self, evento: Dict[str, object]) -> str:
        dano_tipo = str(evento.get("dano_tipo") or evento.get("categoria") or "").strip().casefold()
        if dano_tipo in {"especial", "spa", "magico"}:
            return "spa"
        return "atk"

    def _tooltip_valor_simples(self, titulo: str, linhas: list[str]) -> tuple[str, str]:
        descricao = "\n".join([str(linha) for linha in linhas if str(linha or "").strip()])
        return (titulo, descricao)

    def _tooltip_calculo(self, titulo: str, evento: Dict[str, object], fallback: list[str]) -> tuple[str, str]:
        calculo = [str(linha) for linha in list(evento.get("calculo") or []) if str(linha or "").strip()]
        return self._tooltip_valor_simples(titulo, calculo or fallback)

    def _tooltip_dano(self, evento: Dict[str, object]) -> tuple[str, str]:
        if isinstance(evento.get("calculo"), list) and evento.get("calculo"):
            return self._tooltip_valor_simples("Detalhes do dano", [str(linha) for linha in evento.get("calculo")])
        detalhes = dict(evento.get("detalhes") or {})
        linhas: list[str] = []

        def adicionar(label: str, chave: str, *, sempre: bool = False, esconder_zero: bool = False, esconder_identidade: bool = False):
            if chave not in detalhes:
                return
            valor = self._numero(detalhes.get(chave), 0.0)
            if esconder_zero and self._aprox(valor, 0.0):
                return
            if esconder_identidade and self._aprox(valor, 1.0):
                return
            if (not sempre) and esconder_zero and self._aprox(valor, 0.0):
                return
            linhas.append(f"{label}: {self._formatar_numero(valor)}")

        adicionar("Dano Bruto", "dano_bruto", esconder_zero=True)
        adicionar("Bônus de Intensidade", "bonus_intensidade", esconder_identidade=True)
        adicionar("Multiplicador de Dano Causado", "multiplicador_dano_causado", esconder_identidade=True)
        adicionar("Multiplicador Crítico", "multiplicador_critico", esconder_identidade=True)
        adicionar("Defesa Bruta", "defesa_base", sempre=True)
        adicionar("Perfuração", "perfuracao", esconder_zero=True)
        adicionar("Defesa Reduzida", "defesa_reduzida_por_perfuracao", esconder_zero=True)
        adicionar("Defesa Aplicada", "defesa_aplicada", sempre=True)
        adicionar("Dano Pós Defesa", "dano_pos_defesa", sempre=True)
        adicionar("Multiplicador de Tipo", "multiplicador_tipo", esconder_identidade=True)
        adicionar("Dano Pós Tipo", "dano_pos_tipo", sempre=True)
        adicionar("Multiplicador de Hook", "multiplicador_hook", esconder_identidade=True)
        adicionar("Delta de Hook", "delta_hook", esconder_zero=True)
        adicionar("Multiplicador de Dano Recebido", "multiplicador_dano_recebido", esconder_identidade=True)
        linhas.append(f"Dano Final: {self._formatar_numero(evento.get('dano', 0.0))}")
        return self._tooltip_valor_simples("Detalhes do dano", linhas)

    def _tooltip_vida(self, titulo: str, valor: object, antes: object, depois: object) -> tuple[str, str]:
        return self._tooltip_valor_simples(
            titulo,
            [
                f"Valor aplicado: {self._formatar_numero(valor)}",
                f"Antes: {self._formatar_numero(antes)}",
                f"Depois: {self._formatar_numero(depois)}",
            ],
        )

    def _tooltip_variacao_atributo(self, evento: Dict[str, object]) -> tuple[str, str]:
        atributo = str(evento.get("atributo") or evento.get("stat") or evento.get("chave") or "Atributo")
        calculo = [str(linha) for linha in list(evento.get("calculo") or []) if str(linha or "").strip()]
        if not calculo:
            calculo = [
                f"Valor inicial = {self._formatar_numero(evento.get('valor_antes', 0.0))}",
                f"Variacao = {self._formatar_numero(evento.get('valor', evento.get('variacao', 0.0)))}",
                f"Valor final = {self._formatar_numero(evento.get('valor_depois', 0.0))}",
            ]
        return self._tooltip_valor_simples(f"Detalhes de {atributo}", calculo)

    def _tooltip_barreira(self, valor: object, total: object) -> tuple[str, str]:
        return self._tooltip_valor_simples(
            "Detalhes da barreira",
            [
                f"Barreira ganha: {self._formatar_numero(valor)}",
                f"Barreira total: {self._formatar_numero(total)}",
            ],
        )

    def _tooltip_energia(self, valor: object, total: object, motivo: str = "") -> tuple[str, str]:
        linhas = [
            f"Variação de energia: {self._formatar_numero(valor)}",
            f"Energia atual: {self._formatar_numero(total)}",
        ]
        if motivo:
            linhas.append(f"Motivo: {motivo}")
        return self._tooltip_valor_simples("Detalhes da energia", linhas)

    def _tooltip_captura(self, evento: Dict[str, object]) -> tuple[str, str]:
        checks = ["OK" if bool(v) else "falha" for v in list(evento.get("checagens") or [])]
        return self._tooltip_valor_simples(
            "Detalhes da captura",
            [
                f"Chance por check: {self._formatar_numero(evento.get('chance_check', 0.0))}%",
                f"Chance real em 3 checks: {self._formatar_numero(evento.get('chance_real_3_checks', 0.0))}%",
                f"Dificuldade de batalha: {self._formatar_numero(evento.get('dificuldade_batalha', 0.0))}",
                f"Poder total: {self._formatar_numero(evento.get('poder_total', 0.0))}",
                f"Checks: {', '.join(checks) if checks else 'sem checks'}",
            ],
        )

    def _formatar_motivo_falha(self, motivo: object) -> str:
        token = str(motivo or "").strip()
        if not token:
            return "motivo não informado."
        return self._MOTIVOS_FALHA.get(token, f"falha não catalogada: {token}.")

    def _tooltip_acerto(self, evento: Dict[str, object]) -> tuple[str, str]:
        acerto = evento.get("acerto") if isinstance(evento.get("acerto"), dict) else {}
        calculo = [str(linha) for linha in list(acerto.get("calculo") or []) if str(linha or "").strip()]
        if not calculo:
            if "chance_real" in acerto:
                calculo.append(f"Chance real = {self._formatar_numero(acerto.get('chance_real', 0.0))}%")
            if acerto.get("rolagem") is not None:
                calculo.append(f"Rolagem = {self._formatar_numero(acerto.get('rolagem', 0.0))}")
            if "acertou" in acerto:
                calculo.append("Resultado: acertou" if bool(acerto.get("acertou")) else "Resultado: desvio")
        return self._tooltip_valor_simples("Detalhes do desvio", calculo or ["O alvo desviou, mas o cálculo detalhado não veio no log."])

    def _tooltip_defensivo(self, titulo: str, evento: Dict[str, object], campos: list[tuple[str, str]]) -> tuple[str, str]:
        linhas = []
        for chave, label in campos:
            if chave in evento:
                linhas.append(f"{label}: {self._formatar_numero(evento.get(chave, 0.0))}")
        origem = str(evento.get("origem_nome") or evento.get("usuario_nome") or "").strip()
        if origem:
            linhas.append(f"Origem: {origem}")
        return self._tooltip_valor_simples(titulo, linhas)

    def _nome_efeito(self, evento: Dict[str, object]) -> str:
        return str(evento.get("efeito_nome") or evento.get("efeito") or evento.get("efeito_code") or "efeito")

    def _area_id(self, evento: Dict[str, object]) -> str:
        return str(evento.get("area_id") or evento.get("id") or evento.get("area") or "desconhecida")

    def _registro_placeholder(self, mensagem: str, subtitulo: str = "Sem registros") -> dict[str, object]:
        return {
            "tipo": "placeholder",
            "tick": 0,
            "fase_label": subtitulo,
            "cor_fundo": (20, 28, 44, 220),
            "cor_borda": (90, 112, 152),
            "cor_faixa": (126, 154, 204),
            "segmentos": [self._segmento(mensagem)],
        }

    def _cores_evento(self, tipo: str, evento: Dict[str, object]):
        cores = {
            "laranja": ((82, 43, 18, 238), (232, 126, 46), (255, 158, 76)),
            "roxo": ((48, 28, 70, 238), (168, 104, 224), (206, 150, 255)),
            "azul": ((18, 42, 68, 238), (74, 156, 235), (122, 202, 255)),
            "verde": ((18, 58, 36, 238), (72, 190, 104), (124, 230, 152)),
            "amarelo": ((72, 60, 22, 238), (218, 184, 70), (255, 222, 112)),
            "vermelho": ((82, 26, 30, 238), (226, 70, 78), (255, 126, 132)),
            "rosa": ((72, 32, 58, 238), (224, 104, 172), (255, 158, 210)),
            "marrom": ((58, 42, 30, 238), (166, 118, 78), (210, 158, 112)),
            "cinza": ((42, 46, 54, 238), (132, 142, 156), (176, 186, 202)),
        }
        if tipo == "ataque_resumo":
            impactos = [dict(item) for item in list(evento.get("impactos") or []) if isinstance(item, dict)]
            falhas = [dict(item) for item in list(evento.get("falhas") or []) if isinstance(item, dict)]
            if falhas or bool(evento.get("sem_alvo", False)):
                return cores["cinza"]
            danos = [i for i in impactos if str(i.get("tipo") or "") in {"pokemon_sofreu_dano", "barreira_absorveu"}]
            if any(bool(i.get("critico", False)) for i in danos):
                return cores["vermelho"]
            if any(str(i.get("tipo") or "") == "pokemon_recebeu_efeito" and str(i.get("tipo_efeito") or i.get("tipo") or "").lower() == "negativo" for i in impactos):
                return cores["roxo"]
            if danos:
                if any(str(i.get("categoria") or "").lower() in {"especial", "spa", "magico"} for i in danos):
                    return cores["roxo"]
                return cores["laranja"]
            if any(str(i.get("tipo") or "") in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"} for i in impactos):
                return cores["verde"] if any(not bool(i.get("negativo", False)) for i in impactos) else cores["roxo"]
            if any(str(i.get("tipo") or "") in {"pokemon_recebeu_cura", "pokemon_ganhou_barreira", "pokemon_recebeu_efeito"} for i in impactos):
                return cores["rosa"]
            return cores["cinza"]
        if tipo in {"pokemon_moveu", "movimento"}:
            return cores["azul"]
        if tipo in {"pokemon_trocou_posicao", "pokemon_trocou_reserva", "troca"}:
            return cores["verde"]
        if tipo in {"efeito_expirou", "clima_expirou"}:
            return cores["amarelo"]
        if tipo in {"passiva", "passivo"}:
            return cores["marrom"]
        if tipo == "pokemon_morreu":
            return cores["vermelho"]
        if tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            return cores["roxo"] if bool(evento.get("negativo", False)) else cores["verde"]
        if tipo in {"acao_falhou", "ataque_errou", "ataque_desviado", "pokemon_desviou", "ataque_sem_alvo_real"}:
            return cores["cinza"]
        if tipo in {"evasivo_consumido", "preparado_ativou", "refletindo_ativou"}:
            return cores["azul"]
        if tipo in {"efeito_bloqueado_por_imunidade", "efeito_bloqueado_por_bloqueado"}:
            return cores["roxo"]
        if tipo in {"area_recebeu_efeito", "area_removeu_efeito", "area_limpou_efeitos", "area_definiu_efeitos"}:
            return cores["marrom"]
        if tipo in {"vampirico_curou_atacante", "pokemon_removeu_efeito", "turno_revertido"}:
            return cores["cinza"]
        if tipo == "captura_batalha_resultado":
            return cores["verde"] if bool(evento.get("capturado", False)) else cores["roxo"]
        return self._CORES_TIPO.get(tipo, cores["cinza"])

    def _registro_evento(self, evento: Dict[str, object], tick: int, fase: str) -> dict[str, object]:
        if isinstance(evento.get("dados"), dict):
            dados = dict(evento.get("dados") or {})
            if isinstance(dados.get("dados"), dict):
                for chave, valor in dict(dados.get("dados") or {}).items():
                    dados.setdefault(chave, valor)
            for chave, valor in dados.items():
                evento.setdefault(chave, valor)
        tipo = str(evento.get("tipo") or "").strip().casefold()
        executor = self._nome_pokemon(evento, "executor_nome", "executor_id")
        alvo = self._nome_pokemon(evento, "alvo_nome", "alvo_id")
        pokemon = self._nome_pokemon(evento, "pokemon_nome", "pokemon_id")

        if tipo == "ataque_resumo":
            base = dict(evento.get("base") or {})
            usuario = str(base.get("usuario_nome") or pokemon)
            ataque = str(base.get("ataque_nome") or "Ataque")
            area = str(base.get("area_alvo") or base.get("area_alvo_real") or "").strip()
            segmentos = [self._segmento(usuario), self._segmento(" usou "), self._segmento(ataque)]
            impactos = [dict(item) for item in list(evento.get("impactos") or []) if isinstance(item, dict)]
            falhas = [dict(item) for item in list(evento.get("falhas") or []) if isinstance(item, dict)]
            if impactos:
                tipos_attr = {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}
                if all(str(impacto.get("tipo") or "").strip().casefold() in tipos_attr for impacto in impactos):
                    for idx, impacto in enumerate(impactos):
                        atributo = str(impacto.get("atributo") or "Atributo")
                        valor = self._numero(impacto.get("valor", impacto.get("variacao", 0.0)), 0.0)
                        verbo = "aumentou" if valor >= 0 else "diminuiu"
                        mesmo_alvo = str(impacto.get("origem_id") or impacto.get("usuario_id") or base.get("usuario_id") or "") == str(impacto.get("alvo_id") or impacto.get("pokemon_id") or "")
                        alvo_nome = str(impacto.get("alvo_nome") or impacto.get("pokemon_nome") or "alvo")
                        alvo_txt = f"sua propria {atributo}" if mesmo_alvo else f"{atributo} de {alvo_nome}"
                        titulo, descricao = self._tooltip_variacao_atributo(impacto)
                        segmentos.append(self._segmento(" e " if idx == 0 else ", e "))
                        segmentos.append(self._segmento(f"{verbo} {alvo_txt} para "))
                        segmentos.append(self._segmento(self._formatar_numero(impacto.get("valor_depois", 0.0)), atributo=atributo, titulo=titulo, descricao=descricao))
                else:
                    segmentos.append(self._segmento(" e atingiu "))
                    partes = []
                    for impacto in impactos:
                        alvo_nome = str(impacto.get("alvo_nome") or impacto.get("pokemon_nome") or impacto.get("efeito_nome") or "alvo")
                        itipo = str(impacto.get("tipo") or "").strip().casefold()
                        if itipo == "pokemon_sofreu_dano":
                            titulo, descricao = self._tooltip_dano(impacto)
                            partes.append([self._segmento(alvo_nome), self._segmento(" causando "), self._segmento(self._formatar_numero(impacto.get("valor", 0)), atributo=self._atributo_dano(impacto), titulo=titulo, descricao=descricao), self._segmento(" de dano")])
                        elif itipo == "barreira_absorveu":
                            titulo, descricao = self._tooltip_calculo("Detalhes da barreira", impacto, [f"Barreira absorveu: {self._formatar_numero(impacto.get('dano_barreira', 0))}"])
                            partes.append([self._segmento(alvo_nome), self._segmento(" absorvendo "), self._segmento(self._formatar_numero(impacto.get("dano_barreira", 0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" na barreira")])
                        elif itipo == "pokemon_recebeu_cura":
                            titulo, descricao = self._tooltip_calculo("Detalhes da cura", impacto, [f"Cura final = {self._formatar_numero(impacto.get('valor', 0))}"])
                            partes.append([self._segmento(alvo_nome), self._segmento(" curando "), self._segmento(self._formatar_numero(impacto.get("valor", 0)), atributo="vida", titulo=titulo, descricao=descricao), self._segmento(" de vida")])
                        elif itipo == "pokemon_ganhou_barreira":
                            titulo, descricao = self._tooltip_calculo("Detalhes da barreira", impacto, [f"Barreira final = {self._formatar_numero(impacto.get('valor', 0))}"])
                            partes.append([self._segmento(alvo_nome), self._segmento(" ganhando "), self._segmento(self._formatar_numero(impacto.get("valor", 0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" de barreira")])
                        elif itipo == "pokemon_recebeu_efeito":
                            efeito = str(impacto.get("efeito_nome") or "efeito")
                            passos = impacto.get("passos_restantes", "?")
                            partes.append([self._segmento(alvo_nome), self._segmento(" recebendo "), self._segmento(efeito), self._segmento(f" por {passos} passos")])
                        elif itipo in tipos_attr:
                            atributo = str(impacto.get("atributo") or "Atributo")
                            valor = self._numero(impacto.get("valor", impacto.get("variacao", 0.0)), 0.0)
                            acao_txt = "aumentando" if valor >= 0 else "diminuindo"
                            titulo, descricao = self._tooltip_variacao_atributo(impacto)
                            partes.append([
                                self._segmento(alvo_nome),
                                self._segmento(f" {acao_txt} {atributo} para "),
                                self._segmento(self._formatar_numero(impacto.get("valor_depois", 0.0)), atributo=atributo, titulo=titulo, descricao=descricao),
                            ])
                    for idx, parte in enumerate(partes):
                        if idx > 0:
                            segmentos.append(self._segmento(", "))
                        segmentos.extend(parte)
            elif bool(evento.get("sem_alvo", False)):
                segmentos.extend([self._segmento(" em "), self._segmento(f"Area {area}" if area else "uma area"), self._segmento(", mas nao encontrou alvo")])
            elif falhas:
                falha = falhas[0]
                alvo_falha = str(falha.get("alvo_nome") or falha.get("alvo_id") or area or "o alvo")
                if str(falha.get("tipo") or "").strip().casefold() in {"ataque_errou", "ataque_desviado", "pokemon_desviou"}:
                    titulo, descricao = self._tooltip_acerto(falha)
                    segmentos.extend(
                        [
                            self._segmento(" em "),
                            self._segmento(alvo_falha),
                            self._segmento(f", mas {alvo_falha} "),
                            self._segmento("desviou", titulo=titulo, descricao=descricao),
                        ]
                    )
                else:
                    motivo = self._formatar_motivo_falha(falha.get("motivo") or falha.get("motivo_invalidacao"))
                    segmentos.extend([self._segmento(" em "), self._segmento(alvo_falha), self._segmento(f", mas falhou: {motivo}")])
            elif area:
                segmentos.extend([self._segmento(" em "), self._segmento(f"Area {area}")])
            if any(str(i.get("tipo") or "").strip().casefold() in {"pokemon_sofreu_dano", "barreira_absorveu"} and bool(i.get("critico", False)) for i in impactos):
                segmentos.append(self._segmento(" (critico)"))
            segmentos.append(self._segmento("."))
        elif tipo == "rodada_iniciada":
            segmentos = [self._segmento(f"Rodada {evento.get('rodada')} iniciada.")]
        elif tipo == "rodada_finalizada":
            segmentos = [self._segmento(f"Rodada {evento.get('rodada')} finalizada.")]
        elif tipo == "batalha_finalizada":
            segmentos = [self._segmento("A batalha foi finalizada.")]
        elif tipo == "acao_iniciada":
            segmentos = [self._segmento(pokemon), self._segmento(" preparou "), self._segmento(str(evento.get("tipo_acao") or evento.get("tipo") or "acao")), self._segmento(".")]
        elif tipo == "acao_falhou":
            motivo = self._formatar_motivo_falha(evento.get("motivo") or evento.get("motivo_invalidacao"))
            segmentos = [self._segmento(pokemon), self._segmento(f" tentou agir, mas falhou: {motivo}")]
        elif tipo == "pokemon_gastou_energia":
            titulo, descricao = self._tooltip_energia(-self._numero(evento.get("valor"), 0.0), evento.get("energia_depois", 0.0), "acao")
            segmentos = [self._segmento(pokemon), self._segmento(" gastou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="ene", titulo=titulo, descricao=descricao), self._segmento(" de energia.")]
        elif tipo == "pokemon_ganhou_energia":
            titulo, descricao = self._tooltip_energia(evento.get("valor", 0.0), evento.get("energia_depois", 0.0), str(evento.get("motivo") or ""))
            segmentos = [self._segmento(pokemon), self._segmento(" recuperou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="ene", titulo=titulo, descricao=descricao), self._segmento(" de energia.")]
        elif tipo == "ataque_usado":
            alvo_txt = str(evento.get("area_alvo") or evento.get("area_alvo_real") or "").strip()
            segmentos = [self._segmento(str(evento.get("usuario_nome") or pokemon)), self._segmento(" usou "), self._segmento(str(evento.get("ataque_nome") or "ataque"))]
            if alvo_txt:
                segmentos.extend([self._segmento(" em "), self._segmento(alvo_txt)])
            segmentos.append(self._segmento("."))
        elif tipo == "ataque_sem_alvo_real":
            segmentos = [self._segmento(str(evento.get("ataque_nome") or "Ataque")), self._segmento(" nao encontrou alvo real.")]
        elif tipo in {"ataque_errou", "ataque_desviado", "pokemon_desviou"}:
            usuario = str(evento.get("usuario_nome") or pokemon)
            alvo_nome = str(evento.get("alvo_nome") or "o alvo")
            ataque = str(evento.get("ataque_nome") or "ataque")
            titulo, descricao = self._tooltip_acerto(evento)
            if usuario and usuario != "Combatente":
                segmentos = [
                    self._segmento(usuario),
                    self._segmento(" usou "),
                    self._segmento(ataque),
                    self._segmento(", mas "),
                    self._segmento(alvo_nome, titulo=titulo, descricao=descricao),
                    self._segmento(" desviou."),
                ]
            else:
                segmentos = [self._segmento(alvo_nome), self._segmento(" desviou de "), self._segmento(ataque, titulo=titulo, descricao=descricao), self._segmento(".")]
        elif tipo == "ataque_acertou":
            segmentos = [self._segmento(str(evento.get("usuario_nome") or pokemon)), self._segmento(" acertou "), self._segmento(str(evento.get("alvo_nome") or "o alvo")), self._segmento(".")]
        elif tipo == "evasivo_consumido":
            titulo, descricao = self._tooltip_defensivo("Detalhes do Evasivo", evento, [("dano_original", "Dano original")])
            segmentos = [self._segmento(pokemon), self._segmento(" evitou o dano com "), self._segmento("Evasivo", titulo=titulo, descricao=descricao), self._segmento(".")]
        elif tipo == "preparado_ativou":
            titulo, descricao = self._tooltip_defensivo(
                "Detalhes do Preparado",
                evento,
                [
                    ("dano_original", "Dano original"),
                    ("dano_reduzido", "Dano reduzido"),
                    ("percentual_devolucao", "Percentual de devolução"),
                    ("dano_retorno", "Dano de retorno"),
                ],
            )
            segmentos = [
                self._segmento(pokemon),
                self._segmento(" se preparou, reduziu o dano e devolveu "),
                self._segmento(self._formatar_numero(evento.get("dano_retorno", 0.0)), atributo="atk", titulo=titulo, descricao=descricao),
                self._segmento("."),
            ]
        elif tipo == "refletindo_ativou":
            titulo, descricao = self._tooltip_defensivo(
                "Detalhes do Refletindo",
                evento,
                [("dano_original", "Dano original"), ("dano_reduzido", "Dano reduzido"), ("dano_refletido", "Dano refletido")],
            )
            segmentos = [self._segmento(pokemon), self._segmento(" refletiu", titulo=titulo, descricao=descricao), self._segmento(" parte do dano recebido.")]
        elif tipo == "vampirico_curou_atacante":
            atacante = str(evento.get("atacante_nome") or evento.get("atacante_id") or "Atacante")
            titulo, descricao = self._tooltip_valor_simples(
                "Detalhes do Vampírico",
                [
                    f"Dano causado: {self._formatar_numero(evento.get('dano_vida', 0.0))}",
                    f"Cura gerada: {self._formatar_numero(evento.get('cura', 0.0))}",
                ],
            )
            segmentos = [
                self._segmento(atacante),
                self._segmento(" recuperou "),
                self._segmento(self._formatar_numero(evento.get("cura", 0.0)), atributo="vida", titulo=titulo, descricao=descricao),
                self._segmento(" de vida por Vampírico."),
            ]
        elif tipo == "pokemon_sofreu_dano":
            titulo, descricao = self._tooltip_calculo("Detalhes do dano", evento, [f"Valor aplicado: {self._formatar_numero(evento.get('valor', 0.0))}", f"Antes: {self._formatar_numero(evento.get('vida_antes', 0.0))}", f"Depois: {self._formatar_numero(evento.get('vida_depois', 0.0))}"])
            segmentos = [self._segmento(str(evento.get("alvo_nome") or pokemon)), self._segmento(" sofreu "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="atk", titulo=titulo, descricao=descricao), self._segmento(" de dano.")]
            if bool(evento.get("critico", False)):
                segmentos.append(self._segmento(" Foi critico."))
        elif tipo == "barreira_absorveu":
            titulo, descricao = self._tooltip_valor_simples("Detalhes da barreira", [f"Antes: {self._formatar_numero(evento.get('barreira_antes', 0))}", f"Depois: {self._formatar_numero(evento.get('barreira_depois', 0))}"])
            segmentos = [self._segmento("A barreira de "), self._segmento(str(evento.get("alvo_nome") or alvo)), self._segmento(" absorveu "), self._segmento(self._formatar_numero(evento.get("dano_barreira", 0.0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" de dano.")]
        elif tipo == "pokemon_recebeu_cura":
            titulo, descricao = self._tooltip_calculo("Detalhes da cura", evento, [f"Valor aplicado: {self._formatar_numero(evento.get('valor', 0.0))}", f"Antes: {self._formatar_numero(evento.get('vida_antes', 0.0))}", f"Depois: {self._formatar_numero(evento.get('vida_depois', 0.0))}"])
            segmentos = [self._segmento(str(evento.get("alvo_nome") or pokemon)), self._segmento(" recuperou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="vida", titulo=titulo, descricao=descricao), self._segmento(" de vida.")]
        elif tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            alvo_nome = str(evento.get("alvo_nome") or evento.get("pokemon_nome") or pokemon)
            origem_nome = str(evento.get("origem_nome") or evento.get("usuario_nome") or executor)
            ataque = str(evento.get("ataque_nome") or "ataque")
            atributo = str(evento.get("atributo") or "Atributo")
            valor = self._numero(evento.get("valor", evento.get("variacao", 0.0)), 0.0)
            verbo = "aumentou" if valor >= 0 else "diminuiu"
            alvo_txt = "sua propria" if str(evento.get("origem_id") or evento.get("usuario_id") or "") == str(evento.get("alvo_id") or evento.get("pokemon_id") or "") else f"de {alvo_nome}"
            titulo, descricao = self._tooltip_variacao_atributo(evento)
            segmentos = [
                self._segmento(origem_nome),
                self._segmento(" usou "),
                self._segmento(ataque),
                self._segmento(f" e {verbo} {alvo_txt} {atributo} para "),
                self._segmento(self._formatar_numero(evento.get("valor_depois", 0.0)), atributo=atributo, titulo=titulo, descricao=descricao),
                self._segmento("."),
            ]
        elif tipo == "pokemon_ganhou_barreira":
            titulo, descricao = self._tooltip_calculo("Detalhes da barreira", evento, [f"Barreira ganha: {self._formatar_numero(evento.get('valor', 0.0))}", f"Barreira total: {self._formatar_numero(evento.get('barreira_depois', 0.0))}"])
            segmentos = [self._segmento(str(evento.get("alvo_nome") or pokemon)), self._segmento(" ganhou "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="def", titulo=titulo, descricao=descricao), self._segmento(" de barreira.")]
        elif tipo == "pokemon_recebeu_efeito":
            segmentos = [self._segmento(pokemon), self._segmento(" recebeu "), self._segmento(str(evento.get("efeito_nome") or "efeito")), self._segmento(f" por {evento.get('passos_restantes', '?')} passos.")]
        elif tipo == "efeito_bloqueado_por_limite":
            segmentos = [self._segmento(pokemon), self._segmento(" nao recebeu "), self._segmento(str(evento.get("efeito_nome") or "efeito")), self._segmento(": limite de efeitos.")]
        elif tipo == "pokemon_removeu_efeito":
            efeito = self._nome_efeito(evento)
            if str(evento.get("motivo") or "").strip().casefold() == "dano_real":
                segmentos = [self._segmento(pokemon), self._segmento(" acordou ao receber dano.")]
            else:
                segmentos = [self._segmento(pokemon), self._segmento(" perdeu o efeito "), self._segmento(efeito), self._segmento(".")]
        elif tipo == "efeito_bloqueado_por_imunidade":
            segmentos = [self._segmento(pokemon), self._segmento(" bloqueou "), self._segmento(self._nome_efeito(evento)), self._segmento(" com Imune.")]
        elif tipo == "efeito_bloqueado_por_bloqueado":
            segmentos = [self._segmento(pokemon), self._segmento(" não recebeu "), self._segmento(self._nome_efeito(evento)), self._segmento(" por estar Bloqueado.")]
        elif tipo == "efeito_tickou":
            segmentos = [self._segmento(str(evento.get("efeito_nome") or "Efeito")), self._segmento(" tickou em "), self._segmento(pokemon), self._segmento(f": {evento.get('passos_antes', '?')} -> {evento.get('passos_depois', '?')}.")]
        elif tipo == "efeito_expirou":
            segmentos = [self._segmento(str(evento.get("efeito_nome") or "Efeito")), self._segmento(" expirou em "), self._segmento(pokemon), self._segmento(".")]
        elif tipo == "clima_expirou":
            segmentos = [self._segmento("Clima "), self._segmento(str(evento.get("clima") or evento.get("clima_nome") or "ativo")), self._segmento(" expirou.")]
        elif tipo == "turno_revertido":
            segmentos = [self._segmento("A rodada foi revertida para revisão.")]
        elif tipo == "area_recebeu_efeito":
            segmentos = [self._segmento("A área "), self._segmento(self._area_id(evento)), self._segmento(" recebeu o efeito "), self._segmento(self._nome_efeito(evento)), self._segmento(".")]
        elif tipo == "area_removeu_efeito":
            segmentos = [self._segmento("A área "), self._segmento(self._area_id(evento)), self._segmento(" perdeu o efeito "), self._segmento(self._nome_efeito(evento)), self._segmento(".")]
        elif tipo == "area_limpou_efeitos":
            area_id = self._area_id(evento)
            if area_id == "desconhecida":
                segmentos = [self._segmento("Os efeitos das áreas foram limpos.")]
            else:
                segmentos = [self._segmento("A área "), self._segmento(area_id), self._segmento(" teve os efeitos limpos.")]
        elif tipo == "area_definiu_efeitos":
            efeitos = evento.get("efeitos")
            if isinstance(efeitos, list):
                nomes = ", ".join(str(item.get("nome") or item.get("efeito") or item) if isinstance(item, dict) else str(item) for item in efeitos) or "nenhum efeito"
            else:
                nomes = str(evento.get("efeito") or evento.get("efeito_nome") or "efeitos")
            segmentos = [self._segmento("A área "), self._segmento(self._area_id(evento)), self._segmento(" definiu efeitos: "), self._segmento(nomes), self._segmento(".")]
        elif tipo == "pokemon_moveu":
            segmentos = [self._segmento(pokemon), self._segmento(" moveu-se de "), self._segmento(str(evento.get("area_origem") or "?")), self._segmento(" para "), self._segmento(str(evento.get("area_destino") or "?")), self._segmento(".")]
        elif tipo == "pokemon_trocou_posicao":
            segmentos = [self._segmento(str(evento.get("pokemon_a_nome") or "Pokemon")), self._segmento(" trocou de posicao com "), self._segmento(str(evento.get("pokemon_b_nome") or "Pokemon")), self._segmento(".")]
        elif tipo == "pokemon_trocou_reserva":
            segmentos = [self._segmento(str(evento.get("pokemon_entrou_nome") or "Pokemon")), self._segmento(" entrou no lugar de "), self._segmento(str(evento.get("pokemon_saiu_nome") or "Pokemon")), self._segmento(".")]
        elif tipo == "pokemon_entrou":
            segmentos = [self._segmento(pokemon), self._segmento(" entrou em campo.")]
        elif tipo == "pokemon_saiu":
            segmentos = [self._segmento(pokemon), self._segmento(" saiu de campo.")]
        elif tipo == "pokemon_morreu":
            segmentos = [self._segmento(pokemon), self._segmento(" desmaiou.")]
        elif tipo == "captura_batalha_resultado":
            usuario = str(evento.get("usuario_nome") or executor)
            alvo_nome = str(evento.get("alvo_nome") or alvo)
            bola = str(evento.get("bola_nome") or "Pokeball")
            titulo, descricao = self._tooltip_captura(evento)
            chance = self._formatar_numero(evento.get("chance_real_3_checks", 0.0))
            if bool(evento.get("capturado", False)):
                segmentos = [self._segmento(usuario), self._segmento(" capturou "), self._segmento(alvo_nome), self._segmento(" com "), self._segmento(bola), self._segmento(" ("), self._segmento(f"{chance}%", atributo="per", titulo=titulo, descricao=descricao), self._segmento(").")]
            else:
                segmentos = [self._segmento(usuario), self._segmento(" tentou capturar "), self._segmento(alvo_nome), self._segmento(" com "), self._segmento(bola), self._segmento(", mas falhou ("), self._segmento(f"{chance}%", atributo="per", titulo=titulo, descricao=descricao), self._segmento(").")]
        elif tipo in {"passiva", "passivo"}:
            nome_passiva = str(evento.get("passiva") or evento.get("nome") or "Passiva")
            segmentos = [self._segmento("Passiva "), self._segmento(nome_passiva), self._segmento(" ativou em "), self._segmento(pokemon)]
            atributos = []
            for chave in ("Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Amp", "Dur"):
                if chave in evento:
                    atributos.append(f"{chave} {self._formatar_numero(evento.get(chave))}")
            if atributos:
                segmentos.extend([self._segmento(": "), self._segmento(", ".join(atributos))])
            segmentos.append(self._segmento("."))
        elif tipo == "acao":
            texto = str(evento.get("texto") or "").strip()
            if texto:
                segmentos = [self._segmento(texto)]
            else:
                ataque = str(evento.get("ataque") or "ação")
                destino = evento.get("destino")
                if str(evento.get("estilo") or "").strip().casefold() == "movimento" and destino is not None:
                    segmentos = [
                        self._segmento(executor),
                        self._segmento(" começou a se mover em direção a "),
                        self._segmento(self._formatar_posicao(destino)),
                        self._segmento("."),
                    ]
                else:
                    segmentos = [
                        self._segmento(executor),
                        self._segmento(" usou "),
                        self._segmento(ataque),
                        self._segmento("."),
                    ]
        elif tipo == "movimento":
            segmentos = [
                self._segmento(pokemon),
                self._segmento(" moveu-se até "),
                self._segmento(self._formatar_posicao(evento.get("posicao"))),
                self._segmento("."),
            ]
            if bool(evento.get("interrompido_por_colisao", False)):
                segmentos.append(self._segmento(" O deslocamento foi interrompido por colisão."))
        elif tipo == "objeto":
            fase_objeto = str(evento.get("fase_objeto") or "").strip().casefold()
            subtipo = str(evento.get("subtipo") or "objeto").strip()
            if fase_objeto == "criado":
                segmentos = [
                    self._segmento(executor),
                    self._segmento(" iniciou "),
                    self._segmento(subtipo),
                    self._segmento(" a partir de "),
                    self._segmento(self._formatar_posicao(evento.get("origem") or evento.get("posicao"))),
                    self._segmento("."),
                ]
            elif fase_objeto == "finalizado":
                segmentos = [
                    self._segmento(subtipo),
                    self._segmento(" terminou em "),
                    self._segmento(self._formatar_posicao(evento.get("destino") or evento.get("posicao"))),
                    self._segmento("."),
                ]
            else:
                segmentos = [
                    self._segmento(subtipo),
                    self._segmento(" avançou para "),
                    self._segmento(self._formatar_posicao(evento.get("destino") or evento.get("posicao"))),
                    self._segmento("."),
                ]
        elif tipo == "dano":
            titulo, descricao = self._tooltip_dano(evento)
            segmentos = [
                self._segmento(executor),
                self._segmento(" causou "),
                self._segmento(self._formatar_numero(evento.get("dano", 0.0)), atributo=self._atributo_dano(evento), titulo=titulo, descricao=descricao),
                self._segmento(" de dano em "),
                self._segmento(alvo),
                self._segmento("."),
            ]
            if self._numero(evento.get("dano_barreira"), 0.0) > 0.0:
                segmentos.extend(
                    [
                        self._segmento(" "),
                        self._segmento(self._formatar_numero(evento.get("dano_barreira", 0.0)), atributo="def", titulo=titulo, descricao=descricao),
                        self._segmento(" atingiram a barreira."),
                    ]
                )
            if bool(evento.get("critico", False)):
                segmentos.append(self._segmento(" Foi um acerto crítico."))
        elif tipo == "cura":
            titulo, descricao = self._tooltip_vida("Detalhes da cura", evento.get("valor", 0.0), evento.get("vida_antes", 0.0), evento.get("vida_depois", 0.0))
            segmentos = [
                self._segmento(executor),
                self._segmento(" curou "),
                self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="vida", titulo=titulo, descricao=descricao),
                self._segmento(" de Vida em "),
                self._segmento(alvo),
                self._segmento("."),
            ]
        elif tipo == "barreira":
            titulo, descricao = self._tooltip_barreira(evento.get("valor", 0.0), evento.get("barreira_total", 0.0))
            segmentos = [
                self._segmento(executor),
                self._segmento(" concedeu "),
                self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="def", titulo=titulo, descricao=descricao),
                self._segmento(" de barreira para "),
                self._segmento(alvo),
                self._segmento("."),
            ]
        elif tipo == "energia":
            titulo, descricao = self._tooltip_energia(evento.get("valor", 0.0), evento.get("energia", 0.0), str(evento.get("motivo") or ""))
            segmentos = [
                self._segmento(pokemon),
                self._segmento(" alterou "),
                self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="ene", titulo=titulo, descricao=descricao),
                self._segmento(" de energia."),
            ]
        elif tipo == "efeito":
            efeito = str(evento.get("efeito") or "efeito")
            if str(evento.get("fase_efeito") or "").strip().casefold() == "expirado":
                segmentos = [self._segmento(efeito), self._segmento(" expirou em "), self._segmento(alvo), self._segmento(".")]
            else:
                alvo_real = alvo if alvo != "Combatente" else executor
                executor_real = executor if executor != "Combatente" else alvo_real
                segmentos = [self._segmento(executor_real), self._segmento(" aplicou "), self._segmento(efeito), self._segmento(" em "), self._segmento(alvo_real), self._segmento(".")]
        elif tipo == "troca":
            saiu = str(evento.get("saiu_nome") or evento.get("saiu") or "alguém")
            entrou = str(evento.get("entrou_nome") or evento.get("entrou") or "alguém")
            segmentos = [self._segmento(executor), self._segmento(" trocou "), self._segmento(saiu), self._segmento(" por "), self._segmento(entrou), self._segmento(".")]
        elif tipo == "fim_turno":
            motivo = str(evento.get("motivo") or "efeito de rodada")
            segmentos = [self._segmento(pokemon), self._segmento(f" sofreu {motivo}: ")]
            if "dano" in evento:
                titulo, descricao = self._tooltip_vida("Detalhes do dano passivo", evento.get("dano", 0.0), evento.get("vida_antes", 0.0), evento.get("vida_depois", 0.0))
                segmentos.extend([self._segmento(self._formatar_numero(evento.get("dano", 0.0)), atributo="atk", titulo=titulo, descricao=descricao), self._segmento(" de dano.")])
            elif "cura" in evento:
                titulo, descricao = self._tooltip_vida("Detalhes da cura passiva", evento.get("cura", 0.0), evento.get("vida_antes", 0.0), evento.get("vida_depois", 0.0))
                segmentos.extend([self._segmento(self._formatar_numero(evento.get("cura", 0.0)), atributo="vida", titulo=titulo, descricao=descricao), self._segmento(" de cura.")])
            elif "energia" in evento:
                titulo, descricao = self._tooltip_energia(evento.get("energia", 0.0), evento.get("energia_total", 0.0), motivo)
                segmentos.extend([self._segmento(self._formatar_numero(evento.get("energia", 0.0)), atributo="ene", titulo=titulo, descricao=descricao), self._segmento(" de energia.")])
            else:
                segmentos.append(self._segmento("sem alterações numéricas."))
        elif tipo == "recoil":
            titulo, descricao = self._tooltip_vida("Detalhes do recuo", evento.get("valor", 0.0), evento.get("valor", 0.0), 0.0)
            segmentos = [self._segmento(executor), self._segmento(" recebeu "), self._segmento(self._formatar_numero(evento.get("valor", 0.0)), atributo="atk", titulo=titulo, descricao=descricao), self._segmento(" de recuo.")]
        elif tipo == "execucao":
            segmentos = [self._segmento(executor), self._segmento(" executou "), self._segmento(alvo), self._segmento(".")]
        elif tipo == "jogada_descartada":
            ataque = str(evento.get("ataque") or "a jogada")
            motivo = str(evento.get("motivo") or "motivo não informado")
            segmentos = [self._segmento(executor), self._segmento(" teve "), self._segmento(ataque), self._segmento(f" descartado: {motivo}.")]
        elif tipo in {"acao_bloqueada", "impacto_cancelado", "acao_finalizada"}:
            ataque = str(evento.get("ataque") or "ação")
            motivo = str(evento.get("motivo") or "")
            segmentos = [self._segmento(executor), self._segmento(" encerrou "), self._segmento(ataque)]
            if motivo:
                segmentos.append(self._segmento(f" por {motivo}"))
            segmentos.append(self._segmento("."))
        elif tipo == "reset_variacoes":
            segmentos = [self._segmento(executor), self._segmento(" zerou as variações de "), self._segmento(alvo), self._segmento(".")]
        else:
            segmentos = [self._segmento(f"{executor}: evento {tipo or 'desconhecido'}.")]

        cor_fundo, cor_borda, cor_faixa = self._cores_evento(tipo, evento)
        return {
            "tipo": tipo,
            "tick": int(tick),
            "fase_label": self._FASES_LABEL.get(fase, fase.title()),
            "cor_fundo": cor_fundo,
            "cor_borda": cor_borda,
            "cor_faixa": cor_faixa,
            "segmentos": segmentos,
        }

    def _achatar_eventos(self, log: Dict[str, object] | None) -> list[dict[str, object]]:
        saida: list[dict[str, object]] = []
        movimentos_finais: dict[str, dict[str, object]] = {}

        def flush_movimentos():
            nonlocal saida
            if not movimentos_finais:
                return
            for chave in sorted(movimentos_finais.keys(), key=lambda item: (movimentos_finais[item]["tick"], item)):
                saida.append(dict(movimentos_finais[chave]))
            movimentos_finais.clear()

        historico = [dict(item) for item in list((log or {}).get("historico") or []) if isinstance(item, dict)]
        if historico and any(isinstance(item.get("evento"), dict) for item in historico):
            for idx, item in enumerate(historico, start=1):
                evento = self._evento_plano(dict(item.get("evento") or {}))
                if not self._evento_deve_aparecer(evento):
                    continue
                tick = int(item.get("tick", item.get("ordem", idx)) or 0)
                fase = str(item.get("fase") or "segmentacao")
                saida.append({"tick": tick, "fase": fase, "evento": evento})
            return saida
        if historico and any("tipo" in item for item in historico):
            atual = None
            for idx, evento in enumerate(historico, start=1):
                evento = self._evento_plano(evento)
                if not self._evento_deve_aparecer(evento):
                    continue
                tipo = str(evento.get("tipo") or "").strip().casefold()
                tick = int(evento.get("ordem") or idx)
                if tipo == "ataque_usado":
                    atual = {"tipo": "ataque_resumo", "base": dict(evento), "impactos": [], "falhas": [], "sem_alvo": False, "critico": False}
                    saida.append({"tick": tick, "fase": "segmentacao", "evento": atual})
                    continue
                if atual is not None and tipo in {"pokemon_sofreu_dano", "barreira_absorveu", "pokemon_recebeu_cura", "pokemon_ganhou_barreira", "pokemon_recebeu_efeito", "pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
                    impacto = dict(evento)
                    if tipo == "pokemon_recebeu_efeito":
                        impacto["tipo_efeito"] = str(evento.get("tipo_efeito") or evento.get("tipo_status") or evento.get("efeito_tipo") or evento.get("tipo") or "")
                        if not impacto["tipo_efeito"] and isinstance(evento.get("efeito"), dict):
                            impacto["tipo_efeito"] = str(evento["efeito"].get("tipo") or "")
                    atual["impactos"].append(impacto)
                    if bool(evento.get("critico", False)):
                        atual["critico"] = True
                    continue
                if atual is not None and tipo in {"ataque_errou", "ataque_desviado", "pokemon_desviou"}:
                    atual["falhas"].append(dict(evento))
                    continue
                if atual is not None and tipo == "ataque_sem_alvo_real":
                    atual["sem_alvo"] = True
                    continue
                if atual is not None and tipo == "acao_falhou":
                    atual["falhas"].append(dict(evento))
                    continue
                if tipo in {"ataque_acertou", "acao_iniciada", "pokemon_gastou_energia", "pokemon_ganhou_energia", "efeito_tickou", "pokemon_entrou", "pokemon_saiu"}:
                    continue
                if atual is not None and tipo in {"passiva", "passivo", "pokemon_morreu"}:
                    saida.append({"tick": tick, "fase": "segmentacao", "evento": evento})
                    continue
                atual = None
                saida.append({"tick": tick, "fase": "segmentacao", "evento": evento})
            return saida
        for bloco in historico:
            tick = int(bloco.get("tick", 0) or 0)
            for fase in ("inicializacao", "segmentacao", "passiva", "finalizacao"):
                for evento in [dict(item) for item in list(bloco.get(fase) or []) if isinstance(item, dict)]:
                    if not self._evento_deve_aparecer(evento):
                        continue
                    tipo = str(evento.get("tipo") or "").strip().casefold()
                    if tipo == "movimento":
                        pokemon_id = str(evento.get("pokemon_id") or "")
                        if pokemon_id:
                            movimentos_finais[pokemon_id] = {"tick": tick, "fase": fase, "evento": evento}
                        continue
                    if tipo == "objeto" and str(evento.get("fase_objeto") or "").strip().casefold() == "movimento":
                        continue
                    flush_movimentos()
                    saida.append({"tick": tick, "fase": fase, "evento": evento})
        flush_movimentos()
        return saida

    @staticmethod
    def _evento_plano(evento: Dict[str, object]) -> Dict[str, object]:
        out = dict(evento or {})
        dados = out.get("dados") if isinstance(out.get("dados"), dict) else {}
        if isinstance(dados.get("dados"), dict):
            for chave, valor in dict(dados.get("dados") or {}).items():
                dados.setdefault(chave, valor)
        for chave, valor in dados.items():
            if chave == "tipo" and "tipo" in out:
                out.setdefault("tipo_efeito", valor)
            else:
                out.setdefault(chave, valor)
        return out

    def _evento_deve_aparecer(self, evento: Dict[str, object]) -> bool:
        evento = self._evento_plano(evento)
        tipo = str(evento.get("tipo") or "").strip().casefold()
        ocultos = {
            "rodada_iniciada",
            "rodada_finalizada",
            "batalha_finalizada",
            "acao_iniciada",
            "pokemon_gastou_energia",
            "pokemon_ganhou_energia",
            "efeito_tickou",
            "ataque_acertou",
            "pokemon_entrou",
            "pokemon_saiu",
            "captura_batalha_lancada",
            "inventario_atualizado_batalha",
        }
        if tipo in ocultos:
            return False
        if tipo != "dano":
            return True
        detalhes = dict(evento.get("detalhes") or {})
        dano_bruto = self._numero(detalhes.get("dano_bruto"), self._numero(evento.get("dano"), 0.0))
        dano_final = self._numero(evento.get("dano"), 0.0)
        dano_barreira = self._numero(evento.get("dano_barreira"), 0.0)
        return not (self._aprox(dano_bruto, 0.0) and self._aprox(dano_final, 0.0) and self._aprox(dano_barreira, 0.0))

    def registros_rodada(self, rodada: int, log: Dict[str, object] | None, replay: Dict[str, object]) -> list[dict[str, object]]:
        if not isinstance(log, dict):
            if int(rodada) <= 1:
                return [
                    self._registro_placeholder(
                        "Os registros da rodada 1 aparecerão aqui assim que a primeira resolução do combate chegar.",
                        subtitulo="Aguardando primeira rodada",
                    )
                ]
            return [self._registro_placeholder("Ainda não existe um log salvo para esta rodada.", subtitulo="Rodada indisponível")]

        eventos = self._achatar_eventos(log)
        replay_ativo = bool(replay.get("ativo", False))
        turno_replay = int(replay.get("turno_atual", replay.get("rodada_atual", 0)) or 0)
        if replay_ativo and turno_replay == int(rodada):
            tick_atual = max(0, int(replay.get("tick_atual", 0) or 0))
            eventos = eventos[:tick_atual]
            if not eventos:
                return [
                    self._registro_placeholder(
                        "As acoes vao surgir em ordem conforme a animacao do combate avanca.",
                        subtitulo="Reproduzindo rodada",
                    )
                ]

        registros = [self._registro_evento(dict(item.get("evento") or {}), int(item.get("tick", 0) or 0), str(item.get("fase") or "")) for item in eventos]
        if not registros:
            return [self._registro_placeholder("Esta rodada não trouxe registros visíveis para o jogador.", subtitulo="Rodada vazia")]
        return registros

