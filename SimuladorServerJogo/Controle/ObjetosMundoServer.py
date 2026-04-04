"""Objetos concretos server-side do mundo."""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from Codigo.Modulos.Colisor import Colisor
from SimuladorServerJogo.Logica.AutoridadeCaptura import resolver_captura, resolver_fruta

Vector2 = Tuple[float, float]


class AtorServer:
    NIVEL_MAXIMO = 50

    def __init__(self, id_objeto: int, usuario: str, skin: str, posicao: Vector2 = (0.0, 0.0), dimensao: str = "Mundo") -> None:
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_player"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = 0.55
        self.raio_interacao = 0.75
        self.campo = 0.45
        self.intensidade = 1.15
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        self.estado_extra = {"subtipo": "player", "usuario": str(usuario), "skin": str(skin), "nome": str(usuario), "angulo": 0.0, "perfil": {}, "inventario": {}, "slot_selecionado": 0, "dimensao": str(dimensao or "Mundo")}

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    @classmethod
    def _calcular_xp_alvo_por_nivel(cls, nivel: int) -> int:
        nivel_atual = max(0, int(nivel))
        if nivel_atual >= cls.NIVEL_MAXIMO:
            return 0
        faixa = nivel_atual // 10
        incremento = (faixa + 1) * 100
        base_faixa = 100 + (500 * faixa * faixa) + (600 * faixa)
        return int(base_faixa + (nivel_atual - (faixa * 10)) * incremento)

    def GanharXP(self, quantidade_xp) -> Dict[str, int]:
        perfil = self.estado_extra.get("perfil")
        if not isinstance(perfil, dict):
            perfil = {}
            self.estado_extra["perfil"] = perfil
        nivel = max(0, min(self.NIVEL_MAXIMO, int(perfil.get("nivel", 0) or 0)))
        xp = max(0, int(perfil.get("xp", 0) or 0))
        ganho = max(0, int(quantidade_xp or 0))
        if ganho > 0 and nivel < self.NIVEL_MAXIMO:
            xp += ganho
            while nivel < self.NIVEL_MAXIMO:
                alvo = self._calcular_xp_alvo_por_nivel(nivel)
                if xp < alvo:
                    break
                xp -= alvo
                nivel += 1
        if nivel >= self.NIVEL_MAXIMO:
            nivel = self.NIVEL_MAXIMO
            xp = 0
            xp_alvo = 0
            ganho_real = 0
        else:
            xp_alvo = self._calcular_xp_alvo_por_nivel(nivel)
            ganho_real = ganho
        perfil["nivel"] = int(nivel)
        perfil["xp"] = int(xp)
        perfil["xp_alvo"] = int(xp_alvo)
        return {"xp_ganho": int(ganho_real), "nivel_atual": int(nivel), "xp_atual": int(xp), "xp_alvo": int(xp_alvo)}

    def serializar(self) -> Dict[str, object]:
        estado = dict(self.estado_extra)
        return {
            "id": self.Id,
            "tipo": self.tipo_classe,
            "nome": str(estado.get("nome") or estado.get("usuario") or ""),
            "skin": str(estado.get("skin") or "S1"),
            "perfil": dict(estado.get("perfil", {})) if isinstance(estado.get("perfil"), dict) else {},
            "inventario": dict(estado.get("inventario", {})) if isinstance(estado.get("inventario"), dict) else {},
            "slot_selecionado": int(estado.get("slot_selecionado", 0) or 0),
            "posicao": [self.posicao[0], self.posicao[1]],
            "raio_colisao": self.raio_colisao,
            "raio_interacao": self.raio_interacao,
            "campo": self.campo,
            "intensidade": self.intensidade,
            "estado": estado,
            "dimensao": str(estado.get("dimensao") or "Mundo"),
        }


class BauServer:
    def __init__(self, id_objeto: int, tipo_bau: str, itens: list, posicao: Vector2 = (0.0, 0.0), aberto: bool = False, raio_colisao: float = 0.42, raio_interacao: float = 0.85, quantidade_itens: int = 1, tamanho_tiles: float = 1.10, **kwargs) -> None:
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_bau"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = float(raio_colisao)
        self.raio_interacao = float(raio_interacao)
        self.campo = 0.35
        self.intensidade = 1.4
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        self.estado_extra = {"subtipo": "bau", "tipo_bau": str(tipo_bau), "itens": list(itens), "aberto": bool(aberto), "aberto_em": (time.monotonic() if aberto else 0.0), "quantidade_itens": max(1, min(4, int(quantidade_itens or max(1, len(list(itens)))))), "tamanho_tiles": float(tamanho_tiles or 1.10)}

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    def abrir(self, player=None, dono_id: int = 0) -> Dict[str, object] | None:
        if bool(self.estado_extra.get("aberto", False)):
            return None
        self.estado_extra["aberto"] = True
        self.estado_extra["aberto_em"] = time.monotonic()
        return {"dono_id": int(dono_id or 0), "itens": list(self.estado_extra.get("itens", []))}

    def serializar(self) -> Dict[str, object]:
        return {"id": self.Id, "tipo": self.tipo_classe, "posicao": [self.posicao[0], self.posicao[1]], "raio_colisao": self.raio_colisao, "raio_interacao": self.raio_interacao, "campo": self.campo, "intensidade": self.intensidade, "estado": dict(self.estado_extra)}


class EstruturaNaturalServer:
    def __init__(self, id_objeto: int, tipo: str, nome: str, sprite: str, posicao: Vector2 = (0.0, 0.0), raio_colisao: float = 20.0, raio_interacao: float = 26.0, campo: float = 0.0, intensidade: float = 0.0, codigo_natural: int = 0, quantidade: int = 0, material: str = "", estilo: str = "", dureza: int = 1):
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "estrutura_natural"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = float(raio_colisao)
        self.raio_interacao = float(raio_interacao)
        self.campo = float(campo)
        self.intensidade = float(intensidade)
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        self.estado_extra = {
            "subtipo": str(tipo),
            "quantidade": max(0, int(quantidade or 0)),
            "material": str(material or ""),
            "estilo": str(estilo or ""),
            "dureza": max(1, int(dureza or 1)),
        }
        self.nome = str(nome)
        self.sprite = str(sprite)
        self.codigo_natural = int(codigo_natural)

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    @property
    def quantidade_restante(self) -> int:
        return max(0, int(self.estado_extra.get("quantidade", 0) or 0))

    def tentar_coleta(self, fator_ferramenta: int, estilo_ferramenta: str = "") -> int:
        restante = self.quantidade_restante
        if restante <= 0:
            return 0

        dureza = max(1, int(self.estado_extra.get("dureza", 1) or 1))
        estilo_estrutura = str(self.estado_extra.get("estilo", "") or "").strip().lower()
        estilo_ferramenta = str(estilo_ferramenta or "").strip().lower()
        fator = max(1, int(fator_ferramenta or 1))

        if not estilo_ferramenta or estilo_ferramenta != estilo_estrutura:
            fator = 1

        if fator < dureza:
            return 0
        coletar = 1 + max(0, fator - dureza)
        coletar = min(restante, coletar)
        self.estado_extra["quantidade"] = max(0, restante - coletar)
        return coletar

    def serializar(self) -> Dict[str, object]:
        return {"id": self.Id, "tipo": self.tipo_classe, "posicao": [self.posicao[0], self.posicao[1]], "raio_colisao": self.raio_colisao, "raio_interacao": self.raio_interacao, "campo": self.campo, "intensidade": self.intensidade, "estado": dict(self.estado_extra), "nome": self.nome, "sprite": self.sprite, "codigo_natural": self.codigo_natural}


class EstadioServer:
    def __init__(self, id_objeto: int, tipo_estadio: str, dimensao: str, posicao: Vector2 = (0.0, 0.0), raio_elipse_x: float = 24.0, raio_elipse_y: float = 24.0, raio_interacao: float = 2.5):
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_estadio"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = max(0.4, float((raio_elipse_x + raio_elipse_y) * 0.5))
        self.raio_interacao = max(self.raio_colisao, float(raio_interacao))
        self.campo = 0.35
        self.intensidade = 1.15
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        self.estado_extra = {
            "subtipo": "estadio",
            "tipo_estadio": str(tipo_estadio or "normal"),
            "dimensao": "Mundo",
            "dimensao_destino": str(dimensao or "EstadioNormal"),
            "raio_elipse_x": max(8.0, float(raio_elipse_x)),
            "raio_elipse_y": max(8.0, float(raio_elipse_y)),
            "raio_elipse_interno_x": max(4.0, float(raio_elipse_x) * 0.72),
            "raio_elipse_interno_y": max(4.0, float(raio_elipse_y) * 0.72),
            "entrada_offset": [0.0, max(2.0, float(raio_elipse_y) + 1.0)],
            "entrada_pos": [float(self.posicao[0]), float(self.posicao[1] + max(2.0, float(raio_elipse_y) + 1.0))],
            "largura_interna": 60.0,
            "altura_interna": 40.0,
            "saida_interna_pos": [30.0, 37.0],
            "spawn_interno_pos": [30.0, 34.0],
            "arena_centro": [30.0, 20.0],
        }

    def serializar(self) -> Dict[str, object]:
        return {"id": self.Id, "tipo": self.tipo_classe, "posicao": [self.posicao[0], self.posicao[1]], "raio_colisao": self.raio_colisao, "raio_interacao": self.raio_interacao, "campo": self.campo, "intensidade": self.intensidade, "estado": dict(self.estado_extra)}


class PokemonServer:
    def __init__(self, id_objeto: int, especie: str, posicao: Vector2 = (0.0, 0.0), **kwargs) -> None:
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_pokemon"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = float(kwargs.get("raio_colisao", 0.45))
        self.raio_interacao = float(kwargs.get("raio_interacao", 1.2))
        self.campo = float(kwargs.get("campo", 0.0))
        self.intensidade = float(kwargs.get("intensidade", 0.0))
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        self.estado_extra = {"subtipo": "pokemon", "especie": str(especie), "nome": str(especie), "ativo": True, "movendo": False, "movendo_ate": 0.0, "dificuldade_captura": 50.0, "tamanho_barra_captura": 0.32, "velocidade_barra_captura": 90.0, "tentativas_falhas_captura": 0, "frutas_aplicadas": [], "estado_frutificacao": {"multiplicador_doces": 1.0, "bonus_captura_frutas": 0.0, "bonus_captura_bioma": {}, "limite_frutas": 2}, "captura_fase": "nenhuma", "captura": {"captura_pendente": False, "checks_total": 3, "checagens": [], "resultado": "pendente", "bola_nome": "", "dono_id": 0, "token_arremesso": "", "liberar_movimento_tick": 0, "pokemon_colisao_ativa": True, "pokemon_interacao_ativa": True}, "cooldown_movimento_ate_tick": 0}

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    def mover(self, deslocamento: Vector2, colisor_cb=None, velocidade_tiles_s: float = 1.0) -> bool:
        if not bool(self.estado_extra.get("ativo", True)) or time.monotonic() < float(self.estado_extra.get("movendo_ate", 0.0)):
            return False
        dx = float(deslocamento[0]) if isinstance(deslocamento, (list, tuple)) and len(deslocamento) > 0 else 0.0
        dy = float(deslocamento[1]) if isinstance(deslocamento, (list, tuple)) and len(deslocamento) > 1 else 0.0
        destino = (self.posicao[0] + dx, self.posicao[1] + dy)
        if callable(colisor_cb) and not bool(colisor_cb(destino, self.raio_colisao)):
            return False
        self.definir_posicao(*destino)
        distancia = max(0.0, (dx * dx + dy * dy) ** 0.5)
        duracao = distancia / max(0.01, float(velocidade_tiles_s))
        self.estado_extra["movendo"] = bool(duracao > 0)
        self.estado_extra["movendo_ate"] = time.monotonic() + duracao
        self.estado_extra["ultimo_movimento"] = [dx, dy]
        return True

    def frutificar(self, nome_item: str, contexto: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        return resolver_fruta(self, nome_item, contexto=contexto or {})

    def capturar(self, nome_item: str, contexto: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        return resolver_captura(self, nome_item, contexto=contexto or {})

    def sumir(self) -> None:
        self.estado_extra["ativo"] = False
        self.estado_extra["despawnado"] = True

    def serializar(self) -> Dict[str, object]:
        estado = dict(self.estado_extra)
        captura = estado.get("captura") if isinstance(estado.get("captura"), dict) else {}
        estado["captura_fase"] = str(captura.get("fase", estado.get("captura_fase", "nenhuma")))
        estado["captura_pendente"] = bool(captura.get("captura_pendente", False))
        estado["captura_resultado"] = str(captura.get("resultado", "pendente") or "pendente")
        estado["movendo"] = bool(time.monotonic() < float(estado.get("movendo_ate", 0.0)))
        raio_c = 0.0 if bool(captura.get("captura_pendente", False)) else self.raio_colisao
        raio_i = 0.0 if bool(captura.get("captura_pendente", False)) else self.raio_interacao
        stats = estado.get("stats") if isinstance(estado.get("stats"), dict) else {}
        return {"id": self.Id, "tipo": self.tipo_classe, "posicao": [self.posicao[0], self.posicao[1]], "raio_colisao": raio_c, "raio_interacao": raio_i, "campo": self.campo, "intensidade": self.intensidade, "estado": estado, "nome": str(estado.get("nome") or estado.get("especie") or "Pokemon"), "vida": float(stats.get("Vida", 0.0)), "atk": float(stats.get("Atk", 0.0)), "def": float(stats.get("Def", 0.0))}


class ProjetilServer:
    def __init__(self, id_objeto: int, posicao: Vector2, dono_id: int, tipo_projetil: str, subtipo: str, item_base_id: str, token_arremesso: str, direcao: Vector2, velocidade: float, alcance: float, raio_colisao: float = 0.18) -> None:
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_projetil"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = float(raio_colisao)
        self.raio_interacao = float(raio_colisao)
        self.campo = 0.0
        self.intensidade = 0.0
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        dx, dy = float(direcao[0]), float(direcao[1])
        n = (dx * dx + dy * dy) ** 0.5 or 1.0
        self.estado_extra = {"subtipo": "projetil", "tipo_projetil": str(tipo_projetil or "item"), "nome_item": str(subtipo or "item"), "item_base_id": str(item_base_id or ""), "dono_id": int(dono_id or 0), "token_arremesso": str(token_arremesso or ""), "posicao_inicial": [self.posicao[0], self.posicao[1]], "direcao": [dx / n, dy / n], "velocidade": max(0.1, float(velocidade or 10.0)), "alcance": max(0.1, float(alcance or 6.0)), "distancia": 0.0, "tempo_vida": 0.0, "rotacao": 0.0, "terminado": False}

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    def atualizar(self, dt: float) -> None:
        if bool(self.estado_extra.get("terminado", False)):
            return
        dt = max(0.0, float(dt))
        dx, dy = self.estado_extra.get("direcao", [1.0, 0.0])
        passo = float(self.estado_extra.get("velocidade", 10.0) or 10.0) * dt
        self.definir_posicao(self.posicao[0] + float(dx) * passo, self.posicao[1] + float(dy) * passo)
        self.estado_extra["distancia"] = float(self.estado_extra.get("distancia", 0.0) or 0.0) + passo
        self.estado_extra["tempo_vida"] = float(self.estado_extra.get("tempo_vida", 0.0) or 0.0) + dt
        self.estado_extra["rotacao"] = (float(self.estado_extra.get("rotacao", 0.0) or 0.0) + 560.0 * dt) % 360.0
        if float(self.estado_extra.get("distancia", 0.0) or 0.0) >= float(self.estado_extra.get("alcance", 6.0) or 6.0):
            self.estado_extra["terminado"] = True

    def terminar(self, motivo: str = "") -> None:
        self.estado_extra["terminado"] = True
        if motivo:
            self.estado_extra["motivo_termino"] = str(motivo)

    def serializar(self) -> Dict[str, object]:
        return {"id": self.Id, "tipo": self.tipo_classe, "posicao": [self.posicao[0], self.posicao[1]], "raio_colisao": self.raio_colisao, "raio_interacao": self.raio_interacao, "campo": self.campo, "intensidade": self.intensidade, "estado": dict(self.estado_extra), "tipo_projetil": str(self.estado_extra.get("tipo_projetil", "item")), "subtipo": str(self.estado_extra.get("nome_item", "item")), "item_base_id": str(self.estado_extra.get("item_base_id", "")), "dono_id": int(self.estado_extra.get("dono_id", 0) or 0), "token_arremesso": str(self.estado_extra.get("token_arremesso", ""))}


class ItemMundoServer:
    def __init__(self, id_objeto: int, posicao: Vector2, dono_id: int, item_nome: str, item_base_id: str, quantidade: int, pos_inicial: Vector2, pos_final: Vector2, velocidade: float, tick_spawn: int, token_drop: str = "", item_dados: Optional[Dict[str, object]] = None) -> None:
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_item_mundo"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        self.raio_colisao = 0.24
        self.raio_interacao = 0.24
        self.campo = 0.0
        self.intensidade = 0.0
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        item_meta = dict(item_dados or {}) if isinstance(item_dados, dict) else {}
        item_meta_nome = str(item_meta.get("Nome") or item_nome or "Item")
        item_meta_code = str(item_meta.get("Code") or item_base_id or "")
        item_meta_qtd = max(1, int(item_meta.get("quantidade", quantidade) or quantidade or 1))
        item_meta = {**item_meta, "Nome": item_meta_nome, "Code": item_meta_code, "quantidade": item_meta_qtd}
        self.estado_extra = {
            "subtipo": "item_mundo",
            "dono_id": int(dono_id or 0),
            "item_nome": item_meta_nome,
            "item_base_id": item_meta_code,
            "item_dados": item_meta,
            "quantidade": item_meta_qtd,
            "pos_inicial": [float(pos_inicial[0]), float(pos_inicial[1])],
            "pos_final": [float(pos_final[0]), float(pos_final[1])],
            "velocidade": max(0.1, float(velocidade or 5.5)),
            "voando": bool((float(pos_final[0]) - float(pos_inicial[0])) ** 2 + (float(pos_final[1]) - float(pos_inicial[1])) ** 2 > 0.0009),
            "tick_spawn": int(tick_spawn),
            "token_drop": str(token_drop or ""),
            "voando_ate_tick": int(tick_spawn + max(1, round((((float(pos_final[0]) - float(pos_inicial[0])) ** 2 + (float(pos_final[1]) - float(pos_inicial[1])) ** 2) ** 0.5) / max(0.1, float(velocidade or 3.0)) * 30.0))),
        }

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    def serializar(self) -> Dict[str, object]:
        return {
            "id": self.Id,
            "tipo": self.tipo_classe,
            "posicao": [self.posicao[0], self.posicao[1]],
            "raio_colisao": self.raio_colisao,
            "raio_interacao": self.raio_interacao,
            "campo": self.campo,
            "intensidade": self.intensidade,
            "item_nome": str(self.estado_extra.get("item_nome", "Item")),
            "item_base_id": str(self.estado_extra.get("item_base_id", "")),
            "quantidade": int(self.estado_extra.get("quantidade", 1) or 1),
            "dono_id": int(self.estado_extra.get("dono_id", 0) or 0),
            "token_drop": str(self.estado_extra.get("token_drop", "")),
            "item_dados": dict(self.estado_extra.get("item_dados", {})) if isinstance(self.estado_extra.get("item_dados"), dict) else {},
            "estado": dict(self.estado_extra),
        }


class XpMundoServer:
    XP_POR_TAMANHO = {"pequeno": 15, "medio": 40, "grande": 100}
    RAIO_POR_TAMANHO = {"pequeno": 0.09, "medio": 0.12, "grande": 0.16}

    def __init__(self, id_objeto: int, posicao: Vector2, tamanho: str, pos_inicial: Vector2, pos_final: Vector2, velocidade: float, tick_spawn: int, xp_valor: int | None = None) -> None:
        self.id_objeto = int(id_objeto)
        self.Id = self.id_objeto
        self.tipo_classe = "entidade_xp_mundo"
        self.posicao = (float(posicao[0]), float(posicao[1]))
        tamanho_norm = str(tamanho or "pequeno").strip().lower()
        if tamanho_norm not in self.XP_POR_TAMANHO:
            tamanho_norm = "pequeno"
        self.raio_colisao = float(self.RAIO_POR_TAMANHO.get(tamanho_norm, 0.09))
        self.raio_interacao = self.raio_colisao
        self.campo = 0.0
        self.intensidade = 0.0
        self.Colisor = Colisor(x=self.posicao[0], y=self.posicao[1], raio_colisao=self.raio_colisao, raio_interacao=self.raio_interacao)
        xp_final = int(xp_valor if xp_valor is not None else self.XP_POR_TAMANHO.get(tamanho_norm, 15))
        self.estado_extra = {
            "subtipo": "xp_mundo",
            "tamanho": str(tamanho_norm),
            "xp_valor": max(1, int(xp_final)),
            "pos_inicial": [float(pos_inicial[0]), float(pos_inicial[1])],
            "pos_final": [float(pos_final[0]), float(pos_final[1])],
            "velocidade": max(0.1, float(velocidade or 3.6)),
            "voando": bool((float(pos_final[0]) - float(pos_inicial[0])) ** 2 + (float(pos_final[1]) - float(pos_inicial[1])) ** 2 > 0.0009),
            "tick_spawn": int(tick_spawn),
            "voando_ate_tick": int(tick_spawn + max(1, round((((float(pos_final[0]) - float(pos_inicial[0])) ** 2 + (float(pos_final[1]) - float(pos_inicial[1])) ** 2) ** 0.5) / max(0.1, float(velocidade or 3.6)) * 30.0))),
        }

    def definir_posicao(self, x: float, y: float) -> None:
        self.posicao = (float(x), float(y))
        self.Colisor.mover_para(*self.posicao)

    def serializar(self) -> Dict[str, object]:
        return {
            "id": self.Id,
            "tipo": self.tipo_classe,
            "posicao": [self.posicao[0], self.posicao[1]],
            "raio_colisao": self.raio_colisao,
            "raio_interacao": self.raio_interacao,
            "campo": self.campo,
            "intensidade": self.intensidade,
            "tamanho": str(self.estado_extra.get("tamanho", "pequeno")),
            "xp_valor": int(self.estado_extra.get("xp_valor", 15) or 15),
            "estado": dict(self.estado_extra),
        }


def criar_objeto_mundo_server(dados: Dict[str, object]):
    dados = dict(dados or {})
    tipo = str(dados.get("tipo", "")).strip().lower()
    estado = dados.get("estado") if isinstance(dados.get("estado"), dict) else {}
    pos = dados.get("posicao") if isinstance(dados.get("posicao"), (list, tuple)) and len(dados.get("posicao")) == 2 else [0.0, 0.0]
    oid = int(dados.get("id", 0) or 0)
    if tipo == "entidade_player":
        return AtorServer(id_objeto=oid, usuario=str(estado.get("usuario") or dados.get("usuario") or ""), skin=str(estado.get("skin") or dados.get("skin") or "S1"), posicao=(float(pos[0]), float(pos[1])), dimensao=str(dados.get("dimensao") or estado.get("dimensao") or "Mundo"))
    if tipo in {"entidade_projetil", "projetil"}:
        direcao = estado.get("direcao") if isinstance(estado.get("direcao"), (list, tuple)) else dados.get("direcao", [1.0, 0.0])
        return ProjetilServer(id_objeto=oid, posicao=(float(pos[0]), float(pos[1])), dono_id=int(dados.get("dono_id", estado.get("dono_id", 0)) or 0), tipo_projetil=str(dados.get("tipo_projetil") or estado.get("tipo_projetil") or "item"), subtipo=str(dados.get("subtipo") or estado.get("nome_item") or "item"), item_base_id=str(dados.get("item_base_id") or estado.get("item_base_id") or ""), token_arremesso=str(dados.get("token_arremesso") or estado.get("token_arremesso") or ""), direcao=(float(direcao[0]), float(direcao[1])), velocidade=float(dados.get("velocidade") or estado.get("velocidade") or 10.0), alcance=float(dados.get("alcance") or estado.get("alcance") or 6.0), raio_colisao=float(dados.get("raio_colisao", 0.18) or 0.18))
    if tipo in {"entidade_pokemon", "pokemon"}:
        raio_colisao = float(dados.get("raio_colisao", 0.0) or 0.0)
        if raio_colisao <= 0.0:
            tamanho_tiles = float(estado.get("tamanho_tiles", dados.get("tamanho_tiles", 0.0)) or 0.0)
            if tamanho_tiles <= 0.0:
                try:
                    tamanho = int(float(estado.get("tamanho", dados.get("tamanho", 3)) or 3))
                except (TypeError, ValueError):
                    tamanho = 3
                tamanho_tiles = 1.0 + (max(1, tamanho) - 1) * 0.2
            raio_colisao = max(0.2, tamanho_tiles * 0.5)
        raio_interacao = float(dados.get("raio_interacao", 0.0) or 0.0)
        if raio_interacao <= 0.0:
            raio_interacao = max(raio_colisao, 1.2)
        return PokemonServer(
            id_objeto=oid,
            especie=str(estado.get("especie") or dados.get("nome") or "Pokemon"),
            posicao=(float(pos[0]), float(pos[1])),
            raio_colisao=raio_colisao,
            raio_interacao=raio_interacao,
        )

    if tipo in {"entidade_estadio", "estadio"}:
        return EstadioServer(
            id_objeto=oid,
            tipo_estadio=str(estado.get("tipo_estadio") or dados.get("tipo_estadio") or "normal"),
            dimensao=str(estado.get("dimensao_destino") or dados.get("dimensao") or "EstadioNormal"),
            posicao=(float(pos[0]), float(pos[1])),
            raio_elipse_x=float(estado.get("raio_elipse_x", dados.get("raio_elipse_x", 24.0)) or 24.0),
            raio_elipse_y=float(estado.get("raio_elipse_y", dados.get("raio_elipse_y", 24.0)) or 24.0),
            raio_interacao=float(dados.get("raio_interacao", 2.5) or 2.5),
        )
    if tipo in {"entidade_item_mundo", "item_mundo"}:
        p0 = estado.get("pos_inicial") if isinstance(estado.get("pos_inicial"), (list, tuple)) else pos
        p1 = estado.get("pos_final") if isinstance(estado.get("pos_final"), (list, tuple)) else pos
        return ItemMundoServer(id_objeto=oid, posicao=(float(pos[0]), float(pos[1])), dono_id=int(dados.get("dono_id", estado.get("dono_id", 0)) or 0), item_nome=str(dados.get("item_nome") or estado.get("item_nome") or "Item"), item_base_id=str(dados.get("item_base_id") or estado.get("item_base_id") or ""), quantidade=int(dados.get("quantidade") or estado.get("quantidade") or 1), pos_inicial=(float(p0[0]), float(p0[1])), pos_final=(float(p1[0]), float(p1[1])), velocidade=float(dados.get("velocidade") or estado.get("velocidade") or 5.5), tick_spawn=int(estado.get("tick_spawn", 0) or 0), token_drop=str(dados.get("token_drop") or estado.get("token_drop") or ""), item_dados=(dados.get("item_dados") if isinstance(dados.get("item_dados"), dict) else estado.get("item_dados") if isinstance(estado.get("item_dados"), dict) else None))
    if tipo in {"entidade_xp_mundo", "xp_mundo"}:
        p0 = estado.get("pos_inicial") if isinstance(estado.get("pos_inicial"), (list, tuple)) else pos
        p1 = estado.get("pos_final") if isinstance(estado.get("pos_final"), (list, tuple)) else pos
        return XpMundoServer(id_objeto=oid, posicao=(float(pos[0]), float(pos[1])), tamanho=str(dados.get("tamanho") or estado.get("tamanho") or "pequeno"), pos_inicial=(float(p0[0]), float(p0[1])), pos_final=(float(p1[0]), float(p1[1])), velocidade=float(dados.get("velocidade") or estado.get("velocidade") or 3.6), tick_spawn=int(estado.get("tick_spawn", 0) or 0), xp_valor=int(dados.get("xp_valor") or estado.get("xp_valor") or 0))
    if str(estado.get("subtipo", "")).strip().lower() == "bau" or tipo == "entidade_bau":
        return BauServer(id_objeto=oid, tipo_bau=str(estado.get("tipo_bau", "Comum")), itens=list(estado.get("itens", [])), posicao=(float(pos[0]), float(pos[1])), aberto=bool(estado.get("aberto", False)), raio_colisao=float(dados.get("raio_colisao", 0.42)), raio_interacao=float(dados.get("raio_interacao", 0.85) or 0.85), quantidade_itens=int(estado.get("quantidade_itens", max(1, len(list(estado.get("itens", [])))))), tamanho_tiles=float(estado.get("tamanho_tiles", 1.10) or 1.10))
    if tipo.startswith("estrutura") or tipo == "estrutura_natural":
        return EstruturaNaturalServer(id_objeto=oid, tipo=str(estado.get("subtipo") or "natural"), nome=str(dados.get("nome") or "Estrutura"), sprite=str(dados.get("sprite") or ""), posicao=(float(pos[0]), float(pos[1])), raio_colisao=float(dados.get("raio_colisao", 1.0)), raio_interacao=float(dados.get("raio_interacao", 1.0)), campo=float(dados.get("campo", 0.0)), intensidade=float(dados.get("intensidade", 0.0)), codigo_natural=int(dados.get("codigo_natural", 0) or 0), quantidade=int(estado.get("quantidade", 0) or 0), material=str(estado.get("material", "") or ""), estilo=str(estado.get("estilo", "") or ""), dureza=int(estado.get("dureza", 1) or 1))
    return None
