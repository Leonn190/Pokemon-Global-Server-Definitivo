from __future__ import annotations
from SimuladorServerJogo.Mundo.BancoDados import BANCO_DADOS
from SimuladorServerJogo.Mundo.DungeonGeometria import eh_dimensao_dungeon, nome_dimensao_dungeon
from SimuladorServerJogo.Gerais.LoaderRegras import carregar_regras_dungeons
from SimuladorServerJogo.Gerais.Geradores.GeradorDungeons import gerar_dungeon_layout

class CerebroDungeons:
    def __init__(self, cerebro_central):
        self._cerebro = cerebro_central
        self._regras = carregar_regras_dungeons()
        self._layouts = {}

    def obter_ou_gerar(self, dungeon_code, porta_idx=1, pedra_id=0):
        dim = nome_dimensao_dungeon(dungeon_code)
        if dim in self._layouts:
            return self._layouts[dim]
        self._layouts[dim] = gerar_dungeon_layout(str(dungeon_code), [{"porta_idx": int(porta_idx or 1), "pedra_id": int(pedra_id or 0)}])
        return self._layouts[dim]

    def chunks_proximos(self, dimensao, centro, raio):
        layout = self._layouts.get(str(dimensao), {}) if isinstance(self._layouts.get(str(dimensao), {}), dict) else {}
        bloco = max(1, int(layout.get("tamanho_bloco_sala_tiles", 30) or 30))
        chunk_sz = max(1, int(BANCO_DADOS.chunk_tamanho_unidade()))
        max_x = max(1, int((int(layout.get("largura_blocos", 1) or 1) * bloco + chunk_sz - 1) // chunk_sz))
        max_y = max(1, int((int(layout.get("altura_blocos", 1) or 1) * bloco + chunk_sz - 1) // chunk_sz))
        cx, cy = int(centro[0]), int(centro[1])
        out = []
        for dx in range(-int(raio), int(raio)+1):
            for dy in range(-int(raio), int(raio)+1):
                nx, ny = cx + dx, cy + dy
                if nx < 0 or ny < 0 or nx >= max_x or ny >= max_y:
                    continue
                out.append((nx, ny))
        return out

    def chunk_em_grade(self, dimensao, chunk):
        t = int(BANCO_DADOS.chunk_tamanho_unidade())
        return [[0 for _ in range(t)] for _ in range(t)]

    def entrar_dungeon(self, client_id, pedra_id, porta_idx, dungeon_code):
        obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(client_id)) or 0)
        player = BANCO_DADOS.obter_objeto(obj_id)
        if player is None or not isinstance(getattr(player, 'estado_extra', None), dict): return False
        pedra = BANCO_DADOS.obter_objeto(int(pedra_id or 0))
        estado_pedra = getattr(pedra, "estado_extra", {}) if pedra is not None and isinstance(getattr(pedra, "estado_extra", {}), dict) else {}
        if str(estado_pedra.get("subtipo") or "").lower() != "dungeon":
            return False
        if not bool(estado_pedra.get("porta_ativa", False) or estado_pedra.get("estrutura_quebrada", False)):
            return False
        code_real = str(dungeon_code or estado_pedra.get("dungeon_code") or "").strip()
        if not code_real:
            return False
        porta_real = int(porta_idx or estado_pedra.get("porta_idx", 1) or 1)
        if str(estado_pedra.get("dungeon_code") or code_real).strip().lower() != code_real.lower():
            return False
        if int(estado_pedra.get("porta_idx", porta_real) or porta_real) != int(porta_real):
            return False
        dx = float(player.posicao[0]) - float(getattr(pedra, "posicao", [0.0, 0.0])[0]); dy = float(player.posicao[1]) - float(getattr(pedra, "posicao", [0.0, 0.0])[1])
        if (dx * dx + dy * dy) > float(self._regras.get("raio_interacao_porta", 2.0)) ** 2:
            return False
        layout = self.obter_ou_gerar(code_real, porta_real, pedra_id)
        entrada = next((e for e in layout.get('entradas', []) if int(e.get('porta_idx', 0)) == int(porta_real)), None) or (layout.get('entradas') or [{}])[0]
        player.estado_extra['ultima_pos_mundo']=[float(player.posicao[0]), float(player.posicao[1])]
        player.estado_extra['dimensao']=layout.get('dimensao')
        player.estado_extra['estado_dungeon']={"dungeon_code":str(code_real),"porta_idx":int(porta_real),"pedra_id":int(pedra_id or 0),"coracoes":int(self._regras.get('coracoes_iniciais',3)),'coracoes_max':int(self._regras.get('coracoes_maximos',3)),"entrada_mundo":list(player.estado_extra['ultima_pos_mundo']),"dimensao":layout.get('dimensao')}
        sx, sy = float(entrada.get('spawn', [0, 0])[0]), float(entrada.get('spawn', [0, 0])[1])
        player.definir_posicao(sx, sy)
        return True

    def sair_dungeon(self, client_id):
        obj_id = int(BANCO_DADOS.objeto_id_por_usuario(str(client_id)) or 0)
        player = BANCO_DADOS.obter_objeto(obj_id)
        if player is None or not isinstance(getattr(player,'estado_extra',None),dict): return False
        if not eh_dimensao_dungeon(player.estado_extra.get('dimensao')): return False
        estado_dungeon = player.estado_extra.get("estado_dungeon") if isinstance(player.estado_extra.get("estado_dungeon"), dict) else {}
        dimensao = str(player.estado_extra.get("dimensao") or "")
        layout = self._layouts.get(dimensao) if isinstance(self._layouts.get(dimensao), dict) else {}
        porta_idx = int(estado_dungeon.get("porta_idx", 1) or 1)
        entrada = next((e for e in (layout.get("entradas") or []) if int(e.get("porta_idx", 0) or 0) == porta_idx), None)
        saida = entrada.get("saida") if isinstance(entrada, dict) else None
        if isinstance(saida, (list, tuple)) and len(saida) == 2:
            dx = float(player.posicao[0]) - float(saida[0]); dy = float(player.posicao[1]) - float(saida[1])
            if (dx * dx + dy * dy) > float(self._regras.get("raio_interacao_porta", 2.0)) ** 2:
                return False
        pedra = BANCO_DADOS.obter_objeto(int(estado_dungeon.get("pedra_id", 0) or 0))
        pos = list(getattr(pedra, "posicao", [])) if pedra is not None else []
        if not (isinstance(pos, list) and len(pos) == 2):
            pos = player.estado_extra.get('ultima_pos_mundo') or estado_dungeon.get("entrada_mundo") or [0.0, 0.0]
        player.definir_posicao(float(pos[0]), float(pos[1]))
        player.estado_extra['dimensao']='Mundo'
        return True

    def registrar_derrota_dungeon(self, *args, **kwargs):
        return None
