from __future__ import annotations

import unicodedata

from Codigo.Visual.PokemonBatalhaAnimator import PokemonAnimator


def _normalizar_nome(valor):
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


class ControladorAnimacoes:
    def __init__(self, controlador):
        self.controlador = controlador
        self.animator = PokemonAnimator(controlador)
        self.fila: list[dict[str, object]] = []
        self._avisos: list[str] = []

    def receber_evento(self, evento):
        try:
            animacoes = self.criar_animacao_de_evento(evento)
        except Exception as exc:
            self._avisos.append(f"animacao_falhou:{exc}")
            return
        for anim in list(animacoes or []):
            if anim is not None:
                self.adicionar_animacao(anim, bloqueante=bool(anim.get("bloqueante", True)) if isinstance(anim, dict) else True)

    def criar_animacao_de_evento(self, evento):
        dados = self._dados(evento)
        tipo = str((evento or {}).get("tipo") or "").strip()
        ctrl = self.controlador
        out = []

        if tipo == "ataque_usado":
            usuario = ctrl.pokemons_por_id.get(str(dados.get("usuario_id") or dados.get("pokemon_id") or ""))
            alvo = self._resolver_alvo(dados)
            animacao = dados.get("animacao") if isinstance(dados.get("animacao"), dict) else {}
            contato = self._contato_ataque(dados, animacao)
            tipo_ataque = dados.get("tipo_ataque") or animacao.get("tipo_ataque") or animacao.get("tipo")
            if animacao.get("efeito_usuario"):
                out.append(self.animator.animar_efeito(usuario, animacao.get("efeito_usuario"), posicao="usuario"))
            if contato == "avanco":
                out.append(self.animator.animar_avanco(usuario, alvo))
            elif contato == "salto":
                out.append(self.animator.animar_salto(usuario, alvo))
            elif contato == "laser_linha":
                linha = self._linha_alvo(dados)
                if linha:
                    out.append(self.animator.animar_laser_linha(usuario, linha[0], linha[-1], tipo_ataque=tipo_ataque))
                else:
                    out.append(self.animator.animar_laser(usuario, alvo, tipo_ataque=tipo_ataque))
            elif contato in {"laser", "raio", "jato_liquido"}:
                out.append(self.animator.animar_contato_irregular(contato, usuario, alvo, tipo_ataque=tipo_ataque))
            elif contato == "tiro":
                projetil = animacao.get("projetil") if animacao.get("projetil") is not None else dados.get("projetil")
                out.append(self.animator.animar_lancar_projetil(usuario, alvo, sprite=projetil, tipo_ataque=tipo_ataque))
        elif tipo == "ataque_acertou":
            alvo = self._resolver_alvo(dados)
            animacao = dados.get("animacao") if isinstance(dados.get("animacao"), dict) else {}
            efeito = dados.get("efeito_alvo") or animacao.get("efeito_alvo")
            if efeito:
                out.append(self.animator.animar_efeito(alvo, efeito, posicao="alvo"))
        elif tipo == "ataque_sem_alvo_real":
            alvo = self._resolver_alvo(dados)
            animacao = dados.get("animacao") if isinstance(dados.get("animacao"), dict) else {}
            efeito = dados.get("efeito_alvo") or animacao.get("efeito_alvo")
            if efeito:
                out.append(self.animator.animar_efeito(alvo, efeito, posicao="alvo"))
        elif tipo in {"ataque_desviado", "pokemon_desviou", "ataque_errou"}:
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            alvo_animacao = alvo or self._resolver_alvo(dados)
            animacao = dados.get("animacao") if isinstance(dados.get("animacao"), dict) else {}
            efeito = dados.get("efeito_alvo") or animacao.get("efeito_alvo")
            if efeito:
                out.append(self.animator.animar_efeito(alvo_animacao, efeito, posicao="alvo"))
            out.append(self.animator.animar_desvio(alvo))
            out.append(self.animator.exibir_cartucho(alvo, "DESVIO", "desvio"))
        elif tipo == "pokemon_sofreu_dano":
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            valor = dados.get("valor")
            critico = bool(dados.get("critico", False))
            out.append(self.animator.animar_tomar_dano(alvo, valor=valor))
            out.append(self.animator.exibir_cartucho(alvo, self._fmt(valor), "dano", valor=valor, critico=critico))
        elif tipo == "barreira_absorveu":
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            valor = dados.get("dano_barreira") or dados.get("valor")
            out.append(self.animator.animar_efeito(alvo, "BarreiraCelular"))
            out.append(self.animator.exibir_cartucho(alvo, "bloqueado" if dados.get("protegido") else self._fmt(valor), "barreira", valor=valor))
        elif tipo == "pokemon_recebeu_cura":
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            valor = dados.get("valor")
            critico = bool(dados.get("critico", False))
            out.append(self.animator.animar_receber_cura(alvo, valor=valor))
            out.append(self.animator.exibir_cartucho(alvo, f"+{self._fmt(valor)}", "cura", valor=valor, critico=critico))
            if alvo is not None and hasattr(alvo, "animar_variacao_status"):
                alvo.animar_variacao_status(True)
        elif tipo == "pokemon_ganhou_barreira":
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
            out.append(self.animator.animar_efeito(alvo, "BarreiraCelular"))
            out.append(self.animator.exibir_cartucho(alvo, f"+{self._fmt(dados.get('valor'))}", "barreira", valor=dados.get("valor")))
            if alvo is not None and hasattr(alvo, "animar_variacao_status"):
                alvo.animar_variacao_status(True)
        elif tipo == "pokemon_recebeu_efeito":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            efeito = dados.get("efeito") if isinstance(dados.get("efeito"), dict) else {}
            nome = dados.get("efeito_gif") or efeito.get("gif") or dados.get("efeito_visual")
            if nome:
                out.append(self.animator.animar_efeito(poke, nome))
            if poke is not None:
                if hasattr(poke, "aplicar_efeito_visual") and efeito:
                    poke.aplicar_efeito_visual(efeito)
                if hasattr(poke, "animar_variacao_status"):
                    negativo = bool((efeito or {}).get("negativo")) or str(dados.get("tipo") or (efeito or {}).get("tipo") or "").lower() == "negativo"
                    efeito_dados = efeito.get("dados") if isinstance(efeito.get("dados"), dict) else {}
                    atributo = dados.get("atributo") or efeito.get("atributo") or efeito_dados.get("atributo")
                    valor = dados.get("valor") if dados.get("valor") is not None else efeito.get("valor", efeito_dados.get("valor"))
                    poke.animar_variacao_status(not negativo, atributo=atributo, valor=valor)
        elif tipo in {"pokemon_variou_atributo", "atributo_variou", "pokemon_alterou_atributo"}:
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or dados.get("alvo_id") or ""))
            atributo = dados.get("atributo") or dados.get("stat") or dados.get("chave")
            valor = dados.get("valor") if dados.get("valor") is not None else dados.get("variacao")
            positivo = self._positivo(valor, dados)
            if poke is not None and hasattr(poke, "animar_variacao_status"):
                poke.animar_variacao_status(positivo, atributo=atributo, valor=valor)
            out.append(self.animator.exibir_cartucho_atributo(poke, atributo, valor, positivo=positivo))
        elif tipo == "efeito_tickou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None:
                poke.atualizar_timer_efeito(dados.get("efeito_code"), dados.get("efeito_nome"), dados.get("passos_depois"))
        elif tipo == "efeito_expirou":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None:
                poke.expirar_efeito_visual(dados.get("efeito_code"), dados.get("efeito_nome"))
        elif tipo == "pokemon_moveu":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            out.append(self.animator.animar_movimento(poke, dados.get("area_destino")))
        elif tipo == "pokemon_trocou_posicao":
            a = ctrl.pokemons_por_id.get(str(dados.get("pokemon_a_id") or ""))
            b = ctrl.pokemons_por_id.get(str(dados.get("pokemon_b_id") or ""))
            out.append(self.animator.animar_troca_posicao(a, b, dados.get("area_a_depois"), dados.get("area_b_depois")))
        elif tipo == "pokemon_trocou_reserva":
            saiu = ctrl.pokemons_por_id.get(str(dados.get("pokemon_saiu_id") or ""))
            entrou = ctrl.pokemons_por_id.get(str(dados.get("pokemon_entrou_id") or ""))
            out.append(self.animator.animar_troca(saiu, entrou, origem_saida=dados.get("area_id"), destino_entrada=dados.get("area_id")))
        elif tipo == "pokemon_morreu":
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            out.append(self.animator.animar_morrer(poke))
        elif tipo == "captura_batalha_resultado":
            usuario = ctrl.pokemons_por_id.get(str(dados.get("usuario_id") or ""))
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or ""))
            lado_origem = dados.get("lado_id", getattr(usuario, "lado_id", None))
            origem = ctrl.posicao_captura_lado_mundo(lado_origem) if hasattr(ctrl, "posicao_captura_lado_mundo") else None
            out.append(self.animator.animar_captura_batalha(origem or usuario, alvo, dados))
        elif tipo in {"passiva", "passivo"}:
            poke = ctrl.pokemons_por_id.get(str(dados.get("pokemon_id") or ""))
            if poke is not None and hasattr(poke, "animar_variacao_status"):
                atributo, valor = self._atributo_em_dados(dados)
                poke.animar_variacao_status(True, atributo=atributo, valor=valor)
                out.append(self.animator.exibir_cartucho_atributo(poke, atributo, valor, positivo=self._positivo(valor, dados)))

        return [a for a in out if a is not None]

    def adicionar_animacao(self, animacao, bloqueante=True):
        if isinstance(animacao, dict):
            animacao["bloqueante"] = bool(bloqueante)
        return animacao

    def executar_proxima(self):
        return None

    def atualizar(self, dt):
        self.animator.atualizar(dt)

    def desenhar(self, surface):
        self.animator.desenhar(surface)

    def esta_ocupado(self):
        return self.animator.esta_ocupado()

    def _resolver_alvo(self, dados):
        ctrl = self.controlador
        for pid in list(dados.get("alvos_ids") or []):
            poke = ctrl.pokemons_por_id.get(str(pid))
            if poke is not None:
                return poke
        if dados.get("alvo_id"):
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id")))
            if poke is not None:
                return poke
        area = dados.get("area_alvo_real") or dados.get("area_alvo")
        if area and getattr(ctrl, "arena", None) is not None:
            return ctrl.arena.centro_area(area)
        return None

    def _contato_ataque(self, dados, animacao):
        contato = _normalizar_nome(animacao.get("contato") or dados.get("contato") or "nenhum")
        return {
            "avanco": "avanco",
            "salto": "salto",
            "tiro": "tiro",
            "laser": "laser",
            "raio": "raio",
            "jatoliquido": "jato_liquido",
            "laserlinha": "laser_linha",
        }.get(contato, "nenhum")

    def _linha_alvo(self, dados):
        area_id = str(dados.get("area_alvo") or dados.get("area_alvo_real") or "").upper()
        if not area_id or getattr(self.controlador, "arena", None) is None:
            return []
        try:
            idx = int(area_id[1:]) - 1
        except (TypeError, ValueError, IndexError):
            return []
        prefixo = area_id[:1]
        row = idx // 3
        centros = [self.controlador.arena.centro_area(f"{prefixo}{row * 3 + col + 1}") for col in range(3)]
        return [centro for centro in centros if centro is not None]

    @staticmethod
    def _dados(evento):
        dados = dict((evento or {}).get("dados") or {})
        if isinstance(dados.get("dados"), dict):
            for chave, valor in dict(dados.get("dados") or {}).items():
                dados.setdefault(chave, valor)
        for chave, valor in dict(evento or {}).items():
            if chave not in {"dados"} and chave not in dados:
                dados[chave] = valor
        return dados

    @staticmethod
    def _positivo(valor, dados=None):
        dados = dados or {}
        if "positivo" in dados:
            return bool(dados.get("positivo"))
        if "negativo" in dados:
            return not bool(dados.get("negativo"))
        try:
            return float(valor) >= 0
        except (TypeError, ValueError):
            return True

    @staticmethod
    def _atributo_em_dados(dados):
        for chave in ("atributo", "stat", "chave"):
            if dados.get(chave):
                valor = dados.get("valor") if dados.get("valor") is not None else dados.get("variacao")
                return dados.get(chave), valor
        for chave in ("Vida", "Atk", "SpA", "Def", "SpD", "Mag", "Ene", "Vel", "Per", "Int", "Vamp", "CrC", "CrD", "Dur", "Amp"):
            if chave in dados:
                return chave, dados.get(chave)
        return None, None

    @staticmethod
    def _fmt(valor):
        try:
            num = float(valor)
        except (TypeError, ValueError):
            return str(valor or "0")
        if abs(num - round(num)) < 0.001:
            return str(int(round(num)))
        return f"{num:.1f}".rstrip("0").rstrip(".")
