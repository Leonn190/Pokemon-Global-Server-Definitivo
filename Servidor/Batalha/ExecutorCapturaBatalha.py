from __future__ import annotations

import copy

from Servidor.Mundo.AutoridadeCaptura import resolver_captura_batalha


class ExecutorCapturaBatalha:
    def __init__(self, base):
        self.base = base
        self.rodador = base.rodador
        self.partida = base.partida

    def executar_captura(self, pokemon, acao):
        tipo_batalha = str(getattr(self.partida, "tipo_batalha", "") or "").strip().lower()
        if tipo_batalha != "confronto":
            self.rodador._falhar(acao, "captura_bloqueada_tipo_batalha" if tipo_batalha in {"servo", "boss"} else "captura_fora_de_confronto")
            return
        lado_id = int((acao or {}).get("lado_id", getattr(self.partida, "lado_jogador", 50)) or getattr(self.partida, "lado_jogador", 50))
        jogador_nome = str((acao or {}).get("jogador_nome") or "Jogador").strip() or "Jogador"
        usuario_id = str((acao or {}).get("usuario_id") or f"jogador_{lado_id}")
        alvo = self.partida.obter_pokemon(((acao or {}).get("alvo") or {}).get("pokemon_id") if isinstance((acao or {}).get("alvo"), dict) else None)
        if alvo is None:
            self.rodador._falhar(acao, "captura_alvo_inexistente")
            return
        if int(getattr(alvo, "lado_id", -1)) == int(lado_id):
            self.rodador._falhar(acao, "captura_alvo_aliado", alvo_id=alvo.id_batalha)
            return
        if not alvo.esta_vivo() or not bool(getattr(alvo, "ativo", False)) or bool(getattr(alvo, "reserva", False)):
            self.rodador._falhar(acao, "captura_alvo_invalido", alvo_id=alvo.id_batalha)
            return
        item_base_id = str((acao or {}).get("item_base_id") or ((acao or {}).get("bola") or {}).get("item_base_id") or ((acao or {}).get("bola") or {}).get("Code") or "").strip()
        item_nome = str((acao or {}).get("item_nome") or ((acao or {}).get("bola") or {}).get("Nome") or "Pokeball").strip()
        if not self.partida.consumir_pokebola_batalha(lado_id, item_base_id, item_nome):
            self.rodador._falhar(acao, "pokebola_indisponivel", alvo_id=alvo.id_batalha)
            return
        self.partida.registrar_evento_log(
            "captura_batalha_lancada",
            {
                "id_acao": acao.get("id_acao"),
                "usuario_id": usuario_id,
                "usuario_nome": jogador_nome,
                "capturador_tipo": "jogador",
                "lado_id": lado_id,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "bola_nome": item_nome,
                "item_base_id": item_base_id,
            },
        )
        resultado = resolver_captura_batalha(
            alvo,
            item_nome,
            contexto={
                "rng": self.partida.rng,
                "regras": getattr(self.partida, "regras_mundo", {}) or getattr(self.partida, "regras", {}),
                "em_batalha": True,
                "captura_critica_cliente": False,
                "captura_chance_checks_necessarios": 3,
            },
        )
        sucesso = bool(resultado.get("sucesso", False))
        snapshot = None
        if sucesso:
            snapshot = self.partida.snapshot_pokemon_capturado_batalha(alvo, efeitos_bola=resultado.get("efeitos_bola") if isinstance(resultado.get("efeitos_bola"), dict) else {})
            self.partida.adicionar_pokemon_capturado_batalha(lado_id, snapshot)
            self.partida.remover_pokemon_capturado_batalha(alvo)
        self.partida.registrar_evento_log(
            "captura_batalha_resultado",
            {
                "id_acao": acao.get("id_acao"),
                "usuario_id": usuario_id,
                "usuario_nome": jogador_nome,
                "capturador_tipo": "jogador",
                "lado_id": lado_id,
                "alvo_id": alvo.id_batalha,
                "alvo_nome": alvo.nome,
                "bola_nome": item_nome,
                "item_base_id": item_base_id,
                "checagens": list(resultado.get("checagens") or []),
                "resultado": "sucesso" if sucesso else "falha",
                "capturado": sucesso,
                "chance_check": resultado.get("chance_check"),
                "chance_real_3_checks": resultado.get("chance_real_3_checks"),
                "dificuldade_batalha": resultado.get("dificuldade_batalha"),
                "poder_total": resultado.get("poder_total"),
                "pokemon_capturado": snapshot if sucesso else None,
                "inventario_jogador": copy.deepcopy(self.partida.inventarios_lado.get(int(self.partida.lado_jogador), {})),
            },
        )
        self.partida.registrar_evento_log(
            "inventario_atualizado_batalha",
            {
                "lado_id": int(lado_id),
                "inventario": copy.deepcopy(self.partida.inventarios_lado.get(int(lado_id), {})),
            },
        )
