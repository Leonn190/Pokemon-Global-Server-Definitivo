from __future__ import annotations

import copy
import math

from Codigo.ModulosBatalha.AnimadorAtaquesBatalha import AnimadorAtaquesBatalha
from Codigo.Visual.PokemonBatalhaAnimator import PokemonAnimator

EVENTOS_IMPACTO = {
    "ataque_acertou",
    "ataque_errou",
    "ataque_desviado",
    "pokemon_desviou",
    "pokemon_sofreu_dano",
    "barreira_absorveu",
    "pokemon_recebeu_cura",
    "pokemon_ganhou_barreira",
    "pokemon_recebeu_efeito",
    "pokemon_variou_atributo",
    "atributo_variou",
    "pokemon_alterou_atributo",
}


class ControladorAnimacoes:
    def __init__(self, controlador):
        self.controlador = controlador
        self.animator = PokemonAnimator(controlador)
        self.fila: list[dict[str, object]] = []
        self._avisos: list[str] = []
        self._tempo = 0.0
        self._agendados: list[dict[str, object]] = []
        self._ataques_ativos: list[dict[str, object]] = []
        self.animador_ataques = AnimadorAtaquesBatalha(self)

    def receber_evento(self, evento):
        delay = self._delay_para_evento(evento)
        if delay and delay > 0.001:
            self.agendar_callback(delay, lambda ev=copy.deepcopy(evento): self._executar_evento(ev))
            return delay
        self._executar_evento(evento)
        return 0.0

    def _executar_evento(self, evento):
        try:
            animacoes = self.criar_animacao_de_evento(evento)
        except Exception as exc:
            self._avisos.append(f"animacao_falhou:{exc}")
            return
        for anim in list(animacoes or []):
            if anim is not None:
                self.adicionar_animacao(anim, bloqueante=bool(anim.get("bloqueante", True)) if isinstance(anim, dict) else True)

    def agendar_callback(self, delay, callback):
        if not callable(callback):
            return None
        self._agendados.append({"delay": max(0.0, float(delay or 0.0)), "callback": callback})
        return delay

    def criar_animacao_de_evento(self, evento):
        dados = self._dados(evento)
        tipo = str((evento or {}).get("tipo") or "").strip()
        ctrl = self.controlador
        out = []

        if tipo == "ataque_usado":
            out.extend(self._animar_ataque_usado(dados))
        elif tipo in {"ataque_acertou", "ataque_sem_alvo_real"}:
            return []
        elif tipo in {"ataque_desviado", "pokemon_desviou", "ataque_errou"}:
            alvo = ctrl.pokemons_por_id.get(str(dados.get("alvo_id") or dados.get("pokemon_id") or ""))
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

    def _animar_ataque_usado(self, dados):
        return self.animador_ataques.animar_ataque_usado(dados)

    def _delay_para_evento(self, evento):
        tipo = str((evento or {}).get("tipo") or "")
        if tipo not in EVENTOS_IMPACTO:
            return 0.0
        dados = self._dados(evento)
        contexto = self._contexto_ativo_para_evento(dados)
        if not contexto:
            return 0.0
        alvo_id = str(dados.get("alvo_id") or dados.get("pokemon_id") or "")
        if not alvo_id:
            return 0.0
        impacto_abs = (contexto.get("impactos") or {}).get(alvo_id)
        if impacto_abs is None and contexto.get("modelo") == "Explosao" and self._evento_impacto_secundario_explosao(contexto, dados, alvo_id):
            impacto_abs = self._impacto_explosao_para_alvo(contexto, alvo_id)
            if impacto_abs is not None:
                contexto.setdefault("impactos", {})[alvo_id] = impacto_abs
                efeito_sec = (contexto.get("animacao") or {}).get("efeito_impacto_secundario")
                alvo = self.controlador.pokemons_por_id.get(alvo_id)
                if efeito_sec and alvo is not None:
                    self.agendar_callback(max(0.0, impacto_abs - self._tempo), lambda p=alvo, e=efeito_sec: self.animator.animar_efeito(p, e, posicao="alvo"))
        if impacto_abs is None:
            return 0.0
        return max(0.0, float(impacto_abs) - self._tempo)

    def pode_processar_evento_durante_animacao(self, evento):
        tipo = str((evento or {}).get("tipo") or "")
        if tipo not in EVENTOS_IMPACTO:
            return False
        return self._contexto_ativo_para_evento(self._dados(evento)) is not None

    def adicionar_animacao(self, animacao, bloqueante=True):
        if isinstance(animacao, dict):
            animacao["bloqueante"] = bool(bloqueante)
        return animacao

    def executar_proxima(self):
        return None

    def atualizar(self, dt):
        dt = max(0.0, float(dt or 0.0))
        self._tempo += dt
        restantes = []
        for item in list(self._agendados):
            item["delay"] = float(item.get("delay", 0.0)) - dt
            if float(item.get("delay", 0.0)) <= 0.0:
                try:
                    item["callback"]()
                except Exception as exc:
                    self._avisos.append(f"callback_animacao_falhou:{exc}")
            else:
                restantes.append(item)
        self._agendados = restantes
        self._ataques_ativos = [ctx for ctx in self._ataques_ativos if float(ctx.get("fim", 0.0)) + 2.0 >= self._tempo]
        self.animator.atualizar(dt)

    def desenhar(self, surface):
        self.animator.desenhar(surface)

    def esta_ocupado(self):
        return bool(self._agendados) or self.animator.esta_ocupado()

    def _tempo_onda(self, principal, alvo, raio, duracao):
        p0 = self.animator._posicao_mundo(principal)
        p1 = self.animator._posicao_mundo(alvo)
        if p0 is None or p1 is None:
            return float(duracao or 0.45)
        dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        return float(duracao or 0.45) * max(0.0, min(1.0, dist / max(0.1, float(raio or 1.5))))

    def _impacto_explosao_para_alvo(self, contexto, alvo_id):
        principal = contexto.get("principal")
        alvo = self.controlador.pokemons_por_id.get(str(alvo_id))
        if principal is None or alvo is None:
            return None
        base = float(contexto.get("impacto_principal") or self._tempo)
        return base + self._tempo_onda(principal, alvo, contexto.get("raio_explosao") or 1.5, contexto.get("duracao_onda") or 0.45)

    def _evento_impacto_secundario_explosao(self, contexto, dados, alvo_id):
        if not alvo_id or str(alvo_id) == str(contexto.get("principal_id") or ""):
            return False
        if bool(dados.get("impacto_secundario")):
            return True
        return str(alvo_id) in set(contexto.get("secundarios_ids") or set())

    def _contexto_ativo_para_evento(self, dados):
        ataque_id = str(dados.get("ataque_id") or "")
        ataque_nome = str(dados.get("ataque_nome") or "")
        origem_id = str(dados.get("origem_id") or dados.get("usuario_id") or "")
        for ctx in reversed(self._ataques_ativos):
            if ataque_id and ctx.get("ataque_id") and ataque_id != ctx.get("ataque_id"):
                continue
            if ataque_nome and ctx.get("ataque_nome") and ataque_nome != ctx.get("ataque_nome"):
                continue
            if origem_id and ctx.get("usuario_id") and origem_id != ctx.get("usuario_id"):
                continue
            return ctx
        return None

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
