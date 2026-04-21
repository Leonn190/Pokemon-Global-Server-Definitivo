from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

RAIZ_REPO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPO))

import pygame

from Codigo.ModulosBatalha.ControladorBatalha import ControladorBatalha
from Codigo.ModulosBatalha.ElementosHudBatalha import ElementosHudBatalha
from Codigo.ModulosGerais.Camera import CameraBatalha
from SimuladorServerJogo.Batalha.Combate.CatalogoAtaques import carregar_catalogo_ataques
from SimuladorServerJogo.Batalha.Combate.ValidadorAtaques import validar_arquivo
from Codigo.ModulosBatalha.InicializadorBatalha import InicializadorBatalha
from SimuladorServerJogo.Batalha.LeitorJogadas import LeitorJogadas
from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha as SistemaBatalhaServidor
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado

@dataclass
class ContextoDebug6v6:
    contexto_cliente: Dict[str, object]
    contexto_servidor: Dict[str, object]


def _rng(seed: int | None = None) -> random.Random:
    return random.Random(seed if seed is not None else random.randrange(1_000_000_000))


def _carregar_especies() -> List[str]:
    caminho = Path("Dados") / "Pokemon Global Server - Pokemons.csv"
    if not caminho.exists():
        return ["Pikachu"]
    especies: List[str] = []
    with caminho.open("r", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        for row in leitor:
            nome = str(row.get("Nome") or "").strip()
            if nome:
                especies.append(nome)
    return especies if especies else ["Pikachu"]


def _nomes_ataques_catalogo() -> List[str]:
    catalogo = carregar_catalogo_ataques()
    nomes = [str(getattr(spec, "nome", "")).strip() for spec in catalogo.listar()]
    return nomes


def _montar_pokemon_aleatorio(especie: str, ataques_catalogo: List[str], rng: random.Random) -> Dict[str, object]:
    pokemon = criar_pokemon_inicial_materializado(especie)
    estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    base = [nome for nome in ataques_catalogo if nome]
    rng.shuffle(base)
    escolhidos = base[: rng.randint(3, 5)] if base else ["Investida"]
    habilidades = [{"Ataque": nome} for nome in escolhidos]
    while len(habilidades) < 5:
        habilidades.append(None)
    estado["habilidades"] = habilidades[:5]
    estado["memorias"] = habilidades[:5]
    return pokemon


def _construir_times_aleatorios(seed: int | None = None) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    rng = _rng(seed)
    especies = _carregar_especies()
    ataques_catalogo = _nomes_ataques_catalogo()
    if len(especies) >= 12:
        especies_escolhidas = rng.sample(especies, 12)
    else:
        especies_escolhidas = [rng.choice(especies) for _ in range(12)]
    time_1 = [_montar_pokemon_aleatorio(especies_escolhidas[i], ataques_catalogo, rng) for i in range(6)]
    time_2 = [_montar_pokemon_aleatorio(especies_escolhidas[i + 6], ataques_catalogo, rng) for i in range(6)]
    return time_1, time_2


def criar_contexto_debug_6v6(seed: int | None = None) -> ContextoDebug6v6:
    time_1, time_2 = _construir_times_aleatorios(seed=seed)
    time_jogador = {"Nome": "Time Debug Jogador", "Slots": time_1}
    time_inimigo = {"Nome": "Time Debug Inimigo", "Slots": time_2}

    contexto_cliente: Dict[str, object] = {
        "tipo": "treinador",
        "modo_teste": True,
        "server_ip": "local-debug",
        "client_id": "debug_player",
        "client_id_inimigo": "debug_enemy",
        "batalha_id_servidor": "debug_6v6_novo_combate",
        "largura": 80,
        "altura": 40,
        "centro": [40.0, 20.0],
        "arena_largura": 40,
        "arena_altura": 20,
        "clima": "",
        "time_jogador": time_jogador,
        "times_jogador": [time_jogador],
        "pokemons_jogador": list(time_1),
        "npc_contexto": {
            "batalha_numero": 1,
            "times_pokemon": [time_inimigo],
        },
    }

    batalha_inicial = InicializadorBatalha(contexto_cliente).inicializar()
    contexto_servidor = {
        **contexto_cliente,
        **batalha_inicial,
        "tipo": "debug",
        "modo_teste": True,
        "batalha_id": "debug_6v6_novo_combate",
    }
    return ContextoDebug6v6(contexto_cliente=contexto_cliente, contexto_servidor=contexto_servidor)


class _ServidorLocalBatalha:
    def __init__(self, contexto_servidor: Dict[str, object]):
        self._contexto_servidor = dict(contexto_servidor)
        self._leitor = LeitorJogadas()
        self._sistema_por_batalha: Dict[str, SistemaBatalhaServidor] = {}
        self._client_jogador = str(self._contexto_servidor.get("client_id") or "debug_player")
        self._client_inimigo = str(self._contexto_servidor.get("client_id_inimigo") or "debug_enemy")

    def iniciar(
        self,
        ip: str = "",
        client_id: str = "",
        contexto_batalha: Dict[str, object] | None = None,
        **kwargs,
    ) -> Dict[str, object]:
        _ = ip
        if contexto_batalha is None and isinstance(kwargs.get("contexto"), dict):
            contexto_batalha = dict(kwargs.get("contexto") or {})
        if contexto_batalha is None and isinstance(kwargs.get("contexto_batalha"), dict):
            contexto_batalha = dict(kwargs.get("contexto_batalha") or {})
        client_resolvido = str(client_id or self._client_jogador)
        contexto = dict(self._contexto_servidor)
        if isinstance(contexto_batalha, dict):
            contexto.update(contexto_batalha)
        batalha_id = str(contexto.get("batalha_id") or "debug_6v6_novo_combate")
        sistema = SistemaBatalhaServidor(batalha_id=batalha_id, client_id=client_resolvido, contexto=contexto)
        self._sistema_por_batalha[batalha_id] = sistema
        return {"status": "ok", "mensagem": "Batalha iniciada", "batalha": sistema.snapshot()}

    def enviar_jogadas(
        self,
        ip: str = "",
        client_id: str = "",
        jogadas: List[Dict[str, object]] | None = None,
        batalha_id: str = "",
        **kwargs,
    ) -> Dict[str, object]:
        _ = ip
        client_resolvido = str(client_id or self._client_jogador)
        batalha_resolvida = str(batalha_id or kwargs.get("batalha_id_servidor") or "debug_6v6_novo_combate")
        bid = batalha_resolvida
        sistema = self._sistema_por_batalha.get(bid)
        if sistema is None:
            return {"status": "erro", "mensagem": "Batalha nao encontrada"}
        recebidas = [dict(j) for j in list(jogadas or []) if isinstance(j, dict)]

        por_cliente: Dict[str, List[Dict[str, object]]] = {self._client_jogador: [], self._client_inimigo: []}
        for jogada in recebidas:
            executor_id = str(jogada.get("executor_id") or "")
            pokemon = sistema.obter_pokemon(executor_id) if executor_id else None
            lado = str(getattr(pokemon, "Lado", "") or "").strip().casefold()
            if lado == "inimigo":
                por_cliente[self._client_inimigo].append(jogada)
            else:
                por_cliente[self._client_jogador].append(jogada)

        if client_resolvido == self._client_inimigo:
            jogadas_solicitante = por_cliente[self._client_inimigo]
            jogadas_oponente = por_cliente[self._client_jogador]
            cliente_oponente = self._client_jogador
        else:
            jogadas_solicitante = por_cliente[self._client_jogador]
            jogadas_oponente = por_cliente[self._client_inimigo]
            cliente_oponente = self._client_inimigo
        sistema.adicionar_jogadas(cliente_oponente, jogadas_oponente)

        respostas: List[Dict[str, object]] = []
        resposta_turno = self._leitor.executar_turno(sistema, client_id=client_resolvido, jogadas=jogadas_solicitante)
        respostas.append(resposta_turno)
        final = _mesclar_respostas_turno(respostas)
        return final


def _mesclar_respostas_turno(respostas: List[Dict[str, object]]) -> Dict[str, object]:
    validas = [dict(r) for r in list(respostas or []) if isinstance(r, dict)]
    if not validas:
        return {"status": "erro", "mensagem": "sem_respostas"}
    base = dict(validas[-1])
    logs = [dict(r.get("log") or {}) for r in validas if isinstance(r.get("log"), dict)]
    eventos: List[Dict[str, object]] = []
    for r in validas:
        eventos.extend([dict(e) for e in list(r.get("eventos") or []) if isinstance(e, dict)])
    log_final = {
        "sumario": [],
        "historico": [],
        "resultados": [],
        "alertas": [],
    }
    for log in logs:
        for chave in ("sumario", "historico", "resultados", "alertas"):
            log_final[chave].extend([dict(item) for item in list(log.get(chave) or []) if isinstance(item, dict)])
    base["eventos"] = eventos
    if logs:
        base["log"] = log_final
    escolhida = max(validas, key=lambda r: len(list(((r.get("log") or {}).get("historico") or [])) + list(r.get("eventos") or [])))
    if len(list((log_final.get("historico") or []))) <= 0 and isinstance(escolhida.get("log"), dict):
        base["log"] = dict(escolhida.get("log") or {})
    if isinstance(escolhida.get("batalha"), dict):
        base["batalha"] = dict(escolhida.get("batalha") or {})
    base["status"] = str(base.get("status") or escolhida.get("status") or "ok")
    base["rodada"] = max([int(r.get("rodada") or 0) for r in validas], default=int(base.get("rodada") or 0))
    base["tick"] = max([int(r.get("tick") or 0) for r in validas], default=int(base.get("tick") or 0))
    return base


def _aplicar_patch_servidor_local(servidor_local: _ServidorLocalBatalha):
    import Codigo.ModulosBatalha.ControladorJogadas as modulo_jogadas
    import Codigo.ModulosBatalha.SistemaBatalha as modulo_sistema_cliente

    original_iniciar = modulo_sistema_cliente.iniciar_batalha_server
    original_enviar = modulo_jogadas.enviar_jogada_batalha_server

    modulo_sistema_cliente.iniciar_batalha_server = servidor_local.iniciar
    modulo_jogadas.enviar_jogada_batalha_server = servidor_local.enviar_jogadas

    return modulo_sistema_cliente, modulo_jogadas, original_iniciar, original_enviar


def _restaurar_patch_servidor_local(modulo_sistema_cliente, modulo_jogadas, original_iniciar, original_enviar):
    modulo_sistema_cliente.iniciar_batalha_server = original_iniciar
    modulo_jogadas.enviar_jogada_batalha_server = original_enviar


def _montar_camera(contexto: Dict[str, object], tamanho_tela=(1920, 1080)) -> CameraBatalha:
    tile_px = 40
    largura = float(contexto.get("largura", 80) or 80)
    altura = float(contexto.get("altura", 40) or 40)
    centro = contexto.get("centro") if isinstance(contexto.get("centro"), (list, tuple)) else [largura * 0.5, altura * 0.5]
    arena_w = float(contexto.get("arena_largura", 40) or 40)
    arena_h = float(contexto.get("arena_altura", 20) or 20)
    half_w = (float(tamanho_tela[0]) / float(tile_px)) * 0.5
    half_h = (float(tamanho_tela[1]) / float(tile_px)) * 0.5
    pos_inicial = (float(centro[0]) - half_w, float(centro[1]) - half_h)

    camera = CameraBatalha(tamanho_tela, posicao_inicial_tiles=pos_inicial, tile_px=tile_px)
    camera.definir_limites_mundo(largura, altura, toroidal=False)
    camera.definir_referencia_arena((float(centro[0]) - (arena_w * 0.5), float(centro[1]) - (arena_h * 0.5)), (arena_w, arena_h))
    camera.atualizar(0.0)
    return camera


def _jogada_para_smoke(executor_id: str, ataque: str, alvo_id: str | None = None) -> Dict[str, object]:
    catalogo = carregar_catalogo_ataques()
    spec = catalogo.obter(ataque)
    preparo = getattr(spec, "preparo", None) if spec is not None else None
    execucao = getattr(spec, "execucao", None) if spec is not None else None
    tipo_preparo = str(getattr(preparo, "tipo", "") or "alvo")
    forma = str(getattr(execucao, "forma", "") or "alvo")
    return {
        "executor_id": executor_id,
        "ataque": {"Ataque": ataque},
        "ataque_id": ataque,
        "tipo_preparo": tipo_preparo,
        "forma": forma,
        "origem_mundo": [10.0, 10.0],
        "destino_mundo": [24.0, 10.0],
        "alvo_ids": [alvo_id] if alvo_id else [],
        "intensidade": 1.0,
    }


def _ataques_do_pokemon(pokemon) -> List[str]:
    ataques: List[str] = []
    bruto = pokemon.serializar() if hasattr(pokemon, "serializar") else {}
    for chave in ("habilidades", "memorias"):
        for item in list(bruto.get(chave) or []):
            if not isinstance(item, dict):
                continue
            nome = str(item.get("Ataque") or item.get("Nome") or "").strip()
            if nome and nome not in ataques:
                ataques.append(nome)
    return ataques


def validar_pipeline_basico() -> None:
    erros = validar_arquivo()
    if erros:
        raise AssertionError(f"ValidadorAtaques encontrou erros: {erros[:3]}")

    contexto = criar_contexto_debug_6v6().contexto_servidor
    sistema = SistemaBatalhaServidor(batalha_id="debug_6v6_novo_combate", client_id="debug_player", contexto=contexto)
    leitor = LeitorJogadas()
    rng = _rng(77331)

    ativos_jogador = sistema.listar_ativos("jogador")
    ativos_inimigo = sistema.listar_ativos("inimigo")
    if not ativos_jogador or not ativos_inimigo:
        raise AssertionError("Contexto 6v6 invalido: nao ha ativos de ambos os lados")

    jogador_uid = ativos_jogador[0].Uid
    inimigo_uid = ativos_inimigo[0].Uid

    retorno_final = None
    for _ in range(8):
        poke_j = sistema.obter_pokemon(jogador_uid)
        poke_i = sistema.obter_pokemon(inimigo_uid)
        ataques_j = _ataques_do_pokemon(poke_j)
        ataques_i = _ataques_do_pokemon(poke_i)
        if not ataques_j or not ataques_i:
            raise AssertionError("Pokemon sem ataques para simular rodada aleatoria")
        atk_j = rng.choice(ataques_j)
        atk_i = rng.choice(ataques_i)
        r1 = leitor.executar_turno(sistema, "debug_player", [_jogada_para_smoke(jogador_uid, atk_j, inimigo_uid)])
        if str(r1.get("status")) not in {"aguardando", "ok", "finalizada"}:
            raise AssertionError(f"Status inesperado do player: {r1}")
        r2 = leitor.executar_turno(sistema, "debug_enemy", [_jogada_para_smoke(inimigo_uid, atk_i, jogador_uid)])
        if str(r2.get("status")) not in {"ok", "finalizada"}:
            raise AssertionError(f"Status inesperado do inimigo: {r2}")
        retorno_final = r2

    if not isinstance(retorno_final, dict):
        raise AssertionError("Pipeline sem retorno final")
    for chave in ("status", "rodada", "tick", "log", "eventos", "batalha"):
        if chave not in retorno_final:
            raise AssertionError(f"Retorno sem chave obrigatoria: {chave}")
    log = retorno_final.get("log") if isinstance(retorno_final.get("log"), dict) else {}
    for chave in ("sumario", "historico", "resultados", "alertas"):
        if chave not in log:
            raise AssertionError(f"Log incompleto: {chave}")


class AppTesteBatalhaReal6v6:
    def __init__(self) -> None:
        self.contexto = criar_contexto_debug_6v6()
        self.servidor_local = _ServidorLocalBatalha(self.contexto.contexto_servidor)
        self._patch_info = _aplicar_patch_servidor_local(self.servidor_local)

        pygame.init()
        self.tela = pygame.display.set_mode((1920, 1080))
        pygame.display.set_caption("Teste Batalha Real 6v6 - Novo Combate")
        self.clock = pygame.time.Clock()

        self.camera = _montar_camera(self.contexto.contexto_cliente, tamanho_tela=(1920, 1080))
        self.controlador = ControladorBatalha(self.contexto.contexto_cliente)
        self.hud = ElementosHudBatalha(controlador_batalha=self.controlador, camera=self.camera)

        self.rodando = True

    def finalizar(self):
        _restaurar_patch_servidor_local(*self._patch_info)
        pygame.quit()

    def _salvar_log(self):
        pasta = Path("Relatorios") / "ReestruturaCombate"
        pasta.mkdir(parents=True, exist_ok=True)
        ultimo_retorno = self.controlador.Contexto.get("batalha_servidor_ultimo_envio")
        log = ultimo_retorno.get("log") if isinstance(ultimo_retorno, dict) and isinstance(ultimo_retorno.get("log"), dict) else {}
        arquivo = pasta / "ultimo_log_teste_6v6.json"
        arquivo.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Teste6v6] log salvo em {arquivo}")

    def _processar_hotkeys_debug(self, eventos: List[pygame.event.Event]):
        for ev in eventos:
            if ev.type != pygame.KEYDOWN:
                continue
            if ev.key == pygame.K_F12:
                self._salvar_log()

    def executar(self):
        try:
            while self.rodando:
                dt = self.clock.tick(180) / 1000.0
                eventos = pygame.event.get()
                for ev in eventos:
                    if ev.type == pygame.QUIT:
                        self.rodando = False

                self._processar_hotkeys_debug(eventos)
                eventos_camera = self.hud.filtrar_eventos_camera(self.tela, eventos, dt)
                self.camera.processar_eventos(eventos_camera)
                self.camera.atualizar(dt)

                self.tela.fill((20, 20, 28))
                self.controlador.atualizar(eventos, dt)
                self.controlador.renderizar(self.tela, self.camera)
                self.hud.desenhar(self.tela, eventos, dt)
                pygame.display.flip()
        finally:
            self.finalizar()


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste real 6v6 do novo combate")
    parser.add_argument("--smoke", action="store_true", help="Executa validacao automatica basica sem abrir loop jogavel")
    args = parser.parse_args()

    if args.smoke:
        validar_pipeline_basico()
        print("Smoke test do pipeline 6v6 executado com sucesso.")
        return

    if os.environ.get("SDL_VIDEODRIVER", "").lower() == "dummy":
        print("SDL_VIDEODRIVER=dummy detectado: execute sem --smoke em ambiente com video real para modo jogavel.")

    app = AppTesteBatalhaReal6v6()
    app.executar()


if __name__ == "__main__":
    main()
