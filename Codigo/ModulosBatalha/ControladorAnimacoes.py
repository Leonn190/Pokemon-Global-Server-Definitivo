from __future__ import annotations

import copy
import math
import unicodedata
from pathlib import Path

from Codigo.Visual.PokemonBatalhaAnimator import PokemonAnimator
from Codigo.Visual.AuxiliaresVisuais import EFEITOS_ATAQUE_FPS


MODELOS_VISUAIS = {
    "efeitoproprio": "EfeitoProprio",
    "efeitoalvo": "EfeitoAlvo",
    "avanco": "Avanco",
    "salto": "Salto",
    "raio": "Raio",
    "laser": "Laser",
    "jato": "Jato",
    "projetil": "Projetil",
    "explosao": "Explosao",
}

CONTATOS_EXPLOSAO = {"projetil": "Projetil", "avanco": "Avanco", "salto": "Salto", "raio": "Raio", "jato": "Jato"}
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


def _normalizar_nome(valor):
    bruto = unicodedata.normalize("NFKD", str(valor or "").strip().casefold())
    sem_acento = "".join(ch for ch in bruto if not unicodedata.combining(ch))
    return "".join(ch for ch in sem_acento if ch.isalnum())


def _num(valor, default=None):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _cor(valor):
    if not (isinstance(valor, (list, tuple)) and len(valor) >= 3):
        return None
    try:
        return [max(0, min(255, int(valor[0]))), max(0, min(255, int(valor[1]))), max(0, min(255, int(valor[2])))]
    except (TypeError, ValueError):
        return None


class ControladorAnimacoes:
    def __init__(self, controlador):
        self.controlador = controlador
        self.animator = PokemonAnimator(controlador)
        self.fila: list[dict[str, object]] = []
        self._avisos: list[str] = []
        self._tempo = 0.0
        self._agendados: list[dict[str, object]] = []
        self._ataques_ativos: list[dict[str, object]] = []

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
        usuario = self.controlador.pokemons_por_id.get(str(dados.get("usuario_id") or dados.get("pokemon_id") or ""))
        animacao = dados.get("animacao") if isinstance(dados.get("animacao"), dict) else {}
        modelo = self._modelo(animacao)
        tipo_ataque = dados.get("tipo_ataque") or animacao.get("tipo_ataque") or animacao.get("tipo")
        alvos = self._resolver_alvos(dados, animacao)
        principal = self._resolver_principal(dados, alvos)
        self._validar_animacao(animacao, tipo_ataque=tipo_ataque)

        efeito_executor = animacao.get("efeito_executor")
        if efeito_executor:
            self.animator.animar_efeito(usuario, efeito_executor, posicao="executor")

        if modelo == "EfeitoProprio":
            self._registrar_ataque_ativo(dados, animacao, modelo, {}, self._tempo + float(animacao.get("duracao") or 0.15), principal)
            return []
        if modelo == "EfeitoAlvo":
            impactos = self._animar_efeitos_alvos(animacao, alvos, base_delay=0.0)
            fim = max((impacto + self._duracao_efeito(self._efeito_alvo(animacao, idx), animacao) for idx, (alvo_id, impacto) in enumerate(impactos.items(), start=1)), default=0.15)
            self._registrar_ataque_ativo(dados, animacao, modelo, impactos, self._tempo + fim + 0.1, principal)
            return []
        if modelo in {"Avanco", "Salto"}:
            impactos, fim = self._animar_deslocamento(usuario, alvos, animacao, modelo)
            self._animar_efeitos_alvos(animacao, alvos, impactos_rel=impactos)
            self._registrar_ataque_ativo(dados, animacao, modelo, impactos, self._tempo + fim, principal)
            return []
        if modelo == "Projetil":
            impactos, fim = self._animar_projeteis(usuario, alvos, animacao, tipo_ataque)
            self._animar_efeitos_alvos(animacao, alvos, impactos_rel=impactos)
            self._registrar_ataque_ativo(dados, animacao, modelo, impactos, self._tempo + fim, principal)
            return []
        if modelo in {"Raio", "Jato"}:
            impactos, fim = self._animar_raio_ou_jato(usuario, alvos, animacao, modelo, tipo_ataque)
            self._animar_efeitos_alvos(animacao, alvos, impactos_rel=impactos)
            self._registrar_ataque_ativo(dados, animacao, modelo, impactos, self._tempo + fim, principal)
            return []
        if modelo == "Laser":
            impactos, fim = self._animar_laser(usuario, alvos, animacao, tipo_ataque, dados)
            self._animar_efeitos_alvos(animacao, alvos, impactos_rel=impactos)
            self._registrar_ataque_ativo(dados, animacao, modelo, impactos, self._tempo + fim, principal)
            return []
        if modelo == "Explosao":
            if bool(animacao.get("multiplos_principais")) and len(alvos) > 1:
                for principal_explosao in alvos:
                    self._animar_explosao(usuario, principal_explosao, [], animacao, tipo_ataque, dados)
                return []
            self._animar_explosao(usuario, principal, [a for a in alvos if a is not principal], animacao, tipo_ataque, dados)
            return []
        return []

    def _animar_efeitos_alvos(self, animacao, alvos, base_delay=0.0, impactos_rel=None):
        impactos = {}
        delay = float(base_delay or 0.0)
        simultaneo = bool((animacao or {}).get("simultaneo", False)) and not impactos_rel
        for idx, alvo in enumerate(list(alvos or []), start=1):
            efeito = self._efeito_alvo(animacao, idx)
            alvo_id = str(getattr(alvo, "id_batalha", ""))
            impacto = float((impactos_rel or {}).get(alvo_id, 0.0 if simultaneo else delay))
            impactos[alvo_id] = impacto
            if efeito:
                self.agendar_callback(impacto, lambda p=alvo, e=efeito: self.animator.animar_efeito(p, e, posicao="alvo"))
            if not impactos_rel and not simultaneo:
                delay = self._proximo_delay(delay, self._duracao_efeito(efeito, animacao), animacao)
        return impactos

    def _animar_deslocamento(self, usuario, alvos, animacao, modelo):
        if not alvos:
            return {}, 0.0
        modo = "salto" if modelo == "Salto" else "avanco"
        velocidade = float(animacao.get("velocidade") or (7.0 if modelo == "Salto" else 8.0))
        altura = float(animacao.get("altura") or 1.25)
        retornar = bool(animacao.get("retornar", True))
        distancia = animacao.get("distancia_parada", "contato")
        if bool(animacao.get("simultaneo", False)):
            anim = self.animator.animar_deslocamento_ataque(usuario, alvos, modo=modo, velocidade=velocidade, altura=altura, distancia_parada=distancia, retornar=retornar)
            impactos_lista = list((anim or {}).get("impactos") or [])
            impactos = {str(getattr(alvo, "id_batalha", "")): float(impactos_lista[i]) for i, alvo in enumerate(alvos) if i < len(impactos_lista)}
            return impactos, float((anim or {}).get("duracao") or max(impactos.values(), default=0.4))
        impactos = {}
        inicio = 0.0
        fim = 0.0
        for alvo in alvos:
            dur_ida, dur_total = self._duracao_deslocamento(usuario, alvo, velocidade, distancia, retornar)
            self.agendar_callback(inicio, lambda p=usuario, a=alvo, m=modo, v=velocidade, h=altura, d=distancia, r=retornar: self.animator.animar_deslocamento_ataque(p, [a], modo=m, velocidade=v, altura=h, distancia_parada=d, retornar=r))
            impactos[str(getattr(alvo, "id_batalha", ""))] = inicio + dur_ida
            fim = max(fim, inicio + dur_total)
            inicio = self._proximo_delay(inicio, dur_total, animacao)
        return impactos, fim

    def _animar_projeteis(self, usuario, alvos, animacao, tipo_ataque):
        impactos = {}
        inicio = 0.0
        fim = 0.0
        velocidade = float(animacao.get("velocidade") or 8.0)
        tamanho = float(animacao.get("tamanho") or 16.0)
        projetil = animacao.get("projetil") or "Generico"
        cor_cfg = _cor(animacao.get("cor"))
        for alvo in alvos:
            dur = self._duracao_projetil(usuario, alvo, velocidade)
            self.agendar_callback(inicio, lambda a=alvo: self.animator.animar_lancar_projetil(usuario, a, sprite=projetil, tipo_ataque=tipo_ataque, velocidade=velocidade, tamanho=tamanho, cor=cor_cfg))
            impactos[str(getattr(alvo, "id_batalha", ""))] = inicio + dur
            fim = max(fim, inicio + dur)
            inicio = 0.0 if bool(animacao.get("simultaneo", False)) else self._proximo_delay(inicio, dur, animacao)
        return impactos, fim

    def _animar_raio_ou_jato(self, usuario, alvos, animacao, modelo, tipo_ataque):
        impactos = {}
        inicio = 0.0
        fim = 0.0
        dur = float(animacao.get("duracao") or (0.7 if modelo == "Jato" else 0.5))
        largura = float(animacao.get("largura") or (1.2 if modelo == "Jato" else 1.0))
        cor_cfg = _cor(animacao.get("cor"))
        metodo = self.animator.animar_jato if modelo == "Jato" else self.animator.animar_raio
        for alvo in alvos:
            self.agendar_callback(inicio, lambda a=alvo, fn=metodo: fn(usuario, a, tipo_ataque=tipo_ataque, duracao=dur, largura=largura, cor=cor_cfg))
            impactos[str(getattr(alvo, "id_batalha", ""))] = inicio + dur * 0.35
            fim = max(fim, inicio + dur)
            inicio = 0.0 if bool(animacao.get("simultaneo", False)) else self._proximo_delay(inicio, dur, animacao)
        return impactos, fim

    def _animar_laser(self, usuario, alvos, animacao, tipo_ataque, dados):
        if bool(animacao.get("simultaneo", False)):
            self._avisos.append("Laser recebeu simultaneo=true; valor ignorado.")
        dur = float(animacao.get("duracao") or 0.6)
        largura = float(animacao.get("largura") or 12.0)
        cor_cfg = _cor(animacao.get("cor"))
        impactos = {}
        fim = 0.0
        inicio = 0.0
        grupos = self._grupos_laser(alvos, dados)
        for grupo in grupos:
            linha = grupo.get("linha") or []
            alvos_grupo = grupo.get("alvos") or []
            if len(linha) >= 2:
                self.agendar_callback(inicio, lambda li=linha: self.animator.animar_laser_por_linha(usuario, li[0], li[-1], tipo_ataque=tipo_ataque, duracao=dur, largura=largura, cor=cor_cfg))
                impacto_local = inicio + dur * 0.55
            elif alvos_grupo:
                alvo = alvos_grupo[0]
                self.agendar_callback(inicio, lambda a=alvo: self.animator.animar_laser(usuario, a, tipo_ataque=tipo_ataque, duracao=dur, largura=largura, cor=cor_cfg))
                impacto_local = inicio + dur * 0.18
            else:
                continue
            for alvo in alvos_grupo:
                impactos[str(getattr(alvo, "id_batalha", ""))] = impacto_local
            fim = max(fim, inicio + dur)
            inicio = self._proximo_delay(inicio, dur, animacao)
        return impactos, fim

    def _animar_explosao(self, usuario, principal, secundarios, animacao, tipo_ataque, dados):
        if principal is None:
            return {}, 0.0
        contato = CONTATOS_EXPLOSAO.get(_normalizar_nome(animacao.get("contato")), "Projetil")
        contato_cfg = dict(animacao)
        contato_cfg["simultaneo"] = False
        if contato == "Projetil":
            impactos, fim_contato = self._animar_projeteis(usuario, [principal], contato_cfg, tipo_ataque)
        elif contato in {"Avanco", "Salto"}:
            impactos, fim_contato = self._animar_deslocamento(usuario, [principal], contato_cfg, contato)
        elif contato in {"Raio", "Jato"}:
            impactos, fim_contato = self._animar_raio_ou_jato(usuario, [principal], contato_cfg, contato, tipo_ataque)
        else:
            impactos, fim_contato = {}, 0.35
        pid_principal = str(getattr(principal, "id_batalha", ""))
        impacto_principal = impactos.get(pid_principal, fim_contato)
        efeito_principal = animacao.get("efeito_alvo")
        if efeito_principal:
            self.agendar_callback(impacto_principal, lambda: self.animator.animar_efeito(principal, efeito_principal, posicao="alvo"))
        dur_onda = float(animacao.get("duracao_onda") or 0.45)
        raio = float(animacao.get("raio_explosao") or 1.5)
        cor_onda = _cor(animacao.get("cor_onda")) or _cor(animacao.get("cor"))
        largura_onda = float(animacao.get("largura_onda") or 1.0)
        self.agendar_callback(impacto_principal, lambda: self.animator.animar_explosao_onda(principal, alvos=[], tipo_ataque=tipo_ataque, raio=raio, duracao=dur_onda, largura=largura_onda, cor=cor_onda))
        impactos[pid_principal] = impacto_principal
        fim = max([fim_contato, impacto_principal + dur_onda, *impactos.values()])
        contexto = self._registrar_ataque_ativo(dados, animacao, "Explosao", impactos, self._tempo + fim, principal)
        if contexto:
            contexto["raio_explosao"] = raio
            contexto["duracao_onda"] = dur_onda
            contexto["impacto_principal"] = self._tempo + impacto_principal
            contexto["secundarios_ids"] = {str(pid) for pid in list(dados.get("alvos_secundarios_ids") or []) if str(pid or "")}
        return impactos, fim

    def _registrar_ataque_ativo(self, dados, animacao, modelo, impactos_rel, fim_abs, principal):
        contexto = {
            "ataque_id": str(dados.get("ataque_id") or ""),
            "ataque_nome": str(dados.get("ataque_nome") or ""),
            "usuario_id": str(dados.get("usuario_id") or dados.get("pokemon_id") or ""),
            "modelo": modelo,
            "animacao": dict(animacao or {}),
            "principal": principal,
            "principal_id": str(dados.get("alvo_principal_id") or getattr(principal, "id_batalha", "") or ""),
            "impactos": {str(k): self._tempo + float(v) for k, v in dict(impactos_rel or {}).items() if k},
            "fim": float(fim_abs or self._tempo),
        }
        self._ataques_ativos.append(contexto)
        return contexto

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

    def _modelo(self, animacao):
        modelo = MODELOS_VISUAIS.get(_normalizar_nome((animacao or {}).get("modelo")))
        if not modelo:
            self._avisos.append("animacao_sem_modelo_valido")
            return "EfeitoAlvo"
        return modelo

    def _resolver_alvos(self, dados, animacao=None):
        ctrl = self.controlador
        alvos = []
        vistos = set()
        for pid in list(dados.get("alvos_ids") or []):
            poke = ctrl.pokemons_por_id.get(str(pid))
            if poke is not None and str(pid) not in vistos:
                vistos.add(str(pid))
                alvos.append(poke)
        alvo_id = dados.get("alvo_id")
        if alvo_id and str(alvo_id) not in vistos:
            poke = ctrl.pokemons_por_id.get(str(alvo_id))
            if poke is not None:
                alvos.append(poke)
        if not alvos and not bool((animacao or {}).get("usar_alvos_selecionados")):
            alvo = self._resolver_alvo(dados)
            if alvo is not None:
                alvos.append(alvo)
        if bool((animacao or {}).get("usar_alvos_selecionados")) and getattr(ctrl, "arena", None) is not None:
            for alvo in alvos:
                area_alvo = str(getattr(alvo, "AreaId", "") or getattr(alvo, "area_id", "") or "").upper()
                if area_alvo:
                    vistos.add(f"area:{area_alvo}")
            for selecao in list(dados.get("alvos_selecionados") or []):
                if not isinstance(selecao, dict):
                    continue
                area_id = str(selecao.get("area_id") or "").upper()
                if not area_id:
                    continue
                chave = f"area:{area_id}"
                if chave in vistos:
                    continue
                centro = ctrl.arena.centro_area(area_id)
                if centro is not None:
                    vistos.add(chave)
                    alvos.append(centro)
        return alvos

    def _resolver_principal(self, dados, alvos):
        pid = str(dados.get("alvo_principal_id") or "")
        if pid:
            poke = self.controlador.pokemons_por_id.get(pid)
            if poke is not None:
                return poke
        return alvos[0] if alvos else self._resolver_alvo(dados)

    def _resolver_alvo(self, dados):
        ctrl = self.controlador
        if dados.get("alvo_id"):
            poke = ctrl.pokemons_por_id.get(str(dados.get("alvo_id")))
            if poke is not None:
                return poke
        area = dados.get("area_alvo_real") or dados.get("area_alvo")
        if area and getattr(ctrl, "arena", None) is not None:
            return ctrl.arena.centro_area(area)
        return None

    def _efeito_alvo(self, animacao, indice):
        chave = f"efeito_alvo{indice if indice > 1 else ''}"
        if chave in animacao:
            return animacao.get(chave)
        for i in range(indice - 1, 0, -1):
            anterior = f"efeito_alvo{i if i > 1 else ''}"
            if anterior in animacao:
                return animacao.get(anterior)
        return animacao.get("efeito_alvo")

    def _proximo_delay(self, inicio, duracao_anterior, animacao):
        intervalo = (animacao or {}).get("intervalo", "Ao Acabar")
        if _normalizar_nome(intervalo) == "aoacabar":
            return float(inicio) + float(duracao_anterior)
        valor = _num(intervalo, 0.0)
        return float(inicio) + max(0.0, float(valor or 0.0))

    def _duracao_projetil(self, usuario, alvo, velocidade):
        p0 = self.animator._posicao_mundo(usuario)
        p1 = self.animator._posicao_mundo(alvo)
        if p0 is None or p1 is None:
            return 0.35
        dist = max(0.001, math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        return max(0.18, min(1.20, dist / max(0.1, float(velocidade or 8.0))))

    def _duracao_deslocamento(self, usuario, alvo, velocidade, distancia_parada, retornar):
        p0 = self.animator._posicao_mundo(usuario)
        p1 = self.animator._posicao_mundo(alvo)
        if p0 is None or p1 is None:
            return 0.35, 0.70
        ponto = self.animator._ponto_parada_contato(usuario, alvo, p0, p1, distancia_parada)
        ida = max(0.16, min(0.72, math.hypot(ponto[0] - p0[0], ponto[1] - p0[1]) / max(0.1, float(velocidade or 8.0))))
        volta = max(0.16, min(0.72, math.hypot(ponto[0] - p0[0], ponto[1] - p0[1]) / max(0.1, float(velocidade or 8.0)))) if retornar else 0.16
        return ida, ida + volta

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

    def _grupos_laser(self, alvos, dados):
        if not alvos:
            linha = self._linha_alvo(dados)
            return [{"linha": linha, "alvos": []}] if linha else []
        grupos = {}
        sem_linha = []
        for alvo in alvos:
            area = str(getattr(alvo, "AreaId", "") or getattr(alvo, "area_id", "") or "").upper()
            try:
                idx = int(area[1:]) - 1
                chave = (area[:1], idx // 3)
            except (TypeError, ValueError, IndexError):
                sem_linha.append(alvo)
                continue
            grupos.setdefault(chave, []).append(alvo)
        saida = []
        for (prefixo, row), alvos_linha in grupos.items():
            linha = [self.controlador.arena.centro_area(f"{prefixo}{row * 3 + col + 1}") for col in range(3)] if getattr(self.controlador, "arena", None) is not None else []
            saida.append({"linha": [p for p in linha if p is not None], "alvos": alvos_linha})
        for alvo in sem_linha:
            saida.append({"linha": [], "alvos": [alvo]})
        return saida

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
        return [self.controlador.arena.centro_area(f"{prefixo}{row * 3 + col + 1}") for col in range(3)]

    def _validar_animacao(self, animacao, tipo_ataque=None):
        modelo = self._modelo(animacao)
        if modelo == "Laser" and bool(animacao.get("simultaneo", False)):
            self._avisos.append("Laser nao aceita simultaneo=true; valor ignorado.")
        if modelo == "Explosao":
            contato = _normalizar_nome(animacao.get("contato"))
            if contato == "laser":
                self._avisos.append("Explosao nao aceita contato Laser.")
            elif contato not in CONTATOS_EXPLOSAO:
                self._avisos.append("Explosao com contato invalido; Projetil sera usado.")
        for chave in ("cor", "cor_onda"):
            if chave in animacao and animacao.get(chave) is not None and _cor(animacao.get(chave)) is None:
                self._avisos.append(f"cor_invalida:{chave}")
        for chave in ("efeito_executor", "efeito_alvo", "efeito_alvo2", "efeito_alvo3", "efeito_alvo4", "efeito_impacto_secundario"):
            efeito = animacao.get(chave)
            if efeito and not self._efeito_existe(efeito):
                self._avisos.append(f"efeito_nao_encontrado:{efeito}")
        if modelo in {"Projetil", "Explosao"} and (modelo == "Projetil" or _normalizar_nome(animacao.get("contato")) == "projetil"):
            projetil = animacao.get("projetil") or "Generico"
            if _normalizar_nome(projetil) != "generico" and not self._projetil_existe(projetil):
                self._avisos.append(f"projetil_nao_encontrado:{projetil}")
        if "intervalo" in animacao and not (_normalizar_nome(animacao.get("intervalo")) == "aoacabar" or _num(animacao.get("intervalo")) is not None):
            self._avisos.append("intervalo_invalido")

    def _efeito_existe(self, nome):
        base = Path.cwd() / "Recursos" / "Visual" / "AtaquesGifs"
        return (base / str(nome)).is_dir() or (base / f"{nome}_frames").is_dir()

    def _projetil_existe(self, nome):
        chave = _normalizar_nome(nome)
        base = Path.cwd() / "Recursos" / "Visual" / "Projeteis"
        try:
            return any(c.is_file() and c.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"} and _normalizar_nome(c.stem) == chave for c in base.rglob("*"))
        except Exception:
            return False

    def _duracao_efeito(self, efeito, animacao=None):
        if not efeito:
            return 0.0
        duracao_cfg = _num((animacao or {}).get("duracao"))
        if duracao_cfg is not None:
            return max(0.0, duracao_cfg)
        try:
            frames = self.animator.arena_animator._carregar_frames_efeito(efeito)
        except Exception:
            frames = []
        fps = float(EFEITOS_ATAQUE_FPS.get(str(efeito), 20.0) or 20.0)
        return max(0.15, len(frames) / max(1.0, fps)) if frames else 0.15

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
