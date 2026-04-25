from __future__ import annotations

import unittest

from SimuladorServerJogo.Batalha.Partida import Partida


def _pokemon(pid, lado, area=None, ativo=True, reserva=False, vida=200, ene=40, inte=20, vel=20, ataques=None):
    return {
        "id_batalha": pid,
        "lado_id": lado,
        "ativo": ativo,
        "em_reserva": reserva,
        "vivo": True,
        "area_id": area,
        "ataques": ataques or [{"Code": 6, "Ataque": "Arranhar", "Tipo": "normal"}],
        "dados": {
            "nome": pid,
            "especie": pid,
            "tipos": ["normal"],
            "estado": {"stats": {"Vida": vida, "Atk": 80, "SpA": 60, "Def": 30, "SpD": 30, "Mag": 30, "Ene": 20, "Int": inte, "Vel": vel, "CrC": 0, "CrD": 50, "Acuracia": 100, "Assertividade": 100, "Per": 0}},
            "EnergiaAtual": ene,
            "VidaAtual": vida,
        },
    }


class TesteFase03(unittest.TestCase):
    def _partida(self):
        return Partida(
            "001",
            {
                "rodada_atual": 1,
                "lados": [{"lado_id": 50}, {"lado_id": 51}],
                "pokemons": [
                    _pokemon("p1", 50, "A1", ativo=True, inte=30, vel=20),
                    _pokemon("p2", 50, "A2", ativo=True, inte=20, vel=25),
                    _pokemon("p3", 50, None, ativo=False, reserva=True, inte=10, vel=10),
                    _pokemon("i1", 51, "I1", ativo=True, inte=29, vel=22),
                    _pokemon("i2", 51, "I2", ativo=True, inte=15, vel=30),
                ],
            },
        )

    def test_inicializacao_real(self):
        p = self._partida()
        self.assertEqual(p.id_partida, "001")
        self.assertTrue(p.pokemons_por_id)
        self.assertEqual(p.ocupacao_areas["A1"], "p1")

    def test_ordenacao(self):
        p = self._partida()
        p.jogadas_recebidas = {
            50: {"lado_id": 50, "acoes": [{"tipo": "movimento", "pokemon_id": "p2", "destino": {"area_id": "A3"}}, {"tipo": "ataque", "pokemon_id": "p1", "ataque": {"Code": 6, "nome": "Arranhar"}, "alvo": {"area_id": "I1"}}]},
            51: {"lado_id": 51, "acoes": [{"tipo": "ataque", "pokemon_id": "i1", "ataque": {"Code": 6, "nome": "Arranhar"}, "alvo": {"area_id": "A1"}}]},
        }
        v, _ = p.coletor_acoes.coletar()
        self.assertEqual(v[0]["pokemon_id"], "p1")

    def test_energia(self):
        p = self._partida()
        p.obter_pokemon("p1").EnergiaAtual = 5
        p.jogadas_recebidas = {50: {"lado_id": 50, "acoes": [{"tipo": "ataque", "pokemon_id": "p1", "ataque": {"Code": 6, "nome": "Arranhar"}, "alvo": {"area_id": "I1"}}]}, 51: {"lado_id": 51, "acoes": []}}
        r = p.resolver_rodada()
        self.assertEqual(r["status"], "ok")
        self.assertGreaterEqual(p.obter_pokemon("p1").EnergiaAtual, 0)

    def test_movimento_e_troca(self):
        p = self._partida()
        p.jogadas_recebidas = {50: {"lado_id": 50, "acoes": [{"tipo": "movimento", "pokemon_id": "p1", "destino": {"area_id": "A3"}}]}, 51: {"lado_id": 51, "acoes": []}}
        p.resolver_rodada()
        self.assertEqual(p.obter_pokemon("p1").area_id, "A3")

    def test_troca_reserva(self):
        p = self._partida()
        p.jogadas_recebidas = {50: {"lado_id": 50, "acoes": [{"tipo": "troca_reserva", "pokemon_id": "p1", "pokemon_reserva_id": "p3"}]}, 51: {"lado_id": 51, "acoes": []}}
        p.resolver_rodada()
        self.assertTrue(p.obter_pokemon("p3").ativo)
        self.assertTrue("entrou_na_rodada" not in p.obter_pokemon("p3").estados_transitorios)

    def test_dano_morte(self):
        p = self._partida()
        alvo = p.obter_pokemon("i1")
        alvo.VidaAtual = 20
        p.jogadas_recebidas = {50: {"lado_id": 50, "acoes": [{"tipo": "ataque", "pokemon_id": "p1", "ataque": {"Code": 6, "nome": "Arranhar"}, "alvo": {"area_id": "I1"}}]}, 51: {"lado_id": 51, "acoes": []}}
        p.resolver_rodada()
        self.assertFalse(alvo.esta_vivo() or alvo.VidaAtual > 0)

    def test_barreira(self):
        p = self._partida()
        alvo = p.obter_pokemon("i1")
        alvo.BarreiraAtual = 50
        vida = alvo.VidaAtual
        p.jogadas_recebidas = {50: {"lado_id": 50, "acoes": [{"tipo": "ataque", "pokemon_id": "p1", "ataque": {"Code": 6, "nome": "Arranhar"}, "alvo": {"area_id": "I1"}}]}, 51: {"lado_id": 51, "acoes": []}}
        p.resolver_rodada()
        self.assertEqual(alvo.VidaAtual, vida)

    def test_efeitos_limite(self):
        p = self._partida()
        poke = p.obter_pokemon("p1")
        for c in [1, 2, 3, 4, 5]:
            poke.ReceberEfeito({"code": c, "nome": f"E{c}", "duracao": 2})
        self.assertEqual(len(poke.efeitos_formais), 4)

    def test_fim_batalha(self):
        p = self._partida()
        for pid in ["i1", "i2"]:
            p.obter_pokemon(pid).Morrer()
        p.verificar_fim_batalha()
        self.assertTrue(p.finalizada)
        self.assertEqual(p.vencedor, 50)


if __name__ == "__main__":
    unittest.main()
