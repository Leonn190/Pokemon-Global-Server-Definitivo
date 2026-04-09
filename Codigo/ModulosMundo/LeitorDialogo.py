from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional


class LeitorDialogo:
    SAIDAS_INTERFACE = {
        "loja": "padrao",
        "loja_secreta": "secreta",
        "presente": "presente",
    }

    def __init__(
        self,
        dialogo: Optional[Dict[str, Any]] = None,
        *,
        ator_local=None,
        npc_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._dialogo = dialogo if isinstance(dialogo, dict) else {}
        self._ator_local = ator_local
        self._npc = dict(npc_payload or {})
        self._estado = self._npc.get("estado") if isinstance(self._npc.get("estado"), dict) else {}

        self.npc_nome = str(self._npc.get("nome") or self._estado.get("nome") or "NPC")
        self.npc_code = str(self._estado.get("npc_code") or self._npc.get("code") or self._npc.get("id") or self.npc_nome)
        self.npc_cargo = self.normalizar_cargo(self._estado.get("cargo") or self._npc.get("cargo") or self._estado.get("categoria") or self._npc.get("categoria"))
        self.npc_estadio = str(self._estado.get("estadio_tipo") or self._npc.get("estadio_tipo") or self._estado.get("estadio") or self._npc.get("estadio") or "").strip()

        self._setor = self._garantir_setor_dialogo()
        self._npc_chave_setor = self._slug(self.npc_code or self.npc_nome)
        self._visitas_anteriores = int(self._ler_caminho(self._setor, f"NPCs.{self._npc_chave_setor}.visitas", 0) or 0)
        self._registrar_visita_padrao()

        self.no_atual = ""
        self.fala_atual = "..."
        self._opcoes_visiveis: List[Dict[str, Any]] = []

        self.entrar_no(self._resolver_inicio())

    @classmethod
    def carregar_json(
        cls,
        caminho: Path,
        *,
        ator_local=None,
        npc_payload: Optional[Dict[str, Any]] = None,
    ) -> "LeitorDialogo":
        try:
            with Path(caminho).open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        return cls(data, ator_local=ator_local, npc_payload=npc_payload)

    @staticmethod
    def normalizar_cargo(valor: object) -> str:
        texto = LeitorDialogo._slug(valor)
        mapa = {
            "vendedor": "vendedor",
            "lojista": "vendedor",
            "dissociado": "dissociado",
            "combatente": "dissociado",
            "lider": "lider",
            "capitao": "capitao",
            "capitao_": "capitao",
            "desafiante": "desafiante",
        }
        return mapa.get(texto, "vendedor")

    @staticmethod
    def _slug(valor: object) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
        texto = "".join(ch if ch.isalnum() else "_" for ch in texto.strip().lower())
        while "__" in texto:
            texto = texto.replace("__", "_")
        return texto.strip("_")

    @staticmethod
    def _normalizar_tipo_estadio(valor: object) -> str:
        texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
        texto = texto.strip().lower()
        aliases = {
            "eletrico": "eletrico",
            "terra": "terrestre",
            "dragao": "dragao",
        }
        return aliases.get(texto, texto)

    def _garantir_setor_dialogo(self) -> Dict[str, Any]:
        ator = self._ator_local
        if ator is None:
            return {}
        setor = getattr(ator, "SetorDialogo", None)
        if not isinstance(setor, dict):
            setor = {}
            setattr(ator, "SetorDialogo", setor)
        return setor

    def _registrar_visita_padrao(self) -> None:
        caminho = f"NPCs.{self._npc_chave_setor}.visitas"
        atual = int(self._ler_valor(f"setor.{caminho}", 0) or 0)
        self._gravar_valor("setor", caminho, atual + 1)

    def _resolver_inicio(self) -> str:
        cfg = self._dialogo.get("inicio_condicional")
        if isinstance(cfg, dict):
            inicio = self._resolver_bloco_condicional(cfg)
            if isinstance(inicio, str) and inicio.strip():
                return inicio.strip()

        cfg_legado = self._dialogo.get("inicio_por_respeito")
        if isinstance(cfg_legado, dict):
            tipo_estadio = str(cfg_legado.get("tipo_estadio") or self.npc_estadio)
            mapa = cfg_legado.get("mapa") if isinstance(cfg_legado.get("mapa"), dict) else {}
            no = mapa.get(str(self.nivel_respeito_estadio(tipo_estadio)))
            if isinstance(no, str) and no.strip():
                return no.strip()

        inicio = str(self._dialogo.get("inicio") or "").strip()
        return inicio or "saudacao"

    def nivel_respeito_estadio(self, tipo_estadio: object) -> int:
        ator = self._ator_local
        perfil = getattr(ator, "Perfil", None) if ator is not None else None
        if perfil is None:
            return 0
        tipo = self._normalizar_tipo_estadio(tipo_estadio)
        mapa = {
            "normal": "RespeitoEstadioNormal",
            "fogo": "RespeitoEstadioFogo",
            "agua": "RespeitoEstadioAgua",
            "planta": "RespeitoEstadioPlanta",
            "eletrico": "RespeitoEstadioEletrico",
            "gelo": "RespeitoEstadioGelo",
            "lutador": "RespeitoEstadioLutador",
            "venenoso": "RespeitoEstadioVenenoso",
            "terrestre": "RespeitoEstadioTerrestre",
            "voador": "RespeitoEstadioVoador",
            "psiquico": "RespeitoEstadioPsiquico",
            "inseto": "RespeitoEstadioInseto",
            "pedra": "RespeitoEstadioPedra",
            "fantasma": "RespeitoEstadioFantasma",
            "dragao": "RespeitoEstadioDragao",
            "sombrio": "RespeitoEstadioSombrio",
            "metal": "RespeitoEstadioMetal",
            "fada": "RespeitoEstadioFada",
            "cosmico": "RespeitoEstadioCosmico",
            "sonoro": "RespeitoEstadioSonoro",
        }
        chave = mapa.get(tipo, "")
        valor = int(getattr(perfil, chave, 0) if chave else 0)
        return max(0, min(4, valor))

    def _nos(self) -> Dict[str, Dict[str, Any]]:
        nos = self._dialogo.get("nos")
        if isinstance(nos, dict):
            return {str(k): v for k, v in nos.items() if isinstance(v, dict)}
        return {}

    def _no(self, no_id: str) -> Dict[str, Any]:
        return self._nos().get(str(no_id), {})

    def _contexto_especial(self) -> Dict[str, Any]:
        visitas = int(self._ler_caminho(self._setor, f"NPCs.{self._npc_chave_setor}.visitas", 0) or 0)
        return {
            "respeito_atual": self.nivel_respeito_estadio(self.npc_estadio),
            "npc.visitas": visitas,
            "npc.visitas_anteriores": self._visitas_anteriores,
            "npc.nome": self.npc_nome,
            "npc.code": self.npc_code,
            "npc.cargo": self.npc_cargo,
            "npc.estadio": self.npc_estadio,
        }

    @staticmethod
    def _partes_caminho(caminho: object) -> List[str]:
        return [parte for parte in str(caminho or "").split(".") if parte]

    def _ler_caminho(self, origem: Any, caminho: object, padrao: Any = None) -> Any:
        atual = origem
        for parte in self._partes_caminho(caminho):
            if isinstance(atual, dict):
                if parte not in atual:
                    return padrao
                atual = atual.get(parte)
                continue
            if hasattr(atual, parte):
                atual = getattr(atual, parte)
                continue
            return padrao
        return atual

    def _gravar_caminho(self, origem: Any, caminho: object, valor: Any) -> None:
        partes = self._partes_caminho(caminho)
        if not partes:
            return
        atual = origem
        for parte in partes[:-1]:
            if isinstance(atual, dict):
                prox = atual.get(parte)
                if not isinstance(prox, dict):
                    prox = {}
                    atual[parte] = prox
                atual = prox
                continue
            prox = getattr(atual, parte, None)
            if prox is None:
                prox = {}
                setattr(atual, parte, prox)
            atual = prox
        ultimo = partes[-1]
        if isinstance(atual, dict):
            atual[ultimo] = valor
            return
        setattr(atual, ultimo, valor)

    def _ler_valor(self, alvo: object, padrao: Any = None) -> Any:
        if not isinstance(alvo, str):
            return alvo
        contexto_especial = self._contexto_especial()
        if alvo in contexto_especial:
            return contexto_especial[alvo]
        if alvo.startswith("setor."):
            return self._ler_caminho(self._setor, alvo[6:], padrao)
        if alvo.startswith("perfil."):
            perfil = getattr(self._ator_local, "Perfil", None)
            return self._ler_caminho(perfil, alvo[7:], padrao)
        if alvo.startswith("player."):
            valor = self._ler_caminho(self._ator_local, alvo[7:], None)
            if valor is not None:
                return valor
            perfil = getattr(self._ator_local, "Perfil", None)
            return self._ler_caminho(perfil, alvo[7:], padrao)
        if alvo.startswith("npc."):
            return contexto_especial.get(alvo, padrao)
        if alvo.startswith("respeito."):
            return self.nivel_respeito_estadio(alvo[9:])
        return padrao

    def _gravar_valor(self, escopo: str, caminho: object, valor: Any) -> None:
        if escopo == "setor":
            self._gravar_caminho(self._setor, caminho, valor)
            return
        if escopo == "perfil":
            perfil = getattr(self._ator_local, "Perfil", None)
            if perfil is not None:
                self._gravar_caminho(perfil, caminho, valor)
            return
        if escopo == "player" and self._ator_local is not None:
            partes = self._partes_caminho(caminho)
            if len(partes) == 1 and hasattr(self._ator_local, partes[0]):
                setattr(self._ator_local, partes[0], valor)
                return
            perfil = getattr(self._ator_local, "Perfil", None)
            if perfil is not None:
                self._gravar_caminho(perfil, caminho, valor)

    @staticmethod
    def _coagir(valor: Any) -> Any:
        if isinstance(valor, str):
            texto = valor.strip()
            baixo = texto.lower()
            if baixo == "true":
                return True
            if baixo == "false":
                return False
            try:
                if "." in texto:
                    return float(texto)
                return int(texto)
            except Exception:
                return valor
        return valor

    def _comparar(self, esquerda: Any, op: str, direita: Any = None) -> bool:
        esquerda = self._coagir(esquerda)
        direita = self._coagir(direita)
        if op in {"truthy", "existe", "exists"}:
            return bool(esquerda)
        if op in {"falsy", "nao_existe", "not_exists"}:
            return not bool(esquerda)
        try:
            if op == "==":
                return esquerda == direita
            if op == "!=":
                return esquerda != direita
            if op == ">":
                return esquerda > direita
            if op == ">=":
                return esquerda >= direita
            if op == "<":
                return esquerda < direita
            if op == "<=":
                return esquerda <= direita
            if op == "contains":
                if isinstance(esquerda, dict):
                    return direita in esquerda
                return direita in esquerda if esquerda is not None else False
            if op == "in":
                return esquerda in direita if direita is not None else False
            if op == "not_in":
                return esquerda not in direita if direita is not None else True
        except Exception:
            return False
        return False

    def _condicao_ok(self, condicao: Any) -> bool:
        if condicao in (None, "", [], {}):
            return True
        if isinstance(condicao, list):
            return all(self._condicao_ok(item) for item in condicao)
        if not isinstance(condicao, dict):
            return bool(condicao)
        if "todas" in condicao:
            itens = condicao.get("todas") if isinstance(condicao.get("todas"), list) else []
            return all(self._condicao_ok(item) for item in itens)
        if "qualquer" in condicao:
            itens = condicao.get("qualquer") if isinstance(condicao.get("qualquer"), list) else []
            return any(self._condicao_ok(item) for item in itens)
        if "nao" in condicao:
            return not self._condicao_ok(condicao.get("nao"))
        alvo = condicao.get("alvo") or condicao.get("campo") or condicao.get("ref")
        op = str(condicao.get("op") or ("==" if "valor" in condicao else "truthy")).strip().lower()
        valor = condicao.get("valor")
        return self._comparar(self._ler_valor(alvo), op, valor)

    def _resolver_bloco_condicional(self, bloco: Any) -> Any:
        if not isinstance(bloco, dict):
            return bloco
        casos = bloco.get("casos") if isinstance(bloco.get("casos"), list) else []
        for caso in casos:
            if not isinstance(caso, dict):
                continue
            if self._condicao_ok(caso.get("condicoes")):
                return caso.get("valor")
        return bloco.get("padrao")

    def _resolver_campo(self, origem: Dict[str, Any], campo: str, padrao: Any = None) -> Any:
        chave_condicional = f"{campo}_condicional"
        if chave_condicional in origem:
            valor = self._resolver_bloco_condicional(origem.get(chave_condicional))
            if valor is not None:
                return valor
        return origem.get(campo, padrao)

    def _aplicar_operacao(self, atual: Any, definicao: Any) -> Any:
        if not isinstance(definicao, dict) or "op" not in definicao:
            return definicao
        op = str(definicao.get("op") or "set").strip().lower()
        valor = definicao.get("valor")
        if op in {"set", "="}:
            return valor
        if op in {"add", "somar", "incrementar"}:
            base = self._coagir(atual)
            incremento = self._coagir(valor if valor is not None else 1)
            return (base or 0) + incremento
        if op in {"append_unique", "adicionar_unico"}:
            lista = list(atual or [])
            if valor not in lista:
                lista.append(valor)
            return lista
        if op == "toggle":
            return not bool(atual)
        return valor

    def _aplicar_efeitos(self, bloco: Any) -> None:
        if not isinstance(bloco, dict):
            return
        for escopo in ("setor", "player", "perfil"):
            mapa = bloco.get(escopo)
            if not isinstance(mapa, dict):
                continue
            for caminho, definicao in mapa.items():
                alvo_atual = self._ler_valor(f"{escopo}.{caminho}")
                novo_valor = self._aplicar_operacao(alvo_atual, definicao)
                self._gravar_valor(escopo, caminho, novo_valor)

    def _reconstruir_cache(self) -> None:
        no = self._no(self.no_atual)
        fala = self._resolver_campo(no, "fala", "...")
        self.fala_atual = str(fala if fala is not None else "...")
        opcoes = no.get("opcoes") if isinstance(no.get("opcoes"), list) else []
        resolvidas: List[Dict[str, Any]] = []
        for op in opcoes:
            if not isinstance(op, dict):
                continue
            if not self._condicao_ok(op.get("condicoes")):
                continue
            texto = self._resolver_campo(op, "texto", "")
            if texto in (None, ""):
                continue
            item = dict(op)
            item["texto"] = str(texto)
            destino = self._resolver_campo(op, "destino")
            if destino is not None:
                item["destino"] = destino
            acao = self._resolver_campo(op, "acao")
            if acao is not None:
                item["acao"] = acao
            batalha = self._resolver_campo(op, "batalha")
            if batalha is not None:
                item["batalha"] = batalha
            resolvidas.append(item)
        self._opcoes_visiveis = resolvidas

    def entrar_no(self, no_id: object) -> None:
        alvo = str(no_id or "saudacao").strip() or "saudacao"
        limite = 0
        while limite < 32:
            limite += 1
            self.no_atual = alvo if self._no(alvo) else "fallback"
            no = self._no(self.no_atual)
            if not no and self.no_atual != "fallback":
                self.no_atual = "fallback"
                no = self._no("fallback")
            self._aplicar_efeitos(no.get("ao_entrar"))
            desvio = self._resolver_campo(no, "desvio")
            if isinstance(desvio, str) and desvio.strip():
                alvo = desvio.strip()
                continue
            break
        self._reconstruir_cache()

    def modo_interface_atual(self) -> str:
        no = self._no(self.no_atual)
        saida = str(self._resolver_campo(no, "saida", "") or "").strip().lower()
        return self.SAIDAS_INTERFACE.get(saida, "")

    def opcoes_visiveis(self) -> List[Dict[str, Any]]:
        return list(self._opcoes_visiveis)

    def selecionar_opcao(self, indice: int) -> Dict[str, Any]:
        if indice < 0 or indice >= len(self._opcoes_visiveis):
            return {"tipo": "ignorar"}

        op = self._opcoes_visiveis[indice]
        self._aplicar_efeitos(op.get("ao_escolher"))

        acao = str(op.get("acao") or "").strip().lower()
        if acao == "fim":
            return {"tipo": "fim"}

        if acao == "batalha":
            try:
                numero = int(op.get("batalha") or 1)
            except Exception:
                numero = 1
            return {
                "tipo": "batalha",
                "contexto": {
                    "npc_id": int(self._npc.get("id", 0) or 0),
                    "npc_nome": self.npc_nome,
                    "npc_code": self.npc_code,
                    "npc_cargo": self.npc_cargo,
                    "npc_estadio": self.npc_estadio,
                    "batalha_numero": max(1, numero),
                },
            }

        destino = str(op.get("destino") or "").strip()
        if destino:
            self.entrar_no(destino)
            return {"tipo": "navegou"}

        return {"tipo": "fim"}
