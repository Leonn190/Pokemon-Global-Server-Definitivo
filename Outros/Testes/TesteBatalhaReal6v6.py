from __future__ import annotations

import argparse
import csv
import json
import os
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
from Codigo.ModulosBatalha.DebugCombate import dbg_combate
from SimuladorServerJogo.Batalha.LeitorJogadas import LeitorJogadas
from SimuladorServerJogo.Batalha.SistemaBatalha import SistemaBatalha as SistemaBatalhaServidor
from SimuladorServerJogo.Gerais.Geradores.GeradorPokemon import criar_pokemon_inicial_materializado

ATAQUES_OBRIGATORIOS = [
    "Investida",
    "Biscoito",
    "Enraivecer",
    "Provocar",
    "Proteger",
    "Arranhar",
    "Recarga",
    "Energia",
    "Hiper Raio",
    "Guilhotina",
    "Disparo",
    "Chifrada",
    "Resetar",
    "Tankar",
    "Estocada",
    "Bola Climática",
    "Hiper Presa",
    "Investida Selvagem",
]


@dataclass
class ContextoDebug6v6:
    contexto_cliente: Dict[str, object]
    contexto_servidor: Dict[str, object]


def _carregar_especies(qtd: int = 12) -> List[str]:
    caminho = Path("Dados") / "Pokemon Global Server - Pokemons.csv"
    if not caminho.exists():
        return ["Pikachu"] * qtd
    especies: List[str] = []
    with caminho.open("r", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)
        for row in leitor:
            nome = str(row.get("Nome") or "").strip()
            if nome:
                especies.append(nome)
            if len(especies) >= qtd:
                break
    while len(especies) < qtd:
        especies.append(especies[-1] if especies else "Pikachu")
    return especies


def _montar_pokemon_debug(especie: str, apelido: str, ataques: List[str]) -> Dict[str, object]:
    pokemon = criar_pokemon_inicial_materializado(especie)
    estado = pokemon.get("estado") if isinstance(pokemon.get("estado"), dict) else pokemon
    estado["Nome"] = apelido
    estado["nome"] = apelido
    habilidades = [{"Ataque": nome} for nome in ataques]
    while len(habilidades) < 5:
        habilidades.append(None)
    estado["habilidades"] = habilidades[:5]
    estado["memorias"] = habilidades[:5]
    estado["VidaAtual"] = max(float(estado.get("Vida", 100.0) or 100.0), 180.0)
    estado["energia_atual"] = max(float(estado.get("energia_atual", 100.0) or 100.0), 220.0)
    estado["EnergiaAtual"] = estado["energia_atual"]
    return pokemon


def _construir_times_debug() -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    especies = _carregar_especies(12)
    ataques_time_1 = [
        ["Investida", "Chifrada", "Investida Selvagem"],
        ["Biscoito", "Energia", "Disparo"],
        ["Enraivecer", "Provocar", "Recarga"],
        ["Arranhar", "Guilhotina", "Estocada"],
        ["Bola Climática", "Hiper Raio"],
        ["Proteger", "Resetar", "Hiper Presa", "Tankar"],
    ]
    ataques_time_2 = [
        ["Investida", "Biscoito", "Arranhar"],
        ["Enraivecer", "Proteger", "Recarga"],
        ["Provocar", "Energia", "Guilhotina"],
        ["Disparo", "Chifrada", "Resetar"],
        ["Tankar", "Estocada", "Bola Climática"],
        ["Hiper Presa", "Investida Selvagem", "Hiper Raio"],
    ]
    nomes_1 = [
        "Tester_Investida",
        "Tester_Biscoito",
        "Tester_Status",
        "Tester_Cone",
        "Tester_Projetil",
        "Tester_Laser",
    ]
    nomes_2 = [
        "Alvo_Investida",
        "Alvo_Biscoito",
        "Alvo_Status",
        "Alvo_Cone",
        "Alvo_Projetil",
        "Alvo_Laser",
    ]

    time_1 = [_montar_pokemon_debug(especies[i], nomes_1[i], ataques_time_1[i]) for i in range(6)]
    time_2 = [_montar_pokemon_debug(especies[i + 6], nomes_2[i], ataques_time_2[i]) for i in range(6)]
    return time_1, time_2


def criar_contexto_debug_6v6() -> ContextoDebug6v6:
    dbg_combate("TesteBatalhaReal6v6", "criacao do contexto")
    time_1, time_2 = _construir_times_debug()
    dbg_combate("TesteBatalhaReal6v6", "pokemons criados", jogador=len(time_1), inimigo=len(time_2))
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
        dbg_combate("TesteBatalhaReal6v6", "iniciar chamado", client_id=client_id)
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
        dbg_combate("TesteBatalhaReal6v6", "iniciar chamado", client_id=client_id)
        client_resolvido = str(client_id or self._client_jogador)
        batalha_resolvida = str(batalha_id or kwargs.get("batalha_id_servidor") or "debug_6v6_novo_combate")
        bid = batalha_resolvida
        sistema = self._sistema_por_batalha.get(bid)
        if sistema is None:
            return {"status": "erro", "mensagem": "Batalha nao encontrada"}
        dbg_combate("TesteBatalhaReal6v6", "enviar_jogadas chamado", client_id=client_resolvido, batalha_id=bid)
        recebidas = [dict(j) for j in list(jogadas or []) if isinstance(j, dict)]
        dbg_combate("TesteBatalhaReal6v6", "servidor local recebeu jogadas", quantidade=len(recebidas))

        por_cliente: Dict[str, List[Dict[str, object]]] = {self._client_jogador: [], self._client_inimigo: []}
        for jogada in recebidas:
            executor_id = str(jogada.get("executor_id") or "")
            pokemon = sistema.obter_pokemon(executor_id) if executor_id else None
            lado = str(getattr(pokemon, "Lado", "") or "").strip().casefold()
            if lado == "inimigo":
                por_cliente[self._client_inimigo].append(jogada)
            else:
                por_cliente[self._client_jogador].append(jogada)

        dbg_combate("TesteBatalhaReal6v6", "split por lado", jogador=len(por_cliente[self._client_jogador]), inimigo=len(por_cliente[self._client_inimigo]))
        ultima_resposta: Dict[str, object] = {"status": "aguardando", "mensagem": "Aguardando jogadas"}
        ultima_resposta = self._leitor.executar_turno(sistema, client_id=self._client_jogador, jogadas=por_cliente[self._client_jogador])
        if not por_cliente[self._client_inimigo]:
            dbg_combate("TesteBatalhaReal6v6", "auto-complete lado vazio", lado="inimigo")
        ultima_resposta = self._leitor.executar_turno(sistema, client_id=self._client_inimigo, jogadas=por_cliente[self._client_inimigo])
        if not por_cliente[self._client_jogador]:
            dbg_combate("TesteBatalhaReal6v6", "auto-complete lado vazio", lado="jogador")
        dbg_combate("TesteBatalhaReal6v6", "resposta final", resposta=ultima_resposta)
        return ultima_resposta


def _aplicar_patch_servidor_local(servidor_local: _ServidorLocalBatalha):
    import Codigo.ModulosBatalha.ControladorJogadas as modulo_jogadas
    import Codigo.ModulosBatalha.SistemaBatalha as modulo_sistema_cliente

    original_iniciar = modulo_sistema_cliente.iniciar_batalha_server
    original_enviar = modulo_jogadas.enviar_jogada_batalha_server

    dbg_combate("TesteBatalhaReal6v6", "patch de rede aplicado")
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
    ataque_l = ataque.casefold()
    forma = "self"
    tipo_preparo = "self"
    if ataque_l in {"investida", "investida selvagem"}:
        forma = "impulso"
        tipo_preparo = "direcao_intensidade"
    elif ataque_l in {"biscoito", "disparo", "energia", "bola climática"}:
        forma = "projetil"
        tipo_preparo = "linha"
    elif ataque_l in {"arranhar", "guilhotina", "estocada"}:
        forma = "cone"
        tipo_preparo = "cone"
    elif ataque_l in {"proteger", "resetar", "hiper presa"}:
        forma = "alvo"
        tipo_preparo = "alvo"
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


def validar_pipeline_basico() -> None:
    erros = validar_arquivo()
    if erros:
        raise AssertionError(f"ValidadorAtaques encontrou erros: {erros[:3]}")

    catalogo = carregar_catalogo_ataques()
    faltantes = [nome for nome in ATAQUES_OBRIGATORIOS if not catalogo.existe(nome)]
    if faltantes:
        raise AssertionError(f"Ataques obrigatorios faltando no catalogo: {faltantes}")

    contexto = criar_contexto_debug_6v6().contexto_servidor
    sistema = SistemaBatalhaServidor(batalha_id="debug_6v6_novo_combate", client_id="debug_player", contexto=contexto)
    leitor = LeitorJogadas()

    ativos_jogador = sistema.listar_ativos("jogador")
    ativos_inimigo = sistema.listar_ativos("inimigo")
    if not ativos_jogador or not ativos_inimigo:
        raise AssertionError("Contexto 6v6 invalido: nao ha ativos de ambos os lados")

    jogador_uid = ativos_jogador[0].Uid
    inimigo_uid = ativos_inimigo[0].Uid

    rodadas = [
        ("Enraivecer", "Proteger"),
        ("Proteger", "Resetar"),
        ("Disparo", "Biscoito"),
        ("Arranhar", "Guilhotina"),
        ("Investida", "Investida Selvagem"),
    ]

    retorno_final = None
    for atk_j, atk_i in rodadas:
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

        self.fonte_titulo = pygame.font.SysFont("consolas", 26, bold=True)
        self.fonte_texto = pygame.font.SysFont("consolas", 20)
        self.fonte_mono = pygame.font.SysFont("consolas", 18)
        self.rodando = True
        self.ataques_testados: set[str] = set()
        self.ultimo_retorno: Dict[str, object] = {}
        self.ultimo_evento_historico = "-"
        self.status_turno = "aguardando"
        self.lista_controlaveis: List[object] = []
        self.indice_controlado = 0
        self._atualizar_lista_controlavel()
        self._selecionar_controlado(0)

    def finalizar(self):
        _restaurar_patch_servidor_local(*self._patch_info)
        pygame.quit()

    def _atualizar_lista_controlavel(self):
        aliados = list(self.controlador.PokemonsAliados)
        inimigos = list(self.controlador.PokemonsInimigos)
        self.lista_controlaveis = aliados + inimigos
        if self.lista_controlaveis:
            self.indice_controlado = max(0, min(self.indice_controlado, len(self.lista_controlaveis) - 1))

    def _selecionar_controlado(self, indice: int):
        self._atualizar_lista_controlavel()
        if not self.lista_controlaveis:
            return
        self.indice_controlado = indice % len(self.lista_controlaveis)
        self.controlador.selecionar_pokemon(self.lista_controlaveis[self.indice_controlado])

    def _marcar_ataques_por_log(self, resposta: Dict[str, object]):
        log = resposta.get("log") if isinstance(resposta.get("log"), dict) else {}
        historico = log.get("historico") if isinstance(log.get("historico"), list) else []
        for item in historico:
            if not isinstance(item, dict):
                continue
            tipo_evento = str(item.get("tipo") or item.get("evento") or "").strip()
            if tipo_evento == "acao_iniciada":
                nome = str(item.get("ataque") or "").strip()
                if nome:
                    self.ataques_testados.add(nome)
        if historico:
            ultimo = historico[-1]
            self.ultimo_evento_historico = str(ultimo.get("tipo") or ultimo.get("evento") or "-")

    def _coletar_retorno_servidor(self):
        resposta = self.controlador.Contexto.get("batalha_servidor_ultimo_envio")
        if not isinstance(resposta, dict) or resposta == self.ultimo_retorno:
            return
        self.ultimo_retorno = dict(resposta)
        self.status_turno = str(resposta.get("status") or self.status_turno)
        self._marcar_ataques_por_log(self.ultimo_retorno)
        if self.ultimo_retorno.get("eventos"):
            print("[Teste6v6] eventos:", self.ultimo_retorno.get("eventos"))

    def _salvar_log(self):
        pasta = Path("Relatorios") / "ReestruturaCombate"
        pasta.mkdir(parents=True, exist_ok=True)
        log = self.ultimo_retorno.get("log") if isinstance(self.ultimo_retorno.get("log"), dict) else {}
        arquivo = pasta / "ultimo_log_teste_6v6.json"
        arquivo.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Teste6v6] log salvo em {arquivo}")

    def _processar_hotkeys_debug(self, eventos: List[pygame.event.Event]):
        for ev in eventos:
            if ev.type != pygame.KEYDOWN:
                continue
            if ev.key == pygame.K_TAB and (ev.mod & pygame.KMOD_SHIFT):
                self._selecionar_controlado(self.indice_controlado - 1)
            elif ev.key == pygame.K_TAB:
                self._selecionar_controlado(self.indice_controlado + 1)
            elif pygame.K_1 <= ev.key <= pygame.K_6:
                self._selecionar_controlado(ev.key - pygame.K_1)
            elif pygame.K_F1 <= ev.key <= pygame.K_F6:
                self._selecionar_controlado(6 + (ev.key - pygame.K_F1))
            elif ev.key == pygame.K_RETURN:
                self.hud._confirmar_jogadas()
            elif ev.key == pygame.K_F12:
                self._salvar_log()

    def _desenhar_overlay(self):
        faltantes = [a for a in ATAQUES_OBRIGATORIOS if a not in self.ataques_testados]
        log = self.ultimo_retorno.get("log") if isinstance(self.ultimo_retorno.get("log"), dict) else {}
        historico = log.get("historico") if isinstance(log.get("historico"), list) else []
        painel_w = 620
        painel_h = 235
        painel = pygame.Surface((painel_w, painel_h), pygame.SRCALPHA)
        painel.fill((10, 14, 24, 205))
        pygame.draw.rect(painel, (112, 142, 196, 240), painel.get_rect(), width=2, border_radius=10)
        self.tela.blit(painel, (self.tela.get_width() - painel_w - 16, 16))

        base_x = self.tela.get_width() - painel_w
        base_y = 28
        cabecalho = f"Debug 6v6 | testados {len(self.ataques_testados)}/{len(ATAQUES_OBRIGATORIOS)}"
        self.tela.blit(self.fonte_titulo.render(cabecalho, True, (245, 248, 255)), (base_x, base_y))

        linhas = [
            f"Status: {self.status_turno}",
            f"Historico: {len(historico)} eventos",
            f"Ultimo evento: {self.ultimo_evento_historico}",
            "F12 salva log atual | TAB/SHIFT+TAB troca controlado",
        ]
        for i, linha in enumerate(linhas):
            self.tela.blit(self.fonte_texto.render(linha, True, (220, 232, 252)), (base_x, base_y + 40 + i * 24))

        ok_txt = ", ".join(sorted(self.ataques_testados)) if self.ataques_testados else "-"
        faltando_txt = ", ".join(faltantes) if faltantes else "Nenhum"
        self.tela.blit(self.fonte_mono.render(f"OK: {ok_txt[:82]}", True, (120, 255, 150)), (base_x, base_y + 145))
        self.tela.blit(self.fonte_mono.render(f"Faltando: {faltando_txt[:74]}", True, (255, 196, 120)), (base_x, base_y + 171))

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
                self._coletar_retorno_servidor()
                self._desenhar_overlay()
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
