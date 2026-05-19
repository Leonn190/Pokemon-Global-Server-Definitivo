from __future__ import annotations

import copy
import math

from Codigo.ModulosBatalha.AnimadorAtaquesBatalha import AnimadorAtaquesBatalha
from Codigo.Visual.AuxiliaresVisuais import normalizar_tipo_ataque, obter_cor_tipo
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

EVENTOS_AREA_ARENA = {
    "area_recebeu_efeito",
    "area_removeu_efeito",
    "area_limpou_efeitos",
    "area_definiu_efeitos",
}

MODELOS_ATAQUE_SHADER = {
    "Projetil": 1,
    "Laser": 2,
    "Raio": 3,
    "Jato": 4,
    "Explosao": 5,
    "Avanco": 6,
    "Salto": 6,
    "EfeitoAlvo": 7,
    "EfeitoProprio": 7,
}

TIPOS_ATAQUE_SHADER = {
    "normal": 1,
    "fogo": 2,
    "agua": 3,
    "planta": 4,
    "eletrico": 5,
    "gelo": 6,
    "lutador": 7,
    "venenoso": 8,
    "terra": 9,
    "terrestre": 9,
    "voador": 10,
    "psiquico": 11,
    "inseto": 12,
    "pedra": 13,
    "fantasma": 14,
    "dragao": 15,
    "sombrio": 16,
    "metal": 17,
    "fada": 18,
    "cosmico": 19,
    "sonoro": 20,
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

        if tipo in EVENTOS_AREA_ARENA:
            self._aplicar_evento_area_arena(tipo, dados)
            return []
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

    def _aplicar_evento_area_arena(self, tipo, dados) -> None:
        arena = getattr(self.controlador, "arena", None)
        if arena is None:
            return
        area_id = dados.get("area_id") or dados.get("id") or dados.get("area")
        if tipo == "area_recebeu_efeito" and hasattr(arena, "adicionar_efeito_area"):
            arena.adicionar_efeito_area(area_id, dados.get("efeito") or dados.get("efeito_nome") or dados.get("efeito_code"))
        elif tipo == "area_removeu_efeito" and hasattr(arena, "remover_efeito_area"):
            arena.remover_efeito_area(area_id, dados.get("efeito") or dados.get("efeito_nome") or dados.get("efeito_code"))
        elif tipo == "area_limpou_efeitos":
            if area_id and hasattr(arena, "limpar_efeitos_area"):
                arena.limpar_efeitos_area(area_id)
            elif hasattr(arena, "limpar_efeitos_areas"):
                arena.limpar_efeitos_areas()
        elif tipo == "area_definiu_efeitos" and hasattr(arena, "definir_efeitos_area"):
            efeitos = dados.get("efeitos")
            if efeitos is None and dados.get("efeito") is not None:
                efeitos = [dados.get("efeito")]
            arena.definir_efeitos_area(area_id, efeitos)

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
                contexto["fim"] = max(float(contexto.get("fim", 0.0) or 0.0), float(impacto_abs) + 0.35)
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

    def coletar_ataques_shader_batalha(self, tamanho_tela):
        try:
            largura_tela = max(1.0, float(tamanho_tela[0]))
            altura_tela = max(1.0, float(tamanho_tela[1]))
        except Exception:
            largura_tela, altura_tela = 1.0, 1.0

        saida = []
        for ctx in list(self._ataques_ativos or []):
            if len(saida) >= 8:
                break
            if not isinstance(ctx, dict):
                continue
            try:
                inicio = float(ctx.get("inicio", ctx.get("fim", self._tempo)) or self._tempo)
                fim = float(ctx.get("fim", inicio) or inicio)
            except (TypeError, ValueError):
                continue

            modelo = str(ctx.get("modelo") or "")
            fim_visual = fim
            if modelo == "Explosao" and isinstance(ctx.get("impactos"), dict):
                for impacto in ctx.get("impactos", {}).values():
                    try:
                        fim_visual = max(fim_visual, float(impacto) + 0.35)
                    except (TypeError, ValueError):
                        continue
            if fim_visual <= inicio or self._tempo > fim_visual:
                continue

            modelo_codigo = MODELOS_ATAQUE_SHADER.get(modelo, 0)
            if modelo_codigo <= 0:
                continue

            usuario = self.controlador.pokemons_por_id.get(str(ctx.get("usuario_id") or ""))
            principal = ctx.get("principal")
            principal_id = str(ctx.get("principal_id") or "")
            if principal is None and principal_id:
                principal = self.controlador.pokemons_por_id.get(principal_id)
            if modelo == "EfeitoProprio" and usuario is not None:
                principal = usuario

            origem_uv = self._ataque_pos_uv(usuario, largura_tela, altura_tela)
            alvo_uv = self._ataque_pos_uv(principal, largura_tela, altura_tela)
            if origem_uv is None:
                origem_uv = alvo_uv
            if alvo_uv is None:
                alvo_uv = origem_uv
            if origem_uv is None or alvo_uv is None:
                continue
            if not self._uv_em_margem(origem_uv) and not self._uv_em_margem(alvo_uv):
                continue

            duracao = max(0.001, fim_visual - inicio)
            fase = max(0.0, min(1.0, (self._tempo - inicio) / duracao))
            fade_in = max(0.0, min(1.0, (self._tempo - inicio) / 0.10))
            fade_out = max(0.0, min(1.0, (fim_visual - self._tempo) / 0.16))
            power = max(0.0, min(1.0, fade_in, fade_out))
            impacto_power = self._impacto_power_shader(ctx)
            if impacto_power > power:
                power = min(1.0, max(power, impacto_power * 0.85))
            if power <= 0.001:
                continue

            animacao = ctx.get("animacao") if isinstance(ctx.get("animacao"), dict) else {}
            tipo_valor = ctx.get("tipo_ataque") or animacao.get("tipo_ataque") or animacao.get("tipo") or "normal"
            tipo = normalizar_tipo_ataque(tipo_valor)
            if tipo == "normal" and str(tipo_valor or "").strip().casefold() == "terrestre":
                tipo = "terra"
            cor = self._cor_ataque_shader(ctx, animacao, tipo)
            saida.append({
                "modelo": modelo,
                "modelo_codigo": modelo_codigo,
                "tipo": tipo,
                "tipo_codigo": TIPOS_ATAQUE_SHADER.get(tipo, 1),
                "origem_uv": origem_uv,
                "alvo_uv": alvo_uv,
                "fase": fase,
                "power": power,
                "raio": self._raio_ataque_shader(ctx, animacao, modelo, altura_tela),
                "largura": self._largura_ataque_shader(animacao, modelo),
                "seed": self._seed_ataque_shader(ctx),
                "impacto_power": impacto_power,
                "cor": cor,
            })
        return saida

    def esta_ocupado(self):
        return bool(self._agendados) or self.animator.esta_ocupado()

    def _ataque_pos_uv(self, alvo, largura_tela, altura_tela):
        pos_mundo = self.animator._posicao_mundo(alvo)
        pos_tela = self.animator._posicao_tela(pos_mundo)
        if not (isinstance(pos_tela, (list, tuple)) and len(pos_tela) >= 2):
            return None
        try:
            return (float(pos_tela[0]) / largura_tela, float(pos_tela[1]) / altura_tela)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def _uv_em_margem(uv):
        try:
            return -0.20 <= float(uv[0]) <= 1.20 and -0.20 <= float(uv[1]) <= 1.20
        except Exception:
            return False

    def _impacto_power_shader(self, contexto):
        impactos = contexto.get("impactos") if isinstance(contexto.get("impactos"), dict) else {}
        impacto_power = 0.0
        for impacto in impactos.values():
            try:
                delta = abs(self._tempo - float(impacto))
            except (TypeError, ValueError):
                continue
            if delta <= 0.20:
                impacto_power = max(impacto_power, 1.0 - (delta / 0.20))
        if contexto.get("modelo") == "Explosao":
            try:
                delta = abs(self._tempo - float(contexto.get("impacto_principal")))
                if delta <= 0.28:
                    impacto_power = max(impacto_power, 1.0 - (delta / 0.28))
            except (TypeError, ValueError):
                pass
        return max(0.0, min(1.0, impacto_power))

    def _raio_ataque_shader(self, contexto, animacao, modelo, altura_tela):
        padroes = {
            "Projetil": 0.050,
            "Laser": 0.040,
            "Raio": 0.045,
            "Jato": 0.060,
            "Explosao": 0.090,
            "Avanco": 0.070,
            "Salto": 0.075,
            "EfeitoAlvo": 0.070,
            "EfeitoProprio": 0.070,
        }
        raio = padroes.get(str(modelo or ""), 0.055)
        try:
            if modelo == "Explosao":
                camera = getattr(self.controlador, "camera", None)
                tile_px = max(1.0, float(getattr(camera, "TilePx", 40) or 40)) if camera is not None else 40.0
                raio = max(raio, float(contexto.get("raio_explosao") or animacao.get("raio_explosao") or 0.0) * tile_px / altura_tela)
            elif modelo == "Projetil" and animacao.get("tamanho") is not None:
                raio = max(raio, float(animacao.get("tamanho") or 0.0) / altura_tela * 1.15)
        except (TypeError, ValueError, ZeroDivisionError):
            pass
        return max(0.018, min(0.18, raio))

    @staticmethod
    def _largura_ataque_shader(animacao, modelo):
        try:
            largura = float(animacao.get("largura", 1.0) or 1.0)
        except (TypeError, ValueError):
            largura = 1.0
        if modelo == "Laser" and largura > 4.0:
            largura = largura / 12.0
        return max(0.35, min(3.0, largura))

    @staticmethod
    def _seed_ataque_shader(contexto):
        texto = f"{contexto.get('ataque_id') or ''}:{contexto.get('ataque_nome') or ''}:{contexto.get('usuario_id') or ''}:{contexto.get('inicio') or 0.0}"
        acumulado = 0
        for ch in texto:
            acumulado = (acumulado * 33 + ord(ch)) % 9973
        return float(acumulado % 1000) / 1000.0

    @staticmethod
    def _cor_ataque_shader(contexto, animacao, tipo):
        cor = contexto.get("cor")
        if not cor and contexto.get("modelo") == "Explosao":
            cor = animacao.get("cor_onda")
        if not cor:
            cor = animacao.get("cor")
        if isinstance(cor, (list, tuple)) and len(cor) >= 3:
            try:
                return (
                    max(0, min(255, int(cor[0]))),
                    max(0, min(255, int(cor[1]))),
                    max(0, min(255, int(cor[2]))),
                )
            except (TypeError, ValueError):
                pass
        return tuple(obter_cor_tipo(tipo))

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
