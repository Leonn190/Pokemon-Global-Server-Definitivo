from __future__ import annotations

import math
import unicodedata
from pathlib import Path

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


class AnimadorAtaquesBatalha:
    def __init__(self, controlador_animacoes):
        self.controlador_animacoes = controlador_animacoes
        self.controlador = controlador_animacoes.controlador
        self.animator = controlador_animacoes.animator

    @property
    def _tempo(self):
        return self.controlador_animacoes._tempo

    @property
    def _avisos(self):
        return self.controlador_animacoes._avisos

    @property
    def _ataques_ativos(self):
        return self.controlador_animacoes._ataques_ativos

    def agendar_callback(self, delay, callback):
        return self.controlador_animacoes.agendar_callback(delay, callback)

    def animar_ataque_usado(self, dados):
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
